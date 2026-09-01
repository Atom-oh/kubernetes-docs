"""Deterministic synthetic PII dataset generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Optional

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "experiment.yaml"
GENERATOR_VERSION = "1.0.0"

DOMAINS = ("insurance", "mortgage", "creditcard", "brokerage", "support")
KO_NAMES = ("김가상", "이샘플", "박테스트", "최모형", "정예시")
EN_NAMES = (
    "Alex Example",
    "Taylor Sample",
    "Jordan Test",
    "Morgan Fiction",
    "Casey Model",
)
KO_RELATIONSHIPS = ("배우자", "자녀", "보호자", "부모")
EN_RELATIONSHIPS = ("spouse", "child", "guardian", "parent")


def luhn_valid(digits: str) -> bool:
    """Return whether ``digits`` passes the Luhn checksum."""
    if not digits.isdigit() or len(digits) < 2:
        return False
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def rrn_checksum_valid(digits: str) -> bool:
    """Return whether a 13-digit Korean RRN-shaped value passes checksum."""
    if not digits.isdigit() or len(digits) != 13:
        return False
    weights = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
    check = (11 - sum(int(d) * w for d, w in zip(digits[:12], weights))) % 10
    return check == int(digits[-1])


def _force_invalid_luhn(digits: str) -> str:
    if not luhn_valid(digits):
        return digits
    replacement = str((int(digits[-1]) + 1) % 10)
    candidate = f"{digits[:-1]}{replacement}"
    if luhn_valid(candidate):
        replacement = str((int(replacement) + 1) % 10)
        candidate = f"{digits[:-1]}{replacement}"
    return candidate


def _force_invalid_rrn(digits: str) -> str:
    if not rrn_checksum_valid(digits):
        return digits
    replacement = str((int(digits[-1]) + 1) % 10)
    candidate = f"{digits[:-1]}{replacement}"
    if rrn_checksum_valid(candidate):
        replacement = str((int(replacement) + 1) % 10)
        candidate = f"{digits[:-1]}{replacement}"
    return candidate


def _synthetic_values(
    rng: random.Random, language: str, index: int
) -> dict[str, str]:
    if language == "ko":
        person = rng.choice(KO_NAMES)
        birth = rng.choice(("900101", "920215", "950731", "880909", "010305"))
        tail = f"{rng.choice((1, 2, 3, 4))}{rng.randrange(0, 1_000_000):06d}"
        rrn_digits = _force_invalid_rrn(f"{birth}{tail}")
        rrn = f"{rrn_digits[:6]}-{rrn_digits[6:]}"
        dob = f"19{birth[:2]}-{birth[2:4]}-{birth[4:6]}"
        phone = f"010-0000-{index % 10_000:04d}"
        email = f"synthetic.ko.{index}@example.com"
        address = (
            f"서울특별시 가상구 샘플대로 {100 + index % 800} "
            f"예시동 {1 + index % 50}호"
        )
        relationship = rng.choice(KO_RELATIONSHIPS)
    else:
        person = rng.choice(EN_NAMES)
        rrn = ""
        dob = f"19{70 + index % 25:02d}-{1 + index % 12:02d}-{1 + index % 28:02d}"
        phone = f"+1-555-01{index % 100:02d}"
        email = f"synthetic.en.{index}@example.com"
        address = (
            f"{100 + index % 800} Example Avenue, "
            f"Fiction City, ZZ {10_000 + index % 80_000:05d}"
        )
        relationship = rng.choice(EN_RELATIONSHIPS)

    account_digits = f"000{index % 1_000:03d}{rng.randrange(0, 1_000_000):06d}"
    account = f"{account_digits[:3]}-{account_digits[3:6]}-{account_digits[6:]}"
    card_digits = _force_invalid_luhn(
        f"9999{index % 10_000:04d}{rng.randrange(0, 100_000_000):08d}"
    )
    card = "-".join(card_digits[offset : offset + 4] for offset in range(0, 16, 4))

    return {
        "PERSON": person,
        "RRN": rrn,
        "DOB": dob,
        "REL": relationship,
        "ADDRESS": address,
        "PHONE": phone,
        "EMAIL": email,
        "ACCOUNT": account,
        "CARD": card,
    }


def _entity(entity_type: str, value: str) -> dict[str, str]:
    return {"type": entity_type, "original": value}


def _ko_record(
    values: dict[str, str], domain: str, index: int, pattern: int
) -> tuple[str, list[dict[str, str]]]:
    if pattern == 0:
        text = (
            f"[{domain} 신청서]\n"
            f"성명: {values['PERSON']}\n"
            f"주민등록번호: {values['RRN']}\n"
            f"생년월일: {values['DOB']}\n"
            f"관계: {values['REL']}\n"
            f"주소: {values['ADDRESS']}\n"
            f"연락처: {values['PHONE']}\n"
            f"이메일: {values['EMAIL']}\n"
            f"계좌번호: {values['ACCOUNT']}\n"
            f"카드번호: {values['CARD']}"
        )
        types = (
            "PERSON",
            "RRN",
            "DOB",
            "REL",
            "ADDRESS",
            "PHONE",
            "EMAIL",
            "ACCOUNT",
            "CARD",
        )
    elif pattern == 1:
        phone = values["PHONE"].replace("-", ".")
        text = (
            "| 구분 | 값 |\n"
            "|---|---|\n"
            f"| 고객명 | {values['PERSON']} |\n"
            f"| 주소 | {values['ADDRESS']} |\n"
            f"| 전화 | {phone} |\n"
            f"| 이메일 | {values['EMAIL']} |"
        )
        values = {**values, "PHONE": phone}
        types = ("PERSON", "ADDRESS", "PHONE", "EMAIL")
    elif pattern == 2:
        account = values["ACCOUNT"].replace("-", "")
        text = (
            f"상담 기록: {values['PERSON']} 고객이 {values['EMAIL']}에서 문의했습니다. "
            f"회신 번호는 {values['PHONE']}이고 환급 계좌는 {account}입니다."
        )
        values = {**values, "ACCOUNT": account}
        types = ("PERSON", "EMAIL", "PHONE", "ACCOUNT")
    elif pattern == 3:
        text = (
            f"가족 확인\n신청인 {values['PERSON']}\n"
            f"관계 {values['REL']}\n생년월일 {values['DOB']}"
        )
        types = ("PERSON", "REL", "DOB")
    elif pattern == 4:
        return (
            f"가상금융 문서번호 DOC-2026-{index:06d}, 대표전화 1588-0000, "
            "사업자등록번호 000-00-00000, 심사금액 4,000만원.",
            [],
        )
    else:
        spaced_name = " ".join(values["PERSON"])
        spaced_rrn = values["RRN"].replace("-", " - ")
        card = values["CARD"].replace("-", " ")
        address = unicodedata.normalize("NFD", values["ADDRESS"])
        text = (
            f"OCR 추출\n성 명\t{spaced_name}\n주민 번호\t{spaced_rrn}\n"
            f"주 소\t{address}\n카 드\t{card}"
        )
        values = {
            **values,
            "PERSON": spaced_name,
            "RRN": spaced_rrn,
            "ADDRESS": address,
            "CARD": card,
        }
        types = ("PERSON", "RRN", "ADDRESS", "CARD")
    return text, [_entity(entity_type, values[entity_type]) for entity_type in types]


def _en_record(
    values: dict[str, str], domain: str, index: int, pattern: int
) -> tuple[str, list[dict[str, str]]]:
    if pattern == 0:
        text = (
            f"[{domain} application]\n"
            f"Name: {values['PERSON']}\n"
            f"Date of birth: {values['DOB']}\n"
            f"Relationship: {values['REL']}\n"
            f"Address: {values['ADDRESS']}\n"
            f"Phone: {values['PHONE']}\n"
            f"Email: {values['EMAIL']}\n"
            f"Account: {values['ACCOUNT']}\n"
            f"Card: {values['CARD']}"
        )
        types = (
            "PERSON",
            "DOB",
            "REL",
            "ADDRESS",
            "PHONE",
            "EMAIL",
            "ACCOUNT",
            "CARD",
        )
    elif pattern == 1:
        text = (
            "| field | value |\n"
            "|---|---|\n"
            f"| customer | {values['PERSON']} |\n"
            f"| address | {values['ADDRESS']} |\n"
            f"| phone | {values['PHONE']} |\n"
            f"| email | {values['EMAIL']} |"
        )
        types = ("PERSON", "ADDRESS", "PHONE", "EMAIL")
    elif pattern == 2:
        account = values["ACCOUNT"].replace("-", "")
        text = (
            f"Support note: {values['PERSON']} contacted us from {values['EMAIL']}. "
            f"Call {values['PHONE']} and refund account {account}."
        )
        values = {**values, "ACCOUNT": account}
        types = ("PERSON", "EMAIL", "PHONE", "ACCOUNT")
    elif pattern == 3:
        text = (
            f"Household record\nApplicant {values['PERSON']}\n"
            f"Relationship {values['REL']}\nDate of birth {values['DOB']}"
        )
        types = ("PERSON", "REL", "DOB")
    elif pattern == 4:
        return (
            f"Example Finance document DOC-2026-{index:06d}; "
            "company switchboard +1-555-0100; amount USD 40,000.",
            [],
        )
    else:
        card = values["CARD"].replace("-", " ")
        text = (
            f"OCR extract\nNAME\t{values['PERSON']}\n"
            f"ADDRESS\t{values['ADDRESS']}\nCARD\t{card}"
        )
        values = {**values, "CARD": card}
        types = ("PERSON", "ADDRESS", "CARD")
    return text, [_entity(entity_type, values[entity_type]) for entity_type in types]


def build_record(
    rng: random.Random, language: str, domain: str, index: int
) -> dict:
    """Build one synthetic record with source-order entity annotations."""
    if language not in {"ko", "en"}:
        raise ValueError(f"unsupported language: {language}")
    values = _synthetic_values(rng, language, index)
    pattern = index % 6
    if language == "ko":
        source_text, entities = _ko_record(values, domain, index, pattern)
    else:
        source_text, entities = _en_record(values, domain, index, pattern)
    return {
        "id": f"{language}-{domain}-{index:06d}",
        "language": language,
        "domain": domain,
        "source_text": source_text,
        "entities": entities,
        "target_tsv": "\n".join(
            f"{entity['type']}\t{entity['original']}" for entity in entities
        ),
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    content = "".join(
        f"{json.dumps(record, ensure_ascii=False, sort_keys=True)}\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")


def _language_counts(records: list[dict]) -> dict[str, int]:
    counts = Counter(record["language"] for record in records)
    return {"ko": counts["ko"], "en": counts["en"]}


def _type_counts(records: list[dict]) -> dict[str, int]:
    counts = Counter(
        entity["type"] for record in records for entity in record["entities"]
    )
    return dict(sorted(counts.items()))


def _review_sample(records: list[dict]) -> list[dict]:
    coverage: Counter[tuple[str, str]] = Counter()
    selected: list[dict] = []
    selected_ids: set[str] = set()
    for record in records:
        keys = {
            (record["language"], entity["type"])
            for entity in record["entities"]
        }
        if not keys:
            continue
        if any(coverage[key] < 2 for key in keys):
            if record["id"] not in selected_ids:
                selected.append(record)
                selected_ids.add(record["id"])
            for key in keys:
                if coverage[key] < 2:
                    coverage[key] += 1
    return selected


def generate_dataset(
    output_dir: Path, config_path: Optional[Path] = None
) -> dict[str, Path]:
    """Generate all splits plus manifest and human-review sample."""
    config_file = Path(config_path) if config_path else DEFAULT_CONFIG
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    rng = random.Random(config["seed"])
    split_offsets = {"train": 0, "validation": 100_000, "test": 200_000}
    split_records: dict[str, list[dict]] = {}
    paths: dict[str, Path] = {}

    for split in ("train", "validation", "test"):
        count = int(config["dataset"][split])
        ko_count = int(count * float(config["languages"]["ko"]))
        language_sequence = ["ko"] * ko_count + ["en"] * (count - ko_count)
        records = []
        for position, language in enumerate(language_sequence):
            index = split_offsets[split] + position
            domain = DOMAINS[index % len(DOMAINS)]
            records.append(build_record(rng, language, domain, index))
        rng.shuffle(records)
        split_records[split] = records
        split_path = output / f"{split}.jsonl"
        _write_jsonl(split_path, records)
        paths[split] = split_path

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": config["seed"],
        "counts": {
            split: len(records) for split, records in split_records.items()
        },
        "languages": {
            split: _language_counts(records)
            for split, records in split_records.items()
        },
        "entity_types": {
            split: _type_counts(records)
            for split, records in split_records.items()
        },
        "sha256": {
            split: hashlib.sha256(paths[split].read_bytes()).hexdigest()
            for split in ("train", "validation", "test")
        },
    }
    manifest_path = output / "dataset-manifest.json"
    manifest_path.write_text(
        f"{json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    paths["manifest"] = manifest_path

    all_records = [
        record
        for split in ("train", "validation", "test")
        for record in split_records[split]
    ]
    review_path = output / "review-sample.jsonl"
    _write_jsonl(review_path, _review_sample(all_records))
    paths["review_sample"] = review_path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    generated = generate_dataset(args.output_dir, args.config)
    summary = {name: str(path) for name, path in sorted(generated.items())}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
