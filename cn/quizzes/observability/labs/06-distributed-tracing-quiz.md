# 可观测性实验第 6 部分测验

> **最后更新**: September 13, 2026

1. 如何区分整条 trace（链路）的耗时与单个 span 的耗时？
   - A) 两者始终完全相同。
   - B) trace:duration 与 span:duration。
   - C) span.duration 始终是内置字段。
   - D) 统计日志行数。

<details>
<summary>显示答案</summary>

**答案: B) trace:duration 与 span:duration。**

显式的内置字段（intrinsics）使用冒号；span. 是属性作用域。

</details>

---

2. 哪个查询使用了当前的 HTTP 响应状态属性？
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>显示答案</summary>

**答案: B) { span.http.response.status_code >= 500 }**

如果某个 SDK 仍然发出 http.status_code，请检查其数据并使用相应的旧版查询。

</details>

---

3. A >> B 会筛选出什么？
   - A) A 之前的所有日志。
   - B) 作为 A span 后代的 B span。
   - C) A 与 B 的平均值。
   - D) B 必然与 A 是同一个 span。

<details>
<summary>显示答案</summary>

**答案: B) 作为 A span 后代的 B span。**

将服务选择器放在左侧、数据库选择器放在右侧，即可找到作为后代的数据库操作。

</details>

---

4. 旧示例中 SQL 风格的 order by/limit 应如何替换？
   - A) 原样运行。
   - B) 使用有效的 TraceQL，配合 Grafana 搜索的排序/条数限制设置。
   - C) 把它发送给 Prometheus。
   - D) 在查询中加入数据库密码。

<details>
<summary>显示答案</summary>

**答案: B) 使用有效的 TraceQL，配合 Grafana 搜索的排序/条数限制设置。**

实际的 Tempo3.0.3 解析器会拒绝那些旧的 sort/order-by/limit 示例。

</details>

---

5. 服务拓扑图（service graph）需要什么？
   - A) 只需安装 Tempo。
   - B) 相互关联的 span、service-graphs 处理器、指标后端以及数据源关联配置。
   - C) 只需把 trace ID 存为日志标签。
   - D) 手动绘制红色节点。

<details>
<summary>显示答案</summary>

**答案: B) 相互关联的 span、service-graphs 处理器、指标后端以及数据源关联配置。**

请分别验证 trace 的采集写入与拓扑图指标的投递。

</details>

---

6. 一个耗时 1.8 秒的数据库 span 本身能说明什么？
   - A) 一定缺少索引。
   - B) 该操作被观测到的耗时；其原因还需进一步证据。
   - C) 网络状况良好。
   - D) 可以放心地把它与所有父 span 的耗时相加。

<details>
<summary>显示答案</summary>

**答案: B) 该操作被观测到的耗时；其原因还需进一步证据。**

检查锁、连接池、网络和查询计划；避免对相互重叠的 span 重复计数。

</details>

---

7. 在 Grafana provisioning 中，派生字段（derived field）的链接表达式应如何书写？
   - A) 用 envsubst 移除所有美元符号变量。
   - B) 使用 $${__value.raw} 转义 provisioning 的变量替换。
   - C) 为每个流标签都加上 trace ID。
   - D) 以 LogQL SQL 子句的形式添加时间范围。

<details>
<summary>显示答案</summary>

**答案: B) 使用 $${__value.raw} 转义 provisioning 的变量替换。**

实际的 trace ID 字段名和数据源 UID 也必须匹配。

</details>

---

8. exemplar（样本点）会指向什么请求？
   - A) 必然是恰好处于 p99 边界的那个请求。
   - B) 一次具有代表性的观测，其对应的 trace 仍必须被保留。
   - C) 每个请求的副本。
   - D) 无论 trace 采样如何都始终可检索。

<details>
<summary>显示答案</summary>

**答案: B) 一次具有代表性的观测，其对应的 trace 仍必须被保留。**

采样与保留策略可能导致 exemplar 中的 ID 与实际可用的 trace 不一致。

</details>

---

9. 在实验的第一天执行 [30d] 查询能证明什么？
   - A) 满足了 30 天的 SLO。
   - B) 它聚合的是已有的观测数据；并不会创造出 30 天的历史数据。
   - C) 100% 可用性。
   - D) 无限的错误预算。

<details>
<summary>显示答案</summary>

**答案: B) 它聚合的是已有的观测数据；并不会创造出 30 天的历史数据。**

请记录实际的时间范围、分母，以及缺失数据/无流量的时间区间。

</details>

---

10. 关于当前数据库属性与数据处理方式的组合，哪一项是正确的？
   - A) db.statement 永久是唯一的标准。
   - B) 针对实际使用的 SDK 检查 db.system.name/db.query.text，并对查询做脱敏处理。
   - C) 记录所有密码。
   - D) 重命名查询会转换所有旧数据。

<details>
<summary>显示答案</summary>

**答案: B) 针对实际使用的 SDK 检查 db.system.name/db.query.text，并对查询做脱敏处理。**

数据中可能仍保留旧版属性；迁移与敏感数据处理是两件独立的事情。

</details>

---

[返回指南](../../../labs/observability/06-distributed-tracing-lab.md)