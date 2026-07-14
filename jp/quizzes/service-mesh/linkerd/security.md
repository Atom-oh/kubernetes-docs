# Linkerd セキュリティクイズ

このクイズでは、Linkerd のセキュリティ機能に関する理解度を確認します。

## クイズ問題

### 1. Linkerd で mTLS はどのように有効化されますか？

A. 各 Service に対して手動設定が必要
B. mesh 内のすべてのトラフィックに自動的に適用される
C. Kubernetes Secret による設定が必要
D. Namespace ごとに有効化する必要がある

<details>
<summary>回答を表示</summary>

**回答: B. mesh 内のすべてのトラフィックに自動的に適用される**

**解説:**
Linkerd の中核的な価値の 1 つは「デフォルトでセキュリティを確保すること」です。mesh 内の Service 間のすべてのトラフィックには、設定なしで自動的に mTLS が適用されます。

</details>

### 2. Server リソースの役割は何ですか？

A. 外部 Server 接続を定義する
B. 受信トラフィックのポートとプロトコルを定義する
C. Server 証明書を保存する
D. Load Balancer を設定する

<details>
<summary>回答を表示</summary>

**回答: B. 受信トラフィックのポートとプロトコルを定義する**

**解説:**
Server リソースは、特定の Pod に対する受信トラフィックを定義します。podSelector で対象の Pod を、port でポートを、proxyProtocol でプロトコル（HTTP/1、HTTP/2、gRPC、opaque）を指定します。

</details>

### 3. ServerAuthorization の meshTLS.serviceAccounts は何を指定しますか？

A. Server が使用する ServiceAccount
B. アクセスを許可される Client ServiceAccount
C. 証明書発行権限を持つ ServiceAccount
D. メトリクス収集権限を持つ ServiceAccount

<details>
<summary>回答を表示</summary>

**回答: B. アクセスを許可される Client ServiceAccount**

**解説:**
ServerAuthorization の meshTLS.serviceAccounts は、どの Client ServiceAccount が Server にアクセスできるかを指定します。指定された ServiceAccount を持つ workload のみがアクセスを許可されます。

</details>

### 4. default-deny ポリシーモードでトラフィックを許可するにはどうしますか？

A. すべてのトラフィックが自動的に許可される
B. ServerAuthorization を明示的に定義する必要がある
C. Namespace ラベルで許可する
D. ConfigMap でホワイトリストを設定する

<details>
<summary>回答を表示</summary>

**回答: B. ServerAuthorization を明示的に定義する必要がある**

**解説:**
default-deny モードでは、すべてのトラフィックがデフォルトで拒否されます。トラフィックを許可するには、Server と ServerAuthorization を明示的に定義する必要があります。これはゼロトラストのセキュリティモデルです。

</details>

### 5. Trust Anchor に推奨される有効期間はどれですか？

A. 24 時間
B. 1 年
C. 1～10 年
D. 無期限

<details>
<summary>回答を表示</summary>

**回答: C. 1～10 年**

**解説:**
Trust Anchor（Root CA）は長期間有効であるべきです。一般的には 1～10 年が推奨されます。Trust Anchor の置き換えは複雑であるため、セキュリティ要件に応じて十分に長い有効期間を設定してください。

</details>

### 6. 認証されていない Client（mesh 外）を許可する ServerAuthorization の設定はどれですか？

A. `meshTLS.identities: ["*"]`
B. `unauthenticated: true`
C. `external: allowed`
D. `client: any`

<details>
<summary>回答を表示</summary>

**回答: B. `unauthenticated: true`**

**解説:**
`client.unauthenticated: true` を設定すると、mTLS 認証のない Client（mesh 外）からのアクセスを許可できます。これは health check または ingress からのトラフィックに使用されます。

</details>

### 7. Identity Issuer 証明書を更新する際に必要なことは何ですか？

A. すべての proxy を再起動する必要がある
B. Trust Anchor も置き換える必要がある
C. Kubernetes Secret を更新し、Identity Controller を再起動する
D. Cluster 全体を再起動する必要がある

<details>
<summary>回答を表示</summary>

**回答: C. Kubernetes Secret を更新し、Identity Controller を再起動する**

**解説:**
Identity Issuer を更新する場合は、1) 新しい証明書で Secret を更新し、2) Identity Controller を再起動します。proxy は新しい証明書で自動的に更新されます。Trust Anchor が同じであれば、置き換える必要はありません。

</details>

### 8. mesh 内からの mTLS トラフィックのみを許可するポリシーモードはどれですか？

A. deny
B. all-unauthenticated
C. all-authenticated
D. cluster-unauthenticated

<details>
<summary>回答を表示</summary>

**回答: C. all-authenticated**

**解説:**
`all-authenticated` モードでは、mesh 内からの mTLS 認証済みトラフィックのみが許可されます。mesh 外からの認証されていないトラフィックは拒否されます。

</details>

### 9. Linkerd 統合のために cert-manager Certificate リソースで必要な設定はどれですか？

A. isCA: false
B. isCA: true
C. usages: [digital signature]
D. algorithm: RSA

<details>
<summary>回答を表示</summary>

**回答: B. isCA: true**

**解説:**
Linkerd Identity Issuer は中間 CA として機能するため、cert-manager Certificate には `isCA: true` が必要です。この証明書は workload 証明書に署名します。

</details>

### 10. linkerd viz edges コマンドで確認できるものは何ですか？

A. ネットワーク edge router のステータス
B. Service 間の mTLS 接続ステータス
C. Cluster 境界ポリシー
D. DNS edge cache のステータス

<details>
<summary>回答を表示</summary>

**回答: B. Service 間の mTLS 接続ステータス**

**解説:**
`linkerd viz edges` は Service 間の接続（edge）を表示し、SECURED 列で mTLS のステータスを示します。mesh 外からのトラフィックでは、SECURED に X が表示されます。

</details>

### 11. Linkerd のセキュリティとアプリケーションセキュリティの正しい関係はどれですか？

A. Linkerd がすべてのセキュリティを処理するため、アプリケーションセキュリティは不要である
B. Linkerd はトランスポート層を処理し、アプリケーションはビジネスロジックのセキュリティを処理する
C. アプリケーションセキュリティだけで十分であり、Linkerd のセキュリティは任意である
D. 両方のセキュリティは完全に独立しており、相互作用はない

<details>
<summary>回答を表示</summary>

**回答: B. Linkerd はトランスポート層を処理し、アプリケーションはビジネスロジックのセキュリティを処理する**

**解説:**
多層防御の原則に従い、Linkerd はトランスポート暗号化（mTLS）と Service 認可を処理し、アプリケーションはユーザー認証（JWT）、RBAC、入力検証などのビジネスロジックのセキュリティを処理します。

</details>

### 12. Prometheus アラートで監視する Linkerd セキュリティメトリクスではないものはどれですか？

A. 証明書の有効期限
B. 非 mTLS トラフィックの割合
C. アプリケーションのログイン失敗回数
D. 認可により拒否されたリクエスト数

<details>
<summary>回答を表示</summary>

**回答: C. アプリケーションのログイン失敗回数**

**解説:**
Linkerd のセキュリティメトリクスには、証明書の有効期限、非 mTLS トラフィックの割合、認可により拒否されたリクエスト数が含まれます。アプリケーションのログイン失敗は、Linkerd の対象範囲外であるアプリケーションレベルのメトリクスです。

</details>
