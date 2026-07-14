# Linkerd アーキテクチャ

> **対応バージョン**: Linkerd 2.16+
> **最終更新**: February 22, 2026

## 概要

Linkerd は、control plane（制御プレーン）と data plane（データプレーン）で構成される service mesh アーキテクチャに従います。このドキュメントでは、各コンポーネントの役割、それらの相互作用、証明書階層、および proxy のライフサイクルについて詳しく説明します。

## 全体アーキテクチャ

```mermaid
graph TB
    subgraph "Control Plane (linkerd namespace)"
        subgraph "Core Components"
            DEST[Destination Controller<br/>Service Discovery<br/>Policy Distribution]
            ID[Identity Controller<br/>Certificate Issuance<br/>CA Management]
            PI[Proxy Injector<br/>Sidecar Injection<br/>Admission Webhook]
        end

        subgraph "Policy Engine"
            POL[Policy Controller<br/>Server/Authorization<br/>Policy Validation]
        end
    end

    subgraph "Data Plane"
        subgraph "Application Pod A"
            APP_A[Application Container]
            PROXY_A[linkerd-proxy<br/>Rust Micro Proxy]
            INIT_A[linkerd-init<br/>iptables Setup]
        end

        subgraph "Application Pod B"
            APP_B[Application Container]
            PROXY_B[linkerd-proxy]
            INIT_B[linkerd-init]
        end
    end

    subgraph "Extensions"
        VIZ[Viz Extension<br/>Metrics/Dashboard]
        JAEGER[Jaeger Extension<br/>Distributed Tracing]
        MC[Multicluster Extension<br/>Cluster Linking]
    end

    %% Control Plane Interactions
    PI -->|Webhook| PROXY_A
    PI -->|Webhook| PROXY_B
    ID -->|Certificate| PROXY_A
    ID -->|Certificate| PROXY_B
    DEST -->|Endpoints| PROXY_A
    DEST -->|Endpoints| PROXY_B
    POL -->|Policy| PROXY_A
    POL -->|Policy| PROXY_B

    %% Data Plane Traffic
    APP_A --> PROXY_A
    PROXY_A -->|mTLS| PROXY_B
    PROXY_B --> APP_B

    %% Extension Interactions
    VIZ -->|Metrics Collection| PROXY_A
    VIZ -->|Metrics Collection| PROXY_B

    classDef control fill:#e1f5fe
    classDef data fill:#f3e5f5
    classDef ext fill:#e8f5e9

    class DEST,ID,PI,POL control
    class APP_A,APP_B,PROXY_A,PROXY_B,INIT_A,INIT_B data
    class VIZ,JAEGER,MC ext
```

## Control Plane

control plane は `linkerd` namespace にデプロイされ、data plane proxy を設定および管理するコンポーネントで構成されます。

### Destination Controller

Destination controller は、service discovery と policy 配布を担う中核コンポーネントです。

```mermaid
graph LR
    subgraph "Destination Controller"
        API[Destination API<br/>gRPC Server]
        DISC[Service Discovery<br/>Endpoint Lookup]
        PROF[ServiceProfile<br/>Routing Info]
        SPLIT[TrafficSplit<br/>Traffic Distribution]
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

**主な機能:**

| 機能 | 説明 |
|----------|-------------|
| Service Discovery | Kubernetes Service と Endpoint を監視し、リアルタイムの更新を proxy に提供します |
| Policy Distribution | ServiceProfile や TrafficSplit などの policy を proxy に配信します |
| Load Balancing Info | EWMA ベースの load balancing 用の Endpoint 重み情報 |
| Service Profiles | ルートごとの retry、timeout、および metrics 設定 |

**Destination API の動作:**

```go
// Destination API sends updates to proxies via gRPC streaming
// Proxy requests information about target service
service Destination {
    // Get returns update stream for a specific destination
    rpc Get(GetDestination) returns (stream Update);

    // GetProfile returns service profile update stream
    rpc GetProfile(GetDestination) returns (stream DestinationProfile);
}
```

### Identity Controller

Identity controller は mTLS の証明書発行と管理を処理します。

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant Identity as Identity Controller
    participant CA as Trust Anchor (CA)

    Note over Proxy: Pod starts
    Proxy->>Identity: CSR (Certificate Signing Request)
    Identity->>Identity: Validate ServiceAccount
    Identity->>CA: Certificate signing request
    CA-->>Identity: Signed certificate
    Identity-->>Proxy: Workload certificate

    Note over Proxy: Before certificate expiration
    Proxy->>Identity: Renewal CSR
    Identity-->>Proxy: New certificate
```

**証明書発行プロセス:**

1. Proxy は起動時に CSR（Certificate Signing Request）を生成します
2. Identity controller は Pod の ServiceAccount を検証します
3. Trust Anchor（Root CA）で証明書に署名します
4. workload 証明書を proxy に配信します
5. デフォルトの有効期間は 24 時間で、自動的に更新されます

**Identity 設定:**

```yaml
# Identity settings in linkerd-config ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkerd-config
  namespace: linkerd
data:
  values: |
    identity:
      issuer:
        # Certificate issuance lifetime (default 24 hours)
        issuanceLifetime: 24h0m0s
        # Clock skew allowance
        clockSkewAllowance: 20s
        # Issuer scheme (kubernetes.io/tls)
        scheme: kubernetes.io/tls
```

### Proxy Injector

Proxy Injector は Kubernetes Admission Webhook として動作し、Pod に sidecar を自動的に inject します。

```mermaid
sequenceDiagram
    participant User as kubectl
    participant API as API Server
    participant PI as Proxy Injector
    participant Pod as Pod

    User->>API: Pod creation request
    API->>PI: Admission Review
    PI->>PI: Check injection conditions
    alt Injection enabled
        PI->>PI: Add linkerd-proxy container
        PI->>PI: Add linkerd-init container
        PI->>PI: Configure volumes/env vars
        PI-->>API: Mutated Pod Spec
    else Injection disabled
        PI-->>API: Original Pod Spec
    end
    API->>Pod: Create Pod
```

**Injection 条件:**

```yaml
# Namespace-level injection enablement
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled

---
# Pod-level injection control
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  annotations:
    # Enable injection
    linkerd.io/inject: enabled
    # Or disable
    # linkerd.io/inject: disabled
```

**Inject されるコンポーネント:**

| コンポーネント | 役割 |
|-----------|------|
| `linkerd-init` | Init container、iptables ルールを設定 |
| `linkerd-proxy` | Sidecar container、トラフィック proxy |
| Volumes | Identity token、設定 |
| Environment Variables | Proxy 設定、destination address |

### Policy Controller

Policy Controller は Linkerd の authorization policy を管理します。

```yaml
# Server resource - defines inbound traffic
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
# ServerAuthorization - defines access permissions
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

## Data Plane

Data Plane は、application Pod に inject される `linkerd-proxy` sidecar で構成されます。

### linkerd2-proxy

Linkerd の data plane proxy は、Rust で記述された非常に軽量な micro-proxy です。

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

**Proxy の特性:**

| 特性 | 値 |
|----------------|-------|
| 言語 | Rust |
| Memory 使用量 | ~10MB |
| CPU overhead | 最小限 |
| Latency overhead | <1ms p99 |
| Protocol | HTTP/1.1, HTTP/2, gRPC, TCP |
| TLS | TLS 1.3 (rustls) |

**Istio Envoy との比較:**

| 特性 | linkerd2-proxy | Envoy (Istio) |
|----------------|---------------|---------------|
| 言語 | Rust | C++ |
| Memory | ~10MB | ~50-100MB |
| Binary サイズ | ~10MB | ~60MB |
| Latency | <1ms p99 | 2-5ms p99 |
| Config の複雑さ | 低い（自動） | 高い（xDS） |
| 拡張性 | 制限あり | Wasm, Lua |
| Protocol サポート | HTTP, gRPC, TCP | 非常に広範囲 |

### Proxy のトラフィックフロー

```mermaid
sequenceDiagram
    participant Client as Client App
    participant CProxy as Client Proxy<br/>(Outbound)
    participant SProxy as Server Proxy<br/>(Inbound)
    participant Server as Server App

    Client->>CProxy: HTTP Request<br/>(localhost)
    Note over CProxy: iptables redirect
    CProxy->>CProxy: Lookup target service<br/>(Destination API)
    CProxy->>CProxy: Load balancing<br/>(EWMA)
    CProxy->>CProxy: mTLS handshake
    CProxy->>SProxy: Encrypted Request
    SProxy->>SProxy: mTLS verification
    SProxy->>SProxy: Policy check
    SProxy->>Server: HTTP Request
    Server-->>SProxy: HTTP Response
    SProxy-->>CProxy: Encrypted Response
    CProxy-->>Client: HTTP Response
```

### linkerd-init（Init Container）

`linkerd-init` は、トラフィックを proxy に redirect する iptables ルールを設定します。

```bash
# Example iptables rules set by linkerd-init
# Redirect outbound traffic (to port 4140)
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-port 4140

# Redirect inbound traffic (to port 4143)
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 4143

# Exclude proxy's own traffic
iptables -t nat -A OUTPUT -m owner --uid-owner 2102 -j RETURN
```

**Inject された Pod 構造:**

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

## 証明書階層

Linkerd は、階層型 PKI（Public Key Infrastructure）を使用して mTLS を実装します。

### 証明書階層構造

```mermaid
graph TB
    subgraph "Certificate Hierarchy"
        TA[Trust Anchor<br/>Root CA<br/>Validity: 10 years]
        II[Identity Issuer<br/>Intermediate CA<br/>Validity: 1 year]
        WC1[Workload Cert 1<br/>Validity: 24 hours]
        WC2[Workload Cert 2<br/>Validity: 24 hours]
        WC3[Workload Cert 3<br/>Validity: 24 hours]
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

### Trust Anchor（Root CA）

Trust Anchor は PKI の root であり、すべての証明書 chain における信頼の基盤です。

```bash
# Create Trust Anchor (using step CLI)
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h  # 10 years

# Verify Trust Anchor
openssl x509 -in ca.crt -text -noout

# Example output:
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

**Trust Anchor の保存先:**

```yaml
# Stored as Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: linkerd-identity-trust-roots
  namespace: linkerd
type: Opaque
data:
  ca-bundle.crt: <base64-encoded-ca.crt>
```

### Identity Issuer（Intermediate CA）

Identity Issuer は workload 証明書を発行する intermediate CA です。

```bash
# Create Identity Issuer certificate
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca \
  --ca ca.crt \
  --ca-key ca.key \
  --no-password \
  --insecure \
  --not-after=8760h  # 1 year

# Verify Issuer certificate
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

### Workload 証明書

各 proxy は一意の workload 証明書を受け取ります。

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant ID as Identity Controller
    participant SA as ServiceAccount

    Note over Proxy: Pod starts
    Proxy->>SA: Obtain ServiceAccount token
    Proxy->>Proxy: Generate CSR (with SPIFFE ID)
    Proxy->>ID: Send CSR + SA token
    ID->>ID: Validate SA token
    ID->>ID: Validate SPIFFE ID
    ID->>ID: Sign certificate with Issuer key
    ID-->>Proxy: Signed certificate (24-hour validity)

    Note over Proxy: After 22 hours (2 hours before expiration)
    Proxy->>ID: Renewal CSR
    ID-->>Proxy: New certificate
```

**SPIFFE ID 形式:**

```
spiffe://root.linkerd.cluster.local/ns/<namespace>/sa/<service-account>

# Example:
spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service
```

### 証明書ローテーション

```yaml
# Certificate lifetime configuration
identity:
  issuer:
    # Workload certificate lifetime (default 24 hours)
    issuanceLifetime: 24h0m0s
    # Clock skew allowance (default 20 seconds)
    clockSkewAllowance: 20s

# Proxy automatically renews certificates before expiration
# By default, renewal starts at 70% of certificate lifetime
```

**Trust Anchor のローテーション:**

```bash
# Create new Trust Anchor
step certificate create root.linkerd.cluster.local ca-new.crt ca-new.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h

# Create bundle (existing + new)
cat ca.crt ca-new.crt > ca-bundle.crt

# Update ConfigMap
kubectl create configmap linkerd-identity-trust-roots \
  --from-file=ca-bundle.crt=ca-bundle.crt \
  -n linkerd \
  --dry-run=client -o yaml | kubectl apply -f -

# Then restart all proxies to apply new bundle
kubectl rollout restart deploy -n my-app
```

## Sidecar Injection の詳細

### Injection ワークフロー

```mermaid
graph TB
    subgraph "Injection Flow"
        REQ[Pod Creation Request]
        WH[Webhook Call]
        CHK[Check Injection Conditions]
        INJ[Inject Sidecar]
        POD[Create Pod]
    end

    subgraph "Injection Conditions"
        NS[Namespace Annotation]
        POD_ANN[Pod Annotation]
        WL[Workload Type]
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

### Injection annotation

```yaml
# Namespace level
metadata:
  annotations:
    linkerd.io/inject: enabled  # Inject into all Pods

# Pod/Deployment level
metadata:
  annotations:
    # Enable/disable injection
    linkerd.io/inject: enabled|disabled

    # Proxy configuration overrides
    config.linkerd.io/proxy-cpu-request: "100m"
    config.linkerd.io/proxy-memory-request: "64Mi"
    config.linkerd.io/proxy-cpu-limit: "1"
    config.linkerd.io/proxy-memory-limit: "250Mi"

    # Proxy log level
    config.linkerd.io/proxy-log-level: "warn,linkerd=info"

    # Skip ports (bypass proxy)
    config.linkerd.io/skip-inbound-ports: "25,587"
    config.linkerd.io/skip-outbound-ports: "25,587"

    # Opaque ports (bypass protocol detection)
    config.linkerd.io/opaque-ports: "3306,5432"
```

### Proxy Readiness/Liveness

```yaml
# Proxy health check endpoints
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

## コンポーネント間通信

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

**Port の一覧:**

| コンポーネント | Port | Protocol | 用途 |
|-----------|------|----------|---------|
| Destination | 8086 | gRPC | Service discovery API |
| Identity | 8080 | gRPC | 証明書発行 API |
| Policy | 8090 | gRPC | Policy API |
| Proxy Injector | 8443 | HTTPS | Admission Webhook |
| Proxy (Inbound) | 4143 | HTTP/gRPC | Inbound トラフィック |
| Proxy (Outbound) | 4140 | HTTP/gRPC | Outbound トラフィック |
| Proxy (Admin) | 4191 | HTTP | Metrics、health check |

## Istio アーキテクチャとの比較

### Control Plane の比較

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

| 特性 | Linkerd | Istio |
|----------------|---------|-------|
| Control Plane | 分散型（3 コンポーネント） | 統合型（istiod） |
| Proxy | linkerd2-proxy（Rust） | Envoy（C++） |
| Config Protocol | Custom gRPC | xDS（複雑） |
| CRD 数 | ~10 | ~50+ |
| 学習曲線 | 緩やか | 急峻 |
| リソース使用量 | 低い | 高い |
| 拡張性 | 制限あり | Wasm, Lua |

### Proxy の比較

```yaml
# Linkerd Proxy Resources (typical)
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 1000m
    memory: 250Mi

# Envoy Proxy Resources (typical)
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 2000m
    memory: 1Gi
```

## 次のステップ

- [Traffic Management](./03-traffic-management.md): ServiceProfile と traffic splitting
- [Security](./04-security.md): mTLS と authorization policy
- [Observability](./05-observability.md): Metrics と dashboard

## 参考資料

- [Linkerd アーキテクチャ](https://linkerd.io/2/reference/architecture/)
- [linkerd2-proxy GitHub](https://github.com/linkerd/linkerd2-proxy)
- [Linkerd Identity](https://linkerd.io/2/features/automatic-mtls/)
- [Proxy Injection](https://linkerd.io/2/features/proxy-injection/)
