# 인프라 구성 기초

> **검증 환경**: Terraform 1.15.7, AWS Provider 6.64.0, EKS module 21.25.0, VPC module 6.7.2, Pod Identity module 2.9.0
> **마지막 검토**: 2026년 9월 11일. 로컬 schema/mock-plan 검증이며 실제 AWS 배포를 수행한 결과는 아닙니다.

< [이전: 목차](./README.md) | [목차](./README.md) | [다음: NLB 가중치 라우팅](02-infrastructure-advanced.md) >

이 예제는 **계정·환경별 상태 버킷과 한 리전의 blue/green 클러스터**를 설명합니다. 기본 Auto Mode NodePool은 구성된 여러 AZ를 사용할 수 있으며, 색상 이름이나 서브넷 태그만으로 노드가 한 AZ에 고정되지 않습니다. 단일 AZ 워커 셀은 [Zonal 운영](15-zonal-operations-guide.md)에 따라 별도 NodePool/NodeClass·라우팅·용량을 설계합니다.

아래 파일은 독자가 별도 `eks-terraform/` 프로젝트에 작성하는 예제입니다. 상위 `00-shared`의 `.tf` 파일은 자식 root에 자동 상속되지 않습니다. 각 root의 선언을 사용하고 중복 변수/locals를 함께 복사하지 않습니다. 기존 v20/v5 기반 state에 최신 모듈을 바로 적용하지 말고 각 모듈의 migration guide와 실제 plan을 검토합니다. `.terraform.lock.hcl`은 root별로 보관하며 모듈 버전도 별도로 고정합니다.

API endpoint는 기본적으로 private입니다. `kubectl` 검증과 GitOps 컨트롤러에는 VPC 내부 실행 환경, VPN 등 실제 API 접근 경로가 필요합니다. 이 가이드는 그 경로를 자동 생성하지 않습니다.

***

이 문서에서는 Terraform을 사용하여 EKS Auto Mode 클러스터 인프라를 3개의 독립적인 레이어로 구성하는 방법을 설명합니다. 각 레이어는 변경 빈도, 팀 오너십, 그리고 장애 영향 범위(Blast Radius)에 따라 분리되어 있어 운영 안정성과 팀 협업 효율성을 높입니다.

## 목차

1. [3-Layer 아키텍처 소개](01-infrastructure-setup.md#3-layer-아키텍처-소개)
2. [00-shared: 공통 설정](01-infrastructure-setup.md#00-shared-공통-설정)
3. [01-network: VPC 구성](01-infrastructure-setup.md#01-network-vpc-구성)
4. [02-cluster: EKS Auto Mode](01-infrastructure-setup.md#02-cluster-eks-auto-mode)
5. [03-platform: Add-ons & Pod Identity](01-infrastructure-setup.md#03-platform-add-ons--pod-identity)
6. [레이어 간 연계](01-infrastructure-setup.md#레이어-간-연계)
7. [검증](01-infrastructure-setup.md#검증)

***

## 3-Layer 아키텍처 소개

### 왜 레이어를 분리하는가?

단일 Terraform 상태 파일로 모든 인프라를 관리하면 다음과 같은 문제가 발생합니다:

1. **Blast Radius 확대**: 하나의 실수가 전체 인프라에 영향
2. **긴 Plan/Apply 시간**: 변경 사항이 없는 리소스도 매번 검사
3. **팀 협업 충돌**: 여러 팀이 동시에 작업할 때 Lock 경합
4. **권한 관리 어려움**: 네트워크 팀과 애플리케이션 팀의 세밀한 권한·승인 경계 구성의 어려움

### 레이어별 특성 비교 (변경 빈도는 예시)

| Layer | 이름       | 변경 빈도  | 주요 오너  | Blast Radius | 롤백 난이도 |
| ----- | -------- | ------ | ------ | ------------ | ------ |
| 00    | shared   | 거의 없음  | DevOps | 전체           | 매우 높음  |
| 01    | network  | 월 1-2회 | 네트워크 팀 | VPC 전체       | 높음     |
| 02    | cluster  | 월 1-2회 | 플랫폼 팀  | EKS 클러스터     | 중간     |
| 03    | platform | 주 1-2회 | 플랫폼 팀 | DNS·접근 권한 등 클러스터 전체에 영향 가능 | 구성 요소별로 다름 |

### 디렉토리 구조

```
eks-terraform/
├── 00-shared/
│   ├── backend-bootstrap.tf # local state로 S3 backend 생성
│   └── variables.tf         # 공통 변수 정의
│
├── 01-network/
│   ├── backend.tf           # network/terraform.tfstate
│   ├── main.tf              # VPC 모듈
│   ├── variables.tf         # 네트워크 변수
│   └── outputs.tf           # vpc_id, subnet_ids 출력
│
├── 02-cluster/
│   ├── backend.tf           # cluster/terraform.tfstate
│   ├── data.tf              # remote_state (01-network)
│   ├── main.tf              # EKS Auto Mode 모듈
│   ├── variables.tf         # 클러스터 변수
│   └── outputs.tf           # cluster_name, oidc_arn 출력
│
├── 03-platform/
│   ├── backend.tf           # platform/terraform.tfstate
│   ├── data.tf              # remote_state (01, 02)
│   ├── main.tf              # Add-ons, Pod Identity
│   ├── variables.tf         # 플랫폼 변수
│   └── outputs.tf           # IAM role ARNs 출력
│
├── environments/
│   ├── dev.tfvars
│   ├── staging.tfvars
│   └── prod.tfvars
│
└── modules/                  # 커스텀 모듈 (선택)
    └── pod-identity/
```

새 프로젝트의 `.gitignore`에 아래 항목을 포함합니다. Provider 잠금 파일 `.terraform.lock.hcl`은 제외하지 않고 root별로 커밋합니다.

```text
.terraform/
.terraform-data/
.bootstrap-state/
*.tfstate
*.tfstate.*
*.tfplan
```

### 핵심 원칙

> **Terraform은 AWS 인프라만 관리합니다.**
>
> Kubernetes 리소스(NodePool, Deployment, Service 등)는 ArgoCD를 통한 GitOps 방식으로 관리합니다. 자세한 내용은 [GitOps 멀티 클러스터 배포](04-gitops-multi-cluster.md)를 참조하세요.

***

## 00-shared: 공통 설정

### S3 Backend 구성 (네이티브 S3 잠금)

> **참고**: Terraform 1.10부터 S3 backend에서 `use_lockfile = true` 옵션을 통해 DynamoDB 없이 네이티브 S3 잠금을 사용할 수 있습니다. S3의 conditional writes를 활용하여 상태 파일 잠금을 처리하므로, DynamoDB 테이블 생성 및 관리가 불필요합니다.

모든 레이어가 공유하는 Terraform 상태 저장소를 먼저 구성합니다.

```hcl
# 00-shared/backend-bootstrap.tf
# 이 파일은 최초 1회만 로컬에서 실행합니다

terraform {
  backend "local" {}
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy   = "terraform"
      Project     = var.project_name
      Environment = var.environment
    }
  }
}

# Terraform 상태 저장용 S3 버킷
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    Description = "Terraform state storage for EKS infrastructure"
  }
}

# S3 버킷 버전 관리 활성화
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 버킷 암호화
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# 퍼블릭 액세스 차단
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 출력
output "state_bucket_name" {
  value       = aws_s3_bucket.terraform_state.id
  description = "S3 bucket name for Terraform state"
}

data "aws_caller_identity" "current" {}
```

### 공통 변수 정의

```hcl
# 00-shared/variables.tf
# 모든 레이어에서 참조하는 공통 변수

variable "region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "eks-platform"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

# 공통 태그
variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

# 로컬 변수로 태그 병합
locals {
  default_tags = {
    ManagedBy   = "terraform"
    Project     = var.project_name
    Environment = var.environment
    Repository  = "eks-terraform"
  }

  merged_tags = merge(local.default_tags, var.common_tags)
}
```

### 환경별 변수 파일

```hcl
# environments/dev.tfvars
region       = "ap-northeast-2"
environment  = "dev"
project_name = "eks-platform"

common_tags = {
  CostCenter = "development"
  Team       = "platform-dev"
}
```

```hcl
# environments/prod.tfvars
region       = "ap-northeast-2"
environment  = "prod"
project_name = "eks-platform"

common_tags = {
  CostCenter  = "production"
  Team        = "platform-sre"
  Compliance  = "required"
  BackupLevel = "critical"
}
```

***

## 01-network: VPC 구성

### Backend 설정

```hcl
# 01-network/backend.tf
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    key          = "network/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.merged_tags
  }
}
```

### 변수 정의

```hcl
# 01-network/variables.tf
variable "region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "eks-platform"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

# 두 AZ의 네트워크 배치. 워커의 AZ 고정 설정과는 별개입니다.
variable "availability_zones" {
  description = "Availability zones for blue/green clusters"
  type = object({
    blue  = string
    green = string
  })
  default = {
    blue  = "ap-northeast-2a"
    green = "ap-northeast-2c"
  }
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway (cost optimization)"
  type        = bool
  default     = false # prod에서는 false로 각 AZ에 NAT 배치
}

# 태그
variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

locals {
  default_tags = {
    ManagedBy   = "terraform"
    Project     = var.project_name
    Environment = var.environment
    Layer       = "network"
  }

  merged_tags = merge(local.default_tags, var.common_tags)

  # 클러스터 이름 (EKS 태그에 필요)
  cluster_names = {
    blue  = "${var.project_name}-${var.environment}-blue"
    green = "${var.project_name}-${var.environment}-green"
  }
}
```

### VPC 메인 구성

```hcl
# 01-network/main.tf

# 블루/그린 클러스터를 위한 VPC 구성
# 기본 Auto Mode pools는 여러 AZ를 사용할 수 있습니다.

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.2"

  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  # 서로 다른 두 AZ 사용
  azs = [
    var.availability_zones.blue, # ap-northeast-2a
    var.availability_zones.green # ap-northeast-2c
  ]

  # 프라이빗 서브넷 (EKS 노드)
  # Blue: 10.0.0.0/18 (16,384 IPs)
  # Green: 10.0.64.0/18 (16,384 IPs)
  private_subnets = [
    cidrsubnet(var.vpc_cidr, 2, 0), # 10.0.0.0/18 - Blue
    cidrsubnet(var.vpc_cidr, 2, 1)  # 10.0.64.0/18 - Green
  ]

  # 퍼블릭 서브넷 (NAT Gateway, Load Balancer)
  # Blue: 10.0.128.0/20 (4,096 IPs)
  # Green: 10.0.144.0/20 (4,096 IPs)
  public_subnets = [
    cidrsubnet(var.vpc_cidr, 4, 8), # 10.0.128.0/20 - Blue
    cidrsubnet(var.vpc_cidr, 4, 9)  # 10.0.144.0/20 - Green
  ]

  # 인트라 서브넷 (DB, ElastiCache - 인터넷 접근 불필요)
  # Blue: 10.0.160.0/20
  # Green: 10.0.176.0/20
  intra_subnets = [
    cidrsubnet(var.vpc_cidr, 4, 10), # 10.0.160.0/20 - Blue
    cidrsubnet(var.vpc_cidr, 4, 11)  # 10.0.176.0/20 - Green
  ]

  # NAT Gateway 설정
  enable_nat_gateway     = var.enable_nat_gateway
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = !var.single_nat_gateway

  # DNS 설정
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs (보안 감사용)
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
  flow_log_max_aggregation_interval    = 60

  # 로드밸런서 자동 발견용 태그 - 퍼블릭 서브넷
  public_subnet_tags = {
    "kubernetes.io/role/elb"                             = 1
    "kubernetes.io/cluster/${local.cluster_names.blue}"  = "shared"
    "kubernetes.io/cluster/${local.cluster_names.green}" = "shared"
  }

  # 로드밸런서 자동 발견용 태그 - 프라이빗 서브넷
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"                    = 1
    "kubernetes.io/cluster/${local.cluster_names.blue}"  = "shared"
    "kubernetes.io/cluster/${local.cluster_names.green}" = "shared"
  }

  # 개별 서브넷 태그 (Zone 식별)
  public_subnet_tags_per_az = {
    "${var.availability_zones.blue}" = {
      Zone    = "blue"
      Cluster = local.cluster_names.blue
    }
    "${var.availability_zones.green}" = {
      Zone    = "green"
      Cluster = local.cluster_names.green
    }
  }

  private_subnet_tags_per_az = {
    "${var.availability_zones.blue}" = {
      Zone    = "blue"
      Cluster = local.cluster_names.blue
    }
    "${var.availability_zones.green}" = {
      Zone    = "green"
      Cluster = local.cluster_names.green
    }
  }

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

# VPC Endpoints (프라이빗 EKS 통신용)
module "vpc_endpoints" {
  source  = "terraform-aws-modules/vpc/aws//modules/vpc-endpoints"
  version = "6.7.2"

  vpc_id = module.vpc.vpc_id

  # S3/DynamoDB Gateway endpoint 자체 추가 요금과 서비스 사용료는 구분합니다
  endpoints = {
    s3 = {
      service         = "s3"
      service_type    = "Gateway"
      route_table_ids = module.vpc.private_route_table_ids
      tags = {
        Name = "${var.project_name}-${var.environment}-s3-endpoint"
      }
    }

    dynamodb = {
      service         = "dynamodb"
      service_type    = "Gateway"
      route_table_ids = module.vpc.private_route_table_ids
      tags = {
        Name = "${var.project_name}-${var.environment}-dynamodb-endpoint"
      }
    }
  }

  tags = local.merged_tags
}

# 프라이빗 엔드포인트용 보안 그룹
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.project_name}-${var.environment}-vpc-endpoints-sg"
  description = "Security group for VPC Endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.merged_tags, {
    Name = "${var.project_name}-${var.environment}-vpc-endpoints-sg"
  })
}

# 인터페이스 엔드포인트 (EKS 프라이빗 클러스터용)
resource "aws_vpc_endpoint" "interface_endpoints" {
  for_each = toset([
    "ec2",
    "eks-auth",
    "ecr.api",
    "ecr.dkr",
    "sts",
    "logs",
    "elasticloadbalancing",
    "autoscaling"
  ])

  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = module.vpc.private_subnets
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = merge(local.merged_tags, {
    Name = "${var.project_name}-${var.environment}-${replace(each.value, ".", "-")}-endpoint"
  })
}
```

### 출력 정의

```hcl
# 01-network/outputs.tf

# VPC 기본 정보
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

# 서브넷 ID - 전체
output "private_subnet_ids" {
  description = "Private subnet IDs (all)"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs (all)"
  value       = module.vpc.public_subnets
}

output "intra_subnet_ids" {
  description = "Intra subnet IDs (database)"
  value       = module.vpc.intra_subnets
}

# 서브넷 ID - Zone별 분리
output "blue_zone_subnets" {
  description = "Subnet IDs for Blue zone (ap-northeast-2a)"
  value = {
    private = module.vpc.private_subnets[0]
    public  = module.vpc.public_subnets[0]
    intra   = module.vpc.intra_subnets[0]
  }
}

output "green_zone_subnets" {
  description = "Subnet IDs for Green zone (ap-northeast-2c)"
  value = {
    private = module.vpc.private_subnets[1]
    public  = module.vpc.public_subnets[1]
    intra   = module.vpc.intra_subnets[1]
  }
}

# AZ 정보
output "availability_zones" {
  description = "Availability zones"
  value       = module.vpc.azs
}

# NAT Gateway 정보
output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.natgw_ids
}

output "nat_public_ips" {
  description = "NAT Gateway public IPs"
  value       = module.vpc.nat_public_ips
}

# 보안 그룹
output "vpc_endpoints_security_group_id" {
  description = "Security group ID for VPC endpoints"
  value       = aws_security_group.vpc_endpoints.id
}

# 클러스터 이름 (02-cluster에서 사용)
output "cluster_names" {
  description = "EKS cluster names for blue/green"
  value       = local.cluster_names
}

# 환경 정보
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}
```

***

## 02-cluster: EKS Auto Mode

### Backend 설정

```hcl
# 02-cluster/backend.tf
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    key          = "cluster/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.merged_tags
  }
}
```

### Remote State 데이터 소스

```hcl
# 02-cluster/data.tf

# 01-network 레이어의 상태 참조
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "network/terraform.tfstate"
    region = var.region
  }
}

# 로컬 변수로 네트워크 출력값 매핑
locals {
  vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
  public_subnet_ids  = data.terraform_remote_state.network.outputs.public_subnet_ids
  blue_zone_subnets  = data.terraform_remote_state.network.outputs.blue_zone_subnets
  green_zone_subnets = data.terraform_remote_state.network.outputs.green_zone_subnets
  cluster_names      = data.terraform_remote_state.network.outputs.cluster_names
}

# 현재 AWS 계정 정보
data "aws_caller_identity" "current" {}

# 현재 리전 정보
data "aws_region" "current" {}
```

### 변수 정의

```hcl
# 02-cluster/variables.tf
variable "region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "eks-platform"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.36"
}

# 클러스터 접근 설정
variable "cluster_endpoint_public_access" {
  description = "Enable public API access only for the explicit CIDRs below"
  type        = bool
  default     = false
}

variable "cluster_endpoint_private_access" {
  description = "Enable private access to cluster endpoint"
  type        = bool
  default     = true
}

# 관리자 IAM Role/User ARNs
variable "cluster_admin_arns" {
  description = "Explicit IAM principals that own cluster administration"
  type        = list(string)

  validation {
    condition     = length(var.cluster_admin_arns) > 0 && length(distinct(var.cluster_admin_arns)) == length(var.cluster_admin_arns)
    error_message = "Provide at least one unique cluster administrator ARN."
  }
}

# 블루/그린 클러스터 활성화 여부
variable "enable_blue_cluster" {
  description = "Enable Blue cluster"
  type        = bool
  default     = true
}

variable "enable_green_cluster" {
  description = "Enable Green cluster"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

locals {
  default_tags = {
    ManagedBy   = "terraform"
    Project     = var.project_name
    Environment = var.environment
    Layer       = "cluster"
  }

  merged_tags = merge(local.default_tags, var.common_tags)
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Approved IPv4 CIDRs, required only if public API access is enabled"
  type        = list(string)
  default     = []
  validation {
    condition = !var.cluster_endpoint_public_access || (
      length(var.cluster_endpoint_public_access_cidrs) > 0 &&
      alltrue([for cidr in var.cluster_endpoint_public_access_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"])
    )
    error_message = "Public API access requires explicit IPv4 CIDRs; do not use 0.0.0.0/0."
  }
}
```

### EKS Auto Mode 클러스터 구성

```hcl
# 02-cluster/main.tf

# Blue deployment, multi-AZ baseline
module "eks_blue" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.25.0"

  count = var.enable_blue_cluster ? 1 : 0

  name               = local.cluster_names.blue
  kubernetes_version = var.kubernetes_version

  # EKS API and built-in Auto Mode pools use both configured AZs
  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  # Control Plane 서브넷 (ENI 배치)
  control_plane_subnet_ids = local.private_subnet_ids

  # Cluster Endpoint 접근 설정
  endpoint_public_access       = var.cluster_endpoint_public_access
  endpoint_private_access      = var.cluster_endpoint_private_access
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access ? var.cluster_endpoint_public_access_cidrs : null

  # EKS Auto Mode 활성화
  compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # Auto Mode 네트워킹
  # Auto Mode 스토리지
  # 클러스터 암호화
  iam_role_use_name_prefix      = false
  node_iam_role_use_name_prefix = false
  create_kms_key                = false
  encryption_config = {
    provider_key_arn = aws_kms_key.eks_blue[0].arn
    resources        = ["secrets"]
  }

  # CloudWatch 로그 활성화
  enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  # 선택적 IRSA OIDC provider. Pod Identity의 필수 조건은 아닙니다.
  enable_irsa = true

  # Access Entries (EKS API 인증)
  enable_cluster_creator_admin_permissions = false

  access_entries = {
    for arn in toset(var.cluster_admin_arns) : arn => {
      principal_arn = arn
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  tags = merge(local.merged_tags, {
    Cluster = "blue"
  })
}

# Green deployment, multi-AZ baseline
module "eks_green" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.25.0"

  count = var.enable_green_cluster ? 1 : 0

  name               = local.cluster_names.green
  kubernetes_version = var.kubernetes_version

  # EKS API and built-in Auto Mode pools use both configured AZs
  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  control_plane_subnet_ids = local.private_subnet_ids

  endpoint_public_access       = var.cluster_endpoint_public_access
  endpoint_private_access      = var.cluster_endpoint_private_access
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access ? var.cluster_endpoint_public_access_cidrs : null

  # EKS Auto Mode 활성화
  compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }
  iam_role_use_name_prefix      = false
  node_iam_role_use_name_prefix = false
  create_kms_key                = false
  encryption_config = {
    provider_key_arn = aws_kms_key.eks_green[0].arn
    resources        = ["secrets"]
  }

  enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  enable_irsa = true

  enable_cluster_creator_admin_permissions = false

  access_entries = {
    for arn in toset(var.cluster_admin_arns) : arn => {
      principal_arn = arn
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  tags = merge(local.merged_tags, {
    Cluster = "green"
  })
}

# KMS Keys for cluster encryption
resource "aws_kms_key" "eks_blue" {
  count = var.enable_blue_cluster ? 1 : 0

  description             = "KMS key for EKS Blue cluster encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.merged_tags, {
    Name    = "${local.cluster_names.blue}-encryption-key"
    Cluster = "blue"
  })
}

resource "aws_kms_key" "eks_green" {
  count = var.enable_green_cluster ? 1 : 0

  description             = "KMS key for EKS Green cluster encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.merged_tags, {
    Name    = "${local.cluster_names.green}-encryption-key"
    Cluster = "green"
  })
}

resource "aws_kms_alias" "eks_blue" {
  count = var.enable_blue_cluster ? 1 : 0

  name          = "alias/${local.cluster_names.blue}-encryption"
  target_key_id = aws_kms_key.eks_blue[0].key_id
}

resource "aws_kms_alias" "eks_green" {
  count = var.enable_green_cluster ? 1 : 0

  name          = "alias/${local.cluster_names.green}-encryption"
  target_key_id = aws_kms_key.eks_green[0].key_id
}
```

### 출력 정의

```hcl
# 02-cluster/outputs.tf

# Blue 클러스터 출력
output "blue_cluster_name" {
  description = "Blue cluster name"
  value       = var.enable_blue_cluster ? module.eks_blue[0].cluster_name : null
}

output "blue_cluster_endpoint" {
  description = "Blue cluster API endpoint"
  value       = var.enable_blue_cluster ? module.eks_blue[0].cluster_endpoint : null
}

output "blue_cluster_certificate_authority_data" {
  description = "Blue cluster CA data"
  value       = var.enable_blue_cluster ? module.eks_blue[0].cluster_certificate_authority_data : null
  sensitive   = true
}

output "blue_oidc_provider_arn" {
  description = "Blue cluster OIDC provider ARN"
  value       = var.enable_blue_cluster ? module.eks_blue[0].oidc_provider_arn : null
}

output "blue_oidc_provider_url" {
  description = "Blue cluster OIDC provider URL"
  value       = var.enable_blue_cluster ? module.eks_blue[0].oidc_provider : null
}

# Green 클러스터 출력
output "green_cluster_name" {
  description = "Green cluster name"
  value       = var.enable_green_cluster ? module.eks_green[0].cluster_name : null
}

output "green_cluster_endpoint" {
  description = "Green cluster API endpoint"
  value       = var.enable_green_cluster ? module.eks_green[0].cluster_endpoint : null
}

output "green_cluster_certificate_authority_data" {
  description = "Green cluster CA data"
  value       = var.enable_green_cluster ? module.eks_green[0].cluster_certificate_authority_data : null
  sensitive   = true
}

output "green_oidc_provider_arn" {
  description = "Green cluster OIDC provider ARN"
  value       = var.enable_green_cluster ? module.eks_green[0].oidc_provider_arn : null
}

output "green_oidc_provider_url" {
  description = "Green cluster OIDC provider URL"
  value       = var.enable_green_cluster ? module.eks_green[0].oidc_provider : null
}

# 공통 출력
output "cluster_names" {
  description = "All cluster names"
  value = {
    blue  = var.enable_blue_cluster ? module.eks_blue[0].cluster_name : null
    green = var.enable_green_cluster ? module.eks_green[0].cluster_name : null
  }
}

output "cluster_endpoints" {
  description = "All cluster endpoints"
  value = {
    blue  = var.enable_blue_cluster ? module.eks_blue[0].cluster_endpoint : null
    green = var.enable_green_cluster ? module.eks_green[0].cluster_endpoint : null
  }
}

output "kubernetes_version" {
  description = "Kubernetes version"
  value       = var.kubernetes_version
}
```

***

## 03-platform: Add-ons & Pod Identity

Auto Mode의 Pod Identity agent·노드 네트워킹·블록 스토리지 기능을 일반 `aws-node`/EBS CSI/agent 애드온으로 중복 설치하지 않습니다. [현재 Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)는 노드의 시스템 서비스인 **node-local CoreDNS**를 사용합니다. 순수 Auto Mode에는 CoreDNS Deployment가 필요하지 않습니다. 일반 노드가 섞여 있으면 Deployment를 유지해야 하므로, 아래 예제에서 `enable_coredns_addon = true`를 설정하고 호환 버전을 지정합니다. 기본값은 `false`입니다. StorageClass는 [Auto Mode 안내](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)에 따라 `ebs.csi.eks.amazonaws.com`으로 GitOps에서 생성합니다.

이 예제의 Pod Identity는 **External Secrets 컨트롤러가 이름으로 지정한 Secrets Manager/SSM 값을 읽는 용도**입니다. association은 ServiceAccount나 ESO 설치를 대신하지 않으므로 같은 namespace/SA를 GitOps로 구성하고, Pod Identity를 지원하는 SDK 기본 자격 증명 체인을 사용합니다. `ListSecrets` 기반 검색은 이 최소 예제에 포함하지 않습니다. 고객 관리 KMS 키를 쓰면 해당 키 ARN의 `kms:Decrypt`와 key policy 허용을 추가해야 합니다.

이미지 pull은 kubelet/노드 역할의 권한입니다. 애플리케이션의 Pod Identity로 해결하지 않습니다. ArgoCD의 대상 EKS 인증 및 OCI/ECR 토큰 갱신은 [ArgoCD 설치](../gitops/argocd/01-installation.md)·[애플리케이션 구성](../gitops/argocd/02-applications.md)에서 별도로 구성합니다. 관리자 access entry는 Cluster layer가 소유하고, Platform layer에서 같은 principal을 다시 만들지 않습니다.


### Backend 설정

```hcl
# 03-platform/backend.tf
terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    key          = "platform/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.merged_tags
  }
}
```

### Remote State 데이터 소스

```hcl
# 03-platform/data.tf

# 01-network 레이어 참조
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "network/terraform.tfstate"
    region = var.region
  }
}

# 02-cluster 레이어 참조
data "terraform_remote_state" "cluster" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "cluster/terraform.tfstate"
    region = var.region
  }
}

# 로컬 변수로 매핑
locals {
  # Network 출력
  vpc_id = data.terraform_remote_state.network.outputs.vpc_id

  # Cluster 출력
  blue_cluster_name = data.terraform_remote_state.cluster.outputs.cluster_names.blue

  green_cluster_name = data.terraform_remote_state.cluster.outputs.cluster_names.green
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  enable_blue_cluster  = var.enable_blue_cluster && local.blue_cluster_name != null
  enable_green_cluster = var.enable_green_cluster && local.green_cluster_name != null
}
```

### 변수 정의

```hcl
# 03-platform/variables.tf
variable "region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "eks-platform"
}

# 개발자 IAM ARNs (읽기 전용 접근)
variable "developer_arns" {
  description = "IAM ARNs for developers (read-only access)"
  type        = list(string)
  default     = []
}

# 관리자 IAM ARNs
# 클러스터 활성화 여부 (02-cluster에서 상속)
variable "enable_blue_cluster" {
  description = "Enable Blue cluster resources"
  type        = bool
  default     = true
}

variable "enable_green_cluster" {
  description = "Enable Green cluster resources"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

locals {
  default_tags = {
    ManagedBy   = "terraform"
    Project     = var.project_name
    Environment = var.environment
    Layer       = "platform"
  }

  merged_tags = merge(local.default_tags, var.common_tags)
}

variable "enable_coredns_addon" {
  description = "Retain a CoreDNS deployment for non-Auto Mode nodes in a mixed cluster"
  type = bool
  default = false
}

variable "coredns_addon_version" {
  description = "Pin a CoreDNS EKS addon version verified for this Kubernetes version and region"
  type        = string
  default     = null
  validation {
    condition     = !var.enable_coredns_addon || can(regex("^v[0-9]+\\.[0-9]+\\.[0-9]+-eksbuild\\.[0-9]+$", var.coredns_addon_version))
    error_message = "Select a compatible vX.Y.Z-eksbuild.N version with describe-addon-versions."
  }
}
```

### Pod Identity 및 Add-ons 구성

```hcl
# 03-platform/main.tf

# ============================================
# Pod Identity Associations
# ============================================

# External Secrets Operator용 Pod Identity (Blue)
module "external_secrets_pod_identity_blue" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "2.9.0"

  count = local.enable_blue_cluster ? 1 : 0

  name = "${local.blue_cluster_name}-external-secrets"

  trust_policy_conditions = [
    { test = "StringEquals", variable = "aws:RequestTag/eks-cluster-arn", values = ["arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${local.blue_cluster_name}"] },
    { test = "StringEquals", variable = "aws:RequestTag/kubernetes-namespace", values = ["external-secrets"] },
    { test = "StringEquals", variable = "aws:RequestTag/kubernetes-service-account", values = ["external-secrets"] }
  ]

  use_name_prefix      = false
  attach_custom_policy = true
  policy_statements = [
    {
      sid    = "AllowSecretsManagerAccess"
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
      ]
      resources = [
        "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      ]
    },
    {
      sid    = "AllowSSMParameterAccess"
      effect = "Allow"
      actions = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ]
      resources = [
        "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      ]
    }
  ]

  associations = {
    external-secrets = {
      cluster_name    = local.blue_cluster_name
      namespace       = "external-secrets"
      service_account = "external-secrets"
    }
  }

  tags = merge(local.merged_tags, {
    Cluster   = "blue"
    Component = "external-secrets"
  })
}

# External Secrets Operator용 Pod Identity (Green)
module "external_secrets_pod_identity_green" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "2.9.0"

  count = local.enable_green_cluster ? 1 : 0

  name = "${local.green_cluster_name}-external-secrets"

  trust_policy_conditions = [
    { test = "StringEquals", variable = "aws:RequestTag/eks-cluster-arn", values = ["arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${local.green_cluster_name}"] },
    { test = "StringEquals", variable = "aws:RequestTag/kubernetes-namespace", values = ["external-secrets"] },
    { test = "StringEquals", variable = "aws:RequestTag/kubernetes-service-account", values = ["external-secrets"] }
  ]

  use_name_prefix      = false
  attach_custom_policy = true
  policy_statements = [
    {
      sid    = "AllowSecretsManagerAccess"
      effect = "Allow"
      actions = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
      ]
      resources = [
        "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      ]
    },
    {
      sid    = "AllowSSMParameterAccess"
      effect = "Allow"
      actions = [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ]
      resources = [
        "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      ]
    }
  ]

  associations = {
    external-secrets = {
      cluster_name    = local.green_cluster_name
      namespace       = "external-secrets"
      service_account = "external-secrets"
    }
  }

  tags = merge(local.merged_tags, {
    Cluster   = "green"
    Component = "external-secrets"
  })
}

# ============================================
# EKS Add-ons
# ============================================

# ============================================
# Access Entries (개발자 접근 권한)
# ============================================

# Blue 클러스터 - 개발자 읽기 전용 접근
resource "aws_eks_access_entry" "developers_blue" {
  for_each = local.enable_blue_cluster ? toset(var.developer_arns) : []

  cluster_name  = local.blue_cluster_name
  principal_arn = each.value
  type          = "STANDARD"

  tags = merge(local.merged_tags, {
    Cluster = "blue"
    Role    = "developer"
  })
}

resource "aws_eks_access_policy_association" "developers_blue_view" {
  for_each = local.enable_blue_cluster ? toset(var.developer_arns) : []

  cluster_name  = local.blue_cluster_name
  principal_arn = aws_eks_access_entry.developers_blue[each.key].principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }
}

# Green 클러스터 - 개발자 읽기 전용 접근
resource "aws_eks_access_entry" "developers_green" {
  for_each = local.enable_green_cluster ? toset(var.developer_arns) : []

  cluster_name  = local.green_cluster_name
  principal_arn = each.value
  type          = "STANDARD"

  tags = merge(local.merged_tags, {
    Cluster = "green"
    Role    = "developer"
  })
}

resource "aws_eks_access_policy_association" "developers_green_view" {
  for_each = local.enable_green_cluster ? toset(var.developer_arns) : []

  cluster_name  = local.green_cluster_name
  principal_arn = aws_eks_access_entry.developers_green[each.key].principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }
}


resource "aws_eks_addon" "coredns_blue" {
  count                       = local.enable_blue_cluster && var.enable_coredns_addon ? 1 : 0
  cluster_name                = local.blue_cluster_name
  addon_name                  = "coredns"
  addon_version               = var.coredns_addon_version
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
  tags                        = local.merged_tags
}

resource "aws_eks_addon" "coredns_green" {
  count                       = local.enable_green_cluster && var.enable_coredns_addon ? 1 : 0
  cluster_name                = local.green_cluster_name
  addon_name                  = "coredns"
  addon_version               = var.coredns_addon_version
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
  tags                        = local.merged_tags
}
# If named secrets or SecureString parameters use customer-managed KMS keys,
# grant this ESO role kms:Decrypt on the required key ARNs and allow it in the key policy.
```

### 출력 정의

```hcl
# 03-platform/outputs.tf

# ArgoCD Pod Identity Role ARNs
# External Secrets Role ARNs
output "external_secrets_role_arn_blue" {
  description = "External Secrets IAM role ARN for Blue cluster"
  value       = local.enable_blue_cluster ? module.external_secrets_pod_identity_blue[0].iam_role_arn : null
}

output "external_secrets_role_arn_green" {
  description = "External Secrets IAM role ARN for Green cluster"
  value       = local.enable_green_cluster ? module.external_secrets_pod_identity_green[0].iam_role_arn : null
}

# EBS CSI Driver Add-on Status

output "coredns_addon_version_blue" {
  value = local.enable_blue_cluster && var.enable_coredns_addon ? aws_eks_addon.coredns_blue[0].addon_version : null
}

output "coredns_addon_version_green" {
  value = local.enable_green_cluster && var.enable_coredns_addon ? aws_eks_addon.coredns_green[0].addon_version : null
}
```

***

## 레이어 간 연계

### terraform\_remote\_state 데이터 소스 패턴

각 레이어는 이전 레이어의 root output을 읽습니다. 단, `terraform_remote_state`를 읽는 권한은 실제 state snapshot 전체에 접근할 수 있는 권한이므로 output만 공개하는 보안 경계가 아닙니다. 신뢰 경계가 다른 팀에는 별도 게시한 SSM parameter 등 필요한 값만 제공하는 방식을 검토합니다.

```hcl
# 기본 패턴
data "terraform_remote_state" "previous_layer" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "layer-name/terraform.tfstate"
    region = var.region
  }
}

# 출력값 접근
locals {
  value_from_previous = data.terraform_remote_state.previous_layer.outputs.output_name
}
```

### 데이터 흐름 다이어그램

![계정·환경별 local state로 S3 버킷을 bootstrap하고, Network·Cluster·Platform이 각자의 S3 state와 출력 계약을 사용하는 구조.](../.gitbook/assets/ko-ops-01-infrastructure-setup-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-01-infrastructure-setup-0.html)

### 상태 관리 모범 사례

1. **절대 수동으로 상태 파일을 편집하지 마세요**
   * `terraform state mv`, `terraform import` 명령 사용
2. **상태 파일 버전 관리**
   * S3 버전 관리로 state 복구에 활용. state 버전 복원이 AWS 리소스 롤백을 수행하지는 않음
   * 주기적인 상태 백업 권장
3.  **Lock 충돌 해결**

    ```bash
    # Lock 강제 해제 (주의: 다른 작업이 없는지 확인 후)
    terraform force-unlock LOCK_ID
    ```
4. **출력값 변경 시 주의**
   * 하위 레이어에서 참조하는 출력값 변경 시 영향 범위 확인
   * 출력값 삭제 전 의존성 제거 필요
5. **S3 네이티브 잠금 사용** (Terraform 1.10+)
   * `use_lockfile = true` 설정으로 S3 conditional writes 기반 잠금 활성화
   * DynamoDB 테이블 생성/관리 불필요
   * 기존 DynamoDB 잠금은 전환 기간에 두 잠금을 함께 구성할 수 있음. 모든 실행기를 호환 버전으로 맞춘 뒤 제거하며, 잠금 방식만 바꾸는 것은 state 저장 위치 이동이 아님

***

## 검증

### 레이어별 적용 순서

새 프로젝트용 예제입니다. AWS CLI·Terraform·jq와 배포 권한이 필요합니다. `DOCS_ADMIN_ARN`에 실제 관리자 IAM ARN을 먼저 지정합니다. 아래 절차는 리소스를 생성하므로 각 `terraform apply`가 보여 주는 plan을 검토하고 직접 승인합니다. 순수 Auto Mode는 CoreDNS add-on을 끕니다. 혼합 클러스터로 확장할 때만 `DOCS_ENABLE_COREDNS_ADDON=true`를 지정해 호환 버전을 조회·고정합니다. 환경별 파일에는 필수 값만 생성하므로 추가 태그·팀 권한은 plan 전에 해당 입력에 병합합니다.

backend의 bucket/region은 생성된 JSON으로 전달하고 `TF_DATA_DIR`를 계정·환경·root별로 분리합니다. 한국어 예제의 Cluster root는 두 클러스터를 함께 관리합니다. bootstrap state와 `.terraform-data/`, plan 파일은 Git에 넣지 않고 보호·백업합니다. 기존 state의 위치나 계정을 바꾸는 migration 명령으로 이 절차를 재사용하지 않습니다.

```bash
set -euo pipefail
# Run from the NEW eks-terraform project containing the documented files.
DOCS_ROOT="$PWD"
DOCS_ENV="dev"
DOCS_REGION="ap-northeast-2"
DOCS_PROJECT="eks-platform"
DOCS_K8S_VERSION="1.36"
: "${DOCS_ADMIN_ARN:?Set an existing IAM administrator role ARN}"
DOCS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
mkdir -p environments ".bootstrap-state/$DOCS_ACCOUNT_ID"
chmod 700 .bootstrap-state ".bootstrap-state/$DOCS_ACCOUNT_ID"

jq -n --arg region "$DOCS_REGION" --arg env "$DOCS_ENV" --arg project "$DOCS_PROJECT" \
  '{region:$region, environment:$env, project_name:$project}' \
  > "environments/$DOCS_ENV.tfvars.json"

# Pure Auto Mode uses node-local CoreDNS. Set true only for mixed/non-Auto nodes.
DOCS_ENABLE_COREDNS_ADDON="${DOCS_ENABLE_COREDNS_ADDON:-false}"
case "$DOCS_ENABLE_COREDNS_ADDON" in true|false) ;; *) exit 2 ;; esac
if [[ "$DOCS_ENABLE_COREDNS_ADDON" == true ]]; then
  DOCS_COREDNS_VERSION="$(aws eks describe-addon-versions --region "$DOCS_REGION" \
    --addon-name coredns --kubernetes-version "$DOCS_K8S_VERSION" --output json | \
    jq -er --arg version "$DOCS_K8S_VERSION" '
      [.addons[0].addonVersions[]
       | select(any(.compatibilities[]; .clusterVersion == $version and .defaultVersion == true))
       | .addonVersion] | first // empty
    ')"
  jq -n --arg version "$DOCS_COREDNS_VERSION" \
    '{enable_coredns_addon:true, coredns_addon_version:$version}' \
    > "environments/$DOCS_ENV.platform.tfvars.json"
else
  jq -n '{enable_coredns_addon:false}' > "environments/$DOCS_ENV.platform.tfvars.json"
fi

jq -n --arg admin "$DOCS_ADMIN_ARN" --arg version "$DOCS_K8S_VERSION" \
  '{cluster_admin_arns:[$admin], kubernetes_version:$version}' > "environments/$DOCS_ENV.cluster.tfvars.json"

# Isolate local bootstrap state by account and environment.
export TF_DATA_DIR="$DOCS_ROOT/.terraform-data/$DOCS_ACCOUNT_ID/$DOCS_ENV/bootstrap"
terraform -chdir=00-shared init \
  -backend-config="path=$DOCS_ROOT/.bootstrap-state/$DOCS_ACCOUNT_ID/$DOCS_ENV.tfstate"
terraform -chdir=00-shared plan -var-file="../environments/$DOCS_ENV.tfvars.json"
# Review the plan. This apply presents its own plan and asks for confirmation.
terraform -chdir=00-shared apply -var-file="../environments/$DOCS_ENV.tfvars.json"
DOCS_STATE_BUCKET="$(terraform -chdir=00-shared output -raw state_bucket_name)"
jq -n --arg bucket "$DOCS_STATE_BUCKET" --arg region "$DOCS_REGION" \
  '{bucket:$bucket, region:$region}' > "environments/$DOCS_ENV.backend.json"

apply_layer() {
  local layer="$1" key="$2" suffix="$3"
  shift 3
  export TF_DATA_DIR="$DOCS_ROOT/.terraform-data/$DOCS_ACCOUNT_ID/$DOCS_ENV/$suffix"
  terraform -chdir="$layer" init \
    -backend-config="../environments/$DOCS_ENV.backend.json" -backend-config="key=$key"
  terraform -chdir="$layer" validate
  terraform -chdir="$layer" plan -var-file="../environments/$DOCS_ENV.tfvars.json" "$@"
  # Review the new plan and explicitly confirm apply.
  terraform -chdir="$layer" apply -var-file="../environments/$DOCS_ENV.tfvars.json" "$@"
}

apply_layer 01-network network/terraform.tfstate network

apply_layer 02-cluster cluster/terraform.tfstate cluster   -var-file="../environments/$DOCS_ENV.cluster.tfvars.json"
apply_layer 03-platform platform/terraform.tfstate platform   -var-file="../environments/$DOCS_ENV.platform.tfvars.json"
```

### kubectl 검증

선택한 관리자 principal로 인증한 AWS CLI 환경에서 실행합니다. EKS access policy는 IAM의 `eks:DescribeCluster` 권한을 대신하지 않습니다. Terraform 실행자 자동 관리자 권한은 꺼져 있으므로, 필요한 경우 관리자 프로파일 또는 허용된 AssumeRole 구성을 사용합니다. 아래는 기본값대로 두 클러스터를 생성한 경우이며 비활성 클러스터는 제외합니다. StorageClass는 별도 GitOps 설정 후 확인합니다.

```bash
for DOCS_COLOR in blue green; do
  DOCS_CLUSTER_NAME="${DOCS_PROJECT}-${DOCS_ENV}-${DOCS_COLOR}"
  DOCS_CONTEXT="${DOCS_COLOR}-${DOCS_ENV}"
  aws eks update-kubeconfig --region "$DOCS_REGION" \
    --name "$DOCS_CLUSTER_NAME" --alias "$DOCS_CONTEXT"
  kubectl --context "$DOCS_CONTEXT" get nodes
  kubectl --context "$DOCS_CONTEXT" get nodepools
  kubectl --context "$DOCS_CONTEXT" get pods -n kube-system
  aws eks list-pod-identity-associations --region "$DOCS_REGION" \
    --cluster-name "$DOCS_CLUSTER_NAME"
done
```

### 기본 워크로드·DNS Smoke Test

명시한 kube-context마다 고유한 임시 네임스페이스와 DNS Job을 생성합니다. 외부 LB나 모든 애플리케이션 의존성을 검증하는 스크립트는 아닙니다. 정리 전에 namespace UID를 확인하며, 배포·DNS·시스템 Pod 검사 실패는 0이 아닌 종료 코드로 반환합니다. Docker Hub 접근이 없으면 `DOCS_TEST_IMAGE`로 승인된 미러 이미지를 지정합니다.

```bash
#!/usr/bin/env bash
set -euo pipefail

if (( $# == 0 )); then
  echo "Usage: $0 <kube-context> [<kube-context> ...]" >&2
  exit 2
fi
command -v kubectl >/dev/null
command -v jq >/dev/null
DOCS_TEST_IMAGE="${DOCS_TEST_IMAGE:-docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662}"

smoke_cluster() (
  set -euo pipefail
  context="$1"
  namespace=""
  namespace_uid=""
  cleanup() {
    [[ -n "$namespace" ]] || return 0
    current_uid="$(kubectl --context "$context" get namespace "$namespace" \
      --ignore-not-found -o jsonpath='{.metadata.uid}')" || return 1
    [[ -n "$current_uid" ]] || return 0
    if [[ "$current_uid" != "$namespace_uid" ]]; then
      echo "Cleanup skipped: namespace identity changed: $namespace" >&2
      return 0
    fi
    kubectl --context "$context" delete namespace "$namespace" --timeout=120s
  }
  trap 'result=$?; cleanup || result=1; exit "$result"' EXIT

  kubectl --context "$context" version -o json | jq -er '.serverVersion.gitVersion'
  # Mixed clusters retain the Deployment; pure Auto Mode can have none.
  coredns_deployment="$(kubectl --context "$context" get deployment coredns \
    -n kube-system --ignore-not-found -o name)"
  if [[ -n "$coredns_deployment" ]]; then
    kubectl --context "$context" rollout status deployment/coredns -n kube-system --timeout=600s
  fi
  kubectl --context "$context" get nodepools -o json | jq -e '
    any(.items[]; any(.status.conditions[]?; .type == "Ready" and .status == "True"))
  ' >/dev/null

  record="$(kubectl --context "$context" create -f - -o json <<'JSON'
{"apiVersion":"v1","kind":"Namespace","metadata":{"generateName":"docs-smoke-","labels":{"pod-security.kubernetes.io/enforce":"restricted"}}}
JSON
  )"
  namespace="$(jq -er '.metadata.name' <<<"$record")"
  namespace_uid="$(jq -er '.metadata.uid' <<<"$record")"

  jq -n --arg namespace "$namespace" --arg image "$DOCS_TEST_IMAGE" '{
    apiVersion: "batch/v1", kind: "Job",
    metadata: {name: "dns-check", namespace: $namespace},
    spec: {
      backoffLimit: 0, activeDeadlineSeconds: 300,
      template: {spec: {
        restartPolicy: "Never", automountServiceAccountToken: false,
        securityContext: {runAsNonRoot: true, runAsUser: 65534, seccompProfile: {type: "RuntimeDefault"}},
        containers: [{name: "check", image: $image,
          command: ["sh", "-ec", "nslookup kubernetes.default.svc.cluster.local"],
          securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, capabilities: {drop: ["ALL"]}},
          resources: {requests: {cpu: "10m", memory: "16Mi"}, limits: {cpu: "100m", memory: "64Mi"}}
        }]
      }}
    }
  }' | kubectl --context "$context" create -f -

  if ! kubectl --context "$context" wait --for=condition=complete job/dns-check \
    -n "$namespace" --timeout=360s; then
    kubectl --context "$context" describe pods -n "$namespace" >&2 || true
    kubectl --context "$context" logs job/dns-check -n "$namespace" --tail=100 >&2 || true
    exit 1
  fi
  kubectl --context "$context" logs job/dns-check -n "$namespace" --tail=30
  kubectl --context "$context" get pods -n kube-system -o json | jq -e '
    all(.items[]; .status.phase == "Succeeded" or
      any(.status.conditions[]?; .type == "Ready" and .status == "True"))
  ' >/dev/null
  echo "Workload scheduling and cluster DNS passed: $context"
)

for context in "$@"; do
  smoke_cluster "$context"
done
```

위 코드를 `smoke-test.sh`로 저장한 뒤 생성한 컨텍스트만 명시합니다.

```bash
bash smoke-test.sh "blue-${DOCS_ENV}" "green-${DOCS_ENV}"
```

### 트러블슈팅 가이드

#### 일반적인 문제와 해결 방법

| 문제                          | 원인               | 해결 방법                                      |
| --------------------------- | ---------------- | ------------------------------------------ |
| `terraform_remote_state` 오류 | S3 버킷 접근 권한 없음   | IAM 정책 확인, 버킷 이름 확인                        |
| EKS 클러스터 생성 실패              | 서브넷 태그 누락        | 01-network에서 EKS 태그 확인                     |
| NodePool이 노드를 생성하지 않음       | Auto Mode 미활성화   | `compute_config.enabled = true` 확인 |
| Pod Identity 연결 실패 | association/SA·SDK·trust·agent 경로 문제 | Pod Identity는 OIDC provider를 요구하지 않음. Auto Mode 내장 지원과 eks-auth 접근 확인 |

#### 디버깅 명령어

```bash
# Terraform 상태 확인
terraform state list
terraform state show 'module.eks_blue[0].aws_eks_cluster.this[0]'

# EKS 클러스터 상태 확인
aws eks describe-cluster --name eks-platform-prod-blue

# 클러스터 인증 문제 디버깅
aws eks get-token --cluster-name eks-platform-prod-blue --query status.expirationTimestamp --output text

# Pod Identity 연결 확인
aws eks list-pod-identity-associations \
    --cluster-name eks-platform-prod-blue

# CloudWatch 로그 확인
aws logs describe-log-groups \
    --log-group-name-prefix /aws/eks/eks-platform-prod
```

***

## 다음 단계

이 인프라 구성을 완료한 후 다음 문서를 참조하세요:

* [**NLB 가중치 라우팅과 블루/그린 클러스터**](02-infrastructure-advanced.md): NLB를 사용한 트래픽 분배 및 장애 조치
* [**GitOps 멀티 클러스터 배포**](04-gitops-multi-cluster.md): ArgoCD를 사용한 Kubernetes 리소스 관리
* [**EKS Auto Mode 시작하기**](../eks-auto-mode/01-getting-started.md): Auto Mode 상세 설정
* [**EKS 보안**](../eks/05-eks-security.md): 클러스터 보안 모범 사례

***

## 참고 자료

* [Terraform AWS EKS Module](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest)
* [Terraform AWS VPC Module](https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest)
* [EKS Auto Mode 공식 문서](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
* [EKS Pod Identity 문서](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
* [Terraform Backend Configuration](https://developer.hashicorp.com/terraform/language/settings/backends/s3)
