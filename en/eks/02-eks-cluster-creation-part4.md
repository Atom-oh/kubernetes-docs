# EKS Cluster Creation - Part 4: Creating Clusters Using Terraform

> **Example Versions**: Amazon EKS 1.36; Terraform 1.15.7; AWS provider 6.64.0; EKS module 21.25.0
> **Last Updated**: September 11, 2026

## Three-Layer Terraform Example

Terraform manages infrastructure as code. This example uses AWS provider 6.x and pins EKS module **21.25.0** and VPC module **5.21.0**. The HCL was checked with Terraform 1.15.7 and AWS provider 6.64.0; AWS deployment and production behavior were not executed. The original v20-style `cluster_*` inputs are incompatible with module v21: use `name`, `kubernetes_version`, `addons` and the other v21 names shown below.

Separate states can help teams divide ownership and review changes by lifecycle. They do not eliminate dependencies or operational impact: a network change can still interrupt a cluster, and an add-on or access-policy change can affect every workload. This is an example structure, not a tested production architecture.

### 3-Layer Architecture

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

### Why Separate Layers

| Layer | Changes | Owner | Blast Radius |
|-------|---------|-------|--------------|
| 01-network | Infrequent, as an example | Infra team | VPC/subnets and dependent connectivity |
| 02-cluster | Monthly | Platform team | EKS cluster, nodes |
| 03-platform | Weekly | Platform / App team | Add-ons, RBAC, Pod Identity |

Each layer has a distinct state key and plan. Separate IAM permissions and CI ownership are still required, and cross-layer changes must be coordinated. State separation does not guarantee that an add-on change leaves cluster behavior unaffected.

### Shared S3 Backend

The examples use S3 native locking with `use_lockfile = true` (Terraform 1.10+), with a distinct key per environment/layer. Create the backend bucket separately, enable versioning/encryption and Block Public Access, and replace every `REPLACE_WITH_YOUR_STATE_BUCKET` before initialization. Grant only the required state-key access and Get/Put/Delete on its `.tflock` object. DynamoDB locking is deprecated; coordinate all clients when migrating an existing backend rather than simply deleting its lock table.

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

`terraform_remote_state` exposes root outputs to HCL, but its reader can retrieve the **entire state snapshot**, including sensitive values. It does not create an apply-order dependency between separate projects. Publish selected values through a separately controlled interface when a consuming team must not read the full state.

---

## Layer 1: Network (01-network)

This example creates a three-AZ VPC with one NAT gateway to keep the lab small. A single NAT creates an AZ dependency and can incur cross-AZ transfer charges. Review an AZ-resilient egress design, subnet capacity, DNS and private endpoints before production use.

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

> **Subnet discovery** follows the Load Balancer Controller version, feature gates and subnet eligibility rules, not the Terraform EKS module version. The role tags shown help select public/private subnets; also verify AZ coverage, free addresses, routes and any cluster-tag filtering.

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

This layer creates a **new conventional EC2 cluster**, managed node groups and core add-ons. Set the existing `cluster_admin_role_arn` explicitly; the Terraform caller is not automatically granted Kubernetes administration. The operator must be able to assume that role. Private endpoint access requires a connected, routed management environment before kubectl or platform installation.

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

The node-group root disks use launch-template block-device mappings; `disk_size` is ignored when this module uses its default custom launch template. The example uses default AWS-owned Kubernetes API envelope encryption. A customer KMS key is a separate design choice.

Review module defaults before deployment: this pinned module's managed-node IAM role includes ECR ReadOnly and IPv4 CNI permissions. Those defaults make this example functional but are not a claim of minimum production permissions. Prefer a dedicated CNI identity and an explicitly reviewed node role (including ECR PullOnly where sufficient). Node-group min/max values do not install an autoscaler.

The default-compatible add-on build can change when Terraform reevaluates its data sources. Resolve and record compatible builds for the target cluster and use `addon_version` when reproducibility requires a pin. Preserve reviewed custom configuration on updates.

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

## Layer 3: Platform (03-platform)

The standard EC2 platform layer manages additional add-ons, Pod Identity associations and developer/viewer access. Its state is separate, but its changes can affect cluster security and workload availability. The Auto Mode and Hybrid alternatives below require different platform file selections.

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

Create the new `app-dev` namespace and `app-sa` ServiceAccount through their Kubernetes/GitOps owner before testing the application. The EKS association does not create either object. The example grants read access only to the approved bucket's `app/` prefix; bucket policies, KMS encryption and cross-account access may require additional reviewed permissions. Verify the actual assumed role and handle IAM/association propagation before relying on it.

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

EKS Pod Identity is an option for supported workloads, not a universal replacement for IRSA. It needs no IAM OIDC provider. Conventional Linux EC2, Auto Mode and appropriately configured Hybrid Nodes have supported paths; Fargate and Windows require a different supported identity mechanism. IRSA remains supported.

### How Pod Identity Works

1. Conventional supported nodes use the Pod Identity Agent DaemonSet. Auto Mode provides the capability; Hybrid Nodes need the documented credential-file and dedicated DaemonSet configuration.
2. An IAM role with a Pod Identity trust policy is created (in Layer 3).
3. The role is associated with a Kubernetes service account via `aws_eks_pod_identity_association`.
4. A compatible SDK using its default credential chain retrieves temporary credentials. Existing static credentials earlier in that chain can override this path; verify the actual identity.

The Pod Identity resources shown in `03-platform/pod-identity.tf` above follow this pattern. The IAM role's trust policy uses `pods.eks.amazonaws.com` as the principal, and `sts:TagSession` enables automatic session tagging with cluster, namespace, and service account metadata.

### Pod Identity vs IRSA

| Feature | Pod Identity | IRSA |
|---------|-------------|------|
| OIDC provider required | No | Yes |
| Cross-account support | Explicit role delegation, including `targetRoleArn` where supported; requires trust/permissions | Target-account OIDC trust or explicit role chaining |
| Setup complexity | Low — single association | Medium — OIDC, role, annotation |
| Session tags | Automatic EKS context tags when enabled | No automatic EKS Pod Identity context tags |
| Re-usability | A role can serve multiple reviewed associations | A role can trust multiple explicitly scoped OIDC issuers/subjects |

> Choose an identity mechanism supported by the compute type and SDK. `sts:TagSession` adds tags; it does not itself establish cross-account trust. The trust policies above require session tags to stay enabled. The module may create an OIDC provider for optional IRSA use independently of Pod Identity.

---

## EKS Auto Mode Cluster

Choose this **new-cluster alternative before initial deployment**; replacing an already applied cluster configuration is not a migration procedure. Auto Mode manages compute and infrastructure capabilities. Its pure-Auto-Mode example does not define managed node groups and uses the module v21 `compute_config` input:

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

### Key Points

- **`compute_config.enabled = true`** enables compute, load balancing and block storage through this module. Review the IAM policies the pinned module creates.
- **`node_pools`** specifies which built-in node pools to enable (`general-purpose`, `system`).
- Module v21 hardcodes the underlying `bootstrap_self_managed_addons` to `false`; it is not a module input. Current Auto Mode includes cluster DNS as well as networking, storage and Pod Identity capabilities, so the equivalent traditional add-ons are redundant on Auto Mode compute.
- This variant has no managed node groups. Mixed-compute clusters are supported, but non-Auto-Mode nodes still require their applicable add-ons and placement configuration.
- Auto Mode provisions EC2 instances from the node pools and handles OS patching, scaling, and lifecycle.

---

For pure Auto Mode, omit the standard `03-platform/addons.tf`: its traditional EBS CSI driver is not the Auto Mode storage controller. Use the Auto Mode provisioner `ebs.csi.eks.amazonaws.com` in a reviewed StorageClass. The application Pod Identity/access-entry files can still be used after their prerequisites are met.

## EKS Hybrid Nodes

This is a **new hybrid-only control-plane alternative**, not a complete host-provisioning recipe or an in-place conversion. Establish VPN/Direct Connect or another supported routed network, DNS, firewall rules, a supported OS and a credentials provider separately. After this cluster layer finishes, follow nodeadm/CNI setup and bring hybrid compute online before waiting for CoreDNS add-on readiness.

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

### Key Points

- **`remote_network_config`** declares non-overlapping remote node/Pod CIDRs; it does not create VPNs, routes, firewalls or a CNI. Module v21 takes objects containing `cidrs`, not lists of those objects.
- Hybrid nodes authenticate via an IAM role with access entry type `HYBRID_LINUX`.
- Hybrid nodes connect to the private API on TCP 443; the control plane connects **outbound to hybrid kubelets** on TCP 10250. Configure the corresponding on-premises firewall and required Pod/webhook paths; two SG rules are not a full network design.
- VPC CNI is not used on hybrid nodes — you must configure an alternative CNI (e.g., Cilium) on the on-premises side.

---

The SSM role above also supports scoped nodeadm deregistration. Tag the separate SSM activation/managed instances with `EKSClusterARN = local.cluster_arn` to match that policy. New SSM installations/upgrades require nodeadm 1.0.19 or later due to the signing-key change. Do not store activation secrets in Terraform source or publish state containing them.

The standard EBS CSI platform file is not applicable to on-premises disks. After hybrid node/CNI setup, use a separately reviewed platform composition. The following replaces the standard core-add-on ownership for the hybrid-only variant; do not append it to a configuration already managing the same add-ons:

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

Before using application Pod Identity on hybrid nodes, configure the supported agent's hybrid DaemonSet, the node credentials file and `eks-auth:AssumeRoleForPodIdentity` node permission. The SSM baseline above does not grant that optional permission. Follow the specific Hybrid Nodes add-on guide; creating an association alone is insufficient.

## Add-on Management

For the conventional EC2 variant, the cluster layer manages CoreDNS, VPC CNI, kube-proxy and Pod Identity Agent. The platform layer manages EBS CSI and application identities. Auto Mode and Hybrid have different component requirements and installation order; do not apply the standard platform files unchanged to those variants.

### Key Options

| Option | Description |
|--------|-------------|
| `most_recent` | Resolves the newest compatible build during Terraform evaluation when true; false selects the EKS default. It is not an autonomous upgrade service. Prefer a reviewed `addon_version` for reproducibility. |
| `before_compute` | Orders module-managed add-on creation before node groups. Useful for VPC CNI initialization; not a universal requirement for every add-on. CoreDNS needs usable compute to become healthy. |
| `configuration_values` | JSON string of add-on-specific settings (e.g., VPC CNI prefix delegation). |
| `service_account_role_arn` | IRSA role ARN; Pod Identity uses `pod_identity_association` instead. |
| `resolve_conflicts_on_create` | `NONE` exposes conflicts for review. Use `OVERWRITE` only in a reviewed migration from an existing installation. |
| `resolve_conflicts_on_update` | `PRESERVE` retains conflicting customizations where supported; use the add-on schema/configurationValues for owned fields. `OVERWRITE` can discard changes. |

### Pod Identity for Add-ons

Some add-ons support Pod Identity associations directly. The EBS CSI driver configuration in `03-platform/addons.tf` demonstrates this pattern using `pod_identity_association`:

Use the complete `03-platform/addons.tf` resource above. The nested `pod_identity_association` block is owned by the add-on; do not also create a separate association for that same ServiceAccount.

---

## Access Entry-Based Access Control

Initial Kubernetes administration is an explicit access entry in `02-cluster`; developer/viewer entries belong to `03-platform`. Policy associations reference their access-entry resources to establish Terraform ordering. API access mode changes are a migration decision: enabling the API cannot simply be reversed to a ConfigMap-only design.

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
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Kubernetes administration within the selected access scope; no AWS IAM permissions |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | Read/write to most resources |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | Read access to covered Kubernetes resources, not general Secret access |

---

## Deployment Workflow

These commands are for the **standard EC2 three-layer example**, after backend provisioning, role authorization and private-network prerequisites. Set the required Terraform variables (`cluster_admin_role_arn` in layer 2; `developer_role_arn`, `viewer_role_arn` and `app_bucket_name` in layer 3) through reviewed variable files or `TF_VAR_*` values. Use the intended AWS account and Region. The Auto Mode/Hybrid alternatives need the file and bootstrap changes described above.

### Plan and Apply One Layer at a Time

Use an absolute project path so changing a shell directory cannot select the wrong layer. First initialize and save the network plan:

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
Review resource creation, replacement/deletion, IAM, network exposure and cost in that saved plan. Protect plan files because they can contain sensitive data. Apply only the reviewed file:

```bash
# Run only after reviewing this saved plan; a saved-plan apply does not prompt again.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed.tfplan
```
After success, repeat the plan/review/apply steps with `TF_LAYER=02-cluster`, then `TF_LAYER=03-platform`. A failure stops progression; do not apply a downstream state against missing or stale outputs. Commit reviewed provider lock files, but keep state, kubeconfigs, credentials and plan files out of the source repository.

The previous guide estimated 10–15 minutes for cluster creation. That estimate was not measured or reproduced in this audit; capacity, add-ons, IAM and networking can change the duration.

### Configure kubeconfig

After the cluster layer completes, use the explicitly selected admin role. The current AWS identity must be permitted to assume it; if you instead authenticate directly as an already authorized principal, use the corresponding reviewed credential path.

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
### Validate the Result

For the standard EC2 example, inspect actual nodes, system Pods and managed add-on status:

```bash
: "${EXAMPLE_KUBECONFIG:?}" "${EKS_CLUSTER_NAME:?}" "${EKS_REGION:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get pods
aws eks list-addons --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
aws eks describe-addon --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --addon-name coredns --query 'addon.{status:status,version:addonVersion,health:health}'
```
Repeat `describe-addon` for the expected add-ons. DaemonSet listing alone does not prove EKS add-on health. Check API authentication, DNS, networking, storage and the application's actual AWS identity; no such live checks were executed during this audit. Pure Auto Mode and hybrid-only clusters need the corresponding validation paths and may not have the same system Pods.

### Destroy in Reverse Order

First back up data and remove Kubernetes-created load balancers and volume resources through their controllers, reviewing PVC/PV reclaim behavior. Retain the controllers and IAM permissions until that cleanup completes. Then save and review the platform destruction plan:

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
Apply only after verifying that the selected state and every proposed deletion belong to this environment:

```bash
# Run only after reviewing this exact destruction plan.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed-destroy.tfplan
```
After success, repeat for `02-cluster` and finally `01-network`. Stop on errors and investigate remaining ENIs, load balancers, volumes and finalizers. A destruction plan can also schedule deletion of KMS keys managed in that state; retain keys required for retained encrypted data. Keep the independently managed backend, state versions and recovery evidence.

---

## Best Practices

### State Management

Use distinct S3 state keys and native locking. Locks protect concurrent writers to one state; they do not coordinate deployments across all three states.

- **Enable versioning** on the S3 bucket to recover from accidental state corruption.
- **Restrict bucket access** with IAM policies — only CI/CD pipelines and authorized operators should read/write state.
- **Never edit state files manually** — use `terraform state` commands when state manipulation is needed.

### Module Versioning

- `~> 21.0` permits both minor and patch releases below 22.0; `~> 21.0.0` restricts updates to 21.0.x. Neither guarantees compatibility. This example pins module versions explicitly; `.terraform.lock.hcl` locks providers, not remote module versions.
- Review the module CHANGELOG before upgrading major versions.
- Test upgrades in a non-production environment first.

### Environment Separation

Separate environments using one of these approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Separate directories** | Clear isolation, independent state | Code duplication |
| **Terraform workspaces** | Single codebase, easy switching | Shared backend, limited isolation |
| **Terragrunt** | Reusable configuration and orchestration | Additional tooling; isolation still needs separate states and permissions |

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
| **IRSA** | IAM Roles for Service Accounts — a supported OIDC-based workload identity mechanism. |
| **Remote State** | A Terraform feature that allows one configuration to read outputs from another configuration's state file. |

## Quiz

To test what you learned in this chapter, try the [EKS Cluster Creation - Part 4 Quiz](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md).


## Verification References

- [EKS module v21 migration](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.25.0/docs/UPGRADE-21.0.md)
- [S3 backend locking](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Remote state access](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Pod Identity role trust](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)
- [EKS add-ons and Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Hybrid credentials](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Hybrid add-ons](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
