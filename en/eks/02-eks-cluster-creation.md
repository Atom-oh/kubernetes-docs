# EKS Cluster Creation

There are several ways to create an Amazon EKS cluster. In this chapter, we will learn in detail how to create an EKS cluster using various tools and methods.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Creating a Cluster Using eksctl](#creating-a-cluster-using-eksctl)
3. [Creating a Cluster Using AWS Management Console](#creating-a-cluster-using-aws-management-console)
4. [Creating a Cluster Using AWS CLI](#creating-a-cluster-using-aws-cli)
5. [Creating a Cluster Using Terraform](#creating-a-cluster-using-terraform)
6. [Creating a Cluster Using AWS CDK](#creating-a-cluster-using-aws-cdk)
7. [Configuring Cluster Access](#configuring-cluster-access)
8. [Cluster Validation](#cluster-validation)
9. [Cluster Upgrade](#cluster-upgrade)
10. [Cluster Deletion](#cluster-deletion)

## Prerequisites

Before creating an EKS cluster, the following prerequisites are required:

### 1. AWS Account

A valid AWS account is required. If you don't have an AWS account, you can sign up at the [AWS website](https://aws.amazon.com/).

### 2. IAM Permissions

The following IAM permissions are required to create and manage an EKS cluster:

- `eks:*`
- `ec2:*`
- `iam:*`
- `cloudformation:*`

If you have administrator permissions, no additional permission settings are required. Otherwise, you need to attach the following IAM policy to the user or role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:*",
        "ec2:*",
        "iam:*",
        "cloudformation:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Tool Installation

The following tools must be installed to create and manage an EKS cluster:

#### AWS CLI

AWS CLI is a unified tool for controlling AWS services from the command line.

**macOS**:
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows**:
```
https://awscli.amazonaws.com/AWSCLIV2.msi
```

After installing AWS CLI, run the following command to configure credentials:
```bash
aws configure
```

#### kubectl

kubectl is a command-line tool for communicating with Kubernetes clusters.

**macOS**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Linux**:
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Windows**:
```bash
curl -LO "https://dl.k8s.io/release/v1.26.0/bin/windows/amd64/kubectl.exe"
```

#### eksctl

eksctl is a simple CLI tool for creating and managing EKS clusters.

**macOS**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

Or:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Linux**:
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Windows**:
```bash
# PowerShell
$version = (Invoke-WebRequest -Uri "https://api.github.com/repos/weaveworks/eksctl/releases/latest" | ConvertFrom-Json).tag_name
Invoke-WebRequest -Uri "https://github.com/weaveworks/eksctl/releases/download/$version/eksctl_Windows_amd64.zip" -OutFile eksctl.zip
Expand-Archive -Path eksctl.zip -DestinationPath $env:USERPROFILE\.eksctl\bin
$env:PATH += ";$env:USERPROFILE\.eksctl\bin"
```

### 4. VPC and Subnets

An EKS cluster requires a VPC and subnets. You can use an existing VPC or create a new one. The VPC for an EKS cluster must meet the following requirements:

- At least 2 subnets must be in different availability zones.
- Subnets must have internet access (through a NAT gateway or internet gateway).
- Subnets must have sufficient IP addresses.
- Subnets must have appropriate tags.

#### VPC Tags for EKS Cluster

The following tags must be applied to enable the EKS cluster to use the VPC and subnets correctly:

**VPC Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Public Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/internal-elb`: `1`

## Creating a Cluster Using eksctl

eksctl is the simplest way to create and manage EKS clusters. eksctl uses CloudFormation to create EKS clusters and related resources.

### Basic Cluster Creation

To create the most basic form of an EKS cluster, run the following command:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

This command creates a cluster with the following default settings:
- 2 m5.large nodes
- New VPC and subnets
- Default Amazon Linux 2 AMI
- Latest Kubernetes version

### Creating a Cluster Using a Configuration File

For more complex configurations, you can define the cluster using a YAML file:

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-eks-cluster
  region: us-west-2
  version: "1.26"

vpc:
  id: vpc-12345678
  subnets:
    private:
      us-west-2a:
        id: subnet-12345678
      us-west-2b:
        id: subnet-87654321
    public:
      us-west-2a:
        id: subnet-23456789
      us-west-2b:
        id: subnet-98765432

managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    privateNetworking: true
    volumeSize: 80
    volumeType: gp3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: true
        ebs: true
        fsx: true
        efs: true
        albIngress: true
        xRay: true
        cloudWatch: true

  - name: ng-2
    instanceType: c5.xlarge
    desiredCapacity: 2
    privateNetworking: true
    spot: true

autoModeConfig:
  enabled: true
  # Create default node pools (general-purpose, system)
  # If nodePools is not specified, defaults are used
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

fargate:
  profiles:
    - name: fp-default
      selectors:
        - namespace: default
          labels:
            env: fargate
    - name: fp-kube-system
      selectors:
        - namespace: kube-system
          labels:
            k8s-app: kube-dns

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
```

To create a cluster using this configuration file, run the following command:

```bash
eksctl create cluster -f cluster.yaml
```

### Creating Managed Node Groups

To add a managed node group to an existing cluster, run the following command:

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --ssh-access \
  --ssh-public-key my-key
```

Or you can use a configuration file:

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

managedNodeGroups:
  - name: my-nodegroup
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 1
    maxSize: 5
    volumeSize: 80
    volumeType: gp3
    ssh:
      allow: true
      publicKeyName: my-key
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### Creating an EKS Auto Mode Cluster

EKS Auto Mode is a new feature released in 2024 that automates Kubernetes cluster infrastructure to significantly reduce operational overhead. Auto Mode automatically handles infrastructure management including compute, networking, and storage.

#### Key Features of EKS Auto Mode

- **Automated Node Management**: Automatically adds/removes nodes based on workload requirements
- **Enhanced Security**: Immutable AMI, SELinux enforcing mode, read-only root filesystem
- **Automatic Upgrades**: Regular security patches and updates with 21-day maximum node lifetime
- **Integrated Components**: Pod networking, DNS, storage, GPU support provided by default
- **Cost Optimization**: Automatic termination of unused instances and workload consolidation

#### Basic Auto Mode Cluster Creation

```bash
eksctl create cluster --name my-auto-cluster --enable-auto-mode --region us-west-2
```

#### Creating an Auto Mode Cluster Using a Configuration File

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-auto-cluster
  region: us-west-2
  version: "1.31"

# EKS Auto Mode configuration
autoModeConfig:
  enabled: true
  # Create default node pools (general-purpose, system)
  # If nodePools is not specified, defaults are used
  # nodePools: ["general-purpose", "system"]
  # nodeRoleARN: arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole

# VPC configuration (optional)
vpc:
  cidr: "10.0.0.0/16"
  nat:
    gateway: Single # Or HighlyAvailable
  clusterEndpoints:
    privateAccess: true
    publicAccess: true

# Cluster logging
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]

# Add-on configuration
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
```

Create cluster:
```bash
eksctl create cluster -f auto-cluster.yaml
```

#### Auto Mode vs Traditional Approach Comparison

| Feature | Traditional EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| Node Management | Manual managed node groups | Automatic node management |
| Scaling | Cluster Autoscaler setup required | Built-in auto scaling |
| Upgrades | Manual upgrades | Automatic upgrades (21-day cycle) |
| Security | User configured | Enhanced security by default |
| Networking | CNI plugin setup | Automatic networking configuration |
| Storage | CSI driver installation required | EBS CSI automatically provided |
| GPU Support | Manual driver installation | Automatic GPU support |

#### Auto Mode Cluster Validation

After the cluster is created, you can check its status with the following commands:

```bash
# Check cluster status
kubectl get nodes

# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check system pod status
kubectl get pods -n kube-system
```

#### Creating Custom Node Pools

In Auto Mode, you can create custom node pools in addition to the default node pools:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-nodepool
spec:
  template:
    metadata:
      labels:
        workload-type: gpu
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["p3.2xlarge", "p3.8xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-nodeclass
  limits:
    cpu: 1000
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-nodeclass
spec:
  amiFamily: AL2
  instanceStorePolicy: RAID0
  userData: |
    #!/bin/bash
    /etc/eks/bootstrap.sh my-auto-cluster
```

#### Auto Mode Limitations

- No direct node access via SSH or SSM
- Maximum node lifetime of 21 days (automatic replacement)
- Cannot modify default node pools and node classes
- Certain instance type restrictions possible

#### Auto Mode Monitoring

Auto Mode clusters are integrated with CloudWatch and automatically collect metrics:

```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EKS \
  --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value=my-auto-cluster \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Average
```

### Creating Fargate Profiles

To create a Fargate profile, run the following command:

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

Or you can use a configuration file:

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

fargate:
  profiles:
    - name: my-fargate-profile
      selectors:
        - namespace: default
          labels:
            env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### Updating a Cluster

You can update an existing cluster using eksctl:

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### Deleting a Cluster

You can delete a cluster using eksctl:

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## Creating a Cluster Using AWS Management Console

The steps to create an EKS cluster using the AWS Management Console are as follows:

1. Log in to the [AWS Management Console](https://console.aws.amazon.com/).
2. Search for "EKS" or select "Elastic Kubernetes Service" from the services list.
3. On the "Clusters" page, click the "Create cluster" button.

### Creating an EKS Auto Mode Cluster (Quick Configuration)

Using EKS Auto Mode, you can create a production-ready cluster with minimal configuration.

#### 1. Select Quick Configuration

4. Ensure the "Quick configuration" option is selected.
5. Enter the following information:
   - **Cluster name**: Enter a unique name for the cluster.
   - **Kubernetes version**: Select the Kubernetes version to use (latest version recommended).

#### 2. Configure IAM Roles

6. **Cluster IAM role** selection:
   - For your first Auto Mode cluster, use the "Create recommended role" option.
   - If you have an existing role, you can reuse it.
   - Recommended role name: `AmazonEKSAutoClusterRole`

7. **Node IAM role** selection:
   - For your first Auto Mode cluster, use the "Create recommended role" option.
   - Recommended role name: `AmazonEKSAutoNodeRole`

#### 3. Configure Networking

8. **Select VPC**:
   - Create new VPC: Select the "Create VPC" option to create a new VPC for EKS.
   - Use existing VPC: Select a previously created EKS VPC.

9. **Subnet configuration** (optional):
   - EKS Auto Mode automatically selects private subnets in the VPC.
   - You can add or remove subnets as needed.

#### 4. Review Configuration and Create

10. Select **View quick configuration defaults** to review all configuration values.
11. Click **Create cluster**. (Cluster creation takes approximately 15 minutes)

### Creating a Cluster with Custom Configuration

If you need more granular control, you can use custom configuration.

### Cluster Configuration

4. On the "Configure cluster" page, enter the following information:
   - **Cluster name**: Enter a unique name for the cluster.
   - **Kubernetes version**: Select the Kubernetes version to use.
   - **Cluster service role**: Create a new role or select an existing role.
   - **EKS Auto Mode**: Check the checkbox to enable Auto Mode.
   - **Tags**: Add tags if needed.
   - Click the "Next" button.

### Specify Networking

5. On the "Specify networking" page, enter the following information:
   - **VPC**: Create a new VPC or select an existing VPC.
   - **Subnets**: Select the subnets to use for the cluster. At least 2 subnets must be in different availability zones.
   - **Security groups**: Select the security groups to use for the cluster.
   - **Cluster endpoint access**: Configure access to the cluster API server endpoint.
     - **Public**: The API server can be accessed from the internet.
     - **Private**: The API server can only be accessed from within the VPC.
     - **Public and Private**: The API server can be accessed from both the internet and within the VPC.
   - Click the "Next" button.

### Configure Logging

6. On the "Configure logging" page, enter the following information:
   - **Control plane logging**: Select the log types to enable.
     - API server logs
     - Audit logs
     - Authenticator logs
     - Controller manager logs
     - Scheduler logs
   - Click the "Next" button.

### Select Add-ons

7. On the "Select add-ons" page, enter the following information:
   - **Amazon VPC CNI**: CNI plugin for pod networking.
   - **CoreDNS**: DNS service within the cluster.
   - **kube-proxy**: Provides network proxy and load balancing.
   - **Amazon EBS CSI Driver**: Automatically included in EKS Auto Mode.
   - Click the "Next" button.

### Review and Create

8. On the "Review and create" page, review the configuration and click the "Create" button.

### Adding Node Groups for Non-Auto Mode Clusters

If you are not using EKS Auto Mode, you need to manually add node groups after cluster creation.

### Add Node Group

1. On the "Node group configuration" page, enter the following information:
   - **Node group name**: Enter a unique name for the node group.
   - **Node IAM role**: Create a new role or select an existing role.
   - Click the "Next" button.

2. On the "Set compute and scaling configuration" page, enter the following information:
   - **AMI type**: Select the AMI type to use for the nodes.
   - **Instance type**: Select the EC2 instance type to use for the nodes.
   - **Disk size**: Specify the disk size for the nodes.
   - **Node count**: Specify the minimum, maximum, and desired number of nodes.
   - Click the "Next" button.

3. On the "Specify networking" page, enter the following information:
   - **Subnets**: Select the subnets to use for the node group.
   - **Remote access configuration**: Configure SSH access.
   - Click the "Next" button.

4. On the "Review and create" page, review the configuration and click the "Create" button.

## Creating a Cluster Using AWS CLI

You can create an EKS cluster using AWS CLI. This method is useful for script automation or CI/CD pipelines.

### Creating an EKS Auto Mode Cluster

#### 1. Create Cluster

```bash
# Create Auto Mode cluster
aws eks create-cluster \
  --name my-auto-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/AmazonEKSAutoClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
  --access-config authenticationMode=API_AND_CONFIG_MAP \
  --compute-config nodeRoleArn=arn:aws:iam::123456789012:role/AmazonEKSAutoNodeRole \
  --storage-config blockStorage='{enabled=true}' \
  --kubernetes-network-config ipFamily=ipv4 \
  --region us-west-2
```

#### 2. Check Cluster Status

```bash
# Check cluster status
aws eks describe-cluster --name my-auto-cluster --region us-west-2

# Wait until cluster is ACTIVE
aws eks wait cluster-active --name my-auto-cluster --region us-west-2
```

#### 3. Update kubeconfig

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
```

### Creating a Traditional Cluster

Here's how to create a cluster without using Auto Mode.

#### Basic Cluster Creation

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/eks-service-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,endpointConfigPrivateAccess=true,endpointConfigPublicAccess=true \
  --region us-west-2
```

#### Check Cluster Status

```bash
aws eks describe-cluster --name my-cluster --region us-west-2
```

Once the cluster is created, the status changes to `ACTIVE`. This process takes approximately 10-15 minutes.

#### Update kubeconfig

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

#### Create Managed Node Group

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --ami-type AL2_x86_64 \
  --node-role arn:aws:iam::123456789012:role/NodeInstanceRole \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 \
  --remote-access ec2SshKey=my-key \
  --region us-west-2
```

#### Check Node Group Status

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

## Creating a Cluster Using Terraform

Using Terraform to create an EKS cluster allows you to manage infrastructure as code.

### EKS Auto Mode Cluster Terraform Configuration

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# VPC and subnet data sources
data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  tags = {
    Type = "Private"
  }
}

# EKS Auto Mode cluster
resource "aws_eks_cluster" "auto_mode" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  # EKS Auto Mode configuration
  compute_config {
    enabled      = true
    node_role_arn = aws_iam_role.node.arn
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}

# Cluster IAM role
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

# Node IAM role
resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKSWorkerNodePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKS_CNI_Policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node.name
}

# Variable definitions
variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "my-auto-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-auto-mode"
  }
}

# Outputs
output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.auto_mode.endpoint
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_eks_cluster.auto_mode.vpc_config[0].cluster_security_group_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.auto_mode.arn
}
```

### Running Terraform

```bash
# Initialize Terraform
terraform init

# Review plan
terraform plan -var="vpc_id=vpc-12345678"

# Apply
terraform apply -var="vpc_id=vpc-12345678"

# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

### Traditional Terraform Configuration

Here's the Terraform configuration for not using Auto Mode:

```hcl
# Traditional EKS cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = data.aws_subnets.private.ids
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
  ]

  tags = var.tags
}

# Managed node group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = data.aws_subnets.private.ids

  capacity_type  = "ON_DEMAND"
  instance_types = ["m5.large"]

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]

  tags = var.tags
}
```

## Creating a Cluster Using AWS CDK

You can create an EKS cluster using AWS CDK (Cloud Development Kit).

### EKS Auto Mode Cluster Using TypeScript

```typescript
// lib/eks-auto-mode-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Import or create VPC
    const vpc = ec2.Vpc.fromLookup(this, 'VPC', {
      vpcId: 'vpc-12345678' // Existing VPC ID
    });

    // Or create new VPC
    // const vpc = new ec2.Vpc(this, 'EksVpc', {
    //   maxAzs: 3,
    //   natGateways: 1,
    // });

    // Create EKS Auto Mode cluster
    const cluster = new eks.Cluster(this, 'AutoModeCluster', {
      clusterName: 'my-auto-cluster',
      version: eks.KubernetesVersion.V1_31,
      vpc: vpc,
      vpcSubnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }
      ],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,

      // Auto Mode configuration
      defaultCapacity: 0, // Set default capacity to 0 for Auto Mode

      // Enable logging
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
    });

    // Custom resource to enable Auto Mode
    const autoModeConfig = new cdk.CustomResource(this, 'AutoModeConfig', {
      serviceToken: this.createAutoModeProvider().serviceToken,
      properties: {
        ClusterName: cluster.clusterName,
        NodeRoleArn: this.createNodeRole().roleArn,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'EKS cluster name',
    });

    new cdk.CfnOutput(this, 'ClusterEndpoint', {
      value: cluster.clusterEndpoint,
      description: 'EKS cluster endpoint',
    });
  }

  private createNodeRole(): iam.Role {
    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSWorkerNodePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKS_CNI_Policy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEC2ContainerRegistryReadOnly'),
      ],
    });

    return nodeRole;
  }

  private createAutoModeProvider(): cdk.Provider {
    // Lambda function for enabling Auto Mode
    const onEvent = new cdk.aws_lambda.Function(this, 'AutoModeHandler', {
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_9,
      handler: 'index.on_event',
      code: cdk.aws_lambda.Code.fromInline(`
import boto3
import json

def on_event(event, context):
    print(json.dumps(event))

    eks = boto3.client('eks')
    cluster_name = event['ResourceProperties']['ClusterName']
    node_role_arn = event['ResourceProperties']['NodeRoleArn']

    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        # Auto Mode enablement logic
        try:
            response = eks.update_cluster_config(
                name=cluster_name,
                computeConfig={
                    'enabled': True,
                    'nodeRoleArn': node_role_arn
                }
            )
            return {'PhysicalResourceId': cluster_name}
        except Exception as e:
            print(f"Error: {e}")
            raise e

    return {'PhysicalResourceId': cluster_name}
      `),
    });

    // Grant EKS permissions to Lambda function
    onEvent.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'eks:UpdateClusterConfig',
        'eks:DescribeCluster',
      ],
      resources: ['*'],
    }));

    return new cdk.Provider(this, 'AutoModeProvider', {
      onEventHandler: onEvent,
    });
  }
}
```

### CDK App Entry Point

```typescript
// bin/eks-auto-mode.ts
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
```

### CDK Deployment

```bash
# Install CDK
npm install -g aws-cdk

# Initialize project
cdk init app --language typescript

# Install dependencies
npm install

# CDK bootstrap (only once)
cdk bootstrap

# Deploy
cdk deploy

# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2
```

## Configuring Cluster Access

Proper permissions and configuration are required to access an EKS cluster.

### kubeconfig Configuration

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-cluster --region us-west-2

# Use specific profile
aws eks update-kubeconfig --name my-cluster --region us-west-2 --profile my-profile

# Use role ARN
aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EKSAccessRole
```

### RBAC Configuration

```yaml
# rbac.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/NodeInstanceRole
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

```bash
kubectl apply -f rbac.yaml
```

## Cluster Validation

Here's how to verify that the cluster was created correctly.

### Basic Validation

```bash
# Check cluster info
kubectl cluster-info

# Check node status
kubectl get nodes

# Check system pod status
kubectl get pods -n kube-system

# Check service accounts
kubectl get serviceaccounts -n kube-system
```

### Auto Mode Specific Validation

```bash
# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check Karpenter status (used in Auto Mode)
kubectl get pods -n karpenter
```

### Deploy Sample Application

```yaml
# sample-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
spec:
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

```bash
kubectl apply -f sample-app.yaml
kubectl get pods
kubectl get services
```

## Cluster Upgrade

Here's how to upgrade the Kubernetes version of an EKS cluster.

### Auto Mode Cluster Upgrade

Auto Mode clusters are automatically upgraded, but manual upgrade is also possible:

```bash
# Upgrade using eksctl
eksctl upgrade cluster --name my-auto-cluster --version 1.32

# Upgrade using AWS CLI
aws eks update-cluster-version --name my-auto-cluster --kubernetes-version 1.32
```

### Traditional Cluster Upgrade

```bash
# Upgrade cluster
eksctl upgrade cluster --name my-cluster --version 1.32

# Upgrade node group
eksctl upgrade nodegroup --cluster my-cluster --name my-nodegroup
```

## Cluster Deletion

Here's how to delete a cluster.

### Delete Using eksctl

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### Delete Using AWS CLI

```bash
# Delete node group (for non-Auto Mode)
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# Delete cluster
aws eks delete-cluster --name my-cluster
```

### Delete Using Terraform

```bash
terraform destroy
```

### Delete Using CDK

```bash
cdk destroy
```

## Conclusion

There are several methods for creating an EKS cluster, each with its own advantages and disadvantages:

- **EKS Auto Mode**: Provides production-ready clusters with minimal operational overhead
- **eksctl**: Simple and fast cluster creation
- **AWS Management Console**: Intuitive creation through GUI
- **AWS CLI**: Suitable for script automation
- **Terraform**: Manage infrastructure as code
- **AWS CDK**: Define infrastructure using programming languages

For production environments, using EKS Auto Mode or Terraform/CDK is recommended to build consistent and repeatable infrastructure.
