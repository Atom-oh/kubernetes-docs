# EKS Auto Mode Scaling Behavior Quiz

> **Related Document**: [Scaling Behavior](../../eks-auto-mode/03-scaling-behavior.md)

## Multiple Choice Questions

### 1. What does `consolidationPolicy: WhenEmptyOrUnderutilized` permit?

- A) Only empty-node removal
- B) Cost-saving consolidation of eligible empty or non-empty nodes
- C) Keeping all nodes indefinitely
- D) Removal only at a fixed clock time

<details>
<summary>Show Answer</summary>

**Answer: B) Cost-saving consolidation of eligible empty or non-empty nodes**

**Explanation:**
It permits removal or cheaper replacement when the workloads remain schedulable under the relevant constraints. Resource requests, PDBs, budgets and annotations matter; it is not simply a measured-CPU threshold.

```yaml
# Fragment inside a NodePool; eligibility delay, not a deletion deadline
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m
```

The timer resets when Pods are added or removed. One minute is an eligibility/stability delay, not a guarantee that deletion or replacement finishes in one minute. The current AWS API also supports `Balanced`, which considers disruption cost alongside savings.

</details>

### 2. Which command lists NodeClaims?

- A) kubectl get nodes --show-claims
- B) kubectl get nodeclaims
- C) kubectl describe karpenter claims
- D) kubectl get ec2-nodes

<details>
<summary>Show Answer</summary>

**Answer: B) kubectl get nodeclaims**

**Explanation:**
NodeClaims describe desired node configuration and provider lifecycle/status, not just the instant of provisioning. Inspect conditions and the linked node name; `Drifted` is a condition, not the old fictitious `karpenter.sh/drift-hash` node annotation.

```bash
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodeclaims -o wide
: "${NODECLAIM_NAME:?Select a NodeClaim from the list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe nodeclaim "$NODECLAIM_NAME"
```

</details>

### 3. When can an unschedulable Pod lead Auto Mode to provision capacity?

- A) Every Pod has spent five minutes Pending
- B) The Pod cannot fit existing capacity and a compatible eligible pool/capacity can satisfy its constraints
- C) Node count is below a fixed global threshold
- D) Only after an operator runs a manual scale command

<details>
<summary>Show Answer</summary>

**Answer: B) The Pod cannot fit existing capacity and a compatible eligible pool/capacity can satisfy its constraints**

**Explanation:**
The scheduler's inability to place the Pod, matching NodePool/NodeClass constraints, quotas and actual capacity all matter. A scheduled Pod waiting for an image or init container can be Pending without needing a new node. Auto Mode does not guarantee immediate allocation or the earlier unverified 40–90-second estimate.

</details>

### 4. Which can block consolidation of a candidate node?

- A) An applicable do-not-disrupt annotation
- B) A PDB blocks required workload eviction
- C) The consolidateAfter stability interval has not elapsed
- D) All of the above

<details>
<summary>Show Answer</summary>

**Answer: D) All of the above**

**Explanation:**
Each can prevent or delay a consolidation action. The former answer incorrectly included DaemonSet-only nodes as a blocker: such nodes can qualify as empty.

```yaml
# Metadata fragment on the intended Node or Pod, not NodePool metadata
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

This is not a guarantee against every disruption reason. Expiration, interruptions and termination-grace limits must be considered separately. Remove temporary protection after its intended maintenance need ends.

</details>

### 5. Which can contribute to drift or replacement?

- A) Relevant desired NodeClass configuration no longer matches the node
- B) AWS selects a new managed Auto Mode AMI
- C) Resolved subnet/security-group selection changes
- D) All of the above can contribute

<details>
<summary>Show Answer</summary>

**Answer: D) All of the above can contribute**

**Explanation:**
Inspect actual NodeClaim conditions and provider decisions. Not every edit causes drift: widening requirements can leave existing instances compatible, and weight/limits/disruption settings are behavioral. Editing rules on the same security group is not the same as resolving a different group. Graceful replacement is subject to scheduling and budgets and can be parallel; it is not always a sequential one-node-at-a-time process.

</details>

### 6. How should you improve Auto Mode startup latency?

- A) Switch amiFamily to AL2023
- B) Measure the workload path and test supported capacity, image and storage changes
- C) Assume the smallest possible volume is always fastest
- D) Treat 40–90 seconds as a guaranteed end-to-end SLO

<details>
<summary>Show Answer</summary>

**Answer: B) Measure the workload path and test supported capacity, image and storage changes**

**Explanation:**
AWS selects the managed Bottlerocket image. Auto Mode does not offer the old `amiFamily` comparison knob. Separate node registration, image/initialization time and application readiness, and include failures/timeouts in measurements.

The previous quiz's **AL2023 20–40 seconds** and **Bottlerocket 15–25 seconds** are preserved as unverified historical teaching estimates. They are not measured Auto Mode results and do not establish a current boot-time advantage or supported AMI choice.

</details>
