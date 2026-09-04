# パート3: AWS Management Console と CLI を使用したクラスターの作成

## AWS Management Console を使用したクラスターの作成

AWS Management Console を使用して EKS クラスターを作成する手順は次のとおりです。

![サインインからクラスター設定、確認と作成、ノードグループの追加、接続までのコンソールベースの作成ワークフロー図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part3-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part3-0.html)

1. [AWS Management Console](https://console.aws.amazon.com/) にログインします。
2. 「EKS」を検索するか、サービス一覧から「Elastic Kubernetes Service」を選択します。
3. 「Clusters」ページで、「Create cluster」ボタンをクリックします。

### クラスターの設定

4. 「Configure cluster」ページで、次の情報を入力します。
   * **Cluster name**: クラスターの一意の名前を入力します。
   * **Kubernetes version**: 使用する Kubernetes バージョンを選択します。
   * **Cluster service role**: 新しいロールを作成するか、既存のロールを選択します。
   * **Tags**: 必要に応じてタグを追加します。
   * 「Next」ボタンをクリックします。

### ネットワークの指定

5. 「Specify networking」ページで、次の情報を入力します。
   * **VPC**: 新しい VPC を作成するか、既存の VPC を選択します。
   * **Subnets**: クラスターで使用するサブネットを選択します。少なくとも 2 つのサブネットが異なるアベイラビリティーゾーンに存在する必要があります。
   * **Security groups**: クラスターで使用するセキュリティグループを選択します。
   * **Cluster endpoint access**: クラスター API サーバーエンドポイントへのアクセスを設定します。
     * **Public**: インターネットから API サーバーにアクセスできます。
     * **Private**: VPC 内からのみ API サーバーにアクセスできます。
     * **Public and Private**: インターネットと VPC 内の両方から API サーバーにアクセスできます。
   * 「Next」ボタンをクリックします。

### ロギングの設定

6. 「Configure logging」ページで、次の情報を入力します。
   * **Control plane logging**: 有効にするログタイプを選択します。
     * API サーバーログ
     * 監査ログ
     * Authenticator ログ
     * Controller manager ログ
     * Scheduler ログ
   * 「Next」ボタンをクリックします。

### アドオンの選択

7. 「Select add-ons」ページで、次の情報を入力します。
   * **Amazon VPC CNI**: Pod ネットワーキング用の CNI プラグインです。
   * **CoreDNS**: クラスター内の DNS サービスです。
   * **kube-proxy**: ネットワークプロキシと負荷分散を提供します。
   * 「Next」ボタンをクリックします。

### 確認と作成

8. 「Review and create」ページで設定を確認し、「Create」ボタンをクリックします。

クラスターの作成が完了したら、「Add node group」ボタンをクリックしてノードグループを追加できます。

### ノードグループの追加

1. 「Node group configuration」ページで、次の情報を入力します。
   * **Node group name**: ノードグループの一意の名前を入力します。
   * **Node IAM role**: 新しいロールを作成するか、既存のロールを選択します。
   * 「Next」ボタンをクリックします。
2. 「Set compute and scaling configuration」ページで、次の情報を入力します。
   * **AMI type**: ノードで使用する AMI タイプを選択します。
   * **Instance type**: ノードで使用する EC2 インスタンスタイプを選択します。
   * **Disk size**: ノードのディスクサイズを指定します。
   * **Node count**: ノードの最小数、最大数、希望する数を指定します。
   * 「Next」ボタンをクリックします。
3. 「Specify networking」ページで、次の情報を入力します。
   * **Subnets**: ノードグループで使用するサブネットを選択します。
   * **Remote access configuration**: SSH アクセスを設定します。
   * 「Next」ボタンをクリックします。
4. 「Review and create」ページで設定を確認し、「Create」ボタンをクリックします。

## AWS CLI を使用したクラスターの作成

AWS CLI を使用した EKS クラスターの作成プロセスはいくつかの手順で構成されます。より細かな制御が必要な場合に、この方法は有用です。

![最初に IAM ロール、VPC、セキュリティグループを作成し、次にクラスターとノードグループを作成した後、kubeconfig を更新する AWS CLI ワークフロー図。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part3-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part3-1.html)

### 1. クラスター IAM ロールの作成

EKS クラスターには、Kubernetes コントロールプレーンが AWS リソースを管理できるようにする IAM ロールが必要です。

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

### 2. VPC とサブネットの作成

EKS クラスターには VPC とサブネットが必要です。既存の VPC を使用することも、新しい VPC を作成することもできます。

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

### 3. クラスターセキュリティグループの作成

EKS クラスターにはセキュリティグループが必要です。

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

### 4. EKS クラスターの作成

これで EKS クラスターを作成できます。

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
  --resources-vpc-config subnetIds=subnet-xxxxxxxxxxxxxxxxx,subnet-yyyyyyyyyyyyyyyyy,securityGroupIds=sg-zzzzzzzzzzzzzzzzz \
  --kubernetes-version 1.26
```

クラスターの作成が完了するまで待ちます。クラスターのステータスを確認するには、次のコマンドを実行します。

```bash
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.status"
```

### 5. ノード IAM ロールの作成

EKS ノードには、AWS リソースにアクセスするための IAM ロールが必要です。

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

### 6. ノードグループの作成

これでノードグループを作成できます。

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

ノードグループの作成が完了するまで待ちます。ノードグループのステータスを確認するには、次のコマンドを実行します。

```bash
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --query "nodegroup.status"
```

### 7. kubeconfig の設定

クラスターにアクセスするには、kubeconfig ファイルを設定する必要があります。

```bash
aws eks update-kubeconfig \
  --name my-cluster \
  --region us-west-2
```

### 8. クラスターの検証

クラスターが正しく設定されていることを確認します。

```bash
kubectl get nodes
```

## クイズ

この章で学んだ内容を確認するには、[EKS Cluster Creation - Part 3 クイズ](../quizzes/eks/02-eks-cluster-creation-part3-quiz.md)に挑戦してください。
