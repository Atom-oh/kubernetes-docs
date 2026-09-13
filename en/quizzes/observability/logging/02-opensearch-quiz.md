# Amazon OpenSearch Service Quiz

> **Last Updated**: September 13, 2026

Based on the managed-domain and collector examples in the [guide](../../../observability/logging/02-opensearch.md).

---

1. Which statement correctly distinguishes OpenSearch from Amazon OpenSearch Service?

   - A) Every Elasticsearch client/plugin remains compatible
   - B) AWS immediately supports every upstream release
   - C) OpenSearch is an Apache-2.0 project; the managed service supports selected engine versions
   - D) The service is only a Kibana hosting product

<details>
<summary>Show answer</summary>

**Answer: C**

The Elasticsearch 7.10 lineage is not a blanket compatibility guarantee. Check AWS version support and the actual client/plugin. The earlier 2.11 baseline remains standard-supported through November 7, 2027.

</details>

---

2. With dedicated cluster-manager nodes configured, which role handles cluster state and shard-allocation management?

   - A) Dedicated cluster-manager nodes
   - B) UltraWarm storage
   - C) Cold storage
   - D) The log collector

<details>
<summary>Show answer</summary>

**Answer: A**

AWS configuration fields still use dedicated_master names. Manager count is distinct from data replica count, and zone awareness alone does not enable Multi-AZ with Standby.

</details>

---

3. Which statement is correct for traditional UltraWarm and cold storage?

   - A) UltraWarm stores everything only on EBS
   - B) Both are S3-backed; cold indexes must be attached to UltraWarm before querying
   - C) Every workload saves exactly 75%
   - D) Every instance/engine combination supports both tiers

<details>
<summary>Show answer</summary>

**Answer: B**

A hot→UltraWarm→cold policy needs the relevant service prerequisites and migration capacity. Costs and query latency depend on the workload; tier names are not fixed savings guarantees.

</details>

---

4. Which ISM action deletes an index from managed OpenSearch Service cold storage?

   - A) delete in every storage tier
   - B) force_merge
   - C) warm_migration
   - D) cold_delete

<details>
<summary>Show answer</summary>

**Answer: D**

Managed cold storage requires cold_delete. Policies use one action per action object and run asynchronously; the example 7/30/90-day index ages are not exact event-age retention guarantees.

</details>

---

5. How should direct Fluent Bit delivery and Amazon Data Firehose be compared?

   - A) Firehose is always the cheapest option
   - B) Direct Fluent Bit cannot authenticate to AWS
   - C) Compare operational needs, schema, buffering/retry/backup, access and measured cost
   - D) Both automatically create identical Kubernetes metadata

<details>
<summary>Show answer</summary>

**Answer: C**

Firehose offers a managed delivery path but requires roles, connectivity and compatible records. FailedDocumentsOnly selects its backup mode; a prefix named failed/ alone does not select that behavior.

</details>

---

6. Which statement correctly describes DLS and FLS?

   - A) DLS filters documents; FLS controls returned fields, with effective roles and trusted metadata still important
   - B) FLS authenticates the Kubernetes namespace automatically
   - C) URI-based IAM alone restricts every index named inside a bulk body
   - D) A security-group rule grants document-level read access

<details>
<summary>Show answer</summary>

**Answer: A**

The guide uses trusted kubernetes.namespace_name metadata. A restricted role does not cancel an existing broader grant. FLS does not redact sensitive text inside an allowed message or delete stored data/backups.

</details>

---

7. Which mapped string type supports exact matching and common field aggregations?

   - A) text with no subfield
   - B) keyword
   - C) LowCardinality as an OpenSearch type
   - D) Unmapped fields only

<details>
<summary>Show answer</summary>

**Answer: B**

Keyword differs from analyzed text and from ClickHouse LowCardinality. Many keyword/numeric aggregations use column-oriented doc values, so they do not universally scan every full _source document.

</details>

---

8. With Logstash_Format On and prefix logs-production, where does the illustrated Fluent Bit output write?

   - A) Always to a rollover alias
   - B) Automatically to a Serverless collection
   - C) Directly to detached cold indexes
   - D) Date-based logs-production-YYYY.MM.DD indexes

<details>
<summary>Show answer</summary>

**Answer: D**

An alias is not selected merely because one exists. The guide separates the daily-index path from rollover-logs-*, which needs the rollover alias setting, a numbered index and the write alias.

</details>

---

9. Which Query DSL filters mapped error log lines from the last hour?

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>Show answer</summary>

**Answer: C**

The example mapping nests application fields under app and uses @timestamp. Filter context combines exact keyword matching and a time range without requiring relevance scoring.

</details>

---

10. What is a sound basis for selecting OpenSearch, Loki or ClickHouse for log workloads?

   - A) A universal 100GB/day cutover
   - B) The claim that every organization has the same query mix
   - C) Fixed 3–5× cost and 60–80% savings rules
   - D) Representative queries plus retention, durability, permissions, operational capability and measured cost

<details>
<summary>Show answer</summary>

**Answer: D**

All three have different indexing/query models and operating tradeoffs. Compare equivalent requirements and validate migration, reconciliation and rollback; no product automatically establishes compliance or minimum cost.

</details>
