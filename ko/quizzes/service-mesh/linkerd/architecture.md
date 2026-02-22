# Linkerd 아키텍처 퀴즈

이 퀴즈는 Linkerd 아키텍처에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Linkerd 컨트롤 플레인의 핵심 컴포넌트가 아닌 것은?

A. Destination Controller
B. Identity Controller
C. Proxy Injector
D. Envoy Proxy

<details>
<summary>정답 및 설명</summary>

**정답: D. Envoy Proxy**

**설명:**
Linkerd 컨트롤 플레인은 Destination, Identity, Proxy Injector로 구성됩니다. Envoy는 Istio의 데이터 플레인 프록시이며, Linkerd는 Rust로 작성된 자체 linkerd2-proxy를 사용합니다.

</details>

### 2. linkerd2-proxy가 작성된 프로그래밍 언어는?

A. Go
B. C++
C. Rust
D. Java

<details>
<summary>정답 및 설명</summary>

**정답: C. Rust**

**설명:**
linkerd2-proxy는 Rust로 작성되어 메모리 안전성과 높은 성능을 제공합니다. 약 10MB의 메모리만 사용하고 1ms 미만의 p99 지연 시간을 추가합니다.

</details>

### 3. Destination Controller의 주요 역할이 아닌 것은?

A. 서비스 디스커버리
B. 인증서 발급
C. ServiceProfile 정보 제공
D. 엔드포인트 업데이트

<details>
<summary>정답 및 설명</summary>

**정답: B. 인증서 발급**

**설명:**
인증서 발급은 Identity Controller의 역할입니다. Destination Controller는 서비스 디스커버리, 엔드포인트 업데이트, ServiceProfile 및 TrafficSplit 정책 배포를 담당합니다.

</details>

### 4. Linkerd의 인증서 계층 구조에서 가장 상위에 있는 것은?

A. Workload Certificate
B. Identity Issuer
C. Trust Anchor
D. Proxy Certificate

<details>
<summary>정답 및 설명</summary>

**정답: C. Trust Anchor**

**설명:**
인증서 계층은 Trust Anchor(Root CA) → Identity Issuer(Intermediate CA) → Workload Certificate 순입니다. Trust Anchor는 PKI의 루트로 모든 인증서 체인의 신뢰 기반입니다.

</details>

### 5. 워크로드 인증서의 기본 유효 기간은?

A. 1시간
B. 24시간
C. 7일
D. 30일

<details>
<summary>정답 및 설명</summary>

**정답: B. 24시간**

**설명:**
Linkerd 워크로드 인증서의 기본 유효 기간은 24시간입니다. 프록시는 만료 전에 자동으로 인증서를 갱신합니다. 짧은 유효 기간은 인증서 유출 시 위험을 최소화합니다.

</details>

### 6. Proxy Injector가 동작하는 Kubernetes 메커니즘은?

A. DaemonSet
B. CronJob
C. Admission Webhook
D. Custom Controller

<details>
<summary>정답 및 설명</summary>

**정답: C. Admission Webhook**

**설명:**
Proxy Injector는 Mutating Admission Webhook으로 동작합니다. Pod 생성 요청을 가로채서 linkerd-proxy 사이드카와 linkerd-init init 컨테이너를 자동으로 주입합니다.

</details>

### 7. linkerd-init 컨테이너의 역할은?

A. 프록시 설정 다운로드
B. iptables 규칙 설정
C. 인증서 생성
D. 메트릭 수집

<details>
<summary>정답 및 설명</summary>

**정답: B. iptables 규칙 설정**

**설명:**
linkerd-init은 Init 컨테이너로 실행되어 iptables 규칙을 설정합니다. 이 규칙은 모든 인바운드/아웃바운드 트래픽을 linkerd-proxy로 리다이렉트합니다.

</details>

### 8. Linkerd 프록시의 인바운드 포트는?

A. 4140
B. 4143
C. 4191
D. 8080

<details>
<summary>정답 및 설명</summary>

**정답: B. 4143**

**설명:**
Linkerd 프록시 포트: 4143(인바운드), 4140(아웃바운드), 4191(admin/metrics). 인바운드 포트는 다른 서비스에서 오는 트래픽을 수신합니다.

</details>

### 9. SPIFFE ID 형식으로 올바른 것은?

A. `spiffe://cluster/namespace/service`
B. `spiffe://trust-domain/ns/namespace/sa/service-account`
C. `https://linkerd.io/identity/namespace/pod`
D. `urn:linkerd:identity:namespace:pod`

<details>
<summary>정답 및 설명</summary>

**정답: B. `spiffe://trust-domain/ns/namespace/sa/service-account`**

**설명:**
Linkerd의 SPIFFE ID는 `spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>` 형식입니다. 예: `spiffe://root.linkerd.cluster.local/ns/production/sa/web-server`

</details>

### 10. Istio의 Envoy와 비교했을 때 linkerd2-proxy의 특징이 아닌 것은?

A. 더 적은 메모리 사용량
B. Wasm 확장 지원
C. 더 낮은 지연 시간
D. 더 작은 바이너리 크기

<details>
<summary>정답 및 설명</summary>

**정답: B. Wasm 확장 지원**

**설명:**
linkerd2-proxy는 Wasm 확장을 지원하지 않습니다(제한적 확장성). 대신 약 10MB 메모리(Envoy ~50-100MB), <1ms p99 지연(Envoy 2-5ms), ~10MB 바이너리(Envoy ~60MB)로 더 경량입니다.

</details>

### 11. Identity Controller가 인증서를 발급하기 전에 검증하는 것은?

A. Pod의 IP 주소
B. ServiceAccount 토큰
C. 네임스페이스 레이블
D. ConfigMap 설정

<details>
<summary>정답 및 설명</summary>

**정답: B. ServiceAccount 토큰**

**설명:**
Identity Controller는 프록시가 제출한 CSR과 함께 전송된 ServiceAccount 토큰을 검증합니다. 이를 통해 프록시의 ID(SPIFFE ID)가 실제 워크로드와 일치하는지 확인합니다.

</details>

### 12. Linkerd 프록시 admin 포트(4191)가 제공하는 것이 아닌 것은?

A. Prometheus 메트릭
B. 상태 확인 엔드포인트
C. 트래픽 라우팅 설정
D. 프록시 버전 정보

<details>
<summary>정답 및 설명</summary>

**정답: C. 트래픽 라우팅 설정**

**설명:**
Admin 포트(4191)는 Prometheus 메트릭(/metrics), 상태 확인(/ready, /live), 프록시 정보를 제공합니다. 트래픽 라우팅 설정은 Destination Controller에서 gRPC로 프록시에 전달됩니다.

</details>
