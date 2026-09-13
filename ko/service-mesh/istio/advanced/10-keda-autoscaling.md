# KEDA를 활용한 Istio 메트릭 기반 오토스케일링

> **검증 기준**: KEDA/chart 2.20.2, Istio 1.31.0, Kubernetes 1.32–1.36
> **마지막 검토**: 2026년 9월 11일

이 가이드는 scaling signal과 제약을 설명하며 기존 workload·검증된 metric·충분한 cluster 용량을 가정합니다. 같은 Deployment를 대상으로 하는 예제는 **대안 관계**입니다. 모든 객체를 적용하지 말고 target마다 하나의 ScaledObject/HPA 관리자를 선택하세요.

## 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [Prometheus 메트릭 기반 스케일링](#prometheus-메트릭-기반-스케일링)
4. [CloudWatch 메트릭 기반 스케일링](#cloudwatch-메트릭-기반-스케일링)
5. [실전 스케일링 전략](#실전-스케일링-전략)
6. [모범 사례](#모범-사례)
7. [문제 해결](#문제-해결)
8. [참고: KEDA 설치](#참고-keda-설치)

## 개요

Kubernetes HPA는 해당 API를 통해 resource·custom·external metric과 다중 metric을 지원합니다. CloudWatch도 adapter로 연결할 수 있으므로 HPA에서 원천적으로 불가능한 것은 아닙니다. KEDA는 scaler·external metrics API·활성화 제어를 제공하며 일반적인 replica scaling에는 HPA를 사용합니다.

| 신호 | 의미 | 용도와 제약 |
|---|---|---|
| `istio_requests_total` | HTTP/gRPC 요청 counter | Rate로 수신 부하를 측정; reporter 하나와 실제 target workload 선택 |
| `istio_request_duration_milliseconds_bucket` | Classic latency histogram bucket | Quantile은 품질 관측값이며 용량 증가에 항상 반비례하지 않음 |
| `istio_tcp_connections_opened_total` | 누적 열린 연결 수 | Rate는 연결 생성 속도이며 현재 활성 연결 수가 아님 |
| `istio_request_bytes_sum` | 누적 HTTP request bytes | Rate로 처리량을 측정하고 reporter/workload 범위를 지정 |
| `envoy_cluster_upstream_rq_pending_overflow` | Client-side cluster overflow counter | Pool limit·의존성을 진단한 뒤 어떤 workload를 확장할지 판단 |

보정한 demand/backlog metric을 시작점으로 삼습니다. Latency·error·circuit-breaker 사건은 replica를 늘려도 해결되지 않는 downstream 장애에서 발생할 수 있습니다. Stateful membership·storage·앱 의미도 제약하므로 stateful/latency-sensitive 분류만으로 안전한 정책이 결정되지 않습니다.

## 아키텍처

KEDA는 target의 HPA를 생성·설정하고 external metric을 제공합니다. HPA controller가 API로 metric을 조회하여 target의 `/scale` subresource를 바꾸고, 해당 controller와 scheduler가 Pod를 생성·배치합니다.

| 설정/컴포넌트 | 역할 |
|---|---|
| KEDA `pollingInterval` | Trigger polling과0→1 활성화 |
| HPA controller sync | 추가 metric 조회와1→N 판단; 기본15초이며 cluster 설정에 따름 |
| `useCachedMetrics` | Poll 사이 KEDA metric cache 옵션; 본문 예제에서는 사용하지 않음 |
| `activationThreshold` |0↔1 활성화 임계값이며 별도 HPA scale-down 임계값이 아님 |
| `cooldownPeriod` | 비활성 후 KEDA가0으로 줄이기 전 대기; 모든 scale-down 뒤의 pause가 아님 |
| HPA `behavior` |1→N 안정화·변경 속도 제한 |

`minReplicaCount`가0보다 크면 activation/cooldown을 일반 replica hysteresis로 사용하지 않습니다. Capture·scrape·query·HPA·Pod 시작/readiness가 모두 지연을 더하므로15초 poll이나 stabilization0이 즉시 준비된 용량을 보장하지 않습니다.

### Metric Type과 이상적인 계산

HPA tolerance, 누락/unready Pod, min/max·behavior 제한을 제외하면:

- **AverageValue + 총수요**: desired replicas ≈ `ceil(총 metric / Pod당 target)`.
- **Value + workload 전체 값**: desired replicas ≈ `ceil(현재 replicas × 관측값 / target)`.

600 RPS에100 RPS/Pod면 AverageValue는6개를 요구합니다. Query에서 먼저 Pod3개로 나누면200을 입력하여2개를 요구하는 오류가 생깁니다. `count(up)`도 scrape target 수이지 안전한 replica 분모가 아닙니다.

Replica4개, 전체 latency300ms, Value target200ms이면6개를 제안합니다. Replica를 늘려도 latency가 줄지 않으면 반복하여 cap까지 확장할 수 있습니다. Latency/error ratio controller는 음의 feedback을 입증해야 하는 실험이며 production 기본값이 아닙니다.

## Prometheus 메트릭 기반 스케일링

`default`에 실제 `reviews` Deployment가 있다고 가정합니다. Service 이름은 scale target이 아닙니다. 배포된 Bookinfo는 일반적으로 `reviews-v1` 같은 Deployment를 사용하므로 `scaleTargetRef`와 metric selector를 실제 workload에 맞추세요.

해당 proxy를 중복 scrape하지 않고 실제 label을 확인해야 합니다. 주요 예제는 양쪽 reporter 중복을 피하려고 `reporter="destination"`을 사용합니다. 이는 target에 도달한 요청을 측정하므로 edge 거부/queue에는 별도로 검증한 demand signal이 필요할 수 있습니다.

### 1. RPS 기반 스케일링

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

실패한 요청도 부하에 포함한 총 RPS입니다. AverageValue의 `threshold: "100"`은 replica당 target이며 “전체100 초과 시 Pod 추가”라는 스위치가 아닙니다. Pod 수로 다시 나누지 마세요.

KEDA 2.20.2에서 `ignoreNullValues: "false"`는 누락·NaN·무한대 Prometheus 결과를 error로 처리합니다. 실제 counter의 zero rate는0입니다. Source 장애 fallback을 설정·시험하고 임의의 metric 누락을0으로 바꾸지 않아야 합니다. Scaler 활성화 전에 scrape/metric 전제조건을 확인하세요.

여기의 fallback은 설정한 error threshold 이후 지정 floor와 현재 replica 중 큰 값을 사용하며 HPA 제한·behavior를 따릅니다. KEDA metrics API 자체의 장애나 node 용량 부족까지 보호하는 것은 아닙니다.

### 2. Latency 기반 제어: 조건부 실험

Workload 전체 p95에 Value를 명시하는 대안입니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-latency-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

실제 histogram count의 rate가0일 때만0을 반환합니다. Telemetry가 없으면 absent를 유지하고 잘못된 quantile은 건강한0이 아닌 error입니다. Idle p95의0은 제어용 값이지 관측한 zero-duration 요청이 아닙니다.

여러 quantile도 Value metric으로 설정합니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-quantile-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: p50
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.5, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '50'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p99
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.99, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '500'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

HPA는 평균이나 가중 혼합이 아닌 가장 큰 desired replica 수를 선택합니다. Quantile들은 상관되어 있으므로 trigger 추가만으로 안정성이나 latency가 보장되지는 않습니다.

### 3. 에러율 제어: 조건부 실험

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-error-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: error-percent
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (100 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
          and on() (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '5'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Workload 전체5xx/zero-status 백분율에 Value target을 사용합니다. 관측된 idle은0이며 telemetry 누락을0으로 만들지 않습니다. Replica 부족이 오류 원인임을 확인한 뒤에만 사용하세요. 의존성 장애·인가 실패·client pool 제한이라면 scaling이 효과 없거나 문제를 키울 수 있습니다.

### 4. 복합 메트릭

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-composite-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: prometheus
    name: p95
    metricType: Value
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: |-
        (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
          and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
        or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
      threshold: '200'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

RPS는 총수요/AverageValue, latency는 Value입니다. HPA는 가장 큰 권고를 선택합니다. Scale-up `selectPolicy: Max`는 허용 변경량 중 큰 값을 택하므로 percentage 정책이 더 큰 변경을 허용하면 five-Pod 정책이 절대 cap이 되지 않습니다. 이 대안도 용량·workload 검증이 필요합니다.


## CloudWatch 메트릭 기반 스케일링

Source cadence·발행 지연·집계 기간·lookback·offset이 freshness를 결정합니다. High-resolution custom metric도 있으므로 “CloudWatch는 항상1–3분 지연”이라고 단정할 수 없습니다. Prometheus에도 수집·제어-loop 지연이 있습니다.

### Identity와 발행 Metric 조건

이 예제는 IRSA로 구성한 KEDA operator role과 workload namespace의 TriggerAuthentication을 사용합니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-aws
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
```

`podIdentity.provider: aws`가 현재 IRSA provider이며 `identityOwner: keda`를 사용합니다. Deprecated scaler metadata의 `identityOwner: operator/pod`와는 다릅니다. 옛 metadata는2.20에서 지원되지만3에서 제거 예정입니다. `aws-eks`라는 옛 provider 이름을 새로운 EKS Pod Identity association과 혼동하지 말고 선택한 방식의 provider/SDK credential 설정을 따르세요.

뒤의 발행 예제는 다음 metric을 만듭니다.

| Metric | Namespace·정확한 dimension | 의미 |
|---|---|---|
| `IstioRequestsPerSecond` | `IstioScaling`; ClusterName=`eks-demo`, destination_workload=`reviews`, destination_workload_namespace=`default` | 미리 계산한 RPS gauge |
| `IstioP95LatencyMilliseconds` | 같은 dimension 집합 | Window별로 미리 계산한 p95 gauge, milliseconds |

모든 dimension이 일치해야 합니다. destination_workload 하나만 지정한 query는 같은 custom metric을 가리키지 않습니다.

### RPS Gauge

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

Gauge의60초 Average는 RPS 단위를 유지합니다. 누적 `istio_requests_total` sample을 Sum하면 분당 요청 수가 되지 않습니다. 실제 delta-count metric을 별도로 발행한다면 그 기간에 맞는 target을 다시 계산하세요.

Released scaler parser를 위해 `minMetricValue`를 명시했지만 빈 결과에는 `ignoreNullValues: "false"`가 우선합니다. `metricEndTimeOffset`은 최근의 미완성일 수 있는 point를 건너뛰며 지연을 추가할 뿐 freshness 증명이 아닙니다. 값이 존재해도 오래되었을 수 있으므로 timestamp·publisher 상태를 감시해야 합니다.

### 미리 계산한 Latency Gauge

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-cloudwatch-p95-experiment
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 60
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-cloudwatch
    name: cw-p95
    metricType: Value
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioP95LatencyMilliseconds
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '200'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Maximum
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

기간 안에서 발행한 p95 gauge의 최대값을 조회하며, **그 CloudWatch 기간 전체 요청의 p95가 아닙니다**. Prometheus histogram 변환이나 p95-of-p95 gauge에 `metricStat: p95`를 사용해 원래 분포가 보존된다고 설명하면 안 됩니다. Native CloudWatch percentile에는 적절히 발행한 sample/statistic이 필요합니다.

### 다중 Source는 순서 있는 Failover가 아님

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-dual-source-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: prom-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: aws-cloudwatch
    name: cw-rps
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      namespace: IstioScaling
      metricName: IstioRequestsPerSecond
      dimensionName: ClusterName;destination_workload;destination_workload_namespace
      dimensionValue: eks-demo;reviews;default
      targetMetricValue: '100'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      metricStatPeriod: '60'
      metricStat: Average
      metricCollectionTime: '300'
      metricEndTimeOffset: '60'
      awsRegion: us-west-2
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

두 metric 모두 HPA의 최대 권고 계산에 참여합니다. “Prometheus primary, CloudWatch secondary”는 우선순위/failover 정책이 아니며 stale 값이 높은 replica 권고를 유지할 수 있습니다. 의도한 단일 source 또는 검증한 multi-source/fallback 설계를 선택하세요.

## 실전 스케일링 전략

### 1. 시간대별 Replica Floor

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-scheduled-floor
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

평일 Asia/Seoul window에는 Cron이20개 floor를 제공하며 demand는 max까지 더 요구할 수 있습니다. Traffic prediction model이 아닌 예약 scaling입니다. 시작/readiness 시간이 필요하면 실제 수요보다 앞서 준비하도록 일정을 정합니다.

### 2. 명시적인 비업무 시간 Scale to Zero

비업무 시간에 사용할 수 없어도 되는 workload에는 window 안의 양수 desired count와 `minReplicaCount: 0`을 사용합니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: analytics-office-hours
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-service
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '20'
```

Cron의 `desiredReplicas: "0"`은 유효하지 않습니다. Active window 밖에서는 inactivity/cooldown 규칙에 따라0이 될 수 있습니다. Client 요청이 이 Cron-only workload를 깨우지는 않습니다. Target-side Istio metric은 앱과 함께 사라지므로 단독으로 신뢰할0→1 신호가 되지 못합니다. 요청 시 가용성이 필요하면 독립된 queue/interceptor나 양수 minimum을 사용하세요.

PromQL `hour()`는 UTC이며 Cron의 Asia/Seoul 설정을 상속하지 않습니다. 두 업무 시간 조건을 같다고 가정하여 혼합하지 마세요.

### 3. Circuit-breaker 신호는 먼저 진단

Client-side overflow와 현재 연결을 구분해 확인할 수 있습니다.

```promql
sum(increase(envoy_cluster_upstream_rq_pending_overflow{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
}[1m]))

sum(envoy_cluster_upstream_cx_active{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})

max(envoy_cluster_circuit_breakers_default_cx_open{
  cluster_name=~"outbound[|]9080[|][^|]*[|]backend[.]default[.]svc[.]cluster[.]local"
})
```

실제 cluster 이름/port, export한 stats와 source scrape 범위를 확인합니다. `cx_open`은0/1 flag이지 connection capacity가 아니므로 활성 연결 수를 나누어 saturation 백분율을 계산할 수 없습니다. Backend replica를 늘려도 client의 고정 pool limit이 올라가지는 않습니다. Limit·의존성을 진단한 뒤 scaling target을 선택하세요.

### 4. Scaling Policy는 부하 Tier가 아님

Percent/Pods 정책 목록과 `selectPolicy: Max`/`Min`은 rolling period의 허용 변경량을 제한합니다. 주석에 쓴 low/medium/high 부하 구간을 자동 선택하지 않습니다. 본문의 behavior 예제로 속도를 제한하고 실제 workload 반응을 검증하세요.

### 5. Gateway에서 본 Backend 수요

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: backend-gateway-rps
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 2
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: gateway-backend-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="source",source_workload="istio-ingressgateway",source_workload_namespace="istio-system",destination_service_name="backend",destination_service_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

실제 gateway workload 이름과 destination Service label을 확인합니다. 특정 backend로 향하는 해당 gateway의 트래픽을 측정합니다. `envoy_http_downstream_rq_active`는 pending 연결이 아닌 active HTTP 요청이며 gateway 전체에는 다른 서비스도 포함됩니다. 이 aggregate로 임의의 backend를 확장하지 마세요.

양수 minimum을 유지하는 예제입니다.0 replica를 고려한다면 독립 gateway/interceptor가 endpoint0에서도 필요한 metric을 내고 원하는 buffering/error 동작을 제공하는지 먼저 확인해야 합니다.


## 모범 사례

### 1. Target마다 하나의 Autoscaler 관리자

같은 target에 여러 예시 ScaledObject나 별도 “backup HPA”를 설치하지 마세요. 기존 HPA ownership·GitOps replicas 필드를 조율해야 합니다. 한 ScaledObject에 여러 metric을 넣을 수 있으며, native HPA는 metric error가 있으면 downscale을 건너뛰면서도 유효한 upscale을 허용할 수 있습니다.

KEDA 2.20 fallback은 CPU/memory를 제외한 AverageValue와 Value trigger를 지원하며 ScaledJob이 아닌 ScaledObject에 적용됩니다. CPU/memory trigger는 자체 metrics-server/request 전제조건이 필요하고 독립 failover controller가 아닙니다.

### 2. Benchmark가 아닌 용량 계산 예제

기존 수치를 **가정 입력값**으로 유지합니다.

| 가정/계산 | 결과 |
|---|---|
| 측정했다고 가정한 Pod당200 RPS × 선택한 활용 계수70% |140 RPS/Pod target |
| 평상시500 /140을 올림 |4 replicas |
| 피크2000 /140을 올림 |15 replicas |
| 추가 여유로 선택한 최대값 |20, 실제 배치 가능한 용량 검토 필요 |

이 감사에서 측정한 값이 아닙니다. 승인된 bounded 부하 시험으로 알려진 replica/target의 latency·error·resource·readiness를 기록하세요. 여러 replica로 분산하는 Service 시험을 바로 한 Pod의 용량으로 해석할 수 없습니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-capacity-example
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reviews
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 4
  maxReplicaCount: 20
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
      threshold: '140'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 4
    behavior: currentReplicasIfHigher
```

“maxReplicaCount는 cluster 용량70% 이하”라는 보편적 규칙은 없습니다. Pod 수는 CPU/메모리/IP/quota 백분율이 아닙니다. HPA/KEDA는 workload를 확장하며 node 용량에는 별도 provisioning/autoscaler 설정이 필요합니다.

### 3. Resource와 Health

실제 container 이름·health endpoint를 확인한 후 **기존** Deployment/container에 병합하는 조각입니다. 실제 image·selector·label은 보존합니다.

```yaml
spec:
  template:
    spec:
      containers:
      - name: reviews
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /health
            port: 9080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
```

Requests/limits·probe는 튜닝 입력이며 throughput 실측 보장이 아닙니다. Readiness와 시작/drain이 용량 사용 시점에 영향을 줍니다. Downstream 장애만으로 정상 process를 반복 재시작하는 liveness 정책은 피해야 합니다.

### 4. 여러 Cluster와 Region

각 target cluster에서 검증한 cluster-local datasource를 사용하거나 federated store에 실제 존재하는 cluster label을 명시합니다. Local destination-reporter 데이터라면 다음 예제는 그 cluster backend에 도달한 전체 부하를 셉니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend-local-demand
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 3
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: local-rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="frontend",destination_workload_namespace="default"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 3
    behavior: currentReplicasIfHigher
```

각 설정은 해당 cluster context에 적용합니다. Metadata의 `region` label이 ScaledObject를 원격 cluster로 보내지는 않습니다. `source_cluster`는 출발지이지 확장할 목적지 용량이 아니며, 이미 필터한 수요에0.6/0.4를 곱해 global traffic split을 구현할 수 없습니다.

`*-us-*` 서비스명은 client 지리 정보가 아니고 `destination_region`도 항상 있는 기본 Istio label이 아닙니다. Region별 SLO에는 검증한 telemetry·workload 용량이 필요합니다.

### 5. 결제와 Queue Workload

결제 workload는 보정한 demand와 보수적인 변경 제한으로 시작하고 latency/error를 품질 지표로 관찰할 수 있습니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: payment-capacity-example
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 5
  maxReplicaCount: 50
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: prometheus
    name: rps
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="payment-service",destination_workload_namespace="production"}[2m]))
      threshold: '100'
      ignoreNullValues: 'false'
  fallback:
    failureThreshold: 3
    replicas: 5
    behavior: currentReplicasIfHigher
```

100 RPS target과 제한값은 설명용입니다. Ratio trigger를 추가하기 전에 병목 원인·멱등성·downstream 제한·대표 실패 동작을 확인하세요.

Queue worker는 replica0에서도 queue를 관측할 수 있습니다.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: data-processor-queue
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  pollingInterval: 30
  cooldownPeriod: 600
  minReplicaCount: 0
  maxReplicaCount: 30
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
          policies:
          - type: Percent
            value: 10
            periodSeconds: 60
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 50
            periodSeconds: 60
          - type: Pods
            value: 5
            periodSeconds: 60
          selectPolicy: Max
  triggers:
  - type: aws-sqs-queue
    name: backlog
    metricType: AverageValue
    authenticationRef:
      name: keda-aws
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/data-processing-queue
      queueLength: '10'
      activationQueueLength: '0'
      scaleOnInFlight: 'true'
      scaleOnDelayed: 'false'
      awsRegion: us-west-2
```

예시 account/queue URL을 교체하고 참조한 identity를 구성합니다. `queueLength: "10"`은 replica당 backlog target이지 열 개에서 활성화하는 임계값이 아닙니다. 명시한 activation threshold0에서는 양수 backlog로 활성화합니다. Visible·in-flight 메시지를 포함하고 delayed 메시지는 제외하므로 처리 concurrency·visibility timeout·종료 동작과 맞춰야 합니다.

Istio HTTP latency가 SQS job 처리 시간은 아닙니다.0-replica worker에 관측할 수 없는 Pod-latency trigger를 넣는 대신 업무 처리 시간을 별도로 계측하세요.

### 6. 모니터링

Scaler 상태에는 **operator** metric을 노출·수집해야 합니다. Metrics adapter metric만으로 모든 operator counter를 얻을 수 없습니다. KEDA의 `namespace` metric label은 scale 대상 namespace이므로 exporter Pod namespace로 덮어쓰지 않습니다.

기존 Prometheus 설정에 병합할 scrape 조각이며 EndpointSlice·Service·Pod에 대한 namespace 범위 discovery RBAC가 필요합니다.

```yaml
scrape_configs:
- job_name: keda-components
  kubernetes_sd_configs:
  - role: endpointslice
    namespaces:
      names:
      - keda
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_service_name
    regex: keda-operator|keda-operator-metrics-apiserver
    action: keep
  - source_labels:
    - __meta_kubernetes_endpointslice_port_name
    regex: metrics
    action: keep
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: exporter_namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: exporter_pod
```

HA operator Pod들을 하나의 load-balanced Service로 번갈아 수집하지 않고 각 endpoint를 발견합니다. 실제 Service/port 이름, target label, TLS/mesh 접근과 scrape 결과를 확인하세요. Prometheus Operator라면 생성된 ConfigMap을 덮어쓰지 말고 동등한 ServiceMonitor를 선택되도록 구성합니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: keda-scaling-alerts
  namespace: keda
spec:
  groups:
  - name: keda-scaling
    rules:
    - alert: KEDAMaxReplicasReached
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        ) >= on(namespace, horizontalpodautoscaler)
        max by (namespace, horizontalpodautoscaler) (
         kube_horizontalpodautoscaler_spec_max_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}
        )
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: KEDA-managed HPA is at its configured maximum
    - alert: KEDAScalerErrors
      expr: sum by (namespace, scaledObject) (increase(keda_scaler_detail_errors_total[5m])) > 0
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: Scaler retrieval errors observed; inspect source/identity and fallback
    - alert: KEDAReplicaCountChurn
      expr: |-
        max by (namespace, horizontalpodautoscaler) (
         changes(kube_horizontalpodautoscaler_status_current_replicas{horizontalpodautoscaler=~"keda-hpa-.*"}[10m])
        ) > 6
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Frequent observed replica-count changes; inspect demand, rollout and stabilization
```

PrometheusRule에는 맞는 Operator rule selector/namespace가 필요합니다. HPA filter는 KEDA 기본 이름 prefix를 사용하므로 custom HPA 이름에 맞춰 바꿉니다. Released error counter는 `keda_scaler_detail_errors_total`이며 gauge인 `keda_scaler_active`에 `rate()`를 적용해 replica flapping을 측정하면 안 됩니다.

Replica count 변화는 정상 demand·rollout일 수도 있습니다. 경고는 조사 신호이지 scaling 실패나 준비된 용량의 충분함을 증명하지 않습니다.

## 문제 해결

```bash
kubectl get scaledobject reviews-rps-scaler -n default -o yaml
kubectl describe hpa keda-hpa-reviews-rps-scaler -n default
kubectl logs -n keda deployment/keda-operator
kubectl get apiservice v1beta1.external.metrics.k8s.io
kubectl get pods -n default -o wide

# Port-forward 동안 다른 터미널에서 로컬 query를 확인합니다.
kubectl port-forward -n istio-system svc/prometheus 9090:9090
```

```bash
promtool query instant http://127.0.0.1:9090 'sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))'
```

로컬 port-forward가 KEDA Pod의 연결이나 credential을 증명하지는 않습니다. 실제 component 경로의 provider error, DNS, TLS/mesh policy, metric 존재/label과 aggregated API 가용성을 확인합니다.

느린 scaling은 pollingInterval을 줄이기 전에 source age·lookback·HPA sync/behavior·scheduling·image pull·readiness를 확인합니다. 양수 minimum의 일반1→N에는 activation threshold가 속도 조절이 아닙니다. 불안정한 count는 workload의 실제 반응과 HPA 안정화/속도 제한을 조사하며 cooldownPeriod로 일반 downscale을 제어하지 않습니다.

CloudWatch는 반환 timestamp, 모든 dimension, statistic/unit, 수집 창, offset과 IAM을 확인합니다. 두 번째 metric의 threshold를 높인다고 수동 대기 backup이 되지는 않습니다.


## 참고: KEDA 설치

### 고정 Chart와 실제 호환성

KEDA 2.20의 공개 배포 요구사항은 Kubernetes 1.30 이상이며 chart metadata의 1.23 최소값보다 높습니다. Helm이 버전을 허용한다고 runtime 지원이 증명되지는 않습니다. Istio 1.31의 Kubernetes 1.32–1.36 지원 범위와 관리형 플랫폼의 지원 버전이 겹치는 구간을 사용하세요.

새 설치 또는 기존 값을 보존하는 검토된 업그레이드에는 다음 값을 사용합니다. 업그레이드는 해당 release의 변경사항과 CRD ownership/migration 절차도 먼저 확인해야 합니다.

```yaml
operator:
  replicaCount: 2
prometheus:
  operator:
    enabled: true
  metricServer:
    enabled: true
    port: 9022
```

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm upgrade --install keda kedacore/keda --version 2.20.2   --namespace keda --create-namespace --values keda-values.yaml
kubectl get deployments,services,pods -n keda
```

`operator.replicaCount: 2`와 metrics adapter의 9022 port override는 유효한 chart 값입니다. 9022는 기본값 8080을 명시적으로 바꾼 값이며 operator metric도 8080으로 활성화합니다. Operator replica 두 개만으로 adapter/webhook이나 전체 scaling 경로의 HA가 완성되지는 않습니다.

Component에 Istio sidecar를 주입한다면 KEDA는 자체 TLS로 보호하는 내부 protocol에 다음 선택적 port 제외 설정을 문서화합니다.

```yaml
podAnnotations:
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: '9666'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9443,6443
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: '6443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,9443
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: '9443'
    traffic.sidecar.istio.io/excludeOutboundPorts: 9666,6443
```

병합 전에 실제 port와 injection 설정을 확인하세요. KEDA의 자체 TLS는 유지되며 제외한 트래픽에는 Istio authorization이 적용되지 않습니다. 전체 transport security를 해제하는 설정이 아닙니다. API server aggregation, admission, operator↔adapter, Prometheus 연결을 확인하세요.

### AWS Reader Identity

실제 operator ServiceAccount로 제한한 EKS OIDC trust와 IAM role을 별도로 검토·구성합니다. 기존 ServiceAccount를 무조건 덮어쓰지 말고 해당 Helm 값을 반영하세요.

```yaml
podIdentity:
  aws:
    irsa:
      enabled: true
      roleArn: arn:aws:iam::123456789012:role/KedaMetricsReader
```

본문 CloudWatch scaler의 released 구현은 GetMetricData를 호출합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-west-2"
        }
      }
    }
  ]
}
```

이는 Region 범위 metric 읽기 권한이며 metric namespace별 권한 경계가 아닙니다. AWS 예제의 `cloudwatch:namespace` 조건은 **PutMetricData 발행**을 제한하며 이 query에 적용되지 않습니다. 별도 CloudWatch PromQL API의 IAM 요구사항을 이 scaler에 그대로 대입하지 마세요.

SQS 예제를 사용한다면 operator에는 해당 queue의 attribute 읽기 권한도 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-west-2:123456789012:data-processing-queue"
    }
  ]
}
```

Queue worker에는 별도의 receive/delete/visibility 권한을 부여합니다. Scaler의 읽기 role이 이를 제공하지는 않습니다. Operator identity를 사용할 ScaledObject와 TriggerAuthentication의 생성·변경 권한도 제한하세요.

### 선택적 CloudWatch EMF 발행

이 예제는 Operator의 minor 버전 일치 권고에 맞춰 **upstream Collector Contrib 0.158.0과 Operator 0.158.0**을 사용합니다. Operator 0.158의 Kubernetes 지원 범위는 1.25–1.36입니다. Custom image는 operator가 자동 업그레이드하지 않습니다. ADOT를 선택할 때는 필요한 component와 설정을 별도로 확인해야 하며 아래 설정이 임의의 ADOT image에서 검증되었다고 가정할 수 없습니다.

먼저 기존 Prometheus에 다음 recording-rule 파일을 로드합니다. PrometheusRule을 사용한다면 동등한 내용과 적절한 선택 label을 사용하세요.

```yaml
groups:
- name: istio-scaling-export
  interval: 30s
  rules:
  - record: istio_scaling_requests_per_second
    expr: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m]))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
  - record: istio_scaling_p95_milliseconds
    expr: |-
      (histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])))
        and on() (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) > 0))
      or on() (0 * (sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[2m])) == 0))
    labels:
      destination_workload: reviews
      destination_workload_namespace: default
```

표시한 workload만 발행합니다. 이미 계산한 RPS와 rolling-window p95 gauge이며 누적 request counter나 원래 latency 분포를 재구성할 수 있는 데이터가 아닙니다.

호환 Operator/CRD와 검토된 publisher role/log group을 준비한 뒤 다음 설정을 사용합니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-metrics-publisher
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/IstioMetricsPublisher
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: istio-scaling
  namespace: istio-system
spec:
  mode: deployment
  replicas: 1
  serviceAccount: istio-metrics-publisher
  image: otel/opentelemetry-collector-contrib:0.158.0
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
  config:
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      prometheus:
        config:
          scrape_configs:
          - job_name: istio-scaling-federate
            scrape_interval: 60s
            honor_labels: true
            metrics_path: /federate
            params:
              match[]:
              - '{__name__=~"istio_scaling_requests_per_second|istio_scaling_p95_milliseconds"}'
            static_configs:
            - targets:
              - prometheus.istio-system.svc.cluster.local:9090
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 256
        spike_limit_mib: 64
      metricstransform:
        transforms:
        - include: istio_scaling_requests_per_second
          action: update
          new_name: IstioRequestsPerSecond
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
        - include: istio_scaling_p95_milliseconds
          action: update
          new_name: IstioP95LatencyMilliseconds
          operations:
          - action: add_label
            new_label: ClusterName
            new_value: eks-demo
      batch:
        timeout: 60s
        send_batch_size: 256
    exporters:
      awsemf:
        namespace: IstioScaling
        region: us-west-2
        log_group_name: /aws/otel/istio-scaling
        log_stream_name: eks-demo
        dimension_rollup_option: NoDimensionRollup
        metric_declarations:
        - dimensions:
          - - ClusterName
            - destination_workload
            - destination_workload_namespace
          metric_name_selectors:
          - ^IstioRequestsPerSecond$
          - ^IstioP95LatencyMilliseconds$
        metric_descriptors:
        - metric_name: IstioRequestsPerSecond
          unit: Count/Second
          overwrite: true
        - metric_name: IstioP95LatencyMilliseconds
          unit: Milliseconds
          overwrite: true
    service:
      extensions:
      - health_check
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - metricstransform
          - batch
          exporters:
          - awsemf
```

`v1beta1`의 config는 object입니다. 이 Operator release는 구형 `v1alpha1`도 계속 serve하므로 제거된 API라고 설명하면 안 됩니다. 여기서는 현재 형식과 필요한 component가 포함된 명시적 Contrib image를 사용합니다.

Collector는 이름을 제한한 recording metric 두 개만 federation으로 읽고 workload dimension을 보존하며 설정한 ClusterName을 추가해 고정 log stream으로 EMF를 보냅니다. Namespace, metric 이름, unit, 세 dimension을 CloudWatch scaler와 일치시키세요. EMF exporter는 NaN/Inf를 버립니다. Recording expression은 관측된 idle 0과 telemetry 부재를 구분합니다.

Publisher replica 하나는 이 예제의 중복 polling을 피하기 위한 값이며 HA 설계가 아닙니다. 실제 Prometheus 인증/mesh 연결, publisher identity, log retention과 resource limit을 구성해야 합니다. 이번 감사에서는 Operator/controller나 EMF 전달을 AWS에 배포해 검증하지 않았습니다.

Publisher log group은 retention을 관리하는 플랫폼에서 미리 생성해야 합니다. 예시 role은 해당 stream의 생성·쓰기 권한만 가집니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/otel/istio-scaling:log-stream:eks-demo"
    }
  ]
}
```

EMF는 CloudWatch Logs를 경유하므로 `cloudwatch:PutMetricData` 권한만으로 이 exporter를 사용할 수 없습니다. PutMetricData의 namespace 조건이 이 Logs 호출의 metric namespace를 제한하지도 않습니다. Log 수집/보관과 생성한 custom metric에는 별도 비용이 발생하므로 cardinality와 retention을 관리하세요. Replica 감소를 곧바로 청구 비용 절감으로 해석할 수 없습니다.

## 참고자료

- [KEDA ScaledObject specification](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [Activation과 scaling](https://keda.sh/docs/2.20/concepts/scaling-deployments/)
- [Prometheus scaler](https://keda.sh/docs/2.20/scalers/prometheus/)
- [CloudWatch scaler](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [SQS scaler](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Cron scaler](https://keda.sh/docs/2.20/scalers/cron/)
- [AWS IRSA provider](https://keda.sh/docs/2.20/authentication-providers/aws/)
- [KEDA metric](https://keda.sh/docs/2.20/integrations/prometheus/)
- [KEDA와 Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)
- [KEDA 배포 요구사항](https://keda.sh/docs/2.20/deploy/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Istio 표준 metric](https://istio.io/latest/docs/reference/config/metrics/)
- [Operator 0.158 호환성](https://raw.githubusercontent.com/open-telemetry/opentelemetry-operator/v0.158.0/docs/getting-started/compatibility.md)
- [Collector 0.158 EMF exporter](https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/v0.158.0/exporter/awsemfexporter/README.md)
- [CloudWatch EMF](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format.html)
- [CloudWatch namespace 조건](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-cw-condition-keys-namespace.html)
- [관측성](../observability/README.md)
- [복원력](../resilience/README.md)
- [트래픽 관리](../traffic-management/README.md)

운영 적용 전에 신호 의미, 실제 metric label/freshness, idle·missing-data 동작, 단일 scaling 관리자, 용량, 대표 실패와 복구 동작을 확인하세요. 예제 threshold, replica minimum, 시간 값은 이 검증의 시작 입력입니다.
