# Observability Optimization Quiz

> **Supported Versions**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **Last Updated**: February 2025

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
Grafana Loki uses label-based indexing to provide fast filtering without full-text search indexes. It stores log data in object storage like S3, making storage costs very low (S3: $0.023/GB/month). OpenSearch is strong in full-text search but has high index storage costs, while CloudWatch Logs has relatively high ingestion costs ($0.50/GB).

</details>

3. Which log agent has the lowest memory usage, is written in C, and is natively supported on EKS?
   - A) Fluentd
   - B) Fluent Bit
   - C) Vector
   - D) Logstash

<details>
<summary>View Answer</summary>

**Answer: B) Fluent Bit**

**Explanation:**
Fluent Bit is written in C and uses only about 15MB of memory. It is lighter than Fluentd (~60MB, Ruby/C) or Vector (~30MB, Rust), and provides high throughput of up to ~200K msg/s. AWS officially recommends Fluent Bit as the log collector for EKS and provides the aws-for-fluent-bit image.

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
Cardinality refers to the number of unique time series. Using unique values like Pod UID, timestamps, or request IDs as labels causes label combinations to grow infinitely, resulting in an explosion of time series. This causes Prometheus memory usage to spike and query performance to degrade. It is recommended to remove labels like pod_template_hash and controller_revision_hash in relabel_configs.

</details>

5. In OpenTelemetry Collector's Tail Sampling strategy, which policy type keeps 100% of traces that contain errors?
   - A) probabilistic
   - B) latency
   - C) status_code
   - D) string_attribute

<details>
<summary>View Answer</summary>

**Answer: C) status_code**

**Explanation:**
Tail Sampling makes sampling decisions based on complete trace information after the trace is finished. The `status_code` policy samples based on the trace's status code (OK, ERROR). Setting `status_codes: [ERROR]` keeps 100% of traces containing errors. This is an effective strategy that preserves traces important for problem analysis while reducing overall data volume.

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
eBPF (extended Berkeley Packet Filter) safely runs programs in the Linux kernel to observe system calls, network packets, and more. Traditional instrumentation requires adding SDKs, modifying code, and redeploying, but eBPF operates transparently at the kernel level, enabling monitoring without application changes. It is also language-agnostic, instrumenting applications written in any language equally.

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
Cilium Hubble is the observability component of Cilium, an eBPF-based CNI. Hubble observes all network flows in the cluster in real-time, analyzing DNS requests, TCP connections, HTTP traffic, and more. With the `hubble observe` command, you can filter traffic to specific services or analyze dropped packets. It is useful for service map visualization and network policy validation.

</details>

8. What is the primary metric that Kepler (Kubernetes Efficient Power Level Exporter) measures?
   - A) CPU temperature
   - B) Network bandwidth
   - C) Energy consumption (joules/watts)
   - D) Disk I/O latency

<details>
<summary>View Answer</summary>

**Answer: C) Energy consumption (joules/watts)**

**Explanation:**
Kepler is a CNCF project that uses eBPF to measure energy consumption of containers and Pods. It provides energy consumption (joules) through the `kepler_container_joules_total` metric, and power consumption (watts) can be calculated with `rate(kepler_container_joules_total[5m]) * 1000`. This enables analysis of energy usage by namespace or Pod, helping achieve green computing goals.

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
Error budget is a concept derived from SLO, representing the total amount of errors allowed. For example, a 99.9% availability SLO means a 0.1% error budget. Based on 30 days, approximately 43 minutes of downtime is allowed. When the error budget is exhausted, new feature deployments should be halted to focus on stability improvements. The remaining error budget ratio can be calculated with the expression `1 - (1 - sli:availability:ratio) / (1 - 0.999)`.

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

2. In OpenTelemetry, what is the sampling method called that makes sampling decisions based on complete trace information after the trace is finished?

<details>
<summary>View Answer</summary>

**Answer:** Tail Sampling

**Explanation:**
Tail Sampling makes sampling decisions after all spans of a trace have arrived. This contrasts with Head Sampling (probabilistic sampling), which makes decisions at the start of the trace. The advantage of Tail Sampling is that it can selectively keep only traces with errors or high latency. However, since all spans must be kept in memory before making a decision, the `decision_wait` and `num_traces` settings are important.

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
VictoriaMetrics cluster mode consists of three components. vminsert handles metric collection and distribution, vmselect handles query processing, and vmstorage handles actual metric data storage. vmstorage can scale horizontally with multiple instances and provides high availability through replication. This separated architecture enables independent scaling of ingestion, storage, and query workloads.

</details>

5. What is the strategy called for reducing log/metric storage costs by moving older data to low-cost storage like S3 Glacier?

<details>
<summary>View Answer</summary>

**Answer:** Tiered Storage

**Explanation:**
Tiered storage strategy stores data in different storage tiers based on importance and access frequency. Recent data is stored in high-performance storage (SSD, EBS), medium-term data in S3 Standard-IA, and long-term archive data in S3 Glacier Deep Archive. This can reduce storage costs by 70-90%. Object storage-based solutions like Loki and Tempo support this strategy by default.

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
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$
```

Or using regular expressions:
```ini
[FILTER]
    Name     grep
    Match    *
    Exclude  log (DEBUG|TRACE)
```

**Explanation:**
Fluent Bit's grep filter uses regular expressions to filter logs. The `Exclude` directive excludes logs matching the pattern. Filtering DEBUG/TRACE logs in production environments can reduce log volume by 40-60%, significantly cutting storage costs. However, DEBUG logs can be selectively enabled for specific services when troubleshooting is needed.

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
    decision_wait: 10s
    num_traces: 100000
    policies:
      # Keep 100% of traces with errors
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep 100% of traces with latency over 1 second
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 1000

      # Sample only 10% of the rest
      - name: default-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

**Explanation:**
Tail Sampling policies are evaluated in order, and if any policy matches, the trace is kept. `decision_wait` is the time to wait for trace completion, requiring enough time for all spans to arrive. `num_traces` is the maximum number of traces to keep in memory. This configuration can reduce overall data volume by about 90% while retaining traces important for error and performance analysis.

</details>

---

## Advanced Questions

1. Design an architecture for achieving high availability of the observability stack in a large-scale EKS cluster (500+ nodes). Explain which components should be deployed and how for each layer: collection, storage, and query.

<details>
<summary>View Answer</summary>

**Answer:**

**Data Collection Layer:**
- Fluent Bit: Deploy as DaemonSet on each node (memory limit 100-200Mi)
- OTel Collector: Deploy as DaemonSet with load balancer in front
- Collector redundancy: At least 2+ Collector instances per AZ

**Storage Layer:**
- Logs: Loki Simple Scalable mode
  - Write path: 2+ replicas (AZ distributed)
  - Read path: 2+ replicas (query load balancing)
  - Backend: S3 (durability 99.999999999%)

- Metrics: VictoriaMetrics cluster or AMP
  - vminsert: 2+ replicas (write load balancing)
  - vmstorage: 3+ replicas (replication factor 2)
  - vmselect: 2+ replicas (read load balancing)

- Traces: Grafana Tempo
  - Distributor: 2+ replicas
  - Ingester: 3+ replicas (WAL enabled)
  - Backend: S3

**Query Layer:**
- Grafana: 2+ replicas, external PostgreSQL/MySQL for session storage
- Caching: Query result caching with Redis/Memcached

**Key Considerations:**
1. Deploy all stateful components across multiple AZs
2. Use S3 as shared storage (eliminate single point of failure)
3. Prometheus sharding (3-5 shards) + Remote Write to offload to central storage
4. PodDisruptionBudget to ensure availability during rolling updates

</details>

2. In an environment with $5,000/month in observability costs, propose optimization strategies to achieve 50% cost reduction while maintaining quality. Explain specific methods for each area: logging, metrics, and tracing.

<details>
<summary>View Answer</summary>

**Answer:**

**Logging Optimization (Expected savings: $1,500-2,000)**

1. **Log level filtering** (40-60% reduction)
   - Exclude DEBUG/TRACE logs in production environment
   - Implementation: Fluent Bit grep filter with `Exclude log (DEBUG|TRACE)`

2. **Apply sampling** (30-50% reduction)
   - 10% sampling for high-frequency logs (access logs, health checks)
   - Implementation: Fluent Bit throttle filter `Rate 10, Window 60`

3. **Retention period optimization** (20-40% reduction)
   - Production: 14 days, Dev/Staging: 7 days
   - Long-term retention only for important logs (move to S3 Glacier)

4. **Storage migration** (50-70% reduction)
   - CloudWatch Logs ($0.50/GB ingestion) -> Loki + S3 ($0.023/GB storage)

**Metrics Optimization (Expected savings: $500-800)**

1. **Cardinality management**
   - Remove unnecessary labels (pod_template_hash, controller_revision_hash)
   - Drop metrics: exclude internal metrics like `go_.*`, `promhttp_.*`

2. **Scrape interval adjustment**
   - Critical metrics: 15s, General metrics: 30s-60s
   - Limit histogram buckets (remove unnecessary le values)

3. **Utilize Recording Rules**
   - Pre-compute frequently used aggregation queries
   - Early deletion of original high-resolution data (7 days -> 3 days)

4. **Storage migration**
   - Self-managed Prometheus -> VictoriaMetrics (7x compression ratio)
   - Or use AMP (eliminate operational burden, predictable costs)

**Tracing Optimization (Expected savings: $500-1,000)**

1. **Apply Tail Sampling** (80-90% reduction)
   - Error/slow traces: 100% retention
   - Normal traces: only 5-10% sampling

2. **Storage migration**
   - X-Ray ($5/million traces) -> Tempo + S3 (storage costs only)

3. **Retention period optimization**
   - Detailed traces: 7 days
   - Aggregated data: 30 days

**Total Expected Savings: $2,500-3,800 (50-76%)**

The key is importance-based tiering. Instead of treating all data equally, aggressively reduce data while retaining what is needed for problem analysis.

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
- [EKS Observability Optimization Guide](../../advanced/09-observability-optimization.md)
