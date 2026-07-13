# 成本管理和优化

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: July 11, 2026

本指南涵盖 EKS Auto Mode 的成本优化策略，包括成本分析、Spot 节省测量、资源合理配置以及 Savings Plans 集成。

### 2026 年 7 月更新：GPU 管理费用最高降低 60%

自 2026 年 7 月 1 日起，EKS Auto Mode 针对 GPU 和加速实例类型的管理费用已降低：

- **G-series**：管理费用降低 35%
- **P-series and AWS Trainium**：管理费用降低 60%

这些降价会自动应用于所有提供 EKS Auto Mode 的 AWS Region 中的所有 Auto Mode 集群，无需任何操作。Auto Mode 包含为加速工作负载构建的能力，例如在配备本地 NVMe 存储的 GPU 实例上并行拉取和解包镜像（使大型容器和模型镜像启动更快），以及感知加速器的 Node 修复功能，可检测 GPU 硬件故障并自动替换不健康的 Node。请参阅 [Amazon EKS 定价](https://aws.amazon.com/eks/pricing/) 获取更新后的费率表。([公告](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price))

---

## 成本优化最佳实践

```yaml
# cost-optimization-best-practices.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
        # 1. Allow various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]

        # 2. Include Graviton (ARM) instances (20% cheaper)
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]

        # 3. Prioritize Spot instances
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  # 4. Aggressive Consolidation
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Pod settings for cost optimization
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
spec:
  replicas: 5
  template:
    spec:
      # Prefer Spot
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]

      # Appropriate resource requests (prevent overprovisioning)
      containers:
        - name: app
          resources:
            requests:
              cpu: 250m      # Based on actual usage
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## 成本分析仪表板

### CloudWatch 成本指标

设置 CloudWatch dashboard 来跟踪 Auto Mode 成本：

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Node Hours by Capacity Type",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "spot"],
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "on-demand"]
        ],
        "period": 3600,
        "stat": "Average"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Rate",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_created"],
          ["Karpenter", "karpenter_nodeclaims_terminated"]
        ],
        "period": 3600,
        "stat": "Sum"
      }
    }
  ]
}
```

### Kubecost 集成

若要进行详细的成本分摊，请集成 Kubecost：

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="<your-token>"
```

Auto Mode 的关键 Kubecost 指标：

| 指标 | 描述 | 使用场景 |
|--------|-------------|----------|
| Cluster 成本 | 总计算支出 | 预算跟踪 |
| Namespace 成本 | 每个 Namespace 的成本 | 费用分摊 |
| Pod 成本 | 每个工作负载的成本 | 优化目标 |
| 闲置成本 | 未使用的资源 | 合理配置机会 |
| Spot 节省 | Spot 与 On-Demand 的差额 | 验证 Spot 策略 |

---

## 测量 Spot Instance 节省

### 计算实际 Spot 节省

```bash
# Get current node distribution
kubectl get nodes -L karpenter.sh/capacity-type -L node.kubernetes.io/instance-type | \
  awk 'NR>1 {print $6, $7}' | sort | uniq -c
```

### Spot 节省分析脚本

```bash
#!/bin/bash
# spot-savings-analysis.sh

# Get Spot and On-Demand node counts
SPOT_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=spot --no-headers | wc -l)
OD_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=on-demand --no-headers | wc -l)

echo "Current Node Distribution:"
echo "  Spot nodes: $SPOT_NODES"
echo "  On-Demand nodes: $OD_NODES"
echo "  Spot percentage: $(echo "scale=2; $SPOT_NODES * 100 / ($SPOT_NODES + $OD_NODES)" | bc)%"

# Estimate savings (assuming average 70% Spot discount)
echo ""
echo "Estimated Monthly Savings:"
echo "  If all were On-Demand: \$X,XXX"
echo "  With current Spot mix: \$X,XXX"
echo "  Monthly savings: \$X,XXX (XX%)"
```

### AWS Cost Explorer 查询

使用 Cost Explorer 分析 Auto Mode 成本：

1. **按标签筛选**：`eks:cluster-name` = your-cluster
2. **分组依据**：`Instance Type` 或 `Purchase Option`
3. **时间范围**：过去 30 天
4. **比较**：Spot 与 On-Demand 支出

---

## 资源合理配置分析

### VPA 建议

安装 Vertical Pod Autoscaler 以获取合理配置建议：

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-crd-gen.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-rbac.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/recommender-deployment.yaml
```

以建议模式配置 VPA：

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Recommendation only
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

### 分析使用模式

```bash
# Get VPA recommendations
kubectl get vpa my-app-vpa -o jsonpath='{.status.recommendation.containerRecommendations[0]}' | jq

# Compare with current requests
kubectl get deployment my-app -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

### 合理配置决策矩阵

| 当前值与建议值对比 | 操作 | 预期节省 |
|------------------------|--------|------------------|
| Request > 2x usage | 降低 request | 20-50% |
| Request within 2x | 最优 | - |
| Request < usage | 增加 request | 避免 OOM |
| Limit >> request | 降低 limit | 更好的装箱 |

---

## Savings Plans 和 Reserved Instances 策略

### Savings Plans 如何与 Auto Mode 交互

EKS Auto Mode 与 Savings Plans：

| 场景 | Savings Plans 是否适用 | 建议 |
|----------|---------------------|----------------|
| On-Demand nodes | 是 | 购买 Compute Savings Plans |
| Spot nodes | 否（已享受折扣） | 不纳入覆盖范围 |
| Graviton instances | 是（单独费率） | 考虑 ARM Savings Plans |
| 混合工作负载 | 部分 | 计算 On-Demand 基线 |

### Savings Plans 规模估算

```
Recommended Savings Plans Coverage =
    Baseline On-Demand Hours *
    (1 - Expected Spot Percentage) *
    Average Instance Cost

Where:
- Baseline = Minimum sustained usage
- Expected Spot = Target Spot percentage (e.g., 60%)
- Don't over-commit (leave room for Spot)
```

### Savings Plans 最佳实践

| 实践 | 理由 |
|----------|-----------|
| 覆盖 On-Demand 基线的 60-70% | 为 Spot 优化留出空间 |
| 使用 Compute Savings Plans | 跨实例类型的灵活性 |
| 每季度审查 | 随工作负载演进进行调整 |
| 排除 GPU 实例 | 单独的 GPU 专用计划 |

### Reserved Instances 与 Savings Plans

| 因素 | Reserved Instances | Savings Plans |
|--------|-------------------|---------------|
| 灵活性 | 实例特定 | 任意实例 |
| Auto Mode 适配度 | 差（实例会变化） | 好 |
| 承诺期限 | 1 年或 3 年 | 1 年或 3 年 |
| 建议 | 不推荐 | 推荐 |

---

## 成本优化检查清单

### 快速收益

| 操作 | 预估节省 | 工作量 |
|--------|-------------------|--------|
| 启用 Spot instances | Spot nodes 上 60-90% | 低 |
| 添加 ARM/Graviton 支持 | ARM instances 上 20% | 低 |
| 合理配置 requests | 10-30% | 中 |
| 启用 consolidation | 10-20% | 低 |

### 中期优化

| 操作 | 预估节省 | 工作量 |
|--------|-------------------|--------|
| 实施 VPA | 15-30% | 中 |
| 购买 Savings Plans | On-Demand 上 20-40% | 低 |
| Multi-AZ 优化 | 5-10% | 中 |
| 工作负载调度 | 10-20% | 高 |

### 成本监控告警

设置成本异常告警：

```yaml
# CloudWatch Alarm for unexpected node growth
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  NodeCountAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: EKS-Auto-Mode-Node-Count-High
      MetricName: karpenter_nodes_total
      Namespace: Karpenter
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 100  # Adjust based on expected max
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
```

---

## 成本归因

### 用于成本分配的标签策略

```yaml
# NodeClass with cost allocation tags
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: "12345"
    Application: my-app
    ManagedBy: eks-auto-mode
```

### Namespace 级成本跟踪

```yaml
# Namespace with cost labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: "team-a"
    environment: production
```

---

< [上一页：Operations](./05-operations.md) | [目录](./README.md) | [下一页：Node Lifecycle](./07-node-lifecycle.md) >
