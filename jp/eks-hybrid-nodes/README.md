# EKS Hybrid Nodes

> **サポート対象バージョン**: 現在 EKS がサポートするバージョン。例は EKS 1.36 / nodeadm 1.0.20 でレビュー済み
> **最終更新**: September 16, 2026

Amazon EKS Hybrid Nodes は、お客様が運用するオンプレミスまたはエッジのノードを、AWS が管理する EKS control plane に接続します。ホスト、operating system、接続性、ワークロードの運用は引き続きお客様が担います。本ガイドはサポートされるインターフェイスと設定例を区別して示すものであり、特定のオンプレミス本番環境デプロイがテスト済みであることを示す根拠ではありません。

## 目次

1. [前提条件とシステム要件](01-prerequisites.md)
2. [ネットワーク設定](02-network-configuration.md)
3. [インターネット制限環境のセットアップ (S3 + VPC Endpoints)](03-airgap-setup.md)
4. [ノードのブートストラップ](04-node-bootstrap.md)
5. [GPU サーバーの統合](05-gpu-integration.md)
6. [ワークロード配置戦略](06-workload-placement.md)
7. [ノードライフサイクル管理](07-node-lifecycle.md)
8. [運用と保守](08-operations.md)
9. [ベアメタルサーバーの OS インストールと移行ガイド](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)
11. [ネットワーク分離のセキュリティレビュー](11-network-separation-security.md)

## Hybrid Nodes とは

Hybrid Nodes は、通常の AWS コンピューティングノードと cluster を共有できます。クラウド上のマシンを **hybrid** ノードとして登録することは別の話です。AWS は AWS Region、Local Zones、Outposts、その他のクラウドにおける hybrid ノードのインフラストラクチャをサポートしておらず、EC2 を使用した場合も hybrid の料金は発生します。

![オンプレミスの router と gateway から AWS cluster VPC 内の control plane ENI までを示す EKS hybrid nodes のネットワーク概要図。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

次の図は、VPC、subnet、Transit Gateway/Virtual Private Gateway、および Remote Node/Pod CIDR の接続性を含むネットワーク前提条件を示しています。

![cluster の RemoteNodeNetwork および RemotePodNetwork 設定を、VPC 側とオンプレミス側の両方の route table に関連付けた Hybrid nodes の前提条件図。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

これらの図はプライベート接続とルーティングを説明するものであり、すべてのオンプレミスのルート、ファイアウォールルール、AWS サービスエンドポイントが自動的に作成されるわけではありません。

セキュリティチームによるレビューには、[ネットワーク分離レビューガイド](11-network-separation-security.md) を使用してください。プライベート cluster エンドポイント、EKS ENI、AWS サービスの PrivateLink エンドポイントを区別し、DX をまたぐ管理接続とデータ境界に関する根拠を示します。

## ユースケースとデータ境界

オンプレミスの GPU、大規模なローカルデータセット、エッジ処理、既存ハードウェアの活用は、Hybrid Nodes を使用する理由になり得ます。データローカリティの要件を満たすには、アプリケーション、ストレージ、egress、ロギングの制御が別途必要です。Kubernetes API オブジェクトと control plane のメタデータは AWS 側で管理されます。node selector だけではデータ主権や規制コンプライアンスは成立しません。

`on-premises` という名前の AWS ゾーンが存在すると想定するのではなく、実際の hybrid コンピューティングのラベルと、組織で明示的に管理するラベルを配置に使用してください。

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

この断片はラベル、完全なアプリケーション、セキュリティ境界、データ保持ポリシーを作成するものではありません。イメージ/ランタイムの互換性と実際のデータ経路を検証してください。

## アーキテクチャと責任範囲

| Component | Location | Responsibility |
|-----------|----------|----------------|
| EKS API server、etcd、controller、scheduler | AWS | AWS が管理する control plane |
| nodeadm | オンプレミスのサポート対象 Linux ホスト | インストール/ブートストラップ/アップグレード用 CLI。常駐するノードエージェントではない |
| kubelet / containerd | オンプレミス | ノードエージェント / CRI ランタイム。ホスト所有者が運用 |
| Cilium または Calico | オンプレミスおよび cluster | 互換性のある CNI 設定。VPC CNI は hybrid ノードを管理しない |
| SSM Agent または Roles Anywhere signing helper | オンプレミス | 対応する AWS サービスから一時的な認証情報を取得 |
| SSM / IAM Roles Anywhere サービス | AWS | 認証情報サービスであり、ローカルのオフライン CA の代替ではない |
| VPN / Direct Connect とルーティング | 両環境 | 双方向の接続性。Direct Connect だけでは暗号化を意味しない |

Bottlerocket のサポート対象 VMware バリアントは独自のブートストラップ経路を使用し、nodeadm は使用しません。その他のサポート対象ホストでは、`nodeadm install` が依存関係をインストールし、`nodeadm init` がノードを設定して join させます。SSM ベースの新規インストール/アップグレードでは、SSM の署名鍵の変更により **nodeadm 1.0.19 以降** が必要です。レビュー対象の現行リリースは **1.0.20** です。

## 計画時に考慮すべき制約

- **接続された環境:** AWS への信頼できるプライベートな双方向接続が必要です。Hybrid Nodes は切断/断続的な DDIL 環境での運用を想定していません。本ガイドにおける「エアギャップ」とは、AWS への必要な接続性を保ちながらインターネットアクセスを制限することを意味し、AWS からの隔離ではありません。
- **アドレス:** IPv4 の RFC1918 または CGNAT の範囲を使用し、リモートノード/Pod、VPC、サービスの CIDR が重複しないようにします。**cluster ごとに最大 15 のノード CIDR と 15 の Pod CIDR** がサポートされます。
- **認証:** `API` または `API_AND_CONFIG_MAP` を使用し、Hybrid Nodes 用の IAM ロール/アクセスエントリを準備します。
- **API エンドポイント:** AWS はパブリックのみ、またはプライベートのみを推奨します。両方を有効にすると、VPC 外のノードはパブリックエンドポイントのアドレスを解決します。想定される経路/アクセスルールがプライベートである場合、これが join を妨げる**可能性があります**。API 全般を禁止するものではありません。パブリック API エンドポイントを使用しても、control plane とノード間のプライベート接続要件はなくなりません。
- **Region:** 現在の概要によると、AWS GovCloud (US) と AWS 中国リージョンを除いて利用可能です。
- **ホストのサポート:** OS、アーキテクチャ、CNI、カーネルをまとめて確認してください。AL2023 はオンプレミスの仮想化環境向けであり、ベアメタル全般への推奨ではありません。
- **料金:** hybrid の料金は、ノードが接続されている間に報告される vCPU 時間に基づきます。ハイパースレッディングが有効なベアメタルのコアは 2 vCPU として報告されることがあります。ワークロードがアイドルであってもノードの課金は自動的に停止しません。cluster やその他のサービスの料金は別途発生します。

## 認証情報プロバイダー

いずれのプロバイダーも、認証情報を更新するために AWS サービスエンドポイントへのアクセスが必要です。ローカル CA があっても、IAM Roles Anywhere がオフラインで AWS の認証情報を発行できるようにはなりません。レビュー済みの理由がない限り、フリート全体で 1 つのプロバイダーに統一することを推奨します。

| Topic | SSM hybrid activations | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| ブートストラップ | アクティベーション ID/コードと、SSM を信頼するよう準備したロール | PKI、ノードごとの証明書/鍵、trust anchor、profile、ロール |
| 命名 | SSM が生成する `mi-...` 形式の名前 | 証明書の ID に紐づくカスタムノード名 |
| セッション期間 | 固定 1 時間、SSM が更新 | デフォルト 1 時間。サポートされるリクエスト/profile の期間は 15 分〜12 時間で、実効期間とロールの最大値に従う |
| 切断時 | 更新できない。リトライのバックオフによりネットワーク復旧後の再接続が遅れることがある | オフラインでは新しい認証情報を取得できない。接続が回復すると credential-process がオンデマンドで取得する |
| スケール / コスト | SSM のノード登録料金やノードごとの管理料金はない。機能利用の料金は別途 | IAM Roles Anywhere のクォータと PKI の運用要件を確認 |
| 一般的な選択基準 | 既存の PKI がない場合。登録がより簡単 | 既存の PKI があり、証明書のライフサイクルを管理している場合 |

**2026 年 9 月 16 日時点の料金確認:** SSM は 2026 年 6 月 30 日をもって Advanced Instances Tier を廃止しました。Session Manager と Run Command の利用条件については [現在の SSM の料金](https://aws.amazon.com/systems-manager/pricing/) を参照してください。[EKS Hybrid Nodes の vCPU 料金](https://aws.amazon.com/eks/pricing/) は引き続き別料金です。

Roles Anywhere の profile はカスタムのロールセッション名を受け入れる必要があり、trust policy は選択した証明書の属性にそれを紐づける必要があります。実効セッション期間は IAM ロールの最大値を**超えてはなりません**。同一の値であれば CreateSession API で許可されます。[前提条件](01-prerequisites.md) では、これらの取り決めと安全な準備方法を詳しく説明します。

## ワークロードの例

1. 検証済みのランタイムと復旧計画を備えたローカル GPU でのトレーニングまたは推論。
2. AWS のメタデータ/テレメトリ/egress の経路を個別にレビューしたうえでのローカルデータ処理。
3. 信頼できる接続性と、切断時の動作をテスト済みの工場/エッジアプリケーション。
4. 既存の大規模データセットの近くで実行するメディア処理。

## 次のステップ

まずは [前提条件とシステム要件](01-prerequisites.md) から始めて、環境が EKS Hybrid Nodes に対応できているか確認してください。

## クイズ

EKS Hybrid Nodes の理解度を確認するには、次のクイズに挑戦してください。

* [EKS Hybrid Nodes 前提条件クイズ](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodes ネットワーク設定クイズ](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodes インターネット制限環境セットアップクイズ](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodes ノードブートストラップクイズ](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid Nodes GPU 統合クイズ](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodes ワークロード配置クイズ](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [ノードライフサイクル管理クイズ](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodes 運用クイズ](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [ベアメタルサーバーの OS インストールと移行クイズ](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodes Gateway クイズ](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [ネットワーク分離セキュリティレビュークイズ](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

## 関連ドキュメント

* [EKS 耐障害性ガイド](../eks/10-eks-resiliency.md) - hybrid 環境における高可用性の設定
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

* [Hybrid の operating system 互換性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybrid の認証情報と IAM ロール](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [ネットワーク切断時のホスト認証情報](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession のセマンティクス](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS の料金](https://aws.amazon.com/eks/pricing/)
