# 관측성 스택 운영: Loki, Tempo, Prometheus 구성 가이드

> **지원 버전**: Loki 3.0+, Tempo 2.4+, Prometheus 2.50+, Grafana 10.0+
> **마지막 업데이트**: 2025년 6월

< [이전: 관측성 분석](./08-observability-analysis.md) | [목차](./README.md) | [다음: 리소스 최적화](./10-resource-optimization.md) >

---

## 1. 관측성 스택 아키텍처

### 1.1 Full Stack 개요

현대적인 관측성 스택은 세 가지 핵심 데이터 유형(메트릭, 로그, 트레이스)을 수집하고 분석하는 통합 플랫폼입니다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Grafana (Visualization)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Metrics    │  │    Logs      │  │   Traces     │  │  Dashboards  │     │
│  │   Explorer   │  │   Explorer   │  │   Explorer   │  │   & Alerts   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
└─────────┼─────────────────┼─────────────────┼───────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Prometheus    │ │      Loki       │ │      Tempo      │
│      / AMP      │ │   (Log Store)   │ │  (Trace Store)  │
│  (Metric Store) │ │                 │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │         ┌─────────┴─────────┐         │
         │         │                   │         │
         ▼         ▼                   ▼         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Collectors & Agents                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Prometheus  │  │   Promtail   │  │    OTEL      │  │   Grafana    │     │
│  │   Scraper    │  │   DaemonSet  │  │  Collector   │  │    Alloy     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Applications & Infrastructure                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Pods      │  │   Services   │  │    Nodes     │  │   Control    │     │
│  │  (metrics,   │  │  (endpoints) │  │  (kubelet,   │  │    Plane     │     │
│  │  logs, traces)│ │              │  │   cAdvisor)  │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 컴포넌트 역할

| 컴포넌트 | 역할 | 데이터 유형 | 스토리지 |
|---------|------|------------|---------|
| **Prometheus/AMP** | 메트릭 수집 및 저장 | 시계열 메트릭 | AMP (관리형) |
| **Loki** | 로그 집계 및 쿼리 | 로그 스트림 | S3 |
| **Tempo** | 분산 트레이싱 | 스팬/트레이스 | S3 |
| **Grafana** | 시각화 및 분석 | 통합 뷰 | - |
| **OTEL Collector** | 텔레메트리 수집/변환 | 메트릭, 로그, 트레이스 | - |

### 1.3 스토리지 백엔드 선택

```
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Backend Options                       │
├─────────────────┬───────────────────┬───────────────────────────┤
│   Component     │   Recommended     │   Alternative             │
├─────────────────┼───────────────────┼───────────────────────────┤
│   Prometheus    │   AMP (관리형)     │   Thanos + S3            │
│   Loki          │   S3              │   MinIO, GCS             │
│   Tempo         │   S3              │   MinIO, GCS             │
└─────────────────┴───────────────────┴───────────────────────────┘
```

---

## 2. Loki 운영 가이드

### 2.1 Helm 설치

Loki는 클러스터 규모에 따라 두 가지 배포 모드를 지원합니다.

#### SimpleScalable 모드 (소/중규모)

일일 로그 수집량 100GB 미만의 환경에 적합합니다.

```bash
# Helm 저장소 추가
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 네임스페이스 생성
kubectl create namespace observability

# SimpleScalable 모드 설치
helm install loki grafana/loki \
  --namespace observability \
  --values loki-simple-values.yaml
```

#### Distributed 모드 (대규모)

일일 로그 수집량 100GB 이상의 환경에 적합합니다.

```bash
# Distributed 모드 설치
helm install loki grafana/loki-distributed \
  --namespace observability \
  --values loki-distributed-values.yaml
```

### 2.2 Loki Distributed Helm Values

```yaml
# loki-distributed-values.yaml
# Loki Distributed 모드 전체 설정

global:
  image:
    registry: docker.io
  priorityClassName: system-cluster-critical

loki:
  # 스토리지 스키마 설정
  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: s3
        schema: v13
        index:
          prefix: loki_index_
          period: 24h

  # 스토리지 백엔드 설정
  storage:
    type: s3
    bucketNames:
      chunks: loki-chunks-bucket
      ruler: loki-ruler-bucket
      admin: loki-admin-bucket
    s3:
      region: ap-northeast-2
      # IRSA 사용 시 accessKeyId/secretAccessKey 불필요
      s3ForcePathStyle: false
      insecure: false

  # 구조화된 설정
  structuredConfig:
    auth_enabled: false

    server:
      http_listen_port: 3100
      grpc_listen_port: 9095
      log_level: info

    common:
      path_prefix: /var/loki
      replication_factor: 3
      ring:
        kvstore:
          store: memberlist

    memberlist:
      join_members:
        - loki-memberlist

    # 인제스터 설정
    ingester:
      chunk_idle_period: 30m
      chunk_block_size: 262144
      chunk_encoding: snappy
      chunk_retain_period: 1m
      max_transfer_retries: 0
      wal:
        enabled: true
        dir: /var/loki/wal

    # 쿼리어 설정
    querier:
      max_concurrent: 10
      query_ingesters_within: 3h

    # 쿼리 프론트엔드 설정
    query_scheduler:
      max_outstanding_requests_per_tenant: 2048

    # 리텐션 설정
    limits_config:
      retention_period: 720h  # 30일
      max_query_series: 500
      max_query_parallelism: 32
      max_entries_limit_per_query: 10000
      ingestion_rate_mb: 16
      ingestion_burst_size_mb: 32
      per_stream_rate_limit: 5MB
      per_stream_rate_limit_burst: 15MB

    # 컴팩터 설정
    compactor:
      working_directory: /var/loki/compactor
      shared_store: s3
      compaction_interval: 10m
      retention_enabled: true
      retention_delete_delay: 2h
      retention_delete_worker_count: 150

# 컴포넌트별 리소스 설정
ingester:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/component: ingester
          topologyKey: kubernetes.io/hostname

distributor:
  replicas: 3
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi

querier:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi

queryFrontend:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi

compactor:
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 2Gi
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3

ruler:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi

gateway:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi

# ServiceAccount 설정 (IRSA)
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/LokiS3AccessRole

# 모니터링 설정
monitoring:
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
  selfMonitoring:
    enabled: true
    grafanaAgent:
      installOperator: false
```

### 2.3 로그 수집기: Promtail vs Grafana Alloy

#### Promtail DaemonSet 설정

```yaml
# promtail-values.yaml
daemonset:
  enabled: true

config:
  clients:
    - url: http://loki-gateway.observability.svc:3100/loki/api/v1/push
      tenant_id: default
      batchwait: 1s
      batchsize: 1048576
      timeout: 10s

  positions:
    filename: /var/log/positions.yaml

  scrape_configs:
    # 컨테이너 로그 수집
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
        - role: pod
      relabel_configs:
        # 네임스페이스 레이블
        - source_labels: [__meta_kubernetes_namespace]
          target_label: namespace
        # 파드 이름 레이블 (주의: 높은 카디널리티)
        - source_labels: [__meta_kubernetes_pod_name]
          target_label: pod
        # 컨테이너 이름 레이블
        - source_labels: [__meta_kubernetes_pod_container_name]
          target_label: container
        # 앱 레이블
        - source_labels: [__meta_kubernetes_pod_label_app]
          target_label: app
        # 로그 경로 설정
        - replacement: /var/log/pods/*$1/*.log
          separator: /
          source_labels:
            - __meta_kubernetes_pod_uid
            - __meta_kubernetes_pod_container_name
          target_label: __path__
      pipeline_stages:
        # JSON 로그 파싱
        - cri: {}
        - json:
            expressions:
              level: level
              message: msg
              trace_id: trace_id
        - labels:
            level:
        - timestamp:
            source: time
            format: RFC3339Nano

    # 시스템 로그 수집
    - job_name: journal
      journal:
        max_age: 12h
        labels:
          job: systemd-journal
      relabel_configs:
        - source_labels: [__journal__systemd_unit]
          target_label: unit

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

tolerations:
  - operator: Exists

serviceMonitor:
  enabled: true
```

#### Grafana Alloy 설정

Grafana Alloy는 Promtail, OTEL Collector의 기능을 통합한 차세대 수집기입니다.

```yaml
# alloy-values.yaml
alloy:
  configMap:
    content: |
      // Kubernetes 로그 수집
      discovery.kubernetes "pods" {
        role = "pod"
      }

      discovery.relabel "pods" {
        targets = discovery.kubernetes.pods.targets

        rule {
          source_labels = ["__meta_kubernetes_namespace"]
          target_label  = "namespace"
        }
        rule {
          source_labels = ["__meta_kubernetes_pod_name"]
          target_label  = "pod"
        }
        rule {
          source_labels = ["__meta_kubernetes_pod_container_name"]
          target_label  = "container"
        }
        rule {
          source_labels = ["__meta_kubernetes_pod_label_app"]
          target_label  = "app"
        }
      }

      loki.source.kubernetes "pods" {
        targets    = discovery.relabel.pods.output
        forward_to = [loki.process.pods.receiver]
      }

      loki.process "pods" {
        stage.cri {}

        stage.json {
          expressions = {
            level    = "level",
            trace_id = "trace_id",
          }
        }

        stage.labels {
          values = {
            level = "",
          }
        }

        forward_to = [loki.write.default.receiver]
      }

      loki.write "default" {
        endpoint {
          url = "http://loki-gateway.observability.svc:3100/loki/api/v1/push"
          tenant_id = "default"
        }
      }

      // OTLP 트레이스 수신
      otelcol.receiver.otlp "default" {
        grpc {
          endpoint = "0.0.0.0:4317"
        }
        http {
          endpoint = "0.0.0.0:4318"
        }
        output {
          traces = [otelcol.processor.batch.default.input]
        }
      }

      otelcol.processor.batch "default" {
        output {
          traces = [otelcol.exporter.otlp.tempo.input]
        }
      }

      otelcol.exporter.otlp "tempo" {
        client {
          endpoint = "tempo-distributor.observability.svc:4317"
          tls {
            insecure = true
          }
        }
      }

controller:
  type: daemonset

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 1
    memory: 1Gi
```

### 2.4 레이블 설계 전략

효율적인 Loki 운영을 위한 레이블 설계는 매우 중요합니다.

#### 권장 레이블

```yaml
# 권장: 낮은 카디널리티 레이블
labels:
  namespace: production        # 네임스페이스 수 제한적
  app: api-gateway            # 애플리케이션 수 제한적
  container: main             # 컨테이너 이름 일반적으로 고정
  env: production             # 환경 (dev/staging/production)
  team: platform              # 팀 식별자
```

#### 피해야 할 레이블

```yaml
# 금지: 높은 카디널리티 레이블
labels:
  pod: api-gateway-7d8f9c6b5-x2k4m  # 파드 이름 (지속적 변경)
  pod_ip: 10.0.15.234              # IP 주소 (지속적 변경)
  request_id: uuid-12345           # 요청 ID (무한 증가)
  user_id: 12345                   # 사용자 ID (무한 증가)
```

#### 카디널리티 관리 가이드라인

| 레이블 유형 | 최대 권장 값 | 설명 |
|------------|-------------|------|
| namespace | < 50 | 클러스터당 네임스페이스 수 |
| app | < 200 | 총 애플리케이션 수 |
| container | < 5 | 앱당 컨테이너 수 |
| **총 스트림** | < 10,000 | 전체 고유 레이블 조합 |

### 2.5 리텐션 정책 설정

```yaml
# loki-retention-config.yaml
limits_config:
  # 글로벌 리텐션
  retention_period: 720h  # 30일

  # 테넌트별 리텐션 (multi-tenant 환경)
  per_tenant_override_config: /etc/loki/overrides.yaml

compactor:
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
  delete_request_cancel_period: 24h
```

테넌트별 리텐션 오버라이드:

```yaml
# overrides.yaml
overrides:
  # 개발 환경: 7일 보관
  development:
    retention_period: 168h

  # 스테이징 환경: 14일 보관
  staging:
    retention_period: 336h

  # 프로덕션 환경: 90일 보관
  production:
    retention_period: 2160h

  # 규정 준수 대상: 1년 보관
  compliance:
    retention_period: 8760h
```

### 2.6 인덱스 및 청크 최적화

```yaml
# 최적화된 스키마 및 청크 설정
schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb           # TSDB 인덱스 (권장)
      object_store: s3
      schema: v13           # 최신 스키마 버전
      index:
        prefix: loki_index_
        period: 24h

ingester:
  chunk_idle_period: 30m      # 유휴 청크 플러시 주기
  chunk_block_size: 262144    # 256KB 블록 크기
  chunk_encoding: snappy      # 압축 알고리즘 (snappy: 빠름, gzip: 높은 압축률)
  chunk_retain_period: 1m
  chunk_target_size: 1572864  # 1.5MB 목표 청크 크기
  max_chunk_age: 2h           # 최대 청크 수명
```

청크 인코딩 비교:

| 인코딩 | 압축률 | CPU 사용량 | 사용 케이스 |
|-------|--------|-----------|------------|
| snappy | 중간 | 낮음 | 일반적인 사용 (권장) |
| gzip | 높음 | 높음 | 스토리지 비용 최적화 |
| lz4 | 낮음 | 매우 낮음 | 고성능 요구 환경 |
| none | 없음 | 없음 | 테스트용 |

### 2.7 LogQL 쿼리 패턴

#### 서비스별 에러율

```logql
# 최근 5분간 서비스별 에러 로그 비율
sum(rate({namespace="production"} |= "error" [5m])) by (app)
/
sum(rate({namespace="production"} [5m])) by (app)
* 100
```

#### 구조화된 로그에서 지연시간 추출

```logql
# JSON 로그에서 응답 시간 추출
{namespace="production", app="api-gateway"}
| json
| response_time_ms > 1000
| line_format "slow request: {{.method}} {{.path}} took {{.response_time_ms}}ms"
```

#### 로그 볼륨 분석

```logql
# 네임스페이스별 로그 볼륨 (bytes/sec)
sum(rate({namespace=~".+"} | __error__="" [5m])) by (namespace)

# 앱별 로그 라인 수
sum(count_over_time({namespace="production"} [1h])) by (app)
```

#### 패턴 매칭 쿼리

```logql
# 특정 에러 패턴 검색
{namespace="production", app="payment-service"}
|~ "(?i)payment.*failed|transaction.*error"
| json
| line_format "{{.timestamp}} [{{.level}}] {{.message}}"

# IP 주소 추출
{namespace="production"}
| regexp "(?P<ip>\\d+\\.\\d+\\.\\d+\\.\\d+)"
| ip != ""
```

### 2.8 알림 규칙 설정

```yaml
# loki-ruler-config.yaml
ruler:
  enabled: true
  alertmanager_url: http://alertmanager.monitoring.svc:9093
  enable_api: true
  enable_alertmanager_v2: true
  storage:
    type: local
    local:
      directory: /var/loki/rules
  rule_path: /tmp/loki/rules
  ring:
    kvstore:
      store: memberlist
```

알림 규칙 정의:

```yaml
# alert-rules.yaml
groups:
  - name: loki-alerts
    rules:
      # 에러 로그 급증 알림
      - alert: HighErrorRate
        expr: |
          sum(rate({namespace="production"} |= "error" [5m])) by (app)
          /
          sum(rate({namespace="production"} [5m])) by (app)
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected for {{ $labels.app }}"
          description: "Error rate is {{ $value | printf \"%.2f\" }}% for {{ $labels.app }}"

      # 로그 누락 알림
      - alert: MissingLogs
        expr: |
          absent_over_time({namespace="production", app="critical-service"}[15m])
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "No logs from critical-service"
          description: "critical-service has not produced logs for 15 minutes"

      # 특정 키워드 알림
      - alert: SecurityIncident
        expr: |
          count_over_time({namespace="production"} |~ "unauthorized|forbidden|access denied" [5m]) > 10
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Potential security incident detected"
          description: "Multiple unauthorized access attempts detected"

      # OOM 발생 알림
      - alert: OOMKilled
        expr: |
          count_over_time({namespace="production"} |= "OOMKilled" [5m]) > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Container OOMKilled detected"
          description: "A container was terminated due to OOM"
```

---

## 3. Tempo 운영 가이드

### 3.1 Helm 설치

```bash
# Tempo Distributed 모드 설치
helm install tempo grafana/tempo-distributed \
  --namespace observability \
  --values tempo-distributed-values.yaml
```

### 3.2 Tempo Distributed Helm Values

```yaml
# tempo-distributed-values.yaml
# Tempo Distributed 모드 전체 설정

global:
  image:
    registry: docker.io
  priorityClassName: ""

tempo:
  # 메인 설정
  structuredConfig:
    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: "0.0.0.0:4317"
            http:
              endpoint: "0.0.0.0:4318"
        jaeger:
          protocols:
            thrift_http:
              endpoint: "0.0.0.0:14268"
            grpc:
              endpoint: "0.0.0.0:14250"
        zipkin:
          endpoint: "0.0.0.0:9411"

    # 인제스터 설정
    ingester:
      max_block_duration: 5m
      max_block_bytes: 1073741824  # 1GB
      complete_block_timeout: 15m
      flush_check_period: 10s
      trace_idle_period: 10s

    # 컴팩터 설정
    compactor:
      compaction:
        block_retention: 336h  # 14일
        compacted_block_retention: 1h
        compaction_window: 1h
        max_compaction_objects: 6000000
        max_block_bytes: 107374182400  # 100GB
        retention_concurrency: 10
      ring:
        kvstore:
          store: memberlist

    # 쿼리어 설정
    querier:
      max_concurrent_queries: 20
      search:
        prefer_self: 10
        external_backend: null

    # 쿼리 프론트엔드 설정
    query_frontend:
      max_retries: 2
      search:
        concurrent_jobs: 1000
        target_bytes_per_job: 104857600  # 100MB

    # 메트릭 생성기 설정
    metrics_generator:
      registry:
        external_labels:
          source: tempo
          cluster: eks-production
      storage:
        path: /var/tempo/generator/wal
        remote_write:
          - url: http://prometheus:9090/api/v1/write
            send_exemplars: true
      processor:
        service_graphs:
          wait: 10s
          max_items: 10000
          workers: 10
        span_metrics:
          dimensions:
            - service.name
            - http.method
            - http.status_code
          enable_target_info: true

    # 스토리지 설정
    storage:
      trace:
        backend: s3
        s3:
          bucket: tempo-traces-bucket
          endpoint: s3.ap-northeast-2.amazonaws.com
          region: ap-northeast-2
          # IRSA 사용
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/blocks
        cache: memcached
        memcached:
          consistent_hash: true
          host: tempo-memcached.observability.svc
          service: memcached-client
          timeout: 500ms

    # 오버라이드 설정
    overrides:
      defaults:
        ingestion:
          rate_limit_bytes: 15000000
          burst_size_bytes: 20000000
          max_traces_per_user: 10000
        global:
          max_bytes_per_trace: 5000000
        search:
          max_duration: 168h
        metrics_generator:
          processors:
            - service-graphs
            - span-metrics

# 컴포넌트별 리소스 설정
distributor:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2
      memory: 2Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80

ingester:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/component: ingester
          topologyKey: kubernetes.io/hostname

querier:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi

queryFrontend:
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi

compactor:
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi
  persistence:
    enabled: true
    size: 50Gi

metricsGenerator:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 2Gi

# Memcached 캐시
memcached:
  enabled: true
  replicas: 3
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 1Gi

# ServiceAccount 설정 (IRSA)
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/TempoS3AccessRole

# Gateway
gateway:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi

# 모니터링
monitoring:
  serviceMonitor:
    enabled: true
```

### 3.3 OTEL Collector 설정

```yaml
# otel-collector-config.yaml
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
            endpoint: "0.0.0.0:4317"
            max_recv_msg_size_mib: 16
          http:
            endpoint: "0.0.0.0:4318"
            cors:
              allowed_origins:
                - "*"

      # Jaeger 호환성
      jaeger:
        protocols:
          thrift_http:
            endpoint: "0.0.0.0:14268"
          grpc:
            endpoint: "0.0.0.0:14250"

      # Zipkin 호환성
      zipkin:
        endpoint: "0.0.0.0:9411"

    processors:
      # 배치 처리
      batch:
        send_batch_size: 10000
        send_batch_max_size: 11000
        timeout: 10s

      # 메모리 제한
      memory_limiter:
        check_interval: 1s
        limit_mib: 1500
        spike_limit_mib: 500

      # 리소스 속성 추가
      resource:
        attributes:
          - key: cluster
            value: eks-production
            action: upsert
          - key: environment
            value: production
            action: upsert

      # 속성 처리
      attributes:
        actions:
          - key: http.request.header.authorization
            action: delete
          - key: db.statement
            action: hash

    exporters:
      # Tempo로 트레이스 전송
      otlp/tempo:
        endpoint: tempo-distributor.observability.svc:4317
        tls:
          insecure: true
        sending_queue:
          enabled: true
          num_consumers: 10
          queue_size: 5000
        retry_on_failure:
          enabled: true
          initial_interval: 5s
          max_interval: 30s
          max_elapsed_time: 300s

      # Prometheus로 메트릭 전송 (스팬 메트릭)
      prometheusremotewrite:
        endpoint: http://prometheus:9090/api/v1/write
        resource_to_telemetry_conversion:
          enabled: true

      # 디버그 출력
      debug:
        verbosity: detailed
        sampling_initial: 5
        sampling_thereafter: 200

    extensions:
      health_check:
        endpoint: "0.0.0.0:13133"
      pprof:
        endpoint: "0.0.0.0:1777"
      zpages:
        endpoint: "0.0.0.0:55679"

    service:
      extensions: [health_check, pprof, zpages]
      pipelines:
        traces:
          receivers: [otlp, jaeger, zipkin]
          processors: [memory_limiter, resource, attributes, batch]
          exporters: [otlp/tempo]
      telemetry:
        logs:
          level: info
        metrics:
          address: "0.0.0.0:8888"
```

OTEL Collector Deployment:

```yaml
# otel-collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 3
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
            - containerPort: 4317   # OTLP gRPC
            - containerPort: 4318   # OTLP HTTP
            - containerPort: 14268  # Jaeger HTTP
            - containerPort: 14250  # Jaeger gRPC
            - containerPort: 9411   # Zipkin
            - containerPort: 8888   # Metrics
            - containerPort: 13133  # Health check
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
          volumeMounts:
            - name: config
              mountPath: /etc/otel
          livenessProbe:
            httpGet:
              path: /
              port: 13133
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 13133
            initialDelaySeconds: 5
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  type: ClusterIP
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
    - name: jaeger-http
      port: 14268
      targetPort: 14268
    - name: jaeger-grpc
      port: 14250
      targetPort: 14250
    - name: zipkin
      port: 9411
      targetPort: 9411
  selector:
    app: otel-collector
```

### 3.4 샘플링 전략

#### Head-based 샘플링 (확률적)

```yaml
# otel-collector-head-sampling.yaml
processors:
  # 확률적 샘플링: 10%
  probabilistic_sampler:
    sampling_percentage: 10
    hash_seed: 22

  # Rate limiting: 초당 최대 100 트레이스
  tail_sampling:
    decision_wait: 10s
    num_traces: 100
    expected_new_traces_per_sec: 100
    policies:
      - name: rate-limit
        type: rate_limiting
        rate_limiting:
          spans_per_second: 100

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [probabilistic_sampler]
      exporters: [otlp/tempo]
```

#### Tail-based 샘플링 (조건부)

```yaml
# otel-collector-tail-sampling.yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    expected_new_traces_per_sec: 1000
    policies:
      # 에러가 있는 트레이스 항상 수집
      - name: errors
        type: status_code
        status_code:
          status_codes:
            - ERROR

      # 2초 이상 걸린 트레이스 수집
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 2000

      # 특정 서비스의 트레이스 항상 수집
      - name: critical-services
        type: string_attribute
        string_attribute:
          key: service.name
          values:
            - payment-service
            - order-service
          enabled_regex_matching: false

      # 나머지는 5%만 샘플링
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 5

      # 복합 조건: 특정 HTTP 경로 + 지연시간
      - name: composite
        type: composite
        composite:
          max_total_spans_per_second: 1000
          policy_order: [slow-api-calls, default]
          composite_sub_policy:
            - name: slow-api-calls
              type: and
              and:
                and_sub_policy:
                  - name: latency-filter
                    type: latency
                    latency:
                      threshold_ms: 500
                  - name: api-path
                    type: string_attribute
                    string_attribute:
                      key: http.target
                      values:
                        - /api/.*
                      enabled_regex_matching: true
            - name: default
              type: probabilistic
              probabilistic:
                sampling_percentage: 1

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [tail_sampling, batch]
      exporters: [otlp/tempo]
```

### 3.5 TraceQL 쿼리 예제

```traceql
# 2초 이상 걸린 트레이스 검색
{duration > 2s}

# 에러 상태인 트레이스
{status = error}

# 특정 서비스의 트레이스
{resource.service.name = "api-gateway"}

# HTTP 500 에러
{span.http.status_code = 500}

# 특정 엔드포인트에서 500ms 이상 지연
{span.http.target = "/api/orders" && duration > 500ms}

# 데이터베이스 쿼리가 느린 트레이스
{span.db.system = "postgresql" && duration > 100ms}

# 여러 조건 조합
{resource.service.name = "payment-service" && status = error && duration > 1s}

# 특정 사용자의 요청 추적
{span.user.id = "user-12345"}

# gRPC 에러
{span.rpc.system = "grpc" && span.rpc.grpc.status_code != 0}
```

### 3.6 서비스 그래프 설정

```yaml
# tempo-service-graph.yaml
metrics_generator:
  processor:
    service_graphs:
      wait: 10s              # 그래프 빌드 대기 시간
      max_items: 10000       # 최대 항목 수
      workers: 10            # 워커 스레드 수
      dimensions:
        - service.name
        - service.namespace
      peer_attributes:
        - db.system
        - messaging.system
        - rpc.system
      histogram_buckets:
        - 0.01
        - 0.05
        - 0.1
        - 0.5
        - 1
        - 2
        - 5
```

### 3.7 Trace-to-Log 연동

애플리케이션에서 traceID를 로그에 포함:

```java
// Java (Spring Boot with Sleuth/Micrometer Tracing)
import io.micrometer.tracing.Tracer;
import org.slf4j.MDC;

@Component
public class TracingFilter implements Filter {
    private final Tracer tracer;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) {
        if (tracer.currentSpan() != null) {
            MDC.put("trace_id", tracer.currentSpan().context().traceId());
            MDC.put("span_id", tracer.currentSpan().context().spanId());
        }
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}
```

```python
# Python (OpenTelemetry)
import logging
from opentelemetry import trace

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = "00000000000000000000000000000000"
            record.span_id = "0000000000000000"
        return True
```

```go
// Go (OpenTelemetry)
import (
    "go.opentelemetry.io/otel/trace"
    "go.uber.org/zap"
)

func LogWithTraceContext(ctx context.Context, logger *zap.Logger, msg string) {
    span := trace.SpanFromContext(ctx)
    if span.SpanContext().IsValid() {
        logger.Info(msg,
            zap.String("trace_id", span.SpanContext().TraceID().String()),
            zap.String("span_id", span.SpanContext().SpanID().String()),
        )
    }
}
```

### 3.8 스팬 메트릭 생성기

```yaml
# tempo-span-metrics.yaml
metrics_generator:
  processor:
    span_metrics:
      # 기본 차원
      dimensions:
        - service.name
        - http.method
        - http.status_code
        - http.route

      # 인트린직 차원 (자동 포함)
      intrinsic_dimensions:
        service: true
        span_name: true
        span_kind: true
        status_code: true

      # 히스토그램 설정
      histogram_buckets:
        - 0.002
        - 0.005
        - 0.01
        - 0.025
        - 0.05
        - 0.1
        - 0.25
        - 0.5
        - 1
        - 2.5
        - 5
        - 10

      # 필터링
      filter_policies:
        - include:
            match_type: strict
            attributes:
              - key: span.kind
                value: server

      # target_info 메트릭 생성
      enable_target_info: true
```

생성되는 메트릭:

```promql
# 서비스별 요청 처리량
sum(rate(traces_spanmetrics_calls_total{service_name="api-gateway"}[5m])) by (http_route)

# 서비스별 지연시간 히스토그램
histogram_quantile(0.99,
  sum(rate(traces_spanmetrics_latency_bucket{service_name="api-gateway"}[5m])) by (le, http_route)
)

# 에러율
sum(rate(traces_spanmetrics_calls_total{service_name="api-gateway", status_code="STATUS_CODE_ERROR"}[5m]))
/
sum(rate(traces_spanmetrics_calls_total{service_name="api-gateway"}[5m]))
```

---

## 4. Prometheus/AMP 운영

### 4.1 AMP 워크스페이스 설정

```hcl
# terraform/amp.tf
resource "aws_prometheus_workspace" "main" {
  alias = "eks-production"

  logging_configuration {
    log_group_arn = "${aws_cloudwatch_log_group.amp.arn}:*"
  }

  tags = {
    Environment = "production"
    Project     = "eks-observability"
  }
}

resource "aws_cloudwatch_log_group" "amp" {
  name              = "/aws/prometheus/eks-production"
  retention_in_days = 30
}

# AMP 접근을 위한 IAM 역할
resource "aws_iam_role" "prometheus" {
  name = "PrometheusRemoteWriteRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:monitoring:prometheus"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "prometheus_remote_write" {
  name = "PrometheusRemoteWrite"
  role = aws_iam_role.prometheus.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aps:RemoteWrite",
          "aps:GetSeries",
          "aps:GetLabels",
          "aps:GetMetricMetadata"
        ]
        Resource = aws_prometheus_workspace.main.arn
      }
    ]
  })
}

output "amp_workspace_endpoint" {
  value = aws_prometheus_workspace.main.prometheus_endpoint
}
```

### 4.2 Remote Write 설정

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    # Remote Write to AMP
    remoteWrite:
      - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/ws-xxxxxxxx/api/v1/remote_write
        sigv4:
          region: ap-northeast-2
        queueConfig:
          maxSamplesPerSend: 1000
          maxShards: 200
          capacity: 2500
          minShards: 1
          maxBackoff: 5s
          batchSendDeadline: 5s
          minBackoff: 30ms
        writeRelabelConfigs:
          # 불필요한 메트릭 제외
          - sourceLabels: [__name__]
            regex: "(go_.*|process_.*)"
            action: drop
          # 특정 네임스페이스만 전송
          - sourceLabels: [namespace]
            regex: "(production|staging)"
            action: keep

    # WAL 설정
    walCompression: true

    # 리소스 설정
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2
        memory: 8Gi

    # 스토리지 (로컬 WAL용)
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          resources:
            requests:
              storage: 50Gi

  serviceAccount:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/PrometheusRemoteWriteRole
```

### 4.3 Recording Rules 최적화

```yaml
# recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
    - name: kubernetes-resource-usage
      interval: 30s
      rules:
        # CPU 사용률 (네임스페이스별)
        - record: namespace:container_cpu_usage_seconds_total:sum_rate
          expr: |
            sum(rate(container_cpu_usage_seconds_total{container!="", container!="POD"}[5m])) by (namespace)

        # 메모리 사용량 (네임스페이스별)
        - record: namespace:container_memory_working_set_bytes:sum
          expr: |
            sum(container_memory_working_set_bytes{container!="", container!="POD"}) by (namespace)

        # CPU 요청 대비 사용률
        - record: namespace:container_cpu_usage_vs_request:ratio
          expr: |
            sum(rate(container_cpu_usage_seconds_total{container!="", container!="POD"}[5m])) by (namespace)
            /
            sum(kube_pod_container_resource_requests{resource="cpu"}) by (namespace)

        # 메모리 요청 대비 사용률
        - record: namespace:container_memory_usage_vs_request:ratio
          expr: |
            sum(container_memory_working_set_bytes{container!="", container!="POD"}) by (namespace)
            /
            sum(kube_pod_container_resource_requests{resource="memory"}) by (namespace)

    - name: http-request-metrics
      interval: 30s
      rules:
        # 서비스별 요청률
        - record: service:http_requests_total:rate5m
          expr: |
            sum(rate(http_requests_total[5m])) by (service, method, status_code)

        # 서비스별 에러율
        - record: service:http_errors_total:rate5m
          expr: |
            sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (service)

        # 서비스별 P99 지연시간
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
            )

    - name: pod-restarts
      interval: 1m
      rules:
        # 파드 재시작 횟수 (5분간)
        - record: namespace_pod:kube_pod_container_status_restarts_total:increase5m
          expr: |
            increase(kube_pod_container_status_restarts_total[5m])
```

### 4.4 장기 보존 전략

| 기능 | AMP | Thanos |
|-----|-----|--------|
| **관리** | 완전 관리형 | 자체 운영 |
| **보존 기간** | 150일 (기본) | 무제한 |
| **비용 모델** | 샘플당 과금 | S3 스토리지 + 컴퓨팅 |
| **다운샘플링** | 자동 | 설정 필요 |
| **고가용성** | 내장 | Ruler, Store HA 설정 필요 |
| **멀티클러스터** | 네이티브 지원 | Sidecar/Receive 설정 필요 |
| **운영 복잡도** | 낮음 | 높음 |

### 4.5 멀티클러스터 Federation

```yaml
# prometheus-federation.yaml
prometheus:
  prometheusSpec:
    additionalScrapeConfigs:
      - job_name: 'federate-cluster-a'
        honor_labels: true
        metrics_path: '/federate'
        params:
          'match[]':
            - '{job=~".+"}'
        static_configs:
          - targets:
              - 'prometheus-cluster-a.example.com:9090'
        relabel_configs:
          - source_labels: [__address__]
            target_label: cluster
            replacement: cluster-a

      - job_name: 'federate-cluster-b'
        honor_labels: true
        metrics_path: '/federate'
        params:
          'match[]':
            - '{job=~".+"}'
        static_configs:
          - targets:
              - 'prometheus-cluster-b.example.com:9090'
        relabel_configs:
          - source_labels: [__address__]
            target_label: cluster
            replacement: cluster-b
```

---

## 5. Grafana 연동

### 5.1 데이터소스 프로비저닝

```yaml
# grafana-datasources.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
  labels:
    grafana_datasource: "1"
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      # Prometheus / AMP
      - name: Prometheus
        type: prometheus
        access: proxy
        url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/ws-xxxxxxxx
        jsonData:
          sigV4Auth: true
          sigV4Region: ap-northeast-2
          timeInterval: "15s"
        isDefault: true
        editable: false

      # Loki
      - name: Loki
        type: loki
        access: proxy
        url: http://loki-gateway.observability.svc:3100
        jsonData:
          maxLines: 1000
          timeout: 60
          derivedFields:
            - name: TraceID
              matcherRegex: '"trace_id":"([a-f0-9]+)"'
              url: '$${__value.raw}'
              datasourceUid: tempo
              urlDisplayLabel: "View Trace"
        editable: false

      # Tempo
      - name: Tempo
        type: tempo
        access: proxy
        url: http://tempo-query-frontend.observability.svc:3100
        uid: tempo
        jsonData:
          httpMethod: GET
          tracesToLogs:
            datasourceUid: loki
            tags:
              - service.name
              - namespace
            mapTagNamesEnabled: true
            mappedTags:
              - key: service.name
                value: app
            filterByTraceID: true
            filterBySpanID: false
            lokiSearch: true
          tracesToMetrics:
            datasourceUid: prometheus
            tags:
              - service.name
              - http.method
            queries:
              - name: Request rate
                query: sum(rate(http_requests_total{$$__tags}[5m]))
              - name: Error rate
                query: sum(rate(http_requests_total{$$__tags,status_code=~"5.."}[5m]))
          serviceMap:
            datasourceUid: prometheus
          nodeGraph:
            enabled: true
          search:
            hide: false
          lokiSearch:
            datasourceUid: loki
        editable: false
```

### 5.2 Loki → Tempo 연동 (Derived Fields)

Loki 데이터소스의 Derived Fields를 사용하여 로그에서 트레이스로 이동:

```yaml
# loki-derived-fields.yaml
jsonData:
  derivedFields:
    # JSON 로그에서 trace_id 추출
    - name: TraceID
      matcherRegex: '"trace_id":"([a-f0-9]{32})"'
      url: '$${__value.raw}'
      datasourceUid: tempo
      urlDisplayLabel: "View Trace"

    # 로그 형식: trace_id=xxxxx
    - name: TraceID_KeyValue
      matcherRegex: 'trace_id=([a-f0-9]{32})'
      url: '$${__value.raw}'
      datasourceUid: tempo
      urlDisplayLabel: "View Trace"

    # W3C Trace Context 형식
    - name: TraceID_W3C
      matcherRegex: 'traceparent: 00-([a-f0-9]{32})-'
      url: '$${__value.raw}'
      datasourceUid: tempo
      urlDisplayLabel: "View Trace"
```

### 5.3 Tempo → Loki 연동 (Trace to Logs)

```yaml
# tempo-trace-to-logs.yaml
jsonData:
  tracesToLogs:
    datasourceUid: loki
    # 태그 매핑
    tags:
      - service.name
      - namespace
      - pod
    # 태그 이름 변환
    mapTagNamesEnabled: true
    mappedTags:
      - key: service.name
        value: app
      - key: k8s.namespace.name
        value: namespace
    # 필터 옵션
    filterByTraceID: true
    filterBySpanID: false
    lokiSearch: true
    # 시간 범위 조정
    spanStartTimeShift: "-1h"
    spanEndTimeShift: "1h"
```

### 5.4 Exemplars 설정

Prometheus 메트릭에서 Tempo 트레이스로 연결:

```yaml
# prometheus-exemplars.yaml
prometheus:
  prometheusSpec:
    enableFeatures:
      - exemplar-storage

    # Exemplar 저장 설정
    exemplars:
      maxSize: 100000

# 애플리케이션에서 Exemplar 전송 (Micrometer)
# application.properties
management.metrics.distribution.percentiles-histogram.http.server.requests=true
management.prometheus.metrics.export.histogram-flavor=prometheus
```

애플리케이션 코드에서 Exemplar 추가:

```java
// Java - Micrometer with Prometheus
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.tracing.Tracer;

@Component
public class MetricsService {
    private final Timer requestTimer;
    private final Tracer tracer;

    public MetricsService(MeterRegistry registry, Tracer tracer) {
        this.tracer = tracer;
        this.requestTimer = Timer.builder("http_request_duration")
            .publishPercentileHistogram()
            .register(registry);
    }

    public void recordRequest(Runnable task) {
        requestTimer.record(task);
        // Exemplar는 자동으로 trace_id가 포함됨 (Micrometer Tracing 연동 시)
    }
}
```

### 5.5 대시보드 프로비저닝

```yaml
# grafana-dashboard-provisioning.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-config
  namespace: observability
  labels:
    grafana_dashboard: "1"
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
      - name: 'default'
        orgId: 1
        folder: 'Kubernetes'
        folderUid: 'kubernetes'
        type: file
        disableDeletion: false
        updateIntervalSeconds: 30
        options:
          path: /var/lib/grafana/dashboards/kubernetes

      - name: 'applications'
        orgId: 1
        folder: 'Applications'
        folderUid: 'applications'
        type: file
        disableDeletion: false
        options:
          path: /var/lib/grafana/dashboards/applications
```

---

## 관련 문서

- [모니터링 스택 기초](../observability/README.md)
- [로깅 스택 기초](../observability/logging/README.md)
- [관측성 최적화](../observability/09-observability-optimization.md)
- [리소스 최적화](./10-resource-optimization.md)

---

< [이전: 관측성 분석](./08-observability-analysis.md) | [목차](./README.md) | [다음: 리소스 최적화](./10-resource-optimization.md) >
