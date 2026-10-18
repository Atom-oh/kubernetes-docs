# OpenTelemetry 测验

> **最后更新**：2026年9月13日

测试您对 OpenTelemetry 的理解。

---

1. 本指南重点关注哪三种核心信号？
   - A) 日志、指标、事件
   - B) 追踪、指标、日志
   - C) 跨度、计数器、日志
   - D) 追踪、告警、日志

<details>
<summary>显示答案</summary>

**答案：B) 追踪、指标、日志**

**说明：**
本指南重点关注追踪、指标和日志。OpenTelemetry 也在开发性能剖析支持；其稳定性因信号、组件和语言而异。关联这些信号需要兼容的资源属性和传播的上下文，仅启用三个导出器并不足够。

</details>

---

2. OpenTelemetry Collector 组件的正确顺序是什么？
   - A) 处理器 -> 接收器 -> 导出器
   - B) 导出器 -> 处理器 -> 接收器
   - C) 接收器 -> 处理器 -> 导出器
   - D) 接收器 -> 导出器 -> 处理器

<details>
<summary>显示答案</summary>

**答案：C) 接收器 -> 处理器 -> 导出器**

**说明：**
OTEL Collector 管道的结构为接收器（数据接入）-> 处理器（数据处理/转换）-> 导出器（向后端传输）。接收器接受多种格式的数据，处理器执行批处理、过滤、添加属性等操作，导出器则将处理后的数据发送到目标位置。

</details>

---

3. 以下哪项不是 OpenTelemetry 中自动插桩的优势？
   - A) 无需修改代码即可进行插桩
   - B) 快速引入
   - C) 细粒度的业务逻辑追踪
   - D) 一致的元数据

<details>
<summary>显示答案</summary>

**答案：C) 细粒度的业务逻辑追踪**

**说明：**
自动插桩无需修改代码，即可自动追踪 HTTP、数据库和消息队列等常见库调用。但是，业务逻辑中的详细操作或自定义指标需要手动插桩。通常会结合使用自动插桩和手动插桩。

</details>

---

4. 与头部采样相比，Collector 的 tail_sampling 处理器在何时有用？
   - A) 需要尽量减少资源使用时
   - B) 需要根据已观测到的跨度（span）状态和持续时间决定是否采样时
   - C) 实现需要简单时
   - D) 采样决策需要快速完成时

<details>
<summary>显示答案</summary>

**答案：B) 需要根据已观测到的跨度（span）状态和持续时间决定是否采样时**

**说明：**
使用 Collector 0.160.0 默认的 `trace-complete` 策略时，决策计时器触发后会使用累积的跨度进行评估；该名称并不能证明请求或追踪已完成。已被头部采样丢弃的跨度无法恢复。迟到的跨度、容量限制、重试和路由变更都会影响保留结果。有状态的尾部采样要求同一追踪的跨度到达同一个负责采样的 Collector；它并不能保证保留每个错误或缓慢请求。

</details>

---

5. Resource 在 OpenTelemetry SDK 中的作用是什么？
   - A) 网络连接管理
   - B) 标识生成遥测数据的实体
   - C) 数据压缩
   - D) 身份验证令牌管理

<details>
<summary>显示答案</summary>

**答案：B) 标识生成遥测数据的实体**

**说明：**
Resource 用于标识遥测数据的产生方，例如通过 `service.name`、`service.version` 和 `deployment.environment.name`。已配置的 SDK/提供者会将其与输出的数据关联。Kubernetes、云或自定义身份属性需要适当的配置或检测器；并非所有属性都会被自动发现。

</details>

---

6. 哪种 Kubernetes 工作负载通常会在每个符合条件的节点上运行一个 Collector？
   - A) Sidecar 模式
   - B) DaemonSet 模式
   - C) Gateway 模式
   - D) Deployment 模式

<details>
<summary>显示答案</summary>

**答案：B) DaemonSet 模式**

**说明：**
DaemonSet 会在每个符合条件的节点上放置一个 Pod；选择器、污点和调度约束决定节点是否符合条件。EKS Fargate 不支持 DaemonSet。Sidecar 与应用程序位于同一个 Pod 中，而网关使用可包含多个副本的集中式服务层。没有任何一种模式在所有情况下都最节省资源：应比较实际信号量、节点/Pod 数量、隔离性、可用性和有状态处理需求。位于 DaemonSet 前的 ClusterIP Service 不会自动将流量路由到本地节点。

</details>

---

7. 使用 OpenTelemetry Operator 注入自动插桩时，会向 Pod 添加什么注解？
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>显示答案</summary>

**答案：B) instrumentation.opentelemetry.io/inject-java: "true"**

**说明：**
Operator 使用针对特定语言的注入注解。对于 Deployment，请将这些注解放在 `spec.template.metadata.annotations` 中，并引用正确命名空间中现有的 Instrumentation 资源。成功注入还需要正常工作的 Webhook 以及受支持的语言/运行时配置。注解不会为已经存在的 Pod 自动补充插桩；还必须单独检查 Go 和其他语言各自的前置条件。

</details>

---

8. memory_limiter 处理器在 OTEL Collector 配置中的作用是什么？
   - A) 数据压缩
   - B) 当超过配置的内存阈值时施加背压
   - C) 缓存管理
   - D) 网络缓冲区管理

<details>
<summary>显示答案</summary>

**答案：B) 当超过配置的内存阈值时施加背压**

**说明：**
`limit_mib` 是硬限制；软限制为 `limit_mib - spike_limit_mib`。超过软限制时，处理器会拒绝接收数据并返回可重试的错误。超过硬限制时，它还会强制执行垃圾回收。上游的重试和背压行为很重要：如果被拒绝的数据未被重试，则可能丢失。请在容器内存限制之下留出余量；该处理器既不是持久化存储，也不能绝对保证避免 OOM/数据丢失。

</details>

---

9. 以下哪项不是 OpenTelemetry 的 W3C Trace Context 标准中 traceparent 标头的组成部分？
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>显示答案</summary>

**答案：D) span-name**

**说明：**
OpenTelemetry 使用 W3C Trace Context 标准。`traceparent` 字段包括版本（version）、追踪 ID、父 ID 和追踪标志；父 ID 标识发送该上下文的跨度，标志中包含采样位。该标头不携带跨度名称。传播上下文本身不会记录或导出跨度。

</details>

---

10. 如何在 OTEL Collector 管道中配置向多个后端发送数据？
    - A) 为每个后端运行单独的 Collector
    - B) 在 exporters 数组中列出多个导出器
    - C) 在单个导出器中配置多个端点
    - D) 使用 fanout 处理器

<details>
<summary>显示答案</summary>

**答案：B) 在 exporters 数组中列出多个导出器**

**说明：**
列出已配置且支持该管道信号的导出器，例如在包含这些组件的发行版中，为追踪配置 `exporters: [otlp/tempo, awsxray, datadog]`。向多个后端分发数据并非跨后端的原子事务：导出器错误、队列、重试、转换和后端接收情况可能导致不同的保留结果。

</details>

---

[返回指南](../../../observability/tracing/03-opentelemetry.md)
