# EKS クラスターの作成

> **最終更新日**: 2026年10月16日

Amazon EKS クラスターを作成する方法はいくつかあります。この章では、さまざまなツールや方法を使って EKS クラスターを作成する手順を詳しく説明します。

この章で紹介する作成方法は、それぞれ別の選択肢です。新しい専用クラスターを作成する際はいずれか一つを選び、同じリソースを複数のツールで同時に管理しないでください。サンプルの名前、アカウント、ロール、VPC、サブネット、CIDR は、承認済みの実値に置き換えてください。特に記載がない限り、シェルの例は Bash を使用します。前提条件を満たせない場合は処理を中止してください。この監査では、AWS リソースのプロビジョニングやワークロードの測定は実施していません。

**現在のリリース:** EKS 1.37 は2026年10月1日に利用可能になりました。

**サンプルの基準:** 以下の例では、レビュー済みの EKS 1.36 を引き続き使用します。別のバージョンを選ぶ場合は、[現在の EKS バージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)とコンポーネントの互換性に関するドキュメントを確認してください。

## 目次

1. [前提条件](#prerequisites)
2. [eksctl を使用したクラスターの作成](#creating-a-cluster-using-eksctl)
3. [AWS Management Console を使用したクラスターの作成](#creating-a-cluster-using-aws-management-console)
4. [AWS CLI を使用したクラスターの作成](#creating-a-cluster-using-aws-cli)
5. [Terraform を使用したクラスターの作成](#creating-a-cluster-using-terraform)
6. [AWS CDK を使用したクラスターの作成](#creating-a-cluster-using-aws-cdk)
7. [クラスターアクセスの設定](#configuring-cluster-access)
8. [クラスターの検証](#cluster-validation)
9. [クラスターのアップグレード](#cluster-upgrade)
10. [クラスターの削除](#cluster-deletion)

## 前提条件 {#prerequisites}

EKS クラスターを作成する前に、以下の前提条件を満たす必要があります。

### 1. AWS アカウント

有効な AWS アカウントが必要です。AWS アカウントをお持ちでない場合は、[AWS のウェブサイト](https://aws.amazon.com/)で登録できます。

### 2. IAM の権限

必要な権限は、使用するツールとそのツールが管理するリソースによって異なります。すべてのリソースに対して `eks:*`、`ec2:*`、`iam:*`、`cloudformation:*` を許可するポリシーは、最小権限を満たすために必要なポリシーではありません。

| タスク | 確認する権限の範囲 |
| --- | --- |
| EKS クラスター／ノードグループの管理 | 必要な EKS アクションと対象リソース |
| 既存の IAM ロールの受け渡し | 承認済みのロール ARN とサービス条件に対する `iam:PassRole` |
| IAM ロール／ポリシー／OIDC プロバイダーの作成 | ツールが管理する IAM リソースと名前／タグの範囲 |
| ネットワークの作成 | 新しい VPC、サブネット、セキュリティグループに対する EC2 アクション |
| eksctl／CDK の使用 | 関連する CloudFormation スタック、実行ロール、ブートストラップリソース |

プロビジョニングに使用する ID、クラスターのサービスロール、ノードロールはそれぞれ別のものです。SCP、権限境界、セッションポリシーも引き続き適用されます。組織のプロビジョニング権限を、合成されたテンプレート／プランと照らして確認してください。Auto Mode に必要なロールは、従来のノードグループの場合とは異なります。

参照先: [EKS IAM アクションとリソース](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html)、[Auto Mode のロール](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

### 3. ツールのインストール

#### AWS CLI

使用する OS／CPU に対応するパッケージを選び、[AWS CLI v2 の公式インストールガイド](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)に記載された署名検証手順に従ってください。v1／v2 がすでにインストールされている場合は、まず更新／移行の手順を確認してください。

| 環境 | 公式パッケージ／インストール方法 |
| --- | --- |
| macOS | 署名付きの `AWSCLIV2.pkg` |
| Linux x86_64 | PGP 署名を検証する `awscli-exe-linux-x86_64.zip` |
| Linux ARM64 | PGP 署名を検証する `awscli-exe-linux-aarch64.zip` |
| Windows | サポート対象の Windows バージョン向け MSI インストーラー |

Linux x86_64 用パッケージを ARM でそのまま使用しないでください。`aws --version` で使用中の CLI を確認してください。組織で IAM Identity Center を使用している場合は、次のように承認済みのプロファイルを設定します。それ以外の場合は、長期間有効なアクセスキーを使わず、組織のフェデレーション手順に従ってください。

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

[IAM Identity Center 認証](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)を参照してください。以降のコマンドでも、承認済みのアカウント、ロール、リージョンを使用してください。

#### kubectl と eksctl（Linux/macOS）

この章の EKS 1.36 の例では、kubectl **1.36.5** と eksctl **0.231.0** を基準にしています。サーバーと同じ kubectl のマイナーバージョンを使用することを推奨します。サポートされるバージョン差はマイナーバージョンで ±1 です。古い EKS クラスターに対して、上流の `stable.txt` から最新のマイナーバージョンを無条件にインストールしないでください。

この Bash の例は AMD64／ARM64 を選択し、インストール前に公式チェックサムを検証します。`curl`、`tar`、`awk`、および `sha256sum` または `shasum` が必要です。`/usr/local/bin` へのインストールには管理者権限が必要です。ダウンロードまたはチェックサムの検証に失敗した場合、インストールは中止されます。

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

公式の手順: [Linux 版 kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)、[macOS 版 kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)、[eksctl のインストール](https://eksctl.io/installation/)。

#### Windows

PowerShell で[公式の kubectl インストール手順](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)に従ってください。この章の AMD64 の例では、[kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe)と、同じパスにある `.sha256` ファイルを使用します。使用する CPU に合った Windows ZIP と、[eksctl 0.231.0 のリリース](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0)にある `eksctl_checksums.txt` を選んでください。

`Get-FileHash -Algorithm SHA256` の結果を公式のハッシュと比較し、一致しない場合は中止してください。検証後に ZIP を展開し、実行ファイルのディレクトリを PATH に追加して、`kubectl version --client` と `eksctl version` で確認します。Bash で PowerShell の構文を実行しないでください。

また、AWS CLI の例で JSON を生成するために `jq` を用意してください。この監査では、実際のクライアントのダウンロード／インストールやログインは実施していません。

### 4. VPC とサブネット

リージョンの EKS クラスターには、同じ VPC 内の異なる AZ に少なくとも2つのサブネットが必要です。クラスターの各サブネットには、EKS 用に少なくとも6個の空き IP アドレスが必要です。AWS は少なくとも16個を推奨しています。ノード、Pod、ロードバランサー、アップグレード用に追加のアドレスを計画してください。VPC の DNS ホスト名と DNS 解決を有効にしてください。

すべての EKS クラスターでインターネットアクセスが必須というわけではありません。ノードとワークロードは、NAT／インターネット経路、または必要な VPC エンドポイントとミラーイメージを通じて、Kubernetes API、イメージ、必要な AWS サービスにアクセスする必要があります。プライベート Kubernetes エンドポイントには、適切な DNS とルーティングを設定したうえで、VPC 内または接続されたネットワークからアクセスできます。

#### EKS クラスター向けの VPC タグ

`kubernetes.io/cluster/<cluster-name>` VPC タグはレガシーな仕組みであり、現在の EKS クラスター作成で一律に必須となるものではありません。ロードバランシングのためのサブネット検出ルールは、選択したコントローラーのルールに従ってください。

- パブリックロードバランサー用のサブネット: `kubernetes.io/role/elb=1`
- 内部ロードバランサー用のサブネット: `kubernetes.io/role/internal-elb=1`

タグを設定しても、ルーティング、セキュリティグループ、空き IP アドレス容量は設定されません。[VPC／サブネットの要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)と[インターネットアクセスのないクラスター](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)を参照してください。

## eksctl を使用したクラスターの作成 {#creating-a-cluster-using-eksctl}

eksctl は EKS クラスターの作成と管理を行う最も簡単な方法です。eksctl は CloudFormation を使用して EKS クラスターと関連リソースを作成します。

このシェル専用のパスに eksctl の kubeconfig を保存します。

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### 基本的なクラスターの作成

レビュー済みの構成ファイルを使って、基本的なクラスターを作成します。

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

このコマンドを実行する前に、以下の `cluster.yaml` を読んで編集してください。EKS 1.36、AL2023、既存の VPC サブネット、ノードグループの容量を明示的に選択しています。サンプルの識別子とドキュメント用 CIDR を、実際の承認済みの値に置き換えてください。これらは選択した設定であり、すべての eksctl バージョンでのデフォルト設定を示すものではありません。

### 構成ファイルを使用したクラスターの作成

より複雑な構成では、YAML ファイルを使ってクラスターを定義できます。

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

この構成ファイルを使ってクラスターを作成するには、次のコマンドを実行します。

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

上記の構成では EC2 ノードと、任意のアプリケーション用 Fargate プロファイルを示しています。CoreDNS は EC2 上で稼働します。CoreDNS を Fargate に移す場合は、プロファイルだけでなく CoreDNS のコンピューティング設定も確認する必要があります。

### マネージドノードグループの作成

既存のクラスターにマネージドノードグループを追加するには、次のコマンドを実行します。

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

または、構成ファイルを使用できます。

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

### EKS Auto Mode クラスターの作成

EKS Auto Mode は2024年に一般提供が開始され、運用負荷を軽減するために Kubernetes クラスターのインフラストラクチャを自動化します。コンピューティング、ネットワーク、ストレージの機能は AWS が管理します。

#### EKS Auto Mode の主な機能

- **ノード管理の自動化**: ワークロードの要件に応じてノードを自動的に追加／削除
- **セキュリティの強化**: 不変の AMI、SELinux の強制モード、読み取り専用のルートファイルシステム
- **ノードのメンテナンス**: 有効期限切れや構成ドリフトが発生したノードを置き換えます。21日間という期間は、コントロールプレーンのマイナーバージョンのアップグレードサイクルではありません
- **コンポーネントの統合**: Pod ネットワーク、DNS、ストレージ、GPU サポートをデフォルトで提供
- **コストの最適化**: 使用されていないインスタンスの自動終了とワークロードの集約

#### Auto Mode クラスターの基本的な作成

まず、以下の `auto-cluster.yaml` の CIDR とネットワークを確認してください。Auto Mode と同じネットワーク、DNS、ブロックストレージ機能を提供するアドオンを自分で重複して設定しないでください。複数のコンピューティング方式を混在させるクラスターでは、各方式の配置とコンポーネントの適用範囲を明示する必要があります。

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### 構成ファイルを使用した Auto Mode クラスターの作成

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

#### Auto Mode と従来方式の比較

| 機能 | 従来の EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| ノード管理 | マネージドノードグループまたは利用者管理ノード | AWS が管理するノードのライフサイクル |
| スケーリング | Cluster Autoscaler、セルフマネージド Karpenter、または別の方式を設定 | マネージドのノード自動スケーリング |
| アップグレード | コントロールプレーン、ノード、アドオンの更新を計画 | AWS がノード／コンポーネントの更新を管理。サポートポリシーに沿ったコントロールプレーンのマイナーアップグレードを計画 |
| セキュリティ | ユーザーが設定 | デフォルトでセキュリティを強化 |
| ネットワーク | CNI プラグインのセットアップ | ネットワーク設定を自動化 |
| ストレージ | CSI のインストールと権限設定が必要 | マネージド EBS プロビジョナー `ebs.csi.eks.amazonaws.com` |
| GPU サポート | 互換性のある高速化 AMI と必要なデバイスプラグインを選択 | サポート対象インスタンス向けのマネージドドライバー／プラグイン |

#### Auto Mode クラスターの検証

クラスターの作成後、次のコマンドでステータスを確認できます。

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

#### カスタムノードプールの作成

Auto Mode では、デフォルトのノードプールに加えてカスタムノードプールを作成できます。

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

> **注**: Auto Mode では `EC2NodeClass`、`amiFamily`、カスタムの `userData`（`/etc/eks/bootstrap.sh`）を使用できません。AWS がノード AMI とブートストラップを管理します。サブネット、セキュリティグループ、一時ストレージは、代わりに `eks.amazonaws.com/v1` の `NodeClass` で定義します。

GPU の例では、現在の公式サポート対象リストに含まれる p3 を使用しています。AZ の容量、クォータ、GPU メモリ／モデルの要件を確認してください。GPU Pod は `nvidia.com/gpu` を要求し、上記の taint を許容する必要があります。この YAML はレビュー済みですが、GPU ノードのプロビジョニングやベンチマークは実施していません。

#### Auto Mode の制限

- SSH または SSM によるノードへの直接アクセスはできません
- デフォルトの有効期限は336時間（14日間）で、サポートされる `expireAfter` の最大値は21日間です。ドレイン、PDB／NodePool による阻害要因、デフォルトの24時間の終了猶予期間を併せて確認してください
- デフォルトのノードプールとノードクラスは変更できません
- 特定のインスタンスタイプに制限がある場合があります

#### Auto Mode の監視

インフラストラクチャがマネージドであっても、すべてのワークロードについて CloudWatch メトリクスが自動設定されるわけではありません。`cluster_node_count` は `AWS/EKS` ではなく **ContainerInsights** に属し、Container Insights の収集パイプラインが設定されている必要があります。環境に合わせて収集を設定し、実際のデータが存在する時間範囲を指定してクエリしてください。

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

結果が空でも、ノードがゼロであることや Auto Mode の障害を示すわけではありません。まず収集設定、ディメンション、時間範囲を確認してください。この監査では CloudWatch クエリや測定を実施していません。[Container Insights の公式メトリクス一覧](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)を参照してください。

### Fargate プロファイルの作成

Fargate プロファイルを作成するには、次のコマンドを実行します。

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

または、構成ファイルを使用できます。

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

コントロールプレーン、ノード、アドオンの互換性を確認したうえで、[クラスターのアップグレード](#cluster-upgrade)の手順に従ってください。

### クラスターの削除

ワークロード、ロードバランサー、データ保持、リソースを管理するツールを確認したうえで、[クラスターの削除](#cluster-deletion)の手順に従ってください。

## AWS Management Console を使用したクラスターの作成 {#creating-a-cluster-using-aws-management-console}

AWS Management Console を使って EKS クラスターを作成する手順は次のとおりです。

1. [AWS Management Console](https://console.aws.amazon.com/)にログインします。
2. 「EKS」を検索するか、サービス一覧から「Elastic Kubernetes Service」を選択します。
3. 「Clusters」ページで「Create cluster」ボタンをクリックします。

### EKS Auto Mode クラスターの作成（クイック設定）

EKS Auto Mode により、インフラストラクチャのセットアップが簡素化されます。ただし、ワークロードの ID、ネットワーク、容量、可用性、復旧については、引き続き明示的な設定と検証が必要です。

#### 1. クイック設定の選択

4. 「Quick configuration」が選択されていることを確認します。
5. 次の情報を入力します。
   - **クラスター名**: クラスターの一意な名前を入力します。
   - **Kubernetes バージョン**: 使用する Kubernetes バージョンを選択します（最新バージョンを推奨）。

#### 2. IAM ロールの設定

6. **クラスター IAM ロール**の選択:
   - 最初の Auto Mode クラスターでは、「Create recommended role」オプションを使用します。
   - 既存のロールがある場合は、それを再利用できます。
   - 推奨ロール名: `AmazonEKSAutoClusterRole`

7. **ノード IAM ロール**の選択:
   - 最初の Auto Mode クラスターでは、「Create recommended role」オプションを使用します。
   - 推奨ロール名: `AmazonEKSAutoNodeRole`

#### 3. ネットワークの設定

8. **VPC を選択**:
   - 新しい VPC を作成する: 「Create VPC」を選択して EKS 用の新しい VPC を作成します。
   - 既存の VPC を使用する: 以前に作成した EKS 用 VPC を選択します。

9. **サブネットの設定**（任意）:
   - EKS Auto Mode は VPC 内のプライベートサブネットを自動的に選択します。
   - 必要に応じてサブネットを追加または削除できます。

#### 4. 設定の確認と作成

10. **View quick configuration defaults**を選択し、すべての設定値を確認します。
11. **Create cluster**をクリックします。（クラスターの作成には約15分かかります）

### カスタム設定によるクラスターの作成

より細かく制御する必要がある場合は、カスタム設定を使用できます。

### クラスターの設定

4. 「Configure cluster」ページで、次の情報を入力します。
   - **クラスター名**: クラスターの一意な名前を入力します。
   - **Kubernetes バージョン**: 使用する Kubernetes バージョンを選択します。
   - **クラスターサービスロール**: 新しいロールを作成するか、既存のロールを選択します。
   - **EKS Auto Mode**: Auto Mode を有効にするには、チェックボックスをオンにします。
   - **タグ**: 必要に応じてタグを追加します。
   - 「Next」ボタンをクリックします。

### ネットワークの指定

5. 「Specify networking」ページで、次の情報を入力します。
   - **VPC**: 新しい VPC を作成するか、既存の VPC を選択します。
   - **サブネット**: クラスターで使用するサブネットを選択します。少なくとも2つのサブネットが、異なるアベイラビリティーゾーンに存在する必要があります。
   - **セキュリティグループ**: クラスターで使用するセキュリティグループを選択します。
   - **クラスターエンドポイントへのアクセス**: クラスター API サーバーのエンドポイントへのアクセスを設定します。
     - **パブリック**: API サーバーにインターネット経由でアクセスできます。
     - **プライベート**: VPC 内または接続されたネットワークからアクセスするには、適切な DNS とルーティングが必要です。
     - **パブリックおよびプライベート**: API サーバーにインターネット経由と VPC 内の両方からアクセスできます。
   - 「Next」ボタンをクリックします。

### ログの設定

6. 「Configure logging」ページで、次の情報を入力します。
   - **コントロールプレーンのログ記録**: 有効にするログの種類を選択します。
     - API サーバーログ
     - 監査ログ
     - 認証ログ
     - コントローラーマネージャーログ
     - スケジューラーログ
   - 「Next」ボタンをクリックします。

### アドオンの選択

以下のアドオンは従来のコンピューティング方式を対象としています。Auto Mode は、機能が重複するネットワーク、DNS、ブロックストレージの機能を管理します。クラスター内のコンピューティング方式に応じてコンポーネントを選択してください。

7. 「Select add-ons」ページで、次の情報を入力します。
   - **Amazon VPC CNI**: Pod ネットワーク用の CNI プラグイン。
   - **CoreDNS**: クラスター内の DNS サービス。
   - **kube-proxy**: ネットワークプロキシとロードバランシングを提供します。
   - **ストレージ／ネットワークのアドオン**: 従来のコンピューティング方式では、適切なコンポーネントをインストールし、IAM 権限を設定する必要があります。Auto Mode はマネージド EBS／ネットワーク／DNS 機能を提供するため、Auto Mode ノードに機能が重複するコンポーネントをインストールしないでください。
   - 「Next」ボタンをクリックします。

### 確認と作成

8. 「Review and create」ページで設定を確認し、「Create」ボタンをクリックします。

### Auto Mode 以外のクラスターへのノードグループの追加

従来の EC2 コンピューティングを使用する場合は、クラスター作成後にノードグループを追加します。Fargate プロファイルなど、ほかのサポート対象の選択肢にはそれぞれ独自の設定があります。Auto Mode 以外のすべてのクラスターでマネージドノードグループが必須というわけではありません。

### ノードグループの追加

1. 「Node group configuration」ページで、次の情報を入力します。
   - **ノードグループ名**: ノードグループの一意な名前を入力します。
   - **ノード IAM ロール**: 新しいロールを作成するか、既存のロールを選択します。
   - 「Next」ボタンをクリックします。

2. 「Set compute and scaling configuration」ページで、次の情報を入力します。
   - **AMI タイプ**: ノードに使用する AMI タイプを選択します。
   - **インスタンスタイプ**: ノードに使用する EC2 インスタンスタイプを選択します。
   - **ディスクサイズ**: ノードのディスクサイズを指定します。
   - **ノード数**: ノードの最小数、最大数、希望数を指定します。
   - 「Next」ボタンをクリックします。

3. 「Specify networking」ページで、次の情報を入力します。
   - **サブネット**: ノードグループで使用するサブネットを選択します。
   - **リモートアクセス設定**: 承認済みの管理経路で必要な場合を除き、SSH を無効のままにしてください。送信元セキュリティグループを確認せずに SSH キーを指定しないでください。
   - 「Next」ボタンをクリックします。

4. 「Review and create」ページで設定を確認し、「Create」ボタンをクリックします。

## AWS CLI を使用したクラスターの作成 {#creating-a-cluster-using-aws-cli}

以下の例では**新しいクラスター**を作成します。Auto Mode と従来の EKS のいずれかを選び、同じ名前で両方の作成コマンドを続けて実行しないでください。Bash、`jq`、最新の AWS CLI v2、認可された AWS ロールを使用してください。EKS 1.36 は検証済みのサンプルバージョンです。別のバージョンを選ぶ場合は、リージョンでのサポート状況と互換性を確認してください。

2つのサブネットは、同じ VPC 内の異なる AZ に存在する必要があります。DNS、空き IP アドレス、セキュリティグループ、ノードからイメージ／サービスへのアクセスは、それぞれ別途準備してください。実際の API フィールド名は `endpointPrivateAccess` と `endpointPublicAccess` です。この専用サンプルでは、クラスター作成者の管理者アクセスを初期設定に使います。その後のアクセスはアクセスエントリで管理してください。

### 共通の入力値を準備する

選択したモード用のクラスターロールを事前に作成し、必要な `iam:PassRole` とサービスリンクロール作成の権限を確認してください。作成コマンドを実行する前に、アカウント、リージョン、サブネット、承認済み CIDR を確認してください。

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

### EKS Auto Mode クラスターの作成

クラスターロールには、`eks.amazonaws.com` に対する `sts:AssumeRole` と `sts:TagSession` の信頼設定、および `AmazonEKSClusterPolicy`、`AmazonEKSComputePolicy`、`AmazonEKSBlockStoragePolicyV2`、`AmazonEKSLoadBalancingPolicy`、`AmazonEKSNetworkingPolicy`、またはそれらと同等のカスタム権限が必要です。

ノードロールは `ec2.amazonaws.com` を信頼し、`AmazonEKSWorkerNodeMinimalPolicy` と `AmazonEC2ContainerRegistryPullOnly` を使用します。ワークロード用の AWS 権限は、Pod Identity／IRSA を使って別途付与してください。コンピューティング、ロードバランシング、ブロックストレージをまとめて有効にし、デフォルトのセルフマネージドアドオンのブートストラップは無効にしてください。

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

#### 作成とアクセスの確認

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

Auto Mode では、ワークロードが容量を必要とするまでノードが存在しない場合があります。NodePool／NodeClass のステータスと、その後の Pod スケジューリングを確認してください。クラスターが `ACTIVE` でも、アプリケーションの正常性が証明されるわけではなく、作成時間が一定であることも保証されません。

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### 従来型クラスターの作成

Auto Mode を選択していない場合に限り、この方法を使用してください。クラスターロールには従来型 EKS のクラスター権限が必要です。EC2 ノードロールと CNI／アドオンの権限は別途必要です。デフォルトのネットワークアドオンをブートストラップしても、EBS CSI や AWS LBC はインストールされません。

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

#### 作成を待ち、kubeconfig を設定する

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### マネージドノードグループの作成

EC2 ノードロールにはワーカーノードと ECR からのプルに必要な権限を準備し、CNI ロールまたはレビュー済みのノードロール向け CNI 権限は別途用意してください。Auto Mode の最小権限ノードロールをそのまま再利用しないでください。プライベートサブネットには NAT または必要な VPC エンドポイントも必要です。この AL2023 の例では、デフォルトで SSH を有効にしません。

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

`minSize`／`maxSize` を指定しただけでは、Pod の需要に応じたノードスケーリングは有効になりません。ステータスとヘルスエラーを確認し、必要であればオートスケーラーを設定してください。作成に失敗した場合は、記録された名前／ARN と関連リソースを確認してください。この監査では、これらの作成および待機コマンドを実行していません。

参照先: [CreateCluster API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html)、[CreateNodegroup API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[Auto Mode の IAM と作成手順](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

## Terraform を使用したクラスターの作成 {#creating-a-cluster-using-terraform}

以下の完全な例は、Auto Mode または従来型のマネージドノードグループを最初の apply 前に選択して、**新しいクラスターを1つ**作成するものです。もう一方の方法を2つ目のクラスターリソースとして追加したり、移行計画なしに既存クラスターの設定を切り替えたりしないでください。Terraform の state と provider のロックファイルは、このデプロイメント専用のものです。

### EKS Auto Mode クラスターの Terraform 設定

`main.tf` として保存します。この例では AWS provider **6.69.1** を固定し、EKS **1.36** を使用します。既存のプライベートサブネット ID を明示的に指定してください。カスタムの `Type=Private` タグは、ルートや接続性を検証する代わりにはなりません。事前条件により、プラン作成時に VPC／AZ の関係は検査されますが、プライベートルーティング、サービスエンドポイント、DNS、IP 容量、ロードバランサー用サブネットタグは検証されません。

Auto Mode では、コンピューティング、ロードバランシング、ブロックストレージをまとめて有効にし、`bootstrap_self_managed_addons = false` にする必要があります。クラスターロールには `sts:TagSession` と5つすべての必須ポリシーが含まれます。IAM アタッチメントの依存関係により、EKS がマネージドインフラストラクチャを削除している間も権限が維持されます。

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

オペレーターのアクセスエントリにより、承認済み IAM ロールにクラスター管理者権限が付与されます。作成者に Kubernetes 管理者権限が自動的に付与されるわけではありません。このオペレーターロールは事前に存在している必要があり、kubectl を使用するユーザーはそのロールを引き受けられる必要があります。

従来型ノードを使う方法では、初期ブートストラップ用の基準として、ノードロールに CNI 権限が含まれています。これは権限の共通境界であり、本番環境向けに強化されたワークロード ID 設計ではありません。本番環境で使用する前に、専用の CNI ロールを検討し、Pod から IMDS へのアクセスを制限してください。アプリケーションの AWS 権限は、ワークロードごとの ID に付与します。無関係なアドオンの権限をすべてのノードにアタッチしないでください。

### Terraform の実行

新しい作業ディレクトリと、認証済みのプロビジョニングロールを使用してください。サンプル ID とドキュメント用 CIDR は、対象アカウントのリソースと承認済みのクライアント CIDR に置き換えてください。デフォルトでは Auto Mode が選択されます。

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

apply の前に、state／バックエンド、提案された IAM とネットワークの変更、課金対象となるすべてのリソースを確認してください。`terraform validate` では、AWS アカウントの権限、クォータ、ルーティング、選択したノードでワークロードを実行できるかどうかは検証できません。ノードグループのスケーリング上限を設定しても、Pod の需要に応じたオートスケーラーはインストールされません。

### 従来型 Terraform の設定

**新しい従来型クラスター**を作成する場合は、同じ完全な `main.tf` を使用し、最初の plan の前に `terraform.tfvars` で次の値を設定します。

```hcl
enable_auto_mode = false
```

これにより、Auto Mode の3つの機能すべてが無効になり、従来型のネットワークアドオンがブートストラップされ、従来型 EC2 ノードの権限が選択され、AL2023 のマネージドノードグループが作成されます。EBS CSI、AWS LBC、Metrics Server、ノードオートスケーラーはインストールされません。ワークロードに必要なコンポーネントは別途設定してください。デプロイ後にこの値を切り替えると、インフラストラクチャと IAM が変更されるため、別途移行レビューが必要です。

検証: 署名付き AWS provider **6.69.1** を使用した Terraform **1.16.6** で、ローカルの `terraform validate` がエラー／警告ゼロで成功しました。**plan、apply、AWS API 呼び出しは実行していません**。どちらのモードも、引き続きデプロイ後の検証が必要です。この例は本番環境への準備が整っていることを示すものではありません。

参照先: [AWS provider の EKS クラスター](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_cluster.html.markdown)、[マネージドノードグループ](https://github.com/hashicorp/terraform-provider-aws/blob/v6.69.1/website/docs/r/eks_node_group.html.markdown)、[Auto Mode のロール要件](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

## AWS CDK を使用したクラスターの作成 {#creating-a-cluster-using-aws-cdk}

この**新しいスタック**の例では `aws-cdk-lib/aws-eks-v2` を使用します。ネイティブの `AWS::EKS::Cluster` とアクセスエントリを作成するため、Auto Mode の有効化に Lambda カスタムリソースは必要ありません。既存のデプロイ済み構成をこの例で置き換えることを、インプレース移行として扱わないでください。

この例では CDK ライブラリ **2.273.0**、CLI **2.1145.0**、EKS **1.36** を使用します。合成時に VPC を検索せず、属性を指定して既存のプライベートサブネットをインポートします。デプロイ前に、指定したサブネットと AZ の対応関係、VPC の DNS、ルーティング、サービスアクセス、ロードバランサー用サブネットタグを確認してください。VPC 定義をインポートしても、これらの条件は検証されません。

### TypeScript を使用した EKS Auto Mode クラスター

`lib/eks-auto-mode-stack.ts` として保存します。呼び出し元が既存の承認済みオペレーターロールを指定します。このクラスターの管理者アクセスを受け取るのは、そのロールだけです。ワークロードの権限は別途管理します。

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

クラスターロールには、`sts:TagSession` と、`AmazonEKSBlockStoragePolicyV2` を含む Auto Mode の5つのポリシーを明示的に指定しています。`withoutPolicyUpdates()` によって、CDK 2.273.0 が古いブロックストレージポリシーを追加することを防ぎます。この例では必要な権限をすべて指定する責任があります。クラスターの削除が完了するまで、依存関係によってこれらのロールが保持されます。ノードロールには、Auto Mode の最小権限ワーカー用ポリシーと ECR からのプル用ポリシーのみが設定されています。

`bootstrapSelfManagedAddons: false` により、機能が重複するセルフマネージドのネットワークアドオンを避けます。Auto Mode はコンピューティング、ロードバランシング、ブロックストレージをまとめて管理します。オペレーターのアクセスエントリは、クラスター実行ロールとは別に作成されます。

### CDK アプリケーションのエントリーポイント

`bin/eks-auto-mode.ts` として保存します。シバンは1行目に置いてください。サンプルのアカウント、VPC、ロール値が誤って使われることを防ぐため、環境変数は必須です。

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

### CDK のデプロイ

新しいプロジェクトを作成し、初期化後に上記の2つのファイルを保存して、対象のアカウント／リージョンの値を指定します。認証済みで認可された AWS ロールを使用してください。デプロイ前に、合成された IAM／ネットワーク設定と差分を確認します。CDK ライブラリと CLI は別々のパッケージであり、バージョン番号は同じではありません。

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

監査では、ダミーの識別子を使って両方の TypeScript ファイルをコンパイルし、スタックをローカルで合成しました。Auto Mode の3つすべての機能、スコープを限定した API CIDR、必要なロール、1つのオペレーターアクセスエントリを確認しました。Lambda／カスタムリソースは生成されませんでした。必須入力が不足している場合はエラーになりました。**ブートストラップ、検索、デプロイ、クラスター作成、AWS API 呼び出しは実行していません**。そのため、アカウントのクォータ、ネットワーク、ワークロードの可用性はデプロイ時に確認する必要があります。

参照先: [EKS V2 コンストラクトライブラリ](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html)、[Auto Mode のクラスター IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)、[Auto Mode の作成手順](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

## クラスターアクセスの設定 {#configuring-cluster-access}

選択した方法で作成したクラスター名、リージョン、専用 kubeconfig パスを設定します。Terraform／CDK の例では、承認済みのオペレーターロールを `EKS_OPERATOR_ROLE_ARN` に設定してください。CLI の作成者アクセスを使用する場合は省略できます。kubeconfig を書き込んでも Kubernetes の権限は付与されません。

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

### RBAC の設定

新しい IAM アクセスにはアクセスエントリを使用します。この例では、既存の `dev` Namespace に対し、新しいロールに読み取りアクセスを付与します。作成ツールが管理するオペレーターエントリを重複して作成しないでください。認証モードは `API` または `API_AND_CONFIG_MAP` である必要があります。レガシーの `aws-auth` 方式は非推奨です。ConfigMap 全体を上書きしないでください。必要に応じて公式の移行手順に従ってください。

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

この読み取りロールでは、Secret API へのアクセスも変更権限も付与されません。そのロールとして認証し、`kubectl auth can-i` で確認してください。ほかの RBAC／EKS ポリシーの許可によって権限が追加される場合があります。[EKS アクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)

## クラスターの検証 {#cluster-validation}

アクセスのセクションで設定した `eks_kubectl` と同じ専用 kubeconfig を使用します。コントロールプレーンにアクセスできるだけでは、ノードやワークロードの正常性は確認できません。

### 基本的な検証

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Auto Mode 固有の検証

Auto Mode のプロビジョニングコントローラーは AWS が管理します。`karpenter` Namespace にセルフマネージドのコントローラー Pod があると想定しないでください。NodePool／NodeClass の Conditions とイベントを確認し、容量が必要なワークロードについては NodeClaim も確認してください。

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### サンプルアプリケーションのデプロイ

新しい Namespace を使って、イメージへのアクセス、スケジューリング、HTTP の準備完了状態、Service を確認します。Fargate のみを使う構成では、まずこの Namespace に一致するプロファイルが必要です。

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

ポートフォワーディングの実行中に `http://127.0.0.1:8080` を開き、その後 Ctrl-C で停止します。これは ClusterIP へのアクセスを確認するものであり、外部ロードバランサーは確認しません。NLB を使用する場合は、Auto Mode の `eks.amazonaws.com/nlb`、またはインストール済みで認可された AWS LBC の `service.k8s.aws/nlb` を選択し、ネットワーク／コストの前提条件を別途確認してください。この監査ではデプロイやポートフォワーディングを実行していません。

## クラスターのアップグレード {#cluster-upgrade}

まず、アップグレードインサイト、削除された API、Webhook／アドオンの互換性、ノードのバージョン、予備の IP アドレス、復旧計画を確認してください。遅れているノードを現在のコントロールプレーンバージョンに合わせてから、サポート対象のマイナーバージョンを一つずつ進めます。コンポーネントによっては、コントロールプレーンより先に互換性のある更新が必要です。

Auto Mode では、コントロールプレーンのマイナーバージョンを21日ごとにアップグレードするわけではありません。オペレーターはマイナーアップグレードを計画し、バージョンサポートポリシーに基づく自動アップグレードも考慮する必要があります。

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

更新が `Successful` と報告されてから、データプレーンに進んでください。AWS は Auto Mode ノードを段階的に更新します。従来型のマネージドノードグループは別途更新が必要です。

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

セルフマネージド／Hybrid Node の更新、Fargate Pod の置き換え、アドオンの更新、kubectl の更新は、それぞれの仕組みに応じて計画してください。失敗を force フラグで隠すのではなく、PDB と予備容量を確認してください。条件を満たすコントロールプレーンのアップグレードは、ノード／アドオン／API の互換性とサポートポリシーの制約に従い、7日以内であれば1つ前のマイナーバージョンにロールバックできる場合があります。ロールバックはアプリケーションデータの復旧に代わるものではありません。

[アップグレード手順](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [ロールバックの条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## クラスターの削除 {#cluster-deletion}

対象のアカウントとリージョンで、最初にリソースを作成したツール／state を使って削除してください。まず、コントローラーが稼働している間にワークロードと Ingress／LoadBalancer Service を削除し、完了を確認します。PVC／PV、スナップショット、ログを保持するか復旧するかを決めてください。タイムアウトや finalizer を force オプションで回避しないでください。

### サンプル Namespace のクリーンアップ

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

クリーンアップに失敗した場合は停止して調査してください。対象 ARN は、未確認の現在の検索結果だけでなく、作成時の結果またはリソースを管理する IaC state と照合してください。

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

### eksctl を使用した削除

eksctl で作成したクラスターには、この方法を使用します。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### AWS CLI を使用した削除

CLI で直接作成したクラスターでは、上記で一覧表示した管理対象のノードグループ名／プロファイル名を設定し、各リソースについて繰り返します。削除を待ち、残存リソースがないことを確認してからクラスターを削除してください。

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

### Terraform を使用した削除

元の構成、バックエンド、workspace を使用し、対象のリソース／アカウント向けにレビューした破棄プランのみを適用してください。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### CDK を使用した削除

元のアプリケーション、入力値、アカウント、リージョンを使用し、対象のスタックを確認してください。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

削除後、EKS／CloudFormation のステータスと、残存する ELB、ディスク、NAT、ログ、IAM リソースを確認してください。マネージドインフラストラクチャの削除が完了するまで、Auto Mode のロール／ポリシーを保持してください。クラスターを削除しても、別の場所で管理されている VPC、IAM ロール、ログ、保持対象データまで削除されるとは限りません。この監査では削除コマンドを実行していません。

## まとめ

EKS クラスターの作成方法はいくつかあり、それぞれに長所と短所があります。

- **EKS Auto Mode**: インフラストラクチャの運用を自動化します。アプリケーションの準備状況は引き続き検証が必要です
- **eksctl**: 簡単かつ迅速にクラスターを作成できます
- **AWS Management Console**: GUI を使って直感的に作成できます
- **AWS CLI**: スクリプトによる自動化に適しています
- **Terraform**: インフラストラクチャをコードとして管理できます
- **AWS CDK**: プログラミング言語を使用してインフラストラクチャを定義できます

本番環境では、要件に合ったコンピューティング方式とインフラストラクチャツールを選び、IAM、接続性、容量、中断、復旧の動作を検証してください。テンプレートやクラスターの作成に成功しても、本番環境への準備が整ったことの証明にはなりません。

### 監査での検証範囲

両方の完全な言語版を読み、公式ドキュメントとスキーマに照らして確認しました。検証範囲には、シェル／JSON／YAML、CDK のコンパイル／合成、Terraform validate、モックを使った失敗経路が含まれます。AWS のプロビジョニング、アップグレード、削除、アプリケーションの実行時／負荷テスト、コスト測定は実施していません。
