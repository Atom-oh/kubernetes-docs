# EKS 集群创建测验 - 第 1 部分

> **最后更新**：October 12, 2026

> 以下命令是彼此独立的示例，并非应从头到尾运行的脚本。请使用专用的培训账户/集群、经过审核的 IAM 权限以及私有临时 kubeconfig（`EXAMPLE_KUBECONFIG`）。替换示例 ID 和必需变量。创建命令会产生费用。本次审计检查了来源、语法和本地测试夹具；未配置 AWS 资源，也未验证应用程序是否可用。

本测验用于测试你对 Amazon EKS 集群创建相关概念、工具和最佳实践的理解。内容涵盖集群创建方法、VPC 配置和节点组设置等主题。

## 基础概念问题

1. 哪种工具没有内置命令可直接预置 EKS 控制平面？
   * A) AWS Management Console
   * B) AWS CLI
   * C) eksctl
   * D) kubectl

<details>

<summary>显示答案</summary>

**答案：D) kubectl**

kubectl 通过 Kubernetes API 管理资源，本身没有原生 EKS 预置命令。已经安装的基础设施控制器（例如 ACK）可以将通过 kubectl 提交的资源协调到 EKS 集群中；这是控制器集成，而不是 kubectl 内置的 AWS 操作。

可用于创建 Amazon EKS 集群的工具包括：

1. **AWS Management Console**：
   * 通过 Web 界面创建 EKS 集群。
   * 适合初学者，因为可以通过可视化方式配置集群组件。
   * 通过分步向导引导完成集群创建过程。
2.  **AWS CLI**：

    * 从命令行创建 EKS 集群。
    * 使用 `aws eks create-cluster` 命令。
    * 适用于脚本和自动化。

    ```bash
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
    ```
3.  **eksctl**：

    * 专为创建 EKS 集群而设计的命令行工具。
    * 最初由 Weaveworks 开发；目前该项目由 eksctl-io 组织维护，并由 AWS/社区贡献者参与。
    * 可以通过一条命令创建集群。

    ```bash
    eksctl create cluster --name my-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --nodes-min 1 --nodes-max 4
    ```
4.  **基础设施即代码（IaC）工具**：

    * AWS CloudFormation
    * Terraform
    * AWS CDK
    * Pulumi

    这些工具允许通过代码定义和部署 EKS 集群。

集群创建后，kubectl 用于管理 Kubernetes 资源（Pod、Service、Deployment 等）。若要连接到 EKS 集群，请配置经过授权的 kubeconfig，通常使用 `aws eks update-kubeconfig`。

```bash
aws eks update-kubeconfig --name my-cluster --region us-west-2
```

之后即可使用 kubectl 管理集群资源。

</details>

2. 创建 Amazon EKS 集群时必须指定哪个 VPC 组件？
   * A) 仅公共子网
   * B) 仅私有子网
   * C) 至少跨越 2 个可用区的子网
   * D) NAT Gateway

<details>

<summary>显示答案</summary>

**答案：C) 至少跨越 2 个可用区的子网**

**说明**：创建 Amazon EKS 集群时，必须指定的 VPC 组件是至少跨越 2 个可用区的子网。这是 AWS 为确保 EKS 集群高可用性而提出的要求。

**EKS 集群 VPC 要求：**

1. **至少 2 个可用区（AZ）中需要有子网**：
   * 由于 EKS 控制平面部署在多个可用区中，创建集群时必须指定至少 2 个可用区中的子网。
   * 这有助于实现区域级控制平面可用性。工作负载可用性还需要规划副本分布、容量、存储和依赖项。
2. **子网类型**：
   * 可以仅使用公共子网、仅使用私有子网，也可以混合使用公共和私有子网。
   * 对于生产环境，建议将工作节点放在私有子网中以增强安全性，并将公共子网用于负载均衡器。
3. **子网 CIDR 大小**：
   * 每个集群子网至少需要 6 个可用 IP 地址供 EKS 使用；AWS 建议至少 16 个。应另行规划节点/Pod/负载均衡器容量。
   * 由于 EKS 会为每个 Pod 分配 VPC IP 地址，因此需要根据预期 Pod 数量使用足够大的 CIDR 块。
4. **标签要求**：
   * 以下标签与特定集成的发现/所有权有关，并非 EKS 创建集群的通用要求：
     * 旧版或特定控制器的所有权标签：`kubernetes.io/cluster/<cluster-name>: shared`
     * 公共子网：`kubernetes.io/role/elb: 1`
     * 私有子网：`kubernetes.io/role/internal-elb: 1`

**VPC 配置示例（使用 eksctl）：**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2

vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["203.0.113.10/32"]
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

**使用 AWS CLI 配置 VPC：**

```bash
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-0123456789abcdef0,subnet-0123456789abcdef1,subnet-0123456789abcdef2,subnet-0123456789abcdef3
```

NAT gateway 是一种可能的互联网出口路径。必需的 VPC endpoint、镜像镜像仓库和私有连接可以支持无互联网访问的运行方式。将资源放在私有子网中与消除互联网出口是两个不同的决定。请用经过审核的实际值替换示例 VPC、子网和客户端 CIDR。

</details>

3. 配置采用 EC2 工作节点的常规 EKS 控制平面时，适用哪种角色分离方式？
   * A) 只需要集群角色
   * B) 只需要 EC2 节点角色
   * C) 集群角色和 EC2 节点角色分开配置
   * D) 两者都替换为 Fargate 执行角色

<details>
<summary>显示答案</summary>

**答案：C) 集群角色和 EC2 节点角色分开配置**

集群角色信任 `eks.amazonaws.com`，允许 EKS 管理集群基础设施。常规 EKS 需要 `AmazonEKSClusterPolicy` 或具有等效权限的策略。EC2 节点角色信任 `ec2.amazonaws.com`，并通过实例配置文件提供。EKS 会为托管节点组配置实例配置文件；节点引导过程不会创建 IAM 角色。

EC2 的基线策略是 `AmazonEKSWorkerNodePolicy` 和 `AmazonEC2ContainerRegistryPullOnly`，或遵循最小权限原则的等效权限。还需要 CNI 权限；建议使用单独的 IRSA/Pod Identity 角色。如果不这样做，则节点角色需要具有 CNI 权限。IPv4 的 `AmazonEKS_CNI_Policy` 不是 IPv6 策略。并非每个节点都普遍需要存储、负载均衡器和日志记录控制器权限。

此示例会创建新的常规集群/节点角色。请使用经过授权的账户/角色，并在发生错误时停止。名称冲突不会将策略附加到现有角色。

```bash
IAM_EXAMPLE_DIR=$(mktemp -d /tmp/eks-iam-example.XXXXXX)
: "${IAM_EXAMPLE_DIR:?}"
: "${NEW_CLUSTER_ROLE_NAME:?Choose an unused role name for this example}"
: "${NEW_NODE_ROLE_NAME:?Choose a different unused role name}"
cat > "$IAM_EXAMPLE_DIR/cluster-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "eks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
cat > "$IAM_EXAMPLE_DIR/node-trust.json" << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF
# Attach policies only after successfully creating the new role.
aws iam create-role --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/cluster-trust.json" &&
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

if aws iam create-role --role-name "$NEW_NODE_ROLE_NAME" \
  --assume-role-policy-document "file://$IAM_EXAMPLE_DIR/node-trust.json"; then
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy &&
  aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
fi
```

仅使用 `CreateCluster` 创建控制平面时，暂时不需要 EC2 节点角色。添加 EC2 计算资源时再添加该角色。Fargate 使用独立的 Pod 执行角色，该角色与应用程序的 AWS 权限分开。Auto Mode 需要额外的集群策略/`sts:TagSession` 以及最小化的节点角色策略。应单独审核 `iam:PassRole` 等预置身份权限。

[节点角色要求](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [Auto Mode 角色](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)

</details>

4. 使用 eksctl 创建 EKS 集群的正确命令是什么？
   * A) `eksctl create-cluster --name my-cluster --region us-west-2`
   * B) `eksctl create cluster --name my-cluster --region us-west-2`
   * C) `eksctl new cluster --name my-cluster --region us-west-2`
   * D) `eksctl start cluster --name my-cluster --region us-west-2`

<details>

<summary>显示答案</summary>

**答案：B) `eksctl create cluster --name my-cluster --region us-west-2`**

**说明**：使用 eksctl 创建 EKS 集群的正确命令是 `eksctl create cluster --name my-cluster --region us-west-2`。该命令会在指定名称和区域中使用默认设置创建 EKS 集群。

**eksctl 命令结构：**

* `eksctl`：基础命令
* `create`：创建资源的操作
* `cluster`：要创建的资源类型（集群）
* `--name my-cluster`：指定集群名称
* `--region us-west-2`：指定 AWS 区域

**基本集群创建命令：**

```bash
eksctl create cluster --name my-cluster --region us-west-2
```

默认值取决于 eksctl 版本。请在下方文件中明确选择 EKS 版本、AL2023、节点数量和 endpoint。创建过程可能会预置 VPC、节点和 IAM 资源；请在获得授权的测试账户中审核配置和费用。

**包含其他选项的高级命令：**

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
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --managed
```

**使用配置文件创建集群：**

```bash
# Create cluster.yaml file
cat > cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR:?Set your approved client CIDR}"]

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    amiFamily: AmazonLinux2023
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    ssh:
      allow: false
EOF

# Create cluster using configuration file
eksctl create cluster -f cluster.yaml
```

**其他选项的问题：**

* `eksctl create-cluster`：命令格式错误。eksctl 使用空格而不是连字符 (-) 分隔命令。
* `eksctl new cluster`：`new` 不是有效的 eksctl 命令。
* `eksctl start cluster`：`start` 不是有效的 eksctl 命令。应使用文档中列出的生命周期命令，而不是自行编造动词。

eksctl 提供多种 EKS 集群管理命令：

* `eksctl create cluster`：创建新集群
* `eksctl get cluster`：列出集群
* `eksctl upgrade cluster`：升级集群
* `eksctl delete cluster`：删除集群
* `eksctl create nodegroup`：添加节点组
* `eksctl scale nodegroup`：扩缩节点组

</details>

5. 创建新的 EKS 集群时，可以选择哪些 Kubernetes 版本？
   * A) 仅最新的上游版本
   * B) 始终恰好是最新版本加上两个版本
   * C) 目标区域中 EKS 标准支持或延长支持所提供的版本
   * D) 所有 Kubernetes 版本

<details>
<summary>显示答案</summary>

**答案：C) 目标区域中 EKS 标准支持或延长支持所提供的版本**

EKS 次要版本自其 EKS 发布之日起享有 **14 个月的标准支持**，随后进入 **12 个月的付费延长支持**。截至 2026 年 10 月 12 日，官方列表中的标准支持版本为 **1.34–1.37**，延长支持版本为 **1.31–1.33**。EKS 1.37 于 2026 年 10 月 1 日推出，晚于其 2026 年 8 月 26 日的上游发布。请查询目标区域中可用于新集群的版本。

延长支持默认启用；升级策略和支持终止日期可能会触发控制平面自动升级。节点/附加组件更新应另行规划。应遵循 AWS 的支持日期通知，不要将最长支持期限视为推迟升级的理由。

以下是用于版本发现、生成配置、通过 AWS 创建集群和升级现有集群的不同示例。请准备好经过授权的目标、角色、子网和 CIDR；不要盲目地将创建和升级示例作为一个工作流执行。

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table

# Generate a versioned config for review; this does not create the cluster.
EKS_VERSION_DIR=$(mktemp -d /tmp/eks-version.XXXXXX)
: "${EKS_VERSION_DIR:?}"
eksctl create cluster --name "${NEW_CLUSTER_NAME:?}" --region "$EXAMPLE_REGION" \
  --version 1.36 --dry-run > "$EKS_VERSION_DIR/version-example.yaml"
# Review all generated defaults, AMI, endpoint CIDRs and costs before creating.

# AWS CLI creation uses --kubernetes-version; the API JSON field is version.
aws eks create-cluster --name "$NEW_CLUSTER_NAME" --region "$EXAMPLE_REGION" \
  --kubernetes-version 1.36 --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API \
  --resources-vpc-config "subnetIds=${SUBNET_A:?},${SUBNET_B:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"

# Updating an existing control plane is a separate operation.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query cluster.version
# Only after upgrade-readiness checks and choosing the next supported minor:
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

控制平面只能逐个次要版本向前升级。应综合审核所需功能、剩余支持期限以及附加组件/工作负载兼容性。应测试目标版本，而不是假设旧版本总是更安全。从附加组件元数据中 grep 版本字符串无法取代集群版本查询。

[EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)

</details>

6. 哪个选项本身无法为 EKS 工作负载预置计算资源？
   * A) 托管节点组
   * B) 自管理节点组
   * C) Fargate profile
   * D) Kubernetes namespace

<details>

<summary>显示答案</summary>

**答案：D) Kubernetes namespace**

namespace 用于组织 Kubernetes 资源，但不提供计算资源。托管 EC2 节点组、自管理 EC2 节点和 Fargate profile 都是有效的计算方式。EKS Auto Mode 也可以预置托管节点，Hybrid Nodes 则连接客户自管理的本地/边缘计算容量。这些机制并非都使用托管节点组 API。


以下创建命令是针对现有集群和未使用的组/profile 名称提供的替代方案。请将所有必需变量替换为经过审核的值。检查 CNI/节点授权和私有子网连接。Fargate 需要 Pod 执行角色、兼容的 Pod 和私有子网；其 profile 不会创建应用程序 Pod。

**1. 托管节点组：**

* **特性**：
  * AWS 管理节点预置和生命周期
  * 自动创建和注册 EC2 实例
  * 自动配置 ASG（Auto Scaling Group）
  * 由操作员发起节点 Kubernetes 版本更新
  * EC2 健康状况异常时进行替换；EKS 节点修复需要受支持的健康信号/配置
  * 由操作员通过托管工作流发起 AMI 更新
*   **创建方式**：

    ```bash
    # Create managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-mng --managed --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5

    # Create managed node group using AWS CLI
    aws eks create-nodegroup \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --nodegroup-name my-mng --ami-type AL2023_x86_64_STANDARD \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --instance-types t3.medium \
      --scaling-config minSize=1,maxSize=5,desiredSize=3 \
      --node-role "${NODE_ROLE_ARN:?}"
    ```

**2. 自管理节点组：**

* **特性**：
  * 用户管理节点预置和生命周期
  * 自定义选项更多
  * 可以使用自定义 AMI 或引导脚本
  * 适用于特定实例类型或配置要求
*   **创建方式**：

    ```bash
    # Create self-managed node group using eksctl
    eksctl create nodegroup \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-smng --node-ami-family AmazonLinux2023 --node-private-networking \
      --node-type t3.medium \
      --nodes 3 \
      --nodes-min 1 \
      --nodes-max 5 \
      --managed=false

    # Can also be created manually using CloudFormation or EC2 launch templates.
    ```

**3. Fargate profile：**

* **特性**：
  * 无服务器容器执行环境
  * 无需管理节点
  * 按 Pod 分配资源并计费
  * 根据特定 namespace 和标签选择性运行
*   **创建方式**：

    ```bash
    # Create Fargate profile using eksctl
    eksctl create fargateprofile \
      --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --name my-fargate-profile \
      --namespace my-namespace \
      --labels app=my-app

    # Create Fargate profile using AWS CLI
    aws eks create-fargate-profile \
      --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
      --fargate-profile-name my-fargate-profile \
      --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
      --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
      --selectors '[{"namespace":"my-namespace","labels":{"app":"my-app"}}]'
    ```

**各选项对比：**

| 特性 | 托管节点组 | 自管理节点 | Fargate |
| --- | --- | --- | --- |
| 基础设施管理 | AWS 管理替换工作流；操作员配置更新/扩缩 | 操作员管理 AMI、引导流程和生命周期 | AWS 管理主机；用户管理应用、profile 和请求 |
| 成本 | 评估实例、利用率、承诺和运维 | 综合评估优化和运维 | 比较已分配的 Pod 规格、运行时间和限制 |
| 扩缩 | 需要单独的节点自动扩缩器/策略 | 需要单独的自动化机制 | 为匹配的 Pod 提供计算资源；应用副本扩缩是独立的 |

Auto Mode NodePool 和 Fargate profile 是不同于 EC2 托管节点组的资源。Fargate 仍需管理工作负载、安全性和可用性，而且并非总是更便宜或更贵。

</details>

7. 对新的 EKS 1.36 节点来说，哪种不是 AWS 发布的 EKS 优化 AMI 系列？
   * A) Amazon Linux 2023
   * B) Bottlerocket
   * C) Windows Server 2022
   * D) Ubuntu Core

<details>
<summary>显示答案</summary>

**答案：D) Ubuntu Core**

不要将 Ubuntu Core 视为 AWS 发布的 EKS 优化 AMI。Canonical Ubuntu Server 镜像和客户构建的 AMI 有不同的发布方、兼容性和支持路径；它们与 Ubuntu Core 不是同一产品。

**本示例中的选项**

- **AL2023**：使用 EKS 优化 AMI 和 `nodeadm` 引导。检查 Kubernetes 次要版本、CPU 架构、区域和 CNI 兼容性。
- **Bottlerocket**：一种专注于容器的操作系统，其配置和更新机制不同于通用 Linux 节点。
- **Windows**：匹配受支持的 Windows Server 主机/容器版本，并准备 Windows 网络、身份验证和系统工作负载前置条件。这不是适用于 Auto Mode/Fargate 的 Windows 示例。

**AL2 是旧版环境的迁移来源。** EKS 优化 AL2 AMI 的发布/支持已于 2025 年 11 月 26 日结束；AL2 OS 支持已于 2026 年 6 月 30 日结束。EKS Kubernetes 延长支持不会延长 AL2 支持期限。不要在新的 EKS 1.36 部署中推荐 AL2。

```bash
# Alternative examples; create only the reviewed group needed by your workload.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}"   --name al2023-nodes --managed --node-ami-family AmazonLinux2023 --node-private-networking

eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name bottlerocket-nodes --managed --node-ami-family Bottlerocket --node-private-networking

# Only after preparing the cluster for Windows:
eksctl create nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION"   --name windows-nodes --managed --node-ami-family WindowsServer2022FullContainer --node-private-networking
```

托管节点组启动模板也可以使用自定义 AMI。固定使用某个 AMI 时，必须验证其 OS/运行时、集群元数据和引导配置。仅在任意 Ubuntu 镜像上安装 `docker.io` 并不能得到可用的 EKS 节点。应使用适用于目标 EKS 版本的 Canonical 镜像，并采用经过审核的 eksctl/启动模板配置。高级问题会区分启动模板 `ImageId`、节点组 `amiType` 和用户数据合并限制。

选择镜像时，应综合考虑安全更新、测得的工作负载性能、Kubernetes/驱动程序兼容性、运维需求，以及 GPU 等特殊要求。

[AL2 过渡](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html) · [AL2023/nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [Windows 前置条件](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)

</details>

8. CreateCluster API 未指定 endpoint 访问设置时，默认值是什么？
   * A) 启用公共 endpoint，禁用私有 endpoint
   * B) 仅启用私有 endpoint
   * C) 同时启用两个 endpoint
   * D) 创建后无法更改访问设置

<details>
<summary>显示答案</summary>

**答案：A) 启用公共 endpoint，禁用私有 endpoint**

API 的默认设置是启用公共 endpoint、禁用私有 endpoint。eksctl、CDK 和控制台的创建流程可以明确选择其他设置；这并非所有工具通用的默认值。创建后可以更改访问设置。

| 公共 | 私有 | 访问路径 |
| --- | --- | --- |
| 开启 | 关闭 | 公共 endpoint 和 publicAccessCidrs；还要考虑节点/CI 的实际出口地址 |
| 开启 | 开启 | VPC 中的请求可通过私有路径访问；外部请求受允许的公共 CIDR 限制 |
| 关闭 | 开启 | 通过 VPC 或互联网络中的私有路径访问 |
| 关闭 | 关闭 | 配置无效 |

**集群安全组控制私有 endpoint 和 kubelet 流量，而非公共 endpoint 访问。** `publicAccessCidrs` 仅适用于公共 endpoint。无论网络是否可达，都仍然需要进行身份验证/授权。请将 IPv4 示例 CIDR 替换为实际获批的客户端出口地址。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.resourcesVpcConfig

# Select the actual approved client egress CIDR, not an arbitrary example range.
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text)
: "${ENDPOINT_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

在禁用公共访问前，请确认之前的更新状态为 `Successful`，并确认管理/CI 网络可以使用私有 DNS、路由和 API 访问。不要立即发送互相重叠的异步更新；应在一个请求中设置两个访问标志。

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

私有 API 访问与消除互联网出口是两个独立的设计选择。应综合评估身份、网络和运维控制措施；仅启用私有访问并不能保证安全性或可用性。应考虑 VPN/Direct Connect/管理主机和连接成本。IPv6 endpoint 和 Hybrid Nodes 还有其他 DNS/CIDR 注意事项，详见官方指南。

[集群 endpoint 访问控制](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)

</details>

9. 为 Amazon EKS 集群中的节点组选择实例类型时，以下哪项不是考虑因素？
   * A) 工作负载要求（CPU、内存、存储）
   * B) 成本优化
   * C) 本地 kubeconfig context 别名
   * D) 实例代际（例如 t3 与 t2）

<details>

<summary>显示答案</summary>

**答案：C) 本地 kubeconfig context 别名**

kubeconfig 别名是本地客户端名称，不会改变实例性能、定价或可用性。相较之下，所需可用区是否提供该实例类型、实际容量和账户配额都是重要的选择限制。

**选择节点组实例类型时的实际考虑因素：**

1. **工作负载要求（CPU、内存、存储）**：
   * 选择符合应用程序资源要求的实例类型
   * 内存密集型工作负载：r5、r6g 等内存优化型实例
   * 计算密集型工作负载：c5、c6g 等计算优化型实例
   * 均衡型工作负载：m5、m6g 等通用型实例
   * GPU 工作负载：p3、g4dn 等加速计算型实例
2. **成本优化**：
   * 按需实例与 Spot 实例
   * 预留实例或 Savings Plans
   * 适当选择实例规格（避免过度预置）
   * 通过基于 ARM 的 Graviton 实例（例如 m6g、c6g）节省成本
3. **实例代际**：
   * 针对实际工作负载比较各代实例的价格/性能
   * 对于可突增型实例系列，应考虑 CPU 积分行为和基准性能
   * 最新代际可提供增强网络、存储性能等
4. **网络要求**：
   * 增强型网络支持（ENA、EFA 等）
   * 网络带宽要求
   * 与每个实例最大 Pod 数量相关的网络限制
5. **存储要求**：
   * 是否需要本地实例存储（例如 i3、d3 实例）
   * EBS 优化支持
   * 存储吞吐量和 IOPS 要求
6. **CPU 架构**：
   * x86（Intel、AMD）与 ARM（AWS Graviton）
   * 应用程序兼容性注意事项

**可用区和节点组部署：**

所需的 AZ 覆盖范围会限制可用的实例类型。目录中显示某实例类型可用，并不保证能立即获得容量：

* 在多个可用区中部署节点组以实现高可用性
* 规划节点容量和 Pod 拓扑分布，然后验证实际调度情况
* 可以选择区域中的所有可用区，也可以选择特定可用区

```bash
# Deploy node group to specific availability zones
eksctl create nodegroup \
  --cluster "${EXAMPLE_CLUSTER:?}" --region us-west-2 \
  --name my-nodegroup --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --node-zones us-west-2a,us-west-2b
```

**实例类型选择示例：**

1. **Web 应用服务器**：
   * 通用型实例：t3.medium、m5.large
   * 性价比高，性能均衡
2. **数据库**：
   * 内存优化型实例：r5.xlarge、r6g.xlarge
   * 内存与 CPU 比例较高
3. **批处理作业**：
   * 计算优化型实例：c5.xlarge、c6g.xlarge
   * CPU 性能较高
4. **机器学习工作负载**：
   * GPU 实例：p3.2xlarge、g4dn.xlarge
   * 具备加速计算能力

以上实例系列仅为示例，并非当前产品目录或经过测量的性能排名。应综合审核工作负载、价格、架构、驱动程序以及所需 AZ 中的实例供应/容量。

</details>

10. 创建 Amazon EKS 集群后，配置 kubectl 的正确命令是什么？
    * A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`
    * B) `aws eks get-kubeconfig --name my-cluster --region us-west-2`
    * C) `kubectl config set-cluster my-cluster --region us-west-2`
    * D) `eksctl configure kubectl --name my-cluster --region us-west-2`

<details>

<summary>显示答案</summary>

**答案：A) `aws eks update-kubeconfig --name my-cluster --region us-west-2`**

**说明**：创建 Amazon EKS 集群后，配置 kubectl 的正确命令是 `aws eks update-kubeconfig --name my-cluster --region us-west-2`。此命令使用 AWS CLI 的 EKS 模块，更新指定集群的 kubeconfig 文件。

**kubectl 配置过程：**

1. **更新 kubeconfig 文件**：
   * kubeconfig 文件存储 kubectl 与 Kubernetes 集群通信所需的配置信息。
   * 选择顺序为显式指定的 `--kubeconfig`、第一个 `KUBECONFIG` 路径，然后是 `~/.kube/config`。
   * 该命令会合并集群/exec-auth 配置，并更改所选文件中的当前 context；它不会授予集群权限。
2. **命令组成部分**：
   * `--name`：EKS 集群名称
   * `--region`：集群所在的 AWS 区域
   * `--kubeconfig`（可选）：自定义 kubeconfig 文件路径
   * `--role-arn`（可选）：用于访问集群的 IAM 角色
3.  **完整命令示例**：

    ```bash
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
4.  **其他选项**：

    ```bash
    # Use custom kubeconfig file
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Use specific IAM role
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --role-arn arn:aws:iam::123456789012:role/EksAdminRole --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

    # Set alias
    aws eks update-kubeconfig --name my-cluster --region us-west-2 --alias my-cluster-alias --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
    ```
5.  **验证配置**：

    ```bash
    # Check current context
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config current-context

    # List all contexts
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" config get-contexts

    # Test cluster connection
    kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" cluster-info
    ```

**其他选项的问题：**

* `aws eks get-kubeconfig --name my-cluster --region us-west-2`：此命令不存在。AWS CLI 中没有 `get-kubeconfig` 子命令。
* `kubectl config set-cluster my-cluster --region us-west-2`：此命令语法错误。`kubectl config set-cluster` 不支持 `--region` 标志，也不会自动配置 EKS 集群所需的身份验证信息。
* `eksctl configure kubectl --name my-cluster --region us-west-2`：此命令不存在。eksctl 没有 `configure kubectl` 子命令。使用 eksctl 创建集群时会自动配置 kubeconfig；对于现有集群，请使用 `aws eks update-kubeconfig` 或 `eksctl utils write-kubeconfig`。

**使用 eksctl 为现有集群写入配置：**

对于现有集群，可写入其配置，而无需创建另一个集群：

```bash
eksctl utils write-kubeconfig --cluster my-cluster --region us-west-2 --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

此命令会为现有集群写入 kubeconfig。应另行验证 IAM 身份验证以及 access-entry/RBAC 授权。除非禁用，否则创建集群时也会默认写入 kubeconfig。

**管理多个集群：**

管理多个 EKS 集群时，可以针对每个集群运行 `aws eks update-kubeconfig` 命令，将它们添加到 kubeconfig 文件中：

```bash
# Configure first cluster
aws eks update-kubeconfig --name cluster1 --region us-west-2 --alias cluster1-west --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Configure second cluster
aws eks update-kubeconfig --name cluster2 --region us-east-1 --alias cluster2-east --kubeconfig "${EXAMPLE_KUBECONFIG:?}"

# Switch context
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --context cluster1-west get nodes
```

因此，创建 Amazon EKS 集群后配置 kubectl 的正确命令是 `aws eks update-kubeconfig --name my-cluster --region us-west-2`。

</details>

## 动手练习

### 练习 1：使用 eksctl 创建 EKS 集群

**场景**：为开发团队准备一个采用常规 EC2 托管节点组的集群。这是一个培训设计，并非已经通过生产就绪测试的证据，也不是经过测量的成本结果。

**要求**：使用两个 AZ，初始配置两个 `t3.medium` AL2023 节点，扩缩范围为 2–5，节点使用私有网络，并为两个 API endpoint 启用访问且配置经过批准的公共 CIDR。仅设置范围并不会安装自动扩缩器。在选择 `t3.medium` 之前，应检查可突增型实例的 CPU 积分、内存、IP 容量、配额和实际工作负载需求。

<details>
<summary>显示答案</summary>

**1. 准备工具和身份**。请使用[第 1 部分](../../eks/02-eks-cluster-creation-part1.md)中经过校验和检查、适用于相应架构的安装说明。本示例已根据 EKS 1.36 和 eksctl 0.230.0 进行审核；运行前请检查该区域提供的 EKS 版本，以及兼容的客户端/附加组件版本。`kubectl` 必须符合版本偏差限制。请使用现有且已获批准、登录用户可承担的操作员 IAM 角色；预置权限和 Kubernetes 访问权限是分开的。

**2. 生成并审核本地私有配置**。生成的名称用于新培训集群。公共 CIDR 必须是你实际获准使用的出口范围。两个 AZ 是 `us-west-2` 的示例，实际可用情况取决于供应和容量。

```bash
# Use a dedicated training account/role with reviewed provisioning permissions.
aws sts get-caller-identity
eksctl version
kubectl version --client
EKS_LAB_DIR=$(mktemp -d /tmp/eks-creation-lab.XXXXXX)
: "${EKS_LAB_DIR:?}"
EKS_LAB_CLUSTER="creation-quiz-$(date +%s)-$$"
EKS_LAB_REGION=us-west-2
EKS_LAB_KUBECONFIG="$EKS_LAB_DIR/kubeconfig"
: "${APPROVED_API_CIDR:?Set your actual approved administration egress CIDR}"
: "${OPERATOR_ROLE_ARN:?Set an existing IAM role ARN, not an STS session ARN}"

cat > "$EKS_LAB_DIR/cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_LAB_CLUSTER}
  region: ${EKS_LAB_REGION}
  version: "1.36"
availabilityZones: ["us-west-2a", "us-west-2b"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${APPROVED_API_CIDR}"]
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: false
  accessEntries:
    - principalARN: "${OPERATOR_ROLE_ARN}"
      type: STANDARD
      accessPolicies:
        - policyARN: arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
          accessScope:
            type: cluster
managedNodeGroups:
  - name: dev-ng
    amiFamily: AmazonLinux2023
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    privateNetworking: true
    disableIMDSv1: true
    ssh:
      allow: false
    tags:
      Environment: development
      Owner: training
EOF

# Review the local configuration; this command does not create resources.
eksctl create cluster -f "$EKS_LAB_DIR/cluster.yaml" --dry-run \
  > "$EKS_LAB_DIR/resolved.yaml"
```

此配置会专门为实验中的指定操作员授予 cluster-admin 访问权限，并禁用自动授予集群创建者管理员访问权限的行为。它不会创建操作员角色，也不会授予调用者承担该角色的权限。eksctl 会创建所需的集群/节点角色；请审核其生成策略的权限范围。常规基线配置可以将 VPC CNI 权限放在节点角色上。如需增强工作负载隔离，请根据官方 CNI IAM 指南为 `aws-node` 配置专用角色。不要仅仅因为之后可能会使用这些附加组件，就向所有节点添加宽泛的镜像推送、DNS、存储、负载均衡器或日志记录权限。

**3. 仅在审核配置和费用后预置资源**。默认的新 VPC 拓扑可能会创建 NAT 和其他收费基础设施。`eksctl` 使用 CloudFormation 创建 VPC/子网/安全组/角色/集群/节点组资源。失败时可能留下部分资源；请检查其堆栈事件，不要假定系统会自动彻底清理。

```bash
# Provisioning step: creates billable AWS resources.
if eksctl create cluster -f "${EKS_LAB_DIR:?}/cluster.yaml" --write-kubeconfig=false; then
  EKS_LAB_ARN=$(aws eks describe-cluster \
    --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
    --query cluster.arn --output text)
  : "${EKS_LAB_ARN:?Could not record the created cluster ARN}"
  aws eks update-kubeconfig --name "$EKS_LAB_CLUSTER" \
    --region "$EKS_LAB_REGION" --role-arn "${OPERATOR_ROLE_ARN:?}" \
    --kubeconfig "${EKS_LAB_KUBECONFIG:?}" --alias "$EKS_LAB_CLUSTER"
fi
```

**4. 验证实际状态、访问权限和扩缩范围**。等待 `ACTIVE` 节点组/集群状态和 `Ready` 节点，检查不健康的系统 Pod，并验证预期的 AZ 分布。创建请求成功或 RBAC 列表可见都不足以证明集群安全且运行正常。

```bash
aws eks describe-cluster --name "${EKS_LAB_CLUSTER:?}" \
  --region "${EKS_LAB_REGION:?}" \
  --query 'cluster.{status:status,version:version,endpoint:resourcesVpcConfig,access:accessConfig}'
aws eks describe-nodegroup --cluster-name "$EKS_LAB_CLUSTER" \
  --nodegroup-name dev-ng --region "$EKS_LAB_REGION" \
  --query 'nodegroup.{status:status,scaling:scalingConfig,ami:amiType}'
kubectl --kubeconfig "${EKS_LAB_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" get pods -n kube-system
kubectl --kubeconfig "$EKS_LAB_KUBECONFIG" auth can-i get nodes
```

**5. 仅添加必需组件**。Cluster Autoscaler 需要高级问题 2 中所述的 IAM/服务账户/发现配置；扩缩范围本身不会根据工作负载需求作出响应。`kubectl top` 需要已安装且运行正常的 Metrics Server。在经过审计的 Metrics Server 0.9.0 基线中，支持 Kubernetes 1.34 及更高版本；请验证实际安装的版本。在声称节省成本或正确完成规格配置之前，应先测量有代表性的使用情况。

**6. 清理此培训集群**。首先移除实验创建的 LoadBalancer Service/Ingress，并等待其控制器释放 AWS 资源；检查 PVC 回收策略和保留的卷。本练习本身不会创建此类应用程序资源。然后仅删除已记录的集群：

```bash
# Only after removing this lab's workloads and checking retained resources.
if CURRENT_LAB_ARN=$(aws eks describe-cluster \
  --name "${EKS_LAB_CLUSTER:?}" --region "${EKS_LAB_REGION:?}" \
  --query cluster.arn --output text) &&
  [ "$CURRENT_LAB_ARN" = "${EKS_LAB_ARN:?Original cluster ARN required}" ]; then
  eksctl delete cluster --name "$EKS_LAB_CLUSTER" --region "$EKS_LAB_REGION" --wait
else
  printf '%s\n' 'Cluster lookup/identity mismatch; no deletion attempted.' >&2
fi
```

之后检查 CloudFormation 和 AWS 资源清单，确认是否有删除失败、保留的卷以及独立创建的角色/endpoint。请保留配置/ARN 记录，直到确认清理完成；不再需要时，在本地删除临时 kubeconfig 目录。

</details>

### 练习 2：使用 AWS Management Console 创建 EKS 集群

**场景**：审核一种常规托管节点组设计，该设计可为后续生产部署提供参考。其工作负载规格、路由、IAM、可用性、升级和恢复仍是特定于环境的假设，需要经过测试。本次审计期间未实际预置或进行负载测试。

<details>
<summary>显示答案</summary>

**1. 准备单独的 IAM 角色。**

- 集群角色：信任 `eks.amazonaws.com`，并附加 `AmazonEKSClusterPolicy`。
- EC2 节点角色：信任 `ec2.amazonaws.com`，并附加 `AmazonEKSWorkerNodePolicy` 和 `AmazonEC2ContainerRegistryPullOnly`。在受支持的情况下，为 VPC CNI 配置其专用 IRSA/Pod Identity 角色。如果有意采用较简单的 IPv4 节点角色备用方案，则应明确附加 `AmazonEKS_CNI_Policy`，并记录共享权限的权衡。
- 预置/操作员身份：使用经过批准、限定资源范围的 IAM 权限，并通过 `iam:PassRole` 使用这些角色。为现有操作员角色添加 EKS access entry，并配置实验所需的访问策略。仅创建 kubeconfig 不会授予任何 Kubernetes 授权。

**2. 审核 VPC 和子网**。以下官方示例仍可作为参考；URL 中的日期不是 EKS 版本：

```text
https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml
```

在创建具有唯一名称的培训堆栈前，请阅读 CloudFormation 模板。其默认值会创建一个 VPC，其中包含**跨两个 AZ 的两个公共子网和两个私有子网、一个 internet gateway，以及两个 NAT gateway/EIP**。因此，这是一个由 NAT 支持且可出站访问互联网的设计，而不是无出口的私有集群。不要将默认值直接用于生产；请审核 CIDR 重叠、AZ、IP 容量和 NAT 费用。

记录 `VpcId`、`SubnetIds` 和 `SecurityGroups`。`SubnetIds` 同时包含**公共和私有子网**；请检查各路由表，并为节点选择实际的私有子网。输出中的自定义安全组并不能证明所有必需的通信规则都已存在。请审核 EKS 集群安全组、其他安全组以及控制平面/节点通信规则。

**3. 创建常规集群**。在 EKS 控制台中，选择自定义配置路径，并为本练习禁用 Auto Mode。选择 EKS 标准支持中的可用兼容版本（本次审计示例为 1.36）、集群服务角色以及经过审核的 VPC/子网。

- 选择 API access-entry 身份验证，并授予指定操作员适当的访问权限；不要依赖没有说明的创建者管理员默认行为。
- 如果采用仅限私有访问的 API，请先验证管理网络的私有路由/DNS。或者同时启用公共和私有访问，并将 `publicAccessCidrs` 限制为获批的管理出口范围。
- 为此常规 EC2 集群保留兼容的 VPC CNI、kube-proxy 和 CoreDNS 附加组件；审核其配置/权限。启用必需的控制平面日志，并考虑日志费用。
- 审核并创建集群，然后等待其变为 `ACTIVE`。创建耗时不固定；引用一个预计分钟数不能作为完成验证。

**4. 添加托管节点组**。选择 EC2 节点角色、AL2023 x86_64 AMI，以及受支持的实例类型，例如示例中的 `m5.large`。该示例使用 50 GiB 根磁盘、期望大小 3、最小值 2、最大值 5，并使用经过审核的私有子网。这些只是规格示例，并非生产建议。根据要求配置访问、IMDS 和存储加密；等待节点组变为 `ACTIVE`，并等待节点变为 `Ready`。

**5. 验证访问权限并检查实际 AWS 安全组**。使用控制台中记录的集群名称和获批的操作员角色：

```bash
CONSOLE_LAB_DIR=$(mktemp -d /tmp/eks-console-lab.XXXXXX)
: "${CONSOLE_LAB_DIR:?}"
CONSOLE_KUBECONFIG="$CONSOLE_LAB_DIR/kubeconfig"
aws eks update-kubeconfig --name "${CONSOLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --role-arn "${OPERATOR_ROLE_ARN:?}" \
  --kubeconfig "$CONSOLE_KUBECONFIG" --alias "$CONSOLE_CLUSTER"
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get nodes
kubectl --kubeconfig "$CONSOLE_KUBECONFIG" get pods -n kube-system

# Security groups are AWS resources; kubeconfig does not contain their rules.
aws eks describe-cluster --name "$CONSOLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_CLUSTER_SG_ID:?Copy the cluster SG ID from the result above}"
```

**6. 可选的 NetworkPolicy 练习**。首先验证所选 CNI 及其配置是否强制执行 NetworkPolicy。AWS VPC CNI 的策略支持必须已启用，并且节点/OS 设置必须支持该功能。以下仅拒绝入口流量的默认拒绝策略仅应用于新创建的空实验 namespace；它不会拒绝出口流量，且仅仅因为 `apply` 成功并不能证明策略正在生效。

```bash
# An optional isolated policy example, after enabling CNI policy enforcement.
NP_LAB_NAMESPACE="np-quiz-$(date +%s)-$$"
if kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" create namespace "$NP_LAB_NAMESPACE"; then
  NP_LAB_UID=$(kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    get namespace "$NP_LAB_NAMESPACE" -o jsonpath='{.metadata.uid}')
  : "${NP_LAB_UID:?Namespace identity lookup failed}"
  cat > "${CONSOLE_LAB_DIR:?}/default-deny.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: ${NP_LAB_NAMESPACE}
spec:
  podSelector: {}
  policyTypes:
    - Ingress
EOF
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" \
    apply -f "$CONSOLE_LAB_DIR/default-deny.yaml"
fi
```

使用专用测试 Pod 测试允许和拒绝的流量，并在将此模式用于真实工作负载前添加应用程序所需的允许策略。不要将其应用于现有的共享 `default` namespace。完成后移除隔离的 namespace：

```bash
# Remove only the namespace created above, after confirming its UID.
if CURRENT_NP_UID=$(kubectl --kubeconfig "${CONSOLE_KUBECONFIG:?}" \
  get namespace "${NP_LAB_NAMESPACE:?}" -o jsonpath='{.metadata.uid}') &&
  [ "$CURRENT_NP_UID" = "${NP_LAB_UID:?Original namespace UID required}" ]; then
  kubectl --kubeconfig "$CONSOLE_KUBECONFIG" delete namespace "$NP_LAB_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace lookup/identity mismatch; no deletion attempted.' >&2
fi
```

**7. 控制台清理**：移除实验工作负载，并等待相关云资源释放，然后删除此实验的托管节点组，等待其删除，再删除实验集群。只有在 EKS 资源及外部依赖均已删除后，才能删除实验 VPC CloudFormation 堆栈。仅删除专为此实验创建的 IAM 角色/endpoint；保留共享资源，并检查任何删除失败或保留的资源。本次审核未执行这些操作。

</details>

## 高级主题 {#advanced-topics}

以下问题涉及 Amazon EKS 集群创建的高级主题。本节用于测试你对 EKS 集群创建高级概念和最佳实践的理解。

1. 使用适用于 EKS EC2 托管节点组的自定义启动模板，主要好处是什么？
   * A) 保证缩短集群创建时间
   * B) 自定义节点用户数据和卷配置
   * C) 安装控制平面插件
   * D) 每当发布新的 AMI 时，自动更新所有现有节点

<details>
<summary>显示答案</summary>

**答案：B) 自定义节点用户数据和卷配置**

启动模板可自定义 **EC2 托管节点组**，包括存储、实例元数据和特定于 OS 的用户数据。它们不能配置 EKS 控制平面或 EKS Auto Mode 节点。

**AL2023 用户数据**：使用 MIME multipart 数据。使用 EKS 选择的 AMI（模板中没有 `ImageId`）时，EKS 会提供/合并节点配置。使用自定义 AMI ID 时，请提供高级问题 5 中介绍的完整 `NodeConfig`。AL2023 的 systemd 服务会运行 `nodeadm`；不要调用 `/etc/eks/bootstrap.sh`、再次运行 `nodeadm init` 或手动启动 kubelet。其他软件必须兼容所选 OS，并且其软件包源必须可访问且可信。

以下最小化自定义配置适用于 EKS 选择的 AL2023 AMI；它只会创建一个应用程序目录：

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_CUSTOMIZATION"

--EKS_CUSTOMIZATION
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_CUSTOMIZATION--
```

**存储**：以下是一个有效的 `LaunchTemplateData` 片段。请确认 AMI 的根设备名称。附加卷不会自动格式化或挂载。两个示例卷都经过加密，并会在实例终止时删除；对于必须在节点替换后保留的应用程序数据，请使用由 CSI 管理的 PV，并采用适当的回收/备份策略。

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    },
    {
      "DeviceName": "/dev/sdf",
      "Ebs": {
        "VolumeSize": 500,
        "VolumeType": "gp3",
        "Encrypted": true,
        "DeleteOnTermination": true
      }
    }
  ]
}
```

**网络和元数据**：请将示例安全组替换为其规则允许所需控制平面、节点、DNS 和工作负载流量的安全组。提供自定义安全组时，EKS **不会**自动添加集群安全组。应在实例级别或网络接口级别指定安全组，而不是同时在两者上指定。

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "Groups": ["sg-0123456789abcdef0"],
      "DeleteOnTermination": true
    }
  ],
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1
  }
}
```

跳数限制为 1 的前提是 Pod 使用 IRSA 或 EKS Pod Identity，而不是节点凭证。需要从容器访问 IMDSv2 的工作负载可能需要将跳数限制设为 2。此设置和 IMDSv2 都不会为 `hostNetwork` Pod 创建隔离。多个网络接口、置放方式和实例存储设备需要兼容的实例类型，并受 EKS 启动模板限制；它们并非在所有情况下都可互换使用。

**创建节点组**：审核实际 ID、权限和网络路由后，选择 eksctl 配置或 AWS CLI 示例之一。这两个示例是替代方案，不是连续执行的说明：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    subnets: ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

```bash
# Use an existing reviewed template version and a new node group name.
aws eks create-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --launch-template "id=${LAUNCH_TEMPLATE_ID:?},version=${LAUNCH_TEMPLATE_VERSION:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --node-role "${NODE_ROLE_ARN:?}"
```

不要在启动模板中设置 `SubnetId` 和 `IamInstanceProfile`：子网和节点 IAM 角色属于节点组请求的配置。使用启动模板时，不要同时设置节点组的 `diskSize` 或 `remoteAccess`。应在模板**或**节点组请求中设置实例类型。当存在 `ImageId` 时，应省略节点组的 `amiType`、`releaseVersion` 和 `version`，并验证自定义 AMI 的 kubelet/控制平面兼容性。

显式指定 `ImageId` 会固定使用某个 AMI；不指定该值的模板可以使用 EKS 选择的 AMI。两种情况下，只要发布新 AMI，现有节点都不会自动更新。更新自定义模板需要创建**同一个**模板的新版本，并显式更新节点组；此操作会替换实例。

参考资料：[启动模板限制](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[CreateNodegroup 字段](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[AL2023 初始化](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)。

</details>

2. 哪种方法单独使用不足以优化 EKS 成本？
   * A) 对可容忍中断的工作负载使用 Spot
   * B) 配置并授权 Cluster Autoscaler
   * C) 不经测量，为每个工作负载都选择最新一代实例
   * D) 根据工作负载需求和总成本选择性评估 Fargate

<details>
<summary>显示答案</summary>

**答案：C) 不经测量，为每个工作负载都选择最新一代实例**

仅因某实例属于最新一代就将其用于所有节点，并不足以构成成本分析。应比较工作负载的架构、吞吐量、延迟、内存、区域可用性和中断容忍度。新一代实例可能更经济；对于同等有效工作量，更新或较旧的实例并非总是更便宜。

1. **Spot 和实例类型多样化**：AWS 宣称 Spot 价格相较按需价格最高可优惠 90%；这只是潜在的定价折扣，并非本实验已测得或保证的节省金额。应考虑中断和替换容量。对于 Cluster Autoscaler，同一节点组中的混合实例类型应具有相同的 CPU/内存/GPU 规格，因为调度模拟会使用第一个实例类型。请另行验证对本地磁盘的依赖。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: spot-ng
    amiFamily: AmazonLinux2023
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    privateNetworking: true
    desiredCapacity: 2
    minSize: 1
    maxSize: 5
```

2. **Cluster Autoscaler**：最小/最大规格仅设置扩缩范围。需要安装并授权控制器，使其能根据无法调度的 Pod 和可移除容量调整期望容量。不要向所有节点授予宽泛的自动扩缩权限。在此次**新安装**前，应准备 `kube-system/cluster-autoscaler` 服务账户，并配置专用 IRSA 角色（OIDC 信任范围限定为该服务账户）或受支持的 Pod Identity 设置。将扩缩写入权限限制在目标集群的 Auto Scaling group，并使用 `k8s.io/cluster-autoscaler/enabled=true` 和 `k8s.io/cluster-autoscaler/<cluster-name>=owned` 标签标记这些 group。仅有节点组资源标签并不能证明已配置 ASG 发现功能。

控制器次要版本必须与集群匹配。Chart 9.59.0 默认使用控制器 1.35.0，因此此 EKS 1.36 示例明确选择 1.36.1。其他集群版本需要相匹配的控制器版本。请确认没有现有 CA 安装正在管理相同的 group。

```bash
# EKS 1.36 example: first prepare the dedicated service account/IAM role
# and discovery tags on the target Auto Scaling groups.
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  --set-string "autoDiscovery.clusterName=${EXAMPLE_CLUSTER:?}" \
  --set-string "awsRegion=${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  --wait --timeout 5m
```

3. **Fargate 和合理调整规格**：Fargate 可减少主机管理工作，但会根据分配的资源和运行时间收费，而不只是根据测量到的 CPU 使用量收费。应将 profile 与受支持的 Pod 和私有子网网络相匹配，并与 EC2 总成本进行比较。`kubectl top` 需要 Metrics Server，短时间采样不能替代容量规划。
4. **Graviton**：创建 ARM 节点组前，先测试 ARM64 镜像和依赖项。针对特定代际的“最高提升 40% 价格/性能”说法，并不代表账单普遍降低 40%，也不保证性能相同。

```bash
# Metrics Server must already be installed and healthy.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top nodes
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" top pods --all-namespaces

# Alternative compute examples: each creates separately billed resources.
eksctl create fargateprofile --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name fp-dev --namespace dev
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name arm-ng \
  --managed --node-ami-family AmazonLinux2023 \
  --node-type m6g.large --nodes 2 --node-private-networking
```

5. **承诺用量**：Reserved Instance 和 Savings Plans 可以降低符合条件的可预测用量成本。最高 72% 的宣传节省幅度取决于产品、期限、付款方式和用量；未使用的承诺可能抵消节省。
6. **requests 和 limits**：选择数值前应测量有代表性的工作负载。requests 会影响调度和自动扩缩器决策；limits 过小可能导致 CPU 限流或 OOM 终止。以下是单个容器的示例值：

```yaml
# Fragment inside spec.template.spec.containers[].
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

7. **成本分配**：使用 Cost Explorer 以及已配置的分配报告/工具。Kubernetes 标签不会自动成为已启用的 AWS 成本分配标签。应将控制平面、适用情况下的 Auto Mode 费用、存储、负载均衡器、NAT、传输和日志记录成本都纳入考量。

参考资料：[EKS 上的 CA](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)、[CA Chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler)、[CA 1.36.1](https://github.com/kubernetes/autoscaler/releases/tag/cluster-autoscaler-1.36.1)、[Spot 定价](https://aws.amazon.com/ec2/spot/)、[Fargate 定价](https://aws.amazon.com/fargate/pricing/)、[Graviton](https://aws.amazon.com/ec2/graviton/)、[Savings Plans](https://aws.amazon.com/savingsplans/)。

</details>

3. 哪种设计同时满足 Kubernetes API 仅限私有访问，以及节点/Pod 不访问出站互联网的要求？
   * A) 私有 API、无互联网出口的私有节点子网、必需的服务 endpoint 和私有管理路径
   * B) 仅使用私有节点，API 和出口设置保持不变
   * C) 同时禁用公共和私有 Kubernetes API endpoint
   * D) 禁用公共 API，同时保留不受限制的 NAT 出口

<details>
<summary>显示答案</summary>

**答案：A) 私有 API、无互联网出口的私有节点子网、必需的服务 endpoint 和私有管理路径**

应将两个决策分开考虑：**谁可以访问 Kubernetes API**，以及**节点/Pod 可以向何处发送流量**。仅使用私有 API 不会移除 NAT 路由、阻止工作负载出口，也不会确保每个数据包都留在一个 VPC 内。在路由、DNS、安全组和授权允许的情况下，互联网络可以访问私有 API。

对于本问题，要求是 API 仅限私有访问，并且节点/Pod 无法访问出站互联网。应启用私有 endpoint、禁用公共 endpoint、使用没有互联网出口路径的私有节点子网，并提供工作负载所需的服务 endpoint、镜像仓库镜像和管理路径。

**Endpoint 转换**：首先启用私有访问，等待更新成功，然后从指定私有网络测试经过身份验证的 `kubectl` 访问。只有在此之后，才使用下方单独的仅私有访问方案。检查返回的更新，直到状态为 `Successful`，然后重新检查访问。公共 endpoint 由 `publicAccessCidrs` 限制，而不是由集群安全组限制；后者控制私有 endpoint 流量。

```bash
# Separate alternative: run only after verifying private DNS/routing/API access
# from the administration and CI/CD network, and after prior updates succeeded.
PRIVATE_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
: "${PRIVATE_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$PRIVATE_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```

**节点位置**：此片段使用现有 VPC 和私有子网；使用前请替换 ID 并验证路由。它不会创建 VPC endpoint，也不会移除现有 NAT 路由。从无法访问私有网络的互联网工作站运行 eksctl，并不能访问仅限私有访问的 Kubernetes API。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-0123456789abcdef0
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
managedNodeGroups:
  - name: private-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 3
    privateNetworking: true
```

**AWS 服务连接**：以下 ECR 和 S3 示例只是整体设计的一部分。请先审核现有 endpoint，避免重复的私有 DNS 配置冲突。Interface endpoint 需要启用私有 DNS，并允许预期客户端通过 HTTPS 入站；S3 gateway endpoint 需要关联私有路由表，并使用适当的 endpoint/bucket 策略。

```bash
# Example fragments for a reviewed no-internet VPC design.
# Interface endpoint SG must allow HTTPS from the intended nodes/clients.
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.api" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.ecr.dkr" \
  --vpc-endpoint-type Interface --private-dns-enabled \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --security-group-ids "${ENDPOINT_SG_ID:?}"
aws ec2 create-vpc-endpoint --region "${EXAMPLE_REGION:?}" \
  --vpc-id "${EXAMPLE_VPC:?}" \
  --service-name "com.amazonaws.${EXAMPLE_REGION}.s3" \
  --vpc-endpoint-type Gateway \
  --route-table-ids "${PRIVATE_ROUTE_TABLE_A:?}" "${PRIVATE_ROUTE_TABLE_B:?}"
```

| 依赖项 | 无互联网路径时的私有连接 |
| --- | --- |
| 私有 ECR 镜像拉取 | `ecr.api`、`ecr.dkr` 和 S3 gateway；将公共镜像复制到可访问的私有镜像仓库 |
| 节点/CNI 使用的 EC2 API | `ec2`、适当的权限和 endpoint 策略 |
| IRSA 凭证 | 区域性 `sts`；配置 SDK 使用区域 endpoint |
| VPC 内的 OIDC 发现/JWKS | `oidc-eks`，例如设置 IAM OIDC provider 时；与 STS 分开 |
| EKS Pod Identity 凭证 | `eks-auth`，以及受支持的 Pod Identity Agent/设置 |
| EKS 管理 API | `eks`；它不能替代 Kubernetes API 私有 endpoint |
| Logs、自动扩缩、负载均衡、SSM | 使用的实际服务所需的 endpoint 和权限；SSM 还需要其消息服务连接 |

Endpoint 服务和 DNS 名称因区域/分区而异。请检查每个工作负载的完整依赖项，包括镜像仓库、软件包下载、外部 API 和附加组件功能。单个 AWS 服务的 endpoint 并不能替代通用互联网连接。

**管理**：使用通过路由连接的 VPN/Direct Connect、具有私有访问权限的受控主机，或经过适当配置的 SSM 会话。堡垒机并非必然需要公共 IP。SSM 仍需要其 Agent、IAM 授权和服务连接。

私有 API 配合由 NAT 支持的私有节点也是有效的 EKS 设计，但不符合本问题中无互联网出口的要求。同样，仅有子网公共路由并不能证明某个节点可访问互联网；地址分配和安全控制也很重要。

参考资料：[私有集群要求](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[API endpoint 访问](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[EKS PrivateLink 和 OIDC](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)。

</details>

4. 以下哪项不是 EKS 托管节点组应用新节点 AMI 的机制？
   * A) 通过托管滚动更新替换实例
   * B) 创建并验证单独的蓝绿节点组
   * C) 在运行中的实例上升级 OS 软件包，而不替换实例
   * D) 在扩大替换范围前，先在小型 canary 节点组中验证新 AMI

<details>
<summary>显示答案</summary>

**答案：C) 在运行中的实例上升级 OS 软件包，而不替换实例**

EKS 托管节点组更新会替换 EC2 实例。在运行中的实例上升级 OS 软件包并不是托管 AMI 更新机制。应避免含糊地声称所有“就地升级”都不受支持：AWS 也使用该术语描述保留节点组资源并更改启动模板 AMI 版本的做法，而该做法仍会替换实例。

**滚动更新：**`DEFAULT` 会先创建替换容量，再停用旧节点；`MINIMAL` 可以在创建替换节点前终止选定的旧节点。`maxUnavailable` 默认为 1，但可以配置，因此并非总是严格每次更新一个节点。请检查配额、AZ 容量、Pod 分布和更新策略。使用自定义 AMI 时，应明确选择同一启动模板的新版本；以下命令则演示 EKS 选择的 AMI 情况：

```bash
# EKS-selected AMI case: inspect first, then initiate a reviewed update.
aws eks describe-nodegroup \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'nodegroup.{status:status,version:version,ami:amiType,release:releaseVersion,update:updateConfig}'
if NODE_UPDATE_ID=$(aws eks update-nodegroup-version \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --region "${EXAMPLE_REGION:?}" --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODE_UPDATE_ID" \
    --region "$EXAMPLE_REGION" \
    --query 'update.{status:status,errors:errors}'
fi
```

记录返回的更新 ID，并重复运行 `describe-update`，直到状态变为终止状态。API 提交成功并不意味着更新完成。继续操作前，应先调查返回的错误。阻止驱逐的 PDB 可能导致 `PodEvictionFailure`；不要只为让命令完成就使用 `--force` 绕过它。

**蓝绿部署**：创建单独且兼容的 AL2023 节点组，测试工作负载调度和就绪情况，然后逐步迁移。只有在应用程序检查、卷/AZ 限制和回滚要求均满足后，才保留旧容量。仅列出节点标签并不构成验证；流量通过 Service endpoint/Pod 路由，而不是按节点组名称路由。创建新节点组后，不要立即自动删除旧节点组。

**Canary**：使用小型、单独标记并添加污点的节点组。污点可阻止无关 Pod 落入该组；只有测试工作负载会选择并容忍此污点。如果系统 DaemonSet 的容忍规则允许，它们仍可运行。这是针对现有测试集群的示例配置：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: canary-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    desiredCapacity: 1
    minSize: 1
    maxSize: 2
    privateNetworking: true
    labels:
      example.com/upgrade-track: canary
    taints:
      - key: example.com/upgrade-track
        value: canary
        effect: NoSchedule
```

在专用测试 context 中创建未使用的 `upgrade-lab` namespace，然后再应用下面这个完整的演示 Deployment。真正的 canary 还必须测试应用程序自身的依赖项和有代表性的流量；此 NGINX Pod 只能检查基本调度和就绪情况。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: upgrade-canary
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      nodeSelector:
        example.com/upgrade-track: canary
      tolerations:
        - key: example.com/upgrade-track
          operator: Equal
          value: canary
          effect: NoSchedule
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
```

**中断预算和容量**：以下单独示例假设 `app-namespace` 中存在真实的 `my-app` 工作负载，且通常至少有三个就绪副本。它不是上述单副本 canary 的 PDB：

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: app-namespace
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

PDB 会限制通过 eviction API 处理的自愿驱逐；它不能保证可用性、阻止硬件故障，也不能阻止直接删除 Pod/Deployment。当只有两个匹配 Pod 健康时，`minAvailable: 2` 会阻止驱逐。请验证备用容量、拓扑、探针、终止行为以及故障恢复能力。蓝绿或 canary 计划本身并不能证明回滚安全，特别是在涉及有状态数据时。

参考资料：[托管更新行为](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)、[AL2023 迁移](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[Pod 中断预算](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)。

</details>

5. 以下哪项不属于 EKS 优化的 AL2023 EC2 工作节点引导过程？
   * A) 配置 kubelet/container runtime
   * B) 在工作节点上安装 AWS 管理的控制平面组件
   * C) 配置节点客户端身份验证/连接
   * D) 注册节点

<details>
<summary>显示答案</summary>

**答案：B) 在工作节点上安装 AWS 管理的控制平面组件**

工作节点不会安装 API server、etcd、controller manager 或 scheduler；这些属于 AWS 管理的控制平面。**常规 EKS 中的 CoreDNS 是数据平面集群附加组件，而不是控制平面组件之一。**

EKS 优化的 AL2023 AMI 使用 `nodeadm` 配置 containerd 和 kubelet。`nodeadm-config` 会在用户数据执行前建立基线配置，`nodeadm-run` 则会在之后完成配置并启动守护进程。AMI 会自动运行这些流程；不要在用户数据中再次调用 `nodeadm init`。AL2 的 `/etc/eks/bootstrap.sh` 流程不是当前的 AL2023 引导路径。

**区分节点加入和集群网络配置**

1. 启动节点前，先配置节点 IAM 角色/实例配置文件和必需的节点访问授权。引导流程不会创建 IAM 角色。应使用 AMI 生成的 kubeconfig/身份验证路径，避免手动创建不必要地再次假设实例自身角色的 kubeconfig。
2. kubelet 会注册节点。节点就绪情况不仅取决于集群连接，还取决于 runtime/CNI 健康状况。
3. 常规 EKS 会将 `aws-node`、`kube-proxy` 和 CoreDNS 部署/管理为集群附加组件。主机引导不会安装所有这些附加组件；不要用自行编造的文件覆盖 CNI 配置。
4. 不要手动伪造由 provider 管理的 `eks.amazonaws.com/nodegroup` 或 `topology.kubernetes.io/zone` 标签。应通过节点组/预置器配置来管理自定义标签/污点。

**NodeConfig 输入示例**

以下命令在管理工作站上运行，用于从现有 IPv4 集群的实际元数据生成用户数据。它适用于经过审核的、基于 EKS 优化 AL2023 的自定义 AMI/自管理节点；对于不使用自定义 AMI ID 的托管节点组，EKS 会生成/合并元数据。`NodeConfig` 是主机引导配置，不是可通过 `kubectl apply` 提交的常规 Kubernetes 资源。

```bash
# Run on the administration workstation to prepare reviewed IPv4 node user data.
NODE_CONFIG_DIR=$(mktemp -d /tmp/eks-nodeconfig.XXXXXX)
: "${NODE_CONFIG_DIR:?}"
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster --output json > "$NODE_CONFIG_DIR/cluster.json" || exit 1

jq -e '
  (.name | type == "string" and length > 0) and
  (.endpoint | startswith("https://")) and
  (.certificateAuthority.data | type == "string" and length > 0) and
  (.kubernetesNetworkConfig.ipFamily == "ipv4") and
  (.kubernetesNetworkConfig.serviceIpv4Cidr | type == "string" and length > 0)
' "$NODE_CONFIG_DIR/cluster.json" >/dev/null || exit 1

jq '{
  apiVersion: "node.eks.aws/v1alpha1",
  kind: "NodeConfig",
  spec: {
    cluster: {
      name: .name,
      apiServerEndpoint: .endpoint,
      certificateAuthority: .certificateAuthority.data,
      cidr: .kubernetesNetworkConfig.serviceIpv4Cidr
    }
  }
}' "$NODE_CONFIG_DIR/cluster.json" > "$NODE_CONFIG_DIR/nodeconfig.json" || exit 1

{
  printf 'MIME-Version: 1.0\n'
  printf 'Content-Type: multipart/mixed; boundary="EKS_NODE_CONFIG"\n\n'
  printf '%s\n' '--EKS_NODE_CONFIG' 'Content-Type: application/node.eks.aws' ''
  cat "$NODE_CONFIG_DIR/nodeconfig.json"
  printf '\n%s\n' '--EKS_NODE_CONFIG--'
} > "$NODE_CONFIG_DIR/user-data.mime"
printf 'Review user data: %s\n' "$NODE_CONFIG_DIR/user-data.mime"
# An EC2 LaunchTemplateData.UserData JSON field needs the MIME file base64 encoded.
# The console user-data editor can accept raw text when its encoding option is set accordingly.
```

不要为所有节点硬编码一个 DNS Service IP 或 maxPods 值。应遵循集群 Service CIDR、实例/CNI/前缀设置和文档中的规格规则。这些检查命令描述的是常规 EC2 配置；Auto Mode/Fargate 中的托管组件有所不同。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -L eks.amazonaws.com/nodegroup,topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" describe node "${EXAMPLE_NODE:?}"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get daemonset aws-node kube-proxy
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get deployment coredns
```

本次审计期间未执行或收集节点加入、守护进程运行、网络行为和运行时日志相关信息。

[AL2023/nodeadm 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html) · [NodeConfig API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)

</details>

## 官方参考资料

- [EKS 支持的版本](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS 节点 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [VPC CNI IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [NetworkPolicy 前置条件](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Metrics Server 要求](https://github.com/kubernetes-sigs/metrics-server#requirements)
- [eksctl 配置 schema](https://schema.eksctl.io/)
