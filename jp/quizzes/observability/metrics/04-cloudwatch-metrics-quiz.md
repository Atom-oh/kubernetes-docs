# CloudWatch メトリクスのクイズ

2026年9月13日版のガイドに基づいてレビューしました。

1. マネージド CloudWatch バックエンドを使うと、チームのどの責任がなくなりますか？

   - A) すべての収集作業と IAM 設定
   - B) AWS バックエンドの運用だけ。収集、ID、保持、対応の責任は引き続き必要
   - C) すべてのネットワーク前提条件
   - D) クエリ料金とログ料金のすべて

<details>
<summary>解答を表示</summary>

**解答: B**

従来型、拡張型、OTel による収集では、メトリクスの命名や課金モデルがそれぞれ異なります。ストレージがマネージドでも、運用作業がゼロになるわけではありません。

</details>

2. EKS へのインストールについて、正しい説明はどれですか？

   - A) `update-cluster-logging` を実行すると Container Insights がインストールされる
   - B) どのプラットフォームでも同じホスト DaemonSet を実行する
   - C) 互換性のあるアドオンまたは管理対象の Helm インストールを選び、プラットフォームと ID の前提条件を検証する
   - D) Helm 6.6.0 は必ず EKS アドオンのバージョンである

<details>
<summary>解答を表示</summary>

**解答: C**

コントロールプレーンのログ記録は別の機能です。Fargate では例にあるホスト DaemonSet は実行されません。Auto Mode や複数のコンピュート方式が混在する環境では互換性を確認してください。Pod Identity／IRSA も実際の設定が必要です。

</details>

3. `SEARCH` の結果から上位 10 件をダッシュボードに表示するには、何を使いますか？

   - A) `SEARCH` だけで常に結果が 10 件に制限される
   - B) `SLICE(SORT(SEARCH(...), AVG, DESC), 0, 10)`
   - C) `PERCENTILE(SEARCH(...), 10)`
   - D) `SEARCH` 配列に対する通常のアラーム

<details>
<summary>解答を表示</summary>

**解答: B**

`SEARCH` は一致する時系列を返します。並べ替えと切り取りを明示してください。順位は評価対象の期間に基づきます。`SEARCH` をアラームで直接監視することはできません。

</details>

4. パーセンタイルと比率について、正しい説明はどれですか？

   - A) `PERCENTILE(METRICS(),95)` はリクエスト全体の p95 を返す
   - B) トラフィックがない期間はすべて、エラー 0 の正常な結果である
   - C) `AVG(METRICS()) PERIOD(300)` は移動平均である
   - D) サポートされる p95 統計値を使い、カウント比率ではトラフィック 0 を処理し、テレメトリ欠落を確認する

<details>
<summary>解答を表示</summary>

**解答: D**

ガイドでは ALB カウントに Sum を使い、`IF(m2>0,100*m1/m2)` で比率を計算します。CloudWatch の算術式では欠損値が 0 として扱われ、ゼロ除算の結果は除外されます。サービスごとの p95 値から全体の p95 を再構成することはできません。

</details>

5. 実際のテレメトリで ADOT／EMF のメトリクス宣言に必要なものはどれですか？

   - A) dimension のラベルと値。検出／relabeling またはアプリケーションから提供する
   - B) exporter 設定内の dimension 名だけ
   - C) すべてのラベルに secret access key を含める
   - D) すべての Pod をスクレイプするレプリカを各ノードで実行する

<details>
<summary>解答を表示</summary>

**解答: A**

`awsemf` は、従来型メトリクスとして抽出するためのログイベントを送信します。この例では ClusterName／Namespace／Service を作成し、gauge を使います。新しい直接 OTLP 経路は別の選択肢です。

</details>

6. このガイドと互換性がない、または安全でないコスト削減策はどれですか？

   - A) 取り込み量とクエリ使用量を計測する
   - B) 所有する 1 つのロググループに承認済みの保持期間を設定する
   - C) EMF／Container Insights のログを Infrequent Access に移し、保持期間に上限のないすべてのロググループを短縮する
   - D) 重複スクレイプや不要なラベルを確認する

<details>
<summary>解答を表示</summary>

**解答: C**

Infrequent Access は EMF や Container Insights のログ取り込みをサポートしません。保持期間を短くすると、既存の履歴が期限切れになる場合があります。高解像度の設定はリクエスト料金やアラーム料金を増やすことがありますが、メトリクスストレージ料金が一律 10 倍になることを意味するわけではありません。

</details>

7. `PutMetricData` ヘルパーについて、正しい説明はどれですか？

   - A) IAM を自動的にプロビジョニングする
   - B) 呼び出し元から渡されたクライアントと UTC timestamp を使い、エラーを呼び出し元に返す
   - C) リトライにより業務上のカウントが厳密に 1 回だけ記録される
   - D) CloudWatch がすべての集約用 dimension セットを自動作成する

<details>
<summary>解答を表示</summary>

**解答: B**

カスタムメトリクスは、dimension の組み合わせ全体によって識別されます。`PutMetricData` に冪等性トークンはありません。結果が不明な状態でリトライすると、サンプルが重複することがあります。この例では期間ごとのカウントを報告し、Sum を使います。

</details>

8. 従来型メトリクスの dimension と OTel の label はどう異なりますか？

   - A) どちらも常に上限がない
   - B) 150 label の上限が `PutMetricData` の上限に置き換わる
   - C) 従来型メトリクスは 30 dimension、文書化された OTel モデルは最大 150 label をサポートする
   - D) label は payload の料金や情報開示に影響しない

<details>
<summary>解答を表示</summary>

**解答: C**

これらは別々の取り込みモデルです。label を増やすと payload とメタデータの露出が増えます。dimension 名だけでは cardinality を測れません。

</details>

9. メトリクスの解釈として正しいのはどれですか？

   - A) `node_network_total_bytes` は bytes/second、`namespace_number_of_running_pods` は Pod 数を表す
   - B) `cluster_cpu_utilization` は標準公開メトリクスである
   - C) 実行中のコンテナ数は常に実行中の Pod 数と等しい
   - D) 予約済みキャパシティのメトリクスはすべて拡張型でのみ利用できる

<details>
<summary>解答を表示</summary>

**解答: A**

実際のメトリクス一覧と dimension の組み合わせを確認してください。Pod の CPU／メモリ使用率では、ノードの limits を分母に使うことがあります。拡張オブザーバビリティはメトリクスや dimension を追加し、独自の課金モデルがあります。

</details>

10. 異常検知アラームや再起動アラームで確認すべきことは何ですか？

   - A) アラームを作成すれば実際のテレメトリがあることを証明できる
   - B) 再起動の合計値は常に期間ごとの増分を表す
   - C) 観測対象の異常検知系列から `ReturnData` を必ず削除する
   - D) 履歴、正確なメトリクス ID、合計値か差分かの意味、欠損データ、通知の配信を確認する

<details>
<summary>解答を表示</summary>

**解答: D**

`ANOMALY_DETECTION_BAND` は、学習された期待範囲の上限と下限を返します。文書化された異常検知の式は、観測系列とバンドの両方を返す場合があります。PodName／Namespace／ClusterName ごとの再起動合計値が、5 分間に新たに 5 回再起動したことを自動的に意味するわけではありません。

</details>

---

[ガイドに戻る](../../../observability/metrics/04-cloudwatch-metrics.md)
