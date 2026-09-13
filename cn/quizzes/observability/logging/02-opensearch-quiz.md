# Amazon OpenSearch Service 测验

> **最后更新**: September 13, 2026

基于[指南](../../../observability/logging/02-opensearch.md)中的托管域和收集器示例。

---

1. 下列哪项陈述正确区分了 OpenSearch 与 Amazon OpenSearch Service？

   - A) 每个 Elasticsearch 客户端/插件都保持兼容
   - B) AWS 会立即支持每个上游版本
   - C) OpenSearch 是一个 Apache-2.0 项目；托管服务支持选定的引擎版本
   - D) 该服务仅是一个 Kibana 托管产品

<details>
<summary>显示答案</summary>

**答案: C**

Elasticsearch 7.10 血统并不保证全面兼容。请检查 AWS 版本支持情况以及实际使用的客户端/插件。较早的 2.11 基线版本仍将获得标准支持，直至 2027 年 11 月 7 日。

</details>

---

2. 配置了专用 cluster-manager 节点时，哪个角色负责集群状态和分片分配管理？

   - A) 专用 cluster-manager 节点
   - B) UltraWarm 存储
   - C) 冷存储
   - D) 日志收集器

<details>
<summary>显示答案</summary>

**答案: A**

AWS 配置字段仍使用 dedicated_master 名称。管理节点数量不同于数据副本数量，而且仅启用 Zone Awareness 并不会启用带 Standby 的 Multi-AZ。

</details>

---

3. 对于传统 UltraWarm 和冷存储，下列哪项陈述正确？

   - A) UltraWarm 仅将所有内容存储在 EBS 上
   - B) 两者均以 S3 为后端；查询前必须将冷索引附加到 UltraWarm
   - C) 每个工作负载都恰好节省 75%
   - D) 每种实例/引擎组合都支持这两个层级

<details>
<summary>显示答案</summary>

**答案: B**

hot→UltraWarm→cold 策略需要满足相关服务前提条件并具备迁移容量。成本和查询延迟取决于工作负载；存储层级名称并不保证固定的节省比例。

</details>

---

4. 哪个 ISM 操作会从托管 OpenSearch Service 冷存储中删除索引？

   - A) 每个存储层级中的 delete
   - B) force_merge
   - C) warm_migration
   - D) cold_delete

<details>
<summary>显示答案</summary>

**答案: D**

托管冷存储需要使用 cold_delete。策略在每个操作对象中使用一个操作，并且异步运行；示例中的 7/30/90 天索引年龄并不保证精确的事件年龄保留期。

</details>

---

5. 应如何比较直接 Fluent Bit 传输和 Amazon Data Firehose？

   - A) Firehose 始终是最便宜的选项
   - B) 直接 Fluent Bit 无法向 AWS 进行身份验证
   - C) 比较运营需求、Schema、缓冲/重试/备份、访问和实测成本
   - D) 两者都会自动创建相同的 Kubernetes 元数据

<details>
<summary>显示答案</summary>

**答案: C**

Firehose 提供托管传输路径，但需要角色、连接性以及兼容的记录。FailedDocumentsOnly 用于选择其备份模式；仅将前缀命名为 failed/ 并不能选择该行为。

</details>

---

6. 下列哪项陈述正确描述了 DLS 和 FLS？

   - A) DLS 过滤文档；FLS 控制返回字段，同时有效角色和受信任的元数据仍然很重要
   - B) FLS 会自动验证 Kubernetes namespace
   - C) 仅基于 URI 的 IAM 会限制 bulk 请求正文中命名的每个索引
   - D) 一条 security-group 规则会授予文档级读取访问权限

<details>
<summary>显示答案</summary>

**答案: A**

该指南使用受信任的 kubernetes.namespace_name 元数据。受限角色不会取消已有的更宽泛授权。FLS 不会对允许的消息中包含的敏感文本进行脱敏，也不会删除已存储的数据/备份。

</details>

---

7. 哪种映射字符串类型支持精确匹配和常见字段聚合？

   - A) 不带子字段的 text
   - B) keyword
   - C) 作为 OpenSearch 类型的 LowCardinality
   - D) 仅未映射字段

<details>
<summary>显示答案</summary>

**答案: B**

Keyword 不同于经分析的 text，也不同于 ClickHouse LowCardinality。许多 keyword/数值聚合使用列式 doc values，因此并非在所有情况下都会扫描每个完整的 _source 文档。

</details>

---

8. 使用 Logstash_Format On 和前缀 logs-production 时，图示中的 Fluent Bit 输出写入何处？

   - A) 始终写入 rollover alias
   - B) 自动写入 Serverless collection
   - C) 直接写入分离的冷索引
   - D) 基于日期的 logs-production-YYYY.MM.DD 索引

<details>
<summary>显示答案</summary>

**答案: D**

不会仅因存在 alias 就选择它。该指南将每日索引路径与 rollover-logs-* 分开，后者需要 rollover alias 设置、编号索引和 write alias。

</details>

---

9. 哪个 Query DSL 会筛选过去一小时内已映射的错误日志行？

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>显示答案</summary>

**答案: C**

示例映射将应用字段嵌套在 app 下，并使用 @timestamp。过滤上下文结合精确 keyword 匹配和时间范围，无需进行相关性评分。

</details>

---

10. 为日志工作负载选择 OpenSearch、Loki 或 ClickHouse 的合理依据是什么？

   - A) 通用的 100GB/day 切换阈值
   - B) 每个组织都有相同查询组合的说法
   - C) 固定的 3–5× 成本和 60–80% 节省规则
   - D) 代表性查询，以及保留期、持久性、权限、运营能力和实测成本

<details>
<summary>显示答案</summary>

**答案: D**

三者具有不同的索引/查询模型和运维权衡。应比较等效需求并验证迁移、对账和回滚；没有任何产品会自动实现合规或最低成本。

</details>
