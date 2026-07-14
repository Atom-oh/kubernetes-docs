# 可观测性实验第 3 部分：MSA Deployment 和 Canary 测验

> **最后更新**: February 22, 2026

测试你对可观测性端到端实验第 3 部分中涵盖的 MSA Deployment 和 Canary 发布概念的理解。

---

1. 哪种 ArgoCD ApplicationSet Generator 类型最适合将同一应用程序部署到多个集群？
   - A) 使用硬编码集群名称的 List Generator
   - B) 根据标签自动发现已注册集群的 Cluster Generator
   - C) 读取仓库中集群配置的 Git Generator
   - D) 用于临时环境的 Pull Request Generator

<details>
<summary>显示答案</summary>

**答案：B) 根据标签自动发现已注册集群的 Cluster Generator**

**说明：**
Cluster Generator 会动态发现已注册到 ArgoCD 的集群，并为每个集群生成 Application。通过使用集群标签（例如 `environment: production`、`region: us-east-1`），你可以有选择地定位集群。与硬编码列表相比，这种方式更易于维护，因为添加或移除集群只需更新集群注册和标签，而无需修改 ApplicationSet 定义。

</details>

---

2. ArgoCD 中 App-of-Apps 模式的主要优势是什么？
   - A) 它减少了所需 ArgoCD Application 的总数
   - B) 它支持层级化管理，其中父 Application 管理子 Application，提供组织结构和批量操作
   - C) 它通过并行化所有部署来提升同步性能
   - D) 它消除了对 Helm 或 Kustomize 的需求

<details>
<summary>显示答案</summary>

**答案：B) 它支持层级化管理，其中父 Application 管理子 Application，提供组织结构和批量操作**

**说明：**
App-of-Apps 模式会创建一个层级结构，其中根 Application 的 manifests 包含其他 Application 的定义。它提供：对多个应用程序的集中管理、一致的配置继承、整个平台更轻松的引导，以及通过更新父 Application 将更改应用到多个应用程序的能力。它尤其适用于管理多个微服务或多租户环境的平台团队。

</details>

---

3. Karpenter NodePool 中的 weight 和 limits 设置控制什么？
   - A) Weight 决定每个 Pod 的 CPU 分配；limits 设置内存边界
   - B) Weight 设置 NodePool 之间的调度优先级；limits 限制 Karpenter 可以为该池配置的总资源
   - C) Weight 控制节点定价层级；limits 设置最大节点数
   - D) Weight 决定 Pod 密度；limits 设置网络带宽

<details>
<summary>显示答案</summary>

**答案：B) Weight 设置 NodePool 之间的调度优先级；limits 限制 Karpenter 可以为该池配置的总资源**

**说明：**
当多个 NodePool 都能满足 Pod 的要求时，NodePool weight（0-100）决定首选项——weight 越高，优先级越高。Limits 定义 Karpenter 可以为该 NodePool 配置的最大资源（CPU、内存），从而防止无限扩缩容。这使你能够创建分层基础设施：为首选实例类型配置带有 limits 的高 weight 池以控制成本，并为溢出容量配置较低 weight 的备用池。

</details>

---

4. KEDA 的 SQS scaler 可以使用哪些指标类型来做出扩缩容决策？
   - A) 仅 ApproximateNumberOfMessages
   - B) ApproximateNumberOfMessages、ApproximateNumberOfMessagesNotVisible 或 ApproximateNumberOfMessagesDelayed
   - C) 仅自定义 CloudWatch 指标
   - D) SQS scaler 仅支持基于时间的扩缩容

<details>
<summary>显示答案</summary>

**答案：B) ApproximateNumberOfMessages、ApproximateNumberOfMessagesNotVisible 或 ApproximateNumberOfMessagesDelayed**

**说明：**
KEDA 的 SQS scaler 支持多种队列指标：`ApproximateNumberOfMessages`（可见且准备处理的消息）、`ApproximateNumberOfMessagesNotVisible`（正在处理但尚未删除的消息）以及 `ApproximateNumberOfMessagesDelayed`（延迟队列中的消息）。你可以根据扩缩容策略进行选择——通常使用 `ApproximateNumberOfMessages` 根据积压量进行扩缩容，或使用组合指标来更全面地了解队列深度。

</details>

---

5. OpenTelemetry 自动插桩和手动插桩之间的关键区别是什么？
   - A) 自动插桩提供比手动插桩更详细的 trace
   - B) 自动插桩无需更改代码即可从受支持的框架自动捕获 telemetry，而手动插桩需要为自定义 span 和指标显式调用 SDK
   - C) 手动插桩已弃用，取而代之的是自动插桩
   - D) 自动插桩仅适用于解释型语言

<details>
<summary>显示答案</summary>

**答案：B) 自动插桩无需更改代码即可从受支持的框架自动捕获 telemetry，而手动插桩需要为自定义 span 和指标显式调用 SDK**

**说明：**
自动插桩（通过 agent、字节码操作或 monkey-patching）无需修改应用程序代码，即可从流行的框架、库和运行时自动捕获 telemetry。手动插桩使用 OTel SDK 显式创建 span、添加属性、记录指标并发出日志。最佳实践是结合两者：使用自动插桩覆盖标准框架，使用手动插桩处理业务特定的 span 和自定义指标。

</details>

---

6. `-javaagent:opentelemetry-javaagent.jar` JVM 参数为 Java 服务启用了什么？
   - A) 它仅启用 JMX 监控
   - B) 它附加 OTel Java agent，以对常见的 Java 框架和库进行自动插桩
   - C) 它配置 Java 垃圾回收 telemetry
   - D) 它启用 Java Flight Recorder 集成

<details>
<summary>显示答案</summary>

**答案：B) 它附加 OTel Java agent，以对常见的 Java 框架和库进行自动插桩**

**说明：**
OpenTelemetry Java agent 使用字节码插桩，从流行的 Java 框架（Spring、JAX-RS、gRPC）、HTTP 客户端（Apache HttpClient、OkHttp）、数据库（JDBC、Hibernate）和消息传递系统（Kafka、RabbitMQ）中自动捕获 telemetry。该 agent 在 JVM 启动时通过 `-javaagent` 附加，无需更改代码。通过环境变量进行配置（例如 `OTEL_EXPORTER_OTLP_ENDPOINT`、`OTEL_SERVICE_NAME`）。

</details>

---

7. AnalysisTemplate 在 Argo Rollouts Canary 部署中起什么作用？
   - A) 它定义用于安全扫描的容器镜像分析
   - B) 它指定指标查询和成功标准，用以确定 Canary 发布应继续还是回滚
   - C) 它配置 Canary 期间的流量拆分百分比
   - D) 它管理渐进式交付期间的副本数

<details>
<summary>显示答案</summary>

**答案：B) 它指定指标查询和成功标准，用以确定 Canary 发布应继续还是回滚**

**说明：**
AnalysisTemplate 为 Canary 发布定义自动化分析。它指定：指标提供方（Prometheus、Datadog、CloudWatch）、要评估的查询（例如错误率、延迟）、成功/失败阈值和测量间隔。在 rollout 期间，Argo Rollouts 根据模板创建 AnalysisRuns，并持续评估指标。如果不符合标准，rollout 会自动暂停或回滚，从而无需人工干预即可实现安全的渐进式交付。

</details>

---

8. 类似 `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))` 的成功率 PromQL 查询衡量什么？
   - A) 过去 5 分钟内成功请求的总数
   - B) HTTP 2xx 响应占总响应的比率，代表成功率
   - C) 成功请求的平均响应时间
   - D) 唯一成功用户的数量

<details>
<summary>显示答案</summary>

**答案：B) HTTP 2xx 响应占总响应的比率，代表成功率**

**说明：**
该 PromQL 查询通过将成功请求（由正则表达式 `2..` 匹配的 HTTP 2xx 状态码）除以总请求来计算成功率，两者均按 5 分钟速率计算。`rate()` 函数计算该时间窗口内的每秒平均值，而 `sum()` 会跨所有标签维度进行聚合。结果是介于 0 和 1 之间的比率，通常显示为百分比。这是服务可靠性的关键 SLI。

</details>

---

9. 当 Argo Rollouts AnalysisRun 返回 FAIL 状态时，会自动发生什么？
   - A) rollout 继续，但会发送警报
   - B) rollout 暂停并等待人工干预
   - C) rollout 自动中止并缩减 Canary，将稳定版本恢复为承载全部流量
   - D) AnalysisRun 使用不同参数重新启动

<details>
<summary>显示答案</summary>

**答案：C) rollout 自动中止并缩减 Canary，将稳定版本恢复为承载全部流量**

**说明：**
当 AnalysisRun 失败时（指标超过失败阈值），Argo Rollouts 会自动触发回滚：Canary ReplicaSet 缩减至零，所有流量切回稳定版本，并且 Rollout 状态变为 "Degraded"。这种自动回滚是渐进式交付的一项关键安全功能——有问题的发布会自动还原，无需人工干预，从而将不良部署的影响范围降至最低。

</details>

---

10. 使用 OpenTelemetry SDK 时，为什么 W3C TraceContext 上下文传播如此重要？
    - A) 它是指标收集所必需的
    - B) 它通过 HTTP headers 跨服务边界传递 trace context（trace ID、span ID、flags），从而启用分布式追踪
    - C) 它改善日志压缩
    - D) 它仅适用于 gRPC 服务

<details>
<summary>显示答案</summary>

**答案：B) 它通过 HTTP headers 跨服务边界传递 trace context（trace ID、span ID、flags），从而启用分布式追踪**

**说明：**
W3C TraceContext 是一种通过 HTTP headers（`traceparent`、`tracestate`）传播分布式 trace 信息的标准化格式。当服务 A 调用服务 B 时，上下文传播会传递 trace ID 和父 span ID，使服务 B 的 span 能够关联到服务 A 的 trace。如果没有正确传播，trace 会在服务边界处断开，显示为不连贯的片段，而不是完整的请求流程。配置后，OTel SDK 会自动处理此过程，但服务必须转发这些 headers。

</details>
