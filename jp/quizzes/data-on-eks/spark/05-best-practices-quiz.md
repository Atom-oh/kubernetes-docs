# パート 5: ベストプラクティスとセキュリティのクイズ

Spark 4.2.0 / Hadoop 3.5.0 / AWS SDK v2 2.35.4。

## 1. レビュー対象の Spark 4.2 ディストリビューションに一致する Hadoop/S3A のバージョンはどれですか？

<details>
<summary>回答を表示</summary>

Hadoop client と hadoop-aws はどちらも 3.5.0、AWS SDK v2 bundle は 2.35.4 と、解決済みのランタイム依存関係を使います。別のイメージまたは EMR を使う場合は、同梱されるバージョンを再確認してください。

</details>

## 2. この SDK v2 の組み合わせに適した IRSA provider はどれですか？

<details>
<summary>回答を表示</summary>

software.amazon.awssdk.auth.credentials.WebIdentityTokenFileCredentialsProvider です。この組み合わせでは、以前の com.amazonaws.auth.WebIdentityTokenCredentialsProvider が自動的に対応付けられるわけではありません。

</details>

## 3. Pod Identity を使うと何が変わりますか？

<details>
<summary>回答を表示</summary>

ContainerCredentialsProvider、サービスアカウントの関連付け、pods.eks.amazonaws.com への信頼、Agent/ノードの権限を使用します。IRSA アノテーションと OIDC の設定では、この経路を代替できません。

</details>

## 4. デフォルトの S3A チェーンは自動的に IRSA を使いますか？

<details>
<summary>回答を表示</summary>

レビュー対象の Hadoop 3.5.0 のチェーンには、コンテナ/インスタンスのラッパーが含まれますが、web-identity provider は含まれません。必要な provider を指定し、有効な ID とプレフィックスへのアクセスを確認してください。

</details>

## 5. driver、executor、History Server に別々のサービスアカウントを使うのはなぜですか？

<details>
<summary>回答を表示</summary>

driver に必要な Kubernetes 管理権限を、各プロセスが持つ S3 データ権限から分離するためです。History Server は cleaner を無効にすれば、読み取り専用ロールで起動できます。

</details>

## 6. namespace 内の Role によって、driver の権限を自分自身の executor のみに制限できますか？

<details>
<summary>回答を表示</summary>

いいえ。Pod ラベルによる所有条件がなければ、namespace 全体のリソース/verb に権限が付与されます。Pod 作成、他のサービスアカウント、ホストアクセスを制限するには、admission と信頼境界を組み合わせてください。

</details>

## 7. ClusterRole は常にクラスター全体の権限を意味しますか？

<details>
<summary>回答を表示</summary>

いいえ。ClusterRole を参照する RoleBinding を使うと、namespace のリソース権限をその RoleBinding の namespace に限定できます。ルールと binding の種類/スコープの両方を確認してください。

</details>

## 8. spark.authenticate=true を設定すると、Spark UI にログイン認証が追加されますか？

<details>
<summary>回答を表示</summary>

いいえ。これは内部接続を認証します。Kubernetes が生成したアプリケーション Secret は executor の環境へ伝播する場合があるため、Pod 読み取り権限が重要です。UI の認証、認可、TLS はそれぞれ別の機能です。

</details>

## 9. ロールラベルだけを使う NetworkPolicy の問題は何ですか？

<details>
<summary>回答を表示</summary>

同じ namespace 内の別ジョブの executor も一致します。この例では、driver/executor のラベルとポリシーで一意の run ID を共有します。ラベルは認証の仕組みではないため、Pod 作成者が偽装できることも考慮してください。

</details>

## 10. この NetworkPolicy を適用すれば、ほかの経路もすべて遮断されますか？

<details>
<summary>回答を表示</summary>

ポリシーは追加で適用され、CNI による enforcement が必要です。この例が制限するのは ingress だけです。egress、ノード/hostNetwork の動作、ほかの allow ポリシー、DNS/API/AWS エンドポイント、追加プラグインを別々に確認してください。

</details>

## 11. 固定ポートと spark.port.maxRetries=0 を組み合わせるのはなぜですか？

<details>
<summary>回答を表示</summary>

ポートが競合したとき、ポリシーの範囲外に無言で別のポートへ移動するのではなく、起動を失敗させるためです。追加のエンドポイントには別途ポートとセキュリティを設定してください。

</details>

## 12. PrometheusServlet と executor の集約エンドポイントは同じですか？

<details>
<summary>回答を表示</summary>

いいえ。/metrics/prometheus/ は driver の Dropwizard registry を配信します。/metrics/executors/prometheus/ は driver が収集した executor の集約値を配信します。executor ごとに Spark UI が作られるわけではありません。実際の series、ラベル、単位を比較してください。

</details>

## 13. JMX Java agent と Operator chart のメトリクスについて、正しい説明はどれですか？

<details>
<summary>回答を表示</summary>

agent は別プロセスではなく JVM 内で実行されます。Operator chart のデフォルトのメトリクスは Operator 自体を示します。chart がすべての Spark JVM に agent を自動インストールするわけではありません。

</details>

## 14. PodMonitor を作成するだけでメトリクス収集は十分ですか？

<details>
<summary>回答を表示</summary>

Prometheus のラベル/namespace セレクター、discovery RBAC、Pod のポート/パス、NetworkPolicy が一致している必要があります。UP 状態のターゲットと実際の series を確認してください。短時間のジョブはスクレイプの間に終了する場合があります。

</details>

## 15. driver Pod オブジェクトを保持すれば、ジョブ終了後もその UI を保持できますか？

<details>
<summary>回答を表示</summary>

ライブ UI は JVM の終了とともに停止します。History Server は別途保存されたイベントログから再構築するもので、stdout/stderr やチェックポイントから再構築するわけではありません。

</details>

## 16. History Server の設定ファイルをマウントするだけで読み込まれますか？

<details>
<summary>回答を表示</summary>

いいえ。この例では spark-class org.apache.spark.deploy.history.HistoryServer --properties-file を明示的に使い、フォアグラウンドで実行します。パス、ログディレクトリ、S3 の ID を確認してください。

</details>

## 17. History Server は過去のすべてのジョブのあらゆる詳細を復元しますか？

<details>
<summary>回答を表示</summary>

イベントログが実際に保持され、読み取り可能である必要があります。イベントの欠落、破損、未フラッシュ、削除、圧縮は再構築を制限します。イベントログはデータ復旧用のチェックポイントでも出力のバックアップでもありません。

</details>

## 18. 本番環境で使える選択肢は Operator、cluster mode、IRSA だけですか？

<details>
<summary>回答を表示</summary>

いいえ。要件に合わせて、検証済みの直接送信、Operator、EMR、適切な client/cluster mode、IRSA/Pod Identity を選択してください。実環境で権限、データの正しさ、復旧、ネットワーキング、リソース、コストをテストします。

</details>

[ガイド](../../../data-on-eks/spark/05-best-practices.md)

[README](../../../data-on-eks/spark/README.md)
