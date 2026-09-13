# Grafana Loki Quiz

> **Last Updated**: September 13, 2026

Based on the Loki3.7.7/chart18.12.1 examples in the [guide](../../../observability/logging/01-loki.md).

---

1. What does Loki primarily index in the TSDB/chunk model?

   - A) Every word in every log line
   - B) Stream labels
   - C) Only request IDs
   - D) Only timestamps

<details>
<summary>Show answer</summary>

**Answer: B**

Labels narrow the streams to scan. This does not prove a fixed10× cost advantage or eliminate parsing/chunk-read costs.

</details>

---

2. Which component buffers log streams, writes the WAL when enabled and flushes chunks?

   - A) Distributor
   - B) Query frontend
   - C) Ingester
   - D) Index gateway

<details>
<summary>Show answer</summary>

**Answer: C**

The Ingester also serves recent data. WAL needs persistent storage and is not by itself a lossless-delivery or HA guarantee.

</details>

---

3. Which statement matches the current deployment guidance used by this chapter?

   - A) SSD is permanently the default for all production EKS clusters
   - B) Any three Pods guarantee three-AZ resilience
   - C) SingleBinary is the only chart18.12.1 mode name
   - D) SSD is deprecated; production scaling/HA guidance recommends Distributed with explicit operational planning

<details>
<summary>Show answer</summary>

**Answer: D**

SSD is scheduled for removal in Loki4.0. Capacity and availability depend on workload, storage, topology and tested failure handling, not a fixed GB/day table.

</details>

---

4. Which query returns a per-second rate of matching error log lines over five minutes?

   - A) `rate({app="nginx"} |= "error" [5m])`
   - B) `count({app="nginx"} |= "error")`
   - C) `sum({app="nginx"} |= "error")`
   - D) `increase(count_over_time({app="nginx"}[5m]))`

<details>
<summary>Show answer</summary>

**Answer: A**

This is a log-line rate per stream, not automatically an HTTP request error ratio. LogQL count vector aggregation exists, but B does not provide the required metric-vector input.

</details>

---

5. A unique request ID is needed for investigation. What is the better starting point?

   - A) Index every request ID for faster queries
   - B) Keep necessary IDs in log content or structured metadata under access/privacy controls
   - C) Remove all cluster/namespace labels
   - D) Assume total streams always equal the product of label cardinalities

<details>
<summary>Show answer</summary>

**Answer: B**

High-cardinality index values can create many streams. Structured metadata is not redaction, and the cardinality product is only an upper bound on observed combinations.

</details>

---

6. In the IRSA example, how is ServiceAccount ownership kept consistent?

   - A) eksctl and Helm both create the same ServiceAccount
   - B) Put S3 access keys in the Helm values
   - C) Use eksctl --role-only; Helm creates the matching annotated ServiceAccount
   - D) Give all nodes the bucket policy and disable authentication

<details>
<summary>Show answer</summary>

**Answer: C**

The role trust must match the exact cluster OIDC provider, audience and namespace/service-account subject. Pod Identity is also an option when its platform/SDK prerequisites are met.

</details>

---

7. Which query filters a JSON field and excludes parser failures?

   - A) `{app="api"} | json | level="error" | __error__=""`
   - B) `{app="api"} | json | where level="error"`
   - C) `{app="api"} | json | select level="error"`
   - D) `{app="api"} | json | filter level="error"`

<details>
<summary>Show answer</summary>

**Answer: A**

LogQL uses a label-filter stage after parsing. For an unwrapped numeric metric, place the error filter after unwrap to exclude conversion errors as well.

</details>

---

8. What is the role of the Compactor in this TSDB deployment?

   - A) Authenticate gateway users
   - B) Receive all client push requests
   - C) Guarantee all logs expire exactly31days after ingestion
   - D) Compact index files and asynchronously delete marked chunks when retention is enabled

<details>
<summary>Show answer</summary>

**Answer: D**

It is not a general small-log-chunk merger. Retention needs compatible schema/index period, enabled processing, a deletion store and durable marker state;31days is an example policy.

</details>

---

9. What should happen first after an ingestion429 response?

   - A) Increase every limit without measuring capacity
   - B) Distinguish tenant byte rate/burst, per-stream rate and active-stream limits, then inspect capacity/client retries
   - C) Increase query timeout only
   - D) Disable all limits permanently

<details>
<summary>Show answer</summary>

**Answer: B**

Ingestion-rate and burst limits are under limits_config. Raising a limit can overload the backend, and retries need backoff and a bounded loss/buffering policy.

</details>

---

10. Which statement correctly describes chunk_idle_period and /flush?

   - A) Both are read-only status endpoints
   - B) chunk_idle_period is the log retention period
   - C) chunk_idle_period controls idle flushing; POST /flush actively triggers flushing
   - D) Reducing chunk_idle_period always reduces total cost

<details>
<summary>Show answer</summary>

**Answer: C**

Shorter idle times may produce more small chunks and object requests. A flush operation is not a health check, and readiness is not proof of end-to-end durability.

</details>
