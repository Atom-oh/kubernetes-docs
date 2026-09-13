# Outlier Detection

> **마지막 업데이트**: 2026년 9월 11일 · Istio 1.31. 독립적인 사이드카 예제이며 지정한 namespace·실제 workload/endpoint가 필요합니다. 같은 host 예제는 대안 관계이고 값은 부하 검증된 권장치가 아닌 예시입니다.

Outlier Detection은 비정상적으로 동작하는 서비스 인스턴스를 자동으로 감지하고 트래픽 풀에서 제외하는 Circuit Breaker 패턴의 한 형태입니다.

## 목차

1. [개요](#개요)
2. [작동 원리](#작동-원리)
3. [기본 설정](#기본-설정)
4. [고급 설정](#고급-설정)
5. [외부 서비스 보호](#외부-서비스-보호-serviceentry)
6. [실전 예제](#실전-예제)
7. [모니터링](#모니터링)
8. [문제 해결](#문제-해결)

## 개요

Outlier detection은 관측 프록시별 passive 검사입니다. HTTP를 볼 수 있을 때 해당 응답·로컬 연결 실패를 세며 DestinationRule의 지연 임계치나 주기적 복구 probe를 사용하지 않습니다. Ejection은 해당 프록시의 부하 분산 후보를 바꾸며 Pod를 삭제하거나 서비스를 고치지 않습니다.


### 주요 기능

1. **감지**: 설정한 연속 HTTP·전송 실패를 셉니다.
2. **제외**: 제외 한도·강제 조건이 허용하면 host를 제외합니다.
3. **후보 복귀**: 제외 기간 뒤 다시 후보가 되며 실제 복구는 정상 트래픽으로 확인해야 합니다.

## 작동 원리

### Outlier Detection 프로세스

성공하면 해당 연속 오류 카운트가 초기화됩니다. 임계치에 도달한 실패는 `interval`을 기다리지 않고 즉시 ejection을 유발할 수 있습니다. 반복 제외 시 base 기간×배수로 길어지며 Envoy 상한을 따릅니다. 고정30초 probe나 지수 두 배 증가가 아닙니다.


### 감지 방식

| 방식 | 설명 | 사용 시나리오 |
|------|------|--------------|
| **연속 에러** | 연속된 5xx 에러 감지 | 애플리케이션 크래시 |
| **게이트웨이 에러** | 502, 503, 504 에러 감지 | 서비스 과부하 |
| **연결 실패** | TCP 연결 실패 감지 | 네트워크 문제 |
| **지연시간** | DestinationRule outlier 임계값이 아님 | 지연 관측·애플리케이션/route timeout을 별도 설정 |

## 기본 설정

### 연속 에러 기반 감지

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### 주요 파라미터 설명

#### consecutive5xxErrors
- **설명**: 연속된 에러 발생 횟수 임계값
- **기본값**: 5
- **튜닝 범위 예시**: 3-10 (서비스 특성에 따라)

```yaml
# 민감한 서비스 (빠른 감지)
consecutive5xxErrors: 3

# 일반 서비스
---
consecutive5xxErrors: 5

# 관대한 설정 (오탐 방지)
---
consecutive5xxErrors: 10
```

#### interval
- **설명**: 주기적 ejection sweep 간격; 연속 오류 감지는 즉시 실행
- **기본값**: 10s
- **튜닝 범위 예시**: 10s-60s

```yaml
# 빠른 감지 (높은 부하)
interval: 10s

# 일반적인 경우
---
interval: 30s

# 안정적인 서비스
---
interval: 60s
```

#### baseEjectionTime
- **설명**: 인스턴스가 제외되는 최소 시간
- **기본값**: 30s
- **튜닝 범위 예시**: 30s-300s

```yaml
# 빠른 복구 시도
baseEjectionTime: 30s

# 일반적인 경우
---
baseEjectionTime: 60s

# 신중한 복구
---
baseEjectionTime: 300s
```

#### maxEjectionPercent
- **설명**: 동시에 제외할 수 있는 인스턴스의 최대 비율
- **기본값**: 10%
- **튜닝 범위 예시**: 10%-50%

```yaml
# 보수적 (안정성 우선)
maxEjectionPercent: 10

# 균형잡힌 설정
---
maxEjectionPercent: 30

# 적극적 (품질 우선)
---
maxEjectionPercent: 50
```

## 고급 설정

### 게이트웨이 에러 기반 감지

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-gateway-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveGatewayErrors: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### 정상 Pool의 Panic 임계값

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-panic-threshold-example
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      minHealthPercent: 50
      maxEjectionPercent: 30
```

`minHealthPercent: 50`은 fail-open/panic 선택입니다. 정상 host 비율이 임계치 아래로 떨어지면 비정상 host도 사용할 수 있습니다. 최소 요청 수·정상 용량 보장·split-brain 방지가 아닙니다. Istio 기본값은0이며 다른 예제는 이 panic 임계치를 끄도록0을 사용합니다. 제외 한도가 남은 endpoint를 정상으로 만들지는 않습니다.

### 연결 실패 기반 감지

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-connection-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveLocalOriginFailures: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

### 성공률 기반 감지 (고급)

Envoy 통계적 성공률 감지는 최소 host/요청량·편차 조건을 사용하며 단순히 “95% 미만”이 아닙니다. Istio1.31 DestinationRule에는 `enforcingConsecutiveErrors`/`enforcingSuccessRate`·통계 임계 필드가 없습니다. [릴리스 구현](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go)은 성공률 강제를 명시적으로 끕니다. `splitExternalLocalOriginErrors`는 오류 분류를 나누는 값이며 최소 요청 수가 아닙니다. 여기서는 지원되는 연속 오류 필드를 사용합니다. 고급 EnvoyFilter 변경은 버전별 설정·실행 검증이 필요합니다.

## 외부 서비스 보호 (ServiceEntry)

외부 API나 레거시 시스템을 ServiceEntry로 등록하고 Outlier Detection을 적용하여 장애 전파를 방지합니다.

### 외부 API 보호 아키텍처

![클러스터 안의 애플리케이션 Pod가 Envoy Proxy를 통해 여러 외부 API 인스턴스로 트래픽을 보내는데, 에러가 발생한 인스턴스는 Outlier Detection에 의해 트래픽에서 제외되고 정상 인스턴스만 계속 트래픽을 받는 구조를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-resilience-01-outlier-detection-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-resilience-01-outlier-detection-2.html)

HTTP를 분석하는 다음 외부 API 예제는 애플리케이션이 **HTTP80**으로 호출하고 사이드카가 target443으로 TLS를 시작해야 합니다. SNI/SAN을 지정하고 프록시 OS 신뢰 저장소를 사용하며 사설 CA에는 적절한 CA bundle을 마운트합니다. 앱→사이드카는 평문이므로 그 홉도 암호화해야 하는 요구에는 맞지 않습니다. 앱이 HTTPS를 시작한다면 SIMPLE로 다시 암호화하지 않는 passthrough를 사용하며 Envoy에는 HTTP 상태·지연·HTTP retry가 아닌 전송 실패만 보입니다. 자격 증명을 전송하기 전에 등록·라우팅·인증서 검증을 확인합니다. 아래 host/IP는 생성된 서비스가 아닌 예시이므로 권한 있는 endpoint로 바꿉니다.

### 예제 1: 단일 외부 API (DNS 기반)

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
  namespace: payment
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.payment-provider.com
        subjectAltNames:
        - api.payment-provider.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.payment-provider.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**사용 예제**:
```go
package payment

import (
    "bytes"
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

var paymentClient = &http.Client{
    Timeout: 5 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        return http.ErrUseLastResponse
    },
}

// payload, authentication and payment-provider idempotency are application concerns.
// Requires the port80-to443 sidecar TLS-origination policy above.
func processPayment(ctx context.Context, payload []byte) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodPost,
        "http://api.payment-provider.com/v1/charge", bytes.NewReader(payload))
    if err != nil { return err }
    req.Header.Set("Content-Type", "application/json")
    resp, err := paymentClient.Do(req)
    if err != nil { return fmt.Errorf("payment transport failed: %w", err) }
    defer resp.Body.Close()
    _, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<20))
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        return fmt.Errorf("payment endpoint returned HTTP %d", resp.StatusCode)
    }
    return nil
}
```

Outlier detection은 이후 host 선택에 영향을 줄 뿐 결제를 재시도·중복 제거하지 않습니다. VirtualService로 mesh retry를 명시적으로 껐습니다. DNS 이름이 Envoy host 하나만 노출할 수도 있어 다른 provider endpoint를 보장하지 않습니다. 전송 오류만으로 원격 거래의 완료 여부를 판단할 수 없습니다.

### 예제 2: 다중 외부 API 엔드포인트

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  resolution: STATIC
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  endpoints:
  - address: 203.0.113.10
    labels:
      region: us-east-1
    locality: us-east-1
  - address: 203.0.113.20
    labels:
      region: us-west-2
    locality: us-west-2
  - address: 203.0.113.30
    labels:
      region: eu-central-1
    locality: eu-central-1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-weather-api
  namespace: weather
spec:
  host: weather.api.com
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
      http:
        http1MaxPendingRequests: 20
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 33
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: weather.api.com
        subjectAltNames:
        - weather.api.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  http:
  - name: no-retries
    route:
    - destination:
        host: weather.api.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

세 문서용 IP는 하나의 upstream pool 구성원입니다. `maxEjectionPercent`는 pool 한도이며 “리전마다 하나”가 아닙니다. Labels는 metadata이고 topology는 `locality`로 지정합니다. 반올림·실제 host 수·기존 제외 상태에 따라 실제 제외 수가 달라집니다.

### 예제 3: 레거시 데이터베이스 보호

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: database
spec:
  hosts:
  - legacy-db.company.internal
  resolution: DNS
  ports:
  - number: 5432
    name: tcp-postgres
    protocol: TCP
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-postgres
  namespace: database
spec:
  host: legacy-db.company.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 10s
    outlierDetection:
      consecutive5xxErrors: 10
      consecutiveLocalOriginFailures: 5
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

TCP 예제는 연결·전송 실패를 관찰하며 SQL 오류·lock·쿼리 지연은 보지 못합니다. 목적지가 명확히 식별되어야 하고 공유 TCP 포트에는 DNS capture/VIP 설계가 필요할 수 있습니다. 쓰기 가능한 DB primary를 선출하거나 replica failover 안전성을 보장하지 않습니다.

### 예제 4: 외부 API with Retry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  host: maps.googleapis.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: maps.googleapis.com
        subjectAltNames:
        - maps.googleapis.com
```

Geocoding 예제는 매칭된 멱등 읽기만 재시도합니다. HTTP80 경로로 호출해야 프록시가 메서드를 볼 수 있으며 HTTPS passthrough에는 HTTP 정책이 적용되지 않습니다. 전체5초에서 각 시도가2초를 쓰면 최초+재시도3회가 모두 들어가지 않습니다.

### 예제 5: 외부 서비스 with Rate Limiting

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: api
data:
  config.yaml: "domain: external-api-ratelimit\ndescriptors:\n- key: destination_cluster\n  value: outbound|80||api.third-party.com\n  rate_limit:\n    unit: second\n    requests_per_unit: 100\n"
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  host: api.third-party.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.third-party.com
        subjectAltNames:
        - api.third-party.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.third-party.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

ConfigMap은 rate-limit 서비스 설정 조각입니다. 호환되는 실제 서비스·저장소에 마운트하고 송신 Envoy rate-limit filter·일치하는 `destination_cluster` descriptor를 연결해야 합니다. 이것만으로 제한되지 않습니다. Gateway 오류는429가 아닌502/503/504이며 표준5xx 감지는429를 gateway 오류로 세지 않습니다. Ejection 기간은 provider quota 재설정과 동기화되지 않습니다. 정상 host를 모두 제외하기보다 quota·Retry-After·애플리케이션 backoff를 처리합니다.

### 외부 서비스 Outlier Detection 모범 사례

#### 1. 에러 유형 구분

```yaml
outlierDetection:
  # Gateway 에러 (502, 503, 504)
  consecutiveGatewayErrors: 2  # 빠르게 감지

  # 5xx 에러 (500, 501, etc.)
  consecutive5xxErrors: 3

  # Local 오류 (timeout, connection failure)
  consecutiveLocalOriginFailures: 3

  # 로컬 오류와 원격 오류 분리 추적
  splitExternalLocalOriginErrors: true
```

**중요**: `splitExternalLocalOriginErrors: true`를 설정하면:
- **Local Origin Failures**: 특정 upstream host에 귀속된 연결 timeout/reset/거부; DNS 실패로 host 자체가 없으면 제외할 대상도 없을 수 있음
- **Upstream Failures**: 외부 API가 반환한 5xx 에러

이 둘을 별도로 카운트하여 더 정확한 감지가 가능합니다.

#### 2. Timeout 설정

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 3s
    outlierDetection:
      consecutiveLocalOriginFailures: 3
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
```

#### 3. 외부 서비스 모니터링

```promql
# Outlier Detection 메트릭
# 1. 제외된 외부 엔드포인트
envoy_cluster_outlier_detection_ejections_active{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}

# 2. 로컬 오류 (timeout, connection failure)
rate(envoy_cluster_upstream_rq_timeout{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}[5m])

# 3. 외부 API 5xx 에러
rate(istio_requests_total{
  reporter="source", source_workload_namespace="default",
  destination_service="api.external.com",
  response_code=~"5.."
}[5m])

# 4. 외부 API 응답 시간
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="source", source_workload_namespace="default",
    destination_service="api.external.com"
  }[5m])) by (le)
)
```

#### 4. 알림 설정

Kubernetes 리소스가 아닌 Prometheus rule-file 조각입니다. Prometheus에 마운트·선택하거나 groups를 선택된 PrometheusRule로 감쌉니다. 임계치에는 최소 트래픽·no-data·scrape 상태 처리가 필요하며 검증된 SLO가 아닙니다. 지연은 밀리초, rate는 초당 값입니다.


```yaml
# Prometheus Alert Rules
groups:
- name: external_api_alerts
  interval: 1m
  rules:
  # 외부 API 에러율 높음
  - alert: ExternalAPIHighErrorRate
    expr: |
      (sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*",
        response_code=~"5.."
      }[5m])) by (destination_service)
      /
      sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*"
      }[5m])) by (destination_service))
      * 100 > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate for external API {{ $labels.destination_service }}"
      description: "Error rate is {{ $value }}%"

  # 외부 API 제외됨
  - alert: ExternalAPIInstanceEjected
    expr: |
      envoy_cluster_outlier_detection_ejections_active{
        namespace="default", cluster_name=~"outbound.*external.*"
      } > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "External API instance ejected"
      description: "{{ $value }} instances ejected from {{ $labels.cluster_name }}"

  # 외부 API 타임아웃 증가
  - alert: ExternalAPIHighTimeout
    expr: |
      rate(envoy_cluster_upstream_rq_timeout{
        namespace="default", cluster_name=~"outbound.*external.*"
      }[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High timeout rate for external API"
      description: "Timeout rate is {{ $value }} req/s"
```

#### 5. 문제 해결

호출하는 프록시에서 진단합니다. 연결 명령은 승인된 앱/테스트 컨테이너의 curl·실제 읽기 전용 health endpoint가 필요합니다. `istio-proxy` 내부 curl은 애플리케이션 트래픽 경로를 우회할 수 있습니다. 일반 모니터링 쿼리는 별도 `default`/`api.external.com` 예제를 가리키므로 다른 예제에는 범위를 맞춥니다.


```bash
# 1. ServiceEntry 확인
kubectl get serviceentry -A
kubectl describe serviceentry external-api -n <namespace>

# 2. DestinationRule 적용 확인
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.external.com -o json | \
  jq '.[] | {name: .name, outlierDetection: .outlierDetection}'

# 3. 외부 API 연결 테스트
kubectl exec <client-pod> -n default -c <app-container> -- \
  curl --max-time 5 -v http://api.external.com/health

# 4. Envoy 통계 확인
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep "outbound.*external"

# 5. Outlier Detection 상태
istioctl x envoy-stats <pod-name> -n <namespace> --type clusters
```

### 외부 서비스 장애 시나리오

#### 시나리오 1: 외부 API 일시적 장애

```yaml
# 설정: 빠른 감지 및 복구
outlierDetection:
  consecutive5xxErrors: 3           # 3회 연속 에러
  consecutiveGatewayErrors: 2    # 2회 게이트웨이 에러
  interval: 10s                  # 10초마다 평가
  baseEjectionTime: 30s          # 30초 후 복구 시도
  maxEjectionPercent: 50         # 최대 50% 제외
```

**실제 제한 조건 아래의 예상 동작**:

1. 해당502/503 응답을 gateway 임계치에 셉니다.
2. 연속 gateway 실패2회 시 강제·제외 한도가 허용하면 제외할 수 있습니다.
3. 제외 기간 뒤 후보로 돌아오며 여기에는 active probe를 설정하지 않았습니다.
4. 반복 제외 시 Envoy 배수·상한에 따라 기간이 길어집니다. Pool 복귀가 provider 복구 증명은 아닙니다.

#### 시나리오 2: 외부 API 완전 다운

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      tier: primary
  - address: 203.0.113.20
    labels:
      tier: secondary
  - address: 203.0.113.30
    labels:
      tier: tertiary
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-ha
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 66
      minHealthPercent: 0
      splitExternalLocalOriginErrors: true
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**해석**:

세 endpoint는 하나의 pool입니다. `tier: primary/secondary/tertiary` 레이블은 장애조치 우선순위가 아니며 정상 분산은 어느 후보든 선택할 수 있습니다. 실패 endpoint를 해당 프록시에서 제외하고 다른 후보를 고를 수 있지만 전체 외부 서비스 장애를 라우팅으로 고칠 수는 없습니다. `minHealthPercent: 0`은 비정상 host까지 쓰는 panic 동작을 끄며 비율 한도가 정상 endpoint 하나를 보장하지 않습니다. 순차 장애조치가 필요하면 locality priority나 앱/provider failover를 명시적으로 설계합니다. 문서용 IP는 연결 시험 전에 바꿔야 합니다.

## 실전 예제

### 예제 1: 마이크로서비스 체인

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-outlier
  namespace: default
spec:
  host: backend
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-outlier
  namespace: default
spec:
  host: database
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      minHealthPercent: 0
```

### 예제 2: Canary 배포와 함께 사용

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s
        maxEjectionPercent: 100
        minHealthPercent: 0
```

v2 endpoint 전체를 제외해도 route의10%가 v1으로 이동하지 않습니다. 빈 canary subset으로 선택된 요청은 실패할 수 있으며 rollout controller가 상태를 보고 가중치·rollback을 바꿔야 합니다. 실제 workload 레이블도 두 subset과 일치해야 합니다.

### 예제 3: 다중 리전 배포

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
  namespace: default
spec:
  host: api
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 80
            us-west-2/*: 20
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 120s
      maxEjectionPercent: 30
      minHealthPercent: 0
```

80/20은 두 정상 리전으로 의도적으로 트래픽을 보내는 정책이며 대기 failover가 아닙니다. 실제 region-locality·리전 간 연결·용량이 필요하고 리전 이름만으로 multi-cluster 메시가 생기지는 않습니다.

### 예제 4: Connection Pool + Outlier Detection

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-full-protection
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

## 모니터링

### Prometheus 메트릭

[복원력 개요](README.md#복원력-메트릭)처럼 선택적 proxy 통계·scrape 레이블을 설정합니다. 각 프록시의 `pod`/`cluster_name`을 유지하며 호출자별 제외 수 합계는 고유 서버 Pod 수가 아닙니다. Istio 릴리스 bootstrap은 `cluster_name`을 사용하므로 collector relabeling 이후 실제 레이블을 확인합니다. `enforced_*`는 실제 제외 수이고 `detected_*`는 한도로 제외하지 못해도 증가할 수 있습니다.

```promql
# Current ejections, not a cumulative event counter
envoy_cluster_outlier_detection_ejections_active{namespace="default"}

# Enforced ejection events per second
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m])

# Percentage of the total observed pool, excluding zero-size pools
100 * envoy_cluster_outlier_detection_ejections_active{namespace="default"} /
(envoy_cluster_membership_total{namespace="default"} > 0)

rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure{namespace="default"}[5m])
```

### Grafana 대시보드 예제

[Dashboard 파일 provisioning](../observability/04-dashboards.md) 절차로 저장할 객체입니다. Datasource UID `prometheus`·실제 `namespace`/`pod`/`cluster_name` 레이블을 전제하며 ConfigMap만으로 자동 등록되지는 않습니다.

```json
{
  "uid": "istio-outlier-detection",
  "title": "Istio Outlier Detection",
  "panels": [
    {
      "id": 1,
      "title": "Ejected Hosts",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"}",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 2,
      "title": "Enforced Ejections per Second",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace=\"default\"}[5m])",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 3,
      "title": "Ejected Pool Percentage",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"} / (envoy_cluster_membership_total{namespace=\"default\"} > 0)",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### 실시간 모니터링

```bash
# Envoy 통계 확인
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier

# 주요 메트릭:
# envoy_cluster_outlier_detection_ejections_active: 현재 제외된 인스턴스
# envoy_cluster_outlier_detection_ejections_enforced_total: 총 제외 횟수
# envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx: 5xx 에러로 제외된 횟수
```

### Kiali에서 확인

```bash
# Kiali 접속
istioctl dashboard kiali

# 확인 사항:
# 1. Graph → 서비스 선택 → Traffic 탭
# 2. Graph 상태는 집계 텔레메트리이며 모든 호출 프록시의 ejection 상태가 아님
# 3. Outlier Detection 메트릭 확인
```

## 문제 해결

### Outlier Detection이 작동하지 않음

```bash
# 1. DestinationRule 확인
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 2. Envoy 클러스터 설정 확인
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn <service-fqdn> -o json | \
  jq '.[] | .outlierDetection'

# 3. Envoy 로그 확인
kubectl logs -n <namespace> <pod-name> -c istio-proxy | grep outlier

# 4. 제어 설정 검증 (istiod가 프록시별 ejection을 실행하지는 않음)
istioctl analyze -n <namespace>
```

### 너무 많은 인스턴스가 제외됨

임계치를 바꾸기 전에 enforced/detected/overflow counter·남은 용량·실제 오류 종류를 확인합니다. 애플리케이션이 관측한 실패를 감당할 수 있을 때 연속 오류 임계치를 높이고 제외 cap은 가용성 영향을 고려해 줄입니다. `interval`을 늘려도 즉시 실행되는 연속 오류 제외를 지연시키지는 않습니다.

```yaml
# DestinationRule trafficPolicy 조각; 예시 값
outlierDetection:
  consecutive5xxErrors: 10
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 30
  minHealthPercent: 0
```

### 정상 Upstream Host가 없음

DB split-brain과 다릅니다. Readiness·discovery·route·endpoint 건강·호출자별 ejection을 확인합니다. `minHealthPercent: 50`은 비정상 host까지 허용할 수 있으며 복구시키지 않습니다. Canary subset 전체 제외 시 route rollback이 필요할 수 있습니다. DestinationRule YAML·Kiali 아이콘뿐 아니라 실제 endpoint/cluster 상태를 봅니다.

### 제외 후 복구가 너무 느림

반복 ejection 이력·실제 Envoy 기간 상한을 확인합니다. `baseEjectionTime`을 줄이면 비정상 host로 더 빨리 트래픽을 보낼 수 있을 뿐 고쳐주지는 않습니다. Active health check는 별도 기능이며 이 DestinationRule로 켜지지 않습니다.

### 임시 에러로 인한 오탐

연결 실패·앱 실패를 구분하고 재시도가 증폭하는지 확인합니다. 5xx가 의도한 앱 응답일 수도 있고 느리지만 성공한 응답 자체는 지연 기반 outlier가 아닙니다. 적용 범위를 제한하고 실제 프록시 설정을 확인합니다. 기본 로그에는 outlier event가 없을 수 있습니다.

## 모범 사례

### 1. 서비스 유형별 설정

```yaml
# 중요 서비스 (빠른 감지)
outlierDetection:
  consecutive5xxErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50

# 일반 서비스
---
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 60s
  maxEjectionPercent: 30

# 안정적인 서비스 (관대한 설정)
---
outlierDetection:
  consecutive5xxErrors: 10
  interval: 60s
  baseEjectionTime: 120s
  maxEjectionPercent: 20
```

### 2. Connection Pool과 함께 사용

```yaml
# 독립적인 제한이며 실측 호출자·endpoint 용량에 맞춰 설정
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
  outlierDetection:
    consecutive5xxErrors: 5
    interval: 30s
```

### 3. Panic 동작을 의도적으로 선택

`minHealthPercent: 0`은 Istio 기본값이며 비정상 host까지 사용하는 panic 임계치를 끕니다. 0이 아닌 값은 가용성·격리 사이의 선택이지 일부 host가 정상으로 남는다는 보장이 아닙니다. Connection-pool circuit breaking과 outlier detection은 독립적인 제어입니다.

### 4. 단계적 롤아웃

Baseline과 실제 mesh/namespace/workload 정책을 확인하고 격리된 실습 대상에 측정한 설정을 적용한 뒤 검증 후 확대합니다. `maxEjectionPercent: 0`을 관찰 전용 switch로 쓰지 않습니다. [Istio1.31 구현](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go)은0보다 큰 값만 Envoy 필드에 지정하므로0은 제외를 끄지 않고 Envoy 기본값을 남깁니다. 생략한 값은 mesh 기본 정책을 상속할 수도 있습니다. 범위 확대 전에 실제 강제 제외·남은 endpoint를 관찰합니다.

### 5. 모니터링 및 알림

```yaml
# Prometheus Alerting Rule
groups:
- name: istio_outlier_detection
  rules:
  - alert: HighEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High outlier ejection rate"
      description: "{{ $labels.cluster_name }} has enforced ejection rate > 0.1 events/s"
```

## 참고 자료

- [Istio Outlier Detection](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection)
- [Envoy Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Circuit Breaking](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
