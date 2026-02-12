# Gateway와 VirtualService

Gateway와 VirtualService는 Istio에서 트래픽을 관리하는 핵심 리소스입니다.

## 목차

1. [Gateway 개요](#gateway-개요)
2. [VirtualService 개요](#virtualservice-개요)
3. [기본 설정](#기본-설정)
4. [실전 예제](#실전-예제)
5. [고급 패턴](#고급-패턴)
6. [문제 해결](#문제-해결)

## Gateway 개요

Gateway는 메시로 들어오는 외부 트래픽의 진입점을 정의합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway  # Ingress Gateway 파드 선택
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - "myapp.example.com"
```

## VirtualService 개요

VirtualService는 Gateway로 들어온 트래픽을 어떻게 라우팅할지 정의합니다.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: default
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/api"
    route:
    - destination:
        host: api-service
        port:
          number: 8080
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

## 기본 설정

### HTTP 트래픽

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"  # 모든 호스트 허용
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: app-routes
spec:
  hosts:
  - "*"
  gateways:
  - http-gateway
  http:
  - route:
    - destination:
        host: myapp
        port:
          number: 8080
```

### HTTPS 트래픽

```yaml
# TLS 인증서 Secret 생성
kubectl create secret tls myapp-tls \
  --cert=myapp.crt \
  --key=myapp.key \
  -n istio-system
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: https-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

## 실전 예제

### Path 기반 라우팅

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  # API 트래픽
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
        port:
          number: 8080
  # Admin 트래픽
  - match:
    - uri:
        prefix: "/admin"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000
  # 기본 트래픽
  - route:
    - destination:
        host: frontend
        port:
          number: 3000
```

### Header 기반 라우팅

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-routing
spec:
  hosts:
  - reviews
  http:
  # Mobile 트래픽
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # 개발자 트래픽
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
  # 기본 트래픽
  - route:
    - destination:
        host: reviews
        subset: v1
```

### 다중 도메인 설정

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: multi-domain-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-api
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: api-tls
    hosts:
    - "api.example.com"
  - port:
      number: 443
      name: https-admin
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: admin-tls
    hosts:
    - "admin.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-routes
spec:
  hosts:
  - "api.example.com"
  gateways:
  - multi-domain-gateway
  http:
  - route:
    - destination:
        host: api-service
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: admin-routes
spec:
  hosts:
  - "admin.example.com"
  gateways:
  - multi-domain-gateway
  http:
  - route:
    - destination:
        host: admin-service
```

## 고급 패턴

### HTTP to HTTPS 리다이렉트

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: secure-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTP (리다이렉트용)
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true  # HTTPS로 리다이렉트
  # HTTPS
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

### URL Rewrite

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: url-rewrite
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-api"
    rewrite:
      uri: "/api/v2"  # URL 재작성
    route:
    - destination:
        host: api-service
```

### Header 추가/수정

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-manipulation
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    headers:
      request:
        add:
          x-custom-header: "custom-value"
          x-forwarded-proto: "https"
        set:
          x-api-version: "v2"
        remove:
          - x-internal-header
      response:
        add:
          x-response-time: "100ms"
```

### Redirect

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: redirect-example
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-page"
    redirect:
      uri: "/new-page"
      authority: "newapp.example.com"
```

## 문제 해결

### Gateway가 작동하지 않음

```bash
# 1. Gateway 상태 확인
kubectl get gateway -n istio-system

# 2. Ingress Gateway 파드 확인
kubectl get pods -n istio-system -l istio=ingressgateway

# 3. Gateway 구성 확인
kubectl describe gateway my-gateway -n istio-system

# 4. Envoy 구성 확인
istioctl proxy-config listeners -n istio-system istio-ingressgateway-xxx
```

### VirtualService 라우팅 실패

```bash
# 1. VirtualService 확인
kubectl get virtualservice

# 2. 구성 분석
istioctl analyze

# 3. 라우팅 규칙 확인
istioctl proxy-config routes -n istio-system istio-ingressgateway-xxx

# 4. 로그 확인
kubectl logs -n istio-system -l istio=ingressgateway --tail=100
```

### TLS 인증서 문제

```bash
# Secret 확인
kubectl get secret -n istio-system myapp-tls

# Secret 내용 확인
kubectl describe secret -n istio-system myapp-tls

# Gateway TLS 구성 확인
istioctl proxy-config secret -n istio-system istio-ingressgateway-xxx
```

## 모범 사례

1. **네임스페이스 분리**: Gateway는 `istio-system`에, VirtualService는 애플리케이션 네임스페이스에
2. **TLS 필수 사용**: 프로덕션 환경에서는 항상 HTTPS 사용
3. **명확한 호스트 지정**: 와일드카드(`*`) 대신 명시적 도메인 사용
4. **Match 조건 순서**: 구체적인 조건을 먼저, 일반적인 조건은 나중에
5. **리소스 네이밍**: 일관된 네이밍 규칙 사용

## 참고 자료

- [Istio Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Ingress Traffic](https://istio.io/latest/docs/tasks/traffic-management/ingress/)
