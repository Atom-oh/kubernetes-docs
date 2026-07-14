# 可观测性优化测验

> **支持的版本**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **最后更新**: February 22, 2026

本测验旨在测试你对 EKS 可观测性优化指南的理解。内容涵盖可观测性的三大支柱——日志、指标和追踪，以及基于 eBPF 的监控和成本优化策略。

---

## 选择题

1. 在可观测性的三大支柱中，哪种数据类型最适合回答“为什么这么慢？”这个问题？
   - A) 日志
   - B) 指标
   - C) 追踪
   - D) 事件

<details>
<summary>查看答案</summary>

**答案: C) 追踪**

**说明:**
可观测性的三大支柱回答不同类型的问题。日志回答“发生了什么？”，指标回答“系统是否健康？”，而追踪回答“为什么这么慢？”。追踪经过优化，适用于跟踪请求流以理解因果关系并分析瓶颈。在分布式系统中，分析跨越多个 Service 的请求延迟时，追踪至关重要。

</details>

2. 哪种日志存储解决方案擅长基于标签的快速筛选，并通过使用对象存储（S3）实现高成本效率？
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>查看答案</summary>

**答案: C) Loki**

**说明:**
Grafana Loki 使用基于标签的索引，在不依赖全文搜索索引的情况下提供快速筛选。它将日志数据存储在 S3 等对象存储中，使存储成本非常低（S3: $0.023/GB/月）。OpenSearch 擅长全文搜索，但索引存储成本较高；CloudWatch Logs 的数据摄取成本则相对较高（$0.50/GB）。

</details>

3. 哪种日志 Agent 的内存使用量最低、使用 C 编写，并且受到 EKS 原生支持？
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>查看答案</summary>

**答案: B) Fluent Bit**

**说明:**
Fluent Bit 使用 C 编写，内存仅使用约 15MB。它比 Fluentd（约 60MB，Ruby/C）或 Vector（约 30MB，Rust）更轻量，并可提供最高约 200K msg/s 的高吞吐量。AWS 官方推荐 Fluent Bit 作为 EKS 的日志收集器，并提供 aws-for-fluent-bit 镜像。

</details>

4. Prometheus 中基数爆炸的主要原因是什么？
   - A) scrape 间隔过长
   - B) 使用 Pod UID 或时间戳作为标签
   - C) 使用过多的 Recording Rules
   - D) 启用 Remote Write

<details>
<summary>查看答案</summary>

**答案: B) 使用 Pod UID 或时间戳作为标签**

**说明:**
基数是指唯一时间序列的数量。将 Pod UID、时间戳或请求 ID 等唯一值用作标签，会使标签组合无限增长，导致时间序列爆炸。这会造成 Prometheus 内存使用量激增并降低查询性能。建议在 relabel_configs 中移除 pod_template_hash 和 controller_revision_hash 等标签。

</details>

5. 在 OpenTelemetry Collector 的 Tail Sampling 策略中，哪种 policy 类型会保留 100% 包含错误的追踪？
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>查看答案</summary>

**答案: C) status_code**

**说明:**
Tail Sampling 在追踪完成后基于完整的追踪信息做出采样决策。`status_code` policy 根据追踪的状态代码（OK、ERROR）进行采样。设置 `status_codes: [ERROR]` 会保留 100% 包含错误的追踪。这是一种有效策略，既能保留对问题分析重要的追踪，又能减少总体数据量。

</details>

6. 基于 eBPF 的监控最大的优势是什么？
   - A) 可以收集更多类型的指标
   - B) 无需修改代码即可对应用程序进行插桩
   - C) 降低指标存储成本
   - D) 提升查询性能

<details>
<summary>查看答案</summary>

**答案: B) 无需修改代码即可对应用程序进行插桩**

**说明:**
eBPF（extended Berkeley Packet Filter）可在 Linux 内核中安全地运行程序，以观测系统调用、网络数据包等。传统插桩需要添加 SDK、修改代码并重新部署，而 eBPF 在内核级别透明运行，可在不更改应用程序的情况下实现监控。它也与编程语言无关，能够同样地对任意语言编写的应用程序进行插桩。

</details>

7. Cilium Hubble 的主要用途是什么？
   - A) Container 资源使用情况监控
   - B) 网络流量观测与分析
   - C) 日志收集与存储
   - D) 分布式追踪后端

<details>
<summary>查看答案</summary>

**答案: B) 网络流量观测与分析**

**说明:**
Cilium Hubble 是 Cilium 的可观测性组件，Cilium 是一个基于 eBPF 的 CNI。Hubble 实时观测集群中的所有网络流量，分析 DNS 请求、TCP 连接、HTTP 流量等。通过 `hubble observe` 命令，你可以筛选特定 Service 的流量或分析被丢弃的数据包。它可用于 Service Map 可视化和网络策略验证。

</details>

8. Kepler（Kubernetes Efficient Power Level Exporter）主要测量的指标是什么？
   - A) CPU 温度
   - B) 网络带宽
   - C) 能源消耗（焦耳/瓦特）
   - D) 磁盘 I/O 延迟

<details>
<summary>查看答案</summary>

**答案: C) 能源消耗（焦耳/瓦特）**

**说明:**
Kepler 是一个使用 eBPF 测量 Container 和 Pod 能源消耗的 CNCF 项目。它通过 `kepler_container_joules_total` 指标提供能源消耗（焦耳），并可使用 `rate(kepler_container_joules_total[5m]) * 1000` 计算功耗（瓦特）。这使得可以按 namespace 或 Pod 分析能源使用情况，从而帮助实现绿色计算目标。

</details>

9. 在 OpenCost/KubeCost 中按团队跟踪成本的推荐方法是什么？
   - A) 为每个团队创建单独的 Kubernetes 集群
   - B) 在 namespace 和 Pod 上标准化使用 cost-center 和 team 等标签
   - C) 为每个团队分配单独的 AWS 账户
   - D) 只设置 ResourceQuotas

<details>
<summary>查看答案</summary>

**答案: B) 在 namespace 和 Pod 上标准化使用 cost-center 和 team 等标签**

**说明:**
OpenCost 基于 Kubernetes 标签分配成本。通过在 namespace 和 Pod 上一致地应用 `cost-center`、`team` 和 `environment` 等标签，你可以使用 `aggregate=label:team` 通过 OpenCost API 查询每个团队的成本。该方法在维持现有集群结构的同时，支持精细的成本分析和成本分摊。

</details>

10. 在基于 SLO（Service Level Objective）的监控中，“Error Budget”是什么意思？
    - A) 为监控系统运行分配的预算
    - B) 偏离 SLO 目标时允许的错误量
    - C) 发送告警的成本
    - D) 可用于日志存储的存储容量

<details>
<summary>查看答案</summary>

**答案: B) 偏离 SLO 目标时允许的错误量**

**说明:**
Error Budget 是从 SLO 派生的概念，表示允许的错误总量。例如，99.9% 可用性的 SLO 意味着 0.1% 的 Error Budget。以 30 天为基准，允许约 43 分钟的停机时间。当 Error Budget 耗尽时，应暂停新功能部署，专注于提升稳定性。剩余 Error Budget 比例可使用表达式 `1 - (1 - sli:availability:ratio) / (1 - 0.999)` 计算。

</details>

---

## 简答题

1. Prometheus 中通过预先计算并存储复杂查询来提高仪表板查询性能的功能名称是什么？

<details>
<summary>查看答案</summary>

**答案:** Recording Rules

**说明:**
Recording Rules 会定期计算 PromQL 表达式，并将结果存储为新的时间序列。例如，使用 `record: node:cpu_utilization:ratio` 预先计算节点 CPU 利用率，可让仪表板直接查询该指标而非运行复杂查询，从而获得更快的响应。它们使用 PrometheusRule CRD 中的 `record` 字段定义。

</details>

2. 在 OpenTelemetry 中，在追踪完成后基于完整追踪信息做出采样决策的采样方法称为什么？

<details>
<summary>查看答案</summary>

**答案:** Tail Sampling

**说明:**
Tail Sampling 在一个追踪的所有 span 都到达后做出采样决策。这与 Head Sampling（概率采样）不同，后者在追踪开始时做出决策。Tail Sampling 的优势在于可以选择性地只保留包含错误或高延迟的追踪。但是，由于做出决策前必须将所有 span 保留在内存中，因此 `decision_wait` 和 `num_traces` 设置非常重要。

</details>

3. Prometheus 中将 trace ID 关联到指标数据点，从而支持从指标直接导航到追踪的功能是什么？

<details>
<summary>查看答案</summary>

**答案:** Exemplars

**说明:**
Exemplars 是一种将额外上下文（通常为 traceID）附加到指标样本的功能。当将 exemplars 添加到直方图或计数器指标时，你可以在 Grafana 中点击指标图上的特定点，直接导航到该时刻的追踪。这有助于对可观测性数据进行关联分析，使你能够在追踪中分析“为什么此时延迟会激增”。

</details>

4. 在 VictoriaMetrics cluster mode 中，负责指标数据存储的组件名称是什么？

<details>
<summary>查看答案</summary>

**答案:** vmstorage

**说明:**
VictoriaMetrics cluster mode 由三个组件构成。vminsert 负责指标收集和分发，vmselect 负责查询处理，vmstorage 负责实际的指标数据存储。vmstorage 可以通过多个实例进行水平扩展，并通过复制提供高可用性。这种分离式架构使数据摄取、存储和查询工作负载能够独立扩展。

</details>

5. 通过将较旧的数据移动到 S3 Glacier 等低成本存储来降低日志/指标存储成本的策略称为什么？

<details>
<summary>查看答案</summary>

**答案:** Tiered Storage

**说明:**
分层存储策略根据数据的重要性和访问频率将数据存储在不同的存储层级中。近期数据存储在高性能存储（SSD、EBS）中，中期数据存储在 S3 Standard-IA 中，长期归档数据存储在 S3 Glacier Deep Archive 中。这可将存储成本降低 70-90%。基于对象存储的解决方案（如 Loki 和 Tempo）默认支持此策略。

</details>

---

## 动手实践题

1. 编写一个 Fluent Bit 配置，用于筛选并排除 DEBUG 和 TRACE 级别的日志。

<details>
<summary>查看答案</summary>

**答案:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$
```

或者使用正则表达式：
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log (DEBUG|TRACE)
```

**说明:**
Fluent Bit 的 grep filter 使用正则表达式来筛选日志。`Exclude` 指令会排除匹配该模式的日志。在生产环境中筛选 DEBUG/TRACE 日志可将日志量减少 40-60%，显著降低存储成本。不过，在需要排查问题时，可以针对特定 Service 选择性启用 DEBUG 日志。

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
此告警规则计算每个 Service 的 5XX 状态代码比例。`status=~"5.."` 是一个匹配 500-599 状态代码的正则表达式。`for: 5m` 仅在条件持续 5 分钟时触发告警，防止由临时峰值导致的误告警。使用 `sum by (service)` 可为每个 Service 生成独立告警。

</details>

3. 为 OpenTelemetry Collector 编写一个 tail_sampling processor 配置：对错误追踪进行 100% 采样、对延迟超过 1 秒的追踪进行 100% 采样，其余追踪仅采样 10%。

<details>
<summary>查看答案</summary>

**答案:**
```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      # Keep 100% of traces with errors
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep 100% of traces with latency over 1 second
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000

      # Sample only 10% of the rest
      - name: default-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

**说明:**
Tail Sampling policies 按顺序评估，只要任一 policy 匹配，便会保留该追踪。`decision_wait` 是等待追踪完成的时间，需要为所有 span 到达预留足够时间。`num_traces` 是可保留在内存中的追踪最大数量。该配置可在保留对错误和性能分析重要的追踪的同时，将总体数据量减少约 90%。

</details>

---

## 高级题

1. 为大型 EKS 集群（500+ 节点）设计一个实现可观测性堆栈高可用性的架构。请说明在采集、存储和查询各层应部署哪些组件以及如何部署。

<details>
<summary>查看答案</summary>

**答案:**

**数据采集层:**
- Fluent Bit：在每个节点上以 DaemonSet 部署（内存限制 100-200Mi）
- OTel Collector：以 DaemonSet 部署，并在前方配置负载均衡器
- Collector 冗余：每个 AZ 至少部署 2+ 个 Collector 实例

**存储层:**
- 日志：Loki Simple Scalable mode
  - 写入路径：2+ 个副本（跨 AZ 分布）
  - 读取路径：2+ 个副本（查询负载均衡）
  - 后端：S3（持久性 99.999999999%）

- 指标：VictoriaMetrics cluster 或 AMP
  - vminsert：2+ 个副本（写入负载均衡）
  - vmstorage：3+ 个副本（复制因子为 2）
  - vmselect：2+ 个副本（读取负载均衡）

- 追踪：Grafana Tempo
  - Distributor：2+ 个副本
  - Ingester：3+ 个副本（启用 WAL）
  - 后端：S3

**查询层:**
- Grafana：2+ 个副本，使用外部 PostgreSQL/MySQL 存储会话
- 缓存：使用 Redis/Memcached 缓存查询结果

**关键注意事项:**
1. 跨多个 AZ 部署所有有状态组件
2. 使用 S3 作为共享存储（消除单点故障）
3. Prometheus 分片（3-5 个 shard）+ Remote Write，将数据卸载到中央存储
4. 使用 PodDisruptionBudget 确保滚动更新期间的可用性

</details>

2. 在每月可观测性成本为 $5,000 的环境中，提出在保持质量的同时实现 50% 成本降低的优化策略。请分别说明日志、指标和追踪各领域的具体方法。

<details>
<summary>查看答案</summary>

**答案:**

**日志优化（预期节省：$1,500-2,000）**

1. **日志级别筛选**（减少 40-60%）
   - 在生产环境中排除 DEBUG/TRACE 日志
   - 实现方式：使用 `Exclude log (DEBUG|TRACE)` 的 Fluent Bit grep filter

2. **应用采样**（减少 30-50%）
   - 对高频日志（访问日志、健康检查）进行 10% 采样
   - 实现方式：Fluent Bit throttle filter `Rate 10, Window 60`

3. **保留期优化**（减少 20-40%）
   - 生产环境：14 天，Dev/Staging：7 天
   - 仅对重要日志进行长期保留（移至 S3 Glacier）

4. **存储迁移**（减少 50-70%）
   - CloudWatch Logs（$0.50/GB 数据摄取）-> Loki + S3（$0.023/GB 存储）

**指标优化（预期节省：$500-800）**

1. **基数管理**
   - 移除不必要的标签（pod_template_hash、controller_revision_hash）
   - 丢弃指标：排除 `go_.*`、`promhttp_.*` 等内部指标

2. **scrape 间隔调整**
   - 关键指标：15s，常规指标：30s-60s
   - 限制直方图 bucket（移除不必要的 le 值）

3. **利用 Recording Rules**
   - 预先计算常用聚合查询
   - 尽早删除原始高分辨率数据（7 天 -> 3 天）

4. **存储迁移**
   - 自托管 Prometheus -> VictoriaMetrics（7 倍压缩率）
   - 或使用 AMP（消除运维负担，成本可预测）

**追踪优化（预期节省：$500-1,000）**

1. **应用 Tail Sampling**（减少 80-90%）
   - 错误/慢速追踪：100% 保留
   - 正常追踪：仅采样 5-10%

2. **存储迁移**
   - X-Ray（$5/百万条追踪）-> Tempo + S3（仅存储成本）

3. **保留期优化**
   - 详细追踪：7 天
   - 聚合数据：30 天

**预期总节省：$2,500-3,800（50-76%）**

关键在于基于重要性的分层。与其同等对待所有数据，不如在保留问题分析所需数据的同时，积极减少数据量。

</details>

---

**评分计算:**
- 答对 18-20 题：优秀（可观测性专家级）
- 答对 14-17 题：良好（可应用于实践）
- 答对 10-13 题：一般（建议进一步学习）
- 答对 6-9 题：基础（复习基本概念）
- 答对 0-5 题：不足（需要全面复习内容）

---

**相关学习材料:**
- [EKS 可观测性优化指南](../../observability/09-observability-optimization.md)
