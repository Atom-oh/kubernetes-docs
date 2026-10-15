# VPC Lattice クイズ

ガイドを確認し、YAML だけでなく前提条件も説明してください。

## 1. Amazon VPC Lattice の主な目的は何ですか？

- A) Internet DNS ベースのグローバル負荷分散
- B) VPC およびアカウント間のプライベートなアプリケーションとリソースの接続
- C) クロスリージョンのデータベースレプリケーション
- D) すべての IP ルーティングの置き換え

<details>
<summary>回答を表示</summary>

B. Lattice はサービスとリソース構成を接続します。HTTP サービスルーティングとリソースアクセスモデルは別物です。関連付け、ネットワーク制御、認可は引き続き適用されます。

</details>

## 2. service network は何を表しますか？

- A) 物理ネットワークデバイス
- B) サービス/リソースとクライアントネットワークの関連付けを持つ論理的なグループ
- C) サブネットのルートテーブル
- D) すべてのサービスで共有する 1 つの HTTP リスナー

<details>
<summary>回答を表示</summary>

B. リスナーとルールは個々のサービスに属します。関連付けは、security group と適用されるポリシーに従う経路を有効にしますが、すべてのリクエストを無条件に認可するものではありません。

</details>

## 3. App Mesh と Lattice に関する正しい記述はどれですか？

- A) Lattice では Pod ごとに Envoy sidecar が必要である
- B) App Mesh は Envoy proxy を使用する一方、Lattice はアプリケーション sidecar を必要としないマネージドデータプレーンを提供する
- C) 他のすべての mesh では sidecar が必要である
- D) App Mesh は新規 Deployment で引き続き利用可能である

<details>
<summary>回答を表示</summary>

B. App Mesh は Envoy sidecar proxy を使用していましたが、Lattice はアプリケーション sidecar を使用しないマネージドデータプレーンを提供します。D は誤りです。AWS App Mesh のサポートは 2026-09-30 に終了し、そのコンソールとリソースにはもはやアクセスできないため、新規作成ではなく既存の Deployment を移行してください。他の mesh モードでの sidecar 要件は異なります。

</details>

## 4. AWS Gateway API Controller はリソースをどのようにマッピングしますか？

- A) Kubernetes Service ごとに 1 つの service network を作成する
- B) Gateway は名前でネットワークを選択し、各 HTTPRoute は独自の Lattice service/domain を作成する
- C) Gateway は常に、すべての Route で共有される 1 つの ingress IP を作成する
- D) controller は Ingress API のみを使用する

<details>
<summary>回答を表示</summary>

B. GatewayClass は controller を選択します。Gateway は namespace を付けない名前で既存の service network を参照し、バックエンドの Service/endpoints が target group を提供します。Gateway 単体ではネットワークを作成しません。

</details>

## 5. クライアントは割り当てられた Lattice service DNS 名をどのように取得すべきですか？

- A) Kubernetes Service 名にリージョンを付加する
- B) service-network ID を推測したホスト名に入れる
- C) get-service dnsEntry または Route の lattice-assigned-domain-name annotation を読み取る
- D) Gateway.status.addresses をすべての Route のアドレスとして再利用する

<details>
<summary>回答を表示</summary>

C. 各 Route には独自の service/domain があります。実際に返された値を使用してください。サービスを再作成すると、割り当てられた名前が変わることがあります。custom domain には独自の DNS と certificate の設定が必要です。

</details>

## 6. 認証に関する正しい記述はどれですか？

- A) service の NONE はすべての network policy を無効にする
- B) AWS_IAM は、クライアントに IAM role があれば署名なしの curl リクエストを受け入れる
- C) AWS_IAM はサポート対象の署名付きリクエストを使用し、適用されるすべての IAM 認可レイヤーがアクセスを許可する必要がある
- D) RAM sharing は自動的に Invoke を許可する

<details>
<summary>回答を表示</summary>

C. VPC Lattice は SigV4 と SigV4A をサポートします。署名時には vpc-lattice-svcs と UNSIGNED-PAYLOAD を使用してください。呼び出し元の identity permission と適用される network/service auth policy がアクセスを許可する必要があり、明示的な Deny が優先されます。NONE は自身のレイヤーにのみ影響します。

</details>

## 7. 名前付き Lattice service target-group type ではないものはどれですか？

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>回答を表示</summary>

D. service target-group type には INSTANCE、IP、LAMBDA、ALB があります。これは Lattice が RDS database に接続できないことを意味するものではありません。resource configuration と resource gateway は、別個の TCP resource-access model を提供します。service auth policy はそのリソーストラフィックを管理しません。

</details>

## 8. backendRefs の weight 比率 90:10 は何を意味しますか？

- A) 連続する 10 件のリクエストのうち必ず 1 件が canary に到達する
- B) 2 つの backend 間の相対的なトラフィック分散
- C) Pod の replica-count 要件
- D) Gateway API ではサポートされない annotation

<details>
<summary>回答を表示</summary>

B. ネイティブの backendRefs.weight は相対分散を設定します。少数のリクエストサンプルが正確に一致する必要はありません。両方の backend が存在し、正常である必要があります。canary の割合を増やす前に、エラーとレイテンシーを確認してください。

</details>

## 9. service network のクロスアカウント共有について説明してください。

<details>
<summary>回答を表示</summary>

所有者は、network ARN と対象のアカウント、organization、または OU に対して RAM share を作成します。sharing が有効な organization 内の consumer は招待を必要としません。その他の該当する構成では承諾が必要です。consumer は自身の VPC を関連付けるか、適切な service-network endpoint を作成します。sharing は Invoke を許可しません。呼び出し元ポリシー、auth policy、network path、security group もアクセスを許可する必要があります。share を停止しても、既存の関連付けは残ります。

</details>

## 10. demo backend 用の Kubernetes health-check policy を作成してください。

<details>
<summary>回答を表示</summary>

TargetGroupPolicy を、その対象 Service と同じ namespace で使用します。controller CRD は intervalSeconds/timeoutSeconds/statusMatch を使用しますが、AWS API は healthCheckIntervalSeconds/healthCheckTimeoutSeconds/matcher を使用します。

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

backend は実際に 8080 で listen し、/health で 200 を返す必要があります。threshold は readiness の判断に役立ちますが、可用性やダウンタイムゼロを保証するものではありません。target-type と protocol 固有の動作を確認してください。

</details>

## 11. Transit Gateway と VPC Lattice はどのように異なりますか？

<details>
<summary>回答を表示</summary>

Transit Gateway はネットワーク間で IP traffic をルーティングします。Lattice は service と resource configuration を公開します。HTTP service path は L7 routing を使用できますが、TLS/TCP/resource の機能には異なる特性があります。両者は併用できます。service-network VPC endpoint は transit/peering 経由で到着する該当クライアントをサポートします。直接の VPC association だけでは、その transit access は許可されません。

</details>

## 12. auth policy はどのレベルに適用でき、demo API path をどのように制限しますか？

<details>
<summary>回答を表示</summary>

auth policy は AWS_IAM で構成された service network と個々の service に適用されます。両方の適用レイヤーと呼び出し元の identity policy がリクエストを許可する必要があります。ワイルドカード一致には StringLike を使用し、root path を明示的に含めます。

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

StringEquals は /api/* をリテラルとして一致させます。このポリシーは canonical path に関するものです。application normalization と controller path routing は別の動作です。invocation authorization は PutResourcePolicy ではなく PutAuthPolicy で管理します。

</details>

## 13. AWS Gateway API Controller v2.1.3 の IRSA インストールについて説明してください。

<details>
<summary>回答を表示</summary>

cluster でサポートされる Kubernetes version、Gateway API compatibility、IAM OIDC provider、network/webhook reachability を確認します。対象の account/features 向けにリリースで推奨された policy を確認してください。その広範な upstream permission は least-privilege を保証するものではありません。専用の controller service account とリリース済み OCI chart を使用します。

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

controller role はリソースを管理するものであり、application caller role ではありません。既存の service account/release には ownership を考慮した upgrade が必要です。Helm は CRD を自動的に upgrade しません。個別の service-network/auth-policy 設定についてはガイドを参照してください。

</details>

## 14. 90:10 の stable/canary 分割用 HTTPRoute を作成してください。

<details>
<summary>回答を表示</summary>

前提条件: lattice-demo 内のガイドの my-network HTTPS Gateway、その既存の service network と有効な auth policy、8080 上の両方の backend Deployment/Service、および target-group health policy。続けて以下を適用します。

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

この Route にもガイドの IAMAuthPolicy を適用し、reconciliation を確認してください。weight annotation は不要です。Route に割り当てられた domain と署名付き HTTPS リクエストを使用してください。適用の成功は backend が正常であることの証明にはなりません。

</details>

## 15. 専用の管理 service に対して、AdminRole と DevOpsRole のみが /admin とその subpath を Invoke できるようにしてください。

<details>
<summary>回答を表示</summary>

実際の account/role ARN を使用して、以下を完全な service auth policy として使用してください。その専用 service を AWS_IAM に設定し、caller identity policy と network auth policy もこれらの role と path を許可することを確認してください。ガイドの API 専用 network policy は、この独立した管理 service のために確認済みの変更が必要です。

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

lattice-demo 内で controller が所有する admin という名前の HTTPRoute には、実際の CRD を使用して次のようにアタッチします。

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

広範な AllowGeneralAccess statement はありません。このポリシーでは、他の role と path には Allow がなく、/admin/* だけでなく /admin も明示的に含まれます。path normalization/encoding は application security requirement として扱ってください。専用の role 制限 service と application authorization により、path alias への依存を減らせます。direct backend access も保護する必要があります。IAMAuthPolicy を削除すると target auth type は NONE に変わり、deny や安全な rollback の仕組みにはなりません。

</details>

スコアが 13～15 はこの章をよく理解していることを示し、10～12 は見落としたトピックの確認を、0～9 はガイドの再読を推奨します。クイズのスコアは、本番運用の経験を証明するものではありません。

[ガイドに戻る](../../networking/02-vpc-lattice.md)