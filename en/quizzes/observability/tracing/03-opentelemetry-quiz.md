# OpenTelemetry Quiz

> **Last Updated**: September 13, 2026

Test your understanding of OpenTelemetry.

---

1. Which three core signals does this guide focus on?
   - A) Logs, Metrics, Events
   - B) Traces, Metrics, Logs
   - C) Spans, Counters, Logs
   - D) Traces, Alerts, Logs

<details>
<summary>Show Answer</summary>

**Answer: B) Traces, Metrics, Logs**

**Explanation:**
This guide focuses on traces, metrics, and logs. OpenTelemetry also develops profiling support; stability differs by signal, component, and language. Correlation requires compatible resource attributes and propagated context, not merely enabling three exporters.

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

4. When is the Collector's tail_sampling processor useful compared with head-based sampling?
   - A) When minimizing resource usage
   - B) When observed span status and duration should influence sampling
   - C) When implementation needs to be simple
   - D) When sampling decisions need to be fast

<details>
<summary>Show Answer</summary>

**Answer: B) When observed span status and duration should influence sampling**

**Explanation:**
With the Collector 0.160.0 default `trace-complete` strategy, evaluation uses accumulated spans when the decision timer fires; the name does not prove the request or trace is complete. Spans already discarded by head sampling cannot be recovered. Late spans, capacity limits, retries and routing changes can affect retention. Stateful tail sampling requires spans of a trace to reach the same sampling Collector; it does not guarantee that every error or slow request is retained.

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
A Resource identifies the telemetry producer, for example through `service.name`, `service.version`, and `deployment.environment.name`. The configured SDK/provider associates it with emitted data. Kubernetes, cloud, or custom identity attributes require the appropriate configuration or detector; they are not all discovered automatically.

</details>

---

6. Which Kubernetes workload normally runs one Collector on each eligible node?
   - A) Sidecar pattern
   - B) DaemonSet pattern
   - C) Gateway pattern
   - D) Deployment pattern

<details>
<summary>Show Answer</summary>

**Answer: B) DaemonSet pattern**

**Explanation:**
A DaemonSet places a Pod on each eligible node; selectors, taints and scheduling constraints determine eligibility. It is not supported on EKS Fargate. Sidecars share an application Pod, while gateways use a central tier that may have multiple replicas. No pattern is universally the most resource-efficient: compare actual signal volume, node/Pod counts, isolation, availability and stateful processing needs. A ClusterIP Service in front of a DaemonSet does not automatically route to the local node.

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
The Operator uses language-specific injection annotations. For a Deployment, place them on `spec.template.metadata.annotations` and reference an existing Instrumentation resource in the correct namespace. Successful injection also requires a working webhook and supported language/runtime configuration. Existing Pods are not retroactively instrumented; Go and other language-specific prerequisites must be reviewed separately.

</details>

---

8. What is the role of the memory_limiter processor in OTEL Collector configuration?
   - A) Data compression
   - B) Applying backpressure as configured memory thresholds are exceeded
   - C) Cache management
   - D) Network buffer management

<details>
<summary>Show Answer</summary>

**Answer: B) Applying backpressure as configured memory thresholds are exceeded**

**Explanation:**
`limit_mib` is the hard limit; the soft limit is `limit_mib - spike_limit_mib`. Above the soft limit, the processor refuses data with a retryable error. Above the hard limit, it also forces garbage collection. Upstream retry/backpressure behavior matters: refused data can be lost if it is not retried. Leave headroom below the container memory limit; this processor is neither durable storage nor an absolute OOM/data-loss guarantee.

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
OpenTelemetry uses the W3C Trace Context standard. The `traceparent` fields are version, trace ID, parent ID and trace flags; the parent ID identifies the sending span, and the flags include a sampled bit. A span name is not carried in this header. Propagating context does not itself record or export a span.

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
List configured exporters that support the pipeline's signal, for example `exporters: [otlp/tempo, awsxray, datadog]` for traces in a distribution containing those components. Fan-out is not an atomic transaction across backends: exporter errors, queues, retries, transformations and backend acceptance can produce different retained results.

</details>

---

[Return to the guide](../../../observability/tracing/03-opentelemetry.md)
