# EKS Auto Mode 节点生命周期测验

> **相关文档**：[节点生命周期](../../eks-auto-mode/07-node-lifecycle.md)
> **最后更新**：2026 年 9 月 12 日

## 选择题

### 1. NodePool 中哪个字段指定新创建的 NodeClaim 按存续时长过期？

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>显示答案</summary>

**答案：C) `expireAfter`**

**说明：**
该字段位于 `spec.template.spec` 下。Auto Mode 文档规定默认值为 336h；如果池中未设置终止宽限期，则会为 NodeClaim 应用 24h 的终止宽限期。托管实例的最长存续时间为 21 天，这并不保证实例至少运行这么久。更新模板不会覆盖现有 NodeClaim。此前列出的开发环境 336h、预发布环境 168h、生产环境 72–168h 和安全场景 24–48h 都是未经验证的策略示例，并非必须遵守的合规间隔。
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 2. Auto Mode 的 NodeClaim 过期时，哪项说法正确？

- A) 它总是立即消失
- B) 开始终止和排空，但不保证替代节点已提前就绪
- C) 只发送通知
- D) 重新启动同一实例

<details>
<summary>显示答案</summary>

**答案：B) 开始终止和排空，但不保证替代节点已提前就绪**

**说明：**
过期属于强制触发路径，不受 NodePool 中断预算的速率限制。控制器会阻止普通的新调度，并尝试排空和清理。PDB 和 Pod 注解可能影响驱逐，但终止宽限期和 AWS 的最长存续时间限制了这种保护的持续范围。因此，`nodes: 10%` 预算不会将过期处理变成受控的 10% 滚动更新。替代容量和应用就绪状态需要各自的证据。

</details>

### 3. 关于 EKS Auto Mode 的操作系统选择，哪项说法正确？

- A) 使用 `amiFamily` 选择 AL2023
- B) AWS 管理 Bottlerocket 的不同变体；NodeClass 不是 AMI 系列选择器
- C) 使用 `amiSelectorTerms` 选择自定义 AMI
- D) GPU 节点必须使用客户管理的 AL2023

<details>
<summary>显示答案</summary>

**答案：B) AWS 管理 Bottlerocket 的不同变体；NodeClass 不是 AMI 系列选择器**

**说明：**
Auto Mode 不开放这些自定义 AMI 接口，也不提供 SSH/SSM 访问。其托管镜像也支持加速工作负载。此前测验中的 AL2023 20–40s 与 Bottlerocket 15–25s，以及源文中的 40–60s 与 20–30s/20–40s，都缺乏经核实的测量依据，不能据此确定普遍适用的启动速度排名。通用操作系统比较与 Auto Mode 的托管接口是不同的问题。

</details>

### 4. Auto Mode 托管镜像更新使现有 NodeClaim 发生漂移时，可能出现什么情况？

- A) 所有实例立即原地打补丁
- B) 符合条件的 NodeClaim 可在适用的优雅中断控制下被替换
- C) 在任意节点标签更改之前不会发生任何操作
- D) 必须同时删除所有节点

<details>
<summary>显示答案</summary>

**答案：B) 符合条件的 NodeClaim 可在适用的优雅中断控制下被替换**

**说明：**
检查 `Drifted` 状态条件、原因和当前策略。10% 预算会向上取整，并与其他生效的限制共同作用，并不意味着一次只替换一个节点。调度/PDB 约束和宽限期的具体含义也很重要。并非每项 NodePool 变更都会引发漂移：兼容的需求范围扩大，或权重、限额、中断等行为设置的变更，与期望状态漂移有所不同。`amiFamily` 不是 Auto Mode 的字段。

</details>

### 5. 缩短过期时间的策略可能带来什么权衡？

- A) 保证降低成本
- B) 增加重新调度、预热/恢复工作，并可能影响可用性
- C) 保证出现更多 CVE
- D) 保证稳定性

<details>
<summary>显示答案</summary>

**答案：B) 增加重新调度、预热/恢复工作，并可能影响可用性**

**说明：**
频繁替换可能让托管镜像的滚动发布更频繁，但不能证明所需补丁已经可用，也不能修复每个工作负载漏洞。这可能增加容量、镜像拉取、检查点和恢复成本。它本身不会提高 EC2 Spot 实例的中断概率。应分别评估应用恢复和节点宽限期；NodePool 预算无法限制过期处理的速率。
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 6. 整合与过期的条件重叠时，应如何理解这两种机制？

- A) 整合总是优先
- B) 过期总是先等待漂移处理，再等待整合
- C) 优雅中断方式和强制过期采用不同的控制路径，不存在通用的全局先后顺序
- D) 管理员必须手动选择每个操作

<details>
<summary>显示答案</summary>

**答案：C) 优雅中断方式和强制过期采用不同的控制路径，不存在通用的全局先后顺序**

**说明：**
优雅中断控制器先评估漂移，再评估整合；过期则走独立的强制处理路径。文档并未保证全局 `drift > expiration > consolidation` 顺序，也未保证哪个条件先满足就先执行。存续五天的节点可能在七天的过期时间之前被整合。已存续八天且已过期的 NodeClaim，即使利用率良好，也可能开始终止。

</details>

### 7. 紧急修复节点补丁问题时，合理的起点是什么？

- A) 将所有池的 `expireAfter` 设为零
- B) 虚构一个漂移注解
- C) 确认托管修复已可用，识别受影响的 NodeClaim，并采用带健康检查的单资源处理流程
- D) 批量删除一个池，并称其为顺序替换

<details>
<summary>显示答案</summary>

**答案：C) 确认托管修复已可用，识别受影响的 NodeClaim，并采用带健康检查的单资源处理流程**

**说明：**
确认托管镜像/修复已可用，然后在已审查的操作上下文中检查单个 NodeClaim 的 UID、节点映射、PDB、持久化状态，以及备用或可获取的容量。适合时使用托管漂移机制；手动替换应另行审查，并在处理下一个节点前重新检查健康状态和镜像证据。仅用于标记的 `SecurityPatch` 标签并不能保证触发补丁处理，删除所有带标签的节点也不是滚动更新。`--delete-emptydir-data` 可能丢弃本地数据。

相关指南会设置 `KUBE_CONTEXT`；以下命令仅收集证据。

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```


</details>

### 8. 上游的 `expireAfter: Never` 能让 Auto Mode 节点无限期保留吗？

- A) 能，包括所有维护和中断情形
- B) 不能；Auto Mode 托管实例最长 21 天的限制仍然适用
- C) 能，只要 Pod 有 PDB
- D) 能，对所有有状态工作负载都适用

<details>
<summary>显示答案</summary>

**答案：B) 不能；Auto Mode 托管实例最长 21 天的限制仍然适用**

**说明：**
上游语法并不意味着可以覆盖 Auto Mode 服务的存续时间限制。不要建议通过 `Never` 让 Auto Mode 数据库或长时间运行的作业永久运行在同一实例上，也不要在未经测试的情况下断言某种准入响应一定会出现。应规划检查点、外部持久化存储和恢复。漂移、中断以及其他生命周期操作可能更早发生。

</details>

## 参考资料

- [Auto Mode NodePool 默认值](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode 最长存续时间](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [中断和漂移](https://karpenter.sh/v1.14/concepts/disruption/)
