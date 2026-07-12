#!/usr/bin/env bash
# Translate one markdown file from en/ into cn/jp/es using kiro-cli (headless).
#
# Usage: translate.sh <src_en_path> <dst_path> <lang_code>
#   lang_code: cn | jp | es
#
# kiro-cli's non-interactive `chat` ignores stdin and reads only the prompt
# arg, so the doc body can't be piped in (128KiB argv limit anyway, and some
# docs here are ~137KB). Instead we grant fs_read/fs_write and tell it to
# read <src_en_path> and write <dst_path> itself.
#
# Exits 0 on a validated translation, 1 otherwise. On failure, prints
# "FAILED: <dst_path>" to stderr (single short line — safe for concurrent
# `>>` appends from parallel workers at this fan-out width, ~2 -- the
# kubernetes-docs-claude-arm runner pod only requests 1800m CPU/3500Mi).
set -euo pipefail

SRC="$1"
DST="$2"
LANG="$3"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$LANG" in
  cn) LANG_NAME="Simplified Chinese"; DATE_LABEL="最后更新" ;;
  jp) LANG_NAME="Japanese"; DATE_LABEL="最終更新" ;;
  es) LANG_NAME="Spanish"; DATE_LABEL="Última actualización" ;;
  *) echo "translate.sh: unknown lang_code '$LANG' (want cn|jp|es)" >&2; exit 1 ;;
esac

if [ -f "$REPO_ROOT/$DST" ]; then
  echo "skip (exists): $DST"
  exit 0
fi

PROMPT="Read the file at $SRC (relative to the current directory, which is the repo root) and write its $LANG_NAME translation to $DST.

Rules:
- Translate prose only. Keep all markdown structure, headings, tables, code
  blocks, YAML, shell commands, and link/image paths EXACTLY as in the
  source (do not translate inside code fences, do not change any file path
  or URL).
- Keep Kubernetes/AWS technical terms in English (Pod, Deployment, Service,
  EKS, etc.); you may add the local-language term in parentheses on first
  use only.
- Translate the header date field's label to $LANG_NAME (e.g. use \"$DATE_LABEL\"
  in place of \"Last Updated\"/\"마지막 업데이트\"), but keep the date value itself
  unchanged.
- If the source is a quiz file, translate \"Show Answer\", \"Answer:\", and
  \"Explanation:\" (or their Korean equivalents) into $LANG_NAME, keeping the
  <details><summary> HTML structure intact.
- Write ONLY the translated file to $DST. Do not modify $SRC or any other file."

CELL="$(mktemp -d)"
trap 'rm -rf "$CELL"' EXIT

run_once() {
  # 600s, not 300s: kiro-cli writes large docs (30-45KB+) via several
  # sequential fs_write chunk calls rather than one shot, and a real run
  # showed that consistently taking 4-5 minutes per attempt for the biggest
  # files in this repo (basics/04, 05 are 44-46KB) -- 300s cut those off
  # mid-write on both the first attempt AND the retry, failing every large
  # file in the section.
  ( cd "$REPO_ROOT" && env -i PATH="$PATH" HOME="$CELL" LANG="${LANG_ENV:-C.UTF-8}" \
      KIRO_API_KEY="${KIRO_API_KEY:-}" \
      timeout 600 kiro-cli chat "$PROMPT" --model claude-haiku-4.5 \
      --no-interactive --trust-tools=fs_read,fs_write --wrap never )
}

validate() {
  python3 "$REPO_ROOT/scripts/validate-translation.py" "$REPO_ROOT/$SRC" "$REPO_ROOT/$DST"
}

mkdir -p "$REPO_ROOT/$(dirname "$DST")"

if run_once && [ -s "$REPO_ROOT/$DST" ] && validate; then
  echo "ok: $DST"
  exit 0
fi

echo "::warning::first attempt failed/invalid for $DST, retrying once" >&2
rm -f "$REPO_ROOT/$DST"

if run_once && [ -s "$REPO_ROOT/$DST" ] && validate; then
  echo "ok (retry): $DST"
  exit 0
fi

echo "FAILED: $DST" >&2
exit 1
