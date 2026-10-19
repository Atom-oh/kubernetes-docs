# Linkerd セキュリティクイズ

[セキュリティガイド](../../../service-mesh/linkerd/04-security.md) に基づき、2026年9月11日に確認しました。

### 1. Linkerd はどのように mesh mTLS を有効にしますか?

- A. すべての Service が独自に Linkerd TLS を実装する
- B. mesh に参加している Pod 間の、対象となる TCP 通信で自動的に有効にする
- C. どの Kubernetes Secret でも、すべての network path を暗号化する
- D. すべての UDP 通信を自動的に保護する

<details>
<summary>答えと解説を表示</summary>

**答え: B**

両方の proxy が通信に参加し、trust chain を信頼している必要があります。mesh に参加していない endpoint や対象外の port には、Linkerd mTLS は自動適用されません。既定では inbound の平文通信を受け入れる場合もあります。認証済みアクセスを必須にするには、適切な policy を設定してください。

</details>

### 2. Server resource は何を選択しますか?

- A. 外部 DNS record
- B. 同じ namespace の対象 Pod に届く inbound port/protocol
- C. certificate Secret
- D. outbound load-balancer algorithm

<details>
<summary>答えと解説を表示</summary>

**答え: B**

Server は Pod/port の対象を選びます。application port を宣言し、Server の対象が重複しないようにしてください。`accessPolicy` が動作を変更しない限り、一致する Server がない通信は既定で拒否されます。proxy admin port 4191 に Server を作っても、admin port の interception bypass が解除されるわけではありません。

</details>

### 3. ServerAuthorization の `meshTLS.serviceAccounts` は何を表しますか?

- A. server の `serviceAccountName`
- B. 認証済み client として許可される ServiceAccount
- C. すべての証明書を発行する account
- D. metrics 収集だけを行う account

<details>
<summary>答えと解説を表示</summary>

**答え: B**

この grant は、一致する mesh client identity を受け入れます。別の grant がアクセスを広げる場合もあります。この release では `ServerAuthorization/v1beta1` が提供されています。AuthorizationPolicy から ServiceAccount を直接参照することもでき、その場合この legacy grant は不要です。

</details>

### 4. default-deny の下で、意図した application 通信を許可するにはどうしますか?

- A. すべての request が自動的に許可される
- B. 対象と、それに一致する認可 grant を定義する
- C. 汎用 namespace label を付ければ、任意の caller がアクセスできる
- D. 任意の ConfigMap whitelist だけで十分である

<details>
<summary>答えと解説を表示</summary>

**答え: B**

Server と AuthorizationPolicy は現行の設定パターンです。ServerAuthorization は以前からある代替手段です。これらを必須の順次処理として両方設定する必要はありません。1 つの AuthorizationPolicy に複数の `requiredAuthenticationRefs` を指定した場合は、そのすべてが一致する必要があります。probe 用の通信にも適切な扱いが必要です。

</details>

### 5. trust anchor の有効期間はどのように選ぶべきですか?

- A. 常にちょうど 24 時間
- B. 常に無期限
- C. CA policy、計画している rotation、復旧要件に基づいて選ぶ。CLI の既定値は 1 年
- D. すべての cluster に一律で 1～10 年を推奨する

<details>
<summary>答えと解説を表示</summary>

**答え: C**

手動で 10 年の root を設定することは可能ですが、自動的に推奨される設定ではありません。証明書 chain 全体の有効期限を追跡し、issuer の renewal/lifetime がその CA に適合することを確認してください。root rotation では証明書を重複して信頼できる期間を設け、linked cluster を含むすべての利用者に配布する必要があります。

</details>

### 6. ServerAuthorization で `client.unauthenticated: true` を設定すると何が許可されますか?

- A. wildcard に一致する認証済み identity だけ
- B. mesh 認証を要求しない client
- C. 特別な外部 header を使う caller だけ
- D. 対象とは無関係に、宣言された readiness URL だけ

<details>
<summary>答えと解説を表示</summary>

**答え: B**

この設定は、対象範囲内で mesh 認証のない client からのアクセスを許可します。health path だけに自動で限定されるわけではありません。`meshTLS.identities: ["*"]` は異なる設定です。これは mesh 認証を引き続き要求しつつ、mesh identity を広く受け入れます。

</details>

### 7. 信頼する root が変わらない場合、有効な issuer を更新すると通常どうなりますか?

- A. すべての proxy をただちに再起動しなければならない
- B. root も常に変更しなければならない
- C. owner が issuer Secret を更新し、Identity が検証・再読み込みし、proxy は通常どおり leaf を更新する
- D. cluster 全体を再起動しなければならない

<details>
<summary>答えと解説を表示</summary>

**答え: C**

`IssuerUpdated` を確認し、更新が skip された場合や無効な場合は調査してください。chain が有効な間は、既存の leaf が通常の更新時期まで古い issuer のまま使われる場合があります。issuer を更新するたびに Identity を一律再起動する必要はありません。trust anchor の rotation は、別途段階的に行います。

</details>

### 8. 適切に信頼された multicluster client を含め、認証済み mesh client を要求する既定 policy はどれですか?

- A. deny
- B. all-unauthenticated
- C. all-authenticated
- D. cluster-unauthenticated

<details>
<summary>答えと解説を表示</summary>

**答え: C**

`all-authenticated` は mesh 認証を要求します。特定 caller だけを許可する狭い allowlist ではありません。明示した Server policy と認可 grant も引き続き重要です。namespace の既定 annotation は proxy の初期化時に適用されます。

</details>

### 9. cert-manager で Linkerd の署名用 issuer certificate を発行する場合に必要なものはどれですか?

- A. `isCA: false`
- B. `isCA: true`、適切な ECDSA P-256 credential、有効な chain
- C. 任意の leaf certificate に digital-signature usage だけを設定する
- D. 常に RSA private key を使う

<details>
<summary>答えと解説を表示</summary>

**答え: B**

Identity には workload certificate に署名できる intermediate CA が必要です。`rotationPolicy` を明示し、Secret の形式と owner、CA lifetime を確認したうえで、Identity が証明書を読み込んだことを検証してください。要求に `isCA: true` と書かれていても、一般的な Vault leaf-signing 経路が CA を発行できるとは限りません。

</details>

### 10. `linkerd viz edges` では何を確認できますか?

- A. 各 edge router の hardware 状態
- B. 観測された resource 間の edge と、その mTLS/security 状態
- C. あらゆる経路や未使用経路が暗号化されている証明
- D. end-user 認証の完全な audit

<details>
<summary>答えと解説を表示</summary>

**答え: B**

SECURED 表示が示すのは観測された edge の情報であり、network 全体の完全な一覧ではありません。public certificate には `linkerd identity` を、アクセス判定の調査には policy diagnostics/metrics を使ってください。CLI の表示を Prometheus の TLS label 値そのものと同一視しないでください。

</details>

### 11. Linkerd と application security の適切な関係はどれですか?

- A. mesh mTLS があれば application security は不要である
- B. mesh の workload/transport 制御は、user、tenant、business の認可を補完する
- C. 許可された ServiceAccount は、すべての caller が administrator である証明になる
- D. mesh が input validation を自動で行う

<details>
<summary>答えと解説を表示</summary>

**答え: B**

Linkerd は workload 認証、対象となる transport の暗号化、inbound 認可を提供します。application 側では user credential、permission、input を引き続き検証してください。proxy bypass や mesh 未登録の経路には、network/admission control も必要です。

</details>

### 12. application 側の instrumentation、または別の application-aware source が必要な metric はどれですか?

- A. proxy workload certificate の有効期限
- B. mesh client identity がない状態で観測された HTTP response
- C. application の login 失敗
- D. proxy inbound 認可の拒否 counter

<details>
<summary>答えと解説を表示</summary>

**答え: C**

Linkerd は application の login 結果を自動的には把握しません。Linkerd 自体の alert では、leaf の有効期限 timestamp と issuer TTL duration を区別してください。対象を絞った traffic ratio を rate ベースで計算し、identity label を保持し、telemetry がない場合と traffic が idle の場合を別に扱います。

</details>
