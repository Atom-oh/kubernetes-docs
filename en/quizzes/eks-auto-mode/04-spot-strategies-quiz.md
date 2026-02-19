# EKS Auto Mode Spot Strategies Quiz

> **Related Document**: [Spot Instance Strategies](../../eks-auto-mode/04-spot-strategies.md)

## Multiple Choice Questions

### 1. What is the optimal strategy to distribute Spot instance interruption risk?

- A) Use only a single instance type
- B) Use diverse instance families, generations, and sizes
- C) Use only On-Demand
- D) Select only the cheapest instances

<details>
<summary>Show Answer</summary>

**Answer: B) Use diverse instance families, generations, and sizes**

**Explanation:**
Spot instances experience interruptions per capacity pool. Allowing diverse instance types enables acquiring instances from multiple capacity pools, distributing the interruption risk.

```yaml
spec:
  template:
    spec:
      requirements:
        # Diverse instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Diverse generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Diverse sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Diverse architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

</details>

### 2. What is the Karpenter label key that distinguishes between Spot and On-Demand instances?

- A) `node.kubernetes.io/capacity-type`
- B) `karpenter.sh/capacity-type`
- C) `eks.amazonaws.com/instance-type`
- D) `karpenter.k8s.aws/spot-or-ondemand`

<details>
<summary>Show Answer</summary>

**Answer: B) `karpenter.sh/capacity-type`**

**Explanation:**
This label allows specifying Spot/On-Demand instances in Pod nodeAffinity or NodePool requirements.

```yaml
# Setting Spot instance preference in Pod
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot"]
```

</details>

### 3. What is the default warning time given before a Spot instance is interrupted?

- A) 30 seconds
- B) 2 minutes
- C) 5 minutes
- D) 10 minutes

<details>
<summary>Show Answer</summary>

**Answer: B) 2 minutes**

**Explanation:**
AWS Spot instances are given a 2-minute warning before being reclaimed. Workloads must terminate gracefully during this time.

**Spot Interrupt Handling Best Practices:**
- Set Pod's terminationGracePeriodSeconds to 2 minutes or less
- Implement SIGTERM handler in applications
- Prefer stateless workloads
- Implement checkpointing mechanism (for batch jobs)

</details>

### 4. Which workload type is NOT recommended for Spot instances?

- A) Batch processing jobs
- B) Stateless web servers
- C) Single-instance databases
- D) Development/test environments

<details>
<summary>Show Answer</summary>

**Answer: C) Single-instance databases**

**Explanation:**
Single-instance databases can experience availability issues during interrupts, making them unsuitable for Spot.

**Workloads suitable for Spot:**
- Batch processing / Big data analytics
- CI/CD pipelines
- Stateless web servers (Auto Scaling)
- Development/test environments
- Container-based microservices

**Workloads requiring On-Demand:**
- Databases
- Message queues
- Cluster management components
- Long-running stateful jobs

</details>

### 5. How do you configure Spot-first selection when mixing Spot and On-Demand in NodePool?

- A) `spotPriority: high`
- B) NodePool priority setting via weight value
- C) `capacityPriority: spot`
- D) `preferSpot: true`

<details>
<summary>Show Answer</summary>

**Answer: B) NodePool priority setting via weight value**

**Explanation:**
Create multiple NodePools and specify priority with weight values. Higher weight is used first.

```yaml
# Spot-first NodePool (weight: 100)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100  # High priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
---
# On-Demand fallback NodePool (weight: 10)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10  # Low priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. What is the maximum savings rate for Spot instances compared to On-Demand?

- A) 30-40%
- B) 50-60%
- C) 70-90%
- D) 95% or more

<details>
<summary>Show Answer</summary>

**Answer: C) 70-90%**

**Explanation:**
Spot instances can achieve up to 70-90% cost savings compared to On-Demand.

**Cost Optimization Strategy Combinations:**
| Strategy | Expected Savings |
|----------|-----------------|
| Spot instances | 70-90% |
| Graviton (ARM) | ~20% |
| Spot + Graviton | Up to 90% |

However, Spot savings rates vary depending on instance type and availability zone.

</details>
