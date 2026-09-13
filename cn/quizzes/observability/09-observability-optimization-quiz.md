# 可观测性优化测验

> **已验证的示例版本**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **最后更新**: September 13, 2026

本测验用于检验你对 EKS 可观测性优化指南的理解。内容涵盖可观测性的三大支柱——日志、指标和追踪——以及基于 eBPF 的监控和成本优化策略。

---

## 多项选择题

1. 在可观测性的三大支柱中，哪种数据类型最适合回答“为什么这么慢？”这个问题？
   - A) 日志
   - B) 指标
   - C) 追踪
   - D) 事件

<details>
<summary>查看答案</summary>

**答案: C) 追踪**

**说明:**
可观测性的三大支柱回答不同类型的问题。日志回答“发生了什么？”，指标回答“系统是否健康？”，而追踪回答“为什么这么慢？”。追踪经过优化，可用于跟踪请求流以理解因果关系并分析瓶颈。在分布式系统中，分析跨越多个 Service 的请求延迟时，追踪至关重要。

</details>

2. 哪种日志存储解决方案擅长基于标签进行快速过滤，并通过使用对象存储（S3）实现高成本效益？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>查看答案</summary>

**答案: C) Loki**

**说明:**
Loki 使用标签索引和对象存储，但总成本包括计算、缓存、对象请求、查询和运维。请在相同 Region、数据量、保留期和可用性条件下进行比较，而不要将 S3 存储价格视为总成本。

</details>

3. 哪种基于 C 的 Agent 可以在 EKS 上收集日志？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>查看答案</summary>

**答案: B) Fluent Bit**

**说明:**
Fluent Bit 是可用于 AWS 部署的基于 C 的收集器。内存和吞吐量取决于版本、解析器、记录大小、缓冲和硬件；固定的 15 MB 或 200K msg/s 声明并非保证。

</details>

4. Prometheus 中基数爆炸的主要原因是什么？
   - A) scrape 间隔过长
   - B) 使用 Pod UID 或时间戳作为标签
   - C) 使用过多 Recording Rules
   - D) 启用 Remote Write

<details>
<summary>查看答案</summary>

**答案: B) 使用 Pod UID 或时间戳作为标签**

**说明:**
会变化的 request-ID/时间戳标签会增加时间序列数量。应在源头限制标签并验证唯一性。labeldrop 不会聚合样本，且可能造成冲突；target relabeling 和 metric relabeling 在不同阶段运行。

</details>

5. 在 OpenTelemetry Collector 的 Tail Sampling 策略中，哪种策略类型会选择包含 ERROR span 的已接收 trace？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>查看答案</summary>

**答案: C) status_code**

**说明:**
ERROR status_code 策略使用该采样器接收到的错误 span 来选择 trace。Trace 亲和性、决策时机、缓冲区限制、延迟到达的 span 和上游 head sampling 会使“保留每个失败请求”无法得到保证。

</details>

6. 基于 eBPF 的监控最大的优势是什么？
   - A) 可以收集更多类型的指标
   - B) 可以在不修改代码的情况下为应用程序添加插桩
   - C) 可以降低指标存储成本
   - D) 可以提高查询性能

<details>
<summary>查看答案</summary>

**答案: B) 可以在不修改代码的情况下为应用程序添加插桩**

**说明:**
对于受支持的内核、运行时和协议，它可以减少源代码变更，但并不能同等覆盖每种语言、TLS 库或业务 span。请验证权限、开销和敏感负载；SDK 自动插桩也可能避免源代码变更。

</details>

7. Cilium Hubble 的主要用途是什么？
   - A) 容器资源使用情况监控
   - B) 网络流量观测和分析
   - C) 日志收集和存储
   - D) 分布式追踪后端

<details>
<summary>查看答案</summary>

**答案: B) 网络流量观测和分析**

**说明:**
Hubble 在兼容的 Cilium 部署中观测网络流量。L7 可见性取决于协议和 proxy/policy 配置。应验证实际覆盖范围，而不是承诺涵盖每个流量或提供完整的应用程序追踪。

</details>

8. Kepler (Kubernetes Efficient Power Level Exporter) 测量的主要指标是什么？
   - A) CPU 温度
   - B) 网络带宽
   - C) 能量（焦耳）和功率（瓦特）
   - D) 磁盘 I/O 延迟

<details>
<summary>查看答案</summary>

**答案: C) 能量（焦耳）和功率（瓦特）**

**说明:**
Kepler 0.10+ 与旧版 0.7 不同。在 0.11.4 中，kepler_pod_cpu_watts 是功率 gauge，而 rate(kepler_pod_cpu_joules_total[5m]) 是 J/s=W。乘以 1000 可得到毫瓦。请验证硬件访问和归因支持。

</details>

9. 在 OpenCost/KubeCost 中，按团队跟踪成本的推荐方法是什么？
   - A) 为每个团队创建单独的 Kubernetes 集群
   - B) 在 namespace 和 Pod 上标准化使用 cost-center 和 team 等标签
   - C) 为每个团队分配单独的 AWS 账户
   - D) 仅设置 ResourceQuotas

<details>
<summary>查看答案</summary>

**答案: B) 在 namespace 和 Pod 上标准化使用 cost-center 和 team 等标签**

**说明:**
OpenCost 根据 Kubernetes 标签分摊成本。通过将 `cost-center`、`team` 和 `environment` 等标签一致地应用于 namespace 和 Pod，你可以使用 `aggregate=label:team` 通过 OpenCost API 按团队查询成本。这种方法能够实现详细的成本分析和内部计费，同时保持现有集群结构。

</details>

10. 在基于 SLO (Service Level Objective) 的监控中，“Error Budget”是什么意思？
    - A) 为监控系统运维分配的预算
    - B) 在偏离 SLO 目标时允许的错误量
    - C) 发送告警的成本
    - D) 可用于日志存储的存储容量

<details>
<summary>查看答案</summary>

**答案: B) 在偏离 SLO 目标时允许的错误量**

**说明:**
对于基于请求的 99.9% SLO，在定义的时间窗口内，允许的失败请求数等于总请求数×0.001。不要将其与基于时间的停机时间混淆。剩余的 30 天预算需要基于 30 天、按请求加权的错误比率，而非最近五分钟的比率。

</details>

---

## 简答题

1. Prometheus 中通过预先计算和存储复杂查询来提高仪表板查询性能的功能叫什么？

<details>
<summary>查看答案</summary>

**答案:** Recording Rules

**说明:**
Recording Rules 会定期评估 PromQL 表达式，并将结果存储为新的时间序列。例如，使用 `record: node:cpu_utilization:ratio` 预先计算节点 CPU 利用率后，仪表板可以直接查询此指标，而无需运行复杂查询，从而获得更快的响应。它们使用 PrometheusRule CRD 中的 `record` 字段定义。

</details>

2. 在 OpenTelemetry 中，收集一个决策窗口内的 span 并使用观测到的结果进行采样的方法叫什么？

<details>
<summary>查看答案</summary>

**答案:** Tail Sampling

**说明:**
默认的完整 trace 采样根据其决策窗口内收到的 span 作出决定。它无法证明所有 span 都已完成或到达；请考虑亲和性、缓冲区、延迟到达的 span、重启和上游采样。

</details>

3. Prometheus 中将 trace ID 链接到指标数据点、从而可直接从指标跳转到 trace 的功能是什么？

<details>
<summary>查看答案</summary>

**答案:** Exemplars

**说明:**
Exemplars 是一种将额外上下文（通常是 traceID）附加到指标样本的功能。当向直方图或计数器指标添加 exemplars 时，你可以在 Grafana 中点击指标图上的特定点，直接跳转到该时间点的 trace。这有助于在可观测性数据之间进行关联分析，让你能够在 trace 中分析“为什么此时延迟突然升高”。

</details>

4. 在 VictoriaMetrics cluster mode 中，负责指标数据存储的组件叫什么？

<details>
<summary>查看答案</summary>

**答案:** vmstorage

**说明:**
vmstorage 存储数据。仅部署多个实例并不能建立复制：还需配置复制因子、vminsert/vmselect 行为、查询去重和故障处理。

</details>

5. 通过将较旧数据移动到 S3 Glacier 等低成本存储来降低日志/指标存储成本的策略叫什么？

<details>
<summary>查看答案</summary>

**答案:** Tiered Storage

**说明:**
分层取决于访问频率、恢复延迟和保留期。将活跃的 Loki/Tempo block 移入 Glacier 可能导致查询失效；请验证兼容性/恢复能力，或使用单独的归档。节省并非固定百分比。

</details>

---

## 实操题

1. 编写一个 Fluent Bit 配置，用于过滤并排除 DEBUG 和 TRACE 级别的日志。

<details>
<summary>查看答案</summary>

**答案:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**说明:**
应在已解析的 level 字段上匹配 ^(DEBUG|TRACE)$，而非任意消息文本。请衡量丢弃情况及其对事件调查的影响；无法保证节省 40–60%。

</details>

2. 编写一个 PrometheusRule：当每个 Service 的 HTTP 错误率超过 5% 且持续 5 分钟时触发 warning。

<details>
<summary>查看答案</summary>

**答案:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
spec:
  groups:
    - name: slo.alerts
      rules:
        - alert: HighHTTPErrorRate
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "HTTP error rate for service {{ $labels.service }} exceeded 5%"
            description: "Current error rate: {{ $value | humanizePercentage }}"
```

**说明:**
此告警规则会计算每个 Service 的 5XX 状态码比率。`status=~"5.."` 是匹配 500-599 状态码的正则表达式。`for: 5m` 仅在条件持续 5 分钟时触发告警，从而避免临时峰值导致的误报。使用 `sum by (service)` 会为每个 Service 生成独立告警。

</details>

3. 为 OpenTelemetry Collector 编写一个 tail_sampling processor 配置：以 100% 的比例采样错误 trace，以 100% 的比例采样延迟超过 1 秒的 trace，其余仅以 10% 的比例采样。

<details>
<summary>查看答案</summary>

**答案:**
```yaml
processors:
  tail_sampling:
    decision_wait: 2s
    num_traces: 1000
    maximum_trace_size_bytes: 1048576
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 1000
    - name: baseline
      type: probabilistic
      probabilistic:
        sampling_percentage: 10
```

**说明:**
这些正向策略会保留匹配的已接收错误/慢 trace，并对其余 trace 进行概率采样。缓冲区、亲和性和延迟 span 限制仍然存在。总体保留率取决于错误/慢 trace 的占比；无法保证减少 90%。不要将首个匹配的语义泛化到 drop/composite 策略。

</details>

---

## 高级题

1. 为大型 EKS 集群（500+ 节点）设计一个实现可观测性栈高可用性的架构。说明每一层应部署哪些组件及其部署方式：收集、存储和查询。

<details>
<summary>查看答案</summary>

**答案:**

不要仅根据节点数量推导副本数量。应分离节点日志 Agent 和 gateway，按 trace ID 路由 Tail Sampling，并测量缓冲/背压和丢弃情况。遵循当前 Loki/Tempo mode 的复制、quorum/AZ 要求；配置 VictoriaMetrics 的复制/查询去重以及 AMP 配额/保留期。为 Prometheus 副本×shard 的 PVC/内存做预算，并合并 shard 查询。Grafana 需要共享 DB 和独立的 Alerting HA；请验证版本对查询缓存的支持。PDB 和 S3 持久性并不能保证端到端可用性；应测试故障和恢复。

</details>

2. 在每月可观测性成本为 $5,000 的环境中，提出在保持质量的同时实现 50% 成本降低的优化策略。说明日志、指标和追踪各领域的具体方法。

<details>
<summary>查看答案</summary>

**答案:**

$5,000 基线和 50% 目标均为假设。应先归因于摄取、存储、扫描、计算和运维成本，再优化最大类别。分别试验已解析级别过滤、请求级概率采样、安全的指标/bucket 缩减、Tail Sampling 和保留期。限流并不是 10% 采样器，Recording Rules 也不会改变原始数据保留期。请在相同 Region、可用性、查询和保留期要求下比较完整成本。节省会重叠；不要叠加百分比，而应评估账单、数据丢失、SLO 覆盖率和调查成功率。如果目标尚未确立，请报告证据和下一项实验。

</details>

---

**评分计算:**
- 18-20 个正确答案：优秀（可观测性专家级）
- 14-17 个正确答案：良好（可应用于实践）
- 10-13 个正确答案：一般（建议进一步学习）
- 6-9 个正确答案：基础（复习基本概念）
- 0-5 个正确答案：不足（需要完整复习内容）

---

**相关学习资料:**
- [EKS 可观测性优化指南](../../observability/09-observability-optimization.md)
