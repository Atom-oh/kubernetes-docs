# Observability Lab パート 3: MSA Deployment と Canary クイズ

> **最終更新**: February 22, 2026

Observability End-to-End Lab パート 3 で扱った MSA Deployment と canary release の概念に関する理解を確認しましょう。

---

1. 同じ Application を複数の Cluster にデプロイする場合、最も適した ArgoCD ApplicationSet Generator タイプはどれですか？
   - A) Cluster 名がハードコードされた List Generator
   - B) ラベルに基づいて登録済み Cluster を自動検出する Cluster Generator
   - C) Repository から Cluster 設定を読み取る Git Generator
   - D) 一時的な環境向けの Pull Request Generator

<details>
<summary>回答を表示</summary>

**回答: B) ラベルに基づいて登録済み Cluster を自動検出する Cluster Generator**

**解説:**
Cluster Generator は、ArgoCD に登録されている Cluster を動的に検出し、それぞれに対して Application を生成します。Cluster ラベル（例: `environment: production`、`region: us-east-1`）を使用することで、対象の Cluster を選択できます。Cluster の追加や削除では ApplicationSet 定義を変更せず、Cluster の登録とラベルの更新だけで済むため、ハードコードされたリストよりも保守しやすくなります。

</details>

---

2. ArgoCD における App-of-Apps パターンの主な利点は何ですか？
   - A) 必要な ArgoCD Application の総数を削減する
   - B) 親 Application が子 Application を管理する階層的な管理を可能にし、組織的な構造と一括操作を提供する
   - C) すべての Deployment を並列化することで sync パフォーマンスを改善する
   - D) Helm または Kustomize が不要になる

<details>
<summary>回答を表示</summary>

**回答: B) 親 Application が子 Application を管理する階層的な管理を可能にし、組織的な構造と一括操作を提供する**

**解説:**
App-of-Apps パターンでは、ルート Application の manifest に他の Application の定義を含めることで階層を作成します。これにより、複数 Application の一元管理、一貫した設定の継承、プラットフォーム全体の容易な bootstrap、および親を更新して複数 Application に変更を適用する機能が得られます。複数の microservice やマルチテナント環境を管理するプラットフォームチームにとって特に有用です。

</details>

---

3. Karpenter NodePool の weight と limits 設定は何を制御しますか？
   - A) weight は Pod ごとの CPU 割り当てを決定し、limits はメモリ境界を設定する
   - B) weight は NodePool 間の scheduling 優先度を設定し、limits は Karpenter がその Pool にプロビジョニングできる総リソースを上限設定する
   - C) weight は Node の料金 tier を制御し、limits は最大 Node 数を設定する
   - D) weight は Pod 密度を決定し、limits はネットワーク帯域幅を設定する

<details>
<summary>回答を表示</summary>

**回答: B) weight は NodePool 間の scheduling 優先度を設定し、limits は Karpenter がその Pool にプロビジョニングできる総リソースを上限設定する**

**解説:**
NodePool の weight（0～100）は、複数の NodePool が Pod の要件を満たせる場合の優先順位を決定します。weight が高いほど優先度も高くなります。limits は Karpenter がその NodePool にプロビジョニングできる最大リソース（CPU、memory）を定義し、無制限の scaling を防ぎます。これにより、優先する instance type 用の高 weight Pool に limits を設定してコストを制御し、容量超過時に備えて低 weight の fallback Pool を用意する、階層型 Infrastructure を構築できます。

</details>

---

4. KEDA の SQS scaler は、scaling の判断にどの metric タイプを使用できますか？
   - A) ApproximateNumberOfMessages のみ
   - B) ApproximateNumberOfMessages、ApproximateNumberOfMessagesNotVisible、または ApproximateNumberOfMessagesDelayed
   - C) custom CloudWatch metric のみ
   - D) SQS scaler は time-based scaling のみをサポートする

<details>
<summary>回答を表示</summary>

**回答: B) ApproximateNumberOfMessages、ApproximateNumberOfMessagesNotVisible、または ApproximateNumberOfMessagesDelayed**

**解説:**
KEDA の SQS scaler は複数の queue metric をサポートしています。`ApproximateNumberOfMessages`（処理待ちの可視メッセージ）、`ApproximateNumberOfMessagesNotVisible`（処理中だがまだ削除されていないメッセージ）、`ApproximateNumberOfMessagesDelayed`（delay queue 内のメッセージ）です。scaling 戦略に応じて選択できます。通常は backlog に基づく scaling には `ApproximateNumberOfMessages` を使用し、queue depth をより包括的に把握するには複数の metric を組み合わせます。

</details>

---

5. OpenTelemetry auto-instrumentation と manual instrumentation の主な違いは何ですか？
   - A) auto-instrumentation は manual instrumentation よりも詳細な trace を提供する
   - B) auto-instrumentation はコード変更なしでサポート対象 framework から telemetry を自動取得する一方、manual instrumentation では custom span と metric のために明示的な SDK 呼び出しが必要となる
   - C) manual instrumentation は auto-instrumentation に置き換えられ非推奨となっている
   - D) auto-instrumentation はインタープリタ型言語でのみ動作する

<details>
<summary>回答を表示</summary>

**回答: B) auto-instrumentation はコード変更なしでサポート対象 framework から telemetry を自動取得する一方、manual instrumentation では custom span と metric のために明示的な SDK 呼び出しが必要となる**

**解説:**
auto-instrumentation（agent、bytecode manipulation、または monkey-patching によるもの）は、Application コードを変更せずに、一般的な framework、library、runtime から telemetry を自動取得します。manual instrumentation では OTel SDK を使用して、span の明示的な作成、attribute の追加、metric の記録、log の出力を行います。ベストプラクティスは両方を組み合わせることです。標準的な framework のカバレッジには auto-instrumentation を使用し、business 固有の span と custom metric には manual instrumentation を使用します。

</details>

---

6. `-javaagent:opentelemetry-javaagent.jar` JVM 引数は、Java Service に対して何を有効にしますか？
   - A) JMX monitoring のみを有効にする
   - B) 一般的な Java framework と library を自動 instrumentation するための OTel Java agent をアタッチする
   - C) Java garbage collection telemetry を設定する
   - D) Java Flight Recorder integration を有効にする

<details>
<summary>回答を表示</summary>

**回答: B) 一般的な Java framework と library を自動 instrumentation するための OTel Java agent をアタッチする**

**解説:**
OpenTelemetry Java agent は bytecode instrumentation を使用し、一般的な Java framework（Spring、JAX-RS、gRPC）、HTTP client（Apache HttpClient、OkHttp）、database（JDBC、Hibernate）、および messaging system（Kafka、RabbitMQ）から telemetry を自動取得します。この agent は JVM 起動時に `-javaagent` によってアタッチされ、コード変更を必要としません。設定は環境変数（例: `OTEL_EXPORTER_OTLP_ENDPOINT`、`OTEL_SERVICE_NAME`）で行います。

</details>

---

7. Argo Rollouts の canary Deployment において、AnalysisTemplate はどのような役割を果たしますか？
   - A) security scanning 用の container image 分析を定義する
   - B) canary release を続行するか rollback するかを決定する metric query と成功基準を指定する
   - C) canary 実行中の traffic 分割割合を設定する
   - D) progressive delivery 中の replica 数を管理する

<details>
<summary>回答を表示</summary>

**回答: B) canary release を続行するか rollback するかを決定する metric query と成功基準を指定する**

**解説:**
AnalysisTemplate は canary release の自動分析を定義します。metric provider（Prometheus、Datadog、CloudWatch）、評価する query（例: error rate、latency）、成功・失敗の threshold、および測定 interval を指定します。rollout 中、Argo Rollouts は template から AnalysisRun を作成し、metric を継続的に評価します。基準を満たさなかった場合、rollout は自動的に pause または rollback されるため、手動介入なしで安全な progressive delivery を実現できます。

</details>

---

8. `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))` のような成功率 PromQL query は何を測定しますか？
   - A) 過去 5 分間の成功した request の総数
   - B) HTTP 2xx response と全 response の比率、すなわち成功率
   - C) 成功した request の平均 response time
   - D) 一意の成功ユーザー数

<details>
<summary>回答を表示</summary>

**回答: B) HTTP 2xx response と全 response の比率、すなわち成功率**

**解説:**
この PromQL query は、成功 request（regex `2..` に一致する HTTP 2xx status code）を全 request で除算して、成功率を計算します。どちらも 5 分間の rate として計算されます。`rate()` 関数は window 内の 1 秒あたりの平均を計算し、`sum()` はすべての label dimension にわたって集計します。結果は 0～1 の比率であり、通常はパーセンテージで表示されます。これは Service の信頼性に関する重要な SLI です。

</details>

---

9. Argo Rollouts AnalysisRun が FAIL status を返した場合、自動的に何が起こりますか？
   - A) rollout は続行するが alert を送信する
   - B) rollout は pause し、手動介入を待つ
   - C) rollout は自動的に abort されて canary を scale down し、stable version に全 traffic を復元する
   - D) AnalysisRun は異なる parameter で再起動する

<details>
<summary>回答を表示</summary>

**回答: C) rollout は自動的に abort されて canary を scale down し、stable version に全 traffic を復元する**

**解説:**
AnalysisRun が失敗すると（metric が failure threshold を超えると）、Argo Rollouts は自動的に rollback をトリガーします。canary ReplicaSet は zero まで scale され、すべての traffic は stable version に戻り、Rollout status は "Degraded" になります。この自動 rollback は progressive delivery の主要な安全機能です。問題のある release は人手を介さずに自動的に元に戻されるため、不適切な Deployment の blast radius を最小限に抑えられます。

</details>

---

10. OpenTelemetry SDK を使用する際、W3C TraceContext の context propagation が重要なのはなぜですか？
    - A) metric 収集に必要である
    - B) HTTP header で Service 境界をまたいで trace context（trace ID、span ID、flag）を渡すことで、distributed tracing を可能にする
    - C) log compression を改善する
    - D) gRPC Service でのみ必要である

<details>
<summary>回答を表示</summary>

**回答: B) HTTP header で Service 境界をまたいで trace context（trace ID、span ID、flag）を渡すことで、distributed tracing を可能にする**

**解説:**
W3C TraceContext は、HTTP header（`traceparent`、`tracestate`）を介して distributed trace 情報を伝播するための標準化された形式です。Service A が Service B を呼び出す際、context propagation は trace ID と親 span ID を渡し、Service B の span を Service A の trace にリンクできるようにします。適切に伝播しない場合、trace は Service 境界で途切れ、完全な request flow ではなく接続されていない segment として表示されます。OTel SDK は設定されていればこれを自動的に処理しますが、Service は header を転送する必要があります。

</details>
