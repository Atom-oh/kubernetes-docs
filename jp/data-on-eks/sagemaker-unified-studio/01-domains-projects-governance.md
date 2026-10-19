# パート 4: ドメイン、プロジェクト、メンバーシップのガバナンス

> ドキュメント確認日: 2026-09-12。Qwen のプロビジョニング結果は過去の記録であり、現在のアカウント状態は再確認していません。

記録されている 3 回目の Qwen プロビジョニング試行では、プロジェクトが作成された後、呼び出し元のメンバーシップを理由に読み取り／削除が拒否されています。トレーニングは開始されませんでした。
この記録をすべてのドメインの現在の状態や、あらゆる認可エラーに一般化しないでください。

## 1. オブジェクトと ID を区別する

| オブジェクト／ロール | 意味 |
| --- | --- |
| Unified domain / domain unit | ガバナンスの境界と組織階層 |
| Project profile / blueprint | ツール／環境のプロビジョニングと、利用可能なアカウント／リージョン |
| Project | コラボレーション、ツール、共有リソース |
| User/group profile | SSO ID または登録済み IAM ロールを表すサービス上の情報 |
| Membership designation | PROJECT_OWNER や PROJECT_CONTRIBUTOR などのプロジェクトレベルのロール |
| Project execution role | プロジェクトが AWS のデータ／コンピューティングにアクセスするための ID |
| Catalog asset | 説明、スキーマ、場所など、ガバナンス対象となるメタデータ |

まず、IAM ベースと Identity Center ベースのどちらの構成およびログイン方法かを確認してください。メンバーのロールと実行ロールは、ARN が同じ場合でも目的が異なります。IAM ベースのプロジェクトメンバーは、プロジェクト実行ロールを通じてデータ／コンピューティングにアクセスします。所有者の指定だけでは、ユーザーごとのデータ権限が自動的に分離されるわけではありません。利用する場合は、ID ベースの認可／Trusted Identity Propagation を別途確認してください。

AWS のユーザー管理ドキュメントでは、登録済み IAM ロールのグループプロファイルと、そのロールを通じてログインするユーザーのセッションユーザープロファイルを区別しています。メンバーシップにはロールのグループプロファイルを使用できます。`CreateGroupProfile` の `rolePrincipalARN` は**プロファイルを登録するものであり、IAM ロール自体は作成しません**。
プロジェクトの実行ロールが自動的に扱われる方法は、自動化の呼び出し元の認可と必ずしも同じではありません。

## 2. プロファイル名だけではツールの準備状況を判断できない

All capabilities には、ブループリントのテンプレートが用意されています。プロファイルはプロジェクト作成時にブループリントをプロビジョニングすることも、後からオンデマンドで利用できるようにすることもできます。必要なサービス、アカウント、リージョン、ネットワーク、プロファイルの利用権限を確認してください。

名前が最初に一致したものを無条件に選ぶのではなく、意図したプロファイル ID／構成を選択してください。Qwen の実験には、組織の承認と実際の依存関係を満たすことを条件に、より小規模な機能セットが適する場合があります。このワークフローと、Unified Studio のプロジェクトを使わない通常の SageMaker/EKS トレーニング経路を区別してください。

## 3. IAM、メンバーシップ、データ認可

IAM アクションが許可されていても、プロジェクト所有権が付与されるわけではありません。プロジェクトを所有していても、IAM、SCP、リソースポリシー、データ権限による制限は回避できません。通常のメンバー／コントリビューターに削除権限が自動的に付与されるわけではありません。削除経路で必要となるプロジェクト所有者または管理者の権限を確認してください。

現行の CreateProject API は `membershipAssignments` を受け付けます。
これは**リクエスト構造の例**です。認可されたアクセスで解決した実際のドメイン／プロファイル／グループ ID に置き換えてください。

```json
{
  "domainIdentifier": "dzd-1111111111111111",
  "name": "docs-governance-example",
  "projectProfileId": "c1111111111111",
  "membershipAssignments": [
    {
      "member": {
        "groupIdentifier": "11111111-1111-1111-1111-111111111111"
      },
      "designation": "PROJECT_OWNER"
    }
  ]
}
```


`member` はタグ付きユニオンです。`groupIdentifier` と `userIdentifier` のどちらか**一方だけ**を設定してください。同じリクエストにメンバーシップを含めることで、後続リクエストを別途送るまでの空白を減らせますが、プロジェクト／環境のすべてのプロビジョニングがトランザクションとしてロールバックされる保証はありません。プロジェクトとメンバーシップの状態を読み戻してください。タイムアウトした場合は、プロジェクト名で作成を繰り返すのではなく、元のリクエストとインベントリを照合してください。

## 4. プロジェクトとツールの準備手順

1. 対象のアカウント／リージョン、ドメインの種類、プロファイル ID を確認する。
2. 呼び出し元のログイン／プロファイル、必要な所有者／管理者権限、実行ロールの権限を区別する。
3. 作成時とオンデマンドのブループリントを特定し、承認済みの依存関係を準備する。
4. CreateProject とメンバーシップの結果を保存し、読み戻して確認する。
5. `projectStatus` と `environmentDeploymentDetails` を分けて確認する。
6. 次のコンピューティング工程に進む前に、必要な環境／ツールが準備できていることと、実際に読み書きできることを検証する。

`projectStatus=ACTIVE` であっても、すべての環境／ツールが準備できているとは限りません。`overallDeploymentStatus` には `PENDING_DEPLOYMENT`、`IN_PROGRESS`、`SUCCESSFUL`、`FAILED_VALIDATION`、`FAILED_DEPLOYMENT` があります。意図的にプロビジョニングしていないオンデマンドツールを失敗として扱わないでください。**このワークロードが実際に必要とするもの**を確認してください。

## 5. タグ付けの失敗とカタログでの情報開示

現行 API は `resourceTags` に対応しています。過去の実験で拒否されたことは、そのドメイン／リクエスト固有の観察結果であり、Unified Studio にタグ機能がない証明ではありません。実際のポリシー、値、エラーを確認してください。補償処理の対象は、この実行で作成され、クリーンアップが認可されているリソースに限定してください。プレフィックスが一致するだけでは、共有バケットやロールを削除する理由になりません。

公開ドキュメントには、必要な実験件数、合成データのスキーマ／レコード数、生成ツールのバージョン／seed／hash、所有権／保持の方針を記載できます。実際の PII、認証情報、署名付き URL、再識別の対応表は公開成果物に含めないでください。

アクセス制御された**内部カタログ**では、データの発見やアクセスのために、ストレージの場所やリソース識別子が必要になる場合があります。公開ドキュメントで情報を伏せることは、内部カタログで場所メタデータを一律に禁止することを意味しません。メタデータの公開、サブスクリプションの承認、実際のデータ認可はそれぞれ別の手順です。

## 6. 削除と不存在の検証

1. 保持すべきデータと、この実行が所有するリソース／依存関係を特定する。
2. 認可された所有者／管理者のコンテキストでプロジェクトの作業を停止し、クリーンアップ範囲を確定する。
3. プロジェクト、環境、管理対象リソースそれぞれのライフサイクルに従って削除する。
4. `DELETING` / `DELETE_FAILED` の状態やエラーを調べ、完了を確認する。
5. 関連するアカウント／リージョンのインベントリを使い、残存する外部 Apps、S3、IAM、コンピューティングを照合する。

`GetProject` の AccessDenied は、対象が存在しないことの証拠ではありません。
空の `ListProjects` 応答も、可視性、フィルター、ページネーションに制約があれば不十分です。ドメイン／ID を確認し、すべてのページを調べ、認可された get/list の証拠を外部リソースのインベントリと組み合わせてください。プロジェクトを削除しても、すべての外部サービスリソースが削除される保証はありません。所有権と保持要件を個別に確認してください。

## 7. Qwen 検証の過去時点での範囲

保存された検証 JSON の日付は **2026-09-01** です。
3 回の試行すべてで `trainingStarted=false`、3 回目の後にプロジェクトが 1 つ残っていたこと、実験用 App/S3/IAM リソースがクリーンアップされたことが記録されています。9 月 2 日のドキュメントには、その時点で ACTIVE を再確認したと記載されています。このレビューでは、これらの記録を現行の公開 API ドキュメントと照合しています。現在のアカウントにプロジェクトが存在するか、削除済みかを確認するものではありません。

再開する前に、現在のインベントリと所有権を確認してください。
このレビューでは、プロジェクト、メンバーシップ、IAM、GPU リソースの作成／削除を行っていません。リクエスト例は**ローカル AWS CLI の出力スケルトン入力検証**に合格しました。`member` の両方の ID 種別を設定するケースは ParameterValidation で拒否されました。これは実際の認可や環境プロビジョニングの成功を示すものではありません。

## 参考資料

- [IAM ベースのドメイン](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/iam-based-domains.html)
- [プロジェクトメンバーと実行ロール](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/projects-iam-based-domains.html)
- [ユーザープロファイルとグループプロファイル](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/user-management.html)
- [CreateProject リクエストとデプロイ状態](https://docs.aws.amazon.com/boto3/latest/reference/services/datazone/client/create_project.html)
- [All capabilities プロファイルとオンデマンドプロビジョニング](https://docs.aws.amazon.com/help-panel/sagemaker-unified-studio/latest/console/project-profiles-all-capabilities-hp.html)
- [プロジェクトの削除と外部リソース](https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/delete-project.html)
- [記録された Qwen プロビジョニング検証](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)

[前へ: SageMaker AI / MLflow](../../ai-ml/sagemaker-ai/03-sagemaker-mlflow-execution.md)

[次へ: 検証結果](../../ai-ml/sagemaker-ai/04-validation-results.md)

[クイズ](../../quizzes/data-on-eks/sagemaker-unified-studio/01-domains-projects-governance-quiz.md)
