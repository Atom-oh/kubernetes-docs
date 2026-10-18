# EKS 集群创建 - 第 4 部分：使用 Terraform 创建集群

> **示例版本**：Amazon EKS 1.36；Terraform 1.16.6；AWS provider 6.69.1；EKS module 21.29.0
> **最后更新**：2026年10月16日

## 三层 Terraform 示例

Terraform 以代码形式管理基础设施。本示例使用 AWS provider 6.x，并固定 EKS module **21.29.0** 和 VPC module **6.7.3**。HCL 已使用 Terraform 1.16.6 和 AWS provider 6.69.1 检查；未执行 AWS 部署，也未验证生产环境行为。原先 v20 风格的 `cluster_*` 输入与 module v21 不兼容：请使用下方列出的 v21 名称，例如 `name`、`kubernetes_version` 和 `addons`。

将状态拆分开来有助于团队按生命周期划分所有权并审查变更。但这不会消除依赖关系或运维影响：网络变更仍可能中断集群，附加组件或访问策略变更也可能影响所有工作负载。这只是示例结构，并非经过测试的生产架构。

### 三层架构

```
eks-terraform/
├── 01-network/                   # Layer 1: VPC and networking
│   ├── providers.tf
│   ├── backend.tf                # S3 key: eks/dev/network/terraform.tfstate
│   ├── variables.tf
│   ├── main.tf                   # VPC module
│   └── outputs.tf                # vpc_id, subnet_ids → remote state
├── 02-cluster/                   # Layer 2: EKS cluster and node groups
│   ├── providers.tf
│   ├── backend.tf                # S3 key: eks/dev/cluster/terraform.tfstate
│   ├── data.tf                   # terraform_remote_state → 01-network
│   ├── variables.tf
│   ├── main.tf                   # EKS module, node groups, core add-ons
│   └── outputs.tf                # cluster_name, endpoint → remote state
└── 03-platform/                  # Layer 3: Add-ons, RBAC, Pod Identity
    ├── providers.tf
    ├── backend.tf                # S3 key: eks/dev/platform/terraform.tfstate
    ├── data.tf                   # terraform_remote_state → 01-network, 02-cluster
    ├── variables.tf
    ├── addons.tf                 # EBS CSI driver, additional add-ons
    ├── pod-identity.tf           # Pod Identity associations
    └── access-entries.tf         # Developer/viewer access entries
```

### 为什么要拆分层

| 层 | 变更频率 | 所有者 | 影响范围 |
|-------|---------|-------|--------------|
| 01-network | 不频繁，仅作示例 | 基础设施团队 | VPC/子网和依赖它们的连接 |
| 02-cluster | 每月 | 平台团队 | EKS 集群、节点 |
| 03-platform | 每周 | 平台团队 / 应用团队 | 附加组件、RBAC、Pod Identity |

每一层都有独立的状态键和计划。仍然需要单独配置 IAM 权限和 CI 所有权，并协调跨层变更。状态拆分并不能保证附加组件变更不会影响集群行为。

### 共享 S3 后端

这些示例使用 S3 原生锁定，设置 `use_lockfile = true`（Terraform 1.10+），并为每个环境/层使用不同的键。请单独创建后端存储桶，启用版本控制和加密，并在初始化前替换所有 `REPLACE_WITH_YOUR_STATE_BUCKET`。仅授予所需状态键的访问权限，以及对其 `.tflock` 对象的 Get/Put/Delete 权限。DynamoDB 锁定已弃用；迁移现有后端时，应协调所有客户端，而不是直接删除锁表。

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

`terraform_remote_state` 会向 HCL 暴露根输出，但读取者可以获取**整个状态快照**，包括敏感值。它不会在不同项目之间创建 apply 顺序依赖。如果使用方团队不应读取整个状态，请通过单独受控的接口发布选定值。

---

## 第 1 层：网络（01-network）

此示例创建一个跨三个 AZ 的 VPC，并使用一个 NAT gateway 来缩小实验规模。单个 NAT 会造成 AZ 依赖，也可能产生跨 AZ 传输费用。用于生产之前，请评估具备 AZ 容错能力的出站设计、子网容量、DNS 和私有端点。

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
  version = "6.7.3"

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

> **子网发现**取决于 Load Balancer Controller 的版本、功能门控和子网适用规则，而非 Terraform EKS module 的版本。上面展示的角色标签有助于选择公有/私有子网；还应验证 AZ 覆盖范围、可用地址、路由以及任何集群标签筛选。

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

## 第 2 层：EKS 集群（02-cluster）

此层创建一个**新的传统 EC2 集群**、托管节点组和核心附加组件。请明确设置已存在的 `cluster_admin_role_arn`；Terraform 调用者不会自动获得 Kubernetes 管理权限。操作人员必须能够代入该角色。使用私有端点时，必须先准备好已连接且路由可达的管理环境，之后才能使用 kubectl 或安装平台组件。

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
  version = "21.29.0"

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

  # EKS Add-ons (core only; additional add-ons go in 03-platform)
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

节点组根磁盘使用启动模板的块设备映射；当此 module 使用其默认自定义启动模板时，`disk_size` 会被忽略。本示例使用 AWS 默认拥有的 Kubernetes API 信封加密。客户管理的 KMS key 是另一项独立设计选择。

部署前请检查 module 默认值：此固定版本的 module 为托管节点 IAM 角色配置了 ECR ReadOnly 和 IPv4 CNI 权限。这些默认值使本示例能够运行，但并不意味着它采用了生产环境的最小权限。建议使用专用的 CNI 身份，并明确审查节点角色（在 ECR PullOnly 足够时使用该权限）。节点组的 min/max 值并不会安装 autoscaler。

当 Terraform 重新评估其数据源时，默认兼容的附加组件构建版本可能会变化。请为目标集群确定并记录兼容的构建版本；如需保证可复现性，请使用 `addon_version` 固定版本。更新时保留经过审查的自定义配置。

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

## 第 3 层：平台（03-platform）

标准 EC2 平台层管理额外的附加组件、Pod Identity 关联以及开发者/只读用户访问。其状态单独存储，但其中的变更仍可能影响集群安全和工作负载可用性。以下 Auto Mode 和 Hybrid 替代方案需要选择不同的平台文件。

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

测试应用之前，请通过相应的 Kubernetes/GitOps 所有者创建新的 `app-dev` namespace 和 `app-sa` ServiceAccount。EKS 关联不会创建这两个对象。本示例仅授予对已批准存储桶中 `app/` 前缀的读取权限；存储桶策略、KMS 加密和跨账户访问可能需要额外的、经过审查的权限。请验证实际代入的角色，并在依赖其权限之前处理好 IAM/关联传播问题。

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

## EKS Pod Identity

EKS Pod Identity 是受支持工作负载的一种选项，并非 IRSA 的通用替代方案。它不需要 IAM OIDC provider。传统 Linux EC2、Auto Mode 以及经过适当配置的 Hybrid Nodes 都有受支持的使用方式；Fargate 和 Windows 则需要使用其他受支持的身份机制。IRSA 仍受支持。

### Pod Identity 的工作原理

1. 传统的受支持节点使用 Pod Identity Agent DaemonSet。Auto Mode 提供此功能；Hybrid Nodes 则需要按文档配置凭证文件和专用 DaemonSet。
2. 创建一个采用 Pod Identity 信任策略的 IAM 角色（位于第 3 层）。
3. 通过 `aws_eks_pod_identity_association` 将角色与 Kubernetes service account 关联。
4. 使用默认凭证链的兼容 SDK 会获取临时凭证。该链中排在此路径之前的现有静态凭证可能会覆盖此路径；请验证实际使用的身份。

上面的 `03-platform/pod-identity.tf` 中的 Pod Identity 资源遵循此模式。IAM 角色的信任策略将 `pods.eks.amazonaws.com` 设为主体，并通过 `sts:TagSession` 启用集群、namespace 和 service account 元数据的自动会话标记。

### Pod Identity 与 IRSA 对比

| 特性 | Pod Identity | IRSA |
|---------|-------------|------|
| 是否需要 OIDC provider | 否 | 是 |
| 跨账户支持 | 显式角色委派；在受支持时包括 `targetRoleArn`；需要配置信任/权限 | 目标账户中的 OIDC 信任或显式角色链式代入 |
| 设置复杂度 | 低（单个关联） | 中等（OIDC、角色、注释） |
| 会话标签 | 启用时自动添加 EKS 上下文标签 | 不会自动添加 EKS Pod Identity 上下文标签 |
| 可复用性 | 一个角色可供多个经过审查的关联使用 | 一个角色可信任多个经过明确限定的 OIDC issuer/subject |

> 请选择计算类型和 SDK 支持的身份机制。`sts:TagSession` 会添加标签，但它本身并不能建立跨账户信任。上述信任策略要求保持会话标签启用。module 可能会出于可选的 IRSA 用途创建 OIDC provider，这与 Pod Identity 无关。

---

## EKS Auto Mode 集群

请在**首次部署之前**选择此**新集群替代方案**；替换已 apply 的集群配置并不是迁移流程。Auto Mode 会管理计算和基础设施功能。其纯 Auto Mode 示例不定义托管节点组，并使用 module v21 的 `compute_config` 输入：

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

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

### 要点

- **`compute_config.enabled = true`** 会通过此 module 启用计算、负载均衡和块存储功能。请审查固定版本 module 创建的 IAM policy。
- **`node_pools`** 用于指定要启用的内置节点池（`general-purpose`、`system`）。
- Module v21 将底层的 `bootstrap_self_managed_addons` 硬编码为 `false`；它不是 module 输入。当前 Auto Mode 也包含集群 DNS，以及网络、存储和 Pod Identity 功能，因此传统附加组件在 Auto Mode 计算资源上属于冗余配置。
- 此变体没有托管节点组。支持混合计算集群，但非 Auto Mode 节点仍需要适用的附加组件和放置配置。
- Auto Mode 会从节点池预置 EC2 实例，并负责操作系统修补、扩缩容和生命周期管理。

---

对于纯 Auto Mode 集群，请省略标准的 `03-platform/addons.tf`：其中的传统 EBS CSI driver 并不是 Auto Mode 的存储控制器。请在经过审查的 StorageClass 中使用 Auto Mode provisioner `ebs.csi.eks.amazonaws.com`。满足前置条件后，应用 Pod Identity/访问条目文件仍然可以使用。

## EKS Hybrid Nodes

这是一个**仅适用于新建 Hybrid 集群的控制平面替代方案**，不是完整的主机预置流程，也不是原地转换方案。请另行建立 VPN/Direct Connect 或其他受支持的路由网络，配置 DNS、防火墙规则、受支持的操作系统和凭证提供方。此集群层完成后，请按照 nodeadm/CNI 设置流程操作，并先让 Hybrid 计算资源上线，再等待 CoreDNS 附加组件就绪。

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

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

### 要点

- **`remote_network_config`** 声明互不重叠的远程节点/Pod CIDR；它不会创建 VPN、路由、防火墙或 CNI。Module v21 接受包含 `cidrs` 的对象，而非这些对象组成的列表。
- Hybrid nodes 通过类型为 `HYBRID_LINUX` 的访问条目使用 IAM 角色进行身份验证。
- Hybrid nodes 通过 TCP 443 连接私有 API；控制平面通过 TCP 10250 **出站连接到 Hybrid kubelet**。请配置相应的本地防火墙以及必需的 Pod/webhook 路径；两个安全组规则并不是完整的网络设计。
- Hybrid nodes 不使用 VPC CNI；必须在本地环境配置替代 CNI（例如 Cilium）。

---

上面的 SSM 角色还支持受限的 nodeadm 注销操作。请为单独的 SSM activation/托管实例添加 `EKSClusterARN = local.cluster_arn` 标签，以匹配该 policy。由于签名密钥变更，新的 SSM 安装/升级需要 nodeadm 1.0.19 或更高版本。请勿将 activation 密钥保存在 Terraform 源码中，也不要发布包含这些密钥的状态。

标准 EBS CSI 平台文件不适用于本地磁盘。完成 Hybrid node/CNI 设置后，请使用单独审查的平台组合。以下内容将替代仅限 Hybrid 变体的标准核心附加组件管理；请勿将其附加到已经管理相同附加组件的配置中：

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

在 Hybrid nodes 上使用应用 Pod Identity 之前，请配置受支持的 agent 的 Hybrid DaemonSet、节点凭证文件以及 `eks-auth:AssumeRoleForPodIdentity` 节点权限。上面的 SSM 基础权限不包含此可选权限。请遵循专门的 Hybrid Nodes 附加组件指南；仅创建关联并不足够。

## 附加组件管理

对于传统 EC2 变体，集群层管理 CoreDNS、VPC CNI、kube-proxy 和 Pod Identity Agent。平台层管理 EBS CSI 和应用身份。Auto Mode 和 Hybrid 对组件的要求及安装顺序不同；不要将标准平台文件不加修改地应用于这些变体。

### 关键选项

| 选项 | 说明 |
|--------|-------------|
| `most_recent` | 为 true 时，在 Terraform 评估期间解析最新的兼容构建版本；为 false 时选择 EKS 默认版本。它不是自动升级服务。如需保证可复现性，建议使用经过审查的 `addon_version`。 |
| `before_compute` | 将 module 管理的附加组件创建操作安排在节点组之前。适用于 VPC CNI 初始化；并非所有附加组件都必须如此。CoreDNS 需要可用的计算资源才能达到正常状态。 |
| `configuration_values` | 附加组件专用设置的 JSON 字符串（例如 VPC CNI 前缀委派）。 |
| `service_account_role_arn` | IRSA 角色 ARN；Pod Identity 则使用 `pod_identity_association`。 |
| `resolve_conflicts_on_create` | `NONE` 会暴露冲突以供审查。仅在从现有安装进行经过审查的迁移时使用 `OVERWRITE`。 |
| `resolve_conflicts_on_update` | 在受支持时，`PRESERVE` 会保留冲突的自定义配置；对于由自身管理的字段，请使用附加组件 schema/configurationValues。`OVERWRITE` 可能会丢弃更改。 |

### 附加组件的 Pod Identity

某些附加组件直接支持 Pod Identity 关联。`03-platform/addons.tf` 中的 EBS CSI driver 配置通过 `pod_identity_association` 展示了这种模式：

请使用上面的完整 `03-platform/addons.tf` 资源。嵌套的 `pod_identity_association` 块由附加组件管理；不要再为相同的 ServiceAccount 创建单独的关联。

---

## 基于访问条目的访问控制

初始 Kubernetes 管理员访问权限是在 `02-cluster` 中显式配置的访问条目；开发者/只读用户条目属于 `03-platform`。策略关联会引用其访问条目资源，以建立 Terraform 顺序依赖。访问 API 模式的变更属于迁移决策：启用 API 后，不能简单地恢复为仅使用 ConfigMap 的设计。

### 身份验证模式

| 模式 | 说明 |
|------|-------------|
| `API` | 仅使用访问条目（建议用于新集群）。 |
| `API_AND_CONFIG_MAP` | 同时使用访问条目和 `aws-auth` ConfigMap（迁移期间使用）。 |
| `CONFIG_MAP` | 仅使用旧版 `aws-auth`（不建议）。 |

### 可用的访问策略 ARN

| 策略 | ARN | 说明 |
|--------|-----|-------------|
| 集群管理员 | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | 完整的集群访问权限 |
| 管理员 | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | 在选定的访问范围内管理 Kubernetes；不包含 AWS IAM 权限 |
| 编辑 | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | 对大多数资源具有读写权限 |
| 查看 | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | 可读取涵盖的 Kubernetes 资源，但不包含常规 Secret 访问权限 |

---

## 部署工作流

这些命令适用于**标准 EC2 三层示例**，前提是已配置后端、角色授权和私有网络。请通过经过审查的变量文件或 `TF_VAR_*` 值设置所需的 Terraform 变量（第 2 层的 `cluster_admin_role_arn`；第 3 层的 `developer_role_arn`、`viewer_role_arn` 和 `app_bucket_name`）。请使用预期的 AWS 账户和 Region。Auto Mode/Hybrid 替代方案需要按上文所述调整文件和引导流程。

### 每次仅计划并应用一层

请使用绝对项目路径，以免切换 shell 目录时选错层。首先初始化并保存网络计划：

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
请在保存的计划中审查资源创建、替换/删除、IAM、网络暴露和费用。请妥善保护计划文件，因为其中可能包含敏感数据。仅应用经过审查的文件：

```bash
# Run only after reviewing this saved plan; a saved-plan apply does not prompt again.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed.tfplan
```
成功后，将 `TF_LAYER=02-cluster` 设置为下一层，再重复计划/审查/应用步骤，然后设置 `TF_LAYER=03-platform`。如果某层失败，请停止后续操作；不要针对缺失或过期的输出应用下游状态。请提交经过审查的 provider 锁定文件，但不要将状态、kubeconfig、凭证和计划文件放入源代码仓库。

先前的指南估计创建集群需要 10–15 分钟。此估算未经本次审计测量或复现；容量、附加组件、IAM 和网络状况都可能影响所需时间。

### 配置 kubeconfig

集群层完成后，请使用明确选定的管理员角色。当前 AWS 身份必须获准代入该角色；如果改为直接使用已授权的主体进行身份验证，请采用相应且经过审查的凭证路径。

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
### 验证结果

对于标准 EC2 示例，请检查实际节点、系统 Pod 和托管附加组件状态：

```bash
: "${EXAMPLE_KUBECONFIG:?}" "${EKS_CLUSTER_NAME:?}" "${EKS_REGION:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get pods
aws eks list-addons --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
aws eks describe-addon --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --addon-name coredns --query 'addon.{status:status,version:addonVersion,health:health}'
```
对预期的附加组件重复执行 `describe-addon`。仅列出 DaemonSet 并不能证明 EKS 附加组件运行正常。请检查 API 身份验证、DNS、网络、存储和应用实际使用的 AWS 身份；本次审计没有执行这些实时检查。纯 Auto Mode 和仅限 Hybrid 的集群需要采用相应的验证流程，系统 Pod 也可能不同。

### 按相反顺序销毁

首先备份数据，并通过相应控制器移除 Kubernetes 创建的负载均衡器和卷资源，同时审查 PVC/PV 回收行为。在清理完成之前，请保留控制器及其 IAM 权限。然后保存并审查平台销毁计划：

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
确认所选状态以及所有拟删除资源都属于此环境后，才进行 apply：

```bash
# Run only after reviewing this exact destruction plan.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed-destroy.tfplan
```
成功后，对 `02-cluster` 重复操作，最后处理 `01-network`。发生错误时请停止并调查残留的 ENI、负载均衡器、卷和 finalizer。销毁计划也可能安排删除由该状态管理的 KMS key；请保留仍需用于加密数据的 key。请保留单独管理的后端、状态版本和恢复凭据。

---

## 最佳实践

### 状态管理

使用不同的 S3 状态键和原生锁定。锁定可以保护单个状态的并发写入者，但无法协调跨三种状态的部署。

- **在 S3 存储桶中启用版本控制**，以便从意外的状态损坏中恢复。
- **限制存储桶访问权限**：使用 IAM policy，确保只有 CI/CD 流水线和获授权的操作人员可以读写状态。
- **切勿手动编辑状态文件**；需要操作状态时，请使用 `terraform state` 命令。

### Module 版本控制

- `~> 21.0` 允许使用低于 22.0 的次要版本和补丁版本；`~> 21.0.0` 则将更新限制在 21.0.x。两者都不能保证兼容性。本示例明确固定了 module 版本；`.terraform.lock.hcl` 会锁定 provider，而不是远程 module 版本。
- 升级主要版本之前，请查看 module CHANGELOG。
- 首先在非生产环境中测试升级。

### 环境隔离

使用以下任一方法分隔环境：

| 方法 | 优点 | 缺点 |
|----------|------|------|
| **单独目录** | 隔离明确，状态独立 | 代码重复 |
| **Terraform workspace** | 单一代码库，切换方便 | 共享后端，隔离能力有限 |
| **Terragrunt** | 配置可复用，可编排 | 需要额外工具；仍需通过独立状态和权限实现隔离 |

在多层架构中，最常见的方法是**为每个环境使用单独目录**；每个环境都有自己的 `01-network/`、`02-cluster/`、`03-platform/` 目录树，并使用不同的变量值和状态键。

### 标签策略

应用一致的标签，以用于成本分摊、合规性和资源管理：

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

- [EKS 集群创建 - 第 1 部分：前置条件](./02-eks-cluster-creation-part1.md)：EKS 集群创建的前置条件
- [EKS 集群创建 - 第 2 部分：使用 eksctl 创建集群](./02-eks-cluster-creation-part2.md)：使用 eksctl 创建 EKS 集群
- [EKS 集群创建 - 第 3 部分：使用 AWS 控制台和 CLI 创建集群](./02-eks-cluster-creation-part3.md)：通过控制台和 CLI 创建 EKS 集群
- [EKS 集群创建 - 第 5 部分：集群访问、验证、升级和删除](./02-eks-cluster-creation-part5.md)：管理 EKS 集群
- [EKS 网络 - 第 1 部分：基本概念和 VPC 配置](./03-eks-networking-part1.md)：EKS 网络基础知识
- [EKS 安全](./05-eks-security.md)：EKS 集群的安全配置

### 相关主题

- [ArgoCD](../gitops/argocd/README.md)：GitOps 持续部署
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md)：从 Kubernetes 管理 AWS 资源
- [Karpenter](../autoscaling/02-karpenter.md)：节点预置自动化
- [Kubernetes 扩展](../core/11-extending-kubernetes.md)：使用 Operators 和 CRD 扩展 Kubernetes API

## 术语表

| 术语 | 说明 |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service，由 AWS 提供的托管 Kubernetes 服务。 |
| **Terraform** | HashiCorp 的基础设施即代码工具，用于预置和管理云资源。 |
| **访问条目** | 基于 EKS API 的机制，用于授予 IAM 主体对集群的访问权限，以取代 `aws-auth` ConfigMap。 |
| **Pod Identity** | EKS 功能，无需 OIDC provider 即可为 Pod 提供 AWS 凭证。 |
| **Auto Mode** | 一种 EKS 模式，由 AWS 全面管理节点预置、扩缩容和操作系统更新。 |
| **Hybrid Nodes** | 一项 EKS 功能，允许本地或边缘服务器作为工作节点加入 EKS 集群。 |
| **IAM** | Identity and Access Management，用于控制对 AWS 资源的访问。 |
| **VPC** | Virtual Private Cloud，即 AWS 中逻辑隔离的虚拟网络。 |
| **IRSA** | IAM Roles for Service Accounts，一种受支持的基于 OIDC 的工作负载身份机制。 |
| **远程状态** | Terraform 的一项功能，可让一个配置从另一个配置的状态文件中读取输出。 |

## 测验

要检验你在本章学到的内容，请尝试 [EKS 集群创建 - 第 4 部分测验](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md)。


## 验证参考资料

- [EKS module v21 迁移](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.29.0/docs/UPGRADE-21.0.md)
- [S3 后端锁定](https://developer.hashicorp.com/terraform/language/backend/s3)
- [远程状态访问](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Pod Identity 角色信任](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)
- [EKS 附加组件和 Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Hybrid 凭证](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Hybrid 网络](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Hybrid 附加组件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
