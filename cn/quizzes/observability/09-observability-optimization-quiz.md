# 可观测性优化测验

> **已验证的示例版本**：Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **最后更新**：2026年9月13日

本测验用于检验你对 EKS 可观测性优化指南的理解。内容涵盖可观测性的三大支柱（日志、指标和追踪），以及基于 eBPF 的监控和成本优化策略。

---

## 选择题

1. 在可观测性的三大支柱中，哪种数据类型最适合回答“为什么这么慢？”这个问题？
   - A) 日志
   - B) 指标
   - C) 追踪
   - D) 事件

<details>
<summary>查看答案</summary>

**答案：C) 追踪**

**说明：**
可观测性的三大支柱分别回答不同类型的问题。日志回答“发生了什么？”，指标回答“系统是否健康？”，追踪回答“为什么这么慢？”。追踪针对跟踪请求流进行了优化，能够帮助理解因果关系并分析瓶颈。在分布式系统中，分析经过多个服务的请求延迟时，追踪至关重要。

</details>

2. 哪种日志存储解决方案擅长基于标签快速筛选，并通过使用对象存储（S3）实现较高的成本效益？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>查看答案</summary>

**答案：C) Loki**

**说明：**
Loki 使用标签索引和对象存储，但总成本还包括计算、缓存、对象请求、查询和运维。应在相同的 Region、数据量、保留期和可用性要求下进行比较，而不要将 S3 存储价格视为总成本。

</details>

3. 哪种基于 C 的代理可以在 EKS 上采集日志？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>查看答案</summary>

**答案：B) Fluent Bit**

**说明：**
Fluent Bit 是一种基于 C 的采集器，可用于 AWS 部署。其内存用量和吞吐量取决于版本、解析器、记录大小、缓冲和硬件；固定的 15 MB 或 200K msg/s 说法并非保证值。

</details>

4. Prometheus 中造成基数爆炸的主要原因是什么？
   - A) 抓取间隔过长
   - B) 将 Pod UID 或时间戳用作标签
   - C) 使用过多 Recording Rules
   - D) 启用 Remote Write

<details>
<summary>查看答案</summary>

**答案：B) 将 Pod UID 或时间戳用作标签**

**说明：**
不断变化的请求 ID/时间戳标签会增加时间序列数量。应在源头限制标签，并验证其唯一性。labeldrop 不会聚合样本，还可能导致冲突；目标重标记和指标重标记是在不同阶段执行的。

</details>

5. 在 OpenTelemetry Collector 的 Tail Sampling 策略中，哪种策略类型会选择包含 ERROR span 的已接收追踪？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>查看答案</summary>

**答案：C) status_code**

**说明：**
ERROR status_code 策略会根据该采样器收到的错误 span 来选择追踪。追踪亲和性、决策时间、缓冲区限制、迟到的 span 和上游头部采样都会影响结果，因此无法保证保留每个失败请求。

</details>

6. 基于 eBPF 的监控最大的优势是什么？
   - A) 可以采集更多类型的指标
   - B) 无需修改代码即可为应用插桩
   - C) 可以降低指标存储成本
   - D) 可以提升查询性能

<details>
<summary>查看答案</summary>

**答案：B) 无需修改代码即可为应用插桩**

**说明：**
对于受支持的内核、运行时和协议，它可以减少对源代码的修改，但并非对所有语言、TLS 库或业务 span 都能提供同等覆盖。应验证所需权限、开销和敏感负载；SDK 自动插桩同样可以避免修改源代码。

</details>

7. Cilium Hubble 的主要用途是什么？
   - A) 监控容器资源使用情况
   - B) 观察和分析网络流量
   - C) 日志采集和存储
   - D) 分布式追踪后端

<details>
<summary>查看答案</summary>

**答案：B) 观察和分析网络流量**

**说明：**
Hubble 可在兼容的 Cilium 部署中观察网络流量。L7 可见性取决于协议以及代理/策略配置。应验证实际覆盖范围，而不是承诺能够观察每个流量或提供完整的应用追踪。

</details>

8. Kepler（Kubernetes Efficient Power Level Exporter）主要测量什么指标？
   - A) CPU 温度
   - B) 网络带宽
   - C) 能量（焦耳）和功率（瓦特）
   - D) 磁盘 I/O 延迟

<details>
<summary>查看答案</summary>

**答案：C) 能量（焦耳）和功率（瓦特）**

**说明：**
Kepler 0.10+ 与旧版 0.7 不同。在 0.11.4 中，kepler_pod_cpu_watts 是功率仪表，而 rate(kepler_pod_cpu_joules_total[5m]) 的单位是 J/s=W。乘以 1000 即可得到毫瓦。应验证硬件访问和归因支持情况。

</details>

9. 在 OpenCost/KubeCost 中，推荐采用什么方法跟踪各团队的成本？
   - A) 为每个团队创建独立的 Kubernetes 集群
   - B) 在命名空间和 Pod 上统一使用 cost-center、team 等标签
   - C) 为每个团队分配独立的 AWS 账户
   - D) 仅设置 ResourceQuotas

<details>
<summary>查看答案</summary>

**答案：B) 在命名空间和 Pod 上统一使用 cost-center、team 等标签**

**说明：**
OpenCost 根据 Kubernetes 标签分摊成本。通过在命名空间和 Pod 上一致地应用 `cost-center`、`team` 和 `environment` 等标签，可以使用 `aggregate=label:team` 通过 OpenCost API 查询各团队的成本。这种方法无需更改现有集群结构，即可进行详细的成本分析和费用分摊。

</details>

10. 在基于 SLO（服务等级目标）的监控中，“错误预算”是什么意思？
    - A) 分配给监控系统运维的预算
    - B) 偏离 SLO 目标时允许出现的错误量
    - C) 发送告警的成本
    - D) 可用于日志存储的容量

<details>
<summary>查看答案</summary>

**答案：B) 偏离 SLO 目标时允许出现的错误量**

**说明：**
对于基于请求的 99.9% SLO，在定义的时间窗口内，允许的错误请求数等于总请求数×0.001。不要将其与基于时间的停机时长混淆。要计算剩余的 30 天预算，需要使用按请求加权的 30 天错误率，而不是最近五分钟的错误率。

</details>

---

## 简答题

1. Prometheus 中哪项功能可以通过预先计算并存储复杂查询来提升仪表板查询性能？

<details>
<summary>查看答案</summary>

**答案：** Recording Rules

**说明：**
Recording Rules 会定期评估 PromQL 表达式，并将结果存储为新的时间序列。例如，使用 `record: node:cpu_utilization:ratio` 预先计算节点 CPU 利用率后，仪表板便可直接查询该指标，而不必执行复杂查询，从而加快响应速度。它们通过 PrometheusRule CRD 中的 `record` 字段定义。

</details>

2. 在 OpenTelemetry 中，哪种采样方法会在一个决策时间窗口内收集 span，并根据观察到的结果进行采样？

<details>
<summary>查看答案</summary>

**答案：** Tail Sampling

**说明：**
默认情况下，基于追踪完整性的采样会根据其决策时间窗口内收到的 span 作出决定。它无法证明所有 span 均已完成或到达；应考虑亲和性、缓冲区、迟到的 span、重启和上游采样。

</details>

3. Prometheus 中哪项功能可以将追踪 ID 与指标数据点关联起来，从而支持从指标直接跳转到追踪？

<details>
<summary>查看答案</summary>

**答案：** Exemplars

**说明：**
Exemplars 是一项可将额外上下文（通常为 traceID）附加到指标样本上的功能。将 Exemplars 添加到直方图或计数器指标后，就可以在 Grafana 中点击指标图表上的特定点，直接跳转到对应时间的追踪。这有助于关联分析可观测性数据，让你能够在追踪中分析“为什么延迟在这个时间点突然升高”。

</details>

4. 在 VictoriaMetrics 集群模式中，负责存储指标数据的组件叫什么？

<details>
<summary>查看答案</summary>

**答案：** vmstorage

**说明：**
vmstorage 负责存储数据。仅仅运行多个实例并不能实现复制：还需配置复制因子、vminsert/vmselect 行为、查询去重和故障处理。

</details>

5. 将较旧的数据迁移到 S3 Glacier 等低成本存储，以降低日志/指标存储成本的策略叫什么？

<details>
<summary>查看答案</summary>

**答案：** 分层存储

**说明：**
分层取决于访问频率、恢复延迟和保留要求。将活跃的 Loki/Tempo 块迁移到 Glacier 可能会导致查询失败；应验证兼容性和恢复能力，或使用单独的归档存储。节省比例并非固定值。

</details>

---

## 实操题

1. 编写一个 Fluent Bit 配置，用于筛除并排除 DEBUG 和 TRACE 级别的日志。

<details>
<summary>查看答案</summary>

**答案：**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**说明：**
应在经过解析的 level 字段上匹配 ^(DEBUG|TRACE)$，而不是匹配任意消息文本。应衡量日志丢弃量及其对事件调查的影响；节省 40–60% 的成本并非保证值。

</details>

2. 编写一个 PrometheusRule，当每个服务的 HTTP 错误率超过 5% 并持续 5 分钟时触发警告。

<details>
<summary>查看答案</summary>

**答案：**
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

**说明：**
此告警规则会计算每个服务的 5XX 状态码比例。`status=~"5.."` 是一个匹配 500–599 状态码的正则表达式。`for: 5m` 表示只有当条件持续 5 分钟时才触发告警，从而避免因暂时性峰值产生误报。使用 `sum by (service)` 可以为每个服务分别生成告警。

</details>

3. 为 OpenTelemetry Collector 编写一个 tail_sampling 处理器配置，使错误追踪的采样率为 100%、延迟超过 1 秒的追踪采样率为 100%，其余追踪的采样率仅为 10%。

<details>
<summary>查看答案</summary>

**答案：**
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

**说明：**
这些正向策略会保留符合条件的已接收错误/慢请求追踪，并对其余追踪进行概率采样。缓冲区、亲和性和迟到的 span 仍有限制。总体保留率取决于错误/慢请求所占比例，无法保证减少 90%。不要将“优先匹配”语义泛化到 drop/composite 策略。

</details>

---

## 进阶题

1. 为大型 EKS 集群（500+ 个节点）设计一种实现可观测性技术栈高可用的架构。说明采集、存储和查询各层应部署哪些组件，以及如何部署。

<details>
<summary>查看答案</summary>

**答案：**

不要仅根据节点数量推算副本数。应分离节点日志代理和网关，并按追踪 ID 路由 Tail Sampling，同时衡量缓冲、背压和丢弃情况。遵循当前 Loki/Tempo 模式的复制、仲裁和可用区要求；配置 VictoriaMetrics 复制和查询去重，并考虑 AMP 配额和保留期。为 Prometheus 副本数×分片数预留 PVC/内存，并合并分片查询。Grafana 需要共享数据库，并单独配置 Alerting 高可用；还应确认所用版本是否支持查询缓存。PDB 和 S3 持久性并不能保证端到端可用性；应测试故障和恢复。

</details>

2. 在每月可观测性成本为 $5,000 的环境中，提出在保持质量的同时实现 50% 成本削减的优化策略。请分别说明日志、指标和追踪领域的具体方法。

<details>
<summary>查看答案</summary>

**答案：**

$5,000 的基准成本和 50% 的目标仅为假设值。优化之前，应先按摄取、存储、扫描、计算和运维成本进行归因，确定成本最高的类别。分别试行按解析后的级别筛选、按请求进行概率采样、安全地减少指标/桶、Tail Sampling 和调整保留期。限流不等于 10% 采样，Recording Rules 也不会改变原始数据的保留期。在相同 Region、可用性、查询和保留要求下比较完整成本。各项节省可能重叠；应评估实际账单、数据丢失、SLO 覆盖和调查成效，而不是简单相加各项百分比。如果无法确认目标是否达成，应报告证据和下一项实验。

</details>

---

**分数计算：**
- 答对 18–20 题：优秀（可观测性专家水平）
- 答对 14–17 题：良好（具备实践应用能力）
- 答对 10–13 题：一般（建议进一步学习）
- 答对 6–9 题：基础（复习基本概念）
- 答对 0–5 题：不足（需要全面复习内容）

---

**相关学习材料：**
- [EKS 可观测性优化指南](../../observability/09-observability-optimization.md)
