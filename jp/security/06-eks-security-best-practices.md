# EKS セキュリティのベストプラクティス

> **レビュー基準**: 最新の AWS ドキュメント、Kubernetes 1.35 API スキーマ、Terraform 1.15.7 / AWS プロバイダー 6.64.0。実クラスターへのデプロイは実施していません。
> **最終更新**: September 13, 2026

このドキュメントでは、Amazon EKS 環境におけるセキュリティのベストプラクティスを扱います。IAM 統合からネットワークセキュリティ、ランタイム保護まで、EKS クラスターを安全に運用する方法を学びます。

## 目次

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [Control Plane Logging](#control-plane-logging)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [Cluster Encryption](#cluster-encryption)
10. [Node Security](#node-security)
11. [Private Clusters](#private-clusters)
12. [Multi-tenancy Patterns](#multi-tenancy-patterns)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA の概要

IRSA (IAM Roles for Service Accounts) は IAM ロールを Kubernetes ServiceAccount に関連付け、Pod から AWS サービスへ安全にアクセスできるようにします。

Kubernetes API サーバーが projected ServiceAccount トークンを発行します。SDK はそれを STS AssumeRoleWithWebIdentity で交換し、STS は IAM OIDC プロバイダーに紐づく issuer / JWKS とロールの信頼条件を検証してから一時的な認証情報を返します。IAM OIDC プロバイダーオブジェクトは、トークンを発行する稼働中のプロキシではありません。


### IRSA のセットアップ

以下のオペレーター向けの例は実行していません。実際のリージョン、クラスター、バケットの所有者/パス、ポリシー ARN に合わせ、アプリケーションイメージはレビュー済みのバージョン/ダイジェストに置き換えてください。別リージョンの OIDC issuer や、推測した eksctl 生成ロール ARN を混在させないでください。



```bash
# 1. Create OIDC Provider (once per cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. Create IAM policy
cat <<'EOF' > s3-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        },
        "StringLike": {
          "s3:prefix": [
            "app-data",
            "app-data/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket/app-data/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        }
      }
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name S3ReadPolicy \
    --policy-document file://s3-policy.json

# 3. Create IAM ServiceAccount
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### IRSA の利用

```yaml
# Reuse the ServiceAccount created by eksctl; do not guess its generated role ARN.
# Use ServiceAccount in Pod
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa
  containers:
  - name: app
    image: public.ecr.aws/aws-cli/aws-cli:replace-with-reviewed-version
    command: ["aws", "s3", "ls", "s3://replace-with-owned-bucket/app-data/"]
    # AWS SDK automatically uses IRSA token
```

### IRSA の信頼ポリシー

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### IRSA のベストプラクティス

```yaml
# 1. Principle of least privilege
# Grant only minimum required permissions to each ServiceAccount

# 2. Separate ServiceAccounts per namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dynamodb-reader
  namespace: orders-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-dynamodb-role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-uploader
  namespace: media-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/media-s3-role
```

---

## EKS Pod Identity

### Pod Identity の概要

EKS Pod Identity は、認証情報を配布する別の仕組みです。IRSA との選択は、実際のプラットフォーム/SDK のサポート状況、信頼境界、運用要件に基づいて判断してください。IRSA を廃止するものではなく、すべてのワークロードを自動的にセキュアにするものでもありません。

サポートされる Pod SDK はローカルエージェント経路を使用し、エージェントは association とロールに従って EKS Auth を通じて一時的な認証情報を取得します。クロスアカウントのロールやロールチェーンについては、現時点でサポートされる仕組み、信頼条件、セッションタグ条件を個別に確認してください。


### Pod Identity のセットアップ

EKS Auto Mode にはエージェントが含まれます。その他のサポート対象プラットフォームでは、現在互換性のあるアドオンバージョンを選択し、既存のオーナーを通じて管理してください。以下のアカウント/クラスター/namespace/ServiceAccount の値を置き換え、意図した namespace / ServiceAccount のセッションタグ条件でロールの信頼関係を制限してください。アドオンと association をインストールしただけでは、SDK の互換性、認証情報の優先順位、ネットワークアクセスは検証されません。



```bash
# 1. Install Pod Identity Agent addon
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# 2. Create IAM role (with Pod Identity trust policy)
cat <<'EOF' > trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes-namespace": "production",
          "aws:RequestTag/kubernetes-service-account": "my-app-sa"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
    --role-name my-pod-role \
    --assume-role-policy-document file://trust-policy.json

# 3. Attach policy
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Create Pod Identity Association
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Pod Identity の利用

```yaml
# ServiceAccount (no annotation needed)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
---
# Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK automatically uses Pod Identity
```

### IRSA と Pod Identity の比較

| 項目 | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **セットアップの複雑さ** | OIDC Provider が必要 | シンプル (API 呼び出し) |
| **信頼ポリシー** | 正確な OIDC issuer、audience、subject | サービスプリンシパルと制限条件 |
| **ロールの再利用** | クラスターごとの修正が必要 | クラスター間で再利用可能 |
| **監査ログ** | CloudTrail (SA レベル) | CloudTrail (Pod レベル) |
| **セッションタグ** | EKS Pod Identity と同じセッションタグ動作を前提にしないこと | ドキュメント化されたセッションタグをサポート。無効化/チェーンの動作は確認が必要 |
| **選択基準** | サポート対象プラットフォーム、OIDC 信頼、運用モデル | サポート対象プラットフォーム、association、エージェント/SDK モデル |

---

## Security Groups for Pods

### 概要

Security Groups for Pods は VPC セキュリティグループを Pod に直接適用し、ネットワークレベルの分離を提供します。

### 前提条件

```bash
# Inspect the installed CNI and verify current platform/version requirements
kubectl describe daemonset aws-node -n kube-system | grep Image

# Enable Security Groups for Pods
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Attach to the EKS CLUSTER role, after resolving its actual name
aws iam attach-role-policy \
    --role-name "$EKS_CLUSTER_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Security Groups for Pods には、トランキングに対応したサポート対象インスタンスと CNI モードが必要です。最新のドキュメントでは Windows と EKS Auto Mode は対象外であり、すべての Nitro インスタンスがサポートされているわけではありません。VPC Resource Controller のポリシーはクラスターロールに付与します。複数のセキュリティグループをアタッチした場合、許可ルールは結合されます。積集合にはなりません。有効化する前に strict / standard モード、DNS、プローブ、ロードバランサーの動作を確認してください。

### SecurityGroupPolicy の設定

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # Target Pod selection
  podSelector:
    matchLabels:
      app: database
  # Security Groups to apply
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # Database SG
      - sg-0987654321fedcba0  # Common monitoring SG
```

### Terraform によるセキュリティグループ設定

アタッチされた SG のルールが結合されることを踏まえ、実際のソースセキュリティグループと必要なデータベース、レプリケーション、モニタリングのポートを特定してください。SecurityGroupPolicy、ソース/ターゲット SG、VPC、Pod セレクターは整合している必要があります。旧来の宣言には未定義のモジュール/SG 参照と無制限の egress が含まれており、完全なデプロイモジュールではありませんでした。

セキュリティグループの戻りトラフィックはステートフルですが、アプリケーションが新規に開始する DNS / データベース / 外部への接続には別途 egress の要件があります。宛先を限定し、CNI の強制モードと NetworkPolicy を有効にした状態で接続性をテストしてください。この監査ではセキュリティグループ / Pod ENI の作成やネットワーク分離テストの実行は行っていません。

---

## VPC Endpoints

### プライベート EKS のための VPC Endpoints

Kubernetes のプライベート API エンドポイントと、AWS サービス向けの PrivateLink エンドポイントは別物です。`eks` VPC エンドポイントは、kubectl が使用する Kubernetes API 接続を代替しません。実際のノード、ワークロード、オペレーターの経路で必要なサービスのみを選択し、リージョンのサポート状況、DNS、セキュリティグループ、ルート、エンドポイントポリシー、IAM をあわせて確認してください。

| 目的 | 経路 |
|---|---|
| Kubernetes API | クラスターのプライベート API エンドポイントと接続されたネットワーク |
| EKS 管理 API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA の STS 交換 | `com.amazonaws.<region>.sts`。SDK でリージョナル STS を設定する |
| OIDC ディスカバリー/JWKS | 現在ドキュメント化されている `com.amazonaws.<region>.oidc-eks`。STS とは別 |
| ECR イメージ | `ecr.api`、`ecr.dkr` インターフェイスと S3 のイメージレイヤー経路 |
| 追加のサービス | 実際に使用する EC2、Logs、ELB、Auto Scaling、SSM などの API について確認済みのエンドポイント |

最新の EKS プライベートクラスターのドキュメントには、Route 53 API サービス `com.amazonaws.route53` も記載されています。DNS 解決と Route 53 管理 API 呼び出しを区別し、サービス/リージョンのサポート状況を確認してください。レガシーな `ec2messages` エンドポイントをすべてのリージョンで無条件に作成しないでください。SSM Agent とメッセージングの要件を確認してください。

### Terraform による VPC Endpoint のセットアップ

[完全な Terraform の例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints) は `論理名 → 正確なサービス名` のマップを受け取ります。旧来の `split(...)[4]` はサービス名の長さによって範囲外になったり誤ったタグを生成する可能性があったため、タグには `each.key` を使用します。

既存のサブネット、ルートテーブル、承認済みクライアントセキュリティグループ、レビュー済みの S3 エンドポイントポリシーを指定してください。HTTPS は指定したクライアントグループからのみ許可されます。S3 ポリシーは ECR レイヤー用バケットやその他の必要なバケットを対象に含める必要があります。エンドポイントポリシー自体が IAM アクセスを許可するわけではありません。Terraform 1.15.7 / AWS プロバイダー 6.64.0 でのスキーマ検証は通過しましたが、plan / apply やリソース作成は実施していません。

---

## Control Plane Logging

### EKS コントロールプレーンのログタイプ

サポートされるタイプは `api`、`audit`、`authenticator`、`controllerManager`、`scheduler` です。kubelet / コンテナのログには別の収集経路があります。ロググループは `/aws/eks/<cluster-name>/cluster` です。リージョン、保持期間、アクセス、暗号化、機微データの取り扱い、収集コストを運用ポリシーに従って設定してください。

### ロギングの有効化

変更は既存クラスターの IaC オーナーと調整してください。以下は自身が所有するクラスターを対象としたもので、この監査では実行していません。更新は非同期です。返された更新 ID を `describe-update` で確認し、その後で実際にログが到達しているかを別途検証してください。ロギングの有効化にあたって、新しいクラスターリソースを宣言したり API エンドポイントの公開設定を変更する必要はありません。

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights クエリ

以下は **それぞれ独立した Logs Insights QL クエリ** です。選択したロググループで実際のフィールド / 時間範囲を確認してください。最初のクエリは探索的なテキストマッチであり、認証失敗を完全に検出するものではありません。この監査ではマネージドクエリエンジンの実行は行っていません。

Authenticator のエラー (探索用)

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

特定のアイデンティティによる呼び出し

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

認可の拒否

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Secret API へのアクセス

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection

### GuardDuty EKS Protection の概要

EKS 監査ログの分析、Runtime Monitoring、GuardDuty の基本データソースは区別してください。EKS 監査ログ分析は Kubernetes API のアクティビティを対象とし、ユーザーが CloudWatch へのコントロールプレーンログのエクスポートを有効化しているかどうかには依存しません。Runtime Monitoring にはセキュリティエージェントと実際のカバレッジが必要です。

現在の Runtime Monitoring のドキュメントでは EC2 ベースの EKS と EKS Auto Mode がサポート対象で、EKS Hybrid Nodes と EKS Fargate は対象外です。ECS Fargate のサポートは EKS Fargate のサポートではありません。組織 / 委任管理者の所有関係、リージョンごとの detector、プラットフォーム、コスト、エージェント管理のオーナーを確認してください。

### GuardDuty の有効化

以下は既存の detector に対する **設定ペイロードの例** であり、アカウントに適用したものではありません。`RUNTIME_MONITORING` は EKS を含むため、`EKS_RUNTIME_MONITORING` と併せて指定するのは無効です。常に detector を作成して最初に返された ID を選ぶのではなく、自身が所有する detector を確認してください。エージェント自動管理のリソース / 権限と、実測されたカバレッジをレビューしてください。

```json
[
  {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
  {
    "Name": "RUNTIME_MONITORING",
    "Status": "ENABLED",
    "AdditionalConfiguration": [
      {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
    ]
  }
]
```

### GuardDuty EKS の検出タイプ

実際のタイプには tactic のプレフィックスが付きます。作り込んだ固定の重要度テーブルではなく、検出結果の `severity`、リソース、アカウント/リージョン、カバレッジ、公式の説明を使用してください。

| 実際のタイプ例 | 範囲 |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API アクティビティ |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | 異常な Kubernetes 権限チェック |
| `Execution:Runtime/ReverseShell` | エージェントが観測したランタイム動作 |
| `CryptoCurrency:Runtime/BitcoinTool.B` | ランタイムのマイニング関連検出 |

### 検出結果への自動対応

この EventBridge パターンは Kubernetes / Runtime のタイプをルーティングします。旧来の `prefix: Kubernetes` と `prefix: Runtime` は、実際の tactic プレフィックス付きの名前にはマッチしませんでした。マッチする/しない 6 つのケースと旧来の失敗は、公式の AWS Event Ruler 2.2.0 ライブラリで検証しました。

このパターンには通知 / 隔離のターゲットがありません。Runtime の検出結果は EKS 以外のリソースに関わることもあります。承認済みの対応にルーティングする前に、実際のリソースメタデータを確認してください。ターゲットのロール / 権限、リトライ、DLQ、重複排除は別途設定してください。`boto3.client("eks")` を作成しても Pod は隔離されません。封じ込めには設計された CNI / ホスト / クラウドの制御と、権限のある Kubernetes 操作が必要です。

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [
      {"wildcard": "*:Kubernetes/*"},
      {"wildcard": "*:Runtime/*"}
    ]
  }
}
```

---

## Amazon Inspector

### Inspector によるコンテナイメージスキャン

ECR の拡張スキャンは Amazon Inspector と統合し、サポート対象イメージのパッケージ脆弱性を検査します。実行中イメージの利用コンテキストは、ランタイム動作の検知とは異なります。同じイメージスキャンで任意の Kubernetes マニフェスト、IAM ポリシー、実際のネットワークトラフィックを検査することはできません。

レジストリスキャンの変更はアカウント / リージョンとリポジトリフィルターの範囲に影響します。所有関係と意図した範囲を確認してください。`latest` ではなくデプロイ対象のダイジェストを選択してください。新規 CVE、サポート対象イメージ、再スキャンの適格性、失敗の管理は継続して行ってください。初回スキャンを通過しても将来の安全性は保証されません。

### Inspector と CI/CD の統合

[完全なスキャンゲートとテスト](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security) には、正確なレジストリ / リポジトリ / ダイジェスト、完了タイムスタンプ、明示的な重要度カウントのマップが必要です。継続スキャンが `ACTIVE` であることだけでは、初回結果が利用可能であることの証明にはなりません。結果の欠落、タイムアウト、アクセス拒否、失敗、不明なステータスが、検出ゼロになることは決してありません。

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` は、ビルド / プッシュ後にレジストリで確認された `sha256:...` の値でなければなりません。例のアカウント / リポジトリを置き換え、boto3 をインストールしてください。12 件のリグレッションテストは実際の boto3 / botocore Stubber と擬似時間を使用し、AWS へのリクエストや実際の待機は発生しません。

GitHub Actions との統合には、承認済みの OIDC 信頼ロール ARN、`permissions: id-token: write`、最小権限の読み取り、ECR ログイン出力から得たレジストリ、ビルド済みダイジェストの受け渡しが必要です。未定義の `$ECR_REGISTRY`、ロールなしの認証情報設定、固定 60 秒の sleep は、完全なワークフローではありません。マルチアーキテクチャのインデックスについては、デプロイされる子ダイジェストに対するスキャンポリシーを定義してください。例外、有効期限 / 所有者、結果の鮮度要件は別途管理してください。

拡張スキャンの検出イベントは `aws.inspector2` / `Inspector2 Finding` を使用し、Basic な ECR イメージスキャンのイベントとは異なります。[検証済みのアラート用 CloudFormation の例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) には、キー、権限、受信側に関する別途の前提条件があります。

---

## CIS Kubernetes Benchmark

### kube-bench の実行

レビュー対象のアップストリームリリースは kube-bench **0.16.0** です。`eks-1.5.0`、`eks-1.7.0`、`eks-1.8.0` を含みますが、旧来の例にあった `eks-1.4.0` ディレクトリは含まれません。組織が要求する CIS EKS のエディションと、互換性のあるクラスター / ノード OS / ツールのサポート状況に基づいて選択してください。最も大きい番号が自動的に正しい選択になるわけではありません。アップストリームのサンプル Job 自体は依然として `latest` と 1.5.0 を使用しているため、そのまま適用せず、イメージのダイジェスト、プロファイル、ホストマウント、権限をレビューして固定してください。

一部のチェックはホストの PID / ファイルシステムへのアクセスを必要とし、Restricted なアプリケーション namespace とは競合します。承認されたスキャナーの運用経路を用い、検査したノード、除外項目、警告を記録してください。この監査では実ノード上での kube-bench の実行は行っていません。

### CIS Benchmark の主要セクション

選択した CIS EKS プロファイルにおける実際の controlplane、node、policies、managedservices のチェック項目を確認してください。マネージドコントロールプレーンのファイルに顧客がアクセスできると想定しないでください。ノード設定、RBAC、ネットワークポリシー、監査のチェックには、自動 / 手動 / 該当なしの分類が必要になる場合があります。ツールの合格率は、セキュリティ認証でも網羅的な侵害評価でもありません。

### コンプライアンスチェックの自動化

1 つの Job は、それがスケジュールされたノードのみを検査する場合があります。ノードグループ、OS、アーキテクチャ、設定の差異を考慮してカバレッジを設計し、結果にクラスター / ノード / イメージ / プロファイル / 時刻のラベルを付けてください。定期実行にはホストマウント、ServiceAccount、必要な読み取り権限、同時実行制御、完了 / 失敗の処理、結果の保持が必要です。

旧来の CronJob にはホストマウントがなく、kube-bench イメージに AWS CLI が含まれていることを前提としていました。結果をアップロードする必要がある場合は、制限されたワークロードアイデンティティを持つレビュー済みのアップローダーまたはログパイプラインを使用してください。アップロードの成功が、スキャンの失敗を隠してはなりません。

---

## Cluster Encryption

### EKS Secrets の暗号化 (KMS)

EKS **1.28 以降は、AWS 所有の KMS キーを使用してすべての Kubernetes API データをエンベロープ暗号化するのがデフォルト** です。特定の要件がある場合はカスタマー管理キーを選択してください。そうしたキーがないことは、現在の EKS Secrets が暗号化されずに保存されていることを意味しません。

カスタマー管理キーについては、クラスターロール / KMS の grant、キーポリシー、アカウント / リージョン、キーの可用性、変更手順をあわせてレビューしてください。キーの無効化 / 削除は可用性と復旧に影響し得ます。7 日間の削除待機期間を、普遍的な本番標準としてコピーしないでください。`Resource: "*"` はキーポリシー固有の意味を持ちますが、無制限の IAM アクセスとして転用してはなりません。実際のキーの所有者、管理 / 使用ロール、条件、IAM の委任を確認してください。

保存時の暗号化は、権限のある API 読み取りや、侵害されたアプリケーションによる値の利用を防ぎません。認証情報のローテーション、Secret の配布と再読み込みは、別の [secrets-management](./05-secrets-management.md) の運用です。この章では KMS キー / クラスターの作成や、既存キーの関連付けの変更は行っていません。

---

## Node Security

### Bottlerocket OS

Bottlerocket はコンテナホスト OS の選択肢であり、すべてのワークロードが安全になることを保証するものではありません。クラスターの Kubernetes バージョン、CPU アーキテクチャ、マネージドノードグループ / Auto Mode のモデル、CNI、ストレージ、エージェントのサポート組み合わせを確認してください。クラスター / API / CA の設定を無条件に上書きするのではなく、マネージドノードグループのブートストラップのマージ規則に従ってください。

更新 / 再起動 / 置き換え、control / admin コンテナへのアクセス、SSM 権限、イメージの出自、復旧を運用してください。旧来の例にあったネットワークバッファの sysctl 設定は、セキュリティ強化の根拠ではありませんでした。AMI タイプとインスタンスアーキテクチャは整合している必要があります。この監査ではノードグループや OS の実行は行っていません。

### ノードのセキュリティ強化

制限されたノードロールと、ワークロード固有の IRSA / Pod Identity ロールを分離してください。hostNetwork、特権 Pod、ノードの侵害を含めて、IMDSv2 とメタデータアクセス制御を評価してください。IRSA を有効にしただけで、ノードロールへのアクセスが自動的にブロックされるわけではありません。

適切な非 root のアイデンティティ、特権昇格の禁止、capability の削除、seccomp、明示的な書き込み可能ボリュームを伴う読み取り専用ルートファイルシステムを使用し、実際のアプリケーションでテストしてください。ラベル / セレクター / toleration はスケジューリングの入力であり、OS のアテステーションや認可ではありません。`node.kubernetes.io/os: bottlerocket` のようなユーザー設定のラベルを信頼境界として扱わないでください。セキュリティ上の配置には、管理者が制御するラベルと NodeRestriction のような実際の保護をレビューしてください。

---

## Private Clusters

### 完全プライベートな EKS 構成

プライベートな Kubernetes API には、VPC または接続された管理ネットワークからの DNS、ルート、セキュリティグループに加えて、IAM 認証と Kubernetes 認可が必要です。インターネットから到達できないことは、接続されたすべてのユーザーを認可するものではありません。

API の公開設定を変更する前に、現在のオペレーター、CI、復旧経路からのプライベートアクセスをテストしてください。`endpoint_private_access` / `endpoint_public_access` は、誤って新しいクラスターを宣言するのではなく、既存の IaC オーナーを通じて管理してください。ワーカーのブートストラップと、必要な AWS API / イメージ / パッケージへのアクセスは別途設計してください。インターネットなしでの運用と、プライベートな API 公開は別の要件です。

### Bastion または VPN によるアクセス

VPN、Direct Connect、適切に接続されたネットワーク、または制限された管理ホストを使用してください。Client VPN のサブネット関連付けだけでは不十分です。サーバー / クライアント認証、重複しないクライアント CIDR、認可ルール、ルート / 戻りルート、DNS、セキュリティグループ、接続ログ、IAM / Kubernetes の権限をあわせて設定してください。

bastion にはそれ自体のアクセス、パッチ適用、監査の責任が伴います。広範な SSH ingress や無制限のクラスター管理をデフォルトにしないでください。この章では VPN、bastion、証明書のデプロイは行っていません。

---

## Multi-tenancy Patterns

### Namespace ベースのマルチテナンシー

Namespace は共有クラスター内の管理スコープであり、相互に敵対するテナント間の完全な境界ではありません。PSS、RBAC、クォータ、NetworkPolicy、ストレージ、ワークロードアイデンティティ、ノード / 管理者の境界を組み合わせてください。この例は Kubernetes 1.35 のポリシーベースラインを使用しています。実際のクラスターとの互換性を確認してください。

同一 namespace のピアは許可され、DNS は 1 つのピアの中で kube-system namespace **と** kube-dns の Pod セレクターを使用します。UDP と TCP の 53 番の両方が含まれます。実際の DNS ラベル、NodeLocal DNS、CNI の強制、追加される他のポリシー、hostNetwork / ノードのトラフィックは別途確認してください。実際の接続性テストは実施していません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-a-limits
  namespace: tenant-a
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      min:
        cpu: 50m
        memory: 64Mi
      max:
        cpu: "2"
        memory: 4Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-a-isolation
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: {}
  egress:
    - to:
        - podSelector: {}
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
# Workload administration is sensitive, even when namespace-scoped.
# The group cannot change Namespace labels, RoleBindings or this NetworkPolicy.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workload-admin
  namespace: tenant-a
rules:
  - apiGroups: [""]
    resources: [pods, services, configmaps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [apps]
    resources: [deployments, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-workload-admins
  namespace: tenant-a
subjects:
  - kind: Group
    name: tenant-a-workload-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-admin
  apiGroup: rbac.authorization.k8s.io
```

### RBAC によるマルチテナンシー

例のワークロード管理者は、Namespace のラベル、RoleBinding、NetworkPolicy、Secret API の権限を直接変更できません。ただし、Pod / Deployment を作成することで namespace の Secret、ServiceAccount、ボリュームを間接的に利用できます。Secret の get を除外しても、シークレットにアクセスできないことの証明にはなりません。より強い分離が必要な場合は、クラスターやアカウントの分離を検討してください。

EKS のユーザーアクセスについては、namespace スコープのアクセスポリシーや Kubernetes のグループ / RBAC を用いた現行のアクセスエントリを評価してください。aws-auth ConfigMap はレガシーな互換経路であり、唯一の統合方式ではありません。認証モードの変更には不可逆な移行上の制約があるため、移行前に管理者 / ノードのマッピングと復旧経路を検証してください。EKS のアクセスポリシーと Kubernetes RBAC はそれぞれ独立にアクセスを許可できるため、一方に権限がないことがもう一方の許可を否定するわけではありません。一般の開発者に system:masters を既定の例として付与しないでください。

---

## まとめ

EKS セキュリティの主要なベストプラクティス:

1. **IAM 統合**: IRSA または Pod Identity で AWS サービスにアクセスする
2. **ネットワークセキュリティ**: Security Groups for Pods、VPC エンドポイント
3. **ロギングとモニタリング**: コントロールプレーンログ、GuardDuty
4. **イメージセキュリティ**: Amazon Inspector、ECR スキャン
5. **コンプライアンス**: CIS Benchmark、kube-bench
6. **暗号化**: KMS による Secrets の暗号化
7. **ノードセキュリティ**: Bottlerocket OS、最小権限
8. **マルチテナンシー**: Namespace 分離、RBAC、ResourceQuota

---

## 参考資料

- [EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

- [security-groups-for-pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [sgpp](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [private-clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [configure-sts-endpoint](https://docs.aws.amazon.com/eks/latest/userguide/configure-sts-endpoint.html)
- [how-runtime-monitoring-works-eks](https://docs.aws.amazon.com/guardduty/latest/ug/how-runtime-monitoring-works-eks.html)
- [kubernetes-protection](https://docs.aws.amazon.com/guardduty/latest/ug/kubernetes-protection.html)
- [API_DescribeImageScanFindings](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_DescribeImageScanFindings.html)
- [image-scanning-enhanced](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-enhanced.html)
- [eventbridge-integration](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [access-entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [guardduty_finding-types-kubernetes](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-kubernetes.html)
- [findings-runtime-monitoring](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [API_UpdateDetector](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_UpdateDetector.html)
- [guardduty_findings_eventbridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
