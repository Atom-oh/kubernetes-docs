# Observability Quiz

> **Supported Version**: Istio 1.28.0 **EKS Version**: 1.34 (Kubernetes 1.28+) **Last Updated**: February 19, 2026

This quiz tests your understanding of Istio's observability features.

## Multiple Choice Questions (1-5)

### Question 1: Prometheus Metrics

Which metric is **NOT** collected by default by Prometheus in Istio?

A. istio\_requests\_total (total request count) B. istio\_request\_duration\_milliseconds (request latency) C. istio\_request\_bytes (request size) D. istio\_pod\_cpu\_usage (Pod CPU usage)

<details>

<summary>Show Answer</summary>

**Answer: D**

Istio Envoy collects **traffic-related metrics** only, while Pod CPU usage is collected by **Kubernetes Metrics Server** or **cAdvisor**.

**Explanation:**

**Metrics collected by Istio:**

1. **istio\_requests\_total (A - O)**

```promql
# Total requests by service
sum(rate(istio_requests_total[5m])) by (destination_service_name)
```

2. **istio\_request\_duration\_milliseconds (B - O)**

```promql
# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)
```

3. **istio\_request\_bytes (C - O)**

```promql
# Request size
sum(rate(istio_request_bytes_sum[5m])) by (destination_service_name)
```

4. **istio\_pod\_cpu\_usage (D - X)**

* This is not an Istio metric
* Kubernetes metric: `container_cpu_usage_seconds_total`
* Requires kube-state-metrics to collect in Prometheus

**Istio Metric Categories:**

| Category     | Example Metric                                | Description                   |
| ------------ | --------------------------------------------- | ----------------------------- |
| **Request**  | istio\_requests\_total                        | Request count, response codes |
| **Duration** | istio\_request\_duration\_milliseconds        | Latency distribution          |
| **Size**     | istio\_request\_bytes, istio\_response\_bytes | Traffic size                  |
| **TCP**      | istio\_tcp\_connections\_opened\_total        | TCP connections               |

**Golden Signals Examples:**

```promql
# 1. Latency
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket{
      destination_service_name="reviews"
    }[5m]
  )) by (le)
)

# 2. Traffic
sum(rate(
  istio_requests_total{
    destination_service_name="reviews"
  }[5m]
))

# 3. Errors (error rate)
sum(rate(
  istio_requests_total{
    destination_service_name="reviews",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{
    destination_service_name="reviews"
  }[5m]
))

# 4. Saturation - Uses Kubernetes metrics
sum(rate(
  container_cpu_usage_seconds_total{
    pod=~"reviews-.*"
  }[5m]
))
```

**Checking Metrics:**

```bash
# Check metrics via Envoy Admin API
kubectl exec <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus

# Check in Prometheus
kubectl port-forward -n istio-system svc/prometheus 9090:9090
# Query at http://localhost:9090
```

**Reference:**

* [Metrics](../../../service-mesh/istio/observability/01-metrics.md)

</details>

***

### Question 2: Distributed Tracing

What is the **minimum configuration** required for distributed tracing in Istio?

A. The application must generate trace IDs B. The application must propagate HTTP headers C. Jaeger client must be installed on all services D. Envoy automatically handles everything

<details>

<summary>Show Answer</summary>

**Answer: B**

Istio Envoy automatically generates trace IDs, but **the application must propagate HTTP headers** to the next service.

**Explanation:**

**How Distributed Tracing Works:**

![Diagram showing the ingress gateway minting distributed-tracing headers on an incoming request, each downstream service (A, B, C) required to forward those headers unchanged to the next hop, and every hop also sending its span to Jaeger.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-0.png)

**HTTP Headers to Propagate:**

```yaml
# Zipkin (B3) headers
x-b3-traceid: Trace ID
x-b3-spanid: Current Span ID
x-b3-parentspanid: Parent Span ID
x-b3-sampled: Sampling decision
x-b3-flags: Flags

# Or single header
b3: {traceid}-{spanid}-{sampled}-{parentspanid}

# Istio internal headers
x-request-id: Unique request ID

# Jaeger native headers (optional)
uber-trace-id
```

**Application Code Examples:**

```python
# Python Flask example
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # 1. Extract received headers
    headers = {}
    for header in ['x-request-id', 'x-b3-traceid', 'x-b3-spanid',
                   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags']:
        if header in request.headers:
            headers[header] = request.headers[header]

    # 2. Propagate headers when calling next service
    response = requests.get(
        'http://user-service/users',
        headers=headers  # Header propagation required
    )

    return response.json()
```

```javascript
// Node.js Express example
const express = require('express');
const axios = require('axios');
const app = express();

app.get('/api/users', async (req, res) => {
  // 1. Extract received headers
  const tracingHeaders = {};
  ['x-request-id', 'x-b3-traceid', 'x-b3-spanid',
   'x-b3-parentspanid', 'x-b3-sampled', 'x-b3-flags'].forEach(header => {
    if (req.headers[header]) {
      tracingHeaders[header] = req.headers[header];
    }
  });

  // 2. Propagate headers when calling next service
  const response = await axios.get('http://user-service/users', {
    headers: tracingHeaders  // Header propagation required
  });

  res.json(response.data);
});
```

**Analysis of Each Option:**

* **A (X)**: Envoy automatically generates trace IDs
* **B (O)**: Application must propagate HTTP headers (required)
* **C (X)**: Jaeger client not needed, Envoy sends Spans
* **D (X)**: Envoy creates/sends Spans, but header propagation is application's responsibility

**Sampling Configuration:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 1.0  # 100% sampling (development)
        # sampling: 10.0  # 10% sampling (production)
```

**Accessing Jaeger:**

```bash
istioctl dashboard jaeger
```

**Reference:**

* [Distributed Tracing](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/02-distributed-tracing.md)

</details>

***

### Question 3: Kiali Visualization

Which feature is **NOT** provided by Kiali?

A. Service topology visualization B. Traffic flow analysis C. Automatic Canary deployment execution D. Istio configuration validation

<details>

<summary>Show Answer</summary>

**Answer: C**

Kiali is an **observation and analysis tool**, while deployment execution is handled by tools like **Argo Rollouts**.

**Explanation:**

**Kiali's Main Features:**

**1. Service Topology Visualization (A - O)**

```bash
# Open Kiali dashboard
istioctl dashboard kiali

# Features:
# - Real-time service connection display
# - Traffic flow direction display
# - Service status (healthy/error)
# - Response time display
```

**Graph View Example:**

```
Frontend → Backend → Database
   ↓
External API

Color codes:
- Green: Normal
- Red: Error
- Gray: No traffic
```

**2. Traffic Flow Analysis (B - O)**

Kiali displays:

* Request count (RPS)
* Error rate (%)
* P50/P95/P99 latency
* TCP connection count

**3. Automatic Canary Deployment Execution (C - X)**

* Kiali does NOT execute deployments
* Kiali only **visualizes** traffic split status
* Deployment execution: Argo Rollouts, Flagger

**4. Istio Configuration Validation (D - O)**

```yaml
# Items Kiali validates:

1. VirtualService errors:
   - Non-existent host reference
   - Invalid subset reference
   - Weight sum not equal to 100

2. DestinationRule errors:
   - Subset labels don't match Pods
   - Duplicate subset names

3. Gateway errors:
   - Missing TLS certificate
   - Invalid selector

4. AuthorizationPolicy errors:
   - Conflicting policies
   - Invalid principal format
```

**Kiali Installation:**

```bash
# Install Kiali included in Istio samples
kubectl apply -f samples/addons/kiali.yaml

# Or install with Helm
helm repo add kiali https://kiali.org/helm-charts
helm install kiali-server kiali/kiali-server \
  --namespace istio-system
```

**Kiali Main Menus:**

```
1. Overview: Service summary by Namespace
2. Graph: Service topology
3. Applications: Application list
4. Workloads: Deployment, StatefulSet, etc.
5. Services: Kubernetes Service
6. Istio Config: VirtualService, DestinationRule, etc.
```

**Kiali vs Other Tools:**

| Tool              | Role                                | Deployment Execution |
| ----------------- | ----------------------------------- | -------------------- |
| **Kiali**         | Visualization, analysis, validation | No                   |
| **Argo Rollouts** | Progressive Delivery                | Yes                  |
| **Flagger**       | Automatic Canary deployment         | Yes                  |
| **Grafana**       | Metrics dashboard                   | No                   |
| **Jaeger**        | Distributed tracing                 | No                   |

**Practical Usage Example:**

```bash
# 1. Check service topology in Kiali
istioctl dashboard kiali

# 2. Detect anomalies in Graph view
#    - reviews service error rate 5%
#    - productpage → reviews latency increase

# 3. Check details in Workload view
#    - Check reviews-v2 Pod logs
#    - Check Envoy metrics

# 4. Validate configuration in Istio Config view
#    - Found typo in VirtualService
#    - Fix and redeploy
```

**Reference:**

* [Visualization](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/04-visualization.md)
* [Kiali Official Documentation](https://kiali.io/docs/)

</details>

***

### Question 4: Access Log Configuration

How do you configure Access Log output in **JSON format** in Istio?

A. Set meshConfig.accessLogEncoding to JSON in IstioOperator B. Directly modify Envoy ConfigMap C. Add annotation to each Pod D. Convert to JSON via Prometheus query

<details>

<summary>Show Answer</summary>

**Answer: A**

Set the **meshConfig.accessLogEncoding** field in IstioOperator to `JSON`.

**Explanation:**

**JSON Format Access Log Configuration:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    # Enable Access Log
    accessLogFile: /dev/stdout

    # Output in JSON format
    accessLogEncoding: JSON

    # Define custom JSON format
    accessLogFormat: |
      {
        "start_time": "%START_TIME%",
        "method": "%REQ(:METHOD)%",
        "path": "%REQ(X-ENVOY-ORIGINAL-PATH?:PATH)%",
        "protocol": "%PROTOCOL%",
        "response_code": "%RESPONSE_CODE%",
        "response_flags": "%RESPONSE_FLAGS%",
        "bytes_received": "%BYTES_RECEIVED%",
        "bytes_sent": "%BYTES_SENT%",
        "duration": "%DURATION%",
        "upstream_service_time": "%RESP(X-ENVOY-UPSTREAM-SERVICE-TIME)%",
        "x_forwarded_for": "%REQ(X-FORWARDED-FOR)%",
        "user_agent": "%REQ(USER-AGENT)%",
        "request_id": "%REQ(X-REQUEST-ID)%",
        "authority": "%REQ(:AUTHORITY)%",
        "upstream_host": "%UPSTREAM_HOST%",
        "upstream_cluster": "%UPSTREAM_CLUSTER%",
        "upstream_local_address": "%UPSTREAM_LOCAL_ADDRESS%",
        "downstream_local_address": "%DOWNSTREAM_LOCAL_ADDRESS%",
        "downstream_remote_address": "%DOWNSTREAM_REMOTE_ADDRESS%",
        "requested_server_name": "%REQUESTED_SERVER_NAME%",
        "route_name": "%ROUTE_NAME%"
      }
```

**Output Example:**

```json
{
  "start_time": "2025-01-20T10:30:00.123Z",
  "method": "GET",
  "path": "/api/users",
  "protocol": "HTTP/1.1",
  "response_code": 200,
  "response_flags": "-",
  "bytes_received": 0,
  "bytes_sent": 1234,
  "duration": 42,
  "upstream_service_time": "40",
  "x_forwarded_for": "192.168.1.100",
  "user_agent": "Mozilla/5.0",
  "request_id": "abc-123-def",
  "authority": "example.com",
  "upstream_host": "10.0.1.20:8080",
  "upstream_cluster": "outbound|8080||backend.default.svc.cluster.local",
  "upstream_local_address": "10.0.1.10:54321",
  "downstream_local_address": "10.0.1.10:8080",
  "downstream_remote_address": "10.0.1.5:12345",
  "requested_server_name": "-",
  "route_name": "default"
}
```

**Per-Namespace Configuration:**

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: access-logging
  namespace: production
spec:
  accessLogging:
  - providers:
    - name: envoy
    # Can configure JSON format for specific Namespace only
```

**Envoy Format Variables:**

```yaml
# Key variables:
%START_TIME%: Request start time
%REQ(HEADER)%: Request header
%RESP(HEADER)%: Response header
%RESPONSE_CODE%: HTTP response code
%DURATION%: Total duration (ms)
%BYTES_RECEIVED%: Bytes received
%BYTES_SENT%: Bytes sent
%UPSTREAM_HOST%: Upstream server address
%DOWNSTREAM_REMOTE_ADDRESS%: Client address
```

**CloudWatch Logs Integration:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: istio-system
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/istio/access-logs
        log_stream_prefix istio-
        auto_create_group true
```

**Checking Logs:**

```bash
# Check Pod's Access Log
kubectl logs <pod-name> -c istio-proxy

# Real-time monitoring
kubectl logs -f <pod-name> -c istio-proxy | jq .

# Filter specific response codes
kubectl logs <pod-name> -c istio-proxy | \
  jq 'select(.response_code == "500")'
```

**TEXT Format vs JSON Format:**

| Item            | TEXT         | JSON            |
| --------------- | ------------ | --------------- |
| **Readability** | High (human) | Low (human)     |
| **Parsing**     | Difficult    | Easy (machine)  |
| **Size**        | Small        | Large           |
| **Structure**   | Unstructured | Structured      |
| **Querying**    | Difficult    | Easy (jq, etc.) |

**TEXT Format Example:**

```
[2025-01-20T10:30:00.123Z] "GET /api/users HTTP/1.1" 200 - "-" "-" 0 1234 42 40 "192.168.1.100" "Mozilla/5.0" "abc-123-def" "example.com" "10.0.1.20:8080" outbound|8080||backend.default.svc.cluster.local 10.0.1.10:54321 10.0.1.10:8080 10.0.1.5:12345 - default
```

**Reference:**

* [Logging](../../../service-mesh/istio/observability/03-logging.md)
* [Envoy Access Log Format](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)

</details>

***

### Question 5: Grafana Dashboards

Which Grafana dashboard is **NOT** provided by default with Istio installation?

A. Istio Service Dashboard B. Istio Workload Dashboard C. Istio Performance Dashboard D. Istio Cost Dashboard

<details>

<summary>Show Answer</summary>

**Answer: D**

Istio does **not provide a Cost Dashboard** by default.

**Explanation:**

**Istio Default Grafana Dashboards:**

**1. Istio Service Dashboard (A - O)**

```
Service-level metrics:
- Request Volume (request count)
- Request Duration (P50, P95, P99)
- Request Size / Response Size
- Success Rate
- 4xx, 5xx error trends
```

**2. Istio Workload Dashboard (B - O)**

```
Workload (Pod) level metrics:
- Incoming Request Volume
- Incoming Success Rate
- Incoming Request Duration
- Incoming Request Size
- Outgoing Request Volume
- Outgoing Success Rate
```

**3. Istio Performance Dashboard (C - O)**

```
Istio's own performance metrics:
- Pilot performance (xDS push time)
- Envoy memory usage
- Envoy CPU usage
- Sidecar injection success rate
- Configuration sync latency
```

**4. Istio Control Plane Dashboard**

```
Control Plane metrics:
- Istiod resource usage
- xDS connection count
- Webhook performance
- Certificate issuance statistics
```

**5. Istio Mesh Dashboard**

```
Overall mesh metrics:
- Total request count
- Overall success rate
- Global P99 latency
- Service count, Pod count
```

**Cost Dashboard Not Available (D - X)**

You need to create a custom dashboard for cost-related metrics:

```promql
# Cross-AZ traffic cost estimation
sum(rate(istio_requests_total{
  source_cluster="us-east-1a",
  destination_cluster!="us-east-1a"
}[5m])) * 86400 * 30 * 0.01 / 1000000

# Sidecar resource cost (memory basis)
sum(container_memory_usage_bytes{
  container="istio-proxy"
}) / 1024 / 1024 / 1024 * 30 * 0.01
```

**Grafana Installation and Access:**

```bash
# Install Grafana
kubectl apply -f samples/addons/grafana.yaml

# Access Grafana
istioctl dashboard grafana

# Or port forwarding
kubectl port-forward -n istio-system svc/grafana 3000:3000
# http://localhost:3000
```

**Creating Custom Dashboard:**

```json
{
  "dashboard": {
    "title": "Istio Custom Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total[5m])) by (destination_service_name)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total{response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total[5m]))"
          }
        ]
      }
    ]
  }
}
```

**Using Dashboard Variables:**

```yaml
# Add Namespace variable
variables:
  - name: namespace
    type: query
    query: label_values(istio_requests_total, destination_workload_namespace)

# Use variable in panel
expr: |
  sum(rate(
    istio_requests_total{
      destination_workload_namespace="$namespace"
    }[5m]
  )) by (destination_service_name)
```

**Reference:**

* [Visualization](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/04-visualization.md)
* [Grafana Official Documentation](https://grafana.com/docs/)

</details>

***

## Short Answer Questions (6-10)

### Question 6: Golden Signals Monitoring

Explain how to monitor Google SRE's **Golden Signals** (Latency, Traffic, Errors, Saturation) using Istio and Prometheus. Include **Prometheus queries** and **alerting rules** for each signal.

<details>

<summary>Show Answer</summary>

**Answer:**

**Golden Signals Monitoring Implementation:**

***

**1. Latency**

**Prometheus Query:**

```promql
# P95 latency
histogram_quantile(0.95,
  sum(rate(
    istio_request_duration_milliseconds_bucket{
      destination_service_name="reviews"
    }[5m]
  )) by (le)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(
    istio_request_duration_milliseconds_bucket{
      destination_service_name="reviews"
    }[5m]
  )) by (le)
)

# P50 latency (median)
histogram_quantile(0.50,
  sum(rate(
    istio_request_duration_milliseconds_bucket{
      destination_service_name="reviews"
    }[5m]
  )) by (le)
)
```

**Alerting Rules:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-latency-alerts
  namespace: monitoring
spec:
  groups:
  - name: latency
    interval: 30s
    rules:
    # P95 latency exceeds 500ms
    - alert: HighLatency
      expr: |
        histogram_quantile(0.95,
          sum(rate(
            istio_request_duration_milliseconds_bucket[5m]
          )) by (le, destination_service_name)
        ) > 500
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High latency detected on {{ $labels.destination_service_name }}"
        description: "P95 latency is {{ $value }}ms"

    # P99 latency exceeds 1 second
    - alert: CriticalLatency
      expr: |
        histogram_quantile(0.99,
          sum(rate(
            istio_request_duration_milliseconds_bucket[5m]
          )) by (le, destination_service_name)
        ) > 1000
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "Critical latency on {{ $labels.destination_service_name }}"
```

***

**2. Traffic**

**Prometheus Query:**

```promql
# Requests per second (RPS)
sum(rate(
  istio_requests_total{
    destination_service_name="reviews"
  }[5m]
))

# RPS by service
sum(rate(
  istio_requests_total[5m]
)) by (destination_service_name)

# RPS by HTTP method
sum(rate(
  istio_requests_total[5m]
)) by (request_method)
```

**Alerting Rules:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-traffic-alerts
spec:
  groups:
  - name: traffic
    rules:
    # Traffic spike (2x normal)
    - alert: TrafficSpike
      expr: |
        sum(rate(istio_requests_total[5m])) by (destination_service_name)
        >
        sum(rate(istio_requests_total[1h] offset 1h)) by (destination_service_name) * 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Traffic spike on {{ $labels.destination_service_name }}"

    # Traffic drop (below 50% of normal)
    - alert: TrafficDrop
      expr: |
        sum(rate(istio_requests_total[5m])) by (destination_service_name)
        <
        sum(rate(istio_requests_total[1h] offset 1h)) by (destination_service_name) * 0.5
      for: 10m
      labels:
        severity: warning
```

***

**3. Errors**

**Prometheus Query:**

```promql
# Error rate (5xx)
sum(rate(
  istio_requests_total{
    destination_service_name="reviews",
    response_code=~"5.."
  }[5m]
))
/
sum(rate(
  istio_requests_total{
    destination_service_name="reviews"
  }[5m]
))

# 4xx + 5xx error rate
sum(rate(
  istio_requests_total{
    destination_service_name="reviews",
    response_code=~"[45].."
  }[5m]
))
/
sum(rate(
  istio_requests_total{
    destination_service_name="reviews"
  }[5m]
))

# Distribution by response code
sum(rate(
  istio_requests_total[5m]
)) by (response_code, destination_service_name)
```

**Alerting Rules:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-error-alerts
spec:
  groups:
  - name: errors
    rules:
    # Error rate > 1%
    - alert: HighErrorRate
      expr: |
        (
          sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service_name)
          /
          sum(rate(istio_requests_total[5m])) by (destination_service_name)
        ) > 0.01
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate on {{ $labels.destination_service_name }}"
        description: "Error rate is {{ $value | humanizePercentage }}"

    # Error rate > 5%
    - alert: CriticalErrorRate
      expr: |
        (
          sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service_name)
          /
          sum(rate(istio_requests_total[5m])) by (destination_service_name)
        ) > 0.05
      for: 2m
      labels:
        severity: critical
```

***

**4. Saturation**

**Prometheus Query:**

```promql
# Envoy CPU usage
sum(rate(
  container_cpu_usage_seconds_total{
    pod=~".*",
    container="istio-proxy"
  }[5m]
)) by (pod)

# Envoy memory usage
sum(
  container_memory_usage_bytes{
    pod=~".*",
    container="istio-proxy"
  }
) by (pod)

# Envoy connection count
sum(
  envoy_cluster_upstream_cx_active
) by (cluster_name)

# Envoy pending requests
sum(
  envoy_cluster_upstream_rq_pending_active
) by (cluster_name)
```

**Alerting Rules:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-saturation-alerts
spec:
  groups:
  - name: saturation
    rules:
    # Envoy CPU > 80%
    - alert: HighEnvoyCPU
      expr: |
        sum(rate(
          container_cpu_usage_seconds_total{
            container="istio-proxy"
          }[5m]
        )) by (pod, namespace)
        /
        sum(
          container_spec_cpu_quota{
            container="istio-proxy"
          } / 100000
        ) by (pod, namespace)
        > 0.8
      for: 5m
      labels:
        severity: warning

    # Envoy Memory > 80%
    - alert: HighEnvoyMemory
      expr: |
        sum(
          container_memory_usage_bytes{
            container="istio-proxy"
          }
        ) by (pod, namespace)
        /
        sum(
          container_spec_memory_limit_bytes{
            container="istio-proxy"
          }
        ) by (pod, namespace)
        > 0.8
      for: 5m
      labels:
        severity: warning

    # Connection Pool Saturated
    - alert: ConnectionPoolSaturated
      expr: |
        envoy_cluster_upstream_cx_active
        /
        envoy_cluster_circuit_breakers_default_cx_open
        > 0.9
      for: 5m
      labels:
        severity: critical
```

***

**Grafana Dashboard Configuration:**

```json
{
  "dashboard": {
    "title": "Golden Signals",
    "panels": [
      {
        "title": "Latency (P95, P99)",
        "targets": [
          {"expr": "histogram_quantile(0.95, sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le))"},
          {"expr": "histogram_quantile(0.99, sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le))"}
        ]
      },
      {
        "title": "Traffic (RPS)",
        "targets": [
          {"expr": "sum(rate(istio_requests_total[5m])) by (destination_service_name)"}
        ]
      },
      {
        "title": "Errors (Rate)",
        "targets": [
          {"expr": "sum(rate(istio_requests_total{response_code=~\"5..\"}[5m])) / sum(rate(istio_requests_total[5m]))"}
        ]
      },
      {
        "title": "Saturation (CPU, Memory)",
        "targets": [
          {"expr": "sum(rate(container_cpu_usage_seconds_total{container=\"istio-proxy\"}[5m])) by (pod)"},
          {"expr": "sum(container_memory_usage_bytes{container=\"istio-proxy\"}) by (pod)"}
        ]
      }
    ]
  }
}
```

**Reference:**

* [Metrics](../../../service-mesh/istio/observability/01-metrics.md)
* [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

</details>

***

### Question 7: Finding Performance Bottlenecks with Jaeger

Explain how to use the distributed tracing tool Jaeger to find **performance bottlenecks** in a microservices architecture. Include **Trace analysis methods** and **practical debugging scenarios**.

<details>

<summary>Show Answer</summary>

**Answer:**

**Performance Bottleneck Analysis with Jaeger:**

***

**1. Jaeger Installation and Configuration**

```bash
# Install Jaeger
kubectl apply -f samples/addons/jaeger.yaml

# Enable Tracing (100% sampling)
istioctl install --set values.pilot.traceSampling=100.0
```

```yaml
# Or configure with IstioOperator
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 100.0  # Development: 100%, Production: 1-10%
        zipkin:
          address: jaeger-collector.istio-system:9411
```

***

**2. Understanding Trace Structure**

```
Trace
└─ Span 1: Ingress Gateway (total 150ms)
   └─ Span 2: Frontend (total 140ms)
      ├─ Span 3: Backend API (total 100ms)
      │  ├─ Span 4: Database Query (80ms)  ← Bottleneck!
      │  └─ Span 5: Cache Check (10ms)
      └─ Span 6: External API (30ms)
```

**Span Information:**

* **Duration**: Time spent in Span
* **Tags**: Metadata (HTTP method, URL, response code)
* **Logs**: Events (errors, warnings)
* **Parent-Child Relationship**: Call hierarchy

***

**3. Practical Debugging Scenarios**

**Scenario 1: High P99 Latency**

**Symptoms:**

```promql
# P99 latency is 2 seconds
histogram_quantile(0.99,
  sum(rate(
    istio_request_duration_milliseconds_bucket[5m]
  )) by (le)
) = 2000
```

**Jaeger Analysis Steps:**

```bash
# 1. Access Jaeger UI
istioctl dashboard jaeger

# 2. Set search criteria
Service: productpage
Lookback: Last 1 hour
Min Duration: 2000ms  # Filter only 2+ seconds
Limit Results: 20

# 3. Analyze results
```

**Identified Problem:**

```
Trace ID: abc-123-def
Total Duration: 2.1 seconds

├─ productpage (2.1s)
   └─ reviews (2.0s)  ← Bottleneck!
      └─ ratings (1.9s)  ← Actual bottleneck!
         └─ MongoDB Query (1.8s)  ← Root cause!
```

**Resolution:**

```yaml
# 1. Optimize MongoDB query
# - Add index
# - Query tuning

# 2. Add caching
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratings-config
data:
  redis.conf: |
    host: redis.default.svc.cluster.local
    port: 6379
    ttl: 300

# 3. Set Timeout
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ratings
spec:
  hosts:
  - ratings
  http:
  - timeout: 500ms  # Set timeout
    retries:
      attempts: 3
      perTryTimeout: 200ms
```

***

**Scenario 2: Intermittent Timeouts**

**Jaeger Analysis:**

```
# Normal Trace
Trace ID: normal-001
Duration: 120ms
├─ frontend (120ms)
   └─ backend (100ms)
      └─ database (80ms)

# Timeout Trace
Trace ID: timeout-001
Duration: 10,000ms  ← Abnormal!
├─ frontend (10,000ms)
   └─ backend (9,980ms)
      └─ database (9,950ms)  ← Bottleneck!
         └─ Error: Connection timeout
```

**Check Span Details:**

```json
{
  "traceID": "timeout-001",
  "spanID": "span-db",
  "operationName": "database.query",
  "duration": 9950000,
  "tags": {
    "db.statement": "SELECT * FROM users WHERE status = 'active'",
    "db.type": "postgresql",
    "error": true
  },
  "logs": [
    {
      "timestamp": 1234567890,
      "fields": [
        {"key": "event", "value": "error"},
        {"key": "error.kind", "value": "ConnectionTimeout"},
        {"key": "message", "value": "Connection pool exhausted"}
      ]
    }
  ]
}
```

**Resolution:**

```yaml
# Increase Connection Pool
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: database
spec:
  host: database
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100  # 50 → 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
```

***

**Scenario 3: Cascading Latency**

**Jaeger Analysis:**

```
Trace ID: cascade-001
Total Duration: 5.2 seconds

├─ frontend (5.2s)
   ├─ backend-a (2.0s)
   │  └─ database (1.9s)
   ├─ backend-b (2.0s)  ← Sequential call issue!
   │  └─ external-api (1.9s)
   └─ backend-c (1.0s)
      └─ cache (0.9s)

Problem: Sequential execution of parallelizable calls
```

**Resolution (Application Modification):**

```python
# Sequential calls (Before)
def get_user_data(user_id):
    profile = call_backend_a(user_id)      # 2 seconds
    orders = call_backend_b(user_id)       # 2 seconds
    recommendations = call_backend_c(user_id)  # 1 second
    return merge(profile, orders, recommendations)

# Total time: 5 seconds

# Parallel calls (After)
import asyncio

async def get_user_data(user_id):
    profile, orders, recommendations = await asyncio.gather(
        call_backend_a(user_id),      # 2 seconds
        call_backend_b(user_id),       # 2 seconds
        call_backend_c(user_id)        # 1 second
    )
    return merge(profile, orders, recommendations)

# Total time: 2 seconds (longest call)
```

***

**4. Jaeger UI Tips**

**Service Dependencies (Service Dependency Graph):**

```bash
# Jaeger UI → Dependencies tab
# - Visualize service call relationships
# - Display error rates
# - Display request counts
```

**Compare Traces:**

```bash
# 1. Select normal Trace
# 2. Select slow Trace
# 3. Click Compare button
# 4. Check time differences per Span
```

**Deep Dependency Graph:**

```bash
# Check detailed dependencies for specific Trace
# - Time spent per Span
# - Parallel/sequential execution status
# - Critical Path
```

***

**5. Performance Optimization Checklist**

```yaml
# 1. Remove unnecessary calls
# - N+1 query problem
# - Duplicate API calls

# 2. Parallel processing
# - Execute independent calls in parallel
# - Use asyncio, Promise.all, etc.

# 3. Caching
# - Redis, Memcached
# - CDN (static resources)

# 4. Connection Pool tuning
# - Appropriate max connections
# - Enable Keep-Alive

# 5. Timeout settings
# - Appropriate timeout (not too long)
# - Fail Fast

# 6. Database optimization
# - Add indexes
# - Query optimization
# - Use read replicas
```

***

**6. Prometheus + Jaeger Integration**

```promql
# Find Traces with high latency
histogram_quantile(0.99,
  sum(rate(
    istio_request_duration_milliseconds_bucket[5m]
  )) by (le, destination_service_name)
) > 1000

# After checking in Prometheus, search Traces in Jaeger for that time period
```

**Reference:**

* [Distributed Tracing](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/02-distributed-tracing.md)
* [Jaeger Official Documentation](https://www.jaegertracing.io/docs/)

</details>

***

### Question 8: Service Mesh Troubleshooting with Kiali

Explain how to diagnose and resolve **common problems** (configuration errors, traffic anomalies, security policy conflicts) in the Istio service mesh using Kiali.

<details>

<summary>Show Answer</summary>

**Answer:**

**Service Mesh Troubleshooting with Kiali:**

***

**1. Configuration Error Diagnosis**

**Problem 1: VirtualService Host Error**

**Symptoms:**

```bash
# Service call failure
curl http://reviews:9080
# 503 Service Unavailable
```

**Kiali Diagnosis:**

```bash
# 1. Access Kiali dashboard
istioctl dashboard kiali

# 2. Istio Config → VirtualServices tab
# 3. Warning indicator on reviews VirtualService

# 4. Click for details
```

**Kiali Error Message:**

```
Warning: VirtualService 'reviews-vs' has issues:
- Host 'reviews.default.svc.cluster.local' references service 'reviews'
  but service does not exist
- Subset 'v2' references DestinationRule 'reviews-dr'
  but subset is not defined
```

**Resolution:**

```yaml
# Incorrect configuration
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-vs
spec:
  hosts:
  - reviews.default.svc.cluster.local  # Service doesn't exist!
  http:
  - route:
    - destination:
        host: reviews
        subset: v2  # Not defined in DestinationRule!

---
# Correct configuration
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: reviews-vs
spec:
  hosts:
  - reviews  # Service name only
  http:
  - route:
    - destination:
        host: reviews
        subset: v1  # Existing subset

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews-dr
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
```

***

**Problem 2: DestinationRule Subset Label Mismatch**

**Kiali Diagnosis:**

```
In Graph view:
- No traffic being sent to reviews service
- Kiali shows red dashed line

In Istio Config tab:
Warning: DestinationRule 'reviews-dr' has issues:
- Subset 'v1' selects labels {version: v1}
  but no pods match these labels
```

**Check Problem:**

```bash
# Check Pod labels
kubectl get pods -l app=reviews --show-labels

# Output:
NAME            LABELS
reviews-v1-xxx  app=reviews,version=1.0  ← version=1.0 (wrong)
```

**Resolution:**

```yaml
# Incorrect DestinationRule
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
spec:
  subsets:
  - name: v1
    labels:
      version: v1  # Pod has version=1.0

# Corrected DestinationRule
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
spec:
  subsets:
  - name: v1
    labels:
      version: "1.0"  # Match Pod label
```

***

**2. Traffic Anomaly Diagnosis**

**Problem 3: Traffic Imbalance**

**Check in Kiali Graph view:**

```
frontend → backend-v1 (90% traffic)  ← Expected: 50%
frontend → backend-v2 (10% traffic)  ← Expected: 50%
```

**Root Cause Analysis:**

```bash
# Kiali → Workloads tab → backend
# Check Pod status:

backend-v1: 5 pods (all Ready)
backend-v2: 5 pods (3 Ready, 2 Terminating)

# Problem: backend-v2 Pods not starting normally
```

**Resolution:**

```bash
# 1. Check backend-v2 logs in Kiali
Workloads → backend-v2 → Logs tab

# 2. Analyze logs
Error: Cannot connect to database
Connection: postgresql://db:5432

# 3. Fix
kubectl edit deployment backend-v2
# Fix database connection string

# 4. Verify traffic balance in Kiali
# After few minutes: 50% / 50% normalized
```

***

**Problem 4: Circular Dependency**

**Check in Kiali Graph view:**

```
service-a → service-b
    ↑           ↓
    └───────────┘

Circular dependency detected!
```

**Kiali Alert:**

```
Warning: Circular dependency detected:
service-a → service-b → service-a
```

**Resolution:**

```yaml
# Architecture redesign needed
# Before:
service-a ↔ service-b

# After:
service-a → service-c (common service)
service-b → service-c
```

***

**3. Security Policy Conflict Diagnosis**

**Problem 5: AuthorizationPolicy Conflict**

**Symptoms:**

```bash
# frontend → backend call fails
curl http://backend:8080
# 403 RBAC: access denied
```

**Kiali Diagnosis:**

```bash
# Kiali → Istio Config → Authorization Policies

Policy 1:
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec: {}  # Deny all requests

Policy 2:
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]

# Kiali warning:
Warning: Policy conflict detected:
- deny-all denies all traffic
- allow-frontend allows traffic from frontend
- Evaluation order: DENY policies are evaluated first
```

**Resolution:**

```yaml
# Correct configuration (per-Namespace separation)
---
# deny-all applies only to specific service
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: backend-deny-all
spec:
  selector:
    matchLabels:
      app: backend
  # Empty rules = deny all requests

---
# Explicit allow policy
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: backend-allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

***

**Problem 6: mTLS Mode Mismatch**

**Check in Kiali Security view:**

```
service-a: mTLS STRICT
service-b: mTLS PERMISSIVE
service-c: mTLS DISABLED

Kiali warning:
Warning: mTLS configuration mismatch detected
- service-a requires mTLS but service-c has mTLS disabled
- Connection may fail
```

**Resolution:**

```yaml
# Apply consistent mTLS policy across entire mesh
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Apply STRICT to all services
```

***

**4. Kiali Advanced Features**

**Custom Time Range:**

```bash
# Kiali → Graph view
# Time Range: Last 1 hour
# Refresh Interval: Every 15s

# Analyze specific time period
# - Check before/after incident
# - Compare before/after deployment
```

**Traffic Animation:**

```bash
# Kiali → Graph view
# Display: Enable Traffic Animation

# Real-time traffic flow visualization
# - Request size shown as animation speed
# - Errors shown in red
```

**Edge Labels:**

```bash
# Kiali → Graph view
# Edge Labels:
# - Request percentage
# - Request per second
# - Response time (95th percentile)

# Check traffic split ratio
frontend → backend-v1: 80% (8 rps)
frontend → backend-v2: 20% (2 rps)
```

**Service Details:**

```bash
# Kiali → Services → backend

Tabs:
1. Overview: Summary information
2. Traffic: Inbound/Outbound traffic
3. Inbound Metrics: Metric charts
4. Traces: Jaeger trace integration
5. Envoy: Envoy configuration check
```

***

**5. Troubleshooting Workflow**

![Decision-ladder diagram showing a Kiali-driven troubleshooting loop: open the Kiali graph view, classify the problem into one of four categories (no traffic, errors, slow response, security denied), diagnose and fix it, then verify — looping back to the start if unresolved or finishing if resolved.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-observability-1.png)

**Reference:**

* [Visualization](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/04-visualization.md)
* [Kiali Official Documentation](https://kiali.io/docs/)

</details>

***

### Question 9: Production Observability Stack Setup

Explain how to deploy the Istio observability stack (Prometheus, Grafana, Jaeger, Kiali) in **High Availability (HA)** configuration for a production Kubernetes cluster. Include **persistent storage**, **scaling**, and **backup** strategies.

<details>

<summary>Show Answer</summary>

**Answer:**

**Production Observability Stack Setup:**

Due to the length of this answer, please refer to the Korean source file for the complete implementation details including:

1. **Prometheus HA Configuration** with Helm (kube-prometheus-stack)
2. **Thanos for Long-term Metric Storage** with S3 backend
3. **Jaeger HA Configuration** with Elasticsearch backend
4. **Kiali HA Configuration**
5. **Backup and Recovery Strategy** with Velero
6. **Monitoring and Alerting** with PrometheusRules

**Reference:**

* [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)
* [Thanos](https://thanos.io/tip/thanos/getting-started.md/)
* [Jaeger Operator](https://www.jaegertracing.io/docs/latest/operator/)

</details>

***

### Question 10: Custom Metrics and Dashboard Creation

Explain how to collect **business metrics** (e.g., order count, payment success rate) beyond the default metrics collected by Istio Envoy, and create a Grafana custom dashboard.

<details>

<summary>Show Answer</summary>

**Answer:**

**Custom Metrics and Dashboard Creation:**

Due to the length of this answer, please refer to the Korean source file for the complete implementation details including:

1. **Exposing Metrics from Application** (Python Flask and Node.js Express examples)
2. **Kubernetes ServiceMonitor Configuration**
3. **Prometheus Queries** for business metrics
4. **Grafana Custom Dashboard** JSON configuration
5. **Dashboard Provisioning** with ConfigMap
6. **Alerting Configuration** with PrometheusRules

**Reference:**

* [Metrics](../../../service-mesh/istio/observability/01-metrics.md)
* [Prometheus Client Libraries](https://prometheus.io/docs/instrumenting/clientlibs/)
* [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)

</details>

***

## Score Calculation

* Multiple Choice 1-5: 10 points each (Total 50 points)
* Short Answer 6-10: 10 points each (Total 50 points)
* **Total: 100 points**

**Evaluation Criteria:**

* 90-100 points: Excellent (Istio Observability Expert)
* 80-89 points: Good (Capable of production monitoring)
* 70-79 points: Average (Additional learning recommended)
* 60-69 points: Below Average (Review of basic concepts needed)
* 0-59 points: Re-learning needed

## Learning Resources

* [Metrics](../../../service-mesh/istio/observability/01-metrics.md)
* [Distributed Tracing](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/02-distributed-tracing.md)
* [Logging](../../../service-mesh/istio/observability/03-logging.md)
* [Visualization](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/istio/observability/04-visualization.md)
