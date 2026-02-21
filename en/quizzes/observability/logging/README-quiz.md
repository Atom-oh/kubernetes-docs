# Logging Overview Quiz

Test your understanding of logging basic concepts.

---

1. Which is NOT a major advantage of Structured Logging?

   - A) Improved search and filtering efficiency
   - B) Reduced log file size
   - C) Consistent log format
   - D) Compatibility with automated analysis tools

<details>
<summary>Show Answer</summary>

**Answer: B) Reduced log file size**

**Explanation:**
Structured logging (especially JSON format) can actually result in larger file sizes than unstructured text logs. This is because field names and delimiters are added. The real advantages of structured logging are search efficiency, consistency, and automation tool compatibility.

</details>

---

2. What is the recommended log level for production environments?

   - A) DEBUG
   - B) TRACE
   - C) INFO or WARN
   - D) FATAL

<details>
<summary>Show Answer</summary>

**Answer: C) INFO or WARN**

**Explanation:**
INFO or WARN levels are recommended for production environments. DEBUG or TRACE are too verbose, resulting in excessive log volume, and using only FATAL can miss important operational information.

</details>

---

3. What is the most recommended log collection pattern in Kubernetes?

   - A) File-based logging + Sidecar
   - B) stdout/stderr + DaemonSet agent
   - C) Direct transmission to remote logging server
   - D) Local file storage with manual collection

<details>
<summary>Show Answer</summary>

**Answer: B) stdout/stderr + DaemonSet agent**

**Explanation:**
In Kubernetes, the standard approach is for containers to output logs to stdout/stderr, and agents deployed as DaemonSet collect logs from `/var/log/containers/` on the node. This approach has advantages like kubectl logs command compatibility, automatic rotation, and no separate volume required.

</details>

---

4. Which solution is recommended when "cost optimization" is the top priority for log storage selection?

   - A) Amazon OpenSearch Service
   - B) CloudWatch Logs
   - C) Grafana Loki + S3
   - D) Elasticsearch on EC2

<details>
<summary>Show Answer</summary>

**Answer: C) Grafana Loki + S3**

**Explanation:**
Loki significantly reduces storage costs by indexing only labels, not log content. Using S3 as the backend can achieve storage costs as low as $0.023 per GB.

</details>

---

5. What are the required fields to include in JSON log format for distributed tracing?

   - A) user_id, session_id
   - B) trace_id, span_id
   - C) request_id, response_time
   - D) level, message

<details>
<summary>Show Answer</summary>

**Answer: B) trace_id, span_id**

**Explanation:**
For distributed tracing, trace_id (tracking the entire request) and span_id (identifying individual operations) are required. These fields enable tracking the flow of requests across multiple services.

</details>

---

6. Which is NOT a role of the "Processing Layer" in a log collection pipeline?

   - A) Log parsing and normalization
   - B) Adding Kubernetes metadata
   - C) Log storage and indexing
   - D) Filtering and sampling

<details>
<summary>Show Answer</summary>

**Answer: C) Log storage and indexing**

**Explanation:**
Log storage and indexing is the role of the "Storage Layer". The processing layer handles parsing, metadata addition, filtering, buffering, etc.

</details>

---

7. What is the recommended log retention period for financial regulatory compliance?

   - A) 30 days
   - B) 1 year
   - C) 7 years
   - D) 90 days

<details>
<summary>Show Answer</summary>

**Answer: C) 7 years**

**Explanation:**
For financial regulatory compliance (e.g., SOX, PCI-DSS related), 7 years of log retention is generally recommended. Healthcare (HIPAA) requires 6 years, and general operational logs typically require about 1 year.

</details>

---

8. When should logs be collected using the Sidecar pattern?

   - A) All standard Kubernetes workloads
   - B) When legacy applications only output logs to files
   - C) CPU resource-constrained environments
   - D) Only single-container pods

<details>
<summary>Show Answer</summary>

**Answer: B) When legacy applications only output logs to files**

**Explanation:**
The Sidecar pattern is used for legacy applications (file logging instead of stdout/stderr), log isolation in multi-tenant environments, and when special log format processing is needed. Since it has resource overhead, the DaemonSet approach is more efficient for standard workloads.

</details>

---

9. Which log storage solution is "excellent" in both query performance and full-text search?

   - A) Grafana Loki
   - B) CloudWatch Logs
   - C) Amazon OpenSearch Service
   - D) ClickHouse

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon OpenSearch Service**

**Explanation:**
OpenSearch (Elasticsearch fork) supports both powerful Lucene-based full-text search functionality and complex aggregation queries. Loki has limited full-text search, while CloudWatch and ClickHouse have moderate full-text search capabilities.

</details>

---

10. Which log type must be enabled for security auditing in EKS control plane logging?

    - A) scheduler
    - B) controllerManager
    - C) audit
    - D) api

<details>
<summary>Show Answer</summary>

**Answer: C) audit**

**Explanation:**
Audit logs record all requests to the Kubernetes API server. They are essential for security audits and regulatory compliance because they can track who did what and when. API logs are also important, but audit is the most critical for security audit purposes.

</details>

---
