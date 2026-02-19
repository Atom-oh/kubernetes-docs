# Getting Started with Auto Mode

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: February 2025

This guide covers how to enable EKS Auto Mode on new clusters and how to convert existing clusters to use Auto Mode.

---

## Enabling Auto Mode on a New Cluster

### Creating a Cluster with eksctl

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

### Creating a Cluster with Terraform

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

### Creating a Cluster with AWS CDK

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

## Switching to Auto Mode on Existing Clusters

Here's how to switch from a cluster using existing managed node groups to Auto Mode.

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

## Configuration via AWS Console

1. Navigate to **Amazon EKS** service in AWS Console
2. Select **Create Cluster** or choose an existing cluster
3. Enable **Auto Mode** in the **Compute** tab
4. Select default NodePools (general-purpose, system)
5. Complete cluster creation or update

---

## Verifying Auto Mode Activation

After enabling Auto Mode, verify the configuration:

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

< [Previous: Overview](./README.md) | [Table of Contents](./README.md) | [Next: NodePool Configuration](./02-nodepool-configuration.md) >
