# AWS Controllers for Kubernetes (ACK)

> **最終更新**: September 12, 2026

## 概念とアーキテクチャ

ACK は、サービス固有の controller を通じて Kubernetes custom resource を AWS API に接続します。CRD は入力を定義し、controller は期待状態を観測された AWS 状態と reconcile します。CR を作成しても、AWS resource の準備が完了しているとは限りません。status とサービス自身の readiness を確認してください。

ACK は Kubernetes API、RBAC、GitOps tool を再利用しますが、Kubernetes authorization と AWS IAM は別個のままです。通常、ユーザーの CR は controller の AWS permission で action を実行します。したがって、CR の書き込み permission は、その controller を通じて AWS action をリクエストする能力を委譲します。

ACK は CloudFormation や Terraform の必須の後継ではありません。実際の resource は AWS にあり、Kubernetes には CR spec/status があります。drift handling は、サポートされる field と controller logic に依存します。複数の tool や cluster が同じ AWS resource を reconcile するのではなく、mutation owner を 1 つに割り当ててください。

![ACK は Kubernetes custom resource を AWS API を介して reconcile する](../.gitbook/assets/en-platform-engineering-02-ack-0.png)

[インタラクティブな図](https://www.atomai.click/kubernetes-docs/archmaps/en-platform-engineering-02-ack-0.html)

## バージョンとサポート

| Controller | Version |
| --- | --- |
| s3 | 1.12.1 |
| iam | 1.9.0 |
| sqs | 1.7.0 |
| sns | 1.10.1 |
| elbv2 | 1.7.0 |
| route53 | 1.6.0 |
| rds | 1.12.0 |

これらの version は公式 release と OCI chart に照らして確認しました。完全な coverage と Alpha/Beta/GA status については、公式 service list を参照してください。GA は、すべての AWS API feature またはすべての運用要件がカバーされることを意味しません。CRD の v1alpha1 API string は controller maturity とは別のものです。

過去の Kubernetes 1.16 minimum は、現在の運用 baseline ではありません。サポート対象の Kubernetes/EKS version、controller compatibility、Helm version、CRD upgrade process をまとめて検証してください。

## インストール準備とオフライン検査

以前の eks-charts s3-chart path ではなく、以下の OCI chart path を使用してください。この command は cluster にインストールせずに manifest を render します。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

実際の install/upgrade の前に、infra namespace と controller ServiceAccount を準備し、IRSA またはサポート対象の EKS Pod Identity を設定してください。IRSA の namespace/ServiceAccount 用 OIDC trust condition、または Pod Identity の agent/SDK compatibility と association を検証してください。IAM role を作成するだけでは、ServiceAccount に permission は付与されません。

managed resource に対する controller の read/create/update/delete/tag と PassRole permission を確認してください。AmazonS3FullAccess や Resource:"*" は least-privilege の例ではありません。サブガイドの data-access policy は完全な controller policy ではありません。

render の成功は、IAM、AWS API constraint、admission、CRD installation、endpoint connectivity、resource creation を検証するものではありません。controller のインストールと CRD の変更は別個の運用変更です。

## Namespace と Account の分離

デフォルトの installScope は cluster です。dev/prod namespace に release をインストールするだけでは、両方の controller が同じ CR を watch したままになる可能性があります。この例では installScope=namespace と watchNamespace=infra を設定し、CARM と cross-namespace reference を無効にしています。ほかの team には、別々の watch scope、ServiceAccount、IAM role、RBAC を使用してください。

namespace mode でも、現在の chart は namespace cache 用に namespace の get/list/watch を付与する ClusterRole を render します。namespace mode はすべての cluster permission を除去するわけではありません。render された Role、ClusterRole、Binding、および Secret/FieldExport access を検査してください。namespace annotation、role mapping、reference target を変更する permission も分離に影響します。

CARM は、target-role trust、AssumeRole permission、controller configuration を必要とする cross-account management です。複数の cluster による安全な concurrent mutation を保証するものではありません。read-only reference と mutation ownership を分離してください。

## 作成、Reference、Status

service schema は異なります。S3 policy は Bucket.spec.policy に属し、別個の BucketPolicy CRD はありません。IAM managed policy は Role.policies/policyRefs を通じて attach します。サブガイドでは、SQS queueName/string attribute と専用の SNS Topic/Subscription field を示しています。

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

ACK.ResourceSynced=True は controller synchronization を示します。database connection や app-readiness check を示すものではありません。ACK.Terminal/ACK.Recoverable などの他の condition と service status を確認してください。resource に提供されている場合、その ARN は status.ackResourceMetadata.arn にあります。NLB と TargetGroup の ARN もこの path を使用します。

サポートされる Ref field は、同じ namespace 内の resource を接続できます。複数の YAML document を apply しても、AWS 全体の transaction にはなりません。参照される resource の readiness と external identifier/ARN を検証してください。

## Adoption と Retention

以下の ResourceAdoption annotation を使用してください。現在の S3 chart ではこの feature gate が有効です。adoption の前に identifier、account、region を確認し、ほかの tool からの ownership transfer を計画してください。

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

runtime は adopt と adopt-or-create を受け入れます。adopt は既存の state を spec/status に読み込みます。adopt-or-create は存在しない resource を作成できます。その後の通常の reconciliation は adopted resource を変更できるため、adoption は単なる read access ではありません。read-only behavior は、固有の gate と lifecycle を持つ別機能です。以前の resource-imported:"true" annotation は adoption を設定しません。公式 documentation では、AdoptedResource を以前の approach としても位置付けています。

retention value は **retain** です。現在の runtime は orphan を受け入れません。優先順位は、個々の CR の services.k8s.aws/deletion-policy、namespace の service-specific deletion-policy、controller default の順です。AWS resource を retain すると、継続する cost、ownership、backup responsibility が残ります。

## Observability、Scaling、Recovery

metrics.service.create を有効にし、以下の target namespace と port name を一致させてください。Prometheus Operator CRD と Prometheus ServiceMonitor selector は別個の前提条件です。

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

確認した runtime は ack_outbound_api_requests_total と ack_outbound_api_requests_error_total を定義しています。reconcile success/failure や API-latency metric name を勝手に作らないでください。実際の endpoint で controller-runtime の metric name、label、version を検証してください。CloudTrail auditing は service/API logging support と設定された event に依存します。

replica configuration は deployment.replicas です。複数の replica を実行する場合は leaderElection.enabled を確認してください。replicaCount はこの chart の設定ではありません。追加の leader-elected replica によって parallel throughput が自動的に増加するわけではありません。観測した quota、throttling、resource usage に基づいて reconcile concurrency/resync を調整してください。

environment-specific manifest と chart を Git で version 管理し、credential は含めないでください。recovery には、CR だけでなく AWS data/backup、identifier、retention policy、ownership が必要です。別の region で CR を作成しても、data replication や recovery は実装されません。

## トラブルシューティング

作成失敗の場合は、condition/event、controller image/log、account/region、IAM trust/policy、reference、service constraint を検査してください。Kubernetes RBAC error と AWS IAM error を区別してください。Terminating resource では、finalizer が待機している AWS deletion、dependency、retention condition を特定してください。

finalizer を常に削除しないでください。そうすると、追跡されない AWS resource が残る可能性があります。まず原因を解決してください。実際の resource state、backup、その後の ownership を確認したうえで、最後の手段としてのみ recovery procedure を使用してください。

## 検証と参照

56 個の一意な code block を含む、韓国語/英語の 8 個の元の guide file と 2 個の quiz を読みました。7 個の公式 OCI chart を render し、18 個の resource example を、unknown-spec-field rejection を備えた versioned CRD に対して確認しました。AWS resource creation、controller execution、admission/CEL、message delivery、database connectivity はテストしていません。

- [ACK service](https://aws-controllers-k8s.github.io/community/docs/community/services/)
- [Resource adoption](https://aws-controllers-k8s.github.io/community/docs/user-docs/features/#resourceadoption)
- [Retention](https://aws-controllers-k8s.github.io/community/docs/user-docs/deletion-policy/)
- [S3 chart 1.12.1](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/helm)
- [Runtime 0.63.0](https://github.com/aws-controllers-k8s/runtime/tree/v0.63.0)

[ACK quiz](../quizzes/platform-engineering/02-ack-quiz.md)
