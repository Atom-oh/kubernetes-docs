#!/usr/bin/env python3
"""Repair ** delimiters that cannot open/close next to CJK prose.

Only delimiter positions change. Fenced and inline code stay untouched.
Move edge punctuation outside emphasis; when code or links prevent that,
include the adjacent word so CommonMark can recognize the delimiter.
"""
import argparse
import os
from pathlib import Path
import re
import tempfile
import unicodedata


FENCE = re.compile(r"^\s*(?:>\s*)*(`{3,}|~{3,})(.*)$")
STRONG = re.compile(r"(?<!\\)\*\*([^*\n]+)\*\*")
INLINE_CODE = re.compile(r"(`+)(.+?)\1")


def punctuation(character):
    return bool(character) and unicodedata.category(character)[0] in "PS"


def can_open(before, after):
    return bool(after) and not after.isspace() and (
        not punctuation(after) or not before or before.isspace() or punctuation(before)
    )


def can_close(before, after):
    return bool(before) and not before.isspace() and (
        not punctuation(before) or not after or after.isspace() or punctuation(after)
    )


def repair_line(line):
    code = [(match.start(), match.end()) for match in INLINE_CODE.finditer(line)]
    for match in reversed(list(STRONG.finditer(line))):
        start, end = match.span()
        if any(left <= start < right or left < end <= right for left, right in code):
            continue
        body = match[1]
        before = line[start - 1] if start else ""
        after = line[end] if end < len(line) else ""
        if can_open(before, body[0]) and can_close(body[-1], after):
            continue
        leading, trailing, core = "", "", body
        # Do not split a Markdown link, code span or HTML tag at its edges.
        if not re.search(r"`|!?\[|<[/!A-Za-z]", body):
            while core and punctuation(core[0]):
                leading += core[0]
                core = core[1:]
            # Keep a terminal parenthetical balanced in the source Markdown.
            for closing, opening in ((")", "("), ("）", "（")):
                if not core.endswith(closing):
                    continue
                depth = 0
                for position in range(len(core) - 1, -1, -1):
                    if core[position] == closing:
                        depth += 1
                    elif core[position] == opening:
                        depth -= 1
                        if not depth:
                            if position:
                                trailing = core[position:] + trailing
                                core = core[:position]
                            break
            while core and punctuation(core[-1]):
                trailing = core[-1] + trailing
                core = core[:-1]
            while core and core[-1].isspace():
                trailing = core[-1] + trailing
                core = core[:-1]
        if core and can_open(leading[-1:] or before, core[0]) and can_close(
            core[-1], trailing[:1] or after
        ):
            replacement = leading + "**" + core + "**" + trailing
        else:
            left, right = start, end
            if not can_open(before, body[0]):
                while left and line[left - 1].isalnum():
                    left -= 1
            if not can_close(body[-1], after):
                while right < len(line) and line[right].isalnum():
                    right += 1
            extended = line[left:start] + body + line[end:right]
            if not can_open(line[left - 1:left], extended[0]) or not can_close(
                extended[-1], line[right:right + 1]
            ):
                continue
            start, end = left, right
            replacement = "**" + extended + "**"
        original = line[start:end]
        if original.replace("**", "") != replacement.replace("**", ""):
            raise ValueError("Repair changed prose")
        line = line[:start] + replacement + line[end:]
    return line


def repair(markdown):
    result = []
    fence = None
    for line in markdown.splitlines(keepends=True):
        match = FENCE.match(line.rstrip("\r\n"))
        if fence:
            result.append(line)
            if (match and match[1][0] == fence[0]
                    and len(match[1]) >= len(fence) and not match[2].strip()):
                fence = None
        elif match:
            fence = match[1]
            result.append(line)
        else:
            result.append(repair_line(line))
    repaired = "".join(result)
    if markdown.replace("**", "") != repaired.replace("**", ""):
        raise ValueError("Repair changed Markdown content")
    return repaired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = 0
    for file in args.files:
        original = file.read_text(encoding="utf-8")
        fixed = repair(original)
        if fixed != original:
            changed += 1
            if not args.check:
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", encoding="utf-8", dir=file.parent, delete=False
                    ) as handle:
                        temporary = handle.name
                        handle.write(fixed)
                    os.chmod(temporary, file.stat().st_mode)
                    os.replace(temporary, file)
                finally:
                    if temporary and os.path.exists(temporary):
                        os.unlink(temporary)
            print(file)
    print(f"{changed} Markdown file(s) {'need repair' if args.check else 'repaired'}")
    return int(args.check and changed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
