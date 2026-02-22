# Linkerd 아키텍처

> **지원 버전**: Linkerd 2.16+
> **마지막 업데이트**: 2026년 2월 21일

## 개요

Linkerd는 컨트롤 플레인과 데이터 플레인으로 구성된 서비스 메시 아키텍처를 따릅니다. 이 문서에서는 각 컴포넌트의 역할과 상호작용, 인증서 체계, 프록시 라이프사이클 등을 상세히 설명합니다.

## 전체 아키텍처

```mermaid
graph TB
    subgraph "Control Plane (linkerd namespace)"
        subgraph "Core Components"
            DEST[Destination Controller<br/>서비스 디스커버리<br/>정책 배포]
            ID[Identity Controller<br/>인증서 발급<br/>CA 관리]
            PI[Proxy Injector<br/>사이드카 주입<br/>Admission Webhook]
        end

        subgraph "Policy Engine"
            POL[Policy Controller<br/>Server/Authorization<br/>정책 검증]
        end
    end

    subgraph "Data Plane"
        subgraph "Application Pod A"
            APP_A[Application Container]
            PROXY_A[linkerd-proxy<br/>Rust 마이크로 프록시]
            INIT_A[linkerd-init<br/>iptables 설정]
        end

        subgraph "Application Pod B"
            APP_B[Application Container]
            PROXY_B[linkerd-proxy]
            INIT_B[linkerd-init]
        end
    end

    subgraph "Extensions"
        VIZ[Viz Extension<br/>메트릭/대시보드]
        JAEGER[Jaeger Extension<br/>분산 추적]
        MC[Multicluster Extension<br/>클러스터 연결]
    end

    %% Control Plane Interactions
    PI -->|Webhook| PROXY_A
    PI -->|Webhook| PROXY_B
    ID -->|인증서| PROXY_A
    ID -->|인증서| PROXY_B
    DEST -->|엔드포인트| PROXY_A
    DEST -->|엔드포인트| PROXY_B
    POL -->|정책| PROXY_A
    POL -->|정책| PROXY_B

    %% Data Plane Traffic
    APP_A --> PROXY_A
    PROXY_A -->|mTLS| PROXY_B
    PROXY_B --> APP_B

    %% Extension Interactions
    VIZ -->|메트릭 수집| PROXY_A
    VIZ -->|메트릭 수집| PROXY_B

    classDef control fill:#e1f5fe
    classDef data fill:#f3e5f5
    classDef ext fill:#e8f5e9

    class DEST,ID,PI,POL control
    class APP_A,APP_B,PROXY_A,PROXY_B,INIT_A,INIT_B data
    class VIZ,JAEGER,MC ext
```

## 컨트롤 플레인

컨트롤 플레인은 `linkerd` 네임스페이스에 배포되며, 데이터 플레인 프록시를 구성하고 관리하는 컴포넌트들로 구성됩니다.

### Destination Controller

Destination 컨트롤러는 서비스 디스커버리와 정책 배포를 담당하는 핵심 컴포넌트입니다.

```mermaid
graph LR
    subgraph "Destination Controller"
        API[Destination API<br/>gRPC 서버]
        DISC[Service Discovery<br/>엔드포인트 조회]
        PROF[ServiceProfile<br/>라우팅 정보]
        SPLIT[TrafficSplit<br/>트래픽 분할]
    end

    subgraph "Kubernetes"
        SVC[Services]
        EP[Endpoints]
        SP[ServiceProfiles]
        TS[TrafficSplits]
    end

    subgraph "Proxies"
        P1[Proxy 1]
        P2[Proxy 2]
    end

    SVC --> DISC
    EP --> DISC
    SP --> PROF
    TS --> SPLIT

    API --> P1
    API --> P2
```

**주요 기능:**

| 기능 | 설명 |
|------|------|
| 서비스 디스커버리 | Kubernetes 서비스와 엔드포인트 모니터링, 프록시에 실시간 업데이트 |
| 정책 배포 | ServiceProfile, TrafficSplit 등 정책을 프록시에 전달 |
| 로드 밸런싱 정보 | EWMA 기반 로드 밸런싱을 위한 엔드포인트 가중치 정보 |
| 서비스 프로파일 | 라우트별 재시도, 타임아웃, 메트릭 설정 |

**Destination API 동작:**

```go
// Destination API는 gRPC 스트리밍을 통해 프록시에 업데이트 전송
// 프록시가 대상 서비스에 대한 정보 요청
service Destination {
    // Get은 특정 대상에 대한 업데이트 스트림 반환
    rpc Get(GetDestination) returns (stream Update);

    // GetProfile은 서비스 프로파일 업데이트 스트림 반환
    rpc GetProfile(GetDestination) returns (stream DestinationProfile);
}
```

### Identity Controller

Identity 컨트롤러는 mTLS를 위한 인증서 발급과 관리를 담당합니다.

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant Identity as Identity Controller
    participant CA as Trust Anchor (CA)

    Note over Proxy: Pod 시작
    Proxy->>Identity: CSR (Certificate Signing Request)
    Identity->>Identity: 서비스 계정 검증
    Identity->>CA: 인증서 서명 요청
    CA-->>Identity: 서명된 인증서
    Identity-->>Proxy: 워크로드 인증서

    Note over Proxy: 인증서 만료 전
    Proxy->>Identity: 갱신 CSR
    Identity-->>Proxy: 새 인증서
```

**인증서 발급 프로세스:**

1. 프록시 시작 시 CSR(Certificate Signing Request) 생성
2. Identity 컨트롤러가 Pod의 ServiceAccount 검증
3. Trust Anchor(Root CA)로 인증서 서명
4. 워크로드 인증서를 프록시에 전달
5. 기본 24시간 유효, 자동 갱신

**Identity 설정:**

```yaml
# linkerd-config ConfigMap에서 Identity 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkerd-config
  namespace: linkerd
data:
  values: |
    identity:
      issuer:
        # 인증서 발급 수명 (기본 24시간)
        issuanceLifetime: 24h0m0s
        # 클럭 스큐 허용 범위
        clockSkewAllowance: 20s
        # 발급자 스키마 (kubernetes.io/tls)
        scheme: kubernetes.io/tls
```

### Proxy Injector

Proxy Injector는 Kubernetes Admission Webhook으로 동작하여 Pod에 사이드카를 자동 주입합니다.

```mermaid
sequenceDiagram
    participant User as kubectl
    participant API as API Server
    participant PI as Proxy Injector
    participant Pod as Pod

    User->>API: Pod 생성 요청
    API->>PI: Admission Review
    PI->>PI: 주입 조건 확인
    alt 주입 활성화
        PI->>PI: linkerd-proxy 컨테이너 추가
        PI->>PI: linkerd-init 컨테이너 추가
        PI->>PI: 볼륨/환경변수 설정
        PI-->>API: Mutated Pod Spec
    else 주입 비활성화
        PI-->>API: 원본 Pod Spec
    end
    API->>Pod: Pod 생성
```

**주입 조건:**

```yaml
# 네임스페이스 레벨 주입 활성화
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled

---
# Pod 레벨 주입 제어
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  annotations:
    # 주입 활성화
    linkerd.io/inject: enabled
    # 또는 비활성화
    # linkerd.io/inject: disabled
```

**주입되는 컴포넌트:**

| 컴포넌트 | 역할 |
|---------|------|
| `linkerd-init` | Init 컨테이너, iptables 규칙 설정 |
| `linkerd-proxy` | 사이드카 컨테이너, 트래픽 프록시 |
| 볼륨 | Identity 토큰, 설정 |
| 환경변수 | 프록시 설정, 대상 주소 |

### Policy Controller

Policy Controller는 Linkerd의 인가 정책을 관리합니다.

```yaml
# Server 리소스 - 인바운드 트래픽 정의
apiVersion: policy.linkerd.io/v1beta2
kind: Server
metadata:
  name: web-http
  namespace: my-app
spec:
  podSelector:
    matchLabels:
      app: web
  port: http
  proxyProtocol: HTTP/1

---
# ServerAuthorization - 접근 권한 정의
apiVersion: policy.linkerd.io/v1beta2
kind: ServerAuthorization
metadata:
  name: web-authz
  namespace: my-app
spec:
  server:
    name: web-http
  client:
    meshTLS:
      serviceAccounts:
        - name: api-gateway
          namespace: my-app
```

## 데이터 플레인

데이터 플레인은 애플리케이션 Pod에 주입된 `linkerd-proxy` 사이드카로 구성됩니다.

### linkerd2-proxy

Linkerd의 데이터 플레인 프록시는 Rust로 작성된 초경량 마이크로 프록시입니다.

```mermaid
graph TB
    subgraph "Pod"
        subgraph "linkerd-proxy"
            IN[Inbound Listener<br/>:4143]
            OUT[Outbound Listener<br/>:4140]
            ADMIN[Admin Server<br/>:4191]

            subgraph "Processing"
                TLS[TLS Termination/Origination]
                LB[Load Balancing<br/>EWMA]
                RETRY[Retries]
                TO[Timeouts]
                CB[Circuit Breaking]
                METRICS[Metrics Collection]
            end
        end

        APP[Application]
    end

    EXT_IN[External Inbound] --> IN
    IN --> TLS
    TLS --> APP

    APP --> OUT
    OUT --> LB
    LB --> TLS
    TLS --> EXT_OUT[External Outbound]

    ADMIN --> METRICS
```

**프록시 특성:**

| 특성 | 값 |
|------|-----|
| 언어 | Rust |
| 메모리 사용량 | ~10MB |
| CPU 오버헤드 | 최소 |
| 지연 시간 추가 | <1ms p99 |
| 프로토콜 | HTTP/1.1, HTTP/2, gRPC, TCP |
| TLS | TLS 1.3 (rustls) |

**Istio Envoy와 비교:**

| 특성 | linkerd2-proxy | Envoy (Istio) |
|------|---------------|---------------|
| 언어 | Rust | C++ |
| 메모리 | ~10MB | ~50-100MB |
| 바이너리 크기 | ~10MB | ~60MB |
| 지연 시간 | <1ms p99 | 2-5ms p99 |
| 설정 복잡도 | 낮음 (자동) | 높음 (xDS) |
| 확장성 | 제한적 | Wasm, Lua |
| 프로토콜 지원 | HTTP, gRPC, TCP | 매우 광범위 |

### 프록시 트래픽 흐름

```mermaid
sequenceDiagram
    participant Client as Client App
    participant CProxy as Client Proxy<br/>(Outbound)
    participant SProxy as Server Proxy<br/>(Inbound)
    participant Server as Server App

    Client->>CProxy: HTTP Request<br/>(localhost)
    Note over CProxy: iptables 리다이렉트
    CProxy->>CProxy: 대상 서비스 조회<br/>(Destination API)
    CProxy->>CProxy: 로드 밸런싱<br/>(EWMA)
    CProxy->>CProxy: mTLS 핸드셰이크
    CProxy->>SProxy: Encrypted Request
    SProxy->>SProxy: mTLS 검증
    SProxy->>SProxy: 정책 확인
    SProxy->>Server: HTTP Request
    Server-->>SProxy: HTTP Response
    SProxy-->>CProxy: Encrypted Response
    CProxy-->>Client: HTTP Response
```

### linkerd-init (Init Container)

`linkerd-init`은 iptables 규칙을 설정하여 트래픽을 프록시로 리다이렉트합니다.

```bash
# linkerd-init이 설정하는 iptables 규칙 예시
# Outbound 트래픽 리다이렉트 (포트 4140으로)
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-port 4140

# Inbound 트래픽 리다이렉트 (포트 4143으로)
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 4143

# 프록시 자체 트래픽은 제외
iptables -t nat -A OUTPUT -m owner --uid-owner 2102 -j RETURN
```

**주입된 Pod 구조:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
spec:
  initContainers:
  - name: linkerd-init
    image: cr.l5d.io/linkerd/proxy-init:v2.3.0
    args:
    - --incoming-proxy-port=4143
    - --outgoing-proxy-port=4140
    - --proxy-uid=2102
    securityContext:
      capabilities:
        add:
        - NET_ADMIN
        - NET_RAW

  containers:
  - name: my-app
    image: my-app:latest

  - name: linkerd-proxy
    image: cr.l5d.io/linkerd/proxy:stable-2.16.0
    ports:
    - containerPort: 4143  # Inbound
      name: linkerd-proxy
    - containerPort: 4191  # Admin/Metrics
      name: linkerd-admin
    env:
    - name: LINKERD2_PROXY_LOG
      value: warn,linkerd=info
    - name: LINKERD2_PROXY_DESTINATION_SVC_ADDR
      value: linkerd-dst.linkerd.svc.cluster.local:8086
    - name: LINKERD2_PROXY_IDENTITY_SVC_ADDR
      value: linkerd-identity.linkerd.svc.cluster.local:8080
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 1000m
        memory: 250Mi
    readinessProbe:
      httpGet:
        path: /ready
        port: 4191
    livenessProbe:
      httpGet:
        path: /live
        port: 4191
```

## 인증서 체계

Linkerd는 계층적 PKI(Public Key Infrastructure)를 사용하여 mTLS를 구현합니다.

### 인증서 계층 구조

```mermaid
graph TB
    subgraph "Certificate Hierarchy"
        TA[Trust Anchor<br/>Root CA<br/>유효기간: 10년]
        II[Identity Issuer<br/>Intermediate CA<br/>유효기간: 1년]
        WC1[Workload Cert 1<br/>유효기간: 24시간]
        WC2[Workload Cert 2<br/>유효기간: 24시간]
        WC3[Workload Cert 3<br/>유효기간: 24시간]
    end

    TA --> II
    II --> WC1
    II --> WC2
    II --> WC3

    style TA fill:#ff9800
    style II fill:#2196f3
    style WC1 fill:#4caf50
    style WC2 fill:#4caf50
    style WC3 fill:#4caf50
```

### Trust Anchor (Root CA)

Trust Anchor는 PKI의 루트로, 모든 인증서 체인의 신뢰 기반입니다.

```bash
# Trust Anchor 생성 (step CLI 사용)
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h  # 10년

# Trust Anchor 확인
openssl x509 -in ca.crt -text -noout

# 출력 예시:
# Certificate:
#     Data:
#         Version: 3 (0x2)
#         Serial Number: ...
#         Signature Algorithm: ecdsa-with-SHA256
#         Issuer: CN = root.linkerd.cluster.local
#         Validity
#             Not Before: Feb 21 00:00:00 2026 GMT
#             Not After : Feb 21 00:00:00 2036 GMT
#         Subject: CN = root.linkerd.cluster.local
#         ...
#         X509v3 extensions:
#             X509v3 Key Usage: critical
#                 Certificate Sign, CRL Sign
#             X509v3 Basic Constraints: critical
#                 CA:TRUE
```

**Trust Anchor 저장:**

```yaml
# Kubernetes Secret으로 저장
apiVersion: v1
kind: Secret
metadata:
  name: linkerd-identity-trust-roots
  namespace: linkerd
type: Opaque
data:
  ca-bundle.crt: <base64-encoded-ca.crt>
```

### Identity Issuer (Intermediate CA)

Identity Issuer는 워크로드 인증서를 발급하는 중간 CA입니다.

```bash
# Identity Issuer 인증서 생성
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca \
  --ca ca.crt \
  --ca-key ca.key \
  --no-password \
  --insecure \
  --not-after=8760h  # 1년

# Issuer 인증서 확인
openssl x509 -in issuer.crt -text -noout
```

**Identity Issuer Secret:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-issuer.crt>
  tls.key: <base64-encoded-issuer.key>
  ca.crt: <base64-encoded-ca.crt>
```

### 워크로드 인증서

각 프록시는 고유한 워크로드 인증서를 받습니다.

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant ID as Identity Controller
    participant SA as ServiceAccount

    Note over Proxy: Pod 시작
    Proxy->>SA: ServiceAccount 토큰 획득
    Proxy->>Proxy: CSR 생성 (SPIFFE ID 포함)
    Proxy->>ID: CSR + SA 토큰 전송
    ID->>ID: SA 토큰 검증
    ID->>ID: SPIFFE ID 검증
    ID->>ID: Issuer 키로 인증서 서명
    ID-->>Proxy: 서명된 인증서 (24시간 유효)

    Note over Proxy: 22시간 후 (만료 2시간 전)
    Proxy->>ID: 갱신 CSR
    ID-->>Proxy: 새 인증서
```

**SPIFFE ID 형식:**

```
spiffe://root.linkerd.cluster.local/ns/<namespace>/sa/<service-account>

# 예시:
spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service
```

### 인증서 로테이션

```yaml
# 인증서 수명 설정
identity:
  issuer:
    # 워크로드 인증서 수명 (기본 24시간)
    issuanceLifetime: 24h0m0s
    # 클럭 스큐 허용 (기본 20초)
    clockSkewAllowance: 20s

# 프록시는 인증서 만료 전에 자동 갱신
# 기본적으로 만료 70% 시점에 갱신 시작
```

**Trust Anchor 로테이션:**

```bash
# 새 Trust Anchor 생성
step certificate create root.linkerd.cluster.local ca-new.crt ca-new.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h

# 번들 생성 (기존 + 신규)
cat ca.crt ca-new.crt > ca-bundle.crt

# ConfigMap 업데이트
kubectl create configmap linkerd-identity-trust-roots \
  --from-file=ca-bundle.crt=ca-bundle.crt \
  -n linkerd \
  --dry-run=client -o yaml | kubectl apply -f -

# 이후 모든 프록시 재시작하여 새 번들 적용
kubectl rollout restart deploy -n my-app
```

## 사이드카 주입 상세

### 주입 워크플로우

```mermaid
graph TB
    subgraph "Injection Flow"
        REQ[Pod 생성 요청]
        WH[Webhook 호출]
        CHK[주입 조건 확인]
        INJ[사이드카 주입]
        POD[Pod 생성]
    end

    subgraph "Injection Conditions"
        NS[네임스페이스 어노테이션]
        POD_ANN[Pod 어노테이션]
        WL[워크로드 타입]
    end

    REQ --> WH
    WH --> CHK
    CHK --> NS
    CHK --> POD_ANN
    CHK --> WL
    NS --> INJ
    POD_ANN --> INJ
    WL --> INJ
    INJ --> POD
```

### 주입 어노테이션

```yaml
# 네임스페이스 레벨
metadata:
  annotations:
    linkerd.io/inject: enabled  # 모든 Pod에 주입

# Pod/Deployment 레벨
metadata:
  annotations:
    # 주입 활성화/비활성화
    linkerd.io/inject: enabled|disabled

    # 프록시 설정 오버라이드
    config.linkerd.io/proxy-cpu-request: "100m"
    config.linkerd.io/proxy-memory-request: "64Mi"
    config.linkerd.io/proxy-cpu-limit: "1"
    config.linkerd.io/proxy-memory-limit: "250Mi"

    # 프록시 로그 레벨
    config.linkerd.io/proxy-log-level: "warn,linkerd=info"

    # 포트 건너뛰기 (프록시 우회)
    config.linkerd.io/skip-inbound-ports: "25,587"
    config.linkerd.io/skip-outbound-ports: "25,587"

    # Opaque 포트 (프로토콜 감지 우회)
    config.linkerd.io/opaque-ports: "3306,5432"
```

### 프록시 Readiness/Liveness

```yaml
# 프록시 상태 확인 엔드포인트
livenessProbe:
  httpGet:
    path: /live
    port: 4191
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 4191
  initialDelaySeconds: 2
  periodSeconds: 10
```

## 컴포넌트 간 통신

```mermaid
graph TB
    subgraph "Control Plane"
        DEST[Destination<br/>:8086]
        ID[Identity<br/>:8080]
        PI[Proxy Injector<br/>:8443]
        POL[Policy<br/>:8090]
    end

    subgraph "Data Plane"
        P1[Proxy 1]
        P2[Proxy 2]
    end

    subgraph "Kubernetes"
        API[API Server]
        WH[Webhook Config]
    end

    P1 -->|gRPC| DEST
    P2 -->|gRPC| DEST
    P1 -->|gRPC| ID
    P2 -->|gRPC| ID
    P1 -->|gRPC| POL
    P2 -->|gRPC| POL

    API -->|Admission| PI
    WH --> PI

    DEST --> API
    ID --> API
    POL --> API
```

**포트 정리:**

| 컴포넌트 | 포트 | 프로토콜 | 용도 |
|---------|------|---------|------|
| Destination | 8086 | gRPC | 서비스 디스커버리 API |
| Identity | 8080 | gRPC | 인증서 발급 API |
| Policy | 8090 | gRPC | 정책 API |
| Proxy Injector | 8443 | HTTPS | Admission Webhook |
| Proxy (Inbound) | 4143 | HTTP/gRPC | 인바운드 트래픽 |
| Proxy (Outbound) | 4140 | HTTP/gRPC | 아웃바운드 트래픽 |
| Proxy (Admin) | 4191 | HTTP | 메트릭, 상태 확인 |

## Istio 아키텍처와 비교

### 컨트롤 플레인 비교

```mermaid
graph TB
    subgraph "Linkerd Control Plane"
        L_DEST[Destination]
        L_ID[Identity]
        L_PI[Proxy Injector]
    end

    subgraph "Istio Control Plane"
        ISTIOD[istiod<br/>Pilot + Citadel + Galley]
    end

    subgraph "Linkerd Data Plane"
        L_PROXY[linkerd-proxy<br/>Rust, ~10MB]
    end

    subgraph "Istio Data Plane"
        ENVOY[Envoy<br/>C++, ~50-100MB]
    end
```

| 특성 | Linkerd | Istio |
|------|---------|-------|
| 컨트롤 플레인 | 분산 (3개 컴포넌트) | 통합 (istiod) |
| 프록시 | linkerd2-proxy (Rust) | Envoy (C++) |
| 설정 프로토콜 | 커스텀 gRPC | xDS (복잡함) |
| CRD 수 | ~10개 | ~50개+ |
| 학습 곡선 | 완만 | 가파름 |
| 리소스 사용량 | 낮음 | 높음 |
| 확장성 | 제한적 | Wasm, Lua |

### 프록시 비교

```yaml
# Linkerd Proxy 리소스 (일반적)
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 1000m
    memory: 250Mi

# Envoy Proxy 리소스 (일반적)
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 2000m
    memory: 1Gi
```

## 다음 단계

- [트래픽 관리](./03-traffic-management.md): ServiceProfile과 트래픽 분할
- [보안](./04-security.md): mTLS와 인가 정책
- [관찰성](./05-observability.md): 메트릭과 대시보드

## 참고 자료

- [Linkerd Architecture](https://linkerd.io/2/reference/architecture/)
- [linkerd2-proxy GitHub](https://github.com/linkerd/linkerd2-proxy)
- [Linkerd Identity](https://linkerd.io/2/features/automatic-mtls/)
- [Proxy Injection](https://linkerd.io/2/features/proxy-injection/)
