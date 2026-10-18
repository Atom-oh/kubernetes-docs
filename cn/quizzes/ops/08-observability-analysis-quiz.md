# 可观测性分析测验

> **相关文档**: [可观测性分析](../../ops/08-observability-analysis.md)

## 选择题

### 1. 分布式追踪中的 Trace ID 是什么？

- A) 单个 span 的唯一标识符
- B) 用于关联一次请求在各服务中产生的所有 span 的唯一标识符
- C) 服务名称
- D) 时间戳

<details>
<summary>显示答案</summary>

**答案：B) 用于关联一次请求在各服务中产生的所有 span 的唯一标识符**

**解释：**
服务会继续使用有效的入站 trace context，或创建新的 trace。参与其中的 span 可以共享其 Trace ID；异步设计也可以启动新的 trace，并通过 span link 与其他 trace 关联。这样就能关联处理同一请求的不同服务所产生的日志、span 和指标。

</details>

### 2. 在特定 namespace 中查找错误日志，正确的 LogQL 查询是什么？

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>显示答案</summary>

**答案：B) `{namespace="production"} |= "error"`**

**解释：**
LogQL 使用大括号中的标签选择器，后接过滤表达式。`{namespace="production"}` 选择该 namespace 中的日志，`|= "error"` 则筛选包含 "error" 的日志行。`|=` 运算符执行区分大小写的子字符串匹配。

</details>

### 3. RED 方法衡量什么？

- A) 资源使用、事件、持续时间
- B) 服务的速率、错误和持续时间
- C) 请求、端点、数据
- D) 副本数、端点、部署

<details>
<summary>显示答案</summary>

**答案：B) 服务的速率、错误和持续时间**

**解释：**
RED 方法通过速率（每秒请求数）、错误（失败请求率）和持续时间（延迟分布）衡量服务健康状况。它适用于请求驱动型服务，并可补充面向资源的 USE 方法。

</details>

### 4. USE 方法衡量什么？

- A) 用户、会话、事件
- B) 资源的利用率、饱和度和错误
- C) 上传、存储、加密
- D) 单位、规模、效率

<details>
<summary>显示答案</summary>

**答案：B) 资源的利用率、饱和度和错误**

**解释：**
USE 方法通过利用率（繁忙百分比）、饱和度（队列深度或等待情况）和错误（错误计数）衡量资源健康状况。它适用于分析 CPU、内存、网络和存储资源。

</details>

### 5. Prometheus 中的 Exemplars 是什么？

- A) 示例配置文件
- B) 附加到指标样本的 Trace ID，可实现指标到 trace 的关联
- C) 示例 Prometheus 查询
- D) 模板仪表板

<details>
<summary>显示答案</summary>

**答案：B) 附加到指标样本的 Trace ID，可实现指标到 trace 的关联**

**解释：**
Exemplar 会将上下文标签（通常包含 trace ID）附加到选定的指标观测值上。在 Grafana 中查看直方图或计数器时，已配置的 exemplar 链接可以打开对应且仍保留的 trace。Exemplar 不保证每次观测都有追踪，也不能指出确切的 P99 请求。

</details>

### 6. 哪个 PromQL 函数可从直方图计算第 95 百分位延迟？

- A) `avg()`
- B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- C) `max()`
- D) `percentile(95, latency)`

<details>
<summary>显示答案</summary>

**答案：B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`**

**解释：**
`histogram_quantile()` 根据直方图 bucket 计数计算分位数。第一个参数 0.95 表示百分位；函数作用于 `_bucket` 指标的速率，并根据 bucket 边界估算相应分位数。合并多个实例时，应聚合速率，同时保留 le 以及预期的服务和集群标签；对于缺失流量或零流量，应另行处理。

</details>

### 7. TraceQL 用于什么？

- A) 编写 Prometheus 告警
- B) 在 Grafana Tempo 中查询分布式 trace
- C) 创建日志聚合规则
- D) 定义 service mesh 策略

<details>
<summary>显示答案</summary>

**答案：B) 在 Grafana Tempo 中查询分布式 trace**

**解释：**
TraceQL 是 Tempo 用于搜索 trace 的查询语言。它支持按服务名称、span 名称、持续时间、属性和状态筛选。例如：`{resource.service.name="api-gateway" && duration>1s}` 可查找耗时较长的 API gateway trace。

</details>

### 8. 如何在 LogQL 中提取 JSON 字段？

- A) `json.fieldname`
- B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>
- C) `SELECT fieldname FROM logs`
- D) `logs.fieldname`

<details>
<summary>显示答案</summary>

**答案：B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>**

**解释：**
`| json` 解析器会将日志行中的 JSON 字段提取为标签。之后可以格式化输出，或筛选已提取的字段。应使用 __error__ 过滤器检查解析和转换错误，尤其是在指标聚合之前以及执行 unwrap 之后。

</details>

### 9. 在 Grafana 中，如何实现日志与 trace 的关联？

- A) 手动复制粘贴 ID
- B) 在日志字段中包含 trace_id，并配置 Loki 数据源的 derived fields
- C) 使用同一个仪表板
- D) 安装单独的插件

<details>
<summary>显示答案</summary>

**答案：B) 在日志字段中包含 trace_id，并配置 Loki 数据源的 derived fields**

**解释：**
应用程序必须在日志中输出 trace ID。在 Grafana 中，配置 Loki 的 derived fields 识别 trace_id 字段并链接到 Tempo。这样便能从日志行直接点击跳转到关联的 trace。

</details>

### 10. 分布式追踪中的 span 属性有什么作用？

- A) 设置追踪可视化样式
- B) 附加有界的上下文元数据，例如路由和操作
- C) 加密追踪数据
- D) 压缩追踪存储

<details>
<summary>显示答案</summary>

**答案：B) 附加有界的上下文元数据，例如路由和操作**

**解释：**
span 属性用于添加上下文，例如 http.route 或示例中的 app.operation。查询应符合实际采用的语义约定 schema。应限制基数，避免不加区分地记录凭证、原始请求正文或敏感数据库语句。

</details>
