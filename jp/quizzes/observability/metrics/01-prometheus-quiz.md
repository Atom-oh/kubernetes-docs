# Prometheus クイズ

Prometheus に関する理解度を確認するクイズです。

---

1. Prometheus のデータ収集方式は何ですか？
   - A) Push ベース - アプリケーションがメトリクスを送信する
   - B) Pull ベース - Prometheus がターゲットからメトリクスをスクレイプする
   - C) Streaming ベース - リアルタイムのデータストリーム
   - D) Batch ベース - 定期的なファイル転送

<details>
<summary>回答を表示</summary>

**回答: B) Pull ベース - Prometheus がターゲットからメトリクスをスクレイプする**

**解説:**
Prometheus は Pull ベースのメトリクス収集システムであり、HTTP を介してターゲットの /metrics エンドポイントから定期的にメトリクスをスクレイプします。このアプローチの利点は、収集ターゲットと間隔を一元管理できること、およびターゲットの可用性を自動検出できることです。

</details>

---

2. 過去 5 分間の HTTP リクエストレートを計算する正しい PromQL クエリはどれですか？
   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>回答を表示</summary>

**回答: B) `rate(http_requests_total[5m])`**

**解説:**
`rate()` 関数は、Counter メトリクスの 1 秒あたりの平均増加率を計算します。Range vector では角括弧 `[]` で時間を指定します。`increase()` は合計増加量を返し、`avg()` は平均値を計算する集計関数です。`rate(http_requests_total[5m])` は 5 分間の 1 秒あたりのリクエスト数を計算します。

</details>

---

3. Prometheus Operator における ServiceMonitor の役割は何ですか？
   - A) Prometheus サーバーをデプロイする
   - B) アラートルールを定義する
   - C) 監視する Service とスクレイプ設定を定義する
   - D) Grafana ダッシュボードを作成する

<details>
<summary>回答を表示</summary>

**回答: C) 監視する Service とスクレイプ設定を定義する**

**解説:**
ServiceMonitor は Prometheus Operator の CRD であり、Kubernetes Service を監視するためのスクレイプ設定を宣言的に定義します。ターゲット Service のセレクター、エンドポイント、スクレイプ間隔、ラベルの再ラベル付けなどを設定できます。PrometheusRule はアラートルールを処理し、Prometheus CRD はサーバーのデプロイを処理します。

</details>

---

4. histogram_quantile 関数について正しい記述はどれですか？
   - A) Summary メトリクスでのみ使用できる
   - B) Histogram バケットから分位数を計算する
   - C) 正確な分位数の値を返す
   - D) Counter メトリクスの変化率を計算する

<details>
<summary>回答を表示</summary>

**回答: B) Histogram バケットから分位数を計算する**

**解説:**
`histogram_quantile()` は Histogram バケットデータから分位数を計算します。たとえば、`histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` は p95 レイテンシーを計算します。バケット境界に基づく近似値を返すため、正確な分位数には Summary を使用します。

</details>

---

5. kube-prometheus-stack Helm chart に含まれていないコンポーネントはどれですか？
   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>回答を表示</summary>

**回答: C) VictoriaMetrics**

**解説:**
kube-prometheus-stack は、Prometheus Operator、Prometheus、Alertmanager、Grafana、kube-state-metrics、node-exporter などを含む Helm chart です。VictoriaMetrics は別プロジェクトであり、victoria-metrics-k8s-stack chart を使用してインストールします。

</details>

---

6. Prometheus における Remote Write の主な目的は何ですか？
   - A) ローカルストレージのパフォーマンスを改善する
   - B) 長期メトリクスストレージにデータを送信する
   - C) リアルタイムアラートを送信する
   - D) Grafana ダッシュボードを同期する

<details>
<summary>回答を表示</summary>

**回答: B) 長期メトリクスストレージにデータを送信する**

**解説:**
Remote Write は、Prometheus が収集したメトリクスを外部システム（VictoriaMetrics、Mimir、AMP、Cortex など）に送信する機能です。Prometheus のローカルストレージには保持期間とスケーラビリティの制約があるため、Remote Write を使用して長期保持向けの専用ストレージにデータを送信します。

</details>

---

7. PrometheusRule CRD における `for` フィールドの役割は何ですか？
   - A) ルール評価間隔を設定する
   - B) アラートが発火するまでの条件継続時間を設定する
   - C) アラートの再送間隔を設定する
   - D) メトリクスの保持期間を設定する

<details>
<summary>回答を表示</summary>

**回答: B) アラートが発火するまでの条件継続時間を設定する**

**解説:**
PrometheusRule の `for` フィールドは、アラート条件が満たされてから実際にアラートが発火するまでの待機時間を設定します。たとえば、`for: 5m` は、アラートが発火する前に条件が 5 分間継続する必要があることを意味します。これにより、一時的なスパイクによる不要なアラートを防止します。

</details>

---

8. PromQL の `predict_linear` 関数の目的は何ですか？
   - A) 現在値の絶対値を計算する
   - B) 線形回帰に基づいて将来の値を予測する
   - C) 時系列データを並べ替える
   - D) ラベル値を変換する

<details>
<summary>回答を表示</summary>

**回答: B) 線形回帰に基づいて将来の値を予測する**

**解説:**
`predict_linear(v range-vector, t scalar)` は、線形回帰を使用して将来の値を予測します。たとえば、`predict_linear(node_filesystem_avail_bytes[6h], 24*60*60) < 0` は、現在の傾向で 24 時間以内にディスク容量が枯渇するかどうかを予測します。キャパシティプランニングとプロアクティブなアラートに役立ちます。

</details>

---

9. Alertmanager の `groupBy` 設定の役割は何ですか？
   - A) 特定のグループにのみアラートを送信する
   - B) 指定したラベルでアラートをグループ化する
   - C) アラートの優先度を設定する
   - D) 重複するアラートを削除する

<details>
<summary>回答を表示</summary>

**回答: B) 指定したラベルでアラートをグループ化する**

**解説:**
`groupBy` は、指定したラベルでアラートをグループ化し、単一の通知として送信します。たとえば、`groupBy: ['alertname', 'namespace']` は、同じ alertname と namespace を持つアラートをグループ化します。これにより、アラートストームを防ぎ、関連するアラートをまとめて確認できます。

</details>

---

10. Prometheus TSDB における WAL（Write-Ahead Log）の役割は何ですか？
    - A) クエリキャッシュ
    - B) データ損失を防ぐための先行書き込み記録
    - C) アラート履歴の保存
    - D) ダッシュボード設定の保存

<details>
<summary>回答を表示</summary>

**回答: B) データ損失を防ぐための先行書き込み記録**

**解説:**
WAL（Write-Ahead Log）は、メモリからディスクブロックに完全に書き込まれる前にデータを順次記録するログです。Prometheus が異常終了した場合でも、WAL を通じてデータを復元し、データ損失を防止できます。これはデータベースで一般的に使用される耐久性メカニズムです。

</details>
