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


def _clean_kiro_line(ln):
    """Strip ANSI color codes and kiro-cli's leading '> ' response marker
    (only present on the first line of output, and only visible once ANSI
    codes are stripped -- easy to miss, caught via a real run that leaked
    "> " into translated titles, e.g. "[> Linux 基础知识]")."""
    ln = re.sub(r"\x1b\[[0-9;]*m", "", ln)
    ln = re.sub(r"^>\s*", "", ln)
    return ln.strip()


_title_cache = {}
SUFFIX_RE = re.compile(r"^(.+) (Quiz|Lab)$")


def _run_kiro_batch(prompt, n, lang):
    """Shared kiro-cli batch call: send prompt, expect exactly n lines back.
    Retries once on any failure before giving up -- a real run under
    concurrent runner load (another section's backfill in parallel) hit a
    transient failure here and silently kept a heading/title in English for
    just that one run, with no retry to absorb the blip (unlike
    translate.sh's file-level calls, which already retry once). Returns
    None only after both attempts fail, so callers can fall back -- an
    untranslated nav label is a minor quality gap, not a broken build."""
    for attempt in (1, 2):
        try:
            result = subprocess.run(
                ["kiro-cli", "chat", prompt, "--model", "gpt-5.6-terra",
                 "--no-interactive", "--trust-tools=", "--wrap", "never"],
                capture_output=True, text=True, timeout=90,
            )
            lines = [_clean_kiro_line(ln) for ln in result.stdout.splitlines()]
            lines = [re.sub(r"^\d+\.\s*", "", ln).strip() for ln in lines if ln.strip()]
            if len(lines) == n:
                return lines
            print(f"::warning::sync-nav: title translation attempt {attempt} returned {len(lines)}/{n} lines", file=sys.stderr)
        except Exception as e:
            print(f"::warning::sync-nav: title translation attempt {attempt} failed ({e})", file=sys.stderr)
    print(f"::warning::sync-nav: title translation failed after retry, keeping English", file=sys.stderr)
    return None


def _translate_batch(titles, lang):
    """Translate a batch of independent titles, caching each (title, lang)
    pair so the same English title translates identically wherever it's
    encountered (SUMMARY.md vs README.md) -- without this, two independent
    calls for "Linux Basics" could come back worded differently ("Linux
    基础知识" vs "Linux 基础"), a real inconsistency a quality-gate run
    caught."""
    uncached = [t for t in titles if (t, lang) not in _title_cache]
    if uncached:
        lang_name = LANG_NAMES[lang]
        numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(uncached))
        prompt = (
            f"Translate each of the following {len(uncached)} short documentation titles "
            f"FULLY into {lang_name} -- translate the whole title, do not leave generic "
            f"English words untranslated and do not append the English original alongside "
            f"the translation. The only exception: keep specific Kubernetes/AWS product or "
            f"resource names (Pod, EKS, Karpenter, etc.) in English within an otherwise "
            f"translated sentence. Output EXACTLY {len(uncached)} lines, one translated "
            f"title per line, in the same order, with no numbering and no extra "
            f"commentary:\n{numbered}"
        )
        lines = _run_kiro_batch(prompt, len(uncached), lang) or uncached
        for t, translated in zip(uncached, lines):
            _title_cache[(t, lang)] = translated
    return [_title_cache[t, lang] for t in titles]


def _translate_suffixed_batch(entries, lang):
    """entries: [(full_title, base_title, kind)] where kind is 'Quiz' or
    'Lab'. Anchors each to base_title's already-cached translation instead
    of translating the full compound phrase blind -- otherwise "Introduction
    to Kubernetes" and "Introduction to Kubernetes Quiz" get translated by
    two separate, independent calls and can disagree on wording (a real run
    produced cn "简介" vs "入门" for the same concept). Falls back to
    _translate_batch on the full phrase if this call fails."""
    uncached = [e for e in entries if (e[0], lang) not in _title_cache]
    if not uncached:
        return
    lang_name = LANG_NAMES[lang]
    numbered = "\n".join(
        f"{i + 1}. English title: \"{full}\" | Its topic's fixed {lang_name} translation: "
        f"\"{_title_cache[base, lang]}\" | Page type: {kind}"
        for i, (full, base, kind) in enumerate(uncached)
    )
    prompt = (
        f"For each of the following {len(uncached)} documentation page titles, produce a "
        f"natural {lang_name} title for that Quiz or Lab page. Each is the Quiz/Lab page for "
        f"a topic whose translation is already fixed (given) -- reuse that exact given phrase "
        f"for the topic, phrased the way {lang_name} naturally titles a quiz/lab page for it "
        f"(e.g. a suffix or prefix word meaning Quiz/Lab, whichever reads naturally). Output "
        f"EXACTLY {len(uncached)} lines, one title per line, same order, no numbering, no "
        f"extra commentary:\n{numbered}"
    )
    lines = _run_kiro_batch(prompt, len(uncached), lang)
    if lines is None:
        _translate_batch([full for full, _, _ in uncached], lang)
        return
    for (full, _, _), translated in zip(uncached, lines):
        _title_cache[(full, lang)] = translated


def translate_titles(titles, lang):
    """Public entry point. Splits "X Quiz"/"X Lab" titles from plain ones so
    quiz/lab titles get anchored to their already-translated base concept
    (see _translate_suffixed_batch) instead of translated independently."""
    plain, suffixed = [], []
    for t in titles:
        m = SUFFIX_RE.match(t)
        (suffixed.append((t, m.group(1), m.group(2))) if m else plain.append(t))

    bases = list(dict.fromkeys(plain + [base for _, base, _ in suffixed]))
    if bases:
        _translate_batch(bases, lang)
    if suffixed:
        _translate_suffixed_batch(suffixed, lang)

    return [_title_cache[(t, lang)] for t in titles]


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


def prune_missing(nodes, lang):
    """Drop any node whose destination file doesn't actually exist -- a
    section-scoped translate.sh failure (a file that timed out both
    attempts) or a path that's structurally out of scope for section
    backfill (e.g. 'Lab Guides Introduction' -> labs/README.md, a top-level
    intro never touched by any per-section run). Without this, a nav entry
    can point at a file that was never created -- a dead link a real run
    produced (4/13 basics files failed translation, but SUMMARY.md/README.md
    still linked to all 13)."""
    survivors = []
    for n in nodes:
        n.children = prune_missing(n.children, lang)
        exists = n.path is not None and (REPO_ROOT / lang / n.path).exists()
        n.keep = bool(n.children) or exists
        if n.keep:
            survivors.append(n)
    return survivors


def collect_titled(nodes, out):
    for n in nodes:
        if n.title is not None:
            out.append(n)
        collect_titled(n.children, out)


def descendant_paths(node):
    """Every linked path below (not including) node, in document order."""
    out = []
    for c in node.children:
        if c.path is not None:
            out.append(c.path)
        out.extend(descendant_paths(c))
    return out


def node_present(n, existing_paths):
    """A linked node is already in the destination when its own path is;
    a plain group bullet (path None, e.g. '* Operations Guide' in the Quiz
    Collection) has no path of its own to look up, so it counts as present
    when ANY descendant path already is. Judging a group only by its own
    (nonexistent) path made every follow-up run that added a single new quiz
    re-emit the whole group line -- untranslated, since raw_group_text is
    never translated -- as a brand-new root subtree at the block tail
    (issue #172, score 48: '+* Operations Guide' with one child, right below
    the already-present translated group holding the other 15 quizzes)."""
    if n.path is not None:
        return n.path in existing_paths
    return any(p in existing_paths for p in descendant_paths(n))


def render(nodes, lang, existing_paths=frozenset()):
    """Shared parent bullets (e.g. 'Lab Guides Introduction' wrapping every
    section's lab entries) get pruned back in on every section's run since
    they have surviving children -- render them only the first time; once
    their path is already in the destination file, emit just their children
    so the same wrapper line isn't duplicated on every subsequent section.

    A LEAF node (no children) whose own destination file doesn't exist
    (translation failure) is skipped -- rendered as absent, per #39/#43.
    A node WITH children is always rendered. Quiz category parents are plain
    group bullets such as '* Observability', so they have no destination file
    by design. Dropping those groups would orphan every deeply nested child at
    its original indent and make it appear under an unrelated preceding item."""
    out = []
    for n in nodes:
        already_present = node_present(n, existing_paths)
        file_missing = n.path is not None and not n.children and not (REPO_ROOT / lang / n.path).exists()
        if not already_present and not file_missing:
            prefix = " " * n.indent + "* "
            if n.title is not None:
                out.append(f"{prefix}[{n.title}]({n.path})")
            else:
                out.append(f"{prefix}{n.raw_group_text}")
        out.extend(render(n.children, lang, existing_paths))
    return out


def _subtree_end(dst_text, start_pos, parent_indent):
    """Position right after the last descendant line of a bullet at
    parent_indent, starting the scan at start_pos (its own line's end) --
    the first subsequent bullet line at indent <= parent_indent is a
    sibling or an ancestor's sibling, so everything before it belongs to
    this node's subtree. Returns start_pos unchanged when there are no
    descendants.

    The scan also stops at the next '## ' heading, and the returned position
    sits right after the last NON-BLANK descendant line rather than at the
    start of whatever bullet ended the scan. Without both, the last root of a
    heading block (e.g. 'Operations Guide' -> ops/README.md, whose last child
    is ops/15) has no lower-indent sibling of its own, so the old scan ran
    through the blank line and the next '## ' heading and stopped at the NEXT
    block's first bullet -- and a new child (ops/16) got spliced in there,
    indented under the wrong heading (issue #172, score 48: '## 可观测性'
    followed by '  * [故障排查手册](ops/16-troubleshooting-playbook.md)' in
    all three languages)."""
    end = start_pos
    for lm in re.finditer(r"^[^\n]*\n?", dst_text[start_pos:], re.MULTILINE):
        line = lm.group(0)
        if not line:
            break
        if line.startswith("## "):
            break
        bm = re.match(r"^( *)\* ", line)
        if bm and len(bm.group(1)) <= parent_indent:
            break
        if line.strip():
            end = start_pos + lm.end()
    return end


def _find_group_line(dst_text, group, existing_paths):
    """Locate a path-less group bullet's own line in dst_text via its
    already-present descendants: take the first descendant path that's in
    the destination, then walk UP the bullet lines above it along the
    ancestor chain (each step to the nearest preceding bullet with a smaller
    indent) until reaching one at the group's own indent. Returns the match
    object for that line (group(1) = its indent) or None."""
    for p in descendant_paths(group):
        if p not in existing_paths:
            continue
        m = re.search(rf"^( *)\* \[.*?\]\({re.escape(p)}\)[^\n]*\n", dst_text, re.MULTILINE)
        if not m:
            continue
        cur_indent = len(m.group(1))
        above = list(re.finditer(r"^( *)\* [^\n]*\n", dst_text[:m.start()], re.MULTILINE))
        for bm in reversed(above):
            indent = len(bm.group(1))
            if indent >= cur_indent:
                continue
            if indent <= group.indent:
                return bm
            cur_indent = indent
        return None
    return None


def insert_new_nodes(nodes, dst_text, existing_paths, lang, tail_anchor):
    """Splice new (not-yet-present) subtrees into dst_text anchored right
    after their nearest already-present ancestor's own line, instead of
    always appending at the tail of the whole heading block.

    A tail-only append is correct the first time a heading's tree is added
    (everything is new, in document order, so appending is the tree). It
    breaks on a later run that only adds a few previously-failed leaf files
    whose parent (e.g. an Istio subsection) already exists mid-block: with
    tail-only append those leaves land after whatever unrelated bullet
    happens to be last in the block, visually nesting under it. A real run
    hit exactly this for service-mesh (issue #101): two retried Istio pages
    rendered as children of Cilium Service Mesh's "Best Practices" bullet,
    just because that was the block's last line.

    tail_anchor is the fallback insertion point (end of the whole heading
    block) for a root subtree that's entirely new -- same as the old
    behavior for that case."""
    for n in nodes:
        already_present = node_present(n, existing_paths)
        if already_present:
            if n.path is not None:
                m = re.search(rf"^( *)\* \[.*?\]\({re.escape(n.path)}\)[^\n]*\n", dst_text, re.MULTILINE)
            else:
                # Path-less group bullet (see node_present): its own line
                # has no path to grep for, so find it through a child that
                # IS present and anchor new children under that same line
                # instead of re-emitting the group at the tail (#172).
                m = _find_group_line(dst_text, n, existing_paths)
            # Anchor after the LAST of this node's existing children (end of
            # its whole subtree), not right after its own line -- otherwise
            # a new child lands FIRST among its siblings regardless of where
            # en/SUMMARY.md actually places it. A real run hit this for
            # observability (score 80, just under the gate): "Log
            # Collectors" is the last child of "Logging" in en/SUMMARY.md,
            # but anchoring at the parent's own line put it first.
            child_anchor = _subtree_end(dst_text, m.end(), len(m.group(1))) if m else tail_anchor
            dst_text, new_child_anchor = insert_new_nodes(n.children, dst_text, existing_paths, lang, child_anchor)
            if child_anchor <= tail_anchor:
                # Text inserted at/before the tail anchor shifts it; text
                # inserted after it (a present path whose first occurrence
                # is in a later block) must not.
                tail_anchor += new_child_anchor - child_anchor
            continue
        file_missing = n.path is not None and not n.children and not (REPO_ROOT / lang / n.path).exists()
        if file_missing:
            continue
        fragment = render([n], lang, existing_paths)
        if not fragment:
            continue
        block = "\n".join(fragment) + "\n"
        dst_text = dst_text[:tail_anchor] + block + dst_text[tail_anchor:]
        tail_anchor += len(block)
    return dst_text, tail_anchor


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


def _heading_re(dst_heading, level="##"):
    return re.compile(rf"^{re.escape(level)} {re.escape(dst_heading)}\s*$", re.MULTILINE)


def heading_containing_paths(dst_text, paths, level="##"):
    """Heading text of the '<level> ' block in dst_text whose items link to
    the most of `paths` (first block wins a tie), or None if no block links
    to any. The by-content fallback for a heading whose cached translation
    no longer matches the file (see resolve_dst_heading)."""
    heading_pat = re.compile(rf"^{re.escape(level)} (.+)")
    blocks = []  # [heading, set(paths)] in document order
    for line in dst_text.splitlines():
        h = heading_pat.match(line)
        if h:
            blocks.append([h.group(1).strip(), set()])
        elif blocks:
            blocks[-1][1].update(re.findall(r"\]\(([^)]+)\)", line))
    best, best_hits = None, 0
    for heading, block_paths in blocks:
        hits = len(block_paths & paths)
        if hits > best_hits:
            best, best_hits = heading, hits
    return best


def resolve_dst_heading(heading, lang, heading_map, dst_text, present_paths, block_paths, level="##"):
    """-> (dst_heading, match) where match is the heading's line in dst_text
    (None when the block doesn't exist yet and must be created).

    present_paths: this run's forest paths already in dst_text (what we're
    about to add siblings of). block_paths: every path under `heading` in
    the en file (the whole block, not just this section's slice).

    Lookup order: (1) the cached translation from i18n-heading-map.json, if a
    '<level> <that>' line exists in the file; (2) otherwise the block that
    already CONTAINS this forest's present paths; (3) otherwise, no block
    yet: use the cached translation, or translate the heading now and cache
    it.

    (2) exists because the map and the file can drift apart: the map said
    "Quiz Collection" -> cn "测验集合", but cn/SUMMARY.md's heading had since
    become "## 测验合集" (a translate-sync re-translation rewrote the file
    without touching the map). Trusting only the map found no such heading
    and appended a second, brand-new "## 测验集合" block at EOF re-listing
    every ops quiz already present two lines above (issue #172, score 48).
    The paths under a heading never get translated, so they're the stable
    handle for the block. (2) also short-circuits the kiro-cli call in (3) for
    a heading the map has never seen but the file already has (e.g. en
    renamed "Basic" -> "Linux & Container" while cn still says "## 基础").

    When (2) hits, the map entry is repaired to the heading actually in the
    file so later runs hit (1) again -- but only if that block is also the
    one holding the most of the WHOLE en block's paths. The two can differ
    when en has since regrouped sections (en folded autoscaling/ under
    "Kubernetes Core Concepts"; jp still has a separate "## オートスケーリング"
    holding those pages): the autoscaling forest correctly lands beside its
    existing siblings, but recording "Kubernetes Core Concepts" ->
    "オートスケーリング" would then misplace every future core/ page."""
    dst_heading = heading_map.get(heading, {}).get(lang)
    if dst_heading is not None:
        m = _heading_re(dst_heading, level).search(dst_text)
        if m:
            return dst_heading, m
    found = heading_containing_paths(dst_text, present_paths, level)
    if found is not None:
        if found != dst_heading:
            counterpart = heading_containing_paths(dst_text, block_paths, level)
            if counterpart == found:
                print(f"::notice::sync-nav: heading map for '{heading}' ({lang}) said "
                      f"{dst_heading!r} but {lang}/ file has {found!r}; repairing map", file=sys.stderr)
                heading_map.setdefault(heading, {})[lang] = found
            else:
                print(f"::notice::sync-nav: '{heading}' ({lang}) items live under {found!r} "
                      f"but the block's counterpart looks like {counterpart!r}; anchoring under "
                      f"{found!r}, map left as {dst_heading!r}", file=sys.stderr)
        return found, _heading_re(found, level).search(dst_text)
    if dst_heading is None:
        dst_heading = translate_titles([heading], lang)[0]
        heading_map.setdefault(heading, {})[lang] = dst_heading
    return dst_heading, None


def sync_summary(section, lang, heading_map):
    en_path = REPO_ROOT / "en" / "SUMMARY.md"
    dst_path = REPO_ROOT / lang / "SUMMARY.md"
    prefixes = [f"{section}/", f"quizzes/{section}/", f"labs/{section}/"]

    blocks = extract_heading_blocks(en_path.read_text(encoding="utf-8").splitlines())
    dst_text = dst_path.read_text(encoding="utf-8")

    for heading, item_lines in blocks:
        forest = prune_missing(prune(parse_block(item_lines), prefixes), lang)
        if not forest:
            continue

        titled = []
        collect_titled(forest, titled)
        translated = translate_titles([n.title for n in titled], lang)
        for n, t in zip(titled, translated):
            n.title = t

        existing_paths = set(re.findall(r"\]\(([^)]+)\)", dst_text))
        forest_paths = {n.path for n in titled if n.path is not None}
        block_paths = set(re.findall(r"\]\(([^)]+)\)", "\n".join(item_lines)))

        dst_heading, m = resolve_dst_heading(
            heading, lang, heading_map, dst_text, forest_paths & existing_paths, block_paths)
        if m:
            # Tail-of-block fallback anchor, for a root subtree that's
            # entirely new (no already-present ancestor to splice after) --
            # same position the old tail-only-append logic always used. A
            # single '\n' (not '\n\n') before it continues the existing
            # bullet list without a blank-line gap in the middle --
            # CommonMark treats a blank line between two top-level list
            # items as splitting them into separate lists, which a real
            # quality-gate run flagged (a section like "Amazon EKS" shared
            # between two translate-backfill sections, e.g. eks-hybrid-nodes
            # and eks, got its list visibly split down the middle).
            rest = dst_text[m.end():]
            next_h = re.search(r"^## ", rest, re.MULTILINE)
            insert_at = m.end() + (next_h.start() if next_h else len(rest))
            before = dst_text[:insert_at].rstrip("\n") + "\n"
            # No leading blank line when there's nothing after insert_at --
            # this heading is the last one in the file, so the "\n\n"
            # separator (needed to keep this block visually apart from the
            # NEXT heading) would otherwise land at EOF as a stray trailing
            # blank line, which a real run got dinged for (score 80).
            tail_content = dst_text[insert_at:].lstrip("\n")
            after = ("\n" + tail_content) if tail_content else ""
            dst_text = before + after
            dst_text, _ = insert_new_nodes(forest, dst_text, existing_paths, lang, len(before))
        else:
            fragment_lines = render(forest, lang, existing_paths)
            if not fragment_lines:
                continue
            dst_text = dst_text.rstrip("\n") + f"\n\n## {dst_heading}\n\n" + "\n".join(fragment_lines) + "\n"

    dst_path.write_text(dst_text, encoding="utf-8")


def _readme_link_exists(path, lang):
    return (REPO_ROOT / lang / path.lstrip("./")).exists()


def _filter_readme_line(line, lang):
    """README.md ToC lines look like 'N. [Title](path) | [Quiz](qpath) |
    [Lab](lpath)'. Drop the whole line if its primary (first) link's target
    doesn't exist in this lang (translation failure) -- an entry with no
    content to point to isn't useful. Otherwise drop just the Quiz/Lab
    segments whose own target is missing."""
    links = list(re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line))
    if not links:
        return line
    if not _readme_link_exists(links[0].group(2), lang):
        return None
    for m in links[1:]:
        if not _readme_link_exists(m.group(2), lang):
            line = line.replace(f" | {m.group(0)}", "")
    return line


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
    # Stop at the next '## ' too: the LAST '### ' block of the ToC is
    # followed by '## Lab Guides', not another '### ', and stopping only on
    # '### ' would copy that heading and its prose into the locale's ToC.
    while j < len(en_lines) and not en_lines[j].startswith(("### ", "## ")):
        body.append(en_lines[j])
        j += 1

    filtered_body = []
    for ln in body:
        if not ln.strip():
            filtered_body.append(ln)
            continue
        kept = _filter_readme_line(ln, lang)
        if kept is not None:
            filtered_body.append(kept)
    body = filtered_body

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

    # Match "already synced" by a body link path, not the heading text.
    # Paths never get translated, so they're stable across runs -- unlike
    # the heading, which is re-translated fresh by translate_titles() each
    # time a section is (re-)synced and can come out worded differently
    # from an earlier pass (e.g. Phase 0 scaffolding left "### AI/ML"
    # untranslated while a later backfill run produced "人工智能/机器学习").
    # Matching on heading text alone made that mismatch invisible, so
    # sync_readme() never recognized already-scaffolded content and kept
    # duplicating it at the file tail on every run -- confirmed live across
    # cn/jp/es for 7-10 sections each.
    body_paths = re.findall(r"\]\(([^)]+)\)", "\n".join(body))
    if body_paths and body_paths[0] in dst_path_text:
        return  # already synced for this lang

    # Insert new blocks right before the heading that follows "## Table of
    # Contents" (mirroring sync_summary's tail-of-block insertion) so a
    # section's first-ever README sync lands inside the ToC, not appended
    # after "## License" at the absolute end of the file.
    #
    # Same heading-drift exposure as sync_summary (#172): the map has never
    # held "Table of Contents", so this used to translate it fresh and, on any
    # wording other than the file's "## 目录"/"## 目次"/"## Tabla de contenido",
    # silently fell through to the append-at-EOF branch below. Resolve it the
    # same way -- the ToC block is the one already holding the other
    # sections' entries (paths are identical between en and the locale).
    en_toc_heading = "Table of Contents"
    en_toc_paths, in_toc = set(), False
    for ln in en_lines:
        if ln.startswith("## "):
            in_toc = ln.rstrip() == f"## {en_toc_heading}"
        elif in_toc:
            en_toc_paths.update(re.findall(r"\]\(([^)]+)\)", ln))
    dst_paths = set(re.findall(r"\]\(([^)]+)\)", dst_path_text))
    dst_toc_heading, m = resolve_dst_heading(
        en_toc_heading, lang, heading_map, dst_path_text, en_toc_paths & dst_paths, en_toc_paths)
    if m:
        rest = dst_path_text[m.end():]
        next_h = re.search(r"^## ", rest, re.MULTILINE)
        insert_at = m.end() + (next_h.start() if next_h else len(rest))
        before = dst_path_text[:insert_at].rstrip("\n") + "\n\n"
        after = "\n" + dst_path_text[insert_at:].lstrip("\n")
        dst_path_text = before + f"### {dst_heading}\n" + "\n".join(translated_body) + after
    else:
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
