# Grafana Tempo 测验

测试您对 Grafana Tempo 的理解。

---

1. Grafana Tempo 的主要特点是什么？
   - A) 为快速搜索而索引所有数据
   - B) 消除索引成本的基于 TraceID 的存储
   - C) 实时流处理
   - D) 自动异常检测

<details>
<summary>显示答案</summary>

**答案: B) 消除索引成本的基于 TraceID 的存储**

**说明:**
Tempo 仅使用 TraceID 存储和搜索 trace 数据，无需索引。这使得能够以较低成本存储大规模 trace 数据。其他 tracing 系统会对各种字段建立索引以提升搜索性能，但这会导致存储成本增加。

</details>

---

2. Tempo 架构中的哪个组件接收并验证 trace 数据？
   - A) Ingester
   - B) Querier
   - C) Distributor
   - D) Compactor

<details>
<summary>显示答案</summary>

**答案: C) Distributor**

**说明:**
Distributor 接收各种格式的 trace 数据（Jaeger、Zipkin、OTLP 等）并对其进行验证。验证后的数据会根据哈希分发到相应的 Ingester。Ingester 负责缓冲和存储数据，而 Querier 负责搜索。

</details>

---

3. 仅检索错误状态 span 的正确 TraceQL 查询是什么？
   - A) `{ error = true }`
   - B) `{ status = error }`
   - C) `{ span.error = 1 }`
   - D) `{ state = "ERROR" }`

<details>
<summary>显示答案</summary>

**答案: B) { status = error }**

**说明:**
在 TraceQL 中，使用 `{ status = error }` 语法筛选错误 span。status 字段可取值为 ok、error 或 unset，它们分别对应 OpenTelemetry 的 SpanStatus。

</details>

---

4. 将 S3 用作 Tempo 后端存储时，推荐使用哪种 AWS 身份验证方法？
   - A) 将 Access Key 存储在环境变量中
   - B) 将凭证存储在 Secret 中
   - C) IRSA (IAM Roles for Service Accounts)
   - D) EC2 Instance Profile

<details>
<summary>显示答案</summary>

**答案: C) IRSA (IAM Roles for Service Accounts)**

**说明:**
建议在 EKS 环境中使用 IRSA。IRSA 将 IAM roles 与 Kubernetes ServiceAccounts 关联，可在 Pod 级别实现细粒度的权限管理。与存储静态凭证相比，它更安全，并且凭证轮换会自动处理。

</details>

---

5. 以下哪项不是 Tempo 的 Metrics Generator 生成的指标类型？
   - A) Service Graph 指标
   - B) Span 指标
   - C) 日志指标
   - D) RED 指标（Rate、Error、Duration）

<details>
<summary>显示答案</summary>

**答案: C) 日志指标**

**说明:**
Tempo 的 Metrics Generator 会从 trace 数据中生成 Service Graph 指标和 Span 指标（包括 RED 指标）。这些指标会发送到 Prometheus，用于服务地图可视化和性能监控。日志指标由 Loki 生成，不属于 Tempo 的范围。

</details>

---

6. 在 Tempo Distributed 模式中，用于在多个 Ingester 之间维护副本以确保持久性的功能名称是什么？
   - A) Sharding
   - B) Replication Factor
   - C) Partitioning
   - D) Mirroring

<details>
<summary>显示答案</summary>

**答案: B) Replication Factor**

**说明:**
Replication Factor 决定每个 trace 被复制到多少个 Ingester。例如，replication_factor=3 表示每个 trace 存储在 3 个 Ingester 上，因此即使一个 Ingester 发生故障也不会丢失数据。这是 Tempo 高可用性配置中的重要设置。

</details>

---

7. 通过在 Grafana 中集成 Tempo 和 Loki 实现 Trace-to-Log 关联，需要进行什么配置？
   - A) 部署在同一个 namespace 中
   - B) 配置 derivedFields 以提取 TraceID
   - C) 使用同一个 S3 bucket
   - D) 使用相同的 labels

<details>
<summary>显示答案</summary>

**答案: B) 配置 derivedFields 以提取 TraceID**

**说明:**
在 Loki 数据源设置中配置 derivedFields，从日志中提取 TraceID 并创建指向 Tempo 的链接。通过使用正则表达式模式匹配 TraceID 并将其链接到 Tempo 数据源，您可以直接从日志中查询相关 trace。

</details>

---

8. Compactor 在 Tempo 中的作用是什么？
   - A) 实时查询处理
   - B) 接收和分发 trace 数据
   - C) 压缩已存储的 block 并应用保留策略
   - D) 内存缓冲区管理

<details>
<summary>显示答案</summary>

**答案: C) 压缩已存储的 block 并应用保留策略**

**说明:**
Compactor 会压缩并优化存储在 Object Storage 中的 trace block。它还会根据 block_retention 设置应用保留策略，以删除旧数据。Compactor 通常以单个实例运行，每个 cluster 中只有一个处于活动状态。

</details>

---

9. 用于查找从 Service A 到 Service B 的调用模式的正确 TraceQL 查询是什么？
   - A) `{ resource.service.name = "A" } AND { resource.service.name = "B" }`
   - B) `{ resource.service.name = "A" } >> { resource.service.name = "B" }`
   - C) `{ resource.service.name = "A" } -> { resource.service.name = "B" }`
   - D) `{ resource.service.name = "A" } | { resource.service.name = "B" }`

<details>
<summary>显示答案</summary>

**答案: B) { resource.service.name = "A" } >> { resource.service.name = "B" }**

**说明:**
在 TraceQL 中，`>>` 运算符执行结构匹配，用于查找与第一个条件匹配的 span 是与第二个条件匹配的 span 的祖先的情况。这使得可以分析服务之间的调用模式。`>` 运算符仅匹配直接的父子关系。

</details>

---

10. 以下哪项不是 Tempo 性能优化的推荐设置？
    - A) 将 max_block_duration 设置为 30 分钟
    - B) 使用 Memcached 作为缓存
    - C) 为所有属性建立索引
    - D) 在 Query Frontend 中启用查询分片

<details>
<summary>显示答案</summary>

**答案: C) 为所有属性建立索引**

**说明:**
Tempo 的核心设计原则是尽可能减少索引以降低成本。为所有属性建立索引会抵消 Tempo 的优势，并显著增加存储成本。相反，应通过调整 max_block_duration、缓存和查询分片来优化性能。

</details>

---
