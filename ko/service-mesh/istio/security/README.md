# Security

> **검토 버전**: Istio 1.31.0
> **마지막 업데이트**: 2026년 9월 11일

Istio는 서비스 메시 내에서 강력한 보안 기능을 제공합니다. Zero Trust 보안 모델을 기반으로 서비스 간 통신을 자동으로 암호화하고, 세밀한 접근 제어를 제공합니다.

## 목차

1. [보안 아키텍처 개요](#보안-아키텍처-개요)
2. [핵심 보안 기능](#핵심-보안-기능)
3. [보안 구성요소](#보안-구성요소)
4. [상세 문서](#다음-단계)
5. [보안 베스트 프랙티스](#보안-베스트-프랙티스)
6. [보안 모니터링](#3-security-monitoring)

## 보안 아키텍처 개요

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Istio Security Architecture" width="900">
</p>

Istio는 **Zero Trust 보안 모델**을 구현하여 메시에 등록된 트래픽을 보호합니다. 제외된 트래픽, 평문 클라이언트, 미지원 프로토콜에는 명시적 제어가 필요합니다. 아래는 주요 보안 역할입니다:

### 보안 아키텍처 계층

![Control Plane(istiod)의 Certificate Authority와 Configuration API가 두 Pod의 Envoy 사이드카에 인증서와 정책을 배포하고, 사이드카 간 구간만 mTLS로 암호화되며, Identity부터 Authorization까지 5단계 보안 계층이 순서대로 적용되는 Istio 보안 아키텍처를 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-security-readme-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-security-readme-0.html)

### 보안 구성요소

1. **Control Plane (istiod)**
   - Certificate Authority (CA): X.509 인증서 발급 및 관리
   - Configuration API: 보안 정책 배포 및 관리
   - Service Discovery: 워크로드 Identity 관리

2. **Data Plane (Envoy sidecars or ambient ztunnel/waypoints)**
   - mTLS 종료점: 서비스 간 암호화 통신
   - Policy Enforcement: 인증/인가 정책 적용
   - Security Telemetry: 보안 메트릭 수집

3. **Identity Management**
   - SPIFFE 표준 기반 강력한 신원 관리
   - Kubernetes ServiceAccount와 통합
   - 기본 인증서 수명 24시간; 만료 전에 갱신

4. **Policy Engine**
   - 선언적 보안 정책 (CRD 기반)
   - 세밀한 접근 제어 (RBAC)
   - Audit Logging 지원

## 핵심 보안 기능

Istio는 다음 핵심 보안 기능을 제공합니다:

### 1. 통신 보안 (mTLS)

필요한 클라이언트가 모두 mTLS를 사용하는지 확인한 뒤 등록된 워크로드를 PERMISSIVE에서 STRICT로 전환합니다.

자동 mTLS는 등록된 메시 피어 간 통신을 암호화하며 PERMISSIVE는 평문도 허용합니다. 선택한 인바운드 워크로드에서 mTLS를 강제하려면 STRICT를 사용하세요.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # 프로덕션: STRICT, 마이그레이션: PERMISSIVE
```

**모드 설명**:
- **STRICT**: mTLS만 허용 (프로덕션 권장)
- **PERMISSIVE**: mTLS와 평문 둘 다 허용 (마이그레이션용)
- **DISABLE**: Sidecar의 Istio 전송 mTLS 해제; Ambient에서는 미지원

아래는 Sidecar selector 정책 예제입니다. Ambient ztunnel은 L4 보안을 집행하며 JWT 등 L7 정책에는 적절한 waypoint와 targetRefs 연결이 필요합니다.

### 2. 인증 (Authentication)

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authn.svg" alt="Authentication Architecture" width="700">
</p>

Istio는 두 계층의 인증을 제공합니다:

- **Peer Authentication**: 서비스 간 인증 (mTLS + SPIFFE ID)
- **Request Authentication**: 지원 발급자의 JWT 검증; 로그인/OAuth 흐름은 외부에서 처리

**예시**:
```yaml
# Request Authentication (JWT)
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
```

### 3. 권한 부여 (Authorization)

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Authorization Architecture" width="600">
</p>

세밀한 접근 제어 정책을 적용합니다. AuthorizationPolicy는 다음을 기반으로 제어합니다:
- Service Account / Namespace
- HTTP Method / Path
- IP 주소
- JWT 클레임

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-read
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/myapp"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/api/*"]
```

## 보안 베스트 프랙티스

### 1. Defense in Depth (다층 방어)

전송 계층 ID, 검증한 요청 자격 증명, 명시적 인가 규칙을 함께 적용합니다.

여러 계층에서 보안을 적용하여 심층 방어를 구현합니다:

**Network Layer**:
```yaml
# 1. mTLS STRICT 모드 활성화
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

**Application Layer**:
```yaml
# 2. JWT 인증 활성화
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: require-jwt
  namespace: default
spec:
  jwtRules:
  - issuer: "https://your-auth-provider.com"
    jwksUri: "https://your-auth-provider.com/.well-known/jwks.json"
    audiences: ["<your-api-audience>"]
```

**Access Control Layer**:
```yaml
# 3. 기본 거부 정책
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []
---
# 4. 필요한 접근만 허용
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-specific
  namespace: default
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/frontend/sa/webapp"]
        requestPrincipals: ["*"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

RequestAuthentication만으로는 토큰 없는 요청을 거부하지 않습니다. 위 ALLOW는 검증된 피어와 요청 principal을 모두 요구하며 빈 ALLOW 정책이 기본 거부를 만듭니다. DENY-all은 예외 ALLOW보다 우선해 모두 차단합니다. 네임스페이스 전체 정책은 일치하는 모든 워크로드에 영향을 주므로 selector/targetRefs 범위를 정하세요. AUDIT에는 감사 구현이 필요하고 액세스 로그도 별도 활성화해야 합니다.

### 2. Principle of Least Privilege (최소 권한 원칙)

- 각 서비스에 필요한 최소한의 권한만 부여
- ServiceAccount를 세밀하게 분리
- Namespace 격리 활용

<span id="3-security-monitoring"></span>

### 3. Security Monitoring

- Istio Access Log 활성화
- Prometheus로 보안 메트릭 수집
- Kiali로 mTLS 상태 모니터링

## 다음 단계

1. **[mTLS](01-mtls.md)**: 서비스 간 암호화 및 Identity 관리
2. **[인증](02-authentication.md)**: JWT 및 OAuth/OIDC 통합
3. **[권한 부여](03-authorization.md)**: 세밀한 접근 제어 정책

## 참고 자료

### 공식 문서
- [Istio Security Concepts](https://istio.io/latest/docs/concepts/security/)
- [Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)
- [Security Reference](https://istio.io/latest/docs/reference/config/security/)

### 관련 표준
- [SPIFFE Specification](https://github.com/spiffe/spiffe)
- [OAuth 2.0 / OIDC](https://oauth.net/2/)
- [JWT (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [Istio Security 퀴즈](../../../quizzes/service-mesh/istio/security.md)를 풀어보세요.
