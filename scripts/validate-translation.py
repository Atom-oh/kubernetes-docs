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


def counts(text):
    return {
        "headings": len(re.findall(r"^#{1,6} ", text, re.MULTILINE)),
        "fences": text.count("```"),
    }

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
        r"<(?:a|img)\b[^>]*?\b(?:href|src)=[\"']([^\"']+)[\"']",
        r"^\s*\[[^\]]+]:\s*(?:<([^>]+)>|(\S+))",
    ]
    targets = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            targets.append(next(value for value in match.groups() if value is not None))
    return Counter(targets)


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

    ratio = len(dst) / max(len(src), 1)
    if not (0.4 <= ratio <= 2.5):
        print(f"size ratio out of range: {ratio:.2f} ({dst_path})", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
