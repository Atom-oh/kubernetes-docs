# EKS Auto Mode 成本管理测验

> **相关文档**: [成本管理](../../eks-auto-mode/06-cost-management.md)

## 单项选择题

### 1. 将 Graviton (ARM) 实例纳入成本优化时，大约可以实现多少比例的成本节省？

- A) 5%
- B) 10%
- C) 20%
- D) 50%

<details>
<summary>显示答案</summary>

**答案：C) 20%**

**解释：**
基于 AWS Graviton 处理器的实例 (arm64) 比同类 x86 实例便宜约 20%，同时提供出色的性能。

```yaml
spec:
  template:
    spec:
      requirements:
        # Include Graviton (ARM) instances
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

**成本优化策略：**
- 使用 Graviton (ARM) 实例：约节省 20%
- 使用 Spot 实例：最高可节省 70-90%
- 激进整合：整合利用率不足的节点
- 合理的资源请求：防止过度预置

</details>

### 2. 在 NodePool 的 `limits` 设置中将 CPU limit 设置为 500 意味着什么？

- A) 每个节点的最大 CPU 为 500 核
- B) NodePool 最多可预置总计 500 vCPU
- C) 每个 Pod 最大为 500m CPU
- D) 集群范围的 CPU 限制

<details>
<summary>显示答案</summary>

**答案：B) NodePool 最多可预置总计 500 vCPU**

**解释：**
NodePool 的 `limits` 会限制 NodePool 可以预置的资源总量。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  limits:
    cpu: 500      # Maximum 500 vCPU
    memory: 1Ti   # Maximum 1TB memory
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
```

这有助于防止成本超支并管理预算。

</details>

### 3. 哪种 Consolidation 策略会自动清理利用率不足的节点以优化成本？

- A) `consolidationPolicy: WhenEmpty`
- B) `consolidationPolicy: WhenEmptyOrUnderutilized`
- C) `consolidationPolicy: Always`
- D) `consolidationPolicy: Aggressive`

<details>
<summary>显示答案</summary>

**答案：B) `consolidationPolicy: WhenEmptyOrUnderutilized`**

**解释：**
`WhenEmptyOrUnderutilized` 策略会将空节点和利用率不足的节点都作为整合目标。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

**策略比较：**
- `WhenEmpty`：仅移除空节点（保守，稳定性优先）
- `WhenEmptyOrUnderutilized`：激进的成本优化

成本节省效果：整合利用率不足的节点，以减少节点总数和基础设施成本

</details>

### 4. 使用 Savings Plans 搭配 EKS Auto Mode 时，推荐的方法是什么？

- A) 使用 Compute Savings Plans 以获得实例系列灵活性
- B) 针对特定实例类型使用 EC2 Instance Savings Plans
- C) 仅使用 Reserved Instances
- D) 不使用 Savings Plans

<details>
<summary>显示答案</summary>

**答案：A) 使用 Compute Savings Plans 以获得实例系列灵活性**

**解释：**
Auto Mode 会根据工作负载使用多种实例类型，因此 Compute Savings Plans 最为适合。

**Savings Plans 比较：**
| 类型 | 灵活性 | 折扣 |
|------|-------------|----------|
| Compute Savings Plans | 实例系列、大小、区域、OS 灵活 | 最高 66% |
| EC2 Instance Savings Plans | 固定特定实例系列 | 最高 72% |

```
Recommended Strategy:
1. Analyze baseline workload volume (3-month baseline)
2. Cover 70% of minimum usage with Compute Savings Plans
3. Run remainder flexibly with Spot/On-Demand
```

</details>

### 5. 使用 Kubecost 进行成本分析时，Pod 级成本分配需要什么？

- A) 无需配置即可自动支持
- B) 向 Pods 添加 cost-center 标签
- C) 安装 Kubecost agent 并进行集群集成
- D) AWS Cost Explorer 就足够了

<details>
<summary>显示答案</summary>

**答案：C) 安装 Kubecost agent 并进行集群集成**

**解释：**
Kubecost 是一种 Kubernetes 原生成本监控工具，可提供详细的成本分析。

```bash
# Kubecost installation (Helm)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace
```

Kubecost 功能：
- 按 namespace/workload 进行成本分析
- 资源效率建议
- 预算告警设置
- AWS 集成以提高实际成本准确性

</details>

### 6. 设置 resource requests 时，防止过度预置的最佳实践是什么？

- A) 始终将 limits 和 requests 设置为相同
- B) 参考基于实际使用量的 VPA 建议
- C) 将 requests 设置得尽可能高
- D) 省略 requests 设置

<details>
<summary>显示答案</summary>

**答案：B) 参考基于实际使用量的 VPA 建议**

**解释：**
使用 Vertical Pod Autoscaler (VPA) 分析实际资源使用情况，并设置合适的 request 值。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Only provide recommendations, no auto-apply
```

查看建议：
```bash
kubectl describe vpa my-app-vpa
```

这可以实现：
- 防止过度预置（节省成本）
- 防止预置不足（性能保障）

</details>

### 7. 对于多层工作负载，具有成本效益的 NodePool 分离策略是什么？

- A) 将所有工作负载放在单个 NodePool 中
- B) 按层分离 NodePool（frontend/API/batch/ML）
- C) 按实例大小分离 NodePool
- D) 按可用区分离 NodePool

<details>
<summary>显示答案</summary>

**答案：B) 按层分离 NodePool（frontend/API/batch/ML）**

**解释：**
根据工作负载特征分离 NodePools，可以实现最佳的成本/性能平衡。

| 层 | 策略 | 预期节省 |
|------|----------|-----------------|
| Frontend | On-Demand + Graviton | ~20% |
| API | Spot mixed + Graviton | ~40% |
| Batch | 仅 Spot + 多样化 | ~70% |
| ML | 选择合适的实例大小 | ~30% |

```yaml
# Batch tier example - Maximum cost savings
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
```

</details>

### 8. 要在 AWS Cost Explorer 中按标签对 EKS Auto Mode 成本进行分类，需要什么？

- A) 所有标签都会自动应用
- B) 需要在 NodeClass 中设置 tags 字段
- C) 在 AWS Organizations 中配置
- D) 无法进行基于标签的分类

<details>
<summary>显示答案</summary>

**答案：B) 需要在 NodeClass 中设置 tags 字段**

**解释：**
通过 NodeClass 中的 tags 字段，将成本分配标签应用到预置的节点。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: production-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: engineering-001
    Project: kubernetes-platform
```

AWS Cost Explorer 设置：
1. 在 Billing Console 中启用 Cost Allocation Tags
2. 选择所需的标签键
3. 24 小时后可在 Cost Explorer 中使用

</details>
