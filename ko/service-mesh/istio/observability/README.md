# Observability

> **지원 버전**: Istio 1.31
> **검토일**: 2026년 9월 11일

Istio 프록시는 관측한 트래픽의 텔레메트리를 생성합니다. 메트릭 스크레이프, access log, 추적 제공자와 저장소를 구성해야 합니다. Span을 연결하려면 애플리케이션이 수신·송신 요청 사이에 trace context를 전파해야 하며 애플리케이션 내부 span과 예외는 별도 계측·로깅이 필요합니다.

## 목차

1. [관찰성 개요](#관찰성-개요)
2. [Three Pillars of Observability](#three-pillars-of-observability)
3. [관찰성 아키텍처](#관찰성-아키텍처)
4. [Golden Signals](#golden-signals)
5. [상세 문서](#상세-문서)
6. [관찰성 베스트 프랙티스](#관찰성-베스트-프랙티스)
7. [다음 단계](#다음-단계)

## 관찰성 개요

<p align="center">
  <img src="https://istio.io/latest/docs/tasks/observability/metrics/using-istio-dashboard/grafana-istio-dashboard.png" alt="Istio Observability Dashboard" width="900">
</p>

사이드카·waypoint는 애플리케이션에 프록시 계측 코드를 추가하지 않고 HTTP 메트릭·span·access log를 제공할 수 있습니다. Ambient ztunnel은 L4 텔레메트리를 제공하며 HTTP 관측에는 waypoint가 필요합니다. CPU·메모리·호스트 패킷 메트릭은 Istio 요청 메트릭이 아닌 Kubernetes·노드 exporter에서 수집합니다. 위 화면은 구성된 대시보드 예시이며 Istio가 자동 설치하는 구성 요소가 아닙니다.

## Three Pillars of Observability

### 관찰성의 3요소

![Envoy 사이드카가 만든 메트릭·Span·Access Log가 각각 Prometheus, Jaeger/Zipkin, Loki에 수집된 뒤 Grafana 대시보드·Kiali 토폴로지·Alertmanager 알림으로 구성된 통합 관찰성 계층으로 모이는 관찰성의 3요소 구조를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-observability-readme-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-observability-readme-0.html)

### 1. 메트릭 (Metrics)

**무엇을 측정하는가?**
- 요청 수, 응답 시간, 에러율
- 리소스 사용률 (CPU, 메모리)
- 네트워크 트래픽 (Bytes, Packets)

**언제 사용하는가?**
- 시스템 건강 상태 모니터링
- SLO/SLI 추적
- 용량 계획

**주요 도구**: Prometheus, Grafana, VictoriaMetrics

### 2. 분산 추적 (Distributed Tracing)

**무엇을 추적하는가?**
- 단일 요청의 전체 경로
- 각 서비스의 처리 시간
- 서비스 간 의존성

**언제 사용하는가?**
- 성능 병목 식별
- 장애 근본 원인 분석
- 마이크로서비스 디버깅

**주요 도구**: Jaeger, Zipkin, Grafana Tempo

### 3. 로깅 (Logging)

**무엇을 기록하는가?**
- 설정한 HTTP access 메타데이터(전체 요청·응답 본문이 아님)
- 프록시 오류(애플리케이션 예외는 애플리케이션 로그 필요)
- 보안 이벤트

**언제 사용하는가?**
- 상세 디버깅
- 보안 감사
- 규정 준수

**주요 도구**: Grafana Loki, Elasticsearch, Fluentd

## 관찰성 아키텍처

### 전체 아키텍처

![Envoy 사이드카가 있는 Pod의 메트릭·트레이스·액세스 로그가 Prometheus, Jaeger, Fluentd/Loki 백엔드로 흘러가 Grafana와 Kiali에서 시각화되고, istiod가 사이드카에 텔레메트리 설정을 전파하는 Istio 관찰성 아키텍처를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-observability-readme-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-observability-readme-1.html)

### 데이터 흐름

**1. 메트릭 수집 흐름**:
```
App → Envoy (메트릭 생성)
    → Prometheus (Scrape /stats/prometheus)
    → Grafana (시각화)
```

**2. 분산 추적 흐름**:
```
App의 context 전파 → Envoy span 생성
    → 설정한 수집기·프로토콜(예: OpenTelemetry/OTLP)
    → 선택한 백엔드: Jaeger, Zipkin 또는 Tempo
    → 백엔드 UI 또는 설정한 Grafana datasource
```

**3. 로깅 흐름**:
```
App → Envoy (Access Log 생성)
    → Fluentd/Fluent Bit (로그 수집)
    → Loki (로그 저장)
    → Grafana (로그 쿼리 및 시각화)
```

## Golden Signals

Google SRE 원칙의 핵심 신호입니다. HTTP 쿼리는 같은 메시 홉의 송신·수신 관측을 중복 집계하지 않도록 `reporter="destination"`을 선택합니다. 이는 서비스 홉 수치이며 고유 사용자 트랜잭션 수가 아닙니다. 수신 reporter가 없는 외부·게이트웨이 트래픽은 별도로 분석하고 gRPC 오류는 `grpc_response_status`도 확인합니다. 아래 지연 단위는 밀리초입니다.

### 1. Latency (지연시간)

```promql
# P50 레이턴시
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)

# P95 레이턴시
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)

# P99 레이턴시
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])) by (le)
)
```

### 2. Traffic (트래픽)

```promql
# 초당 요청 수 (RPS)
sum(rate(istio_requests_total{reporter="destination"}[5m]))

# 서비스별 트래픽
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service)
```

### 3. Errors (에러)

```promql
# 에러율 (%)
sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))
* 100

# 4xx vs 5xx 에러
sum(rate(istio_requests_total{reporter="destination",response_code=~"4.."}[5m])) by (response_code)
sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) by (response_code)
```

### 4. Saturation (포화도)

```promql
# CPU consumption in cores (not percent), one series per application container.
sum by (namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m])
)

# Memory working set / configured limit (%); containers without limits omitted.
100 * max by (namespace, pod, container) (
  container_memory_working_set_bytes{container!="",container!="POD"}
)
/ on (namespace, pod, container)
(max by (namespace, pod, container) (
  kube_pod_container_resource_limits{resource="memory",unit="byte"}
) > 0)
```

이 쿼리는 kubelet/cAdvisor와 kube-state-metrics 스크레이프가 필요하며 Istio 메트릭이 아닙니다. 중복 스크레이프 대상을 피하고 멀티 클러스터 집계에는 cluster 레이블도 포함합니다. 제한 대비 사용량 외에 throttling·대기열·미처리 작업도 확인합니다.



## 관찰성 베스트 프랙티스

### 1. 표준 메트릭 활용

✅ **권장**:
- Istio 표준 메트릭을 우선 활용
- 커스텀 메트릭은 필요시에만 추가
- 라벨은 카디널리티를 고려하여 최소화

❌ **지양**:
- 불필요한 커스텀 메트릭 남발
- 높은 카디널리티 라벨 (user_id, request_id 등)

### 2. Trace Sampling

프로덕션 환경에서는 적절한 샘플링 비율 설정:

아래 주소의 OTLP collector Service와 선택한 백엔드로의 export 설정이 먼저 필요합니다. 제공자를 기존 설치 설정에 병합한 뒤 Telemetry API로 샘플링을 구성합니다:

```yaml
# istioctl install -f input, not kubectl apply
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: otel
    randomSamplingPercentage: 1.0
```

`1.0`은 100%가 아닌 **1%**입니다. 트래픽량·조사 목적·수집기와 백엔드 용량에 맞춰 선택합니다. 작은 테스트 환경은 100%를 사용할 수 있지만 운영의 낮은 비율도 유효성을 검증해야 합니다. Context 전파는 여전히 필요합니다. 같은 네임스페이스에 selector 없는 Telemetry를 둘 이상 생성하지 말고 아래 로깅 예제와 함께 사용할 때는 하나에 병합합니다.

### 3. Access Log 최적화

다음은 필드가 아니라 요청을 필터링합니다. 필드 선택·마스킹은 access-log 제공자에 구성합니다. 이 HTTP 필터는 성공 요청을 생략하므로 전체 접근 감사 기록으로 사용할 수 없습니다:

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-default
  namespace: istio-system
spec:
  accessLogging:
  - providers:
    - name: envoy
    filter:
      expression: response.code >= 400  # 에러만 기록
```

### 4. 메트릭 보관 정책

운영 필요·저장 비용·실제 보존 요구에 맞춰 조정할 예시 범위입니다(규정의 기본값이 아님):
- **실시간 메트릭**: 1-7일 (고해상도)
- **장기 메트릭**: 30-90일 (다운샘플링)
- **트레이스**: 7-30일
- **로그**: 실제 보존 정책으로 결정하며 30–365일은 예시일 뿐입니다

Prometheus 로컬 TSDB는 오래된 데이터를 자동 다운샘플링하지 않습니다. 필요하면 다운샘플링·장기 저장을 지원하는 백엔드를 명시적으로 구성합니다.

### 5. 알림 설정

아래 임계치는 예시입니다. 서비스 SLO와 지속적인 오류 예산 소진을 기준으로 하고 최소 트래픽 조건을 두어 불필요한 알림을 줄입니다.

**Critical Alerts** (즉시 대응):
- 에러율 > 5%
- P99 레이턴시 > 임계값
- 서비스 다운

**Warning Alerts** (모니터링):
- 에러율 > 1%
- P95 레이턴시 증가
- 리소스 사용률 > 80%

## 상세 문서

관찰성의 각 영역에 대한 상세 가이드:

### 1. 메트릭 (Metrics)

**[메트릭 가이드](01-metrics.md)**에서 다음을 학습합니다:
- Istio 표준 메트릭
- Prometheus 통합
- OpenTelemetry 통합
- 커스텀 메트릭 추가
- 메트릭 최적화

**주요 내용**:
- `istio_requests_total`: 총 요청 수
- `istio_request_duration_milliseconds`: 요청 지연시간
- `istio_request_bytes` / `istio_response_bytes`: 요청 / 응답 크기 히스토그램
- Circuit Breaker 메트릭
- Telemetry API 커스터마이징

### 2. 분산 추적 (Distributed Tracing)

**[분산 추적 가이드](02-tracing.md)**에서 다음을 학습합니다:
- Jaeger 통합
- Zipkin 통합
- 트레이스 샘플링
- 컨텍스트 전파
- 성능 분석

**주요 내용**:
- Trace Context 전파 (W3C Trace Context)
- Span 생성 및 관리
- 백엔드 선택 (Jaeger, Zipkin, Tempo)
- 샘플링 전략
- 트레이스 분석

### 3. 로깅 (Logging)

**[로깅 가이드](03-logging.md)**에서 다음을 학습합니다:
- Access Log 설정
- 로그 포맷 커스터마이징
- Grafana Loki 통합
- 로그 필터링
- 로그 집계

**주요 내용**:
- Envoy Access Log 형식
- JSON 구조화 로그
- 로그 레벨 설정
- 로그 수집 (Fluentd, Fluent Bit)
- 로그 쿼리 (LogQL)

### 4. 대시보드 (Dashboards)

**[대시보드 가이드](04-dashboards.md)**에서 다음을 학습합니다:
- Grafana 대시보드
- Kiali 서비스 그래프
- 커스텀 대시보드 생성
- 알림 규칙 설정

**주요 내용**:
- Istio 표준 대시보드
- Service Mesh 대시보드
- Workload 대시보드
- Kiali 트래픽 시각화
- SLO 대시보드

## 다음 단계

1. **[메트릭](01-metrics.md)**: Prometheus 메트릭 수집 및 쿼리
2. **[분산 추적](02-tracing.md)**: Jaeger/Zipkin 트레이스 분석
3. **[로깅](03-logging.md)**: Access Log 및 Loki 통합
4. **[대시보드](04-dashboards.md)**: Grafana 및 Kiali 대시보드

## 참고 자료

### 공식 문서
- [Istio Observability](https://istio.io/latest/docs/tasks/observability/)
- [Metrics](https://istio.io/latest/docs/tasks/observability/metrics/)
- [Distributed Tracing](https://istio.io/latest/docs/tasks/observability/distributed-tracing/)
- [Logs](https://istio.io/latest/docs/tasks/observability/logs/)

### 관련 프로젝트
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Jaeger](https://www.jaegertracing.io/)
- [Grafana Loki](https://grafana.com/oss/loki/)
- [Kiali](https://kiali.io/)

### 표준 및 사양
- [OpenTelemetry](https://opentelemetry.io/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Google SRE - Golden Signals](https://sre.google/sre-book/monitoring-distributed-systems/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [Istio Observability 퀴즈](../../../quizzes/service-mesh/istio/observability.md)를 풀어보세요.
