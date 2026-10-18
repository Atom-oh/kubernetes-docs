# Creación de clústeres EKS - Parte 4: Creación de clústeres con Terraform

> **Versiones de ejemplo**: Amazon EKS 1.36; Terraform 1.16.6; proveedor de AWS 6.69.1; módulo EKS 21.29.0
> **Última actualización**: October 16, 2026

## Ejemplo de Terraform en tres capas

Terraform administra la infraestructura como código. Este ejemplo usa el proveedor de AWS 6.x y fija las versiones del módulo EKS en **21.29.0** y del módulo VPC en **6.7.3**. El HCL se verificó con Terraform 1.16.6 y el proveedor de AWS 6.69.1; no se ejecutaron implementaciones en AWS ni se comprobó el comportamiento en producción. Las entradas originales de estilo v20 `cluster_*` son incompatibles con la versión 21 del módulo: usa `name`, `kubernetes_version`, `addons` y los demás nombres de v21 que se muestran a continuación.

Los estados separados pueden ayudar a los equipos a dividir responsabilidades y revisar los cambios según su ciclo de vida. No eliminan las dependencias ni el impacto operativo: un cambio en la red aún puede interrumpir un clúster, y un cambio en un complemento o en una política de acceso puede afectar a todas las cargas de trabajo. Esta es una estructura de ejemplo, no una arquitectura de producción probada.

### Arquitectura de 3 capas

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

### Por qué separar las capas

| Capa | Cambios | Responsable | Radio de impacto |
|-------|---------|--------------|--------------|
| 01-network | Poco frecuentes, a modo de ejemplo | Equipo de infraestructura | VPC/subredes y conectividad dependiente |
| 02-cluster | Mensuales | Equipo de plataforma | Clúster EKS, nodos |
| 03-platform | Semanales | Equipo de plataforma / aplicaciones | Complementos, RBAC, Pod Identity |

Cada capa tiene una clave de estado y un plan distintos. Aun así, se necesitan permisos de IAM y responsables de CI separados, y se deben coordinar los cambios entre capas. Separar los estados no garantiza que un cambio en un complemento deje intacto el comportamiento del clúster.

### Backend S3 compartido

Los ejemplos usan el bloqueo nativo de S3 con `use_lockfile = true` (Terraform 1.10+), con una clave distinta para cada entorno/capa. Crea el bucket de backend por separado, habilita el control de versiones, el cifrado y Block Public Access, y reemplaza cada instancia de `REPLACE_WITH_YOUR_STATE_BUCKET` antes de la inicialización. Concede únicamente el acceso necesario a la clave de estado y los permisos Get/Put/Delete sobre su objeto `.tflock`. El bloqueo de DynamoDB está obsoleto; coordina todos los clientes al migrar un backend existente en lugar de simplemente eliminar su tabla de bloqueos.

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

`terraform_remote_state` expone las salidas raíz a HCL, pero quien las lee puede recuperar **la instantánea de estado completa**, incluidos los valores sensibles. No crea una dependencia de orden de aplicación entre proyectos separados. Publica los valores seleccionados mediante una interfaz controlada por separado cuando un equipo consumidor no deba poder leer el estado completo.

---

## Capa 1: Red (01-network)

Este ejemplo crea una VPC en tres AZ con una gateway NAT para mantener pequeño el laboratorio. Una sola NAT crea una dependencia de AZ y puede generar cargos por transferencia entre AZ. Antes de usarla en producción, revisa un diseño de salida resiliente a las fallas de AZ, la capacidad de las subredes, DNS y los endpoints privados.

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

> **La detección de subredes** depende de la versión del Load Balancer Controller, los feature gates y las reglas de elegibilidad de las subredes, no de la versión del módulo Terraform EKS. Las etiquetas de función que se muestran ayudan a seleccionar subredes públicas/privadas; verifica también la cobertura de AZ, las direcciones libres, las rutas y cualquier filtrado de etiquetas del clúster.

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

Esta capa crea un **clúster EC2 convencional nuevo**, grupos de nodos administrados y complementos principales. Establece explícitamente el valor existente de `cluster_admin_role_arn`; quien ejecuta Terraform no recibe automáticamente permisos de administración de Kubernetes. El operador debe poder asumir ese rol. Para acceder al endpoint privado, se necesita un entorno de administración conectado y con rutas configuradas antes de usar kubectl o instalar la plataforma.

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

Los discos raíz de los grupos de nodos usan asignaciones de dispositivos de bloques de una plantilla de lanzamiento; se ignora `disk_size` cuando este módulo usa su plantilla de lanzamiento personalizada predeterminada. El ejemplo usa el cifrado de sobres predeterminado de AWS para la API de Kubernetes. Una clave KMS del cliente es una decisión de diseño independiente.

Revisa los valores predeterminados del módulo antes de la implementación: el rol de IAM para nodos administrados de este módulo fijado incluye permisos de ECR ReadOnly y CNI IPv4. Estos valores predeterminados hacen que el ejemplo sea funcional, pero no implican que se trate de permisos mínimos para producción. Es preferible usar una identidad CNI dedicada y un rol de nodo revisado explícitamente (incluido ECR PullOnly cuando sea suficiente). Los valores min/max del grupo de nodos no instalan un autoscaler.

La compilación predeterminada compatible puede cambiar cuando Terraform vuelve a evaluar sus fuentes de datos. Resuelve y registra las compilaciones compatibles con el clúster de destino y usa `addon_version` cuando la reproducibilidad requiera fijar una versión. Conserva la configuración personalizada revisada al actualizar.

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

## Capa 3: Plataforma (03-platform)

La capa de plataforma EC2 estándar administra complementos adicionales, asociaciones de Pod Identity y acceso para desarrolladores/lectores. Su estado es independiente, pero sus cambios pueden afectar la seguridad del clúster y la disponibilidad de las cargas de trabajo. Las alternativas Auto Mode e Hybrid que aparecen más adelante requieren seleccionar archivos de plataforma distintos.

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

Crea el nuevo namespace `app-dev` y el ServiceAccount `app-sa` mediante el responsable de Kubernetes/GitOps antes de probar la aplicación. La asociación EKS no crea ninguno de estos objetos. El ejemplo concede acceso de lectura únicamente al prefijo `app/` del bucket aprobado; las políticas del bucket, el cifrado de KMS y el acceso entre cuentas pueden requerir permisos adicionales revisados. Verifica el rol que se asume realmente y ten en cuenta la propagación de IAM y de la asociación antes de depender de ella.

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

EKS Pod Identity es una opción para las cargas de trabajo compatibles, no un reemplazo universal de IRSA. No necesita un proveedor IAM OIDC. Hay rutas compatibles para EC2 Linux convencional, Auto Mode y Hybrid Nodes configurados adecuadamente; Fargate y Windows requieren otro mecanismo de identidad compatible. IRSA sigue siendo compatible.

### Cómo funciona Pod Identity

1. Los nodos compatibles convencionales usan el DaemonSet de Pod Identity Agent. Auto Mode proporciona esta capacidad; Hybrid Nodes necesitan la configuración documentada del archivo de credenciales y un DaemonSet dedicado.
2. Se crea un rol de IAM con una política de confianza de Pod Identity (en la Capa 3).
3. El rol se asocia a una cuenta de servicio de Kubernetes mediante `aws_eks_pod_identity_association`.
4. Un SDK compatible que use su cadena de credenciales predeterminada obtiene credenciales temporales. Las credenciales estáticas existentes que aparezcan antes en esa cadena pueden prevalecer sobre esta ruta; verifica la identidad real.

Los recursos de Pod Identity que se muestran arriba en `03-platform/pod-identity.tf` siguen este patrón. La política de confianza del rol de IAM usa `pods.eks.amazonaws.com` como principal y `sts:TagSession` habilita el etiquetado automático de sesiones con metadatos del clúster, el namespace y la cuenta de servicio.

### Pod Identity frente a IRSA

| Función | Pod Identity | IRSA |
|---------|-------------|------|
| ¿Se requiere un proveedor OIDC? | No | Sí |
| Compatibilidad entre cuentas | Delegación explícita de roles, incluido `targetRoleArn` cuando sea compatible; requiere confianza/permisos | Confianza OIDC en la cuenta de destino o encadenamiento explícito de roles |
| Complejidad de configuración | Baja (una sola asociación) | Media (OIDC, rol, anotación) |
| Etiquetas de sesión | Etiquetas de contexto EKS automáticas cuando están habilitadas | Sin etiquetas automáticas de contexto EKS Pod Identity |
| Reutilización | Un rol puede servir para varias asociaciones revisadas | Un rol puede confiar en varios emisores/sujetos OIDC con alcance explícito |

> Elige un mecanismo de identidad compatible con el tipo de cómputo y el SDK. `sts:TagSession` agrega etiquetas; por sí mismo, no establece confianza entre cuentas. Las políticas de confianza anteriores requieren que las etiquetas de sesión permanezcan habilitadas. El módulo puede crear un proveedor OIDC para uso opcional de IRSA, de manera independiente de Pod Identity.

---

## Clúster EKS Auto Mode

Elige esta **alternativa para un clúster nuevo antes de la implementación inicial**; reemplazar una configuración de clúster ya aplicada no es un procedimiento de migración. Auto Mode administra las capacidades de cómputo e infraestructura. Su ejemplo de Auto Mode puro no define grupos de nodos administrados y usa la entrada `compute_config` del módulo v21:

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

### Puntos clave

- **`compute_config.enabled = true`** habilita las capacidades de cómputo, balanceo de carga y almacenamiento en bloque mediante este módulo. Revisa las políticas de IAM que crea el módulo fijado.
- **`node_pools`** especifica cuáles grupos de nodos integrados se habilitarán (`general-purpose`, `system`).
- El módulo v21 establece de forma fija en `false` la configuración `bootstrap_self_managed_addons` subyacente; no es una entrada del módulo. Auto Mode actualmente también incluye DNS del clúster, además de capacidades de red, almacenamiento y Pod Identity, por lo que los complementos tradicionales equivalentes son redundantes en el cómputo de Auto Mode.
- Esta variante no tiene grupos de nodos administrados. Se admiten clústeres con cómputo mixto, pero los nodos que no sean de Auto Mode siguen necesitando sus complementos y configuración de ubicación aplicables.
- Auto Mode aprovisiona instancias EC2 a partir de los grupos de nodos y administra la aplicación de parches del sistema operativo, el escalado y el ciclo de vida.

---

Para Auto Mode puro, omite el archivo estándar `03-platform/addons.tf`: su controlador EBS CSI tradicional no es el controlador de almacenamiento de Auto Mode. Usa el aprovisionador de Auto Mode `ebs.csi.eks.amazonaws.com` en una StorageClass revisada. Los archivos de Pod Identity de la aplicación y de entradas de acceso pueden seguir utilizándose una vez cumplidos sus requisitos previos.

## EKS Hybrid Nodes

Esta es una **alternativa nueva de plano de control solo para entornos híbridos**, no una receta completa para aprovisionar hosts ni una conversión en el lugar. Configura por separado VPN/Direct Connect u otra red enrutada compatible, DNS, reglas de firewall, un sistema operativo compatible y un proveedor de credenciales. Cuando termine esta capa del clúster, sigue la configuración de nodeadm/CNI y conecta el cómputo híbrido antes de esperar que el complemento CoreDNS esté listo.

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

### Puntos clave

- **`remote_network_config`** declara CIDR no superpuestos para nodos/Pods remotos; no crea VPN, rutas, firewalls ni un CNI. El módulo v21 recibe objetos que contienen `cidrs`, no listas de esos objetos.
- Los Hybrid Nodes se autentican mediante un rol de IAM con el tipo de entrada de acceso `HYBRID_LINUX`.
- Los Hybrid Nodes se conectan a la API privada por TCP 443; el plano de control se conecta **de salida a los kubelets híbridos** por TCP 10250. Configura el firewall local correspondiente y las rutas necesarias para Pods/webhooks; dos reglas de SG no constituyen un diseño de red completo.
- VPC CNI no se usa en Hybrid Nodes; debes configurar un CNI alternativo (p. ej., Cilium) en el entorno local.

---

El rol SSM anterior también admite la cancelación del registro de nodeadm con alcance limitado. Etiqueta las instancias administradas/activaciones SSM independientes con `EKSClusterARN = local.cluster_arn` para que coincidan con esa política. Las instalaciones/actualizaciones nuevas de SSM requieren nodeadm 1.0.19 o posterior debido al cambio de clave de firma. No almacenes secretos de activación en el código fuente de Terraform ni publiques estados que los contengan.

El archivo de plataforma EBS CSI estándar no corresponde a discos locales. Después de configurar el nodo híbrido/CNI, usa una composición de plataforma revisada por separado. Lo siguiente reemplaza la administración de los complementos principales estándar para la variante solo híbrida; no lo agregues a una configuración que ya administre los mismos complementos:

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

Antes de usar Pod Identity de aplicaciones en Hybrid Nodes, configura el DaemonSet híbrido del agente compatible, el archivo de credenciales del nodo y el permiso de nodo `eks-auth:AssumeRoleForPodIdentity`. La configuración básica de SSM anterior no concede ese permiso opcional. Sigue la guía específica de complementos de Hybrid Nodes; crear solo una asociación no es suficiente.

## Administración de complementos

Para la variante EC2 convencional, la capa del clúster administra CoreDNS, VPC CNI, kube-proxy y Pod Identity Agent. La capa de plataforma administra EBS CSI e identidades de aplicaciones. Auto Mode y Hybrid tienen distintos requisitos de componentes y orden de instalación; no apliques sin cambios los archivos de plataforma estándar a esas variantes.

### Opciones clave

| Opción | Descripción |
|--------|-------------|
| `most_recent` | Si es true, resuelve la compilación compatible más reciente durante la evaluación de Terraform; si es false, selecciona la opción predeterminada de EKS. No es un servicio de actualización autónomo. Para mayor reproducibilidad, es preferible usar un `addon_version` revisado. |
| `before_compute` | Ordena la creación de complementos administrados por el módulo antes que la de los grupos de nodos. Es útil para inicializar VPC CNI; no es un requisito universal para todos los complementos. CoreDNS necesita cómputo utilizable para alcanzar el estado correcto. |
| `configuration_values` | Cadena JSON con ajustes específicos del complemento (p. ej., delegación de prefijos de VPC CNI). |
| `service_account_role_arn` | ARN de rol de IRSA; Pod Identity usa `pod_identity_association` en su lugar. |
| `resolve_conflicts_on_create` | `NONE` expone los conflictos para que se revisen. Usa `OVERWRITE` solo en una migración revisada desde una instalación existente. |
| `resolve_conflicts_on_update` | `PRESERVE` conserva las personalizaciones en conflicto cuando es compatible; usa el esquema del complemento/configurationValues para los campos administrados. `OVERWRITE` puede descartar cambios. |

### Pod Identity para complementos

Algunos complementos admiten directamente asociaciones de Pod Identity. La configuración del controlador EBS CSI en `03-platform/addons.tf` muestra este patrón mediante `pod_identity_association`:

Usa el recurso completo `03-platform/addons.tf` que aparece arriba. El bloque anidado `pod_identity_association` pertenece al complemento; no crees también una asociación independiente para esa misma ServiceAccount.

---

## Control de acceso basado en Access Entry

La administración inicial de Kubernetes se configura mediante una entrada de acceso explícita en `02-cluster`; las entradas de desarrollador/lector corresponden a `03-platform`. Las asociaciones de políticas hacen referencia a los recursos de entrada de acceso para establecer el orden de Terraform. Los cambios del modo de acceso a la API son una decisión de migración: habilitar la API no se puede revertir simplemente a un diseño que use solo ConfigMap.

### Modo de autenticación

| Modo | Descripción |
|------|-------------|
| `API` | Solo Access Entries (recomendado para clústeres nuevos). |
| `API_AND_CONFIG_MAP` | Access Entries y ConfigMap `aws-auth` (periodo de migración). |
| `CONFIG_MAP` | Solo el `aws-auth` heredado (no recomendado). |

### ARN de políticas de acceso disponibles

| Política | ARN | Descripción |
|--------|-----|-------------|
| Administrador del clúster | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy` | Acceso completo al clúster |
| Administrador | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy` | Administración de Kubernetes dentro del alcance de acceso seleccionado; no concede permisos de IAM de AWS |
| Edición | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSEditPolicy` | Lectura/escritura en la mayoría de los recursos |
| Visualización | `arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy` | Acceso de lectura a los recursos de Kubernetes incluidos, no acceso general a Secret |

---

## Flujo de implementación

Estos comandos corresponden al **ejemplo estándar de tres capas con EC2**, una vez aprovisionado el backend y configurados la autorización de roles y los requisitos de red privada. Establece las variables requeridas de Terraform (`cluster_admin_role_arn` en la capa 2; `developer_role_arn`, `viewer_role_arn` y `app_bucket_name` en la capa 3) mediante archivos de variables revisados o valores `TF_VAR_*`. Usa la cuenta y la región de AWS previstas. Las alternativas Auto Mode/Hybrid requieren los cambios en los archivos y en la inicialización descritos anteriormente.

### Planifica y aplica una capa a la vez

Usa una ruta absoluta al proyecto para que cambiar el directorio del shell no seleccione la capa equivocada. Primero inicializa y guarda el plan de red:

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
Revisa la creación, sustitución/eliminación de recursos, IAM, exposición de red y costos en ese plan guardado. Protege los archivos del plan porque pueden contener datos sensibles. Aplica únicamente el archivo revisado:

```bash
# Run only after reviewing this saved plan; a saved-plan apply does not prompt again.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed.tfplan
```
Después de completar correctamente una capa, repite los pasos de planificación/revisión/aplicación con `TF_LAYER=02-cluster` y luego con `TF_LAYER=03-platform`. Si se produce un error, detén el avance; no apliques un estado posterior con salidas faltantes u obsoletas. Confirma los archivos de bloqueo de proveedores revisados, pero mantén el estado, kubeconfigs, credenciales y archivos de plan fuera del repositorio de código fuente.

La guía anterior estimaba entre 10 y 15 minutos para crear el clúster. Esa estimación no se midió ni se reprodujo en esta auditoría; la capacidad, los complementos, IAM y la red pueden cambiar la duración.

### Configura kubeconfig

Cuando termine la capa del clúster, usa el rol de administrador seleccionado explícitamente. La identidad actual de AWS debe tener permiso para asumirlo; si en cambio te autenticas directamente como una entidad principal ya autorizada, usa la ruta de credenciales revisada correspondiente.

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
### Valida el resultado

Para el ejemplo estándar de EC2, inspecciona los nodos reales, los Pods del sistema y el estado de los complementos administrados:

```bash
: "${EXAMPLE_KUBECONFIG:?}" "${EKS_CLUSTER_NAME:?}" "${EKS_REGION:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" wait --for=condition=Ready nodes --all --timeout=5m
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get pods
aws eks list-addons --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
aws eks describe-addon --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --addon-name coredns --query 'addon.{status:status,version:addonVersion,health:health}'
```
Repite `describe-addon` para los complementos esperados. Enumerar los DaemonSet por sí solo no demuestra que los complementos EKS estén en buen estado. Comprueba la autenticación de la API, DNS, la red, el almacenamiento y la identidad AWS real de la aplicación; durante esta auditoría no se ejecutaron comprobaciones en vivo de este tipo. Los clústeres de Auto Mode puro y solo híbridos necesitan las rutas de validación correspondientes y podrían no tener los mismos Pods del sistema.

### Destruye en orden inverso

Primero haz una copia de seguridad de los datos y elimina, mediante sus controladores, los balanceadores de carga y los recursos de volúmenes creados por Kubernetes, revisando el comportamiento de recuperación de PVC/PV. Conserva los controladores y los permisos de IAM hasta que se complete esa limpieza. Luego guarda y revisa el plan de destrucción de la plataforma:

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
Aplica solo después de verificar que el estado seleccionado y cada eliminación propuesta pertenecen a este entorno:

```bash
# Run only after reviewing this exact destruction plan.
: "${TF_PROJECT_DIR:?}" "${TF_LAYER:?}"
terraform -chdir="$TF_PROJECT_DIR/$TF_LAYER" apply reviewed-destroy.tfplan
```
Cuando termine correctamente, repite el proceso con `02-cluster` y, por último, con `01-network`. Detente ante los errores e investiga las ENI, los balanceadores de carga, los volúmenes y los finalizadores restantes. Un plan de destrucción también puede programar la eliminación de las claves KMS administradas en ese estado; conserva las claves necesarias para los datos cifrados que se mantengan. Conserva el backend administrado de forma independiente, las versiones de estado y las pruebas necesarias para la recuperación.

---

## Prácticas recomendadas

### Administración del estado

Usa claves de estado S3 distintas y el bloqueo nativo. Los bloqueos protegen frente a escrituras simultáneas en un mismo estado; no coordinan implementaciones entre los tres estados.

- **Habilita el control de versiones** en el bucket S3 para recuperarte de daños accidentales en el estado.
- **Restringe el acceso al bucket** con políticas de IAM: solo las canalizaciones de CI/CD y los operadores autorizados deben poder leer/escribir el estado.
- **Nunca edites manualmente los archivos de estado**; usa los comandos `terraform state` cuando sea necesario manipular el estado.

### Versionado de módulos

- `~> 21.0` permite versiones menores y de parche anteriores a 22.0; `~> 21.0.0` restringe las actualizaciones a 21.0.x. Ninguna de las dos garantiza la compatibilidad. Este ejemplo fija explícitamente las versiones de los módulos; `.terraform.lock.hcl` bloquea los proveedores, no las versiones de módulos remotos.
- Revisa el CHANGELOG del módulo antes de actualizar a versiones principales nuevas.
- Prueba primero las actualizaciones en un entorno que no sea de producción.

### Separación de entornos

Separa los entornos con uno de estos métodos:

| Método | Ventajas | Desventajas |
|----------|------|------|
| **Directorios separados** | Aislamiento claro, estado independiente | Duplicación de código |
| **Workspaces de Terraform** | Una sola base de código, cambio sencillo | Backend compartido, aislamiento limitado |
| **Terragrunt** | Configuración y orquestación reutilizables | Herramientas adicionales; el aislamiento sigue requiriendo estados y permisos separados |

En la arquitectura multicapa, el método más habitual es usar **directorios separados por entorno**, donde cada entorno tiene su propio árbol `01-network/`, `02-cluster/`, `03-platform/` con distintos valores de variables y claves de estado.

### Estrategia de etiquetado

Aplica etiquetas coherentes para la asignación de costos, el cumplimiento y la administración de recursos:

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

- [Creación de clústeres EKS - Parte 1: Requisitos previos](./02-eks-cluster-creation-part1.md): Requisitos previos para crear un clúster EKS
- [Creación de clústeres EKS - Parte 2: Creación de clústeres con eksctl](./02-eks-cluster-creation-part2.md): Creación de clústeres EKS con eksctl
- [Creación de clústeres EKS - Parte 3: Creación de clústeres con la consola y la CLI de AWS](./02-eks-cluster-creation-part3.md): Creación de clústeres EKS mediante la consola y la CLI
- [Creación de clústeres EKS - Parte 5: Acceso, validación, actualización y eliminación de clústeres](./02-eks-cluster-creation-part5.md): Administración de clústeres EKS
- [Redes de EKS - Parte 1: Conceptos básicos y configuración de VPC](./03-eks-networking-part1.md): Fundamentos de redes de EKS
- [Seguridad de EKS](./05-eks-security.md): Configuración de seguridad para clústeres EKS

### Temas relacionados

- [ArgoCD](../gitops/argocd/README.md): Implementación continua de GitOps
- [AWS Controllers for Kubernetes (ACK)](../platform-engineering/02-ack.md): Administración de recursos de AWS desde Kubernetes
- [Karpenter](../autoscaling/02-karpenter.md): Automatización del aprovisionamiento de nodos
- [Extensiones de Kubernetes](../core/11-extending-kubernetes.md): Ampliación de la API de Kubernetes con Operators y CRD

## Glosario

| Término | Descripción |
|------|-------------|
| **EKS** | Amazon Elastic Kubernetes Service, un servicio de Kubernetes administrado que ofrece AWS. |
| **Terraform** | Herramienta de HashiCorp para aprovisionar y administrar recursos en la nube mediante infraestructura como código. |
| **Access Entry** | Mecanismo de EKS basado en la API para conceder acceso a un clúster a entidades principales de IAM; reemplaza el ConfigMap `aws-auth`. |
| **Pod Identity** | Función de EKS que proporciona credenciales de AWS a los Pods sin requerir un proveedor OIDC. |
| **Auto Mode** | Modo de EKS en el que AWS administra por completo el aprovisionamiento de nodos, el escalado y las actualizaciones del sistema operativo. |
| **Hybrid Nodes** | Función de EKS que permite que servidores locales o de borde se unan a un clúster EKS como nodos de trabajo. |
| **IAM** | Identity and Access Management, que controla el acceso a los recursos de AWS. |
| **VPC** | Virtual Private Cloud, una red virtual aislada lógicamente dentro de AWS. |
| **IRSA** | IAM Roles for Service Accounts, un mecanismo de identidad de cargas de trabajo basado en OIDC compatible. |
| **Remote State** | Función de Terraform que permite que una configuración lea las salidas del archivo de estado de otra configuración. |

## Cuestionario

Para comprobar lo que aprendiste en este capítulo, prueba el [Cuestionario sobre creación de clústeres EKS - Parte 4](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md).


## Referencias de verificación

- [Migración del módulo EKS v21](https://github.com/terraform-aws-modules/terraform-aws-eks/blob/v21.29.0/docs/UPGRADE-21.0.md)
- [Bloqueo del backend S3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Acceso al estado remoto](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Confianza de roles de Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html)
- [Complementos de EKS y Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [Credenciales de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [Redes de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [Complementos de Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
