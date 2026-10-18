# Linkerd トラフィック管理クイズ

[メンテナンス対象のトラフィック管理ガイド](../../../service-mesh/linkerd/03-traffic-management.md)に基づいています（2026 年 10 月 16 日確認）。

### 1. ServiceProfile でルートごとに設定できないものはどれですか？

- A. タイムアウト
- B. リトライ可否
- C. ロードバランサーのアルゴリズム
- D. パス条件

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** ServiceProfile のルートでは、タイムアウト、`isRetryable`、method／path 条件を指定できます。ロードバランサーのアルゴリズムは選択できません。これは、あらゆる構成で使えるグローバルなアルゴリズム切り替えが存在するという意味ではありません。

</details>

### 2. Linkerd の HTTP ロードバランシングを説明しているのはどれですか？

- A. 厳密なラウンドロビン
- B. 常に接続数が最少の宛先を選ぶ
- C. レイテンシーを考慮した EWMA の動作
- D. レイテンシー情報を使わず、常にランダムな宛先を選ぶ

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** EWMA はレイテンシーの低い候補を選びやすくしますが、すべてのリクエストで、表示上のスコアが最小の宛先が必ず選ばれるわけではありません。HTTP はリクエスト単位で、TCP は接続単位で負荷分散します。

</details>

### 3. 従来の TrafficSplit リソースを定義する仕様はどれですか？

- A. CNCF
- B. SMI（Service Mesh Interface）
- C. OpenAPI
- D. gRPC

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** TrafficSplit は SMI リソースです。Linkerd の TrafficSplit／linkerd-smi は非推奨で、拡張機能と CRD が必要です。新しい構成では、メンテナンス対象のガイドに従ってサポートされている Gateway API HTTPRoute を使います。古いリソースを適用しただけでは、その拡張機能はインストールされません。

</details>

### 4. ServiceProfile の `retryRatio: 0.2` はリトライ予算にどう加算されますか？

- A. すべてのリクエストのちょうど 20% をリトライする
- B. 失敗したリクエストのうち、20% だけをリトライできる
- C. `minRetriesPerSecond` に加えて、元のリクエスト数に比例した許容量を加える
- D. 20 秒ごとに予算をリセットする

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** `minRetriesPerSecond` も許容量を加えるため、比率の分は合計リトライ数を厳密に 20% までに制限する上限ではありません。`ttl` は参照・保持する時間窓であり、定期リセットの間隔ではありません。実際のリトライは適格性、バッファリング、deadline によっても制限されます。

</details>

### 5. ServiceProfile に必要なアプリケーション操作を推測する情報として、単独では不十分なものはどれですか？

- A. OpenAPI 仕様
- B. Tap で観察したライブトラフィック
- C. Protobuf のサービス定義
- D. Kubernetes Service の selector とポート一覧

<details>
<summary>解答を表示</summary>

**解答: D**

**解説:** CLI は OpenAPI／Protobuf からの生成をサポートし、Viz は Tap に基づく生成をサポートします。短い Service 名と `-n` を使ってください。Tap コマンドには位置引数として Service 名も必要です。サンプリングされたトラフィックは API の完全な一覧ではないため、生成された match とリトライの安全性を確認してください。

</details>

### 6. backend の weight について正しい説明はどれですか？

- A. 合計は必ず 100 にする
- B. 合計は必ず 1 にする
- C. 有効な非負の相対値を使い、合計は正の値にする。90/10 と 9/1 は同じ比率を表す
- D. 負の weight や合計 0 も常に使える

<details>
<summary>解答を表示</summary>

**解答: C**

**解説:** weight は相対値です。選択したリソースの schema と backend の有効性にも従います。合計を 100 にする必要はなく、設定した比率が短時間のリクエスト数に厳密に反映される保証もありません。新しい例では HTTPRoute を使い、TrafficSplit は従来の SMI 経路です。

</details>

### 7. HTTPRoute のリクエスト条件に含まれないものはどれですか？

- A. HTTP header
- B. HTTP path
- C. HTTP method
- D. 送信元 IP

<details>
<summary>解答を表示</summary>

**解答: D**

**解説:** HTTPRoute は header／path／method による条件をサポートします。Cookie header の完全一致では header 全体の値が比較され、個々の Cookie ペアを比較するわけではありません。呼び出し元が指定できる cohort／debug header は認可手段ではありません。送信元アドレスの制限には、適切なネットワーク／セキュリティポリシーを使ってください。

</details>

### 8. このガイドの Linkerd 用カスタム Flagger MetricTemplate が使う provider はどれですか？

- A. Kubernetes Metrics Server
- B. Prometheus
- C. 宣言されていない InfluxDB Service
- D. 必須の Datadog backend

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** これらの template は、namespace／Deployment／通信方向を明示して Linkerd Viz Prometheus に問い合わせます。Flagger は他の provider にも対応しています。この例は `gatewayapi:v1` routing とカスタムメトリクス名を使います。Flagger 1.45.0 では `meshProvider:linkerd` は引き続き従来の SMI router を選択します。

</details>

### 9. ServiceProfile の route に一致する `isRetryable: false` は何を意味しますか？

- A. 一致するリクエストはすべて失敗する
- B. ServiceProfile の仕組みでは、その route をリトライしない
- C. タイムアウトポリシーをすべて無視する
- D. route を無効にする

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** リクエストは通常どおり転送されます。この設定は、クライアント、SDK、別のプロキシによるリトライを止めません。現在の annotation 経路では、`limit:0` は edge-26.10.1 で確実な無効化手段ではありません。Service の既定設定ではリトライを使わず、対象の read route にだけ明示的に有効化してください。

</details>

### 10. Linkerd の HTTP circuit breaking はどのように構成しますか？

- A. 自動インストールされる CircuitBreaker CRD
- B. 明示的に有効化する Service failure-accrual annotation
- C. 接続に 5 回失敗すると必ず動く既定ルール
- D. 定期的な合成 readiness probe のループ

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** Failure accrual は既定では無効で、対象 Service に ServiceProfile がある場合は併用できません。連続失敗のポリシーでは、サポート対象の応答失敗が既定で 7 回続くと対象になります。backoff 後の回復確認は、合成 probe の定期実行ではなく、実際のアプリケーションリクエストで行います。

</details>

### 11. マルチクラスターの mirror Service として表される公開サービスを、クライアントが明示的に呼び出すにはどうしますか？

- A. 架空の TrafficMirror CRD を適用する
- B. 必要な接続性とポリシーを用意し、mirror Service の DNS 名を呼び出す
- C. すべてのローカルリクエストが自動的に複製される
- D. mirror Service は呼び出せない

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** マルチクラスターのサービスミラーリングは、リモートサービスの検出とルーティングを提供します。その DNS 名を呼び出すとリクエストはリモートに送られますが、シャドーテストのために自動複製されるわけではありません。リクエストのミラーリングは別機能であり、選択した実装とバージョンでサポート状況を確認してください。

</details>

### 12. ServiceProfile の route で timeout を省略した場合、どうなりますか？

- A. profile に自動で 5 秒 timeout が設定される
- B. ServiceProfile のその field では timeout を追加しない
- C. 直ちに失敗する
- D. ほかのレイヤーの timeout もすべて解除される

<details>
<summary>解答を表示</summary>

**解答: B**

**解説:** その field による route timeout は追加されませんが、アプリケーション、クライアント、transport、proxy、load balancer の制限は別に適用される場合があります。エンドツーエンドの無期限実行が保証されるわけではありません。ストリーミングの deadline とキャンセルは、アプリケーションの動作を考慮して明示的に設計してください。

</details>
