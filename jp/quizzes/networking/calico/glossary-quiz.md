# Calico 用語集クイズ

> **関連ドキュメント**: [Calico 用語集](../../../networking/calico/glossary.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico アーキテクチャにおける Felix の主な役割は何ですか？
   - A) etcd データベースを管理する
   - B) 各 node 上でネットワークポリシールールとルートをプログラミングする
   - C) Service トラフィックをロードバランシングする
   - D) Service の DNS 名前解決を提供する

<details>
<summary>回答を表示</summary>

**回答: B) 各 node 上でネットワークポリシールールとルートをプログラミングする**

**解説:**
Felix は Calico の node ごとのエージェント（DaemonSet として実行）であり、各 node 上でネットワークポリシールール（iptables または eBPF）、ルート、ACL をプログラミングします。データストアを監視してポリシーと endpoint の更新を検知し、それらをカーネルレベルのルールに変換します。

</details>

2. BIRD とは何の略で、Calico ではどのような機能を果たしますか？
   - A) Binary Internet Routing Daemon - コンテナ DNS を管理する
   - B) BIRD Internet Routing Daemon - BGP を通じてルーティング情報を配布する
   - C) Basic Internal Route Distribution - Service discovery を処理する
   - D) Broadcast IP Routing Distributor - マルチキャストトラフィックを管理する

<details>
<summary>回答を表示</summary>

**回答: B) BIRD Internet Routing Daemon - BGP を通じてルーティング情報を配布する**

**解説:**
BIRD（BIRD Internet Routing Daemon - 再帰的頭字語）は、node 間でルーティング情報を配布するために Calico が使用する BGP デーモンです。BGP ピアリングセッションを確立し、Pod CIDR ルートをアドバタイズすることで、オーバーレイカプセル化なしに直接的な Pod 間通信を実現します。

</details>

3. Calico デプロイメントにおける Typha の機能は何ですか？
   - A) Pod 間トラフィックを暗号化する
   - B) データストアの更新をキャッシュし、Felix インスタンスへファンアウトする
   - C) Ingress のロードバランシングを提供する
   - D) 証明書ローテーションを管理する

<details>
<summary>回答を表示</summary>

**回答: B) データストアの更新をキャッシュし、Felix インスタンスへファンアウトする**

**解説:**
Typha は、Felix インスタンスとデータストア（Kubernetes API または etcd）の間でキャッシュプロキシとして機能します。複数の Felix インスタンスからの watch を単一の watch に集約し、その後すべての接続済み Felix デーモンに更新を配布することで、データストアの負荷を軽減します。

</details>

4. Calico における IPPool と IPAM の違いは何ですか？
   - A) 名前が異なるだけで、同じもの
   - B) IPPool は利用可能な CIDR 範囲を定義し、IPAM はそれらの範囲からの割り当てを管理する
   - C) IPPool は IPv4 用で、IPAM は IPv6 用
   - D) IPPool は IPAM に置き換えられ非推奨になっている

<details>
<summary>回答を表示</summary>

**回答: B) IPPool は利用可能な CIDR 範囲を定義し、IPAM はそれらの範囲からの割り当てを管理する**

**解説:**
IPPool は、NAT やカプセル化設定とともに、Pod への割り当てに利用可能な IP アドレス範囲（CIDR）を定義する Calico リソースです。IPAM（IP Address Management）は、これらのプールから個々の IP を Pod や node に実際に割り当てる処理を管理するシステムです。

</details>

5. GlobalNetworkPolicy は Kubernetes NetworkPolicy とどのように異なりますか？
   - A) GlobalNetworkPolicy は IPv6 でのみ機能する
   - B) GlobalNetworkPolicy はクラスター全体をスコープとし、tier や deny ルールなどの追加機能をサポートする
   - C) GlobalNetworkPolicy は Kubernetes NetworkPolicy と同様に namespace をスコープとする
   - D) GlobalNetworkPolicy は非推奨である

<details>
<summary>回答を表示</summary>

**回答: B) GlobalNetworkPolicy はクラスター全体をスコープとし、tier や deny ルールなどの追加機能をサポートする**

**解説:**
GlobalNetworkPolicy は、namespace の制限なしにクラスター全体へ適用される Calico 固有のリソースです。Kubernetes NetworkPolicy と異なり、明示的な deny ルール、順序付けのためのポリシー tier、アプリケーションレイヤー（L7）ルール、HostEndpoint など namespace に属さないリソース用のセレクターをサポートします。

</details>

6. Calico のポリシーモデルにおける Tier とは何ですか？
   - A) トラフィックを分離するためのネットワークセグメント
   - B) ポリシー評価順序を制御する階層的なグループ化
   - C) Calico Enterprise の料金レベル
   - D) ネットワーク暗号化の種類

<details>
<summary>回答を表示</summary>

**回答: B) ポリシー評価順序を制御する階層的なグループ化**

**解説:**
Tier は、Calico ネットワークポリシーを整理し、順序付ける方法を提供します。上位の Tier にあるポリシーは、下位の Tier より先に評価されます。これにより、アプリケーションチームのポリシーより優先されるプラットフォームレベルのセキュリティポリシーなどのパターンが可能となり、マルチテナントのポリシー管理をサポートします。

</details>

7. Calico において WorkloadEndpoint は何を表しますか？
   - A) Kubernetes Service endpoint
   - B) Pod または VM ワークロードに関連付けられたネットワークインターフェース
   - C) 外部 API endpoint
   - D) ストレージマウントポイント

<details>
<summary>回答を表示</summary>

**回答: B) Pod または VM ワークロードに関連付けられたネットワークインターフェース**

**解説:**
WorkloadEndpoint は、ワークロード（Pod、VM、またはコンテナ）に接続されたネットワークインターフェースを表します。インターフェースの IP アドレス、実行されるホスト、ポリシー選択用のラベル、適用される profile/ポリシーに関する情報を含みます。Calico は Pod 用の WorkloadEndpoint を自動的に作成します。

</details>

8. Calico における BGPPeer と BGPConfiguration の関係は何ですか？
   - A) 同じリソースのエイリアスである
   - B) BGPConfiguration はグローバル BGP 設定を行い、BGPPeer は特定のピアリングセッションを定義する
   - C) BGPPeer は内部ピア用、BGPConfiguration は外部用
   - D) BGPConfiguration は BGPPeer に置き換えられ非推奨になっている

<details>
<summary>回答を表示</summary>

**回答: B) BGPConfiguration はグローバル BGP 設定を行い、BGPPeer は特定のピアリングセッションを定義する**

**解説:**
BGPConfiguration は、AS 番号、node 間メッシュの有効化、ロギングなど、クラスター全体の BGP 設定を定義するグローバルリソースです。BGPPeer リソースは、IP アドレス、AS 番号、node セレクターを含め、外部ルーターまたは route reflector との特定の BGP ピアリング関係を定義します。

</details>

9. Calico の NetworkSet とは何ですか？また、Cilium での同等機能は何ですか？
   - A) Service のグループ。Cilium ServiceGroup に相当する
   - B) ポリシーで使用する名前付き IP アドレス/CIDR セット。CIDR ルールを持つ Cilium CiliumNetworkPolicy に類似する
   - C) namespace のコレクション。Cilium ClusterPolicy に相当する
   - D) DNS ゾーン設定。Cilium DNSPolicy に相当する

<details>
<summary>回答を表示</summary>

**回答: B) ポリシーで使用する名前付き IP アドレス/CIDR セット。CIDR ルールを持つ Cilium CiliumNetworkPolicy に類似する**

**解説:**
NetworkSet は、ネットワークポリシーから参照できる、IP アドレス、CIDR、またはドメインの名前付きコレクションを定義する Calico リソースです。同じ外部 IP のセットが複数のポリシーに現れる場合、これによりポリシー管理が簡素化されます。Cilium は、CiliumNetworkPolicy の CIDR ベースルールを通じて同様の機能を実現します。

</details>

10. Calico における HostEndpoint の目的は何ですか？
    - A) コンテナ endpoint を定義する
    - B) ホストインターフェース（Pod 以外のトラフィック）にネットワークポリシーを適用する
    - C) ホスト用の DNS を設定する
    - D) node ラベルを管理する

<details>
<summary>回答を表示</summary>

**回答: B) ホストインターフェース（Pod 以外のトラフィック）にネットワークポリシーを適用する**

**解説:**
HostEndpoint は、ホスト node 自体にあるネットワークインターフェース（Pod ではない）を表します。これにより、Calico ネットワークポリシーはホストプロセスへの、およびホストプロセスからのトラフィックを制御でき、Pod として実行されない kubelet、SSH、その他のシステムデーモンといった node レベルの Service を保護できます。

</details>
