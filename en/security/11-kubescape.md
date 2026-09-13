# Security Posture Management with Kubescape

> **Last Updated**: September 13, 2026
> **Validation baseline**: CLI 4.0.14 and Operator chart 1.40.4. The chart's scanner image is 4.0.13, separate from the CLI. Policy hashes are recorded in the example directory.

Kubescape evaluates Kubernetes configuration and selected image/runtime data. **Passing a scan is not a security guarantee or compliance certification; unavailable coverage must be identified separately.** This guide was checked with local YAML, policy bundles, the actual CLI, and chart rendering. No live cluster scan, node-agent installation, registry image/DB scan, or SaaS submission was performed.

<span id="what-kubescape-solves"></span>
<span id="cncf-sandbox-project"></span>
<span id="comparison-with-similar-tools"></span>
<span id="kubescape-architecture"></span>

## Overview

Kubescape joined CNCF on December 13, 2022 and became **Incubating on January 13, 2025**. The former Sandbox description and stale tool-maturity comparison table are not current guidance.

The CLI performs explicit file or cluster scans; the Operator provides continuous/scheduled behavior according to enabled capabilities. Configuration controls, RBAC analysis, image CVEs, and runtime detection have different scopes. Compare kube-bench's node/CIS checks, Polaris workload policies, and Trivy image/configuration scans against versioned requirements rather than broad superiority claims.

![Kubescape inputs, controls, separate results and optional outputs](../.gitbook/assets/en-security-11-kubescape-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-0.html)


<span id="linux-and-macos"></span>
<span id="windows"></span>
<span id="container-image"></span>
<span id="helm-operator-installation-in-cluster"></span>
<span id="operator-configuration-values"></span>
<span id="kubescape-cloud-saas"></span>

## Installation

### CLI Installation

Download the matching OS/CPU asset from the [official 4.0.14 release](https://github.com/kubescape/kubescape/releases/tag/v4.0.14) and verify its checksum. This Linux AMD64 example pins the reviewed archive hash; ARM64 needs a different archive/hash.

```bash
curl --fail --location \
  https://github.com/kubescape/kubescape/releases/download/v4.0.14/kubescape_4.0.14_linux_amd64.tar.gz \
  --output kubescape.tgz
printf '%s  %s\n' '1d253b70f88e80b74f68af73ccd422f897381468300be7cc486fdd656d907a40' kubescape.tgz | sha256sum --check
tar -xzf kubescape.tgz kubescape
./kubescape version
./kubescape scan --help
```

Check the actual package version when using Homebrew/Krew or other installers. Limit installer execution and kubeconfig exposure to the intended scope. Omitting a file target from `kubescape scan` can scan the current cluster.

### Helm Operator Installation

Download the [example directory](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/kubescape) and run these commands from `examples/security/kubescape`. The profile focuses on posture checks and metrics, explicitly disabling node/image/runtime/remediation capabilities.

```bash
helm repo add kubescape https://kubescape.github.io/helm-charts
helm repo update kubescape
helm upgrade --install kubescape kubescape/kubescape-operator \
  --version 1.40.4 --namespace kubescape --create-namespace \
  --values operator-values.yaml
```

```yaml
clusterName: documentation-cluster
defaultFrameworks:
- nsa
- mitre
capabilities:
  continuousScan: enable
  configurationScan: enable
  nodeScan: disable
  nodeSbomGeneration: disable
  vulnerabilityScan: disable
  relevancy: disable
  runtimeObservability: disable
  networkPolicyService: disable
  networkEventsStreaming: disable
  runtimeDetection: disable
  nodeProfileService: disable
  admissionController: disable
  httpDetection: disable
  seccompProfileService: disable
  prometheusExporter: enable
  riskAcceptance: disable
  remediation: disable
  manageWorkloads: disable
global:
  enableClusterWideSecretAccess: false
persistence:
  storageClass: gp3
kubescapeScheduler:
  scanSchedule: 0 8 * * *
```


Prepare the gp3 StorageClass/CSI driver and verify namespaces, RBAC, CRDs, and aggregated API availability. EKS Auto Mode and ordinary EBS CSI StorageClasses can use different provisioners. Helm rendering does not establish installation, persistence, or scanning success.

credentials.cloudSecret is an existing Secret name, not an account ID. Configure and authorize the backend/account/accessKey/data scope explicitly when SaaS is needed. CLI --submit requests submission; local examples use --keep-local and an isolated cache. Enable node/runtime features separately after checking host privileges, kernels/BTF, and supported node types.

<span id="nsa-cisa-kubernetes-hardening-guide"></span>
<span id="cis-kubernetes-benchmark"></span>
<span id="mitre-att-ck-framework"></span>
<span id="framework-comparison"></span>

## Security Frameworks

### Frameworks and Controls

Framework names and control counts depend on the policy bundle. The reviewed download contained NSA, MITRE, SOC2, ArmoBest, DevOpsBest, AllControls, and versioned CIS frameworks. NSA contained 26 controls, not all applicable to a local Pod.

```bash
kubescape list frameworks
kubescape list controls --framework NSA
kubescape list controls --framework NSA --search container
```

Example names in the reviewed bundle include cis-v1.12.0 and cis-eks-t1.8.0. Do not assume cis-v1.23 or cis is a universal alias. Policy updates change coverage/scores; record binary versions and policy hashes together.

| Control ID | Reviewed bundle name |
|---|---|
| C-0004 | Resources memory limit and request |
| C-0009 | Resource limits |
| C-0013 | Non-root containers |
| C-0016 | Allow privilege escalation |
| C-0034 | Automatic mapping of service account |
| C-0035 | Administrative Roles |
| C-0036 | Validate admission controller (validating) |
| C-0039 | Validate admission controller (mutating) |
| C-0057 | Privileged container |

C-0036/0039 are not wildcard-RBAC/risky-ServiceAccount controls. Severity also depends on the bundle: the reviewed C-0057 was High, not universally Critical.

### Custom Frameworks

--use-from loads a local policy object. A YAML name and unresolved list of control IDs is not necessarily an executable framework. The example policies/nsa.json is the tested bundle with license, provenance, and SHA records. Author/test new Rego controls with current CLI features such as kubescape policy init and kubescape policy test, then review organizational requirements.

<span id="scanning-pipeline-flow"></span>
<span id="cluster-scanning"></span>
<span id="specific-control-scanning"></span>
<span id="yaml-and-helm-manifest-scanning-shift-left"></span>
<span id="image-vulnerability-scanning"></span>
<span id="rbac-visualization-and-analysis"></span>

## CLI Scanning

![Kubescape input, evaluation, score fields and report formats](../.gitbook/assets/en-security-11-kubescape-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-1.html)


### Cluster versus Local Input

```bash
# This accesses the current cluster; check authorization and scope first.
kubescape scan framework nsa --include-namespaces production
# Explicit local-file scan:
kubescape scan framework nsa secure-pod.yaml \
  --use-from policies/nsa.json --controls-config policies/controls-inputs.json \
  --exceptions no-exceptions.json --keep-local \
  --format json --output report.json
```

--format/-f selects the format; --output/-o names the file. `-o json > report.json` does not select JSON output. Version 4.0.14 supports JSON/SARIF/HTML/PDF/JUnit/gitlab-sast and other formats; choose the one the receiving tool expects.

Render Helm/Kustomize locally before scanning to make effective values explicit. Local checks do not reproduce API defaulting, admission, IAM authorization, or network behavior. --include-api-audit, --custom-framework, and --sort-by were unknown in the reviewed CLI. Do not present scan rbac as a separate current subcommand.

### Actual Local Results

insecure-pod.yaml is a **synthetic scan fixture, not a deployment recipe**. It uses real privileged/runAsUser fields rather than nonexistent runAsRoot. secure-pod.yaml also demonstrates configuration only; replace its application image before any real deployment.

| Local input | Compliance | score | Result |
|---|---:|---:|---|
| Insecure Pod | 55 | 62.5 | High failures |
| Secure Pod | 95 | 6.818182 | High gate passes; not every control passes |

These values apply to the attached policy snapshot and one local Pod. They do not measure cluster security or exploitability.

### Image and RBAC Analysis

Request image scanning explicitly with kubescape scan image IMAGE. CLI 4.0.14 uses Grype 0.104.1 and Syft 1.42.3 in its source dependencies; the Operator kubevuln component is separately versioned. Verify registry credentials, platform, database freshness, and scan errors. Host scanning differs from image scanning and can require additional host access/resource creation.

RBAC controls evaluate collected Roles/Bindings within authorized API scope. A RoleBinding grants access within its namespace, not every namespace. Static analysis does not by itself establish unused permissions, external IAM authorization, or every effective access path.

<span id="continuous-scanning-architecture"></span>
<span id="operator-components"></span>
<span id="scheduled-scanning-configuration"></span>
<span id="vulnerability-scanning-integration"></span>
<span id="runtime-threat-detection-node-agent-with-ebpf"></span>
<span id="kubernetes-api-attack-detection"></span>

## Operator Mode (In-Cluster)

![Kubescape operator coordination and aggregated storage API](../.gitbook/assets/en-security-11-kubescape-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-2.html)


Use the chart's kubescapeScheduler.scanSchedule and requestBody.commands[].args.scanV1 fields. defaultFrameworks supplies defaults for requests without targets; explicit targetNames wins. An arbitrary ConfigMap with scanSchedule does not establish that a controller consumes it.

spdx.softwarecomposition.kubescape.io/v1beta1 results are served by the storage component's **aggregated API**, not all ordinary CRDs. Separate CRDs include SecurityException, ClusterSecurityException, and OperatorCommand. Discover actual names/scopes before querying results.

```bash
kubectl get apiservices v1beta1.spdx.softwarecomposition.kubescape.io
kubectl api-resources --api-group=spdx.softwarecomposition.kubescape.io
kubectl get pods,pvc -n kubescape
```

Do not present the old ScanSchedule, VulnerabilityScanConfig, ThreatDetectionConfig, AcceptedRisk, and ScanConfiguration examples as APIs installed by this chart. Node-agent profiles/detection must use actual APIs/capabilities for the chosen image. Enabled configuration is not proof of healthy collection or detection on all nodes.

<span id="risk-score-calculation"></span>
<span id="severity-levels"></span>
<span id="viewing-risk-scores"></span>
<span id="prioritization-strategy"></span>

## Risk Scoring

summaryDetails.complianceScore and summaryDetails.score are different aggregates. Higher compliance indicates more checks passing; risk score is neither the same value nor simply 100-compliance. Do not present invented severity weights or response SLAs as a universal Kubescape formula.

```bash
jq '{compliance: .summaryDetails.complianceScore, risk: .summaryDetails.score,
     failed: [.summaryDetails.controls[] | select(.status == "failed") | {controlID, name, severity}]}' report.json
```

Use --compliance-threshold as a **minimum compliance score**, and --severity-threshold for failed-control severity. A local score of 55 returned exit 0 at threshold 55 and exit 1 at 56. --min-severity filters output; it does not replace current gate calculations.

**Version 4.0.14 accepts --fail-threshold as a deprecated compatibility flag but ignores its value.** The test returned exit 0 with failed findings when only --fail-threshold 0 was supplied. Distinguish that inert flag from still-processed options such as --scan-images/--skip-controls and genuinely unknown flags.

<span id="ci-cd-integration-workflow"></span>
<span id="github-actions-workflow"></span>
<span id="gitlab-ci-cd-integration"></span>
<span id="jenkins-pipeline-integration"></span>
<span id="threshold-based-gates"></span>

<span id="cicd-integration"></span>

## CI/CD Integration

![CI gates based on minimum compliance, severity and command exit](../.gitbook/assets/en-security-11-kubescape-3.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-3.html)


### Shared Security Gate

```bash
#!/usr/bin/env bash
# Scan explicit local manifests. Never falls back to the current cluster.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  printf 'Usage: %s LOCAL_MANIFEST OUTPUT_JSON\n' "$0" >&2
  exit 2
fi
manifest_path=$1
report_path=$2
if [[ ! -f $manifest_path ]]; then
  printf 'Expected an existing local manifest file: %s\n' "$manifest_path" >&2
  exit 2
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${KUBESCAPE_BIN:=kubescape}"
: "${COMPLIANCE_MINIMUM:=90}"
: "${SEVERITY_LIMIT:=high}"
: "${KS_CACHE_DIR:=${TMPDIR:-/tmp}/kubescape-example-cache}"
# This does not make the CI score a compliance certification or runtime test.
exec "$KUBESCAPE_BIN" --cache-dir "$KS_CACHE_DIR" scan framework nsa "$manifest_path" \
  --use-from "$script_dir/policies/nsa.json" \
  --controls-config "$script_dir/policies/controls-inputs.json" \
  --exceptions "$script_dir/no-exceptions.json" \
  --keep-local \
  --compliance-threshold "$COMPLIANCE_MINIMUM" \
  --severity-threshold "$SEVERITY_LIMIT" \
  --format json --output "$report_path"
```


Missing input, scan errors, and failed thresholds return nonzero. Do not hide them with continue-on-error or `|| true`. Report upload can run after failure but does not determine success. Excluding a control changes the evaluated denominator and must be recorded.

### GitHub Actions

The [validated workflow](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/kubescape/github-actions.yaml) pins the binary/checksum and scans only k8s/rendered.yaml using the local policy snapshot. The project must produce that file first; absence fails the job. Permissions are contents:read, with no PR comments or SaaS submission.

### GitLab and Jenkins

Both systems can preserve the same scan-manifests.sh exit code and archive reports. Generic Kubescape JSON is not GitLab SAST or Code Quality schema. For integrated SAST reporting, validate current --format gitlab-sast output against the receiving version. Jenkins readJSON/publishHTML require plugins; do not publish an HTML file the pipeline never generated.

<span id="eks-specific-controls"></span>
<span id="aws-auth-configmap-analysis"></span>
<span id="irsa-iam-roles-for-service-accounts-validation"></span>
<span id="eks-security-best-practices-scan"></span>

## EKS-Specific Guide

Kubernetes manifest scans do not fully validate EKS control-plane configuration, IAM, access entries, Pod Identity/IRSA, or node policies. aws-auth is a legacy authentication path; inspect the current authentication mode and access entries. system:masters or an emergency IAM user is not a least-privilege example.

C-0034 checks service account token automounting, not complete IRSA trust/aud/sub/IAM policy. Distinguish the projected STS token from automatic Kubernetes API token mounting. Validate actual workload identity and allowed AWS operations separately.

Review host-scanning and remediation permissions/mutations before enabling them. The example disables cluster-wide Secret access and remediation, while operators must still inspect the scanner/operator/storage RBAC needed for their installation.

<span id="exception-policies"></span>
<span id="applying-exceptions-via-cli"></span>
<span id="accepted-risks-documentation"></span>
<span id="inline-resource-exceptions"></span>

## Control Exception Handling

### CLI Exceptions

```json
[
  {
    "name": "documentation-privileged-exception",
    "policyType": "postureExceptionPolicy",
    "actions": [
      "alertOnly"
    ],
    "resources": [
      {
        "designatorType": "Attributes",
        "attributes": {
          "namespace": "demo-app",
          "kind": "Pod",
          "name": "insecure-example"
        }
      }
    ],
    "posturePolicies": [
      {
        "controlID": "C-0057"
      }
    ]
  }
]
```


This is a **JSON array** consumed by the CLI, not a ConfigMap wrapper. The tested alertOnly exception marked C-0057 acknowledged while preserving failure and compliance 55. --exclude-controls C-0057 removed the control from evaluation, changing the denominator and score. An exception is not a remediation.

### In-Cluster Exceptions

```yaml
apiVersion: kubescape.io/v1beta1
kind: SecurityException
metadata:
  name: documentation-privileged-exception
  namespace: demo-app
spec:
  author: documentation-security-team
  reason: Synthetic scan example; replace with an approved owner and justification.
  expiresAt: '2026-09-30T00:00:00Z'
  match:
    resources:
      - apiGroup: ''
        kind: Pod
        name: insecure-example
  posture:
    - controlID: C-0057
      action: alert_only
```


The current APIs are kubescape.io/v1beta1 SecurityException/ClusterSecurityException. Set namespace scope, match, posture action, expiry, and ownership according to approved policy. Schema success does not establish controller enforcement, RBAC, or CEL behavior. CLI alertOnly differs from CRD alert_only. Do not rely on invented ignore annotations for exception processing.

<span id="periodic-scanning-schedule"></span>
<span id="scanning-configuration"></span>
<span id="compliance-reporting"></span>
<span id="remediation-workflow"></span>
<span id="integration-with-other-security-tools"></span>
<span id="prometheus-metrics-integration"></span>

## Best Practices

![Remediation verification and separately tracked risk acceptance](../.gitbook/assets/en-security-11-kubescape-4.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-11-kubescape-4.html)


Record scope, passed/failed/unavailable checks, policy hashes, tool images, exception owners, and expiry dates. Compare scores only across equivalent inputs/policies. Node scanning, image scanning, and runtime detection are separate sources of evidence.

### Prometheus Integration

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: kubescape-posture
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [kubescape]
  selector:
    matchLabels:
      app.kubernetes.io/name: kubescape-operator
      app.kubernetes.io/instance: kubescape
      app.kubernetes.io/component: prometheus-exporter
  podMetricsEndpoints:
    - port: metrics
      path: /metrics
      interval: 60s
```


The reviewed exporter Pod names container port 8080 metrics, while its Service port is unnamed. This example therefore uses a PodMonitor matching the actual Pod labels and named port. Prometheus Operator and Prometheus PodMonitor selection are separate prerequisites.

Actual exporter 0.2.23 gauge examples are kubescape_controls_total_cluster_high and kubescape_controls_total_workload_high. A _total suffix does not make them counters. The old kubescape_compliance_score/critical_findings/last_scan_timestamp names are not established common metrics. Monitor missing scrapes and stale data separately.

<span id="table-of-contents"></span>
<span id="key-takeaways"></span>
<span id="quick-reference-commands"></span>
<span id="references"></span>
<span id="related-documentation"></span>

## Summary and References

Local validation covered binary/checksum, policy snapshot, threshold boundaries/severity/deprecated gate, exception/exclusion behavior, the published shell gate, Helm rendering, SecurityException schema, PodMonitor targeting, GitHub Actions syntax, and thirty diagram browser cases. No real AWS/Kubernetes/registry/notification/SaaS operations were performed.

- [CNCF Kubescape history](https://www.cncf.io/projects/kubescape/)
- [Kubescape documentation](https://kubescape.io/docs/)
- [Frameworks and controls](https://kubescape.io/docs/frameworks-and-controls/)
- [Operator documentation](https://kubescape.io/docs/operator/)
- [CLI 4.0.14](https://github.com/kubescape/kubescape/releases/tag/v4.0.14)
- [Pinned CLI flags](https://github.com/kubescape/kubescape/blob/v4.0.14/cmd/scan/scan.go)
- [Operator chart 1.40.4](https://github.com/kubescape/helm-charts/releases/tag/kubescape-operator-1.40.4)
- [Policy library](https://github.com/kubescape/regolibrary)
- [Exporter metrics 0.2.23](https://github.com/kubescape/prometheus-exporter/blob/v0.2.23/metrics/metrics.go)
- [Runtime security](./08-runtime-security.md)
- [EKS security practices](./06-eks-security-best-practices.md)
