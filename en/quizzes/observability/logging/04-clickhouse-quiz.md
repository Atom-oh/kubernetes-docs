# ClickHouse for Log Analytics Quiz

Test your understanding of ClickHouse log analytics.

---

1. What is the main reason ClickHouse shows high performance in log analytics?

   - A) Row-based storage
   - B) Column-based storage
   - C) Document-based storage
   - D) Key-Value storage

<details>
<summary>Show Answer</summary>

**Answer: B) Column-based storage**

**Explanation:**
ClickHouse is a column-based database optimized for analytical queries (scanning specific columns only). Same data types are stored consecutively, enabling high compression ratios and vectorized query execution.

</details>

---

2. Which component is used for data replication and distributed query coordination in a ClickHouse cluster?

   - A) Kafka
   - B) Redis
   - C) ZooKeeper/ClickHouse Keeper
   - D) etcd

<details>
<summary>Show Answer</summary>

**Answer: C) ZooKeeper/ClickHouse Keeper**

**Explanation:**
ClickHouse clusters use ZooKeeper or ClickHouse Keeper to coordinate data synchronization between replicas, distributed DDL execution, and leader election. ClickHouse Keeper is a ClickHouse-specific alternative to ZooKeeper.

</details>

---

3. Which ClickHouse table engine supports replication and is most suitable for log storage?

   - A) MergeTree
   - B) ReplicatedMergeTree
   - C) Log
   - D) Memory

<details>
<summary>Show Answer</summary>

**Answer: B) ReplicatedMergeTree**

**Explanation:**
ReplicatedMergeTree adds replication functionality to all MergeTree features (sorting, partitioning, TTL, etc.). It is recommended for production log storage requiring high availability.

</details>

---

4. What optimization type should be used for low-cardinality string columns (e.g., level, namespace) in ClickHouse?

   - A) String
   - B) FixedString
   - C) LowCardinality(String)
   - D) Enum

<details>
<summary>Show Answer</summary>

**Answer: C) LowCardinality(String)**

**Explanation:**
LowCardinality(String) is used for string columns with few unique values (~10,000 or less). It uses dictionary encoding internally to optimize storage space and query performance.

</details>

---

5. What is the principle for specifying column order in the `ORDER BY` clause when designing ClickHouse log tables?

   - A) Alphabetical order
   - B) Column size order (smallest first)
   - C) Frequently filtered columns first
   - D) Creation time order

<details>
<summary>Show Answer</summary>

**Answer: C) Frequently filtered columns first**

**Explanation:**
ClickHouse's ORDER BY affects data sorting and index creation. Placing columns frequently used in WHERE clauses at the front results in scanning less data during queries. Example: `ORDER BY (namespace, service, timestamp)`

</details>

---

6. What is the syntax for sampling techniques used for fast analysis of large datasets in ClickHouse?

   - A) `LIMIT RANDOM 10%`
   - B) `SAMPLE 0.1`
   - C) `WHERE rand() < 0.1`
   - D) `TABLESAMPLE (10 PERCENT)`

<details>
<summary>Show Answer</summary>

**Answer: B) `SAMPLE 0.1`**

**Explanation:**
ClickHouse's `SAMPLE` clause scans only a portion of data for fast approximate analysis. `SAMPLE 0.1` reads only 10% of the data. Results can be multiplied by an appropriate factor to get estimated totals.

</details>

---

7. What is the main reason for placing Kafka between log sources and ClickHouse for log collection?

   - A) Data encryption
   - B) Buffering and peak traffic handling
   - C) Data compression
   - D) Query optimization

<details>
<summary>Show Answer</summary>

**Answer: B) Buffering and peak traffic handling**

**Explanation:**
Kafka serves as a message queue that buffers logs during peak traffic, allowing ClickHouse to consume data at a consistent rate. It also prevents data loss during ClickHouse failures.

</details>

---

8. What functions are used to extract JSON field values in ClickHouse SQL?

   - A) JSON_EXTRACT()
   - B) JSONExtractString(), JSONExtractFloat()
   - C) parseJSON()
   - D) getJSON()

<details>
<summary>Show Answer</summary>

**Answer: B) JSONExtractString(), JSONExtractFloat()**

**Explanation:**
ClickHouse extracts JSON fields using functions like `JSONExtractString(json, 'field')` and `JSONExtractFloat(json, 'field')`. Different functions are used for each type.

</details>

---

9. What feature in ClickHouse tables automatically deletes old data?

   - A) AUTO_DELETE
   - B) RETENTION_POLICY
   - C) TTL (Time To Live)
   - D) EXPIRE_AFTER

<details>
<summary>Show Answer</summary>

**Answer: C) TTL (Time To Live)**

**Explanation:**
ClickHouse's TTL feature automatically deletes data after a certain period or moves it to different storage (e.g., S3). Example: `TTL date + INTERVAL 90 DAY DELETE`

</details>

---

10. What data source plugin is used when integrating ClickHouse with Grafana?

    - A) grafana-mysql-datasource
    - B) grafana-clickhouse-datasource
    - C) grafana-sql-datasource
    - D) grafana-olap-datasource

<details>
<summary>Show Answer</summary>

**Answer: B) grafana-clickhouse-datasource**

**Explanation:**
To integrate ClickHouse with Grafana, install the `grafana-clickhouse-datasource` plugin. This plugin allows you to visualize ClickHouse data using SQL queries and build dashboards.

</details>
