# EKS Cluster 创建

创建 Amazon EKS cluster 有多种方式。在本章中，我们将详细学习如何使用各种工具和方法创建 EKS cluster。

## 目录

1. [先决条件](#prerequisites)
2. [使用 eksctl 创建 Cluster](#creating-a-cluster-using-eksctl)
3. [使用 AWS Management Console 创建 Cluster](#creating-a-cluster-using-aws-management-console)
4. [使用 AWS CLI 创建 Cluster](#creating-a-cluster-using-aws-cli)
5. [使用 Terraform 创建 Cluster](#creating-a-cluster-using-terraform)
6. [使用 AWS CDK 创建 Cluster](#creating-a-cluster-using-aws-cdk)
7. [配置 Cluster 访问](#configuring-cluster-access)
8. [Cluster 验证](#cluster-validation)
9. [Cluster 升级](#cluster-upgrade)
10. [Cluster 删除](#cluster-deletion)

## 先决条件

在创建 EKS cluster 之前，需要满足以下先决条件：

### 1. AWS 账户

需要一个有效的 AWS 账户。如果你没有 AWS 账户，可以在 [AWS website](https://aws.amazon.com/) 注册。

### 2. IAM 权限

创建和管理 EKS cluster 需要以下 IAM 权限：

- `eks:*`
- `ec2:*`
- `iam:*`
- `cloudformation:*`

如果你拥有 administrator 权限，则不需要额外的权限设置。否则，你需要将以下 IAM policy 附加到 user 或 role：

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

### 3. 工具安装

要创建和管理 EKS cluster，必须安装以下工具：

#### AWS CLI

AWS CLI 是用于从命令行控制 AWS services 的统一工具。

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

安装 AWS CLI 后，运行以下命令配置凭证：
```bash
aws configure
```

#### kubectl

kubectl 是用于与 Kubernetes clusters 通信的命令行工具。

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

eksctl 是用于创建和管理 EKS clusters 的简单 CLI 工具。

**macOS**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

或者：
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

### 4. VPC 和 Subnet

EKS cluster 需要 VPC 和 subnets。你可以使用现有 VPC，也可以创建新的 VPC。用于 EKS cluster 的 VPC 必须满足以下要求：

- 至少 2 个 subnets 必须位于不同的 availability zones。
- Subnets 必须能够访问互联网（通过 NAT gateway 或 internet gateway）。
- Subnets 必须有足够的 IP addresses。
- Subnets 必须具有适当的 tags。

#### EKS Cluster 的 VPC Tags

必须应用以下 tags，才能使 EKS cluster 正确使用 VPC 和 subnets：

**VPC Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Public Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/internal-elb`: `1`

## 使用 eksctl 创建 Cluster

eksctl 是创建和管理 EKS clusters 的最简单方式。eksctl 使用 CloudFormation 创建 EKS clusters 及相关资源。

### 基本 Cluster 创建

要创建最基本形式的 EKS cluster，请运行以下命令：

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

此命令会使用以下默认设置创建 cluster：
- 2 个 m5.large nodes
- 新的 VPC 和 subnets
- 默认 Amazon Linux 2 AMI
- 最新 Kubernetes 版本

### 使用配置文件创建 Cluster

对于更复杂的配置，你可以使用 YAML 文件定义 cluster：

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

要使用此配置文件创建 cluster，请运行以下命令：

```bash
eksctl create cluster -f cluster.yaml
```

### 创建 Managed Node Groups

要向现有 cluster 添加 managed node group，请运行以下命令：

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

或者你可以使用配置文件：

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

### 创建 EKS Auto Mode Cluster

EKS Auto Mode 是 2024 年发布的一项新功能，可自动化 Kubernetes cluster infrastructure，从而显著降低运营开销。Auto Mode 会自动处理包括 compute、networking 和 storage 在内的 infrastructure management。

#### EKS Auto Mode 的主要特性

- **Automated Node Management**：根据 workload 需求自动添加/移除 nodes
- **Enhanced Security**：不可变 AMI、SELinux enforcing mode、只读 root filesystem
- **Automatic Upgrades**：定期 security patches 和 updates，node 最长生命周期为 21 天
- **Integrated Components**：默认提供 Pod networking、DNS、storage、GPU support
- **Cost Optimization**：自动终止未使用的 instances 并整合 workloads

#### 基本 Auto Mode Cluster 创建

```bash
eksctl create cluster --name my-auto-cluster --enable-auto-mode --region us-west-2
```

#### 使用配置文件创建 Auto Mode Cluster

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

创建 cluster：
```bash
eksctl create cluster -f auto-cluster.yaml
```

#### Auto Mode 与传统方式对比

| Feature | Traditional EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| Node Management | 手动 managed node groups | 自动 node management |
| Scaling | 需要设置 Cluster Autoscaler | 内置 auto scaling |
| Upgrades | 手动 upgrades | 自动 upgrades（21 天周期） |
| Security | 由用户配置 | 默认增强 security |
| Networking | CNI plugin 设置 | 自动 networking 配置 |
| Storage | 需要安装 CSI driver | 自动提供 EBS CSI |
| GPU Support | 手动安装 driver | 自动 GPU support |

#### Auto Mode Cluster 验证

Cluster 创建完成后，你可以使用以下命令检查其状态：

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

#### 创建自定义 Node Pools

在 Auto Mode 中，除了默认 node pools 外，你还可以创建自定义 node pools：

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

#### Auto Mode 限制

- 无法通过 SSH 或 SSM 直接访问 node
- Node 最长生命周期为 21 天（自动替换）
- 无法修改默认 node pools 和 node classes
- 可能存在某些 instance type 限制

#### Auto Mode 监控

Auto Mode clusters 已与 CloudWatch 集成，并会自动收集 metrics：

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

### 创建 Fargate Profiles

要创建 Fargate profile，请运行以下命令：

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

或者你可以使用配置文件：

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

### 更新 Cluster

你可以使用 eksctl 更新现有 cluster：

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### 删除 Cluster

你可以使用 eksctl 删除 cluster：

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## 使用 AWS Management Console 创建 Cluster

使用 AWS Management Console 创建 EKS cluster 的步骤如下：

1. 登录到 [AWS Management Console](https://console.aws.amazon.com/)。
2. 搜索 "EKS"，或从 services 列表中选择 "Elastic Kubernetes Service"。
3. 在 "Clusters" 页面上，点击 "Create cluster" 按钮。

### 创建 EKS Auto Mode Cluster（快速配置）

使用 EKS Auto Mode，你可以用最少的配置创建 production-ready cluster。

#### 1. 选择 Quick Configuration

4. 确保已选择 "Quick configuration" 选项。
5. 输入以下信息：
   - **Cluster name**: 输入 cluster 的唯一名称。
   - **Kubernetes version**: 选择要使用的 Kubernetes version（推荐最新版本）。

#### 2. 配置 IAM Roles

6. **Cluster IAM role** 选择：
   - 对于你的第一个 Auto Mode cluster，请使用 "Create recommended role" 选项。
   - 如果你已有现有 role，可以复用它。
   - 推荐 role 名称：`AmazonEKSAutoClusterRole`

7. **Node IAM role** 选择：
   - 对于你的第一个 Auto Mode cluster，请使用 "Create recommended role" 选项。
   - 推荐 role 名称：`AmazonEKSAutoNodeRole`

#### 3. 配置 Networking

8. **Select VPC**:
   - 创建新 VPC：选择 "Create VPC" 选项，为 EKS 创建新的 VPC。
   - 使用现有 VPC：选择之前创建的 EKS VPC。

9. **Subnet configuration**（可选）：
   - EKS Auto Mode 会自动选择 VPC 中的 private subnets。
   - 你可以根据需要添加或移除 subnets。

#### 4. 查看配置并创建

10. 选择 **View quick configuration defaults** 以查看所有配置值。
11. 点击 **Create cluster**。（Cluster 创建大约需要 15 分钟）

### 使用自定义配置创建 Cluster

如果你需要更精细的控制，可以使用自定义配置。

### Cluster 配置

4. 在 "Configure cluster" 页面上，输入以下信息：
   - **Cluster name**: 输入 cluster 的唯一名称。
   - **Kubernetes version**: 选择要使用的 Kubernetes version。
   - **Cluster service role**: 创建新的 role 或选择现有 role。
   - **EKS Auto Mode**: 勾选 checkbox 以启用 Auto Mode。
   - **Tags**: 根据需要添加 tags。
   - 点击 "Next" 按钮。

### 指定 Networking

5. 在 "Specify networking" 页面上，输入以下信息：
   - **VPC**: 创建新的 VPC 或选择现有 VPC。
   - **Subnets**: 选择要用于 cluster 的 subnets。至少 2 个 subnets 必须位于不同的 availability zones。
   - **Security groups**: 选择要用于 cluster 的 security groups。
   - **Cluster endpoint access**: 配置对 cluster API server endpoint 的访问。
     - **Public**: 可以从互联网访问 API server。
     - **Private**: 只能从 VPC 内部访问 API server。
     - **Public and Private**: 可以同时从互联网和 VPC 内部访问 API server。
   - 点击 "Next" 按钮。

### 配置 Logging

6. 在 "Configure logging" 页面上，输入以下信息：
   - **Control plane logging**: 选择要启用的 log types。
     - API server logs
     - Audit logs
     - Authenticator logs
     - Controller manager logs
     - Scheduler logs
   - 点击 "Next" 按钮。

### 选择 Add-ons

7. 在 "Select add-ons" 页面上，输入以下信息：
   - **Amazon VPC CNI**: 用于 pod networking 的 CNI plugin。
   - **CoreDNS**: cluster 内的 DNS service。
   - **kube-proxy**: 提供 network proxy 和 load balancing。
   - **Amazon EBS CSI Driver**: 自动包含在 EKS Auto Mode 中。
   - 点击 "Next" 按钮。

### Review and Create

8. 在 "Review and create" 页面上，检查配置并点击 "Create" 按钮。

### 为非 Auto Mode Clusters 添加 Node Groups

如果你未使用 EKS Auto Mode，则需要在 cluster 创建后手动添加 node groups。

### 添加 Node Group

1. 在 "Node group configuration" 页面上，输入以下信息：
   - **Node group name**: 输入 node group 的唯一名称。
   - **Node IAM role**: 创建新的 role 或选择现有 role。
   - 点击 "Next" 按钮。

2. 在 "Set compute and scaling configuration" 页面上，输入以下信息：
   - **AMI type**: 选择要用于 nodes 的 AMI type。
   - **Instance type**: 选择要用于 nodes 的 EC2 instance type。
   - **Disk size**: 指定 nodes 的 disk size。
   - **Node count**: 指定 nodes 的最小、最大和期望数量。
   - 点击 "Next" 按钮。

3. 在 "Specify networking" 页面上，输入以下信息：
   - **Subnets**: 选择要用于 node group 的 subnets。
   - **Remote access configuration**: 配置 SSH access。
   - 点击 "Next" 按钮。

4. 在 "Review and create" 页面上，检查配置并点击 "Create" 按钮。

## 使用 AWS CLI 创建 Cluster

你可以使用 AWS CLI 创建 EKS cluster。此方法适用于 script automation 或 CI/CD pipelines。

### 创建 EKS Auto Mode Cluster

#### 1. 创建 Cluster

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

#### 2. 检查 Cluster 状态

```bash
# Check cluster status
aws eks describe-cluster --name my-auto-cluster --region us-west-2

# Wait until cluster is ACTIVE
aws eks wait cluster-active --name my-auto-cluster --region us-west-2
```

#### 3. 更新 kubeconfig

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-auto-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
```

### 创建传统 Cluster

以下是不使用 Auto Mode 创建 cluster 的方法。

#### 基本 Cluster 创建

```bash
aws eks create-cluster \
  --name my-cluster \
  --version 1.31 \
  --role-arn arn:aws:iam::123456789012:role/eks-service-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,endpointConfigPrivateAccess=true,endpointConfigPublicAccess=true \
  --region us-west-2
```

#### 检查 Cluster 状态

```bash
aws eks describe-cluster --name my-cluster --region us-west-2
```

Cluster 创建完成后，状态会变为 `ACTIVE`。此过程大约需要 10-15 分钟。

#### 更新 kubeconfig

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

#### 创建 Managed Node Group

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

#### 检查 Node Group 状态

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

## 使用 Terraform 创建 Cluster

使用 Terraform 创建 EKS cluster 允许你以 code 形式管理 infrastructure。

### EKS Auto Mode Cluster Terraform 配置

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

### 运行 Terraform

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

### 传统 Terraform 配置

以下是不使用 Auto Mode 的 Terraform 配置：

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

## 使用 AWS CDK 创建 Cluster

你可以使用 AWS CDK (Cloud Development Kit) 创建 EKS cluster。

### 使用 TypeScript 创建 EKS Auto Mode Cluster

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

## 配置 Cluster 访问

访问 EKS cluster 需要适当的权限和配置。

### kubeconfig 配置

```bash
# Update kubeconfig
aws eks update-kubeconfig --name my-cluster --region us-west-2

# Use specific profile
aws eks update-kubeconfig --name my-cluster --region us-west-2 --profile my-profile

# Use role ARN
aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EKSAccessRole
```

### RBAC 配置

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

## Cluster 验证

以下是验证 cluster 是否已正确创建的方法。

### 基本验证

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

### Auto Mode 专项验证

```bash
# Check Auto Mode node pools
kubectl get nodepools

# Check Auto Mode node classes
kubectl get nodeclasses

# Check Karpenter status (used in Auto Mode)
kubectl get pods -n karpenter
```

### 部署示例 Application

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

## Cluster 升级

以下是升级 EKS cluster 的 Kubernetes version 的方法。

### Auto Mode Cluster 升级

Auto Mode clusters 会自动升级，但也可以手动升级：

```bash
# Upgrade using eksctl
eksctl upgrade cluster --name my-auto-cluster --version 1.32

# Upgrade using AWS CLI
aws eks update-cluster-version --name my-auto-cluster --kubernetes-version 1.32
```

### 传统 Cluster 升级

```bash
# Upgrade cluster
eksctl upgrade cluster --name my-cluster --version 1.32

# Upgrade node group
eksctl upgrade nodegroup --cluster my-cluster --name my-nodegroup
```

## Cluster 删除

以下是删除 cluster 的方法。

### 使用 eksctl 删除

```bash
eksctl delete cluster --name my-cluster --region us-west-2
```

### 使用 AWS CLI 删除

```bash
# Delete node group (for non-Auto Mode)
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name my-nodegroup

# Delete cluster
aws eks delete-cluster --name my-cluster
```

### 使用 Terraform 删除

```bash
terraform destroy
```

### 使用 CDK 删除

```bash
cdk destroy
```

## 结论

创建 EKS cluster 有多种方法，每种方法都有各自的优点和缺点：

- **EKS Auto Mode**：以最少的运营开销提供 production-ready clusters
- **eksctl**：简单且快速的 cluster 创建
- **AWS Management Console**：通过 GUI 进行直观创建
- **AWS CLI**：适合 script automation
- **Terraform**：以 code 形式管理 infrastructure
- **AWS CDK**：使用 programming languages 定义 infrastructure

对于 production environments，建议使用 EKS Auto Mode 或 Terraform/CDK 来构建一致且可重复的 infrastructure。
