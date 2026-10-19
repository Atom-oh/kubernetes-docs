# VPC Lattice クイズ

ガイドを確認し、YAML だけでなく前提条件も説明してください。

## 1. Amazon VPC Lattice の主な目的は何ですか？

- A) インターネットの DNS を使ったグローバル負荷分散
- B) VPC およびアカウント間のプライベートなアプリケーションとリソースの接続
- C) クロスリージョンのデータベースレプリケーション
- D) すべての IP ルーティングの置き換え

<details>
<summary>回答を表示</summary>

B. Lattice はサービスとリソース構成を接続します。HTTP サービスルーティングとリソースアクセスモデルは別物です。関連付け、ネットワーク制御、認可は引き続き適用されます。

</details>

## 2. サービスネットワークは何を表しますか？

- A) 物理ネットワークデバイス
- B) サービス/リソースとクライアントネットワークの関連付けを持つ論理的なグループ
- C) サブネットのルートテーブル
- D) すべてのサービスで共有する 1 つの HTTP リスナー

<details>
<summary>回答を表示</summary>

B. リスナーとルールは個々のサービスに属します。関連付けによって、セキュリティグループと適用されるポリシーの範囲内で通信経路が有効になりますが、すべてのリクエストが無条件に認可されるわけではありません。

</details>

## 3. App Mesh と Lattice に関する正しい記述はどれですか？

- A) Lattice では Pod ごとに Envoy サイドカーが必要である
- B) App Mesh は Envoy プロキシを使用する一方、Lattice はアプリケーションサイドカーを必要としないマネージドデータプレーンを提供する
- C) 他のすべてのメッシュではサイドカーが必要である
- D) App Mesh は新規 Deployment で引き続き利用可能である

<details>
<summary>回答を表示</summary>

B. App Mesh は Envoy サイドカープロキシを使用していましたが、Lattice はアプリケーションサイドカーを使わないマネージドデータプレーンを提供します。D は誤りです。AWS App Mesh のサポートは 2026-09-30 に終了し、そのコンソールとリソースにはアクセスできなくなったため、新しく作成するのではなく、既存のデプロイメントを移行してください。他のメッシュ方式ではサイドカーの要件が異なります。

</details>

## 4. AWS Gateway API Controller はリソースをどのようにマッピングしますか？

- A) Kubernetes Service ごとに 1 つのサービスネットワークを作成する
- B) Gateway は名前でサービスネットワークを選択し、各 HTTPRoute は独自の Lattice サービス／ドメインを作成する
- C) Gateway は常に、すべての Route で共有される 1 つの ingress IP を作成する
- D) コントローラーは Ingress API のみを使用する

<details>
<summary>回答を表示</summary>

B. GatewayClass はコントローラーを選択します。Gateway は namespace を付けない名前で既存のサービスネットワークを参照し、バックエンドの Service とエンドポイントがターゲットグループになります。Gateway 単体ではネットワークを作成しません。

</details>

## 5. クライアントは割り当てられた Lattice サービスの DNS 名をどのように取得すべきですか？

- A) Kubernetes Service 名にリージョンを付加する
- B) サービスネットワーク ID を推測で作ったホスト名に入れる
- C) get-service の dnsEntry または Route の lattice-assigned-domain-name annotation を読み取る
- D) Gateway.status.addresses をすべての Route のアドレスとして再利用する

<details>
<summary>回答を表示</summary>

C. Route ごとに独自のサービスとドメインがあります。実際に返された値を使用してください。サービスを再作成すると、割り当てられた名前が変わることがあります。カスタムドメインには、個別の DNS と証明書の設定が必要です。

</details>

## 6. 認証に関する正しい記述はどれですか？

- A) サービスの NONE 設定ですべてのネットワークポリシーが無効になる
- B) AWS_IAM は、クライアントに IAM ロールがあれば署名なしの curl リクエストを受け入れる
- C) AWS_IAM はサポート対象の署名付きリクエストを使用し、適用されるすべての IAM 認可レイヤーがアクセスを許可する必要がある
- D) RAM で共有すると自動的に Invoke が許可される

<details>
<summary>回答を表示</summary>

C. VPC Lattice は SigV4 と SigV4A をサポートします。署名時には vpc-lattice-svcs と UNSIGNED-PAYLOAD を使用してください。呼び出し元の ID に付与された権限と、適用されるネットワーク／サービス認証ポリシーの両方がアクセスを許可する必要があります。明示的な Deny があればそれが優先されます。NONE は自身のレイヤーにのみ影響します。

</details>

## 7. Lattice サービスのターゲットグループの種類として定義されていないものはどれですか？

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>回答を表示</summary>

D. サービスのターゲットグループの種類には INSTANCE、IP、LAMBDA、ALB があります。Lattice が RDS データベースに接続できないという意味ではありません。リソース設定とリソースゲートウェイは、別の TCP リソースアクセス方式を提供します。サービス認証ポリシーは、そのリソース通信には適用されません。

</details>

## 8. backendRefs の weight 比率 90:10 は何を意味しますか？

- A) 連続する 10 件のリクエストのうち必ず 1 件がカナリア版に到達する
- B) 2 つのバックエンド間の相対的なトラフィック分散
- C) Pod のレプリカ数に関する要件
- D) Gateway API ではサポートされない annotation

<details>
<summary>回答を表示</summary>

B. ネイティブの backendRefs.weight は相対分散を設定します。少数のリクエストサンプルが正確に一致する必要はありません。両方の backend が存在し、正常である必要があります。canary の割合を増やす前に、エラーとレイテンシーを確認してください。

</details>

## 9. サービスネットワークをアカウント間で共有する方法を説明してください。

<details>
<summary>回答を表示</summary>

所有者は、サービスネットワーク ARN と共有先のアカウント、組織、または OU を指定して RAM 共有を作成します。共有が有効な組織内の利用者には招待は不要です。その他の構成では承諾が必要な場合があります。利用者は自分の VPC を関連付けるか、適切なサービスネットワークエンドポイントを作成します。共有しただけでは Invoke は許可されません。呼び出し元のポリシー、認証ポリシー、ネットワーク経路、セキュリティグループもアクセスを許可する必要があります。共有を停止しても、既存の関連付けは残ります。

</details>

## 10. デモのバックエンド用に Kubernetes のヘルスチェックポリシーを作成してください。

<details>
<summary>回答を表示</summary>

TargetGroupPolicy は、対象の Service リソースと同じ namespace に作成します。コントローラーの CRD では intervalSeconds／timeoutSeconds／statusMatch を使いますが、AWS API では healthCheckIntervalSeconds／healthCheckTimeoutSeconds／matcher を使います。

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

バックエンドが実際に 8080 番ポートで待ち受け、/health に 200 を返す必要があります。しきい値は準備状態の判定に役立ちますが、可用性やダウンタイムゼロを保証するものではありません。ターゲットの種類とプロトコル固有の動作を確認してください。

</details>

## 11. Transit Gateway と VPC Lattice はどのように異なりますか？

<details>
<summary>回答を表示</summary>

Transit Gateway はネットワーク間の IP 通信をルーティングします。Lattice はサービスとリソース設定へのアクセスを提供します。HTTP サービスでは L7 ルーティングを使えますが、TLS／TCP／リソースアクセスでは利用できる機能が異なります。両者は併用できます。サービスネットワークの VPC エンドポイントを使うと、Transit Gateway やピアリング経由で到達する一部のクライアントも接続できます。VPC を直接関連付けるだけでは、そのような中継経由のアクセスは許可されません。

</details>

## 12. 認証ポリシーはどのレベルに適用でき、デモ API のパスをどのように制限しますか？

<details>
<summary>回答を表示</summary>

認証ポリシーは AWS_IAM を設定したサービスネットワークと個々のサービスに適用できます。該当する各レイヤーと呼び出し元の ID ポリシーの両方がリクエストを許可する必要があります。ワイルドカードには StringLike を使用し、ルートパスも明示的に含めます。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

StringEquals は /api/* という文字列そのものに一致します。このポリシーが対象とするのは正規化されたパスです。アプリケーションによる正規化とコントローラーのパスルーティングは別の動作です。呼び出しの認可には PutResourcePolicy ではなく PutAuthPolicy を使います。

</details>

## 13. AWS Gateway API Controller v2.1.3 の IRSA インストールについて説明してください。

<details>
<summary>回答を表示</summary>

クラスターでサポートされる Kubernetes のバージョン、Gateway API との互換性、IAM OIDC プロバイダー、ネットワークと Webhook の疎通性を確認します。対象アカウントと有効にする機能に応じて、リリースで推奨されたポリシーを確認してください。upstream が推奨する広範な権限は、最小権限を保証するものではありません。専用のコントローラー用サービスアカウントと、リリース済みの OCI チャートを使用します。

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

コントローラーのロールはリソースを管理するためのもので、アプリケーションの呼び出し元ロールではありません。既存のサービスアカウントやリリースを更新する場合は、リソースの所有関係を確認してください。Helm は CRD を自動的に更新しません。サービスネットワークと認証ポリシーの設定については、ガイドを参照してください。

</details>

## 14. 安定版とカナリア版に 90:10 で振り分ける HTTPRoute を作成してください。

<details>
<summary>回答を表示</summary>

前提条件: lattice-demo 内にあるガイド記載の my-network HTTPS Gateway と、その既存のサービスネットワークおよび有効な認証ポリシー、8080 番ポートを使う両バックエンドの Deployment／Service、ターゲットグループのヘルスチェックポリシー。準備後、次を適用します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

この Route にもガイドの IAMAuthPolicy を適用し、調整結果を確認してください。weight annotation は不要です。Route に割り当てられたドメインと署名付き HTTPS リクエストを使います。適用に成功しても、バックエンドが正常だとは限りません。

</details>

## 15. 専用の管理サービスで、AdminRole と DevOpsRole だけが /admin とその配下のパスを Invoke できるようにしてください。

<details>
<summary>回答を表示</summary>

実際のアカウント／ロール ARN を指定し、以下をサービス認証ポリシー全体として使用します。専用サービスを AWS_IAM に設定し、呼び出し元の ID ポリシーとネットワーク認証ポリシーでも、これらのロールとパスが許可されていることを確認してください。ガイドの API 専用ネットワークポリシーをこの独立した管理サービスにも適用するには、内容を確認して変更する必要があります。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
          "vpc-lattice-svcs:RequestPath": [
            "/admin",
            "/admin/*"
          ]
        }
      }
    }
  ]
}
```

lattice-demo 内でコントローラーが管理する admin という名前の HTTPRoute には、次の実際の CRD を使ってポリシーを関連付けます。

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: admin-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["arn:aws:iam::123456789012:role/AdminRole","arn:aws:iam::123456789012:role/DevOpsRole"]},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/admin","/admin/*"]}}}]}'
```

広範な AllowGeneralAccess ステートメントはありません。このポリシーでは、他のロールやパスには Allow がなく、/admin/* だけでなく /admin も明示的に含まれます。パスの正規化／エンコードは、アプリケーションのセキュリティ要件として扱ってください。ロールを限定した専用サービスとアプリケーション側の認可により、パス別名への依存を減らせます。バックエンドへの直接アクセスも保護が必要です。IAMAuthPolicy を削除すると対象の認証タイプは NONE に変わります。これは拒否設定でも、安全にロールバックする方法でもありません。

</details>

スコアが 13～15 はこの章をよく理解していることを示し、10～12 は見落としたトピックの確認を、0～9 はガイドの再読を推奨します。クイズのスコアは、本番運用の経験を証明するものではありません。

[ガイドに戻る](../../networking/02-vpc-lattice.md)
