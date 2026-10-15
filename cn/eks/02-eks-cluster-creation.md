# EKS 集群创建

> **最后更新**: October 12, 2026

创建 Amazon EKS 集群有多种方法。本章将详细学习如何使用不同的工具和方法创建 EKS 集群。

本章中的创建方法互为替代方案。为一个新的专用集群选择一种方法，不要同时使用多个工具管理相同资源。请将示例名称、账户、角色、VPC、子网和 CIDR 替换为已批准的实际值。除非另有说明，Shell 示例使用 Bash；如前置条件失败，请停止操作。本次审计期间未执行 AWS 预置或工作负载测量。

**当前版本：**EKS 1.37 于 2026 年 10 月 1 日可用。

**示例基线：**以下示例保留经过审核的 EKS 1.36 基线。选择其他版本时，请参阅[当前 EKS 版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)和组件兼容性文档。

## 目录

1. [前置条件](#prerequisites)
2. [使用 eksctl 创建集群](#creating-a-cluster-using-eksctl)
3. [使用 AWS Management Console 创建集群](#creating-a-cluster-using-aws-management-console)
4. [使用 AWS CLI 创建集群](#creating-a-cluster-using-aws-cli)
5. [使用 Terraform 创建集群](#creating-a-cluster-using-terraform)
6. [使用 AWS CDK 创建集群](#creating-a-cluster-using-aws-cdk)
7. [配置集群访问](#configuring-cluster-access)
8. [集群验证](#cluster-validation)
9. [集群升级](#cluster-upgrade)
10. [集群删除](#cluster-deletion)

## 前置条件

创建 EKS 集群前，需要满足以下前置条件：

### 1. AWS 账户

需要有效的 AWS 账户。如果您没有 AWS 账户，可以在 [AWS 网站](https://aws.amazon.com/)注册。

### 2. IAM 权限

所需权限取决于工具及其管理的资源。在所有资源上授予 `eks:*`、`ec2:*`、`iam:*` 和 `cloudformation:*` 的策略并非所需的最小权限策略。

| 任务 | 要审核的权限范围 |
| --- | --- |
| EKS 集群/节点组管理 | 所需的 EKS 操作和目标资源 |
| 传递现有 IAM 角色 | 已批准角色 ARN 和服务条件的 `iam:PassRole` |
| 创建 IAM 角色/策略/OIDC 提供商 | 工具管理的 IAM 资源以及名称/标签范围 |
| 创建网络 | 新 VPC、子网和安全组的 EC2 操作 |
| 使用 eksctl/CDK | 相关 CloudFormation 堆栈、执行角色和引导资源 |

预置身份、集群服务角色和节点角色彼此独立。SCP、权限边界和会话策略仍然适用。请根据合成的模板/计划审核组织的预置权限。Auto Mode 角色要求与传统节点组不同。

参考资料：[EKS IAM 操作和资源](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html)、[Auto Mode 角色](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

### 3. 工具安装

#### AWS CLI

选择适合您的 OS/CPU 的软件包，并按照[官方 AWS CLI v2 安装指南](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)进行签名验证。对于现有 v1/v2 安装，请先查看其更新/迁移流程。

| 环境 | 官方软件包/安装方法 |
| --- | --- |
| macOS | 已签名的 `AWSCLIV2.pkg` |
| Linux x86_64 | 带 PGP 签名验证的 `awscli-exe-linux-x86_64.zip` |
| Linux ARM64 | 带 PGP 签名验证的 `awscli-exe-linux-aarch64.zip` |
| Windows | 适用于受支持 Windows 版本的 MSI 安装程序 |

不要在 ARM 上不加修改地使用 Linux x86_64 软件包。使用 `aws --version` 检查活动 CLI。如果您的组织使用 IAM Identity Center，请按如下方式配置已批准的 profile。否则，请遵循其联合身份验证流程，而不是假定使用长期访问密钥。

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

请参阅 [IAM Identity Center 身份验证](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)。后续命令继续使用已批准的账户、角色和区域。

#### kubectl 和 eksctl — Linux/macOS

本章的 EKS 1.36 示例以 kubectl **1.36.4** 和 eksctl **0.230.0** 为基线。应优先使用与服务器相同的 kubectl 次版本；支持的版本偏差为 ±1 个次版本。不要为较旧的 EKS 集群盲目从上游 `stable.txt` 安装最新次版本。

此 Bash 示例会选择 AMD64/ARM64，并在安装前验证官方校验和。它需要 `curl`、`tar`、`awk` 以及 `sha256sum` 或 `shasum`；安装到 `/usr/local/bin` 需要管理员权限。下载或校验和失败将停止安装。

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.4
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.230.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

官方流程：[Linux kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)、[macOS kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)、[eksctl 安装](https://eksctl.io/installation/)。

#### Windows

请在 PowerShell 中遵循[官方 kubectl 安装流程](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)。对于本章的 AMD64 示例，请使用 [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe)及同一路径中的 `.sha256` 文件。从 [eksctl 0.230.0 发布版本](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0)选择与您的 CPU 匹配的 Windows ZIP 和 `eksctl_checksums.txt`。

将 `Get-FileHash -Algorithm SHA256` 与官方哈希值比较，并在不匹配时停止。验证后，解压 ZIP，将可执行文件目录添加到 PATH，并检查 `kubectl version --client` 和 `eksctl version`。不要在 Bash 中运行 PowerShell 语法。

还要为 AWS CLI 示例准备 `jq` 用于生成 JSON。本次审计期间未实际下载/安装客户端或登录。

### 4. VPC 和子网

区域 EKS 集群需要同一 VPC 中不同 AZ 的至少两个子网。每个集群子网至少需要为 EKS 提供六个可用 IP；AWS 建议至少十六个。为节点、Pod、负载均衡器和升级规划额外地址。启用 VPC DNS 主机名和 DNS 解析。

并非每个 EKS 集群都必须访问互联网。节点和工作负载需要通过 NAT/互联网路径或所需的 VPC 端点及镜像，访问 Kubernetes API、镜像和所需 AWS 服务。私有 Kubernetes endpoint 可从具有适当 DNS 和路由的 VPC 或已连接网络访问。

#### EKS 集群的 VPC 标签

`kubernetes.io/cluster/<cluster-name>` VPC 标签是一种旧机制，而非通用的当前 EKS 创建要求。请遵循所选 controller 的子网发现规则来进行负载均衡：

- 公共负载均衡器的子网：`kubernetes.io/role/elb=1`
- 内部负载均衡器的子网：`kubernetes.io/role/internal-elb=1`

标签不会配置路由、安全组或可用 IP 容量。请参阅 [VPC/子网要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)和[无互联网访问的集群](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)。

## 使用 eksctl 创建集群

eksctl 是创建和管理 EKS 集群最简单的方法。eksctl 使用 CloudFormation 创建 EKS 集群及相关资源。

将此 shell 的 eksctl kubeconfig 存储在专用路径。

```bash
EKS_CLIENT_DIR=$(mktemp -d /tmp/eks-client.XXXXXX)
: "${EKS_CLIENT_DIR:?}"
EKS_KUBECONFIG="$EKS_CLIENT_DIR/kubeconfig"
export KUBECONFIG="$EKS_KUBECONFIG"
```

### 基本集群创建

从经过审核的配置文件创建基本集群：

```bash
eksctl create cluster --config-file cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

运行此命令前，请阅读并编辑下面的 `cluster.yaml`。它明确选择 EKS 1.36、AL2023、现有 VPC 子网和节点组容量。将示例标识符和文档 CIDR 替换为实际的已批准值。这些是选定设置，并非关于每个 eksctl 版本默认值的声明。

### 使用配置文件创建集群

对于更复杂的配置，可以使用 YAML 文件定义集群：

```yaml
# cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: '1.36'
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
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
managedNodeGroups:
- name: ng-1
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
  privateNetworking: true
  volumeSize: 80
  volumeType: gp3
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
- name: ng-2
  instanceType: c5.xlarge
  desiredCapacity: 2
  privateNetworking: true
  spot: true
  amiFamily: AmazonLinux2023
  disableIMDSv1: true
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
fargateProfiles:
- name: fp-default
  selectors:
  - namespace: default
    labels:
      env: fargate
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
```

要使用此配置文件创建集群，请运行以下命令：

```bash
eksctl create cluster -f cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

上述配置展示了 EC2 节点和可选的应用程序 Fargate profile。CoreDNS 保留在 EC2 上；将其移至 Fargate 需要同时审核 CoreDNS 计算设置和该 profile。

### 创建托管节点组

要向现有集群添加托管节点组，请运行以下命令：

```bash
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking
```

或者，您可以使用配置文件：

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
  amiFamily: AmazonLinux2023
  privateNetworking: true
  disableIMDSv1: true
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

### 创建 EKS Auto Mode 集群

EKS Auto Mode 于 2024 年全面推出，并自动化 Kubernetes 集群基础设施以降低运维开销。AWS 管理其计算、网络和存储功能。

#### EKS Auto Mode 的主要功能

- **自动节点管理**：根据工作负载要求自动添加/删除节点
- **增强的安全性**：不可变 AMI、SELinux enforcing mode、只读根文件系统
- **节点维护**：节点会因到期和漂移而被替换。二十一天并非 control plane 次版本升级周期
- **集成组件**：默认提供 Pod 网络、DNS、存储和 GPU 支持
- **成本优化**：自动终止未使用实例并整合工作负载

#### 基本 Auto Mode 集群创建

先审核以下 `auto-cluster.yaml` 中的 CIDR 和网络。不要使用自行管理的 add-on 重复配置 Auto Mode 的网络、DNS 和块存储。混合集群需要为每种计算类型明确放置位置和组件范围。

```bash
eksctl create cluster --config-file auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### 使用配置文件创建 Auto Mode 集群

```yaml
# auto-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-auto-cluster
  region: us-west-2
  version: '1.36'
autoModeConfig:
  enabled: true
  nodePools:
  - system
  - general-purpose
vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: Single
  clusterEndpoints:
    privateAccess: true
    publicAccess: true
  publicAccessCIDRs:
  - 203.0.113.10/32
cloudWatch:
  clusterLogging:
    enableTypes:
    - api
    - audit
    - authenticator
    - controllerManager
    - scheduler
accessConfig:
  authenticationMode: API
```

创建集群：
```bash
eksctl create cluster -f auto-cluster.yaml --kubeconfig "${EKS_KUBECONFIG:?}"
```

#### Auto Mode 与传统方法比较

| 功能 | 传统 EKS | EKS Auto Mode |
|---------|-----------------|---------------|
| 节点管理 | 托管节点组或客户管理的节点 | AWS 管理的节点生命周期 |
| 扩缩容 | 配置 Cluster Autoscaler、自行管理的 Karpenter 或其他策略 | 托管节点自动扩缩容 |
| 升级 | 规划 control plane、节点和 add-on 更新 | AWS 管理节点/组件更新；根据支持策略规划 control plane 次版本 |
| 安全性 | 用户配置 | 默认增强安全性 |
| 网络 | CNI plugin 设置 | 自动网络配置 |
| 存储 | 需要安装 CSI 并配置权限 | 托管 EBS provisioner `ebs.csi.eks.amazonaws.com` |
| GPU 支持 | 选择兼容的加速 AMI 和所需 device plugin | 为受支持实例提供托管驱动程序/plugin |

#### Auto Mode 集群验证

集群创建后，您可以使用以下命令检查其状态：

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

#### 创建自定义节点池

在 Auto Mode 中，除默认节点池外，您还可以创建自定义节点池：

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
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.2xlarge
        - p3.8xlarge
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 336h
      taints:
      - key: nvidia.com/gpu
        value: present
        effect: NoSchedule
  limits:
    cpu: '1000'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

> **注意**：在 Auto Mode 中，不能使用 `EC2NodeClass`、`amiFamily` 或自定义 `userData` (`/etc/eks/bootstrap.sh`)。AWS 管理节点 AMI 和 bootstrap；子网、安全组和临时存储则通过 `eks.amazonaws.com/v1` `NodeClass` 定义。

GPU 示例保留 p3，它位于当前官方支持列表中。请检查 AZ 容量、配额以及 GPU 内存/型号要求。GPU Pod 必须请求 `nvidia.com/gpu` 并容忍上述 taint。此 YAML 已经过审核；未预置或基准测试 GPU 节点。

#### Auto Mode 限制

- 无法通过 SSH 或 SSM 直接访问节点
- 默认到期时间为 336 小时（14 天），支持的 `expireAfter` 设置最长为 21 天。请一并审核 draining、PDB/NodePool 阻塞因素和默认的 24 小时终止宽限期
- 无法修改默认节点池和节点类
- 某些实例类型可能存在限制

#### Auto Mode 监控

托管基础设施不会自动配置每个工作负载的 CloudWatch 指标。`cluster_node_count` 属于 **ContainerInsights**，而不是 `AWS/EKS`，并且需要已配置的 Container Insights 收集管道。请为您的环境配置收集并查询含有实际数据的时间范围。

```bash
# Requires a configured Container Insights collection pipeline and metric data.
aws cloudwatch list-metrics --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights --metric-name cluster_node_count \
  --dimensions Name=ClusterName,Value="$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --start-time "${METRICS_START_TIME:?Set a reviewed ISO8601 start time}" \
  --end-time "${METRICS_END_TIME:?Set a later ISO8601 end time}" \
  --period 3600 --statistics Average
```

空结果不能证明节点数为零或 Auto Mode 发生故障。请先检查收集、维度和时间范围。本次审计未运行 CloudWatch 查询或测量。请参阅[官方 Container Insights 指标目录](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### 创建 Fargate profile

要创建 Fargate profile，请运行以下命令：

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-fargate-profile \
  --namespace default \
  --labels env=fargate
```

或者，您可以使用配置文件：

```yaml
# fargate.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: my-fargate-profile
  selectors:
  - namespace: default
    labels:
      env: fargate
```

```bash
eksctl create fargateprofile -f fargate.yaml
```

### 更新集群

审核 control plane、节点和 add-on 兼容性，然后遵循[集群升级](#cluster-upgrade)。

### 删除集群

审核工作负载、负载均衡器、数据保留和所属工具，然后遵循[集群删除](#cluster-deletion)。


## 使用 AWS Management Console 创建集群

使用 AWS Management Console 创建 EKS 集群的步骤如下：

1. 登录 [AWS Management Console](https://console.aws.amazon.com/)。
2. 搜索“EKS”，或从服务列表中选择“Elastic Kubernetes Service”。
3. 在“Clusters”页面上，单击“Create cluster”按钮。

### 创建 EKS Auto Mode 集群（快速配置）

EKS Auto Mode 可减少基础设施设置。工作负载身份、网络、容量、可用性和恢复仍需进行明确配置和验证。

#### 1. 选择快速配置

4. 确保已选择“Quick configuration”选项。
5. 输入以下信息：
   - **Cluster name**：输入集群的唯一名称。
   - **Kubernetes version**：选择要使用的 Kubernetes 版本（建议使用最新版本）。

#### 2. 配置 IAM 角色

6. **Cluster IAM role** 选择：
   - 对于第一个 Auto Mode 集群，请使用“Create recommended role”选项。
   - 如果已有角色，可以重复使用它。
   - 建议的角色名称：`AmazonEKSAutoClusterRole`

7. **Node IAM role** 选择：
   - 对于第一个 Auto Mode 集群，请使用“Create recommended role”选项。
   - 建议的角色名称：`AmazonEKSAutoNodeRole`

#### 3. 配置网络

8. **选择 VPC**：
   - 创建新 VPC：选择“Create VPC”选项为 EKS 创建新的 VPC。
   - 使用现有 VPC：选择此前创建的 EKS VPC。

9. **子网配置**（可选）：
   - EKS Auto Mode 会自动选择 VPC 中的私有子网。
   - 可以根据需要添加或删除子网。

#### 4. 审核配置并创建

10. 选择 **View quick configuration defaults** 以审核所有配置值。
11. 单击 **Create cluster**。（创建集群大约需要 15 分钟）

### 使用自定义配置创建集群

如果需要更精细的控制，可以使用自定义配置。

### 集群配置

4. 在“Configure cluster”页面上，输入以下信息：
   - **Cluster name**：输入集群的唯一名称。
   - **Kubernetes version**：选择要使用的 Kubernetes 版本。
   - **Cluster service role**：创建新角色或选择现有角色。
   - **EKS Auto Mode**：选中复选框以启用 Auto Mode。
   - **Tags**：如有需要，添加标签。
   - 单击“Next”按钮。

### 指定网络

5. 在“Specify networking”页面上，输入以下信息：
   - **VPC**：创建新 VPC 或选择现有 VPC。
   - **Subnets**：选择要用于集群的子网。至少 2 个子网必须位于不同的可用区。
   - **Security groups**：选择要用于集群的安全组。
   - **Cluster endpoint access**：配置对集群 API server endpoint 的访问。
     - **Public**：可从互联网访问 API server。
     - **Private**：从 VPC 或已连接网络访问需要适当的 DNS 和路由。
     - **Public and Private**：可从互联网和 VPC 内部访问 API server。
   - 单击“Next”按钮。

### 配置日志记录

6. 在“Configure logging”页面上，输入以下信息：
   - **Control plane logging**：选择要启用的日志类型。
     - API server 日志
     - 审计日志
     - Authenticator 日志
     - Controller manager 日志
     - Scheduler 日志
   - 单击“Next”按钮。

### 选择 Add-on

以下 add-on 描述传统计算。Auto Mode 管理重叠的网络、DNS 和块存储功能；请根据集群中的计算类型选择组件。

7. 在“Select add-ons”页面上，输入以下信息：
   - **Amazon VPC CNI**：用于 Pod 网络的 CNI plugin。
   - **CoreDNS**：集群内的 DNS 服务。
   - **kube-proxy**：提供网络代理和负载均衡。
   - **Storage/networking add-ons**：传统计算需要安装适当组件和 IAM 权限。Auto Mode 提供托管 EBS/网络/DNS 功能；不要在 Auto Mode 节点上安装重叠组件。
   - 单击“Next”按钮。

### 审核并创建

8. 在“Review and create”页面上，审核配置并单击“Create”按钮。

### 为非 Auto Mode 集群添加节点组

对于传统 EC2 计算，请在创建集群后添加节点组。其他受支持选项（如 Fargate profile）具有各自的设置；并非每个非 Auto Mode 集群都必须使用托管节点组。

### 添加节点组

1. 在“Node group configuration”页面上，输入以下信息：
   - **Node group name**：输入节点组的唯一名称。
   - **Node IAM role**：创建新角色或选择现有角色。
   - 单击“Next”按钮。

2. 在“Set compute and scaling configuration”页面上，输入以下信息：
   - **AMI type**：选择要用于节点的 AMI 类型。
   - **Instance type**：选择要用于节点的 EC2 实例类型。
   - **Disk size**：指定节点的磁盘大小。
   - **Node count**：指定节点的最小、最大和所需数量。
   - 单击“Next”按钮。

3. 在“Specify networking”页面上，输入以下信息：
   - **Subnets**：选择要用于节点组的子网。
   - **Remote access configuration**：除非已批准的管理路径要求，否则保持 SSH 禁用；未审核源安全组时不要指定 SSH key。
   - 单击“Next”按钮。

4. 在“Review and create”页面上，审核配置并单击“Create”按钮。

## 使用 AWS CLI 创建集群

这些示例会创建一个**新集群**。请选择 Auto Mode 或传统 EKS；不要使用相同名称连续运行两个创建命令。请使用 Bash、`jq`、当前 AWS CLI v2 和已授权的 AWS 角色。EKS 1.36 是已验证的示例版本；选择其他版本前，请审核区域支持和兼容性。

两个子网必须位于同一 VPC 的不同 AZ。请分别准备 DNS、空闲 IP、安全组和节点对镜像/服务的访问。实际 API 字段名为 `endpointPrivateAccess` 和 `endpointPublicAccess`。创建者管理员访问将引导此专用示例；请通过 access entry 管理后续访问。

### 准备通用输入

为选定模式预先创建集群角色，并验证所需的 `iam:PassRole` 和 service-linked role 创建权限。执行创建命令前，请审核账户、区域、子网和已批准 CIDR。

```bash
: "${EKS_CLUSTER_NAME:?Choose a unique new cluster name}"
: "${EKS_REGION:?Choose the intended AWS region}"
: "${EKS_CLUSTER_ROLE_ARN:?Pre-created cluster role for the chosen mode}"
: "${EKS_SUBNET_A:?Existing subnet in the intended VPC}"
: "${EKS_SUBNET_B:?Existing subnet in a different AZ of the same VPC}"
: "${EKS_PUBLIC_API_CIDR:?Approved client CIDR, normally /32}"
EKS_CREATION_DIR=$(mktemp -d /tmp/eks-create.XXXXXX)
: "${EKS_CREATION_DIR:?}"
EKS_KUBECONFIG="$EKS_CREATION_DIR/kubeconfig"
unset EKS_CREATED_CLUSTER_ARN
aws sts get-caller-identity
```

### 创建 EKS Auto Mode 集群

集群角色需要针对 `eks.amazonaws.com` 的 `sts:AssumeRole` 和 `sts:TagSession` 信任关系，以及 `AmazonEKSClusterPolicy`、`AmazonEKSComputePolicy`、`AmazonEKSBlockStoragePolicyV2`、`AmazonEKSLoadBalancingPolicy` 和 `AmazonEKSNetworkingPolicy`，或等效的自定义权限。

节点角色信任 `ec2.amazonaws.com`，并使用 `AmazonEKSWorkerNodeMinimalPolicy` 加 `AmazonEC2ContainerRegistryPullOnly`。请通过 Pod Identity/IRSA 单独授予工作负载 AWS 权限。请同时启用计算、负载均衡和块存储，并禁用默认自行管理 add-on 的 bootstrap。

```bash
: "${EKS_AUTO_NODE_ROLE_ARN:?Pre-created Auto Mode node role}"
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  --arg nodeRole "$EKS_AUTO_NODE_ROLE_ARN" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: false,
  computeConfig: {
    enabled: true, nodePools: ["system", "general-purpose"], nodeRoleArn: $nodeRole
  },
  kubernetesNetworkConfig: {ipFamily: "ipv4", elasticLoadBalancing: {enabled: true}},
  storageConfig: {blockStorage: {enabled: true}}
}' > "${EKS_CREATION_DIR:?}/create-auto.json"
cat "$EKS_CREATION_DIR/create-auto.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-auto.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 验证创建和访问

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

在工作负载需要节点前，Auto Mode 可能没有节点。检查 NodePool/NodeClass 状态和后续 Pod 调度。集群 `ACTIVE` 并不能证明应用程序健康，也不能保证固定的创建时长。

```bash
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodepools.karpenter.sh
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodeclasses.eks.amazonaws.com
```

### 创建传统集群

仅当未选择 Auto Mode 时才使用此替代方案。集群角色需要传统 EKS 集群权限；EC2 节点角色以及 CNI/add-on 权限是独立的。引导默认网络 add-on 不会安装 EBS CSI 或 AWS LBC。

```bash
jq -n \
  --arg name "${EKS_CLUSTER_NAME:?}" \
  --arg role "${EKS_CLUSTER_ROLE_ARN:?}" \
  --arg subnetA "${EKS_SUBNET_A:?}" --arg subnetB "${EKS_SUBNET_B:?}" \
  --arg cidr "${EKS_PUBLIC_API_CIDR:?}" \
  '{
  name: $name,
  version: "1.36",
  roleArn: $role,
  resourcesVpcConfig: {
    subnetIds: [$subnetA, $subnetB],
    endpointPrivateAccess: true,
    endpointPublicAccess: true,
    publicAccessCidrs: [$cidr]
  },
  accessConfig: {authenticationMode: "API", bootstrapClusterCreatorAdminPermissions: true},
  logging: {clusterLogging: [{
    types: ["api", "audit", "authenticator", "controllerManager", "scheduler"],
    enabled: true
  }]},
  tags: {"docs-lab": $name}
} + {
  bootstrapSelfManagedAddons: true,
  kubernetesNetworkConfig: {ipFamily: "ipv4"}
}' > "${EKS_CREATION_DIR:?}/create-standard.json"
cat "$EKS_CREATION_DIR/create-standard.json"
EKS_CREATED_CLUSTER_ARN=$(aws eks create-cluster --region "${EKS_REGION:?}" \
  --cli-input-json "file://$EKS_CREATION_DIR/create-standard.json" \
  --query cluster.arn --output text)
: "${EKS_CREATED_CLUSTER_ARN:?Creation failed; inspect the error before continuing}"
```

#### 等待创建并配置 kubeconfig

```bash
: "${EKS_CREATED_CLUSTER_ARN:?Create and verify the new cluster first}"
aws eks wait cluster-active --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}"
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query 'cluster.{arn:arn,status:status,version:version}' --output table

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --kubeconfig "${EKS_KUBECONFIG:?}"
kubectl --kubeconfig "$EKS_KUBECONFIG" get nodes
```

#### 创建托管节点组

为 EC2 节点角色准备 worker-node 和 ECR pull 权限，以及独立的 CNI 角色或已审核的节点角色 CNI 权限。不要不加修改地重复使用 Auto Mode 最小节点角色。私有子网还需要 NAT 或所需 VPC 端点。此 AL2023 示例默认不启用 SSH。

```bash
: "${EKS_MANAGED_NODE_ROLE_ARN:?Pre-created conventional EC2 node role}"
: "${EKS_NODEGROUP_NAME:?Unique managed node group name}"
aws eks create-nodegroup \
  --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" \
  --subnets "${EKS_SUBNET_A:?}" "${EKS_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --node-role "$EKS_MANAGED_NODE_ROLE_ARN" \
  --scaling-config minSize=1,maxSize=3,desiredSize=2 \
  --disk-size 20 --region "${EKS_REGION:?}"

aws eks wait nodegroup-active --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
aws eks describe-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
  --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version}' --output json
kubectl --kubeconfig "${EKS_KUBECONFIG:?}" get nodes
```

仅使用 `minSize`/`maxSize` 不会启用基于 Pod 需求的节点扩缩容。检查状态和健康错误，然后根据需要配置 autoscaler。创建失败时，请检查记录的名称/ARN 和相关资源。本次审计未执行这些创建和等待命令。

参考资料：[CreateCluster API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateCluster.html)、[CreateNodegroup API](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)、[Auto Mode IAM 和创建](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。


## 使用 Terraform 创建集群

以下完整示例支持**一个新集群**，并在第一次 apply 前选择 Auto Mode 或传统托管节点组。不要将替代方案作为第二个集群资源追加，也不要在没有迁移计划的情况下切换现有集群。Terraform state 及其 provider lock 文件属于此特定部署。

### EKS Auto Mode 集群 Terraform 配置

保存为 `main.tf`。该示例将 AWS provider 固定为 **6.64.0**，并使用 EKS **1.36**。请明确提供现有私有子网 ID；自定义 `Type=Private` 标签不能可靠地替代对路由和连接性的验证。前置条件会在规划期间检查 VPC/AZ 关系，但不会验证私有路由、服务 endpoint、DNS、IP 容量或负载均衡器子网标签。

Auto Mode 需要同时启用计算、负载均衡和块存储，并设置 `bootstrap_self_managed_addons = false`。集群角色包含 `sts:TagSession` 和全部五项所需策略。IAM attachment 依赖关系会在 EKS 删除托管基础设施期间保留权限。

```hcl
terraform {
  required_version = ">= 1.5.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_partition" "current" {}
data "aws_subnet" "selected" {
  for_each = toset(var.private_subnet_ids)
  id       = each.value
}

locals {
  cluster_policies = var.enable_auto_mode ? toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSComputePolicy",
    "AmazonEKSBlockStoragePolicyV2",
    "AmazonEKSLoadBalancingPolicy",
    "AmazonEKSNetworkingPolicy",
  ]) : toset(["AmazonEKSClusterPolicy"])
  node_policies = var.enable_auto_mode ? toset([
    "AmazonEKSWorkerNodeMinimalPolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    ]) : toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEC2ContainerRegistryPullOnly",
    # Conventional bootstrap baseline; see the CNI role caveat in the text.
    "AmazonEKS_CNI_Policy",
  ])
}

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = var.enable_auto_mode ? ["sts:AssumeRole", "sts:TagSession"] : ["sts:AssumeRole"]
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each   = local.cluster_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["sts:AssumeRole"]
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each   = local.node_policies
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/${each.value}"
  role       = aws_iam_role.node.name
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = false
  }
  bootstrap_self_managed_addons = !var.enable_auto_mode

  compute_config {
    enabled       = var.enable_auto_mode
    node_pools    = var.enable_auto_mode ? ["system", "general-purpose"] : null
    node_role_arn = var.enable_auto_mode ? aws_iam_role.node.arn : null
  }
  kubernetes_network_config {
    ip_family = "ipv4"
    elastic_load_balancing {
      enabled = var.enable_auto_mode
    }
  }
  storage_config {
    block_storage {
      enabled = var.enable_auto_mode
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_api_cidrs
  }
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Keep policies attached until EKS finishes deleting managed infrastructure.
  depends_on = [
    aws_iam_role_policy_attachment.cluster,
    aws_iam_role_policy_attachment.node,
  ]
  lifecycle {
    precondition {
      condition = (
        alltrue([for subnet in data.aws_subnet.selected : subnet.vpc_id == var.vpc_id]) &&
        length(toset([for subnet in data.aws_subnet.selected : subnet.availability_zone])) >= 2
      )
      error_message = "Supply subnets in at least two AZs of the selected VPC."
    }
  }
  tags = var.tags
}

resource "aws_eks_node_group" "standard" {
  count           = var.enable_auto_mode ? 0 : 1
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = aws_eks_cluster.main.version
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"
  instance_types  = ["m5.large"]
  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [aws_iam_role_policy_attachment.node]
  tags       = var.tags
}

resource "aws_eks_access_entry" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = var.operator_role_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "operator" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = aws_eks_access_entry.operator.principal_arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  access_scope {
    type = "cluster"
  }
}

variable "enable_auto_mode" {
  description = "Creation-time choice. Changing an existing cluster requires a separate migration plan."
  type        = bool
  default     = true
}
variable "cluster_name" {
  description = "Unique name for this new cluster."
  type        = string
}
variable "kubernetes_version" {
  description = "EKS-supported minor version; 1.36 is the reviewed example."
  type        = string
  default     = "1.36"
}
variable "region" {
  type = string
}
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition     = length(distinct(var.private_subnet_ids)) >= 2
    error_message = "At least two distinct subnet IDs are required."
  }
}
variable "public_api_cidrs" {
  type = list(string)
  validation {
    condition = length(var.public_api_cidrs) > 0 && alltrue([
      for cidr in var.public_api_cidrs :
      can(cidrhost(cidr, 0)) && cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "Supply reviewed client CIDRs instead of unrestricted public API access."
  }
}
variable "operator_role_arn" {
  description = "Existing approved IAM role allowed to administer this cluster."
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "eks-creation-example"
  }
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}
output "cluster_security_group_id" {
  value = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}
output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}
```

operator access entry 向已批准的 IAM 角色授予集群管理权限；创建者不会自动获得 Kubernetes 管理员访问权限。该 operator role 必须已经存在，并且使用 kubectl 的人员必须能够 assume 它。

传统节点替代方案将 CNI 权限包含在节点角色中，作为初始 bootstrap 基线。这是共享权限边界，而非强化的生产工作负载身份设计。投入生产前，请审核专用 CNI 角色并限制 Pod 对 IMDS 的访问。应用程序 AWS 权限应属于工作负载特定身份；不要将无关 add-on 权限附加到每个节点。

### 运行 Terraform

使用一个新的工作目录和经过身份验证的预置角色。将示例 ID 和文档 CIDR 替换为目标账户的资源和已批准的客户端 CIDR。默认选择 Auto Mode：

```hcl
# terraform.tfvars — replace every example identifier before planning.
cluster_name       = "eks-docs-unique-name"
region             = "us-west-2"
vpc_id             = "vpc-0123456789abcdef0"
private_subnet_ids = ["subnet-0123456789abcdef0", "subnet-1123456789abcdef0"]
public_api_cidrs   = ["203.0.113.10/32"]
operator_role_arn  = "arn:aws:iam::111122223333:role/ApprovedOperator"
enable_auto_mode  = true
```

```bash
# Run in a new directory containing main.tf and the reviewed terraform.tfvars.
terraform init
terraform fmt -check
terraform validate
terraform plan -out=reviewed.tfplan
# Apply only the plan you reviewed for the intended account/region/resources.
terraform apply reviewed.tfplan

: "${EKS_REGION:?Use the same region as terraform.tfvars}"
: "${EKS_OPERATOR_ROLE_ARN:?Use the same operator role as terraform.tfvars}"
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)" \
  --region "$EKS_REGION" --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

在 apply 前，审核 state/backend、拟议的 IAM 和网络更改，以及所有可计费资源。`terraform validate` 无法验证 AWS 账户权限、配额、路由或所选节点是否能运行您的工作负载。节点组扩缩容边界不会安装基于 Pod 需求的 autoscaler。

### 传统 Terraform 配置

对于**新的传统集群**，请使用相同的完整 `main.tf`，并在第一次 plan 前在 `terraform.tfvars` 中设置以下值：

```hcl
enable_auto_mode = false
```

这会禁用全部三项 Auto Mode 功能，引导传统网络 add-on，选择传统 EC2 节点权限，并创建 AL2023 托管节点组。它不会安装 EBS CSI、AWS LBC、Metrics Server 或节点 autoscaler；请单独配置工作负载所需的组件。部署后切换此值会改变基础设施和 IAM，并需要单独的迁移审核。

验证：Terraform **1.15.7** 和已签名的 AWS provider **6.64.0** 以零错误/警告通过了本地 `terraform validate`。**未执行 plan、apply 或 AWS API 调用。**两种模式仍需要部署验证；该示例并不能证明生产就绪。

参考资料：[AWS provider EKS cluster](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_cluster.html.markdown)、[托管节点组](https://github.com/hashicorp/terraform-provider-aws/blob/v6.64.0/website/docs/r/eks_node_group.html.markdown)、[Auto Mode 角色要求](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。


## 使用 AWS CDK 创建集群

对此**新堆栈**示例使用 `aws-cdk-lib/aws-eks-v2`。它会创建原生 `AWS::EKS::Cluster` 和 access entry；无需 Lambda custom resource 即可启用 Auto Mode。不要将已部署的现有 construct 替换为此示例并视为原地迁移。

该示例使用 CDK library **2.269.0**、CLI **2.1141.0** 和 EKS **1.36**。它通过属性导入现有私有子网，而不进行 synthesis-time VPC lookup。部署前请验证所提供的子网/AZ 对应关系、VPC DNS、路由、服务访问和负载均衡器子网标签。导入的 VPC 定义不会验证这些条件。

### 使用 TypeScript 的 EKS Auto Mode 集群

保存为 `lib/eks-auto-mode-stack.ts`。调用方提供现有且已批准的 operator role；只有该角色获得此集群的管理员访问权限。工作负载权限仍然独立。

```typescript
import * as cdk from 'aws-cdk-lib';
import * as eks from 'aws-cdk-lib/aws-eks-v2';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EksAutoModeProps extends cdk.StackProps {
  readonly clusterName: string;
  readonly vpcId: string;
  readonly privateSubnetIds: string[];
  readonly availabilityZones: string[];
  readonly publicApiCidrs: string[];
  readonly operatorRoleArn: string;
}

export class EksAutoModeStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EksAutoModeProps) {
    super(scope, id, props);

    if (props.privateSubnetIds.length < 2 ||
        props.privateSubnetIds.length !== props.availabilityZones.length ||
        new Set(props.availabilityZones).size < 2 ||
        props.publicApiCidrs.length === 0) {
      throw new Error('Supply corresponding private subnets/AZs in at least two AZs and approved API CIDRs');
    }
    const vpc = ec2.Vpc.fromVpcAttributes(this, 'Vpc', {
      vpcId: props.vpcId,
      availabilityZones: props.availabilityZones,
      privateSubnetIds: props.privateSubnetIds,
    });

    const clusterRole = new iam.Role(this, 'ClusterRole', {
      assumedBy: new iam.ServicePrincipal('eks.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSClusterPolicy',
        'AmazonEKSComputePolicy',
        'AmazonEKSBlockStoragePolicyV2',
        'AmazonEKSLoadBalancingPolicy',
        'AmazonEKSNetworkingPolicy',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });
    clusterRole.assumeRolePolicy!.addStatements(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal('eks.amazonaws.com')],
      actions: ['sts:TagSession'],
    }));

    const nodeRole = new iam.Role(this, 'NodeRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        'AmazonEKSWorkerNodeMinimalPolicy',
        'AmazonEC2ContainerRegistryPullOnly',
      ].map(name => iam.ManagedPolicy.fromAwsManagedPolicyName(name)),
    });

    const cluster = new eks.Cluster(this, 'Cluster', {
      clusterName: props.clusterName,
      version: eks.KubernetesVersion.V1_36,
      vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE.onlyFrom(...props.publicApiCidrs),
      defaultCapacityType: eks.DefaultCapacityType.AUTOMODE,
      bootstrapSelfManagedAddons: false,
      bootstrapClusterCreatorAdminPermissions: false,
      // All required policies/trust are defined above. Avoid adding the older
      // BlockStoragePolicy that CDK 2.269.0 otherwise attaches automatically.
      role: clusterRole.withoutPolicyUpdates(),
      compute: {
        nodePools: ['system', 'general-purpose'],
        nodeRole: nodeRole.withoutPolicyUpdates(),
      },
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    cluster.node.addDependency(clusterRole, nodeRole);
    cluster.grantClusterAdmin('OperatorAccess', props.operatorRoleArn);

    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
    new cdk.CfnOutput(this, 'ClusterEndpoint', { value: cluster.clusterEndpoint });
  }
}
```

集群角色显式包含 `sts:TagSession` 和五项 Auto Mode 策略，包括 `AmazonEKSBlockStoragePolicyV2`。`withoutPolicyUpdates()` 阻止 CDK 2.269.0 添加旧的块存储策略；此示例负责提供所有必需权限。依赖关系会在集群删除完成前保留这些角色。节点角色仅具有 Auto Mode 最小 worker 和 ECR pull 策略。

`bootstrapSelfManagedAddons: false` 可避免重叠的自行管理网络 add-on。Auto Mode 会一并管理计算、负载均衡和块存储。operator access entry 与集群执行角色分开创建。

### CDK 应用程序入口点

保存为 `bin/eks-auto-mode.ts`；请将 shebang 保留在第一行。环境值为必需项，以防意外使用示例账户、VPC 或角色值。

```typescript
#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { EksAutoModeStack } from '../lib/eks-auto-mode-stack';

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Set ${name} before synthesis/deployment`);
  return value;
}
function list(name: string): string[] {
  return required(name).split(',').map(value => value.trim()).filter(Boolean);
}
const app = new cdk.App();
new EksAutoModeStack(app, 'EksAutoModeStack', {
  env: {
    account: required('CDK_DEFAULT_ACCOUNT'),
    region: required('CDK_DEFAULT_REGION'),
  },
  clusterName: required('EKS_CLUSTER_NAME'),
  vpcId: required('EKS_VPC_ID'),
  privateSubnetIds: list('EKS_PRIVATE_SUBNET_IDS'),
  availabilityZones: list('EKS_AVAILABILITY_ZONES'),
  publicApiCidrs: list('EKS_PUBLIC_API_CIDRS'),
  operatorRoleArn: required('EKS_OPERATOR_ROLE_ARN'),
});
```

### CDK 部署

创建一个新项目，初始化后保存上述两个文件，并提供目标账户/区域的值。使用已经身份验证且获得授权的 AWS 角色。部署前审核合成的 IAM/网络配置和 diff。CDK library/CLI 是独立的软件包，并不共享相同版本号。

```bash
mkdir eks-auto-mode
cd eks-auto-mode
npx --yes --package aws-cdk@2.1141.0 cdk init app --language typescript
npm install --save-exact aws-cdk-lib@2.269.0 constructs@10.5.0
npm install --save-dev --save-exact aws-cdk@2.1141.0 typescript@5.9.3

# Save the source files above, then set the required environment values.
: "${CDK_DEFAULT_ACCOUNT:?Set the intended AWS account ID}"
: "${CDK_DEFAULT_REGION:?Set the intended AWS region}"
: "${EKS_CLUSTER_NAME:?Use a unique name for this new cluster}"
: "${EKS_VPC_ID:?}"
: "${EKS_PRIVATE_SUBNET_IDS:?Comma-separated existing subnet IDs}"
: "${EKS_AVAILABILITY_ZONES:?Corresponding comma-separated AZs}"
: "${EKS_PUBLIC_API_CIDRS:?Approved client CIDRs, normally /32}"
: "${EKS_OPERATOR_ROLE_ARN:?Existing operator role you may assume}"
# Export the variables so the CDK application receives them.
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION EKS_CLUSTER_NAME EKS_VPC_ID
export EKS_PRIVATE_SUBNET_IDS EKS_AVAILABILITY_ZONES EKS_PUBLIC_API_CIDRS EKS_OPERATOR_ROLE_ARN

npx tsc --noEmit
npx cdk synth
# Bootstrap creates AWS resources; review the account/region and execution policy.
npx cdk bootstrap "aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION"
npx cdk diff
npx cdk deploy

aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$CDK_DEFAULT_REGION" \
  --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig ./kubeconfig
kubectl --kubeconfig ./kubeconfig get nodes
```

本次审计使用虚拟标识符在本地编译了两个 TypeScript 文件并合成堆栈：已验证全部三项 Auto Mode 功能、范围限定的 API CIDR、所需角色和一个 operator access entry。未生成 Lambda/custom resource。缺少必需输入会被拒绝。**未执行 bootstrap、lookup、deploy、集群创建或 AWS API 调用**，因此账户配额、网络和工作负载可用性仍需在部署时检查。

参考资料：[EKS V2 construct library](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_eks_v2-readme.html)、[Auto Mode 集群角色](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)、[Auto Mode 创建](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

## 配置集群访问

设置由所选方法生成的集群名称、区域和专用 kubeconfig 路径。对于 Terraform/CDK 示例，请在 `EKS_OPERATOR_ROLE_ARN` 中设置已批准的 operator role。使用 CLI 创建者访问时可省略它。写入 kubeconfig 不会授予 Kubernetes 权限。

```bash
: "${EKS_CLUSTER_NAME:?Use the selected cluster name}"
: "${EKS_REGION:?Use the selected region}"
: "${EKS_KUBECONFIG:?Set the dedicated kubeconfig path for this method}"
aws sts get-caller-identity
if [[ -n ${EKS_OPERATOR_ROLE_ARN:-} ]]; then
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --role-arn "$EKS_OPERATOR_ROLE_ARN" --kubeconfig "$EKS_KUBECONFIG"
else
  aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
    --kubeconfig "$EKS_KUBECONFIG"
fi
eks_kubectl() {
  kubectl --kubeconfig "${EKS_KUBECONFIG:?}" "$@"
}
eks_kubectl config current-context
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --query cluster.accessConfig.authenticationMode
```

### RBAC 配置

对新的 IAM 访问使用 access entry。此示例向新角色授予现有 `dev` namespace 的只读访问权限；不要重复由创建工具管理的 operator entry。身份验证模式必须是 `API` 或 `API_AND_CONFIG_MAP`。旧版 `aws-auth` 方法已弃用；不要覆盖其整个 ConfigMap。需要时请遵循官方迁移流程。

```bash
# A new reader identity, distinct from the operator already granted by IaC.
: "${EKS_READER_ROLE_ARN:?Existing approved IAM role without an access entry yet}"
if eks_kubectl get namespace dev &&
   aws eks create-access-entry --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --principal-arn "$EKS_READER_ROLE_ARN" \
  --type STANDARD --kubernetes-groups eks-docs-readers; then
EKS_ACCESS_DIR=$(mktemp -d /tmp/eks-access.XXXXXX)
: "${EKS_ACCESS_DIR:?}"
cat > "$EKS_ACCESS_DIR/rbac.yaml" << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: eks-docs-reader
  namespace: dev
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-docs-readers
  namespace: dev
subjects:
- kind: Group
  name: eks-docs-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: eks-docs-reader
  apiGroup: rbac.authorization.k8s.io
EOF
eks_kubectl create -f "$EKS_ACCESS_DIR/rbac.yaml"
fi
```

此 reader role 不授予 Secret API 访问或修改权限。请以该角色进行身份验证并检查 `kubectl auth can-i`；其他 RBAC/EKS policy 授权可能会增加权限。[EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)


## 集群验证

使用 `eks_kubectl` 及访问部分中的同一专用 kubeconfig。仅能访问 control plane 并不能证明节点或工作负载健康。

### 基本验证

```bash
eks_kubectl cluster-info
eks_kubectl get nodes
eks_kubectl get pods -n kube-system
eks_kubectl get events --sort-by='.lastTimestamp'
```

### Auto Mode 特定验证

AWS 管理 Auto Mode provisioning controller。不要期望在 `karpenter` namespace 中存在自行管理的 controller Pod。检查 NodePool/NodeClass 条件和事件，以及需要容量的工作负载对应的 NodeClaim。

```bash
eks_kubectl get nodepools.karpenter.sh
eks_kubectl get nodeclasses.eks.amazonaws.com
eks_kubectl get nodeclaims.karpenter.sh
```

### 部署示例应用程序

使用新 namespace 检查镜像访问、调度、HTTP 就绪状态和 Service。仅 Fargate 的配置首先需要与此 namespace 匹配的 profile。

```bash
EKS_SAMPLE_DIR=$(mktemp -d /tmp/eks-validate.XXXXXX)
: "${EKS_SAMPLE_DIR:?}"
unset EKS_SAMPLE_NAMESPACE EKS_SAMPLE_UID
EKS_SAMPLE_CANDIDATE=$(basename "$EKS_SAMPLE_DIR" | tr '[:upper:].' '[:lower:]-')
if EKS_SAMPLE_UID=$(eks_kubectl create namespace "$EKS_SAMPLE_CANDIDATE" -o jsonpath='{.metadata.uid}'); then
  EKS_SAMPLE_NAMESPACE=$EKS_SAMPLE_CANDIDATE
fi
: "${EKS_SAMPLE_NAMESPACE:?Namespace creation failed}"
: "${EKS_SAMPLE_UID:?Namespace UID missing}"
cat > "$EKS_SAMPLE_DIR/sample-app.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: ${EKS_SAMPLE_NAMESPACE}
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
      automountServiceAccountToken: false
      containers:
      - name: app
        image: nginx:1.30.4-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app-service
  namespace: ${EKS_SAMPLE_NAMESPACE}
spec:
  type: ClusterIP
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: http
EOF
eks_kubectl apply -f "$EKS_SAMPLE_DIR/sample-app.yaml"
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" rollout status deployment/sample-app --timeout=180s
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" get pods,services
eks_kubectl -n "$EKS_SAMPLE_NAMESPACE" port-forward --address 127.0.0.1 service/sample-app-service 8080:80
```

在端口转发运行期间，打开 `http://127.0.0.1:8080`，然后使用 Ctrl-C 停止。此操作检查 ClusterIP 访问，而非外部负载均衡器。对于 NLB，请选择 Auto Mode 的 `eks.amazonaws.com/nlb` 或已安装且已授权的 AWS LBC 的 `service.k8s.aws/nlb`，并另行审核网络/成本前置条件。本次审计未执行部署或端口转发。

## 集群升级

首先审核升级洞察、已删除 API、webhook/add-on 兼容性、节点版本、备用 IP 和恢复计划。将滞后节点提升到当前 control plane 版本，然后每次升级一个受支持的次版本。某些组件需要在 control plane 之前进行兼容更新。

Auto Mode 不会每 21 天升级 control plane 次版本。operator 需要规划次版本升级，并根据版本支持策略考虑自动升级。

```bash
aws eks describe-cluster-versions --region "${EKS_REGION:?}" --output table
aws eks describe-cluster --name "${EKS_CLUSTER_NAME:?}" --region "$EKS_REGION" \
  --query 'cluster.{version:version,status:status}' --output table
eks_kubectl get nodes

# After readiness/compatibility review, choose the next supported minor.
: "${NEXT_MINOR_VERSION:?Select one supported minor step, for example 1.35 to 1.36}"
EKS_UPDATE_ID=$(aws eks update-cluster-version --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --kubernetes-version "$NEXT_MINOR_VERSION" \
  --query update.id --output text)
: "${EKS_UPDATE_ID:?Update request failed}"
aws eks describe-update --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" \
  --update-id "$EKS_UPDATE_ID" --query 'update.{status:status,errors:errors}'

# Alternative interface; do not execute both:
# eksctl upgrade cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" --version "$NEXT_MINOR_VERSION" --approve
```

仅在更新报告 `Successful` 后再继续处理 data plane。AWS 会逐步更新 Auto Mode 节点；传统托管节点组需要单独更新。

```bash
# Conventional managed node group only, after the control plane update is Successful.
aws eks update-nodegroup-version --cluster-name "${EKS_CLUSTER_NAME:?}" \
  --region "${EKS_REGION:?}" --nodegroup-name "${EKS_NODEGROUP_NAME:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
```

根据各自机制规划自行管理/Hybrid Node 更新、Fargate Pod 替换、add-on 更新和 kubectl 更新。检查 PDB 和备用容量，而不要用 force flag 隐藏失败。符合条件的 control plane 升级可在七天内回滚一个次版本，但须受节点/add-on/API 兼容性和支持策略限制；回滚不能替代应用程序数据恢复。

[升级流程](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html) · [回滚条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)

## 集群删除

在目标账户和区域中，通过原始所属工具/state 进行删除。先在 controller 仍运行时移除工作负载和 Ingress/LoadBalancer Service，然后验证完成情况。决定如何保留或恢复 PVC/PV、snapshot 和日志。不要使用 force 选项绕过 timeout 或 finalizer。

### 清理示例 namespace

```bash
EKS_SAMPLE_CLEANUP_OK=true
if [[ -n ${EKS_SAMPLE_NAMESPACE:-} && -n ${EKS_SAMPLE_UID:-} ]]; then
  current_uid=$(eks_kubectl get namespace "$EKS_SAMPLE_NAMESPACE" -o jsonpath='{.metadata.uid}') || current_uid=""
  if [[ "$current_uid" = "$EKS_SAMPLE_UID" ]]; then
    eks_kubectl delete namespace "$EKS_SAMPLE_NAMESPACE" --wait=true --timeout=180s || EKS_SAMPLE_CLEANUP_OK=false
  else
    EKS_SAMPLE_CLEANUP_OK=false
  fi
elif [[ -n ${EKS_SAMPLE_NAMESPACE:-} || -n ${EKS_SAMPLE_UID:-} ]]; then
  EKS_SAMPLE_CLEANUP_OK=false
fi
# Remove local files only after successful sample cleanup.
if [[ "$EKS_SAMPLE_CLEANUP_OK" = true ]]; then
if [[ -n ${EKS_SAMPLE_DIR:-} ]]; then
  rm -f -- "$EKS_SAMPLE_DIR/sample-app.yaml"
  rmdir -- "$EKS_SAMPLE_DIR"
fi
if [[ -n ${EKS_ACCESS_DIR:-} ]]; then
  rm -f -- "$EKS_ACCESS_DIR/rbac.yaml"
  rmdir -- "$EKS_ACCESS_DIR"
fi
else
  printf 'Sample cleanup could not be verified; stop before deleting the cluster\n' >&2
fi
```

如果清理失败，请停止并调查。将目标 ARN 与创建结果或所属 IaC state 进行比较，而不只是未审核的当前 lookup。

```bash
: "${EKS_EXPECTED_CLUSTER_ARN:?Copy the ARN from the creation result or owning IaC state}"
: "${EKS_CLUSTER_NAME:?}"
: "${EKS_REGION:?}"
EKS_DELETE_TARGET_VERIFIED=false
if [[ ${EKS_SAMPLE_CLEANUP_OK:-false} != true ]]; then
  printf 'Complete the sample cleanup check above first\n' >&2
else
current_arn=$(aws eks describe-cluster --name "$EKS_CLUSTER_NAME" \
  --region "$EKS_REGION" --query cluster.arn --output text) || current_arn=""
if [[ "$current_arn" = "$EKS_EXPECTED_CLUSTER_ARN" ]]; then
  EKS_DELETE_TARGET_VERIFIED=true
  aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
else
  printf 'Target mismatch; stop and check the account, region and owning tool\n' >&2
fi
fi
```

### 使用 eksctl 删除

对由 eksctl 创建的集群使用此方法。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  eksctl delete cluster --name "${EKS_CLUSTER_NAME:?}" --region "${EKS_REGION:?}" --wait
fi
```

### 使用 AWS CLI 删除

对于直接使用 CLI 创建的集群，请设置上面列出的所属节点组/profile 名称，并对每个资源重复操作。删除集群前请等待删除完成，并验证没有资源残留。

```bash
# For a cluster created directly with the AWS CLI, after workload/data cleanup.
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  if [[ -n ${EKS_NODEGROUP_NAME:-} ]]; then
    aws eks delete-nodegroup --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION" &&
    aws eks wait nodegroup-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --nodegroup-name "$EKS_NODEGROUP_NAME" --region "$EKS_REGION"
  fi
  if [[ -n ${EKS_FARGATE_PROFILE_NAME:-} ]]; then
    aws eks delete-fargate-profile --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION" &&
    aws eks wait fargate-profile-deleted --cluster-name "$EKS_CLUSTER_NAME" \
      --fargate-profile-name "$EKS_FARGATE_PROFILE_NAME" --region "$EKS_REGION"
  fi
  remaining_nodes=$(aws eks list-nodegroups --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(nodegroups)' --output text) || remaining_nodes=unknown
  remaining_profiles=$(aws eks list-fargate-profiles --cluster-name "$EKS_CLUSTER_NAME" \
    --region "$EKS_REGION" --query 'length(fargateProfileNames)' --output text) || remaining_profiles=unknown
  if [[ "$remaining_nodes" = 0 && "$remaining_profiles" = 0 ]]; then
    aws eks delete-cluster --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION" &&
      aws eks wait cluster-deleted --name "$EKS_CLUSTER_NAME" --region "$EKS_REGION"
  else
    printf 'Owned node groups/Fargate profiles remain, or their status could not be verified\n' >&2
  fi
fi
```

### 使用 Terraform 删除

使用原始配置、backend 和 workspace；仅针对目标资源/账户 apply 已审核的 destruction plan。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  terraform plan -destroy -out=reviewed-destroy.tfplan &&
    terraform apply reviewed-destroy.tfplan
fi
```

### 使用 CDK 删除

使用原始 application、输入、账户和区域，并验证目标 stack。

```bash
if [[ ${EKS_DELETE_TARGET_VERIFIED:-false} = true ]]; then
  npx cdk list
  npx cdk destroy EksAutoModeStack
fi
```

完成后，验证 EKS/CloudFormation 状态以及任何剩余的 ELB、磁盘、NAT、日志和 IAM 资源。在托管基础设施删除完成前保留 Auto Mode 角色/策略。不要假定集群删除会移除属于其他位置的 VPC、IAM 角色、日志或保留的数据。本次审计未执行删除命令。

## 结论

创建 EKS 集群有多种方法，每种都有其优缺点：

- **EKS Auto Mode**：自动化基础设施操作；应用程序就绪状态仍需验证
- **eksctl**：简单快速地创建集群
- **AWS Management Console**：通过 GUI 直观地创建
- **AWS CLI**：适用于脚本自动化
- **Terraform**：将基础设施作为代码进行管理
- **AWS CDK**：使用编程语言定义基础设施

对于生产环境，请选择符合您要求的计算模型和基础设施工具，并验证 IAM、连接性、容量、中断和恢复行为。模板或集群创建成功并不能证明生产就绪。

### 审计验证范围

已阅读两个完整语言版本，并根据官方文档和 schema 进行了检查。验证涵盖 shell/JSON/YAML、CDK 编译/synthesis、Terraform validate 和模拟的失败路径。未执行 AWS 预置、升级、删除、应用程序运行时/负载测试或成本测量。
