# Auto Mode 入门

> **支持版本**：EKS Auto Mode GA；示例基线为 EKS 1.36
> **最后更新**：2026 年 9 月 12 日

本章介绍如何创建新集群，以及如何在现有集群上启用 Auto Mode。创建方式任选**一种**；运行全部三种会创建彼此独立且会产生费用的基础设施。仅对计划修改的现有集群使用现有集群一节。

示例使用商业区首尔区域和经审查、预先创建的 IAM 角色。已使用 eksctl 0.229.0、Terraform 1.15.7/AWS provider 6.64.0，以及 CDK 2.269.0/constructs 10.5.0 进行本地验证和合成。**本次审查未创建或迁移任何实际集群**。IAM/SCP 权限、配额、路由、实例可用性和工作负载兼容性仍需结合具体环境验证。这些示例并非经过测试的生产部署。

截至审查日期，EKS 1.36 仍处于标准支持期。Auto Mode 最初支持的最低版本 1.29，并不能证明当前仍符合 EKS 支持资格。运行示例前请检查 AWS 版本日历。`STANDARD` 升级策略允许在标准支持结束后自动升级；它不会停止计费。

## 前提条件与 IAM 角色

请使用临时角色凭证、AWS CLI v2、与 EKS 1.36 兼容的 kubectl、Bash、Python 3 和 jq。请管理员批准以下不同角色，以及调用方的资源配置/PassRole 权限：

| 角色 | 信任关系与权限 |
|------|-----------------------|
| 集群角色 | 对 `sts:AssumeRole` 和 `sts:TagSession` 信任 `eks.amazonaws.com`。当前 AWS 指南推荐使用 `AmazonEKSClusterPolicy`、`AmazonEKSComputePolicy`、`AmazonEKSBlockStoragePolicyV2`、`AmazonEKSLoadBalancingPolicy` 和 `AmazonEKSNetworkingPolicy` |
| Auto Mode 节点角色 | 信任 `ec2.amazonaws.com`；附加 `AmazonEKSWorkerNodeMinimalPolicy` 和 `AmazonEC2ContainerRegistryPullOnly` |
| 工作负载角色 | 为应用配置独立权限，例如通过 EKS Pod Identity 授权；不要把应用权限放进节点角色 |

启用 Auto Mode 时不能替换现有集群角色 ARN；应通过其所属 IaC 工作流更新已批准的策略/信任关系。不要盲目覆盖共享信任策略。以下代码使用经审查的角色，不负责创建它们。更改存储策略前，现有卷可能还需要额外迁移检查。

Auto Mode 提供 Pod Identity agent 功能；仅启用 Auto Mode 并不要求 IAM OIDC provider。如果应用使用 IRSA，请另行配置 OIDC。

### 通用账户与本地环境

请将必需的环境变量设为已批准的真实值。创建新集群时，应选择唯一名称；操作现有集群时，请核实其身份和所有权。在专用 Bash 会话中运行其余命令，并妥善保护生成的目录。

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

## 创建新集群

### 使用已批准私有子网的 eksctl

此示例复用已审查的 VPC 和两个位于不同 AZ 的私有子网。请先设置 `VPC_ID`、`PRIVATE_SUBNET_A` 和 `PRIVATE_SUBNET_B`。确认子网路由表可通过 NAT 或适当的 VPC endpoint 访问所需的外部服务和镜像。`MapPublicIpOnLaunch=false` 本身不能证明子网具备私有路由。

所选私有子网同时也是集群子网。这一点很重要，因为默认 Auto Mode NodeClass 会继承集群子网选择；如果通过通用 eksctl 配置创建的集群使用公共子网，Auto Mode 节点也可能在这些子网中启动。

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

当前 eksctl schema 支持 `autoModeConfig.nodePools`。通过 eksctl 启用 Auto Mode 会协调计算、负载均衡和块存储，并将提供的节点角色用于默认 NodePool。生成 kubeconfig 的操作放在验证一节中。

如果创建失败，请保留配置并检查命名的 CloudFormation stack。超时并不能证明没有创建资源。重试或删除之前，应先厘清资源所有权并处理部分创建的资源。

### Terraform

将下列内容保存为专用目录中的 `main.tf`。此方法会创建包含一个计费 NAT Gateway 的 VPC；这是实验环境中的可用性/成本取舍，并非按 AZ 配置 NAT 冗余。使用前应调整 CIDR 和 AZ，以避免冲突。

示例固定使用 EKS module 21.25.0 和 VPC module 5.21.0。EKS module 要求 AWS provider **6.59 或更高版本**；请保留生成的 dependency lock 文件。创建集群角色时，21.25.0 仍会附加较早的 `AmazonEKSBlockStoragePolicy`，因此示例使用前提条件中审查过的角色。它使用 EKS 默认的 API 数据加密，而不是另行创建客户管理的 KMS key。

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

此 module 的 `compute_config` 输入会协调相应的 EKS 计算、存储和负载均衡资源块。它不同于旧版 module v20 的 `cluster_compute_config` 名称。此处为专用实验显式授予了创建者管理员访问权限；生产环境应定义范围更小、经过审查的 access entry。

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

请在面向已批准账户和 `ap-northeast-2` 区域的 CDK 应用中使用此 stack。将 `ClusterName`、`ClusterRoleArn`、`NodeRoleArn`、`OperatorRoleArn` 和 `ApiClientCidr` 作为 CloudFormation 参数传入。Operator 参数必须是你将用 kubectl 操作时所用、经过审查的 IAM 角色，不能是 STS assumed-role session ARN。

这里使用真正的 **L1 `eks.CfnCluster`**。将原 `eks.Cluster` L2 construct 的 `defaultChild` 强制转换为 `CfnCluster`，不会把其自定义资源变成 `AWS::EKS::Cluster`，也不能可靠配置 Auto Mode。此处明确配置了全部三种 Auto Mode 能力、API 访问和节点角色。Access entry 授予经过审查的实验操作员 Kubernetes 管理员权限；CloudFormation 执行身份的 bootstrap 访问已禁用。生产环境应将此实验级授权替换为适当的 access scope。此 stack 不管理所引用 IAM 角色的生命周期。

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

请从 CDK 应用中实例化 `EksAutoModeStack`，并在 `StackProps.env` 中设置目标账户/区域。获得授权部署前，请审查 `cdk synth` / `cdk diff`。本地审查编译了此 TypeScript 并检查合成后的集群属性，但没有执行 `cdk deploy`。

## 在现有集群上启用 Auto Mode

启用 Auto Mode 与将工作负载迁移到其节点是两个不同操作。开始之前：

- 如果集群由 IaC 管理，请使用所属 Terraform/CDK/eksctl 配置，避免产生非托管漂移。
- 确认现有集群角色具有上述 Auto Mode 权限和 `sts:TagSession` 信任关系。示例会核对其 ARN 是否与已审查的角色一致。
- 根据[所需的迁移最低版本](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)检查已安装 add-on 当前兼容的版本。历史最低版本并不是建议安装的旧版本。
- 启用 API 身份验证前规划 access entry。`CONFIG_MAP` 到 `API_AND_CONFIG_MAP` 是单向迁移；它会保留现有 ConfigMap 路径，同时增加 access entry。
- 为非 Auto 节点保留现有 worker group 和 CoreDNS Deployment。审查受支持的 CNI/网络配置。启用 Auto Mode 不会自动迁移现有 EBS 卷或负载均衡器。

对于由 eksctl 管理的集群，当前命令是 `eksctl update auto-mode-config --config-file <reviewed-config>`。它**不是** `eksctl update cluster --enable-auto-mode`；仅为启用此功能也不应添加 `--drain-all-nodegroups`。

下面的 AWS CLI 替代方式会在同一请求中启用计算、负载均衡和块存储。此方式用于尚未启用 Auto Mode 的集群。它会保存每个 update ID 并等待最终状态，而不是把请求已接受误当作操作已完成：

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

如果更新失败、超时或返回未知状态，请检查私有响应并在重试前协调该操作。启用计算后，默认 NodePool 使用的节点角色不能任意更改；重新设计节点身份时，应遵循文档说明的 NodeClass/access entry 流程。

## AWS Console

完成相同的 IAM、add-on 和访问前提后，打开集群的 **EKS Auto Mode → Manage** 设置，启用 Auto Mode，选择默认 NodePool 和经过审查的节点角色，并监控生成的更新。创建新集群时也有相应选项。Console 中的设置位置可能变化；重要的是核对所需 API 能力和 IAM 角色。

## 验证启用状态

选择的创建方式成功，或现有集群更新完成后：

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

空闲集群可能没有 Auto Mode 节点，直到有符合条件的工作负载需要容量。NodePool Ready 并不代表应用可用。请使用受限的测试工作负载，检查 NodeClaim/节点和应用就绪状态，然后删除该测试工作负载。

Auto Mode 节点将 CoreDNS 作为本地系统服务运行。纯 Auto Mode 迁移可以在工作负载迁移后删除传统 Deployment；**混合 Auto/非 Auto 集群必须保留它**，以供其他节点使用。

## 清理与后续步骤

仅删除所选创建方式拥有的资源；删除前请导出所需数据，并根据保留策略移除应用负载均衡器/PVC。视情况使用带 `--wait` 的 eksctl 删除、经过审查的 Terraform destroy plan，或删除经过审查的 CDK stack。示例引用已有 IAM 角色，eksctl 示例还复用了 VPC；不要把这些共享前提资源误当成示例创建的资源而删除。

启用现有集群的操作不是可随意销毁的实验。工作负载、存储、DNS 和流量迁移经过验证之前，不要删除旧 worker group 或禁用其控制器。操作中断后，节点、卷、负载均衡器、NAT 和控制平面仍可能继续计费；请检查剩余资源，不要依赖固定等待时间。

- [NodePool 配置](./02-nodepool-configuration.md)
- [托管节点组迁移](./09-migration-guide.md)
- [入门测验](../quizzes/eks-auto-mode/01-getting-started-quiz.md)

## 参考资料

- [使用 CLI 创建 Auto Mode 集群与 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)
- [在现有集群上启用 Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [eksctl Auto Mode 配置](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)
- [EKS 支持日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Terraform EKS module v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.25.0)
- [CDK CfnCluster API](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks.CfnCluster.html)
- [通过 EKS access entry 配置 IAM principal 访问](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Auto Mode 网络与 DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [迁移边界](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)

< [上一篇：概览](./README.md) | [目录](./README.md) | [下一篇：NodePool 配置](./02-nodepool-configuration.md) >
