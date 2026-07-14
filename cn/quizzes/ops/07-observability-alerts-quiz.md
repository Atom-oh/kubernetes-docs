# 可观测性告警测验

> **相关文档**: [可观测性告警](../../ops/07-observability-alerts.md)

## 选择题

### 1. 哪个 PromQL 表达式用于检测 container 中的 CPU throttling？

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>显示答案</summary>

**答案：B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**解释：**
当 container 超过其 CPU limit 时，会发生 CPU throttling。`container_cpu_cfs_throttled_seconds_total` metric 会跟踪被 throttled 的时间。正的 rate 表示存在 active throttling，可能会影响应用程序性能。

</details>

### 2. Alertmanager 的 `group_by` 配置有什么用途？

- A) 删除告警
- B) 将具有匹配 label 的告警聚合为单个通知
- C) 提高告警 severity
- D) 将告警路由到日志

<details>
<summary>显示答案</summary>

**答案：B) 将具有匹配 label 的告警聚合为单个通知**

**解释：**
`group_by` 会将共享指定 label 值的多个 firing alerts 合并为一个通知。这可以减少由许多相似告警触发的 incident 中的告警疲劳（例如，一个 Deployment 中的所有 pods 都失败）。

</details>

### 3. 哪个 metric 对检测 EKS Auto Mode node 终止最重要？

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` with condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>显示答案</summary>

**答案：B) `kube_node_status_condition` with condition="Ready"**

**解释：**
监控 `kube_node_status_condition` 中的 Ready=false 可以检测 nodes 变为不可用。在 Auto Mode 中，这表示 node 终止或替换。结合 labels，你可以跟踪 node lifecycle 和替换模式。

</details>

### 4. Prometheus 告警规则中的 `for` duration 指定了什么？

- A) 告警在历史记录中保留多久
- B) 条件在 firing 前必须保持为 true 的时长
- C) 告警评估 interval
- D) 通知 timeout

<details>
<summary>显示答案</summary>

**答案：B) 条件在 firing 前必须保持为 true 的时长**

**解释：**
`for` 子句指定条件必须持续为 true 多久，告警才会从 “pending” 转换为 “firing”。这可以防止短暂尖峰触发告警，并减少误报。

</details>

### 5. 应如何定义告警 severity levels？

- A) 所有告警都应为 critical
- B) 基于业务影响和所需响应时间
- C) 随机分配
- D) 基于 metric 名称

<details>
<summary>显示答案</summary>

**答案：B) 基于业务影响和所需响应时间**

**解释：**
Severity 应反映影响：critical 用于需要立即响应的面向客户的故障，warning 用于需要在数小时内关注的降级，info 用于无需行动的认知提醒。这可以实现适当的路由和 on-call 升级。

</details>

### 6. 哪个 PromQL function 用于计算随时间增长的 rate？

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>显示答案</summary>

**答案：B) `rate()`**

**解释：**
`rate()` 计算某个时间范围内每秒平均增长率。它专为 counters 设计，并会处理 counter resets。例如，`rate(http_requests_total[5m])` 给出 5 分钟内平均的每秒请求数。

</details>

### 7. packet drop 告警的推荐做法是什么？

- A) 对任何单个 packet drop 发出告警
- B) 当 drop rate 超过阈值并持续一段时间时发出告警
- C) 永远不要对 packet drops 发出告警
- D) 只记录 packet drops

<details>
<summary>显示答案</summary>

**答案：B) 当 drop rate 超过阈值并持续一段时间时发出告警**

**解释：**
偶发的 packet drops 在网络中是正常的。告警应在持续升高的 drop rates 表明存在实际问题时触发。使用一个窗口（例如 5m）上的 `rate()` 并设置阈值，可以防止瞬时尖峰触发告警。

</details>

### 8. 在 Alertmanager routing 中，`continue: true` 有什么作用？

- A) 停止处理后续 routes
- B) 允许告警在当前 route 之后继续匹配其他 routes
- C) 重复告警通知
- D) 静默告警

<details>
<summary>显示答案</summary>

**答案：B) 允许告警在当前 route 之后继续匹配其他 routes**

**解释：**
默认情况下，Alertmanager 会在第一个匹配的 route 处停止。设置 `continue: true` 允许告警匹配多个 routes，从而支持同时将 critical 告警发送到 PagerDuty 和 Slack 等场景。

</details>

### 9. 哪个 metric 表示 EKS nodes 上的网络带宽超限？

- A) `container_cpu_usage_seconds_total`
- B) `node_network_transmit_bytes_total` approaching instance network limits
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>显示答案</summary>

**答案：B) `node_network_transmit_bytes_total` approaching instance network limits**

**解释：**
`node_network_transmit_bytes_total` 和 `node_network_receive_bytes_total` 跟踪 network I/O。将 rate 与 EC2 instance network bandwidth limits 进行比较，有助于识别 workloads 何时触及网络约束。

</details>

### 10. Alertmanager 中 alert inhibition rules 的用途是什么？

- A) 提高告警优先级
- B) 当父级告警正在 firing 时，抑制依赖告警
- C) 将告警路由到不同 receivers
- D) 创建新告警

<details>
<summary>显示答案</summary>

**答案：B) 当父级告警正在 firing 时，抑制依赖告警**

**解释：**
Inhibition rules 会在根因告警触发时静默下游告警，以防止告警风暴。例如，当 “NodeDown” 触发时，抑制该 node 上 pods 的所有 “PodNotReady” 告警，因为它们是同一问题的症状。

</details>
