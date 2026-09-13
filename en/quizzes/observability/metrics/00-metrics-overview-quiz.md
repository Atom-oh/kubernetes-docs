# Metrics Overview Quiz

> **Last Updated**: September 12, 2026

1. Which type represents a cumulative count that may reset?

   - A) Gauge
   - B) Counter
   - C) A precomputed p99
   - D) A scrape timestamp

<details>
<summary>Show answer</summary>

**Answer: B**

A Counter accumulates nonnegative increments. Resets can occur when the measured state is recreated. rate() handles observed resets, but cannot recover unobserved increments.

</details>

2. Five methods, twenty routes and ten statuses imply what?

   - A) Exactly 1,000 stored series in every deployment
   - B) At most 1,000 application label combinations if all combinations are possible
   - C) Exactly 1,000 samples per day
   - D) No effect on resource use

<details>
<summary>Show answer</summary>

**Answer: B**

The product is an upper bound. Actual combinations, target/replica labels, histogram buckets and historical churn determine the real series/storage footprint.

</details>

3. Which Pushgateway use is appropriate?

   - A) Use one HOSTNAME grouping key for every short-lived Pod and rely on automatic expiry
   - B) Use it for a suitable service-level batch with stable grouping, success timestamps and an explicit retirement policy
   - C) Treat gateway up=1 as proof that every batch succeeded
   - D) Push success timestamps even when the batch fails

<details>
<summary>Show answer</summary>

**Answer: B**

Pushgateway is not the default for all short-lived jobs and groups have no automatic TTL. Its scrape health is separate from batch freshness. Scraping with honor_labels preserves the pushed job identity.

</details>

4. Which statement about Histogram and Summary is correct?

   - A) Summary quantiles are always exact
   - B) Averaging instance p99 values gives fleet p99
   - C) Compatible classic histogram buckets can be combined; Summary sum/count can be combined for a mean
   - D) No Summary data can ever be aggregated

<details>
<summary>Show answer</summary>

**Answer: C**

Classic buckets are counted by the instrumented producer; Prometheus calculates quantiles at query time. Summary quantiles have algorithm/window-dependent error and are not aggregatable into a fleet quantile, while nonnegative-duration sum/count rates can yield a fleet mean.

</details>

5. Which is NOT the recommended convention for a new Prometheus application metric?

   - A) Use a descriptive prefix
   - B) Use a unit suffix such as _seconds or _bytes
   - C) Prefer camelCase and millisecond units over the usual base-unit convention
   - D) Use _total to identify a cumulative counter

<details>
<summary>Show answer</summary>

**Answer: C**

Prefer descriptive underscore-separated names and base units. _total is a counter marker, not a physical unit. Existing exporter APIs such as node_memory_MemAvailable_bytes retain their published spelling.

</details>

6. Which statement about Prometheus retention is correct?

   - A) It can never retain more than 30 days
   - B) The default is 15 days without explicit time/size retention settings; longer retention needs suitable configuration and capacity
   - C) It does not compress local data
   - D) Independent collection replicas are impossible without Mimir

<details>
<summary>Show answer</summary>

**Answer: B**

Default retention is not a maximum. Local TSDB is not a replicated distributed store; collection redundancy, query deduplication, durability and recovery are separate design decisions.

</details>

7. Which product/storage claim is incorrect?

   - A) VictoriaMetrics single-node and cluster deployments have different operating requirements
   - B) Traditional CloudWatch metric resolution becomes coarser with age
   - C) Mimir object storage guarantees unlimited scale and eliminates every local storage requirement
   - D) Datadog metrics use query rollups, so retention does not guarantee original resolution in every graph

<details>
<summary>Show answer</summary>

**Answer: C**

Object storage is part of Mimir's architecture, not a guarantee of unlimited capacity. Ingest/local resources, query limits, replication and operational capacity still matter. Do not conflate backup destinations or edition-specific features with a product's primary store.

</details>

8. Which approach fails to control metric cardinality?

   - A) Use normalized route templates
   - B) Avoid user/session IDs as ordinary labels
   - C) Group status codes when losing detail is acceptable
   - D) Assign a new request_id label value to every request

<details>
<summary>Show answer</summary>

**Answer: D**

Distinct label values create distinct series, including when values are hashed. Request-specific context belongs in appropriately controlled logs/traces when needed. Cardinality and sensitive-data exposure both require review.

</details>

9. Which Kubernetes metrics role is correctly matched?

   - A) node-exporter — Kubernetes API object status
   - B) kube-state-metrics — measured container CPU usage
   - C) cAdvisor/kubelet metrics — container resource measurements
   - D) metrics-server — long-term Prometheus TSDB

<details>
<summary>Show answer</summary>

**Answer: C**

node-exporter reports host OS metrics; kube-state-metrics exposes API object state; metrics-server serves the Resource Metrics API. Prometheus/vmalert/Mimir rules evaluate alerts, and Alertmanager routes them. vmagent is a collector/forwarder, not a queryable TSDB.

</details>

10. What makes a cost comparison reviewable?

   - A) A product ranking based only on team size
   - B) The node count without sample interval or feature assumptions
   - C) Measured series/sample volume, retention/resolution, HA/query requirements and current pricing for the selected features
   - D) Assuming metric name/value lengths never matter

<details>
<summary>Show answer</summary>

**Answer: C**

One million actual exported series at 15-second intervals over 30 days implies 172.8 billion samples before delivery filtering/deduplication. Infrastructure, indexes/WAL, replicas, query work, custom-metric allowances and operator effort can change costs. This is a workload calculation, not a provider quote.

</details>

[Return to the guide](../../../observability/metrics/README.md)
