# SageMaker Unified Studio のガバナンス

> ドキュメント確認日: 2026-09-12。実験結果は、2026-09-01 の記録と、2026年9月2日時点の過去のドキュメントに基づきます。

Amazon SageMaker Unified Studio は、データ/AI チーム向けのコラボレーション、ツール、カタログアセットを管理します。このセクションでは、EKS パイプラインのアセット、ユーザー、実行権限に関するドメインとプロジェクトの境界について説明します。
ここで扱う **Unified Studio/DataZone project** は、SageMaker AI MLOps Project や SageMaker AI Studio domain と同じ API オブジェクトではありません。

## 対象となる境界

| トピック | 確認事項 |
| --- | --- |
| Domain type | IAM ベースと IAM Identity Center ベースのログイン/管理 |
| Project profile / blueprint | 作成時にプロビジョニングされるツールと、オンデマンドで有効化されるツール |
| Member / execution role | ポータル/プロジェクトへのアクセスに使う ID と、AWS リソースの実行 ID |
| Membership / data access | 管理上の指定と、IAM、Lake Formation、カタログデータの権限 |
| Lifecycle | プロジェクトの存在、環境の準備状況、実際のツールアクセス、所有リソースのクリーンアップ |

[Part 4: Domain, project and membership](01-domains-projects-governance.md) では、Qwen 実験で記録された失敗を、これらの境界に照らして説明します。Unified Studio project は、このガイドで選択したガバナンス方式であり、すべての SageMaker Training Job や EKS training workload に必須の技術的依存関係ではありません。

## 過去の証跡と現在の状態を区別する

保存された 2026-09-01 の検証 JSON には、トレーニング開始前に停止したこと、実験用の App/S3/IAM リソースをクリーンアップしたこと、Unified Studio project が1つ残っていたことが記録されています。9月2日のドキュメントには、その時点で ACTIVE であることを再確認した記録があります。
**このドキュメント確認では AWS account に再照会しておらず、現在も project が1つ残っているとは述べていません。**

その実験を再開する前に、権限のあるオペレーターが現在のインベントリ、メンバーシップ、クリーンアップの状態を確認する必要があります。過去の失敗を一般化して、新しい権限の自動付与や共有リソースの削除を行わないでください。

関連ガイド:

- [SageMaker Qwen PII guidebook](../../ai-ml/sagemaker-ai/README.md)
- [Part 3: SageMaker AI and MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)
- [Part 5: Factual validation results](../../ai-ml/sagemaker-ai/04-validation-results.md)

## 参考資料

- [IAM-based domains](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [Project member and execution roles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [User and group profiles](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject request and deployment status](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities profiles and on-demand provisioning](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [Project deletion and external resources](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [Recorded Qwen provisioning validation](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
