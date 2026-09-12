# Cilium Service Mesh 인그레스 & 게이트웨이 퀴즈

검토 기준: Cilium 1.20.1, Gateway API 1.6.1, AWS LBC 3.5.0. [본문](../../../service-mesh/cilium-service-mesh/05-ingress-gateway.md)과 공식 근거를 함께 확인합니다.

## 퀴즈 문제

### 1. Cilium Ingress의 `loadbalancerMode: shared`가 공유하는 것은?

- A. 클러스터의 모든 컨트롤러 프런트엔드
- B. 해당 모드를 사용하는 리소스의 Cilium Ingress 공유 Service
- C. 내부 NodePort만
- D. 모든 Gateway API Gateway의 로드 밸런서

<details>
<summary>정답 및 설명</summary>

**정답: B. 해당 모드를 사용하는 리소스의 Cilium Ingress 공유 Service**

shared 모드로 Cilium이 관리하는 Ingress에 적용됩니다. dedicated 재정의나 다른 컨트롤러는 별개입니다. GatewayClass 공유도 하나의 클라우드 로드 밸런서 공유를 의미하지 않습니다.

</details>

### 2. HTTPRoute를 Gateway의 HTTPS 리스너에만 명시적으로 연결하는 방법은?

- A. 부모 Pod 이름 지정
- B. `parentRefs`에 Gateway 이름과 `sectionName: https` 지정
- C. Route 네임스페이스만 지정
- D. 임의의 리스너 어노테이션 사용

<details>
<summary>정답 및 설명</summary>

**정답: B. `parentRefs`에 Gateway 이름과 `sectionName: https` 지정**

section 이름은 실제 리스너와 일치해야 하고 `allowedRoutes`가 연결을 허용하며 호스트·프로토콜도 호환되어야 합니다. 해당 부모의 Accepted/ResolvedRefs 상태를 확인합니다. 참조만으로 실제 도달성이 보장되지는 않습니다.

</details>

### 3. Cilium Ingress에서 TLS passthrough를 켜는 어노테이션은?

- A. `ingress.cilium.io/tls-mode: passthrough`
- B. `ingress.cilium.io/tls-passthrough: "true"`
- C. `cilium.io/tls: passthrough`
- D. nginx 전용 어노테이션

<details>
<summary>정답 및 설명</summary>

**정답: B. `ingress.cilium.io/tls-passthrough: "true"`**

백엔드가 TLS를 종료합니다. Ingress에 호스트와 경로 `/`가 필요하며 HTTP 경로가 아니라 SNI로 선택합니다. 백엔드는 원래 클라이언트 소켓 주소가 아닌 Envoy/노드 연결을 봅니다.

</details>

### 4. Gateway의 프로토콜과 포트를 설정하는 위치는?

- A. `protocols`
- B. `listeners`
- C. `endpoints`
- D. `handlers`

<details>
<summary>정답 및 설명</summary>

**정답: B. `listeners`**

리스너별로 프로토콜·포트와 해당 호스트·TLS·연결 설정을 정의합니다. 실제 프로토콜 조합은 컨트롤러에 따라 다릅니다. 예를 들어 LBC 3.5는 하나의 Gateway에 L4/NLB와 L7/ALB 리스너를 혼합할 수 없습니다.

</details>

### 5. 본문의 Cilium shared Ingress NLB 프런트엔드를 AWS LBC가 관리하도록 선택하는 구성은?

- A. 과거 `aws-load-balancer-type: nlb` 어노테이션만 사용
- B. Service의 `spec.loadBalancerClass: service.k8s.aws/nlb`, instance 대상, 할당된 NodePort
- C. EndpointSlice 확인 없는 IP 대상
- D. 임의의 EKS 네임스페이스 레이블

<details>
<summary>정답 및 설명</summary>

**정답: B. Service의 `spec.loadBalancerClass: service.k8s.aws/nlb`, instance 대상, 할당된 NodePort**

Helm에서는 `ingressController.service.loadBalancerClass`에 대응합니다. Cilium L7 shared Ingress의 합성 EndpointSlice에는 Pod 대상 참조가 없어 LBC IP 해석기가 건너뜁니다. EC2 instance/NodePort 전제도 검증해야 합니다.

</details>

### 6. 클라이언트 리다이렉트 없이 업스트림 호스트·경로를 바꾸는 HTTPRoute 필터는?

- A. `PathRewrite`
- B. `URLRewrite`
- C. `RequestTransform`
- D. `RequestRedirect`

<details>
<summary>정답 및 설명</summary>

**정답: B. `URLRewrite`**

URLRewrite는 백엔드로 전달하는 요청을 바꿉니다. RequestRedirect는 클라이언트에 리다이렉트를 반환합니다. 본문의 헤더 값은 문자열 리터럴이며 UUID나 지연 시간을 자동 생성하지 않습니다.

</details>

### 7. 허용한 레이블이 있는 네임스페이스로만 교차 네임스페이스 Route 연결을 제한하는 설정은?

- A. `allowedRoutes.namespaces.from: All`
- B. `allowedRoutes.namespaces.from: Selector`와 일치 선택자
- C. `crossNamespace: true`
- D. `routes.scope: cluster`

<details>
<summary>정답 및 설명</summary>

**정답: B. `allowedRoutes.namespaces.from: Selector`와 일치 선택자**

All도 교차 네임스페이스 연결을 허용하지만 레이블로 제한하지 않습니다. Same은 Gateway 네임스페이스로 제한합니다. 다른 네임스페이스의 백엔드 Service를 참조하면 백엔드 쪽 ReferenceGrant가 추가로 필요하며 이는 별도 검사입니다.

</details>

### 8. Envoy 능동 상태 검사를 설정하는 위치는?

- A. Listener 이름
- B. Cluster의 `health_checks`
- C. Route 이름
- D. Endpoint 네임스페이스

<details>
<summary>정답 및 설명</summary>

**정답: B. Cluster의 `health_checks`**

동작하는 CEC에는 Service→Listener→경로→Cluster 연결도 필요합니다. HTTP 상태 검사 호스트·경로가 실제 백엔드에서 동작해야 합니다. 상태 범위 상한은 제외하므로 start 200/end 300이 전체 2xx를 포함합니다.

</details>

### 9. 요청 메서드·본문을 유지하는 영구 리다이렉트와 HTTP→HTTPS Route의 올바른 연결은?

- A. 302를 HTTP와 HTTPS 모두에 연결
- B. 307을 HTTP와 HTTPS 모두에 연결
- C. 308을 HTTP 리스너에만 연결
- D. 303을 HTTPS 리스너에만 연결

<details>
<summary>정답 및 설명</summary>

**정답: C. 308을 HTTP 리스너에만 연결**

308은 메서드·본문을 유지하는 영구 리다이렉트이고 307은 임시 리다이렉트입니다. 스킴 리다이렉트를 HTTP에만 연결하면 HTTPS 자기 리다이렉트 루프를 피합니다. 최초 평문 요청에 이미 실린 데이터까지 보호하지는 못합니다.

</details>

### 10. 올바른 비용·기능 비교는?

- A. Cilium은 클라우드 로드 밸런서가 절대 필요 없음
- B. AWS LBC가 항상 더 빠름
- C. Cilium 노드·프록시 비용과 클라우드 LB 비용이 함께 발생할 수 있으며 버전별 기능 비교가 필요함
- D. 모든 컨트롤러가 Gateway API 전체 기능 지원

<details>
<summary>정답 및 설명</summary>

**정답: C. Cilium 노드·프록시 비용과 클라우드 LB 비용이 함께 발생할 수 있으며 버전별 기능 비교가 필요함**

Cilium 앞에 ALB/NLB를 두면 해당 비용도 발생합니다. LBC 3.5는 HTTP/GRPC Route를 ALB, TCP/UDP/TLS Route를 NLB로 구성합니다. 워크로드 mTLS와 ACM 서버 인증서는 다른 메커니즘이며 성능은 동등 조건에서 측정해야 합니다.

</details>

### 11. 본문의 Gateway API 1.6.1 기준에서 TCPRoute가 하는 일은?

- A. HTTP 경로 검사
- B. 기본 TLS 종료
- C. 제공되는 v1 API로 불투명한 TCP 스트림 전달
- D. UDP 전용 처리

<details>
<summary>정답 및 설명</summary>

**정답: C. 제공되는 v1 API로 불투명한 TCP 스트림 전달**

TCP 안에 HTTP나 TLS가 있어도 TCPRoute가 해당 L7 기능을 갖지는 않습니다. 이 기준에서는 이전 TCPRoute v1alpha2를 제공하지 않습니다. TLSRoute v1의 SNI 라우팅에는 호환되는 TLS passthrough 리스너가 필요합니다.

</details>

### 12. 이 Cilium Ingress 구성에서 NLB PPv2를 켤 때 함께 조정할 것은?

- A. 클라이언트 X-Forwarded-For 헤더만
- B. NLB 송신과 Cilium `enableProxyProtocol` 수신, 상태 검사, 신뢰한 접근 경로
- C. 수신 설정은 필요 없음
- D. 모든 NLB에 PPv2가 필수

<details>
<summary>정답 및 설명</summary>

**정답: B. NLB 송신과 Cilium `enableProxyProtocol` 수신, 상태 검사, 신뢰한 접근 경로**

파서가 PROXY 헤더를 요구하므로 한쪽만 켜면 트래픽이 실패합니다. PPv2는 선택 사항이며 IP 보존은 대상 종류·속성에도 달려 있습니다. AWS LBC는 PPv2·instance 대상·externalTrafficPolicy Local 조합을 경고합니다. PROXY 메타데이터는 인증된 신원이 아닙니다.

</details>
