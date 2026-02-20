# Grafana Loki Quiz

Test your understanding of Grafana Loki.

---

1. What is the main reason Loki is more cost-effective than Elasticsearch?

   - A) Faster query performance
   - B) Indexes only labels instead of log content
   - C) Uses better compression algorithms
   - D) Cloud-native design

<details>
<summary>Show Answer</summary>

**Answer: B) Indexes only labels instead of log content**

**Explanation:**
Loki does not index log content, only metadata (labels). This significantly reduces index size and enables the use of cheap object storage (like S3), allowing operations to be 10x cheaper compared to Elasticsearch.

</details>

---

2. Which component in Loki architecture buffers log data in memory and stores it to storage?

   - A) Distributor
   - B) Querier
   - C) Ingester
   - D) Compactor

<details>
<summary>Show Answer</summary>

**Answer: C) Ingester**

**Explanation:**
The Ingester receives log data from the Distributor, buffers it in memory (creating chunks), manages WAL, and flushes chunks to storage. It also serves real-time queries.

</details>

---

3. What is the recommended Loki deployment mode for production EKS environments?

   - A) Monolithic mode
   - B) Simple Scalable mode
   - C) Microservices mode
   - D) Standalone mode

<details>
<summary>Show Answer</summary>

**Answer: B) Simple Scalable mode**

**Explanation:**
Simple Scalable mode separates read/write paths for scalability while being simpler to operate than Microservices mode. It is suitable for most production EKS clusters with daily log volumes of 100GB to 10TB.

</details>

---

4. What is the correct LogQL query to calculate the per-second error log rate?

   - A) `count({app="nginx"} |= "error")`
   - B) `rate({app="nginx"} |= "error" [5m])`
   - C) `sum({app="nginx"} |= "error")`
   - D) `avg({app="nginx"} |= "error" [5m])`

<details>
<summary>Show Answer</summary>

**Answer: B) `rate({app="nginx"} |= "error" [5m])`**

**Explanation:**
The `rate()` function calculates the per-second log line count over the specified time range. `[5m]` means a 5-minute range. `count()` is not used this way in metric queries, and `sum()` and `avg()` are not used standalone like this.

</details>

---

5. Which is an example of a high-cardinality label that should be avoided in Loki label design?

   - A) namespace
   - B) app
   - C) pod_name
   - D) environment

<details>
<summary>Show Answer</summary>

**Answer: C) pod_name**

**Explanation:**
pod_name can have thousands of unique values, making it a high-cardinality label. High-cardinality labels dramatically increase stream count, leading to larger index sizes and higher memory usage. namespace, app, and environment typically have dozens or fewer values, making them appropriate.

</details>

---

6. What is the recommended authentication method for Loki S3 backend access in EKS?

   - A) Access Key ID/Secret Access Key
   - B) IAM Roles for Service Accounts (IRSA)
   - C) EC2 Instance Profile
   - D) AWS STS AssumeRole

<details>
<summary>Show Answer</summary>

**Answer: B) IAM Roles for Service Accounts (IRSA)**

**Explanation:**
IRSA links IAM roles to Kubernetes service accounts, eliminating the need to store Access Keys in code or configuration. It is the most secure recommended approach and is natively supported in EKS environments.

</details>

---

7. What is the correct LogQL syntax for filtering by a specific field value after parsing JSON logs?

   - A) `{app="api"} | json | level="error"`
   - B) `{app="api"} | json | filter level="error"`
   - C) `{app="api"} | json | where level="error"`
   - D) `{app="api"} | json | select level="error"`

<details>
<summary>Show Answer</summary>

**Answer: A) `{app="api"} | json | level="error"`**

**Explanation:**
In LogQL, label filters after JSON parsing use the `| field_name="value"` format. `filter`, `where`, and `select` are not LogQL syntax.

</details>

---

8. Which is NOT a primary role of the Loki Compactor?

   - A) Merging small chunks into larger chunks
   - B) Applying retention policies (data deletion)
   - C) Receiving logs from clients
   - D) Index optimization

<details>
<summary>Show Answer</summary>

**Answer: C) Receiving logs from clients**

**Explanation:**
Receiving logs from clients is the Distributor's role. The Compactor optimizes stored data in the background and deletes old data according to retention policies.

</details>

---

9. Which settings should be adjusted when encountering "rate limit exceeded" errors in Loki?

   - A) max_streams_per_user
   - B) ingestion_rate_mb, ingestion_burst_size_mb
   - C) max_query_parallelism
   - D) chunk_idle_period

<details>
<summary>Show Answer</summary>

**Answer: B) ingestion_rate_mb, ingestion_burst_size_mb**

**Explanation:**
"Rate limit exceeded" errors occur when log ingestion rate exceeds the limit. This can be resolved by increasing `ingestion_rate_mb` (maximum ingestion per second) and `ingestion_burst_size_mb` (burst allowance).

</details>

---

10. What does the Ingester's `chunk_idle_period` setting mean in Loki performance tuning?

    - A) Time from chunk creation to deletion
    - B) Time an idle stream waits before being flushed
    - C) Query timeout duration
    - D) Log retention period

<details>
<summary>Show Answer</summary>

**Answer: B) Time an idle stream waits before being flushed**

**Explanation:**
`chunk_idle_period` is the time to wait before flushing a chunk to storage when no new logs arrive for that stream. Reducing this value decreases memory usage but may create many small chunks.

</details>
