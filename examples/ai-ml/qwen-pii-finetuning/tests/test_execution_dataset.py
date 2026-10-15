"""Execution data contracts; fixtures and logs never contain customer data."""

import copy
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

from data.generate_dataset import luhn_valid, rrn_checksum_valid
from src.dataset import completion_messages, prompt_messages, read_jsonl
from src.pii_tokens import parse_tsv, pseudonymize_text, reassemble_text


ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("train", "validation", "test")
LABELS = {"PERSON", "RRN", "DOB", "REL", "ADDRESS", "PHONE", "EMAIL", "ACCOUNT", "CARD"}
MANIFEST = "dataset-manifest.json"


def cli(*args, hash_seed="0"):
    return subprocess.run(
        [sys.executable, "-m", "data.execution_dataset", *map(str, args)],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": hash_seed},
        capture_output=True, text=True, timeout=30,
    )


def test_cli_builds_auditable_execution_corpus(tmp_path):
    directory = tmp_path / "corpus"
    result = cli("--output-dir", directory)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "passed"
    assert summary["counts"] == {"train": 1600, "validation": 200, "test": 400}
    assert summary["families"] == {"train": 800, "validation": 200, "test": 400}
    assert summary["augmented_records"] == {"train": 800, "validation": 0, "test": 0}
    assert summary["seed"] == 42
    assert summary["model_id"] == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    audit = cli("--audit-dir", directory)
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout) == summary


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    directory = tmp_path_factory.mktemp("execution") / "corpus"
    result = cli("--output-dir", directory)
    assert result.returncode == 0, result.stderr
    return directory


@pytest.fixture
def editable(corpus, tmp_path):
    directory = tmp_path / "editable"
    shutil.copytree(corpus, directory)
    return directory


def records(directory):
    return {split: read_jsonl(directory / f"{split}.jsonl") for split in SPLITS}


def test_reproducibility_is_independent_of_output_path_and_python_hash_seed(corpus, tmp_path):
    second, changed = tmp_path / "second", tmp_path / "changed"
    assert cli("--output-dir", second, "--seed", 42, hash_seed="91").returncode == 0
    assert cli("--output-dir", changed, "--seed", 43).returncode == 0
    for name in [*(f"{split}.jsonl" for split in SPLITS), MANIFEST]:
        assert (corpus / name).read_bytes() == (second / name).read_bytes()
    first_rows, changed_rows = records(corpus), records(changed)
    first_families = {r["provenance"]["family_id"] for r in first_rows["test"]}
    changed_families = {r["provenance"]["family_id"] for r in changed_rows["test"]}
    assert first_families != changed_families


def test_family_and_exact_nfc_text_contamination_are_absent(corpus):
    seen_sources, family_splits, seen_ids = set(), {}, set()
    for split, rows in records(corpus).items():
        by_id = {row["id"]: row for row in rows}
        for row in rows:
            provenance = row["provenance"]
            family = provenance["family_id"]
            source = unicodedata.normalize("NFC", row["source_text"])
            assert source not in seen_sources
            seen_sources.add(source)
            assert row["id"] not in seen_ids
            seen_ids.add(row["id"])
            assert family_splits.setdefault(family, split) == split
            assert provenance["split"] == split
            if provenance["augmentation"] == "base":
                assert provenance["parent_id"] is None
            else:
                assert split == "train"
                parent = by_id[provenance["parent_id"]]
                assert parent["provenance"]["family_id"] == family
                assert parent["provenance"]["augmentation"] == "base"
        sizes = Counter(row["provenance"]["family_id"] for row in rows)
        assert set(sizes.values()) == ({2} if split == "train" else {1})


def test_both_languages_cover_all_nine_labels_and_negative_documents(corpus):
    expected_languages = {
        "train": {"ko": 1280, "en": 320},
        "validation": {"ko": 160, "en": 40},
        "test": {"ko": 320, "en": 80},
    }
    for split, rows in records(corpus).items():
        assert Counter(row["language"] for row in rows) == expected_languages[split]
        assert {row["domain"] for row in rows} == {
            "insurance", "mortgage", "creditcard", "brokerage", "support",
        }
        for language in ("ko", "en"):
            selected = [r for r in rows if r["language"] == language]
            assert {e["type"] for r in selected for e in r["entities"]} == LABELS
            assert 0.1 < sum(not r["entities"] for r in selected) / len(selected) < 0.25
            assert len({r["provenance"]["template"] for r in selected}) == 6


def test_all_gold_values_match_source_order_and_round_trip_through_existing_loader(corpus):
    saw_nfd = False
    for rows in records(corpus).values():
        for row in rows:
            source, entities = row["source_text"], row["entities"]
            positions = [source.index(e["original"]) for e in entities]
            assert positions == sorted(positions)
            assert row["target_tsv"] == "\n".join(f"{e['type']}\t{e['original']}" for e in entities)
            parsed = parse_tsv(row["target_tsv"], source)
            assert {(e.type, e.original) for e in parsed} == {
                (e["type"], unicodedata.normalize("NFC", e["original"])) for e in entities
            }
            masked = pseudonymize_text(source, parsed)
            assert reassemble_text(masked.masked_text, masked.mapping) == unicodedata.normalize("NFC", source)
            assert prompt_messages(row)[1] == {"role": "user", "content": source}
            assert completion_messages(row) == [{"role": "assistant", "content": row["target_tsv"]}]
            assert row["id"] not in source
            assert row["provenance"]["family_id"] not in source
            saw_nfd |= source != unicodedata.normalize("NFC", source)
            for e in entities:
                digits = "".join(c for c in e["original"] if c.isdigit())
                if e["type"] == "RRN":
                    assert not rrn_checksum_valid(digits)
                if e["type"] == "CARD":
                    assert not luhn_valid(digits)
    assert saw_nfd


def test_manifest_records_hashes_and_honest_limitations_without_raw_values(corpus):
    summary = json.loads(cli("--audit-dir", corpus).stdout)
    raw_summary = json.dumps(summary, ensure_ascii=False)
    assert summary["guarantees"]["entity_disjoint"] is False
    assert summary["guarantees"]["template_disjoint"] is False
    assert summary["limitations"]
    for split, rows in records(corpus).items():
        assert summary["sha256"][split] == hashlib.sha256((corpus / f"{split}.jsonl").read_bytes()).hexdigest()
        assert summary["entity_types"][split] == Counter(e["type"] for r in rows for e in r["entities"])
        for row in rows:
            assert row["source_text"] not in raw_summary
            for e in row["entities"]:
                assert e["original"] not in raw_summary


def rewrite_with_new_hashes(directory, data):
    """Challenge semantic checks, with the ordinary file hash gate satisfied."""
    manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    for split, rows in data.items():
        file = directory / f"{split}.jsonl"
        file.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        manifest["sha256"][split] = hashlib.sha256(file.read_bytes()).hexdigest()
    (directory / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize("mutation", [
    "duplicate-id", "crosssplit-nfc-source", "family-leak", "holdout-child",
    "wrong-parent", "missing-record", "omitted-gold", "wrong-type",
    "absent-gold", "label-order", "wrong-tsv", "negative-false-positive",
    "source-and-gold", "source-fingerprint", "unexpected-field",
])
def test_audit_rejects_rehashed_semantic_tampering_without_logging_sources(editable, mutation):
    data = records(editable)
    train = data["train"]
    positive = next(r for r in train if len(r["entities"]) >= 4)
    canary = "PRIVATE_VALUE_MUST_NOT_APPEAR_IN_ERRORS"
    if mutation == "duplicate-id":
        train[1]["id"] = train[0]["id"]
    elif mutation == "crosssplit-nfc-source":
        original = next(r for r in train if r["language"] == "ko")
        target = data["test"][0]
        target["source_text"] = unicodedata.normalize("NFD", original["source_text"])
        target["entities"] = [
            {**e, "original": unicodedata.normalize("NFD", e["original"])}
            for e in original["entities"]
        ]
        target["target_tsv"] = "\n".join(f"{e['type']}\t{e['original']}" for e in target["entities"])
    elif mutation == "family-leak":
        parent = next(r for r in train if r["provenance"]["augmentation"] == "base")
        train.remove(parent)
        parent["provenance"]["split"] = "test"
        data["test"].append(parent)
    elif mutation == "holdout-child":
        parent = data["test"][0]
        child = copy.deepcopy(parent)
        child["id"] += ":child"
        child["source_text"] = "Extra context\n" + child["source_text"]
        child["provenance"].update(augmentation="context", parent_id=parent["id"])
        data["test"].append(child)
    elif mutation == "wrong-parent":
        child = next(r for r in train if r["provenance"]["parent_id"])
        child["provenance"]["parent_id"] = data["test"][0]["id"]
    elif mutation == "missing-record":
        train.pop()
    elif mutation == "omitted-gold":
        positive["entities"] = []
        positive["target_tsv"] = ""
    elif mutation in {"absent-gold", "wrong-type", "source-and-gold", "label-order"}:
        if mutation == "absent-gold":
            positive["entities"][0]["original"] = canary
        elif mutation == "wrong-type":
            # Valid whitelist type, but semantically wrong for this source.
            positive["entities"][0]["type"] = "EMAIL"
        elif mutation == "source-and-gold":
            old = positive["entities"][0]["original"]
            positive["source_text"] = positive["source_text"].replace(old, canary)
            positive["entities"][0]["original"] = canary
        else:
            positive["entities"].reverse()
        positive["target_tsv"] = "\n".join(f"{e['type']}\t{e['original']}" for e in positive["entities"])
    elif mutation == "wrong-tsv":
        positive["target_tsv"] = f"PERSON\t{canary}"
    elif mutation == "negative-false-positive":
        negative = next(r for r in train if not r["entities"])
        value = "1588-0000" if negative["language"] == "ko" else "+1-555-0100"
        negative["entities"] = [{"type": "PHONE", "original": value}]
        negative["target_tsv"] = f"PHONE\t{value}"
    elif mutation == "source-fingerprint":
        positive["provenance"]["source_nfc_sha256"] = "0" * 64
    else:
        positive["messages"] = [{"role": "user", "content": canary}]
    rewrite_with_new_hashes(editable, data)
    result = cli("--audit-dir", editable)
    assert result.returncode != 0
    assert result.stdout == ""
    assert canary not in result.stderr
    assert "Traceback" not in result.stderr


def test_hash_tampering_is_rejected(editable):
    path = editable / "train.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    result = cli("--audit-dir", editable)
    assert result.returncode != 0
    assert "hash" in result.stderr.lower()


@pytest.mark.parametrize("field,value", [
    ("seed", True), ("generator_version", "future"), ("counts", {"train": 1}),
    ("guarantees", {"entity_disjoint": True}), ("source_files_sha256", {}),
])
def test_manifest_tampering_is_rejected(editable, field, value):
    path = editable / MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest[field] = value
    path.write_text(json.dumps(manifest), encoding="utf-8")
    result = cli("--audit-dir", editable)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling-symlink"])
def test_existing_output_is_never_overwritten(tmp_path, kind):
    target = tmp_path / "existing"
    if kind == "directory":
        target.mkdir()
        sentinel = target / "keep"
    elif kind == "file":
        sentinel = target
    else:
        other = tmp_path / "other"
        if kind == "symlink":
            other.mkdir()
            sentinel = other / "keep"
        else:
            sentinel = tmp_path / "keep"
        target.symlink_to(other, target_is_directory=True)
    sentinel.write_bytes(b"untouched")
    result = cli("--output-dir", target)
    assert result.returncode != 0
    assert sentinel.read_bytes() == b"untouched"
    if kind == "dangling-symlink":
        assert not (tmp_path / "other").exists()


def test_api_rejects_boolean_seed_without_creating_output(tmp_path):
    module = importlib.import_module("data.execution_dataset")
    output = tmp_path / "bad-seed"
    with pytest.raises(ValueError):
        module.generate_execution_dataset(output, seed=True)
    assert not output.exists()


def test_invalid_json_is_rejected_without_echoing_input(editable):
    path = editable / MANIFEST
    path.write_text('{"PRIVATE_VALUE_MUST_NOT_APPEAR_IN_ERRORS":', encoding="utf-8")
    result = cli("--audit-dir", editable)
    assert result.returncode != 0
    assert "PRIVATE_VALUE_MUST_NOT_APPEAR_IN_ERRORS" not in result.stderr
    assert "Traceback" not in result.stderr
