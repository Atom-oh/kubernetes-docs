# Observability Optimization Quiz

> **Validated example versions**: Prometheus 3.14.0 · OTel Collector Contrib 0.160.0

> **Last Updated**: September 13, 2026

This quiz tests your understanding of the EKS Observability Optimization Guide. It covers the three pillars of observability—logging, metrics, and tracing—as well as eBPF-based monitoring and cost optimization strategies.

---

## Multiple Choice Questions

1. Among the three pillars of observability, which data type is most suitable for answering the question "Why is it slow?"
   - A) Logging
   - B) Metrics
   - C) Tracing
   - D) Events

<details>
<summary>View Answer</summary>

**Answer: C) Tracing**

**Explanation:**
The three pillars of observability answer different types of questions. Logging answers "What happened?", Metrics answer "Is the system healthy?", and Tracing answers "Why is it slow?". Tracing is optimized for tracking request flows to understand causality and analyze bottlenecks. In distributed systems, tracing is essential when analyzing latency for requests that traverse multiple services.

</details>

2. Which log storage solution excels at label-based fast filtering and achieves high cost efficiency by utilizing object storage (S3)?
   - A) CloudWatch Logs
   - B) OpenSearch
   - C) Loki
   - D) ClickHouse

<details>
<summary>View Answer</summary>

**Answer: C) Loki**

**Explanation:**
Loki uses label indexing and object storage, but total cost includes compute, caches, object requests, queries and operations. Compare the same Region, volume, retention and availability instead of treating S3 storage price as total cost.

</details>

3. Which C-based agent can collect logs on EKS?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>View Answer</summary>

**Answer: B) Fluent Bit**

**Explanation:**
Fluent Bit is a C-based collector usable in AWS deployments. Memory and throughput depend on version, parsers, record size, buffering and hardware; fixed 15 MB or 200K msg/s claims are not guarantees.

</details>

4. What is the main cause of cardinality explosion in Prometheus?
   - A) When the scrape interval is too long
   - B) When using Pod UID or timestamp as labels
   - C) When using too many Recording Rules
   - D) When enabling Remote Write

<details>
<summary>View Answer</summary>

**Answer: B) When using Pod UID or timestamp as labels**

**Explanation:**
Changing request-ID/timestamp labels increases series counts. Bound labels at the source and verify uniqueness. labeldrop does not aggregate samples and can create collisions; target relabeling and metric relabeling run at different stages.

</details>

5. In OpenTelemetry Collector's Tail Sampling strategy, which policy type selects received traces containing an ERROR span?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>View Answer</summary>

**Answer: C) status_code**

**Explanation:**
The ERROR status_code policy selects traces using error spans received by that sampler. Trace affinity, decision timing, buffer limits, late spans and upstream head sampling prevent a guarantee that every failing request is retained.

</details>

6. What is the biggest advantage of eBPF-based monitoring?
   - A) It can collect more types of metrics
   - B) It can instrument applications without code modification
   - C) It reduces metric storage costs
   - D) It improves query performance

<details>
<summary>View Answer</summary>

**Answer: B) It can instrument applications without code modification**

**Explanation:**
It can reduce source changes for supported kernels, runtimes and protocols, but does not cover every language, TLS library or business span equally. Validate permissions, overhead and sensitive payloads; SDK auto-instrumentation may also avoid source changes.

</details>

7. What is the primary use of Cilium Hubble?
   - A) Container resource usage monitoring
   - B) Network flow observation and analysis
   - C) Log collection and storage
   - D) Distributed tracing backend

<details>
<summary>View Answer</summary>

**Answer: B) Network flow observation and analysis**

**Explanation:**
Hubble observes network flows in a compatible Cilium deployment. L7 visibility depends on protocols and proxy/policy configuration. Verify actual coverage instead of promising every flow or complete application tracing.

</details>

8. What is the primary metric that Kepler (Kubernetes Efficient Power Level Exporter) measures?
   - A) CPU temperature
   - B) Network bandwidth
   - C) Energy (joules) and power (watts)
   - D) Disk I/O latency

<details>
<summary>View Answer</summary>

**Answer: C) Energy (joules) and power (watts)**

**Explanation:**
Kepler 0.10+ differs from legacy 0.7. In 0.11.4, kepler_pod_cpu_watts is a power gauge and rate(kepler_pod_cpu_joules_total[5m]) is J/s=W. Multiplying by 1000 gives milliwatts. Verify hardware access and attribution support.

</details>

9. What is the recommended method for tracking costs per team in OpenCost/KubeCost?
   - A) Create separate Kubernetes clusters per team
   - B) Standardize labels like cost-center and team on namespaces and Pods
   - C) Assign separate AWS accounts to each team
   - D) Only set up ResourceQuotas

<details>
<summary>View Answer</summary>

**Answer: B) Standardize labels like cost-center and team on namespaces and Pods**

**Explanation:**
OpenCost allocates costs based on Kubernetes labels. By consistently applying labels like `cost-center`, `team`, and `environment` to namespaces and Pods, you can query costs per team through the OpenCost API using `aggregate=label:team`. This approach enables detailed cost analysis and chargeback while maintaining the existing cluster structure.

</details>

10. In SLO (Service Level Objective) based monitoring, what does "Error Budget" mean?
    - A) Budget allocated for monitoring system operations
    - B) The amount of errors allowed while deviating from SLO targets
    - C) Cost of sending alerts
    - D) Storage capacity available for log storage

<details>
<summary>View Answer</summary>

**Answer: B) The amount of errors allowed while deviating from SLO targets**

**Explanation:**
For a request-based 99.9% SLO, allowed bad requests equal total requests×0.001 over the defined window. Do not confuse this with time-based downtime. Remaining 30-day budget requires a 30-day request-weighted error ratio, not the latest five-minute ratio.

</details>

---

## Short Answer Questions

1. What is the name of the Prometheus feature that improves dashboard query performance by pre-computing and storing complex queries?

<details>
<summary>View Answer</summary>

**Answer:** Recording Rules

**Explanation:**
Recording Rules periodically evaluate PromQL expressions and store the results as new time series. For example, pre-computing node CPU utilization with `record: node:cpu_utilization:ratio` allows dashboards to query this metric directly instead of running complex queries, resulting in faster responses. They are defined using the `record` field in the PrometheusRule CRD.

</details>

2. In OpenTelemetry, what is the sampling method called that collects spans for a decision window and samples using observed outcomes?

<details>
<summary>View Answer</summary>

**Answer:** Tail Sampling

**Explanation:**
Default trace-complete sampling decides using spans received during its decision window. It cannot prove completion or arrival of all spans; consider affinity, buffers, late spans, restarts and upstream sampling.

</details>

3. What is the Prometheus feature that links trace IDs to metric data points, enabling direct navigation from metrics to traces?

<details>
<summary>View Answer</summary>

**Answer:** Exemplars

**Explanation:**
Exemplars is a feature that attaches additional context (typically traceID) to metric samples. When exemplars are added to histogram or counter metrics, you can click on a specific point in the metric graph in Grafana to navigate directly to the trace from that time. This facilitates correlation analysis between observability data, allowing you to analyze "why latency spiked at this point" in the trace.

</details>

4. In VictoriaMetrics cluster mode, what is the name of the component responsible for metric data storage?

<details>
<summary>View Answer</summary>

**Answer:** vmstorage

**Explanation:**
vmstorage stores the data. Multiple instances alone do not establish replication: configure replication factors, vminsert/vmselect behavior, query deduplication and failure handling.

</details>

5. What is the strategy called for reducing log/metric storage costs by moving older data to low-cost storage like S3 Glacier?

<details>
<summary>View Answer</summary>

**Answer:** Tiered Storage

**Explanation:**
Tiering depends on access frequency, restore delay and retention. Moving active Loki/Tempo blocks into Glacier can break queries; validate compatibility/recovery or use a separate archive. Savings are not a fixed percentage.

</details>

---

## Hands-on Questions

1. Write a Fluent Bit configuration to filter out and exclude DEBUG and TRACE level logs.

<details>
<summary>View Answer</summary>

**Answer:**
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  level ^(DEBUG|TRACE)$
```

**Explanation:**
Match ^(DEBUG|TRACE)$ on a parsed level field rather than arbitrary message text. Measure drops and incident-investigation impact; 40–60% savings are not guaranteed.

</details>

2. Write a PrometheusRule that triggers a warning when the HTTP error rate per service exceeds 5% and persists for 5 minutes.

<details>
<summary>View Answer</summary>

**Answer:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
spec:
  groups:
    - name: slo.alerts
      rules:
        - alert: HighHTTPErrorRate
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "HTTP error rate for service {{ $labels.service }} exceeded 5%"
            description: "Current error rate: {{ $value | humanizePercentage }}"
```

**Explanation:**
This alert rule calculates the 5XX status code ratio per service. `status=~"5.."` is a regex that matches status codes 500-599. `for: 5m` triggers the alert only when the condition persists for 5 minutes, preventing false alerts from temporary spikes. Using `sum by (service)` generates independent alerts for each service.

</details>

3. Write a tail_sampling processor configuration for OpenTelemetry Collector that samples error traces at 100%, traces with latency over 1 second at 100%, and the rest at only 10%.

<details>
<summary>View Answer</summary>

**Answer:**
```yaml
processors:
  tail_sampling:
    decision_wait: 2s
    num_traces: 1000
    maximum_trace_size_bytes: 1048576
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 1000
    - name: baseline
      type: probabilistic
      probabilistic:
        sampling_percentage: 10
```

**Explanation:**
These positive policies retain matching received error/slow traces and probabilistically sample the rest. Buffer, affinity and late-span limits remain. Overall retention depends on the error/slow share; 90% reduction is not guaranteed. Do not generalize first-match semantics to drop/composite policies.

</details>

---

## Advanced Questions

1. Design an architecture for achieving high availability of the observability stack in a large-scale EKS cluster (500+ nodes). Explain which components should be deployed and how for each layer: collection, storage, and query.

<details>
<summary>View Answer</summary>

**Answer:**

Do not derive replica counts from node count alone. Separate node log agents and gateways, route tail sampling by trace ID, and measure buffering/backpressure and drops. Follow current Loki/Tempo mode replication/quorum/AZ requirements; configure VictoriaMetrics replication/query deduplication and AMP quotas/retention. Budget PVC/memory for Prometheus replicas×shards and merge shard queries. Grafana needs a shared DB and separate Alerting HA; verify edition support for query caching. PDBs and S3 durability do not guarantee end-to-end availability; test failures and recovery.

</details>

2. In an environment with $5,000/month in observability costs, propose optimization strategies to achieve 50% cost reduction while maintaining quality. Explain specific methods for each area: logging, metrics, and tracing.

<details>
<summary>View Answer</summary>

**Answer:**

The $5,000 baseline and 50% target are hypothetical. Attribute ingestion, storage, scan, compute and operating costs before optimizing the largest category. Trial parsed-level filtering, request-level probability sampling, safe metric/bucket reduction, tail sampling and retention separately. Throttling is not a 10% sampler, and recording rules do not change raw-data retention. Compare complete costs with equal Region, availability, query and retention requirements. Savings overlap; evaluate the bill, data loss, SLO coverage and investigation success instead of adding percentages. If the target is not established, report evidence and the next experiment.

</details>

---

**Score Calculation:**
- 18-20 correct answers: Excellent (Observability expert level)
- 14-17 correct answers: Good (Applicable in practice)
- 10-13 correct answers: Average (Additional study recommended)
- 6-9 correct answers: Basic (Review fundamental concepts)
- 0-5 correct answers: Insufficient (Full content review needed)

---

**Related Learning Materials:**
- [EKS Observability Optimization Guide](../../observability/09-observability-optimization.md)
