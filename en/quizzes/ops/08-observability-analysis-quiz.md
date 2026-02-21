# Observability Analysis Quiz

> **Related Document**: [Observability Analysis](../../ops/08-observability-analysis.md)

## Multiple Choice Questions

### 1. What is a Trace ID in distributed tracing?

- A) A unique identifier for a single span
- B) A unique identifier that correlates all spans in a request across services
- C) The name of a service
- D) A timestamp

<details>
<summary>Show Answer</summary>

**Answer: B) A unique identifier that correlates all spans in a request across services**

**Explanation:**
A Trace ID is a unique identifier assigned when a request enters the system and propagated through all downstream service calls. It allows connecting logs, spans, and metrics from different services that handled the same request.

</details>

### 2. What is the correct LogQL query to find error logs in a specific namespace?

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>Show Answer</summary>

**Answer: B) `{namespace="production"} |= "error"`**

**Explanation:**
LogQL uses label selectors in curly braces followed by filter expressions. `{namespace="production"}` selects logs from that namespace, and `|= "error"` filters for lines containing "error". The `|=` operator performs case-sensitive substring matching.

</details>

### 3. What does the RED method measure?

- A) Resource usage, Events, Duration
- B) Rate, Errors, Duration (for services)
- C) Requests, Endpoints, Data
- D) Replicas, Endpoints, Deployments

<details>
<summary>Show Answer</summary>

**Answer: B) Rate, Errors, Duration (for services)**

**Explanation:**
The RED method measures service health through Rate (requests per second), Errors (failed request rate), and Duration (latency distribution). It's optimized for request-driven services and complements the USE method for resources.

</details>

### 4. What does the USE method measure?

- A) User, Session, Events
- B) Utilization, Saturation, Errors (for resources)
- C) Upload, Storage, Encryption
- D) Units, Scale, Efficiency

<details>
<summary>Show Answer</summary>

**Answer: B) Utilization, Saturation, Errors (for resources)**

**Explanation:**
The USE method measures resource health through Utilization (percentage busy), Saturation (queue depth/waiting), and Errors (error counts). It's designed for analyzing CPU, memory, network, and storage resources.

</details>

### 5. What are Exemplars in Prometheus?

- A) Example configuration files
- B) Trace IDs attached to metric samples enabling metric-to-trace correlation
- C) Sample Prometheus queries
- D) Template dashboards

<details>
<summary>Show Answer</summary>

**Answer: B) Trace IDs attached to metric samples enabling metric-to-trace correlation**

**Explanation:**
Exemplars are trace IDs stored alongside metric samples at specific points in time. When viewing a histogram or counter in Grafana, exemplars let you click directly to the trace that generated a specific metric data point.

</details>

### 6. Which PromQL function calculates the 95th percentile latency from a histogram?

- A) `avg()`
- B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- C) `max()`
- D) `percentile(95, latency)`

<details>
<summary>Show Answer</summary>

**Answer: B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`**

**Explanation:**
`histogram_quantile()` calculates quantiles from histogram bucket counts. The first argument (0.95) is the percentile, and it operates on the rate of the `_bucket` metric. This gives the latency below which 95% of requests complete.

</details>

### 7. What is TraceQL used for?

- A) Writing Prometheus alerts
- B) Querying distributed traces in Grafana Tempo
- C) Creating log aggregation rules
- D) Defining service mesh policies

<details>
<summary>Show Answer</summary>

**Answer: B) Querying distributed traces in Grafana Tempo**

**Explanation:**
TraceQL is Tempo's query language for searching traces. It supports filtering by service name, span name, duration, attributes, and status. For example: `{resource.service.name="api-gateway" && duration>1s}` finds slow API gateway traces.

</details>

### 8. How do you extract a JSON field in LogQL?

- A) `json.fieldname`
- B) `{app="myapp"} | json | line_format "{{.fieldname}}"`
- C) `SELECT fieldname FROM logs`
- D) `logs.fieldname`

<details>
<summary>Show Answer</summary>

**Answer: B) `{app="myapp"} | json | line_format "{{.fieldname}}"`**

**Explanation:**
The `| json` parser extracts JSON fields from log lines into labels. You can then use `| line_format` with Go template syntax to format output, or filter with extracted fields like `| status_code >= 500`.

</details>

### 9. What enables correlation between logs and traces in Grafana?

- A) Manual copy-paste of IDs
- B) Including trace_id in log fields and configuring derived fields in Loki datasource
- C) Using the same dashboard
- D) Installing a separate plugin

<details>
<summary>Show Answer</summary>

**Answer: B) Including trace_id in log fields and configuring derived fields in Loki datasource**

**Explanation:**
Applications must emit trace IDs in their logs. In Grafana, you configure Loki's derived fields to recognize the trace_id field and link to Tempo. This creates clickable links from log lines directly to the associated trace.

</details>

### 10. What is the purpose of span attributes in distributed tracing?

- A) To style the trace visualization
- B) To attach contextual metadata (user ID, request parameters) to spans
- C) To encrypt trace data
- D) To compress trace storage

<details>
<summary>Show Answer</summary>

**Answer: B) To attach contextual metadata (user ID, request parameters) to spans**

**Explanation:**
Span attributes are key-value pairs that add context to spans, such as `http.method`, `http.status_code`, `user.id`, or `db.statement`. They enable filtering traces by business context and help identify which requests are problematic.

</details>
