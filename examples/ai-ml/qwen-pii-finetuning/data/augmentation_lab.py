"""Small synthetic CPU exercise: split families first, augment train only.

This lab is separate from generator 1.0.0. Names/templates intentionally repeat
between families; family separation is not entity or template independence.
Phone values are placeholders, not validated reserved or unassigned numbers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import unicodedata
from pathlib import Path

from src.pii_tokens import VALID_TYPES


LAB_VERSION = "1.0.0"
SPLITS = ("train", "validation", "test")
AUGMENTATIONS = ("base", "context", "layout_unicode")


class LabError(ValueError):
    """An audit reason containing only a fixed, non-sensitive message."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        # Never include source text, entity values or caller-supplied IDs.
        raise LabError(message)


def _family_plan(seed: int) -> dict[str, tuple[str, str, int, str]]:
    """Assign unaugmented family identities before any descendants exist."""
    rng = random.Random(seed)
    plan = {}
    for language in ("ko", "en"):
        for kind in ("positive", "negative"):
            indices = list(range(10))
            rng.shuffle(indices)
            for position, index in enumerate(indices):
                split = "train" if position < 6 else "validation" if position < 8 else "test"
                family = f"{language}-{kind}-{index:02d}"
                plan[family] = (language, kind, index, split)
    return plan


def _record(family: str, identity: tuple[str, str, int, str], augmentation: str) -> dict:
    """Render source and gold labels together; never paraphrase gold blindly."""
    language, kind, index, split = identity
    korean = language == "ko"
    # Family IDs describe polarity; do not hand that metadata to the model.
    reference = hashlib.sha256(family.encode("utf-8")).hexdigest()[:16]
    fields = [("문서번호" if korean else "Document", f"DOC-{reference}", None)]
    if kind == "positive":
        person = ("김가상", "이샘플")[index % 2] if korean else ("Alex Example", "Taylor Sample")[index % 2]
        phone = f"010-0000-{index:04d}" if korean else f"+1-555-01{index:02d}"
        fields += [
            ("성명" if korean else "Name", person, "PERSON"),
            ("이메일" if korean else "Email", f"synthetic.{reference}@example.com", "EMAIL"),
            ("전화" if korean else "Phone", phone, "PHONE"),
        ]
    else:
        # The lab's policy excludes these fictional organization/reference fields.
        fields += [
            ("기관" if korean else "Organization", "Example Support", None),
            ("대표번호" if korean else "Switchboard", "1588-0000" if korean else "+1-555-0100", None),
            ("금액" if korean else "Amount", "1,000", None),
        ]
    title = "합성 지원 문서" if korean else "Synthetic support document"
    separator = ": "
    if augmentation == "context":
        title = ("참고: 고객 자료가 아닌 합성 실습입니다.\n" if korean else
                 "Note: a synthetic exercise, not customer data.\n") + title
    elif augmentation == "layout_unicode":
        title = ("목록 형식\n" if korean else "List format\n") + title
        fields = list(reversed(fields))
        separator = " = "
    source = "\n".join([title, *(label + separator + value for label, value, _ in fields)])
    entities = [{"type": entity_type, "original": value}
                for _, value, entity_type in fields if entity_type]
    if korean and augmentation == "layout_unicode":
        source = unicodedata.normalize("NFD", source)
        entities = [{"type": e["type"], "original": unicodedata.normalize("NFD", e["original"])}
                    for e in entities]
    return {
        "id": f"{family}:{augmentation}", "language": language, "domain": "support",
        "source_text": source, "entities": entities,
        "target_tsv": "\n".join(f"{e['type']}\t{e['original']}" for e in entities),
        "provenance": {
            "family_id": family, "kind": kind, "split": split,
            "augmentation": augmentation,
            "parent_id": None if augmentation == "base" else f"{family}:base",
        },
    }


def _manifest(records: dict[str, list[dict]], seed: int, hashes: dict[str, str]) -> dict:
    return {
        "lab_version": LAB_VERSION, "seed": seed,
        "counts": {s: len(records[s]) for s in SPLITS},
        "families": {s: len({r["provenance"]["family_id"] for r in records[s]}) for s in SPLITS},
        "negative_records": {s: sum(r["provenance"]["kind"] == "negative" for r in records[s]) for s in SPLITS},
        "augmented_records": {s: sum(r["provenance"]["augmentation"] != "base" for r in records[s]) for s in SPLITS},
        "entity_types": ["EMAIL", "PERSON", "PHONE"],
        "sha256": hashes,
        "guarantees": {
            "family_disjoint": True, "exact_nfc_source_disjoint": True,
            "train_only_augmentation": True,
            "entity_disjoint": False, "template_disjoint": False,
        },
        "scope": "Synthetic CPU data exercise; shared entity values/templates; no model-quality or privacy guarantee.",
    }


def generate_lab(output_dir: Path, seed: int = 42) -> dict:
    _require(type(seed) is int, "seed must be an integer")
    plan = _family_plan(seed)
    records = {s: [] for s in SPLITS}
    for family, identity in sorted(plan.items()):
        split = identity[3]
        variants = AUGMENTATIONS if split == "train" else ("base",)
        records[split].extend(_record(family, identity, variant) for variant in variants)

    output = Path(output_dir)
    # exist_ok=False also refuses existing empty directories, files and symlinks.
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    hashes = {}
    for split, rows in records.items():
        content = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
        file = output / f"{split}.jsonl"
        file.write_text(content, encoding="utf-8")
        hashes[split] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest = _manifest(records, seed, hashes)
    (output / "augmentation-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return audit_lab(output)


def audit_lab(directory: Path) -> dict:
    """Check this versioned demo, including rehashed semantic tampering.

    Hashes alone do not authenticate a producer. This audit also checks the
    deterministic family recipe; it is not a general real-PII annotation judge.
    """
    directory = Path(directory)
    manifest = json.loads((directory / "augmentation-manifest.json").read_text(encoding="utf-8"))
    _require(isinstance(manifest, dict), "invalid manifest")
    _require(manifest.get("lab_version") == LAB_VERSION, "unsupported lab version")
    seed = manifest.get("seed")
    _require(type(seed) is int, "invalid manifest seed")
    declared_hashes = manifest.get("sha256")
    _require(isinstance(declared_hashes, dict) and set(declared_hashes) == set(SPLITS), "invalid hash manifest")
    plan = _family_plan(seed)
    expected_ids = {
        f"{family}:{variant}"
        for family, identity in plan.items()
        for variant in (AUGMENTATIONS if identity[3] == "train" else ("base",))
    }
    seen_ids, seen_sources, family_splits = set(), set(), {}
    records, hashes = {}, {}
    for split in SPLITS:
        content = (directory / f"{split}.jsonl").read_bytes()
        hashes[split] = hashlib.sha256(content).hexdigest()
        _require(hashes[split] == declared_hashes[split], "split file hash mismatch")
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
        records[split] = rows
        for row in rows:
            _require(isinstance(row, dict), "invalid record")
            identifier, source = row.get("id"), row.get("source_text")
            _require(isinstance(identifier, str) and identifier, "invalid record ID")
            _require(identifier not in seen_ids, "duplicate record ID")
            seen_ids.add(identifier)
            _require(isinstance(source, str) and source, "invalid source text")
            source_hash = hashlib.sha256(unicodedata.normalize("NFC", source).encode("utf-8")).hexdigest()
            _require(source_hash not in seen_sources, "duplicate NFC source")
            seen_sources.add(source_hash)

            provenance = row.get("provenance")
            _require(isinstance(provenance, dict), "invalid provenance")
            family = provenance.get("family_id")
            _require(isinstance(family, str) and family in plan, "unknown family")
            _require(provenance.get("split") == split == plan[family][3], "family split mismatch")
            _require(family_splits.setdefault(family, split) == split, "family leakage")
            variant = provenance.get("augmentation")
            _require(variant in AUGMENTATIONS, "unknown augmentation")
            _require(split == "train" or variant == "base", "augmentation is train-only")
            expected_parent = None if variant == "base" else f"{family}:base"
            _require(provenance.get("parent_id") == expected_parent, "parent family mismatch")

            entities = row.get("entities")
            _require(isinstance(entities, list), "invalid labels")
            pairs, positions = set(), []
            for entity in entities:
                _require(isinstance(entity, dict) and set(entity) == {"type", "original"}, "invalid label shape")
                kind, original = entity["type"], entity["original"]
                _require(isinstance(kind, str) and kind in VALID_TYPES, "unknown entity type")
                _require(isinstance(original, str) and original and not any(c in original for c in "\t\r\n"), "invalid label value")
                _require(original in source, "label does not occur in source")
                _require((kind, original) not in pairs, "duplicate label")
                pairs.add((kind, original))
                positions.append(source.index(original))
            _require(positions == sorted(positions), "labels must follow source order")
            target = "\n".join(f"{e['type']}\t{e['original']}" for e in entities)
            _require(row.get("target_tsv") == target, "TSV does not match labels")
            _require(row == _record(family, plan[family], variant), "record differs from the deterministic family recipe")

    _require(seen_ids == expected_ids, "missing or unexpected family records")
    expected_manifest = _manifest(records, seed, hashes)
    # JSON comparison distinguishes false/0 and true/1 unlike Python equality.
    _require(
        json.dumps(manifest, sort_keys=True) == json.dumps(expected_manifest, sort_keys=True),
        "manifest counts or policy mismatch",
    )
    return {"status": "passed", **expected_manifest}


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
            audit_lab(args.audit_dir) if args.audit_dir is not None else
            generate_lab(args.output_dir, 42 if args.seed is None else args.seed)
        )
    except FileExistsError:
        parser.error("output directory already exists; choose a new path")
    except LabError as error:
        parser.error(str(error))
    except (ValueError, KeyError, TypeError, UnicodeError):
        parser.error("lab validation failed; source values are not included in errors")
    except OSError:
        parser.error("lab I/O failed; inspect the selected directory")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
