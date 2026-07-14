# 可观测性堆栈测验

> **相关文档**: [可观测性堆栈](../../ops/09-observability-stack.md)

## 多项选择题

### 1. LGTM 可观测性堆栈由哪些组件组成？

- A) Linux、Git、Terminal、Make
- B) Loki（日志）、Grafana（可视化）、Tempo（追踪）、Mimir/Prometheus（指标）
- C) Lambda、Gateway、Transit、Monitor
- D) 负载均衡器、Gateway、TLS、Mesh

<details>
<summary>显示答案</summary>

**答案：B) Loki（日志）、Grafana（可视化）、Tempo（追踪）、Mimir/Prometheus（指标）**

**解释：**
LGTM 是 Grafana Labs 的可观测性堆栈，由用于日志聚合的 Loki、用于可视化和仪表板的 Grafana、用于分布式追踪的 Tempo，以及用于指标的 Mimir（或 Prometheus）组成。这些组件可以无缝集成。

</details>

### 2. Loki 的 SimpleScalable 和 Distributed 部署模式有什么区别？

- A) SimpleScalable 仅用于测试
- B) SimpleScalable 分离读/写路径；Distributed 增加了更细粒度的组件分离
- C) Distributed 已被弃用
- D) 它们完全相同

<details>
<summary>显示答案</summary>

**答案：B) SimpleScalable 分离读/写路径；Distributed 增加了更细粒度的组件分离**

**解释：**
SimpleScalable 模式将 Loki 拆分为可独立扩展的读路径和写路径。Distributed 模式进一步分离组件（ingesters、distributors、queriers 等），以便在大规模场景下获得最大的可扩展性和运维灵活性。

</details>

### 3. Tempo 中基于尾部采样的目的是什么？

- A) 对日志文件末尾进行采样
- B) 在看到完整 trace 后再做采样决策
- C) 降低查询延迟
- D) 压缩 trace 数据

<details>
<summary>显示答案</summary>

**答案：B) 在看到完整 trace 后再做采样决策**

**解释：**
基于尾部采样会等到 trace 完成后再决定是否存储它。这样可以保留所有错误 trace 或慢 trace，同时对正常 trace 进行采样；而基于头部采样在 trace 开始时就做出决定，因此无法做到这一点。

</details>

### 4. OTEL Collector 在可观测性堆栈中扮演什么角色？

- A) 长期存储指标
- B) 从应用程序接收、处理并导出 telemetry 数据
- C) 创建 Grafana 仪表板
- D) 管理用户身份认证

<details>
<summary>显示答案</summary>

**答案：B) 从应用程序接收、处理并导出 telemetry 数据**

**解释：**
OpenTelemetry Collector 充当 telemetry pipeline，从应用程序接收 traces、metrics 和 logs，对它们进行处理（批处理、过滤、丰富），并导出到 Tempo、Prometheus 和 Loki 等后端。

</details>

### 5. Amazon Managed Prometheus (AMP) 如何与 Prometheus 集成？

- A) 它完全替代 Prometheus
- B) Prometheus 使用 remote_write 将指标发送到 AMP 进行存储
- C) AMP 作为 Prometheus sidecar 运行
- D) AMP 只与 CloudWatch 配合使用

<details>
<summary>显示答案</summary>

**答案：B) Prometheus 使用 remote_write 将指标发送到 AMP 进行存储**

**解释：**
AMP 为 Prometheus 指标提供托管且可扩展的存储后端。Prometheus 继续在本地抓取并评估规则，但使用 `remote_write` 将指标发送到 AMP。随后 Grafana 使用 PromQL 查询 AMP。

</details>

### 6. 推荐的 Loki label 设计策略是什么？

- A) 为了灵活性，使用尽可能多的 labels
- B) 使用有界的低基数 labels，以避免索引爆炸
- C) 避免使用任何 labels
- D) 只使用 timestamp labels

<details>
<summary>显示答案</summary>

**答案：B) 使用有界的低基数 labels，以避免索引爆炸**

**解释：**
高基数 labels（如用户 ID 或请求 ID）会创建过多 streams 并使索引膨胀。Labels 应保持低基数（namespace、app、environment），而高基数数据应放在日志内容中，以便使用 LogQL 进行过滤。

</details>

### 7. Promtail 和 Grafana Alloy 在日志收集方面有什么区别？

- A) Promtail 只收集指标
- B) Alloy 是支持日志、指标和 traces 的统一 agent；Promtail 专用于 Loki
- C) Promtail 比 Alloy 更新
- D) Alloy 不支持 Kubernetes

<details>
<summary>显示答案</summary>

**答案：B) Alloy 是支持日志、指标和 traces 的统一 agent；Promtail 专用于 Loki**

**解释：**
Promtail 专门用于将日志发送到 Loki。Grafana Alloy（以前称为 Agent）是一个统一 collector，使用 OpenTelemetry 和原生 receivers 处理日志、指标和 traces，从而减少所需 agent 的数量。

</details>

### 8. 如何配置 Grafana 中 Loki 和 Tempo 之间的 datasource 链接？

- A) 它们无需配置即可自动链接
- B) 在 Loki datasource 中配置指向 Tempo datasource 的 derived fields
- C) 安装单独的链接插件
- D) 将数据导出到一个公共数据库

<details>
<summary>显示答案</summary>

**答案：B) 在 Loki datasource 中配置指向 Tempo datasource 的 derived fields**

**解释：**
在 Grafana 的 Loki datasource 设置中，配置 derived fields，并使用正则表达式从日志中提取 trace ID，然后链接到 Tempo datasource。这样会从日志行创建到关联 traces 的可点击链接。

</details>

### 9. Tempo 的 compactor 组件的目的是什么？

- A) 压缩网络流量
- B) 合并 trace blocks 并管理保留策略
- C) 编译 TraceQL 查询
- D) 减少仪表板加载时间

<details>
<summary>显示答案</summary>

**答案：B) 合并 trace blocks 并管理保留策略**

**解释：**
compactor 会将较小的 trace blocks 合并为较大的 blocks 以提高存储效率，并通过删除过期数据来应用保留策略。它在 distributed 模式下作为单独进程运行，或在 monolithic binary 内运行。

</details>

### 10. 配置 OTEL Collector processors 时，batch processor 做什么？

- A) 为 traces 分配 batch IDs
- B) 在导出前将 telemetry 分组为 batches，以提高效率
- C) 处理数据库批量操作
- D) 在 Kubernetes 中创建 batch jobs

<details>
<summary>显示答案</summary>

**答案：B) 在导出前将 telemetry 分组为 batches，以提高效率**

**解释：**
batch processor 会累积 telemetry 数据，并根据大小或超时阈值以 batches 发送。这样可以减少发出的请求数量，提高压缩效果，并降低接收后端的负载。

</details>
