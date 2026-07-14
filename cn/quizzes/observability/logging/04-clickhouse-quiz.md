# 用于日志分析的 ClickHouse 测验

测试你对 ClickHouse 日志分析的理解。

---

1. ClickHouse 在日志分析中表现出高性能的主要原因是什么？

   - A) 基于行的存储
   - B) 基于列的存储
   - C) 基于文档的存储
   - D) 键值存储

<details>
<summary>显示答案</summary>

**答案：B) 基于列的存储**

**解释：**
ClickHouse 是一种针对分析查询优化的基于列的数据库（仅扫描特定列）。相同数据类型会连续存储，从而实现高压缩率和向量化查询执行。

</details>

---

2. 在 ClickHouse 集群中，哪个组件用于数据复制和分布式查询协调？

   - A) Kafka
   - B) Redis
   - C) ZooKeeper/ClickHouse Keeper
   - D) etcd

<details>
<summary>显示答案</summary>

**答案：C) ZooKeeper/ClickHouse Keeper**

**解释：**
ClickHouse 集群使用 ZooKeeper 或 ClickHouse Keeper 来协调副本之间的数据同步、分布式 DDL 执行和领导者选举。ClickHouse Keeper 是 ClickHouse 特有的 ZooKeeper 替代方案。

</details>

---

3. 哪个 ClickHouse 表引擎支持复制，且最适合用于日志存储？

   - A) MergeTree
   - B) ReplicatedMergeTree
   - C) Log
   - D) Memory

<details>
<summary>显示答案</summary>

**答案：B) ReplicatedMergeTree**

**解释：**
ReplicatedMergeTree 为所有 MergeTree 功能（排序、分区、TTL 等）添加了复制功能。建议将其用于需要高可用性的生产环境日志存储。

</details>

---

4. 在 ClickHouse 中，低基数字符串列（例如 level、namespace）应使用哪种优化类型？

   - A) String
   - B) FixedString
   - C) LowCardinality(String)
   - D) Enum

<details>
<summary>显示答案</summary>

**答案：C) LowCardinality(String)**

**解释：**
LowCardinality(String) 用于唯一值较少（约 10,000 个或更少）的字符串列。它在内部使用字典编码来优化存储空间和查询性能。

</details>

---

5. 设计 ClickHouse 日志表时，在 `ORDER BY` 子句中指定列顺序的原则是什么？

   - A) 按字母顺序
   - B) 按列大小顺序（最小的在前）
   - C) 经常被过滤的列在前
   - D) 按创建时间顺序

<details>
<summary>显示答案</summary>

**答案：C) 经常被过滤的列在前**

**解释：**
ClickHouse 的 ORDER BY 会影响数据排序和索引创建。将 WHERE 子句中经常使用的列放在前面，可以在查询期间扫描更少的数据。示例：`ORDER BY (namespace, service, timestamp)`

</details>

---

6. 在 ClickHouse 中，用于快速分析大型数据集的采样技术语法是什么？

   - A) `LIMIT RANDOM 10%`
   - B) `SAMPLE 0.1`
   - C) `WHERE rand() < 0.1`
   - D) `TABLESAMPLE (10 PERCENT)`

<details>
<summary>显示答案</summary>

**答案：B) `SAMPLE 0.1`**

**解释：**
ClickHouse 的 `SAMPLE` 子句仅扫描部分数据，以进行快速近似分析。`SAMPLE 0.1` 仅读取 10% 的数据。可以将结果乘以适当的系数来获得估算总数。

</details>

---

7. 在日志收集过程中，将 Kafka 放在日志源与 ClickHouse 之间的主要原因是什么？

   - A) 数据加密
   - B) 缓冲和峰值流量处理
   - C) 数据压缩
   - D) 查询优化

<details>
<summary>显示答案</summary>

**答案：B) 缓冲和峰值流量处理**

**解释：**
Kafka 充当消息队列，在流量高峰期间缓冲日志，使 ClickHouse 能以稳定速率消费数据。它还可以防止 ClickHouse 发生故障时丢失数据。

</details>

---

8. 在 ClickHouse SQL 中，使用哪些函数提取 JSON 字段值？

   - A) JSON_EXTRACT()
   - B) JSONExtractString(), JSONExtractFloat()
   - C) parseJSON()
   - D) getJSON()

<details>
<summary>显示答案</summary>

**答案：B) JSONExtractString(), JSONExtractFloat()**

**解释：**
ClickHouse 使用 `JSONExtractString(json, 'field')` 和 `JSONExtractFloat(json, 'field')` 等函数提取 JSON 字段。每种类型使用不同的函数。

</details>

---

9. ClickHouse 表中的哪项功能会自动删除旧数据？

   - A) AUTO_DELETE
   - B) RETENTION_POLICY
   - C) TTL (Time To Live)
   - D) EXPIRE_AFTER

<details>
<summary>显示答案</summary>

**答案：C) TTL (Time To Live)**

**解释：**
ClickHouse 的 TTL 功能会在一段时间后自动删除数据，或将其移动到不同的存储（例如 S3）。示例：`TTL date + INTERVAL 90 DAY DELETE`

</details>

---

10. 将 ClickHouse 与 Grafana 集成时，使用哪个数据源插件？

    - A) grafana-mysql-datasource
    - B) grafana-clickhouse-datasource
    - C) grafana-sql-datasource
    - D) grafana-olap-datasource

<details>
<summary>显示答案</summary>

**答案：B) grafana-clickhouse-datasource**

**解释：**
要将 ClickHouse 与 Grafana 集成，请安装 `grafana-clickhouse-datasource` 插件。该插件可让你使用 SQL 查询可视化 ClickHouse 数据并构建仪表板。

</details>
