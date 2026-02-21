# Observability Stack Quiz

> **Related Document**: [Observability Stack](../../ops/09-observability-stack.md)

## Multiple Choice Questions

### 1. What are the components of the LGTM observability stack?

- A) Linux, Git, Terminal, Make
- B) Loki (logs), Grafana (visualization), Tempo (traces), Mimir/Prometheus (metrics)
- C) Lambda, Gateway, Transit, Monitor
- D) Load balancer, Gateway, TLS, Mesh

<details>
<summary>Show Answer</summary>

**Answer: B) Loki (logs), Grafana (visualization), Tempo (traces), Mimir/Prometheus (metrics)**

**Explanation:**
LGTM is a Grafana Labs observability stack consisting of Loki for log aggregation, Grafana for visualization and dashboards, Tempo for distributed tracing, and Mimir (or Prometheus) for metrics. These components integrate seamlessly.

</details>

### 2. What is the difference between Loki's SimpleScalable and Distributed deployment modes?

- A) SimpleScalable is for testing only
- B) SimpleScalable separates read/write paths; Distributed adds more granular component separation
- C) Distributed is deprecated
- D) They are identical

<details>
<summary>Show Answer</summary>

**Answer: B) SimpleScalable separates read/write paths; Distributed adds more granular component separation**

**Explanation:**
SimpleScalable mode splits Loki into read and write paths that can scale independently. Distributed mode further separates components (ingesters, distributors, queriers, etc.) for maximum scalability and operational flexibility at large scale.

</details>

### 3. What is the purpose of tail-based sampling in Tempo?

- A) To sample the end of log files
- B) To make sampling decisions after seeing the complete trace
- C) To reduce query latency
- D) To compress trace data

<details>
<summary>Show Answer</summary>

**Answer: B) To make sampling decisions after seeing the complete trace**

**Explanation:**
Tail-based sampling waits until a trace is complete before deciding whether to store it. This allows keeping all error traces or slow traces while sampling normal traces, which head-based sampling cannot do since it decides at trace start.

</details>

### 4. What role does the OTEL Collector play in the observability stack?

- A) Storing metrics long-term
- B) Receiving, processing, and exporting telemetry data from applications
- C) Creating Grafana dashboards
- D) Managing user authentication

<details>
<summary>Show Answer</summary>

**Answer: B) Receiving, processing, and exporting telemetry data from applications**

**Explanation:**
The OpenTelemetry Collector acts as a telemetry pipeline, receiving traces, metrics, and logs from applications, processing them (batching, filtering, enriching), and exporting to backends like Tempo, Prometheus, and Loki.

</details>

### 5. How does Amazon Managed Prometheus (AMP) integrate with Prometheus?

- A) It replaces Prometheus entirely
- B) Prometheus uses remote_write to send metrics to AMP for storage
- C) AMP runs as a Prometheus sidecar
- D) AMP only works with CloudWatch

<details>
<summary>Show Answer</summary>

**Answer: B) Prometheus uses remote_write to send metrics to AMP for storage**

**Explanation:**
AMP provides a managed, scalable storage backend for Prometheus metrics. Prometheus continues to scrape and evaluate rules locally, but uses `remote_write` to ship metrics to AMP. Grafana then queries AMP using PromQL.

</details>

### 6. What is the recommended Loki label design strategy?

- A) Use as many labels as possible for flexibility
- B) Use bounded, low-cardinality labels to avoid index explosion
- C) Avoid using any labels
- D) Only use timestamp labels

<details>
<summary>Show Answer</summary>

**Answer: B) Use bounded, low-cardinality labels to avoid index explosion**

**Explanation:**
High-cardinality labels (like user IDs or request IDs) create too many streams and bloat the index. Labels should be low-cardinality (namespace, app, environment) while high-cardinality data goes in log content for filtering with LogQL.

</details>

### 7. What is the difference between Promtail and Grafana Alloy for log collection?

- A) Promtail only collects metrics
- B) Alloy is a unified agent supporting logs, metrics, and traces; Promtail is Loki-specific
- C) Promtail is newer than Alloy
- D) Alloy doesn't support Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) Alloy is a unified agent supporting logs, metrics, and traces; Promtail is Loki-specific**

**Explanation:**
Promtail is purpose-built for shipping logs to Loki. Grafana Alloy (formerly Agent) is a unified collector that handles logs, metrics, and traces using OpenTelemetry and native receivers, reducing the number of agents needed.

</details>

### 8. How do you configure Grafana datasource linking between Loki and Tempo?

- A) They automatically link without configuration
- B) Configure derived fields in Loki datasource pointing to Tempo datasource
- C) Install a separate linking plugin
- D) Export data to a common database

<details>
<summary>Show Answer</summary>

**Answer: B) Configure derived fields in Loki datasource pointing to Tempo datasource**

**Explanation:**
In Grafana's Loki datasource settings, configure derived fields with a regex to extract trace IDs from logs and link to the Tempo datasource. This creates clickable links from log lines to associated traces.

</details>

### 9. What is the purpose of Tempo's compactor component?

- A) To compress network traffic
- B) To merge trace blocks and manage retention
- C) To compile TraceQL queries
- D) To reduce dashboard loading time

<details>
<summary>Show Answer</summary>

**Answer: B) To merge trace blocks and manage retention**

**Explanation:**
The compactor merges smaller trace blocks into larger ones for storage efficiency and applies retention policies by deleting expired data. It runs as a separate process in distributed mode or within the monolithic binary.

</details>

### 10. When configuring OTEL Collector processors, what does the batch processor do?

- A) Assigns batch IDs to traces
- B) Groups telemetry into batches before export to improve efficiency
- C) Processes database batch operations
- D) Creates batch jobs in Kubernetes

<details>
<summary>Show Answer</summary>

**Answer: B) Groups telemetry into batches before export to improve efficiency**

**Explanation:**
The batch processor accumulates telemetry data and sends it in batches based on size or timeout thresholds. This reduces the number of outgoing requests, improves compression, and decreases load on receiving backends.

</details>
