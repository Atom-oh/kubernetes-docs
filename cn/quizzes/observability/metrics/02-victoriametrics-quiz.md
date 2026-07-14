# VictoriaMetrics 测验

测试你对 VictoriaMetrics 的理解。

---

1. 与 Prometheus 相比，以下哪项**不是** VictoriaMetrics 的主要优势？
   - A) 数据压缩效率最高可提升 7 倍
   - B) 复杂查询性能最高可提升 20 倍
   - C) 需要学习另一种查询语言
   - D) 具备水平扩展能力

<details>
<summary>显示答案</summary>

**答案：C) 需要学习另一种查询语言**

**说明：**
VictoriaMetrics 使用 MetricsQL 查询语言，它是 PromQL 的超集。所有现有的 PromQL 查询都可正常工作，并且它仅提供额外的便捷功能。因此，无需学习另一种查询语言。

</details>

---

2. 以下哪项**不是** VictoriaMetrics cluster mode 的组件？
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmoperator

<details>
<summary>显示答案</summary>

**答案：D) vmoperator**

**说明：**
VictoriaMetrics cluster mode 由三个核心组件组成：vminsert（写入请求路由）、vmstorage（数据存储）、vmselect（查询处理）。vmoperator 是一个独立的 Kubernetes Operator，并非 cluster mode 的核心组件。

</details>

---

3. vmagent 的主要作用是什么？
   - A) 长期数据存储
   - B) 仪表板渲染
   - C) 指标收集和 Remote Write 传输
   - D) 告警路由

<details>
<summary>显示答案</summary>

**答案：C) 指标收集和 Remote Write 传输**

**说明：**
vmagent 是一个轻量级 Agent，用于收集指标并将其发送到 VictoriaMetrics 或其他远程存储。它兼容 Prometheus scrape 配置，并提供数据缓冲、重传和标签重标记等功能。

</details>

---

4. MetricsQL 中 `keep_last_value()` 函数的用途是什么？
   - A) 保留最大值
   - B) 保留最后一个值（填补间隙）
   - C) 保留第一个值
   - D) 保留平均值

<details>
<summary>显示答案</summary>

**答案：B) 保留最后一个值（填补间隙）**

**说明：**
`keep_last_value()` 是一个 MetricsQL 扩展函数，它会使用最后一个已知值填补时间序列数据中的缺失值（间隙）。当发生 scrape 失败或临时数据丢失时，它可用于防止仪表板和告警中出现间隙。

</details>

---

5. VictoriaMetrics 中 `--dedup.minScrapeInterval` 标志的作用是什么？
   - A) 设置最小 scrape 间隔
   - B) 删除指定间隔内的重复样本
   - C) 设置数据压缩间隔
   - D) 设置告警评估间隔

<details>
<summary>显示答案</summary>

**答案：B) 删除指定间隔内的重复样本**

**说明：**
`--dedup.minScrapeInterval` 会删除指定时间间隔内同一时间序列的重复样本。例如，`--dedup.minScrapeInterval=30s` 会将 30 秒内的重复数据点合并为一个。在多个 Prometheus 实例 scrape 相同目标的 HA 配置中，此功能非常有用。

</details>

---

6. 在 vmsingle 和 vmcluster 之间进行选择的正确标准是什么？
   - A) 始终使用 vmcluster
   - B) 对于每天少于 1 亿个样本且不需要高可用性的场景，建议使用 vmsingle
   - C) vmsingle 不支持查询功能
   - D) vmcluster 只能在单个节点上运行

<details>
<summary>显示答案</summary>

**答案：B) 对于每天少于 1 亿个样本且不需要高可用性的场景，建议使用 vmsingle**

**说明：**
vmsingle（单节点模式）配置简单，适用于中小型环境。当每天的样本少于 1 亿且高可用性不是必需条件时，建议使用 vmsingle。对于大规模环境或需要高可用性时，请使用 vmcluster。

</details>

---

7. VictoriaMetrics cluster 中 `replicationFactor=2` 设置表示什么？
   - A) 仅使用 2 个存储节点
   - B) 将每个数据点复制到 2 个存储节点
   - C) 仅在 2 个节点上执行查询
   - D) 应用 2 倍压缩

<details>
<summary>显示答案</summary>

**答案：B) 将每个数据点复制到 2 个存储节点**

**说明：**
`replicationFactor=2` 会将 vminsert 配置为把每个数据点复制到 2 个 vmstorage 节点。即使一个存储节点发生故障，服务也能在不丢失数据的情况下继续运行。这是高可用性的推荐设置。

</details>

---

8. MetricsQL 中 `default` 运算符的用途是什么？
   - A) 设置默认标签
   - B) 没有结果时返回默认值
   - C) 设置默认聚合函数
   - D) 设置默认时间范围

<details>
<summary>显示答案</summary>

**答案：B) 没有结果时返回默认值**

**说明：**
MetricsQL 中的 `default` 运算符会在查询结果为空或为 NaN 时返回默认值。例如，`rate(http_requests_total[5m]) / rate(http_requests_total[5m]) default 0` 会返回 0，而不是除以零错误。在 PromQL 中，需要使用复杂的条件语句来实现此处理。

</details>

---

9. vmalert 的正确作用是什么？
   - A) 指标收集
   - B) 数据存储
   - C) 告警规则评估和告警生成
   - D) 仪表板创建

<details>
<summary>显示答案</summary>

**答案：C) 告警规则评估和告警生成**

**说明：**
vmalert 会评估告警规则，并在满足条件时向 Alertmanager 发送告警，类似于 Prometheus 的告警功能。它可以使用 VictoriaMetrics 或 Prometheus 作为数据源，也支持记录规则。

</details>

---

10. vmbackup 在 VictoriaMetrics 中的主要用途是什么？
    - A) 实时数据复制
    - B) 将备份创建到对象存储
    - C) 日志备份
    - D) 配置文件备份

<details>
<summary>显示答案</summary>

**答案：B) 将备份创建到对象存储**

**说明：**
vmbackup 是一个将 VictoriaMetrics 数据备份到 S3、GCS、Azure Blob 等对象存储的工具。它使用快照功能创建一致性备份，并可使用 vmrestore 进行恢复。它是灾难恢复和数据保护的重要工具。

</details>

---
