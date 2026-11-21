# EKS ワークロード IAM 移行ラボ：ノードロールから IRSA と Pod Identity へ

> **難易度**：上級
> **所要時間の目安**：40～60 分（`harden` を実行する場合は約 30 分追加）
> **対応バージョン**：Amazon EKS 1.36、AWS CLI 2.35.11（Pod 内）で検証済み
> **最終更新日**：2026年11月21日

## 学習目標

- 同じ orders アプリの 3 つのコピーを、すべてノード IAM ロールを使う状態から始め、1 つを IRSA に、もう 1 つを EKS Pod Identity に移行します。
- 2 つの方法で、注入される環境変数、トークン、ロールの信頼ポリシーがどう異なるかを実際に確認します。
- ノードロールから S3 権限を取り消し、移行していない Pod だけが拒否される様子を確認し、IAM と関連付けの結果整合性を観察します。
- （任意）IMDS のホップ制限を 1 に下げて、通常の Pod からノード認証情報を取得できる経路を閉じます。
- サーバーサイドのドライランを使って、1 つの ServiceAccount に IRSA アノテーションと Pod Identity の関連付けの両方がある場合に、新しい Pod が何を受け取るかを確認します。

このラボでは、[EKS ノード IAM 権限を IRSA と Pod Identity に移行する](../../security/17-eks-workload-identity-migration.md)の[ライブデモ](../../security/17-eks-workload-identity-migration.md#live-demo)を、手順を追って実施します。最初にワークブックの[IRSA のフロー](../../security/17-eks-workload-identity-migration.md#irsa-flow)と[Pod Identity のフロー](../../security/17-eks-workload-identity-migration.md#pod-identity-flow)のセクションを読んでください。

## 所要時間とコスト

| 手順 | 実測時間 | 備考 |
| --- | --- | --- |
| `up` | 174 秒（実行 `t1121`） | 主にノードグループの作成。環境によって 3～5 分 |
| `migrate-irsa` | 6 秒 | |
| `migrate-podid` | 11 秒 | 関連付けが Admission に反映されるまでの 5 秒を含む |
| `diff` | 8 秒 | 読み取り専用 |
| `revoke` | 最初の `denied` まで 13 秒 | コマンドは 17～18 秒後に終了 |
| `harden`（任意） | 878 秒 | ノードグループをローリング置換 |
| `restore` | 15 秒、`harden` 後は 578 秒 | 繰り返し練習する場合に使用 |
| `down` | 323 秒（実行 `t1121`） | 主にノードグループの削除 |

コストの大半は、t3.medium のオンデマンドインスタンス 1 台（ソウルで 1 時間あたり 0.052 米ドル）と、20 GiB の gp3 ボリュームです。ラボを 1 時間実行した場合の費用は約 0.06 米ドルで、S3 リクエストと API 呼び出しの費用は無視できる程度です。任意の公開デモページを使うと、ALB の費用として 1 日あたり約 0.55 米ドルが追加されます。終了したら、必ず `down` でリソースをクリーンアップしてください。

## 前提条件

- [ ] **既存の EKS クラスター**（1.36 で検証済み）。基本のデモでは、クラスター、VPC、サブネット、セキュリティグループは作成しません（任意の `page-up` のみ、内部 ALB 用のセキュリティグループを 1 つと、`PAGE_DOMAIN` の DNS レコードを作成します）。クラスターの vpc-cni がノードロールで動作する一般的な構成を前提とします。
- [ ] **`eks-pod-identity-agent` アドオン**がインストール済みであること。スクリプトはアドオンの有無を確認するだけで、インストールはしません。
- [ ] クラスターの Issuer が**IAM OIDC プロバイダー**として登録されていること。これもスクリプトでは作成しません。
- [ ] クラスターの VPC 内にある**プライベートサブネット**と、それらの Name タグ。`MapPublicIpOnLaunch=false` のサブネットのみ受け付けます。ノードは VPC に既存の NAT 経路を通じて `public.ecr.aws/aws-cli/aws-cli` を取得します。
- [ ] ツール：AWS CLI v2、kubectl、jq、bash、git。
- [ ] 権限：EKS、EC2（起動テンプレート）、IAM、S3 の権限と、クラスターへの cluster-admin アクセスを持つ認証情報。一時認証情報を使用し、長期アクセスキーは使わないでください。

### 事前確認コマンド

```bash
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>

aws sts get-caller-identity --query Arn --output text
aws eks describe-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent \
  --query addon.status --output text                       # ACTIVE
ISSUER=$(aws eks describe-cluster --name "$CLUSTER" \
  --query cluster.identity.oidc.issuer --output text | sed 's#^https://##')
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
  "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${ISSUER}" --query ClientIDList   # ["sts.amazonaws.com"]
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)
aws eks describe-cluster --name "$CLUSTER" --query cluster.resourcesVpcConfig.vpcId --output text  # must equal $VPC_ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$SUBNET_NAMES" \
  --query 'Subnets[].[Tags[?Key==`Name`]|[0].Value,SubnetId,MapPublicIpOnLaunch]' --output table
```

アドオンが `ACTIVE` であること、OIDC プロバイダーの参照が成功すること、クラスターの VPC ID が `VPC_NAME` で検出した VPC と一致すること、そして各サブネットの `MapPublicIpOnLaunch` が `False` であることを確認してください。いずれかの確認に失敗すると、`up` は何も作成する前に停止します。

### コードと環境ファイル

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs/examples/security/eks-workload-identity

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/env" <<'EOF'
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER>
export VPC_NAME=<Name tag of the cluster VPC>
export SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
EOF

export RUN_ID=lab01     # 4–12 lowercase letters or digits; goes into resource names wid-<RUN_ID>-*
export NS="wid-$RUN_ID"
export KUBECONFIG="$STATE_DIR/kubeconfig-$RUN_ID"   # the dedicated kubeconfig demo.sh writes
```

`demo.sh` は実行のたびにこの環境ファイルを読み込むため、別のターミナルで実行する `watch` も同じ値を使います。このファイルはシェル変数を設定した後に読み込まれるので、同名のシェル変数よりもファイル内の値が優先されます。以下で `kubectl` を直接実行するときは、別のクラスターコンテキストにコマンドが接続しないよう、上記の `KUBECONFIG` を使ってください。このファイルは `up` を初めて実行したときに作成されます。

スクリプトが表示するコマンドと結果では、アカウント ID、OIDC Issuer ID、クラスター名、起動テンプレート ID が、それぞれ `<ACCOUNT_ID>`、`<OIDC_ID>`、`<CLUSTER>`、`<LAUNCH_TEMPLATE_ID>` としてマスクされます。以下の想定出力も同じようにマスクされています。これらは 2026年11月21日にソウルリージョンで実施したリハーサルの結果で、各ブロックには実行 ID（`d1124` または `t1121`）を記載しています。実際の画面には、自分の `RUN_ID` とタイムスタンプが表示されます。

## ステップ 0：ラボ環境をデプロイする（`up`）

**コマンド**（ターミナル A）

```bash
./demo.sh up "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`、174 秒）

```text
==> bucket and test object
==> node role (with the app's S3 permission, the legacy pattern)
==> IRSA and Pod Identity roles
==> creating node group wid-t1121 (3–5 min)
==> namespace, ServiceAccounts and three copies of the orders app
Waiting for deployment "orders-legacy" rollout to finish: 0 of 1 updated replicas are available...
deployment "orders-legacy" successfully rolled out
deployment "orders-irsa" successfully rolled out
deployment "orders-podid" successfully rolled out
==> ready. In a second terminal run: ./demo.sh watch t1121
```

**確認項目**

```bash
./demo.sh status "$RUN_ID"
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `status` には、ノードグループが `ACTIVE t3.medium lt-version=1`、3 つのロール（`wid-<RUN_ID>-node`、`-irsa`、`-podid`）すべてにインラインポリシー `OrdersReadInvoices` が設定済み、バケットが `present`、`pod-id 0 association(s)`、`irsa SA (not annotated)`、3 つの Pod が `Running` と表示されます。
- 起動テンプレートの `MetadataOptions` は `HttpTokens: required`、`HttpPutResponseHopLimit: 2`、`HttpEndpoint: enabled` です。

**理由。** `up` は、本番用ノードグループと同じ開始状態を構築します。IMDSv2 は必須ですが、ホップ制限が 2 の場合、ホストネットワークを使用しない通常の Pod でも IMDS トークンとノードロールの認証情報を取得でき、そのノードロールにはアプリの `s3:GetObject` 権限があります。IRSA と Pod Identity のロールはあらかじめ作成されますが、この時点ではどの ServiceAccount にも関連付けられていません。

## ステップ 1：開始状態を確認する（`watch`）

**コマンド**（同じディレクトリのターミナル B）

```bash
export RUN_ID=lab01
./demo.sh watch "$RUN_ID"     # refreshes every 2 s; Ctrl-C to stop
```

**想定画面**（実測、実行 `d1124`）

```text
04:11:37 EKS workload identity — <CLUSTER>/wid-d1124  (Ctrl-C to stop)

COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36
orders-irsa     node (IMDS)    wid-d1124-node  ← node       allowed   04:11:35
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36

node role: wid-d1124-node   bucket object: invoices/2026-11.txt
```

**確認項目。** 3 行すべてに `node (IMDS)`、`wid-<RUN_ID>-node ← node`、`allowed` と表示され、`AT` の時刻が 3 秒ごとに更新されます。画面には、各コピーの最新 Pod の最新ログ行が表示されます。ターミナル A では、生の JSON を確認できます。

```bash
kubectl -n "$NS" logs deploy/orders-legacy --tail=3
# format: {"t":"HH:MM:SS","src":"imds","role":"wid-<RUN_ID>-node","s3":"allowed"}
```

**理由。** 3 つの Pod のいずれにも認証情報の環境変数が注入されていないため、AWS CLI のデフォルトのプロバイダーチェーンは最後の手段である IMDS に進み、ノードロールを取得します。`app.sh` は、`AWS_WEB_IDENTITY_TOKEN_FILE` または `AWS_CONTAINER_CREDENTIALS_FULL_URI` が存在するかどうかに基づいて `src` を設定し、`sts get-caller-identity` の ARN からロール名を取得します。トークンやキーは出力しません。

## ステップ 2：IRSA に移行する（`migrate-irsa`）

**コマンド**（ターミナル A）

```bash
./demo.sh migrate-irsa "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`、6 秒）

```text
==> IRSA: point the ServiceAccount at its own role, then restart the copy
$ kubectl -n wid-t1121 annotate serviceaccount orders-irsa --overwrite eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-irsa
$ kubectl -n wid-t1121 rollout restart deployment/orders-irsa
$ kubectl -n wid-t1121 rollout status deployment/orders-irsa --timeout=180s
Waiting for deployment "orders-irsa" rollout to finish: 1 old replicas are pending termination...
deployment "orders-irsa" successfully rolled out
```

ターミナル B では `orders-irsa` の行が `IRSA (STS)`、`wid-<RUN_ID>-irsa`、`allowed` に変わり、ほかの 2 行は変わりません（実測、実行 `d1124`）。

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:59
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:01
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:12:00
```

**自分で確認する。** Kubernetes オブジェクトで何が変わったかを確認します。

```bash
# 1) The ServiceAccount annotation
kubectl -n "$NS" get sa orders-irsa \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# 2) Names of the environment variables the webhook added to the new Pod (no values)
POD=$(kubectl -n "$NS" get pod -l app=orders,track=irsa \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'

# 3) The projected token mount path
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].volumeMounts[*]}{.mountPath}{"\n"}{end}'
```

**確認項目**

- アノテーションは `arn:aws:iam::<ACCOUNT_ID>:role/wid-<RUN_ID>-irsa` です。
- マニフェスト独自の `BUCKET`、`KEY`、`AWS_REGION` などに加え、変数一覧に Webhook が追加した `AWS_STS_REGIONAL_ENDPOINTS`、`AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE` が表示されます。
- マウントパスに `/var/run/secrets/eks.amazonaws.com/serviceaccount` が追加されています。
- `orders-legacy` と `orders-podid` の Pod にはこれらの変数がありません。

**理由。** EKS Mutating Webhook は、**Pod の作成時に** ServiceAccount の `eks.amazonaws.com/role-arn` アノテーションを読み取り、環境変数とトークンボリュームを追加します。実行中の Pod は変化しないため、スクリプトはアノテーションを付けた直後に `rollout restart` を実行します。新しい Pod では、AWS CLI はプロバイダーチェーンで IMDS より前に位置する Web Identity トークンプロバイダーを見つけ、STS の `AssumeRoleWithWebIdentity` を通じて IRSA ロールを取得します。

## ステップ 3：Pod Identity に移行する（`migrate-podid`）

**コマンド**（ターミナル A）

```bash
./demo.sh migrate-podid "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`、11 秒）

```text
==> Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart
$ aws eks create-pod-identity-association --cluster-name <CLUSTER> --namespace wid-t1121 --service-account orders-podid --role-arn arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-podid --tags Lab=eks-workload-identity-demo\,LabRun=t1121 --query association.associationId --output text
==> waiting for the association change to reach Pod admission (eventually consistent)
    2s  not yet   injected after 5s
$ kubectl -n wid-t1121 rollout restart deployment/orders-podid
$ kubectl -n wid-t1121 rollout status deployment/orders-podid --timeout=180s
Waiting for deployment "orders-podid" rollout to finish: 1 old replicas are pending termination...
deployment "orders-podid" successfully rolled out
```

ターミナル B では `orders-podid` の行が `Pod Identity`、`wid-<RUN_ID>-podid`、`allowed` に変わります（実測、実行 `d1124`）。

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:12:27
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:29
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:27
```

**自分で確認する**

```bash
# The association lives in the EKS API; the ServiceAccount has no annotation
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" \
  --query 'associations[].[serviceAccount,associationId]' --output text
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'

POD=$(kubectl -n "$NS" get pod -l app=orders,track=podid \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'
```

**確認項目**

- `orders-podid` の関連付けが 1 つあり、ServiceAccount のアノテーションは空です。
- 新しい Pod には `AWS_STS_REGIONAL_ENDPOINTS`、`AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` があります。
- 出力の `injected after Ns` は、関連付けを作成してから Admission が注入するまでにかかった時間です。2 回のリハーサルでは、どちらも 5 秒でした。

**注入を待つ理由。** 関連付けの反映には結果整合性があります。最初のリハーサルでは、関連付けの作成直後に行ったロールアウトで Pod Identity の環境変数がない Pod が作成され、その Pod はノードロールを使い続けました。そのためスクリプトは、Deployment の Pod テンプレートを `kubectl create --dry-run=server` に渡し、Mutating Webhook が実際に変数を注入するまでロールアウトしません。サーバーサイドのドライランでは何も保存されませんが、実際の Pod と同じ Admission 手順を通過するため、この確認に最適です。

## ステップ 4：2 つの方法を比較する（`diff`）

**コマンド**

```bash
./demo.sh diff "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`）

```text
1. What EKS injected into each new Pod (env var names)
  irsa   AWS_STS_REGIONAL_ENDPOINTS, AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
  podid  AWS_STS_REGIONAL_ENDPOINTS, AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE

2. The projected ServiceAccount token (claims only)
  irsa   {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["sts.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-irsa","lifetime_s":86400}
  podid  {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-podid","lifetime_s":79636}

3. Who each role trusts
  irsa             {"principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>"},"action":"sts:AssumeRoleWithWebIdentity","conditions":["<issuer>:aud","<issuer>:sub"]}
  podid            {"principal":{"Service":"pods.eks.amazonaws.com"},"action":["sts:AssumeRole","sts:TagSession"],"conditions":["aws:RequestTag/eks-cluster-arn","aws:RequestTag/kubernetes-namespace","aws:RequestTag/kubernetes-service-account"]}

4. Where the SDK goes for credentials
  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials
  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials
  legacy Pod → IMDSv2 169.254.169.254 → node role credentials

5. Wiring lives in
  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub
  podid  EKS association (1 found) + one service principal trust, reusable across clusters
```

**出力の読み方**

- **1**：どちらの方法も新しい Pod に環境変数を追加しますが、変数名は異なります。IRSA はロール ARN とトークンファイルを渡し、SDK が STS を呼び出します。Pod Identity はロール ARN を渡さず、認証情報 URI と認可トークンファイルのみを渡します。Pod に割り当てるロールは関連付けによって決まります。
- **2**：どちらのトークンも、同じクラスター Issuer が署名した ServiceAccount トークンで、`sub` の形式も同じです。異なるのは `aud` です。`sts.amazonaws.com` トークンを受け入れるのは STS のみで、`pods.eks.amazonaws.com` トークンを受け入れるのは EKS Auth のみです。Pod Identity トークンの有効期間は実行ごとに異なります。これは Webhook がランダムなジッターを加えるためです（実測値は 79,636 秒と 86,171 秒）。
- **3**：IRSA ロールは `aud` と `sub` の条件を持つクラスターごとの OIDC プロバイダーを信頼するため、クラスターが増えるたびに信頼ポリシーも増えます。Pod Identity ロールはセッションタグ条件付きの 1 つのサービスプリンシパルを信頼するため、別のクラスターで信頼ポリシーを変更する必要がありません。
- **4～5** はスクリプトが出力する固定の説明文です。項目 5 の `1 found` のみ、実際の関連付け数を表します。

**理由。** 2 つの方法の違いは、誰がトークンを受け取り、それをロールに変換するかです。IRSA では Pod が直接 STS にアクセスし、STS は OIDC プロバイダーを通じて署名を検証します。Pod Identity では同じノード上の Agent が EKS Auth に要求し、EKS Auth が関連付けを特定してセッションタグ付きの認証情報を返します。

## ステップ 5：ノードロールの権限を取り消す（`revoke`）

**コマンド**

```bash
./demo.sh revoke "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`、最初の `denied` まで 13 秒）

```text
==> remove the app's S3 permission from the node role
$ aws iam delete-role-policy --role-name wid-t1121-node --policy-name OrdersReadInvoices
==> waiting for IAM to propagate: legacy copy should flip to denied
    1s  legacy still: allowed     5s  legacy still: allowed     9s  legacy still: allowed   legacy denied after 13s
  orders-irsa   allowed via wid-t1121-irsa
  orders-podid  allowed via wid-t1121-podid
```

ターミナル B（実測、実行 `d1124`。`revoke` の直後と 60 秒後で同じ状態）：

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```

**確認項目**

- `denied` になるのは `orders-legacy` のみで、ロールは引き続きノードロールです。認証情報は取得していますが、そのロールには権限がなくなっています。
- IRSA と Pod Identity のコピーは `allowed` のままです。アプリケーション権限をノードロールに依存しなくなったことが確認できます。
- その後数分間、遅れて `allowed` となった読み取りがないかログを確認してください。

```bash
kubectl -n "$NS" logs deploy/orders-legacy --since=10m | jq -r 'select(.s3=="allowed") | .t' | tail -n 3
```

**理由。** IAM ポリシーの変更は結果整合性を伴って反映されます。どちらのリハーサルでも最初の拒否は 13 秒後でしたが、最初のリハーサルではその約 4.5 分後に `allowed` の読み取りがさらに 2 回発生しました。`revoke` は最初の `denied` が確認された時点で終了するため、本番環境ではノードポリシーを削除した後、判断する前に数分間監視を続けてください。

## ステップ 6（任意）：IMDS 経路を閉じる（`harden`）

実測で 878 秒、約 15 分かかります。`revoke` の直後に開始し、ステップ 7 に進んでもかまいません。

**コマンド**

```bash
./demo.sh harden "$RUN_ID"
./demo.sh status "$RUN_ID"      # in another terminal: nodegroup UPDATING → ACTIVE
```

**想定出力**（実測、実行 `d1124`、878 秒）。スクリプトはノードグループを新しい起動テンプレートバージョンに更新し、完了するまで 15 秒ごとにドットを表示します。

```text
==> block Pod access to IMDS on the demo node group (hop limit 1)
$ aws eks update-nodegroup-version --cluster-name <CLUSTER> --nodegroup-name wid-d1124 --launch-template id=<LAUNCH_TEMPLATE_ID>\,version=2 --query update.id --output text
...
deployment "orders-legacy" successfully rolled out
==> legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected
```

置換後の各コピーの最新ログ行（実測、実行 `d1124`）：

```text
legacy: {"t":"04:00:27","src":"imds","role":"no-credentials","s3":"no-creds"}
irsa: {"t":"04:00:26","src":"irsa","role":"wid-d1124-irsa","s3":"allowed"}
podid: {"t":"04:00:27","src":"pod-identity","role":"wid-d1124-podid","s3":"allowed"}
```

**確認項目**

```bash
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `HttpPutResponseHopLimit` は `1` で、`HttpEndpoint` は引き続き `enabled` です。
- `orders-legacy` は認証情報をまったく取得できず（`no-credentials` / `no-creds`）、ほかの 2 つのコピーは新しいノード上でも `allowed` のままです。

**理由。** ホップ制限が 1 の場合、IMDSv2 のトークン応答はノードのネットワーク名前空間から Pod へは届かないため、通常の Pod はノードロールの認証情報を取得できません。**IMDS を無効にしないでください（`HttpEndpoint=disabled`）。** Pod Identity Agent はホストネットワーク上で動作し、EKS Auth を呼び出すために IMDS からノードロールの認証情報を取得します。IMDS を無効にすると、`orders-podid` も認証情報を失います。hostNetwork Pod はホップ制限にかかわらず IMDS に到達するため、別途制御してください。

`harden` 後に `restore` または `down` を実行する前に、ノードグループが再び `ACTIVE` になるまで待ってください。`harden` 後の `restore` はホップ制限を 2 に戻し、実測で約 10 分（578 秒）かかります。

## ステップ 7：実験 — IRSA アノテーションと関連付けを併用する

ワークブックには、1 つの ServiceAccount に IRSA アノテーションと関連付けの両方がある場合、EKS Webhook は新しい Pod に Pod Identity の環境変数のみを注入するとあります。ステップ 3 の後に自分で確認してください。`orders-irsa` には関連付けを作成しないでください。スクリプトの `restore` と `down` が削除するのは `orders-podid` の関連付けだけなので、`orders-irsa` の関連付けは残ってしまいます。代わりに、すでに関連付けがある `orders-podid` に一時的に IRSA アノテーションを追加します。

**7.1 注入結果を表示する関数** — `demo.sh` の `podid_injected()` と同じように、Deployment の Pod テンプレートをサーバーサイドのドライランに渡します。

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

injected() { # deployment name
  kubectl -n "$NS" get deployment "$1" -o json |
    jq --arg n "probe-$RUN_ID" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
    kubectl -n "$NS" create --dry-run=server -o json -f - |
    jq -r '[.spec.containers[0].env[]?.name
            | select(test("^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|CONTAINER_)"))] | join(", ")'
}
```

**7.2 基準状態：アノテーションのみの ServiceAccount と、関連付けのみの ServiceAccount**

```bash
injected orders-irsa     # expected (from diff output and coexistence.log): AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.3 関連付けのある `orders-podid` に IRSA アノテーションを追加して、再度ドライランを実行する**

```bash
kubectl -n "$NS" annotate sa orders-podid \
  "eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/wid-${RUN_ID}-irsa"
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.4 クリーンアップ：アノテーションを削除し、ロールアウトは行わない**

```bash
kubectl -n "$NS" annotate sa orders-podid eks.amazonaws.com/role-arn-
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'   # should be empty
```

**確認項目。** 7.3 で `AWS_ROLE_ARN` がなく、Pod Identity の環境変数だけが表示されれば、結果はワークブックの記述と一致します。2026年11月21日の実行 `d1124` での実測値：アノテーションのみの場合は `AWS_ROLE_ARN` と `AWS_WEB_IDENTITY_TOKEN_FILE`。関連付けを追加して 5 秒後には `AWS_CONTAINER_CREDENTIALS_FULL_URI` と `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` のみ。両方を削除して 2 秒後には何も表示されません。ドライランでは Pod が作成されないため、実行中の `orders-podid` には影響しません。

**理由。** 関連付けがある ServiceAccount では、IRSA アノテーションが存在していても EKS Webhook は Pod Identity の環境変数を優先し、IRSA の環境変数は注入しません。一方、後から関連付けを追加した場合、**すでに実行中の** Pod は再作成されるまで IRSA の環境変数を保持します。そのため方法を切り替えるときは、ロールアウトで Pod を再作成し、使用しないアノテーションを削除して、2 つの設定が混在しないようにしてください。

## 公開デモページ（任意）

これを実行すると、参加者がそれぞれのブラウザーで開ける読み取り専用のライブページが起動します。3 つのカードに、各コピーの認証情報ソース、ロール、S3 の結果、EKS が注入した `AWS_*` 変数名、最近の読み取りが表示されます。ページ上の操作によって何かが変更されることはありません。**URL を知っている人は誰でも閲覧できます**。表示されるのはロール名、Pod 名、注入された変数名、読み取り結果のみで、認証情報、トークン、アカウント ID、ARN は表示されません。

経路は CloudFront（HTTPS、GET/HEAD のみ、HTTP は HTTPS にリダイレクト）→ CloudFront VPC オリジン → **内部** ALB（HTTP 80）→ ダッシュボード Pod です。ALB のセキュリティグループで許可するのは、VPC の `CloudFront-VPCOrigins-Service-SG` のみです。このセキュリティグループがまだ存在しない場合は、CloudFront マネージドプレフィックスリスト（`com.amazonaws.global.cloudfront.origin-facing`）を許可します。インターネット向けロードバランサー、パブリック IP、パブリック CIDR ルールは作成されません。ダッシュボード Pod には IAM ロールがなく、その Role にはこの namespace 内の Pod 一覧取得と Pod ログの読み取りのみが設定されています。デモノードのホップ制限は 2 なので、NetworkPolicy によって Pod の送信を DNS と TCP 443（Kubernetes API）に制限し、IMDS や Pod Identity Agent に到達できないようにしています。

**追加の前提条件**：AWS Load Balancer Controller、VPC CNI のネットワークポリシーが有効（`enableNetworkPolicy`）であること、CloudFront VPC オリジンに対応した最新の AWS CLI v2、CloudFront VPC オリジンとディストリビューション、ELB、EC2 セキュリティグループ、Route 53 レコードの作成・削除権限、ACM 証明書の読み取り権限。環境ファイルに次の 3 つの値を追加してください。

```bash
export PAGE_DOMAIN=<page host name>
export PAGE_CERT_ARN=<ACM certificate ARN in us-east-1 covering PAGE_DOMAIN>
export PAGE_ZONE_ID=<public hosted zone ID for PAGE_DOMAIN>
```

**コマンド**

```bash
./demo.sh page-up "$RUN_ID"     # measured 446 s (mostly the VPC origin and distribution deployments)
./demo.sh status "$RUN_ID"      # page https://<PAGE_DOMAIN>/ (Deployed)
```

`PAGE_DOMAIN` に、この実行のディストリビューションを指していないレコードがすでにある場合、スクリプトは DNS を変更せずに停止します。`page-down` の後に `page-up` を実行すると、その間に名前を検索したリゾルバーは「名前が存在しない」という応答を、最大 15 分間キャッシュすることがあります（ホストゾーンの SOA ネガティブ TTL）。再作成の直後、作業ホストの VPC リゾルバーのみが NXDOMAIN を返し、権威 DNS サーバーとパブリックリゾルバーは正しく応答する状態が確認されました。約 10 分後には通常どおり名前解決されました。発表の直前にページを再作成しないでください。

**想定画面**（実測、実行 `d1124`。各ステップでスクリーンショットを確認）：タイトル行のステップ表示はデモの進行に合わせて変わります。開始時には「0 · 시작: 세 벌 모두 노드 역할」と表示され、3 枚のカードはすべて node (IMDS) です。`migrate-irsa` の後は orders-irsa のカードが IRSA に切り替わります。`migrate-podid` の後は orders-podid のカードが Pod Identity に切り替わり、注入された変数名が表示されます。`revoke` の後は orders-legacy のカードのみが赤色になり、`denied` と表示されます。

**確認項目。** カードの内容がターミナルの `watch` と一致し、画面上部の UTC 時刻が 2 秒ごとに更新されることを確認してください。ダッシュボード Pod から IMDS にアクセスできないことを確認するには、次を実行します。

```bash
P=$(kubectl -n "wid-$RUN_ID" get pod -l app=wid-dashboard -o name | head -1)
kubectl -n "wid-$RUN_ID" exec "$P" -- python3 -c "import urllib.request as u; u.urlopen(u.Request('http://169.254.169.254/latest/api/token', method='PUT', headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}), timeout=3)"
# measured: urllib.error.URLError (timed out) — blocked
```

**理由。** ダッシュボードは Kubernetes API から 2 秒ごとに状態を収集してメモリに保存し、`Cache-Control: max-age=1` を付けて応答します。CloudFront はこのヘッダーに従ってキャッシュするため、閲覧者が多くてもクラスター API への呼び出しは増えません。

**コストとクリーンアップ。** 起動中は ALB の費用として 1 日あたり約 0.55 米ドルが追加されます。`./demo.sh page-down "$RUN_ID"` で削除してください（実測 546 秒）。`down` を実行すると、最初にこの処理が行われます。何も残っていないことを確認するには、次を実行します。

```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='wid-$RUN_ID-page'].Id" --output text   # empty
aws cloudfront list-vpc-origins --query "VpcOriginList.Items[?Name=='wid-$RUN_ID-page'].Id" --output text         # empty
aws elbv2 describe-load-balancers --names "wid-$RUN_ID-page" 2>&1 | grep -c LoadBalancerNotFound                   # 1
aws route53 list-resource-record-sets --hosted-zone-id "$PAGE_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='$PAGE_DOMAIN.'].Type" --output text                                          # empty
```

## クリーンアップ（`down`）

`harden` を実行した場合は、最初にノードグループが `ACTIVE` であることを確認してください。同じ RUN_ID で再度練習する場合は、`down` の代わりに `./demo.sh restore "$RUN_ID"` を実行して開始状態に戻せます。

**コマンド**

```bash
./demo.sh down "$RUN_ID"
```

**想定出力**（実測、実行 `t1121`、323 秒）

```text
==> deleted namespace
==> deleting node group (3–5 min)
==> deleted launch template
==> deleted role wid-t1121-node
==> deleted role wid-t1121-irsa
==> deleted role wid-t1121-podid
==> deleted bucket
==> done
```

**残存リソースを確認する。** `down` は専用 kubeconfig を削除するため、AWS CLI を使って確認します。

```bash
aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" 2>&1 | grep -c ResourceNotFound   # 1
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "wid-$RUN_ID" \
  --query 'length(associations)'                                                             # 0
for r in node irsa podid; do
  aws iam get-role --role-name "wid-$RUN_ID-$r" >/dev/null 2>&1 && echo "left: wid-$RUN_ID-$r"
done                                                                                          # no output
aws ec2 describe-launch-templates --filters "Name=tag:LabRun,Values=$RUN_ID" \
  --query 'LaunchTemplates[].LaunchTemplateName' --output text                               # empty
aws ec2 describe-instances --filters "Name=tag:LabRun,Values=$RUN_ID" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text                              # empty
aws s3api head-bucket --bucket "wid-$RUN_ID-$(aws sts get-caller-identity --query Account --output text)-$AWS_REGION" \
  2>&1 | grep -c 404                                                                         # 1
```

普段使っている kubeconfig でも、`kubectl get namespace wid-$RUN_ID` が `NotFound` を返すことを確認してください。公開デモページを起動した場合は、CloudFront ディストリビューションや内部 ALB が残っていないことも確認してください。次のラボで使うなら環境ファイルは残しておけます。不要になった場合は `$STATE_DIR` を削除してください。

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| 使用方法のテキスト（`Usage: ./demo.sh <command> RUN_ID`）しか表示されない | RUN_ID は小文字英字または数字で 4～12 文字にする必要があります。ハイフンや大文字は使用できません。 |
| `set CLUSTER to an existing EKS cluster name` などが表示される | `CLUSTER`、`VPC_NAME`、`SUBNET_NAMES` のいずれかが空です。環境ファイルのパスと内容を確認してください。環境ファイルの値がシェル変数より優先されます。 |
| `cluster VPC is not <VPC_NAME>` | `VPC_NAME` で検出した VPC がクラスターの VPC ではありません。クラスターの VPC の Name タグを再確認してください。 |
| `private subnet '<name>' not found in <VPC_NAME>` | サブネットがクラスターの VPC 内にないか、`MapPublicIpOnLaunch=true` のパブリックサブネットです。プライベートサブネットの Name タグを使ってください。 |
| `eks-pod-identity-agent add-on is required` | `aws eks create-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent` でインストールし、`ACTIVE` になるまで待ってください。クラスター管理者と調整してください。 |
| `IAM OIDC provider for the cluster is required` | クラスター Issuer を IAM OIDC プロバイダーとして登録します（例：`eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER" --approve`）。 |
| `role ... is not tagged for run ...; refusing to modify it` | 同じ名前のロールがすでに存在しますが、このラボのタグが付いていません。別の RUN_ID を使ってください。 |
| ノードグループ作成中に `up` が停止したように見える | `aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" --query nodegroup.health` を確認してください。プライベートサブネットから NAT 経路がないと、ノードはクラスターに参加できず、イメージも取得できません。 |
| `watch` に `starting` が表示され続ける | Pod がまだ `Running` になっていないか、ログがありません。`kubectl -n "$NS" get pods` と `kubectl -n "$NS" describe pod` で確認してください。 |
| `association change not visible to admission within 120s` | `aws eks list-pod-identity-associations` で関連付けが存在することを確認し、`migrate-podid` を再実行してください。関連付けがすでにある場合は作成をスキップし、注入確認に進みます。 |
| `migrate-podid` 後も `orders-podid` がノードロールを使用している | 注入前に Pod が作成されています。ステップ 3 のコマンドで環境変数を確認してください。変数がない場合は `kubectl -n "$NS" rollout restart deploy/orders-podid` を再実行してください。 |
| `legacy copy did not flip within 180s` | IAM の反映に時間がかかっています。`watch` で監視を続けてください。`revoke` を再実行すると、ポリシーはすでに削除済みと報告され、再度待機します。 |
| S3 の結果が `error` | `AccessDenied` や認証情報の不足以外のエラーです。Pod から STS および S3 エンドポイントへの経路（NAT、VPC エンドポイント、DNS）を確認してください。 |
| 想定したロールだが `denied` になる | ロールの ID とリソースへのアクセス権は別のものです。バケットポリシー、SCP、権限境界、VPC エンドポイントポリシーを確認してください。 |

## 参考資料

- [EKS ノード IAM 権限を IRSA と Pod Identity に移行する](../../security/17-eks-workload-identity-migration.md) — このラボのワークブック
- [デモコードとプレゼンター用手順書](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)
- [サービスアカウント用 IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity の仕組み](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [マネージドノードグループの起動テンプレート](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)

## 次のステップ

- [EKS ワークロード IAM 移行クイズ](../../quizzes/security/17-eks-workload-identity-migration-quiz.md)で理解度を確認してください。
- 実際のワークロードで依存関係の調査とカナリア切り替えを計画するには、ワークブックの[本番環境での移行順序](../../security/17-eks-workload-identity-migration.md)を活用してください。
