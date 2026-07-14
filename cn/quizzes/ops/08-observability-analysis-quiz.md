# 可观测性分析测验

> **相关文档**: [可观测性分析](../../ops/08-observability-analysis.md)

## 选择题

### 1. 在分布式追踪中，Trace ID 是什么？

- A) 单个 span 的唯一标识符
- B) 一个唯一标识符，用于关联跨服务请求中的所有 span
- C) 服务的名称
- D) 时间戳

<details>
<summary>显示答案</summary>

**答案: B) 一个唯一标识符，用于关联跨服务请求中的所有 span**

**解析:**
Trace ID 是请求进入系统时分配的唯一标识符，并会在所有下游服务调用中传播。它可以将处理同一请求的不同服务中的日志、span 和指标关联起来。

</details>

### 2. 用于在特定 namespace 中查找错误日志的正确 LogQL 查询是什么？

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>显示答案</summary>

**答案: B) `{namespace="production"} |= "error"`**

**解析:**
LogQL 使用大括号中的标签选择器，后跟过滤表达式。`{namespace="production"}` 选择该 namespace 中的日志，`|= "error"` 过滤包含 "error" 的行。`|=` 运算符执行区分大小写的子字符串匹配。

</details>

### 3. RED 方法衡量什么？

- A) Resource usage、Events、Duration
- B) Rate、Errors、Duration（用于服务）
- C) Requests、Endpoints、Data
- D) Replicas、Endpoints、Deployments

<details>
<summary>显示答案</summary>

**答案: B) Rate、Errors、Duration（用于服务）**

**解析:**
RED 方法通过 Rate（每秒请求数）、Errors（失败请求率）和 Duration（延迟分布）来衡量服务健康状况。它针对请求驱动型服务进行了优化，并补充了面向资源的 USE 方法。

</details>

### 4. USE 方法衡量什么？

- A) User、Session、Events
- B) Utilization、Saturation、Errors（用于资源）
- C) Upload、Storage、Encryption
- D) Units、Scale、Efficiency

<details>
<summary>显示答案</summary>

**答案: B) Utilization、Saturation、Errors（用于资源）**

**解析:**
USE 方法通过 Utilization（使用率/繁忙百分比）、Saturation（队列深度/等待情况）和 Errors（错误计数）来衡量资源健康状况。它设计用于分析 CPU、内存、网络和存储资源。

</details>

### 5. Prometheus 中的 Exemplars 是什么？

- A) 示例配置文件
- B) 附加到指标样本上的 Trace ID，用于实现指标到追踪的关联
- C) 示例 Prometheus 查询
- D) 模板仪表板

<details>
<summary>显示答案</summary>

**答案: B) 附加到指标样本上的 Trace ID，用于实现指标到追踪的关联**

**解析:**
Exemplars 是在特定时间点与指标样本一起存储的 Trace ID。在 Grafana 中查看直方图或计数器时，exemplars 让你可以直接点击进入生成特定指标数据点的 trace。

</details>

### 6. 哪个 PromQL 函数用于从直方图计算第 95 百分位延迟？

- A) `avg()`
- B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- C) `max()`
- D) `percentile(95, latency)`

<details>
<summary>显示答案</summary>

**答案: B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`**

**解析:**
`histogram_quantile()` 根据直方图 bucket 计数计算分位数。第一个参数 (0.95) 是百分位，它作用于 `_bucket` 指标的 rate。这会给出 95% 的请求完成时低于该值的延迟。

</details>

### 7. TraceQL 用于什么？

- A) 编写 Prometheus 告警
- B) 在 Grafana Tempo 中查询分布式 trace
- C) 创建日志聚合规则
- D) 定义 service mesh 策略

<details>
<summary>显示答案</summary>

**答案: B) 在 Grafana Tempo 中查询分布式 trace**

**解析:**
TraceQL 是 Tempo 用于搜索 trace 的查询语言。它支持按服务名称、span 名称、持续时间、属性和状态进行过滤。例如：`{resource.service.name="api-gateway" && duration>1s}` 可以查找较慢的 API gateway trace。

</details>

### 8. 如何在 LogQL 中提取 JSON 字段？

- A) `json.fieldname`
- B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>
- C) `SELECT fieldname FROM logs`
- D) `logs.fieldname`

<details>
<summary>显示答案</summary>

**答案: B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>**

**解析:**
`| json` 解析器会从日志行中提取 JSON 字段并转换为标签。然后你可以使用带有 Go 模板语法的 `| line_format` 来格式化输出，或使用提取的字段进行过滤，例如 `| status_code >= 500`。

</details>

### 9. 在 Grafana 中，是什么实现了日志和 trace 之间的关联？

- A) 手动复制粘贴 ID
- B) 在日志字段中包含 trace_id，并在 Loki 数据源中配置 derived fields
- C) 使用同一个仪表板
- D) 安装单独的插件

<details>
<summary>显示答案</summary>

**答案: B) 在日志字段中包含 trace_id，并在 Loki 数据源中配置 derived fields**

**解析:**
应用程序必须在日志中输出 Trace ID。在 Grafana 中，你需要配置 Loki 的 derived fields 来识别 trace_id 字段并链接到 Tempo。这会创建从日志行直接跳转到相关 trace 的可点击链接。

</details>

### 10. 分布式追踪中 span 属性的目的是什么？

- A) 设置 trace 可视化的样式
- B) 将上下文元数据（用户 ID、请求参数）附加到 span
- C) 加密 trace 数据
- D) 压缩 trace 存储

<details>
<summary>显示答案</summary>

**答案: B) 将上下文元数据（用户 ID、请求参数）附加到 span**

**解析:**
Span 属性是为 span 添加上下文的键值对，例如 `http.method`、`http.status_code`、`user.id` 或 `db.statement`。它们支持按业务上下文过滤 trace，并帮助识别哪些请求存在问题。

</details>
