# Observability Stack クイズ

> **関連ドキュメント**: [Observability Stack](../../ops/09-observability-stack.md)

## 選択問題

### 1. LGTM observability stack のコンポーネントは何ですか？

- A) Linux, Git, Terminal, Make
- B) Loki (logs), Grafana (visualization), Tempo (traces), Mimir/Prometheus (metrics)
- C) Lambda, Gateway, Transit, Monitor
- D) Load balancer, Gateway, TLS, Mesh

<details>
<summary>答えを表示</summary>

**回答: B) Loki (logs), Grafana (visualization), Tempo (traces), Mimir/Prometheus (metrics)**

**解説:**
LGTM は Grafana Labs の observability stack で、log aggregation のための Loki、visualization と dashboard のための Grafana、distributed tracing のための Tempo、metrics のための Mimir（または Prometheus）で構成されます。これらのコンポーネントはシームレスに統合されます。

</details>

### 2. Loki の SimpleScalable と Distributed deployment modes の違いは何ですか？

- A) SimpleScalable はテスト専用である
- B) SimpleScalable は read/write paths を分離し、Distributed はより細かな component separation を追加する
- C) Distributed は非推奨である
- D) これらは同一である

<details>
<summary>答えを表示</summary>

**回答: B) SimpleScalable は read/write paths を分離し、Distributed はより細かな component separation を追加する**

**解説:**
SimpleScalable mode は Loki を、独立してスケールできる read paths と write paths に分割します。Distributed mode は、大規模環境で最大限の scalability と operational flexibility を実現するために、components（ingesters、distributors、queriers など）をさらに分離します。

</details>

### 3. Tempo における tail-based sampling の目的は何ですか？

- A) log files の末尾をサンプリングするため
- B) 完全な trace を確認した後に sampling decisions を行うため
- C) query latency を削減するため
- D) trace data を圧縮するため

<details>
<summary>答えを表示</summary>

**回答: B) 完全な trace を確認した後に sampling decisions を行うため**

**解説:**
Tail-based sampling は、trace が完了するまで待ってから保存するかどうかを決定します。これにより、normal traces はサンプリングしつつ、すべての error traces や slow traces を保持できます。head-based sampling は trace の開始時に判断するため、これは実現できません。

</details>

### 4. observability stack において OTEL Collector はどのような役割を果たしますか？

- A) metrics を長期保存する
- B) applications から telemetry data を受信、処理、export する
- C) Grafana dashboards を作成する
- D) user authentication を管理する

<details>
<summary>答えを表示</summary>

**回答: B) applications から telemetry data を受信、処理、export する**

**解説:**
OpenTelemetry Collector は telemetry pipeline として機能し、applications から traces、metrics、logs を受信し、それらを処理（batching、filtering、enriching）して、Tempo、Prometheus、Loki などの backends に export します。

</details>

### 5. Amazon Managed Prometheus (AMP) は Prometheus とどのように統合されますか？

- A) Prometheus を完全に置き換える
- B) Prometheus が remote_write を使用して storage のために metrics を AMP に送信する
- C) AMP が Prometheus sidecar として実行される
- D) AMP は CloudWatch でのみ動作する

<details>
<summary>答えを表示</summary>

**回答: B) Prometheus が remote_write を使用して storage のために metrics を AMP に送信する**

**解説:**
AMP は Prometheus metrics のための managed で scalable な storage backend を提供します。Prometheus は引き続き local で scrape と rule evaluation を行いますが、`remote_write` を使用して metrics を AMP に送信します。その後、Grafana が PromQL を使用して AMP に query します。

</details>

### 6. 推奨される Loki label design strategy は何ですか？

- A) flexibility のためにできるだけ多くの labels を使用する
- B) index explosion を避けるために、bounded で low-cardinality な labels を使用する
- C) labels を一切使用しない
- D) timestamp labels のみを使用する

<details>
<summary>答えを表示</summary>

**回答: B) index explosion を避けるために、bounded で low-cardinality な labels を使用する**

**解説:**
High-cardinality labels（user IDs や request IDs など）は過剰な streams を作成し、index を肥大化させます。Labels は low-cardinality（namespace、app、environment）にし、high-cardinality data は LogQL で filtering できるように log content に含めるべきです。

</details>

### 7. log collection における Promtail と Grafana Alloy の違いは何ですか？

- A) Promtail は metrics のみを収集する
- B) Alloy は logs、metrics、traces をサポートする unified agent であり、Promtail は Loki 専用である
- C) Promtail は Alloy より新しい
- D) Alloy は Kubernetes をサポートしていない

<details>
<summary>答えを表示</summary>

**回答: B) Alloy は logs、metrics、traces をサポートする unified agent であり、Promtail は Loki 専用である**

**解説:**
Promtail は logs を Loki に送信するために特化して作られています。Grafana Alloy（旧 Agent）は、OpenTelemetry と native receivers を使用して logs、metrics、traces を扱う unified collector であり、必要な agents の数を減らします。

</details>

### 8. Loki と Tempo の間で Grafana datasource linking をどのように設定しますか？

- A) 設定なしで自動的に link される
- B) Tempo datasource を指す derived fields を Loki datasource に設定する
- C) 別の linking plugin をインストールする
- D) 共通の database に data を export する

<details>
<summary>答えを表示</summary>

**回答: B) Tempo datasource を指す derived fields を Loki datasource に設定する**

**解説:**
Grafana の Loki datasource settings で、logs から trace IDs を抽出して Tempo datasource に link するための regex を持つ derived fields を設定します。これにより、log lines から関連する traces へのクリック可能な links が作成されます。

</details>

### 9. Tempo の compactor component の目的は何ですか？

- A) network traffic を圧縮するため
- B) trace blocks を merge し、retention を管理するため
- C) TraceQL queries をコンパイルするため
- D) dashboard loading time を短縮するため

<details>
<summary>答えを表示</summary>

**回答: B) trace blocks を merge し、retention を管理するため**

**解説:**
Compactor は storage efficiency のために小さな trace blocks を大きなものに merge し、期限切れ data を削除することで retention policies を適用します。Distributed mode では別の process として、または monolithic binary 内で実行されます。

</details>

### 10. OTEL Collector processors を設定するとき、batch processor は何をしますか？

- A) traces に batch IDs を割り当てる
- B) efficiency を向上させるため、export 前に telemetry を batches にグループ化する
- C) database batch operations を処理する
- D) Kubernetes で batch jobs を作成する

<details>
<summary>答えを表示</summary>

**回答: B) efficiency を向上させるため、export 前に telemetry を batches にグループ化する**

**解説:**
Batch processor は telemetry data を蓄積し、size または timeout thresholds に基づいて batches で送信します。これにより outgoing requests の数が減り、compression が向上し、receiving backends への load が低減されます。

</details>
