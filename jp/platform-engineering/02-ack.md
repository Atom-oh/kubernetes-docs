# AWS Controllers for Kubernetes (ACK)

## 目次

* [はじめに](02-ack.md#introduction)
* [アーキテクチャ](02-ack.md#architecture)
* [インストールと設定](02-ack.md#installation-and-configuration)
* [サポートされている AWS Services](02-ack.md#supported-aws-services)
* [ACK の起源と進化](02-ack.md#the-origins-and-evolution-of-ack)
* [Resource 作成例](02-ack.md#resource-creation-examples)
* [Resource 管理](02-ack.md#resource-management)
* [セキュリティに関する考慮事項](02-ack.md#security-considerations)
* [監視とログ](02-ack.md#monitoring-and-logging)
* [ベストプラクティス](02-ack.md#best-practices)
* [トラブルシューティング](02-ack.md#troubleshooting)
* [まとめ](02-ack.md#conclusion)

## はじめに

AWS Controllers for Kubernetes (ACK) は、Kubernetes ユーザーが Kubernetes API を通じて AWS services と resources を直接管理できるようにするプロジェクトです。ACK は Kubernetes の宣言的 API model を AWS resources に拡張し、開発者や運用担当者が使い慣れた Kubernetes tools と APIs を使って AWS infrastructure を管理できるようにします。

### ACK の主なメリット

* **統一された体験**: 同じ tools と workflows で Kubernetes と AWS resources を管理
* **GitOps サポート**: AWS resources を code として定義し、Git repositories で管理
* **宣言的な設定**: 望ましい状態を定義し、controller に実際の状態を調整させる
* **Kubernetes Native アプローチ**: 標準の Kubernetes concepts と APIs を使用
* **Multi-Cluster サポート**: 複数の clusters から同じ AWS resources を参照
* **IAM 統合**: Kubernetes service accounts と AWS IAM roles の統合

### 既存アプローチとの比較

| Feature                | ACK                 | AWS CloudFormation       | Terraform       | AWS SDK/CLI         |
| ---------------------- | ------------------- | ------------------------ | --------------- | ------------------- |
| Interface              | Kubernetes API      | CloudFormation templates | HCL             | Programming API/CLI |
| Declarative            | ✅                   | ✅                        | ✅               | ❌                   |
| State Management       | Kubernetes etcd     | CloudFormation stack     | Terraform state | Manual management   |
| Drift Detection        | ✅                   | ✅                        | ✅               | ❌                   |
| Kubernetes Integration | Native              | Limited                  | Limited         | Limited             |
| Supported Services     | Limited (expanding) | Extensive                | Extensive       | All services        |

## アーキテクチャ

ACK は Kubernetes operator pattern に基づいており、各 AWS service 向けの controllers を提供します。

### 主なコンポーネント

1. **Service Controller**: 各 AWS service 専用の controller
2. **Custom Resource Definitions (CRD)**: AWS resources を Kubernetes API として定義
3. **Custom Resources (CR)**: AWS resources の instances
4. **Reconciliation Loop**: 望ましい状態と実際の状態の差異を検出して解決

### 仕組み

1. ユーザーが AWS resource を定義する Kubernetes YAML manifest を適用する
2. ACK controller が custom resource の変更を検出する
3. Controller が AWS API を呼び出し、対応する AWS resource を作成、更新、または削除する
4. Controller が AWS resource の状態を監視し、Kubernetes resource status を更新する

## インストールと設定

### 前提条件

* Kubernetes cluster (v1.16 or higher)
* kubectl configured
* AWS account and appropriate IAM permissions
* Helm 3 (optional)

### インストール方法

#### 1. ACK Service Controller のインストール

ACK controllers は AWS service ごとに個別にインストールします。たとえば、S3 controller をインストールするには次のようにします。

```bash
# Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts

# Install S3 controller
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart
```

#### 2. IAM Permission の設定

ACK controllers が AWS resources を管理するには、適切な IAM permissions が必要です。IRSA (IAM Roles for Service Accounts) を使用して permissions を設定できます。

```bash
# Create IAM policy
aws iam create-policy \
  --policy-name ACKs3ControllerPolicy \
  --policy-document file://s3-controller-policy.json

# Attach IAM role to service account
eksctl create iamserviceaccount \
  --cluster=<cluster-name> \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::<account-id>:policy/ACKs3ControllerPolicy \
  --approve
```

s3-controller-policy.json の例:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutBucketTagging",
        "s3:GetBucketTagging",
        "s3:PutEncryptionConfiguration",
        "s3:GetEncryptionConfiguration",
        "s3:PutBucketPolicy",
        "s3:GetBucketPolicy",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 3. Controller 設定

Helm values files を使用して controller 設定をカスタマイズできます。

```yaml
# values.yaml
aws:
  region: us-west-2
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<account-id>:role/ACKs3ControllerRole
```

```bash
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart -f values.yaml
```

## サポートされている AWS Services

ACK はさまざまな AWS services 向けの controllers を提供します。各 service controller は個別にインストールして管理できます。

### 現在サポートされている Services（2025年7月時点）

* Amazon API Gateway (apigatewayv2)
* Amazon DynamoDB
* Amazon ECR
* Amazon EKS
* Amazon ElastiCache
* Amazon MemoryDB
* Amazon MQ
* Amazon RDS
* Amazon S3
* Amazon SageMaker
* AWS IAM
* AWS Lambda
* AWS SNS
* AWS SQS
* Amazon EventBridge
* Amazon MSK
* Amazon OpenSearch Service
* AWS ACM
* AWS Route 53

### Service Controller のステータス

各 service controller は次のいずれかの状態を持ちます。

* **Alpha**: 初期開発段階で、API が変更される可能性がある
* **Beta**: 機能は完成しており安定しているが、API が変更される可能性がある
* **GA (Generally Available)**: 本番環境での使用に対応

最新のステータスは [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community) で確認してください。

## ACK の起源と進化

### Infrastructure as Code の進化

AWS resource 管理は次のように進化してきました。

1. **Manual Management Era**: AWS Console で resources を直接作成および管理
2. **AWS CloudFormation**: Template-based の宣言的 infrastructure 管理の導入。ただし Kubernetes workflows からは分離
3. **Terraform**: Multi-cloud サポートと HCL による統一された infrastructure 管理。ただし、依然として別個の tools と workflows が必要
4. **ACK**: Kubernetes API を通じた直接的な AWS resource 管理 — kubectl、GitOps、RBAC など既存の K8s toolchain を活用

### なぜ Kubernetes-Native な AWS 管理なのか？

既存アプローチの制限:

* **Tool Separation**: Terraform/CloudFormation と kubectl を別々に運用する二重管理の負担
* **State Inconsistency**: IaC tool の state と Kubernetes cluster state が分離され、潜在的な drift の原因となる
* **GitOps Integration Difficulty**: ArgoCD/Flux などの GitOps tools で AWS resources を管理するのが難しい
* **Team Experience Fragmentation**: Infrastructure teams と application teams が異なる tools と workflows を使用

ACK は単一の Kubernetes control plane を通じて AWS infrastructure と applications を統一的に管理できるようにすることで、これらの課題に対応します。

## Resource 作成例

ACK で AWS resources を作成する詳細な例については、次のドキュメントを参照してください。

* [S3 and IAM](ack/01-s3-iam.md)
* [SQS and SNS](ack/02-sqs-sns.md)
* [ELBv2, Route 53, RDS (NLB + Aurora PostgreSQL)](ack/03-elbv2-route53-rds.md)

## Resource 管理

### Resource Status の確認

ACK resources の status を確認するには、次のようにします。

```bash
kubectl describe bucket my-sample-bucket
```

出力例:

```
Name:         my-sample-bucket
Namespace:    default
API Version:  s3.services.k8s.aws/v1alpha1
Kind:         Bucket
Metadata:
  ...
Spec:
  Name:  my-unique-bucket-name-123
  ...
Status:
  Ack Resource Metadata:
    Arn:                    arn:aws:s3:::my-unique-bucket-name-123
    Owner Account ID:       123456789012
  Conditions:
    Last Transition Time:  2025-07-13T04:00:00Z
    Status:                True
    Type:                  ACK.ResourceSynced
```

### Resources の更新

ACK resource を更新するには、manifest を変更して再適用します。

```bash
kubectl apply -f updated-bucket.yaml
```

### Resources の削除

ACK resource を削除するには、次のようにします。

```bash
kubectl delete bucket my-sample-bucket
```

デフォルトでは、Kubernetes resource が削除されると、ACK は対応する AWS resource も削除します。この動作は annotations を使用して変更できます。

```yaml
metadata:
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
```

### Resources のインポート

既存の AWS resources を ACK にインポートするには、次のようにします。

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: imported-bucket
  annotations:
    services.k8s.aws/resource-imported: "true"
spec:
  name: existing-bucket-name
```

## セキュリティに関する考慮事項

### IAM Permission 管理

ACK controllers が管理対象の AWS resources を扱うには、適切な IAM permissions が必要です。最小権限の原則に従い、必要な permissions のみを付与することを推奨します。

#### きめ細かな IAM Policy の例

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:GetBucketTagging",
        "s3:PutBucketTagging"
      ],
      "Resource": "arn:aws:s3:::my-unique-bucket-name-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Namespace Isolation

異なる teams や environments で別々の namespaces と IAM roles を使用し、permissions を分離できます。

```bash
# Install controller for development environment
helm install --create-namespace -n ack-system-dev ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleDev

# Install controller for production environment
helm install --create-namespace -n ack-system-prod ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleProd
```

### Resource Policies

Kubernetes RBAC を使用して ACK resources へのアクセスを制限できます。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: s3-editor
rules:
- apiGroups: ["s3.services.k8s.aws"]
  resources: ["buckets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-s3-editor
  namespace: dev
subjects:
- kind: User
  name: developer
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: s3-editor
  apiGroup: rbac.authorization.k8s.io
```

## 監視とログ

### Controller Logs の確認

ACK controller logs を確認するには、次のようにします。

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
```

### Prometheus Metrics

ACK controllers は Prometheus metrics を公開します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3-controller
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ack-s3-controller
  endpoints:
  - port: metrics
    interval: 30s
```

主な metrics:

* `ack_reconcile_success_total`: 成功した reconciliations の数
* `ack_reconcile_failure_total`: 失敗した reconciliations の数
* `ack_api_call_duration_seconds`: AWS API call の latency

### AWS CloudTrail 統合

ACK controllers によって行われた AWS API calls は CloudTrail に記録されます。CloudTrail logs を確認して ACK operations を監査できます。

## ベストプラクティス

### Resource Organization

1. **Clear Naming**: 明確で一貫性のある resource names を使用
2. **Use Annotations**: Resource 管理に annotations を活用
3. **Apply Labels**: Resource の grouping と filtering に labels を使用

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data-bucket
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
    description: "Application data storage"
  labels:
    environment: production
    app: my-application
    team: data-engineering
spec:
  name: my-app-data-20250713
  tagging:
    tagSet:
      - key: Environment
        value: Production
```

### Version Control

1. **Use Git Repository**: ACK resource manifests を Git repository に保存
2. **Separate Environment Configurations**: Development、staging、production environments 向けに別々の configurations を維持
3. **Use Kustomize**: Environment 固有の差異を管理するために Kustomize を使用

```
├── base/
│   ├── s3-bucket.yaml
│   ├── sqs-queue.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   └── prod/
│       ├── kustomization.yaml
│       └── patch.yaml
```

### Performance and Scalability

1. **Set Resource Requests and Limits**: Controllers に適切な resources を割り当て
2. **Scale Controller Replicas**: 大規模 environments では controller replicas を増やす
3. **Adjust Reconciliation Frequency**: 必要に応じて reconciliation frequency を最適化

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: ack-s3-controller
  namespace: ack-system
spec:
  chart:
    spec:
      chart: s3-chart
      sourceRef:
        kind: HelmRepository
        name: aws-controllers-k8s
  values:
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
    replicaCount: 2
```

### Disaster Recovery

1. **Backup Strategy**: ACK resource manifests の定期的なバックアップ
2. **Recovery Plan**: 障害発生時の resource recovery procedures を文書化
3. **Multi-Region Consideration**: 重要な resources には multi-region strategy を実装

## トラブルシューティング

### よくある問題

#### 1. Resource 作成の失敗

**症状**: ACK resource は作成されたが、AWS resource が作成されない

**解決策**:

* Controller logs を確認する
* IAM permissions を検証する
* Resource status と events を確認する

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
kubectl describe bucket my-sample-bucket
```

#### 2. Permission の問題

**症状**: "AccessDenied" error message

**解決策**:

* IAM policies と roles を検証する
* IRSA configuration を確認する
* CloudTrail logs を確認する

#### 3. Resource 削除が進まない

**症状**: Resource が "Terminating" state のままになる

**解決策**:

* Dependencies を確認する
* Finalizers を削除する（必要な場合）

```bash
kubectl patch bucket my-sample-bucket -p '{"metadata":{"finalizers":[]}}' --type=merge
```

### デバッグ Tools

```bash
# Check controller version
kubectl get deployment -n ack-system ack-s3-controller -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check CRDs
kubectl get crd | grep services.k8s.aws

# Check events
kubectl get events --field-selector involvedObject.name=my-sample-bucket

# Check controller logs in detail
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller --tail=100
```

## まとめ

AWS Controllers for Kubernetes (ACK) は、Kubernetes と AWS services のギャップを埋める強力な tool です。ACK により、Kubernetes ユーザーは使い慣れた Kubernetes APIs と tools を使用して AWS resources を管理できます。

このドキュメントでは、ACK の基本概念、インストール方法、S3、IAM、SQS、SNS resource 作成例、resource 管理、セキュリティに関する考慮事項、監視、トラブルシューティングについて説明しました。

ACK は進化を続けており、より多くの AWS services のサポートが追加されています。GitOps workflows と組み合わせることで、AWS infrastructure を code として管理する強力な方法を提供します。

### 次のステップ

* ACK を使用して GitOps pipelines を構築する
* 複数の AWS service controllers を統合する
* Custom resource definitions を拡張する
* Multi-account と multi-region strategies を開発する

## 参考資料

* [ACK Official Documentation](https://aws-controllers-k8s.github.io/community/)
* [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community)
* [AWS Service Controller List](https://aws-controllers-k8s.github.io/community/docs/community/services/)
* [ACK Design Principles](https://aws-controllers-k8s.github.io/community/docs/community/design/)
* [EKS Workshop - ACK](https://www.eksworkshop.com/intermediate/290_ack/)

## クイズ

この章で学んだ内容を確認するには、[ACK Quiz](../quizzes/platform-engineering/02-ack-quiz.md) に挑戦してください。
