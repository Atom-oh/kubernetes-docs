# Istio 메트릭

> **지원 버전**: Istio 1.28
> **마지막 업데이트**: 2026년 2월 19일

Istio는 서비스 메시의 모든 트래픽에 대한 메트릭을 자동으로 수집하고, Prometheus, OpenTelemetry 등 다양한 백엔드와 통합하여 포괄적인 관찰성을 제공합니다.

## 목차

1. [메트릭 개요](#메트릭-개요)
2. [Istio 표준 메트릭](#istio-표준-메트릭)
3. [Circuit Breaker 메트릭](#circuit-breaker-메트릭)
4. [Resilience 메트릭](#resilience-메트릭)
5. [OpenTelemetry 통합](#opentelemetry-통합)
6. [Prometheus 통합](#prometheus-통합)
7. [Telemetry API를 통한 커스터마이징](#telemetry-api를-통한-커스터마이징)
8. [실전 메트릭 쿼리](#실전-메트릭-쿼리)
9. [메트릭 최적화](#메트릭-최적화)
10. [문제 해결](#문제-해결)

## 메트릭 개요

### Golden Signals

Istio는 Google의 SRE 원칙에 따른 Golden Signals를 자동으로 수집합니다:

1. **Latency (지연시간)**: 요청 처리 시간
2. **Traffic (트래픽)**: 시스템 처리량 (RPS, Bandwidth)
3. **Errors (에러)**: 실패율과 에러 유형
4. **Saturation (포화도)**: 리소스 사용률

### 메트릭 수집 아키텍처

![애플리케이션 파드의 Envoy 사이드카가 istiod의 설정을 받아 메트릭을 생성하고, Prometheus에 스크레이프되거나 OpenTelemetry Collector로 푸시된 뒤, Prometheus를 거쳐 Grafana와 Kiali로 시각화되는 Istio 메트릭 수집 흐름을 보여준다.](../../../../assets/diagrams/rendered/ko-service-mesh-istio-observability-01-metrics-0.svg)

## Istio 표준 메트릭

### HTTP/gRPC 메트릭

Istio는 모든 HTTP/gRPC 트래픽에 대해 다음 메트릭을 생성합니다:

#### istio_requests_total

**타입**: Counter
**설명**: 처리된 총 요청 수

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

**주요 레이블**:
- `response_code`: HTTP 상태 코드 (200, 404, 500, etc.)
- `response_flags`: Envoy 응답 플래그
  - `UH`: Upstream connection failure
  - `UF`: Upstream connection failure
  - `UR`: Upstream request timeout
  - `DC`: Downstream connection termination
  - `LR`: Local reset
  - `URX`: Rejected by circuit breaker
- `connection_security_policy`: mTLS 여부 (`mutual_tls`, `none`)

#### istio_request_duration_milliseconds

**타입**: Histogram
**설명**: 요청 처리 시간 (밀리초)

```promql
istio_request_duration_milliseconds_bucket{le="10"}  # 10ms 이하
istio_request_duration_milliseconds_bucket{le="50"}  # 50ms 이하
istio_request_duration_milliseconds_bucket{le="100"} # 100ms 이하
istio_request_duration_milliseconds_bucket{le="500"} # 500ms 이하
istio_request_duration_milliseconds_sum            # 총 시간
istio_request_duration_milliseconds_count          # 총 요청 수
```

#### istio_request_bytes

**타입**: Histogram
**설명**: 요청 본문 크기 (바이트)

```promql
istio_request_bytes_bucket{le="1024"}   # 1KB 이하
istio_request_bytes_bucket{le="10240"}  # 10KB 이하
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**타입**: Histogram
**설명**: 응답 본문 크기 (바이트)

```promql
istio_response_bytes_bucket{le="1024"}
istio_response_bytes_bucket{le="10240"}
istio_response_bytes_sum
istio_response_bytes_count
```

### TCP 메트릭

#### istio_tcp_connections_opened_total

**타입**: Counter
**설명**: 열린 TCP 연결 수

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**타입**: Counter
**설명**: 닫힌 TCP 연결 수

#### istio_tcp_sent_bytes_total

**타입**: Counter
**설명**: 전송한 바이트 수

#### istio_tcp_received_bytes_total

**타입**: Counter
**설명**: 수신한 바이트 수

## Circuit Breaker 메트릭

Circuit Breaker와 Outlier Detection 동작을 모니터링하기 위한 핵심 메트릭입니다.

### 주요 Circuit Breaker 메트릭

#### 1. Upstream Connection Pool Overflow

```promql
# 연결 풀 오버플로우로 거부된 요청
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**의미**: `maxConnections` 제한 초과

#### 2. Circuit Breaker Open (Upstream Request Rejected)

```promql
# Circuit Breaker로 거부된 요청
envoy_cluster_circuit_breakers_default_rq_open{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 3. Pending Requests Overflow

```promql
# 대기 중인 요청 수 초과
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**의미**: `http1MaxPendingRequests` 또는 `http2MaxRequests` 초과

#### 4. Retry Budget Exhausted

```promql
# 재시도 예산 소진
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. Response Flags로 Circuit Breaker 감지

```promql
# Circuit Breaker로 거부된 요청 (response_flags="UO")
sum(rate(istio_requests_total{
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**Response Flags 상세**:
- `UO`: Upstream overflow (circuit breaker open)
- `URX`: Rejected by circuit breaker
- `UF`: Upstream connection failure
- `UH`: No healthy upstream

### Circuit Breaker 모니터링 대시보드 쿼리

```promql
# 1. Circuit Breaker 발동률
sum(rate(envoy_cluster_circuit_breakers_default_rq_open[5m])) by (cluster_name)
/
sum(rate(envoy_cluster_upstream_rq_total[5m])) by (cluster_name)
* 100

# 2. 연결 풀 사용률
envoy_cluster_upstream_cx_active{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
/
envoy_cluster_circuit_breakers_default_cx_max{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
* 100

# 3. 대기 요청 사용률
envoy_cluster_upstream_rq_pending_active{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
/
envoy_cluster_circuit_breakers_default_rq_pending_max{cluster_name="outbound|80||httpbin.default.svc.cluster.local"}
* 100

# 4. Circuit Breaker로 거부된 요청 수
sum(increase(envoy_cluster_upstream_rq_pending_overflow[5m])) by (cluster_name)
```

### Circuit Breaker 알림 규칙

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

## Resilience 메트릭

### Outlier Detection 메트릭

#### 1. Ejected Hosts

```promql
# Outlier Detection으로 제거된 호스트 수
envoy_cluster_outlier_detection_ejections_active{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 2. Ejection Events

```promql
# 제거 이벤트 발생률
rate(envoy_cluster_outlier_detection_ejections_total[5m])
```

**제거 유형별**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_failure_percentage
```

### Retry 메트릭

```promql
# 재시도된 요청 수
rate(envoy_cluster_upstream_rq_retry[5m])

# 재시도 성공률
rate(envoy_cluster_upstream_rq_retry_success[5m])
/
rate(envoy_cluster_upstream_rq_retry[5m])

# 재시도 예산 소진
rate(envoy_cluster_upstream_rq_retry_overflow[5m])
```

### Timeout 메트릭

```promql
# 타임아웃 발생 요청
sum(rate(istio_requests_total{
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# 타임아웃률
sum(rate(istio_requests_total{response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total[5m]))
* 100
```

## OpenTelemetry 통합

### OpenTelemetry Collector 설정

Istio는 OpenTelemetry 프로토콜을 통해 메트릭을 내보낼 수 있습니다.

#### 1. MeshConfig 설정

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
  namespace: istio-system
data:
  mesh: |
    defaultConfig:
      tracing: {} # 추적 설정
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

#### 2. Telemetry API로 OpenTelemetry 활성화

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

#### 3. OpenTelemetry Collector 배포

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

      # Istio 메트릭에 추가 속성 추가
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

#### 4. Prometheus ServiceMonitor 설정

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

### OpenTelemetry 메트릭 검증

```bash
# 1. OpenTelemetry Collector 로그 확인
kubectl logs -n observability deployment/otel-collector

# 2. Collector 메트릭 확인
kubectl port-forward -n observability svc/opentelemetry-collector 8889:8889
curl http://localhost:8889/metrics

# 3. Envoy가 메트릭을 전송하는지 확인
istioctl proxy-config log deploy/productpage-v1 --level debug
kubectl logs -n default deploy/productpage-v1 -c istio-proxy | grep -i otel
```

## Prometheus 통합

### Prometheus 설정

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

#### 2. ServiceMonitor로 자동 스크래핑

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

### Prometheus 쿼리 최적화

```promql
# Recording Rules로 자주 사용하는 쿼리 사전 계산
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # 서비스별 요청률
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total[5m])) by (destination_service_name, destination_service_namespace)

  # 서비스별 에러율
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_service_name)
      /
      sum(rate(istio_requests_total[5m])) by (destination_service_name)

  # 서비스별 P95 지연시간
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m]))
        by (destination_service_name, le)
      )

  # Circuit Breaker 발동률
  - record: istio:circuit_breaker:open_rate:1m
    expr: |
      rate(envoy_cluster_circuit_breakers_default_rq_open[1m])
```

## Telemetry API를 통한 커스터마이징

### 메트릭 커스터마이징

#### 1. 특정 메트릭만 활성화

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
    # 요청 메트릭만 활성화
    - match:
        metric: REQUEST_COUNT
      mode: CLIENT_AND_SERVER
    - match:
        metric: REQUEST_DURATION
      mode: CLIENT_AND_SERVER
    # TCP 메트릭 비활성화
    - match:
        metric: TCP_OPENED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_CLOSED_CONNECTIONS
      disabled: true
```

#### 2. 커스텀 레이블 추가

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
        # 요청 헤더를 레이블로 추가
        request_id:
          value: "request.headers['x-request-id']"
        user_agent:
          value: "request.headers['user-agent']"
        # 응답 헤더를 레이블로 추가
        upstream_cluster:
          value: "response.headers['x-envoy-upstream-service-time']"
        # 커스텀 속성
        api_version:
          value: "request.path | split('/')[2]"
```

#### 3. 네임스페이스별 메트릭 설정

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

#### 4. 메트릭 비활성화로 성능 향상

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
    # TCP 메트릭 완전 비활성화
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

## 실전 메트릭 쿼리

### Golden Signals 대시보드

#### 1. Latency (지연시간)

```promql
# P50 지연시간
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# P95 지연시간
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# P99 지연시간
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{
    destination_service_name="reviews"
  }[5m])) by (le)
)

# 서비스별 평균 지연시간
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name)
```

#### 2. Traffic (트래픽)

```promql
# 서비스별 요청률 (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name)

# 총 요청률
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# 서비스별 인바운드 트래픽 (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name)

# 서비스별 아웃바운드 트래픽 (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name)

# HTTP 메서드별 요청 분포
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name)
```

#### 3. Errors (에러)

```promql
# 에러율 (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name)
* 100

# 4xx vs 5xx 분리
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name)

# 특정 에러 코드 추적
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name)

# Response flags로 에러 유형 분석
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name)
```

#### 4. Saturation (포화도)

```promql
# 연결 풀 사용률
(envoy_cluster_upstream_cx_active / envoy_cluster_circuit_breakers_default_cx_max) * 100

# 활성 요청 수
envoy_cluster_upstream_rq_active

# 대기 중인 요청 수
envoy_cluster_upstream_rq_pending_active

# Envoy 메모리 사용량
envoy_server_memory_allocated / envoy_server_memory_heap_size * 100
```

### mTLS 모니터링

```promql
# mTLS 사용률
sum(rate(istio_requests_total{
  connection_security_policy="mutual_tls",
  reporter="destination"
}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))
* 100

# mTLS 미사용 트래픽 감지
sum(rate(istio_requests_total{
  connection_security_policy="none",
  reporter="destination"
}[5m])) by (source_workload, destination_workload)

# mTLS 인증 실패
sum(rate(istio_requests_total{
  response_code="401",
  connection_security_policy="mutual_tls"
}[5m])) by (destination_service_name)
```

### 서비스 메시 health 대시보드

```promql
# 1. 컨트롤 플레인 상태
up{job="istiod"}

# 2. Pilot 푸시 에러
rate(pilot_xds_push_errors[5m])

# 3. Envoy 구성 업데이트 지연
rate(pilot_xds_pushes[5m])

# 4. Envoy 프록시 버전 분포
count(envoy_server_version) by (envoy_server_version)

# 5. 오래된 프록시 감지 (24시간 이상)
(time() - envoy_server_uptime) > 86400
```

## 메트릭 최적화

### 고카디널리티 문제 해결

#### 1. 불필요한 레이블 제거

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
        # 고카디널리티 레이블 제거
        request_id:
          operation: REMOVE
        user_agent:
          operation: REMOVE
```

#### 2. 레이블 값 정규화

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
        # HTTP 메서드를 정규화 (GET, POST, PUT, DELETE, OTHER)
        request_protocol:
          value: |
            request.protocol == "http" ? 
              (request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER") 
              : request.protocol
```

### 메트릭 샘플링

Envoy 통계 샘플링으로 메모리 및 CPU 사용량 감소:

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

### Prometheus 성능 튜닝

```yaml
global:
  scrape_interval: 30s  # 기본값: 15s
  evaluation_interval: 30s

# Remote write로 장기 스토리지 분리
remote_write:
- url: http://victoria-metrics:8428/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 5
    min_shards: 1
    max_samples_per_send: 5000

# 메트릭 relabeling으로 불필요한 레이블 제거
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'istio_tcp_.*'
  action: drop  # TCP 메트릭 제거
```

## 문제 해결

### 메트릭이 수집되지 않을 때

#### 1. Envoy 메트릭 엔드포인트 확인

```bash
# Envoy admin 포트 확인
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# 메트릭 필터 확인
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. Prometheus가 타겟을 발견했는지 확인

```bash
# Prometheus UI에서 Targets 페이지 확인
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# 브라우저에서: http://localhost:9090/targets
```

#### 3. Telemetry API 설정 검증

```bash
# Telemetry 리소스 확인
kubectl get telemetry -A

# 특정 Telemetry 상세 확인
kubectl describe telemetry <name> -n <namespace>

# Envoy 설정에 반영되었는지 확인
istioctl proxy-config log <pod-name> -o json | jq '.stats'
```

### 메트릭 레이블이 누락되었을 때

```bash
# 1. Envoy가 올바른 레이블을 생성하는지 확인
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Prometheus relabeling 규칙 확인
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. ServiceMonitor/PodMonitor 확인
kubectl get servicemonitor,podmonitor -n istio-system
```

### 메트릭 cardinality 폭발

```bash
# 1. 메트릭 카디널리티 확인
kubectl exec -it -n istio-system <prometheus-pod> -- sh -c \
  'wget -O- "http://localhost:9090/api/v1/label/__name__/values" 2>/dev/null' | \
  jq '.data | length'

# 2. 특정 메트릭의 시계열 수 확인
curl http://localhost:9090/api/v1/query?query='count(istio_requests_total)%20by%20(__name__)'

# 3. 레이블별 카디널리티 확인
count by (__name__, le) (istio_request_duration_milliseconds_bucket)
```

### Circuit Breaker 메트릭이 보이지 않을 때

```bash
# 1. Envoy 클러스터 통계 확인
istioctl proxy-config cluster <pod-name> --fqdn <service-fqdn> -o json | \
  jq '.[] | .circuitBreakers'

# 2. Envoy admin에서 직접 확인
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl "localhost:15000/clusters" | grep -A 10 "outbound|80||<service>"

# 3. DestinationRule이 올바르게 적용되었는지 확인
istioctl analyze -n <namespace>
```

## 참고 자료

- [Istio Metrics](https://istio.io/latest/docs/reference/config/metrics/)
- [Istio Observability](https://istio.io/latest/docs/tasks/observability/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Envoy Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Istio Dashboards](https://grafana.com/grafana/dashboards/?search=istio)
