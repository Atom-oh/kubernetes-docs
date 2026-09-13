# Two-cluster observability lab stack

This is a bounded lab baseline, using one durable Loki/Tempo/Prometheus instance
per relevant cluster. It is not an HA production sizing recommendation. Metrics
use service-cluster Prometheus and mTLS remote-write; traces/logs use the service
Collector and a management Collector that requires client certificates.

| Component | Pinned chart / application |
|---|---|
| kube-prometheus-stack | 90.0.0 / Operator 0.93.1; inspect rendered component images |
| Tempo | 3.0.0 / 3.0.3 |
| Loki | 18.13.0 / 3.7.7 |
| OpenTelemetry Collector | 0.173.1 / contrib 0.160.0 |

Prerequisites: working `managed` and `service` contexts, private routable networks,
EBS CSI and a reviewed `gp3` StorageClass, the AWS Load Balancer Controller for
`service.k8s.aws/nlb`, DNS control, and an existing NLB security group allowing only
the approved service source ranges on TCP4318/9090. The charts do not create these
prerequisites. Kubernetes NetworkPolicy must be enforced by the chosen CNI.

## Prepare private inputs

Run from this directory. Use a private `LAB_STATE` directory created for this lab;
keep the generated files out of Git. The helper refuses existing output paths.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_tls.py \
  --collector-dns "$COLLECTOR_DNS" --prometheus-dns "$PROMETHEUS_DNS" \
  --output-directory "$LAB_STATE/tls"
.venv/bin/python render_network.py \
  --service-source-cidr "$SERVICE_SOURCE_CIDR" \
  --nlb-security-group "$NLB_SECURITY_GROUP" \
  --nlb-source-cidr "$NLB_SUBNET_CIDR_A" \
  --nlb-source-cidr "$NLB_SUBNET_CIDR_B" \
  --output-directory "$LAB_STATE/network"
```

This creates a disposable seven-day lab CA, server/client certificates, Grafana
credentials, datasource provisioning and endpoint overrides. The CA private key
never enters Kubernetes Secrets. Existing organizational PKI may be used instead
if it supplies the same Secret keys, SANs and client/server EKUs. Do not reuse this
short-lived lab CA as a production trust root.

Create namespaces in the intended clusters before applying Secrets:

```bash
kubectl --context managed create namespace monitoring --dry-run=client -o yaml |
  kubectl --context managed apply -f -
kubectl --context service create namespace monitoring --dry-run=client -o yaml |
  kubectl --context service apply -f -
kubectl --context service create namespace observability --dry-run=client -o yaml |
  kubectl --context service apply -f -
kubectl --context managed apply -f "$LAB_STATE/tls/management-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-monitoring-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-observability-secrets.yaml"
```

## Install the management backends

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
kubectl --context managed apply -f prometheus-probe.yaml
helm upgrade --install lab-monitoring prometheus-community/kube-prometheus-stack \
  --version 90.0.0 --kube-context managed -n monitoring \
  -f monitoring-management-values.yaml
helm upgrade --install lab-loki grafana-community/loki --version 18.13.0 \
  --kube-context managed -n monitoring -f loki-values.yaml
helm upgrade --install lab-tempo grafana-community/tempo --version 3.0.0 \
  --kube-context managed -n monitoring -f tempo-values.yaml
```

Management Prometheus requires mTLS on its web port. Default kubelet HTTPS probes
cannot supply a client certificate, so the profile uses authenticated `promtool`
exec probes and the matching client Secret. Operator0.93.1 removes inherited HTTP
handlers when merging those probe overrides; retest this on Operator upgrades.
Grafana and Tempo metrics-generator use the same verified Prometheus endpoint.

Loki uses Monolithic mode (the old SingleBinary deployment name is deprecated),
TSDB/v13 and filesystem PVC storage. Tempo3 uses live-store and backend scheduler/
worker settings rather than the old Tempo2 ingester/compactor configuration. Each
keeps 24 hours of trace/log data; Prometheus retains two days. These windows do not
provide 30 days of SLO evidence.

## Management Collector and authenticated endpoints

The application infrastructure stack supplies a log group and CollectorRoleArn.
`application/prepare_values.py` produces `collector-identity.yaml` with those exact
values. This extra profile is required for the AIOps chapter's CloudWatch logs.

```bash
helm upgrade --install lab-collector open-telemetry/opentelemetry-collector \
  --version 0.173.1 --kube-context managed -n monitoring \
  -f collector-management-values.yaml -f collector-cloudwatch-values.yaml \
  -f "$LAB_STATE/helm-inputs/collector-identity.yaml"
kubectl --context managed apply -f backend-network-policies.yaml
kubectl --context managed apply -f "$LAB_STATE/network/endpoints.yaml"
kubectl --context managed -n monitoring get svc lab-collector-ingest lab-prometheus-ingest
```

These are internal TCP NLBs: TLS terminates in the Collector/Prometheus process,
preserving client-certificate verification. The existing NLB SG must allow only
approved sources; the controller needs permission to manage backend rules. The
NetworkPolicies allow the stated service source plus actual NLB subnet ranges
for TCP health checks. Verify source-IP behavior for your topology rather than
assuming it works through every peering/TGW/proxy arrangement.

Create private DNS records mapping `COLLECTOR_DNS` and `PROMETHEUS_DNS` to the
actual NLB hostnames, and verify routing/security groups/NACLs from service Pods.
A `*.svc.cluster.local` name in another cluster is not a cross-cluster endpoint.
The helper only writes manifests; it does not configure DNS or routes.

## Install service-cluster collection

```bash
helm upgrade --install lab-service-monitoring prometheus-community/kube-prometheus-stack \
  --version 90.0.0 --kube-context service -n monitoring \
  -f monitoring-service-values.yaml -f "$LAB_STATE/tls/prometheus-endpoint-values.yaml"
helm upgrade --install lab-agent open-telemetry/opentelemetry-collector \
  --version 0.173.1 --kube-context service -n observability \
  -f collector-service-values.yaml -f "$LAB_STATE/tls/collector-endpoint-values.yaml"
```

The service Collector reads only `msa` Pod logs through a read-only host mount.
It uses a root UID for node-log access with all capabilities dropped and no
privilege escalation; permit that specific DaemonSet in the namespace's admission
policy. It has only Pod/namespace read RBAC. CRI parsing precedes JSON parsing;
`service` becomes `service.name`, and the JSON trace ID remains available to Loki
correlation and CloudWatch aggregate queries. This baseline does not persist
file offsets or exporter queues: restarts/outages can lose or duplicate telemetry.

Management Collector uses `raw_log: true` for CloudWatch so `service`, `level` and
`trace_id` remain at the expected JSON level. Verify real workload-role access;
chart rendering alone does not prove an IRSA exchange or Logs permissions.

## Verify the complete path

Install the application and its ServiceMonitor after both stack profiles. Inspect
actual targets, logs, queue processing and exporter failures. Port-forward the
Grafana Service privately:

```bash
kubectl --context managed -n monitoring port-forward svc/lab-grafana 3000:80
```

Use the generated private Grafana admin Secret. The provisioned UIDs are
`prometheus`, `loki` and `tempo`; the exemplar label is `trace_id`. Confirm a real
request's metric/exemplar, trace and log share that ID. A configured datasource or
an enabled graph option is not proof that data arrived. Service graphs require
Tempo metrics-generator, successful authenticated remote-write and the linked
Prometheus datasource.

`backend-network-policies.yaml` restricts Loki/Tempo backend ingress to the
Collector/Grafana roles; it does not claim to restrict all egress or protect a
cluster whose CNI ignores NetworkPolicy. Cross-cluster endpoints have separate
source-limited policies. Do not expose the unprotected Loki/Tempo backend ports
as public LoadBalancers.

Validation covered pinned Helm/native configuration, actual local Collector mTLS
and CRI/JSON forwarding, Prometheus mTLS probes and Operator merge behavior,
synthetic certificate/SAN/EKU checks, and schema checks. Actual EKS/LBC routing,
NetworkPolicy enforcement, live IRSA, Grafana UI data queries and production
availability were not executed during the audit.

Grafana reads datasource provisioning files from its dedicated Secret mount. The
unused dashboard sidecar, Kubernetes API token mount and Grafana RBAC are disabled;
the lab does not need cluster-wide ConfigMap or Secret discovery.

The service Collector explicitly enables the `lab-agent` ClusterIP Service on
OTLP HTTP port4318. Its `internalTrafficPolicy: Local` requires a ready Collector
on each application node; verify taints, tolerations and DaemonSet readiness.
