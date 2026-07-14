# OpenTelemetry 测验

测试你对 OpenTelemetry 的理解。

---

1. OpenTelemetry 支持哪三种信号？
   - A) Logs、Metrics、Events
   - B) Traces、Metrics、Logs
   - C) Spans、Counters、Logs
   - D) Traces、Alerts、Logs

<details>
<summary>显示答案</summary>

**答案：B) Traces、Metrics、Logs**

**说明：**
OpenTelemetry 对三种核心可观测性信号进行了标准化：Traces（分布式追踪）、Metrics 和 Logs。通过以集成方式收集并关联这三种信号，你可以实现全面的系统可观测性。

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
OTEL Collector pipeline 的结构为 Receivers（数据接收）-> Processors（数据处理/转换）-> Exporters（后端传输）。Receivers 接受各种格式的数据，Processors 执行批处理、过滤、添加属性等操作，Exporters 将处理后的数据发送到目标位置。

</details>

---

3. 以下哪项不是 OpenTelemetry 中 auto-instrumentation 的优势？
   - A) 无需修改代码即可进行 instrumentation
   - B) 快速采用
   - C) 细粒度的业务逻辑追踪
   - D) 一致的元数据

<details>
<summary>显示答案</summary>

**答案：C) 细粒度的业务逻辑追踪**

**说明：**
auto-instrumentation 无需修改代码，即可自动追踪 HTTP、数据库和消息队列等常见库调用。但是，业务逻辑内的详细操作或自定义 Metrics 需要 manual instrumentation。通常会将 auto-instrumentation 和 manual instrumentation 结合使用。

</details>

---

4. 在什么情况下，OTEL Collector 的 tail_sampling processor 比 head-based sampling 更具优势？
   - A) 需要尽量减少资源使用时
   - B) 不能遗漏出现错误或高延迟的请求时
   - C) 实现需要简单时
   - D) 需要快速作出采样决策时

<details>
<summary>显示答案</summary>

**答案：B) 不能遗漏出现错误或高延迟的请求时**

**说明：**
tail-based sampling 会在请求完成后根据结果（错误、延迟等）决定是否采样。这可确保不会遗漏重要请求（发生错误、响应时间超标）。相比之下，head-based sampling 在请求开始时作出决策，因此实现更简单、资源使用更低，但可能遗漏重要请求。

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
Resource 是用于标识生成 telemetry 数据的实体（Service、主机、容器等）的元数据。它包含 service.name、service.version、deployment.environment 等属性，以明确数据来源。此信息会自动附加到所有 telemetry 数据上。

</details>

---

6. 在 EKS 中，哪种 OTEL Collector 部署模式最节省资源？
   - A) Sidecar 模式
   - B) DaemonSet 模式
   - C) Gateway 模式
   - D) Deployment 模式

<details>
<summary>显示答案</summary>

**答案：B) DaemonSet 模式**

**说明：**
DaemonSet 模式每个节点只运行一个 Collector，因此资源效率较高。Sidecar 模式会为每个 Pod 运行一个 Collector，资源开销较大。Gateway 模式是集中式的，但可能成为单点故障。通常建议采用 DaemonSet 进行收集、Gateway 进行处理和传输的组合方式。

</details>

---

7. 使用 OpenTelemetry Operator 进行 auto-instrumentation 注入时，应将哪个 annotation 应用于 Pod？
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>显示答案</summary>

**答案：B) instrumentation.opentelemetry.io/inject-java: "true"**

**说明：**
OpenTelemetry Operator 使用 `instrumentation.opentelemetry.io/inject-{language}` 格式的 annotations。特定语言的 annotations 包括 inject-java、inject-python、inject-nodejs、inject-dotnet、inject-go 等。instrumentation agents 会自动注入带有这些 annotations 的 Pods。

</details>

---

8. OTEL Collector 配置中的 memory_limiter processor 有什么作用？
   - A) 数据压缩
   - B) 内存不足时防止数据丢失
   - C) 缓存管理
   - D) 网络缓冲区管理

<details>
<summary>显示答案</summary>

**答案：B) 内存不足时防止数据丢失**

**说明：**
memory_limiter processor 会监控并限制 Collector 的内存使用量。当内存使用量达到 limit_mib 时，它会拒绝接收新数据，以防止因 OOM（Out of Memory）导致数据丢失。spike_limit_mib 为突发的内存峰值提供缓冲。

</details>

---

9. 在 OpenTelemetry 的 W3C Trace Context 标准中，以下哪项不是 traceparent header 的组成部分？
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>显示答案</summary>

**答案：D) span-name**

**说明：**
W3C Trace Context 的 traceparent header 格式为 `version-trace_id-parent_id-trace_flags`。version 是格式版本，trace_id 是整个 trace 的标识符，parent_id 是父 Span ID，trace_flags 是采样标志。span-name 存储在 Span 内，不包含在传播 header 中。

</details>

---

10. 如何在 OTEL Collector pipeline 中配置将数据发送到多个后端？
    - A) 为每个后端运行独立的 Collector
    - B) 在 exporters 数组中列出多个 exporter
    - C) 在单个 exporter 中配置多个 endpoint
    - D) 使用 fanout processor

<details>
<summary>显示答案</summary>

**答案：B) 在 exporters 数组中列出多个 exporter**

**说明：**
在 OTEL Collector pipeline 配置中，在 exporters 数组中列出多个 exporter 会将相同的数据发送到所有后端。例如：`exporters: [otlp/tempo, awsxray, datadog]`。这使得可以通过单个 Collector 同时使用多个可观测性后端。

</details>

---
