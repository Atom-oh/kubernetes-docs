# Prometheus Quiz

A quiz to test your understanding of Prometheus.

---

1. What is Prometheus's data collection method?
   - A) Push-based - Applications send metrics
   - B) Pull-based - Prometheus scrapes metrics from targets
   - C) Streaming-based - Real-time data streams
   - D) Batch-based - Periodic file transfers

<details>
<summary>Show Answer</summary>

**Answer: B) Pull-based - Prometheus scrapes metrics from targets**

**Explanation:**
Prometheus is a Pull-based metrics collection system that periodically scrapes metrics from targets' /metrics endpoints via HTTP. The advantages of this approach are central control of collection targets and intervals, and automatic detection of target availability.

</details>

---

2. What is the correct PromQL query to calculate HTTP request rate over the last 5 minutes?
   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>Show Answer</summary>

**Answer: B) `rate(http_requests_total[5m])`**

**Explanation:**
The `rate()` function calculates the average per-second increase rate of Counter metrics. Range vectors specify time in square brackets `[]`. `increase()` returns total increase, and `avg()` is an aggregation function that calculates averages. `rate(http_requests_total[5m])` calculates requests per second over 5 minutes.

</details>

---

3. What is the role of ServiceMonitor in Prometheus Operator?
   - A) Deploys the Prometheus server
   - B) Defines alerting rules
   - C) Defines services to monitor and scrape configurations
   - D) Creates Grafana dashboards

<details>
<summary>Show Answer</summary>

**Answer: C) Defines services to monitor and scrape configurations**

**Explanation:**
ServiceMonitor is a CRD of Prometheus Operator that declaratively defines scrape configurations for monitoring Kubernetes services. You can configure target service selectors, endpoints, scrape intervals, label relabeling, etc. PrometheusRule handles alerting rules, and the Prometheus CRD handles server deployment.

</details>

---

4. Which statement about the histogram_quantile function is correct?
   - A) It can only be used with Summary metrics
   - B) It calculates quantiles from Histogram buckets
   - C) It returns exact quantile values
   - D) It calculates the rate of change for Counter metrics

<details>
<summary>Show Answer</summary>

**Answer: B) It calculates quantiles from Histogram buckets**

**Explanation:**
`histogram_quantile()` calculates quantiles from Histogram bucket data. For example, `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` calculates p95 latency. It returns approximations based on bucket boundaries; use Summary for exact quantiles.

</details>

---

5. Which component is NOT included in the kube-prometheus-stack Helm chart?
   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>Show Answer</summary>

**Answer: C) VictoriaMetrics**

**Explanation:**
kube-prometheus-stack is a Helm chart that includes Prometheus Operator, Prometheus, Alertmanager, Grafana, kube-state-metrics, node-exporter, and more. VictoriaMetrics is a separate project, installed via the victoria-metrics-k8s-stack chart.

</details>

---

6. What is the primary purpose of Remote Write in Prometheus?
   - A) Improve local storage performance
   - B) Send data to long-term metrics storage
   - C) Send real-time alerts
   - D) Sync Grafana dashboards

<details>
<summary>Show Answer</summary>

**Answer: B) Send data to long-term metrics storage**

**Explanation:**
Remote Write is a feature that sends metrics collected by Prometheus to external systems (VictoriaMetrics, Mimir, AMP, Cortex, etc.). Since Prometheus's local storage has retention and scalability limitations, Remote Write is used to send data to dedicated storage for long-term retention.

</details>

---

7. What is the role of the `for` field in PrometheusRule CRD?
   - A) Set rule evaluation interval
   - B) Set condition duration time before alert fires
   - C) Set alert resend interval
   - D) Set metric retention period

<details>
<summary>Show Answer</summary>

**Answer: B) Set condition duration time before alert fires**

**Explanation:**
The `for` field in PrometheusRule sets the wait time after an alert condition is met before the alert actually fires. For example, `for: 5m` means the condition must persist for 5 minutes before the alert fires. This prevents unnecessary alerts from temporary spikes.

</details>

---

8. What is the purpose of the `predict_linear` function in PromQL?
   - A) Calculate absolute value of current value
   - B) Predict future values based on linear regression
   - C) Sort time series data
   - D) Transform label values

<details>
<summary>Show Answer</summary>

**Answer: B) Predict future values based on linear regression**

**Explanation:**
`predict_linear(v range-vector, t scalar)` uses linear regression to predict future values. For example, `predict_linear(node_filesystem_avail_bytes[6h], 24*60*60) < 0` predicts whether disk space will be exhausted in 24 hours at the current trend. Useful for capacity planning and proactive alerting.

</details>

---

9. What is the role of Alertmanager's `groupBy` setting?
   - A) Send alerts only to specific groups
   - B) Group alerts by specified labels
   - C) Set alert priority
   - D) Remove duplicate alerts

<details>
<summary>Show Answer</summary>

**Answer: B) Group alerts by specified labels**

**Explanation:**
`groupBy` groups alerts by specified labels and sends them as a single notification. For example, `groupBy: ['alertname', 'namespace']` groups alerts with the same alertname and namespace. This prevents alert storms and allows related alerts to be viewed together.

</details>

---

10. What is the role of WAL (Write-Ahead Log) in Prometheus TSDB?
    - A) Query caching
    - B) Write-ahead recording to prevent data loss
    - C) Store alert history
    - D) Store dashboard settings

<details>
<summary>Show Answer</summary>

**Answer: B) Write-ahead recording to prevent data loss**

**Explanation:**
WAL (Write-Ahead Log) is a log that records data sequentially before it's fully written from memory to disk blocks. Even if Prometheus terminates abnormally, data can be recovered through the WAL to prevent data loss. This is a durability mechanism commonly used in databases.

</details>
