# メトリクス概要クイズ

> **最終更新**: September 12, 2026

1. リセットされる可能性がある累積カウントを表すタイプはどれですか？

   - A) Gauge
   - B) Counter
   - C) 事前計算された p99
   - D) スクレイプのタイムスタンプ

<details>
<summary>回答を表示</summary>

**回答: B**

Counter は非負の増分を累積します。計測対象の状態が再作成された場合、リセットが発生することがあります。rate() は観測されたリセットを処理しますが、観測されなかった増分を復元することはできません。

</details>

2. 5 つのメソッド、20 のルート、10 のステータスは何を意味しますか？

   - A) すべての Deployment に正確に 1,000 個の保存済み series が存在する
   - B) すべての組み合わせが可能な場合、アプリケーションラベルの組み合わせは最大 1,000 個
   - C) 1 日あたり正確に 1,000 個のサンプル
   - D) リソース使用量に影響しない

<details>
<summary>回答を表示</summary>

**回答: B**

この積は上限です。実際の組み合わせ、target/replica ラベル、histogram bucket、および履歴上の変動によって、実際の series/ストレージ使用量が決まります。

</details>

3. 適切な Pushgateway の使用方法はどれですか？

   - A) すべての短命な Pod に 1 つの HOSTNAME grouping key を使用し、自動期限切れに依存する
   - B) 安定したグループ化、成功タイムスタンプ、明示的な削除ポリシーを備えた、適切なサービスレベルのバッチに使用する
   - C) gateway up=1 を、すべてのバッチが成功した証拠として扱う
   - D) バッチが失敗した場合でも成功タイムスタンプを push する

<details>
<summary>回答を表示</summary>

**回答: B**

Pushgateway はすべての短命な job に対するデフォルトではなく、group に自動 TTL はありません。スクレイプの正常性は、バッチの鮮度とは別です。honor_labels を使用したスクレイプでは、push された job identity が保持されます。

</details>

4. Histogram と Summary に関する正しい記述はどれですか？

   - A) Summary の quantile は常に正確である
   - B) instance の p99 値を平均すると fleet の p99 が得られる
   - C) 互換性のある classic histogram bucket は結合できる。Summary の sum/count は平均のために結合できる
   - D) Summary データを集約できることは一切ない

<details>
<summary>回答を表示</summary>

**回答: C**

Classic bucket は計装された producer によってカウントされ、Prometheus はクエリ時に quantile を計算します。Summary の quantile にはアルゴリズムおよび window に依存する誤差があり、fleet の quantile に集約することはできません。一方、非負の duration の sum/count rate からは fleet の平均を得られます。

</details>

5. 新しい Prometheus アプリケーションメトリクスで推奨されない規則はどれですか？

   - A) 説明的な prefix を使用する
   - B) _seconds や _bytes などの unit suffix を使用する
   - C) 一般的な base-unit 規則よりも camelCase と millisecond 単位を優先する
   - D) 累積 Counter を識別するために _total を使用する

<details>
<summary>回答を表示</summary>

**回答: C**

説明的なアンダースコア区切りの名前と base unit を優先します。_total は Counter のマーカーであり、物理単位ではありません。node_memory_MemAvailable_bytes など、既存の exporter API は公開済みの表記を維持します。

</details>

6. Prometheus の retention に関する正しい記述はどれですか？

   - A) 30 日を超えて保持することは決してできない
   - B) 明示的な時間/サイズの retention 設定がない場合、デフォルトは 15 日である。より長い retention には適切な設定と容量が必要である
   - C) ローカルデータを圧縮しない
   - D) Mimir なしでは独立した collection replica は不可能である

<details>
<summary>回答を表示</summary>

**回答: B**

デフォルトの retention は上限ではありません。ローカル TSDB はレプリケートされた分散ストアではありません。collection redundancy、query deduplication、durability、および recovery はそれぞれ個別の設計判断です。

</details>

7. product/storage に関する誤った主張はどれですか？

   - A) VictoriaMetrics の single-node と cluster の Deployment では運用要件が異なる
   - B) 従来の CloudWatch メトリクスの resolution は時間の経過とともに粗くなる
   - C) Mimir の object storage は無制限のスケールを保証し、すべてのローカルストレージ要件を不要にする
   - D) Datadog メトリクスは query rollup を使用するため、retention はすべてのグラフで元の resolution を保証しない

<details>
<summary>回答を表示</summary>

**回答: C**

Object storage は Mimir のアーキテクチャの一部であり、無制限の容量を保証するものではありません。ingest/local resource、query limit、replication、および運用容量は依然として重要です。バックアップ先や edition 固有の機能を、product の主要ストアと混同しないでください。

</details>

8. メトリクスの cardinality を制御できないアプローチはどれですか？

   - A) 正規化されたルートテンプレートを使用する
   - B) user/session ID を通常の label として使用しない
   - C) 詳細を失っても許容できる場合は status code をグループ化する
   - D) すべての request に新しい request_id label value を割り当てる

<details>
<summary>回答を表示</summary>

**回答: D**

値がハッシュ化されている場合も含め、異なる label value は異なる series を作成します。必要に応じて、request 固有のコンテキストは適切に制御された logs/traces に含めるべきです。cardinality と機密データの露出は、どちらもレビューが必要です。

</details>

9. 正しく対応付けられている Kubernetes メトリクスの役割はどれですか？

   - A) node-exporter — Kubernetes API object の status
   - B) kube-state-metrics — 計測された container CPU usage
   - C) cAdvisor/kubelet metrics — container resource measurements
   - D) metrics-server — 長期的な Prometheus TSDB

<details>
<summary>回答を表示</summary>

**回答: C**

node-exporter は host OS metrics を報告します。kube-state-metrics は API object state を公開し、metrics-server は Resource Metrics API を提供します。Prometheus/vmalert/Mimir rules は alert を評価し、Alertmanager はそれらをルーティングします。vmagent は collector/forwarder であり、クエリ可能な TSDB ではありません。

</details>

10. コスト比較をレビュー可能にするものは何ですか？

   - A) team size のみに基づく product ranking
   - B) sample interval や feature の前提なしの node count
   - C) 計測された series/sample volume、retention/resolution、HA/query requirements、および選択した feature の現在の pricing
   - D) metric name/value の長さは決して重要ではないと仮定する

<details>
<summary>回答を表示</summary>

**回答: C**

15 秒間隔で 30 日間にわたり実際に export された 100 万 series は、delivery filtering/deduplication 前に 1,728 億サンプルを意味します。infrastructure、index/WAL、replica、query work、custom-metric allowance、および operator effort によりコストは変化します。これは workload の計算であり、provider quote ではありません。

</details>

[ガイドに戻る](../../../observability/metrics/README.md)
