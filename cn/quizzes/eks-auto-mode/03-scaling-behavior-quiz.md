# EKS Auto Mode 扩展行为测验

> **相关文档**: [Scaling Behavior](../../eks-auto-mode/03-scaling-behavior.md)

## 选择题

### 1. NodePool 的 `consolidationPolicy: WhenEmptyOrUnderutilized` 行为是什么？

- A) 只移除空节点
- B) 同时整合空节点和利用率不足的节点
- C) 始终保留所有节点
- D) 只在特定时间移除节点

<details>
<summary>显示答案</summary>

**答案：B) 同时整合空节点和利用率不足的节点**

**解释：**
`WhenEmptyOrUnderutilized` 策略不仅会整合空节点，还会整合利用率不足的节点以优化成本。这允许将多个利用率不足节点上的工作负载整合到更少的节点上。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m  # Consolidate 1 minute after condition is met
```

**比较：**
- `WhenEmpty`: 只移除空节点（保守）
- `WhenEmptyOrUnderutilized`: 整合空节点 + 利用率不足的节点（激进）

</details>

### 2. 用于检查 NodeClaim 状态的 kubectl 命令是什么？

- A) `kubectl get nodes --show-claims`
- B) `kubectl get nodeclaims`
- C) `kubectl describe karpenter claims`
- D) `kubectl get ec2-nodes`

<details>
<summary>显示答案</summary>

**答案：B) `kubectl get nodeclaims`**

**解释：**
NodeClaim 是表示正在预置的节点状态的资源。

```bash
# List NodeClaims
kubectl get nodeclaims

# Detailed information for specific NodeClaim
kubectl describe nodeclaim <name>

# View NodeClaims with node information
kubectl get nodeclaims -o wide
```

</details>

### 3. 在 Auto Mode 中出现 Pending Pod 时，什么条件下会开始节点预置？

- A) 当 Pod 处于 Pending 状态超过 5 分钟时
- B) 当没有节点满足 NodePool 的要求时
- C) 当节点总数低于阈值时
- D) 当执行手动扩容命令时

<details>
<summary>显示答案</summary>

**答案：B) 当没有节点满足 NodePool 的要求时**

**解释：**
Auto Mode 会分析 Pending Pods 的要求，并在不存在合适节点时立即预置新节点。

**预置流程：**
1. Pod 进入 Pending 状态
2. Karpenter 分析 Pod 的资源请求、nodeSelector、affinity
3. 检查合适 NodePools 的要求
4. 选择最佳实例类型
5. 启动 EC2 实例（40-90 秒）

</details>

### 4. 在哪些情况下不会发生 Consolidation？

- A) 当节点带有 do-not-disrupt annotation 时
- B) 当节点上只有 DaemonSet Pods 时
- C) 当 consolidateAfter 时间尚未经过时
- D) 以上全部

<details>
<summary>显示答案</summary>

**答案：D) 以上全部**

**解释：**
在以下情况下不会发生 Consolidation：

1. **do-not-disrupt annotation**: 带有此 annotation 的节点或 Pods 会被排除在 Consolidation 之外
2. **只有 DaemonSet Pods**: DaemonSets 在所有节点上运行，因此被视为空节点
3. **consolidateAfter 尚未经过**: 必须在条件满足后等待指定时间

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

</details>

### 5. 哪些情况会触发 Drift 检测？

- A) 当 NodeClass spec 发生变化时
- B) 当新的 AMI 可用时
- C) 当 security groups 发生变化时
- D) 以上全部

<details>
<summary>显示答案</summary>

**答案：D) 以上全部**

**解释：**
当节点的当前状态与期望状态不同时，会触发 Drift 检测：

- **NodeClass 变化**: AMI 系列、subnets、security groups 等发生变化
- **新的 AMI**: EKS optimized AMI 已更新
- **Security group 变化**: 引用的 security groups 已修改

检测到 Drift 后，节点会被依次替换。

</details>

### 6. 建议使用哪个 AMI 系列来优化节点预置速度？

- A) AL2023
- B) Bottlerocket
- C) Ubuntu
- D) Amazon Linux 2

<details>
<summary>显示答案</summary>

**答案：B) Bottlerocket**

**解释：**
Bottlerocket 是专为容器设计的 OS，与 AL2023 相比可提供更快的启动时间。

**启动时间比较：**
- **AL2023**: 20-40 秒
- **Bottlerocket**: 15-25 秒

Bottlerocket 的其他优势：
- 更小的攻击面
- 不可变文件系统
- 自动安全更新

</details>
