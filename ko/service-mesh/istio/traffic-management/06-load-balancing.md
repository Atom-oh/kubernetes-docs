# 로드 밸런싱

Istio는 Envoy를 통해 다양한 로드 밸런싱 알고리즘을 제공하여 트래픽을 효율적으로 분산시킵니다.

## 목차

1. [Why Load Balancing?](#why-load-balancing)
2. [로드 밸런싱 개요](#로드-밸런싱-개요)
3. [로드 밸런싱 알고리즘](#로드-밸런싱-알고리즘)
4. [Consistent Hash 상세](#consistent-hash-상세)
5. [Locality 기반 로드 밸런싱](#locality-기반-로드-밸런싱)
6. [Connection Pool 설정](#connection-pool-설정)
7. [실전 예제](#실전-예제)
8. [알고리즘 선택 가이드](#알고리즘-선택-가이드)
9. [모범 사례](#모범-사례)
10. [문제 해결](#문제-해결)

## Why Load Balancing?

### 효율적인 리소스 활용

로드 밸런싱은 트래픽을 여러 인스턴스에 분산시켜 시스템 전체의 처리량과 안정성을 향상시킵니다.

![로드 밸런싱 없이 모든 요청이 서비스 1에 몰려 100% 과부하가 나고 서비스 2·3은 0% 부하로 노는 상황과, 로드 밸런서가 같은 요청을 세 서비스에 33%·33%·34%로 나눠 균등하게 분산하는 상황을 나란히 비교해 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-0.html)

### 주요 이점

| 문제 | 로드 밸런싱 없이 | 로드 밸런싱 사용 |
|------|-----------------|----------------|
| **가용성** | 단일 장애점 (SPOF) | 장애 시 자동 우회 |
| **성능** | 특정 인스턴스 과부하 | 균등한 부하 분산 |
| **확장성** | 수평 확장 어려움 | 쉬운 스케일 아웃 |
| **응답 시간** | 불균일 (0-1000ms+) | 일관된 응답 시간 |
| **리소스 활용** | 비효율 (일부만 사용) | 효율적 리소스 활용 |

## 로드 밸런싱 개요

![클라이언트 요청이 로드 밸런서의 알고리즘을 거쳐 서로 다른 부하를 가진 세 파드 중 하나로 라우팅되는 개요를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-1.html)

## 로드 밸런싱 알고리즘

Istio는 다음과 같은 로드 밸런싱 알고리즘을 제공합니다.

### 알고리즘 비교

| 알고리즘 | 설명 | 사용 시나리오 | 장점 | 단점 |
|---------|------|-------------|------|-----|
| **ROUND_ROBIN** | 순차적 분배 (기본값) | 스테이트리스 서비스 | 간단, 공평 | 부하 불균형 가능 |
| **LEAST_REQUEST** | 최소 활성 요청 | 고성능 API, DB 연결 | 부하 균등화 | 약간의 오버헤드 |
| **RANDOM** | 무작위 분배 | 대량 트래픽 | 간단, 빠름 | 단기 불균형 가능 |
| **PASSTHROUGH** | 원본 목적지 | TCP 프록시, SNI 라우팅 | 유연성 | 제한적 제어 |
| **CONSISTENT_HASH** | 해시 기반 고정 | 세션 유지, 캐시 | Sticky 세션 | 불균형 가능 |

### 1. ROUND_ROBIN (기본값)

요청을 순차적으로 각 엔드포인트에 분배합니다.

![클라이언트가 보낸 4번의 요청을 로드 밸런서가 파드 1, 파드 2, 파드 3에 순서대로 라우팅하고 네 번째 요청에서 다시 파드 1로 순환하는 ROUND_ROBIN 동작을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-2.html)

**설정 예제:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-round-robin
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
```

**사용 사례:**
- 스테이트리스 REST API
- 동일한 성능을 가진 파드
- 기본 설정으로 충분한 경우

**장점:**
- 구현이 간단하고 예측 가능
- 공평한 분배

**단점:**
- 파드별 부하 차이를 고려하지 않음
- 긴 요청이 있으면 불균형 발생 가능

### 2. LEAST_REQUEST

가장 적은 활성 요청을 처리 중인 엔드포인트로 라우팅합니다.

![로드 밸런서가 세 파드의 활성 요청 수를 확인한 뒤 활성 요청이 가장 적은 파드 2로 새 요청을 라우팅하는 LEAST_REQUEST 동작을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-3.html)

**설정 예제:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-least-request
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      warmupDurationSecs: 60  # 60초 워밍업 (선택)
```

**고급 설정:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-least-request-advanced
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      warmupDurationSecs: 120  # 새 파드 워밍업
    connectionPool:
      http:
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
```

**사용 사례:**
- 응답 시간이 불균일한 API
- 데이터베이스 연결 풀
- 무거운 처리를 하는 서비스
- 실시간 부하 균형이 중요한 경우

**장점:**
- 실시간 부하에 따라 적응
- 응답 시간 일관성 향상
- 파드별 성능 차이 흡수

**단점:**
- 약간의 오버헤드 (활성 요청 추적)

### 3. RANDOM

무작위로 엔드포인트를 선택합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-random
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: RANDOM
```

**사용 사례:**
- 대량의 트래픽 (통계적으로 균등)
- 간단하고 빠른 선택이 필요한 경우
- 파드 성능이 동일한 경우

**장점:**
- 매우 빠른 선택
- 구현이 간단
- 대규모에서 통계적으로 균등

**단점:**
- 단기적으로 불균형 가능
- 예측 불가능

### 4. PASSTHROUGH

클라이언트가 지정한 원본 목적지로 직접 연결합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: tcp-passthrough
spec:
  host: "*.external-service.com"
  trafficPolicy:
    loadBalancer:
      simple: PASSTHROUGH
```

**사용 사례:**
- TCP 프록시
- SNI 기반 라우팅
- 외부 서비스 직접 연결
- TLS PASSTHROUGH 모드

**장점:**
- 원본 목적지 주소 유지
- 유연한 라우팅

**단점:**
- 로드 밸런싱 제어 제한적

### 5. LEAST_CONN (Deprecated → LEAST_REQUEST)

**주의**: `LEAST_CONN`은 **deprecated**되었으며, `LEAST_REQUEST`로 대체되었습니다.

**마이그레이션:**
```yaml
# ❌ 구버전 (deprecated)
trafficPolicy:
  loadBalancer:
    simple: LEAST_CONN

# ✅ 신규 버전
trafficPolicy:
  loadBalancer:
    simple: LEAST_REQUEST
```

## Consistent Hash 상세

Consistent Hash는 특정 속성을 기반으로 항상 같은 엔드포인트로 라우팅하여 세션 유지를 보장합니다.

### Consistent Hash 동작 원리

![동일한 쿠키를 가진 User A의 두 요청이 항상 같은 해시 값을 거쳐 같은 파드 1로 라우팅되어 세션이 유지되는 Consistent Hash 동작 원리를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-4.html)

### 1. HTTP Header 기반

특정 HTTP 헤더 값으로 해시를 계산합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: user-hash
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"
```

**사용 사례:**
- 사용자별 세션 유지
- API 키 기반 라우팅
- 테넌트별 격리

### 2. HTTP Cookie 기반

쿠키 값으로 해시를 계산하며, 쿠키가 없으면 자동 생성합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cookie-hash
spec:
  host: web-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "user-session"
          ttl: 3600s  # 1시간 TTL
```

**사용 사례:**
- 웹 애플리케이션 세션 유지
- 쇼핑 카트 유지
- 사용자 경험 일관성

### 3. Source IP 기반

클라이언트의 소스 IP 주소로 해시를 계산합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: source-ip-hash
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        useSourceIp: true
```

**사용 사례:**
- IP 기반 세션 유지
- Rate limiting (IP별)
- 지역별 캐시

**주의사항:**
- NAT 뒤에 있는 클라이언트는 같은 파드로 라우팅될 수 있음
- 프록시 사용 시 실제 클라이언트 IP를 확인해야 함

### 4. HTTP Query Parameter 기반

쿼리 파라미터 값으로 해시를 계산합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: query-param-hash
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpQueryParameterName: "user_id"
```

**사용 사례:**
- RESTful API에서 리소스 ID 기반 라우팅
- 캐시 친화적 라우팅
- 샤딩 전략

### 5. Minimum Ring Size 설정

Consistent Hash Ring의 최소 크기를 설정하여 재분배를 최소화합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: hash-with-ring-size
spec:
  host: cache-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-cache-key"
        minimumRingSize: 1024  # 기본값: 1024
```

**설명:**
- Ring size가 클수록 더 균등한 분배
- 파드 추가/제거 시 재분배되는 키의 비율 감소
- 메모리 사용량 약간 증가

**권장값:**
- 소규모 (< 10 파드): 1024 (기본값)
- 중규모 (10-50 파드): 2048
- 대규모 (50+ 파드): 4096

### Consistent Hash 조합 예제

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: advanced-consistent-hash
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          path: "/api"
          ttl: 7200s  # 2시간
        minimumRingSize: 2048
    connectionPool:
      http:
        maxRequestsPerConnection: 100
        idleTimeout: 300s
```

### Consistent Hash 주의사항

#### 1. 불균형 위험

![1000명의 사용자 중 80%가 같은 해시 값으로 몰려 파드 1이 과부하 상태가 되는 Consistent Hash의 불균형 위험을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-5.html)

**원인**: 특정 해시 값에 트래픽이 집중되는 경우

**해결책:**
- `minimumRingSize` 증가
- 여러 해시 키 조합 사용
- Bounded Load 알고리즘 고려 (Envoy 미지원)

#### 2. 파드 추가/제거 시 재분배

```yaml
# 파드 스케일 아웃 시
# - 기존: Pod 1, Pod 2, Pod 3
# - 신규: Pod 1, Pod 2, Pod 3, Pod 4
# - 결과: ~25%의 세션이 다른 파드로 재분배됨
```

**대응 방안:**
- Graceful shutdown 활용
- 세션 외부 저장소 사용 (Redis, Memcached)
- 서서히 스케일 조정

## Locality 기반 로드 밸런싱

Locality-based Load Balancing은 지리적으로 가까운 엔드포인트를 우선적으로 사용합니다.

### 기본 Locality 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-lb
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
```

### Locality 분배 비율 설정

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-distribute
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/zone-1/*
          to:
            "us-west/zone-1/*": 80  # 80%는 같은 zone
            "us-west/zone-2/*": 20  # 20%는 다른 zone
```

### Locality Failover

한 지역이 실패하면 다른 지역으로 자동 전환합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-failover
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failover:
        - from: us-west
          to: us-east
```

### Multi-Region 예제

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: global-service-locality
spec:
  host: global-api
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        distribute:
        # US West 클라이언트
        - from: us-west/*
          to:
            "us-west/*": 90      # 90% 로컬
            "us-east/*": 10      # 10% 원격 (DR)
        # US East 클라이언트
        - from: us-east/*
          to:
            "us-east/*": 90
            "us-west/*": 10
        failover:
        - from: us-west
          to: us-east
        - from: us-east
          to: us-west
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**사용 사례:**
- Multi-region 배포
- 지연 시간 최소화
- 리전 간 장애 복구
- 비용 최적화 (같은 AZ 통신)

## Connection Pool 설정

로드 밸런싱과 함께 Connection Pool을 설정하여 성능을 최적화합니다.

### HTTP/1.1 Connection Pool

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: http1-connection-pool
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100        # 최대 연결 수
        connectTimeout: 3s         # 연결 타임아웃
      http:
        http1MaxPendingRequests: 50  # 대기 요청 수
        maxRequestsPerConnection: 100 # 연결당 최대 요청
        idleTimeout: 300s             # 유휴 연결 타임아웃
```

### HTTP/2 Connection Pool

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: http2-connection-pool
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50
      http:
        http2MaxRequests: 1000     # HTTP/2 동시 요청
        maxRequestsPerConnection: 0 # 무제한 (HTTP/2 멀티플렉싱)
        h2UpgradePolicy: UPGRADE    # HTTP/2 업그레이드 허용
```

## 실전 예제

### 예제 1: 고성능 API 서비스

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-high-performance
  namespace: production
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      warmupDurationSecs: 60  # 새 파드 워밍업
    connectionPool:
      tcp:
        maxConnections: 200
        connectTimeout: 5s
      http:
        http2MaxRequests: 500
        maxRequestsPerConnection: 100
        idleTimeout: 300s
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**사용 시나리오:**
- 고성능 REST API
- 응답 시간이 불균일한 요청
- 파드별 성능 차이가 있는 환경

### 예제 2: 사용자 세션 기반 라우팅

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-session-affinity
spec:
  host: web-frontend
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          ttl: 7200s  # 2시간
        minimumRingSize: 2048
    connectionPool:
      tcp:
        maxConnections: 500
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 50
```

**사용 시나리오:**
- 웹 애플리케이션 세션 유지
- 쇼핑 카트 일관성
- 사용자별 캐시 활용

### 예제 3: Multi-Region 글로벌 서비스

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: global-api-multi-region
spec:
  host: global-api
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        distribute:
        # US West
        - from: us-west-1/*
          to:
            "us-west-1/*": 80
            "us-west-2/*": 15
            "us-east-1/*": 5
        # US East
        - from: us-east-1/*
          to:
            "us-east-1/*": 80
            "us-east-2/*": 15
            "us-west-1/*": 5
        # EU
        - from: eu-central-1/*
          to:
            "eu-central-1/*": 90
            "eu-west-1/*": 10
        failover:
        - from: us-west-1
          to: us-west-2
        - from: us-east-1
          to: us-east-2
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http2MaxRequests: 2000
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 60s
```

**사용 시나리오:**
- 글로벌 SaaS 서비스
- 지연 시간 최소화
- 리전별 장애 복구
- Cross-AZ 트래픽 비용 절감

### 예제 4: 캐시 서비스 최적화

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cache-service-optimized
spec:
  host: redis-cache
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-cache-key"
        minimumRingSize: 4096  # 큰 링 사이즈로 재분배 최소화
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 20
        maxRequestsPerConnection: 1000
        idleTimeout: 600s
    outlierDetection:
      consecutiveErrors: 3
      interval: 10s
      baseEjectionTime: 30s
```

**사용 시나리오:**
- 캐시 히트율 최대화
- 일관된 캐시 키 라우팅
- 샤딩 전략

### 예제 5: 데이터베이스 연결 풀

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-connection-pool
spec:
  host: postgres-primary
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50  # DB 연결 제한
        connectTimeout: 5s
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 100
    outlierDetection:
      consecutiveErrors: 3
      interval: 60s
      baseEjectionTime: 120s
```

**사용 시나리오:**
- 데이터베이스 연결 풀 관리
- 느린 쿼리 분산
- 연결 수 제한

### 예제 6: 대규모 트래픽 처리

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-traffic-service
spec:
  host: analytics-ingestion
  trafficPolicy:
    loadBalancer:
      simple: RANDOM  # 빠른 선택으로 오버헤드 최소화
    connectionPool:
      tcp:
        maxConnections: 5000
        connectTimeout: 1s
      http:
        http2MaxRequests: 10000
        maxRequestsPerConnection: 1000
        idleTimeout: 60s
    outlierDetection:
      consecutiveErrors: 10
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 20  # 대규모에서는 제한적 ejection
```

**사용 시나리오:**
- 이벤트 수집 (Analytics)
- 로그 수집
- 대용량 데이터 처리

## 알고리즘 선택 가이드

### 결정 트리

![세션 유지, 트래픽 규모, 응답 시간 불균일, 지리적 분산, TCP 프록시 여부를 차례로 물어 CONSISTENT_HASH, RANDOM, LEAST_REQUEST(+Locality Setting), PASSTHROUGH, 기본값 ROUND_ROBIN 중 알맞은 로드 밸런싱 알고리즘으로 안내하는 결정 트리를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-traffic-management-06-load-balancing-6.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-traffic-management-06-load-balancing-6.html)

### 서비스 유형별 권장 알고리즘

| 서비스 유형 | 권장 알고리즘 | 이유 |
|-----------|-------------|------|
| **REST API** | LEAST_REQUEST | 응답 시간 일관성 |
| **GraphQL API** | LEAST_REQUEST | 복잡한 쿼리 분산 |
| **gRPC** | LEAST_REQUEST | 스트리밍 부하 균형 |
| **웹 프론트엔드** | CONSISTENT_HASH (cookie) | 세션 유지 |
| **WebSocket** | CONSISTENT_HASH (header) | 연결 유지 |
| **캐시 서비스** | CONSISTENT_HASH (header) | 캐시 히트율 |
| **분석/로그 수집** | RANDOM | 대규모 처리 |
| **데이터베이스** | LEAST_REQUEST | 연결 풀 관리 |
| **Static Content** | ROUND_ROBIN | 간단하고 충분 |
| **Message Queue** | LEAST_REQUEST | 큐 부하 균형 |
| **배치 처리** | LEAST_REQUEST | 작업 분산 |

### 트래픽 패턴별 선택

```yaml
# 1. 균일한 작은 요청 (< 10ms)
trafficPolicy:
  loadBalancer:
    simple: ROUND_ROBIN  # 간단하고 효율적

# 2. 불균일한 요청 (10ms ~ 1s+)
trafficPolicy:
  loadBalancer:
    simple: LEAST_REQUEST  # 부하 적응

# 3. 매우 큰 트래픽 (10,000+ RPS)
trafficPolicy:
  loadBalancer:
    simple: RANDOM  # 오버헤드 최소화

# 4. 세션 기반 (사용자 상태)
trafficPolicy:
  loadBalancer:
    consistentHash:
      httpCookie:
        name: "session-id"
        ttl: 3600s

# 5. Multi-region
trafficPolicy:
  loadBalancer:
    simple: LEAST_REQUEST
    localityLbSetting:
      enabled: true
```

## 모범 사례

### 1. 알고리즘 선택 원칙

**✅ 좋은 예:**
```yaml
# 응답 시간이 불균일한 API
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-best-practice
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # 부하 적응
      warmupDurationSecs: 60  # 새 파드 워밍업
```

**❌ 나쁜 예:**
```yaml
# 응답 시간이 불균일한데 ROUND_ROBIN 사용
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-bad-practice
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN  # 부하 불균형 발생
```

### 2. Connection Pool 필수 설정

로드 밸런싱과 함께 항상 Connection Pool을 설정하세요:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: complete-lb-config
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:  # 필수
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 100
```

### 3. Outlier Detection 조합

Circuit Breaker와 함께 사용하여 장애 파드 제거:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: lb-with-outlier
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:  # 필수
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

### 4. Consistent Hash 사용 시 주의

```yaml
# ✅ 좋은 예: 세션 저장소 사용
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-with-redis-session
  annotations:
    description: "Uses Redis for session storage"
spec:
  host: web-frontend
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          ttl: 3600s
    # Redis 세션 저장소를 사용하므로
    # 파드 재시작 시에도 세션 유지
```

```yaml
# ⚠️ 주의: 로컬 세션만 사용
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-local-session-only
  annotations:
    warning: "No external session storage - sessions lost on pod restart"
spec:
  host: web-frontend
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpCookie:
          name: "session-id"
          ttl: 3600s
    # ⚠️ 문제: 파드 재시작 시 세션 손실
```

### 5. Multi-Region 배포

```yaml
# ✅ 좋은 예: Locality + Failover
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: multi-region-best-practice
spec:
  host: global-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/*
          to:
            "us-west/*": 80
            "us-east/*": 20
        failover:  # 필수
        - from: us-west
          to: us-east
```

### 6. 모니터링 및 메트릭

로드 밸런싱 효과를 모니터링하세요:

```yaml
# Prometheus 쿼리
# 파드별 요청 분포
sum by (destination_workload) (rate(istio_requests_total[5m]))

# 파드별 응답 시간
histogram_quantile(0.95,
  sum by (destination_workload, le) (
    rate(istio_request_duration_milliseconds_bucket[5m])
  )
)

# 활성 연결 수
sum by (destination_workload) (envoy_cluster_upstream_cx_active)
```

### 7. 점진적 적용

```yaml
# 1단계: 기본 ROUND_ROBIN
simple: ROUND_ROBIN

# 2단계: 모니터링 후 LEAST_REQUEST
simple: LEAST_REQUEST

# 3단계: Connection Pool 추가
simple: LEAST_REQUEST
connectionPool: ...

# 4단계: Outlier Detection 추가
simple: LEAST_REQUEST
connectionPool: ...
outlierDetection: ...
```

### 8. 문서화

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-lb
  annotations:
    # 설정 이유
    purpose: "Distribute load based on active requests"

    # 알고리즘 선택 근거
    algorithm-rationale: |
      - LEAST_REQUEST: Response times vary 10ms-500ms
      - warmupDurationSecs: New pods need 60s to warm up cache

    # 테스트 결과
    test-results: |
      - Load test: 1000 RPS evenly distributed
      - P95 latency: 150ms (improved from 300ms with ROUND_ROBIN)
      - No pod overload observed

    # 모니터링
    monitoring: |
      - Dashboard: grafana.example.com/d/istio-workload
      - Alert: High P95 latency > 500ms
```

## 문제 해결

### 불균형한 부하 분산

**증상:**
```bash
# 파드별 CPU 사용률 확인
kubectl top pods -n production

# 출력:
# NAME                CPU    MEMORY
# api-pod-1           80%    2Gi
# api-pod-2           20%    1Gi
# api-pod-3           15%    1Gi
```

**원인 및 해결:**

```yaml
# 1. ROUND_ROBIN → LEAST_REQUEST로 변경
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-fix
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # 변경

# 2. Warmup 추가
      warmupDurationSecs: 60

# 3. Outlier Detection 추가
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

### Consistent Hash 불균형

**증상:**
```bash
# Envoy 메트릭 확인
kubectl exec -it pod-name -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep upstream_rq_total

# 특정 파드에 요청 집중
```

**해결:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: hash-fix
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"
        minimumRingSize: 4096  # 2048 → 4096 증가
```

### Locality 기반 라우팅이 작동하지 않음

**확인 사항:**

```bash
# 1. 파드의 Locality 레이블 확인
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.topology\.kubernetes\.io/region}{"\t"}{.metadata.labels.topology\.kubernetes\.io/zone}{"\n"}{end}'

# 2. Istio Proxy 설정 확인
istioctl proxy-config endpoints pod-name | grep locality

# 3. DestinationRule 적용 확인
istioctl proxy-config clusters pod-name --fqdn api-service.default.svc.cluster.local -o json | jq '.[] | .localityLbEndpoints'
```

**수정:**

```yaml
# 노드 레이블 확인 및 추가
apiVersion: v1
kind: Node
metadata:
  labels:
    topology.kubernetes.io/region: us-west
    topology.kubernetes.io/zone: us-west-1
```

## 참고 자료

- [Istio Load Balancing](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings)
- [Envoy Load Balancing](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/load_balancing)
- [Consistent Hashing](https://www.toptal.com/big-data/consistent-hashing)
- [Locality Load Balancing](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
