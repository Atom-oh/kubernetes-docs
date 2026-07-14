# パート 7: Calico の高度なトピック

> **対応バージョン**: Calico v3.29+ / Kubernetes 1.28+
> **最終更新**: February 23, 2026

## 概要

この章では、IPAM の詳細、WireGuard 暗号化、Egress Gateway、マルチクラスター・フェデレーション、Windows コンテナのサポート、大規模クラスターの設計パターンなど、本番環境向けの高度な Calico トピックを扱います。

```mermaid
graph TB
    subgraph "Advanced Calico Topics"
        IPAM[IPAM Deep Dive<br/>Block-based Allocation]
        WG[WireGuard Encryption<br/>In-transit Security]
        EG[Egress Gateway<br/>Controlled Egress]
        MC[Multi-Cluster<br/>Federation]
        WIN[Windows Support<br/>HNS Integration]
        SCALE[Large-Scale Design<br/>1000+ Nodes]
    end

    IPAM --> WG
    WG --> EG
    EG --> MC
    MC --> WIN
    WIN --> SCALE

    style IPAM fill:#4fc3f7
    style WG fill:#81c784
    style EG fill:#ffb74d
    style MC fill:#ce93d8
    style WIN fill:#ef9a9a
    style SCALE fill:#90a4ae
```

## IPAM の詳細

Calico の IP Address Management (IPAM) システムは、高いパフォーマンスとスケーラビリティを実現するよう設計されています。そのアーキテクチャを理解することは、大規模なデプロイメントの最適化に不可欠です。

### ブロックベース IPAM アーキテクチャ

Calico は、IP アドレスをブロック単位（デフォルトでは /26 = 64 IP）でノードに割り当てるブロックベースの IPAM システムを使用します。この方式によりデータストアとのやり取りが最小化され、割り当て速度が向上します。

```mermaid
graph TB
    subgraph "IPAM Architecture"
        DS[Datastore<br/>etcd/Kubernetes]

        subgraph "Node 1"
            B1A[Block A<br/>10.244.0.0/26]
            B1B[Block B<br/>10.244.0.64/26]
            P1[Pod 10.244.0.5]
            P2[Pod 10.244.0.10]
        end

        subgraph "Node 2"
            B2A[Block C<br/>10.244.1.0/26]
            P3[Pod 10.244.1.5]
            P4[Pod 10.244.1.15]
        end

        subgraph "Node 3"
            B3A[Block D<br/>10.244.2.0/26]
            B3B[Block E<br/>10.244.2.64/26]
            P5[Pod 10.244.2.20]
        end
    end

    DS --> B1A
    DS --> B1B
    DS --> B2A
    DS --> B3A
    DS --> B3B

    B1A --> P1
    B1A --> P2
    B2A --> P3
    B2A --> P4
    B3A --> P5

    style DS fill:#ff9800
    style B1A fill:#4fc3f7
    style B1B fill:#4fc3f7
    style B2A fill:#81c784
    style B3A fill:#ce93d8
    style B3B fill:#ce93d8
```

### IP ブロックのアフィニティ

ブロックアフィニティにより、IP ブロックは特定のノードへ優先的に割り当てられ、ルーティング効率が向上し、ルートテーブルのサイズが削減されます。

```yaml
# View block affinities
# calicoctl get blockaffinity -o yaml

apiVersion: projectcalico.org/v3
kind: BlockAffinity
metadata:
  name: node1-10-244-0-0-26
spec:
  cidr: 10.244.0.0/26
  node: node1
  state: confirmed
  # States: pending, confirmed, pendingDeletion
---
apiVersion: projectcalico.org/v3
kind: BlockAffinity
metadata:
  name: node1-10-244-0-64-26
spec:
  cidr: 10.244.0.64/26
  node: node1
  state: confirmed
```

### 割り当てアルゴリズム

IPAM の割り当ては、次のプロセスに従います。

```mermaid
flowchart TD
    START[Pod Creation Request] --> CHECK{Node has<br/>affine block<br/>with free IPs?}
    CHECK -->|Yes| ALLOC1[Allocate from<br/>affine block]
    CHECK -->|No| CHECK2{Free blocks<br/>in pool?}
    CHECK2 -->|Yes| CLAIM[Claim new block<br/>for node]
    CLAIM --> ALLOC2[Allocate from<br/>new block]
    CHECK2 -->|No| CHECK3{Blocks with<br/>free IPs on<br/>other nodes?}
    CHECK3 -->|Yes| BORROW[Borrow IP from<br/>non-affine block]
    CHECK3 -->|No| FAIL[Allocation Failed<br/>IP Exhaustion]

    ALLOC1 --> SUCCESS[IP Assigned]
    ALLOC2 --> SUCCESS
    BORROW --> SUCCESS

    style START fill:#4fc3f7
    style SUCCESS fill:#81c784
    style FAIL fill:#ef5350
```

### ブロックサイズの設定

デフォルトのブロックサイズは /26（64 IP）です。クラスターの特性に応じて調整してください。

```yaml
# IPPool with custom block size
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26  # Default: /26 (64 IPs per block)
  # Options:
  # /24 = 256 IPs (large pods per node)
  # /26 = 64 IPs (default, balanced)
  # /28 = 16 IPs (many nodes, few pods each)
  # /29 = 8 IPs (minimum recommended)
  # /30 = 4 IPs (not recommended)
  ipipMode: CrossSubnet
  vxlanMode: Never
  natOutgoing: true
  nodeSelector: all()
```

**ブロックサイズ選択のガイドライン:**

| ブロックサイズ | ブロックあたりの IP 数 | 推奨シナリオ |
|------------|---------------|---------------------|
| /24 | 256 | 高い Pod 密度（50+ Pods/node） |
| /25 | 128 | 中～高密度 |
| /26 | 64 | デフォルト、バランス型 |
| /27 | 32 | 多数のノード、中程度の Pod 数 |
| /28 | 16 | 大規模クラスター、低密度 |
| /29 | 8 | 非常に大規模なクラスター、最小限の Pod 数 |

### Host-Local IPAM

よりシンプルなデプロイメントや特定のユースケース向けに、Calico は host-local IPAM モードをサポートしています。

```yaml
# Installation with host-local IPAM
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLANCrossSubnet
        natOutgoing: Enabled
    # Use host-local IPAM instead of Calico IPAM
    hostLocalIPAMEnabled: true
```

**Calico IPAM と Host-Local IPAM の比較:**

| 機能 | Calico IPAM | Host-Local IPAM |
|---------|-------------|-----------------|
| IP の再利用 | クラスター全体 | ノードローカル |
| ブロック管理 | 動的 | 静的 |
| ルート集約 | あり | 制限あり |
| IP の解放 | 即時 | 遅延 |
| 複雑さ | 高い | 低い |
| スケーラビリティ | 優れている | 制限あり |

### マルチプール戦略

異なるワークロード種別に対して複数の IP プールを構成します。

```yaml
# Production workloads pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: production-pool
spec:
  cidr: 10.244.0.0/18
  blockSize: 26
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "node-type == 'production'"
---
# Development workloads pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: development-pool
spec:
  cidr: 10.244.64.0/18
  blockSize: 28  # Smaller blocks for dev
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "node-type == 'development'"
---
# High-performance pool (no encapsulation)
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: highperf-pool
spec:
  cidr: 10.244.128.0/18
  blockSize: 26
  ipipMode: Never
  vxlanMode: Never
  natOutgoing: false
  nodeSelector: "network == 'direct'"
```

**Pod を特定のプールへ割り当てる:**

```yaml
# Pod annotation to select IP pool
apiVersion: v1
kind: Pod
metadata:
  name: production-app
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
spec:
  containers:
    - name: app
      image: nginx
---
# Namespace-level pool assignment
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
```

### IPv6 およびデュアルスタックの設定

Calico は IPv6 専用およびデュアルスタックのデプロイメントをサポートしています。

```yaml
# Dual-stack IPPool configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: all()
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv6-pool
spec:
  cidr: fd00:10:244::/48
  blockSize: 122  # /122 = 64 IPv6 addresses
  ipipMode: Never  # IPIP not supported for IPv6
  vxlanMode: CrossSubnet
  natOutgoing: true
  nodeSelector: all()
```

```yaml
# FelixConfiguration for dual-stack
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  ipv6Support: true
  # IPv6 auto-detection
  ipAutoDetectionMethod: "kubernetes-internal-ip"
  ip6AutoDetectionMethod: "kubernetes-internal-ip"
```

### IP 枯渇への対策

IP アドレスが不足してきた場合は、次の戦略を実装します。

```yaml
# 1. Enable strict block affinity release
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Release unused blocks faster
  ipamAutoGC: true
  # Garbage collection interval
  # ipamAutoGCInterval: "5m"
---
# 2. Configure node-specific IP limits
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: limited-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  # Limit blocks per node
  allowedUses:
    - Workload
  # Disable tunnel addresses from this pool
  disableBGPExport: false
```

```bash
# Monitor IP usage
calicoctl ipam show

# Show detailed block allocation
calicoctl ipam show --show-blocks

# Check for leaked IPs
calicoctl ipam check

# Release orphaned IPs
calicoctl ipam release --ip=10.244.1.5

# Show IP usage per node
calicoctl ipam show --show-blocks | grep -E "Node|Block"
```

## BlockAffinity によるノードごとの PodCIDR の照会

Calico のブロックベース IPAM では、各ノードに割り当てられた CIDR ブロックは **BlockAffinity CR** を通じて追跡されます。これらの CR は、静的ルートの設定または IPAM のデバッグのためにノードごとの Pod CIDR を識別する際に使用されます。

> **⚠ EKS Hybrid Nodes の注記**: Calico は EKS Hybrid Nodes では**公式にサポートされなくなりました**。新規デプロイメントには [Cilium](../cilium/04-ipam-policy.md) を使用してください。以下の情報は、既存の Calico 環境における参照用として提供されています。

### BlockAffinity CR の照会

```bash
# Query IPAM blocks using calicoctl
calicoctl ipam show --show-blocks

# Check per-node CIDRs via BlockAffinity CRs
kubectl get blockaffinities

# Table format query
kubectl get blockaffinities -o custom-columns='\
NAME:.metadata.name,\
CIDR:.spec.cidr,\
NODE:.spec.node'
```

出力例:

```
NAME                                    CIDR               NODE
hybrid-node-001-10-85-0-0-25            10.85.0.0/25       hybrid-node-001
hybrid-node-002-10-85-0-128-25          10.85.0.128/25     hybrid-node-002
hybrid-node-003-10-85-1-0-25            10.85.1.0/25       hybrid-node-003
```

### IPPool 全体の確認

```bash
kubectl get ippools -o custom-columns='\
NAME:.metadata.name,\
CIDR:.spec.cidr,\
BLOCK_SIZE:.spec.blockSize'
```

### 静的ルートの自動生成

BlockAffinity から静的ルートコマンドを生成する例:

```bash
# Generate ip route commands from BlockAffinity
kubectl get blockaffinities -o json | jq -r \
  '.items[] | "ip route add \(.spec.cidr) via <NODE_IP_FOR_\(.spec.node)>"'
```

> **ユースケース**: この情報は、EKS Hybrid Nodes 環境で BGP なしの静的ルートを設定するために使用されます。詳細は、[EKS Hybrid Nodes - Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md) を参照してください。

## WireGuard 暗号化

WireGuard は、ノード間の Pod 間トラフィックに対して効率的な暗号化を提供します。

### WireGuard アーキテクチャ

```mermaid
graph TB
    subgraph "Node 1"
        P1[Pod A<br/>10.244.0.5]
        WG1[WireGuard Interface<br/>wireguard.cali]
        ETH1[eth0<br/>192.168.1.10]
    end

    subgraph "Node 2"
        P2[Pod B<br/>10.244.1.10]
        WG2[WireGuard Interface<br/>wireguard.cali]
        ETH2[eth0<br/>192.168.1.11]
    end

    P1 -->|Plain| WG1
    WG1 -->|Encrypted| ETH1
    ETH1 <-->|WireGuard Tunnel<br/>UDP 51820| ETH2
    ETH2 -->|Encrypted| WG2
    WG2 -->|Plain| P2

    style WG1 fill:#81c784
    style WG2 fill:#81c784
```

### 設定

```yaml
# Enable WireGuard encryption
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Enable WireGuard for IPv4
  wireguardEnabled: true

  # Enable WireGuard for IPv6 (if using dual-stack)
  wireguardEnabledV6: true

  # WireGuard interface MTU (default: auto)
  wireguardMTU: 1440

  # WireGuard listen port
  wireguardListeningPort: 51820

  # Keep-alive interval for NAT traversal
  wireguardPersistentKeepAlive: "25s"

  # Host encryption (encrypt host-networked pod traffic)
  wireguardHostEncryptionEnabled: true
```

```yaml
# Operator-based installation with WireGuard
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: WireguardCrossSubnet
        natOutgoing: Enabled
```

### WireGuard のステータスを確認する

```bash
# Check WireGuard status on nodes
kubectl exec -n calico-system -it $(kubectl get pods -n calico-system -l k8s-app=calico-node -o name | head -1) -- wg show

# Sample output:
# interface: wireguard.cali
#   public key: ABC123...
#   private key: (hidden)
#   listening port: 51820
#
# peer: DEF456...
#   endpoint: 192.168.1.11:51820
#   allowed ips: 10.244.1.0/26
#   latest handshake: 5 seconds ago
#   transfer: 1.5 MiB received, 2.3 MiB sent

# Check Felix WireGuard statistics
calicoctl node status

# View WireGuard public keys
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}: {.metadata.annotations.projectcalico\.org/WireguardPublicKey}{"\n"}{end}'
```

### パフォーマンスへの影響

| 指標 | 暗号化なし | WireGuard | IPsec (AES-GCM) |
|--------|-------------------|-----------|-----------------|
| スループット | ベースライン | -5 to -10% | -15 to -25% |
| レイテンシ | ベースライン | +0.1-0.3ms | +0.5-1.0ms |
| CPU 使用率 | ベースライン | +10-15% | +30-50% |
| セットアップの複雑さ | N/A | 低い | 中程度 |
| キー管理 | N/A | 自動 | 手動/IKE |

### WireGuard と IPsec の比較

```mermaid
graph LR
    subgraph "WireGuard"
        WG1[Modern Crypto<br/>ChaCha20-Poly1305]
        WG2[Simple Code<br/>~4000 lines]
        WG3[Fast Key Exchange<br/>Noise Protocol]
        WG4[Low Overhead<br/>~60 bytes]
    end

    subgraph "IPsec"
        IP1[Traditional Crypto<br/>AES-GCM, 3DES]
        IP2[Complex Code<br/>~100K+ lines]
        IP3[IKE Key Exchange<br/>IKEv1/v2]
        IP4[Higher Overhead<br/>~80-100 bytes]
    end

    style WG1 fill:#81c784
    style WG2 fill:#81c784
    style WG3 fill:#81c784
    style WG4 fill:#81c784
    style IP1 fill:#ffb74d
    style IP2 fill:#ffb74d
    style IP3 fill:#ffb74d
    style IP4 fill:#ffb74d
```

| 機能 | WireGuard | IPsec |
|---------|-----------|-------|
| 暗号方式 | ChaCha20-Poly1305, Curve25519 | AES-GCM, SHA-256, DH |
| コードの複雑さ | ~4,000 行 | 100,000+ 行 |
| 攻撃対象領域 | 最小限 | 大きい |
| キーローテーション | 自動 | 手動または IKE |
| NAT トラバーサル | 組み込み | NAT-T が必要 |
| ローミング | シームレス | セッションの再確立 |
| カーネルサポート | 5.6+ (mainline) | 全バージョン |
| ハードウェアオフロード | 制限あり | 広くサポート |

## Egress Gateway

Egress Gateway は、特定の送信元 IP を必要とする Pod に対して、制御可能で予測可能なエグレスを提供します。

### アーキテクチャ

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Namespace: production"
            POD1[Pod A]
            POD2[Pod B]
        end

        subgraph "Egress Gateway Nodes"
            EG1[Egress Gateway 1<br/>External IP: 203.0.113.10]
            EG2[Egress Gateway 2<br/>External IP: 203.0.113.11]
        end
    end

    subgraph "External Services"
        EXT1[Partner API<br/>Firewall: Allow 203.0.113.10-11]
        EXT2[Database<br/>ACL: 203.0.113.0/24]
    end

    POD1 --> EG1
    POD2 --> EG2
    EG1 -->|SNAT| EXT1
    EG2 -->|SNAT| EXT2

    style EG1 fill:#ff9800
    style EG2 fill:#ff9800
```

### 設定

```yaml
# 1. Label egress gateway nodes
# kubectl label node egress-node-1 egress-gateway=true
# kubectl label node egress-node-2 egress-gateway=true

# 2. Create Egress Gateway IP Pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: egress-gateway-pool
spec:
  cidr: 203.0.113.0/28
  blockSize: 32
  nodeSelector: "!all()"  # Don't auto-assign
  allowedUses:
    - Workload
  natOutgoing: false
---
# 3. Create Egress Gateway deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: egress-gateway
  namespace: calico-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: egress-gateway
  template:
    metadata:
      labels:
        app: egress-gateway
      annotations:
        cni.projectcalico.org/ipv4pools: '["egress-gateway-pool"]'
    spec:
      nodeSelector:
        egress-gateway: "true"
      tolerations:
        - key: "egress-gateway"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      containers:
        - name: egress-gateway
          image: calico/egress-gateway:v3.29.0
          env:
            - name: EGRESS_POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
# 4. Configure egress gateway selector
apiVersion: projectcalico.org/v3
kind: EgressGateway
metadata:
  name: production-egress
  namespace: production
spec:
  # Select egress gateway pods
  selector: app == 'egress-gateway'
  # Maximum gateways per client (for HA)
  maxGatewaysPerClient: 2
```

### SNAT ポリシーの設定

```yaml
# Egress IP policy for specific namespaces
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceExternalIPs:
    - cidr: 203.0.113.0/28
---
# Network policy to route through egress gateway
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: use-egress-gateway
  namespace: production
spec:
  selector: requires-egress == 'true'
  egress:
    - action: Allow
      destination:
        notNets:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16
      # Route through egress gateway
```

### コンプライアンスのユースケース

コンプライアンス要件（PCI-DSS、HIPAA）がある組織では、予測可能なエグレス IP が必要となることがよくあります。

```yaml
# Compliance-focused egress configuration
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: compliance-egress
spec:
  selector: "compliance-level in {'pci', 'hipaa'}"
  order: 100
  egress:
    # Allow only through egress gateway
    - action: Allow
      destination:
        selector: app == 'egress-gateway'
    # Block direct external access
    - action: Deny
      destination:
        notNets:
          - 10.0.0.0/8
```

## マルチクラスター・フェデレーション

Calico は、クラスター間通信とポリシーのためのマルチクラスター・デプロイメントをサポートしています。

### フェデレーションのアーキテクチャ

```mermaid
graph TB
    subgraph "Cluster A (us-east-1)"
        CA_API[API Server]
        CA_TYPHA[Typha]
        CA_FELIX[Felix Agents]
        CA_PODS[Workloads<br/>10.244.0.0/16]
    end

    subgraph "Cluster B (us-west-2)"
        CB_API[API Server]
        CB_TYPHA[Typha]
        CB_FELIX[Felix Agents]
        CB_PODS[Workloads<br/>10.245.0.0/16]
    end

    subgraph "Cluster C (eu-west-1)"
        CC_API[API Server]
        CC_TYPHA[Typha]
        CC_FELIX[Felix Agents]
        CC_PODS[Workloads<br/>10.246.0.0/16]
    end

    subgraph "Federation Layer"
        FED[Federation Controller]
        SYNC[Policy Sync]
    end

    CA_API <--> FED
    CB_API <--> FED
    CC_API <--> FED
    FED --> SYNC

    CA_PODS <-->|BGP/Overlay| CB_PODS
    CB_PODS <-->|BGP/Overlay| CC_PODS
    CA_PODS <-->|BGP/Overlay| CC_PODS

    style FED fill:#ff9800
    style SYNC fill:#ffb74d
```

### クラスター間接続のセットアップ

```yaml
# Cluster A configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: cluster-a-pool
spec:
  cidr: 10.244.0.0/16
  ipipMode: CrossSubnet
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false
---
# BGP peer to Cluster B
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: cluster-b-peer
spec:
  peerIP: 192.168.2.1  # Cluster B border router
  asNumber: 64513
  password:
    secretKeyRef:
      name: bgp-secrets
      key: cluster-b-password
```

```yaml
# Cluster B configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: cluster-b-pool
spec:
  cidr: 10.245.0.0/16
  ipipMode: CrossSubnet
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64513
  nodeToNodeMeshEnabled: false
---
# BGP peer to Cluster A
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: cluster-a-peer
spec:
  peerIP: 192.168.1.1  # Cluster A border router
  asNumber: 64512
  password:
    secretKeyRef:
      name: bgp-secrets
      key: cluster-a-password
```

### クラスター間 Network Policy

```yaml
# Global policy that applies across clusters
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: cross-cluster-allow
spec:
  selector: all()
  order: 500
  ingress:
    # Allow from other clusters' pod CIDRs
    - action: Allow
      source:
        nets:
          - 10.244.0.0/16  # Cluster A
          - 10.245.0.0/16  # Cluster B
          - 10.246.0.0/16  # Cluster C
      protocol: TCP
      destination:
        ports:
          - 80
          - 443
          - 8080
  egress:
    - action: Allow
      destination:
        nets:
          - 10.244.0.0/16
          - 10.245.0.0/16
          - 10.246.0.0/16
```

## Windows コンテナのサポート

Calico は Kubernetes の Windows コンテナ向けにネットワーキングとポリシーを提供します。

### 機能と制限

| 機能 | Linux | Windows |
|---------|-------|---------|
| Overlay (VXLAN) | あり | あり |
| ダイレクトルーティング | あり | 制限あり |
| BGP | あり | あり |
| Network Policy L3-L4 | あり | あり |
| Network Policy L7 | あり | なし |
| eBPF Dataplane | あり | なし |
| WireGuard | あり | なし |
| IPsec | あり | あり |
| Host Endpoint Policy | あり | 制限あり |
| IPAM | フル | フル |

### Windows のインストール

```yaml
# Installation resource for Windows support
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  # Kubernetes provider
  kubernetesProvider: AKS  # or EKS, GKE, etc.

  # Windows dataplane
  windowsDataplane: HNS

  calicoNetwork:
    bgp: Enabled
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLAN
        natOutgoing: Enabled

    # Windows-specific settings
    windowsIPAM: Calico
```

### HNS (Host Networking Service) 統合

```mermaid
graph TB
    subgraph "Windows Node"
        subgraph "Windows Container"
            APP[Application]
            VNIC[Virtual NIC]
        end

        HNS[Host Networking Service<br/>HNS]
        VSWITCH[Hyper-V Virtual Switch]
        CALICO[Calico Windows Agent]

        subgraph "Policy Engine"
            VFP[Virtual Filtering Platform]
            ACL[ACL Rules]
        end

        NIC[Physical NIC]
    end

    APP --> VNIC
    VNIC --> VSWITCH
    VSWITCH --> HNS
    HNS --> VFP
    VFP --> ACL
    CALICO --> HNS
    CALICO --> VFP
    VSWITCH --> NIC

    style HNS fill:#4fc3f7
    style CALICO fill:#81c784
    style VFP fill:#ffb74d
```

### Windows Network Policy

```yaml
# Network policy for Windows workloads
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: windows-web-policy
  namespace: windows-apps
spec:
  selector: app == 'iis-web'
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'load-balancer'
      destination:
        ports:
          - 80
          - 443
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'sql-server'
        ports:
          - 1433
```

### ハイブリッド Linux/Windows クラスター

```yaml
# Separate IP pools for Linux and Windows
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: linux-pool
spec:
  cidr: 10.244.0.0/17
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "kubernetes.io/os == 'linux'"
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: windows-pool
spec:
  cidr: 10.244.128.0/17
  vxlanMode: Always  # Windows requires VXLAN
  natOutgoing: true
  nodeSelector: "kubernetes.io/os == 'windows'"
```

## Calico Enterprise / Tigera

Tigera は、エンタープライズ向けデプロイメントの追加機能を備えた Calico Enterprise を提供しています。

### OSS と Enterprise の比較

| 機能 | Calico OSS | Calico Enterprise |
|---------|-----------|-------------------|
| **ネットワーキング** | | |
| CNI Plugin | あり | あり |
| BGP Routing | あり | あり |
| VXLAN/IPIP Overlay | あり | あり |
| eBPF Dataplane | あり | あり |
| WireGuard Encryption | あり | あり |
| Egress Gateway | 基本 | 高度 |
| **Network Policy** | | |
| Kubernetes NetworkPolicy | あり | あり |
| Calico NetworkPolicy | あり | あり |
| GlobalNetworkPolicy | あり | あり |
| Policy Tiers | あり | あり |
| DNS Policy | あり | あり |
| L7 Policy (HTTP) | 基本 | フル |
| Policy Preview | なし | あり |
| Policy Recommendations | なし | あり |
| **セキュリティ** | | |
| Threat Detection | なし | あり |
| Anomaly Detection | なし | あり |
| Compliance Reports | なし | あり |
| Security Alerts | なし | あり |
| Workload Identity | 基本 | SPIFFE/SPIRE |
| **可観測性** | | |
| Flow Logs | 基本 | フル |
| Service Graph | なし | あり |
| Kibana Dashboards | なし | あり |
| DNS Logs | 基本 | フル |
| L7 Logs | なし | あり |
| **運用** | | |
| Web UI | なし | あり |
| Multi-Cluster Management | 手動 | 統合 |
| RBAC | Kubernetes | 拡張 |
| Audit Logs | 基本 | フル |
| **サポート** | | |
| Community Support | あり | あり |
| Enterprise Support | なし | 24/7 SLA |
| Professional Services | なし | あり |

### Calico Cloud

Calico Cloud は、以下を提供する SaaS オファリングです。

```mermaid
graph TB
    subgraph "Calico Cloud (SaaS)"
        UI[Management UI]
        ANALYTICS[Analytics Engine]
        THREAT[Threat Intelligence]
        COMPLY[Compliance Engine]
    end

    subgraph "Customer Cluster 1"
        AGENT1[Calico Agent]
        PODS1[Workloads]
    end

    subgraph "Customer Cluster 2"
        AGENT2[Calico Agent]
        PODS2[Workloads]
    end

    subgraph "Customer Cluster 3"
        AGENT3[Calico Agent]
        PODS3[Workloads]
    end

    AGENT1 <--> UI
    AGENT2 <--> UI
    AGENT3 <--> UI

    UI --> ANALYTICS
    ANALYTICS --> THREAT
    ANALYTICS --> COMPLY

    style UI fill:#4fc3f7
    style ANALYTICS fill:#81c784
    style THREAT fill:#ef5350
    style COMPLY fill:#ffb74d
```

## 大規模クラスター設計（1000+ ノード）

大規模クラスター向けに Calico を設計するには、コンポーネントとリソースを慎重に計画する必要があります。

### Typha のサイジング式

Typha はデータストア接続を集約することで API Server の負荷を軽減します。

```
Typha Replicas = max(3, ceil(Node Count / 200))

Examples:
- 100 nodes: 3 Typha replicas (minimum)
- 500 nodes: 3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
- 5000 nodes: 25 Typha replicas
```

```yaml
# Large cluster Typha configuration
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  typhaDeployment:
    spec:
      replicas: 10  # For ~2000 nodes
      template:
        spec:
          containers:
            - name: calico-typha
              resources:
                requests:
                  cpu: 500m
                  memory: 512Mi
                limits:
                  cpu: 2000m
                  memory: 1Gi
          affinity:
            podAntiAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                - labelSelector:
                    matchLabels:
                      k8s-app: calico-typha
                  topologyKey: kubernetes.io/hostname
          topologySpreadConstraints:
            - maxSkew: 1
              topologyKey: topology.kubernetes.io/zone
              whenUnsatisfiable: DoNotSchedule
              labelSelector:
                matchLabels:
                  k8s-app: calico-typha
```

### Route Reflector トポロジー

大規模な BGP デプロイメントでは、フルメッシュの代わりに Route Reflector を使用します。

```mermaid
graph TB
    subgraph "Route Reflector Tier"
        RR1[RR 1<br/>Zone A]
        RR2[RR 2<br/>Zone B]
        RR3[RR 3<br/>Zone C]
    end

    subgraph "Zone A (300 nodes)"
        NA1[Node A1]
        NA2[Node A2]
        NAN[Node A...]
    end

    subgraph "Zone B (350 nodes)"
        NB1[Node B1]
        NB2[Node B2]
        NBN[Node B...]
    end

    subgraph "Zone C (350 nodes)"
        NC1[Node C1]
        NC2[Node C2]
        NCN[Node C...]
    end

    RR1 <--> RR2
    RR2 <--> RR3
    RR1 <--> RR3

    NA1 --> RR1
    NA2 --> RR1
    NAN --> RR1

    NB1 --> RR2
    NB2 --> RR2
    NBN --> RR2

    NC1 --> RR3
    NC2 --> RR3
    NCN --> RR3

    style RR1 fill:#ff9800
    style RR2 fill:#ff9800
    style RR3 fill:#ff9800
```

```yaml
# Route Reflector node configuration
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-1
  labels:
    route-reflector: "true"
    topology.kubernetes.io/zone: "zone-a"
spec:
  bgp:
    routeReflectorClusterID: 244.0.0.1
    ipv4Address: 192.168.1.10/24
---
# Regular nodes peer with zone-local RR
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: node-to-rr-zone-a
spec:
  nodeSelector: "topology.kubernetes.io/zone == 'zone-a' && !has(route-reflector)"
  peerSelector: "route-reflector == 'true' && topology.kubernetes.io/zone == 'zone-a'"
---
# RR mesh between zones
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rr-full-mesh
spec:
  nodeSelector: "has(route-reflector)"
  peerSelector: "has(route-reflector)"
```

### 大規模クラスター向け Felix チューニング

```yaml
# Optimized Felix configuration for large clusters
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Reduce datastore polling
  datastoreType: kubernetes

  # Increase refresh intervals (reduce API load)
  routeRefreshInterval: "90s"
  iptablesRefreshInterval: "180s"
  ipSetsRefreshInterval: "90s"

  # Optimize iptables
  iptablesBackend: NFT  # Use nftables if available
  iptablesMarkMask: 0xffff0000

  # Reduce logging overhead
  logSeverityScreen: Warning
  logSeverityFile: Warning

  # Flow logs (if enabled, optimize)
  flowLogsFlushInterval: "60s"
  flowLogsFileAggregationKindForAllowed: 2
  flowLogsFileAggregationKindForDenied: 1

  # Health check optimization
  healthEnabled: true
  healthPort: 9099
  healthTimeoutOverrides:
    - name: "InternalDataplaneMainLoop"
      timeout: "120s"

  # BPF mode optimization (if using eBPF)
  bpfEnabled: true
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: "DSR"
  bpfMapSizeConntrack: 512000
  bpfMapSizeNATFrontend: 65536
  bpfMapSizeNATBackend: 262144
  bpfMapSizeNATAffinity: 65536
```

### 大規模環境のデータストア

```yaml
# etcd optimization for large Calico deployments
# (if using etcd datastore instead of Kubernetes)
apiVersion: v1
kind: ConfigMap
metadata:
  name: etcd-config
  namespace: kube-system
data:
  etcd.conf.yaml: |
    name: etcd-0
    data-dir: /var/lib/etcd

    # Increase quota for large deployments
    quota-backend-bytes: 8589934592  # 8GB

    # Snapshot tuning
    snapshot-count: 50000
    auto-compaction-mode: periodic
    auto-compaction-retention: "1h"

    # Performance tuning
    heartbeat-interval: 250
    election-timeout: 2500

    # Enable gRPC gateway
    enable-grpc-gateway: true
```

## パフォーマンスチューニング

### Felix パラメータ

```yaml
# Comprehensive Felix performance tuning
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # === CPU Optimization ===
  # Use eBPF for better CPU efficiency
  bpfEnabled: true
  bpfDisableUnprivileged: true

  # Batch iptables updates
  iptablesPostWriteCheckIntervalSecs: 5
  iptablesLockFilePath: "/run/xtables.lock"
  iptablesLockTimeoutSecs: 30
  iptablesLockProbeIntervalMillis: 50

  # === Memory Optimization ===
  # Limit in-memory caches
  routeTableRanges:
    - min: 1
      max: 250

  # === Network Optimization ===
  # MTU configuration
  mtuIfacePattern: "^(en.*|eth.*|bond.*)"

  # Failsafe inbound/outbound ports
  failsafeInboundHostPorts:
    - protocol: tcp
      port: 22
    - protocol: udp
      port: 68
  failsafeOutboundHostPorts:
    - protocol: tcp
      port: 443
    - protocol: udp
      port: 53

  # === Logging Optimization ===
  logFilePath: "/var/log/calico/felix.log"
  logSeverityFile: Warning
  logSeverityScreen: Warning
  logSeveritySys: Warning

  # === Health Check Optimization ===
  healthEnabled: true
  healthPort: 9099
  healthHost: "0.0.0.0"
```

### Typha の比率と設定

```yaml
# Typha deployment for optimal performance
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 5  # Adjust based on cluster size
  selector:
    matchLabels:
      k8s-app: calico-typha
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      priorityClassName: system-cluster-critical
      tolerations:
        - key: CriticalAddonsOnly
          operator: Exists
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  k8s-app: calico-typha
              topologyKey: kubernetes.io/hostname
      containers:
        - name: calico-typha
          image: calico/typha:v3.29.0
          ports:
            - containerPort: 5473
              name: calico-typha
            - containerPort: 9093
              name: metrics
          env:
            - name: TYPHA_LOGSEVERITYSCREEN
              value: "warning"
            - name: TYPHA_DATASTORETYPE
              value: "kubernetes"
            # Max connections per Typha
            - name: TYPHA_MAXCONNECTIONSLOWERLIMIT
              value: "200"
            - name: TYPHA_MAXCONNECTIONSUPPERLIMIT
              value: "400"
            # Connection rebalancing
            - name: TYPHA_CONNECTIONREBALANCINGMODE
              value: "kubernetes"
            # Reduce sync interval
            - name: TYPHA_SNAPSHOTSYNCSINTERVAL
              value: "300s"
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /liveness
              port: 9098
            periodSeconds: 30
            initialDelaySeconds: 30
            failureThreshold: 5
          readinessProbe:
            httpGet:
              path: /readiness
              port: 9098
            periodSeconds: 10
            failureThreshold: 3
```

### リソース割り当てのガイドライン

| クラスター規模 | Felix CPU | Felix メモリ | Typha CPU | Typha メモリ | Typha レプリカ数 |
|--------------|-----------|--------------|-----------|--------------|----------------|
| < 50 ノード | 100m-250m | 128Mi-256Mi | N/A | N/A | 0 |
| 50-200 | 250m-500m | 256Mi-512Mi | 100m-250m | 128Mi-256Mi | 3 |
| 200-500 | 500m-1000m | 512Mi-1Gi | 250m-500m | 256Mi-512Mi | 3 |
| 500-1000 | 500m-1000m | 512Mi-1Gi | 500m-1000m | 512Mi-1Gi | 5 |
| 1000-2000 | 1000m-2000m | 1Gi-2Gi | 500m-1000m | 512Mi-1Gi | 10 |
| 2000+ | 1000m-2000m | 1Gi-2Gi | 1000m-2000m | 1Gi-2Gi | ノード数/200 |

---

## 参考資料

- [Calico IPAM ドキュメント](https://docs.tigera.io/calico/latest/networking/ipam/)
- [WireGuard 暗号化](https://docs.tigera.io/calico/latest/network-policy/encrypt-cluster-pod-traffic)
- [Egress Gateway](https://docs.tigera.io/calico/latest/networking/egress/egress-gateway/)
- [Windows コンテナ](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/)
- [Calico Enterprise](https://docs.tigera.io/calico-enterprise/)
- [パフォーマンスチューニング](https://docs.tigera.io/calico/latest/operations/monitor/component-performance)

## クイズ

この章で学んだ内容を確認するには、[高度なトピックのクイズ](../../quizzes/networking/calico/07-advanced-topics-quiz.md)に挑戦してください。
