# AWS X-Ray 测验

> **最后更新**: September 13, 2026

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. 以下哪项行为不是 X-Ray 追踪管道自动提供的？
   - A) 基于收集到的 trace 生成 Service 依赖关系可视化
   - B) 分布式请求追踪
   - C) 收集每个应用程序的普通日志文件
   - D) 分析收集到的 span 时间

<details>
<summary>显示答案</summary>

**答案：C) 收集每个应用程序的普通日志文件**

**说明：**

追踪不会配置通用的应用程序日志收集器。CloudWatch Transaction Search 可以将结构化 span 存储在 aws/spans 中，但这不同于收集所有普通应用程序日志。Metrics/logs 需要各自配置的管道和访问控制。

</details>

---

2. 对于旧版 daemon 路径，哪种 Kubernetes workload 可以在每个符合条件的 EC2 worker 上运行一个 daemon？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**说明：**

DaemonSet 会选择符合条件的 node；EKS Fargate 不支持它。ClusterIP Service 可能会选择另一个 node 上的 daemon，因此仅凭 DaemonSet 放置并不能保证 node 本地或无丢失的 UDP 传递。X-Ray SDKs/daemon 处于维护模式；本指南针对新的 instrumentation 使用单独的 OpenTelemetry collector Deployment。

</details>

---

3. 以下哪项不是 X-Ray 集中式 sampling rule 的字段？
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>显示答案</summary>

**答案：D) RetentionDays**

**说明：**

FixedRate、ReservoirSize 和 Priority 是 sampling 字段。RetentionDays 不是 sampling-rule 参数。当没有流量时，reservoir 并不能保证最低 trace 数量。规则需要兼容的 remote sampler；head sampling 无法选择尚未发生的响应错误。

</details>

---

4. 以下哪种说法正确区分了 X-Ray annotations 和 metadata？
   - A) 每个 segment 都会独立接收 100 个已建立索引的 annotation
   - B) Annotations 会建立索引以供 X-Ray 筛选；未建立索引的 metadata 会保持存储且可访问
   - C) Annotations 仅接受字符串
   - D) Metadata 会自动脱敏

<details>
<summary>显示答案</summary>

**答案：B) Annotations 会建立索引以供 X-Ray 筛选；未建立索引的 metadata 会保持存储且可访问**

**说明：**

X-Ray 每个 trace 最多为50个 annotation 建立索引。Metadata 不会像 annotation 一样建立索引，但未建立索引并不意味着它是机密的或不可访问的。请使用经过审慎限定的字段，并在收集前移除敏感 payload、identifier、token 和 SQL parameter。index_all_attributes=false 不是 redaction processor。

</details>

---

5. 关于 ADOT Collector，哪种说法是错误的？
   - A) 它接受受支持的 OpenTelemetry protocol
   - B) 它可以将受支持的 pipeline 连接到多个 backend
   - C) 声明一个未使用的 CloudWatch Logs exporter 会自动将 trace 转换为 log
   - D) 必须检查其发布的 component inventory

<details>
<summary>显示答案</summary>

**答案：C) 声明一个未使用的 CloudWatch Logs exporter 会自动将 trace 转换为 log**

**说明：**

Receivers、processors 和 exporters 必须连接到适当的 logs/metrics/traces pipeline。ADOT 包含 awsxray 等 AWS integration，因此 AWS 特定行为并非旧版 daemon 独有。不要假设每个上游 Contrib exporter 都存在于所选的 ADOT release 中。

</details>

---

6. X-Ray/CloudWatch trace map 中的红色流量类别代表什么？
   - A) 每个缓慢请求
   - B) 高流量
   - C) HTTP5xx 等 server fault
   - D) 新发现的 Service

<details>
<summary>显示答案</summary>

**答案：C) HTTP5xx 等 server fault**

**说明：**

红色代表 server fault，黄色代表 client error，紫色代表 HTTP429 等 throttling，绿色代表成功的流量。这些类别不是任意的 latency threshold，也不意味着每个红色 Service 都已超过用户定义的高错误率 alarm。

</details>

---

7. 通过本指南的 X-Ray 收集路径发送 OpenTelemetry span 需要什么？
   - A) 每个 producer 都必须使用旧版 X-Ray SDK
   - B) 具有正确 AWS identity 的兼容且经过身份验证的 OTLP collector/export pipeline
   - C) 每个应用程序都必须安装 CloudWatch Agent
   - D) 每个 EKS Pod 都必须安装 Lambda Layer

<details>
<summary>显示答案</summary>

**答案：B) 具有正确 AWS identity 的兼容且经过身份验证的 OTLP collector/export pipeline**

**说明：**

本指南通过 mTLS 向 ADOT 发送 OTLP，其 awsxray exporter 调用经过签名的经典 X-Ray API。X-Ray 支持 W3C128-bit ID；特殊的 X-Ray ID generator/propagator 并非普遍强制要求。替代的原生 OTLP HTTPS endpoint 需要 SigV4 和 Transaction Search。请为实际 integration 配置 propagation。

</details>

---

8. 以下哪个 X-Ray response-time filter 会选择严格大于两秒的值？
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>显示答案</summary>

**答案：B) `responsetime > 2`**

**说明：**

Response-time 值以秒为单位。>2 不包括恰好为2秒；>=2 包括它。这些是 X-Ray filter expression，不是 shell command 或 Logs Insights QL。duration 也是有文档说明的 X-Ray keyword，不能将其描述为虚构的无效 keyword。

</details>

---

9. 仅仅打开 CloudWatch trace map 无法证明什么？
   - A) 已收集 trace 依赖关系的视图
   - B) 与已配置 metrics/alarms 的关联
   - C) 每个应用程序的自动 instrumentation 和成功收集
   - D) 指向适当关联的 logs 的链接

<details>
<summary>显示答案</summary>

**答案：C) 每个应用程序的自动 instrumentation 和成功收集**

**说明：**

Instrumentation、collection、identity 和 correlation 必须分别配置。原来的 ServiceLens 和 X-Ray map 已合并到 CloudWatch trace map 中。现有 telemetry 可以在那里关联，但未挂载的 ConfigMap 或空视图不能证明 agent 和应用程序已完成配置。

</details>

---

10. X-Ray Groups 的用途是什么？
   - A) 替代 IAM authorization
   - B) 对匹配的 trace 分组以进行分析和关联的 metrics/alarms
   - C) 自动分配 AWS billing ownership
   - D) 通过 sampling rule 设置 retention

<details>
<summary>显示答案</summary>

**答案：B) 对匹配的 trace 分组以进行分析和关联的 metrics/alarms**

**说明：**

Groups 使用 filter expression 选择 trace。请审查生成的 metrics，并分别配置 CloudWatch alarms。创建 group 不会为 producer 添加 instrumentation、覆盖 sampling、定义 IAM isolation，或证明端到端 alert 已触发。

</details>

---
