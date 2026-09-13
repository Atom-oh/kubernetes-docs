# Amazon EKS Advanced Debugging Quiz

> **Last Updated**: September 12, 2026

The [source chapter](../../eks/11-eks-advanced-debugging.md) defines the current API, scope and safety assumptions. Examples are not live cluster/benchmark results. No cloud or cluster actions were run in this audit.

This quiz tests your understanding of advanced debugging techniques in Amazon EKS, including incident response, control plane debugging, node troubleshooting, kubectl debug, PromQL queries, and observability.

## Quiz Overview
- Incident Response Process
- EKS Control Plane Debugging
- Node and kubelet Troubleshooting
- kubectl debug Command Usage
- PromQL Queries and Metric Analysis
- Distributed Tracing and Log Analysis

## Multiple Choice Questions

### 1. Where are enabled EKS control-plane audit logs normally queried?

A. A customer-managed /var/log/kubernetes directory
B. Amazon CloudWatch Logs
C. Direct access to managed etcd
D. kubectl logs on an AWS control-plane Pod

<details>
<summary>View Answer</summary>

**Answer: B. Amazon CloudWatch Logs**

Use `/aws/eks/<cluster-name>/cluster` in the correct Region/account. The five available types are api, audit, authenticator, controllerManager and scheduler; they are opt-in and enabling them does not reconstruct old logs. A 403 is authorization evidence, not automatically failed IAM authentication. Run the query separately as Logs Insights QL with an explicit time window.

```bash
# Read-only: confirm logging is enabled before searching the owned group.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.logging
```
```text
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

</details>

### 2. Which kubectl debug flag requests a separate copy of a Pod?

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>View Answer</summary>

**Answer: B. --copy-to**

The previous question incorrectly described adding a container to the original Pod. --copy-to creates another Pod; debugging the existing Pod with an ephemeral container does not use that flag or a --ephemeral flag. --target requests a process namespace when supported by the runtime. A copy can retain ServiceAccount, environment/Secret references, volumes and other regular containers; disabling init containers and changing one command does not make it an isolated data clone.

```bash
# MUTATION: separate reviewed reproduction Pod, not an ephemeral container in the original.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${DEBUG_POD_NAME:?Choose a new owned name}"; : "${DEBUG_IMAGE:?Reviewed image providing sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --share-processes=true --profile=general -- sleep 3600
```

</details>

### 3. Which evidence is useful after checking the node condition and heartbeat for a NotReady node?

A. Unrelated application logs only
B. Applicable kubelet/runtime status and logs, correlated with network/EC2 evidence
C. Direct manipulation of AWS-managed etcd
D. CoreDNS logs as the sole proof

<details>
<summary>View Answer</summary>

**Answer: B. Applicable kubelet/runtime status and logs, correlated with network/EC2 evidence**

No measured frequency supports the old “most common cause” assertion. Ready=False, heartbeat loss/Unknown, resource pressure and an instance outage are different signals. Use approved host access on compatible nodes or NodeDiagnostic/documented Auto Mode debug access; SSH/systemctl is not universal. Collect bounded logs before any separately reviewed restart or replacement.

```bash
# Read-only Kubernetes evidence first; no automatic kubelet restart.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,nodeInfo:.status.nodeInfo,conditions:.status.conditions
}'
```

</details>

### 4. Which calculation measures container CPU use relative to a positive configured CPU limit?

A. An assumed cpu_usage metric >80
B. CPU seconds per second >0.8 without a denominator
C. CPU usage in cores / the matching positive CPU limit in cores
D. An assumed container_cpu_percent metric

<details>
<summary>View Answer</summary>

**Answer: C. CPU usage in cores / the matching positive CPU limit in cores**

rate(cpu_usage_seconds_total) is CPU cores, not a percentage on its own. Join by cluster scope, namespace, Pod and container and use matching positive limits; an unlimited/missing-limit container is not 0% utilization. HPA utilization is normally relative to requests, which is a different calculation. These queries assume the source chapter’s single-cluster/label/scrape contract and show a fraction above0.8.

```promql
(sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
)
/ on (namespace,pod,container)
max by (namespace,pod,container) (
  kube_pod_container_resource_limits{namespace="diagnostics-example",resource="cpu",unit="core"} > 0
)) > 0.8
```
```promql
(max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)) > 0.8
```

</details>

### 5. Which is not the normal tool for customer diagnosis of inter-node networking in managed EKS?

A. tcpdump with authorized capture
B. Wireshark for an authorized saved capture
C. Scoped curl/DNS tests from a workload
D. etcdctl against the AWS-managed etcd endpoint

<details>
<summary>View Answer</summary>

**Answer: D. etcdctl against the AWS-managed etcd endpoint**

Customers do not receive a direct managed-etcd endpoint. This does not mean etcdctl can never help diagnose networking in a self-managed etcd system. Packet capture needs appropriate capabilities/host context, bounds and private handling; a new debug Pod can follow a different policy/DNS path from the failing workload. A throughput counter is not a latency measurement.

```bash
# Deliberate bounded request from an owned workload with curl installed.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${HEALTH_URL:?Set a reviewed safe health URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```

</details>

### 6. Which approach can reduce detection delay without simply lowering every threshold?

A. Only more manual observation
B. The lowest possible thresholds for every metric
C. Appropriate measured alerts, coverage checks and escalation
D. Longer retention alone

<details>
<summary>View Answer</summary>

**Answer: C. Appropriate measured alerts, coverage checks and escalation**

Tune against actual SLOs and failure modes; low thresholds can create alert fatigue. The HTTP counter and status labels below require application instrumentation, and a zero/missing request denominator is not proof of success. Use the waiting reason for CrashLoopBackOff rather than treating every restart as a crash loop. Prometheus must select the rule/namespace, and notification delivery is a separate check. No MTTD result was measured here.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-quiz-alerts
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-quiz-alerts
    rules:
    - alert: HighErrorRate
      expr: "(\n  sum(rate(http_requests_total{namespace=\"diagnostics-example\",job=\"\
        owned-app\",status=~\"5..\"}[5m]))\n  / sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m]))\n) > 0.05\nand on() (sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m])) > 0)"
      for: 2m
      labels:
        severity: critical
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
```

</details>

### 7. Which command form creates a diagnostic Pod on a node?

A. `kubectl debug node/<node-name> --image=<reviewed-image>`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>View Answer</summary>

**Answer: A. `kubectl debug node/<node-name> --image=<reviewed-image>`**

The tested general profile mounts /host and uses host namespaces, but privileged is false. An explicit sysadmin profile grants broader privilege; chroot/nsenter/tool/SELinux behavior depends on the platform and permissions. Creating the Pod is a mutation, not passive inspection, and a failed kubelet/runtime may prevent it from starting. Record the created name/UID and use the reviewed cleanup procedure.

```bash
# MUTATION: creates a node diagnostic Pod; general is not automatically privileged.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${NODE_NAME:?}"; : "${NODE_DEBUG_IMAGE:?Reviewed image}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" \
  --image="$NODE_DEBUG_IMAGE" --profile=general --attach=false -- true
```

</details>

### 8. What does a Span represent in distributed tracing?

A. Only the total end-to-end request duration
B. One unit of work with timing and associated metadata
C. Only network latency
D. A log timestamp

<details>
<summary>View Answer</summary>

**Answer: B. One unit of work with timing and associated metadata**

A span can describe an HTTP call, database operation or another unit of work. Trace IDs associate spans; parent/child relationships and links express related work. Propagation and sampling determine what is actually visible. Baggage is propagated context, not automatically a span attribute, and must not contain secrets. The JSON below is an illustrative human-readable record, not an OTLP wire payload or measured request. For Collector configuration use the current v1beta1 object-shaped source example and a supported backend/OTLP path; the old jaeger exporter/14250 recipe is not current guidance.

```json
{
  "exampleOnly": true,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "parent_span_id": "fedcba9876543210",
  "name": "GET /api/products",
  "kind": "SERVER",
  "duration_ms": 85
}
```

</details>

### 9. For Deployment-based CoreDNS, which evidence is useful when investigating DNS errors?

A. Scoped CoreDNS Pod logs/status and workload resolver checks
B. Only describe service kubernetes
C. Only AWS cluster metadata
D. Only the old Endpoints list

<details>
<summary>View Answer</summary>

**Answer: A. Scoped CoreDNS Pod logs/status and workload resolver checks**

Not all DNS queries are logged by default. Correlate resolver configuration, Pod/Service health and upstream errors. Pure Auto Mode uses node-system DNS; mixed clusters retain the Deployment for non-Auto nodes. Test from the relevant Pod/container when tools exist, not an unrelated default-namespace Pod with an ancient image. Tool-specific nslookup debug flags are not universal.

```bash
# Deployment-based CoreDNS only; use the Auto Mode path when applicable.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

</details>

### 10. Which command displays recent Pod resource samples from the resource-metrics API?

A. kubectl describe pod
B. kubectl top pods
C. kubectl get pods -o wide
D. kubectl logs

<details>
<summary>View Answer</summary>

**Answer: B. kubectl top pods**

kubectl top needs a working metrics.k8s.io provider, commonly Metrics Server. It reports recent sampled CPU/memory data, not an instantaneous measurement or history. Missing metrics are not zero usage. Compare the appropriate requests/limits separately and use a monitoring backend for historical analysis.

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --sort-by=memory
kubectl --context "$KUBE_CONTEXT" top nodes
```

</details>

## Short Answer Questions

### 1. What is the CloudWatch Logs group pattern for enabled EKS control-plane logs?

<details>
<summary>View Answer</summary>

**Answer:** `/aws/eks/<cluster-name>/cluster`. Log types must be enabled for the cluster; enabling them does not reconstruct earlier events. Select the correct account, Region, group and time window. Run the following Logs Insights QL queries separately. Audit usernames are recorded identities, not necessarily the short IAM role name.

```sql
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @logStream not like /kube-apiserver-audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50
```

```sql
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_EXACT_AUDIT_USERNAME"
| sort @timestamp desc
| limit 100
```

</details>

### 2. Does current Kubernetes require enabling the old EphemeralContainers feature gate?

<details>
<summary>View Answer</summary>

**Answer:** No. `EphemeralContainers` was the historical gate; the feature became beta in 1.23 and stable in 1.25. On current versions, check RBAC for `pods/ephemeralcontainers`, admission policies, image access and runtime support instead. Adding one changes the Pod, and its entry cannot be changed or removed afterward. `--target` process visibility depends on runtime support. Reuse the source chapter’s explicitly reviewed creation procedure; this command only lists metadata.

```bash
# Read-only inventory; adding an ephemeral container is a separate mutation.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq '{
    uid:.metadata.uid,
    ephemeralContainers:[.spec.ephemeralContainers[]? | {name,image,targetContainerName}],
    ephemeralStatuses:.status.ephemeralContainerStatuses
  }'
```

</details>

### 3. How do rate() and irate() differ in PromQL?

<details>
<summary>View Answer</summary>

`rate()` estimates the per-second counter increase over the selected range, adjusts resets and extrapolates to the range boundaries. `irate()` uses only the last two samples in that range and adjusts resets. Both need enough samples; neither sees an unsampled spike. Apply the function before aggregation so each series reset remains detectable. Usually use `rate()` for alerts; `irate()` can help inspect volatile counters but does not guarantee better incident detection. These are counter functions, not generic gauge derivatives. The first two examples use an instrumented application counter; the last returns CPU cores, not a percentage. Use one cluster and the source chapter’s label/scrape contract.

```promql
sum by (namespace,service) (
  rate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
sum by (namespace,service) (
  irate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

</details>

### 4. Where does kubectl debug node mount the host filesystem, and what does that permit?

<details>
<summary>View Answer</summary>

**Answer:** `/host`. The `general` profile is not automatically privileged. A host mount does not guarantee that `chroot`, `systemctl` or reading protected host files will work. The image must contain the tools, and admission, capabilities, SELinux, OS and node health matter. The explicitly privileged `sysadmin` profile needs a separately authorized diagnostic procedure. Auto Mode supports documented node-debug procedures; direct SSH and ordinary host paths are not universal. Use MCQ 7 and the source chapter for creation and cleanup, and never print kubeconfig or credential files.


</details>

### 5. How can incident recovery time be decomposed without double counting?

<details>
<summary>View Answer</summary>

Define the convention before using “MTTR”: some teams measure from detection, others from incident start, and resolve/repair/recover have different meanings. Here use `t0 = service impact starts`, `t1 = detected`, `t2 = actionable diagnosis`, `t3 = service restored`. The non-overlapping intervals are detection `t1−t0`, investigation `t2−t1`, and restoration `t3−t2`; their sum is `t3−t0`. Averaging the same incidents with these definitions preserves the sum. One 45-minute incident is a duration, not a demonstrated mean. Root-cause confirmation and follow-up work can occur after restoration, so do not force every incident into this sequence. Improve monitoring coverage, runbooks and tested recovery procedures, and measure their actual outcomes.


</details>

## Hands-on Exercises

### 1. Find production containers with an estimated restart increase of at least two in five minutes.

<details>
<summary>View Answer</summary>

Use one cluster and kube-state-metrics with `namespace`, `pod`, `uid` and `container` labels. `increase()` handles counter resets and extrapolates, so the result may be fractional and is not a complete event ledger. `max` avoids adding identical exporter replicas together but is not a universal HA deduplication solution; verify scrape health and backend deduplication. Preserve Pod UID so replacements with the same name remain distinct. The variants below show lifetime count >5, the top ten **Pods** by summed container increases over one hour, and restart rate per second for a graph. Missing series are not zero restarts.

```promql
max by (namespace,pod,uid,container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2
```

```promql
max by (namespace,pod,uid,container) (
  kube_pod_container_status_restarts_total{namespace="production"}
) > 5
```

```promql
topk(10,
  sum by (namespace,pod,uid) (
    max by (namespace,pod,uid,container) (
      increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
    )
  )
)
```

```promql
max by (namespace,pod,uid,container) (
  rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])
)
```

</details>

### 2. Collect scoped evidence for a container in CrashLoopBackOff before changing the workload.

<details>
<summary>View Answer</summary>

`CrashLoopBackOff` is a container waiting reason; the Pod can still have phase `Running`. Select the actual context, namespace, Pod and failing container. Check its current UID before collecting logs; name-based log calls are not atomic with the UID check. Start with the following bounded inspection. Investigate exit code/reason, application errors, configuration references, node pressure and dependency failures. Startup/liveness probe failures can restart a container; readiness failure alone does not. Missing Secret/configuration data can also prevent creation rather than produce a crash loop. Do not print all environment variables, Secret values or configuration files.

```bash
# Read-only, bounded evidence for one owned Pod and container.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE")
pod_state=$("${k[@]}" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid, phase:.status.phase, conditions:.status.conditions,
  containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
  initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
}')
printf '%s\n' "$pod_state"
pod_uid=$(jq -er '.uid' <<<"$pod_state")
"${k[@]}" get events --field-selector "involvedObject.uid=$pod_uid" \
  --sort-by='.metadata.creationTimestamp'
# These logs can contain sensitive application data; keep the terminal/evidence private.
# A missing previous instance/log is an evidence gap, not an empty successful result.
if ! "${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous \
  --tail=100 --limit-bytes=65536 --timestamps; then
  printf '%s\n' 'Previous container log unavailable; retain this limitation.' >&2
fi
"${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=100 --limit-bytes=65536 --timestamps
```

If reproduction is necessary, use MCQ 2/source instructions only after reviewing the copy’s identity, Secret references, volumes, other containers and external side effects. Replacing one image/command and disabling init containers does not isolate those resources. Prefer a sanitized reproduction in an appropriate environment; record the new name/UID and review cleanup separately. A sleeping debug container is not proof the application is fixed.

</details>

### 3. Query EKS audit 403 events for the last hour and wait for complete results.

<details>
<summary>View Answer</summary>

Audit logging must already be enabled. Select the owned account/Region and `/aws/eks/<cluster-name>/cluster`; in the console choose the last-hour window. Each block is a separate Logs Insights QL query. Use discovered JSON fields rather than parsing a fixed key order. These count audit events, not necessarily unique requests: audit stages can repeat an audit ID. A 403 is authorization denial, not by itself proof of the responsible IAM/RBAC policy. The CLI example needs AWS CLI, Bash, jq and Python; it queries at most 100 records and stores results privately. Only `Complete` is final, even when a running query has rows. A polling timeout does not cancel the service-side query.

```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

```sql
filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| stats count(*) as deniedEvents by user.username, verb, objectRef.resource
| sort deniedEvents desc
| limit 100
```

```bash
# Read-only query with possible CloudWatch scan charges; no log configuration changes.
set -euo pipefail
umask 077
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
evidence_dir=$(mktemp -d "$PWD/eks-audit403.XXXXXX")
printf 'Private evidence directory: %s\n' "$evidence_dir"
read -r start_epoch end_epoch < <(python3 - <<'PY'
import time
end = int(time.time())
print(end - 3600, end)
PY
)
query_string='fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100'
query_id=$(aws logs start-query --region "$AWS_REGION" --no-cli-pager \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$start_epoch" --end-time "$end_epoch" \
  --query-string "$query_string" --query queryId --output text)
if [[ ! "$query_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  printf '%s\n' 'No valid query ID returned.' >&2
  exit 1
fi
printf '%s\n' "$query_id" > "$evidence_dir/query-id.txt"
for attempt in {1..15}; do
  aws logs get-query-results --region "$AWS_REGION" --no-cli-pager \
    --query-id "$query_id" --output json > "$evidence_dir/result.json"
  status=$(jq -er '.status' "$evidence_dir/result.json")
  case "$status" in
    Complete)
      printf 'Query complete; inspect private file %s/result.json\n' "$evidence_dir"
      exit 0
      ;;
    Scheduled|Running) sleep 2 ;;
    *)
      printf 'Query ended without complete results: %s\n' "$status" >&2
      exit 1
      ;;
  esac
done
printf 'Polling limit reached; query %s may still run. Partial results are not final.\n' "$query_id" >&2
exit 2
```

</details>

## Advanced Questions

### 1. Develop a tracing, metrics and logs strategy for intermittent API latency.

<details>
<summary>View Answer</summary>

**1. Define the measurement contract.** Use one cluster, an instrumented `api-gateway` in `diagnostics-example`, and a classic histogram in seconds with bounded `endpoint` labels and a `le="0.5"` bucket. Confirm identical series scope for the bucket and count. Kubernetes does not supply these application metrics automatically. Compare affected routes, traffic volume and time ranges. The following queries show p99, cumulative bucket rates for a heatmap, and the fraction slower than 0.5 seconds; subtracting rates alone gives requests/second, not a ratio. Zero traffic has no defined ratio.

```promql
histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (
  rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[5m])
))
```

```promql
sum by (le,namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[1m]))
```

```promql
(
  (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) - sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway",le="0.5"}[5m])))
  / sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m]))
)
and on (namespace,service,endpoint) (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) > 0)
```

**2. Inspect traces.** In the backend UI, select service `api-gateway`, the affected time range, duration >2 seconds, and the relevant operation such as `GET /api/products`. Inspect error spans and downstream calls with the backend’s actual attribute names. These are UI search criteria, not an importable Jaeger YAML configuration. Verify propagation and sampling first; absence of a span does not prove that no call occurred. Parallel spans must not simply be summed as request duration.

**3. Correlate logs.** If structured logs contain `trace_id`, replace the placeholder with an actual trace ID and run this separate Logs Insights QL query in the owned application log group/time range. This requires application instrumentation; avoid logging tokens, request bodies or propagated secrets. Correlation narrows a hypothesis but does not establish causation.

```sql
fields @timestamp, @message
| filter trace_id = "REPLACE_WITH_ACTUAL_TRACE_ID"
| sort @timestamp asc
| limit 100
```

**4. Compare infrastructure evidence.** In order, these queries return throttled CPU seconds/second, received bytes/second and JVM GC pause seconds/second. Network throughput is **not network latency**; use correctly scoped client/server spans or an authorized bounded RTT test for latency. GC pause rate is not the delay of each request. Metric names/labels depend on the exporters and runtime. Compare the actual node/Pod and time interval, not unrelated cluster totals.

```promql
rate(container_cpu_cfs_throttled_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
rate(container_network_receive_bytes_total{namespace="diagnostics-example",pod!=""}[5m])
```

```promql
rate(jvm_gc_pause_seconds_sum{namespace="diagnostics-example",service="api-gateway"}[5m])
```

**5. Design a dashboard.** This table is a panel design, not a Grafana dashboard import file. Use the installed Grafana version’s editor/export format and actual datasource UID.

| Panel | Measurement |
|---|---|
| p50/p95/p99 latency | Three separate histogram-quantile queries with 0.50, 0.95 and 0.99 |
| Request rate by status | Rate of the instrumented request counter, grouped by the actual status label |
| Heatmap | Matching classic histogram bucket rates, preserving `le` and route scope |
| Downstream latency | The downstream service’s own histogram and label contract |
| Pod resources | CPU counter rate in cores; memory working-set gauge in bytes |

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"}
```

**6. Evaluate a comparison alert.** Select this rule/namespace in Prometheus and replace the release label. The 50% threshold and five-minute hold are examples requiring traffic/SLO tuning. The longer-window p99 is **not a one-hour average latency** and includes the recent five minutes. This is a comparison rule, not a predictive model. A positive baseline is required; missing/NaN data does not prove health. Check collection and low traffic separately, and test notification delivery.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-comparison-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: latency-comparison-example
    rules:
    - record: diagnostics:http_duration_seconds:p99_5m
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[5m])\n))"
    - record: diagnostics:http_duration_seconds:p99_1h
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[1h])\n))"
    - alert: LatencyComparedWithLongerWindow
      expr: "(\n  diagnostics:http_duration_seconds:p99_5m\n  / diagnostics:http_duration_seconds:p99_1h\
        \ > 1.5\n)\nand on (namespace,service,endpoint) (diagnostics:http_duration_seconds:p99_1h\
        \ > 0)"
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Five-minute p99 exceeds one-hour p99 by over 50%; investigate.
```

Keep hypotheses separate: endpoint-specific behavior, downstream calls, CPU throttling, GC, network path and traffic changes each require supporting evidence. No latency reduction or benchmark was measured here.

</details>

### 2. Establish an evidence-based RCA process for intermittent NotReady nodes.

<details>
<summary>View Answer</summary>

**1. Collect identity and timing.** Distinguish `Ready=False` from heartbeat loss/`Unknown`. Record node UID, provider ID, OS/runtime versions, condition transition times and lease renewal. Events have limited retention; an empty list does not rule out an earlier failure. A stopped node may not support node-debug at all.

```bash
# Read-only scoped node evidence; confirm account/cluster/Region first.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s)
node_state=$("${k[@]}" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,
  nodeInfo:.status.nodeInfo,conditions:.status.conditions
}')
printf '%s\n' "$node_state"
node_uid=$(jq -er '.uid' <<<"$node_state")
"${k[@]}" get events --all-namespaces \
  --field-selector "involvedObject.uid=$node_uid" --sort-by='.metadata.creationTimestamp'
"${k[@]}" -n kube-node-lease get lease "$NODE_NAME" \
  -o jsonpath='{.spec.renewTime}{"\n"}'
```

For the corresponding EC2 instance, `Maximum=1` means at least one failed status-check sample in that bucket. `Sum` is not outage duration, and missing datapoints are not success. Fargate and Hybrid Nodes need their own infrastructure evidence.

```bash
# EC2-backed nodes only: resolve the actual instance from providerID, not a guessed name.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verified EC2 instance ID}"
read -r start_time end_time < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc)
print((end-timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
      end.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" --no-cli-pager \
  --namespace AWS/EC2 --metric-name StatusCheckFailed \
  --dimensions "Name=InstanceId,Value=$INSTANCE_ID" \
  --start-time "$start_time" --end-time "$end_time" --period 300 \
  --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

**2. Collect applicable host evidence.** Use approved host access, NodeDiagnostic or the documented Auto Mode diagnostic path from the source chapter. `general` is not a privileged chroot shortcut. The following reads apply to a compatible systemd Linux host, not every debug image or Bottlerocket/Auto Mode path. Logs may be sensitive; collect privately before a separately reviewed repair.

```bash
# Only inside an already authorized, compatible systemd Linux host context.
# These are bounded reads, not instructions to restart or prune the node.
journalctl -u kubelet --since '24 hours ago' -n 200 --no-pager
journalctl -u containerd --since '24 hours ago' -n 200 --no-pager
dmesg | tail -n 100
free -h
vmstat 1 5
cat /proc/pressure/memory /proc/pressure/cpu
```

**3. Check the relevant network path.** This request validates TLS using the selected kubeconfig and needs authorization to `/readyz`. It tests the caller’s path, not necessarily the failing node’s path. A 401/403 proves an HTTP response but does not establish readiness; DNS, timeout and certificate errors need separate diagnosis. Do not use `curl -k` to hide trust failures.

```bash
# Uses the selected kubeconfig CA and authentication; do not disable TLS verification.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=10s get --raw='/readyz'
```

For standard VPC CNI only, inspect the actual aws-node Pod and the affected instance’s ENIs. Auto Mode uses its managed networking path; do not infer a missing DaemonSet means failure.

```bash
# Standard VPC CNI on an EC2 node; choose the aws-node Pod on the affected node.
: "${KUBE_CONTEXT:?}"; : "${AWS_NODE_POD:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  logs "$AWS_NODE_POD" -c aws-node --since=15m --tail=100 --limit-bytes=65536
aws ec2 describe-network-interfaces --region "$AWS_REGION" --no-cli-pager \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ENI:NetworkInterfaceId,Subnet:SubnetId,Status:Status,IPv4Prefixes:Ipv4Prefixes,PrivateIPs:PrivateIpAddresses[].PrivateIpAddress}'
```

**4. Interpret resource signals.** These single-cluster queries show memory headroom, root-filesystem capacity, system thread-limit utilization, and an actual kubelet pressure condition. They require the corresponding Node Exporter/kube-state-metrics series and correct host mounts/labels. `processes` is disabled by default in Node Exporter; `node_processes_max_threads` is Linux `threads-max`. That ratio is not the kubelet’s PIDPressure decision or a container’s `pids.max`. Filesystem/inode/imagefs/cgroup limits and scrape failures require separate checks. Thresholds here are examples, not defaults.

```promql
(1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0)) * 100 > 90
```

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0)) * 100 > 85
```

```promql
node_processes_threads / (node_processes_max_threads > 0) * 100 > 80
```

```promql
max by (node) (kube_node_status_condition{condition=~"MemoryPressure|DiskPressure|PIDPressure",status="true"}) == 1
```

**5. Test hypotheses.** Correlate kernel OOM records with the killed process, workload memory and limits; correlate disk/inode exhaustion with the affected filesystem. Compare kubelet/runtime logs, node-to-API reachability, CNI/IP evidence and EC2 health at matching timestamps. High memory or a failed probe alone does not prove a memory leak or infrastructure fault.

**6. Prevent recurrence using the actual compute model.** Auto Mode includes node monitoring and repair. Managed node groups require their repair configuration to be checked. Self-managed Karpenter repair requires a compatible release, `NodeRepair=true` and the applicable condition/repair policy; diagnostic agents supply additional conditions. The current Karpenter policy allows 30 minutes for `Ready=False/Unknown`, blocks repairs when more than 20% of a NodePool is unhealthy, and repair can force termination instead of ordinary graceful drain. Do not treat voluntary disruption budgets/PDBs as a universal repair guarantee. EKS repair does not by default repair `MemoryPressure`, `DiskPressure` or `PIDPressure`; address workload pressure. These EKS monitoring/repair features are Linux-only and the monitoring agent is unavailable on Fargate. Use the source chapter and current provider configuration rather than deploying an incomplete privileged Node Problem Detector DaemonSet or duplicating an existing agent.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: node-health-example
    rules:
    - alert: NodeHighMemoryUse
      expr: (1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0))
        * 100 > 90
      for: 5m
      labels:
        severity: warning
    - alert: NodeRootFilesystemLowSpace
      expr: (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
        / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0))
        * 100 > 85
      for: 5m
      labels:
        severity: warning
    - alert: NodeNotReady
      expr: max by (node) (kube_node_status_condition{condition="Ready",status="true"})
        == 0
      for: 2m
      labels:
        severity: critical
```

Prometheus must select these rules; missing condition/exporter series need independent collection/inventory alerts. The capacity alerts are not named as kubelet pressure conditions because they measure different signals.

If you own a configurable Linux kubelet, the following is a **fragment to review and merge into its existing configuration**, not a complete config or a command to overwrite an EKS node file. Use the OS/provisioner’s supported bootstrap mechanism. `mergeDefaultEvictionSettings` retains unspecified hard defaults; otherwise a partial override can set omitted thresholds to zero. Soft thresholds need matching grace periods, and `evictionMaxPodGracePeriod` limits termination grace. The sample values require workload/capacity validation and are not Auto Mode customization instructions.

```json
{
  "mergeDefaultEvictionSettings": true,
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  },
  "evictionMaxPodGracePeriod": 60
}
```

**Historical RCA template — unverified example, not an incident report.** Original dates, quantities and the original locale-specific timezone are retained; the PST and KST examples do not claim to describe the same instant. There is no source evidence for the asserted memory leak, actual remediation or completion status. Replace the placeholders with evidence before operational use.

```markdown
## Incident summary (illustrative)
- Start: 2024-01-15 14:30 PST
- Example impact: 3 nodes, 45 Pods
- Example restoration: 2024-01-15 15:15 PST (duration 45 minutes, not a measured mean)

## Example timeline — evidence required for every entry
- 14:30 — NodeNotReady alert
- 14:35 — Investigation starts
- 14:50 — Hypothesis: memory pressure killed kubelet; confirm with kernel/process evidence
- 15:00 — Proposed drain/restart; record actual authorization, effects and data safety checks
- 15:15 — Proposed restoration point; supply workload/SLO verification

## Root-cause hypothesis
A memory leak could exhaust node memory; not established by this template.

## Follow-up proposals — no completion asserted
1. Validate application memory behavior and appropriate requests/limits.
2. Evaluate alert threshold change from 90% to 80% against noise and capacity.
3. Review existing node monitoring before considering Node Problem Detector.
```

</details>

**Primary references for these exercises:**

- [Prometheus functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Karpenter disruption and node repair](https://karpenter.sh/docs/concepts/disruption/)
- [EKS node monitoring and repair](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)
- [Kubelet node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Exporter collectors](https://github.com/prometheus/node_exporter#disabled-by-default)
