# Runtime security examples

Reviewed on September 13, 2026: Falco 0.44.1/chart 9.1.0, Falcosidekick 2.35.0 explicitly pinned with chart 0.14.0, Tetragon 1.7.1. Choose compatible Linux kernels, BTF, architectures, privileges, and node types before installation.

| File | Use and prerequisite |
|---|---|
| `falco-values.yaml`, `falco-rules.yaml` | Modern eBPF profile and self-contained custom rules. Container fields need the bundled container plugin. Requires the separately installed Sidekick service and Prometheus Operator CRD. No deprecated evt.dir or camelCase Falco config. |
| `falcosidekick-values.yaml` | Explicit image 2.35.0; existing credential Secret `falcosidekick-output-credentials` in namespace falco. Provide approved output environment variables securely; do not put credentials or literal shell placeholders into values. AWS uses workload identity, config.aws, and scoped permissions. |
| `tetragon-values.yaml` | Process credential/namespace metadata. Verify operator/CRDs and actual kernel support. |
| `tetragon-file-observe.yaml` | Namespaced observation using security_file_permission's permission mask, not security_file_open's nonexistent flags argument. Does not cover every mmap/truncate action. |
| `tetragon-network-observe.yaml` | Selected TCP port connection attempts, not proof of malicious traffic, DNS contents, or policy denial. |
| `audit-policy.yaml` | Self-managed API server only; Metadata for Secrets/token requests. EKS audit policy is managed by AWS. |
| `restricted-pod.yaml` | Complete Pod shape with explicit security controls; replace the placeholder application image and prepare demo-app namespace. Writable volumes remain writable. |
| `collect-evidence.sh` | Authorized API reads of one Pod into a new private directory with checksums. No quarantine, memory dump, or filesystem snapshot. Output may contain secrets/personal data. |
| `alert-queries.promql` | Actual Sidekick received-event metric; verify scrape labels and counters separately from notification-delivery metrics. |

Local checks compiled two Falco rules with the actual binary/container plugin while disabling all runtime engines and using nodriver; four configuration-schema cases included rejected old settings. Three tetra stdin filters, two CRD policies, the Pod OpenAPI schema, three chart renders, two ServiceMonitor links, and four evidence-script subprocess cases passed. No real cluster/API reads, kernel hook attachment, enforcement, event capture, GuardDuty coverage, AWS calls, or external notifications were executed.

Falco's tarball came from its official HTTPS distribution endpoint; a SHA-256 was recorded, but no independent published checksum was available at the attempted checksum URLs. Tetra and all Helm chart archives matched their published checksums.

See the [Korean guide](../../../ko/security/08-runtime-security.md), [English guide](../../../en/security/08-runtime-security.md), and `docs/reviews/2026-09-11/runtime-security-validation.json` for scope and evidence.
