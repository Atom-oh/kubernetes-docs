# Cilium Service Mesh 可観測性クイズ

Cilium 1.20.3／Hubble CLI 1.20.2 に基づいています。検証済みコマンド、メトリクスの定義、制約については[可観測性ガイド](../../../service-mesh/cilium-service-mesh/04-observability.md)を参照してください。

### 1. Hubble の主要コンポーネントではないものはどれですか？

- **A.** Hubble Observer
- **B.** Hubble Relay
- **C.** Hubble Router
- **D.** Hubble UI

<details>
<summary>解答を表示</summary>

**解答: C. Hubble Router**

関連する Hubble コンポーネントは Observer、Relay、UI、CLI です。Observer とメトリクス処理は Cilium に組み込まれ、Relay は接続されたサーバーから情報を集約します。Hubble Router はこのアーキテクチャのコンポーネント名ではありません。

</details>

### 2. Hubble CLI で HTTP トラフィックだけを絞り込んで観察するコマンドはどれですか？

- **A.** `hubble observe --type http`
- **B.** `hubble observe --protocol http`
- **C.** `hubble observe --filter http`
- **D.** `hubble observe --layer http`

<details>
<summary>解答を表示</summary>

**解答: B. `hubble observe --protocol http`**

このコマンドは、すでに観察できている HTTP トラフィックを絞り込みます。L7 検査を有効にしたり、任意の TLS 通信を復号したりするものではありません。観察対象を得るには、対応する L7 ポリシー／プロキシ経路が構成され、トラフィックがすでに観測されている必要があります。

</details>

### 3. Prometheus で Hubble メトリクスを収集するため、values.yaml で有効にする設定はどれですか？

- **A.** `hubble.prometheus.enabled: true`
- **B.** `hubble.metrics.enabled`
- **C.** `hubble.export.prometheus: true`
- **D.** `prometheus.hubble: true`

<details>
<summary>解答を表示</summary>

**解答: B. `hubble.metrics.enabled`**

`hubble.metrics.enabled` では、`dns` や `httpV2` などのハンドラーを選択します。Prometheus で収集するには、正常なサービス検出／スクレイプも必要です。ServiceMonitor を使う場合は Operator の CRD／コントローラーと selector の一致も確認してください。ServiceMonitor が作成されただけでは、対象がスクレイプされている証明にはなりません。

</details>

### 4. モニタリングの 4 つの Golden Signals に含まれないものはどれですか？

- **A.** レイテンシー
- **B.** トラフィック
- **C.** 可用性
- **D.** 飽和度

<details>
<summary>解答を表示</summary>

**解答: C. 可用性**

4 つはレイテンシー、トラフィック、エラー、飽和度です。可用性を測るには明示的な SLI が必要です。HTTP 5xx の一部の観察ストリームだけから、可用性全体を推定することはできません。

</details>

### 5. 原因をさらに調査するため、ドロップされたフローを最初に選ぶコマンドはどれですか？

- **A.** `hubble observe --denied`
- **B.** `hubble observe --verdict DROPPED`
- **C.** `hubble observe --blocked`
- **D.** `hubble observe --policy-denied`

<details>
<summary>解答を表示</summary>

**解答: B. `hubble observe --verdict DROPPED`**

`DROPPED` には複数の原因が含まれます。ポリシーによる拒否として報告されたドロップを調べるには、`--drop-reason-desc POLICY_DENIED` を追加します。L7 やアプリケーションの失敗は別途調査してください。`FORWARDED` はデータプレーンで転送されたことを示す観察結果であり、ビジネス処理の成功を証明するものではありません。

</details>

### 6. PromQL で HTTP の P99 レイテンシーを測る関数はどれですか？

- **A.** `avg()`
- **B.** `histogram_quantile()`
- **C.** `rate()`
- **D.** `sum()`

<details>
<summary>解答を表示</summary>

**解答: B. `histogram_quantile()`**

`histogram_quantile` はヒストグラムから推定値を計算します。ワークロード全体の値を求めるには、互換性のある bucket の rate を、`le` と選択したクラスター／namespace／ワークロードのラベルを残して合計し、その後で分位点を求めます。インスタンスごとのパーセンタイルを平均しても同じ結果にはなりません。

</details>

### 7. Hubble UI の主な機能ではないものはどれですか？

- **A.** Service Map
- **B.** Flow Timeline
- **C.** Auto Scaling
- **D.** Namespace Filter

<details>
<summary>解答を表示</summary>

**解答: C. Auto Scaling**

UI は観察できた関係やフローの詳細をフィルター付きで表示します。ワークロードを自動的にスケーリングする機能はありません。トラフィックがない経路、未対応の経路、メタデータ欠落などによって、マップに表示されない情報が生じる場合があります。

</details>

### 8. httpV2 で観察された HTTP 5xx の割合は、どのように計算すべきですか？

- **A.** error と request の累積カウンターを rate を使わずに割る
- **B.** 対象範囲をそろえ、5xx レスポンス率を総レスポンス率で割り、系列欠落とゼロを適切に扱う
- **C.** メトリクス系列の数を数える
- **D.** 自動提供される `hubble_http_error_rate` gauge を読む

<details>
<summary>解答を表示</summary>

**解答: B. 対象範囲をそろえ、5xx レスポンス率を総レスポンス率で割り、系列欠落とゼロを適切に扱う**

httpV2 では `hubble_http_requests_total` に status が含まれ、レスポンスイベントから更新されます。分子と分母で集計ラベルと観察範囲を一致させてください。総数が存在する場合に限り、存在しない 5xx 分子を補完します。観察データ自体が欠けている場合はデータなしとし、割合の計算から総数がゼロのケースを除外してください。

</details>

### 9. Hubble で特定の Service 宛てのトラフィックだけを観察するオプションはどれですか？

- **A.** `--destination-service`
- **B.** `--to-service`
- **C.** `--target-service`
- **D.** `--svc`

<details>
<summary>解答を表示</summary>

**解答: B. `--to-service`**

Service のフィルターでは、namespace を含む名前のプレフィックスと、Service／ClusterIP 由来のメタデータを使います。`--from-service` では、その Service の背後にいる Pod が呼び出し元であるトラフィックを一般には選べません。呼び出し元を絞るには workload／Pod／label のフィルターを使ってください。namespace を省略すると `default` が使われます。

</details>

### 10. 計測対象の BPF map にかかる pressure を報告するメトリクスはどれですか？

- **A.** `cilium_ct_usage`
- **B.** `cilium_bpf_map_pressure`
- **C.** `cilium_connections_total`
- **D.** `cilium_datapath_conntrack_active` / `cilium_datapath_conntrack_max`

<details>
<summary>解答を表示</summary>

**解答: B. `cilium_bpf_map_pressure`**

`cilium_bpf_map_pressure` は、計測対象の BPF map の pressure を報告します。一部の map には報告しきい値がありますが、すべての CT map が対象である証明にはなりません。文書化されている CT GC-entry メトリクスはガベージコレクション時のスナップショットであり、以前の架空の active／max メトリクスの組み合わせではありません。

</details>

### 11. Hubble の出力を JSON 形式で受け取るオプションはどれですか？

- **A.** `--format json`
- **B.** `-o json`
- **C.** `--json`
- **D.** `--output-type json`

<details>
<summary>解答を表示</summary>

**解答: B. `-o json`**

`json` は `jsonpb` の別名です。Protobuf JSON では、`latency_ns` などの 64 ビット値は文字列として出力されます。`jq` で数値比較する前に数値へ変換してください。ほかに `dict`、`compact`、`table` 形式もサポートされています。

</details>

### 12. OpenTelemetry Collector で Hubble のフローログを収集する、サポート対象の方法はどれですか？

- **A.** chart で `hubble.export.opentelemetry` を有効にする
- **B.** Hubble のファイルエクスポートと filelog receiver を使い、対応するログ exporter に送る
- **C.** すべてのフローを自動的に分散トレースへ変換する
- **D.** 削除済みの jaeger exporter をフローログ収集に使う

<details>
<summary>解答を表示</summary>

**解答: B. Hubble のファイルエクスポートと filelog receiver を使い、対応するログ exporter に送る**

Cilium 1.20.3 ではフローログのファイルエクスポートが文書化されています。filelog receiver でファイルを収集し、OTLP／HTTP で Loki に送るなど、対応する exporter へログを送信できます。メトリクスとアプリケーショントレースにはそれぞれ別の収集経路があります。以前の Hubble `opentelemetry` values や、削除済みの Collector jaeger／loki exporter は代替手段ではありません。

</details>
