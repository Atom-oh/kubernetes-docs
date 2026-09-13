# Grafana Mimir Quiz

Baseline: Mimir 3.2.1 / chart 6.2.0. Review current architecture, identity, storage and validation limits.

## 1. Which backend is intended for production Mimir block storage?

- A. Only local SSD
- B. Object storage such as S3, GCS, Azure Blob or Swift
- C. Only NFS
- D. Only an in-memory cache

<details>
<summary>Show answer</summary>

**Answer: B. Object storage such as S3, GCS, Azure Blob or Swift**

Production deployments use appropriate external object storage. A filesystem backend exists for local development; this does not make it a shared production object store. Local ingester TSDB/WAL and Kafka storage have separate persistence and recovery requirements.

</details>

## 2. What does the distributor do in ingest-storage architecture?

- A. Store all long-term blocks itself
- B. Validate writes and append records to Kafka
- C. Return every query from a result cache
- D. Compact TSDB blocks

<details>
<summary>Show answer</summary>

**Answer: B. Validate writes and append records to Kafka**

Distributors validate and limit writes, then shard them to Kafka partitions. Write acknowledgement depends on Kafka write success under configured durability conditions. It does not wait for an S3 block upload. Direct writes to an ingester quorum describe classic architecture.

</details>

## 3. How should tenant selection be secured for untrusted callers?

- A. Let clients choose any X-Scope-OrgID value
- B. Authenticate and authorize at a trusted gateway that sets the tenant header
- C. Use only an object key prefix
- D. Treat a namespace name as automatic HTTP authentication

<details>
<summary>Show answer</summary>

**Answer: B. Authenticate and authorize at a trusted gateway that sets the tenant header**

X-Scope-OrgID identifies a tenant; it is not a credential. The trusted gateway must replace untrusted headers and enforce the caller-to-tenant mapping. A basic-auth username maps to a tenant only when the proxy implements that policy. Backend bypass must also be restricted.

</details>

## 4. Why do ingesters upload TSDB blocks to object storage?

- A. To avoid all local persistence
- B. To provide long-term block storage and block-query access
- C. To back up Grafana dashboards
- D. To guarantee every acknowledged sample survives every possible failure

<details>
<summary>Show answer</summary>

**Answer: B. To provide long-term block storage and block-query access**

Ingesters maintain local TSDB/WAL and periodically upload blocks. Local retention overlaps the handoff to store-gateways. Kafka acknowledgement, ingester consumption and object upload are separate stages; recovery still depends on persistence, retention and failure conditions.

</details>

## 5. Which responsibilities belong to the compactor?

- A. Scrape every application endpoint
- B. Merge blocks, deduplicate replicated samples and perform retention cleanup
- C. Authenticate all tenants
- D. Automatically downsample all raw series with downsampling_enabled

<details>
<summary>Show answer</summary>

**Answer: B. Merge blocks, deduplicate replicated samples and perform retention cleanup**

Compaction merges blocks and removes duplicated samples from replicas. Retention cleanup is asynchronous. The invented compactor.downsampling_enabled option is not valid; recording rules create derived series without automatically deleting raw data.

</details>

## 6. Which is not a query-frontend responsibility?

- A. Split and shard supported queries
- B. Use a query result cache
- C. Persist the authoritative long-term TSDB blocks
- D. Combine query responses

<details>
<summary>Show answer</summary>

**Answer: C. Persist the authoritative long-term TSDB blocks**

The frontend plans/caches work and returns combined responses. The scheduler queues work and queriers fetch required data. Metadata or chunk-cache hits are not automatically complete query answers. Step alignment can change requested timestamps and PromQL conformance.

</details>

## 7. Which comparison with VictoriaMetrics is accurate?

- A. Mimir never has a filesystem backend
- B. Grafana use makes Mimir universally faster
- C. Compare storage architecture, query semantics, tenancy enforcement, recovery and measured cost
- D. VictoriaMetrics cannot support tenants

<details>
<summary>Show answer</summary>

**Answer: C. Compare storage architecture, query semantics, tenancy enforcement, recovery and measured cost**

Both products require an authentication/authorization boundary. Mimir production block storage and the reviewed VictoriaMetrics local-storage architecture have different operational requirements. Neither unsupported compression rankings nor ecosystem preference establish a performance or cost winner.

</details>

## 8. What does the store-gateway provide?

- A. Application metric collection
- B. Block-query access using object storage, index headers and configured caches
- C. Automatic tenant authentication
- D. Kafka broker replication

<details>
<summary>Show answer</summary>

**Answer: B. Block-query access using object storage, index headers and configured caches**

Queriers request block data from store-gateways and recent data from ingesters; ranges may overlap during block handoff. Cache/index metadata reuse avoids some work but does not imply every query is answered without chunk reads.

</details>

## 9. What does compactor_blocks_retention_period control?

- A. In-memory cache expiration only
- B. The long-term block retention policy used by the compactor
- C. Kafka topic retention
- D. An exact physical deletion/compliance deadline

<details>
<summary>Show answer</summary>

**Answer: B. The long-term block retention policy used by the compactor**

Block time ranges, scans, deletion markers and deletion_delay affect actual removal. Local TSDB retention and Kafka retention are separate. S3 versioning, Object Lock and backups also affect complete deletion; a 365d setting alone is not a regulatory guarantee.

</details>

## 10. Which is not a sound availability assumption?

- A. Validate Kafka durability and recovery independently
- B. Match zone selectors to real schedulable nodes
- C. Place everything in one AZ and claim zone-failure tolerance
- D. Review ingester partition coverage, store-gateway replicas and rollout dependencies

<details>
<summary>Show answer</summary>

**Answer: C. Place everything in one AZ and claim zone-failure tolerance**

Logical zones are not physical placement. The example renders three ingesters/store-gateways in three selected zones, but broker topology, PVCs, capacity, queues, rollouts and other components still require validation. Cache redundancy and a single compactor do not establish end-to-end HA.

</details>

[Return to the chapter](../../../observability/metrics/03-mimir.md)
