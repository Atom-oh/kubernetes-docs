# EKS クラスター作成クイズ - Part 1

> **最終更新日**: 2026年10月12日

> コマンドはそれぞれ独立した例であり、上から順に一括実行するスクリプトではありません。専用のトレーニングアカウント/クラスター、レビュー済みのIAM権限、非公開の一時kubeconfig（`EXAMPLE_KUBECONFIG`）を使用してください。例示のIDと必須変数は置き換えてください。作成コマンドには料金が発生します。この監査ではソース、構文、ローカルfixtureを確認しましたが、AWSリソースの作成やアプリケーションの可用性確認はしていません。

このクイズでは、Amazon EKSクラスターの作成に関連する概念、ツール、ベストプラクティスへの理解を確認します。クラスターの作成方法、VPC設定、ノードグループのセットアップなどを扱います。

## 基本概念の問題

1. EKSコントロールプレーンを直接プロビジョニングする組み込みコマンドがないツールはどれですか？
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>答えを表示</summary>

**答え: D) kubectl**

kubectlはKubernetes APIを通じてリソースを管理しますが、EKSをプロビジョニングするネイティブコマンドはありません。ACKなど、すでに導入済みのインフラストラクチャコントローラーはkubectlで作成したリソースをEKSクラスターに反映できますが、それはコントローラーとの連携であり、kubectlにAWS操作機能が組み込まれているわけではありません。

Amazon EKSクラスターの作成には、次のツールを使用できます。

1. **AWS Management Console**:
   * WebインターフェースからEKSクラスターを作成できます。
   * クラスターのコンポーネントを視覚的に設定できるため、初心者にも使いやすい方法です。
   * ステップごとのウィザードで作成手順を案内します。
2.  **AWS CLI**:

    * コマンドラインからEKSクラスターを作成します。
    * `aws eks create-cluster`コマンドを使います。
    * スクリプトや自動化に適しています。

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * EKSクラスター作成専用のコマンドラインツールです。
    * Weaveworksが開発したプロジェクトで、現在はAWSとコミュニティの協力を得てeksctl-io組織が保守しています。
    * 1つのコマンドでクラスターを作成できます。

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code (IaC) ツール**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    これらのツールを使うと、EKSクラスターをコードとして定義し、デプロイできます。

kubectlは、クラスター作成後にPod、Service、DeploymentなどのKubernetesリソースを管理するために使います。EKSクラスターに接続するには、通常`aws eks update-kubeconfig`を使うなどして、認可済みのkubeconfigを設定します。

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

その後、kubectlでクラスターのリソースを管理できます。

</details>

2. Amazon EKSクラスターの作成時に指定する必要があるVPCコンポーネントはどれですか？
   * A) Public subnetのみ
   * B) Private subnetのみ
   * C) 2つ以上のAvailability ZoneにまたがるSubnet
   * D) NAT Gateway

<details>

<summary>答えを表示</summary>

**答え: C) 2つ以上のAvailability ZoneにまたがるSubnet**

**解説:** Amazon EKSクラスターの作成時には、少なくとも2つのAvailability ZoneにあるSubnetを指定する必要があります。これはEKSクラスターの高可用性を確保するためのAWS要件です。

**EKSクラスターのVPC要件:**

1. **少なくとも2つのAvailability Zone (AZ) にSubnetが必要**:
   * EKSコントロールプレーンは複数のAvailability Zoneに配置されるため、クラスター作成時に2つ以上のAZにあるSubnetを指定します。
   * これによりリージョン内のコントロールプレーン可用性を支えます。ワークロードの可用性には、レプリカ配置、容量、ストレージ、依存関係の計画も必要です。
2. **Subnetの種類**:
   * Public subnetのみ、Private subnetのみ、または両方を組み合わせて使用できます。
   * 本番環境では、セキュリティのためワーカーノードをPrivate subnetに配置し、ロードバランサーにはPublic subnetを使う構成が推奨されます。
3. **SubnetのCIDRサイズ**:
   * 各クラスターSubnetには、EKS用に少なくとも6個の空きIPアドレスが必要で、AWSは16個を推奨しています。ノード、Pod、ロードバランサーの容量は別途計画してください。
   * EKSは各PodにVPCのIPアドレスを割り当てるため、想定Pod数に応じた十分なCIDRブロックが必要です。
4. **タグ要件**:
   * 次のタグは特定の連携機能による検出/所有権管理に関するもので、EKSクラスター作成全般の必須要件ではありません。
     * 旧式またはコントローラー固有の所有権タグ: `kubernetes.io/cluster/<cluster-name>: shared`
     * Public subnet: `kubernetes.io/role/elb: 1`
     * Private subnet: `kubernetes.io/role/internal-elb: 1`

**eksctlを使ったVPC設定例:**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["203.0.113.10/32"]
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

**AWS CLIを使ったVPC設定:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

NAT Gatewayはインターネットへのアウトバウンド経路の一つです。必要なVPC endpoint、ミラーイメージ、プライベート接続を用意すれば、インターネットアクセスなしで運用することもできます。Private subnetへの配置とインターネットへのegressをなくすことは、別々の設計判断です。例のVPC、Subnet、クライアントCIDRはレビュー済みの実際の値に置き換えてください。

</details>

3. EC2ワーカーを使う一般的なEKSコントロールプレーン構成に必要なロールの分離はどれですか？
   * A) クラスターRoleだけが必要
   * B) EC2ノードRoleだけが必要
   * C) クラスターRoleとEC2ノードRoleを分ける
   * D) 両方をFargate実行Roleに置き換える

<details>
<summary>答えを表示</summary>

**答え: C) クラスターRoleとEC2ノードRoleを分ける**

クラスターRoleは`eks.amazonaws.com`を信頼し、EKSによるクラスターインフラの管理を許可します。一般的なEKS構成では`AmazonEKSClusterPolicy`または同等の権限が必要です。EC2ノードRoleは`ec2.amazonaws.com`を信頼し、インスタンスプロファイル経由で渡します。EKSはマネージドノードグループ用のインスタンスプロファイルを設定します。ノードのBootstrap処理がIAM Roleを作成するわけではありません。

EC2の基本権限は`AmazonEKSWorkerNodePolicy`と`AmazonEC2ContainerRegistryPullOnly`または同等の最小権限です。CNIの権限も必要です。IRSA/Pod Identity用に独立したRoleを使う方法を推奨します。そうしない場合、ノードRoleにCNI権限が必要になります。IPv4用の`AmazonEKS_CNI_Policy`はIPv6用ポリシーではありません。ストレージ、ロードバランサー、ログコントローラーの権限が、すべてのノードで必須というわけではありません。

この例では一般的なクラスターRoleとノードRoleを新規作成します。認可済みのアカウント/Roleを使用し、エラーが出たら停止してください。名前が競合しても既存Roleにポリシーが追加されるわけではありません。

```bash
IAM_EXAMPLE_DIR=$(mktemp -d /tmp/eks-iam-example.XXXXXX)
: "${IAM_EXAMPLE_DIR:?}"
: "${NEW_CLUSTER_ROLE_NAME:?Choose an unused role name for this example}"
: "${NEW_NODE_ROLE_NAME:?Choose a different unused role name}"
cat > "$IAM_EXAMPLE_DIR/cluster-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "eks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
cat > "$IAM_EXAMPLE_DIR/node-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
# Attach policies only after successfully creating the new role.
aws iam create-role --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/cluster-trust.json" &&
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

if aws iam create-role --role-name "$NEW_NODE_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/node-trust.json"; then
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy &&
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
fi
```

`CreateCluster`でコントロールプレーンだけを作る場合、EC2ノードRoleはまだ必要ありません。EC2コンピューティングを追加するときに用意します。Fargateでは専用のPod実行Roleを使い、アプリケーションのAWS権限とは分離します。Auto Modeには追加のクラスターPolicyと`sts:TagSession`、最小限のノードRole Policyが必要です。プロビジョニング主体に必要な`iam:PassRole`などの権限は別途確認してください。

[ノードRole要件](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Auto ModeのRole](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. eksctlを使ってEKSクラスターを作成する正しいコマンドはどれですか？
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>答えを表示</summary>

**答え: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**解説:** eksctlを使ってEKSクラスターを作成する正しいコマンドは、`eksctl create cluster --name my-cluster --region us-west-2`です。このコマンドは、指定した名前とリージョンに、デフォルト設定でクラスターを作成します。

**eksctlコマンドの構成:**

* `eksctl`: 基本コマンド
* `create`: リソースの作成操作
* `cluster`: 作成するリソースの種類
* `--name my-cluster`: クラスター名
* `--region us-west-2`: AWSリージョン

**基本的なクラスター作成コマンド:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

デフォルト値はeksctlのバージョンによって異なります。下の設定ファイルでは、EKSバージョン、AL2023、ノード数、API endpointを明示してください。クラスター作成ではVPC、ノード、IAMリソースがプロビジョニングされることがあります。認可済みのテストアカウントで設定と料金を確認してください。

**追加オプションを指定するコマンド:**

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --managed
```

**設定ファイルを使ったクラスター作成:**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR:?Set your approved client CIDR}"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: false
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**ほかの選択肢が誤りである理由:**

* `eksctl create-cluster`: コマンド形式が誤っています。eksctlではコマンドをハイフンではなく空白で区切ります。
* `eksctl new cluster`: `new`は有効なeksctlコマンドではありません。
* `eksctl start cluster`: `start`は有効なeksctlコマンドではありません。存在しない動詞を使わず、文書化されたライフサイクルコマンドを使ってください。

eksctlにはEKSクラスター管理用の各種コマンドがあります。

* `eksctl create cluster`: 新しいクラスターを作成
* `eksctl get cluster`: クラスター一覧を取得
* `eksctl upgrade cluster`: クラスターをアップグレード
* `eksctl delete cluster`: クラスターを削除
* `eksctl create nodegroup`: ノードグループを追加
* `eksctl scale nodegroup`: ノードグループをスケール

</details>

5. 新しいEKSクラスターで選択できるKubernetesバージョンはどれですか？
   * A) 最新のアップストリームバージョンのみ
   * B) 常に最新バージョンとその2つ前のバージョン
   * C) 対象リージョンのEKS標準サポートまたは延長サポートで提供されているバージョン
   * D) すべてのKubernetesバージョン

<details>
<summary>答えを表示</summary>

**答え: C) 対象リージョンのEKS標準サポートまたは延長サポートで提供されているバージョン**

EKSのマイナーバージョンは、EKSでのリリース日から**14か月間の標準サポート**を受け、その後**有償の延長サポートを12か月間**受けます。2026年10月12日時点の公式一覧では、標準サポートが**1.34～1.37**、延長サポートが**1.31～1.33**です。EKS 1.37はアップストリーム版リリースの2026年8月26日より後の10月1日に利用可能になりました。新規クラスターで利用できるバージョンは対象リージョンで確認してください。

延長サポートはデフォルトで有効です。アップグレードポリシーやサポート終了日によってコントロールプレーンが自動アップグレードされる場合があります。ノードとアドオンの更新は別途計画してください。サポート期間を最大限使うためにアップグレードを遅らせるのではなく、AWSのサポート終了通知に従ってください。

以下は、バージョンの確認、設定生成、AWSでの作成、既存クラスターのアップグレードという別々の例です。認可済みの対象、Role、Subnet、CIDRを準備してください。作成例とアップグレード例を一連の手順として無条件に実行しないでください。

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table

# Generate a versioned config for review; this does not create the cluster.
EKS_VERSION_DIR=$(mktemp -d /tmp/eks-version.XXXXXX)
: "${EKS_VERSION_DIR:?}"
eksctl create cluster --name "${NEW_CLUSTER_NAME:?}" --region "$EXAMPLE_REGION" \
  --version 1.36 --dry-run > "$EKS_VERSION_DIR/version-example.yaml"
# Review all generated defaults, AMI, endpoint CIDRs and costs before creating.

# AWS CLI creation uses --kubernetes-version; the API JSON field is version.
aws eks create-cluster --name "$NEW_CLUSTER_NAME" --region "$EXAMPLE_REGION" \
  --kubernetes-version 1.36 --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API \
  --resources-vpc-config "subnetIds=${SUBNET_A:?},${SUBNET_B:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"

# Updating an existing control plane is a separate operation.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query cluster.version
# Only after upgrade-readiness checks and choosing the next supported minor:
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

コントロールプレーンを前方アップグレードする場合は、マイナーバージョンを一段階ずつ上げます。必要な機能、残りのサポート期間、アドオン/ワークロードとの互換性をまとめて確認してください。古いバージョンの方が常に安全だと考えず、対象バージョンをテストします。アドオンのメタデータからバージョン文字列を検索するだけでは、クラスターのバージョン確認にはなりません。

[EKSのバージョンライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. それだけではEKSワークロードのコンピューティングを提供しないものはどれですか？
   * A) マネージドノードグループ
   * B) セルフマネージドノードグループ
   * C) Fargate Profile
   * D) Kubernetes Namespace

<details>

<summary>答えを表示</summary>

**答え: D) Kubernetes Namespace**

NamespaceはKubernetesリソースを整理するものであり、コンピューティングを提供しません。マネージドEC2ノードグループ、セルフマネージドEC2ノード、Fargate Profileはコンピューティングを提供する方式です。EKS Auto Modeも管理対象ノードをプロビジョニングし、Hybrid Nodesは顧客管理のオンプレミス/エッジ容量を接続します。これらの仕組みがすべてマネージドノードグループAPIを使うわけではありません。

以下の作成コマンドは、すでに存在するクラスターに対する代替案であり、まだ使われていないグループ/Profile名を前提とします。必須変数をすべてレビュー済みの値に置き換えてください。CNI/ノードの認可とPrivate subnetの接続性を確認します。FargateにはPod実行Role、対応するPod、Private subnetが必要で、Profile自体はアプリケーションPodを作成しません。

**1. マネージドノードグループ:**

* **特徴**:
  * AWSがノードのプロビジョニングとライフサイクルを管理
  * EC2インスタンスの作成と登録を自動化
  * ASG (Auto Scaling Group) の設定を自動化
  * オペレーターが開始するノードKubernetesバージョン更新
  * EC2のヘルスチェックに基づくノード交換。EKSのノード修復には、対応するヘルスシグナルと設定が必要
  * マネージドワークフローを通じてオペレーターが開始するAMI更新
*   **作成方法**:

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-mng --managed --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --nodegroup-name my-mng --ami-type AL2023_x86_64_STANDARD \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role "${NODE_ROLE_ARN:?}"
    ```

**2. セルフマネージドノードグループ:**

* **特徴**:
  * ユーザーがノードのプロビジョニングとライフサイクルを管理
  * より多くのカスタマイズが可能
  * カスタムAMIやBootstrapスクリプトを使用できる
  * 特定のインスタンスタイプや設定要件に対応しやすい
*   **作成方法**:

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-smng --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Fargate Profile:**

* **特徴**:
  * サーバーレスのコンテナ実行環境
  * ノード管理が不要
  * Podごとにリソースを割り当てて課金
  * Namespaceとラベルに基づいて対象を選択
*   **作成方法**:

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --selectors '[{"namespace":"my-namespace","labels":{"app":"my-app"}}]'
    ```

**各選択肢の比較:**

| 項目 | マネージドノードグループ | セルフマネージドノード | Fargate |
| --- | --- | --- | --- |
| インフラ管理 | AWSが交換ワークフローを管理。更新/スケーリングはオペレーターが設定 | AMI、Bootstrap、ライフサイクルをオペレーターが管理 | AWSがホストを管理。ユーザーはアプリ、Profile、リソース要求を管理 |
| コスト | インスタンス、利用率、契約、運用を含めて評価する | 運用と合わせて最適化を評価する | 割り当てるPodサイズ、実行時間、制約を比較する |
| スケーリング | 別途ノードオートスケーラー/ポリシーが必要 | 別途自動化が必要 | 条件に一致するPodのコンピューティングを提供。アプリのレプリカ数は別途スケーリングする |

Auto ModeのNodePoolとFargate Profileは、EC2マネージドノードグループとは異なるリソースです。Fargateでもワークロード、セキュリティ、可用性の管理が必要で、常に安価または高価とは限りません。

</details>

7. 新しいEKS 1.36ノード向けにAWSが公開しているEKS最適化AMIファミリーではないものはどれですか？
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>答えを表示</summary>

**答え: D) Ubuntu Core**

Ubuntu CoreをAWS公開のEKS最適化AMIとして扱わないでください。Canonical Ubuntu Serverイメージや顧客作成のAMIは、公開元、互換性、サポート経路が異なります。Ubuntu Coreとは別製品です。

**この例での選択肢**

- **AL2023**: EKS最適化AMIと`nodeadm` Bootstrapを使います。Kubernetesマイナー、CPUアーキテクチャ、リージョン、CNI互換性を確認してください。
- **Bottlerocket**: コンテナ向けOSです。一般用途のLinuxノードとは異なる設定/更新方法を使います。
- **Windows**: 対応するWindows Serverホスト/コンテナバージョンを合わせ、Windowsネットワーク、認証、システムワークロードの前提を準備します。これはAuto Mode/Fargate向けWindows例ではありません。

**AL2はレガシー環境からの移行元です。** EKS最適化AL2 AMIの公開/サポートは2025年11月26日に終了し、AL2 OSのサポートは2026年6月30日に終了しました。EKSのKubernetes延長サポートでAL2のサポートが延長されることはありません。新しいEKS 1.36デプロイにAL2を推奨しないでください。

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

マネージドノードグループのLaunch TemplateでもカスタムAMIを使えます。AMIを固定する場合はOS/ランタイム、クラスターのメタデータ、Bootstrap設定を確認します。任意のUbuntuイメージに`docker.io`だけをインストールしても、動作するEKSノードにはなりません。対象EKSバージョンに合うCanonicalイメージと、レビュー済みのeksctl/Launch Template設定を使ってください。高度な設問では、Launch Templateの`ImageId`、ノードグループの`amiType`、User Dataのマージ制約を区別します。

イメージ選択時は、セキュリティ更新、実測したワークロード性能、Kubernetes/ドライバー互換性、運用、GPUなどの特殊要件を確認してください。

[AL2移行](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Windowsの前提条件](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. CreateCluster APIでendpoint accessを指定しなかった場合のデフォルトはどれですか？
   * A) Publicは有効、Privateは無効
   * B) Privateのみ
   * C) 両方のendpointが有効
   * D) 作成後に変更できない

<details>
<summary>答えを表示</summary>

**答え: A) Publicは有効、Privateは無効**

APIのデフォルトはPublic有効、Private無効です。eksctl、CDK、Consoleの作成経路では別の設定を明示できるため、すべてのツールに共通するデフォルトではありません。作成後にもアクセス設定を変更できます。

| Public | Private | アクセス経路 |
| --- | --- | --- |
| On | Off | Public endpointと`publicAccessCidrs`。ノード/CIの実際のegressアドレスも考慮する |
| On | On | VPC内からPrivate経路でアクセス。外部からのアクセスは許可Public CIDRに従う |
| Off | On | VPCまたは接続済みネットワークからPrivate経路でアクセス |
| Off | Off | 無効な設定 |

**クラスターのSecurity Groupが制御するのはPrivate endpointとkubeletのトラフィックであり、Public endpointへのアクセスではありません。** `publicAccessCidrs`が適用されるのはPublic endpointだけです。ネットワーク到達性とは別に認証/認可が必要です。IPv4の例示CIDRを実際に承認されたクライアントegressアドレスに置き換えてください。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.resourcesVpcConfig

# Select the actual approved client egress CIDR, not an arbitrary example range.
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text)
: "${ENDPOINT_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Public accessを無効にする前に、直前の更新が`Successful`であることと、管理/CIネットワークからPrivate DNS、ルーティング、APIにアクセスできることを確認します。非同期の更新を重ねて直ちに送信せず、両方のアクセスFlagを1回のリクエストで設定してください。

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

Private APIアクセスとインターネットegressの排除は別々の設計判断です。Identity、ネットワーク、運用制御を合わせて評価してください。Private accessだけでセキュリティや可用性が保証されるわけではありません。VPN、Direct Connect、管理ホスト、接続費用を考慮します。IPv6 endpointやHybrid Nodesには、公式ガイダンスに記載された追加のDNS/CIDR考慮事項があります。

[クラスターendpointアクセス制御](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. Amazon EKSクラスターのノードグループ用インスタンスタイプの選定に関係しないものはどれですか？
   * A) ワークロード要件（CPU、メモリ、ストレージ）
   * B) コスト最適化
   * C) kubeconfigのローカルcontext alias
   * D) インスタンス世代（例: t3とt2）

<details>

<summary>答えを表示</summary>

**答え: C) kubeconfigのローカルcontext alias**

kubeconfigのaliasはローカルクライアント上の名前であり、インスタンスの性能、料金、利用可能性を変えません。一方、必要なAZでそのタイプが提供されるか、実際の容量、アカウントのquotaは重要な制約です。

**ノードグループ用インスタンスタイプの実際の選定要素:**

1. **ワークロード要件（CPU、メモリ、ストレージ）**:
   * アプリケーションのリソース要件に合うインスタンスタイプを選ぶ
   * メモリ集約型ワークロード: r5、r6gなどのメモリ最適化インスタンス
   * コンピューティング集約型ワークロード: c5、c6gなどのコンピューティング最適化インスタンス
   * バランス型ワークロード: m5、m6gなどの汎用インスタンス
   * GPUワークロード: p3、g4dnなどのアクセラレーテッドコンピューティングインスタンス
2. **コスト最適化**:
   * On-DemandとSpotの比較
   * Reserved InstanceまたはSavings Plans
   * 過剰プロビジョニングを避けた適正サイズの選択
   * ARMベースのGravitonインスタンス（例: m6g、c6g）によるコスト削減
3. **インスタンス世代**:
   * 実際のワークロードに対する世代別の価格/性能を比較する
   * バースト可能なファミリーでは、CPU Creditの動作とベースライン性能も確認する
   * 新しい世代ではネットワークやストレージ性能などが向上している
4. **ネットワーク要件**:
   * 拡張ネットワーク（ENA、EFAなど）への対応
   * ネットワーク帯域幅の要件
   * インスタンスあたりの最大Pod数に関するネットワーク制約
5. **ストレージ要件**:
   * インスタンスローカルストレージが必要か（例: i3、d3インスタンス）
   * EBS最適化への対応
   * ストレージのスループットとIOPS要件
6. **CPUアーキテクチャ**:
   * x86（Intel、AMD）とARM（AWS Graviton）の比較
   * アプリケーション互換性

**Availability Zoneとノードグループの配置:**

必要なAZのカバレッジは、利用できるインスタンスタイプを制約します。カタログ上の提供は、すぐに容量を確保できる保証ではありません。

* 高可用性のため、ノードグループを複数のAZに配置する
* ノード容量とPodのtopology spreadを計画し、実際の配置を確認する
* リージョン内すべてのAZまたは特定のAZを選択できる

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster "${EXAMPLE_CLUSTER:?}" --region us-west-2 \
  --name my-nodegroup --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**インスタンスタイプの選択例:**

1. **Webアプリケーションサーバー**:
   * 汎用インスタンス: t3.medium、m5.large
   * バランスのよい性能とコスト効率
2. **データベース**:
   * メモリ最適化インスタンス: r5.xlarge、r6g.xlarge
   * CPUに対するメモリ比率が高い
3. **バッチ処理**:
   * コンピューティング最適化インスタンス: c5.xlarge、c6g.xlarge
   * 高いCPU性能
4. **機械学習ワークロード**:
   * GPUインスタンス: p3.2xlarge、g4dn.xlarge
   * アクセラレーテッドコンピューティング機能

上のファミリーは例であり、現行製品一覧や実測性能の順位ではありません。必要なAZでのワークロード、価格、アーキテクチャ、ドライバー、提供状況と容量をまとめて確認してください。

</details>

10. Amazon EKSクラスター作成後にkubectlを設定する正しいコマンドはどれですか？
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>答えを表示</summary>

**答え: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**解説:** Amazon EKSクラスター作成後にkubectlを設定する正しいコマンドは、`aws eks update-kubeconfig --name my-cluster --region us-west-2`です。AWS CLIのEKS機能を使い、指定したクラスター用にkubeconfigファイルを更新します。

**kubectl設定の手順:**

1. **kubeconfigファイルの更新**:
   * kubeconfigにはkubectlがKubernetesクラスターと通信するための設定を保存します。
   * 選択順は`--kubeconfig`の明示指定、最初の`KUBECONFIG`パス、`~/.kube/config`です。
   * コマンドは選択したファイルにクラスター/exec認証設定をマージし、現在のcontextを変更します。クラスター権限を付与するわけではありません。
2. **コマンドの構成要素**:
   * `--name`: EKSクラスター名
   * `--region`: クラスターがあるAWSリージョン
   * `--kubeconfig`（省略可）: 独自のkubeconfigファイルパス
   * `--role-arn`（省略可）: クラスターアクセスに使用するIAM Role
3.  **完全なコマンド例**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
4.  **追加オプション**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
5.  **設定の確認**:

    ```bash
    # Check current context
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # List all contexts
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # Test cluster connection
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**ほかの選択肢が誤りである理由:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: このコマンドは存在せず、AWS CLIに`get-kubeconfig`サブコマンドはありません。
* `kubectl config set-cluster my-cluster --region us-west-2`: 構文が誤っています。`kubectl config set-cluster`は`--region`Flagに対応せず、EKSクラスターに必要な認証情報を自動設定もしません。
* `eksctl configure kubectl --name my-cluster --region us-west-2`: このコマンドは存在せず、eksctlに`configure kubectl`サブコマンドはありません。eksctlでクラスターを作成するとkubeconfigは通常自動設定されますが、既存クラスターでは`aws eks update-kubeconfig`または`eksctl utils write-kubeconfig`を使ってください。

**既存クラスターにeksctlで設定を書き出す:**

既存クラスター向けにkubeconfigを書き出し、新しいクラスターは作成しません。

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

これは既存クラスター用のkubeconfigを書き出します。IAM認証とAccess Entry/RBAC認可は別々に確認してください。作成を無効にしていない場合、クラスター作成時にもkubeconfigが書き出されます。

**複数クラスターの管理:**

複数のEKSクラスターを管理するには、各クラスターに対して`aws eks update-kubeconfig`を実行し、kubeconfigに追加します。

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Switch context
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

したがって、Amazon EKSクラスター作成後にkubectlを設定する正しいコマンドは`aws eks update-kubeconfig --name my-cluster --region us-west-2`です。

</details>

## ハンズオン演習

### 演習 1: eksctl を使用した EKS クラスターの作成

**シナリオ:** 開発チーム向けに、一般的なEC2マネージドノードグループを使うクラスターを準備します。これはトレーニング用の設計であり、本番環境への適合性や実測コストを示すものではありません。

**要件:** 2つのAZを使い、AL2023の`t3.medium`ノードを初期状態で2台、スケーリング範囲を2～5、ノードネットワークはPrivate、API endpointは両方有効にして承認済みPublic CIDRを指定します。範囲を設定しただけではオートスケーラーは導入されません。`t3.medium`を選ぶ前に、burstable instanceのCPU Credit、メモリ、IP容量、quota、実際のワークロード要件を確認してください。

<details>
<summary>答えを表示</summary>

**1. ツールとIdentityを準備する。** [Part 1](../../eks/02-eks-cluster-creation-part1.md)にあるchecksum検証済みのアーキテクチャ別インストール手順を使います。この例はEKS 1.36とeksctl 0.230.0を基準にレビューしました。実行前にリージョンで利用可能なEKSバージョンと、互換性のあるクライアント/アドオンバージョンを確認します。`kubectl`はバージョンスキューの制限を満たす必要があります。ログインユーザーが引き受けられる承認済みの既存オペレーターIAM Roleを使います。プロビジョニング権限とKubernetesアクセス権限は別です。

**2. 非公開のローカル設定を生成し、レビューする。** 生成する名前は新しいトレーニングクラスター用です。Public CIDRには実際に許可するegress範囲を指定してください。2つのAZは`us-west-2`用の例であり、提供状況と容量によって変わります。

```bash
# Use a dedicated training account/role with reviewed provisioning permissions.
aws sts get-caller-identity
eksctl version
kubectl version --client
EKS_LAB_DIR=$(mktemp -d /tmp/eks-creation-lab.XXXXXX)
: "${EKS_LAB_DIR:?}"
EKS_LAB_CLUSTER="creation-quiz-$(date +%s)-$$"
EKS_LAB_REGION=us-west-2
EKS_LAB_KUBECONFIG="$EKS_LAB_DIR/kubeconfig"
: "${APPROVED_API_CIDR:?Set your actual approved administration egress CIDR}"
: "${OPERATOR_ROLE_ARN:?Set an existing IAM role ARN, not an STS session ARN}"

cat > "$EKS_LAB_DIR/cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_LAB_CLUSTER}
  region: ${EKS_LAB_REGION}
  version: "1.36"
availabilityZones: ["us-west-2a", "us-west-2b"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR}"]
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: false
  accessEntries:
    - principalARN: "${OPERATOR_ROLE_ARN}"
      type: STANDARD
      accessPolicies:
        - policyARN: arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
          accessScope:
            type: cluster
managedNodeGroups:
  - name: dev-ng
    amiFamily: AmazonLinux2023
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    privateNetworking: true
    disableIMDSv1: true
    ssh:
      allow: false
    tags:
      Environment: development
      Owner: training
EOF

# Review the local configuration; this command does not create resources.
eksctl create cluster -f "$EKS_LAB_DIR/cluster.yaml" --dry-run \
  > "$EKS_LAB_DIR/resolved.yaml"
```

この設定はラボ専用に指定したオペレーターへcluster-adminを付与し、作成者への自動管理者アクセスは無効化します。オペレーターRoleの作成や、呼び出し元にそのRoleを引き受ける権限を与えるものではありません。eksctlは必要なクラスター/ノードRoleを作成します。生成するPolicyの範囲をレビューしてください。一般的なEC2構成ではVPC CNIの権限をノードRoleに含める場合があります。ワークロードをより強く分離するには、公式CNI IAMガイダンスに従って専用の`aws-node` Roleを設定してください。後で使う可能性があるというだけで、イメージpush、DNS、ストレージ、ロードバランサー、ログの広範な権限をすべてのノードに追加しないでください。

**3. 設定とコストをレビューしてからプロビジョニングする。** 新しいVPCのデフォルト構成では、NATなど課金対象のインフラが作成されることがあります。`eksctl`はCloudFormationを使ってVPC/Subnet/Security Group/Role/クラスター/ノードグループを作成します。失敗しても一部のリソースが残る場合があります。完全に自動削除されたと思い込まず、スタックイベントを調べてください。

```bash
# Provisioning step: creates billable AWS resources.
if eksctl create cluster -f "${EKS_LAB_DIR:?}/cluster.yaml" --write-kubeconfig=false; then
  EKS_LAB_ARN=$(aws eks describe-cluster \
    --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
    --query cluster.arn --output text)
  : "${EKS_LAB_ARN:?Could not record the created cluster ARN}"
  aws eks update-kubeconfig --name "$EKS_LAB_CLUSTER" \
    --region "$EKS_LAB_REGION" --role-arn "${OPERATOR_ROLE_ARN:?}" \
    --kubeconfig "${EKS_LAB_KUBECONFIG:?}" --alias "$EKS_LAB_CLUSTER"
fi
```

**4. 実際の状態、アクセス、スケーリング範囲を確認する。** ノードグループ/クラスターが`ACTIVE`、ノードが`Ready`になるまで待ち、異常なシステムPodを確認し、想定したAZに配置されていることを調べます。作成APIの成功応答やRBACによる一覧表示だけでは、クラスターが安全に動作していることを確認できません。

```bash
aws eks describe-cluster --name "${EKS_LAB_CLUSTER:?}" \
  --region "${EKS_LAB_REGION:?}" \
  --query 'cluster.{status:status,version:version,endpoint:resourcesVpcConfig,access:accessConfig}'
aws eks describe-nodegroup --cluster-name "$EKS_LAB_CLUSTER" \
  --nodegroup-name dev-ng --region "$EKS_LAB_REGION" \
  --query 'nodegroup.{status:status,scaling:scalingConfig,ami:amiType}'
kubectl --kubeconfig "${EKS_LAB_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get pods -n kube-system
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" auth can-i get nodes
```

**5. 必要なコンポーネントだけを追加する。** Cluster Autoscalerを使うには、高度な設問2にある対象を絞ったIAM/ServiceAccount/検出設定が必要です。範囲を指定しただけではワークロード需要に応じて自動調整されません。`kubectl top`にはインストール済みで正常なMetrics Serverが必要です。監査したMetrics Server 0.9.0の基準ではKubernetes 1.34以降がサポートされています。実際に導入するバージョンを確認してください。コスト削減や適切なサイジングを主張する前に、代表的な利用状況を測定します。

**6. トレーニングクラスターを削除する。** ラボで作成したLoadBalancer Service/Ingressを先に削除し、ControllerがAWSリソースを解放するまで待ちます。PVCのreclaim policyと保持されるVolumeも確認してください。この演習自体はそのようなアプリケーションリソースを作成しません。その後、記録したクラスターだけを削除します。

```bash
# Only after removing this lab's workloads and checking retained resources.
if CURRENT_LAB_ARN=$(aws eks describe-cluster \
  --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
  --query cluster.arn --output text) &&
  [ "$CURRENT_LAB_ARN" = "${EKS_LAB_ARN:?Original cluster ARN required}" ]; then
  eksctl delete cluster --name "$EKS_LAB_CLUSTER" --region "$EKS_LAB_REGION" --wait
else
  printf '%s\n' 'Cluster lookup/identity mismatch; no deletion attempted.' >&2
fi
```

完了後にCloudFormationとAWSリソース一覧を確認し、削除失敗、保持Volume、個別作成したRole/endpointが残っていないか調べます。クリーンアップを確認するまでは設定/ARNの記録を保管し、不要になったらローカルの一時kubeconfigディレクトリを削除します。

</details>

### 演習 2: AWS Management Consoleを使用したEKSクラスターの作成

**シナリオ:** 後の本番環境へのデプロイで参考にできる、一般的なマネージドノードグループ設計を確認します。ワークロードのサイジング、ルーティング、IAM、高可用性、アップグレード、復旧は環境ごとに異なるため、検証が必要な前提です。この手順は監査時にプロビジョニングも負荷試験も行っていません。

<details>
<summary>答えを表示</summary>

**1. IAMロールを分けて準備する。**

- クラスターロール: `eks.amazonaws.com`を信頼し、`AmazonEKSClusterPolicy`をアタッチします。
- EC2ノードロール: `ec2.amazonaws.com`を信頼し、`AmazonEKSWorkerNodePolicy`と`AmazonEC2ContainerRegistryPullOnly`をアタッチします。対応している場合、VPC CNIには専用のIRSA/Pod Identityロールを付与します。より簡単なIPv4ノードロール方式を意図的に選ぶ場合は、`AmazonEKS_CNI_Policy`を明示的にアタッチし、権限を共有するトレードオフを記録します。
- プロビジョニング/オペレーターIdentity: リソースを適切にスコープした承認済みIAM権限と、これらのロールに対する`iam:PassRole`を使用します。既存のオペレーターRoleに、このラボで必要なアクセスPolicyを持つEKS Access Entryを追加します。kubeconfigを作成しただけではKubernetesの認可は付与されません。

**2. VPCとサブネットを確認する。** 次の公式サンプルは引き続き参照できます。URLの日付はEKSのバージョンを表しません。

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

一意のトレーニング用スタックを作る前にCloudFormationテンプレートを読みます。デフォルトでは**2つのAZにまたがるPublic subnet 2つとPrivate subnet 2つ、Internet Gateway、NAT Gateway/EIP各2つ**を持つVPCが作成されます。つまりNAT経由で外向きインターネット接続がある設計であり、egressのないPrivate Clusterではありません。本番環境でデフォルトをそのまま使わず、CIDRの重複、AZ、IP容量、NAT料金を確認してください。

`VpcId`、`SubnetIds`、`SecurityGroups`を記録します。`SubnetIds`には**Public subnetとPrivate subnetの両方**が含まれます。各Route Tableを調べ、ノードに使う実際のPrivate subnetを選択してください。出力されるカスタムSecurity Groupが、必要な通信ルールをすべて備えている証明にはなりません。EKS Cluster Security Group、追加のGroup、コントロールプレーンとノード間の通信ルールを確認します。

**3. 一般的なクラスターを作成する。** EKS Consoleでカスタム設定の経路を選び、この演習ではAuto Modeを無効にします。EKS標準サポート中の利用可能かつ互換性のあるバージョン（監査した例は1.36）、Cluster Service Role、確認済みのVPC/サブネットを選択します。

- API Access Entry認証を選び、指定したオペレーターに適切なアクセス権を付与します。理由が明確でない作成者管理者のデフォルトに依存しないでください。
- APIをPrivateのみで公開する場合は、先に管理ネットワークのPrivate Routing/DNSを確認します。またはPublic/Privateの両方を有効にし、`publicAccessCidrs`を承認済みの管理用egress範囲に制限します。
- この一般的なEC2クラスターでは、互換性のあるVPC CNI、kube-proxy、CoreDNSアドオンを維持し、それぞれの設定と権限を確認します。必要なコントロールプレーンログを有効にし、ログ料金を考慮してください。
- 設定を確認してクラスターを作成し、`ACTIVE`になるまで待ちます。作成時間は一定ではありません。所要時間の目安を完了判定に使わないでください。

**4. マネージドノードグループを追加する。** EC2ノードRole、AL2023 x86_64 AMI、例示用の`m5.large`などサポート対象のインスタンスタイプを選びます。この例は50 GiBのルートディスク、Desired size 3、最小2、最大5、確認済みのPrivate subnetを使います。これらはサイジング例であり、本番環境への推奨値ではありません。必要なAccess、IMDS、ストレージ暗号化を設定します。ノードグループが`ACTIVE`、ノードが`Ready`になるまで待ちます。

**5. アクセスを確認し、実際のAWS Security Groupを調べる。** Consoleに記録したクラスター名と承認済みのオペレーターRoleを使います。

```bash
CONSOLE_LAB_DIR=$(mktemp -d /tmp/eks-console-lab.XXXXXX)
: "${CONSOLE_LAB_DIR:?}"
CONSOLE_KUBECONFIG="$CONSOLE_LAB_DIR/kubeconfig"
aws eks update-kubeconfig --name "${CONSOLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --role-arn "${OPERATOR_ROLE_ARN:?}" \
  --kubeconfig "$CONSOLE_KUBECONFIG" --alias "$CONSOLE_CLUSTER"
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get pods -n kube-system

# Security groups are AWS resources; kubeconfig does not contain their rules.
aws eks describe-cluster --name "$CONSOLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_CLUSTER_SG_ID:?Copy the cluster SG ID from the result above}"
```

**6. NetworkPolicyの任意演習。** 選択したCNIとその設定がNetworkPolicyを適用することを、まず確認してください。AWS VPC CNIでPolicyをサポートするには、その機能を有効にし、ノード/OS構成も対応している必要があります。次のingress-onlyのデフォルト拒否Policyは、新規作成した空のラボNamespaceに限定します。egressは拒否せず、`apply`が成功しただけでPolicy適用を証明するものでもありません。

```bash
# An optional isolated policy example, after enabling CNI policy enforcement.
NP_LAB_NAMESPACE="np-quiz-$(date +%s)-$$"
if kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" create namespace "$NP_LAB_NAMESPACE"; then
  NP_LAB_UID=$(kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    get namespace "$NP_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}')
  : "${NP_LAB_UID:?Namespace identity lookup failed}"
  cat > "${CONSOLE_LAB_DIR:?}/default-deny.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: ${NP_LAB_NAMESPACE}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
EOF
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    apply -f "$CONSOLE_LAB_DIR/default-deny.yaml"
fi
```

実際のワークロードで使う前に、専用のテストPodで許可/拒否される通信を検証し、アプリケーションに必要な許可Policyを追加します。既存の共有`default` Namespaceには適用しないでください。完了したら分離したNamespaceを削除します。

```bash
# Remove only the namespace created above, after confirming its UID.
if CURRENT_NP_UID=$(kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" \
  get namespace "${NP_LAB_NAMESPACE:?}" -o jsonpath='{.metadata.uid}') &&
  [ "$CURRENT_NP_UID" = "${NP_LAB_UID:?Original namespace UID required}" ]; then
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" delete namespace "$NP_LAB_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace lookup/identity mismatch; no deletion attempted.' >&2
fi
```

**7. Consoleでのクリーンアップ:** ラボのワークロードを削除し、関連するCloud Resourceが解放されるのを待ちます。次に、このラボのマネージドノードグループを削除して削除完了を待ち、ラボクラスターを削除します。ラボVPCのCloudFormation Stackは、EKS Resourceと外部依存関係がなくなってから削除してください。このラボ専用に作成したIAM Role/Endpointのみを削除し、共有Resourceは維持して、削除に失敗したResourceや保持されたResourceを確認します。このレビューでは削除操作を実行していません。

</details>

## 高度なトピック {#advanced-topics}

次はAmazon EKSクラスター作成に関する高度なトピックの設問です。EKSクラスター作成の高度な概念とベストプラクティスについて理解しているか確認します。

1. EKS EC2マネージドノードグループでカスタムLaunch Templateを使う主な利点は何ですか？
   * A) クラスター作成が必ず短時間になる
   * B) ノードのUser DataやVolume設定をカスタマイズできる
   * C) コントロールプレーンのプラグインをインストールできる
   * D) 新しいAMIが公開されるたびに、既存ノードすべてが自動更新される

<details>
<summary>答えを表示</summary>

**答え: B) ノードのUser DataやVolume設定をカスタマイズできる**

Launch Templateでは、**EC2マネージドノードグループ**のストレージ、インスタンスメタデータ、OS固有のUser Dataなどをカスタマイズできます。EKSコントロールプレーンやEKS Auto Modeノードを設定するものではありません。

**AL2023 User Data:** MIME multipart形式を使います（User DataのMIME boundaryはテンプレートの一部として保持）。AMIをEKSに選択させる場合（テンプレートに`ImageId`がない場合）、EKSがNode Configurationを提供/マージします。カスタムAMI IDを指定する場合は、高度な設問5にある完全な`NodeConfig`を指定します。AL2023のsystemd serviceが`nodeadm`を実行するため、`/etc/eks/bootstrap.sh`を呼んだり、`nodeadm init`を再実行したり、kubeletを手動起動したりしないでください。追加Softwareは選択したOSに対応し、信頼できるPackage Sourceへ到達できる必要があります。

これはEKS選択のAL2023 AMIを使う最小限のカスタマイズ例です。アプリケーション用Directoryを作成するだけです。

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_CUSTOMIZATION"

--EKS_CUSTOMIZATION
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_CUSTOMIZATION--
```

**ストレージ:** 次は`LaunchTemplateData`の有効な例のひとつです。AMIのルートデバイス名を確認してください。VolumeをアタッチしただけではFormatもMountもされません。例のVolumeは両方とも暗号化され、インスタンス削除時に削除されます。ノード置換後も保持する必要があるアプリケーションデータには、CSI管理のPVと適切なReclaim/Backup Policyを使います。

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    },
    {
      "DeviceName": "/dev/sdf",
      "Ebs": {
        "VolumeSize": 500,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }
  ]
}
```

**ネットワークとMetadata:** 例のSecurity Groupは、コントロールプレーン、ノード、DNS、ワークロードに必要な通信を許可するRuleを持つものに置き換えます。カスタムSecurity Groupを指定すると、EKSはCluster Security Groupを**自動追加しません**。Security GroupはインスタンスレベルまたはNetwork Interfaceレベルのいずれか一方で指定してください。

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "Groups": ["sg-0123456789abcdef0"],
      "DeleteOnTermination": true
    }
  ],
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

Hop Limitが1の設定は、PodがノードCredentialではなくIRSAまたはEKS Pod Identityを使う前提です。ContainerからIMDSv2へのAccessを必要とするワークロードでは、Hop Limitを2にする必要がある場合があります。この設定もIMDSv2も、`hostNetwork` Podを分離するものではありません。複数のNetwork Interface、Placement、Instance Store Deviceは、対応するインスタンスタイプとEKS Launch Templateの制約を満たす必要があります。どのインスタンスでも自由に選べるオプションではありません。

**ノードグループを作成する:** 実際のID、権限、ネットワークRouteを確認してから、eksctl設定例またはAWS CLI例のどちらかを選びます。両方を続けて実行する手順ではありません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    subnets: ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

```bash
# Use an existing reviewed template version and a new node group name.
aws eks create-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --launch-template "id=${LAUNCH_TEMPLATE_ID:?},version=${LAUNCH_TEMPLATE_VERSION:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --node-role "${NODE_ROLE_ARN:?}"
```

`SubnetId`と`IamInstanceProfile`はLaunch Templateに含めません。サブネットとノードIAM Roleはノードグループ要求側の設定です。Launch Templateを使う場合、ノードグループ側で`diskSize`や`remoteAccess`も設定しないでください。インスタンスタイプはTemplateまたはノードグループ要求のいずれか一方で指定します。`ImageId`がある場合、ノードグループの`amiType`、`releaseVersion`、`version`は省略し、カスタムAMIのkubeletとコントロールプレーンの互換性を確認してください。

明示的な`ImageId`があればAMIは固定されます。`ImageId`のないTemplateではEKS選択のAMIを使えます。どちらの場合も、新しいAMIが公開されるたびに既存ノードが自動更新されるわけではありません。カスタムTemplateを更新するには、**同じ**Templateの新しいVersionを作成して、ノードグループ更新を明示的に行います。これによりインスタンスが置換されます。

参考資料: [Launch Templateの制約](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[CreateNodegroupのフィールド](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[AL2023初期化](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)

</details>

2. それだけではEKSのコスト最適化として不十分な方法はどれですか？
   * A) 中断を許容できるワークロードでSpotを使う
   * B) Cluster Autoscalerを設定し、認可する
   * C) 測定せずにすべてのワークロードへ最新世代のインスタンスを選ぶ
   * D) ワークロード要件と総コストを比較してFargateを選択的に評価する

<details>
<summary>答えを表示</summary>

**答え: C) 測定せずにすべてのワークロードへ最新世代のインスタンスを選ぶ**

最新世代という理由だけですべてのノードを選んでも、コスト分析として十分ではありません。ワークロードのArchitecture、Throughput、Latency、Memory、Regionでの提供状況、中断許容度を比較します。新世代の方が効率的な場合もありますが、同じ処理を完了するコストが新旧どちらで必ず安くなるということはありません。

1. **SpotとInstance Typeの分散:** AWSはOn-Demandに比べて最大90%の割引を提示しています。これは本ラボで実測した割引でも、保証された節約額でもありません。中断と代替Capacityを考慮してください。Cluster Autoscalerでは、同じノードグループ内で異なるTypeを混在させる場合、SchedulerのSimulationが先頭のTypeを使うため、CPU/Memory/GPUの構成を揃えます。Local Diskの依存関係も個別に確認してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: spot-ng
    amiFamily: AmazonLinux2023
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 5
```

2. **Cluster Autoscaler:** 最小/最大サイズはスケーリング範囲を指定するだけです。スケジュールできないPodや削除可能なCapacityに応じてDesired Capacityを変更するControllerをインストールし、認可する必要があります。すべてのノードに広範なAuto Scaling権限を付与しないでください。**新規インストール**の前に、専用IRSA Role（OIDC Trustを対象Service Accountに限定）またはサポート対象のPod Identity設定を用意し、`kube-system/cluster-autoscaler` Service Accountを準備します。スケーリング書き込み権限は対象ClusterのAuto Scaling Groupに限定します。Groupには`k8s.io/cluster-autoscaler/enabled=true`と`k8s.io/cluster-autoscaler/<cluster-name>=owned`のTagを付けます。ノードグループResource Tagがあるだけでは、ASG Discoveryが設定済みとは限りません。

ControllerのMinor Versionはクラスターと合わせます。Chart 9.59.0のデフォルトはController 1.35.0のため、このEKS 1.36の例では1.36.1を明示的に選択します。他のCluster Versionでは一致するController Versionを選んでください。同じGroupを管理するCAがすでに存在しないか確認します。

```bash
# EKS 1.36 example: first prepare the dedicated service account/IAM role
# and discovery tags on the target Auto Scaling groups.
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  --set-string "autoDiscovery.clusterName=${EXAMPLE_CLUSTER:?}" \
  --set-string "awsRegion=${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  --wait --timeout 5m
```

3. **Fargateと適正サイジング:** Fargateはホスト管理の作業を減らしますが、測定したCPU使用量だけでなく割り当てたResourceと実行時間に対して課金されます。Profileを対応PodやPrivate subnetのNetworkingに合わせ、総コストをEC2と比較します。`kubectl top`にはMetrics Serverが必要で、短い使用量サンプルはCapacity Planになりません。
4. **Graviton:** ARM Node Groupを作成する前に、ARM64 Imageと依存関係をテストします。世代固有の「価格性能比が最大40%向上」という主張は、請求額が一律40%下がる保証でも、性能が等しい保証でもありません。

```bash
# Metrics Server must already be installed and healthy.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top nodes
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top pods --all-namespaces

# Alternative compute examples: each creates separately billed resources.
eksctl create fargateprofile --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name fp-dev --namespace dev
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name arm-ng \
  --managed --node-ami-family AmazonLinux2023 \
  --node-type m6g.large --nodes 2 --node-private-networking
```

5. **利用コミットメント:** Reserved InstanceとSavings Plansは、対象となる予測可能な使用量のコストを下げられます。「最大72%節約」という表示は商品、期間、支払い方法、使用量に依存し、使われないコミットメントは節約効果を損ないます。
6. **RequestsとLimits:** 値を選ぶ前に代表的なワークロードを測定します。RequestはスケジューリングとAutoscalerの判断に影響します。Limitが小さすぎるとCPU ThrottlingやOOM Terminationが起こる可能性があります。次はContainerごとの例示値です。

```yaml
# Fragment inside spec.template.spec.containers[].
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

7. **コスト配賦:** Cost Explorerと、設定済みの配賦Report/Toolを使います。Kubernetes Labelが自動的に有効化済みAWS Cost Allocation Tagになるわけではありません。コントロールプレーン、該当する場合のAuto Mode料金、Storage、Load Balancer、NAT、転送量、Loggingの費用を含めてください。

参考資料: [EKS上のCluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)、[CA Chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler)、[CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1)、[Spot料金](https://aws.amazon.com/ec2/spot/)、[Fargate料金](https://aws.amazon.com/fargate/pricing/)、[Graviton](https://aws.amazon.com/ec2/graviton/)、[Savings Plans](https://aws.amazon.com/savingsplans/)

</details>

3. Kubernetes APIをPrivateのみにし、ノード/PodからのインターネットへのOutbound通信もなくす要件を、両方満たす設計はどれですか？
   * A) Private API、Internet EgressのないPrivate Node Subnet、必要なService Endpoint、Privateな管理経路
   * B) Private Nodeだけにして、APIとEgressの設定はそのままにする
   * C) Public/PrivateのKubernetes API Endpointを両方無効にする
   * D) Public APIを無効にする一方、NAT Egressは制限しない

<details>
<summary>答えを表示</summary>

**答え: A) Private API、Internet EgressのないPrivate Node Subnet、必要なService Endpoint、Privateな管理経路**

2つの判断を分けてください。**誰がKubernetes APIに到達できるか**と、**ノード/Podがどこへ通信を送れるか**です。APIをPrivateのみで公開してもNAT Routeはなくならず、ワークロードのEgressが遮断されたり、すべてのPacketが1つのVPC内に留まったりするわけではありません。経路、DNS、Security Group、認可が許せば、接続されたネットワークからPrivate APIへ到達できます。

この設問の要件はAPIをPrivateのみで公開し、ノード/PodからインターネットへのOutboundもなくすことです。Private Endpointを有効にし、Public Endpointを無効にし、Internet Egress経路のないPrivate Node Subnetを使います。ワークロードに必要なService Endpoint、Registry Image、管理経路も用意してください。

**Endpoint切替:** まずPrivate Accessを有効にし、更新成功を待って、想定したPrivate Networkから認証付き`kubectl` Accessをテストします。その後で、下の別方式でPrivateのみの設定にします。返されたUpdateが`Successful`になるまで確認してから、再度Accessを試してください。Public Endpointは`publicAccessCidrs`で制限します。Cluster Security GroupはPublic EndpointではなくPrivate Endpointへの通信を制御します。

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

**Node配置:** この断片は既存のVPCとPrivate Subnetを使います。IDを置き換え、使用前にRouteを確認してください。VPC Endpointの作成や既存NAT Routeの削除は行いません。インターネット接続しかない別のWorkstationでeksctlを実行しても、Private-onlyのKubernetes APIにはAccessできません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
managedNodeGroups:
  - name: private-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true
```

**AWS Serviceへの接続:** 次のECR/S3例は設計の一部にすぎません。Private DNSの重複Conflictを避けるため、まず既存Endpointを確認してください。Interface EndpointにはPrivate DNSと、利用対象ClientからのHTTPS Ingressが必要です。S3 Gateway EndpointにはPrivate Route Tableと適切なEndpoint/Bucket Policyが必要です。

```bash
# Example fragments for a reviewed no-internet VPC design.
# Interface endpoint SG must allow HTTPS from the intended nodes/clients.
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.api" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.dkr" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.s3" \
  --vpc-endpoint-type Gateway \
  --route-table-ids "${PRIVATE_ROUTE_TABLE_A:?}" "${PRIVATE_ROUTE_TABLE_B:?}"
```

| 依存関係 | Internet経路がない場合のPrivate接続 |
| --- | --- |
| Private ECRからのImage Pull | `ecr.api`、`ecr.dkr`、S3 Gateway。Public Imageは到達可能なPrivate Registryにコピーする |
| Node/CNIが使うEC2 API | `ec2`、適切な権限とEndpoint Policy |
| IRSA Credential | Regional `sts`。SDKがRegional Endpointを使うよう設定する |
| VPC内からのOIDC Discovery/JWKS | 例: IAM OIDC Provider設定時の`oidc-eks`。STSとは別 |
| EKS Pod Identity Credential | `eks-auth`とサポート対象のPod Identity Agent/設定 |
| EKS Management API | `eks`。Kubernetes API Private Endpointの代替ではない |
| Log、Autoscaling、Load Balancing、SSM | 実際に使うServiceのEndpointと権限。SSMにはMessaging接続も必要 |

Endpoint ServiceとDNS名はRegion/Partitionによって異なります。Image Registry、Package Download、外部API、Addon機能など、各ワークロードの依存関係をすべて確認してください。あるAWS ServiceのEndpointが汎用インターネット接続の代わりになるわけではありません。

**管理:** Route設定済みのVPN/Direct Connect、Private Accessが可能な管理Host、または適切に設定したSSM Sessionを使います。BastionにPublic IPが必須とは限りません。SSMにもAgent、IAM認可、Serviceへの接続性が必要です。

NAT経由のPrivate NodeとPrivate APIを組み合わせる設計もEKSで有効ですが、この設問のInternet Egressなしという要件は満たしません。同様に、SubnetにPublic Routeがあるだけでは、個別Nodeがインターネットから到達可能とは証明できません。Addressの割当とSecurity Controlが関係します。

参考資料: [Private Clusterの要件](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[API Endpoint Access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[EKS PrivateLinkとOIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)

</details>

4. 新しいNode AMIを適用する際、EKSマネージドノードグループの仕組みではないものはどれですか？
   * A) マネージドRolling Updateでインスタンスを置き換える
   * B) 別のBlue/Green Node Groupを作成して検証する
   * C) インスタンスを置き換えず、実行中インスタンス上でOS Packageを更新する
   * D) 小規模なCanary Node Groupで新AMIを検証してから、広範に置換する

<details>
<summary>答えを表示</summary>

**答え: C) インスタンスを置き換えず、実行中インスタンス上でOS Packageを更新する**

EKSマネージドノードグループの更新ではEC2インスタンスを置き換えます。実行中インスタンス上のOS Package更新は、マネージドAMI更新の仕組みではありません。「In-place Upgradeはすべて非対応」と曖昧に説明しないでください。AWSはNode Group Resourceを保持したままLaunch TemplateのAMI Versionを変える意味でもこの語を使いますが、その場合もインスタンスは置換されます。

**Rolling Update:** `DEFAULT`は古いNodeを退役させる前に置換Capacityを作成します。`MINIMAL`は置換Node作成の前に選択した古いNodeを終了させる場合があります。`maxUnavailable`のデフォルトは1ですが変更可能なため、常に一度に厳密に1 Nodeというわけではありません。Quota、AZ Capacity、Pod配置、Update Strategyを確認します。カスタムAMIの場合は、同じLaunch Templateの新しいVersionを明示的に選択してください。次のCommandはEKS選択AMIの例です。

```bash
# EKS-selected AMI case: inspect first, then initiate a reviewed update.
aws eks describe-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'nodegroup.{status:status,version:version,ami:amiType,release:releaseVersion,update:updateConfig}'
if NODE_UPDATE_ID=$(aws eks update-nodegroup-version \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODE_UPDATE_ID" \
    --region "$EXAMPLE_REGION" \
    --query 'update.{status:status,errors:errors}'
fi
```

返されたUpdate IDを記録し、Updateが終端状態になるまで`describe-update`を繰り返します。APIの送信成功は完了を意味しません。次へ進む前に、報告されたErrorを調べてください。Evictionを妨げるPDBは`PodEvictionFailure`の原因になることがあります。Commandを完了させる目的だけで`--force`により回避しないでください。

**Blue/Green:** 互換性のあるAL2023 Node Groupを別に作成し、ワークロードのSchedulingとReady状態をテストしてから段階的に移行します。アプリケーションの確認、Volume/AZ制約、Rollback要件を満たすまで旧Capacityを維持してください。Node Labelを一覧しただけでは検証になりません。TrafficはNode Group名ではなくService Endpoint/Podに向かいます。新しいGroupを作成した直後に旧Groupを自動削除しないでください。

**Canary:** Label/Taintを分けた小規模Groupを使います。Taintは無関係なPodが配置されにくくし、テスト対象WorkloadだけがNodeを選択してTolerateします。System DaemonSetは該当するTolerationがあれば実行されます。次は既存のテストクラスター用の例示設定です。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: canary-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 1
    minSize: 1
    maxSize: 2
    privateNetworking: true
    labels:
      example.com/upgrade-track: canary
    taints:
      - key: example.com/upgrade-track
        value: canary
        effect: NoSchedule
```

この完全なサンプルDeploymentを適用する前に、専用のテストContextに未使用の`upgrade-lab` Namespaceを作ります。実際のCanaryでは、アプリケーション独自の依存関係と代表的なTrafficも試す必要があります。このNGINX Podが確認するのは基本的なSchedulingとReady状態だけです。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: upgrade-canary
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      nodeSelector:
        example.com/upgrade-track: canary
      tolerations:
        - key: example.com/upgrade-track
          operator: Equal
          value: canary
          effect: NoSchedule
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
```

**Disruption BudgetとCapacity:** 次の別例は、通常Ready Replicaが3つ以上ある、`app-namespace`内の実際の`my-app` Workloadを想定します。上記のReplicaが1つだけのCanary用PDBではありません。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-namespace
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

PDBはEviction APIで処理される自発的なEvictionを制限しますが、可用性を保証したり、Hardware Failureや直接のPod/Deployment削除を防いだりするものではありません。Healthyな該当Podが2つだけの場合、`minAvailable: 2`はEvictionを阻止します。余剰Capacity、Topology、Probe、終了処理、FailureからのRecoveryを確認してください。Blue/GreenやCanaryの計画だけでは、安全なRollbackを証明できません。Stateful Dataがある場合は特に注意します。

参考資料: [マネージド更新の動作](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)、[AL2023移行](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[Pod Disruption Budget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)

</details>

5. EKS最適化AL2023 EC2 WorkerのBootstrapに含まれない操作はどれですか？
   * A) kubelet/Container Runtimeを設定する
   * B) AWS管理のControl Plane ComponentをWorkerへインストールする
   * C) Node Clientの認証/接続性を設定する
   * D) Nodeを登録する

<details>
<summary>答えを表示</summary>

**答え: B) AWS管理のControl Plane ComponentをWorkerへインストールする**

WorkerにAPI Server、etcd、Controller Manager、Schedulerをインストールすることはありません。これらはAWS管理Control Planeの構成要素です。**一般的なEKSのCoreDNSはData Plane側のCluster Addonであり、Control Plane Componentのひとつではありません。**

EKS最適化AL2023 AMIは、containerdとkubeletの設定に`nodeadm`を使います。`nodeadm-config`はUser Dataより前に基礎設定を確立し、`nodeadm-run`はその後に設定を完了してDaemonを起動します。AMIがこれを自動実行するため、User Dataから`nodeadm init`を再度呼び出さないでください。AL2の`/etc/eks/bootstrap.sh`方式は、現在のAL2023 Bootstrap手順ではありません。

**Node JoinとCluster Networkingを分けて考える**

1. 起動前にNode IAM Role/Instance Profileと、必要なNode Access認可を用意します。BootstrapはIAM Roleを作成しません。Instance自体のRoleを不必要に再度想定する手動kubeconfigではなく、AMIが生成するkubeconfig/認証経路を使います。
2. kubeletがNodeを登録します。Readyになるかどうかは、Clusterへの接続だけでなくRuntime/CNIの健全性にも依存します。
3. 一般的なEKSでは、Cluster Addonとして`aws-node`、`kube-proxy`、CoreDNSをデプロイ/管理します。Host BootstrapがこれらすべてをAddonとしてインストールするわけではありません。実在しないファイルでCNI設定を上書きしないでください。
4. Provider管理の`eks.amazonaws.com/nodegroup`や`topology.kubernetes.io/zone` Labelを手動で偽装しないでください。カスタムLabel/TaintはNode Group/Provisioner設定で管理します。

**NodeConfigの入力例**

次は管理Workstation上で、既存IPv4クラスターの実際のMetadataからUser Dataを生成します。EKS最適化AL2023ベースのカスタムAMI/セルフマネージドNode向けに確認した例です。カスタムAMI IDのないマネージドノードグループでは、EKSがMetadataの生成/マージを行います。`NodeConfig`はHost Bootstrap設定であり、`kubectl apply`で送信する通常のKubernetes Resourceではありません。

```bash
# Run on the administration workstation to prepare reviewed IPv4 node user data.
NODE_CONFIG_DIR=$(mktemp -d /tmp/eks-nodeconfig.XXXXXX)
: "${NODE_CONFIG_DIR:?}"
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster --output json > "$NODE_CONFIG_DIR/cluster.json" || exit 1

jq -e '
  (.name | type == "string" and length > 0) and
  (.endpoint | startswith("https://")) and
  (.certificateAuthority.data | type == "string" and length > 0) and
  (.kubernetesNetworkConfig.ipFamily == "ipv4") and
  (.kubernetesNetworkConfig.serviceIpv4Cidr | type == "string" and length > 0)
' "$NODE_CONFIG_DIR/cluster.json" >/dev/null || exit 1

jq '{
  apiVersion: "node.eks.aws/v1alpha1",
  kind: "NodeConfig",
  spec: {
    cluster: {
      name: .name,
      apiServerEndpoint: .endpoint,
      certificateAuthority: .certificateAuthority.data,
      cidr: .kubernetesNetworkConfig.serviceIpv4Cidr
    }
  }
}' "$NODE_CONFIG_DIR/cluster.json" > "$NODE_CONFIG_DIR/nodeconfig.json" || exit 1

{
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: multipart/mixed; boundary="EKS_NODE_CONFIG"\n\n'
  printf '%s\n' '--EKS_NODE_CONFIG' 'Content-Type: application/node.eks.aws' ''
  cat "$NODE_CONFIG_DIR/nodeconfig.json"
  printf '\n%s\n' '--EKS_NODE_CONFIG--'
} > "$NODE_CONFIG_DIR/user-data.mime"
printf 'Review user data: %s\n' "$NODE_CONFIG_DIR/user-data.mime"
# An EC2 LaunchTemplateData.UserData JSON field needs the MIME file base64 encoded.
# The console user-data editor can accept raw text when its encoding option is set accordingly.
```

すべてのNodeで同じDNS Service IPやmaxPods値を固定しないでください。Cluster Service CIDR、Instance/CNI/Prefix設定、ドキュメント記載のSizing Ruleに従います。次の確認Commandは一般的なEC2構成を対象にしています。Auto Mode/Fargateでは管理Componentが異なります。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

この監査では、Node Join、Daemonの実行、ネットワーク動作を実地検証しておらず、Runtime Logも収集していません。

[AL2023/nodeadmのLifecycle](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [NodeConfig API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## 公式リファレンス

- [EKSサポート対象Version](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS Node IAM Role](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [VPC CNI IAM Role](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [NetworkPolicyの前提条件](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS Access Entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Metrics Serverの要件](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [eksctl設定Schema](https://schema.eksctl.io/)
