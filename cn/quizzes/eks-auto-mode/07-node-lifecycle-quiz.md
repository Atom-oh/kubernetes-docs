# EKS Auto Mode Node 生命周期测验

> **相关文档**: [Node 生命周期](../../eks-auto-mode/07-node-lifecycle.md)

## 选择题

### 1. 在 NodePool 中用于定期替换 node 的配置字段名称是什么？

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>显示答案</summary>

**答案: C) `expireAfter`**

**解释:**
`expireAfter` 字段允许你设置用于定期替换 node 的最大 node 生命周期，以应用安全补丁或 AMI 更新。

```yaml
spec:
  template:
    spec:
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

**常见设置:**
- 开发环境: 336h（14 天）
- 预发布环境: 168h（7 天）
- 生产环境: 72h ~ 168h（3-7 天）
- 安全关键环境: 24h ~ 48h（1-2 天）

</details>

### 2. 设置了 expireAfter 的 node 过期时会发生什么？

- A) Node 会立即被删除
- B) Node 会被 cordon、drain，然后删除
- C) 仅向管理员发送通知
- D) Node 会自动重启

<details>
<summary>显示答案</summary>

**答案: B) Node 会被 cordon、drain，然后删除**

**解释:**
当 node 过期时，Karpenter 会执行一个优雅处理流程：

1. **Cordon**: 阻止新的 Pod 调度
2. **Drain**: 将现有 Pod 移动到其他 node
3. **Delete**: 终止 EC2 instance

在此过程中会遵循 PodDisruptionBudgets 和 Disruption Budgets。

```yaml
disruption:
  budgets:
    # Expiration-based replacement also follows this budget
    - nodes: "10%"
```

</details>

### 3. 在 AL2023 和 Bottlerocket 之间，哪种 AMI 提供更快的启动时间？

- A) AL2023
- B) Bottlerocket
- C) 它们相同
- D) 取决于 instance type

<details>
<summary>显示答案</summary>

**答案: B) Bottlerocket**

**解释:**
Bottlerocket 是针对容器工作负载优化的 OS，启动时间比 AL2023 更快。

**启动时间比较:**
| AMI | 启动时间 | 特性 |
|-----|-----------|-----------------|
| AL2023 | 20-40 秒 | 通用软件包，灵活性 |
| Bottlerocket | 15-25 秒 | 仅容器，最小化 OS |

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: fast-boot
spec:
  amiFamily: Bottlerocket  # Fast boot
```

Bottlerocket 的其他优势：
- 不可变根文件系统
- 自动安全更新
- 更小的攻击面

</details>

### 4. 当由于 AMI 更新在现有 node 上检测到 Drift 时会发生什么？

- A) Node 会自动原地更新
- B) Node 会按顺序替换为使用新 AMI 的 node
- C) 管理员批准后替换
- D) 什么也不会发生

<details>
<summary>显示答案</summary>

**答案: B) Node 会按顺序替换为使用新 AMI 的 node**

**解释:**
当新的 AMI 可用时，EKS Auto Mode 会检测 Drift 并按顺序替换 node。

**Drift 检测条件:**
- 新的 EKS optimized AMI 发布
- NodeClass 中的 amiFamily 变更
- Security group 变更
- Subnet 设置变更

```yaml
# Drift-based replacement also follows Disruption Budget
disruption:
  budgets:
    - nodes: "10%"  # Only 10% replaced at a time
```

</details>

### 5. 为了保持 node 新鲜度而将 expireAfter 设置得较短时，可能的权衡是什么？

- A) 成本降低
- B) 由于 node 替换频率增加，可能出现临时性能下降
- C) 安全漏洞增加
- D) 集群稳定性提高

<details>
<summary>显示答案</summary>

**答案: B) 由于 node 替换频率增加，可能出现临时性能下降**

**解释:**
较短的 expireAfter 可增强安全性，但有以下权衡：

**优点:**
- 应用最新安全补丁
- 快速应用 AMI 更新
- 防止 node drift

**缺点:**
- node 替换期间容量临时减少
- 更多 Pod 重新调度
- Spot instance 出现额外中断的可能性

**建议:**
```yaml
# Balanced setting
spec:
  template:
    spec:
      expireAfter: 168h  # 7 days
  disruption:
    budgets:
      - nodes: "10%"  # Limit concurrent replacement
```

</details>

### 6. 当 Consolidation 和 Expiration 同时触发时，哪个优先？

- A) Consolidation 总是优先
- B) Expiration 总是优先
- C) 哪个先达到 node 替换条件，哪个就执行
- D) 管理员必须选择

<details>
<summary>显示答案</summary>

**答案: C) 哪个先达到 node 替换条件，哪个就执行**

**解释:**
Karpenter 会独立评估多个 disruption 原因，并在条件满足时执行。

**Disruption 优先级（典型评估顺序）:**
1. **Drift**: 检测到配置变更或 AMI 更新
2. **Expiration**: 超过 expireAfter 时间
3. **Consolidation**: 利用率不足或空 node

```yaml
# Example: 5-day-old underutilized node
# - expireAfter: 7 days -> Not expired yet
# - Consolidation condition met -> Replaced by Consolidation

# Example: 8-day-old normal utilization node
# - expireAfter: 7 days -> Expired
# - Replaced by Expiration
```

</details>

### 7. 当需要立即替换 node 以应用安全补丁时，使用什么方法？

- A) 将 expireAfter 设置为 0
- B) 向 node 添加 Drift annotation
- C) 更新 NodeClass 以触发 Drift，或 drain node
- D) 重启 cluster

<details>
<summary>显示答案</summary>

**答案: C) 更新 NodeClass 以触发 Drift，或 drain node**

**解释:**
紧急应用安全补丁的方法：

**方法 1: NodeClass 更新（推荐）**
```yaml
# Trigger drift by changing tags or settings
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: default
spec:
  tags:
    SecurityPatch: "2025-02-19"  # Drift triggered by tag change
```

**方法 2: 手动 drain**
```bash
# Drain specific node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node (Auto Mode provisions new node)
kubectl delete node <node-name>
```

**方法 3: 滚动替换**
```bash
# Sequentially replace all nodes
kubectl delete nodes -l karpenter.sh/nodepool=general-purpose
```

</details>

### 8. 将 expireAfter 设置为 Never 会产生什么行为？

- A) Node 立即过期
- B) 禁用基于时间的自动替换
- C) 设置无效并应用默认值
- D) 发生错误

<details>
<summary>显示答案</summary>

**答案: B) 禁用基于时间的自动替换**

**解释:**
设置 `expireAfter: Never` 会禁用基于时间的 node 过期。

```yaml
spec:
  template:
    spec:
      expireAfter: Never  # Disable time-based expiration
```

**注意事项:**
- Drift 和 Consolidation 仍然有效
- 安全补丁应用可能会延迟
- 仅建议用于长时间运行的工作负载

**推荐使用场景:**
- Stateful 工作负载（数据库）
- 非常长时间运行的 job
- 具有手动维护计划的环境

</details>
