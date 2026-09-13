from decimal import Decimal
import pytest

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


def test_partial_redaction_does_not_hide_a_gold_entity_leak():
    records = [{
        "id": "r",
        "source_text": "Alpha Beta",
        "entities": [{"type": "PERSON", "original": "Alpha Beta"}],
    }]
    result = evaluate_predictions(records, [
        {"id": "r", "content": "PERSON\tAlpha", "parse_success": True},
    ])
    assert result["entities"]["leaked"] == 1
    assert result["documents"]["leak_rate"] == 1


def test_generated_token_text_is_not_counted_as_unmasked_source():
    records = [{
        "id": "r",
        "source_text": "PERSON",
        "entities": [{"type": "PERSON", "original": "PERSON"}],
    }]
    result = evaluate_predictions(records, [
        {"id": "r", "content": "PERSON\tPERSON", "parse_success": True},
    ])
    assert result["entities"]["leaked"] == 0


def test_repeated_gold_pairs_do_not_produce_a_leak_rate_over_one():
    records = [{
        "id": "r",
        "source_text": "Alice Alice",
        "entities": [{"type": "PERSON", "original": "Alice"}] * 2,
    }]
    result = evaluate_predictions(records, [
        {"id": "r", "content": "", "parse_success": True},
    ])
    assert result["entities"]["expected"] == 1
    assert result["entities"]["leaked"] == 1
    assert result["entities"]["leak_rate"] == 1


def test_source_present_row_is_not_hallucinated_when_parse_flag_is_false():
    records = [{
        "id": "r",
        "source_text": "Alice",
        "entities": [{"type": "PERSON", "original": "Alice"}],
    }]
    result = evaluate_predictions(records, [
        {"id": "r", "content": "PERSON\tAlice", "parse_success": False},
    ])
    assert result["entities"]["hallucinated"] == 0
    assert result["entity"]["fn"] == 1


def test_per_type_counts_use_the_same_normalization_as_overall_counts():
    records = [{
        "id": "r",
        "source_text": "Alice",
        "entities": [{"type": " person ", "original": "Alice"}],
    }]
    result = evaluate_predictions(records, [
        {"id": "r", "content": "PERSON\tAlice", "parse_success": True},
    ])
    assert result["per_type"]["PERSON"]["tp"] == result["entity"]["tp"] == 1
    assert result["per_type"]["PERSON"]["fp"] == 0


@pytest.mark.parametrize("predictions", [
    [{"id": "unknown", "content": "PERSON\tAlice", "parse_success": True}],
    [{"id": "r", "content": "", "parse_success": True}] * 2,
])
def test_evaluation_rejects_misaligned_or_duplicate_prediction_ids(predictions):
    records = [{"id": "r", "source_text": "Alice", "entities": []}]
    with pytest.raises(ValueError):
        evaluate_predictions(records, predictions)


def test_adjacent_replacements_can_cover_one_complete_gold_span():
    records = [{
        "id": "r",
        "source_text": "AlphaBeta",
        "entities": [{"type": "PERSON", "original": "AlphaBeta"}],
    }]
    result = evaluate_predictions(records, [{
        "id": "r",
        "content": "PERSON\tAlpha\nPERSON\tBeta",
        "parse_success": True,
    }])
    assert result["entity"]["fn"] == 1
    assert result["entities"]["leaked"] == 0


def test_every_source_occurrence_of_a_gold_value_must_be_covered():
    records = [{
        "id": "r",
        "source_text": "AlphaStreet Alpha",
        "entities": [{"type": "PERSON", "original": "Alpha"}],
    }]
    result = evaluate_predictions(records, [{
        "id": "r",
        "content": "ADDRESS\tAlphaStreet",
        "parse_success": True,
    }])
    assert result["entities"]["leaked"] == 1


def test_invalid_gold_annotation_is_rejected_without_echoing_its_value():
    records = [{
        "id": "r",
        "source_text": "Alice",
        "entities": [{"type": "PERSON", "original": "missing-value"}],
    }]
    with pytest.raises(ValueError) as error:
        evaluate_predictions(records, [])
    assert "missing-value" not in str(error.value)


def test_duplicate_record_ids_are_rejected():
    records = [{"id": "r", "source_text": "Alice", "entities": []}] * 2
    with pytest.raises(ValueError):
        evaluate_predictions(records, [])
