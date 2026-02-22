# Cilium Service Mesh Observability Quiz

This quiz tests your understanding of Hubble, metrics collection, service maps, Golden Signals monitoring, and OpenTelemetry integration.

## Quiz Questions

### 1. Which is NOT a main component of Hubble?

A. Hubble Observer
B. Hubble Relay
C. Hubble Router
D. Hubble UI

<details>
<summary>Show Answer</summary>

**Answer: C. Hubble Router**

**Explanation:**
The main components of Hubble are Hubble Observer (embedded in Cilium Agent), Hubble Relay (cluster-wide flow aggregation), Hubble UI (visualization dashboard), and Hubble CLI (command-line interface). Hubble Router is not an existing component.

</details>

### 2. What command filters and observes only HTTP traffic in Hubble CLI?

A. hubble observe --type http
B. hubble observe --protocol http
C. hubble observe --filter http
D. hubble observe --layer http

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --protocol http**

**Explanation:**
The `hubble observe --protocol http` command filters only HTTP protocol traffic. Other protocols (tcp, dns, etc.) can be filtered in the same way.

</details>

### 3. What setting needs to be enabled in values.yaml to collect Hubble metrics in Prometheus?

A. hubble.prometheus.enabled: true
B. hubble.metrics.enabled
C. hubble.export.prometheus: true
D. prometheus.hubble: true

<details>
<summary>Show Answer</summary>

**Answer: B. hubble.metrics.enabled**

**Explanation:**
To enable Hubble metrics, specify the metric types to collect (dns, drop, tcp, flow, http, etc.) as a list under hubble.metrics.enabled. Also, setting serviceMonitor.enabled: true allows Prometheus Operator to automatically scrape.

</details>

### 4. Which is NOT one of the four Golden Signals for monitoring?

A. Latency
B. Traffic
C. Availability
D. Saturation

<details>
<summary>Show Answer</summary>

**Answer: C. Availability**

**Explanation:**
The four Golden Signals defined by Google SRE are Latency, Traffic, Errors, and Saturation. Availability is not included in Golden Signals and is measured indirectly through the Errors metric.

</details>

### 5. What is the correct command to observe traffic denied by policies in Hubble?

A. hubble observe --denied
B. hubble observe --verdict DROPPED
C. hubble observe --blocked
D. hubble observe --policy-denied

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

**Explanation:**
The `--verdict DROPPED` option filters traffic denied by network policies. Conversely, `--verdict FORWARDED` shows allowed traffic.

</details>

### 6. Which function is used in PromQL queries to measure HTTP P99 latency?

A. avg()
B. histogram_quantile()
C. rate()
D. sum()

<details>
<summary>Show Answer</summary>

**Answer: B. histogram_quantile()**

**Explanation:**
Percentile metrics like P99 latency use the histogram_quantile() function. Example: `histogram_quantile(0.99, rate(hubble_http_request_duration_seconds_bucket[5m]))`. Here, 0.99 means the 99th percentile.

</details>

### 7. Which is NOT a main feature provided by Hubble UI?

A. Service Map
B. Flow Timeline
C. Auto Scaling
D. Namespace Filter

<details>
<summary>Show Answer</summary>

**Answer: C. Auto Scaling**

**Explanation:**
Hubble UI provides service maps, flow timeline, namespace filter, verdict filter, and L7 details for individual flows. Auto scaling is a workload management feature, not an observability feature.

</details>

### 8. What is the correct form of a PromQL query to calculate HTTP error rate in Cilium?

A. hubble_http_errors_total / hubble_http_requests_total
B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))
C. count(hubble_http_errors) / count(hubble_http_requests)
D. hubble_http_error_rate

<details>
<summary>Show Answer</summary>

**Answer: B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))**

**Explanation:**
HTTP error rate is calculated by dividing the count of 5xx responses by the total response count. The rate() function calculates per-second rates, and the status label filter (status=~"5..") selects only server errors.

</details>

### 9. What option is used to observe only traffic destined for a specific service in Hubble?

A. --destination-service
B. --to-service
C. --target-service
D. --svc

<details>
<summary>Show Answer</summary>

**Answer: B. --to-service**

**Explanation:**
The `hubble observe --to-service <service-name>` command filters traffic destined for a specific service. Conversely, `--from-service` filters traffic originating from a specific service.

</details>

### 10. What metric monitors connection tracking table utilization in Cilium?

A. cilium_ct_usage
B. cilium_datapath_conntrack_active
C. cilium_connections_total
D. cilium_ct_table_size

<details>
<summary>Show Answer</summary>

**Answer: B. cilium_datapath_conntrack_active**

**Explanation:**
The cilium_datapath_conntrack_active metric represents the current number of active connections. It can be used with cilium_datapath_conntrack_max to calculate connection tracking table utilization.

</details>

### 11. What option is used to receive Hubble output in JSON format?

A. --format json
B. -o json
C. --json
D. --output-type json

<details>
<summary>Show Answer</summary>

**Answer: B. -o json**

**Explanation:**
The `hubble observe -o json` command outputs in JSON format. This is useful for piping to tools like jq for additional processing.

</details>

### 12. What protocol is used when integrating OpenTelemetry Collector with Hubble?

A. HTTP REST API
B. OTLP (OpenTelemetry Protocol)
C. Prometheus Remote Write
D. StatsD

<details>
<summary>Show Answer</summary>

**Answer: B. OTLP (OpenTelemetry Protocol)**

**Explanation:**
Hubble can export flow data to OpenTelemetry Collector using OpenTelemetry Protocol (OTLP). This allows routing data to various backends like Jaeger, Prometheus, Loki, etc.

</details>
