import unicodedata

from src.pii_tokens import (
    Entity,
    parse_tsv,
    pseudonymize_text,
    reassemble_text,
)


def test_tsv_parser_filters_prose_think_blocks_and_unknown_types():
    content = (
        "<think>hidden</think>\n설명\nPERSON\t김민수\n"
        "NAME\t버림\nPHONE\t010-2345-6789"
    )
    assert parse_tsv(content, "김민수 010-2345-6789") == [
        Entity("PERSON", "김민수"),
        Entity("PHONE", "010-2345-6789"),
    ]


def test_tsv_parser_rejects_hallucinated_values():
    content = "PERSON\t김민수\nEMAIL\tabsent@example.com"
    assert parse_tsv(content, "고객 김민수") == [Entity("PERSON", "김민수")]


def test_token_numbers_follow_source_order_not_model_order():
    text = "김민수 고객님과 이서연 고객님이 함께 방문했습니다."
    reversed_entities = [Entity("PERSON", "이서연"), Entity("PERSON", "김민수")]

    result = pseudonymize_text(text, reversed_entities)

    assert result.masked_text == "[PERSON_1] 고객님과 [PERSON_2] 고객님이 함께 방문했습니다."
    assert result.mapping == {"PERSON_1": "김민수", "PERSON_2": "이서연"}
    assert reassemble_text(result.masked_text, result.mapping) == text


def test_literal_original_wins_over_another_entities_variant():
    text = "전화 01012345678 계좌 010-1234-5678"

    result = pseudonymize_text(
        text,
        [Entity("PHONE", "01012345678"), Entity("ACCOUNT", "010-1234-5678")],
    )

    assert result.masked_text == "전화 [PHONE_1] 계좌 [ACCOUNT_1]"
    assert result.mapping["PHONE_1"] == "01012345678"
    assert result.mapping["ACCOUNT_1"] == "010-1234-5678"


def test_nfc_normalization_and_repeated_variants_are_deterministic():
    nfd_name = unicodedata.normalize("NFD", "김가상")
    text = f"고객 {nfd_name}, 별칭 김 가 상"

    result = pseudonymize_text(text, [Entity("PERSON", "김가상")])

    assert result.masked_text == "고객 [PERSON_1], 별칭 [PERSON_1]"
    assert result.mapping == {"PERSON_1": "김가상"}


def test_equal_offset_prefers_longer_value_and_numeric_boundary_is_preserved():
    text = "서울특별시 가상구 주문번호 55199001019012 생년월일 19900101"
    entities = [
        Entity("ADDRESS", "서울특별시"),
        Entity("ADDRESS", "서울특별시 가상구"),
        Entity("DOB", "19900101"),
    ]

    result = pseudonymize_text(text, entities)

    assert result.masked_text.startswith("[ADDRESS_1]")
    assert "55199001019012" in result.masked_text
    assert result.masked_text.endswith("[DOB_1]")


def test_empty_entities_leave_text_unchanged():
    result = pseudonymize_text("일반 문서", [])

    assert result.masked_text == "일반 문서"
    assert result.mapping == {}


def test_rrn_and_card_format_variants_replace_source_occurrences():
    text = "주민번호-900101-1234567 카드 9999 0001 0002 0003"
    entities = [
        Entity("RRN", "9001011234567"),
        Entity("CARD", "9999-0001-0002-0003"),
    ]

    result = pseudonymize_text(text, entities)

    assert result.masked_text == "주민번호-[RRN_1] 카드 [CARD_1]"


def test_same_value_multiple_types_uses_fixed_priority():
    text = "식별값 010-1234-5678"
    entities = [
        Entity("PHONE", "010-1234-5678"),
        Entity("ACCOUNT", "010-1234-5678"),
    ]

    result = pseudonymize_text(text, entities)

    assert result.masked_text == "식별값 [ACCOUNT_1]"
    assert result.mapping == {"ACCOUNT_1": "010-1234-5678"}


def test_repeated_original_is_replaced_globally():
    text = "김가상 고객과 김가상 고객"

    result = pseudonymize_text(text, [Entity("PERSON", "김가상")])

    assert result.masked_text == "[PERSON_1] 고객과 [PERSON_1] 고객"


def test_unknown_reassembly_token_is_preserved():
    assert reassemble_text("[PERSON_1] [UNKNOWN_9]", {"PERSON_1": "김가상"}) == (
        "김가상 [UNKNOWN_9]"
    )


def test_pseudonymize_skips_values_absent_from_source():
    result = pseudonymize_text(
        "고객 김가상",
        [Entity("PERSON", "김가상"), Entity("EMAIL", "absent@example.com")],
    )

    assert result.masked_text == "고객 [PERSON_1]"
    assert result.mapping == {"PERSON_1": "김가상"}
