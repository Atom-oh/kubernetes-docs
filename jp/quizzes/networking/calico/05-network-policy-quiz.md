# Network Policy クイズ

> **関連ドキュメント**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **最終更新**: 2026年9月12日

## クイズ

1. Calico が補う Kubernetes 標準 NetworkPolicy の主な制約は何ですか？
   - A) ポート番号を指定できない
   - B) egress ルールをサポートしない
   - C) deny ルールがなく、グローバルポリシーがなく、セレクターの選択肢が限られる
   - D) ラベルによる Pod の選択ができない

<details>
<summary>答えを表示</summary>

**答え: C) deny ルールがなく、グローバルポリシーがなく、セレクターの選択肢が限られる**

**解説:**
標準 Kubernetes NetworkPolicy オブジェクトが提供するのは、名前空間スコープで加算的に適用される L3／L4 の allow ルールです。プラグインが実装していれば、名前付きポートや `endPort` を使う数値ポート範囲も既にサポートします。Calico は明示的なアクション、グローバルポリシー、tier、式セレクターを追加します。Open Source で HTTP ポリシーを使うには Istio／Dikastes 統合が必要で、DNS ドメインは商用拡張です。

</details>

2. Calico NetworkPolicy のセレクター構文はどれですか？
   - A) 標準 Kubernetes のような YAML のキーと値
   - B) `app == 'frontend'` のような式ベースの構文
   - C) 正規表現
   - D) JSONPath 式

<details>
<summary>答えを表示</summary>

**答え: B) `app == 'frontend'` のような式ベースの構文**

**解説:**
Calico は式ベースのセレクター構文を使い、`==`、`!=`、`in`、`not in`、`has()`、`!has()` などの演算子をサポートします。例: `app == 'frontend'`、`environment in {'prod', 'staging'}`、`has(role)`。標準 Kubernetes のラベルセレクターより柔軟に指定できます。

</details>

3. Calico NetworkPolicy ルールで使えるアクションはどれですか？
   - A) Accept、Reject
   - B) Allow、Deny、Log、Pass
   - C) Permit、Block、Audit
   - D) Enable、Disable、Monitor

<details>
<summary>答えを表示</summary>

**答え: B) Allow、Deny、Log、Pass**

**解説:**
Allow と Deny は、そのエンドポイント／方向に対する通常のポリシー判定を終了します。Log は評価を続けるため、後続の deny が適用される場合があります。Pass は現在の tier にある残りのポリシーをすべて飛ばし、次の該当 tier に進みます。最後の tier の後には Profile が評価されます。もう一方のエンドポイントに適用されるポリシーは引き続き有効です。

</details>

4. Calico の GlobalNetworkPolicy と NetworkPolicy の違いは何ですか？
   - A) GlobalNetworkPolicy の方が高速
   - B) NetworkPolicy は名前空間が必要で、GlobalNetworkPolicy はクラスター全体に適用できる
   - C) GlobalNetworkPolicy は eBPF モードでのみ動作する
   - D) NetworkPolicy の方が多くの機能をサポートする

<details>
<summary>答えを表示</summary>

**答え: B) NetworkPolicy は名前空間が必要で、GlobalNetworkPolicy はクラスター全体に適用できる**

**解説:**
NetworkPolicy は自身の名前空間のワークロードを選択します。非名前空間スコープの GlobalNetworkPolicy は、複数の名前空間にまたがるワークロードや HostEndpoint を選択できます。すべてのエンドポイントが自動的に対象になるわけではありません。対象範囲を明示し、ホスト／システムの接続性を保ってください。

</details>

5. Calico の NetworkSet は何に使いますか？
   - A) ネットワークインターフェイスのグループ化
   - B) 再利用可能な IP アドレス／CIDR セットの定義
   - C) ネットワーク名前空間の設定
   - D) ネットワークプラグインの管理

<details>
<summary>答えを表示</summary>

**答え: B) 再利用可能な IP アドレス／CIDR セットの定義**

**解説:**
NetworkSet は、ラベルを付けた IP／CIDR 範囲をグループ化し、再利用できるようにします。名前空間スコープの NetworkSet と GlobalNetworkSet では、選択範囲が異なります。名前空間スコープのポリシーからグローバルリソースを選ぶときは、`namespaceSelector: global()` を別途指定してください。`global(label-expression)` は有効な構文ではありません。

</details>

6. Calico のポリシーモデルでは、tier はどのように評価されますか？
   - A) 名前順
   - B) `order` フィールド順で、数値が小さいものから評価
   - C) ランダム
   - D) 作成時刻順

<details>
<summary>答えを表示</summary>

**答え: B) `order` フィールド順で、数値が小さいものから評価**

**解説:**
数値の小さい tier が先に評価され、各 tier 内では `order` の小さいポリシーが先に評価されます。対象エンドポイントと方向を選択する tier だけが適用されます。該当 tier 内のルールが一致しなければ、その tier の `defaultAction` が使われ、通常は Deny です。組み込みの default tier は 1,000,000 に固定されており、暗黙の無限大ではありません。

</details>

7. Calico ポリシールールの Pass アクションは何をしますか？
   - A) 直ちにトラフィックを許可する
   - B) トラフィックを黙って破棄する
   - C) 次の tier に進んで評価を続ける
   - D) トラフィックを記録して許可する

<details>
<summary>答えを表示</summary>

**答え: C) 次の tier に進んで評価を続ける**

**解説:**
Pass は、後続のセキュリティ制限を含め、同じ tier にある残りのポリシーを飛ばします。委譲する前に deny 専用のガードレールをすべて評価する場合は、早い段階の無条件 Pass ルールよりも、tier レベルで `defaultAction: Pass` を設定する方が適切な場合があります。

</details>

8. Calico Enterprise 3.23 で、許可する egress ドメイン名はどこに指定しますか？
   - A) ingress ルールの `hosts` フィールド
   - B) 宛先指定の `domains` フィールド
   - C) FQDN ポリシーはサポートされない
   - D) DNS NetworkPolicy CRD

<details>
<summary>答えを表示</summary>

**答え: B) 宛先指定の `domains` フィールド**

**解説:**
Calico Enterprise は、信頼された DNS 学習を使う egress Allow ルールの `destination.domains` をサポートします。このフィールドは Open Source 3.32 の CRD にはありません。`policySyncPathPrefix` や任意の DNS プロキシを有効にしても、この機能は追加されません。prefix ワイルドカードは1つ以上のドメイン構成要素に一致します。IP ベースの照合は、HTTPS のホスト名認証ではありません。

</details>

9. GlobalNetworkPolicy の `applyOnForward` は何を制御しますか？
   - A) ポリシーをホスト経由で転送／ルーティングされるトラフィックにも適用するか
   - B) ポリシーを順方向または逆順で適用するか
   - C) ポリシー違反を SIEM に転送するか
   - D) ポートフォワーディングにポリシーを適用するか

<details>
<summary>答えを表示</summary>

**答え: A) ポリシーをホスト経由で転送／ルーティングされるトラフィックにも適用するか**

**解説:**
HostEndpoint ポリシーでは、`applyOnForward: true` にすると転送トラフィックにも適用されます。`doNotTrack` または `preDNAT` が `true` の場合、この設定は必須です。ホストに対する Allow が、該当するワークロードエンドポイントのポリシーを迂回するわけではありません。

</details>

10. Calico ポリシーの `doNotTrack` は何をしますか？
    - A) ポリシーログを無効にする
    - B) コネクショントラッキング前にポリシーを適用する（ステートレス）
    - C) 監査ログでポリシーを追跡できないようにする
    - D) エンドポイントの追跡を無効にする

<details>
<summary>答えを表示</summary>

**答え: B) コネクショントラッキング前にポリシーを適用する（ステートレス）**

**解説:**
`doNotTrack` はホストポリシーのオプションで、`applyOnForward: true` が必要です。コネクショントラッキング前に適用されます。追跡しない Allow では、一致するトラフィックが追跡されなくなり、要求と応答に明示的なルールが必要です。普遍的な高速化策ではなく、conntrack に依存する Service／NAT 経路と競合する場合があります。

</details>

11. Calico ポリシーの `preDNAT` は何をしますか？
    - A) DNS 解決前にポリシーを適用する
    - B) Destination NAT 前に元の宛先を見てポリシーを適用する
    - C) DNAT の実行を防ぐ
    - D) DNS トラフィックだけにポリシーを適用する

<details>
<summary>答えを表示</summary>

**答え: B) Destination NAT 前に元の宛先を見てポリシーを適用する**

**解説:**
`preDNAT` は DNAT 前の元の宛先 IP／ポートを使って、ingress のホストトラフィックを評価します。`applyOnForward: true` が必要で、egress ルールは含められず、`doNotTrack` と併用できません。この段階で一致しなくても、自動的に破棄されるとは限りません。後続のホスト／ワークロードポリシーが引き続き適用されます。

</details>

12. 先行する明示的な Allow ポリシーの後で、demo-namespace のワークロードについて両方向を選択するベースラインはどれですか？
    - A) FelixConfiguration にクラスター全体のフラグを設定する
    - B) `types: [Ingress, Egress]` と空のルールを持つ、対象を絞った GlobalNetworkPolicy を作る
    - C) 既存の NetworkPolicy をすべて削除する
    - D) IPPool で default deny を設定する

<details>
<summary>答えを表示</summary>

**答え: B) `types: [Ingress, Egress]` と空のルールを持つ、対象を絞った GlobalNetworkPolicy を作る**

**解説:**
意図する名前空間／ワークロードを選び、両方の `types` を明示して、ルールは空のままにします。`order` を省略すると、明示的に順序指定されたポリシーの後に続きます。このベースラインが、先行する終端 Allow を上書きすることはありません。また、`selector: all()` だけでは HostEndpoint も対象に含まれる可能性があります。システムトラフィックに、スコープなしの catch-all を一般的な手順として適用しないでください。

</details>

13. Calico ポリシーの `order` フィールドは何を制御しますか？
    - A) Pod を選択する順序
    - B) tier 内での評価優先度（数値が小さいほど先）
    - C) ポリシー内のルールを適用する順序
    - D) NetworkSet 内の IP アドレスの順序

<details>
<summary>答えを表示</summary>

**答え: B) tier 内での評価優先度（数値が小さいほど先）**

**解説:**
`order` フィールドは tier 内でのポリシーの評価優先度を決定します。値の小さいポリシーから先に評価され、一致して終端アクション（Allow または Deny）を実行すると評価が終了します。これにより、一般ルールより先に評価する例外を作れます。

</details>

14. Calico の HostEndpoint とは何ですか？
    - A) ホストネットワーク上で実行する Pod
    - B) ポリシー適用のためにホストのネットワークインターフェイスを表すもの
    - C) API サーバーのエンドポイント
    - D) ホスト上の Service エンドポイント

<details>
<summary>答えを表示</summary>

**答え: B) ポリシー適用のためにホストのネットワークインターフェイスを表すもの**

**解説:**
HostEndpoint は、ポリシー適用のため、管理対象ホスト上のインターフェイスを表します。手動で作成したエンドポイントは default-deny の挙動を引き起こす場合があります。自動作成されたエンドポイントには通常 default-allow Profile があり、failsafe ポートも引き続き重要です。`Installation.hostPorts` は HostEndpoint を自動作成しません。

</details>

15. ネットワークポリシーが期待どおりに機能しない場合、どのように調査しますか？
    - A) ポリシー YAML を読むだけ
    - B) エンドポイントラベル、該当するすべての tier、バックエンド／ログ、実際の接続を確認する
    - C) Calico コンポーネントをすべて再起動する
    - D) ネットワークポリシーのデバッグはサポートされていない

<details>
<summary>答えを表示</summary>

**答え: B) エンドポイントラベル、該当するすべての tier、バックエンド／ログ、実際の接続を確認する**

**解説:**
Kubernetes と Calico の両方のポリシーを一覧表示し、関連する tier をすべて明示的に調査し、エンドポイントラベルを確認して、新しい接続の許可／拒否をテストしてください。Felix の readiness はレイテンシーのベンチマークではありません。iptables の Log アクションはカーネルログを使います。kube-proxy またはその代替機能の Service／NAT 動作が障害原因となる場合もあります。`tc` プログラムの一覧だけでは、実際に適用中のポリシー経路を追跡できません。

</details>

16. 標準 API サーバー経由で Calico の application tier を編集するには、どの権限構成が必要ですか？
    - A) `resourceNames: ["application.*"]` だけを指定した通常の networkpolicies
    - B) application Tier の Get と、`application.*` に対する tier.networkpolicies、および意図した名前空間へのバインド
    - C) `verbs: ["*"]` を含む任意の Role
    - D) application という名前の名前空間

<details>
<summary>答えを表示</summary>

**答え: B) application Tier の Get と、`application.*` に対する tier.networkpolicies、および意図した名前空間へのバインド**

**解説:**
Calico は `tier.networkpolicies` 疑似リソース、`application.*` またはポリシー名という合成名、および Tier に対する get 権限を確認します。これは汎用 Kubernetes の `resourceNames` ワイルドカードではありません。追加で許可される広範なバインドと、native-v3 の読み取り制限も考慮してください。

</details>

17. クライアントが送信元ポート 49152 からバックエンドのポート 8080 に接続します。サーバーのリスナーポートを表す ingress のポート条件はどれですか？
    - A) `source.ports: [8080]`
    - B) すべてのクライアントに `source.ports: [49152]`
    - C) TCP プロトコルで `destination.ports: [8080]`
    - D) プロトコルを指定せず、すべてのポートを含む source ポート範囲

<details>
<summary>答えを表示</summary>

**答え: C) TCP プロトコルで `destination.ports: [8080]`**

**解説:**
Service は宛先ポート 8080 でリッスンします。クライアントの送信元ポートは変わります。数値ポート条件には、ポートを持つサポート対象プロトコルが必要です。送信元ポート条件が適切な別の例として、明示的に定義した untracked DNS 応答ルールがあります。

</details>

---

[学習教材に戻る](../../../networking/calico/05-network-policy.md) | [前のクイズ: BGP の詳細](./04-bgp-deep-dive-quiz.md)
