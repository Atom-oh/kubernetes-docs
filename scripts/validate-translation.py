#!/usr/bin/env python3
"""Structural sanity check for a machine-translated doc vs its en/ source.

We don't score translation quality here (the CI quality gate does that on
the aggregate diff) -- this just catches the failure modes of a headless
translation call: truncated output, empty file, or a model that rewrote the
markdown structure instead of leaving it alone. Code fences and links are
supposed to be copied verbatim, so their counts must match exactly; heading
count and overall size are allowed to drift a little (some languages are
more or less verbose).

Usage: validate-translation.py <src_path> <dst_path>
Exit 0 if the translation passes, 1 otherwise (reason printed to stderr).
"""
import re
import sys
from collections import Counter
from pathlib import Path


def counts(text):
    return {
        "headings": len(re.findall(r"^#{1,6} ", text, re.MULTILINE)),
        "fences": text.count("```"),
    }


def minimum_size_ratio(dst_path):
    # Natural Chinese prose often uses fewer characters than English. A size
    # heuristic must not encourage padding; fidelity is checked separately.
    return 0.25 if "cn" in Path(dst_path).parts else 0.4


def code_blocks(text):
    """Keep code bytes and fence languages unchanged, including quoted fences."""
    blocks = []
    marker = None
    language = None
    body = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:>\s*)*(`{3,}|~{3,})(.*)$", line)
        if marker is None:
            if match:
                marker, language = match.group(1), match.group(2).strip()
                body = []
        elif (match and match.group(1)[0] == marker[0]
              and len(match.group(1)) >= len(marker) and not match.group(2).strip()):
            blocks.append((language, "\n".join(body)))
            marker = None
        else:
            body.append(line)
    if marker is not None:
        raise ValueError("unclosed code fence")
    return blocks


def link_targets(text):
    patterns = [
        r"!?\[[^\]]*]\(\s*(?:<([^>]+)>|([^\s)]+))",
        # Linked images also have an enclosing destination, such as a video URL.
        r"\[\s*!\[[^\]]*]\([^)]*\)\s*]\(\s*(?:<([^>]+)>|([^\s)]+))",
        r"<(?:a|img)\b[^>]*?\b(?:href|src)=[\"']([^\"']+)[\"']",
        r"^\s*\[[^\]]+]:\s*(?:<([^>]+)>|(\S+))",
    ]
    targets = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            targets.append(next(value for value in match.groups() if value is not None))
    return Counter(targets)


def introduced_document_wrappers(source, translated):
    """Reject response envelopes without rejecting XML documented in the source."""
    # A truncated closing tag (for example "</final" without ">") also reaches
    # the Vue compiler as malformed HTML.
    pattern = r"<(/?)(source_document|translated_document|final|analysis|response)\b[^>\n]*(>|(?=\n|$))"
    # Count the tag's identity and terminator, rather than localized prose
    # following a documented unterminated tag.
    def tags(text):
        return Counter(
            f"<{closing}{name.lower()}{terminator}"
            for closing, name, terminator in re.findall(pattern, text, re.IGNORECASE)
        )
    source_tags = tags(source)
    translated_tags = tags(translated)
    return list((translated_tags - source_tags).elements())


def answer_tag_counts(text):
    """Preserve GitBook quiz answer containers without counting anchor spans."""
    return Counter(
        (closing, name.lower())
        for closing, name in re.findall(r"<(/?)(details|summary)\b[^>]*>", text, re.IGNORECASE)
    )


def table_shapes(text):
    """Keep pipe-table row/column counts, excluding fenced examples."""
    tables = []
    previous = None
    active = None
    fence = None
    for original in text.splitlines():
        line = re.sub(r"^\s*(?:>\s*)*", "", original).strip()
        marker = re.match(r"(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if (marker and marker.group(1)[0] == fence[0]
                    and len(marker.group(1)) >= len(fence) and not marker.group(2).strip()):
                fence = None
            continue
        if marker:
            fence = marker.group(1)
            previous = active = None
            continue
        # An escaped pipe is cell content; an even number of backslashes does
        # not escape the separator.
        cells = []
        start = 0
        escaped = False
        for index, char in enumerate(line):
            if char == "|" and not escaped:
                cells.append(line[start:index].strip())
                start = index + 1
            escaped = char == "\\" and not escaped
        cells.append(line[start:].strip())
        if line.startswith("|"):
            cells.pop(0)
        if line.endswith("|") and not escaped and cells[-1] == "":
            cells.pop()
        is_row = len(cells) > 1
        is_separator = is_row and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)
        if is_separator and previous is not None:
            active = [len(previous), len(cells)]
            tables.append(active)
        elif active is not None and is_row:
            active.append(len(cells))
        else:
            active = None
        previous = cells if is_row else None
    return tables


def main():
    if len(sys.argv) != 3:
        print("usage: validate-translation.py <src_path> <dst_path>", file=sys.stderr)
        return 1

    src_path, dst_path = sys.argv[1], sys.argv[2]
    src = open(src_path, encoding="utf-8").read()
    dst = open(dst_path, encoding="utf-8").read()

    if not dst.strip():
        print(f"empty output: {dst_path}", file=sys.stderr)
        return 1

    src_c, dst_c = counts(src), counts(dst)
    if src_c["headings"] != dst_c["headings"]:
        print(
            f"heading count mismatch: src={src_c['headings']} dst={dst_c['headings']} ({dst_path})",
            file=sys.stderr,
        )
        return 1
    if src_c["fences"] != dst_c["fences"]:
        print(
            f"code fence count mismatch: src={src_c['fences']} dst={dst_c['fences']} ({dst_path})",
            file=sys.stderr,
        )
        return 1
    try:
        if code_blocks(src) != code_blocks(dst):
            print(f"code block content/language mismatch: {dst_path}", file=sys.stderr)
            return 1
    except ValueError as error:
        print(f"{error}: {dst_path}", file=sys.stderr)
        return 1
    if link_targets(src) != link_targets(dst):
        print(f"link/image target mismatch: {dst_path}", file=sys.stderr)
        return 1

    wrappers = introduced_document_wrappers(src, dst)
    if wrappers:
        print(f"unexpected translation wrapper {wrappers[0]}: {dst_path}", file=sys.stderr)
        return 1
    if answer_tag_counts(src) != answer_tag_counts(dst):
        print(f"answer container tag mismatch: {dst_path}", file=sys.stderr)
        return 1
    if table_shapes(src) != table_shapes(dst):
        print(f"table row/column mismatch: {dst_path}", file=sys.stderr)
        return 1

    ratio = len(dst) / max(len(src), 1)
    if not (minimum_size_ratio(dst_path) <= ratio <= 2.5):
        print(f"size ratio out of range: {ratio:.2f} ({dst_path})", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
