# EKS Auto Mode Workload Optimization Quiz

> **Related Document**: [Workload Optimization](../../eks-auto-mode/08-workload-optimization.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. Which is a reasonable starting point for an availability-sensitive frontend?

- A) Assume Spot-only is always appropriate
- B) On-Demand with application availability and disruption controls
- C) Always require GPUs
- D) Use only memory-optimized nodes

<details>
<summary>Show Answer</summary>

**Answer: B) On-Demand with application availability and disruption controls**

**Explanation:**
On-Demand avoids Spot reclaim events but is not an availability guarantee. Replicas, topology, readiness, PDBs and recovery must be tested. The alternative budget below starts one daily window at UTC 00:00 for 14 hours: Seoul 09:00–23:00. It does not use the old hourly `9-23` pattern, which repeatedly extended the window. Active budgets combine by minimum and do not control every forceful disruption.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
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
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
    - nodes: '1'
      schedule: 0 0 * * *
      duration: 14h
  limits:
    cpu: '32'
    memory: 128Gi
```


</details>

### 2. Which pool can suit a batch workload that has demonstrated interruption tolerance and durable recovery?

- A) On-Demand is the only possible option
- B) Spot with compatible instance diversity and empty-node cleanup
- C) Only GPUs
- D) The system pool by default

<details>
<summary>Show Answer</summary>

**Answer: B) Spot with compatible instance diversity and empty-node cleanup**

**Explanation:**
Not every batch job tolerates interruption. Spot-only has no On-Demand fallback. Container restart or `SPOT_AWARE=true` is not checkpoint/resume logic; use idempotent outputs and durable progress. `WhenEmpty` with a 30s debounce does not kill a running job after 30 seconds. The related guide provides a bounded Indexed smoke Job, not a production data processor.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
```


</details>

### 3. How should a 15-minute `consolidateAfter` for an inference pool be interpreted?

- A) A guaranteed GPU startup deadline
- B) An illustrative consolidation debounce/churn trade-off
- C) A delay before the scheduler may place any Pod
- D) A guarantee that the node never expires

<details>
<summary>Show Answer</summary>

**Answer: B) An illustrative consolidation debounce/churn trade-off**

**Explanation:**
It does not make a GPU Ready or guarantee warm capacity. `WhenEmpty` narrows consolidation; drift, expiration and interruption are separate. Match model warm-up, desired capacity and cost to measured behavior. The guide's inference template stays at zero replicas until a reviewed image/runtime/probes are supplied. A 4 CPU/16Gi Pod also cannot fit a g5.xlarge after system reservations.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
```


</details>

### 4. What may balance cost and availability for a compatible, interruption-tolerant application API backend?

- A) On-Demand is always wrong
- B) Spot-only always guarantees availability
- C) Evaluate mixed Spot/On-Demand and tested ARM support
- D) Assume Auto Mode provisions Fargate nodes

<details>
<summary>Show Answer</summary>

**Answer: C) Evaluate mixed Spot/On-Demand and tested ARM support**

**Explanation:**
This concerns an application API backend, not the AWS-managed Kubernetes API server. Mixed capacity is not a fixed ratio or immediate fallback, and ARM requires compatible images/dependencies and application tests. `weight: 10` is a relative provisioning preference, not a percentage or spending limit. The original ~40% saving is unverified.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: api-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: api-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 10
```


</details>

### 5. What should be verified before permitting both amd64 and arm64?

- A) Nothing
- B) The pinned image platforms, native dependencies and application behavior
- C) Only Kubernetes version
- D) Only region

<details>
<summary>Show Answer</summary>

**Answer: B) The pinned image platforms, native dependencies and application behavior**

**Explanation:**
The index check below establishes Linux platform entries, not runtime correctness. It ignores unrelated attestation entries and rejects missing platforms. The related guide shows a local OCI build output; publishing an unspecified `myapp:latest` image is not a required architecture test.

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```


</details>

### 6. How do workloads select the intended pool while tolerating its placement restriction?

- A) Pod-name matching
- B) A matching toleration plus nodeSelector or required node affinity
- C) Automatic namespace matching
- D) AWS tags alone

<details>
<summary>Show Answer</summary>

**Answer: B) A matching toleration plus nodeSelector or required node affinity**

**Explanation:**
A toleration permits placement on a tainted node but does not require that node. The selector or required affinity narrows eligible nodes. The fragment below belongs in the Pod template's `spec`; the source includes a complete Job. Labels/taints are not a tenant authorization boundary, and insufficient matching capacity can still leave a Pod Pending.
```yaml
nodeSelector:
  karpenter.sh/nodepool: batch-tier
tolerations:
- key: workload-lab
  operator: Equal
  value: batch-tier
  effect: NoSchedule
```


</details>

## References

- [Auto Mode ML compute](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Karpenter disruption](https://karpenter.sh/v1.14/concepts/disruption/)
- [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)
