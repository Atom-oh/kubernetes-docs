# Cilium Service Mesh アーキテクチャクイズ

Cilium 1.20.3 に照らして確認しています。設定上の条件と注意事項、主な参照先については[アーキテクチャガイド](../../../service-mesh/cilium-service-mesh/01-architecture.md)を参照してください。

### 1. Cilium のアーキテクチャの特徴はどれですか？

- **A.** Kubernetes API server を置き換える
- **B.** eBPF による L3/L4 処理と、該当する L7 トラフィック向けの Envoy を組み合わせる
- **C.** すべてのパケットを Pod ごとの Envoy に送る
- **D.** Kubernetes リソースを使用できない

<details>
<summary>解答を表示</summary>

**解答: B. eBPF による L3/L4 処理と、該当する L7 トラフィック向けの Envoy を組み合わせる**

Cilium は eBPF でネットワーキングと L3/L4 ポリシーを実装します。該当する L7 機能には Envoy を使い、Agent が管理する構成と、独立した DaemonSet として動作する構成があります。これはコンポーネントの配置を説明するものであり、普遍的な性能測定結果を示すものではありません。

</details>

### 2. Cilium のデータパスを説明する際に使われる、カーネルへのアタッチ機構ではないものはどれですか？

- **A.** TC/TCX
- **B.** cgroup の socket hook
- **C.** アプリケーションの HTTP handler
- **D.** XDP

<details>
<summary>解答を表示</summary>

**解答: C. アプリケーションの HTTP handler**

HTTP handler はアプリケーションコードであり、カーネル hook ではありません。Cilium は TC/TCX と cgroup hook を使用できます。XDP による高速化には、適切な設定とデバイスが必要です。eBPF が存在するからといって、これらすべての hook がすべてのパケットで実行されるわけではありません。

</details>

### 3. Envoy プロセスをノード単位で共有することから、何が分かりますか？

- **A.** 各ノードでメモリを必ず 100 MB 使用する
- **B.** リクエストレイテンシーが必ず 0.1 ms になる
- **C.** プロキシのライフサイクル、リソース、障害の共有境界となるため、ワークロードに合わせたサイジングが必要である
- **D.** 暗号化の設定が不要になる

<details>
<summary>解答を表示</summary>

**解答: C. プロキシのライフサイクル、リソース、障害の共有境界となるため、ワークロードに合わせたサイジングが必要である**

ノード単位で共有すると、Pod ごとに sidecar を配置する場合よりプロキシのインスタンス数を減らせることがあります。ただし、合計リソースには Agent、map、コントロールプレーン、オプションのコンポーネントも含まれます。実際のコストはノード数、トラフィック、ポリシー、機能によって変わります。以前示されていた「5 GB 対 500 MB」という固定比較は、測定結果ではありません。

</details>

### 4. CiliumEnvoyConfig が定義するものは何ですか？

- **A.** Pod のスケジューリングのみ
- **B.** 名前空間スコープの低レベル Envoy リソースと、関連する Service のリダイレクト／バックエンド同期
- **C.** すべての CiliumEndpoint の置き換え
- **D.** `kubectl apply` が成功すれば必ず受け入れられる汎用設定

<details>
<summary>解答を表示</summary>

**解答: B. 名前空間スコープの低レベル Envoy リソースと、関連する Service のリダイレクト／バックエンド同期**

CEC は Kubernetes Service と Envoy の Listener、Route、Cluster を接続します。Cilium は省略された Listener アドレスを割り当て、xDS のソースを補うことができます。Kubernetes は埋め込み Envoy フィールドをすべて検証するわけではないため、リソースが受け入れられた後も、実行時の動作を確認する必要があります。CCEC はクラスター全体のスコープですが、`*` が Service のワイルドカードになるわけではありません。

</details>

### 5. Maglev について正しい記述はどれですか？

- **A.** HTTP cookie を解析する
- **B.** Kubernetes の ClientIP セッションアフィニティを置き換える
- **C.** 対象となる外部トラフィックに対して、一貫したバックエンド選択を行う。セッションアフィニティとは別の機能である
- **D.** 削除済みのバックエンドが既存接続を処理し続けることを保証する

<details>
<summary>解答を表示</summary>

**解答: C. 対象となる外部トラフィックに対して、一貫したバックエンド選択を行う。セッションアフィニティとは別の機能である**

Maglev は、対象となる north–south ロードバランシングでフローを一貫してバックエンドに割り当てます。文書化されている socket レベルの east–west 経路には Maglev は適用されません。ClientIP アフィニティとコネクショントラッキングは別の機構です。Maglev は利用できなくなったバックエンドを稼働し続けさせるものではありません。

</details>

### 6. Cilium のワークロードセキュリティ ID はどのように割り当てられますか？

- **A.** 常に Pod IP と同じ ID になる
- **B.** ID に関係するラベルの組み合わせに対し、Cilium が数値 ID を割り当てる。複数の Pod が同じ ID を共有する場合がある
- **C.** ユーザーがラベルの hash を計算し、推測した CiliumIdentity を作成する
- **D.** 各 Pod にグローバルで永続的な数値 ID が割り当てられる

<details>
<summary>解答を表示</summary>

**解答: B. ID に関係するラベルの組み合わせに対し、Cilium が数値 ID を割り当てる。複数の Pod が同じ ID を共有する場合がある**

ID に関係するラベルには、namespace、service account、選択されたワークロードラベルなどが含まれます。割り当て機構がラベルの組み合わせから ID を決定します。ユーザーが hash を計算する方式ではなく、Pod ごとに一意となるとも限りません。CiliumEndpoint／CiliumIdentity と、Agent の `cilium-dbg identity list` で確認してください。

</details>

### 7. どのトラフィックが Envoy を使用することがありますか？

- **A.** すべての構成におけるすべてのパケット
- **B.** HTTP L7 ポリシーの対象トラフィックと、サポートされた Service／Ingress／Gateway 設定でリダイレクトされるトラフィック
- **C.** CiliumNetworkPolicy に HTTP ルールがあるトラフィックのみ。Gateway トラフィックは対象外
- **D.** すべての Pod に Envoy sidecar がなければ、どのトラフィックも対象にならない

<details>
<summary>解答を表示</summary>

**解答: B. HTTP L7 ポリシーの対象トラフィックと、サポートされた Service／Ingress／Gateway 設定でリダイレクトされるトラフィック**

HTTP ポリシーは、対応する ingress または egress トラフィックを Envoy にリダイレクトします。CEC による Service ロードバランシングと Gateway／Ingress も Envoy を必要とすることがあります。プロキシ経由のリクエストへの応答は、確立済みのプロキシ接続を使います。応答ごとに任意で独立したリダイレクトを行うわけではありません。

</details>

### 8. Cilium の BPF コネクショントラッキングは何に使用されますか？

- **A.** Kubernetes API を置き換える
- **B.** フロー状態を保持し、ポリシー判定と併せて戻りトラフィックを識別する
- **C.** 最初の許可判定を、以後すべてのパケットに対して永続的にキャッシュする
- **D.** HTTP アプリケーションの認証情報を保存する

<details>
<summary>解答を表示</summary>

**解答: B. フロー状態を保持し、ポリシー判定と併せて戻りトラフィックを識別する**

CT map はフローの状態と存続期間、および変換やプロキシに関するメタデータを追跡します。公開済みのエンドポイントデータパスでは、明示的な例外を除き、新規トラフィックと確立済みフローの開始方向のトラフィックの両方でポリシーが確認され、識別済みの応答は状態に基づいて処理されます。CT によるキャッシュは、ポリシー適用を一律に免除するものではありません。

</details>

### 9. CiliumClusterwideNetworkPolicy と CiliumNetworkPolicy の違いは何ですか？

- **A.** Kubernetes リソースとしてのスコープは同じである
- **B.** CCNP はクラスター全体のスコープ、CNP は名前空間スコープであり、影響を受けるエンドポイントはセレクターで決まる
- **C.** あらゆる L7 ルールを記述できるのは CNP のみである
- **D.** どの CCNP も必ずすべての名前空間を拒否する

<details>
<summary>解答を表示</summary>

**解答: B. CCNP はクラスター全体のスコープ、CNP は名前空間スコープであり、影響を受けるエンドポイントはセレクターで決まる**

どちらも、対応する L7 ポリシールールをサポートします。リソースのスコープとエンドポイントの選択は別の概念です。クラスター全体のスコープを持つリソースでも、すべてのワークロードを自動的に選択または拒否するわけではありません。ほかに適用されるポリシーによる許可も考慮してください。

</details>

### 10. Cilium のベータ版帯域外相互認証における既定の SPIFFE ID 形式はどれですか？

- **A.** urn:spiffe:cluster/namespace/pod
- **B.** `spiffe://spiffe.cilium/identity/<numeric-security-identity>`
- **C.** すべての Cilium インストールで `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`
- **D.** `https://spiffe.io/id/<pod-name>`

<details>
<summary>解答を表示</summary>

**解答: B. `spiffe://spiffe.cilium/identity/<numeric-security-identity>`**

リリース済みの Cilium SPIRE provider は、設定された trust domain の下に `/identity/<numeric-id>` のパスを構築します。trust domain の既定値は `spiffe.cilium` です。Agent は Cilium security identity を代行します。認証交換は帯域外で行われ、アプリケーションの暗号化には別途 WireGuard／IPsec の設定が必要です。帯域外機能は引き続きベータ版で、未完成の部分があります。別の ztunnel 暗号化ベータ版は異なるワークロード ID モデルを使うため、この回答はその証明書パスを説明するものではありません。

</details>

### 11. Cilium Agent の役割ではないものはどれですか？

- **A.** ローカルの eBPF プログラムと map の管理
- **B.** ローカルのポリシーおよび Envoy 設定の管理
- **C.** Kubernetes API server として動作する
- **D.** ローカルのエンドポイントおよび ID 関連の管理

<details>
<summary>解答を表示</summary>

**解答: C. Kubernetes API server として動作する**

Agent は各ノードで動作します。Kubernetes API server は独立したコントロールプレーンコンポーネントです。Cilium Operator も別個の Deployment であり、ID のガベージコレクションや該当する IPAM 操作など、クラスター全体のタスクを担当します。

</details>

### 12. 同一ノード上の Pod トラフィックについて、正しい記述はどれですか？

- **A.** 常にノード外へ送信される
- **B.** 条件を満たす BPF host-routing 経路は上位のホストネットワーク層を迂回できるが、実際の経路は設定によって異なる
- **C.** Linux と Pod のネットワークスタックを常にすべて迂回する
- **D.** レイテンシーが必ず 0.1 ms になる

<details>
<summary>解答を表示</summary>

**解答: B. 条件を満たす BPF host-routing 経路は上位のホストネットワーク層を迂回できるが、実際の経路は設定によって異なる**

要件を満たす場合、BPF host routing は netfilter を含む上位のホストスタックを迂回できます。Pod のプロトコルスタックは引き続き使用されます。従来型のルーティング、エンドポイントデバイスモード、L7 ポリシー、各種統合によって経路は変わります。レイテンシーは実測が必要です。

</details>
