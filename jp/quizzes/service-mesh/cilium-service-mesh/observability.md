# Cilium Service Mesh Observability クイズ

このクイズでは、Hubble、metrics 収集、service maps、Golden Signals のモニタリング、および OpenTelemetry 統合に関する理解度を確認します。

## クイズの問題

### 1. Hubble の主要コンポーネントではないものはどれですか？

A. Hubble Observer
B. Hubble Relay
C. Hubble Router
D. Hubble UI

<details>
<summary>解答を表示</summary>

**回答: C. Hubble Router**

**解説:**
Hubble の主要コンポーネントは、Hubble Observer（Cilium Agent に組み込み）、Hubble Relay（クラスター全体のフロー集約）、Hubble UI（可視化ダッシュボード）、および Hubble CLI（コマンドラインインターフェイス）です。Hubble Router は既存のコンポーネントではありません。

</details>

### 2. Hubble CLI で HTTP トラフィックのみをフィルタリングして監視するコマンドはどれですか？

A. hubble observe --type http
B. hubble observe --protocol http
C. hubble observe --filter http
D. hubble observe --layer http

<details>
<summary>解答を表示</summary>

**回答: B. hubble observe --protocol http**

**解説:**
`hubble observe --protocol http` コマンドは、HTTP プロトコルのトラフィックのみをフィルタリングします。他のプロトコル（tcp、dns など）も同じ方法でフィルタリングできます。

</details>

### 3. Prometheus で Hubble metrics を収集するには、values.yaml でどの設定を有効にする必要がありますか？

A. hubble.prometheus.enabled: true
B. hubble.metrics.enabled
C. hubble.export.prometheus: true
D. prometheus.hubble: true

<details>
<summary>解答を表示</summary>

**回答: B. hubble.metrics.enabled**

**解説:**
Hubble metrics を有効にするには、収集する metric の種類（dns、drop、tcp、flow、http など）を hubble.metrics.enabled の下でリストとして指定します。また、serviceMonitor.enabled: true を設定すると、Prometheus Operator による自動スクレイピングが可能になります。

</details>

### 4. モニタリングにおける 4 つの Golden Signals に含まれないものはどれですか？

A. Latency
B. Traffic
C. Availability
D. Saturation

<details>
<summary>解答を表示</summary>

**回答: C. Availability**

**解説:**
Google SRE で定義された 4 つの Golden Signals は、Latency、Traffic、Errors、および Saturation です。Availability は Golden Signals に含まれず、Errors metric を通じて間接的に測定されます。

</details>

### 5. Hubble でポリシーにより拒否されたトラフィックを監視する正しいコマンドはどれですか？

A. hubble observe --denied
B. hubble observe --verdict DROPPED
C. hubble observe --blocked
D. hubble observe --policy-denied

<details>
<summary>解答を表示</summary>

**回答: B. hubble observe --verdict DROPPED**

**解説:**
`--verdict DROPPED` オプションは、network policies により拒否されたトラフィックをフィルタリングします。反対に、`--verdict FORWARDED` は許可されたトラフィックを表示します。

</details>

### 6. PromQL クエリで HTTP P99 latency を測定するために使用する関数はどれですか？

A. avg()
B. histogram_quantile()
C. rate()
D. sum()

<details>
<summary>解答を表示</summary>

**回答: B. histogram_quantile()**

**解説:**
P99 latency のようなパーセンタイル metric には histogram_quantile() 関数を使用します。例: `histogram_quantile(0.99, rate(hubble_http_request_duration_seconds_bucket[5m]))`。ここで、0.99 は 99 パーセンタイルを意味します。

</details>

### 7. Hubble UI が提供する主な機能ではないものはどれですか？

A. Service Map
B. Flow Timeline
C. Auto Scaling
D. Namespace Filter

<details>
<summary>解答を表示</summary>

**回答: C. Auto Scaling**

**解説:**
Hubble UI は、service maps、flow timeline、namespace filter、verdict filter、および個々のフローの L7 details を提供します。Auto scaling は workload 管理機能であり、observability 機能ではありません。

</details>

### 8. Cilium で HTTP error rate を計算する PromQL クエリの正しい形式はどれですか？

A. hubble_http_errors_total / hubble_http_requests_total
B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))
C. count(hubble_http_errors) / count(hubble_http_requests)
D. hubble_http_error_rate

<details>
<summary>解答を表示</summary>

**回答: B. sum(rate(hubble_http_responses_total{status=~"5.."}[5m])) / sum(rate(hubble_http_responses_total[5m]))**

**解説:**
HTTP error rate は、5xx レスポンス数を総レスポンス数で割って計算します。rate() 関数は 1 秒あたりの rate を計算し、status label filter（status=~"5.."）は server errors のみを選択します。

</details>

### 9. Hubble で特定の service 宛てのトラフィックのみを監視するために使用するオプションはどれですか？

A. --destination-service
B. --to-service
C. --target-service
D. --svc

<details>
<summary>解答を表示</summary>

**回答: B. --to-service**

**解説:**
`hubble observe --to-service <service-name>` コマンドは、特定の service 宛てのトラフィックをフィルタリングします。反対に、`--from-service` は特定の service から発信されるトラフィックをフィルタリングします。

</details>

### 10. Cilium で connection tracking table の使用率をモニタリングする metric はどれですか？

A. cilium_ct_usage
B. cilium_datapath_conntrack_active
C. cilium_connections_total
D. cilium_ct_table_size

<details>
<summary>解答を表示</summary>

**回答: B. cilium_datapath_conntrack_active**

**解説:**
cilium_datapath_conntrack_active metric は、現在のアクティブな connection 数を表します。cilium_datapath_conntrack_max と組み合わせて、connection tracking table の使用率を計算できます。

</details>

### 11. Hubble の出力を JSON 形式で取得するために使用するオプションはどれですか？

A. --format json
B. -o json
C. --json
D. --output-type json

<details>
<summary>解答を表示</summary>

**回答: B. -o json**

**解説:**
`hubble observe -o json` コマンドは JSON 形式で出力します。これは、jq などのツールにパイプして追加処理を行う場合に役立ちます。

</details>

### 12. OpenTelemetry Collector を Hubble と統合するときに使用するプロトコルはどれですか？

A. HTTP REST API
B. OTLP (OpenTelemetry Protocol)
C. Prometheus Remote Write
D. StatsD

<details>
<summary>解答を表示</summary>

**回答: B. OTLP (OpenTelemetry Protocol)**

**解説:**
Hubble は OpenTelemetry Protocol（OTLP）を使用して、flow data を OpenTelemetry Collector にエクスポートできます。これにより、Jaeger、Prometheus、Loki などのさまざまなバックエンドにデータをルーティングできます。

</details>
