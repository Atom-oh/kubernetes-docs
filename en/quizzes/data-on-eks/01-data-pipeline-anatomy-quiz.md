# Anatomy of a Modern Data Pipeline Quiz

> **Last Updated**: August 28, 2026

Tests your understanding of the five data pipeline layers (source, ingestion, storage, processing, consumption) and the contracts between them.

## Multiple Choice Questions

1. Why is a streaming queue (such as Kafka) considered more than just a transport?
   - A) Because it automatically curates data to match the warehouse schema
   - B) Because consumer offsets can be rewound within the retention window for re-consumption, making it the anchor for reprocessing
   - C) Because it always has higher throughput than batch connectors
   - D) Because it can replace the storage layer

<details>
<summary>Show Answer</summary>

**Answer: B) Because consumer offsets can be rewound within the retention window for re-consumption, making it the anchor for reprocessing**

**Explanation:**
A streaming queue retains events for its retention window, so after an incident or a logic fix you can rewind offsets and re-consume. The processing layer's correctness guarantees (exactly-once and friends) are built on this reprocessing ability.

</details>

2. What is the most common division of roles between a data lake and a warehouse?
   - A) Land raw data in the warehouse first, keeping the lake only as backup
   - B) Land raw data in the lake first to preserve reprocessing ability, then load curated versions into the warehouse (ELT)
   - C) Double-write identical data to both lake and warehouse
   - D) Streaming data goes only to the warehouse, batch data only to the lake

<details>
<summary>Show Answer</summary>

**Answer: B) Land raw data in the lake first to preserve reprocessing ability, then load curated versions into the warehouse (ELT)**

**Explanation:**
Keeping the raw originals in a low-cost lake means you can always reprocess when logic changes later. Loading only curated data into the query-optimized warehouse is the standard ELT pattern — and increasingly, an open table format like Iceberg lets one lake play both roles (the lakehouse).

</details>

3. What is the purpose of the typical pattern that computes the same metric in both stream and batch processing?
   - A) To find bugs by comparing the two results
   - B) To serve a real-time approximation from streaming while batch recomputes the exact value — satisfying different freshness/accuracy contracts at once
   - C) To run batch only when stream processing fails
   - D) To split processing costs between two teams

<details>
<summary>Show Answer</summary>

**Answer: B) To serve a real-time approximation from streaming while batch recomputes the exact value — satisfying different freshness/accuracy contracts at once**

**Explanation:**
Live dashboards prioritize freshness in seconds; settlement prioritizes exactness. Batch and stream are a division of labor by latency requirement, and per-consumer freshness/accuracy contracts drive that design in reverse.

</details>

4. What is the standard defense against the classic pipeline outage — a source schema change silently propagating downstream?
   - A) Consolidating every layer into a single database
   - B) Managing source schema changes as contracts, via a schema registry and compatibility rules
   - C) Daily manual inspection at the consumption layer
   - D) Disabling CDC and using only full snapshots

<details>
<summary>Show Answer</summary>

**Answer: B) Managing source schema changes as contracts, via a schema registry and compatibility rules**

**Explanation:**
When a source schema changes without notice, the breakage is discovered only at the consumption layer. Registering schemas in a registry and enforcing compatibility rules (backward/forward) blocks incompatible changes at deployment time.

</details>

---

[Back to Study Material](../../data-on-eks/01-data-pipeline-anatomy.md) | [Next Quiz: Kafka Fundamentals](./kafka/01-kafka-fundamentals-quiz.md)
