#!/usr/bin/env python3
"""Append one section's SUMMARY.md / README.md nav entries into a cn/jp/es
locale, translating only the link titles (never headings' first occurrence
gets a one-off translation, then reused — see below).

Why this exists: VitePress builds its sidebar purely from SUMMARY.md
(.vitepress/summary.ts), so a translated page with no nav entry is an orphan
page nobody can reach. Quizzes and labs for a "section" (e.g. basics/) don't
live under that section's own SUMMARY.md heading -- they're flattened into
two global headings ("## Quiz Collection", "## Lab Guides") shared by every
section, appended in whatever order sections get backfilled. README.md's
ToC has the opposite shape: one "### <Section>" block per section with
Quiz/Lab already inlined per item.

Because a shared heading (e.g. "## Quiz Collection") gets created once by
whichever section is backfilled first and re-translating its title every
time would drift, translated heading text is cached in
.github/i18n-heading-map.json (en heading -> {lang: translated}) and reused.

Usage: sync-nav.py <section> <lang>   (lang: cn | jp | es)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEADING_MAP_PATH = REPO_ROOT / ".github" / "i18n-heading-map.json"
LANG_NAMES = {"cn": "Simplified Chinese", "jp": "Japanese", "es": "Spanish"}

ITEM_RE = re.compile(r"^( *)\* (?:\[(.+?)\]\((.+?)\)|(.+))$")


def load_heading_map():
    if HEADING_MAP_PATH.exists():
        return json.loads(HEADING_MAP_PATH.read_text(encoding="utf-8"))
    return {}


def save_heading_map(m):
    HEADING_MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def translate_titles(titles, lang):
    """One kiro-cli call translates a batch of short titles. Falls back to
    the original English titles (logged, non-fatal) if the model call fails
    or returns the wrong line count -- an untranslated nav label is a minor
    quality gap, not a broken build."""
    if not titles:
        return []
    lang_name = LANG_NAMES[lang]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    prompt = (
        f"Translate each of the following {len(titles)} short documentation titles into "
        f"{lang_name}. Keep Kubernetes/AWS technical terms (Pod, EKS, Karpenter, etc.) in "
        f"English. Output EXACTLY {len(titles)} lines, one translated title per line, in the "
        f"same order, with no numbering and no extra commentary:\n{numbered}"
    )
    try:
        result = subprocess.run(
            ["kiro-cli", "chat", prompt, "--model", "claude-haiku-4.5",
             "--no-interactive", "--trust-tools=", "--wrap", "never"],
            capture_output=True, text=True, timeout=90,
        )
        lines = [re.sub(r"\x1b\[[0-9;]*m", "", ln).strip() for ln in result.stdout.splitlines()]
        lines = [re.sub(r"^\d+\.\s*", "", ln).strip() for ln in lines if ln.strip()]
        if len(lines) == len(titles):
            return lines
        print(f"::warning::sync-nav: title translation returned {len(lines)}/{len(titles)} lines, keeping English", file=sys.stderr)
    except Exception as e:
        print(f"::warning::sync-nav: title translation failed ({e}), keeping English", file=sys.stderr)
    return titles


class Node:
    def __init__(self, indent, title, path, raw_group_text):
        self.indent = indent
        self.title = title          # None for a plain grouping bullet
        self.path = path            # None for a plain grouping bullet
        self.raw_group_text = raw_group_text
        self.children = []
        self.keep = False


def parse_block(lines):
    """Parse the item lines under one '## Heading' into a forest of Nodes."""
    roots = []
    stack = []  # list of (indent, Node)
    for line in lines:
        m = ITEM_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        node = Node(indent, m.group(2), m.group(3), m.group(4))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((indent, node))
    return roots


def prune(nodes, prefixes):
    survivors = []
    for n in nodes:
        n.children = prune(n.children, prefixes)
        n.keep = bool(n.children) or (n.path and any(n.path.startswith(p) for p in prefixes))
        if n.keep:
            survivors.append(n)
    return survivors


def collect_titled(nodes, out):
    for n in nodes:
        if n.title is not None:
            out.append(n)
        collect_titled(n.children, out)


def render(nodes, existing_paths=frozenset()):
    """Shared parent bullets (e.g. 'Lab Guides Introduction' wrapping every
    section's lab entries) get pruned back in on every section's run since
    they have surviving children -- render them only the first time; once
    their path is already in the destination file, emit just their children
    so the same wrapper line isn't duplicated on every subsequent section."""
    out = []
    for n in nodes:
        already_present = n.path is not None and n.path in existing_paths
        if not already_present:
            prefix = " " * n.indent + "* "
            if n.title is not None:
                out.append(f"{prefix}[{n.title}]({n.path})")
            else:
                out.append(f"{prefix}{n.raw_group_text}")
        out.extend(render(n.children, existing_paths))
    return out


def extract_heading_blocks(summary_lines):
    """-> list of (heading_text, [item_lines]) in document order."""
    blocks = []
    current_heading = None
    current_lines = []
    for line in summary_lines:
        h = re.match(r"^## (.+)", line)
        if h:
            if current_heading is not None:
                blocks.append((current_heading, current_lines))
            current_heading = h.group(1).strip()
            current_lines = []
        elif current_heading is not None:
            current_lines.append(line)
    if current_heading is not None:
        blocks.append((current_heading, current_lines))
    return blocks


def sync_summary(section, lang, heading_map):
    en_path = REPO_ROOT / "en" / "SUMMARY.md"
    dst_path = REPO_ROOT / lang / "SUMMARY.md"
    prefixes = [f"{section}/", f"quizzes/{section}/", f"labs/{section}/"]

    blocks = extract_heading_blocks(en_path.read_text(encoding="utf-8").splitlines())
    dst_text = dst_path.read_text(encoding="utf-8")

    for heading, item_lines in blocks:
        forest = prune(parse_block(item_lines), prefixes)
        if not forest:
            continue

        titled = []
        collect_titled(forest, titled)
        translated = translate_titles([n.title for n in titled], lang)
        for n, t in zip(titled, translated):
            n.title = t

        existing_paths = set(re.findall(r"\]\(([^)]+)\)", dst_text))
        fragment_lines = render(forest, existing_paths)
        if not fragment_lines:
            continue

        dst_heading = heading_map.get(heading, {}).get(lang)
        if dst_heading is None:
            dst_heading = translate_titles([heading], lang)[0]
            heading_map.setdefault(heading, {})[lang] = dst_heading

        heading_re = re.compile(rf"^## {re.escape(dst_heading)}\s*$", re.MULTILINE)
        m = heading_re.search(dst_text)
        if m:
            # Insert before the next '## ' heading (or EOF), keeping this heading's block contiguous.
            rest = dst_text[m.end():]
            next_h = re.search(r"^## ", rest, re.MULTILINE)
            insert_at = m.end() + (next_h.start() if next_h else len(rest))
            dst_text = dst_text[:insert_at].rstrip("\n") + "\n\n" + "\n".join(fragment_lines) + "\n\n" + dst_text[insert_at:].lstrip("\n")
        else:
            dst_text = dst_text.rstrip("\n") + f"\n\n## {dst_heading}\n\n" + "\n".join(fragment_lines) + "\n"

    dst_path.write_text(dst_text, encoding="utf-8")


def sync_readme(section, lang, heading_map):
    en_path = REPO_ROOT / "en" / "README.md"
    dst_path = REPO_ROOT / lang / "README.md"
    en_lines = en_path.read_text(encoding="utf-8").splitlines()

    # README.md ToC is one '### Heading' block per section, items already
    # inline Quiz/Lab -- no cross-section flattening, so a whole-block copy
    # (minus the link titles, which get translated) is enough.
    heading_idx = None
    for i, line in enumerate(en_lines):
        h = re.match(r"^### (.+)", line)
        if h and section_matches_heading(en_lines, i, section):
            heading_idx = i
            heading_text = h.group(1).strip()
            break
    if heading_idx is None:
        return  # section has no dedicated README ToC block (e.g. "news")

    j = heading_idx + 1
    body = []
    while j < len(en_lines) and not en_lines[j].startswith("### "):
        body.append(en_lines[j])
        j += 1

    titles = re.findall(r"\[([^\]]+)\]\([^)]+\)", "\n".join(body))
    # Skip bare "Quiz"/"Lab" labels -- keep those in English for consistency
    # with SUMMARY.md's untranslated nav chrome, only translate real titles.
    real_titles = [t for t in titles if t not in ("Quiz", "Lab")]
    translated_map = dict(zip(real_titles, translate_titles(real_titles, lang)))

    def sub_title(m):
        t = m.group(1)
        return f"[{translated_map.get(t, t)}]({m.group(2)})"

    translated_body = [re.sub(r"\[([^\]]+)\]\(([^)]+)\)", sub_title, line) for line in body]

    dst_heading = heading_map.get(heading_text, {}).get(lang)
    if dst_heading is None:
        dst_heading = translate_titles([heading_text], lang)[0]
        heading_map.setdefault(heading_text, {})[lang] = dst_heading

    dst_path_text = dst_path.read_text(encoding="utf-8")
    if f"### {dst_heading}" in dst_path_text:
        return  # already synced for this lang
    dst_path_text = dst_path_text.rstrip("\n") + f"\n\n### {dst_heading}\n" + "\n".join(translated_body) + "\n"
    dst_path.write_text(dst_path_text, encoding="utf-8")


def section_matches_heading(en_lines, heading_idx, section):
    """A README ToC heading 'belongs' to a section if its first item link
    path starts with '<section>/'."""
    j = heading_idx + 1
    while j < len(en_lines) and not en_lines[j].startswith("### "):
        m = re.search(r"\]\(\./?([^)]+)\)", en_lines[j])
        if m:
            return m.group(1).startswith(f"{section}/")
        j += 1
    return False


def main():
    if len(sys.argv) != 3:
        print("usage: sync-nav.py <section> <lang>", file=sys.stderr)
        return 1
    section, lang = sys.argv[1], sys.argv[2]
    if lang not in LANG_NAMES:
        print(f"unknown lang '{lang}' (want cn|jp|es)", file=sys.stderr)
        return 1

    heading_map = load_heading_map()
    sync_summary(section, lang, heading_map)
    sync_readme(section, lang, heading_map)
    save_heading_map(heading_map)
    return 0


if __name__ == "__main__":
    sys.exit(main())
