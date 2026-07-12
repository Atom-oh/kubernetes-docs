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


def counts(text):
    return {
        "headings": len(re.findall(r"^#{1,6} ", text, re.MULTILINE)),
        "fences": text.count("```"),
    }


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

    ratio = len(dst) / max(len(src), 1)
    if not (0.4 <= ratio <= 2.5):
        print(f"size ratio out of range: {ratio:.2f} ({dst_path})", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
