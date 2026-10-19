# EKS クラスターの作成 - Part 4: Terraform によるクラスター作成

> **例のバージョン**: Amazon EKS 1.36、Terraform 1.16.6、AWS provider 6.69.1、EKS module 21.29.0
> **最終更新日**: 2026年10月16日

## Terraform の3層構成例

Terraform はインフラストラクチャをコードとして管理します。この例では AWS provider 6.x を使用し、EKS module **21.29.0** と VPC module **6.7.3** を固定しています。HCL は Terraform 1.16.6 と AWS provider 6.69.1 で確認しましたが、AWS へのデプロイは行っておらず、本番環境での動作も検証していません。以前の v20 形式の `cluster_*` 入力値は module v21 と互換性がありません。以下の `name`、`kubernetes_version`、`addons` など v21 の名前を使ってください。

state を分けると、チームごとに所有範囲やライフサイクルごとの変更を分担し、レビューしやすくできます。ただし依存関係や運用への影響がなくなるわけではありません。ネットワークの変更でクラスターが中断することがあり、add-on やアクセス・ポリシーの変更はすべてのワークロードに影響する場合があります。これは構成例であり、本番アーキテクチャとして検証されたものではありません。

### 3層アーキテクチャ

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

### 層を分ける理由

| 層 | 変更頻度 | 所有者 | 影響範囲 |
|-------|---------|-------|--------------|
| 01-network | 例として低頻度 | インフラチーム | VPC/サブネットと、それらに依存する接続性 |
| 02-cluster | 月次 | プラットフォームチーム | EKS クラスター、ノード |
| 03-platform | 週次 | プラットフォーム/アプリチーム | add-on、RBAC、Pod Identity |

各層には個別の state key と plan があります。層ごとに IAM 権限と CI の所有者を分ける必要があり、層をまたぐ変更は調整してください。state を分離しても、add-on の変更がクラスターの動作に影響しないとは限りません。

### S3 の共有バックエンド

この例では、Terraform 1.10 以降の S3 ネイティブロック機能 `use_lockfile = true` を使い、環境/層ごとに別の key を指定します。バックエンド用 bucket は別途作成し、versioning、暗号化、Block Public Access を有効にしてください。初期化前に、すべての `REPLACE_WITH_YOUR_STATE_BUCKET` を実際の値に置き換えます。必要な state key へのアクセスと、その `.tflock` オブジェクトへの Get/Put/Delete だけを許可します。DynamoDB ロックは非推奨です。既存バックエンドの移行では、ロックテーブルを単に削除せず、すべての利用者を調整してください。

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

`terraform_remote_state` は root outputs を HCL から参照できるようにしますが、読み取り側は機密値を含む**state snapshot 全体**を取得できます。別々のプロジェクト間に apply 順序の依存関係を作るものではありません。利用側のチームに state 全体を読ませられない場合は、選択した値を別途管理するインターフェースで公開してください。

---

## 層1: ネットワーク (01-network)

ラボを小さく保つため、この例では3つの AZ にまたがる VPC と NAT gateway を1つ作成します。NAT が1つだと AZ に依存し、AZ 間転送料金が発生する可能性があります。本番利用前に、AZ 障害に耐える egress 設計、サブネット容量、DNS、private endpoint を確認してください。

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

> **サブネット検出**は Terraform EKS module のバージョンではなく、Load Balancer Controller のバージョン、feature gate、サブネット適格性ルールに従います。ここに示す role tag は public/private サブネットの選択に役立ちますが、AZ のカバー範囲、空き IP、route、およびクラスター tag による絞り込みも確認してください。

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

## 層2: EKS クラスター (02-cluster)

この層では、**新しい標準 EC2 クラスター**、managed node group、基本 add-on を作成します。既存の `cluster_admin_role_arn` を明示的に設定してください。Terraform の実行主体に Kubernetes 管理権限が自動付与されるわけではありません。実行者はその role を引き受けられる必要があります。private endpoint を使う場合、kubectl の実行や platform のインストール前に、接続経路と route が確立した管理環境が必要です。

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

node group の root disk は launch template の block-device mapping を使います。この module が既定のカスタム launch template を使う場合、`disk_size` は無視されます。この例では AWS 所有キーによる Kubernetes API envelope encryption を既定で使います。顧客管理 KMS key は別途設計してください。

デプロイ前に module の既定値を確認してください。このバージョンに固定した module の managed node IAM role には ECR ReadOnly と IPv4 CNI 権限が含まれます。これらの既定値によって例は動作しますが、本番に必要な最小権限だと示すものではありません。専用 CNI identity と、明示的にレビューした node role を優先してください（十分な場合は ECR PullOnly も検討します）。node group の min/max 値を設定しても autoscaler はインストールされません。

Terraform が data source を再評価すると、互換 add-on の既定 build が変わることがあります。対象クラスターと互換性のある build を特定して記録し、再現性のため固定が必要なら `addon_version` を指定してください。更新時にはレビュー済みのカスタム設定を保持します。

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

## 層3: Platform (03-platform)

標準 EC2 用の platform 層では、追加 add-on、Pod Identity association、developer/viewer access を管理します。state は分かれていますが、その変更はクラスターのセキュリティやワークロードの可用性に影響します。以下の Auto Mode と Hybrid の代替案では、使う platform ファイルの選択が異なります。

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

アプリケーションをテストする前に、Kubernetes/GitOps の管理者を通じて新しい `app-dev` namespace と `app-sa` ServiceAccount を作成してください。EKS association はどちらのオブジェクトも作成しません。この例で許可するのは、承認済み bucket の `app/` prefix に対する読み取りだけです。bucket policy、KMS 暗号化、クロスアカウントアクセスには、レビュー済みの追加権限が必要な場合があります。実際に引き受けられた role を確認し、IAM/association の反映を待ってから利用してください。

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

EKS Pod Identity は、サポートされるワークロード向けの選択肢であり、IRSA を全面的に置き換えるものではありません。IAM OIDC provider は不要です。標準 Linux EC2、Auto Mode、適切に構成した Hybrid Nodes でサポート経路を利用できます。Fargate と Windows には、別のサポート対象 identity 機構が必要です。IRSA も引き続き利用できます。

### Pod Identity の仕組み

1. サポート対象の標準ノードでは Pod Identity Agent DaemonSet を使います。Auto Mode では機能が提供されます。Hybrid Nodes では、文書化された credential file と専用 DaemonSet の設定が必要です。
2. Pod Identity trust policy を持つ IAM role を作成します（層3）。
3. `aws_eks_pod_identity_association` を使って、その role を Kubernetes service account に関連付けます。
4. 互換性のある SDK は default credential chain を使って一時的な credential を取得します。chain の前方に既存の static credential があると、この経路を上書きする場合があります。実際の identity を確認してください。

上記 `03-platform/pod-identity.tf` の Pod Identity resource はこの方式に沿っています。IAM role の trust policy では `pods.eks.amazonaws.com` を principal とし、`sts:TagSession` によってクラスター、namespace、service account の metadata を使った session tag が自動付与されます。

### Pod Identity と IRSA の比較

| 機能 | Pod Identity | IRSA |
|---------|-------------|------|
| OIDC provider の要否 | 不要 | 必要 |
| クロスアカウント対応 | サポートされる場合は `targetRoleArn` を含む明示的な role 委任。trust/permission が必要 | target account の OIDC trust、または明示的な role chaining |
| 設定の複雑さ | 低（単一 association） | 中（OIDC、role、annotation） |
| Session tag | 有効時に EKS context tag を自動付与 | EKS Pod Identity の context tag は自動付与されない |
| 再利用性 | 1つの role を複数のレビュー済み association で使える | 1つの role で、範囲を明示した複数の OIDC issuer/subject を信頼できる |

> コンピュート種別と SDK がサポートする identity 機構を選んでください。`sts:TagSession` は tag を追加しますが、それだけでクロスアカウント trust が成立するわけではありません。上記 trust policy では session tag を有効にしておく必要があります。module は Pod Identity とは別に、任意の IRSA 用 OIDC provider を作成する場合があります。

---

## EKS Auto Mode クラスター

これは**新規クラスター向けの代替案**です。初回デプロイ前に選択してください。すでに apply 済みのクラスター設定を置き換える手順ではありません。Auto Mode はコンピュートとインフラストラクチャ機能を管理します。純粋な Auto Mode の例では managed node group を定義せず、module v21 の `compute_config` 入力を使います。

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

- **`compute_config.enabled = true`** によって、この module 経由でコンピュート、ロードバランシング、ブロックストレージが有効になります。固定した module が作成する IAM policy を確認してください。
- **`node_pools`** で有効化する組み込み node pool（`general-purpose`、`system`）を指定します。
- module v21 は内部の `bootstrap_self_managed_addons` を `false` に固定しています。これは module の入力値ではありません。現在の Auto Mode はネットワーク、ストレージ、Pod Identity に加えてクラスター DNS も提供するため、Auto Mode のコンピュートでは従来の同等 add-on は重複します。
- この variant には managed node group がありません。混合コンピュートのクラスターもサポートされますが、Auto Mode 以外のノードには適切な add-on と配置設定が引き続き必要です。
- Auto Mode は node pool から EC2 instance を起動し、OS patching、スケーリング、ライフサイクルを管理します。

---

純粋な Auto Mode では、標準の `03-platform/addons.tf` を省略してください。そこにある従来型 EBS CSI driver は Auto Mode のストレージコントローラーではありません。レビュー済み StorageClass で Auto Mode の provisioner `ebs.csi.eks.amazonaws.com` を使います。前提条件を満たせば、アプリケーション用 Pod Identity/access-entry ファイルは引き続き使用できます。

## EKS Hybrid Nodes

これは**Hybrid 専用の新しいコントロールプレーン構成**であり、ホストを準備する完全な手順でも、既存クラスターをその場で変換する手順でもありません。VPN/Direct Connect などサポートされるルーティングネットワーク、DNS、ファイアウォール規則、サポート対象 OS、credential provider は個別に準備してください。この cluster 層の処理後、nodeadm/CNI の設定に従って Hybrid コンピュートをオンラインにしてから、CoreDNS add-on の Ready を待ちます。

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

- **`remote_network_config`** は重複しない remote node/Pod CIDR を宣言します。VPN、route、firewall、CNI は作成しません。module v21 では `cidrs` を含む object を指定し、その object のリストを入れる形式ではありません。
- Hybrid node は `HYBRID_LINUX` access entry type を持つ IAM role で認証します。
- Hybrid node は TCP 443 で private API に接続します。コントロールプレーンは**Hybrid kubelet に向けて外向きに TCP 10250 で接続**します。対応するオンプレミス側 firewall と必要な Pod/webhook 経路を構成してください。2つの security group rule だけでは完全なネットワーク設計になりません。
- Hybrid node では VPC CNI を使用しません。オンプレミス側に代替 CNI（例: Cilium）を構成してください。

---

上記の SSM role は、範囲を絞った nodeadm 登録解除にも対応します。別途管理する SSM activation/managed instance に `EKSClusterARN = local.cluster_arn` tag を付け、この policy に一致させます。署名鍵の変更により、新規 SSM インストール/アップグレードでは nodeadm 1.0.19 以降が必要です。activation secret を Terraform のソースに保存したり、secret を含む state を公開したりしないでください。

標準の EBS CSI platform file はオンプレミスのディスクには適用できません。Hybrid node/CNI を設定した後、別途レビューした platform 構成を使ってください。次は Hybrid 専用 variant 用に標準の core add-on 管理を置き換える例です。同じ add-on をすでに管理している設定に追加しないでください。

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

Hybrid node でアプリケーション Pod Identity を使う前に、サポート対象 agent の Hybrid DaemonSet、node credential file、`eks-auth:AssumeRoleForPodIdentity` node permission を設定してください。上記 SSM の基本設定には、この任意 permission は含まれません。Hybrid Nodes 用 add-on ガイドに従ってください。association を作成するだけでは不十分です。

## Add-on の管理

標準 EC2 variant では、cluster 層が CoreDNS、VPC CNI、kube-proxy、Pod Identity Agent を管理します。platform 層が EBS CSI とアプリケーション identity を管理します。Auto Mode と Hybrid では必要なコンポーネントとインストール順序が異なります。それらの variant に標準 platform file をそのまま適用しないでください。

### 主なオプション

| オプション | 説明 |
|--------|-------------|
| `most_recent` | true の場合、Terraform 評価時に互換性のある最新 build を解決します。false は EKS の既定値を選びます。自動 upgrade サービスではありません。再現性のためレビュー済み `addon_version` を優先してください。 |
| `before_compute` | module が管理する add-on の作成を node group より前にします。VPC CNI の初期化には有用ですが、すべての add-on で必須ではありません。CoreDNS が正常になるには利用可能なコンピュートが必要です。 |
| `configuration_values` | add-on 固有設定（例: VPC CNI prefix delegation）を表す JSON string です。 |
| `service_account_role_arn` | IRSA role ARN です。Pod Identity では代わりに `pod_identity_association` を使います。 |
| `resolve_conflicts_on_create` | `NONE` は競合を表示してレビューできるようにします。既存インストールからのレビュー済み移行に限り `OVERWRITE` を使ってください。 |
| `resolve_conflicts_on_update` | サポートされる場合、`PRESERVE` は競合するカスタマイズを保持します。所有するフィールドには add-on schema/configurationValues を使います。`OVERWRITE` は変更を破棄する可能性があります。 |

### Add-on の Pod Identity

一部の add-on は Pod Identity association を直接サポートします。`03-platform/addons.tf` の EBS CSI driver 設定では、`pod_identity_association` を使う方式を示しています。

上記の `03-platform/addons.tf` にある完全な resource を使ってください。ネストされた `pod_identity_association` block は add-on 側が所有します。同じ ServiceAccount 用の association を別途作成しないでください。

---

## Access Entry によるアクセス制御

初回の Kubernetes 管理アクセスは `02-cluster` の明示的な access entry で設定します。developer/viewer の entry は `03-platform` に置きます。policy association は Terraform の実行順序を定めるために access-entry resource を参照します。API access mode の変更は移行上の判断です。API を有効にした後、ConfigMap のみを使う設計に単純に戻せるわけではありません。

### 認証モード

| モード | 説明 |
|------|-------------|
| `API` | Access Entry のみ（新規クラスターに推奨）。 |
| `API_AND_CONFIG_MAP` | Access Entry と `aws-auth` ConfigMap の両方（移行期間）。 |
| `CONFIG_MAP` | 従来の `aws-auth` のみ（非推奨）。 |

### 利用できる Access Policy ARN

| Policy | ARN | 説明 |
|--------|-----|-------------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | クラスターへの完全なアクセス |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | 選択した access scope 内の Kubernetes 管理。AWS IAM 権限は含まない |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | ほとんどのリソースへの読み書き |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | 対象の Kubernetes resource を読み取る。Secret 全般へのアクセスではない |

---

## デプロイの流れ

以下のコマンドは、バックエンド作成、role 認可、private network の前提条件を整えた後に使う**標準 EC2 の3層構成例**向けです。必要な Terraform variable（層2の `cluster_admin_role_arn`、層3の `developer_role_arn`、`viewer_role_arn`、`app_bucket_name`）を、レビュー済みの variable file または `TF_VAR_*` 値で指定します。意図した AWS account と Region を使ってください。Auto Mode/Hybrid の代替案には上記で説明した file 選択と bootstrap の変更が必要です。

### 層ごとに Plan と Apply を行う

shell のディレクトリを変えても誤った層を選ばないよう、絶対パスの project path を使います。最初にネットワーク層を初期化し、plan を保存します。

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

保存した plan で resource の作成、置換/削除、IAM、ネットワーク公開、コストを確認します。plan file に機密情報が含まれる場合があるため保護してください。レビュー済みの file だけを apply します。

```bash
# Run only after reviewing this saved plan; a saved-plan apply does not prompt again.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed.tfplan
```

成功したら、`TF_LAYER=02-cluster`、続いて `TF_LAYER=03-platform` で plan/review/apply を繰り返します。失敗した場合は先へ進まず、欠落または古い output を使って下流の state に apply しないでください。レビュー済み provider lock file は commit して構いませんが、state、kubeconfig、credential、plan file はソースリポジトリに含めないでください。

以前のガイドではクラスター作成に10～15分かかると見積もっていました。この監査ではその時間を測定も再現もしていません。容量、add-on、IAM、ネットワークによって所要時間は変わります。

### kubeconfig の設定

cluster 層の完了後、明示的に選んだ admin role を使います。現在の AWS identity にその role を引き受ける権限が必要です。すでに認可済みの principal として直接認証する場合は、対応するレビュー済み credential 経路を使ってください。

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

### 結果の検証

標準 EC2 の例では、実際の node、system Pod、managed add-on の状態を確認します。

```bash
: "${EXAMPLE_KUBECONFIG:?}" "${EKS_CLUSTER_NAME:?}" "${EKS_REGION:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get pods
aws eks list-addons --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
aws eks describe-addon --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --addon-name coredns --query 'addon.{status:status,version:addonVersion,health:health}'
```

想定した add-on ごとに `describe-addon` を繰り返してください。DaemonSet の一覧だけでは EKS add-on の正常性を証明できません。API 認証、DNS、ネットワーク、ストレージ、アプリケーションが実際に使う AWS identity を確認してください。この監査では、そのような実環境での確認は行っていません。純粋な Auto Mode および Hybrid 専用クラスターでは対応する検証経路を使い、同じ system Pod が存在するとは限らない点に注意してください。

### 逆順に Destroy する

まずデータをバックアップし、Kubernetes が作成したロードバランサーや volume resource を、それぞれの controller を通じて削除します。PVC/PV の reclaim 動作も確認してください。削除が終わるまで controller と IAM permission を残します。その後、platform の destroy plan を保存してレビューします。

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

選択した state と、削除予定のすべての resource がこの環境に属することを確認してから apply してください。

```bash
# Run only after reviewing this exact destruction plan.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed-destroy.tfplan
```

成功後、`02-cluster`、最後に `01-network` でも同じ作業を行います。エラーが出たら止め、残った ENI、ロードバランサー、volume、finalizer を調査してください。destroy plan は、その state が管理する KMS key の削除も予約する場合があります。暗号化データを保持するなら、必要な key も保持してください。独立して管理するバックエンド、state version、復旧証跡を残します。

---

## ベストプラクティス

### State の管理

S3 state key を分け、ネイティブロックを使います。ロックが保護するのは1つの state に対する同時書き込みです。3つの state にまたがるデプロイを調整するものではありません。

- S3 bucket の **versioning を有効化**し、誤って state が破損した場合に復旧できるようにします。
- IAM policy で **bucket access を制限**します。CI/CD pipeline と認可済み運用者だけが state を読み書きできるようにしてください。
- **state file を手作業で編集しないでください**。state を操作する必要がある場合は `terraform state` command を使います。

### Module のバージョン管理

- `~> 21.0` は22.0未満の minor/patch release を許可し、`~> 21.0.0` は21.0.x に更新を制限します。どちらも互換性を保証しません。この例は module version を明示的に固定します。`.terraform.lock.hcl` が固定するのは provider であり、remote module version ではありません。
- major version を上げる前に module の CHANGELOG を確認します。
- まず non-production 環境でアップグレードを試します。

### 環境の分離

次のいずれかの方法で環境を分けます。

| 方法 | 長所 | 短所 |
|----------|------|------|
| **ディレクトリを分ける** | 明確な分離、独立した state | コードの重複 |
| **Terraform workspace** | 単一 codebase、簡単な切り替え | backend を共有し、分離は限定的 |
| **Terragrunt** | 設定を再利用して orchestration | 追加ツールが必要。分離には別々の state と permission も必要 |

この多層構成では、最も一般的なのは**環境ごとにディレクトリを分ける**方法です。各環境に、それぞれ異なる variable 値と state key を持つ `01-network/`、`02-cluster/`、`03-platform/` の tree を用意します。

### Tag 戦略

コスト配賦、コンプライアンス、resource 管理のため、tag を一貫して付与してください。

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

## 次のステップ

- [EKS クラスターの作成 - Part 1: 前提条件](./02-eks-cluster-creation-part1.md): EKS クラスター作成の前提条件
- [EKS クラスターの作成 - Part 2: eksctl によるクラスター作成](./02-eks-cluster-creation-part2.md): eksctl で EKS クラスターを作成する
- [EKS クラスターの作成 - Part 3: AWS Console と CLI によるクラスター作成](./02-eks-cluster-creation-part3.md): Console と CLI で EKS クラスターを作成する
- [EKS クラスターの作成 - Part 5: クラスターアクセス、検証、アップグレード、削除](./02-eks-cluster-creation-part5.md): EKS クラスターを管理する
- [EKS ネットワーク - Part 1: 基本概念と VPC 構成](./03-eks-networking-part1.md): EKS ネットワークの基礎
- [EKS セキュリティ](./05-eks-security.md): EKS クラスターのセキュリティ設定

### 関連トピック

- [ArgoCD](../gitops/argocd/README.md): GitOps による継続的デプロイ
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md): Kubernetes から AWS resource を管理する
- [Karpenter](../autoscaling/02-karpenter.md): node provisioning の自動化
- [Kubernetes 拡張](../core/11-extending-kubernetes.md): Operator と CRD による Kubernetes API の拡張

## 用語集

| 用語 | 説明 |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service。AWS が提供するマネージド Kubernetes サービスです。 |
| **Terraform** | cloud resource をプロビジョニング、管理するための HashiCorp 製 Infrastructure as Code ツールです。 |
| **Access Entry** | IAM principal にクラスターアクセスを許可する EKS API の仕組みで、`aws-auth` ConfigMap を置き換えます。 |
| **Pod Identity** | OIDC provider を必要とせず Pod に AWS credential を提供する EKS 機能です。 |
| **Auto Mode** | AWS が node provisioning、スケーリング、OS 更新を全面管理する EKS mode です。 |
| **Hybrid Nodes** | オンプレミスまたは edge server を worker node として EKS クラスターに参加させる EKS 機能です。 |
| **IAM** | Identity and Access Management。AWS resource へのアクセスを制御します。 |
| **VPC** | Virtual Private Cloud。AWS 内で論理的に分離された仮想ネットワークです。 |
| **IRSA** | IAM Roles for Service Accounts。サポート対象の OIDC ベース workload identity 機構です。 |
| **Remote State** | ある Terraform configuration が、別の configuration の state file から output を読み取れる機能です。 |

## クイズ

この章で学んだ内容を確認するには、[EKS クラスターの作成 - Part 4 クイズ](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md)に挑戦してください。

## 検証用リファレンス

- [EKS module v21 移行](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.29.0/docs/UPGRADE-21.0.md)
- [S3 backend のロック](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Remote state へのアクセス](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Pod Identity role の trust](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)
- [EKS add-on と Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Hybrid credential](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Hybrid add-on](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
