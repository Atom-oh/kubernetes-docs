# Configuración de infraestructura

> **Base de validación**: Terraform 1.16.6, AWS Provider 6.69.1, módulo EKS 21.29.0, módulo VPC 6.7.3, módulo Pod Identity 2.9.0
> **Última revisión**: 16 de octubre de 2026. Validación local del esquema y de planes simulados; no es el resultado de un despliegue real en AWS.

< [Tabla de contenido](./README.md) | [Siguiente: Enrutamiento ponderado NLB y clústeres Blue/Green](02-infrastructure-advanced.md) >

Este ejemplo describe **un bucket de estado específico de una cuenta y un entorno, junto con clústeres blue/green en una misma región**. Los grupos de nodos integrados de Auto Mode pueden utilizar varias zonas de disponibilidad configuradas. Los nombres de colores o las etiquetas de subred no limitan los nodos a una única zona. Para crear celdas de nodos de una sola zona, diseñe por separado la ubicación mediante NodePool/NodeClass, el enrutamiento y la capacidad de recuperación según la guía de [operaciones zonales](15-zonal-operations-guide.md).

Cree los archivos del ejemplo en un proyecto independiente llamado `eks-terraform/`. Terraform no hereda automáticamente los archivos `.tf` de un directorio padre `00-shared`; utilice las declaraciones de cada módulo raíz y evite copiar junto a ellas variables o valores locales duplicados. Antes de actualizar un estado existente con módulos v20/v5, revise las guías de migración y el plan real. Conserve el archivo `.terraform.lock.hcl` de cada módulo raíz y fije también las versiones de los módulos por separado.

El endpoint de la API es privado de forma predeterminada. La validación con kubectl y los controladores GitOps necesitan conectividad real con la API, por ejemplo mediante un runner en la VPC o una VPN. Esta guía no crea esa vía de acceso.

***

## Descripción general

Esta guía presenta una arquitectura de referencia de Terraform para desplegar clústeres de Amazon EKS con Auto Mode habilitado. El enfoque de tres capas separa las responsabilidades de infraestructura según la frecuencia de cambio, los equipos responsables y el alcance del impacto. Así, los equipos pueden trabajar de forma independiente y mantener la seguridad operativa.

**Principios de diseño clave:**

* **Separación de responsabilidades**: Cada capa tiene responsables y patrones de cambio diferenciados
* **Reducción del alcance del impacto**: Separar el estado reduce el alcance de los cambios; los fallos en las dependencias aún pueden afectar a otras capas
* **Aislamiento del estado**: Archivos de estado de Terraform independientes para cada capa
* **Preparado para GitOps**: Terraform administra la infraestructura de AWS; ArgoCD administra los recursos de Kubernetes

***

## 1. Introducción a la arquitectura de 3 capas

### ¿Por qué separar las capas?

Las configuraciones monolíticas tradicionales de Terraform crean varios desafíos operativos:

1. **Tiempos prolongados de Plan/Apply**: Cada cambio requiere evaluar todos los recursos
2. **Alcance del impacto**: Una sola configuración incorrecta puede afectar a toda la infraestructura
3. **Conflictos entre equipos**: Varios equipos compiten por el mismo archivo de estado
4. **Riesgo de cambio**: Agrupar los cambios de red con los de las aplicaciones aumenta el riesgo del despliegue

La arquitectura de tres capas aborda estos desafíos organizando la infraestructura en niveles diferenciados según su estabilidad y los equipos responsables.

### Características de las capas (frecuencias ilustrativas)

| Capa | Nombre | Frecuencia de cambio | Responsable principal | Alcance del impacto | Dependencias |
| ----- | -------- | ---------------- | ------------------- | ------------ | ---------------------- |
| 01 | Red | Trimestral | Equipo de infraestructura | Alto | Ninguna |
| 02 | Clúster | Mensual | Equipo de plataforma | Medio | 01-network |
| 03 | Plataforma | Semanal | Equipos de plataforma/aplicaciones | Los cambios de DNS o acceso pueden afectar al clúster | 01-network, 02-cluster |

### Estructura de directorios

```
eks-terraform/
├── 00-shared/
│   ├── variables.tf          # Common variables across all layers
│   ├── bootstrap/main.tf     # Local state creates the S3 backend
│   └── providers.tf.template # Provider configuration template
├── 01-network/
│   ├── main.tf               # VPC, subnets, NAT Gateway
│   ├── variables.tf          # Network-specific variables
│   ├── outputs.tf            # VPC ID, subnet IDs for downstream
│   ├── backend.tf            # S3 backend: network/terraform.tfstate
│   └── providers.tf
├── 02-cluster/
│   ├── main.tf               # EKS cluster with Auto Mode
│   ├── data.tf               # Remote state from 01-network
│   ├── variables.tf          # Cluster-specific variables
│   ├── outputs.tf            # Cluster endpoint, OIDC provider
│   ├── backend.tf            # S3 backend: cluster/terraform.tfstate
│   └── providers.tf
└── 03-platform/
    ├── main.tf               # Add-ons, Pod Identity, RBAC
    ├── data.tf               # Remote state from 01-network, 02-cluster
    ├── variables.tf          # Platform-specific variables
    ├── outputs.tf            # Add-on ARNs, role mappings
    ├── backend.tf            # S3 backend: platform/terraform.tfstate
    └── providers.tf
```

Incluya estas rutas en el archivo .gitignore del nuevo proyecto. Mantenga el archivo .terraform.lock.hcl de cada módulo raíz bajo control de versiones.

```text
.terraform/
.terraform-data/
.bootstrap-state/
*.tfstate
*.tfstate.*
*.tfplan
```

### Visualización del flujo de cambios

![Responsabilidades separadas para el estado de Terraform de red, clúster y plataforma, con dependencias compartidas durante la ejecución y claves de S3 distintas.](../.gitbook/assets/en-ops-01-infrastructure-setup-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-01-infrastructure-setup-0.html)

***

## 2. 00-shared: Configuración común

La capa compartida contiene plantillas de configuración y variables comunes para todas las capas. Son ejemplos de nomenclatura, no una configuración del directorio padre que se importe automáticamente.

### Configuración del backend de S3

Primero, cree el bucket de S3 para la administración del estado de Terraform:

> **Nota**: A partir de Terraform 1.10, el backend de S3 admite el bloqueo de estado nativo mediante `use_lockfile = true`, aprovechando las escrituras condicionales de S3. Esto elimina la necesidad de una tabla de DynamoDB para el bloqueo de estado.

```hcl
# 00-shared/bootstrap/main.tf
# Run this once to create backend infrastructure

terraform {
  backend "local" {}
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "eks-platform"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

locals {
  bucket_name = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
}

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = local.bucket_name

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = local.bucket_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket_name" {
  value = aws_s3_bucket.terraform_state.id
}

data "aws_caller_identity" "current" {}
```

### Variables comunes

```hcl
# 00-shared/variables.tf
# Common variables used across all layers

variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "eks-platform"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.project_name))
    error_message = "Project name must be lowercase, start with letter, 3-21 chars."
  }
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    ManagedBy = "terraform"
    Project   = "eks-platform"
  }
}

locals {
  # Standard naming convention
  name_prefix = "${var.project_name}-${var.environment}"

  # Merge common tags with environment
  tags = merge(var.common_tags, {
    Environment = var.environment
  })

  # Backend configuration
}
```

***

## 3. 01-network: Configuración de VPC

La capa de red establece la infraestructura básica de la VPC. Cambia con poca frecuencia y requiere una planificación cuidadosa por el amplio alcance de su impacto.

### Consideraciones de diseño

Esta distribución utiliza dos zonas de disponibilidad distintas. Blue/green identifica los entornos de despliegue; los grupos de nodos predeterminados de Auto Mode no están limitados a una sola zona. Dimensione los CIDR teniendo en cuenta la asignación de direcciones a Pods, las reservas de direcciones, las ENI de endpoints, el crecimiento y los demás recursos de la VPC. El /16 del ejemplo no es una recomendación universal de producción ni garantiza que no se agoten las IP.

### Configuración principal

```hcl
# 01-network/main.tf

terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Layer       = "network"
  }

  # Availability zones for blue/green clusters
  azs = var.availability_zones

  # Subnet CIDR allocation
  # VPC: 10.0.0.0/16 (65,536 IPs)
  # Public subnets:  10.0.0.0/20, 10.0.16.0/20  (4,096 IPs each)
  # Private subnets: 10.0.128.0/18, 10.0.192.0/18 (16,384 IPs each)
  public_subnets  = [cidrsubnet(var.vpc_cidr, 4, 0), cidrsubnet(var.vpc_cidr, 4, 1)]
  private_subnets = [cidrsubnet(var.vpc_cidr, 2, 2), cidrsubnet(var.vpc_cidr, 2, 3)]
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  public_subnets  = local.public_subnets
  private_subnets = local.private_subnets

  # NAT Gateway configuration
  enable_nat_gateway     = true
  single_nat_gateway     = false # One per AZ for HA
  one_nat_gateway_per_az = true

  # DNS settings
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  # Public subnet tags for EKS load balancers
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    Type                     = "public"
  }

  # Private subnet tags for EKS internal load balancers
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    Type                              = "private"
  }

  tags = local.tags
}

# Additional subnet tags for specific clusters
# Blue cluster (ap-northeast-2a)
# Green cluster (ap-northeast-2c)
# VPC endpoints reduce NAT traffic; compare endpoint hourly/data costs for the actual workload
module "vpc_endpoints" {
  source  = "terraform-aws-modules/vpc/aws//modules/vpc-endpoints"
  version = "6.7.3"

  vpc_id = module.vpc.vpc_id

  endpoints = {
    eks_auth = {
      service             = "eks-auth"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.vpc_endpoints.id]
    }

    s3 = {
      service      = "s3"
      service_type = "Gateway"
      route_table_ids = concat(
        module.vpc.private_route_table_ids,
        module.vpc.public_route_table_ids
      )
      tags = { Name = "${local.name_prefix}-s3-endpoint" }
    }
    ecr_api = {
      service             = "ecr.api"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.vpc_endpoints.id]
      tags                = { Name = "${local.name_prefix}-ecr-api-endpoint" }
    }
    ecr_dkr = {
      service             = "ecr.dkr"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.vpc_endpoints.id]
      tags                = { Name = "${local.name_prefix}-ecr-dkr-endpoint" }
    }
    sts = {
      service             = "sts"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.vpc_endpoints.id]
      tags                = { Name = "${local.name_prefix}-sts-endpoint" }
    }
    logs = {
      service             = "logs"
      private_dns_enabled = true
      subnet_ids          = module.vpc.private_subnets
      security_group_ids  = [aws_security_group.vpc_endpoints.id]
      tags                = { Name = "${local.name_prefix}-logs-endpoint" }
    }
  }

  tags = local.tags
}

# Security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.name_prefix}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-vpc-endpoints-sg"
  })
}
```

### Variables

```hcl
# 01-network/variables.tf

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
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

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Two distinct standard Availability Zones in the selected region"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Choose two distinct Availability Zones for this layout."
  }
}
```

### Salidas

```hcl
# 01-network/outputs.tf

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks"
  value       = module.vpc.private_subnets_cidr_blocks
}

output "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks"
  value       = module.vpc.public_subnets_cidr_blocks
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.natgw_ids
}

output "azs" {
  description = "Availability zones used"
  value       = module.vpc.azs
}

# Zone-specific outputs for blue/green clusters
output "blue_zone" {
  description = "Blue cluster availability zone"
  value       = module.vpc.azs[0]
}

output "green_zone" {
  description = "Green cluster availability zone"
  value       = module.vpc.azs[1]
}

output "blue_private_subnet_id" {
  description = "Blue cluster private subnet ID"
  value       = module.vpc.private_subnets[0]
}

output "green_private_subnet_id" {
  description = "Green cluster private subnet ID"
  value       = module.vpc.private_subnets[1]
}

output "blue_public_subnet_id" {
  description = "Blue cluster public subnet ID"
  value       = module.vpc.public_subnets[0]
}

output "green_public_subnet_id" {
  description = "Green cluster public subnet ID"
  value       = module.vpc.public_subnets[1]
}

output "vpc_endpoints_sg_id" {
  description = "VPC endpoints security group ID"
  value       = aws_security_group.vpc_endpoints.id
}
```

### Configuración del backend

```hcl
# 01-network/backend.tf

terraform {
  backend "s3" {
    key          = "network/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
```

***

## 4. 02-cluster: EKS Auto Mode

La capa de clúster despliega EKS con Auto Mode habilitado. Auto Mode simplifica las operaciones del clúster al automatizar la gestión del cómputo, las redes y el almacenamiento.

### Cómo funciona EKS Auto Mode

EKS Auto Mode proporciona:

* **Compute Auto Mode**: Aprovisionamiento y escalado automáticos de nodos
* **Network Auto Mode**: VPC CNI administrado con gestión automática de IP
* **Storage Auto Mode**: Integración administrada de almacenamiento en bloques; cree la StorageClass explícitamente

Para más detalles sobre EKS Auto Mode, consulte [Primeros pasos con EKS Auto Mode](../eks-auto-mode/01-getting-started.md).

### Fuentes de datos

```hcl
# 02-cluster/data.tf

# Reference network layer outputs
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "network/terraform.tfstate"
    region = var.region
  }
}

# Current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# EKS cluster auth for kubectl provider
```

### Configuración principal

```hcl
# 02-cluster/main.tf

terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

locals {
  name_prefix  = "${var.project_name}-${var.environment}"
  cluster_name = "${local.name_prefix}-${var.cluster_color}"

  tags = {
    Environment  = var.environment
    Project      = var.project_name
    ManagedBy    = "terraform"
    Layer        = "cluster"
    ClusterColor = var.cluster_color
  }

  # Network outputs from layer 01
  vpc_id             = data.terraform_remote_state.network.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
  public_subnet_ids  = data.terraform_remote_state.network.outputs.public_subnet_ids

  # Select subnet based on cluster color
  cluster_subnet_id = var.cluster_color == "blue" ? data.terraform_remote_state.network.outputs.blue_private_subnet_id : data.terraform_remote_state.network.outputs.green_private_subnet_id
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = local.cluster_name
  kubernetes_version = var.cluster_version

  # Network configuration
  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  # Cluster endpoint access
  endpoint_public_access  = false
  endpoint_private_access = true

  # EKS Auto Mode Configuration
  compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # Enable Auto Mode for networking
  # Enable Auto Mode for storage
  # Control plane logging
  cloudwatch_log_group_retention_in_days = var.log_retention_days

  enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  # Encryption configuration
  iam_role_use_name_prefix      = false
  node_iam_role_use_name_prefix = false
  create_kms_key                = false
  encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  # Access configuration - using Access Entries (recommended)
  authentication_mode = "API_AND_CONFIG_MAP"

  # Cluster access entries
  access_entries = {
    # Cluster admin
    admin = {
      kubernetes_groups = []
      principal_arn     = var.cluster_admin_arn
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

  tags = local.tags
}

# KMS key for EKS secrets encryption
resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS ${local.cluster_name} secrets encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.cluster_name}-eks-secrets"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.cluster_name}-eks-secrets"
  target_key_id = aws_kms_key.eks.key_id
}

# CloudWatch Log Group for EKS control plane logs
# Security group rules for cluster
resource "aws_security_group_rule" "cluster_ingress_vpc" {
  description       = "Allow VPC traffic to cluster API"
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [data.terraform_remote_state.network.outputs.vpc_cidr]
  security_group_id = module.eks.cluster_security_group_id
}
```

### Variables

```hcl
# 02-cluster/variables.tf

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "eks-platform"
}

variable "cluster_color" {
  description = "Cluster color identifier (blue or green)"
  type        = string
  default     = "blue"

  validation {
    condition     = contains(["blue", "green"], var.cluster_color)
    error_message = "Cluster color must be blue or green."
  }
}

variable "cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.36"
}

variable "cluster_admin_arn" {
  description = "IAM ARN for cluster admin access"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
```

### Salidas

```hcl
# 02-cluster/outputs.tf

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded cluster CA certificate"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = module.eks.cluster_version
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "node_security_group_id" {
  description = "EKS node security group ID"
  value       = module.eks.node_security_group_id
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN for IRSA"
  value       = module.eks.oidc_provider_arn
}

output "oidc_provider_url" {
  description = "OIDC provider URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "cluster_primary_security_group_id" {
  description = "EKS cluster primary security group ID"
  value       = module.eks.cluster_primary_security_group_id
}

output "kms_key_arn" {
  description = "KMS key ARN for secrets encryption"
  value       = aws_kms_key.eks.arn
}

output "cluster_color" {
  description = "Cluster color identifier"
  value       = var.cluster_color
}
```

### Configuración del backend

```hcl
# 02-cluster/backend.tf

terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

***

## 5. 03-platform: Complementos y Pod Identity

Evite duplicar el agente Pod Identity, la red de nodos o la integración de almacenamiento en bloques incorporados en Auto Mode mediante los complementos habituales aws-node/EBS CSI/agente. [Auto Mode actual](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) ejecuta **CoreDNS local en cada nodo como servicio del sistema**. Un clúster compuesto únicamente por nodos Auto Mode no necesita un Deployment de CoreDNS. Los clústeres mixtos que contienen nodos ajenos a Auto Mode deben conservar ese Deployment: establezca enable_coredns_addon=true y fije una versión compatible. El ejemplo utiliza false de forma predeterminada. Cree mediante GitOps la StorageClass de Auto Mode con ebs.csi.eks.amazonaws.com siguiendo las [instrucciones oficiales](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html).

Este ejemplo de Pod Identity permite que el **controlador External Secrets lea valores de Secrets Manager/SSM identificados explícitamente por nombre**. Una asociación no instala ESO ni crea su ServiceAccount: configure mediante GitOps el mismo namespace y la misma cuenta de servicio, y use una cadena de credenciales predeterminada de un SDK compatible. El descubrimiento mediante ListSecrets queda fuera de esta política mínima. Las claves KMS administradas por el cliente también requieren kms:Decrypt sobre los ARN de las claves necesarias y autorización en la política de la clave.

La descarga de imágenes utiliza los permisos del kubelet o del rol del nodo, no el Pod Identity de la aplicación. Configure por separado la autenticación de ArgoCD con el EKS de destino y la renovación de tokens OCI/ECR mediante las guías de [instalación de ArgoCD](../gitops/argocd/01-installation.md) y [aplicaciones](../gitops/argocd/02-applications.md). Los administradores de la capa de clúster son responsables de sus entradas de acceso; no cree de nuevo el mismo principal en la capa de plataforma.


La capa de plataforma administra los complementos de EKS, las asociaciones de Pod Identity y las entradas de acceso de los equipos de aplicaciones. Esta capa cambia con frecuencia a medida que se incorporan equipos y evolucionan los requisitos de las aplicaciones.

### Fuentes de datos

```hcl
# 03-platform/data.tf

# Reference network layer
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "network/terraform.tfstate"
    region = var.region
  }
}

# Reference cluster layer
data "terraform_remote_state" "cluster" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "cluster/${var.cluster_color}/terraform.tfstate"
    region = var.region
  }
}

# Current AWS account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# EKS cluster auth
```

### Configuración principal

```hcl
# 03-platform/main.tf

terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

locals {
  name_prefix  = "${var.project_name}-${var.environment}"
  cluster_name = data.terraform_remote_state.cluster.outputs.cluster_name

  tags = {
    Environment  = var.environment
    Project      = var.project_name
    ManagedBy    = "terraform"
    Layer        = "platform"
    ClusterColor = var.cluster_color
  }
}

#------------------------------------------------------------------------------
# EKS Add-ons
#------------------------------------------------------------------------------

# Optional CoreDNS Deployment for mixed clusters; pure Auto Mode uses node-local CoreDNS
resource "aws_eks_addon" "coredns" {
  count = var.enable_coredns_addon ? 1 : 0
  cluster_name = local.cluster_name
  addon_name   = "coredns"

  addon_version               = var.coredns_addon_version
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = local.tags
}

#------------------------------------------------------------------------------
# Pod Identity Associations
#------------------------------------------------------------------------------

# External Secrets Operator Pod Identity
resource "aws_eks_pod_identity_association" "external_secrets" {
  cluster_name    = local.cluster_name
  namespace       = "external-secrets"
  service_account = "external-secrets"
  role_arn        = aws_iam_role.external_secrets.arn

  tags = local.tags
}

resource "aws_iam_role" "external_secrets" {
  name = "${local.cluster_name}-external-secrets-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
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
            "aws:RequestTag/eks-cluster-arn"            = "arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${local.cluster_name}"
            "aws:RequestTag/kubernetes-namespace"       = "external-secrets"
            "aws:RequestTag/kubernetes-service-account" = "external-secrets"
          }
        }
      }
    ]
  })

  tags = local.tags
}

# External Secrets Secrets Manager access
resource "aws_iam_role_policy" "external_secrets_sm" {
  name = "secrets-manager-access"
  role = aws_iam_role.external_secrets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      }
    ]
  })
}

#------------------------------------------------------------------------------
# Access Entries for Teams
#------------------------------------------------------------------------------

# Developer access (namespace-scoped)
resource "aws_eks_access_entry" "developers" {
  for_each = var.developer_roles

  cluster_name  = local.cluster_name
  principal_arn = each.value.arn
  type          = "STANDARD"

  tags = local.tags
}

resource "aws_eks_access_policy_association" "developers" {
  for_each = var.developer_roles

  cluster_name  = local.cluster_name
  principal_arn = each.value.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy"

  access_scope {
    type       = "namespace"
    namespaces = each.value.namespaces
  }

  depends_on = [aws_eks_access_entry.developers]
}

# Read-only access for monitoring
resource "aws_eks_access_entry" "readonly" {
  for_each = var.readonly_roles

  cluster_name  = local.cluster_name
  principal_arn = each.value
  type          = "STANDARD"

  tags = local.tags
}

resource "aws_eks_access_policy_association" "readonly" {
  for_each = var.readonly_roles

  cluster_name  = local.cluster_name
  principal_arn = each.value
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.readonly]
}
# If named secrets or SecureString parameters use customer-managed KMS keys,
# grant this ESO role kms:Decrypt on the required key ARNs and allow it in the key policy.
```

### Variables

```hcl
# 03-platform/variables.tf

variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "eks-platform"
}

variable "cluster_color" {
  description = "Cluster color identifier"
  type        = string
  default     = "blue"
}

variable "developer_roles" {
  description = "Developer IAM roles and their namespace access"
  type = map(object({
    arn        = string
    namespaces = list(string)
  }))
  default = {}
}

variable "readonly_roles" {
  description = "Read-only IAM role ARNs"
  type        = map(string)
  default     = {}
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

### Salidas

```hcl
# 03-platform/outputs.tf

output "external_secrets_role_arn" {
  description = "External Secrets IAM role ARN"
  value       = aws_iam_role.external_secrets.arn
}


output "coredns_addon_version" {
  value = var.enable_coredns_addon ? aws_eks_addon.coredns[0].addon_version : null
}
```

### Configuración del backend

```hcl
# 03-platform/backend.tf

terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
```

***

## 6. Integración entre capas

### Patrón de estado remoto

La fuente de datos terraform_remote_state expone las salidas del módulo raíz, pero quien la lee puede acceder a la instantánea completa del estado. No constituye un límite de seguridad que permita acceder solo a las salidas. Entre ámbitos con distintos niveles de confianza, considere publicar únicamente los valores necesarios por un canal separado, como los parámetros de SSM.

```hcl
# Pattern: Consuming outputs from another layer
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}-tfstate"
    key    = "network/terraform.tfstate"
    region = "ap-northeast-2"
  }
}

# Usage
locals {
  vpc_id = data.terraform_remote_state.network.outputs.vpc_id
}
```

### Flujo de salidas/datos

![Diagrama de cómo las salidas de las capas de Terraform alimentan las entradas de la siguiente capa mediante referencias a terraform_remote_state.](../.gitbook/assets/en-ops-01-infrastructure-setup-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-01-infrastructure-setup-1.html)

### Buenas prácticas para gestionar el estado

1. **Use nombres de buckets coherentes**: `{project}-{env}-{account-id}-tfstate`
2. **Organice por capa y color**: `network/`, `cluster/blue/`, `platform/green/`
3. **Habilite el versionado**: Permite recuperarse de daños en el estado
4. **Habilite el cifrado**: Protege los valores sensibles del estado
5. **Use el bloqueo nativo de S3** (Terraform 1.10+): Habilite `use_lockfile = true` en la configuración del backend para bloquear el estado mediante escrituras condicionales de S3, sin DynamoDB

### Organización de archivos de estado

```
s3://eks-platform-prod-ACCOUNT_ID-tfstate/
├── network/
│   └── terraform.tfstate
├── cluster/
│   ├── blue/
│   │   └── terraform.tfstate
│   └── green/
│       └── terraform.tfstate
└── platform/
    ├── blue/
    │   └── terraform.tfstate
    └── green/
        └── terraform.tfstate
```

***

## 7. Validación

### Orden de despliegue

Este procedimiento es para un proyecto nuevo. Requiere AWS CLI, Terraform, jq y permisos de despliegue. Establezca primero DOCS_ADMIN_ARN con el ARN IAM de un administrador real. Los comandos crean recursos: revise y confirme explícitamente el plan de cada terraform apply. Un clúster compuesto solo por nodos Auto Mode deshabilita el complemento CoreDNS. Establezca DOCS_ENABLE_COREDNS_ADDON=true únicamente al adaptar el ejemplo a clústeres mixtos, para consultar y fijar la versión del complemento. Los archivos de entrada generados contienen solo los valores obligatorios; incorpore cualquier etiqueta o permiso adicional de los equipos antes de generar el plan.

El bucket y la región proceden del JSON de backend generado. TF_DATA_DIR separa la cuenta, el entorno, el módulo raíz y el color del clúster. El ejemplo en inglés administra cada clúster en su propio estado. Proteja y respalde el estado de inicialización; exclúyalo de Git junto con .terraform-data/ y los archivos de plan. Evite reutilizar este procedimiento para migrar estados existentes.

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
  '{cluster_admin_arn:$admin, cluster_version:$version}' > "environments/$DOCS_ENV.cluster.tfvars.json"

# Isolate local bootstrap state by account and environment.
export TF_DATA_DIR="$DOCS_ROOT/.terraform-data/$DOCS_ACCOUNT_ID/$DOCS_ENV/bootstrap"
terraform -chdir=00-shared/bootstrap init \
  -backend-config="path=$DOCS_ROOT/.bootstrap-state/$DOCS_ACCOUNT_ID/$DOCS_ENV.tfstate"
terraform -chdir=00-shared/bootstrap plan -var-file="../../environments/$DOCS_ENV.tfvars.json"
# Review the plan. This apply presents its own plan and asks for confirmation.
terraform -chdir=00-shared/bootstrap apply -var-file="../../environments/$DOCS_ENV.tfvars.json"
DOCS_STATE_BUCKET="$(terraform -chdir=00-shared/bootstrap output -raw state_bucket_name)"
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

for DOCS_COLOR in blue green; do
  apply_layer 02-cluster "cluster/$DOCS_COLOR/terraform.tfstate" "cluster/$DOCS_COLOR"     -var-file="../environments/$DOCS_ENV.cluster.tfvars.json" -var="cluster_color=$DOCS_COLOR"
  apply_layer 03-platform "platform/$DOCS_COLOR/terraform.tfstate" "platform/$DOCS_COLOR"     -var-file="../environments/$DOCS_ENV.platform.tfvars.json" -var="cluster_color=$DOCS_COLOR"
done
```

### Comandos de verificación

Ejecute los comandos con credenciales de AWS CLI del principal administrador configurado. Las políticas de acceso de EKS no sustituyen el permiso IAM eks:DescribeCluster. La administración automática del creador de Terraform está deshabilitada; utilice un perfil de administrador o una configuración autorizada de AssumeRole cuando sea necesario. Estas comprobaciones abarcan el despliegue predeterminado de dos clústeres; omita los clústeres deshabilitados. Verifique las StorageClass después de configurarlas por separado mediante GitOps.

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

### Script de prueba básica

El siguiente script crea un namespace temporal con nombre único y un Job de DNS en cada contexto de Kubernetes seleccionado explícitamente. Comprueba la asignación de cargas de trabajo a nodos y el DNS del clúster, no el tráfico externo del balanceador ni todas las dependencias de las aplicaciones. La limpieza verifica el UID del namespace, y los fallos devuelven un código de salida distinto de cero. Si Docker Hub no está disponible, utilice una imagen replicada aprobada mediante DOCS_TEST_IMAGE.

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

Guarde el script como smoke-test.sh y seleccione explícitamente los contextos creados.

```bash
bash smoke-test.sh "blue-${DOCS_ENV}" "green-${DOCS_ENV}"
```

### Validación de Terraform

Utilice los mismos directorios de datos inicializados que en el procedimiento de despliegue. Un plan puede leer recursos de AWS y el estado remoto y adquirir un bloqueo del estado; no aplica los cambios de infraestructura propuestos.

```bash
export TF_DATA_DIR="$DOCS_ROOT/.terraform-data/$DOCS_ACCOUNT_ID/$DOCS_ENV/network"
terraform -chdir=01-network validate
terraform -chdir=01-network fmt -check
for DOCS_COLOR in blue green; do
  for DOCS_LAYER in cluster platform; do
    DOCS_DIR="02-cluster"
    [[ "$DOCS_LAYER" == platform ]] && DOCS_DIR="03-platform"
    export TF_DATA_DIR="$DOCS_ROOT/.terraform-data/$DOCS_ACCOUNT_ID/$DOCS_ENV/$DOCS_LAYER/$DOCS_COLOR"
    terraform -chdir="$DOCS_DIR" validate
    terraform -chdir="$DOCS_DIR" fmt -check
  done
done
```

***

## Principios de diseño clave

### Terraform administra solo la infraestructura de AWS

Esta arquitectura sigue una separación clara:

| Capa | Terraform administra | GitOps administra |
| ---------- | ---------------------------------- | ------------------------------- |
| Red | VPC, subredes, NAT, endpoints | - |
| Clúster | EKS, KMS, CloudWatch | - |
| Plataforma | Complementos, roles de IAM, entradas de acceso | - |
| Kubernetes | - | NodePool, Deployments, Services |

ArgoCD GitOps administra los recursos de Kubernetes, como las definiciones de NodePool y los Deployments de aplicaciones. Consulte [Configuración del pipeline de GitOps](04-gitops-multi-cluster.md) para más detalles.

### Referencias cruzadas

* [Primeros pasos con EKS Auto Mode](../eks-auto-mode/01-getting-started.md)
* [Prácticas recomendadas de seguridad de EKS](../eks/05-eks-security.md)
* [Enrutamiento ponderado NLB y clústeres Blue/Green](02-infrastructure-advanced.md)
* [Configuración del pipeline de GitOps](04-gitops-multi-cluster.md)

***

< [Tabla de contenido](./README.md) | [Siguiente: Enrutamiento ponderado NLB y clústeres Blue/Green](02-infrastructure-advanced.md) >
