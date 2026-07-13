# EKS Auto Mode Spot 策略测验

> **相关文档**: [Spot Instance Strategies](../../eks-auto-mode/04-spot-strategies.md)

## 选择题

### 1. 分散 Spot instance 中断风险的最佳策略是什么？

- A) 仅使用单一 instance type
- B) 使用多样化的 instance family、generation 和 size
- C) 仅使用 On-Demand
- D) 只选择最便宜的 instance

<details>
<summary>显示答案</summary>

**答案：B) 使用多样化的 instance family、generation 和 size**

**说明：**
Spot instance 会按 capacity pool 发生中断。允许多样化的 instance type 可以从多个 capacity pool 获取 instance，从而分散中断风险。

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

### 2. 用于区分 Spot 和 On-Demand instance 的 Karpenter label key 是什么？

- A) `node.kubernetes.io/capacity-type`
- B) `karpenter.sh/capacity-type`
- C) `eks.amazonaws.com/instance-type`
- D) `karpenter.k8s.aws/spot-or-ondemand`

<details>
<summary>显示答案</summary>

**答案：B) `karpenter.sh/capacity-type`**

**说明：**
此 label 允许在 Pod nodeAffinity 或 NodePool requirements 中指定 Spot/On-Demand instance。

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

### 3. Spot instance 被中断前默认会提前多久发出警告？

- A) 30 秒
- B) 2 分钟
- C) 5 分钟
- D) 10 分钟

<details>
<summary>显示答案</summary>

**答案：B) 2 分钟**

**说明：**
AWS Spot instance 在被回收前会收到 2 分钟警告。Workload 必须在此期间优雅终止。

**Spot 中断处理最佳实践：**
- 将 Pod 的 terminationGracePeriodSeconds 设置为 2 分钟或更短
- 在应用程序中实现 SIGTERM handler
- 优先使用 stateless workload
- 实现 checkpointing 机制（用于 batch job）

</details>

### 4. 哪种 workload 类型不推荐用于 Spot instance？

- A) Batch processing job
- B) Stateless web server
- C) Single-instance database
- D) Development/test environment

<details>
<summary>显示答案</summary>

**答案：C) Single-instance database**

**说明：**
Single-instance database 在中断期间可能出现可用性问题，因此不适合使用 Spot。

**适合 Spot 的 workload：**
- Batch processing / Big data analytics
- CI/CD pipeline
- Stateless web server (Auto Scaling)
- Development/test environment
- Container-based microservice

**需要 On-Demand 的 workload：**
- Database
- Message queue
- Cluster management component
- Long-running stateful job

</details>

### 5. 在 NodePool 中混合 Spot 和 On-Demand 时，如何配置优先选择 Spot？

- A) `spotPriority: high`
- B) 通过 weight 值设置 NodePool priority
- C) `capacityPriority: spot`
- D) `preferSpot: true`

<details>
<summary>显示答案</summary>

**答案：B) 通过 weight 值设置 NodePool priority**

**说明：**
创建多个 NodePool，并使用 weight 值指定 priority。weight 更高的会优先使用。

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

### 6. 与 On-Demand 相比，Spot instance 的最高节省率是多少？

- A) 30-40%
- B) 50-60%
- C) 70-90%
- D) 95% 或更高

<details>
<summary>显示答案</summary>

**答案：C) 70-90%**

**说明：**
与 On-Demand 相比，Spot instance 最多可实现 70-90% 的成本节省。

**成本优化策略组合：**
| Strategy | Expected Savings |
|----------|-----------------|
| Spot instances | 70-90% |
| Graviton (ARM) | ~20% |
| Spot + Graviton | Up to 90% |

不过，Spot 节省率会因 instance type 和 availability zone 而异。

</details>
