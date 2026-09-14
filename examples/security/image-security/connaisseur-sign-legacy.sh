#!/usr/bin/env bash
# Compatibility producer for Connaisseur 3.12.0, using Cosign 3.1.3 explicitly.
# Separate from secure-build.yaml, which keeps the default Cosign 3 bundle format.
set -euo pipefail
: "${IMAGE_REF:?Set an immutable image digest reference}"
: "${COSIGN_PRIVATE_KEY:?Set the approved signing key path or KMS URI}"
: "${COSIGN_PUBLIC_KEY:?Set the corresponding approved verification key}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[[ "$IMAGE_REF" =~ @sha256:[a-f0-9]{64}$ ]]
cosign sign --yes --key "$COSIGN_PRIVATE_KEY" \
  --new-bundle-format=false --registry-referrers-mode=legacy \
  --signing-config "$script_dir/connaisseur-signing-config.json" "$IMAGE_REF"
cosign verify --key "$COSIGN_PUBLIC_KEY" \
  --new-bundle-format=false "$IMAGE_REF"
