# Node Lifecycle Management

> **Supported Versions**: EKS Auto Mode GA; examples reviewed for EKS 1.36
> **Last Updated**: September 12, 2026

Expiration, managed image updates and application recovery are different parts of a node lifecycle. A young Kubernetes Node object is not proof that every CVE is patched or that a workload is compliant. These examples were reviewed against official sources and local schemas/fixtures; no live node rotation, cloud mutation or benchmark was performed.

## Expiration and the Auto Mode Lifetime Limit

`spec.template.spec.expireAfter` determines age-based expiration of NodeClaims created from that template. The old Provisioner-era `ttlSecondsUntilExpired` field is not used in these `karpenter.sh/v1` NodePools.

Distinguish three settings:

| Concept | Auto Mode behavior |
|---------|--------------------|
| Default expiration | AWS documents **336h (14 days)**, not 7 or 21 days |
| Termination grace | If omitted on the NodePool, Auto Mode defaults **24h on the NodeClaim**; inspect the claim even when the pool does not show it |
| Managed instance maximum lifetime | AWS enforces **21 days (504h)**; this is not a promise that a node will remain available until then |

The upstream Karpenter 720h default must not be substituted for Auto Mode's defaults. A larger duration or upstream `Never` syntax does not provide indefinite retention of an Auto Mode managed instance. Do not treat 504h plus a long drain as a way to extend the AWS maximum.

Use the account/context guard and private `WORK_DIR` in [Operations](./05-operations.md) before the read-only commands below. The example pools assume a reviewed `default` NodeClass. They are bounded, tainted lab configurations; matching workload selectors/tolerations and application recovery testing are required.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

### What expiration actually does

Expiration is a **forceful disruption trigger**. It begins termination/draining after the NodeClaim reaches its policy age and does not wait for a pre-provisioned replacement to become Ready. NodePool disruption budgets do not rate-limit expiration. Workload controllers and provisioning may create replacement capacity as needed; the old five-step “new node Ready, then drain” ordering is not guaranteed here.

The termination controller prevents new ordinary scheduling, attempts Eviction API-based draining, handles volume detach and terminates the instance. PDBs and Pod `do-not-disrupt` can affect draining, but a termination grace deadline and the AWS maximum lifetime mean they are not indefinite availability protection. Pod shutdown grace and node termination grace are different settings. Data on local/ephemeral storage must have a recovery plan.

Changing the pool's `expireAfter` does not rewrite existing NodeClaims; it can induce drift and applies to replacement claims. Other disruption methods can end a node's life earlier. A one-node budget cannot make several simultaneous expirations sequential.

### Choosing a duration

The prior 24h, 48h, 72h, 168h and 336h environment-specific examples are policy choices, not AWS production defaults or required PCI/HIPAA/SOC2 rotation intervals. The former 504h development example represented the service ceiling, not recommended `expireAfter` plus drain time.

Choose a policy from patch urgency, workload checkpointing, cache warm-up, replica/quorum behavior, available capacity and recovery tests. Frequent rotation may increase image pulls, rescheduling and billed recovery work. It does not itself increase the probability that EC2 interrupts a particular Spot instance or guarantee a newly released patch is available.

## Managed AMIs and NodeClass Configuration

Auto Mode uses AWS-managed **Bottlerocket variants**. It does not offer an AL2023/Bottlerocket `amiFamily` switch, custom `amiSelectorTerms`, arbitrary `userData`, SSH or SSM Session Manager access. Those interfaces must not be copied from self-managed Karpenter's EC2NodeClass or ordinary managed node-group recipes.

The supported NodeClass below configures storage/network identity; it does not select or pin an AMI:

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: lifecycle-nodeclass
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

Review its instance-profile role/access entry and actual subnet/security-group selection, then reference `lifecycle-nodeclass` only from the intended pool. Auto Mode's IMDSv2/hop-limit settings are managed, not fields to override with `metadataOptions`. Use `ephemeralStorage` rather than `blockDeviceMappings`; node root/data EBS encryption does not establish application PVC encryption. See [NodePool configuration](./02-nodepool-configuration.md) for supported key/certificate settings.

### Historical OS comparisons are not an Auto Mode selection menu

AL2023 is a general-purpose Amazon Linux distribution with selected Fedora upstream components; it is not simply RHEL. General AL2023 or independently operated Bottlerocket hosts have different management options from locked-down Auto Mode nodes. Auto Mode also supports GPU workloads through its managed images; “GPU therefore requires AL2023” is incorrect here.

The original AL2023 40–60s and Bottlerocket 20–30s/20–40s boot ranges, and quiz ranges 20–40s versus 15–25s, have no verified measurement provenance. They are retained as historical examples, not an OS speed ranking or a prediction for these manifests. Image pulls, architecture, instance type and workload readiness must be measured separately.

## Drift and Managed Image Updates

AWS documents Auto Mode AMI releases roughly weekly and allows eligible nodes to be replaced through drift. That cadence is not a per-CVE patch SLA. A release of a different EKS-optimized AMI family is not automatically an Auto Mode image update.

| Change or observation | Correct interpretation |
|-----------------------|------------------------|
| A managed Auto Mode AMI update | May make existing claims drifted; inspect actual conditions and rollout state |
| NodePool requirement change | Not every change causes drift; widening compatible allowed values may leave an existing node compliant |
| `expireAfter` template change | Existing claims keep their stored value; replacement claims use the updated policy |
| Weight, limits or disruption settings | Behavioral settings, not a blanket drift trigger |
| NodeClass desired-state change | Use supported fields and observe the managed controller; a cosmetic tag is not a guaranteed emergency patch trigger |
| `amiFamily` / `blockDeviceMappings` change | These are not valid Auto Mode NodeClass fields |

Use `Drifted` conditions on NodeClaims. A hash annotation is not a boolean drift status, and no reported condition is not proof of “not drifted.” Read reason/transition/generation information and compare it with the current resource state:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
jq '[.items[] | {
  name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
  createdAt:.metadata.creationTimestamp,deletionTimestamp:.metadata.deletionTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
  imageID:.status.imageID,
  drift:([.status.conditions[]?|select(.type=="Drifted")|
    {status,reason,lastTransitionTime,observedGeneration}] |
    if length == 0 then {status:"NotReported"} else .[0] end),
  conditions:[.status.conditions[]?|{type,status,reason,lastTransitionTime,observedGeneration}]
}]'
```

Drift is a graceful method subject to applicable budgets, scheduling feasibility and draining constraints. The following allows one applicable voluntary disruption and pauses **drift only** on weekdays from UTC 00:00–08:00, equivalent to Seoul 09:00–17:00. The old `0 9-17`/`0 9-18` hourly schedules restarted long overlapping windows.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
    - nodes: '1'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 8h
      reasons:
      - Drifted
  limits:
    cpu: '100'
    memory: 400Gi
```

This does not pause expiration, EC2 interruption or repair. `consolidateAfter` affects consolidation, not an AMI patch deadline. Pod and Node `do-not-disrupt` annotations differ; Auto Mode's default NodeClaim grace matters when evaluating whether a Pod annotation prevents drift.

## Patching and Exceptional Manual Recovery

AWS manages node OS/Auto Mode component patches; you still own application/container dependencies and workload security. Record the actual image information, relevant AWS release/advisory, rollout progress and application checks. A fresh timestamp or a `SecurityPatch` tag is not evidence that a fix is present.

For urgent remediation:

1. Verify that the required managed image/fix is available for this cluster and determine the affected workloads.
2. Review a **single NodeClaim UID**, node mapping, pool, current conditions, PDBs, data durability and spare/obtainable capacity using the intended context.
3. Prefer the managed drift rollout when it meets the requirement. If manual replacement is needed, use a reviewed single-resource maintenance procedure and establish replacement/application readiness before proceeding to another resource.
4. Recheck health and image evidence after each change; stop on unknown state, capacity failure or application regression.

The following gathers evidence only:

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```

`kubectl delete nodes -l ...` is a bulk deletion request, not a sequential rolling update. Manual node/claim deletion is not limited by a NodePool budget; `drain --delete-emptydir-data` can discard local data, and drain alone does not guarantee that a replacement exists. The old quiz's unrestricted deletion commands and tag-change “patch trigger” are therefore not an emergency runbook.

## Consolidation, Drift and Expiration

| Mechanism | Trigger and control |
|-----------|---------------------|
| Consolidation | Cheaper feasible placement based on requests/constraints; graceful disruption controls apply |
| Drift | Existing claim no longer matches desired managed state; graceful disruption controls apply |
| Expiration | Claim age reaches its stored policy; forceful trigger, not constrained by NodePool budgets |

The graceful disruption controller evaluates drift before consolidation, but expiration is a separate forceful path. There is no universal “drift > expiration > consolidation” priority or first-condition-wins contract. A five-day-old node can consolidate before a seven-day expiry; an eight-day-old expired node need not be underutilized before termination begins.

The following are alternative lab policies, not guaranteed cost/security outcomes:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
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
      expireAfter: 336h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
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
      expireAfter: 72h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

`WhenEmpty` narrows consolidation but does not disable drift/expiration. Coordinate applications with the selected expiry and grace; do not infer availability from a policy name.

## Node Object Age and Image Evidence

`Node.metadata.creationTimestamp`, NodeClaim creation time and EC2 launch time are different observations. `Node.status.nodeInfo.osImage` is an OS description, not an AMI ID. The earlier repeated CREATED/AGE timestamp columns and “security patch status” age script did not prove patch state.

Capture selected Node fields, then calculate portable fractional age and explicit buckets. Invalid, missing, timezone-less or future timestamps remain unknown:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '{items:[.items[] | {
  name:.metadata.name,uid:.metadata.uid,createdAt:.metadata.creationTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  osImage:.status.nodeInfo.osImage,kernelVersion:.status.nodeInfo.kernelVersion
}]}' > "$WORK_DIR/node-lifecycle.json"
```

```bash
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-lifecycle.json").read_text())["items"]:
    result = {"node": item["name"], "pool": item.get("pool")}
    try:
        created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("unusable timestamp")
        hours = (now - created).total_seconds() / 3600
        bucket = "<1d" if hours < 24 else "1d–<3d" if hours < 72 else "3d–<7d" if hours < 168 else ">=7d"
        result.update(nodeObjectAgeHours=round(hours, 3), bucket=bucket)
    except (KeyError, AttributeError, TypeError, ValueError):
        result["bucket"] = "UnknownTimestamp"
    rows.append(result)
summary = [{"bucket": bucket, "count": sum(row["bucket"] == bucket for row in rows)}
           for bucket in ("<1d", "1d–<3d", "3d–<7d", ">=7d", "UnknownTimestamp")]
print(json.dumps({"observedAt": now.isoformat(), "nodes": rows, "distribution": summary}, indent=2))
PY
```

The buckets are `[0,1)`, `[1,3)`, `[3,7)` and `>=7` days; exactly seven days belongs to the last bucket. An empty successful Node list is distinguishable from an API error. This snapshot is a diagnostic, not a live-updating dashboard or a patch compliance check.

### Prometheus and Grafana

Install kube-state-metrics and allowlist `karpenter.sh/nodepool` and `eks.amazonaws.com/compute-type`. The following **single-cluster** rule file deduplicates scrapes and joins Auto Mode labels to the Node creation gauge. Multi-cluster queries must retain a real cluster label in every grouping/join. Missing metrics or future timestamps do not become healthy zero-age nodes.

The age alerts retain the old ten-day and three-day standard-deviation thresholds as **illustrative review signals**. They are not Auto Mode defaults; mixed pool policies and normal autoscaling can make age distributions broad. Load this as a Prometheus rule file, or put its groups under `spec` in a PrometheusRule selected by your operator:

```yaml
groups:
- name: node-lifecycle
  rules:
  - record: eks_auto:node_object_age_days
    expr: "(\n  ((time() - max by (node) (kube_node_created)) >= 0) / 86400\n) * on\
      \ (node) group_left (label_karpenter_sh_nodepool)\nmax by (node,label_karpenter_sh_nodepool)\
      \ (\n  kube_node_labels{label_karpenter_sh_nodepool!=\"\",label_eks_amazonaws_com_compute_type=\"\
      auto\"}\n)"
  - alert: ReviewNodeObjectAge
    expr: eks_auto:node_object_age_days > 10
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: Review this node against its actual lifecycle policy
  - alert: ReviewNodeAgeSpread
    expr: stddev(eks_auto:node_object_age_days) > 3
    for: 4h
    labels:
      severity: info
    annotations:
      summary: Age spread is a review signal, not proof of failed rotation
```

```promql
# median_object_age_days
quantile(0.5, eks_auto:node_object_age_days)

# mean_by_pool
avg by (label_karpenter_sh_nodepool) (eks_auto:node_object_age_days)

# oldest_five
topk(5, eks_auto:node_object_age_days)

# less_than_1d
sum((eks_auto:node_object_age_days >= bool 0) * (eks_auto:node_object_age_days < bool 1))

# 1d_to_under_3d
sum((eks_auto:node_object_age_days >= bool 1) * (eks_auto:node_object_age_days < bool 3))

# 3d_to_under_7d
sum((eks_auto:node_object_age_days >= bool 3) * (eks_auto:node_object_age_days < bool 7))

# 7d_or_more
sum(eks_auto:node_object_age_days >= bool 7)
```

`kube_node_created` is a timestamp gauge, not a histogram/counter. There is no default `kube_node_created_bucket`; `rate()` plus `histogram_quantile()` cannot manufacture a node-age histogram. Use `quantile()` for the current age median and explicit boolean buckets for a bar chart. These bucket sums return zero when there are observed nodes but none in the bucket; absent input remains absent.

| Grafana panel | Evidence |
|---------------|----------|
| Current age distribution | The four explicit bucket queries |
| Average by pool / oldest nodes | Label join and `avg` / `topk` |
| Claims approaching expiration | Actual NodeClaim creation time and stored `expireAfter`; Node age alone is insufficient |
| Replacement rate | A configured event/log history or verified counter publisher, not counts inferred from current objects |
| Patch rollout | Managed image/release information, claim conditions and application health |

## References

- [Auto Mode NodePool defaults and termination grace](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode security and maximum instance lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode managed OS and responsibilities](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [NodeClass supported configuration](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Karpenter disruption, expiration and drift](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kube-state-metrics Node metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Prometheus aggregation operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [AL2023 relationship to Fedora](https://docs.aws.amazon.com/linux/al2023/ug/relationship-to-fedora.html)

< [Previous: Cost Management](./06-cost-management.md) | [Table of Contents](./README.md) | [Next: Workload Optimization](./08-workload-optimization.md) >
