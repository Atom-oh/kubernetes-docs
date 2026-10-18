# 扩缩容策略测验

> **相关文档**：[扩缩容策略](../../ops/06-scaling-strategies.md)

## 选择题

### 1. 使用自定义指标与 HPA 需要什么？

- A) Kubernetes 1.30 或更高版本
- B) Prometheus Adapter 或类似的自定义指标服务器
- C) AWS Auto Scaling 集成
- D) 手动扩缩 Pod

<details>
<summary>显示答案</summary>

**答案：B) Prometheus Adapter 或类似的自定义指标服务器**

**说明：**
使用自定义指标的 HPA 需要一个实现 custom.metrics.k8s.io API 的指标服务器。Prometheus Adapter 会查询 Prometheus，并以 HPA 所需的格式提供指标，从而支持根据每秒请求数等应用专属指标进行扩缩容。

</details>

### 2. KEDA 在原生 HPA 控制循环的基础上增加了什么？

- A) CPU 利用率
- B) 内存使用量
- C) 事件源扩缩器以及激活和缩容至零的管理
- D) Pod 重启次数

<details>
<summary>显示答案</summary>

**答案：C) 事件源扩缩器以及激活和缩容至零的管理**

**说明：**
KEDA（Kubernetes 事件驱动自动扩缩容）包含适用于 AWS SQS、Kafka、RabbitMQ、数据库等外部系统的扩缩器。它向 HPA 提供外部指标，并管理受支持工作负载的激活和缩容至零过程。HPA 本身也可以通过适配器使用外部指标。

</details>

### 3. VPA 的“Recreate”和“Off”模式有什么区别？

- A) Recreate 启用 HPA，Off 禁用 HPA
- B) Recreate 可以驱逐并重新创建 Pod；Off 仅提供建议
- C) Recreate 保证不中断；Off 会立即生效
- D) Recreate 使用 Spot 实例；Off 使用按需实例

<details>
<summary>显示答案</summary>

**答案：B) Recreate 可以驱逐并重新创建 Pod；Off 仅提供建议**

**说明：**
VPA 1.8.0 弃用了 Auto 模式，该模式目前的行为与 Recreate 相同。Recreate 可以通过驱逐和重新创建来更新；Off 则保留建议供审核。显式的 InPlaceOrRecreate 模式和受功能门控控制的 InPlace 模式是独立模式，具有不同的回退行为。

</details>

### 4. 什么是 Pod 删除成本，它如何影响扩缩容？

- A) 删除 Pod 的财务成本
- B) 一种注解，可影响缩容时先移除哪些 Pod
- C) 删除 Pod 所需的时间
- D) 与 Pod 终止相关的存储成本

<details>
<summary>显示答案</summary>

**答案：B) 一种注解，可影响缩容时先移除哪些 Pod**

**说明：**
`controller.kubernetes.io/pod-deletion-cost` 注解为 Pod 指定成本值。在同一 ReplicaSet 内，先比较 Pod 的分配情况、所处阶段和就绪状态，再优先考虑删除成本较低的 Pod。这只是尽力而为的机制，不能保证免受驱逐、Spot 回收、Job/StatefulSet 行为或跨 Deployment 扩缩容的影响。

</details>

### 5. 使用自定义指标的 HPA 在计算期望副本数时采用什么公式？

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>显示答案</summary>

**答案：B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**说明：**
HPA 会将当前指标值与目标值进行比较，然后按比例调整副本数。这个简化公式假定指标可用且 Pod 已就绪。容差、缺失数据、最小值/最大值和扩缩容行为都可能阻止或限制实际变更；向上取整并不保证会增加一个 Pod。

</details>

### 6. 处理 Spot 节点中断的推荐策略是什么？

- A) 忽略中断
- B) 使用 Pod 中断预算，并配合中断处理程序进行优雅终止
- C) 只运行无状态工作负载
- D) 完全禁用 Spot 实例

<details>
<summary>显示答案</summary>

**答案：B) 使用 Pod 中断预算，并配合中断处理程序进行优雅终止**

**说明：**
应根据节点模式选择合适的处理方式：托管的 Auto Mode、已配置的自管理 Karpenter，或在需要时使用完整的 Node Termination Handler 设置。避免重复配置排空控制器。PDB 和宽限期无法阻止 Spot 实例丢失，也不能保证应用获得完整的两分钟关停时间。

</details>

### 7. 在 KEDA 中，`pollingInterval` 配置什么？

- A) Pod 重启的频率
- B) KEDA 检查外部指标源的频率
- C) 扩缩操作之间的延迟
- D) 健康检查的频率

<details>
<summary>显示答案</summary>

**答案：B) KEDA 检查外部指标源的频率**

**说明：**
`pollingInterval` 定义 KEDA 查询外部扩缩器（例如 SQS、Prometheus）以获取指标值的频率。较短的间隔可以加快响应速度，但会增加指标源的负载。

</details>

### 8. 哪项 Kubernetes 功能可以让 VPA 在较新版本中无需重启即可调整 Pod 大小？

- A) 滚动更新
- B) Pod 原地垂直扩缩容
- C) 蓝绿部署
- D) 金丝雀发布

<details>
<summary>显示答案</summary>

**答案：B) Pod 原地垂直扩缩容**

**说明：**
Pod 原地调整资源配置功能从 1.27 版的 Alpha 阶段发展到 1.33 版的 Beta 阶段，并于 1.35 版达到稳定阶段。受支持的 VPA 模式可以使用此功能，但 resizePolicy 仍可能要求重启容器，容量/QoS 限制也可能导致更新延迟或被拒绝。

</details>

### 9. 与 metrics-server 相比，Prometheus Adapter 用于 HPA 有什么优势？

- A) 资源使用量更低
- B) 支持 CPU/内存之外的自定义指标和外部指标
- C) 指标采集速度更快
- D) 内置告警功能

<details>
<summary>显示答案</summary>

**答案：B) 支持 CPU/内存之外的自定义指标和外部指标**

**说明：**
metrics-server 仅提供 CPU 和内存指标。Prometheus Adapter 会通过 custom.metrics.k8s.io API 暴露已配置且可用的时间序列，使 HPA 能够根据每秒请求数、队列深度或延迟等应用指标进行扩缩容。

</details>

### 10. 将 HPA 与 VPA 结合使用时应考虑什么？

- A) 两者不能同时使用
- B) 将它们配置在不同的资源维度上（HPA 管理 CPU，VPA 管理内存）
- C) 启用 VPA 时始终禁用 HPA
- D) 无需配置，两者会自动协调

<details>
<summary>显示答案</summary>

**答案：B) 将它们配置在不同的资源维度上（HPA 管理 CPU，VPA 管理内存）**

**说明：**
如果 HPA 和 VPA 都试图管理同一资源维度，就可能发生冲突。可选方案包括仅提供建议的 VPA，或者让 HPA 使用 RPS/积压量等工作负载指标，同时由 VPA 负责资源配置。Initial 模式仍会更改新 Pod 的资源请求值（requests），因此不能消除 CPU 利用率计算分母方面的相互影响。还应验证重启和调度方面的影响。

</details>
