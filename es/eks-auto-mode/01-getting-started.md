# Primeros pasos con Auto Mode

> **Versiones compatibles**: EKS 1.29+, EKS Auto Mode GA
> **Última actualización**: February 19, 2026

Esta guía cubre cómo habilitar EKS Auto Mode en clusters nuevos y cómo convertir clusters existentes para que usen Auto Mode.

---

## Habilitar Auto Mode en un cluster nuevo

### Crear un cluster con eksctl

```yaml
# cluster-auto-mode.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-auto-mode-cluster
  region: ap-northeast-2
  version: "1.31"

# Enable Auto Mode
autoModeConfig:
  enabled: true
  # Auto-create default NodePools
  nodePools:
    - general-purpose
    - system

vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    publicAccess: true
    privateAccess: true

# Auto-create IAM OIDC Provider
iam:
  withOIDC: true
```

```bash
# Create cluster
eksctl create cluster -f cluster-auto-mode.yaml

# Verify creation
kubectl get nodepools
```

### Crear un cluster con Terraform

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "eks-auto-mode-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# EKS Cluster with Auto Mode
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "my-auto-mode-cluster"
  cluster_version = "1.31"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Enable Auto Mode
  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }

  # OIDC Provider
  enable_irsa = true

  tags = {
    Environment = "production"
    Terraform   = "true"
  }
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_name" {
  value = module.eks.cluster_name
}
```

```bash
# Run Terraform
terraform init
terraform plan
terraform apply
```

### Crear un cluster con AWS CDK

```typescript
// lib/eks-auto-mode-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create VPC
    const vpc = new ec2.Vpc(this, 'EksVpc', {
      maxAzs: 3,
      natGateways: 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });

    // EKS Cluster with Auto Mode
    const cluster = new eks.Cluster(this, 'EksAutoModeCluster', {
      version: eks.KubernetesVersion.V1_31,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      defaultCapacity: 0, // Auto Mode disables default capacity
      clusterName: 'my-auto-mode-cluster',
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,
    });

    // Enable Auto Mode (using CfnCluster)
    const cfnCluster = cluster.node.defaultChild as eks.CfnCluster;
    cfnCluster.computeConfig = {
      enabled: true,
      nodePools: ['general-purpose', 'system'],
    };

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
    });
  }
}
```

---

## Cambiar a Auto Mode en clusters existentes

Así es como se cambia de un cluster que usa managed node groups existentes a Auto Mode.

```bash
# 1. Check current cluster state
aws eks describe-cluster --name my-cluster --query 'cluster.computeConfig'

# 2. Enable Auto Mode
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=true,nodePools=general-purpose,nodePools=system

# 3. Check update status
aws eks describe-update \
    --name my-cluster \
    --update-id <update-id>

# 4. Verify NodePool creation
kubectl get nodepools

# 5. Verify coexistence with existing node groups
kubectl get nodes -L eks.amazonaws.com/compute-type
```

---

## Configuración mediante AWS Console

1. Navegue al servicio **Amazon EKS** en AWS Console
2. Seleccione **Create Cluster** o elija un cluster existente
3. Habilite **Auto Mode** en la pestaña **Compute**
4. Seleccione los NodePools predeterminados (general-purpose, system)
5. Complete la creación o actualización del cluster

---

## Verificar la activación de Auto Mode

Después de habilitar Auto Mode, verifique la configuración:

```bash
# Check cluster compute configuration
aws eks describe-cluster --name my-cluster \
    --query 'cluster.computeConfig'

# List available NodePools
kubectl get nodepools

# Check NodePool details
kubectl describe nodepool general-purpose
kubectl describe nodepool system

# Verify nodes are being provisioned
kubectl get nodes -w
```

---

< [Anterior: Descripción general](./README.md) | [Tabla de contenido](./README.md) | [Siguiente: Configuración de NodePool](./02-nodepool-configuration.md) >
