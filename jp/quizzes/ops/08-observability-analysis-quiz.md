# Observability Analysis クイズ

> **関連ドキュメント**: [可観測性の分析](../../ops/08-observability-analysis.md)

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
サービスは、有効な受信trace contextを引き継ぐか、新しいtraceを作成します。非同期処理では、span linkで接続した新しいtraceを開始する場合もあります。参加するspanが同じTrace IDを共有することで、同じリクエストを処理した各サービスのlogs、spans、metricsを関連付けられます。

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
Exemplars は、選択されたmetricの観測値にcontextual label（多くの場合Trace ID）を付与します。Grafanaでhistogramやcounterを表示するとき、設定済みのexemplar linkから関連する保持済みtraceを開けます。すべての観測値がtrace化されるわけではなく、厳密にP99となったリクエストを特定する保証もありません。

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
`histogram_quantile()` はhistogramのbucket countからquantileを計算します。最初の引数（0.95）がpercentileで、`_bucket` metricのrateを使います。結果はbucket境界からの推定値です。インスタンスをまとめる場合は、`le`と対象のservice/cluster labelを保持してrateを集約してください。トラフィックがない場合やrateが0の場合は別途扱う必要があります。

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
`| json` parserは、log lineからJSON fieldを抽出します。出力を整形したり、抽出したfieldで絞り込んだりできます。特にmetric集約の前や`unwrap`の後は、`__error__` filterを使ってparser/conversion errorを確認してください。

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
- B) routeやoperationなど、範囲を限定したcontextual metadataを付与するため
- C) trace data を暗号化するため
- D) trace storage を圧縮するため

<details>
<summary>回答を表示</summary>

**回答: B) routeやoperationなど、範囲を限定したcontextual metadataを付与するため**

**解説:**
Span attributesは、routeやoperationなど、範囲を限定したcontextを追加します。クエリは実際のsemantic-convention schemaに合わせてください。カーディナリティに上限を設け、認証情報、リクエスト本文全体、機密性の高いデータベース文を無差別に記録しないでください。

</details>
