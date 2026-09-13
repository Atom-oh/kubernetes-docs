# Auto Mode 시작하기

> **지원 버전**: EKS Auto Mode GA; 예제 기준 EKS 1.36
> **마지막 업데이트**: 2026년 9월 12일

새 클러스터 생성과 기존 클러스터의 Auto Mode 활성화를 다룹니다. 생성 방법은 **하나만** 선택하세요. 세 방법을 모두 실행하면 각각 과금되는 인프라가 만들어집니다. 기존 클러스터 절차는 의도한 대상 클러스터에만 적용합니다.

예제는 상용 서울 리전과 사전에 생성·검토한 IAM 역할을 사용합니다. eksctl 0.229.0, Terraform 1.15.7/AWS provider 6.64.0, CDK 2.269.0/constructs 10.5.0으로 로컬 검증과 합성을 수행했습니다. **이번 감사에서 실제 클러스터 생성이나 마이그레이션은 실행하지 않았습니다.** IAM/SCP 권한, 할당량, 라우팅, 인스턴스 가용성과 워크로드 호환성은 환경별 검증이 필요합니다. 프로덕션 실행을 검증한 배포 예제가 아닙니다.

검토일에 EKS 1.36은 표준 지원 대상입니다. 초기 Auto Mode 기능 지원 하한인 1.29가 현재 EKS 지원 여부를 보장하지는 않습니다. 실행 전에 AWS 버전 일정을 확인하세요. `STANDARD` 업그레이드 정책은 표준 지원 종료 후 자동 업그레이드를 허용하며 과금을 중지하지 않습니다.

## 사전 요구 사항과 IAM 역할

임시 역할 자격 증명, AWS CLI v2, EKS 1.36과 호환되는 kubectl, Bash, Python 3, jq를 준비합니다. 관리자에게 아래의 서로 다른 역할과 호출자의 프로비저닝/PassRole 권한을 검토받으세요.

| 역할 | 신뢰 관계와 권한 |
|------|-----------------|
| 클러스터 역할 | `eks.amazonaws.com`에 `sts:AssumeRole`과 `sts:TagSession`을 허용합니다. 현재 AWS 권장 정책은 `AmazonEKSClusterPolicy`, `AmazonEKSComputePolicy`, `AmazonEKSBlockStoragePolicyV2`, `AmazonEKSLoadBalancingPolicy`, `AmazonEKSNetworkingPolicy`입니다 |
| Auto Mode 노드 역할 | `ec2.amazonaws.com`을 신뢰하며 `AmazonEKSWorkerNodeMinimalPolicy`와 `AmazonEC2ContainerRegistryPullOnly`를 연결합니다 |
| 워크로드 역할 | EKS Pod Identity 등으로 애플리케이션 권한을 별도로 부여합니다. 노드 역할에 애플리케이션 권한을 넣지 않습니다 |

기존 클러스터를 Auto Mode로 전환할 때 클러스터 역할 ARN 자체는 교체할 수 없습니다. 그 역할을 관리하는 IaC 절차로 승인된 정책·신뢰 관계를 갱신하세요. 공유 역할의 신뢰 정책을 무작정 덮어쓰지 마세요. 아래 코드는 검토된 역할을 참조하며 생성하지 않습니다. 기존 볼륨이 있다면 스토리지 정책을 바꾸기 전에 추가 마이그레이션 검토가 필요할 수 있습니다.

Auto Mode는 Pod Identity agent 기능을 제공합니다. Auto Mode 활성화만을 위해 IAM OIDC provider를 만들 필요는 없습니다. 애플리케이션이 IRSA를 사용한다면 OIDC를 별도로 구성하세요.

### 공통 계정과 로컬 컨텍스트

필수 환경 변수를 승인된 실제 값으로 설정합니다. 새 클러스터에는 고유한 이름을 사용하고, 기존 클러스터에는 식별 정보와 소유권을 확인합니다. 이후 명령도 이 전용 Bash 세션에서 실행하고 생성된 디렉터리를 비공개로 보관하세요.

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

## 새 클러스터 생성

### 승인된 프라이빗 서브넷을 사용하는 eksctl

이 예제는 검토된 VPC와 서로 다른 AZ의 프라이빗 서브넷 2개를 재사용합니다. 먼저 `VPC_ID`, `PRIVATE_SUBNET_A`, `PRIVATE_SUBNET_B`를 설정하세요. 서브넷 라우팅 테이블이 NAT 또는 적절한 엔드포인트를 통해 필요한 서비스·이미지 접근을 제공하는지 확인합니다. `MapPublicIpOnLaunch=false`만으로 프라이빗 라우팅이 입증되지는 않습니다.

선택한 프라이빗 서브넷을 클러스터 서브넷으로도 사용합니다. 기본 Auto Mode NodeClass가 클러스터 서브넷 선택을 상속하기 때문입니다. 퍼블릭 클러스터 서브넷을 가진 일반적인 eksctl 클러스터에서는 Auto Mode 노드도 해당 서브넷에 생성될 수 있습니다.

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

현재 eksctl 스키마에서 `autoModeConfig.nodePools`는 유효합니다. eksctl은 Auto Mode 활성화 시 compute, load balancing, block storage를 함께 구성하며, 기본 풀에는 제공한 노드 역할을 사용합니다. kubeconfig는 뒤의 검증 절차에서 생성합니다.

생성이 실패하면 구성을 보관하고 해당 이름의 CloudFormation 스택을 확인하세요. timeout이 리소스 미생성을 뜻하지 않습니다. 재시도나 삭제 전에 소유권과 부분 생성 리소스를 확인합니다.

### Terraform

다음 내용을 전용 디렉터리의 `main.tf`로 저장합니다. 이 방법은 VPC와 과금되는 NAT Gateway 하나를 만듭니다. 이는 실습의 가용성·비용 선택이며 AZ별 NAT 이중화가 아닙니다. CIDR과 AZ를 검토해 충돌을 방지하세요.

EKS 모듈 21.25.0과 VPC 모듈 5.21.0을 고정합니다. EKS 모듈에는 AWS provider **6.59 이상**이 필요하며 생성된 의존성 lock 파일을 보관해야 합니다. 21.25.0은 클러스터 역할을 직접 만들 때 이전 `AmazonEKSBlockStoragePolicy`를 연결하므로 이 예제는 사전 요구 사항의 검토된 역할을 제공합니다. 별도의 고객 관리 KMS 키를 생성하지 않고 EKS 기본 API 데이터 암호화를 사용합니다.

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

모듈의 `compute_config` 입력은 대응하는 EKS compute·storage·load-balancing 리소스 블록을 함께 구성합니다. 모듈 v20의 이전 `cluster_compute_config` 이름과 다릅니다. 전용 실습을 위해 생성자의 관리자 접근을 명시했습니다. 프로덕션에서는 필요한 범위로 검토한 access entry를 정의하세요.

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

승인된 계정과 `ap-northeast-2`를 대상으로 하는 CDK 애플리케이션에서 사용합니다. CloudFormation 파라미터 `ClusterName`, `ClusterRoleArn`, `NodeRoleArn`, `OperatorRoleArn`, `ApiClientCidr`를 지정하세요. Operator 파라미터에는 kubectl에 사용할 자격 증명의 검토된 IAM 역할 ARN을 입력합니다. STS assumed-role 세션 ARN을 사용하지 않습니다.

실제 **L1 `eks.CfnCluster`**를 사용합니다. 기존 `eks.Cluster` L2의 `defaultChild`를 `CfnCluster`로 형 변환해도 해당 custom resource가 `AWS::EKS::Cluster`로 바뀌거나 Auto Mode가 올바르게 설정되는 것은 아닙니다. 여기서는 세 Auto Mode 기능, API 접근과 노드 역할을 명시합니다. Access entry로 검토된 실습 운영자에게 Kubernetes 관리자 접근을 부여하며, CloudFormation 실행 주체의 bootstrap 접근은 비활성화합니다. 프로덕션에서는 이 실습용 클러스터 전체 권한을 적절한 접근 범위로 대체하세요. 참조한 IAM 역할은 이 스택의 수명 주기에 포함되지 않습니다.

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

CDK 앱에서 `EksAutoModeStack`을 생성하고 `StackProps.env`에 대상 계정·리전을 지정합니다. 승인된 배포 전에 `cdk synth`와 `cdk diff`를 검토하세요. 로컬 감사에서는 TypeScript 컴파일과 합성된 클러스터 속성을 확인했으며 `cdk deploy`는 실행하지 않았습니다.

## 기존 클러스터에서 Auto Mode 활성화

Auto Mode 활성화와 워크로드 이동은 별개의 작업입니다. 먼저 다음 사항을 확인하세요.

- Terraform/CDK/eksctl 등 IaC로 관리하는 클러스터라면 해당 구성을 갱신해 비관리 변경을 피합니다.
- 기존 클러스터 역할에 앞에서 설명한 Auto Mode 권한과 `sts:TagSession` 신뢰 관계가 있어야 합니다. 예제는 그 ARN이 검토한 역할과 같은지 확인합니다.
- 설치된 add-on의 현재 호환 버전과 [마이그레이션 최소 요구 버전](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)을 확인합니다. 과거 최소 버전이 그 오래된 빌드를 새로 설치하라는 권고는 아닙니다.
- API 인증 활성화 전에 access entry 전환을 계획합니다. `CONFIG_MAP`에서 `API_AND_CONFIG_MAP`으로의 변경은 단방향이며, 기존 ConfigMap 경로를 유지하면서 access entry를 추가합니다.
- 기존 워커 그룹과 non-Auto 노드용 CoreDNS Deployment를 유지합니다. 지원되는 CNI·네트워크 구성을 검토하세요. Auto Mode 활성화만으로 기존 EBS 볼륨이나 로드 밸런서가 이전되지는 않습니다.

eksctl 관리 클러스터의 현재 명령은 `eksctl update auto-mode-config --config-file <reviewed-config>`입니다. `eksctl update cluster --enable-auto-mode`가 아닙니다. 기능 활성화만을 위해 `--drain-all-nodegroups`를 추가하지 마세요.

아래 AWS CLI 대안은 같은 요청에서 compute, load balancing과 block storage를 활성화합니다. 아직 Auto Mode를 활성화하지 않은 클러스터를 대상으로 합니다. 요청 수락을 완료로 간주하지 않고 update ID를 보관해 최종 결과를 기다립니다.

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

업데이트 실패·timeout·알 수 없는 상태가 발생하면 비공개 응답을 확인하고 작업 상태를 정리한 뒤 재시도하세요. 기본 풀의 노드 역할은 compute 활성화 후 임의로 바꿀 수 없습니다. 노드 ID 구성을 바꾸려면 문서화된 NodeClass/access-entry 절차를 따릅니다.

## AWS 콘솔

동일한 IAM, add-on과 접근 사전 요구 사항을 확인한 뒤 클러스터의 **EKS Auto Mode → Manage**에서 기능을 활성화하고 기본 풀과 검토된 노드 역할을 선택합니다. 업데이트 결과를 확인하세요. 새 클러스터 생성 화면에서도 대응하는 설정을 제공합니다. 콘솔 배치는 바뀔 수 있으며, 필수 API 기능과 IAM 역할 확인이 핵심입니다.

## 활성화 검증

선택한 생성 방법이 성공하거나 기존 클러스터 업데이트가 완료된 뒤 실행합니다.

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

유휴 클러스터는 적합한 워크로드에 용량이 필요해질 때까지 Auto Mode 노드가 없을 수 있습니다. NodePool readiness가 애플리케이션 가용성 검증을 대신하지는 않습니다. 제약을 지정한 테스트 워크로드로 NodeClaim·노드·애플리케이션 readiness를 확인한 뒤 테스트 워크로드를 제거하세요.

Auto Mode 노드는 CoreDNS를 로컬 시스템 서비스로 실행합니다. 순수 Auto Mode로 워크로드를 옮긴 뒤에는 기존 Deployment를 제거할 수 있지만, **Auto/non-Auto 혼합 클러스터에서는 다른 노드를 위해 유지해야 합니다.**

## 정리와 다음 단계

필요한 데이터를 내보내고 보존 정책에 따라 애플리케이션 로드 밸런서/PVC를 정리한 뒤, 선택한 생성 방법이 소유한 리소스만 삭제합니다. 상황에 맞게 `--wait`를 포함한 eksctl 삭제, 검토한 Terraform destroy plan 또는 검토한 CDK 스택 삭제를 사용하세요. 예제는 기존 IAM 역할을 참조하며 eksctl 예제는 VPC도 재사용합니다. 예제가 생성하지 않은 공유 사전 요구 리소스를 함께 삭제하지 마세요.

기존 클러스터의 기능 활성화는 일회용 클러스터 실습이 아닙니다. 워크로드, 스토리지, DNS와 트래픽 이전을 검증하기 전에 기존 워커 그룹이나 컨트롤러를 제거하지 마세요. 작업이 중단돼도 노드, 볼륨, 로드 밸런서, NAT와 컨트롤 플레인 비용이 계속 발생할 수 있습니다. 고정 sleep에 의존하지 말고 잔여 리소스를 확인합니다.

- [NodePool 구성](./02-nodepool-configuration.md)
- [관리형 노드 그룹 마이그레이션](./09-migration-guide.md)
- [시작하기 퀴즈](../quizzes/eks-auto-mode/01-getting-started-quiz.md)

## 참고 자료

- [Auto Mode CLI creation and IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)
- [Enable Auto Mode on an existing cluster](https://docs.aws.amazon.com/eks/latest/userguide/auto-enable-existing.html)
- [eksctl Auto Mode configuration](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)
- [EKS support calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Terraform EKS module v21.25.0](https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.25.0)
- [CDK CfnCluster API](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks.CfnCluster.html)
- [IAM principal access through EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Auto Mode networking and DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [Migration boundaries](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)

< [이전: 목차](./README.md) | [목차](./README.md) | [다음: NodePool 구성](./02-nodepool-configuration.md) >
