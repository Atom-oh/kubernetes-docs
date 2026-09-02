"""TSV entity parsing and deterministic PII token replacement."""

import re
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass


VALID_TYPES = frozenset(
    {
        "PERSON",
        "RRN",
        "DOB",
        "REL",
        "ADDRESS",
        "PHONE",
        "EMAIL",
        "ACCOUNT",
        "CARD",
    }
)
TYPE_PRIORITY = (
    "RRN",
    "CARD",
    "ACCOUNT",
    "PHONE",
    "EMAIL",
    "DOB",
    "PERSON",
    "ADDRESS",
    "REL",
)
TOKEN_PATTERN = re.compile(r"\[[A-Z_]+_\d+\]")
THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class Entity:
    type: str
    original: str


@dataclass(frozen=True)
class TokenizationResult:
    masked_text: str
    mapping: dict[str, str]


def parse_tsv(content: str, source_text: str) -> list[Entity]:
    """Parse whitelisted TSV rows whose values can be found in the source."""
    source_nfc = unicodedata.normalize("NFC", source_text)
    clean = THINK_PATTERN.sub("", content)
    parsed: list[Entity] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in clean.splitlines():
        if "\t" not in raw_line:
            continue
        raw_type, raw_value = raw_line.split("\t", 1)
        entity_type = raw_type.strip().upper()
        value = unicodedata.normalize("NFC", raw_value.strip())
        if entity_type not in VALID_TYPES or not value:
            continue
        key = (entity_type, value)
        if key in seen or _first_source_position(source_nfc, value, entity_type) < 0:
            continue
        seen.add(key)
        parsed.append(Entity(entity_type, value))
    return parsed


def pseudonymize_text(text: str, entities: list[Entity]) -> TokenizationResult:
    """Replace entities with deterministic source-order tokens."""
    source = unicodedata.normalize("NFC", text)
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    positions: dict[str, int] = {}

    for entity in entities:
        entity_type = entity.type.strip().upper()
        original = unicodedata.normalize("NFC", entity.original.strip())
        if entity_type not in VALID_TYPES or not original:
            continue
        position = _first_source_position(source, original, entity_type)
        if position < 0:
            continue
        if original not in grouped:
            grouped[original] = []
            positions[original] = position
        else:
            positions[original] = min(positions[original], position)
        grouped[original].append(entity_type)

    def sort_key(item: tuple[str, list[str]]) -> tuple:
        original, _types = item
        position = positions[original]
        if position >= 0:
            return (0, position, -len(original), original)
        return (1, 0, -len(original), original)

    ordered = sorted(grouped.items(), key=sort_key)
    counters: dict[str, int] = {}
    token_by_original: OrderedDict[str, str] = OrderedDict()
    chosen_type: dict[str, str] = {}
    mapping: dict[str, str] = {}

    for original, types in ordered:
        entity_type = _pick_type(types)
        counters[entity_type] = counters.get(entity_type, 0) + 1
        token_key = f"{entity_type}_{counters[entity_type]}"
        token_by_original[original] = f"[{token_key}]"
        chosen_type[original] = entity_type
        mapping[token_key] = original

    if not token_by_original:
        return TokenizationResult(source, {})

    originals: list[tuple[str, str]] = []
    variants: list[tuple[str, str]] = []
    for original, token in token_by_original.items():
        originals.append((original, token))
        variants.extend(
            (variant, token)
            for variant in _generate_variants(original, chosen_type[original])
        )

    lookup: dict[str, str] = {}
    for pattern, token in originals + variants:
        normalized = unicodedata.normalize("NFC", pattern)
        if normalized and normalized not in lookup:
            lookup[normalized] = token

    alternation: list[str] = []
    for pattern in sorted(lookup, key=lambda value: (-len(value), value)):
        escaped = re.escape(pattern)
        if pattern.isdigit():
            alternation.append(f"(?<!\\d){escaped}(?!\\d)")
        else:
            alternation.append(escaped)

    if not alternation:
        return TokenizationResult(source, mapping)

    combined = re.compile("|".join(alternation))
    masked = combined.sub(lambda match: lookup[match.group(0)], source)
    return TokenizationResult(masked, mapping)


def reassemble_text(masked_text: str, mapping: dict[str, str]) -> str:
    """Restore known tokens while leaving unknown tokens unchanged."""

    def replace(match: re.Match) -> str:
        token_key = match.group(0)[1:-1]
        return mapping.get(token_key, match.group(0))

    return TOKEN_PATTERN.sub(replace, masked_text)


def _pick_type(types: list[str]) -> str:
    for candidate in TYPE_PRIORITY:
        if candidate in types:
            return candidate
    return sorted(types)[0]


def _first_source_position(source: str, original: str, entity_type: str) -> int:
    candidates = [original, *_generate_variants(original, entity_type)]
    positions = [
        source.find(unicodedata.normalize("NFC", candidate))
        for candidate in candidates
    ]
    found = [position for position in positions if position >= 0]
    return min(found) if found else -1


def _generate_variants(original: str, entity_type: str) -> list[str]:
    variants: list[str] = []
    compact_spaces = re.sub(r"\s+", "", original)

    if entity_type == "PERSON":
        characters = list(compact_spaces)
        if 2 <= len(characters) <= 6:
            variants.extend(
                (
                    "".join(characters),
                    " ".join(characters),
                    "  ".join(characters),
                    "\t".join(characters),
                    "\n".join(characters),
                )
            )
    elif entity_type == "RRN":
        digits = re.sub(r"\D", "", original)
        if len(digits) == 13:
            variants.extend(
                (
                    digits,
                    f"{digits[:6]}-{digits[6:]}",
                    f"{digits[:6]} - {digits[6:]}",
                    f"{digits[:6]}- {digits[6:]}",
                )
            )
    elif entity_type == "PHONE":
        digits = re.sub(r"\D", "", original)
        if len(digits) == 11 and digits.startswith("010"):
            groups = (digits[:3], digits[3:7], digits[7:])
            variants.extend(
                (
                    digits,
                    "-".join(groups),
                    " ".join(groups),
                    ".".join(groups),
                )
            )
        elif len(digits) == 10 and digits.startswith("02"):
            groups = (digits[:2], digits[2:6], digits[6:])
            variants.extend((digits, "-".join(groups), " ".join(groups)))
        elif original.startswith("+1"):
            variants.append(original.replace("-", " "))
    elif entity_type == "CARD":
        digits = re.sub(r"\D", "", original)
        if len(digits) == 16:
            groups = tuple(digits[offset : offset + 4] for offset in range(0, 16, 4))
            variants.extend(
                (digits, "-".join(groups), " ".join(groups), ".".join(groups))
            )
        elif len(digits) == 15:
            groups = (digits[:4], digits[4:10], digits[10:])
            variants.extend((digits, "-".join(groups), " ".join(groups)))
    elif entity_type == "ACCOUNT":
        digits = re.sub(r"\D", "", original)
        if digits:
            variants.append(digits)
            if len(digits) == 12:
                variants.extend(
                    (
                        f"{digits[:3]}-{digits[3:6]}-{digits[6:]}",
                        f"{digits[:3]} {digits[3:6]} {digits[6:]}",
                    )
                )
    elif entity_type == "DOB":
        digits = re.sub(r"\D", "", original)
        if len(digits) == 8:
            variants.extend(
                (
                    digits,
                    f"{digits[:4]}-{digits[4:6]}-{digits[6:]}",
                    f"{digits[:4]}.{digits[4:6]}.{digits[6:]}",
                )
            )
        elif len(digits) == 6:
            variants.extend(
                (
                    digits,
                    f"{digits[:2]}-{digits[2:4]}-{digits[4:]}",
                    f"{digits[:2]}.{digits[2:4]}.{digits[4:]}",
                )
            )

    normalized_original = unicodedata.normalize("NFC", original)
    return list(
        dict.fromkeys(
            unicodedata.normalize("NFC", variant)
            for variant in variants
            if variant and unicodedata.normalize("NFC", variant) != normalized_original
        )
    )
