# パート 2: アーキテクチャ

> **サポート対象バージョン**: Calico v3.29+ / Kubernetes 1.28+ **最終更新**: February 23, 2026

## 概要

このセクションでは、Calico のアーキテクチャを詳しく解説します。本番環境で Calico を効果的にデプロイ、トラブルシューティング、最適化するには、各コンポーネントの動作と相互作用を理解することが不可欠です。

## アーキテクチャ全体図

![Kubernetes control plane、Calico control plane（API server、kube-controllers、Typha）、および Felix がローカル Data Plane をプログラムし、confd/BIRD がノード間の BGP mesh を介して route を配布する代表的な worker node を示すアーキテクチャ図。](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

## Felix: Calico Agent

Felix は、cluster 内のすべての node で実行される主要な Calico Agent です。目的の接続性と Network Policy の適用を実現するために、host 上の route と ACL（Access Control List）をプログラムします。

### Felix の責務

![Felix の Datastore Watcher が route、ACL、interface、IPAM manager に更新を配信し、それらが node の routing table、iptables rule、IP set、network interface をプログラムすることを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-1.svg)

### コア機能

1. **Route のプログラミング**: Pod CIDR block の route を管理します
2. **ACL の適用**: Network Policy 用の iptables/nftables/eBPF rule をプログラムします
3. **Interface の管理**: workload endpoint interface を設定します
4. **Health の報告**: node と endpoint の health を datastore に報告します
5. **IPAM の調整**: ローカル workload の IP address allocation を管理します

### Felix Data Plane のオプション

Felix は複数の Data Plane backend をサポートしています。

| Data Plane   | 説明                | 最適な用途                                    |
| ------------ | -------------------------- | ------------------------------------------- |
| **iptables** | 従来の Linux firewall | 互換性、成熟したデプロイメント           |
| **nftables** | 最新の Linux firewall      | 新しい kernel、より優れた performance           |
| **eBPF**     | Kernel 内でプログラム可能     | 最高の performance、kube-proxy の置き換え |

### FelixConfiguration Resource

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Logging configuration
  logSeverityScreen: Info
  logSeverityFile: Warning
  logFilePath: /var/log/calico/felix.log

  # Data plane selection
  bpfEnabled: false                    # Set true for eBPF data plane
  bpfDataIfacePattern: ^((en|wl|eth).*|bond[0-9]+)$
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: Tunnel

  # iptables configuration
  iptablesBackend: Auto               # Auto, Legacy, NFT
  iptablesRefreshInterval: 90s
  iptablesPostWriteCheckIntervalSecs: 1
  iptablesLockFilePath: /run/xtables.lock
  iptablesLockTimeoutSecs: 0
  iptablesLockProbeIntervalMillis: 50

  # Performance tuning
  ipipMTU: 1440
  vxlanMTU: 1410
  wireguardMTU: 1420

  # Health and metrics
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  prometheusGoMetricsEnabled: true
  prometheusProcessMetricsEnabled: true

  # Policy configuration
  defaultEndpointToHostAction: Drop
  failsafeInboundHostPorts:
    - protocol: TCP
      port: 22
    - protocol: UDP
      port: 68
  failsafeOutboundHostPorts:
    - protocol: UDP
      port: 53
    - protocol: UDP
      port: 67

  # Interface configuration
  interfacePrefix: cali
  chainInsertMode: Insert

  # Reporting
  reportingIntervalSecs: 30
  reportingTTLSecs: 90
```

### Felix iptables Rule の構造

Felix は、効率的に処理するため iptables rule を chain に整理します。

```
                         ┌─────────────────────────────────────────┐
                         │              FORWARD Chain              │
                         └─────────────────┬───────────────────────┘
                                           │
                         ┌─────────────────▼───────────────────────┐
                         │          cali-FORWARD (Calico)          │
                         └─────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│   cali-from-wl-dispatch   │ │   cali-to-wl-dispatch   │ │    cali-from-host-ep     │
│  (from workload traffic)  │ │  (to workload traffic)  │ │   (from host endpoints)   │
└─────────────┬─────────────┘ └────────────┬────────────┘ └─────────────┬─────────────┘
              │                            │                            │
┌─────────────▼─────────────┐ ┌────────────▼────────────┐ ┌─────────────▼─────────────┐
│    cali-fw-caliXXXXXX     │ │    cali-tw-caliXXXXXX   │ │    Per-endpoint policy    │
│    (per-endpoint rules)   │ │   (per-endpoint rules)  │ │          chains           │
└───────────────────────────┘ └─────────────────────────┘ └───────────────────────────┘
```

### Felix Data Flow

![Felix が datastore から policy、endpoint、IP pool の更新を受け取り、それぞれを iptables rule、route table entry、または network interface 設定に変換することを示すシーケンス図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-2.svg)

## BIRD: BGP Routing Daemon

BIRD（BIRD Internet Routing Daemon）は、Calico が node 間で route を配布するために使用する BGP daemon です。

### Calico アーキテクチャにおける BIRD

![各 node の BIRD instance が完全な iBGP mesh を形成して Pod route を交換し、その後 top-of-rack switch および core router と eBGP peer を確立してそれらの route を外部に advertise することを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-3.svg)

### BGP Session のタイプ

| Session タイプ          | Use Case                    | 設定          |
| --------------------- | --------------------------- | ---------------------- |
| **Node-to-Node Mesh** | 小規模 cluster のデフォルト  | 自動、full mesh   |
| **Route Reflector**   | 大規模 cluster（100+ node） | 専用 RR node     |
| **External Peering**  | On-premises integration     | 手動 BGP peer 設定 |

### BGP 設定例

#### Node-to-Node Mesh（デフォルト）

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Route Reflector 設定

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
# Configure route reflector nodes
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: node-rr-1
  labels:
    route-reflector: "true"
spec:
  bgp:
    routeReflectorClusterID: 224.0.0.1
---
# Configure BGP peer to route reflector
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-rr
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: route-reflector == "true"
```

#### External BGP Peering

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### Route 伝播プロセス

![新しい Pod の route が Felix によって割り当てられ、BIRD のローカル routing table に追加され、BGP UPDATE によって peer node へ伝播されることで、peer node が route をインストールして Felix が適切に routing することを示すシーケンス図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-4.svg)

### BIRD Status Command

```bash
# Access BIRD CLI on a Calico node
kubectl exec -n calico-system calico-node-xxxxx -c calico-node -- birdcl

# Show BGP protocol status
birdcl> show protocols
name     proto    table    state  since       info
kernel1  Kernel   master   up     2024-01-01
device1  Device   master   up     2024-01-01
direct1  Direct   master   up     2024-01-01
Mesh_10_0_1_10  BGP  master  up   2024-01-01  Established
Mesh_10_0_1_11  BGP  master  up   2024-01-01  Established

# Show BGP routes
birdcl> show route protocol Mesh_10_0_1_10
192.168.1.0/26     via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]
192.168.1.64/26    via 10.0.1.10 on eth0 [Mesh_10_0_1_10 2024-01-01] * (100/0) [i]

# Show route details
birdcl> show route 192.168.1.0/26 all
```

## confd: Configuration Management

confd は、Calico datastore を監視し、BIRD configuration file を生成する軽量な configuration management tool です。

### confd のワークフロー

![confd の watcher が Calico datastore 内の BGP configuration、peer、node resource に反応し、template から bird.cfg file をレンダリングして、実行中の BIRD process に渡すことを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-5.svg)

### confd Template 処理

confd は Go template を使用して BIRD configuration を生成します。

```
# Template: /etc/calico/confd/templates/bird.cfg.template
# Output: /etc/calico/confd/config/bird.cfg

router id {{.NodeIP}};

protocol kernel {
    learn;
    persist;
    scan time 2;
    import all;
    export {{if .ExportKernel}}all{{else}}none{{end}};
}

protocol device {
    scan time 2;
}

{{range .BGPPeers}}
protocol bgp {{.Name}} {
    local as {{$.LocalAS}};
    neighbor {{.PeerIP}} as {{.PeerAS}};
    import all;
    export {{if .ExportFilter}}filter {{.ExportFilter}}{{else}}all{{end}};
    {{if .Password}}password "{{.Password}}";{{end}}
    graceful restart;
}
{{end}}
```

## Typha: Scaling Component

Typha は、Kubernetes API server と Felix Agent の間に配置される fan-out proxy です。datastore update を cache して配布することで、API server の負荷を軽減します。

### Typha が必要な理由

![小規模 cluster ではすべての Felix が Kubernetes API を直接 watch する一方、大規模 cluster では Typha Pod が cache した update を数百の Felix Agent に fan-out することを比較した図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-6.svg)

### Typha Scaling の計算

推奨する Typha replica 数は cluster size によって異なります。

```
Typha Replicas = max(3, ceil(Nodes / 200))

Examples:
- 50 nodes:   3 Typha replicas (minimum)
- 200 nodes:  3 Typha replicas
- 500 nodes:  3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
```

### Typha Deployment 設定

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      k8s-app: calico-typha
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      nodeSelector:
        kubernetes.io/os: linux
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
      priorityClassName: system-cluster-critical
      serviceAccountName: calico-typha
      containers:
      - name: calico-typha
        image: calico/typha:v3.29.0
        ports:
        - containerPort: 5473
          name: calico-typha
          protocol: TCP
        env:
        - name: TYPHA_LOGSEVERITYSCREEN
          value: "info"
        - name: TYPHA_LOGFILEPATH
          value: "none"
        - name: TYPHA_LOGSEVERITYSYS
          value: "none"
        - name: TYPHA_CONNECTIONREBALANCINGMODE
          value: "kubernetes"
        - name: TYPHA_DATASTORETYPE
          value: "kubernetes"
        - name: TYPHA_HEALTHENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSENABLED
          value: "true"
        - name: TYPHA_PROMETHEUSMETRICSPORT
          value: "9093"
        livenessProbe:
          httpGet:
            path: /liveness
            port: 9098
          periodSeconds: 30
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /readiness
            port: 9098
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 1000m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  ports:
  - port: 5473
    protocol: TCP
    targetPort: calico-typha
    name: calico-typha
  selector:
    k8s-app: calico-typha
```

### Typha Fan-out アーキテクチャ

![2 つの API server watch stream が 2 つの Typha Pod に入力され、各 Pod が update をローカルに cache して、その node group 内の約 100 の Felix Agent に fan-out することを示すアーキテクチャ図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-7.svg)

## kube-controllers: Kubernetes Integration

calico-kube-controllers Pod は、Kubernetes resource を Calico datastore と sync する一連の controller を実行します。

### Controller の概要

| Controller                      | 目的                                           |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller**             | Kubernetes node を Calico node resource と sync します |
| **Policy Controller**           | Kubernetes NetworkPolicy を Calico policy と sync します |
| **Namespace Controller**        | profile management 用に namespace label を sync します     |
| **ServiceAccount Controller**   | RBAC 用に service account label を sync します             |
| **WorkloadEndpoint Controller** | 古い workload endpoint をクリーンアップします                |

### Controller Reconciliation Loop

![kube-controllers が Kubernetes と Calico の resource を繰り返し list して差分を比較し、変更を Calico datastore に書き込むか、両者がすでに sync している場合は何もしないことを示すシーケンス図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-8.svg)

### kube-controllers 設定

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-kube-controllers-config
  namespace: calico-system
data:
  config: |
    {
      "logSeverityScreen": "info",
      "healthEnabled": true,
      "prometheusPort": 9094,
      "controllers": {
        "node": {
          "hostEndpoint": {
            "autoCreate": "Disabled"
          },
          "syncLabels": "Enabled",
          "leakGracePeriod": "15m"
        },
        "policy": {
          "reconcilerPeriod": "5m"
        },
        "workloadEndpoint": {
          "reconcilerPeriod": "5m"
        },
        "namespace": {
          "reconcilerPeriod": "5m"
        },
        "serviceAccount": {
          "reconcilerPeriod": "5m"
        }
      }
    }
```

## Datastore のオプション

Calico は、configuration と state を保存するための 2 つの datastore backend をサポートしています。

### Kubernetes API Datastore（推奨）

![Felix、Typha、kube-controllers のすべてが Kubernetes API server を介して Calico state の read/write を行い、API server 自体は etcd に永続化することを示す図。独立した Calico etcd cluster は必要ありません。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-9.svg)

**利点:**

* 管理する独立した etcd cluster が不要
* access control に Kubernetes RBAC を使用
* よりシンプルな operational model
* あらゆる Kubernetes distribution で動作

### etcd Datastore（レガシー）

![Felix と Typha が専用の Calico etcd cluster を直接 read/write する一方、kube-controllers がその cluster と Kubernetes API server を橋渡しする、レガシーで分離された datastore オプションを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-10.svg)

**利点:**

* Kubernetes API server から分離
* 非 Kubernetes workload（VM、bare metal）に使用可能
* 非常に大規模な cluster 向けの歴史的な選択肢

### Datastore の比較

| 機能                    | Kubernetes API    | etcd               |
| -------------------------- | ----------------- | ------------------ |
| **運用の複雑さ** | 低い             | 高い             |
| **Scalability**            | 良好（Typha 使用時） | 優れている          |
| **Non-K8s Workloads**      | 限定的           | 完全サポート       |
| **Backup/Restore**         | K8s 経由           | 個別の tool   |
| **Access Control**         | K8s RBAC          | etcd auth          |
| **推奨**         | デフォルトの選択    | 特別なケースのみ |

## Component Interaction Sequence

![Kubernetes API を通じた NetworkPolicy と Pod の作成を、kube-controllers と Typha を経由して Felix まで追跡し、Felix がローカル Data Plane をプログラムして BGP route を更新することを示すシーケンス図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-11.svg)

## Packet Flow の分析

### Ingress Packet Flow（Pod-to-Pod、同一 Node）

![同じ node にある一方の Pod からもう一方の Pod へ、veth interface と host の iptables/eBPF policy check を通過して packet が移動することを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-12.svg)

### Egress Packet Flow（Pod-to-Pod、IPIP を使用する異なる Node）

![一方の node の Pod から出る packet が veth と iptables check を通過し、物理 network switch を越えて IPIP encapsulate され、2 つ目の node で decapsulate されて Pod に配信されることを示す図。](../../../assets/diagrams/rendered/en-networking-calico-02-architecture-13.svg)

### Packet Structure の比較

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## まとめ

Calico のアーキテクチャは、scalability、performance、operational simplicity を考慮して設計されています。

1. **Felix**: すべての node 上の主力 Agent で、route と ACL をプログラムします
2. **BIRD**: BGP により route を配布し、native routing integration を実現します
3. **confd**: datastore を BIRD configuration に橋渡しします
4. **Typha**: API server の負荷を軽減して system を scale します
5. **kube-controllers**: Kubernetes と Calico を sync します
6. **Datastore**: configuration storage 用の Kubernetes API（推奨）または etcd

これらのコンポーネントと相互作用を理解することは、次のために不可欠です。

* 接続性の問題のトラブルシューティング
* 大規模環境での performance 最適化
* capacity とアーキテクチャの計画
* 既存の network infrastructure との integration

[前へ: パート 1 - Calico の紹介](01-introduction.md)

[次へ: パート 3 - Networking Modes](03-networking-modes.md)

[Calico の概要に戻る](./README.md)

## クイズ

この章で学んだ内容を確認するには、[Architecture Quiz](../../quizzes/networking/calico/02-architecture-quiz.md)に挑戦してください。
