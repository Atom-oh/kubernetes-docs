# 用語集と略語

> **参照バージョン**: Cilium 1.20.3。
> **最終レビュー日**: 2026年10月16日。

Cilium、eBPF、Kubernetes、ネットワークに関する用語をアルファベット順にまとめています。重複する項目は統合しています。

## A

**API (Application Programming Interface)** - 一般

- アプリケーション間の通信を可能にするインターフェース定義の集合です。

**ARP (Address Resolution Protocol)** - ネットワーク

- ローカルリンク上でIPv4アドレスをリンク層アドレス（一般にはEthernet MACアドレス）に解決します。
- 宛先がリモートにある場合、ホストは次ホップのアドレスを解決します。IPv6ではARPではなくNeighbor Discoveryを使います。

**AWS ENI (Elastic Network Interface)** - ネットワーク

- Amazon Web Servicesが提供する仮想ネットワークインターフェースです。
- CiliumのAWS ENI IPAMモードで使用されます。

## B

**BGP (Border Gateway Protocol)** - ネットワーク

- ピア間で到達可能性を広告するために使われるドメイン間ルーティングプロトコルです。
- Cilium BGP Control Planeは選択したプレフィックスを広告します。これはネイティブルーティングモードではなく、ローカルデータパスのルートを設定するものでもありません。

**BPF (Berkeley Packet Filter)** - eBPF

- eBPFの前身となったパケットフィルタリング技術です。
- もともとはネットワークパケットのキャプチャ用に開発されました。

**BPF Maps** - eBPF

- BPFプログラムとユーザー空間が状態やイベントを共有するために使う、カーネル管理のデータ構造です。
- 多くの型はキーと値を使いますが、ring buffer、queue、stackでは操作方法が異なります。BPF ring bufferではmapの検索／更新／削除操作はできません。

## C

**CGroup (Control Group)** - Kubernetes

- Linuxのcontrol group（cgroup）はプロセスをまとめ、CPUやメモリなどのリソース使用量を記録または制御します。
- コンテナランタイムはcgroupを使いますが、cgroupだけでプロセス／ネットワークの名前空間分離が実現するわけではありません。

**CIDR (Classless Inter-Domain Routing)** - ネットワーク

- IPアドレスの割り当てとルーティング集約に使う方式です。
- 例: 192.168.1.0/24は、192.168.1.0から192.168.1.255までのIPアドレス範囲を表します。

**Cilium** - Cilium

- eBPFを基盤とするオープンソースのネットワーク、セキュリティ、可観測性ソリューションです。
- Kubernetes CNIの実装として使用されます。

**Cilium Agent** - Cilium

- エンドポイント、BPFプログラム、ポリシー／データパスの状態を管理する、ノード上のCiliumコンポーネントです。Ciliumが管理する対象ノードで動作します。

**Cilium Operator** - Cilium

- CRDの登録、モードに応じたIPAM／LB IPAM、ガベージコレクション、有効化されたIngress／Gatewayコントローラーなどを担当する、クラスター単位のコントローラーです。
- レプリカ数は設定可能です。ID管理やClusterMesh同期などの任意機能は有効化した機能に依存します。ノード上でパケット転送を行うコンポーネントではありません。

**ClusterMesh** - Cilium

- サービスディスカバリー、ロードバランシング、リモートidentityに基づくポリシーのための、Ciliumのマルチクラスター接続／ネットワークメタデータ機能です。
- アドレス設計の互換性、信頼関係、到達可能な経路が必要です。共有ストレージを提供したり、すべてのポリシーリソースを自動で複製したりする機能ではありません。

**CNI (Container Network Interface)** - Kubernetes

- コンテナのネットワーク接続を構成する仕様およびプラグイン群です。
- 現行Kubernetesでは、CRIコンテナランタイムがCNIプラグインを読み込み、呼び出します。kubeletの従来のCNI直接管理フラグはKubernetes 1.24で削除されました。

**CoreDNS** - Kubernetes

- Kubernetesクラスターで一般的に使われるDNSサーバーです。
- サービスディスカバリーで重要な役割を果たします。

**CRD (Custom Resource Definition)** - Kubernetes

- Kubernetes APIを拡張し、カスタムリソースを定義する方法です。
- Ciliumはネットワークポリシーなどの定義にCRDを使います。

## D

**DaemonSet**

- スケジューリング制約で選択した対象ノード上でデーモンPodを実行するKubernetesコントローラーです。すべてのノードを対象にするとは限りません。

**DNAT (Destination Network Address Translation)** - ネットワーク

- パケットの宛先IPアドレスを書き換えるNATの方式です。
- ロードバランシングやポートフォワーディングに使われます。

**DNS (Domain Name System)** - ネットワーク

- A／AAAAアドレス、CNAME alias、SRVサービス情報などのレコードを公開する分散型の名前解決システムです。
- CiliumのDNSポリシーと、学習したIPを使うFQDNポリシーは、関連していますが別の制御機能です。

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- Ciliumが使う、プログラム可能なカーネルhookと関連基盤です。
- verifierはプログラムを受け入れる前に性質を検査しますが、カーネルやverifierの実装に脆弱性がないことを保証するものではありません。

**Endpoint** - Cilium

- Ciliumが管理するネットワークエンドポイントです。一般にはPodで、ローカルのデータパス／ポリシー状態を持ちます。
- エンドポイントIDはagent内でローカルに割り当てられるIDで、複数のエンドポイントで共有されるsecurity identityとは異なります。

**Envoy** - Cilium

- 設定されたHTTP／gRPCポリシー、L7の可視化、プロキシ経由のサービスルーティングにCiliumが使うオープンソースのプロキシです。
- DNSポリシーにはCiliumのDNSプロキシが使われます。KafkaのL7ポリシーは現在サポートされておらず、L7ルールを設定するたびにEnvoy instanceが起動するわけでもありません。

## F

**FQDN (Fully Qualified Domain Name)**

- DNS階層における位置を完全に示す絶対名です。末尾にroot dotを付けて書くこともあり、例は `www.example.com.` です。
- Ciliumの `toFQDNs` は学習した宛先IPを許可します。それだけでHTTPSサーバーを認証したり、共有IP上のすべてのHTTP Hostヘッダーの値を制限したりすることはできません。

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- ネットワーク仮想化で使うカプセル化プロトコルです。

**gRPC (gRPC Remote Procedure Call)**

- Googleが開発した高性能なRPC (Remote Procedure Call) frameworkです。

## H

**Hubble** - Cilium

- Ciliumのネットワーク可観測性レイヤーです。flowイベント、対応するプロトコルメタデータ、メトリクス、クエリーインターフェースを提供します。
- 履歴の保持量には上限があり、観測結果が失われたり絞り込まれたりする場合があります。アラート、永続ストレージ、自動応答には連携機能の設定が必要です。

## I

**Identity** - Cilium

- セキュリティに関係するラベルから導出される数値のセキュリティ識別子です。適用される割り当て範囲内で、複数のエンドポイントが同じsecurity identityを共有することがあります。
- CRD割り当てモードでは、`CiliumIdentity` の `security-labels` フィールドが正本です。予約済みidentityやノードローカルidentityのすべてが、クラスター単位のこのオブジェクトに記録されるわけではありません。

**IPAM (IP Address Management)** - ネットワーク

- IPアドレスの割り当て、追跡、回収を管理します。
- Ciliumの各モードは、cluster-pool、multi-pool、Kubernetes host-scope、クラウド固有モードなど、割り当ての担当主体やデータソースが異なります。プラットフォーム名が別の `ipam.mode` 値に対応するとは限りません。

**IPsec** - ネットワーク

- IP層での認証／完全性保護と、適切に設定した場合の機密性を実現する仕組みの総称です。
- Ciliumは対応するノード間通信の暗号化にIPsecを使います。鍵管理や経路ごとの制限も考慮してください。

**Istio**

- サービスメッシュを実装するオープンソースプラットフォームです。

## K

**Kafka**

- 分散イベントストリーミングプラットフォームです。現在もワークロードとして利用できますが、現行Ciliumは以前のKafkaトピック向けL7ポリシーAPIを提供していません。

**kube-proxy** - Kubernetes

- 対応するノードネットワーク機構を使ってServiceの仮想IP／ポート転送を実装するKubernetesコンポーネントです。
- Ciliumはこの機能をeBPFで置き換えられます。XDPアクセラレーションは任意で、選択した構成をプラットフォームがサポートしている必要があります。

**Kubernetes**

- コンテナ化アプリケーションのデプロイ、スケーリング、管理を自動化するオープンソースプラットフォームです。

## L

**L2 (Layer 2)**

- OSIモデルのデータリンク層です。

**L3 (Layer 3)**

- OSIモデルのネットワーク層です。

**L4 (Layer 4)**

- OSIモデルのトランスポート層です。

**L7 (Layer 7)**

- OSIモデルのアプリケーション層です。

**LoadBalancer**

- トラフィックを分散する機能です。Kubernetesの `type: LoadBalancer` はコントローラー／プロバイダーに実装を要求しますが、外部ロードバランサーが必ず作成されるとは限りません。

## M

**MAC (Media Access Control) Address**

- インターフェースに割り当てられるリンク層アドレスです。
- アドレスはローカル管理用に設定されたり、変更されたりすることがあります。一意性や真正性を前提にしないでください。

**mTLS (mutual TLS)**

- 通常、双方が相手の証明書を検証して認証するTLSです。
- peer認証とアプリケーション認可は別の機能です。Ciliumの帯域外mutual authenticationとBeta版ztunnelのworkload mTLSは別々の機能であり、通信を保護する性質も異なります。

**MTU (Maximum Transmission Unit)**

- リンク／インターフェース上で断片化なしに転送できる最大のネットワーク層パケットサイズです。IPヘッダーを含み、リンク層ヘッダーは含みません。
- Path MTUは経路によって制約されます。トンネル／暗号化のオーバーヘッドは内側パケットの利用可能サイズに影響します。MTUはTCP MSSでもアプリケーションのペイロードサイズでもありません。

## N

**NAT (Network Address Translation)**

- IPパケット内のIPアドレス情報を書き換える処理です。

**NodePort**

- 対象ノードのアドレス上で割り当てられたノードポートを使ってServiceを公開する方式です。
- 到達性は、アドレス選択、トラフィックポリシー、ファイアウォール、プラットフォームのroutingによって決まります。NodePortを宣言しただけでインターネットからのアクセスが保証されるわけではありません。

## O

**OSI (Open Systems Interconnection) Model**

- ネットワーク通信を7つの抽象レイヤーに分類する概念モデルです。

**Overlay Network**

- 既存ネットワーク上に構築する仮想ネットワークです。

## P

**Pod**

- Kubernetesでデプロイできる最小のコンピューティング単位です。

**Proxy**

- ピア間の通信を仲介するコンポーネントです。物理的に独立したサーバーとは限りません。

## R

**RBAC (Role-Based Access Control)**

- ロールに基づいてシステムリソースへのアクセスを制御する方式です。

## S

**Service**

- 論理的なバックエンド群（多くの場合、ラベルで選択したPod群）へのアクセスを提供するKubernetesの抽象化です。
- 通常のClusterIP Serviceには仮想IPがありますが、headless Serviceにはありません。ExternalNameはDNSエイリアスを使い、セレクターを持たないServiceではEndpointSliceを手動管理できます。

**SNAT (Source Network Address Translation)**

- パケットの送信元IPアドレスを書き換えるNATの方式です。

**Socket**

- ネットワーク通信またはローカルのプロセス間通信に使う、OS上の通信エンドポイントです。

## T

**TCP (Transmission Control Protocol)**

- 信頼性の高いバイトストリームを提供する、接続指向のトランスポートプロトコルです。

**TLS (Transport Layer Security)**

- ネットワーク上の通信を保護する暗号プロトコルです。

## U

**UDP (User Datagram Protocol)**

- コネクションレス型のトランスポートプロトコルです。

## V

**VETH (Virtual Ethernet)**

- 通常はペアで作成される仮想Ethernetデバイスです。

**VNI (VXLAN Network Identifier)**

- VXLANヘッダー内の24ビットフィールドです。
- Ciliumはオーバーレイメタデータにidentity情報を格納できますが、このフィールドの幅は数百万のテナントネットワークを個別に構成できることを意味しません。

**VTEP (VXLAN Tunnel Endpoint)**

- VXLANパケットのカプセル化とカプセル化解除を行うエンドポイントです。

**VXLAN (Virtual Extensible LAN)** - ネットワーク

- レイヤー3ネットワーク上にレイヤー2ネットワークを重ねるネットワーク仮想化技術です。
- Ciliumのオーバーレイネットワーキングモードの1つです。

## W

**WireGuard** - ネットワーク

- Ciliumが対応するノード間通信に使うVPNトンネルプロトコルです。
- 同一ノード上のPod通信はノードトンネルでは暗号化されません。外部通信と任意のノード暗号化にもそれぞれ制限があります。IPsecとの性能比較には、条件をそろえた測定が必要です。

## X

**XDP (eXpress Data Path)** - eBPF

- パケット処理フックです。native XDPは対応するネットワークドライバーの受信pathで動作します。
- PASSはネットワークスタックへの処理継続を意味します。他のアクションではパケットの破棄、送信、リダイレクトが可能です。CiliumのXDPアクセラレーションは任意機能であり、すべての環境でのスループットやDDoS防御を保証するものではありません。

## 主な参考資料

- [Cilium identities](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/security-identities.rst)
- [CiliumIdentity schema](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/cilium_operator.rst)
- [Identity management modes](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC addressing / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## クイズ

[トピッククイズ](../../quizzes/networking/cilium/glossary-quiz.md)
