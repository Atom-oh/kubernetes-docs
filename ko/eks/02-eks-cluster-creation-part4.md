# EKS 클러스터 생성 - Part 4: Terraform을 사용한 클러스터 생성

> **예제 버전**: Amazon EKS 1.36; Terraform 1.15.7; AWS 프로바이더 6.64.0; EKS 모듈 21.25.0
> **마지막 업데이트**: 2026년 9월 11일

## 3개 레이어 Terraform 예제

Terraform은 인프라를 코드로 관리합니다. 이 예제는 AWS 프로바이더 6.x와 고정된 EKS 모듈 **21.25.0**, VPC 모듈 **5.21.0**을 사용합니다. HCL은 Terraform 1.15.7·AWS 프로바이더 6.64.0으로 검사했으며 AWS 배포나 프로덕션 동작은 실행하지 않았습니다. 기존 v20 방식의 `cluster_*` 입력은 모듈 v21과 호환되지 않으므로 아래의 `name`, `kubernetes_version`, `addons` 등 v21 이름을 사용하세요.

상태를 분리하면 팀별 소유권과 수명주기에 따라 변경을 검토하기 쉽습니다. 의존성이나 운영 영향을 없애지는 않습니다. 네트워크 변경은 클러스터를 중단시킬 수 있고 애드온·접근 정책 변경은 모든 워크로드에 영향을 줄 수 있습니다. 검증된 프로덕션 아키텍처가 아닌 구조 예제입니다.

### 3-레이어 아키텍처

```
eks-terraform/
├── 01-network/                   # 레이어 1: VPC 및 네트워킹
│   ├── providers.tf
│   ├── backend.tf                # S3 키: eks/dev/network/terraform.tfstate
│   ├── variables.tf
│   ├── main.tf                   # VPC 모듈
│   └── outputs.tf                # vpc_id, subnet_ids → 원격 상태
├── 02-cluster/                   # 레이어 2: EKS 클러스터 및 노드 그룹
│   ├── providers.tf
│   ├── backend.tf                # S3 키: eks/dev/cluster/terraform.tfstate
│   ├── data.tf                   # terraform_remote_state → 01-network
│   ├── variables.tf
│   ├── main.tf                   # EKS 모듈, 노드 그룹, 코어 애드온
│   └── outputs.tf                # cluster_name, endpoint → 원격 상태
└── 03-platform/                  # 레이어 3: 애드온, RBAC, Pod Identity
    ├── providers.tf
    ├── backend.tf                # S3 키: eks/dev/platform/terraform.tfstate
    ├── data.tf                   # terraform_remote_state → 01-network, 02-cluster
    ├── variables.tf
    ├── addons.tf                 # EBS CSI 드라이버, 추가 애드온
    ├── pod-identity.tf           # Pod Identity 연결
    └── access-entries.tf         # 개발자/뷰어 액세스 엔트리
```

### 레이어를 분리하는 이유

| 레이어 | 변경 빈도 | 소유 팀 | 영향 범위 |
|--------|----------|---------|----------|
| 01-network | 예시: 낮은 빈도 | 인프라 팀 | VPC·서브넷과 이에 의존하는 연결 |
| 02-cluster | 월간 | 플랫폼 팀 | EKS 클러스터, 노드 |
| 03-platform | 주간 | 플랫폼 / 앱 팀 | 애드온, RBAC, Pod Identity |

각 레이어는 별도 상태 키와 계획을 갖습니다. IAM 권한·CI 소유권도 분리하고 레이어 간 변경을 조율해야 합니다. 상태 분리만으로 애드온 변경이 클러스터 동작에 영향을 주지 않는다고 보장할 수는 없습니다.

### 공유 S3 백엔드

예제는 S3 기본 잠금인 `use_lockfile = true`(Terraform 1.10 이상)와 환경·레이어별 상태 키를 사용합니다. 백엔드 버킷을 별도로 생성하고 버전 관리·암호화·퍼블릭 액세스 차단을 설정한 뒤 초기화 전에 모든 `REPLACE_WITH_YOUR_STATE_BUCKET`을 바꾸세요. 필요한 상태 키 권한과 해당 `.tflock` 객체의 Get·Put·Delete 권한만 부여합니다. DynamoDB 잠금은 폐기 예정이므로 기존 백엔드 전환 시 잠금 테이블을 바로 삭제하지 말고 모든 클라이언트를 조율하세요.

```hcl
terraform {
  backend "s3" {
    bucket       = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key          = "eks/dev/network/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
    encrypt      = true
  }
}
```

`terraform_remote_state`는 HCL에 루트 출력을 제공하지만 읽기 권한을 가진 주체는 민감한 값이 포함된 **전체 상태 스냅샷**을 가져올 수 있습니다. 별도 프로젝트 간 적용 순서를 자동으로 만들지도 않습니다. 소비 팀에 전체 상태를 공개하면 안 되는 경우 선택한 값만 별도 통제된 경로로 게시하세요.

---

## 레이어 1: 네트워크 (01-network)

이 예제는 실습 규모를 줄이기 위해 3개 AZ VPC에 NAT Gateway 하나를 만듭니다. 단일 NAT는 특정 AZ 의존성과 AZ 간 전송 요금을 만들 수 있습니다. 프로덕션에는 AZ 장애를 고려한 egress, 서브넷 용량, DNS와 프라이빗 엔드포인트를 검토하세요.

### 01-network/providers.tf

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"

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
    bucket       = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key          = "eks/dev/network/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
    encrypt      = true
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
  version = "5.21.0"

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

> **서브넷 검색**은 Terraform EKS 모듈 버전이 아닌 Load Balancer Controller 버전·기능 게이트·서브넷 적격성 규칙을 따릅니다. 예제의 역할 태그 외에도 AZ 범위, 가용 주소, 라우팅과 클러스터 태그 필터를 확인하세요.

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

이 레이어는 **새 일반 EC2 클러스터**, 관리형 노드 그룹과 코어 애드온을 생성합니다. 기존 `cluster_admin_role_arn`을 명시적으로 설정하며 Terraform 호출자에게 Kubernetes 관리자 권한을 자동 부여하지 않습니다. 운영자는 해당 역할을 맡을 수 있어야 합니다. kubectl·플랫폼 설치 전에 프라이빗 엔드포인트에 연결·라우팅되는 관리 환경이 필요합니다.

### 02-cluster/providers.tf

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"

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
    bucket       = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key          = "eks/dev/cluster/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
    encrypt      = true
  }
}
```

### 02-cluster/data.tf

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key    = "eks/dev/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

data "aws_caller_identity" "current" {}

locals {
  cluster_arn = "arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.cluster_name}"
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
  default     = "1.36"
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

variable "cluster_admin_role_arn" {
  description = "Existing approved IAM role for initial Kubernetes administration; not an STS session ARN"
  type        = string
}
```

### 02-cluster/main.tf

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.25.0"

  name               = var.cluster_name
  kubernetes_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  encryption_config = null
  create_kms_key    = false

  # Cluster endpoint access
  endpoint_private_access = true
  endpoint_public_access  = false

  # Use API-based authentication (replaces aws-auth ConfigMap)
  authentication_mode = "API"

  # Use an explicitly selected existing administrator role
  enable_cluster_creator_admin_permissions = false

  access_entries = {
    bootstrap_admin = {
      principal_arn = var.cluster_admin_role_arn
      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }

  # EKS Add-ons (core only — additional add-ons go in 03-platform)
  addons = {
    coredns = {
      most_recent                 = false
      resolve_conflicts_on_update = "PRESERVE"
    }
    vpc-cni = {
      most_recent                 = false
      resolve_conflicts_on_update = "PRESERVE"
      before_compute              = true
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
        }
      })
    }
    kube-proxy = {
      most_recent                 = false
      resolve_conflicts_on_update = "PRESERVE"
    }
    eks-pod-identity-agent = {
      most_recent                 = false
      resolve_conflicts_on_update = "PRESERVE"
      before_compute              = true
    }
  }

  # Managed Node Groups
  eks_managed_node_groups = {
    default = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = ["m5.large"]

      min_size     = 2
      max_size     = 5
      desired_size = 2

      block_device_mappings = {
        root = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 50
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }
    }

    spot = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = ["m5.large", "m5a.large", "m5d.large"]
      capacity_type  = "SPOT"

      min_size     = 0
      max_size     = 5
      desired_size = 1

      block_device_mappings = {
        root = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size           = 50
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }
    }
  }

  # CloudWatch Logging
  enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = var.tags
}
```

노드 그룹 루트 디스크는 Launch Template의 block-device mapping으로 설정합니다. 모듈 기본 커스텀 Launch Template을 사용할 때 `disk_size`는 무시됩니다. 이 예제는 기본 AWS 소유 키 기반 Kubernetes API envelope encryption을 사용하며 고객 KMS 키는 별도 설계 선택입니다.

배포 전에 모듈 기본값을 검토하세요. 고정 모듈의 관리형 노드 IAM 역할에는 ECR ReadOnly와 IPv4 CNI 권한이 포함됩니다. 예제 동작을 위한 기본값이며 프로덕션 최소 권한이라는 주장이 아닙니다. 전용 CNI 신원과 명시적으로 검토한 노드 역할을 우선하고 충분한 경우 ECR PullOnly를 사용하세요. 노드 그룹 min/max는 오토스케일러를 설치하지 않습니다.

Terraform이 데이터 소스를 다시 평가하면 기본 호환 애드온 빌드가 달라질 수 있습니다. 대상 클러스터의 호환 빌드를 확인·기록하고 재현성을 위해 고정해야 한다면 `addon_version`을 사용하세요. 업데이트 시 검토한 커스텀 구성을 보존합니다.

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

output "cluster_arn" {
  description = "EKS cluster ARN used to scope platform role trust"
  value       = module.eks.cluster_arn
}
```

---

## 레이어 3: 플랫폼 구성 (03-platform)

일반 EC2 플랫폼 레이어는 추가 애드온, Pod Identity 연결과 개발자·뷰어 접근을 관리합니다. 상태는 분리되지만 변경은 클러스터 보안과 워크로드 가용성에 영향을 줄 수 있습니다. 아래 Auto Mode·Hybrid 대안은 플랫폼 파일 구성이 다릅니다.

### 03-platform/providers.tf

```hcl
terraform {
  required_version = ">= 1.10, < 2.0"

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
    bucket       = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key          = "eks/dev/platform/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
    encrypt      = true
  }
}
```

### 03-platform/data.tf

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key    = "eks/dev/network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

data "terraform_remote_state" "cluster" {
  backend = "s3"
  config = {
    bucket = "REPLACE_WITH_YOUR_STATE_BUCKET"
    key    = "eks/dev/cluster/terraform.tfstate"
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

variable "developer_role_arn" {
  description = "Existing approved IAM role for app-dev/app-staging Kubernetes access"
  type        = string
}

variable "viewer_role_arn" {
  description = "Existing approved IAM role for Kubernetes read access"
  type        = string
}

variable "app_bucket_name" {
  description = "Existing approved S3 bucket for the application's app/ prefix"
  type        = string
}
```

### 03-platform/addons.tf

```hcl
# EBS CSI Driver with Pod Identity
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
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-arn"            = data.terraform_remote_state.cluster.outputs.cluster_arn
          "aws:RequestTag/kubernetes-namespace"       = "kube-system"
          "aws:RequestTag/kubernetes-service-account" = "ebs-csi-controller-sa"
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
  depends_on                  = [aws_iam_role_policy_attachment.ebs_csi]

  pod_identity_association {
    role_arn        = aws_iam_role.ebs_csi.arn
    service_account = "ebs-csi-controller-sa"
  }

  tags = var.tags
}
```

### 03-platform/pod-identity.tf

```hcl
# The Kubernetes namespace and ServiceAccount are managed separately.
resource "aws_iam_role" "app_s3_access" {
  name = "${var.cluster_name}-app-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Condition = {
        StringEquals = {
          "aws:RequestTag/eks-cluster-arn"            = data.terraform_remote_state.cluster.outputs.cluster_arn
          "aws:RequestTag/kubernetes-namespace"       = "app-dev"
          "aws:RequestTag/kubernetes-service-account" = "app-sa"
        }
      }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "app_s3_access" {
  name = "ReadApprovedAppPrefix"
  role = aws_iam_role.app_s3_access.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = "arn:aws:s3:::${var.app_bucket_name}"
        Condition = {
          StringLike = { "s3:prefix" = ["app/", "app/*"] }
        }
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "arn:aws:s3:::${var.app_bucket_name}/app/*"
      }
    ]
  })
}

resource "aws_eks_pod_identity_association" "app_s3_access" {
  cluster_name    = data.terraform_remote_state.cluster.outputs.cluster_name
  namespace       = "app-dev"
  service_account = "app-sa"
  role_arn        = aws_iam_role.app_s3_access.arn
  depends_on      = [aws_iam_role_policy.app_s3_access]
}
```

애플리케이션 테스트 전에 Kubernetes·GitOps 소유자를 통해 새 `app-dev` 네임스페이스와 `app-sa` ServiceAccount를 만드세요. EKS 연결은 두 객체를 생성하지 않습니다. 예제는 승인한 버킷의 `app/` prefix 읽기만 허용하며 버킷 정책·KMS 암호화·크로스 어카운트 접근에는 추가로 검토한 권한이 필요할 수 있습니다. 실제 assumed role을 확인하고 IAM·연결 전파를 고려한 후 사용하세요.

### 03-platform/access-entries.tf

```hcl
# Developer with namespace-scoped access
resource "aws_eks_access_entry" "developer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = var.developer_role_arn
}

resource "aws_eks_access_policy_association" "developer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = aws_eks_access_entry.developer.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  access_scope {
    type       = "namespace"
    namespaces = ["app-dev", "app-staging"]
  }
}

# Read-only access
resource "aws_eks_access_entry" "viewer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = var.viewer_role_arn
}

resource "aws_eks_access_policy_association" "viewer" {
  cluster_name  = data.terraform_remote_state.cluster.outputs.cluster_name
  principal_arn = aws_eks_access_entry.viewer.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }
}
```

---

## EKS Pod Identity 구성

EKS Pod Identity는 지원되는 워크로드의 선택지이며 IRSA를 보편적으로 대체하지는 않습니다. IAM OIDC provider가 필요하지 않습니다. 일반 Linux EC2·Auto Mode·적절히 구성한 Hybrid Nodes에는 지원 경로가 있으며 Fargate·Windows에는 다른 지원 신원 방식을 사용해야 합니다. IRSA도 계속 지원됩니다.

### Pod Identity 동작 방식

1. 일반 지원 노드는 Pod Identity Agent DaemonSet을 사용합니다. Auto Mode는 기능을 제공하며 Hybrid Nodes는 문서화된 자격 증명 파일·전용 DaemonSet 구성이 필요합니다.
2. Pod Identity 트러스트 정책이 포함된 IAM 역할이 생성됩니다 (레이어 3에서 생성).
3. `aws_eks_pod_identity_association`을 통해 IAM 역할이 Kubernetes 서비스 어카운트와 연결됩니다.
4. 기본 자격 증명 체인을 사용하는 호환 SDK가 임시 자격 증명을 가져옵니다. 체인 앞쪽의 기존 정적 자격 증명이 우선할 수 있으므로 실제 신원을 확인하세요.

위의 `03-platform/pod-identity.tf`에 표시된 Pod Identity 리소스가 이 패턴을 따릅니다. IAM 역할의 트러스트 정책은 `pods.eks.amazonaws.com`을 보안 주체로 사용하며, `sts:TagSession`은 클러스터, 네임스페이스, 서비스 어카운트 메타데이터를 사용한 자동 세션 태깅을 활성화합니다.

### Pod Identity vs IRSA 비교

| 기능 | Pod Identity | IRSA |
|------|-------------|------|
| OIDC 프로바이더 필요 | 아니오 | 예 |
| 크로스 어카운트 | 지원되는 `targetRoleArn` 등 명시적 역할 위임; 신뢰·권한 필요 | 대상 계정의 OIDC 신뢰 또는 명시적 역할 체이닝 |
| 설정 복잡도 | 낮음 — 단일 연결 | 보통 — OIDC, 역할, 어노테이션 |
| 세션 태그 | 활성화 시 자동 EKS 컨텍스트 태그 | EKS Pod Identity 컨텍스트 태그는 자동 제공되지 않음 |
| 재사용 | 검토한 여러 연결에서 역할 사용 가능 | 명시적으로 제한한 여러 OIDC 발급자·subject를 한 역할에서 신뢰 가능 |

> 컴퓨팅 유형·SDK가 지원하는 신원 방식을 선택하세요. `sts:TagSession`은 태그를 추가하며 그 자체로 크로스 어카운트 신뢰를 설정하지 않습니다. 위 신뢰 정책은 세션 태그 활성화를 요구합니다. 모듈은 Pod Identity와 별개로 선택적 IRSA 사용을 위한 OIDC provider를 생성할 수 있습니다.

---

## EKS Auto Mode 클러스터

최초 배포 전에 선택하는 **새 클러스터 대안**입니다. 이미 적용한 클러스터 구성을 덮어쓰는 것은 마이그레이션 절차가 아닙니다. Auto Mode는 컴퓨팅·인프라 기능을 관리합니다. 아래 순수 Auto Mode 예제는 관리형 노드 그룹을 정의하지 않으며 모듈 v21의 `compute_config`를 사용합니다:

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.25.0"

  name               = var.cluster_name
  kubernetes_version = var.cluster_version
  vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids         = data.terraform_remote_state.network.outputs.private_subnet_ids

  endpoint_private_access                  = true
  endpoint_public_access                   = false
  authentication_mode                      = "API"
  encryption_config                        = null
  create_kms_key                           = false
  enable_cluster_creator_admin_permissions = false

  access_entries = {
    bootstrap_admin = {
      principal_arn = var.cluster_admin_role_arn
      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }

  compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  tags              = var.tags
}
```

### 핵심 사항

- **`compute_config.enabled = true`**를 통해 이 모듈이 컴퓨팅·로드 밸런싱·블록 스토리지를 함께 활성화합니다. 고정 모듈이 생성하는 IAM 정책을 검토하세요.
- **`node_pools`**는 활성화할 내장 노드 풀을 지정합니다 (`general-purpose`, `system`).
- 모듈 v21은 기반 리소스의 `bootstrap_self_managed_addons`를 `false`로 고정하며 모듈 입력으로 받지 않습니다. 현재 Auto Mode는 클러스터 DNS·네트워킹·스토리지·Pod Identity 기능을 포함하므로 Auto Mode 컴퓨팅에 대응하는 기존 애드온을 중복 설치할 필요가 없습니다.
- 이 대안은 관리형 노드 그룹을 사용하지 않습니다. 혼합 컴퓨팅도 지원하지만 Auto Mode 이외 노드는 해당 애드온과 배치 구성이 필요합니다.
- Auto Mode는 노드 풀에서 EC2 인스턴스를 프로비저닝하고 OS 패치, 스케일링, 라이프사이클을 처리합니다.

---

순수 Auto Mode에서는 일반 `03-platform/addons.tf`를 제외합니다. 그 파일의 기존 EBS CSI 드라이버는 Auto Mode 스토리지 컨트롤러가 아닙니다. 검토한 StorageClass에 Auto Mode provisioner인 `ebs.csi.eks.amazonaws.com`을 사용하세요. 애플리케이션 Pod Identity·액세스 엔트리 파일은 선행조건 충족 후 사용할 수 있습니다.

## EKS Hybrid Nodes 구성

이 구성은 **새 Hybrid 전용 제어 플레인 대안**이며 전체 호스트 프로비저닝 절차나 기존 클러스터 변환 절차가 아닙니다. VPN·Direct Connect 등 지원되는 라우팅 경로, DNS·방화벽·지원 OS·자격 증명 공급자를 별도로 준비해야 합니다. 클러스터 레이어 완료 후 nodeadm·CNI 설정으로 Hybrid 컴퓨팅을 연결한 다음 CoreDNS 애드온 준비를 기다리세요.

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.25.0"

  name               = var.cluster_name
  kubernetes_version = var.cluster_version
  vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids         = data.terraform_remote_state.network.outputs.private_subnet_ids

  endpoint_private_access                  = true
  endpoint_public_access                   = false
  authentication_mode                      = "API"
  encryption_config                        = null
  create_kms_key                           = false
  enable_cluster_creator_admin_permissions = false

  access_entries = {
    hybrid_nodes = {
      principal_arn = aws_iam_role.hybrid_node_role.arn
      type          = "HYBRID_LINUX"
    }
    bootstrap_admin = {
      principal_arn = var.cluster_admin_role_arn
      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }

  remote_network_config = {
    remote_node_networks = { cidrs = ["172.16.0.0/16"] }
    remote_pod_networks  = { cidrs = ["192.168.0.0/16"] }
  }

  security_group_additional_rules = {
    hybrid_api = {
      description = "Hybrid nodes to private Kubernetes API"
      protocol    = "tcp"
      from_port   = 443
      to_port     = 443
      type        = "ingress"
      cidr_blocks = ["172.16.0.0/16"]
    }
    hybrid_kubelet = {
      description = "Control plane to hybrid kubelet"
      protocol    = "tcp"
      from_port   = 10250
      to_port     = 10250
      type        = "egress"
      cidr_blocks = ["172.16.0.0/16"]
    }
  }

  enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  tags              = var.tags
}

resource "aws_iam_role" "hybrid_node_role" {
  name = "${var.cluster_name}-hybrid-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ssm.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike = {
          "aws:SourceArn" = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:*"
        }
      }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "hybrid_baseline" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
  ])
  role       = aws_iam_role.hybrid_node_role.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "hybrid_lifecycle" {
  name = "ScopedHybridNodeLifecycle"
  role = aws_iam_role.hybrid_node_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["eks:DescribeCluster", "eks:ListAccessEntries"]
        Resource = local.cluster_arn
      },
      {
        Effect    = "Allow"
        Action    = "ssm:DescribeInstanceInformation"
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = var.region } }
      },
      {
        Effect   = "Allow"
        Action   = "ssm:DeregisterManagedInstance"
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:managed-instance/*"
        Condition = {
          StringEquals = { "ssm:resourceTag/EKSClusterARN" = local.cluster_arn }
        }
      }
    ]
  })
}
```

### 핵심 사항

- **`remote_network_config`**는 중복되지 않는 원격 노드·Pod CIDR을 선언하며 VPN·라우팅·방화벽·CNI를 만들지 않습니다. 모듈 v21은 `cidrs`를 담은 객체를 받으며 해당 객체의 목록이 아닙니다.
- Hybrid 노드는 `HYBRID_LINUX` 유형의 액세스 엔트리가 있는 IAM 역할을 통해 인증합니다.
- Hybrid 노드는 TCP 443으로 프라이빗 API에 연결하고 제어 플레인은 TCP 10250으로 **Hybrid kubelet에 아웃바운드 연결**합니다. 온프레미스 방화벽과 필요한 Pod·웹훅 경로도 구성해야 하며 SG 규칙 두 개가 전체 네트워크 설계는 아닙니다.
- Hybrid 노드에서는 VPC CNI가 사용되지 않으므로 온프레미스 측에서 대체 CNI(예: Cilium)를 구성해야 합니다.

---

위 SSM 역할은 범위를 제한한 nodeadm 등록 해제도 지원합니다. 별도의 SSM activation·관리형 인스턴스에 `EKSClusterARN = local.cluster_arn` 태그를 지정해 정책과 맞추세요. 서명 키 변경 때문에 신규 SSM 설치·업그레이드에는 nodeadm 1.0.19 이상이 필요합니다. activation 비밀을 Terraform 소스에 넣거나 포함된 상태를 공개하지 마세요.

일반 EBS CSI 플랫폼 파일은 온프레미스 디스크에 적용되지 않습니다. Hybrid 노드·CNI 설정 후 별도로 검토한 플랫폼 구성을 사용합니다. 아래는 Hybrid 전용 대안의 코어 애드온 소유권 구성이며 같은 애드온을 이미 관리하는 구성에 덧붙이면 안 됩니다:

```hcl
# Hybrid-only platform alternative, after nodeadm/CNI and node readiness checks.
resource "aws_eks_addon" "hybrid_core" {
  for_each = toset(["coredns", "kube-proxy"])

  cluster_name = data.terraform_remote_state.cluster.outputs.cluster_name
  addon_name   = each.value
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

Hybrid 노드에서 애플리케이션 Pod Identity를 사용하기 전에 지원 에이전트의 Hybrid DaemonSet, 노드 자격 증명 파일과 노드의 `eks-auth:AssumeRoleForPodIdentity` 권한을 구성하세요. 위 SSM 기본 역할에는 이 선택적 권한이 없습니다. Hybrid Nodes 전용 애드온 안내를 따라야 하며 연결 생성만으로 충분하지 않습니다.

## Add-on 관리

일반 EC2 대안은 클러스터 레이어에서 CoreDNS·VPC CNI·kube-proxy·Pod Identity Agent를 관리하고 플랫폼 레이어에서 EBS CSI·애플리케이션 신원을 관리합니다. Auto Mode·Hybrid는 구성 요소와 설치 순서가 다르므로 일반 플랫폼 파일을 그대로 적용하면 안 됩니다.

### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `most_recent` | true이면 Terraform 평가 시 최신 호환 빌드, false이면 EKS 기본값을 선택합니다. 자율적인 업그레이드 서비스가 아닙니다. 재현성이 필요하면 검토한 `addon_version`을 지정하세요. |
| `before_compute` | 모듈 관리 애드온을 노드 그룹보다 먼저 생성하도록 순서를 정합니다. VPC CNI 초기화 등에 유용하지만 모든 애드온의 보편적 필수조건은 아닙니다. CoreDNS 정상 동작에는 사용 가능한 컴퓨팅이 필요합니다. |
| `configuration_values` | 애드온별 설정의 JSON 문자열입니다 (예: VPC CNI 프리픽스 위임). |
| `service_account_role_arn` | IRSA 역할 ARN입니다. Pod Identity는 `pod_identity_association`을 사용합니다. |
| `resolve_conflicts_on_create` | `NONE`은 충돌을 검토할 수 있게 합니다. 기존 설치의 검토된 마이그레이션에서만 `OVERWRITE`를 사용하세요. |
| `resolve_conflicts_on_update` | `PRESERVE`는 지원 범위에서 충돌하는 커스텀 설정을 보존합니다. 애드온 소유 필드는 스키마·configurationValues로 관리하세요. `OVERWRITE`는 변경을 버릴 수 있습니다. |

### Add-on의 Pod Identity

일부 애드온은 Pod Identity 연결을 직접 지원합니다. `03-platform/addons.tf`의 EBS CSI 드라이버 구성이 `pod_identity_association`을 사용하는 패턴을 보여줍니다:

위의 완전한 `03-platform/addons.tf` 리소스를 사용하세요. 중첩된 `pod_identity_association` 블록은 애드온이 소유하므로 같은 ServiceAccount의 연결을 별도 리소스로 중복 생성하지 않습니다.

---

## Access Entry 기반 접근 제어

초기 Kubernetes 관리 권한은 `02-cluster`의 명시적 액세스 엔트리로, 개발자·뷰어 권한은 `03-platform`으로 관리합니다. 정책 연결이 액세스 엔트리 리소스를 참조하여 Terraform 실행 순서를 만듭니다. API 접근 모드 변경은 마이그레이션 결정이며 API 활성화를 단순히 ConfigMap 전용으로 되돌릴 수는 없습니다.

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
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | 선택한 접근 범위의 Kubernetes 관리; AWS IAM 권한은 제공하지 않음 |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | 대부분의 리소스 읽기/쓰기 |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | 정책 대상 Kubernetes 리소스 조회; 일반적인 Secret 조회 권한은 아님 |

---

## 배포 워크플로

아래 명령은 백엔드·역할 권한·프라이빗 네트워크 선행조건을 갖춘 **일반 EC2 3개 레이어 예제**입니다. 필수 Terraform 변수(레이어 2의 `cluster_admin_role_arn`, 레이어 3의 `developer_role_arn`·`viewer_role_arn`·`app_bucket_name`)는 검토한 변수 파일이나 `TF_VAR_*` 값으로 설정합니다. 의도한 AWS 계정·리전을 사용하세요. Auto Mode·Hybrid 대안은 앞서 설명한 파일·부트스트랩 변경이 필요합니다.

### 레이어를 하나씩 계획하고 적용

셸 디렉터리 변경으로 다른 레이어를 선택하지 않도록 절대 프로젝트 경로를 사용합니다. 먼저 네트워크 계획을 초기화·저장합니다:

```bash
set -euo pipefail
umask 077
: "${TF_PROJECT_DIR:?Set the absolute path to eks-terraform}"
case "$TF_PROJECT_DIR" in /*) ;; *) printf '%s\n' 'An absolute project path is required.' >&2; exit 1 ;; esac

# Repeat for 02-cluster and then 03-platform only after the previous layer succeeds.
TF_LAYER=01-network
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" init
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" plan -out=reviewed.tfplan
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" show -no-color reviewed.tfplan
```
저장한 계획에서 생성·교체·삭제 리소스, IAM, 네트워크 노출과 비용을 검토합니다. 계획 파일에는 민감한 데이터가 포함될 수 있으므로 보호하세요. 검토한 파일만 적용합니다:

```bash
# Run only after reviewing this saved plan; a saved-plan apply does not prompt again.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed.tfplan
```
성공하면 `TF_LAYER=02-cluster`, 이어서 `TF_LAYER=03-platform`으로 계획·검토·적용을 반복합니다. 실패하면 진행을 중단하고 누락되거나 오래된 출력을 사용하는 하위 상태를 적용하지 마세요. 검토한 프로바이더 잠금 파일은 버전 관리하되 상태·kubeconfig·자격 증명·계획 파일은 소스 저장소에 넣지 않습니다.

기존 문서는 클러스터 생성 시간을 10–15분으로 추정했습니다. 이번 감사에서 측정·재현한 값이 아니며 용량·애드온·IAM·네트워크에 따라 시간이 달라집니다.

### kubeconfig 구성

클러스터 레이어 완료 후 명시적으로 선택한 관리자 역할을 사용합니다. 현재 AWS 신원에 해당 역할을 맡을 권한이 있어야 합니다. 이미 허용된 주체로 직접 인증한다면 그에 맞는 검토한 자격 증명 경로를 사용하세요.

```bash
set -euo pipefail
: "${TF_PROJECT_DIR:?}"
: "${EXAMPLE_KUBECONFIG:?Choose a private kubeconfig file}"
: "${TF_VAR_cluster_admin_role_arn:?Set the approved role the operator can assume}"
EKS_CLUSTER_NAME=$(terraform -chdir="$TF_PROJECT_DIR/02-cluster" output -raw cluster_name)
EKS_REGION=$(terraform -chdir="$TF_PROJECT_DIR/02-cluster" output -raw region)
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --role-arn "$TF_VAR_cluster_admin_role_arn" --kubeconfig "$EXAMPLE_KUBECONFIG"
```
### 결과 검증

일반 EC2 예제는 실제 노드·시스템 Pod·관리형 애드온 상태를 확인합니다:

```bash
: "${EXAMPLE_KUBECONFIG:?}" "${EKS_CLUSTER_NAME:?}" "${EKS_REGION:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get pods
aws eks list-addons --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
aws eks describe-addon --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --addon-name coredns --query 'addon.{status:status,version:addonVersion,health:health}'
```
예상 애드온별로 `describe-addon`을 반복합니다. DaemonSet 목록만으로 EKS 애드온 정상 상태를 입증할 수는 없습니다. API 인증·DNS·네트워크·스토리지·애플리케이션의 실제 AWS 신원을 확인하세요. 이번 감사에서는 이러한 실환경 검사를 실행하지 않았습니다. 순수 Auto Mode·Hybrid 전용 클러스터는 해당 검증 경로가 필요하며 같은 시스템 Pod가 없을 수 있습니다.

### 역순으로 삭제

데이터를 백업하고 PVC·PV 회수 동작을 검토한 뒤, Kubernetes가 생성한 로드 밸런서·볼륨 리소스를 담당 컨트롤러를 통해 먼저 정리합니다. 정리가 끝날 때까지 컨트롤러와 IAM 권한을 유지하세요. 이후 플랫폼 삭제 계획을 저장·검토합니다:

```bash
set -euo pipefail
: "${TF_PROJECT_DIR:?Set the absolute project path}"
case "$TF_PROJECT_DIR" in /*) ;; *) printf '%s\n' 'An absolute project path is required.' >&2; exit 1 ;; esac
# After workload/data cleanup, handle one layer at a time in this order:
# 03-platform, then 02-cluster, then 01-network.
TF_LAYER=03-platform
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" plan -destroy -out=reviewed-destroy.tfplan
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" show -no-color reviewed-destroy.tfplan
```
선택한 상태와 제안된 모든 삭제 대상이 이 환경의 리소스임을 확인한 뒤에만 적용합니다:

```bash
# Run only after reviewing this exact destruction plan.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed-destroy.tfplan
```
성공하면 `02-cluster`, 마지막으로 `01-network`에 반복합니다. 오류가 나면 중단하고 남은 ENI·로드 밸런서·볼륨·finalizer를 조사하세요. 삭제 계획은 해당 상태의 KMS 키 삭제도 예약할 수 있으므로 보존된 암호화 데이터에 필요한 키를 유지합니다. 독립적으로 관리하는 백엔드·상태 버전·복구 자료를 보존하세요.

---

## 모범 사례

### 상태 관리

서로 다른 S3 상태 키와 기본 잠금을 사용합니다. 잠금은 한 상태의 동시 쓰기를 제어하며 3개 상태 전체의 배포를 조율하지는 않습니다.

- S3 버킷에 **버전 관리를 활성화**하여 실수로 인한 상태 손상을 복구할 수 있도록 합니다.
- IAM 정책으로 **버킷 접근을 제한**합니다 — CI/CD 파이프라인과 권한 있는 운영자만 상태를 읽고 쓸 수 있어야 합니다.
- **상태 파일을 수동으로 편집하지 마세요** — 상태 조작이 필요한 경우 `terraform state` 명령을 사용합니다.

### 모듈 버전 관리

- `~> 21.0`은 22.0 미만의 마이너·패치 릴리스를 모두 허용하며 `~> 21.0.0`은 21.0.x로 제한합니다. 호환성을 보장하지는 않습니다. 이 예제는 모듈 버전을 명시적으로 고정하며 `.terraform.lock.hcl`은 원격 모듈이 아닌 프로바이더를 잠급니다.
- 메이저 버전 업그레이드 전에 모듈 CHANGELOG를 검토합니다.
- 비프로덕션 환경에서 먼저 업그레이드를 테스트합니다.

### 환경 분리

다음 방법 중 하나를 사용하여 환경을 분리합니다:

| 방식 | 장점 | 단점 |
|------|------|------|
| **별도 디렉토리** | 명확한 격리, 독립적인 상태 | 코드 중복 |
| **Terraform Workspace** | 단일 코드베이스, 쉬운 전환 | 공유 백엔드, 제한적 격리 |
| **Terragrunt** | 구성 재사용과 실행 조율 | 추가 도구 필요; 상태·권한 분리가 여전히 필요 |

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

- [ArgoCD](../gitops/argocd/README.md) — GitOps 연속 배포
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md) — Kubernetes에서 AWS 리소스 관리
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
| **IRSA** | IAM Roles for Service Accounts — 지원되는 OIDC 기반 워크로드 신원 방식입니다. |
| **원격 상태** | 하나의 Terraform 구성이 다른 구성의 상태 파일에서 출력을 읽을 수 있게 하는 Terraform 기능입니다. |

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [EKS 클러스터 생성 - Part 4 퀴즈](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md)를 풀어보세요.


## 검증 참고 자료

- [EKS module v21 migration](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.25.0/docs/UPGRADE-21.0.md)
- [S3 backend locking](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Remote state access](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Pod Identity role trust](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)
- [EKS add-ons and Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Hybrid credentials](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Hybrid add-ons](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
