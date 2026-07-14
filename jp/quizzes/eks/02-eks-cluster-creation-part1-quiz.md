# EKS Cluster Creation クイズ - Part 1

このクイズでは、Amazon EKS cluster 作成に関連する concepts、tools、best practices についての理解を確認します。cluster 作成方法、VPC configuration、node group setup などのトピックを扱います。

## 基本概念の問題

1. Amazon EKS cluster の作成に使用できない tool はどれですか？
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>答えを表示</summary>

**答え: D) kubectl**

**解説:** kubectl は Kubernetes clusters を管理するための command-line tool ですが、EKS clusters の作成には使用できません。kubectl は既存の Kubernetes cluster に接続して resources を管理するために使用されます。

Amazon EKS clusters の作成に使用できる tools には、次のものがあります:

1. **AWS Management Console**:
   * Web interface を通じて EKS clusters を作成します。
   * cluster components を視覚的に設定できるため、初心者に適しています。
   * step-by-step wizard によって cluster 作成 process を案内します。
2.  **AWS CLI**:

    * command line から EKS clusters を作成します。
    * `aws eks create-cluster` command を使用します。
    * scripts と automation に適しています。

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * EKS cluster 作成専用に設計された command-line tool です。
    * EKS cluster の作成と管理を簡素化する、Weaveworks が開発した open-source tool です。
    * 1 つの command で cluster を作成できます。

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code (IaC) tools**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    これらの tools により、EKS clusters を code として定義し、デプロイできます。

kubectl は、cluster 作成後に Kubernetes resources (pods、services、deployments など) を管理するために使用されます。EKS cluster に接続するには、まず `aws eks update-kubeconfig` command を使用して kubectl configuration を更新する必要があります。

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

その後、kubectl を使用して cluster resources を管理できます。

</details>

2. Amazon EKS cluster を作成するときに指定する必要がある VPC component は何ですか？
   * A) Public subnets のみ
   * B) Private subnets のみ
   * C) 少なくとも 2 つの availability zones にまたがる subnets
   * D) NAT Gateway

<details>

<summary>答えを表示</summary>

**答え: C) 少なくとも 2 つの availability zones にまたがる subnets**

**解説:** Amazon EKS cluster を作成するときに指定する必要がある VPC component は、少なくとも 2 つの availability zones にまたがる subnets です。これは EKS clusters の high availability を確保するための AWS の要件です。

**EKS cluster VPC requirements:**

1. **少なくとも 2 つの availability zones (AZs) に subnets が必要**:
   * EKS control plane は複数の availability zones にまたがってデプロイされるため、cluster 作成時には少なくとも 2 つの availability zones の subnets を指定する必要があります。
   * これにより、単一の availability zone 障害時でも cluster が稼働し続けることを確保します。
2. **Subnet types**:
   * public subnets のみ、private subnets のみ、または public と private subnets の組み合わせを使用できます。
   * production environments では、security のため worker nodes を private subnets に配置し、load balancers には public subnets を使用することが推奨されます。
3. **Subnet CIDR size**:
   * 各 subnet には十分な IP addresses が必要です。
   * EKS は各 pod に VPC IP addresses を割り当てるため、想定される pod 数に基づいて十分に大きい CIDR blocks が必要です。
4. **Tag requirements**:
   * EKS が subnets を識別し適切に使用するために、特定の tags が必要です:
     * Shared subnets: `kubernetes.io/cluster/<cluster-name>: shared`
     * Public subnets: `kubernetes.io/role/elb: 1`
     * Private subnets: `kubernetes.io/role/internal-elb: 1`

**VPC configuration example (using eksctl):**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  cidr: 192.168.0.0/16
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
    public:
      us-west-2a:
        id: subnet-0123456789abcdef2
      us-west-2b:
        id: subnet-0123456789abcdef3
```

**VPC configuration using AWS CLI:**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

Private subnets 内の worker nodes が internet access を必要とする場合、NAT Gateway が必要ですが、EKS cluster 作成そのものに必須の component ではありません。public subnets のみを使用する場合、NAT Gateway なしで cluster を作成できます (production environments では推奨されません)。

</details>

3. Amazon EKS cluster を作成するときに必要な IAM roles は何ですか？
   * A) EKS service role のみ
   * B) Node instance role のみ
   * C) EKS service role と node instance role
   * D) Fargate execution role

<details>

<summary>答えを表示</summary>

**答え: C) EKS service role と node instance role**

**解説:** Amazon EKS cluster を作成して運用するには、2 つの主要な IAM roles が必要です: EKS service role と node instance role です。これら 2 つの roles は異なる目的を持ち、cluster の適切な運用にはどちらも必要です。

**1. EKS Service Role (EKS Cluster Role):**

* **Purpose**: AWS EKS service が users に代わって他の AWS services を呼び出せるようにします。
* **Required permissions**:
  * EC2、ELB、CloudWatch、KMS などの AWS services への access
  * VPC resource management
  * Log group creation and management
* **Managed policy**: `AmazonEKSClusterPolicy`
*   **Creation method**:

    ```bash
    # Create role using AWS CLI
    aws iam create-role \
      --role-name EKSClusterRole \
      --assume-role-policy-document file://eks-cluster-trust-policy.json

    # Attach managed policy
    aws iam attach-role-policy \
      --role-name EKSClusterRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
    ```

    Trust policy (eks-cluster-trust-policy.json):

    ```json
    {
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
    }
    ```

**2. Node Instance Role (Node Instance Role):**

* **Purpose**: EKS worker nodes (EC2 instances) が AWS services とやり取りできるようにします。
* **Required permissions**:
  * ECR から container images を pull する
  * CloudWatch に logs を書き込む
  * EBS/EFS volumes を管理する
  * Load balancer registration/deregistration
* **Managed policies**:
  * `AmazonEKSWorkerNodePolicy`
  * `AmazonEC2ContainerRegistryReadOnly`
  * `AmazonEKS_CNI_Policy`
*   **Creation method**:

    ```bash
    # Create role using AWS CLI
    aws iam create-role \
      --role-name EKSNodeRole \
      --assume-role-policy-document file://ec2-trust-policy.json

    # Attach managed policies
    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

    aws iam attach-role-policy \
      --role-name EKSNodeRole \
      --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
    ```

    Trust policy (ec2-trust-policy.json):

    ```json
    {
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
    }
    ```

**Automatic role creation using eksctl:**

eksctl を使用して cluster を作成する場合、必要な IAM roles を自動的に作成できます:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

**Additional roles (optional):**

* **Fargate execution role**: Fargate profiles を使用する場合にのみ必要です。
* **Service account IAM roles**: IRSA (IAM Roles for Service Accounts) を使用する場合に必要です。
* **ALB controller role**: AWS Load Balancer Controller を使用する場合に必要です。

Fargate execution role は Fargate profiles を使用する場合にのみ必要であり、basic EKS cluster 作成には必須ではありません。したがって、EKS cluster を作成するために必要な IAM roles は EKS service role と node instance role です。

</details>

4. eksctl を使用して EKS cluster を作成する正しい command はどれですか？
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>答えを表示</summary>

**答え: B) `eksctl create cluster --name my-cluster --region us-west-2`**

**解説:** eksctl を使用して EKS cluster を作成する正しい command は `eksctl create cluster --name my-cluster --region us-west-2` です。この command は、指定した name と region に default settings で EKS cluster を作成します。

**eksctl command structure:**

* `eksctl`: Base command
* `create`: resource を作成する action
* `cluster`: 作成する resource の type (cluster)
* `--name my-cluster`: cluster name を指定
* `--region us-west-2`: AWS region を指定

**Basic cluster creation command:**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

この command は、次の default settings で cluster を作成します:

* 2 m5.large nodes
* New VPC creation
* Default Amazon Linux 2 AMI
* Managed node groups
* 必要な IAM roles の automatic creation

**Advanced command with additional options:**

```bash
eksctl create cluster \
  --name my-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --with-oidc \
  --ssh-access \
  --ssh-public-key my-key \
  --managed
```

**Cluster creation using a configuration file:**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.28"

nodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: true
      publicKeyName: my-key
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**Problems with other options:**

* `eksctl create-cluster`: command format が正しくありません。eksctl は commands を区切るために hyphens (-) ではなく spaces を使用します。
* `eksctl new cluster`: 'new' は有効な eksctl command ではありません。
* `eksctl start cluster`: 'start' は有効な eksctl command ではありません。既存の cluster を起動するという concept は EKS には適用されません。

eksctl は EKS cluster management のためにさまざまな commands を提供します:

* `eksctl create cluster`: 新しい cluster を作成
* `eksctl get cluster`: clusters を一覧表示
* `eksctl update cluster`: cluster を更新
* `eksctl delete cluster`: cluster を削除
* `eksctl create nodegroup`: node group を追加
* `eksctl scale nodegroup`: node group を scale

</details>

5. Amazon EKS cluster 作成時に指定できる Kubernetes versions について正しいものはどれですか？
   * A) 最新 version のみがサポートされる
   * B) 最新 version と直前の 2 versions のみがサポートされる
   * C) AWS がサポートするすべての Kubernetes versions
   * D) すべての Kubernetes versions

<details>

<summary>答えを表示</summary>

**答え: C) AWS がサポートするすべての Kubernetes versions**

**解説:** Amazon EKS cluster を作成する際、AWS が現在サポートしている Kubernetes versions から選択できます。AWS は通常、latest version と複数の previous versions を含め、複数の Kubernetes versions を同時にサポートします。

**EKS Kubernetes version support policy:**

1. **Support period**:
   * 各 Kubernetes version は、EKS での release 後 14 か月間サポートされます。
   * End of support dates は少なくとも 60 日前に発表されます。
2. **Supported versions**:
   * 通常、EKS は 3〜4 個の Kubernetes versions を同時にサポートします。
   * 新しい versions は、Kubernetes community release から数か月以内に EKS で利用可能になります。
3.  **How to check versions**:

    ```bash
    # Check supported versions using AWS CLI
    aws eks describe-addon-versions | grep kubernetesVersion | sort -u

    # Or
    aws eks get-cluster-version-list
    ```
4.  **Version specification examples**:

    ```bash
    # Specify a specific version using eksctl
    eksctl create cluster --name my-cluster --version 1.28 --region us-west-2

    # Specify a specific version using AWS CLI
    aws eks create-cluster \
      --name my-cluster \
      --kubernetes-version 1.28 \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890
    ```
5.  **Version upgrades**:

    * cluster 作成後、サポートされている versions へ upgrade できます。
    * 一般的には、一度に 1 つの minor version ずつ upgrade することが推奨されます。

    ```bash
    # Cluster version upgrade
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.28
    ```

**Considerations when selecting a version:**

1. **Stability**:
   * latest version は新機能を提供しますが、初期 bugs がある場合があります。
   * stability が重要な production environments では、実績のある previous version を選択する方がよい場合があります。
2. **Feature requirements**:
   * 特定の Kubernetes features が必要な場合、それらの features をサポートする minimum version を選択する必要があります。
3. **Support period**:
   * long-term support のためには、support period を最大化するために最近 release された version を選択します。
4. **Ecosystem compatibility**:
   * 使用している tools、add-ons、operators が、選択した Kubernetes version と互換性があることを確認します。

他の選択肢の問題点:

* 最新 version のみがサポートされるわけではなく、複数の versions が同時にサポートされます。
* サポートされる versions の数は「最新 version と直前の 2 versions」に固定されているわけではなく、AWS の support policy によって変わります。
* すべての Kubernetes versions がサポートされるわけではなく、AWS によってテストされサポートされている versions のみ使用できます。

</details>

6. Amazon EKS cluster で node groups を作成する option ではないものはどれですか？
   * A) Managed node groups
   * B) Self-managed node groups
   * C) Fargate profiles
   * D) Serverless node groups

<details>

<summary>答えを表示</summary>

**答え: D) Serverless node groups**

**解説:** 「Serverless node groups」は Amazon EKS に存在する concept ではありません。EKS で workloads を実行するための 3 つの主な options は、managed node groups、self-managed node groups、Fargate profiles です。

**1. Managed Node Groups:**

* **Features**:
  * AWS が node provisioning と lifecycle を管理
  * EC2 instance creation and registration の自動化
  * ASG (Auto Scaling Group) configuration の自動化
  * Kubernetes version upgrades の自動化
  * damaged nodes の自動 replacement
  * node AMI updates の自動化
*   **Creation method**:

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-mng \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name my-mng \
      --subnets subnet-12345 subnet-67890 \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role arn:aws:iam::123456789012:role/EksNodeRole
    ```

**2. Self-managed Node Groups:**

* **Features**:
  * user が node provisioning と lifecycle を管理
  * より多くの customization options
  * custom AMIs や bootstrap scripts を使用可能
  * 特定の instance types や configuration requirements に適している
*   **Creation method**:

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-smng \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Fargate Profiles:**

* **Features**:
  * Serverless container execution environment
  * node management が不要
  * pod ごとの resource allocation and billing
  * 特定の namespaces と labels に基づく selective execution
*   **Creation method**:

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster my-cluster \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name my-cluster \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn arn:aws:iam::123456789012:role/FargatePodExecutionRole \
      --selectors namespace=my-namespace,labels={app=my-app}
    ```

**Comparison of each option:**

| Feature             | Managed Node Groups | Self-managed Node Groups | Fargate Profiles             |
| ------------------- | ------------------- | ------------------------ | ---------------------------- |
| Management overhead | Low                 | High                     | None                         |
| Customization       | Medium              | High                     | Low                          |
| Cost efficiency     | Medium              | High (when optimized)    | Low (paying for convenience) |
| Scalability         | Automatic           | Manual/Automatic         | Automatic                    |
| Use case            | General workloads   | Special requirements     | Variable workloads, dev/test |

「serverless node groups」という term は公式には存在しません。Fargate は serverless container execution environment を提供しますが、「node groups」ではなく「Fargate profiles」として設定されます。Fargate を使用する場合、nodes を直接管理する必要はなく、pod execution に必要な compute resources だけが provision されます。

</details>

7. Amazon EKS clusters でサポートされている node AMI type ではないものはどれですか？
   * A) Amazon Linux 2
   * B) Amazon Linux 2023
   * C) Bottlerocket
   * D) Ubuntu Core

<details>

<summary>答えを表示</summary>

**答え: D) Ubuntu Core**

**解説:** Ubuntu Core は Amazon EKS で公式にサポートされている node AMI type ではありません。EKS で公式にサポートされている node AMI types は Amazon Linux 2、Amazon Linux 2023、Bottlerocket です。

**Supported node AMI types in EKS:**

1.  **Amazon Linux 2 (AL2)**:

    * AWS が提供する default Linux distribution
    * EKS optimized AMI として利用可能
    * ほとんどの EKS workloads に推奨
    * Long-term support and security updates

    ```bash
    # Create Amazon Linux 2 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2-nodes \
      --node-ami-family AmazonLinux2
    ```
2.  **Amazon Linux 2023 (AL2023)**:

    * Amazon Linux の latest version
    * enhanced security and performance
    * latest kernel and software packages
    * EKS optimized AMI として利用可能

    ```bash
    # Create Amazon Linux 2023 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2023-nodes \
      --node-ami-family AmazonLinux2023
    ```
3.  **Bottlerocket**:

    * container workloads に最適化された open-source Linux-based OS
    * minimized attack surface
    * transaction-based updates
    * container-centric design

    ```bash
    # Create Bottlerocket based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name bottlerocket-nodes \
      --node-ami-family Bottlerocket
    ```

**Other supported AMI options:**

1.  **Windows**:

    * Windows Server 2019、2022 based AMIs
    * Windows container workloads を実行可能

    ```bash
    # Create Windows based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-nodes \
      --node-ami-family WindowsServer2022FullContainer
    ```
2.  **Custom AMIs**:

    * 特定の requirements に custom AMIs を使用可能
    * 主に self-managed node groups で使用される

    ```bash
    # Create custom AMI based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-nodes \
      --node-ami ami-1234567890abcdef0
    ```

**How to use Ubuntu in EKS:**

Ubuntu Core は公式にはサポートされていませんが、standard Ubuntu Server AMIs を使用して self-managed node groups を作成できます。この場合、追加の configuration が必要です:

1. Ubuntu Server AMI を選択
2. 必要な Kubernetes components をインストール
3. bootstrap script を使用して nodes を cluster に接続

```bash
# Example of creating Ubuntu-based self-managed node group
eksctl create nodegroup \
  --cluster my-cluster \
  --name ubuntu-nodes \
  --node-ami ami-ubuntu-server-id \
  --managed=false \
  --ssh-access \
  --ssh-public-key my-key \
  --pre-bootstrap-commands 'apt-get update && apt-get install -y docker.io'
```

**Considerations when selecting AMI:**

* **Security**: Regular security updates and patches
* **Performance**: workload に最適化された kernel and configuration
* **Compatibility**: Kubernetes version との compatibility
* **Ease of management**: Update and maintenance processes
* **Special requirements**: GPU support、kernel modules など

Ubuntu Core は IoT と edge devices 向けの lightweight operating system であり、EKS nodes としての使用は公式にサポートも最適化もされていません。したがって、Ubuntu Core は EKS clusters でサポートされている node AMI type ではありません。

</details>

8. Amazon EKS clusters の endpoint access configuration について正しいものはどれですか？
   * A) デフォルトでは public endpoint のみ有効
   * B) デフォルトでは private endpoint のみ有効
   * C) デフォルトでは public と private endpoints の両方が有効
   * D) Endpoint access は cluster 作成後に変更できない

<details>

<summary>答えを表示</summary>

**答え: A) デフォルトでは public endpoint のみ有効**

**解説:** Amazon EKS cluster を作成する場合、デフォルトでは public endpoint のみが有効で、private endpoint は無効です。この configuration は cluster 作成後に変更でき、security requirements に応じてさまざまな endpoint access configurations を選択できます。

**EKS cluster endpoint access options:**

1.  **Public endpoint only enabled (default setting)**:

    * Cluster API server は internet 経由でアクセス可能
    * Security groups によって access を制限可能
    * development または test environments に適している

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=false
    ```
2.  **Both public and private endpoints enabled**:

    * VPC 内から private IP 経由でアクセス可能
    * internet 経由でもアクセス可能
    * hybrid environments に適している

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true
    ```
3.  **Private endpoint only enabled**:

    * Cluster API server は VPC 内からのみアクセス可能
    * internet 経由の access はなし
    * 最高レベルの security を提供
    * production environments に推奨

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
    ```
4.  **Restricting public access**:

    * 特定の CIDR blocks からのみ public endpoint access を許可
    * company network または VPN からの access のみに制限

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]
    ```

**Endpoint configuration when creating cluster with eksctl:**

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  clusterEndpoints:
    publicAccess: true   # Enable public endpoint
    privateAccess: true  # Enable private endpoint
  publicAccessCIDRs: ["203.0.113.0/24"]  # Restrict public access
```

```bash
eksctl create cluster -f cluster.yaml
```

**Changing endpoint access configuration:**

```bash
# Enable private endpoint
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPrivateAccess=true

# Disable public endpoint
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false
```

**Considerations when configuring endpoint access:**

1. **Security requirements**:
   * private endpoint のみを使用すると、最高レベルの security が提供されます。
   * public access が必要な場合は CIDR restrictions を適用します。
2. **Network connectivity**:
   * private endpoint のみを使用する場合、access は VPC 内または VPN/Direct Connect 経由でのみ可能です。
   * 両方の endpoints を有効にすると、hybrid work environments で有用な場合があります。
3. **Operational requirements**:
   * CI/CD pipelines、external tools などが cluster access を必要とする場合を考慮します。
4. **Cost**:
   * endpoint configuration 自体に追加 cost はありません。
   * private endpoint のみを使用する場合は、VPN または Direct Connect costs を考慮します。

他の選択肢の問題点:

* デフォルトでは private endpoint ではなく、public endpoint のみが有効です。
* デフォルトでは public と private endpoints の両方が有効ではなく、public endpoint のみが有効です。
* Endpoint access は cluster 作成後に変更できます。

</details>

9. Amazon EKS clusters の node groups で instance types を選択するときの考慮事項ではないものはどれですか？
   * A) Workload requirements (CPU, memory, storage)
   * B) Cost optimization
   * C) availability zones の数
   * D) Instance generation (e.g., t3 vs t2)

<details>

<summary>答えを表示</summary>

**答え: C) availability zones の数**

**解説:** availability zones の数は、node groups の instance types を選択する際の直接的な考慮事項ではありません。availability zones は node groups がどこにデプロイされるかに関連し、instance types そのものの選択とは別です。instance types は workload requirements、cost optimization、instance generation などを考慮して選択する必要があります。

**Actual considerations when selecting node group instance types:**

1. **Workload requirements (CPU, memory, storage)**:
   * application resource requirements に合う instance types を選択
   * Memory-intensive workloads: r5、r6g などの Memory optimized instances
   * Compute-intensive workloads: c5、c6g などの Compute optimized instances
   * Balanced workloads: m5、m6g などの General purpose instances
   * GPU workloads: p3、g4dn などの Accelerated computing instances
2. **Cost optimization**:
   * On-demand vs Spot instances
   * Reserved Instances または Savings Plans
   * 適切な size の instance selection (over-provisioning を避ける)
   * ARM-based Graviton instances (e.g., m6g, c6g) による cost savings
3. **Instance generation**:
   * latest generation instances は一般に、より良い performance と cost efficiency を提供します。
   * Example: t3 は t2 よりも優れた performance と price-to-performance を提供します。
   * latest generations は enhanced networking、storage performance などを提供します。
4. **Networking requirements**:
   * Enhanced networking support (ENA、EFA など)
   * Network bandwidth requirements
   * instance あたりの maximum pods に関連する networking limits
5. **Storage requirements**:
   * local instance storage が必要かどうか (e.g., i3、d3 instances)
   * EBS optimization support
   * Storage throughput and IOPS requirements
6. **CPU architecture**:
   * x86 (Intel、AMD) vs ARM (AWS Graviton)
   * Application compatibility considerations

**Availability zones and node group deployment:**

availability zones の数は、instance type selection ではなく、node group deployment strategy に関連します:

* high availability のため、node groups を複数の availability zones にまたがってデプロイ
* 各 availability zone に nodes を均等に分散
* region 内のすべての availability zones、または特定の availability zones を選択可能

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**Instance type selection examples:**

1. **Web application servers**:
   * General purpose instances: t3.medium、m5.large
   * balanced performance で cost-effective
2. **Databases**:
   * Memory optimized instances: r5.xlarge、r6g.xlarge
   * 高い memory to CPU ratio
3. **Batch processing jobs**:
   * Compute optimized instances: c5.xlarge、c6g.xlarge
   * 高い CPU performance
4. **Machine learning workloads**:
   * GPU instances: p3.2xlarge、g4dn.xlarge
   * Accelerated computing capabilities

Instance type selection は workload characteristics、cost constraints、performance requirements などによって決定されるべきであり、availability zones の数は instance types そのものの選択ではなく node group deployment strategy に関連します。

</details>

10. Amazon EKS cluster 作成後に kubectl を設定する正しい command はどれですか？
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>答えを表示</summary>

**答え: A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**解説:** Amazon EKS cluster 作成後に kubectl を設定する正しい command は `aws eks update-kubeconfig --name my-cluster --region us-west-2` です。この command は AWS CLI の EKS module を使用して、指定された cluster の kubeconfig file を更新します。

**kubectl configuration process:**

1. **Updating kubeconfig file**:
   * kubeconfig file は、kubectl が Kubernetes clusters と通信するために必要な configuration information を保存します。
   * デフォルトでは `~/.kube/config` に保存されます。
   * `aws eks update-kubeconfig` command はこの file を自動的に更新します。
2. **Command components**:
   * `--name`: EKS cluster name
   * `--region`: cluster が配置されている AWS region
   * `--kubeconfig` (optional): Custom kubeconfig file path
   * `--role-arn` (optional): cluster access に使用する IAM role
3.  **Full command example**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
4.  **Additional options**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig ~/.kube/eks-config

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias
    ```
5.  **Verify configuration**:

    ```bash
    # Check current context
    kubectl config current-context

    # List all contexts
    kubectl config get-contexts

    # Test cluster connection
    kubectl cluster-info
    ```

**Problems with other options:**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`: この command は存在しません。AWS CLI には `get-kubeconfig` subcommand はありません。
* `kubectl config set-cluster my-cluster --region us-west-2`: この command は syntax が正しくありません。`kubectl config set-cluster` は `--region` flag をサポートしておらず、EKS clusters に必要な authentication information を自動設定しません。
* `eksctl configure kubectl --name my-cluster --region us-west-2`: この command は存在しません。eksctl には `configure kubectl` subcommand はありません。eksctl で cluster を作成する場合、kubeconfig は自動的に設定されますが、既存の clusters では `aws eks update-kubeconfig` command を使用する必要があります。

**Cluster creation and configuration using eksctl:**

eksctl を使用して cluster を作成する場合、kubeconfig は自動的に更新されます:

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

この command は cluster を作成し、kubeconfig を自動的に更新します。ただし、既存の cluster または別の tool で作成した cluster に接続するには、`aws eks update-kubeconfig` command を使用する必要があります。

**Managing multiple clusters:**

複数の EKS clusters を管理する場合、各 cluster に対して `aws eks update-kubeconfig` command を実行することで、それらを kubeconfig file に追加できます:

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1

# Switch context
kubectl config use-context arn:aws:eks:us-west-2:123456789012:cluster/cluster1
```

したがって、Amazon EKS cluster 作成後に kubectl を設定する正しい command は `aws eks update-kubeconfig --name my-cluster --region us-west-2` です。

</details>

## ハンズオン演習

### Exercise 1: eksctl を使用して EKS Cluster を作成

**Scenario:** あなたは会社の DevOps engineer で、development team 向けに Amazon EKS cluster を作成する必要があります。この cluster は cost-effective でありながら scalable で、basic security settings を備える必要があります。

**Requirements:**

1. eksctl を使用して EKS cluster を作成
2. 2 つの availability zones にまたがってデプロイ
3. t3.medium instance type を使用
4. auto-scaling (minimum 2、maximum 5 nodes) を設定
5. private と public endpoints の両方を有効化

**Solution:**

<details>

<summary>答えを表示</summary>

**1. Install eksctl (if not already installed)**

```bash
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version
```

**2. Create cluster configuration file**

```bash
cat > eks-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true

availabilityZones: ["us-west-2a", "us-west-2b"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        ebs: true
        albIngress: true
        cloudWatch: true
    ssh:
      allow: false
    privateNetworking: true
    tags:
      Environment: development
      Owner: devops-team
EOF
```

**3. Create the cluster**

```bash
eksctl create cluster -f eks-cluster.yaml
```

この command は次の tasks を実行します:

* CloudFormation stacks を作成
* VPC と subnets を作成
* security groups を設定
* EKS cluster を作成
* managed node groups を作成
* nodes を bootstrap し cluster に接続
* kubeconfig を設定

**4. Verify the cluster**

```bash
# Check cluster status
eksctl get cluster --name dev-cluster --region us-west-2

# Check nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

**5. Configure cluster access**

```bash
# Verify kubeconfig
kubectl config current-context

# Check cluster information
kubectl cluster-info
```

**6. Verify basic security settings**

```bash
# Check namespaces
kubectl get namespaces

# Check RBAC settings
kubectl get clusterroles
kubectl get clusterrolebindings
```

**7. Monitor cluster resources**

```bash
# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods --all-namespaces
```

この演習を通じて、eksctl を使用して cost-effective で scalable な EKS cluster を作成する方法を学びました。t3.medium instances は cost-effective な選択肢であり、auto-scaling configuration により workload に基づいて node count を自動調整できます。internal と external の両方から cluster access を可能にするため、private と public endpoints の両方を有効化しました。

</details>

### Exercise 2: AWS Management Console を使用して EKS Cluster を作成

**Scenario:** AWS Management Console を使用して EKS cluster を作成および設定する必要があります。この cluster は、security と high availability が重要な production environment 向けです。

**Requirements:**

1. AWS Management Console を使用して EKS cluster を作成
2. nodes を private subnets に配置
3. cluster endpoint への public access を制限
4. managed node groups を設定
5. 必要な IAM roles を作成

**Solution:**

<details>

<summary>答えを表示</summary>

**1. Create required IAM roles**

**Create EKS cluster role:**

1. AWS Management Console にログインし、IAM service に移動します。
2. left menu で "Roles" を選択し、"Create role" をクリックします。
3. trusted entity type として "AWS service" を選択します。
4. use case で "EKS" を選択し、次に "EKS - Cluster" を選択します。
5. "Next" をクリックします。
6. `AmazonEKSClusterPolicy` が自動的に選択されていることを確認します。
7. "Next" をクリックします。
8. role name として "EKSClusterRole" を入力し、"Create role" をクリックします。

**Create EKS node role:**

1. IAM service で再度 "Create role" をクリックします。
2. trusted entity type として "AWS service" を選択します。
3. use case で "EC2" を選択します。
4. "Next" をクリックします。
5. 次の policies を検索して選択します:
   * `AmazonEKSWorkerNodePolicy`
   * `AmazonEC2ContainerRegistryReadOnly`
   * `AmazonEKS_CNI_Policy`
6. "Next" をクリックします。
7. role name として "EKSNodeRole" を入力し、"Create role" をクリックします。

**2. Prepare VPC and subnets**

production environments には適切な VPC configuration が必要です。AWS CloudFormation template を使用して、EKS-optimized VPC を作成できます:

1. CloudFormation console に移動します。
2. "Create stack" > "With new resources (standard)" を選択します。
3.  Amazon S3 URL に次の address を入力します:

    ```
    https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
    ```
4. "Next" をクリックします。
5. stack name として "eks-vpc" を入力します。
6. default parameters のままにして "Next" をクリックします。
7. 次の page で default options のままにして "Next" をクリックします。
8. "Create stack" をクリックします。
9. stack creation が完了したら、"Outputs" tab から次の values を記録します:
   * VpcId
   * SubnetIds
   * SecurityGroups

**3. Create EKS cluster**

1. AWS Management Console で EKS service に移動します。
2. "Create cluster" をクリックします。
3. "Cluster configuration" page で:
   * Cluster name: "prod-cluster"
   * Kubernetes version: latest version (e.g., 1.28) を選択
   * Cluster service role: 以前に作成した "EKSClusterRole" を選択
   * "Next" をクリックします。
4. "Specify networking" page で:
   * VPC: 以前に作成した VPC を選択
   * Subnets: private subnets のみを選択 (public subnets の選択を解除)
   * Security groups: default security group を選択
   * Cluster endpoint access:
     * "Private" を選択、または
     * "Public and Private" を選択し、CIDR blocks を company IP range に制限
   * "Next" をクリックします。
5. "Configure logging" page で:
   * 必要な log types (API server, Audit, Authenticator, Controller manager, Scheduler) を選択
   * "Next" をクリックします。
6. "Select add-ons" page で:
   * default add-ons (kube-proxy, CoreDNS, VPC CNI) を維持
   * "Next" をクリックします。
7. review page ですべての settings を確認し、"Create" をクリックします。
8. cluster creation が完了するまで待ちます (約 15〜20 分)。

**4. Create managed node group**

1. cluster が作成されたら、cluster name をクリックします。
2. "Compute" tab に移動し、"Add node group" をクリックします。
3. "Node group configuration" page で:
   * Name: "prod-nodes"
   * Node IAM role: 以前に作成した "EKSNodeRole" を選択
   * "Next" をクリックします。
4. "Set compute and scaling configuration" page で:
   * AMI type: Amazon Linux 2 (x86)
   * Instance type: m5.large を選択
   * Disk size: 50 GiB
   * Node group scaling configuration:
     * Minimum size: 2
     * Maximum size: 5
     * Desired size: 3
   * "Next" をクリックします。
5. "Specify networking" page で:
   * Subnets: private subnets のみを選択
   * "Next" をクリックします。
6. "Review and create" page ですべての settings を確認し、"Create" をクリックします。
7. node group creation が完了するまで待ちます (約 5 分)。

**5. Configure kubectl and access cluster**

1. AWS CLI がインストールされていることを確認します。
2.  kubectl configuration file を更新するために、次の command を実行します:

    ```bash
    aws eks update-kubeconfig --name prod-cluster --region us-west-2
    ```
3.  cluster connection を確認します:

    ```bash
    kubectl get nodes
    kubectl cluster-info
    ```

**6. Enhance basic security**

1.  AWS security group rules を確認して制限します:

    ```bash
    # Check cluster information for current context
    kubectl config view --minify
    ```
2.  network policies を適用します (optional):

    ```yaml
    # default-deny.yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: default-deny
      namespace: default
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
    ```

    ```bash
    kubectl apply -f default-deny.yaml
    ```

この演習を通じて、AWS Management Console を使用して production environments に適した security と high availability settings を備えた EKS cluster を作成する方法を学びました。nodes を private subnets に配置し、cluster endpoint への public access を制限することで security を強化し、managed node groups を使用することで node management を簡素化しました。

</details>

## 高度なトピック

以下は Amazon EKS cluster 作成に関連する advanced topics についての問題です。この section では、EKS cluster 作成の advanced concepts と best practices についての理解を確認します。

1. Amazon EKS clusters で custom Launch Templates を使用する主なメリットは何ですか？
   * A) cluster creation time の短縮
   * B) Customizable node bootstrap scripts と additional volume configuration
   * C) Cluster control plane customization
   * D) latest AMI version を自動的に使用する

<details>

<summary>答えを表示</summary>

**答え: B) Customizable node bootstrap scripts と additional volume configuration**

**解説:** Amazon EKS clusters で custom Launch Templates を使用する主なメリットは、node bootstrap scripts をカスタマイズし、additional volumes を設定できることです。Launch templates により EC2 instances のさまざまな側面をきめ細かく制御でき、default node group creation options では不可能な advanced configurations を実現できます。

**Customizable items with Launch Templates:**

1. **Custom bootstrap scripts**:
   * nodes が cluster に参加する前に実行される custom scripts を定義
   * additional software をインストールして設定
   * system settings (kernel parameters、network settings など) を調整
   *   Example:

       ```bash
       #!/bin/bash
       # Custom bootstrap script
       echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
       sysctl -p

       # Install additional packages
       yum install -y amazon-cloudwatch-agent

       # Run EKS bootstrap script
       /etc/eks/bootstrap.sh my-cluster --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker'
       ```
2. **Additional volume configuration**:
   * root volume size、type、IOPS をカスタマイズ
   * data、logs、temporary storage 用に additional EBS volumes を attach
   * instance store volumes を設定
   *   Example:

       ```json
       {
         "DeviceName": "/dev/xvda",
         "Ebs": {
           "VolumeSize": 100,
           "VolumeType": "gp3",
           "Iops": 3000,
           "Throughput": 125,
           "DeleteOnTermination": true
         }
       },
       {
         "DeviceName": "/dev/sdf",
         "Ebs": {
           "VolumeSize": 500,
           "VolumeType": "gp3",
           "DeleteOnTermination": true
         }
       }
       ```
3. **Advanced networking configuration**:
   * enhanced networking を有効化
   * multiple network interfaces を設定
   * placement groups を指定
   *   Example:

       ```json
       {
         "NetworkInterfaces": [
           {
             "DeviceIndex": 0,
             "Groups": ["sg-12345"],
             "DeleteOnTermination": true
           }
         ]
       }
       ```
4. **Instance metadata options**:
   * IMDSv2 を必須化 (enhanced security)
   * hop limit を設定
   *   Example:

       ```json
       {
         "MetadataOptions": {
           "HttpTokens": "required",
           "HttpPutResponseHopLimit": 2
         }
       }
       ```
5. **User data scripts**:
   * instance startup 時に実行される scripts を提供
   * cluster join 前に custom configuration を実行
   *   Example:

       ```bash
       #!/bin/bash
       # User data script
       mkdir -p /opt/app
       mount -t tmpfs -o size=10G tmpfs /opt/app
       ```

**Creating and using Launch Templates:**

1. **Create Launch Template in AWS Management Console**:
   * EC2 Console > Launch Templates > Create launch template
   * AMI、instance type、key pair、security groups などを設定
   * storage、network interfaces、user data などの advanced settings を設定
2.  **Create node group based on launch template using eksctl**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig

    metadata:
      name: my-cluster
      region: us-west-2

    managedNodeGroups:
      - name: custom-ng
        launchTemplate:
          id: lt-12345abcdef
          version: "1"
    ```
3.  **Create node group based on launch template using AWS CLI**:

    ```bash
    aws eks create-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name custom-ng \
      --launch-template id=lt-12345abcdef,version=1 \
      --subnets subnet-12345 subnet-67890 \
      --node-role arn:aws:iam::123456789012:role/EKSNodeRole
    ```

**Problems with other options:**

* **Reduced cluster creation time**: launch templates を使用しても cluster creation time は短縮されません。実際には、additional configuration によって少し長くかかる場合があります。
* **Cluster control plane customization**: Launch templates は worker nodes にのみ適用されます。EKS control plane は AWS によって管理され、launch templates を通じてカスタマイズできません。
* **Automatically uses latest AMI version**: Launch templates は特定の AMI ID を指定するため、実際には AMI version を固定する効果があります。latest AMI を自動的に使用するには、launch templates を使用しないか、launch template を定期的に更新する必要があります。

Launch templates は EKS node groups の advanced customization が必要な場合に特に有用であり、standard configuration では満たせない special requirements がある場合に使用すべきです。

</details>

2. Amazon EKS clusters の cost optimization strategy ではないものはどれですか？
   * A) Spot instances の使用
   * B) Cluster Autoscaler の設定
   * C) すべての worker nodes に latest instance types を使用
   * D) Fargate profiles の selective use

<details>

<summary>答えを表示</summary>

**答え: C) すべての worker nodes に latest instance types を使用**

**解説:** すべての worker nodes に latest instance types を使用することは、必ずしも cost optimization strategy ではありません。latest instance types は多くの場合、より良い performance と features を提供しますが、常に cost-effective とは限りません。workload requirements に合った適切な instance types を選択することの方が重要です。

**Actual cost optimization strategies for EKS clusters:**

1. **Using Spot instances**:
   * On-Demand instances と比較して最大 90% の cost savings
   * interruptible workloads (batch jobs、dev/test environments など) に適している
   *   Configure Spot instances in managed node groups:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name spot-ng \
         --node-type m5.large \
         --nodes 2 \
         --nodes-min 1 \
         --nodes-max 5 \
         --spot
       ```
   *   Mix multiple instance types to improve availability:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: spot-ng
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
           spot: true
       ```
2. **Configuring Cluster Autoscaler**:
   * workload requirements に基づいて node count を自動調整
   * 未使用 nodes を自動的に削除することで cost savings
   *   Installation and configuration:

       ```bash
       # Install Cluster Autoscaler using Helm
       helm repo add autoscaler https://kubernetes.github.io/autoscaler

       helm install cluster-autoscaler autoscaler/cluster-autoscaler \
         --namespace kube-system \
         --set autoDiscovery.clusterName=my-cluster \
         --set awsRegion=us-west-2 \
         --set rbac.create=true
       ```
3. **Selective use of Fargate profiles**:
   * Serverless container execution environment により node management overhead を排除
   * 使用した resources に対してのみ支払い
   * intermittent workloads または dev/test environments に適している
   *   Use Fargate only for specific namespaces or labels:

       ```bash
       eksctl create fargateprofile \
         --cluster my-cluster \
         --name fp-dev \
         --namespace dev
       ```
4. **Selecting appropriate instance sizes**:
   * workload requirements に合った instance sizes を選択
   * over-provisioning を防止
   *   Monitor and analyze resource usage:

       ```bash
       kubectl top nodes
       kubectl top pods --all-namespaces
       ```
5. **Using Graviton (ARM) based instances**:
   * x86-based instances と比較して最大 40% の cost savings
   * equivalent performance を提供
   * Compatibility verification required
   *   Example:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name arm-ng \
         --node-type m6g.large \
         --nodes 2
       ```
6. **Utilizing Reserved Instances or Savings Plans**:
   * long-term commitments による cost savings
   * predictable workloads に適している
   * On-Demand と比較して最大 72% の cost savings
7. **Optimizing resource requests and limits**:
   * pod resource requests を適切に設定することで node utilization を向上
   * over-provisioning を防止
   *   Example:

       ```yaml
       resources:
         requests:
           cpu: 100m
           memory: 128Mi
         limits:
           cpu: 500m
           memory: 256Mi
       ```
8. **Cost monitoring and analysis**:
   * AWS Cost Explorer を使用
   * Kubernetes cost allocation tags を設定
   * third-party cost monitoring tools (Kubecost、CloudHealth など) を使用

**Problems with using the latest instance types:**

1. **Increased costs**:
   * Latest instance types は previous generations より高価な場合が多い
   * すべての workloads が latest instances の features を必要とするわけではない
2. **Over-provisioning**:
   * workload requirements を超える resources を提供
   * 不要な costs につながる
3. **Availability limitations**:
   * latest instance types はすべての regions または availability zones で利用できない場合がある
   * Spot instances を使用する場合は特に availability が制限される
4. **Compatibility issues**:
   * 一部の workloads は特定の instance types に最適化されている場合がある
   * new instance types へ移行する際には testing が必要

Cost optimization では、workload characteristics、resource requirements、availability requirements などを包括的に考慮し、適切な instance types と sizes を選択することが重要です。latest instance types が常に最も cost-effective な選択とは限らず、workload に適した instance types を選択することがより重要です。

</details>

3. Amazon EKS で private cluster を設定する正しい方法はどれですか？
   * A) nodes を private subnets のみに配置し public endpoint を無効化する
   * B) nodes を private subnets のみに配置し public endpoint を有効化する
   * C) nodes を public subnets に配置し public endpoint を無効化する
   * D) VPC endpoints なしで nodes を private subnets のみに配置する

<details>

<summary>答えを表示</summary>

**答え: A) nodes を private subnets のみに配置し public endpoint を無効化する**

**解説:** Amazon EKS で完全な private cluster を設定するには、nodes を private subnets のみに配置し、public endpoint を無効化する必要があります。これにより、cluster の Kubernetes API server が internet からアクセスできなくなり、すべての traffic が VPC 内でのみ発生します。

**Private EKS cluster configuration components:**

1. **Endpoint access configuration**:
   * public endpoint を無効化
   * private endpoint を有効化
   *   AWS CLI configuration example:

       ```bash
       aws eks update-cluster-config \
         --name my-cluster \
         --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
       ```
   *   eksctl configuration example:

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       vpc:
         clusterEndpoints:
           publicAccess: false
           privateAccess: true
       ```
2. **Node placement**:
   * nodes を private subnets のみに配置
   * public IP assignment なし
   *   Managed node group configuration example:

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name private-ng \
         --node-type m5.large \
         --nodes 3 \
         --node-private-networking \
         --subnet-ids subnet-private1,subnet-private2
       ```
3.  **VPC endpoint configuration**: private clusters が AWS services にアクセスするには VPC endpoints が必要です:

    * com.amazonaws.region.ecr.api
    * com.amazonaws.region.ecr.dkr
    * com.amazonaws.region.s3
    * com.amazonaws.region.logs (optional)
    * com.amazonaws.region.sts (optional)

    ```bash
    # Create ECR API endpoint
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.ecr.api \
      --vpc-endpoint-type Interface \
      --subnet-ids subnet-private1 subnet-private2 \
      --security-group-ids sg-12345 \
      --private-dns-enabled

    # Create ECR Docker endpoint
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.ecr.dkr \
      --vpc-endpoint-type Interface \
      --subnet-ids subnet-private1 subnet-private2 \
      --security-group-ids sg-12345 \
      --private-dns-enabled

    # Create S3 endpoint (Gateway type)
    aws ec2 create-vpc-endpoint \
      --vpc-id vpc-12345 \
      --service-name com.amazonaws.us-west-2.s3 \
      --vpc-endpoint-type Gateway \
      --route-table-ids rtb-12345
    ```
4. **Network configuration**:
   * private subnets では NAT Gateway または VPC endpoints が必要
   * security group rules による traffic restriction
   * Routing table configuration

**Methods to access private clusters:**

1. **Access via VPN or Direct Connect**:
   * AWS Client VPN
   * AWS Site-to-Site VPN
   * AWS Direct Connect
2.  **Access via Bastion Host**:

    * bastion host を public subnet に配置
    * bastion host から cluster API server にアクセス

    ```bash
    # Configure kubeconfig on bastion host
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
3. **Access via AWS Systems Manager Session Manager**:
   * internet gateway なしで EC2 instances にアクセス
   * IAM permissions and logging による access control

**Problems with other options:**

* **Place nodes only in private subnets and enable public endpoint**: public endpoint が有効な場合、cluster API server は internet からアクセス可能であるため、完全な private cluster ではありません。security groups または CIDR restrictions で access を制限できますが、それでも public networks に公開されています。
* **Place nodes in public subnets and disable public endpoint**: nodes が public subnets にある場合、internet から直接アクセスできる可能性があるため、完全な private cluster ではありません。security groups で access を制限できますが、nodes に public IPs が割り当てられる可能性があります。
* **Place nodes only in private subnets without VPC endpoints**: VPC endpoints なしで nodes を private subnets に配置すると、nodes は ECR、S3 などの AWS services にアクセスできません。この場合、NAT Gateway 経由の internet access が必要になり、完全な private cluster configuration ではありません。

Private EKS clusters は high security を必要とする environments に適しており、すべての cluster traffic が VPC 内でのみ発生することを確保します。ただし、configuration はより複雑で、cluster access のために追加 infrastructure (VPN、Direct Connect、bastion hosts など) が必要になる場合があります。

</details>

4. Amazon EKS clusters で有効な node group upgrade strategy ではないものはどれですか？
   * A) Rolling upgrade
   * B) Blue/Green deployment
   * C) In-place upgrade
   * D) Canary deployment

<details>

<summary>答えを表示</summary>

**答え: C) In-place upgrade**

**解説:** 「In-place upgrade」は Amazon EKS node groups の公式 upgrade strategy ではありません。EKS managed node groups は default で rolling upgrade approach を使用し、self-managed node groups では blue/green deployment や canary deployment などの strategies を実装できます。

**EKS node group upgrade strategies:**

1. **Rolling Upgrade**:
   * EKS managed node groups の default upgrade method
   * nodes を一度に 1 つずつ置き換えることで workload disruption を最小化
   * Process:
     1. new node を作成
     2. existing node に cordoning を適用 (new pod scheduling を防止)
     3. existing node から pods を drain (pods を移行)
     4. existing node を terminate
     5. next node で繰り返し
   *   Configuration example:

       ```bash
       # Managed node group upgrade
       aws eks update-nodegroup-version \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup

       # Check upgrade status
       aws eks describe-update \
         --name <update-id> \
         --nodegroup-name my-nodegroup \
         --cluster-name my-cluster
       ```
2. **Blue/Green Deployment**:
   * 完全に new node group を作成してから traffic を切り替える
   * rollback が簡単で risk が低い
   * resource usage が一時的に増加 (nodes が二重に稼働)
   * Implementation steps:
     1. new node group (green) を作成
     2. new node group に workloads をデプロイしてテスト
     3. traffic を new node group に切り替え
     4. existing node group (blue) を削除
   *   Configuration example:

       ```bash
       # Create new node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v2 \
         --node-type m5.large \
         --nodes 3 \
         --node-ami-family AmazonLinux2

       # Check node labels
       kubectl get nodes --show-labels

       # Delete existing node group
       eksctl delete nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v1
       ```
3. **Canary Deployment**:
   * まず一部の nodes のみを upgrade することで risk を最小化
   * 問題発生時の impact scope を限定
   * gradual rollout が可能
   * Implementation steps:
     1. small new node group を作成
     2. 一部の workloads を new node group に移動
     3. monitor and verify
     4. 問題がなければ残りの nodes を upgrade
   *   Configuration example:

       ```bash
       # Create canary node group (small scale)
       eksctl create nodegroup \
         --cluster my-cluster \
         --name canary-ng \
         --node-type m5.large \
         --nodes 1 \
         --node-labels "deployment=canary"

       # Deploy specific workloads to canary nodes
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: my-app
       spec:
         template:
           spec:
             nodeSelector:
               deployment: canary
       ```

**Problems with in-place upgrades:**

「in-place upgrade」という term は、既存の nodes を terminate せずに upgrade することを意味する場合があります。これは次の理由により EKS node groups には適していません:

1. **Violates immutable infrastructure principles**:
   * Cloud-native environments では、resources を変更するのではなく置き換えることが推奨されます。
   * node configuration drift を防止します。
2. **Risk of upgrade failure**:
   * in-place upgrade が失敗した場合、nodes が不安定になる可能性があります。
   * rollback が困難です。
3. **EKS node AMI structure**:
   * EKS optimized AMIs は version ごとに異なる AMI IDs を持ちます。
   * AMI は in-place upgrade では変更できません。
4. **Managed node group limitations**:
   * EKS managed node groups は in-place upgrades をサポートしていません。
   * 常に rolling upgrade method を使用します。

**Node group upgrade best practices:**

1.  **Configure PodDisruptionBudget**:

    * upgrades 中の application availability を確保します。

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```
2. **Ensure sufficient resources**:
   * node draining 中の pod relocation のために spare capacity が必要
   * Cluster Autoscaler configuration を考慮
3. **Test before upgrade**:
   * まず non-production environments で upgrades をテスト
   * application compatibility を確認
4. **Enhanced monitoring**:
   * upgrade 中および後に system を monitor
   * anomalies の早期検出

EKS node group upgrades は、workload disruption を最小限に抑えながら security patches、bug fixes、新機能を適用するための重要な tasks です。状況に応じて rolling upgrade、blue/green deployment、canary deployment などの strategies を選択し、安全に upgrades を実行してください。

</details>

5. Amazon EKS clusters の node bootstrap process 中に発生しないものはどれですか？
   * A) kubelet configuration and startup
   * B) Cluster control plane component installation
   * C) AWS IAM Authenticator configuration
   * D) Registering node with cluster

<details>

<summary>答えを表示</summary>

**答え: B) Cluster control plane component installation**

**解説:** Amazon EKS node bootstrap process 中に cluster control plane components はインストールされません。EKS は managed service であり、control plane (API server、controller manager、scheduler など) は AWS によって管理され、worker nodes とは別に実行されます。node bootstrap process 中には、node を既存の EKS cluster に接続するための configuration のみが実行されます。

**What actually occurs during EKS node bootstrap:**

1. **kubelet configuration and startup**:
   * kubelet configuration file (`/etc/kubernetes/kubelet/kubelet-config.json`) を作成
   * cluster endpoint、certificates、cluster DNS などを設定
   * kubelet service を開始
   *   Example configuration:

       ```json
       {
         "kind": "KubeletConfiguration",
         "apiVersion": "kubelet.config.k8s.io/v1beta1",
         "address": "0.0.0.0",
         "authentication": {
           "anonymous": {
             "enabled": false
           },
           "webhook": {
             "cacheTTL": "2m0s",
             "enabled": true
           },
           "x509": {
             "clientCAFile": "/etc/kubernetes/pki/ca.crt"
           }
         },
         "clusterDomain": "cluster.local",
         "clusterDNS": ["10.100.0.10"],
         "podCIDR": "",
         "maxPods": 58
       }
       ```
2. **AWS IAM Authenticator configuration**:
   * IAM authentication のために aws-iam-authenticator を設定
   * kubeconfig file を作成
   * node IAM role を設定
   *   Example configuration:

       ```yaml
       apiVersion: v1
       kind: Config
       clusters:
       - cluster:
           certificate-authority: /etc/kubernetes/pki/ca.crt
           server: https://my-cluster.eks.amazonaws.com
         name: kubernetes
       contexts:
       - context:
           cluster: kubernetes
           user: kubelet
         name: kubelet
       current-context: kubelet
       users:
       - name: kubelet
         user:
           exec:
             apiVersion: client.authentication.k8s.io/v1beta1
             command: aws-iam-authenticator
             args:
               - token
               - -i
               - my-cluster
               - --role
               - arn:aws:iam::123456789012:role/EKSNodeRole
       ```
3. **Registering node with cluster**:
   * node object を作成
   * node labels and taints を設定
   * cluster API server に登録
   *   Example log:

       ```
       Node my-node-1 successfully registered with API server
       ```
4. **CNI plugin configuration**:
   * Amazon VPC CNI plugin を設定
   * pod networking を setup
   * IP address allocation を設定
   *   Example configuration:

       ```json
       {
         "cniVersion": "0.3.1",
         "name": "aws-vpc",
         "plugins": [
           {
             "name": "aws-vpc",
             "type": "vpc-cni",
             "vethPrefix": "eni",
             "mtu": "9001",
             "ipam": {
               "type": "aws-cni"
             }
           }
         ]
       }
       ```
5. **kube-proxy setup**:
   * cluster networking のために kube-proxy を設定
   * service IP routing を setup
   *   Example configuration:

       ```yaml
       apiVersion: kubeproxy.config.k8s.io/v1alpha1
       kind: KubeProxyConfiguration
       bindAddress: 0.0.0.0
       clientConnection:
         acceptContentTypes: ""
         burst: 10
         contentType: application/vnd.kubernetes.protobuf
         kubeconfig: /var/lib/kube-proxy/kubeconfig
         qps: 5
       ```
6. **Node labels and taints application**:
   * instance type、availability zone などに基づいて labels を設定
   * custom labels を適用
   * 必要に応じて taints を適用
   *   Example commands:

       ```bash
       kubectl label node my-node-1 eks.amazonaws.com/nodegroup=my-nodegroup
       kubectl label node my-node-1 topology.kubernetes.io/zone=us-west-2a
       ```

**Bootstrap script:**

EKS node bootstrapping は `/etc/eks/bootstrap.sh` script を通じて実行されます。この script は次の parameters を受け取ることができます:

```bash
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker' \
  --b64-cluster-ca <base64-encoded-ca> \
  --apiserver-endpoint <api-server-endpoint> \
  --dns-cluster-ip 10.100.0.10
```

custom launch template を使用する場合、user data section でこの script を呼び出して additional configuration を実行できます:

```bash
#!/bin/bash
set -ex
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=environment=prod,node-type=worker' \
  --max-pods 110
```

**Cluster control plane components:**

EKS cluster control plane components は AWS によって管理され、node bootstrap process とは別です:

* API server
* Controller manager
* Scheduler
* etcd
* CoreDNS

これらの components は AWS-managed infrastructure 上で実行され、high availability と scalability を確保します。Nodes はこれらの control plane components に接続するだけで、直接インストールまたは管理することはありません。

したがって、Amazon EKS node bootstrap 中に発生しないものは「cluster control plane component installation」です。

</details>
