# EKS Auto Mode を始めるためのクイズ

> **関連ドキュメント**: [EKS Auto Mode を始める](../../eks-auto-mode/01-getting-started.md)

## 多肢選択問題

### 1. EKS Auto Mode のマネージドコンピューティングプロビジョニングの基盤となる技術は何ですか？

- A) Cluster Autoscaler
- B) Karpenter
- C) AWS Fargate
- D) EC2 Auto Scaling Groups

<details>
<summary>回答を表示</summary>

**回答: B) Karpenter**

**解説:**
Auto Mode は AWS が運用する Karpenter ベースのコントローラーを使用します。Auto Mode 用に別個の Karpenter コントローラーをインストールする必要はありません。引き続き、ワークロードリクエスト、NodePools/NodeClasses、中断制約、およびアプリケーションのオートスケーリングを設定します。インフラストラクチャの自動化によって、アプリケーションの可用性に対する責任が AWS に移ることはありません。

</details>

### 2. 新しい Auto Mode クラスターでは、Kubernetes バージョンをどのように選択すべきですか？

- A) 任意のアップストリーム Kubernetes バージョンが EKS ですぐに利用可能である
- B) 元の機能下限によって現在のサポートが保証されるため、常に 1.29 を使用する
- C) 現在の AWS EKS サポートカレンダーとリージョンでの利用可否を確認する
- D) 常に延長サポートのバージョンを選択する

<details>
<summary>回答を表示</summary>

**回答: C) 現在の AWS EKS サポートカレンダーとリージョンでの利用可否を確認する**

**解説:**
元の 1.29+ 機能下限は、現在のサポートを保証するものではありません。2026 年 10 月 12 日時点で、EKS 1.34～1.37 は標準サポートの対象です。この章では、レビュー済みの 1.36 ベースラインを維持しています。[AWS のバージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)と該当する料金を確認してください。以前の裏付けのない固定 NodePool/node 数に依存するのではなく、適用されるサービスクォータとサブネット容量を確認してください。

</details>

### 3. 新しいクラスターを作成するときに Auto Mode を有効にする eksctl フラグはどれですか？

- A) `eksctl create cluster --auto-mode`
- B) `eksctl create cluster --enable-auto-mode`
- C) `eksctl create cluster --with-auto-mode`
- D) `eksctl create cluster --compute autoMode=enabled`

<details>
<summary>回答を表示</summary>

**回答: B) `eksctl create cluster --enable-auto-mode`**

**解説:**
`--enable-auto-mode` 作成フラグは、確認済みの eksctl 0.229.0 リリースで有効です。この章では、ロールとネットワークを明示するために、`autoModeConfig.enabled`、`nodePools`、`nodeRoleARN` を含むレビュー済み設定ファイルを使用します。

既存の eksctl 管理クラスターでは、`eksctl update auto-mode-config --config-file <reviewed-config>` を使用します。`eksctl update cluster` は非推奨のコントロールプレーンアップグレードコマンドであり、Auto Mode を有効化するコマンドではありません。この機能を有効にするだけのために node-group draining を追加しないでください。[eksctl リファレンス](https://docs.aws.amazon.com/eks/latest/eksctl/auto-mode.html)を参照してください。

</details>

### 4. Auto Mode のプロビジョニング時間について、根拠を持って言える記述はどれですか？

- A) すべての node と Pod は 5～10 秒以内に準備完了となる
- B) 容量、ブートストラップ、イメージプル、スケジューリング制約が準備完了に影響する。ワークロードを測定する
- C) AWS はすべてのプロビジョニングが 5 分以内に完了することを保証する
- D) ACTIVE のコントロールプレーンは、すべてのアプリケーションの準備完了を示す

<details>
<summary>回答を表示</summary>

**回答: B) 容量、ブートストラップ、イメージプル、スケジューリング制約が準備完了に影響する。ワークロードを測定する**

**解説:**
この例には、エンドツーエンドの固定された準備完了保証はありません。node の起動、node の準備完了、アプリケーションの準備完了を区別してください。

以前のクイズでは、EC2 起動 **10～30**、AMI ブート **20～40**、kubelet 登録 **5～10**、スケジューリング **1～5 秒**を含む **40～90 秒**が記載されていました。これらは、測定結果や現在の SLO ではなく、**検証されていない過去の教育用見積もり**としてここに保持されています。この監査では出所を確認できませんでした。Auto Mode はマネージド Bottlerocket バリアントを選択するため、Auto Mode の起動を高速化するために AL2023 と Bottlerocket を選ぶという以前の提案は誤解を招くものでした。

</details>

### 5. Terraform の `aws_eks_cluster` リソースでコンピューティングを設定するブロックはどれですか？

- A) `auto_mode_config { enabled = true }`
- B) `compute_config { enabled = true }`
- C) `karpenter_config { enabled = true }`
- D) `node_config { auto_mode = true }`

<details>
<summary>回答を表示</summary>

**回答: B) `compute_config { enabled = true }`**

**解説:**
このリソースでは `compute_config` を使用しますが、コンピューティングだけでは不十分です。Auto Mode のコンピューティング、ロードバランシング、ブロックストレージを、API ベースのアクセスおよびデフォルトプールに適した node ロールとともに設定する必要があります。このフラグメントは、レビュー済みのロール、プロバイダー、および変数が別の場所で定義されていることを前提としており、スタンドアロンのデプロイではありません。

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

この章では、AWS provider 6.59 以降を必要とし、provider 6.64.0 で検証済みの EKS module 21.25.0 を使用します。その module 入力も `compute_config` という名前です。古い module-v20 の入力 `cluster_compute_config` はリソースブロック名ではありません。適用する前に、保存したプランと必要なロールポリシーを確認してください。

</details>

### 6. Auto Mode **node IAM ロール**が信頼する必要があるサービスプリンシパルはどれですか？

- A) eks.amazonaws.com
- B) ec2.amazonaws.com
- C) eks-auto.amazonaws.com
- D) karpenter.amazonaws.com

<details>
<summary>回答を表示</summary>

**回答: B) ec2.amazonaws.com**

**解説:**
node ロールは EC2 マネージドインスタンスに割り当てられ、`ec2.amazonaws.com` を信頼します。別個の **cluster ロール**は `eks.amazonaws.com` を信頼し、Auto Mode のために `sts:AssumeRole` に加えて `sts:TagSession` を必要とします。

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

node ロールは `AmazonEKSWorkerNodeMinimalPolicy` および `AmazonEC2ContainerRegistryPullOnly` を使用します。アプリケーションの AWS 権限は、たとえば Pod Identity を通じて、別個のワークロードロールに属します。[AWS ロール要件](https://docs.aws.amazon.com/eks/latest/userguide/automode-get-started-cli.html)を参照してください。

</details>
