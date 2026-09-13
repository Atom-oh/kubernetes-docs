# 指标概览测验

> **最后更新**: September 12, 2026

1. 哪种类型表示可能重置的累积计数？

   - A) Gauge
   - B) Counter
   - C) 预先计算的 p99
   - D) 抓取时间戳

<details>
<summary>显示答案</summary>

**答案：B**

Counter 会累积非负增量。当被测量的状态被重新创建时，可能发生重置。rate() 会处理观测到的重置，但无法恢复未观测到的增量。

</details>

2. 五种方法、二十个路由和十种状态意味着什么？

   - A) 每次 Deployment 中恰好存储 1,000 个 series
   - B) 如果所有组合都可能存在，应用标签组合最多为 1,000 个
   - C) 每天恰好有 1,000 个样本
   - D) 对资源使用没有影响

<details>
<summary>显示答案</summary>

**答案：B**

该乘积是上限。实际组合、target/replica 标签、histogram buckets 和历史变化决定了实际的 series/存储占用。

</details>

3. 哪种 Pushgateway 用法是合适的？

   - A) 为每个短生命周期 Pod 使用一个 HOSTNAME 分组键，并依赖自动过期
   - B) 将其用于具有稳定分组、成功时间戳和明确退役策略的适当服务级批处理
   - C) 将 gateway up=1 视为每个批处理均已成功的证明
   - D) 即使批处理失败也推送成功时间戳

<details>
<summary>显示答案</summary>

**答案：B**

Pushgateway 并非所有短生命周期任务的默认选择，且分组没有自动 TTL。其抓取健康状态与批处理新鲜度相互独立。使用 honor_labels 进行抓取可保留推送的 job 身份。

</details>

4. 关于 Histogram 和 Summary，哪项陈述正确？

   - A) Summary quantile 始终精确
   - B) 对 instance p99 值取平均可得到 fleet p99
   - C) 兼容的 classic histogram buckets 可以合并；Summary 的 sum/count 可以合并以计算均值
   - D) 任何 Summary 数据都永远无法聚合

<details>
<summary>显示答案</summary>

**答案：C**

Classic buckets 由埋点的生产者计数；Prometheus 在查询时计算 quantile。Summary quantile 的误差取决于算法/窗口，无法聚合为 fleet quantile；而非负持续时间的 sum/count rate 可以得出 fleet mean。

</details>

5. 以下哪项不是新 Prometheus 应用指标的推荐约定？

   - A) 使用描述性前缀
   - B) 使用诸如 _seconds 或 _bytes 的单位后缀
   - C) 相较于通常的基本单位约定，优先使用 camelCase 和毫秒单位
   - D) 使用 _total 标识累积 Counter

<details>
<summary>显示答案</summary>

**答案：C**

应优先使用描述性的下划线分隔名称和基本单位。_total 是 Counter 标记，而不是物理单位。现有 exporter API（例如 node_memory_MemAvailable_bytes）保留其已发布的拼写。

</details>

6. 关于 Prometheus 保留期，哪项陈述正确？

   - A) 它绝不能保留超过 30 天
   - B) 在未显式设置基于时间/大小的保留期时，默认值为 15 天；更长的保留期需要合适的配置和容量
   - C) 它不会压缩本地数据
   - D) 没有 Mimir 就不可能使用独立的 collection replica

<details>
<summary>显示答案</summary>

**答案：B**

默认保留期不是最大值。本地 TSDB 不是复制式分布式存储；采集冗余、查询去重、持久性和恢复是独立的设计决策。

</details>

7. 哪项产品/存储声明不正确？

   - A) VictoriaMetrics 单节点和集群 Deployment 有不同的运维要求
   - B) 传统 CloudWatch 指标的分辨率会随时间推移而变粗
   - C) Mimir 对象存储保证无限扩展，并消除了所有本地存储需求
   - D) Datadog 指标使用查询 rollup，因此保留期并不能保证每个图表中均保有原始分辨率

<details>
<summary>显示答案</summary>

**答案：C**

对象存储是 Mimir 架构的一部分，而非无限容量的保证。摄取/本地资源、查询限制、复制和运维容量仍然重要。不要将备份目标或特定版本功能与产品的主要存储混为一谈。

</details>

8. 哪种方法无法控制指标基数？

   - A) 使用规范化的路由模板
   - B) 避免将用户/会话 ID 作为常规标签
   - C) 在可以接受丢失细节时对状态码进行分组
   - D) 为每个请求分配一个新的 request_id 标签值

<details>
<summary>显示答案</summary>

**答案：D**

不同的标签值会创建不同的 series，即使这些值经过哈希处理也是如此。需要时，请求特定的上下文应放在受到适当控制的 logs/traces 中。基数和敏感数据暴露都需要审查。

</details>

9. 哪个 Kubernetes 指标角色匹配正确？

   - A) node-exporter — Kubernetes API 对象状态
   - B) kube-state-metrics — 测量到的 container CPU 使用量
   - C) cAdvisor/kubelet metrics — container 资源测量值
   - D) metrics-server — 长期 Prometheus TSDB

<details>
<summary>显示答案</summary>

**答案：C**

node-exporter 报告主机 OS 指标；kube-state-metrics 暴露 API 对象状态；metrics-server 提供 Resource Metrics API。Prometheus/vmalert/Mimir rules 评估告警，Alertmanager 对其进行路由。vmagent 是采集器/转发器，而不是可查询的 TSDB。

</details>

10. 什么能使成本比较可供审查？

   - A) 仅基于团队规模的产品排名
   - B) 未包含样本间隔或功能假设的节点数量
   - C) 已测量的 series/sample 数量、保留期/分辨率、HA/query 要求，以及所选功能的当前定价
   - D) 假定指标名称/值的长度永远无关紧要

<details>
<summary>显示答案</summary>

**答案：C**

在交付筛选/去重之前，以 15 秒间隔运行 30 天的 100 万个实际导出 series 意味着 1,728 亿个样本。基础设施、indexes/WAL、replica、查询工作负载、自定义指标配额和运维人员投入都可能改变成本。这是工作负载计算，而非供应商报价。

</details>

[返回指南](../../../observability/metrics/README.md)
