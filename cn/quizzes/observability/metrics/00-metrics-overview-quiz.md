# 指标概述测验

测试您对基本指标概念和监控解决方案的理解。

---

1. 在 Prometheus 指标的四种基本类型中，哪一种类型的值只能增加，并在重启时重置为 0？
   - A) Gauge
   - B) Counter
   - C) Histogram
   - D) Summary

<details>
<summary>显示答案</summary>

**答案：B) Counter**

**解释：**
Counter 是一种跟踪累积值的指标类型，其值只能增加，并在重启时重置为 0。它用于跟踪 HTTP 请求计数、错误计数、已完成任务计数等。Gauge 可以增加和减少，而 Histogram 和 Summary 用于衡量分布。

</details>

---

2. 以下哪项陈述正确描述了 Cardinality？
   - A) 它指指标采集间隔
   - B) 它指唯一时间序列组合的数量
   - C) 它指指标数据压缩比
   - D) 它指指标保留期限

<details>
<summary>显示答案</summary>

**答案：B) 它指唯一时间序列组合的数量**

**解释：**
Cardinality 指指标中唯一标签组合的数量。高 Cardinality 会直接影响存储使用量和查询性能。将 user_id 或 request_id 等可无限增长的值作为标签，会导致 Cardinality 急剧增长。

</details>

---

3. 关于 Pull 和 Push 模型的哪项陈述不正确？
   - A) Prometheus 是一个基于 Pull 的系统
   - B) 在 Pull 模型中，采集目标和采集间隔由中心化方式控制
   - C) Push 模型适合从短生命周期任务中采集指标
   - D) Pull 模型可以轻松访问位于 NAT/防火墙之后的目标

<details>
<summary>显示答案</summary>

**答案：D) Pull 模型可以轻松访问位于 NAT/防火墙之后的目标**

**解释：**
在 Pull 模型中，监控服务器直接向目标发送 HTTP 请求以采集指标，因此很难访问位于 NAT/防火墙之后的目标。相比之下，Push 模型允许目标直接发送指标，因此在 NAT/防火墙环境中更具优势。使用 Pushgateway 时，Pull 模型也可以采集来自短生命周期任务的指标。

</details>

---

4. 以下哪项陈述正确描述了 Histogram 和 Summary 之间的区别？
   - A) Histogram 在客户端计算分位数
   - B) Summary 允许跨多个实例进行聚合
   - C) Histogram 在服务器端（查询时）计算分位数
   - D) Summary 的存储效率高于 Histogram

<details>
<summary>显示答案</summary>

**答案：C) Histogram 在服务器端（查询时）计算分位数**

**解释：**
Histogram 将数据存储在 bucket 中，并在查询时于服务器端计算分位数。Summary 在客户端计算并存储分位数。Histogram 允许跨多个实例进行聚合，但 Summary 不允许。建议将 Histogram 用于 SLO/SLI 测量和分布式系统。

</details>

---

5. 以下哪项不是推荐的指标命名约定？
   - A) 使用 snake_case
   - B) 将单位作为后缀（_seconds、_bytes）
   - C) 使用 camelCase
   - D) 使用应用程序/领域前缀

<details>
<summary>显示答案</summary>

**答案：C) 使用 camelCase**

**解释：**
Prometheus 风格的指标命名约定使用 snake_case，而不是 camelCase。像 `http_requests_total`、`http_request_duration_seconds` 这样的良好指标名称使用小写字母和下划线，将单位作为后缀，并使用应用程序/领域前缀。

</details>

---

6. 以下哪项不是 Prometheus 需要单独的长期存储解决方案的恰当原因？
   - A) 较低的压缩比会增加磁盘使用量
   - B) 单节点架构限制了可扩展性
   - C) PromQL 不支持复杂查询
   - D) 不支持原生 HA 集群

<details>
<summary>显示答案</summary>

**答案：C) PromQL 不支持复杂查询**

**解释：**
PromQL 是一种非常强大的查询语言，支持复杂查询。Prometheus 不适合长期存储的原因包括相对较低的压缩比、单节点架构的可扩展性限制、缺乏原生 HA 集群，以及长期数据查询速度较慢。

</details>

---

7. 以下哪项解决方案对比不正确？
   - A) VictoriaMetrics 提供比 Prometheus 更高的压缩比
   - B) CloudWatch 是一项完全托管的服务
   - C) Mimir 仅支持本地磁盘
   - D) Datadog 以 SaaS 模式提供

<details>
<summary>显示答案</summary>

**答案：C) Mimir 仅支持本地磁盘**

**解释：**
Grafana Mimir 是一个需要对象存储（S3、GCS、Azure Blob 等）的分布式指标存储。它使用云对象存储而非本地磁盘，以提供无限的可扩展性和长期保留。VictoriaMetrics 同时支持本地磁盘和对象存储。

</details>

---

8. 以下哪项不是防止高 Cardinality 问题的恰当方法？
   - A) 不要将用户 ID 用作指标标签
   - B) 不要将请求 ID 用作指标标签
   - C) 对 HTTP 状态码进行分组（200 → 2xx）
   - D) 保持所有标签值唯一

<details>
<summary>显示答案</summary>

**答案：D) 保持所有标签值唯一**

**解释：**
为防止高 Cardinality，标签值不应无限增长。用户 ID、请求 ID、会话 ID 等可无限增长的值不应作为标签使用。更好的做法是对 HTTP 状态码进行分组（200 → 2xx），并规范化 URL 路径（/users/123 → /users/{id}）。

</details>

---

9. 在 Kubernetes 环境中，以下哪项正确匹配了主要指标来源及其角色？
   - A) node-exporter - Kubernetes 对象状态指标
   - B) kube-state-metrics - Node 级硬件指标
   - C) cAdvisor - 容器级资源指标
   - D) metrics-server - 长期指标存储

<details>
<summary>显示答案</summary>

**答案：C) cAdvisor - 容器级资源指标**

**解释：**
cAdvisor（Container Advisor）按容器采集 CPU、内存、I/O 等资源指标。node-exporter 提供 Node 级硬件/OS 指标，kube-state-metrics 提供 Kubernetes API 对象（Pod、Deployment、Node 等）的状态指标，metrics-server 为 HPA/VPA 提供实时资源指标。

</details>

---

10. 选择指标解决方案时，以下哪项不是恰当的考虑因素？
    - A) 团队的运维能力和规模
    - B) 多云需求
    - C) 成本结构和预算
    - D) 指标名称的长度

<details>
<summary>显示答案</summary>

**答案：D) 指标名称的长度**

**解释：**
选择指标解决方案时，应考虑团队的运维能力、多云需求、成本结构、可扩展性需求以及与现有生态系统的集成。指标名称的长度不会影响解决方案选择。相反，Cardinality、数据保留期限和查询性能才是重要的考虑因素。

</details>

---
