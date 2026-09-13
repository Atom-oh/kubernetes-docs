# Cilium Service Mesh Observability Quiz

Reviewed against Cilium 1.20.1/Hubble CLI 1.19.4. See the [observability guide](../../../service-mesh/cilium-service-mesh/04-observability.md) for tested commands, metric definitions and limitations.

### 1. Which is NOT a main component of Hubble?

- **A.** Hubble Observer
- **B.** Hubble Relay
- **C.** Hubble Router
- **D.** Hubble UI

<details>
<summary>Show Answer</summary>

**Answer: C. Hubble Router**

Observer, Relay, UI and CLI are the relevant Hubble components. Observer and metric processing are embedded in Cilium; Relay aggregates connected servers. Hubble Router is not a named component of this architecture.

</details>

### 2. What command filters and observes only HTTP traffic in Hubble CLI?

- **A.** hubble observe --type http
- **B.** hubble observe --protocol http
- **C.** hubble observe --filter http
- **D.** hubble observe --layer http

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --protocol http**

This filters existing HTTP observations. It does not enable L7 inspection or decrypt arbitrary TLS. A supported L7 policy/proxy path and traffic must already provide the observations.

</details>

### 3. What setting needs to be enabled in values.yaml to collect Hubble metrics in Prometheus?

- **A.** hubble.prometheus.enabled: true
- **B.** hubble.metrics.enabled
- **C.** hubble.export.prometheus: true
- **D.** prometheus.hubble: true

<details>
<summary>Show Answer</summary>

**Answer: B. hubble.metrics.enabled**

hubble.metrics.enabled selects handlers such as dns and httpV2. Prometheus collection additionally needs working discovery/scraping, Operator CRDs/controller where ServiceMonitor is used, and matching selectors. ServiceMonitor creation alone is not proof that a target is scraped.

</details>

### 4. Which is NOT one of the four Golden Signals for monitoring?

- **A.** Latency
- **B.** Traffic
- **C.** Availability
- **D.** Saturation

<details>
<summary>Show Answer</summary>

**Answer: C. Availability**

The four names are latency, traffic, errors and saturation. Availability still requires an explicit SLI and cannot be fully inferred from a partial HTTP5xx observation stream.

</details>

### 5. Which command first selects dropped flows for further cause analysis?

- **A.** hubble observe --denied
- **B.** hubble observe --verdict DROPPED
- **C.** hubble observe --blocked
- **D.** hubble observe --policy-denied

<details>
<summary>Show Answer</summary>

**Answer: B. hubble observe --verdict DROPPED**

DROPPED includes several causes. Add --drop-reason-desc POLICY_DENIED for reported policy-denied drops, and inspect L7/application failures separately. FORWARDED is a datapath observation, not proof of business success.

</details>

### 6. Which function is used in PromQL queries to measure HTTP P99 latency?

- **A.** avg()
- **B.** histogram_quantile()
- **C.** rate()
- **D.** sum()

<details>
<summary>Show Answer</summary>

**Answer: B. histogram_quantile()**

histogram_quantile calculates an estimate from the histogram. For a workload aggregate, sum compatible bucket rates while retaining le and the chosen cluster/namespace/workload labels, then calculate the quantile. Averaging per-instance percentiles is not equivalent.

</details>

### 7. Which is NOT a main feature provided by Hubble UI?

- **A.** Service Map
- **B.** Flow Timeline
- **C.** Auto Scaling
- **D.** Namespace Filter

<details>
<summary>Show Answer</summary>

**Answer: C. Auto Scaling**

The UI displays observed relationships and flow details with filters; it does not automatically scale workloads. Quiet or unsupported paths and missing metadata can leave gaps in the map.

</details>

### 8. How should an observed HTTP5xx percentage be calculated with httpV2?

- **A.** Divide lifetime error and request counters without rates
- **B.** Divide matching 5xx response rates by observed total rates, with scoped missing/zero handling
- **C.** Count the number of metric series
- **D.** Read an automatically provided hubble_http_error_rate gauge

<details>
<summary>Show Answer</summary>

**Answer: B. Divide matching 5xx response rates by observed total rates, with scoped missing/zero handling**

With httpV2, hubble_http_requests_total includes status and is updated from response events. Use the same grouping/observation boundary in numerator and denominator. Fill an absent 5xx numerator only for an existing total, retain no-data for missing observations and exclude zero totals from percentages.

</details>

### 9. What option is used to observe only traffic destined for a specific service in Hubble?

- **A.** --destination-service
- **B.** --to-service
- **C.** --target-service
- **D.** --svc

<details>
<summary>Show Answer</summary>

**Answer: B. --to-service**

Service filters use namespace-qualified name prefixes and Service/ClusterIP-derived metadata. --from-service does not generally select calls made by Pods behind that Service; use workload/Pod/label filters for callers. Omitted namespaces default to default.

</details>

### 10. Which documented metric reports pressure for instrumented BPF maps?

- **A.** cilium_ct_usage
- **B.** cilium_bpf_map_pressure
- **C.** cilium_connections_total
- **D.** cilium_datapath_conntrack_active / cilium_datapath_conntrack_max

<details>
<summary>Show Answer</summary>

**Answer: B. cilium_bpf_map_pressure**

cilium_bpf_map_pressure reports pressure for instrumented BPF maps, with reporting thresholds for some maps. It is not proof that every CT map is represented. The documented CT GC-entry metric is a snapshot from garbage collection, not the former invented active/max metric pair.

</details>

### 11. What option is used to receive Hubble output in JSON format?

- **A.** --format json
- **B.** -o json
- **C.** --json
- **D.** --output-type json

<details>
<summary>Show Answer</summary>

**Answer: B. -o json**

json is an alias for jsonpb. Protobuf JSON encodes 64-bit values such as latency_ns as strings; convert to a number before numeric comparison in jq. dict, compact and table are also supported display formats.

</details>

### 12. Which supported path collects Hubble flow logs with OpenTelemetry Collector?

- **A.** Enable hubble.export.opentelemetry in the chart
- **B.** Use Hubble file export and a filelog receiver, then a supported log exporter
- **C.** Turn every flow automatically into a distributed trace
- **D.** Use the removed jaeger exporter for flow-log ingestion

<details>
<summary>Show Answer</summary>

**Answer: B. Use Hubble file export and a filelog receiver, then a supported log exporter**

Cilium 1.20.1 documents file export for flow logs. A filelog receiver can collect those files and send logs through a supported exporter such as OTLP/HTTP to Loki. Metrics and application traces use their own collection paths; the old Hubble opentelemetry values and removed Collector jaeger/loki exporters are not the replacement.

</details>
