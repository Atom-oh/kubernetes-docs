#!/usr/bin/env bash
# Reference setup for an existing Vault PKI mount and Kubernetes auth mount.
# Requires approved Vault identity, TLS trust, and separately configured TokenReview access.
set -euo pipefail
vault policy write cert-manager-demo-app vault-policy.hcl
vault write pki/roles/example-role \
  allowed_domains=example.com allow_subdomains=true \
  allow_bare_domains=false allow_any_name=false max_ttl=72h
vault write auth/kubernetes/role/cert-manager-demo-app \
  bound_service_account_names=vault-issuer \
  bound_service_account_namespaces=demo-app \
  audience=vault://demo-app/vault-pki \
  policies=cert-manager-demo-app ttl=1m
