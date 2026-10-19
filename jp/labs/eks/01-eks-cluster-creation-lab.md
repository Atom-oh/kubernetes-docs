# EKS クラスター作成ラボガイド

> **難易度**: 中級
> **所要時間**: 60～90 分。プロビジョニングと削除にかかる時間は状況によって異なります
> **最終更新日**: 2026年9月12日

## 学習目標

- eksctl を使って専用の EKS クラスターを作成する。
- リソースを変更する前に AWS アカウントとクラスターの識別情報を確認する。
- ノードを調べ、サンプルアプリケーションをデプロイしてスケールする。
- ラボのリソースを削除し、クリーンアップ漏れがないか確認する。

## 前提条件

- [ ] 承認済みの AWS ラボアカウントと、IAM Identity Center などを通じて発行された一時的なロール認証情報。管理者に、この構成に必要な EKS、EC2、CloudFormation、IAM/PassRole などの権限を承認してもらってください。このガイドのためだけに長期 IAM ユーザーを作成したり、AdministratorAccess を付与したりしないでください。
- [ ] AWS CLI v2、eksctl、kubectl、Bash、Python 3、jq、curl。
- [ ] 承認済みのパブリック IPv4 クライアント CIDR。通常は、ワークステーションの現在の送信元アドレスを表す `/32` です。生成スクリプトは `/24` より広い範囲を拒否します。組織でさらに狭い範囲が求められる場合は、その制限を使用してください。
- [ ] [EKS クラスター作成](../../eks/02-eks-cluster-creation-part1.md) を完了していること。

このラボでは EKS 1.36 のマネージドノードグループを使用します。レビュー時点で、AWS は 1.36 を標準サポート対象としています。以前の例にあった 1.31 は延長サポート対象です。実行前に AWS の最新のサポートカレンダーを確認してください。kubectl のマイナーバージョンは API サーバーのバージョンから 1 つ以内の差にし、この例では可能であれば 1.36 を使用してください。

例は eksctl 0.229.0 と kubectl 1.36.2 を使用し、スキーマとローカルモックで確認しました。**この監査ではクラスターをプロビジョニングしておらず、デプロイ時間も測定していません。** アカウント権限、クォータ、インスタンスの利用可否、ネットワーク接続は、ラボアカウントで別途検証する必要があります。

EKS、EC2、EBS、NAT ゲートウェイ、データ転送には料金が発生します。この構成は NAT ゲートウェイを 1 つ使ってノードをプライベートに配置します。これはラボのコストと可用性の選択であり、本番環境の可用性設計ではありません。`STANDARD` サポートポリシーでは、後続の自動バージョンアップグレードを許可することで延長サポートへの移行を避けますが、クラスターやその他のリソースを停止するものではなく、料金も止まりません。

コマンドは専用の Bash ターミナル（**ターミナル A**）で順番に実行してください。表示されたプライベートなラボディレクトリを保持し、その kubeconfig や識別情報の記録をコミットしないでください。後続のコマンドは、そのディレクトリに保存された変数と関数に依存します。

## 演習 1: ツールとアカウント

### 1.1 ツールを確認する

```bash
aws --version
eksctl version
kubectl version --client
python3 --version
jq --version
```

### 1.2 使用するアカウントとクライアント範囲を設定する

このブロックの前に、承認された値を `EXPECTED_ACCOUNT_ID` と `CLIENT_CIDR` に設定してください。例示用アカウント ID やドキュメント専用の IP アドレスをコピーしないでください。`AWS_REGION` の既定値はソウルです。2 つのリージョン変数は同じ値に保ちます。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit lab account ID}"
: "${CLIENT_CIDR:?Set your approved public client IPv4 CIDR, usually a /32}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLIENT_CIDR
umask 077
export LAB_DIR
LAB_DIR=$(mktemp -d "$PWD/eks-lab.XXXXXXXX")
export LAB_RUN_ID
LAB_RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
export CLUSTER_NAME="eks-lab-$LAB_RUN_ID"
export KUBECONFIG="$LAB_DIR/kubeconfig"
printf 'Private lab directory: %s\nCluster: %s\nRegion: %s\n' "$LAB_DIR" "$CLUSTER_NAME" "$AWS_REGION"
```

構成生成スクリプトは、これらの入力を検証し、作成前に予定するクラスターを記録します。

```bash
python3 - <<'PY'
import ipaddress, json, os, re
from pathlib import Path
account = os.environ["EXPECTED_ACCOUNT_ID"]
region = os.environ["AWS_REGION"]
name = os.environ["CLUSTER_NAME"]
run_id = os.environ["LAB_RUN_ID"]
network = ipaddress.ip_network(os.environ["CLIENT_CIDR"], strict=True)
if not re.fullmatch(r"\d{12}", account):
    raise SystemExit("Expected a 12-digit account ID")
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid Region")
if not re.fullmatch(r"eks-lab-[0-9a-f]{12}", name) or name != "eks-lab-" + run_id:
    raise SystemExit("Unexpected lab name")
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed narrow IPv4 CIDR (/24 or narrower); never 0.0.0.0/0")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": name, "region": region, "version": "1.36",
                 "tags": {"content-lab-id": run_id}},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "vpc": {"clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [str(network)], "nat": {"gateway": "Single"}},
    "managedNodeGroups": [{
        "name": "workers", "instanceType": "t3.medium", "amiFamily": "AmazonLinux2023",
        "desiredCapacity": 2, "minSize": 1, "maxSize": 3,
        "privateNetworking": True, "volumeSize": 20, "volumeType": "gp3",
        "volumeEncrypted": True
    }]
}
directory = Path(os.environ["LAB_DIR"])
(directory / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
(directory / "lab-state.json").write_text(json.dumps({
    "account": account, "region": region, "cluster": name, "labId": run_id
}, indent=2) + "\n")
PY
```

```bash
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch; stop.' >&2; return 1; }
}
check_account
aws sts get-caller-identity --region "$AWS_REGION"
```

取得したアカウント ID が `EXPECTED_ACCOUNT_ID` と一致することを確認してください。一時認証情報では、引き受けたロールの ARN が返るのが通常です。不一致や認証失敗があれば作業を中止してください。

## 演習 2: クラスターを作成して識別する

### 2.1 構成を確認する

```bash
cat "$LAB_DIR/cluster.json"
```

この構成では、EKS 1.36、API ベースのアクセスエントリ、`t3.medium` のマネージドノード 2 台、AL2023、暗号化された 20 GiB gp3 ノードディスク、一意な `content-lab-id` タグを選択します。API エンドポイントは両方とも有効です。ノードはプライベートエンドポイントを使い、パブリックエンドポイントは承認済みクライアント CIDR からの接続だけを許可します。ノードには引き続き、イメージやパッケージのエンドポイントへ出ていく通信が必要です。

### 2.2 クラスターを作成する

次のコマンドは課金対象のリソースを作成します。作成とクリーンアップの両方に十分な時間を確保してください。45 分のタイムアウトは待機時間の上限であり、完了を保証するものではありません。

```bash
# MUTATION: creates billed CloudFormation/EKS/VPC/NAT/EC2/EBS resources.
check_account
eksctl create cluster --config-file "$LAB_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

作成に失敗した場合や途中で中断された場合、**ランダムな名前で別のクラスターを作成したり、通常のクリーンアップブロックを確認せずに実行したりしないでください。** `lab-state.json` と `cluster.json` を保持し、該当する名前の CloudFormation スタックを調べ、タグ、アカウント、リソースの対応を確認してください。CLI が失敗を返しても、リソースが作成されていないとは限りません。解決していないリソースには料金が発生し続ける可能性があります。

### 2.3 識別情報とプライベート kubeconfig を保存する

クラスターの作成が成功した後にのみ実行してください。上の `--write-kubeconfig=false` は通常の kubeconfig に変更を加えません。次のコマンドは、このラボ専用のパスだけに書き込みます。

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,createdAt:createdAt,endpoint:endpoint,tags:tags}' \
  --output json > "$LAB_DIR/cluster-identity.json"
jq -e --arg id "$LAB_RUN_ID" '.tags["content-lab-id"] == $id' "$LAB_DIR/cluster-identity.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
```

後続の変更を行う前に、アカウント、クラスター ARN、作成時刻、所有者タグ、kubeconfig のエンドポイントを確認するガードを定義します。

```bash
check_lab() {
  check_account || return
  local current endpoint
  current=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json) || return
  jq -e --arg id "$LAB_RUN_ID" --slurpfile saved "$LAB_DIR/cluster-identity.json" '
    .cluster.arn == $saved[0].arn and
    .cluster.createdAt == $saved[0].createdAt and
    .cluster.tags["content-lab-id"] == $id and
    .cluster.endpoint == $saved[0].endpoint
  ' <<<"$current" >/dev/null || { printf '%s\n' 'Cluster identity mismatch; stop.' >&2; return 1; }
  endpoint=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CLUSTER_NAME" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$LAB_DIR/cluster-identity.json" >/dev/null ||
    { printf '%s\n' 'Kubeconfig endpoint mismatch; stop.' >&2; return 1; }
}
check_lab
```

### 検証

```bash
check_lab
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -o wide
kubectl --context "$CLUSTER_NAME" wait node --selector=eks.amazonaws.com/nodegroup=workers \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/nodegroup=workers -o json |
  jq -e '(.items | length) == 2 and all(.items[];
    any(.status.conditions[]; .type == "Ready" and .status == "True"))'
```

2 台のノードが `Ready` になることを確認してください。登録されたノードが少ない場合は、ノードグループと CloudFormation イベントを調べてください。コントロールプレーンの作成成功だけでワーカーノードの正常性を判断しないでください。

## 演習 3: クラスターを確認する

検証済みのノード一覧から `NODE_NAME` を選び、このブロックの前に設定してください。このラボでは通常のマネージドノードを使用するため、システムコンポーネントの構成は Auto Mode のみを使用する場合と異なります。

```bash
check_lab
: "${NODE_NAME:?Choose a node name from the preceding list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe node "$NODE_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get pods
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get services
# Run separately; preserve the actual error if the metrics API is unavailable.
if ! kubectl --context "$CLUSTER_NAME" --request-timeout=15s top nodes; then
  printf 'Metrics query failed; inspect the error and metrics API status.\n' >&2
fi
```

`kubectl top` には metrics API が必要です。失敗の原因として、metrics-server がない、メトリクスを取得できない、RBAC や接続に問題がある、といった可能性があります。実際のエラーを保持して原因を調べ、metrics-server がないと決めつけないでください。

## 演習 4: アプリケーションをデプロイしてスケールする

### 4.1 nginx をデプロイする

Deployment には明示的なリソース requests/limits と readiness probe が設定されています。Service は `ClusterIP` です。この演習ではロードバランサーコントローラーをインストールせず、パブリックロードバランサーも割り当てません。

```bash
cat > "$LAB_DIR/app.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: eks-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  namespace: eks-lab
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
YAML
```

```bash
# MUTATION in the verified dedicated lab cluster.
check_lab
kubectl --context "$CLUSTER_NAME" create namespace eks-lab
kubectl --context "$CLUSTER_NAME" label namespace eks-lab "content-lab-id=$LAB_RUN_ID"
kubectl --context "$CLUSTER_NAME" apply -f "$LAB_DIR/app.yaml"
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
```

### 4.2 ローカルからのアクセスを確認する

ターミナル A でポートフォワードを開始し、同じワークステーション上の **ターミナル B** で curl コマンドを実行してください。待ち受け先はループバックだけです。ポートフォワードされた接続で確認できるのは選択された Pod であり、外部ロードバランシングや全レプリカの動作確認にはなりません。

```bash
# Keep this in Terminal A; it binds only loopback. Stop with Ctrl+C before continuing.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab port-forward service/nginx 8080:80 --address=127.0.0.1 || test "$?" -eq 130
```

```bash
# Terminal B on the same workstation; no AWS credentials are needed for this local URL.
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  http://127.0.0.1:8080/ --output /dev/null --write-out 'HTTP %{http_code}\n'
```

成功すると `HTTP 200` が出力されます。続行する前に、ターミナル A で Ctrl+C を押してフォアグラウンドのポートフォワードを停止してください。このコマンドは、想定される割り込みを許容しつつ、その他の失敗チェックを維持します。

### 4.3 レプリカを 4 つにスケールする

```bash
# MUTATION: after stopping port-forward in Terminal A.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab scale deployment/nginx --replicas=4
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n eks-lab get deployment nginx -o json |
  jq -e '.spec.replicas == 4 and .status.observedGeneration >= .metadata.generation and
         .status.readyReplicas == 4 and .status.availableReplicas == 4'
```

パブリック `LoadBalancer` の演習も行う場合は、まず [EKS ネットワーキング](../../eks/03-eks-networking-part1.md) に従い、使用するコントローラー、IAM 権限、公開範囲を設定してください。そのリソースと費用は別途追跡して削除する必要があります。ホスト名が割り当てられたことや Deployment が Ready であることだけでは、ロードバランサーを介した通信全体が正常とは確認できません。

## クリーンアップ

最初にポートフォワードを停止してください。このブロックは、タグが付いたラボの namespace と専用クラスターを削除します。namespace が存在しない場合は許容しますが、読み取れない namespace やタグが異なる namespace を安全に削除できるとは見なしません。

```bash
# DESTRUCTIVE: only the verified dedicated lab resources.
check_lab
namespace_json=$(kubectl --context "$CLUSTER_NAME" --request-timeout=15s \
  get namespace eks-lab --ignore-not-found -o json)
if [ -n "$namespace_json" ]; then
  jq -e --arg id "$LAB_RUN_ID" '.metadata.labels["content-lab-id"] == $id' \
    <<<"$namespace_json" >/dev/null
  kubectl --context "$CLUSTER_NAME" delete namespace eks-lab --wait=true --timeout=180s
fi
check_lab
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --wait --timeout=45m
aws eks wait cluster-deleted --name "$CLUSTER_NAME" --region "$AWS_REGION"
# Keep private config/identity records until remaining resources/billing are checked.
```

削除の失敗を検出するには `--wait` が必要です。EKS の削除完了待機処理で確認できるのは、コントロールプレーンのオブジェクトがなくなったことです。依存リソースや料金がすべてなくなったことまでは確認できません。保存したラボ情報で CloudFormation スタックの状態を調べ、`DELETE_FAILED` や保持されたリソースを含め、タグが付いた EC2/EBS/NAT/VPC リソースが残っていないか確認してください。この確認が終わるまで、ローカルの識別情報と構成記録を保持してください。削除確認の代わりに一定時間の sleep を使わないでください。

作成が識別情報の保存まで到達しなかった場合は、プライベートな作成意図の記録と CloudFormation イベント／タグを使って、リソースの所有者を手動で確認してください。ガードを通すためだけに `cluster-identity.json` を作らないでください。

## トラブルシューティング

<details>
<summary>クラスターの作成に失敗する</summary>

選択したリージョンで、承認済みロールの権限、サービスクォータ、サブネット／IP 容量、インスタンスの利用可否を確認してください。eksctl は CloudFormation を使用します。既定の対処として広範な管理者権限を付与するのではなく、実際の失敗原因を調べてください。

```bash
check_account
eksctl utils describe-stacks --region "$AWS_REGION" --cluster "$CLUSTER_NAME"
```

作成途中の復旧中は、プライベートなラボディレクトリを保持してください。削除を実行する前に、対象リソースが実際に自分のラボに属するか確認してください。

</details>

<details>
<summary>kubectl が接続できない</summary>

ロールの認証情報、アクセスエントリ、DNS、ワークステーションの現在の送信元アドレスが承認済み CIDR に含まれているかを確認してください。プライベート kubeconfig を再作成する必要がある場合は、まずクラスターの識別情報を確認し、このラボ専用のパスだけに書き込んでください。

```bash
check_account
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
check_lab
```

クライアントアドレスが変わった場合でも、回避策としてエンドポイントのアクセス範囲をインターネット全体に広げないでください。

</details>

## 参考資料

- [EKS のサポート対象バージョン](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS のアップグレードポリシー](https://docs.aws.amazon.com/eks/latest/userguide/view-upgrade-policy.html)
- [クラスターエンドポイントへのアクセス](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [eksctl の IAM 権限](https://docs.aws.amazon.com/eks/latest/eksctl/minimum-iam-policies.html)
- [eksctl によるクラスターの作成と削除](https://docs.aws.amazon.com/eks/latest/eksctl/creating-and-managing-clusters.html)
- [kubectl のバージョンスキュー](https://kubernetes.io/releases/version-skew-policy/)
- [ポートフォワーディング](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [nginx 公式イメージの定義](https://github.com/docker-library/official-images/blob/master/library/nginx)

## 次のステップ

- [EKS クラスター作成クイズ](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- [EKS ネットワーキング](../../eks/03-eks-networking-part1.md)
