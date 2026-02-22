# Linkerd Observability Quiz

This quiz tests your understanding of Linkerd observability features.

## Quiz Questions

### 1. Which is NOT a golden metric automatically collected by Linkerd?

A. Success rate
B. Request rate (RPS)
C. Latency
D. CPU usage

<details>
<summary>Show Answer</summary>

**Answer: D. CPU usage**

**Explanation:**
Linkerd automatically collects three golden metrics: success rate, request rate (RPS), and latency (p50, p95, p99). CPU usage is a Kubernetes metric that must be collected separately.

</details>

### 2. What is NOT included in the `linkerd viz stat` command output?

A. SUCCESS (success rate)
B. RPS (request rate)
C. LATENCY_P99
D. ERROR_TYPE

<details>
<summary>Show Answer</summary>

**Answer: D. ERROR_TYPE**

**Explanation:**
`linkerd viz stat` shows MESHED, SUCCESS, RPS, LATENCY_P50/P95/P99. Error types must be checked via `linkerd viz tap` or logs.

</details>

### 3. What is the purpose of the `linkerd viz tap` command?

A. Network packet capture
B. View real-time request stream
C. Change proxy configuration
D. Renew certificates

<details>
<summary>Show Answer</summary>

**Answer: B. View real-time request stream**

**Explanation:**
`linkerd viz tap` streams requests in real-time. It shows request method, path, status code, latency, mTLS status, and more.

</details>

### 4. What additional metrics can be obtained by defining a ServiceProfile?

A. Pod resource usage
B. Per-route metrics
C. Network bandwidth
D. Disk I/O

<details>
<summary>Show Answer</summary>

**Answer: B. Per-route metrics**

**Explanation:**
Defining a ServiceProfile enables collection of per-route (e.g., GET /api/users, POST /api/orders) success rate, request rate, and latency metrics. View with `linkerd viz routes` command.

</details>

### 5. What is the default method to access the Viz extension's Prometheus?

A. NodePort service
B. LoadBalancer service
C. kubectl port-forward
D. Public URL

<details>
<summary>Show Answer</summary>

**Answer: C. kubectl port-forward**

**Explanation:**
Viz's Prometheus is deployed as a ClusterIP service. Access via `kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090`. External exposure is not recommended for security.

</details>

### 6. Which header is NOT required for distributed tracing propagation?

A. x-b3-traceid
B. x-request-id
C. x-linkerd-proxy
D. x-b3-spanid

<details>
<summary>Show Answer</summary>

**Answer: C. x-linkerd-proxy**

**Explanation:**
Headers needed for distributed tracing: x-request-id, x-b3-traceid, x-b3-spanid, x-b3-parentspanid, x-b3-sampled, b3, etc. x-linkerd-proxy doesn't exist.

</details>

### 7. What does the `linkerd viz top` command show?

A. Pods using most resources
B. Most active request paths
C. Top error messages
D. Latest log entries

<details>
<summary>Show Answer</summary>

**Answer: B. Most active request paths**

**Explanation:**
`linkerd viz top` shows the most active request paths in real-time. It displays Source, Destination, Method, Path, Count, Latency, Success Rate, etc.

</details>

### 8. What annotation sets the proxy log level?

A. config.linkerd.io/log-level
B. config.linkerd.io/proxy-log-level
C. linkerd.io/proxy-log
D. proxy.linkerd.io/log-level

<details>
<summary>Show Answer</summary>

**Answer: B. config.linkerd.io/proxy-log-level**

**Explanation:**
The `config.linkerd.io/proxy-log-level` annotation sets the proxy log level. Example: "warn,linkerd=info,linkerd_proxy=debug"

</details>

### 9. What is the correct Prometheus query to calculate Linkerd success rate?

A. `sum(response_total{classification="success"}) / sum(response_total)`
B. `rate(success_total[5m]) / rate(request_total[5m])`
C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`
D. `avg(success_rate)`

<details>
<summary>Show Answer</summary>

**Answer: C. `sum(rate(response_total{classification="success"}[5m])) / sum(rate(response_total[5m]))`**

**Explanation:**
Success rate is calculated by dividing successful response rate by total response rate. The rate() function calculates per-second rate within the time range, and sum() aggregates.

</details>

### 10. What is the main function of the Jaeger extension?

A. Metrics collection
B. Log aggregation
C. Distributed tracing
D. Traffic splitting

<details>
<summary>Show Answer</summary>

**Answer: C. Distributed tracing**

**Explanation:**
The Jaeger extension provides distributed tracing. It visualizes the complete path of requests through multiple services and analyzes latency at each step.

</details>

### 11. Which view is NOT provided by the linkerd viz dashboard command?

A. Topology
B. Deployments
C. Pod Logs
D. Routes

<details>
<summary>Show Answer</summary>

**Answer: C. Pod Logs**

**Explanation:**
The Viz dashboard provides Namespace, Deployments, Pods, TCP, Routes, Topology, and Tap views. Pod logs must be checked via kubectl logs or a separate logging system.

</details>

### 12. What Viz installation option is used when integrating with external Grafana?

A. `--set grafana.external=true`
B. `--set grafana.enabled=false`
C. `--set grafana.url=external`
D. `--set monitoring=external`

<details>
<summary>Show Answer</summary>

**Answer: B. `--set grafana.enabled=false`**

**Explanation:**
When using external Grafana, disable Viz's built-in Grafana. Use `helm install linkerd-viz linkerd/linkerd-viz --set grafana.enabled=false` or configure in values file.

</details>
