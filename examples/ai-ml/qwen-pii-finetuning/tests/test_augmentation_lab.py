"""Behavioral checks for the separate CPU augmentation exercise."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from data.generate_dataset import generate_dataset
from src.dataset import completion_messages, prompt_messages
from src.pii_tokens import Entity, parse_tsv, pseudonymize_text, reassemble_text


ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("train", "validation", "test")


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "data.augmentation_lab", *map(str, args)],
        cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )


def read_records(directory):
    return {
        split: [json.loads(line) for line in (directory / f"{split}.jsonl").read_text().splitlines()]
        for split in SPLITS
    }


@pytest.fixture
def lab(tmp_path):
    directory = tmp_path / "lab"
    result = cli("--output-dir", directory, "--seed", 42)
    assert result.returncode == 0, result.stderr
    return directory


def rewrite_with_new_hashes(directory, records):
    """Keep hash checks satisfied so semantic audit checks must catch edits."""
    manifest_path = directory / "augmentation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for split, rows in records.items():
        file = directory / f"{split}.jsonl"
        file.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))
        manifest["sha256"][split] = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest["counts"][split] = len(rows)
        manifest["families"][split] = len({r["provenance"]["family_id"] for r in rows})
        manifest["negative_records"][split] = sum(r["provenance"]["kind"] == "negative" for r in rows)
        manifest["augmented_records"][split] = sum(r["provenance"]["augmentation"] != "base" for r in rows)
    manifest_path.write_text(json.dumps(manifest))


def test_cli_generates_then_audits_with_aggregate_only_output(tmp_path):
    directory = tmp_path / "new-lab"
    result = cli("--output-dir", directory, "--seed", 42)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["counts"] == {"train": 72, "validation": 8, "test": 8}
    assert summary["families"] == {"train": 24, "validation": 8, "test": 8}
    assert summary["negative_records"] == {"train": 36, "validation": 4, "test": 4}
    assert summary["augmented_records"] == {"train": 48, "validation": 0, "test": 0}
    assert summary["guarantees"]["entity_disjoint"] is False
    assert summary["guarantees"]["template_disjoint"] is False
    audit = cli("--audit-dir", directory)
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout) == summary
    for rows in read_records(directory).values():
        for row in rows:
            assert row["source_text"] not in result.stdout + audit.stdout
            for entity in row["entities"]:
                assert entity["original"] not in result.stdout + audit.stdout


def test_same_seed_reproduces_bytes_and_another_seed_changes_assignment(lab, tmp_path):
    second, different = tmp_path / "same", tmp_path / "different"
    assert cli("--output-dir", second, "--seed", 42).returncode == 0
    assert cli("--output-dir", different, "--seed", 43).returncode == 0
    for name in [*(f"{s}.jsonl" for s in SPLITS), "augmentation-manifest.json"]:
        assert (lab / name).read_bytes() == (second / name).read_bytes()
    assert (lab / "train.jsonl").read_bytes() != (different / "train.jsonl").read_bytes()


def test_families_are_disjoint_and_only_train_has_children(lab):
    records = read_records(lab)
    families = {
        split: {row["provenance"]["family_id"] for row in rows}
        for split, rows in records.items()
    }
    assert not families["train"] & families["validation"]
    assert not families["train"] & families["test"]
    assert not families["validation"] & families["test"]
    for split, rows in records.items():
        by_id = {row["id"]: row for row in rows}
        for row in rows:
            provenance = row["provenance"]
            assert provenance["split"] == split
            if provenance["augmentation"] == "base":
                assert provenance["parent_id"] is None
            else:
                assert split == "train"
                parent = by_id[provenance["parent_id"]]
                assert parent["provenance"]["augmentation"] == "base"
                assert parent["provenance"]["family_id"] == provenance["family_id"]


def test_labels_tsv_loader_and_unicode_round_trip_agree(lab):
    saw_nfd = False
    for rows in read_records(lab).values():
        for row in rows:
            source = row["source_text"]
            entities = [Entity(x["type"], x["original"]) for x in row["entities"]]
            assert all(entity.original in source for entity in entities)
            positions = [source.index(entity.original) for entity in entities]
            assert positions == sorted(positions)
            assert row["target_tsv"] == "\n".join(f"{e.type}\t{e.original}" for e in entities)
            parsed = parse_tsv(row["target_tsv"], source)
            assert {(e.type, e.original) for e in parsed} == {
                (e.type, unicodedata.normalize("NFC", e.original)) for e in entities
            }
            tokenized = pseudonymize_text(source, parsed)
            assert reassemble_text(tokenized.masked_text, tokenized.mapping) == unicodedata.normalize("NFC", source)
            assert prompt_messages(row)[1]["content"] == source
            assert completion_messages(row)[0]["content"] == row["target_tsv"]
            saw_nfd |= source != unicodedata.normalize("NFC", source)
    assert saw_nfd


def test_negative_descendants_keep_empty_targets_and_source_text(lab):
    for rows in read_records(lab).values():
        negatives = [r for r in rows if r["provenance"]["kind"] == "negative"]
        assert negatives
        for row in negatives:
            assert row["entities"] == []
            assert row["target_tsv"] == ""
            tokenized = pseudonymize_text(row["source_text"], [])
            assert tokenized.masked_text == unicodedata.normalize("NFC", row["source_text"])
            assert tokenized.mapping == {}


def test_polarity_bearing_provenance_is_not_copied_into_model_input(lab):
    for rows in read_records(lab).values():
        for row in rows:
            user_input = prompt_messages(row)[1]["content"]
            assert row["provenance"]["family_id"] not in user_input
            assert row["id"] not in user_input


@pytest.mark.parametrize("mutation", [
    "duplicate-id", "duplicate-source", "family-leak", "holdout-child",
    "wrong-parent", "absent-gold", "unknown-type", "wrong-tsv", "omitted-gold",
])
def test_audit_rejects_semantic_tampering_even_after_rehash(lab, mutation):
    records = read_records(lab)
    train = records["train"]
    positive = next(row for row in train if row["entities"])
    canary = "PRIVATE_VALUE_MUST_NOT_APPEAR_IN_ERRORS"
    if mutation in {"duplicate-id", "duplicate-source"}:
        duplicate = copy.deepcopy(train[0])
        if mutation == "duplicate-source":
            duplicate["id"] = "different-id"
        train.append(duplicate)
    elif mutation == "family-leak":
        moved = next(row for row in train if row["provenance"]["augmentation"] == "base")
        train.remove(moved)
        moved["provenance"]["split"] = "validation"
        records["validation"].append(moved)
    elif mutation == "holdout-child":
        parent = records["validation"][0]
        child = copy.deepcopy(parent)
        child["id"] += ":child"
        child["source_text"] = "Extra context\n" + child["source_text"]
        child["provenance"].update(augmentation="context", parent_id=parent["id"])
        records["validation"].append(child)
    elif mutation == "wrong-parent":
        child = next(row for row in train if row["provenance"]["augmentation"] != "base")
        child["provenance"]["parent_id"] = records["test"][0]["id"]
    elif mutation == "absent-gold":
        positive["entities"][0]["original"] = canary
        positive["target_tsv"] = "\n".join(f"{x['type']}\t{x['original']}" for x in positive["entities"])
    elif mutation == "unknown-type":
        positive["entities"][0]["type"] = "SECRET"
        positive["target_tsv"] = "\n".join(f"{x['type']}\t{x['original']}" for x in positive["entities"])
    elif mutation == "wrong-tsv":
        positive["target_tsv"] = f"PERSON\t{canary}"
    else:
        positive["entities"] = []
        positive["target_tsv"] = ""
    rewrite_with_new_hashes(lab, records)
    result = cli("--audit-dir", lab)
    assert result.returncode != 0
    assert result.stdout == ""
    assert canary not in result.stderr
    expected_reason = {
        "duplicate-id": "duplicate record", "duplicate-source": "duplicate nfc source",
        "family-leak": "family split", "holdout-child": "train-only",
        "wrong-parent": "parent", "absent-gold": "source",
        "unknown-type": "entity type", "wrong-tsv": "tsv", "omitted-gold": "recipe",
    }[mutation]
    assert expected_reason in result.stderr.lower()


def test_hash_tampering_is_rejected(lab):
    path = lab / "train.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    result = cli("--audit-dir", lab)
    assert result.returncode != 0
    assert "hash" in result.stderr.lower()


@pytest.mark.parametrize("field,value", [
    ("seed", True), ("lab_version", "unsupported"), ("counts", {"train": 1}),
])
def test_manifest_tampering_is_rejected(lab, field, value):
    path = lab / "augmentation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest[field] = value
    path.write_text(json.dumps(manifest))
    assert cli("--audit-dir", lab).returncode != 0


def test_manifest_boolean_is_not_accepted_as_an_integer_count(lab):
    path = lab / "augmentation-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["augmented_records"]["test"] = False
    path.write_text(json.dumps(manifest))
    assert cli("--audit-dir", lab).returncode != 0


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_generation_refuses_existing_output_without_modifying_it(tmp_path, kind):
    target = tmp_path / "existing"
    if kind == "directory":
        target.mkdir()
        sentinel = target / "keep.txt"
    elif kind == "file":
        sentinel = target
    else:
        other = tmp_path / "other"
        other.mkdir()
        target.symlink_to(other, target_is_directory=True)
        sentinel = other / "keep.txt"
    sentinel.write_bytes(b"untouched")
    result = cli("--output-dir", target, "--seed", 42)
    assert result.returncode != 0
    assert sentinel.read_bytes() == b"untouched"


def test_legacy_generator_manifest_is_unchanged_by_lab(lab, tmp_path):
    paths = generate_dataset(tmp_path / "legacy")
    assert json.loads(paths["manifest"].read_text()) == json.loads(
        (ROOT / "data/dataset-manifest.json").read_text()
    )
