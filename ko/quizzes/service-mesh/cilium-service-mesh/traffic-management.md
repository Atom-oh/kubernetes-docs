# Cilium Service Mesh 트래픽 관리 퀴즈

이 퀴즈는 Cilium Service Mesh의 L7 트래픽 관리, CiliumEnvoyConfig, 로드 밸런싱, 트래픽 분할, Gateway API 통합에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. CiliumEnvoyConfig에서 HTTP 라우팅 규칙을 정의할 때 사용하는 Envoy 필터는?

A. envoy.filters.network.tcp_proxy
B. envoy.filters.network.http_connection_manager
C. envoy.filters.http.fault
D. envoy.filters.network.redis_proxy

<details>
<summary>정답 및 설명</summary>

**정답: B. envoy.filters.network.http_connection_manager**

**설명:**
HTTP Connection Manager는 Envoy에서 HTTP 트래픽을 처리하는 핵심 필터입니다. 이 필터 내에서 route_config를 통해 경로 기반, 헤더 기반, 메서드 기반 라우팅 규칙을 정의할 수 있습니다.

</details>

### 2. CiliumNetworkPolicy에서 L7 HTTP 규칙을 정의할 때 사용할 수 있는 필드가 아닌 것은?

A. method
B. path
C. headers
D. body

<details>
<summary>정답 및 설명</summary>

**정답: D. body**

**설명:**
CiliumNetworkPolicy의 HTTP L7 규칙에서는 method(HTTP 메서드), path(URL 경로), headers(HTTP 헤더)를 기반으로 필터링할 수 있습니다. body(요청 본문)는 L7 규칙에서 지원되지 않습니다.

</details>

### 3. Cilium에서 Kafka L7 정책을 적용할 때 사용할 수 있는 apiKey가 아닌 것은?

A. produce
B. fetch
C. delete
D. metadata

<details>
<summary>정답 및 설명</summary>

**정답: C. delete**

**설명:**
Cilium의 Kafka L7 정책에서 지원하는 apiKey에는 produce(메시지 생산), fetch(메시지 소비), metadata(메타데이터 조회), offsetcommit, offsetfetch, joingroup 등이 있습니다. 'delete'는 지원되는 Kafka API 키가 아닙니다.

</details>

### 4. Cilium의 eBPF 기반 L4 로드 밸런싱에서 Maglev 해싱의 장점은?

A. 완전히 무작위 분배
B. 백엔드 변경 시에도 세션 유지
C. 가장 낮은 메모리 사용
D. L7 라우팅 지원

<details>
<summary>정답 및 설명</summary>

**정답: B. 백엔드 변경 시에도 세션 유지**

**설명:**
Maglev는 일관된 해싱 알고리즘으로, 백엔드 서버가 추가되거나 제거되어도 대부분의 기존 연결이 동일한 백엔드로 유지됩니다. 이는 상태가 있는 애플리케이션이나 세션 어피니티가 필요한 경우에 유용합니다.

</details>

### 5. Gateway API에서 HTTPRoute의 가중치 기반 트래픽 분할을 설정할 때 올바른 구성은?

A. split 필드 사용
B. backendRefs에 weight 필드 지정
C. trafficPolicy 사용
D. destinationRule 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. backendRefs에 weight 필드 지정**

**설명:**
Gateway API의 HTTPRoute에서 트래픽 분할은 backendRefs 배열의 각 백엔드에 weight 필드를 지정하여 구성합니다. 예: `weight: 90`과 `weight: 10`을 사용하면 90:10 비율로 트래픽이 분할됩니다.

</details>

### 6. CiliumEnvoyConfig에서 재시도 정책을 구성할 때 retry_on 필드에 지정할 수 있는 조건이 아닌 것은?

A. 5xx
B. reset
C. timeout
D. connect-failure

<details>
<summary>정답 및 설명</summary>

**정답: C. timeout**

**설명:**
Envoy의 retry_on 조건에는 5xx(서버 오류), reset(연결 리셋), connect-failure(연결 실패), retriable-4xx 등이 있습니다. 'timeout'은 직접적인 retry_on 조건이 아니며, per_try_timeout으로 각 재시도의 타임아웃을 설정합니다.

</details>

### 7. Cilium에서 DNS L7 정책을 사용할 때의 주요 이점은?

A. DNS 서버 성능 향상
B. 특정 도메인에 대한 DNS 쿼리만 허용
C. DNS 캐시 무효화
D. DNS over HTTPS 지원

<details>
<summary>정답 및 설명</summary>

**정답: B. 특정 도메인에 대한 DNS 쿼리만 허용**

**설명:**
DNS L7 정책을 사용하면 워크로드가 조회할 수 있는 도메인을 제한할 수 있습니다. matchPattern이나 matchName을 사용하여 허용된 도메인만 조회하도록 하여, 데이터 유출이나 악성 도메인 접근을 방지할 수 있습니다.

</details>

### 8. CiliumEnvoyConfig에서 로컬 Rate Limiting을 구성할 때 사용하는 필터는?

A. envoy.filters.http.ratelimit
B. envoy.filters.http.local_ratelimit
C. envoy.filters.http.bandwidth_limit
D. envoy.filters.http.throttle

<details>
<summary>정답 및 설명</summary>

**정답: B. envoy.filters.http.local_ratelimit**

**설명:**
로컬 Rate Limiting은 envoy.filters.http.local_ratelimit 필터를 사용합니다. 이 필터는 token_bucket 설정을 통해 요청 수를 제한합니다. envoy.filters.http.ratelimit은 외부 Rate Limit 서비스와 통신하는 글로벌 Rate Limiting에 사용됩니다.

</details>

### 9. Gateway API에서 HTTP -> HTTPS 리다이렉트를 구성할 때 사용하는 필터 타입은?

A. URLRewrite
B. RequestMirror
C. RequestRedirect
D. ResponseHeaderModifier

<details>
<summary>정답 및 설명</summary>

**정답: C. RequestRedirect**

**설명:**
Gateway API에서 RequestRedirect 필터를 사용하여 HTTP에서 HTTPS로 리다이렉트할 수 있습니다. scheme: https와 statusCode: 301을 설정하면 영구 리다이렉트가 구성됩니다.

</details>

### 10. Cilium Service Mesh에서 트래픽 미러링(shadowing)의 용도는?

A. 트래픽 암호화
B. 프로덕션 트래픽을 테스트 환경으로 복제
C. 로드 밸런싱 최적화
D. 캐시 무효화

<details>
<summary>정답 및 설명</summary>

**정답: B. 프로덕션 트래픽을 테스트 환경으로 복제**

**설명:**
트래픽 미러링은 프로덕션 트래픽의 복사본을 다른 서비스(예: 새 버전의 테스트 환경)로 전송합니다. 이를 통해 실제 트래픽으로 새 버전을 테스트하면서도 사용자에게 영향을 주지 않습니다. request_mirror_policies를 통해 구성합니다.

</details>

### 11. CiliumEnvoyConfig에서 weighted_clusters를 사용한 카나리 배포에서 total_weight의 역할은?

A. 전체 요청 수 제한
B. 가중치 합계의 기준값 정의
C. 타임아웃 설정
D. 연결 수 제한

<details>
<summary>정답 및 설명</summary>

**정답: B. 가중치 합계의 기준값 정의**

**설명:**
total_weight는 개별 클러스터 가중치의 합계 기준을 정의합니다. 예를 들어 total_weight: 100으로 설정하고 클러스터 A에 90, 클러스터 B에 10을 지정하면, 각각 90%와 10%의 트래픽을 받습니다.

</details>

### 12. Gateway API의 HTTPRoute에서 헤더 기반 라우팅을 구성할 때 matches 섹션에 사용하는 필드는?

A. headerMatchers
B. headers
C. requestHeaders
D. matchHeaders

<details>
<summary>정답 및 설명</summary>

**정답: B. headers**

**설명:**
HTTPRoute의 matches 섹션에서 headers 필드를 사용하여 헤더 기반 라우팅을 구성합니다. 각 헤더에 대해 name과 value를 지정하여 특정 헤더 값을 가진 요청을 다른 백엔드로 라우팅할 수 있습니다.

</details>
