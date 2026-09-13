# ClickHouse 日志分析测验

> **最后更新**: September 13, 2026

1. 为什么列式存储有助于分析型日志查询？

   - A) 它始终扫描每个字段
   - B) 它可以读取选定的列并压缩重复值
   - C) 它保证固定的压缩比
   - D) 它无需进行 schema 设计

<details>
<summary>显示答案</summary>

**答案：B) 它可以读取选定的列并压缩重复值**

收益取决于数据、排序键和查询。该指南并未承诺 10:1 的压缩比或固定吞吐量。

</details>

---

2. Keeper/ZooKeeper 在此设计中扮演什么角色？

   - A) 运行每个分布式 SELECT
   - B) 存储每一行日志
   - C) 协调复制表和分布式 DDL
   - D) 替代采集器

<details>
<summary>显示答案</summary>

**答案：C) 协调复制表和分布式 DDL**

ClickHouse 查询发起方和 Distributed 表执行分布式查询。Keeper 不是它们的查询路由器。

</details>

---

3. 哪种 engine 为 MergeTree 存储添加复制功能？

   - A) ReplicatedMergeTree
   - B) Memory
   - C) Buffer
   - D) 仅使用 Distributed

<details>
<summary>显示答案</summary>

**答案：A) ReplicatedMergeTree**

副本仍需要协调、独立的持久化存储以及适当的故障域设计。仅靠复制并不能无条件保证 HA。

</details>

---

4. 对于重复的 namespace 或 severity 值，哪种类型值得评估？

   - A) 始终使用 FixedString(255)
   - B) LowCardinality(String)
   - C) 为每条日志消息使用唯一整数
   - D) 仅使用未压缩的 String

<details>
<summary>显示答案</summary>

**答案：B) LowCardinality(String)**

字典编码有助于处理重复值；应对字典大小和查询行为进行基准测试，而非假设存在通用的不同值数量阈值。

</details>

---

5. 应如何选择日志表的 ORDER BY？

   - A) 按字母顺序
   - B) 按字段创建时间
   - C) 根据选择性过滤条件、局部性和代表性查询
   - D) 无论查询如何，始终将 timestamp 放在最后

<details>
<summary>显示答案</summary>

**答案：C) 根据选择性过滤条件、局部性和代表性查询**

该键会影响排序和索引剪枝。仅凭经常查询的列无法确定最佳顺序。

</details>

---

6. 在使用 SAMPLE 0.1 之前，必须满足什么条件？

   - A) 任何表都会自动支持它
   - B) 该表必须恰好包含十行
   - C) 它始终恰好返回 10% 的行
   - D) 必须定义兼容的 MergeTree 采样表达式，并将其包含在主键中

<details>
<summary>显示答案</summary>

**答案：D) 必须定义兼容的 MergeTree 采样表达式，并将其包含在主键中**

主日志表没有 SAMPLE BY。单独的 sample_demo 展示了所需的设计。确定性采样键区间不必恰好包含有限行集的 10%。

</details>

---

7. 在受其配置约束的前提下，Kafka 提供什么功能？

   - A) 通过内存 Buffer 保证恰好一次传递
   - B) 在保留期内进行突发缓冲和重放
   - C) 自动消除所有解析器错误
   - D) 在发生故障时提供无限存储

<details>
<summary>显示答案</summary>

**答案：B) 在保留期内进行突发缓冲和重放**

必须对保留期、确认、复制、容量、offset 提交和下游插入行为进行测试。内存 Buffer 可能会在崩溃时丢失已确认的数据。

</details>

---

8. 为什么对可选的 response_time_ms 使用可空 JSON 提取？

   - A) 缺失的测量值不应变成零延迟请求
   - B) 所有日志都是 HTTP 请求
   - C) 它无需进行 JSON 验证
   - D) 它会改变服务器时钟

<details>
<summary>显示答案</summary>

**答案：A) 缺失的测量值不应变成零延迟请求**

先检查 JSONType 以排除布尔值和数字字符串，然后提取可空数字。仅使用可空提取仍可能强制转换这些值。计数和百分位数查询应使用已测量的事件。

</details>

---

9. TTL TO VOLUME 子句需要什么并保证什么？

   - A) 它会创建一个 S3 bucket 和 IAM role
   - B) 它会在精确的挂钟截止时间删除每一行
   - C) 一个现有的选定存储策略；异步后台工作
   - D) 它使冷数据 part 成为独立的 Parquet 备份

<details>
<summary>显示答案</summary>

**答案：C) 一个现有的选定存储策略；异步后台工作**

TTL 无法创建策略或云权限。冷表存储与单独验证的 Parquet archive 具有不同的所有权和恢复语义。

</details>

---

10. 应如何构建由 ClickHouse 支持的 Grafana 告警？

   - A) 编造一个 clickhouse_custom_query Prometheus metric
   - B) 使用 grafana-clickhouse-datasource、数值 SQL 结果和 Grafana Alerting
   - C) 为每个 dashboard 提供管理员账户
   - D) 将未收到日志视为健康的证明

<details>
<summary>显示答案</summary>

**答案：B) 使用 grafana-clickhouse-datasource、数值 SQL 结果和 Grafana Alerting**

使用受限的只读账户、已验证的 TLS 和所需的 timeout-setting 权限。单独监控摄取；即使没有输入，聚合结果也可能返回零。

</details>

---

[返回指南](../../../observability/logging/04-clickhouse.md)
