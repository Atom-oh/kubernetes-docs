# Cilium IPAM と Network Policy のクイズ

> **対応バージョン**: Cilium 1.20.3 · 2026-10-16

## IPAM

1. **プラットフォーム固有の上書きがない場合、一般的なデフォルトの IPAM モードと割り当て方式は何ですか？**
   - A) kubernetes。各 Pod が Kubernetes API に IP アドレスを要求する
   - B) cluster-pool。Operator がノード CIDR を割り当て、agent がローカルで Pod IP を割り当てる
   - C) crd。各 Pod が CiliumPodIPPool を作成する
   - D) すべてのプラットフォームで eni

   <details>
   <summary>回答を表示</summary>

   **回答: B) cluster-pool。Operator がノード CIDR を割り当て、agent がローカルで Pod IP を割り当てる**

   cluster-pool は CiliumNode を使ってノード単位のプレフィックスを割り当てます。Pod ごとに中央へアドレスを要求する方式ではありません。また、プラットフォームのプロファイルによって別のバックエンドが選ばれる場合があります。

   </details>

2. **Operator による cluster-pool 割り当てではなく、Kubernetes の Node 状態からノードプレフィックスを取得するモードはどれですか？**
   - A) cluster-pool
   - B) kubernetes（host scope）
   - C) multi-pool のみ
   - D) eni のみ

   <details>
   <summary>回答を表示</summary>

   **回答: B) kubernetes（host scope）**

   Kubernetes が必要なノード CIDR を提供し、agent がその範囲内で IP アドレスを割り当てます。host scope と cluster-pool は、どちらも個々のアドレスをローカルで割り当てます。どちらもプレフィックスの調整が不要になるわけではありません。

   </details>

3. **Cilium 自身が AWS ENI と VPC アドレスを管理する、準備済みの EC2 ノード環境で使うバックエンドはどれですか？**
   - A) kubernetes
   - B) cluster-pool
   - C) eni
   - D) AWS のすべてのノードで delegated-plugin

   <details>
   <summary>回答を表示</summary>

   **回答: C) eni**

   これは ENI IPAM です。AWS VPC CNI とチェーンする場合、IP の割り当ては AWS VPC CNI が引き続き担当します。Hybrid Nodes には別の方式があり、Fargate／Auto Mode ではこの置き換え構成はサポートされません。

   </details>

4. **host-scope IPAM に関係する Kubernetes のフィールドはどれですか？**
   - A) Node.spec.podCIDRs と、旧式／単一ファミリーの Node.spec.podCIDR
   - B) Node.spec.subnet
   - C) Service.spec.podCIDR
   - D) CiliumPodIPPool.spec.selector

   <details>
   <summary>回答を表示</summary>

   **回答: A) Node.spec.podCIDRs と、旧式／単一ファミリーの Node.spec.podCIDR**

   これらは Kubernetes Node のフィールドです。一方、cluster-pool は CiliumNode.spec.ipam.podCIDRs を使います。どの状態が正となるかは、選択したモードによって異なります。

   </details>

5. **実際に有効な IPAM 設定を調査するには、何を確認すべきですか？**
   - A) ipam を含む grep の行だけで設定全体を判断する
   - B) Pod の Ready 状態だけを見る
   - C) 常に CiliumNode の最初のアドレスと CIDR を使う
   - D) 望ましい値とノード上書き、agent／Operator の実状態、選択した割り当て方式のリソースを照合する

   <details>
   <summary>回答を表示</summary>

   **回答: D) 望ましい値とノード上書き、agent／Operator の実状態、選択した割り当て方式のリソースを照合する**

   Helm／ConfigMap の値、ノード上書き、割り当て状態はそれぞれ補完的な情報です。CiliumNode がすべての IPAM モードで常に正となるわけではなく、アドレス配列内の位置だけでは次のホップも判断できません。

   </details>

## Policy の基本

6. **このガイドで扱う CiliumNetworkPolicy のリソース API バージョンは何ですか？**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>回答を表示</summary>

   **回答: C) cilium.io/v2**

   CiliumNetworkPolicy は cilium.io/v2 を使います。CiliumPodIPPool の v2alpha1 API や、通常の Kubernetes NetworkPolicy と混同しないでください。

   </details>

7. **名前空間スコープの CiliumNetworkPolicy で、endpointSelector は何を選択しますか？**
   - A) その名前空間内でポリシーの適用対象となる endpoint
   - B) 作成する Kubernetes Service
   - C) すべての名前空間にあるホストノード
   - D) 継承する別のポリシー

   <details>
   <summary>回答を表示</summary>

   **回答: A) その名前空間内でポリシーの適用対象となる endpoint**

   ポリシーを適用する endpoint を選択します。リソースのスコープとセレクターは、ingress／egress で記述する通信相手とは別のものです。

   </details>

8. **ingress ルールは何を表しますか？**
   - A) 選択した endpoint に入るトラフィック
   - B) 選択した endpoint から出るトラフィック
   - C) 新しい IP プール
   - D) 経路のアドバタイズ

   <details>
   <summary>回答を表示</summary>

   **回答: A) 選択した endpoint に入るトラフィック**

   ingress は、ポリシーの対象として選択した endpoint を基準にした受信方向です。対応する peer、ポート、サポート対象のプロトコル制約を適用してください。

   </details>

9. **egress ルールは何を表しますか？**
   - A) 選択した endpoint に入るトラフィック
   - B) 選択した endpoint から出るトラフィック
   - C) あらゆる場所へのすべてのトラフィック
   - D) Kubernetes 外部からのトラフィックのみ

   <details>
   <summary>回答を表示</summary>

   **回答: B) 選択した endpoint から出るトラフィック**

   egress は、選択した endpoint から出るトラフィックを制御します。必要な DNS とアプリケーションの依存先を意識して許可してください。

   </details>

10. **任意の Cilium ルールにある spec.labels は何に使いますか？**
    - A) endpointSelector の代わりに対象 Pod を選択する
    - B) ルールの識別とメタデータ
    - C) 同じラベルを持つ任意のポリシーを継承する
    - D) Pod IP を割り当てる

    <details>
    <summary>回答を表示</summary>

    **回答: B) ルールの識別とメタデータ**

    ルールラベルは識別や検索に利用でき、必ず一意である必要はありません。別のポリシーを参照したり継承したりする機能ではありません。Kubernetes の metadata.labels はリソース自体にラベルを付けます。

    </details>

## peer の選択

11. **toCIDR／toCIDRSet の目的とデフォルトの適用範囲は何ですか？**
    - A) IP プレフィックスによる選択。主に外部 peer が対象で、管理対象 Pod／ノードとの照合には文書化されたデフォルト制限がある
    - B) HTTP URL のフィルタリング
    - C) Service の自動作成
    - D) 指定プレフィックスからのアドレス割り当て

    <details>
    <summary>回答を表示</summary>

    **回答: A) IP プレフィックスによる選択。主に外部 peer が対象で、管理対象 Pod／ノードとの照合には文書化されたデフォルト制限がある**

    通常の管理対象 Pod には endpoint selector を使ってください。このリリースでは、Pod／ノードとの CIDR 照合はオプトインのベータ機能として文書化されており、identity の消費にも影響します。デフォルトの動作を無条件の IP マッチャーとして説明しないでください。

    </details>

12. **toFQDNs が許可するのは何ですか？**
    - A) すべての DNS クエリを自動的に許可する
    - B) そのドメイン配下の任意の HTTP URL
    - C) 選択した名前について学習した IP への通信。ただしポートなどポリシーの制約を受ける
    - D) 静的に設定した IP のみ

    <details>
    <summary>回答を表示</summary>

    **回答: C) 選択した名前について学習した IP への通信。ただしポートなどポリシーの制約を受ける**

    名前と IP の対応を観測するには、別途 DNS proxy ルールが必要です。ポート53を許可するだけでは学習は有効になりません。また、IP の許可は HTTP ホスト名の検証でも、アプリケーション利用者の認可でもありません。

    </details>

13. **world entity は何を表しますか？**
    - A) ローカルとリモートの Pod を区別せずにすべて含む
    - B) クラスター外部にある広い identity 区分
    - C) コントロールプレーンノードのみ
    - D) パブリックインターネット上のアドレスのみ

    <details>
    <summary>回答を表示</summary>

    **回答: B) クラスター外部にある広い identity 区分**

    world にはプライベートネットワーク上の外部 peer も含まれる場合があります。all entity や、名前を指定したリモートクラスターのセレクターとは異なります。必要に応じて、明示的な peer とより限定的なルールを使ってください。

    </details>

14. **toServices はどのように動作しますか？**
    - A) Kubernetes Service の selector、または selector のない Service の EndpointSlice アドレスをポリシー用セレクターに変換する
    - B) Service を作成して自動的にルーティングする
    - C) すべての DNS 名への通信を可能にする
    - D) kube-apiserver entity ルールすべての置き換えとなる

    <details>
    <summary>回答を表示</summary>

    **回答: A) Kubernetes Service の selector、または selector のない Service の EndpointSlice アドレスをポリシー用セレクターに変換する**

    selector のない Service では CIDR 由来のセレクターが使われ、その制限も引き継がれます。特殊な default／kubernetes Service が通常のワークロード用セレクターと同じように動作すると想定しないでください。

    </details>

15. **ホストファイアウォールの対象を選ぶ nodeSelector はどこで使いますか？**
    - A) 前提条件なしで、任意の名前空間スコープ CiliumNetworkPolicy に指定する
    - B) ホストファイアウォールを設定した CiliumClusterwideNetworkPolicy に指定する
    - C) すべての Pod IP を割り当てるため CiliumPodIPPool に指定する
    - D) Service annotation に指定する

    <details>
    <summary>回答を表示</summary>

    **回答: B) ホストファイアウォールを設定した CiliumClusterwideNetworkPolicy に指定する**

    Rule API では nodeSelector の使用先が CiliumClusterwideNetworkPolicy に限定されています。endpointSelector や peer 選択の fromNodes／toNodes とは別の機能です。

    </details>

## L7 ポリシー

16. **サポート対象の Cilium L7 ルールで制約できる HTTP リクエスト属性はどれですか？**
    - A) Path
    - B) Method
    - C) Headers
    - D) 上記すべて

    <details>
    <summary>回答を表示</summary>

    **回答: D) 上記すべて**

    Envoy は可視な HTTP トラフィックにルールを適用します。重複する L7 制約とは別に無制限の L4 許可を設定すると、その L7 制約を迂回できる場合があります。また、ポリシー上の許可はアプリケーションの成功を保証しません。

    </details>

17. **Cilium 1.20.3 の rules.kafka について正しい説明はどれですか？**
    - A) デフォルトで topic の認可を提供する
    - B) apiVersion を v2alpha1 に変えると有効になる
    - C) broker 接続を自動的に暗号化する
    - D) 組み込みの Kafka L7 API は削除されている。適切なネットワーク制御と broker 側の認可を使う

    <details>
    <summary>回答を表示</summary>

    **回答: D) 組み込みの Kafka L7 API は削除されている。適切なネットワーク制御と broker 側の認可を使う**

    旧式の topic／API key／client ID ポリシーを適用しないでください。L4 接続には実際の broker listener port を使い、認証／認可には broker が備える機能を使ってください。

    </details>

18. **リリースの実装に合うワイルドカードの説明はどれですか？**
    - A) `*.example.com` は example.com と a.b.example.com にも一致する
    - B) `*.example.com` はサブドメイン1階層に一致し、`**.example.com` は1階層以上に一致する。どちらも apex には一致しない
    - C) アスタリスクは常にドットも含めて一致する
    - D) matchName と matchPattern は DNS アドレスを割り当てる

    <details>
    <summary>回答を表示</summary>

    **回答: B) `*.example.com` はサブドメイン1階層に一致し、`**.example.com` は1階層以上に一致する。どちらも apex には一致しない**

    実装では正規化した DNS 名を基準に照合します。完全一致、1階層のワイルドカード、複数階層を示すプレフィックスはそれぞれ意味が異なります。apex も含めるには、別途 matchName を指定できます。

    </details>

19. **サポート対象の gRPC service／method と metadata の制約は、どのように表しますか？**
    - A) rules.grpc の protobuf フィールドフィルター
    - B) L3 CIDR マッチのみ
    - C) サポート対象の Envoy 経由で HTTP/2 の path と header を照合する
    - D) CNI を kube-proxy に置き換える

    <details>
    <summary>回答を表示</summary>

    **回答: C) サポート対象の Envoy 経由で HTTP/2 の path と header を照合する**

    gRPC の service／method 名は HTTP/2 の path に、metadata は header に現れます。任意の protobuf payload を検査する機能ではありません。また、TLS の可視性も考慮する必要があります。

    </details>

20. **コンポーネントの役割について正しい説明はどれですか？**
    - A) kube-proxy がすべての L7 ルールを適用する
    - B) Envoy がサポート対象の HTTP／gRPC ルールを処理し、Cilium の DNS proxy が DNS ポリシーを処理する
    - C) DNS ポリシーには NGINX Ingress が必須である
    - D) すべての L7 parser はカーネル BPF のみで動作する

    <details>
    <summary>回答を表示</summary>

    **回答: B) Envoy がサポート対象の HTTP／gRPC ルールを処理し、Cilium の DNS proxy が DNS ポリシーを処理する**

    デフォルトでは DNS proxy は agent 内で動作し、単独モードは別途文書化された alpha 機能です。すべての DNS ルールに Envoy が必要だと考えたり、暗号化されていれば payload が見えると想定したりしないでください。

    </details>

[ガイドを確認する](../../../networking/cilium/04-ipam-policy.md)
