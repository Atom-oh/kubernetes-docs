# 用語集と略語

> **最終更新**: February 22, 2026

このドキュメントでは、Cilium に関連する主要な用語と略語を説明します。この用語集は、Cilium、eBPF、Kubernetes、およびネットワーキングの概念を理解するのに役立ちます。

## 用語のカテゴリ

用語は次のカテゴリに分類されます。
- 青: **Cilium 関連の用語**
- オレンジ: **eBPF 関連の用語**
- 緑: **Kubernetes 関連の用語**
- 紫: **ネットワーキング関連の用語**
- 白: **一般用語**

## A

**API (Application Programming Interface)** - 一般
- アプリケーション間の通信を可能にするインターフェース定義の集合

**AWS ENI (Elastic Network Interface)** - ネットワーキング
- Amazon Web Services が提供する仮想ネットワークインターフェース
- Cilium の AWS ENI IPAM モードで使用される

**ARP (Address Resolution Protocol)** - ネットワーキング
- IP アドレスを MAC アドレスに変換するプロトコル
- L2 ネットワークでの通信に不可欠なプロトコル

## B

**BGP (Border Gateway Protocol)** - ネットワーキング
- インターネット上でルーティング情報を交換するために使用される標準的な外部ゲートウェイプロトコル
- Cilium ではネイティブルーティングモードとして使用できる

**BPF (Berkeley Packet Filter)** - eBPF
- eBPF の前身であるパケットフィルタリング技術
- 元来、ネットワークパケットのキャプチャのために開発された

**BPF Maps** - eBPF
- eBPF プログラム内でデータを保存および取得するために使用されるキー・バリューストア
- ユーザースペースとカーネルスペース間のデータ共有に使用される

## C

**CGroup (Control Group)** - Kubernetes
- プロセスグループのリソース使用量を制限および分離する Linux カーネル機能
- コンテナのリソース制限に使用される

**CIDR (Classless Inter-Domain Routing)** - ネットワーキング
- IP アドレスの割り当ておよびルーティング集約の手法
- 例: 192.168.1.0/24 は、192.168.1.0 から 192.168.1.255 までの IP アドレス範囲を表す

**CNI (Container Network Interface)** - Kubernetes
- コンテナランタイムとネットワークプラグイン間の標準インターフェース
- Cilium は CNI 実装の 1 つ

**CoreDNS** - Kubernetes
- Kubernetes クラスターで一般的に使用される DNS サーバー
- サービスディスカバリーにおいて重要な役割を果たす

**CRD (Custom Resource Definition)** - Kubernetes
- Kubernetes API を拡張してカスタムリソースを定義する手法
- Cilium はネットワークポリシーなどを定義するために CRD を使用する

**Cilium** - Cilium
- eBPF をベースとしたオープンソースのネットワーキング、セキュリティ、およびオブザーバビリティソリューション
- Kubernetes CNI 実装として使用される

## D

**DNAT (Destination Network Address Translation)** - ネットワーキング
- パケットの宛先 IP アドレスを変更する NAT の種類
- ロードバランシングおよびポートフォワーディングに使用される

**DNS (Domain Name System)** - ネットワーキング
- ドメイン名を IP アドレスに変換するシステム
- Cilium は DNS ベースのネットワークポリシーをサポートする

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF
- Linux カーネル内でプログラムを安全に実行できる技術
- Cilium で使用される中核技術

**Endpoint** - Cilium
- Cilium でネットワークポリシーが適用されるワークロード単位
- 一般的には Kubernetes Pod に対応する

**Envoy** - Cilium
- L7 プロキシおよびサービスメッシュコンポーネント
- Cilium での L7 ポリシーの適用に使用される

## H

**Hubble** - Cilium
- Cilium のオブザーバビリティレイヤー
- ネットワークフローをリアルタイムで監視および分析するためのツール

## I

**IPAM (IP Address Management)** - ネットワーキング
- IP アドレスの割り当て、追跡、および管理を担うシステム
- Cilium は複数の IPAM モードをサポートする

**IPsec** - ネットワーキング
- IP パケットを暗号化してセキュアな通信を提供するプロトコルスイート
- Cilium ではノード間トラフィックの暗号化に使用できる

## K

**kube-proxy** - Kubernetes
- Kubernetes Service 抽象化を実装するネットワークプロキシ
- Cilium は kube-proxy を置き換えられる

## V

**VXLAN (Virtual Extensible LAN)** - ネットワーキング
- L3 ネットワーク上に L2 ネットワークをオーバーレイするネットワーク仮想化技術
- Cilium のオーバーレイネットワーキングモードの 1 つ

## W

**WireGuard** - ネットワーキング
- モダンで高速な VPN プロトコル
- Cilium ではノード間トラフィックの暗号化に使用できる

## X

**XDP (eXpress Data Path)** - eBPF
- ネットワークドライバーレベルでパケットを処理する eBPF 機能
- 非常に高性能なパケット処理を提供する

**DaemonSet**
- すべてのノードで Pod のコピーを実行する Kubernetes リソース

## E

**eBPF (extended Berkeley Packet Filter)**
- Linux カーネル内でプログラムを安全に実行できる技術

**Endpoint**
- Cilium でネットワークポリシーが適用されるネットワークエンドポイント（一般的には Pod）

**Envoy**
- L7 プロキシおよび通信バスとして使用されるオープンソースのエッジおよびサービスプロキシ

## F

**FQDN (Fully Qualified Domain Name)**
- ホストの完全修飾ドメイン名（例: www.example.com）

## G

**GENEVE (Generic Network Virtualization Encapsulation)**
- ネットワーク仮想化のためのカプセル化プロトコル

**gRPC (gRPC Remote Procedure Call)**
- Google が開発した高性能な RPC (Remote Procedure Call) フレームワーク

## H

**Hubble**
- Cilium のネットワーク可視化およびモニタリングコンポーネント

## I

**IPAM (IP Address Management)**
- IP アドレスの計画、追跡、および管理

**IPsec (Internet Protocol Security)**
- IP 通信のセキュリティのためのプロトコルスイート

**Istio**
- サービスメッシュを実装するオープンソースプラットフォーム

## K

**Kafka**
- 分散ストリーミングプラットフォーム

**kube-proxy**
- Kubernetes Service 抽象化を実装するネットワークプロキシ

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
- 複数のサーバーにトラフィックを分散するデバイスまたはサービス

## M

**MAC (Media Access Control) Address**
- ネットワークインターフェースに割り当てられる一意の識別子

**MTU (Maximum Transmission Unit)**
- ネットワーク経由で送信できる最大パケットサイズ

**mTLS (mutual TLS)**
- クライアントとサーバーの両方が証明書で相互に認証する TLS の拡張

## N

**NAT (Network Address Translation)**
- IP パケット内の IP アドレス情報を変更するプロセス

**NodePort**
- 各ノードの IP 上で静的ポートを公開する Kubernetes Service タイプ

## O

**OSI (Open Systems Interconnection) Model**
- ネットワーク通信を 7 つの抽象レイヤーに分類する概念モデル

**Overlay Network**
- 既存のネットワーク上に構築される仮想ネットワーク

## P

**Pod**
- Kubernetes における最小のデプロイ可能なコンピューティング単位

**Proxy**
- クライアントとサーバーの仲介役として機能するサーバー

## R

**RBAC (Role-Based Access Control)**
- ロールに基づいてシステムリソースへのアクセスを制御する手法

## S

**Service**
- Pod のセットに安定したエンドポイントを提供する Kubernetes の抽象化

**SNAT (Source Network Address Translation)**
- パケットの送信元 IP アドレスを変更する NAT の種類

**Socket**
- ネットワーク経由のプロセス間通信のためのエンドポイント

## T

**TCP (Transmission Control Protocol)**
- 信頼性の高いバイトストリームを提供する接続指向のトランスポートプロトコル

**TLS (Transport Layer Security)**
- ネットワーク上の通信を保護する暗号化プロトコル

## U

**UDP (User Datagram Protocol)**
- コネクションレス型のトランスポートプロトコル

## V

**VETH (Virtual Ethernet)**
- 通常はペアで作成される仮想 Ethernet デバイス

**VNI (VXLAN Network Identifier)**
- VXLAN ネットワークを識別する 24 ビットの識別子

**VTEP (VXLAN Tunnel Endpoint)**
- VXLAN パケットのカプセル化およびデカプセル化を担うエンドポイント

**VXLAN (Virtual Extensible LAN)**
- L3 ネットワーク上に L2 ネットワークをオーバーレイするネットワーク仮想化技術

## W

**WireGuard**
- モダンで高速かつセキュアな VPN トンネルプロトコル

## X

**XDP (eXpress Data Path)**
- 非常に高速なネットワークパケット処理のための eBPF ベース技術

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../../quizzes/networking/cilium/glossary-quiz.md)に挑戦してください。
