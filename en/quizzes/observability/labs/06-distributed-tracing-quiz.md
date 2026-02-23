# Observability Lab Part 6: Distributed Tracing Analysis Quiz

> **Last Updated**: February 22, 2026

Test your understanding of distributed tracing analysis concepts covered in the Observability End-to-End Lab Part 6.

---

1. What is the basic syntax structure of TraceQL for span filtering?
   - A) SQL-like SELECT statements with JOIN clauses
   - B) Curly braces containing span attribute filters using dot notation, e.g., `{ span.attribute = "value" }`
   - C) XML-based query format
   - D) Regular expressions only

<details>
<summary>Show Answer</summary>

**Answer: B) Curly braces containing span attribute filters using dot notation, e.g., `{ span.attribute = "value" }`**

**Explanation:**
TraceQL uses a pipeline-based syntax with curly braces for span selectors. Basic structure: `{ spanset_filter }` where filters use dot notation for attributes. Intrinsic attributes use `span.` prefix (e.g., `span.duration`, `span.status`), resource attributes use `resource.` prefix (e.g., `resource.service.name`), and span attributes are direct (e.g., `http.status_code`). Filters support operators like `=`, `!=`, `>`, `<`, `=~` (regex), and can be combined with `&&` and `||`.

</details>

---

2. What does the TraceQL query `{ span.http.status_code >= 500 }` return?
   - A) All traces in the system
   - B) Spans where the HTTP response status code was 500 or higher, indicating server errors
   - C) Spans that took longer than 500 milliseconds
   - D) The 500 most recent spans

<details>
<summary>Show Answer</summary>

**Answer: B) Spans where the HTTP response status code was 500 or higher, indicating server errors**

**Explanation:**
This query filters spans based on the `http.status_code` attribute, returning only those with server error status codes (500, 502, 503, etc.). This is useful for investigating error conditions in distributed systems. The query returns the entire trace containing matching spans, highlighting the error spans. You could further narrow results with additional filters like `{ span.http.status_code >= 500 && resource.service.name = "payment-service" }` to focus on specific services.

</details>

---

3. How can you identify high error rate or latency edges in Tempo's Service Graph?
   - A) Edges are always displayed identically regardless of metrics
   - B) Service Graph visualizes edges with color coding or thickness based on error rates and latency, highlighting problematic service-to-service communications
   - C) You must manually calculate edge metrics from raw spans
   - D) Service Graph only shows service names without metrics

<details>
<summary>Show Answer</summary>

**Answer: B) Service Graph visualizes edges with color coding or thickness based on error rates and latency, highlighting problematic service-to-service communications**

**Explanation:**
Tempo's Service Graph (generated from span data using metrics-generator) displays services as nodes and their communications as edges. Edges are enriched with metrics: error rates shown through color (red for high errors), latency through color gradients or tooltips, and request rates through edge thickness. This visualization quickly identifies problematic dependencies—if the edge from Service A to Service B is red, investigate that specific communication path. Clicking edges often reveals detailed metrics and links to relevant traces.

</details>

---

4. How do you identify bottlenecks using the Span timeline (Waterfall View)?
   - A) Bottlenecks are identified by span name only
   - B) Look for spans with disproportionately long duration compared to parent span, large gaps between child spans, or sequential operations that could be parallelized
   - C) The waterfall view doesn't show timing information
   - D) Bottlenecks are only visible in the service graph

<details>
<summary>Show Answer</summary>

**Answer: B) Look for spans with disproportionately long duration compared to parent span, large gaps between child spans, or sequential operations that could be parallelized**

**Explanation:**
The waterfall view shows hierarchical span relationships with timing. Bottleneck indicators include: long spans dominating the trace duration (e.g., a database query taking 80% of total time), gaps between spans indicating waiting time (network latency, queue delays), sequential child spans that could run in parallel, and spans with high self-time (time not attributed to children). By visually scanning the waterfall, you identify where time is spent and whether the execution pattern is optimal.

</details>

---

5. How do you configure the Loki to Tempo TraceID derived field for correlation?
   - A) No configuration needed; it's automatic
   - B) In Grafana's Loki data source settings, add a derived field with a regex to extract trace IDs from logs and configure an internal link to the Tempo data source
   - C) Install a separate plugin for correlation
   - D) Derived fields only work with external URLs

<details>
<summary>Show Answer</summary>

**Answer: B) In Grafana's Loki data source settings, add a derived field with a regex to extract trace IDs from logs and configure an internal link to the Tempo data source**

**Explanation:**
Configuration steps: In Grafana, edit the Loki data source and find "Derived fields". Add a field with: Name (e.g., "TraceID"), Regex to match trace IDs in your log format (e.g., `traceID=(\w+)` or `"trace_id":"([^"]+)"`), Internal link enabled, pointing to your Tempo data source, with Query using the regex capture group (`${__value.raw}`). When viewing logs, extracted trace IDs become clickable links that open the corresponding trace in Tempo's explore view.

</details>

---

6. What does Tempo's Span to Logs feature enable?
   - A) It automatically generates logs from spans
   - B) It allows navigating from a span in a trace directly to correlated logs in Loki based on time range and labels like service name or trace ID
   - C) It replaces logs with spans entirely
   - D) It only works with CloudWatch Logs

<details>
<summary>Show Answer</summary>

**Answer: B) It allows navigating from a span in a trace directly to correlated logs in Loki based on time range and labels like service name or trace ID**

**Explanation:**
Tempo's "Span to Logs" feature (configured in Tempo data source settings) creates links from spans to Loki queries. When viewing a trace, each span has a "Logs" link that constructs a Loki query using the span's time window, service name, and optionally trace ID. This enables investigating what a service logged during the span's execution—invaluable for understanding errors or debugging unexpected behavior. Configuration specifies which Loki labels to map from span attributes.

</details>

---

7. How does the exemplar mechanism enable drill-down from metrics to traces?
   - A) Exemplars replace metrics entirely
   - B) Exemplars attach trace IDs to metric samples at recording time, allowing direct navigation from a metric data point to a representative trace
   - C) Exemplars only work with counter metrics
   - D) You must manually correlate metrics and traces by timestamp

<details>
<summary>Show Answer</summary>

**Answer: B) Exemplars attach trace IDs to metric samples at recording time, allowing direct navigation from a metric data point to a representative trace**

**Explanation:**
Exemplars are metadata (including trace ID) attached to metric observations. When recording a histogram or counter, the application includes a trace ID from the current request context. In Grafana, metric visualizations show exemplars as dots on the graph. Clicking an exemplar reveals its trace ID with a link to the tracing backend. This enables powerful workflows: spot a latency spike in a dashboard, click an exemplar on that spike, and immediately see a representative trace showing why that request was slow.

</details>

---

8. What do Rate, Errors, and Duration represent in RED metrics dashboards?
   - A) Resource utilization metrics for nodes
   - B) Rate is requests per second throughput, Errors is the count or percentage of failed requests, Duration is response time latency (typically as percentiles)
   - C) Database-specific metrics only
   - D) Network bandwidth measurements

<details>
<summary>Show Answer</summary>

**Answer: B) Rate is requests per second throughput, Errors is the count or percentage of failed requests, Duration is response time latency (typically as percentiles)**

**Explanation:**
RED is a service-centric monitoring methodology: Rate measures throughput (requests/second), answering "how much traffic is the service handling?". Errors measures failure rate (error count or percentage), answering "how often does the service fail?". Duration measures latency distribution (p50, p95, p99), answering "how long do requests take?". Together, these metrics provide comprehensive service health visibility. If Rate drops, something's blocking requests; if Errors spike, something's failing; if Duration increases, something's slow.

</details>

---

9. How would you configure an SLI/SLO dashboard gauge for 99.9% availability and p99 latency under 500ms?
   - A) These metrics cannot be displayed in a single dashboard
   - B) Create gauge panels with PromQL queries calculating current SLI values, configure thresholds to show green/yellow/red zones relative to SLO targets
   - C) SLI/SLO dashboards require commercial Grafana licensing
   - D) Use static text panels with manually entered values

<details>
<summary>Show Answer</summary>

**Answer: B) Create gauge panels with PromQL queries calculating current SLI values, configure thresholds to show green/yellow/red zones relative to SLO targets**

**Explanation:**
For availability SLI: query `sum(rate(requests_total{status!~"5.."}[30d])) / sum(rate(requests_total[30d])) * 100`, displaying current availability percentage with thresholds (green >= 99.9%, yellow >= 99.5%, red < 99.5%). For p99 latency: query `histogram_quantile(0.99, sum(rate(request_duration_seconds_bucket[5m])) by (le)) * 1000` (in ms), with thresholds (green <= 500ms, yellow <= 750ms, red > 750ms). Add error budget panels showing remaining budget based on SLO targets and current burn rate.

</details>

---

10. How are database query span attributes like `db.system` and `db.statement` useful in distributed tracing?
    - A) They are only used for database connection pooling
    - B) They identify the database type and capture the actual query, enabling identification of slow queries, N+1 problems, and database-related bottlenecks in traces
    - C) These attributes are deprecated in OpenTelemetry
    - D) They only apply to SQL databases, not NoSQL

<details>
<summary>Show Answer</summary>

**Answer: B) They identify the database type and capture the actual query, enabling identification of slow queries, N+1 problems, and database-related bottlenecks in traces**

**Explanation:**
OpenTelemetry semantic conventions define standard database span attributes: `db.system` identifies the database type (postgresql, mysql, redis, mongodb), `db.statement` contains the query text (with sanitization for security), `db.operation` shows the operation type (SELECT, INSERT), and `db.name` indicates the database name. These attributes enable: filtering traces by database type, identifying slow queries in the waterfall view, detecting N+1 query patterns (many similar sequential queries), and correlating database spans with overall request latency. This visibility is crucial for performance optimization.

</details>
