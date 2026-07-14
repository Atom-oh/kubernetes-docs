# AWS X-Ray 测验

测试你对 AWS X-Ray 的理解。

---

1. 以下哪项不是 AWS X-Ray 的主要功能？
   - A) Service map 可视化
   - B) 分布式追踪
   - C) 日志聚合
   - D) 性能分析

<details>
<summary>显示答案</summary>

**答案：C) 日志聚合**

**说明：**
AWS X-Ray 提供分布式追踪、Service map 可视化和性能分析。日志聚合是 CloudWatch Logs 的功能。X-Ray 可以与 CloudWatch Logs 集成以关联 traces 和 logs，但它本身不会收集或存储日志。

</details>

---

2. 在 EKS 中部署 X-Ray daemon 的推荐方式是什么？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>显示答案</summary>

**答案：C) DaemonSet**

**说明：**
建议将 X-Ray Daemon 部署为 DaemonSet。DaemonSet 会在每个 node 上运行一个 Pod，使该 node 上的所有应用程序 Pod 都能够将 trace data 发送到本地 X-Ray Daemon。这样可以最大限度地降低网络延迟，并确保可靠的数据传输。

</details>

---

3. 在 X-Ray 中设置集中式采样规则时，以下哪项不是使用的参数？
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>显示答案</summary>

**答案：D) RetentionDays**

**说明：**
X-Ray 采样规则包括 FixedRate（固定采样率）、ReservoirSize（每秒最小样本数）和 Priority（规则优先级）。RetentionDays 不是采样规则参数，而是与 X-Ray 数据保留设置相关。默认数据保留期为 30 天。

</details>

---

4. X-Ray 中 Annotation 和 Metadata 有什么区别？
   - A) Annotation 的最大数量为 100，Metadata 不受限制
   - B) Annotation 已编入索引且可筛选，Metadata 未编入索引
   - C) Annotation 仅支持 strings，Metadata 支持所有类型
   - D) Annotation 自动生成，Metadata 手动添加

<details>
<summary>显示答案</summary>

**答案：B) Annotation 已编入索引且可筛选，Metadata 未编入索引**

**说明：**
Annotations 已编入索引，并且可以在 X-Ray console 中使用 filter expressions 搜索（最多 50 个）。Metadata 未编入索引，无法搜索，但用于存储详细信息。应将 Annotations 用于重要标识符（user_id、order_id 等），并将 Metadata 用于 request/response bodies 等详细信息。

</details>

---

5. 使用 ADOT (AWS Distro for OpenTelemetry) Collector 的以下哪项不是优势？
   - A) 使用 vendor-neutral 标准
   - B) 支持多个 backend
   - C) 针对 X-Ray 的特定优化
   - D) 支持 OpenTelemetry protocol

<details>
<summary>显示答案</summary>

**答案：C) 针对 X-Ray 的特定优化**

**说明：**
ADOT Collector 基于 OpenTelemetry，具有 vendor-neutral 特性，除 X-Ray 外还可以将数据发送到各种 backend（Prometheus、Jaeger、Datadog 等）。针对 X-Ray 的特定优化是 X-Ray Daemon 的特性。ADOT 的优势是标准化 instrumentation 和多 backend 支持。

</details>

---

6. X-Ray service map 中的 node 何时显示为红色？
   - A) 当 response time 较慢时
   - B) 当 traffic 较高时
   - C) 当 error rate 较高时
   - D) 当它是新添加的 service 时

<details>
<summary>显示答案</summary>

**答案：C) 当 error rate 较高时**

**说明：**
X-Ray service map 中的 node 颜色表示 service health status。红色表示 error rate 较高的 service，黄色表示存在 warning-level issues 的 service，绿色表示正常的 service。这有助于快速识别存在问题的 service。

</details>

---

7. 要在 X-Ray 中接收 OpenTelemetry trace data，需要什么配置？
   - A) 安装 X-Ray SDK
   - B) 配置 AWS X-Ray Propagator 和 ID Generator
   - C) 安装 CloudWatch Agent
   - D) 添加 Lambda Layer

<details>
<summary>显示答案</summary>

**答案：B) 配置 AWS X-Ray Propagator 和 ID Generator**

**说明：**
要将 trace data 从 OpenTelemetry 发送到 X-Ray，需要配置 AWS X-Ray Propagator（context propagation）和 AWS X-Ray ID Generator（生成 X-Ray format TraceIDs）。这样可以在使用 OpenTelemetry 标准的同时生成与 X-Ray 兼容的 trace data。

</details>

---

8. 要查找 response time 超过 2 秒的 requests，正确的 X-Ray filter expression query 是什么？
   - A) `duration > 2`
   - B) `responsetime > 2`
   - C) `latency >= 2000`
   - D) `time > 2s`

<details>
<summary>显示答案</summary>

**答案：B) responsetime > 2**

**说明：**
在 X-Ray filter expressions 中，`responsetime` keyword 用于表示 response time，单位为秒。`responsetime > 2` 会筛选耗时超过 2 秒的 requests。其他有用的 filters 包括 `fault = true`（server errors）、`error = true`（client errors）和 `service("name")`（特定 service）。

</details>

---

9. 将 X-Ray 与 CloudWatch ServiceLens 集成时，以下哪项不是提供的功能？
   - A) traces 和 metrics 的集成视图
   - B) 在 service map 上显示 CloudWatch alarms
   - C) 自动 code instrumentation
   - D) 关联 logs 和 traces

<details>
<summary>显示答案</summary>

**答案：C) 自动 code instrumentation**

**说明：**
CloudWatch ServiceLens 提供 X-Ray traces、CloudWatch metrics 和 logs 的集成视图。它会在 service map 上显示 CloudWatch alarms，并提供关联 logs 和 traces 的功能。但是，必须通过 X-Ray SDK 或 OpenTelemetry auto-instrumentation 实现自动 code instrumentation。

</details>

---

10. X-Ray Groups 的主要用途是什么？
    - A) 用户权限管理
    - B) 基于 filter 的 trace grouping 和 alerting
    - C) 资源成本分配
    - D) 数据保留策略设置

<details>
<summary>显示答案</summary>

**答案：B) 基于 filter 的 trace grouping 和 alerting**

**说明：**
X-Ray Groups 使用 filter expressions 对 traces 进行分组。例如，可以为生产环境、特定 service、error requests 等创建 groups。可以为每个 group 设置 CloudWatch alarms，以便在特定条件下（例如 error rates 增加时）接收 alerts。

</details>

---
