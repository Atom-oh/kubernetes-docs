#!/usr/bin/env bash
# Runs `npm run docs:build` and writes peak memory, wall time and disk use to
# the GitHub step summary, so build resource changes are visible on every run.
set -euo pipefail

label="${1:-full}"
samples="$(mktemp)"
df --output=avail -B1M . | tail -1 > "$samples"
start_avail="$(cat "$samples")"

# Sample free disk every 5 s to catch the peak (staging + merged output).
( while true; do df --output=avail -B1M . | tail -1 >> "$samples"; sleep 5; done ) &
sampler=$!
trap 'kill "$sampler" 2>/dev/null || true' EXIT

if [ -x /usr/bin/time ]; then
  /usr/bin/time -v -o build-time.txt npm run docs:build
  max_rss_mb=$(( $(awk -F: '/Maximum resident set size/ {gsub(/ /, "", $2); print $2}' build-time.txt) / 1024 ))
  elapsed="$(awk -F': ' '/Elapsed \(wall clock\)/ {print $2}' build-time.txt)"
else
  started=$SECONDS
  npm run docs:build
  max_rss_mb="n/a"
  elapsed="$(( SECONDS - started ))s"
fi
kill "$sampler" 2>/dev/null || true

min_avail="$(sort -n "$samples" | head -1)"
dist_mb="$(du -sm .vitepress/dist | cut -f1)"
{
  echo "### Docs build resources (${label})"
  echo ""
  echo "| Metric | Value |"
  echo "| --- | --- |"
  echo "| Peak RSS of the largest process | ${max_rss_mb} MB |"
  echo "| Wall clock | ${elapsed} |"
  echo "| Peak disk used during the build | $(( start_avail - min_avail )) MB |"
  echo "| Built site size | ${dist_mb} MB |"
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"
