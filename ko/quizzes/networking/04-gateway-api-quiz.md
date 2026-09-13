# Gateway API 퀴즈

v1.6 API 기준과 본문의 구현체별 사전 요구사항을 따릅니다. 각 코드 예제는 별도 시나리오입니다.

## 1. Gateway API의 설계 목표가 아닌 것은 무엇인가요?

- A. 인프라/운영자/애플리케이션 리소스 소유권을 더 명시적으로 분리
- B. 여러 트래픽 프로토콜의 API 유형
- C. 기능 지원 수준이 정의된 표준 필드
- D. 모든 네트워크 기능을 단일 객체로 결합

<details>
<summary>정답 보기</summary>

D. GatewayClass, Gateway, Route가 책임을 분리합니다. 컨트롤러는 해당 API 버전·프로파일·기능을 구현해야 하며 소유권은 RBAC/admission으로 강제합니다. 표준 필드는 이식성을 높이지만 구현체별 확장이 사라지는 것은 아닙니다.

</details>

## 2. 역할 중심 모델에서 GatewayClass는 보통 누가 관리하나요?

- A. 모든 애플리케이션 개발자가 각각 관리
- B. 백엔드 Service 소유자만 관리
- C. 인프라 제공자 또는 플랫폼/네트워크 팀
- D. 미인증 애플리케이션 클라이언트

<details>
<summary>정답 보기</summary>

C. GatewayClass는 설치된 컨트롤러와 지원되는 구현체별 매개변수를 선택합니다. 플랫폼 운영자는 Gateway와 연결 정책을, 개발자는 Route를 관리합니다. 참조 대상 네임스페이스의 소유자는 ReferenceGrant를 관리합니다. 이는 운영 역할이며 자동으로 주어지는 Kubernetes 권한이 아닙니다.

</details>

## 3. TLS termination과 passthrough의 차이는 무엇인가요?

- A. Terminate는 암호화 바이트를 변경 없이 통과
- B. Terminate는 게이트웨이에서 다운스트림 TLS 종료, Passthrough는 백엔드에서 종료
- C. 둘 다 HTTPS 리스너에서 mode만 교체하면 됨
- D. Terminate는 항상 백엔드 평문을 강제

<details>
<summary>정답 보기</summary>

B. HTTPS 종료와 TLS passthrough의 리스너 구성은 다릅니다. 종료 후 백엔드 암호화는 지원되는 BackendTLSPolicy나 구현체 구성으로 별도 결정합니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-tls
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
  - name: tls-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
```

참조한 TLS Secret과 적절한 Route/백엔드는 존재해야 합니다. HTTPS 리스너의 mode만 바꿔 passthrough를 활성화할 수는 없습니다.

</details>

## 4. HTTPRoute는 백엔드 가중치 분배를 어떻게 표현하나요?

- A. trafficSplit 필드
- B. 여러 backendRefs의 weight
- C. 필수 canary 어노테이션
- D. 다른 API의 TrafficSplit CRD

<details>
<summary>정답 보기</summary>

B. 본문의 Gateway/Namespace와 기존 백엔드 Service가 있으면 다음과 같습니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-split
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

가중치는 상대 비율이며 합이 100일 필요는 없습니다. 작은 표본이 정확한 비율을 보장하지도 않습니다. 이 Gateway 뒤의 백엔드를 선택하며 기존 Ingress 프런트엔드와 새 Gateway 프런트엔드 사이의 클라이언트 전환은 수행하지 않습니다.

</details>

## 5. 다른 네임스페이스의 백엔드를 위한 ReferenceGrant는 어디에 만드나요?

- A. 항상 Route 네임스페이스
- B. 참조 대상 백엔드 네임스페이스에서 그 소유자가 생성
- C. kube-system에만 생성
- D. 클라이언트 워크스테이션

<details>
<summary>정답 보기</summary>

B. 참조받는 쪽에서 허용합니다. 예를 들면 다음과 같습니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-shared-api
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /shared
    backendRefs:
    - name: shared-api
      namespace: backend-services
      port: 80
```

shared-api Service가 backend-services에 있어야 하며 to.name이 그 Service로 허용 범위를 제한합니다. Route→Gateway 연결은 parentRefs와 allowedRoutes를 사용하고 그 연결 자체에는 ReferenceGrant가 필요하지 않습니다. Grant가 애플리케이션 사용자를 인증하지는 않습니다.

</details>

## 6. Gateway API v1.6 Standard 번들에 속하지 않는 리소스는 무엇인가요?

- A. GatewayClass
- B. GRPCRoute
- C. TCPRoute
- D. Istio VirtualService

<details>
<summary>정답 보기</summary>

D. VirtualService는 Istio API입니다. v1.6 Standard 번들에는 HTTPRoute, GRPCRoute, TCPRoute, TLSRoute, UDPRoute 등이 있습니다. TCPRoute가 Experimental이라는 기존 정답은 현재 맞지 않습니다. 채널과 API 버전은 다릅니다. Standard에서도 ReferenceGrant v1beta1과 v1을 함께 제공하고, Experimental 번들의 v1 리소스에 실험 필드가 추가될 수 있습니다.

</details>

## 7. 클라이언트 리다이렉트 없이 업스트림 요청을 바꾸는 필터는 무엇인가요?

- A. RequestHeaderModifier
- B. ResponseHeaderModifier
- C. URLRewrite
- D. RequestMirror

<details>
<summary>정답 보기</summary>

C. URLRewrite는 업스트림 경로/Host를 바꾸며 목적지는 여전히 backendRefs가 선택합니다. RequestRedirect는 클라이언트에 3xx를 반환합니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-rewrite
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /old-api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /new-api
        hostname: new-api.example.com
    backendRefs:
    - name: new-api-service
      port: 80
```

여기서 /old-api/users는 /new-api/users가 됩니다. ReplaceFullPath는 경로 전체를 교체하므로 기존 리라이트를 변환할 때 두 동작을 구분해야 합니다.

</details>

## 8. Gateway API 리소스를 조정하지 않는 구성 요소는 무엇인가요?

- A. Istio Gateway 컨트롤러
- B. Cilium Gateway 컨트롤러
- C. kube-proxy
- D. Envoy Gateway

<details>
<summary>정답 보기</summary>

C. kube-proxy는 Service 전달을 처리하고 백엔드 네트워크 경로에 참여할 수 있지만 GatewayClass/Gateway/Route를 조정하지 않습니다. Gateway API CRD 설치만으로 나열된 컨트롤러가 설치되지는 않습니다.

</details>

## 9. 기존 Ingress의 HTTP 경로 리라이트를 표현하는 Gateway API 구성은 무엇인가요?

- A. Gateway 객체 이름
- B. HTTPRoute URLRewrite 필터
- C. 임의 네임스페이스의 ReferenceGrant
- D. Namespace 레이블만 사용

<details>
<summary>정답 보기</summary>

B. 기존 리라이트 의미를 확인한 뒤 ReplaceFullPath 또는 ReplacePrefixMatch를 선택하세요. 본문의 고정 rewrite-target: /에는 접미사 보존이 아니라 전체 경로 교체가 필요합니다. 다른 Ingress 어노테이션은 Gateway 설정이나 컨트롤러 정책 CRD로 매핑될 수 있고 지원되는 대응 기능이 없을 수도 있습니다. HTTP→HTTPS 리다이렉트는 HTTP 리스너에 연결해야 합니다.

</details>

## 10. Gateway에 Route를 연결할 수 있는 네임스페이스를 어떻게 제한하나요?

- A. from: All이 하나의 네임스페이스로 제한
- B. from: Same은 자신의 네임스페이스 허용
- C. from: Selector는 Namespace 레이블로 선택
- D. B와 C 모두 유효하지만 범위가 다름

<details>
<summary>정답 보기</summary>

D. from에는 값 하나를 선택합니다. 셀렉터 예제는 다음과 같습니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-namespace-selector
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

레이블은 Route나 Pod가 아니라 Namespace에 있습니다. Namespace 레이블 변경 권한을 통제하세요. allowedRoutes는 연결을 제한하며 다른 네임스페이스 백엔드 접근이나 애플리케이션 요청을 인가하지 않습니다.

</details>

## 11. GRPCRoute에서 서비스의 특정 메서드를 고르는 매치는 무엇인가요?

- A. path.service와 path.method
- B. method.service와 method.method
- C. grpc.service와 grpc.method
- D. rpc.service와 rpc.method

<details>
<summary>정답 보기</summary>

B. 본문의 gRPC 리스너에서는 다음과 같습니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: quiz-grpc
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: grpc
  hostnames:
  - grpc.example.com
  rules:
  - matches:
    - method:
        service: myapp.UserService
        method: GetUser
    backendRefs:
    - name: user-service
      port: 50051
```

기본 Exact 매칭은 메서드 이름의 대소문자를 구분합니다. 백엔드는 예상한 gRPC 전송 방식과 적절한 TLS 구성을 제공해야 하며 포트 번호만으로 증명되지는 않습니다. 서비스만 지정한 method 매치는 해당 서비스의 메서드를 포함합니다.

</details>

## 12. Ingress와의 비교 중 틀린 것은 무엇인가요?

- A. Gateway API는 리스너와 Route 소유권을 더 명시적으로 분리
- B. Gateway API는 TCP/UDP/gRPC 전용 라우팅 유형을 정의
- C. 표준 라우팅 필드에도 구현체 지원 요구사항이 있음
- D. Gateway API는 Ingress보다 리소스 유형이 적음

<details>
<summary>정답 보기</summary>

D. Gateway API는 여러 리소스 유형을 도입합니다. Ingress에도 IngressClass와 RBAC/admission 제어가 있으므로 인가·소유권 제어가 전혀 없다고 설명하면 부정확합니다. Gateway API는 여러 책임과 네임스페이스 간 상호 허용을 더 명시적으로 표현합니다. 모든 필드가 어디서나 동일하게 동작한다고 가정하지 말고 컨트롤러/버전 지원을 확인하세요.

</details>

[본문으로 돌아가기](../../networking/04-gateway-api.md)
