# Kubescape examples

Reviewed on September 13, 2026 with CLI 4.0.14 and Operator chart 1.40.4. The chart renders scanner image 4.0.13. Policy snapshots have their own hashes; tool and policy versions are separate inputs.

Run commands from this directory after obtaining a checksum-verified Kubescape binary. `scan-manifests.sh` requires an existing local file and returns the scanner exit code. It normalizes the input to an absolute path, creates a fresh private cache and empty kubeconfig, clears inherited in-cluster discovery variables, disables host scans and inline exceptions, and preserves nonzero scanner errors. --keep-local alone is not cluster isolation. The bundled NSA policy and control inputs are an Apache-2.0 snapshot from Kubescape's public artifact download; see `policies/provenance.json` and `policies/LICENSE`.

```bash
# Pass the actual absolute binary path if it is not on PATH.
KUBESCAPE_BIN=/absolute/path/to/kubescape bash scan-manifests.sh secure-pod.yaml report.json
# Expected failure: synthetic insecure fixture, never apply it to a cluster.
KUBESCAPE_BIN=/absolute/path/to/kubescape bash scan-manifests.sh insecure-pod.yaml findings.json
```

| File | Purpose and prerequisites |
|---|---|
| `scan-manifests.sh` | Local policy/input, isolated empty kubeconfig, inline exceptions disabled, keep-local, minimum compliance 90 and high-severity gate. Missing input or scan errors fail. Override thresholds only as an explicit policy decision. |
| `secure-pod.yaml`, `insecure-pod.yaml` | Synthetic input fixtures. The insecure Pod is only for scanning. The secure Pod's app image is a placeholder and local results are not a deployment certification. |
| `policies/` | Tested NSA/control-input snapshot, license and SHA provenance. Review policy changes before replacing it. |
| `no-exceptions.json`, `exceptions.json` | CLI JSON arrays. The narrow example uses alertOnly; it acknowledges a finding without fixing it. It is not the default gate's exception policy. |
| `security-exception.yaml` | In-cluster kubescape.io/v1beta1 SecurityException with namespace/resource match and alert_only. Requires installed CRD/controller/RBAC; expiry is illustrative and must be reviewed before use. |
| `operator-values.yaml` | Configuration-only profile with optional metrics, node/image/runtime/remediation disabled, and no cluster-wide Secret reads. Prepare the correct gp3 StorageClass/CSI driver and inspect all rendered RBAC. |
| `podmonitor.yaml` | Selects the actual exporter Pod's named metrics port 8080. Requires Prometheus Operator and matching Prometheus PodMonitor selection. The chart Service's port is unnamed. |
| `github-actions.yaml` | Example workflow to copy to `.github/workflows/kubescape.yaml`. The project must first produce `k8s/rendered.yaml`; missing input fails. Binary/action revisions are pinned; reporting artifacts do not override failure status. |

Native local results: insecure compliance 55 / risk score 62.5; secure compliance 95 / risk score 6.818182. Minimum threshold 55 passed and 56 failed for the insecure fixture. A high-severity gate failed the insecure fixture and passed the secure one. Deprecated `--fail-threshold 0` alone returned zero despite failed findings, so the workflow does not use it. The JSON summary is under `summaryDetails`, not top-level riskScore/complianceScore.

Local checks covered CLI scans, exception/exclusion behavior, shell gate, chart rendering, SecurityException OpenAPI, PodMonitor target wiring, and actionlint. They did not install an Operator, run a node/cluster scan, pull images, scan a vulnerability database, submit to SaaS, or send notifications. CRD schema checks do not execute CEL or controller policy.

- [Korean guide](../../../ko/security/11-kubescape.md)
- [English guide](../../../en/security/11-kubescape.md)
