# EKS Hybrid Nodes 工作负载放置测验

> **相关文档**：[工作负载放置](../../eks-hybrid-nodes/06-workload-placement.md)
> **最后更新**：2026 年 9 月 13 日

### 1. 哪项不是 Pod 放置或调度资格的直接机制？

A. `nodeSelector`

B. Node affinity

C. Taints 和 tolerations

D. PodDisruptionBudget

<details>
<summary>显示答案</summary>

**答案：D. PodDisruptionBudget**

**解释**：PDB 会约束受支持的自愿驱逐请求；它既不选择节点，也不保证所有删除路径下的可用性。节点选择、affinity 和 taints 分别承担不同的调度职责。

</details>

### 2. `dedicated=gpu:NoSchedule` 能确保什么？

A. 只有申请 GPU 的容器才能在该节点运行

B. 新 Pod 需要适用的 toleration；仅有 toleration 不能证明会使用 GPU，也不会强制 Pod 放到该节点

C. 现有 Pod 会立即被驱逐

D. 节点会自动声明 GPU 资源

<details>
<summary>显示答案</summary>

**答案：B. 新 Pod 需要适用的 toleration；仅有 toleration 不能证明会使用 GPU，也不会强制 Pod 放到该节点**

**解释**：仅使用 CPU 的 Pod 也可以容忍该 taint。GPU 资源请求和准入策略是另外的配置。`NoSchedule` 影响新调度；`NoExecute` 的驱逐语义不同。

</details>

### 3. 对允许突发扩容的工作负载，preferred node affinity 提供什么？

A. 将正在运行的云端 Pod 自动迁回本地

B. 固定的本地与云端副本比例

C. 在符合资格的节点中提供调度偏好，同时受其他约束和可用容量影响

D. 第八个 Pod 之后就能获得无限 AWS 容量

<details>
<summary>显示答案</summary>

**答案：C. 在符合资格的节点中提供调度偏好，同时受其他约束和可用容量影响**

**解释**：preferred affinity 不是容量耗尽检测器、严格顺序规则或迁移控制器。节点数不等于 Pod 容量。Karpenter 和副本自动扩缩器是不同的控制循环；配额、可用实例、IP 和工作负载依赖都可能阻止扩容。

</details>

### 4. 使用 `DoNotSchedule` 时，如何解读 topology `maxSkew`？

A. 集群 Pod 总数上限

B. 相对于所有符合条件域中的全局最小值计算；配置时也要考虑 `minDomains`

C. 使用 `ScheduleAnyway` 时保证均匀分布

D. AWS 账户数量

<details>
<summary>显示答案</summary>

**答案：B. 相对于所有符合条件域中的全局最小值计算；配置时也要考虑 `minDomains`**

**解释**：符合条件的域取决于 Pod 的约束和拓扑策略。`ScheduleAnyway` 使用软评分，因此可能超过 `maxSkew`。缺少可用域或硬性规则也可能使 Pod 保持 Pending。

</details>

### 5. 对本地持久化数据，哪种做法合适？

A. 使用节点标签并假设数据已经存在

B. 使用受管理的本地 PV/PVC 拓扑和绑定，并另行规划云端放置所需的数据访问或复制

C. 通过 `hostPath` 挂载 `/mnt/data`，并将其视为可移植存储

D. 不检查卷就把 Pod 移到任意云节点

<details>
<summary>显示答案</summary>

**答案：B. 使用受管理的本地 PV/PVC 拓扑和绑定，并另行规划云端放置所需的数据访问或复制**

**解释**：标签不会创建或复制数据。本地 PV 的节点亲和性和 `WaitForFirstConsumer` 会协调放置；已绑定的本地卷不会自动变成 EC2 回退节点可访问的卷。

</details>

### 6. required hostname anti-affinity 有助于实现什么？

A. 完整的应用可用性保证

B. 容量足够时，将匹配的副本分散到符合条件的不同 Kubernetes 节点

C. 保证副本位于不同的物理电源故障域

D. 无需其他 controller 就能自动修复副本

<details>
<summary>显示答案</summary>

**答案：B. 容量足够时，将匹配的副本分散到符合条件的不同 Kubernetes 节点**

**解释**：这可以减少一种相关故障来源。剩余副本仍需要通过就绪检查、依赖项检查并具备足够的服务容量；不同 Kubernetes 节点也可能共享同一物理主机或故障域。

</details>

### 7. 本地 Pod 的 deletion-cost 为 1000，是否可能比 cost 为 0 的云端 Pod 更早被删除？

A. 不可能；1000 能防止驱逐

B. 不可能；ReplicaSet 首先比较 cost

C. 可能；在审查的 controller 中，调度分配状态、阶段和就绪状态先于删除 cost

D. 只有未设置 cost annotation 时才可能

<details>
<summary>显示答案</summary>

**答案：C. 可能；在审查的 controller 中，调度分配状态、阶段和就绪状态先于删除 cost**

**解释**：未分配、Pending/Unknown 和 NotReady 等条件可能优先决定删除对象。deletion cost 只是同一 ReplicaSet 的 Pod 之间尽力采用的偏好，无法防止所有 controller 操作、发布、驱逐或故障。

</details>

### 8. 为什么旧的、仅处理 CREATE 的位置变更 webhook 并不完整？

A. Pod 创建阶段不支持 admission webhook

B. 云节点没有标签

C. 普通 CREATE 请求通常尚未绑定节点，因此还无法获知最终节点位置

D. 只有在调度前才能修改 deletion cost

<details>
<summary>显示答案</summary>

**答案：C. 普通 CREATE 请求通常尚未绑定节点，因此还无法获知最终节点位置**

**解释**：绑定之后的处理流程可以检查 `spec.nodeName`。生产环境中的 webhook 还需要有效的后端、Service、TLS 和范围明确的策略；配置不完整且 fail-closed 的 webhook 可能阻止 Pod 创建。

</details>

### 9. Karpenter 1.14.1 是否读取 `pod-deletion-cost`？

A. 不会；只有 ReplicaSet 能读取

B. 会，将其作为包含其他输入的归一化驱逐成本启发式的一部分；它不是禁止中断的规则

C. 会；1000 能带来 1000 倍保护

D. 会；它能取代 PDB 和所有中断预算

<details>
<summary>显示答案</summary>

**答案：B. 会，将其作为包含其他输入的归一化驱逐成本启发式的一部分；它不是禁止中断的规则**

**解释**：标记版本的 Karpenter 源码会将此 annotation 纳入 Pod 驱逐成本。候选对象评估、节点状态、优先级和生命周期约束仍然重要；成本 annotation 不保证空节点会立即被移除。

</details>

### 10. 为什么逐个 Pod 打补丁的 annotation 方案比旧的集群级 CronJob 更安全？

A. 忽略所有 API 错误

B. 根据标签缺失推断云端放置

C. 检查预期的 ReplicaSet 所有者、节点分类、Pod UID 和 resourceVersion，然后审查范围有限的补丁

D. 第一次冲突后删除并发更新测试

<details>
<summary>显示答案</summary>

**答案：C. 检查预期的 ReplicaSet 所有者、节点分类、Pod UID 和 resourceVersion，然后审查范围有限的补丁**

**解释**：示例会拒绝未知或尚未调度的状态，并生成可审查的补丁。UID/resourceVersion/节点条件可拒绝过期状态，同时保留无关 annotation。它不会扫描或修改每个命名空间。

</details>
