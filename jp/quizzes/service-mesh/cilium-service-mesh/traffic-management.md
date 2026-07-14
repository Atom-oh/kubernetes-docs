# Cilium Service Mesh トラフィック管理クイズ

このクイズでは、Cilium Service Mesh における L7 トラフィック管理、CiliumEnvoyConfig、ロードバランシング、トラフィック分割、Gateway API 統合についての理解を確認します。

## クイズ問題

### 1. CiliumEnvoyConfig で HTTP ルーティングルールを定義するために使用される Envoy filter はどれですか？

A. envoy.filters.network.tcp_proxy
B. envoy.filters.network.http_connection_manager
C. envoy.filters.http.fault
D. envoy.filters.network.redis_proxy

<details>
<summary>回答を表示</summary>

**回答: B. envoy.filters.network.http_connection_manager**

**解説:**
HTTP Connection Manager は、HTTP トラフィックを処理するための中核となる Envoy filter です。この filter 内では、route_config を通じて、パスベース、ヘッダーベース、メソッドベースのルーティングルールを定義できます。

</details>

### 2. CiliumNetworkPolicy で L7 HTTP ルールを定義する際に使用できないフィールドはどれですか？

A. method
B. path
C. headers
D. body

<details>
<summary>回答を表示</summary>

**回答: D. body**

**解説:**
CiliumNetworkPolicy の HTTP L7 ルールでは、method（HTTP メソッド）、path（URL パス）、headers（HTTP ヘッダー）に基づくフィルタリングが可能です。body（リクエスト本文）は L7 ルールではサポートされていません。

</details>

### 3. Cilium で Kafka L7 ポリシーを適用する際に、有効な apiKey ではないものはどれですか？

A. produce
B. fetch
C. delete
D. metadata

<details>
<summary>回答を表示</summary>

**回答: C. delete**

**解説:**
Cilium の Kafka L7 ポリシーは、produce（メッセージ生成）、fetch（メッセージ取得）、metadata（メタデータ照会）、offsetcommit、offsetfetch、joingroup などの apiKey をサポートします。'delete' はサポートされる Kafka API key ではありません。

</details>

### 4. Cilium の eBPF ベース L4 ロードバランシングにおける Maglev hashing の利点は何ですか？

A. 完全にランダムな分散
B. バックエンドが変更されてもセッションを維持できる
C. 最小のメモリ使用量
D. L7 ルーティングのサポート

<details>
<summary>回答を表示</summary>

**回答: B. バックエンドが変更されてもセッションを維持できる**

**解説:**
Maglev は一貫性ハッシュアルゴリズムであり、バックエンドサーバーが追加または削除されても、既存の接続の大部分を同じバックエンドに維持します。これはステートフルなアプリケーションや、セッションアフィニティが必要な場合に有用です。

</details>

### 5. Gateway API HTTPRoute で重みベースのトラフィック分割を設定する正しい方法はどれですか？

A. split フィールドを使用する
B. backendRefs で weight フィールドを指定する
C. trafficPolicy を使用する
D. destinationRule を使用する

<details>
<summary>回答を表示</summary>

**回答: B. backendRefs で weight フィールドを指定する**

**解説:**
Gateway API HTTPRoute では、backendRefs 配列内の各バックエンドに weight フィールドを指定してトラフィック分割を設定します。たとえば、`weight: 90` と `weight: 10` を使用すると、トラフィックは 90:10 の比率で分割されます。

</details>

### 6. CiliumEnvoyConfig でリトライポリシーを設定する際、retry_on フィールドに指定できない有効な条件はどれですか？

A. 5xx
B. reset
C. timeout
D. connect-failure

<details>
<summary>回答を表示</summary>

**回答: C. timeout**

**解説:**
Envoy の retry_on 条件には、5xx（サーバーエラー）、reset（接続リセット）、connect-failure（接続失敗）、retriable-4xx などがあります。'timeout' は直接指定できる retry_on 条件ではありません。各リトライ試行のタイムアウトは per_try_timeout で設定します。

</details>

### 7. Cilium で DNS L7 ポリシーを使用する主な利点は何ですか？

A. DNS サーバーのパフォーマンス向上
B. 特定ドメインへの DNS クエリのみを許可する
C. DNS キャッシュの無効化
D. DNS over HTTPS のサポート

<details>
<summary>回答を表示</summary>

**回答: B. 特定ドメインへの DNS クエリのみを許可する**

**解説:**
DNS L7 ポリシーでは、ワークロードがクエリ可能なドメインを制限できます。matchPattern または matchName を使用すると、許可されたドメインのみがクエリされるようにし、データ流出や悪意あるドメインへのアクセスを防止できます。

</details>

### 8. CiliumEnvoyConfig でローカル Rate Limiting を設定するために使用される filter はどれですか？

A. envoy.filters.http.ratelimit
B. envoy.filters.http.local_ratelimit
C. envoy.filters.http.bandwidth_limit
D. envoy.filters.http.throttle

<details>
<summary>回答を表示</summary>

**回答: B. envoy.filters.http.local_ratelimit**

**解説:**
ローカル Rate Limiting では envoy.filters.http.local_ratelimit filter を使用します。この filter は token_bucket 設定を通じてリクエストレートを制限します。envoy.filters.http.ratelimit は、外部の Rate Limit Service と通信するグローバル Rate Limiting に使用されます。

</details>

### 9. Gateway API で HTTP -> HTTPS リダイレクトを設定するために使用される filter タイプはどれですか？

A. URLRewrite
B. RequestMirror
C. RequestRedirect
D. ResponseHeaderModifier

<details>
<summary>回答を表示</summary>

**回答: C. RequestRedirect**

**解説:**
Gateway API では、HTTP から HTTPS へのリダイレクトに RequestRedirect filter を使用します。scheme: https と statusCode: 301 を設定すると、恒久的なリダイレクトが構成されます。

</details>

### 10. Cilium Service Mesh におけるトラフィックミラーリング（shadowing）の目的は何ですか？

A. トラフィックの暗号化
B. 本番トラフィックをテスト環境に複製する
C. ロードバランシングの最適化
D. キャッシュの無効化

<details>
<summary>回答を表示</summary>

**回答: B. 本番トラフィックをテスト環境に複製する**

**解説:**
トラフィックミラーリングは、本番トラフィックのコピーを別の Service（例: 新バージョンを含むテスト環境）に送信します。これにより、ユーザーに影響を与えることなく、実トラフィックを用いて新バージョンをテストできます。これは request_mirror_policies を通じて設定されます。

</details>

### 11. CiliumEnvoyConfig で weighted_clusters を使用した canary Deployment において、total_weight の役割は何ですか？

A. リクエスト総数を制限する
B. 重みの合計に対する基準値を定義する
C. タイムアウト設定
D. 接続数の制限

<details>
<summary>回答を表示</summary>

**回答: B. 重みの合計に対する基準値を定義する**

**解説:**
total_weight は、個々の cluster の重みの合計に対する基準値を定義します。たとえば、total_weight: 100 を設定し、cluster A に 90、cluster B に 10 を割り当てると、トラフィックはそれぞれ 90% と 10% になります。

</details>

### 12. Gateway API HTTPRoute でヘッダーベースのルーティングを設定する際、matches セクションで使用するフィールドはどれですか？

A. headerMatchers
B. headers
C. requestHeaders
D. matchHeaders

<details>
<summary>回答を表示</summary>

**回答: B. headers**

**解説:**
HTTPRoute の matches セクションでは、ヘッダーベースのルーティングを設定するために headers フィールドを使用します。各ヘッダーに name と value を指定することで、特定のヘッダー値を持つリクエストを異なるバックエンドにルーティングできます。

</details>
