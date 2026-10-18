# EKS セキュリティのベストプラクティス

> **レビュー基準**: 現行の AWS ドキュメント、Kubernetes 1.35 API スキーマ、Terraform 1.15.7 / AWS provider 6.64.0。ライブクラスターへのデプロイは実施していません。
> **最終更新**: October 15, 2026

このドキュメントでは、Amazon EKS 環境向けのセキュリティベストプラクティスを扱います。IAM 統合からネットワークセキュリティ、ランタイム保護まで、EKS クラスターを安全に運用する方法を学びます。

## 目次

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Pod の Security Groups](#security-groups-for-pods)
4. [VPC エンドポイント](#vpc-endpoints)
5. [コントロールプレーンのログ記録](#control-plane-logging)
6. [GuardDuty EKS 保護](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [クラスター暗号化](#cluster-encryption)
10. [ノードセキュリティ](#node-security)
11. [プライベートクラスター](#private-clusters)
12. [マルチテナンシーのパターン](#multi-tenancy-patterns)
13. [境界セキュリティと検査パス](#perimeter-security-and-inspection-paths)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA の概要

IRSA (IAM Roles for Service Accounts) は IAM ロールを Kubernetes ServiceAccount に関連付け、Pod が AWS サービスへ安全にアクセスできるようにします。

Kubernetes API サーバーがプロジェクテッド ServiceAccount トークンを発行します。SDK はそれを STS AssumeRoleWithWebIdentity と交換します。STS は IAM OIDC provider およびロールの信頼条件に関連付けられた issuer/JWKS を検証してから、一時的な認証情報を返します。IAM OIDC provider オブジェクトは、実行中のトークン発行プロキシではありません。


### IRSA のセットアップ

次のオペレーター例は実行されていません。実際の Region、クラスター、バケット所有者/パス、ポリシー ARN に合わせ、アプリケーションイメージはレビュー済みのバージョン/ダイジェストに置き換えてください。別の Region の OIDC issuer や、推測した eksctl 生成ロール ARN を混在させないでください。



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

### IRSA の使用

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

### IRSA 信頼ポリシー

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

EKS Pod Identity は代替の認証情報配信メカニズムです。実際のプラットフォーム/SDK サポート、信頼境界、運用要件に基づいて IRSA と使い分けてください。IRSA を廃止するものでも、すべてのワークロードを自動的により安全にするものでもありません。

サポート対象の Pod SDK はローカルエージェントパスを使用します。エージェントは、association とロールに従い EKS Auth を介して一時的な認証情報を取得します。クロスアカウントロールまたはロールチェーンについては、現在サポートされているメカニズム、信頼、セッションタグ条件を個別に確認してください。


### Pod Identity のセットアップ

EKS Auto Mode にはエージェントが含まれます。その他のサポート対象プラットフォームでは、現在互換性のある addon バージョンを選択し、既存の所有者を通じて管理してください。下記のアカウント/クラスター/namespace/ServiceAccount 値を置き換え、意図した namespace/ServiceAccount のセッションタグ条件でロール信頼を制限してください。addon と association をインストールしても、SDK の互換性、認証情報の優先順位、ネットワークアクセスは検証されません。



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

### Pod Identity の使用

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

| 機能 | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **セットアップの複雑さ** | OIDC Provider が必要 | 簡単（API 呼び出し） |
| **信頼ポリシー** | 正確な OIDC issuer、audience、subject | サービスプリンシパルと制限付き条件 |
| **ロールの再利用** | クラスターごとの変更が必要 | クラスター間で再利用 |
| **監査ログ** | CloudTrail（SA レベル） | CloudTrail（Pod レベル） |
| **セッションタグ** | EKS Pod Identity と同じセッションタグの動作を前提にしない | ドキュメント化されたセッションタグをサポート。無効化/チェーンの動作をレビューする |
| **選択** | サポート対象プラットフォーム、OIDC 信頼、運用モデル | サポート対象プラットフォーム、association、エージェント/SDK モデル |

---

## Pod の Security Groups {#security-groups-for-pods}

### 概要

Pod の Security Groups は、VPC Security Groups を Pod に直接適用し、ネットワークレベルの分離を提供します。

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

Pod の Security Groups には、サポート対象のトランキング対応インスタンスと CNI モードが必要です。現在のドキュメントでは Windows と EKS Auto Mode は対象外であり、すべての Nitro インスタンスがサポートされるわけではありません。VPC Resource Controller ポリシーはクラスターのロールに属します。複数のアタッチ済みセキュリティグループでは許可ルールが結合され、交差するわけではありません。有効化する前に strict/standard モード、DNS、プローブ、ロードバランサーの動作を確認してください。

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

### Terraform による Security Group の設定

実際のソースセキュリティグループと、必要なデータベース、レプリケーション、モニタリングのポートを特定し、アタッチ済み SG ルールが結合されることを忘れないでください。SecurityGroupPolicy、ソース/ターゲット SG、VPC、Pod セレクターは一致していなければなりません。古い宣言には未定義の module/SG 参照と無制限の egress が含まれており、完全なデプロイモジュールではありませんでした。

Security group の戻りトラフィックはステートフルですが、アプリケーションが新たに開始する DNS/データベース/外部接続には個別の egress 要件があります。宛先を制限し、CNI の強制モードおよび NetworkPolicy で接続性をテストしてください。この監査では、security groups/Pod ENI の作成やネットワーク分離テストの実行は行っていません。

---

## VPC エンドポイント {#vpc-endpoints}

### プライベート EKS 向け VPC エンドポイント

Kubernetes のプライベート API エンドポイントと AWS サービスの PrivateLink エンドポイントは異なります。`eks` VPC エンドポイントは kubectl が使用する Kubernetes API 接続の代わりにはなりません。実際のノード、ワークロード、オペレーターパスで必要なサービスだけを選択し、Region のサポート、DNS、security groups、ルート、エンドポイントポリシー、IAM をまとめて検証してください。

| 目的 | パス |
|---|---|
| Kubernetes API | クラスターのプライベート API エンドポイントと接続済みネットワーク |
| EKS 管理 API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA STS 交換 | `com.amazonaws.<region>.sts`。SDK でリージョナル STS を設定する |
| OIDC 検出/JWKS | 現在ドキュメント化されている `com.amazonaws.<region>.oidc-eks`。STS とは別 |
| ECR イメージ | `ecr.api`、`ecr.dkr` インターフェイスと S3 イメージレイヤーパス |
| 追加サービス | 実際に使用する EC2、Logs、ELB、Auto Scaling、SSM、その他の API の検証済みエンドポイント |

現在の EKS プライベートクラスターのドキュメントには、Route 53 API サービス `com.amazonaws.route53` も記載されています。DNS 解決と Route 53 管理 API 呼び出しを区別し、サービス/Region のサポートを確認してください。すべての Region で旧式の `ec2messages` エンドポイントを無条件に作成せず、SSM Agent とメッセージングの要件を確認してください。

### Terraform VPC エンドポイントのセットアップ

[完全な Terraform の例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints)では、`論理名 → 正確なサービス名` のマップを使用します。古い `split(...)[4]` は範囲外になるか、サービス名の長さによって誤ったタグを生成する可能性がありました。現在、タグには `each.key` を使用します。

既存のサブネット、ルートテーブル、承認済みクライアント security groups、レビュー済みの S3 エンドポイントポリシーを指定してください。HTTPS は、名前付きクライアントグループからのみ許可されます。S3 ポリシーは ECR レイヤーバケットおよびその他の必要なバケットをカバーする必要があります。エンドポイントポリシー自体は IAM アクセスを付与しません。Terraform 1.15.7/AWS provider 6.64.0 のスキーマ検証は合格しましたが、plan/apply やリソース作成は実行していません。

---

## コントロールプレーンのログ記録 {#control-plane-logging}

### EKS コントロールプレーンログの種類

サポートされている種類は `api`、`audit`、`authenticator`、`controllerManager`、`scheduler` です。Kubelet/container ログには個別の収集パスがあります。ロググループは `/aws/eks/<cluster-name>/cluster` です。運用ポリシーに従って Region、保持期間、アクセス、暗号化、機密データの取り扱い、収集コストを設定してください。

### ログ記録の有効化

既存クラスターの IaC 所有者と変更を調整してください。次の例は所有するクラスターを対象としており、この監査中には実行されていません。更新は非同期です。返された更新 ID を `describe-update` で確認してから、実際のログ到着を個別に検証してください。ログ記録の有効化では、新しいクラスターリソースの宣言や API エンドポイント公開範囲の変更は必要ありません。

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights クエリ

これらは**個別の Logs Insights QL クエリ**です。選択したロググループで実際のフィールド/時間範囲を調べてください。最初のクエリは探索的なテキスト一致であり、完全な認証失敗検出器ではありません。この監査中にマネージドクエリエンジンは実行していません。

Authenticator エラー（探索的）

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

選択した ID による呼び出し

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

認可拒否

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Secret API アクセス

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS 保護 {#guardduty-eks-protection}

### GuardDuty EKS 保護の概要

EKS 監査ログ分析、Runtime Monitoring、基盤となる GuardDuty データソースを分けて考えてください。EKS 監査分析は Kubernetes API アクティビティに関するものであり、ユーザーの CloudWatch コントロールプレーンログエクスポートの有効化には依存しません。Runtime Monitoring にはセキュリティエージェントと実際のカバレッジが必要です。

現在の Runtime Monitoring ドキュメントでは、EC2 ベースの EKS と EKS Auto Mode をサポートし、EKS Hybrid Nodes と EKS Fargate は対象外です。ECS Fargate のサポートは EKS Fargate のサポートではありません。organization/delegated-administrator の所有権、リージョナル detector、プラットフォーム、コスト、エージェント管理の所有者を確認してください。

### GuardDuty の有効化

以下は既存 detector 向けの**設定ペイロード例**であり、アカウントには適用されていません。`RUNTIME_MONITORING` には EKS が含まれるため、`EKS_RUNTIME_MONITORING` と同時に指定するのは無効です。常に detector を作成して最初に返された ID を選ぶのではなく、所有する detector を調べてください。自動化されたエージェント管理リソース/権限と、測定されたカバレッジをレビューしてください。

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

### GuardDuty EKS Finding の種類

実際の種類には tactic プレフィックスが含まれます。作り上げた固定の重要度テーブルではなく、Finding の `severity`、リソース、アカウント/Region、カバレッジ、公式の説明を使用してください。

| 実際の種類の例 | スコープ |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API アクティビティ |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | 異常な Kubernetes 権限チェック |
| `Execution:Runtime/ReverseShell` | エージェントが観測したランタイムの動作 |
| `CryptoCurrency:Runtime/BitcoinTool.B` | ランタイムのマイニング関連検出 |

### Finding 応答の自動化

この EventBridge パターンは Kubernetes/Runtime の種類をルーティングします。古い `prefix: Kubernetes` および `prefix: Runtime` は実際の tactic プレフィックス付き名前と一致しませんでした。公式 AWS Event Ruler 2.2.0 ライブラリを使い、6 件の一致/不一致ケースと古い失敗を確認しました。

このパターンには通知/隔離ターゲットがありません。Runtime Finding は EKS を超えるリソースに関係する可能性があります。承認済みの応答へルーティングする前に、実際のリソースメタデータを調べてください。ターゲットのロール/権限、リトライ、DLQ、重複排除は個別に設定してください。`boto3.client("eks")` を作成しても Pod は隔離されません。封じ込めには、設計された CNI/ホスト/クラウドコントロールと、認可された Kubernetes 操作が必要です。

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

### Inspector コンテナイメージスキャン

ECR 拡張スキャンは Amazon Inspector と統合され、サポート対象イメージのパッケージ脆弱性を検査します。実行中イメージの使用コンテキストは、ランタイム動作の検出とは異なります。同じイメージスキャンでは、任意の Kubernetes manifest、IAM ポリシー、ライブネットワークトラフィックは検査されません。

レジストリスキャンの変更はアカウント/Region とリポジトリフィルターのスコープに影響します。所有権と意図したスコープを確認してください。`latest` ではなく、デプロイするダイジェストを選択してください。新しい CVE、サポート対象イメージ、再スキャン適格性、失敗を継続して管理してください。初回スキャンに合格しても、将来の安全性は保証されません。

### Inspector と CI/CD の統合

[完全なスキャンゲートとテスト](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security)には、正確なレジストリ/リポジトリ/ダイジェスト、完了タイムスタンプ、明示的な重要度カウントマップが必要です。継続スキャンの `ACTIVE` だけでは、初回結果の準備完了を証明しません。結果の欠落、タイムアウト、アクセス拒否、失敗、不明なステータスは、決して検出結果ゼロにはなりません。

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` は、build/push 後のレジストリ確認済み `sha256:...` 値でなければなりません。例のアカウント/リポジトリを置き換え、boto3 をインストールしてください。12 件の回帰テストでは、AWS リクエストや実際の待機を行わず、本物の boto3/botocore Stubber と偽の時刻を使用します。

GitHub Actions 統合には、承認済みの OIDC 信頼ロール ARN、`permissions: id-token: write`、最小権限の読み取り、ECR ログイン出力のレジストリ、build したダイジェストの伝播が必要です。未定義の `$ECR_REGISTRY`、ロールなしの認証情報設定、固定の 60 秒スリープは完全なワークフローではありません。マルチアーキテクチャインデックスでは、デプロイされた子ダイジェストのスキャンポリシーを定義してください。例外、有効期限/所有権、結果鮮度の要件は個別に管理してください。

拡張 Finding イベントは `aws.inspector2` / `Inspector2 Finding` を使用し、Basic ECR イメージスキャンイベントとは異なります。[検証済みのアラート CloudFormation 例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)には、個別のキー、権限、受信者の前提条件があります。

---

## CIS Kubernetes Benchmark

### kube-bench の実行

レビュー済みのアップストリームリリースは kube-bench **0.16.0** です。これには `eks-1.5.0`、`eks-1.7.0`、`eks-1.8.0` が含まれますが、古い例の `eks-1.4.0` ディレクトリは含まれません。組織で必要とされ、クラスター/ノード OS/ツールのサポートと互換性がある CIS EKS エディションを選んでください。最も大きい番号が自動的に正しい選択になるわけではありません。アップストリームのサンプル Job 自体は依然として `latest` と 1.5.0 を使用しているため、盲目的に適用せず、イメージダイジェスト、プロファイル、ホストマウント、権限をレビューして固定してください。

一部のチェックにはホスト PID/ファイルシステムアクセスが必要で、Restricted アプリケーション namespace と競合します。承認されたスキャナーの運用パスを使用し、検査済みノード、除外、警告を記録してください。この監査では実際のノードで kube-bench を実行していません。

### CIS Benchmark の主要セクション

選択した CIS EKS プロファイルで、実際の controlplane、node、policies、managedservices チェックを調べてください。マネージドコントロールプレーンファイルへの顧客アクセスを前提にしないでください。ノード設定、RBAC、network policy、監査チェックには、自動/手動/該当なしの分類が必要になる場合があります。ツールの合格率は、セキュリティ認定や網羅的な侵害評価ではありません。

### 自動コンプライアンスチェック

1 つの Job で検査できるのは、スケジュールされたノードだけです。ノードグループ、OS、アーキテクチャ、設定の差異をカバーするよう設計し、結果にはクラスター/ノード/イメージ/プロファイル/時刻のラベルを付けてください。スケジュール実行には、ホストマウント、ServiceAccount、必要な読み取り権限、同時実行制御、完了/失敗処理、結果保持が必要です。

古い CronJob にはホストマウントがなく、kube-bench イメージに AWS CLI が含まれると仮定していました。結果をアップロードする必要がある場合は、制約されたワークロード ID を持つレビュー済みアップローダーまたはログパイプラインを使用してください。アップロードの成功によってスキャン失敗が隠されてはなりません。

---

## クラスター暗号化 {#cluster-encryption}

### EKS Secrets 暗号化 (KMS)

EKS **1.28+ では、AWS 所有の KMS キーを使用したすべての Kubernetes API データのエンベロープ暗号化がデフォルトです**。特定の要件には customer-managed key を選択してください。このようなキーがないことは、現在の EKS Secrets が暗号化されずに保存されていることを意味しません。

customer-managed key では、クラスターのロール/KMS grants、キーポリシー、アカウント/Region、キーの可用性、変更手順をまとめてレビューしてください。キーの無効化/削除は可用性と復旧に影響する可能性があります。7 日間の削除ウィンドウを汎用的な本番標準としてコピーしないでください。`Resource: "*"` にはキーポリシー固有の意味がありますが、無制限の IAM アクセスとして再利用してはなりません。実際のキー所有者、管理/使用ロール、条件、IAM 委任を検証してください。

保存時暗号化では、認可された API 読み取りや侵害されたアプリケーションによる値の使用を阻止できません。認証情報のローテーション、Secret 配信、リロードは、個別の [secrets-management](./05-secrets-management.md) 操作です。この章では KMS キー/クラスターの作成や既存キーの関連付け変更は行っていません。

---

## ノードセキュリティ {#node-security}

### Bottlerocket OS

Bottlerocket はコンテナホスト OS の選択肢であり、すべてのワークロードが安全であることを保証するものではありません。クラスター Kubernetes バージョン、CPU アーキテクチャ、managed-node-group/Auto Mode モデル、CNI、ストレージ、エージェントのサポート対象の組み合わせを確認してください。クラスター/API/CA 設定を盲目的に上書きせず、managed-node-group の bootstrap マージルールに従ってください。

更新/再起動/置換、control/admin-container アクセス、SSM 権限、イメージ来歴、復旧を運用してください。古い例のネットワークバッファ sysctl は、セキュリティ強化の根拠ではありませんでした。AMI タイプとインスタンスアーキテクチャは一致していなければなりません。この監査では node group または OS は実行していません。

### ノードセキュリティの強化

制限されたノードロールを、ワークロード固有の IRSA/Pod Identity ロールから分離してください。hostNetwork、特権 Pod、ノード侵害を含む IMDSv2 とメタデータアクセス制御を評価してください。IRSA を有効にするだけでは、ノードロールへのアクセスは自動的にブロックされません。

適切な非 root ID、権限昇格なし、capability の削除、seccomp、明示的な書き込み可能ボリュームを備えた読み取り専用 root ファイルシステムを使用し、実際のアプリケーションをテストしてください。ラベル/selector/toleration はスケジューリング入力であり、OS の証明や認可ではありません。`node.kubernetes.io/os: bottlerocket` のようなユーザー設定ラベルを信頼境界として扱わないでください。セキュリティ配置のため、管理者制御ラベルと NodeRestriction などの実際の保護をレビューしてください。

---

## プライベートクラスター {#private-clusters}

### 完全にプライベートな EKS 設定

プライベート Kubernetes API には、VPC または接続済み管理ネットワークからの DNS、ルート、security groups に加え、IAM 認証と Kubernetes 認可が必要です。パブリックインターネットから到達できないことは、接続されたすべてのユーザーを認可することではありません。

API 公開範囲を変更する前に、現在のオペレーター、CI、復旧パスからのプライベートアクセスをテストしてください。不注意に新しいクラスターを宣言するのではなく、既存 IaC の所有者を通じて `endpoint_private_access`/`endpoint_public_access` を管理してください。worker bootstrap と必要な AWS API/イメージ/パッケージアクセスは個別に設計してください。インターネットなしの運用とプライベート API 公開は別の要件です。

### Bastion または VPN アクセス

VPN、Direct Connect、適切に接続されたネットワーク、または制限付き管理ホストを使用してください。Client VPN のサブネット関連付けだけでは不十分です。サーバー/クライアント認証、重複しないクライアント CIDR、認可ルール、ルート/戻りルート、DNS、security groups、接続ログ、IAM/Kubernetes 権限をまとめて設定してください。

bastion には、独自のアクセス、パッチ、監査の責任が追加されます。広範な SSH ingress や無制限のクラスター管理をデフォルトにしないでください。この章では VPN、bastion、証明書をデプロイしていません。

---

## マルチテナンシーのパターン {#multi-tenancy-patterns}

### Namespace ベースのマルチテナンシー

Namespace は共有クラスターにおける管理スコープであり、相互に敵対的なテナント間の完全な境界ではありません。PSS、RBAC、quota、NetworkPolicy、ストレージ、ワークロード ID、ノード/管理者境界を組み合わせてください。この例では Kubernetes 1.35 のポリシーベースラインを使用しています。実際のクラスターとの互換性を確認してください。

同一 namespace のピアは許可されます。一方、DNS では 1 つのピア内で kube-system namespace **と** kube-dns Pod selector を使用します。UDP と TCP 53 の両方が含まれます。実際の DNS ラベル、NodeLocal DNS、CNI の強制、その他の加算的ポリシー、hostNetwork/ノードトラフィックを個別に確認してください。ライブ接続テストは実施していません。

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

### RBAC マルチテナンシー

この例のワークロード管理者は、Namespace ラベル、RoleBindings、NetworkPolicy、Secret API 権限を直接変更できません。しかし、Pod/Deployment を作成すると、namespace の Secrets、ServiceAccounts、ボリュームを間接的に使用できます。Secret get を除外しても、secret へのアクセス不能を証明するものではありません。より強力な分離が必要な場合は、別のクラスター/アカウントを検討してください。

EKS のユーザーアクセスでは、namespace スコープの access policies を持つ現在の access entries、または Kubernetes groups/RBAC を評価してください。aws-auth ConfigMap はレガシーな互換性パスであり、唯一の統合メカニズムではありません。authentication-mode の変更には元に戻せない移行制約があります。移行前に管理者/ノードマッピングと復旧パスを検証してください。EKS access policies と Kubernetes RBAC はそれぞれ独立してアクセスを許可できます。そのため、一方で権限がなくても他方からの許可は拒否されません。通常の開発者に system:masters をデフォルト例として付与しないでください。

---

## 境界セキュリティと検査パス {#perimeter-security-and-inspection-paths}

IAM と Pod ポリシーに加えて、パブリックアプリケーション、admission webhooks、管理者アクセス、アウトバウンドトラフィック、VPC 間パスを個別に検証してください。外部 WAF は内部 webhook を自動的に保護するわけではありません。中央 TGW 検査は、実際にそれを経由してルーティングされるトラフィックを対象とします。既存の IAM、CNI、ランタイムコントロールを以下のガイドに接続してください。

| 保護領域 | 詳細ガイド |
|---|---|
| インシデント、検出、パッチ適用後の復旧 | [多層防御とインシデント対応](./13-defense-in-depth-incident-response.md) |
| HTTP(S)、API、オリジンバイパス | [WAF、エッジ、API セキュリティ](./14-waf-edge-api-security.md) |
| 管理、TLS 可視性、アプライアンスの選択 | [Palo Alto と Fortinet NGFW](./15-ngfw-paloalto-fortinet.md) |
| 対称ルーティング、NAT、AZ、障害 | [GWLB と GENEVE](./16-gwlb-geneve-inspection.md) |

これらのガイドには、一次情報源、検査の限界、承認済み環境での検証計画が含まれます。実際のアプライアンスデプロイやパフォーマンス結果は含まれません。

---

## まとめ

EKS セキュリティの主なベストプラクティス:

1. **IAM 統合**: IRSA または Pod Identity で AWS サービスへアクセスする
2. **ネットワークセキュリティ**: Pod の Security Groups、VPC エンドポイント
3. **ログ記録とモニタリング**: コントロールプレーンログ、GuardDuty
4. **イメージセキュリティ**: Amazon Inspector、ECR スキャン
5. **コンプライアンス**: CIS Benchmark、kube-bench
6. **暗号化**: KMS による Secrets 暗号化
7. **ノードセキュリティ**: Bottlerocket OS、最小権限
8. **マルチテナンシー**: Namespace 分離、RBAC、ResourceQuota

---

## 参考資料

- [EKS セキュリティのベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Amazon EKS ユーザーガイド - セキュリティ](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS セキュリティブログ - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
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