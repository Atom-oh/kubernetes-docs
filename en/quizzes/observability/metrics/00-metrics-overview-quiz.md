# Metrics Overview Quiz

Test your understanding of basic metrics concepts and monitoring solutions.

---

1. Among the four basic types of Prometheus metrics, which type can only increase in value and resets to 0 on restart?
   - A) Gauge
   - B) Counter
   - C) Histogram
   - D) Summary

<details>
<summary>Show Answer</summary>

**Answer: B) Counter**

**Explanation:**
Counter is a metric type that tracks cumulative values, where values can only increase and reset to 0 on restart. It's used to track HTTP request counts, error counts, completed task counts, etc. Gauge can both increase and decrease, while Histogram and Summary measure distributions.

</details>

---

2. Which statement correctly describes Cardinality?
   - A) It refers to the metric collection interval
   - B) It refers to the number of unique time series combinations
   - C) It refers to the metric data compression ratio
   - D) It refers to the metric retention period

<details>
<summary>Show Answer</summary>

**Answer: B) It refers to the number of unique time series combinations**

**Explanation:**
Cardinality refers to the number of unique label combinations in metrics. High cardinality directly impacts storage usage and query performance. Using values that can grow infinitely as labels, such as user_id or request_id, causes cardinality to explode.

</details>

---

3. Which statement about Pull and Push models is NOT correct?
   - A) Prometheus is a Pull-based system
   - B) In the Pull model, collection targets and intervals are controlled centrally
   - C) The Push model is suitable for collecting metrics from short-lived jobs
   - D) The Pull model easily accesses targets behind NAT/firewalls

<details>
<summary>Show Answer</summary>

**Answer: D) The Pull model easily accesses targets behind NAT/firewalls**

**Explanation:**
In the Pull model, the monitoring server sends HTTP requests directly to targets to collect metrics, making it difficult to access targets behind NAT/firewalls. In contrast, the Push model allows targets to send metrics directly, which is advantageous in NAT/firewall environments. Using Pushgateway, the Pull model can also collect metrics from short-lived jobs.

</details>

---

4. Which statement correctly describes the difference between Histogram and Summary?
   - A) Histogram calculates quantiles on the client
   - B) Summary allows aggregation across multiple instances
   - C) Histogram calculates quantiles on the server (at query time)
   - D) Summary has higher storage efficiency than Histogram

<details>
<summary>Show Answer</summary>

**Answer: C) Histogram calculates quantiles on the server (at query time)**

**Explanation:**
Histogram stores data in buckets and calculates quantiles on the server at query time. Summary calculates and stores quantiles on the client. Histogram allows aggregation across multiple instances, but Summary does not. Histogram is recommended for SLO/SLI measurement and distributed systems.

</details>

---

5. Which is NOT a recommended metric naming convention?
   - A) Use snake_case
   - B) Include units as suffix (_seconds, _bytes)
   - C) Use camelCase
   - D) Use application/domain prefix

<details>
<summary>Show Answer</summary>

**Answer: C) Use camelCase**

**Explanation:**
Prometheus-style metric naming conventions use snake_case instead of camelCase. Good metric names like `http_requests_total`, `http_request_duration_seconds` use lowercase and underscores, include units as suffix, and use application/domain prefixes.

</details>

---

6. Which is NOT an appropriate reason why Prometheus requires a separate solution for long-term storage?
   - A) Low compression ratio increases disk usage
   - B) Single-node architecture limits scalability
   - C) PromQL doesn't support complex queries
   - D) Native HA clustering is not supported

<details>
<summary>Show Answer</summary>

**Answer: C) PromQL doesn't support complex queries**

**Explanation:**
PromQL is a very powerful query language that supports complex queries. Reasons why Prometheus is not suitable for long-term storage include relatively low compression ratio, scalability limits of single-node architecture, lack of native HA clustering, and slow query speed for long-term data.

</details>

---

7. Which solution comparison is NOT correct?
   - A) VictoriaMetrics provides higher compression ratio than Prometheus
   - B) CloudWatch is a fully managed service
   - C) Mimir only supports local disk
   - D) Datadog is provided as a SaaS model

<details>
<summary>Show Answer</summary>

**Answer: C) Mimir only supports local disk**

**Explanation:**
Grafana Mimir is a distributed metric store that requires object storage (S3, GCS, Azure Blob, etc.). It uses cloud object storage instead of local disk to provide unlimited scalability and long-term retention. VictoriaMetrics supports both local disk and object storage.

</details>

---

8. Which is NOT an appropriate method to prevent high cardinality issues?
   - A) Don't use user ID as a metric label
   - B) Don't use request ID as a metric label
   - C) Group HTTP status codes (200 → 2xx)
   - D) Keep all label values unique

<details>
<summary>Show Answer</summary>

**Answer: D) Keep all label values unique**

**Explanation:**
To prevent high cardinality, label values should not grow infinitely. Values that can grow infinitely like user ID, request ID, session ID should not be used as labels. It's better to group HTTP status codes (200 → 2xx) and normalize URL paths (/users/123 → /users/{id}).

</details>

---

9. Which correctly matches the main metric sources and roles in Kubernetes environments?
   - A) node-exporter - Kubernetes object state metrics
   - B) kube-state-metrics - Node-level hardware metrics
   - C) cAdvisor - Container-level resource metrics
   - D) metrics-server - Long-term metric storage

<details>
<summary>Show Answer</summary>

**Answer: C) cAdvisor - Container-level resource metrics**

**Explanation:**
cAdvisor (Container Advisor) collects resource metrics like CPU, memory, I/O per container. node-exporter provides node-level hardware/OS metrics, kube-state-metrics provides Kubernetes API object (Pod, Deployment, Node, etc.) state metrics, and metrics-server provides real-time resource metrics for HPA/VPA.

</details>

---

10. Which is NOT an appropriate consideration when selecting a metrics solution?
    - A) Team's operational capabilities and size
    - B) Multi-cloud requirements
    - C) Cost structure and budget
    - D) Length of metric names

<details>
<summary>Show Answer</summary>

**Answer: D) Length of metric names**

**Explanation:**
When selecting a metrics solution, you should consider the team's operational capabilities, multi-cloud requirements, cost structure, scalability requirements, and integration with existing ecosystems. The length of metric names doesn't affect solution selection. Instead, cardinality, data retention period, and query performance are important considerations.

</details>

---
