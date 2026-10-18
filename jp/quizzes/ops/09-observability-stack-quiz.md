# Observability stack クイズ

> **関連ドキュメント**: [Observability stack](../../ops/09-observability-stack.md)

## 1. 新しい Loki のデプロイを検討する際、判断の指針となる説明はどれですか？

- A) SimpleScalable は、今後もすべての新規デプロイで恒久的な既定モードである
- B) SimpleScalable は非推奨で、4.0 で削除予定のため、代替手段を評価する
- C) Monolithic は object storage を利用できない
- D) replica を 3 つにすれば AZ の分離が自動的に保証される

<details>
<summary>回答を表示</summary>

**回答: B**

read、write、backend の分割は SSD のアーキテクチャを表します。新しい設計では、そのライフサイクルに加えて、Monolithic mode と Distributed mode の容量および運用上の制約も評価してください。

</details>

## 2. Tempo 3 の Distributed mode と Monolithic mode は、どのように異なりますか？

- A) どちらも従来の ingester を保持する
- B) Monolithic mode は常に Kafka を必要とする
- C) Distributed mode は Kafka を使い、Monolithic mode は Kafka なしで実行できる
- D) Monolithic chart の replica を増やせば、サポートされた Distributed HA が実現する

<details>
<summary>回答を表示</summary>

**回答: C**

version 3 では、分散 ingester／compactor アーキテクチャの代わりに block-builder／live-store と backend-scheduler／worker を使います。異なるデプロイモードを混在させないでください。

</details>

## 3. tail sampling には、どのような制約がありますか？

- A) すべての error trace を必ず保持する
- B) `decision_wait` の間に受信した span に基づいて判断し、head sampling で破棄済みのデータは復元できない
- C) Service をランダムに振り分ければ、trace は常に同じ sampler に届く
- D) `num_traces` は 1 秒あたりの trace 数を指定する

<details>
<summary>回答を表示</summary>

**回答: B**

遅れて届く span、buffer の上限、再起動、transport の障害を考慮してください。複数の sampler を使う場合は、trace ID に基づいて routing する必要があります。

</details>

## 4. batch processor の `send_batch_size` は何を制御しますか？

- A) batch の最大サイズ
- B) trace の最大継続時間
- C) 送信を開始する item 数のしきい値
- D) 永続ストレージの容量

<details>
<summary>回答を表示</summary>

**回答: C**

batch サイズの上限は `send_batch_max_size` で指定します。memory limiter と sampling／drop 処理の後に batch processor を配置してください。

</details>

## 5. すべての Alloy DaemonSet Pod がクラスター内のすべての log target を収集すると、何が起こりますか？

- A) 完全な HA と重複排除が自動的に実現する
- B) 重複収集が起きることがあるため、target を分割するか source clustering を構成する
- C) Kubernetes API が collector を必ず 1 つだけ許可する
- D) hostPath が必須なので起動できない

<details>
<summary>回答を表示</summary>

**回答: B**

Kubernetes logs API を使う source と file tailing は異なります。単一の Deployment と `Recreate` を使う例は重複を減らしますが、HA や中断のない収集を実現するものではありません。

</details>

## 6. Loki retention を有効にするには何が必要ですか？

- A) `retention_period` だけ
- B) 24 時間の TSDB index、compactor retention の有効化、`delete_request_store`、retention 期間
- C) bucket 内のすべての object を同じ期間で期限切れにする
- D) Grafana dashboard の time range

<details>
<summary>回答を表示</summary>

**回答: B**

削除は遅延を伴い、非同期で行われます。compactor の state と marker は再起動後も保持される必要があります。bucket 全体に lifecycle expiration を設定すると、index など必要な object が損なわれることがあります。

</details>

## 7. AMP の HA group と replica を識別する label はどれですか？

- A) `namespace` と `pod`
- B) `cluster` と `__replica__`
- C) `service` と `trace_id`
- D) `region` のみ

<details>
<summary>回答を表示</summary>

**回答: B**

同じ scrape data の replica は `cluster` を共有し、異なる `__replica__` の値を使います。独立した scrape coverage を 1 つの HA group にまとめると、データが失われることがあります。

</details>

## 8. AMP の retention について、正しい説明はどれですか？

- A) 150 日が変更できない上限である
- B) workspace ごとに設定でき、最大 1,095 日である
- C) 常に無期限である
- D) 期間を延長すれば、すでに削除された metric が復元される

<details>
<summary>回答を表示</summary>

**回答: B**

要件、コスト、サービスの制限を評価してから retention を設定してください。期限切れになったデータは後から復元されません。

</details>

## 9. Grafana で Loki の log から Tempo の trace に移動するには何が必要ですか？

- A) 両方をインストールすれば自動的にリンクされる
- B) 正しい trace ID 抽出、明示的な datasource UID、アクセス可能な trace data
- C) trace ID を通常の Prometheus label として追加する
- D) HTTP/2 だけを有効にする

<details>
<summary>回答を表示</summary>

**回答: B**

`derivedFields` と `tracesToLogsV2` の対応関係、time range、tenant、権限を確認してください。exemplar には、instrumentation、OpenMetrics、ストレージの構成も必要です。

</details>

## 10. chart の render が成功した後も、何を確認する必要がありますか？

- A) 不要。未知の value もすべて適用されている
- B) 実際の PVC、Service、identity、backend の設定、write／query 経路
- C) YAML の indentation だけ
- D) すべての image を `latest` に置き換える

<details>
<summary>回答を表示</summary>

**回答: B**

chart の value によっては、警告なしに無視されるものがあります。PVC の `accessModes` と Service の port を確認し、parser による構成検証と実環境への接続性を区別してください。

</details>
