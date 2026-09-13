# Operations and Management

> **Supported Versions**: EKS Auto Mode GA; example baseline EKS 1.36
> **Last Updated**: September 12, 2026

Day-2 operations must distinguish desired capacity, node lifecycle, application availability and the signals actually collected. The examples below are controlled lab configurations, not a tested production runbook. No cloud resource changes or live node/Pod execution were performed during this audit.

The NodePool manifests were checked with the released Karpenter 1.14.1 structural schema. Workload examples passed Kubernetes 1.36.2 structural and Restricted Pod Security policy checks; their nginx image tag/index digest and documented non-root layout were verified. Runtime image pulls, IAM, networking and application behavior still require validation in your environment.

## Confirm the Operational Context

Use temporary credentials and the intended kubeconfig. This read-only guard compares the account and direct API endpoint; a deliberately proxied kubeconfig needs separate review rather than bypassing a mismatch.

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the intended cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig path}"
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-ops.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,endpoint:endpoint}' --output json > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostic directory: %s\n' "$WORK_DIR"
```

The manifests assume a reviewed `default` NodeClass. Select only the examples you need, replace resource names/network identifiers deliberately, and review the resulting capacity and costs. Lab pools use an `ops-lab` taint and workloads use matching tolerations/pool selectors; these are placement controls, not a tenant-security boundary.

## Budgets Are Combined, Not Overridden

Every applicable NodePool budget contributes to the minimum allowed disruption count. Adding a scheduled `30%` budget cannot make an always-active `10%` budget more permissive. Percentages round up, and deleting/not-ready nodes reduce the remaining allowance.

This explicit calendar uses a 30% ceiling, a 10% weekday ceiling and a one-node business-hours ceiling. Karpenter schedules are UTC:

| Entry | UTC schedule | Intended window |
|-------|--------------|-----------------|
| 30% | Always | Outer ceiling |
| 10% | Sunday–Thursday 15:00, duration 24h | Monday–Friday calendar days in Seoul |
| 1 node | Monday–Friday 00:00, duration 9h | Seoul 09:00–18:00 business hours |
| 0 nodes | First day of month 00:00, duration 24h | Explicit **UTC** monthly freeze |

For 20 otherwise healthy nodes, the example permits six new voluntary disruptions on a weekend, two on a weekday outside business hours, one during business hours, and zero in the freeze. These are example policy choices, not universal production recommendations.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-calendar
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 30%
    - nodes: 10%
      schedule: 0 15 * * sun-thu
      duration: 24h
    - nodes: '1'
      schedule: 0 0 * * mon-fri
      duration: 9h
    - nodes: '0'
      schedule: 0 0 1 * *
      duration: 24h
  limits:
    cpu: '100'
    memory: 400Gi
```

The previous hourly `9-18`/`9-21` cron ranges and repeated 48-hour weekend windows overlapped beyond their stated hours. A schedule starts a window; it is not a list of hours in which a long window should restart.

## Replacement and Application Availability

A one-node budget rate-limits applicable graceful actions. It does not guarantee that expiration, interruption or repair happens sequentially. `expireAfter` is not a minimum uptime promise, and changing it does not rewrite existing NodeClaims. Auto Mode's default expiry/grace behavior and maximum lifetime still apply.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-rolling
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '100'
    memory: 400Gi
```

An empty-node consolidation policy does not disable drift or expiry. `do-not-disrupt` is not an indefinite retention guarantee: Node and Pod controls have different scope, and an explicit/default termination grace period changes how blocking Pods affect drift and final termination. Review the [disruption guide](https://karpenter.sh/v1.14/concepts/disruption/) before using it for a maintenance window.

### PDB example

The following namespace pins Restricted policy to the reviewed Kubernetes version. The image runs as UID/GID 101, listens on 8080, and uses `/tmp` for PID/temp paths; it needs the writable emptyDir even though the container root filesystem is read-only. The image's stop signal is SIGQUIT. These details are not interchangeable with a root-running nginx image on port 80.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ops-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: ops-lab
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: ops-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-calendar
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

With five desired healthy replicas, `minAvailable: 3` permits up to two voluntary Pod evictions, subject to other constraints. `maxUnavailable: 1` would be a different, more restrictive choice, not an equivalent spelling.

PDBs constrain Eviction API decisions using healthy/Ready Pods; they do not make replicas exist or protect against every failure/direct deletion. Percentage values round up: `minAvailable: "80%"` for six replicas requires five healthy replicas, while a `maxUnavailable: "30%"` budget for one replica can allow that one replica to be evicted.

For stateful systems, use the application's actual quorum and readiness semantics. Two healthy members may suit a three-voter majority system; a five-voter system needs three. No single `minAvailable: 2` recommendation fits all stateful workloads. A singleton PDB can deliberately block voluntary drain but cannot create high availability.

## AZ Placement Is Not Guaranteed Capacity or Failover

The dynamic pool's `limits.cpu` is an aggregate ceiling, not a per-AZ minimum. The example lists possible AZs, but the NodeClass subnets, capacity and scheduling constraints determine what is eligible.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-multi-az
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
        - ap-northeast-2b
        - ap-northeast-2c
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
  namespace: ops-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-app
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: ha-app
      containers:
      - name: app
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-multi-az
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

Six replicas do not by themselves prove a 3-AZ × 2 layout. This example requires at least two eligible domains; adjust only after evaluating your actual subnet coverage and failure policy. Hard `DoNotSchedule` constraints can leave Pods Pending during an AZ impairment.

If you require one replica per node, the following affinity fragment can be added to a reviewed Pod template. Nine replicas with this constraint require at least nine eligible nodes; they still do not prove three-AZ availability without the corresponding topology and capacity.

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

Active-active/standby designs also need application state, health checks and traffic/failover control. ARC zonal shift is supported for Auto Mode and can avoid new capacity in an impaired AZ; autoshift needs its own configuration. It does not make an AZ-bound volume or a hard placement constraint portable.

### Existing capacity reservations

Naming a pool `reserved-capacity`, allowing On-Demand and setting a CPU limit does not create a reservation. To consume an approved existing reservation, select it in a custom NodeClass and permit `reserved` capacity. Replace the example reservation ID and verify account, AZ, type, status, permissions and available reserved capacity.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: reserved-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  capacityReservationSelectorTerms:
  - id: cr-0123456789abcdef0
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: reserved-nodeclass
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
```

These manifests do not create the EC2 reservation or a fixed number of nodes. Reservations can incur charges even while unused. For desired node counts independent of Pod demand, Auto Mode supports static pools using `spec.replicas`, with distinct limits/weight/consolidation and scaling semantics; see the static-capacity reference. A desired count still requires successful provisioning and healthy capacity.

## Monitoring Must Match Its Publisher

EKS control-plane metrics, configured Container Insights, self-managed Prometheus exporters and Auto Mode component logs are different interfaces. Do not assume an automatically populated `Karpenter` CloudWatch namespace containing the former `karpenter_*` names.

Auto Mode managed compute/storage/load-balancer/IPAM logs use separately configured Vended Logs delivery. Basic control-plane logging is not a switch for all managed component logs. Choose a scoped time range and verify IAM, destination and charges.

### Build a dashboard from actual metric metadata

For the `AWS/EKS` control-plane namespace, first discover the metrics actually returned for the reviewed cluster:

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

Choose the exact catalog index and the metric's appropriate documented statistic. The following local generator preserves its real namespace/dimensions and includes the widget region. It rejects a missing or wrong-cluster entry instead of creating an invented metric panel.

```bash
: "${METRIC_INDEX:?Choose an exact entry from the captured catalog}"
: "${METRIC_STAT:?Choose the documented statistic for that metric, such as Maximum}"
export METRIC_INDEX METRIC_STAT AWS_REGION CLUSTER_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
metrics = json.loads((folder / "metric-catalog.json").read_text())["Metrics"]
index = int(os.environ["METRIC_INDEX"])
if index < 0 or index >= len(metrics):
    raise SystemExit("Metric is absent; verify collection instead of creating an empty widget")
metric = metrics[index]
if metric["Namespace"] != "AWS/EKS" or not any(
    d["Name"] == "ClusterName" and d["Value"] == os.environ["CLUSTER_NAME"]
    for d in metric["Dimensions"]
):
    raise SystemExit("Metric catalog entry does not match the reviewed cluster")
stat = os.environ["METRIC_STAT"]
if stat not in {"Average", "Sum", "Minimum", "Maximum", "SampleCount"}:
    if not re.fullmatch(r"p[0-9]+(?:\.[0-9]+)?", stat) or not 0 <= float(stat[1:]) <= 100:
        raise SystemExit("Unsupported statistic for this template")
series = [metric["Namespace"], metric["MetricName"]]
for dim in sorted(metric["Dimensions"], key=lambda d: d["Name"]):
    series.extend([dim["Name"], dim["Value"]])
body = {"widgets": [{"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
    "properties": {"title": metric["MetricName"], "region": os.environ["AWS_REGION"],
                   "view": "timeSeries", "metrics": [series], "stat": stat, "period": 60}}]}
(folder / "dashboard.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

Review `dashboard.json` before creating/updating a dashboard through your approved workflow. Catalog presence is not proof of datapoints in every time range. Node-pool counts, provisioning latency and application SLOs need their actual publishers/instrumentation; Container Insights alone should not be assumed to produce every signal.

## Structured Kubernetes Diagnostics

Use NodeClaim conditions rather than a nonexistent `.status.phase`, and avoid treating every Pending Pod as a node-capacity request:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodepools -o json |
  jq '[.items[] | {name:.metadata.name,limits:.spec.limits,resources:.status.resources,
      requirements:.spec.template.spec.requirements,disruption:.spec.disruption,
      conditions:[.status.conditions[]? | {type,status,reason,observedGeneration}]}]'
```

```bash
: "${WORKLOAD_NAMESPACE:?Select the workload namespace}"
: "${POD_NAME:?Select the Pod}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pod "$POD_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,phase:.status.phase,
       nodeSelector:.spec.nodeSelector,affinity:.spec.affinity,tolerations:.spec.tolerations,
       conditions:[.status.conditions[]? | {type,status,reason,lastTransitionTime}],
       containers:[.status.containerStatuses[]? |
         {name,ready,restartCount,waitingReason:.state.waiting.reason}]}'
```

For node distribution, parse structured fields instead of a human table column. This counts active Pod objects, including assigned-but-not-ready Pods, and separates unassigned objects:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

Use `kubectl top` only when the metrics API is configured and healthy. A failed query is not proof that metrics-server is absent. Review event reasons and managed compute logs for actual failures such as incompatible instance types, NodeClass readiness, IAM or network problems. Lowering `consolidateAfter` does not speed up Spot interruption recovery.

### PDB allowance is not a compliance verdict

Zero `disruptionsAllowed` can be intentional and healthy. Check generation freshness and current versus desired health before interpreting it:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[] | {
    namespace: .metadata.namespace, name: .metadata.name,
    currentHealthy: .status.currentHealthy, desiredHealthy: .status.desiredHealthy,
    disruptionsAllowed: .status.disruptionsAllowed,
    assessment: (if .status.observedGeneration != .metadata.generation
                    or .status.currentHealthy == null or .status.desiredHealthy == null
                    or .status.disruptionsAllowed == null
                  then "UnknownOrStale"
                  elif .status.currentHealthy < .status.desiredHealthy then "BelowDesiredHealthy"
                  elif .status.disruptionsAllowed == 0 then "HealthyNoVoluntaryEvictions"
                  else "EvictionsPermitted" end)
  }]'
```

Do not delete or relax a blocking PDB until you understand the workload availability requirement and recovery plan.

### Node object age

Node object creation time is not EC2 launch time or AMI patch age. Choose a diagnostic threshold for your policy; the old fixed “greater than seven whole days” script both truncated time and assumed an inappropriate universal limit.

```bash
: "${MAX_NODE_OBJECT_AGE_HOURS:?Set a reviewed diagnostic threshold in hours}"
export MAX_NODE_OBJECT_AGE_HOURS
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
  jq '{items:[.items[] | {name:.metadata.name,createdAt:.metadata.creationTimestamp}]}' \
  > "$WORK_DIR/node-times.json"
python3 - <<'PY'
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
limit = float(os.environ["MAX_NODE_OBJECT_AGE_HOURS"])
if not math.isfinite(limit) or limit <= 0:
    raise SystemExit("Set a finite positive threshold")
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-times.json").read_text())["items"]:
    result = {"node": item["name"], "thresholdHours": limit}
    try:
        created = datetime.fromisoformat(item.get("createdAt").replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("timestamp is not usable")
        hours = (now - created).total_seconds() / 3600
        result.update(nodeObjectAgeHours=round(hours, 3), exceedsThreshold=hours > limit)
    except (ValueError, TypeError, AttributeError):
        result["assessment"] = "UnknownTimestamp"
    rows.append(result)
print(json.dumps(rows, indent=2))
PY
```

Unknown or future timestamps are not reported as healthy. Compare the observed NodeClaim policy, image information and AWS maintenance/security context before diagnosing overdue rotation. This local report does not create a CloudWatch alarm.

## Security Configuration

Auto Mode selects its managed Bottlerocket image and fixed IMDSv2/hop-limit settings. The earlier `amiFamily`, `metadataOptions`, `blockDeviceMappings` and malformed KMS ARN example was not valid Auto Mode NodeClass configuration.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ops-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
```

Review the profile's node role/access entry, actual private routing and security-group rules. Tags alone do not prove network restriction. Node root/data EBS encryption does not establish application PVC encryption. For a customer-managed key or CA bundle, use the valid `ephemeralStorage.kmsKeyID`/certificate procedure in [NodePool configuration](./02-nodepool-configuration.md), with reviewed IAM and key policies.

The Restricted namespace example requires compatible workload security contexts. Do not force node-level monitoring agents with host access into it or disable cluster-wide security to make an agent work; review the collector's separate permissions and namespace policy.

## Optional Prometheus Queries and Alerts

These examples assume **one cluster**, an installed kube-state-metrics collector and Linux node-exporter metrics. Before using them:

- Allowlist the Node labels `karpenter.sh/nodepool` and `eks.amazonaws.com/compute-type` in kube-state-metrics.
- Ensure the CPU series has a correctly mapped `node` label. That label is not automatically present in every node-exporter scrape configuration.
- Deduplicate kube-state-metrics replicas before joins/counts. There must be one current NodePool label per node.
- For multiple clusters, preserve a real cluster label on all sources and include it in every grouping and join.

The node queries filter Auto Mode nodes; Pod pending/unschedulable signals are cluster-wide and require diagnosis before attributing them to Auto Mode. CPU below is **non-idle time per node**, not a resource request ratio or capacity-weighted pool mean. A missing series is not automatically zero usage.

```promql
# nodes_by_pool
count by (label_karpenter_sh_nodepool) (max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))

# cpu
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",node!=""}[5m])))
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# pending
sum(max by (namespace, pod, uid) (kube_pod_status_phase{phase="Pending"}))

# unschedulable
sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable))

# age
((time() - max by (node) (kube_node_created)) / 86400)
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# not_ready
max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})
```

With Prometheus Operator installed, place the following rule in a namespace selected by your Prometheus instance and match its `ruleSelector`. Thresholds and durations are illustrative. The rules do not establish that every provisioning failure is represented by a termination counter.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: auto-ops-example
  namespace: monitoring
spec:
  groups:
  - name: auto-ops-example
    rules:
    - alert: ReportedUnschedulablePods
      expr: sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable)) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Reported unschedulable Pods exceed the example threshold
    - alert: AutoNodeNotReady
      expr: '(max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})

        * on (node) group_left (label_karpenter_sh_nodepool)

        max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))
        == 1'
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A registered Auto Mode node is not Ready
```

## Review Cadence

| Cadence | Evidence to review |
|---------|--------------------|
| Daily | Sustained scheduling/NodeClaim errors, Node conditions, workload health, current PDB allowance and collector freshness |
| Weekly | Disruption/drift events, observed node/object age, actual capacity/Spot distribution, resource requests and billing trends |
| Before/monthly change review | IAM/network/storage policy, compatible software and image updates, tested recovery, quotas and future workload needs |

The prior “Pending 0–5”, “CPU/memory below 80%”, “startup below 90 seconds”, “99.9% availability” and response-time ranges were unverified planning heuristics, not Auto Mode normal ranges or default SLOs. Define thresholds from application objectives and measured behavior rather than labeling every transition or zero PDB allowance as a violation.

## References

- [Auto Mode NodePool behavior](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Disruption budgets, drift and termination](https://karpenter.sh/v1.14/concepts/disruption/)
- [Configure a PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Topology spread constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Auto Mode static capacity](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [NodeClass and capacity reservation selectors](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [Managed component log delivery](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Control-plane metrics and CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [CloudWatch dashboard structure](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [Kube-state-metrics node metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Kube-state-metrics Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [NGINX unprivileged image](https://github.com/nginx/docker-nginx-unprivileged)

< [Previous: Spot Strategies](./04-spot-strategies.md) | [Table of Contents](./README.md) | [Next: Cost Management](./06-cost-management.md) >
