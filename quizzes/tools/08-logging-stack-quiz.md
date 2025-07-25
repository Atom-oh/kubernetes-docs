# 로깅 스택 퀴즈

이 퀴즈는 Kubernetes 로깅 스택 (Loki, Tempo)에 대한 이해도를 테스트합니다.

## 문제 1: 로깅 스택 구성 요소

<details>
<summary>Kubernetes 로깅 스택의 주요 구성 요소와 역할은?</summary>

**답변:**
- **Grafana Loki**: 로그 집계 및 저장 시스템
- **Grafana Tempo**: 분산 추적 백엔드
- **Promtail**: 로그 수집 에이전트
- **Grafana**: 로그 및 추적 데이터 시각화
- **OpenTelemetry Collector**: 추적 데이터 수집 및 처리
- **Jaeger**: 분산 추적 시스템 (대안)
- **Fluentd/Fluent Bit**: 로그 수집 및 전송 (대안)
</details>

## 문제 2: Loki vs Elasticsearch

<details>
<summary>Grafana Loki가 Elasticsearch보다 나은 점은?</summary>

**답변:**
**Loki 장점:**
- **비용 효율성**: 로그 내용 대신 메타데이터만 인덱싱
- **Prometheus 호환성**: 동일한 레이블 기반 접근 방식
- **간단한 운영**: 복잡한 클러스터 관리 불필요
- **압축 효율성**: 더 나은 스토리지 압축
- **LogQL**: Prometheus PromQL과 유사한 쿼리 언어
- **수평 확장**: 마이크로서비스 아키텍처
- **클라우드 네이티브**: Kubernetes 환경에 최적화
</details>

## 문제 3: Promtail 구성

<details>
<summary>Promtail을 사용한 로그 수집 구성 예시는?</summary>

**답변:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
data:
  config.yml: |
    server:
      http_listen_port: 3101
      grpc_listen_port: 0

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki:3100/loki/api/v1/push

    scrape_configs:
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
        - role: pod
      pipeline_stages:
        - docker: {}
      relabel_configs:
        - source_labels:
            - __meta_kubernetes_pod_controller_name
          regex: ([0-9a-z-.]+?)(-[0-9a-f]{8,10})?
          action: replace
          target_label: __tmp_controller_name
        - source_labels:
            - __meta_kubernetes_pod_label_app_kubernetes_io_name
            - __meta_kubernetes_pod_label_app
            - __tmp_controller_name
            - __meta_kubernetes_pod_name
          regex: ^;*([^;]+)(;.*)?$
          action: replace
          target_label: app
        - source_labels:
            - __meta_kubernetes_pod_label_app_kubernetes_io_instance
            - __meta_kubernetes_pod_label_release
          regex: ^;*([^;]+)(;.*)?$
          action: replace
          target_label: instance
        - action: replace
          source_labels:
          - __meta_kubernetes_namespace
          target_label: namespace
        - action: replace
          source_labels:
          - __meta_kubernetes_pod_name
          target_label: pod
```
</details>

## 문제 4: LogQL 쿼리

<details>
<summary>Loki에서 사용하는 LogQL 쿼리 예시는?</summary>

**답변:**
```logql
# 기본 로그 스트림 선택
{namespace="default", app="nginx"}

# 정규식을 사용한 필터링
{namespace="default"} |= "error" |~ ".*timeout.*"

# JSON 로그 파싱
{namespace="default"} | json | level="error"

# 메트릭 쿼리 - 로그 라인 수
count_over_time({namespace="default"}[5m])

# 메트릭 쿼리 - 에러율
sum(rate({namespace="default"} |= "error" [5m])) by (app)
/
sum(rate({namespace="default"}[5m])) by (app)

# 로그 패턴 추출
{namespace="default"} 
| pattern `<timestamp> <level> <message>`
| level = "ERROR"

# 라벨 필터와 라인 필터 조합
{namespace=~"prod-.*", app="api"} 
|= "POST" 
|= "/users" 
| json 
| status_code >= 400
```
</details>

## 문제 5: Tempo 분산 추적

<details>
<summary>Grafana Tempo를 사용한 분산 추적 구성은?</summary>

**답변:**
```yaml
# Tempo 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: tempo-config
data:
  tempo.yaml: |
    server:
      http_listen_port: 3200
      grpc_listen_port: 9095

    distributor:
      receivers:
        jaeger:
          protocols:
            thrift_http:
              endpoint: 0.0.0.0:14268
            grpc:
              endpoint: 0.0.0.0:14250
        zipkin:
          endpoint: 0.0.0.0:9411
        otlp:
          protocols:
            http:
              endpoint: 0.0.0.0:4318
            grpc:
              endpoint: 0.0.0.0:4317

    ingester:
      trace_idle_period: 10s
      max_block_bytes: 1_000_000
      max_block_duration: 5m

    compactor:
      compaction:
        compaction_window: 1h
        max_block_bytes: 100_000_000
        block_retention: 1h
        compacted_block_retention: 10m

    storage:
      trace:
        backend: s3
        s3:
          bucket: tempo-traces
          endpoint: s3.amazonaws.com
          region: us-west-2

---
# OpenTelemetry Collector 구성
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
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

    exporters:
      otlp:
        endpoint: tempo:4317
        tls:
          insecure: true

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp]
```
</details>

## 문제 6: 통합 관찰성

<details>
<summary>로그, 메트릭, 추적을 통합하여 관찰성을 구현하는 방법은?</summary>

**답변:**
1. **상관 관계 설정**:
   ```yaml
   # 공통 레이블 사용
   labels:
     app: "my-service"
     version: "v1.0.0"
     environment: "production"
   ```

2. **TraceID 연결**:
   ```logql
   # 로그에서 TraceID로 추적 데이터 연결
   {namespace="default"} | json | trace_id="abc123"
   ```

3. **Grafana 대시보드 통합**:
   ```json
   {
     "panels": [
       {
         "title": "Application Metrics",
         "type": "graph",
         "datasource": "Prometheus"
       },
       {
         "title": "Application Logs", 
         "type": "logs",
         "datasource": "Loki"
       },
       {
         "title": "Distributed Traces",
         "type": "traces",
         "datasource": "Tempo"
       }
     ]
   }
   ```

4. **알림 통합**:
   ```yaml
   # Prometheus 알림에서 로그 링크 포함
   annotations:
     logs_url: "https://grafana.com/explore?left=%5B%22now-1h%22,%22now%22,%22Loki%22,%7B%22expr%22:%22%7Bnamespace%3D%5C%22{{ $labels.namespace }}%5C%22%7D%22%7D%5D"
   ```

5. **애플리케이션 계측**:
   ```go
   // Go 애플리케이션 예시
   import (
     "go.opentelemetry.io/otel"
     "go.opentelemetry.io/otel/trace"
   )
   
   tracer := otel.Tracer("my-service")
   ctx, span := tracer.Start(ctx, "operation")
   defer span.End()
   
   // 로그에 TraceID 포함
   logger.Info("Processing request", 
     "trace_id", span.SpanContext().TraceID().String())
   ```
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (로깅 스택 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)
