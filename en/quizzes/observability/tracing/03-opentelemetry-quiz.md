# OpenTelemetry Quiz

Test your understanding of OpenTelemetry.

---

1. What are the three signals supported by OpenTelemetry?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>Show Answer</summary>

**Answer: B) Traces, Metrics, Logs**

**Explanation:**
OpenTelemetry standardizes the three core observability signals: Traces (distributed tracing), Metrics, and Logs. By collecting and correlating these three signals in an integrated way, you can achieve comprehensive system observability.

</details>

---

2. What is the correct order of OpenTelemetry Collector components?
   - A) Processors -> Receivers -> Exporters
   - B) Exporters -> Processors -> Receivers
   - C) Receivers -> Processors -> Exporters
   - D) Receivers -> Exporters -> Processors

<details>
<summary>Show Answer</summary>

**Answer: C) Receivers -> Processors -> Exporters**

**Explanation:**
The OTEL Collector pipeline is structured as Receivers (data ingestion) -> Processors (data processing/transformation) -> Exporters (backend transmission). Receivers accept data in various formats, Processors perform batch processing, filtering, attribute addition, etc., and Exporters send processed data to destinations.

</details>

---

3. Which is NOT an advantage of auto-instrumentation in OpenTelemetry?
   - A) Instrumentation without code changes
   - B) Fast adoption
   - C) Fine-grained business logic tracing
   - D) Consistent metadata

<details>
<summary>Show Answer</summary>

**Answer: C) Fine-grained business logic tracing**

**Explanation:**
Auto-instrumentation automatically traces common library calls like HTTP, databases, and message queues without code changes. However, detailed operations within business logic or custom metrics require manual instrumentation. It's common to use both auto-instrumentation and manual instrumentation together.

</details>

---

4. When is the OTEL Collector's tail_sampling processor more advantageous than head-based sampling?
   - A) When minimizing resource usage
   - B) When you can't miss requests with errors or latency
   - C) When implementation needs to be simple
   - D) When sampling decisions need to be fast

<details>
<summary>Show Answer</summary>

**Answer: B) When you can't miss requests with errors or latency**

**Explanation:**
Tail-based sampling decides whether to sample after the request completes, based on results (errors, latency, etc.). This ensures important requests (error occurrences, response time exceeded) are never missed. In contrast, head-based sampling decides at request start, so it's simpler to implement with lower resource usage, but may miss important requests.

</details>

---

5. What is the role of Resource in the OpenTelemetry SDK?
   - A) Network connection management
   - B) Identifying the entity generating telemetry data
   - C) Data compression
   - D) Authentication token management

<details>
<summary>Show Answer</summary>

**Answer: B) Identifying the entity generating telemetry data**

**Explanation:**
Resource is metadata that identifies the entity (service, host, container, etc.) generating telemetry data. It includes attributes like service.name, service.version, deployment.environment to clarify the source of data. This information is automatically attached to all telemetry data.

</details>

---

6. Which OTEL Collector deployment pattern is most resource-efficient in EKS?
   - A) Sidecar pattern
   - B) DaemonSet pattern
   - C) Gateway pattern
   - D) Deployment pattern

<details>
<summary>Show Answer</summary>

**Answer: B) DaemonSet pattern**

**Explanation:**
The DaemonSet pattern is resource-efficient as it runs only one Collector per node. The Sidecar pattern has high resource overhead as it runs a Collector for each Pod. The Gateway pattern is centralized but can become a single point of failure. Typically, a combination of DaemonSet for collection and Gateway for processing/transmission is recommended.

</details>

---

7. What annotation is applied to a Pod for auto-instrumentation injection using the OpenTelemetry Operator?
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>Show Answer</summary>

**Answer: B) instrumentation.opentelemetry.io/inject-java: "true"**

**Explanation:**
The OpenTelemetry Operator uses annotations in the format `instrumentation.opentelemetry.io/inject-{language}`. Language-specific annotations include inject-java, inject-python, inject-nodejs, inject-dotnet, inject-go, etc. Instrumentation agents are automatically injected into Pods with these annotations.

</details>

---

8. What is the role of the memory_limiter processor in OTEL Collector configuration?
   - A) Data compression
   - B) Preventing data loss when memory is low
   - C) Cache management
   - D) Network buffer management

<details>
<summary>Show Answer</summary>

**Answer: B) Preventing data loss when memory is low**

**Explanation:**
The memory_limiter processor monitors and limits the Collector's memory usage. When memory usage reaches limit_mib, it refuses new data ingestion to prevent data loss due to OOM (Out of Memory). spike_limit_mib provides a buffer for sudden memory spikes.

</details>

---

9. Which is NOT a component of the traceparent header in OpenTelemetry's W3C Trace Context standard?
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>Show Answer</summary>

**Answer: D) span-name**

**Explanation:**
The W3C Trace Context traceparent header format is `version-trace_id-parent_id-trace_flags`. version is the format version, trace_id is the entire trace identifier, parent_id is the parent span ID, and trace_flags is the sampling flag. span-name is stored within the Span and is not included in the propagation header.

</details>

---

10. How do you configure sending data to multiple backends in an OTEL Collector pipeline?
    - A) Run separate Collectors for each backend
    - B) List multiple exporters in the exporters array
    - C) Configure multiple endpoints in a single exporter
    - D) Use a fanout processor

<details>
<summary>Show Answer</summary>

**Answer: B) List multiple exporters in the exporters array**

**Explanation:**
In the OTEL Collector pipeline configuration, listing multiple exporters in the exporters array sends the same data to all backends. For example: `exporters: [otlp/tempo, awsxray, datadog]`. This allows using multiple observability backends simultaneously with a single Collector.

</details>

---
