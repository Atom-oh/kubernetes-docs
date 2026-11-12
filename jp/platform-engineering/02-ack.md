# AWS Controllers for Kubernetes (ACK)

> **最終更新日**: 2026年10月23日

## 概念とアーキテクチャ

ACKは、サービス固有のコントローラーを通じて、KubernetesのカスタムリソースとAWS APIを接続します。CRDは入力を定義し、コントローラーは望ましい状態と観測されたAWSの状態を調整します。CRを作成しても、AWSリソースの準備が完了したことにはなりません。ステータスと、そのサービス固有の準備状態を確認してください。

ACKはKubernetes API、RBAC、GitOpsツールを再利用しますが、Kubernetesの認可とAWS IAMは別々のままです。通常、ユーザーのCRによって、コントローラーのAWS権限で操作が実行されます。したがって、CRを書き込む権限を与えることは、そのコントローラーを通じてAWS操作を要求する能力を委譲することになります。

ACKは、CloudFormationやTerraformを必ず置き換えるものではありません。実際のリソースはAWSが保持し、CRのspec/statusはKubernetesが保持します。ドリフトの処理は、サポートされるフィールドとコントローラーのロジックに依存します。複数のツールやクラスターで同じAWSリソースを調整するのではなく、変更の所有者を1つに決めてください。

![ACKはAWS APIを通じてKubernetesカスタムリソースを調整します](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

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

これらのバージョンは、公式リリースとOCI Chartに照らして確認済みです。対応状況の全容とAlpha/Beta/GAのステータスについては、公式のサービス一覧を参照してください。GAであっても、すべてのAWS API機能や運用上の要件がカバーされているとは限りません。CRDのv1alpha1というAPI文字列は、コントローラーの成熟度とは別のものです。

過去に示されていたKubernetes 1.16という最小要件は、現在の運用基準ではありません。サポート対象のKubernetes/EKSバージョン、コントローラーとの互換性、Helmのバージョン、CRDのアップグレード手順をまとめて確認してください。

## インストールの準備とオフラインでの確認

以前のeks-charts s3-chartパスではなく、以下のOCI Chartパスを使用してください。このコマンドは、クラスターにインストールせずにマニフェストをレンダリングします。

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

実際にインストールまたはアップグレードする前に、infra namespaceとコントローラーのServiceAccountを準備し、IRSAまたはサポートされているEKS Pod Identityを設定してください。IRSAを使う場合はnamespace/ServiceAccountに対するOIDCの信頼条件を確認し、Pod Identityを使う場合はエージェント/SDKとの互換性と関連付けを確認してください。IAMロールを作成しただけでは、ServiceAccountに権限は付与されません。

管理対象リソースに対するコントローラーの読み取り/作成/更新/削除/タグ付け権限と、必要に応じたPassRole権限を確認してください。AmazonS3FullAccessやResource:"*"は最小権限の例ではありません。サブガイドに記載されているデータアクセス用のポリシーは、コントローラー用ポリシーの完全な例ではありません。

レンダリングに成功しても、IAM、AWS APIの制約、Admission、CRDのインストール、エンドポイントへの接続性、リソース作成が検証されたことにはなりません。コントローラーのインストールとCRDの変更は、別々の運用変更です。

## Namespaceとアカウントの分離

デフォルトのinstallScopeはclusterです。リリースをdev/prod namespaceにインストールするだけでは、両方のコントローラーが同じCRを監視する状態になり得ます。この例では、installScope=namespaceとwatchNamespace=infraを設定し、CARMとnamespaceをまたぐ参照を無効にしています。他のチームには、個別の監視範囲、ServiceAccount、IAMロール、RBACを使用してください。

namespaceモードでも、現在のChartは、namespaceキャッシュのためにnamespaceに対するget/list/watchを許可するClusterRoleをレンダリングします。namespaceモードにしても、すべてのクラスター権限がなくなるわけではありません。レンダリングされたRole、ClusterRole、Binding、Secret/FieldExportへのアクセスを確認してください。namespaceのアノテーション、ロールのマッピング、参照先を変更する権限も、分離に影響します。

CARMは、対象ロールの信頼設定、AssumeRole権限、コントローラーの設定を必要とするクロスアカウント管理機能です。複数のクラスターによる安全な同時変更を保証するものではありません。読み取り専用の参照と、変更の所有権を分けてください。

## 作成、参照、ステータス

サービスによってスキーマは異なります。S3ポリシーはBucket.spec.policyに設定し、個別のBucketPolicy CRDはありません。IAMの管理ポリシーはRole.policies/policyRefsを通じてアタッチします。SQSのqueueName/string属性と、SNS専用のTopic/Subscriptionフィールドについては、サブガイドを参照してください。

- [S3 / IAM](ack/01-s3-iam.md)
- [SQS / SNS](ack/02-sqs-sns.md)
- [ELBv2 / Route 53 / Aurora](ack/03-elbv2-route53-rds.md)

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

ACK.ResourceSynced=Trueはコントローラーとの同期状態を示すものであり、データベースへの接続やアプリの準備状態を確認するものではありません。ACK.Terminal/ACK.Recoverableなど、他の条件やサービスのステータスも確認してください。リソースに指定されている場合、そのARNはstatus.ackResourceMetadata.arnにあります。NLBとTargetGroupのARNも同じパスを使います。

サポート対象のRefフィールドを使って、同じnamespace内のリソースを接続できます。複数のYAMLドキュメントを適用しても、AWS全体にわたるトランザクションにはなりません。参照先リソースの準備状態と、外部識別子/ARNを確認してください。

## 既存リソースの取り込みと保持

以下のResourceAdoptionアノテーションを使用してください。現在のS3 Chartでは、この機能ゲートが有効になっています。識別子、アカウント、リージョンを確認し、取り込み前に他のツールから所有権を移す計画を立ててください。

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

ランタイムで受け付けられる値はadoptとadopt-or-createです。adoptは既存の状態をspec/statusに読み込みます。adopt-or-createは、リソースが存在しない場合に作成できます。その後の通常の調整では、取り込んだリソースが変更される可能性があるため、取り込みは単なる読み取りアクセスではありません。読み取り専用の動作は独自のゲートとライフサイクルを持つ別の機能です。以前のresource-imported:"true"アノテーションでは、取り込みは設定されません。公式ドキュメントでは、AdoptedResourceは旧方式とも説明されています。

保持値は**retain**です。現在のランタイムはorphanを受け付けません。優先順位は、個々のCRのservices.k8s.aws/deletion-policy、namespaceのサービス固有のdeletion-policy、コントローラーのデフォルトの順です。AWSリソースを保持すると、継続的なコスト、所有権、バックアップに関する責任が残ります。

## 可観測性、スケーリング、復旧

metrics.service.createを有効にし、以下の対象namespaceとポート名を一致させてください。Prometheus OperatorのCRDと、PrometheusのServiceMonitorセレクターは、それぞれ別途必要です。

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

確認済みのランタイムでは、ack_outbound_api_requests_totalとack_outbound_api_requests_error_totalが定義されています。調整の成功/失敗やAPIレイテンシのメトリクス名を作り出さないでください。実際のエンドポイントでcontroller-runtimeのメトリクス名、ラベル、バージョンを確認してください。CloudTrailの監査は、サービス/APIのログ記録サポートと設定されたイベントに依存します。

レプリカの設定はdeployment.replicasです。複数のレプリカを実行する場合は、leaderElection.enabledも確認してください。replicaCountはこのChartの設定項目ではありません。リーダー選出されるレプリカを追加しても、並列スループットが自動的に増えるわけではありません。観測されたクォータ、スロットリング、リソース使用量を踏まえて、調整の並行数/再同期を調整してください。

環境ごとのマニフェストとChartをGitでバージョン管理し、認証情報は含めないでください。復旧には、CRだけでなくAWSのデータ/バックアップ、識別子、保持ポリシー、所有権も必要です。別のリージョンにCRを作成しても、データのレプリケーションや復旧は実現されません。

## EKSマネージドACK

EKS CapabilitiesのACK機能は、AWSが所有するインフラストラクチャ上で、アップストリームのGAサービスコントローラーを1つのCapabilityとして実行します。2026年10月時点のテストに基づくと、以下の点で上記のHelmインストールとは異なります。

- IAMは単一のCapabilityロールから始まり、クラスター範囲の`IAMRoleSelector`によってnamespaceごとに異なるロールを引き受けます。OSSコントローラーで同じ分離を行うには、`featureGates.IAMRoleSelector=true`と`enableCARM=false`の両方が必要です。CARMを有効にしたままでは、コントローラーは起動しません。
- AWSリソースタグとセッションタグでは`eks:`プレフィックス（`eks:eks-capability-arn`など）が使われます。移行時には、OSSの`services.k8s.aws/`タグに基づいて記述されたコスト配分とIAM条件を更新してください。
- `FieldExport` CRDはなく、コントローラーのバージョンと再同期間隔を選択・変更することもできません。マネージド環境でもOSS環境でも、25分以内にAWS側のドリフトが定期的に元に戻されることはありませんでした。
- 取り込み（`adopt-or-create`）と`deletion-policy: retain`のアノテーションは、マネージドCapabilityでも動作しました（マネージド環境で測定）。RETAINを指定してCapabilityを削除した後にOSSコントローラーをインストールしたところ、既存のCRが取り込まれました。

測定結果と選択の指針については、[EKS Capabilities](../eks/13-eks-capabilities.md)を参照してください。

## トラブルシューティング

作成に失敗した場合は、条件/イベント、コントローラーのイメージ/ログ、アカウント/リージョン、IAMの信頼設定/ポリシー、参照、サービスの制約を確認してください。Kubernetes RBACのエラーとAWS IAMのエラーを区別してください。Terminating状態のリソースについては、ファイナライザーが待機しているAWS側の削除、依存関係、保持に関する条件を特定してください。

日常的にファイナライザーをクリアしないでください。追跡されないAWSリソースが残る可能性があります。まず原因を解決してください。最後の手段として復旧手順を使う場合も、実際のリソース状態、バックアップ、その後の所有権を確認してから実施してください。

## 検証と参考資料

韓国語/英語の元のガイドファイル8件とクイズ2件を、固有のコードブロック56個を含めて読みました。公式OCI Chart 7件をレンダリングし、バージョン管理されたCRDに照らしてリソース例18件を確認し、未定義のspecフィールドが拒否されることも検証しました。AWSリソースの作成、コントローラーの実行、Admission/CEL、メッセージ配信、データベース接続はテストしていません。

- [ACKサービス](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [リソースの取り込み](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [保持](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 Chart 1.13.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/helm)
- [Runtime 0.66.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.66.0)

[ACKクイズ](../quizzes/platform-engineering/02-ack-quiz.md)
