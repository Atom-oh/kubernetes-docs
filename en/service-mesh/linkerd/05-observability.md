# Linkerd Observability

> **Supported Versions**: Linkerd 2.16+
> **Last Updated**: February 21, 2025

## Overview

Linkerd provides powerful observability features out of the box. Without any instrumentation, it automatically collects golden signals (success rate, request rate, latency) and enables real-time service health monitoring through intuitive dashboards and CLI tools.

## Observability Architecture

```mermaid
graph TB
    subgraph "Data Plane"
        P1[Proxy 1<br/>Metrics Collection]
        P2[Proxy 2<br/>Metrics Collection]
        P3[Proxy 3<br/>Metrics Collection]
    end

    subgraph "Viz Extension"
        PROM[Prometheus<br/>Metrics Storage]
        GRAF[Grafana<br/>Visualization]
        WEB[Web Dashboard<br/>UI]
        TAP[Tap API<br/>Real-time Stream]
        METRICS[Metrics API<br/>Aggregation]
    end

    subgraph "External (Optional)"
        EXT_PROM[External Prometheus]
        EXT_GRAF[External Grafana]
        JAEGER[Jaeger<br/>Distributed Tracing]
    end

    P1 -->|:4191| PROM
    P2 -->|:4191| PROM
    P3 -->|:4191| PROM

    PROM --> GRAF
    PROM --> METRICS
    METRICS --> WEB
    TAP --> WEB

    PROM --> EXT_PROM
    EXT_PROM --> EXT_GRAF
    P1 --> JAEGER
```

## Golden Metrics

Linkerd automatically collects three of Google's golden signals.

### Three Core Metrics

| Metric | Description | Prometheus Metric |
|--------|-------------|-------------------|
| **Success Rate** | Ratio of successful requests (2xx/3xx) | `response_total{classification="success"}` |
| **Request Rate** | Requests per second (RPS) | `request_total` |
| **Latency** | Request processing time distribution (p50, p95, p99) | `response_latency_ms_bucket` |

### Checking Metrics

```bash
# Basic statistics
linkerd viz stat deploy -n my-app

# Expected output:
# NAME      MESHED   SUCCESS   RPS  LATENCY_P50  LATENCY_P95  LATENCY_P99
# api       2/2      99.50%   100       10ms         50ms        100ms
# web       3/3      98.20%   200       15ms         80ms        200ms
# database  1/1     100.00%    50        5ms         20ms         50ms

# Detailed specific Deployment
linkerd viz stat deploy/web -n my-app --to deploy/api

# Per-Pod statistics
linkerd viz stat po -n my-app

# Per-Namespace statistics
linkerd viz stat ns
```

## Viz Dashboard

The Viz extension provides a web-based dashboard.

### Accessing the Dashboard

```bash
# Open dashboard (auto-launches browser)
linkerd viz dashboard

# Open on specific port
linkerd viz dashboard --port 8084

# Run in background
linkerd viz dashboard &

# Allow external access (caution: security consideration required)
linkerd viz dashboard --address 0.0.0.0
```

### Dashboard Features

```mermaid
graph TB
    subgraph "Dashboard Views"
        NS[Namespace Overview<br/>Per-namespace Status]
        DEPLOY[Deployments<br/>Deployment Status]
        PODS[Pods<br/>Pod Status]
        TOPO[Topology<br/>Service Topology]
        ROUTES[Routes<br/>Per-route Metrics]
        TAP[Tap<br/>Real-time Requests]
    end

    NS --> DEPLOY
    DEPLOY --> PODS
    DEPLOY --> ROUTES
    NS --> TOPO
    DEPLOY --> TAP
```

**Dashboard Views:**

| View | Description |
|------|-------------|
| Namespace | Mesh status overview per namespace |
| Deployments | Success rate, RPS, latency per deployment |
| Pods | Detailed metrics per Pod |
| TCP | TCP connection metrics |
| Routes | Metrics per ServiceProfile route |
| Topology | Service-to-service communication visualization |
| Tap | Real-time request stream |

## CLI Tools

### linkerd viz stat

Queries service statistics.

```bash
# Basic usage
linkerd viz stat <resource-type> [flags]

# Resource types: deploy, po, ns, svc, rs, job, cronjob, ds, sts

# Deployment statistics
linkerd viz stat deploy -n my-app

# Traffic to specific service only
linkerd viz stat deploy/web -n my-app --to deploy/api

# Traffic from specific service only
linkerd viz stat deploy/api -n my-app --from deploy/web

# Specify time range
linkerd viz stat deploy -n my-app --time-window 10m

# JSON output
linkerd viz stat deploy -n my-app -o json

# Show additional info (proxy version, etc.)
linkerd viz stat deploy -n my-app -o wide
```

### linkerd viz top

Shows the most active paths in real-time.

```bash
# Top request paths for Deployment
linkerd viz top deploy/web -n my-app

# Expected output:
# Source                Destination          Method  Path                Count  Best  Worst  Last  Success
# web-7b8f9c-abc12     api-5d6e7f-xyz89      GET    /api/users            150   2ms   50ms   5ms    98.00%
# web-7b8f9c-abc12     api-5d6e7f-xyz89      POST   /api/orders            50   5ms  100ms  10ms    96.00%

# Entire namespace
linkerd viz top ns/my-app

# Show hidden headers
linkerd viz top deploy/web -n my-app --hide-sources=false
```

### linkerd viz tap

Views real-time request streams.

```bash
# Basic tap
linkerd viz tap deploy/web -n my-app

# Expected output:
# req id=0:0 proxy=out src=10.0.0.1:54321 dst=10.0.0.2:80 tls=true :method=GET :path=/api/users
# rsp id=0:0 proxy=out src=10.0.0.1:54321 dst=10.0.0.2:80 tls=true :status=200 latency=5ms
# end id=0:0 proxy=out src=10.0.0.1:54321 dst=10.0.0.2:80 tls=true duration=5ms response-length=1234B

# Filtering
linkerd viz tap deploy/web -n my-app --method GET --path /api

# Traffic to specific destination
linkerd viz tap deploy/web -n my-app --to deploy/api

# Traffic from specific source
linkerd viz tap deploy/api -n my-app --from deploy/web

# Include HTTP headers
linkerd viz tap deploy/web -n my-app --show-headers

# Limit maximum requests
linkerd viz tap deploy/web -n my-app --max-rps 100

# JSON output
linkerd viz tap deploy/web -n my-app -o json
```

### linkerd viz routes

Checks metrics per ServiceProfile route.

```bash
# Per-route statistics
linkerd viz routes deploy/api -n my-app

# Expected output:
# ROUTE                          SERVICE   SUCCESS      RPS   LATENCY_P50   LATENCY_P95   LATENCY_P99
# GET /api/users                 api       99.50%    50.0rps         10ms          50ms         100ms
# POST /api/orders               api       98.00%    20.0rps         20ms         100ms         200ms
# GET /health                    api      100.00%     5.0rps          1ms           2ms           5ms
# [DEFAULT]                      api       95.00%    10.0rps         15ms          80ms         150ms

# Routes to specific destination
linkerd viz routes deploy/web -n my-app --to svc/api

# Time range
linkerd viz routes deploy/api -n my-app --time-window 10m
```

### linkerd viz edges

Checks service-to-service connections (edges).

```bash
# Check edges
linkerd viz edges deploy -n my-app

# Expected output:
# SRC          DST          SRC_NS    DST_NS    SECURED
# web          api          my-app    my-app    √
# api          database     my-app    database  √
# ingress      web          ingress   my-app    √

# Per-Pod edges
linkerd viz edges po -n my-app
```

## Prometheus Integration

### Built-in Prometheus (Viz Included)

Uses the Prometheus included with the Viz extension.

```bash
# Access Prometheus
kubectl port-forward -n linkerd-viz svc/prometheus 9090:9090

# Access http://localhost:9090 in browser
```

### External Prometheus Integration

Integrate Linkerd metrics with existing Prometheus.

```yaml
# prometheus-additional-scrape-configs.yaml
- job_name: 'linkerd-controller'
  kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
      - linkerd
      - linkerd-viz
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: admin-http
  - source_labels: [__meta_kubernetes_namespace]
    action: replace
    target_label: namespace
  - source_labels: [__meta_kubernetes_pod_name]
    action: replace
    target_label: pod
  - source_labels: [__meta_kubernetes_pod_container_name]
    action: replace
    target_label: container

- job_name: 'linkerd-proxy'
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_container_name
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: ^linkerd-proxy;linkerd-admin$
  - source_labels: [__meta_kubernetes_namespace]
    action: replace
    target_label: namespace
  - source_labels: [__meta_kubernetes_pod_name]
    action: replace
    target_label: pod
  - source_labels: [__meta_kubernetes_pod_label_linkerd_io_proxy_deployment]
    action: replace
    target_label: deployment
  - action: labeldrop
    regex: __meta_kubernetes_pod_label_linkerd_io_proxy_job
```

### Prometheus Operator Integration

```yaml
# ServiceMonitor for Linkerd
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: linkerd-controller
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames:
    - linkerd
  selector:
    matchLabels:
      linkerd.io/control-plane-component: destination
  endpoints:
  - port: admin-http
    interval: 10s

---
# PodMonitor for Linkerd Proxies
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: linkerd-proxies
  namespace: monitoring
spec:
  namespaceSelector:
    any: true
  selector:
    matchLabels:
      linkerd.io/control-plane-ns: linkerd
  podMetricsEndpoints:
  - port: linkerd-admin
    interval: 10s
    path: /metrics
```

### Key Prometheus Metrics

```promql
# Success rate (5-minute window)
sum(rate(response_total{classification="success"}[5m])) by (deployment)
/
sum(rate(response_total[5m])) by (deployment)

# Request rate (RPS)
sum(rate(request_total[5m])) by (deployment)

# P99 latency
histogram_quantile(0.99,
  sum(rate(response_latency_ms_bucket[5m])) by (le, deployment)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(response_latency_ms_bucket[5m])) by (le, deployment)
)

# P50 latency
histogram_quantile(0.50,
  sum(rate(response_latency_ms_bucket[5m])) by (le, deployment)
)

# TCP connection count
sum(tcp_open_total) by (deployment)

# Retry ratio
sum(rate(request_total{direction="outbound", tls="true", retry="true"}[5m]))
/
sum(rate(request_total{direction="outbound", tls="true"}[5m]))

# mTLS ratio
sum(rate(response_total{tls="true"}[5m]))
/
sum(rate(response_total[5m]))
```

## Grafana Dashboards

### Viz Built-in Grafana

```bash
# Access Grafana
kubectl port-forward -n linkerd-viz svc/grafana 3000:3000

# Access http://localhost:3000 in browser
```

### External Grafana Integration

```yaml
# Disable Grafana when installing Viz
# viz-values.yaml
grafana:
  enabled: false
```

### Pre-built Dashboards

Linkerd provides several Grafana dashboards:

| Dashboard | Description |
|-----------|-------------|
| Linkerd Health | Control plane status |
| Linkerd Top Line | Overall mesh overview |
| Linkerd Deployment | Per-deployment details |
| Linkerd Pod | Per-Pod details |
| Linkerd Service | Per-service details |
| Linkerd Route | Per-route details |
| Linkerd Authority | Per-authority details |
| Linkerd Multicluster | Multicluster status |

### Custom Dashboard Example

```json
{
  "title": "Linkerd Service Overview",
  "panels": [
    {
      "title": "Success Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(rate(response_total{classification=\"success\", namespace=\"$namespace\", deployment=\"$deployment\"}[5m])) / sum(rate(response_total{namespace=\"$namespace\", deployment=\"$deployment\"}[5m])) * 100",
          "legendFormat": "Success Rate"
        }
      ]
    },
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(request_total{namespace=\"$namespace\", deployment=\"$deployment\"}[5m]))",
          "legendFormat": "RPS"
        }
      ]
    },
    {
      "title": "Latency Distribution",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, sum(rate(response_latency_ms_bucket{namespace=\"$namespace\", deployment=\"$deployment\"}[5m])) by (le))",
          "legendFormat": "p50"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(response_latency_ms_bucket{namespace=\"$namespace\", deployment=\"$deployment\"}[5m])) by (le))",
          "legendFormat": "p95"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(response_latency_ms_bucket{namespace=\"$namespace\", deployment=\"$deployment\"}[5m])) by (le))",
          "legendFormat": "p99"
        }
      ]
    }
  ]
}
```

## Distributed Tracing (Jaeger)

### Jaeger Extension Installation

```bash
# Install Jaeger extension
linkerd jaeger install | kubectl apply -f -

# Verify installation
linkerd jaeger check

# Open dashboard
linkerd jaeger dashboard
```

### Tracing Configuration

```yaml
# Jaeger extension values
# jaeger-values.yaml
collector:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 100Mi
      limit: 500Mi

jaeger:
  replicas: 1
  resources:
    cpu:
      request: 100m
      limit: 500m
    memory:
      request: 100Mi
      limit: 500Mi

# Sampling configuration
webhook:
  collectorSvcAddr: collector.linkerd-jaeger:55678
```

### Application Trace Headers

Applications must propagate trace headers for distributed tracing:

```yaml
# Headers to propagate
# - x-request-id
# - x-b3-traceid
# - x-b3-spanid
# - x-b3-parentspanid
# - x-b3-sampled
# - x-b3-flags
# - b3
```

```python
# Python Flask example
from flask import Flask, request
import requests

app = Flask(__name__)

# Headers to propagate
TRACE_HEADERS = [
    'x-request-id',
    'x-b3-traceid',
    'x-b3-spanid',
    'x-b3-parentspanid',
    'x-b3-sampled',
    'x-b3-flags',
    'b3'
]

@app.route('/api/data')
def get_data():
    # Extract trace headers
    headers = {h: request.headers.get(h) for h in TRACE_HEADERS if request.headers.get(h)}

    # Propagate headers when calling downstream services
    response = requests.get('http://backend-service/api/backend', headers=headers)
    return response.json()
```

```go
// Go example
package main

import (
    "net/http"
)

var traceHeaders = []string{
    "x-request-id",
    "x-b3-traceid",
    "x-b3-spanid",
    "x-b3-parentspanid",
    "x-b3-sampled",
    "x-b3-flags",
    "b3",
}

func handler(w http.ResponseWriter, r *http.Request) {
    // Create downstream request
    req, _ := http.NewRequest("GET", "http://backend-service/api/backend", nil)

    // Propagate trace headers
    for _, h := range traceHeaders {
        if v := r.Header.Get(h); v != "" {
            req.Header.Set(h, v)
        }
    }

    client := &http.Client{}
    resp, _ := client.Do(req)
    defer resp.Body.Close()
}
```

### External Jaeger Integration

```yaml
# When using external Jaeger
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkerd-jaeger-config
  namespace: linkerd-jaeger
data:
  config.yaml: |
    collector:
      address: jaeger-collector.monitoring:14268
```

## Access Logging

### Proxy Log Configuration

```yaml
# Set log level via Pod annotation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template:
    metadata:
      annotations:
        config.linkerd.io/proxy-log-level: "warn,linkerd=info,linkerd_proxy=debug"
        config.linkerd.io/proxy-log-format: "json"
```

### Log Levels

| Level | Description |
|-------|-------------|
| error | Errors only |
| warn | Warnings and above |
| info | Info and above (default) |
| debug | Debug and above |
| trace | All logs |

### Viewing Logs

```bash
# Check proxy logs
kubectl logs deploy/web -n my-app -c linkerd-proxy

# Real-time log stream
kubectl logs deploy/web -n my-app -c linkerd-proxy -f

# Filter specific keywords
kubectl logs deploy/web -n my-app -c linkerd-proxy | grep "error"
```

## ServiceProfile Metrics

Defining ServiceProfiles enables per-route metric collection.

### Enabling Per-Route Metrics

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: api-service.my-app.svc.cluster.local
  namespace: my-app
spec:
  routes:
  - name: GET /api/users
    condition:
      method: GET
      pathRegex: /api/users
    isRetryable: true

  - name: POST /api/orders
    condition:
      method: POST
      pathRegex: /api/orders
    isRetryable: false

  - name: GET /health
    condition:
      method: GET
      pathRegex: /health
```

### Route Metric Queries

```promql
# Per-route success rate
sum(rate(route_response_total{classification="success"}[5m])) by (rt_route)
/
sum(rate(route_response_total[5m])) by (rt_route)

# Per-route latency
histogram_quantile(0.99,
  sum(rate(route_response_latency_ms_bucket[5m])) by (le, rt_route)
)

# Per-route request rate
sum(rate(route_request_total[5m])) by (rt_route)
```

## Monitoring Best Practices

### Alert Configuration

```yaml
# Prometheus alert rules
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: linkerd-alerts
  namespace: monitoring
spec:
  groups:
  - name: linkerd
    rules:
    # Low success rate alert
    - alert: LinkerdHighErrorRate
      expr: |
        (
          sum(rate(response_total{classification="failure"}[5m])) by (deployment, namespace)
          /
          sum(rate(response_total[5m])) by (deployment, namespace)
        ) > 0.05
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"
        description: "{{ $labels.deployment }} in {{ $labels.namespace }} has error rate > 5%"

    # High latency alert
    - alert: LinkerdHighLatency
      expr: |
        histogram_quantile(0.99,
          sum(rate(response_latency_ms_bucket[5m])) by (le, deployment, namespace)
        ) > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High latency detected"
        description: "{{ $labels.deployment }} p99 latency > 1s"

    # Proxy not injected alert
    - alert: LinkerdProxyNotInjected
      expr: |
        sum by (namespace) (
          kube_pod_status_phase{phase="Running"}
        ) - sum by (namespace) (
          kube_pod_container_status_running{container="linkerd-proxy"}
        ) > 0
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Pods without Linkerd proxy"
        description: "Some pods in {{ $labels.namespace }} are not meshed"
```

### Dashboard Configuration Recommendations

```yaml
# Key monitoring dashboard configuration
1. Overview Dashboard:
   - Overall mesh success rate
   - Total request rate
   - Top error services

2. Per-Service Dashboard:
   - Service success rate trend
   - Request rate trend
   - Latency distribution (p50, p95, p99)
   - Upstream/downstream dependencies

3. Infrastructure Dashboard:
   - Control plane status
   - Proxy resource usage
   - Certificate expiration time
```

### Troubleshooting Workflow

```mermaid
graph TB
    START[Issue Detected] --> STAT[linkerd viz stat]
    STAT --> CHECK{Low Success<br/>Rate?}

    CHECK -->|Yes| TOP[linkerd viz top]
    CHECK -->|No| LATENCY{High<br/>Latency?}

    TOP --> TAP[linkerd viz tap]
    TAP --> LOGS[Check Proxy Logs]

    LATENCY -->|Yes| ROUTES[linkerd viz routes]
    LATENCY -->|No| EDGES[linkerd viz edges]

    ROUTES --> TAP
    EDGES --> CHECK_TLS{mTLS<br/>Issue?}

    CHECK_TLS -->|Yes| CERT[Check Certificates]
    CHECK_TLS -->|No| END[Issue Resolved]

    LOGS --> END
    CERT --> END
```

## Next Steps

- [Multi-cluster](./06-multi-cluster.md): Cross-cluster observability
- [Best Practices](./07-best-practices.md): Production monitoring setup

## References

- [Linkerd Observability](https://linkerd.io/2/features/dashboard/)
- [Prometheus Integration](https://linkerd.io/2/tasks/exporting-metrics/)
- [Grafana Dashboards](https://linkerd.io/2/tasks/grafana/)
- [Distributed Tracing](https://linkerd.io/2/tasks/distributed-tracing/)
