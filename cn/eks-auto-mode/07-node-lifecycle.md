# Node 生命周期管理

> **支持的版本**: EKS 1.29+, EKS Auto Mode GA
> **最后更新**: July 3, 2026

本指南介绍 EKS Auto Mode 中的 Node 生命周期管理，包括过期策略、AMI 管理、漂移检测和 Node 新鲜度监控。

---

## Node 过期策略 (expireAfter)

`expireAfter` 字段控制 Node 在被自动替换之前可以运行多长时间。

### expireAfter 工作原理

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

### 过期流程

1. Node 达到 `expireAfter` 时长
2. Controller 将 Node 标记为需要替换
3. 使用最新配置预置新的 Node
4. 在遵守 PDB 的前提下迁移工作负载
5. 旧 Node 被 drain 并终止

### Auto Mode 的 21 天最大 Node 生命周期

EKS Auto Mode 使用基于 Karpenter 的 `expireAfter` 默认值，并且 Node 在创建后达到 **21 天 (504h)** 的最大年龄时会自动被替换。你可以将 `expireAfter` 设置为短于 21 天，以便更频繁地替换，但将其设置为长于 21 天不会产生效果 — Auto Mode 会强制将 21 天作为硬性上限。与 managed node groups 或 self-managed Karpenter 不同，Node 不能无限期保留。

如果你运行会长时间保持状态的工作负载（缓存预热时间较长的服务、依赖本地存储的有状态工作负载等），请提前围绕这个 21 天上限规划 Pod 重新调度和数据再平衡流程。

### 推荐的 expireAfter 值

| 使用场景 | expireAfter | 理由 |
|----------|-------------|-----------|
| **安全关键** | 24h - 72h | 频繁修补，满足合规要求 |
| **标准生产** | 168h (7 days) | 在新鲜度和稳定性之间取得平衡 |
| **成本敏感** | 336h (14 days) | 最小化替换开销（在 21 天上限内） |
| **开发/测试** | 504h (21 days, maximum) | 最大化 Node 复用；这是强制执行的上限 |
| **合规 (PCI/HIPAA)** | 72h - 168h | 满足审计要求 |

### expireAfter 配置示例

```yaml
# Security-first configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-critical
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days for security compliance
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
---
# Cost-optimized configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days for cost efficiency
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

---

## AMI 管理策略

### Auto Mode 如何选择 AMI

EKS Auto Mode 会根据你的 NodeClass 配置自动选择并管理 AMI。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ami-managed
spec:
  # AMI family selection
  amiFamily: AL2023  # or Bottlerocket
```

### AMI Family 对比

| 功能 | AL2023 | Bottlerocket |
|---------|--------|--------------|
| 基础 OS | Amazon Linux 2023 | 专为容器构建的 OS |
| 启动时间 | ~40-60 seconds | ~20-40 seconds |
| 攻击面 | 标准 | 最小（只读 root） |
| 自定义 | 完整 (userData) | 有限 (settings API) |
| Package manager | dnf | 无（不可变） |
| 安全更新 | 标准修补 | 原子更新 |
| 使用场景 | 通用工作负载 | 安全重点工作负载 |

### AMI Family 选择指南

| 工作负载类型 | 推荐 AMI | 理由 |
|---------------|-----------------|-----------|
| 通用 Web services | AL2023 | 灵活性，熟悉的工具 |
| 安全关键 | Bottlerocket | 最小攻击面 |
| 合规 (PCI/SOC2) | Bottlerocket | 不可变基础设施 |
| GPU 工作负载 | AL2023 | NVIDIA driver 支持 |
| 自定义 kernel modules | AL2023 | 完整 OS 访问 |
| 快速扩缩容 | Bottlerocket | 更快的启动时间 |

### 自定义 AMI 配置

```yaml
# For specific AMI requirements
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-ami
spec:
  amiFamily: AL2023

  # AMI selection by tags (if using custom AMIs)
  amiSelectorTerms:
    - tags:
        Name: my-custom-eks-ami
        Environment: production
```

---

## AMI 更新和漂移检测

### AMI 更新如何触发漂移

当 AWS 发布新的 AMI 或你更新 NodeClass 时：

1. **AMI 发布**：AWS 发布新的 EKS-optimized AMI
2. **漂移检测**：Controller 检测到 AMI 版本不匹配
3. **Node 标记**：现有 Node 被标记为“已漂移”
4. **替换**：根据 disruption 设置替换 Node

### 漂移检测触发条件

| 变更 | 触发漂移 | 替换速度 |
|--------|----------------|-------------------|
| 新 AMI version | 是 | 基于 disruption budget |
| NodeClass AMI family 变更 | 是 | 立即调度 |
| Security patch AMI | 是 | 基于 disruption budget |
| NodePool requirement 变更 | 是 | 基于 consolidation |
| NodeClass block device 变更 | 是 | 仅新 Node |

### 监控漂移状态

```bash
# Check for drifted nodes
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
AGE:.metadata.creationTimestamp,\
DRIFT:.metadata.annotations.karpenter\\.sh/drift-hash

# Check NodeClaim drift status
kubectl get nodeclaims -o wide

# Watch for drift events
kubectl get events --sort-by='.lastTimestamp' | grep -i drift
```

### 控制漂移替换

```yaml
# Slow drift replacement for stability
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
spec:
  template:
    spec:
      expireAfter: 168h
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      # Slow, controlled replacement
      - nodes: "1"
      # No replacement during business hours
      - nodes: "0"
        schedule: "0 9-17 * * mon-fri"
        duration: 8h
```

---

## Node 新鲜度策略和安全补丁

### Node 新鲜度为何重要

| 关注点 | 影响 | 缓解措施 |
|---------|--------|------------|
| **安全补丁** | 未修补的漏洞 | 较短的 expireAfter |
| **AMI 更新** | 缺少功能/修复 | 启用漂移替换 |
| **配置漂移** | 行为不一致 | 定期 Node rotation |
| **合规** | 审计发现 | 有文档记录的 rotation policy |

### 安全补丁策略

```yaml
# Security-focused NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-patched
spec:
  template:
    spec:
      # Maximum node age for security compliance
      expireAfter: 72h  # 3 days
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Allow faster replacement for security patches
      - nodes: "20%"
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  metadataOptions:
    httpTokens: required  # IMDSv2 only
    httpPutResponseHopLimit: 1

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        encrypted: true
        volumeType: gp3
```

---

## Consolidation 与过期的权衡

### 各机制何时适用

| 机制 | 触发条件 | 目的 | 优先级 |
|-----------|---------|---------|----------|
| **Consolidation** | 利用率不足 | 成本优化 | 较低 |
| **过期** | 年龄阈值 | 安全/新鲜度 | 较高 |
| **漂移** | 配置变更 | 一致性 | 最高 |

### 机制间的交互

```
Node Lifecycle Priority:
1. Drift (immediate) - Configuration mismatch
2. Expiration (scheduled) - Age threshold reached
3. Consolidation (opportunistic) - Underutilization detected
```

### 不同优先级的配置

```yaml
# Cost-priority (consolidation aggressive, expiration relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days - relaxed
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m  # Aggressive consolidation
---
# Security-priority (expiration aggressive, consolidation relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days - aggressive
  disruption:
    consolidationPolicy: WhenEmpty  # Relaxed consolidation
    consolidateAfter: 10m
```

---

## 监控 Node Age 分布

### 基于 kubectl 的监控

```bash
# List nodes with age
kubectl get nodes --sort-by='.metadata.creationTimestamp' \
  -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
CREATED:.metadata.creationTimestamp,\
AGE:.metadata.creationTimestamp

# Calculate node ages in days
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_seconds=$(($(date +%s) - $(date -d "$created" +%s)))
  age_days=$((age_seconds / 86400))
  age_hours=$(((age_seconds % 86400) / 3600))
  echo "$name: ${age_days}d ${age_hours}h"
done
```

### Prometheus/Grafana 监控

用于 Node age 的关键 Prometheus 查询：

```promql
# Node age in days
(time() - kube_node_created) / 86400

# Nodes older than 7 days
count(((time() - kube_node_created) / 86400) > 7)

# Average node age by NodePool
avg((time() - kube_node_created) / 86400) by (label_karpenter_sh_nodepool)

# Node age distribution histogram
histogram_quantile(0.50,
  sum(rate(kube_node_created_bucket[24h])) by (le)
)
```

### 告警规则

```yaml
# Prometheus alerting rules for node age
groups:
  - name: node-lifecycle
    rules:
      - alert: NodeTooOld
        expr: (time() - kube_node_created) / 86400 > 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Node {{ $labels.node }} is older than 10 days"

      - alert: NodeAgeDistributionSkewed
        expr: stddev((time() - kube_node_created) / 86400) > 3
        for: 4h
        labels:
          severity: info
        annotations:
          summary: "Node ages are highly variable, check rotation"
```

### Node Age Dashboard

创建包含以下内容的 Grafana dashboard：

| 面板 | 查询 | 可视化 |
|-------|-------|---------------|
| 按 age bucket 的 Node 数量 | Node age 直方图 | 条形图 |
| 按 NodePool 的平均 age | `avg by (nodepool)` | Stat panel |
| 最旧的 Node | 按 age 排序的 Top N | 表格 |
| 即将过期的 Node | 接近 expireAfter 的 age | 告警列表 |
| 替换率 | NodeClaims 创建/终止 | 时间序列 |

---

## Node 生命周期最佳实践

| 实践 | 建议 |
|----------|----------------|
| 设置 expireAfter | 始终配置，默认 7 天 |
| 出于安全目的使用 Bottlerocket | 最小攻击面 |
| 监控 Node age | 对超过预期 age 的 Node 发出告警 |
| 尊重 PDBs | 确保工作负载平滑迁移 |
| 错开替换 | 使用 disruption budgets |
| 跟踪 AMI versions | 监控安全补丁 |

---

< [上一页：成本管理](./06-cost-management.md) | [目录](./README.md) | [下一页：工作负载优化](./08-workload-optimization.md) >
