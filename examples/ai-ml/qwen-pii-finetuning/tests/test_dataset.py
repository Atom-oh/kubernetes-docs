import hashlib
import json
from pathlib import Path

from data.generate_dataset import generate_dataset, luhn_valid, rrn_checksum_valid


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_generator_is_deterministic_and_split_safe(tmp_path):
    first = generate_dataset(tmp_path / "first")
    second = generate_dataset(tmp_path / "second")

    for split in ("train", "validation", "test"):
        assert first[split].read_bytes() == second[split].read_bytes()

    train = read_jsonl(first["train"])
    validation = read_jsonl(first["validation"])
    test = read_jsonl(first["test"])

    assert (len(train), len(validation), len(test)) == (1600, 200, 400)
    assert len({r["id"] for r in train} & {r["id"] for r in validation}) == 0
    assert len({r["id"] for r in train} & {r["id"] for r in test}) == 0
    assert len({r["id"] for r in validation} & {r["id"] for r in test}) == 0
    assert sum(r["language"] == "ko" for r in train) == 1280
    assert sum(r["language"] == "en" for r in train) == 320
    assert sum(r["language"] == "ko" for r in validation) == 160
    assert sum(r["language"] == "en" for r in validation) == 40
    assert sum(r["language"] == "ko" for r in test) == 320
    assert sum(r["language"] == "en" for r in test) == 80


def test_identifiers_are_deliberately_invalid(tmp_path):
    paths = generate_dataset(tmp_path)

    for split in ("train", "validation", "test"):
        for record in read_jsonl(paths[split]):
            for entity in record["entities"]:
                digits = "".join(ch for ch in entity["original"] if ch.isdigit())
                if entity["type"] == "RRN":
                    assert not rrn_checksum_valid(digits)
                if entity["type"] == "CARD":
                    assert not luhn_valid(digits)


def test_manifest_hashes_and_targets_match_generated_files(tmp_path):
    paths = generate_dataset(tmp_path)
    manifest = json.loads(paths["manifest"].read_text())

    assert manifest["seed"] == 42
    assert manifest["counts"] == {"train": 1600, "validation": 200, "test": 400}

    for split in ("train", "validation", "test"):
        expected_hash = hashlib.sha256(paths[split].read_bytes()).hexdigest()
        assert manifest["sha256"][split] == expected_hash
        for record in read_jsonl(paths[split]):
            expected_rows = [
                f'{entity["type"]}\t{entity["original"]}'
                for entity in record["entities"]
            ]
            assert record["target_tsv"] == "\n".join(expected_rows)
