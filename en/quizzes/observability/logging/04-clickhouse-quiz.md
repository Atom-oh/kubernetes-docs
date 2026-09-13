# ClickHouse for Log Analytics Quiz

> **Last Updated**: September 13, 2026

1. Why can columnar storage help analytical log queries?

   - A) It always scans every field
   - B) It can read selected columns and compress repeated values
   - C) It guarantees a fixed compression ratio
   - D) It removes the need for schema design

<details>
<summary>Show answer</summary>

**Answer: B) It can read selected columns and compress repeated values**

Benefits depend on the data, sort key and query. The guide does not promise 10:1 compression or a fixed throughput.

</details>

---

2. What is Keeper/ZooKeeper's role in this design?

   - A) Run every distributed SELECT
   - B) Store every log row
   - C) Coordinate replicated tables and distributed DDL
   - D) Replace the collector

<details>
<summary>Show answer</summary>

**Answer: C) Coordinate replicated tables and distributed DDL**

ClickHouse query initiators and Distributed tables perform distributed queries. Keeper is not their query router.

</details>

---

3. Which engine adds replication to MergeTree storage?

   - A) ReplicatedMergeTree
   - B) Memory
   - C) Buffer
   - D) Distributed alone

<details>
<summary>Show answer</summary>

**Answer: A) ReplicatedMergeTree**

Replicas still need coordination, independent persistent storage and an appropriate failure-domain design. Replication alone is not an unconditional HA guarantee.

</details>

---

4. Which type is worth evaluating for repeated namespace or severity values?

   - A) Always FixedString(255)
   - B) LowCardinality(String)
   - C) A unique integer for every log message
   - D) Only uncompressed String

<details>
<summary>Show answer</summary>

**Answer: B) LowCardinality(String)**

Dictionary encoding can help repeated values; benchmark dictionary size and query behavior instead of assuming a universal distinct-value cutoff.

</details>

---

5. How should the log table's ORDER BY be chosen?

   - A) Alphabetically
   - B) By field creation time
   - C) From selective filters, locality and representative queries
   - D) Always put timestamp last regardless of queries

<details>
<summary>Show answer</summary>

**Answer: C) From selective filters, locality and representative queries**

The key affects ordering and index pruning. Frequently queried columns alone do not determine the best order.

</details>

---

6. What must be true before using SAMPLE 0.1?

   - A) Any table supports it automatically
   - B) The table must contain exactly ten rows
   - C) It always returns exactly 10% of rows
   - D) A compatible MergeTree sampling expression must be defined and included in the primary key

<details>
<summary>Show answer</summary>

**Answer: D) A compatible MergeTree sampling expression must be defined and included in the primary key**

The main log table has no SAMPLE BY. The separate sample_demo shows the required design. A deterministic sampling-key interval need not contain exactly 10% of a finite row set.

</details>

---

7. What does Kafka add, subject to its configuration?

   - A) Guaranteed exactly-once delivery through a memory Buffer
   - B) Burst buffering and replay within retention
   - C) Automatic removal of all parser errors
   - D) Unlimited storage during outages

<details>
<summary>Show answer</summary>

**Answer: B) Burst buffering and replay within retention**

Retention, acknowledgements, replication, capacity, offset commits and downstream insert behavior must be tested. An in-memory Buffer can lose acknowledged data on a crash.

</details>

---

8. Why use a nullable JSON extraction for optional response_time_ms?

   - A) Missing measurements should not become zero-latency requests
   - B) All logs are HTTP requests
   - C) It removes the need for JSON validation
   - D) It changes the server clock

<details>
<summary>Show answer</summary>

**Answer: A) Missing measurements should not become zero-latency requests**

Check JSONType first to exclude booleans and numeric strings, then extract a nullable number. Nullable extraction alone can coerce those values. Count and percentile queries should use measured events.

</details>

---

9. What does a TTL TO VOLUME clause require and guarantee?

   - A) It creates an S3 bucket and IAM role
   - B) It deletes every row at an exact wall-clock deadline
   - C) An existing selected storage policy; asynchronous background work
   - D) It makes cold parts independent Parquet backups

<details>
<summary>Show answer</summary>

**Answer: C) An existing selected storage policy; asynchronous background work**

TTL cannot create the policy or cloud permissions. Cold table storage and a separately validated Parquet archive have different ownership and recovery semantics.

</details>

---

10. How should ClickHouse-backed Grafana alerts be built?

   - A) Invent a clickhouse_custom_query Prometheus metric
   - B) Use grafana-clickhouse-datasource with numeric SQL results and Grafana Alerting
   - C) Give every dashboard an administrator account
   - D) Treat no incoming logs as proof of health

<details>
<summary>Show answer</summary>

**Answer: B) Use grafana-clickhouse-datasource with numeric SQL results and Grafana Alerting**

Use a restricted read-only account, verified TLS and required timeout-setting permissions. Monitor ingestion separately; an aggregate can return zero even with no input.

</details>

---

[Return to the guide](../../../observability/logging/04-clickhouse.md)
