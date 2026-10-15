"""Build the separate synthetic corpus for the live Qwen PII experiment.

From the experiment directory:
    python -m data.execution_dataset --output-dir /new/runtime/dataset --seed 42
    python -m data.execution_dataset --audit-dir /new/runtime/dataset

The destination must be new. Historical datasets/configuration are never read
as inputs or overwritten. Families are deduplicated and assigned before any
train descendants are rendered. Eight hundred train families yield 1,600 rows;
200 validation and 400 test families retain only their base records.

This is synthetic, shared-template evaluation, not unseen-template or real-PII
validation. The audit checks the deterministic recipe, not arbitrary annotations.
Hashes provide reproducibility/integrity, not producer authentication. Runtime
JSONL contains source values; CLI output is limited to aggregate metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from data import generate_dataset as legacy
from src.pii_tokens import VALID_TYPES


GENERATOR_VERSION = "execution-1.0.0"
MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507"
SPLITS = ("train", "validation", "test")
LANGUAGES = ("ko", "en")
TEMPLATES = ("application", "table", "support_note", "household", "negative_reference", "ocr")
AUGMENTATIONS = ("base", "context", "layout_unicode")
MANIFEST_NAME = "dataset-manifest.json"
# Counts here are unaugmented families. Training alone has two rows per family.
FAMILY_COUNTS = {
    "ko": {"train": 640, "validation": 160, "test": 320},
    "en": {"train": 160, "validation": 40, "test": 80},
}
LIMITATIONS = [
    "Synthetic documents only; no real-PII accuracy, anonymity or privacy guarantee.",
    "Templates and a finite entity lexicon, including names and relationships, are shared across splits.",
    "Family and exact NFC source separation do not establish entity or template independence.",
    "Phone/account values are fictional placeholders, not verified reserved or unassigned identifiers.",
    "RRN and CARD values deliberately fail their checksums; this is not representative of all real identifiers.",
    "Organization switchboards, document references and amounts are excluded by the synthetic annotation policy.",
    "English RRN examples represent English-language forms for Korean residents.",
    "File and recipe hashes detect changes; they do not authenticate the producer.",
]


class ExecutionDatasetError(ValueError):
    """Fixed diagnostic without record IDs, source text or entity values."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ExecutionDatasetError(reason)


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_hash(source: str) -> str:
    return _sha256(unicodedata.normalize("NFC", source).encode("utf-8"))


def _jsonl(rows: list[dict]) -> bytes:
    return "".join(_json(row) + "\n" for row in rows).encode("utf-8")


def _base_record(seed: int, language: str, index: int) -> dict:
    """Reuse historical field/render mechanics with a broader birth-date pool.

    The old five Korean dates permit only 100 distinct household records.
    Vary dates before rendering instead of hiding duplicate content behind a
    unique document prefix. Render values and gold together, including NFD OCR.
    """
    rng = random.Random(_sha256(f"{seed}:{language}:{index}".encode("ascii")))
    values = legacy._synthetic_values(rng, language, index)
    birth = date(1960, 1, 1) + timedelta(days=rng.randrange(60 * 365))
    values["DOB"] = birth.isoformat()
    century = (1, 2) if birth.year < 2000 else (3, 4)
    rrn = legacy._force_invalid_rrn(
        f"{birth:%y%m%d}{rng.choice(century)}{rng.randrange(1_000_000):06d}"
    )
    values["RRN"] = f"{rrn[:6]}-{rrn[6:]}"
    domain, pattern = legacy.DOMAINS[index % len(legacy.DOMAINS)], index % 6
    renderer = legacy._ko_record if language == "ko" else legacy._en_record
    source, entities = renderer(values, domain, index, pattern)
    if language == "en" and pattern == 0:
        source += f"\nKorean resident ID: {values['RRN']}"
        entities.append({"type": "RRN", "original": values["RRN"]})
    return {
        "language": language, "domain": domain, "source_text": source,
        "entities": entities,
        "target_tsv": "\n".join(f"{e['type']}\t{e['original']}" for e in entities),
    }


def _quota(count: int, pattern: int) -> int:
    return count // len(TEMPLATES) + int(pattern < count % len(TEMPLATES))


def _family_plan(seed: int) -> dict[str, tuple[str, int, str]]:
    """Deduplicate unaugmented sources, then stratify by language/template.

    A family is one synthetic source instance plus all its eventual descendants.
    Shared names/templates alone are not asserted to be independent identities.
    """
    rng = random.Random(seed)
    plan: dict[str, tuple[str, int, str]] = {}
    seen: dict[str, str] = {}
    for language in LANGUAGES:
        for pattern in range(len(TEMPLATES)):
            quotas = {split: _quota(FAMILY_COUNTS[language][split], pattern) for split in SPLITS}
            needed = sum(quotas.values())
            candidates = []
            attempt = 0
            while len(candidates) < needed:
                _require(attempt < needed * 100, "insufficient unique source families")
                index = pattern + len(TEMPLATES) * attempt
                attempt += 1
                base = _base_record(seed, language, index)
                fingerprint = _source_hash(base["source_text"])
                labels = unicodedata.normalize("NFC", base["target_tsv"])
                if fingerprint in seen:
                    _require(seen[fingerprint] == labels, "source-label conflict")
                    continue
                seen[fingerprint] = labels
                candidates.append((f"family-{fingerprint}", index))
            rng.shuffle(candidates)
            position = 0
            for split in SPLITS:
                for family, index in candidates[position:position + quotas[split]]:
                    plan[family] = (language, index, split)
                position += quotas[split]
    return plan


def _variants(family: str, split: str) -> tuple[str, ...]:
    if split != "train":
        return ("base",)
    return ("base", AUGMENTATIONS[1 + int(family[-1], 16) % 2])


def _record(seed: int, family: str, identity: tuple[str, int, str], variant: str) -> dict:
    language, index, split = identity
    row = _base_record(seed, language, index)
    source, entities = row["source_text"], row["entities"]
    if variant == "context":
        source = (
            "업무 메모: 아래 문서의 정보를 확인하세요.\n" if language == "ko"
            else "Processing note: review the information in the document below.\n"
        ) + source
    elif variant == "layout_unicode":
        lines = source.splitlines()
        # Preserve table headings; reverse field reading order for OCR/forms.
        heading_lines = 2 if index % 6 == 1 else 1
        lines = lines[:heading_lines] + list(reversed(lines[heading_lines:]))
        title = "재배열된 문서" if language == "ko" else "Reformatted document"
        source = title + "\n" + "\n\n".join(lines).replace(": ", " = ")
        if language == "ko":
            source = unicodedata.normalize("NFD", source)
            entities = [
                {**e, "original": unicodedata.normalize("NFD", e["original"])}
                for e in entities
            ]
    entities = sorted(entities, key=lambda e: source.index(e["original"]))
    return {
        **row, "id": f"{family}:{variant}", "source_text": source,
        "entities": entities,
        "target_tsv": "\n".join(f"{e['type']}\t{e['original']}" for e in entities),
        "provenance": {
            "family_id": family, "split": split, "augmentation": variant,
            "parent_id": None if variant == "base" else f"{family}:base",
            "kind": "positive" if entities else "negative",
            "template": TEMPLATES[index % 6], "candidate_index": index,
            "base_source_nfc_sha256": family.removeprefix("family-"),
            "source_nfc_sha256": _source_hash(source),
        },
    }


def _validate_records(records: dict[str, list[dict]], seed: int, plan: dict) -> None:
    seen_ids, seen_sources, family_splits = set(), set(), {}
    expected_ids = {
        f"{family}:{variant}"
        for family, identity in plan.items()
        for variant in _variants(family, identity[2])
    }
    for split in SPLITS:
        for row in records[split]:
            _require(isinstance(row, dict), "invalid record")
            identifier, source = row.get("id"), row.get("source_text")
            _require(isinstance(identifier, str) and bool(identifier), "invalid record ID")
            _require(identifier not in seen_ids, "duplicate record ID")
            seen_ids.add(identifier)
            _require(isinstance(source, str) and bool(source), "invalid source text")
            fingerprint = _source_hash(source)
            _require(fingerprint not in seen_sources, "duplicate NFC source")
            seen_sources.add(fingerprint)
            provenance = row.get("provenance")
            _require(isinstance(provenance, dict), "invalid provenance")
            family, variant = provenance.get("family_id"), provenance.get("augmentation")
            _require(isinstance(family, str) and family in plan, "unknown family")
            _require(provenance.get("split") == split == plan[family][2], "family split mismatch")
            _require(family_splits.setdefault(family, split) == split, "family leakage")
            _require(isinstance(variant, str) and variant in AUGMENTATIONS, "unknown augmentation")
            _require(split == "train" or variant == "base", "augmentation is train-only")
            _require(variant in _variants(family, split), "unexpected family augmentation")
            parent = None if variant == "base" else f"{family}:base"
            _require(provenance.get("parent_id") == parent, "parent family mismatch")
            _require(provenance.get("source_nfc_sha256") == fingerprint, "source fingerprint mismatch")
            entities = row.get("entities")
            _require(isinstance(entities, list), "invalid labels")
            pairs, positions = set(), []
            for entity in entities:
                _require(isinstance(entity, dict) and set(entity) == {"type", "original"}, "invalid label shape")
                kind, value = entity["type"], entity["original"]
                _require(isinstance(kind, str) and kind in VALID_TYPES, "unknown entity type")
                _require(
                    isinstance(value, str) and bool(value) and not any(c in value for c in "\t\r\n"),
                    "invalid label value",
                )
                _require(value in source, "label does not occur in source")
                _require((kind, value) not in pairs, "duplicate label")
                pairs.add((kind, value))
                positions.append(source.index(value))
            _require(positions == sorted(positions), "labels must follow source order")
            target = "\n".join(f"{e['type']}\t{e['original']}" for e in entities)
            _require(row.get("target_tsv") == target, "TSV does not match labels")
            # Also detect omitted gold, wrong-but-whitelisted labels, or changes
            # to source and gold together after an attacker recomputes hashes.
            expected = _record(seed, family, plan[family], variant)
            _require(_json(row) == _json(expected), "record differs from deterministic family recipe")
        _require(
            records[split] == sorted(records[split], key=lambda r: r["id"]),
            "noncanonical record order",
        )
        for language in LANGUAGES:
            labels = {
                e["type"] for row in records[split] if row["language"] == language
                for e in row["entities"]
            }
            _require(labels == VALID_TYPES, "incomplete nine-label language coverage")
    _require(seen_ids == expected_ids, "missing or unexpected family records")


def _manifest(records: dict[str, list[dict]], seed: int, hashes: dict, plan: dict) -> dict:
    files = {
        "data/execution_dataset.py": Path(__file__),
        "data/generate_dataset.py": Path(legacy.__file__),
    }
    return {
        "generator_version": GENERATOR_VERSION, "model_id": MODEL_ID, "seed": seed,
        "counts": {s: len(records[s]) for s in SPLITS},
        "families": {s: sum(identity[2] == s for identity in plan.values()) for s in SPLITS},
        "languages": {s: dict(sorted(Counter(r["language"] for r in records[s]).items())) for s in SPLITS},
        "entity_types": {
            s: dict(sorted(Counter(e["type"] for r in records[s] for e in r["entities"]).items()))
            for s in SPLITS
        },
        "negative_records": {s: sum(not r["entities"] for r in records[s]) for s in SPLITS},
        "augmented_records": {
            s: sum(r["provenance"]["augmentation"] != "base" for r in records[s]) for s in SPLITS
        },
        "templates": {
            s: dict(sorted(Counter(r["provenance"]["template"] for r in records[s]).items())) for s in SPLITS
        },
        "sha256": hashes,
        "source_files_sha256": {name: _sha256(path.read_bytes()) for name, path in files.items()},
        "family_assignment_sha256": _sha256(
            _json({family: identity[2] for family, identity in plan.items()}).encode("utf-8")
        ),
        "guarantees": {
            "family_disjoint": True, "exact_nfc_source_disjoint": True,
            "source_label_consistent": True, "train_only_augmentation": True,
            "entity_disjoint": False, "template_disjoint": False,
        },
        "split_policy": "Deduplicate base NFC sources; stratify families by language and template; augment train only.",
        "schema": {
            "training_fields": ["id", "source_text", "target_tsv", "entities"],
            "metadata_fields": ["language", "domain", "provenance"],
            "prompt_fields": ["source_text"],
        },
        "limitations": LIMITATIONS,
    }


def generate_execution_dataset(output_dir: Path, seed: int = 42) -> dict:
    """Write three splits and dataset-manifest.json; return aggregate audit."""
    _require(type(seed) is int, "seed must be an integer")
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise FileExistsError("output directory already exists")
    plan = _family_plan(seed)
    records = {split: [] for split in SPLITS}
    for family, identity in sorted(plan.items()):
        split = identity[2]
        records[split].extend(_record(seed, family, identity, v) for v in _variants(family, split))
    for rows in records.values():
        rows.sort(key=lambda row: row["id"])
    _validate_records(records, seed, plan)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    hashes = {}
    for split, rows in records.items():
        content = _jsonl(rows)
        (output / f"{split}.jsonl").write_bytes(content)
        hashes[split] = _sha256(content)
    manifest = _manifest(records, seed, hashes, plan)
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return audit_execution_dataset(output)


def audit_execution_dataset(directory: Path) -> dict:
    """Validate local bytes, separation, provenance and the full seeded recipe."""
    directory = Path(directory)
    manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    _require(isinstance(manifest, dict), "invalid manifest")
    _require(manifest.get("generator_version") == GENERATOR_VERSION, "unsupported generator version")
    seed = manifest.get("seed")
    _require(type(seed) is int, "invalid manifest seed")
    declared_hashes = manifest.get("sha256")
    _require(isinstance(declared_hashes, dict) and set(declared_hashes) == set(SPLITS), "invalid hash manifest")
    records, hashes = {}, {}
    for split in SPLITS:
        content = (directory / f"{split}.jsonl").read_bytes()
        hashes[split] = _sha256(content)
        _require(hashes[split] == declared_hashes[split], "split file hash mismatch")
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
        _require(content == _jsonl(rows), "split serialization mismatch")
        records[split] = rows
    plan = _family_plan(seed)
    _validate_records(records, seed, plan)
    expected = _manifest(records, seed, hashes, plan)
    # JSON equality also distinguishes booleans from integer counts.
    _require(_json(manifest) == _json(expected), "manifest counts, source files or policy mismatch")
    return {"status": "passed", **expected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output-dir", type=Path)
    mode.add_argument("--audit-dir", type=Path)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.audit_dir is not None and args.seed is not None:
        parser.error("audit uses the recorded manifest seed")
    try:
        summary = (
            audit_execution_dataset(args.audit_dir) if args.audit_dir is not None else
            generate_execution_dataset(args.output_dir, 42 if args.seed is None else args.seed)
        )
    except FileExistsError:
        parser.error("output directory already exists; choose a new path")
    except ExecutionDatasetError as error:
        parser.error(str(error))
    except (ValueError, KeyError, TypeError, UnicodeError):
        parser.error("dataset validation failed; source values are not included in errors")
    except OSError:
        parser.error("dataset I/O failed; inspect the selected directory")
    print(_json(summary))


if __name__ == "__main__":
    main()
