# Creación de clústeres EKS - Parte 4: Creación de clústeres usando Terraform

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: February 23, 2026

## Estructura de proyecto Terraform para producción

Terraform es una herramienta de infrastructure-as-code que permite definir, aprovisionar y administrar clústeres EKS de forma repetible y con control de versiones. Esta guía usa el **AWS provider ~> 6.0** y el **EKS module ~> 21.0** de la comunidad, que admiten las funcionalidades más recientes de EKS, incluidos Auto Mode, Hybrid Nodes, Pod Identity y Access Entries basadas en API.

En entornos de producción, un único directorio plano de Terraform con un solo archivo de estado crea problemas: un cambio en la VPC puede destruir accidentalmente tu clúster, cada `terraform plan` tarda más a medida que el proyecto crece, y distintos equipos no pueden trabajar de forma independiente. Una **arquitectura multicapa** resuelve esto dividiendo la infraestructura en archivos de estado separados según la frecuencia de cambio y la propiedad.

### Arquitectura de 3 capas

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

### Por qué separar las capas

| Capa | Cambios | Propietario | Radio de impacto |
|-------|---------|-------|--------------|
| 01-network | Rara vez | Equipo de infraestructura | Solo VPC, subnets |
| 02-cluster | Mensualmente | Equipo de plataforma | Clúster EKS, nodes |
| 03-platform | Semanalmente | Equipo de plataforma / aplicaciones | Add-ons, RBAC, Pod Identity |

Cada capa tiene su propio archivo de estado en S3 y se puede planificar/aplicar de forma independiente. Un cambio en un add-on en `03-platform` nunca supone el riesgo de tocar la VPC o el clúster en sí.

### Backend S3 compartido

Todas las capas comparten un único bucket S3 con bloqueo de DynamoDB, pero cada capa escribe en una **clave de estado diferente**:

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

Las capas se referencian entre sí mediante fuentes de datos `terraform_remote_state`, que leen outputs del archivo de estado de otra capa sin crear una dependencia del propio código de Terraform.

---

## Capa 1: Red (01-network)

Esta capa aprovisiona la VPC, las subnets, los NAT gateways y todos los prerrequisitos de red. Cambia rara vez y normalmente es propiedad de un equipo de infraestructura.

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

> **Nota**: La etiqueta `kubernetes.io/cluster/<cluster-name>` ya no es necesaria en las subnets al usar EKS module ~> 21.0 con AWS Load Balancer Controller. Las etiquetas `kubernetes.io/role/elb` y `kubernetes.io/role/internal-elb` son suficientes para el descubrimiento de subnets.

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

## Capa 2: Clúster EKS (02-cluster)

Esta capa aprovisiona el clúster EKS, los managed node groups y los add-ons principales. Lee la información de red desde la Capa 1 mediante `terraform_remote_state`.

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

## Capa 3: Plataforma (03-platform)

Esta capa administra add-ons más allá del conjunto principal, asociaciones de Pod Identity y access entries. Cambia con mayor frecuencia y se puede aplicar de forma independiente sin afectar al clúster ni a la red.

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

EKS Pod Identity es el enfoque recomendado para otorgar permisos de AWS a workloads de Kubernetes. Reemplaza IAM Roles for Service Accounts (IRSA) y no requiere un proveedor OIDC.

### Cómo funciona Pod Identity

1. El add-on `eks-pod-identity-agent` se ejecuta como un DaemonSet en cada node (instalado en la Capa 2).
2. Se crea un rol IAM con una política de confianza de Pod Identity (en la Capa 3).
3. El rol se asocia con una Kubernetes service account mediante `aws_eks_pod_identity_association`.
4. Los Pods que usan esa service account reciben automáticamente credenciales temporales de AWS.

Los recursos de Pod Identity mostrados arriba en `03-platform/pod-identity.tf` siguen este patrón. La política de confianza del rol IAM usa `pods.eks.amazonaws.com` como principal, y `sts:TagSession` habilita el etiquetado automático de sesiones con metadatos de clúster, namespace y service account.

### Pod Identity vs IRSA

| Funcionalidad | Pod Identity | IRSA |
|---------|-------------|------|
| Proveedor OIDC requerido | No | Sí |
| Soporte cross-account | Integrado mediante `sts:TagSession` | Requiere confianza OIDC por cuenta |
| Complejidad de configuración | Baja — una sola asociación | Media — OIDC, rol, annotation |
| Etiquetas de sesión | Automáticas (clúster, namespace, SA) | No disponibles |
| Reutilización | El mismo rol para varios clústeres | Un rol por OIDC de clúster |

> **Recomendación**: Usa Pod Identity para todos los workloads nuevos. IRSA sigue siendo compatible por retrocompatibilidad.

---

## Clúster EKS Auto Mode

EKS Auto Mode delega completamente a AWS el aprovisionamiento de nodes, el escalado y la administración del sistema operativo. No es necesario definir managed node groups: EKS aprovisiona y administra el cómputo automáticamente. Al usar Auto Mode, reemplaza el `02-cluster/main.tf` estándar con la siguiente variante:

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

### Puntos clave

- **`cluster_compute_config.enabled = true`** activa Auto Mode.
- **`node_pools`** especifica qué node pools integrados habilitar (`general-purpose`, `system`).
- **`bootstrap_self_managed_addons = false`** evita conflictos: Auto Mode administra automáticamente los add-ons principales (CoreDNS, kube-proxy, VPC CNI).
- **No** debes definir `eks_managed_node_groups` al usar Auto Mode.
- Auto Mode aprovisiona instancias EC2 desde los node pools y se encarga del parcheo del sistema operativo, el escalado y el ciclo de vida.

---

## EKS Hybrid Nodes

EKS Hybrid Nodes permite unir servidores on-premises o edge a un clúster EKS como worker nodes, manteniendo el plano de control de EKS en AWS. Al usar Hybrid Nodes, reemplaza el `02-cluster/main.tf` estándar con la siguiente variante:

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

### Puntos clave

- **`remote_network_config`** define los rangos CIDR de nodes y pods on-premises.
- Hybrid nodes se autentican mediante un rol IAM con el tipo de access entry `HYBRID_LINUX`.
- Las reglas de security group deben permitir tráfico desde los CIDR on-premises hacia el servidor de API de EKS (443) y kubelet (10250).
- VPC CNI no se usa en hybrid nodes: debes configurar una CNI alternativa (por ejemplo, Cilium) en el lado on-premises.

---

## Administración de add-ons

Los add-ons de EKS son componentes administrados que se ejecutan en el clúster. En la arquitectura multicapa, los **add-ons principales** (coredns, vpc-cni, kube-proxy, eks-pod-identity-agent) se definen en `02-cluster` porque son necesarios para que el clúster funcione, mientras que los **add-ons adicionales** (EBS CSI, etc.) se administran en `03-platform`.

### Opciones clave

| Opción | Descripción |
|--------|-------------|
| `most_recent` | Usa siempre la última versión compatible para la versión de Kubernetes del clúster. |
| `before_compute` | Instala el add-on antes de aprovisionar node groups. Es obligatorio para `vpc-cni` y `eks-pod-identity-agent` para que los nodes puedan iniciar correctamente. |
| `configuration_values` | Cadena JSON de configuraciones específicas del add-on (por ejemplo, delegación de prefijos de VPC CNI). |
| `service_account_role_arn` | ARN del rol IAM para add-ons que necesitan acceso a la API de AWS (por ejemplo, EBS CSI driver). Funciona tanto con IRSA como con Pod Identity. |
| `resolve_conflicts_on_create` | Establécelo en `"OVERWRITE"` para reemplazar versiones self-managed existentes durante la migración. |
| `resolve_conflicts_on_update` | Establécelo en `"OVERWRITE"` para forzar la actualización de una configuración de add-on en conflicto. |

### Pod Identity para add-ons

Algunos add-ons admiten asociaciones de Pod Identity directamente. La configuración de EBS CSI driver en `03-platform/addons.tf` demuestra este patrón usando `pod_identity_association`:

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

## Control de acceso basado en Access Entries

EKS admite autenticación basada en API mediante Access Entries, reemplazando el ConfigMap `aws-auth` heredado. En la arquitectura multicapa, el acceso inicial de administrador del clúster se configura en `02-cluster` (mediante `enable_cluster_creator_admin_permissions`), mientras que las access entries adicionales para desarrolladores y usuarios de solo lectura se administran en `03-platform/access-entries.tf`.

### Modo de autenticación

| Modo | Descripción |
|------|-------------|
| `API` | Solo Access Entries (recomendado para clústeres nuevos). |
| `API_AND_CONFIG_MAP` | Tanto Access Entries como ConfigMap `aws-auth` (período de migración). |
| `CONFIG_MAP` | Solo `aws-auth` heredado (no recomendado). |

### ARN de políticas de acceso disponibles

| Política | ARN | Descripción |
|--------|-----|-------------|
| Cluster Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | Acceso completo al clúster |
| Admin | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Acceso de administrador (sin administración de IAM) |
| Edit | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | Lectura/escritura en la mayoría de los recursos |
| View | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | Acceso de solo lectura |

---

## Flujo de despliegue

### Desplegar en orden de capas

Cada capa debe inicializarse y aplicarse en secuencia, ya que las capas posteriores dependen de los outputs de estado de las capas anteriores:

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

> **Nota**: La creación del clúster EKS (Capa 2) normalmente tarda entre 10 y 15 minutos. Las capas 1 y 3 son más rápidas.

### Configurar kubeconfig

Después de que finalice la Capa 2, configura el acceso de `kubectl`:

```bash
cd eks-terraform/02-cluster

aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_name) \
  --region $(terraform output -raw region)
```

### Verificar el clúster

```bash
# Check node status
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system

# Verify EKS add-ons
kubectl get daemonsets -n kube-system
```

Salida esperada para un clúster saludable:

```
NAME                              STATUS   ROLES    AGE   VERSION
ip-10-0-1-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
ip-10-0-2-xxx.ap-northeast-2...  Ready    <none>   5m    v1.33.x
```

### Destruir en orden inverso

Para eliminar todos los recursos, destruye las capas en orden inverso para que las dependencias se eliminen antes que los recursos de los que dependen:

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

> **Precaución**: `terraform destroy` elimina todos los recursos administrados por el estado de esa capa. Asegúrate de que no haya workloads críticos en ejecución antes de destruir la capa del clúster.

---

## Buenas prácticas

### Administración del estado

La arquitectura multicapa ya usa claves de estado S3 por capa con bloqueo de DynamoDB. Recomendaciones adicionales:

- **Habilita el versionado** en el bucket S3 para recuperarte de una corrupción accidental del estado.
- **Restringe el acceso al bucket** con políticas IAM: solo las canalizaciones CI/CD y los operadores autorizados deberían leer/escribir el estado.
- **Nunca edites archivos de estado manualmente**: usa comandos `terraform state` cuando sea necesario manipular el estado.

### Versionado de módulos

- Fija las versiones de módulos con `~>` (por ejemplo, `~> 21.0`) para permitir actualizaciones de parche y evitar cambios incompatibles.
- Revisa el CHANGELOG del módulo antes de actualizar versiones principales.
- Prueba las actualizaciones primero en un entorno que no sea de producción.

### Separación de entornos

Separa entornos usando uno de estos enfoques:

| Enfoque | Ventajas | Desventajas |
|----------|------|------|
| **Directorios separados** | Aislamiento claro, estado independiente | Duplicación de código |
| **Terraform workspaces** | Base de código única, cambio sencillo | Backend compartido, aislamiento limitado |
| **Terragrunt** | Configuración DRY, aislamiento fuerte | Dependencia de herramientas adicional |

Con la arquitectura multicapa, el enfoque más común es usar **directorios separados por entorno**, donde cada entorno tiene su propio árbol `01-network/`, `02-cluster/`, `03-platform/` con valores de variables y claves de estado diferentes.

### Estrategia de etiquetas

Aplica etiquetas coherentes para asignación de costos, cumplimiento y administración de recursos:

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

## Próximos pasos

- [Creación de clústeres EKS - Parte 1: Prerrequisitos](./02-eks-cluster-creation-part1.md) — Prerrequisitos para la creación de clústeres EKS
- [Creación de clústeres EKS - Parte 2: Creación de clústeres usando eksctl](./02-eks-cluster-creation-part2.md) — Creación de clústeres EKS con eksctl
- [Creación de clústeres EKS - Parte 3: Creación de clústeres usando AWS Console y CLI](./02-eks-cluster-creation-part3.md) — Creación de clústeres EKS mediante Console y CLI
- [Creación de clústeres EKS - Parte 5: Acceso, validación, actualización y eliminación de clústeres](./02-eks-cluster-creation-part5.md) — Administración de clústeres EKS
- [Networking de EKS - Parte 1: Conceptos básicos y configuración de VPC](./03-eks-networking-part1.md) — Fundamentos de networking de EKS
- [Seguridad de EKS](./05-eks-security.md) — Configuración de seguridad para clústeres EKS

### Temas relacionados

- [ArgoCD](../gitops/argocd/README.md) — Despliegue continuo GitOps
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md) — Administración de recursos de AWS desde Kubernetes
- [Karpenter](../autoscaling/02-karpenter.md) — Automatización del aprovisionamiento de nodes
- [Extensiones de Kubernetes](../core/11-extending-kubernetes.md) — Extensión de la API de Kubernetes con Operators y CRDs

## Glosario

| Término | Descripción |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service — un servicio administrado de Kubernetes proporcionado por AWS. |
| **Terraform** | Una herramienta de infrastructure-as-code de HashiCorp para aprovisionar y administrar recursos en la nube. |
| **Access Entry** | Un mecanismo de EKS basado en API para otorgar acceso a principales IAM a un clúster, reemplazando el ConfigMap `aws-auth`. |
| **Pod Identity** | Una funcionalidad de EKS que proporciona credenciales de AWS a pods sin requerir un proveedor OIDC. |
| **Auto Mode** | Un modo de EKS en el que AWS administra completamente el aprovisionamiento de nodes, el escalado y las actualizaciones del sistema operativo. |
| **Hybrid Nodes** | Una funcionalidad de EKS que permite que servidores on-premises o edge se unan a un clúster EKS como worker nodes. |
| **IAM** | Identity and Access Management — controla el acceso a los recursos de AWS. |
| **VPC** | Virtual Private Cloud — una red virtual lógicamente aislada dentro de AWS. |
| **IRSA** | IAM Roles for Service Accounts — el método heredado para otorgar permisos de AWS a pods mediante OIDC. |
| **Remote State** | Una funcionalidad de Terraform que permite que una configuración lea outputs desde el archivo de estado de otra configuración. |

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [quiz de Creación de clústeres EKS - Parte 4](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md).
