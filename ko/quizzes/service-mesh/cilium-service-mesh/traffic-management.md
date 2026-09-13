# Cilium Service Mesh 트래픽 관리 퀴즈

Cilium1.20.1/Gateway API1.6.1 기준입니다. 완전한 예시와 공식 근거는 [트래픽 관리 본문](../../../service-mesh/cilium-service-mesh/02-traffic-management.md)을 참고하세요.

### 1. CiliumEnvoyConfig에서 HTTP 라우팅 규칙을 정의할 때 사용하는 Envoy 필터는?

- **A.** envoy.filters.network.tcp_proxy
- **B.** envoy.filters.network.http_connection_manager
- **C.** envoy.filters.http.fault
- **D.** envoy.filters.network.redis_proxy

<details>
<summary>정답 및 설명</summary>

**정답: B. envoy.filters.network.http_connection_manager**

HTTP Connection Manager는 HTTP 트래픽을 처리하고 inline route_config 또는 RDS로 경로를 가져옵니다. Router HTTP 필터와 참조하는 Cluster 리소스도 필요하며 백엔드 Service 목록만으로는 충분하지 않습니다.

</details>

### 2. CiliumNetworkPolicy에서 L7 HTTP 규칙을 정의할 때 사용할 수 있는 필드가 아닌 것은?

- **A.** method
- **B.** path
- **C.** headers
- **D.** body

<details>
<summary>정답 및 설명</summary>

**정답: D. body**

HTTP 정책은 method, path, headers와 구조화된 headerMatches를 검사할 수 있지만 임의의 요청 본문 필드를 인가하지는 못합니다. 인증·애플리케이션 인가는 별도로 처리해야 합니다.

</details>

### 3. Cilium1.20.1에서 Kafka 토픽 접근 권한은 어떻게 제어해야 하나요?

- **A.** 기존 Cilium rules.kafka를 그대로 사용
- **B.** HTTP 본문 규칙으로 Kafka 메시지를 검사
- **C.** Kafka 브로커 ACL을 사용하고 접근 가능 여부는 별도 L4 정책으로 제어
- **D.** 모든 규칙을 삭제해도 토픽 권한은 유지된다고 가정

<details>
<summary>정답 및 설명</summary>

**정답: C. Kafka 브로커 ACL을 사용하고 접근 가능 여부는 별도 L4 정책으로 제어**

Cilium1.20.1의 L7 규칙 스키마는 HTTP와 DNS를 지원하고 기존 rules.kafka 객체를 거부합니다. 브로커 접근은 L4 정책, 토픽·그룹·작업 권한은 Kafka TLS/SASL과 브로커 ACL로 제어하세요. 폐기된 Kafka 규칙을 제거하는 것만으로 토픽 권한 제어가 유지되지는 않습니다.

</details>

### 4. 해당 Cilium eBPF 로드 밸런싱에서 Maglev가 제공하는 것은?

- **A.** 완전히 무작위 분배
- **B.** 백엔드 집합 변경 시 재할당을 줄이는 일관된 백엔드 선택
- **C.** 제거된 백엔드와의 연결 생존 보장
- **D.** 가능한 가장 낮은 메모리 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. 백엔드 집합 변경 시 재할당을 줄이는 일관된 백엔드 선택**

Maglev는 해당 외부 로드 밸런싱에서 백엔드 집합이 바뀔 때 흐름 재할당을 줄입니다. ClientIP 세션 어피니티와 별개이며 사용할 수 없는 백엔드의 연결 유지를 보장하지 않습니다. Cilium의 소켓 수준 east–west 경로에는 이 Maglev 선택이 적용되지 않습니다.

</details>

### 5. Gateway API에서 HTTPRoute의 가중치 기반 트래픽 분할을 설정할 때 올바른 구성은?

- **A.** split 필드 사용
- **B.** backendRefs에 weight 필드 지정
- **C.** trafficPolicy 사용
- **D.** destinationRule 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. backendRefs에 weight 필드 지정**

backendRefs의 가중치는 상대적 선택 확률입니다. 90과10은90:10 비율이며 요청10개마다 정확한 개수나 사용자별 세션 유지를 보장하지 않습니다. Service·포트·부모 Listener가 올바르게 해석되고 경로를 수락해야 합니다.

</details>

### 6. CiliumEnvoyConfig에서 재시도 정책을 구성할 때 retry_on 필드에 지정할 수 있는 조건이 아닌 것은?

- **A.** 5xx
- **B.** reset
- **C.** timeout
- **D.** connect-failure

<details>
<summary>정답 및 설명</summary>

**정답: C. timeout**

timeout은 retry_on 토큰이 아닙니다. per_try_timeout은 첫 시도를 포함한 각 upstream 시도의 제한이며 backoff 간격이 아닙니다. 본문은 안전한 GET만 재시도하고 다른 메서드의 재시도를 명시적으로 끄며, 라우팅 전에 클라이언트의 Envoy 재시도·타임아웃 제어 헤더를 제거합니다.

</details>

### 7. Cilium에서 DNS L7 정책을 사용할 때의 주요 이점은?

- **A.** DNS 서버 성능 향상
- **B.** 특정 도메인에 대한 DNS 쿼리만 허용
- **C.** DNS 캐시 무효화
- **D.** DNS over HTTPS 지원

<details>
<summary>정답 및 설명</summary>

**정답: B. 특정 도메인에 대한 DNS 쿼리만 허용**

DNS 규칙은 선택한 신뢰 resolver로 보내는 질의 이름을 제한합니다. 반환된 주소로의 연결을 자동 허용하거나 데이터 유출·DoH 방지를 보장하지 않습니다. 목적지·포트 정책을 별도로 추가하고 UDP/TCP, 실제 resolver와 검색 목록 동작도 고려하세요.

</details>

### 8. CiliumEnvoyConfig에서 로컬 Rate Limiting을 구성할 때 사용하는 필터는?

- **A.** envoy.filters.http.ratelimit
- **B.** envoy.filters.http.local_ratelimit
- **C.** envoy.filters.http.bandwidth_limit
- **D.** envoy.filters.http.throttle

<details>
<summary>정답 및 설명</summary>

**정답: B. envoy.filters.http.local_ratelimit**

envoy.filters.http.local_ratelimit은 명시적인 enabled/enforced 비율과 토큰 버킷을 사용합니다. 경로별 오버라이드를 포함하여 이 비율의 기본값은0%입니다. 예시는 worker thread가 공유하는 Envoy 프로세스별 버킷이며 클러스터 전체 또는 사용자별 쿼터가 아닙니다.

</details>

### 9. Gateway API에서 HTTP -> HTTPS 리다이렉트를 구성할 때 사용하는 필터 타입은?

- **A.** URLRewrite
- **B.** RequestMirror
- **C.** RequestRedirect
- **D.** ResponseHeaderModifier

<details>
<summary>정답 및 설명</summary>

**정답: C. RequestRedirect**

RequestRedirect로 scheme:https 리다이렉트를 반환할 수 있습니다. 301은 영구 리다이렉트지만 클라이언트에서 요청 메서드를 바꿀 수 있습니다. HTTP Listener 경로를 별도로 구성하고 유효한 HTTPS Listener·인증서를 준비하며, 쓰기를 메서드 변경 방식으로 조용히 리다이렉트하지 마세요.

</details>

### 10. Cilium Service Mesh에서 트래픽 미러링(shadowing)의 용도는?

- **A.** 트래픽 암호화
- **B.** 프로덕션 트래픽을 테스트 환경으로 복제
- **C.** 로드 밸런싱 최적화
- **D.** 캐시 무효화

<details>
<summary>정답 및 설명</summary>

**정답: B. 프로덕션 트래픽을 테스트 환경으로 복제**

request_mirror_policies는 shadow 백엔드로 요청을 복사하고 그 응답을 호출자 결과에 사용하지 않습니다. 하지만 데이터를 복사하고 리소스를 소비하며 부수 효과를 만들 수 있습니다. 본문은 승인된 GET/HEAD를 격리된 백엔드로 미러링하고 다른 메서드는 복사하지 않습니다. 사용자 영향0을 보장하지는 않습니다.

</details>

### 11. 현재 Envoy는 weighted_clusters의 총가중치를 어떻게 결정하나요?

- **A.** 전체 요청 개수를 제한
- **B.** Cluster 가중치의 합계를 사용하며 total_weight는 폐기됨
- **C.** 가중치를 타임아웃으로 처리
- **D.** 모든 요청을 가중치가 가장 낮은 Cluster로 전달

<details>
<summary>정답 및 설명</summary>

**정답: B. Cluster 가중치의 합계를 사용하며 total_weight는 폐기됨**

현재 Envoy는 개별 Cluster 가중치의 합계를 사용합니다. total_weight는 폐기되어 수정 예시에서는 생략합니다. 90과10은90:10의 상대 선택 비율이며 자동 승격·롤백이나 시간 구간별 엄격한 요청 쿼터가 아닙니다.

</details>

### 12. Gateway API의 HTTPRoute에서 헤더 기반 라우팅을 구성할 때 matches 섹션에 사용하는 필드는?

- **A.** headerMatchers
- **B.** headers
- **C.** requestHeaders
- **D.** matchHeaders

<details>
<summary>정답 및 설명</summary>

**정답: B. headers**

HTTPRoute.matches.headers는 헤더 일치 조건을 표현합니다. 하나의 match 안에 있는 여러 헤더는 AND 관계이며 Gateway API의 경로·헤더 우선순위에 따라 선택합니다. 클라이언트가 보낸 버전·카나리 헤더가 인증을 의미하지는 않습니다.

</details>
