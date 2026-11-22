# EKS ノードの IAM 権限を IRSA と Pod Identity に移行する

> **最終更新日**: 2026年11月21日

アプリケーションの S3 権限が EC2 ノードのインスタンスプロファイル（ノード IAM ロール）に付与されていると、そのノード上でインスタンスメタデータサービス（IMDS）にアクセスできるすべての Pod が同じ権限を取得します。payments Pod 1つのために追加した権限が、同じノード上のログ転送ツールやバッチ Job にも与えられてしまいます。CloudTrail ではすべてが同じノードのインスタンスセッションとして記録されるため、どのワークロードが呼び出しを行ったのか判別できません。

このワークブックでは、その権限をワークロードごとの ID に移す2つの方法、IRSA（IAM Roles for Service Accounts）と EKS Pod Identity を比較します。次に、本番クラスターでの移行順序を示し、同じアプリの3つのコピーを並行して移行するライブデモを紹介します。

## 認証情報の取得元

![3つの Pod が、それぞれ異なる経路で認証情報を取得します。ノードロールを使う Pod は IMDSv2 から、IRSA の Pod は STS AssumeRoleWithWebIdentity から、Pod Identity の Pod はノード上の Pod Identity Agent と EKS Auth を介して認証情報を取得します。各 Pod は、受け取った認証情報を使って S3 リクエストに署名します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

Pod 内の AWS SDK と AWS CLI は、[デフォルトの認証情報プロバイダーチェーン](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)を先頭から順にたどります。環境変数の静的キー、ウェブ ID トークン（IRSA）、コンテナ認証情報プロバイダー（Pod Identity）は、いずれも IMDS より先に評価されます。そのため、EKS が IRSA または Pod Identity の変数を注入した新しい Pod は、コードを変更せずに新しいロールを使用します。何も注入されていない Pod は最後の手順である IMDS に進み、ノードロールを取得します。

| 経路 | Pod への注入内容 | SDK の呼び出し先 | 使用されるロール |
| --- | --- | --- | --- |
| ノードのインスタンスプロファイル | なし | IMDSv2 `169.254.169.254` | ノード IAM ロール（ノード上のすべての Pod で共有） |
| IRSA | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、トークンボリューム | リージョナル STS（Security Token Service）`AssumeRoleWithWebIdentity` | ServiceAccount のアノテーションで指定したロール |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、トークンボリューム | 同じノード上の Pod Identity Agent、`169.254.170.23` | アソシエーションで指定したロール |

**変数を注入するのは誰か、いつ注入されるか。** Pod が作成されると、API サーバーはリクエストを認証および認可してから、Mutating Admission の段階で Webhook `iam-for-pods.amazonaws.com`（amazon-eks-pod-identity-webhook）を呼び出します。この Webhook は EKS コントロールプレーン内で実行されるため、ノード上に Webhook Pod はありません。Webhook は Pod の ServiceAccount を確認します。アソシエーションがある場合は Pod Identity の変数とトークンボリュームを追加し、IRSA アノテーションだけがある場合は IRSA の変数とトークンボリュームを追加します。両方ある場合は Pod Identity だけを追加します。その後、kubelet がそのオーディエンス向けの投影トークンを要求し、マウントします。デモクラスターの `MutatingWebhookConfiguration` には `CREATE pods` というルールが1つだけあり、`failurePolicy: Ignore` に設定されています。そのため、実行中の Pod はロールアウトするまで変更されず、Webhook が応答できない場合は、変数がない状態で Pod が作成され、気付かないうちにノードロールが使われます。呼び出し元 ARN で結果を確認してください。また、Pod を作成する前に `kubectl create --dry-run=server` を使うと、Webhook 適用後の Pod 仕様を確認できます。

IMDS 応答ホップ制限が2以上の場合、host networking を使わない一般的な Pod でも、IMDSv2 トークンとノードロールの認証情報を取得できます。マネージドノードグループの起動テンプレートでは、この値が2に設定されていることがよくあります。これが、移行の最後の手順でホップ制限を1に下げる理由です。

<a id="irsa-flow"></a>
## IRSA の仕組み

![IRSA のフロー。Webhook は ServiceAccount のアノテーションを確認し、環境変数と投影トークン（aud sts.amazonaws.com）を注入します。SDK はトークンを STS AssumeRoleWithWebIdentity に送信します。STS は IAM OIDC プロバイダーを通じて署名を検証し、信頼ポリシーの aud と sub を確認して、一時認証情報を返します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **信頼関係の設定。** 各クラスターには OIDC（OpenID Connect）発行者 URL があります。その発行者を、アカウント内の IAM OIDC プロバイダーとして一度登録します。ロールの信頼ポリシーでは、そのプロバイダーを `Federated` プリンシパルとして指定し、`aud`（`sts.amazonaws.com`）と `sub`（`system:serviceaccount:<namespace>:<serviceaccount>`）を条件として設定します。
2. **Pod 作成時の注入。** ServiceAccount に `eks.amazonaws.com/role-arn` が設定されている場合、EKS の Mutating Webhook は、新しい各 Pod に `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE` と、`/var/run/secrets/eks.amazonaws.com/serviceaccount/token` にマウントされる投影トークンボリュームを追加します。実行中の Pod は変更されないため、ロールアウトが必要です。
3. **トークンの発行と更新。** kubelet はオーディエンス `sts.amazonaws.com` 向けの ServiceAccount トークンを要求し、ファイルに書き込み、有効期限が切れる前に更新します。
4. **トークンの交換。** SDK はトークンをリージョナル STS の `AssumeRoleWithWebIdentity` に送信します。STS は、IAM OIDC プロバイダーを通じて登録された発行者の鍵で署名を検証し、`aud` と `sub` の条件を確認して、一時認証情報を返します。Pod は STS と直接通信するため、STS へのネットワーク経路が必要です。[AWS の IRSA ドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## EKS Pod Identity の仕組み

![Pod Identity のフロー。EKS API のアソシエーションが ServiceAccount をロールに紐付け、EKS がコンテナ認証情報用の変数と投影トークン（aud pods.eks.amazonaws.com）を注入します。SDK はノード上の Pod Identity Agent を呼び出し、Agent はノードロールの eks-auth 権限を使って EKS Auth AssumeRoleForPodIdentity を呼び出します。EKS はセッションタグ付きのロール認証情報を返します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **Agent のセットアップ。** クラスターごとに `eks-pod-identity-agent` アドオンを一度インストールします。Agent はノードのホストネットワーク上で動作する DaemonSet で、リンクローカルアドレス `169.254.170.23`（IPv6 `[fd00:ec2::23]`）のポート80と2703を使用します。EKS Auto Mode には組み込み済みです。
2. **ロールとアソシエーション。** ロールは、サービスプリンシパル `pods.eks.amazonaws.com` に対して `sts:AssumeRole` と `sts:TagSession` を信頼します。クラスターごとのプロバイダーは不要なため、信頼ポリシーを変更せずに別のクラスターでも同じロールを使用できます。紐付けは EKS API のアソシエーション（クラスター、名前空間、ServiceAccount → ロール）で行い、Kubernetes オブジェクトにはアノテーションを付けません。
3. **Pod 作成時の注入。** アソシエーションが設定された ServiceAccount を使う場合、EKS は新しい Pod に `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` と、オーディエンス `pods.eks.amazonaws.com` 向けの投影トークンを注入します。
4. **認証情報の取得。** SDK はトークンをノード上の Agent に送信します。Agent はノードロールの `eks-auth:AssumeRoleForPodIdentity` 権限（`AmazonEKSWorkerNodePolicy` の一部）を使って EKS Auth を呼び出します。EKS Auth はトークンとアソシエーションを検証し、ロールを引き受け、`eks-cluster-arn`、`kubernetes-namespace`、`kubernetes-service-account` などのセッションタグ付き認証情報を返します。ノードロールに残すのは、Agent が EKS Auth を呼び出すために必要な権限だけです。アプリケーションの業務権限は Pod Identity ロールに付与します。[Pod Identity の仕組み](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSA と Pod Identity の比較

AWS は、可能な場合は EKS Pod Identity を推奨しています。IRSA が適しているランタイムやチーム構成もあります。[AWS による比較](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| 属性 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| クラスターごとの設定 | クラスターごとに IAM OIDC プロバイダーを登録 | クラスターごとに Pod Identity Agent アドオンを導入（Auto Mode には組み込み済み） |
| 紐付けの場所 | Kubernetes ServiceAccount のアノテーション | EKS API のアソシエーション（Kubernetes オブジェクトの変更なし） |
| 信頼ポリシー | `aud`/`sub` 条件付きの `Federated` OIDC プロバイダー。クラスターごとにステートメントが1つ増える | プリンシパルは `pods.eks.amazonaws.com` の1つ。新しいクラスターを追加しても変更不要 |
| スケールの上限 | アカウントあたりの OIDC プロバイダーはデフォルトで100個。デフォルトの2,048文字の信頼ポリシーでは、通常1ロールあたり約4つの紐付けが上限 | クラスターあたり5,000個のアソシエーション。ロールの信頼ポリシーは増えない |
| 認証情報の経路 | Pod → リージョナル STS（Pod が STS API クォータを使用） | Pod → ノード Agent → EKS Auth（Pod は STS を呼び出さない） |
| セッション情報 | ロールセッション名。セッションタグなし | クラスター、名前空間、ServiceAccount のセッションタグにより ABAC（属性ベースのアクセス制御）が可能 |
| ランタイム | EC2 上の EKS と Fargate、EKS Anywhere、ROSA、EC2 上のセルフマネージド Kubernetes | EKS の Linux EC2 ノードと EKS Hybrid Nodes（Agent のハイブリッド用 DaemonSet とノード認証情報ファイルが必要）。Fargate、Windows、Outposts、EKS Anywhere は非対応 |
| クロスアカウント | ターゲットアカウントのロールが、このクラスターの OIDC プロバイダーを信頼 | アソシエーションのロールはクラスターのアカウント内に配置。ターゲットロールへの委任またはロールチェーンで対応 |
| 職務分離 | IAM 管理者が OIDC プロバイダーを作成し、クラスター運用者がアノテーションを設定 | IAM はロールのみを管理し、紐付けは EKS API に配置 |

要するに、EC2 上で動く新しい EKS ワークロードでは、Pod Identity のほうがシンプルでスケールしやすい方法です。Fargate または Windows ノードを使う場合や、EKS 以外の Kubernetes でも同じ設定を実行する必要がある場合は、IRSA を使用してください。1つのクラスターで両方を使うこともできます。1つの ServiceAccount に IRSA アノテーションとアソシエーションの両方がある場合、EKS Webhook は新しい Pod に Pod Identity の変数だけを注入し、IRSA の変数は注入しません。デモクラスターで `kubectl create --dry-run=server` を実行して確認したところ、アノテーションだけの場合は `AWS_ROLE_ARN` と `AWS_WEB_IDENTITY_TOKEN_FILE` が返され、アソシエーションを追加すると `AWS_CONTAINER_CREDENTIALS_FULL_URI` と `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` だけが返されました。実行中の Pod は再作成されるまで IRSA の変数を保持するため、ロールアウトで切り替えて、不要になったアノテーションを削除してください。

どちらも EKS Hybrid Nodes で動作します。IRSA には Pod から STS への経路だけが必要です。通常、Pod Identity Agent はノードの IMDS から認証情報を取得しますが、ハイブリッドノードには IMDS がありません。そのため、ノードの `nodeadm` 設定で `spec.hybrid.enableCredentialsFile: true` を設定して `/eks-hybrid/.aws/credentials` を作成し、アドオンの設定で `daemonsets.hybrid.create` を有効にします（v1.3.3-eksbuild.1 以降）。Bottlerocket では、アドオン v1.3.7-eksbuild.2 以降、OS 1.39.0 以降、および `daemonsets.hybrid-bottlerocket.create` が必要です。[ハイブリッドノード向けアドオンの設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) · [ノードのブートストラップ](../eks-hybrid-nodes/04-node-bootstrap.md)

プライベートクラスターでは、IRSA Pod からリージョナル STS への経路と、Pod Identity Agent から EKS Auth（`eks-auth`）への経路を確保してください。インターネットへの経路がない場合は、対応する VPC インターフェイスエンドポイント、DNS、セキュリティグループを確認します。プロキシの背後で動作する場合は、`169.254.170.23` と `[fd00:ec2::23]` を `NO_PROXY` に追加してください。[Pod Identity を使用する際の考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [プライベートクラスターの要件](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 本番クラスターでの移行順序

1. **依存関係を洗い出す。** ノードロールのポリシーと、CloudTrail に実際に記録された IAM セッションを照合し、Deployment、StatefulSet、DaemonSet、CronJob、コントローラーが呼び出す AWS API を一覧にします。CloudTrail で S3 オブジェクトへのアクセスを確認するには、そのバケットでデータイベントを有効にする必要があります。ノードの登録と Pod Identity Agent のために `AmazonEKSWorkerNodePolicy` を残し、Amazon ECR（Elastic Container Registry）からイメージを取得するために `AmazonEC2ContainerRegistryPullOnly`（または同等のポリシー）も残します。VPC CNI（Container Network Interface）の `AmazonEKS_CNI_Policy` は専用の `aws-node` ロールに移せます。ノードロールから削除する前に、CNI の認証情報と新しい Pod への IP 割り当てを確認してください。[EKS ノード IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 の CloudTrail イベント](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **スコープを限定した IAM ロールと、ワークロードごとの専用 ServiceAccount を作成する。** IRSA の場合は、クラスターの発行者を IAM OIDC プロバイダーとして登録し、正確なオーディエンスとサブジェクトを確認するロールを作成して、ServiceAccount に `eks.amazonaws.com/role-arn` を設定します。Pod Identity の場合は、Agent の準備状況とノードの EKS Auth 権限を確認してから、リクエストタグでスコープを限定したロールとのアソシエーションを作成します。コンピューティング環境と SDK が対応していることを確認してください。[IRSA に必要な SDK バージョン](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity に必要な SDK バージョン](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **カナリア Pod を作成する。** Pod テンプレートの `serviceAccountName` を変更するか、新しい Pod をロールアウトしてから、注入された変数名、実行中のプロセスの呼び出し元 ARN、必要な AWS API を確認します。トークンやキーをログに記録してはいけません。明示的な認証情報や、デフォルトのプロバイダーチェーンで先に評価されるプロバイダーが優先される場合があります。[デフォルトの認証情報プロバイダーチェーン](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **ワークロードを1つずつ切り替える。** エラー率、`AccessDenied`、トークンと認証情報の更新、スケジュール実行を監視します。ワークロードがノードロールの業務権限に依存しなくなったら、そのポリシーステートメントだけを削除します。ロールバック期間中は、以前の Pod テンプレートとノードポリシーの正確なコピーを保持してください。権限を削除した後にロールバックする場合は、まず最小限のポリシーを復元して反映を確認してから、以前の Pod をデプロイします。
5. **ノード認証情報へのアクセスを制限する。** 互換性をテスト済みのノードグループから順に、IMDSv2 を必須にして一般の Pod から IMDS へのアクセスを制限します。カスタム起動テンプレートを使うマネージドノードグループでは、新しいテンプレートバージョンで `HttpTokens=required` と `HttpPutResponseHopLimit=1` を設定して、ノードをロールします。Karpenter では `EC2NodeClass.spec.metadataOptions` を使用します。EKS Auto Mode では、デフォルトで IMDSv2 が必須になり、ホップ制限は1に設定されます。`hostNetwork` を使う Pod はホップ制限に関係なく IMDS にアクセスできるため、別途制御してください。IMDS を無効化（`HttpEndpoint=disabled`）してはいけません。Pod Identity Agent 自身がホストネットワーク上で動作し、EKS Auth を呼び出すために IMDS からノードロールの認証情報を取得するからです。[マネージドノードグループの起動テンプレート](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAM のベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>信頼ポリシーとカナリア用コマンド</summary>

IRSA ロールの信頼ポリシーでは、クラスターの発行者と ServiceAccount のスコープを限定します。`<OIDC_ISSUER>` には `https://` を含めずに指定します。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<OIDC_ISSUER>"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "<OIDC_ISSUER>:aud": "sts.amazonaws.com",
      "<OIDC_ISSUER>:sub": "system:serviceaccount:<NAMESPACE>:<IRSA_SA>"
    }}
  }]
}
```

Pod Identity ロールでは、EKS サービスプリンシパルを信頼します。これらの条件はセッショ​​ンタグを通じてクラスター、名前空間、ServiceAccount のスコープを限定するため、アソシエーションでセッションタグを有効にしておいてください。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {"StringEquals": {
      "aws:RequestTag/eks-cluster-arn": "<CLUSTER_ARN>",
      "aws:RequestTag/kubernetes-namespace": "<NAMESPACE>",
      "aws:RequestTag/kubernetes-service-account": "<POD_IDENTITY_SA>"
    }}
  }]
}
```

```bash
# If you chose IRSA
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" annotate sa "$IRSA_SA" \
  "eks.amazonaws.com/role-arn=$IRSA_ROLE_ARN"

# If you chose Pod Identity and the Agent is ready
aws eks create-pod-identity-association --region "$AWS_REGION" --cluster-name "$CLUSTER" \
  --namespace "$NAMESPACE" --service-account "$POD_IDENTITY_SA" --role-arn "$POD_IDENTITY_ROLE_ARN"

# Roll out the canary with the ServiceAccount chosen above
SA="$IRSA_SA"   # or "$POD_IDENTITY_SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

<a id="live-demo"></a>
## ライブデモ：同じアプリの3つのコピーを移行する

![デモのフロー。最初は orders アプリの3つのコピーすべてが IMDS からノードロールを取得して S3 を読み取ります。migrate-irsa の後、1つのコピーが STS から IRSA ロールを取得します。migrate-podid の後、別のコピーが Agent を介して Pod Identity ロールを取得します。revoke でノードロールの S3 権限を削除すると、拒否されるのはレガシーのコピーだけです。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

このデモでは、既存の EKS 1.36 クラスターに専用のマネージドノードグループ（t3.medium、プライベートサブネット、テイントあり）を1つ追加し、同じ orders アプリのコピーを3つ実行します。各コピーは3秒ごとに STS `GetCallerIdentity` と S3 `GetObject` を呼び出し、認証情報の取得元、ロール名、S3 の結果を含む JSON を1行出力します。開始時の状態はクラスターの本番ノードグループと同じで、IMDSv2 が必須、ホップ制限は2、ノードロールにはアプリの `s3:GetObject` 権限があります。レガシー Pod は host networking を使わない通常の Pod です。[デモのコードと発表者向け手順書](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [スライド（韓国語）](https://presentation.atomai.click/eks-workload-identity/)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<cluster name> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
./demo.sh up d1124            # before the talk: node group, roles, bucket, three copies
./demo.sh watch d1124         # second terminal: live table
./demo.sh migrate-irsa d1124  # ServiceAccount annotation + rollout
./demo.sh migrate-podid d1124 # association + injection check + rollout
./demo.sh diff d1124          # compare injected variables, tokens, trust policies
./demo.sh revoke d1124        # remove the S3 permission from the node role
./demo.sh harden d1124        # (optional, ~15 min) roll the nodes to hop limit 1
./demo.sh restore d1124       # back to the start (rehearse again)
./demo.sh down d1124          # clean up
```

`page-up` を使うと、閲覧専用のライブページを参加者と共有できます。経路は CloudFront → VPC オリジン → 内部 ALB → ダッシュボード Pod で、ALB のセキュリティグループは CloudFront VPC オリジンからの通信だけを許可します。ダッシュボード Pod に IAM ロールはなく、この名前空間の Pod とログを読み取る Role だけがあります。また、デモノードのホップ制限が2であるため、NetworkPolicy によって IMDS や Pod Identity Agent へのアクセスを遮断します。この分離には VPC CNI のネットワークポリシー適用（`enableNetworkPolicy`）が必要で、`page-up` は最初にその有効化を確認します。

スクリプトが作成するすべてのリソースには、名前または `LabRun` タグに実行 ID が含まれます。スクリプトが変更または削除するのは、その名前またはタグに一致するリソースだけです。VPC、サブネット、アドオン、OIDC プロバイダーは作成せず、存在確認だけを行います。唯一のセキュリティグループは、オプションの `page-up` が内部 ALB 用に作成するものです。[ハンズオンラボ](../labs/security/17-eks-workload-identity-migration-lab.md)では、各手順をコマンド、期待される出力、チェックポイントとともに説明します。

### ソウルリージョンでの測定結果

2026年11月21日、`ap-northeast-2` の EKS 1.36 クラスターで2回リハーサルを行い、Pod 内では AWS CLI 2.35.11 を使用しました。1回目のリハーサルでは Pod Identity の注入に失敗したため（下記参照）、スクリプトを修正しました。表には、修正後のスクリプトを使って最初から最後まで実行した2回目のリハーサルの結果を示しています。`harden` の結果だけは1回目のリハーサルから取得しています。

| 手順 | orders-legacy | orders-irsa | orders-podid | 所要時間 |
| --- | --- | --- | --- | --- |
| 開始時 | IMDS · ノードロール · 読み取り許可 | IMDS · ノードロール · 読み取り許可 | IMDS · ノードロール · 読み取り許可 | — |
| `migrate-irsa` | 変更なし | STS · IRSA ロール · 読み取り許可 | 変更なし | 6秒 |
| `migrate-podid` | 変更なし | 変更なし | Agent · Pod Identity ロール · 読み取り許可 | 11秒（アソシエーション作成後、注入が見えるまでの5秒を含む） |
| `revoke` | ノードロール · **読み取り拒否** | 読み取り許可 | 読み取り許可 | 13秒後に拒否 |
| `harden`（オプション、1回目のリハーサル） | **認証情報なし**（IMDS 応答を遮断） | 読み取り許可 | 読み取り許可 | ノードのロールアウト 878秒 |

`diff` では、2つの方式の違いを確認できます。どちらのトークンも同じクラスター発行者が署名した ServiceAccount トークンですが、オーディエンスと受信先は異なります。

| 比較項目 | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| 注入される変数 | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` |
| トークンの `aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| トークンの `sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| トークンの有効期間 | 86,400秒（24時間） | 約22～24時間（Webhook がランダムなずれを追加。測定値は79,636秒と86,171秒） |
| ロールの信頼プリンシパル | `Federated`：クラスターの OIDC プロバイダー。条件は `aud` と `sub` | `Service`：`pods.eks.amazonaws.com`。リクエストタグの条件が3つ |

リハーサルでは、結果が反映されるまでに時間がかかる事象が2つ確認されました。1つ目は、最初のリハーサルでアソシエーション作成直後に Pod をロールアウトしたところ、Pod Identity の変数がなくノードロールを使い続けたため、ノードポリシーを削除した後にその Pod も拒否されたことです。そのため `migrate-podid` は、Deployment の Pod テンプレートを `kubectl create --dry-run=server` に渡して Mutating Webhook が何を注入するか確認し、その後にロールアウトするようになっています。2回目のリハーサルでは、アソシエーションの作成から5秒後に注入が確認できました。2つ目は、1回目のリハーサルで `revoke` を実行した後、レガシー Pod のリクエストは13秒以内に拒否されたものの、その約4.5分後に許可された読み取りがさらに2回確認されたことです。その直後に確認した1分間の読み取り11回は、すべて拒否されました。本番環境では、ノードポリシーを削除した後、結論を出す前に数分間監視を続けてください。

## トラブルシューティング

- **ノードロールが使われている。** Pod が新しく作成されたものか、正しい ServiceAccount を参照しているか、IRSA アノテーションまたは正確なアソシエーションがあるかを確認します。SDK のバージョン、デフォルトのプロバイダーチェーン、注入された変数名も確認してください。
- **IRSA のトークン交換に失敗する。** トークン発行者に対する IAM プロバイダー、`aud`/`sub` の信頼条件、STS への接続性を確認します。
- **Pod Identity の認証情報取得に失敗する。** 対象ノード上の Agent、EKS Auth への接続性、ノードの IAM 権限、アソシエーションの反映状況、ロールのリクエストタグに関する信頼条件を確認します。アソシエーションの作成後、反映まで数秒かかることがあります。
- **想定したロールで S3 アクセスが拒否される。** ID に対するアクセス権とリソースへのアクセス権は別です。オブジェクト ARN、バケットポリシー、SCP（Service Control Policies）、権限境界、VPC エンドポイントポリシーを確認してください。AWS KMS（Key Management Service）キーで暗号化されたオブジェクト（SSE-KMS）の場合は、キーに対する権限も確認します。
