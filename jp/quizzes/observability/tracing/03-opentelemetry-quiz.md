# OpenTelemetry クイズ

OpenTelemetry についての理解度を確認しましょう。

---

1. OpenTelemetry がサポートする 3 つのシグナルは何ですか？
   - A) Logs、Metrics、Events
   - B) Traces、Metrics、Logs
   - C) Spans、Counters、Logs
   - D) Traces、Alerts、Logs

<details>
<summary>回答を表示</summary>

**回答: B) Traces、Metrics、Logs**

**解説:**
OpenTelemetry は、可観測性の 3 つの中核シグナルである Traces（分散トレーシング）、Metrics、Logs を標準化します。これら 3 つのシグナルを統合的に収集して関連付けることで、包括的なシステム可観測性を実現できます。

</details>

---

2. OpenTelemetry Collector のコンポーネントの正しい順序はどれですか？
   - A) Processors -> Receivers -> Exporters
   - B) Exporters -> Processors -> Receivers
   - C) Receivers -> Processors -> Exporters
   - D) Receivers -> Exporters -> Processors

<details>
<summary>回答を表示</summary>

**回答: C) Receivers -> Processors -> Exporters**

**解説:**
OTEL Collector のパイプラインは、Receivers（データ取り込み）-> Processors（データ処理・変換）-> Exporters（バックエンドへの送信）という構造です。Receivers はさまざまな形式のデータを受け入れ、Processors はバッチ処理、フィルタリング、属性の追加などを実行し、Exporters は処理済みのデータを送信先へ送ります。

</details>

---

3. OpenTelemetry の auto-instrumentation の利点ではないものはどれですか？
   - A) コード変更なしでの Instrumentation
   - B) 迅速な導入
   - C) ビジネスロジックのきめ細かなトレーシング
   - D) 一貫したメタデータ

<details>
<summary>回答を表示</summary>

**回答: C) ビジネスロジックのきめ細かなトレーシング**

**解説:**
Auto-instrumentation は、コードを変更せずに HTTP、データベース、メッセージキューなどの一般的なライブラリ呼び出しを自動的にトレースします。ただし、ビジネスロジック内の詳細な操作やカスタム Metrics には manual instrumentation が必要です。auto-instrumentation と manual instrumentation を併用するのが一般的です。

</details>

---

4. OTEL Collector の tail_sampling processor は、どのような場合に head-based sampling より有利ですか？
   - A) リソース使用量を最小化する場合
   - B) エラーまたはレイテンシーが発生したリクエストを見逃せない場合
   - C) 実装をシンプルにする必要がある場合
   - D) サンプリングの判断を高速に行う必要がある場合

<details>
<summary>回答を表示</summary>

**回答: B) エラーまたはレイテンシーが発生したリクエストを見逃せない場合**

**解説:**
Tail-based sampling は、リクエスト完了後に結果（エラー、レイテンシーなど）に基づいてサンプリングするかどうかを判断します。これにより、重要なリクエスト（エラーの発生、応答時間の超過）を見逃すことがありません。一方、head-based sampling はリクエスト開始時に判断するため、より少ないリソース使用量でシンプルに実装できますが、重要なリクエストを見逃す可能性があります。

</details>

---

5. OpenTelemetry SDK における Resource の役割は何ですか？
   - A) ネットワーク接続管理
   - B) テレメトリデータを生成するエンティティの識別
   - C) データ圧縮
   - D) 認証トークン管理

<details>
<summary>回答を表示</summary>

**回答: B) テレメトリデータを生成するエンティティの識別**

**解説:**
Resource は、テレメトリデータを生成するエンティティ（service、host、container など）を識別するメタデータです。データの発生元を明確にするため、service.name、service.version、deployment.environment などの属性が含まれます。この情報はすべてのテレメトリデータに自動的に付加されます。

</details>

---

6. EKS で最もリソース効率のよい OTEL Collector のデプロイパターンはどれですか？
   - A) Sidecar パターン
   - B) DaemonSet パターン
   - C) Gateway パターン
   - D) Deployment パターン

<details>
<summary>回答を表示</summary>

**回答: B) DaemonSet パターン**

**解説:**
DaemonSet パターンは、ノードごとに 1 つの Collector だけを実行するため、リソース効率に優れています。Sidecar パターンは Pod ごとに Collector を実行するため、リソースのオーバーヘッドが大きくなります。Gateway パターンは集中管理できますが、単一障害点になる可能性があります。通常は、収集に DaemonSet、処理・送信に Gateway を組み合わせることが推奨されます。

</details>

---

7. OpenTelemetry Operator を使用して auto-instrumentation を注入するために Pod に適用する annotation はどれですか？
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>回答を表示</summary>

**回答: B) instrumentation.opentelemetry.io/inject-java: "true"**

**解説:**
OpenTelemetry Operator は、`instrumentation.opentelemetry.io/inject-{language}` 形式の annotation を使用します。言語固有の annotation には、inject-java、inject-python、inject-nodejs、inject-dotnet、inject-go などがあります。これらの annotation を持つ Pod には、Instrumentation agent が自動的に注入されます。

</details>

---

8. OTEL Collector の設定における memory_limiter processor の役割は何ですか？
   - A) データ圧縮
   - B) メモリ不足時のデータ損失防止
   - C) キャッシュ管理
   - D) ネットワークバッファ管理

<details>
<summary>回答を表示</summary>

**回答: B) メモリ不足時のデータ損失防止**

**解説:**
memory_limiter processor は、Collector のメモリ使用量を監視し、制限します。メモリ使用量が limit_mib に達すると、OOM（Out of Memory）によるデータ損失を防ぐため、新規データの取り込みを拒否します。spike_limit_mib は、急激なメモリスパイクに備えるバッファを提供します。

</details>

---

9. OpenTelemetry の W3C Trace Context 標準において、traceparent header のコンポーネントではないものはどれですか？
   - A) version
   - B) trace-id
   - C) parent-id
   - D) span-name

<details>
<summary>回答を表示</summary>

**回答: D) span-name**

**解説:**
W3C Trace Context の traceparent header 形式は `version-trace_id-parent_id-trace_flags` です。version は形式のバージョン、trace_id はトレース全体の識別子、parent_id は親 Span の ID、trace_flags はサンプリングフラグです。span-name は Span 内に保存され、伝播 header には含まれません。

</details>

---

10. OTEL Collector パイプラインで複数のバックエンドにデータを送信するには、どのように設定しますか？
    - A) バックエンドごとに別々の Collector を実行する
    - B) exporters 配列に複数の exporter を列挙する
    - C) 1 つの exporter に複数の endpoint を設定する
    - D) fanout processor を使用する

<details>
<summary>回答を表示</summary>

**回答: B) exporters 配列に複数の exporter を列挙する**

**解説:**
OTEL Collector のパイプライン設定では、exporters 配列に複数の exporter を列挙すると、同じデータがすべてのバックエンドに送信されます。例: `exporters: [otlp/tempo, awsxray, datadog]`。これにより、1 つの Collector で複数の可観測性バックエンドを同時に使用できます。

</details>

---
