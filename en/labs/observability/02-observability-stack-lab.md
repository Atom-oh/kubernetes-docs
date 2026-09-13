# Part 2: Deploy the observability stack

<span id="architecture-overview"></span>
<span id="cleanup"></span>
<span id="exercise-1-opentelemetry-collector-deployment"></span>
<span id="exercise-2-metrics-stack-deployment"></span>
<span id="exercise-3-logging-stack-deployment"></span>
<span id="exercise-4-tracing-stack-deployment"></span>
<span id="exercise-5-grafana-deployment-and-data-source-configuration"></span>
<span id="exercise-6-alerting-configuration"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="part-2-observability-stack-deployment"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **Difficulty**: Advanced
> **Last Updated**: September 13, 2026
Connect service-cluster applications to management-cluster metrics, logs and traces. Use the pinned chart/TLS/identity files in the [stack examples](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/stack). [Part1](./01-infrastructure-setup-lab.md) must provide contexts, gp3/EBS CSI, LBC, DNS/routes, IRSA and `helm-inputs/collector-identity.yaml`.

![The wired metrics, logs and traces paths](../../.gitbook/assets/en-labs-observability-02-observability-stack-lab-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-02-observability-stack-lab-0.html)

## 1. Versions and baseline paths {#baseline}

| Component | Chart | Application |
|---|---|---|
| kube-prometheus-stack | 90.0.0 | Operator0.93.1; inspect component images |
| Tempo | 3.0.0 | 3.0.3 |
| Loki | 18.13.0 | 3.7.7 |
| OTel Collector | 0.173.1 | contrib0.160.0 |

Service Prometheus scrapes metrics and sends mTLS remote-write to management Prometheus. Collectors receive CRI/JSON logs and OTLP traces, forwarding to the authenticated management endpoint. Management Collector sends to Loki/Tempo; the CloudWatch addon supplies structured logs for AIOps. Grafana UIDs consistently use `prometheus`, `loki` and `tempo`.

Backends are single durable lab instances, not HA or measured capacity. Two-day Prometheus and24-hour Loki/Tempo retention do not establish a30-day SLO.

## 2. Private TLS and network inputs {#tls-network}

```bash
cd examples/labs/observability/stack
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python prepare_tls.py   --collector-dns "$COLLECTOR_DNS" --prometheus-dns "$PROMETHEUS_DNS"   --output-directory "$LAB_STATE/tls"
.venv/bin/python render_network.py --service-source-cidr "$SERVICE_SOURCE_CIDR"   --nlb-security-group "$NLB_SECURITY_GROUP"   --nlb-source-cidr "$NLB_SUBNET_CIDR_A" --nlb-source-cidr "$NLB_SUBNET_CIDR_B"   --output-directory "$LAB_STATE/network"
```
Generate a seven-day lab CA and distinct server/client-purpose certificates. The CA private key never enters cluster Secrets. Organizational PKI must provide matching Secret keys, SANs and EKUs. The helper creates no DNS, route or SG; use actual service source and NLB health-check subnet CIDRs.

```bash
kubectl --context managed create namespace monitoring --dry-run=client -o yaml | kubectl --context managed apply -f -
kubectl --context service create namespace monitoring --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context service create namespace observability --dry-run=client -o yaml | kubectl --context service apply -f -
kubectl --context managed apply -f "$LAB_STATE/tls/management-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-monitoring-secrets.yaml"
kubectl --context service apply -f "$LAB_STATE/tls/service-observability-secrets.yaml"
```

## 3. Install management backends {#management}

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
kubectl --context managed apply -f prometheus-probe.yaml
helm upgrade --install lab-monitoring prometheus-community/kube-prometheus-stack   --version 90.0.0 --kube-context managed -n monitoring -f monitoring-management-values.yaml
helm upgrade --install lab-loki grafana-community/loki --version 18.13.0   --kube-context managed -n monitoring -f loki-values.yaml
helm upgrade --install lab-tempo grafana-community/tempo --version 3.0.0   --kube-context managed -n monitoring -f tempo-values.yaml
```
Prometheus web requires mTLS, so default kubelet HTTPS probes cannot provide the client certificate. Use the `promtool check ready/healthy --http.config.file=...` exec probes/client Secret; Operator probe merging was verified. Grafana and Tempo metrics-generator also use client certificates.

Loki uses Monolithic/TSDB-v13/filesystem-PVC. Tempo3 uses live-store/backend scheduler/worker, not mixed Tempo2 ingester/compactor settings. Grafana uses one replica, PVC and a private admin Secret rather than a known shared password. Grafana disables the unused dashboard sidecar, API token and RBAC; datasource files remain mounted from the designated Secret.

## 4. Collectors, endpoints and service collection {#collectors}

```bash
helm upgrade --install lab-collector open-telemetry/opentelemetry-collector   --version 0.173.1 --kube-context managed -n monitoring   -f collector-management-values.yaml -f collector-cloudwatch-values.yaml   -f "$LAB_STATE/helm-inputs/collector-identity.yaml"
kubectl --context managed apply -f backend-network-policies.yaml
kubectl --context managed apply -f "$LAB_STATE/network/endpoints.yaml"
kubectl --context managed -n monitoring get svc lab-collector-ingest lab-prometheus-ingest
```
Map private DNS to the actual internal NLB hostnames and verify service-Pod routing, SG/NACL and client-IP behavior before proceeding. Do not use another cluster’s `.svc.cluster.local` address. TLS terminates at Collector/Prometheus, preserving client authentication through the TCP NLB.

```bash
helm upgrade --install lab-service-monitoring prometheus-community/kube-prometheus-stack   --version 90.0.0 --kube-context service -n monitoring   -f monitoring-service-values.yaml -f "$LAB_STATE/tls/prometheus-endpoint-values.yaml"
helm upgrade --install lab-agent open-telemetry/opentelemetry-collector   --version 0.173.1 --kube-context service -n observability   -f collector-service-values.yaml -f "$LAB_STATE/tls/collector-endpoint-values.yaml"
```
The service DaemonSet reads msa Pod logs through a read-only mount. Root UID, dropped capabilities and no privilege escalation are explicit for node-log access; allow only this collector in the namespace admission policy. CRI parsing precedes JSON parsing, and Kubernetes metadata is attached in the source cluster. Management Collector cannot magically query another cluster’s Pods.

This lab does not persist file offsets/exporter queues; record possible loss/duplication during restarts/outages and design durable buffering separately. CloudWatch `raw_log: true` preserves service/level/trace_id; verify real IRSA and Logs permissions.

## 5. Verify data and extend deliberately {#verify-extend}

```bash
kubectl --context managed -n monitoring get pods,pvc
kubectl --context service -n observability get pods
kubectl --context managed -n monitoring port-forward svc/lab-grafana 3000:80
```
Sign in with the private admin Secret. After Part3 app deployment, compare actual scrapes, exporter errors, CloudWatch JSON fields, Tempo trace IDs, Loki trace_id and exemplars. A datasource or enabled UI option alone is not proof of ingestion.

VictoriaMetrics/Mimir/AMP, ClickHouse/OpenSearch, X-Ray, AMG and MWAA are optional extensions. Use their [metrics](../../observability/metrics/README.md), [logging](../../observability/logging/README.md) and [tracing](../../observability/tracing/README.md) guides to verify authentication/storage/transport/cost before adding them. The baseline does not claim to deploy every backend simultaneously. Continue to [Part3](./03-msa-deployment-lab.md).

## Validation scope

Validation covered chart/CRD/native config, actual local Collector mTLS/CRI/JSON forwarding, Prometheus mTLS probes, synthetic PKI and NetworkPolicy schemas. Real EKS/LBC/DNS, policy enforcement, IRSA and Grafana live datasource execution were not performed.

The DaemonSet profile explicitly creates the `lab-agent.observability.svc.cluster.local:4318` Service. Its default `internalTrafficPolicy: Local` requires a ready Collector on each application node; check taints, tolerations and DaemonSet readiness.
