# Cilium Service Mesh 安全性

> **支持的版本**: Cilium 1.16+, Kubernetes 1.28+
> **最后更新**: July 13, 2026

## 概述

Cilium Service Mesh 基于 eBPF 和 SPIFFE 提供强大的安全功能。您可以通过透明 mTLS、基于身份的网络策略和 WireGuard 加密实现零信任网络。本章将详细说明 Cilium Service Mesh 的安全架构和配置方法。

## 安全架构

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Transport Security"
            mTLS[Mutual TLS]
            WG[WireGuard Encryption]
            IPsec[IPsec]
        end

        subgraph "Identity Security"
            SPIFFE[SPIFFE/SPIRE]
            CiliumID[Cilium Identity]
            SA[Service Account]
        end

        subgraph "Policy Security"
            L3L4[L3/L4 Network Policy]
            L7[L7 Network Policy]
            Auth[Authorization Policy]
        end
    end

    Pod[Pod] --> CiliumID
    CiliumID --> SPIFFE
    SPIFFE --> mTLS

    Pod --> L3L4
    L3L4 --> L7
    L7 --> Auth
```

## 透明 mTLS

### 无 Sidecar 的 mTLS

Cilium Service Mesh 提供无需 Sidecar 代理的透明 mTLS：

```mermaid
sequenceDiagram
    participant PodA as Pod A
    participant eBPFA as eBPF (Node A)
    participant SPIRE as SPIRE Agent
    participant eBPFB as eBPF (Node B)
    participant PodB as Pod B

    PodA->>eBPFA: Plain TCP
    eBPFA->>SPIRE: Get SVID
    SPIRE->>eBPFA: X.509 Certificate
    Note over eBPFA: TLS Handshake
    eBPFA->>eBPFB: Encrypted Traffic
    Note over eBPFB: TLS Verification
    eBPFB->>PodB: Plain TCP

    Note over PodA,PodB: No application code changes required
```

### 通过 ztunnel 实现的原生 mTLS（2026 更新）

2026 年 3 月，Cilium 引入了受 Istio Ambient 的 ztunnel 模型启发的更新版 mTLS 架构，超越了上文所示的纯 eBPF 握手方式。该技术栈现在包含三个协作组件：

- **SPIRE** — 颁发工作负载身份和 X.509 证书（与下方基于 SPIRE 的配置中作用相同）
- **Cilium** — 安装 iptables 规则，将出站 Pod 流量透明地重定向到端口 15001 上的 ztunnel
- **ztunnel** — 每个 Node 一个代理（而非每个 Pod 一个 Sidecar），负责执行实际的 mTLS 握手并加密 Pod 到 Pod 的流量

这保留了相同的“无需 Sidecar、无需修改应用程序”的保证，但 TLS 握手现在在专用的每 Node 进程中运行，而非完全在 eBPF 中运行——这是 Cilium 直接采用自 Istio Ambient 的 ztunnel 的设计。截至 2026 年 3 月，该功能已作为 Azure Kubernetes Service 上的公开预览功能提供（适用于 AKS 的“Cilium mTLS encryption”）。相互身份验证仍仅适用于由 Cilium 管理的集群，并且与外部 mTLS 解决方案不兼容。

有关完整的架构说明，请参阅 [Cilium 关于原生 mTLS 的博客文章](https://cilium.io/blog/2026/03/23/native-mtls-cilium/)。

### 基于 SPIRE 的 mTLS 配置

```yaml
# values.yaml - SPIRE integration configuration
authentication:
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
        namespace: cilium-spire

        server:
          # SPIRE Server configuration
          replicas: 1
          dataStorage:
            enabled: true
            size: 1Gi
            storageClass: gp3

          # Trust Domain configuration
          trustDomain: cluster.local

          # CA configuration
          ca:
            # Use internal CA
            keyType: ec-p256
            ttl: 24h

          # Node Attestor configuration
          nodeAttestor:
            k8sPsat:
              enabled: true

        agent:
          # SPIRE Agent configuration
          socketPath: /run/spire/sockets/agent.sock

          # Workload Attestor configuration
          workloadAttestor:
            k8s:
              enabled: true
              disableContainerSelectors: false
```

### mTLS 策略强制执行

```yaml
# Enable mTLS for entire cluster
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: enforce-mtls
spec:
  endpointSelector: {}
  authentication:
  - mode: required
```

### 按 Namespace 配置 mTLS

```yaml
# Apply mTLS to specific namespace only
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-mtls
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - {}
    authentication:
    - mode: required
  egress:
  - toEndpoints:
    - {}
    authentication:
    - mode: required
```

### 按 Service 配置 mTLS

```yaml
# Enforce mTLS between specific services
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-mtls
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    authentication:
    - mode: required
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

## CiliumNetworkPolicy L7 规则

### HTTP L7 安全策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: api-server

  ingress:
  # Read-only access
  - fromEndpoints:
    - matchLabels:
        role: reader
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/api/.*"

  # Admin access
  - fromEndpoints:
    - matchLabels:
        role: admin
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: ".*"
          path: "/api/.*"
          headers:
          - "Authorization: Bearer .*"

  # Health checks
  - fromEndpoints:
    - matchLabels:
        app: monitoring
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/health"
        - method: GET
          path: "/metrics"
```

### Kafka L7 安全策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-security
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      app: kafka

  ingress:
  # Producer - allow writing to specific topics only
  - fromEndpoints:
    - matchLabels:
        role: producer
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: produce
          topic: "orders"
        - apiKey: produce
          topic: "events"
        - apiKey: metadata

  # Consumer - allow reading from specific topics only
  - fromEndpoints:
    - matchLabels:
        role: consumer
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: fetch
          topic: "orders"
        - apiKey: fetch
          topic: "events"
        - apiKey: listoffsets
          topic: "orders"
        - apiKey: listoffsets
          topic: "events"
        - apiKey: metadata
        - apiKey: findcoordinator
        - apiKey: joingroup
        - apiKey: heartbeat
        - apiKey: leavegroup
        - apiKey: syncgroup
        - apiKey: offsetcommit
          topic: "orders"
        - apiKey: offsetfetch
          topic: "orders"
```

### DNS L7 安全策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: web-application

  egress:
  # Restrict DNS queries
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        # Allow internal services only
        - matchPattern: "*.svc.cluster.local"
        # Allow specific external domains only
        - matchName: "api.stripe.com"
        - matchName: "api.aws.amazon.com"
        - matchPattern: "*.s3.amazonaws.com"

  # Egress to allowed external services
  - toFQDNs:
    - matchName: "api.stripe.com"
    - matchName: "api.aws.amazon.com"
    - matchPattern: "*.s3.amazonaws.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

## 相互身份验证

### 身份验证模式

```yaml
# Cilium authentication mode options

# 1. disabled - no authentication (default)
authentication:
- mode: disabled

# 2. optional - use authentication if possible, otherwise allow
authentication:
- mode: optional

# 3. required - authentication required
authentication:
- mode: required

# 4. test-always-fail - for testing (always fails)
authentication:
- mode: test-always-fail
```

### 相互身份验证策略示例

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: mutual-auth-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: secure-service

  ingress:
  # Allow authenticated clients only
  - fromEndpoints:
    - matchLabels:
        app: trusted-client
    authentication:
    - mode: required
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP

  # Optional authentication for monitoring
  - fromEndpoints:
    - matchLabels:
        app: prometheus
    authentication:
    - mode: optional
    toPorts:
    - ports:
      - port: "9090"
        protocol: TCP
```

### 基于 SPIFFE ID 的身份验证

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: spiffe-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: database

  ingress:
  # Allow specific SPIFFE ID only
  - fromEndpoints:
    - matchLabels:
        app: backend
    authentication:
    - mode: required
      # SPIFFE ID verification is performed automatically
      # spiffe://cluster.local/ns/default/sa/backend
```

## 加密

### WireGuard 透明加密

WireGuard 在 Linux 内核级别加密所有 Pod 到 Pod 的流量：

```yaml
# values.yaml - Enable WireGuard
encryption:
  enabled: true
  type: wireguard

  wireguard:
    # Userspace fallback (when kernel support unavailable)
    userspaceFallback: true

  # Node-to-node encryption
  nodeEncryption: true
```

```bash
# Check WireGuard status
cilium status | grep Encryption

# Expected output
Encryption:              Wireguard  [NodeEncryption: Enabled, cilium_wg0 (Pubkey: xxx, Port: 51871, Peers: 2)]

# Check WireGuard peers
cilium encrypt status

# Expected output
Encryption: Wireguard
Keys in use: 1
Max Seq. Number: 0x0
Errors: 0
```

#### WireGuard 架构

```mermaid
graph TB
    subgraph "Node A"
        PodA[Pod A]
        CiliumA[Cilium Agent]
        WGA[WireGuard Interface<br/>cilium_wg0]
    end

    subgraph "Node B"
        PodB[Pod B]
        CiliumB[Cilium Agent]
        WGB[WireGuard Interface<br/>cilium_wg0]
    end

    PodA --> CiliumA
    CiliumA --> WGA
    WGA <-->|"Encrypted Tunnel<br/>(ChaCha20Poly1305)"| WGB
    WGB --> CiliumB
    CiliumB --> PodB
```

### IPsec 加密

```yaml
# values.yaml - Enable IPsec
encryption:
  enabled: true
  type: ipsec

  ipsec:
    # IPsec interface
    interface: ""

    # Key rotation interval
    keyRotationDuration: "5m"

    # Encryption interface
    mountPath: /etc/ipsec

# Generate IPsec key
# kubectl create secret generic -n kube-system cilium-ipsec-keys \
#   --from-literal=keys="3 rfc4106(gcm(aes)) $(openssl rand -hex 20) 128"
```

### 加密对比

| Feature | WireGuard | IPsec |
|---------|-----------|-------|
| Performance | Very High | High |
| Configuration Complexity | Low | Medium |
| Kernel Support | 5.6+ (built-in) | All versions |
| Encryption Algorithm | ChaCha20Poly1305 | AES-GCM, etc. |
| Key Management | Automatic | Manual/Automatic |
| Standard | Non-standard | IETF Standard |

## 基于身份的安全性

### Cilium Identity

Cilium 根据身份而非 IP 应用安全策略：

```mermaid
graph LR
    subgraph "Identity Assignment"
        Pod[Pod] --> Labels[Labels]
        Labels --> Hash[Hash Function]
        Hash --> Identity[Numeric Identity<br/>e.g., 12345]
    end

    subgraph "Policy Evaluation"
        Identity --> PolicyMap[Policy Map]
        PolicyMap --> Decision[Allow/Deny]
    end
```

### Identity 组件

```bash
# Identity label composition
# - k8s:io.kubernetes.pod.namespace
# - k8s:io.cilium.k8s.policy.serviceaccount
# - k8s:app
# - k8s:version
# - Other user-defined labels

# List identities
cilium identity list

# Example output
IDENTITY   LABELS
1          reserved:host
2          reserved:world
3          reserved:unmanaged
4          reserved:health
5          reserved:init
6          reserved:remote-node
12345      k8s:app=frontend,k8s:io.kubernetes.pod.namespace=default
12346      k8s:app=backend,k8s:io.kubernetes.pod.namespace=default
```

### 基于身份的策略

```yaml
# Identity-based network policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  # Allow only Pods with specific labels (Identity)
  - fromEndpoints:
    - matchLabels:
        app: frontend
        environment: production
    toPorts:
    - ports:
      - port: "8080"

  # Allow specific service from another namespace
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        app: prometheus
    toPorts:
    - ports:
      - port: "9090"
```

### IP 与 Identity 对比

```mermaid
graph TB
    subgraph "IP-based Security (Traditional)"
        IPPolicy[IP-based Policy]
        IP1[10.0.1.5 -> 10.0.2.10: Allow]
        IP2[Problem: Policy update needed<br/>when Pod IP changes]
    end

    subgraph "Identity-based Security (Cilium)"
        IDPolicy[Identity-based Policy]
        ID1[frontend -> backend: Allow]
        ID2[Benefit: Unaffected by<br/>IP changes]
    end
```

## 外部 PKI 集成

### cert-manager 集成

```yaml
# Certificate management with cert-manager
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h  # 1 year
  renewBefore: 720h  # Renew 30 days before expiry
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
  subject:
    organizations:
    - Cilium
  commonName: SPIRE CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
```

### Vault 集成

```yaml
# Use Vault as CA in SPIRE
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server-config
  namespace: cilium-spire
data:
  server.conf: |
    server {
      trust_domain = "cluster.local"

      ca_subject = {
        country = ["US"]
        organization = ["MyOrg"]
        common_name = ""
      }

      # Vault UpstreamAuthority
      UpstreamAuthority "vault" {
        plugin_data {
          vault_addr = "https://vault.vault.svc:8200"
          pki_mount_path = "pki"
          ca_cert_path = "/vault/ca/ca.crt"
          token_path = "/vault/token/token"
        }
      }
    }
```

## 零信任网络

### 默认拒绝策略

```yaml
# Cluster-wide default deny
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: default-deny
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        reserved:host: ""
  egress:
  - toEndpoints:
    - matchLabels:
        reserved:host: ""
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
```

### 最小权限访问

```yaml
# Production namespace security policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  # Apply to all Pods
  endpointSelector: {}

  # Default deny
  ingressDeny:
  - fromEntities:
    - world

  # Allow rules
  ingress:
  # Allow communication within same namespace
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    authentication:
    - mode: required

  # Allow access from Ingress Controller
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: ingress-nginx
        app: nginx-ingress
    toPorts:
    - ports:
      - port: "8080"

  egress:
  # DNS
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP

  # Communication within same namespace
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    authentication:
    - mode: required
```

### 微分段

```yaml
# 3-tier architecture security
---
# Frontend policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: frontend

  ingress:
  - fromEntities:
    - world
    toPorts:
    - ports:
      - port: "443"

  egress:
  - toEndpoints:
    - matchLabels:
        tier: backend
    toPorts:
    - ports:
      - port: "8080"
---
# Backend policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        tier: frontend
    toPorts:
    - ports:
      - port: "8080"
    authentication:
    - mode: required

  egress:
  - toEndpoints:
    - matchLabels:
        tier: database
    toPorts:
    - ports:
      - port: "5432"
    authentication:
    - mode: required
---
# Database policy
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      tier: database

  ingress:
  - fromEndpoints:
    - matchLabels:
        tier: backend
    toPorts:
    - ports:
      - port: "5432"
    authentication:
    - mode: required

  # No external egress (data exfiltration prevention)
  egressDeny:
  - toEntities:
    - world
```

## 安全审计与监控

### 策略审计模式

```yaml
# Test policy in audit mode
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: audit-policy
  namespace: default
  annotations:
    # Audit mode - logging only, no blocking
    cilium.io/audit-mode: "true"
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
```

### 策略违规监控

```bash
# Observe policy violations with Hubble
hubble observe --verdict DROPPED

# Dropped traffic in specific namespace
hubble observe --namespace production --verdict DROPPED

# Policy violation statistics
hubble observe --verdict DROPPED -o json | jq -r '.flow | "\(.source.namespace)/\(.source.pod_name) -> \(.destination.namespace)/\(.destination.pod_name)"' | sort | uniq -c | sort -rn
```

### Prometheus 指标

```yaml
# Collect security-related metrics
hubble:
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - http
    - icmp
    - port-distribution
    - tcp

# Useful metrics
# - cilium_drop_count_total: Packets dropped by policy
# - cilium_policy_verdict: Policy decisions (allow/deny)
# - cilium_forward_count_total: Forwarded packets
```

## 后续步骤

- [可观测性](./04-observability.md): 使用 Hubble 进行安全监控
- [Ingress 与 Gateway](./05-ingress-gateway.md): 外部流量安全性
- [最佳实践](./06-best-practices.md): 生产环境安全配置

## 参考资料

- [Cilium Network Policy 文档](https://docs.cilium.io/en/stable/security/policy/)
- [Cilium 相互身份验证](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/)
- [Cilium 加密文档](https://docs.cilium.io/en/stable/security/network/encryption/)
- [SPIFFE/SPIRE 文档](https://spiffe.io/docs/latest/)
- [零信任架构 - NIST](https://www.nist.gov/publications/zero-trust-architecture)
