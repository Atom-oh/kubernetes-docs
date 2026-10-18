#!/usr/bin/env bash
# Translate one English Markdown file via Bedrock Mantle GPT-6 Luna.
# Usage: translate.sh <src_en_path> <dst_path> <cn|jp|es>
# Exit 78 stops the batch for unavailable models or IAM credentials.
set -euo pipefail

SRC="$1"
DST="$2"
LANG_CODE="$3"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "$LANG_CODE" in
  cn|jp|es) ;;
  *) echo "Unknown language: $LANG_CODE" >&2; exit 1 ;;
esac
if [ -f "$REPO_ROOT/$DST" ]; then
  echo "skip (exists): $DST"
  exit 0
fi

for ATTEMPT in 1 2; do
  status=0
  # Keep the runner's AWS credential chain, including EKS Pod Identity.
  python3 "$REPO_ROOT/scripts/bedrock-translation.py" document \
    "$REPO_ROOT/$SRC" "$REPO_ROOT/$DST" "$LANG_CODE" || status=$?
  if [ "$status" -eq 78 ]; then
    rm -f "$REPO_ROOT/$DST"
    exit 78
  fi
  if [ "$status" -eq 0 ] && [ -s "$REPO_ROOT/$DST" ] && \
      python3 "$REPO_ROOT/scripts/validate-translation.py" "$REPO_ROOT/$SRC" "$REPO_ROOT/$DST"; then
    echo "ok: $DST (attempt $ATTEMPT)"
    exit 0
  fi
  rm -f "$REPO_ROOT/$DST"
  echo "::warning::translation attempt $ATTEMPT failed/invalid for $DST" >&2
done

echo "FAILED: $DST" >&2
exit 1
