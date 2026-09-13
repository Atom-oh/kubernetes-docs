# Grafana Tempo Quiz

> **Last Updated**: September 13, 2026

Baseline: Tempo 3.0.3 and chart 3.6.0.

---

1. What best describes Tempo storage and search?

   - A) Every attribute must be indexed in Elasticsearch
   - B) Object-store Parquet blocks support TraceID/TraceQL; storage and querying still have costs
   - C) Knowing an ID recovers every dropped span
   - D) Tempo retains traces forever

<details>
<summary>Show Answer</summary>

**Answer: B) Object-store Parquet blocks support TraceID/TraceQL; storage and querying still have costs**

Dedicated columns, metadata and caches do not mean zero indexing or query cost. Only successfully ingested, retained data is available.

</details>

---

2. Which component receives and validates trace data before the Tempo 3 distributed write path commits to Kafka?

   - A) Block-builder
   - B) Querier
   - C) Distributor
   - D) Backend worker

<details>
<summary>Show Answer</summary>

**Answer: C) Distributor**

The distributor writes to Kafka. Live-stores, block-builders and optional metrics-generators consume separately; this is not the Tempo 2 ingester path.

</details>

---

3. Which TraceQL query selects spans with error status?

   - A) `{ duration > 1s }`
   - B) `{ status = error }`
   - C) `{ status = ok }`
   - D) `{ span.http.response.status_code = 200 }`

<details>
<summary>Show Answer</summary>

**Answer: B) `{ status = error }`**

Span status error is distinct from a latency threshold or an arbitrary HTTP response condition.

</details>

---

4. Which identity configuration does this EKS/S3 example use?

   - A) Static access keys in Helm values
   - B) The node role shared by every workload
   - C) IRSA bound to monitoring:tempo with exact OIDC sub/aud and scoped S3 permissions
   - D) An unrelated ServiceAccount with no Pod association

<details>
<summary>Show Answer</summary>

**Answer: C) IRSA bound to monitoring:tempo with exact OIDC sub/aud and scoped S3 permissions**

The role annotation and every Tempo Pod ServiceAccount must agree. Other workload-identity approaches need their own pinned-image compatibility check.

</details>

---

5. Which is not generated from traces by the illustrated metrics-generator processors?

   - A) Service graph metrics
   - B) Span metrics
   - C) Arbitrary application log metrics
   - D) Rate/error/duration metrics derived from spans

<details>
<summary>Show Answer</summary>

**Answer: C) Arbitrary application log metrics**

Span-metrics and service-graphs need explicit processor activation and remote write. They do not turn arbitrary logs into metrics.

</details>

---

6. Which statement about Tempo 3 durability is correct?

   - A) Three Tempo replicas always guarantee zero loss
   - B) Microservices use Kafka; its replication, ISR, retention and recovery must be designed separately
   - C) Monolithic mode always requires Kafka
   - D) Every StatefulSet automatically has a persistent PVC

<details>
<summary>Show Answer</summary>

**Answer: B) Microservices use Kafka; its replication, ISR, retention and recovery must be designed separately**

The chart uses emptyDir for live-store/block-builder data. Kafka durability is not established by a Tempo replica count; monolithic mode does not require Kafka.

</details>

---

7. Which Grafana correlation direction is correct?

   - A) Same namespace alone creates correlation
   - B) Tempo tracesToLogsV2 provides Trace→Logs; Loki derivedFields provides Logs→Trace
   - C) Both systems must share an S3 bucket
   - D) derivedFields causes applications to generate TraceIDs

<details>
<summary>Show Answer</summary>

**Answer: B) Tempo tracesToLogsV2 provides Trace→Logs; Loki derivedFields provides Logs→Trace**

Identifiers, data-source UIDs, labels and the queried time range must match real data. A link cannot recover missing telemetry.

</details>

---

8. Which components handle Tempo 3 background compaction and retention work?

   - A) Grafana browser tabs
   - B) OTLP clients
   - C) Backend scheduler and backend workers
   - D) The old compactor configuration copied unchanged

<details>
<summary>Show Answer</summary>

**Answer: C) Backend scheduler and backend workers**

These replace the old compactor architecture. Retention is asynchronous, and an independent blanket S3 expiration rule can conflict with backend operations.

</details>

---

9. What does `{ resource.service.name = "A" } >> { resource.service.name = "B" }` select?

   - A) Any two spans in different traces
   - B) Matching B descendants of matching A spans
   - C) Only A parents, never B
   - D) Only direct B children

<details>
<summary>Show Answer</summary>

**Answer: B) Matching B descendants of matching A spans**

The result is on the right-hand side. Use > for direct children. Neither sibling matching nor a same-trace membership test means the same thing.

</details>

---

10. What is the safest first response to slow queries and apparently empty recent searches?

   - A) Copy ingester.max_block_duration: 30m from Tempo 2
   - B) Disable all lag and recent-query protections
   - C) Check time range, actual received data, lag, scan volume and limits before tuning
   - D) Turn missing telemetry and zero traffic into a guaranteed healthy value

<details>
<summary>Show Answer</summary>

**Answer: C) Check time range, actual received data, lag, scan volume and limits before tuning**

Tempo 3 has different components/defaults. Empty results, zero traffic and failures are distinct; configuration rendering alone does not prove a production system works.

</details>

---

[Review the Tempo guide](../../../observability/tracing/01-tempo.md).
