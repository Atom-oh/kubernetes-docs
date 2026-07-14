# Métricas de Istio

> **Versiones compatibles**: Istio 1.28
> **Última actualización**: February 19, 2026

Istio recopila automáticamente métricas de todo el tráfico en el service mesh y se integra con diversos backends como Prometheus y OpenTelemetry para proporcionar una observabilidad integral.

## Tabla de contenido

1. [Descripción general de métricas](#metrics-overview)
2. [Métricas estándar de Istio](#istio-standard-metrics)
3. [Métricas de Circuit Breaker](#circuit-breaker-metrics)
4. [Métricas de resiliencia](#resilience-metrics)
5. [Integración con OpenTelemetry](#opentelemetry-integration)
6. [Integración con Prometheus](#prometheus-integration)
7. [Personalización con Telemetry API](#customization-with-telemetry-api)
8. [Consultas de métricas prácticas](#practical-metric-queries)
9. [Optimización de métricas](#metrics-optimization)
10. [Solución de problemas](#troubleshooting)

## Descripción general de métricas

### Señales doradas

Istio recopila automáticamente las señales doradas según los principios de SRE de Google:

1. **Latencia**: Tiempo de procesamiento de solicitudes
2. **Tráfico**: Rendimiento del sistema (RPS, ancho de banda)
3. **Errores**: Tasa de fallos y tipos de errores
4. **Saturación**: Utilización de recursos

### Arquitectura de recopilación de métricas

```mermaid
flowchart TD
    subgraph "Application Pods"
        App1[App Container]
        Envoy1[Envoy Sidecar]
        App1 -.-> Envoy1
    end

    subgraph "Istio Control Plane"
        Istiod[istiod]
        Telemetry[Telemetry Config]
    end

    subgraph "Metrics Backend"
        Prometheus[Prometheus]
        OTEL[OpenTelemetry<br/>Collector]
    end

    subgraph "Visualization"
        Grafana[Grafana]
        Kiali[Kiali]
    end

    Envoy1 -->|Scrape /stats/prometheus| Prometheus
    Envoy1 -->|Push Metrics| OTEL
    Istiod -->|Configure| Envoy1
    Telemetry -.->|Applied by| Istiod

    Prometheus --> Grafana
    Prometheus --> Kiali
    OTEL --> Prometheus

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef istioComponent fill:#466BB0,stroke:#333,stroke-width:1px,color:white;
    classDef monitoring fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef visualization fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    class App1 k8sComponent;
    class Envoy1,Istiod,Telemetry istioComponent;
    class Prometheus,OTEL monitoring;
    class Grafana,Kiali visualization;
```

## Métricas estándar de Istio

### Métricas HTTP/gRPC

Istio genera las siguientes métricas para todo el tráfico HTTP/gRPC:

#### istio_requests_total

**Tipo**: Contador
**Descripción**: Número total de solicitudes procesadas

```promql
istio_requests_total{
  reporter="source",  # or "destination"
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

**Etiquetas clave**:
- `response_code`: Código de estado HTTP (200, 404, 500, etc.)
- `response_flags`: Indicadores de respuesta de Envoy
  - `UH`: Fallo de conexión upstream
  - `UF`: Fallo de conexión upstream
  - `UR`: Tiempo de espera agotado de la solicitud upstream
  - `DC`: Terminación de conexión downstream
  - `LR`: Restablecimiento local
  - `URX`: Rechazada por Circuit Breaker
- `connection_security_policy`: Estado de mTLS (`mutual_tls`, `none`)

#### istio_request_duration_milliseconds

**Tipo**: Histograma
**Descripción**: Tiempo de procesamiento de solicitudes (milisegundos)

```promql
istio_request_duration_milliseconds_bucket{le="10"}  # 10ms or less
istio_request_duration_milliseconds_bucket{le="50"}  # 50ms or less
istio_request_duration_milliseconds_bucket{le="100"} # 100ms or less
istio_request_duration_milliseconds_bucket{le="500"} # 500ms or less
istio_request_duration_milliseconds_sum            # Total time
istio_request_duration_milliseconds_count          # Total request count
```

#### istio_request_bytes

**Tipo**: Histograma
**Descripción**: Tamaño del cuerpo de la solicitud (bytes)

```promql
istio_request_bytes_bucket{le="1024"}   # 1KB or less
istio_request_bytes_bucket{le="10240"}  # 10KB or less
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**Tipo**: Histograma
**Descripción**: Tamaño del cuerpo de la respuesta (bytes)

```promql
istio_response_bytes_bucket{le="1024"}
istio_response_bytes_bucket{le="10240"}
istio_response_bytes_sum
istio_response_bytes_count
```

### Métricas TCP

#### istio_tcp_connections_opened_total

**Tipo**: Contador
**Descripción**: Número de conexiones TCP abiertas

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**Tipo**: Contador
**Descripción**: Número de conexiones TCP cerradas

#### istio_tcp_sent_bytes_total

**Tipo**: Contador
**Descripción**: Número de bytes enviados

#### istio_tcp_received_bytes_total

**Tipo**: Contador
**Descripción**: Número de bytes recibidos

## Métricas de Circuit Breaker

Métricas clave para supervisar el comportamiento de Circuit Breaker y Outlier Detection.

### Métricas clave de Circuit Breaker

#### 1. Desbordamiento del pool de conexiones upstream

```promql
# Requests rejected due to connection pool overflow
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**Significado**: Se superó el límite de `maxConnections`

#### 2. Circuit Breaker abierto (solicitud upstream rechazada)

```promql
# Requests rejected by circuit breaker
envoy_cluster_circuit_breakers_default_rq_open{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 3. Desbordamiento de solicitudes pendientes

```promql
# Pending request count exceeded
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**Significado**: Se superó `http1MaxPendingRequests` o `http2MaxRequests`

#### 4. Presupuesto de reintentos agotado

```promql
# Retry budget exhausted
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. Detección de Circuit Breaker mediante indicadores de respuesta

```promql
# Requests rejected by circuit breaker (response_flags="UO")
sum(rate(istio_requests_total{
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**Detalles de los indicadores de respuesta**:
- `UO`: Desbordamiento upstream (Circuit Breaker abierto)
- `URX`: Rechazada por Circuit Breaker
- `UF`: Fallo de conexión upstream
- `UH`: No hay upstream en buen estado

### Consultas del dashboard de supervisión de Circuit Breaker

```promql
# 1. Circuit breaker trigger rate
sum(rate(envoy_cluster_circuit_breakers_default_rq_open[5m])) by (cluster_name)
/
sum(rate(envoy_cluster_upstream_rq_total[5m])) by (cluster_name)
* 100

# 2. Connection pool utilization
envoy_cluster_upstream_cx_active{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
/
envoy_cluster_circuit_breakers_default_cx_max{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
* 100

# 3. Pending request utilization
envoy_cluster_upstream_rq_pending_active{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
/
envoy_cluster_circuit_breakers_default_rq_pending_max{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
* 100

# 4. Requests rejected by circuit breaker
sum(increase(envoy_cluster_upstream_rq_pending_overflow[5m])) by (cluster_name)
```

### Reglas de alerta de Circuit Breaker

```yaml
groups:
- name: istio_circuit_breaker
  interval: 30s
  rules:
  - alert: CircuitBreakerOpen
    expr: |
      rate(envoy_cluster_circuit_breakers_default_rq_open[1m]) > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Circuit breaker opened for {{ $labels.cluster_name }}"
      description: "Circuit breaker has opened for cluster {{ $labels.cluster_name }}"

  - alert: HighConnectionPoolUsage
    expr: |
      (envoy_cluster_upstream_cx_active
      /
      envoy_cluster_circuit_breakers_default_cx_max) > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High connection pool usage for {{ $labels.cluster_name }}"
      description: "Connection pool usage is above 80% for {{ $labels.cluster_name }}"

  - alert: PendingRequestsOverflow
    expr: |
      rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Pending requests overflow for {{ $labels.cluster_name }}"
      description: "Requests are being rejected due to pending queue overflow"
```

## Métricas de resiliencia

### Métricas de Outlier Detection

#### 1. Hosts expulsados

```promql
# Number of hosts ejected by outlier detection
envoy_cluster_outlier_detection_ejections_active{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 2. Eventos de expulsión

```promql
# Ejection event rate
rate(envoy_cluster_outlier_detection_ejections_total[5m])
```

**Por tipo de expulsión**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_failure_percentage
```

### Métricas de reintentos

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

### Métricas de tiempo de espera agotado

```promql
# Requests that timed out
sum(rate(istio_requests_total{
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# Timeout rate
sum(rate(istio_requests_total{response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total[5m]))
* 100
```

## Integración con OpenTelemetry

### Configuración de OpenTelemetry Collector

Istio puede exportar métricas mediante el protocolo OpenTelemetry.

#### 1. Configuración de MeshConfig

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
  namespace: istio-system
data:
  mesh: |
    defaultConfig:
      tracing: {} # Tracing configuration
    extensionProviders:
    - name: otel
      opentelemetry:
        service: opentelemetry-collector.observability.svc.cluster.local
        port: 4317
    - name: otel-tracing
      opentelemetry:
        service: opentelemetry-collector.observability.svc.cluster.local
        port: 4317
        resource_detectors:
          environment: {}
```

#### 2. Habilitar OpenTelemetry con Telemetry API

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: otel-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: otel
    overrides:
    - match:
        metric: ALL_METRICS
      mode: CLIENT_AND_SERVER
```

#### 3. Implementar OpenTelemetry Collector

```yaml
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

    processors:
      batch:
        timeout: 10s
        send_batch_size: 1024

      memory_limiter:
        check_interval: 1s
        limit_mib: 512

      # Add additional attributes to Istio metrics
      attributes:
        actions:
        - key: cluster.name
          value: production
          action: insert

    exporters:
      prometheus:
        endpoint: "0.0.0.0:8889"
        namespace: istio
        const_labels:
          environment: production

      otlp:
        endpoint: tempo:4317
        tls:
          insecure: true

      logging:
        loglevel: debug

    service:
      pipelines:
        metrics:
          receivers: [otlp]
          processors: [memory_limiter, batch, attributes]
          exporters: [prometheus, logging]
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [otlp, logging]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.96.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 4317  # OTLP gRPC
          name: otlp-grpc
        - containerPort: 4318  # OTLP HTTP
          name: otlp-http
        - containerPort: 8889  # Prometheus metrics
          name: prometheus
        volumeMounts:
        - name: config
          mountPath: /etc/otel
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: opentelemetry-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: 4317
  - name: otlp-http
    port: 4318
    targetPort: 4318
  - name: prometheus
    port: 8889
    targetPort: 8889
```

#### 4. Configuración de Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-collector
  endpoints:
  - port: prometheus
    interval: 15s
    path: /metrics
```

### Verificación de métricas de OpenTelemetry

```bash
# 1. Check OpenTelemetry Collector logs
kubectl logs -n observability deployment/otel-collector

# 2. Check Collector metrics
kubectl port-forward -n observability svc/opentelemetry-collector 8889:8889
curl http://localhost:8889/metrics

# 3. Verify Envoy is sending metrics
istioctl proxy-config log deploy/productpage-v1 --level debug
kubectl logs -n default deploy/productpage-v1 -c istio-proxy | grep -i otel
```

## Integración con Prometheus

### Configuración de Prometheus

#### 1. Prometheus ConfigMap

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
    # Istio mesh metrics
    - job_name: 'istio-mesh'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: istio-telemetry;prometheus

    # Envoy sidecar metrics
    - job_name: 'envoy-stats'
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_container_port_name]
        action: keep
        regex: '.*-envoy-prom'
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:15020
        target_label: __address__
      - action: labeldrop
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: pod_name

    # Istiod metrics
    - job_name: 'istiod'
      kubernetes_sd_configs:
      - role: endpoints
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels: [__meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: istiod;http-monitoring

    # Istio gateways
    - job_name: 'istio-gateway'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_istio]
        action: keep
        regex: ingressgateway|egressgateway
      - source_labels: [__address__]
        action: replace
        regex: ([^:]+)(?::\d+)?
        replacement: $1:15020
        target_label: __address__
```

#### 2. Auto-scraping con ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-component-monitor
  namespace: istio-system
  labels:
    monitoring: istio-components
spec:
  selector:
    matchExpressions:
    - key: istio
      operator: In
      values:
      - pilot
  endpoints:
  - port: http-monitoring
    interval: 15s
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: envoy-stats-monitor
  namespace: istio-system
  labels:
    monitoring: istio-proxies
spec:
  selector:
    matchExpressions:
    - key: istio-prometheus-ignore
      operator: DoesNotExist
  podMetricsEndpoints:
  - path: /stats/prometheus
    interval: 15s
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_container_port_name]
      action: keep
      regex: '.*-envoy-prom'
```

### Optimización de consultas de Prometheus

```promql
# Recording Rules to pre-compute frequently used queries
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # Request rate by service
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total[5m])) by (destination_service_name, destination_service_namespace)

  # Error rate by service
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service_name)
      /
      sum(rate(istio_requests_total[5m])) by (destination_service_name)

  # P95 latency by service
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m]))
        by (destination_service_name, le)
      )

  # Circuit breaker trigger rate
  - record: istio:circuit_breaker:open_rate:1m
    expr: |
      rate(envoy_cluster_circuit_breakers_default_rq_open[1m])
```

## Personalización con Telemetry API

### Personalización de métricas

#### 1. Habilitar solo métricas específicas

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: custom-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    # Enable only request metrics
    - match:
        metric: REQUEST_COUNT
      mode: CLIENT_AND_SERVER
    - match:
        metric: REQUEST_DURATION
      mode: CLIENT_AND_SERVER
    # Disable TCP metrics
    - match:
        metric: TCP_OPENED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_CLOSED_CONNECTIONS
      disabled: true
```

#### 2. Agregar etiquetas personalizadas

```yaml
apiVersion: telemetry.istio.io/v1alpha1
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
        metric: ALL_METRICS
      tagOverrides:
        # Add request headers as labels
        request_id:
          value: "request.headers['x-request-id']"
        user_agent:
          value: "request.headers['user-agent']"
        # Add response headers as labels
        upstream_cluster:
          value: "response.headers['x-envoy-upstream-service-time']"
        # Custom attributes
        api_version:
          value: "request.path | split('/')[2]"
```

#### 3. Configuración de métricas específica de Namespace

```yaml
apiVersion: telemetry.istio.io/v1alpha1
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
          value: "production"
```

#### 4. Mejorar el rendimiento deshabilitando métricas

```yaml
apiVersion: telemetry.istio.io/v1alpha1
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

## Consultas de métricas prácticas

### Dashboard de señales doradas

#### 1. Latencia

```promql
# P50 latency
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# Average latency by service
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name)
```

#### 2. Tráfico

```promql
# Request rate by service (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name)

# Total request rate
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# Inbound traffic by service (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name)

# Outbound traffic by service (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name)

# Request distribution by HTTP method
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name)
```

#### 3. Errores

```promql
# Error rate (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name)
* 100

# Separate 4xx vs 5xx
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)

# Track specific error codes
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name)

# Analyze error types via response flags
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name)
```

#### 4. Saturación

```promql
# Connection pool utilization
(envoy_cluster_upstream_cx_active / envoy_cluster_circuit_breakers_default_cx_max) * 100

# Active request count
envoy_cluster_upstream_rq_active

# Pending request count
envoy_cluster_upstream_rq_pending_active

# Envoy memory usage
envoy_server_memory_allocated / envoy_server_memory_heap_size * 100
```

### Supervisión de mTLS

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

# mTLS authentication failures
sum(rate(istio_requests_total{
  response_code="401",
  connection_security_policy="mutual_tls"
}[5m])) by (destination_service_name)
```

### Dashboard de estado del service mesh

```promql
# 1. Control plane status
up{job="istiod"}

# 2. Pilot push errors
rate(pilot_xds_push_errors[5m])

# 3. Envoy configuration update delays
rate(pilot_xds_pushes[5m])

# 4. Envoy proxy version distribution
count(envoy_server_version) by (envoy_server_version)

# 5. Detect stale proxies (older than 24 hours)
(time() - envoy_server_uptime) > 86400
```

## Optimización de métricas

### Resolver problemas de alta cardinalidad

#### 1. Eliminar etiquetas innecesarias

```yaml
apiVersion: telemetry.istio.io/v1alpha1
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

#### 2. Normalizar valores de etiquetas

```yaml
apiVersion: telemetry.istio.io/v1alpha1
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
        request_protocol:
          value: |
            request.protocol == "http" ?
              (request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER")
              : request.protocol
```

### Muestreo de métricas

Reduzca el uso de memoria y CPU con el muestreo de estadísticas de Envoy:

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
```

### Ajuste de rendimiento de Prometheus

```yaml
global:
  scrape_interval: 30s  # Default: 15s
  evaluation_interval: 30s

# Separate long-term storage with remote write
remote_write:
- url: http://victoria-metrics:8428/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 5
    min_shards: 1
    max_samples_per_send: 5000

# Remove unnecessary labels with metric relabeling
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'istio_tcp_.*'
  action: drop  # Remove TCP metrics
```

## Solución de problemas

### Cuando no se recopilan métricas

#### 1. Comprobar el endpoint de métricas de Envoy

```bash
# Check Envoy admin port
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# Check metrics filter
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. Comprobar si Prometheus detectó targets

```bash
# Check Targets page in Prometheus UI
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# In browser: http://localhost:9090/targets
```

#### 3. Validar la configuración de Telemetry API

```bash
# Check Telemetry resources
kubectl get telemetry -A

# Check specific Telemetry details
kubectl describe telemetry <name> -n <namespace>

# Check if reflected in Envoy config
istioctl proxy-config log <pod-name> -o json | jq '.stats'
```

### Cuando faltan etiquetas de métricas

```bash
# 1. Check if Envoy generates correct labels
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Check Prometheus relabeling rules
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. Check ServiceMonitor/PodMonitor
kubectl get servicemonitor,podmonitor -n istio-system
```

### Explosión de cardinalidad de métricas

```bash
# 1. Check metric cardinality
kubectl exec -it -n istio-system <prometheus-pod> -- sh -c \
  'wget -O- "http://localhost:9090/api/v1/label/__name__/values" 2>/dev/null' | \
  jq '.data | length'

# 2. Check time series count for specific metrics
curl http://localhost:9090/api/v1/query?query='count(istio_requests_total)%20by%20(__name__)'

# 3. Check cardinality by label
count by (__name__, le) (istio_request_duration_milliseconds_bucket)
```

### Cuando las métricas de Circuit Breaker no son visibles

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

## Referencias

- [Métricas de Istio](https://istio.io/latest/docs/reference/config/metrics/)
- [Observabilidad de Istio](https://istio.io/latest/docs/tasks/observability/)
- [Ejemplos de consultas de Prometheus](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Estadísticas de Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Dashboards de Istio de Grafana](https://grafana.com/grafana/dashboards/?search=istio)
