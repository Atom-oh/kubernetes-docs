# EKS Hybrid Nodes

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+ **最終更新**: February 23, 2026

Amazon EKS Hybrid Nodes は、AWS EKS コントロールプレーンからオンプレミスサーバーを管理できる機能です。このガイドでは、本番環境における EKS Hybrid Nodes の概念、設定方法、実践的な使用方法を扱います。

## 目次

1. [前提条件とシステム要件](01-prerequisites.md)
2. [ネットワーク設定](02-network-configuration.md)
3. [エアギャップ環境のセットアップ (S3 + VPC Endpoints)](03-airgap-setup.md)
4. [ノードのブートストラップ](04-node-bootstrap.md)
5. [GPU サーバーの統合](05-gpu-integration.md)
6. [ワークロード配置戦略](06-workload-placement.md)
7. [ノードライフサイクル管理](07-node-lifecycle.md)
8. [運用と保守](08-operations.md)
9. [ベアメタルサーバーの OS インストールおよび移行ガイド](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)

## Hybrid Nodes とは？

EKS Hybrid Nodes は、オンプレミスのデータセンターまたはエッジ環境のサーバーを、AWS EKS コントロールプレーンによって管理される Kubernetes ノードとして登録できる機能です。これにより、クラウドとオンプレミスのインフラストラクチャを単一の Kubernetes クラスターとして管理できます。

![オンプレミスのルーターおよびゲートウェイから AWS クラスター VPC 内のコントロールプレーン ENI までを示す EKS hybrid nodes ネットワークの概要図。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

次の図は、VPC、サブネット、Transit Gateway/Virtual Private Gateway、Remote Node/Pod CIDR の接続を含むネットワーク前提条件を示しています。

![クラスターの RemoteNodeNetwork および RemotePodNetwork 設定と、VPC 側およびオンプレミス側の両方のルートテーブルを結び付けた Hybrid nodes の前提条件図。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## Hybrid Nodes を使用する理由

### 1. 規制遵守とデータ主権

特定の業界（金融、医療、政府）では、データを特定のリージョンまたは施設内に保持することを求める規制があります。Hybrid Nodes を使用すると、EKS の管理機能を活用しながら、機密データをオンプレミスに保持できます。

```yaml
# Example of regulatory compliance workload placement
apiVersion: v1
kind: Pod
metadata:
  name: financial-data-processor
spec:
  nodeSelector:
    topology.kubernetes.io/zone: "on-premises"
    compliance.company.io/data-sovereignty: "required"
  containers:
  - name: processor
    image: harbor.internal.company.io/finance/data-processor:v1.2.0
```

### 2. データグラビティ

大規模なデータセットがオンプレミスに存在する場合、データをクラウドへ移動するよりも、コンピューティングをデータの近くに配置するほうが効率的です。

### 3. 既存ハードウェアの活用

すでに投資した高性能サーバー（特に GPU サーバー）を継続して活用しつつ、最新の Kubernetes ベースのワークロード管理を適用できます。

### 4. 統合管理

単一のコントロールプレーンからクラウドとオンプレミスの両方の環境にある Kubernetes ワークロードを管理することで、運用の複雑さを軽減できます。

## アーキテクチャコンポーネント

EKS Hybrid Nodes のアーキテクチャは、次のコンポーネントで構成されます。

| コンポーネント                       | 場所          | 役割                                            |
| ------------------------------- | ----------- | ----------------------------------------------- |
| EKS Control Plane               | AWS         | API server、etcd、controller manager、scheduler |
| nodeadm                         | オンプレミス | ノードのブートストラップおよび管理エージェント             |
| kubelet                         | オンプレミス | Pod の実行およびノードステータスの報告         |
| containerd                      | オンプレミス | コンテナランタイム                               |
| VPN/Direct Connect              | ネットワーク     | AWS とオンプレミス間のセキュアな接続   |
| SSM Agent or IAM Roles Anywhere | オンプレミス | 認証情報管理                           |

### 主な制約と制限事項

* **ネットワーク接続**: VPN または Direct Connect による、オンプレミスから AWS への信頼性の高い接続が必要です（切断、断続的、制限、または拒否された環境には適していません）
* **CIDR 制限**: クラスターあたり Remote Node Networks および Remote Pod Networks に最大 15 個の CIDR
* **IPv4 のみ**: IPv4 アドレスファミリーを使用する必要があります（Hybrid Nodes では IPv6 はサポートされません）
* **認証モード**: クラスターでは `API` または `API_AND_CONFIG_MAP` の認証モードを使用する必要があります
* **エンドポイントアクセス**: Public または Private のみを使用する必要があります（「Public and Private」は **サポートされません**。Hybrid Node の参加に失敗します）
* **vCPU 単位の料金**: Hybrid Nodes には vCPU ごとの時間単位で料金が発生します（最低利用コミットメントはありません）
* **クラウドインフラストラクチャ**: クラウドインフラストラクチャではサポートされません（EC2 で実行すると Hybrid Node の料金が発生します）
* **VPC CNI**: Amazon VPC CNI は Hybrid Nodes と互換性がありません。Cilium または Calico を使用してください

### 認証情報プロバイダーの選択肢

EKS Hybrid Nodes は、オンプレミスノードを AWS で認証するために 2 つの認証情報プロバイダーをサポートしています。

| 機能                  | SSM Hybrid Activations                                                           | IAM Roles Anywhere                                     |
| ------------------------ | -------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **セットアップの複雑さ**     | シンプル — アクティベーションコード/ID のペア                                                 | 中程度 — PKI インフラストラクチャが必要                 |
| **証明書が必要** | いいえ                                                                               | はい（ノードごとに X.509 証明書）                       |
| **エアギャップ対応**   | いいえ（SSM エンドポイントへのアクセスが必要）                                                | はい（ローカル CA で動作）                              |
| **認証情報のローテーション**  | 自動（AWS 管理、1 時間の TTL 固定）                                        | 自動（証明書ベース、1～12 時間で設定可能） |
| **ノード名**          | 自動生成（`mi-xxxx`、カスタマイズ不可）                                     | カスタム（証明書の CN と一致する必要があります）                     |
| **スケーリング制限**       | リージョンごとのアカウントあたり 1,000 まで無料。さらに必要な場合は advanced-instances ティア（追加料金） | 制限なし                                              |
| **AWS への依存**       | SSM サービス                                                                      | IAM Roles Anywhere サービス                             |
| **最適な用途**             | インターネット/VPN 接続がある標準環境                                          | エアギャップ、厳格なコンプライアンス、既存の PKI               |

> **推奨**: ほとんどの環境では、シンプルな SSM Hybrid Activations を使用してください。エアギャップのサポートが必要な場合や、すでに PKI インフラストラクチャがある場合は IAM Roles Anywhere を選択してください。

## 主なユースケース

1. **AI/ML ワークロード**: オンプレミスの GPU サーバーでのモデル学習、クラウドでの推論サービス
2. **金融サービス**: オンプレミスでの取引データ処理、クラウドでの分析
3. **製造業**: 中央クラウドと統合された工場でのエッジコンピューティング
4. **メディア処理**: データが存在する場所での大規模メディアファイル処理

## 次のステップ

まず [前提条件とシステム要件](01-prerequisites.md) を確認し、環境が EKS Hybrid Nodes の準備を完了していることを確認してください。

## クイズ

EKS Hybrid Nodes の理解度を確認するには、次のクイズに挑戦してください。

* [EKS Hybrid Nodes クイズ](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/eks-hybrid-nodes/README.md)

## 関連ドキュメント

* [EKS Resiliency ガイド](../eks/10-eks-resiliency.md) - ハイブリッド環境における高可用性の設定
* [EKS コスト最適化](../eks/07-eks-cost-optimization.md) - コスト管理戦略
* [EKS モニタリングとロギング](../eks/06-eks-monitoring-logging.md) - 統合モニタリングの設定

## 公式ドキュメント

* [AWS EKS Hybrid Nodes 公式ドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [nodeadm ユーザーガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 公式ドキュメント](https://goharbor.io/docs/)
* [NVIDIA GPU Operator ドキュメント](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Hybrid Nodes ネットワークガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Hybrid Nodes CNI 設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Hybrid Nodes トラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)
