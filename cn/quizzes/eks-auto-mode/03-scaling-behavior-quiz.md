# EKS Auto Mode 扩展行为测验

> **相关文档**：[扩展行为](../../eks-auto-mode/03-scaling-behavior.md)

## 选择题

### 1. `consolidationPolicy: WhenEmptyOrUnderutilized` 允许什么操作？

- A) 仅移除空节点
- B) 对符合条件的空节点或非空节点进行节省成本的整合
- C) 永久保留所有节点
- D) 只在固定的时钟时间移除节点

<details>
<summary>显示答案</summary>

**答案：B) 对符合条件的空节点或非空节点进行节省成本的整合**

只要相关约束下的工作负载仍可调度，就可以移除节点或用成本较低的节点替换。资源请求、PDB、预算和注解都会影响结果；它不是简单依据实测 CPU 利用率的阈值。

```yaml
# Fragment inside a NodePool; eligibility delay, not a deletion deadline
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m
```

添加或移除 Pod 时，计时器会重置。一分钟是资格判定/稳定等待时间，不保证删除或替换会在一分钟内完成。当前 AWS API 也支持 `Balanced`，它会在节省成本的同时考虑中断代价。

</details>

### 2. 哪个命令可以列出 NodeClaim？

- A) kubectl get nodes --show-claims
- B) kubectl get nodeclaims
- C) kubectl describe karpenter claims
- D) kubectl get ec2-nodes

<details>
<summary>显示答案</summary>

**答案：B) kubectl get nodeclaims**

NodeClaim 描述期望的节点配置以及 Provider 的生命周期/状态，而不只是节点创建的瞬间。检查其 conditions 和关联节点名称；`Drifted` 是一种 condition，并非早已废弃的虚构 `karpenter.sh/drift-hash` 节点注解。

```bash
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodeclaims -o wide
: "${NODECLAIM_NAME:?Select a NodeClaim from the list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe nodeclaim "$NODECLAIM_NAME"
```

</details>

### 3. 什么情况下无法调度的 Pod 会促使 Auto Mode 配置新容量？

- A) 每个 Pod 都已 Pending 五分钟
- B) Pod 无法放入现有容量，且有符合条件的兼容池/容量可以满足其约束
- C) 节点数低于固定的全局阈值
- D) 只有操作员手动运行扩容命令后才会发生

<details>
<summary>显示答案</summary>

**答案：B) Pod 无法放入现有容量，且有符合条件的兼容池/容量可以满足其约束**

调度器无法放置 Pod、NodePool/NodeClass 约束匹配、配额和实际容量都会影响结果。已调度但在等待镜像或 init container 的 Pod 也可能处于 Pending，却不需要新节点。Auto Mode 不保证立即分配容量；此前未经验证的 40–90 秒估算也不能作为保证。

</details>

### 4. 哪些情况可能阻止候选节点整合？

- A) 适用的 do-not-disrupt 注解
- B) PDB 阻止了所需的工作负载驱逐
- C) consolidateAfter 稳定等待时间尚未结束
- D) 以上全部

<details>
<summary>显示答案</summary>

**答案：D) 以上全部**

这些情况都可能阻止或延迟整合。此前的错误答案把仅有 DaemonSet Pod 的节点也列为阻碍；这类节点仍可能符合空节点条件。

```yaml
# Metadata fragment on the intended Node or Pod, not NodePool metadata
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

此注解并不保证能阻止所有中断原因。还必须分别考虑到期、抢占和终止宽限时间限制。临时保护应在相应维护需求结束后移除。

</details>

### 5. 哪些变化可能导致节点 drift 或被替换？

- A) 相关的期望 NodeClass 配置不再与节点匹配
- B) AWS 选择了新的托管 Auto Mode AMI
- C) 解析出的子网/安全组选择发生变化
- D) 以上情况都可能导致此结果

<details>
<summary>显示答案</summary>

**答案：D) 以上情况都可能导致此结果**

应检查实际的 NodeClaim conditions 和 Provider 的决策。并非每项编辑都会导致 drift：放宽要求可能仍与现有实例兼容，而 weight/limits/disruption 设置属于行为配置。修改同一安全组中的规则，不等于解析出不同的安全组。平滑替换仍受调度和预算约束，也可能并行进行；它不一定是每次严格顺序替换一个节点。

</details>

### 6. 如何改善 Auto Mode 的启动延迟？

- A) 将 amiFamily 切换为 AL2023
- B) 测量工作负载路径，并测试受支持的容量、镜像和存储改动
- C) 假设卷越小就一定越快
- D) 将 40–90 秒视为端到端 SLO 保证

<details>
<summary>显示答案</summary>

**答案：B) 测量工作负载路径，并测试受支持的容量、镜像和存储改动**

AWS 会选择托管的 Bottlerocket 镜像。Auto Mode 不提供旧版 `amiFamily` 对比选项。应分别测量节点注册、镜像/初始化时间和应用就绪时间，并将失败与超时纳入测量。

此前测验中的 **AL2023 20–40 秒**和 **Bottlerocket 15–25 秒**仅作为未经验证的历史教学估算保留。它们不是 Auto Mode 的实测结果，也不能证明当前启动时间优势或受支持的 AMI 选择。

</details>
