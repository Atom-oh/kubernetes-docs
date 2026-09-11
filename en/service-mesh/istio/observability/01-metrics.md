# Istio Metrics

> **Supported Versions**: Istio 1.31
> **Last Reviewed**: September 11, 2026

> **Validation scope**: These lab configurations were checked against official references and offline validators, without deploying a cluster. Namespace, identity, storage, backend and load assumptions are stated with each example and must be verified for the target environment.

Istio proxies generate metrics for observed traffic. This guide covers sidecar/Envoy HTTP and TCP metrics and scraping through Prometheus or the OpenTelemetry Collector. Ambient ztunnel has different L4 metrics; HTTP metrics require a waypoint.

## Table of Contents

1. [Metrics Overview](#metrics-overview)
2. [Istio Standard Metrics](#istio-standard-metrics)
3. [Circuit Breaker Metrics](#circuit-breaker-metrics)
4. [Resilience Metrics](#resilience-metrics)
5. [OpenTelemetry Integration](#opentelemetry-integration)
6. [Prometheus Integration](#prometheus-integration)
7. [Customization with Telemetry API](#customization-with-telemetry-api)
8. [Practical Metric Queries](#practical-metric-queries)
9. [Metrics Optimization](#metrics-optimization)
10. [Troubleshooting](#troubleshooting)

## Metrics Overview

### Golden Signals

Combine proxy telemetry with node/container exporters to measure the Golden Signals:

1. **Latency**: Request processing time
2. **Traffic**: System throughput (RPS, Bandwidth)
3. **Errors**: Failure rate and error types
4. **Saturation**: Queue/connection pressure plus CPU/memory from Kubernetes exporters

### Metrics Collection Architecture

Envoy exposes Prometheus metrics → either Prometheus scrapes directly, or an OpenTelemetry Collector Prometheus receiver scrapes them → a configured metrics backend → Grafana/Kiali. The Istio OpenTelemetry extension provider configures tracing; it is not an OTLP metrics sender.

## Istio Standard Metrics

### HTTP/gRPC Metrics

Envoy generates these metrics for recognized HTTP/gRPC traffic. A metric is emitted per reporting proxy, so choose one reporter for a given question. Destination reporting avoids duplicate observations of a hop, while source reporting is needed for upstream failures that never reach the destination. Group service names with namespaces (and clusters where relevant).

#### istio_requests_total

**Type**: Counter
**Description**: Total number of requests processed

```promql
istio_requests_total{
  reporter="destination",  # Peer security policy populated at destination
  source_workload="productpage-v1",
  source_workload_namespace="default",
  source_principal="spiffe://cluster.local/ns/default/sa/bookinfo-productpage",
  source_app="productpage",
  source_version="v1",
  source_canonical_service="productpage",
  source_canonical_revision="v1",
  destination_workload="reviews-v1",
  destination_workload_namespace="default",
  destination_principal="spiffe://cluster.local/ns/default/sa/bookinfo-reviews",
  destination_app="reviews",
  destination_version="v1",
  destination_service="reviews.default.svc.cluster.local",
  destination_service_name="reviews",
  destination_service_namespace="default",
  destination_canonical_service="reviews",
  destination_canonical_revision="v1",
  request_protocol="http",
  response_code="200",
  response_flags="-",
  connection_security_policy="mutual_tls",
  grpc_response_status="",
  destination_cluster="",
  source_cluster=""
}
```

**Key Labels**:
- `response_code`: HTTP status code (200, 404, 500, etc.)
- `response_flags`: Envoy response flags
  - `UH`: No healthy upstream
  - `UF`: Upstream connection failure
  - `UR`: Upstream remote reset; `UT`: upstream request timeout
  - `DC`: Downstream connection termination
  - `LR`: Local reset
  - `URX`: Upstream retry limit exceeded (or TCP maximum connect attempts)
- `connection_security_policy`: mTLS status (`mutual_tls`, `none`; source reports can be `unknown`)

#### istio_request_duration_milliseconds

**Type**: Histogram
**Description**: Request processing time (milliseconds)

```promql
istio_request_duration_milliseconds_bucket{le="10"}  # 10ms or less
istio_request_duration_milliseconds_bucket{le="50"}  # 50ms or less
istio_request_duration_milliseconds_bucket{le="100"} # 100ms or less
istio_request_duration_milliseconds_bucket{le="500"} # 500ms or less
istio_request_duration_milliseconds_sum            # Total time
istio_request_duration_milliseconds_count          # Total request count
```

#### istio_request_bytes

**Type**: Histogram
**Description**: Request body size (bytes)

```promql
istio_request_bytes_bucket  # Inspect actual le bounds
istio_request_bytes_bucket{le="+Inf"}  # All body sizes
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**Type**: Histogram
**Description**: Response body size (bytes)

```promql
istio_response_bytes_bucket
istio_response_bytes_bucket{le="+Inf"}
istio_response_bytes_sum
istio_response_bytes_count
```

### TCP Metrics

#### istio_tcp_connections_opened_total

**Type**: Counter
**Description**: Number of opened TCP connections

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**Type**: Counter
**Description**: Number of closed TCP connections

#### istio_tcp_sent_bytes_total

**Type**: Counter
**Description**: Number of bytes sent

#### istio_tcp_received_bytes_total

**Type**: Counter
**Description**: Number of bytes received

## Circuit Breaker Metrics

Enable required Envoy statistics with `proxyStatsMatcher` before scraping. The default Istio bootstrap extracts `cluster_name`; custom bootstraps may change labels. Circuit-breaker `_open` metrics are 0/1 gauges, not event counters. Some counters appear only after traffic.

### Key Circuit Breaker Metrics

#### 1. Upstream Connection Pool Overflow

```promql
# Requests rejected due to connection pool overflow
envoy_cluster_upstream_cx_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**Meaning**: `maxConnections` limit exceeded

#### 2. Circuit Breaker Open (Gauge)

```promql
# Gauge: 1 at capacity, 0 below limit
envoy_cluster_circuit_breakers_default_rq_open{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 3. Pending Requests Overflow

```promql
# Pending request count exceeded
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**Meaning**: pending/active request circuit-breaking rejection. Inspect `rq_pending_open`, `rq_open` and the generated thresholds to distinguish queue pressure from the active-request limit.

#### 4. Retry Budget Exhausted

```promql
# Retry budget exhausted
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. Detecting Circuit Breaker via Response Flags

```promql
# Requests rejected by circuit breaker (response_flags="UO")
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**Response Flags Details**:
- `UO`: Upstream overflow (circuit breaker open)
- `URX`: Upstream retry limit exceeded (or TCP maximum connect attempts)
- `UF`: Upstream connection failure
- `UH`: No healthy upstream

### Circuit Breaker Monitoring Dashboard Queries

```promql
# Fraction of observed samples at capacity over five minutes (%).
100 * avg_over_time(envoy_cluster_circuit_breakers_default_rq_open[5m])

# Active connections and pending requests (per proxy/cluster).
envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active

# Rejected request events over five minutes.
sum by (namespace, pod, cluster_name) (
  increase(envoy_cluster_upstream_rq_pending_overflow[5m])
)
```

There are no standard `circuit_breakers_default_cx_max` or `rq_pending_max` gauges. Read limits from generated cluster configuration. Optional `remaining_cx`/`remaining_pending` gauges require Envoy `track_remaining`; merely including a metric name does not enable them. A utilization denominator must come from a known matching configured limit.

### Circuit Breaker Alert Rules

```yaml
groups:
- name: istio_circuit_breaker
  rules:
  - alert: CircuitBreakerAtCapacity
    expr: envoy_cluster_circuit_breakers_default_rq_open == 1
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: Request breaker remains at capacity for {{ $labels.cluster_name }}
  - alert: ConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_cx_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Connection limit exceeded for {{ $labels.cluster_name }}
  - alert: PendingRequestsOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Request circuit-breaking rejection for {{ $labels.cluster_name }}
```

## Resilience Metrics

### Outlier Detection Metrics

#### 1. Ejected Hosts

```promql
# Number of hosts ejected by outlier detection
envoy_cluster_outlier_detection_ejections_active{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 2. Ejection Events

```promql
# Ejection event rate
rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m])
```

**By Ejection Type**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_enforced_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
```

Detected and enforced ejections differ: a detected outlier can remain in service because enforcement probability or the maximum ejection percentage prevents ejection. Some Envoy algorithms are not exposed by Istio DestinationRule; a missing series is not evidence that a configured algorithm is healthy.

### Retry Metrics

```promql
# Number of retried requests
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry success rate
rate(envoy_cluster_upstream_rq_retry_success[5m])
/
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry budget exhausted
rate(envoy_cluster_upstream_rq_retry_overflow[5m])
```

### Timeout Metrics

```promql
# Requests that timed out
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# Timeout rate
sum(rate(istio_requests_total{reporter="source",response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total{reporter="source"}[5m]))
* 100
```

## OpenTelemetry Integration

### Prometheus Receiver for Istio Metrics

The Istio `opentelemetry` extension provider exports **traces**. To collect standard mesh metrics, keep the Prometheus metrics provider and let an OpenTelemetry Collector **Prometheus receiver scrape** the exposed endpoints. A collector can then export metrics over OTLP to a metrics-capable backend; Tempo is a trace backend, not a metrics destination.

This example uses Collector Contrib 0.160.0 with a Prometheus exporter for a visible demonstration path. Create namespace `observability` first. Use one replica because replicas with identical scrape configurations duplicate every target; production scaling needs target allocation/sharding. The ServiceAccount can only read pods, as required by the pod discovery jobs. Configure network access to cleartext proxy metrics 15090 and istiod 15014; this example does not scrape application metrics or ambient ztunnel.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-metrics
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-metrics-pod-reader
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-metrics-pod-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-metrics-pod-reader
subjects:
- kind: ServiceAccount
  name: otel-metrics
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-metrics-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      prometheus:
        config:
          global:
            scrape_interval: 15s
            evaluation_interval: 15s
          scrape_configs:
          - job_name: envoy-stats
            metrics_path: /stats/prometheus
            kubernetes_sd_configs:
            - role: pod
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_phase
              action: keep
              regex: Running
            - source_labels:
              - __meta_kubernetes_pod_container_name
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istio-proxy;.*-envoy-prom
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
          - job_name: istiod
            metrics_path: /metrics
            kubernetes_sd_configs:
            - role: pod
              namespaces:
                names:
                - istio-system
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_label_app
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istiod;http-monitoring
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 512
      batch:
        timeout: 10s
        send_batch_size: 1024
    exporters:
      prometheus:
        endpoint: 0.0.0.0:8889
        const_labels:
          environment: production
      debug:
        verbosity: basic
    service:
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - batch
          exporters:
          - prometheus
          - debug
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-metrics
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-metrics
  template:
    metadata:
      labels:
        app: otel-metrics
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: otel-metrics
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 8889
          name: prometheus
        volumeMounts:
        - name: config
          mountPath: /etc/otel
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      volumes:
      - name: config
        configMap:
          name: otel-metrics-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-metrics
  namespace: observability
  labels:
    app: otel-metrics
spec:
  selector:
    app: otel-metrics
  ports:
  - name: prometheus
    port: 8889
    targetPort: prometheus
```

The retired `logging` exporter is replaced by `debug`. Remove diagnostic exporting after validation. No `namespace: istio` prefix is added, avoiding a second `istio_` prefix on existing metric names. Inspect the collector's emitted labels/names before reusing Kiali dashboards. With a Prometheus Operator, select the labelled Service:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: otel-metrics
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-metrics
  endpoints:
  - port: prometheus
    interval: 15s
    path: /metrics
    honorLabels: true
```

The Prometheus resource must select this ServiceMonitor and its namespace. `honorLabels` retains the original target `job`/`instance`; the collector must be a trusted source. Use either this collector path or direct proxy scraping below for the same series, not both. This ServiceMonitor does not install Prometheus.

### Verify Collection

```bash
kubectl logs -n observability deployment/otel-metrics
# Keep this running in one terminal.
kubectl port-forward -n observability svc/otel-metrics 8889:8889
```

```bash
# In a second terminal, after generating test mesh traffic:
curl -fsS http://localhost:8889/metrics | rg '^istio_'
```

Trace OTLP receivers and exporters are configured separately in the [tracing chapter](02-tracing.md); proxy debug logs do not prove metric delivery.

## Prometheus Integration

### Prometheus Configuration

Use the following config in an installed Prometheus server with pod list/watch permission. A ConfigMap alone does not deploy or reload Prometheus. These pod discovery jobs preserve Kubernetes-discovered addresses (including IPv6) and select exactly the Envoy metrics port or istiod monitoring port. They include sidecars and gateways, so a separate gateway job would duplicate series. The removed Mixer `istio-telemetry` Service is not a scrape target.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: istio-system
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
    - job_name: envoy-stats
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_phase
        action: keep
        regex: Running
      - source_labels:
        - __meta_kubernetes_pod_container_name
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istio-proxy;.*-envoy-prom
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
    - job_name: istiod
      metrics_path: /metrics
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_label_app
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istiod;http-monitoring
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
```

Proxy-only scraping uses 15090 `/stats/prometheus`. Default merged agent/application metrics use 15020 `/stats/prometheus` with `prometheus.io` annotations and require a different, non-duplicating scrape job. Agent certificate metrics require that agent endpoint. These metrics listeners are cleartext even when application traffic uses STRICT mTLS; restrict their network exposure. Scraping a separate application endpoint follows its own authentication policy.

### Prometheus Operator Alternative

Use these instead of the manual jobs. Ensure the Prometheus resource selects their labels/namespaces. `namespaceSelector.any: true` makes PodMonitor inspect application namespaces; `port: http-envoy-prom` picks the actual metrics container port. Adapt a custom gateway's port name. ServiceMonitor selects Services, not Deployment labels.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-component-monitor
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: istiod
  endpoints:
  - port: http-monitoring
    interval: 15s
    path: /metrics
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: envoy-stats-monitor
  namespace: istio-system
spec:
  namespaceSelector:
    any: true
  selector:
    matchExpressions:
    - key: istio-prometheus-ignore
      operator: DoesNotExist
  podMetricsEndpoints:
  - port: http-envoy-prom
    path: /stats/prometheus
    interval: 15s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      action: keep
      regex: istio-proxy
```

### Prometheus Query Optimization

```yaml
# Recording Rules to pre-compute frequently used queries
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # Request rate by service
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # Error rate by service
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) by (destination_service_name, destination_service_namespace)
      /
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # P95 latency by service
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))
        by (destination_service_name, destination_service_namespace, le)
      )

  # Circuit breaker state gauge
  - record: istio:circuit_breaker:at_capacity
    expr: |
      envoy_cluster_circuit_breakers_default_rq_open
```

## Customization with Telemetry API

### Metrics Customization

#### 1. Enable Only Specific Metrics

Overrides are evaluated in order. Disable ALL_METRICS first, then re-enable the two required HTTP metrics. `mode` belongs inside `match`. Merge related settings into a single Telemetry per selection scope rather than applying all independent examples together.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
        mode: CLIENT_AND_SERVER
      disabled: true
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      disabled: false
    - match:
        metric: REQUEST_DURATION
        mode: CLIENT_AND_SERVER
      disabled: false
```

#### 2. Add Custom Labels

Use bounded CEL expressions on HTTP metrics. Request IDs, arbitrary User-Agent values and timing headers create unbounded labels. `x-envoy-upstream-service-time` is a duration, not an upstream cluster identity. CEL does not use the example shell-style `| split()` syntax.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-tags
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        api_version:
          value: 'request.url_path.startsWith("/api/v1/") ? "v1" : (request.url_path.startsWith("/api/v2/")
            ? "v2" : "other")'
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method
            : "OTHER"'
```

#### 3. Namespace-Specific Metrics Configuration

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: namespace-metrics
  namespace: production
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      tagOverrides:
        environment:
          value: '"production"'
```

#### 4. Improve Performance by Disabling Metrics

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: disable-tcp-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    # Completely disable TCP metrics
    - match:
        metric: TCP_OPENED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_CLOSED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_SENT_BYTES
      disabled: true
    - match:
        metric: TCP_RECEIVED_BYTES
      disabled: true
```

## Practical Metric Queries

HTTP status-based error ratios do not catch every gRPC failure. For gRPC, examine `grpc_response_status` and the application's definition of failure; HTTP 200 can carry a nonzero gRPC status.

### Golden Signals Dashboard

#### 1. Latency

```promql
# P50 latency
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# Average latency by service
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

#### 2. Traffic

```promql
# Request rate by service (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Total request rate
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# Inbound traffic by service (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Outbound traffic by service (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Request distribution by protocol (not HTTP method)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name, destination_service_namespace)
```

#### 3. Errors

```promql
# Error rate (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# Separate 4xx vs 5xx
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Track specific error codes
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Analyze error types via response flags
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name, destination_service_namespace)
```

#### 4. Saturation

```promql
# Connection count and breaker state (not a utilization percentage).
envoy_cluster_upstream_cx_active
envoy_cluster_circuit_breakers_default_cx_open

# Active and pending requests.
envoy_cluster_upstream_rq_active
envoy_cluster_upstream_rq_pending_active

# Allocated proxy memory in bytes; compare with the container memory limit separately.
envoy_server_memory_allocated
```

### mTLS Monitoring

```promql
# mTLS usage rate
sum(rate(istio_requests_total{
  connection_security_policy="mutual_tls",
  reporter="destination"
}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))
* 100

# Detect non-mTLS traffic
sum(rate(istio_requests_total{
  connection_security_policy="none",
  reporter="destination"
}[5m])) by (source_workload, destination_workload)

# HTTP 401 observed on authenticated mesh traffic; this is not a TLS handshake failure.
sum by (destination_service_name, destination_service_namespace) (
  rate(istio_requests_total{reporter="destination",response_code="401",connection_security_policy="mutual_tls"}[5m])
)
```

### Service Mesh Health Dashboard

```promql
# Scrape health, not a complete control-plane health check.
up{job="istiod"}

# Istiod xDS build/send error rate, by type.
sum by (type) (rate(pilot_xds_pushes{type=~".*(builderr|senderr)"}[5m]))

# Configuration convergence time, seconds (not push count).
histogram_quantile(0.95,
  sum by (le) (rate(pilot_proxy_convergence_time_bucket[5m]))
)

# Recently started Envoy process; uptime is elapsed seconds, not a timestamp.
envoy_server_uptime < 300
```

Use `istioctl version` to inspect actual proxy versions and `istioctl proxy-status` for synchronization/NACK diagnosis. Process age does not measure configuration freshness, and an Envoy numeric version gauge is not a version-label distribution. For mTLS failures inspect TLS verification counters and certificates as described in the [mTLS guide](../security/01-mtls.md).

## Metrics Optimization

### Solving High Cardinality Problems

#### 1. Remove Unnecessary Labels

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: reduce-cardinality
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
      tagOverrides:
        # Remove high cardinality labels
        request_id:
          operation: REMOVE
        user_agent:
          operation: REMOVE
```

#### 2. Normalize Label Values

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: normalize-labels
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        # Normalize HTTP methods (GET, POST, PUT, DELETE, OTHER)
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER"'
```

### Selecting Envoy Statistics

`proxyStatsMatcher` selects which Envoy statistics to create; it does not sample requests. Include only needed families, preserve required existing matches, and roll selected proxies after changing bootstrap settings. This example enables statistics needed by the preceding queries:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyStatsMatcher:
        inclusionRegexps:
        - ".*upstream_rq_timeout.*"
        - ".*upstream_cx_connect_timeout.*"
        - ".*upstream_cx_connect_fail.*"
        - ".*upstream_rq_pending_overflow.*"
        - ".*circuit_breakers.*"
        - ".*outlier_detection.*"
        - ".*upstream_cx_(active|overflow).*"
        - ".*upstream_rq_(active|retry|pending).*"
```

### Prometheus Performance Tuning

Prometheus defaults to a 1-minute scrape interval; 15s/30s are deliberate choices. This is a configuration fragment to merge with existing scrape jobs. `metric_relabel_configs` belongs inside each scrape job and drops samples, not just labels. Remote-write endpoint, authentication/TLS and persistence must be configured for the chosen backend.

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
remote_write:
- url: http://victoria-metrics:8428/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 5
    min_shards: 1
    max_samples_per_send: 5000
scrape_configs:
- job_name: envoy-stats
  metrics_path: /stats/prometheus
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_phase
    action: keep
    regex: Running
  - source_labels:
    - __meta_kubernetes_pod_container_name
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: istio-proxy;.*-envoy-prom
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: pod
  metric_relabel_configs:
  - source_labels:
    - __name__
    regex: istio_tcp_.*
    action: drop
```

## Troubleshooting

The exec/curl examples require a proxy image containing curl. Otherwise use `kubectl port-forward pod/<pod-name> 15090:15090` (or 15020 for the agent) and query from a second terminal. Telemetry examples here are for Envoy; use waypoint attachment for ambient L7 policy and separate ztunnel L4 collection.

### When Metrics Are Not Being Collected

#### 1. Check Envoy Metrics Endpoint

```bash
# Check Envoy admin port
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# Check metrics filter
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. Check if Prometheus Discovered Targets

```bash
# Check Targets page in Prometheus UI
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# In browser: http://localhost:9090/targets
```

#### 3. Validate Telemetry API Configuration

```bash
# Check Telemetry resources
kubectl get telemetry -A

# Check specific Telemetry details
kubectl describe telemetry <name> -n <namespace>

# Check if reflected in Envoy config
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
```

### When Metric Labels Are Missing

```bash
# 1. Check if Envoy generates correct labels
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Check Prometheus relabeling rules
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. Check ServiceMonitor/PodMonitor
kubectl get servicemonitor,podmonitor -n istio-system
```

### Metric Cardinality Explosion

After port-forwarding Prometheus in another terminal, query active series and TSDB statistics. Counting metric names is not counting time series. The TSDB status endpoint also reports per-label/value cardinality.

```bash
curl -fsS http://localhost:9090/api/v1/status/tsdb | jq '.data'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=count(istio_requests_total)' | jq '.data.result'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=topk(10, count by (__name__) ({__name__=~"istio_.*"}))' | jq '.data.result'
```

### When Circuit Breaker Metrics Are Not Visible

```bash
# 1. Check Envoy cluster statistics
istioctl proxy-config cluster <pod-name> --fqdn <service-fqdn> -o json | \
  jq '.[] | .circuitBreakers'

# 2. Check directly from Envoy admin
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl "localhost:15000/clusters" | grep -A 10 "outbound|80||<service>"

# 3. Verify DestinationRule is correctly applied
istioctl analyze -n <namespace>
```

## References

- [Istio Metrics](https://istio.io/latest/docs/reference/config/metrics/)
- [Istio Observability](https://istio.io/latest/docs/tasks/observability/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Envoy Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Istio Dashboards](https://grafana.com/grafana/dashboards/?search=istio)
