# OpenTelemetry クイズ

> **最終更新**: September 13, 2026

OpenTelemetry についての理解を確認しましょう。

---

1. このガイドが焦点を当てている 3 つのコアシグナルはどれですか？
   - A) Logs、Metrics、Events
   - B) Traces、Metrics、Logs
   - C) Spans、Counters、Logs
   - D) Traces、Alerts、Logs

<details>
<summary>回答を表示</summary>

**回答: B) Traces、Metrics、Logs**

**解説:**
このガイドでは、traces、metrics、logs に焦点を当てています。OpenTelemetry では profiling のサポートも開発されていますが、安定性はシグナル、コンポーネント、言語によって異なります。相関付けには、3 つの exporter を有効にするだけではなく、互換性のある resource attributes と伝播された context が必要です。

</details>

---

2. OpenTelemetry Collector コンポーネントの正しい順序はどれですか？
   - A) Processors -> Receivers -> Exporters
   - B) Exporters -> Processors -> Receivers
   - C) Receivers -> Processors -> Exporters
   - D) Receivers -> Exporters -> Processors

<details>
<summary>回答を表示</summary>

**回答: C) Receivers -> Processors -> Exporters**

**解説:**
OTEL Collector パイプラインは、Receivers（データ取り込み）-> Processors（データ処理・変換）-> Exporters（バックエンドへの送信）として構成されます。Receivers はさまざまな形式のデータを受け取り、Processors はバッチ処理、フィルタリング、属性の追加などを実行し、Exporters は処理済みデータを送信先に送ります。

</details>

---

3. OpenTelemetry における自動インストルメンテーションの利点ではないものはどれですか？
   - A) コード変更なしのインストルメンテーション
   - B) 迅速な導入
   - C) きめ細かなビジネスロジックのトレーシング
   - D) 一貫したメタデータ

<details>
<summary>回答を表示</summary>

**回答: C) きめ細かなビジネスロジックのトレーシング**

**解説:**
自動インストルメンテーションは、コードを変更せずに、HTTP、データベース、メッセージキューなどの一般的なライブラリ呼び出しを自動的にトレースします。ただし、ビジネスロジック内の詳細な操作やカスタムメトリクスには手動インストルメンテーションが必要です。自動インストルメンテーションと手動インストルメンテーションを併用することが一般的です。

</details>

---

4. head-based sampling と比較して、Collector の tail_sampling processor はどのような場合に有用ですか？
   - A) リソース使用量を最小化する場合
   - B) 観測された span のステータスと継続時間を sampling に反映すべき場合
   - C) 実装をシンプルにする必要がある場合
   - D) sampling の判断を迅速に行う必要がある場合

<details>
<summary>回答を表示</summary>

**回答: B) 観測された span のステータスと継続時間を sampling に反映すべき場合**

**解説:**
Collector 0.160.0 のデフォルト `trace-complete` 戦略では、判断タイマーが起動した時点で蓄積された spans を使用して評価します。この名前は、リクエストまたは trace が完了していることを証明するものではありません。head sampling によってすでに破棄された spans は復元できません。遅延して到着する spans、容量制限、再試行、ルーティングの変更は、保持に影響を与える可能性があります。状態を持つ tail sampling では、trace の spans が同じ sampling Collector に到達する必要があります。すべてのエラーまたは低速なリクエストが保持されることを保証するものではありません。

</details>

---

5. OpenTelemetry SDK における Resource の役割は何ですか？
   - A) ネットワーク接続の管理
   - B) telemetry データを生成するエンティティの識別
   - C) データ圧縮
   - D) 認証トークンの管理

<details>
<summary>回答を表示</summary>

**回答: B) telemetry データを生成するエンティティの識別**

**解説:**
Resource は telemetry の生成元を識別します。たとえば、`service.name`、`service.version`、`deployment.environment.name` で識別します。構成された SDK/provider は、これを出力されるデータに関連付けます。Kubernetes、クラウド、またはカスタムの identity attributes には、適切な設定または detector が必要です。これらすべてが自動的に検出されるわけではありません。

</details>

---

6. 通常、各対象 node で 1 つの Collector を実行する Kubernetes workload はどれですか？
   - A) Sidecar パターン
   - B) DaemonSet パターン
   - C) Gateway パターン
   - D) Deployment パターン

<details>
<summary>回答を表示</summary>

**回答: B) DaemonSet パターン**

**解説:**
DaemonSet は各対象 node に Pod を配置します。selectors、taints、scheduling constraints によって対象かどうかが決まります。これは EKS Fargate ではサポートされていません。Sidecars は application Pod を共有し、gateways は複数の replicas を持つ可能性がある中央層を使用します。すべての状況で最もリソース効率のよいパターンはありません。実際の signal volume、node/Pod 数、分離、可用性、stateful processing の要件を比較してください。DaemonSet の前に置かれた ClusterIP Service は、自動的にローカル node へルーティングしません。

</details>

---

7. OpenTelemetry Operator を使用した自動インストルメンテーション injection のために Pod に適用する annotation はどれですか？
   - A) `otel.io/inject: "true"`
   - B) `instrumentation.opentelemetry.io/inject-java: "true"`
   - C) `opentelemetry.io/auto: "enabled"`
   - D) `trace.otel.io/enabled: "true"`

<details>
<summary>回答を表示</summary>

**回答: B) instrumentation.opentelemetry.io/inject-java: "true"**

**解説:**
Operator は言語固有の injection annotations を使用します。Deployment の場合は、`spec.template.metadata.annotations` に配置し、正しい namespace にある既存の Instrumentation resource を参照します。injection を成功させるには、動作する webhook とサポート対象の言語/runtime 設定も必要です。既存の Pods が後からインストルメンテーションされることはありません。Go およびその他の言語固有の前提条件は個別に確認する必要があります。

</details>

---

8. OTEL Collector 設定における memory_limiter processor の役割は何ですか？
   - A) データ圧縮
   - B) 設定されたメモリしきい値を超えた場合に backpressure を適用する
   - C) キャッシュ管理
   - D) ネットワークバッファ管理

<details>
<summary>回答を表示</summary>

**回答: B) 設定されたメモリしきい値を超えた場合に backpressure を適用する**

**解説:**
`limit_mib` はハードリミットであり、ソフトリミットは `limit_mib - spike_limit_mib` です。ソフトリミットを超えると、processor は再試行可能なエラーでデータを拒否します。ハードリミットを超えると、garbage collection も強制します。アップストリームの retry/backpressure の動作が重要です。拒否されたデータは再試行されない場合に失われる可能性があります。コンテナのメモリ制限の下に余裕を確保してください。この processor は永続ストレージでも、OOM/データ損失を絶対に防ぐ保証でもありません。

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
OpenTelemetry は W3C Trace Context 標準を使用します。`traceparent` のフィールドは version、trace ID、parent ID、trace flags です。parent ID は送信元の span を識別し、flags には sampled bit が含まれます。span 名はこの header には含まれません。context を伝播すること自体は、span の記録や export を行いません。

</details>

---

10. OTEL Collector パイプラインで複数のバックエンドにデータを送信するには、どのように設定しますか？
    - A) 各バックエンドに対して別々の Collectors を実行する
    - B) exporters array に複数の exporters を列挙する
    - C) 単一の exporter に複数の endpoints を設定する
    - D) fanout processor を使用する

<details>
<summary>回答を表示</summary>

**回答: B) exporters array に複数の exporters を列挙する**

**解説:**
パイプラインの signal をサポートするように構成された exporters を列挙します。たとえば、これらのコンポーネントを含む distribution で traces を扱う場合は、`exporters: [otlp/tempo, awsxray, datadog]` とします。fan-out はバックエンド間のアトミックトランザクションではありません。exporter エラー、queues、retries、transformations、バックエンドによる受け入れの違いにより、保持される結果が異なる可能性があります。

</details>

---

[ガイドに戻る](../../../observability/tracing/03-opentelemetry.md)
