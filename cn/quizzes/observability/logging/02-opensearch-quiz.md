# Amazon OpenSearch Service 测验

测试你对 Amazon OpenSearch Service 的理解。

---

1. Amazon OpenSearch Service 基于哪个开源项目？

   - A) Apache Solr
   - B) Elasticsearch 7.10 分支
   - C) 仅 Apache Lucene
   - D) Splunk 开源版本

<details>
<summary>显示答案</summary>

**答案：B) Elasticsearch 7.10 分支**

**解释：**
OpenSearch 是 AWS 于 2021 年基于 Apache 2.0 许可证从 Elasticsearch 7.10 分支出来创建的开源项目。它的启动是为了应对 Elastic 的许可证变更（SSPL）。

</details>

---

2. 在 OpenSearch 集群中，哪种节点类型负责索引元数据管理和集群状态管理？

   - A) Data Node
   - B) Master Node
   - C) UltraWarm Node
   - D) Coordinating Node

<details>
<summary>显示答案</summary>

**答案：B) Master Node**

**解释：**
Master Node 负责集群管理任务，例如集群状态管理、索引创建/删除和分片分配决策。在生产环境中，建议使用 3 个专用 master node。

</details>

---

3. OpenSearch 中具有成本效益的只读存储层是什么？

   - A) Hot Storage
   - B) Warm Storage
   - C) UltraWarm
   - D) Standard Storage

<details>
<summary>显示答案</summary>

**答案：C) UltraWarm**

**解释：**
UltraWarm 是基于 S3 的只读存储层，其成本约比 Hot storage (EBS) 低 75%。它适合存储不经常查询的历史日志数据。

</details>

---

4. ISM (Index State Management) 策略的主要用途是什么？

   - A) 管理索引安全设置
   - B) 自动化索引生命周期（rollover、删除等）
   - C) 优化索引查询
   - D) 配置索引复制

<details>
<summary>显示答案</summary>

**答案：B) 自动化索引生命周期（rollover、删除等）**

**解释：**
ISM 策略会自动管理索引生命周期。它们可以自动执行索引 rollover、Hot→UltraWarm→Cold 转换，以及在保留期结束后删除索引。

</details>

---

5. 对于 OpenSearch，哪种日志收集方法最具成本效益且最容易管理？

   - A) 在 EC2 上运行 Logstash
   - B) FluentBit DaemonSet + 直接传输
   - C) Kinesis Data Firehose
   - D) Lambda 函数

<details>
<summary>显示答案</summary>

**答案：C) Kinesis Data Firehose**

**解释：**
Kinesis Data Firehose 是一项全托管服务，可自动执行缓冲、压缩和批处理。凭借内置的 S3 备份和错误处理，它具有较低的运维开销，并且适合大规模日志收集，具有成本效益。

</details>

---

6. 在 OpenSearch Fine-Grained Access Control (FGAC) 中，哪项功能会将日志访问权限限制为仅特定 namespace 的日志？

   - A) Field-Level Security (FLS)
   - B) Document-Level Security (DLS)
   - C) Index-Level Security
   - D) Cluster-Level Security

<details>
<summary>显示答案</summary>

**答案：B) Document-Level Security (DLS)**

**解释：**
Document-Level Security (DLS) 会将访问权限限制为仅匹配特定条件的文档。例如，可以使用条件 `kubernetes.namespace: "team-a"` 配置为仅访问特定团队的日志。

</details>

---

7. 在 OpenSearch 索引模板中，用于替代 `LowCardinality` 的 Elasticsearch/OpenSearch 字符串优化类型是什么？

   - A) text
   - B) keyword
   - C) analyzed_string
   - D) compact_string

<details>
<summary>显示答案</summary>

**答案：B) keyword**

**解释：**
在 OpenSearch 中，低基数字符串字段（namespace、level 等）使用 `keyword` 类型。`text` 类型会被分词以用于全文搜索，而 `keyword` 则针对精确匹配和聚合进行了优化。

</details>

---

8. OpenSearch 成本优化的正确存储分层顺序是什么？

   - A) Cold → UltraWarm → Hot
   - B) Hot → Cold → UltraWarm
   - C) Hot → UltraWarm → Cold
   - D) UltraWarm → Hot → Cold

<details>
<summary>显示答案</summary>

**答案：C) Hot → UltraWarm → Cold**

**解释：**
数据首先存储在 Hot storage (EBS) 中以便快速查询，然后随着时间推移转移到 UltraWarm（只读），最后转移到 Cold Storage (S3) 以存储较旧的数据。成本将按此顺序降低。

</details>

---

9. 在 OpenSearch 中搜索特定时间范围内的错误日志时，正确的 Query DSL 是什么？

   - A) `{"query": {"match": {"level": "error", "time": "1h"}}}`
   - B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`
   - C) `{"filter": {"level": "error", "time": "> now-1h"}}`
   - D) `{"search": {"level": "error", "since": "1h"}}`

<details>
<summary>显示答案</summary>

**答案：B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`**

**解释：**
在 OpenSearch Query DSL 中，`bool` 查询用于组合多个条件。`must` 数组同时包含 `match`（文本匹配）和 `range`（时间范围）规范。

</details>

---

10. 比较 OpenSearch 和 Loki 时，OpenSearch 更适合哪种使用场景？

    - A) 将成本优化作为最高优先级的初创公司
    - B) 需要全文搜索和复杂分析查询的场景
    - C) 与现有 Grafana stack 集成
    - D) 仅需要简单日志过滤的场景

<details>
<summary>显示答案</summary>

**答案：B) 需要全文搜索和复杂分析查询的场景**

**解释：**
OpenSearch 支持强大的基于 Lucene 的全文搜索功能和复杂的聚合查询。它适用于安全分析（SIEM）、合规性和复杂日志分析。对于成本优化或简单过滤，Loki 更适合。

</details>
