#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
OUTPUT=${1:-"$PACKAGE_ROOT/generated/source.tar.gz"}
STAGING=$(mktemp -d /tmp/qwen-source.XXXXXX)

cleanup() {
  rm -rf "$STAGING"
}
trap cleanup EXIT

mkdir -p "$STAGING/src" "$STAGING/config" "$(dirname "$OUTPUT")"
cp "$PACKAGE_ROOT"/src/*.py "$STAGING/src/"
cp "$PACKAGE_ROOT/config/experiment.yaml" "$STAGING/config/experiment.yaml"
cp "$PACKAGE_ROOT/requirements.lock" "$STAGING/requirements.lock"
cp "$PACKAGE_ROOT/requirements.lock" "$STAGING/requirements.txt"
tar -czf "$OUTPUT" -C "$STAGING" .
printf '%s\n' "$OUTPUT"
