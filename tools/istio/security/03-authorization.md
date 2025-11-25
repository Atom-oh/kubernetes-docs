# 권한 부여

AuthorizationPolicy를 사용하여 서비스 접근 권한을 세밀하게 제어할 수 있습니다.

## 목차

1. [권한 부여 개요](#권한-부여-개요)
2. [기본 정책](#기본-정책)
3. [고급 정책](#고급-정책)
4. [실전 예제](#실전-예제)
5. [모범 사례](#모범-사례)

## 권한 부여 개요

```mermaid
flowchart TB
    Request[요청]
    
    subgraph AuthZ["Authorization Policy"]
        Check1{Service Account<br/>확인}
        Check2{Namespace<br/>확인}
        Check3{HTTP Method<br/>확인}
    end
    
    Allow[허용]
    Deny[거부]
    
    Request --> Check1
    Check1 -->|일치| Check2
    Check1 -.->|불일치| Deny
    Check2 -->|일치| Check3
    Check2 -.->|불일치| Deny
    Check3 -->|일치| Allow
    Check3 -.->|불일치| Deny
    
    %% 스타일 정의
    classDef request fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef check fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef result fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef deny fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    
    %% 클래스 적용
    class Request request;
    class Check1,Check2,Check3 check;
    class Allow result;
    class Deny deny;
```

## 기본 정책

### 기본 거부 (Deny All)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: DENY
  rules:
  - {}  # 모든 요청 거부
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

## 참고 자료

- [Istio Authorization Policy](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Authorization Examples](https://istio.io/latest/docs/tasks/security/authorization/)
