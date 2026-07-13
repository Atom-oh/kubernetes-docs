# Spot Instance 使用策略

> **支持版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: February 19, 2026

本指南介绍在 EKS Auto Mode 中有效使用 Spot instances（竞价实例）的策略，包括混合容量配置、多样化和中断处理。

---

## 混合 Spot 和 On-Demand 策略

混合策略可以同时实现稳定性和成本效率。

```yaml
# spot-ondemand-mixed.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        # Allow both Spot and On-Demand
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Configure Spot preference in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      # Prefer Spot instances
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]
      # For critical workloads, require On-Demand
      # requiredDuringSchedulingIgnoredDuringExecution:
      #   nodeSelectorTerms:
      #     - matchExpressions:
      #         - key: karpenter.sh/capacity-type
      #           operator: In
      #           values: ["on-demand"]
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
```

### 容量类型选择指南

| 工作负载类型 | 推荐容量 | 理由 |
|---------------|---------------------|-----------|
| 无状态 Web services | 优先使用 Spot | 可以处理中断 |
| Batch processing | 仅 Spot | 节省成本，可重试 |
| Databases | 仅 On-Demand | 数据完整性 |
| CI/CD runners | 优先使用 Spot | 节省成本，可重试 |
| Machine learning inference | 混合 | 平衡成本和可用性 |
| Machine learning training | 混合并使用 checkpointing | 长时间运行，可设置 checkpoint |

---

## Spot Instance 多样化

使用多种 instance types 来分散中断风险。

```yaml
# diversified-spot.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
        # Various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Various generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Various sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Various architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        # Use only Spot
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Fast re-provisioning on Spot interrupt
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 多样化最佳实践

| 策略 | 好处 | 配置 |
|----------|---------|---------------|
| 多个 instance families | 减少相关性中断 | `["m", "c", "r", "i", "d"]` |
| 多个 generations | 访问更大的容量池 | `["5", "6", "7"]` |
| 多个 sizes | 提高预置灵活性 | `["large", "xlarge", "2xlarge"]` |
| 多个 architectures | 2 倍容量池 | `["amd64", "arm64"]` |

---

## Spot 中断处理

### Disruption Budget 配置

```yaml
# spot-disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # Limit concurrent node disruptions
    budgets:
      - nodes: "10%"    # Only 10% of total nodes simultaneously
      - nodes: "3"      # Or maximum 3 nodes
      # Minimize disruptions during business hours
      - nodes: "0"
        schedule: "0 9-18 * * mon-fri"  # Weekdays 9-18
        duration: 9h
```

### 面向 Spot 感知的 Pod 配置

```yaml
# Configure Spot interrupt handling in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      # Allow time for graceful shutdown
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 90"]
      # Spread across multiple AZs
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spot-aware
```

### 中断处理检查清单

| 项目 | 描述 | 实现方式 |
|------|-------------|----------------|
| 优雅关闭 | 正确处理 SIGTERM | `terminationGracePeriodSeconds` |
| PreStop hook | 延迟终止 | `lifecycle.preStop` |
| Multi-AZ 分布 | 在 AZ 范围中断中保持存活 | `topologySpreadConstraints` |
| 多个 replicas | 无单点故障 | `replicas > 1` |
| 状态外部化 | 不要在本地存储状态 | 使用外部 databases/caches |

---

## 成本节省示例

```
+-----------------------------------------------------------------------------+
|                       Spot Instance Cost Savings Examples                    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Workload Type          On-Demand Cost   Spot Cost      Savings             |
|  ---------------------------------------------------------------------------  |
|  Batch Processing        $1,000/month    $300/month     70%                 |
|  Dev/Test Environment    $2,000/month    $500/month     75%                 |
|  CI/CD Pipeline          $500/month      $150/month     70%                 |
|  Non-critical API Server $3,000/month    $1,200/month   60%                 |
|                                                                              |
|  * Spot instance prices vary based on supply and demand                      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### 计算 Spot 节省

要估算你潜在的 Spot 节省：

1. **识别适合 Spot 的工作负载**：无状态、容错、灵活
2. **检查 Spot 定价历史**：使用 AWS Spot Instance Advisor
3. **计算 On-Demand 基线成本**：当前或预计支出
4. **应用平均 Spot 折扣**：通常比 On-Demand 低 60-90%
5. **考虑中断开销**：用于重新预置的额外计算资源

### Spot 节省公式

```
Estimated Monthly Savings =
    (On-Demand Hours * On-Demand Price) -
    (Spot Hours * Spot Price) -
    (Interrupt Overhead * On-Demand Price)

Where:
- Interrupt Overhead = Estimated interrupts * Recovery time * Instance count
```

---

## Spot 最佳实践总结

| 实践 | 描述 |
|----------|-------------|
| 多样化 instance types | 使用 10+ 种 instance types 以降低中断风险 |
| 使用多个 AZs | 跨 3+ 个 AZs 分布以提高可用性 |
| 设置合适的 grace periods | 为优雅关闭预留 120+ 秒 |
| 实现 health checks | 快速检测并替换不健康的 pods |
| 使用 topology spread | 防止所有 replicas 位于同一个 Spot pool |
| 外部化状态 | 不要在 Spot nodes 上存储关键数据 |
| 设置 disruption budgets | 限制并发中断 |
| 监控 Spot metrics | 跟踪中断和节省 |

---

< [上一页：Scaling Behavior](./03-scaling-behavior.md) | [目录](./README.md) | [下一页：Operations](./05-operations.md) >
