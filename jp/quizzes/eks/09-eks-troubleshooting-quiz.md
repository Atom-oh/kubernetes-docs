# Amazon EKS トラブルシューティングクイズ

> **最終更新日**: 2026年9月12日

このクイズでは、Amazon EKS クラスターで起こり得る問題の診断と解決について確認します。

## クイズの概要

- クラスターの作成と設定
- ネットワーク
- ノードと Pod
- ストレージ
- セキュリティとアクセス
- パフォーマンスとスケーラビリティ

## 選択問題

### 1. EKS コントロールプレーンの作成に失敗したとき、最初に何を調べるべきですか？

- A. クラスター名が一意かどうかだけを確認する
- B. 正確なエラーとリクエストを調べ、呼び出し元とサービスロールの IAM、VPC とサブネット、関連クォータを確認する
- C. すぐに別のリージョンでクラスターを作成する
- D. より大きなワーカーノードのインスタンスタイプを選ぶ

<details>
<summary>解答を表示</summary>

**正解: B. 正確なエラーとリクエストを調べ、呼び出し元とサービスロールの IAM、VPC とサブネット、関連クォータを確認する**

CloudFormation イベントまたは失敗したリクエストから調査を始めます。IAM、ネットワーク、クォータ、名前の競合は確認すべき仮説ですが、エラーを読む前に原因だと決めつけてはいけません。

**確認する証拠**

| 対象 | 確認事項 |
| --- | --- |
| 呼び出し元 | 正しいアカウント、リージョン、プロファイルか。必要な EKS アクション、`iam:PassRole`、境界、セッションや SCP の制御、必要に応じたサービスリンクロール作成権限があるか |
| クラスターサービスロール | 正確なロール ARN、EKS の信頼関係、必要なサービスロールポリシー。呼び出し元やワーカーノードのロールと混同しない |
| クラスターサブネット | 対応 AZ、異なる2つ以上の AZ、空き IP アドレス。ノード、Pod、ロードバランサー用の容量は別に見積もる |
| エンドポイントと依存先 | 意図したプライベート/パブリック構成、DNS、ルート、SG/NACL、必要な AWS サービスへのアクセス |
| クォータ | 実際のサービスクォータとアカウント/リージョンで適用中の上限。ノード作成時は EC2 vCPU 制限も確認 |
| インフラ所有者 | 元の Terraform/CloudFormation/eksctl 設定、state、失敗した操作 |

選択した各クラスターサブネットには現在少なくとも **6個の IP アドレス**が必要で、**16個以上が推奨**されます。また、2つ以上の AZ にサブネットが必要です。CIDR の大きさだけでは、必要なアドレスが空いているとは確認できません。従来の一般的な「最低 /28、推奨 /24」という記述は、コントロールプレーンとワークロードのサイズを混同していました。必要なエンドポイントを用意したプライベート構成も可能で、NAT や一般インターネット接続が常に必要とは限りません。

`AmazonEKSClusterPolicy` はクラスターサービスロールに付与するポリシーです。人間のユーザーに付与しても、作成権限や PassRole、Kubernetes RBAC が一括で得られるわけではありません。サブネットにクラスター所有タグを追加することも、作成失敗を普遍的に解決する方法ではありません。

**読み取り専用の調査**

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"; : "${CLUSTER_NAME:?}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
: "${VPC_ID:?Set the VPC from the original request}"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount}'
# For an eksctl-owned creation attempt, inspect its existing stacks:
eksctl utils describe-stacks --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

利用可能なクラスターがある場合は `describe-cluster` で調べます。まだない場合は、ResourceNotFound を第2の根本原因とみなさず、作成時のエラーを保存します。別の CloudFormation 所有者については対象スタックのイベントを確認します。`eksctl create cluster --verbose ...` と CLI の debug モードはリソースを作成するため、読み取り専用の診断ではありません。

**エラーメッセージの例**

- `eks:CreateCluster` の拒否なら、呼び出し元の権限を調べます。サービスロールの問題とは権限経路が異なります。
- `us-west-2a` で容量不足とする旧例は、AZ/容量への対応例であり、現在のリージョン状況を示すものではありません。
- “Current limit is 5” という旧例は過去の説明です。引き上げ値を選ぶ前に、現在適用されているクォータを調べます。
- `UnsupportedAvailabilityZoneException` は、そのアカウントで EKS クラスターに使えない AZ を示します。EC2 インスタンスタイプの提供状況だけを示すものではありません。

**インフラ設定の確認**

元の所有者が管理する設定を調べ、修正します。次の Terraform 例はバージョンとネットワークの意図を明示し、状態出力を示すものです。診断中に適用する完全な新規クラスター用モジュールではありません。

```hcl
# Excerpt of the original state-owned configuration, not a diagnostic apply.
# Preserve its other settings and role/policy dependencies.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.cluster_version
  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = var.cluster_security_group_ids
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

確認済みの既存ロール/サブネット/セキュリティグループを渡し、必要なロールポリシーの依存関係や他の設定を維持します。プライベートエンドポイントへのアクセス経路も確認します。Terraform の output は state から評価されるため、作成失敗時に最新の失敗情報を必ず含むとは限りません。プロバイダーの診断情報と AWS リクエスト/スタックの証拠を使います。このレビューでは Terraform apply もクラスター作成も行っていません。

原因を特定した後、対象を絞った権限、ネットワーク、クォータの修正を所有者と確認し、再試行します。A は限定的な確認には有用ですが、それだけでは不十分です。C は配置やデータ、ネットワークを変え、費用が増える可能性があります。D はワーカーノードを変えるだけで、コントロールプレーンの作成問題には対処しません。

参考: [EKS のネットワーク要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)、[EKS のトラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)、[Terraform EKS クラスター](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster)

</details>

### 2. EKS ノードが NotReady になった場合、最初に何を調べるのが効果的ですか？

- A. すぐにノードを終了する
- B. ノードの condition/event、ログ、リソース、実際のネットワーク/ID 経路を調べる
- C. 管理対象 EKS API サーバーを自分で再起動する
- D. クラスター内のすべての Pod を削除する

<details>
<summary>解答を表示</summary>

**正解: B. ノードの condition/event、ログ、リソース、実際のネットワーク/ID 経路を調べる**

condition の理由と時刻、ノードの実際の ID を使って調査します。Ready=False、heartbeat 欠落による Ready=Unknown、DiskPressure、MemoryPressure は異なる証拠であり、いずれも単独で根本原因を特定するものではありません。

**ノードとワークロードの一覧**

次の読み取り専用例はノード名/UID でノードを特定し、`spec.nodeName` で Pod を選択します。IP や grep による不確かな照合を避けます。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

EC2 やホストにアクセスする前に ProviderID、アカウント/リージョン、コンピューティング種別を確認します。マネージドグループでは、その健全性と修復/更新設定を調べます。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

アクセス可能な標準 Linux ノードでは、[元ガイドのリモートセッション手順](../../eks/09-eks-troubleshooting.md)を使い、kubelet/containerd の journal、バイト数と inode、メモリ、ルーティングを確認します。実際のイメージに Docker daemon や `/var/log/syslog` があるとは限りません。ノード DNS は自動的に Pod のクラスタ DNS と同じではありません。エンドポイント TLS にはクラスター CA を使い、`curl -k` で証明書の問題を隠さないでください。

イメージ削除、journal 削除、再起動の前に証拠を保全します。`kubectl top` は正常なメトリクス経路が必要で、異常なノードでは失敗する場合があります。秘密鍵を表示せずに証明書パスを確認します。`kubeadm alpha certs renew all` は現在の一般的なコマンドでも EKS ノード修復手順でもありません。`eksctl replace nodegroup` はサポートされません。

**自動修復と復旧の区別**

原因を特定してから、容量、PDB、データ、ノード所有者と調整し、ノードの置き換え/再起動を行います。drain が上限時間内に完了しなければ停止します。非同期再起動の直後に無条件で uncordon してはいけません。

自動ノード修復は実際にある EKS の機能です。`update_config.max_unavailable` はバージョン更新による中断数を制御しますが、修復を有効にする設定ではありません。また `health_check { type = "EKS" }` は `aws_eks_node_group` のブロックではありません。現在のプロバイダーには `node_repair_config` があります。

```hcl
# Fragment of a reviewed EKS-optimized-AMI managed node group.
resource "aws_eks_node_group" "self_healing" {
  cluster_name    = var.cluster_name
  node_group_name = var.node_group_name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.node_kubernetes_version
  ami_type        = var.ami_type
  release_version = var.ami_release
  instance_types  = var.instance_types

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
  update_config {
    max_unavailable = 1
  }
  node_repair_config {
    enabled                           = true
    max_parallel_nodes_repaired_count = 1
  }
}
```

これは設定断片であり、本番で検証済みのモジュールではありません。互換性を確認した Kubernetes/AMI/インスタンス入力と既存の所有関係が必要です。オートスケーラーが管理している場合は希望容量を調整します。ノードグループのタグが、基礎となる ASG に CA が必要とするタグがある証拠にはなりません。

修復の既定値やしきい値はコンピューティング所有者によって異なります。Auto Mode は既定で修復を有効にします。マネージドグループでは有効化が必要で、Karpenter にも独自の要件があります。ノード監視は修復が無効でも問題を報告できます。現在の既定修復表は MemoryPressure や DiskPressure を自動修復しません。Fleet health のしきい値、並列数、ARC 制御は実行を制限するため、必ず置き換えられる/PDB が常に守られると約束してはいけません。

**監視の例**

`AWS/EKS` のメトリクス名 `NodeNotReady` が組み込みだと仮定できません。既存の kube-state-metrics/Prometheus Operator 構成では、実際のノード condition を評価できます。

```yaml
# Existing single-cluster Prometheus Operator/KSM installation required.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-readiness-example
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
    - name: node-readiness-example
      rules:
        - alert: NodeNotReady
          expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="Ready",status="true"}) == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ $labels.node }} is not Ready"
            description: "Investigate node conditions, reachability and workload impact before recovery."
```

namespace/release/job の selector を実際の導入構成に合わせます。10分の待機は例です。scrape や condition のデータが欠ける場合は、telemetry の健全性を別に監視し、正常なノードと見なしてはいけません。この alert は通知を接続せず復旧も実行しません。個別に検証してください。未定義の `node-recovery.zip` Lambda を作っても安全な自動復旧にはなりません。

C は顧客が管理対象 EKS API サーバーを再起動する手段ではありません。ただし API 接続が readiness の問題になることはあります。A と D は中断を広げ、原因を解決せず証拠を失わせる可能性があります。

参考: [EKS ノード修復](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)、[Terraform マネージドノードリソース](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group)、[ノードメトリクス](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)

</details>

### 3. EKS の ImagePullBackOff を適切に調査する方法はどれですか？

- A. すべてのコンテナのメモリ上限を増やす
- B. pull エラーを読み、イメージ/プラットフォームと実際の pull ID/ネットワーク経路を確認する
- C. エラーを確認せず強制的にイメージを再取得する
- D. すべての NetworkPolicy を削除する

<details>
<summary>解答を表示</summary>

**正解: B. pull エラーを読み、イメージ/プラットフォームと実際の pull ID/ネットワーク経路を確認する**

ImagePullBackOff は再試行時の待機状態であり、単一の「最も可能性の高い」原因を示しません。対象となるすべての通常/init コンテナと kubelet event を調べます。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

リポジトリ、tag/digest の欠落、非対応アーキテクチャ、認証/認可、レジストリの rate limit、ノード DNS/TLS/egress、ローカルディスク/runtime の問題を区別します。ローカル Docker pull は別の ID/経路を使うため、ノードが pull できる証明にはなりません。

**ECR の ID とネットワーク**

EC2 ノードは通常ノードの pull credential 経路を使い、Fargate は Pod 実行ロールを使います。アプリケーションの IRSA/Pod Identity は、アプリ起動前のイメージ取得に使う ID ではありません。必要に応じてリポジトリポリシーとクロスアカウントアクセスを確認します。compute に関連付けていない IAM ロールを作っても pull 動作は変わりません。

任意のイメージ文字列を `cut` で分割せず、リポジトリ/アカウント/リージョンと tag **または** digest を明示します。

```bash
set -euo pipefail
: "${REGISTRY_REGION:?Set the image registry Region}"
: "${REGISTRY_ACCOUNT_ID:?Set its account ID}"
: "${REPOSITORY_NAME:?Set the exact repository path}"
: "${ECR_IMAGE_ID:?Set imageTag=... or imageDigest=sha256:...}"
aws ecr describe-images --region "$REGISTRY_REGION" \
  --registry-id "$REGISTRY_ACCOUNT_ID" --repository-name "$REPOSITORY_NAME" \
  --image-ids "$ECR_IMAGE_ID" \
  --query 'imageDetails[].{digest:imageDigest,tags:imageTags,pushedAt:imagePushedAt,mediaType:imageManifestMediaType}'
```

これは操作者の AWS credential でイメージメタデータを調べるもので、kubelet の権限を検証するものではありません。プライベート ECR では ECR API/DKR と S3 への経路、endpoint policy/security group、DNS が必要になることがあります。`ecr.dkr` は任意のプライベートレジストリ用 endpoint ではありません。通常の Pod NetworkPolicy 変更で、ノード runtime のレジストリ認証問題が直るわけではありません。

**権限の例**

意図的に選んだ既存 EC2 ノードロールでは、次の権限が1リポジトリからの pull を示します。`GetAuthorizationToken` はリポジトリの resource scope を持たないため、該当 statement はリージョン条件付き `*` を使います。イメージ読み取り権限はリポジトリに限定します。

```hcl
# Permission example for a reviewed existing EC2 node role.
# This does not create/associate a new role or create an image-pull Secret.
data "aws_iam_role" "node" {
  name = var.existing_node_role_name
}

resource "aws_iam_policy" "ecr_pull" {
  name = var.pull_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.registry_region }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = var.repository_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = data.aws_iam_role.node.name
  policy_arn = aws_iam_policy.ecr_pull.arn
}
```

実際のリポジトリ ARN/リージョンを使い、既存 grant、境界、SCP、クロスアカウントのリポジトリポリシーを確認します。限定ポリシーを追加しても既存の広範なポリシーは削除されません。Fargate には専用の実行ロール設定が必要です。この EC2 例は Kubernetes Secret を作成せず、Fargate profile も設定しません。このレビューでは IAM 変更を実行していません。

**イメージ pull Secret**

Secret が必要なレジストリでは、保護された自己完結型の Docker auth ファイルと[元ガイドの namespace 指定 Secret/Pod template 手順](../../eks/09-eks-troubleshooting.md)を使います。Secret の値や token を表示したり、診断コマンドラインに password を渡したりしません。デスクトップの credential-helper 参照だけでは kubelet の認証データになりません。

既存 Pod の imagePullSecrets は通常その場で patch できません。既存の pull-secret リストを維持し、所有する Deployment/StatefulSet template を変更して制御された rollout を行います。ServiceAccount 更新の影響を受けるのは新しく admission された Pod です。無関係なアプリケーション用に default ServiceAccount を変更しないでください。

**credential 更新設計**

標準的な EKS の ECR pull に、従来の token 更新 CronJob は不要です。ECR 認可 token の有効期間は12時間です。ECR の pull Secret を手動管理する必要が本当にある非標準 consumer では、サポートされた credential 機能か、明示的に設計した更新手順を使います。

旧スケジュール `*/6 * * * *` は6時間ごとではなく **6分ごと**です。6時間ごとの例は `0 */6 * * *` で、controller の timezone またはサポートされる `.spec.timeZone` を確認します。スケジュールだけでは更新処理になりません。必要なツールを含む確認済みイメージ、AWS ID、範囲を限定した Kubernetes 権限、正確な対象 namespace、重複/失敗処理、テスト済みの rotation が要ります。確認が終わるまでは suspend します。credential の空白期間を作らないよう、事前作成した名前付き Secret を更新します。標準の AWS CLI image に kubectl が含まれるとは限りません。

意図した image digest を固定し、レジストリの可用性を維持して、変更前に実際の event を調査します。`Always` でも存在しないイメージや権限不足は解決しません。A/C/D は失敗した pull 経路を特定しません。

参考: [Fargate 実行ロール](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html)、[ECR token コマンド](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html)、[プライベートレジストリの Secret](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)

</details>

### 4. Service が Pod に到達しないとき、最初に何を調べるべきですか？

- A. Service をすぐに作り直す
- B. selector/type、Pod readiness、EndpointSlice、port、実際に許可された経路を調べる
- C. すべての Pod を再起動する
- D. 管理対象 API サーバーを自分で再起動する

<details>
<summary>解答を表示</summary>

**正解: B. selector/type、Pod readiness、EndpointSlice、port、実際に許可された経路を調べる**

リソースを変更する前に、Service の検出と routing を順に追います。対象 namespace と送信元 client を使い、Service 設定を実際のアプリケーション listener/readiness と比較します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

この helper は selector のない Service に対し、誤ってすべての Pod を選択しません。ExternalName は別名を解決し、headless Service は意図的に `clusterIP: None` を使います。手動管理の EndpointSlice も有効な構成です。endpoint の Ready/serving/terminating condition と traffic policy を調べます。ready sidecar が1つあることや phase=Running は、Pod の Ready condition と同じではありません。

**観測した問題の修正**

- selector の不一致: 置き換え可能な Pod 1つの label だけでなく、所有者の Service/Pod template を直します。
- port の不一致: Service port、名前付き targetPort、実際のアプリ listener を一致させます。containerPort 宣言だけでは listener は作られません。
- policy の制限: 送信元 egress と宛先 ingress の両方、label、実装範囲を確認します。policy を削除したり、すべての namespace から全 port を許可したりしません。
- DNS/data plane: 名前解決と transport を区別し、標準 kube-proxy、別の実装、Auto Mode のいずれかを特定します。Auto Mode のみのクラスターではノード DNS を使います。混在クラスターでは Auto Mode 以外のノード用に DNS を残します。

この**独立した policy の例**は、確認済みの peer/port だけを許可します。使用前に label/namespace と必要な通信経路の全体表を調整してください。

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

別の許可 policy がなければ、これは選択した backend ingress 以外を隔離する可能性があります。client の egress rule は作りません。許可経路と拒否経路の両方をテストします。

**Terraform の Service/Deployment fixture**

元の Service-to-Pod の例は、listener、label、readiness、上限付き resource を宣言した、破棄可能な Linux fixture として維持します。provider に確認済みの test context を設定し、新しい namespace を選択します。既存アプリケーションの namespace を import しないでください。

```hcl
# Disposable example; configure the Kubernetes provider/context externally.
variable "test_namespace" {
  type = string
  validation {
    condition     = can(regex("^docs-service-check-[a-z0-9]{8,16}$", var.test_namespace))
    error_message = "Supply a new unique namespace with the test prefix."
  }
}
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.test_namespace
  }
}
resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "app-deployment"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "service-demo" }
    }
    template {
      metadata {
        labels = { app = "service-demo" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "app"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args    = ["mkdir -p /tmp/www; printf 'ok\\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www"]
          port {
            name           = "http"
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "http"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "app-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "service-demo" }
    type     = "ClusterIP"
    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
```

これは本番アプリケーションでも、測定済みの resource 推奨値でもありません。アプリケーション API/RBAC 要件もありません。provider の field は確認しましたが、実環境で Terraform apply したり image を実行したりしたとは主張していません。

**範囲を限定した接続 Job**

fixture Service と Pod の readiness が整った後、namespace を準備済みの値に置き換えて Job を保存します。この probe に kubectl binary や Kubernetes API token は不要です。

```yaml
# Use kubectl create; replace namespace with the prepared fixture namespace.
apiVersion: batch/v1
kind: Job
metadata:
  generateName: service-probe-
  namespace: docs-service-check-12345678
spec:
  activeDeadlineSeconds: 60
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: probe
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - nslookup app-service; wget -T 5 -q -O- http://app-service:80
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
```

共通名を再利用せず、新しい一意な名前の Job を作成します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TEST_NAMESPACE:?}"; : "${SERVICE_PROBE_FILE:?}"
JOB_NAME=$(kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" create \
  -f "$SERVICE_PROBE_FILE" -o jsonpath='{.metadata.name}')
: "${JOB_NAME:?Job creation did not return a name}"
printf 'Created probe: %s/%s\n' "$TEST_NAMESPACE" "$JOB_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" wait \
  --for=condition=complete "job/$JOB_NAME" --timeout=90s
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" logs "job/$JOB_NAME"
```

wait が失敗した場合は生成された Job を残し、その Pod/event/log を調べます。無条件の成功を表示したり、既存 namespace を削除したりしません。UID を記録し、証拠を確認した後に所有する test resource だけを削除します。この test が確認するのは DNS と1回の HTTP request であり、すべての client ID、直接 Pod への経路、load balancer、SLO ではありません。必要に応じて、許可された同じ送信元から Pod への直接接続と Service 経由を別々に比較します。

A/C は診断前に証拠を失うか中断を増やします。D は顧客が操作する EKS control plane の手段ではありません。証拠が示す場合は API/controller の健全性を調べます。

参考: [Service](https://kubernetes.io/docs/concepts/services-networking/service/)、[EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)、[NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

</details>

### 5. PVC が Pending のままのとき、最初に何を調べるべきですか？

- A. 常に大きなノードを追加する
- B. claim/class、binding mode、利用 Pod の scheduling、driver、provisioner の ID を調べる
- C. 常に Pod priority を上げる
- D. 常に Cluster Autoscaler を導入する

<details>
<summary>解答を表示</summary>

**正解: B. claim/class、binding mode、利用 Pod の scheduling、driver、provisioner の ID を調べる**

Pending は、それだけでストレージ障害を示しません。WaitForFirstConsumer では、適切な利用 Pod の scheduling まで claim が待つ場合があります。EBS または IAM 障害と決めつけず、実際の driver/compute 経路を確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

この helper は storageClassName の未指定/空文字を区別し、JSON で利用 Pod を選択します。Kubernetes は以前の Pod field selector `spec.volumes.persistentVolumeClaim.claimName` をサポートしません。claim が Bound の場合、binding 完了をアプリ検証済みとせず、mount/readability を調べます。

**観測された状態の確認**

- Class/provisioner: 参照先 class が存在し、標準 EBS、Auto Mode、EFS、他の driver のどれに合うか確認します。明示的な空の class と default の省略は異なる binding 経路を要求します。
- 遅延 binding: 利用 Pod の request、taint/affinity、zone、容量を調べます。consumer の都合で node 供給、priority、autoscaling が間接的に PVC に影響する場合はあります。A/C/D は普遍的な修正ではありません。
- ID: node role だけでなく、実際の controller IRSA/Pod Identity と KMS 権限を調べます。Fargate は EBS volume を mount できません。Auto Mode は別の provisioner を使います。
- CSI: controller/node の健全性、event、現行の互換 add-on version、所有関係を確認します。エラーを把握せず force で再インストールしないでください。

**Class とデータのライフサイクル**

既存 StorageClass の変更不可な binding mode を patch したり、1つの claim のためにクラスターの default を切り替えたりしません。新しい standard-driver class を明示して選ぶ場合は次のようにします。

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

YAML は設定例であり、既存 class に適用するコマンドではありません。Retain は別途ライフサイクルを判断するまで storage を残し、料金が発生し続ける可能性があります。PVC YAML はデータバックアップではありません。claim の削除/再作成はデータ破損や、Retain された volume の意図しない再 bind を招く場合があります。

Auto Mode には標準 provisioner ではなく `ebs.csi.eks.amazonaws.com` が必要です。ノードの root/data encryption だけでは、動的に作成される全 PVC が暗号化されたことになりません。`encrypted: "true"` を明示し、実際の EBS volume/key を調べます。bind 済み claim の provisioner/class を変更するのではなく、文書化された snapshot または適切な Retain/static migration 手順を使います。

**Terraform による所有例**

既存の standard EBS CSI add-on には、確認した version、schema 検証済みの完全な設定、準備済み controller ID を使います。この IRSA 例は Pod Identity も同時に設定するものではありません。

```hcl
# Existing standard EBS CSI add-on with a reviewed IRSA identity.
# Preserve/import its existing resource ownership; do not create a duplicate add-on.
resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.reviewed_ebs_addon_version
  service_account_role_arn    = var.controller_irsa_role_arn
  configuration_values        = file(var.reviewed_configuration_file)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

既存の所有関係を維持/取り込みます。controller role には現在の scope を限定した EBS 権限/tag 条件と、必要なら customer key の権限が必要です。以前の IAM module/add-on version の組み合わせは、現在の互換性を保証しません。また `--role-only` は role を add-on に関連付けません。詳しくは[ストレージの元ガイド](../../eks/04-eks-storage-part1.md)と現行 add-on catalog を参照します。

同じ新しい class は、現行 Kubernetes resource 経由でも管理できます。

```hcl
# New standard-driver class, explicitly selected by test PVCs.
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "diagnostic-ebs-gp3"
  }
  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  parameters = {
    type                        = "gp3"
    encrypted                   = "true"
    "csi.storage.k8s.io/fstype" = "ext4"
  }
}
```

その class の所有者は YAML **または** Terraform のどちらかにします。provider field/syntax をローカルで確認しても、IAM、CSI provisioning、対象クラスターでのデータ復旧が証明されるわけではありません。

**分離された provisioning test**

確認済みの Linux EC2 経路を試すには、[EKS upgrade](../../eks/08-eks-upgrades.md) の `eks-upgrade-smoke.py` helper 全体を保存し、明示的に選んだ test context/class を使います。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test context}"
: "${TEST_STORAGE_CLASS:?Set the reviewed compatible test class}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
# Save the complete helper from the EKS upgrades source guide first.
python3 eks-upgrade-smoke.py
```

一意な namespace と PVC writer を作成してから遅延 binding を待ち、別の consumer で marker を読み取ります。証拠を記録し、失敗した resource は保持します。実際に実行する場合は Retain の後処理とストレージ料金を考慮します。この監査ではクラウド provisioning、volume 作成、mount、benchmark を実行していません。無関係で請求対象になり得る volume を作る旧 AWS CLI Job を PVC 診断に使わないでください。

参考: [StorageClass](https://kubernetes.io/docs/concepts/storage/storage-classes/)、[EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[Auto Mode class](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)

</details>

### 6. autoscaling が期待どおりに動かないとき、最も効果的な調査方法は何ですか？

- A. すべての Pod に多くの resource を割り当てる
- B. 手動でノードを増やして調査をやめる
- C. replica/resource/node の所有者を特定し、その metric、condition、上限、ID、event を調べる
- D. クラスターを作り直す

<details>
<summary>解答を表示</summary>

**正解: C. replica/resource/node の所有者を特定し、その metric、condition、上限、ID、event を調べる**

HPA による replica scaling、VPA による resource の推奨/更新、CA/Karpenter/Auto Mode による node provisioning を分けて調べます。それぞれ制御する resource も依存する signal も異なります。全て導入されている必要はありません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

HPA の condition、現在の metric、request、min/max、behavior を確認します。desired/current replica の差は、正常な収束中であることもあります。metric data の欠落や error は scale-down を妨げる場合があります。CPU/memory の resource metric には Metrics Server が必要です。custom/external metric には専用 adapter/integration が必要です。query 失敗から API/CRD が存在しないとは判断できません。

既存の managed node group は、tag を推測して全アカウントの group を探さず、実際の ASG を調べます。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{scaling:scalingConfig,health:health,autoScalingGroups:resources.autoScalingGroups}'
: "${ASG_NAME:?Select the actual group returned above}"
aws autoscaling describe-auto-scaling-groups --region "$AWS_REGION" \
  --auto-scaling-group-names "$ASG_NAME" \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances,Tags:Tags}'
```

CA は平均 node CPU の高さではなく、schedule 不可能な Pod とその制約に反応します。対応する Kubernetes minor、正確な Pod identity、最小権限の discovery/scaling 権限、ASG tag、最大サイズ、EC2/IP quota、起動失敗を確認します。node group tag だけでは CA discovery 用の ASG tag がある証拠になりません。managed group の上限は EKS/インフラ所有者に確認します。ASG を直接編集すると drift が起きることがあり、scaling 設定変更は PDB を考慮しません。

Karpenter/Auto Mode では該当する NodePool/NodeClaim/provider の上限と event を調べます。固定した CA Pod label に一致する object がないからという理由で CA を導入しません。VPA の Off/Initial は意図的な設定の場合があります。Auto mode は Recreate に置き換えられる予定の非推奨 mode です。同じ CPU/memory signal を使う HPA との組み合わせで、mode 変更が中断を引き起こす場合があります。

**Helm/Terraform 設定例**

これは既存 Helm 管理下の CA と Metrics Server にのみ使います。確認済み chart version と、対象クラスター minor に互換な CA image version を渡します。chart default の image が対象環境に追随しているとは限りません。各 component の所有者を1つにします。

```hcl
# Existing Helm-owned installations only; supply reviewed compatible versions.
# The IRSA trust subject must match kube-system:cluster-autoscaler.
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = var.ca_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  values = [yamlencode({
    autoDiscovery = { clusterName = var.cluster_name }
    awsRegion     = var.aws_region
    image         = { tag = var.ca_image_tag }
    rbac = {
      serviceAccount = {
        create = true
        name   = "cluster-autoscaler"
        annotations = {
          "eks.amazonaws.com/role-arn" = var.ca_irsa_role_arn
        }
      }
    }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  # Retain/migrate the existing owner's reviewed values.
  values = [file(var.metrics_server_values_file)]
}
```

これは Helm provider 3.x と互換性がある values document を使い、削除された繰り返し `set {}` 構文は使いません。CA ServiceAccount 名を明示し、IRSA trust subject と一致させます。Pod Identity は別途所有する設定です。role には[cost/scaling ガイド](../../eks/07-eks-cost-optimization.md)に記載された範囲付き権限が必要です。一般的な対処として AutoScalingFullAccess を付与しません。

Metrics Server の既存導入から確認済み values を merge します。現行 upstream chart の default は kubelet の安全な接続経路を使い、`--kubelet-insecure-tls` を意味しません。certificate/trust/address の問題を調べてから、lab 限定の回避策を選びます。EKS add-on が所有する component に別 Helm release を作りません。chart/ID/network/runtime の互換性は対象環境で検証が必要です。このレビューでは Helm install を行っていません。

**HPA metric と behavior**

次の resource metric の例は CPU/memory と scale-up/down policy の考え方を維持します。

```yaml
# Example resource metrics and behavior; requires an existing target with requests.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

utilization target には request が必要です。HPA は複数 metric の desired replica 数の最大値を選びます。一方、欠損/error metric は scale-down を抑制する場合があります。Policy の Max/Min は許可する変更率を選びます。stabilization は一律の「cooldown」ではありません。percentage、上限、期間は例示で、memory scaling の挙動が CPU と同じとは限りません。Terraform/GitOps と他の autoscaler が同じ replica 数を競合して管理しないようにします。

**Dashboard の例**

data source UID が `prometheus` で、sidecar が `grafana_dashboard=1` label を `monitoring` 内で監視する、既存の単一クラスター kube-prometheus-stack 構成を想定します。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaling-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  autoscaling-dashboard.json: |
    {
      "uid": "eks-autoscaling-diagnostics",
      "title": "EKS Autoscaling Diagnostics",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "HPA replicas",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Current {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "B",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_desired_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Desired {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "C",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_min_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Min {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "D",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Max {{namespace}}/{{horizontalpodautoscaler}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Observed node count",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count(max by (node) (kube_node_info{job=\"kube-state-metrics\"}))",
              "legendFormat": "Nodes"
            }
          ]
        },
        {
          "id": 3,
          "title": "Pod CPU usage (cores)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "cores"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        },
        {
          "id": 4,
          "title": "Pod working set (bytes)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "bytes"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (container_memory_working_set_bytes{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        }
      ]
    }
```

selector/UID/namespace を実環境に合わせます。HPA series は namespace を維持し、集約前に exporter の重複を除きます。CPU は core 単位の使用量、memory は working-set byte で、割合ではありません。複数クラスターの data source には cluster dimension/filter を追加します。scrape の欠落は正常なゼロではなく no-data/unknown として残します。Dashboard は scaling 成功の証明でも alert/automation pipeline でもありません。

A/B は一時的に capacity を変えるだけで、controller/metric の失敗を特定しません。D は原因を診断せず migration のリスクを増やします。期待した挙動と実測、復旧させた具体的な変更を記録します。

参考: [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)、[Cluster Autoscaler AWS](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md)、[CA chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler)、[Metrics Server](https://github.com/kubernetes-sigs/metrics-server)、[VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

</details>

### 7. NetworkPolicy の動作が予想と異なるとき、最も効果的な調査方法は何ですか？

- A. すべての NetworkPolicy を削除する
- B. 実際の enforcement 実装、policy selector/意味、log、失敗する通信を調べる
- C. 全 Pod に hostNetwork を設定する
- D. VPC を再構築する

<details>
<summary>解答を表示</summary>

**正解: B. 実際の enforcement 実装、policy selector/意味、log、失敗する通信を調べる**

宣言された policy と、それを適用する実装の両方を確認します。NetworkPolicy object を作っただけでは enforcement engine は導入されません。

**一覧と policy の意味**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,labels:.metadata.labels,owners:.metadata.ownerReferences,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,status:.status.phase}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" get daemonsets -A -o json \
  | jq '.items[] | {namespace:.metadata.namespace,name:.metadata.name,containers:[.spec.template.spec.containers[] | {name,image}]}'
```

Pod list が空でも kubectl は成功 exit code を返します。`if kubectl get pods -l ...` で VPC CNI、Calico、Cilium の導入を証明しないでください。設定上の所有者、実際の object/image、policy agent の状態、対応する compute/kernel/version を確認します。Auto Mode は組み込み NodeClass network control を使い、任意の代替 CNI 導入を受け付けません。

VPC CNI は native policy をサポートします。現在の AWS ガイドは、新規 Pod の rule を設定中に初期許可する standard startup mode と、初期拒否となり DNS/依存先への経路が必要な strict mode を区別しています。実際の policy-agent container と有効な event logging を確認し、古い「VPC CNI は policy 非対応」という説明を適用しないでください。

**standard networking.k8s.io/v1 NetworkPolicy** では、許可 traffic は加算され、rule に優先度や last-wins の競合解決はありません。隔離された送信元の egress と宛先の ingress の両方で接続を許可する必要があります。admin/cluster-wide/vendor の policy API は異なる意味を持つため、別途考慮します。HostNetwork の挙動も実装に依存するため、全 Pod に設定するのは安全な修正ではありません。

**範囲を限定した policy の例**

次の2つの document は `---` で分かれた object です。既存の backend namespace、frontend web Pod、database Pod、従来型 CoreDNS Pod endpoint を想定します。

```yaml
# Independent example for a reviewed backend namespace and traditional CoreDNS Pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: database
          podSelector:
            matchLabels:
              app: db
      ports:
        - protocol: TCP
          port: 5432
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
```

namespace selector と Pod selector は**同じ peer 内**なので、両方に一致する必要があります。peer を分けると OR になります。namespace 名には標準の kubernetes.io/metadata.name label を使います。独自の `name` label があるとは仮定しないでください。

default deny は backend の全 Pod を選択し、示した例外を受けるのは選択した API Pod だけです。他の backend workload や API 依存先には、別の確認済み許可が必要です。frontend egress や database ingress は設定しません。DNS rule の対象は CoreDNS Pod であり、すべての Auto Mode/NodeLocal resolver 経路ではありません。

適切な owner-managed test workload から、許可される frontend-web→API:8080、誤った namespace/label/port からの拒否、API→database:5432、実際の DNS 経路をテストします。後から作った label のない debug Pod は対象 Pod と異なる policy を受ける場合があります。ping だけでは TCP/UDP policy を証明しません。capture を許可する場合は、対象の network namespace/traffic と期間を制限します。別 Pod の tcpdump が他の Pod を観測できるとは限りません。

**Terraform の代替例**

```hcl
# Alternative owner for the same policy intent; do not also apply duplicate YAML.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}
resource "kubernetes_network_policy_v1" "api" {
  metadata {
    name      = "api-allow"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {
      match_labels = { app = "api" }
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "frontend" }
        }
        pod_selector {
          match_labels = { app = "web" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "database" }
        }
        pod_selector {
          match_labels = { app = "db" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}
```

所有者を1つにし、隔離環境で通信経路全体を確認/適用します。現行 Kubernetes provider field を確認しましたが、この監査では policy を適用せず traffic enforcement も試していません。version を固定しない Calico/Cilium の導入や aws-node image だけの変更は、一般的な policy 修正ではありません。現行実装がサポートする upgrade/migration 手順を使います。

**一覧表示は enforcement の証拠ではない**

元の `kube_networkpolicy_info`/`calico_denied_packets` の例は、想定した label でその metric があることを確認していませんでした。現行 kube-state-metrics は experimental な created/ingress-rule/egress-rule gauge を文書化しています。既存の単一クラスター scrape 構成と Grafana sidecar を前提に、次の ConfigMap は宣言済み policy の一覧を示します。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-policy-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  network-policy-dashboard.json: |
    {
      "uid": "eks-network-policy-inventory",
      "title": "Declared NetworkPolicy Inventory",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Declared policies by namespace",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_created{job=\"kube-state-metrics\"}))",
              "legendFormat": "{{namespace}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Declared ingress/egress rule counts",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_ingress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Ingress {{namespace}}"
            },
            {
              "refId": "B",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_egress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Egress {{namespace}}"
            }
          ]
        }
      ]
    }
```

experimental metric が公開されていることを確認し、job/UID/namespace selector を適合させます。rule がゼロなら deny-all の可能性があり、policy/rule 件数では dropped connection を測定したり enforcement を証明したりできません。telemetry がなければ正常ではなく unknown です。deny/allow の証拠には実装固有の有効な decision log/flow observability を使い、公表済み label/schema を確認します。“policy” を含むすべての log を denial と見なして、存在しない counter を作ってはいけません。

policy 削除、全 workload の hostNetwork 変更、VPC 再構築は、原因を見つけずに公開範囲を広げる可能性があります。失敗した通信の証拠を保全し、確認済みの policy/configuration だけを変更します。

参考: [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)、[VPC CNI policies](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)、[Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[kube-state-metrics policy metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md)

</details>

### 8. Helm deployment の問題を調べる最も効果的な方法は何ですか？

- A. すべての Helm release を削除する
- B. EKS クラスターを作り直す
- C. client/chart/dependency 設定、release 所有関係、権限、event、workload の挙動を調べる
- D. release manager をすべて手動 object に置き換える

<details>
<summary>解答を表示</summary>

**正解: C. client/chart/dependency 設定、release 所有関係、権限、event、workload の挙動を調べる**

client/chart の error、Kubernetes admission/権限、workload readiness、アプリケーションの挙動を切り分けます。Helm 2/Tiller は過去の移行に関する話です。現行 Helm 3/4 の操作に Tiller deployment は必要ありません。

**実際の release を調べる**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
HELM_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/helm-diagnosis.XXXXXXXX")
helm version --short
helm status "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > "$HELM_EVIDENCE/values.yaml"
helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  > "$HELM_EVIDENCE/manifest.yaml"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$HELM_EVIDENCE/events.txt"
printf 'Review protected evidence in %s\n' "$HELM_EVIDENCE"
```

query の失敗は権限/network/context の問題かもしれず、release がない証明にはなりません。values と rendered manifest に credential や Secret data が含まれることがあるため、保護し、共有前に redact します。app.kubernetes.io/instance のような label は慣例であり、所有関係の完全な一覧ではありません。release manifest で正確な resource を特定し、condition/event を調べます。

Helm client が使う Kubernetes identity と chart values が選ぶ workload ServiceAccount は別です。現行 `helm install --service-account` option はありません。chart の文書化された ServiceAccount value を使い、該当 actor の RBAC を確認します。impersonation には権限が必要で、EKS access policy のすべてを再現するとは限りません。

**変更前の設定検証**

```bash
set -euo pipefail
: "${CHART_DIR:?}"; : "${VALUES_FILE:?}"; : "${KUBE_VERSION:?Set the target capability version}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
RENDER_DIR=$(mktemp -d "$EVIDENCE_PARENT/helm-render.XXXXXXXX")
# For charts with dependencies, first review/commit Chart.lock and build from that lock.
helm lint "$CHART_DIR" --values "$VALUES_FILE"
helm template review "$CHART_DIR" --namespace review \
  --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
  > "$RENDER_DIR/rendered.yaml"
```

render/lint だけでは、server-side API/admission 互換性、CRD 導入、image 動作、readiness、アプリ test 成功は確認できません。`--debug` 付き install は実際に install します。`helm dependency update` は lock/dependency 選択を変更し得るため、再現性を保つには確認済み Chart.lock と `dependency build` を使います。lock がない場合、build が dependency を解決することがあります。それを lock 済み検証と説明しないでください。

resource 競合では既存所有者と意図した移行方法を特定します。release を自動 uninstall したり、残存 resource を削除したり、force/take-ownership を使ったり、別 release 名を選んだりしないでください。これらは data に影響したり controller を重複させたりします。管理下の upgrade の前に既存 values、schema/CRD、stateful dependency を保全します。

**Terraform Helm provider の意味**

この例はローカルで schema を確認した Helm provider 3.3 と、準備済み namespace/release owner を対象とします。長時間の apply で一度取得した短期 token を使わず、確認済み exec-credential flow の kubeconfig を使います。

```hcl
# Choose the existing release/configuration owner and reviewed chart artifact.
variable "verify_chart_provenance" {
  type = bool
}
provider "helm" {
  debug = false
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}
resource "helm_release" "example" {
  name              = var.release_name
  repository        = var.chart_repository
  chart             = var.chart_name
  version           = var.chart_version
  namespace         = var.release_namespace
  create_namespace  = false
  values            = [file(var.reviewed_values_file)]
  dependency_update = false
  lint              = true
  wait              = true
  wait_for_jobs     = true
  timeout           = 600
  atomic            = true
  verify            = var.verify_chart_provenance
  keyring           = var.chart_keyring
}
```

`lint` は有効な release field で、plan 中に Helm lint を実行します。`debug` は provider の設定で、helm_release の設定ではありません。provider 3.x は `set = [...]` のような nested value attribute を使います。上の values-file 形式は、繰り返しの古い set block を避けます。

`verify` は信頼済み keyring で chart package の provenance を検証するもので、Helm test hook は実行しません。実際の artifact に provenance/trust 設定がある場合だけ有効にし、配布方法も確認します。`wait_for_jobs` と `wait` は readiness/job の待機であり、すべての application test ではありません。`atomic` は Helm install failure の cleanup/upgrade rollback を行いますが、database/PVC のデータ復元や hook/CRD/外部副作用をすべて自動で元に戻すものではありません。

`set_sensitive` は表示上の redaction を行いますが、通常の state/release storage に保存される value の公開安全性は高めません。別管理の Secret への参照を使い、Terraform state と Helm release storage を保護します。このレビューでは provider apply や release installation はしていません。

**Chart test hook**

chart は `my-chart.fullname` を定義し、その Service 名を使い、設定した HTTP path を公開する必要があります。次は values 断片を含む、**別々の template file 2つ**です。

```yaml
# Relevant values fragment for the chart that owns the Service.
service:
  port: 80
tests:
  enabled: true
  image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
  apiPath: /api/health
```

`templates/tests/test-connection.yaml` として保存します。

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-connection" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v/" (include "my-chart.fullname" .) .Values.service.port | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

`templates/tests/test-api.yaml` として保存します。

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-api" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v%s" (include "my-chart.fullname" .) .Values.service.port .Values.tests.apiPath | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

test label に application selector label をコピーしていません。probe は応答を stdout に書き、Kubernetes API token を使わず、request/Pod の lifetime に上限があります。before-hook-creation は再実行を可能にし、次回実行/所有 resource の cleanup まで log を保持します。この HTTP check はすべての business behavior を検証しません。`/api/health` が実際に存在する必要があります。

既に準備された分離 test cluster では、release/namespace 名を明示します。

```bash
set -euo pipefail
: "${TEST_CONTEXT:?Set the owned disposable cluster context}"
: "${TEST_NAMESPACE:?Choose a new unique namespace}"
: "${TEST_RELEASE:?}"; : "${CHART_DIR:?}"; : "${VALUES_FILE:?}"
# Fails on an existing namespace rather than adopting it.
TEST_NAMESPACE_UID=$(kubectl --context "$TEST_CONTEXT" create namespace "$TEST_NAMESPACE" \
  -o jsonpath='{.metadata.uid}')
printf 'Test namespace: %s UID: %s\n' "$TEST_NAMESPACE" "$TEST_NAMESPACE_UID"
helm install "$TEST_RELEASE" "$CHART_DIR" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --values "$VALUES_FILE" --wait --timeout 5m
helm test "$TEST_RELEASE" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --logs --timeout 90s
```

失敗時は resource を残し、hook/workload log を調べます。namespace UID を記録し、test namespace だと確認してから cleanup します。既存 namespace を削除しないでください。変更 trigger のない以前の null_resource は、release 変更のたびに再検証される保証がありませんでした。

**静的 CI の例**

この workflow は、commit 済み dependency/Chart.lock と Secret を含まない `ci/values.yaml` を使って chart を確認します。chart path と対象 capability version は合わせてください。dependency のない chart では lock/build の step を省略します。クラスターは作らず runtime test 成功も主張しません。

```yaml
name: Static Helm chart validation
on:
  pull_request:
    paths:
      - charts/**
      - ci/values.yaml
      - .github/workflows/helm-validate.yml
permissions:
  contents: read
jobs:
  lint-render:
    runs-on: ubuntu-24.04
    env:
      CHART_DIR: charts/my-chart
      VALUES_FILE: ci/values.yaml
      KUBE_VERSION: "1.36.0"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Azure/setup-helm@9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310 # v5.0.1
        with:
          version: v3.21.3
      - name: Build reviewed dependencies, lint and render
        shell: bash
        run: |
          set -euo pipefail
          umask 077
          test -f "$CHART_DIR/Chart.lock"
          helm dependency build "$CHART_DIR"
          helm lint "$CHART_DIR" --values "$VALUES_FILE"
          helm template chart-ci "$CHART_DIR" --namespace chart-ci \
            --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
            > "$RUNNER_TEMP/chart-rendered.yaml"
```

setup action/release pin は公式 metadata と照合済みです。必要なら所有する使い捨て環境で integration/test-hook stage を別に実行します。chart-testing を使う場合は、report された release/namespace と test option を用います。chart directory 名は後続 `helm test` loop の契約ではありません。

すべての chart を削除する、EKS を作り直す、release manager をやめるだけでは、元の chart/権限/runtime 問題を診断できません。

参考: [Helm debugging](https://helm.sh/docs/chart_template_guide/debugging/)、[chart test](https://helm.sh/docs/topics/chart_tests/)、[Helm provider release](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release)、[setup-helm release](https://github.com/Azure/setup-helm/releases/tag/v5.0.1)、[Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3)

</details>

### 9. メモリリークと他の memory-pressure 原因を区別するため、何を調べますか？

- A. すべての Pod を再起動する
- B. node size だけを増やす
- C. memory/process evidence、limit、runtime profile、アプリケーション code を関連付ける
- D. node だけを追加する

<details>
<summary>解答を表示</summary>

**正解: C. memory/process evidence、limit、runtime profile、アプリケーション code を関連付ける**

working set の増加、OOMKilled container、MemoryPressure node は、単独ではメモリリークを診断しません。修正を選ぶ前に負荷、process lifetime/UID、heap/native memory、cache、limit を比較します。

**比較できる証拠の収集**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${APP_SELECTOR:?Set an explicit label selector}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MEMORY_DIR=$(mktemp -d "$EVIDENCE_PARENT/memory-observation.XXXXXXXX")
for sample in {1..10}; do
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$MEMORY_DIR/sample-$sample.time"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$APP_SELECTOR" -o json \
    | jq '[.items[] | {
        name:.metadata.name,uid:.metadata.uid,created:.metadata.creationTimestamp,
        node:.spec.nodeName,phase:.status.phase,
        resources:[.spec.containers[] | {name,resources}],
        containers:((.status.initContainerStatuses // []) + (.status.containerStatuses // []))
      }]' > "$MEMORY_DIR/sample-$sample.pods.json"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods \
    -l "$APP_SELECTOR" --containers > "$MEMORY_DIR/sample-$sample.usage.txt"
  if [ "$sample" -lt 10 ]; then sleep 30; fi
done
printf 'Observations saved to %s; these samples do not establish a leak.\n' "$MEMORY_DIR"
```

これは30秒間隔で10回観測するため、元の5分間の計測計画に command 実行時間を足した例です。監査中に実行していません。短時間の窓で長期リークを証明できません。query に失敗すると収集を停止して部分結果を残します。metric 欠落を使用量ゼロに変換しないでください。

不確かな Pod 名 prefix を label 値として使わず、kubectl の quantity 対応出力を使います。存在しない4列目で sort しないでください。Pod snapshot には UID と通常/init container の state を記録します。名前は置き換え後に再利用されることがあります。metric と status request は atomic snapshot ではありません。現在/直近の termination reason と restart count を調べますが、status に残る過去情報は限定的です。

**memory pressure の解釈**

- working set、RSS、管理対象 heap、native allocation は異なる計測値です。cache 増加や traffic 増加もリークに見えることがあります。
- node に空き memory があっても container が cgroup limit に達する場合があります。request/limit の差が大きいだけでは OOM 原因になりません。
- kubelet は node の process であり、kube-system で log を読む汎用 `kubelet-pod` ではありません。サポートされた node/monitoring 経路を使います。
- fragmentation は証拠を要する仮説です。定期 reboot や強制 GC は普遍的な修正ではありません。

**現行 metric と単位の例**

既存の単一クラスター kube-prometheus-stack 構成に対し、この rule は現行の container 単位 limit metric を使い、重複 exporter sample を減らし、欠落/ゼロ limit を除外します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: memory-observation
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
  - name: memory-observation
    rules:
    - alert: ContainerWorkingSetHigh
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Container working set is above 85% of its declared limit
        description: Inspect {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container
          }} and actual termination/pressure evidence.
    - alert: ContainerWorkingSetCritical
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Container working set is above 95% of its declared limit
        description: This is an observation threshold, not proof of a leak or guaranteed
          OOM prediction.
    - alert: ContainerWorkingSetGrowth
      expr: max by (namespace, pod, container) (deriv(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""}[30m]))
        > 5 * 1024 * 1024 / 60
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Estimated working-set slope exceeds 5 MiB/min
        description: The rolling 30-minute regression has stayed above the threshold;
          correlate with load and process lifetime.
    - alert: NodeMemoryPressure
      expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"})
        == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure
        description: Investigate node resources and workloads; this is distinct from
          a container limit OOM.
```

namespace/release/job selector を実際の導入に合わせます。この rule は通常 container の limit を扱います。init-container と Pod 単位 budget は別に確認します。正の limit が報告されない container はこの比率に含まれません。健全と見なさず、coverage を別に監視します。working-set/limit のしきい値は観測例で、heap leak detector ではありません。

ここで `deriv` が返すのは**バイト/秒**です。`5 * 1024 * 1024` を60で割るため、しきい値は **5 MiB/分**です。旧式は5 MiB/s と比較しながら説明では per minute としていました。30分の regression と `for: 30m` の保持は、全時点で単調増加した証明ではありません。scrape 欠落、restart、workload 変更も解釈に影響します。

**runtime profile の前提条件**

| Runtime | 適切な調査範囲 |
| --- | --- |
| JVM | 対象 JVM PID に対応する JDK tool/権限を使います。`jcmd PID GC.heap_info` はサポートされた調査コマンドです。native-memory report には起動時の tracking が必要です。heap dump は process を停止させたり Secret を含んだりする可能性があります |
| Node.js | 対象 process がサポートする inspector/profiling 機構を使います。`node --inspect` は新しい process を起動します。debugger access を制限します |
| Python | 実アプリケーションまたは制御した再現環境で profiling/tracemalloc を設定します。別の interpreter は既存 process の allocation を見ません。また Python allocation tracking が native RSS 全体を示すわけではありません |
| Go | 実際の保護された heap profile と、対応する binary/symbol 情報を pprof で使います。認証不要の profiling endpoint や既存の `/tmp/profile` があると決めつけません |

本番で使う前に tool/runtime version と収集負荷を確認します。稼働中アプリケーションに任意の profiling package を既定で install しないでください。このレビューでは JVM、profiler、heap dump、実メモリ実験は行っていません。

**アプリケーション設定の例**

元の256m/768m heap と1Gi container 値は説明用であり、測定された最適値ではありません。OpenJDK 21 は JAVA_TOOL_OPTIONS を読みます。JAVA_OPTS は image entrypoint が転送する場合にだけ有効です。command-line flag や _JAVA_OPTIONS がこれらを上書きする可能性があるため、実際の JVM option を確認します。JVM startup 時に option が表示される場合があり、Secret を含めないでください。

```yaml
# Pod-template fragment for an existing reviewed OpenJDK 21 application container.
# Merge through its owner; this is not a standalone Deployment manifest.
spec:
  template:
    spec:
      containers:
        - name: java-app
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 2Gi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 4Gi
          env:
            - name: JAVA_TOOL_OPTIONS
              value: >-
                -XX:+UseG1GC -XX:MaxGCPauseMillis=200
                -Xms256m -Xmx768m
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/diagnostics
                -XX:+ExitOnOutOfMemoryError
          volumeMounts:
            - name: heap-diagnostics
              mountPath: /diagnostics
      volumes:
        - name: heap-diagnostics
          emptyDir:
            sizeLimit: 2Gi
```

アプリケーションの実際の image、起動動作、他の環境変数/volume、security context を保ちます。diagnostic mount に UID が書き込めることを確認します。`MaxGCPauseMillis` は soft target です。heap は process memory の一部にすぎません。native allocation、thread、code/metaspace、その他 overhead 用に測定済みの余裕を残します。

disk-backed emptyDir は Pod 削除後に永続しません。artifact を意図的に収集/保護し、container PID 再利用時の filename collision を考慮します。kernel/cgroup の SIGKILL は JVM の heap dump 処理を妨げる場合があります。`ExitOnOutOfMemoryError` は JVM が投げる OOM を処理するだけで、dump を保証せず allocation 原因も解決しません。

従来の MEMORY_MONITOR_* 環境変数は JVM/Kubernetes の組み込み機能ではありません。Spring Actuator の liveness/readiness path は、アプリケーションが実際に有効にして公開した場合にのみ使えます。想像した URL ではなく実際の health contract を確認します。

**既存監視の管理**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

Kubernetes manifest provider は plan 時に PrometheusRule CRD を必要とします。同一 apply 内の Helm install に `depends_on` を指定するのは、schema discovery の一般的な解決策ではありません。既存 monitoring stack と問6の working-set panel を再利用します。別 stack を導入したり、説明のない dashboard file を参照したりしません。rule 選択、alert routing、実環境の telemetry 健全性を確認します。

A/B/D は一時的な capacity 緩和にはなるかもしれませんが、allocation 不具合を立証/修正しません。示された原因を記録し、代表的な負荷で実際の code/config 修正を検証します。

参考: [Prometheus deriv](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv)、[current Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)、[OpenJDK 21 option processing](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp)、[Java 21 options](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)、[jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html)

</details>

### 10. EKS の DNS 解決に失敗するとき、最も効果的な調査方法は何ですか？

- A. すべての Pod に固定 IP を割り当てる
- B. 実際の Pod resolver、DNS 実装、policy/transport、upstream 設定を追跡する
- C. すべての Service に ExternalName を使う
- D. VPC を再構築する

<details>
<summary>解答を表示</summary>

**正解: B. 実際の Pod resolver、DNS 実装、policy/transport、upstream 設定を追跡する**

問題が発生する Pod の resolver と失敗する名前から調べます。tool 不足、DNS answer、UDP/TCP transport、upstream/private zone 設定、アプリケーション cache を切り分けます。

**Pod の実際の経路を調べる**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,dnsPolicy:.spec.dnsPolicy,dnsConfig:.spec.dnsConfig}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Run only where the selected container actually has this diagnostic tool.
: "${DNS_TEST_NAME:?Set the actual Service FQDN or reviewed external name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

image に cat/nslookup がなくても DNS 障害とは限りません。対象 Pod の network/identity context を保つ準備済みの診断方法を使います。新しい debug Pod では label、policy、DNS 設定が異なる可能性があります。DNS server 自身の Service 名を解決できることに依存せず、実際の nameserver IP を使って resolver transport を調べます。必要に応じて UDP/TCP 53 を確認します。TCP のみの接続 test は DNS response を検証しません。

従来の CoreDNS では Deployment readiness、Service/EndpointSlice、設定、log を確認します。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"
# Traditional CoreDNS path only; pure Auto Mode node DNS is different.
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**Auto Mode node では CoreDNS は node system service として動きます。** Auto Mode のみの構成には従来の Deployment がない場合があります。混在クラスターでは非 Auto node 用に残す必要があります。どのクラスターでも Deployment がないのを障害と決めつけたり、Auto Mode に2つ目の node-local DNS service を導入したりしません。

**Resolver 設定と policy**

cluster DNS を使う通常 Pod 経路は ClusterFirst です。hostNetwork を意図的に設定した Pod が cluster DNS を使うには通常 ClusterFirstWithHostNet が必要です。DNS 修正のためだけに hostNetwork にすると isolation が変わるので、一般的な対処ではありません。DNSPolicy None には意図的に完全な resolver 設定が必要です。

旧 `169.254.20.10` は選択された NodeLocal DNSCache の IP で、VPC resolver の共通値ではありません。`8.8.8.8` のような public resolver は Kubernetes Service zone/private AWS name を解決せず、nameserver list は zone ごとの fallback を保証しません。`172.20.0.10` や public backup を固定指定せず、実際の CoreDNS/NodeLocal upstream と cluster domain を調べます。

standard CoreDNS Pod 向けの次の例は、選択した backend への DNS だけを許可します。適用前に他のアプリケーション egress をすべて確認します。

```yaml
# Example for application Pods using traditional CoreDNS Pod endpoints.
# This selects applications and isolates other egress unless another policy allows it.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-dns-egress
  namespace: applications
spec:
  podSelector:
    matchLabels:
      app: example
  policyTypes:
    - Egress
  egress:
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
```

送信元 egress と宛先 ingress の両方に許可が必要なことがあります。1つの peer 内では namespace と Pod selector は AND です。Auto Mode/NodeLocal 経路には実装固有の設定が必要です。Pod label selector が host-level cache を対象にすると仮定しないでください。別 Pod の tcpdump は別 workload の query を capture できません。該当 context で許可された短時間の capture を使います。

**VPC DNS 設定を正しく読む**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
VPC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsHostnames
DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$AWS_REGION" \
  --query 'Vpcs[0].DhcpOptionsId' --output text)
aws ec2 describe-dhcp-options --dhcp-options-ids "$DHCP_OPTIONS_ID" --region "$AWS_REGION"
```

DNS attribute は DescribeVpcs の field ではなく DescribeVpcAttribute から取得します。クラスター名と Region は明示します。任意の kubeconfig alias を分割してクラスター名を決めるのは安全ではありません。query 前にアカウント/context を確認します。共有 VPC 設定を変更する前に DHCP option、DNS routing/forwarding、private zone を確認します。新しい DHCP option set の作成/関連付けは一般的な修正ではありません。

**CoreDNS 設定と所有関係**

EKS managed CoreDNS add-on が導入済みなら、version/configuration と確認中候補の schema を調べます。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

custom zone/forwarder を保ち、health/ready plugin を実際の probe と一致させます。replica count、CPU/memory、PDB、placement、autoscaling は workload ごとの確認が必要です。旧3 replica/70Mi/170Mi 例は普遍的に最適な値ではありません。既存 Deployment を EKS-Distro 1.8.7 の古い image に置き換えたり、汎用 Corefile で local customization を上書きしたりしないでください。

Terraform 所有者は既存 add-on を管理し、既存 VPC を調べられます。

```hcl
# Existing EKS-managed CoreDNS for standard/mixed clusters only.
# Preserve/import the existing resource; do not duplicate its ownership.
resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.reviewed_coredns_version
  configuration_values        = file(var.complete_reviewed_coredns_config)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

# Read an existing VPC; do not add a second aws_vpc resource to repair DNS.
data "aws_vpc" "cluster" {
  id = var.cluster_vpc_id
}
output "vpc_dns_attributes" {
  value = {
    enable_dns_support   = data.aws_vpc.cluster.enable_dns_support
    enable_dns_hostnames = data.aws_vpc.cluster.enable_dns_hostnames
  }
}
```

完全な configuration file を、選択した add-on schema と現行設定に照らして検証する必要があります。PRESERVE は明示 payload の完全な merge を保証しません。[EKS upgrades](../../eks/08-eks-upgrades.md) の正確な update procedure に従い、実際の DNS 動作を確認します。この例は Auto Mode の node DNS を設定せず、共有 VPC の置き換えも許可しません。

**対応した標準 node 構成で使う任意の NodeLocal DNSCache**

[公式 install guide](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)と確認済みの release manifest を使います。旧い手書き DaemonSet は不完全でした。image だけ変更しても必要な interface、filtering rule、mount、upstream Service、kubelet 配線は追加されません。

| 判断項目 | 事前準備 |
| --- | --- |
| Local address | 競合しない node-local IP、実際の cluster domain/CoreDNS Service IP を選びます。IPv6 address/port 表記も考慮します |
| 既存 data plane | 文書化された iptables 経路では cache が local と CoreDNS Service IP で listen します。対応 IPVS 構成では local のみで listen し、kubelet の cluster-DNS 設定変更が必要です。他方式には現行の統合ガイドがあります |
| Manifest/configuration | 文書化された placeholder を render し、必要な privilege/interface/filtering/lock mount、probe、upstream 設定を保ちます。不完全な旧 DaemonSet に置き換えません |
| Workload 移行 | node/kubelet 設定と新規/既存 Pod resolver が合うことを確認し、段階的な rollout と cache/kubelet 変更双方の戻し方を計画します |
| Memory/運用 | query/cache/concurrency の観測から容量を決め、failure を監視し、再起動/rollout 中の DNS 維持を計画します |

NodeLocal DNSCache は cache miss を適切な upstream に転送します。すべての query を local cache hit にするものではありません。公式ガイドは OOM による終了後、packet-filtering rule が停止中の local cache を指したままになり、再起動まで DNS が中断する可能性を説明しています。小さな固定 memory request や cache 追加だけで性能が保証されるわけではありません。

このレビューでは DNS query、packet capture、CoreDNS 更新、NodeLocal 導入、Terraform apply を実行していません。選択した topology と仮定を管理環境で検証してください。

Pod 固定 IP、すべての Service に ExternalName、VPC 再構築では、失敗した resolver 経路は特定できません。実際の query/response、送信元 context、設定変更、復旧証拠を記録します。

参考: [EKS CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)、[Auto Mode DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[Pod DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)、[VPC DNS](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)、[NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)

</details>
