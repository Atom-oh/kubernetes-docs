# 로깅 스택 퀴즈

이 퀴즈는 Kubernetes 로깅 스택 (Grafana Loki, Grafana Tempo)에 대한 이해도를 테스트합니다.

## 객관식 문제

1. Grafana Loki의 인덱싱 방식으로 올바른 것은?
   - A) 모든 로그 내용을 전문(full-text) 인덱싱한다
   - B) 레이블(메타데이터)만 인덱싱하고 로그 내용은 인덱싱하지 않는다
   - C) 로그의 첫 100자만 인덱싱한다
   - D) 정규표현식 패턴 매칭으로 인덱싱한다

<details>

<summary>정답 보기</summary>

**정답: B) 레이블(메타데이터)만 인덱싱하고 로그 내용은 인덱싱하지 않는다**

**설명:**
Loki는 Prometheus에서 영감을 받은 "레이블 기반 인덱싱" 방식을 사용합니다. 로그 내용 자체는 인덱싱하지 않고, 레이블(namespace, pod, container 등)만 인덱싱합니다. 로그 내용은 압축된 청크(chunk)로 저장되며, 쿼리 시 레이블로 필터링한 후 해당 청크를 스캔합니다. 이 방식은 Elasticsearch 같은 전문 인덱싱에 비해 인덱스 크기가 작아 비용이 절감되지만, 로그 내용 검색 시 더 많은 데이터를 스캔해야 할 수 있습니다.
</details>

2. Grafana Tempo가 다른 분산 추적 시스템(Jaeger, Zipkin)과 다른 점은?
   - A) 추적 데이터를 실시간으로 분석한다
   - B) 추적 데이터를 인덱싱하지 않고 TraceID로만 검색한다
   - C) 오직 OpenTelemetry 형식만 지원한다
   - D) 메모리에만 데이터를 저장한다

<details>

<summary>정답 보기</summary>

**정답: B) 추적 데이터를 인덱싱하지 않고 TraceID로만 검색한다**

**설명:**
Tempo의 핵심 설계 철학은 "인덱스 없는 분산 추적"입니다. 추적 데이터를 인덱싱하지 않고 오브젝트 스토리지(S3, GCS 등)에 직접 저장하며, TraceID를 알고 있을 때만 검색이 가능합니다. 이 접근 방식은 운영 복잡성과 비용을 크게 줄입니다. 서비스 이름이나 태그로 추적을 검색하려면 Grafana의 TraceQL이나 로그/메트릭과의 연계를 통해 TraceID를 먼저 찾아야 합니다.
</details>

3. Promtail의 주요 역할로 올바른 것은?
   - A) 메트릭을 수집하여 Prometheus로 전송
   - B) 로그 파일을 읽어 Loki로 전송
   - C) 분산 추적 데이터를 수집하여 Tempo로 전송
   - D) Kubernetes 이벤트를 모니터링

<details>

<summary>정답 보기</summary>

**정답: B) 로그 파일을 읽어 Loki로 전송**

**설명:**
Promtail은 Loki를 위한 로그 수집 에이전트입니다. Kubernetes 환경에서 DaemonSet으로 배포되어 각 노드의 컨테이너 로그 파일(/var/log/pods/)을 tail하고, Kubernetes 메타데이터(namespace, pod, container 레이블)를 추가하여 Loki로 전송합니다. 또한 pipeline stages를 통해 로그 파싱, 필터링, 레이블 추가 등의 처리를 수행할 수 있습니다.
</details>

4. LogQL에서 로그 내용에 "error"가 포함된 라인을 필터링하는 올바른 문법은?
   - A) {namespace="default"} where "error"
   - B) {namespace="default"} |= "error"
   - C) {namespace="default"} LIKE "error"
   - D) {namespace="default"} contains("error")

<details>

<summary>정답 보기</summary>

**정답: B) {namespace="default"} |= "error"**

**설명:**
LogQL에서 `|=`는 로그 라인에 지정된 문자열이 포함된 라인을 필터링하는 연산자입니다. 반대로 `!=`는 해당 문자열이 포함되지 않은 라인을 선택합니다. 정규표현식을 사용할 때는 `|~` (포함)와 `!~` (미포함)를 사용합니다. 예: `{namespace="default"} |~ "error|warn"`. 이 필터링은 레이블 선택 후 로그 청크를 스캔하여 수행됩니다.
</details>

5. Loki의 Distributor 컴포넌트의 역할은?
   - A) 로그 데이터를 장기 저장소에 보관
   - B) 클라이언트의 로그를 수신하고 유효성 검사 후 Ingester로 분배
   - C) 사용자 쿼리를 처리하고 결과를 반환
   - D) 저장된 로그를 압축하고 최적화

<details>

<summary>정답 보기</summary>

**정답: B) 클라이언트의 로그를 수신하고 유효성 검사 후 Ingester로 분배**

**설명:**
Loki의 Distributor는 Promtail 등의 클라이언트로부터 로그 스트림을 수신하는 첫 번째 컴포넌트입니다. 수신된 로그의 유효성을 검사하고(레이블 형식, 타임스탬프 등), 해싱을 통해 적절한 Ingester 인스턴스로 분배합니다. 이 분배는 일관된 해싱을 사용하여 같은 로그 스트림이 항상 같은 Ingester로 전달되도록 보장합니다.
</details>

6. OpenTelemetry Collector가 지원하는 텔레메트리 신호 유형으로 올바른 것은?
   - A) 로그만
   - B) 메트릭만
   - C) 트레이스만
   - D) 로그, 메트릭, 트레이스 모두

<details>

<summary>정답 보기</summary>

**정답: D) 로그, 메트릭, 트레이스 모두**

**설명:**
OpenTelemetry Collector는 벤더 중립적인 텔레메트리 데이터 수집기로, 세 가지 핵심 신호 유형인 로그(Logs), 메트릭(Metrics), 트레이스(Traces)를 모두 수집, 처리, 내보내기할 수 있습니다. Collector는 다양한 형식(OTLP, Jaeger, Zipkin, Prometheus 등)의 데이터를 수신하고, 여러 백엔드(Loki, Tempo, Prometheus, 상용 APM 등)로 내보낼 수 있어 관찰성 파이프라인의 허브 역할을 합니다.
</details>

7. Loki에서 청크(Chunk)의 역할과 특성으로 올바른 것은?
   - A) 실시간 로그 스트리밍을 위한 메모리 버퍼
   - B) 로그 데이터를 압축하여 저장하는 기본 단위
   - C) 인덱스 메타데이터를 저장하는 구조체
   - D) 쿼리 결과를 캐싱하는 임시 저장소

<details>

<summary>정답 보기</summary>

**정답: B) 로그 데이터를 압축하여 저장하는 기본 단위**

**설명:**
Loki의 청크(Chunk)는 같은 레이블 셋을 가진 로그 라인들을 묶어 압축 저장하는 기본 단위입니다. Ingester는 로그를 메모리에 버퍼링하다가 일정 크기나 시간이 되면 청크를 생성하고 오브젝트 스토리지에 저장합니다. 청크는 gzip, snappy, lz4 등으로 압축되어 저장 비용을 줄입니다. Compactor는 이후 작은 청크들을 더 큰 청크로 병합하여 쿼리 효율성을 높입니다.
</details>

8. Tempo에서 지원하는 수신 프로토콜이 아닌 것은?
   - A) Jaeger Thrift
   - B) Zipkin JSON
   - C) OpenTelemetry Protocol (OTLP)
   - D) Prometheus Remote Write

<details>

<summary>정답 보기</summary>

**정답: D) Prometheus Remote Write**

**설명:**
Prometheus Remote Write는 메트릭 데이터를 전송하는 프로토콜로, 추적(Tracing) 시스템인 Tempo에서는 사용되지 않습니다. Tempo는 분산 추적 데이터를 수신하기 위해 Jaeger(Thrift, gRPC), Zipkin(JSON, Thrift), OTLP(gRPC, HTTP)를 지원합니다. 이 다양한 프로토콜 지원 덕분에 기존 Jaeger나 Zipkin 환경에서 Tempo로 쉽게 마이그레이션할 수 있습니다.
</details>

## 단답형 문제

9. Loki에서 레이블 카디널리티(cardinality)를 낮게 유지해야 하는 이유를 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
레이블 카디널리티가 높으면 인덱스 크기가 증가하고, 쿼리 성능이 저하되며, 메모리 사용량이 급격히 증가합니다.

**설명:**
Loki는 레이블 조합마다 별도의 로그 스트림을 생성합니다. 예를 들어 user_id나 request_id처럼 고유 값이 많은 필드를 레이블로 사용하면 수백만 개의 스트림이 생성될 수 있습니다. 이는 인덱스 크기 폭증, Ingester 메모리 부족, 쿼리 시 많은 청크 스캔으로 이어집니다. 권장 사항은 namespace, pod, container, app, env 같은 낮은 카디널리티 레이블만 사용하고, 고유 식별자는 로그 내용에 포함시켜 LogQL로 필터링하는 것입니다.
</details>

10. trace-to-log 상관관계(correlation)를 구현하는 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
애플리케이션 로그에 TraceID를 포함시키고, Grafana에서 Tempo 데이터 소스와 Loki 데이터 소스를 연결하여 TraceID로 로그를 조회합니다.

**설명:**
trace-to-log 상관관계 구현 단계:
1. **애플리케이션 계측**: 로그 출력 시 현재 스팬의 TraceID를 포함 (예: `logger.info("Processing request", trace_id=span.context.trace_id)`)
2. **Grafana 데이터 소스 설정**: Tempo 데이터 소스 설정에서 "Trace to logs" 섹션에 Loki 데이터 소스를 연결하고, TraceID 필드명을 지정
3. **LogQL 쿼리 템플릿**: `{app="myapp"} | json | trace_id="${__span.traceId}"`
4. 이렇게 설정하면 Grafana에서 추적을 볼 때 관련 로그로 바로 이동할 수 있습니다.
</details>

11. Loki의 retention(보존 기간) 정책을 설정하는 두 가지 방법을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
1. **전역 보존 기간**: `limits_config.retention_period`로 모든 로그에 적용되는 기본 보존 기간 설정
2. **스트림별 보존 기간**: `limits_config.retention_stream`으로 특정 레이블 셀렉터에 대해 다른 보존 기간 설정

**설명:**
Loki의 보존 정책 설정 예시:
```yaml
limits_config:
  retention_period: 720h  # 30일 기본 보존
  retention_stream:
  - selector: '{namespace="production"}'
    priority: 1
    period: 2160h  # 90일 보존
  - selector: '{level="debug"}'
    priority: 2
    period: 168h   # 7일 보존
```
Compactor가 이 정책에 따라 만료된 청크를 삭제합니다. compactor.retention_enabled: true 설정이 필요합니다. 스트림별 보존을 통해 중요한 프로덕션 로그는 오래 보관하고, 디버그 로그는 빨리 삭제하여 비용을 최적화할 수 있습니다.
</details>

12. Grafana Alloy(구 Grafana Agent)가 Promtail 대비 제공하는 이점을 설명하세요.

<details>

<summary>정답 보기</summary>

**정답:**
Grafana Alloy는 로그, 메트릭, 추적을 하나의 에이전트로 통합 수집할 수 있어 배포 복잡성을 줄이고 리소스를 절약합니다.

**설명:**
Grafana Alloy의 주요 이점:
1. **통합 수집**: Promtail(로그) + Prometheus Agent(메트릭) + OpenTelemetry Collector(추적)의 기능을 단일 바이너리로 제공
2. **동적 구성**: River 구성 언어로 파이프라인을 유연하게 정의
3. **자동 상관관계**: 같은 에이전트에서 수집되므로 trace_id, span_id를 자동으로 연결 가능
4. **리소스 효율**: 여러 에이전트 대신 하나만 실행하여 메모리/CPU 절약
5. **커뮤니티 통합**: OpenTelemetry 생태계와 더 밀접하게 통합
</details>

## 실습 문제

13. production 네임스페이스에서 error 레벨 로그를 검색하고, 5분간 앱별 에러 수를 집계하는 LogQL 쿼리를 작성하세요.

<details>

<summary>정답 보기</summary>

**정답:**
```logql
# 에러 로그 검색
{namespace="production"} | json | level="error"

# 5분간 앱별 에러 수 집계 (메트릭 쿼리)
sum by (app) (
  count_over_time(
    {namespace="production"} | json | level="error" [5m]
  )
)

# 또는 rate 사용 (초당 에러 수)
sum by (app) (
  rate(
    {namespace="production"} |= "error" [5m]
  )
)
```

**설명:**
LogQL은 두 가지 유형의 쿼리를 지원합니다:
1. **로그 쿼리**: 로그 라인을 반환 (예: 첫 번째 쿼리)
2. **메트릭 쿼리**: 로그에서 메트릭을 계산 (예: count_over_time, rate)

`| json`은 JSON 형식 로그를 파싱하여 필드를 레이블로 추출합니다. `level="error"`는 파싱된 level 필드로 필터링합니다. `count_over_time`은 지정된 기간 동안 로그 라인 수를 집계하고, `sum by (app)`으로 앱별로 그룹화합니다.
</details>

14. Tempo의 기본 구성 파일을 작성하세요. (OTLP gRPC 수신, S3 스토리지, 7일 보존)

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tempo-config
  namespace: tracing
data:
  tempo.yaml: |
    server:
      http_listen_port: 3200
      grpc_listen_port: 9095

    distributor:
      receivers:
        otlp:
          protocols:
            grpc:
              endpoint: 0.0.0.0:4317
            http:
              endpoint: 0.0.0.0:4318
        jaeger:
          protocols:
            grpc:
              endpoint: 0.0.0.0:14250
            thrift_http:
              endpoint: 0.0.0.0:14268

    ingester:
      trace_idle_period: 10s
      max_block_bytes: 1000000
      max_block_duration: 5m

    compactor:
      compaction:
        compaction_window: 1h
        max_block_bytes: 100000000
        block_retention: 168h  # 7일
        compacted_block_retention: 1h

    storage:
      trace:
        backend: s3
        s3:
          bucket: tempo-traces
          endpoint: s3.amazonaws.com
          region: ap-northeast-2
          access_key: ${AWS_ACCESS_KEY_ID}
          secret_key: ${AWS_SECRET_ACCESS_KEY}
        wal:
          path: /var/tempo/wal
        local:
          path: /var/tempo/blocks

    querier:
      frontend_worker:
        frontend_address: tempo-query-frontend:9095
```

**설명:**
Tempo 구성의 핵심 요소:
- **distributor.receivers**: 지원할 추적 프로토콜 정의 (OTLP, Jaeger 등)
- **ingester**: 추적 데이터를 메모리에 버퍼링하는 설정 (idle_period 동안 새 스팬이 없으면 블록 플러시)
- **compactor.block_retention**: 추적 데이터 보존 기간 (168h = 7일)
- **storage.trace.backend**: 백엔드 스토리지 타입 (s3, gcs, azure, local)
- WAL(Write-Ahead Log)은 인제스터 재시작 시 데이터 손실 방지를 위해 로컬에 저장
</details>

15. Promtail에서 JSON 로그를 파싱하고 레이블을 추가하는 pipeline_stages 설정을 작성하세요. (timestamp, level, message 필드 추출)

<details>

<summary>정답 보기</summary>

**정답:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: logging
data:
  promtail.yaml: |
    server:
      http_listen_port: 3101
      grpc_listen_port: 0

    positions:
      filename: /tmp/positions.yaml

    clients:
      - url: http://loki-gateway:3100/loki/api/v1/push

    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            target_label: app
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_container_name]
            target_label: container
        pipeline_stages:
          # JSON 파싱
          - json:
              expressions:
                timestamp: timestamp
                level: level
                message: message
                trace_id: trace_id

          # timestamp 필드를 로그 타임스탬프로 사용
          - timestamp:
              source: timestamp
              format: RFC3339Nano
              fallback_formats:
                - RFC3339
                - "2006-01-02T15:04:05.000Z"

          # level을 레이블로 추가
          - labels:
              level:
              trace_id:

          # message를 로그 라인으로 사용
          - output:
              source: message

          # debug 레벨 로그 드롭 (옵션)
          - match:
              selector: '{level="debug"}'
              stages:
                - drop:
                    expression: ".*"
```

**설명:**
Promtail의 pipeline_stages는 순차적으로 실행됩니다:
1. **json**: JSON 로그를 파싱하여 필드를 추출합니다
2. **timestamp**: 추출된 timestamp를 Loki 로그의 타임스탬프로 설정합니다 (기본값은 수집 시간)
3. **labels**: 추출된 필드를 Loki 레이블로 추가합니다 (주의: 고카디널리티 필드는 피해야 함)
4. **output**: 지정된 필드를 로그 라인으로 사용합니다 (전체 JSON 대신 message만)
5. **match + drop**: 특정 조건의 로그를 버릴 수 있습니다

trace_id를 레이블로 추가하면 Grafana에서 trace-to-log 연동이 쉬워지지만, 고유 값이므로 카디널리티가 높아질 수 있어 주의가 필요합니다.
</details>

---

**점수 계산:**
- 13-15개 정답: 우수 (로깅 스택 전문가 수준)
- 10-12개 정답: 양호 (실무 적용 가능)
- 7-9개 정답: 보통 (추가 학습 권장)
- 4-6개 정답: 기초 (기본 개념 복습 필요)
- 0-3개 정답: 미흡 (전체 내용 재학습 필요)
