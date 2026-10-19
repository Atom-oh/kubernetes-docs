# パート 1: 前提条件

> **最終更新日**: 2026 年 10 月 16 日

Amazon EKS クラスターを作成する方法はいくつかあります。この章では、さまざまなツールと方法を使用して EKS クラスターを作成する方法を学びます。

**現在のリリース:** EKS 1.37 は 2026 年 10 月 1 日に利用可能になりました。

**例のベースライン:** クラスター作成の章では、レビュー済みの EKS 1.36 ベースラインを使用します。別のサポート対象バージョンを選択する前に、そのツール、ノードイメージ、アドオンとの互換性を確認してください。

## 目次

1. [前提条件](#prerequisites)
2. [eksctl](02-eks-cluster-creation-part2.md)
3. [AWS マネジメントコンソールと CLI](02-eks-cluster-creation-part3.md)
4. [Terraform](02-eks-cluster-creation-part4.md)
5. [アクセス、検証、アップグレード、削除](02-eks-cluster-creation-part5.md)
6. [完全ガイドと CDK](02-eks-cluster-creation.md)

## 前提条件 {#prerequisites}

EKS クラスターを作成する前に、次の前提条件を満たす必要があります。

### 1. AWS アカウント

有効な AWS アカウントが必要です。AWS アカウントをお持ちでない場合は、[AWS ウェブサイト](https://aws.amazon.com/) で登録できます。

### 2. IAM 権限

必要な権限は、ツールとそのツールが管理するリソースによって異なります。すべてのリソースに対して `eks:*`、`ec2:*`、`iam:*`、`cloudformation:*` を許可するポリシーは、必須の最小権限ポリシーではありません。

| タスク | 確認すべき権限スコープ |
| --- | --- |
| EKS クラスター／ノードグループの管理 | 必要な EKS アクションと対象リソース |
| 既存 IAM ロールの引き渡し | 承認済みロール ARN およびサービス条件に対する `iam:PassRole` |
| IAM ロール／ポリシー／OIDC プロバイダーの作成 | ツール管理 IAM リソースと名前／タグのスコープ |
| ネットワークの作成 | 新しい VPC、サブネット、セキュリティグループに対する EC2 アクション |
| eksctl/CDK の使用 | 関連する CloudFormation スタック、実行ロール、ブートストラップリソース |

プロビジョニングアイデンティティ、クラスターサービスロール、ノードロールはそれぞれ別です。SCP、permissions boundary、セッションポリシーは引き続き適用されます。組織のプロビジョニング権限を、生成されたテンプレート／プランに照らして確認してください。Auto Mode のロール要件は、従来のノードグループとは異なります。

参照: [EKS IAM アクションとリソース](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html)、[Auto Mode のロール](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

### 3. ツールのインストール

#### AWS CLI

OS/CPU 用のパッケージを選択し、[AWS CLI v2 公式インストールガイド](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) に従って署名を検証してください。既存の v1/v2 インストールがある場合は、先にその更新／移行手順を確認してください。

| 環境 | 公式パッケージ／インストール方法 |
| --- | --- |
| macOS | 署名済み `AWSCLIV2.pkg` |
| Linux x86_64 | PGP 署名検証付きの `awscli-exe-linux-x86_64.zip` |
| Linux ARM64 | PGP 署名検証付きの `awscli-exe-linux-aarch64.zip` |
| Windows | サポート対象 Windows バージョン用の MSI インストーラー |

ARM で Linux x86_64 パッケージを変更せずに使用しないでください。`aws --version` でアクティブな CLI を確認してください。組織で IAM Identity Center を使用している場合は、以下のように承認済みプロファイルを設定してください。それ以外の場合は、長期アクセスキーを想定せず、そのフェデレーション手順に従ってください。

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

[IAM Identity Center 認証](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) を参照してください。以降のコマンドでは、引き続き承認済みのアカウント、ロール、リージョンを使用してください。

#### kubectl と eksctl — Linux/macOS

この章の EKS 1.36 の例では、kubectl **1.36.5** と eksctl **0.231.0** をベースラインとして使用します。サーバーと同じ kubectl マイナーバージョンを優先してください。サポートされるバージョンの差は ±1 マイナーです。古い EKS クラスターに対して、上流の `stable.txt` から最新のマイナーバージョンを無条件にインストールしないでください。

この Bash の例では、AMD64/ARM64 を選択し、インストール前に公式チェックサムを検証します。`curl`、`tar`、`awk`、および `sha256sum` または `shasum` が必要です。`/usr/local/bin` へのインストールには管理者権限が必要です。ダウンロードまたはチェックサムの検証に失敗すると、インストールは停止します。

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

PowerShell では、[kubectl の公式インストール手順](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) に従ってください。この章の AMD64 の例では、[kubectl 1.36.5](https://dl.k8s.io/release/v1.36.5/bin/windows/amd64/kubectl.exe) と同じパスにある `.sha256` ファイルを使用してください。CPU に一致する Windows ZIP と、[eksctl 0.231.0 リリース](https://github.com/eksctl-io/eksctl/releases/tag/v0.231.0) の `eksctl_checksums.txt` を選択してください。

`Get-FileHash -Algorithm SHA256` を公式ハッシュと比較し、不一致の場合は停止してください。検証後、ZIP を展開し、実行可能ファイルのディレクトリを PATH に追加して、`kubectl version --client` と `eksctl version` を確認してください。Bash で PowerShell 構文を実行しないでください。

また、AWS CLI の例で JSON を生成するために `jq` を準備してください。この監査中に、実際のクライアントのダウンロード／インストールまたはログインは実行していません。

### 4. VPC とサブネット

![2 つの Availability Zone にまたがるパブリックサブネット内のロードバランサー、NAT Gateway、プライベートサブネット内のワーカーノードを配置した EKS VPC アーキテクチャ図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

この図は NAT ベースのレイアウトの一例であり、すべてのクラスターにインターネットアクセスが必要であることを示す要件ではありません。

リージョン EKS クラスターには、同じ VPC 内で異なる AZ にある少なくとも 2 つのサブネットが必要です。各クラスターサブネットには EKS 用に少なくとも 6 個の使用可能な IP が必要です。AWS では少なくとも 16 個を推奨しています。ノード、Pod、ロードバランサー、アップグレード用に追加のアドレスを計画してください。VPC DNS ホスト名と DNS 解決を有効にしてください。

すべての EKS クラスターでインターネットアクセスが必須というわけではありません。ノードとワークロードは、NAT／インターネット経路、または必要な VPC エンドポイントとミラーリングされたイメージを通じて、Kubernetes API、イメージ、必要な AWS サービスにアクセスする必要があります。プライベート Kubernetes エンドポイントには、適切な DNS とルーティングを備えた VPC または接続済みネットワークから到達できます。

#### EKS クラスター用 VPC タグ

`kubernetes.io/cluster/<cluster-name>` VPC タグはレガシーのメカニズムであり、現在のすべての EKS 作成に共通して必要なものではありません。ロードバランシングについては、選択したコントローラーのサブネット検出ルールに従ってください。

- パブリックロードバランサー用のサブネット: `kubernetes.io/role/elb=1`
- 内部ロードバランサー用のサブネット: `kubernetes.io/role/internal-elb=1`

タグによってルーティング、セキュリティグループ、または空き IP 容量が構成されることはありません。[VPC／サブネット要件](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) および [インターネットアクセスのないクラスター](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html) を参照してください。

## クイズ

この章で学んだ内容をテストするには、[EKS クラスター作成パート 1 のクイズ](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md) を試してください。
