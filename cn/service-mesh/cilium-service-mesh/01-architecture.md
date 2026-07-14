# Cilium Service Mesh 架构

> **支持的版本**: Cilium 1.16+, Kubernetes 1.28+
> **最后更新**: February 22, 2026

## 概述

Cilium Service Mesh 的架构与传统基于 sidecar 的服务网格有着根本性的不同。它利用 eBPF 在内核级别处理 L3/L4 流量，并通过每个节点一个共享的 Envoy proxy 提供 L7 功能。本章将详细说明 Cilium Service Mesh 的核心架构组件和运行方式。

## 整体架构

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

## eBPF 数据路径

### 什么是 eBPF？

eBPF（extended Berkeley Packet Filter）是一项可在 Linux 内核中运行沙箱程序的技术。它无需修改内核即可实现网络、安全和可观测性功能。

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

### eBPF 挂载点

Cilium 使用多个 eBPF 挂载点：

| 挂载点 | 位置 | 用途 |
|------------|----------|---------|
| **XDP (eXpress Data Path)** | NIC 驱动程序 | 超高速数据包处理、DDoS 防护 |
| **TC (Traffic Control)** | 网络栈入口 | 数据包过滤、重定向 |
| **Socket 操作** | Socket 层级 | Socket 连接加速 |
| **cgroup** | 进程组 | 资源控制、策略执行 |

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

### L3/L4 处理

eBPF 中的 L3/L4 处理流程如下：

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

#### eBPF Map 结构

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

### kube-proxy 替代方案

Cilium 基于 eBPF 的负载均衡器可完全替代 kube-proxy：

```yaml
# Enable kube-proxy replacement during Cilium installation
kubeProxyReplacement: true

# Load balancer algorithm configuration
loadBalancer:
  algorithm: maglev  # or random
  mode: dsr          # Direct Server Return
```

**kube-proxy 与 Cilium eBPF 对比：**

| 功能 | kube-proxy (iptables) | Cilium eBPF |
|---------|----------------------|-------------|
| 规则复杂度 | O(n) - 与 Service 数量成正比 | O(1) - hash map 查找 |
| 连接跟踪 | conntrack 模块 | eBPF CT Map |
| DSR 支持 | 有限 | 完整支持 |
| 会话亲和性 | 基于 iptables | Maglev hashing |
| 性能 | 中等 | 高 |

## 每节点 Envoy Proxy

### Sidecar 与节点 Proxy

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

### Envoy 部署方式

Cilium 通过 DaemonSet 在每个节点上部署一个 Envoy proxy：

```bash
# Check Envoy DaemonSet
kubectl get daemonset -n kube-system cilium-envoy

# Expected output
NAME           DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE
cilium-envoy   3         3         3       3            3
```

### L7 处理流程

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

### Envoy 资源配置

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

## CRD 模型

### Cilium CRD 结构

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

CiliumEnvoyConfig 定义 namespace 作用域的 Envoy 配置：

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

集群范围的 Envoy 配置：

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

包含 L7 规则的网络策略：

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

## Cilium Agent 与 Service Mesh

### Cilium Agent 的角色

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

### Agent 配置

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

## Service Identity 和 SPIFFE

### Cilium Identity

Cilium 为每个 workload 分配唯一的 identity：

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

### 基于 Identity 的策略

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

### SPIFFE 集成

通过 SPIFFE（Secure Production Identity Framework for Everyone）实现 workload identity：

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

SPIFFE ID 格式：
```
spiffe://cluster.local/ns/<namespace>/sa/<service-account>
```

## 数据包流分析

### Pod 到 Pod 通信（同一节点）

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

### Pod 到 Pod 通信（不同节点）

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

### 需要 L7 处理时

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
    eBPF_C->>Client: Deliver Packet
```

## 与 Istio Sidecar 架构的比较

### 架构对比表

| 方面 | Cilium Service Mesh | Istio Sidecar |
|--------|---------------------|---------------|
| **Proxy 位置** | 每个节点 1 个 | 每个 Pod 1 个 |
| **Proxy 类型** | eBPF + Envoy | 仅 Envoy |
| **L4 处理** | 内核（eBPF） | 用户空间（Envoy） |
| **L7 处理** | 用户空间（Envoy） | 用户空间（Envoy） |
| **内存使用量** | ~100MB/节点 | ~50MB/Pod |
| **CPU 使用量** | 低 | 中高 |
| **延迟** | 0.1-0.5ms | 1-3ms |
| **配置模型** | CiliumEnvoyConfig | VirtualService/DestinationRule |
| **mTLS 实现** | eBPF/WireGuard | Envoy |
| **注入** | 不需要 | 需要注入 Sidecar |

### 延迟分析

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

### 资源效率分析

对于一个包含 100 个 Pod 的集群：

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

## 可扩展性注意事项

### eBPF Map 大小

```yaml
# Cilium ConfigMap settings
bpf-map-dynamic-size-ratio: "0.0025"
bpf-ct-global-tcp-max: "524288"
bpf-ct-global-any-max: "262144"
bpf-nat-global-max: "524288"
bpf-policy-map-max: "16384"
```

### 大型集群配置

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

### Node Envoy 扩缩容

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

## 后续步骤

- [流量管理](./02-traffic-management.md)：配置 L7 路由和流量控制
- [安全](./03-security.md)：设置 mTLS 和 L7 网络策略
- [可观测性](./04-observability.md)：使用 Hubble 监控服务网格

## 参考资料

- [Cilium 架构文档](https://docs.cilium.io/en/stable/concepts/overview/)
- [eBPF 文档](https://ebpf.io/what-is-ebpf/)
- [Envoy Proxy 架构](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview)
- [SPIFFE 规范](https://spiffe.io/docs/latest/spiffe-about/overview/)
