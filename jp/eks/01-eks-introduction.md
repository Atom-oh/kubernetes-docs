# EKS の概要

> **サポート対象バージョン**: Amazon EKS の標準サポート 1.34–1.37、延長サポート 1.31–1.33（確認日: 2026年10月12日）
> **最終更新**: 2026年10月12日

Amazon Elastic Kubernetes Service (EKS) は、AWS 上で Kubernetes を実行するためのマネージドサービスです。この章では、EKS の基本概念、アーキテクチャ、および標準的な Kubernetes との違いについて説明します。

## EKS と Kubernetes

EKS は標準 Kubernetes API を提供するマネージドサービスです。Kubernetes の基本概念と操作に関する詳細は、[Kubernetes の概要](../basics/04-kubernetes-introduction.md)ドキュメントを参照してください。

### EKS の主な利点

1. **マネージド Control Plane**: AWS が Kubernetes Control Plane の可用性とスケーラビリティを管理します
2. **強化されたセキュリティ**: AWS IAM との統合による認証と認可
3. **AWS サービスとの統合**: 他の AWS サービス（ELB、ECR、IAM など）とのシームレスな統合
4. **多様なコンピュートオプション**: EC2 ベースのノード、EKS Auto Mode、Fargate、Hybrid Nodes。Bottlerocket はノード用オペレーティングシステムであり、独立したコンピュートサービスではありません
5. **Auto Scaling**: Cluster Autoscaler、Karpenter などによる Auto Scaling のサポート
6. **Managed Node Groups**: 自動化されたノードライフサイクル管理

## EKS のアーキテクチャとコンポーネント

Amazon EKS の全体アーキテクチャは次のとおりです。

### Control Plane

EKS は高可用性の Control Plane を提供します。Control Plane は複数の Availability Zone にまたがって実行され、次のコンポーネントで構成されます。

* **API Server**: Kubernetes API を公開し、クラスターとの対話を処理します。
* **etcd**: クラスターの状態を保存する分散キー・バリューストアです。
* **Controller Manager**: クラスターの状態を管理する Controller を実行します。
* **Scheduler**: Pod をノードに割り当てます。

EKS では、これらの Control Plane コンポーネントを AWS が管理するため、ユーザーが直接管理する必要はありません。

### Data Plane

EKS の Data Plane は、次のオプションで構成できます。

1. **Managed Node Groups**: AWS がプロビジョニングと置き換えのワークフローを管理する EC2 ノードグループです。運用者はノードのバージョン/AMI 更新を選択して開始します。Control Plane のアップグレードでこれらのノードが自動的に更新されることはありません。
2. **Self-Managed Nodes**: ユーザーが直接管理する EC2 インスタンスです。
3. **AWS Fargate**: Fargate プロファイルを介して選択する Pod 単位のコンピュートです。運用者は引き続きワークロード構成とリソースリクエストを管理します。
4. **EKS Auto Mode**: AWS が EC2 ノードのプロビジョニング、スケーリング、更新に加え、サポート対象のネットワーキング、ロードバランシング、ブロックストレージ機能を管理します。
5. **Hybrid Nodes**: お客様が管理するオンプレミス/エッジマシンが AWS にホストされた EKS Control Plane に接続します。信頼できる接続が必要です。

### ネットワーキング

従来の EC2 ベースの EKS ノードでは、Amazon VPC CNI がデフォルトであり、通常の Pod に VPC アドレスを割り当てます。`hostNetwork` Pod はノードのネットワークを共有します。Auto Mode は独自のネットワーキング機能を管理し、Hybrid Nodes は Amazon VPC CNI ではなく、互換性のあるオンプレミス CNI を使用します。

## 標準 Kubernetes と EKS の違い

### 管理責任

* **セルフマネージド Kubernetes**: 運用者が Control Plane と Data Plane を管理します。他のマネージドディストリビューションでは責任分担が異なる場合があります。
* **EKS**: AWS が Control Plane を管理します。Data Plane の責任はコンピュートオプションによって異なります。ワークロードのセキュリティ、アイデンティティ、構成、可用性、データ保護は引き続きお客様の責任です。

### ネットワーキング

* **標準 Kubernetes**: さまざまな CNI プラグインを選択できます。
* **EKS**: 従来の EC2 ベースのクラスターでは、Amazon VPC CNI がデフォルトです。代替 CNI および Auto Mode/Hybrid Nodes には、異なる機能上およびサポート上の制約があります。

### ロードバランシング

* **標準 Kubernetes**: `LoadBalancer` タイプの Service を使用するには、別の Controller をインストールする必要があります。
* **EKS**: 従来のクラスターでは、NLB Service と ALB Ingress に AWS Load Balancer Controller をインストールして認可します。レガシー Controller は Classic Load Balancer を作成できます。Auto Mode は、独自のクラスとサポート対象の構成により、マネージド NLB/ALB 統合を提供します。Service タイプだけでは Controller を識別できません。Fargate は ALB/NLB IP ターゲットをサポートします。

### ストレージ

* **標準 Kubernetes**: さまざまなストレージドライバーを手動でインストールして構成する必要があります。
* **EKS**: 従来のクラスターでは、EBS CSI ドライバー/アドオンをインストールし、その IAM 権限を付与します。Auto Mode には、`ebs.csi.aws.com` とは異なるプロビジョナー `ebs.csi.eks.amazonaws.com` によるマネージド EBS サポートがあります。EFS と FSx の統合には別途前提条件があります。EBS ボリュームは Fargate または Hybrid Nodes ではマウントできません。

## EKS のコスト構造

EKS クラスターの運用時に発生するコストは、次のとおりです。

1. **EKS Control Plane のコスト**: クラスターごとに時間単位の料金が発生します。標準/延長サポートでは料金が異なり、オプションのプロビジョニング済み Control Plane ティアには追加料金がかかります。
2. **コンピュートコスト**:
   * EC2 インスタンス（Managed Node Groups または Self-Managed Nodes）
   * Fargate（Pod の実行時間とリソース使用量に基づいて課金）
3. **ストレージコスト**: EBS、EFS、FSx などのストレージサービスにかかるコスト
4. **ネットワークコスト**: データ転送、NAT Gateway、パブリック IPv4 アドレス、ロードバランサーの使用にかかるコスト
5. **マネージド機能のコスト**: Auto Mode、EKS Capabilities、Hybrid Nodes には、関連するクラスター/インフラストラクチャのコストに加えて独自の料金がかかります。

### コスト最適化戦略

1. **Spot Instance を使用する**: 現在の Spot 料金と中断への許容度を比較してください。提示される節約額は、ワークロードレベルでの保証ではありません。
2. **Fargate を評価する**: プロビジョニングした Pod サイズ、実行時間、機能制限、運用労力を EC2 と比較してください。アプリケーションの使用率が低いだけでは、コスト削減は保証されません。
3. **Auto Scaling を構成する**: 必要に応じてノードを自動的にスケールアップおよびスケールダウンします。
4. **同一ゾーン内ルーティング**: サポートされている場合は、十分なキャパシティとフェイルオーバーを維持しつつ、同一ゾーン内のトラフィックを優先してください。ルーティングとロードバランサーの設定によって、転送コストが削減されるかどうかが決まります。
5. **EKS Auto Mode**: Auto Mode の管理料金と合わせて、自動スケーリングおよび統合によるコスト削減を評価してください。
6. **Hybrid Nodes**: 既存のオンプレミスキャパシティを、vCPU あたりの Hybrid Nodes 料金および接続/運用コストと合わせて評価してください。この機能は、EC2 インスタンスタイプを混在させることの同義語ではありません。

## AWS サービスとの統合

EKS は次の AWS サービスと統合されます。

![Amazon EKS を中心とした AWS サービス統合の図: IAM、VPC、ストレージ、CloudWatch、ECR、SageMaker/Bedrock。](../.gitbook/assets/en-eks-01-eks-introduction-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-01-eks-introduction-0.html)

1. **IAM**: IAM アイデンティティがクラスターに対して認証を行います。EKS access entry は access policy および/または Kubernetes RBAC グループを通じて認可します。Pod Identity と IRSA は、個別にワークロードへ AWS 権限を付与します。
2. **VPC**: ネットワークインフラストラクチャを提供します。
3. **CloudWatch**: モニタリングとロギングを提供します。
4. **ALB/NLB**: ロードバランシングを提供します。
5. **ECR**: コンテナイメージレジストリを提供します。
6. **EBS/EFS/FSx**: 永続ストレージを提供します。
7. **AWS App Mesh**: AWS は 2026年9月30日にサポートを終了しており、App Mesh のコンソールおよびリソースにはアクセスできなくなっています。既存の統合は移行する必要があります。新しいデプロイメントには選択しないでください。
8. **AWS Certificate Manager**: SSL/TLS 証明書を管理します。
9. **AWS Secrets Manager**: 機密情報を安全に保存および管理します。
10. **AWS SageMaker**: 機械学習ワークロードを実行します。
11. **AWS Bedrock**: 生成 AI モデルを活用します。

## EKS のベストプラクティス

1. **クラスター設計**:
   * 複数の Availability Zone にノードをデプロイする
   * 適切なインスタンスタイプを選択する
   * ノードグループ戦略を策定する
2. **セキュリティ**:
   * 最小権限の原則を適用する
   * ネットワークポリシーを実装する
   * Pod Security Admission および/または admission policy を使用して Pod Security Standards を適用する。PodSecurityPolicy API は Kubernetes 1.25 で削除されました
   * イメージスキャンと脆弱性管理
3. **ネットワーキング**:
   * 適切なサブネット設計
   * セキュリティグループの構成
   * 同一ゾーン内ルーティングを活用する
4. **モニタリングとロギング**:
   * CloudWatch Container Insights を有効にする
   * Control Plane のロギングを構成する
   * Prometheus と Grafana を活用する
5. **アップグレード戦略**:
   * 定期的なアップグレードを計画する
   * ブルー/グリーンデプロイメント戦略を検討する
   * アップグレード前にテストを実施する

## 公式リファレンス

- [EKS のバージョンライフサイクル](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [コンピュートと責任分担](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [AWS Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [EBS CSI と Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
- [Fargate に関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [App Mesh のサポートに関する通知](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)
- [EKS の料金](https://aws.amazon.com/eks/pricing/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)

## クイズ

この章で学んだ内容を確認するには、[Amazon EKS 概要クイズ](../quizzes/eks/01-eks-introduction-quiz.md)に挑戦してください。
