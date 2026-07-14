# Cilium Service Mesh 可观测性测验

本测验检验你对 Hubble、指标收集、服务地图、Golden Signals 监控和 OpenTelemetry 集成的理解。

## 测验题目

### 1. 以下哪项不是 Hubble 的主要组件？

A. Hubble Observer
B. Hubble Relay
C. Hubble Router
D. Hubble UI

<details>
<summary>显示答案</summary>

**答案：C. Hubble Router**

**解释：**
Hubble 的主要组件包括 Hubble Observer（嵌入在 Cilium Agent 中）、Hubble Relay（集群范围的流量聚合）、Hubble UI（可视化仪表板）和 Hubble CLI（命令行界面）。Hubble Router 不是现有组件。

</details>

### 2. 在 Hubble CLI 中，哪个命令可仅筛选和观察 HTTP 流量？

A. hubble observe --type http
B. hubble observe --protocol http
C. hubble observe --filter http
D. hubble observe --layer http

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --protocol http**

**解释：**
`hubble observe --protocol http` 命令仅筛选 HTTP 协议流量。其他协议（tcp、dns 等）也可以用相同方式筛选。

</details>

### 3. 要在 Prometheus 中收集 Hubble 指标，需要在 values.yaml 中启用哪个设置？

A. hubble.prometheus.enabled: true
B. hubble.metrics.enabled
C. hubble.export.prometheus: true
D. prometheus.hubble: true

<details>
<summary>显示答案</summary>

**答案：B. hubble.metrics.enabled**

**解释：**
要启用 Hubble 指标，请在 hubble.metrics.enabled 下以列表形式指定要收集的指标类型（dns、drop、tcp、flow、http 等）。此外，设置 serviceMonitor.enabled: true 可让 Prometheus Operator 自动抓取。

</details>

### 4. 以下哪项不是监控中的四个 Golden Signals 之一？

A. Latency
B. Traffic
C. Availability
D. Saturation

<details>
<summary>显示答案</summary>

**答案：C. Availability**

**解释：**
Google SRE 定义的四个 Golden Signals 是 Latency、Traffic、Errors 和 Saturation。Availability 不包含在 Golden Signals 中，而是通过 Errors 指标间接衡量。

</details>

### 5. 在 Hubble 中观察被策略拒绝的流量，正确的命令是什么？

A. hubble observe --denied
B. hubble observe --verdict DROPPED
C. hubble observe --blocked
D. hubble observe --policy-denied

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

**解释：**
`--verdict DROPPED` 选项会筛选被网络策略拒绝的流量。相反，`--verdict FORWARDED` 显示被允许的流量。

</details>

### 6. 在 PromQL 查询中，使用哪个函数来衡量 HTTP P99 延迟？

A. avg()
B. histogram_quantile()
C. rate()
D. sum()

<details>
<summary>显示答案</summary>

**答案：B. histogram_quantile()**

**解释：**
P99 延迟等百分位指标使用 histogram_quantile() 函数。例如：`histogram_quantile(0.99, rate(hubble_http_request_duration_seconds_bucket[5m]))`。其中，0.99 表示第 99 个百分位。

</details>

### 7. 以下哪项不是 Hubble UI 提供的主要功能？

A. Service Map
B. Flow Timeline
C. Auto Scaling
D. Namespace Filter

<details>
<summary>显示答案</summary>

**答案：C. Auto Scaling**

**解释：**
Hubble UI 提供服务地图、流量时间线、Namespace 筛选、判定筛选以及单个流量的 L7 详情。Auto Scaling 是工作负载管理功能，而不是可观测性功能。

</details>

### 8. 在 Cilium 中，计算 HTTP 错误率的 PromQL 查询的正确形式是什么？

A. hubble_http_errors_total / hubble_http_requests_total
B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))
C. count(hubble_http_errors) / count(hubble_http_requests)
D. hubble_http_error_rate

<details>
<summary>显示答案</summary>

**答案：B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))**

**解释：**
HTTP 错误率的计算方式是将 5xx 响应数量除以总响应数量。rate() 函数计算每秒速率，status 标签筛选器（status=~"5.."）仅选择服务器错误。

</details>

### 9. 在 Hubble 中，仅观察发往特定服务的流量时使用哪个选项？

A. --destination-service
B. --to-service
C. --target-service
D. --svc

<details>
<summary>显示答案</summary>

**答案：B. --to-service**

**解释：**
`hubble observe --to-service <service-name>` 命令会筛选发往特定服务的流量。相反，`--from-service` 会筛选源自特定服务的流量。

</details>

### 10. 在 Cilium 中，哪个指标监控连接跟踪表利用率？

A. cilium_ct_usage
B. cilium_datapath_conntrack_active
C. cilium_connections_total
D. cilium_ct_table_size

<details>
<summary>显示答案</summary>

**答案：B. cilium_datapath_conntrack_active**

**解释：**
cilium_datapath_conntrack_active 指标表示当前活跃连接数。它可与 cilium_datapath_conntrack_max 一起使用，以计算连接跟踪表利用率。

</details>

### 11. 使用哪个选项可接收 JSON 格式的 Hubble 输出？

A. --format json
B. -o json
C. --json
D. --output-type json

<details>
<summary>显示答案</summary>

**答案：B. -o json**

**解释：**
`hubble observe -o json` 命令以 JSON 格式输出。这对于通过管道传递给 jq 等工具进行进一步处理很有用。

</details>

### 12. 将 OpenTelemetry Collector 与 Hubble 集成时使用什么协议？

A. HTTP REST API
B. OTLP (OpenTelemetry Protocol)
C. Prometheus Remote Write
D. StatsD

<details>
<summary>显示答案</summary>

**答案：B. OTLP (OpenTelemetry Protocol)**

**解释：**
Hubble 可使用 OpenTelemetry Protocol (OTLP) 将流量数据导出到 OpenTelemetry Collector。这允许将数据路由到 Jaeger、Prometheus、Loki 等各种后端。

</details>
