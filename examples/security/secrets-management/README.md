# Secrets management examples

These are documentation and local-validation examples, not a complete cluster
installation. Replace example account IDs, OIDC IDs, paths and application images.
No production keys or credentials belong in this directory.

- ESO: chart/application 2.10.0. The IRSA store references
  `production/external-secrets-reader`. Pod Identity is a separate alternative
  attached to `external-secrets/external-secrets-controller`, without a
  `serviceAccountRef` on the store.
- The IAM policy reads named secrets/parameters. A customer-managed KMS key also
  needs a correctly constrained decrypt grant and key policy. No wildcard
  `ListSecrets` discovery permission is included.
- Vault: chart 0.34.1 with explicit server/agent 2.1.0 overrides. TLS certificates,
  initialization, unseal, Raft membership, audit activation, storage, availability
  and recovery are separate prerequisites. Rendering does not prove readiness.
- Vault Agent writes JSON. The application parses this file; it must not source
  secret values as shell code. File refresh does not automatically reload an app.
- Flux references an existing private age key Secret. The Argo CD plugin file
  belongs inside a configured CMP sidecar; it is not a resource to apply.

The chapter distinguishes provider credential rotation, controller key renewal,
file re-encryption, Kubernetes Secret synchronization and application reload.
