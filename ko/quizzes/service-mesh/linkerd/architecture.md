# Linkerd 아키텍처 퀴즈

2026년 9월 11일 edge-26.9.1 기준으로 검토했습니다. 근거와 적용 한계는 [아키텍처 가이드](../../../service-mesh/linkerd/02-architecture.md)를 확인하세요.

### 1. Linkerd control-plane 구성 요소가 아닌 것은?

A. Destination controller

B. Identity controller

C. Proxy Injector

D. Envoy proxy

<details>
<summary>정답 및 설명</summary>

**정답: D**

Linkerd는 Rust data-plane proxy를 사용합니다. 고정한 control plane의 핵심 Deployment는 3개이며 policy 같은 추가 논리 controller가 그 안에서 실행됩니다. Envoy는 Istio sidecar/waypoint에 사용되며 Linkerd controller가 아닙니다.

</details>

### 2. linkerd2-proxy의 구현 언어는?

A. Go

B. C++

C. Rust

D. Java

<details>
<summary>정답 및 설명</summary>

**정답: C**

Rust로 작성되었습니다. 언어 선택만으로 보편적인 10MB, 1ms 미만 p99나 다른 proxy 대비 일정한 우위가 증명되지 않습니다. 실제 build, workload와 설정으로 비교해야 합니다.

</details>

### 3. Destination의 주된 책임이 아닌 것은?

A. Service discovery

B. Workload 인증서 발급

C. 지원 ServiceProfile 정보

D. Endpoint 갱신

<details>
<summary>정답 및 설명</summary>

**정답: B**

Workload 인증서는 Identity가 구성한 issuer credential로 발급합니다. Destination은 discovery/profile 정보를 제공하며 현재 Gateway API 라우팅·인가에는 policy controller도 관여합니다. 이전 TrafficSplit 확장이 현재 정책 모델의 전부는 아닙니다.

</details>

### 4. 기본 인증서 계층의 최상위 신뢰 기반은?

A. Workload 인증서

B. Identity issuer

C. Trust anchor

D. 고유 Pod 이름

<details>
<summary>정답 및 설명</summary>

**정답: C**

공개 trust anchor가 chain 검증의 신뢰 기반입니다. 보통 중간 issuer를 서명하고 issuer 키가 workload 인증서를 서명합니다. Linkerd가 모든 workload CSR을 처리하기 위해 root 개인 키를 필요로 하지는 않습니다.

</details>

### 5. Workload 인증서의 명목 기본 유효기간은?

A. 1시간

B. 24시간

C. 7일

D. 30일

<details>
<summary>정답 및 설명</summary>

**정답: B**

기본 issuance lifetime은 24시간이며 만료 전에 갱신합니다. 실제 유효기간·refresh 시점은 설정과 인증서 상태에 따릅니다. 인증서 갱신이 새 개인 키, issuer 회전이나 root 회전과 같지는 않습니다.

</details>

### 6. 자동 proxy 주입에 사용하는 Kubernetes 메커니즘은?

A. DaemonSet

B. CronJob

C. Mutating admission webhook

D. Application load balancer

<details>
<summary>정답 및 설명</summary>

**정답: C**

Webhook이 대상인 새 Pod를 변형합니다. 선택한 릴리스는 보통 native sidecar를 만들며 Linkerd CNI를 구성하면 linkerd-init을 생략합니다. 기존 Pod와 제외·override된 Pod는 별도로 고려해야 합니다.

</details>

### 7. Linkerd CNI가 없을 때 linkerd-init은 무엇을 하나요?

A. 모든 routing policy 다운로드

B. Pod network 트래픽 캡처 구성

C. Root CA 역할

D. Prometheus 시계열 저장

<details>
<summary>정답 및 설명</summary>

**정답: B**

Pod network namespace 안에 capture 규칙을 구성합니다. TCP를 redirect하기 전에 proxy UID와 설정된 bypass를 고려해야 합니다. 모든 protocol과 우회 port를 proxy가 처리한다는 뜻은 아닙니다.

</details>

### 8. 기본 inbound proxy port는?

A. 4140

B. 4143

C. 4191

D. 8080

<details>
<summary>정답 및 설명</summary>

**정답: B**

기본값은 inbound 4143, outbound 4140, admin/metrics 4191입니다. Inbound/outbound는 HTTP/gRPC 또는 opaque payload가 담긴 캡처 TCP를 처리합니다. Port는 변경할 수 있습니다.

</details>

### 9. Control-plane namespace가 linkerd, trust domain이 cluster.local일 때 my-app의 web-service ServiceAccount에 대한 기본 Kubernetes identity는?

A. spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service

B. web-service.my-app.serviceaccount.identity.linkerd.cluster.local

C. https://linkerd.io/identity/my-pod

D. urn:linkerd:my-pod

<details>
<summary>정답 및 설명</summary>

**정답: B**

Kubernetes TokenReview로 확인한 ServiceAccount identity를 DNS 이름으로 만듭니다. 같은 ServiceAccount를 쓰는 여러 Pod가 identity를 공유합니다. SPIFFE/SPIRE 외부 workload는 별도 bootstrap 경로이며 기본 Kubernetes URI 형식이 아닙니다.

</details>

### 10. 동일 조건의 benchmark 없이 정당화할 수 있는 비교는?

A. Linkerd는 항상 정확히 10MB 사용

B. 아키텍처·지원 API를 비교하고 실제 workload의 resource·latency 차이를 측정

C. Istio는 항상 p99 2–5ms 추가

D. 작은 memory request가 적은 실제 소비량을 증명

<details>
<summary>정답 및 설명</summary>

**정답: B**

설정한 예약, binary 크기, 실제 memory와 latency는 서로 다른 특성입니다. 같은 version/build, architecture, traffic과 policy로 비교하세요. 확장성도 제품의 일반 순위가 아니라 선택한 mode/API에서 확인해야 합니다.

</details>

### 11. 기본 Kubernetes identity validator가 확인하는 것은?

A. Pod IP만

B. 제출된 ServiceAccount token을 Kubernetes TokenReview로 검증

C. Namespace label만

D. ConfigMap 이름만

<details>
<summary>정답 및 설명</summary>

**정답: B**

릴리스 validator는 token을 인증하고 Kubernetes user 정보에서 DNS 형식 identity를 만듭니다. 인증 요청에는 identity와 CSR도 포함됩니다. 호출자가 그럴듯한 SPIFFE URI를 보냈다는 이유만으로 수용한다는 의미가 아닙니다.

</details>

### 12. 동적으로 갱신되는 routing/policy 설정은 보통 어떻게 proxy에 전달되나요?

A. Prometheus metric endpoint에 쓰기

B. Root 인증서 subject 변경

C. Streaming gRPC를 포함한 control-plane API

D. Node namespace에 임의 REDIRECT 규칙 적용

<details>
<summary>정답 및 설명</summary>

**정답: C**

Admin port의 health·metric interface는 control-plane policy API의 대체재가 아닙니다. 시작 시 environment/injection 설정과 동적 정책은 서로 다른 입력이므로 진단할 때 둘 다 확인해야 합니다.

</details>
