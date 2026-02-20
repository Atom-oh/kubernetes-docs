# EKS Auto Mode Workload Optimization Quiz

> **Related Document**: [Workload Optimization](../../eks-auto-mode/08-workload-optimization.md)

## Multiple Choice Questions

### 1. What is the recommended NodePool setting for frontend workloads on a large-scale e-commerce platform?

- A) Spot only, aggressive Consolidation
- B) On-Demand priority, availability-focused Disruption Budget
- C) GPU instances, high-performance settings
- D) Memory-optimized instances only

<details>
<summary>Show Answer</summary>

**Answer: B) On-Demand priority, availability-focused Disruption Budget**

**Explanation:**
Frontend workloads are user-facing, so availability is the top priority.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend-tier
spec:
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # Availability first
      taints:
        - key: tier
          value: frontend
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
      - nodes: "1"
        schedule: "0 9-23 * * *"  # Peak hours
        duration: 14h
```

</details>

### 2. What is the most suitable NodePool setting for batch processing workloads?

- A) On-Demand only, conservative Consolidation
- B) Spot only, diverse instance families, quick cleanup
- C) Use only GPU instances
- D) Place in system NodePool

<details>
<summary>Show Answer</summary>

**Answer: B) Spot only, diverse instance families, quick cleanup**

**Explanation:**
Batch jobs are interrupt-tolerant, making them suitable for Spot instances.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r", "i", "d"]  # Diverse families
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s  # Quick cleanup
```

</details>

### 3. What is the recommended Consolidation setting for GPU ML inference workloads?

- A) `consolidateAfter: 0s`
- B) `consolidateAfter: 15m` (considering GPU startup time)
- C) `consolidationPolicy: WhenEmptyOrUnderutilized`
- D) Disable Consolidation

<details>
<summary>Show Answer</summary>

**Answer: B) `consolidateAfter: 15m` (considering GPU startup time)**

**Explanation:**
GPU instances take longer to start, requiring sufficient consolidateAfter.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-inference
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m  # Consider GPU startup time
```

</details>

### 4. What strategy balances stability and cost for API server workloads?

- A) On-Demand only
- B) Spot only
- C) Spot/On-Demand mixed + Include Graviton
- D) Fargate only

<details>
<summary>Show Answer</summary>

**Answer: C) Spot/On-Demand mixed + Include Graviton**

**Explanation:**
API servers need appropriate availability while enabling cost optimization.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    metadata:
      labels:
        tier: api
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]  # Mixed
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
      taints:
        - key: tier
          value: api
          effect: NoSchedule
  weight: 10
```

**Expected cost savings:** ~40%

</details>

### 5. What should be verified in applications for multi-architecture (amd64/arm64) support?

- A) No special verification needed
- B) Verify that container images support multi-arch
- C) Only check Kubernetes version
- D) Only check AWS region

<details>
<summary>Show Answer</summary>

**Answer: B) Verify that container images support multi-arch**

**Explanation:**
To utilize Graviton (arm64) instances, container images must support that architecture.

```bash
# Check image supported architectures
docker manifest inspect nginx:latest | grep architecture

# Multi-arch image build example
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:latest \
    --push .
```

**Checklist:**
- Verify base image multi-arch support
- Build native binaries for both architectures
- Configure multi-arch build in CI/CD pipeline

</details>

### 6. What is the method to ensure Pods schedule to the correct NodePool when separating NodePools by workload?

- A) Auto-matching by Pod name
- B) Use Taint/Toleration and NodeSelector or Affinity
- C) Automatic separation by namespace
- D) Separation by AWS tags only

<details>
<summary>Show Answer</summary>

**Answer: B) Use Taint/Toleration and NodeSelector or Affinity**

**Explanation:**
Set taints on NodePool and add tolerations and affinity to Pods.

```yaml
# Set taint on NodePool
spec:
  template:
    spec:
      taints:
        - key: tier
          value: batch
          effect: NoSchedule

---
# Set toleration and affinity on Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: tier
                    operator: In
                    values: ["batch"]
```

</details>
