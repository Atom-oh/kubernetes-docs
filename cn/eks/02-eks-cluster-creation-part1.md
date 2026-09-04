# 第 1 部分：前提条件

创建 Amazon EKS 集群有多种方式。本章将学习如何使用各种工具和方法创建 EKS 集群。

## 目录

1. [前提条件](02-eks-cluster-creation-part1.md#prerequisites)
2. [使用 eksctl 创建集群](02-eks-cluster-creation-part1.md#creating-a-cluster-using-eksctl)
3. [使用 AWS Management Console 创建集群](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-management-console)
4. [使用 AWS CLI 创建集群](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-cli)
5. [使用 Terraform 创建集群](02-eks-cluster-creation-part1.md#creating-a-cluster-using-terraform)

## 前提条件

在创建 EKS 集群之前，需要满足以下前提条件：

### 1. AWS 账户

需要有效的 AWS 账户。如果您没有 AWS 账户，可以在 [AWS 网站](https://aws.amazon.com/) 注册。

### 2. IAM 权限

创建和管理 EKS 集群需要以下 IAM 权限：

* `eks:*`
* `ec2:*`
* `iam:*`
* `cloudformation:*`

如果您拥有管理员权限，则无需额外设置权限。否则，您需要将以下 IAM policy 附加到用户或 role：

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

创建和管理 EKS 集群必须安装以下工具：

#### AWS CLI

AWS CLI 是用于从命令行控制 AWS services 的统一工具。

**macOS**：

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux**：

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows**：

```
https://awscli.amazonaws.com/AWSCLIV2.msi
```

安装 AWS CLI 后，运行以下命令配置凭证：

```bash
aws configure
```

#### kubectl

kubectl 是用于与 Kubernetes 集群通信的命令行工具。

**macOS**：

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Linux**：

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
```

**Windows**：

```bash
curl -LO "https://dl.k8s.io/release/v1.26.0/bin/windows/amd64/kubectl.exe"
```

#### eksctl

eksctl 是用于创建和管理 EKS 集群的简单 CLI 工具。

**macOS**：

```bash
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl
```

或者：

```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Linux**：

```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

**Windows**：

```bash
# PowerShell
$version = (Invoke-WebRequest -Uri "https://api.github.com/repos/weaveworks/eksctl/releases/latest" | ConvertFrom-Json).tag_name
Invoke-WebRequest -Uri "https://github.com/weaveworks/eksctl/releases/download/$version/eksctl_Windows_amd64.zip" -OutFile eksctl.zip
Expand-Archive -Path eksctl.zip -DestinationPath $env:USERPROFILE\.eksctl\bin
$env:PATH += ";$env:USERPROFILE\.eksctl\bin"
```

### 4. VPC 和子网

EKS 集群需要 VPC 和子网。您可以使用现有 VPC 或创建新的 VPC。EKS 集群的 VPC 必须满足以下要求：

![EKS VPC 架构图：负载均衡器位于公有子网中，NAT Gateways 和 worker nodes 位于跨两个 Availability Zones 的私有子网中。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

* 至少 2 个子网必须位于不同的 availability zones。
* 子网必须能够访问互联网（通过 NAT gateway 或 internet gateway）。
* 子网必须具有足够的 IP addresses。
* 子网必须具有适当的 tags。

#### EKS 集群的 VPC Tags

必须应用以下 tags，才能使 EKS 集群正确使用 VPC 和子网：

**VPC Tags**：

* `kubernetes.io/cluster/<cluster-name>`: `shared` 或 `owned`

**公有子网 Tags**：

* `kubernetes.io/cluster/<cluster-name>`: `shared` 或 `owned`
* `kubernetes.io/role/elb`: `1`

**私有子网 Tags**：

* `kubernetes.io/cluster/<cluster-name>`: `shared` 或 `owned`
* `kubernetes.io/role/internal-elb`: `1`

## 测验

为了测试您在本章中学到的内容，请尝试 [EKS 集群创建 - 第 1 部分测验](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)。
