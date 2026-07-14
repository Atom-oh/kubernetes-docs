# パート 4: BGP 詳細解説

> **サポート対象バージョン**: Calico v3.29+ / Kubernetes 1.28+ **最終更新**: February 23, 2026

## はじめに

Border Gateway Protocol (BGP) はインターネットを支えるルーティングプロトコルであり、Calico はこれを活用して Kubernetes クラスター向けに高いスケーラビリティと標準ベースのネットワーキングを提供します。トラフィックをカプセル化するオーバーレイネットワークとは異なり、Calico の BGP ベースのネットワーキングはネイティブ IP ルーティングを可能にし、優れたパフォーマンスと既存のネットワークインフラストラクチャとのシームレスな統合を実現します。

この詳細解説では、BGP の基本、Calico の BGP アーキテクチャオプション、設定リソース、およびエンタープライズ環境向けの高度なデプロイメントパターンについて説明します。

***

## BGP の基本

### BGP とは

BGP (Border Gateway Protocol) は、自律システム間でルーティング情報を交換するために設計されたパスベクタールーティングプロトコルです。Calico では、BGP が Pod IP ルートをクラスターの Node 間および必要に応じて外部ネットワークインフラストラクチャへ配布します。

### BGP の主要概念

| 概念                    | 説明                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| **自律システム (AS)** | 単一の管理ドメイン下にある IP ネットワークの集合     |
| **AS 番号 (ASN)**        | AS の一意の識別子 (16 ビット: 1-65534、32 ビット: 1-4294967294)  |
| **iBGP**                   | 内部 BGP - 同一 AS 内のルーター間セッション               |
| **eBGP**                   | 外部 BGP - 異なる AS 内のルーター間セッション            |
| **NLRI**                   | Network Layer Reachability Information - 広報されるルート |
| **BGP Speaker**            | BGP に参加するルーターまたはソフトウェア                        |

### プライベート AS 番号の範囲

組織内での内部利用のため、IANA は次のプライベート ASN 範囲を予約しています。

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico は通常、クラスター内部 BGP に `64512-65534` の範囲の ASN を使用します。

### BGP ルート選択プロセス

BGP Speaker が同じ宛先への複数のルートを受信すると、次の基準（順番どおり）で最適なルートを選択します。

```mermaid
flowchart TD
    A[Receive Multiple Routes] --> B{Highest Weight?}
    B -->|Tie| C{Highest LOCAL_PREF?}
    C -->|Tie| D{Locally Originated?}
    D -->|Tie| E{Shortest AS_PATH?}
    E -->|Tie| F{Lowest Origin Type?}
    F -->|Tie| G{Lowest MED?}
    G -->|Tie| H{eBGP over iBGP?}
    H -->|Tie| I{Lowest IGP Metric?}
    I -->|Tie| J{Oldest Route?}
    J -->|Tie| K{Lowest Router ID}
    K --> L[Select Best Route]
```

### iBGP と eBGP の動作

| 属性               | iBGP                               | eBGP                                   |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| AS\_PATH の変更   | 変更されない                       | ローカル AS を先頭に追加                      |
| Next-hop                | デフォルトでは変更されない             | ピアリングアドレスに変更される             |
| デフォルト TTL             | 255                                | 1（隣接していない場合は multihop が必要） |
| ルートの広報     | eBGP ピアにのみ送信（split-horizon） | すべてのピアへ送信                           |
| 管理距離 | 200                                | 20                                     |

***

## Calico BGP アーキテクチャ

![Calico BGP トポロジ](../../.gitbook/assets/calico_bgp_topology.png)

### BIRD: Calico の BGP 実装

Calico は BGP 実装として BIRD (BIRD Internet Routing Daemon) を使用します。BIRD はすべての Node 上で `calico-node` DaemonSet の一部として実行されます。

```mermaid
graph TB
    subgraph "Calico Node"
        FV[Felix] --> DT[Dataplane<br/>iptables/eBPF]
        BIRD[BIRD BGP] --> RT[Routing Table]
        CONFD[confd] --> BIRD
        API[Calico API] --> CONFD
    end

    BIRD <--> EXT[External Router]
    BIRD <--> OTHER[Other Calico Nodes]
```

### BGP トポロジオプション

Calico は主に 2 種類の BGP トポロジをサポートします。

1. **Node-to-Node Mesh (Full Mesh)** - デフォルト設定
2. **Route Reflectors** - より大規模なクラスターに推奨

***

## Full-Mesh トポロジ

### Full-Mesh の仕組み

デフォルトの Full-Mesh 設定では、すべての Calico Node がクラスター内の他のすべての Node と BGP ピアリングセッションを確立します。

```mermaid
graph TB
    subgraph "Full-Mesh BGP (5 Nodes)"
        N1[Node 1<br/>AS 64512] <--> N2[Node 2<br/>AS 64512]
        N1 <--> N3[Node 3<br/>AS 64512]
        N1 <--> N4[Node 4<br/>AS 64512]
        N1 <--> N5[Node 5<br/>AS 64512]
        N2 <--> N3
        N2 <--> N4
        N2 <--> N5
        N3 <--> N4
        N3 <--> N5
        N4 <--> N5
    end
```

### セッション数の計算式

Full-Mesh トポロジにおける BGP セッション数は二次的に増加します。

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### Full-Mesh のスケーリング上の制限

| クラスターサイズ  | BGP セッション | Node あたりのメモリ | CPU への影響 | 推奨事項 |
| ------------- | ------------ | --------------- | ---------- | -------------- |
| < 50 Node    | < 1,225      | \~50 MB         | 最小限    | Full-mesh で問題なし   |
| 50-100 Node  | 1,225-4,950  | \~100 MB        | 低        | RR を検討    |
| 100-200 Node | 4,950-19,900 | \~200 MB        | 中程度   | RR を使用         |
| > 200 Node   | > 19,900     | > 400 MB        | 高       | RR が必要     |

### Node-to-Node Mesh の有効化と無効化

現在のステータスを確認します。

```bash
calicoctl get bgpconfiguration default -o yaml
```

Node-to-Node Mesh を無効化します（Route Reflectors を使用する場合）。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

***

## Route Reflector トポロジ

### Route Reflector の概念

Route Reflectors (RR) は、一部の Node が他の Node にルートを反映できるようにすることで、iBGP のスケーラビリティ問題を解決します。これにより、Full-Mesh の必要がなくなります。

```mermaid
graph TB
    subgraph "Route Reflector Topology"
        subgraph "Route Reflectors"
            RR1[RR Node 1<br/>Cluster ID: 1.0.0.1]
            RR2[RR Node 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Client Nodes"
            C1[Client 1]
            C2[Client 2]
            C3[Client 3]
            C4[Client 4]
            C5[Client 5]
            C6[Client 6]
        end

        RR1 <--> RR2

        C1 --> RR1
        C2 --> RR1
        C3 --> RR1
        C1 --> RR2
        C2 --> RR2
        C3 --> RR2

        C4 --> RR1
        C5 --> RR1
        C6 --> RR1
        C4 --> RR2
        C5 --> RR2
        C6 --> RR2
    end
```

### Route Reflector の主要属性

| 属性            | 説明                                                   |
| -------------------- | ------------------------------------------------------------- |
| **Cluster ID**       | 同じクライアントにサービスを提供する RR のセットを識別する              |
| **Originator ID**    | ルーティングループを防止する（発信元の router ID に設定）   |
| **Route Reflection** | RR がクライアントから学習したルートを他のクライアントに再広報する |

### Route Reflectors 使用時のセッション数

2 台の Route Reflector と N 台のクライアント Node の場合:

```
Sessions = 2 × N + 1 (RR-to-RR peering)

Examples:
- 100 nodes: 2 × 100 + 1 = 201 sessions (vs 4,950 in full-mesh)
- 500 nodes: 2 × 500 + 1 = 1,001 sessions (vs 124,750 in full-mesh)
```

### Route Reflector Node の設定

**ステップ 1: Route Reflector として指定する Node にラベルを付与する**

```bash
kubectl label node rr-node-1 calico-route-reflector=true
kubectl label node rr-node-2 calico-route-reflector=true
```

**ステップ 2: Route Reflector の Cluster ID を設定する**

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-1
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    routeReflectorClusterID: 1.0.0.1
---
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-2
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.11/24
    routeReflectorClusterID: 1.0.0.1
```

**ステップ 3: Node-to-Node Mesh を無効化する**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

**ステップ 4: Route Reflectors への BGP ピアリングを設定する**

```yaml
# Peering from non-RR nodes to RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-route-reflectors
spec:
  nodeSelector: "!has(calico-route-reflector)"
  peerSelector: has(calico-route-reflector)
---
# Peering between RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: route-reflector-mesh
spec:
  nodeSelector: has(calico-route-reflector)
  peerSelector: has(calico-route-reflector)
```

### Route Reflector の冗長化パターン

**パターン 1: デュアル Route Reflector（小規模・中規模クラスター）**

```mermaid
graph TB
    subgraph "Availability Zone 1"
        RR1[Route Reflector 1]
        N1[Node 1]
        N2[Node 2]
        N3[Node 3]
    end

    subgraph "Availability Zone 2"
        RR2[Route Reflector 2]
        N4[Node 4]
        N5[Node 5]
        N6[Node 6]
    end

    RR1 <--> RR2
    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
```

**パターン 2: 階層型 Route Reflector（大規模クラスター）**

```mermaid
graph TB
    subgraph "Tier 1 - Global RRs"
        GRR1[Global RR 1]
        GRR2[Global RR 2]
    end

    subgraph "Tier 2 - Rack RRs"
        RRR1[Rack 1 RR]
        RRR2[Rack 2 RR]
        RRR3[Rack 3 RR]
    end

    subgraph "Rack 1 Nodes"
        R1N1[Node]
        R1N2[Node]
    end

    subgraph "Rack 2 Nodes"
        R2N1[Node]
        R2N2[Node]
    end

    subgraph "Rack 3 Nodes"
        R3N1[Node]
        R3N2[Node]
    end

    GRR1 <--> GRR2
    GRR1 <--> RRR1 & RRR2 & RRR3
    GRR2 <--> RRR1 & RRR2 & RRR3

    R1N1 & R1N2 --> RRR1
    R2N1 & R2N2 --> RRR2
    R3N1 & R3N2 --> RRR3
```

***

## BGPPeer リソース

`BGPPeer` リソースは、Calico Node と外部 BGP Speaker 間の BGP ピアリング関係を定義します。

### BGPPeer スコープタイプ

| タイプ              | 説明          | ユースケース                |
| ----------------- | -------------------- | ----------------------- |
| **グローバル**        | すべての Node に適用 | 外部ルーターピアリング |
| **Node 固有** | nodeSelector を使用    | Rack ローカルピアリング      |
| **Node ごと**      | 正確な Node を指定 | 特別な設定  |

### グローバル BGPPeer の例

すべての Node を外部 ToR スイッチとピアリングします。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-tor-switches
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  # No nodeSelector means all nodes peer with this address
```

### Node 固有の BGPPeer の例

特定の Rack 内の Node をローカル ToR スイッチとピアリングします。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-tor-peer
spec:
  nodeSelector: rack == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-tor-peer
spec:
  nodeSelector: rack == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002
```

### peerSelector を使用する BGPPeer

`peerSelector` を使用して、ピアとなる Calico Node を動的に選択します。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: client-to-rr-peering
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: has(route-reflector)
```

### 高度な BGPPeer 設定

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: advanced-peer
spec:
  node: specific-node-name
  peerIP: 192.168.1.1
  asNumber: 65100

  # Authentication
  password:
    secretKeyRef:
      name: bgp-secrets
      key: peer-password

  # Timers (seconds)
  keepAliveTime: 30
  holdTime: 90

  # Source address for BGP session
  sourceAddress: 10.0.0.5

  # Maximum number of hops for eBGP multihop
  numAllowedLocalASNumbers: 2

  # TTL security (GTSM)
  ttlSecurity: 1

  # Filters
  filters:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
```

***

## BGPConfiguration リソース

`BGPConfiguration` リソースはクラスター全体の BGP 設定を定義します。

### 基本的な BGPConfiguration

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  # Cluster AS number
  asNumber: 64512

  # Node-to-node mesh (disable for Route Reflectors)
  nodeToNodeMeshEnabled: false

  # Log level for BIRD
  logSeverityScreen: Info
```

### Service IP の広報

Calico は Kubernetes Service IP を BGP 経由で広報でき、外部クライアントが Service に直接到達できるようにします。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

  # Advertise Service ClusterIPs
  serviceClusterIPs:
    - cidr: 10.96.0.0/12

  # Advertise Service ExternalIPs
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

  # Advertise Service LoadBalancerIPs
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24
```

### BGP Community の設定

BGP Community を使用すると、外部ルーター上のポリシーベースルーティング用にルートへタグを付けられます。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Community tagging for pod networks
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"  # Standard community
        - "64512:200"
    - cidr: 10.96.0.0/12
      communities:
        - "64512:300"  # Service IPs community

  # Named communities (referenced in other configs)
  communities:
    - name: pod-networks
      value: "64512:100"
    - name: service-networks
      value: "64512:300"
    - name: no-export
      value: "65535:65281"  # Well-known NO_EXPORT
```

### Node 固有の AS 番号

複雑なトポロジでは、Node ごとに異なる AS 番号を割り当てることができます。

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: border-node-1
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    asNumber: 65001  # Override cluster default
```

***

## Service IP の広報

### 広報タイプ

| タイプ               | 説明               | ユースケース                |
| ------------------ | ------------------------- | ----------------------- |
| **ClusterIP**      | 内部 Service IP       | 内部ロードバランシング |
| **ExternalIP**     | ユーザー割り当ての外部 IP | 外部からの直接アクセス  |
| **LoadBalancerIP** | クラウドプロバイダーが割り当て   | クラウド統合       |

### ExternalIP 広報の例

```yaml
# BGPConfiguration for ExternalIP advertisement
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

---
# Service with ExternalIP
apiVersion: v1
kind: Service
metadata:
  name: my-external-service
spec:
  type: ClusterIP
  externalIPs:
    - 203.0.113.10
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

### LoadBalancer IP の広報

クラウドプロバイダー統合のないベアメタルクラスターの場合:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24

---
apiVersion: v1
kind: Service
metadata:
  name: my-lb-service
  annotations:
    metallb.universe.tf/loadBalancerIPs: 198.51.100.50
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - port: 443
      targetPort: 8443
```

### 選択的な Service 広報

アノテーションを使用して、広報する Service を制御します。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: internal-only-service
  annotations:
    # Prevent BGP advertisement
    projectcalico.org/bgp-advertise: "false"
spec:
  type: LoadBalancer
  ...
```

***

## 物理ネットワークとの統合

### ToR スイッチ設定例

**Cisco NX-OS 設定:**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer with Kubernetes nodes in rack
  neighbor 10.0.1.0/24 remote-as 64512

  address-family ipv4 unicast
    ! Accept pod network routes
    network 10.244.0.0/16
    ! Redistribute connected for node networks
    redistribute connected route-map KUBERNETES-NODES

    ! Route map for prefix filtering
    neighbor 10.0.1.0/24 route-map ACCEPT-K8S-ROUTES in
    neighbor 10.0.1.0/24 route-map DENY-ALL out

! Route map definitions
route-map ACCEPT-K8S-ROUTES permit 10
  match ip address prefix-list K8S-POD-NETS

ip prefix-list K8S-POD-NETS seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-POD-NETS seq 20 permit 10.96.0.0/12 le 32
```

**Arista EOS 設定:**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer group for Kubernetes nodes
  neighbor K8S-NODES peer group
  neighbor K8S-NODES remote-as 64512
  neighbor K8S-NODES maximum-routes 10000
  neighbor K8S-NODES password 7 <encrypted>

  ! Dynamic neighbors from subnet
  bgp listen range 10.0.1.0/24 peer-group K8S-NODES

  address-family ipv4
    neighbor K8S-NODES activate
    neighbor K8S-NODES prefix-list K8S-PODS-IN in
    neighbor K8S-NODES prefix-list DENY-ALL out

! Prefix lists
ip prefix-list K8S-PODS-IN seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-PODS-IN seq 20 permit 10.96.0.0/12 le 32
ip prefix-list DENY-ALL seq 10 deny 0.0.0.0/0 le 32
```

**Juniper Junos 設定:**

```
protocols {
    bgp {
        group K8S-NODES {
            type external;
            peer-as 64512;
            local-as 65001;

            multipath multiple-as;

            import K8S-IMPORT;
            export DENY-ALL;

            allow 10.0.1.0/24;

            authentication-key "$9$encrypted";
        }
    }
}

policy-options {
    prefix-list K8S-POD-NETS {
        10.244.0.0/16;
    }
    prefix-list K8S-SVC-NETS {
        10.96.0.0/12;
    }
    policy-statement K8S-IMPORT {
        term accept-pods {
            from {
                prefix-list K8S-POD-NETS;
                prefix-length-range /26-/26;
            }
            then accept;
        }
        term accept-services {
            from {
                prefix-list K8S-SVC-NETS;
            }
            then accept;
        }
        term reject-all {
            then reject;
        }
    }
    policy-statement DENY-ALL {
        then reject;
    }
}
```

### Spine-Leaf アーキテクチャとの統合

```mermaid
graph TB
    subgraph "Spine Layer (AS 65000)"
        S1[Spine 1<br/>10.0.0.1]
        S2[Spine 2<br/>10.0.0.2]
    end

    subgraph "Leaf Layer"
        subgraph "Rack 1 (AS 65001)"
            L1[Leaf 1<br/>10.0.1.1]
            K1[K8s Node 1<br/>AS 64512]
            K2[K8s Node 2<br/>AS 64512]
        end

        subgraph "Rack 2 (AS 65002)"
            L2[Leaf 2<br/>10.0.2.1]
            K3[K8s Node 3<br/>AS 64512]
            K4[K8s Node 4<br/>AS 64512]
        end

        subgraph "Rack 3 (AS 65003)"
            L3[Leaf 3<br/>10.0.3.1]
            K5[K8s Node 5<br/>AS 64512]
            K6[K8s Node 6<br/>AS 64512]
        end
    end

    S1 <--> L1 & L2 & L3
    S2 <--> L1 & L2 & L3

    K1 & K2 --> L1
    K3 & K4 --> L2
    K5 & K6 --> L3
```

Spine-Leaf 向けの Calico 設定:

```yaml
# Disable node-to-node mesh
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512

---
# Peer nodes with their local leaf switch
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack3-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack3'
  peerIP: 10.0.3.1
  asNumber: 65003
```

***

## BGP Community タギング戦略

### Community 設計パターン

| Community     | 意味        | アクション                           |
| ------------- | -------------- | -------------------------------- |
| `64512:100`   | Pod ネットワーク   | 受け入れ、通常のルーティング           |
| `64512:200`   | Service IP    | 受け入れ、特別なポリシーを適用する場合がある |
| `64512:300`   | インフラストラクチャ | より高い優先度のルーティング          |
| `65535:65281` | NO\_EXPORT     | AS 外部へ広報しない      |
| `65535:65282` | NO\_ADVERTISE  | いかなるピアへも広報しない     |

### Community ベースのトラフィックエンジニアリング

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  communities:
    - name: production
      value: "64512:100"
    - name: staging
      value: "64512:200"
    - name: local-only
      value: "65535:65281"  # NO_EXPORT

  prefixAdvertisements:
    # Production pod networks - advertise everywhere
    - cidr: 10.244.0.0/17
      communities:
        - production

    # Staging pod networks - keep local
    - cidr: 10.244.128.0/17
      communities:
        - staging
        - local-only

    # Service IPs
    - cidr: 10.96.0.0/12
      communities:
        - production
```

***

## BGP セキュリティ

### MD5 認証

MD5 認証で BGP セッションを保護します。

```yaml
# Create secret for BGP password
apiVersion: v1
kind: Secret
metadata:
  name: bgp-auth
  namespace: kube-system
type: Opaque
stringData:
  bgp-password: "SuperSecretPassword123!"

---
# Reference in BGPPeer
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: secure-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  password:
    secretKeyRef:
      name: bgp-auth
      key: bgp-password
```

### Prefix フィルタリング

受け入れる／広報する Prefix を制限します。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPFilter
metadata:
  name: allow-pod-nets-only
spec:
  exportV4:
    - action: Accept
      matchOperator: In
      cidr: 10.244.0.0/16
      prefixLength: "24-28"
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

  importV4:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: filtered-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  filters:
    - allow-pod-nets-only
```

### GTSM (TTL Security)

Generalized TTL Security Mechanism は、スプーフィングされた BGP パケットを防止します。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: gtsm-enabled-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  ttlSecurity: 1  # Expect TTL of 254 or higher
```

***

## パフォーマンスチューニング

### BGP タイマー設定

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tuned-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001

  # Keepalive interval (default: 60s)
  keepAliveTime: 20

  # Hold time (default: 180s, must be 3x keepalive)
  holdTime: 60
```

### ルート集約

Pod CIDR を集約して、広報するルート数を減らします。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Aggregate individual /26 pod CIDRs into /16
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"
```

### Graceful Restart

BIRD の再起動中のトラフィック中断を最小限に抑えるため、BGP Graceful Restart を有効にします。

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Enable graceful restart (BIRD default is enabled)
  # Stale route time in seconds
  nodeMeshMaxRestartTime: 120
```

***

## BGP のデバッグ

### birdcl コマンド

calico-node Pod から BIRD コマンドラインインターフェースにアクセスします。

```bash
# Enter calico-node pod
kubectl exec -it -n kube-system calico-node-xxxxx -c calico-node -- /bin/sh

# Show BGP protocol status
birdcl -s /var/run/calico/bird.ctl show protocols all

# Show BGP neighbors
birdcl -s /var/run/calico/bird.ctl show protocols all bgp*

# Show routing table
birdcl -s /var/run/calico/bird.ctl show route

# Show routes to specific prefix
birdcl -s /var/run/calico/bird.ctl show route for 10.244.1.0/24

# Show route export to specific peer
birdcl -s /var/run/calico/bird.ctl show route export Mesh_10_0_1_11

# Show BGP neighbor details
birdcl -s /var/run/calico/bird.ctl show protocols all Mesh_10_0_1_11
```

### よくある BGP の問題と解決策

| 問題                    | 症状                      | 解決策                              |
| ------------------------ | ----------------------------- | ------------------------------------- |
| セッションが Active のまま | ルートを学習しない             | ファイアウォール（TCP 179）、AS 番号を確認  |
| ルートが伝播しない   | Rack をまたいで Pod に到達できない | Node-to-Node Mesh または RR 設定を検証 |
| ルートフラッピング           | 断続的な接続性     | BGP タイマー、ネットワーク安定性を確認   |
| セッションリセット           | Established->Active が頻発  | MTU、MD5 パスワードを確認              |

### 診断コマンド

```bash
# Check Calico node status
calicoctl node status

# List all BGP peers
calicoctl get bgppeers -o wide

# Check BGP configuration
calicoctl get bgpconfiguration default -o yaml

# View BIRD logs
kubectl logs -n kube-system calico-node-xxxxx -c calico-node | grep -i bird

# Check IP routes on node
ip route show | grep bird
```

***

## マルチ Rack およびマルチデータセンター設計

### Route Reflectors を使用するマルチ Rack

```mermaid
graph TB
    subgraph "Datacenter"
        subgraph "Management Rack"
            RR1[Route Reflector 1<br/>Cluster ID: 1.0.0.1]
            RR2[Route Reflector 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Compute Rack 1"
            N1[Node 1]
            N2[Node 2]
            N3[Node 3]
        end

        subgraph "Compute Rack 2"
            N4[Node 4]
            N5[Node 5]
            N6[Node 6]
        end

        subgraph "Compute Rack 3"
            N7[Node 7]
            N8[Node 8]
            N9[Node 9]
        end
    end

    RR1 <--> RR2

    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
    N7 & N8 & N9 --> RR1
    N7 & N8 & N9 --> RR2
```

### マルチデータセンター BGP 設計

```mermaid
graph TB
    subgraph "DC1 (AS 64512)"
        subgraph "DC1 RRs"
            DC1_RR1[DC1 RR1]
            DC1_RR2[DC1 RR2]
        end
        DC1_N1[DC1 Nodes]

        DC1_RR1 <--> DC1_RR2
        DC1_N1 --> DC1_RR1 & DC1_RR2
    end

    subgraph "DC2 (AS 64513)"
        subgraph "DC2 RRs"
            DC2_RR1[DC2 RR1]
            DC2_RR2[DC2 RR2]
        end
        DC2_N1[DC2 Nodes]

        DC2_RR1 <--> DC2_RR2
        DC2_N1 --> DC2_RR1 & DC2_RR2
    end

    subgraph "WAN Edge (AS 65000)"
        WAN1[WAN Router 1]
        WAN2[WAN Router 2]
    end

    DC1_RR1 & DC1_RR2 <--> WAN1 & WAN2
    DC2_RR1 & DC2_RR2 <--> WAN1 & WAN2
```

マルチデータセンター向け設定:

```yaml
# DC1 Configuration
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

  communities:
    - name: dc1-origin
      value: "64512:1"

---
# Peer DC1 RRs with WAN routers
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: dc1-to-wan
spec:
  nodeSelector: has(route-reflector)
  peerIP: 10.255.0.1  # WAN Router
  asNumber: 65000
```

***

## ベストプラクティスのまとめ

### 設計に関する推奨事項

1. **クラスターサイズ < 50 Node**: Full-mesh で問題なし
2. **クラスターサイズ 50-200 Node**: 2～3 台の Route Reflector をデプロイ
3. **クラスターサイズ > 200 Node**: 階層型 Route Reflector をデプロイ
4. **マルチ Rack**: Rack を考慮した Route Reflector 配置を使用
5. **マルチデータセンター**: DC ごとに個別の AS を使用し、DC 間は eBGP を使用

### セキュリティに関する推奨事項

1. 外部ピアには常に MD5 認証を有効化する
2. ルートインジェクションを防ぐため Prefix フィルタリングを実装する
3. サポートされている場合は GTSM (TTL Security) を使用する
4. ピアごとに受け入れる最大ルート数を制限する
5. BGP セッションの異常を監視する

### 運用に関する推奨事項

1. BGP トポロジ用の Node ラベルを一貫して付与する
2. AS 番号の割り当てスキームを文書化する
3. BGP のモニタリングとアラートを実装する
4. フェイルオーバーシナリオを定期的にテストする
5. BGP タイマーをピア間で一貫させる

***

## 参考資料

* [Calico BGP ドキュメント](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://tools.ietf.org/html/rfc4271)
* [RFC 4456 - BGP Route Reflection](https://tools.ietf.org/html/rfc4456)
* [RFC 5765 - GTSM for BGP](https://tools.ietf.org/html/rfc5082)
