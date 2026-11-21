# EKSノードのIAM権限をIRSAとPod Identityに移行する

> **最終更新日**: 2026年11月21日

アプリケーションのS3権限がEC2ノードのインスタンスプロファイル、つまりノードのIAMロールにアタッチされていると、そのノード上でインスタンスメタデータサービス（IMDS）にアクセスできるすべてのPodが同じ権限を取得します。あるpayments Podのために追加した許可は、同じノード上のログ転送PodやバッチJobにも与えられます。CloudTrailにはすべてが同じノードのインスタンスセッションとして記録されるため、どのワークロードが呼び出しを行ったのか判別できません。

このワークブックでは、その権限をワークロード単位のIDに移行する2つの方法、IRSA（IAM Roles for Service Accounts）とEKS Pod Identityを比較します。続いて、本番クラスターでの移行順序を示し、同じアプリの3つのコピーを並行して移行するライブデモを紹介します。

## 認証情報の取得元

![3つのPodが3つの経路で認証情報を取得します。ノードロールのPodはIMDSv2から、IRSA PodはSTS AssumeRoleWithWebIdentityから、Pod Identity Podはノード上のPod Identity AgentとEKS Authを介して認証情報を取得します。各Podは、受け取った認証情報を使ってS3リクエストに署名します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

Pod内のAWS SDKとAWS CLIは、[デフォルト認証情報プロバイダーチェーン](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)を先頭から順にたどります。環境変数の静的キー、Web IDトークン（IRSA）、コンテナ認証情報プロバイダー（Pod Identity）は、いずれもIMDSより先に評価されます。そのため、EKSがIRSAまたはPod Identityの変数を注入した新しいPodは、コードを変更しなくても新しいロールを使用します。何も注入されていないPodは最後の手順であるIMDSに進み、ノードロールを取得します。

| 経路 | Podに注入されるもの | SDKの呼び出し先 | 使用されるロール |
| --- | --- | --- | --- |
| ノードのインスタンスプロファイル | なし | IMDSv2 `169.254.169.254` | ノードIAMロール（ノード上のすべてのPodで共有） |
| IRSA | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、トークンボリューム | リージョナルSTS（Security Token Service）`AssumeRoleWithWebIdentity` | ServiceAccountのアノテーションに記載されたロール |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、トークンボリューム | 同じノード上のPod Identity Agent、`169.254.170.23` | アソシエーションで指定されたロール |

IMDSレスポンスのホップ制限が2以上の場合、host networkingを使用しない通常のPodでもIMDSv2トークンとノードロールの認証情報を取得できます。マネージドノードグループの起動テンプレートでは、この値が2に設定されていることがよくあります。そのため、移行の最後の手順でホップ制限を1に引き下げます。

<a id="irsa-flow"></a>
## IRSAの仕組み

![IRSAのフロー。WebhookはServiceAccountのアノテーションを確認し、環境変数と投影トークン（aud sts.amazonaws.com）を注入します。SDKはトークンをSTS AssumeRoleWithWebIdentityに送信します。STSはIAM OIDCプロバイダーを通じて署名を検証し、信頼ポリシーのaudとsubを確認して、一時的な認証情報を返します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **信頼関係の設定。** 各クラスターにはOIDC（OpenID Connect）発行者URLがあります。その発行者をアカウント内のIAM OIDCプロバイダーとして一度登録します。ロールの信頼ポリシーでは、そのプロバイダーを`Federated`プリンシパルとして指定し、`aud`（`sts.amazonaws.com`）と`sub`（`system:serviceaccount:<namespace>:<serviceaccount>`）を条件に設定します。
2. **Pod作成時の注入。** ServiceAccountに`eks.amazonaws.com/role-arn`が設定されていると、EKSの変更Webhookが新しい各Podに`AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`と、`/var/run/secrets/eks.amazonaws.com/serviceaccount/token`にある投影トークンボリュームを追加します。実行中のPodは変更されないため、ロールアウトが必要です。
3. **トークンの発行と更新。** kubeletはaudienceが`sts.amazonaws.com`のServiceAccountトークンを要求し、ファイルに書き込んで、有効期限が切れる前に更新します。
4. **トークンの交換。** SDKはトークンをリージョナルSTSの`AssumeRoleWithWebIdentity`に送信します。STSはIAM OIDCプロバイダーを通じて登録された発行者キーで署名を検証し、`aud`と`sub`の条件を確認して、一時的な認証情報を返します。PodはSTSと直接通信するため、STSへのネットワーク経路が必要です。[AWSのIRSAドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## EKS Pod Identityの仕組み

![Pod Identityのフロー。EKS APIのアソシエーションがServiceAccountをロールに対応付け、EKSがコンテナ認証情報用の変数と投影トークン（aud pods.eks.amazonaws.com）を注入します。SDKはノード上のPod Identity Agentを呼び出し、Agentはノードロールのeks-auth権限を使ってEKS AuthのAssumeRoleForPodIdentityを呼び出します。EKSはセッションタグ付きのロール認証情報を返します。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **Agentの設定。** クラスターごとに`eks-pod-identity-agent`アドオンを一度インストールします。Agentはノードのホストネットワーク上で動作するDaemonSetで、リンクローカルアドレス`169.254.170.23`（IPv6 `[fd00:ec2::23]`）のポート80と2703を使用します。EKS Auto Modeには組み込み済みです。
2. **ロールとアソシエーション。** ロールは、サービスプリンシパル`pods.eks.amazonaws.com`に対して`sts:AssumeRole`と`sts:TagSession`を信頼します。クラスターごとのプロバイダーは不要なため、信頼ポリシーを変更せずに同じロールを別のクラスターでも使えます。紐付けはEKS APIのアソシエーション（クラスター、namespace、ServiceAccount → ロール）で行い、Kubernetesオブジェクトにはアノテーションを付けません。
3. **Pod作成時の注入。** アソシエーションが設定されたServiceAccountを使う新しいPodには、EKSが`AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`と、audienceが`pods.eks.amazonaws.com`の投影トークンを注入します。
4. **認証情報の取得。** SDKはトークンをノード上のAgentに送信します。Agentはノードロールの`eks-auth:AssumeRoleForPodIdentity`権限（`AmazonEKSWorkerNodePolicy`の一部）を使ってEKS Authを呼び出します。EKS Authはトークンとアソシエーションを検証し、ロールを引き受けて、`eks-cluster-arn`、`kubernetes-namespace`、`kubernetes-service-account`などのセッションタグ付き認証情報を返します。ノードロールに残すのは、AgentがEKS Authを呼び出すために必要な権限だけです。アプリケーションの業務権限はPod Identityロールに設定します。[Pod Identityの仕組み](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSAとPod Identityの比較

AWSは、可能な場合はEKS Pod Identityを推奨しています。IRSAも、一部のランタイムやチーム構成では引き続き適しています。[AWSによる比較](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| 属性 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| クラスターごとの設定 | クラスターごとにIAM OIDCプロバイダーを登録 | クラスターごとにPod Identity Agentアドオンを設定（Auto Modeには組み込み済み） |
| 紐付けの保存場所 | Kubernetes ServiceAccountのアノテーション | EKS APIのアソシエーション（Kubernetesオブジェクトの変更なし） |
| 信頼ポリシー | `aud`/`sub`条件付きの`Federated` OIDCプロバイダー。ロールごとにクラスターあたり1つのステートメントを追加 | プリンシパルは`pods.eks.amazonaws.com`の1つ。新しいクラスターでも変更不要 |
| スケール上限 | アカウントあたりデフォルトでOIDCプロバイダー100個。デフォルトの信頼ポリシー上限2,048文字では、通常、ロールあたり約4つの紐付けが上限 | クラスターあたり5,000件のアソシエーション。ロールの信頼ポリシーは増えない |
| 認証情報の経路 | Pod → リージョナルSTS（PodがSTS APIクォータを使用） | Pod → ノードAgent → EKS Auth（PodはSTSを呼び出さない） |
| セッション情報 | ロールのセッション名。セッションタグなし | クラスター、namespace、ServiceAccountのセッションタグによりABAC（属性ベースのアクセス制御）が可能 |
| ランタイム | EC2上のEKSとFargate、EKS Anywhere、ROSA、EC2上のセルフマネージドKubernetes | EKSのLinux EC2ノードのみ。Fargate、Windows、Outposts、EKS Anywhereには非対応 |
| クロスアカウント | 移行先アカウントのロールがこのクラスターのOIDCプロバイダーを信頼 | アソシエーションのロールはクラスターのアカウントに配置。移行先ロールまたはロールチェーンで委任 |
| 職務分掌 | IAM管理者がOIDCプロバイダーを作成し、クラスター運用者がアノテーションを設定 | IAMはロールのみを管理し、紐付けはEKS APIに保存 |

要するに、EC2上の新しいEKSワークロードでは、Pod Identityのほうがシンプルでスケールしやすいです。FargateやWindowsノードを使う場合、またはEKS以外のKubernetesでも同じ設定を実行する必要がある場合は、IRSAを使います。1つのクラスターで両方を使うこともできます。1つのServiceAccountにIRSAアノテーションとアソシエーションの両方が設定されている場合、EKS webhookは新しいPodにPod Identityの変数だけを注入し、IRSAの変数は注入しません。デモクラスターでは、アノテーションだけの状態で`kubectl create --dry-run=server`を実行すると`AWS_ROLE_ARN`と`AWS_WEB_IDENTITY_TOKEN_FILE`が返され、アソシエーションを追加すると`AWS_CONTAINER_CREDENTIALS_FULL_URI`と`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`だけが返されました。実行中のPodは再作成されるまでIRSA変数を保持するため、ロールアウトで切り替え、使わなくなったアノテーションを削除してください。

プライベートクラスターでは、IRSA PodからリージョナルSTSへ、またPod Identity AgentからEKS Auth（`eks-auth`）へ、それぞれ安全な経路を確保してください。インターネット経路がない場合は、対応するVPCインターフェイスエンドポイント、DNS、セキュリティグループを確認します。プロキシの背後では、`169.254.170.23`と`[fd00:ec2::23]`を`NO_PROXY`に追加してください。[Pod Identityに関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [プライベートクラスターの要件](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 本番クラスターでの移行順序

1. **依存関係を棚卸しする。** ノードロールのポリシーと、CloudTrailに実際に記録されるIAMセッションを比較し、Deployment、StatefulSet、DaemonSet、CronJob、コントローラーが呼び出すAWS APIを一覧にします。CloudTrailでS3オブジェクトへのアクセスを確認するには、そのバケットでデータイベントを有効にする必要があります。ノード登録とPod Identity Agentのために`AmazonEKSWorkerNodePolicy`を維持し、Amazon ECR（Elastic Container Registry）からのイメージ取得のために`AmazonEC2ContainerRegistryPullOnly`（または同等のポリシー）を維持します。VPC CNI（Container Network Interface）の`AmazonEKS_CNI_Policy`は専用の`aws-node`ロールに移せます。ノードロールから削除する前に、CNIの認証情報と新しいPodへのIP割り当てを確認してください。[EKSノードIAMロール](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3のCloudTrailイベント](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **ワークロードごとに、範囲を限定したIAMロールと専用のServiceAccountを作成する。** IRSAの場合は、クラスターの発行者をIAM OIDCプロバイダーとして登録し、audienceとsubjectを正確に確認するロールを作成して、ServiceAccountに`eks.amazonaws.com/role-arn`を設定します。Pod Identityの場合は、Agentの準備状態とノードのEKS Auth権限を確認し、リクエストタグで範囲を限定したロールとのアソシエーションを作成します。コンピューティング環境とSDKの対応状況を確認してください。[IRSAのSDKバージョン](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod IdentityのSDKバージョン](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **カナリアPodを作成する。** Podテンプレートの`serviceAccountName`を変更するか、新しいPodをロールアウトしてから、注入された変数名、実行中プロセスの呼び出し元ARN、必要なAWS APIを確認します。トークンやキーをログに記録してはいけません。明示的に指定された認証情報や、デフォルトチェーン内で先に評価されるプロバイダーが優先される場合があります。[デフォルト認証情報プロバイダーチェーン](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **ワークロードを1つずつ切り替える。** エラー率、`AccessDenied`、トークンと認証情報の更新、スケジュール実行を監視します。ワークロードがノードロールの業務権限に依存しなくなったら、そのポリシーステートメントだけを削除します。ロールバック期間中は、以前のPodテンプレートとノードポリシーの正確なコピーを保持します。権限を削除した後にロールバックする場合は、まず最小限のポリシーを復元して、反映を確認してから以前のPodをデプロイします。
5. **ノード認証情報へのアクセスを制限する。** 互換性を確認済みのノードグループから始めて、IMDSv2を強制し、通常のPodからのIMDSアクセスを制限します。カスタム起動テンプレートを使うマネージドノードグループでは、新しいテンプレートバージョンで`HttpTokens=required`と`HttpPutResponseHopLimit=1`を設定し、ノードをロールします。Karpenterでは`EC2NodeClass.spec.metadataOptions`を使用します。EKS Auto Modeでは、IMDSv2とホップ制限1がデフォルトで強制されます。`hostNetwork`を使うPodはホップ制限に関係なくIMDSに到達できるため、別途制御してください。IMDSを無効に（`HttpEndpoint=disabled`に）してはいけません。Pod Identity Agent自体がホストネットワーク上で動作し、EKS Authを呼び出すためにIMDSからノードロールの認証情報を取得するからです。[マネージドノードグループの起動テンプレート](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAMのベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>信頼ポリシーとカナリア用コマンド</summary>

IRSAロールの信頼ポリシーでは、クラスターの発行者とServiceAccountの範囲を限定します。`<OIDC_ISSUER>`には`https://`を除いた発行者を指定してください。

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

Pod IdentityロールはEKSサービスプリンシパルを信頼します。以下の条件は、セッションタグを使ってクラスター、namespace、ServiceAccountの範囲を限定します。そのため、アソシエーションではセッションタグを有効にしておいてください。

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
## ライブデモ：1つのアプリの3つのコピーを移行する

![デモのフロー。最初はordersアプリの3つのコピーすべてがIMDSからノードロールを取得してS3を読み込みます。migrate-irsaの後、1つのコピーがSTSからIRSAロールを取得します。migrate-podidの後、別のコピーがAgent経由でPod Identityロールを取得します。revokeでノードロールのS3権限を削除すると、レガシーのコピーだけが拒否されます。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

このデモでは、既存のEKS 1.36クラスターに専用のマネージドノードグループ（t3.medium、プライベートサブネット、taint付き）を1つ追加し、その上で同じordersアプリのコピーを3つ実行します。各コピーは3秒ごとにSTSの`GetCallerIdentity`とS3の`GetObject`を呼び出し、認証情報の取得元、ロール名、S3の結果を含むJSON行を1行出力します。開始時の状態はクラスターの本番ノードグループに合わせてあり、IMDSv2が必須、ホップ制限は2、ノードロールにはアプリの`s3:GetObject`が設定されています。レガシーPodはhost networkingを使わない通常のPodです。[デモコードと発表者用手順書](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [スライド（韓国語）](https://presentation.atomai.click/eks-workload-identity/)

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

`page-up`を使うと、読み取り専用のライブページを参加者と共有できます。経路はCloudFront → VPCオリジン → 内部ALB → ダッシュボードPodで、ALBのセキュリティグループが許可するのはCloudFront VPCオリジンだけです。ダッシュボードPodにはIAMロールがなく、このnamespace内のPodとログを読み取るRoleだけがあります。また、デモ用ノードのホップ制限は2のため、NetworkPolicyによってIMDSやPod Identity Agentへのアクセスを阻止します。この分離にはVPC CNIのネットワークポリシー適用（`enableNetworkPolicy`）が必要で、`page-up`は最初にこれを確認します。

スクリプトが作成するすべてのリソースには、名前か`LabRun`タグに実行IDが含まれます。スクリプトが変更または削除するのは、その名前かタグに一致するリソースだけです。VPC、サブネット、アドオン、OIDCプロバイダーは作成せず、存在確認のみを行います。作成される唯一のセキュリティグループは、オプションの`page-up`が内部ALB用に作成するものです。[ハンズオンラボ](../labs/security/17-eks-workload-identity-migration-lab.md)では、各手順をコマンド、期待される出力、チェックポイントとともに説明します。

### ソウルリージョンでの測定結果

2026年11月21日、`ap-northeast-2`のEKS 1.36クラスターで、Pod内のAWS CLI 2.35.11を使って2回リハーサルを行いました。1回目はPod Identityの注入に失敗したため（下記参照）、スクリプトを修正しました。この表は、修正済みスクリプトを使って最初から最後まで実行した2回目のリハーサルの結果です。`harden`の結果だけは1回目のリハーサルから取っています。

| 手順 | orders-legacy | orders-irsa | orders-podid | 所要時間 |
| --- | --- | --- | --- | --- |
| 開始時 | IMDS · ノードロール · 読み取り許可 | IMDS · ノードロール · 読み取り許可 | IMDS · ノードロール · 読み取り許可 | — |
| `migrate-irsa` | 変更なし | STS · IRSAロール · 読み取り許可 | 変更なし | 6秒 |
| `migrate-podid` | 変更なし | 変更なし | Agent · Pod Identityロール · 読み取り許可 | 11秒（アソシエーション作成後、注入が確認できるまでの5秒を含む） |
| `revoke` | ノードロール · **読み取り拒否** | 読み取り許可 | 読み取り許可 | 13秒後に拒否 |
| `harden`（オプション、1回目のリハーサル） | **認証情報なし**（IMDSレスポンスを遮断） | 読み取り許可 | 読み取り許可 | ノードのロールアウトに878秒 |

`diff`では、2つの違いを確認できます。どちらのトークンも同じクラスター発行者によって署名されたServiceAccountトークンですが、audienceと受信側が異なります。

| 比較項目 | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| 注入される変数 | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` |
| トークンの`aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| トークンの`sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| トークンの有効期間 | 86,400秒（24時間） | 約22～24時間（webhookがばらつきを加える。測定値は79,636秒と86,171秒） |
| ロールの信頼プリンシパル | `Federated`：クラスターのOIDCプロバイダー。`aud`と`sub`の条件付き | `Service`：`pods.eks.amazonaws.com`。3つのリクエストタグ条件付き |

リハーサルでは、2つの結果整合性の影響が明らかになりました。1つ目は、1回目のリハーサルで、アソシエーション作成直後にロールアウトされたPodにPod Identityの変数がなく、ノードロールを使い続けたため、ノードポリシーを削除した後にそのPodも拒否されたことです。そのため、`migrate-podid`はDeploymentのPodテンプレートを`kubectl create --dry-run=server`に渡して、変更Webhookが何を注入するか確認してからロールアウトします。2回目のリハーサルでは、アソシエーションの作成後5秒で注入が確認できました。2つ目は、1回目のリハーサルで`revoke`を実行した後、レガシーPodは13秒以内に拒否されたものの、その約4.5分後に許可された読み取りがさらに2回記録されたことです。その直後に確認した1分間の読み取り11回は、すべて拒否されました。本番環境では、ノードポリシーの削除後、結論を出す前に数分間監視を続けてください。

## トラブルシューティング

- **ノードロールが使われている。** Podが新しいこと、正しいServiceAccountを参照していること、IRSAアノテーションまたは正確なアソシエーションが設定されていることを確認します。SDKのバージョン、デフォルトのプロバイダーチェーン、注入された変数名を調べます。
- **IRSAのトークン交換に失敗する。** IAMプロバイダーにトークン発行者が設定されていること、`aud`/`sub`の信頼条件、STSへの接続性を確認します。
- **Pod Identityの認証情報取得に失敗する。** 該当ノード上のAgent、EKS Authへの接続性、ノードのIAM権限、アソシエーションの反映、ロールのリクエストタグ信頼条件を確認します。アソシエーションは作成後、反映まで数秒かかることがあります。
- **想定したロールでS3へのアクセスが拒否される。** IDベースのアクセスとリソースベースのアクセスは別々です。オブジェクトARN、バケットポリシー、SCP（Service Control Policies）、アクセス許可の境界、VPCエンドポイントポリシーを確認します。AWS KMS（Key Management Service）キーで暗号化されたオブジェクト（SSE-KMS）の場合は、キーに対するアクセス許可も確認します。
