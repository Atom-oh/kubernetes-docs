# EKS Cluster Creation - Part 4: Creating Clusters Using Terraform and CDK

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: July 25, 2025

## Lab Environment Setup

To follow along with the examples in this document, you need the following tools and environment:

### Required Tools
- AWS CLI v2.0 or higher
- Terraform v1.0.0 or higher (for Terraform examples)
- AWS CDK v2.0 or higher (for CDK examples)
- kubectl v1.31 or higher
- Node.js v14 or higher (when using CDK)

### AWS Account Setup
1. An AWS account is required. If you don't have one, refer to [Create an AWS Account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/).
2. The following IAM permissions are required:
   - AmazonEKSClusterPolicy
   - AmazonEKSServicePolicy
   - AmazonVPCFullAccess
   - IAMFullAccess

### AWS CLI Configuration
```bash
aws configure
# Enter AWS Access Key ID, Secret Access Key, region, and output format.
```

### Local Development Environment (Optional)
To test Kubernetes locally, you can use one of the following tools:
- **minikube**: `brew install minikube` (macOS) or see [minikube installation guide](https://minikube.sigs.k8s.io/docs/start/)
- **kind**: `brew install kind` (macOS) or see [kind installation guide](https://kind.sigs.k8s.io/docs/user/quick-start/)

## Creating a Cluster Using Terraform

Terraform is a tool for managing infrastructure as code that can be used to create and manage EKS clusters. Using Terraform allows you to version control your infrastructure and deploy it in a repeatable manner.

### EKS Cluster Creation Process Using Terraform

![EKS Cluster Creation Process Using Terraform](../assets/generated-diagrams/terraform_eks_creation_process.drawio)

### Terraform Component Relationships

![Terraform Component Relationships](../assets/generated-diagrams/terraform_components_relationship.drawio)

    %% Apply classes
    class E,F awsService;
    class G,H,I,J awsService;
    class A,B,C,D userApp;
```

### 1. Install Terraform

First, you need to install Terraform:

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

### 2. Create Project Directory

Create a directory for the Terraform project:

```bash
mkdir eks-terraform
cd eks-terraform
```

### 3. Write Terraform Configuration Files

Write the following Terraform configuration files:

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

### 4. Initialize and Apply Terraform

After writing the Terraform configuration files, proceed with the following steps:

> **Important**: Verify that all configuration files are correctly written before execution.

#### 4.1 Initialize Terraform

First, initialize Terraform to download the required providers and modules:

```bash
terraform init
```

#### 4.2 Review Plan

Before applying changes, review the plan to preview what resources will be created:

```bash
terraform plan
```

This command shows a list of resources to be created and changes. Review the output carefully.

#### 4.3 Create Infrastructure

After reviewing the plan, if there are no issues, create the infrastructure with the following command:

```bash
terraform apply
```

When you run the `terraform apply` command, Terraform displays the plan again and asks for confirmation. Enter `yes` to apply the plan.

> **Note**: EKS cluster creation may take approximately 15-20 minutes.

When you run the `terraform apply` command, Terraform displays the plan and asks for confirmation. Enter `yes` to apply the plan.

### 5. Configure kubeconfig

Configure kubeconfig using the cluster name and region from the Terraform output:

```bash
aws eks update-kubeconfig \
  --name $(terraform output -raw cluster_id) \
  --region $(terraform output -raw region)
```

### 6. Verify Cluster

Verify that the cluster is configured correctly:

```bash
kubectl get nodes
```

### 7. Delete Cluster

To delete the cluster, run the following command:

```bash
terraform destroy
```

## Creating a Cluster Using AWS CDK

AWS Cloud Development Kit (CDK) is a tool for defining cloud infrastructure using familiar programming languages. With CDK, you can create and manage EKS clusters using languages like TypeScript, Python, Java, or C#.

### EKS Cluster Creation Process Using AWS CDK

![EKS Cluster Creation Process Using AWS CDK](../assets/generated-diagrams/cdk_eks_creation_process.drawio)

### CDK Component Relationships

![CDK Component Relationships](../assets/generated-diagrams/cdk_components_relationship.drawio)
    class F,G,H,I awsService;
    class A userApp;
```

### 1. Install AWS CDK

First, you need to install AWS CDK:

```bash
npm install -g aws-cdk
```

### 2. Create CDK Project

Create a CDK project:

```bash
mkdir eks-cdk
cd eks-cdk
cdk init app --language typescript
```

### 3. Install Required Packages

Install the packages required to create an EKS cluster:

```bash
npm install @aws-cdk/aws-eks @aws-cdk/aws-ec2 @aws-cdk/aws-iam
```

### 4. Define CDK Stack

Modify the `lib/eks-cdk-stack.ts` file as follows:

```typescript
import * as cdk from '@aws-cdk/core';
import * as ec2 from '@aws-cdk/aws-ec2';
import * as eks from '@aws-cdk/aws-eks';
import * as iam from '@aws-cdk/aws-iam';

export class EksCdkStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create VPC
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

    // Create EKS cluster
    const cluster = new eks.Cluster(this, 'EksCluster', {
      vpc,
      version: eks.KubernetesVersion.V1_26,
      defaultCapacity: 0,
    });

    // Add managed node group
    cluster.addNodegroupCapacity('ManagedNodeGroup', {
      instanceTypes: [new ec2.InstanceType('m5.large')],
      minSize: 1,
      maxSize: 3,
      desiredSize: 2,
      diskSize: 80,
    });

    // Add node group using Spot instances
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

    // Add Fargate profile
    cluster.addFargateProfile('DefaultProfile', {
      selectors: [
        { namespace: 'default', labels: { env: 'fargate' } },
      ],
    });

    // Outputs
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

### 5. Deploy CDK

Deploy the CDK stack:

```bash
cdk bootstrap
cdk deploy
```

When you run the `cdk deploy` command, CDK displays the changes and asks for confirmation. Enter `y` to proceed with deployment.

### 6. Configure kubeconfig

Configure kubeconfig using the cluster name from the CDK output:

```bash
aws eks update-kubeconfig \
  --name $(aws cloudformation describe-stacks --stack-name EksCdkStack --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" --output text) \
  --region us-west-2
```

### 7. Verify Cluster

Verify that the cluster is configured correctly:

```bash
kubectl get nodes
```

### 8. Delete Cluster

To delete the cluster, run the following command:

```bash
cdk destroy
```

## Extending EKS with Kubernetes Operators and CRDs

Kubernetes Operators and Custom Resource Definitions (CRDs) are powerful mechanisms for extending Kubernetes functionality. They allow you to create and manage custom resources in an EKS cluster.

### Kubernetes Operator Overview

![Kubernetes Operator Overview](../assets/generated-diagrams/kubernetes_operator_overview.drawio)

### Relationship Between Operator and CRD

![Operator and CRD Relationship](../assets/generated-diagrams/operator_crd_relationship.drawio)

### 1. What is an Operator?

A Kubernetes Operator is a software extension that encodes application-specific operational knowledge into software to manage services through the Kubernetes API. Operators automate tasks such as installing, updating, backing up, and recovering complex applications.

An Operator consists of the following components:

1. **Custom Resource Definition (CRD)**: Defines the schema for custom resources.
2. **Custom Resource (CR)**: Resource instances created according to the CRD.
3. **Controller**: A controller that monitors CR state and reconciles it to the desired state.

### 2. Custom Resource Definition (CRD)

CRDs allow you to extend the Kubernetes API to define custom resources. When you create a CRD, a new resource type is added to the Kubernetes API, allowing you to create and manage custom resources.

CRD Example:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.example.com
spec:
  group: example.com
  names:
    kind: Database
    listKind: DatabaseList
    plural: databases
    singular: database
    shortNames:
    - db
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              engine:
                type: string
              version:
                type: string
              storageSize:
                type: string
              replicas:
                type: integer
                minimum: 1
            required:
            - engine
            - version
            - storageSize
          status:
            type: object
            properties:
              phase:
                type: string
              message:
                type: string
```

### 3. Using Operators in EKS

Here's how to use Operators in EKS:

1. **Install Operator**: Install the Operator using Helm, YAML manifests, or Operator Lifecycle Manager (OLM).
2. **Create CRD**: Create the CRD that the Operator will use.
3. **Create Custom Resource**: Create a Custom Resource according to the CRD.
4. **Verify Operator Behavior**: Verify that the Operator detects the Custom Resource and performs the necessary actions.

### 4. Popular Kubernetes Operators

Popular Operators that can be used with EKS include:

1. **Prometheus Operator**: Manages the Prometheus monitoring stack.
2. **Elasticsearch Operator**: Manages Elasticsearch clusters.
3. **PostgreSQL Operator**: Manages PostgreSQL databases.
4. **Kafka Operator**: Manages Kafka clusters.
5. **Istio Operator**: Manages the Istio service mesh.

### 5. Operator Development Tools

Tools that can be used to develop Operators include:

1. **Operator SDK**: A framework for quickly developing and deploying Operators.
2. **Kubebuilder**: A framework for extending the Kubernetes API.
3. **KUDO (Kubernetes Universal Declarative Operator)**: A tool for creating Operators declaratively.

### 6. Managing CRDs and Operators with Terraform and CDK

You can deploy CRDs and Operators to an EKS cluster using Terraform and AWS CDK.

**Deploying CRD with Terraform**:

```hcl
resource "kubernetes_manifest" "database_crd" {
  manifest = {
    apiVersion = "apiextensions.k8s.io/v1"
    kind       = "CustomResourceDefinition"
    metadata = {
      name = "databases.example.com"
    }
    spec = {
      group = "example.com"
      names = {
        kind     = "Database"
        listKind = "DatabaseList"
        plural   = "databases"
        singular = "database"
        shortNames = ["db"]
      }
      scope = "Namespaced"
      versions = [{
        name    = "v1"
        served  = true
        storage = true
        schema = {
          openAPIV3Schema = {
            type = "object"
            properties = {
              spec = {
                type = "object"
                properties = {
                  engine = {
                    type = "string"
                  }
                  version = {
                    type = "string"
                  }
                  storageSize = {
                    type = "string"
                  }
                  replicas = {
                    type = "integer"
                    minimum = 1
                  }
                }
                required = ["engine", "version", "storageSize"]
              }
              status = {
                type = "object"
                properties = {
                  phase = {
                    type = "string"
                  }
                  message = {
                    type = "string"
                  }
                }
              }
            }
          }
        }
      }]
    }
  }
}
```

**Deploying CRD with AWS CDK**:

```typescript
import * as cdk from '@aws-cdk/core';
import * as eks from '@aws-cdk/aws-eks';

export class EksCrdStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Reference existing EKS cluster
    const cluster = eks.Cluster.fromClusterAttributes(this, 'ImportedCluster', {
      clusterName: 'my-eks-cluster',
      kubectlRoleArn: 'arn:aws:iam::account:role/role-name',
    });

    // Apply CRD manifest
    cluster.addManifest('DatabaseCRD', {
      apiVersion: 'apiextensions.k8s.io/v1',
      kind: 'CustomResourceDefinition',
      metadata: {
        name: 'databases.example.com',
      },
      spec: {
        group: 'example.com',
        names: {
          kind: 'Database',
          listKind: 'DatabaseList',
          plural: 'databases',
          singular: 'database',
          shortNames: ['db'],
        },
        scope: 'Namespaced',
        versions: [{
          name: 'v1',
          served: true,
          storage: true,
          schema: {
            openAPIV3Schema: {
              type: 'object',
              properties: {
                spec: {
                  type: 'object',
                  properties: {
                    engine: {
                      type: 'string',
                    },
                    version: {
                      type: 'string',
                    },
                    storageSize: {
                      type: 'string',
                    },
                    replicas: {
                      type: 'integer',
                      minimum: 1,
                    },
                  },
                  required: ['engine', 'version', 'storageSize'],
                },
                status: {
                  type: 'object',
                  properties: {
                    phase: {
                      type: 'string',
                    },
                    message: {
                      type: 'string',
                    },
                  },
                },
              },
            },
          },
        }],
      },
    });
  }
}
```

## Learn More

In this document, we learned how to create an EKS cluster using Terraform and AWS CDK, and how to extend EKS using Kubernetes Operators and CRDs. You can deepen your understanding of EKS through the following topics:

- [EKS Cluster Creation - Part 1: Prerequisites](./02-eks-cluster-creation-part1.md) - Prerequisites for EKS cluster creation
- [EKS Cluster Creation - Part 2: Creating Clusters Using eksctl](./02-eks-cluster-creation-part2.md) - How to create EKS clusters using eksctl
- [EKS Cluster Creation - Part 3: Creating Clusters Using AWS Management Console and CLI](./02-eks-cluster-creation-part3.md) - How to create EKS clusters using AWS Management Console and CLI
- [EKS Cluster Creation - Part 5: Cluster Access, Validation, Upgrade, and Deletion](./02-eks-cluster-creation-part5.md) - How to manage EKS clusters
- [EKS Networking - Part 1: Basic Concepts and VPC Configuration](./03-eks-networking-part1.md) - Basic concepts of EKS networking
- [EKS Security](./05-eks-security.md) - Security configuration for EKS clusters
- [Kubernetes Extensions](../core/11-extending-kubernetes.md) - Details on extending the Kubernetes API

### Related Tools and Integrations

- [ArgoCD](../tools/01-argocd.md) - Declarative continuous deployment tool for GitOps
- [AWS Controllers for Kubernetes (ACK)](../tools/03-ack.md) - Managing AWS resources from Kubernetes
- [Karpenter](../tools/06-karpenter.md) - Automating node provisioning for Kubernetes clusters

### Lab Environment Setup

To follow along with the examples in this document, you need the following tools:

- AWS CLI v2.0 or higher
- Terraform v1.0.0 or higher
- AWS CDK v2.0 or higher
- kubectl v1.31 or higher
- Node.js v14 or higher (when using CDK)

Your AWS account requires the following IAM permissions:
- AmazonEKSClusterPolicy
- AmazonEKSServicePolicy
- AmazonVPCFullAccess
- IAMFullAccess

To test in a local development environment, you can use [minikube](https://minikube.sigs.k8s.io/) or [kind](https://kind.sigs.k8s.io/).

## Glossary

The key terms and abbreviations used in this document are as follows:

| Term | Description |
|------|-------------|
| **EKS** | Abbreviation for Amazon Elastic Kubernetes Service, a managed Kubernetes service provided by AWS. |
| **Kubernetes** | An open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. |
| **Cluster** | The basic unit of Kubernetes, consisting of a control plane and nodes. |
| **Node** | A worker machine in a Kubernetes cluster that runs containerized applications. |
| **Pod** | The smallest deployment unit in Kubernetes, containing one or more containers. |
| **Terraform** | A tool developed by HashiCorp for managing infrastructure as code. |
| **CDK** | Abbreviation for AWS Cloud Development Kit, a tool for defining cloud infrastructure using familiar programming languages. |
| **Operator** | A software extension that encodes application-specific operational knowledge by extending the Kubernetes API. |
| **CRD** | Abbreviation for Custom Resource Definition, a feature that allows you to extend the Kubernetes API to define custom resources. |
| **IAM** | Abbreviation for Identity and Access Management, a service that securely controls access to AWS resources. |
| **VPC** | Abbreviation for Virtual Private Cloud, a logically isolated virtual network within the AWS cloud. |

## Quiz

To test what you learned in this chapter, try the [EKS Cluster Creation - Part 4 Quiz](../quizzes/eks/02-eks-cluster-creation-part4-quiz.md).
