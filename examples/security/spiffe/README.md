# SPIFFE/SPIRE examples

Reviewed September 13, 2026: SPIRE 1.15.3, hardened umbrella chart 0.30.2, CRD chart 0.6.1, Controller Manager 0.7.0, chart CSI image 0.2.7 (current standalone CSI 0.2.13 docs also checked), and go-spiffe 2.8.1. These files represent distinct lab/HA/integration paths; do not apply the whole directory blindly.

| File | Use and prerequisites |
|---|---|
| `lab-values.yaml` | Single-server SQLite lab. Install spire-crds first, prepare StorageClass/hostPath/CSI/kubelet access, and verify the API-server CA can validate the actual kubelet serving certificate. Broad default/test/OIDC identities are disabled. |
| `ha-values.yaml` | Three servers with shared PostgreSQL, raw `spire-database` Secret key `password` delivered through `PGPASSWORD`, `spire-database-ca` ConfigMap key `ca.crt`, verify-full TLS, and matching anti-affinity. The chart password interpolation is disabled: no password enters the rendered JSON/DSN. Do not escape/encode the Secret value; coordinate DB rotation with Pod restart. Prepare database/DNS/CA/Secret/storage and test failover separately. |
| `workload.yaml` | Namespace, ServiceAccount, explicit ClusterSPIFFEID and example Pod. Replace the application image with a real Workload API consumer. CSI mounts the API socket directory, not certificate/key files. Control who can create Pods using the selected SA or alter matching labels. |
| `envoy.yaml` | Complete loopback-bound demonstration listener, HTTP filters, SPIRE SDS cluster, required client certificate and exact allowed peer URI. Register both server/client identities and mount the socket for the actual Envoy process. This was schema-validated, not run as a live proxy. |
| `federation-https-web.yaml` | A real Web-PKI HTTPS endpoint is required. For https_spiffe, additionally obtain a trusted initial bundle and verify endpointSPIFFEID; a URL alone is insufficient. Configure each direction and peer authorization separately. |
| `aws-pca-plugin.conf` | Plugin fragment to merge into a complete server configuration. The external CA signs SPIRE's intermediate; the server retains leaf-signing responsibility. Select a compatible real CA and template. |
| `aws-pca-policy.json` | Scope required PCA operations to the real CA ARN. Replace placeholder account/CA ID; use workload identity instead of static keys. No AWS policy/deployment test was performed. |

Native checks: SPIRE server/agent config validation; nine SPIFFE-ID cases, five X.509-SVID cases, and six JWT cases with go-spiffe; lab/HA chart rendering and exact Secret/volume/label contracts; six synthetic PostgreSQL password cases with actual SPIRE configuration/lib/pq parsing (quotes, backslashes, whitespace and dollar signs preserved); workload/federation schemas; Envoy 1.37 protobuf validation and source review of exact URI SAN matching. No cluster installation, node/workload attestation, DB connection, AWS issuance, federation fetch, or runtime TLS handshake was executed. Synthetic private keys stayed in memory/local audit fixtures and are not published.

Important distinctions: chart identity `jwtTTL` versus CRD `jwtTtl`; API socket delivery versus certificate-file delivery; signature/audience/expiry validation versus replay protection; importing a trust bundle versus rotating a CA private key. The chapter covers X.509/JWT paths and separately identifies the Incubating WIT-SVID specification.

PostgreSQL driver source: [SPIRE sqlstore](https://github.com/spiffe/spire/blob/v1.15.3/pkg/server/datastore/sqlstore/postgres.go), [lib/pq PGPASSWORD parsing](https://github.com/lib/pq/blob/v1.12.3/connector.go).

- [Korean guide](../../../ko/security/12-spiffe-spire.md)
- [English guide](../../../en/security/12-spiffe-spire.md)
