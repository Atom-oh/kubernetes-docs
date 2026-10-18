# EKS クラスター作成クイズ - パート 4

> **最終更新**: 2026年10月12日

このクイズでは、Terraform クラスターガイドをスケーリング、ID、ライフサイクル運用と結び付けます。最後のセクションでは Terraform 固有の概念を確認します。例では、レビュー済みのアカウント/Region/kubeconfig、IAM、およびネットワークの前提条件が必要です。この監査ではデプロイしていません。

## 基本概念の問題

1. Cluster Autoscaler と Karpenter のプロビジョニングにおける主な違いは何ですか？
   * A) CA は AWS マネージドサービスである
   * B) CA は既存のグループをスケールし、Karpenter は選択した個別のキャパシティをプロビジョニングする
   * C) CA は CPU のみを測定し、Karpenter は Pod 数のみを測定する
   * D) Karpenter は Kubernetes scheduler を置き換える

<details>
<summary>回答を表示</summary>

**回答: B) CA は既存のグループをスケールし、Karpenter は選択した個別のキャパシティをプロビジョニングする**

Cluster Autoscaler は、検出された事前定義済み node group/ASG のサイズを調整します。Karpenter は、NodePools および EC2NodeClasses を通じて選択された NodeClaims と EC2 キャパシティを作成します。Kubernetes が Pod をスケジュールします。Karpenter が Kubernetes scheduler を置き換えることはありません。

どちらも、スケジュールできないワークロード要求と配置制約を考慮します。どちらも単に「CPU 割合対 Pod 数」ではなく、実行中の EC2 インスタンスをその場でリサイズするものでもありません。Karpenter は異なるサイズのインスタンスでキャパシティを置き換えられます。VPA は別途 Pod リソース要求を管理します。

**Cluster Autoscaler の例:** EKS 1.36 では、一致するマイナーバージョンと、レビュー済み IAM および検出タグを備えた専用 ServiceAccount を使用します。Chart 9.59.0 には明示的な v1.36.1 イメージオーバーライドが必要です。インストール前に RBAC、イメージ、引数をレンダリングします。

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
レビュー済みのワークロード/データポリシーで別途必要とされない限り、ローカルストレージおよび system-Pod の保護機能を維持してください。1 つの CA 管理グループに含まれる混在インスタンスタイプは、CPU/メモリ/GPU の形状が同等であるべきです。

**Karpenter の例:** 互換性のある controller/CRD をインストールし、IAM、node authorization、検出タグ、中断処理、キャパシティ制限を個別に設定します。両方の AMI プレースホルダーを、クラスターのバージョンおよび各アーキテクチャに一致するレビュー済み AL2023 イメージに置き換えます。両方のアーキテクチャを許可する場合、ワークロードイメージも両方のアーキテクチャをサポートする必要があります。

```yaml
# Karpenter NodePool (karpenter.sh/v1) + EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_REVIEWED_AMD64_IMAGE
    - id: ami-REPLACE_WITH_REVIEWED_ARM64_IMAGE
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
| 比較項目 | Cluster Autoscaler | Karpenter |
| --- | --- | --- |
| スケーリング単位 | 既存の node-group/ASG キャパシティ | NodeClaims と選択された EC2 キャパシティ |
| 設定 | グループ、検出、IAM、controller | NodePools、EC2NodeClasses、IAM、controller |
| 削除 | スケジューリングおよび disruption チェックが必要 | consolidation、budget、disruption control の対象 |
| 元のガイドにある履歴上の所要時間の主張 | 2～10 分、未検証 | 1 分未満、未検証 |

元の所要時間の数値は、今回の監査で再現したベンチマークや現在のパフォーマンス保証ではなく、**未検証の履歴上の主張**として残されています。Node の起動、イメージ、quota、ワークロード制約は両ツールに影響します。この表から、コスト、簡潔さ、レイテンシについて普遍的な順位を推論しないでください。

</details>

2. 現行の EKS CreateNodegroup API にあるキャパシティタイプはどれですか？
   * A) Reserved、On-Demand、Spot
   * B) On-Demand、Spot、Dedicated
   * C) ON_DEMAND、SPOT、CAPACITY_BLOCK
   * D) Standard、Burstable、Compute-Optimized

<details>
<summary>回答を表示</summary>

**回答: C) ON_DEMAND、SPOT、CAPACITY_BLOCK**

現行の EKS CreateNodegroup API には **ON_DEMAND、SPOT、CAPACITY_BLOCK** が含まれます。managed node group は 1 つのキャパシティタイプを使用します。異なるキャパシティプールには別々のグループを使用してください。

On-Demand は Spot の回収を回避しますが、中断または可用性を保証するものではありません。Spot は余剰キャパシティを使用するため、中断に耐えられるワークロードが必要です。提示される割引率も、実際の節約を保証するものではありません。Reserved Instances/Savings Plans は請求の取り決めであり、CreateNodegroup の追加 enum 値ではありません。

Capacity Blocks は、サポートされるインスタンス/Regions 向けの、別個の期限付き予約ワークフローです。予約を対象とするカスタム launch template、一致する AZ/subnet、予約を考慮したスケーリングが必要です。EKS は予約終了の 40 分前にスケジュール済みスケールダウンを作成します。このアクションを変更または削除しないでください。以下の例は通常の On-Demand/Spot の代替であり、Capacity Block のプロビジョニングではありません。

**AWS CLI:** 未使用の node-group 名、既存の private subnets、および承認済みの EC2 node role（CNI のアイデンティティ連携に必要な設定を含む）を使用します。グループがアクティブになるまで待機してから、実際の Node/ワークロードの readiness を確認してください。

```bash
set -euo pipefail
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types t3.medium t3a.medium --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}"
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$NEW_NODEGROUP_NAME"
```
**eksctl の代替案:** 既存のクラスターおよび未使用のグループ名用の設定を保存してから、`eksctl create nodegroup -f nodegroups.yaml` を使用します。元の例にあった未サポートの `capacityType` フィールドではなく、`managedNodeGroups` および `spot` を使用してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: ng-on-demand
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 5
  spot: false
- name: ng-spot
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large]
  privateNetworking: true
  desiredCapacity: 2
  minSize: 0
  maxSize: 5
  spot: true
```
affinity/selectors と tolerations を使用して、適切なワークロードを配置します。managed node groups には組み込みの Spot rebalance/drain 処理があります。Node Termination Handler は汎用的な追加要件ではありません。PDB は EC2 が Spot インスタンスを回収することを防げず、すべての Pod が完全な中断時間を受け取るわけでもありません。checkpointing、余剰キャパシティ、中断からの復旧を計画してください。

</details>

3. 各 Fargate profile selector で必須のフィールドはどれですか？
   * A) インスタンスタイプ
   * B) Namespace。labels は任意
   * C) Security group ID
   * D) 最大 Pod 数

<details>
<summary>回答を表示</summary>

**回答: B) Namespace。labels は任意**

各 profile selector には **namespace** が必要で、labels は任意です。profile には name と Pod execution role も必要で、対象となる private subnets を使用します。security-group パラメータはありません。Pod security groups は別個にサポートされるポリシーメカニズムであり、Fargate-profile のフィールドではありません。

未使用の profile 名とレビュー済み private subnet ID を使用します。この selector は既存の CoreDNS の配置を変更せず、アプリケーション Pod のみを意図的に対象にします。

```bash
set -euo pipefail
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"fargate-lab","labels":{"app":"nginx"}}]'
aws eks describe-fargate-profile --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --fargate-profile-name "$NEW_FARGATE_PROFILE" \
  --query 'fargateProfile.{status:status,subnets:subnets,selectors:selectors}'
```
一致する Pod を起動する前に `ACTIVE` を待ちます。eksctl profile 定義の代替を以下に示します。作成前に、クラスターの private subnet 検出および execution-role の設定を検証してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: fp-application
  selectors:
  - namespace: fargate-lab
    labels:
      app: nginx
```
namespace とラベル付きワークロードは、引き続き別途作成する必要があります。複数の profile が一致する場合、Pod が `eks.amazonaws.com/fargate-profile` で一致する profile を選択しない限り、EKS は英数字の profile 名順を使用します。profile は immutable です。置き換え/削除はその Pod に影響します。

Pod execution role は Fargate infrastructure 用であり、アプリケーションの AWS アクセス用ではありません。IRSA などの互換性のある workload identity を使用します。EKS Pod Identity は Fargate ではサポートされません。CoreDNS を Fargate に移動するには、単に selector に `kube-system` を追加するのではなく、その compute configuration と一致する profile が必要です。

Fargate の料金は、要求リソースと overhead/rounding により決まる**プロビジョニング済みキャパシティ**に対して発生します。サンプリングされた CPU/メモリ使用量のみに課金されるわけではありません。`CapacityProvisioned` を確認してください。EKS Fargate は Spot、DaemonSets、privileged containers、host networking、または EBS-mounted workload volumes をサポートしません。永続 EFS は static provisioning を使用します。profile の一致だけでは file system/PV/PVC は作成されません。DNS、image pull、STS、その他必要なネットワークパスを考慮してください。

</details>

4. NodegroupUpdateConfig のフィールドではないものはどれですか？
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) ノードグループ操作のタイムアウト

<details>
<summary>回答を表示</summary>

**回答: D) ノードグループ操作のタイムアウト**

`NodegroupUpdateConfig` は、整数の `maxUnavailable`、整数の `maxUnavailablePercentage`、および `updateStrategy`（`DEFAULT` または `MINIMAL`）をサポートします。数または割合のいずれかを設定し、両方は設定しないでください。割合は `maxUnavailable` 自体の有効な値ではありません。

operation timeout は NodegroupUpdateConfig のフィールドではありません。`--force` は version-update リクエストに属し、Pod eviction protection を回避できます。保存される update-config 設定ではありません。CLI/IaC の wait timeout もサービス操作とは別物です。

```bash
set -euo pipefail
UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":2,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
割合を設定する場合は、`{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}` を使用します。version update を開始する前に、返された update ID を `Successful` まで追跡してください。`DEFAULT` は先に置換キャパシティを起動します。`MINIMAL` は、一時的な追加キャパシティを減らすために、選択した古い Node を先に終了します。

`update-lab` 内の、レビュー済みの 3 replica Deployment について、この PDB は voluntary eviction を制約します。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
PDB は一般的な可用性の保証ではありません。直接の削除、障害、ワークロード controller 自身の rollout は eviction とは異なります。余剰キャパシティ、readiness、volume を確認してください。すでに実行中の EKS update を単純に一時停止またはロールバックできるとは約束しないでください。以降に予定されている変更を停止し、該当する復旧手順に従ってください。

</details>

5. 通常の EKS version workflow でサポートされる control-plane upgrade ステップはどれですか？
   * A) 2 つのマイナーバージョンを直接飛ばす
   * B) 任意の upstream release に移行する
   * C) readiness チェック後、EKS がサポートする次のマイナーバージョンに移行する
   * D) 先に control-plane バージョンより上のバージョンへ Node をアップグレードする

<details>
<summary>回答を表示</summary>

**回答: C) readiness チェック後、EKS がサポートする次のマイナーバージョンに移行する**

EKS control-plane upgrade は、1.34 → 1.35 → 1.36 のように、**一度に 1 つのマイナーバージョン**ずつ進めます。各 target が EKS で提供されていることを確認してください。upstream Kubernetes release は EKS で利用可能である証明にはなりません。今日の Kubernetes 1.x workflow から、将来のメジャーバージョン upgrade policy を推論しないでください。

control plane をアップグレードする前に、EKS 手順で要求されるとおり managed および Fargate Node を現在のマイナーに合わせます。self-managed/hybrid Node は推奨どおり更新します。kubelet が API server より新しいバージョンであってはなりません。Kubernetes 1.28+ の一般的な skew 上限では、kubelet は最大で 3 マイナー古いことが許容されますが、これは EKS upgrade の前提条件を無視する推奨ではありません。

最初に insights、削除された API、add-on の互換性、キャパシティ、アプリケーション/データバックアップをレビューしてください。EKS は、DIY snapshot コマンド用の managed etcd に対する通常の管理者 shell access を提供しません。サポートされる cluster/resource および persistent-data の backup/restore 手順を使用してください。このコマンドは 1 マイナーずつ進めることのみを強制し、それらのチェックを置き換えるものではありません。

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${NEXT_KUBERNETES_VERSION:?Confirm the next supported EKS minor}"
CURRENT_KUBERNETES_VERSION=$(aws eks describe-cluster \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --query cluster.version --output text)
if [[ "$CURRENT_KUBERNETES_VERSION" =~ ^1\.([0-9]+)$ ]]; then
  CURRENT_MINOR="${BASH_REMATCH[1]}"
else
  printf '%s\n' 'Unexpected cluster version; stop and inspect.' >&2
  exit 1
fi
EXPECTED_NEXT_VERSION="1.$((CURRENT_MINOR + 1))"
[ "$NEXT_KUBERNETES_VERSION" = "$EXPECTED_NEXT_VERSION" ] || {
  printf '%s\n' 'Only the next minor version is allowed in this upgrade example.' >&2
  exit 1
}
CLUSTER_UPDATE_ID=$(aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --kubernetes-version "$NEXT_KUBERNETES_VERSION" \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$CLUSTER_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
その update ID が成功するまで待ち、その後、文書化された順序で Node と互換性のある cluster components を更新します。Cluster Autoscaler のマイナーをクラスターに合わせ、kubectl はサポートされる skew 内に収めます。

現行の EKS では、完了した in-place upgrade 後 7 日以内であれば、直前のマイナーへの条件付き rollback を提供します。そのバージョンで作成されたクラスターや extended-support 終了時の automatic upgrade では利用できません。最初に互換性のある Node/add-ons を準備してください。Auto Mode はその node rollback を管理します。rollback は etcd、workloads、persistent data を巻き戻しません。無条件の取り消しとして扱うのではなく、公式の rollback readiness 要件を確認してください。

</details>

## 短答式問題

6. EKS managed node group のインスタンスタイプを変更するにはどうすればよいですか？

<details>
<summary>回答と解説</summary>

インスタンスタイプがどこで設定されているかによって異なります。

* managed node group の `instanceTypes` で設定されたタイプは `UpdateNodegroupConfig` のフィールドではありません。古いグループを廃止する前に、置換グループを作成し、キャパシティを検証して、ワークロードを移行してください。
* グループが当初、EKS group フィールドではなくその template 内でインスタンスタイプを指定した**独自の custom launch template**で作成された場合、**同一 template**の新しいバージョンに更新できます。EKS が Node を入れ替えます。EKS 生成 template を変更したり、任意の template ID に切り替えられると想定したりしないでください。
* self-managed ASG の場合、launch-template update/instance refresh にも Kubernetes を認識した drain および lifecycle design が必要です。EC2 の置換だけでは PDB を考慮した migration にはなりません。

AMI architecture、drivers、Pod IP limits、labels/taints、storage topology、quotas、PDBs をレビューしてください。Terraform が所有する resources では、所有 state を通じて変更し、replacement actions を確認します。out-of-band CLI 変更を行って state が正しいままであると想定しないでください。

</details>

7. Kubernetes API endpoint への private access のみを許可するにはどうすればよいですか？

<details>
<summary>回答と解説</summary>

private access を true、public access を false に設定します。module v21 では、これらは `endpoint_private_access` と `endpoint_public_access` です。該当する場合は、所有する Terraform state を通じて変更してください。

public access を無効にする前に、管理者の接続済みネットワークから private endpoint への DNS、routes、security rules を検証してください。システムは VPC **または適切に接続された別のネットワーク**から到達できます。物理的に VPC 内に存在する必要はありません。これは Kubernetes API endpoint を変更するものであり、別個の AWS EKS service API へのアクセスを変更するものではありません。

API 所有クラスターの場合、同等の CLI 操作は次のとおりです。

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
その update ID を `Successful` まで追跡し、意図した management path から認証済み kubectl access をテストしてください。1 回の `InProgress` 応答は完了ではありません。

</details>

8. EKS Kubernetes version の support lifecycle はどのようなものですか？

<details>
<summary>回答と解説</summary>

EKS のマイナーバージョンには、**14 か月の standard support**が提供され、その後、追加の cluster-hour コストで**12 か月の extended support**が続きます。時計は upstream release 日ではなく、EKS release 日に開始します。

2026 年 10 月 12 日時点で、EKS は 1.34～1.37 を standard support、1.31～1.33 を extended support としてリストしています。EKS 1.37 は、8 月 26 日の upstream release 後、2026 年 10 月 1 日に利用可能になりました。deployment/upgrade target を選択する前に、現在の EKS release calendar を確認してください。

extended support はデフォルトで有効です。cluster upgrade policy は standard support 終了時の動作を決定します。extended support 終了後、EKS は control plane を最も古くサポートされる extended version に自動でアップグレードします。古いバージョンが更新なしで無期限に実行されることはありません。managed/self-managed/hybrid Node と add-ons にはそれぞれ独自の lifecycle actions が必要ですが、Auto Mode はその capabilities と Node を管理します。

古いクイズにあった固定の「4 バージョン」、「60 日通知」、または「2～3 か月の release lag」ルールに依存しないでください。実際のクラスターについて、公開されている日付と policy を使用してください。upstream Kubernetes には独自の support schedule があります。古い 9 か月という比較は現在のガイダンスではありません。

</details>

## ハンズオン問題

9. CPU 75% / memory 80% utilization targets と、初期値 3、範囲 2～10 Node の node group で Pod autoscaling を設計してください。

<details>
<summary>回答と解説</summary>

**Pod demand scaling** と **node capacity scaling** を分離します。Metrics Server と有効な container requests を用いて、CPU 75% および memory 80% の HPA resource-utilization targets を使用します。HPA は tolerance、limits、stabilization に従い、metrics から最大の replica recommendation を選択します。これは即時の「threshold exceeded」アラームではありません。

次に、min=2、max=10、initial desired=3 の managed node group に Cluster Autoscaler を使用します。同等の Terraform module node-group fields は `min_size`、`max_size`、`desired_size` です。所有する configuration をレビューしてください。この完全な eksctl 代替は、レビュー済みの既存クラスター上の新規 group 用です。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: autoscaling-workers
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  minSize: 2
  maxSize: 10
  desiredCapacity: 3
```
問題 1 の専用かつ認可済み Cluster Autoscaler setup を使用してください。bounds だけでは autoscaler は動作しません。CA はスケジュールできない Pod requests と removal constraints に反応します。要求された CPU/memory percentages 自体を実装するわけではありません。

新しい `autoscaling-lab` namespace で、次の Deployment/HPA は requests と両方の metrics を示します。Pod replica range 2～20 は Node range 2～10 とは別です。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: autoscaling-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: my-app}
  template:
    metadata:
      labels: {app: my-app}
    spec:
      automountServiceAccountToken: false
      containers:
      - name: web
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
承認済み load test のもとで、HPA conditions、metric availability、Pending reasons、autoscaler decisions を確認してください。replica が増加しても memory use は比例して低下しない可能性があるため、アプリケーションについてその metric を検証してください。これらの request/limit 値は例であり、測定済みの sizing ではありません。

同じ desired-capacity loop に、独立した ASG CPU/memory target-tracking policies を追加しないでください。これらは CA と競合する可能性があり、draining behavior も異なります。EC2 は通常の memory utilization をデフォルトでは提供しません。CA 以外の別設計には、正しく公開された custom metric と custom namespace が必要であり、想定上の `AWS/EC2` memory metric ではありません。この HPA+CA ソリューションにそのような ASG policy は不要です。

</details>

## 高度な問題

10. blue/green node-group upgrade、そのリスク、および保護された migration workflow を説明してください。

<details>
<summary>回答と解説</summary>

置換キャパシティを作成してテストし、段階的に移行して、アプリケーション/データの検証後にのみ古い group を廃止します。rollback が必要である間は、古いキャパシティと互換性のある state を維持してください。1 つのクラスターを共有することは、完全な分離や zero-downtime の保証ではありません。

quotas、subnet IPs、images/architecture、labels、taints、daemon overhead、PDBs、local data、volume AZ/attachment constraints をレビューしてください。StatefulSet membership 自体が volume を portable にするわけではありません。TTL を変更したり service mesh を追加したりする前に、DNS failures を調査してください。monitoring/log collectors が実際に新しい Node を対象にしていることを確認してください。

次の CLI 例は、未使用の green-group 名を使用する**API 所有グループ**用です。Terraform または eksctl/CloudFormation が所有する groups では、drift や orphaned stacks を避けるため、その所有者を通じて同等の変更を行ってください。

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${OLD_NODEGROUP_NAME:?}" "${GREEN_NODEGROUP_NAME:?}"
[ "$OLD_NODEGROUP_NAME" != "$GREEN_NODEGROUP_NAME" ]
OLD_NODEGROUP_ARN=$(aws eks describe-nodegroup --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$OLD_NODEGROUP_NAME" \
  --query nodegroup.nodegroupArn --output text)
aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME" --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --instance-types t3.large \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}" \
  --labels audit.example.com/pool=green
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME"
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l "eks.amazonaws.com/nodegroup=$GREEN_NODEGROUP_NAME" -o wide
```
node-group tag は、基盤となる ASG に Cluster Autoscaler discovery tags がある証拠ではありません。CA が管理する場合は、実際の ASG tags/IAM を検証してください。メインワークロードを移行する前に、新しい Node readiness と別途スコープされた canary workload を確認します。

確認済みの古い Node を一度に 1 つ drain します。これは意図的に、automatic emptyDir deletion および forced eviction を省略しています。

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
各ステップの後に readiness、application health、persistent data を検証してください。drain が失敗した場合は停止し、原因を解決します。すべてのワークロードが検証され、保持していた古い group が不要になった後にのみ、この別個の最終削除の前に、その元の ARN を比較してください。

```bash
# A separate final step for API-owned groups only.
: "${OLD_NODEGROUP_ARN:?Use the ARN captured before migration}"
if [ "${MIGRATION_VERIFIED:?Set yes only after application/data checks}" = yes ]; then
  CURRENT_OLD_GROUP_ARN=$(aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --nodegroup-name "${OLD_NODEGROUP_NAME:?}" \
    --query nodegroup.nodegroupArn --output text) || exit 1
  [ "$CURRENT_OLD_GROUP_ARN" = "$OLD_NODEGROUP_ARN" ] || {
    printf '%s\n' 'Node-group identity changed; no deletion attempted.' >&2
    exit 1
  }
  aws eks delete-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME" || exit 1
  aws eks wait nodegroup-deleted --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME"
fi
```

</details>


## Terraform の確認

11. terraform_remote_state の reader は何にアクセスできますか？
   * A) storage layer で宣言された outputs のみ
   * B) HCL は outputs を公開するものの、完全な state snapshot
   * C) どの条件でも sensitive values にはアクセスできない
   * D) 自身の module 内の resources のみ

<details>
<summary>回答を表示</summary>

**回答: B) HCL は outputs を公開するものの、完全な state snapshot**

state access は authorization boundary です。consumer が完全な snapshot を読む必要がない場合は、選択した values を別途公開してください。

</details>

12. EKS module v21 の例に一致する input 名はどれですか？
   * A) cluster_name および cluster_version
   * B) name および kubernetes_version
   * C) clusterId および versionNumber
   * D) cluster_addons および cluster_compute_config

<details>
<summary>回答を表示</summary>

**回答: B) name および kubernetes_version**

Module v21 ではこれらの inputs の名前が変更されました。aws_eks_addon.cluster_name などの AWS resource fields や cluster_name などの module outputs は、それぞれの文書化された名前を引き続き使用します。すべての出現箇所を一律に置換しないでください。

</details>

13. S3 backend の例について正しい説明はどれですか？
   * A) encrypt=true も state locking を有効にする
   * B) DynamoDB は唯一の locking option である
   * C) use_lockfile=true は S3 locking を有効にする。clients と lock-file IAM permissions を準備する必要がある
   * D) 1 つの lock がすべての state keys を調整する

<details>
<summary>回答を表示</summary>

**回答: C) use_lockfile=true は S3 locking を有効にする。clients と lock-file IAM permissions を準備する必要がある**

S3 lock files には Terraform 1.10+ を使用してください。DynamoDB locking は非推奨です。古い clients が依然として依存している間に table を削除するのではなく、連携して clients を移行してください。

</details>

14. aws_eks_pod_identity_association は Kubernetes ServiceAccount を作成しますか？
   * A) はい、cluster-admin とともに作成する
   * B) いいえ。namespace/ServiceAccount と、サポートされる agent/SDK path は別個の前提条件である
   * C) はい、Metrics Server をインストールする
   * D) Fargate でのみ作成する

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。namespace/ServiceAccount と、サポートされる agent/SDK path は別個の前提条件である**

association は AWS identity を既存の Kubernetes identity にバインドします。trust と permissions の scope を設定し、必要な session tags を有効なままにし、propagation を処理して、実際に assumed された role を検証してください。

</details>

15. module constraint ~> 21.0 が許可するものは何ですか？
   * A) 21.0.0 のみ
   * B) 21.0.x の patches のみ
   * C) 動作を保証せずに、22.0 未満の互換範囲 21.x の minor および patch versions
   * D) 将来のすべての major versions

<details>
<summary>回答を表示</summary>

**回答: C) 動作を保証せずに、22.0 未満の互換範囲 21.x の minor および patch versions**

~> 21.0.0 は範囲を 21.0.x に制限します。ガイドでは module versions を明示的に pin しています。.terraform.lock.hcl は remote module versions ではなく provider selections を記録します。適用前に保存済み plans をレビューしてください。

</details>

## 参考資料

- [API_CreateNodegroup.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)
- [ml-node-groups.html](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-groups.html)
- [fargate-profile.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)
- [fargate-pod-configuration.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [API_NodegroupUpdateConfig.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html)
- [launch-templates.html](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [kubernetes-versions.html](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [update-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [rollback-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [cas.html](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [horizontal-pod-autoscale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [s3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [remote-state-data](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
