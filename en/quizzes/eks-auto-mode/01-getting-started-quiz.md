# EKS Auto Mode Getting Started Quiz

> **Related Document**: [Getting Started with EKS Auto Mode](../../eks-auto-mode/01-getting-started.md)

## Multiple Choice Questions

### 1. What is the underlying technology that powers EKS Auto Mode?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>Show Answer</summary>

**Answer: B) Karpenter**

**Explanation:**
EKS Auto Mode is based on Karpenter, but runs within the AWS-managed control plane. Users don't need to install or configure any node management components separately - AWS manages everything.

**EKS Auto Mode Features:**
- Karpenter-based automated node management
- Runs in AWS control plane
- Automatic optimal instance selection based on workload requirements
- Fast scaling within tens of seconds

</details>

### 2. What is the minimum EKS version required to use EKS Auto Mode?

- A) 1.27
- B) 1.28
- C) 1.29
- D) 1.30

<details>
<summary>Show Answer</summary>

**Answer: C) 1.29**

**Explanation:**
EKS Auto Mode is only available on EKS version 1.29 and above.

**Key Limitations:**
- Minimum EKS version: 1.29
- Maximum NodePools per cluster: 100
- Maximum nodes per NodePool: 1000
- Maximum nodes per cluster: 5000

</details>

### 3. What is the correct way to create a new cluster with Auto Mode enabled using eksctl?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) `eksctl create cluster --enable-auto-mode`**

**Explanation:**
With eksctl 0.200.0 or later, you can use the `--enable-auto-mode` flag to create a cluster with Auto Mode enabled.

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

### 4. What is the typical expected time for node provisioning in Auto Mode?

- A) 5-10 seconds
- B) 40-90 seconds
- C) 3-5 minutes
- D) 10-15 minutes

<details>
<summary>Show Answer</summary>

**Answer: B) 40-90 seconds**

**Explanation:**
The node provisioning timeline for EKS Auto Mode is as follows:
- EC2 instance launch: 10-30 seconds
- AMI boot: 20-40 seconds
- kubelet registration: 5-10 seconds
- Pod scheduling: 1-5 seconds
- **Total expected time: 40-90 seconds**

Using Bottlerocket AMI can achieve faster boot times compared to AL2023.

</details>

### 5. What block needs to be added to enable Auto Mode on an existing EKS cluster using Terraform?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>Show Answer</summary>

**Answer: B) `compute_config { enabled = true }`**

**Explanation:**
With Terraform AWS Provider 5.79.0 or later, use the `compute_config` block to enable Auto Mode.

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

### 6. What service principal must be allowed in the trust relationship of the IAM role required for Auto Mode clusters?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>Show Answer</summary>

**Answer: B) ec2.amazonaws.com**

**Explanation:**
The IAM role used by Auto Mode nodes must trust the EC2 service principal because nodes run as EC2 instances.

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

Required managed policies:
- `AmazonEKSWorkerNodeMinimalPolicy`
- `AmazonEC2ContainerRegistryPullOnly`

</details>
