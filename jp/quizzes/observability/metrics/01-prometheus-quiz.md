# Prometheus クイズ

> **最終更新**: September 12, 2026

1. Prometheus の通常のメトリクス収集経路は何ですか？

   - A) アプリケーションがすべてのサンプルを直接 push する必要がある
   - B) Prometheus が設定されたターゲットを HTTP 経由で scrape する
   - C) ストリーミングイベントログのみ
   - D) 定期的な CSV インポートのみ

<details>
<summary>回答を表示</summary>

**回答: B**

通常の経路は pull/scrape です。Remote write とオプションのバッチ統合により、ほかの配信経路が追加されます。up は scrape の成功を示すものであり、アプリケーションの完全な可用性を示すものではありません。

</details>

2. Counter の5分間における1秒あたりの平均 rate を得る式はどれですか？

   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>回答を表示</summary>

**回答: B**

rate() は range vector を使用し、観測された reset/extrapolation を処理します。increase() は総増加量を推定するもので、1秒あたりの rate ではありません。集約の前に rate を適用し、欠落したすべての増分を復元するものと解釈しないでください。

</details>

3. 正常に動作する ServiceMonitor が記述しなければならないものは何ですか？

   - A) Grafana ダッシュボード
   - B) Prometheus コンテナイメージのみ
   - C) Prometheus の設定と selector/port 名が一致する、選択対象の Service と scrape endpoint
   - D) 完全なアプリケーション Deployment

<details>
<summary>回答を表示</summary>

**回答: C**

Prometheus はまず monitor の namespace と label を選択し、その monitor が対象の Service を選択します。endpoint port は Service の port 名です。RBAC、TLS/ネットワークアクセス、計装されたアプリケーションも追加要件です。

</details>

4. histogram_quantile() は classic histogram に対して何を返しますか？

   - A) 正確な Summary percentile
   - B) bucket ベースの quantile 推定値
   - C) bucket の解像度に依存しない正確な percentile
   - D) Counter の request rate

<details>
<summary>回答を表示</summary>

**回答: B**

互換性のある classic bucket を、le を保持したまま集約します。結果は bucket 内で補間されます。Summary quantile にもアルゴリズムや window に依存する誤差があり、fleet 全体の percentile に平均化することはできません。

</details>

5. kube-prometheus-stack パッケージの構成要素ではないものはどれですか？

   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>回答を表示</summary>

**回答: C**

この chart は、有効化された values に応じて Prometheus/Alertmanager、Operator、Grafana、exporter をパッケージ化します。VictoriaMetrics は別の deployment です。任意の image version を混在させるのではなく、確認した chart cohort を pin してください。

</details>

6. remote write は何に使用されますか？

   - A) Alertmanager 通知の送信
   - B) 設定された外部 receiver への非同期サンプル配信
   - C) 無制限の障害時バッファリングの保証
   - D) Grafana ダッシュボードの同期

<details>
<summary>回答を表示</summary>

**回答: B**

receiver には AMP、VictoriaMetrics、Mimir があります。それぞれに独自の endpoint、identity、quota、HA 契約があります。WAL バッファリングには上限があり、ローカル Prometheus の retention 自体も設定可能で、普遍的に30日間に制限されるものではありません。

</details>

7. alert rule の for duration は何を制御しますか？

   - A) メトリクスの retention
   - B) 同じ alert condition/label set が firing 前に pending 状態のままである期間
   - C) Alertmanager の repeat interval
   - D) Prometheus replica の数

<details>
<summary>回答を表示</summary>

**回答: B**

その alert identity に対して、condition は evaluation を通じて満たされ続ける必要があります。データの欠落や label の変更により、pending 状態が中断されることがあります。通知の grouping と timing は別の Alertmanager 設定です。

</details>

8. predict_linear() はどのように解釈すべきですか？

   - A) 保証されたディスク障害の期限
   - B) 将来に外挿された、fitting 済みの Gauge trend
   - C) 季節性を考慮した三重指数予測
   - D) すべての capacity measurement の代替

<details>
<summary>回答を表示</summary>

**回答: B**

観測された linear trend を予測します。workload の変更、cleanup、sparse data、非線形な動作により無効になる可能性があります。以前の holt_winters 名は、Prometheus 3 では明示的に experimental な double-exponential smoothing function に置き換えられています。これは seasonal model ではありません。

</details>

9. AlertmanagerConfig の groupBy は何をしますか？

   - A) すべての namespace からの alert を自動的に認可する
   - B) 選択した label で通知をグループ化する
   - C) Prometheus の for duration を定義する
   - D) 一致するすべての sibling route を実行する

<details>
<summary>回答を表示</summary>

**回答: B**

groupBy は native configuration では group_by になります。通常、route は continue が設定されていない限り、最初に一致した sibling で停止します。inhibition では、無関係な service/node warning を抑制しないように、意味のある resource-identity の equal label が必要です。

</details>

10. TSDB WAL は何を提供しますか？

   - A) query result cache
   - B) block persistence 前の crash recovery を支える順次記録
   - C) volume を失っても存続する backup
   - D) 無制限の remote-write 配信キュー

<details>
<summary>回答を表示</summary>

**回答: B**

WAL replay は durability の仕組みであり、破損、volume 障害、または長時間の remote outage が発生しても損失がゼロであるという保証ではありません。retention と WAL/head/compaction のディスク要件は別個です。検証済みの backup と recovery procedure を維持してください。

</details>

[ガイドに戻る](../../../observability/metrics/01-prometheus.md)
