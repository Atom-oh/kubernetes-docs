# Log Collectors Comparison Quiz

Test your understanding of log collectors (FluentBit, Promtail, Alloy, OTEL Collector).

---

1. Which of the following log collectors has the lowest memory usage?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) OpenTelemetry Collector

<details>
<summary>Show Answer</summary>

**Answer: B) FluentBit**

**Explanation:**
FluentBit is written in C and has the lowest memory usage at approximately 10-50MB. The others are written in Go and use approximately 50-100MB of memory.

</details>

---

2. Which FluentBit FILTER adds Kubernetes metadata (namespace, pod_name, etc.) to logs?

   - A) [FILTER] Name modify
   - B) [FILTER] Name kubernetes
   - C) [FILTER] Name parser
   - D) [FILTER] Name record_modifier

<details>
<summary>Show Answer</summary>

**Answer: B) [FILTER] Name kubernetes**

**Explanation:**
FluentBit's `kubernetes` filter automatically adds metadata such as pod, namespace, and labels to logs through the Kubernetes API.

</details>

---

3. What is Promtail's main limitation?

   - A) No JSON parsing support
   - B) Cannot send to destinations other than Loki
   - C) Cannot be used in Kubernetes environments
   - D) Cannot handle multiline logs

<details>
<summary>Show Answer</summary>

**Answer: B) Cannot send to destinations other than Loki**

**Explanation:**
Promtail is designed as a dedicated agent for Grafana Loki and does not support sending to other destinations like OpenSearch or CloudWatch. If multiple destinations are needed, use FluentBit or OTEL Collector.

</details>

---

4. What configuration language does Grafana Alloy use?

   - A) YAML
   - B) JSON
   - C) River (HCL-like)
   - D) INI

<details>
<summary>Show Answer</summary>

**Answer: C) River (HCL-like)**

**Explanation:**
Grafana Alloy uses River, a configuration language similar to HCL (HashiCorp Configuration Language). It is more expressive than YAML and allows defining reusable components.

</details>

---

5. What is the order of pipeline components in OpenTelemetry Collector?

   - A) Processors → Receivers → Exporters
   - B) Receivers → Exporters → Processors
   - C) Receivers → Processors → Exporters
   - D) Exporters → Processors → Receivers

<details>
<summary>Show Answer</summary>

**Answer: C) Receivers → Processors → Exporters**

**Explanation:**
OTEL Collector pipelines are composed in the order: Receivers (receive data) → Processors (process/transform data) → Exporters (send data).

</details>

---

6. What scripting language can be used in FluentBit to implement complex log processing logic?

   - A) Python
   - B) JavaScript
   - C) Lua
   - D) Ruby

<details>
<summary>Show Answer</summary>

**Answer: C) Lua**

**Explanation:**
FluentBit supports Lua scripting to implement complex log processing logic (field transformation, conditional processing, sensitive data masking, etc.). Use the `[FILTER] Name lua` filter.

</details>

---

7. What pipeline_stages setting in Promtail configuration excludes specific logs?

   - A) stage.filter
   - B) stage.drop
   - C) stage.exclude
   - D) stage.ignore

<details>
<summary>Show Answer</summary>

**Answer: B) stage.drop**

**Explanation:**
Promtail's `stage.drop` excludes log lines matching regex or conditions. Example: Use `expression: "healthcheck|readiness"` to exclude healthcheck logs.

</details>

---

8. Which collector is most suitable when you need to send logs to both CloudWatch Logs and OpenSearch in AWS environments?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) Logstash

<details>
<summary>Show Answer</summary>

**Answer: B) FluentBit**

**Explanation:**
FluentBit natively supports both `cloudwatch_logs` and `opensearch` output plugins. It can be easily deployed using the `aws-for-fluent-bit` image provided by AWS. Promtail and Alloy are optimized for Loki.

</details>

---

9. Which processor in OpenTelemetry Collector limits memory usage?

   - A) batch
   - B) memory_limiter
   - C) resource
   - D) filter

<details>
<summary>Show Answer</summary>

**Answer: B) memory_limiter**

**Explanation:**
The `memory_limiter` processor monitors OTEL Collector's memory usage and temporarily pauses data collection when the configured limit is reached to prevent OOM.

</details>

---

10. What is the recommended migration target when you need to also collect metrics and traces from an existing Promtail environment?

    - A) FluentBit
    - B) Logstash
    - C) Grafana Alloy
    - D) Filebeat

<details>
<summary>Show Answer</summary>

**Answer: C) Grafana Alloy**

**Explanation:**
Grafana Alloy is the successor project to Promtail, including all Promtail functionality while also being able to collect metrics (Prometheus) and traces (Tempo). Promtail configurations can be easily migrated to River syntax.

</details>
