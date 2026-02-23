# EKS Cluster Creation - Part 4: Creating Clusters Using Terraform

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 19, 2025

## Production Terraform Project Structure

Terraform is an infrastructure-as-code tool that enables you to define, provision, and manage EKS clusters in a repeatable and version-controlled manner. This guide uses the **AWS provider ~> 6.0** and the community **EKS module ~> 21.0**, which support the latest EKS features including Auto Mode, Hybrid Nodes, Pod Identity, and API-based Access Entries.

In production environments, a single flat Terraform directory with one state file creates problems: a VPC change can accidentally destroy your cluster, every `terraform plan` takes longer as the project grows, and different teams cannot work independently. A **multi-layer architecture** solves this by splitting infrastructure into separate state files based on change frequency and ownership.

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

### Why Separate Layers

| Layer | Changes | Owner | Blast Radius |
|-------|---------|-------|--------------|
| 01-network | Rarely | Infra team | VPC, subnets only |
| 02-cluster | Monthly | Platform team | EKS cluster, nodes |
| 03-platform | Weekly | Platform / App team | Add-ons, RBAC, Pod Identity |

Each layer has its own S3 state file and can be planned/applied independently. A change to an add-on in `03-platform` never risks touching the VPC or the cluster itself.

### Shared S3 Backend

All layers share a single S3 bucket with DynamoDB locking, but each layer writes to a **different state key**:

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

Layers reference each other through `terraform_remote_state` data sources, which read outputs from another layer's state file without creating a dependency on the Terraform code itself.

---

## Layer 1: Network (01-network)

This layer provisions the VPC, subnets, NAT gateways, and all networking prerequisites. It changes rarely and is typically owned by an infrastructure team.

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

> **Note**: The `kubernetes.io/cluster/<cluster-name>` tag is no longer required on subnets when using EKS module ~> 21.0 with the AWS Load Balancer Controller. The `kubernetes.io/role/elb` and `kubernetes.io/role/internal-elb` tags are sufficient for subnet discovery.

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

This layer provisions the EKS cluster, managed node groups, and core add-ons. It reads network information from Layer 1 via `terraform_remote_state`.

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

This layer manages add-ons beyond the core set, Pod Identity associations, and access entries. It changes most frequently and can be applied independently without affecting the cluster or network.

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

EKS Pod Identity is the recommended approach for granting AWS permissions to Kubernetes workloads. It replaces IAM Roles for Service Accounts (IRSA) and does not require an OIDC provider.

### How Pod Identity Works

1. The `eks-pod-identity-agent` add-on runs as a DaemonSet on every node (installed in Layer 2).
2. An IAM role with a Pod Identity trust policy is created (in Layer 3).
3. The role is associated with a Kubernetes service account via `aws_eks_pod_identity_association`.
4. Pods using that service account automatically receive temporary AWS credentials.

The Pod Identity resources shown in `03-platform/pod-identity.tf` above follow this pattern. The IAM role's trust policy uses `pods.eks.amazonaws.com` as the principal, and `sts:TagSession` enables automatic session tagging with cluster, namespace, and service account metadata.

### Pod Identity vs IRSA

| Feature | Pod Identity | IRSA |
|---------|-------------|------|
| OIDC provider required | No | Yes |
| Cross-account support | Built-in via `sts:TagSession` | Requires OIDC trust per account |
| Setup complexity | Low — single association | Medium — OIDC, role, annotation |
| Session tags | Automatic (cluster, namespace, SA) | Not available |
| Re-usability | Same role for multiple clusters | One role per cluster OIDC |

> **Recommendation**: Use Pod Identity for all new workloads. IRSA remains supported for backward compatibility.

---

## EKS Auto Mode Cluster

EKS Auto Mode delegates node provisioning, scaling, and OS management entirely to AWS. There is no need to define managed node groups — EKS provisions and manages compute automatically. When using Auto Mode, replace the standard `02-cluster/main.tf` with the following variant:

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

- **`cluster_compute_config.enabled = true`** activates Auto Mode.
- **`node_pools`** specifies which built-in node pools to enable (`general-purpose`, `system`).
- **`bootstrap_self_managed_addons = false`** prevents conflicts — Auto Mode manages core add-ons (CoreDNS, kube-proxy, VPC CNI) automatically.
- You do **not** define `eks_managed_node_groups` when using Auto Mode.
- Auto Mode provisions EC2 instances from the node pools and handles OS patching, scaling, and lifecycle.

---

## EKS Hybrid Nodes

EKS Hybrid Nodes let you join on-premises or edge servers to an EKS cluster as worker nodes, keeping the EKS control plane in AWS. When using Hybrid Nodes, replace the standard `02-cluster/main.tf` with the following variant:

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

- **`remote_network_config`** defines the CIDR ranges of on-premises nodes and pods.
- Hybrid nodes authenticate via an IAM role with access entry type `HYBRID_LINUX`.
- Security group rules must allow traffic from on-premises CIDRs to the EKS API server (443) and kubelet (10250).
- VPC CNI is not used on hybrid nodes — you must configure an alternative CNI (e.g., Cilium) on the on-premises side.

---

## Add-on Management

EKS add-ons are managed components that run on the cluster. In the multi-layer architecture, **core add-ons** (coredns, vpc-cni, kube-proxy, eks-pod-identity-agent) are defined in `02-cluster` because they are required for the cluster to function, while **additional add-ons** (EBS CSI, etc.) are managed in `03-platform`.

### Key Options

| Option | Description |
|--------|-------------|
| `most_recent` | Always use the latest compatible version for the cluster's Kubernetes version. |
| `before_compute` | Install the add-on before provisioning node groups. Required for `vpc-cni` and `eks-pod-identity-agent` so nodes can start correctly. |
| `configuration_values` | JSON string of add-on-specific settings (e.g., VPC CNI prefix delegation). |
| `service_account_role_arn` | IAM role ARN for add-ons that need AWS API access (e.g., EBS CSI driver). Works with both IRSA and Pod Identity. |
| `resolve_conflicts_on_create` | Set to `"OVERWRITE"` to replace existing self-managed versions during migration. |
| `resolve_conflicts_on_update` | Set to `"OVERWRITE"` to force-update conflicting add-on configuration. |

### Pod Identity for Add-ons

Some add-ons support Pod Identity associations directly. The EBS CSI driver configuration in `03-platform/addons.tf` demonstrates this pattern using `pod_identity_association`:

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

EKS supports API-based authentication via Access Entries, replacing the legacy `aws-auth` ConfigMap. In the multi-layer architecture, the initial cluster admin access is configured in `02-cluster` (via `enable_cluster_creator_admin_permissions`), while additional access entries for developers and viewers are managed in `03-platform/access-entries.tf`.

### Authentication Mode

| Mode | Description |
|------|-------------|
| `API` | Access Entries only (recommended for new clusters). |
| `API_AND_CONFIG_MAP` | Both Access Entries and `aws-auth` ConfigMap (migration period). |
| `CONFIG_MAP` | Legacy `aws-auth` only (not recommended). |

### Available Access Policy ARNs

| Policy | ARN | Description |
|--------|-----|-------------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | Full cluster access |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Admin access (no IAM management) |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | Read/write to most resources |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | Read-only access |

---

## Deployment Workflow

### Deploy in Layer Order

Each layer must be initialized and applied in sequence, since later layers depend on the state outputs of earlier layers:

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

> **Note**: EKS cluster creation (Layer 2) typically takes 10-15 minutes. Layers 1 and 3 are faster.

### Configure kubeconfig

After Layer 2 completes, configure `kubectl` access:

```bash
cd eks-terraform/02-cluster

aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region)
```

### Verify the Cluster

```bash
# Check node status
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Verify EKS add-ons
kubectl get daemonsets -n kube-system
```

Expected output for a healthy cluster:

```
NAME                              STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
ip-10-0-2-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
```

### Destroy in Reverse Order

To tear down all resources, destroy layers in reverse order so dependencies are removed before the resources they depend on:

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

> **Caution**: `terraform destroy` deletes all resources managed by that layer's state. Ensure there are no critical workloads running before destroying the cluster layer.

---

## Best Practices

### State Management

The multi-layer architecture already uses per-layer S3 state keys with DynamoDB locking. Additional recommendations:

- **Enable versioning** on the S3 bucket to recover from accidental state corruption.
- **Restrict bucket access** with IAM policies — only CI/CD pipelines and authorized operators should read/write state.
- **Never edit state files manually** — use `terraform state` commands when state manipulation is needed.

### Module Versioning

- Pin module versions with `~>` (e.g., `~> 21.0`) to allow patch updates while preventing breaking changes.
- Review the module CHANGELOG before upgrading major versions.
- Test upgrades in a non-production environment first.

### Environment Separation

Separate environments using one of these approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Separate directories** | Clear isolation, independent state | Code duplication |
| **Terraform workspaces** | Single codebase, easy switching | Shared backend, limited isolation |
| **Terragrunt** | DRY configuration, strong isolation | Additional tooling dependency |

With the multi-layer architecture, the most common approach is **separate directories per environment**, where each environment has its own `01-network/`, `02-cluster/`, `03-platform/` tree with different variable values and state keys.

### Tagging Strategy

Apply consistent tags for cost allocation, compliance, and resource management:

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

- [EKS Cluster Creation - Part 1: Prerequisites](./02-eks-cluster-creation-part1.md) — Prerequisites for EKS cluster creation
- [EKS Cluster Creation - Part 2: Creating Clusters Using eksctl](./02-eks-cluster-creation-part2.md) — Creating EKS clusters with eksctl
- [EKS Cluster Creation - Part 3: Creating Clusters Using AWS Console and CLI](./02-eks-cluster-creation-part3.md) — Creating EKS clusters via Console and CLI
- [EKS Cluster Creation - Part 5: Cluster Access, Validation, Upgrade, and Deletion](./02-eks-cluster-creation-part5.md) — Managing EKS clusters
- [EKS Networking - Part 1: Basic Concepts and VPC Configuration](./03-eks-networking-part1.md) — EKS networking fundamentals
- [EKS Security](./05-eks-security.md) — Security configuration for EKS clusters

### Related Topics

- [ArgoCD](../gitops/argocd/README.md) — GitOps continuous deployment
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md) — Managing AWS resources from Kubernetes
- [Karpenter](../autoscaling/02-karpenter.md) — Node provisioning automation
- [Kubernetes Extensions](../core/11-extending-kubernetes.md) — Extending the Kubernetes API with Operators and CRDs

## Glossary

| Term | Description |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service — a managed Kubernetes service provided by AWS. |
| **Terraform** | An infrastructure-as-code tool by HashiCorp for provisioning and managing cloud resources. |
| **Access Entry** | An EKS API-based mechanism for granting IAM principals access to a cluster, replacing the `aws-auth` ConfigMap. |
| **Pod Identity** | An EKS feature that provides AWS credentials to pods without requiring an OIDC provider. |
| **Auto Mode** | An EKS mode where AWS fully manages node provisioning, scaling, and OS updates. |
| **Hybrid Nodes** | An EKS feature allowing on-premises or edge servers to join an EKS cluster as worker nodes. |
| **IAM** | Identity and Access Management — controls access to AWS resources. |
| **VPC** | Virtual Private Cloud — a logically isolated virtual network within AWS. |
| **IRSA** | IAM Roles for Service Accounts — the legacy method for granting AWS permissions to pods via OIDC. |
| **Remote State** | A Terraform feature that allows one configuration to read outputs from another configuration's state file. |

## Quiz

To test what you learned in this chapter, try the [EKS Cluster Creation - Part 4 Quiz](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md).
