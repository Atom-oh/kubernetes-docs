"""Dataset loading helpers for Qwen PII fine-tuning."""

import json
from pathlib import Path


SYSTEM_INSTRUCTION = (
    "Extract personally identifiable information from the document. "
    "Return zero or more lines in the exact format TYPE<TAB>ORIGINAL. "
    "Allowed TYPE values are PERSON, RRN, DOB, REL, ADDRESS, PHONE, EMAIL, "
    "ACCOUNT, and CARD. Copy ORIGINAL exactly from the document. "
    "Do not add prose, JSON, Markdown, or explanations."
)


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line
    ]


def prompt_messages(record: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": record["source_text"]},
    ]


def completion_messages(record: dict) -> list[dict[str, str]]:
    return [{"role": "assistant", "content": record["target_tsv"]}]


def load_sft_dataset(path: Path):
    """Load a conversational prompt-completion dataset lazily."""
    from datasets import Dataset

    rows = [
        {
            "prompt": prompt_messages(record),
            "completion": completion_messages(record),
        }
        for record in read_jsonl(path)
    ]
    return Dataset.from_list(rows)
