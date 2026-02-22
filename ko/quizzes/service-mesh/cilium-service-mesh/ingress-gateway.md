# Cilium Service Mesh 인그레스 & 게이트웨이 퀴즈

이 퀴즈는 Cilium Ingress Controller, Gateway API, TLS 종료, EKS 통합 패턴에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Cilium Ingress Controller의 loadbalancerMode 옵션에서 'shared' 모드의 의미는?

A. 각 Ingress마다 별도의 로드밸런서 생성
B. 모든 Ingress가 하나의 로드밸런서를 공유
C. 로드밸런서 없이 NodePort만 사용
D. 내부 트래픽만 처리

<details>
<summary>정답 및 설명</summary>

**정답: B. 모든 Ingress가 하나의 로드밸런서를 공유**

**설명:**
loadbalancerMode: shared 설정은 모든 Ingress 리소스가 하나의 공유 로드밸런서를 사용하도록 합니다. 이는 비용 효율적이며, dedicated 모드는 각 Ingress마다 별도의 로드밸런서를 생성합니다.

</details>

### 2. Gateway API에서 HTTPRoute의 parentRefs 필드의 역할은?

A. 부모 Pod 정의
B. 이 라우트가 연결될 Gateway 지정
C. 상위 네임스페이스 참조
D. 상속할 정책 정의

<details>
<summary>정답 및 설명</summary>

**정답: B. 이 라우트가 연결될 Gateway 지정**

**설명:**
parentRefs는 HTTPRoute가 어떤 Gateway에 연결될지를 지정합니다. Gateway의 이름과 네임스페이스를 참조하여 라우트가 적용될 리스너를 결정합니다.

</details>

### 3. Cilium Ingress에서 TLS 패스스루를 활성화하는 어노테이션은?

A. ingress.cilium.io/tls-mode: passthrough
B. ingress.cilium.io/tls-passthrough: "true"
C. cilium.io/tls: passthrough
D. nginx.ingress.kubernetes.io/ssl-passthrough

<details>
<summary>정답 및 설명</summary>

**정답: B. ingress.cilium.io/tls-passthrough: "true"**

**설명:**
`ingress.cilium.io/tls-passthrough: "true"` 어노테이션을 사용하여 TLS 트래픽을 종료하지 않고 백엔드 서비스로 직접 전달합니다. 이는 백엔드에서 TLS를 처리해야 하는 경우에 유용합니다.

</details>

### 4. Gateway API의 Gateway 리소스에서 여러 프로토콜을 지원하기 위해 사용하는 필드는?

A. protocols
B. listeners
C. endpoints
D. handlers

<details>
<summary>정답 및 설명</summary>

**정답: B. listeners**

**설명:**
Gateway의 listeners 필드에 여러 리스너를 정의하여 HTTP, HTTPS, TCP, TLS 등 다양한 프로토콜을 지원할 수 있습니다. 각 리스너는 protocol, port, hostname 등을 개별적으로 설정할 수 있습니다.

</details>

### 5. EKS에서 Cilium Ingress에 NLB를 사용할 때 필요한 어노테이션은?

A. service.kubernetes.io/load-balancer-type: nlb
B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
C. eks.amazonaws.com/load-balancer: nlb
D. aws.load-balancer/type: network

<details>
<summary>정답 및 설명</summary>

**정답: B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"**

**설명:**
AWS EKS에서 Network Load Balancer를 사용하려면 `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` 어노테이션을 서비스에 추가해야 합니다. 추가로 scheme, target-type 등의 어노테이션으로 NLB 동작을 세부 설정할 수 있습니다.

</details>

### 6. Gateway API의 HTTPRoute에서 URL 재작성을 구성할 때 사용하는 filter 타입은?

A. PathRewrite
B. URLRewrite
C. RequestTransform
D. PathModifier

<details>
<summary>정답 및 설명</summary>

**정답: B. URLRewrite**

**설명:**
HTTPRoute의 filters 섹션에서 type: URLRewrite를 사용하여 요청 URL을 재작성할 수 있습니다. path와 hostname 모두 변경 가능합니다.

</details>

### 7. Cilium Gateway API에서 크로스 네임스페이스 라우팅을 허용하려면 Gateway의 어떤 설정이 필요한가요?

A. allowedRoutes.namespaces.from: All
B. allowedRoutes.namespaces.from: Selector
C. crossNamespace: true
D. routes.scope: cluster

<details>
<summary>정답 및 설명</summary>

**정답: B. allowedRoutes.namespaces.from: Selector**

**설명:**
Gateway의 listeners에서 allowedRoutes.namespaces.from: Selector를 설정하고, selector로 특정 레이블을 가진 네임스페이스의 라우트만 허용할 수 있습니다. 'All'은 모든 네임스페이스를 허용하고, 'Same'은 같은 네임스페이스만 허용합니다.

</details>

### 8. CiliumEnvoyConfig에서 서비스 헬스 체크를 구성할 때 사용하는 Envoy 리소스 타입은?

A. envoy.config.listener.v3.Listener
B. envoy.config.cluster.v3.Cluster
C. envoy.config.route.v3.Route
D. envoy.config.endpoint.v3.Endpoint

<details>
<summary>정답 및 설명</summary>

**정답: B. envoy.config.cluster.v3.Cluster**

**설명:**
헬스 체크 설정은 Cluster 리소스의 health_checks 필드에 정의합니다. HTTP 헬스 체크, TCP 헬스 체크, 간격, 임계값 등을 설정할 수 있습니다.

</details>

### 9. Gateway API에서 HTTP에서 HTTPS로 리다이렉트할 때 권장되는 statusCode는?

A. 302 (Found)
B. 307 (Temporary Redirect)
C. 301 (Moved Permanently)
D. 303 (See Other)

<details>
<summary>정답 및 설명</summary>

**정답: C. 301 (Moved Permanently)**

**설명:**
HTTP에서 HTTPS로의 영구 리다이렉트에는 301 상태 코드가 권장됩니다. 이는 브라우저와 검색 엔진에 URL이 영구적으로 변경되었음을 알려, 캐싱과 SEO에 유리합니다.

</details>

### 10. Cilium과 AWS Load Balancer Controller의 주요 차이점은?

A. Cilium은 L4만 지원
B. AWS LBC는 더 낮은 지연 시간 제공
C. Cilium은 추가 LB 비용 없이 노드 리소스만 사용
D. AWS LBC는 Gateway API를 완전히 지원

<details>
<summary>정답 및 설명</summary>

**정답: C. Cilium은 추가 LB 비용 없이 노드 리소스만 사용**

**설명:**
Cilium Ingress/Gateway는 노드의 eBPF와 Envoy를 사용하여 외부 트래픽을 처리하므로 별도의 AWS 로드밸런서 비용이 발생하지 않습니다. 반면 AWS LBC는 ALB/NLB를 프로비저닝하여 추가 비용이 발생합니다.

</details>

### 11. Gateway API의 TCPRoute는 어떤 용도로 사용되나요?

A. HTTP 트래픽 라우팅
B. TLS 종료가 필요한 트래픽
C. 원시 TCP 트래픽 라우팅 (비 HTTP)
D. UDP 트래픽 전용

<details>
<summary>정답 및 설명</summary>

**정답: C. 원시 TCP 트래픽 라우팅 (비 HTTP)**

**설명:**
TCPRoute는 데이터베이스 연결, 메시지 큐 등 HTTP가 아닌 원시 TCP 트래픽을 라우팅하는 데 사용됩니다. Gateway의 TCP 리스너와 함께 사용하여 비 HTTP 서비스에 대한 외부 접근을 제공합니다.

</details>

### 12. Cilium Ingress에서 클라이언트 IP를 보존하기 위해 사용하는 NLB 설정은?

A. X-Forwarded-For 헤더
B. Proxy Protocol
C. Source NAT 비활성화
D. Direct Server Return

<details>
<summary>정답 및 설명</summary>

**정답: B. Proxy Protocol**

**설명:**
NLB에서 클라이언트 IP를 보존하려면 Proxy Protocol을 활성화해야 합니다. `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` 어노테이션을 사용합니다. Envoy가 Proxy Protocol 헤더에서 원본 클라이언트 IP를 추출합니다.

</details>
