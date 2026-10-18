# 第 3 部分：使用 AWS Management Console 和 CLI 创建集群

> **最后更新**：2026年9月11日

先完成[第 1 部分的前置条件](02-eks-cluster-creation-part1.md)。这些示例会创建需要付费的 AWS 资源，属于教学流程；本次审核并未实际预置资源，也未认证其适用于生产环境。

## 使用 AWS Management Console 创建集群

本节将创建采用 EC2 托管节点组的常规集群。请选择 **Custom configuration（自定义配置）**，并关闭 **Use EKS Auto Mode**。Auto Mode 的快速创建流程使用不同的角色和基础设施管理方式。

![基于控制台的创建流程图：从登录开始，依次进行集群配置、审核并创建、添加节点组和连接。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part3-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part3-0.html)

该图仅说明工作流程，实际创建时间会有差异。请明确检查创建者的访问权限和节点就绪情况，不要假设默认设置一定符合要求。

### 集群配置

在目标账户和区域中打开 EKS 控制台，选择 **Add cluster → Create**，然后选择上述自定义配置。

- 选择唯一的集群名称和当前受支持的 EKS 版本。下方 CLI 示例使用 **1.36**；上游 Kubernetes 发行版本列表并不等同于 EKS 支持版本目录。
- 选择已审核且信任策略包含 `eks.amazonaws.com`、并附加 `AmazonEKSClusterPolicy` 的集群 IAM 角色。预置资源所用的身份也需要适当的 EKS/IAM 权限，包括范围受限的 `iam:PassRole`；必要时还需创建服务相关角色。
- 检查标准/延长支持策略、标签和可选功能。EKS 1.28 及更高版本已使用 AWS 拥有的密钥对 Kubernetes API 数据进行信封加密；客户管理的 KMS 密钥是可选项。
- 选择 API 访问条目认证模式。此实验应禁用自动向创建者授予管理员权限，并为现有操作员角色规划显式访问条目。稍后创建 kubeconfig 并不会授予授权。

### 指定网络

选择符合 EKS 要求的现有 VPC，或先按完整网络设计准备一个 VPC。在不同 AZ 中至少选择两个合适的子网。每个集群子网至少需要 6 个可用 IP 地址；AWS 建议至少 16 个，并且还需为节点、Pod 和更新预留额外容量。

检查 VPC DNS、路由、IP 地址族与服务 CIDR 是否重叠，以及节点能否访问所需的 AWS 服务和容器镜像仓库。为节点使用具备合适 NAT 或 VPC 端点的私有子网。API 端点有以下选项：

- **Public（公有）**：通过公有网络路由访问，并使用 `publicAccessCidrs` 限制客户端来源地址范围。
- **Private（私有）**：通过 VPC 或已连接的网络访问，并正确配置所需路由、DNS、安全组及 IAM/Kubernetes 授权。
- **Public and Private（公有和私有）**：同时启用两条路径；限制公有 CIDR，并验证私有访问路径。

EKS 会创建集群安全组。可选的额外安全组会附加到集群网络接口，并不会自动附加到每个节点组。集群安全组上笼统的 TCP 443 规则并不能控制公有 API 端点的访问。

### 配置日志

在 **Configure observability（配置可观测性）** 中选择所需的控制平面日志类型：`api`、`audit`、`authenticator`、`controllerManager` 和 `scheduler`。请分别检查可选的指标功能。CloudWatch 摄取、存储和查询均会产生费用，日志投递采用尽力而为方式。

### 选择附加组件

对于此常规 EC2 集群，除非已有经过审核的替代方案，否则保留兼容的 VPC CNI、CoreDNS 和 kube-proxy。在 **Configure selected add-ons settings（配置所选附加组件设置）** 中选择兼容版本，并配置附加组件所需的 IAM 身份。可选控制器和存储驱动需要单独安装并配置权限。

### 审核并创建

检查所选角色、访问模式、网络和附加组件设置，然后创建集群并等待状态变为 **ACTIVE**。在预期能够使用 kubectl 访问集群之前，先配置操作员访问条目。

### 添加节点组

在集群的 **Compute（计算）** 区域添加托管节点组：

1. 选择未使用过的节点组名称和经过审核的 EC2 节点 IAM 角色。
2. 选择 **AL2023 x86_64**、兼容的实例类型，以及适合工作负载的磁盘和扩缩容数值。CLI 示例中的 `m5.large`、80 GiB 和 1–3 个节点范围只是示例，并非经测量得出的容量建议。
3. 选择实际的私有子网。除非已有单独审核过的访问路径，否则保持禁用 SSH 访问。
4. 创建节点组并等待其状态变为 **ACTIVE**，且节点健康并处于 **Ready** 状态。设置最小/最大节点数并不会安装基于工作负载的节点自动扩缩容器。

节点角色需要工作节点和镜像拉取权限。优先使用单独的 CNI 工作负载角色；下方 CLI 示例明确说明了较简单的 IPv4 节点角色回退方案。

## 使用 AWS CLI 创建集群

以下常规 IPv4 示例使用 EKS 1.36 和 AL2023 托管节点。请选择此流程或控制台流程之一。请在同一个 Bash 会话中执行 CLI 步骤，使用未占用的实验名称，并保留私有响应文件以便检查资源归属和清理情况。

![AWS CLI 工作流程图：先创建 IAM 角色、VPC 和安全组，再创建集群和节点组，最后刷新 kubeconfig。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part3-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part3-1.html)

该图展示一般步骤。EKS 会自动创建集群安全组；请使用下方当前的角色策略和明确的访问设置。本次审核未执行这些 AWS 操作。

```bash
: "${EKS_CLUSTER_NAME:?Choose an unused training cluster name}"
: "${EKS_REGION:?For example us-west-2}"
: "${OPERATOR_ROLE_ARN:?Existing operator IAM role that this login may assume}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
EKS_CREATE_DIR=$(mktemp -d /tmp/eks-console-cli.XXXXXX)
: "${EKS_CREATE_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATE_DIR/kubeconfig"
aws sts get-caller-identity
```

### 1. 创建集群 IAM 角色

以下命令会创建一个**新**角色，并在创建失败时停止。若要重复使用已经审核过的角色，请设置 `EKS_CLUSTER_ROLE_ARN` 并跳过创建/附加策略代码块；不要仅因名称碰巧相同就修改已有角色。

```bash
cat > "${EKS_CREATE_DIR:?}/cluster-trust.json" << 'EOF'
{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Principal":{"Service":"eks.amazonaws.com"},
    "Action":"sts:AssumeRole"
  }]
}
EOF
aws iam create-role --role-name "${NEW_CLUSTER_ROLE_NAME:?Unused role name}" \
  --assume-role-policy-document "file://$EKS_CREATE_DIR/cluster-trust.json" \
  --query Role --output json > "$EKS_CREATE_DIR/created-cluster-role.json" || exit 1
EKS_CLUSTER_ROLE_ARN=$(jq -er '.Arn' "$EKS_CREATE_DIR/created-cluster-role.json") || exit 1
aws iam attach-role-policy --role-name "$NEW_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy || exit 1
```

### 2. 创建 VPC 和子网

可以使用经过审核的现有 VPC，也可以选择使用下方的官方模板创建完整示例网络。该模板会跨两个 AZ 创建两个公有子网和两个私有子网、一个互联网网关，以及两个 NAT 网关/EIP。请先检查 CIDR 是否重叠、路由和费用。模板 URL 中的日期不是 Kubernetes 版本。

```bash
# Optional new-network path; review the entire template and its CIDR/NAT costs first.
aws cloudformation create-stack --region "${EKS_REGION:?}" \
  --stack-name "${NEW_VPC_STACK_NAME:?Unused stack name}" \
  --template-url https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml \
  > "${EKS_CREATE_DIR:?}/vpc-stack.json" || exit 1
aws cloudformation wait stack-create-complete --region "$EKS_REGION" \
  --stack-name "$NEW_VPC_STACK_NAME" || exit 1
aws cloudformation describe-stacks --region "$EKS_REGION" \
  --stack-name "$NEW_VPC_STACK_NAME" --query 'Stacks[0].Outputs' --output table
```

堆栈的 `SubnetIds` 输出包含**全部四个子网**。在设置 `EKS_PRIVATE_SUBNET_A/B` 前，请根据路由表和标签识别其中的私有子网对。若子网未显式关联路由表，它会使用 VPC 的主路由表；该子网仍具有路由。

下方检查会验证基本的 AZ/VPC/IP/DNS 前置条件。还需另行验证实际生效的路由、安全控制、容器镜像仓库和 S3 访问，以及任何必需的 VPC 端点。仅创建 VPC 和两个子网并不能提供可用的节点出站网络路径。

```bash
# Set these IDs after identifying the actual private subnets and their routes.
aws ec2 describe-subnets --region "${EKS_REGION:?}" \
  --subnet-ids "${EKS_PRIVATE_SUBNET_A:?}" "${EKS_PRIVATE_SUBNET_B:?}" \
  --query Subnets --output json > "${EKS_CREATE_DIR:?}/subnets.json" || exit 1
jq -e 'length == 2 and
  (map(.VpcId) | unique | length) == 1 and
  (map(.AvailabilityZone) | unique | length) == 2 and
  all(.[]; .AvailableIpAddressCount >= 6)' \
  "$EKS_CREATE_DIR/subnets.json" >/dev/null || exit 1
EKS_VPC_ID=$(jq -er '.[0].VpcId' "$EKS_CREATE_DIR/subnets.json") || exit 1
aws ec2 describe-vpc-attribute --region "$EKS_REGION" --vpc-id "$EKS_VPC_ID" \
  --attribute enableDnsSupport --output json > "$EKS_CREATE_DIR/dns-support.json" || exit 1
aws ec2 describe-vpc-attribute --region "$EKS_REGION" --vpc-id "$EKS_VPC_ID" \
  --attribute enableDnsHostnames --output json > "$EKS_CREATE_DIR/dns-hostnames.json" || exit 1
jq -e '.EnableDnsSupport.Value == true' "$EKS_CREATE_DIR/dns-support.json" >/dev/null || exit 1
jq -e '.EnableDnsHostnames.Value == true' "$EKS_CREATE_DIR/dns-hostnames.json" >/dev/null || exit 1
```

### 3. 创建集群安全组

EKS 会在创建集群时自动创建集群安全组。此示例不需要另建一个向 `0.0.0.0/0` 开放的安全组。公有 API 访问通过 `publicAccessCidrs` 限制；集群安全组规则则管理私有访问路径和节点通信。

如果需要额外安全组，请先审核其规则，再有意地将其 ID 加入配置。使用 JSON 构建集群网络请求：

```bash
# EKS creates the cluster security group; public API restrictions use this CIDR list.
jq -n --arg a "${EKS_PRIVATE_SUBNET_A:?}" --arg b "${EKS_PRIVATE_SUBNET_B:?}" \
  --arg cidr "${APPROVED_API_CIDR:?}" '{
    subnetIds:[$a,$b],
    endpointPublicAccess:true,
    endpointPrivateAccess:true,
    publicAccessCidrs:[$cidr]
  }' > "${EKS_CREATE_DIR:?}/vpc-config.json" || exit 1
```

### 4. 创建 EKS 集群

对 `aws eks create-cluster` 使用 `--kubernetes-version`；`--version` 显示的是 AWS CLI 版本。API JSON 字段仍为 `version`。此示例会禁用自动向创建者授予管理员权限，启用五种控制平面日志类型，并引导创建常规核心附加组件。CLI 引导创建的附加组件由用户自行管理；若要将其改为 EKS 托管附加组件，需要单独执行兼容版本/配置流程。

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks create-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --kubernetes-version 1.36 --role-arn "${EKS_CLUSTER_ROLE_ARN:?}" \
  --resources-vpc-config "file://${EKS_CREATE_DIR:?}/vpc-config.json" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --bootstrap-self-managed-addons \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query cluster --output json > "$EKS_CREATE_DIR/created-cluster.json" || exit 1
aws eks wait cluster-active --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" || exit 1
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version,vpc:resourcesVpcConfig}'
```

等待命令失败并不能证明所有资源都已回滚。继续操作之前，请检查集群状态和已保存的响应。本操作会产生 CloudWatch 日志费用。

### 5. 创建节点 IAM 角色

创建一个信任 EC2 的新角色。`AmazonEC2ContainerRegistryPullOnly` 提供镜像拉取权限。对于此简单的 **IPv4 实验**，CNI 权限放在节点角色上，以便已引导创建的 VPC CNI 正常工作。在支持的情况下，优先使用专用的 CNI IRSA/Pod Identity 角色；仅在该配置生效后才移除回退权限。不要把其他应用程序或控制器的 AWS 权限放到每个节点上。

```bash
cat > "${EKS_CREATE_DIR:?}/node-trust.json" << 'EOF'
{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Principal":{"Service":"ec2.amazonaws.com"},
    "Action":"sts:AssumeRole"
  }]
}
EOF
aws iam create-role --role-name "${NEW_NODE_ROLE_NAME:?Unused role name}" \
  --assume-role-policy-document "file://$EKS_CREATE_DIR/node-trust.json" \
  --query Role --output json > "$EKS_CREATE_DIR/created-node-role.json" || exit 1
EKS_NODE_ROLE_ARN=$(jq -er '.Arn' "$EKS_CREATE_DIR/created-node-role.json") || exit 1
aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy || exit 1
aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly || exit 1
# Simple IPv4 lab fallback only. Prefer a dedicated CNI workload role in production.
aws iam attach-role-policy --role-name "$NEW_NODE_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy || exit 1
```

### 6. 创建节点组

在经过审核的私有子网中创建托管节点组。EKS 会为所选 AL2023 AMI 提供节点初始化配置，并创建托管节点访问条目。此示例不设置 SSH 访问或自定义启动模板覆盖。

```bash
aws eks create-nodegroup --cluster-name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" \
  --nodegroup-name "${NEW_NODEGROUP_NAME:?}" --node-role "${EKS_NODE_ROLE_ARN:?}" \
  --subnets "${EKS_PRIVATE_SUBNET_A:?}" "${EKS_PRIVATE_SUBNET_B:?}" \
  --ami-type AL2023_x86_64_STANDARD --instance-types m5.large --capacity-type ON_DEMAND \
  --disk-size 80 --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --query nodegroup --output json > "${EKS_CREATE_DIR:?}/created-nodegroup.json" || exit 1
aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --nodegroup-name "$NEW_NODEGROUP_NAME" || exit 1
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --nodegroup-name "$NEW_NODEGROUP_NAME" \
  --query 'nodegroup.{status:status,health:health,ami:amiType,release:releaseVersion}'
```

### 7. 配置 kubeconfig

使用当前登录身份获准代入的现有操作员 IAM 角色。预置身份必须获准创建 EKS 访问条目并关联实验访问策略。这些命令会授予该集群的 Kubernetes 管理权限，而非整个 AWS 账户的管理员权限。

```bash
# The named operator gets cluster-admin only on this training cluster.
aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" \
  --principal-arn "${OPERATOR_ROLE_ARN:?}" --type STANDARD || exit 1
aws eks associate-access-policy --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --principal-arn "$OPERATOR_ROLE_ARN" \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy \
  --access-scope type=cluster || exit 1
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --role-arn "$OPERATOR_ROLE_ARN" --kubeconfig "${EKS_KUBECONFIG:?}" \
  --alias "$EKS_CLUSTER_NAME" || exit 1
```

### 8. 验证集群

检查预期使用的上下文、节点就绪情况和系统 Pod：

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" config current-context
kubectl --kubeconfig "$EKS_KUBECONFIG" auth can-i get nodes
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$EKS_KUBECONFIG" get pods -n kube-system
```

基础设施状态为 `ACTIVE` 并不能证明应用已经就绪；`get nodes` 的输出必须实际显示健康且处于 Ready 状态的节点。投入生产之前，请验证工作负载调度、DNS、镜像拉取和应用依赖项。本次审核没有进行工作负载性能或可用性测量。

清理时请遵循[已审核的生命周期流程](02-eks-cluster-creation.md#cluster-deletion)：先移除应用程序依赖的云资源，再按适当顺序删除节点组/实例配置文件和集群。只有在依赖资源均已删除后才删除专用实验 VPC，并且只删除实验专用角色。若清理失败，请保留响应文件和资源归属记录。

## 测验

要检验本章所学内容，请尝试 [EKS 集群创建——第 3 部分测验](../quizzes/eks/02-eks-cluster-creation-part3-quiz.md)。

## 参考资料

- [创建 EKS 集群](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html)
- [EKS 网络要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [API 端点访问](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [节点 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
- [默认信封加密](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)
- [EKS 访问条目](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
