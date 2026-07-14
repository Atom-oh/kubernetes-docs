# EKS Cluster Creation

Amazon EKS cluster（クラスター）を作成する方法はいくつかあります。この章では、さまざまなツールと方法を使用して EKS cluster を作成する方法を詳しく学びます。

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

EKS cluster を作成する前に、次の前提条件が必要です。

### 1. AWS Account

有効な AWS account が必要です。AWS account を持っていない場合は、[AWS website](https://aws.amazon.com/) でサインアップできます。

### 2. IAM Permissions

EKS cluster を作成および管理するには、次の IAM permissions が必要です。

- `eks:*`
- `ec2:*`
- `iam:*`
- `cloudformation:*`

administrator permissions がある場合、追加の permission 設定は不要です。それ以外の場合は、次の IAM policy を user または role にアタッチする必要があります。

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

EKS cluster を作成および管理するには、次のツールをインストールしておく必要があります。

#### AWS CLI

AWS CLI は、command line から AWS services を制御するための統合ツールです。

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

AWS CLI をインストールしたら、次のコマンドを実行して credentials を設定します。
```bash
aws configure
```

#### kubectl

kubectl は、Kubernetes clusters と通信するための command-line tool です。

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

eksctl は、EKS clusters を作成および管理するためのシンプルな CLI tool です。

**macOS**:
```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

または:
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

EKS cluster には VPC と subnets が必要です。既存の VPC を使用することも、新しい VPC を作成することもできます。EKS cluster 用の VPC は、次の要件を満たす必要があります。

- 少なくとも 2 つの subnets が異なる availability zones に存在する必要があります。
- Subnets には internet access（NAT gateway または internet gateway 経由）が必要です。
- Subnets には十分な IP addresses が必要です。
- Subnets には適切な tags が必要です。

#### VPC Tags for EKS Cluster

EKS cluster が VPC と subnets を正しく使用できるようにするには、次の tags を適用する必要があります。

**VPC Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Public Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:
- `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
- `kubernetes.io/role/internal-elb`: `1`

## Creating a Cluster Using eksctl

eksctl は、EKS clusters を作成および管理する最も簡単な方法です。eksctl は CloudFormation を使用して、EKS clusters と関連 resources を作成します。

### Basic Cluster Creation

最も基本的な形式の EKS cluster を作成するには、次のコマンドを実行します。

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

このコマンドは、次のデフォルト設定で cluster を作成します。
- 2 m5.large nodes
- 新しい VPC と subnets
- デフォルトの Amazon Linux 2 AMI
- 最新の Kubernetes version

### Creating a Cluster Using a Configuration File

より複雑な configurations では、YAML file を使用して cluster を定義できます。

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

この configuration file を使用して cluster を作成するには、次のコマンドを実行します。

```bash
eksctl create cluster -f cluster.yaml
```

### Creating Managed Node Groups

既存の cluster に managed node group を追加するには、次のコマンドを実行します。

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

または、configuration file を使用できます。

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

EKS Auto Mode は 2024 年にリリースされた新機能で、Kubernetes cluster infrastructure を自動化し、operational overhead を大幅に削減します。Auto Mode は、compute、networking、storage を含む infrastructure management を自動的に処理します。

#### Key Features of EKS Auto Mode

- **Automated Node Management**: workload requirements に基づいて nodes を自動的に追加/削除します
- **Enhanced Security**: Immutable AMI、SELinux enforcing mode、read-only root filesystem
- **Automatic Upgrades**: 21 日間の最大 node lifetime による定期的な security patches と updates
- **Integrated Components**: Pod networking、DNS、storage、GPU support がデフォルトで提供されます
- **Cost Optimization**: 未使用 instances の自動終了と workload consolidation

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

Cluster を作成します。
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

Cluster が作成されたら、次のコマンドで状態を確認できます。

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

Auto Mode では、デフォルトの node pools に加えて custom node pools を作成できます。

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

- SSH または SSM 経由での直接 node access はありません
- 最大 node lifetime は 21 日間です（自動置換）
- デフォルトの node pools と node classes は変更できません
- 特定の instance type restrictions が発生する可能性があります

#### Auto Mode Monitoring

Auto Mode clusters は CloudWatch と統合されており、metrics を自動的に収集します。

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

Fargate profile を作成するには、次のコマンドを実行します。

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

または、configuration file を使用できます。

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

eksctl を使用して既存の cluster を更新できます。

```bash
# Upgrade cluster version
eksctl upgrade cluster --name=my-cluster --version=1.27

# Upgrade node group
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

### Deleting a Cluster

eksctl を使用して cluster を削除できます。

```bash
eksctl delete cluster --name=my-cluster --region=us-west-2
```

## Creating a Cluster Using AWS Management Console

AWS Management Console を使用して EKS cluster を作成する手順は次のとおりです。

1. [AWS Management Console](https://console.aws.amazon.com/) にログインします。
2. "EKS" を検索するか、services list から "Elastic Kubernetes Service" を選択します。
3. "Clusters" ページで、"Create cluster" ボタンをクリックします。

### Creating an EKS Auto Mode Cluster (Quick Configuration)

EKS Auto Mode を使用すると、最小限の configuration で production-ready cluster を作成できます。

#### 1. Select Quick Configuration

4. "Quick configuration" オプションが選択されていることを確認します。
5. 次の情報を入力します。
   - **Cluster name**: Cluster の一意の名前を入力します。
   - **Kubernetes version**: 使用する Kubernetes version を選択します（最新 version を推奨）。

#### 2. Configure IAM Roles

6. **Cluster IAM role** の選択:
   - 初めての Auto Mode cluster では、"Create recommended role" オプションを使用します。
   - 既存の role がある場合は、それを再利用できます。
   - 推奨 role name: `AmazonEKSAutoClusterRole`

7. **Node IAM role** の選択:
   - 初めての Auto Mode cluster では、"Create recommended role" オプションを使用します。
   - 推奨 role name: `AmazonEKSAutoNodeRole`

#### 3. Configure Networking

8. **Select VPC**:
   - 新しい VPC を作成: EKS 用に新しい VPC を作成するには、"Create VPC" オプションを選択します。
   - 既存の VPC を使用: 以前に作成した EKS VPC を選択します。

9. **Subnet configuration**（任意）:
   - EKS Auto Mode は、VPC 内の private subnets を自動的に選択します。
   - 必要に応じて subnets を追加または削除できます。

#### 4. Review Configuration and Create

10. **View quick configuration defaults** を選択して、すべての configuration values を確認します。
11. **Create cluster** をクリックします。（Cluster の作成には約 15 分かかります）

### Creating a Cluster with Custom Configuration

より細かな制御が必要な場合は、custom configuration を使用できます。

### Cluster Configuration

4. "Configure cluster" ページで、次の情報を入力します。
   - **Cluster name**: Cluster の一意の名前を入力します。
   - **Kubernetes version**: 使用する Kubernetes version を選択します。
   - **Cluster service role**: 新しい role を作成するか、既存の role を選択します。
   - **EKS Auto Mode**: Auto Mode を有効にするには checkbox をオンにします。
   - **Tags**: 必要に応じて tags を追加します。
   - "Next" ボタンをクリックします。

### Specify Networking

5. "Specify networking" ページで、次の情報を入力します。
   - **VPC**: 新しい VPC を作成するか、既存の VPC を選択します。
   - **Subnets**: Cluster で使用する subnets を選択します。少なくとも 2 つの subnets が異なる availability zones に存在する必要があります。
   - **Security groups**: Cluster で使用する security groups を選択します。
   - **Cluster endpoint access**: Cluster API server endpoint への access を設定します。
     - **Public**: API server は internet から access できます。
     - **Private**: API server は VPC 内からのみ access できます。
     - **Public and Private**: API server は internet と VPC 内の両方から access できます。
   - "Next" ボタンをクリックします。

### Configure Logging

6. "Configure logging" ページで、次の情報を入力します。
   - **Control plane logging**: 有効にする log types を選択します。
     - API server logs
     - Audit logs
     - Authenticator logs
     - Controller manager logs
     - Scheduler logs
   - "Next" ボタンをクリックします。

### Select Add-ons

7. "Select add-ons" ページで、次の情報を入力します。
   - **Amazon VPC CNI**: pod networking 用の CNI plugin です。
   - **CoreDNS**: Cluster 内の DNS service です。
   - **kube-proxy**: network proxy と load balancing を提供します。
   - **Amazon EBS CSI Driver**: EKS Auto Mode に自動的に含まれます。
   - "Next" ボタンをクリックします。

### Review and Create

8. "Review and create" ページで、configuration を確認し、"Create" ボタンをクリックします。

### Adding Node Groups for Non-Auto Mode Clusters

EKS Auto Mode を使用していない場合は、cluster 作成後に node groups を手動で追加する必要があります。

### Add Node Group

1. "Node group configuration" ページで、次の情報を入力します。
   - **Node group name**: Node group の一意の名前を入力します。
   - **Node IAM role**: 新しい role を作成するか、既存の role を選択します。
   - "Next" ボタンをクリックします。

2. "Set compute and scaling configuration" ページで、次の情報を入力します。
   - **AMI type**: Nodes に使用する AMI type を選択します。
   - **Instance type**: Nodes に使用する EC2 instance type を選択します。
   - **Disk size**: Nodes の disk size を指定します。
   - **Node count**: Nodes の最小数、最大数、希望数を指定します。
   - "Next" ボタンをクリックします。

3. "Specify networking" ページで、次の情報を入力します。
   - **Subnets**: Node group で使用する subnets を選択します。
   - **Remote access configuration**: SSH access を設定します。
   - "Next" ボタンをクリックします。

4. "Review and create" ページで、configuration を確認し、"Create" ボタンをクリックします。

## Creating a Cluster Using AWS CLI

AWS CLI を使用して EKS cluster を作成できます。この方法は、script automation や CI/CD pipelines に便利です。

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

Auto Mode を使用せずに cluster を作成する方法は次のとおりです。

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

Cluster が作成されると、status は `ACTIVE` に変わります。この処理には約 10〜15 分かかります。

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

Terraform を使用して EKS cluster を作成すると、infrastructure as code として管理できます。

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

Auto Mode を使用しない場合の Terraform configuration は次のとおりです。

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

AWS CDK（Cloud Development Kit）を使用して EKS cluster を作成できます。

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

EKS cluster に access するには、適切な permissions と configuration が必要です。

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

Cluster が正しく作成されたことを確認する方法は次のとおりです。

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

EKS cluster の Kubernetes version を upgrade する方法は次のとおりです。

### Auto Mode Cluster Upgrade

Auto Mode clusters は自動的に upgrade されますが、手動 upgrade も可能です。

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

Cluster を削除する方法は次のとおりです。

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

EKS cluster を作成する方法はいくつかあり、それぞれに利点と欠点があります。

- **EKS Auto Mode**: 最小限の operational overhead で production-ready clusters を提供します
- **eksctl**: シンプルで高速な cluster 作成
- **AWS Management Console**: GUI による直感的な作成
- **AWS CLI**: script automation に適しています
- **Terraform**: infrastructure as code として管理します
- **AWS CDK**: programming languages を使用して infrastructure を定義します

Production environments では、一貫性があり再現可能な infrastructure を構築するために、EKS Auto Mode または Terraform/CDK の使用が推奨されます。
