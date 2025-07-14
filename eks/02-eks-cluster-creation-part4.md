# EKS 클러스터 생성 - 4부

## Terraform을 사용한 클러스터 생성

Terraform은 인프라를 코드로 관리하는 도구로, EKS 클러스터를 생성하고 관리하는 데 사용할 수 있습니다. Terraform을 사용하면 인프라를 버전 관리하고 반복 가능한 방식으로 배포할 수 있습니다.

### 1. Terraform 설치

먼저 Terraform을 설치해야 합니다:

**macOS**:
```bash
brew install terraform
```

**Linux**:
```bash
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install terraform
```

**Windows**:
```
https://www.terraform.io/downloads.html
```

### 2. 프로젝트 디렉토리 생성

Terraform 프로젝트를 위한 디렉토리를 생성합니다:

```bash
mkdir eks-terraform
cd eks-terraform
```

### 3. Terraform 구성 파일 작성

다음과 같은 Terraform 구성 파일을 작성합니다:

**providers.tf**:
```hcl
provider "aws" {
  region = "us-west-2"
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}
```

**variables.tf**:
```hcl
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "my-eks-cluster"
}

variable "cluster_version" {
  description = "Kubernetes version to use for the EKS cluster"
  type        = string
  default     = "1.26"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnets" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "node_groups" {
  description = "Map of EKS managed node group definitions"
  type        = map(any)
  default     = {
    ng1 = {
      name           = "node-group-1"
      instance_types = ["m5.large"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
      disk_size      = 80
    }
    ng2 = {
      name           = "node-group-2"
      instance_types = ["c5.xlarge"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
      disk_size      = 80
      capacity_type  = "SPOT"
    }
  }
}
```

**vpc.tf**:
```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 3.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/internal-elb"           = "1"
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

**eks.tf**:
```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 18.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  # EKS Managed Node Groups
  eks_managed_node_group_defaults = {
    disk_size      = 80
    instance_types = ["m5.large"]
  }

  eks_managed_node_groups = {
    for k, v in var.node_groups : k => {
      name           = v.name
      instance_types = v.instance_types
      min_size       = v.min_size
      max_size       = v.max_size
      desired_size   = v.desired_size
      disk_size      = v.disk_size
      capacity_type  = lookup(v, "capacity_type", "ON_DEMAND")
    }
  }

  # Fargate Profile
  fargate_profiles = {
    default = {
      name = "default"
      selectors = [
        {
          namespace = "default"
          labels = {
            env = "fargate"
          }
        }
      ]
    }
    kube-system = {
      name = "kube-system"
      selectors = [
        {
          namespace = "kube-system"
          labels = {
            k8s-app = "kube-dns"
          }
        }
      ]
    }
  }

  # Enable EKS Cluster CloudWatch Logging
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}
```

**outputs.tf**:
```hcl
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "config_map_aws_auth" {
  description = "A kubernetes configuration to authenticate to this EKS cluster"
  value       = module.eks.aws_auth_configmap_yaml
}

output "region" {
  description = "AWS region"
  value       = "us-west-2"
}
```

### 4. Terraform 초기화 및 적용

Terraform 구성 파일을 작성한 후 다음 명령을 실행하여 Terraform을 초기화하고 EKS 클러스터를 생성합니다:

```bash
# Terraform 초기화
terraform init

# 계획 확인
terraform plan

# 인프라 생성
terraform apply
```

`terraform apply` 명령을 실행하면 Terraform은 계획을 표시하고 확인을 요청합니다. `yes`를 입력하여 계획을 적용합니다.

### 5. kubeconfig 구성

Terraform 출력에서 클러스터 이름과 리전을 사용하여 kubeconfig를 구성합니다:

```bash
aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_id) \
  --region $(terraform output -raw region)
```

### 6. 클러스터 확인

클러스터가 올바르게 구성되었는지 확인합니다:

```bash
kubectl get nodes
```

### 7. 클러스터 삭제

클러스터를 삭제하려면 다음 명령을 실행합니다:

```bash
terraform destroy
```

## AWS CDK를 사용한 클러스터 생성

AWS Cloud Development Kit(CDK)는 익숙한 프로그래밍 언어를 사용하여 클라우드 인프라를 정의하는 도구입니다. CDK를 사용하면 TypeScript, Python, Java 또는 C#과 같은 언어로 EKS 클러스터를 생성하고 관리할 수 있습니다.

### 1. AWS CDK 설치

먼저 AWS CDK를 설치해야 합니다:

```bash
npm install -g aws-cdk
```

### 2. CDK 프로젝트 생성

CDK 프로젝트를 생성합니다:

```bash
mkdir eks-cdk
cd eks-cdk
cdk init app --language typescript
```

### 3. 필요한 패키지 설치

EKS 클러스터를 생성하는 데 필요한 패키지를 설치합니다:

```bash
npm install @aws-cdk/aws-eks @aws-cdk/aws-ec2 @aws-cdk/aws-iam
```

### 4. CDK 스택 정의

`lib/eks-cdk-stack.ts` 파일을 다음과 같이 수정합니다:

```typescript
import * as cdk from '@aws-cdk/core';
import * as ec2 from '@aws-cdk/aws-ec2';
import * as eks from '@aws-cdk/aws-eks';
import * as iam from '@aws-cdk/aws-iam';

export class EksCdkStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC 생성
    const vpc = new ec2.Vpc(this, 'EksVpc', {
      cidr: '10.0.0.0/16',
      natGateways: 1,
      maxAzs: 2,
      subnetConfiguration: [
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_NAT,
          cidrMask: 24,
        },
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // EKS 클러스터 생성
    const cluster = new eks.Cluster(this, 'EksCluster', {
      vpc,
      version: eks.KubernetesVersion.V1_26,
      defaultCapacity: 0,
    });

    // 관리형 노드 그룹 추가
    cluster.addNodegroupCapacity('ManagedNodeGroup', {
      instanceTypes: [new ec2.InstanceType('m5.large')],
      minSize: 1,
      maxSize: 3,
      desiredSize: 2,
      diskSize: 80,
    });

    // Spot 인스턴스를 사용하는 노드 그룹 추가
    cluster.addNodegroupCapacity('SpotNodeGroup', {
      instanceTypes: [
        new ec2.InstanceType('c5.large'),
        new ec2.InstanceType('c5a.large'),
        new ec2.InstanceType('c5d.large'),
      ],
      minSize: 1,
      maxSize: 3,
      desiredSize: 2,
      capacityType: eks.CapacityType.SPOT,
      diskSize: 80,
    });

    // Fargate 프로필 추가
    cluster.addFargateProfile('DefaultProfile', {
      selectors: [
        { namespace: 'default', labels: { env: 'fargate' } },
      ],
    });

    // 출력
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
    });

    new cdk.CfnOutput(this, 'ClusterArn', {
      value: cluster.clusterArn,
    });
  }
}
```

### 5. CDK 배포

CDK 스택을 배포합니다:

```bash
cdk bootstrap
cdk deploy
```

`cdk deploy` 명령을 실행하면 CDK는 변경 사항을 표시하고 확인을 요청합니다. `y`를 입력하여 배포를 진행합니다.

### 6. kubeconfig 구성

CDK 출력에서 클러스터 이름을 사용하여 kubeconfig를 구성합니다:

```bash
aws eks update-kubeconfig \
  --name $(aws cloudformation describe-stacks --stack-name EksCdkStack --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" --output text) \
  --region us-west-2
```

### 7. 클러스터 확인

클러스터가 올바르게 구성되었는지 확인합니다:

```bash
kubectl get nodes
```

### 8. 클러스터 삭제

클러스터를 삭제하려면 다음 명령을 실행합니다:

```bash
cdk destroy
```
