# 권한 부여

AuthorizationPolicy를 사용하여 서비스 접근 권한을 세밀하게 제어할 수 있습니다.

## 목차

1. [권한 부여 개요](#권한-부여-개요)
2. [기본 정책](#기본-정책)
3. [고급 정책](#고급-정책)
4. [실전 예제](#실전-예제)
5. [모범 사례](#모범-사례)

## 권한 부여 개요

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Istio Authorization" width="700">
</p>

Istio AuthorizationPolicy는 서비스에 대한 세밀한 접근 제어를 제공합니다. 위 다이어그램은 Authorization Policy가 어떻게 작동하는지 보여줍니다:

1. **요청 수신**: Envoy가 인바운드 요청을 받음
2. **Policy 평가**: 일치하는 CUSTOM, DENY, ALLOW 순서; YAML 생성 순서가 아님
3. **접근 결정**: ALLOW, DENY, CUSTOM 액션 적용
4. **Audit Logging**: Access/audit 로깅 구성 필요; AUDIT만으로는 요청 표시만 수행

**지원되는 조건**:
- **Source**: 요청 출처 (ServiceAccount, Namespace, IP)
- **Operation**: HTTP 메서드, 경로, 포트
- **Conditions**: 커스텀 조건 (헤더, JWT 클레임 등)

![요청이 AuthorizationPolicy 안에서 Service Account, Namespace, HTTP Method 순으로 세 가지 조건을 검사하며, 모두 일치하면 허용되고 어느 단계든 불일치하면 즉시 거부로 이동하는 흐름을 보여준다.](../../../.gitbook/assets/ko-service-mesh-istio-security-03-authorization-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-service-mesh-istio-security-03-authorization-0.html)

## 기본 정책

그림은 하나의 AND 조건 규칙을 나타냅니다. 한 규칙의 from/to/when은 함께 적용되고, 별도 규칙과 ALLOW 정책은 대안으로 합쳐집니다. 워크로드에 ALLOW 정책이 없으면 CUSTOM/DENY가 거부하지 않는 요청은 허용되며 ALLOW가 적용되면 하나 이상에 일치해야 합니다. 아래 예제는 대안입니다. allow-all을 함께 적용하면 GET 전용 정책도 넓어집니다.

### 기본 거부 (Deny All)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []  # 구체적 ALLOW 예외를 추가할 수 있는 기본 거부
```

### 기본 허용 (Allow All)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-all
  namespace: default
spec:
  action: ALLOW
  rules:
  - {}  # 모든 요청 허용
```

### HTTP Method 기반

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin-get-only
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - to:
    - operation:
        methods: ["GET"]  # GET만 허용
```

## 고급 정책

### Service Account 기반

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ratings-sa-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]  # reviews SA만 허용
```

### Namespace 기반

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: db-namespace-policy
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgresql
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production", "staging"]  # 특정 네임스페이스만
```

### Path 기반

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: path-based-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
  - to:
    - operation:
        paths: ["/api/public/*"]  # 공개 API만 허용
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/admin"]
    to:
    - operation:
        paths: ["/api/admin/*"]  # admin SA는 admin API 접근 가능
```

### JWT Claims 기반

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: jwt-claims-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[role]
      values: ["admin", "superuser"]  # role claim이 admin 또는 superuser
```

## 실전 예제

기본 거부와 예외는 빈 ALLOW 정책과 의도한 구체적 ALLOW 규칙만 조합합니다. 명시적 DENY의 rules: [{}]는 어떤 ALLOW도 해제할 수 없는 전체 차단입니다. selector 없는 정책은 해당 네임스페이스에 적용되며 root namespace와 targetRefs 연결 규칙도 따로 확인하세요.

서비스 계정/네임스페이스 조건은 인증한 mTLS 피어 ID가 필요합니다. JWT role 예제는 일치하는 RequestAuthentication과 의도한 issuer/audience 검증이 필요합니다. 클라이언트 헤더는 두 ID를 대체하지 않습니다. 일반 TCP에는 HTTP 메서드/JWT 대신 ID·IP·포트를 사용하세요. DENY 규칙의 누락된 HTTP 속성은 TCP와 예상치 않게 일치할 수 있습니다.

## 모범 사례

- 대상 워크로드/리소스로 범위를 제한하고 적용되는 모든 ALLOW를 함께 검토합니다.
- Ambient L7 정책은 waypoint targetRefs를 사용하며 Sidecar selector로 연결되지 않습니다.
- 정책 없음·불일치·명시적 거부·허용 요청과 네임스페이스 경계를 각각 검사합니다.
- 로깅을 명시적으로 구성하고 `istioctl x authz check <pod> -n <namespace>`로 유효 정책을 확인합니다.

## 참고 자료

- [Istio Authorization Policy](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Authorization Examples](https://istio.io/latest/docs/tasks/security/authorization/)
