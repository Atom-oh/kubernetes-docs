# EKS Auto Mode 入門クイズ

> **関連ドキュメント**: [EKS Auto Mode の開始方法](../../eks-auto-mode/01-getting-started.md)

## 選択式問題

### 1. EKS Auto Mode を支える基盤技術は何ですか？

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>答えを表示</summary>

**答え: B) Karpenter**

**解説:**
EKS Auto Mode は Karpenter をベースにしていますが、AWS 管理の control plane 内で実行されます。ユーザーは node 管理コンポーネントを個別にインストールまたは設定する必要はありません。AWS がすべてを管理します。

**EKS Auto Mode の機能:**
- Karpenter ベースの自動 node 管理
- AWS control plane で実行
- workload 要件に基づく最適な instance の自動選択
- 数十秒以内の高速 scaling

</details>

### 2. EKS Auto Mode を使用するために必要な最小 EKS version は何ですか？

- A) 1.27
- B) 1.28
- C) 1.29
- D) 1.30

<details>
<summary>答えを表示</summary>

**答え: C) 1.29**

**解説:**
EKS Auto Mode は EKS version 1.29 以上でのみ利用できます。

**主な制限事項:**
- 最小 EKS version: 1.29
- cluster あたりの最大 NodePools 数: 100
- NodePool あたりの最大 nodes 数: 1000
- cluster あたりの最大 nodes 数: 5000

</details>

### 3. eksctl を使用して Auto Mode を有効にした新しい cluster を作成する正しい方法は何ですか？

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>答えを表示</summary>

**答え: B) `eksctl create cluster --enable-auto-mode`**

**解説:**
eksctl 0.200.0 以降では、`--enable-auto-mode` flag を使用して Auto Mode が有効な cluster を作成できます。

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

### 4. Auto Mode における node provisioning の一般的な想定時間はどれですか？

- A) 5-10 秒
- B) 40-90 秒
- C) 3-5 分
- D) 10-15 分

<details>
<summary>答えを表示</summary>

**答え: B) 40-90 秒**

**解説:**
EKS Auto Mode における node provisioning の timeline は次のとおりです。
- EC2 instance launch: 10-30 秒
- AMI boot: 20-40 秒
- kubelet registration: 5-10 秒
- Pod scheduling: 1-5 秒
- **合計想定時間: 40-90 秒**

Bottlerocket AMI を使用すると、AL2023 と比較してより高速な boot time を実現できます。

</details>

### 5. Terraform を使用して既存の EKS cluster で Auto Mode を有効にするには、どの block を追加する必要がありますか？

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>答えを表示</summary>

**答え: B) `compute_config { enabled = true }`**

**解説:**
Terraform AWS Provider 5.79.0 以降では、`compute_config` block を使用して Auto Mode を有効にします。

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

### 6. Auto Mode clusters に必要な IAM role の trust relationship では、どの service principal を許可する必要がありますか？

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>答えを表示</summary>

**答え: B) ec2.amazonaws.com**

**解説:**
Auto Mode nodes で使用される IAM role は EC2 service principal を信頼する必要があります。これは、nodes が EC2 instances として実行されるためです。

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

必要な managed policies:
- `AmazonEKSWorkerNodeMinimalPolicy`
- `AmazonEC2ContainerRegistryPullOnly`

</details>
