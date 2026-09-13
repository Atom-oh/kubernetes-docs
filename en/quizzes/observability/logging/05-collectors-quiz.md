# Log Collectors Comparison Quiz

> **Last Updated**: September 13, 2026

1. How should collector resource requirements be compared?

   - A) Assume a fixed memory ranking from implementation language
   - B) Benchmark the same records, processing, destinations and failure settings
   - C) Treat every Go collector as identical
   - D) Use a single published events/second number

<details>
<summary>Show answer</summary>

**Answer: B) Benchmark the same records, processing, destinations and failure settings**

Buffer limits, metadata caches, batching, retries and concurrency affect resource use. A language or compression format alone does not establish a throughput guarantee.

</details>

---

2. Which Fluent Bit filter adds Pod and namespace metadata?

   - A) modify
   - B) parser
   - C) kubernetes
   - D) record_modifier only

<details>
<summary>Show answer</summary>

**Answer: C) kubernetes**

The kubernetes filter needs correct tags and authorized metadata access. Enabling Use_Kubelet requires its own kubelet connectivity and permission checks.

</details>

---

3. What is the correct current approach to Promtail?

   - A) Migrate: it reached EOL on March 2, 2026
   - B) Choose it for every new Loki deployment
   - C) Assume existing installations still receive future updates
   - D) The retirement also automatically includes lambda-promtail

<details>
<summary>Show answer</summary>

**Answer: A) Migrate: it reached EOL on March 2, 2026**

The official lifecycle notice directs migration to Alloy or another supported client and explicitly excludes the separate lambda-promtail client from that notice.

</details>

---

4. What syntax does Grafana Alloy use?

   - A) Any Kubernetes YAML without conversion
   - B) Alloy configuration syntax, formerly River
   - C) Terraform HCL with all Terraform providers
   - D) Only INI

<details>
<summary>Show answer</summary>

**Answer: B) Alloy configuration syntax, formerly River**

The syntax is HCL-like, but an Alloy component graph is not an interchangeable Terraform file. Validate it with the selected Alloy binary.

</details>

---

5. What is the usual Collector pipeline order?

   - A) Exporters → Receivers → Processors
   - B) Processors → Exporters → Receivers
   - C) Receivers → Processors → Exporters
   - D) All components run in an arbitrary order

<details>
<summary>Show answer</summary>

**Answer: C) Receivers → Processors → Exporters**

Connectors can link pipelines. The current Loki path uses OTLP HTTP; the removed loki exporter is not present in Contrib0.160.0.

</details>

---

6. What does the example Lua transform guarantee?

   - A) Removal of every possible secret from arbitrary text
   - B) Deletion of original node log files
   - C) Exactly-once delivery
   - D) Redaction of selected structured keys and removal of the raw duplicate

<details>
<summary>Show answer</summary>

**Answer: D) Redaction of selected structured keys and removal of the raw duplicate**

It is not a general PII detector or a fail-closed boundary. Plaintext and free-text message values may still contain sensitive data.

</details>

---

7. Which names correctly distinguish legacy Promtail and Alloy drop stages?

   - A) Both use stage.drop as the Promtail YAML key
   - B) Promtail YAML drop; Alloy stage.drop
   - C) Promtail filter.exclude; Alloy ignore
   - D) Neither supports dropping records

<details>
<summary>Show answer</summary>

**Answer: B) Promtail YAML drop; Alloy stage.drop**

Parser, template, labels and output stages also have ordering and field-retention effects. Do not treat a stage catalogue as one universal processing chain.

</details>

---

8. Which are native Fluent Bit output plugin names for the two AWS destinations?

   - A) cloudwatch_logs and opensearch
   - B) cloudwatch and elastic only
   - C) stage.cloudwatch and stage.opensearch
   - D) Loki tenant_id creates both AWS destinations

<details>
<summary>Show answer</summary>

**Answer: A) cloudwatch_logs and opensearch**

Plugin availability does not grant IAM permissions. Match the real ServiceAccount identity, Region, endpoint, TLS and pre-created resource ownership.

</details>

---

9. What does memory_limiter do when under memory pressure?

   - A) Guarantees that the process can never OOM
   - B) Creates additional node memory
   - C) Can refuse data with retryable errors and request garbage collection
   - D) Persists every source record automatically

<details>
<summary>Show answer</summary>

**Answer: C) Can refuse data with retryable errors and request garbage collection**

Receiver retry behavior, limits and queues matter. The bounded filelog retry window can expire and discard a failed batch.

</details>

---

10. What must follow a successful Promtail-to-Alloy conversion?

   - A) Immediately declare identical delivery and metrics
   - B) Ignore all diagnostic warnings
   - C) Run both agents on the same logs indefinitely
   - D) Verify parsing, state, ownership, authentication, self-metrics and real backend records

<details>
<summary>Show answer</summary>

**Answer: D) Verify parsing, state, ownership, authentication, self-metrics and real backend records**

The converter can change a global rate limit to per-pipeline limits and does not validate host mounts or Kubernetes permissions. Choose file or API ownership to avoid duplicate collection.

</details>

---

[Return to the guide](../../../observability/logging/05-collectors.md)
