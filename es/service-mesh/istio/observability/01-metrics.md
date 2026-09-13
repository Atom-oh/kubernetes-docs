# Métricas de Istio

> **Versiones compatibles**: Istio 1.31
> **Última actualización**: 11 de septiembre de 2026

> **Alcance de validación**: Configuraciones de laboratorio comprobadas con referencias oficiales y validadores offline, sin desplegar clúster. Cada ejemplo declara supuestos de namespace, identidad, almacenamiento, backend y carga que deben verificarse en el destino.

Los proxies Istio generan métricas del tráfico observado. La guía cubre HTTP/TCP sidecar/Envoy y scraping con Prometheus u OpenTelemetry Collector. ztunnel ambient tiene otras métricas L4; HTTP requiere waypoint.

## Índice

1. [Descripción de métricas](#metrics-overview)
2. [Métricas estándar Istio](#istio-standard-metrics)
3. [Métricas de circuit breaker](#circuit-breaker-metrics)
4. [Métricas de resiliencia](#resilience-metrics)
5. [Integración OpenTelemetry](#opentelemetry-integration)
6. [Integración Prometheus](#prometheus-integration)
7. [Personalización con Telemetry API](#customization-with-telemetry-api)
8. [Consultas prácticas](#practical-metric-queries)
9. [Optimización](#metrics-optimization)
10. [Resolución de problemas](#troubleshooting)

## Descripción de métricas {#metrics-overview}

### Señales doradas

Combine telemetría de proxy con exporters de nodo/contenedor:

1. **Latencia**: Tiempo de procesamiento
2. **Tráfico**: Rendimiento del sistema, RPS y ancho de banda
3. **Errores**: Tasa y tipos de fallo
4. **Saturación**: Presión de colas/conexiones más CPU/memoria de exporters Kubernetes

### Arquitectura de recogida

Envoy expone métricas Prometheus → Prometheus las recoge directamente o lo hace el receptor Prometheus de OpenTelemetry Collector → backend configurado → Grafana/Kiali. El proveedor de extensión OpenTelemetry Istio configura trazas; no envía métricas OTLP.

## Métricas estándar Istio {#istio-standard-metrics}

### Métricas HTTP/gRPC

Envoy genera estas métricas para tráfico reconocido. Cada proxy reporter emite métricas; elija uno para cada pregunta. Destination evita duplicar observaciones del salto, mientras source permite ver fallos upstream que nunca llegan. Agrupe nombres de servicio con namespaces y clústeres donde corresponda.

#### istio_requests_total

**Tipo**: Contador
**Descripción**: Total de solicitudes procesadas

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

**Etiquetas principales**:
- `response_code`: Código HTTP, como 200, 404, 500
- `response_flags`: Indicadores Envoy
  - `UH`: Sin upstream saludable
  - `UF`: Fallo de conexión upstream
  - `UR`: Reset remoto upstream; `UT`: timeout de solicitud upstream
  - `DC`: Terminación de conexión downstream
  - `LR`: Reset local
  - `URX`: Límite de reintentos upstream superado o máximo de intentos TCP
- `connection_security_policy`: Estado mTLS, `mutual_tls` o `none`; source puede informar `unknown`

#### istio_request_duration_milliseconds

**Tipo**: Histograma
**Descripción**: Tiempo de procesamiento en milisegundos

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
**Descripción**: Tamaño del cuerpo de solicitud en bytes

```promql
istio_request_bytes_bucket  # Inspect actual le bounds
istio_request_bytes_bucket{le="+Inf"}  # All body sizes
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**Tipo**: Histograma
**Descripción**: Tamaño del cuerpo de respuesta en bytes

```promql
istio_response_bytes_bucket
istio_response_bytes_bucket{le="+Inf"}
istio_response_bytes_sum
istio_response_bytes_count
```

### Métricas TCP

#### istio_tcp_connections_opened_total

**Tipo**: Contador
**Descripción**: Conexiones TCP abiertas

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**Tipo**: Contador
**Descripción**: Conexiones TCP cerradas

#### istio_tcp_sent_bytes_total

**Tipo**: Contador
**Descripción**: Bytes enviados

#### istio_tcp_received_bytes_total

**Tipo**: Contador
**Descripción**: Bytes recibidos

## Métricas de circuit breaker {#circuit-breaker-metrics}

Habilite estadísticas Envoy necesarias con `proxyStatsMatcher` antes de recogerlas. El bootstrap Istio extrae `cluster_name`; bootstraps personalizados pueden cambiar etiquetas. `_open` son gauges 0/1, no contadores de eventos. Algunos contadores aparecen solo tras tráfico.

### Métricas principales

#### 1. Desbordamiento del pool upstream

```promql
# Requests rejected due to connection pool overflow
envoy_cluster_upstream_cx_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**Significado**: Se excedió `maxConnections`

#### 2. Circuit breaker abierto (Gauge)

```promql
# Gauge: 1 at capacity, 0 below limit
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

**Significado**: Rechazo por límites de solicitudes pendientes/activas. Inspeccione `rq_pending_open`, `rq_open` y umbrales generados para distinguir presión de cola del límite activo.

#### 4. Presupuesto de reintentos agotado

```promql
# Retry budget exhausted
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. Detectar circuit breaker mediante flags

```promql
# Requests rejected by circuit breaker (response_flags="UO")
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**Detalle de flags**:
- `UO`: Desbordamiento upstream, circuit breaker abierto
- `URX`: Reintentos upstream o intentos TCP máximos superados
- `UF`: Fallo de conexión upstream
- `UH`: Sin upstream saludable

### Consultas para dashboard de circuit breaker

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

No hay gauges estándar `circuit_breakers_default_cx_max` ni `rq_pending_max`. Lea límites en la configuración generada del clúster. Los opcionales `remaining_cx`/`remaining_pending` requieren `track_remaining` de Envoy; incluir el nombre no los activa. El denominador de utilización debe proceder de un límite configurado conocido y coincidente.

### Reglas de alerta

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

## Métricas de resiliencia {#resilience-metrics}

### Métricas de detección de anomalías

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
rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m])
```

**Por tipo de expulsión**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_enforced_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
```

Expulsiones detectadas y aplicadas difieren: un host anómalo puede seguir sirviendo si la probabilidad o el máximo impiden expulsarlo. Algunos algoritmos Envoy no los expone DestinationRule; una serie ausente no demuestra que el algoritmo configurado esté saludable.

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

### Métricas de timeout

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

## Integración OpenTelemetry {#opentelemetry-integration}

### Receptor Prometheus para métricas Istio

El proveedor `opentelemetry` Istio exporta **trazas**. Para métricas estándar, conserve el proveedor Prometheus y deje que **un receptor Prometheus del Collector recoja** endpoints. Después puede exportar métricas por OTLP a un backend compatible; Tempo es de trazas, no destino de métricas.

El ejemplo usa Collector Contrib 0.160.0 con exporter Prometheus para una ruta demostrativa visible. Cree `observability` primero. Use una réplica: varias con el mismo scrape duplican cada target; producción necesita asignación/sharding. La ServiceAccount solo lee Pods para los jobs de descubrimiento. Configure acceso a métricas proxy en claro 15090 e istiod 15014; no recoge métricas de aplicación ni ztunnel ambient.

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

`logging` retirado se sustituye por `debug`. Quite exportación diagnóstica tras validar. No se añade `namespace: istio`, evitando duplicar el prefijo `istio_`. Inspeccione etiquetas/nombres emitidos antes de reutilizar dashboards Kiali. Con Prometheus Operator, seleccione el Service etiquetado:

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

Prometheus debe seleccionar ServiceMonitor y namespace. `honorLabels` conserva `job`/`instance` originales; el Collector debe ser confiable. Use esta vía o el scrape directo siguiente para las mismas series, no ambas. ServiceMonitor no instala Prometheus.

### Verificar recogida

```bash
kubectl logs -n observability deployment/otel-metrics
# Keep this running in one terminal.
kubectl port-forward -n observability svc/otel-metrics 8889:8889
```

```bash
# In a second terminal, after generating test mesh traffic:
curl -fsS http://localhost:8889/metrics | rg '^istio_'
```

Receptores/exporters OTLP de trazas se configuran aparte en el [capítulo de trazado](02-tracing.md); logs debug del proxy no prueban entrega de métricas.

## Integración Prometheus {#prometheus-integration}

### Configuración Prometheus

Use la configuración en un servidor instalado con permiso list/watch Pod. Un ConfigMap no despliega ni recarga Prometheus. Los jobs conservan direcciones descubiertas, incluido IPv6, y seleccionan exactamente el puerto Envoy o istiod. Incluyen sidecars y gateways; un job gateway separado duplicaría series. El Service Mixer eliminado `istio-telemetry` no es target.

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

Solo proxy usa 15090 `/stats/prometheus`. Las métricas fusionadas de agente/aplicación usan 15020 `/stats/prometheus` con anotaciones `prometheus.io`, y necesitan otro job sin duplicación. Los certificados del agente se miden en ese endpoint. Los listeners métricos son texto plano incluso con STRICT mTLS en aplicación; restrinja su exposición. Un endpoint de aplicación separado sigue su propia autenticación.

### Alternativa Prometheus Operator

Use estos recursos en lugar de jobs manuales. Asegure selección de etiquetas/namespaces. `namespaceSelector.any: true` hace que PodMonitor inspeccione namespaces de aplicación; `port: http-envoy-prom` selecciona el puerto real de contenedor. Adapte nombres de puertos de gateways personalizados. ServiceMonitor selecciona Services, no etiquetas Deployment.

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

### Optimización de consultas

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

## Personalización con Telemetry API {#customization-with-telemetry-api}

### Personalizar métricas

#### 1. Habilitar solo métricas concretas

Las sobrescrituras se evalúan en orden. Desactive primero ALL_METRICS y reactive las dos HTTP necesarias. `mode` va dentro de `match`. Combine ajustes relacionados en un Telemetry por alcance, sin aplicar todos los ejemplos independientes a la vez.

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

#### 2. Añadir etiquetas personalizadas

Use expresiones CEL acotadas sobre HTTP. IDs de solicitud, User-Agent arbitrarios y cabeceras temporales crean etiquetas ilimitadas. `x-envoy-upstream-service-time` es duración, no identidad de clúster upstream. CEL no usa la sintaxis shell `| split()` del ejemplo.

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

#### 3. Configuración por namespace

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

#### 4. Mejorar rendimiento desactivando métricas

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

## Consultas prácticas {#practical-metric-queries}

Las proporciones de error por estado HTTP no capturan todos los fallos gRPC. Examine `grpc_response_status` y la definición de fallo de la aplicación; HTTP 200 puede llevar estado gRPC distinto de cero.

### Dashboard de señales doradas

#### 1. Latencia

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

#### 2. Tráfico

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

#### 3. Errores

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

#### 4. Saturación

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

### Monitorización mTLS

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

### Dashboard de salud de malla

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

Use `istioctl version` para versiones reales y `istioctl proxy-status` para sincronización/NACK. Antigüedad de proceso no mide frescura de configuración, y un gauge numérico de versión Envoy no distribuye etiquetas de versión. Para fallos mTLS revise contadores TLS y certificados como en la [guía mTLS](../security/01-mtls.md).

## Optimización de métricas {#metrics-optimization}

### Resolver alta cardinalidad

#### 1. Eliminar etiquetas innecesarias

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

#### 2. Normalizar valores de etiquetas

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

### Seleccionar estadísticas Envoy

`proxyStatsMatcher` selecciona qué estadísticas crear; no muestrea solicitudes. Incluya solo familias necesarias, conserve coincidencias existentes requeridas y haga rollout de proxies elegidos al cambiar bootstrap. El ejemplo activa estadísticas para consultas anteriores:

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

### Ajustar rendimiento Prometheus

Prometheus usa scrape de 1 minuto por defecto; 15s/30s son elecciones deliberadas. Combine el fragmento con jobs existentes. `metric_relabel_configs` va dentro de cada job y elimina muestras, no solo etiquetas. Configure endpoint remote-write, autenticación/TLS y persistencia para el backend.

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

## Resolución de problemas {#troubleshooting}

Los ejemplos exec/curl requieren curl en la imagen proxy. Si no existe, use `kubectl port-forward pod/<pod-name> 15090:15090`, o 15020 para el agente, y consulte desde otro terminal. Telemetry aquí es para Envoy; ambient L7 necesita asociación waypoint y ztunnel L4 una recogida separada.

### No se recogen métricas

#### 1. Comprobar endpoint Envoy

```bash
# Check Envoy admin port
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# Check metrics filter
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. Comprobar targets descubiertos por Prometheus

```bash
# Check Targets page in Prometheus UI
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# In browser: http://localhost:9090/targets
```

#### 3. Validar configuración Telemetry API

```bash
# Check Telemetry resources
kubectl get telemetry -A

# Check specific Telemetry details
kubectl describe telemetry <name> -n <namespace>

# Check if reflected in Envoy config
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
```

### Faltan etiquetas

```bash
# 1. Check if Envoy generates correct labels
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Check Prometheus relabeling rules
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. Check ServiceMonitor/PodMonitor
kubectl get servicemonitor,podmonitor -n istio-system
```

### Explosión de cardinalidad

Tras port-forward de Prometheus en otro terminal, consulte series activas y estadísticas TSDB. Contar nombres métricos no es contar series. El endpoint de estado TSDB también informa cardinalidad por etiqueta/valor.

```bash
curl -fsS http://localhost:9090/api/v1/status/tsdb | jq '.data'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=count(istio_requests_total)' | jq '.data.result'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=topk(10, count by (__name__) ({__name__=~"istio_.*"}))' | jq '.data.result'
```

### No aparecen métricas de circuit breaker

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

- [Métricas Istio](https://istio.io/latest/docs/reference/config/metrics/)
- [Observabilidad Istio](https://istio.io/latest/docs/tasks/observability/)
- [Ejemplos de consulta Prometheus](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Estadísticas Envoy](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Dashboards Istio de Grafana](https://grafana.com/grafana/dashboards/?search=istio)
