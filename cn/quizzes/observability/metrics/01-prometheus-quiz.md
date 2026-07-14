# Prometheus 测验

用于测试你对 Prometheus 理解程度的测验。

---

1. Prometheus 的数据收集方式是什么？
   - A) Push-based - 应用程序发送指标
   - B) Pull-based - Prometheus 从目标抓取指标
   - C) Streaming-based - 实时数据流
   - D) Batch-based - 定期文件传输

<details>
<summary>显示答案</summary>

**答案：B) Pull-based - Prometheus 从目标抓取指标**

**解释：**
Prometheus 是一个 Pull-based 指标收集系统，它会通过 HTTP 定期从目标的 /metrics 端点抓取指标。这种方法的优点是可以集中控制收集目标和间隔，并自动检测目标的可用性。

</details>

---

2. 用于计算过去 5 分钟 HTTP 请求速率的正确 PromQL 查询是什么？
   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>显示答案</summary>

**答案：B) `rate(http_requests_total[5m])`**

**解释：**
`rate()` 函数计算 Counter 指标的每秒平均增长速率。范围向量使用方括号 `[]` 指定时间。`increase()` 返回总增长量，而 `avg()` 是一个计算平均值的聚合函数。`rate(http_requests_total[5m])` 计算 5 分钟内每秒的请求数。

</details>

---

3. Prometheus Operator 中的 ServiceMonitor 的作用是什么？
   - A) 部署 Prometheus 服务器
   - B) 定义告警规则
   - C) 定义要监控的服务和抓取配置
   - D) 创建 Grafana 仪表板

<details>
<summary>显示答案</summary>

**答案：C) 定义要监控的服务和抓取配置**

**解释：**
ServiceMonitor 是 Prometheus Operator 的一个 CRD，用于以声明式方式定义监控 Kubernetes 服务的抓取配置。你可以配置目标 Service 选择器、端点、抓取间隔、标签重标记等。PrometheusRule 处理告警规则，而 Prometheus CRD 处理服务器部署。

</details>

---

4. 关于 histogram_quantile 函数，哪个说法是正确的？
   - A) 它只能与 Summary 指标一起使用
   - B) 它从 Histogram bucket 计算分位数
   - C) 它返回精确的分位数值
   - D) 它计算 Counter 指标的变化速率

<details>
<summary>显示答案</summary>

**答案：B) 它从 Histogram bucket 计算分位数**

**解释：**
`histogram_quantile()` 从 Histogram bucket 数据计算分位数。例如，`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` 计算 p95 延迟。它根据 bucket 边界返回近似值；如需精确分位数，请使用 Summary。

</details>

---

5. 以下哪个组件未包含在 kube-prometheus-stack Helm chart 中？
   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>显示答案</summary>

**答案：C) VictoriaMetrics**

**解释：**
kube-prometheus-stack 是一个 Helm chart，其中包括 Prometheus Operator、Prometheus、Alertmanager、Grafana、kube-state-metrics、node-exporter 等。VictoriaMetrics 是一个独立项目，通过 victoria-metrics-k8s-stack chart 安装。

</details>

---

6. Prometheus 中 Remote Write 的主要用途是什么？
   - A) 提高本地存储性能
   - B) 将数据发送到长期指标存储
   - C) 发送实时告警
   - D) 同步 Grafana 仪表板

<details>
<summary>显示答案</summary>

**答案：B) 将数据发送到长期指标存储**

**解释：**
Remote Write 是一项将 Prometheus 收集的指标发送到外部系统（VictoriaMetrics、Mimir、AMP、Cortex 等）的功能。由于 Prometheus 的本地存储在保留期和可扩展性方面存在限制，因此使用 Remote Write 将数据发送到专用存储中进行长期保留。

</details>

---

7. PrometheusRule CRD 中 `for` 字段的作用是什么？
   - A) 设置规则评估间隔
   - B) 设置告警触发前条件持续的时间
   - C) 设置告警重新发送间隔
   - D) 设置指标保留期限

<details>
<summary>显示答案</summary>

**答案：B) 设置告警触发前条件持续的时间**

**解释：**
PrometheusRule 中的 `for` 字段设置告警条件满足后、告警实际触发前的等待时间。例如，`for: 5m` 表示该条件必须持续 5 分钟后才会触发告警。这可防止由短暂峰值导致的不必要告警。

</details>

---

8. PromQL 中 `predict_linear` 函数的用途是什么？
   - A) 计算当前值的绝对值
   - B) 基于线性回归预测未来值
   - C) 对时间序列数据排序
   - D) 转换标签值

<details>
<summary>显示答案</summary>

**答案：B) 基于线性回归预测未来值**

**解释：**
`predict_linear(v range-vector, t scalar)` 使用线性回归预测未来值。例如，`predict_linear(node_filesystem_avail_bytes[6h], 24*60*60) < 0` 可根据当前趋势预测磁盘空间是否会在 24 小时内耗尽。它适用于容量规划和主动告警。

</details>

---

9. Alertmanager 的 `groupBy` 设置的作用是什么？
   - A) 仅向特定组发送告警
   - B) 按指定标签对告警分组
   - C) 设置告警优先级
   - D) 移除重复告警

<details>
<summary>显示答案</summary>

**答案：B) 按指定标签对告警分组**

**解释：**
`groupBy` 按指定标签对告警分组，并将其作为单个通知发送。例如，`groupBy: ['alertname', 'namespace']` 将具有相同 alertname 和 namespace 的告警分组。这可防止告警风暴，并允许将相关告警一同查看。

</details>

---

10. WAL（Write-Ahead Log）在 Prometheus TSDB 中的作用是什么？
    - A) 查询缓存
    - B) 预写记录以防止数据丢失
    - C) 存储告警历史记录
    - D) 存储仪表板设置

<details>
<summary>显示答案</summary>

**答案：B) 预写记录以防止数据丢失**

**解释：**
WAL（Write-Ahead Log）是一种日志，在数据从内存完全写入磁盘块之前按顺序记录数据。即使 Prometheus 异常终止，也可以通过 WAL 恢复数据，以防止数据丢失。这是一种常用于数据库的持久性机制。

</details>
