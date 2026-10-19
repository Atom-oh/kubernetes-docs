# AWS Controllers for Kubernetes (ACK)

> **最終更新日**: 2026年10月16日

## 概念とアーキテクチャ

ACK は、サービスごとのコントローラーを通じて Kubernetes カスタムリソースを AWS API に接続します。CRD は入力を定義し、コントローラーは望ましい状態と AWS で観測された状態を調整します。CR を作成しただけでは、AWS リソースの準備が完了したとは限りません。status と、サービス側の readiness を確認してください。

ACK は Kubernetes API、RBAC、GitOps ツールを利用しますが、Kubernetes の認可と AWS IAM は別々の仕組みです。通常、ユーザーが作成した CR による操作は、コントローラーに付与された AWS 権限で実行されます。そのため、CR の書き込み権限を与えることは、そのコントローラーを通じて AWS の操作を要求する権限を委譲することになります。

ACK は CloudFormation や Terraform の必須の後継ではありません。実際のリソースは AWS にあり、Kubernetes には CR の spec/status が保存されます。ドリフトへの対処は、サポートされるフィールドとコントローラーのロジックに依存します。同じ AWS リソースを複数のツールやクラスターで調整させず、変更を管理する主体を 1 つにしてください。

![ACK は Kubernetes カスタムリソースを AWS API を通じて調整します](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## バージョンとサポート

| コントローラー | バージョン |
| --- | --- |
| s3 | 1.13.1 |
| iam | 1.10.1 |
| sqs | 1.8.2 |
| sns | 1.11.1 |
| elbv2 | 1.8.2 |
| route53 | 1.7.1 |
| rds | 1.13.3 |

これらのバージョンは公式リリースと OCI チャートで確認しました。対応範囲の全容と Alpha／Beta／GA の段階については、公式のサービス一覧を参照してください。GA であっても、すべての AWS API 機能や運用要件が網羅されているとは限りません。CRD の v1alpha1 という API 文字列は、コントローラーの成熟度とは別のものです。

以前に示されていた Kubernetes 1.16 という最小バージョンは、現在の運用基準ではありません。サポート対象の Kubernetes／EKS バージョン、コントローラーとの互換性、Helm バージョン、CRD のアップグレード手順をまとめて確認してください。

## インストールの準備とオフライン検査

以前の eks-charts s3-chart パスではなく、以下の OCI チャートのパスを使用してください。このコマンドは、クラスターにインストールせずにマニフェストをレンダリングします。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.13.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

実際にインストールまたはアップグレードする前に、infra namespace とコントローラーの ServiceAccount を用意し、IRSA またはサポート対象の EKS Pod Identity を設定してください。IRSA では namespace／ServiceAccount に対する OIDC 信頼条件を確認してください。Pod Identity では agent／SDK の互換性と association を確認します。IAM ロールを作成しただけでは、ServiceAccount に権限は付与されません。

管理対象リソースに必要なコントローラーの read／create／update／delete／tag および PassRole 権限を確認してください。AmazonS3FullAccess や Resource:"*" は最小権限の例ではありません。サブガイドにあるデータアクセス用ポリシーも、コントローラーに必要なポリシー全体を示すものではありません。

レンダリングに成功しても、IAM、AWS API の制約、admission、CRD のインストール、エンドポイントへの接続、リソース作成が検証されたことにはなりません。コントローラーのインストールと CRD の変更は、それぞれ別の運用変更です。

## Namespace とアカウントの分離

既定の installScope は cluster です。dev／prod の namespace にリリースをインストールするだけでは、両方のコントローラーが同じ CR を監視し続けることがあります。この例では installScope=namespace と watchNamespace=infra を設定し、CARM と cross-namespace reference を無効にしています。他のチームには、監視範囲、ServiceAccount、IAM ロール、RBAC をそれぞれ分けてください。

namespace モードでも、現在のチャートは namespace cache 用に namespace の get／list／watch を許可する ClusterRole をレンダリングします。namespace モードですべてのクラスター権限がなくなるわけではありません。レンダリングされた Role、ClusterRole、Binding、Secret／FieldExport へのアクセスを確認してください。namespace annotation、role mapping、reference target を変更する権限も分離に影響します。

CARM は、対象ロールへの信頼設定、AssumeRole 権限、コントローラーの設定を必要とするクロスアカウント管理機能です。複数のクラスターによる同時変更が安全になることを保証するものではありません。読み取り専用の参照と、変更を管理する主体を分けてください。

## リソースの作成、参照、状態

サービスごとにスキーマは異なります。S3 のポリシーは Bucket.spec.policy に設定し、別個の BucketPolicy CRD はありません。IAM の管理ポリシーは Role.policies／policyRefs を通じて関連付けます。サブガイドでは、SQS の queueName／string 属性と、SNS 専用の Topic／Subscription フィールドを説明しています。

- [S3／IAM](ack/01-s3-iam.md)
- [SQS／SNS](ack/02-sqs-sns.md)
- [ELBv2／Route 53／Aurora](ack/03-elbv2-route53-rds.md)

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

ACK.ResourceSynced=True は、コントローラーによる同期状態を示します。データベース接続やアプリケーションの readiness を示すものではありません。ACK.Terminal／ACK.Recoverable などの他の condition とサービスの状態も確認してください。リソースに提供されている場合、ARN は status.ackResourceMetadata.arn にあります。NLB と TargetGroup の ARN もこのパスに格納されます。

サポートされる Ref フィールドを使うと、同じ namespace 内のリソースを関連付けられます。複数の YAML ドキュメントを適用しても、AWS 全体にわたるトランザクションにはなりません。参照先リソースの readiness と外部 identifier／ARN を確認してください。

## リソースの引き継ぎと保持

以下の ResourceAdoption annotation を使用します。現在の S3 チャートでは、この機能ゲートが有効です。引き継ぎの前に identifier、アカウント、リージョンを確認し、他のツールからの所有権移行を計画してください。

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: existing-data
  namespace: infra
  annotations:
    services.k8s.aws/adoption-policy: adopt
    services.k8s.aws/adoption-fields: '{"name":"REPLACE_WITH_EXISTING_BUCKET"}'
    services.k8s.aws/deletion-policy: retain
spec:
  name: REPLACE_WITH_EXISTING_BUCKET
```

実行時に指定できる値は adopt と adopt-or-create です。adopt は既存の状態を spec/status に読み込みます。adopt-or-create は、リソースが存在しない場合に作成できます。その後の通常の調整で引き継いだリソースが変更されることがあるため、引き継ぎは読み取り専用アクセスではありません。読み取り専用の動作は、独自のゲートとライフサイクルを持つ別の機能です。以前の resource-imported:"true" annotation ではリソースの引き継ぎは設定されません。公式ドキュメントでは AdoptedResource も以前の方式として扱っています。

保持値は **retain** です。現在のランタイムは orphan を受け付けません。適用される順序は、個別の CR にある services.k8s.aws/deletion-policy、namespace のサービス固有 deletion-policy、コントローラーの既定値です。AWS リソースを保持すると、その後のコスト、所有権管理、バックアップの責任も残ります。

## 可観測性、スケーリング、復旧

metrics.service.create を有効にし、以下の target namespace と port name を一致させてください。Prometheus Operator の CRD と Prometheus ServiceMonitor の selector は、それぞれ別に必要です。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames: [infra]
  selector:
    matchLabels:
      app.kubernetes.io/name: s3-chart
      app.kubernetes.io/instance: ack-s3
  endpoints:
    - port: metricsport
      interval: 30s
```

レビュー済みのランタイムで定義されているメトリクスは ack_outbound_api_requests_total と ack_outbound_api_requests_error_total です。reconcile の成功／失敗や API latency のメトリクス名を推測で作らないでください。実際のエンドポイントで controller-runtime のメトリクス名、ラベル、バージョンを確認してください。CloudTrail で監査できる範囲は、サービス／API のログ対応状況と設定したイベントに依存します。

レプリカ数は deployment.replicas で設定します。複数のレプリカを実行する場合は leaderElection.enabled を確認してください。replicaCount はこのチャートの設定項目ではありません。leader election を使うレプリカを増やしても、並列処理のスループットが自動的に向上するわけではありません。観測されたクォータ、スロットリング、リソース使用量に基づいて reconcile concurrency／resync を調整してください。

環境固有のマニフェストとチャートは Git でバージョン管理し、認証情報は含めないでください。復旧には CR だけでなく、AWS のデータ／バックアップ、識別子、保持ポリシー、所有権の情報も必要です。別リージョンに CR を作成しても、データ複製や復旧の仕組みにはなりません。

## トラブルシューティング

作成に失敗した場合は、condition／event、コントローラーのイメージ／ログ、アカウント／リージョン、IAM の信頼設定／ポリシー、参照、サービスの制約を確認してください。Kubernetes RBAC のエラーと AWS IAM のエラーを区別します。リソースが Terminating のままなら、finalizer が待機している AWS リソースの削除、依存関係、保持条件を特定してください。

通常の対処として finalizer を消さないでください。追跡されない AWS リソースが残ることがあります。まず原因を解決してください。最後の手段として復旧手順を使う場合も、実際のリソース状態、バックアップ、その後の所有権を確認してから実行してください。

## 検証と参考資料

56 個の異なるコードブロックを含む、韓国語／英語のガイド 8 本とクイズ 2 本を読みました。公式 OCI チャート 7 種をレンダリングし、未定義の spec フィールドを拒否する設定で、バージョン管理された CRD に対してリソース例 18 件を確認しました。AWS リソースの作成、コントローラーの実行、admission／CEL、メッセージ配送、データベース接続はテストしていません。

- [ACK 対応サービス](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [リソースの引き継ぎ](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [保持ポリシー](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 チャート 1.13.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/helm)
- [ランタイム 0.66.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.66.0)

[ACK クイズ](../quizzes/platform-engineering/02-ack-quiz.md)
