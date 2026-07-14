# Calico 用語集

> **最終更新**: February 22, 2026

このドキュメントでは、Calico ネットワーキングとセキュリティに関連する主要な用語と概念を定義します。これらの用語を理解することは、Kubernetes 環境で Calico を効果的にデプロイおよび運用するために不可欠です。

## 用語カテゴリ

用語は次のカテゴリに分類されています:
- **ネットワーク用語** - 一般的なネットワークの概念
- **Calico コンポーネント** - Calico 固有のコンポーネントとサービス
- **ポリシー用語** - ネットワークポリシーとセキュリティの概念
- **運用用語** - 運用と管理の概念

---

## ネットワーク用語

### A

**AS (Autonomous System)**
- 単一の組織の管理下にあり、インターネットに対して共通のルーティングポリシーを提示する IP ネットワークおよびルーターの集合です。Calico では、AS 番号は BGP ピアリング設定に使用されます。

**ASN (Autonomous System Number)**
- Autonomous System に割り当てられる一意の識別子です。Calico ノードは、内部 BGP ルーティング用にプライベート ASN (64512-65534) を設定できます。

### B

**BGP (Border Gateway Protocol)**
- Autonomous System 間でルーティング情報を交換するために使用される標準の外部ゲートウェイプロトコルです。Calico は BGP を使用して、Pod IP アドレスのルートをノード間および外部ネットワークへ配布します。

**Block Affinity**
- IP アドレスブロックと特定のノード間の関連付けです。Calico はルーティング効率を向上させ、クラスター内のルート数を削減するために、IP ブロックをノードに割り当てます。

### C

**CIDR (Classless Inter-Domain Routing)**
- IP アドレスの割り当ておよび IP ルーティングの方式です。例: 10.244.0.0/16 は 65,536 個の IP アドレスの範囲を表します。

**CNI (Container Network Interface)**
- Linux コンテナ内のネットワークインターフェイスを設定するための仕様およびライブラリ群です。Calico は CNI 仕様を実装し、Kubernetes Pod 向けのネットワーキングを提供します。

**Conntrack (Connection Tracking)**
- ステートフルパケットインスペクションのためにネットワーク接続を追跡する Linux カーネル機能です。Calico はネットワークポリシーと NAT を実装するために conntrack を使用します。

### D

**DNAT (Destination NAT)**
- パケットの宛先 IP アドレスを変更するネットワークアドレス変換です。Kubernetes では Service ロードバランシングに使用されます。

**Direct Routing**
- 異なるノード上の Pod 間のトラフィックが、カプセル化なしで直接ルーティングされるネットワーキングモードです。基盤となるネットワークが Pod CIDR ルーティングをサポートしている必要があります。

**DSR (Direct Server Return)**
- 応答トラフィックがロードバランサーを迂回し、サーバーからクライアントへ直接送られるロードバランシング手法です。Calico の eBPF dataplane は、パフォーマンス向上のために DSR をサポートします。

### E

**eBPF (extended Berkeley Packet Filter)**
- カーネル空間でサンドボックス化されたプログラムを実行できる Linux カーネル技術です。Calico はパフォーマンスを向上させるため、iptables の代替 dataplane として eBPF を使用します。

**Encapsulation**
- ネットワークパケットを別のパケット内にラップするプロセスです。Calico はオーバーレイネットワーキング向けに IPIP および VXLAN カプセル化をサポートします。

### F

**FQDN (Fully Qualified Domain Name)**
- DNS 階層内のホストの正確な位置を指定する完全なドメイン名です。Calico は Egress 制御のために FQDN ベースのネットワークポリシーをサポートします。

**Full Mesh**
- すべてのノードが他のすべてのノードとピアリングする BGP トポロジです。小規模なクラスターには適していますが、100 ノードを超えると適切にスケールしません。

### I

**IPAM (IP Address Management)**
- IP アドレスの割り当て、追跡、管理を担うシステムです。Calico には、ブロックベースの割り当てを備えた組み込みの IPAM システムが含まれます。

**IPIP (IP-in-IP)**
- IP パケットを他の IP パケット内にラップするカプセル化プロトコルです。VXLAN よりオーバーヘッドは低いものの、クラウドプロバイダーのサポートは限定的です。

**IPset**
- IP アドレス、ネットワーク、またはポートのセットを保存する Linux カーネル機能です。Calico は ipsets を使用し、複数のアドレスに対するトラフィックの照合を効率的に行います。

**iptables**
- ネットワーク層で動作する Linux カーネルファイアウォールです。Calico は標準 dataplane において、パケットフィルタリングおよび NAT に iptables（または nftables）を使用します。

### M

**MTU (Maximum Transmission Unit)**
- ネットワークセグメント上で送信できる最大パケットサイズです。カプセル化により実効 MTU は低下します（IPIP: -20 bytes、VXLAN: -50 bytes）。

### N

**NAT (Network Address Translation)**
- パケットヘッダー内の IP アドレス情報を変更するプロセスです。Calico は Pod Egress および Service の実装に NAT を使用します。

**nftables**
- iptables の後継であり、パケット分類のためのモダンなフレームワークを提供します。Calico は iptables の代替として nftables をサポートします。

### O

**Overlay Network**
- 既存の物理ネットワーク上に構築される仮想ネットワークです。Calico は、直接ルーティングが不可能な環境向けに IPIP および VXLAN オーバーレイモードをサポートします。

### R

**Route Reflector**
- クライアント間でルートを反映し、フルメッシュピアリングを不要にする BGP ルーターです。大規模な Calico クラスターで BGP をスケールさせるために不可欠です。

**Routing Table**
- ネットワーク宛先へのルートを保存するデータ構造です。Calico は Pod CIDR のルートを Linux カーネルのルーティングテーブルに設定します。

### S

**SNAT (Source NAT)**
- パケットの送信元 IP アドレスを変更するネットワークアドレス変換です。Pod Egress トラフィックおよびマスカレードに使用されます。

### V

**veth (Virtual Ethernet)**
- ネットワーク名前空間を接続するために使用される仮想ネットワークインターフェイスのペアです。各 Calico Pod には、ホストネットワークに接続する veth ペアがあります。

**VXLAN (Virtual Extensible LAN)**
- Layer 3 インフラストラクチャ上で Layer 2 ネットワークを拡張するカプセル化プロトコルです。IPIP より優れたクラウド互換性を提供しますが、オーバーヘッドは高くなります。

### W

**WireGuard**
- 高速かつ安全な暗号化を提供するモダンな VPN プロトコルです。Calico はノード間の Pod 間トラフィックを暗号化するために WireGuard を使用します。

**Workload Endpoint**
- ワークロード（Pod、VM、またはコンテナ）のネットワークインターフェイスを表す Calico の表現です。IP アドレス、ラベル、およびポリシーの関連付けを保存します。

---

## Calico コンポーネント

### B

**BIRD (BIRD Internet Routing Daemon)**
- ルート配布のために Calico が使用する BGP デーモンです。BIRD は BGP ピアリング、ルートアドバタイズメント、および Route Reflector 機能を管理します。

### C

**calicoctl**
- Calico リソースを管理するためのコマンドラインツールです。ステータスの表示、ポリシーの設定、IPAM の管理、トラブルシューティングに使用されます。

**Calico API Server**
- Calico リソース向けの Kubernetes API 拡張を提供するオプションのコンポーネントです。kubectl から Calico CRD へのアクセスを可能にします。

**CNI Plugin**
- Calico 向けに CNI 仕様を実装するバイナリです。Pod ネットワーキング（veth ペア、ルート、IP 割り当て）のセットアップを担います。

**confd**
- Calico datastore から BIRD 設定ファイルを生成する設定管理ツールです。変更を監視し、BIRD を動的に更新します。

### D

**Dikastes**
- Calico における L7 ポリシー適用に使用されるサイドカープロキシです（主に Calico Enterprise）。アプリケーション層の可視性と制御を提供します。

### F

**Felix**
- 各ノードで実行される主要な Calico エージェントです。ルート、iptables/eBPF ルールの設定、およびネットワークポリシーの適用を担います。

### K

**kube-controllers**
- Kubernetes と Calico datastore 間でデータを同期するコントローラーのセットです。policy、namespace、serviceaccount、workloadendpoint、および node コントローラーが含まれます。

### T

**Tigera Operator**
- Calico のインストールとライフサイクルを管理する Kubernetes Operator です。CRD を通じて宣言的な設定を提供します。

**Typha**
- Felix と datastore の間に配置されるファンアウトプロキシです。接続をキャッシュおよび多重化することで API server の負荷を軽減します。

---

## ポリシー用語

### A

**Action**
- ポリシールール評価の結果です: Allow、Deny、Log、または Pass。一致するトラフィックをどのように処理するかを決定します。

**applyOnForward**
- 転送トラフィック（ホストを通過するトラフィック）にルールを適用するポリシー設定です。Pod と外部ネットワーク間のトラフィックを制御するために使用されます。

### D

**Default Deny**
- 明示的に許可されない限り、すべてのトラフィックをブロックするセキュリティ態勢です。allow ルールを持たないキャッチオールポリシーを使用して実装されます。

**DoNotTrack**
- 一致するトラフィックに対して接続追跡をバイパスするポリシーオプションです。ステートレスな処理を許容できる高スループットのシナリオで有用です。

### E

**Egress**
- Pod からの送信ネットワークトラフィックです。Egress ポリシーは、Pod が通信可能な宛先を制御します。

### G

**GlobalNetworkPolicy**
- クラスター内のすべての Namespace に適用される Calico ポリシーリソースです。クラスター全体のセキュリティルールに使用されます。

**GlobalNetworkSet**
- クラスタースコープの IP アドレスまたは CIDR のセットです。一貫した外部 Endpoint 定義のために GlobalNetworkPolicies から参照されます。

### H

**Host Endpoint**
- ホストのネットワークインターフェイスを表す Calico リソースです。ホストレベルのトラフィックにネットワークポリシーを適用できます。

### I

**Ingress**
- Pod への受信ネットワークトラフィックです。Ingress ポリシーは、Pod と通信可能な送信元を制御します。

### N

**NetworkPolicy**
- Pod がどのように通信を許可されるかを指定する Kubernetes または Calico リソースです。L3-L4（Calico Enterprise では L7 も）で動作します。

**NetworkSet**
- Namespace スコープの IP アドレスまたは CIDR のセットです。ネットワークポリシーで使用する外部 Endpoint をグループ化する方法を提供します。

### O

**Order**
- ポリシーの評価順序を決定する数値です。小さい数値から先に評価されます。同じ Order のポリシーはアルファベット順に評価されます。

### P

**Pass**
- 判断を行わずに次の Tier へスキップするポリシーアクションです。階層型ポリシーモデルで判断を委譲するために使用されます。

**Policy Selector**
- ポリシーの適用先 Endpoint を決定するラベルベースの式です。Calico のセレクター構文を使用します（例: `app == 'web'`）。

**PreDNAT**
- destination NAT の前に適用されるポリシータイプです。NodePort および LoadBalancer Service へのアクセスを制御するために使用されます。

### S

**Staged Policy**
- 実際には適用せず、発生する内容をログに記録するプレビューモードのポリシーです。ポリシーテストのために Calico Enterprise で利用できます。

**Selector**
- ラベルに基づいてリソースに一致する式です。Calico はポリシーターゲットと送信元/宛先の照合の両方にセレクターを使用します。

### T

**Tier**
- 階層型のポリシー評価を提供するポリシーグループ化メカニズムです。より低い Order の Tier にあるポリシーから先に評価されます。

---

## 運用用語

### A

**APIServer (Calico)**
- Calico リソースへの API アクセスを提供するコンポーネントです。kubectl 統合のために有効化できます。

### B

**Block**
- Calico IPAM における IP アドレス割り当ての単位です。デフォルトサイズは /26（64 アドレス）です。効率的なルーティングのため、Block はノードに割り当てられます。

**Block Affinity**
- IP ブロックとノード間のバインディングです。ノード上の Pod がそのノードに割り当てられたブロックから IP を受け取ることを保証します。

### D

**Dataplane**
- パケット転送とポリシー適用を担うコンポーネントです。Calico は iptables および eBPF dataplane をサポートします。

**Datastore**
- Calico 設定のバックエンドストレージです。Kubernetes API（デフォルト）または etcd をサポートします。

### F

**FelixConfiguration**
- クラスター全体で Felix の動作を設定する CRD です。ロギング、メトリクス、dataplane 設定などを制御します。

**Flow Logs**
- Calico によって処理されるネットワーク接続の記録です。送信元、宛先、アクション、およびメタデータが含まれます。

### H

**Health Check**
- Calico コンポーネントの liveness および readiness probe です。Felix はポート 9099 でヘルス Endpoint を公開します。

### I

**Installation**
- Calico Deployment 設定を定義する Tigera Operator CRD です。ネットワーキングモード、リソース、およびコンポーネント設定を指定します。

### M

**Metrics**
- Calico コンポーネントによって公開される Prometheus 形式の統計情報です。Felix（9091）、Typha（9093）、および kube-controllers が運用メトリクスを公開します。

### P

**Pod CIDR**
- クラスター内の Pod 向けに割り当てられる IP アドレス範囲です。Calico の IPPool リソースで設定されます。

### R

**Rollout**
- Calico コンポーネントを更新するプロセスです。中断を最小限に抑えるため、Operator がローリングアップデートを管理します。

### T

**TigeraStatus**
- Calico コンポーネントのステータスを報告する CRD です。Deployment の健全性と設定状態を表示します。

---

## Calico と Kubernetes の用語対応

| Kubernetes 用語 | Calico 相当 | 注記 |
|-----------------|-------------------|-------|
| NetworkPolicy | NetworkPolicy | Calico は K8s NetworkPolicy を追加機能で拡張します |
| - | GlobalNetworkPolicy | クラスター全体のポリシー（Calico 固有） |
| - | Tier | ポリシー階層（Calico 固有） |
| Service CIDR | N/A | Calico は K8s Service CIDR を尊重します |
| Pod CIDR | IPPool | Calico は Pod IP 割り当てを管理します |
| Node | Node | Calico は K8s Node リソースをミラーリングします |
| Namespace | Namespace | Calico ポリシーは Namespace で選択できます |
| Labels | Labels | 同じラベル構文で、セレクターに使用されます |
| Endpoint | WorkloadEndpoint | Calico 内部の Endpoint 表現 |
| - | HostEndpoint | ホストインターフェイスのポリシー（Calico 固有） |

---

## Calico と Cilium の用語対応

| Calico 用語 | Cilium 相当 | 説明 |
|-------------|-------------------|-------------|
| Felix | Cilium Agent | 主要なノードエージェント |
| BIRD | BGP Control Plane | BGP ルーティングデーモン |
| Typha | - | 接続ファンアウトプロキシ（Calico 固有） |
| IPPool | IPAM Pool | IP アドレス割り当てプール |
| NetworkPolicy | CiliumNetworkPolicy | Namespace スコープのポリシー |
| GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy | クラスター全体のポリシー |
| NetworkSet | CiliumIPSet | IP アドレスのグループ化 |
| Tier | - | ポリシー階層（Calico 固有） |
| WorkloadEndpoint | CiliumEndpoint | Pod ネットワーク Endpoint |
| HostEndpoint | - | ホストポリシー（Calico 固有） |
| eBPF Dataplane | eBPF Dataplane | 高性能パケット処理 |
| WireGuard | WireGuard | ノード間の暗号化 |
| - | Hubble | 可観測性プラットフォーム（Cilium 固有） |
| Flow Logs | Hubble Flows | ネットワークフローの可視性 |
| kube-controllers | Cilium Operator | Kubernetes 同期 |
| calicoctl | cilium CLI | 管理用コマンドラインツール |

---

## 相互参照

### アーキテクチャの詳細
- **Felix**: [Part 2: Architecture](02-architecture.md) を参照
- **BGP Configuration**: [Part 4: BGP Deep Dive](04-bgp-deep-dive.md) を参照
- **Typha Scaling**: [Part 7: Advanced Topics](07-advanced-topics.md#typha-sizing-formula) を参照

### ネットワークポリシー
- **Kubernetes NetworkPolicy**: [Part 5: Network Policy](05-network-policy.md) を参照
- **GlobalNetworkPolicy**: [Part 5: Network Policy](05-network-policy.md) を参照
- **Tier-Based Policies**: [Part 5: Network Policy](05-network-policy.md) を参照

### 運用
- **Installation Methods**: [Part 9: Operations](09-operations.md#installation-guide) を参照
- **calicoctl Commands**: [Part 9: Operations](09-operations.md#calicoctl-command-reference) を参照
- **Troubleshooting**: [Part 9: Operations](09-operations.md#troubleshooting) を参照

### EKS 統合
- **VPC CNI + Calico**: [Part 8: EKS Integration](08-eks-integration.md#vpc-cni--calico-architecture) を参照
- **Installation Methods**: [Part 8: EKS Integration](08-eks-integration.md#installation-methods-comparison) を参照

---

## クイズ

この章で学んだ内容を確認するには、[Glossary Quiz](../../quizzes/networking/calico/glossary-quiz.md) に挑戦してください。
