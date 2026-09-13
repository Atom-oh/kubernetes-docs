# EKS Auto Mode Operations Quiz

> **Related Document**: [Operations](../../eks-auto-mode/05-operations.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. Which scheduled setting blocks applicable voluntary NodePool disruptions during Seoul business hours?

- A) `nodes: "100%"`
- B) `nodes: "0"` with a correctly bounded UTC schedule
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>Show Answer</summary>

**Answer: B) `nodes: "0"` with a correctly bounded UTC schedule**

**Explanation:**
A zero budget blocks applicable graceful methods such as consolidation and drift while active. It does not stop EC2 interruption, expiration, repair or every manual deletion. The daily UTC 00:00 start and nine-hour duration below correspond to Seoul 09:00–18:00 on weekdays. An hourly `9-18` schedule with a nine-hour duration repeatedly starts overlapping windows.
```yaml
# Fragment of NodePool spec.disruption
budgets:
  - nodes: "10%"
  - nodes: "0"
    schedule: "0 0 * * mon-fri"
    duration: 9h
```


</details>

### 2. What does `minAvailable: "80%"` mean for a PDB selecting six replicas of one scalable controller?

- A) No more than 80% may run
- B) Eviction decisions require five healthy replicas after rounding up
- C) Each Pod has an 80% chance of retention
- D) The Pods are protected for 80 seconds

<details>
<summary>Show Answer</summary>

**Answer: B) Eviction decisions require five healthy replicas after rounding up**

**Explanation:**
The controller rounds 80% of six up to five healthy/Ready replicas. This constrains Eviction API decisions, not all failures, direct deletions or replica creation. `minAvailable` and `maxUnavailable` are alternative fields with different meanings; do not configure both. The source example with five replicas and `minAvailable: 3` permits up to two evictions, unlike `maxUnavailable: 1`.
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: ops-lab
spec:
  minAvailable: "80%"
  selector:
    matchLabels:
      app: web-app
```

Zero `disruptionsAllowed` can be a healthy intentional block. Inspect `observedGeneration`, `currentHealthy` and `desiredHealthy` before calling it a violation.

</details>

### 3. Which resource helps diagnose the provisioning lifecycle of an Auto Mode node?

- A) Only application logs
- B) NodeClaim conditions, followed by related NodePool/NodeClass evidence
- C) Only the EC2 console
- D) Only a CloudWatch widget

<details>
<summary>Show Answer</summary>

**Answer: B) NodeClaim conditions, followed by related NodePool/NodeClass evidence**

**Explanation:**
Read conditions and reasons, then investigate scheduling constraints, NodeClass readiness, IAM and network configuration as the evidence requires. A NodeClaim has no general `.status.phase` field. The following uses the reviewed `KUBE_CONTEXT` established in the related guide and selects diagnostic fields instead of dumping complete objects.
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```


</details>

### 4. Which is the recognized do-not-disrupt annotation?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>Show Answer</summary>

**Answer: B) `karpenter.sh/do-not-disrupt: "true"`**

**Explanation:**
Pod and Node placement have different scope. A Pod annotation blocks its voluntary eviction and consolidation of its node; a NodeClaim termination grace period allows drift of a node containing such Pods and ultimately bounds draining. A Node annotation excludes the node from voluntary disruption. Neither is an indefinite guarantee against expiration, interruption, repair or manual deletion. Auto Mode has its own default termination grace period; do not assume it is unset.
```yaml
# Metadata fragment for a deliberately selected Pod or Node.
# Review the different Pod/Node semantics before applying.
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

A metadata fragment is not a complete runnable Pod. Set a recovery/removal plan before applying this control to a real workload.

</details>

### 5. Which monitoring approach gives useful evidence for Auto Mode operations?

- A) Use `kubectl top` alone
- B) Combine configured collectors/log delivery with Kubernetes conditions and workload signals
- C) Use the EC2 console alone
- D) Assume every metric exists in CloudWatch without collection setup

<details>
<summary>Show Answer</summary>

**Answer: B) Combine configured collectors/log delivery with Kubernetes conditions and workload signals**

**Explanation:**
Container Insights, EKS control-plane metrics, kube-state-metrics/node-exporter and managed Auto Mode component logs have separate prerequisites. Verify each publisher and dimensions. `kubectl top` requires a functioning metrics API; an error does not prove metrics-server is absent. Managed component logs require their own Vended Logs delivery configuration. Scheduling latency and application availability need appropriate instrumentation; enabling Container Insights does not automatically produce every proposed signal.

</details>

### 6. Which NodePool field sets age-based expiration eligibility?

- A) `autoUpdate: true`
- B) `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>Show Answer</summary>

**Answer: B) `expireAfter`**

**Explanation:**
The example makes a NodeClaim eligible for expiration after 168 hours and bounds its termination phase separately. It does not promise uninterrupted seven-day uptime, exactly timed replacement or the latest security patch by that deadline. Earlier drift/consolidation/interruption is possible, and changing the template does not rewrite existing NodeClaims. Check Auto Mode defaults/maximum lifetime and application recovery requirements.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 7. How do multiple applicable NodePool disruption budgets combine?

- A) The latest scheduled entry overrides earlier entries
- B) The smallest allowance wins
- C) Their percentages add together
- D) They set a guaranteed number of replacement nodes

<details>
<summary>Show Answer</summary>

**Answer: B) The smallest allowance wins**

**Explanation:**
An always-active 10% ceiling cannot be relaxed by a scheduled 30% budget. The related guide instead starts with 30%, adds a 10% Seoul-weekday ceiling and a one-node business-hours ceiling, plus an explicit UTC monthly freeze. For 20 otherwise healthy nodes the allowances are six, two, one and zero respectively. Deleting/not-ready nodes reduce the allowance; these budgets do not constrain every forceful disruption.
```yaml
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
```


</details>

### 8. Which signals can help define node-related operational alerts when their publishers are configured?

- A) EC2 status only
- B) Scheduling backlog, measured provisioning latency and workload availability
- C) Cost only
- D) Network traffic only

<details>
<summary>Show Answer</summary>

**Answer: B) Scheduling backlog, measured provisioning latency and workload availability**

**Explanation:**
Choose a publisher, dimensions, statistic, time window and application objective for each alert. Pending is not synonymous with unschedulable. The original numeric examples below are retained as unverified planning thresholds, not measured normal ranges, Auto Mode defaults or guaranteed Container Insights metrics.

| Signal | Previous planning example | Previous alert example |
|--------|---------------------------|------------------------|
| Pending Pods | 0–5 | >10 for 5 min |
| Node provisioning time | <90 sec | >120 sec |
| Workload availability | >99.9% | <99.5% |
| API response time | <200 ms | >500 ms |

Missing metrics or stale collectors must remain distinguishable from zero errors. The guide builds a local CloudWatch dashboard definition from an actual metric catalog instead of inventing metric names.

</details>

## References

- [Karpenter disruption controls](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kubernetes PDB semantics](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Auto Mode NodePools](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
