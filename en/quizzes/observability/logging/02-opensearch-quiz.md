# Amazon OpenSearch Service Quiz

Test your understanding of Amazon OpenSearch Service.

---

1. What open-source project is Amazon OpenSearch Service based on?

   - A) Apache Solr
   - B) Elasticsearch 7.10 fork
   - C) Apache Lucene alone
   - D) Splunk open-source version

<details>
<summary>Show Answer</summary>

**Answer: B) Elasticsearch 7.10 fork**

**Explanation:**
OpenSearch is an open-source project created by AWS in 2021 by forking Elasticsearch 7.10 under the Apache 2.0 license. It was started in response to Elastic's license change (SSPL).

</details>

---

2. Which node type in an OpenSearch cluster is responsible for index metadata management and cluster state management?

   - A) Data Node
   - B) Master Node
   - C) UltraWarm Node
   - D) Coordinating Node

<details>
<summary>Show Answer</summary>

**Answer: B) Master Node**

**Explanation:**
Master Nodes handle cluster management tasks such as cluster state management, index creation/deletion, and shard allocation decisions. In production environments, 3 dedicated master nodes are recommended.

</details>

---

3. What is OpenSearch's cost-effective read-only storage tier?

   - A) Hot Storage
   - B) Warm Storage
   - C) UltraWarm
   - D) Standard Storage

<details>
<summary>Show Answer</summary>

**Answer: C) UltraWarm**

**Explanation:**
UltraWarm is an S3-based read-only storage tier that is approximately 75% cheaper than Hot storage (EBS). It is suitable for storing historical log data that is not frequently queried.

</details>

---

4. What is the primary purpose of ISM (Index State Management) policies?

   - A) Managing index security settings
   - B) Automating index lifecycle (rollover, deletion, etc.)
   - C) Optimizing index queries
   - D) Configuring index replication

<details>
<summary>Show Answer</summary>

**Answer: B) Automating index lifecycle (rollover, deletion, etc.)**

**Explanation:**
ISM policies automatically manage index lifecycles. They can automate index rollover, Hot→UltraWarm→Cold transitions, and deletion after retention periods.

</details>

---

5. Which log collection method for OpenSearch is most cost-effective and easiest to manage?

   - A) Logstash on EC2
   - B) FluentBit DaemonSet + direct transmission
   - C) Kinesis Data Firehose
   - D) Lambda functions

<details>
<summary>Show Answer</summary>

**Answer: C) Kinesis Data Firehose**

**Explanation:**
Kinesis Data Firehose is a fully managed service that automatically performs buffering, compression, and batch processing. With built-in S3 backup and error handling, it has low operational overhead and is cost-effective for large-scale log collection.

</details>

---

6. In OpenSearch Fine-Grained Access Control (FGAC), which feature restricts access to logs from only specific namespaces?

   - A) Field-Level Security (FLS)
   - B) Document-Level Security (DLS)
   - C) Index-Level Security
   - D) Cluster-Level Security

<details>
<summary>Show Answer</summary>

**Answer: B) Document-Level Security (DLS)**

**Explanation:**
Document-Level Security (DLS) restricts access to only documents matching specific conditions. For example, you can configure access to only a specific team's logs using the condition `kubernetes.namespace: "team-a"`.

</details>

---

7. In OpenSearch index templates, what is the Elasticsearch/OpenSearch string optimization type used instead of `LowCardinality`?

   - A) text
   - B) keyword
   - C) analyzed_string
   - D) compact_string

<details>
<summary>Show Answer</summary>

**Answer: B) keyword**

**Explanation:**
In OpenSearch, low-cardinality string fields (namespace, level, etc.) use the `keyword` type. The `text` type is tokenized for full-text search, while `keyword` is optimized for exact matching and aggregations.

</details>

---

8. What is the correct storage tiering order for OpenSearch cost optimization?

   - A) Cold → UltraWarm → Hot
   - B) Hot → Cold → UltraWarm
   - C) Hot → UltraWarm → Cold
   - D) UltraWarm → Hot → Cold

<details>
<summary>Show Answer</summary>

**Answer: C) Hot → UltraWarm → Cold**

**Explanation:**
Data is first stored in Hot storage (EBS) for fast queries, then moves to UltraWarm (read-only) as time passes, and finally to Cold Storage (S3) for older data. Cost decreases in this order.

</details>

---

9. What is the correct Query DSL for searching error logs within a specific time range in OpenSearch?

   - A) `{"query": {"match": {"level": "error", "time": "1h"}}}`
   - B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`
   - C) `{"filter": {"level": "error", "time": "> now-1h"}}`
   - D) `{"search": {"level": "error", "since": "1h"}}`

<details>
<summary>Show Answer</summary>

**Answer: B) `{"query": {"bool": {"must": [{"match": {"level": "error"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}}`**

**Explanation:**
In OpenSearch Query DSL, `bool` queries are used to combine multiple conditions. The `must` array includes both `match` (text matching) and `range` (time range) specifications.

</details>

---

10. When comparing OpenSearch and Loki, which use case is OpenSearch more suitable for?

    - A) Startups where cost optimization is the top priority
    - B) Cases requiring full-text search and complex analytical queries
    - C) Integration with existing Grafana stack
    - D) Cases requiring only simple log filtering

<details>
<summary>Show Answer</summary>

**Answer: B) Cases requiring full-text search and complex analytical queries**

**Explanation:**
OpenSearch supports powerful Lucene-based full-text search capabilities and complex aggregation queries. It is suitable for security analysis (SIEM), compliance, and complex log analysis. For cost optimization or simple filtering, Loki is more appropriate.

</details>
