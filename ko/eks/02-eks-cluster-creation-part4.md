# EKS 클러스터 생성 - Part 4: Terraform을 사용한 클러스터 생성

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33
> **마지막 업데이트**: 2026년 2월 19일

## 프로덕션 Terraform 프로젝트 구조

Terraform은 인프라를 코드로 정의하고, 프로비저닝하며, 관리할 수 있는 도구로 EKS 클러스터를 반복 가능하고 버전 관리되는 방식으로 배포할 수 있습니다. 이 가이드에서는 **AWS 프로바이더 ~> 6.0**과 커뮤니티 **EKS 모듈 ~> 21.0**을 사용하며, Auto Mode, Hybrid Nodes, Pod Identity, API 기반 Access Entry 등 최신 EKS 기능을 지원합니다.

프로덕션 환경에서 단일 Terraform 디렉토리에 하나의 상태 파일을 사용하면 문제가 발생합니다. VPC 변경이 실수로 클러스터를 삭제할 수 있고, 프로젝트가 커질수록 `terraform plan`이 느려지며, 서로 다른 팀이 독립적으로 작업할 수 없습니다. **멀티 레이어 아키텍처**는 변경 빈도와 소유권에 따라 인프라를 별도의 상태 파일로 분리하여 이러한 문제를 해결합니다.

### 3-레이어 아키텍처

```
eks-terraform/
├── 01-network/                   # 레이어 1: VPC 및 네트워킹
│   ├── providers.tf
│   ├── backend.tf                # S3 키: eks/network/terraform.tfstate
│   ├── variables.tf
│   ├── main.tf                   # VPC 모듈
│   └── outputs.tf                # vpc_id, subnet_ids → 원격 상태
├── 02-cluster/                   # 레이어 2: EKS 클러스터 및 노드 그룹
│   ├── providers.tf
│   ├── backend.tf                # S3 키: eks/cluster/terraform.tfstate
│   ├── data.tf                   # terraform_remote_state → 01-network
│   ├── variables.tf
│   ├── main.tf                   # EKS 모듈, 노드 그룹, 코어 애드온
│   └── outputs.tf                # cluster_name, endpoint → 원격 상태
└── 03-platform/                  # 레이어 3: 애드온, RBAC, Pod Identity
    ├── providers.tf
    ├── backend.tf                # S3 키: eks/platform/terraform.tfstate
    ├── data.tf                   # terraform_remote_state → 01-network, 02-cluster
    ├── variables.tf
    ├── addons.tf                 # EBS CSI 드라이버, 추가 애드온
    ├── pod-identity.tf           # Pod Identity 연결
    └── access-entries.tf         # 개발자/뷰어 액세스 엔트리
```

### 레이어를 분리하는 이유

| 레이어 | 변경 빈도 | 소유 팀 | 영향 범위 |
|--------|----------|---------|----------|
| 01-network | 드물게 | 인프라 팀 | VPC, 서브넷만 |
| 02-cluster | 월간 | 플랫폼 팀 | EKS 클러스터, 노드 |
| 03-platform | 주간 | 플랫폼 / 앱 팀 | 애드온, RBAC, Pod Identity |

각 레이어는 자체 S3 상태 파일을 가지며 독립적으로 plan/apply 할 수 있습니다. `03-platform`에서 애드온을 변경해도 VPC나 클러스터 자체에 영향을 주지 않습니다.

### 공유 S3 백엔드

모든 레이어는 DynamoDB 잠금이 있는 단일 S3 버킷을 공유하지만, 각 레이어는 **서로 다른 상태 키**에 기록합니다:

```hcl
# 예시: 01-network/backend.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "eks/network/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

레이어 간 참조는 `terraform_remote_state` 데이터 소스를 통해 이루어지며, 이는 다른 레이어의 상태 파일에서 출력을 읽어 Terraform 코드 자체에 대한 의존성 없이 연결합니다.

---

## 레이어 1: 네트워크 (01-network)

이 레이어는 VPC, 서브넷, NAT 게이트웨이 및 모든 네트워킹 전제 조건을 프로비저닝합니다. 변경이 드물며 일반적으로 인프라 팀이 소유합니다.

### 01-network/providers.tf

```hcl
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}
```

### 01-network/backend.tf

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "eks/network/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

### 01-network/variables.tf

```hcl
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "my-eks-cluster"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
}

variable "private_subnets" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

### 01-network/main.tf

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = var.tags
}
```

> **참고**: EKS 모듈 ~> 21.0과 AWS Load Balancer Controller를 사용할 때 서브넷에 `kubernetes.io/cluster/<cluster-name>` 태그는 더 이상 필요하지 않습니다. `kubernetes.io/role/elb` 및 `kubernetes.io/role/internal-elb` 태그만으로 서브넷 검색이 가능합니다.

### 01-network/outputs.tf

```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}
```

---

## 레이어 2: EKS 클러스터 (02-cluster)

이 레이어는 EKS 클러스터, 관리형 노드 그룹, 코어 애드온을 프로비저닝합니다. `terraform_remote_state`를 통해 레이어 1의 네트워크 정보를 읽어옵니다.

### 02-cluster/providers.tf

```hcl
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}
```

### 02-cluster/backend.tf

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "eks/cluster/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

### 02-cluster/data.tf

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "my-terraform-state"
    key    = "eks/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```

### 02-cluster/variables.tf

```hcl
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "my-eks-cluster"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.33"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

### 02-cluster/main.tf

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  # 클러스터 엔드포인트 접근 설정
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  # API 기반 인증 사용 (aws-auth ConfigMap 대체)
  authentication_mode = "API"

  # Terraform 호출자에게 클러스터 관리자 권한 부여
  enable_cluster_creator_admin_permissions = true

  # EKS 애드온 (코어만 — 추가 애드온은 03-platform에서 관리)
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    vpc-cni = {
      most_recent    = true
      before_compute = true
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
        }
      })
    }
    kube-proxy = {
      most_recent = true
    }
    eks-pod-identity-agent = {
      most_recent    = true
      before_compute = true
    }
  }

  # 관리형 노드 그룹
  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = ["m5.large"]

      min_size     = 2
      max_size     = 5
      desired_size = 2

      disk_size = 50
    }

    spot = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = ["m5.large", "m5a.large", "m5d.large"]
      capacity_type  = "SPOT"

      min_size     = 0
      max_size     = 5
      desired_size = 1

      disk_size = 50
    }
  }

  # CloudWatch 로깅
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = var.tags
}
```

### 02-cluster/outputs.tf

```hcl
output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data for the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN for the EKS cluster"
  value       = module.eks.oidc_provider_arn
}

output "region" {
  description = "AWS region"
  value       = var.region
}
```

---

## 레이어 3: 플랫폼 구성 (03-platform)

이 레이어는 코어 세트 이외의 애드온, Pod Identity 연결, 액세스 엔트리를 관리합니다. 가장 자주 변경되며 클러스터나 네트워크에 영향을 주지 않고 독립적으로 적용할 수 있습니다.

### 03-platform/providers.tf

```hcl
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}
```

### 03-platform/backend.tf

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "eks/platform/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
```

### 03-platform/data.tf

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "my-terraform-state"
    key    = "eks/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

data "terraform_remote_state" "cluster" {
  backend = "s3"
  config = {
    bucket = "my-terraform-state"
    key    = "eks/cluster/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```

### 03-platform/variables.tf

```hcl
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "my-eks-cluster"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

### 03-platform/addons.tf

```hcl
# Pod Identity를 사용하는 EBS CSI 드라이버
resource "aws_iam_role" "ebs_csi" {
  name = "${var.cluster_name}-ebs-csi"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name   = "aws-ebs-csi-driver"

  pod_identity_association {
    role_arn        = aws_iam_role.ebs_csi.arn
    service_account = "ebs-csi-controller-sa"
  }

  tags = var.tags
}
```

### 03-platform/pod-identity.tf

```hcl
# 예제: 애플리케이션 파드의 S3 접근
resource "aws_iam_role" "app_s3_access" {
  name = "${var.cluster_name}-app-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "app_s3_access" {
  role       = aws_iam_role.app_s3_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# IAM 역할을 Kubernetes 서비스 어카운트와 연결
resource "aws_eks_pod_identity_association" "app_s3_access" {
  cluster_name    = data.terraform_remote_state.cluster.outputs.cluster_name
  namespace       = "default"
  service_account = "app-sa"
  role_arn        = aws_iam_role.app_s3_access.arn
}
```

### 03-platform/access-entries.tf

```hcl
resource "aws_eks_access_entry" "admin" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/AdminRole"
}

resource "aws_eks_access_policy_association" "admin" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/AdminRole"
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
}

# 네임스페이스 범위 접근 권한의 개발자
resource "aws_eks_access_entry" "developer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/DevRole"
}

resource "aws_eks_access_policy_association" "developer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/DevRole"
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  access_scope {
    type       = "namespace"
    namespaces = ["app-dev", "app-staging"]
  }
}

# 읽기 전용 접근
resource "aws_eks_access_entry" "viewer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/ViewerRole"
}

resource "aws_eks_access_policy_association" "viewer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = "arn:aws:iam::123456789012:role/ViewerRole"
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }
}
```

---

## EKS Pod Identity 구성

EKS Pod Identity는 Kubernetes 워크로드에 AWS 권한을 부여하는 권장 방식입니다. IAM Roles for Service Accounts(IRSA)를 대체하며 OIDC 프로바이더가 필요하지 않습니다.

### Pod Identity 동작 방식

1. `eks-pod-identity-agent` 애드온이 모든 노드에서 DaemonSet으로 실행됩니다 (레이어 2에서 설치).
2. Pod Identity 트러스트 정책이 포함된 IAM 역할이 생성됩니다 (레이어 3에서 생성).
3. `aws_eks_pod_identity_association`을 통해 IAM 역할이 Kubernetes 서비스 어카운트와 연결됩니다.
4. 해당 서비스 어카운트를 사용하는 파드는 자동으로 임시 AWS 자격 증명을 받습니다.

위의 `03-platform/pod-identity.tf`에 표시된 Pod Identity 리소스가 이 패턴을 따릅니다. IAM 역할의 트러스트 정책은 `pods.eks.amazonaws.com`을 보안 주체로 사용하며, `sts:TagSession`은 클러스터, 네임스페이스, 서비스 어카운트 메타데이터를 사용한 자동 세션 태깅을 활성화합니다.

### Pod Identity vs IRSA 비교

| 기능 | Pod Identity | IRSA |
|------|-------------|------|
| OIDC 프로바이더 필요 | 아니오 | 예 |
| 크로스 어카운트 지원 | `sts:TagSession`으로 내장 지원 | 어카운트별 OIDC 트러스트 필요 |
| 설정 복잡도 | 낮음 — 단일 연결 | 보통 — OIDC, 역할, 어노테이션 |
| 세션 태그 | 자동 (클러스터, 네임스페이스, SA) | 지원하지 않음 |
| 재사용성 | 동일 역할을 여러 클러스터에서 사용 | 클러스터 OIDC당 하나의 역할 |

> **권장 사항**: 모든 새 워크로드에는 Pod Identity를 사용하세요. IRSA는 하위 호환성을 위해 계속 지원됩니다.

---

## EKS Auto Mode 클러스터

EKS Auto Mode는 노드 프로비저닝, 스케일링, OS 관리를 AWS에 완전히 위임합니다. 관리형 노드 그룹을 정의할 필요가 없으며 EKS가 자동으로 컴퓨팅을 프로비저닝하고 관리합니다. Auto Mode를 사용할 때는 표준 `02-cluster/main.tf`를 다음 변형으로 대체합니다:

```hcl
# 02-cluster/main.tf (Auto Mode 변형)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  # Auto Mode 활성화
  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # Auto Mode가 이 애드온을 관리하므로 자체 관리 애드온 부트스트랩 비활성화
  bootstrap_self_managed_addons = false

  tags = var.tags
}
```

### 핵심 사항

- **`cluster_compute_config.enabled = true`**로 Auto Mode를 활성화합니다.
- **`node_pools`**는 활성화할 내장 노드 풀을 지정합니다 (`general-purpose`, `system`).
- **`bootstrap_self_managed_addons = false`**로 충돌을 방지합니다 — Auto Mode가 코어 애드온(CoreDNS, kube-proxy, VPC CNI)을 자동으로 관리합니다.
- Auto Mode 사용 시 `eks_managed_node_groups`를 정의하지 **않습니다**.
- Auto Mode는 노드 풀에서 EC2 인스턴스를 프로비저닝하고 OS 패치, 스케일링, 라이프사이클을 처리합니다.

---

## EKS Hybrid Nodes 구성

EKS Hybrid Nodes를 사용하면 온프레미스 또는 엣지 서버를 EKS 클러스터의 워커 노드로 참여시킬 수 있으며, EKS 컨트롤 플레인은 AWS에 유지됩니다. Hybrid Nodes를 사용할 때는 표준 `02-cluster/main.tf`를 다음 변형으로 대체합니다:

```hcl
# 02-cluster/main.tf (Hybrid Nodes 변형)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  # Hybrid Nodes 네트워크 구성
  remote_network_config = {
    remote_node_networks = [
      {
        cidrs = ["172.16.0.0/16"]
      }
    ]
    remote_pod_networks = [
      {
        cidrs = ["192.168.0.0/16"]
      }
    ]
  }

  # Hybrid 노드용 액세스 엔트리
  access_entries = {
    hybrid_nodes = {
      principal_arn = aws_iam_role.hybrid_node_role.arn
      type          = "HYBRID_LINUX"
    }
  }

  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
  }

  tags = var.tags
}

resource "aws_iam_role" "hybrid_node_role" {
  name = "${var.cluster_name}-hybrid-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ssm.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "hybrid_eks_node" {
  role       = aws_iam_role.hybrid_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodeMinimalPolicy"
}

# Hybrid 노드 트래픽을 위한 보안 그룹 규칙
resource "aws_security_group_rule" "hybrid_node_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["172.16.0.0/16"]
  security_group_id = module.eks.cluster_security_group_id
  description       = "Hybrid 노드에서 API 서버와의 통신 허용"
}

resource "aws_security_group_rule" "hybrid_node_kubelet" {
  type              = "ingress"
  from_port         = 10250
  to_port           = 10250
  protocol          = "tcp"
  cidr_blocks       = ["172.16.0.0/16"]
  security_group_id = module.eks.cluster_security_group_id
  description       = "Hybrid 노드에서의 kubelet 통신 허용"
}
```

### 핵심 사항

- **`remote_network_config`**는 온프레미스 노드와 파드의 CIDR 범위를 정의합니다.
- Hybrid 노드는 `HYBRID_LINUX` 유형의 액세스 엔트리가 있는 IAM 역할을 통해 인증합니다.
- 보안 그룹 규칙에서 온프레미스 CIDR에서 EKS API 서버(443) 및 kubelet(10250)으로의 트래픽을 허용해야 합니다.
- Hybrid 노드에서는 VPC CNI가 사용되지 않으므로 온프레미스 측에서 대체 CNI(예: Cilium)를 구성해야 합니다.

---

## Add-on 관리

EKS 애드온은 클러스터에서 실행되는 관리형 컴포넌트입니다. 멀티 레이어 아키텍처에서 **코어 애드온**(coredns, vpc-cni, kube-proxy, eks-pod-identity-agent)은 클러스터 동작에 필수적이므로 `02-cluster`에 정의하고, **추가 애드온**(EBS CSI 등)은 `03-platform`에서 관리합니다.

### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `most_recent` | 클러스터의 Kubernetes 버전과 호환되는 최신 버전을 항상 사용합니다. |
| `before_compute` | 노드 그룹 프로비저닝 전에 애드온을 설치합니다. `vpc-cni`와 `eks-pod-identity-agent`에서 노드가 올바르게 시작되도록 필요합니다. |
| `configuration_values` | 애드온별 설정의 JSON 문자열입니다 (예: VPC CNI 프리픽스 위임). |
| `service_account_role_arn` | AWS API 접근이 필요한 애드온의 IAM 역할 ARN입니다 (예: EBS CSI 드라이버). IRSA와 Pod Identity 모두 지원합니다. |
| `resolve_conflicts_on_create` | 마이그레이션 중 기존 자체 관리 버전을 교체하려면 `"OVERWRITE"`로 설정합니다. |
| `resolve_conflicts_on_update` | 충돌하는 애드온 구성을 강제 업데이트하려면 `"OVERWRITE"`로 설정합니다. |

### Add-on의 Pod Identity

일부 애드온은 Pod Identity 연결을 직접 지원합니다. `03-platform/addons.tf`의 EBS CSI 드라이버 구성이 `pod_identity_association`을 사용하는 패턴을 보여줍니다:

```hcl
resource "aws_eks_addon" "ebs_csi" {
  cluster_name = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name   = "aws-ebs-csi-driver"

  pod_identity_association {
    role_arn        = aws_iam_role.ebs_csi.arn
    service_account = "ebs-csi-controller-sa"
  }
}
```

---

## Access Entry 기반 접근 제어

EKS는 레거시 `aws-auth` ConfigMap을 대체하는 Access Entry를 통한 API 기반 인증을 지원합니다. 멀티 레이어 아키텍처에서 초기 클러스터 관리자 접근은 `02-cluster`에서 (`enable_cluster_creator_admin_permissions`를 통해) 구성하고, 개발자와 뷰어를 위한 추가 액세스 엔트리는 `03-platform/access-entries.tf`에서 관리합니다.

### 인증 모드

| 모드 | 설명 |
|------|------|
| `API` | Access Entry만 사용 (신규 클러스터에 권장). |
| `API_AND_CONFIG_MAP` | Access Entry와 `aws-auth` ConfigMap 모두 사용 (마이그레이션 기간). |
| `CONFIG_MAP` | 레거시 `aws-auth`만 사용 (권장하지 않음). |

### 사용 가능한 Access Policy ARN

| 정책 | ARN | 설명 |
|------|-----|------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | 전체 클러스터 접근 |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | 관리자 접근 (IAM 관리 제외) |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | 대부분의 리소스 읽기/쓰기 |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | 읽기 전용 접근 |

---

## 배포 워크플로

### 레이어 순서대로 배포

각 레이어는 순서대로 초기화하고 적용해야 합니다. 이후 레이어가 이전 레이어의 상태 출력에 의존하기 때문입니다:

```bash
# 레이어 1: 네트워크
cd eks-terraform/01-network
terraform init
terraform plan
terraform apply

# 레이어 2: 클러스터
cd ../02-cluster
terraform init
terraform plan
terraform apply

# 레이어 3: 플랫폼
cd ../03-platform
terraform init
terraform plan
terraform apply
```

> **참고**: EKS 클러스터 생성(레이어 2)에는 일반적으로 10-15분이 소요됩니다. 레이어 1과 3은 더 빠릅니다.

### kubeconfig 구성

레이어 2 완료 후 `kubectl` 접근을 구성합니다:

```bash
cd eks-terraform/02-cluster

aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region)
```

### 클러스터 확인

```bash
# 노드 상태 확인
kubectl get nodes

# 시스템 파드 확인
kubectl get pods -n kube-system

# EKS 애드온 확인
kubectl get daemonsets -n kube-system
```

정상적인 클러스터의 예상 출력:

```
NAME                              STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
ip-10-0-2-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
```

### 역순으로 삭제

모든 리소스를 삭제하려면 의존하는 리소스가 먼저 제거되도록 역순으로 삭제합니다:

```bash
# 레이어 3: 플랫폼
cd eks-terraform/03-platform
terraform destroy

# 레이어 2: 클러스터
cd ../02-cluster
terraform destroy

# 레이어 1: 네트워크
cd ../01-network
terraform destroy
```

> **주의**: `terraform destroy`는 해당 레이어의 상태에서 관리하는 모든 리소스를 삭제합니다. 클러스터 레이어를 삭제하기 전에 실행 중인 중요한 워크로드가 없는지 확인하세요.

---

## 모범 사례

### 상태 관리

멀티 레이어 아키텍처는 이미 DynamoDB 잠금이 있는 레이어별 S3 상태 키를 사용합니다. 추가 권장 사항:

- S3 버킷에 **버전 관리를 활성화**하여 실수로 인한 상태 손상을 복구할 수 있도록 합니다.
- IAM 정책으로 **버킷 접근을 제한**합니다 — CI/CD 파이프라인과 권한 있는 운영자만 상태를 읽고 쓸 수 있어야 합니다.
- **상태 파일을 수동으로 편집하지 마세요** — 상태 조작이 필요한 경우 `terraform state` 명령을 사용합니다.

### 모듈 버전 관리

- `~>`로 모듈 버전을 고정하여 (예: `~> 21.0`) 패치 업데이트는 허용하면서 호환성 파괴 변경을 방지합니다.
- 메이저 버전 업그레이드 전에 모듈 CHANGELOG를 검토합니다.
- 비프로덕션 환경에서 먼저 업그레이드를 테스트합니다.

### 환경 분리

다음 방법 중 하나를 사용하여 환경을 분리합니다:

| 방식 | 장점 | 단점 |
|------|------|------|
| **별도 디렉토리** | 명확한 격리, 독립적인 상태 | 코드 중복 |
| **Terraform Workspace** | 단일 코드베이스, 쉬운 전환 | 공유 백엔드, 제한적 격리 |
| **Terragrunt** | DRY 구성, 강력한 격리 | 추가 도구 의존성 |

멀티 레이어 아키텍처에서 가장 일반적인 접근 방식은 **환경별 별도 디렉토리**로, 각 환경이 서로 다른 변수 값과 상태 키를 가진 자체 `01-network/`, `02-cluster/`, `03-platform/` 트리를 갖는 것입니다.

### 태깅 전략

비용 할당, 컴플라이언스, 리소스 관리를 위해 일관된 태그를 적용합니다:

```hcl
variable "tags" {
  default = {
    Environment = "dev"
    Team        = "platform"
    ManagedBy   = "terraform"
    Project     = "eks-cluster"
  }
}
```

---

## 다음 단계

- [EKS 클러스터 생성 - 1부: 사전 요구 사항](./02-eks-cluster-creation-part1.md) — EKS 클러스터 생성을 위한 사전 준비 사항
- [EKS 클러스터 생성 - 2부: eksctl을 사용한 클러스터 생성](./02-eks-cluster-creation-part2.md) — eksctl을 사용한 EKS 클러스터 생성
- [EKS 클러스터 생성 - 3부: AWS Console 및 CLI를 사용한 클러스터 생성](./02-eks-cluster-creation-part3.md) — Console과 CLI를 사용한 EKS 클러스터 생성
- [EKS 클러스터 생성 - 5부: 클러스터 액세스, 검증, 업그레이드 및 삭제](./02-eks-cluster-creation-part5.md) — EKS 클러스터 관리
- [EKS 네트워킹 - 1부: 기본 개념 및 VPC 구성](./03-eks-networking-part1.md) — EKS 네트워킹 기본 개념
- [EKS 보안](./05-eks-security.md) — EKS 클러스터 보안 구성

### 관련 주제

- [ArgoCD](../gitops/01-argocd.md) — GitOps 연속 배포
- [AWS Controllers for Kubernetes (ACK)](../platform/01-ack.md) — Kubernetes에서 AWS 리소스 관리
- [Karpenter](../autoscaling/02-karpenter.md) — 노드 프로비저닝 자동화
- [Kubernetes 확장](../core/11-extending-kubernetes.md) — Operator와 CRD를 사용한 Kubernetes API 확장

## 용어집

| 용어 | 설명 |
|------|------|
| **EKS** | Amazon Elastic Kubernetes Service — AWS에서 제공하는 관리형 Kubernetes 서비스입니다. |
| **Terraform** | HashiCorp에서 개발한 인프라를 코드로 프로비저닝하고 관리하는 도구입니다. |
| **Access Entry** | `aws-auth` ConfigMap을 대체하는 EKS API 기반의 클러스터 접근 권한 부여 메커니즘입니다. |
| **Pod Identity** | OIDC 프로바이더 없이 파드에 AWS 자격 증명을 제공하는 EKS 기능입니다. |
| **Auto Mode** | AWS가 노드 프로비저닝, 스케일링, OS 업데이트를 완전히 관리하는 EKS 모드입니다. |
| **Hybrid Nodes** | 온프레미스 또는 엣지 서버를 EKS 클러스터의 워커 노드로 참여시킬 수 있는 EKS 기능입니다. |
| **IAM** | Identity and Access Management — AWS 리소스에 대한 접근을 제어하는 서비스입니다. |
| **VPC** | Virtual Private Cloud — AWS 클라우드 내의 논리적으로 격리된 가상 네트워크입니다. |
| **IRSA** | IAM Roles for Service Accounts — OIDC를 통해 파드에 AWS 권한을 부여하는 레거시 방식입니다. |
| **원격 상태** | 하나의 Terraform 구성이 다른 구성의 상태 파일에서 출력을 읽을 수 있게 하는 Terraform 기능입니다. |

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [EKS 클러스터 생성 - Part 4 퀴즈](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md)를 풀어보세요.
