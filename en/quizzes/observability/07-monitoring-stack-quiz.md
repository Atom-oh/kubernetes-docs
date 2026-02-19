# Monitoring Stack Quiz

This quiz tests your understanding of the Kubernetes monitoring stack (VictoriaMetrics, Prometheus, Grafana).

## Multiple Choice Questions

1. Which is correct about Prometheus's metrics collection method?
   - A) Applications push metrics to the Prometheus server
   - B) Prometheus scrapes metrics from targets via HTTP
   - C) Agents collect metrics and send them to a central server
   - D) Metrics are streamed in real-time via events

<details>

<summary>Show Answer</summary>

**Answer: B) Prometheus scrapes metrics from targets via HTTP**

**Explanation:**
Prometheus uses a pull-based metrics collection method. The Prometheus server sends HTTP requests to each target's /metrics endpoint at configured scrape intervals (scrape_interval) to collect metrics. This approach integrates well with service discovery and has the advantage of directly verifying target status. However, for short-lived jobs, push method via Pushgateway is also supported.
</details>

2. Which is NOT an advantage of VictoriaMetrics over Prometheus?
   - A) Higher data compression ratio
   - B) Faster query performance
   - C) Uses a completely different query language from PromQL
   - D) Supports cluster mode for horizontal scaling

<details>

<summary>Show Answer</summary>

**Answer: C) Uses a completely different query language from PromQL**

**Explanation:**
VictoriaMetrics supports fully compatible PromQL with Prometheus. Therefore, existing queries and dashboards can be used as-is when migrating from Prometheus to VictoriaMetrics. The actual advantages of VictoriaMetrics are up to 7x more efficient data compression, up to 20x faster query performance, and horizontal scalability through vmcluster.
</details>

3. What is the correct role of kube-state-metrics?
   - A) Collect node CPU, memory, and disk usage
   - B) Convert Kubernetes API object states to metrics
   - C) Collect container runtime metrics
   - D) Monitor network traffic

<details>

<summary>Show Answer</summary>

**Answer: B) Convert Kubernetes API object states to metrics**

**Explanation:**
kube-state-metrics monitors the Kubernetes API server and converts states of various Kubernetes objects (Deployment, Pod, Node, Service, etc.) to Prometheus metrics format. For example, it provides metrics like kube_pod_status_phase, kube_deployment_spec_replicas, kube_node_status_condition. Node system resources (CPU, memory, etc.) are handled by node-exporter.
</details>

4. What is the main purpose of the Prometheus Operator's ServiceMonitor CRD?
   - A) Automatically create Kubernetes services
   - B) Declaratively define service endpoints to monitor
   - C) Route service mesh traffic
   - D) Perform service health checks

<details>

<summary>Show Answer</summary>

**Answer: B) Declaratively define service endpoints to monitor**

**Explanation:**
ServiceMonitor is a CRD (Custom Resource Definition) provided by Prometheus Operator that declaratively defines which Kubernetes services to collect metrics from. In ServiceMonitor, you select target services with label selectors and specify scrape interval, metrics path, port, etc. Prometheus Operator detects this and automatically updates Prometheus's scrape configuration.
</details>

5. What is the purpose of Alertmanager's groupBy setting?
   - A) To send alerts only to specific recipients
   - B) To bundle alerts with same characteristics to reduce duplicate alerts
   - C) To determine alert priority
   - D) To specify alert message format

<details>

<summary>Show Answer</summary>

**Answer: B) To bundle alerts with same characteristics to reduce duplicate alerts**

**Explanation:**
Alertmanager's groupBy setting bundles alerts with the same labels (e.g., alertname, job, namespace) into one group. For example, with `groupBy: ['alertname', 'namespace']`, alerts of the same type from the same namespace are bundled into one alert message. This prevents alert storms during major incidents and reduces recipient fatigue.
</details>

6. What is the benefit of Grafana dashboard provisioning?
   - A) No need to manually create dashboards
   - B) Dashboard configurations can be managed as code and deployed GitOps-style
   - C) Dashboard performance is improved
   - D) User authentication is simplified

<details>

<summary>Show Answer</summary>

**Answer: B) Dashboard configurations can be managed as code and deployed GitOps-style**

**Explanation:**
Grafana dashboard provisioning is a feature where Grafana automatically loads dashboards defined as JSON files or ConfigMaps. This allows dashboard configurations to be managed in version control systems (Git) and deployed consistently through CI/CD pipelines. It provides the advantage of automatically deploying the same dashboards to multiple environments (development, staging, production) and tracking change history.
</details>

7. Which component handles query processing in VictoriaMetrics cluster mode?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) vmagent

<details>

<summary>Show Answer</summary>

**Answer: C) vmselect**

**Explanation:**
VictoriaMetrics cluster mode consists of three main components. vminsert handles metrics collection and distribution, vmstorage stores actual metric data. vmselect processes user PromQL queries, retrieves data from multiple vmstorage nodes, and aggregates results. This separated architecture allows each component to be scaled independently.
</details>

8. Which is NOT a metric type collected by Node Exporter?
   - A) CPU usage
   - B) Filesystem usage
   - C) Kubernetes Pod status
   - D) Network interface statistics

<details>

<summary>Show Answer</summary>

**Answer: C) Kubernetes Pod status**

**Explanation:**
Node Exporter is a Prometheus exporter that collects hardware and OS-level metrics from Linux/Unix systems. It collects system resource metrics like CPU, memory, disk, and network. Kubernetes Pod status metrics (e.g., pod count, status, restart count) are collected by kube-state-metrics through the Kubernetes API.
</details>

## Short Answer Questions

9. What is the PromQL function to calculate the average rate of HTTP requests per second over the last 5 minutes?

<details>

<summary>Show Answer</summary>

**Answer:**
The `rate()` function.

**Explanation:**
In PromQL, the `rate()` function calculates the rate of change per time for Counter type metrics. For example, `rate(http_requests_total[5m])` returns the average HTTP requests per second over the last 5 minutes. The rate() function automatically handles Counter resets and interpolates start and end points of time series data for accurate rate calculation. A similar function `irate()` uses only the last two samples to calculate instantaneous rate.
</details>

10. Explain two main reasons for using Recording Rules in Prometheus.

<details>

<summary>Show Answer</summary>

**Answer:**
1. **Query Performance Optimization**: Pre-compute and store complex, frequently used queries to reduce response time for dashboard and alert queries.
2. **Resource Efficiency**: Prevent the same complex query from being executed multiple times, reducing Prometheus server CPU and memory usage.

**Explanation:**
Recording Rules are defined using the `record` field in PrometheusRule CRD. For example, you can pre-compute `sum(rate(http_requests_total[5m])) by (job)` as `job:http_requests_total:rate5m`. This allows dashboards to directly query this metric for fast responses, with particularly significant performance benefits when querying long-term data.
</details>

11. Explain the role of Alertmanager's `for` field (e.g., for: 5m).

<details>

<summary>Show Answer</summary>

**Answer:**
The `for` field specifies how long the condition must persist before an alert is actually sent.

**Explanation:**
An alert rule with `for: 5m` will only transition to "firing" state and be sent to Alertmanager after the alert condition is met continuously for 5 minutes. During this period, the alert stays in "pending" state. This setting is important for preventing false alerts from temporary spikes or flapping. For example, if CPU usage briefly exceeds 90% then returns to normal, no alert is triggered.
</details>

12. Explain the role of vmagent and the reason for using Remote Write in Prometheus.

<details>

<summary>Show Answer</summary>

**Answer:**
vmagent is a lightweight agent that collects metrics and forwards them to VictoriaMetrics (or other remote storage). Remote Write is a protocol for sending collected metrics to remote time series databases.

**Explanation:**
vmagent is compatible with Prometheus scrape configuration while using fewer resources. Main reasons for using Remote Write:
1. **Long-term Storage**: Overcome Prometheus local storage limitations for long-term data retention
2. **High Availability**: Centralize data from multiple Prometheus/vmagent instances
3. **Scalability**: Handle large-scale metrics with VictoriaMetrics cluster
4. **Separated Architecture**: Separate collection and storage for independent scaling
</details>

## Hands-on Questions

13. Write a PrometheusRule that fires when HTTP 5XX error rate is 10% or higher. (Critical alert after 10 minutes)

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: http-error-rate-alert
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: http-alerts
    rules:
    - alert: HighHTTPErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        /
        sum(rate(http_requests_total[5m]))
        > 0.1
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "High HTTP 5XX error rate detected"
        description: "HTTP 5XX error rate is above 10% (current value: {{ $value | printf \"%.2f\" }}%)"
```

**Explanation:**
This PrometheusRule calculates the ratio of HTTP requests with 5XX status codes to total HTTP requests. `status=~"5.."` is a regex matching 500-599 status codes. `for: 10m` only fires alerts when this condition persists for 10 minutes. The release: prometheus label enables Prometheus Operator to detect this rule.
</details>

14. Write a ServiceMonitor to have Prometheus collect application metrics. (app: myapp label, port: metrics, path: /metrics, interval: 30 seconds)

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: myapp-monitor
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: myapp
  namespaceSelector:
    matchNames:
    - default
    - production
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    scheme: http
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace
```

**Explanation:**
ServiceMonitor selects target services with selector and defines scrape configuration in endpoints. namespaceSelector specifies namespaces to monitor. relabelings can add Kubernetes metadata (pod name, namespace) as metric labels for use in queries and alerts. The release: prometheus label must match Prometheus's serviceMonitorSelector.
</details>

15. Write a ConfigMap to add both VictoriaMetrics and Prometheus as Grafana data sources.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
  labels:
    grafana_datasource: "true"
data:
  datasources.yaml: |-
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-operated:9090
      access: proxy
      isDefault: true
      editable: false
      jsonData:
        timeInterval: "15s"
        httpMethod: POST
    - name: VictoriaMetrics
      type: prometheus
      url: http://victoria-metrics-single-server:8428
      access: proxy
      isDefault: false
      editable: false
      jsonData:
        timeInterval: "15s"
        httpMethod: POST
    - name: VictoriaMetrics-LongTerm
      type: prometheus
      url: http://victoria-metrics-cluster-vmselect:8481/select/0/prometheus
      access: proxy
      isDefault: false
      editable: false
      jsonData:
        timeInterval: "1m"
```

**Explanation:**
Grafana data source provisioning is declaratively managed through ConfigMaps. Since VictoriaMetrics is compatible with the Prometheus API, set type to prometheus. Single-node VictoriaMetrics uses port 8428, cluster mode vmselect uses port 8481. The data source with isDefault: true is selected by default in new dashboards. httpMethod: POST is recommended to avoid URL length limits for long queries.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (Monitoring stack expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 4-6 correct: Basic (basic concepts review needed)
- 0-3 correct: Insufficient (full content re-study needed)
