# Grafana Mimir Quiz

A quiz to test your understanding of Grafana Mimir.

---

1. What is Grafana Mimir's primary storage backend?
   - A) Local SSD only
   - B) Object storage (S3, GCS, Azure Blob)
   - C) NFS shared storage
   - D) Block storage only

<details>
<summary>Show Answer</summary>

**Answer: B) Object storage (S3, GCS, Azure Blob)**

**Explanation:**
Grafana Mimir requires object storage. It supports S3, Google Cloud Storage, Azure Blob Storage, etc., providing unlimited scalability and cost-effective long-term storage. Local storage is only used for Ingester's WAL and temporary data.

</details>

---

2. What is the role of Distributor in Mimir architecture?
   - A) Long-term data storage
   - B) First entry point for write requests, tenant validation and sample distribution
   - C) Query result caching
   - D) Block compaction

<details>
<summary>Show Answer</summary>

**Answer: B) First entry point for write requests, tenant validation and sample distribution**

**Explanation:**
Distributor is the first entry point for write requests, responsible for tenant ID validation, time series validation, hash ring-based Ingester distribution, and replication based on replication factor. It's a stateless component that scales horizontally easily.

</details>

---

3. How is multi-tenancy implemented in Mimir?
   - A) Operate separate clusters per tenant
   - B) Identify tenants via X-Scope-OrgID header
   - C) IP address-based tenant separation
   - D) Namespace-based tenant separation

<details>
<summary>Show Answer</summary>

**Answer: B) Identify tenants via X-Scope-OrgID header**

**Explanation:**
Mimir identifies tenants via the HTTP header `X-Scope-OrgID`. Adding this header to Prometheus's remote_write configuration isolates each tenant's data. Per-tenant limits can be configured, and data is separated by tenant paths in object storage.

</details>

---

4. Why does Mimir's Ingester upload blocks to object storage?
   - A) Improve real-time query performance
   - B) Persist data from memory to disk
   - C) Store alerting rules
   - D) Back up dashboard settings

<details>
<summary>Show Answer</summary>

**Answer: B) Persist data from memory to disk**

**Explanation:**
Ingester first stores received time series data in memory, then periodically (default 2 hours) creates TSDB blocks and uploads them to object storage. This ensures data is permanently stored and minimizes data loss even if an Ingester fails.

</details>

---

5. What is the correct role of Mimir's Compactor?
   - A) Real-time query processing
   - B) Merge small blocks into large blocks and deduplicate
   - C) Metrics collection
   - D) Alert transmission

<details>
<summary>Show Answer</summary>

**Answer: B) Merge small blocks into large blocks and deduplicate**

**Explanation:**
Compactor merges (compacts) small blocks in object storage into larger blocks, removes duplicate data, and deletes old data according to retention policies. This improves query performance and reduces storage costs.

</details>

---

6. Which is NOT a function provided by Mimir's Query-frontend?
   - A) Large query splitting
   - B) Result caching
   - C) Data storage
   - D) Query retries

<details>
<summary>Show Answer</summary>

**Answer: C) Data storage**

**Explanation:**
Query-frontend is a stateless component responsible for query optimization and caching. It splits large queries into smaller queries, caches results, and retries failed queries. Data storage is handled by Ingester (short-term) and object storage (long-term).

</details>

---

7. When comparing Mimir with VictoriaMetrics, which is a correct characteristic of Mimir?
   - A) Only local disk available
   - B) Lower operational complexity
   - C) Object storage required, enterprise-grade multi-tenancy
   - D) Uses MetricsQL query language

<details>
<summary>Show Answer</summary>

**Answer: C) Object storage required, enterprise-grade multi-tenancy**

**Explanation:**
Mimir requires object storage and provides native multi-tenancy, making it suitable for enterprise environments. VictoriaMetrics also supports local disk and is simpler to operate, but Mimir has excellent integration with the Grafana ecosystem.

</details>

---

8. What is the role of Store-gateway in Mimir?
   - A) Metrics collection
   - B) Cache object storage blocks and process historical data queries
   - C) Alert rule evaluation
   - D) Tenant authentication

<details>
<summary>Show Answer</summary>

**Answer: B) Cache object storage blocks and process historical data queries**

**Explanation:**
Store-gateway caches indexes and chunks of blocks stored in object storage and processes queries for historical data. Querier retrieves recent data from Ingester and historical data from Store-gateway, then merges them.

</details>

---

9. What is the role of the `compactor_blocks_retention_period` setting in Mimir?
   - A) Memory cache retention period
   - B) Set block data retention period
   - C) Log retention period
   - D) Alert history retention period

<details>
<summary>Show Answer</summary>

**Answer: B) Set block data retention period**

**Explanation:**
`compactor_blocks_retention_period` sets the period that Compactor retains blocks. For example, setting it to `365d` deletes blocks older than 1 year. This setting helps manage storage costs and meet compliance requirements.

</details>

---

10. Which is NOT a recommendation for Mimir high availability configuration?
    - A) Minimum 3 Ingester replicas, zone-aware replication
    - B) Minimum 2 Store-gateway replicas
    - C) Deploy all components in a single availability zone
    - D) Enable caching with memcached

<details>
<summary>Show Answer</summary>

**Answer: C) Deploy all components in a single availability zone**

**Explanation:**
For high availability, components should be distributed across multiple availability zones (AZ). Mimir supports zone-aware replication to distribute Ingesters across multiple AZs. Deploying in a single AZ causes complete service disruption if that AZ fails.

</details>
