# Amazon EMR on EKS クイズ

2026年10月16日にレビューしたガイドに基づきます。

## 1. 仮想クラスターとは何ですか？

<details>
<summary>回答を表示</summary>

EMR に EKS の名前空間を論理的に登録したものです。コンピューティング容量は作成しませんが、初回のサービスリンクロールと CAM のアクセスエントリ/ポリシーが設定される場合があります。

</details>

## 2. StartJobRun と EMR Spark Operator による送信にはどのような違いがありますか？

<details>
<summary>回答を表示</summary>

StartJobRun は仮想クラスターを対象とする AWS API です。別途インストールした Operator は SparkApplication CR を受け取ります。これは StartJobRun に組み込まれた委譲オプションではありません。

</details>

## 3. Operator が送信した CR には、自動的に EMR のジョブ ID が付与されますか？

<details>
<summary>回答を表示</summary>

そうとは限りません。Operator 経由の経路では CR の状態、ログ、再試行を確認し、EMR ジョブ API のライフサイクルとは別に扱ってください。

</details>

## 4. EMR Spark Operator はいつからサポートされ、どのようにインストールしますか？

<details>
<summary>回答を表示</summary>

EMR 6.10.0 以降です。ドキュメントに記載された EMR chart と互換性のある実行環境をインストールし、kubectl apply で送信します。パート 2 の現行上流 chart と同じ配布物だと考えないでください。

</details>

## 5. emr-spark-8.0.0 に含まれる Apache Spark のバージョンは何ですか？

<details>
<summary>回答を表示</summary>

4.0.2-amzn-0 です。2026年5月のこのリリースで Spark 4.x が一般提供されました。8.0.0 は EMR 実行環境のリリース名です。

</details>

## 6. -latest と日付付きのサフィックスにはどのような違いがありますか？

<details>
<summary>回答を表示</summary>

-latest はリリースのセキュリティ更新に追従するため、イメージのバイト列を同一に固定しません。日付付きサフィックスはリリースの再現に役立ちますが、その後の更新確認は引き続き必要です。

</details>

## 7. CreateVirtualCluster の応答値のうち、後続のジョブに使うものはどれですか？

<details>
<summary>回答を表示</summary>

id フィールドです。StartJobRun の virtualClusterId に指定し、登録された名前空間と RUNNING 状態を確認してください。

</details>

## 8. 実行ロールのデータ権限と呼び出し元の権限は同じですか？

<details>
<summary>回答を表示</summary>

いいえ。実行ロールはワークロードに S3、KMS、ログなどへのアクセスを許可します。呼び出し元には API 権限と許可されたロールの使用権限が必要です。ExecutionRoleArn の条件と適用される PassRole 権限を確認してください。

</details>

## 9. update-role-trust-policy は何をしますか？

<details>
<summary>回答を表示</summary>

IRSA の場合、実行ロールの信頼ポリシーを更新し、クラスターの OIDC プロバイダー、名前空間、EMR が管理するサービスアカウント ID を信頼させます。S3 権限や呼び出し元権限は自動的に付与しません。

</details>

## 10. StartJobRun で Pod Identity を使えますか？

<details>
<summary>回答を表示</summary>

はい。EMR 7.3.0 以降で利用できます。Agent、ノードの EKS Auth 権限、pods.eks.amazonaws.com への信頼、サービスアカウントの関連付けが必要です。IRSA アノテーションで代用できません。

</details>

## 11. create-role-associations で準備される関連付けは何ですか？

<details>
<summary>回答を表示</summary>

実行ロールと、EMR ジョブ送信用、ドライバー用、エグゼキューター用のサービスアカウントとの間に 3 つの関連付けを作成します。現行の CLI ヘルパーを使い、名前空間やロールを廃止する際には未使用の関連付けを別途削除してください。

</details>

## 12. maxConcurrentJobRuns=2 は namespace の CPU 上限を設定しますか？

<details>
<summary>回答を表示</summary>

いいえ。ジョブ数を制限します。maxInQueueJobRuns はキューに入れられるジョブ数を制限します。CPU/メモリのクォータやジョブごとのエグゼキューター上限は別に設定します。

</details>

## 13. StartJobRun が正常に応答すれば、ジョブは完了していますか？

<details>
<summary>回答を表示</summary>

いいえ。受け付けられたジョブ ID を使って、最終状態とログを確認してください。スモークテストの例では COMPLETED と SMOKE_OK rows=10 total=45 の両方を確認します。

</details>

## 14. clientToken を再利用すれば、データ出力が厳密に 1 回だけになりますか？

<details>
<summary>回答を表示</summary>

API リクエストは重複排除されますが、アプリケーションの再試行や外部への副作用は対象外です。新しい実行を意図する場合は新しいトークンを使ってください。

</details>

## 15. EMR の Pod テンプレートやイメージはカスタマイズできますか？

<details>
<summary>回答を表示</summary>

はい。サポート対象の Pod テンプレート/カスタムイメージの方法でカスタマイズできます。リリース固有の制約を守り、StartJobRun が管理する名前空間、サービスアカウント、Pod 名を任意に上書きしないでください。

</details>

## 16. CloudWatch と Step Functions の統合は、設定なしで完全に利用できますか？

<details>
<summary>回答を表示</summary>

いいえ。ログ監視と実行ロールの権限に加え、ステートマシンとそのロールを構成してください。サービスメトリクスは Spark JVM のテレメトリ全体を表すものではありません。

</details>

## 17. EMR Studio で対話型ワークロードはどのように実行されますか？

<details>
<summary>回答を表示</summary>

CreateManagedEndpoint エンドポイントが Jupyter Enterprise Gateway を使ってカーネルを管理します。通常の StartJobRun によるバッチ呼び出しとは異なり、プライベートネットワーキング、ALB、ロールの設定が必要です。同じエンドポイントのユーザー/カーネルはロールを共有します。

</details>

## 18. 仮想クラスターの削除だけではクリーンアップが完了しないのはなぜですか？

<details>
<summary>回答を表示</summary>

先に対象のジョブ/エンドポイントを確認してクリーンアップしてください。EKS、名前空間、S3、ログ、IAM ロール、Pod Identity の関連付けはそれぞれ別のライフサイクルです。削除状態と権限エラーも調査してください。

</details>

[ガイド](../../../data-on-eks/spark/03-emr-on-eks.md)
