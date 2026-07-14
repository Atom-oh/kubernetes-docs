# 可观测性实验第 6 部分：分布式追踪分析测验

> **最后更新**: February 22, 2026

测试你对可观测性端到端实验第 6 部分中涵盖的分布式追踪分析概念的理解。

---

1. 用于 span 过滤的 TraceQL 基本语法结构是什么？
   - A) 带有 JOIN 子句的类 SQL SELECT 语句
   - B) 使用点表示法包含 span 属性过滤器的花括号，例如 `{ span.attribute = "value" }`
   - C) 基于 XML 的查询格式
   - D) 仅使用正则表达式

<details>
<summary>显示答案</summary>

**答案：B) 使用点表示法包含 span 属性过滤器的花括号，例如 `{ span.attribute = "value" }`**

**解释：**
TraceQL 使用基于管道的语法，并使用花括号表示 span 选择器。基本结构为：`{ spanset_filter }`，其中过滤器对属性使用点表示法。固有属性使用 `span.` 前缀（例如 `span.duration`、`span.status`），资源属性使用 `resource.` 前缀（例如 `resource.service.name`），span 属性则直接使用（例如 `http.status_code`）。过滤器支持 `=`、`!=`、`>`、`<`、`=~`（正则表达式）等运算符，并且可以使用 `&&` 和 `||` 组合。

</details>

---

2. TraceQL 查询 `{ span.http.status_code >= 500 }` 会返回什么？
   - A) 系统中的所有 trace
   - B) HTTP 响应状态码为 500 或更高的 span，表示服务器错误
   - C) 耗时超过 500 毫秒的 span
   - D) 最近的 500 个 span

<details>
<summary>显示答案</summary>

**答案：B) HTTP 响应状态码为 500 或更高的 span，表示服务器错误**

**解释：**
该查询根据 `http.status_code` 属性过滤 span，仅返回具有服务器错误状态码（500、502、503 等）的 span。这对于调查分布式系统中的错误情况很有用。该查询返回包含匹配 span 的完整 trace，并突出显示错误 span。你还可以使用额外的过滤器进一步缩小结果范围，例如 `{ span.http.status_code >= 500 && resource.service.name = "payment-service" }`，以聚焦于特定 Service。

</details>

---

3. 如何在 Tempo 的 Service Graph 中识别高错误率或高延迟的边？
   - A) 无论指标如何，边始终以相同方式显示
   - B) Service Graph 根据错误率和延迟，使用颜色编码或粗细来可视化边，从而突出有问题的 Service 间通信
   - C) 必须根据原始 span 手动计算边的指标
   - D) Service Graph 只显示 Service 名称，不显示指标

<details>
<summary>显示答案</summary>

**答案：B) Service Graph 根据错误率和延迟，使用颜色编码或粗细来可视化边，从而突出有问题的 Service 间通信**

**解释：**
Tempo 的 Service Graph（通过 metrics-generator 使用 span 数据生成）将 Service 显示为节点，将它们之间的通信显示为边。边附带以下指标：通过颜色显示错误率（红色表示高错误率）、通过颜色渐变或工具提示显示延迟、通过边的粗细显示请求率。此可视化可以快速识别有问题的依赖关系——如果从 Service A 到 Service B 的边是红色的，请调查该特定通信路径。单击边通常会显示详细指标以及指向相关 trace 的链接。

</details>

---

4. 如何使用 Span 时间线（瀑布图视图）识别瓶颈？
   - A) 瓶颈只能通过 span 名称识别
   - B) 查找相对于父 span 耗时异常长的 span、子 span 之间的大间隔，或可并行化的顺序操作
   - C) 瀑布图视图不显示时间信息
   - D) 瓶颈只能在 Service Graph 中看到

<details>
<summary>显示答案</summary>

**答案：B) 查找相对于父 span 耗时异常长的 span、子 span 之间的大间隔，或可并行化的顺序操作**

**解释：**
瀑布图视图显示具有时间信息的层级 span 关系。瓶颈指标包括：占据 trace 耗时大部分的长 span（例如，数据库查询占总时间的 80%）、表示等待时间的 span 间隔（网络延迟、队列延迟）、本可并行运行的顺序子 span，以及自身耗时较高的 span（未归因于子 span 的时间）。通过直观浏览瀑布图，你可以识别时间花在何处，并判断执行模式是否最优。

</details>

---

5. 如何配置用于关联的 Loki 到 Tempo TraceID 派生字段？
   - A) 无需配置；它是自动的
   - B) 在 Grafana 的 Loki 数据源设置中，添加一个派生字段，使用正则表达式从日志中提取 trace ID，并配置指向 Tempo 数据源的内部链接
   - C) 安装单独的插件以实现关联
   - D) 派生字段只能与外部 URL 一起使用

<details>
<summary>显示答案</summary>

**答案：B) 在 Grafana 的 Loki 数据源设置中，添加一个派生字段，使用正则表达式从日志中提取 trace ID，并配置指向 Tempo 数据源的内部链接**

**解释：**
配置步骤：在 Grafana 中，编辑 Loki 数据源并找到“Derived fields”。添加一个字段，包含：名称（例如“TraceID”）、用于匹配日志格式中 trace ID 的正则表达式（例如 `traceID=(\w+)` 或 `"trace_id":"([^"]+)"`）、启用的内部链接（指向你的 Tempo 数据源），以及使用正则表达式捕获组的查询（`${__value.raw}`）。查看日志时，提取出的 trace ID 会成为可点击的链接，以在 Tempo 的 Explore 视图中打开相应 trace。

</details>

---

6. Tempo 的 Span to Logs 功能支持什么？
   - A) 它会从 span 自动生成日志
   - B) 它允许根据时间范围及 Service 名称或 trace ID 等标签，从 trace 中的 span 直接跳转到 Loki 中关联的日志
   - C) 它完全用 span 替代日志
   - D) 它仅适用于 CloudWatch Logs

<details>
<summary>显示答案</summary>

**答案：B) 它允许根据时间范围及 Service 名称或 trace ID 等标签，从 trace 中的 span 直接跳转到 Loki 中关联的日志**

**解释：**
Tempo 的“Span to Logs”功能（在 Tempo 数据源设置中配置）会创建从 span 到 Loki 查询的链接。查看 trace 时，每个 span 都有一个“Logs”链接，该链接会使用 span 的时间窗口、Service 名称以及可选的 trace ID 构建 Loki 查询。这使你能够调查 Service 在 span 执行期间记录的内容——对于理解错误或调试意外行为极有价值。配置指定要从 span 属性映射哪些 Loki 标签。

</details>

---

7. exemplar 机制如何支持从指标深入查看 trace？
   - A) exemplar 会完全替代指标
   - B) exemplar 在记录时将 trace ID 附加到指标样本，从而可以从指标数据点直接跳转到一个具有代表性的 trace
   - C) exemplar 仅适用于计数器指标
   - D) 必须按时间戳手动关联指标和 trace

<details>
<summary>显示答案</summary>

**答案：B) exemplar 在记录时将 trace ID 附加到指标样本，从而可以从指标数据点直接跳转到一个具有代表性的 trace**

**解释：**
exemplar 是附加到指标观测值的元数据（包括 trace ID）。记录直方图或计数器时，应用程序会包含来自当前请求上下文的 trace ID。在 Grafana 中，指标可视化会将 exemplar 显示为图上的点。单击 exemplar 会显示其 trace ID，并提供指向追踪后端的链接。这支持强大的工作流：在仪表板中发现延迟峰值，单击该峰值上的 exemplar，立即查看一个具有代表性的 trace，了解该请求为何缓慢。

</details>

---

8. 在 RED 指标仪表板中，Rate、Errors 和 Duration 分别代表什么？
   - A) 节点的资源利用率指标
   - B) Rate 是每秒请求吞吐量，Errors 是失败请求的数量或百分比，Duration 是响应时间延迟（通常以百分位数表示）
   - C) 仅限数据库的指标
   - D) 网络带宽测量

<details>
<summary>显示答案</summary>

**答案：B) Rate 是每秒请求吞吐量，Errors 是失败请求的数量或百分比，Duration 是响应时间延迟（通常以百分位数表示）**

**解释：**
RED 是一种以 Service 为中心的监控方法：Rate 衡量吞吐量（请求/秒），回答“Service 正在处理多少流量？”；Errors 衡量失败率（错误数量或百分比），回答“Service 多久失败一次？”；Duration 衡量延迟分布（p50、p95、p99），回答“请求需要多长时间？”。这些指标结合起来，可全面呈现 Service 健康状况。如果 Rate 降低，说明某些因素正在阻塞请求；如果 Errors 激增，说明某些因素正在失败；如果 Duration 增加，说明某些因素变慢了。

</details>

---

9. 如何为 99.9% 可用性和低于 500ms 的 p99 延迟配置 SLI/SLO 仪表板仪表盘？
   - A) 这些指标无法在单个仪表板中显示
   - B) 创建仪表盘面板，使用 PromQL 查询计算当前 SLI 值，并配置相对于 SLO 目标显示绿色/黄色/红色区域的阈值
   - C) SLI/SLO 仪表板需要商业 Grafana 许可证
   - D) 使用手动输入值的静态文本面板

<details>
<summary>显示答案</summary>

**答案：B) 创建仪表盘面板，使用 PromQL 查询计算当前 SLI 值，并配置相对于 SLO 目标显示绿色/黄色/红色区域的阈值**

**解释：**
对于可用性 SLI：查询 `sum(rate(requests_total{status!~"5.."}[30d])) / sum(rate(requests_total[30d])) * 100`，显示当前可用性百分比及阈值（绿色 >= 99.9%、黄色 >= 99.5%、红色 < 99.5%）。对于 p99 延迟：查询 `histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[5m])) by (le)) * 1000`（单位为 ms），并设置阈值（绿色 <= 500ms、黄色 <= 750ms、红色 > 750ms）。添加错误预算面板，根据 SLO 目标和当前消耗率显示剩余预算。

</details>

---

10. 像 `db.system` 和 `db.statement` 这样的数据库查询 span 属性在分布式追踪中有什么作用？
    - A) 它们仅用于数据库连接池
    - B) 它们识别数据库类型并捕获实际查询，从而能够在 trace 中识别慢查询、N+1 问题和与数据库相关的瓶颈
    - C) 这些属性在 OpenTelemetry 中已弃用
    - D) 它们仅适用于 SQL 数据库，不适用于 NoSQL

<details>
<summary>显示答案</summary>

**答案：B) 它们识别数据库类型并捕获实际查询，从而能够在 trace 中识别慢查询、N+1 问题和与数据库相关的瓶颈**

**解释：**
OpenTelemetry 语义约定定义了标准数据库 span 属性：`db.system` 标识数据库类型（postgresql、mysql、redis、mongodb），`db.statement` 包含查询文本（为安全起见会进行清理），`db.operation` 显示操作类型（SELECT、INSERT），`db.name` 表示数据库名称。这些属性支持：按数据库类型过滤 trace、在瀑布图视图中识别慢查询、检测 N+1 查询模式（许多相似的顺序查询），以及将数据库 span 与整体请求延迟相关联。这种可观测性对于性能优化至关重要。

</details>
