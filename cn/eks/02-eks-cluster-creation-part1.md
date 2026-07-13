# 第 1 部分：先决条件

创建 Amazon EKS cluster 有多种方式。在本章中，我们将学习如何使用各种工具和方法创建 EKS cluster。

## 目录

1. [先决条件](02-eks-cluster-creation-part1.md#prerequisites)
2. [使用 eksctl 创建 Cluster](02-eks-cluster-creation-part1.md#creating-a-cluster-using-eksctl)
3. [使用 AWS Management Console 创建 Cluster](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-management-console)
4. [使用 AWS CLI 创建 Cluster](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-cli)
5. [使用 Terraform 创建 Cluster](02-eks-cluster-creation-part1.md#creating-a-cluster-using-terraform)

## 先决条件

在创建 EKS cluster 之前，需要满足以下先决条件：

### 1. AWS 账户

需要一个有效的 AWS 账户。如果你没有 AWS 账户，可以在 [AWS website](https://aws.amazon.com/) 注册。

### 2. IAM 权限

创建和管理 EKS cluster 需要以下 IAM 权限：

* `eks:*`
* `ec2:*`
* `iam:*`
* `cloudformation:*`

如果你拥有 administrator 权限，则不需要额外的权限设置。否则，需要将以下 IAM policy 附加到 user 或 role：

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

AWS CLI 是一个用于从命令行控制 AWS services 的统一工具。

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

EKS cluster 需要 VPC 和 Subnet。你可以使用现有 VPC，也可以创建新的 VPC。用于 EKS cluster 的 VPC 必须满足以下要求：

![EKS VPC Architecture](../.gitbook/assets/eks_vpc_architecture.png)

* 至少 2 个 Subnet 必须位于不同的 Availability Zone（可用区）。
* Subnet 必须能够访问互联网（通过 NAT gateway 或 internet gateway）。
* Subnet 必须有足够的 IP addresses。
* Subnet 必须具有适当的 tags。

#### EKS Cluster 的 VPC Tags

必须应用以下 tags，才能使 EKS cluster 正确使用 VPC 和 Subnet：

**VPC Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Public Subnet Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/internal-elb`: `1`

## 测验

为了测试你在本章学到的内容，请尝试 [EKS Cluster Creation - Part 1 Quiz](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)。
