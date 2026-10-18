# Auto Mode の利用開始

> **サポート対象バージョン**: EKS Auto Mode GA。例の基準は EKS 1.36
> **最終更新**: 2026年9月12日

この章では、新しいクラスターの作成と、既存クラスターでの Auto Mode 有効化を説明します。作成方法は**いずれか1つ**を選んでください。3つすべてを実行すると、それぞれ別の課金対象インフラストラクチャが作成されます。既存クラスターの手順は、変更する対象のクラスターに対してのみ使用してください。

例では商用のソウルリージョンと、レビュー済みで事前作成された IAM Role を使います。eksctl 0.229.0、Terraform 1.15.7/AWS Provider 6.64.0、CDK 2.269.0/constructs 10.5.0 を使い、ローカル検証と Synth を行いました。**この監査では、実クラスターの作成も移行も行っていません。** IAM/SCP 権限、Quota、Routing、Instance の提供状況、ワークロード互換性は環境ごとに検証が必要です。これらは本番デプロイのテスト済み手順ではありません。

レビュー日時点で EKS 1.36 は標準サポート期間中です。Auto Mode の当初の機能要件が 1.29 だったことは、現在の EKS サポート対象であることを意味しません。手順を実行する前に AWS のバージョンカレンダーを確認してください。`STANDARD` アップグレードポリシーでは標準サポート終了後に自動アップグレードが許可されますが、課金は停止しません。

## 前提条件と IAM Role

一時的な Role 認証情報、AWS CLI v2、EKS 1.36 と互換性のある kubectl、Bash、Python 3、jq を使用してください。管理者に以下の別個の Role と、呼び出し元のプロビジョニング/PassRole 権限を承認してもらいます。

| Role | 信頼関係と権限 |
|------|-----------------|
| クラスター Role | `eks.amazonaws.com` に `sts:AssumeRole` と `sts:TagSession` を信頼させる。現行 AWS ガイダンスでは `AmazonEKSClusterPolicy`、`AmazonEKSComputePolicy`、`AmazonEKSBlockStoragePolicyV2`、`AmazonEKSLoadBalancingPolicy`、`AmazonEKSNetworkingPolicy` を推奨 |
| Auto Mode ノード Role | `ec2.amazonaws.com` を信頼させ、`AmazonEKSWorkerNodeMinimalPolicy` と `AmazonEC2ContainerRegistryPullOnly` をアタッチ |
| ワークロード Role | EKS Pod Identity などを通じてアプリケーション権限を別途設定。アプリケーション権限をノード Role に含めない |

既存クラスターで Auto Mode を有効にするとき、クラスター Role ARN は置き換えられません。所有する IaC ワークフローで、承認済みの Policy と信頼関係を更新してください。共有信頼 Policy を無条件に上書きしないでください。以下のコードはレビュー済み Role を利用し、作成はしません。ストレージ Policy を変更する前に、既存 Volume の追加移行確認が必要な場合があります。

Auto Mode は Pod Identity Agent の機能を提供するため、Auto Mode の有効化だけなら IAM OIDC Provider は不要です。アプリケーションで IRSA を利用する場合は、OIDC を別途設定してください。

### アカウントとローカル実行環境の共通設定

必要な環境変数に、承認済みの実値を設定してください。新規クラスターでは一意な名前を選び、既存クラスターでは ID と所有者を確認します。以降のコマンドは専用の Bash セッションで実行してください。生成したディレクトリは他者が読めないように保護します。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the approved account ID}"
: "${CLUSTER_NAME:?Set a unique new name, or the approved existing cluster name}"
: "${AUTO_CLUSTER_ROLE_ARN:?Set the reviewed EKS cluster role ARN}"
: "${AUTO_NODE_ROLE_ARN:?Set the reviewed Auto Mode node role ARN}"
: "${API_CLIENT_CIDR:?Set the approved public client IPv4 CIDR}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
test "$AWS_REGION" = ap-northeast-2 || { printf 'This concrete example uses Seoul subnets/AZs; adapt it before using another region.\n' >&2; exit 1; }
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLUSTER_NAME AUTO_CLUSTER_ROLE_ARN AUTO_NODE_ROLE_ARN API_CLIENT_CIDR
python3 - <<'PY'
import ipaddress, os, re
account = os.environ["EXPECTED_ACCOUNT_ID"]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("Invalid account")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", os.environ["CLUSTER_NAME"]):
    raise SystemExit("Invalid cluster name")
for key in ("AUTO_CLUSTER_ROLE_ARN", "AUTO_NODE_ROLE_ARN"):
    if not re.fullmatch(r"arn:aws:iam::" + account + r":role/[A-Za-z0-9+=,.@_/-]+", os.environ[key]):
        raise SystemExit("Role account/ARN mismatch: " + key)
network = ipaddress.ip_network(os.environ["API_CLIENT_CIDR"], strict=True)
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed /24 or narrower IPv4 CIDR")
PY
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Wrong AWS account; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-mode.XXXXXXXX")
export KUBECONFIG="$WORK_DIR/kubeconfig"
printf 'Private evidence/config directory: %s\n' "$WORK_DIR"
```

## 新しいクラスターを作成する

### 承認済みのプライベートサブネットを使った eksctl

この例では、レビュー済み VPC と、異なる AZ にある2つのプライベートサブネットを再利用します。最初に `VPC_ID`、`PRIVATE_SUBNET_A`、`PRIVATE_SUBNET_B` を設定してください。サブネットの Route Table が NAT または適切な Endpoint を通じて、必要な外部 Service/Image にアクセスできることを確認します。`MapPublicIpOnLaunch=false` だけでは、そのサブネットがプライベート経路を持つ証明にはなりません。

選択したプライベートサブネットはクラスターサブネットとしても使われます。既定の Auto Mode NodeClass はクラスターのサブネット選択を引き継ぐため、この点が重要です。クラスターサブネットにパブリックサブネットを指定した一般的な eksctl クラスターでは、Auto Mode ノードもそこに起動する可能性があります。

```bash
# Use approved PRIVATE subnets in the same VPC and at least two AZs.
: "${VPC_ID:?Set the approved VPC ID}"
: "${PRIVATE_SUBNET_A:?Set the first private subnet ID}"
: "${PRIVATE_SUBNET_B:?Set the second private subnet ID in another AZ}"
export VPC_ID
check_account
aws ec2 describe-subnets --region "$AWS_REGION" \
  --subnet-ids "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" > "$WORK_DIR/subnets.json"
python3 - <<'PY'
import json, os
from pathlib import Path
out = Path(os.environ["WORK_DIR"])
subnets = json.loads((out / "subnets.json").read_text())["Subnets"]
if len(subnets) != 2 or len({s["AvailabilityZone"] for s in subnets}) != 2:
    raise SystemExit("Two subnets in distinct AZs are required")
if not all(s["VpcId"] == os.environ["VPC_ID"] and
           s["OwnerId"] == os.environ["EXPECTED_ACCOUNT_ID"] and
           s["State"] == "available" and not s["MapPublicIpOnLaunch"] for s in subnets):
    raise SystemExit("Subnet account/VPC/state/public-IP settings do not match")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": os.environ["CLUSTER_NAME"], "region": os.environ["AWS_REGION"], "version": "1.36"},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "iam": {"serviceRoleARN": os.environ["AUTO_CLUSTER_ROLE_ARN"], "withOIDC": False},
    "autoModeConfig": {"enabled": True, "nodePools": ["general-purpose", "system"],
                       "nodeRoleARN": os.environ["AUTO_NODE_ROLE_ARN"]},
    "vpc": {"id": os.environ["VPC_ID"],
            "controlPlaneSubnetIDs": [s["SubnetId"] for s in subnets],
            "subnets": {"private": {s["AvailabilityZone"]: {"id": s["SubnetId"]} for s in subnets}},
            "clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [os.environ["API_CLIENT_CIDR"]]}
}
(out / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
PY
# REVIEW cluster.json and routes/permissions first. Creates billed EKS resources.
check_account
eksctl create cluster --config-file "$WORK_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

現行の eksctl Schema では `autoModeConfig.nodePools` が有効です。eksctl で Auto Mode を有効にすると、Compute、Load Balancing、Block Storage の各機能が連携して設定され、指定したノード Role が既定 Node Pool で使われます。生成される kubeconfig は検証の節で作成します。

作成に失敗した場合は、名前が示された CloudFormation Stack を確認できるよう、設定を残してください。Timeout はリソースが何も作成されなかった証拠ではありません。再試行または削除の前に、所有関係と部分作成されたリソースを整理してください。

### Terraform

専用ディレクトリに `main.tf` として以下を保存してください。この方法では課金対象の NAT Gateway を1つ作成します。これは検証用の可用性/コスト上の選択であり、AZ ごとに NAT を冗長化する構成ではありません。CIDR と AZ は競合がないよう、利用前に調整してください。

この例は EKS Module 21.25.0 と VPC Module 5.21.0 を固定します。EKS Module は AWS Provider **6.59 以降**が必要です。生成された Dependency Lock File を保持してください。21.25.0 は独自にクラスター Role を作成すると、旧 `AmazonEKSBlockStoragePolicy` をアタッチします。そのためこの例では、前提条件でレビュー済みの Role を渡します。別個の Customer-managed KMS Key は作成せず、EKS の既定 API データ暗号化を利用します。

```hcl
terraform {
  required_version = ">= 1.5.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.59, < 7.0"
    }
  }
}

variable "expected_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Set the intended 12-digit AWS account."
  }
}
variable "cluster_name" { type = string }
variable "auto_cluster_role_arn" { type = string }
variable "auto_node_role_arn" { type = string }
variable "api_client_cidr" {
  type = string
  validation {
    condition = can(cidrnetmask(var.api_client_cidr)) && try(
      tonumber(split("/", var.api_client_cidr)[1]) >= 24, false
    )
    error_message = "Use an approved narrow IPv4 CIDR (/24 through /32)."
  }
}

provider "aws" {
  region              = "ap-northeast-2"
  allowed_account_ids = [var.expected_account_id]
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.21.0"
  name    = "${var.cluster_name}-vpc"
  cidr    = "10.0.0.0/16"

  azs                  = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  private_subnets      = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets       = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true
  public_subnet_tags   = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags  = { "kubernetes.io/role/internal-elb" = "1" }
}

module "eks" {
  source             = "terraform-aws-modules/eks/aws"
  version            = "21.25.0"
  name               = var.cluster_name
  kubernetes_version = "1.36"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets

  endpoint_public_access                   = true
  endpoint_private_access                  = true
  endpoint_public_access_cidrs             = [var.api_client_cidr]
  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true # Dedicated lab creator only.
  upgrade_policy                           = { support_type = "STANDARD" }

  # Reviewed pre-created roles: this module release still attaches the older
  # AmazonEKSBlockStoragePolicy when it creates the cluster role itself.
  create_iam_role      = false
  iam_role_arn         = var.auto_cluster_role_arn
  create_node_iam_role = false
  compute_config = {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
  }
  # EKS default API-data encryption; no separate customer-managed KMS key here.
  create_kms_key    = false
  encryption_config = null
  enable_irsa       = false # Pod Identity does not require a cluster OIDC provider.
  tags              = { Environment = "lab", Terraform = "true" }
}

output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "cluster_name" { value = module.eks.cluster_name }
```

Module の `compute_config` 入力は、対応する EKS Compute、Storage、Load Balancing の各 Resource Block を連携させます。旧 v20 Module の `cluster_compute_config` という名前とは異なります。この専用ラボでは作成者への管理者アクセスを明示しています。本番環境では、より限定されたレビュー済み Access Entry を定義してください。

```bash
python3 - <<'PY'
import json, os
from pathlib import Path
fields = {"expected_account_id": "EXPECTED_ACCOUNT_ID", "cluster_name": "CLUSTER_NAME",
          "auto_cluster_role_arn": "AUTO_CLUSTER_ROLE_ARN", "auto_node_role_arn": "AUTO_NODE_ROLE_ARN",
          "api_client_cidr": "API_CLIENT_CIDR"}
(Path(os.environ["WORK_DIR"]) / "terraform.tfvars.json").write_text(
    json.dumps({key: os.environ[value] for key, value in fields.items()}, indent=2) + "\n")
PY
check_account
terraform init
terraform validate
terraform plan -var-file="$WORK_DIR/terraform.tfvars.json" -out="$WORK_DIR/tfplan"
# REVIEW the saved plan; this applies billed infrastructure changes.
terraform apply "$WORK_DIR/tfplan"
```

### AWS CDK

承認済みアカウントと `ap-northeast-2` を対象とする CDK アプリケーション内で、この Stack を使います。`ClusterName`、`ClusterRoleArn`、`NodeRoleArn`、`OperatorRoleArn`、`ApiClientCidr` を CloudFormation Parameter として渡してください。Operator Parameter には kubectl で使う IAM Role の認証情報を指定します。STS AssumeRole 済みセッションの ARN ではありません。

これは実際の **L1 `eks.CfnCluster`** を使います。元の `eks.Cluster` L2 Construct の `defaultChild` を `CfnCluster` に Cast しても、その Custom Resource が `AWS::EKS::Cluster` に変わるわけではなく、Auto Mode が確実に設定されることもありません。ここでは Auto Mode の3機能、API Access、ノード Role をすべて明示します。Access Entry はレビュー済みのラボ Operator に Kubernetes 管理者権限を付与します。CloudFormation 実行 Identity の Bootstrap Access は無効です。このラボ全体への権限付与は、本番環境に適した Access Scope に置き換えてください。参照される IAM Role のライフサイクルは、この Stack の外部で管理します。

```typescript
import * as cdk from 'aws-cdk-lib/core';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    // Pre-created, reviewed roles; see the IAM prerequisites in this chapter.
    const clusterRole = new cdk.CfnParameter(this, 'ClusterRoleArn', { type: 'String' });
    const nodeRole = new cdk.CfnParameter(this, 'NodeRoleArn', { type: 'String' });
    const operatorRole = new cdk.CfnParameter(this, 'OperatorRoleArn', {
      type: 'String',
      allowedPattern: '^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$',
      constraintDescription: 'The reviewed lab operator IAM role ARN, not an STS session ARN',
    });
    const clientCidr = new cdk.CfnParameter(this, 'ApiClientCidr', {
      type: 'String',
      allowedPattern: '^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/(?:2[4-9]|3[0-2])$',
      constraintDescription: 'An approved narrow IPv4 CIDR (/24 through /32)',
    });
    const clusterName = new cdk.CfnParameter(this, 'ClusterName', { type: 'String' });
    const vpc = new ec2.Vpc(this, 'EksVpc', {
      maxAzs: 3,
      natGateways: 1, // Lab tradeoff: billed, and not per-AZ NAT redundancy.
      subnetConfiguration: [
        { cidrMask: 24, name: 'Public', subnetType: ec2.SubnetType.PUBLIC },
        { cidrMask: 24, name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      ],
    });
    for (const subnet of vpc.publicSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/elb', '1');
    }
    for (const subnet of vpc.privateSubnets) {
      cdk.Tags.of(subnet).add('kubernetes.io/role/internal-elb', '1');
    }
    // An actual L1 AWS::EKS::Cluster, not an L2 defaultChild cast.
    const cluster = new eks.CfnCluster(this, 'EksAutoModeCluster', {
      name: clusterName.valueAsString,
      version: '1.36',
      roleArn: clusterRole.valueAsString,
      accessConfig: {
        authenticationMode: 'API',
        bootstrapClusterCreatorAdminPermissions: false,
      },
      resourcesVpcConfig: {
        subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
        endpointPrivateAccess: true,
        endpointPublicAccess: true,
        publicAccessCidrs: [clientCidr.valueAsString],
      },
      computeConfig: {
        enabled: true,
        nodePools: ['general-purpose', 'system'],
        nodeRoleArn: nodeRole.valueAsString,
      },
      kubernetesNetworkConfig: { elasticLoadBalancing: { enabled: true } },
      storageConfig: { blockStorage: { enabled: true } },
      upgradePolicy: { supportType: 'STANDARD' },
    });
    // CloudFormation's execution role may differ from the interactive operator.
    new eks.CfnAccessEntry(this, 'LabOperatorAccess', {
      clusterName: cluster.ref,
      principalArn: operatorRole.valueAsString,
      type: 'STANDARD',
      accessPolicies: [{
        policyArn: cdk.Fn.sub('arn:${AWS::Partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy'),
        accessScope: { type: 'cluster' }, // Explicit, reviewed admin access for this lab only.
      }],
    });
    new cdk.CfnOutput(this, 'ClusterNameOutput', { value: cluster.ref });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.attrEndpoint });
  }
}
```

CDK アプリケーションから、`StackProps.env` に対象アカウント/リージョンを指定して `EksAutoModeStack` を作成してください。承認済みのデプロイ前に `cdk synth`/`cdk diff` をレビューします。ローカル監査では TypeScript をコンパイルし、Synth されたクラスター設定を確認しましたが、`cdk deploy` は実行していません。

## 既存クラスターで Auto Mode を有効にする

Auto Mode の有効化と、そのノードへのワークロード移行は別々の操作です。実施前に以下を確認してください。

- IaC がクラスターを管理している場合は、所有者の Terraform/CDK/eksctl 設定を使い、管理外の Drift を避けてください。
- 既存クラスター Role に、上記の Auto Mode 権限と `sts:TagSession` の信頼設定があることを確認します。サンプルはレビューした Role と ARN が一致するか検証します。
- インストール済み Add-on の現行互換バージョンを[必要な移行最小バージョン](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)と照合してください。歴史的な最小バージョンは、その古い Build のインストール推奨ではありません。
- API 認証を有効にする前に Access Entry を計画します。`CONFIG_MAP` から `API_AND_CONFIG_MAP` への移行は一方向です。既存の ConfigMap 経路を維持したまま Access Entry を追加します。
- Auto Mode 対象外ノード用に、既存の Worker Group と CoreDNS Deployment を保持します。対応する CNI/ネットワーク設定を確認してください。Auto Mode を有効にしても、既存 EBS Volume や Load Balancer は自動移行されません。

eksctl 管理クラスターで使う現行コマンドは `eksctl update auto-mode-config --config-file <reviewed-config>` です。`eksctl update cluster --enable-auto-mode` ではありません。また、機能を有効にするだけのために `--drain-all-nodegroups` を追加しないでください。

以下の AWS CLI 代替手順は、Compute、Load Balancing、Block Storage を同じリクエストで有効にします。すでに Auto Mode が有効なクラスターには使用しません。リクエストが受理されただけで完了したと判断せず、各 Update ID を記録し、終端結果まで待ちます。

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --output json > "$WORK_DIR/before.json"
jq -e --arg role "$AUTO_CLUSTER_ROLE_ARN" '
  .cluster.status == "ACTIVE" and .cluster.roleArn == $role and
  .cluster.computeConfig.enabled != true
' "$WORK_DIR/before.json" >/dev/null

wait_update() {
  local id=$1 status
  for attempt in $(seq 1 120); do
    aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --update-id "$id" --output json > "$WORK_DIR/update-$id.json" || return
    status=$(jq -er '.update.status' "$WORK_DIR/update-$id.json") || return
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled) printf 'Update %s: %s; inspect the private response.\n' "$id" "$status" >&2; return 1 ;;
      InProgress) sleep 15 ;;
      *) printf 'Unknown update state; stop.\n' >&2; return 1 ;;
    esac
  done
  printf 'Update wait timed out; do not assume completion or resubmit blindly.\n' >&2
  return 1
}
# One-way authentication migration; review existing access before running.
mode=$(jq -er '.cluster.accessConfig.authenticationMode' "$WORK_DIR/before.json")
case "$mode" in
  CONFIG_MAP)
    auth_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
      --access-config authenticationMode=API_AND_CONFIG_MAP --query update.id --output text)
    wait_update "$auth_id"
    ;;
  API|API_AND_CONFIG_MAP) ;;
  *) printf 'Unknown authentication mode; stop.\n' >&2; exit 1 ;;
esac
compute=$(jq -nc --arg role "$AUTO_NODE_ROLE_ARN" \
  '{enabled:true,nodePools:["general-purpose","system"],nodeRoleArn:$role}')
# MUTATION: compute, load balancing and block storage change together.
check_account
update_id=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --compute-config "$compute" \
  --kubernetes-network-config '{"elasticLoadBalancing":{"enabled":true}}' \
  --storage-config '{"blockStorage":{"enabled":true}}' \
  --query update.id --output text)
wait_update "$update_id"
```

Update が失敗・Timeout した場合や状態が不明な場合は、非公開の応答を確認し、再試行前に操作の状態を整理してください。既定 Node Pool で使われる Node Role は、Compute 有効化後に任意の Role へ変更できません。ノード Identity を再設計するときは、文書化された NodeClass/Access Entry 手順に従ってください。

## AWS Console

同じ IAM、Add-on、Access の前提条件を満たした後、クラスターの **EKS Auto Mode → Manage** 設定を開き、Auto Mode を有効化して既定 Node Pool とレビュー済み Node Role を選び、生成される Update を監視します。新規クラスターの作成時にも対応する設定があります。Console 上の配置は変わる場合があります。重要なのは、必要な API 機能と IAM Role を確認することです。

## 有効化を検証する

選択した作成方法が成功した後、または既存クラスターの Update が完了した後に、以下を実行します。

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{status:status,compute:computeConfig,network:kubernetesNetworkConfig,storage:storageConfig,access:accessConfig}' \
  --output json > "$WORK_DIR/after.json"
jq -e '.status == "ACTIVE" and .compute.enabled == true and
       .network.elasticLoadBalancing.enabled == true and .storage.blockStorage.enabled == true' \
  "$WORK_DIR/after.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodepools,nodeclasses
kubectl --context "$CLUSTER_NAME" wait nodepool/general-purpose nodepool/system \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -L eks.amazonaws.com/compute-type
```

アイドル状態のクラスターでは、Auto Mode NodePool が Ready でも、対象ワークロードが容量を必要とするまで Auto Mode Node が存在しない場合があります。NodePool の Ready はアプリケーション可用性のテストではありません。制約を設けたテストワークロードを使い、NodeClaim/Node とアプリケーションの Ready 状態を確認してから、テストワークロードを削除してください。

Auto Mode Node は CoreDNS をローカルの System Service として実行します。Auto Mode のみへ完全移行した場合は、ワークロード移行後に従来の Deployment を削除できます。**Auto Mode とそれ以外のノードが混在するクラスターでは、従来の Deployment を維持してください。**

## クリーンアップと次の手順

必要なデータを Export し、保持ポリシーに従ってアプリケーションの Load Balancer/PVC を削除してから、選択した作成方法が所有するリソースだけを削除してください。状況に応じて `--wait` を指定した eksctl 削除、レビュー済み Terraform Destroy Plan、またはレビュー済み CDK Stack の削除を使います。これらの例は既存 IAM Role を参照し、eksctl の例は既存 VPC も再利用します。例が作成した共有前提条件のように扱って削除しないでください。

既存クラスターでの有効化は、使い捨てクラスターのラボではありません。ワークロード、ストレージ、DNS、通信経路の移行を検証するまでは、古い Worker Group を削除したり、Controller を無効化したりしないでください。中断した操作の後も、Node、Volume、Load Balancer、NAT、Control Plane に課金されることがあります。固定時間の Sleep だけに頼らず、残存リソースを確認してください。

- [NodePool の設定](./02-nodepool-configuration.md)
- [Managed Node Group の移行](./09-migration-guide.md)
- [利用開始クイズ](../quizzes/eks-auto-mode/01-getting-started-quiz.md)

## 参考資料

- [Auto Mode の CLI 作成手順と IAM Role](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)
- [既存クラスターで Auto Mode を有効にする](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [eksctl Auto Mode 設定](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)
- [EKS サポートカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Terraform EKS Module v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.25.0)
- [CDK CfnCluster API](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks.CfnCluster.html)
- [EKS Access Entry による IAM Principal Access](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Auto Mode のネットワークと DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [移行の境界](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)

< [前へ: 概要](./README.md) | [目次](./README.md) | [次へ: NodePool の設定](./02-nodepool-configuration.md) >
