# EKS Auto Mode Getting Started Quiz

> **Related Document**: [Getting Started with EKS Auto Mode](../../eks-auto-mode/01-getting-started.md)

## Multiple Choice Questions

### 1. What technology underpins EKS Auto Mode's managed compute provisioning?

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>Show Answer</summary>

**Answer: B) Karpenter**

**Explanation:**
Auto Mode uses Karpenter-based controllers operated by AWS. You do not install a separate Karpenter controller for Auto Mode. You still configure workload requests, NodePools/NodeClasses, disruption constraints and application autoscaling; infrastructure automation does not transfer responsibility for application availability to AWS.

</details>

### 2. How should you choose the Kubernetes version for a new Auto Mode cluster?

- A) Any upstream Kubernetes version is immediately available in EKS
- B) Always use 1.29 because the original feature floor guarantees current support
- C) Check the current AWS EKS support calendar and regional availability
- D) Always select a version in extended support

<details>
<summary>Show Answer</summary>

**Answer: C) Check the current AWS EKS support calendar and regional availability**

**Explanation:**
The original 1.29+ feature floor is not a current support guarantee. On September 12, 2026, EKS 1.34–1.36 are in standard support and the chapter uses 1.36. Check [AWS's version calendar](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html) and applicable fees. Check applied service quotas and subnet capacity instead of relying on the former unsubstantiated fixed NodePool/node counts.

</details>

### 3. Which eksctl flag enables Auto Mode when creating a new cluster?

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) `eksctl create cluster --enable-auto-mode`**

**Explanation:**
The `--enable-auto-mode` creation flag is valid in the checked eksctl 0.229.0 release. The chapter uses a reviewed configuration file with `autoModeConfig.enabled`, `nodePools` and `nodeRoleARN` to make roles and networking explicit.

For an existing eksctl-managed cluster, use `eksctl update auto-mode-config --config-file <reviewed-config>`. `eksctl update cluster` is a deprecated control-plane upgrade command, not the Auto Mode enablement command. Do not add node-group draining merely to enable the feature. See the [eksctl reference](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html).

</details>

### 4. Which statement about Auto Mode provisioning time is defensible?

- A) Every node and Pod is ready within 5–10 seconds
- B) Capacity, bootstrap, image pulls and scheduling constraints affect readiness; measure the workload
- C) AWS guarantees all provisioning completes within five minutes
- D) An ACTIVE control plane proves that every application is ready

<details>
<summary>Show Answer</summary>

**Answer: B) Capacity, bootstrap, image pulls and scheduling constraints affect readiness; measure the workload**

**Explanation:**
There is no fixed end-to-end readiness guarantee in this example. Distinguish node launch, node readiness and application readiness.

The previous quiz listed **40–90 seconds** with EC2 launch **10–30**, AMI boot **20–40**, kubelet registration **5–10** and scheduling **1–5 seconds**. These are preserved here as **unverified historical teaching estimates**, not measured results or a current SLO; their provenance could not be established in this audit. Auto Mode selects its managed Bottlerocket variant, so the old suggestion to choose AL2023 versus Bottlerocket for faster Auto Mode boot was misleading.

</details>

### 5. Which block configures compute in the Terraform `aws_eks_cluster` resource?

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>Show Answer</summary>

**Answer: B) `compute_config { enabled = true }`**

**Explanation:**
The resource uses `compute_config`, but compute alone is insufficient: Auto Mode compute, load balancing and block storage must be configured together, with API-based access and a suitable node role for the default pools. This fragment assumes the reviewed roles, provider and variables are defined elsewhere; it is not a standalone deployment.

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

The chapter uses EKS module 21.25.0, which requires AWS provider 6.59 or later, and validated provider 6.64.0. Its module input is also named `compute_config`; the older module-v20 input `cluster_compute_config` is not the resource block name. Review the saved plan and required role policies before applying.

</details>

### 6. Which service principal must the Auto Mode **node IAM role** trust?

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>Show Answer</summary>

**Answer: B) ec2.amazonaws.com**

**Explanation:**
The node role is assigned to EC2 managed instances and trusts `ec2.amazonaws.com`. The separate **cluster role** trusts `eks.amazonaws.com` and requires `sts:TagSession` as well as `sts:AssumeRole` for Auto Mode.

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

The node role uses `AmazonEKSWorkerNodeMinimalPolicy` and `AmazonEC2ContainerRegistryPullOnly`. Application AWS permissions belong in separate workload roles, for example through Pod Identity. See the [AWS role requirements](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html).

</details>
