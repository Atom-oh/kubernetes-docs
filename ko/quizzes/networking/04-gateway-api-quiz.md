# Gateway API 퀴즈

이 퀴즈는 Kubernetes Gateway API의 리소스 모델, 구현체, 그리고 Ingress에서의 마이그레이션에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Gateway API가 기존 Ingress API를 개선한 주요 방식이 아닌 것은?

A. 역할 기반 리소스 분리 (인프라 제공자, 클러스터 운영자, 애플리케이션 개발자)
B. TCP, UDP, gRPC 등 다양한 프로토콜 네이티브 지원
C. annotation 대신 표준화된 필드로 기능 구현
D. 단일 리소스로 모든 네트워크 기능 통합

<details>
<summary>정답 및 설명</summary>

**정답: D. 단일 리소스로 모든 네트워크 기능 통합**

**설명:**
Gateway API의 개선 사항:
- **역할 분리**: GatewayClass(인프라), Gateway(운영자), Routes(개발자)로 책임 분리
- **다양한 프로토콜**: HTTPRoute, GRPCRoute, TCPRoute, TLSRoute, UDPRoute
- **표준화**: annotation 없이 명시적 필드로 기능 정의
- **확장성**: CRD 기반으로 새로운 기능 추가 용이

Gateway API는 여러 리소스로 분리되어 있어, "단일 리소스 통합"은 올바르지 않습니다.

</details>

### 2. Gateway API의 역할 분리에서 GatewayClass를 관리하는 역할은?

A. 애플리케이션 개발자
B. 클러스터 운영자
C. 인프라 제공자
D. 보안 관리자

<details>
<summary>정답 및 설명</summary>

**정답: C. 인프라 제공자**

**설명:**
Gateway API 역할 분리:

| 역할 | 담당 리소스 | 책임 |
|------|------------|------|
| **인프라 제공자** | GatewayClass | 기본 인프라 구성 정의, 컨트롤러 지정 |
| **클러스터 운영자** | Gateway, ReferenceGrant | 로드밸런서 프로비저닝, 네임스페이스 권한 관리 |
| **애플리케이션 개발자** | HTTPRoute, GRPCRoute 등 | 애플리케이션 라우팅 규칙 정의 |

GatewayClass는 클라우드 프로바이더나 네트워크 팀이 정의합니다.

</details>

### 3. Gateway에서 TLS termination과 passthrough의 차이점으로 올바른 것은?

A. Terminate는 TLS를 백엔드로 전달하고, Passthrough는 Gateway에서 종료
B. Terminate는 Gateway에서 TLS 종료, Passthrough는 TLS를 백엔드로 전달
C. 두 모드 모두 동일하게 동작
D. Terminate는 HTTP만 지원, Passthrough는 HTTPS만 지원

<details>
<summary>정답 및 설명</summary>

**정답: B. Terminate는 Gateway에서 TLS 종료, Passthrough는 TLS를 백엔드로 전달**

**설명:**
TLS 모드:

| 모드 | 설명 | 사용 사례 |
|------|------|----------|
| **Terminate** | Gateway에서 TLS 종료, 백엔드는 평문 | 일반적인 HTTPS, 인증서 중앙 관리 |
| **Passthrough** | TLS를 백엔드로 그대로 전달 | End-to-end 암호화, 백엔드에서 인증서 관리 |

```yaml
listeners:
  - name: https
    protocol: HTTPS
    tls:
      mode: Terminate  # 또는 Passthrough
```

</details>

### 4. HTTPRoute에서 트래픽 분할(가중치)을 구현하는 방법으로 올바른 것은?

A. `trafficSplit` 필드 사용
B. 여러 `backendRefs`에 `weight` 필드 지정
C. `canary` annotation 사용
D. 별도의 TrafficSplit CRD 생성

<details>
<summary>정답 및 설명</summary>

**정답: B. 여러 `backendRefs`에 `weight` 필드 지정**

**설명:**
HTTPRoute에서 트래픽 분할:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
spec:
  rules:
    - backendRefs:
        - name: app-stable
          port: 80
          weight: 90  # 90%
        - name: app-canary
          port: 80
          weight: 10  # 10%
```

용도:
- 카나리 배포
- A/B 테스팅
- 블루-그린 배포

weight의 합이 100일 필요는 없으며, 비율로 계산됩니다.

</details>

### 5. ReferenceGrant의 주요 목적은?

A. Gateway 리소스 권한 관리
B. 크로스 네임스페이스 참조 허용
C. API 버전 호환성 관리
D. TLS 인증서 권한 부여

<details>
<summary>정답 및 설명</summary>

**정답: B. 크로스 네임스페이스 참조 허용**

**설명:**
ReferenceGrant 사용:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes
  namespace: backend-services
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend
  to:
    - group: ""
      kind: Service
```

용도:
- 다른 네임스페이스의 Service 참조 허용
- Gateway가 다른 네임스페이스의 Secret(TLS 인증서) 참조
- 보안을 위한 명시적 권한 부여

기본적으로 크로스 네임스페이스 참조는 차단됩니다.

</details>

### 6. Gateway API의 Standard 채널에 포함된 리소스가 아닌 것은?

A. GatewayClass
B. Gateway
C. HTTPRoute
D. TCPRoute

<details>
<summary>정답 및 설명</summary>

**정답: D. TCPRoute**

**설명:**
Gateway API 채널 분류:

**Standard 채널 (GA)**:
- GatewayClass
- Gateway
- HTTPRoute
- ReferenceGrant

**Experimental 채널 (Beta/Alpha)**:
- GRPCRoute
- TCPRoute
- TLSRoute
- UDPRoute

Standard 채널의 리소스는 `gateway.networking.k8s.io/v1` API 버전을 사용하고, Experimental은 `v1alpha2` 또는 `v1beta1`을 사용합니다.

</details>

### 7. HTTPRoute의 필터 유형 중 요청을 다른 URL로 변경하는 것은?

A. RequestHeaderModifier
B. ResponseHeaderModifier
C. URLRewrite
D. RequestMirror

<details>
<summary>정답 및 설명</summary>

**정답: C. URLRewrite**

**설명:**
HTTPRoute 필터 유형:

| 필터 | 설명 |
|------|------|
| RequestHeaderModifier | 요청 헤더 추가/수정/삭제 |
| ResponseHeaderModifier | 응답 헤더 추가/수정/삭제 |
| **URLRewrite** | URL 경로 또는 호스트 변경 |
| RequestRedirect | 다른 URL로 리다이렉트 (3xx 응답) |
| RequestMirror | 트래픽 미러링 (섀도우 서비스로 복사) |

```yaml
filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /new-api
      hostname: "new-api.example.com"
```

</details>

### 8. Gateway API를 지원하는 구현체가 아닌 것은?

A. Istio
B. Cilium
C. kube-proxy
D. Envoy Gateway

<details>
<summary>정답 및 설명</summary>

**정답: C. kube-proxy**

**설명:**
Gateway API 구현체:

| 구현체 | 컨트롤러 |
|--------|---------|
| **Istio** | istio.io/gateway-controller |
| **Cilium** | io.cilium/gateway-controller |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller |
| **Contour** | projectcontour.io/gateway-controller |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller |

kube-proxy는 Service의 ClusterIP/NodePort 라우팅을 담당하며, Gateway API와 무관합니다.

</details>

### 9. Ingress에서 Gateway API로 마이그레이션 시 Ingress의 annotation에 해당하는 Gateway API 기능은?

A. Gateway의 metadata
B. HTTPRoute의 matches 및 filters
C. GatewayClass의 parameters
D. ReferenceGrant의 spec

<details>
<summary>정답 및 설명</summary>

**정답: B. HTTPRoute의 matches 및 filters**

**설명:**
Ingress annotation → Gateway API 매핑:

| Ingress annotation | Gateway API |
|-------------------|-------------|
| `nginx.ingress.kubernetes.io/rewrite-target` | HTTPRoute filter: URLRewrite |
| `nginx.ingress.kubernetes.io/ssl-redirect` | HTTPRoute filter: RequestRedirect |
| `nginx.ingress.kubernetes.io/canary-weight` | HTTPRoute backendRefs weight |
| 경로 기반 라우팅 | HTTPRoute matches path |
| 헤더 기반 라우팅 | HTTPRoute matches headers |

Gateway API는 annotation 대신 명시적 필드를 사용하여 이식성을 높입니다.

</details>

### 10. Gateway에서 특정 네임스페이스의 Route만 허용하는 설정은?

A. `allowedRoutes.namespaces.from: All`
B. `allowedRoutes.namespaces.from: Same`
C. `allowedRoutes.namespaces.from: Selector`
D. B와 C 모두 가능

<details>
<summary>정답 및 설명</summary>

**정답: D. B와 C 모두 가능**

**설명:**
Gateway의 allowedRoutes 설정:

```yaml
listeners:
  - name: https
    allowedRoutes:
      namespaces:
        from: All  # 모든 네임스페이스
        # 또는
        from: Same  # Gateway와 같은 네임스페이스만
        # 또는
        from: Selector  # 레이블 셀렉터로 선택
        selector:
          matchLabels:
            gateway-access: "true"
```

- **All**: 모든 네임스페이스의 Route 허용
- **Same**: Gateway와 동일한 네임스페이스만 허용
- **Selector**: 특정 레이블을 가진 네임스페이스만 허용

</details>

### 11. GRPCRoute에서 특정 서비스의 특정 메서드로 라우팅하는 matches 설정은?

A. `path.service` 및 `path.method`
B. `method.service` 및 `method.method`
C. `grpc.service` 및 `grpc.method`
D. `rpc.service` 및 `rpc.method`

<details>
<summary>정답 및 설명</summary>

**정답: B. `method.service` 및 `method.method`**

**설명:**
GRPCRoute 매칭:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
spec:
  rules:
    - matches:
        - method:
            service: "myapp.UserService"
            method: "GetUser"
      backendRefs:
        - name: user-service
          port: 50051
```

gRPC 라우팅 옵션:
- 서비스만 지정: 해당 서비스의 모든 메서드
- 서비스 + 메서드: 특정 메서드만
- 헤더 기반 라우팅도 지원

</details>

### 12. Gateway API와 Ingress API의 비교로 올바르지 않은 것은?

A. Gateway API는 역할 기반 분리를 지원하고, Ingress는 지원하지 않음
B. Gateway API는 TCP/UDP를 네이티브 지원하고, Ingress는 지원하지 않음
C. Gateway API는 트래픽 분할을 네이티브 지원하고, Ingress는 annotation 필요
D. Gateway API는 Ingress보다 더 적은 리소스 유형을 사용함

<details>
<summary>정답 및 설명</summary>

**정답: D. Gateway API는 Ingress보다 더 적은 리소스 유형을 사용함**

**설명:**
Gateway API vs Ingress:

| 기능 | Ingress | Gateway API |
|------|---------|-------------|
| 리소스 수 | 1개 (Ingress) | 여러 개 (GatewayClass, Gateway, Routes 등) |
| 역할 분리 | 없음 | 3계층 분리 |
| TCP/UDP | 미지원 | 네이티브 지원 |
| 트래픽 분할 | annotation | 네이티브 (weight) |
| 확장성 | 제한적 | CRD 기반 |

Gateway API는 더 많은 리소스 유형을 사용하지만, 이를 통해 역할 분리와 유연성을 제공합니다.

</details>

---

## 추가 학습 자료

- [Gateway API 공식 문서](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [구현체별 가이드](https://gateway-api.sigs.k8s.io/implementations/)
