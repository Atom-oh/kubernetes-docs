# パート 3: AWS Management Console と CLI による Cluster の作成

## AWS Management Console を使用した Cluster の作成

AWS Management Console を使用して EKS Cluster を作成する手順は次のとおりです。

![AWS Management Console 経由の EKS Cluster 作成ワークフロー](../.gitbook/assets/eks_console_cluster_creation_workflow.png)

1. [AWS Management Console](https://console.aws.amazon.com/) にログインします。
2. 「EKS」を検索するか、サービス一覧から「Elastic Kubernetes Service」を選択します。
3. 「Clusters」ページで「Create cluster」ボタンをクリックします。

### Cluster 設定

4. 「Configure cluster」ページで、次の情報を入力します。
   * **Cluster name**: Cluster の一意の名前を入力します。
   * **Kubernetes version**: 使用する Kubernetes version を選択します。
   * **Cluster service role**: 新しい role を作成するか、既存の role を選択します。
   * **Tags**: 必要に応じて tag を追加します。
   * 「Next」ボタンをクリックします。

### ネットワーキングの指定

5. 「Specify networking」ページで、次の情報を入力します。
   * **VPC**: 新しい VPC を作成するか、既存の VPC を選択します。
   * **Subnets**: Cluster に使用する subnets を選択します。少なくとも 2 つの subnets は異なる availability zones に存在する必要があります。
   * **Security groups**: Cluster に使用する security groups を選択します。
   * **Cluster endpoint access**: Cluster API server endpoint へのアクセスを設定します。
     * **Public**: API server にはインターネットからアクセスできます。
     * **Private**: API server には VPC 内からのみアクセスできます。
     * **Public and Private**: API server にはインターネットと VPC 内の両方からアクセスできます。
   * 「Next」ボタンをクリックします。

### ログ記録の設定

6. 「Configure logging」ページで、次の情報を入力します。
   * **Control plane logging**: 有効にする log types を選択します。
     * API server logs
     * Audit logs
     * Authenticator logs
     * Controller manager logs
     * Scheduler logs
   * 「Next」ボタンをクリックします。

### Add-ons の選択

7. 「Select add-ons」ページで、次の情報を入力します。
   * **Amazon VPC CNI**: pod networking 用の CNI plugin です。
   * **CoreDNS**: Cluster 内の DNS service です。
   * **kube-proxy**: network proxy と load balancing を提供します。
   * 「Next」ボタンをクリックします。

### レビューして作成

8. 「Review and create」ページで、設定を確認し、「Create」ボタンをクリックします。

Cluster の作成が完了したら、「Add node group」ボタンをクリックして Node Group を追加できます。

### Node Group の追加

1. 「Node group configuration」ページで、次の情報を入力します。
   * **Node group name**: Node Group の一意の名前を入力します。
   * **Node IAM role**: 新しい role を作成するか、既存の role を選択します。
   * 「Next」ボタンをクリックします。
2. 「Set compute and scaling configuration」ページで、次の情報を入力します。
   * **AMI type**: nodes に使用する AMI type を選択します。
   * **Instance type**: nodes に使用する EC2 instance type を選択します。
   * **Disk size**: nodes の disk size を指定します。
   * **Node count**: nodes の最小数、最大数、希望数を指定します。
   * 「Next」ボタンをクリックします。
3. 「Specify networking」ページで、次の情報を入力します。
   * **Subnets**: Node Group に使用する subnets を選択します。
   * **Remote access configuration**: SSH access を設定します。
   * 「Next」ボタンをクリックします。
4. 「Review and create」ページで、設定を確認し、「Create」ボタンをクリックします。

## AWS CLI を使用した Cluster の作成

AWS CLI を使用して EKS Cluster を作成するプロセスは、複数の手順で構成されます。この方法は、より細かい制御が必要な場合に役立ちます。

![AWS CLI 経由の EKS Cluster 作成ワークフロー](../.gitbook/assets/eks_cli_cluster_creation_workflow.png)

### 1. Cluster IAM Role の作成

EKS Cluster には、Kubernetes control plane が AWS resources を管理できるようにする IAM role が必要です。

```bash
# Create role
aws iam create-role \
  --role-name EKSClusterRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "eks.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach required policy
aws iam attach-role-policy \
  --role-name EKSClusterRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

### 2. VPC と Subnets の作成

EKS Cluster には VPC と subnets が必要です。既存の VPC を使用することも、新しい VPC を作成することもできます。

```bash
# Create VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=EKS-VPC}]' \
  --query Vpc.VpcId \
  --output text

# Create subnets
aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-west-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Subnet-1}]' \
  --query Subnet.SubnetId \
  --output text

aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-west-2b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=EKS-Subnet-2}]' \
  --query Subnet.SubnetId \
  --output text
```

### 3. Cluster Security Group の作成

EKS Cluster には security group が必要です。

```bash
# Create security group
aws ec2 create-security-group \
  --group-name EKS-Cluster-SG \
  --description "Security group for EKS cluster" \
  --vpc-id vpc-xxxxxxxxxxxxxxxxx \
  --query GroupId \
  --output text

# Add inbound rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxxxxxxxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 4. EKS Cluster の作成

これで EKS Cluster を作成できます。

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
  --resources-vpc-config subnetIds=subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy,securityGroupIds=sg-zzzzzzzzzzzzzzzzz \
  --kubernetes-version 1.26
```

Cluster の作成が完了するまで待ちます。Cluster の status を確認するには、次のコマンドを実行します。

```bash
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.status"
```

### 5. Node IAM Role の作成

EKS nodes には AWS resources にアクセスするための IAM role が必要です。

```bash
# Create role
aws iam create-role \
  --role-name EKSNodeRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach required policies
aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam attach-role-policy \
  --role-name EKSNodeRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

### 6. Node Group の作成

これで Node Group を作成できます。

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --node-role arn:aws:iam::123456789012:role/EKSNodeRole \
  --subnets subnet-xxxxxxxxxxxxxxxxx subnet-yyyyyyyyyyyyyyyyy \
  --disk-size 80 \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --instance-types m5.large
```

Node Group の作成が完了するまで待ちます。Node Group の status を確認するには、次のコマンドを実行します。

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --query "nodegroup.status"
```

### 7. kubeconfig の設定

Cluster にアクセスするには、kubeconfig file を設定する必要があります。

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

### 8. Cluster の確認

Cluster が正しく設定されていることを確認します。

```bash
kubectl get nodes
```

## クイズ

この章で学んだ内容を確認するには、[EKS Cluster 作成 - パート 3 クイズ](../quizzes/eks/02-eks-cluster-creation-part3-quiz.md)に挑戦してみてください。
