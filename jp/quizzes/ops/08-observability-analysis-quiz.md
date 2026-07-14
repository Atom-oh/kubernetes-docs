# Observability Analysis クイズ

> **関連ドキュメント**: [Observability Analysis](../../ops/08-observability-analysis.md)

## 選択問題

### 1. 分散トレーシングにおける Trace ID とは何ですか？

- A) 単一の span に対する一意の識別子
- B) サービスをまたいでリクエスト内のすべての span を関連付ける一意の識別子
- C) サービスの名前
- D) タイムスタンプ

<details>
<summary>回答を表示</summary>

**回答: B) サービスをまたいでリクエスト内のすべての span を関連付ける一意の識別子**

**解説:**
Trace ID は、リクエストがシステムに入ったときに割り当てられ、すべての下流サービス呼び出しへ伝播される一意の識別子です。同じリクエストを処理した異なるサービスの logs、spans、metrics を結び付けることができます。

</details>

### 2. 特定の namespace で error logs を見つける正しい LogQL クエリはどれですか？

- A) `SELECT * FROM logs WHERE level='error'`
- B) `{namespace="production"} |= "error"`
- C) `logs.namespace.production.error`
- D) `grep error /var/log/production`

<details>
<summary>回答を表示</summary>

**回答: B) `{namespace="production"} |= "error"`**

**解説:**
LogQL は、波かっこ内の label selector に続けて filter expression を使用します。`{namespace="production"}` はその namespace の logs を選択し、`|= "error"` は "error" を含む行で絞り込みます。`|=` operator は大文字小文字を区別する substring matching を行います。

</details>

### 3. RED method は何を測定しますか？

- A) Resource usage、Events、Duration
- B) Rate、Errors、Duration（サービス向け）
- C) Requests、Endpoints、Data
- D) Replicas、Endpoints、Deployments

<details>
<summary>回答を表示</summary>

**回答: B) Rate、Errors、Duration（サービス向け）**

**解説:**
RED method は、Rate（1 秒あたりのリクエスト数）、Errors（失敗したリクエスト率）、Duration（レイテンシ分布）を通じてサービスの健全性を測定します。リクエスト駆動型サービスに最適化されており、リソース向けの USE method を補完します。

</details>

### 4. USE method は何を測定しますか？

- A) User、Session、Events
- B) Utilization、Saturation、Errors（リソース向け）
- C) Upload、Storage、Encryption
- D) Units、Scale、Efficiency

<details>
<summary>回答を表示</summary>

**回答: B) Utilization、Saturation、Errors（リソース向け）**

**解説:**
USE method は、Utilization（使用率）、Saturation（キューの深さ/待機）、Errors（エラー数）を通じてリソースの健全性を測定します。CPU、memory、network、storage リソースの分析向けに設計されています。

</details>

### 5. Prometheus における Exemplars とは何ですか？

- A) 設定ファイルの例
- B) metric から trace への関連付けを可能にする、metric samples に付与された Trace IDs
- C) Prometheus クエリのサンプル
- D) テンプレート dashboards

<details>
<summary>回答を表示</summary>

**回答: B) metric から trace への関連付けを可能にする、metric samples に付与された Trace IDs**

**解説:**
Exemplars は、特定の時点で metric samples と一緒に保存される Trace IDs です。Grafana で histogram や counter を表示しているとき、exemplars により、特定の metric data point を生成した trace へ直接クリックして移動できます。

</details>

### 6. histogram から 95 パーセンタイルの latency を計算する PromQL 関数はどれですか？

- A) `avg()`
- B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- C) `max()`
- D) `percentile(95, latency)`

<details>
<summary>回答を表示</summary>

**回答: B) `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`**

**解説:**
`histogram_quantile()` は histogram bucket counts から quantile を計算します。最初の引数（0.95）は percentile で、`_bucket` metric の rate に対して動作します。これにより、リクエストの 95% が完了する latency の上限値が得られます。

</details>

### 7. TraceQL は何に使用されますか？

- A) Prometheus alerts の作成
- B) Grafana Tempo での distributed traces のクエリ
- C) log aggregation rules の作成
- D) service mesh policies の定義

<details>
<summary>回答を表示</summary>

**回答: B) Grafana Tempo での distributed traces のクエリ**

**解説:**
TraceQL は、traces を検索するための Tempo のクエリ言語です。サービス名、span 名、duration、attributes、status によるフィルタリングをサポートします。例: `{resource.service.name="api-gateway" && duration>1s}` は遅い API gateway traces を見つけます。

</details>

### 8. LogQL で JSON field を抽出するにはどうしますか？

- A) `json.fieldname`
- B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>
- C) `SELECT fieldname FROM logs`
- D) `logs.fieldname`

<details>
<summary>回答を表示</summary>

**回答: B) <code v-pre>{app="myapp"} | json | line_format "{{.fieldname}}"</code>**

**解説:**
`| json` parser は、log lines から JSON fields を labels に抽出します。その後、Go template syntax を使って `| line_format` で出力を整形したり、`| status_code >= 500` のように抽出した fields でフィルタリングしたりできます。

</details>

### 9. Grafana で logs と traces の関連付けを可能にするものは何ですか？

- A) IDs の手動コピーアンドペースト
- B) log fields に trace_id を含め、Loki datasource で derived fields を設定すること
- C) 同じ dashboard を使用すること
- D) 別の plugin をインストールすること

<details>
<summary>回答を表示</summary>

**回答: B) log fields に trace_id を含め、Loki datasource で derived fields を設定すること**

**解説:**
Applications は logs に Trace IDs を出力する必要があります。Grafana では、trace_id field を認識して Tempo にリンクするように Loki の derived fields を設定します。これにより、log lines から関連する trace へ直接移動できるクリック可能なリンクが作成されます。

</details>

### 10. distributed tracing における span attributes の目的は何ですか？

- A) trace visualization の見た目を整えるため
- B) contextual metadata（user ID、request parameters）を spans に付与するため
- C) trace data を暗号化するため
- D) trace storage を圧縮するため

<details>
<summary>回答を表示</summary>

**回答: B) contextual metadata（user ID、request parameters）を spans に付与するため**

**解説:**
Span attributes は、`http.method`、`http.status_code`、`user.id`、`db.statement` など、spans に context を追加する key-value pairs です。これにより、business context で traces をフィルタリングでき、どのリクエストに問題があるかを特定しやすくなります。

</details>
