# EKS 集群创建 - 第 4 部分：使用 Terraform 创建集群

> **支持的版本**: Kubernetes 1.31, 1.32, 1.33
> **最后更新**: February 23, 2026

## 生产级 Terraform 项目结构

Terraform 是一种基础设施即代码工具，使你能够以可重复且受版本控制的方式定义、预置和管理 EKS 集群。本指南使用 **AWS provider ~> 6.0** 和社区 **EKS module ~> 21.0**，它们支持最新的 EKS 功能，包括 Auto Mode、Hybrid Nodes、Pod Identity 和基于 API 的 Access Entries。

在生产环境中，只有一个 state file 的单一扁平 Terraform 目录会带来问题：VPC 变更可能意外销毁你的集群，随着项目增长，每次 `terraform plan` 都会耗时更久，并且不同团队无法独立工作。**多层架构** 通过按变更频率和所有权将基础设施拆分到独立的 state files 来解决这个问题。

### 3 层架构

```
eks-terraform/
├── 01-network/                   # Layer 1: VPC and networking
│   ├── providers.tf
│   ├── backend.tf                # S3 key: eks/network/terraform.tfstate
│   ├── variables.tf
│   ├── main.tf                   # VPC module
│   └── outputs.tf                # vpc_id, subnet_ids → remote state
├── 02-cluster/                   # Layer 2: EKS cluster and node groups
│   ├── providers.tf
│   ├── backend.tf                # S3 key: eks/cluster/terraform.tfstate
│   ├── data.tf                   # terraform_remote_state → 01-network
│   ├── variables.tf
│   ├── main.tf                   # EKS module, node groups, core add-ons
│   └── outputs.tf                # cluster_name, endpoint → remote state
└── 03-platform/                  # Layer 3: Add-ons, RBAC, Pod Identity
    ├── providers.tf
    ├── backend.tf                # S3 key: eks/platform/terraform.tfstate
    ├── data.tf                   # terraform_remote_state → 01-network, 02-cluster
    ├── variables.tf
    ├── addons.tf                 # EBS CSI driver, additional add-ons
    ├── pod-identity.tf           # Pod Identity associations
    └── access-entries.tf         # Developer/viewer access entries
```

### 为什么要分层

| 层 | 变更频率 | 负责人 | 影响范围 |
|-------|---------|-------|--------------|
| 01-network | 很少 | Infra team | 仅 VPC、subnets |
| 02-cluster | 每月 | Platform team | EKS 集群、nodes |
| 03-platform | 每周 | Platform / App team | Add-ons、RBAC、Pod Identity |

每一层都有自己的 S3 state file，并且可以独立 plan/apply。对 `03-platform` 中某个 add-on 的变更绝不会冒着触碰 VPC 或集群本身的风险。

### 共享 S3 Backend

所有层共享一个带有 DynamoDB locking 的 S3 bucket，但每一层都会写入 **不同的 state key**：

```hcl
# Example: 01-network/backend.tf
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

各层通过 `terraform_remote_state` data sources 相互引用；它们会从另一层的 state file 读取 outputs，而不会依赖 Terraform 代码本身。

---

## 第 1 层：Network (01-network)

这一层预置 VPC、subnets、NAT gateways 以及所有网络前置条件。它很少变化，通常由基础设施团队负责。

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

> **注意**: 使用 EKS module ~> 21.0 和 AWS Load Balancer Controller 时，subnets 上不再需要 `kubernetes.io/cluster/<cluster-name>` tag。`kubernetes.io/role/elb` 和 `kubernetes.io/role/internal-elb` tags 足以用于 subnet discovery。

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

## 第 2 层：EKS 集群 (02-cluster)

这一层预置 EKS 集群、managed node groups 和核心 add-ons。它通过 `terraform_remote_state` 从第 1 层读取网络信息。

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

  # Cluster endpoint access
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  # Use API-based authentication (replaces aws-auth ConfigMap)
  authentication_mode = "API"

  # Grant the Terraform caller cluster admin access
  enable_cluster_creator_admin_permissions = true

  # EKS Add-ons (core only — additional add-ons go in 03-platform)
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

  # Managed Node Groups
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

  # CloudWatch Logging
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

## 第 3 层：Platform (03-platform)

这一层管理核心集合之外的 add-ons、Pod Identity associations 和 access entries。它变化最频繁，并且可以独立应用，而不会影响集群或网络。

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
# Example: S3 access for application pods
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

# Associate the role with a Kubernetes service account
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

# Developer with namespace-scoped access
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

# Read-only access
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

## EKS Pod Identity

EKS Pod Identity 是为 Kubernetes workloads 授予 AWS 权限的推荐方法。它取代 IAM Roles for Service Accounts (IRSA)，并且不需要 OIDC provider。

### Pod Identity 的工作原理

1. `eks-pod-identity-agent` add-on 作为 DaemonSet 在每个 node 上运行（在第 2 层安装）。
2. 创建一个带有 Pod Identity trust policy 的 IAM role（在第 3 层）。
3. 通过 `aws_eks_pod_identity_association` 将该 role 与 Kubernetes service account 关联。
4. 使用该 service account 的 Pods 会自动获得临时 AWS credentials。

上面 `03-platform/pod-identity.tf` 中展示的 Pod Identity resources 遵循此模式。IAM role 的 trust policy 使用 `pods.eks.amazonaws.com` 作为 principal，并且 `sts:TagSession` 会启用带有 cluster、namespace 和 service account metadata 的自动 session tagging。

### Pod Identity vs IRSA

| 功能 | Pod Identity | IRSA |
|---------|-------------|------|
| 是否需要 OIDC provider | 否 | 是 |
| Cross-account support | 通过 `sts:TagSession` 内置支持 | 每个 account 都需要 OIDC trust |
| 设置复杂度 | 低 — 单个 association | 中 — OIDC、role、annotation |
| Session tags | 自动（cluster、namespace、SA） | 不可用 |
| 可复用性 | 同一个 role 可用于多个 clusters | 每个 cluster OIDC 一个 role |

> **建议**: 对所有新 workloads 使用 Pod Identity。IRSA 仍然为了向后兼容而受支持。

---

## EKS Auto Mode 集群

EKS Auto Mode 将 node provisioning、scaling 和 OS management 完全委托给 AWS。无需定义 managed node groups —— EKS 会自动预置和管理 compute。使用 Auto Mode 时，请将标准 `02-cluster/main.tf` 替换为以下变体：

```hcl
# 02-cluster/main.tf (Auto Mode variant)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  # Enable Auto Mode
  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # Auto Mode manages these add-ons — do not bootstrap self-managed ones
  bootstrap_self_managed_addons = false

  tags = var.tags
}
```

### 关键要点

- **`cluster_compute_config.enabled = true`** 激活 Auto Mode。
- **`node_pools`** 指定要启用哪些内置 node pools（`general-purpose`、`system`）。
- **`bootstrap_self_managed_addons = false`** 防止冲突 —— Auto Mode 会自动管理核心 add-ons（CoreDNS、kube-proxy、VPC CNI）。
- 使用 Auto Mode 时，你 **不** 定义 `eks_managed_node_groups`。
- Auto Mode 会从 node pools 预置 EC2 instances，并处理 OS patching、scaling 和 lifecycle。

---

## EKS Hybrid Nodes

EKS Hybrid Nodes 允许你将本地或边缘服务器作为 worker nodes 加入 EKS 集群，同时将 EKS control plane 保持在 AWS 中。使用 Hybrid Nodes 时，请将标准 `02-cluster/main.tf` 替换为以下变体：

```hcl
# 02-cluster/main.tf (Hybrid Nodes variant)
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids

  authentication_mode                      = "API"
  enable_cluster_creator_admin_permissions = true

  # Hybrid Nodes network configuration
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

  # Access entry for hybrid nodes
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

# Security group rules for hybrid node traffic
resource "aws_security_group_rule" "hybrid_node_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["172.16.0.0/16"]
  security_group_id = module.eks.cluster_security_group_id
  description       = "Allow hybrid nodes to communicate with the API server"
}

resource "aws_security_group_rule" "hybrid_node_kubelet" {
  type              = "ingress"
  from_port         = 10250
  to_port           = 10250
  protocol          = "tcp"
  cidr_blocks       = ["172.16.0.0/16"]
  security_group_id = module.eks.cluster_security_group_id
  description       = "Allow kubelet communication from hybrid nodes"
}
```

### 关键要点

- **`remote_network_config`** 定义本地 nodes 和 pods 的 CIDR ranges。
- Hybrid nodes 通过带有 access entry type `HYBRID_LINUX` 的 IAM role 进行身份验证。
- Security group rules 必须允许来自本地 CIDRs 的流量访问 EKS API server (443) 和 kubelet (10250)。
- VPC CNI 不会在 hybrid nodes 上使用 —— 你必须在本地侧配置替代 CNI（例如 Cilium）。

---

## Add-on 管理

EKS add-ons 是在集群上运行的托管组件。在多层架构中，**核心 add-ons**（coredns、vpc-cni、kube-proxy、eks-pod-identity-agent）定义在 `02-cluster` 中，因为它们是集群运行所必需的；而 **额外 add-ons**（EBS CSI 等）则在 `03-platform` 中管理。

### 关键选项

| 选项 | 描述 |
|--------|-------------|
| `most_recent` | 始终使用与集群 Kubernetes 版本兼容的最新版本。 |
| `before_compute` | 在预置 node groups 之前安装 add-on。`vpc-cni` 和 `eks-pod-identity-agent` 需要此选项，以便 nodes 能正确启动。 |
| `configuration_values` | add-on 特定设置的 JSON 字符串（例如 VPC CNI prefix delegation）。 |
| `service_account_role_arn` | 需要 AWS API 访问权限的 add-ons 的 IAM role ARN（例如 EBS CSI driver）。同时适用于 IRSA 和 Pod Identity。 |
| `resolve_conflicts_on_create` | 设置为 `"OVERWRITE"`，以在迁移期间替换现有 self-managed versions。 |
| `resolve_conflicts_on_update` | 设置为 `"OVERWRITE"`，以强制更新存在冲突的 add-on configuration。 |

### Add-ons 的 Pod Identity

某些 add-ons 直接支持 Pod Identity associations。`03-platform/addons.tf` 中的 EBS CSI driver 配置展示了使用 `pod_identity_association` 的这种模式：

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

## 基于 Access Entry 的访问控制

EKS 通过 Access Entries 支持基于 API 的身份验证，取代旧版 `aws-auth` ConfigMap。在多层架构中，初始 cluster admin access 在 `02-cluster` 中配置（通过 `enable_cluster_creator_admin_permissions`），而面向开发者和查看者的其他 access entries 在 `03-platform/access-entries.tf` 中管理。

### 身份验证模式

| 模式 | 描述 |
|------|-------------|
| `API` | 仅 Access Entries（推荐用于新集群）。 |
| `API_AND_CONFIG_MAP` | 同时使用 Access Entries 和 `aws-auth` ConfigMap（迁移期）。 |
| `CONFIG_MAP` | 仅旧版 `aws-auth`（不推荐）。 |

### 可用的 Access Policy ARNs

| Policy | ARN | 描述 |
|--------|-----|-------------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | 完整 cluster access |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Admin access（无 IAM management） |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | 对大多数 resources 的读/写权限 |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | 只读 access |

---

## 部署工作流

### 按层顺序部署

每一层都必须按顺序初始化并应用，因为后面的层依赖前面层的 state outputs：

```bash
# Layer 1: Network
cd eks-terraform/01-network
terraform init
terraform plan
terraform apply

# Layer 2: Cluster
cd ../02-cluster
terraform init
terraform plan
terraform apply

# Layer 3: Platform
cd ../03-platform
terraform init
terraform plan
terraform apply
```

> **注意**: EKS 集群创建（第 2 层）通常需要 10-15 分钟。第 1 层和第 3 层更快。

### 配置 kubeconfig

第 2 层完成后，配置 `kubectl` access：

```bash
cd eks-terraform/02-cluster

aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region)
```

### 验证集群

```bash
# Check node status
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Verify EKS add-ons
kubectl get daemonsets -n kube-system
```

健康集群的预期输出：

```
NAME                              STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
ip-10-0-2-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
```

### 按相反顺序销毁

要删除所有 resources，请按相反顺序销毁各层，以便在删除依赖的 resources 之前先移除依赖关系：

```bash
# Layer 3: Platform
cd eks-terraform/03-platform
terraform destroy

# Layer 2: Cluster
cd ../02-cluster
terraform destroy

# Layer 1: Network
cd ../01-network
terraform destroy
```

> **警告**: `terraform destroy` 会删除由该层 state 管理的所有 resources。销毁 cluster layer 前，请确保没有关键 workloads 正在运行。

---

## 最佳实践

### State 管理

多层架构已经使用按层划分的 S3 state keys 和 DynamoDB locking。其他建议：

- 在 S3 bucket 上 **启用 versioning**，以便从意外的 state 损坏中恢复。
- 使用 IAM policies **限制 bucket access** —— 只有 CI/CD pipelines 和授权 operators 应该能够读/写 state。
- **切勿手动编辑 state files** —— 需要 state manipulation 时，请使用 `terraform state` commands。

### Module 版本控制

- 使用 `~>` 固定 module versions（例如 `~> 21.0`），以允许 patch updates，同时防止 breaking changes。
- 升级 major versions 前查看 module CHANGELOG。
- 先在非生产环境中测试升级。

### 环境隔离

使用以下方法之一隔离环境：

| 方法 | 优点 | 缺点 |
|----------|------|------|
| **独立目录** | 清晰隔离，独立 state | 代码重复 |
| **Terraform workspaces** | 单一 codebase，易于切换 | 共享 backend，隔离有限 |
| **Terragrunt** | DRY configuration，强隔离 | 额外 tooling dependency |

在多层架构中，最常见的方法是 **每个环境使用独立目录**，其中每个环境都有自己的 `01-network/`、`02-cluster/`、`03-platform/` 树，以及不同的 variable values 和 state keys。

### Tagging 策略

应用一致的 tags，用于 cost allocation、compliance 和 resource management：

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

## 后续步骤

- [EKS 集群创建 - 第 1 部分：前置条件](./02-eks-cluster-creation-part1.md) — EKS 集群创建的前置条件
- [EKS 集群创建 - 第 2 部分：使用 eksctl 创建集群](./02-eks-cluster-creation-part2.md) — 使用 eksctl 创建 EKS 集群
- [EKS 集群创建 - 第 3 部分：使用 AWS Console 和 CLI 创建集群](./02-eks-cluster-creation-part3.md) — 通过 Console 和 CLI 创建 EKS 集群
- [EKS 集群创建 - 第 5 部分：集群访问、验证、升级和删除](./02-eks-cluster-creation-part5.md) — 管理 EKS 集群
- [EKS 网络 - 第 1 部分：基本概念和 VPC 配置](./03-eks-networking-part1.md) — EKS 网络基础
- [EKS 安全](./05-eks-security.md) — EKS 集群的安全配置

### 相关主题

- [ArgoCD](../gitops/argocd/README.md) — GitOps continuous deployment
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md) — 从 Kubernetes 管理 AWS resources
- [Karpenter](../autoscaling/02-karpenter.md) — Node provisioning automation
- [Kubernetes Extensions](../core/11-extending-kubernetes.md) — 使用 Operators 和 CRDs 扩展 Kubernetes API

## 术语表

| 术语 | 描述 |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service — AWS 提供的 managed Kubernetes service。 |
| **Terraform** | HashiCorp 提供的基础设施即代码工具，用于预置和管理 cloud resources。 |
| **Access Entry** | 一种基于 EKS API 的机制，用于向 IAM principals 授予 cluster access，取代 `aws-auth` ConfigMap。 |
| **Pod Identity** | 一项 EKS 功能，可在不需要 OIDC provider 的情况下向 pods 提供 AWS credentials。 |
| **Auto Mode** | 一种 EKS 模式，其中 AWS 完全管理 node provisioning、scaling 和 OS updates。 |
| **Hybrid Nodes** | 一项 EKS 功能，允许本地或边缘服务器作为 worker nodes 加入 EKS 集群。 |
| **IAM** | Identity and Access Management — 控制对 AWS resources 的访问。 |
| **VPC** | Virtual Private Cloud — AWS 中逻辑隔离的虚拟网络。 |
| **IRSA** | IAM Roles for Service Accounts — 通过 OIDC 向 pods 授予 AWS permissions 的旧方法。 |
| **Remote State** | 一项 Terraform 功能，允许一个 configuration 从另一个 configuration 的 state file 读取 outputs。 |

## 测验

要测试你在本章中学到的内容，请尝试 [EKS 集群创建 - 第 4 部分测验](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md)。
