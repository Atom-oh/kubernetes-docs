"""Strict execution parsing and aggregate-only metrics; never persist completions."""

import unicodedata

from src.metrics import evaluate_predictions
from src.pii_tokens import VALID_TYPES, parse_tsv


def strict_parse_success(content: str, source_text: str, terminated: bool) -> bool:
    """Reject the entire answer on malformed rows, prose, or invented spellings.

    EOS is required even for an empty negative answer. NFC normalization matches
    the historical evaluator, but numeric spelling variants are not accepted.
    This validates format/source grounding, not correctness of semantic labels.
    """
    if not terminated or not isinstance(content, str):
        return False
    if not content.strip():
        return True
    source = unicodedata.normalize("NFC", source_text)
    seen = set()
    for line in content.splitlines():
        if line.count("\t") != 1:
            return False
        kind, value = line.split("\t")
        value = unicodedata.normalize("NFC", value)
        if kind not in VALID_TYPES or not value or value != value.strip():
            return False
        pair = (kind, value)
        if pair in seen or value not in source:
            return False
        # Also retain the historical numeric-boundary rule.
        if len(parse_tsv(line, source)) != 1:
            return False
        seen.add(pair)
    return True


def aggregate_predictions(records: list[dict], predictions: list[dict]) -> dict:
    """Preserve the historical all-or-none scores and add safe subgroup counts."""
    result = evaluate_predictions(records, predictions)
    by_id = {prediction["id"]: prediction for prediction in predictions}

    def subgroup(selected):
        return evaluate_predictions(
            selected, [by_id[row["id"]] for row in selected if row["id"] in by_id]
        )

    result["generation"] = {
        "total": len(predictions),
        "missing_eos": sum(not row.get("terminated", False) for row in predictions),
    }
    result["subgroups"] = {
        "language": {
            language: subgroup([row for row in records if row.get("language") == language])
            for language in ("ko", "en")
        },
        "negative": subgroup([row for row in records if not row["entities"]]),
        "positive": subgroup([row for row in records if row["entities"]]),
    }
    return result
