# OpenTelemetry 测验

> **最后更新**: September 13, 2026

测试您对 OpenTelemetry 的理解。

---

1. 本指南重点关注哪三种核心信号？
   - A) Logs、Metrics、Events
   - B) Traces、Metrics、Logs
   - C) Spans、Counters、Logs
   - D) Traces、Alerts、Logs

<details>
<summary>显示答案</summary>

**答案：B) Traces、Metrics、Logs**

**说明：**
本指南重点关注 traces、metrics 和 logs。OpenTelemetry 也在开发 profiling 支持；其稳定性因信号、组件和语言而异。关联需要兼容的资源属性和已传播的上下文，而不仅仅是启用三个 exporter。

</details>

---

2. OpenTelemetry Collector 组件的正确顺序是什么？
   - A) Processors -> Receivers -> Exporters
   - B) Exporters -> Processors -> Receivers
   - C) Receivers -> Processors -> Exporters
   - D) Receivers -> Exporters -> Processors

<details>
<summary>显示答案</summary>

**答案：C) Receivers -> Processors -> Exporters**

**说明：**
OTEL Collector pipeline 的结构为 Receivers（数据采集）-> Processors（数据处理/转换）-> Exporters（后端传输）。Receivers 以各种格式接收数据，Processors 执行批处理、过滤、添加属性等操作，Exporters 则将处理后的数据发送到目标位置。

</details>

---

3. 以下哪项不是 OpenTelemetry 中 auto-instrumentation 的优势？
   - A) 无需修改代码即可进行 instrumentation
   - B) 快速采用
   - C) 精细的业务逻辑 tracing
   - D) 一致的元数据

<details>
<summary>显示答案</summary>

**答案：C) 精细的业务逻辑 tracing**

**说明：**
Auto-instrumentation 无需修改代码，即可自动追踪 HTTP、数据库和消息队列等常见库调用。但是，业务逻辑中的详细操作或自定义 metrics 需要 manual instrumentation。通常会同时使用 auto-instrumentation 和 manual instrumentation。

</details>

---

4. 与基于 head 的 sampling 相比，Collector 的 tail_sampling processor 在何时有用？
   - A) 需要尽量减少资源使用时
   - B) 已观测到的 span 状态和持续时间应影响 sampling 时
   - C) 实现需要简单时
   - D) sampling 决策需要快速完成时

<details>
<summary>显示答案</summary>

**答案：B) 已观测到的 span 状态和持续时间应影响 sampling 时**

**说明：**
使用 Collector 0.160.0 默认的 `trace-complete` 策略时，决策计时器触发后会使用累积的 spans 进行评估；该名称并不能证明请求或 trace 已完成。已被 head sampling 丢弃的 spans 无法恢复。迟到的 spans、容量限制、重试和路由变更都会影响保留结果。有状态的 tail sampling 要求同一 trace 的 spans 到达同一个进行 sampling 的 Collector；它并不能保证保留每个错误或缓慢请求。

</details>

---

5. Resource 在 OpenTelemetry SDK 中的作用是什么？
   - A) 网络连接管理
   - B) 标识生成 telemetry 数据的实体
   - C) 数据压缩
   - D) 身份验证令牌管理

<details>
<summary>显示答案</summary>

**答案：B) 标识生成 telemetry 数据的实体**

**说明：**
Resource 用于标识 telemetry 生产者，例如通过 `service.name`、`service.version` 和 `deployment.environment.name`。配置的 SDK/provider 会将其与发出的数据关联。Kubernetes、云或自定义身份属性需要适当的配置或 detector；并非所有属性都会被自动发现。

</details>

---

6. 哪种 Kubernetes workload 通常会在每个符合条件的节点上运行一个 Collector？
   - A) Sidecar 模式
   - B) DaemonSet 模式
   - C) Gateway 模式
   - D) Deployment 模式

<details>
<summary>显示答案</summary>

**答案：B) DaemonSet 模式**

**说明：**
DaemonSet 会在每个符合条件的节点上放置一个 Pod；selector、taint 和调度约束决定节点是否符合条件。它不受 EKS Fargate 支持。Sidecar 与应用 Pod 共享，而 gateway 使用中央层，该层可能有多个副本。没有任何一种模式在所有情况下都最节省资源：应比较实际信号量、节点/Pod 数量、隔离性、可用性和有状态处理需求。DaemonSet 前的 ClusterIP Service 不会自动路由到本地节点。

</details>

---

7. 使用 OpenTelemetry Operator 进行 auto-instrumentation 注入时，会向 Pod 应用什么 annotation？
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>显示答案</summary>

**答案：B) instrumentation.opentelemetry.io/inject-java: "true"**

**说明：**
Operator 使用特定于语言的注入 annotation。对于 Deployment，请将它们放在 `spec.template.metadata.annotations` 中，并引用正确 namespace 中现有的 Instrumentation resource。成功注入还需要可用的 webhook 以及受支持的语言/runtime 配置。现有的 Pods 不会被追溯性地 instrument；还必须单独检查 Go 和其他语言特定的前提条件。

</details>

---

8. memory_limiter processor 在 OTEL Collector 配置中的作用是什么？
   - A) 数据压缩
   - B) 当超过配置的内存阈值时施加 backpressure
   - C) 缓存管理
   - D) 网络缓冲区管理

<details>
<summary>显示答案</summary>

**答案：B) 当超过配置的内存阈值时施加 backpressure**

**说明：**
`limit_mib` 是硬限制；软限制为 `limit_mib - spike_limit_mib`。超过软限制时，processor 会以可重试错误拒绝数据。超过硬限制时，它还会强制执行垃圾回收。上游的重试/backpressure 行为很重要：如果被拒绝的数据未被重试，则可能丢失。请在 container 内存限制之下留出余量；该 processor 既不是持久化存储，也不能绝对保证避免 OOM/数据丢失。

</details>

---

9. 以下哪项不是 OpenTelemetry 的 W3C Trace Context 标准中 traceparent header 的组成部分？
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>显示答案</summary>

**答案：D) span-name**

**说明：**
OpenTelemetry 使用 W3C Trace Context 标准。`traceparent` 字段包括 version、trace ID、parent ID 和 trace flags；parent ID 标识发送方 span，flags 包含一个 sampled bit。span name 不会携带在此 header 中。传播上下文本身不会记录或导出 span。

</details>

---

10. 如何在 OTEL Collector pipeline 中配置向多个 backend 发送数据？
    - A) 为每个 backend 运行单独的 Collectors
    - B) 在 exporters 数组中列出多个 exporter
    - C) 在单个 exporter 中配置多个 endpoint
    - D) 使用 fanout processor

<details>
<summary>显示答案</summary>

**答案：B) 在 exporters 数组中列出多个 exporter**

**说明：**
列出支持 pipeline 信号的已配置 exporters，例如在包含这些组件的 distribution 中，为 traces 配置 `exporters: [otlp/tempo, awsxray, datadog]`。Fan-out 并非跨 backend 的原子事务：exporter 错误、队列、重试、转换和 backend 接受情况可能导致不同的保留结果。

</details>

---

[返回指南](../../../observability/tracing/03-opentelemetry.md)
