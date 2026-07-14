# Grafana Loki 测验

测试你对 Grafana Loki 的理解。

---

1. Loki 比 Elasticsearch 更具成本效益的主要原因是什么？

   - A) 更快的查询性能
   - B) 仅索引标签而非日志内容
   - C) 使用更好的压缩算法
   - D) 云原生设计

<details>
<summary>显示答案</summary>

**答案：B) 仅索引标签而非日志内容**

**解释：**
Loki 不会索引日志内容，只索引元数据（标签）。这可显著减小索引大小，并能够使用廉价的对象存储（如 S3），与 Elasticsearch 相比可将运营成本降低 10 倍。

</details>

---

2. Loki 架构中，哪个组件会在内存中缓冲日志数据并将其存储到存储系统？

   - A) Distributor
   - B) Querier
   - C) Ingester
   - D) Compactor

<details>
<summary>显示答案</summary>

**答案：C) Ingester**

**解释：**
Ingester 从 Distributor 接收日志数据，在内存中进行缓冲（创建 chunks），管理 WAL，并将 chunks 刷新到存储系统。它还会提供实时查询服务。

</details>

---

3. 生产 EKS 环境中推荐使用哪种 Loki 部署模式？

   - A) Monolithic 模式
   - B) Simple Scalable 模式
   - C) Microservices 模式
   - D) Standalone 模式

<details>
<summary>显示答案</summary>

**答案：B) Simple Scalable 模式**

**解释：**
Simple Scalable 模式为实现可扩展性而分离了读写路径，同时比 Microservices 模式更易于运维。它适用于大多数每日日志量为 100GB 到 10TB 的生产 EKS 集群。

</details>

---

4. 用于计算每秒错误日志速率的正确 LogQL 查询是什么？

   - A) `count({app="nginx"} |= "error")`
   - B) `rate({app="nginx"} |= "error" [5m])`
   - C) `sum({app="nginx"} |= "error")`
   - D) `avg({app="nginx"} |= "error" [5m])`

<details>
<summary>显示答案</summary>

**答案：B) `rate({app="nginx"} |= "error" [5m])`**

**解释：**
`rate()` 函数计算指定时间范围内每秒的日志行数。`[5m]` 表示 5 分钟的范围。`count()` 不会以这种方式用于指标查询，`sum()` 和 `avg()` 也不会像这样单独使用。

</details>

---

5. 以下哪项是应在 Loki 标签设计中避免使用的高基数标签示例？

   - A) namespace
   - B) app
   - C) pod_name
   - D) environment

<details>
<summary>显示答案</summary>

**答案：C) pod_name**

**解释：**
pod_name 可能有数千个唯一值，因此是高基数标签。高基数标签会大幅增加流数量，导致索引更大且内存使用量更高。namespace、app 和 environment 通常只有数十个或更少的值，因此比较合适。

</details>

---

6. 在 EKS 中，推荐使用哪种身份验证方法来访问 Loki S3 后端？

   - A) Access Key ID/Secret Access Key
   - B) IAM Roles for Service Accounts (IRSA)
   - C) EC2 Instance Profile
   - D) AWS STS AssumeRole

<details>
<summary>显示答案</summary>

**答案：B) IAM Roles for Service Accounts (IRSA)**

**解释：**
IRSA 将 IAM roles 关联到 Kubernetes service accounts，无需在代码或配置中存储 Access Keys。这是最安全的推荐方法，并且在 EKS 环境中得到原生支持。

</details>

---

7. 解析 JSON 日志后，按特定字段值进行筛选的正确 LogQL 语法是什么？

   - A) `{app="api"} | json | level="error"`
   - B) `{app="api"} | json | filter level="error"`
   - C) `{app="api"} | json | where level="error"`
   - D) `{app="api"} | json | select level="error"`

<details>
<summary>显示答案</summary>

**答案：A) `{app="api"} | json | level="error"`**

**解释：**
在 LogQL 中，JSON 解析后的标签筛选使用 `| field_name="value"` 格式。`filter`、`where` 和 `select` 不是 LogQL 语法。

</details>

---

8. 以下哪项不是 Loki Compactor 的主要职责？

   - A) 将小 chunks 合并为更大的 chunks
   - B) 应用保留策略（删除数据）
   - C) 从客户端接收日志
   - D) 索引优化

<details>
<summary>显示答案</summary>

**答案：C) 从客户端接收日志**

**解释：**
从客户端接收日志是 Distributor 的职责。Compactor 会在后台优化已存储的数据，并根据保留策略删除旧数据。

</details>

---

9. 在 Loki 中遇到“rate limit exceeded”错误时，应调整哪些设置？

   - A) max_streams_per_user
   - B) ingestion_rate_mb, ingestion_burst_size_mb
   - C) max_query_parallelism
   - D) chunk_idle_period

<details>
<summary>显示答案</summary>

**答案：B) ingestion_rate_mb, ingestion_burst_size_mb**

**解释：**
当日志摄取速率超过限制时，会发生“rate limit exceeded”错误。可通过增加 `ingestion_rate_mb`（每秒最大摄取量）和 `ingestion_burst_size_mb`（突发额度）来解决。

</details>

---

10. 在 Loki 性能调优中，Ingester 的 `chunk_idle_period` 设置是什么意思？

    - A) 从 chunk 创建到删除的时间
    - B) 空闲流在被刷新前等待的时间
    - C) 查询超时时长
    - D) 日志保留期限

<details>
<summary>显示答案</summary>

**答案：B) 空闲流在被刷新前等待的时间**

**解释：**
`chunk_idle_period` 是指当某个流不再有新日志到达时，将 chunk 刷新到存储系统之前的等待时间。减小此值可降低内存使用量，但可能会创建许多小 chunks。

</details>
