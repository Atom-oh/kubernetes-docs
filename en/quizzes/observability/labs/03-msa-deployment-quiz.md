# Observability Lab Part 3: MSA Deployment and Canary Quiz

> **Last Updated**: February 2025

Test your understanding of MSA deployment and canary release concepts covered in the Observability End-to-End Lab Part 3.

---

1. Which ArgoCD ApplicationSet Generator type is most suitable for deploying the same application to multiple clusters?
   - A) List Generator with hardcoded cluster names
   - B) Cluster Generator that automatically discovers registered clusters based on labels
   - C) Git Generator that reads cluster configurations from repository
   - D) Pull Request Generator for ephemeral environments

<details>
<summary>Show Answer</summary>

**Answer: B) Cluster Generator that automatically discovers registered clusters based on labels**

**Explanation:**
The Cluster Generator dynamically discovers clusters registered with ArgoCD and generates Applications for each. By using cluster labels (e.g., `environment: production`, `region: us-east-1`), you can selectively target clusters. This is more maintainable than hardcoded lists because adding or removing clusters only requires updating cluster registrations and labels, not modifying ApplicationSet definitions.

</details>

---

2. What is the primary advantage of the App-of-Apps pattern in ArgoCD?
   - A) It reduces the total number of ArgoCD Applications needed
   - B) It enables hierarchical management where a parent Application manages child Applications, providing organizational structure and batch operations
   - C) It improves sync performance by parallelizing all deployments
   - D) It eliminates the need for Helm or Kustomize

<details>
<summary>Show Answer</summary>

**Answer: B) It enables hierarchical management where a parent Application manages child Applications, providing organizational structure and batch operations**

**Explanation:**
The App-of-Apps pattern creates a hierarchy where a root Application's manifests contain definitions for other Applications. This provides: centralized management of multiple applications, consistent configuration inheritance, easier bootstrapping of entire platforms, and the ability to apply changes to multiple applications by updating the parent. It's particularly useful for platform teams managing multiple microservices or multi-tenant environments.

</details>

---

3. What do weight and limits settings control in a Karpenter NodePool?
   - A) Weight determines CPU allocation per pod; limits set memory boundaries
   - B) Weight sets scheduling priority among NodePools; limits cap the total resources Karpenter can provision for that pool
   - C) Weight controls node pricing tiers; limits set maximum node count
   - D) Weight determines pod density; limits set network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B) Weight sets scheduling priority among NodePools; limits cap the total resources Karpenter can provision for that pool**

**Explanation:**
NodePool weight (0-100) determines preference when multiple NodePools can satisfy a pod's requirements—higher weight means higher priority. Limits define maximum resources (CPU, memory) that Karpenter can provision for that NodePool, preventing unbounded scaling. This allows creating tiered infrastructure: high-weight pools for preferred instance types with limits to control costs, and lower-weight fallback pools for overflow capacity.

</details>

---

4. Which metric types can KEDA's SQS scaler use for scaling decisions?
   - A) Only ApproximateNumberOfMessages
   - B) ApproximateNumberOfMessages, ApproximateNumberOfMessagesNotVisible, or ApproximateNumberOfMessagesDelayed
   - C) Only custom CloudWatch metrics
   - D) SQS scalers only support time-based scaling

<details>
<summary>Show Answer</summary>

**Answer: B) ApproximateNumberOfMessages, ApproximateNumberOfMessagesNotVisible, or ApproximateNumberOfMessagesDelayed**

**Explanation:**
KEDA's SQS scaler supports multiple queue metrics: `ApproximateNumberOfMessages` (visible messages ready for processing), `ApproximateNumberOfMessagesNotVisible` (messages being processed but not yet deleted), and `ApproximateNumberOfMessagesDelayed` (messages in delay queue). You can choose based on your scaling strategy—typically `ApproximateNumberOfMessages` for scaling based on backlog, or combined metrics for more comprehensive queue depth awareness.

</details>

---

5. What is the key difference between OpenTelemetry auto-instrumentation and manual instrumentation?
   - A) Auto-instrumentation provides more detailed traces than manual instrumentation
   - B) Auto-instrumentation automatically captures telemetry from supported frameworks without code changes while manual instrumentation requires explicit SDK calls for custom spans and metrics
   - C) Manual instrumentation is deprecated in favor of auto-instrumentation
   - D) Auto-instrumentation only works with interpreted languages

<details>
<summary>Show Answer</summary>

**Answer: B) Auto-instrumentation automatically captures telemetry from supported frameworks without code changes while manual instrumentation requires explicit SDK calls for custom spans and metrics**

**Explanation:**
Auto-instrumentation (via agents, bytecode manipulation, or monkey-patching) automatically captures telemetry from popular frameworks, libraries, and runtimes without modifying application code. Manual instrumentation uses the OTel SDK to explicitly create spans, add attributes, record metrics, and emit logs. Best practice is to combine both: auto-instrumentation for standard framework coverage, manual instrumentation for business-specific spans and custom metrics.

</details>

---

6. What does the `-javaagent:opentelemetry-javaagent.jar` JVM argument enable for Java services?
   - A) It enables JMX monitoring only
   - B) It attaches the OTel Java agent for automatic instrumentation of common Java frameworks and libraries
   - C) It configures Java garbage collection telemetry
   - D) It enables Java Flight Recorder integration

<details>
<summary>Show Answer</summary>

**Answer: B) It attaches the OTel Java agent for automatic instrumentation of common Java frameworks and libraries**

**Explanation:**
The OpenTelemetry Java agent uses bytecode instrumentation to automatically capture telemetry from popular Java frameworks (Spring, JAX-RS, gRPC), HTTP clients (Apache HttpClient, OkHttp), databases (JDBC, Hibernate), and messaging systems (Kafka, RabbitMQ). The agent is attached at JVM startup via `-javaagent` and requires no code changes. Configuration is done through environment variables (e.g., `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`).

</details>

---

7. What role does AnalysisTemplate play in Argo Rollouts canary deployments?
   - A) It defines the container image analysis for security scanning
   - B) It specifies metrics queries and success criteria that determine whether a canary release should proceed or rollback
   - C) It configures the traffic split percentages during canary
   - D) It manages the replica count during progressive delivery

<details>
<summary>Show Answer</summary>

**Answer: B) It specifies metrics queries and success criteria that determine whether a canary release should proceed or rollback**

**Explanation:**
AnalysisTemplate defines automated analysis for canary releases. It specifies: metric providers (Prometheus, Datadog, CloudWatch), queries to evaluate (e.g., error rate, latency), success/failure thresholds, and measurement intervals. During a rollout, Argo Rollouts creates AnalysisRuns from the template, continuously evaluating metrics. If criteria fail, the rollout automatically pauses or rolls back, enabling safe progressive delivery without manual intervention.

</details>

---

8. What does a success-rate PromQL query like `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))` measure?
   - A) Total number of successful requests in the last 5 minutes
   - B) The ratio of HTTP 2xx responses to total responses, representing the success rate
   - C) Average response time for successful requests
   - D) Number of unique successful users

<details>
<summary>Show Answer</summary>

**Answer: B) The ratio of HTTP 2xx responses to total responses, representing the success rate**

**Explanation:**
This PromQL query calculates success rate by dividing successful requests (HTTP 2xx status codes, matched by regex `2..`) by total requests, both computed as 5-minute rates. The `rate()` function calculates per-second average over the window, and `sum()` aggregates across all label dimensions. The result is a ratio between 0 and 1, typically displayed as a percentage. This is a key SLI for service reliability.

</details>

---

9. What happens automatically when an Argo Rollouts AnalysisRun returns a FAIL status?
   - A) The rollout continues but sends an alert
   - B) The rollout pauses and waits for manual intervention
   - C) The rollout automatically aborts and scales down the canary, restoring the stable version to full traffic
   - D) The AnalysisRun restarts with different parameters

<details>
<summary>Show Answer</summary>

**Answer: C) The rollout automatically aborts and scales down the canary, restoring the stable version to full traffic**

**Explanation:**
When an AnalysisRun fails (metrics exceed failure thresholds), Argo Rollouts automatically triggers a rollback: the canary ReplicaSet scales to zero, all traffic shifts back to the stable version, and the Rollout status becomes "Degraded". This automated rollback is a key safety feature of progressive delivery—problematic releases are automatically reverted without requiring human intervention, minimizing the blast radius of bad deployments.

</details>

---

10. Why is W3C TraceContext context propagation important when using the OpenTelemetry SDK?
    - A) It's required for metrics collection
    - B) It enables distributed tracing by passing trace context (trace ID, span ID, flags) across service boundaries in HTTP headers
    - C) It improves log compression
    - D) It's only needed for gRPC services

<details>
<summary>Show Answer</summary>

**Answer: B) It enables distributed tracing by passing trace context (trace ID, span ID, flags) across service boundaries in HTTP headers**

**Explanation:**
W3C TraceContext is a standardized format for propagating distributed trace information via HTTP headers (`traceparent`, `tracestate`). When service A calls service B, context propagation passes the trace ID and parent span ID, allowing service B's spans to be linked to service A's trace. Without proper propagation, traces break at service boundaries, showing disconnected segments instead of complete request flows. OTel SDK handles this automatically when configured, but services must forward the headers.

</details>
