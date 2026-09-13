# Istio 메트릭

> **지원 버전**: Istio 1.31
> **마지막 업데이트**: 2026년 9월 11일

> **검증 범위**: 실습 설정은 공식 자료와 오프라인 검증기로 확인했으며 클러스터에 배포해 실행하지 않았습니다. 각 예제의 네임스페이스·신원·스토리지·백엔드·부하 전제 조건은 대상 환경에서 확인해야 합니다.

Istio 프록시는 관측한 트래픽의 메트릭을 생성합니다. 이 문서는 사이드카/Envoy의 HTTP·TCP 메트릭과 Prometheus 또는 OpenTelemetry Collector 스크레이프를 다룹니다. Ambient ztunnel은 별도 L4 메트릭을 사용하며 HTTP 메트릭에는 waypoint가 필요합니다.

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

프록시 텔레메트리와 노드·컨테이너 exporter를 함께 사용해 Golden Signals를 측정합니다:

1. **Latency (지연시간)**: 요청 처리 시간
2. **Traffic (트래픽)**: 시스템 처리량 (RPS, Bandwidth)
3. **Errors (에러)**: 실패율과 에러 유형
4. **Saturation (포화도)**: 대기열·연결 압력과 Kubernetes exporter의 CPU·메모리

### 메트릭 수집 아키텍처

Envoy가 Prometheus 메트릭 노출 → Prometheus가 직접 스크레이프하거나 OpenTelemetry Collector의 Prometheus receiver가 스크레이프 → 설정한 메트릭 백엔드 → Grafana/Kiali. Istio OpenTelemetry extension provider는 추적을 구성하며 OTLP 메트릭 송신기가 아닙니다.

## Istio 표준 메트릭

### HTTP/gRPC 메트릭

Envoy는 HTTP/gRPC로 인식한 트래픽에 아래 메트릭을 생성합니다. 프록시별 관측이므로 목적에 맞는 reporter를 선택합니다. 수신 reporter는 같은 홉의 중복 집계를 피하고, 대상에 도달하지 못한 upstream 오류는 송신 reporter가 필요합니다. 서비스 이름은 네임스페이스(필요 시 클러스터)와 함께 그룹화합니다.

#### istio_requests_total

**타입**: Counter
**설명**: 처리된 총 요청 수

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

**주요 레이블**:
- `response_code`: HTTP 상태 코드 (200, 404, 500, etc.)
- `response_flags`: Envoy 응답 플래그
  - `UH`: No healthy upstream
  - `UF`: Upstream connection failure
  - `UR`: Upstream remote reset; `UT`: upstream request timeout
  - `DC`: Downstream connection termination
  - `LR`: Local reset
  - `URX`: Upstream retry limit exceeded (or TCP maximum connect attempts)
- `connection_security_policy`: mTLS 여부 (`mutual_tls`, `none`; source reports can be `unknown`)

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
istio_request_bytes_bucket  # 실제 le 경계를 확인
istio_request_bytes_bucket{le="+Inf"}  # 모든 본문 크기
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**타입**: Histogram
**설명**: 응답 본문 크기 (바이트)

```promql
istio_response_bytes_bucket
istio_response_bytes_bucket{le="+Inf"}
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

스크레이프 전에 `proxyStatsMatcher`로 필요한 Envoy 통계를 활성화합니다. 기본 Istio bootstrap은 `cluster_name`을 추출하며 사용자 bootstrap은 레이블이 다를 수 있습니다. Circuit breaker `_open` 메트릭은 이벤트 카운터가 아닌 0/1 gauge입니다. 일부 카운터는 트래픽 발생 후에만 보입니다.

### 주요 Circuit Breaker 메트릭

#### 1. Upstream Connection Pool Overflow

```promql
# 연결 풀 오버플로우로 거부된 요청
envoy_cluster_upstream_cx_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**의미**: `maxConnections` 제한 초과

#### 2. Circuit Breaker Open (Gauge)

```promql
# Gauge: 한도 도달 시 1, 한도 미만 0
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

**의미**: 대기·활성 요청 circuit breaker의 거부입니다. `rq_pending_open`, `rq_open`과 생성된 임계치로 대기열 압력과 활성 요청 제한을 구분합니다.

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
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**Response Flags 상세**:
- `UO`: Upstream overflow (circuit breaker open)
- `URX`: Upstream retry limit exceeded (or TCP maximum connect attempts)
- `UF`: Upstream connection failure
- `UH`: No healthy upstream

### Circuit Breaker 모니터링 대시보드 쿼리

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

표준 `circuit_breakers_default_cx_max`·`rq_pending_max` gauge는 없습니다. 제한 값은 생성된 클러스터 설정에서 확인합니다. 선택적 `remaining_cx`·`remaining_pending`은 Envoy `track_remaining`이 필요하며 통계 이름을 포함하는 것만으로 활성화되지 않습니다. 사용률 분모는 일치하는 실제 설정 한도여야 합니다.

### Circuit Breaker 알림 규칙

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
rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m])
```

**제거 유형별**:
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_enforced_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
```

감지와 실제 ejection은 다릅니다. 감지된 outlier도 enforcement 확률·최대 ejection 비율 때문에 제외되지 않을 수 있습니다. 일부 Envoy 알고리즘은 Istio DestinationRule에 노출되지 않으므로 시계열 누락을 해당 알고리즘의 정상 상태로 해석하지 않습니다.

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
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# 타임아웃률
sum(rate(istio_requests_total{reporter="source",response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total{reporter="source"}[5m]))
* 100
```

## OpenTelemetry 통합

### Istio 메트릭용 Prometheus Receiver

Istio `opentelemetry` extension provider는 **트레이스**를 내보냅니다. 표준 메시 메트릭은 Prometheus metrics provider를 유지하고 OpenTelemetry Collector의 **Prometheus receiver로 노출 endpoint를 스크레이프**합니다. Collector는 이후 OTLP로 메트릭 지원 백엔드에 내보낼 수 있습니다. Tempo는 트레이스 백엔드이며 메트릭 목적지가 아닙니다.

아래는 Collector Contrib 0.160.0의 Prometheus exporter로 결과를 조회하는 예제입니다. 먼저 `observability` 네임스페이스를 생성합니다. 동일 설정의 복제본은 모든 대상을 중복 수집하므로 replica는 1이며 운영 확장에는 대상 할당·샤딩이 필요합니다. ServiceAccount에는 파드 검색에 필요한 읽기 권한만 부여합니다. 평문 프록시 메트릭 15090·istiod 15014에 네트워크 접근을 구성하며 애플리케이션 메트릭·ambient ztunnel은 이 예제의 수집 대상이 아닙니다.

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

제거된 `logging` exporter 대신 `debug`를 사용하며 검증 후 진단 출력은 제거합니다. 기존 메트릭 이름에 `istio_`가 중복되지 않도록 `namespace: istio` 접두사를 추가하지 않습니다. Kiali 대시보드 재사용 전에 실제 출력 레이블·이름을 확인합니다. Prometheus Operator를 사용하면 레이블이 지정된 Service를 선택합니다:

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

Prometheus 리소스가 이 ServiceMonitor와 네임스페이스를 선택해야 합니다. `honorLabels`는 원본 target의 `job`/`instance`를 유지하므로 collector를 신뢰할 수 있어야 합니다. 같은 시계열에는 이 경로와 아래 직접 프록시 스크레이프 중 하나를 사용합니다. ServiceMonitor는 Prometheus를 설치하지 않습니다.

### 수집 검증

```bash
kubectl logs -n observability deployment/otel-metrics
# Keep this running in one terminal.
kubectl port-forward -n observability svc/otel-metrics 8889:8889
```

```bash
# In a second terminal, after generating test mesh traffic:
curl -fsS http://localhost:8889/metrics | rg '^istio_'
```

트레이스 OTLP receiver·exporter는 [추적 장](02-tracing.md)에서 별도로 구성합니다. 프록시 debug 로그만으로 메트릭 전달을 증명할 수는 없습니다.

## Prometheus 통합

### Prometheus 설정

다음 설정을 파드 list/watch 권한이 있는 설치된 Prometheus 서버에 적용합니다. ConfigMap만으로 Prometheus가 배포·재로드되지는 않습니다. 파드 검색 주소(IPv6 포함)를 유지하며 Envoy 메트릭 포트 또는 istiod monitoring 포트만 선택합니다. 사이드카·게이트웨이를 함께 포함하므로 별도 gateway job은 중복 수집을 만듭니다. 제거된 Mixer `istio-telemetry` Service는 대상이 아닙니다.

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

프록시 전용 수집은 15090 `/stats/prometheus`를 사용합니다. 기본 agent·애플리케이션 병합 메트릭은 `prometheus.io` annotation 기반 15020 `/stats/prometheus`를 사용하므로 중복되지 않는 별도 job이 필요합니다. Agent 인증서 메트릭에는 agent endpoint가 필요합니다. 애플리케이션이 STRICT mTLS여도 이 메트릭 listener는 평문이므로 네트워크 노출을 제한합니다. 별도 애플리케이션 endpoint는 해당 인증 정책을 따릅니다.

### Prometheus Operator 대안

수동 job 대신 다음을 사용하고 Prometheus 리소스가 레이블·네임스페이스를 선택하도록 합니다. `namespaceSelector.any: true`는 애플리케이션 네임스페이스도 검색하고 `port: http-envoy-prom`은 실제 메트릭 컨테이너 포트를 선택합니다. 사용자 gateway 포트 이름은 맞춰야 합니다. ServiceMonitor는 Deployment 레이블이 아닌 Service를 선택합니다.

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

### Prometheus 쿼리 최적화

```yaml
# Recording Rules로 자주 사용하는 쿼리 사전 계산
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # 서비스별 요청률
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # 서비스별 에러율
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) by (destination_service_name, destination_service_namespace)
      /
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # 서비스별 P95 지연시간
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))
        by (destination_service_name, destination_service_namespace, le)
      )

  # Circuit Breaker 상태 gauge
  - record: istio:circuit_breaker:at_capacity
    expr: |
      envoy_cluster_circuit_breakers_default_rq_open
```

## Telemetry API를 통한 커스터마이징

### 메트릭 커스터마이징

#### 1. 특정 메트릭만 활성화

Override는 순서대로 적용됩니다. ALL_METRICS를 끈 뒤 필요한 두 HTTP 메트릭을 켭니다. `mode`는 `match` 내부 필드입니다. 아래 독립 예제를 모두 함께 적용하지 말고 선택 범위별 하나의 Telemetry에 필요한 설정을 병합합니다.

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

#### 2. 커스텀 레이블 추가

HTTP 메트릭에는 값이 제한된 CEL 표현식을 사용합니다. 요청 ID·임의 User-Agent·타이밍 헤더는 레이블 수를 폭증시킵니다. `x-envoy-upstream-service-time`은 upstream 클러스터 신원이 아닌 시간이며 CEL은 예전 셸 형태의 `| split()` 문법을 사용하지 않습니다.

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

#### 3. 네임스페이스별 메트릭 설정

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

#### 4. 메트릭 비활성화로 성능 향상

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

HTTP 상태 기반 에러율은 모든 gRPC 실패를 포착하지 않습니다. gRPC는 `grpc_response_status`와 애플리케이션의 실패 정의를 확인해야 하며 HTTP 200에도 0이 아닌 gRPC 상태가 포함될 수 있습니다.

### Golden Signals 대시보드

#### 1. Latency (지연시간)

```promql
# P50 지연시간
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P95 지연시간
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P99 지연시간
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# 서비스별 평균 지연시간
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

#### 2. Traffic (트래픽)

```promql
# 서비스별 요청률 (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# 총 요청률
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# 서비스별 인바운드 트래픽 (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# 서비스별 아웃바운드 트래픽 (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# 프로토콜별 요청 분포(HTTP 메서드가 아님)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name, destination_service_namespace)
```

#### 3. Errors (에러)

```promql
# 에러율 (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# 4xx vs 5xx 분리
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# 특정 에러 코드 추적
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Response flags로 에러 유형 분석
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name, destination_service_namespace)
```

#### 4. Saturation (포화도)

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

# 인증된 메시 트래픽의 HTTP 401이며 TLS 핸드셰이크 실패가 아닙니다.
sum by (destination_service_name, destination_service_namespace) (
  rate(istio_requests_total{reporter="destination",response_code="401",connection_security_policy="mutual_tls"}[5m])
)
```

### 서비스 메시 health 대시보드

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

실제 프록시 버전은 `istioctl version`, 동기화·NACK은 `istioctl proxy-status`로 확인합니다. 프로세스 나이는 설정 최신성을 나타내지 않으며 숫자형 Envoy version gauge를 버전 레이블 분포로 집계할 수 없습니다. mTLS 오류는 [mTLS 가이드](../security/01-mtls.md)의 TLS 검증 카운터·인증서를 확인합니다.

## 메트릭 최적화

### 고카디널리티 문제 해결

#### 1. 불필요한 레이블 제거

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
        # 고카디널리티 레이블 제거
        request_id:
          operation: REMOVE
        user_agent:
          operation: REMOVE
```

#### 2. 레이블 값 정규화

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
        # HTTP 메서드를 정규화 (GET, POST, PUT, DELETE, OTHER)
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER"'
```

### Envoy 통계 선택

`proxyStatsMatcher`는 생성할 Envoy 통계를 선택하며 요청을 샘플링하지 않습니다. 필요한 종류만 포함하고 기존 필수 조건을 유지하며 부트스트랩 변경 후 대상 프록시를 순차 교체합니다. 다음은 앞의 쿼리에 필요한 통계 활성화 예제입니다:

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

### Prometheus 성능 튜닝

Prometheus 기본 scrape 간격은 1분이며 15초·30초는 선택한 값입니다. 다음은 기존 scrape job에 병합할 설정 조각입니다. `metric_relabel_configs`는 각 scrape job 내부에 위치하고 레이블만이 아닌 샘플을 버립니다. Remote-write endpoint·인증/TLS·영속성은 선택한 백엔드에 맞춰 구성합니다.

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

## 문제 해결

exec/curl 예제는 curl이 있는 프록시 이미지가 필요합니다. 없으면 `kubectl port-forward pod/<pod-name> 15090:15090`(agent는 15020) 후 다른 터미널에서 조회합니다. 여기의 Telemetry 예제는 Envoy 기준이며 ambient L7은 waypoint에 연결하고 ztunnel L4는 별도로 수집합니다.

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
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
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

다른 터미널에서 Prometheus를 port-forward한 뒤 활성 시계열과 TSDB 통계를 조회합니다. 메트릭 이름 수는 시계열 수가 아닙니다. TSDB status endpoint에는 레이블·값별 카디널리티도 포함됩니다.

```bash
curl -fsS http://localhost:9090/api/v1/status/tsdb | jq '.data'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=count(istio_requests_total)' | jq '.data.result'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=topk(10, count by (__name__) ({__name__=~"istio_.*"}))' | jq '.data.result'
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
