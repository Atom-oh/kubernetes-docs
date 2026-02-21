# VictoriaMetrics Quiz

Test your understanding of VictoriaMetrics.

---

1. Which is NOT a major advantage of VictoriaMetrics compared to Prometheus?
   - A) Up to 7x more efficient data compression
   - B) Up to 20x faster performance on complex queries
   - C) Requires learning a separate query language
   - D) Horizontal scaling capability

<details>
<summary>Show Answer</summary>

**Answer: C) Requires learning a separate query language**

**Explanation:**
VictoriaMetrics uses MetricsQL query language, which is a superset of PromQL. All existing PromQL queries work, and it only provides additional convenience features. Therefore, there's no need to learn a separate query language.

</details>

---

2. Which is NOT a component of VictoriaMetrics cluster mode?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmoperator

<details>
<summary>Show Answer</summary>

**Answer: D) vmoperator**

**Explanation:**
VictoriaMetrics cluster mode consists of three core components: vminsert (write request routing), vmstorage (data storage), vmselect (query processing). vmoperator is a separate Kubernetes Operator, not a core component of cluster mode.

</details>

---

3. What is the main role of vmagent?
   - A) Long-term data storage
   - B) Dashboard rendering
   - C) Metric collection and Remote Write transmission
   - D) Alert routing

<details>
<summary>Show Answer</summary>

**Answer: C) Metric collection and Remote Write transmission**

**Explanation:**
vmagent is a lightweight agent that collects metrics and sends them to VictoriaMetrics or other remote storage. It's compatible with Prometheus scrape configuration and provides features like data buffering, retransmission, and label relabeling.

</details>

---

4. What is the purpose of the `keep_last_value()` function in MetricsQL?
   - A) Keep maximum value
   - B) Keep last value (gap filling)
   - C) Keep first value
   - D) Keep average value

<details>
<summary>Show Answer</summary>

**Answer: B) Keep last value (gap filling)**

**Explanation:**
`keep_last_value()` is a MetricsQL extension function that fills missing values (gaps) in time series data with the last known value. It's useful for preventing gaps in dashboards and alerts when there are scrape failures or temporary data loss.

</details>

---

5. What is the role of the `--dedup.minScrapeInterval` flag in VictoriaMetrics?
   - A) Set minimum scrape interval
   - B) Remove duplicate samples within specified interval
   - C) Set data compression interval
   - D) Set alert evaluation interval

<details>
<summary>Show Answer</summary>

**Answer: B) Remove duplicate samples within specified interval**

**Explanation:**
`--dedup.minScrapeInterval` removes duplicate samples of the same time series within the specified time interval. For example, `--dedup.minScrapeInterval=30s` merges duplicate data points within 30 seconds into one. It's useful in HA configurations where multiple Prometheus instances scrape the same targets.

</details>

---

6. What is the correct criterion for choosing between vmsingle and vmcluster?
   - A) Always use vmcluster
   - B) vmsingle is recommended for under 100M samples/day without high availability requirements
   - C) vmsingle doesn't support query functionality
   - D) vmcluster only works on a single node

<details>
<summary>Show Answer</summary>

**Answer: B) vmsingle is recommended for under 100M samples/day without high availability requirements**

**Explanation:**
vmsingle (single-node mode) is simple to configure and suitable for small to medium environments. vmsingle is recommended when daily samples are under 100M and high availability is not essential. Use vmcluster for large-scale environments or when high availability is required.

</details>

---

7. What does the `replicationFactor=2` setting mean in VictoriaMetrics cluster?
   - A) Use only 2 storage nodes
   - B) Replicate each data point to 2 storage nodes
   - C) Execute queries on only 2 nodes
   - D) Apply 2x compression

<details>
<summary>Show Answer</summary>

**Answer: B) Replicate each data point to 2 storage nodes**

**Explanation:**
`replicationFactor=2` configures vminsert to replicate each data point to 2 vmstorage nodes. This allows service to continue without data loss even if one storage node fails. This is a recommended setting for high availability.

</details>

---

8. What is the purpose of the `default` operator in MetricsQL?
   - A) Set default labels
   - B) Return default value when there's no result
   - C) Set default aggregation function
   - D) Set default time range

<details>
<summary>Show Answer</summary>

**Answer: B) Return default value when there's no result**

**Explanation:**
The `default` operator in MetricsQL returns a default value when the query result is empty or NaN. For example, `rate(http_requests_total[5m]) / rate(http_requests_total[5m]) default 0` returns 0 instead of a division by zero error. In PromQL, complex conditionals are needed for this handling.

</details>

---

9. What is the correct role of vmalert?
   - A) Metric collection
   - B) Data storage
   - C) Alert rule evaluation and alert generation
   - D) Dashboard creation

<details>
<summary>Show Answer</summary>

**Answer: C) Alert rule evaluation and alert generation**

**Explanation:**
vmalert evaluates alerting rules and sends alerts to Alertmanager when conditions are met, similar to Prometheus's alerting functionality. It can use VictoriaMetrics or Prometheus as data sources and also supports recording rules.

</details>

---

10. What is the main purpose of vmbackup in VictoriaMetrics?
    - A) Real-time data replication
    - B) Create backups to object storage
    - C) Log backup
    - D) Configuration file backup

<details>
<summary>Show Answer</summary>

**Answer: B) Create backups to object storage**

**Explanation:**
vmbackup is a tool that backs up VictoriaMetrics data to object storage like S3, GCS, Azure Blob. It creates consistent backups using snapshot functionality and can be restored using vmrestore. It's an essential tool for disaster recovery and data protection.

</details>

---
