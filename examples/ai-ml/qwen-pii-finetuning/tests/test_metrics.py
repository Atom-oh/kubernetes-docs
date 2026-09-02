from decimal import Decimal

from src.metrics import compute_cost, evaluate_predictions, score_entities
from src.pii_tokens import Entity


def test_entity_metrics_use_exact_normalized_pairs():
    expected = [Entity("PERSON", "김민수"), Entity("PHONE", "010-1234-5678")]
    predicted = [
        Entity("PERSON", "김민수"),
        Entity("EMAIL", "kim@example.com"),
    ]

    metrics = score_entities(expected, predicted)

    assert metrics.tp == 1
    assert metrics.fp == 1
    assert metrics.fn == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5


def test_cost_uses_decimal_and_seconds():
    assert compute_cost(7200, Decimal("4.6169375000")) == Decimal(
        "9.2338750000"
    )


def test_evaluation_separates_leaks_over_redaction_and_round_trip():
    records = [
        {
            "id": "doc-1",
            "source_text": "고객 김민수 전화 010-1234-5678",
            "entities": [
                {"type": "PERSON", "original": "김민수"},
                {"type": "PHONE", "original": "010-1234-5678"},
            ],
        },
        {
            "id": "doc-2",
            "source_text": "Example Finance 안내문",
            "entities": [],
        },
    ]
    predictions = [
        {"id": "doc-1", "content": "PERSON\t김민수", "parse_success": True},
        {
            "id": "doc-2",
            "content": "PERSON\tExample Finance",
            "parse_success": True,
        },
    ]

    summary = evaluate_predictions(records, predictions)

    assert summary["entity"]["tp"] == 1
    assert summary["entity"]["fp"] == 1
    assert summary["entity"]["fn"] == 1
    assert summary["documents"]["leaked"] == 1
    assert summary["entities"]["leaked"] == 1
    assert summary["entities"]["over_redacted"] == 1
    assert summary["parse"]["success"] == 2
    assert summary["tokenization"]["deterministic"] == 2
    assert summary["tokenization"]["round_trip"] == 2


def test_repeated_values_in_different_documents_count_as_separate_entities():
    records = [
        {
            "id": "doc-1",
            "source_text": "고객 김가상",
            "entities": [{"type": "PERSON", "original": "김가상"}],
        },
        {
            "id": "doc-2",
            "source_text": "고객 김가상",
            "entities": [{"type": "PERSON", "original": "김가상"}],
        },
    ]
    predictions = [
        {"id": "doc-1", "content": "PERSON\t김가상", "parse_success": True},
        {"id": "doc-2", "content": "", "parse_success": True},
    ]

    summary = evaluate_predictions(records, predictions)

    assert summary["entity"]["tp"] == 1
    assert summary["entity"]["fn"] == 1
    assert summary["entity"]["recall"] == 0.5
    assert summary["entities"]["expected"] == 2


def test_reasoning_block_rows_do_not_count_as_hallucinations():
    records = [
        {
            "id": "doc-1",
            "source_text": "고객 김가상",
            "entities": [{"type": "PERSON", "original": "김가상"}],
        }
    ]
    predictions = [
        {
            "id": "doc-1",
            "content": "<think>\nPERSON\t없는사람\n</think>\nPERSON\t김가상",
            "parse_success": True,
        }
    ]

    summary = evaluate_predictions(records, predictions)

    assert summary["entities"]["hallucinated"] == 0
