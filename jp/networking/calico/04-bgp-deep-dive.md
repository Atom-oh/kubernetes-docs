# Part 4: BGP 詳解

> **対応バージョン**: Calico v3.29+ / Kubernetes 1.28+ **最終更新**: February 23, 2026

## はじめに

Border Gateway Protocol（BGP）はインターネットを支えるルーティングプロトコルであり、Calico はこれを活用して Kubernetes クラスター向けに高いスケーラビリティと標準ベースのネットワーキングを提供します。トラフィックをカプセル化するオーバーレイネットワークとは異なり、Calico の BGP ベースネットワーキングはネイティブ IP ルーティングを可能にし、優れたパフォーマンスと既存ネットワークインフラストラクチャとのシームレスな統合を実現します。

この詳解では、BGP の基本、Calico の BGP アーキテクチャオプション、設定リソース、およびエンタープライズ環境向けの高度なデプロイメントパターンを扱います。

***

## BGP の基本

### BGP とは

BGP（Border Gateway Protocol）は、自律システム間でルーティング情報を交換するために設計されたパスベクタールーティングプロトコルです。Calico では、BGP はクラスターのノード間で Pod IP ルートを配布し、必要に応じて外部ネットワークインフラストラクチャにも配布します。

### BGP の主要概念

| 概念                    | 説明                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| **自律システム（AS）** | 単一の管理ドメイン下にある IP ネットワークの集合     |
| **AS 番号（ASN）**        | AS の一意の識別子（16 ビット: 1-65534、32 ビット: 1-4294967294）  |
| **iBGP**                   | 内部 BGP - 同じ AS 内のルーター間のセッション               |
| **eBGP**                   | 外部 BGP - 異なる AS 内のルーター間のセッション            |
| **NLRI**                   | Network Layer Reachability Information - 広報されるルート |
| **BGP Speaker**            | BGP に参加するルーターまたはソフトウェア                        |

### プライベート AS 番号の範囲

組織内での内部使用向けに、IANA は次のプライベート ASN 範囲を予約しています。

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico は通常、クラスター内部 BGP に `64512-65534` の範囲の ASN を使用します。

### BGP ルート選択プロセス

BGP Speaker が同じ宛先への複数のルートを受信すると、次の基準を順に使用して最適なルートを選択します。

![同じ宛先への複数のルートを持つ BGP Speaker は、7 つのタイブレーク基準を順に評価し、同点の場合は次の基準へ進み、最適なルートを 1 つ選択します。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-0.svg)

### iBGP と eBGP の動作

| 属性               | iBGP                               | eBGP                                   |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| AS\_PATH の変更   | 変更なし                       | ローカル AS を追加                      |
| Next-hop                | デフォルトでは変更なし             | ピアリングアドレスに変更             |
| デフォルト TTL             | 255                                | 1（隣接していない場合はマルチホップが必要） |
| ルート広報     | eBGP ピアにのみ送信（スプリットホライズン） | すべてのピアに送信                           |
| Administrative Distance | 200                                | 20                                     |

***

## Calico BGP アーキテクチャ

![Calico BGP トポロジーを並べて比較します。デフォルトのフルメッシュでは 4 つのノードが他のすべてのノードとピアリングします（N(N−1)/2 セッション）。一方、Route Reflector 設計ではノードは相互にピアリングした 2 つの Reflector とのみピアリングします（2N+1 セッション）。](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-9.html)

### BIRD: Calico の BGP 実装

Calico は BGP 実装として BIRD（BIRD Internet Routing Daemon）を使用します。BIRD はすべてのノード上の `calico-node` DaemonSet の一部として実行されます。

![各 calico-node Pod 内では、Calico API が confd に情報を渡して BIRD を設定し、BIRD がルーティングテーブルをプログラムして外部ルーターおよび他の Calico ノードと BGP でピアリングします。一方、Felix は独立して iptables/eBPF データプレーンをプログラムします。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-1.svg)

### BGP トポロジーオプション

Calico は主に 2 つの BGP トポロジーをサポートします。

1. **ノード間メッシュ（フルメッシュ）** - デフォルト設定
2. **Route Reflector** - 大規模クラスターに推奨

***

## フルメッシュトポロジー

### フルメッシュの仕組み

デフォルトのフルメッシュ設定では、すべての Calico ノードがクラスター内の他のすべてのノードと BGP ピアリングセッションを確立します。

![デフォルトのフルメッシュ設定では、すべての Calico ノードが他のすべてのノードとピアリングします。Node 1 の視点では残りの 4 ノードに接続し、同じ関係が 5 ノードすべてで対称的に成立するため、合計 10 の BGP セッションが生成されます。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-2.svg)

### セッション数の計算式

フルメッシュトポロジーの BGP セッション数は二次的に増加します。

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### フルメッシュのスケーリング上の制約

| クラスターサイズ  | BGP セッション | ノードあたりのメモリ | CPU への影響 | 推奨事項 |
| ------------- | ------------ | --------------- | ---------- | -------------- |
| < 50 ノード    | < 1,225      | \~50 MB         | 最小限    | フルメッシュで可   |
| 50-100 ノード  | 1,225-4,950  | \~100 MB        | 低        | RR を検討    |
| 100-200 ノード | 4,950-19,900 | \~200 MB        | 中程度   | RR を使用         |
| > 200 ノード   | > 19,900     | > 400 MB        | 高       | RR が必須     |

### ノード間メッシュの有効化/無効化

現在の状態を確認します。

```bash
calicoctl get bgpconfiguration default -o yaml
```

ノード間メッシュを無効化します（Route Reflector を使用する場合）。

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

## Route Reflector トポロジー

### Route Reflector の概念

Route Reflector（RR）は、ノードの一部が他のノードへルートを反射できるようにすることで iBGP のスケーラビリティ問題を解決します。これによりフルメッシュが不要になります。

![2 つの Route Reflector は相互に、かつすべてのクライアントノードとピアリングし、クライアントノード同士が直接ピアリングしなくてもルートを学習できるようにするため、フルメッシュが不要になります。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-3.svg)

### Route Reflector の主要属性

| 属性            | 説明                                                   |
| -------------------- | ------------------------------------------------------------- |
| **Cluster ID**       | 同じクライアントにサービスを提供する RR のセットを識別します              |
| **Originator ID**    | ルーティングループを防止します（送信元の router ID に設定）   |
| **Route Reflection** | RR はクライアントから学習したルートを他のクライアントへ再広報します |

### Route Reflector 使用時のセッション数

2 つの Route Reflector と N 個のクライアントノードの場合:

```
Sessions = 2 × N + 1 (RR-to-RR peering)

Examples:
- 100 nodes: 2 × 100 + 1 = 201 sessions (vs 4,950 in full-mesh)
- 500 nodes: 2 × 500 + 1 = 1,001 sessions (vs 124,750 in full-mesh)
```

### Route Reflector ノードの設定

**手順 1: Route Reflector として指定するノードにラベルを付与する**

```bash
kubectl label node rr-node-1 calico-route-reflector=true
kubectl label node rr-node-2 calico-route-reflector=true
```

**手順 2: Route Reflector の Cluster ID を設定する**

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

**手順 3: ノード間メッシュを無効化する**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

**手順 4: Route Reflector への BGP ピアリングを設定する**

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

**パターン 1: デュアル Route Reflector（小規模/中規模クラスター）**

![各 Availability Zone に 1 つの Route Reflector を配置し、両方の Zone にあるすべてのノードが両方の Route Reflector とピアリングします。そのため、1 つの Zone の Route Reflector を失っても、どのノードも孤立しません。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-4.svg)

**パターン 2: 階層型 Route Reflector（大規模クラスター）**

![2 階層の Route Reflector 構成です。2 つのグローバル Route Reflector が相互に、かつすべてのラックレベル Route Reflector とピアリングし、各ラックのノードはそのラックの Route Reflector とのみピアリングします。これにより、クラスターの成長に伴ってもセッション数を低く抑えられます。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-5.svg)

***

## BGPPeer リソース

`BGPPeer` リソースは、Calico ノードと外部 BGP Speaker 間の BGP ピアリング関係を定義します。

### BGPPeer スコープタイプ

| タイプ              | 説明          | ユースケース                |
| ----------------- | -------------------- | ----------------------- |
| **グローバル**        | すべてのノードに適用 | 外部ルーターピアリング |
| **ノード固有** | nodeSelector を使用    | ラックローカルピアリング      |
| **ノード単位**      | 正確なノードを指定 | 特別な設定  |

### グローバル BGPPeer の例

すべてのノードを外部 ToR スイッチとピアリングします。

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

### ノード固有 BGPPeer の例

特定のラックにあるノードをローカル ToR スイッチとピアリングします。

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

`peerSelector` を使用して、Calico ノードをピアとして動的に選択します。

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

`BGPConfiguration` リソースは、クラスター全体の BGP 設定を定義します。

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

Calico は BGP を介して Kubernetes Service IP を広報できるため、外部クライアントは Service に直接到達できます。

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

BGP Community を使用すると、外部ルーター上でポリシーベースルーティングを行うためにルートへタグ付けできます。

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

### ノード固有の AS 番号

複雑なトポロジーでは、ノードごとに異なる AS 番号を割り当てることができます。

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
| **ClusterIP**      | 内部 Service IP       | 内部負荷分散 |
| **ExternalIP**     | ユーザー割り当ての外部 IP | 外部からの直接アクセス  |
| **LoadBalancerIP** | Cloud provider が割り当て   | Cloud 統合       |

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

Cloud provider 統合のないベアメタルクラスターの場合:

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

### ToR スイッチ設定の例

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

![Spine-Leaf ファブリックでは、各 Leaf スイッチが冗長性のために両方の Spine スイッチとピアリングし、各ラックの Kubernetes ノードはそのラックの Leaf スイッチとのみピアリングします。したがって、BGP ルートはノードから Leaf 層、Spine 層へと流れます。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-6.svg)

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

## BGP Community タグ付け戦略

### Community 設計パターン

| Community     | 意味        | アクション                           |
| ------------- | -------------- | -------------------------------- |
| `64512:100`   | Pod ネットワーク   | 受け入れ、通常のルーティング           |
| `64512:200`   | Service IP    | 受け入れ、特別なポリシーを適用する場合がある |
| `64512:300`   | インフラストラクチャ | より優先度の高いルーティング          |
| `65535:65281` | NO\_EXPORT     | AS 外へ広報しない      |
| `65535:65282` | NO\_ADVERTISE  | どのピアにも広報しない     |

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

受け入れる/広報する Prefix を制限します。

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

### GTSM（TTL セキュリティ）

Generalized TTL Security Mechanism は、偽装された BGP パケットを防ぎます。

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

Pod CIDR を集約して、広報するルート数を削減します。

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

BIRD の再起動中のトラフィック中断を最小限にするため、BGP Graceful Restart を有効化します。

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

### 一般的な BGP の問題と解決策

| 問題                    | 症状                      | 解決策                              |
| ------------------------ | ----------------------------- | ------------------------------------- |
| セッションが Active で停止 | ルートを学習しない             | ファイアウォール（TCP 179）、AS 番号を確認  |
| ルートが伝播しない   | ラック間で Pod に到達できない | ノード間メッシュまたは RR 設定を確認 |
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

## マルチラックおよびマルチデータセンターの設計

### Route Reflector を使用するマルチラック

![管理ラックにある 2 つの Route Reflector は相互に、かつすべてのコンピュートラックとピアリングします。そのため、各コンピュートラックのノードはフルメッシュなしですべての他ラックのルートに到達でき、1 つの Route Reflector を失ってもどのラックも孤立しません。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-7.svg)

### マルチデータセンター BGP 設計

![各データセンターは独自の AS を実行し、各自の Route Reflector が内部でノードとピアリングします。また、各データセンターの Route Reflector は共有 WAN エッジと eBGP でピアリングし、2 つのデータセンターを接続します。](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-8.svg)

マルチデータセンター向けの設定:

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

## ベストプラクティスの要約

### 設計に関する推奨事項

1. **クラスターサイズ < 50 ノード**: フルメッシュで問題ありません
2. **クラスターサイズ 50-200 ノード**: 2～3 個の Route Reflector をデプロイします
3. **クラスターサイズ > 200 ノード**: 階層型 Route Reflector をデプロイします
4. **マルチラック**: ラックを考慮した Route Reflector 配置を使用します
5. **マルチデータセンター**: DC ごとに個別の AS を使用し、DC 間には eBGP を使用します

### セキュリティに関する推奨事項

1. 外部ピアには常に MD5 認証を有効化します
2. ルートインジェクションを防ぐため Prefix フィルタリングを実装します
3. サポートされる場合は GTSM（TTL セキュリティ）を使用します
4. ピアごとに受け入れる最大ルート数を制限します
5. BGP セッションの異常を監視します

### 運用に関する推奨事項

1. BGP トポロジー用に一貫してノードにラベルを付けます
2. AS 番号の割り当てスキームを文書化します
3. BGP のモニタリングとアラートを実装します
4. フェイルオーバーシナリオを定期的にテストします
5. ピア間で BGP タイマーを一貫させます

***

## 参考資料

* [Calico BGP ドキュメント](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://tools.ietf.org/html/rfc4271)
* [RFC 4456 - BGP Route Reflection](https://tools.ietf.org/html/rfc4456)
* [RFC 5765 - BGP の GTSM](https://tools.ietf.org/html/rfc5082)
