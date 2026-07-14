# Grafana Mimir 测验

用于测试您对 Grafana Mimir 理解程度的测验。

---

1. Grafana Mimir 的主要存储后端是什么？
   - A) 仅本地 SSD
   - B) 对象存储（S3、GCS、Azure Blob）
   - C) NFS 共享存储
   - D) 仅块存储

<details>
<summary>显示答案</summary>

**答案：B) 对象存储（S3、GCS、Azure Blob）**

**说明：**
Grafana Mimir 需要对象存储。它支持 S3、Google Cloud Storage、Azure Blob Storage 等，可提供无限扩展能力和高性价比的长期存储。本地存储仅用于 Ingester 的 WAL 和临时数据。

</details>

---

2. Distributor 在 Mimir 架构中的作用是什么？
   - A) 长期数据存储
   - B) 写入请求的第一个入口点、租户验证和样本分发
   - C) 查询结果缓存
   - D) 块压缩

<details>
<summary>显示答案</summary>

**答案：B) 写入请求的第一个入口点、租户验证和样本分发**

**说明：**
Distributor 是写入请求的第一个入口点，负责租户 ID 验证、时间序列验证、基于哈希环的 Ingester 分发，以及基于复制因子的复制。它是一个无状态组件，易于水平扩展。

</details>

---

3. Mimir 如何实现多租户？
   - A) 为每个租户运行单独的集群
   - B) 通过 X-Scope-OrgID header 识别租户
   - C) 基于 IP 地址的租户隔离
   - D) 基于 Namespace 的租户隔离

<details>
<summary>显示答案</summary>

**答案：B) 通过 X-Scope-OrgID header 识别租户**

**说明：**
Mimir 通过 HTTP header `X-Scope-OrgID` 识别租户。在 Prometheus 的 remote_write 配置中添加此 header 可隔离各个租户的数据。可以配置每个租户的限制，数据会按租户路径存储在对象存储中。

</details>

---

4. Mimir 的 Ingester 为什么要将块上传到对象存储？
   - A) 提升实时查询性能
   - B) 将数据从内存持久化到磁盘
   - C) 存储告警规则
   - D) 备份仪表板设置

<details>
<summary>显示答案</summary>

**答案：B) 将数据从内存持久化到磁盘**

**说明：**
Ingester 首先将接收到的时间序列数据存储在内存中，然后定期（默认每 2 小时）创建 TSDB 块并将其上传到对象存储。这确保数据被永久存储，即使 Ingester 发生故障也能最大限度地减少数据丢失。

</details>

---

5. Mimir 的 Compactor 的正确作用是什么？
   - A) 实时查询处理
   - B) 将小块合并为大块并去重
   - C) Metrics 收集
   - D) 告警传递

<details>
<summary>显示答案</summary>

**答案：B) 将小块合并为大块并去重**

**说明：**
Compactor 将对象存储中的小块合并（压缩）为较大的块，删除重复数据，并根据保留策略删除旧数据。这可提升查询性能并降低存储成本。

</details>

---

6. 以下哪项不是 Mimir 的 Query-frontend 提供的功能？
   - A) 大型查询拆分
   - B) 结果缓存
   - C) 数据存储
   - D) 查询重试

<details>
<summary>显示答案</summary>

**答案：C) 数据存储**

**说明：**
Query-frontend 是负责查询优化和缓存的无状态组件。它将大型查询拆分为较小的查询，缓存结果，并重试失败的查询。数据存储由 Ingester（短期）和对象存储（长期）处理。

</details>

---

7. 与 VictoriaMetrics 相比，以下哪项是 Mimir 的正确特性？
   - A) 仅可使用本地磁盘
   - B) 运维复杂度更低
   - C) 需要对象存储，提供企业级多租户
   - D) 使用 MetricsQL 查询语言

<details>
<summary>显示答案</summary>

**答案：C) 需要对象存储，提供企业级多租户**

**说明：**
Mimir 需要对象存储，并提供原生多租户功能，因此适用于企业环境。VictoriaMetrics 也支持本地磁盘，且运维更简单，但 Mimir 与 Grafana 生态系统的集成非常出色。

</details>

---

8. Store-gateway 在 Mimir 中的作用是什么？
   - A) Metrics 收集
   - B) 缓存对象存储块并处理历史数据查询
   - C) 告警规则评估
   - D) 租户认证

<details>
<summary>显示答案</summary>

**答案：B) 缓存对象存储块并处理历史数据查询**

**说明：**
Store-gateway 缓存存储在对象存储中的块索引和 chunks，并处理历史数据查询。Querier 从 Ingester 获取近期数据，从 Store-gateway 获取历史数据，然后将它们合并。

</details>

---

9. Mimir 中的 `compactor_blocks_retention_period` 设置的作用是什么？
   - A) 内存缓存保留期
   - B) 设置块数据保留期
   - C) 日志保留期
   - D) 告警历史保留期

<details>
<summary>显示答案</summary>

**答案：B) 设置块数据保留期**

**说明：**
`compactor_blocks_retention_period` 设置 Compactor 保留块的期限。例如，将其设置为 `365d` 会删除超过 1 年的块。此设置有助于管理存储成本并满足合规要求。

</details>

---

10. 以下哪项不是 Mimir 高可用性配置的建议？
    - A) 至少 3 个 Ingester 副本，采用区域感知复制
    - B) 至少 2 个 Store-gateway 副本
    - C) 在单个可用区中部署所有组件
    - D) 使用 memcached 启用缓存

<details>
<summary>显示答案</summary>

**答案：C) 在单个可用区中部署所有组件**

**说明：**
为实现高可用性，应将组件分布在多个可用区（AZ）中。Mimir 支持区域感知复制，可将 Ingesters 分布在多个 AZ 中。在单个 AZ 中部署会导致该 AZ 发生故障时服务完全中断。

</details>
