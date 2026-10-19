# EKS クラスター作成クイズ - パート 1

> **最終更新日**: 2026年10月12日

> コマンドはそれぞれ独立した例であり、上から順に実行するスクリプトではありません。専用のトレーニング用アカウント／クラスター、レビュー済みの IAM 権限、非公開の一時 kubeconfig（`EXAMPLE_KUBECONFIG`）を使用してください。例示の ID と必須変数は置き換えてください。作成コマンドには料金が発生します。この監査では、ソース、構文、ローカルのフィクスチャを確認しましたが、AWS リソースのプロビジョニングやアプリケーションの可用性確認は行っていません。

このクイズでは、Amazon EKS クラスターの作成に関する概念、ツール、ベストプラクティスへの理解度を確認します。クラスターの作成方法、VPC の設定、ノードグループのセットアップなどを扱います。

## 基本概念に関する質問

1. EKS コントロールプレーンを直接プロビジョニングする組み込みコマンドがないツールはどれですか？
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>回答を表示</summary>

**回答: D) kubectl**

kubectl は Kubernetes API を通じてリソースを管理するもので、EKS をプロビジョニングするネイティブコマンドはありません。ACK など、すでにインストールされているインフラストラクチャコントローラーが、kubectl で送信されたリソースを EKS クラスターに反映することはありますが、これはコントローラーとの連携であり、kubectl に組み込まれた AWS 操作ではありません。

Amazon EKS クラスターの作成に使用できるツールには、次のものがあります。

1. **AWS Management Console**:
   * Web インターフェイスから EKS クラスターを作成できます。
   * クラスターコンポーネントを視覚的に設定できるため、初心者に適しています。
   * ステップごとのウィザードでクラスター作成手順を進められます。
2.  **AWS CLI**:

    * コマンドラインから EKS クラスターを作成できます。
    * `aws eks create-cluster` コマンドを使用します。
    * スクリプトや自動化に適しています。

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * EKS クラスターの作成専用に設計されたコマンドラインツールです。
    * 当初は Weaveworks が開発しました。現在は AWS／コミュニティの貢献を受け、eksctl-io 組織がプロジェクトを保守しています。
    * 1つのコマンドでクラスターを作成できます。

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code（IaC）ツール**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    これらのツールを使うと、EKS クラスターをコードとして定義し、デプロイできます。

kubectl は、クラスターの作成後に Kubernetes リソース（Pod、Service、Deployment など）を管理するために使用します。EKS クラスターに接続するには、一般的には `aws eks update-kubeconfig` を使って、認可済みの kubeconfig を設定します。

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

その後、kubectl でクラスターリソースを管理できます。

</details>

2. Amazon EKS クラスターの作成時に指定が必要な VPC コンポーネントはどれですか？
   * A) パブリックサブネットのみ
   * B) プライベートサブネットのみ
   * C) 少なくとも 2 つのアベイラビリティーゾーンにまたがるサブネット
   * D) NAT Gateway

<details>

<summary>回答を表示</summary>

**回答: C) 少なくとも 2 つのアベイラビリティーゾーンにまたがるサブネット**

**説明:** Amazon EKS クラスターの作成時に指定が必要な VPC コンポーネントは、少なくとも 2 つのアベイラビリティーゾーンにまたがるサブネットです。これは、EKS クラスターの高可用性を確保するための AWS の要件です。

**EKS クラスターの VPC 要件:**

1. **少なくとも 2 つのアベイラビリティーゾーン（AZ）にサブネットが必要**:
   * EKS コントロールプレーンは複数のアベイラビリティーゾーンにデプロイされるため、クラスター作成時に少なくとも 2 つのアベイラビリティーゾーンのサブネットを指定する必要があります。
   * これにより、リージョン内でコントロールプレーンの可用性を確保できます。ワークロードの可用性には、レプリカの配置、容量、ストレージ、依存関係の計画も必要です。
2. **サブネットの種類**:
   * パブリックサブネットのみ、プライベートサブネットのみ、またはパブリックサブネットとプライベートサブネットの混在を使用できます。
   * 本番環境では、セキュリティのためにワーカーノードをプライベートサブネットに配置し、ロードバランサーにはパブリックサブネットを使うことが推奨されます。
3. **サブネットの CIDR サイズ**:
   * クラスターの各サブネットには、EKS 用に少なくとも 6 個の空き IP アドレスが必要です。AWS は 16 個を推奨しています。ノード／Pod／ロードバランサーの容量は別途計画してください。
   * EKS は各 Pod に VPC の IP アドレスを割り当てるため、想定する Pod 数に応じて十分な大きさの CIDR ブロックが必要です。
4. **タグ要件**:
   * 以下のタグは、特定の連携機能における検出／所有権に関するものであり、EKS クラスター作成に常に必要な要件ではありません。
     * レガシーまたはコントローラー固有の所有権タグ: `kubernetes.io/cluster/<cluster-name>: shared`
     * パブリックサブネット: `kubernetes.io/role/elb: 1`
     * プライベートサブネット: `kubernetes.io/role/internal-elb: 1`

**VPC 設定例（eksctl を使用）:**

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

**AWS CLI を使用した VPC 設定:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

NAT gateway は、インターネットへの送信経路として利用できる選択肢の1つです。必要な VPC endpoint、ミラーイメージ、プライベート接続を用意すれば、インターネットアクセスなしでも運用できます。ノードをプライベートサブネットに配置することと、インターネットへの送信をなくすことは別々の判断です。例示の VPC、サブネット、クライアント CIDR は、レビュー済みの実際の値に置き換えてください。

</details>

3. EC2 ワーカーを使用する従来型の EKS コントロールプレーンを設定する場合、適切なロールの分離はどれですか？
   * A) クラスターロールのみが必要
   * B) EC2 ノードロールのみが必要
   * C) クラスターと EC2 ノードで別々のロールが必要
   * D) どちらも Fargate 実行ロールに置き換える

<details>
<summary>回答を表示</summary>

**回答: C) クラスターと EC2 ノードで別々のロールが必要**

クラスターロールは `eks.amazonaws.com` を信頼し、EKS がクラスターインフラストラクチャを管理できるようにします。従来型の EKS には `AmazonEKSClusterPolicy` または同等の権限が必要です。EC2 ノードロールは `ec2.amazonaws.com` を信頼し、インスタンスプロファイルを通じて指定します。EKS はマネージドノードグループ用のインスタンスプロファイルを設定します。ノードのブートストラップで IAM ロールが作成されることはありません。

EC2 の基本セットは `AmazonEKSWorkerNodePolicy` と `AmazonEC2ContainerRegistryPullOnly`、またはそれらと同等の最小権限です。CNI の権限も必要です。IRSA／Pod Identity 用の別ロールを使用することを推奨します。それを使用しない場合、ノードロールに CNI の権限が必要です。IPv4 用の `AmazonEKS_CNI_Policy` は IPv6 用ポリシーではありません。ストレージ、ロードバランサー、ロギングのコントローラー権限は、すべてのノードに常に必要なわけではありません。

この例では、従来型のクラスター／ノード用ロールを新規作成します。認可済みのアカウント／ロールを使い、エラーが出たら処理を止めてください。名前が競合しても、既存ロールにポリシーがアタッチされることはありません。

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

`CreateCluster` でコントロールプレーンのみを作成する場合、EC2 ノードロールはまだ必要ありません。EC2 コンピューティングを追加する際に設定してください。Fargate では、アプリケーションの AWS 権限とは別の Pod 実行ロールを使用します。Auto Mode には追加のクラスターポリシー／`sts:TagSession` と、最小限のノードロールポリシーが必要です。`iam:PassRole` など、プロビジョニングを行う ID に必要な権限は別途確認してください。

[ノードロールの要件](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Auto Mode のロール](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. eksctl を使って EKS クラスターを作成する正しいコマンドはどれですか？
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>回答を表示</summary>

**回答: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**説明:** eksctl を使って EKS クラスターを作成する正しいコマンドは、`eksctl create cluster --name my-cluster --region us-west-2` です。このコマンドは、指定した名前とリージョンで、デフォルト設定の EKS クラスターを作成します。

**eksctl コマンドの構造:**

* `eksctl`: 基本コマンド
* `create`: リソースを作成する操作
* `cluster`: 作成するリソースの種類（クラスター）
* `--name my-cluster`: クラスター名を指定
* `--region us-west-2`: AWS リージョンを指定

**基本的なクラスター作成コマンド:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

デフォルト値は eksctl のバージョンによって異なります。以下のファイルでは、EKS バージョン、AL2023、ノード数、endpoint を明示的に選択してください。作成によって VPC、ノード、IAM リソースがプロビジョニングされる可能性があります。認可されたテストアカウントで、設定と費用を確認してください。

**追加オプションを指定した高度なコマンド:**

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

**設定ファイルを使用したクラスター作成:**

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

**他の選択肢が誤りである理由:**

* `eksctl create-cluster`: コマンド形式が誤っています。eksctl ではコマンドの区切りにハイフン（-）ではなくスペースを使います。
* `eksctl new cluster`: `new` は有効な eksctl コマンドではありません。
* `eksctl start cluster`: `start` は有効な eksctl コマンドではありません。独自の動詞を作らず、文書化されたライフサイクルコマンドを使用してください。

eksctl には EKS クラスター管理用のさまざまなコマンドがあります。

* `eksctl create cluster`: 新しいクラスターを作成
* `eksctl get cluster`: クラスターを一覧表示
* `eksctl upgrade cluster`: クラスターを更新
* `eksctl delete cluster`: クラスターを削除
* `eksctl create nodegroup`: ノードグループを追加
* `eksctl scale nodegroup`: ノードグループをスケーリング

</details>

5. 新しい EKS クラスターで選択できる Kubernetes バージョンはどれですか？
   * A) 最新の upstream バージョンのみ
   * B) 常に最新バージョンとその2つ前までのバージョン
   * C) 対象リージョンで EKS の標準サポートまたは延長サポートが提供されているバージョン
   * D) すべての Kubernetes バージョン

<details>
<summary>回答を表示</summary>

**回答: C) 対象リージョンで EKS の標準サポートまたは延長サポートが提供されているバージョン**

EKS の各マイナーバージョンは、**EKS でのリリース日から14か月間の標準サポート**を受け、その後**有料の延長サポートを12か月間**受けます。2026年10月12日時点の公式一覧では、標準サポートは **1.34～1.37**、延長サポートは **1.31～1.33** です。EKS 1.37 は upstream での8月26日のリリース後、2026年10月1日に利用可能になりました。新規クラスターで利用できるバージョンは、対象リージョンに問い合わせてください。

延長サポートはデフォルトで有効です。アップグレードポリシーとサポート終了日によって、コントロールプレーンの自動アップグレードが実行されることがあります。ノード／アドオンの更新は別途計画してください。サポート期間の上限をアップグレード延期の理由にせず、AWS のサポート日程に関する告知に従ってください。

以下は、バージョンの確認、設定の生成、AWS での作成、既存クラスターのアップグレードという別々の例です。実行前に、認可された対象、ロール、サブネット、CIDR を準備してください。作成例とアップグレード例を1つのワークフローとして、そのまま連続実行しないでください。

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

コントロールプレーンを前方アップグレードする場合は、一度に1つのマイナーバージョンずつ進める必要があります。必要な機能、残りのサポート期間、アドオン／ワークロードとの互換性をあわせて確認してください。古いバージョンなら常に安全と決めつけず、対象バージョンをテストしてください。アドオンのメタデータからバージョン文字列を grep しても、クラスターのバージョンを確認したことにはなりません。

[EKS バージョンのライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. それ単独では EKS ワークロード向けのコンピューティングをプロビジョニングしない選択肢はどれですか？
   * A) マネージドノードグループ
   * B) セルフマネージドノードグループ
   * C) Fargate プロファイル
   * D) Kubernetes namespace

<details>

<summary>回答を表示</summary>

**回答: D) Kubernetes namespace**

namespace は Kubernetes リソースを整理するもので、コンピューティングを提供するものではありません。マネージド EC2 ノードグループ、セルフマネージド EC2 ノード、Fargate プロファイルはいずれも有効なコンピューティング手段です。EKS Auto Mode もマネージドノードをプロビジョニングし、Hybrid Nodes は顧客が管理するオンプレミス／エッジの容量を接続します。これらの仕組みがすべてマネージドノードグループ API を使うわけではありません。


以下の作成コマンドは、既存クラスターと未使用のグループ／プロファイル名を前提とする代替例です。必須変数はすべてレビュー済みの値に置き換えてください。CNI／ノード認可とプライベートサブネットの接続性を確認してください。Fargate には Pod 実行ロール、対応する Pod、プライベートサブネットが必要です。Fargate プロファイルはアプリケーションの Pod を作成しません。

**1. マネージドノードグループ:**

* **特徴**:
  * AWS がノードのプロビジョニングとライフサイクルを管理
  * EC2 インスタンスの作成と登録を自動化
  * ASG（Auto Scaling Group）の設定を自動化
  * Kubernetes ノードバージョンの更新はオペレーターが開始
  * EC2 のヘルスチェックによる置き換え。EKS のノード修復には、サポート対象のヘルスシグナル／設定が必要
  * マネージドワークフローを通じた AMI 更新はオペレーターが開始
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
  * カスタマイズの選択肢がより多い
  * カスタム AMI やブートストラップスクリプトを使用可能
  * 特定のインスタンスタイプや構成要件に適している
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

**3. Fargate プロファイル:**

* **特徴**:
  * サーバーレスのコンテナ実行環境
  * ノード管理が不要
  * Pod ごとのリソース割り当てと課金
  * 特定の namespace とラベルに基づいた選択的な実行
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

| 特徴 | マネージドノードグループ | セルフマネージドノード | Fargate |
| --- | --- | --- | --- |
| インフラストラクチャの管理 | AWS が置き換えのワークフローを管理。オペレーターが更新／スケーリングを設定 | オペレーターが AMI、ブートストラップ、ライフサイクルを管理 | AWS がホストを管理。ユーザーがアプリ、プロファイル、リクエストを管理 |
| コスト | インスタンス、利用率、コミットメント、運用を評価 | 運用とあわせて最適化を評価 | 割り当てられた Pod サイズ、実行時間、制約を比較 |
| スケーリング | 別途ノードオートスケーラー／ポリシーが必要 | 別途自動化が必要 | 対象 Pod 向けのコンピューティングを提供。アプリケーションのレプリカスケーリングは別途 |

Auto Mode の NodePools と Fargate プロファイルは、EC2 マネージドノードグループとは別のリソースです。Fargate でもワークロード、セキュリティ、可用性の管理は必要であり、常に安価または高価というわけではありません。

</details>

7. 新しい EKS 1.36 ノード向けに、AWS が公開する EKS 最適化 AMI ファミリーではないものはどれですか？
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>回答を表示</summary>

**回答: D) Ubuntu Core**

Ubuntu Core を AWS 公開の EKS 最適化 AMI として扱わないでください。Canonical Ubuntu Server イメージや顧客が作成した AMI は、公開元、互換性、サポート経路がそれぞれ異なります。Ubuntu Core と同じ製品ではありません。

**この例での選択肢**

- **AL2023**: EKS 最適化 AMI と `nodeadm` ブートストラップを使用します。Kubernetes マイナーバージョン、CPU アーキテクチャ、リージョン、CNI との互換性を確認してください。
- **Bottlerocket**: コンテナ向け OS であり、汎用 Linux ノードとは設定および更新の仕組みが異なります。
- **Windows**: サポートされる Windows Server のホスト／コンテナバージョンを一致させ、Windows ネットワーク、認証、システムワークロードの前提条件を準備します。これは Auto Mode／Fargate 向けの Windows 例ではありません。

**AL2 は、レガシー環境からの移行元です。** EKS 最適化 AL2 AMI の公開／サポートは2025年11月26日に終了し、AL2 OS のサポートは2026年6月30日に終了しました。EKS の Kubernetes 延長サポートによって AL2 のサポートが延長されることはありません。新規の EKS 1.36 デプロイに AL2 を推奨しないでください。

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

マネージドノードグループの起動テンプレートでは、カスタム AMI も使用できます。AMI を固定する場合は、OS／ランタイム、クラスターのメタデータ、ブートストラップ設定を確認してください。任意の Ubuntu イメージに `docker.io` だけをインストールしても、動作する EKS ノードにはなりません。対象の EKS バージョンに対応する Canonical イメージと、レビュー済みの eksctl／起動テンプレート設定を使用してください。高度な質問では、起動テンプレートの `ImageId`、ノードグループの `amiType`、ユーザーデータのマージに関する制約を区別します。

イメージを選ぶ際は、セキュリティ更新、測定したワークロードのパフォーマンス、Kubernetes／ドライバーとの互換性、運用、GPU などの特殊要件を確認してください。

[AL2 の移行](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Windows の前提条件](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. CreateCluster API で endpoint アクセスを省略した場合のデフォルトは何ですか？
   * A) パブリックが有効、プライベートが無効
   * B) プライベートのみ
   * C) 両方の endpoint が有効
   * D) 作成後にアクセス設定を変更できない

<details>
<summary>回答を表示</summary>

**回答: A) パブリックが有効、プライベートが無効**

API のデフォルトでは、パブリックアクセスが有効、プライベートアクセスが無効です。eksctl、CDK、コンソールの作成手順では、別の設定を明示的に選択できます。これはすべてのツールに共通するデフォルトではありません。作成後もアクセス設定を変更できます。

| パブリック | プライベート | アクセス経路 |
| --- | --- | --- |
| 有効 | 無効 | パブリック endpoint と publicAccessCidrs を使用。ノード／CI の実際の送信元 IP アドレスも考慮 |
| 有効 | 有効 | VPC 内のリクエストにはプライベート経路を使用。外部からは許可されたパブリック CIDR を使用 |
| 無効 | 有効 | VPC または接続済みネットワークからのプライベート経路 |
| 無効 | 無効 | 無効な設定 |

**クラスターセキュリティグループは、プライベート endpoint と kubelet のトラフィックを制御し、パブリック endpoint のアクセスは制御しません。** `publicAccessCidrs` が適用されるのはパブリック endpoint のみです。ネットワーク到達性とは別に、認証／認可も必要です。IPv4 の例示 CIDR は、実際に許可されたクライアントの送信元 CIDR に置き換えてください。

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

パブリックアクセスを無効にする前に、前回の更新が `Successful` であり、管理／CI ネットワークからプライベート DNS、ルーティング、API アクセスを利用できることを確認してください。重複する非同期更新をすぐに送信せず、1回のリクエストで両方のアクセスフラグを設定してください。

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

プライベート API アクセスとインターネットへの送信をなくすことは、別々の設計判断です。ID、ネットワーク、運用の各コントロールをあわせて評価してください。プライベートアクセスだけでセキュリティや可用性が保証されるわけではありません。VPN／Direct Connect／管理ホストと接続コストも考慮してください。IPv6 endpoint と Hybrid Nodes には、公式ガイダンスで説明されている追加の DNS／CIDR 上の考慮事項があります。

[クラスター endpoint のアクセス制御](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. Amazon EKS クラスターのノードグループ向けインスタンスタイプを選ぶ際、考慮事項ではないものはどれですか？
   * A) ワークロードの要件（CPU、メモリ、ストレージ）
   * B) コスト最適化
   * C) ローカル kubeconfig のコンテキストエイリアス
   * D) インスタンス世代（例: t3 と t2）

<details>

<summary>回答を表示</summary>

**回答: C) ローカル kubeconfig のコンテキストエイリアス**

kubeconfig のエイリアスはローカルクライアント上の名前であり、インスタンスのパフォーマンス、価格、可用性を変えません。一方、必要な AZ でそのタイプが提供されているか、実際に容量があるか、アカウントクォータが足りているかは重要な選択上の制約です。

**ノードグループのインスタンスタイプを選ぶ際の実際の考慮事項:**

1. **ワークロードの要件（CPU、メモリ、ストレージ）**:
   * アプリケーションのリソース要件に合ったインスタンスタイプを選択する
   * メモリ負荷の高いワークロード: r5、r6g などのメモリ最適化インスタンス
   * 計算負荷の高いワークロード: c5、c6g などのコンピューティング最適化インスタンス
   * バランス型のワークロード: m5、m6g などの汎用インスタンス
   * GPU ワークロード: p3、g4dn などの高速コンピューティングインスタンス
2. **コスト最適化**:
   * オンデマンドインスタンスと Spot インスタンスの比較
   * Reserved Instances または Savings Plans
   * 適切なインスタンスサイズの選択（過剰なプロビジョニングを避ける）
   * ARM ベースの Graviton インスタンス（例: m6g、c6g）によるコスト削減
3. **インスタンス世代**:
   * 実際のワークロードについて、世代ごとの価格／パフォーマンスを比較する
   * バースト可能なファミリーでは、CPU クレジットの動作とベースライン性能を考慮する
   * 最新世代では、ネットワークやストレージの性能などが向上している
4. **ネットワーク要件**:
   * 拡張ネットワークのサポート（ENA、EFA など）
   * ネットワーク帯域幅の要件
   * インスタンスあたりの最大 Pod 数に関するネットワーク上限
5. **ストレージ要件**:
   * ローカルインスタンスストレージが必要か（例: i3、d3 インスタンス）
   * EBS 最適化のサポート
   * ストレージのスループットと IOPS の要件
6. **CPU アーキテクチャ**:
   * x86（Intel、AMD）と ARM（AWS Graviton）の比較
   * アプリケーションの互換性に関する考慮事項

**アベイラビリティーゾーンとノードグループのデプロイ:**

必要な AZ 範囲によって、利用可能なインスタンスタイプが制限されます。カタログに掲載されていても、即時に容量が確保できるとは限りません。

* 高可用性のため、複数のアベイラビリティーゾーンにノードグループをデプロイする
* ノード容量と Pod のトポロジー分散を計画し、実際の配置を確認する
* リージョン内のすべてのアベイラビリティーゾーン、または特定のアベイラビリティーゾーンを選択できる

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

1. **Web アプリケーションサーバー**:
   * 汎用インスタンス: t3.medium、m5.large
   * バランスの取れた性能でコスト効率が良い
2. **データベース**:
   * メモリ最適化インスタンス: r5.xlarge、r6g.xlarge
   * CPU に対するメモリの比率が高い
3. **バッチ処理ジョブ**:
   * コンピューティング最適化インスタンス: c5.xlarge、c6g.xlarge
   * 高い CPU 性能
4. **機械学習ワークロード**:
   * GPU インスタンス: p3.2xlarge、g4dn.xlarge
   * 高速コンピューティング機能

上記のファミリーは例示であり、現行の製品カタログや測定済みのパフォーマンス順位を示すものではありません。ワークロード、価格、アーキテクチャ、ドライバー、必要な AZ での提供状況／容量をあわせて確認してください。

</details>

10. Amazon EKS クラスターの作成後に kubectl を設定する正しいコマンドはどれですか？
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>回答を表示</summary>

**回答: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**説明:** Amazon EKS クラスターの作成後に kubectl を設定する正しいコマンドは、`aws eks update-kubeconfig --name my-cluster --region us-west-2` です。このコマンドは AWS CLI の EKS モジュールを使って、指定したクラスターの kubeconfig ファイルを更新します。

**kubectl の設定手順:**

1. **kubeconfig ファイルの更新**:
   * kubeconfig ファイルには、kubectl が Kubernetes クラスターと通信するために必要な設定情報が保存されます。
   * 選択の優先順位は、明示的に指定した `--kubeconfig`、`KUBECONFIG` の最初のパス、`~/.kube/config` の順です。
   * このコマンドは選択されたファイルのクラスター／exec 認証設定をマージし、現在のコンテキストを変更します。クラスター権限を付与するものではありません。
2. **コマンドの各要素**:
   * `--name`: EKS クラスター名
   * `--region`: クラスターが配置されている AWS リージョン
   * `--kubeconfig`（任意）: kubeconfig ファイルのカスタムパス
   * `--role-arn`（任意）: クラスターアクセスに使用する IAM ロール
3.  **コマンド全体の例**:

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

**他の選択肢が誤りである理由:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: このコマンドは存在しません。AWS CLI に `get-kubeconfig` サブコマンドはありません。
* `kubectl config set-cluster my-cluster --region us-west-2`: コマンドの構文が誤っています。`kubectl config set-cluster` は `--region` フラグに対応しておらず、EKS クラスターに必要な認証情報を自動設定しません。
* `eksctl configure kubectl --name my-cluster --region us-west-2`: このコマンドは存在しません。eksctl に `configure kubectl` サブコマンドはありません。eksctl でクラスターを作成すると kubeconfig は自動設定されますが、既存クラスターには `aws eks update-kubeconfig` または `eksctl utils write-kubeconfig` を使用してください。

**eksctl で既存クラスターの設定を書き込む:**

既存クラスターの場合、別のクラスターを作成せずに、その設定を書き込みます。

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

既存クラスターの kubeconfig が書き込まれます。IAM 認証と access entry／RBAC 認可は別途確認してください。無効にしていない限り、クラスター作成時にもデフォルトで kubeconfig が書き込まれます。

**複数クラスターの管理:**

複数の EKS クラスターを管理する場合は、クラスターごとに `aws eks update-kubeconfig` コマンドを実行して kubeconfig ファイルに追加できます。

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Switch context
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

したがって、Amazon EKS クラスターの作成後に kubectl を設定する正しいコマンドは、`aws eks update-kubeconfig --name my-cluster --region us-west-2` です。

</details>

## 実践演習

### 演習 1: eksctl を使用して EKS クラスターを作成する

**シナリオ:** 開発チーム向けに、従来型の EC2 マネージドノードグループクラスターを準備します。これはトレーニング用の設計であり、本番環境での準備完了をテストした証拠でも、測定済みのコスト結果でもありません。

**要件:** 2つの AZ を使用し、AL2023 の `t3.medium` ノードを初期状態で2台、スケーリング範囲を2～5台、ノードネットワークをプライベートに設定し、承認済みのパブリック CIDR を指定して両方の API endpoint を有効にします。上限／下限を設定しただけではオートスケーラーはインストールされません。`t3.medium` を選ぶ前に、バースト可能インスタンスの CPU クレジット、メモリ、IP 容量、クォータ、実際のワークロード要件を確認してください。

<details>
<summary>回答を表示</summary>

**1. ツールと ID を準備する。** [パート 1](../../eks/02-eks-cluster-creation-part1.md) に記載された、チェックサムで検証されたアーキテクチャ別のインストール手順を使用してください。この例は EKS 1.36 と eksctl 0.230.0 に照らしてレビューされています。実行前に、リージョンで利用できる EKS バージョンと、互換性のあるクライアント／アドオンのバージョンを確認してください。`kubectl` はバージョンのスキュー制限を満たす必要があります。ログインから引き受けられる既存の承認済みオペレーター IAM ロールを使ってください。プロビジョニング権限と Kubernetes アクセス権は別です。

**2. 非公開のローカル設定を生成してレビューする。** 生成する名前は、新しいトレーニング用クラスター向けです。パブリック CIDR には、実際に許可された送信元範囲を指定してください。2つの AZ は `us-west-2` の例であり、提供状況と容量を確認する必要があります。

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

これにより、指定したオペレーターにこのラボの cluster-admin アクセス権を付与し、クラスター作成者への管理者権限の自動付与を無効にします。オペレーターのロールを作成したり、呼び出し元にそのロールを引き受ける権限を付与したりすることはありません。eksctl は必要なクラスター／ノードロールを作成するため、生成されるポリシーの範囲を確認してください。従来型の基本設定では、VPC CNI 権限をノードロールに設定できます。ワークロードをより強く分離するには、公式の CNI IAM ガイダンスに従い、`aws-node` 用の専用ロールを設定してください。後でアドオンを使う可能性があるというだけの理由で、すべてのノードに広範なイメージ push、DNS、ストレージ、ロードバランサー、ロギングの権限を付与しないでください。

**3. 設定とコストを確認してからプロビジョニングする。** 新しい VPC のデフォルトトポロジーでは、NAT など課金対象のインフラストラクチャが作成されることがあります。`eksctl` は CloudFormation を使用して、VPC／サブネット／セキュリティグループ／ロール／クラスター／ノードグループのリソースを作成します。失敗時に一部のリソースが残る場合があるため、自動的に完全削除されると思い込まず、スタックイベントを確認してください。

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

**4. 実際のステータス、アクセス、スケーリング範囲を確認する。** クラスター／ノードグループが `ACTIVE`、ノードが `Ready` になるまで待ち、異常なシステム Pod と想定される AZ への配置を調べてください。作成リクエストの成功や RBAC の一覧表示だけで、安全に動作するクラスターであることが証明されるわけではありません。

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

**5. 必要なコンポーネントだけを追加する。** Cluster Autoscaler には、高度な質問2で説明する、適切な範囲の IAM／service account／検出設定が必要です。上限／下限を設定しても、それだけでワークロード需要に応じて動くわけではありません。`kubectl top` の実行には、Metrics Server がインストールされ、正常に動作している必要があります。監査した Metrics Server 0.9.0 の基本構成では Kubernetes 1.34 以降がサポートされています。実際にインストールされているバージョンを確認してください。コスト削減や適正なサイズ設定を主張する前に、代表的な使用状況を測定してください。

**6. トレーニング用クラスターをクリーンアップする。** まず、ラボで作成した LoadBalancer Service／Ingress があれば削除し、コントローラーが AWS リソースを解放するのを待ちます。PVC の reclaim policy と保持されたボリュームを確認してください。この演習自体では、そのようなアプリケーションリソースは作成しません。その後、記録したクラスターだけを削除します。

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

その後、CloudFormation と AWS リソースの一覧を確認し、削除に失敗したもの、保持されたボリューム、独立して作成されたロール／endpoint がないか調べてください。クリーンアップの完了が確認されるまで設定／ARN の記録を保管し、不要になったら一時 kubeconfig ディレクトリをローカルから削除してください。

</details>

### 演習 2: AWS Management Console を使用して EKS クラスターを作成する

**シナリオ:** 後の本番デプロイに役立つ可能性のある、従来型のマネージドノードグループ設計をレビューします。ワークロードのサイズ、ルーティング、IAM、可用性、アップグレード、復旧は、引き続きテストが必要な環境固有の前提事項です。このウォークスルーは、監査中にプロビジョニングも負荷テストも行っていません。

<details>
<summary>回答を表示</summary>

**1. 別々の IAM ロールを準備する。**

- クラスターロール: `eks.amazonaws.com` を信頼し、`AmazonEKSClusterPolicy` をアタッチします。
- EC2 ノードロール: `ec2.amazonaws.com` を信頼し、`AmazonEKSWorkerNodePolicy` と `AmazonEC2ContainerRegistryPullOnly` をアタッチします。対応している場合は、VPC CNI に専用の IRSA／Pod Identity ロールを付与してください。より単純な IPv4 のノードロールへのフォールバックを意図的に使用する場合は、`AmazonEKS_CNI_Policy` を明示的にアタッチし、権限を共有するトレードオフを記録します。
- プロビジョニング／オペレーター ID: 承認済みのリソース範囲を指定した IAM 権限と、これらのロールに対する `iam:PassRole` を使用します。ラボで必要なアクセス権ポリシーを使って、既存のオペレーターロールの EKS access entry を追加します。kubeconfig を作成しただけでは Kubernetes の認可は付与されません。

**2. VPC とサブネットを確認する。** 次の公式サンプルは、引き続き参照例として利用できます。URL 内の日付は EKS バージョンではありません。

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

一意な名前を付けたトレーニング用スタックを作成する前に、CloudFormation テンプレートを確認してください。デフォルトでは、**2つの AZ にまたがる2つのパブリックサブネットと2つのプライベートサブネット、インターネット gateway、2つの NAT gateway／EIP** を持つ VPC が作成されます。したがって、これは送信インターネットアクセスのある NAT 経由の設計であり、送信経路のないプライベートクラスターではありません。本番環境でデフォルトをそのまま使わず、CIDR の重複、AZ、IP 容量、NAT 料金を確認してください。

`VpcId`、`SubnetIds`、`SecurityGroups` を記録します。`SubnetIds` には**パブリックサブネットとプライベートサブネットの両方**が含まれます。各ルートテーブルを調べ、ノード用の実際のプライベートサブネットを選んでください。出力されるカスタムセキュリティグループがあるからといって、必要な通信ルールがすべて存在するとは限りません。EKS クラスターセキュリティグループ、追加のセキュリティグループ、コントロールプレーン／ノード間の通信ルールを確認してください。

**3. 従来型のクラスターを作成する。** EKS コンソールでカスタム設定の手順を選び、この演習では Auto Mode を無効にします。EKS 標準サポート対象の、利用可能で互換性のあるバージョン（監査での例は 1.36）、クラスターサービスロール、レビュー済みの VPC／サブネットを選択してください。

- API access-entry 認証を選び、指定したオペレーターに適切なアクセス権を付与します。説明されていない作成者管理者権限のデフォルトに依存しないでください。
- API アクセスをプライベートのみにする場合は、管理ネットワークのプライベートルーティング／DNS を先に確認します。別の方法として、パブリックとプライベートの両方のアクセスを有効にし、`publicAccessCidrs` を許可された管理用の送信元範囲に制限します。
- この従来型 EC2 クラスターでは、互換性のある VPC CNI、kube-proxy、CoreDNS アドオンを維持し、各設定／権限を確認してください。必要なコントロールプレーンログを有効にし、ログ料金も考慮します。
- 確認してクラスターを作成し、`ACTIVE` になるまで待ちます。作成時間は変動するため、所要時間の目安だけでは完了確認になりません。

**4. マネージドノードグループを追加する。** EC2 ノードロール、AL2023 x86_64 AMI、例示用の `m5.large` などのサポート対象インスタンスタイプを選択します。この例では、ルートディスク 50 GiB、希望サイズ 3、最小サイズ 2、最大サイズ 5 と、レビュー済みのプライベートサブネットを使用します。これらはサイズ設定の例であり、本番環境向けの推奨値ではありません。必要に応じてアクセス、IMDS、ストレージ暗号化を設定し、ノードグループが `ACTIVE`、ノードが `Ready` になるまで待ってください。

**5. アクセスを確認し、実際の AWS セキュリティグループを調べる。** コンソールで記録したクラスター名と、承認済みのオペレーターロールを使用します。

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

**6. 任意の NetworkPolicy 演習。** まず、選択した CNI とその設定が NetworkPolicy を適用することを確認します。AWS VPC CNI のポリシーサポートは、ノード／OS 設定で有効化され、サポートされている必要があります。次の ingress のみを拒否する default-deny 設定は、新規作成した空のラボ namespace に限定されます。egress は拒否しません。また、`apply` が成功しただけでポリシーが適用されていると証明されるわけではありません。

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

専用のテスト Pod を使って許可／拒否されるトラフィックをテストし、このパターンを実際のワークロードに使う前に、アプリケーションに必要な許可ポリシーを追加してください。この設定を既存の共有 `default` namespace に適用しないでください。完了したら、分離した namespace を削除します。

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

**7. コンソールでのクリーンアップ:** ラボのワークロードを削除して、関連するクラウドリソースが解放されるまで待ちます。その後、このラボのマネージドノードグループを削除し、削除完了を待ってからラボのクラスターを削除します。ラボの VPC CloudFormation スタックは、EKS リソースと外部依存関係がなくなってから削除してください。このラボ専用に作成した IAM ロール／endpoint だけを削除し、共有リソースは保持して、削除に失敗したリソースや保持されたリソースを調べてください。このレビューでは、これらの操作を実行していません。

</details>

## 高度なトピック

以下は、Amazon EKS クラスターの作成に関連する高度なトピックについての質問です。このセクションでは、EKS クラスター作成に関する高度な概念とベストプラクティスへの理解度を確認します。

1. EKS EC2 マネージドノードグループでカスタム起動テンプレートを使う主な利点はどれですか？
   * A) クラスターの作成時間が必ず短くなる
   * B) カスタムのノードユーザーデータとボリューム設定
   * C) コントロールプレーンのプラグインをインストールできる
   * D) 新たに公開される AMI ごとに、既存のすべてのノードが自動更新される

<details>
<summary>回答を表示</summary>

**回答: B) カスタムのノードユーザーデータとボリューム設定**

起動テンプレートを使うと、**EC2 マネージドノードグループ**のストレージ、インスタンスメタデータ、OS 固有のユーザーデータなどをカスタマイズできます。EKS コントロールプレーンや EKS Auto Mode のノードは設定できません。

**AL2023 のユーザーデータ:** MIME multipart データを使用します。EKS が選択した AMI を使用する場合（テンプレートに `ImageId` がない場合）、EKS がノード設定を提供／マージします。カスタム AMI ID を使用する場合は、高度な質問5で説明する完全な `NodeConfig` を指定してください。AL2023 の systemd サービスが `nodeadm` を実行します。`/etc/eks/bootstrap.sh` を呼び出したり、再度 `nodeadm init` を実行したり、kubelet を手動で起動したりしないでください。追加ソフトウェアは、選択した OS に対応し、到達可能で信頼できるパッケージソースを利用できる必要があります。

以下は、EKS が選択した AL2023 AMI を使う場合の最小限のカスタマイズ例です。アプリケーション用ディレクトリを作成するだけです。

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

**ストレージ:** 次は、有効な `LaunchTemplateData` フラグメントの1つです。AMI のルートデバイス名を確認してください。ボリュームをアタッチしただけでは、フォーマットもマウントもされません。どちらの例のボリュームも暗号化され、インスタンスとともに削除されます。ノードの置き換え後も存続させる必要があるアプリケーションデータには、適切な reclaim／バックアップポリシーを設定した CSI 管理の PV を使用してください。

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

**ネットワークとメタデータ:** 必要なコントロールプレーン、ノード、DNS、ワークロードのトラフィックを許可するルールを持つセキュリティグループに、例示のセキュリティグループを置き換えてください。カスタムセキュリティグループを指定した場合、EKS はクラスターセキュリティグループを**自動的に追加しません**。セキュリティグループは、インスタンスレベルかネットワークインターフェイスレベルのどちらか一方で指定し、両方には指定しないでください。

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

ホップ制限 1 は、Pod がノードの認証情報ではなく IRSA または EKS Pod Identity を使うことを前提とします。コンテナから IMDSv2 にアクセスする必要があるワークロードでは、ホップ制限を 2 にする必要がある場合があります。この設定も IMDSv2 も、`hostNetwork` Pod を分離するものではありません。複数のインターフェイス、配置、インスタンスストアデバイスを利用するには、互換性のあるインスタンスタイプを選び、EKS の起動テンプレート制限を満たす必要があります。これらはすべての環境で互換的に使える選択肢ではありません。

**ノードグループの作成:** 実際の ID、権限、ネットワークルートを確認した後、eksctl の設定または AWS CLI の例のどちらかを選んでください。これは代替手順であり、連続して実行する手順ではありません。

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

起動テンプレートには `SubnetId` と `IamInstanceProfile` を含めないでください。サブネットとノード IAM ロールは、ノードグループのリクエストで指定します。起動テンプレートを使用する場合、ノードグループの `diskSize` や `remoteAccess` も設定しないでください。インスタンスタイプは、テンプレートまたはノードグループのリクエストのどちらか一方に設定します。`ImageId` を指定する場合は、ノードグループの `amiType`、`releaseVersion`、`version` を省略し、カスタム AMI の kubelet／コントロールプレーンとの互換性を確認してください。

明示的な `ImageId` を指定すると AMI が固定されます。指定しないテンプレートでは、EKS が選択した AMI を使用できます。どちらの場合も、AMI が公開されるたびに既存ノードが自動更新されるわけではありません。カスタムテンプレートを更新するには、同じテンプレートの新しいバージョンを作成し、ノードグループの明示的な更新を行う必要があります。これにより、インスタンスが置き換えられます。

参照: [起動テンプレートの制約](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[CreateNodegroup のフィールド](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[AL2023 の初期化](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)。

</details>

2. EKS のコスト最適化策として、それ単独では不十分なものはどれですか？
   * A) 中断に耐えられるワークロードに Spot を使用する
   * B) Cluster Autoscaler を設定して認可する
   * C) 測定せず、すべてのワークロードに最新世代のインスタンスを選ぶ
   * D) ワークロードのニーズと総コストを比較し、Fargate を選択的に評価する

<details>
<summary>回答を表示</summary>

**回答: C) 測定せず、すべてのワークロードに最新世代のインスタンスを選ぶ**

すべてのノードを最新世代だからという理由だけで選んでも、十分なコスト分析にはなりません。ワークロードのアーキテクチャ、スループット、レイテンシー、メモリ、リージョンでの提供状況、中断への耐性を比較してください。新しい世代のほうが経済的な場合はありますが、同じ有用な処理に対して常に新しい世代または古い世代のほうが安価とは限りません。

1. **Spot と分散:** AWS が公表する Spot の割引率はオンデマンドと比べて最大 90% です。これは価格上の割引の可能性を示すものであり、このラボで測定または保証された節約額ではありません。中断と代替容量を考慮してください。Cluster Autoscaler では、スケジューリングのシミュレーションが最初のタイプを使うため、1つのノードグループ内で混在させるインスタンスタイプの CPU／メモリ／GPU の形状を揃える必要があります。ローカルディスクへの依存は別途確認してください。

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

2. **Cluster Autoscaler:** 最小／最大サイズは、スケーリング範囲を設定するだけです。スケジュールできない Pod と削除可能な容量に応じて希望容量を変更するコントローラーを、インストールして認可してください。すべてのノードに広範なオートスケーリング権限を付与しないでください。この**新規インストール**の前に、専用 IRSA ロール（OIDC の信頼関係をその service account に限定）またはサポート対象の Pod Identity 構成を用意し、`kube-system/cluster-autoscaler` service account を準備します。スケーリングの書き込み権限を、対象クラスターの Auto Scaling group のみに限定し、該当 group に `k8s.io/cluster-autoscaler/enabled=true` と `k8s.io/cluster-autoscaler/<cluster-name>=owned` のタグを設定してください。ノードグループのリソースタグだけでは、ASG の検出が設定済みであることは確認できません。

コントローラーのマイナーバージョンはクラスターと一致させる必要があります。Chart 9.59.0 のコントローラーのデフォルトは 1.35.0 なので、この EKS 1.36 の例では 1.36.1 を明示的に選択しています。別のクラスターのバージョンには、それに一致するコントローラーバージョンが必要です。同じ group を管理する既存の CA インストールがないことを確認してください。

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

3. **Fargate と適正なサイズ設定:** Fargate はホスト管理の作業を減らしますが、測定した CPU 使用量だけではなく、割り当てたリソースと実行時間に対して課金されます。プロファイルをサポート対象の Pod とプライベートサブネットのネットワークに合わせ、EC2 と総コストを比較してください。`kubectl top` の実行には Metrics Server が必要であり、短時間のサンプルは容量計画にはなりません。
4. **Graviton:** ARM ノードグループを作成する前に、ARM64 イメージと依存関係をテストしてください。世代別の「価格／パフォーマンスが最大40%向上」という主張は、請求額が一律40%下がることを示すものでも、同等のパフォーマンスを保証するものでもありません。

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

5. **コミットメント:** Reserved Instances と Savings Plans を利用すると、条件を満たす予測可能な使用量のコストを削減できます。最大72%という公表値は、製品、期間、支払い方法、使用量によって異なります。未使用のコミットメントによって、節約効果がなくなることもあります。
6. **requests と limits:** 値を選ぶ前に、代表的なワークロードを測定してください。requests はスケジューリングとオートスケーラーの判断に影響します。limits が小さすぎると、CPU のスロットリングや OOM による終了が起きることがあります。次はコンテナあたりの値の例です。

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

7. **コスト配賦:** Cost Explorer と、設定済みの配賦レポート／ツールを使用してください。Kubernetes のラベルは、自動的に有効化された AWS のコスト配賦タグにはなりません。コントロールプレーン、該当する場合は Auto Mode の料金、ストレージ、ロードバランサー、NAT、転送、ログのコストを含めてください。

参照: [EKS 上の CA](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)、[CA Chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler)、[CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1)、[Spot の料金](https://aws.amazon.com/ec2/spot/)、[Fargate の料金](https://aws.amazon.com/fargate/pricing/)、[Graviton](https://aws.amazon.com/ec2/graviton/)、[Savings Plans](https://aws.amazon.com/savingsplans/)。

</details>

3. Kubernetes API へのプライベート限定アクセスと、ノード／Pod からのインターネットへの送信なしの両方を満たす設計はどれですか？
   * A) プライベート API、インターネットへの送信経路のないプライベートノードサブネット、必要なサービス endpoint、プライベートな管理経路
   * B) ノードをプライベートにするだけで、API と送信の設定はすべて変更しない
   * C) パブリックとプライベートの Kubernetes API endpoint を両方とも無効にする
   * D) パブリック API を無効にし、制限のない NAT 経由の送信を維持する

<details>
<summary>回答を表示</summary>

**回答: A) プライベート API、インターネットへの送信経路のないプライベートノードサブネット、必要なサービス endpoint、プライベートな管理経路**

次の2つの判断を分けてください。**誰が Kubernetes API に到達できるか**と、**ノード／Pod がどこへトラフィックを送信できるか**です。API をプライベートのみにしても、NAT ルートが削除されたり、ワークロードの送信がブロックされたり、すべてのパケットが1つの VPC 内にとどまったりするわけではありません。ルーティング、DNS、セキュリティグループ、認可が許可されていれば、接続済みネットワークからプライベート API に到達できます。

この質問の要件は、API へのプライベート限定アクセスと、ノード／Pod からのインターネットへの送信なしの両方です。プライベート endpoint を有効にし、パブリック endpoint を無効にして、インターネットへの送信経路のないプライベートノードサブネットを使い、ワークロードが必要とするサービス endpoint、レジストリイメージ、管理経路を用意します。

**endpoint の切り替え:** まずプライベートアクセスを有効にし、その更新の成功を待ってから、対象のプライベートネットワークから認証済み `kubectl` アクセスをテストしてください。その後に限り、以下の別手順でプライベート限定にします。返された更新を確認し、`Successful` になってからアクセスを再確認してください。パブリック endpoint は `publicAccessCidrs` で制限され、クラスターセキュリティグループでは制限されません。後者が制御するのはプライベート endpoint のトラフィックです。

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

**ノードの配置:** このフラグメントは既存の VPC とプライベートサブネットを使用します。ID を置き換え、使用前にルートを確認してください。VPC endpoint を作成したり、既存の NAT ルートを削除したりはしません。インターネットのみで接続している別のワークステーションから eksctl を実行しても、プライベート限定の Kubernetes API にはアクセスできません。

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

**AWS サービスへの接続:** 以下の ECR と S3 の例は、設計の一部にすぎません。重複したプライベート DNS の競合を避けるため、既存の endpoint を先に確認してください。Interface endpoint には、プライベート DNS と、対象クライアントからの HTTPS ingress が必要です。S3 gateway endpoint には、プライベートのルートテーブルと適切な endpoint／bucket policy が必要です。

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

| 依存関係 | インターネット経路がない場合のプライベート接続 |
| --- | --- |
| プライベート ECR イメージの pull | `ecr.api`、`ecr.dkr`、S3 gateway。パブリックイメージは、到達可能なプライベートレジストリにコピー |
| ノード／CNI が使用する EC2 API | `ec2`、適切な権限と endpoint policy |
| IRSA の認証情報 | リージョンの `sts`。SDK がリージョン endpoint を使用するよう設定 |
| VPC 内からの OIDC ディスカバリー／JWKS | IAM OIDC provider の設定時などに使用する `oidc-eks`。STS とは別 |
| EKS Pod Identity の認証情報 | `eks-auth` と、サポート対象の Pod Identity Agent／設定 |
| EKS 管理 API | `eks`。Kubernetes API のプライベート endpoint の代わりにはならない |
| Logs、autoscaling、load balancing、SSM | 実際に使用するサービスの endpoint と権限。SSM には messaging 接続も必要 |

endpoint サービスと DNS 名はリージョン／パーティションによって異なります。イメージレジストリ、パッケージのダウンロード、外部 API、アドオン機能など、各ワークロードの依存関係をすべて確認してください。1つの AWS サービスの endpoint が、汎用のインターネット代替になるわけではありません。

**管理:** ルーティングされた VPN／Direct Connect、プライベートアクセスが可能な管理用ホスト、または適切に設定された SSM セッションを使用します。bastion に必ずパブリック IP が必要なわけではありません。SSM にも、Agent、IAM 認可、サービスへの接続性が必要です。

NAT 経由のプライベートノードとプライベート API の組み合わせも有効な EKS 設計ですが、この質問のインターネット送信なしという要件は満たしません。同様に、サブネットにパブリックルートがあるだけでは、個々のノードがインターネットから到達可能とは限りません。アドレスの割り当てとセキュリティ制御も重要です。

参照: [プライベートクラスターの要件](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[API endpoint アクセス](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[EKS PrivateLink と OIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)。

</details>

4. 新しいノード AMI を適用する EKS マネージドノードグループの仕組みではないものはどれですか？
   * A) マネージドローリング更新でインスタンスを置き換える
   * B) 別の blue/green ノードグループを作成して検証する
   * C) インスタンスを置き換えず、稼働中のインスタンスで OS パッケージをアップグレードする
   * D) より広範な置き換えの前に、小規模なカナリーノードグループで新しい AMI を検証する

<details>
<summary>回答を表示</summary>

**回答: C) インスタンスを置き換えず、稼働中のインスタンスで OS パッケージをアップグレードする**

EKS マネージドノードグループの更新では、EC2 インスタンスを置き換えます。稼働中のインスタンスで OS パッケージをアップグレードすることは、マネージド AMI 更新の仕組みではありません。「インプレースアップグレードはすべてサポートされない」と曖昧に主張しないでください。AWS は、起動テンプレートの AMI バージョンを変更しながらノードグループリソースを維持することにも、この用語を使いますが、その場合もインスタンスは置き換えられます。

**ローリング更新:** `DEFAULT` では、古いノードを終了する前に置き換え用の容量が作られます。`MINIMAL` では、置き換えを作成する前に、選択された古いノードを終了する場合があります。`maxUnavailable` のデフォルトは 1 ですが、設定可能なので、常にちょうど1台ずつ更新されるわけではありません。クォータ、AZ 容量、Pod 配置、更新戦略を確認してください。カスタム AMI の場合は、同じ起動テンプレートの新しいバージョンを明示的に選択してください。以下のコマンドは、EKS が選択した AMI の場合の例です。

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

返された更新 ID を記録し、更新が終端状態になるまで `describe-update` を繰り返してください。API の送信成功は処理完了を意味しません。報告されたエラーを調査してから先に進んでください。Pod の退避を妨げる PDB があると `PodEvictionFailure` になることがあります。コマンドを完了させるためだけに `--force` でこれを回避しないでください。

**Blue/green:** 互換性のある AL2023 ノードグループを別途作成し、ワークロードのスケジューリングと readiness をテストしてから、段階的に移行します。アプリケーションのチェック、ボリューム／AZ の制約、ロールバック要件を確認できるまで、古い容量を保持してください。ノードラベルを一覧表示しただけでは検証にならず、トラフィックはノードグループ名ではなく Service endpoint／Pod に従います。新しいグループを作成した直後に、古いグループを自動的に削除しないでください。

**カナリア:** 小規模で、個別のラベルと taint を設定したグループを使用します。taint は無関係な Pod の配置を避けるもので、テストワークロードだけがグループを選択して toleration を設定します。システム DaemonSet は toleration があれば引き続き実行できます。これは、既存のテストクラスター向けの設定例です。

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

この完全な Deployment の例を適用する前に、専用のテストコンテキストで未使用の `upgrade-lab` namespace を作成してください。実際のカナリアでは、アプリケーション固有の依存関係と代表的なトラフィックもテストする必要があります。この NGINX Pod は、基本的なスケジューリングと readiness を確認するだけです。

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

**中断予算と容量:** この別の例は、通常 Ready なレプリカが少なくとも3つある `app-namespace` の実際の `my-app` ワークロードを前提としています。上記のレプリカが1つだけのカナリアの PDB ではありません。

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

PDB は eviction API を介して処理される自発的な退避を制限しますが、可用性を保証したり、ハードウェア障害を防止したり、Pod／Deployment の直接削除を止めたりするものではありません。`minAvailable: 2` の場合、一致する Pod のうち健全なものが2つだけだと退避はブロックされます。余剰容量、トポロジー、probe、終了時の動作、障害からの復旧を確認してください。Blue/green やカナリアの計画だけでは、安全なロールバックは証明されません。状態を持つデータでは特に注意が必要です。

参照: [マネージド更新の動作](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)、[AL2023 への移行](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[Pod disruption budget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)。

</details>

5. EKS 最適化 AL2023 EC2 ワーカーのブートストラップに含まれない処理はどれですか？
   * A) kubelet／コンテナランタイムを設定する
   * B) AWS が管理するコントロールプレーンのコンポーネントをワーカーにインストールする
   * C) ノードのクライアント認証／接続を設定する
   * D) ノードを登録する

<details>
<summary>回答を表示</summary>

**回答: B) AWS が管理するコントロールプレーンのコンポーネントをワーカーにインストールする**

ワーカーには API server、etcd、controller manager、scheduler をインストールしません。これらは AWS 管理のコントロールプレーンに属します。**従来型 EKS の CoreDNS はデータプレーンのクラスターアドオンであり、これらのコントロールプレーンコンポーネントの1つではありません。**

EKS 最適化 AL2023 AMI は `nodeadm` を使って containerd と kubelet を設定します。`nodeadm-config` がユーザーデータの前に基本設定を行い、その後 `nodeadm-run` が設定を完了してデーモンを起動します。AMI がこれを自動実行するため、ユーザーデータから `nodeadm init` を再度呼び出さないでください。AL2 の `/etc/eks/bootstrap.sh` の手順は、現在の AL2023 ブートストラップではありません。

**ノードの参加とクラスターのネットワークを分けて考える**

1. 起動前にノード IAM ロール／インスタンスプロファイルと必要なノードアクセス認可を用意してください。ブートストラップは IAM ロールを作成しません。インスタンス自身のロールを不必要に再度引き受ける手動 kubeconfig ではなく、AMI が生成する kubeconfig／認証経路を使ってください。
2. kubelet がノードを登録します。Ready になるかどうかは、クラスターへの接続だけでなく、ランタイム／CNI の健全性にも依存します。
3. 従来型 EKS では、`aws-node`、`kube-proxy`、CoreDNS をクラスターアドオンとしてデプロイ／管理します。ホストのブートストラップですべてのアドオンをインストールするわけではありません。独自に作成したファイルで CNI 設定を上書きしないでください。
4. プロバイダーが管理する `eks.amazonaws.com/nodegroup` や `topology.kubernetes.io/zone` のラベルを手動で偽装しないでください。カスタムラベル／taint は、ノードグループ／プロビジョナーの設定で管理します。

**NodeConfig 入力例**

次のコマンドは管理ワークステーション上で実行し、既存の IPv4 クラスターの実際のメタデータからユーザーデータを生成します。レビュー済みの EKS 最適化 AL2023 ベースのカスタム AMI／セルフマネージドノード向けです。カスタム AMI ID を指定しないマネージドノードグループでは、EKS がメタデータを生成／マージします。`NodeConfig` はホストのブートストラップ設定であり、`kubectl apply` で送信する通常の Kubernetes リソースではありません。

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

すべてのノードに同じ DNS サービス IP や maxPods 値をハードコードしないでください。クラスターのサービス CIDR、インスタンス／CNI／prefix 設定、文書化されたサイジング規則に従ってください。これらの確認コマンドは従来型の EC2 構成向けです。Auto Mode／Fargate では、マネージドコンポーネントが異なります。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

この監査ではノードの参加、デーモンの実行、ネットワーク動作を試しておらず、ランタイムログも収集していません。

[AL2023/nodeadm のライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [NodeConfig API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## 公式リファレンス

- [EKS のサポート対象バージョン](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS ノード IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [VPC CNI IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [NetworkPolicy の前提条件](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Metrics Server の要件](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [eksctl 設定スキーマ](https://schema.eksctl.io/)
