# Spark Operator クイズ

ベースライン: Kubeflow 2.5.2、Apache Operator 1.0.0 / chart 1.8.0。

## 1. 2 つの Spark Operator はどのような関係ですか？

- A) 同じ chart の名称変更版
- B) Kubeflow のサポート終了後に置き換わったもの
- C) API とライフサイクルモデルが異なる別々のプロジェクト
- D) apiVersion だけを変更すれば完全な互換性がある

<details>
<summary>解答を表示</summary>

**解答: C**

Kubeflow は sparkoperator.k8s.io/v1beta2 を使い、この章では Apache の spark.apache.org/v1 を扱います。フィールド、状態、再試行の動作についても移行時に確認が必要です。

</details>

## 2. 確認済みの Apache Operator 1.0.0 に対応する chart はどれですか？

- A) 必ず 1.0.0
- B) Kubeflow と同じ 2.5.2
- C) Spark と同じ 4.2.0
- D) 1.8.0

<details>
<summary>解答を表示</summary>

**解答: D**

chart のバージョンとアプリケーションのバージョンは別です。リリース／chart のメタデータと、レンダリングされたリソースを確認してください。

</details>

## 3. Comet または Gluten を使うには何が必要ですか？

- A) 互換性のあるプラグイン、イメージ、クラスパス、構成
- B) Apache Operator のインストールだけ
- C) すべてのアーキテクチャと Spark バージョンでの同一の動作
- D) Kubeflow ではそのようなワークロードを実行できない

<details>
<summary>解答を表示</summary>

**解答: A**

公式の例には追加の前提条件があります。Operator を選ぶだけでは、高速化やプラグインとの互換性は保証されません。

</details>

## 4. 通常の spark-submit に関する正しい説明はどれですか？

- A) 常に fire-and-forget である
- B) 完了を待ってログを確認できる。Operator による CR の調整は別の機能である
- C) Executor Pod を作成できない
- D) 構成を Git でバージョン管理できない

<details>
<summary>解答を表示</summary>

**解答: B**

Native 提出では、状態、ログ、UI にアクセスできます。Operator は CR のライフサイクル管理、スケジュール実行コントローラー、アプリケーションの再試行を追加します。

</details>

## 5. Kubeflow 2.5.2 の webhook.enable の既定値は何ですか？

- A) false
- B) Spark のバージョンに応じて自動的に変わる
- C) true
- D) デフォルトのインストール namespace でのみ true

<details>
<summary>解答を表示</summary>

**解答: C**

例では既定値が明示されています。無効にする場合は、そのアドミッション経路に依存する機能を確認してください。

</details>

## 6. 確認済みの各 chart では、アドミッション機能にどのような違いがありますか？

- A) どちらも同じ Pod mutator をインストールする
- B) Webhook が Pod をノードに配置する
- C) Webhook が Spark タスクを割り当てる
- D) Apache は Kubeflow と同等の Pod 変更用 webhook をインストールしない

<details>
<summary>解答を表示</summary>

**解答: D**

図は Kubeflow を説明しています。Kubernetes のスケジューリングと Spark driver によるタスク割り当ては、それぞれ別の役割です。

</details>

## 7. spark-jobs 内のジョブには何が必要ですか？

- A) 監視対象の namespace、ジョブの namespace、RBAC を一致させる
- B) すべてのジョブをインストール先の namespace にだけ提出する
- C) ClusterRole があれば監視範囲を考慮する必要はない
- D) default を監視すれば自動的にすべての namespace が含まれる

<details>
<summary>解答を表示</summary>

**解答: A**

インストール先の namespace とワークロードの namespace は異なる場合があります。既定の監視範囲に新しいジョブの namespace が自動的に含まれるわけではありません。

</details>

## 8. Kubeflow のカスタムボリュームはどこに指定しますか？

- A) `spec.driver.volumes` のみ
- B) `spec.volumes` に定義し、`driver/executor.volumeMounts` でマウントする
- C) `spec.executor.volumes` のみ
- D) `status.volumes`

<details>
<summary>解答を表示</summary>

**解答: B**

確認済みの CRD には `driver.volumes` や `executor.volumes` フィールドはありません。共有ボリューム定義を `spec.volumes` に記述し、必要な場所でマウントしてください。

</details>

## 9. spark-local-dir- ボリュームの特別な点は何ですか？

- A) 物理 NVMe ディスクを自動作成する
- B) すべてのボリュームを S3 に変換する
- C) ネイティブな Spark のローカルボリューム構成に変換される
- D) webhook の経路だけで実装しなければならない

<details>
<summary>解答を表示</summary>

**解答: C**

汎用のボリューム mutator はこれらのローカルディレクトリボリュームを処理せず、提出時の構成が処理します。`emptyDir` を使うだけでは、物理ストレージが選択されるわけではありません。

</details>

## 10. Kubeflow 2.5.2 で有効な serviceAccount フィールドはどれですか？

- A) `driver.serviceAccount` のみ
- B) `executor.serviceAccount` のみ
- C) どちらにも AWS IAM ARN を指定する必要がある
- D) `driver.serviceAccount` と `executor.serviceAccount` の両方

<details>
<summary>解答を表示</summary>

**解答: D**

両方のフィールドで Kubernetes サービスアカウントを指定します。API の RBAC と AWS データ権限は別途構成します。

</details>

## 11. ScheduledSparkApplication を毎日 02:00 UTC に実行するにはどうしますか？

- A) `schedule: "0 2 * * *"` と `timeZone: UTC` を指定する
- B) 常にコントローラーのローカル時刻に依存する
- C) `timeZone` はサポートされていない
- D) Executor Pod の TZ だけを設定する

<details>
<summary>解答を表示</summary>

**解答: A**

バージョン 2.5.2 は `timeZone` をサポートし、既定値は Local です。スケジュールでタイムゾーンを明示すれば、コントローラーの環境に依存せずに済みます。

</details>

## 12. `concurrencyPolicy: Forbid` で防止できるのは何ですか？

- A) すべてのシステムにまたがる重複書き込み
- B) スケジュール対象リソースの前回実行と次回実行の重複
- C) すべてのアプリケーション再試行
- D) すべての手動提出

<details>
<summary>解答を表示</summary>

**解答: B**

別のスケジューラー、手動実行、再試行によって、重複した副作用が発生することはあります。冪等またはトランザクション対応の出力を設計してください。

</details>

## 13. `suspend: true` の動作は何ですか？

- A) 実行中の子ジョブを必ず終了させる
- B) すでに書き込まれたデータをロールバックする
- C) 今後のスケジュール起動を停止する
- D) Operator のデプロイメントを削除する

<details>
<summary>解答を表示</summary>

**解答: C**

実行中のジョブは別途調査または終了してください。停止はデータのロールバックでもバックアップでもありません。

</details>

## 14. `sparkVersion` だけを 4.2.0 に変更すると、何が保証されますか？

- A) コントローラーのランタイムが自動的にアップグレードされる
- B) すべての Spark プラグインとの互換性
- C) Kubernetes が自動的にアップグレードされる
- D) コントローラーの spark-submit がアップグレードされる保証はない

<details>
<summary>解答を表示</summary>

**解答: D**

Kubeflow のラボでは、コントローラーの提出ランタイムとして 4.0.4 を使用しています。ほかの submitter／ワークロードの組み合わせは、別途テストしてください。

</details>

## 15. Operator はどの Pod の状態を監視しますか？

- A) Driver と Executor の両方
- B) Driver のみ
- C) Executor のみ
- D) Pod の状態は監視しない

<details>
<summary>解答を表示</summary>

**解答: A**

コントローラーは Executor の状態も更新し、クリーンアップを実行します。Spark driver は Executor を要求し、Spark タスクを割り当てます。

</details>

## 16. OnFailure の再試行を使う場合に重要なことは何ですか？

- A) exactly-once の書き込みが自動的に保証される
- B) アプリケーションの再実行によって出力への副作用が重複することがある
- C) 常に同じコンテナだけが再起動される
- D) 失敗した外部トランザクションがすべてロールバックされる

<details>
<summary>解答を表示</summary>

**解答: B**

提出／アプリケーションの試行とコンテナの再起動は別のものです。再試行回数や間隔だけでなく、データの意味的な正しさも検証してください。

</details>

## 17. IRSA と EKS Pod Identity はどのように異なりますか？

- A) どちらも同じアノテーションだけが必要
- B) Kubernetes Role が S3 アクセス権を付与する
- C) IRSA は OIDC／ロールアノテーションを使用し、Pod Identity は関連付けと Agent を使用する
- D) S3 URI を指定すれば認証が完了する

<details>
<summary>解答を表示</summary>

**解答: C**

AWS 権限、信頼関係または関連付け、互換性のある認証情報プロバイダーを構成してください。実際の Pod で有効な ID とアクセス権を確認します。

</details>

## 18. chart の既定の Prometheus エンドポイント（ポート 8080）が公開するのは何ですか？

- A) すべての Spark JVM から自動収集した JMX メトリクス
- B) Spark History Server のすべてのログ
- C) S3 データ検証の結果
- D) Operator のメトリクス

<details>
<summary>解答を表示</summary>

**解答: D**

ワークロードの JMX には、アプリケーション独自の exporter JAR、構成、スクレイプ設定が必要です。

</details>

## 19. Helm アップグレード時に CRD をどう扱うべきですか？

- A) CRD の移行と明示的な `hook.upgradeCrd` オプトインを確認する
- B) 通常の helm upgrade で常に CRD が置き換わる
- C) 既存の CRD を必ず先に削除する
- D) CRD はアプリケーションリソースに影響しない

<details>
<summary>解答を表示</summary>

**解答: A**

通常のアップグレードでは、`crds/` 内の CRD が自動的に置き換わることはありません。CRD を削除すると、そのカスタムリソースにも影響するため、通常のアップグレード手順ではありません。

</details>

## 20. Helm のレンダリングと CRD の検査が成功した場合、何が確認できますか？

- A) 稼働中の webhook 接続が証明される
- B) リソースの形状と構成経路が確認できる。稼働中のワークロードの成功は別途確認が必要
- C) S3 アクセスとデータの正しさが証明される
- D) すべての Spark バージョンとの互換性が証明される

<details>
<summary>解答を表示</summary>

**解答: B**

実際の Pod、状態、出力、再試行の動作、権限も確認してください。`COMPLETED` だけでは、外部データの正しさは証明されません。

</details>

[本文 / Guide](../../../data-on-eks/spark/02-spark-operator.md)
