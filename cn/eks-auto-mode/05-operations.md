# 运维和管理

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: February 19, 2026

本指南介绍 EKS Auto Mode 的运维方面，包括 Disruption Budget（中断预算）、滚动替换、监控、故障排查和安全最佳实践。

---

## Disruption Budget 设置

配置预算以安全地替换 Node（节点）。

```yaml
# disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production-pool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Default: only 10% of total nodes disrupted simultaneously
      - nodes: "10%"

      # Business hours: minimize disruptions
      - nodes: "1"
        schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
        duration: 9h

      # Weekends: allow more aggressive consolidation
      - nodes: "30%"
        schedule: "0 0 * * sat-sun"
        duration: 48h

      # Emergency maintenance window: no disruptions
      - nodes: "0"
        schedule: "0 0 1 * *"  # 1st of each month
        duration: 24h
```

---

## 滚动替换策略

```yaml
# rolling-replacement-strategy.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: rolling-replacement
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Node expiration time
      expireAfter: 168h  # 7 days
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      # Limit concurrent disrupted nodes for sequential replacement
      - nodes: "1"
```

### Node 替换策略对比

| 策略 | 使用场景 | 配置 | 权衡 |
|----------|----------|---------------|------------|
| **Rolling（保守）** | 生产关键 | `nodes: "1"` | 较慢但更安全 |
| **Rolling（适中）** | 标准生产 | `nodes: "10%"` | 平衡方案 |
| **激进** | Dev/Test、批处理 | `nodes: "30%"` | 更快但风险更高 |
| **Scheduled** | 维护窗口 | 基于时间的预算 | 可预测的中断 |

### 何时使用每种策略

- **Rolling（保守）**: Stateful workloads、数据库、关键 APIs
- **Rolling（适中）**: 标准 Web 服务、微服务
- **激进**: CI/CD runners、批处理、开发环境
- **Scheduled**: 合规要求、计划维护

---

## 与 PodDisruptionBudget 集成

```yaml
# pdb-example.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Minimum available Pods
  minAvailable: 3
  # Or maximum unavailable Pods
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:latest
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
      # Graceful shutdown during node replacement
      terminationGracePeriodSeconds: 60
```

### PDB 最佳实践

| Workload 类型 | Replicas | PDB 配置 |
|---------------|----------|-------------------|
| Stateless（3+ replicas） | 3-10 | `minAvailable: N-1` 或 `maxUnavailable: 1` |
| Stateless（10+ replicas） | 10+ | `maxUnavailable: 10%` |
| Stateful | 3+ | `minAvailable: 2`（维持 quorum） |
| Singleton | 1 | 无 PDB（或接受中断） |

---

## Availability Zone（可用区）故障响应

### Multi-AZ Deployment 配置

```yaml
# multi-az-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      # Availability zone distribution
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-app
        # Node distribution
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: ha-app
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
---
# NodePool for guaranteed minimum nodes per zone
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-pool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Guarantee minimum capacity per zone
  limits:
    cpu: 1000
```

### Availability Zone 故障响应模式

| 模式 | 描述 | 实现 |
|---------|-------------|----------------|
| **Active-Active** | 所有 AZ 都提供流量服务 | 使用 `DoNotSchedule` 的 `topologySpreadConstraints` |
| **Active-Standby** | 故障转移到备用 AZ | Pod anti-affinity + health checks |
| **Capacity Reservation** | 预置容量 | On-Demand Capacity Reservations |
| **Overflow** | 突增到其他 AZ | `ScheduleAnyway` 约束 |

---

## CloudWatch 监控

EKS Auto Mode 会自动将指标发送到 CloudWatch。

```bash
# CloudWatch metric namespaces
# - AWS/EKS
# - Karpenter

# Key metrics
# - karpenter_nodes_total: Total node count
# - karpenter_pods_pending: Pending Pod count
# - karpenter_nodeclaims_created: Created NodeClaim count
# - karpenter_nodeclaims_terminated: Terminated NodeClaim count
```

### CloudWatch Dashboard 设置

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Auto Mode Node Count",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Pending Pods",
        "metrics": [
          ["Karpenter", "karpenter_pods_pending", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Time",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_startup_duration_seconds", "cluster", "my-cluster"]
        ],
        "stat": "p99",
        "period": 300
      }
    }
  ]
}
```

---

## 基于 kubectl 的诊断

```bash
# Check NodePool status
kubectl get nodepools
kubectl describe nodepool general-purpose

# Check NodeClaim status (nodes being provisioned)
kubectl get nodeclaims
kubectl describe nodeclaim <name>

# Check node status and labels
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Check Pending Pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep -E "karpenter|nodepool|nodeclaim"

# Node resource usage
kubectl top nodes

# Pod distribution by node
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c | sort -rn
```

---

## 常见问题和解决方案

### 问题 1：Pod 保持 Pending 状态

```bash
# Analyze cause
kubectl describe pod <pending-pod>

# Common causes:
# 1. Resource requests too large
# 2. NodePool limits exceeded
# 3. nodeSelector/affinity condition mismatch
# 4. taint/toleration mismatch

# Solution: Check NodePool limits
kubectl get nodepool -o yaml | grep -A5 limits

# Solution: Check nodeSelector conditions
kubectl get pod <pending-pod> -o yaml | grep -A10 nodeSelector
```

### 问题 2：Node 预置失败

```bash
# Check NodeClaim status
kubectl describe nodeclaim <name>

# Check error messages in events
kubectl get events --field-selector reason=FailedProvisioning

# Common causes:
# 1. Instance capacity shortage
# 2. Subnet IP exhaustion
# 3. IAM permission issues
# 4. Security group configuration errors

# Solution: Allow more diverse instance types
# Expand NodePool requirements
```

### 问题 3：Node Consolidation 不工作

```bash
# Check Consolidation status
kubectl get nodeclaims -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\.sh/nodepool,\
PHASE:.status.phase,\
AGE:.metadata.creationTimestamp

# Check PodDisruptionBudget
kubectl get pdb -A

# Solution: Adjust PDB or check budgets settings
```

### 问题 4：Spot 中断后 Pod 重新调度延迟

```bash
# Check Spot interrupt events
kubectl get events --sort-by='.lastTimestamp' | grep -i "spot\|interrupt"

# Solutions for fast re-provisioning:
# 1. Allow diverse instance types
# 2. Reduce consolidateAfter time
# 3. Use mixed Spot and On-Demand
```

---

## 安全最佳实践

```yaml
# security-best-practices.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  # IMDSv2 required
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1  # Block Pod IMDS access
    httpTokens: required

  # EBS encryption
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        kmsKeyId: arn:aws:kms:ap-northeast-2:123456789:key/xxx

  # Use only private subnets
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"

  # Restrictive security groups
  securityGroupSelectorTerms:
    - tags:
        Type: worker-restricted
---
# Apply Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## Day-2 运维检查清单

### 每日任务

| 任务 | 命令/操作 | 目的 |
|------|----------------|---------|
| 检查 pending pods | `kubectl get pods -A --field-selector=status.phase=Pending` | 识别调度问题 |
| 查看 node 健康状况 | `kubectl get nodes` | 检测 NotReady nodes |
| 检查 node 容量 | `kubectl top nodes` | 监控资源压力 |
| 查看 events | `kubectl get events --sort-by='.lastTimestamp'` | 捕获警告/错误 |

### 每周任务

| 任务 | 命令/操作 | 目的 |
|------|----------------|---------|
| 查看 node age | `kubectl get nodes --sort-by='.metadata.creationTimestamp'` | 跟踪 node 新鲜度 |
| 审计 NodePool limits | `kubectl get nodepools -o yaml` | 确保限制适当 |
| 检查 consolidation | 查看 CloudWatch 指标 | 验证成本优化 |
| 查看 Spot 使用情况 | 检查 capacity type 分布 | 优化成本/可用性 |

### 每月任务

| 任务 | 命令/操作 | 目的 |
|------|----------------|---------|
| 查看 AMI 版本 | 检查 node AMI IDs | 安全补丁 |
| 审计 security groups | 查看 NodeClass 配置 | 安全合规 |
| 成本分析 | AWS Cost Explorer | 预算跟踪 |
| 容量规划 | 查看使用趋势 | 适当扩缩容 |

---

## 运维自动化

### 自动化轮换告警

```yaml
# CloudWatch Alarm for old nodes
# Create alarm when nodes exceed age threshold
```

```bash
# Script to check node ages
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_days=$(( ($(date +%s) - $(date -d "$created" +%s)) / 86400 ))
  if [ $age_days -gt 7 ]; then
    echo "WARNING: Node $name is $age_days days old"
  fi
done
```

### PDB 合规性监控

```bash
# Check PDB status across all namespaces
kubectl get pdb -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
MIN-AVAILABLE:.spec.minAvailable,\
MAX-UNAVAILABLE:.spec.maxUnavailable,\
CURRENT:.status.currentHealthy,\
DESIRED:.status.desiredHealthy,\
DISRUPTIONS-ALLOWED:.status.disruptionsAllowed
```

### 容量 Dashboard 查询

用于容量监控的关键 Prometheus 查询：

```promql
# Total nodes by NodePool
count(kube_node_labels) by (label_karpenter_sh_nodepool)

# Node CPU utilization by pool
avg(1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) by (node) * on(node) group_left(label_karpenter_sh_nodepool) kube_node_labels

# Pending pods over time
sum(kube_pod_status_phase{phase="Pending"})

# Node age distribution
(time() - kube_node_created) / 86400
```

---

## 运维摘要检查清单

| 领域 | 检查项 | 状态 |
|------|----------------|--------|
| **配置** | 已配置 NodePool limits | |
| | 已配置 Disruption Budget | |
| | 已审查 NodeClass 安全设置 | |
| **监控** | 已创建 CloudWatch dashboard | |
| | 已设置告警（Pending Pod、预置失败） | |
| | 已配置成本监控 | |
| **可用性** | 已配置 PodDisruptionBudget | |
| | 已验证 Multi-AZ 分布 | |
| | 已审查 Spot/On-Demand 混合比例 | |
| **成本** | 已优化 Spot instance 比例 | |
| | 已审查 Consolidation policy | |
| | 已审查 Resource requests/limits 适当性 | |

---

< [上一篇：Spot 策略](./04-spot-strategies.md) | [目录](./README.md) | [下一篇：成本管理](./06-cost-management.md) >
