# Auto Mode 시작하기

> **지원 버전**: EKS 1.29+, EKS Auto Mode GA
> **마지막 업데이트**: 2026년 2월 19일

< [이전: 목차](./README.md) | [목차](./README.md) | [다음: NodePool 구성](./02-nodepool-configuration.md) >

---

이 문서에서는 EKS Auto Mode를 새 클러스터 또는 기존 클러스터에서 활성화하는 방법을 설명합니다. eksctl, Terraform, AWS CDK, 그리고 AWS 콘솔을 사용한 설정 방법을 다룹니다.

## 새 클러스터에서 Auto Mode 활성화

### eksctl을 사용한 클러스터 생성

```yaml
# cluster-auto-mode.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-auto-mode-cluster
  region: ap-northeast-2
  version: "1.31"

# Auto Mode 활성화
autoModeConfig:
  enabled: true
  # 기본 NodePool 자동 생성
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

# IAM OIDC Provider 자동 생성
iam:
  withOIDC: true
```

```bash
# 클러스터 생성
eksctl create cluster -f cluster-auto-mode.yaml

# 생성 확인
kubectl get nodepools
```

### Terraform을 사용한 클러스터 생성

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

# VPC 모듈
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

# EKS 클러스터 with Auto Mode
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "my-auto-mode-cluster"
  cluster_version = "1.31"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Auto Mode 활성화
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
# Terraform 실행
terraform init
terraform plan
terraform apply
```

### AWS CDK를 사용한 클러스터 생성

```typescript
// lib/eks-auto-mode-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC 생성
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

    // EKS 클러스터 with Auto Mode
    const cluster = new eks.Cluster(this, 'EksAutoModeCluster', {
      version: eks.KubernetesVersion.V1_31,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      defaultCapacity: 0, // Auto Mode는 기본 용량 비활성화
      clusterName: 'my-auto-mode-cluster',
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,
    });

    // Auto Mode 활성화 (CfnCluster 사용)
    const cfnCluster = cluster.node.defaultChild as eks.CfnCluster;
    cfnCluster.computeConfig = {
      enabled: true,
      nodePools: ['general-purpose', 'system'],
    };

    // 출력
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
    });
  }
}
```

## 기존 클러스터에서 Auto Mode 전환

기존 관리형 노드 그룹을 사용하는 클러스터에서 Auto Mode로 전환하는 방법입니다.

```bash
# 1. 현재 클러스터 상태 확인
aws eks describe-cluster --name my-cluster --query 'cluster.computeConfig'

# 2. Auto Mode 활성화
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=true,nodePools=general-purpose,nodePools=system

# 3. 업데이트 상태 확인
aws eks describe-update \
    --name my-cluster \
    --update-id <update-id>

# 4. NodePool 생성 확인
kubectl get nodepools

# 5. 기존 노드 그룹과 공존 확인
kubectl get nodes -L eks.amazonaws.com/compute-type
```

## AWS 콘솔에서 설정

1. AWS 콘솔에서 **Amazon EKS** 서비스로 이동
2. **클러스터 생성** 또는 기존 클러스터 선택
3. **컴퓨팅** 탭에서 **Auto Mode** 활성화
4. 기본 NodePool 선택 (general-purpose, system)
5. 클러스터 생성 또는 업데이트 완료

---

< [이전: 목차](./README.md) | [목차](./README.md) | [다음: NodePool 구성](./02-nodepool-configuration.md) >
