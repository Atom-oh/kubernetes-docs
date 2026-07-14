# 可观测性实验第 2 部分：可观测性栈测验

> **最后更新**: February 22, 2026

测试你对可观测性端到端实验第 2 部分中所涵盖的可观测性栈概念的理解。

---

1. OpenTelemetry Collector 的 DaemonSet 和 Gateway 部署模式之间的关键区别是什么？
   - A) DaemonSet 模式已弃用，Gateway 是唯一推荐的方法
   - B) DaemonSet 在每个节点上运行一个 collector 以进行本地采集，而 Gateway 集中采集以进行跨节点处理
   - C) Gateway 模式无法处理 metrics，只能处理 traces
   - D) DaemonSet 模式需要集群之间更多的网络带宽

<details>
<summary>显示答案</summary>

**答案：B) DaemonSet 在每个节点上运行一个 collector 以进行本地采集，而 Gateway 集中采集以进行跨节点处理**

**说明：**
DaemonSet 模式会在每个节点上部署一个 OTel Collector Pod，以低延迟在本地采集 telemetry 并减少网络跳数。Gateway 模式使用集中式部署（Deployment 或 StatefulSet），接收来自所有来源的 telemetry，从而支持基于 tail 的 sampling 等跨节点处理。这两种模式通常会结合使用：DaemonSet collector 收集本地数据并转发到 Gateway，以便聚合并导出到后端。

</details>

---

2. OpenTelemetry Collector pipeline 架构如何组织数据流？
   - A) Exporter → Processor → Receiver
   - B) Receiver → Processor → Exporter
   - C) Processor → Receiver → Exporter
   - D) 所有组件都并行运行，不存在顺序

<details>
<summary>显示答案</summary>

**答案：B) Receiver → Processor → Exporter**

**说明：**
OTel Collector pipeline 遵循清晰的数据流：Receiver 从各种来源（OTLP、Prometheus、Jaeger 等）摄取 telemetry 数据，Processor 转换、筛选或丰富数据（batching、attribute 操作、sampling），Exporter 将处理后的数据发送到后端（Prometheus、Jaeger、云服务）。可以针对不同的信号类型（metrics、traces、logs）定义多个 pipeline，它们还可以共享组件。

</details>

---

3. 将 Prometheus remote write 配置为写入 Amazon Managed Prometheus (AMP) 时，认证如何工作？
   - A) 将用户名和密码存储在 Kubernetes secrets 中
   - B) IRSA 提供 IAM 凭证，SigV4 extension 使用 AWS Signature Version 4 对请求进行签名
   - C) 在 AMP 控制台中生成 API keys
   - D) 使用 AWS Certificate Manager 签发的 mTLS certificates

<details>
<summary>显示答案</summary>

**答案：B) IRSA 提供 IAM 凭证，SigV4 extension 使用 AWS Signature Version 4 对请求进行签名**

**说明：**
AMP 使用 AWS IAM 进行认证。remote write 组件（Prometheus、OTel Collector 或 Grafana Agent）使用 IRSA 获取临时 IAM 凭证。SigV4（AWS Signature Version 4）extension 或 proxy 使用这些凭证为每个请求签名。该方法利用 AWS 的身份基础设施，无需管理长期凭证，并通过 CloudTrail 提供审计跟踪。

</details>

---

4. VictoriaMetrics 如何与 Prometheus 兼容？
   - A) 它需要数据迁移工具来导入 Prometheus 数据
   - B) 它实现了 Prometheus remote write/read API，并支持使用 PromQL 进行查询
   - C) 它只能作为 Prometheus sidecar 工作
   - D) 兼容性需要付费的企业许可证

<details>
<summary>显示答案</summary>

**答案：B) 它实现了 Prometheus remote write/read API，并支持使用 PromQL 进行查询**

**说明：**
VictoriaMetrics 被设计为 Prometheus storage 的即插即用替代品。它实现了 Prometheus remote write 和 remote read API，允许任何与 Prometheus 兼容的 client 发送 metrics，并允许任何与 PromQL 兼容的工具查询这些 metrics。它使用 MetricsQL 扩展 PromQL 以提供额外函数。这种兼容性意味着现有的 Grafana dashboards、alerting rules 和 recording rules 无需修改即可工作。

</details>

---

5. Grafana Mimir 的 single binary 模式有什么特点？
   - A) 它仅支持 single-tenant 部署
   - B) 所有 Mimir 组件（ingester、querier、compactor 等）在单个进程中运行，以简化部署
   - C) 它无法进行水平扩缩容
   - D) single binary 模式会禁用长期 storage

<details>
<summary>显示答案</summary>

**答案：B) 所有 Mimir 组件（ingester、querier、compactor 等）在单个进程中运行，以简化部署**

**说明：**
Mimir 的 single binary 模式（monolithic mode）会在单个进程中运行所有组件——distributor、ingester、querier、query-frontend、compactor、store-gateway 和 ruler。这为较小的环境简化了部署和运维。尽管在一个进程中运行，它仍然可以通过运行多个 replicas 来进行水平扩缩容。对于较大的部署，可以将组件拆分为 microservices 模式以进行独立扩缩容。

</details>

---

6. Grafana Loki 的 SimpleScalable 部署模式包含哪些组件？
   - A) 仅一个 read-write Pod
   - B) 可独立扩缩容的独立 read、write 和 backend 组件
   - C) 仅有 Ingester 和 querier，使用外部 compactor
   - D) 具有自动 sharding 的 monolithic 模式

<details>
<summary>显示答案</summary>

**答案：B) 可独立扩缩容的独立 read、write 和 backend 组件**

**说明：**
Loki 的 SimpleScalable 模式（也称为 Simple Scalable Deployment 或 SSD）将组件分为三个 target：Write（distributor、ingester）、Read（query-frontend、querier）和 Backend（compactor、index-gateway、ruler）。这允许独立扩缩容——write path 根据摄取量扩缩容，read path 根据查询负载扩缩容。它位于 monolithic（single binary）和 microservices（完全分布式）模式之间，在运维简易性与可扩展性之间取得平衡。

</details>

---

7. 与传统方案相比，使用 ClickHouse 作为 log store 有哪些优势？
   - A) ClickHouse 仅支持结构化 JSON logs
   - B) 面向列的 storage、高压缩率，以及在大量 logs 上快速执行分析查询
   - C) 它需要更少的 storage，但查询性能更慢
   - D) ClickHouse 主要为 metrics 而非 logs 设计

<details>
<summary>显示答案</summary>

**答案：B) 面向列的 storage、高压缩率，以及在大量 logs 上快速执行分析查询**

**说明：**
ClickHouse 是针对分析查询优化的面向列 OLAP database。对于 log storage，这意味着：由于列中相似的数据易于压缩，具有极佳的压缩比（通常比基于行的 stores 高 10 倍）；可在数十亿条 log entries 上执行极快的聚合查询；并且可在不读取整行的情况下高效筛选特定列。这些特性使其能够以较低成本存储高容量 logs，同时提供交互式查询性能。

</details>

---

8. FluentBit 和 Grafana Alloy 用于 log collection 时的关键区别是什么？
   - A) FluentBit 使用 Go 编写，而 Alloy 使用 C 编写
   - B) FluentBit 轻量且专注于 log forwarding，而 Alloy 是支持 metrics、logs、traces 和 profiles 的统一 telemetry collector
   - C) Alloy 仅支持 Grafana 后端，而 FluentBit 与供应商无关
   - D) 对于等效工作负载，FluentBit 比 Alloy 需要更多 memory

<details>
<summary>显示答案</summary>

**答案：B) FluentBit 轻量且专注于 log forwarding，而 Alloy 是支持 metrics、logs、traces 和 profiles 的统一 telemetry collector**

**说明：**
FluentBit 是使用 C 编写的轻量、高性能 log processor 和 forwarder，专为资源受限环境设计。Grafana Alloy（Grafana Agent 的演进版本）是一个统一的 observability collector，可处理所有 telemetry signals——metrics、logs、traces 和 profiles。Alloy 使用基于组件的配置模型，并与 Grafana 的生态系统紧密集成。对于最小资源占用的 log forwarding，选择 FluentBit；对于跨所有信号类型的统一采集，选择 Alloy。

</details>

---

9. 如何配置 Tempo-Loki TraceID derived field correlation？
   - A) correlation 自动完成，无需配置
   - B) 在 Loki data source 中配置一个 derived field，从 logs 中提取 TraceID，并使用 trace ID 链接到 Tempo
   - C) 在 Tempo 和 Loki 之间安装单独的 correlation service
   - D) TraceID correlation 仅适用于 Jaeger，不适用于 Tempo

<details>
<summary>显示答案</summary>

**答案：B) 在 Loki data source 中配置一个 derived field，从 logs 中提取 TraceID，并使用 trace ID 链接到 Tempo**

**说明：**
在 Grafana 的 Loki data source settings 中，需要配置 derived fields，使用 regex 从 log lines 中提取 trace IDs。derived field 指定指向 Tempo data source 的内部链接，并将提取出的 trace ID 用作变量。查看 logs 时，包含 trace IDs 的 log lines 旁会显示可点击链接，从而可以从 log entry 直接导航到 Tempo 中对应的 distributed trace。

</details>

---

10. 如何配置 Alertmanager 以将通知发送到 AWS SNS？
    - A) Alertmanager 原生支持 SNS，仅需 topic ARN
    - B) 配置具有 topic ARN、region 以及通过 IRSA 或 access keys 进行 IAM 认证的 SNS receiver
    - C) SNS 集成需要 webhook proxy service
    - D) Alertmanager 无法发送到 SNS；请改用 CloudWatch Alarms

<details>
<summary>显示答案</summary>

**答案：B) 配置具有 topic ARN、region 以及通过 IRSA 或 access keys 进行 IAM 认证的 SNS receiver**

**说明：**
Alertmanager 支持将 SNS 作为原生 receiver 类型。配置需要 SNS topic ARN、AWS region 和认证凭证。对于 EKS 部署，通过为 ServiceAccount 配置一个具有 `sns:Publish` 权限的 IAM role 来使用 IRSA。receiver 配置包含用于 AWS 认证的 `sigv4` settings。这可以将 alerts 直接发送到 SNS，随后 SNS 可以扇出到 email、SMS、Lambda、SQS 或其他 SNS subscribers。

</details>
