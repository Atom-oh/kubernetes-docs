# EKS Auto Mode 入门测验

> **相关文档**: [EKS Auto Mode 入门](../../eks-auto-mode/01-getting-started.md)

## 多项选择题

### 1. 支撑 EKS Auto Mode 的底层技术是什么？

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>显示答案</summary>

**答案: B) Karpenter**

**说明:**
EKS Auto Mode 基于 Karpenter，但运行在 AWS 托管的 control plane 中。用户无需单独安装或配置任何 node 管理组件 - AWS 会管理所有内容。

**EKS Auto Mode 功能:**
- 基于 Karpenter 的自动化 node 管理
- 在 AWS control plane 中运行
- 根据 workload 要求自动选择最佳 instance
- 在数十秒内快速扩缩容

</details>

### 2. 使用 EKS Auto Mode 所需的最低 EKS 版本是多少？

- A) 1.27
- B) 1.28
- C) 1.29
- D) 1.30

<details>
<summary>显示答案</summary>

**答案: C) 1.29**

**说明:**
EKS Auto Mode 仅适用于 EKS 版本 1.29 及以上。

**主要限制:**
- 最低 EKS 版本: 1.29
- 每个 cluster 的最大 NodePools 数: 100
- 每个 NodePool 的最大 nodes 数: 1000
- 每个 cluster 的最大 nodes 数: 5000

</details>

### 3. 使用 eksctl 创建启用了 Auto Mode 的新 cluster 的正确方式是什么？

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>显示答案</summary>

**答案: B) `eksctl create cluster --enable-auto-mode`**

**说明:**
使用 eksctl 0.200.0 或更高版本时，可以使用 `--enable-auto-mode` 标志创建启用了 Auto Mode 的 cluster。

```bash
# Create new cluster with Auto Mode enabled
eksctl create cluster \
    --name my-cluster \
    --region us-west-2 \
    --enable-auto-mode

# Enable Auto Mode on existing cluster
eksctl update cluster \
    --name my-cluster \
    --enable-auto-mode
```

</details>

### 4. Auto Mode 中 node 预置的典型预期时间是多少？

- A) 5-10 秒
- B) 40-90 秒
- C) 3-5 分钟
- D) 10-15 分钟

<details>
<summary>显示答案</summary>

**答案: B) 40-90 秒**

**说明:**
EKS Auto Mode 的 node 预置时间线如下：
- EC2 instance 启动: 10-30 秒
- AMI 启动: 20-40 秒
- kubelet 注册: 5-10 秒
- Pod 调度: 1-5 秒
- **总预期时间: 40-90 秒**

与 AL2023 相比，使用 Bottlerocket AMI 可以实现更快的启动时间。

</details>

### 5. 使用 Terraform 在现有 EKS cluster 上启用 Auto Mode 需要添加哪个 block？

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>显示答案</summary>

**答案: B) `compute_config { enabled = true }`**

**说明:**
使用 Terraform AWS Provider 5.79.0 或更高版本时，使用 `compute_config` block 启用 Auto Mode。

```hcl
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  compute_config {
    enabled       = true
    node_pools    = ["general-purpose", "system"]
    node_role_arn = aws_iam_role.node.arn
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
    subnet_ids = var.subnet_ids
  }
}
```

</details>

### 6. Auto Mode clusters 所需 IAM role 的 trust relationship 中必须允许哪个 service principal？

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>显示答案</summary>

**答案: B) ec2.amazonaws.com**

**说明:**
Auto Mode nodes 使用的 IAM role 必须信任 EC2 service principal，因为 nodes 以 EC2 instances 形式运行。

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

必需的 managed policies:
- `AmazonEKSWorkerNodeMinimalPolicy`
- `AmazonEC2ContainerRegistryPullOnly`

</details>
