# Glossary and Abbreviations

> **Review baseline**: Cilium 1.20.2.
> **最終レビュー**: October 15, 2026.

Cilium、eBPF、Kubernetes、およびネットワーキングに関するアルファベット順のリファレンスです。重複する項目は統合されています。

## A

**API (Application Programming Interface)** - General

- アプリケーション間の通信を可能にするインターフェース定義の集合

**ARP (Address Resolution Protocol)** - Networking

- IPv4 アドレスをローカルリンク上のリンク層アドレス（一般的には Ethernet MAC アドレス）に解決します。
- リモートの宛先では、ホストは次ホップを解決します。IPv6 では ARP ではなく Neighbor Discovery を使用します。

**AWS ENI (Elastic Network Interface)** - Networking

- Amazon Web Services が提供する仮想ネットワークインターフェース
- Cilium の AWS ENI IPAM モードで使用されます

## B

**BGP (Border Gateway Protocol)** - Networking

- ピア間で到達可能性を広告するために使用されるドメイン間ルーティングプロトコル。
- Cilium BGP Control Plane は選択したプレフィックスを広告します。これはネイティブルーティングモードではなく、ローカルデータパスのルートを設定しません。

**BPF (Berkeley Packet Filter)** - eBPF

- パケットフィルタリングの技術であり、eBPF の前身
- 元来はネットワークパケットキャプチャのために開発されました

**BPF Maps** - eBPF

- BPF プログラムとユーザースペースが状態またはイベントを共有するために使用する、カーネル管理のデータ構造。
- 多くの型はキーと値を使用します。一方、リングバッファ、キュー、スタックには異なる操作があります。BPF リングバッファは map の lookup/update/delete をサポートしません。

## C

**CGroup (Control Group)** - Kubernetes

- Linux の control groups はプロセスを編成し、CPU やメモリなどのリソースを計上または制御します。
- コンテナランタイムは cgroups を使用しますが、それだけでプロセスまたはネットワーク名前空間の分離を提供するものではありません。

**CIDR (Classless Inter-Domain Routing)** - Networking

- IP アドレスの割り当ておよびルーティング集約の方法
- 例: 192.168.1.0/24 は、192.168.1.0 から 192.168.1.255 までの IP アドレス範囲を表します

**Cilium** - Cilium

- eBPF を基盤とするオープンソースのネットワーキング、セキュリティ、および可観測性ソリューション
- Kubernetes CNI 実装として使用されます

**Cilium Agent** - Cilium

- エンドポイント、BPF プログラム、ポリシー／データパス状態を管理するノードローカルの Cilium コンポーネントです。Cilium が管理する適格なノード上で実行されます。

**Cilium Operator** - Cilium

- CRD 登録、モード依存の IPAM/LB IPAM、ガベージコレクション、有効化された Ingress/Gateway コントローラーなどのタスクを担当するクラスターレベルのコントローラー。
- レプリカ数は設定可能です。オプションのアイデンティティ管理および ClusterMesh 同期は有効化した機能に依存し、ノードのパケット転送コンポーネントではありません。

**ClusterMesh** - Cilium

- サービスディスカバリー、ロードバランシング、およびリモートアイデンティティポリシー向けの、Cilium のマルチクラスターのネットワークメタデータ／接続性機能。
- 互換性のあるアドレッシング、信頼、および到達可能なパスが必要です。共有ストレージを提供するものでも、すべてのポリシーリソースを自動的にレプリケートするものでもありません。

**CNI (Container Network Interface)** - Kubernetes

- Container Network Interface: コンテナネットワーク接続を設定するための仕様およびプラグイン。
- 現在の Kubernetes では、CRI コンテナランタイムが CNI プラグインをロード／呼び出しします。kubelet の従来の直接的な CNI 管理フラグは Kubernetes 1.24 で削除されました。

**CoreDNS** - Kubernetes

- Kubernetes クラスターで一般的に使用される DNS サーバー
- サービスディスカバリーで重要な役割を果たします

**CRD (Custom Resource Definition)** - Kubernetes

- Kubernetes API を拡張してカスタムリソースを定義する方法
- Cilium はネットワークポリシーなどを定義するために CRD を使用します

## D

**DaemonSet**

- スケジューリング制約によって選択された適格なノード上でデーモン Pod を実行する Kubernetes コントローラーです。すべてのノードを対象にする必要はありません。

**DNAT (Destination Network Address Translation)** - Networking

- パケットの宛先 IP アドレスを変更する NAT の種類
- ロードバランシングおよびポートフォワーディングに使用されます

**DNS (Domain Name System)** - Networking

- A/AAAA アドレス、CNAME エイリアス、SRV サービス情報などのレコードを公開する分散型ネーミングシステム。
- Cilium DNS ポリシーと学習済み IP の FQDN ポリシーは、関連はありますが別個の制御です。

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- extended Berkeley Packet Filter: Cilium が使用するプログラム可能なカーネルフックおよび関連インフラストラクチャ。
- verifier は受け入れ前にプログラムの特性を確認します。カーネルまたは verifier の実装に脆弱性がないことを保証するものではありません。

**Endpoint** - Cilium

- ローカルのデータパス／ポリシー状態を持つ、Cilium 管理のネットワークエンドポイントであり、一般的には Pod です。
- その endpoint ID は agent にローカルなものであり、複数の endpoint で共有される security identity とは異なります。

**Envoy** - Cilium

- 設定済みの HTTP/gRPC ポリシー、L7 可視性、およびプロキシベースのサービスルーティングのために Cilium が使用するオープンソースプロキシ。
- DNS ポリシーでは Cilium の DNS プロキシを使用します。Kafka L7 ポリシーはすでにサポートされておらず、すべての L7 ルールが自動的に Envoy インスタンスをデプロイするわけではありません。

## F

**FQDN (Fully Qualified Domain Name)**

- Fully Qualified Domain Name: DNS ツリーにおける完全な位置を識別する絶対名です。多くの場合、末尾のルートドットを付けて、たとえば `www.example.com.` のように記述されます。
- Cilium `toFQDNs` は学習済みの宛先 IP を許可します。これ単独では HTTPS サーバーを認証せず、共有 IP 上のすべての HTTP Host 値を制約するものでもありません。

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- ネットワーク仮想化のためのカプセル化プロトコル

**gRPC (gRPC Remote Procedure Call)**

- Google が開発した高性能 RPC (Remote Procedure Call) フレームワーク

## H

**Hubble** - Cilium

- Cilium のネットワーク可観測性レイヤー: フローイベント、サポートされるプロトコルメタデータ、メトリクス、およびクエリインターフェース。
- 履歴には上限があり、観測結果が失われたりフィルタリングされたりする場合があります。アラート、永続ストレージ、および自動応答には設定済みの統合が必要です。

## I

**Identity** - Cilium

- セキュリティに関連するラベルから導出される数値の security identifier。同じ適用可能な割り当てスコープ内では、複数の endpoint が共有できます。
- CiliumIdentity の `security-labels` フィールドは、CRD 割り当てモードにおける信頼できる情報源です。予約済みおよびノードローカルの identity がすべて、これらのクラスタースコープオブジェクトで表現されるわけではありません。

**IPAM (IP Address Management)** - Networking

- IP Address Management: アドレスの割り当て、追跡、および回収。
- Cilium モードには、cluster-pool、multi-pool、Kubernetes host-scope、クラウド固有モードなど、異なる割り当て所有者およびデータソースがあります。プラットフォーム名が必ずしも別個の `ipam.mode` 値であるとは限りません。

**IPsec** - Networking

- Internet Protocol Security: IP 層の認証／完全性、および適切な設定による機密性のためのメカニズム群。
- Cilium はサポートされるノード間トラフィックの暗号化に IPsec を使用します。キー管理およびパス固有の制限は依然として適用されます。

**Istio**

- サービスメッシュを実装するオープンソースプラットフォーム

## K

**Kafka**

- 分散イベントストリーミングプラットフォームです。ワークロードとして使用することは可能ですが、現在の Cilium は従来の Kafka topic L7 ポリシー API を提供していません。

**kube-proxy** - Kubernetes

- サポートされるノードネットワーキングのメカニズムを通じて Service の仮想 IP／ポート転送を実装する Kubernetes コンポーネント。
- Cilium はこの機能を eBPF で置き換えられます。XDP アクセラレーションはオプションであり、プラットフォームは選択した構成をサポートする必要があります。

**Kubernetes**

- コンテナ化されたアプリケーションのデプロイ、スケーリング、および管理を自動化するオープンソースプラットフォーム

## L

**L2 (Layer 2)**

- OSI モデルのデータリンク層

**L3 (Layer 3)**

- OSI モデルのネットワーク層

**L4 (Layer 4)**

- OSI モデルのトランスポート層

**L7 (Layer 7)**

- OSI モデルのアプリケーション層

**LoadBalancer**

- トラフィック分散機能。Kubernetes の `type: LoadBalancer` はコントローラー／プロバイダーに実装を要求します。外部ロードバランサーは、それがなければ保証されません。

## M

**MAC (Media Access Control) Address**

- Media Access Control address: インターフェースに関連付けられたリンク層アドレス。
- アドレスはローカル管理される場合や変更される場合があります。唯一性および真正性を前提にしてはなりません。

**mTLS (mutual TLS)**

- Mutual TLS: 通常は相互の証明書を検証することで、両方のピアが認証する TLS。
- ピア認証はアプリケーション認可とは別物です。Cilium の帯域外相互認証と Beta ztunnel workload mTLS は、トラフィック保護特性が異なる別個の機能です。

**MTU (Maximum Transmission Unit)**

- Maximum Transmission Unit: リンク／インターフェース上でフラグメンテーションなしに運べる最大のネットワーク層パケットです。IP ヘッダーを含みますが、リンク層ヘッダーは含みません。
- Path MTU はパスによって制約されます。トンネル／暗号化のオーバーヘッドは使用可能な内側パケットサイズに影響します。これは TCP MSS やアプリケーションペイロードサイズではありません。

## N

**NAT (Network Address Translation)**

- IP パケット内の IP アドレス情報を変更するプロセス

**NodePort**

- 適格なノードアドレス上の割り当て済みノードポートを使用する Kubernetes Service の公開方法。
- アドレス選択、トラフィックポリシー、ファイアウォール、およびプラットフォームルーティングが到達可能性を決定します。NodePort を宣言してもパブリックアクセスが保証されるわけではありません。

## O

**OSI (Open Systems Interconnection) Model**

- ネットワーク通信を 7 つの抽象レイヤーに分類する概念モデル

**Overlay Network**

- 既存のネットワーク上に構築される仮想ネットワーク

## P

**Pod**

- Kubernetes における最小のデプロイ可能なコンピューティング単位

**Proxy**

- ピア間の通信を仲介するコンポーネント。必ずしも独立した物理サーバーである必要はありません。

## R

**RBAC (Role-Based Access Control)**

- ロールに基づいてシステムリソースへのアクセスを制御する方法

## S

**Service**

- 論理的なバックエンドの集合（多くの場合はラベルで選択された Pod）に到達するための Kubernetes 抽象化。
- 通常の ClusterIP Service には仮想 IP がありますが、headless Service にはありません。ExternalName は DNS エイリアシングを使用し、selectorless Service は手動管理の EndpointSlice を使用できます。

**SNAT (Source Network Address Translation)**

- パケットの送信元 IP アドレスを変更する NAT の種類

**Socket**

- ネットワークまたはローカルのプロセス間通信に使用される、オペレーティングシステムの通信エンドポイント。

## T

**TCP (Transmission Control Protocol)**

- 信頼性のあるバイトストリームを提供する、接続指向のトランスポートプロトコル

**TLS (Transport Layer Security)**

- ネットワーク上の通信を保護する暗号プロトコル

## U

**UDP (User Datagram Protocol)**

- コネクションレスのトランスポートプロトコル

## V

**VETH (Virtual Ethernet)**

- 通常はペアで作成される仮想 Ethernet デバイス

**VNI (VXLAN Network Identifier)**

- VXLAN Network Identifier: VXLAN ヘッダー内の 24 ビットフィールド。
- Cilium はオーバーレイメタデータで identity 情報を伝送できます。このフィールド幅は、独立して構成された数百万ものテナントネットワークを保証するものではありません。

**VTEP (VXLAN Tunnel Endpoint)**

- VXLAN パケットのカプセル化およびカプセル化解除を担うエンドポイント

**VXLAN (Virtual Extensible LAN)** - Networking

- Layer 3 ネットワーク上に Layer 2 ネットワークをオーバーレイするネットワーク仮想化技術
- Cilium のオーバーレイネットワーキングモードの1つ

## W

**WireGuard** - Networking

- サポートされるノード間トラフィックのために Cilium が使用する VPN トンネルプロトコル。
- 同一ノードの Pod トラフィックは、そのノードトンネルによって暗号化されません。外部トラフィックおよびオプションのノード暗号化には別個の制限があります。IPsec との性能比較には、比較可能な測定が必要です。

## X

**XDP (eXpress Data Path)** - eBPF

- eXpress Data Path: パケット処理フックです。ネイティブ XDP は、対応するネットワークドライバーの受信パスで実行されます。
- PASS はネットワーキングスタックへ処理を継続します。他のアクションでは、ドロップ、送信、またはリダイレクトが可能です。Cilium がサポートする XDP アクセラレーションはオプションであり、普遍的なスループットまたは DDoS 防御を保証するものではありません。

## Primary References

- [Cilium identities](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/security-identities.rst)
- [CiliumIdentity schema](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/cilium_operator.rst)
- [Identity management modes](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC addressing / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## Quiz

[Topic quiz](../../quizzes/networking/cilium/glossary-quiz.md)
