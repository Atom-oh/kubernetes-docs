# EKS の概要

> **対応バージョン**: Amazon EKS 1.31, 1.32, 1.33 **最終更新**: February 21, 2026

Amazon Elastic Kubernetes Service (EKS) は、AWS 上で Kubernetes を実行するためのマネージドサービスです。この章では、EKS の基本概念、アーキテクチャ、および標準 Kubernetes との違いについて学びます。

## EKS と Kubernetes

EKS は、標準 Kubernetes API を提供するマネージドサービスです。Kubernetes の基本概念と運用に関する詳細は、[Kubernetes の概要](../basics/04-kubernetes-introduction.md)を参照してください。

### EKS の主な利点

1. **マネージド Control Plane**: AWS が Kubernetes control plane の可用性とスケーラビリティを管理します
2. **セキュリティの強化**: AWS IAM との統合による認証と認可
3. **AWS サービスとの統合**: 他の AWS サービス（ELB、ECR、IAM など）とのシームレスな統合
4. **多様なコンピューティングオプション**: EC2、Fargate、Bottlerocket を含む複数のコンピューティングオプションをサポート
5. **Auto Scaling**: Cluster Autoscaler、Karpenter などによる Auto Scaling をサポート
6. **Managed Node Groups**: Node lifecycle の自動管理

## EKS のアーキテクチャとコンポーネント

Amazon EKS の全体アーキテクチャは次のとおりです。

### Control Plane

EKS は高可用性の Control Plane を提供します。Control Plane は複数の Availability Zone にまたがって稼働し、次のコンポーネントで構成されます。

* **API Server**: Kubernetes API を公開し、cluster とのやり取りを処理します。
* **etcd**: cluster の状態を保存する分散 key-value store です。
* **Controller Manager**: cluster の状態を管理する controller を実行します。
* **Scheduler**: Pod を node に割り当てます。

EKS では、これらの Control Plane コンポーネントは AWS によって管理されるため、ユーザーが直接管理する必要はありません。

### Data Plane

EKS Data Plane は、次のオプションで構成できます。

1. **Managed Node Groups**: AWS が node lifecycle を管理する EC2 instance で構成される Node Group。
2. **Self-Managed Nodes**: ユーザーが直接管理する EC2 instance。
3. **AWS Fargate**: container 実行用の infrastructure を管理する必要がない serverless compute engine。

### Networking

EKS は、Pod networking を提供するために Amazon VPC CNI plugin を使用します。この plugin は各 Pod に VPC IP address を割り当て、AWS networking 機能を利用できるようにします。

## 標準 Kubernetes と EKS の違い

### 管理責任

* **標準 Kubernetes**: ユーザーが Control Plane と Data Plane の両方を管理する必要があります。
* **EKS**: AWS が Control Plane を管理し、ユーザーは Data Plane のみを管理すればよいです。

### Networking

* **標準 Kubernetes**: さまざまな CNI plugin から選択できます。
* **EKS**: デフォルトで Amazon VPC CNI が使用され、各 Pod に VPC IP address が割り当てられます。

### Load Balancing

* **標準 Kubernetes**: `LoadBalancer` type の Service を使用するには、別途 controller をインストールする必要があります。
* **EKS**: `LoadBalancer` type の Service は AWS Network Load Balancer (NLB) を自動的に作成します。Application Load Balancer (ALB) を使用するには、AWS Load Balancer Controller をインストールする必要があります。

### Storage

* **標準 Kubernetes**: さまざまな storage driver を手動でインストールおよび設定する必要があります。
* **EKS**: AWS EBS CSI driver がデフォルトで提供され、EFS や FSx など他の AWS storage service 用 driver も簡単にインストールできます。

## EKS のコスト構造

EKS cluster の運用時には、次のコストが発生します。

1. **EKS Control Plane のコスト**: cluster ごとに時間単位の料金が課金されます。
2. **コンピューティングコスト**:
   * EC2 instance（managed または self-managed node）
   * Fargate（Pod の実行時間と resource 使用量に基づいて課金）
3. **Storage コスト**: EBS、EFS、FSx などの storage service のコスト
4. **Network コスト**: data transfer および load balancer 使用のコスト

### コスト最適化戦略

1. **Spot Instance を使用**: コストを最大 90% 削減できます。
2. **Fargate を活用**: 使用率の低い workload に適しています。
3. **Auto Scaling を設定**: 必要に応じて node を自動的にスケールアップ・スケールダウンします。
4. **Locality Routing**: network コストを削減するため、traffic を同じ Availability Zone 内に維持します。
5. **EKS Auto Mode**: 自動 cluster scaling によりコストを最適化します。
6. **Hybrid Nodes**: さまざまな instance type を組み合わせてコスト効率を向上させます。

## AWS サービスとの統合

EKS は、次の AWS サービスと統合されます。

![Amazon EKS を中心とした AWS サービス統合の図: IAM、VPC、storage、CloudWatch、ECR、SageMaker/Bedrock。](../.gitbook/assets/en-eks-01-eks-introduction-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-01-eks-introduction-0.html)

1. **IAM**: Kubernetes RBAC との統合により、認証と認可を管理します。
2. **VPC**: networking infrastructure を提供します。
3. **CloudWatch**: monitoring と logging を提供します。
4. **ALB/NLB**: load balancing を提供します。
5. **ECR**: container image registry を提供します。
6. **EBS/EFS/FSx**: persistent storage を提供します。
7. **AWS App Mesh**: service mesh 機能を提供します。
8. **AWS Certificate Manager**: SSL/TLS certificate を管理します。
9. **AWS Secrets Manager**: 機密情報を安全に保存および管理します。
10. **AWS SageMaker**: machine learning workload を実行します。
11. **AWS Bedrock**: generative AI model を活用します。

## EKS のベストプラクティス

1. **Cluster 設計**:
   * 複数の Availability Zone に node を配置する
   * 適切な instance type を選択する
   * Node Group 戦略を策定する
2. **Security**:
   * 最小権限の原則を適用する
   * network policy を実装する
   * Pod security policy を適用する
   * image scanning と vulnerability management を実施する
3. **Networking**:
   * 適切な subnet 設計
   * security group の設定
   * Locality Routing の活用
4. **Monitoring と Logging**:
   * CloudWatch Container Insights を有効にする
   * Control Plane logging を設定する
   * Prometheus と Grafana を活用する
5. **Upgrade 戦略**:
   * 定期的な upgrade を計画する
   * blue/green deployment 戦略を検討する
   * upgrade 前にテストを実施する

## クイズ

この章で学んだ内容を確認するには、[Amazon EKS 概要クイズ](../quizzes/eks/01-eks-introduction-quiz.md)に挑戦してください。
