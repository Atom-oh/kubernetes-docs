# EKS Auto Mode 入门测验

> **相关文档**: [EKS Auto Mode 入门](../../eks-auto-mode/01-getting-started.md)

## 选择题

### 1. 哪项技术支撑 EKS Auto Mode 的托管计算预置？

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>显示答案</summary>

**答案: B) Karpenter**

**说明:**
Auto Mode 使用由 AWS 运营的、基于 Karpenter 的控制器。无需为 Auto Mode 安装单独的 Karpenter 控制器。您仍需配置工作负载请求、NodePools/NodeClasses、中断约束和应用程序自动扩缩；基础设施自动化不会将应用程序可用性的责任转移给 AWS。

</details>

### 2. 应如何为新的 Auto Mode 集群选择 Kubernetes 版本？

- A) 任何上游 Kubernetes 版本都会立即在 EKS 中可用
- B) 始终使用 1.29，因为原始功能下限可保证当前支持
- C) 查看当前 AWS EKS 支持日历和区域可用性
- D) 始终选择处于扩展支持期的版本

<details>
<summary>显示答案</summary>

**答案: C) 查看当前 AWS EKS 支持日历和区域可用性**

**说明:**
原始的 1.29+ 功能下限并非当前支持保证。截至 2026 年 10 月 12 日，EKS 1.34–1.37 处于标准支持期；本章保留其经过审查的 1.36 基线。请查看 [AWS 的版本日历](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) 和适用费用。请检查已应用的服务配额和子网容量，而不要依赖先前未经证实的固定 NodePool/节点数量。

</details>

### 3. 创建新集群时，哪个 eksctl 标志可启用 Auto Mode？

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>显示答案</summary>

**答案: B) `eksctl create cluster --enable-auto-mode`**

**说明:**
已验证的 eksctl 0.229.0 版本支持 `--enable-auto-mode` 创建标志。本章使用经过审查的配置文件，其中包含 `autoModeConfig.enabled`、`nodePools` 和 `nodeRoleARN`，以明确角色和网络配置。

对于由现有 eksctl 管理的集群，请使用 `eksctl update auto-mode-config --config-file <reviewed-config>`。`eksctl update cluster` 是一个已弃用的控制平面升级命令，并非 Auto Mode 启用命令。不要仅为启用此功能而排空节点组。请参阅 [eksctl 参考文档](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)。

</details>

### 4. 关于 Auto Mode 预置时间，以下哪项说法站得住脚？

- A) 每个节点和 Pod 都会在 5–10 秒内就绪
- B) 容量、引导启动、镜像拉取和调度约束会影响就绪状态；请测量工作负载
- C) AWS 保证所有预置会在五分钟内完成
- D) ACTIVE 控制平面证明每个应用程序都已就绪

<details>
<summary>显示答案</summary>

**答案: B) 容量、引导启动、镜像拉取和调度约束会影响就绪状态；请测量工作负载**

**说明:**
此示例中没有固定的端到端就绪保证。请区分节点启动、节点就绪和应用程序就绪。

先前的测验列出了 **40–90 秒**，其中 EC2 启动为 **10–30**、AMI 启动为 **20–40**、kubelet 注册为 **5–10**，调度为 **1–5 秒**。这些数据在此作为**未经验证的历史教学估算**予以保留，而非测量结果或当前 SLO；在本次审计中无法确定其来源。Auto Mode 会选择其托管的 Bottlerocket 变体，因此先前关于为加快 Auto Mode 启动而在 AL2023 和 Bottlerocket 之间进行选择的建议具有误导性。

</details>

### 5. Terraform `aws_eks_cluster` 资源中哪个块用于配置计算？

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>显示答案</summary>

**答案: B) `compute_config { enabled = true }`**

**说明:**
该资源使用 `compute_config`，但仅配置计算还不够：必须同时配置 Auto Mode 计算、负载均衡和块存储，并为默认池配置基于 API 的访问方式和合适的节点角色。此片段假定已在其他位置定义经过审查的角色、provider 和变量；它不是独立部署。

```hcl
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.auto_cluster_role_arn
  version  = "1.36"

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true # Dedicated lab only.
  }
  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = var.auto_node_role_arn
  }
  kubernetes_network_config {
    elastic_load_balancing {
      enabled = true
    }
  }
  storage_config {
    block_storage {
      enabled = true
    }
  }
  vpc_config {
    subnet_ids              = var.private_subnet_ids
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = [var.api_client_cidr]
  }
}
```

本章使用 EKS 模块 21.25.0，该模块需要 AWS provider 6.59 或更高版本，并已验证 provider 6.64.0。其模块输入也名为 `compute_config`；较旧的 module-v20 输入 `cluster_compute_config` 并非资源块名称。应用前请审查已保存的计划和所需的角色策略。

</details>

### 6. Auto Mode **节点 IAM 角色**必须信任哪个服务主体？

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>显示答案</summary>

**答案: B) ec2.amazonaws.com**

**说明:**
节点角色分配给 EC2 托管实例，并信任 `ec2.amazonaws.com`。独立的**集群角色**信任 `eks.amazonaws.com`，并且 Auto Mode 除了需要 `sts:AssumeRole` 外，还需要 `sts:TagSession`。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

节点角色使用 `AmazonEKSWorkerNodeMinimalPolicy` 和 `AmazonEC2ContainerRegistryPullOnly`。应用程序 AWS 权限应属于单独的工作负载角色，例如通过 Pod Identity。请参阅 [AWS 角色要求](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)。

</details>
