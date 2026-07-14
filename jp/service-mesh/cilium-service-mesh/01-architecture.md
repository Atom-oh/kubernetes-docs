# Cilium Service Mesh アーキテクチャ

> **対応バージョン**: Cilium 1.16+, Kubernetes 1.28+
> **最終更新**: February 22, 2026

## 概要

Cilium Service Mesh のアーキテクチャは、従来のサイドカー型 Service Mesh とは根本的に異なります。eBPF を活用してカーネルレベルで L3/L4 トラフィックを処理し、ノードごとに単一の共有 Envoy proxy を通じて L7 機能を提供します。この章では、Cilium Service Mesh の主要なアーキテクチャコンポーネントと動作を詳しく説明します。

## 全体アーキテクチャ

```mermaid
graph TB
    subgraph "Kubernetes Node"
        subgraph "User Space"
            CA[Cilium Agent]
            CO[Cilium Operator]
            NE[Node Envoy<br/>L7 Proxy]
            HR[Hubble Relay]
        end

        subgraph "Kernel Space"
            eBPF[eBPF Programs]
            TC[TC/XDP Hooks]
            CT[Connection Tracking]
            LB[Load Balancer Maps]
            Policy[Policy Maps]
        end

        subgraph "Pods"
            P1[Pod A]
            P2[Pod B]
            P3[Pod C]
        end

        CA --> eBPF
        CA --> NE
        eBPF --> TC
        eBPF --> CT
        eBPF --> LB
        eBPF --> Policy

        P1 --> TC
        P2 --> TC
        P3 --> TC
        TC --> NE
    end

    subgraph "Control Plane"
        API[Kubernetes API Server]
        CRD[Cilium CRDs]
    end

    API --> CA
    API --> CO
    CRD --> CA
```

## eBPF Datapath

### eBPF とは？

eBPF（extended Berkeley Packet Filter）は、Linux カーネル内でサンドボックス化されたプログラムを実行できる技術です。カーネルを変更せずに、ネットワーキング、セキュリティ、オブザーバビリティの機能を実装できます。

```mermaid
graph LR
    subgraph "Traditional Networking"
        App1[Application] --> Kernel1[Kernel<br/>Network Stack]
        Kernel1 --> NIC1[NIC]
    end

    subgraph "eBPF Networking"
        App2[Application] --> eBPF2[eBPF<br/>Programs]
        eBPF2 --> Kernel2[Kernel<br/>Network Stack]
        Kernel2 --> NIC2[NIC]
        eBPF2 -.-> |"Bypass"| NIC2
    end
```

### eBPF Hook Point

Cilium は複数の eBPF Hook Point を利用します。

| Hook Point | 場所 | 目的 |
|------------|----------|---------|
| **XDP (eXpress Data Path)** | NIC Driver | 超高速パケット処理、DDoS 保護 |
| **TC (Traffic Control)** | Network Stack Entry | パケットフィルタリング、リダイレクト |
| **Socket Operations** | Socket Level | Socket 接続の高速化 |
| **cgroup** | Process Group | リソース制御、ポリシー適用 |

```mermaid
graph TB
    subgraph "Packet Flow with eBPF Hooks"
        NIC[NIC] --> XDP[XDP Hook]
        XDP --> TC_IN[TC Ingress]
        TC_IN --> Stack[Network Stack]
        Stack --> Socket[Socket Layer]
        Socket --> App[Application]

        App --> Socket
        Socket --> Stack
        Stack --> TC_OUT[TC Egress]
        TC_OUT --> NIC
    end

    style XDP fill:#e1f5fe
    style TC_IN fill:#e1f5fe
    style TC_OUT fill:#e1f5fe
    style Socket fill:#e1f5fe
```

### L3/L4 処理

eBPF における L3/L4 処理は次のように動作します。

```mermaid
sequenceDiagram
    participant Pod as Source Pod
    participant TC as TC eBPF
    participant CT as Connection Tracker
    participant LB as Load Balancer
    participant Policy as Policy Engine
    participant Dest as Destination Pod

    Pod->>TC: Send Packet
    TC->>CT: Lookup Connection State

    alt New Connection
        CT->>LB: Check Service IP
        LB->>CT: Return Backend Pod IP
        CT->>Policy: Evaluate Policy
        Policy->>CT: Allow/Deny
    else Existing Connection
        CT->>TC: Return Cached Decision
    end

    TC->>Dest: Deliver Packet
```

#### eBPF Map 構造

```c
// Connection Tracking Map
struct ct_entry {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8  protocol;
    __u64 lifetime;
    __u32 rx_packets;
    __u32 tx_packets;
};

// Service Map
struct lb_service {
    __u32 service_ip;
    __u16 service_port;
    __u32 backend_count;
    __u32 backend_slot;
};

// Policy Map
struct policy_entry {
    __u32 identity;
    __u16 port;
    __u8  protocol;
    __u8  action;  // ALLOW, DENY, AUDIT
};
```

### kube-proxy の置き換え

Cilium の eBPF ベース Load Balancer は、kube-proxy を完全に置き換えられます。

```yaml
# Enable kube-proxy replacement during Cilium installation
kubeProxyReplacement: true

# Load balancer algorithm configuration
loadBalancer:
  algorithm: maglev  # or random
  mode: dsr          # Direct Server Return
```

**kube-proxy と Cilium eBPF の比較:**

| 機能 | kube-proxy (iptables) | Cilium eBPF |
|---------|----------------------|-------------|
| ルールの複雑さ | O(n) - Service 数に比例 | O(1) - hash map ルックアップ |
| Connection Tracking | conntrack module | eBPF CT Map |
| DSR サポート | 制限あり | 完全サポート |
| Session Affinity | iptables ベース | Maglev hashing |
| パフォーマンス | 中 | 高 |

## ノードごとの Envoy Proxy

### Sidecar と Node Proxy

```mermaid
graph TB
    subgraph "Sidecar Model"
        subgraph "Pod A"
            AppA1[App]
            ProxyA1[Envoy<br/>50MB RAM]
        end
        subgraph "Pod B"
            AppB1[App]
            ProxyB1[Envoy<br/>50MB RAM]
        end
        subgraph "Pod C"
            AppC1[App]
            ProxyC1[Envoy<br/>50MB RAM]
        end
    end

    subgraph "Node Proxy Model"
        subgraph "Node"
            AppA2[Pod A<br/>App]
            AppB2[Pod B<br/>App]
            AppC2[Pod C<br/>App]
            NodeProxy[Shared Envoy<br/>100MB RAM]
        end
    end
```

### Envoy のデプロイ方法

Cilium は DaemonSet として、ノードごとに 1 つの Envoy proxy をデプロイします。

```bash
# Check Envoy DaemonSet
kubectl get daemonset -n kube-system cilium-envoy

# Expected output
NAME           DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE
cilium-envoy   3         3         3       3            3
```

### L7 処理フロー

```mermaid
sequenceDiagram
    participant Client as Client Pod
    participant eBPF as eBPF Datapath
    participant Envoy as Node Envoy
    participant Server as Server Pod

    Client->>eBPF: HTTP Request
    Note over eBPF: Check L4 Policy

    alt L7 Policy Required
        eBPF->>Envoy: Redirect Traffic
        Note over Envoy: HTTP Parsing<br/>L7 Policy Enforcement<br/>Header Manipulation
        Envoy->>eBPF: Processed Request
    end

    eBPF->>Server: Deliver Packet
    Server->>eBPF: HTTP Response

    alt L7 Policy Required
        eBPF->>Envoy: Redirect Response
        Envoy->>eBPF: Processed Response
    end

    eBPF->>Client: Deliver Response
```

### Envoy リソース設定

```yaml
# values.yaml
envoy:
  enabled: true
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 100m
      memory: 256Mi

  # Envoy concurrent connection settings
  maxConnectionsPerHost: 1000
  connectTimeout: 5s

  # Proxy protocol settings
  proxy:
    protocol:
      http2:
        enabled: true
      tls:
        enabled: true
```

## CRD モデル

### Cilium CRD 構造

```mermaid
graph TB
    subgraph "Network Policy CRDs"
        CNP[CiliumNetworkPolicy]
        CCNP[CiliumClusterwideNetworkPolicy]
    end

    subgraph "Envoy Configuration CRDs"
        CEC[CiliumEnvoyConfig]
        CCEC[CiliumClusterwideEnvoyConfig]
    end

    subgraph "Service Mesh CRDs"
        CLB[CiliumLoadBalancerIPPool]
        CBGP[CiliumBGPPeeringPolicy]
        CEG[CiliumEgressGateway]
    end

    subgraph "Identity CRDs"
        CID[CiliumIdentity]
        CEP[CiliumEndpoint]
    end

    CNP --> CEP
    CCNP --> CEP
    CEC --> CEP
    CCEC --> CEP
```

### CiliumEnvoyConfig

CiliumEnvoyConfig は Namespace スコープの Envoy 設定を定義します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: http-filter
  namespace: default
spec:
  # Services this configuration applies to
  services:
  - name: my-service
    namespace: default

  # Envoy resource definitions
  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-service-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service
          route_config:
            name: local_route
            virtual_hosts:
            - name: my-service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: default/my-service
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

### CiliumClusterwideEnvoyConfig

クラスター全体の Envoy 設定:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideEnvoyConfig
metadata:
  name: global-ratelimit
spec:
  # Apply to all services cluster-wide
  services:
  - name: "*"
    namespace: "*"

  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    name: global-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: global
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

### CiliumNetworkPolicy (L7)

L7 ルールを含む Network Policy:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/api/v1/.*"
          headers:
          - name: "X-Request-ID"
            value: ".*"
        - method: POST
          path: "/api/v1/users"
        - method: DELETE
          path: "/api/v1/users/[0-9]+"

  egress:
  - toEndpoints:
    - matchLabels:
        app: database
    toPorts:
    - ports:
      - port: "5432"
        protocol: TCP
```

## Cilium Agent と Service Mesh

### Cilium Agent の役割

```mermaid
graph TB
    subgraph "Cilium Agent Responsibilities"
        direction TB

        subgraph "Network Management"
            IPAM[IPAM<br/>IP Address Management]
            Routing[Routing<br/>Table Management]
            LB[Load Balancing<br/>Service Management]
        end

        subgraph "Policy Management"
            Policy[Policy Compilation]
            Identity[Identity Management]
            Endpoint[Endpoint<br/>Management]
        end

        subgraph "Proxy Management"
            EnvoyConfig[Envoy Config<br/>Generation]
            EnvoySync[Envoy Sync]
            L7Policy[L7 Policy<br/>Translation]
        end

        subgraph "Observability"
            FlowLog[Flow Logging]
            Metrics[Metrics Collection]
            Events[Event Generation]
        end
    end

    API[K8s API] --> IPAM
    API --> Policy
    API --> EnvoyConfig

    IPAM --> Routing
    Policy --> Identity
    Identity --> Endpoint
    EnvoyConfig --> EnvoySync

    Endpoint --> FlowLog
    LB --> Metrics
```

### Agent 設定

```yaml
# ConfigMap: cilium-config
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Agent basic settings
  debug: "false"
  enable-ipv4: "true"
  enable-ipv6: "false"

  # Service mesh settings
  enable-l7-proxy: "true"
  enable-envoy-config: "true"

  # kube-proxy replacement
  kube-proxy-replacement: "true"

  # Observability
  enable-hubble: "true"
  hubble-listen-address: ":4244"
  hubble-metrics-server: ":9965"

  # Encryption
  enable-wireguard: "true"
  enable-ipsec: "false"
```

## Service Identity と SPIFFE

### Cilium Identity

Cilium は各 workload に一意の Identity を割り当てます。

```mermaid
graph TB
    subgraph "Identity Assignment"
        Pod[Pod] --> Labels[Labels]
        Labels --> Identity[Cilium Identity<br/>Numeric ID]
        Identity --> SecurityContext[Security Context]
    end

    subgraph "Identity Components"
        Namespace[Namespace]
        ServiceAccount[Service Account]
        PodLabels[Pod Labels]
    end

    Namespace --> Identity
    ServiceAccount --> Identity
    PodLabels --> Identity
```

### Identity ベースの Policy

```yaml
# Check Pod's Identity
apiVersion: cilium.io/v2
kind: CiliumIdentity
metadata:
  name: "12345"
  labels:
    app: frontend
    k8s:io.kubernetes.pod.namespace: default
spec:
  security-labels:
    k8s:app: frontend
    k8s:io.kubernetes.pod.namespace: default
```

```bash
# List identities
cilium identity list

# Expected output
ID      LABELS
1       reserved:host
2       reserved:world
3       reserved:health
12345   k8s:app=frontend,k8s:io.kubernetes.pod.namespace=default
12346   k8s:app=backend,k8s:io.kubernetes.pod.namespace=default
```

### SPIFFE 統合

SPIFFE（Secure Production Identity Framework for Everyone）による workload Identity:

```mermaid
graph LR
    subgraph "SPIFFE Integration"
        Workload[Workload] --> Agent[SPIRE Agent]
        Agent --> Server[SPIRE Server]
        Server --> CA[Certificate Authority]
        CA --> SVID[SVID<br/>X.509 Certificate]
        SVID --> Workload
    end
```

```yaml
# SPIRE integration configuration
authentication:
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
        server:
          dataStorage:
            size: 1Gi
        agent:
          socketPath: /run/spire/sockets/agent.sock
```

SPIFFE ID 形式:
```
spiffe://cluster.local/ns/<namespace>/sa/<service-account>
```

## パケットフロー分析

### Pod 間通信（同一 Node）

```mermaid
sequenceDiagram
    participant PodA as Pod A
    participant VethA as veth (Pod A)
    participant eBPF_In as eBPF Ingress
    participant CT as CT Map
    participant Policy as Policy Map
    participant eBPF_Out as eBPF Egress
    participant VethB as veth (Pod B)
    participant PodB as Pod B

    PodA->>VethA: Send Packet
    VethA->>eBPF_In: TC Ingress
    eBPF_In->>CT: Connection Lookup
    CT->>Policy: Policy Check
    Policy->>eBPF_Out: Allow
    eBPF_Out->>VethB: Direct Forward
    VethB->>PodB: Receive Packet

    Note over eBPF_In,eBPF_Out: Direct path in kernel<br/>Bypass network stack
```

### Pod 間通信（異なる Node）

```mermaid
sequenceDiagram
    participant PodA as Pod A (Node 1)
    participant eBPF1 as eBPF (Node 1)
    participant Tunnel as Tunnel/Native
    participant eBPF2 as eBPF (Node 2)
    participant PodB as Pod B (Node 2)

    PodA->>eBPF1: Send Packet
    Note over eBPF1: Policy Evaluation<br/>Tunnel Encapsulation
    eBPF1->>Tunnel: VXLAN/Geneve/Native
    Tunnel->>eBPF2: Receive Packet
    Note over eBPF2: Policy Evaluation<br/>Tunnel Decapsulation
    eBPF2->>PodB: Deliver Packet
```

### L7 処理が必要な場合

```mermaid
sequenceDiagram
    participant Client as Client Pod
    participant eBPF_C as eBPF (Client)
    participant Envoy as Node Envoy
    participant eBPF_S as eBPF (Server)
    participant Server as Server Pod

    Client->>eBPF_C: HTTP Request
    Note over eBPF_C: Detect L7 Policy
    eBPF_C->>Envoy: Redirect to Proxy

    Note over Envoy: HTTP Parsing<br/>L7 Policy Enforcement<br/>Metrics Collection<br/>Tracing

    Envoy->>eBPF_S: Forward Request
    eBPF_S->>Server: Deliver Packet

    Server->>eBPF_S: HTTP Response
    eBPF_S->>Envoy: Forward Response

    Note over Envoy: Response Processing<br/>Metrics Update

    Envoy->>eBPF_C: Forward Response
    eBPF_C->>Client: Deliver Response
```

## Istio Sidecar アーキテクチャとの比較

### アーキテクチャ比較表

| 観点 | Cilium Service Mesh | Istio Sidecar |
|--------|---------------------|---------------|
| **Proxy の配置** | Node ごとに 1 つ | Pod ごとに 1 つ |
| **Proxy の種類** | eBPF + Envoy | Envoy のみ |
| **L4 処理** | Kernel（eBPF） | User space（Envoy） |
| **L7 処理** | User space（Envoy） | User space（Envoy） |
| **メモリ使用量** | ~100MB/node | ~50MB/Pod |
| **CPU 使用量** | 低 | 中～高 |
| **レイテンシー** | 0.1-0.5ms | 1-3ms |
| **設定モデル** | CiliumEnvoyConfig | VirtualService/DestinationRule |
| **mTLS 実装** | eBPF/WireGuard | Envoy |
| **Injection** | 不要 | Sidecar injection が必要 |

### レイテンシー分析

```mermaid
graph TB
    subgraph "Istio Latency Components"
        I1[App → Sidecar] --> I2[Sidecar Processing]
        I2 --> I3[Network]
        I3 --> I4[Sidecar Processing]
        I4 --> I5[Sidecar → App]

        I1 -.- |"~0.2ms"| I1
        I2 -.- |"~0.5ms"| I2
        I3 -.- |"~0.1ms"| I3
        I4 -.- |"~0.5ms"| I4
        I5 -.- |"~0.2ms"| I5
    end

    subgraph "Cilium Latency Components"
        C1[App → eBPF] --> C2[eBPF Processing]
        C2 --> C3[Network]
        C3 --> C4[eBPF Processing]
        C4 --> C5[eBPF → App]

        C1 -.- |"~0.02ms"| C1
        C2 -.- |"~0.05ms"| C2
        C3 -.- |"~0.1ms"| C3
        C4 -.- |"~0.05ms"| C4
        C5 -.- |"~0.02ms"| C5
    end
```

### リソース効率分析

100 Pod のクラスターの場合:

```mermaid
graph LR
    subgraph "Memory Usage"
        Istio[Istio<br/>100 pods × 50MB<br/>= 5GB]
        Cilium[Cilium<br/>5 nodes × 100MB<br/>= 500MB]
    end

    subgraph "CPU Overhead"
        IstioC[Istio<br/>100 sidecars<br/>High CPU overhead]
        CiliumC[Cilium<br/>5 Node Envoys<br/>Low CPU overhead]
    end
```

## スケーラビリティに関する考慮事項

### eBPF Map サイズ

```yaml
# Cilium ConfigMap settings
bpf-map-dynamic-size-ratio: "0.0025"
bpf-ct-global-tcp-max: "524288"
bpf-ct-global-any-max: "262144"
bpf-nat-global-max: "524288"
bpf-policy-map-max: "16384"
```

### 大規模クラスター設定

```yaml
# Large cluster (1000+ nodes) configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Identity-related settings
  cluster-id: "1"
  cluster-name: "production"

  # Connection tracking optimization
  bpf-ct-global-tcp-max: "1048576"
  bpf-ct-global-any-max: "524288"

  # NAT table size
  bpf-nat-global-max: "1048576"

  # Policy map size
  bpf-policy-map-max: "65536"

  # Performance optimization
  sockops-enable: "true"
  bpf-lb-sock: "true"

  # Hubble settings
  hubble-disable: "false"
  hubble-socket-path: "/var/run/cilium/hubble.sock"
```

### Node Envoy のスケーリング

```yaml
# Envoy resource scaling
envoy:
  resources:
    limits:
      cpu: 4000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 512Mi

  # Envoy worker threads
  concurrency: 4

  # Connection limits
  perConnectionBufferLimitBytes: 32768

  # Cluster settings
  cluster:
    connectTimeout: 5s
    circuitBreakers:
      maxConnections: 10000
      maxPendingRequests: 10000
      maxRequests: 10000
```

## 次のステップ

- [Traffic Management](./02-traffic-management.md): L7 routing と traffic control を設定する
- [Security](./03-security.md): mTLS と L7 network policy を設定する
- [Observability](./04-observability.md): Hubble で Service Mesh を監視する

## 参照資料

- [Cilium Architecture Documentation](https://docs.cilium.io/en/stable/concepts/overview/)
- [eBPF Documentation](https://ebpf.io/what-is-ebpf/)
- [Envoy Proxy Architecture](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview)
- [SPIFFE Specification](https://spiffe.io/docs/latest/spiffe-about/overview/)
