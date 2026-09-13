# 第 6 部分：分布式追踪分析

<span id="cleanup-steps-table"></span>
<span id="drill-down-analysis-workflow"></span>
<span id="exercise-1-traceql-trace-search"></span>
<span id="exercise-2-service-graph-visualization"></span>
<span id="exercise-3-latency-identification-workflow"></span>
<span id="exercise-4-loki-tempo-correlation"></span>
<span id="exercise-5-exemplar-usage"></span>
<span id="exercise-6-comprehensive-dashboard-setup"></span>
<span id="final-verification-checklist"></span>
<span id="full-cleanup-script"></span>
<span id="key-takeaways"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="traceql-query-reference"></span>
<span id="verification"></span>

> **难度**：高级 · **预计时间**：45 分钟
> **最后更新**：September 13, 2026

从指标出发，经由 exemplar 追踪到其 trace 和日志，跟踪一个真实请求，并将观察结果与因果假设区分开来。这需要 [第 2 部分](./02-observability-stack-lab.md) 的数据摄取路径以及 [第 3 部分](./03-msa-deployment-lab.md) 的上下文传播。本节中的 TraceQL 已通过实际 Tempo **3.0.3** 解析器验证，并使用当前 OTel 属性。

![通过其 trace 和日志调查指标](../../.gitbook/assets/en-labs-observability-06-distributed-tracing-lab-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-06-distributed-tracing-lab-0.html)

## 1. TraceQL 搜索 {#traceql}

```traceql
{ resource.service.name = "order-service" && span:duration > 1s }

{ trace:duration > 2s && resource.service.name = "order-service" }

{ span:kind = server && span.http.response.status_code >= 500 }

{ span.db.system.name = "postgresql" && span:duration > 100ms }

{ span.messaging.system = "aws_sqs" && span.messaging.operation.type = "send" }

{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }

{ resource.service.name = "order-service" } >> { span.db.system.name = "postgresql" }

{ span:status = error } | select(resource.service.name, span.http.response.status_code, span:duration)
```

`span:duration` 测量单个 span；`trace:duration` 测量整个 trace。对显式内部属性使用 `span:`，对属性使用 `span.`/`resource.`。`>>` 查找从左侧 span 向下派生的右侧 span。搜索 DB span 的后代不同于查找某个 Service 下的 DB 工作。

`sort(duration)`、SQL `order by`、`| limit 20` 和 `{ duration > p99 }` 不属于此搜索语法。请在 Grafana 中配置结果排序、搜索限制和时间范围，并以持续时间字面量（例如 `800ms`）替换测得的 p99。`select()` 请求显示属性；它无法重建从未存储过的 span。

较旧的 SDK 可能会发出 `http.status_code`、`http.method`、`db.system`、`db.statement` 或 `messaging.operation`。在使用当前的 `http.response.status_code`、`http.request.method`、`db.system.name`、`db.query.text` 或 `messaging.operation.type` 前，请检查实际 span 和 SDK 版本。重命名查询属性并不会转换已采集的数据。仅在明确的数据脱敏策略下采集查询文本；应排除密码、SQL 字面量和客户数据。

## 2. Service graph 前提条件 {#service-graph}

仅在 Tempo 中接收 trace 并不能完成 Grafana Service graph。启用 metrics-generator 的 service-graphs processor，将其指标交付给真实的指标后端，并将 Grafana Tempo datasource 的 serviceMap UID 链接到该后端。客户端/服务端或生产者/消费者 span 必须共享上下文。采样、缺失的 span 和错误的 span kind 都会影响生成的边。

```promql
sum by (client, server) (rate(traces_service_graph_request_total[5m]))

(
  sum by (client, server) (rate(traces_service_graph_request_failed_total[5m]))
  or on (client, server)
  (0 * sum by (client, server) (rate(traces_service_graph_request_total[5m])))
)
/ on (client, server)
(sum by (client, server) (rate(traces_service_graph_request_total[5m])) > 0)

sum by (client, server) (rate(traces_service_graph_request_server_seconds_sum[5m]))
/
sum by (client, server) (rate(traces_service_graph_request_server_seconds_count[5m]))
```

在首次失败发生前，失败计数器可能没有任何序列。使用匹配的请求总数序列将其缺失的分子填充为零，然后要求分母为正值，以便将健康的 0% 与无流量或数据摄取缺失区分开来。

最后一个查询测量服务端平均持续时间。客户端持续时间使用 `traces_service_graph_request_client_seconds_*`；不要查询不存在的 `traces_service_graph_request_duration_seconds_*` 指标族。将零流量时间区间视为缺失证据。颜色和边宽取决于 Grafana/dashboard 设置；应检查请求/错误/持续时间值，而不要假定固定的 1%/5% 颜色规则。

## 3. 根据瀑布图形成瓶颈假设 {#waterfall}

| 观察结果 | 后续操作 |
|---|---|
| DB span 缓慢 | 检查查询计划、锁、连接池和 DB 指标 |
| 客户端 span 很长 | 比较 DNS/TLS/网络/服务端等待/重试时间区间 |
| 父 span 与子 span 之间存在间隙 | 检查未埋点的工作、队列、GC 和调度 |
| 并行的子 span | 分析重叠和关键路径，而不是累加持续时间 |
| 消息延迟 | 将发送/接收/处理持续时间与队列等待和重新投递区分开来 |

父级持续时间包含子级持续时间；累加所有 span 会重复计算时间。仅凭一个 1.8 秒的 DB span 并不能证明缺少索引。在接受某个假设之前，请在相同的发布版本、流量和时间范围内比较日志和指标。

## 4. 链接日志和 trace {#correlation}

```logql
{service_name="order-service"} | json | level="ERROR"

{service_name="order-service"} | json | trace_id="0123456789abcdef0123456789abcdef"
```

这些查询假定存在实际的 `service_name` 流标签和 JSON `trace_id` 字段。请将这个 32 字符的示例 trace ID 替换为真实请求 ID。`traceID`、`traceId` 和 `trace_id` 是不同的字段。将 trace ID 保留在日志字段/结构化元数据中，而不是作为唯一的流标签。在 Grafana/HTTP 参数中设置时间边界；不要将 `timestamp >= 2025-...` 附加到 LogQL。

Loki derived field 会提取 trace ID，并链接到 Tempo datasource UID。在 Grafana provisioning YAML 中，将内部链接表达式转义为 `$${__value.raw}`。双引号正则表达式和宽泛的 shell envsubst 可能会更改反斜杠或 Grafana 变量；请使用适当的单引号和范围受限的替换。

使用 Loki UID、实际的资源到日志标签映射、时间填充和 trace-ID 过滤配置 Tempo `tracesToLogsV2`。点击“Logs for this span”后，检查生成的 LogQL。链接的存在和成功检索同一请求是两项独立检查。

## 5. Exemplar 的含义和验证 {#exemplars}

![跟踪一个代表性 exemplar 到其 trace 和日志](../../.gitbook/assets/en-labs-observability-06-distributed-tracing-lab-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-06-distributed-tracing-lab-1.html)

exemplar 是附加到聚合数据上的**代表性观测**。点击 p99 图上的一个点并不能证明该请求确定了精确的百分位边界。exemplar 的生成、exporter/remote-write 保留、Prometheus 存储和 Grafana datasource 链接都必须正常工作。采样或保留策略可能留下 trace 不可用的 exemplar ID。

检查实际 Prometheus exemplar API 结果，并使用返回的 `trace_id` 查询 Tempo。启用 Grafana 显示选项或搜索不存在的 Prometheus ConfigMap 并不是数据摄取验证。请根据已安装的 Prometheus/chart 版本以及渲染后的 Prometheus 资源/运行时参数确认 exemplar-storage 设置。

## 6. RED 和 SLI/SLO dashboard {#slo}

根据实际指标名称、标签和 histogram 单位构建 RED 面板。在相同的 Service/route 范围内比较请求速率、失败率和持续时间分布。计算可用性之前，先定义合格请求和成功的含义；说明如何处理 4xx 响应、健康检查和重试。

30 天 SLO 需要在该期间内保留真实数据并获得真实观测结果。新建实验中的 `[30d]` 查询并不会产生 30 天的证据。处理无流量、缺失序列和计数器重置；披露低流量百分位数的限制。使用同一时间窗口内允许的失败数和观测到的失败数计算错误预算。记录周期、分母和值，而不是声称固定的“已达成 99.9%”。

## 7. 验证流程，然后清理 {#cleanup}

清理前，记录一个其 exemplar ID、Tempo trace ID 和日志 trace ID 均匹配的请求；验证实际 Service graph 依赖关系和告警投递。保留测量值、时间戳和配置版本，而不是用估算值填充结果。

| 顺序 | 操作和完成条件 |
|---|---|
| 1 | 停止 k6/Locust、故障注入和 AI 分析触发器；保存结果 |
| 2 | 停止 GitOps ApplicationSet/父级重建，并级联删除实际的应用程序 |
| 3 | 移除 Service-cluster LoadBalancers/Ingresses、workload 和 PVC；验证外部 LB/volume 清理 |
| 4 | 在使用实际 release/namespace 名称卸载其 operator 之前，删除 telemetry custom resource |
| 5 | 在移除 controller 之前，drain/delete Karpenter NodeClaims；在依赖项存在时保留 API/LB/storage controller |
| 6 | 使用相同的 IaC state 审查 destroy plan；对手动创建的 AWS 资源使用记录的精确 ID/ARN |
| 7 | 在依赖项清理后删除 EKS/VPC，然后验证 managed-service 删除和残留资源 |

不要删除共享 namespace 或集群范围的 CRD。请使用记录的安装 release/namespace/version，而不是使用 `latest` 安装器 URL。版本控制的 S3 除当前对象外，还需要检查旧版本和删除标记。根据资源清单核对 Aurora snapshot policy、MWAA/DAG bucket、AMG、AMP、OpenSearch、SNS/SQS/DLQ、Lambda/API Gateway、IAM attachment、EBS/LB、log group 和 alarm。已接受的删除请求并不等于删除已完成。

审查资源所有权并保留证据/state，而不是使用未经检查且自动批准的 destroy、抑制所有错误，或删除整个工作目录。

## 验证范围和参考资料

当前 Tempo 解析器验证了 12 个被接受的查询，并拒绝了之前三个错误查询。一个临时本地 Loki 3.7.7 接收了两条合成日志行；两个 LogQL 查询均检索到了完全符合预期的 trace ID。实际 Service Tempo 搜索、Loki 收集、Grafana 数据链接和云资源删除均未执行。

- [TraceQL](https://grafana.com/docs/tempo/latest/traceql/)
- [Service graph 指标](https://grafana.com/docs/tempo/latest/metrics-from-traces/service_graphs/)
- [OTel HTTP span](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- [OTel database span](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [Loki derived fields](https://grafana.com/docs/grafana/latest/datasources/loki/configure-loki-data-source/)
- [Tempo 指南](../../observability/tracing/01-tempo.md)
- [Loki 指南](../../observability/logging/01-loki.md)
- [系列索引](./README.md)
