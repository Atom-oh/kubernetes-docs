# 扩缩容策略测验

> **相关文档**: [扩缩容策略](../../ops/06-scaling-strategies.md)

## 选择题

### 1. 使用 HPA 的自定义指标需要什么？

- A) Kubernetes 1.30 或更高版本
- B) Prometheus Adapter 或类似的自定义指标服务器
- C) AWS Auto Scaling 集成
- D) 手动 Pod 扩缩容

<details>
<summary>显示答案</summary>

**答案: B) Prometheus Adapter 或类似的自定义指标服务器**

**解释:**
使用自定义指标的 HPA 需要一个实现 custom.metrics.k8s.io API 的指标服务器。Prometheus Adapter 会查询 Prometheus，并以 HPA 期望的格式公开指标，从而能够基于每秒请求数等应用特定指标进行扩缩容。

</details>

### 2. KEDA 可以基于哪些 HPA 无法基于的事件进行扩缩容？

- A) CPU 利用率
- B) 内存使用量
- C) SQS 队列深度或 Kafka 滞后等外部事件
- D) Pod 重启次数

<details>
<summary>显示答案</summary>

**答案: C) SQS 队列深度或 Kafka 滞后等外部事件**

**解释:**
KEDA (Kubernetes Event-Driven Autoscaling) 包含适用于 AWS SQS、Kafka、RabbitMQ、数据库等外部系统的缩放器。它可以扩缩容到零，并响应 Kubernetes 指标系统之外的事件。

</details>

### 3. VPA 模式 “Auto” 和 “Off” 之间有什么区别？

- A) Auto 启用 HPA，Off 禁用 HPA
- B) Auto 就地更新 Pod，Off 仅提供建议
- C) Auto 需要重启，Off 会立即生效
- D) Auto 使用 Spot 实例，Off 使用 On-Demand 实例

<details>
<summary>显示答案</summary>

**答案: B) Auto 就地更新 Pod，Off 仅提供建议**

**解释:**
VPA “Auto” 模式会自动驱逐并重新创建带有更新后资源请求的 Pod。“Off” 模式只生成建议而不进行更改，适用于在手动实施前审查建议。

</details>

### 4. 什么是 Pod Deletion Cost，它如何影响扩缩容？

- A) 删除一个 Pod 的财务成本
- B) 一个注解，用于影响缩容期间哪些 Pod 会先被移除
- C) 删除一个 Pod 所需的时间
- D) 与 Pod 终止相关的存储成本

<details>
<summary>显示答案</summary>

**答案: B) 一个注解，用于影响缩容期间哪些 Pod 会先被移除**

**解释:**
`controller.kubernetes.io/pod-deletion-cost` 注解会为 Pod 分配一个成本值。在缩容期间，删除成本较低的 Pod 会先被终止。这有助于保留运行重要工作负载或包含缓存数据的 Pod。

</details>

### 5. 使用带自定义指标的 HPA 时，计算期望副本数的公式是什么？

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>显示答案</summary>

**答案: B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**解释:**
HPA 通过将当前指标值与目标值进行比较来计算期望副本数，然后按比例扩缩容。向上取整函数确保在扩容时至少增加一个额外副本。

</details>

### 6. 针对 Spot 节点中断处理，推荐的策略是什么？

- A) 忽略中断
- B) 使用 Pod Disruption Budgets，并结合中断处理程序进行优雅终止
- C) 只运行无状态工作负载
- D) 完全禁用 Spot 实例

<details>
<summary>显示答案</summary>

**答案: B) 使用 Pod Disruption Budgets，并结合中断处理程序进行优雅终止**

**解释:**
Spot 中断处理结合了 AWS Node Termination Handler（或 Karpenter 的原生处理）、用于确保可用性的 Pod Disruption Budgets、足够的终止宽限期，以及能够优雅处理抢占的工作负载设计。

</details>

### 7. 在 KEDA 中，`pollingInterval` 配置什么？

- A) Pod 重启的频率
- B) KEDA 检查外部指标源的频率
- C) 扩缩容操作之间的延迟
- D) 健康检查频率

<details>
<summary>显示答案</summary>

**答案: B) KEDA 检查外部指标源的频率**

**解释:**
`pollingInterval` 定义 KEDA 向外部缩放器（例如 SQS、Prometheus）查询指标值的频率。较低的间隔可以提供更快的响应时间，但会增加指标源的负载。

</details>

### 8. 哪个 Kubernetes 功能使 VPA 能够在较新版本中无需重启即可调整 Pod 大小？

- A) Rolling updates
- B) In-place Pod Vertical Scaling
- C) Blue/green deployment
- D) Canary releases

<details>
<summary>显示答案</summary>

**答案: B) In-place Pod Vertical Scaling**

**解释:**
Kubernetes 1.27+ 通过 `resizePolicy` 字段支持就地垂直扩缩容，允许在不重启 Pod 的情况下更改 CPU 和内存。VPA 可以利用此能力实现干扰更少的资源调整。

</details>

### 9. 与 metrics-server 相比，使用 Prometheus Adapter 支持 HPA 有什么好处？

- A) 更低的资源使用量
- B) 支持 CPU/内存之外的自定义和外部指标
- C) 更快的指标收集
- D) 内置告警

<details>
<summary>显示答案</summary>

**答案: B) 支持 CPU/内存之外的自定义和外部指标**

**解释:**
Metrics-server 只提供 CPU 和内存指标。Prometheus Adapter 通过 custom.metrics.k8s.io API 公开任何 Prometheus 指标，使 HPA 能够基于每秒请求数、队列深度或延迟等应用指标进行扩缩容。

</details>

### 10. 组合使用 HPA 和 VPA 时应该考虑什么？

- A) 它们不能一起使用
- B) 将它们配置在不同的资源维度上（HPA 基于 CPU，VPA 基于内存）
- C) 启用 VPA 时始终禁用 HPA
- D) 它们会自动协调，无需配置

<details>
<summary>显示答案</summary>

**答案: B) 将它们配置在不同的资源维度上（HPA 基于 CPU，VPA 基于内存）**

**解释:**
如果 HPA 和 VPA 都尝试管理同一资源维度，就可能发生冲突。一种常见模式是使用 HPA 基于 CPU 进行水平扩缩容，并将 VPA 用于内存的建议模式；或者使用 VPA “Initial” 模式，该模式仅在 Pod 创建时设置资源。

</details>
