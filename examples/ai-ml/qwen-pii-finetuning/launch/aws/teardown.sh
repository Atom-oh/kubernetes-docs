#!/usr/bin/env bash
set -euo pipefail
umask 077
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
INVENTORY=${1:-"$PACKAGE_ROOT/results/resource-inventory.json"}
if (($#)); then shift; fi
exec "${PYTHON:-python3}" "$SCRIPT_DIR/lifecycle.py" teardown "$INVENTORY" "$@"
