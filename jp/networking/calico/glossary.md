# Calico 用語集

> **確認済みの基準バージョン**: Calico 3.32.2。比較用語は Cilium 1.20.1 と照合
> **最終更新**: 2026年9月12日

このドキュメントでは、Calico のネットワークとセキュリティに関する主要な用語や概念を説明します。Kubernetes 環境で Calico を適切に導入、運用するには、これらの用語を理解しておく必要があります。

## 用語の分類

用語は次のカテゴリに分類されています。
- **ネットワーク用語** - 一般的なネットワーク概念
- **Calico のコンポーネント** - Calico 固有のコンポーネントやサービス
- **ポリシー用語** - ネットワークポリシーとセキュリティの概念
- **運用用語** - 運用と管理に関する概念

---

## ネットワーク用語

### A

**AS (Autonomous System、自律システム)**
- 単一の組織が管理し、インターネットに対して共通のルーティングポリシーを提示する IP ネットワークとルーターの集合です。Calico では、AS 番号を BGP ピアリングの設定に使用します。

**ASN (Autonomous System Number、自律システム番号)**
- BGP で使われる識別子です。RFC 6996 は、プライベート利用範囲として **64512～65534** と **4200000000～4294967294** を予約しています。プライベート ASN は管理ドメイン内で再利用できるため、グローバルに一意なパブリック割り当てとして扱ってはいけません。

### B

**BGP (Border Gateway Protocol)**
- 自律システム間（eBGP）と、1つの AS 内（iBGP）の両方で使われるルーティングプロトコルです。Calico は BGP を使って Pod や Service のルートを配布できますが、すべての Calico データプレーンやオーバーレイ設定で必要なわけではありません。

**Block Affinity (ブロックアフィニティ)**
- IPAM ブロックと、その所有者（一般にはノード）との関連付けです。strict affinity を使わない場合、条件を満たす割り当てが別ノードのブロックから借用されることがあります。アフィニティがあっても、ノード上の Pod アドレスがすべてそのノード所有のブロックから割り当てられるとは限りません。リソースの種類と状態、および実際の割り当て処理を確認してください。

### C

**CIDR (Classless Inter-Domain Routing)**
- IP アドレスの割り当てと IP ルーティングに使う方式です。例: 10.244.0.0/16 は 65,536 個の IP アドレスの範囲を表します。

**CNI (Container Network Interface)**
- コンテナネットワーク接続と関連プラグインを設定するための仕様です。Calico は CNI 実装を提供します。動作は Linux ネットワークと、サポート対象の Windows HNS 設定とで異なります。

**Conntrack (Connection Tracking、接続追跡)**
- ステートフルポリシーや NAT のために通信フローを追跡する状態情報です。標準の Linux データプレーンはカーネルの接続追跡を使います。一方、Calico の BPF データプレーンは BPF conntrack map も管理するため、両者を同じ調整対象として扱うことはできません。

### D

**DNAT (Destination NAT、宛先 NAT)**
- パケットの宛先 IP アドレスを書き換えるネットワークアドレス変換です。Kubernetes では Service のロードバランシングに使われます。

**Direct Routing (直接ルーティング)**
- 異なるノード上の Pod 間のトラフィックを、カプセル化せずに直接ルーティングするネットワークモードです。基盤ネットワークが Pod CIDR のルーティングに対応している必要があります。

**DSR (Direct Server Return)**
- バックエンドからの応答が、元の転送ノードを経由せずに返る Service ロードバランシング方式です。Calico BPF は、特定のネットワーク条件と送信元アドレス条件の下で DSR をサポートします。すべてのクラウドロードバランサーと互換性があるわけではありません。

### E

**eBPF (extended Berkeley Packet Filter)**
- Linux カーネルをプログラムする仕組みです。Calico の BPF データプレーンは、ネットワーク、ポリシー、Service の処理に利用します。互換性と性能はカーネル、プラットフォーム、ワークロードによって異なり、どの環境でもオーバーヘッドが下がることを保証するものではありません。

**Encapsulation (カプセル化)**
- ネットワークパケットを別のパケットの中に包む処理です。Calico はオーバーレイネットワーク向けに IPIP と VXLAN のカプセル化をサポートします。

### F

**FQDN (Fully Qualified Domain Name、完全修飾ドメイン名)**
- 完全な DNS 名です。ドキュメントに記載されている Calico のドメインベースの Egress ポリシー機能には商用エディションが必要です。OSS の NetworkSet に登録した CIDR が DNS ルールになるわけではありません。また、別途統合する HTTP アプリケーション層ポリシーとも混同しないでください。

**Full Mesh (フルメッシュ)**
- N 台の参加ノードが相互にすべてピアリングする BGP トポロジです。セッション数は N(N−1)/2 です。処理能力は接続の増減、ルート数、ハードウェアに依存し、100 ノードがプロトコル上の一律な上限というわけではありません。

### I

**IPAM (IP Address Management、IP アドレス管理)**
- IP アドレスを割り当て、追跡、管理するシステムです。Calico にはブロック単位で割り当てる組み込み IPAM があります。

**IPIP (IP-in-IP)**
- IP カプセル化方式です。Calico の IPv4 IP-in-IP モードでは、外側に20バイトの IPv4 ヘッダーを追加し、基盤ネットワークで IP プロトコル4を許可する必要があります。UDP ポートではありません。

**IPset**
- IP アドレス、ネットワーク、ポートの集合を保存する Linux カーネル機能です。Calico は ipset を使って、複数のアドレスに対するトラフィック照合を効率化します。

**iptables**
- Linux Netfilter のパケットフィルタリングや NAT ルールを操作するユーザー空間インターフェイスです。iptables の legacy バックエンドと nft バックエンドは、Calico の独立したネイティブ Nftables データプレーンとは異なります。iptables のバックエンドを変更しても、そのデータプレーンが選択されるわけではありません。

### M

**MTU (Maximum Transmission Unit、最大転送単位)**
- リンクまたは経路で扱える最大パケットサイズです。実効アンダーレイ MTU が1500バイトの場合の Calico MTU の例は、IPv4 IPIP が1480、IPv4/IPv6 VXLAN が1450/1430、IPv4/IPv6 WireGuard が1440/1420です。実際の最小経路 MTU と使用モード、プラットフォーム固有の制約を確認してください。これらは計算例であり、性能測定値ではありません。

### N

**NAT (Network Address Translation、ネットワークアドレス変換)**
- パケットヘッダー内の IP アドレス情報を書き換える処理です。Calico は Pod の Egress と Service の実装に NAT を使います。

**nftables**
- Calico のネイティブ Nftables モードで使う Linux パケットフィルタリングフレームワークです。これは、NFT バックエンドを使う Iptables とは別の Installation データプレーン選択肢です。

### O

**Overlay Network (オーバーレイネットワーク)**
- 既存の物理ネットワーク上に構築する仮想ネットワークです。直接ルーティングができない環境向けに、Calico は IPIP と VXLAN のオーバーレイモードをサポートします。

### R

**Route Reflector (ルートリフレクター)**
- クライアントにルートを反映する BGP スピーカーです。総ノード数を N、相互にフルメッシュ接続するリフレクター数を r とし、各クライアントが r 台すべてとピアリングする場合、セッション数は r(N−r)+r(r−1)/2 です。N=100、r=2 なら、フルメッシュの4,950ではなく197セッションです。リフレクターが1台の場合は99セッションですが、リフレクターの冗長性はありません。

**Routing Table (ルーティングテーブル)**
- ネットワーク宛先への経路を保存するデータ構造です。Calico は Pod CIDR の経路を Linux カーネルのルーティングテーブルに設定します。

### S

**SNAT (Source NAT、送信元 NAT)**
- パケットの送信元 IP アドレスを書き換えるネットワークアドレス変換です。Pod の Egress トラフィックやマスカレードに使われます。

### V

**veth (Virtual Ethernet)**
- CNI プラグインが作成することの多い Linux 仮想インターフェイスのペアです。Pod のネットワーク名前空間とホストを接続します。すべての Pod に対して Felix が作るわけではありません。hostNetwork Pod、Windows、その他のネットワーク接続方式では異なります。

**VXLAN (Virtual Extensible LAN)**
- Layer 3 基盤上で Layer 2 ネットワークを拡張するカプセル化プロトコルです。IPIP よりクラウドとの互換性が高い一方、オーバーヘッドも大きくなります。

### W

**WireGuard**
- 設定済みで対応可能なノードピア間のサポート対象トラフィックに使う暗号化トンネルプロトコルです。同一ノード内の通信、非対応ピア、すべての外部トラフィックを自動的に暗号化するものではなく、アプリケーションの mTLS とは異なります。

**Workload Endpoint**
- ワークロードのインターフェイスを表す、名前空間に属する Calico の表現です。アドレス、ラベル、ポリシー計算で使うプロファイル参照を持ちます。通常はオーケストレーターやプラグインが管理するもので、適用されたすべてのポリシー判断を保存した一覧ではありません。

---

## Calico のコンポーネント

### B

**BIRD (BIRD Internet Routing Daemon)**
- BGP を使う Calico プロファイルのルーティングデーモンです。Calico 3.32.2 では、パッチ適用版 BIRD 1.6.8 系統を使用します。任意の upstream BIRD 2 の設定と同等ではありません。

### C

**calicoctl**
- Calico リソースを管理するコマンドラインツールです。状態の表示、ポリシーの設定、IPAM の管理、トラブルシューティングに使います。

**Calico API Server**
- Calico API と Kubernetes API サーバーを統合する機能です。OSS で利用できます。ユーザー向けの projectcalico.org/v3 API と、バックエンドの CRD または native-API モードは、設定したインストール方式によって異なります。すべての API グループが別名として同じように使えると考えず、保守されているインストールガイドに従ってください。

**CNI Plugin**
- Calico の CNI 仕様を実装するバイナリです。Pod ネットワーク（veth ペア、経路、IP 割り当て）を設定します。

**confd**
- Calico データストアから BIRD 設定ファイルを生成する設定管理ツールです。変更を監視し、BIRD の設定を動的に更新します。

### D

**Dikastes**
- Istio/Envoy と組み合わせて使うアプリケーション層ポリシーの判定コンポーネントです。トラフィックを処理するのは Envoy であり、Envoy が Dikastes に認可を問い合わせます。Dikastes 自体は転送プロキシではありません。この統合は、バージョン別の前提条件とともに Calico OSS 向けに文書化されています。

### F

**Felix**
- ノードごとに動作し、選択されたデータプレーン、ポリシー、関連する経路を設定するエージェントです。Pod インターフェイスと IPAM は CNI プラグインが設定します。Felix はパケットごとに処理するユーザー空間の転送経路ではありません。

### G

**Goldmane / Whisker**
- OSS のフロー集約 API が Goldmane、Web UI が Whisker です。導入方法、アクセス制御、プレビュー段階かどうかは、基本的な Felix メトリクスとは別に確認してください。

### K

**kube-controllers**
- ノード/IPAM 処理やデータストア依存の同期など、Kubernetes と Calico の調整を行うコントローラー群です。有効なコントローラーの種類はインストール方式とデータストアによって異なります。コントローラーの種類を列挙しても、Kubernetes データストアを使うすべての環境でその全てが動作するという意味ではありません。

### T

**Tigera Operator**
- Calico のインストールとライフサイクルを管理する Kubernetes Operator です。CRD を通じて宣言的な設定を提供します。

**Typha**
- Felix ごとの watch 負荷を減らす、データストア更新のファンアウトおよびキャッシュサービスです。複数種類の watch/syncer と複数レプリカを利用できます。クラスター全体に対する唯一の watch や、自動的なポリシーフェデレーションサービスではありません。Operator によるスケーリングについては、上級編を参照してください。

---

## ポリシー用語

### A

**Action (アクション)**
- Calico ルールの評価結果です。Allow と Deny はその評価経路のポリシー評価を終了し、Log は評価を続けます。Pass は次に該当する Tier へ処理を渡し、最後に該当する Tier を過ぎるとプロファイルを評価します。Log 自体は Allow の判定ではありません。

**applyOnForward**
- HostEndpoint を通過する転送トラフィック向けの GlobalNetworkPolicy オプションです。HostEndpoint を作成する機能ではなく、preDNAT または doNotTrack ポリシーと併用する必要があります。ワークロードポリシーとホスト転送ポリシーでは対象範囲が異なります。

### D

**Default Deny (デフォルト拒否)**
- 選択した範囲で、実効ポリシーの組み合わせが許可しないトラフィックを拒否する状態です。依存関係とテスト済みの名前空間範囲を明確にして導入してください。範囲を確認せず、空のクラスター全体ポリシーを設定することは避けてください。

**DoNotTrack**
- doNotTrack を設定した GlobalNetworkPolicy は、HostEndpoint のトラフィックを接続追跡前に評価します。applyOnForward が必要です。ステートレスな戻り通信には明示的なルールが必要で、preDNAT と併用できません。

### E

**Egress (送信トラフィック)**
- Pod から外部へ向かうネットワークトラフィックです。Egress ポリシーは、Pod が通信できる宛先を制御します。

### G

**GlobalNetworkPolicy**
- 名前空間をまたぐワークロードや HostEndpoint を選択できる、クラスター範囲の Calico ポリシーです。実際に適用される対象範囲はセレクターで決まります。クラスター範囲であることは、すべての Pod に自動適用されることを意味しません。

**GlobalNetworkSet**
- IP アドレス/CIDR をラベル付きでまとめたクラスター範囲の集合です。ポリシーのセレクターで一致させられます。適切なグローバル名前空間の選択を行えば、名前空間付き Calico ポリシーからも参照できます。GlobalNetworkPolicy 専用ではありません。

### H

**Host Endpoint**
- ホストインターフェイスを表し、ホストポリシーや設定に応じて転送トラフィックのポリシーにも使われるリソースです。作成するとトラフィック処理が変わる場合があります。事前にポリシー、プロファイル、failsafe、管理アクセスを確認してください。

### I

**Ingress (受信トラフィック)**
- Pod に入ってくるネットワークトラフィックです。Ingress ポリシーは、Pod と通信できる送信元を制御します。

### N

**NetworkPolicy**
- 別個の API が2種類あります。Kubernetes の `networking.k8s.io/v1` NetworkPolicy と、Calico の `projectcalico.org/v3` NetworkPolicy です。Calico は Action、Order、Tier、セレクターを追加します。HTTP ルールには、OSS の Dikastes を含む別途サポートされたアプリケーション層統合が必要です。ドメインベースのルールにはエディション上の制約があります。

**NetworkSet**
- IP アドレスまたは CIDR をまとめた名前空間範囲の集合です。ネットワークポリシーで使用する外部エンドポイントをグループ化できます。

### O

**Order (評価順序)**
- 数値で表す評価優先度です。先に Tier の Order が評価され、その Tier 内でポリシーの Order が評価されます。順序が重要な場合は、同じ値に頼らず異なる優先度を明示してください。先行ポリシーの終端 Action によって、後続ポリシーが評価されない場合があります。

### P

**Pass**
- 現在の Tier の残りのポリシーを飛ばし、次に該当する Tier へ進みます。最後に該当する Tier の後はエンドポイントのプロファイルを評価します。最終的な Allow 判定ではありません。

**Profile (プロファイル)**
- エンドポイントが継承する共有ラベルです。プロファイルには従来型のポリシールールを含められますが、この使い方は非推奨であり、NetworkPolicy/GlobalNetworkPolicy の利用が推奨されます。プロファイルを Kubernetes RBAC として扱わないでください。

**Policy Selector (ポリシーセレクター)**
- ポリシーを適用するエンドポイントを決めるラベルベースの式です。Calico 固有のセレクター構文を使います（例: `app == 'web'`）。

**PreDNAT**
- preDNAT を設定した GlobalNetworkPolicy は、宛先 NAT の前に HostEndpoint の受信トラフィックを評価します。applyOnForward が必要で、doNotTrack および Egress のポリシー方向とは併用できません。

### S

**Staged Policy (ステージングポリシー)**
- 提案した変更の影響を評価するための、強制適用しないポリシーリソースです。文書化されたリソースや可観測性の前提条件を満たせば OSS でも利用できます。作成しただけで完全な判定ログが得られるとは限りません。

**Selector (セレクター)**
- ラベルに基づいてリソースを照合する式です。Calico はポリシー対象と送信元/宛先の照合の両方にセレクターを使います。

### T

**Tier**
- 順序を持つポリシーのグループです。数値の小さい Order が優先されます。Allow/Deny は終端アクション、Pass は処理の委譲です。選択された Tier 内に一致するルールがない場合は、通常 Deny である defaultAction が使われます。

---

## 運用用語

### A

**APIServer (Calico)**
- Calico API 統合を設定する Operator リソースです。Kubernetes コントロールプレーンそのものではなく、Enterprise 専用機能でもありません。API にアクセスするには、正しく設定した API 経路と RBAC が引き続き必要です。

### B

**Block (ブロック)**
- Calico IPAM の割り当て単位です。デフォルトのサイズは IPv4 が /26、IPv6 が /122 で、いずれも64アドレスを含みます。予約や割り当て制約によってワークロードが使える容量が減る場合があり、特に Windows では注意が必要です。

**Block Affinity (ブロックアフィニティ)**
- IPAM ブロックと、その所有者（一般にはノード）との関連付けです。strict affinity がなければ、条件を満たす割り当ては別ノードのブロックを借用する場合があります。ローカル Pod のアドレスがすべてローカル所有ブロック由来とは限りません。リソースの種類と状態、および実際の割り当て処理を確認してください。

### D

**Dataplane (データプレーン)**
- パケット処理を行う実装です。Calico は Linux の Iptables、Nftables、BPF と、サポート対象の Windows HNS 設定を提供します。その他の統合方式にはそれぞれ要件があります。

**Datastore (データストア)**
- Calico の設定や状態にアクセスするためのストレージ/API です。Kubernetes API データストア、またはサポート対象の直接 etcdv3 構成を使います。Kubernetes データストアが推奨されます。BPF など一部機能には追加のデータストア制約があります。

### F

**FelixConfiguration**
- クラスター全体のデフォルトや、サポートされるノード単位の上書きを含む Felix 設定用 API リソースです。メトリクス、ログ、データプレーンのオプションなどを制御します。Operator の Installation API の代わりにはなりません。

**Flow Logs (フローログ)**
- 集約した通信フローの記録です。パケットキャプチャやプロセスログとは異なります。現在の OSS Operator/Helm インストールでは Goldmane と Whisker を利用できますが、フローログのガイドではこの機能をテクニカルプレビューとしています。

### H

**Health Check (ヘルスチェック)**
- コンポーネントの Liveness/Readiness 状態を報告します。Felix は設定ポート（デフォルト9099）でヘルスエンドポイントを公開できます。コンポーネントが正常でも、アプリケーションへの到達性やポリシー適用が正しいとは限りません。

### I

**IPPool**
- アドレス範囲、カプセル化/NAT、割り当て対象を定義する Calico 独立リソースです。Calico IPAM は、サポート対象の Workload、Tunnel、LoadBalancer 用途に割り当てられます。Kubernetes Node の PodCIDR と同じものではありません。CIDR と blockSize は変更できません。

**Installation**
- Calico のデプロイ設定を定義する Tigera Operator の CRD です。ネットワークモード、リソース、コンポーネント設定を指定します。

### M

**Metrics (メトリクス)**
- コンポーネントごとに有効化方法とポートが異なる Prometheus 統計情報です。Felix のデフォルトは9091、Typha のデフォルトも9091ですが、明示的に9093へ設定する構成が一般的です。kube-controllers のデフォルトは9094です。実際の設定とメトリクスの種類を確認してください。

### P

**Pod CIDR**
- Pod 用のアドレス範囲です。クラスター範囲を指す場合と、Kubernetes Node に割り当てられた範囲を指す場合があります。Calico IPPool は別リソースであり、Node PodCIDR との関係は IPAM によって異なります。VPC CNI を使う場合、Calico をポリシー専用で使っても Pod IP は割り当てません。

### R

**Rollout (ロールアウト)**
- コンポーネントを制御しながら更新することです。Operator の調整とローリング更新設定は可用性の管理に役立ちますが、トラフィックの中断がないことや、スキーマ/データ変更を元に戻せることを保証しません。

### T

**TigeraStatus**
- Calico コンポーネントの状態を報告する CRD です。デプロイの健全性と設定状態を表示します。

---

## Calico と Kubernetes の用語対応

| Kubernetes の用語 | Calico の相当用語 | 注記 |
|-----------------|-------------------|-------|
| NetworkPolicy | Calico NetworkPolicy | API グループとリソースは別で、ルールの意味も異なる |
| - | GlobalNetworkPolicy | クラスター範囲のポリシー（Calico 固有） |
| - | Tier | ポリシー階層（Calico 固有） |
| Service CIDR | N/A | Calico は K8s Service CIDR を尊重する |
| Pod CIDR | Calico IPAM 使用時の IPPool | Node PodCIDR の別名でも、自動的に一致するものでもない |
| Node | Calico Node | 関連するノード情報。ライフサイクルと表現はデータストアによって異なる |
| Namespace | Namespace | Calico ポリシーでは Namespace を選択条件にできる |
| Labels | Labels | 同じラベル構文をセレクターで使う |
| Pod ネットワークインターフェイス | WorkloadEndpoint | Service Endpoint/EndpointSlice でも、適用済みポリシーの全一覧でもない |
| - | HostEndpoint | ホストインターフェイス向けポリシー（Calico 固有） |

---

## Calico と Cilium の用語比較

これは機能上の比較であり、リソースが相互に置き換えられることや、機能が保証されることを意味しません。ポリシーを移行する前に、モード、プラットフォーム、インストール済みバージョンを確認してください。

| 概念 | Calico | Cilium 1.20.1 との比較 |
| --- | --- | --- |
| ノードエージェント | Felix | Cilium Agent |
| BGP | BGP 対応プロファイルの BIRD | 組み込み BGP Control Plane が到達可能性を広告する。データパスをプログラムしたり、内部ルーティングを確立したりするものではない |
| データストアのファンアウト | Typha | 同一の Typha コンポーネント/API はない |
| Pod IP の割り当て | IPPool + 選択した IPAM | Cilium の IPAM モードによって異なる。共通の単一プール API はない |
| 名前空間ポリシー | Calico NetworkPolicy | CiliumNetworkPolicy。どちらも標準 Kubernetes NetworkPolicy とは異なる |
| クラスターポリシー | GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy。ルール/順序の意味は異なる |
| 再利用可能な外部 CIDR | NetworkSet / GlobalNetworkSet | クラスター範囲の CiliumCIDRGroup。CIDR ルール内の cidrGroupRef または cidrGroupSelector から参照する。CiliumIPSet ではない |
| ポリシー Tier | Calico Tier | Calico Tier と同一の API はない。他のポリシー API にはそれぞれ順序規則がある |
| ワークロードインターフェイス | WorkloadEndpoint | CiliumEndpoint。ライフサイクル/状態の意味が異なる |
| ホスト保護 | 転送ルールを設定した HostEndpoint ポリシーを含む | nodeSelector ポリシーを使う Linux host firewall。転送対象範囲は同一ではない |
| データプレーン | Linux Iptables/Nftables/BPF、Windows HNS | Linux eBPF の要件がある。この比較を根拠に Windows をサポート対象のベータ版と説明してはいけない |
| 暗号化 | サポート対象のピア経路に対する OSS WireGuard | WireGuard または IPsec。モード/プラットフォーム固有の制約がある |
| L7 ポリシー | OSS 向けに文書化された独立した Istio/Envoy/Dikastes 統合 | Envoy ベースのポリシー機能。独自の前提条件がある |
| フローメトリクス | Goldmane/Whisker とコンポーネントメトリクス | Hubble とコンポーネントメトリクス |
| コントローラー | kube-controllers / Tigera Operator | Cilium Operator。責務は一対一で対応しない |
| CLI | calicoctl | cilium と agent 側の cilium-dbg は役割が異なる |

Calico の Windows 対応機能は Linux より限定的です。たとえば、文書化された VXLAN/BGP の制限を伴う IPv4 HNS が対象であり、WireGuard/eBPF/HostEndpoint が同等に使えるわけではありません。この比較から、性能、成熟度、コミュニティ規模の無条件な優劣を裏付ける根拠は得られません。具体的なワークロードと運用要件を比較してください。

---

## 関連項目

### アーキテクチャの詳細
- **Felix**: [第2部: アーキテクチャ](02-architecture.md) を参照
- **BGP の設定**: [第4部: BGP の詳細](04-bgp-deep-dive.md) を参照
- **Typha のスケーリング**: [第7部: 上級トピック](07-advanced-topics.md) を参照

### ネットワークポリシー
- **Kubernetes NetworkPolicy**: [第5部: ネットワークポリシー](05-network-policy.md) を参照
- **GlobalNetworkPolicy**: [第5部: ネットワークポリシー](05-network-policy.md) を参照
- **Tier ベースのポリシー**: [第5部: ネットワークポリシー](05-network-policy.md) を参照

### 運用
- **インストール方法**: [第9部: 運用](09-operations.md) を参照
- **calicoctl コマンド**: [第9部: 運用](09-operations.md) を参照
- **トラブルシューティング**: [第9部: 運用](09-operations.md) を参照

### EKS との統合
- **VPC CNI + Calico**: [第8部: EKS との統合](08-eks-integration.md) を参照
- **インストール方法**: [第8部: EKS との統合](08-eks-integration.md) を参照

---

## 主な参照資料

- [Calico リソースリファレンス](https://docs.tigera.io/calico/latest/reference/resources/)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu)
- [RFC 6996 プライベート ASN](https://www.rfc-editor.org/rfc/rfc6996.txt)
- [Cilium CIDR group API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/v2/cidrgroups_types.go)
- [Cilium BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Cilium host firewall](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/host-firewall.rst)

## クイズ

この章で学んだ内容を確認するには、[用語集クイズ](../../quizzes/networking/calico/glossary-quiz.md)に挑戦してください。
