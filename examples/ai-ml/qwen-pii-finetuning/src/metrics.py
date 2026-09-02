"""Deterministic PII extraction, leakage, and cost metrics."""

import unicodedata
from dataclasses import asdict
from dataclasses import dataclass
from decimal import Decimal

from src.pii_tokens import (
    THINK_PATTERN,
    VALID_TYPES,
    Entity,
    parse_tsv,
    pseudonymize_text,
    reassemble_text,
)


@dataclass(frozen=True)
class EntityMetrics:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


def _pair(entity: Entity) -> tuple[str, str]:
    return (
        entity.type.strip().upper(),
        unicodedata.normalize("NFC", entity.original.strip()),
    )


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _metrics_from_counts(tp: int, fp: int, fn: int) -> EntityMetrics:
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return EntityMetrics(tp, fp, fn, precision, recall, f1)


def score_entities(
    expected: list[Entity], predicted: list[Entity]
) -> EntityMetrics:
    expected_pairs = {_pair(entity) for entity in expected}
    predicted_pairs = {_pair(entity) for entity in predicted}
    tp = len(expected_pairs & predicted_pairs)
    fp = len(predicted_pairs - expected_pairs)
    fn = len(expected_pairs - predicted_pairs)
    return _metrics_from_counts(tp, fp, fn)


def compute_cost(duration_seconds: float, hourly_usd: Decimal) -> Decimal:
    return Decimal(str(duration_seconds)) * hourly_usd / Decimal("3600")


def _entities_from_record(record: dict) -> list[Entity]:
    return [
        Entity(item["type"], item["original"])
        for item in record.get("entities", [])
    ]


def _raw_whitelisted_rows(content: str) -> list[Entity]:
    rows: list[Entity] = []
    clean = THINK_PATTERN.sub("", content)
    for line in clean.splitlines():
        if "\t" not in line:
            continue
        raw_type, raw_value = line.split("\t", 1)
        entity_type = raw_type.strip().upper()
        original = unicodedata.normalize("NFC", raw_value.strip())
        if entity_type in VALID_TYPES and original:
            rows.append(Entity(entity_type, original))
    return rows


def evaluate_predictions(records: list[dict], predictions: list[dict]) -> dict:
    """Evaluate predictions without returning source text or entity values."""
    predictions_by_id = {prediction["id"]: prediction for prediction in predictions}
    overall_counts = {"tp": 0, "fp": 0, "fn": 0}
    per_type_counts: dict[str, dict[str, int]] = {}

    parse_success = 0
    leaked_documents = 0
    leaked_entities = 0
    over_redacted = 0
    hallucinated = 0
    deterministic = 0
    round_trip = 0
    expected_entity_count = 0
    predicted_entity_count = 0

    for record in records:
        prediction = predictions_by_id.get(
            record["id"],
            {"id": record["id"], "content": "", "parse_success": False},
        )
        source = unicodedata.normalize("NFC", record["source_text"])
        expected = _entities_from_record(record)
        content = prediction.get("content", "")
        succeeded = bool(prediction.get("parse_success"))
        if succeeded:
            parse_success += 1
            predicted = parse_tsv(content, source)
        else:
            predicted = []

        raw_rows = _raw_whitelisted_rows(content)
        parsed_pairs = {_pair(entity) for entity in predicted}
        hallucinated += sum(
            1 for entity in raw_rows if _pair(entity) not in parsed_pairs
        )

        document_metrics = score_entities(expected, predicted)
        for field in overall_counts:
            overall_counts[field] += getattr(document_metrics, field)

        expected_pairs = {_pair(entity) for entity in expected}
        predicted_pairs = {_pair(entity) for entity in predicted}
        expected_entity_count += len(expected_pairs)
        predicted_entity_count += len(predicted_pairs)
        for entity_type in {
            entity_type for entity_type, _original in expected_pairs | predicted_pairs
        }:
            expected_for_type = [
                entity for entity in expected if entity.type == entity_type
            ]
            predicted_for_type = [
                entity for entity in predicted if entity.type == entity_type
            ]
            type_metrics = score_entities(expected_for_type, predicted_for_type)
            counts = per_type_counts.setdefault(
                entity_type, {"tp": 0, "fp": 0, "fn": 0}
            )
            for field in counts:
                counts[field] += getattr(type_metrics, field)

        tokenized = pseudonymize_text(source, predicted)
        reversed_tokenized = pseudonymize_text(source, list(reversed(predicted)))
        if tokenized == reversed_tokenized:
            deterministic += 1
        if reassemble_text(tokenized.masked_text, tokenized.mapping) == source:
            round_trip += 1

        document_leaks = 0
        for entity in expected:
            original = unicodedata.normalize("NFC", entity.original)
            if original and original in tokenized.masked_text:
                leaked_entities += 1
                document_leaks += 1
        if document_leaks:
            leaked_documents += 1

        over_redacted += sum(
            1 for entity in predicted if _pair(entity) not in expected_pairs
        )

    overall = _metrics_from_counts(**overall_counts)
    per_type = {
        entity_type: asdict(_metrics_from_counts(**counts))
        for entity_type, counts in sorted(per_type_counts.items())
    }

    total_documents = len(records)
    return {
        "entity": asdict(overall),
        "per_type": per_type,
        "documents": {
            "total": total_documents,
            "leaked": leaked_documents,
            "leak_rate": _rate(leaked_documents, total_documents),
        },
        "entities": {
            "expected": expected_entity_count,
            "predicted": predicted_entity_count,
            "leaked": leaked_entities,
            "leak_rate": _rate(leaked_entities, expected_entity_count),
            "over_redacted": over_redacted,
            "over_redaction_rate": _rate(over_redacted, predicted_entity_count),
            "hallucinated": hallucinated,
            "hallucination_rate": _rate(hallucinated, len(_raw_rows(predictions))),
        },
        "parse": {
            "total": total_documents,
            "success": parse_success,
            "success_rate": _rate(parse_success, total_documents),
        },
        "tokenization": {
            "total": total_documents,
            "deterministic": deterministic,
            "deterministic_rate": _rate(deterministic, total_documents),
            "round_trip": round_trip,
            "round_trip_rate": _rate(round_trip, total_documents),
        },
    }


def _raw_rows(predictions: list[dict]) -> list[Entity]:
    return [
        entity
        for prediction in predictions
        for entity in _raw_whitelisted_rows(prediction.get("content", ""))
    ]
