# Introduction to EKS

> **Supported Versions**: Amazon EKS 1.31, 1.32, 1.33 **最終更新**: February 21, 2026

Amazon Elastic Kubernetes Service (EKS) は、AWS 上で Kubernetes を実行するための managed service（マネージドサービス）です。この章では、EKS の基本概念、アーキテクチャ、および標準の Kubernetes との違いについて説明します。

## EKS and Kubernetes

EKS は、標準の Kubernetes API を提供する managed service です。Kubernetes の基本概念と運用に関する詳細については、[Introduction to Kubernetes](../basics/04-kubernetes-introduction.md) ドキュメントを参照してください。

### Key Benefits of EKS

1. **Managed Control Plane**: AWS が Kubernetes control plane の可用性とスケーラビリティを管理します
2. **Enhanced Security**: AWS IAM との統合による認証と認可
3. **AWS Service Integration**: 他の AWS services（ELB、ECR、IAM など）とのシームレスな統合
4. **Various Compute Options**: EC2、Fargate、Bottlerocket など、複数の compute options をサポート
5. **Auto Scaling**: Cluster Autoscaler、Karpenter などによる auto scaling のサポート
6. **Managed Node Groups**: 自動化された node ライフサイクル管理

## EKS Architecture and Components

Amazon EKS の全体的なアーキテクチャは次のとおりです。

### Control Plane

EKS は高可用性の control plane を提供します。control plane は複数の availability zones にまたがって稼働し、次のコンポーネントで構成されます。

* **API Server**: Kubernetes API を公開し、cluster とのやり取りを処理します。
* **etcd**: cluster state を保存する分散 key-value store です。
* **Controller Manager**: cluster state を管理する controllers を実行します。
* **Scheduler**: pods を nodes に割り当てます。

EKS では、これらの control plane components は AWS によって管理されるため、ユーザーが直接管理する必要はありません。

### Data Plane

EKS data plane は、次のオプションで構成できます。

1. **Managed Node Groups**: AWS が node lifecycle を管理する、EC2 instances で構成される node groups。
2. **Self-Managed Nodes**: ユーザーが直接管理する EC2 instances。
3. **AWS Fargate**: containers を実行するためのインフラストラクチャ管理を不要にする serverless compute engine。

### Networking

EKS は Amazon VPC CNI plugin を使用して pod networking を提供します。この plugin は各 pod に VPC IP addresses を割り当て、AWS networking capabilities を利用できるようにします。

## Differences Between Standard Kubernetes and EKS

### Management Responsibility

* **Standard Kubernetes**: ユーザーは control plane と data plane の両方を管理する必要があります。
* **EKS**: AWS が control plane を管理し、ユーザーは data plane のみを管理すればよいです。

### Networking

* **Standard Kubernetes**: さまざまな CNI plugins から選択できます。
* **EKS**: デフォルトでは Amazon VPC CNI が使用され、各 pod に VPC IP address が割り当てられます。

### Load Balancing

* **Standard Kubernetes**: `LoadBalancer` type services を使用するには、別途 controller をインストールする必要があります。
* **EKS**: `LoadBalancer` type services は AWS Network Load Balancer (NLB) を自動的に作成します。Application Load Balancer (ALB) を使用するには、AWS Load Balancer Controller をインストールする必要があります。

### Storage

* **Standard Kubernetes**: さまざまな storage drivers を手動でインストールして設定する必要があります。
* **EKS**: AWS EBS CSI driver がデフォルトで提供され、EFS や FSx など他の AWS storage services 向け drivers も簡単にインストールできます。

## EKS Cost Structure

EKS cluster を運用する際に発生するコストは次のとおりです。

1. **EKS Control Plane Cost**: cluster ごとに時間単位の料金が請求されます。
2. **Compute Costs**:
   * EC2 instances（managed または self-managed nodes）
   * Fargate（pod の実行時間とリソース使用量に基づいて課金）
3. **Storage Costs**: EBS、EFS、FSx などの storage services のコスト
4. **Network Costs**: data transfer と load balancer の使用コスト

### Cost Optimization Strategies

1. **Use Spot Instances**: コストを最大 90% 削減できます。
2. **Leverage Fargate**: 使用率の低い workloads に適しています。
3. **Configure Auto Scaling**: 必要に応じて nodes を自動的に増減します。
4. **Locality Routing**: traffic を同じ availability zone 内に維持して network costs を削減します。
5. **EKS Auto Mode**: 自動的な cluster scaling によってコストを最適化します。
6. **Hybrid Nodes**: さまざまな instance types を組み合わせることでコスト効率を高めます。

## Integration with AWS Services

EKS は次の AWS services と統合されます。

![EKS AWS Services Integration](../.gitbook/assets/eks_aws_services_integration.png)

1. **IAM**: Kubernetes RBAC と統合して認証と認可を管理します。
2. **VPC**: networking infrastructure を提供します。
3. **CloudWatch**: monitoring と logging を提供します。
4. **ALB/NLB**: load balancing を提供します。
5. **ECR**: container image registry を提供します。
6. **EBS/EFS/FSx**: persistent storage を提供します。
7. **AWS App Mesh**: service mesh capabilities を提供します。
8. **AWS Certificate Manager**: SSL/TLS certificates を管理します。
9. **AWS Secrets Manager**: 機密情報を安全に保存および管理します。
10. **AWS SageMaker**: machine learning workloads を実行します。
11. **AWS Bedrock**: generative AI models を活用します。

## EKS Best Practices

1. **Cluster Design**:
   * 複数の availability zones に nodes をデプロイする
   * 適切な instance types を選択する
   * node group strategy を確立する
2. **Security**:
   * 最小権限の原則を適用する
   * network policies を実装する
   * pod security policies を適用する
   * image scanning と vulnerability management
3. **Networking**:
   * 適切な subnet design
   * security group configuration
   * Locality Routing を活用する
4. **Monitoring and Logging**:
   * CloudWatch Container Insights を有効にする
   * control plane logging を設定する
   * Prometheus と Grafana を活用する
5. **Upgrade Strategy**:
   * 定期的な upgrades を計画する
   * blue/green deployment strategy を検討する
   * upgrades 前に testing を実施する

## Quiz

この章で学んだ内容を確認するには、[Amazon EKS Introduction Quiz](../quizzes/eks/01-eks-introduction-quiz.md) に挑戦してください。
