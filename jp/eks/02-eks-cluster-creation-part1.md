# Part 1: Prerequisites

Amazon EKS cluster を作成する方法はいくつかあります。この章では、さまざまな tools と方法を使用して EKS cluster を作成する方法を学びます。

## Table of Contents

1. [Prerequisites](02-eks-cluster-creation-part1.md#prerequisites)
2. [Creating a Cluster Using eksctl](02-eks-cluster-creation-part1.md#creating-a-cluster-using-eksctl)
3. [Creating a Cluster Using AWS Management Console](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-management-console)
4. [Creating a Cluster Using AWS CLI](02-eks-cluster-creation-part1.md#creating-a-cluster-using-aws-cli)
5. [Creating a Cluster Using Terraform](02-eks-cluster-creation-part1.md#creating-a-cluster-using-terraform)

## Prerequisites

EKS cluster を作成する前に、次の prerequisites が必要です。

### 1. AWS Account

有効な AWS account が必要です。AWS account を持っていない場合は、[AWS website](https://aws.amazon.com/) でサインアップできます。

### 2. IAM Permissions

EKS cluster を作成および管理するには、次の IAM permissions が必要です。

* `eks:*`
* `ec2:*`
* `iam:*`
* `cloudformation:*`

administrator permissions がある場合、追加の permission settings は不要です。それ以外の場合は、次の IAM policy を user または role にアタッチする必要があります。

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

EKS cluster を作成および管理するには、次の tools をインストールする必要があります。

#### AWS CLI

AWS CLI は、command line から AWS services を制御するための統合 tool です。

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

AWS CLI をインストールした後、次の command を実行して credentials を設定します。

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

EKS cluster には VPC と subnets が必要です。既存の VPC を使用することも、新しいものを作成することもできます。EKS cluster 用の VPC は、次の要件を満たす必要があります。

![EKS VPC Architecture](../.gitbook/assets/eks_vpc_architecture.png)

* 少なくとも 2 つの subnets が異なる availability zones に存在する必要があります。
* Subnets は internet access（NAT gateway または internet gateway 経由）を持つ必要があります。
* Subnets には十分な IP addresses が必要です。
* Subnets には適切な tags が必要です。

#### VPC Tags for EKS Cluster

EKS cluster が VPC と subnets を正しく使用できるようにするには、次の tags を適用する必要があります。

**VPC Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`

**Public Subnet Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/elb`: `1`

**Private Subnet Tags**:

* `kubernetes.io/cluster/<cluster-name>`: `shared` or `owned`
* `kubernetes.io/role/internal-elb`: `1`

## Quiz

この章で学んだ内容を確認するには、[EKS Cluster Creation - Part 1 Quiz](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md) に挑戦してください。
