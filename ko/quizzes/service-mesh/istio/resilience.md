# Resilience 퀴즈

> **지원 버전**: Istio 1.28.0 **EKS 버전**: 1.34 (Kubernetes 1.28+) **마지막 업데이트**: 2026년 2월 19일

이 퀴즈는 Istio의 복원력(Resilience) 기능에 대한 이해도를 테스트합니다.

## 객관식 문제 (1-5번)

### 문제 1: Outlier Detection 기본 개념

Outlier Detection의 주요 목적으로 옳지 **않은** 것은?

A. 비정상적으로 동작하는 인스턴스를 자동으로 감지\
B. 임계값 초과 시 트래픽 풀에서 자동 제외\
C. 제외된 인스턴스를 영구적으로 삭제\
D. 일정 시간 후 자동으로 복구 시도

<details>

<summary>정답 및 해설</summary>

**정답: C**

Outlier Detection은 **인스턴스를 삭제하지 않고** 트래픽 풀에서 일시적으로 제외합니다.

**해설:**

**Outlier Detection의 작동 원리:**

**주요 기능:**

1. **자동 감지**: 에러율, 지연시간, 응답 실패를 자동으로 모니터링
2. **자동 제외**: 임계값 초과 시 트래픽 풀에서 일시적 제외
3. **자동 복구**: baseEjectionTime 후 자동으로 복구 시도
4. **일시적 조치**: 인스턴스를 삭제하지 않고 트래픽만 차단

**잘못된 선택지 C의 문제점:**

* Outlier Detection은 Circuit Breaker 패턴
* 인스턴스를 **일시적으로 제외**하되 삭제하지 않음
* 복구 시도를 통해 정상화되면 다시 트래픽 수신

**참고 자료:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 문제 2: Rate Limiting 유형 비교

로컬 Rate Limiting과 글로벌 Rate Limiting의 비교로 옳은 것은?

A. 로컬 Rate Limiting이 정확도가 더 높다\
B. 글로벌 Rate Limiting이 성능이 더 빠르다\
C. 로컬 Rate Limiting은 각 Envoy 프록시가 독립적으로 제한한다\
D. 글로벌 Rate Limiting은 외부 서비스 없이 동작한다

<details>

<summary>정답 및 해설</summary>

**정답: C**

로컬 Rate Limiting은 **각 Envoy 프록시가 독립적으로** 요청을 제한합니다.

**해설:**

**로컬 vs 글로벌 Rate Limiting 비교:**

| 특성        | 로컬 Rate Limiting | 글로벌 Rate Limiting |
| --------- | ---------------- | ----------------- |
| **정확도**   | ❌ 낮음 (인스턴스별)     | ✅ 높음 (전체)         |
| **성능**    | ✅ 매우 빠름          | ⚠️ 약간 느림          |
| **복잡도**   | ✅ 낮음             | ⚠️ 높음 (외부 서비스 필요) |
| **사용 사례** | 일반적인 보호          | 정확한 제한 필요 시       |

**로컬 Rate Limiting의 특징:**

```yaml
# 각 파드당 100 req/s 제한
# 파드가 3개면 전체 300 req/s까지 허용됨
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: local-ratelimit
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100        # 최대 토큰 수
            tokens_per_fill: 10    # 초당 10개 추가
            fill_interval: 1s
```

**글로벌 Rate Limiting의 특징:**

```yaml
# 전체 100 req/s 제한
# 파드 개수와 무관하게 100 req/s까지만 허용
# 중앙 집중식 Rate Limit 서버 필요 (예: Redis)
```

**Token Bucket 알고리즘:**

**참고 자료:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 문제 3: Zone Aware Routing의 이점

Zone Aware Routing을 사용할 때 얻을 수 있는 이점으로 옳지 **않은** 것은?

A. 같은 AZ 내 통신으로 지연시간 감소\
B. 크로스 AZ 데이터 전송 비용 절감\
C. 모든 트래픽을 단일 AZ로 집중하여 성능 향상\
D. 장애 시 자동으로 다른 AZ로 장애조치

<details>

<summary>정답 및 해설</summary>

**정답: C**

Zone Aware Routing은 **트래픽을 단일 AZ에 집중하는 것이 아니라**, 같은 AZ를 우선하되 가용성을 위해 분산합니다.

**해설:**

**Zone Aware Routing의 올바른 동작:**

**Zone Aware Routing의 실제 이점:**

1. **지연시간 감소**:
   * 같은 AZ 내 통신: \~0.5ms
   * 크로스 AZ 통신: \~1-2ms
2. **비용 절감**:
   * AWS 크로스 AZ 전송: GB당 $0.01-0.02
   * 대용량 트래픽 환경에서 월 수백\~수천 달러 절감
3. **가용성 향상**:
   * 같은 AZ 파드 장애 시 자동으로 다른 AZ로 전환
   * 단일 AZ 집중은 **잘못된 접근** (가용성 저하)
4. **성능 최적화**:
   * 네트워크 홉 감소
   * 대역폭 최적화

**DestinationRule 설정 예시:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80   # 같은 AZ 80%
            "us-east-1/us-east-1b/*": 10   # 다른 AZ 10%
            "us-east-1/us-east-1c/*": 10   # 다른 AZ 10%
```

**참고 자료:**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 문제 4: Outlier Detection 파라미터

다음 Outlier Detection 설정에서 인스턴스가 제외되는 조건은?

```yaml
outlierDetection:
  consecutiveErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. 5초 동안 에러 발생 시\
B. 연속으로 5번 에러 발생 시\
C. 30초 동안 에러율 50% 초과 시\
D. 30초마다 무조건 제외

<details>

<summary>정답 및 해설</summary>

**정답: B**

`consecutiveErrors: 5`는 **연속으로 5번** 에러가 발생하면 인스턴스를 제외합니다.

**해설:**

**Outlier Detection 주요 파라미터:**

| 파라미터                   | 설명        | 기본값 | 권장값      |
| ---------------------- | --------- | --- | -------- |
| **consecutiveErrors**  | 연속 에러 임계값 | 5   | 3-10     |
| **interval**           | 분석 주기     | 10s | 10s-60s  |
| **baseEjectionTime**   | 최소 제외 시간  | 30s | 30s-300s |
| **maxEjectionPercent** | 최대 제외 비율  | 10% | 10%-50%  |

**파라미터 상세 설명:**

**consecutiveErrors**

```yaml
# 민감한 서비스 (빠른 감지)
consecutiveErrors: 3

# 일반 서비스
consecutiveErrors: 5

# 관대한 설정 (오탐 방지)
consecutiveErrors: 10
```

**interval**

```yaml
# 빠른 감지 (높은 부하)
interval: 10s

# 일반적인 경우
interval: 30s

# 안정적인 서비스
interval: 60s
```

**baseEjectionTime**

```yaml
# 빠른 복구 시도
baseEjectionTime: 30s

# 일반적인 경우
baseEjectionTime: 60s

# 신중한 복구
baseEjectionTime: 300s
```

**maxEjectionPercent**

```yaml
# 보수적 (안정성 우선)
maxEjectionPercent: 10

# 균형잡힌 설정
maxEjectionPercent: 30

# 공격적 (성능 우선)
maxEjectionPercent: 50
```

**완전한 DestinationRule 예제:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5          # 연속 5번 에러
      interval: 30s                 # 30초마다 평가
      baseEjectionTime: 30s         # 30초 동안 제외
      maxEjectionPercent: 50        # 최대 50%까지 제외 가능
      minHealthPercent: 50          # 최소 50%는 정상 유지
```

**동작 예시:**

```
T=0: Pod-1이 5번 연속 에러 → 제외됨
T=30s: interval 주기 도래, 제외된 파드 복구 시도
T=30s: Pod-1이 정상이면 → 복구됨
T=30s: Pod-1이 여전히 에러 → 추가 30s 제외 (누적)
```

**참고 자료:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 문제 5: Token Bucket 알고리즘

다음 Rate Limiting 설정에서 평균 초당 처리 가능한 요청 수는?

```yaml
token_bucket:
  max_tokens: 100
  tokens_per_fill: 10
  fill_interval: 1s
```

A. 10 req/s\
B. 100 req/s\
C. 110 req/s\
D. 1000 req/s

<details>

<summary>정답 및 해설</summary>

**정답: A**

`tokens_per_fill: 10`과 `fill_interval: 1s`로 **초당 10개의 토큰**이 추가되므로, 평균 **10 req/s**입니다.

**해설:**

**Token Bucket 알고리즘 파라미터:**

* **max\_tokens**: 버킷에 저장할 수 있는 최대 토큰 수 (버스트 허용량)
* **tokens\_per\_fill**: 매 fill\_interval마다 추가할 토큰 수 (**평균 처리량**)
* **fill\_interval**: 토큰 추가 주기

**계산 방식:**

```
평균 요청 처리율 = tokens_per_fill / fill_interval
                = 10 / 1s
                = 10 req/s

버스트 처리량 = max_tokens
            = 100 req (짧은 순간)
```

**시간에 따른 동작:**

```
T=0: 버킷에 100개 토큰 (초기 상태)
     100개 요청 동시 처리 가능 ✅

T=0.1s: 버킷 비어있음 (0개)
        추가 요청 거부 ❌

T=1s: 10개 토큰 추가 (Refill)
      10개 요청 처리 가능 ✅

T=2s: 10개 토큰 추가
      10개 요청 처리 가능 ✅

평균: 10 req/s (지속 가능한 처리량)
버스트: 100 req/s (짧은 순간만)
```

**실전 설정 예시:**

```yaml
# 시나리오 1: 일반 API 엔드포인트
token_bucket:
  max_tokens: 100        # 버스트 100개 허용
  tokens_per_fill: 10    # 평균 10 req/s
  fill_interval: 1s

# 시나리오 2: 고성능 API
token_bucket:
  max_tokens: 1000       # 버스트 1000개 허용
  tokens_per_fill: 100   # 평균 100 req/s
  fill_interval: 1s

# 시나리오 3: 제한적인 리소스
token_bucket:
  max_tokens: 10         # 버스트 10개만
  tokens_per_fill: 1     # 평균 1 req/s
  fill_interval: 1s
```

**EnvoyFilter 완전한 예제:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100        # 버스트
            tokens_per_fill: 10    # 평균 처리량
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**참고 자료:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 주관식 문제 (6-10번)

### 문제 6: Outlier Detection 구현

프로덕션 환경에서 실행 중인 `product-service`가 간헐적으로 느려지고 타임아웃이 발생합니다. Outlier Detection을 구현하여 문제있는 인스턴스를 자동으로 제외하고 싶습니다. 다음 요구사항을 만족하는 DestinationRule을 작성하세요:

**요구사항:**

* 연속 3번 에러 발생 시 제외
* 20초마다 평가
* 제외된 인스턴스는 60초 후 복구 시도
* 최대 30%까지만 제외 가능
* 502, 503, 504 게이트웨이 에러도 감지

<details>

<summary>예시 답안</summary>

**답변:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: product-service-outlier
  namespace: production
spec:
  host: product-service
  trafficPolicy:
    outlierDetection:
      # 연속 에러 임계값
      consecutiveErrors: 3
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 3  # 502, 503, 504 감지

      # 분석 주기
      interval: 20s

      # 제외 시간
      baseEjectionTime: 60s

      # 최대 제외 비율
      maxEjectionPercent: 30

      # 최소 정상 비율 (70% 이상 유지)
      minHealthPercent: 70

      # 최소 요청 수 (5개 이상일 때만 평가)
      enforcingConsecutive5xx: 100
      enforcingConsecutiveGatewayFailure: 100
```

**해설:**

**1. consecutiveErrors vs consecutive5xxErrors vs consecutiveGatewayErrors**

| 파라미터                         | 감지 대상                | 사용 사례       |
| ---------------------------- | -------------------- | ----------- |
| **consecutiveErrors**        | 모든 에러 (5xx, 연결 실패 등) | 일반적인 에러 감지  |
| **consecutive5xxErrors**     | 5xx 에러만              | 서버 에러만 감지   |
| **consecutiveGatewayErrors** | 502, 503, 504만       | 게이트웨이 문제 감지 |

**2. 파라미터 설명**

**interval: 20s**

* Outlier Detection을 20초마다 실행
* 각 인스턴스의 에러율을 평가

**baseEjectionTime: 60s**

* 제외된 인스턴스는 최소 60초 동안 트래픽 수신 안 함
* 반복 제외 시 시간이 증가 (60s → 120s → 180s...)

**maxEjectionPercent: 30**

* 동시에 최대 30%의 인스턴스만 제외 가능
* 예: 10개 파드면 최대 3개까지만 제외
* 가용성 보장

**minHealthPercent: 70**

* 최소 70%의 인스턴스는 정상 상태 유지
* maxEjectionPercent와 보완 관계

**3. 동작 예시**

```
초기 상태: 10개 파드 모두 정상

T=0:   Pod-1이 3번 연속 503 에러
       → Pod-1 제외 (9개 정상)

T=20s: Pod-2가 3번 연속 502 에러
       → Pod-2 제외 (8개 정상)

T=40s: Pod-3이 3번 연속 504 에러
       → Pod-3 제외 (7개 정상)

T=40s: Pod-4가 3번 연속 에러 발생
       → 제외 안 됨 (maxEjectionPercent 30% 도달)
       → 30% = 3개까지만 제외 가능

T=60s: Pod-1 복구 시도
       → 정상이면 트래픽 수신 재개
```

**4. 모니터링**

```bash
# Outlier Detection 이벤트 확인
kubectl logs <envoy-pod> -c istio-proxy | grep outlier

# Prometheus 메트릭
envoy_cluster_outlier_detection_ejections_active
envoy_cluster_outlier_detection_ejections_total
```

**5. 프로덕션 고려사항**

**민감한 서비스 (빠른 감지):**

```yaml
outlierDetection:
  consecutiveErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

**안정적인 서비스 (오탐 방지):**

```yaml
outlierDetection:
  consecutiveErrors: 10
  interval: 60s
  baseEjectionTime: 300s
  maxEjectionPercent: 10
```

**참고 자료:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 문제 7: 로컬 Rate Limiting 적용

`api-gateway` 서비스가 DDoS 공격을 받고 있습니다. 로컬 Rate Limiting을 적용하여 각 Envoy 프록시에서 초당 50개 요청으로 제한하고, 버스트로 최대 200개까지 허용하려고 합니다. EnvoyFilter를 작성하세요.

추가 요구사항:

* Rate limit이 적용될 때 `X-RateLimit-Limit` 헤더 추가
* 429 응답 시 `Retry-After: 1` 헤더 포함

<details>

<summary>예시 답안</summary>

**답변:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: api-gateway-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter

          # Token Bucket 설정
          token_bucket:
            max_tokens: 200         # 버스트: 최대 200개
            tokens_per_fill: 50     # 평균: 초당 50개
            fill_interval: 1s       # 1초마다 50개 추가

          # Rate Limit 활성화
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100        # 100%
              denominator: HUNDRED

          # Rate Limit 강제
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100        # 100%
              denominator: HUNDRED

          # 응답 헤더 추가
          response_headers_to_add:
          # Rate limit 정보
          - append: false
            header:
              key: X-RateLimit-Limit
              value: '50'

          # 현재 남은 토큰 수
          - append: false
            header:
              key: X-RateLimit-Remaining
              value: '%DYNAMIC_METADATA(envoy.extensions.filters.http.local_ratelimit:tokens_remaining)%'

          # Rate limit이 적용되었는지 여부
          - append: false
            header:
              key: X-Local-Rate-Limit
              value: 'true'

          # 429 응답 시 Retry-After 헤더
          rate_limited_status:
            code: TOO_MANY_REQUESTS  # 429

          # Retry-After 헤더 추가 (별도 패치 필요)

  # 429 응답 시 Retry-After 헤더 추가
  - applyTo: HTTP_ROUTE
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        response_headers_to_add:
        - header:
            key: Retry-After
            value: '1'
          append: false
```

**해설:**

**1. Token Bucket 계산**

```
평균 처리율: tokens_per_fill / fill_interval
          = 50 / 1s
          = 50 req/s

버스트 처리: max_tokens
          = 200 req (짧은 순간)
```

**2. 시나리오별 동작**

**정상 트래픽 (40 req/s):**

```
초당 50개 토큰 추가, 40개 사용
→ 항상 여유 있음 ✅
```

**버스트 트래픽 (순간 200 req/s):**

```
T=0: 200개 토큰 있음
     200개 요청 모두 처리 ✅

T=0.1s: 토큰 0개
        추가 요청 거부 ❌ (429 반환)

T=1s: 50개 토큰 추가
      50개 요청 처리 ✅
```

**지속적인 과부하 (100 req/s):**

```
초당 50개 토큰 추가
100개 요청 중 50개만 처리
나머지 50개는 429 반환 ❌
```

**3. 응답 헤더 예시**

**정상 요청:**

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 45
X-Local-Rate-Limit: true
```

**Rate limit 초과:**

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 0
X-Local-Rate-Limit: true
Retry-After: 1
```

**4. 경로별 Rate Limiting**

더 세밀한 제어가 필요하면 경로별로 다른 제한 설정:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: path-based-ratelimit
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter

          # 경로별 설정
          descriptors:
          # /api/login: 초당 10개
          - entries:
            - key: path
              value: /api/login
            token_bucket:
              max_tokens: 30
              tokens_per_fill: 10
              fill_interval: 1s

          # /api/search: 초당 100개
          - entries:
            - key: path
              value: /api/search
            token_bucket:
              max_tokens: 300
              tokens_per_fill: 100
              fill_interval: 1s
```

**5. 모니터링**

```bash
# Prometheus 메트릭
envoy_http_local_rate_limit_enabled
envoy_http_local_rate_limit_enforced
envoy_http_local_rate_limit_rate_limited

# 429 응답 횟수
sum(rate(istio_requests_total{response_code="429"}[5m]))
```

**참고 자료:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 문제 8: Zone Aware Routing 설정

AWS EKS 클러스터가 3개의 AZ (us-east-1a, us-east-1b, us-east-1c)에 분산되어 있습니다. `order-service`에 Zone Aware Routing을 설정하여 크로스 AZ 데이터 전송 비용을 절감하려고 합니다.

**요구사항:**

* 같은 AZ 파드에 70% 트래픽 전송
* 다른 AZ에 각각 15%씩 분산
* AZ 전체 장애 시 다른 AZ로 자동 장애조치
* 최소 50% 이상의 파드가 정상일 때만 Zone Aware 적용

<details>

<summary>예시 답안</summary>

**답변:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: order-service-locality
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        # Zone Aware Routing 활성화
        enabled: true

        # 트래픽 분산 비율
        distribute:
        # us-east-1a에서 시작한 트래픽
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 70   # 같은 AZ 70%
            "us-east-1/us-east-1b/*": 15   # 다른 AZ 15%
            "us-east-1/us-east-1c/*": 15   # 다른 AZ 15%

        # us-east-1b에서 시작한 트래픽
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 70
            "us-east-1/us-east-1a/*": 15
            "us-east-1/us-east-1c/*": 15

        # us-east-1c에서 시작한 트래픽
        - from: us-east-1/us-east-1c/*
          to:
            "us-east-1/us-east-1c/*": 70
            "us-east-1/us-east-1a/*": 15
            "us-east-1/us-east-1b/*": 15

        # 장애조치 설정
        failover:
        # us-east-1a 장애 시
        - from: us-east-1/us-east-1a
          to: us-east-1/us-east-1b    # 1순위: us-east-1b

        # us-east-1b 장애 시
        - from: us-east-1/us-east-1b
          to: us-east-1/us-east-1c    # 1순위: us-east-1c

        # us-east-1c 장애 시
        - from: us-east-1/us-east-1c
          to: us-east-1/us-east-1a    # 1순위: us-east-1a

    # Outlier Detection (정상 파드 판단)
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s

      # 최소 50% 이상 정상 유지
      minHealthPercent: 50
```

**해설:**

**1. Kubernetes 노드 레이블 확인**

AWS EKS는 자동으로 Topology 레이블을 추가합니다:

```bash
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# 출력 예시:
# NAME                          ZONE         REGION
# ip-10-0-1-10.ec2.internal     us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal     us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal     us-east-1c   us-east-1
```

**2. Locality 계층 구조**

```
Region/Zone/SubZone

예시:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-east-1/us-east-1c/*
```

**3. 트래픽 흐름 다이어그램**

**4. 비용 절감 계산**

**시나리오**: 월 1TB 트래픽

**Zone Aware 없음 (균등 분산):**

```
전체 트래픽: 1TB
크로스 AZ: 66.7% (667GB)
비용: 667GB × $0.01 = $6.67
```

**Zone Aware 적용 (70% 같은 AZ):**

```
전체 트래픽: 1TB
크로스 AZ: 30% (300GB)
비용: 300GB × $0.01 = $3.00

절감액: $6.67 - $3.00 = $3.67 (55% 절감)
```

**대용량 환경 (월 100TB):**

```
Zone Aware 없음: $667
Zone Aware 적용: $300

절감액: $367/월 = $4,404/년
```

**5. 장애조치 시나리오**

**정상 상태:**

```
us-east-1a의 Client
→ 70% us-east-1a 파드
→ 15% us-east-1b 파드
→ 15% us-east-1c 파드
```

**us-east-1a 전체 장애:**

```
us-east-1a의 Client
→ failover: us-east-1b로 전환
→ 100% us-east-1b 파드

(us-east-1b 장애 시 → us-east-1c로 전환)
```

**일부 파드 비정상 (Outlier Detection):**

```
us-east-1a: 2개 파드 (1개 정상, 1개 제외)
us-east-1b: 2개 파드 (모두 정상)

→ minHealthPercent: 50% 충족
→ Zone Aware 계속 적용
→ 비정상 파드는 트래픽 수신 안 함
```

**6. 모니터링**

```bash
# Locality별 트래픽 확인
kubectl exec <pod> -c istio-proxy -- \
  curl localhost:15000/clusters | grep locality

# Prometheus 쿼리
# 같은 Zone 내 트래픽 비율
sum(rate(istio_requests_total{
  source_workload_namespace="production",
  source_canonical_service="client",
  destination_canonical_service="order-service"
}[5m])) by (source_cluster_zone, destination_cluster_zone)
```

**7. AWS EKS 특화 설정**

**EKS 노드 그룹을 AZ별로 구성:**

```yaml
# eksctl config
managedNodeGroups:
- name: ng-us-east-1a
  availabilityZones: ["us-east-1a"]
  labels:
    topology.kubernetes.io/zone: us-east-1a

- name: ng-us-east-1b
  availabilityZones: ["us-east-1b"]
  labels:
    topology.kubernetes.io/zone: us-east-1b

- name: ng-us-east-1c
  availabilityZones: ["us-east-1c"]
  labels:
    topology.kubernetes.io/zone: us-east-1c
```

**Pod를 AZ별로 고르게 분산:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 9
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: order-service
```

**참고 자료:**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 문제 9: 복합 Resilience 전략

`payment-service`는 외부 결제 API를 호출하는 중요한 서비스입니다. 다음 복합 Resilience 전략을 구현하세요:

1. **Outlier Detection**: 연속 3번 에러 시 인스턴스 제외
2. **Retry**: 502, 503, 504 에러 시 최대 3번 재시도
3. **Timeout**: 요청당 5초 타임아웃
4. **Circuit Breaker**: 에러율 50% 초과 시 서비스 전체 차단

DestinationRule과 VirtualService를 작성하세요.

<details>

<summary>예시 답안</summary>

**답변:**

```yaml
# ========================================
# DestinationRule: Outlier Detection + Circuit Breaker
# ========================================
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service-resilience
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    # Connection Pool (Circuit Breaker)
    connectionPool:
      tcp:
        maxConnections: 100          # 최대 동시 연결 수
      http:
        http1MaxPendingRequests: 50  # 대기 중인 요청 수
        http2MaxRequests: 100        # HTTP/2 최대 요청
        maxRequestsPerConnection: 2  # 연결당 최대 요청
        maxRetries: 3                # 최대 재시도 횟수

    # Outlier Detection
    outlierDetection:
      # 연속 에러 감지
      consecutiveErrors: 3
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 3

      # 분석 주기
      interval: 10s

      # 제외 시간
      baseEjectionTime: 30s

      # 최대 제외 비율
      maxEjectionPercent: 50

      # 에러율 기반 제외 (Circuit Breaker)
      splitExternalLocalOriginErrors: true

      # 에러율 50% 초과 시 제외
      enforcingLocalOriginSuccessRate: 100
      enforcingSuccessRate: 100
      successRateMinimumHosts: 3
      successRateRequestVolume: 10
      successRateStdevFactor: 1900  # 50% 에러율

---
# ========================================
# VirtualService: Retry + Timeout
# ========================================
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-service-retry
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - match:
    - uri:
        prefix: /payment
    route:
    - destination:
        host: payment-service
        port:
          number: 8080

    # Timeout 설정
    timeout: 5s

    # Retry 설정
    retries:
      attempts: 3                    # 최대 3번 재시도
      perTryTimeout: 2s              # 재시도당 2초 타임아웃
      retryOn: 5xx,reset,connect-failure,refused-stream,retriable-4xx
      retryRemoteLocalities: true    # 다른 AZ 파드로 재시도
```

**해설:**

**1. Outlier Detection (인스턴스 수준)**

**연속 에러 감지:**

```yaml
consecutiveErrors: 3
consecutive5xxErrors: 3
consecutiveGatewayErrors: 3
```

* 특정 파드가 3번 연속 에러 → 해당 파드만 제외
* 다른 정상 파드는 계속 트래픽 수신

**2. Circuit Breaker (서비스 수준)**

**에러율 기반 차단:**

```yaml
successRateStdevFactor: 1900  # 50% 에러율
successRateMinimumHosts: 3    # 최소 3개 파드
successRateRequestVolume: 10  # 최소 10개 요청
```

**동작 방식:**

```
에러율 < 50%: 정상 동작
에러율 ≥ 50%: 서비스 전체 차단 (Circuit Open)

Circuit Open 상태:
- 모든 요청 즉시 503 반환
- baseEjectionTime 후 복구 시도 (Circuit Half-Open)
```

**3. Retry 전략**

**재시도 조건 (retryOn):**

| 조건                  | 설명                     |
| ------------------- | ---------------------- |
| **5xx**             | 모든 5xx 에러              |
| **reset**           | 연결 리셋                  |
| **connect-failure** | 연결 실패                  |
| **refused-stream**  | HTTP/2 스트림 거부          |
| **retriable-4xx**   | 재시도 가능한 4xx (409, 429) |

**재시도 타임라인:**

```
T=0:    첫 번째 시도 (2s timeout)
T=2s:   타임아웃 → 2번째 시도
T=4s:   타임아웃 → 3번째 시도
T=6s:   타임아웃 → 최종 실패 (503 반환)

총 시간: 6s (하지만 VirtualService timeout: 5s)
→ 5초 후 최종 실패
```

**4. Timeout 계층**

```
VirtualService timeout: 5s
↓
Retry perTryTimeout: 2s
↓
DestinationRule connectionPool
```

**전체 타임라인:**

```
attempt=1: 2s timeout
attempt=2: 2s timeout
attempt=3: 1s timeout (5s 전체 제한 도달)
```

**5. 완전한 동작 예시**

**시나리오 1: 일시적인 네트워크 문제**

```
Pod-1: 502 에러 (1번째)
→ Retry → Pod-2: 200 OK ✅

결과: 클라이언트는 성공 응답 수신
Pod-1: 에러 카운트 1 (아직 제외 안 됨)
```

**시나리오 2: 특정 파드 문제**

```
Pod-1: 503 에러 (1번째)
→ Retry → Pod-1: 503 에러 (2번째)
→ Retry → Pod-1: 503 에러 (3번째)
→ Pod-1 제외됨 ❌

→ Retry → Pod-2: 200 OK ✅

결과: 클라이언트는 성공 응답 수신
Pod-1: 30초 동안 트래픽 차단
```

**시나리오 3: 서비스 전체 장애 (Circuit Breaker)**

```
모든 파드에서 에러율 50% 초과
→ Circuit Breaker Open
→ 모든 새 요청 즉시 503 반환 (재시도 없음)

baseEjectionTime 후:
→ Circuit Half-Open
→ 일부 요청으로 테스트
→ 성공하면 Circuit Closed
→ 실패하면 다시 Circuit Open
```

**6. Connection Pool (추가 보호)**

```yaml
connectionPool:
  tcp:
    maxConnections: 100
  http:
    http1MaxPendingRequests: 50
    http2MaxRequests: 100
```

**동작:**

* 동시 연결 수 100개 초과 → 새 연결 거부
* 대기 요청 50개 초과 → 503 반환
* 서비스 과부하 방지

**7. 모니터링**

```bash
# Circuit Breaker 상태
kubectl exec <pod> -c istio-proxy -- \
  curl localhost:15000/stats | grep circuit_breakers

# Outlier Detection 이벤트
kubectl logs <pod> -c istio-proxy | grep outlier

# Prometheus 쿼리
# 재시도 횟수
sum(rate(envoy_cluster_upstream_rq_retry[5m]))

# Circuit Breaker 발동 횟수
sum(rate(envoy_cluster_circuit_breakers_default_rq_pending_open[5m]))

# 타임아웃 발생 횟수
sum(rate(istio_requests_total{response_flags=~".*UT.*"}[5m]))
```

**8. 프로덕션 고려사항**

**외부 API 호출 시:**

```yaml
# 더 관대한 설정
timeout: 10s
retries:
  attempts: 5
  perTryTimeout: 3s
outlierDetection:
  consecutiveErrors: 10
  baseEjectionTime: 300s
```

**내부 서비스 간:**

```yaml
# 더 엄격한 설정
timeout: 1s
retries:
  attempts: 2
  perTryTimeout: 500ms
outlierDetection:
  consecutiveErrors: 3
  baseEjectionTime: 30s
```

**참고 자료:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Traffic Management](https://github.com/Atom-oh/kubernetes-docs/blob/main/ko/service-mesh/istio/traffic/README.md)

</details>

***

### 문제 10: 성능 최적화 및 비용 절감

대규모 마이크로서비스 환경에서 월 네트워크 비용이 $5,000입니다. Istio Resilience 기능을 활용하여 성능을 최적화하고 비용을 절감하는 종합 전략을 수립하세요.

**현재 상황:**

* 3개 AZ에 균등 분산된 100개 서비스
* 월 트래픽: 500TB
* 평균 응답 시간: 150ms
* 에러율: 3%

**목표:**

* 크로스 AZ 비용 50% 절감
* 평균 응답 시간 100ms 이하
* 에러율 1% 이하

<details>

<summary>예시 답안</summary>

**답변:**

### 종합 Resilience 전략

#### 1. Zone Aware Routing (비용 절감 + 성능 향상)

**DestinationRule 템플릿:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: zone-aware-template
  namespace: production
spec:
  host: "*"  # 모든 서비스에 적용
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 10
            "us-east-1/us-east-1c/*": 10
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1c/*": 10
        - from: us-east-1/us-east-1c/*
          to:
            "us-east-1/us-east-1c/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1b/*": 10
```

**비용 절감 계산:**

```
현재 상태 (균등 분산):
- 크로스 AZ 트래픽: 66.7% (333TB)
- 비용: 333TB × $0.015/GB = $5,000

Zone Aware 적용 (80% 같은 AZ):
- 크로스 AZ 트래픽: 20% (100TB)
- 비용: 100TB × $0.015/GB = $1,500

절감액: $5,000 - $1,500 = $3,500/월 (70% 절감)
```

**성능 향상:**

```
현재 (크로스 AZ 지연):
- 평균 지연시간: ~1.5ms

Zone Aware 적용:
- 같은 AZ 지연: ~0.3ms
- 크로스 AZ 지연: ~1.5ms
- 가중 평균: 0.3×0.8 + 1.5×0.2 = 0.54ms

개선: 1.5ms → 0.54ms (64% 개선)
```

#### 2. Outlier Detection (에러율 감소)

**민감한 감지 설정:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: strict-outlier-detection
  namespace: production
spec:
  host: "*"
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 3           # 빠른 감지
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2    # 게이트웨이 에러 더 민감

      interval: 10s                  # 빠른 평가
      baseEjectionTime: 60s          # 충분한 복구 시간
      maxEjectionPercent: 30         # 가용성 보장

      # 에러율 기반 제외
      enforcingSuccessRate: 100
      successRateMinimumHosts: 3
      successRateRequestVolume: 10
```

**에러율 감소 효과:**

```
현재 에러율: 3%
- 문제있는 파드가 트래픽 계속 수신
- 재시도로 인한 추가 부하

Outlier Detection 적용:
- 문제 파드 즉시 제외
- 정상 파드로만 라우팅
- 예상 에러율: 1% 이하 ✅

추가 효과:
- 재시도 횟수 감소 → 네트워크 부하 감소
- 응답 시간 개선
```

#### 3. Rate Limiting (서비스 보호)

**티어별 Rate Limiting:**

```yaml
# Critical 서비스 (결제, 인증)
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: critical-service-ratelimit
spec:
  workloadSelector:
    labels:
      tier: critical
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          token_bucket:
            max_tokens: 500
            tokens_per_fill: 100
            fill_interval: 1s

---
# Standard 서비스
apiVersion: networking.istio.io/v1beta1
kind: EnvoyFilter
metadata:
  name: standard-service-ratelimit
spec:
  workloadSelector:
    labels:
      tier: standard
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
```

#### 4. 종합 성능 최적화

**응답 시간 개선 전략:**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: performance-optimization
  namespace: production
spec:
  host: "*"
  trafficPolicy:
    # Connection Pool 최적화
    connectionPool:
      tcp:
        maxConnections: 1000
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        idleTimeout: 60s

    # Zone Aware Routing
    loadBalancer:
      localityLbSetting:
        enabled: true

    # Outlier Detection
    outlierDetection:
      consecutiveErrors: 3
      interval: 10s
      baseEjectionTime: 60s

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: performance-routing
  namespace: production
spec:
  hosts:
  - "*"
  http:
  - route:
    - destination:
        host: service

    # Timeout 최적화
    timeout: 3s

    # Retry 전략
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: 5xx,reset,connect-failure
```

#### 5. 구현 로드맵

**Phase 1: Zone Aware Routing (Week 1-2)**

```bash
# 1. 노드 Topology 확인
kubectl get nodes -L topology.kubernetes.io/zone

# 2. 파드 AZ 분산 확인
kubectl get pods -o wide | awk '{print $7}' | sort | uniq -c

# 3. Zone Aware DestinationRule 적용
kubectl apply -f zone-aware-template.yaml

# 4. 비용 모니터링 설정
# CloudWatch에서 크로스 AZ 데이터 전송 모니터링
```

**예상 효과:**

* 비용: $5,000 → $1,500 (70% 절감)
* 지연시간: 150ms → 120ms (20% 개선)

**Phase 2: Outlier Detection (Week 3-4)**

```bash
# 1. 각 서비스에 Outlier Detection 적용
kubectl apply -f strict-outlier-detection.yaml

# 2. 모니터링 대시보드 설정
# Grafana에서 Outlier ejection 메트릭 확인

# 3. 에러율 모니터링
```

**예상 효과:**

* 에러율: 3% → 1.5% (50% 감소)
* 지연시간: 120ms → 100ms (추가 개선)

**Phase 3: Rate Limiting (Week 5-6)**

```bash
# 1. 티어별 Rate Limiting 적용
kubectl apply -f critical-service-ratelimit.yaml
kubectl apply -f standard-service-ratelimit.yaml

# 2. 429 응답률 모니터링
# 정상 트래픽은 차단되지 않도록 조정
```

**예상 효과:**

* DDoS 보호
* 서비스 안정성 향상
* 불필요한 리소스 소비 방지

#### 6. 모니터링 및 검증

**Grafana 대시보드:**

```promql
# 크로스 AZ 트래픽 비율
100 * sum(rate(istio_requests_total{
  source_cluster_zone!="",
  destination_cluster_zone!="",
  source_cluster_zone!=destination_cluster_zone
}[5m])) /
sum(rate(istio_requests_total{
  source_cluster_zone!="",
  destination_cluster_zone!=""
}[5m]))

# 평균 응답 시간
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket[5m]))
  by (le, destination_service_name)
)

# 에러율
100 * sum(rate(istio_requests_total{response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total[5m]))

# Outlier ejection 이벤트
sum(rate(envoy_cluster_outlier_detection_ejections_active[5m]))

# Rate limit 적용 횟수
sum(rate(envoy_http_local_rate_limit_rate_limited[5m]))
```

#### 7. 최종 결과 예측

| 지표             | 현재     | 목표     | 예상 결과             |
| -------------- | ------ | ------ | ----------------- |
| **월 네트워크 비용**  | $5,000 | $2,500 | $1,500 (✅ 70% 절감) |
| **평균 응답 시간**   | 150ms  | 100ms  | 95ms (✅ 37% 개선)   |
| **에러율**        | 3%     | 1%     | 0.8% (✅ 73% 감소)   |
| **크로스 AZ 트래픽** | 66.7%  | 33%    | 20% (✅ 70% 감소)    |

#### 8. 추가 최적화 기회

**캐싱 전략:**

```yaml
# Redis/Memcached를 동일 AZ에 배치
# 캐시 히트율 향상 + 네트워크 비용 절감
```

**Service Mesh 최적화:**

```yaml
# Ambient Mode 고려 (Sidecar 오버헤드 감소)
# 리소스 사용량 30-50% 감소
# 추가 응답 시간 개선
```

**Auto Scaling:**

```yaml
# HPA + Zone Aware Routing
# 트래픽 패턴에 따라 AZ별로 독립적 스케일링
# 비용 효율성 극대화
```

**참고 자료:**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 점수 계산

* 객관식 1-5번: 각 10점 (총 50점)
* 주관식 6-10번: 각 10점 (총 50점)
* **총점: 100점**

**평가 기준:**

* 90-100점: 우수 (Istio Resilience 전문가)
* 80-89점: 양호 (프로덕션 적용 가능)
* 70-79점: 보통 (추가 학습 권장)
* 60-69점: 미흡 (기본 개념 복습 필요)
* 0-59점: 재학습 필요

## 학습 자료

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
