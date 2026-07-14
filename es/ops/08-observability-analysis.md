# Análisis de observabilidad: correlación de logs/métricas/trazas

> **Versiones compatibles**: Loki 3.0+, Tempo 2.4+, Prometheus 2.50+, Grafana 10.0+
> **Última actualización**: February 23, 2026

< [Anterior: Configuración de alertas operativas](./07-observability-alerts.md) | [Tabla de contenidos](./README.md) | [Siguiente: Operaciones del stack de observabilidad](./09-observability-stack.md) >

---

## 1. Estrategia de correlación

La observabilidad efectiva requiere correlacionar logs, métricas y trazas para comprender el comportamiento del sistema. Esta sección cubre la arquitectura y la implementación de la correlación entre señales en entornos EKS.

### Estándares de propagación de Trace ID

Dos estándares principales para la propagación del contexto de trazas distribuidas:

**W3C TraceContext (Recomendado)**

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             |  |                                |                |
             |  |                                |                └─ flags (sampled)
             |  |                                └─ parent span ID (16 hex chars)
             |  └─ trace ID (32 hex chars)
             └─ version

tracestate: vendor1=value1,vendor2=value2
```

**B3 Headers (Legacy/Zipkin)**

```
X-B3-TraceId: 463ac35c9f6413ad48485a3953bb6124
X-B3-SpanId: 0020000000000001
X-B3-ParentSpanId: 0010000000000000
X-B3-Sampled: 1
X-B3-Flags: 0

# Single header format
b3: 463ac35c9f6413ad48485a3953bb6124-0020000000000001-1-0010000000000000
```

### Instrumentación del SDK de OpenTelemetry

Configura el SDK de OTEL para la propagación automática de trazas:

```yaml
# otel-config.yaml for Kubernetes deployment
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
            cors:
              allowed_origins:
                - "*"

    processors:
      batch:
        timeout: 1s
        send_batch_size: 1024

      resource:
        attributes:
          - key: k8s.cluster.name
            value: "production"
            action: upsert
          - key: deployment.environment
            value: "production"
            action: upsert

      # Add Kubernetes metadata
      k8sattributes:
        auth_type: "serviceAccount"
        passthrough: false
        extract:
          metadata:
            - k8s.namespace.name
            - k8s.deployment.name
            - k8s.pod.name
            - k8s.node.name
          labels:
            - tag_name: app
              key: app.kubernetes.io/name
            - tag_name: version
              key: app.kubernetes.io/version

    exporters:
      otlp/tempo:
        endpoint: tempo-distributor.observability:4317
        tls:
          insecure: true

      prometheusremotewrite:
        endpoint: http://prometheus:9090/api/v1/write

      loki:
        endpoint: http://loki-gateway.observability:3100/loki/api/v1/push
        labels:
          resource:
            k8s.namespace.name: "namespace"
            k8s.pod.name: "pod"
            service.name: "service"

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch, resource, k8sattributes]
          exporters: [otlp/tempo]
        metrics:
          receivers: [otlp]
          processors: [batch, resource]
          exporters: [prometheusremotewrite]
        logs:
          receivers: [otlp]
          processors: [batch, resource]
          exporters: [loki]
```

### Ejemplo de instrumentación de aplicaciones

Aplicación Python Flask con OTEL:

```python
# app.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.b3 import B3MultiFormat
import logging
import json_log_formatter

# Configure trace propagation (both W3C and B3 for compatibility)
set_global_textmap(CompositePropagator([
    TraceContextTextMapPropagator(),
    B3MultiFormat()
]))

# Configure tracer
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Configure logging with trace correlation
class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = '0' * 32
            record.span_id = '0' * 16
        return True

# JSON formatter for structured logging
formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.addFilter(TraceIdFilter())

logger = logging.getLogger('app')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Flask application
from flask import Flask, request
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.route('/api/orders/<order_id>')
def get_order(order_id):
    logger.info('Processing order request', extra={
        'order_id': order_id,
        'method': request.method,
        'path': request.path
    })
    # Business logic here
    return {'order_id': order_id, 'status': 'completed'}
```

### Exemplars: de métricas a trazas

Los exemplars enlazan muestras de métricas de alta cardinalidad con trazas específicas:

```yaml
# Prometheus configuration to enable exemplars
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'app-metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['app:8080']
    # Enable exemplar storage
    enable_http2: true
```

Código de aplicación para emitir exemplars:

```go
// Go application with exemplars
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "go.opentelemetry.io/otel/trace"
)

var requestDuration = promauto.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request duration in seconds",
        Buckets: prometheus.DefBuckets,
    },
    []string{"method", "path", "status"},
)

func recordMetric(ctx context.Context, method, path string, status int, duration float64) {
    span := trace.SpanFromContext(ctx)
    if span.SpanContext().IsSampled() {
        requestDuration.WithLabelValues(method, path, strconv.Itoa(status)).(prometheus.ExemplarObserver).ObserveWithExemplar(
            duration,
            prometheus.Labels{
                "traceID": span.SpanContext().TraceID().String(),
                "spanID":  span.SpanContext().SpanID().String(),
            },
        )
    } else {
        requestDuration.WithLabelValues(method, path, strconv.Itoa(status)).Observe(duration)
    }
}
```

### Diagrama de arquitectura de correlación

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                     Application                              │
                    │  ┌──────────────────────────────────────────────────────┐   │
                    │  │  Request with TraceContext Header                     │   │
                    │  │  traceparent: 00-abc123...-def456...-01               │   │
                    │  └──────────────────────────────────────────────────────┘   │
                    │         │              │                │                    │
                    │         ▼              ▼                ▼                    │
                    │    ┌────────┐    ┌─────────┐     ┌────────────┐             │
                    │    │ Logs   │    │ Metrics │     │   Traces   │             │
                    │    │traceID │    │exemplar │     │  spans     │             │
                    │    └────┬───┘    └────┬────┘     └─────┬──────┘             │
                    └─────────┼─────────────┼───────────────┼─────────────────────┘
                              │             │               │
              ┌───────────────┼─────────────┼───────────────┼─────────────────────┐
              │ OTEL Collector│             │               │                      │
              │               ▼             ▼               ▼                      │
              │         ┌─────────────────────────────────────────┐               │
              │         │  Enrich with K8s metadata               │               │
              │         │  namespace, pod, node, service          │               │
              │         └─────────────────────────────────────────┘               │
              └───────────────┬─────────────┬───────────────┬─────────────────────┘
                              │             │               │
                    ┌─────────┼─────────────┼───────────────┼─────────────────────┐
                    │ Storage │             │               │                      │
                    │         ▼             ▼               ▼                      │
                    │    ┌────────┐    ┌─────────┐     ┌────────────┐             │
                    │    │  Loki  │    │Prometheus│    │   Tempo    │             │
                    │    │        │    │         │     │            │             │
                    │    └────┬───┘    └────┬────┘     └─────┬──────┘             │
                    └─────────┼─────────────┼───────────────┼─────────────────────┘
                              │             │               │
                    ┌─────────┼─────────────┼───────────────┼─────────────────────┐
                    │ Grafana │             │               │                      │
                    │         ▼             ▼               ▼                      │
                    │  ┌─────────────────────────────────────────────────────┐    │
                    │  │              Unified Query Interface                 │    │
                    │  │  Logs ──(traceID)──▶ Traces                         │    │
                    │  │  Metrics ──(exemplar)──▶ Traces                     │    │
                    │  │  Traces ──(labels)──▶ Logs                          │    │
                    │  └─────────────────────────────────────────────────────┘    │
                    └─────────────────────────────────────────────────────────────┘
```

### Flujo de trabajo de correlación

1. **La solicitud llega** con o sin contexto de traza
2. **La aplicación crea/continúa la traza** y registra logs con traceID
3. **Las métricas se registran** con un exemplar que contiene traceID
4. **OTEL Collector enriquece** todas las señales con metadatos de K8s
5. **Las consultas de Grafana** pueden navegar entre señales usando identificadores compartidos

---

## 2. Análisis LogQL de Loki

Loki proporciona un lenguaje de consulta potente (LogQL) para el análisis de logs. Esta sección cubre patrones prácticos para el análisis operativo de EKS.

### Cálculo de tasa de errores

Calcula tasas de errores a partir de flujos de logs:

```logql
# Error rate per service (last 5 minutes)
sum(rate({namespace="production"} |= "error" [5m])) by (app)
/ sum(rate({namespace="production"} [5m])) by (app)

# HTTP 5xx error rate from structured logs
sum(rate({namespace="production"} | json | status_code >= 500 [5m])) by (service)
/ sum(rate({namespace="production"} | json | status_code > 0 [5m])) by (service)

# Error rate with severity label
sum(rate({namespace="production", level="error"} [5m])) by (app)
```

### Extracción de latencia desde logs

Extrae métricas de latencia desde mensajes de log:

```logql
# Extract duration from JSON logs
{namespace="production", app="api-gateway"}
| json
| duration_ms > 1000
| line_format "{{.method}} {{.path}} took {{.duration_ms}}ms"

# Calculate latency percentiles from logs
quantile_over_time(0.99,
  {namespace="production"}
  | json
  | unwrap duration_ms [5m]
) by (service)

# Average latency per endpoint
avg_over_time(
  {namespace="production", app="api"}
  | json
  | unwrap response_time_ms [5m]
) by (path)
```

### Reglas de alerta basadas en logs

Crea alertas a partir de patrones de logs:

```yaml
# loki-alert-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: loki-alerts
  namespace: observability
spec:
  groups:
    - name: loki.alerts
      rules:
        # High error rate in logs
        - alert: HighLogErrorRate
          expr: |
            sum(rate({namespace="production"} |= "error" [5m])) by (app)
            / sum(rate({namespace="production"} [5m])) by (app)
            > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate in logs for {{ $labels.app }}"
            description: "Error rate is {{ $value | printf \"%.2f\" }}%"

        # Out of memory errors
        - alert: OutOfMemoryErrors
          expr: |
            sum(count_over_time({namespace="production"}
              |~ "OutOfMemoryError|OOMKilled|memory allocation failed" [15m]
            )) by (pod) > 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "OOM errors detected in {{ $labels.pod }}"

        # Database connection errors
        - alert: DatabaseConnectionErrors
          expr: |
            sum(rate({namespace="production"}
              |~ "connection refused|connection timed out|too many connections" [5m]
            )) by (app) > 1
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Database connection errors in {{ $labels.app }}"

        # Authentication failures
        - alert: HighAuthFailureRate
          expr: |
            sum(rate({namespace="production"}
              | json
              | event_type="authentication_failed" [5m]
            )) by (app) > 10
          for: 5m
          labels:
            severity: warning
            category: security
          annotations:
            summary: "High authentication failure rate in {{ $labels.app }}"
```

### Estrategia de labels y cardinalidad

Gestiona la cardinalidad de labels para evitar problemas de rendimiento:

```yaml
# promtail-config.yaml - Label extraction strategy
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Keep only essential labels
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      # Drop high-cardinality labels
      - action: labeldrop
        regex: __meta_kubernetes_pod_label_(pod-template-hash|controller-revision-hash)
    pipeline_stages:
      - json:
          expressions:
            level: level
            # Don't extract high-cardinality fields as labels
      - labels:
          level:
      # Keep request_id in log line, not as label
      - output:
          source: message
```

### Coincidencia de patrones y análisis sintáctico con LogQL

Patrones avanzados de análisis sintáctico:

```logql
# Parse unstructured Nginx logs
{app="nginx"}
| pattern `<ip> - - [<timestamp>] "<method> <path> <_>" <status> <bytes>`
| status >= 500

# Parse with regex
{app="api"}
| regexp `(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}) \[(?P<level>\w+)\] (?P<message>.*)`
| level = "ERROR"

# Parse JSON and filter
{namespace="production"}
| json
| line_format `{{.timestamp}} [{{.level}}] {{.message}}`
| level = "error"
| message =~ ".*timeout.*"

# Unpack nested JSON
{app="api-gateway"}
| json
| json request_body="request.body"
| request_body != ""
```

### Consultas de agregación

Agrega datos de logs para análisis:

```logql
# Count errors by service over time
sum by (service) (count_over_time({namespace="production", level="error"} [1h]))

# Top 10 error messages
topk(10, sum by (message) (count_over_time(
  {namespace="production"}
  | json
  | level = "error" [24h]
)))

# Log volume by namespace
sum by (namespace) (bytes_over_time({job="kubernetes-pods"} [1h]))

# Rate of specific events
sum(rate({namespace="production"} |= "payment_processed" [5m])) by (app)
```

### Manejo de logs multilínea

Configura el análisis de logs multilínea:

```yaml
# promtail-config.yaml - Multi-line configuration
scrape_configs:
  - job_name: java-apps
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
    pipeline_stages:
      # Java stack trace multi-line
      - multiline:
          firstline: '^\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
          max_lines: 128
      - regex:
          expression: '^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) (?P<level>\w+) .*'
      - labels:
          level:

  - job_name: python-apps
    kubernetes_sd_configs:
      - role: pod
    pipeline_stages:
      # Python traceback multi-line
      - multiline:
          firstline: '^\d{4}-\d{2}-\d{2}|^Traceback'
          max_wait_time: 3s
```

### YAML completo de reglas de alerta de Loki

```yaml
apiVersion: 1
groups:
  - name: loki-application-alerts
    rules:
      - alert: ApplicationErrorSpike
        expr: |
          sum(rate({namespace="production"} |= "error" [5m])) by (app)
          > 1.5 * sum(rate({namespace="production"} |= "error" [1h])) by (app)
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Error spike detected in {{ $labels.app }}"

      - alert: SlowRequestsDetected
        expr: |
          avg_over_time(
            {namespace="production"}
            | json
            | unwrap response_time_ms [5m]
          ) by (service) > 5000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow requests in {{ $labels.service }}"

      - alert: UnusualLogVolume
        expr: |
          sum(rate({namespace="production"} [5m])) by (app)
          > 3 * avg_over_time(sum(rate({namespace="production"} [5m])) by (app) [1d])
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Unusual log volume from {{ $labels.app }}"

      - alert: CriticalPatternDetected
        expr: |
          count_over_time({namespace="production"}
            |~ "FATAL|panic|segfault|core dumped" [5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Critical error pattern detected"

      - alert: PodCrashLoopDetected
        expr: |
          count_over_time({namespace="production"}
            |= "Back-off restarting failed container" [10m]) > 3
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Pod crash loop detected"
```

---

## 3. Patrones de PromQL de Prometheus

PromQL proporciona capacidades de consulta potentes para el análisis de métricas. Esta sección cubre patrones esenciales para operaciones de EKS.

### Cálculo de RPS

Calcula solicitudes por segundo:

```promql
# Total RPS across all services
sum(rate(http_requests_total[5m]))

# RPS by service
sum(rate(http_requests_total[5m])) by (service)

# RPS by endpoint (be careful with cardinality)
sum(rate(http_requests_total[5m])) by (service, path)

# RPS increase compared to yesterday
sum(rate(http_requests_total[5m]))
- sum(rate(http_requests_total[5m] offset 1d))
```

### Tasa de errores (método RED)

Rate, Errors, Duration: el método RED:

```promql
# Error rate (errors / total requests)
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
/ sum(rate(http_requests_total[5m])) by (service)

# Error rate with threshold
(
  sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
  / sum(rate(http_requests_total[5m])) by (service)
) > 0.01

# Client error rate (4xx)
sum(rate(http_requests_total{status=~"4.."}[5m])) by (service)
/ sum(rate(http_requests_total[5m])) by (service)

# Success rate (inverse of error rate)
1 - (
  sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
  / sum(rate(http_requests_total[5m])) by (service)
)
```

### Percentiles de latencia

Calcula percentiles de latencia a partir de histogramas:

```promql
# P50 latency
histogram_quantile(0.50,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
)

# Apdex score (target: 500ms, tolerated: 2s)
(
  sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m])) by (service)
  + sum(rate(http_request_duration_seconds_bucket{le="2"}[5m])) by (service)
) / 2
/ sum(rate(http_request_duration_seconds_count[5m])) by (service)
```

### Métricas de Istio Service Mesh

Consulta la telemetría de Istio:

```promql
# Request rate by source and destination
sum(rate(istio_requests_total[5m])) by (source_workload, destination_workload)

# Service error rate
sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service)
/ sum(rate(istio_requests_total[5m])) by (destination_service)

# P99 latency by service
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le, destination_service)
)

# TCP connections
sum(istio_tcp_connections_opened_total) by (source_workload, destination_workload)
- sum(istio_tcp_connections_closed_total) by (source_workload, destination_workload)

# Request size
histogram_quantile(0.99,
  sum(rate(istio_request_bytes_bucket[5m])) by (le, destination_service)
)
```

### Métricas de ALB mediante CloudWatch

Consulta métricas de ALB exportadas desde CloudWatch:

```promql
# ALB request count
sum(rate(aws_applicationelb_request_count_sum[5m])) by (load_balancer)

# ALB target response time
aws_applicationelb_target_response_time_average

# ALB 5xx errors
sum(rate(aws_applicationelb_httpcode_elb_5xx_count_sum[5m])) by (load_balancer)

# ALB healthy host count
aws_applicationelb_healthy_host_count_average

# ALB active connection count
aws_applicationelb_active_connection_count_sum
```

### Patrones de Amazon Managed Prometheus (AMP)

Consultas optimizadas para AMP:

```promql
# Use recording rules to reduce query complexity
# AMP has query limits, so pre-aggregate where possible

# Efficient aggregation
sum by (namespace) (
  rate(container_cpu_usage_seconds_total[5m])
)

# Avoid high-cardinality queries
# Bad: sum(rate(http_requests_total[5m])) by (pod, path, method, status)
# Good: sum(rate(http_requests_total[5m])) by (service, status_class)

# Use label_replace to reduce cardinality
sum by (service, status_class) (
  label_replace(
    rate(http_requests_total[5m]),
    "status_class", "${1}xx", "status", "([0-9]).*"
  )
)
```

### Reglas de recording

Precalcula consultas costosas:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
    - name: http.recording.rules
      interval: 30s
      rules:
        # Request rate by service
        - record: service:http_requests:rate5m
          expr: sum(rate(http_requests_total[5m])) by (service)

        # Error rate by service
        - record: service:http_errors:rate5m
          expr: sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)

        # Error ratio by service
        - record: service:http_error_ratio:rate5m
          expr: |
            service:http_errors:rate5m
            / service:http_requests:rate5m

        # P50 latency by service
        - record: service:http_latency_p50:rate5m
          expr: |
            histogram_quantile(0.50,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
            )

        # P95 latency by service
        - record: service:http_latency_p95:rate5m
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
            )

        # P99 latency by service
        - record: service:http_latency_p99:rate5m
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
            )

    - name: kubernetes.recording.rules
      interval: 30s
      rules:
        # Node CPU utilization
        - record: node:cpu_utilization:rate5m
          expr: |
            100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

        # Node memory utilization
        - record: node:memory_utilization:ratio
          expr: |
            1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

        # Pod CPU usage by namespace
        - record: namespace:pod_cpu:rate5m
          expr: |
            sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (namespace)

        # Pod memory usage by namespace
        - record: namespace:pod_memory:bytes
          expr: |
            sum(container_memory_working_set_bytes{container!=""}) by (namespace)

    - name: istio.recording.rules
      interval: 30s
      rules:
        # Service request rate
        - record: service:istio_requests:rate5m
          expr: |
            sum(rate(istio_requests_total[5m])) by (destination_service)

        # Service error rate
        - record: service:istio_errors:rate5m
          expr: |
            sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service)

        # Service P99 latency
        - record: service:istio_latency_p99:rate5m
          expr: |
            histogram_quantile(0.99,
              sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le, destination_service)
            )
```

---

## 4. Análisis TraceQL de Tempo

TraceQL de Tempo proporciona una sintaxis similar a SQL para buscar y analizar trazas distribuidas.

### Sintaxis básica de TraceQL

```traceql
# Find all traces for a service
{ resource.service.name = "api-gateway" }

# Filter by span name
{ name = "HTTP GET" }

# Filter by attribute
{ span.http.status_code >= 500 }

# Combine filters
{ resource.service.name = "order-service" && span.http.status_code = 500 }

# Duration filter
{ resource.service.name = "payment-service" && duration > 1s }

# Find traces with specific error
{ status = error && span.error.message =~ ".*timeout.*" }
```

### Análisis de latencia

Encuentra y analiza trazas lentas:

```traceql
# Traces slower than 5 seconds
{ duration > 5s }

# Slow database queries
{ span.db.system = "postgresql" && duration > 500ms }

# Slow HTTP calls
{ span.http.method = "POST" && duration > 2s }

# Find the slowest spans in a trace
{ duration > 1s } | select(duration, name, resource.service.name)

# P99 latency traces
{ resource.service.name = "checkout" && duration > 2s } | quantile_over_time(duration, 0.99)
```

### Búsqueda de trazas con errores

Encuentra y analiza trazas con errores:

```traceql
# All error traces
{ status = error }

# Errors by service
{ resource.service.name = "inventory-service" && status = error }

# Specific error types
{ span.exception.type = "java.lang.NullPointerException" }

# HTTP errors
{ span.http.status_code >= 500 }

# gRPC errors
{ span.rpc.grpc.status_code != 0 }

# Database errors
{ span.db.system = "mysql" && status = error }
```

### Mapeo de dependencias de servicios

Analiza dependencias de servicios:

```traceql
# Find all downstream calls from a service
{ resource.service.name = "api-gateway" && kind = client }

# Find all upstream callers of a service
{ resource.service.name = "user-service" && kind = server }

# Cross-service calls
{
  resource.service.name = "order-service"
  && span.peer.service = "payment-service"
}

# External dependency calls
{ span.http.url =~ ".*external-api.com.*" }
```

### Filtrado de atributos de span

Filtra por diversos atributos de span:

```traceql
# Kubernetes metadata
{ resource.k8s.namespace.name = "production" }
{ resource.k8s.pod.name =~ "api-.*" }
{ resource.k8s.node.name = "ip-10-0-1-100.ec2.internal" }

# HTTP attributes
{ span.http.method = "POST" && span.http.route = "/api/orders" }
{ span.http.request_content_length > 1000000 }

# Database attributes
{ span.db.statement =~ ".*SELECT.*users.*" }
{ span.db.operation = "INSERT" }

# Custom attributes
{ span.user.id = "user-123" }
{ span.order.total > 1000 }
```

### Consultas estructurales (padre-hijo)

Consulta la estructura de trazas:

```traceql
# Find child spans of a specific parent
{ name = "HTTP POST /checkout" } >> { span.db.system = "postgresql" }

# Find parent of slow database queries
{ span.db.system = "postgresql" && duration > 1s } << { }

# Multi-level ancestry
{ name = "api-gateway" } >> { name = "order-service" } >> { span.db.system = "postgresql" }

# Sibling spans (same parent)
{ name = "inventory-check" } ~ { name = "payment-process" }

# Find traces where DB query is child of HTTP call
{ span.http.method = "GET" } >> { span.db.operation = "SELECT" && duration > 500ms }
```

### Comparación de trazas

Compara trazas entre momentos o versiones:

```traceql
# Compare latency between deployments (using resource attributes)
{ resource.service.version = "v2.0.0" && duration > 1s }
{ resource.service.version = "v1.9.0" && duration > 1s }

# Find anomalous traces (compare to baseline)
{
  resource.service.name = "checkout"
  && duration > 2s
  && span.http.route = "/api/checkout"
}

# Traces by environment
{ resource.deployment.environment = "canary" && status = error }
```

### Consultas de grafo de servicios

Analiza la topología de servicios:

```traceql
# Service graph metrics (via Tempo metrics generator)
# These generate Prometheus metrics from trace data

# Request rate between services
traces_service_graph_request_total

# Error rate between services
traces_service_graph_request_failed_total

# Latency between services
traces_service_graph_request_server_seconds_bucket
```

Configuración de Tempo Metrics Generator:

```yaml
# tempo-config.yaml
metrics_generator:
  registry:
    external_labels:
      source: tempo
      cluster: production
  storage:
    path: /var/tempo/generator/wal
    remote_write:
      - url: http://prometheus:9090/api/v1/write
        send_exemplars: true
  traces_storage:
    path: /var/tempo/generator/traces
  processor:
    service_graphs:
      dimensions:
        - k8s.namespace.name
        - k8s.deployment.name
      histogram_buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5]
      max_items: 10000
      wait: 10s
      workers: 10
    span_metrics:
      dimensions:
        - service.name
        - span.name
        - http.method
        - http.status_code
      histogram_buckets: [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.512, 1.024]
```

---

## 5. Dashboards de Grafana

Los dashboards de Grafana reúnen métricas, logs y trazas para una observabilidad unificada.

### Paneles de los métodos RED/USE

**Dashboard del método RED (centrado en solicitudes)**

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total[5m])) by (service)",
          "legendFormat": "{{ service }}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service)",
          "legendFormat": "{{ service }}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "thresholds": {
            "steps": [
              {"value": 0, "color": "green"},
              {"value": 0.01, "color": "yellow"},
              {"value": 0.05, "color": "red"}
            ]
          }
        }
      }
    },
    {
      "title": "Latency (P95)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))",
          "legendFormat": "{{ service }}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        }
      }
    }
  ]
}
```

**Dashboard del método USE (centrado en recursos)**

```json
{
  "panels": [
    {
      "title": "CPU Utilization",
      "type": "gauge",
      "targets": [
        {
          "expr": "100 - (avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
          "legendFormat": "CPU %"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent",
          "max": 100,
          "thresholds": {
            "steps": [
              {"value": 0, "color": "green"},
              {"value": 70, "color": "yellow"},
              {"value": 85, "color": "red"}
            ]
          }
        }
      }
    },
    {
      "title": "Memory Saturation",
      "type": "timeseries",
      "targets": [
        {
          "expr": "1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)",
          "legendFormat": "{{ instance }}"
        }
      ]
    },
    {
      "title": "Disk I/O Errors",
      "type": "stat",
      "targets": [
        {
          "expr": "rate(node_disk_io_time_seconds_total{device!~\"dm-.*\"}[5m])",
          "legendFormat": "{{ device }}"
        }
      ]
    }
  ]
}
```

### Enlaces entre datasources

**Prometheus a Tempo mediante exemplars**

```yaml
# Grafana datasource configuration
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    jsonData:
      exemplarTraceIdDestinations:
        - name: traceID
          datasourceUid: tempo
          urlDisplayLabel: "View Trace"
      httpMethod: POST
```

**Loki a Tempo mediante campos derivados**

```yaml
# Grafana datasource configuration
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"traceId":"([a-f0-9]+)"'
          url: '$${__value.raw}'
          datasourceUid: tempo
          urlDisplayLabel: "View Trace"
        - name: TraceID-W3C
          matcherRegex: 'traceparent.*-([a-f0-9]{32})-'
          url: '$${__value.raw}'
          datasourceUid: tempo
```

### Provisioning de dashboards

```yaml
# grafana-dashboards-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: observability
  labels:
    grafana_dashboard: "1"
data:
  eks-overview.json: |
    {
      "dashboard": {
        "title": "EKS Cluster Overview",
        "uid": "eks-overview",
        "tags": ["eks", "kubernetes"],
        "timezone": "browser",
        "refresh": "30s",
        "templating": {
          "list": [
            {
              "name": "namespace",
              "type": "query",
              "datasource": "Prometheus",
              "query": "label_values(kube_namespace_labels, namespace)",
              "refresh": 2,
              "multi": true,
              "includeAll": true
            },
            {
              "name": "service",
              "type": "query",
              "datasource": "Prometheus",
              "query": "label_values(kube_service_info{namespace=~\"$namespace\"}, service)",
              "refresh": 2,
              "multi": true,
              "includeAll": true
            }
          ]
        },
        "panels": []
      }
    }
```

### Plantillas de variables

```json
{
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus"
      },
      {
        "name": "cluster",
        "type": "query",
        "datasource": "${datasource}",
        "query": "label_values(up, cluster)",
        "refresh": 2
      },
      {
        "name": "namespace",
        "type": "query",
        "datasource": "${datasource}",
        "query": "label_values(kube_pod_info{cluster=\"$cluster\"}, namespace)",
        "refresh": 2,
        "multi": true,
        "includeAll": true
      },
      {
        "name": "workload",
        "type": "query",
        "datasource": "${datasource}",
        "query": "label_values(kube_deployment_labels{cluster=\"$cluster\", namespace=~\"$namespace\"}, deployment)",
        "refresh": 2,
        "multi": true
      },
      {
        "name": "interval",
        "type": "interval",
        "query": "1m,5m,15m,30m,1h,6h,12h,1d",
        "current": {
          "value": "5m"
        }
      }
    ]
  }
}
```

### Ejemplo de modelo JSON de dashboard

Panel completo con enlaces entre datasources:

```json
{
  "title": "Service Latency with Traces",
  "type": "timeseries",
  "datasource": "Prometheus",
  "targets": [
    {
      "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{namespace=\"$namespace\", service=\"$service\"}[$interval])) by (le))",
      "legendFormat": "P99 Latency",
      "exemplar": true
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "s",
      "links": [
        {
          "title": "View slow traces",
          "url": "/explore?orgId=1&left=%7B%22datasource%22:%22Tempo%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22query%22:%22%7Bresource.service.name%3D%5C%22${service}%5C%22%20%26%26%20duration%20%3E%201s%7D%22%7D%5D%7D",
          "targetBlank": true
        },
        {
          "title": "View logs",
          "url": "/explore?orgId=1&left=%7B%22datasource%22:%22Loki%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22expr%22:%22%7Bnamespace%3D%5C%22${namespace}%5C%22,%20app%3D%5C%22${service}%5C%22%7D%22%7D%5D%7D",
          "targetBlank": true
        }
      ]
    }
  },
  "options": {
    "tooltip": {
      "mode": "single"
    },
    "legend": {
      "displayMode": "list",
      "placement": "bottom"
    }
  }
}
```

---

## Recursos relacionados

- [Optimización de observabilidad](../observability/09-observability-optimization.md) - Ajuste de rendimiento para el stack de observabilidad
- [Stack de logging](../observability/logging/README.md) - Despliegue y configuración de Loki
- [Configuración de alertas operativas](./07-observability-alerts.md) - Reglas de alerta y configuración de Alertmanager

---

< [Anterior: Configuración de alertas operativas](./07-observability-alerts.md) | [Tabla de contenidos](./README.md) | [Siguiente: Operaciones del stack de observabilidad](./09-observability-stack.md) >
