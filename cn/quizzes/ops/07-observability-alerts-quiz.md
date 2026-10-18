# 可观测性告警测验

> **相关文档**: [可观测性告警](../../ops/07-observability-alerts.md)

## 选择题

### 1. 哪个 PromQL 表达式可以检测容器中的 CPU throttling？

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>显示答案</summary>

**答案：B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**解释：**
可用的 CFS 配额耗尽时可能发生 CPU throttling；解读时应结合工作负载的配额和性能情况。`container_cpu_cfs_throttled_seconds_total` 指标记录受到 throttling 的时间。其速率大于零表示当前存在 throttling，可能影响应用性能。

</details>

### 2. Alertmanager 的 `group_by` 配置有什么作用？

- A) 删除告警
- B) 将具有匹配标签的告警聚合为一条通知
- C) 提高告警严重级别
- D) 将告警路由到日志

<details>
<summary>显示答案</summary>

**答案：B) 将具有匹配标签的告警聚合为一条通知**

**解释：**
`group_by` 会把共享指定标签值的多个 firing 告警合并到一条通知中。当一次事件触发许多相似告警时（例如某个 Deployment 中的所有 Pod 都发生故障），这样可以减少告警疲劳。

</details>

### 3. 哪个指标有助于观察 Kubernetes Node 是否就绪？

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` with condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>显示答案</summary>

**答案：B) `kube_node_status_condition` with condition="Ready"**

**解释：**
Ready condition 报告当前观测到的 Node 是否就绪。状态为 False 或 Unknown 可能由多种原因导致，不能据此断定 Node 已终止或正在替换。应结合资源清单、Node 和 NodeClaim 的 condition，以及实际事件或审计日志进行核实。

</details>

### 4. Prometheus 告警规则中的 `for` 时长指定什么？

- A) 告警在历史记录中保留多久
- B) 条件必须持续为真的时长，超过后告警才会触发
- C) 告警评估间隔
- D) 通知超时时间

<details>
<summary>显示答案</summary>

**答案：B) 条件必须持续为真的时长，超过后告警才会触发**

**解释：**
`for` 子句指定某个条件必须连续为真多久，告警才会从 pending 转为 firing。这样可以避免短暂尖峰触发告警，并减少误报。

</details>

### 5. 应如何定义告警严重级别？

- A) 所有告警都应设为 critical
- B) 根据业务影响和所需响应时间确定
- C) 随机分配
- D) 根据指标名称确定

<details>
<summary>显示答案</summary>

**答案：B) 根据业务影响和所需响应时间确定**

**解释：**
严重级别应反映影响：面向客户的故障且需要立即响应时标为 critical；需要在数小时内处理的服务降级可标为 warning；无需采取行动、仅供了解的信息可标为 info。这样才能按严重程度进行恰当的路由和 on-call 升级。

</details>

### 6. 哪个 PromQL 函数用于计算数值随时间增加的速率？

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>显示答案</summary>

**答案：B) `rate()`**

**解释：**
`rate()` 计算给定时间范围内每秒的平均增量速率。它适用于 counter，并能处理 counter 重置。例如，`rate(http_requests_total[5m])` 表示 5 分钟窗口内每秒请求数的平均值。

</details>

### 7. 对网络丢包告警，推荐采用什么做法？

- A) 每发生一次丢包就告警
- B) 丢包率持续一段时间超过阈值时告警
- C) 永远不针对丢包告警
- D) 只记录丢包

<details>
<summary>显示答案</summary>

**答案：B) 丢包率持续一段时间超过阈值时告警**

**解释：**
网络中偶尔丢包是正常现象。只有持续偏高的丢包率表明可能存在实际问题时，才应触发告警。可在一段时间窗口（例如 5m）上使用 `rate()` 并设置阈值，避免短暂尖峰触发告警。

</details>

### 8. 在 Alertmanager 路由中，`continue: true` 有什么作用？

- A) 停止处理后续路由
- B) 允许告警在匹配当前路由后继续匹配后续的同级路由
- C) 重复发送告警通知
- D) 静默告警

<details>
<summary>显示答案</summary>

**答案：B) 允许告警在匹配当前路由后继续匹配后续的同级路由**

**解释：**
continue: true 会允许告警继续匹配后续的同级路由。如果某个子路由已经匹配，根接收器不会自动充当备用接收器。应测试完整的路由树，包括没有匹配团队路由的 critical 告警。

</details>

### 9. 哪个表达式有助于衡量网络发送吞吐量？

- A) `container_cpu_usage_seconds_total`
- B) `rate(node_network_transmit_bytes_total[5m])`，并将单位与实际容量约定保持一致
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>显示答案</summary>

**答案：B) `rate(node_network_transmit_bytes_total[5m])`，并将单位与实际容量约定保持一致**

**解释：**
`node_network_transmit_bytes_total` 和 `node_network_receive_bytes_total` 用于跟踪网络 I/O。速率的单位是字节/秒；乘以 8 可换算为比特/秒，然后与经过验证的基准值、突发能力和网络路径限制比较。仅凭累计计数器、宣传的虚拟网卡速率，或假定存在通用的 10 Gbps 限值，都不能证明网络已饱和。

</details>

### 10. Alertmanager 中的告警抑制规则有什么作用？

- A) 提高告警优先级
- B) 父级告警触发时，抑制符合条件的相关告警
- C) 将告警路由到不同接收器
- D) 创建新告警

<details>
<summary>显示答案</summary>

**答案：B) 父级告警触发时，抑制符合条件的相关告警**

**解释：**
告警抑制会根据配置的来源/目标匹配器和相等标签抑制相应通知，但它本身不能确定根因。应要求 cluster 和实体标识符存在且非空，避免缺失标签导致互不相关的告警被抑制；Prometheus 仍会继续评估规则。

</details>
