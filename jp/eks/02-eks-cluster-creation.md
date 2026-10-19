# EKS クラスターの作成

> **最終更新**: 2026年10月16日

Amazon EKS クラスターの作成方法はいくつかあります。この章では、さまざまなツールと方法を使ってクラスターを作成する手順を詳しく説明します。

この章で紹介する作成方法は互いに代替の選択肢です。新しく専用クラスターを作るときは1つを選び、同じリソースを複数のツールで同時に管理しないでください。例の名前、アカウント、ロール、VPC、サブネット、CIDRは、承認済みの実値に置き換えてください。特に記載がない限り、シェル例はBashです。前提条件の確認に失敗した場合は先へ進まないでください。この監査ではAWSリソースの作成も、ワークロードの計測も行っていません。

**最新リリース:** EKS 1.37は2026年10月1日に利用可能になりました。

**例で使用する基準:** 以下の例は、確認済みのEKS 1.36を引き続き使用します。別のバージョンを選ぶ場合は、[現在のEKSバージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)と各コンポーネントの互換性資料を確認してください。

## 目次

1. [前提条件](#prerequisites)
2. [eksctlを使用したクラスター作成](#creating-a-cluster-using-eksctl)
3. [AWS Management Consoleを使用したクラスター作成](#creating-a-cluster-using-aws-management-console)
4. [AWS CLIを使用したクラスター作成](#creating-a-cluster-using-aws-cli)
5. [Terraformを使用したクラスター作成](#creating-a-cluster-using-terraform)
6. [AWS CDKを使用したクラスター作成](#creating-a-cluster-using-aws-cdk)
7. [クラスターアクセスの設定](#configuring-cluster-access)
8. [クラスターの検証](#cluster-validation)
9. [クラスターのアップグレード](#cluster-upgrade)
10. [クラスターの削除](#cluster-deletion)

## 前提条件 {#prerequisites}

EKSクラスターを作成する前に、次の前提条件を満たしてください。

### 1. AWSアカウント

有効なAWSアカウントが必要です。アカウントをお持ちでない場合は、[AWSウェブサイト](https://aws.amazon.com/)から登録してください。

### 2. IAM権限

必要な権限は、使用するツールとそのツールが管理するリソースによって異なります。すべてのリソースに対する`eks:*`、`ec2:*`、`iam:*`、`cloudformation:*`を許可するポリシーは、最小権限に必要なものではありません。

| タスク | 確認する権限の範囲 |
| --- | --- |
| EKSクラスター/ノードグループの管理 | 必要なEKSアクションと対象リソース |
| 既存IAMロールの引き渡し | 承認済みロールARNとサービス条件に対する`iam:PassRole` |
| IAMロール/ポリシー/OIDCプロバイダーの作成 | ツールが管理するIAMリソース、名前、タグの範囲 |
| ネットワークの作成 | 新しいVPC、サブネット、セキュリティグループに必要なEC2アクション |
| eksctl/CDKの利用 | 関連するCloudFormationスタック、実行ロール、ブートストラップリソース |

プロビジョニングに使うID、クラスターサービスロール、ノードロールはそれぞれ別です。SCP、権限境界、セッションポリシーも引き続き適用されます。組織のプロビジョニング権限を、生成したテンプレートやプランと照らし合わせて確認してください。Auto Modeのロール要件は従来のノードグループとは異なります。

参考資料: [EKS IAMアクションとリソース](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html)、[Auto Modeのロール](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

### 3. ツールのインストール

#### AWS CLI

使用するOS/CPUに合ったパッケージを選び、[公式AWS CLI v2インストールガイド](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)の署名検証手順に従ってください。既存のv1/v2を更新する場合は、先に更新/移行方法を確認してください。

| 環境 | 公式パッケージ/インストール方法 |
| --- | --- |
| macOS | 署名済み`AWSCLIV2.pkg` |
| Linux x86_64 | PGP署名を検証した`awscli-exe-linux-x86_64.zip` |
| Linux ARM64 | PGP署名を検証した`awscli-exe-linux-aarch64.zip` |
| Windows | サポートされているWindows用MSIインストーラー |

Linux x86_64用パッケージをARMでそのまま使わないでください。`aws --version`で有効なCLIを確認します。組織でIAM Identity Centerを使う場合は、承認済みプロファイルを次のように設定してください。それ以外の場合は、長期アクセスキーを前提にせず、組織のフェデレーション手順に従ってください。

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

[IAM Identity Center認証](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)を参照してください。以降のコマンドでも、承認されたアカウント、ロール、リージョンを使用してください。

#### kubectlとeksctl（Linux/macOS）

この章のEKS 1.36の例では、kubectl **1.36.5**とeksctl **0.231.0**を基準にします。kubectlはサーバーと同じマイナーバージョンを優先してください。許容されるバージョン差は±1マイナーです。古いEKSクラスターに対して、上流の`stable.txt`から最新マイナー版を無条件にインストールしないでください。

次のBash例はAMD64/ARM64を選択し、インストール前に公式チェックサムを検証します。`curl`、`tar`、`awk`、`sha256sum`または`shasum`が必要です。`/usr/local/bin`へのインストールには管理者権限が必要です。ダウンロードまたはチェックサム検証に失敗した場合、インストールは停止します。

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.5
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.231.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

公式手順: [Linux版kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)、[macOS版kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)、[eksctlのインストール](https://eksctl.io/installation/)。

#### Windows

PowerShellでは[公式kubectlインストール手順](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)に従ってください。この章のAMD64例では[kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe)と同じパスにある`.sha256`ファイルを使います。CPUに合うWindows ZIPと、[eksctl 0.231.0リリース](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0)の`eksctl_checksums.txt`を選んでください。

`Get-FileHash -Algorithm SHA256`の結果を公式ハッシュと比較し、一致しなければ停止します。検証後にZIPを展開し、実行ファイルのディレクトリをPATHに追加して、`kubectl version --client`と`eksctl version`を確認してください。PowerShellの構文をBashで実行しないでください。

AWS CLIの例でJSONを生成するため、`jq`も準備してください。この監査では、クライアントのダウンロード/インストールやログインは行っていません。

### 4. VPCとサブネット

リージョンEKSクラスターには、同じVPC内の異なるAZに少なくとも2つのサブネットが必要です。クラスターの各サブネットにはEKS用に少なくとも6個の空きIPが必要で、AWSは16個以上を推奨しています。ノード、Pod、ロードバランサー、アップグレード分の追加アドレスも計画してください。VPCのDNSホスト名とDNS解決を有効にします。

すべてのEKSクラスターにインターネット接続が必須というわけではありません。ノードとワークロードがKubernetes API、イメージ、必要なAWSサービスへ接続できるよう、NAT/インターネット経路か、必要なVPCエンドポイントとミラー済みイメージを用意してください。Kubernetesのプライベートエンドポイントには、適切なDNSとルーティングを備えたVPC内または接続ネットワークから到達できます。

#### EKSクラスター用VPCタグ

`kubernetes.io/cluster/<cluster-name>` VPCタグは従来の仕組みであり、現在のEKSクラスター作成に常に必要なものではありません。ロードバランシングで使うサブネットは、選択したコントローラーのサブネット検出ルールに従ってください。

- パブリックロードバランサー用サブネット: `kubernetes.io/role/elb=1`
- 内部ロードバランサー用サブネット: `kubernetes.io/role/internal-elb=1`

タグはルーティング、セキュリティグループ、空きIP容量を設定しません。[VPC/サブネット要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)と[インターネット接続のないクラスター](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)を参照してください。

## eksctlを使用したクラスター作成 {#creating-a-cluster-using-eksctl}

eksctlはEKSクラスターを作成・管理する簡単な方法です。CloudFormationを使ってクラスターと関連リソースを作成します。

このシェル専用のパスにeksctlのkubeconfigを保存します。

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### 基本的なクラスター作成

確認済み設定ファイルを使って基本的なクラスターを作成します。

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

実行前に、以下の`cluster.yaml`を読んで編集してください。ここではEKS 1.36、AL2023、既存のVPCサブネット、ノードグループ容量を明示的に指定します。例の識別子とドキュメント用CIDRは承認済みの実値に置き換えてください。これらは選択した設定であり、すべてのeksctlバージョンにおける既定値を示すものではありません。

### 設定ファイルを使ったクラスター作成

より複雑な構成では、YAMLファイルでクラスターを定義できます。

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: '1.36'
vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
managedNodeGroups:
- name: ng-1
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
  privateNetworking: true
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
- name: ng-2
  instanceType: c5.xlarge
  desiredCapacity: 2
  privateNetworking: true
  spot: true
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
fargateProfiles:
- name: fp-default
  selectors:
  - namespace: default
    labels:
      env: fargate
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
```

この設定ファイルでクラスターを作るには、次のコマンドを実行します。

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

上記の構成はEC2ノードと任意のアプリケーション用Fargateプロファイルを示します。CoreDNSはEC2上に残ります。Fargateへ移す場合は、プロファイルだけでなくCoreDNSのコンピューティング設定も確認してください。

### マネージドノードグループの作成

既存クラスターにマネージドノードグループを追加するには、次のコマンドを実行します。

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking
```

設定ファイルを使うこともできます。

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: my-nodegroup
  instanceType: m5.large
  desiredCapacity: 3
  minSize: 1
  maxSize: 5
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  privateNetworking: true
  disableIMDSv1: true
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### EKS Auto Modeクラスターの作成

EKS Auto Modeは2024年に一般提供が始まり、クラスターインフラストラクチャを自動化して運用負荷を軽減します。AWSがコンピューティング、ネットワーキング、ストレージ機能を管理します。

#### EKS Auto Modeの主な機能

- **ノード管理の自動化**: ワークロード要件に応じてノードを自動で追加/削除
- **セキュリティ強化**: 不変のAMI、SELinuxの強制モード、読み取り専用ルートファイルシステム
- **ノードの保守**: 期限切れやドリフトのあるノードを置き換えます。21日間はコントロールプレーンのマイナーバージョンアップグレード周期ではありません
- **コンポーネント統合**: Podネットワーキング、DNS、ストレージ、GPUサポートを既定で提供
- **コスト最適化**: 未使用インスタンスを自動終了し、ワークロードを集約

#### Auto Modeクラスターの基本作成

以下の`auto-cluster.yaml`を使う前に、CIDRとネットワーク設定を確認してください。Auto Modeが管理するネットワーク、DNS、ブロックストレージ機能を自己管理アドオンで重複させないでください。混在クラスターでは、各コンピューティング種別に対する配置とコンポーネントの適用範囲を明示する必要があります。

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### 設定ファイルを使ったAuto Modeクラスター作成

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-auto-cluster
  region: us-west-2
  version: '1.36'
autoModeConfig:
  enabled: true
  nodePools:
  - system
  - general-purpose
vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
accessConfig:
  authenticationMode: API
```

クラスターを作成します。

```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Auto Modeと従来方式の比較

| 機能 | 従来のEKS | EKS Auto Mode |
|---------|-----------------|---------------|
| ノード管理 | マネージドノードグループまたは顧客管理ノード | AWSがノードライフサイクルを管理 |
| スケーリング | Cluster Autoscaler、自己管理Karpenterなどを設定 | マネージドノードの自動スケーリング |
| アップグレード | コントロールプレーン、ノード、アドオンを計画して更新 | AWSがノード/コンポーネントを更新。サポートポリシーに沿ったコントロールプレーンのマイナー更新は計画が必要 |
| セキュリティ | ユーザーが設定 | 既定でセキュリティを強化 |
| ネットワーキング | CNIプラグインを設定 | ネットワーク設定を自動化 |
| ストレージ | CSIのインストールと権限が必要 | 管理対象EBSプロビジョナー`ebs.csi.eks.amazonaws.com` |
| GPUサポート | 互換性のある高速化AMIと必要なデバイスプラグインを選択 | 対応インスタンスでは管理対象ドライバー/プラグインを提供 |

#### Auto Modeクラスターの検証

クラスター作成後、次のコマンドで状態を確認できます。

```bash
# Check cluster status
kubectl get nodes

# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check system pod status
kubectl get pods -n kube-system
```

#### カスタムNodePoolの作成

Auto Modeでは、既定のNodePoolに加えてカスタムNodePoolを作成できます。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.2xlarge
        - p3.8xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 336h
      taints:
      - key: nvidia.com/gpu
        value: present
        effect: NoSchedule
  limits:
    cpu: '1000'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

> **注意:** Auto Modeでは`EC2NodeClass`、`amiFamily`、カスタム`userData`（`/etc/eks/bootstrap.sh`）は使えません。AWSがノードAMIとブートストラップを管理します。サブネット、セキュリティグループ、一時ストレージは`eks.amazonaws.com/v1`の`NodeClass`で定義します。

GPU例では、現行の公式サポート一覧にあるp3を使用します。AZの容量、クォータ、GPUメモリ/モデル要件を確認してください。GPU Podは`nvidia.com/gpu`を要求し、上記のtaintを許容する必要があります。このYAMLは確認済みですが、GPUノードのプロビジョニングやベンチマークは行っていません。

#### Auto Modeの制限

- SSHまたはSSMによるノードへの直接アクセスはできません
- 既定の有効期限は336時間（14日）です。サポートされる`expireAfter`の最大値は21日です。drain、PDB/NodePoolによるブロック、既定の24時間の終了猶予を併せて確認してください
- 既定のNodePoolとNodeClassは変更できません
- 特定のインスタンスタイプに制限がある場合があります

#### Auto Modeの監視

インフラストラクチャ管理によって、各ワークロードのCloudWatchメトリクスが自動設定されるわけではありません。`cluster_node_count`は`AWS/EKS`ではなく**ContainerInsights**に属し、設定済みのContainer Insights収集パイプラインが必要です。環境に合わせて収集を設定し、実データのある期間をクエリしてください。

```bash
# Requires a configured Container Insights collection pipeline and metric data.
aws cloudwatch list-metrics --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --start-time "${METRICS_START_TIME:?Set a reviewed ISO8601 start time}" \
  --end-time "${METRICS_END_TIME:?Set a later ISO8601 end time}" \
  --period 3600 --statistics Average
```

結果が空でも、ノードがゼロであることやAuto Modeの失敗を意味しません。まず収集設定、ディメンション、時間範囲を確認してください。この監査ではCloudWatchクエリや計測を行っていません。[公式Container Insightsメトリクス一覧](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)を参照してください。

### Fargateプロファイルの作成

Fargateプロファイルを作成するには、次のコマンドを実行します。

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

設定ファイルを使うこともできます。

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-fargate-profile
  selectors:
  - namespace: default
    labels:
      env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### クラスターの更新

コントロールプレーン、ノード、アドオンの互換性を確認し、[クラスターのアップグレード](#cluster-upgrade)に従ってください。

### クラスターの削除

ワークロード、ロードバランサー、データ保持、所有ツールを確認し、[クラスターの削除](#cluster-deletion)に従ってください。

## AWS Management Consoleを使用したクラスター作成 {#creating-a-cluster-using-aws-management-console}

AWS Management ConsoleでEKSクラスターを作成する手順は次のとおりです。

1. [AWS Management Console](https://console.aws.amazon.com/)にログインします。
2. 「EKS」を検索するか、サービス一覧から「Elastic Kubernetes Service」を選びます。
3. 「Clusters」ページで「Create cluster」を選択します。

### EKS Auto Modeクラスターの作成（クイック設定）

EKS Auto Modeはインフラストラクチャの設定を簡素化します。ワークロードのID、ネットワーク、容量、可用性、復旧方法は、引き続き明示的な設定と検証が必要です。

#### 1. クイック設定を選択

4. 「Quick configuration」が選択されていることを確認します。
5. 次の情報を入力します。
   - **Cluster name**: 一意のクラスター名
   - **Kubernetes version**: 使用するKubernetesバージョン（最新バージョンを推奨）

#### 2. IAMロールを設定

6. **クラスターIAMロール**を選択します。
   - 初めてAuto Modeクラスターを作成する場合は、「Create recommended role」を使います。
   - 既存ロールを再利用することもできます。
   - 推奨ロール名: `AmazonEKSAutoClusterRole`

7. **ノードIAMロール**を選択します。
   - 初めて作成する場合は、「Create recommended role」を使います。
   - 推奨ロール名: `AmazonEKSAutoNodeRole`

#### 3. ネットワーキングを設定

8. **VPCを選択**します。
   - 新しいVPCを作る場合は「Create VPC」を選択します。
   - 既存のEKS VPCを使う場合は、そのVPCを選択します。

9. **サブネット設定**（任意）:
   - EKS Auto ModeはVPC内のプライベートサブネットを自動選択します。
   - 必要に応じてサブネットを追加または削除できます。

#### 4. 設定を確認して作成

10. **View quick configuration defaults**を選択して設定値をすべて確認します。
11. **Create cluster**を選択します（作成には約15分かかります）。

### カスタム設定によるクラスター作成

より細かく制御する場合は、カスタム設定を使用します。

### クラスター設定

4. 「Configure cluster」ページで次の情報を入力します。
   - **Cluster name**: 一意のクラスター名
   - **Kubernetes version**: 使用するバージョン
   - **Cluster service role**: 新しいロールを作るか、既存ロールを選択
   - **EKS Auto Mode**: 有効にする場合はチェックボックスをオン
   - **Tags**: 必要に応じてタグを追加
   - 「Next」を選択

### ネットワーキングを指定

5. 「Specify networking」ページで次の情報を入力します。
   - **VPC**: 新しいVPCを作るか、既存VPCを選択
   - **Subnets**: クラスターで使うサブネットを選択。異なるAZに少なくとも2つ必要です
   - **Security groups**: クラスターで使うセキュリティグループを選択
   - **Cluster endpoint access**: クラスターAPIサーバーエンドポイントへのアクセスを設定
     - **Public**: APIサーバーにインターネットからアクセス可能
     - **Private**: 適切なDNSとルーティングがあれば、VPC内または接続ネットワークからアクセス可能
     - **Public and Private**: インターネットとVPC内の両方からアクセス可能
   - 「Next」を選択

### ロギングを設定

6. 「Configure logging」ページで有効にするログ種別を選択します。
   - APIサーバーログ
   - 監査ログ
   - 認証ログ
   - コントローラーマネージャーログ
   - スケジューラーログ
   - 「Next」を選択

### アドオンを選択

以下のアドオンは従来型コンピューティングを説明しています。Auto Modeは重複するネットワーク、DNS、ブロックストレージ機能を管理します。クラスター内のコンピューティング種別に応じてコンポーネントを選択してください。

7. 「Select add-ons」ページで次のアドオンを設定します。
   - **Amazon VPC CNI**: Podネットワーキング用CNIプラグイン
   - **CoreDNS**: クラスター内のDNSサービス
   - **kube-proxy**: ネットワークプロキシとロードバランシングを提供
   - **ストレージ/ネットワークアドオン**: 従来型コンピューティングには適切なコンポーネントとIAM権限が必要です。Auto Modeは管理対象EBS/ネットワーク/DNS機能を提供するため、Auto Modeノード上に重複コンポーネントをインストールしないでください
   - 「Next」を選択

### 確認して作成

8. 「Review and create」ページで設定を確認し、「Create」を選択します。

### Auto Modeを使わないクラスターへのノードグループ追加

従来型EC2コンピューティングでは、クラスター作成後にノードグループを追加します。Fargateプロファイルなど、ほかのサポート対象の方式には個別の設定があります。Auto Modeを使わないクラスターすべてでマネージドノードグループが必須というわけではありません。

### ノードグループの追加

1. 「Node group configuration」ページで次を入力します。
   - **Node group name**: 一意のノードグループ名
   - **Node IAM role**: 新しいロールを作るか、既存ロールを選択
   - 「Next」を選択

2. 「Set compute and scaling configuration」ページで次を入力します。
   - **AMI type**: ノード用AMIの種類
   - **Instance type**: EC2インスタンスタイプ
   - **Disk size**: ノードのディスクサイズ
   - **Node count**: ノードの最小数、最大数、希望数
   - 「Next」を選択

3. 「Specify networking」ページで次を入力します。
   - **Subnets**: ノードグループで使用するサブネット
   - **Remote access configuration**: 承認済みの管理経路で必要な場合を除き、SSHは無効のままにします。SSHキーを指定する前に、送信元セキュリティグループを確認してください
   - 「Next」を選択

4. 「Review and create」ページで設定を確認し、「Create」を選択します。

## AWS CLIを使用したクラスター作成 {#creating-a-cluster-using-aws-cli}

以下の例は**新しいクラスター**を作成します。Auto Modeか従来のEKSを選び、同じ名前で両方の作成コマンドを続けて実行しないでください。Bash、`jq`、最新のAWS CLI v2、認証済みのAWSロールを使います。検証済みの例はEKS 1.36です。別のバージョンを選ぶ前に、リージョンでの対応状況と互換性を確認してください。

2つのサブネットは同じVPC内の異なるAZに置く必要があります。DNS、空きIP、セキュリティグループ、ノードからのアクセス先を別途準備してください。APIの実際のフィールド名は`endpointPrivateAccess`と`endpointPublicAccess`です。この専用例では、作成者に付与された管理者アクセスを初期設定に使います。その後のアクセスはアクセスエントリで管理してください。

### 共通入力の準備

選択したモード用のクラスターIAMロールを事前に作成し、必要な`iam:PassRole`とサービスリンクロール作成権限を確認してください。実行前にアカウント、リージョン、サブネット、承認済みCIDRも確認します。

```bash
: "${EKS_CLUSTER_NAME:?Choose a unique new cluster name}"
: "${EKS_REGION:?Choose the intended AWS region}"
: "${EKS_CLUSTER_ROLE_ARN:?Pre-created cluster role for the chosen mode}"
: "${EKS_SUBNET_A:?Existing subnet in the intended VPC}"
: "${EKS_SUBNET_B:?Existing subnet in a different AZ of the same VPC}"
: "${EKS_PUBLIC_API_CIDR:?Approved client CIDR, normally /32}"
EKS_CREATION_DIR=$(mktemp -d /tmp/eks-create.XXXXXX)
: "${EKS_CREATION_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATION_DIR/kubeconfig"
unset EKS_CREATED_CLUSTER_ARN
aws sts get-caller-identity
```

### EKS Auto Modeクラスターの作成

クラスターIAMロールは`eks.amazonaws.com`に対する`sts:AssumeRole`と`sts:TagSession`の信頼を持ち、`AmazonEKSClusterPolicy`、`AmazonEKSComputePolicy`、`AmazonEKSBlockStoragePolicyV2`、`AmazonEKSLoadBalancingPolicy`、`AmazonEKSNetworkingPolicy`、または同等のカスタム権限を備える必要があります。

ノードロールは`ec2.amazonaws.com`を信頼し、`AmazonEKSWorkerNodeMinimalPolicy`と`AmazonEC2ContainerRegistryPullOnly`を使用します。ワークロードのAWS権限はPod Identity/IRSAを通じて別途付与してください。コンピューティング、ロードバランシング、ブロックストレージをまとめて有効にし、既定の自己管理アドオンのブートストラップを無効にします。

```bash
: "${EKS_AUTO_NODE_ROLE_ARN:?Pre-created Auto Mode node role}"
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  --arg nodeRole "$EKS_AUTO_NODE_ROLE_ARN" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: false,
  computeConfig: {
    enabled: true, nodePools: ["system", "general-purpose"], nodeRoleArn: $nodeRole
  },
  kubernetesNetworkConfig: {ipFamily: "ipv4", elasticLoadBalancing: {enabled: true}},
  storageConfig: {blockStorage: {enabled: true}}
}' > "${EKS_CREATION_DIR:?}/create-auto.json"
cat "$EKS_CREATION_DIR/create-auto.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-auto.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 作成とアクセスを確認

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

ワークロードが容量を必要とするまでは、Auto Modeにノードが存在しないことがあります。NodePool/NodeClassの状態と、その後のPodスケジューリングを確認してください。クラスターが`ACTIVE`でも、アプリケーションの健全性や一定時間内の作成は保証されません。

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### 従来型クラスターの作成

Auto Modeを選択しなかった場合に限り、この代替方法を使います。クラスターIAMロールには従来型EKSの権限が必要です。EC2ノードロールとCNI/アドオン権限は別に設定します。既定のネットワークアドオンをブートストラップしても、EBS CSIやAWS LBCはインストールされません。

```bash
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: true,
  kubernetesNetworkConfig: {ipFamily: "ipv4"}
}' > "${EKS_CREATION_DIR:?}/create-standard.json"
cat "$EKS_CREATION_DIR/create-standard.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-standard.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 作成を待ち、kubeconfigを設定

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### マネージドノードグループを作成

EC2ノードロールにはワーカーノードとECRイメージ取得の権限を準備し、CNI用には別のロールを用意するか、ノードロールのCNI権限を確認してください。Auto Mode用の最小権限ノードロールをそのまま流用しないでください。プライベートサブネットにはNATまたは必要なVPCエンドポイントも必要です。このAL2023例ではSSHを既定で有効にしません。

```bash
: "${EKS_MANAGED_NODE_ROLE_ARN:?Pre-created conventional EC2 node role}"
: "${EKS_NODEGROUP_NAME:?Unique managed node group name}"
aws eks create-nodegroup \
  --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" \
  --subnets "${EKS_SUBNET_A:?}" "${EKS_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --node-role "$EKS_MANAGED_NODE_ROLE_ARN" \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 --region "${EKS_REGION:?}"

aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version}' --output json
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodes
```

`minSize`/`maxSize`を指定するだけでは、Pod需要に応じたノードスケーリングは有効になりません。状態とヘルスエラーを確認し、必要ならオートスケーラーを設定してください。作成に失敗した場合は、記録された名前/ARNと関連リソースを調べます。この監査では作成コマンドも待機コマンドも実行していません。

参考資料: [CreateCluster API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html)、[CreateNodegroup API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[Auto ModeのIAMと作成手順](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

## Terraformを使用したクラスター作成 {#creating-a-cluster-using-terraform}

次の完全な例では、**新しいクラスターを1つ**作成し、最初のapplyより前にAuto Modeまたは従来のマネージドノードグループを選択します。代替方法を2つ目のクラスターリソースとして追加したり、移行計画なしで既存クラスターを切り替えたりしないでください。Terraformのstateとprovider lockファイルは、このデプロイメント専用のものです。

### EKS Auto Mode用Terraform設定

`main.tf`として保存します。この例ではAWS provider **6.69.1**を固定し、EKS **1.36**を使います。既存のプライベートサブネットIDを明示的に指定してください。`Type=Private`のカスタムタグだけではルートや接続性の確認になりません。事前条件はplan時にVPC/AZの関係を確認しますが、プライベートルーティング、サービスエンドポイント、DNS、IP容量、ロードバランサー用サブネットタグまでは検証しません。

Auto Modeでは、コンピューティング、ロードバランシング、ブロックストレージをすべて有効にし、`bootstrap_self_managed_addons = false`にします。クラスターIAMロールには`sts:TagSession`と5つの必須ポリシーを設定します。IAMアタッチメントの依存関係は、EKSが管理対象インフラストラクチャを削除し終えるまで権限を保持します。

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_partition" "current" {}
data "aws_subnet" "selected" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}

locals {
  cluster_policies = var.enable_auto_mode ? toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSComputePolicy",
    "AmazonEKSBlockStoragePolicyV2",
    "AmazonEKSLoadBalancingPolicy",
    "AmazonEKSNetworkingPolicy",
  ]) : toset(["AmazonEKSClusterPolicy"])
  node_policies = var.enable_auto_mode ? toset([
    "AmazonEKSWorkerNodeMinimalPolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    ]) : toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    # Conventional bootstrap baseline; see the CNI role caveat in the text.
    "AmazonEKS_CNI_Policy",
  ])
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = var.enable_auto_mode ? ["sts:AssumeRole", "sts:TagSession"] : ["sts:AssumeRole"]
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each   = local.cluster_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = local.node_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.node.name
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  bootstrap_self_managed_addons = !var.enable_auto_mode

  compute_config {
    enabled       = var.enable_auto_mode
    node_pools    = var.enable_auto_mode ? ["system", "general-purpose"] : null
    node_role_arn = var.enable_auto_mode ? aws_iam_role.node.arn : null
  }
  kubernetes_network_config {
    ip_family = "ipv4"
    elastic_load_balancing {
      enabled = var.enable_auto_mode
    }
  }
  storage_config {
    block_storage {
      enabled = var.enable_auto_mode
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_api_cidrs
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Keep policies attached until EKS finishes deleting managed infrastructure.
  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_iam_role_policy_attachment.node,
  ]
  lifecycle {
    precondition {
      condition = (
        alltrue([for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id]) &&
        length(toset([for subnet in data.aws_subnet.selected : subnet.availability_zone])) >= 2
      )
      error_message = "Supply subnets in at least two AZs of the selected VPC."
    }
  }
  tags = var.tags
}

resource "aws_eks_node_group" "standard" {
  count           = var.enable_auto_mode ? 0 : 1
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = aws_eks_cluster.main.version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = ["m5.large"]
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [aws_iam_role_policy_attachment.node]
  tags       = var.tags
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

variable "enable_auto_mode" {
  description = "Creation-time choice. Changing an existing cluster requires a separate migration plan."
  type        = bool
  default     = true
}
variable "cluster_name" {
  description = "Unique name for this new cluster."
  type        = string
}
variable "kubernetes_version" {
  description = "EKS-supported minor version; 1.36 is the reviewed example."
  type        = string
  default     = "1.36"
}
variable "region" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two distinct subnet IDs are required."
  }
}
variable "public_api_cidrs" {
  type = list(string)
  validation {
    condition = length(var.public_api_cidrs) > 0 && alltrue([
      for cidr in var.public_api_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "Supply reviewed client CIDRs instead of unrestricted public API access."
  }
}
variable "operator_role_arn" {
  description = "Existing approved IAM role allowed to administer this cluster."
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-creation-example"
  }
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}
output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}
```

オペレーターアクセスエントリは、承認済みIAMロールにこのクラスターの管理者権限を付与します。作成者にKubernetes管理者権限が自動付与されるわけではありません。そのオペレーターロールはあらかじめ存在し、kubectl利用者がそのロールを引き受けられる必要があります。

従来型ノードの代替構成では、初期ブートストラップ用のCNI権限をノードロールに含めます。これは共通の権限境界であり、本番向けの強化されたワークロードID設計ではありません。本番利用前に専用CNIロールを検討し、PodからIMDSへのアクセスを制限してください。アプリケーションのAWS権限はワークロードごとのIDに付与し、無関係なアドオン権限をすべてのノードに付けないでください。

### Terraformの実行

新しい作業ディレクトリと認証済みプロビジョニングロールを使用します。サンプルIDとCIDRを対象アカウントのリソースおよび承認済みクライアントCIDRに置き換えてください。既定ではAuto Modeを選びます。

```hcl
# terraform.tfvars: replace every example identifier before planning.
cluster_name       = "eks-docs-unique-name"
region             = "us-west-2"
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-0123456789abcdef0", "subnet-1123456789abcdef0"]
public_api_cidrs   = ["203.0.113.10/32"]
operator_role_arn  = "arn:aws:iam::111122223333:role/ApprovedOperator"
enable_auto_mode  = true
```

```bash
# Run in a new directory containing main.tf and the reviewed terraform.tfvars.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply only the plan you reviewed for the intended account/region/resources.
terraform apply reviewed.tfplan

: "${EKS_REGION:?Use the same region as terraform.tfvars}"
: "${EKS_OPERATOR_ROLE_ARN:?Use the same operator role as terraform.tfvars}"
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" \
  --region "$EKS_REGION" --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

apply前にstate/backend、IAMとネットワークの変更案、課金対象リソースを確認してください。`terraform validate`ではAWSアカウント権限、クォータ、ルーティング、選択ノードがワークロードを実行できるかは検証できません。ノードグループのスケーリング範囲を設定しても、Pod需要に応じたオートスケーラーはインストールされません。

### 従来型Terraform設定

**新しい従来型クラスター**を作る場合は、同じ完全な`main.tf`を使い、最初のplanより前に`terraform.tfvars`で次の値を設定してください。

```hcl
enable_auto_mode = false
```

この設定では3つのAuto Mode機能を無効にし、従来型ネットワークアドオンをブートストラップし、従来型EC2ノード権限とAL2023マネージドノードグループを選択します。EBS CSI、AWS LBC、Metrics Server、ノードオートスケーラーはインストールしません。ワークロードに必要なコンポーネントは別途設定してください。デプロイ後にこの値を切り替えるとインフラストラクチャとIAMが変更されるため、別途移行レビューが必要です。

検証: Terraform **1.16.6**と署名済みAWS provider **6.69.1**で、ローカルの`terraform validate`を実行し、エラー/警告なしで通過しました。**plan、apply、AWS API呼び出しは実行していません**。どちらのモードもデプロイ後の検証が必要です。この例は本番運用への適合性を証明するものではありません。

参考資料: [AWS provider EKS cluster](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_cluster.html.markdown)、[マネージドノードグループ](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_node_group.html.markdown)、[Auto Modeロール要件](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

## AWS CDKを使用したクラスター作成 {#creating-a-cluster-using-aws-cdk}

この**新しいスタック**の例では`aws-cdk-lib/aws-eks-v2`を使います。ネイティブの`AWS::EKS::Cluster`とアクセスエントリを作成し、Auto Modeの有効化にLambdaカスタムリソースを必要としません。既存のデプロイ済みconstructをこの例に置き換えることを、インプレース移行として扱わないでください。

使用するバージョンはCDKライブラリ**2.273.0**、CLI **2.1145.0**、EKS **1.36**です。合成時のVPC lookupを行わず、属性指定で既存プライベートサブネットを読み込みます。デプロイ前に、指定サブネットとAZの対応、VPC DNS、ルーティング、サービス接続、ロードバランサー用サブネットタグを確認してください。インポートしたVPC定義は、これらの条件を検証しません。

### TypeScriptを使ったEKS Auto Modeクラスター

`lib/eks-auto-mode-stack.ts`として保存します。呼び出し側は既存の承認済みオペレーターロールを渡します。このクラスターの管理者アクセスを得るのはそのロールだけです。ワークロード権限は別に管理します。

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EksAutoModeProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly vpcId: string;
  readonly privateSubnetIds: string[];
  readonly availabilityZones: string[];
  readonly publicApiCidrs: string[];
  readonly operatorRoleArn: string;
}

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EksAutoModeProps) {
    super(scope, id, props);

    if (props.privateSubnetIds.length < 2 ||
        props.privateSubnetIds.length !== props.availabilityZones.length ||
        new Set(props.availabilityZones).size < 2 ||
        props.publicApiCidrs.length === 0) {
      throw new Error('Supply corresponding private subnets/AZs in at least two AZs and approved API CIDRs');
    }
    const vpc = ec2.Vpc.fromVpcAttributes(this, 'Vpc', {
      vpcId: props.vpcId,
      availabilityZones: props.availabilityZones,
      privateSubnetIds: props.privateSubnetIds,
    });

    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSClusterPolicy',
        'AmazonEKSComputePolicy',
        'AmazonEKSBlockStoragePolicyV2',
        'AmazonEKSLoadBalancingPolicy',
        'AmazonEKSNetworkingPolicy',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });
    clusterRole.assumeRolePolicy!.addStatements(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
      actions: ['sts:TagSession'],
    }));

    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSWorkerNodeMinimalPolicy',
        'AmazonEC2ContainerRegistryPullOnly',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });

    const cluster = new eks.Cluster(this, 'Cluster', {
      clusterName: props.clusterName,
      version: eks.KubernetesVersion.V1_36,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE.onlyFrom(...props.publicApiCidrs),
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
      bootstrapSelfManagedAddons: false,
      bootstrapClusterCreatorAdminPermissions: false,
      // All required policies/trust are defined above. Avoid adding the older
      // BlockStoragePolicy that CDK 2.273.0 otherwise attaches automatically.
      role: clusterRole.withoutPolicyUpdates(),
      compute: {
        nodePools: ['system', 'general-purpose'],
        nodeRole: nodeRole.withoutPolicyUpdates(),
      },
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    cluster.node.addDependency(clusterRole, nodeRole);
    cluster.grantClusterAdmin('OperatorAccess', props.operatorRoleArn);

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.clusterEndpoint });
  }
}
```

クラスターIAMロールには`sts:TagSession`と、`AmazonEKSBlockStoragePolicyV2`を含む5つのAuto Modeポリシーを明示的に設定します。`withoutPolicyUpdates()`により、CDK 2.273.0が古いブロックストレージポリシーを追加しないようにします。この例では必要な権限をすべて指定する責任があります。依存関係はクラスター削除完了までロールを保持します。ノードロールに付けるのはAuto Mode最小ワーカーポリシーとECR pullポリシーだけです。

`bootstrapSelfManagedAddons: false`は、自己管理ネットワークアドオンとの重複を避けます。Auto Modeはコンピューティング、ロードバランシング、ブロックストレージをまとめて管理します。オペレーターアクセスエントリはクラスター実行ロールとは別に作成します。

### CDKアプリのエントリーポイント

`bin/eks-auto-mode.ts`として保存し、shebangを1行目に置いてください。例のアカウント、VPC、ロール値を誤って使わないよう、環境値は必須です。

```typescript
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before synthesis/deployment`);
  return value;
}
function list(name: string): string[] {
  return required(name).split(',').map(value => value.trim()).filter(Boolean);
}
const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: required('CDK_DEFAULT_ACCOUNT'),
    region: required('CDK_DEFAULT_REGION'),
  },
  clusterName: required('EKS_CLUSTER_NAME'),
  vpcId: required('EKS_VPC_ID'),
  privateSubnetIds: list('EKS_PRIVATE_SUBNET_IDS'),
  availabilityZones: list('EKS_AVAILABILITY_ZONES'),
  publicApiCidrs: list('EKS_PUBLIC_API_CIDRS'),
  operatorRoleArn: required('EKS_OPERATOR_ROLE_ARN'),
});
```

### CDKのデプロイ

新しいプロジェクトを作成し、初期化後に上記の2ファイルを保存して、対象のアカウント/リージョンの値を指定します。認証済みで権限のあるAWSロールを使ってください。デプロイ前に合成されたIAM/ネットワーク設定と差分を確認します。CDKライブラリとCLIは別パッケージであり、バージョン番号は共通ではありません。

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1145.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.273.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1145.0 typescript@5.9.3

# Save the source files above, then set the required environment values.
: "${CDK_DEFAULT_ACCOUNT:?Set the intended AWS account ID}"
: "${CDK_DEFAULT_REGION:?Set the intended AWS region}"
: "${EKS_CLUSTER_NAME:?Use a unique name for this new cluster}"
: "${EKS_VPC_ID:?}"
: "${EKS_PRIVATE_SUBNET_IDS:?Comma-separated existing subnet IDs}"
: "${EKS_AVAILABILITY_ZONES:?Corresponding comma-separated AZs}"
: "${EKS_PUBLIC_API_CIDRS:?Approved client CIDRs, normally /32}"
: "${EKS_OPERATOR_ROLE_ARN:?Existing operator role you may assume}"
# Export the variables so the CDK application receives them.
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION EKS_CLUSTER_NAME EKS_VPC_ID
export EKS_PRIVATE_SUBNET_IDS EKS_AVAILABILITY_ZONES EKS_PUBLIC_API_CIDRS EKS_OPERATOR_ROLE_ARN

npx tsc --noEmit
npx cdk synth
# Bootstrap creates AWS resources; review the account/region and execution policy.
npx cdk bootstrap "aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION"
npx cdk diff
npx cdk deploy

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$CDK_DEFAULT_REGION" \
  --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

監査では両方のTypeScriptファイルをコンパイルし、ダミー識別子でスタックをローカル合成しました。Auto Modeの3機能、範囲を絞ったAPI CIDR、必須ロール、オペレーターアクセスエントリ1件を確認しました。Lambda/カスタムリソースは生成されませんでした。必須入力を省略すると拒否されました。**bootstrap、lookup、deploy、クラスター作成、AWS API呼び出しは実行していません**。したがって、アカウントクォータ、ネットワーク、ワークロード利用可能性はデプロイ時の確認事項です。

参考資料: [EKS V2 constructライブラリ](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html)、[Auto ModeクラスターIAMロール](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)、[Auto Mode作成手順](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

## クラスターアクセスの設定 {#configuring-cluster-access}

選択した作成方法で設定したクラスター名、リージョン、専用kubeconfigパスを使います。Terraform/CDKの例では、承認済みオペレーターロールを`EKS_OPERATOR_ROLE_ARN`に設定してください。CLI作成者のアクセスを使う場合は省略できます。kubeconfigを書き込んでもKubernetes権限は付与されません。

```bash
: "${EKS_CLUSTER_NAME:?Use the selected cluster name}"
: "${EKS_REGION:?Use the selected region}"
: "${EKS_KUBECONFIG:?Set the dedicated kubeconfig path for this method}"
aws sts get-caller-identity
if [[ -n ${EKS_OPERATOR_ROLE_ARN:-} ]]; then
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig "$EKS_KUBECONFIG"
else
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --kubeconfig "$EKS_KUBECONFIG"
fi
eks_kubectl() {
  kubectl --kubeconfig "${EKS_KUBECONFIG:?}" "$@"
}
eks_kubectl config current-context
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query cluster.accessConfig.authenticationMode
```

### RBACの設定

新しいIAMアクセスにはアクセスエントリを使います。この例は既存の`dev` namespaceで新しいロールに読み取りアクセスを付与します。作成ツールが管理するオペレーターエントリを重複して作成しないでください。認証モードは`API`または`API_AND_CONFIG_MAP`である必要があります。従来の`aws-auth`方式は非推奨です。ConfigMap全体を上書きしないでください。必要に応じて公式移行手順に従います。

```bash
# A new reader identity, distinct from the operator already granted by IaC.
: "${EKS_READER_ROLE_ARN:?Existing approved IAM role without an access entry yet}"
if eks_kubectl get namespace dev &&
   aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --principal-arn "$EKS_READER_ROLE_ARN" \
  --type STANDARD --kubernetes-groups eks-docs-readers; then
EKS_ACCESS_DIR=$(mktemp -d /tmp/eks-access.XXXXXX)
: "${EKS_ACCESS_DIR:?}"
cat > "$EKS_ACCESS_DIR/rbac.yaml" << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: eks-docs-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-docs-readers
  namespace: dev
subjects:
- kind: Group
  name: eks-docs-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: eks-docs-reader
  apiGroup: rbac.authorization.k8s.io
EOF
eks_kubectl create -f "$EKS_ACCESS_DIR/rbac.yaml"
fi
```

このreaderロールにはSecret APIアクセスも変更権限もありません。そのロールで認証し、`kubectl auth can-i`を使って確認してください。他のRBAC/EKSポリシー付与で権限が追加される場合があります。[EKSアクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)を参照してください。

## クラスターの検証 {#cluster-validation}

アクセス設定の章で準備した専用kubeconfigと`eks_kubectl`を使用してください。コントロールプレーンへアクセスできても、ノードやワークロードが健全とは限りません。

### 基本的な検証

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Auto Mode固有の検証

Auto ModeのプロビジョニングコントローラーはAWSが管理します。`karpenter` namespaceに自己管理コントローラーPodがあると期待しないでください。NodePool/NodeClassの条件とイベントを確認し、容量を必要とするワークロードではNodeClaimも調べます。

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### サンプルアプリケーションのデプロイ

新しいnamespaceを使って、イメージ取得、スケジューリング、HTTP readiness、Serviceを確認します。Fargateのみの構成では、先にこのnamespaceに一致するプロファイルを用意してください。

```bash
EKS_SAMPLE_DIR=$(mktemp -d /tmp/eks-validate.XXXXXX)
: "${EKS_SAMPLE_DIR:?}"
unset EKS_SAMPLE_NAMESPACE EKS_SAMPLE_UID
EKS_SAMPLE_CANDIDATE=$(basename "$EKS_SAMPLE_DIR" | tr '[:upper:].' '[:lower:]-')
if EKS_SAMPLE_UID=$(eks_kubectl create namespace "$EKS_SAMPLE_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  EKS_SAMPLE_NAMESPACE=$EKS_SAMPLE_CANDIDATE
fi
: "${EKS_SAMPLE_NAMESPACE:?Namespace creation failed}"
: "${EKS_SAMPLE_UID:?Namespace UID missing}"
cat > "$EKS_SAMPLE_DIR/sample-app.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      automountServiceAccountToken: false
      containers:
      - name: app
        image: nginx:1.30.6-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: http
EOF
eks_kubectl apply -f "$EKS_SAMPLE_DIR/sample-app.yaml"
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" rollout status deployment/sample-app --timeout=180s
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" get pods,services
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" port-forward --address 127.0.0.1 service/sample-app-service 8080:80
```

ポートフォワーディング中に`http://127.0.0.1:8080`を開き、Ctrl-Cで停止します。これはClusterIPへのアクセスを確認するもので、外部ロードバランサーは検証しません。NLBの場合は、Auto Modeの`eks.amazonaws.com/nlb`か、インストール済みで承認されたAWS LBCの`service.k8s.aws/nlb`を選び、ネットワーク/コストの前提条件を別途確認してください。この監査ではデプロイもポートフォワーディングも行っていません。

## クラスターのアップグレード {#cluster-upgrade}

まずアップグレードインサイト、削除されたAPI、webhook/アドオン互換性、ノードバージョン、空きIP、復旧計画を確認してください。古いノードを現在のコントロールプレーンバージョンまで更新してから、サポートされるマイナーバージョンを一つずつ進めます。コンポーネントによっては、コントロールプレーンより先に互換性のある更新が必要です。

Auto Modeが21日ごとにコントロールプレーンのマイナーバージョンを更新するわけではありません。オペレーターがマイナーアップグレードを計画し、バージョンサポートポリシーに基づく自動アップグレードも考慮します。

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks describe-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --query 'cluster.{version:version,status:status}' --output table
eks_kubectl get nodes

# After readiness/compatibility review, choose the next supported minor.
: "${NEXT_MINOR_VERSION:?Select one supported minor step, for example 1.35 to 1.36}"
EKS_UPDATE_ID=$(aws eks update-cluster-version --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --kubernetes-version "$NEXT_MINOR_VERSION" \
  --query update.id --output text)
: "${EKS_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --update-id "$EKS_UPDATE_ID" --query 'update.{status:status,errors:errors}'

# Alternative interface; do not execute both:
# eksctl upgrade cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" --version "$NEXT_MINOR_VERSION" --approve
```

更新結果が`Successful`になってからデータプレーンに進んでください。AWSはAuto Modeノードを段階的に更新します。従来型マネージドノードグループは別途更新が必要です。

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

自己管理/Hybrid Node、Fargate Podの置き換え、アドオン、kubectlは、それぞれの方式に合わせて更新を計画してください。失敗をforceフラグで隠さず、PDBと余剰容量を確認します。条件を満たすコントロールプレーンアップグレードは、ノード/アドオン/API互換性とサポートポリシー上の制約のもと、7日以内なら1マイナー分ロールバックできる場合があります。ロールバックはアプリケーションデータの復旧に代わるものではありません。

[アップグレード手順](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [ロールバック条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## クラスターの削除 {#cluster-deletion}

対象アカウントとリージョンで、元の所有ツール/stateを使って削除してください。まず、コントローラーが稼働中のうちにワークロードとIngress/LoadBalancer Serviceを削除し、完了を確認します。PVC/PV、スナップショット、ログの保持または復旧方法を決めてください。タイムアウトやfinalizerをforceオプションで回避しないでください。

### サンプルnamespaceのクリーンアップ

```bash
EKS_SAMPLE_CLEANUP_OK=true
if [[ -n ${EKS_SAMPLE_NAMESPACE:-} && -n ${EKS_SAMPLE_UID:-} ]]; then
  current_uid=$(eks_kubectl get namespace "$EKS_SAMPLE_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [[ "$current_uid" = "$EKS_SAMPLE_UID" ]]; then
    eks_kubectl delete namespace "$EKS_SAMPLE_NAMESPACE" --wait=true --timeout=180s || EKS_SAMPLE_CLEANUP_OK=false
  else
    EKS_SAMPLE_CLEANUP_OK=false
  fi
elif [[ -n ${EKS_SAMPLE_NAMESPACE:-} || -n ${EKS_SAMPLE_UID:-} ]]; then
  EKS_SAMPLE_CLEANUP_OK=false
fi
# Remove local files only after successful sample cleanup.
if [[ "$EKS_SAMPLE_CLEANUP_OK" = true ]]; then
if [[ -n ${EKS_SAMPLE_DIR:-} ]]; then
  rm -f -- "$EKS_SAMPLE_DIR/sample-app.yaml"
  rmdir -- "$EKS_SAMPLE_DIR"
fi
if [[ -n ${EKS_ACCESS_DIR:-} ]]; then
  rm -f -- "$EKS_ACCESS_DIR/rbac.yaml"
  rmdir -- "$EKS_ACCESS_DIR"
fi
else
  printf 'Sample cleanup could not be verified; stop before deleting the cluster\n' >&2
fi
```

クリーンアップに失敗したら停止して調査してください。未確認の現在値だけでなく、作成結果または所有IaC stateと対象ARNを照合します。

```bash
: "${EKS_EXPECTED_CLUSTER_ARN:?Copy the ARN from the creation result or owning IaC state}"
: "${EKS_CLUSTER_NAME:?}"
: "${EKS_REGION:?}"
EKS_DELETE_TARGET_VERIFIED=false
if [[ ${EKS_SAMPLE_CLEANUP_OK:-false} != true ]]; then
  printf 'Complete the sample cleanup check above first\n' >&2
else
current_arn=$(aws eks describe-cluster --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --query cluster.arn --output text) || current_arn=""
if [[ "$current_arn" = "$EKS_EXPECTED_CLUSTER_ARN" ]]; then
  EKS_DELETE_TARGET_VERIFIED=true
  aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
else
  printf 'Target mismatch; stop and check the account, region and owning tool\n' >&2
fi
fi
```

### eksctlで削除

eksctlで作成したクラスターには、この方法を使います。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### AWS CLIで削除

CLIで直接作成したクラスターの場合は、上記に記録した所有ノードグループ/プロファイル名を設定し、各リソースについて繰り返します。リソースを削除して残存がないことを確認してから、クラスターを削除してください。

```bash
# For a cluster created directly with the AWS CLI, after workload/data cleanup.
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  if [[ -n ${EKS_NODEGROUP_NAME:-} ]]; then
    aws eks delete-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" &&
    aws eks wait nodegroup-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
  fi
  if [[ -n ${EKS_FARGATE_PROFILE_NAME:-} ]]; then
    aws eks delete-fargate-profile --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION" &&
    aws eks wait fargate-profile-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION"
  fi
  remaining_nodes=$(aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(nodegroups)' --output text) || remaining_nodes=unknown
  remaining_profiles=$(aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(fargateProfileNames)' --output text) || remaining_profiles=unknown
  if [[ "$remaining_nodes" = 0 && "$remaining_profiles" = 0 ]]; then
    aws eks delete-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" &&
      aws eks wait cluster-deleted --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  else
    printf 'Owned node groups/Fargate profiles remain, or their status could not be verified\n' >&2
  fi
fi
```

### Terraformで削除

元の設定、backend、workspaceを使い、対象リソース/アカウント用にレビューした破棄プランだけを適用します。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### CDKで削除

元のアプリケーション、入力値、アカウント、リージョンを使い、対象スタックを確認してください。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

完了後、EKS/CloudFormationの状態と、残存するELB、ディスク、NAT、ログ、IAMリソースを確認してください。Auto Modeのロール/ポリシーは、管理対象インフラストラクチャの削除が終わるまで保持します。クラスターの削除によって、別所有のVPC、IAMロール、ログ、保持データまで削除されるとは限りません。この監査では削除コマンドを実行していません。

## まとめ

EKSクラスターの作成方法はいくつかあり、それぞれに利点と注意点があります。

- **EKS Auto Mode**: インフラ運用を自動化しますが、アプリケーションの準備状況は別途検証が必要です
- **eksctl**: シンプルで迅速なクラスター作成
- **AWS Management Console**: GUIによる作成
- **AWS CLI**: スクリプトによる自動化に適しています
- **Terraform**: Infrastructure as Codeで管理
- **AWS CDK**: プログラミング言語でインフラストラクチャを定義

本番環境では、要件に合ったコンピューティング方式とインフラ管理ツールを選び、IAM、接続性、容量、中断、復旧の動作を検証してください。テンプレートの検証やクラスター作成に成功しても、本番運用に耐えることの証明にはなりません。

### 監査での検証範囲

英語版と日本語版をそれぞれ全文読み、公式ドキュメントおよびスキーマと照合しました。検証範囲は、シェル/JSON/YAML、CDKのコンパイル/合成、Terraform validate、モックした失敗経路です。AWSプロビジョニング、アップグレード、削除、アプリケーションの実行/負荷テスト、コスト計測は行っていません。
