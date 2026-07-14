# EKS Cluster の作成 - Part 4: Terraform を使用した Cluster の作成

> **サポート対象バージョン**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 23, 2026

## Production Terraform Project 構造

Terraform は、EKS cluster を反復可能かつ version 管理された方法で定義、provisioning、管理できる infrastructure-as-code tool です。この guide では、Auto Mode、Hybrid Nodes、Pod Identity、API-based Access Entries など最新の EKS 機能をサポートする **AWS provider ~> 6.0** と community **EKS module ~> 21.0** を使用します。

Production environment では、1 つの state file を持つ単一の flat Terraform directory には問題があります。VPC の変更によって誤って cluster が破棄される可能性があり、project が大きくなるほどすべての `terraform plan` に時間がかかり、異なる team が独立して作業できません。**multi-layer architecture** は、変更頻度と ownership に基づいて infrastructure を個別の state file に分割することで、これを解決します。

### 3-Layer Architecture

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

### Layer を分離する理由

| Layer | 変更頻度 | Owner | Blast Radius |
|-------|---------|-------|--------------|
| 01-network | まれ | Infra team | VPC、subnets のみ |
| 02-cluster | 月次 | Platform team | EKS cluster、nodes |
| 03-platform | 週次 | Platform / App team | Add-ons、RBAC、Pod Identity |

各 layer は独自の S3 state file を持ち、独立して plan/apply できます。`03-platform` の add-on への変更が VPC や cluster 自体に触れるリスクはありません。

### Shared S3 Backend

すべての layer は DynamoDB locking を使用する単一の S3 bucket を共有しますが、各 layer は **異なる state key** に書き込みます。

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

Layer は `terraform_remote_state` data source を通じて相互に参照します。これは Terraform code 自体への dependency を作成せずに、別 layer の state file から outputs を読み取ります。

---

## Layer 1: Network (01-network)

この layer は、VPC、subnets、NAT gateways、およびすべての networking prerequisites を provision します。変更頻度は低く、通常は infrastructure team が ownership を持ちます。

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

> **注記**: EKS module ~> 21.0 と AWS Load Balancer Controller を使用する場合、subnets に `kubernetes.io/cluster/<cluster-name>` tag は不要になりました。`kubernetes.io/role/elb` と `kubernetes.io/role/internal-elb` tags が subnet discovery には十分です。

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

## Layer 2: EKS Cluster (02-cluster)

この layer は、EKS cluster、managed node groups、および core add-ons を provision します。Layer 1 から `terraform_remote_state` 経由で network 情報を読み取ります。

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

## Layer 3: Platform (03-platform)

この layer は、core set を超える add-ons、Pod Identity associations、および access entries を管理します。最も頻繁に変更され、cluster や network に影響を与えずに独立して適用できます。

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

EKS Pod Identity は、Kubernetes workloads に AWS permissions を付与するための推奨 approach です。IAM Roles for Service Accounts (IRSA) を置き換え、OIDC provider を必要としません。

### Pod Identity の仕組み

1. `eks-pod-identity-agent` add-on がすべての node 上で DaemonSet として実行されます（Layer 2 で install）。
2. Pod Identity trust policy を持つ IAM role が作成されます（Layer 3）。
3. その role は `aws_eks_pod_identity_association` により Kubernetes service account に関連付けられます。
4. その service account を使用する Pods は、一時的な AWS credentials を自動的に受け取ります。

上記の `03-platform/pod-identity.tf` に示した Pod Identity resources は、この pattern に従っています。IAM role の trust policy は `pods.eks.amazonaws.com` を principal として使用し、`sts:TagSession` は cluster、namespace、service account metadata による automatic session tagging を有効にします。

### Pod Identity vs IRSA

| Feature | Pod Identity | IRSA |
|---------|-------------|------|
| OIDC provider required | 不要 | 必要 |
| Cross-account support | `sts:TagSession` により built-in | account ごとに OIDC trust が必要 |
| Setup complexity | 低 — single association | 中 — OIDC、role、annotation |
| Session tags | 自動（cluster、namespace、SA） | 利用不可 |
| Re-usability | 複数 cluster に同じ role | cluster OIDC ごとに 1 role |

> **推奨**: すべての新しい workloads には Pod Identity を使用してください。IRSA は backward compatibility のため引き続きサポートされます。

---

## EKS Auto Mode Cluster

EKS Auto Mode は、node provisioning、scaling、および OS management を完全に AWS に委任します。Managed node groups を定義する必要はありません。EKS が compute を自動的に provision して管理します。Auto Mode を使用する場合は、標準の `02-cluster/main.tf` を次の variant に置き換えます。

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

### Key Points

- **`cluster_compute_config.enabled = true`** は Auto Mode を有効化します。
- **`node_pools`** は有効化する built-in node pools（`general-purpose`、`system`）を指定します。
- **`bootstrap_self_managed_addons = false`** は conflicts を防ぎます。Auto Mode は core add-ons（CoreDNS、kube-proxy、VPC CNI）を自動的に管理します。
- Auto Mode を使用する場合、`eks_managed_node_groups` は定義しません。
- Auto Mode は node pools から EC2 instances を provision し、OS patching、scaling、lifecycle を処理します。

---

## EKS Hybrid Nodes

EKS Hybrid Nodes を使用すると、on-premises または edge servers を worker nodes として EKS cluster に参加させ、EKS control plane は AWS 内に保持できます。Hybrid Nodes を使用する場合は、標準の `02-cluster/main.tf` を次の variant に置き換えます。

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

### Key Points

- **`remote_network_config`** は on-premises nodes と pods の CIDR ranges を定義します。
- Hybrid nodes は access entry type `HYBRID_LINUX` を持つ IAM role 経由で authenticate します。
- Security group rules は、on-premises CIDRs から EKS API server（443）および kubelet（10250）への traffic を許可する必要があります。
- VPC CNI は hybrid nodes では使用されません。on-premises 側で代替 CNI（例: Cilium）を設定する必要があります。

---

## Add-on Management

EKS add-ons は cluster 上で実行される managed components です。multi-layer architecture では、**core add-ons**（coredns、vpc-cni、kube-proxy、eks-pod-identity-agent）は cluster の動作に必要なため `02-cluster` で定義され、**additional add-ons**（EBS CSI など）は `03-platform` で管理されます。

### Key Options

| Option | Description |
|--------|-------------|
| `most_recent` | cluster の Kubernetes version に対して常に最新の compatible version を使用します。 |
| `before_compute` | node groups を provision する前に add-on を install します。nodes が正しく開始できるように、`vpc-cni` と `eks-pod-identity-agent` では必須です。 |
| `configuration_values` | add-on 固有 settings の JSON string（例: VPC CNI prefix delegation）。 |
| `service_account_role_arn` | AWS API access を必要とする add-ons（例: EBS CSI driver）用の IAM role ARN。IRSA と Pod Identity の両方で動作します。 |
| `resolve_conflicts_on_create` | migration 中に既存の self-managed versions を置き換えるには `"OVERWRITE"` に設定します。 |
| `resolve_conflicts_on_update` | conflicting add-on configuration を強制 update するには `"OVERWRITE"` に設定します。 |

### Add-ons 用の Pod Identity

一部の add-ons は Pod Identity associations を直接サポートします。`03-platform/addons.tf` の EBS CSI driver configuration は、`pod_identity_association` を使用してこの pattern を示しています。

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

## Access Entry-Based Access Control

EKS は Access Entries による API-based authentication をサポートし、legacy `aws-auth` ConfigMap を置き換えます。multi-layer architecture では、initial cluster admin access は `02-cluster` で（`enable_cluster_creator_admin_permissions` 経由で）設定され、developers と viewers 用の additional access entries は `03-platform/access-entries.tf` で管理されます。

### Authentication Mode

| Mode | Description |
|------|-------------|
| `API` | Access Entries のみ（新規 cluster に推奨）。 |
| `API_AND_CONFIG_MAP` | Access Entries と `aws-auth` ConfigMap の両方（migration period）。 |
| `CONFIG_MAP` | Legacy `aws-auth` のみ（非推奨）。 |

### Available Access Policy ARNs

| Policy | ARN | Description |
|--------|-----|-------------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | Full cluster access |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Admin access（IAM management なし） |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | ほとんどの resources への read/write |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | Read-only access |

---

## Deployment Workflow

### Layer 順に Deploy する

後続の layer は先行 layer の state outputs に依存するため、各 layer は順番に initialize して apply する必要があります。

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

> **注記**: EKS cluster の作成（Layer 2）には通常 10〜15 分かかります。Layer 1 と 3 はより高速です。

### kubeconfig を設定する

Layer 2 が完了したら、`kubectl` access を設定します。

```bash
cd eks-terraform/02-cluster

aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region)
```

### Cluster を検証する

```bash
# Check node status
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Verify EKS add-ons
kubectl get daemonsets -n kube-system
```

正常な cluster の expected output:

```
NAME                              STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
ip-10-0-2-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
```

### Reverse Order で Destroy する

すべての resources を削除するには、dependencies を依存先 resources より前に削除できるよう、layer を reverse order で destroy します。

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

> **注意**: `terraform destroy` は、その layer の state によって管理されるすべての resources を削除します。cluster layer を destroy する前に、critical workloads が実行されていないことを確認してください。

---

## Best Practices

### State Management

multi-layer architecture はすでに layer ごとの S3 state keys と DynamoDB locking を使用しています。追加の推奨事項は次のとおりです。

- accidental state corruption から recovery できるよう、S3 bucket で **versioning を有効化** します。
- IAM policies で **bucket access を制限** します。CI/CD pipelines と authorized operators のみが state を read/write できるようにしてください。
- **state files を手動で編集しない** でください。state manipulation が必要な場合は `terraform state` commands を使用します。

### Module Versioning

- breaking changes を防ぎつつ patch updates を許可するため、module versions を `~>`（例: `~> 21.0`）で pin します。
- major versions に upgrade する前に module CHANGELOG を確認します。
- まず non-production environment で upgrades を test します。

### Environment Separation

次のいずれかの approach を使用して environments を分離します。

| Approach | Pros | Cons |
|----------|------|------|
| **Separate directories** | 明確な isolation、independent state | Code duplication |
| **Terraform workspaces** | Single codebase、容易な switching | Shared backend、limited isolation |
| **Terragrunt** | DRY configuration、strong isolation | Additional tooling dependency |

multi-layer architecture では、最も一般的な approach は **environment ごとの separate directories** です。各 environment は、異なる variable values と state keys を持つ独自の `01-network/`、`02-cluster/`、`03-platform/` tree を持ちます。

### Tagging Strategy

cost allocation、compliance、resource management のために一貫した tags を適用します。

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

## Next Steps

- [EKS Cluster の作成 - Part 1: Prerequisites](./02-eks-cluster-creation-part1.md) — EKS cluster 作成の prerequisites
- [EKS Cluster の作成 - Part 2: eksctl を使用した Cluster の作成](./02-eks-cluster-creation-part2.md) — eksctl による EKS clusters の作成
- [EKS Cluster の作成 - Part 3: AWS Console と CLI を使用した Cluster の作成](./02-eks-cluster-creation-part3.md) — Console と CLI 経由での EKS clusters の作成
- [EKS Cluster の作成 - Part 5: Cluster Access、Validation、Upgrade、Deletion](./02-eks-cluster-creation-part5.md) — EKS clusters の管理
- [EKS Networking - Part 1: Basic Concepts と VPC Configuration](./03-eks-networking-part1.md) — EKS networking fundamentals
- [EKS Security](./05-eks-security.md) — EKS clusters の security configuration

### Related Topics

- [ArgoCD](../gitops/argocd/README.md) — GitOps continuous deployment
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md) — Kubernetes から AWS resources を管理する
- [Karpenter](../autoscaling/02-karpenter.md) — Node provisioning automation
- [Kubernetes Extensions](../core/11-extending-kubernetes.md) — Operators と CRDs による Kubernetes API の拡張

## Glossary

| Term | Description |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service — AWS が提供する managed Kubernetes service。 |
| **Terraform** | cloud resources を provisioning および管理するための HashiCorp による infrastructure-as-code tool。 |
| **Access Entry** | IAM principals に cluster への access を付与する EKS API-based mechanism で、`aws-auth` ConfigMap を置き換えます。 |
| **Pod Identity** | OIDC provider を必要とせずに AWS credentials を pods に提供する EKS feature。 |
| **Auto Mode** | AWS が node provisioning、scaling、OS updates を完全に管理する EKS mode。 |
| **Hybrid Nodes** | on-premises または edge servers が worker nodes として EKS cluster に参加できる EKS feature。 |
| **IAM** | Identity and Access Management — AWS resources への access を制御します。 |
| **VPC** | Virtual Private Cloud — AWS 内の論理的に分離された virtual network。 |
| **IRSA** | IAM Roles for Service Accounts — OIDC 経由で pods に AWS permissions を付与する legacy method。 |
| **Remote State** | ある configuration が別の configuration の state file から outputs を読み取ることを可能にする Terraform feature。 |

## Quiz

この章で学んだ内容を確認するには、[EKS Cluster の作成 - Part 4 Quiz](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md) を試してください。
