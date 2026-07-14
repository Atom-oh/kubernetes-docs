# VPC Lattice クイズ

このクイズでは、Amazon VPC Lattice の理解度を確認します。

## 選択式問題

1. Amazon VPC Lattice の主な目的は何ですか？
   - A) インターネットから AWS リソースへの外部トラフィックを管理すること
   - B) 異なる VPC とアカウント間における Service の内部通信
   - C) AWS リージョン間のデータレプリケーション
   - D) DNS ベースのグローバルロードバランシング

<details>

<summary>回答を表示</summary>

**回答: B) 異なる VPC とアカウント間における Service の内部通信**

**解説:**
VPC Lattice は、複数の VPC および AWS アカウントにまたがる Service を安全に接続・管理することを主な目的とする AWS アプリケーションネットワーキングサービスです。Service Network と呼ばれる論理的な境界内で、Service discovery、トラフィックルーティング、認証、認可を提供します。外部トラフィックの管理には API Gateway または ALB を使用し、リージョン間レプリケーションには S3 Cross-Region Replication などの Service を使用します。
</details>

2. VPC Lattice の Service Network について正しいものはどれですか？
   - A) 物理ネットワーク機器を接続するレイヤー
   - B) Service をグループ化し、その通信を管理する論理的な境界
   - C) VPC 内の subnet を接続するルーティングテーブル
   - D) Internet Gateway の代替 Service

<details>

<summary>回答を表示</summary>

**回答: B) Service をグループ化し、その通信を管理する論理的な境界**

**解説:**
Service Network は、複数の Service を論理的にグループ化する VPC Lattice の中核コンポーネントです。VPC を Service Network に関連付けると、その VPC 内のリソースはネットワーク内の Service と通信できます。複数の VPC（異なるアカウントのものを含む）を 1 つの Service Network に接続でき、各 Service の認証ポリシーとアクセス制御を一元管理できます。
</details>

3. VPC Lattice と AWS App Mesh の違いは何ですか？
   - A) VPC Lattice には sidecar proxy が必要だが、App Mesh には必要ない
   - B) App Mesh は sidecar proxy ベースだが、VPC Lattice には sidecar が不要
   - C) VPC Lattice は TCP のみをサポートし、App Mesh は HTTP のみをサポートする
   - D) 両 Service は同じアーキテクチャを使用する

<details>

<summary>回答を表示</summary>

**回答: B) App Mesh は sidecar proxy ベースだが、VPC Lattice には sidecar が不要**

**解説:**
AWS App Mesh は、トラフィックを制御するために各 Service pod に Envoy sidecar proxy を注入する Service mesh です。一方、VPC Lattice は、sidecar proxy なしで Service 間通信、ルーティング、認証を提供するフルマネージド AWS Service です。そのため、VPC Lattice は運用上の複雑さとリソースオーバーヘッドが低くなりますが、App Mesh が提供するきめ細かなトラフィック制御機能の一部は制限される場合があります。
</details>

4. EKS を VPC Lattice と統合する際に使用する Kubernetes API は何ですか？
   - A) Ingress API
   - B) Service API
   - C) Gateway API
   - D) NetworkPolicy API

<details>

<summary>回答を表示</summary>

**回答: C) Gateway API**

**解説:**
AWS Gateway API Controller は、Kubernetes Gateway API リソース（GatewayClass、Gateway、HTTPRoute など）を VPC Lattice リソースに変換します。Gateway API は Kubernetes の次世代 Ingress 仕様であり、Ingress よりも豊富な機能と拡張性を提供します。GatewayClass で amazon-vpc-lattice controller を指定し、Gateway と HTTPRoute を作成すると、controller が VPC Lattice Services と Target Groups を自動的に作成します。
</details>

5. VPC Lattice Service の正しい DNS 名形式はどれですか？
   - A) service-name.region.amazonaws.com
   - B) service-name.vpc-lattice-svcs.region.on.aws
   - C) service-name.internal.aws
   - D) service-name.lattice.region.aws

<details>

<summary>回答を表示</summary>

**回答: B) service-name.vpc-lattice-svcs.region.on.aws**

**解説:**
VPC Lattice Service には DNS 名が自動的に割り当てられます。形式は `<service-name>.<service-network-id>.vpc-lattice-svcs.<region>.on.aws` です。この DNS 名は Service Network に接続されているすべての VPC から解決できます。Client はこの DNS 名を使用して Service にアクセスし、VPC Lattice が内部で適切な target にルーティングします。カスタムドメインを使用するには、Route 53 などで CNAME または Alias レコードを設定できます。
</details>

6. VPC Lattice がサポートする認証方式は何ですか？
   - A) API Key のみ
   - B) OAuth 2.0 のみ
   - C) AWS IAM または認証なし
   - D) SAML のみ

<details>

<summary>回答を表示</summary>

**回答: C) AWS IAM または認証なし**

**解説:**
VPC Lattice は 2 つの認証モードをサポートします。AWS_IAM モードでは、リクエストに SigV4（Signature Version 4）署名が必要で、IAM ポリシーとリソースポリシーを通じてアクセスを制御します。NONE モードでは、認証なしですべてのリクエストが許可されます。IAM 認証を使用すると、どの IAM role/user がどの Service のどの path にアクセスできるかをきめ細かく制御できます。
</details>

7. VPC Lattice Target Groups でサポートされていない target type はどれですか？
   - A) EC2 instance
   - B) EKS pod（IP type）
   - C) Lambda function
   - D) RDS database

<details>

<summary>回答を表示</summary>

**回答: D) RDS database**

**解説:**
VPC Lattice Target Groups は、EC2 instance、IP address（EKS pod を含む）、Lambda function、ALB を target としてサポートします。RDS database は HTTP/HTTPS ではなくデータベースプロトコルを使用するため、VPC Lattice の target にはできません。EKS pod には IP type の Target Groups を使用し、AWS Gateway API Controller が pod IP を自動的に登録・登録解除します。
</details>

8. VPC Lattice における weighted routing の主なユースケースは何ですか？
   - A) ロードバランシングのみ
   - B) Canary deployment と blue-green deployment
   - C) 地理的なルーティング
   - D) Sticky session

<details>

<summary>回答を表示</summary>

**回答: B) Canary deployment と blue-green deployment**

**解説:**
Weighted routing は、複数の Target Groups にトラフィックを比例配分します。Canary deployment では、検証のためにトラフィックの 10% を新しいバージョンに送信し、その後徐々に増加させます。Blue-green deployment では、blue から green へ 100% を一度に切り替えます。例: `service-v1: weight 90, service-v2: weight 10` を設定すると、トラフィックの 10% のみが v2 に送信されます。問題が見つかった場合は、weight を調整して rollback できます。
</details>

## 短答式問題

9. VPC Lattice Service Network をアカウント間で共有する方法を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
AWS Resource Access Manager（RAM）を使用して、Service Network を他の AWS アカウントまたは organization と共有します。

**解説:**
アカウント間共有の手順:
1. **所有アカウント**: RAM で Service Network の resource share を作成する
   ```bash
   aws ram create-resource-share \
     --name my-service-network-share \
     --resource-arns arn:aws:vpc-lattice:region:account:servicenetwork/sn-xxx \
     --principals 123456789012  # Target account ID
   ```
2. **対象アカウント**: RAM の招待を承諾する
3. **対象アカウント**: 自身の VPC を共有された Service Network に関連付ける
4. その後、対象アカウントの Service も Service Network に登録できる

Organizations を使用している場合は、organization 全体への自動共有も可能です。
</details>

10. VPC Lattice で Health Check の設定が重要である理由を説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Health Checks は、不健全な target をトラフィックルーティングから自動的に除外し、Service の可用性を確保します。

**解説:**
VPC Lattice Health Checks の動作:
1. **定期的なチェック**: 設定した間隔（例: 30 秒）で target の Health Check endpoint にリクエストを送信する
2. **threshold に基づく判定**: 連続した成功/失敗回数（healthyThresholdCount/unhealthyThresholdCount）によって状態を判定する
3. **自動的な除外/復旧**: 不健全な target をトラフィックから除外し、復旧すると自動的に復元する
4. **設定例**:
   ```yaml
   healthCheck:
     enabled: true
     protocol: HTTP
     path: /health
     healthCheckIntervalSeconds: 30
     healthyThresholdCount: 5
     unhealthyThresholdCount: 2
     matcher:
       httpCode: "200-299"
   ```
適切な Health Check の設定により、rolling update 中の downtime を防ぎ、障害が発生した target へのリクエストを防止して user experience を保護します。
</details>

11. VPC Lattice と Transit Gateway の違いを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Transit Gateway はネットワークレイヤー（L3）で VPC 間の IP routing を提供する一方、VPC Lattice はアプリケーションレイヤー（L7）で Service ベースの通信を提供します。

**解説:**
主な違い:

| 観点 | Transit Gateway | VPC Lattice |
|--------|-----------------|-------------|
| 抽象化レベル | ネットワーク（IP ベース） | Service（名前ベース） |
| ルーティング | IP routing table | HTTP path/header ベース |
| プロトコル | すべての IP traffic | HTTP/HTTPS/gRPC |
| 認証 | Security Groups、NACLs | AWS IAM、resource policies |
| 可視性 | Network flow logs | アプリケーションレベルの metrics/logs |

Transit Gateway は VPC 間であらゆる IP 通信が必要な場合に使用し、VPC Lattice は microservices 間の HTTP ベース通信に適しています。両 Service は併用できます。
</details>

12. VPC Lattice における Auth Policy の役割と、適用できるレベルを説明してください。

<details>

<summary>回答を表示</summary>

**回答:**
Auth Policy は IAM ベースのアクセス制御を定義し、Service Network レベルと個々の Service レベルの両方に適用されます。

**解説:**
Auth Policy の適用レベル:
1. **Service Network レベル**: ネットワーク全体に適用されるデフォルトポリシー
   - どの IAM principal がネットワークに接続できるかを制御する
2. **Service レベル**: 個々の Service に適用される詳細なポリシー
   - 特定の Service のどの path にどの principal がアクセスできるかを制御する

ポリシー例:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
    },
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "vpc-lattice-svcs:RequestPath": "/api/*"
      }
    }
  }]
}
```
このポリシーは、MyAppRole が /api/* path にのみアクセスできるよう制限します。
</details>

## ハンズオン問題

13. EKS に AWS Gateway API Controller をインストールするための IAM policy と IRSA 設定を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```bash
# 1. Create IAM policy for VPC Lattice permissions
cat <<EOF > vpc-lattice-controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:*",
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document file://vpc-lattice-controller-policy.json

# 2. Create service account using IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=aws-application-networking-system \
  --name=gateway-api-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/VPCLatticeControllerPolicy \
  --override-existing-serviceaccounts \
  --approve

# 3. Install AWS Gateway API Controller
kubectl apply -f https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/deploy-v1.0.yaml
```

**解説:**
AWS Gateway API Controller は Kubernetes cluster 内の Gateway API リソースを監視し、VPC Lattice リソースを作成・管理します。IRSA（IAM Roles for Service Accounts）を通じて、controller pod は必要な AWS API を呼び出す権限を取得します。policy には vpc-lattice 操作、VPC/subnet の検索、および log delivery の権限が含まれます。
</details>

14. VPC Lattice を使用して 2 つの Service 間の weighted routing（90:10）を設定する HTTPRoute を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
# GatewayClass definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Gateway definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
# Weighted routing HTTPRoute
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: weighted-routing
  namespace: default
spec:
  parentRefs:
  - name: my-gateway
    sectionName: http
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 80
      weight: 90
    - name: service-canary
      port: 80
      weight: 10
---
# Stable service
apiVersion: v1
kind: Service
metadata:
  name: service-stable
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 80
    targetPort: 8080
---
# Canary service
apiVersion: v1
kind: Service
metadata:
  name: service-canary
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 80
    targetPort: 8080
```

**解説:**
この設定では、`/api` path へのトラフィックの 90% が service-stable に、10% が service-canary にルーティングされます。AWS Gateway API Controller がこの HTTPRoute を検出すると、VPC Lattice に 2 つの Target Groups を作成し、指定された weight に従ってトラフィックを分散する listener rule を設定します。Canary deployment の検証後、weight を徐々に調整できます。
</details>

15. VPC Lattice Service 用の IAM ベース Auth Policy を記述してください。（特定の IAM role のみが /admin path にアクセスできるようにする）

<details>

<summary>回答を表示</summary>

**回答:**
```bash
# Apply Auth Policy to VPC Lattice service
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-0123456789abcdef0 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowGeneralAccess",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "AllowAdminAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": [
            "arn:aws:iam::123456789012:role/AdminRole",
            "arn:aws:iam::123456789012:role/DevOpsRole"
          ]
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "DenyUnauthorizedAdmin",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          },
          "StringNotEquals": {
            "aws:PrincipalArn": [
              "arn:aws:iam::123456789012:role/AdminRole",
              "arn:aws:iam::123456789012:role/DevOpsRole"
            ]
          }
        }
      }
    ]
  }'
```

**Kubernetes Gateway API の方法:**
```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-type: "AWS_IAM"
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-lattice-auth-policy
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-policy: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::123456789012:role/AdminRole"
            },
            "Action": "vpc-lattice-svcs:Invoke",
            "Resource": "*"
          }
        ]
      }
data: {}
```

**解説:**
この Auth Policy は 3 つの rule で構成されます:
1. **AllowGeneralAccess**: /admin/* を除くすべての path について、すべての principal を許可する
2. **AllowAdminAccess**: AdminRole と DevOpsRole に /admin/* path へのアクセスを許可する
3. **DenyUnauthorizedAdmin**: 上記以外の role による /admin/* へのアクセスを明示的に拒否する

Client は SigV4 でリクエストに署名する必要があります。署名には AWS SDK または aws-sigv4 library を使用できます。
</details>

---

**採点:**
- 13-15 問正解: 優秀（VPC Lattice expert レベル）
- 10-12 問正解: 良好（実践的な適用が可能）
- 7-9 問正解: 平均（追加学習を推奨）
- 4-6 問正解: 基礎（基本概念の復習が必要）
- 0-3 問正解: 不十分（内容全体の再学習が必要）
