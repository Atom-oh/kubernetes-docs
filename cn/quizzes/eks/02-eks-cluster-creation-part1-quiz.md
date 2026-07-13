# EKS Cluster 创建测验 - 第 1 部分

本测验测试你对 Amazon EKS cluster 创建相关概念、工具和最佳实践的理解。内容涵盖 cluster 创建方法、VPC 配置以及 node group 设置等主题。

## 基础概念问题

1. 以下哪一项不是可用于创建 Amazon EKS cluster 的工具？
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>显示答案</summary>

**答案：D) kubectl**

**解释：** kubectl 是用于管理 Kubernetes cluster 的命令行工具，但不能用于创建 EKS cluster。kubectl 用于连接到现有 Kubernetes cluster 以管理资源。

可用于创建 Amazon EKS cluster 的工具包括：

1. **AWS Management Console**:
   * 通过 Web 界面创建 EKS cluster。
   * 适合初学者，因为它允许以可视化方式配置 cluster 组件。
   * 通过分步向导引导完成 cluster 创建过程。
2.  **AWS CLI**:

    * 从命令行创建 EKS cluster。
    * 使用 `aws eks create-cluster` 命令。
    * 适合脚本和自动化。

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**:

    * 专为 EKS cluster 创建而设计的命令行工具。
    * 由 Weaveworks 开发的开源工具，可简化 EKS cluster 创建和管理。
    * 可以使用单个命令创建 cluster。

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **Infrastructure as Code (IaC) tools**:

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    这些工具允许以代码形式定义和部署 EKS cluster。

kubectl 在 cluster 创建后用于管理 Kubernetes resources（Pod、Service、Deployment 等）。要连接到 EKS cluster，必须先使用 `aws eks update-kubeconfig` 命令更新 kubectl 配置。

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

之后，你可以使用 kubectl 管理 cluster resources。

</details>

2. 创建 Amazon EKS cluster 时必须指定哪个 VPC 组件？
   * A) 仅 public subnets
   * B) 仅 private subnets
   * C) 跨至少 2 个 availability zones 的 subnets
   * D) NAT Gateway

<details>

<summary>显示答案</summary>

**答案：C) 跨至少 2 个 availability zones 的 subnets**

**解释：** 创建 Amazon EKS cluster 时，必须指定的 VPC 组件是跨至少 2 个 availability zones 的 subnets。这是 AWS 的要求，用于确保 EKS cluster 的高可用性。

**EKS cluster VPC 要求：**

1. **至少 2 个 availability zones (AZs) 中需要 subnets**:
   * 由于 EKS control plane 部署在多个 availability zones 中，因此创建 cluster 时必须在至少 2 个 availability zones 中指定 subnets。
   * 这确保即使单个 availability zone 发生故障，cluster 仍可继续运行。
2. **Subnet 类型**:
   * 可以仅使用 public subnets、仅使用 private subnets，或混合使用 public 和 private subnets。
   * 对于生产环境，建议出于安全考虑将 worker nodes 放在 private subnets 中，并将 public subnets 用于 load balancers。
3. **Subnet CIDR 大小**:
   * 每个 subnet 必须有足够的 IP addresses。
   * 由于 EKS 会为每个 pod 分配 VPC IP address，因此需要根据预期的 pod 数量准备足够大的 CIDR blocks。
4. **Tag 要求**:
   * EKS 需要特定 tags 来识别并正确使用 subnets：
     * Shared subnets: `kubernetes.io/cluster/<cluster-name>: shared`
     * Public subnets: `kubernetes.io/role/elb: 1`
     * Private subnets: `kubernetes.io/role/internal-elb: 1`

**VPC 配置示例（使用 eksctl）：**

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

**使用 AWS CLI 的 VPC 配置：**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

当 private subnets 中的 worker nodes 需要访问互联网时，需要 NAT Gateway，但它不是 EKS cluster 创建本身的必需组件。如果仅使用 public subnets，可以在没有 NAT Gateway 的情况下创建 cluster（不建议用于生产环境）。

</details>

3. 创建 Amazon EKS cluster 时需要哪些 IAM roles？
   * A) 仅 EKS service role
   * B) 仅 Node instance role
   * C) EKS service role 和 node instance role
   * D) Fargate execution role

<details>

<summary>显示答案</summary>

**答案：C) EKS service role 和 node instance role**

**解释：** 要创建和运行 Amazon EKS cluster，需要两个主要 IAM roles：EKS service role 和 node instance role。这两个 roles 用途不同，并且都是 cluster 正常运行所必需的。

**1. EKS Service Role (EKS Cluster Role):**

* **用途**：允许 AWS EKS service 代表用户调用其他 AWS services。
* **所需权限**:
  * 访问 EC2、ELB、CloudWatch、KMS 等 AWS services
  * VPC resource 管理
  * Log group 创建和管理
* **Managed policy**: `AmazonEKSClusterPolicy`
*   **创建方法**:

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

* **用途**：允许 EKS worker nodes（EC2 instances）与 AWS services 交互。
* **所需权限**:
  * 从 ECR 拉取 container images
  * 将 logs 写入 CloudWatch
  * 管理 EBS/EFS volumes
  * Load balancer 注册/注销
* **Managed policies**:
  * `AmazonEKSWorkerNodePolicy`
  * `AmazonEC2ContainerRegistryReadOnly`
  * `AmazonEKS_CNI_Policy`
*   **创建方法**:

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

**使用 eksctl 自动创建 role：**

使用 eksctl 创建 cluster 时，可以自动创建所需的 IAM roles：

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

**其他 roles（可选）：**

* **Fargate execution role**：仅在使用 Fargate profiles 时需要。
* **Service account IAM roles**：使用 IRSA (IAM Roles for Service Accounts) 时需要。
* **ALB controller role**：使用 AWS Load Balancer Controller 时需要。

Fargate execution role 仅在使用 Fargate profiles 时需要，并不是基本 EKS cluster 创建的必需项。因此，创建 EKS cluster 所需的 IAM roles 是 EKS service role 和 node instance role。

</details>

4. 使用 eksctl 创建 EKS cluster 的正确命令是什么？
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>显示答案</summary>

**答案：B) `eksctl create cluster --name my-cluster --region us-west-2`**

**解释：** 使用 eksctl 创建 EKS cluster 的正确命令是 `eksctl create cluster --name my-cluster --region us-west-2`。该命令会在指定名称和 region 中使用默认设置创建 EKS cluster。

**eksctl 命令结构：**

* `eksctl`：基础命令
* `create`：创建 resource 的操作
* `cluster`：要创建的 resource 类型（cluster）
* `--name my-cluster`：指定 cluster 名称
* `--region us-west-2`：指定 AWS region

**基础 cluster 创建命令：**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

该命令会使用以下默认设置创建 cluster：

* 2 个 m5.large nodes
* 创建新的 VPC
* 默认 Amazon Linux 2 AMI
* Managed node groups
* 自动创建所需的 IAM roles

**带附加选项的高级命令：**

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

**使用配置文件创建 cluster：**

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

**其他选项的问题：**

* `eksctl create-cluster`：命令格式不正确。eksctl 使用空格而不是连字符 (-) 来分隔命令。
* `eksctl new cluster`：'new' 不是有效的 eksctl 命令。
* `eksctl start cluster`：'start' 不是有效的 eksctl 命令。启动现有 cluster 的概念不适用于 EKS。

eksctl 提供了用于 EKS cluster 管理的多种命令：

* `eksctl create cluster`：创建新的 cluster
* `eksctl get cluster`：列出 clusters
* `eksctl update cluster`：更新 cluster
* `eksctl delete cluster`：删除 cluster
* `eksctl create nodegroup`：添加 node group
* `eksctl scale nodegroup`：扩缩 node group

</details>

5. 关于创建 Amazon EKS cluster 时可指定的 Kubernetes 版本，哪项是正确的？
   * A) 仅支持最新版本
   * B) 仅支持最新版本和前 2 个版本
   * C) AWS 支持的所有 Kubernetes 版本
   * D) 所有 Kubernetes 版本

<details>

<summary>显示答案</summary>

**答案：C) AWS 支持的所有 Kubernetes 版本**

**解释：** 创建 Amazon EKS cluster 时，可以从 AWS 当前支持的 Kubernetes 版本中进行选择。AWS 通常会同时支持多个 Kubernetes 版本，包括最新版本和多个先前版本。

**EKS Kubernetes 版本支持策略：**

1. **支持周期**:
   * 每个 Kubernetes 版本在 EKS 发布后支持 14 个月。
   * 支持结束日期会至少提前 60 天公布。
2. **支持的版本**:
   * 通常，EKS 会同时支持 3-4 个 Kubernetes 版本。
   * 新版本通常在 Kubernetes 社区发布后的几个月内在 EKS 上可用。
3.  **如何检查版本**:

    ```bash
    # Check supported versions using AWS CLI
    aws eks describe-addon-versions | grep kubernetesVersion | sort -u

    # Or
    aws eks get-cluster-version-list
    ```
4.  **版本指定示例**:

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
5.  **版本升级**:

    * cluster 创建后，可以升级到受支持的版本。
    * 通常建议一次只升级一个 minor version。

    ```bash
    # Cluster version upgrade
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.28
    ```

**选择版本时的注意事项：**

1. **稳定性**:
   * 最新版本提供新功能，但可能存在早期 bug。
   * 对于重视稳定性的生产环境，选择经过验证的先前版本可能更好。
2. **功能需求**:
   * 如果需要特定 Kubernetes features，必须选择支持这些 features 的最低版本。
3. **支持周期**:
   * 对于长期支持，选择最近发布的版本以最大化支持周期。
4. **生态系统兼容性**:
   * 确保正在使用的 tools、add-ons 和 operators 与所选 Kubernetes 版本兼容。

其他选项的问题：

* 并非只支持最新版本；多个版本会被同时支持。
* 支持版本数量并不固定为“最新版本和前 2 个版本”，而是会根据 AWS 的支持策略变化。
* 并非支持所有 Kubernetes 版本；只能使用 AWS 测试并支持的版本。

</details>

6. 以下哪一项不是在 Amazon EKS cluster 中创建 node group 的选项？
   * A) Managed node groups
   * B) Self-managed node groups
   * C) Fargate profiles
   * D) Serverless node groups

<details>

<summary>显示答案</summary>

**答案：D) Serverless node groups**

**解释：** “Serverless node groups” 不是 Amazon EKS 中存在的概念。在 EKS 中运行 workloads 的三个主要选项是 managed node groups、self-managed node groups 和 Fargate profiles。

**1. Managed Node Groups:**

* **功能**:
  * AWS 管理 node provisioning 和生命周期
  * 自动创建并注册 EC2 instance
  * 自动配置 ASG (Auto Scaling Group)
  * 自动升级 Kubernetes 版本
  * 自动替换损坏的 nodes
  * 自动更新 node AMI
*   **创建方法**:

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

* **功能**:
  * 用户管理 node provisioning 和生命周期
  * 更多自定义选项
  * 可以使用 custom AMIs 或 bootstrap scripts
  * 适合特定 instance types 或配置需求
*   **创建方法**:

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

* **功能**:
  * Serverless container execution environment
  * 无需 node 管理
  * 按 Pod 分配资源和计费
  * 基于特定 namespaces 和 labels 选择性运行
*   **创建方法**:

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

**各选项比较：**

| 特性                | Managed Node Groups | Self-managed Node Groups | Fargate Profiles             |
| ------------------- | ------------------- | ------------------------ | ---------------------------- |
| 管理开销            | Low                 | High                     | None                         |
| 自定义能力          | Medium              | High                     | Low                          |
| 成本效率            | Medium              | High (when optimized)    | Low (paying for convenience) |
| 可扩展性            | Automatic           | Manual/Automatic         | Automatic                    |
| 使用场景            | General workloads   | Special requirements     | Variable workloads, dev/test |

“serverless node groups” 这个术语并不存在官方概念。Fargate 提供 serverless container execution environment，但它配置为 “Fargate profiles”，而不是 “node groups”。使用 Fargate 时，不需要直接管理 nodes，只会为 Pod 执行所需的 compute resources 进行 provisioning。

</details>

7. 以下哪一项不是 Amazon EKS clusters 中支持的 node AMI type？
   * A) Amazon Linux 2
   * B) Amazon Linux 2023
   * C) Bottlerocket
   * D) Ubuntu Core

<details>

<summary>显示答案</summary>

**答案：D) Ubuntu Core**

**解释：** Ubuntu Core 不是 Amazon EKS 官方支持的 node AMI type。EKS 中官方支持的 node AMI types 是 Amazon Linux 2、Amazon Linux 2023 和 Bottlerocket。

**EKS 中支持的 node AMI types：**

1.  **Amazon Linux 2 (AL2)**:

    * AWS 提供的默认 Linux distribution
    * 可作为 EKS optimized AMI 使用
    * 推荐用于大多数 EKS workloads
    * 长期支持和安全更新

    ```bash
    # Create Amazon Linux 2 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2-nodes \
      --node-ami-family AmazonLinux2
    ```
2.  **Amazon Linux 2023 (AL2023)**:

    * Amazon Linux 的最新版本
    * 增强的安全性和性能
    * 最新 kernel 和 software packages
    * 可作为 EKS optimized AMI 使用

    ```bash
    # Create Amazon Linux 2023 based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name al2023-nodes \
      --node-ami-family AmazonLinux2023
    ```
3.  **Bottlerocket**:

    * 针对 container workloads 优化的开源 Linux-based OS
    * 最小化 attack surface
    * 基于事务的更新
    * 以 container 为中心的设计

    ```bash
    # Create Bottlerocket based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name bottlerocket-nodes \
      --node-ami-family Bottlerocket
    ```

**其他支持的 AMI 选项：**

1.  **Windows**:

    * 基于 Windows Server 2019、2022 的 AMIs
    * 可以运行 Windows container workloads

    ```bash
    # Create Windows based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-nodes \
      --node-ami-family WindowsServer2022FullContainer
    ```
2.  **Custom AMIs**:

    * 可以使用 custom AMIs 满足特定需求
    * 主要与 self-managed node groups 一起使用

    ```bash
    # Create custom AMI based node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-nodes \
      --node-ami ami-1234567890abcdef0
    ```

**如何在 EKS 中使用 Ubuntu：**

Ubuntu Core 不受官方支持，但可以使用标准 Ubuntu Server AMIs 创建 self-managed node groups。在这种情况下，需要额外配置：

1. 选择 Ubuntu Server AMI
2. 安装必要的 Kubernetes components
3. 使用 bootstrap script 将 nodes 连接到 cluster

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

**选择 AMI 时的注意事项：**

* **安全性**：定期安全更新和补丁
* **性能**：针对 workload 优化的 kernel 和配置
* **兼容性**：与 Kubernetes 版本的兼容性
* **管理便捷性**：更新和维护流程
* **特殊需求**：GPU 支持、kernel modules 等

Ubuntu Core 是用于 IoT 和 edge devices 的轻量级 operating system，并未官方支持或优化用于 EKS nodes。因此，Ubuntu Core 不是 EKS clusters 中支持的 node AMI type。

</details>

8. 关于 Amazon EKS clusters 的 endpoint access 配置，哪项是正确的？
   * A) 默认情况下，仅启用 public endpoint
   * B) 默认情况下，仅启用 private endpoint
   * C) 默认情况下，同时启用 public 和 private endpoints
   * D) cluster 创建后无法更改 endpoint access

<details>

<summary>显示答案</summary>

**答案：A) 默认情况下，仅启用 public endpoint**

**解释：** 创建 Amazon EKS cluster 时，默认情况下仅启用 public endpoint，private endpoint 被禁用。该配置可以在 cluster 创建后更改，并且可以根据安全需求选择多种 endpoint access 配置。

**EKS cluster endpoint access 选项：**

1.  **仅启用 public endpoint（默认设置）**:

    * Cluster API server 可通过互联网访问
    * 可通过 security groups 限制访问
    * 适合开发或测试环境

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=false
    ```
2.  **同时启用 public 和 private endpoints**:

    * 可从 VPC 内通过 private IP 访问
    * 也可通过互联网访问
    * 适合混合环境

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true
    ```
3.  **仅启用 private endpoint**:

    * Cluster API server 只能从 VPC 内访问
    * 无法通过互联网访问
    * 提供最高级别的安全性
    * 推荐用于生产环境

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
    ```
4.  **限制 public access**:

    * 仅允许来自特定 CIDR blocks 的 public endpoint access
    * 只允许来自公司网络或 VPN 的访问

    ```bash
    # Configuration using AWS CLI
    aws eks update-cluster-config \
      --name my-cluster \
      --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]
    ```

**使用 eksctl 创建 cluster 时的 endpoint 配置：**

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

**更改 endpoint access 配置：**

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

**配置 endpoint access 时的注意事项：**

1. **安全需求**:
   * 仅使用 private endpoint 提供最高级别的安全性
   * 需要 public access 时应用 CIDR 限制
2. **网络连接**:
   * 仅使用 private endpoint 时，只能从 VPC 内部或通过 VPN/Direct Connect 访问
   * 同时启用两个 endpoints 在混合办公环境中可能很有用
3. **运维需求**:
   * 考虑 CI/CD pipelines、external tools 等是否需要 cluster access
4. **成本**:
   * endpoint 配置本身没有额外成本
   * 仅使用 private endpoint 时需考虑 VPN 或 Direct Connect 成本

其他选项的问题：

* 默认情况下仅启用 public endpoint，而不是 private endpoint。
* 默认情况下并不会同时启用 public 和 private endpoints；只启用 public endpoint。
* endpoint access 可以在 cluster 创建后更改。

</details>

9. 以下哪一项不是在 Amazon EKS clusters 中为 node groups 选择 instance types 时的考虑因素？
   * A) Workload 要求（CPU、memory、storage）
   * B) 成本优化
   * C) availability zones 的数量
   * D) Instance generation（例如 t3 vs t2）

<details>

<summary>显示答案</summary>

**答案：C) availability zones 的数量**

**解释：** availability zones 的数量不是为 node groups 选择 instance types 时的直接考虑因素。availability zones 与 node groups 部署位置相关，与 instance types 本身的选择相互独立。选择 instance types 时应考虑 workload 要求、成本优化、instance generation 等因素。

**选择 node group instance types 时的实际考虑因素：**

1. **Workload 要求（CPU、memory、storage）**:
   * 选择与 application resource 要求匹配的 instance types
   * Memory-intensive workloads：memory optimized instances，例如 r5、r6g
   * Compute-intensive workloads：compute optimized instances，例如 c5、c6g
   * Balanced workloads：general purpose instances，例如 m5、m6g
   * GPU workloads：accelerated computing instances，例如 p3、g4dn
2. **成本优化**:
   * On-demand vs Spot instances
   * Reserved Instances 或 Savings Plans
   * 合适大小的 instance 选择（避免过度 provisioning）
   * 通过基于 ARM 的 Graviton instances（例如 m6g、c6g）节省成本
3. **Instance generation**:
   * 最新一代 instances 通常提供更好的性能和成本效率
   * 示例：t3 相比 t2 提供更好的性能和性价比
   * 最新一代提供 enhanced networking、storage performance 等
4. **网络需求**:
   * Enhanced networking 支持（ENA、EFA 等）
   * Network bandwidth 要求
   * 与每个 instance 最大 pods 数相关的 networking limits
5. **Storage 需求**:
   * 是否需要本地 instance storage（例如 i3、d3 instances）
   * EBS optimization 支持
   * Storage throughput 和 IOPS 要求
6. **CPU 架构**:
   * x86 (Intel, AMD) vs ARM (AWS Graviton)
   * Application compatibility 注意事项

**availability zones 和 node group 部署：**

availability zones 的数量与 node group 部署策略相关，而不是 instance type 选择：

* 为实现高可用，将 node groups 部署到多个 availability zones
* 在每个 availability zone 中均匀分布 nodes
* 可以选择 region 中的所有 availability zones 或特定 availability zones

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

**Instance type 选择示例：**

1. **Web application servers**:
   * General purpose instances：t3.medium、m5.large
   * 以均衡性能实现成本效益
2. **Databases**:
   * Memory optimized instances：r5.xlarge、r6g.xlarge
   * 高 memory-to-CPU 比例
3. **Batch processing jobs**:
   * Compute optimized instances：c5.xlarge、c6g.xlarge
   * 高 CPU 性能
4. **Machine learning workloads**:
   * GPU instances：p3.2xlarge、g4dn.xlarge
   * Accelerated computing 能力

Instance type 选择应由 workload 特征、成本约束、性能要求等决定，availability zones 的数量与 node group 部署策略相关，而不是与 instance types 本身的选择相关。

</details>

10. 创建 Amazon EKS cluster 后配置 kubectl 的正确命令是什么？
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>显示答案</summary>

**答案：A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**解释：** 创建 Amazon EKS cluster 后配置 kubectl 的正确命令是 `aws eks update-kubeconfig --name my-cluster --region us-west-2`。该命令使用 AWS CLI 的 EKS module 为指定 cluster 更新 kubeconfig 文件。

**kubectl 配置过程：**

1. **更新 kubeconfig 文件**:
   * kubeconfig 文件存储 kubectl 与 Kubernetes clusters 通信所需的配置信息。
   * 默认情况下，它存储在 `~/.kube/config`。
   * `aws eks update-kubeconfig` 命令会自动更新此文件。
2. **命令组成部分**:
   * `--name`：EKS cluster 名称
   * `--region`：cluster 所在的 AWS region
   * `--kubeconfig`（可选）：自定义 kubeconfig 文件路径
   * `--role-arn`（可选）：用于 cluster access 的 IAM role
3.  **完整命令示例**:

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
4.  **附加选项**:

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig ~/.kube/eks-config

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias
    ```
5.  **验证配置**:

    ```bash
    # Check current context
    kubectl config current-context

    # List all contexts
    kubectl config get-contexts

    # Test cluster connection
    kubectl cluster-info
    ```

**其他选项的问题：**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`：此命令不存在。AWS CLI 中没有 `get-kubeconfig` subcommand。
* `kubectl config set-cluster my-cluster --region us-west-2`：此命令语法不正确。`kubectl config set-cluster` 不支持 `--region` flag，也不会自动配置 EKS clusters 所需的 authentication information。
* `eksctl configure kubectl --name my-cluster --region us-west-2`：此命令不存在。eksctl 没有 `configure kubectl` subcommand。使用 eksctl 创建 cluster 时，kubeconfig 会自动配置；但对于现有 clusters，必须使用 `aws eks update-kubeconfig` 命令。

**使用 eksctl 创建和配置 cluster：**

使用 eksctl 创建 cluster 时，kubeconfig 会自动更新：

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

该命令会创建 cluster 并自动更新 kubeconfig。但是，要连接到现有 cluster 或由其他工具创建的 cluster，必须使用 `aws eks update-kubeconfig` 命令。

**管理多个 clusters：**

管理多个 EKS clusters 时，可以通过为每个 cluster 运行 `aws eks update-kubeconfig` 命令，将它们添加到 kubeconfig 文件中：

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1

# Switch context
kubectl config use-context arn:aws:eks:us-west-2:123456789012:cluster/cluster1
```

因此，创建 Amazon EKS cluster 后配置 kubectl 的正确命令是 `aws eks update-kubeconfig --name my-cluster --region us-west-2`。

</details>

## 动手练习

### 练习 1：使用 eksctl 创建 EKS Cluster

**场景：** 你是公司的一名 DevOps engineer，需要为开发团队创建 Amazon EKS cluster。该 cluster 应兼具成本效益和可扩展性，并具备基本安全设置。

**要求：**

1. 使用 eksctl 创建 EKS cluster
2. 跨 2 个 availability zones 部署
3. 使用 t3.medium instance type
4. 配置 auto-scaling（最少 2 个、最多 5 个 nodes）
5. 同时启用 private 和 public endpoints

**解决方案：**

<details>

<summary>显示答案</summary>

**1. 安装 eksctl（如果尚未安装）**

```bash
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version
```

**2. 创建 cluster 配置文件**

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

**3. 创建 cluster**

```bash
eksctl create cluster -f eks-cluster.yaml
```

该命令执行以下任务：

* 创建 CloudFormation stacks
* 创建 VPC 和 subnets
* 配置 security groups
* 创建 EKS cluster
* 创建 managed node groups
* Bootstrap nodes 并连接到 cluster
* 配置 kubeconfig

**4. 验证 cluster**

```bash
# Check cluster status
eksctl get cluster --name dev-cluster --region us-west-2

# Check nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

**5. 配置 cluster access**

```bash
# Verify kubeconfig
kubectl config current-context

# Check cluster information
kubectl cluster-info
```

**6. 验证基本安全设置**

```bash
# Check namespaces
kubectl get namespaces

# Check RBAC settings
kubectl get clusterroles
kubectl get clusterrolebindings
```

**7. 监控 cluster resources**

```bash
# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods --all-namespaces
```

通过本练习，你学习了如何使用 eksctl 创建兼具成本效益和可扩展性的 EKS cluster。t3.medium instances 是一种具有成本效益的选择，auto-scaling 配置允许根据 workload 自动调整 node 数量。同时启用 private 和 public endpoints，可允许从内部和外部访问 cluster。

</details>

### 练习 2：使用 AWS Management Console 创建 EKS Cluster

**场景：** 你需要使用 AWS Management Console 创建并配置 EKS cluster。该 cluster 用于生产环境，安全性和高可用性非常重要。

**要求：**

1. 使用 AWS Management Console 创建 EKS cluster
2. 将 nodes 放在 private subnets 中
3. 限制对 cluster endpoint 的 public access
4. 配置 managed node groups
5. 创建所需 IAM roles

**解决方案：**

<details>

<summary>显示答案</summary>

**1. 创建所需 IAM roles**

**创建 EKS cluster role：**

1. 登录 AWS Management Console 并导航到 IAM service。
2. 在左侧菜单中选择 “Roles”，然后单击 “Create role”。
3. 选择 “AWS service” 作为 trusted entity type。
4. 在 use case 下，选择 “EKS”，然后选择 “EKS - Cluster”。
5. 单击 “Next”。
6. 验证 `AmazonEKSClusterPolicy` 已自动选中。
7. 单击 “Next”。
8. 输入 “EKSClusterRole” 作为 role name，然后单击 “Create role”。

**创建 EKS node role：**

1. 在 IAM service 中再次单击 “Create role”。
2. 选择 “AWS service” 作为 trusted entity type。
3. 在 use case 下选择 “EC2”。
4. 单击 “Next”。
5. 搜索并选择以下 policies：
   * `AmazonEKSWorkerNodePolicy`
   * `AmazonEC2ContainerRegistryReadOnly`
   * `AmazonEKS_CNI_Policy`
6. 单击 “Next”。
7. 输入 “EKSNodeRole” 作为 role name，然后单击 “Create role”。

**2. 准备 VPC 和 subnets**

生产环境需要适当的 VPC 配置。你可以使用 AWS CloudFormation template 创建 EKS-optimized VPC：

1. 导航到 CloudFormation console。
2. 选择 “Create stack” > “With new resources (standard)”。
3.  在 Amazon S3 URL 中输入以下地址：

    ```
    https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
    ```
4. 单击 “Next”。
5. 输入 “eks-vpc” 作为 stack name。
6. 保留默认参数并单击 “Next”。
7. 在下一页保留默认选项并单击 “Next”。
8. 单击 “Create stack”。
9. stack 创建完成后，从 “Outputs” 选项卡记录以下值：
   * VpcId
   * SubnetIds
   * SecurityGroups

**3. 创建 EKS cluster**

1. 在 AWS Management Console 中导航到 EKS service。
2. 单击 “Create cluster”。
3. 在 “Cluster configuration” 页面：
   * Cluster name: “prod-cluster”
   * Kubernetes version: 选择最新版本（例如 1.28）
   * Cluster service role: 选择之前创建的 “EKSClusterRole”
   * 单击 “Next”。
4. 在 “Specify networking” 页面：
   * VPC: 选择之前创建的 VPC
   * Subnets: 仅选择 private subnets（取消选择 public subnets）
   * Security groups: 选择 default security group
   * Cluster endpoint access:
     * 选择 “Private” 或
     * 选择 “Public and Private” 并将 CIDR blocks 限制为公司 IP 范围
   * 单击 “Next”。
5. 在 “Configure logging” 页面：
   * 选择所需 log types（API server、Audit、Authenticator、Controller manager、Scheduler）
   * 单击 “Next”。
6. 在 “Select add-ons” 页面：
   * 保留默认 add-ons（kube-proxy、CoreDNS、VPC CNI）
   * 单击 “Next”。
7. 在 review 页面检查所有设置，然后单击 “Create”。
8. 等待 cluster 创建完成（约 15-20 分钟）。

**4. 创建 managed node group**

1. cluster 创建完成后，单击 cluster 名称。
2. 转到 “Compute” 选项卡并单击 “Add node group”。
3. 在 “Node group configuration” 页面：
   * Name: “prod-nodes”
   * Node IAM role: 选择之前创建的 “EKSNodeRole”
   * 单击 “Next”。
4. 在 “Set compute and scaling configuration” 页面：
   * AMI type: Amazon Linux 2 (x86)
   * Instance type: 选择 m5.large
   * Disk size: 50 GiB
   * Node group scaling configuration:
     * Minimum size: 2
     * Maximum size: 5
     * Desired size: 3
   * 单击 “Next”。
5. 在 “Specify networking” 页面：
   * Subnets: 仅选择 private subnets
   * 单击 “Next”。
6. 在 “Review and create” 页面检查所有设置，然后单击 “Create”。
7. 等待 node group 创建完成（约 5 分钟）。

**5. 配置 kubectl 并访问 cluster**

1. 验证 AWS CLI 已安装。
2.  运行以下命令更新 kubectl 配置文件：

    ```bash
    aws eks update-kubeconfig --name prod-cluster --region us-west-2
    ```
3.  验证 cluster 连接：

    ```bash
    kubectl get nodes
    kubectl cluster-info
    ```

**6. 增强基本安全性**

1.  查看并限制 AWS security group rules：

    ```bash
    # Check cluster information for current context
    kubectl config view --minify
    ```
2.  应用 network policies（可选）：

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

通过本练习，你学习了如何使用 AWS Management Console 创建具有适合生产环境的安全性和高可用性设置的 EKS cluster。通过将 nodes 放在 private subnets 中并限制对 cluster endpoint 的 public access 增强了安全性，并通过使用 managed node groups 简化了 node 管理。

</details>

## 高级主题

以下是与 Amazon EKS cluster 创建相关的高级主题问题。本节测试你对 EKS cluster 创建高级概念和最佳实践的理解。

1. 在 Amazon EKS clusters 中使用 custom Launch Templates 的主要好处是什么？
   * A) 缩短 cluster 创建时间
   * B) 可自定义 node bootstrap scripts 和 additional volume configuration
   * C) Cluster control plane 自定义
   * D) 自动使用最新 AMI version

<details>

<summary>显示答案</summary>

**答案：B) 可自定义 node bootstrap scripts 和 additional volume configuration**

**解释：** 在 Amazon EKS clusters 中使用 custom Launch Templates 的主要好处是能够自定义 node bootstrap scripts 并配置 additional volumes。Launch templates 允许对 EC2 instances 的各个方面进行细粒度控制，从而实现默认 node group 创建选项无法提供的高级配置。

**Launch Templates 可自定义的项目：**

1. **Custom bootstrap scripts**:
   * 定义在 nodes 加入 cluster 之前运行的 custom scripts
   * 安装和配置 additional software
   * 调整 system settings（kernel parameters、network settings 等）
   *   示例：

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
   * 自定义 root volume size、type、IOPS
   * 附加用于 data、logs、temporary storage 的 additional EBS volumes
   * 配置 instance store volumes
   *   示例：

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
   * 启用 enhanced networking
   * 配置多个 network interfaces
   * 指定 placement groups
   *   示例：

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
   * 要求 IMDSv2（增强安全性）
   * 设置 hop limit
   *   示例：

       ```json
       {
         "MetadataOptions": {
           "HttpTokens": "required",
           "HttpPutResponseHopLimit": 2
         }
       }
       ```
5. **User data scripts**:
   * 提供在 instance 启动时运行的 scripts
   * 在加入 cluster 前执行自定义配置
   *   示例：

       ```bash
       #!/bin/bash
       # User data script
       mkdir -p /opt/app
       mount -t tmpfs -o size=10G tmpfs /opt/app
       ```

**创建和使用 Launch Templates：**

1. **在 AWS Management Console 中创建 Launch Template**:
   * EC2 Console > Launch Templates > Create launch template
   * 配置 AMI、instance type、key pair、security groups 等
   * 配置 storage、network interfaces、user data 等高级设置
2.  **使用 eksctl 基于 launch template 创建 node group**:

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
3.  **使用 AWS CLI 基于 launch template 创建 node group**:

    ```bash
    aws eks create-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name custom-ng \
      --launch-template id=lt-12345abcdef,version=1 \
      --subnets subnet-12345 subnet-67890 \
      --node-role arn:aws:iam::123456789012:role/EKSNodeRole
    ```

**其他选项的问题：**

* **缩短 cluster 创建时间**：使用 launch templates 不会缩短 cluster 创建时间。事实上，额外配置可能会使其耗时稍长。
* **Cluster control plane 自定义**：Launch templates 仅适用于 worker nodes；EKS control plane 由 AWS 管理，无法通过 launch templates 自定义。
* **自动使用最新 AMI version**：Launch templates 指定特定 AMI ID，实际上会产生锁定 AMI version 的效果。若要自动使用最新 AMI，必须不使用 launch templates，或定期更新 launch template。

当需要对 EKS node groups 进行高级自定义时，launch templates 特别有用；当存在标准配置无法满足的特殊需求时，应使用它们。

</details>

2. 以下哪一项不是 Amazon EKS clusters 的成本优化策略？
   * A) 使用 Spot instances
   * B) 配置 Cluster Autoscaler
   * C) 为所有 worker nodes 使用最新 instance types
   * D) 选择性使用 Fargate profiles

<details>

<summary>显示答案</summary>

**答案：C) 为所有 worker nodes 使用最新 instance types**

**解释：** 为所有 worker nodes 使用最新 instance types 不一定是成本优化策略。最新 instance types 通常提供更好的性能和功能，但并不总是最具成本效益。选择与 workload 要求匹配的适当 instance types 更重要。

**EKS clusters 的实际成本优化策略：**

1. **使用 Spot instances**:
   * 与 On-Demand instances 相比，最多可节省 90% 成本
   * 适合可中断 workloads（batch jobs、dev/test environments 等）
   *   在 managed node groups 中配置 Spot instances：

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
   *   混合多个 instance types 以提高可用性：

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
2. **配置 Cluster Autoscaler**:
   * 根据 workload 要求自动调整 node 数量
   * 通过自动删除未使用的 nodes 节省成本
   *   安装和配置：

       ```bash
       # Install Cluster Autoscaler using Helm
       helm repo add autoscaler https://kubernetes.github.io/autoscaler

       helm install cluster-autoscaler autoscaler/cluster-autoscaler \
         --namespace kube-system \
         --set autoDiscovery.clusterName=my-cluster \
         --set awsRegion=us-west-2 \
         --set rbac.create=true
       ```
3. **选择性使用 Fargate profiles**:
   * Serverless container execution environment 消除 node 管理开销
   * 只为使用的资源付费
   * 适合间歇性 workloads 或 dev/test environments
   *   仅针对特定 namespaces 或 labels 使用 Fargate：

       ```bash
       eksctl create fargateprofile \
         --cluster my-cluster \
         --name fp-dev \
         --namespace dev
       ```
4. **选择适当的 instance sizes**:
   * 选择与 workload 要求匹配的 instance sizes
   * 防止过度 provisioning
   *   监控并分析 resource usage：

       ```bash
       kubectl top nodes
       kubectl top pods --all-namespaces
       ```
5. **使用基于 Graviton (ARM) 的 instances**:
   * 与基于 x86 的 instances 相比，最多可节省 40% 成本
   * 提供同等性能
   * 需要验证兼容性
   *   示例：

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name arm-ng \
         --node-type m6g.large \
         --nodes 2
       ```
6. **利用 Reserved Instances 或 Savings Plans**:
   * 通过长期承诺节省成本
   * 适合可预测 workloads
   * 与 On-Demand 相比，最多可节省 72% 成本
7. **优化 resource requests 和 limits**:
   * 通过正确设置 pod resource requests 提高 node 利用率
   * 防止过度 provisioning
   *   示例：

       ```yaml
       resources:
         requests:
           cpu: 100m
           memory: 128Mi
         limits:
           cpu: 500m
           memory: 256Mi
       ```
8. **成本监控和分析**:
   * 使用 AWS Cost Explorer
   * 设置 Kubernetes cost allocation tags
   * 使用第三方成本监控工具（Kubecost、CloudHealth 等）

**使用最新 instance types 的问题：**

1. **成本增加**:
   * 最新 instance types 往往可能比上一代更昂贵
   * 并非所有 workloads 都需要最新 instances 的功能
2. **过度 provisioning**:
   * 提供超出 workload 要求的资源
   * 导致不必要成本
3. **可用性限制**:
   * 最新 instance types 可能并非在所有 regions 或 availability zones 中可用
   * 使用 Spot instances 时可用性尤其有限
4. **兼容性问题**:
   * 某些 workloads 可能针对特定 instance types 优化
   * 迁移到新 instance types 时需要测试

对于成本优化，重要的是综合考虑 workload 特征、resource 要求、可用性要求等，并选择合适的 instance types 和 sizes。最新 instance types 并不总是最具成本效益的选择，为 workload 选择适当的 instance types 更重要。

</details>

3. 在 Amazon EKS 中配置 private cluster 的正确方式是什么？
   * A) 仅将 nodes 放在 private subnets 中并禁用 public endpoint
   * B) 仅将 nodes 放在 private subnets 中并启用 public endpoint
   * C) 将 nodes 放在 public subnets 中并禁用 public endpoint
   * D) 仅将 nodes 放在 private subnets 中但不配置 VPC endpoints

<details>

<summary>显示答案</summary>

**答案：A) 仅将 nodes 放在 private subnets 中并禁用 public endpoint**

**解释：** 要在 Amazon EKS 中配置完全 private cluster，需要仅将 nodes 放在 private subnets 中并禁用 public endpoint。这确保 cluster 的 Kubernetes API server 不能从互联网访问，所有流量只在 VPC 内发生。

**Private EKS cluster 配置组件：**

1. **Endpoint access 配置**:
   * 禁用 public endpoint
   * 启用 private endpoint
   *   AWS CLI 配置示例：

       ```bash
       aws eks update-cluster-config \
         --name my-cluster \
         --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
       ```
   *   eksctl 配置示例：

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
2. **Node 放置**:
   * 仅将 nodes 放在 private subnets 中
   * 不分配 public IP
   *   Managed node group 配置示例：

       ```bash
       eksctl create nodegroup \
         --cluster my-cluster \
         --name private-ng \
         --node-type m5.large \
         --nodes 3 \
         --node-private-networking \
         --subnet-ids subnet-private1,subnet-private2
       ```
3.  **VPC endpoint 配置**：private clusters 访问 AWS services 需要 VPC endpoints：

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
4. **Network 配置**:
   * private subnets 中需要 NAT Gateway 或 VPC endpoints
   * 使用 security group rules 限制流量
   * Routing table 配置

**访问 private clusters 的方法：**

1. **通过 VPN 或 Direct Connect 访问**:
   * AWS Client VPN
   * AWS Site-to-Site VPN
   * AWS Direct Connect
2.  **通过 Bastion Host 访问**:

    * 将 bastion host 放在 public subnet 中
    * 从 bastion host 访问 cluster API server

    ```bash
    # Configure kubeconfig on bastion host
    aws eks update-kubeconfig --name my-cluster --region us-west-2
    ```
3. **通过 AWS Systems Manager Session Manager 访问**:
   * 在没有 internet gateway 的情况下访问 EC2 instances
   * 通过 IAM permissions 和 logging 进行 access control

**其他选项的问题：**

* **仅将 nodes 放在 private subnets 中并启用 public endpoint**：启用 public endpoint 时，cluster API server 可从互联网访问，因此这不是完全 private cluster。可以通过 security groups 或 CIDR restrictions 限制访问，但它仍暴露在 public networks 中。
* **将 nodes 放在 public subnets 中并禁用 public endpoint**：当 nodes 位于 public subnets 中时，它们可以直接从互联网访问，因此这不是完全 private cluster。可以通过 security groups 限制访问，但 nodes 可能会被分配 public IPs。
* **仅将 nodes 放在 private subnets 中但不配置 VPC endpoints**：将 nodes 放在 private subnets 中但不配置 VPC endpoints，会阻止 nodes 访问 ECR、S3 等 AWS services。在这种情况下，需要通过 NAT Gateway 访问互联网，这不是完全 private cluster 配置。

Private EKS clusters 适合需要高安全性的环境，可确保所有 cluster 流量只在 VPC 内发生。但是，配置更复杂，并且可能需要额外基础设施（VPN、Direct Connect、bastion hosts 等）来访问 cluster。

</details>

4. 以下哪一项不是 Amazon EKS clusters 中有效的 node group upgrade strategy？
   * A) Rolling upgrade
   * B) Blue/Green deployment
   * C) In-place upgrade
   * D) Canary deployment

<details>

<summary>显示答案</summary>

**答案：C) In-place upgrade**

**解释：** “In-place upgrade” 不是 Amazon EKS node groups 的官方 upgrade strategy。EKS managed node groups 默认使用 rolling upgrade 方法；对于 self-managed node groups，可以实现 blue/green deployment 或 canary deployment 等策略。

**EKS node group upgrade strategies：**

1. **Rolling Upgrade**:
   * EKS managed node groups 的默认升级方法
   * 通过一次替换一个 node 来最小化 workload 中断
   * 流程：
     1. 创建新 node
     2. 对现有 node 应用 cordoning（防止调度新的 pod）
     3. 从现有 node drain pods（迁移 pods）
     4. 终止现有 node
     5. 对下一个 node 重复
   *   配置示例：

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
   * 创建全新的 node group，然后切换流量
   * 易于回滚且风险较低
   * 资源使用会临时增加（运行双倍 nodes）
   * 实施步骤：
     1. 创建新的 node group（green）
     2. 在新 node group 上部署并测试 workloads
     3. 将流量切换到新 node group
     4. 删除现有 node group（blue）
   *   配置示例：

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
   * 先仅升级部分 nodes，以最小化风险
   * 如果出现问题，可限制影响范围
   * 可以逐步推出
   * 实施步骤：
     1. 创建小规模的新 node group
     2. 将部分 workloads 移动到新 node group
     3. 监控并验证
     4. 如果没有问题，则升级其余 nodes
   *   配置示例：

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

**In-place upgrades 的问题：**

术语 “in-place upgrade” 可能表示在不终止现有 nodes 的情况下升级它们。由于以下原因，这不适合 EKS node groups：

1. **违反 immutable infrastructure 原则**:
   * Cloud-native environments 建议替换 resources，而不是修改它们
   * 防止 node configuration drift
2. **升级失败风险**:
   * 如果 in-place upgrade 失败，nodes 可能变得不稳定
   * 回滚困难
3. **EKS node AMI 结构**:
   * EKS optimized AMIs 每个版本都有不同的 AMI IDs
   * AMI 不能通过 in-place upgrade 更改
4. **Managed node group 限制**:
   * EKS managed node groups 不支持 in-place upgrades
   * 始终使用 rolling upgrade 方法

**Node group upgrade 最佳实践：**

1.  **配置 PodDisruptionBudget**:

    * 在升级期间确保 application availability

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
2. **确保资源充足**:
   * node draining 期间需要备用 capacity 用于 pod relocation
   * 考虑 Cluster Autoscaler 配置
3. **升级前测试**:
   * 先在非生产环境中测试升级
   * 验证 application compatibility
4. **加强监控**:
   * 在升级期间和之后监控系统
   * 早期发现异常

EKS node group upgrades 是在最小化 workload 中断的同时应用安全补丁、bug fixes 和新功能的重要任务。根据你的情况选择 rolling upgrade、blue/green deployment 或 canary deployment 等策略，安全执行升级。

</details>

5. Amazon EKS clusters 的 node bootstrap process 中不会发生什么？
   * A) kubelet 配置和启动
   * B) Cluster control plane component 安装
   * C) AWS IAM Authenticator 配置
   * D) 向 cluster 注册 node

<details>

<summary>显示答案</summary>

**答案：B) Cluster control plane component 安装**

**解释：** 在 Amazon EKS node bootstrap process 中，不会安装 cluster control plane components。EKS 是一项 managed service，其 control plane（API server、controller manager、scheduler 等）由 AWS 管理，并且与 worker nodes 分开运行。在 node bootstrap process 中，只执行将 node 连接到现有 EKS cluster 的配置。

**EKS node bootstrap 期间实际发生的内容：**

1. **kubelet 配置和启动**:
   * 创建 kubelet 配置文件（`/etc/kubernetes/kubelet/kubelet-config.json`）
   * 配置 cluster endpoint、certificates、cluster DNS 等
   * 启动 kubelet service
   *   示例配置：

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
2. **AWS IAM Authenticator 配置**:
   * 为 IAM authentication 配置 aws-iam-authenticator
   * 创建 kubeconfig 文件
   * 配置 node IAM role
   *   示例配置：

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
3. **向 cluster 注册 node**:
   * 创建 node object
   * 设置 node labels 和 taints
   * 注册到 cluster API server
   *   示例 log：

       ```
       Node my-node-1 successfully registered with API server
       ```
4. **CNI plugin 配置**:
   * 配置 Amazon VPC CNI plugin
   * 设置 pod networking
   * 配置 IP address allocation
   *   示例配置：

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
5. **kube-proxy 设置**:
   * 为 cluster networking 配置 kube-proxy
   * 设置 service IP routing
   *   示例配置：

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
6. **Node labels 和 taints 应用**:
   * 根据 instance type、availability zone 等设置 labels
   * 应用 custom labels
   * 如有需要，应用 taints
   *   示例命令：

       ```bash
       kubectl label node my-node-1 eks.amazonaws.com/nodegroup=my-nodegroup
       kubectl label node my-node-1 topology.kubernetes.io/zone=us-west-2a
       ```

**Bootstrap script：**

EKS node bootstrapping 通过 `/etc/eks/bootstrap.sh` script 执行。此 script 可以接收以下参数：

```bash
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker' \
  --b64-cluster-ca <base64-encoded-ca> \
  --apiserver-endpoint <api-server-endpoint> \
  --dns-cluster-ip 10.100.0.10
```

使用 custom launch template 时，可以在 user data 部分调用此 script 以执行附加配置：

```bash
#!/bin/bash
set -ex
/etc/eks/bootstrap.sh my-cluster \
  --kubelet-extra-args '--node-labels=environment=prod,node-type=worker' \
  --max-pods 110
```

**Cluster control plane components：**

EKS cluster control plane components 由 AWS 管理，并且与 node bootstrap process 分离：

* API server
* Controller manager
* Scheduler
* etcd
* CoreDNS

这些 components 运行在 AWS-managed infrastructure 上，并确保高可用性和可扩展性。Nodes 只连接到这些 control plane components；它们不会直接安装或管理这些 components。

因此，在 Amazon EKS node bootstrap 期间不会发生的是 “cluster control plane component installation”。

</details>
