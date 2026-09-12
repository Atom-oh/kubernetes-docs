# Observability stack quiz

> **Related document**: [Observability stack](../../ops/09-observability-stack.md)

## 1. Which statement should guide a new Loki deployment?

- A) SimpleScalable is the permanent default for all new deployments
- B) SimpleScalable is deprecated and scheduled for removal in 4.0; evaluate alternatives
- C) Monolithic cannot use object storage
- D) Three replicas automatically guarantee AZ isolation

<details>
<summary>Show answer</summary>

**Answer: B**

The read/write/backend split describes SSD's architecture. New designs must also assess its lifecycle and the capacity/operational constraints of Monolithic and Distributed modes.

</details>

## 2. How do Tempo 3 distributed and monolithic modes differ?

- A) Both retain the old ingester
- B) Monolithic always requires Kafka
- C) Distributed mode uses Kafka; monolithic can run without Kafka
- D) Increasing monolithic chart replicas produces supported distributed HA

<details>
<summary>Show answer</summary>

**Answer: C**

Version 3 uses block-builders/live-stores and backend-scheduler/workers instead of the distributed ingester/compactor architecture. Do not mix its deployment modes.

</details>

## 3. Which limitation applies to tail sampling?

- A) It always preserves every error trace
- B) It decides from spans received within decision_wait and cannot recover head-dropped data
- C) Random Service balancing always keeps a trace on one sampler
- D) num_traces is the trace-per-second rate

<details>
<summary>Show answer</summary>

**Answer: B**

Late spans, buffer limits, restarts and transport failures matter. Multiple samplers require trace-ID-based routing.

</details>

## 4. What does the batch processor's send_batch_size control?

- A) Maximum batch size
- B) Maximum trace duration
- C) An item-count trigger for sending
- D) Persistent storage capacity

<details>
<summary>Show answer</summary>

**Answer: C**

send_batch_max_size is the batch-size ceiling. Place batching after memory limiting and sampling/drop processing.

</details>

## 5. What happens if every Alloy DaemonSet pod collects every cluster log target?

- A) Perfect HA deduplication is automatic
- B) Collection can duplicate; partition targets or configure source clustering
- C) The Kubernetes API automatically permits only one collector
- D) It cannot start because hostPath is always required

<details>
<summary>Show answer</summary>

**Answer: B**

The Kubernetes logs API source differs from file tailing. The single Deployment/Recreate example reduces duplication but does not provide HA or uninterrupted collection.

</details>

## 6. What is required for Loki retention?

- A) Only retention_period
- B) A 24-hour TSDB index, enabled compactor retention, delete_request_store and retention period
- C) Expire every object in the bucket at the same age
- D) The Grafana dashboard time range

<details>
<summary>Show answer</summary>

**Answer: B**

Deletion is delayed and asynchronous, and compactor state/markers must survive restarts. Bucket-wide lifecycle expiration can damage required objects such as indexes.

</details>

## 7. Which labels identify an AMP HA group and its replicas?

- A) namespace and pod
- B) cluster and __replica__
- C) service and trace_id
- D) region alone

<details>
<summary>Show answer</summary>

**Answer: B**

Replicas of the same scrape data share cluster and use distinct __replica__ values. Grouping independent scrape coverage into one HA group can lose data.

</details>

## 8. Which statement about AMP retention is correct?

- A) 150 days is an immutable maximum
- B) It is configurable per workspace up to 1,095 days
- C) It is always unlimited
- D) Increasing it restores already deleted metrics

<details>
<summary>Show answer</summary>

**Answer: B**

Set retention after assessing requirements, cost and service limits. Expired data is not retroactively restored.

</details>

## 9. What is needed to link a Loki log to a Tempo trace in Grafana?

- A) Installing both automatically links them
- B) Correct trace-ID extraction, explicit datasource UIDs and accessible trace data
- C) Add trace IDs as ordinary Prometheus labels
- D) Enable HTTP/2 alone

<details>
<summary>Show answer</summary>

**Answer: B**

Match derivedFields/tracesToLogsV2 mappings, time range, tenancy and permissions. Exemplars also require instrumentation, OpenMetrics and storage configuration.

</details>

## 10. What must still be checked after chart rendering succeeds?

- A) Nothing; all unknown values are applied
- B) Actual PVCs, Services, identity, backend configuration and write/query paths
- C) Only YAML indentation
- D) Replace every image with latest

<details>
<summary>Show answer</summary>

**Answer: B**

Some chart values can be silently ignored. Check claims/accessModes and Service ports, and distinguish native parser validation from live environment connectivity.

</details>
