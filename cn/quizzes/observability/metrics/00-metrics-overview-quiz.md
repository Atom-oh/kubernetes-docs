# 指标概览测验

> **最后更新**：September 12, 2026

1. 哪种类型表示可能重置的累积计数？

   - A) Gauge
   - B) Counter
   - C) 预先计算的 p99
   - D) 抓取时间戳

<details>
<summary>显示答案</summary>

**答案：B**

Counter 会累积非负增量。当被测状态重新创建时，计数可能会重置。rate() 会处理观测到的重置，但无法恢复未观测到的增量。

</details>

2. 五种方法、二十条路由和十种状态码意味着什么？

   - A) 每个 Deployment 中恰好有 1,000 个已存储序列
   - B) 如果所有组合都可能出现，则应用标签组合最多为 1,000 个
   - C) 每天恰好有 1,000 个样本
   - D) 不影响资源使用

<details>
<summary>显示答案</summary>

**答案：B**

这个乘积是上限。实际组合、目标/副本标签、直方图桶以及历史变化决定真实的序列/存储占用。

</details>

3. 哪种 Pushgateway 用法是恰当的？

   - A) 为每个短生命周期 Pod 使用一个 HOSTNAME 分组键，并依赖自动过期
   - B) 将其用于适当的服务级批处理，采用稳定的分组方式、成功时间戳和明确的退役策略
   - C) 将 gateway up=1 视为每个批处理都成功的证明
   - D) 即使批处理失败，也推送成功时间戳

<details>
<summary>显示答案</summary>

**答案：B**

Pushgateway 并非所有短生命周期任务的默认选择，且分组没有自动 TTL。其抓取健康状态与批处理数据的新鲜度是两回事。使用 honor_labels 进行抓取可保留推送的 job 标识。

</details>

4. 关于 Histogram 和 Summary，哪项说法正确？

   - A) Summary 分位数始终精确
   - B) 对各实例的 p99 求平均即可得到整个集群的 p99
   - C) 兼容的经典直方图桶可以合并；Summary 的 sum/count 可以合并以计算均值
   - D) Summary 数据绝不可能聚合

<details>
<summary>显示答案</summary>

**答案：C**

经典直方图桶由埋点生产端进行计数；Prometheus 在查询时计算分位数。Summary 分位数的误差取决于算法/窗口，无法聚合为整个集群的分位数；而非负时长的 sum/count 速率可以得出整个集群的均值。

</details>

5. 以下哪项**不是**新建 Prometheus 应用指标的推荐约定？

   - A) 使用描述性前缀
   - B) 使用 _seconds 或 _bytes 这样的单位后缀
   - C) 相较于通常使用基本单位的约定，优先使用 camelCase 和毫秒单位
   - D) 使用 _total 标识累积计数器

<details>
<summary>显示答案</summary>

**答案：C**

优先使用描述性、以下划线分隔的名称和基本单位。_total 是计数器标记，不是物理单位。node_memory_MemAvailable_bytes 等现有导出器 API 应保留其已发布的拼写。

</details>

6. 关于 Prometheus 保留期，哪项说法正确？

   - A) 保留期绝不可能超过 30 天
   - B) 未显式设置时间/容量保留选项时，默认保留期为 15 天；更长的保留期需要合适的配置和容量
   - C) 它不会压缩本地数据
   - D) 没有 Mimir 就不可能使用独立的采集副本

<details>
<summary>显示答案</summary>

**答案：B**

默认保留期不是上限。本地 TSDB 并非具备复制能力的分布式存储；采集冗余、查询去重、持久性和恢复是需要单独设计的事项。

</details>

7. 以下哪项关于产品/存储的说法不正确？

   - A) VictoriaMetrics 单节点和集群部署的运维要求不同
   - B) 传统 CloudWatch 指标分辨率会随着数据变旧而变粗
   - C) Mimir 对象存储可保证无限扩展，并消除所有本地存储需求
   - D) Datadog 指标使用查询汇总，因此保留期并不能保证每个图表都保留原始分辨率

<details>
<summary>显示答案</summary>

**答案：C**

对象存储是 Mimir 架构的一部分，并不意味着容量无限。摄取/本地资源、查询限制、复制和运维容量仍然重要。不要将备份目标或特定版本的功能与产品的主要存储混为一谈。

</details>

8. 以下哪种做法无法控制指标基数？

   - A) 使用规范化的路由模板
   - B) 避免将用户/会话 ID 用作普通标签
   - C) 在可以接受细节丢失时对状态码进行分组
   - D) 为每个请求分配一个新的 request_id 标签值

<details>
<summary>显示答案</summary>

**答案：D**

不同的标签值会创建不同的序列，即使这些值经过哈希处理也是如此。必要时，请求专属的上下文应放在受到适当控制的日志/trace 中。基数和敏感数据暴露都需要审查。

</details>

9. 哪项 Kubernetes 指标职责匹配正确？

   - A) node-exporter：Kubernetes API 对象状态
   - B) kube-state-metrics：测量容器 CPU 使用量
   - C) cAdvisor/kubelet 指标：容器资源测量值
   - D) metrics-server：长期 Prometheus TSDB

<details>
<summary>显示答案</summary>

**答案：C**

node-exporter 报告主机操作系统指标；kube-state-metrics 暴露 API 对象状态；metrics-server 提供 Resource Metrics API。Prometheus/vmalert/Mimir 规则会评估告警，而 Alertmanager 会对告警进行路由。vmagent 是采集器/转发器，不是可查询的 TSDB。

</details>

10. 怎样的成本比较才便于审查？

   - A) 只依据团队规模对产品进行排名
   - B) 只列出节点数量，却不说明采样间隔或功能假设
   - C) 提供实测序列/样本量、保留期/分辨率、高可用/查询要求，以及所选功能的当前定价
   - D) 假设指标名称/值的长度永远无关紧要

<details>
<summary>显示答案</summary>

**答案：C**

每 15 秒采集一次的 100 万个实际导出序列，在 30 天内意味着 1,728 亿个样本（尚未扣除传输过滤/去重）。基础设施、索引/WAL、副本、查询工作量、自定义指标配额和运维工作量都会影响成本。这是工作负载计算，不是服务商报价。

</details>

[返回指南](../../../observability/metrics/README.md)
