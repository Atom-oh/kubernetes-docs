# EKS Hybrid Nodes

> **サポート対象バージョン**: 現在 EKS がサポートするバージョン。例は EKS 1.36 / nodeadm 1.0.20 向けにレビュー済み
> **最終更新**: 2026年10月12日

Amazon EKS Hybrid Nodes は、顧客が運用するオンプレミスまたはエッジのノードを、AWS が管理する EKS control plane に接続します。ホスト、オペレーティングシステム、接続性、ワークロードの運用は引き続きお客様が担います。このガイドでは、サポート対象のインターフェイスと設定例を区別しています。特定のオンプレミス本番デプロイメントがテスト済みであることを示すものではありません。

EKS 1.37 は 2026 年 10 月 1 日に利用可能になりました。このガイドの例は引き続き EKS 1.36 および nodeadm 1.0.20 に対してレビューされています。

バージョンを選択する前に、[EKS バージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)、Hybrid Nodes のドキュメント、およびホスト/CNI のサポート情報を確認してください。

## 目次

1. [前提条件とシステム要件](01-prerequisites.md)
2. [ネットワーク設定](02-network-configuration.md)
3. [制限されたインターネット環境のセットアップ（S3 + VPC エンドポイント）](03-airgap-setup.md)
4. [ノードのブートストラップ](04-node-bootstrap.md)
5. [GPU サーバーの統合](05-gpu-integration.md)
6. [ワークロード配置戦略](06-workload-placement.md)
7. [ノードライフサイクル管理](07-node-lifecycle.md)
8. [運用と保守](08-operations.md)
9. [ベアメタルサーバーの OS インストールおよび移行ガイド](09-bare-metal-os-setup.md)
10. [Hybrid Nodes Gateway](10-hybrid-nodes-gateway.md)
11. [ネットワーク分離セキュリティレビュー](11-network-separation-security.md)

## Hybrid Nodes とは？

Hybrid Nodes は、通常の AWS コンピューティングノードとクラスターを共有できます。クラウドマシンを **hybrid** ノードとして登録することは別の問題です。AWS は、AWS リージョン、Local Zones、Outposts、または他のクラウドにおける hybrid-node インフラストラクチャをサポートしておらず、EC2 の使用には引き続き hybrid 料金が発生します。

![オンプレミスのルーターとゲートウェイから AWS クラスター VPC 内の control plane ENI までを示す EKS hybrid nodes のネットワーク概要図。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

次の図は、VPC、サブネット、Transit Gateway/Virtual Private Gateway、および Remote Node/Pod CIDR の接続性を含むネットワークの前提条件を示しています。

![クラスターの RemoteNodeNetwork および RemotePodNetwork 設定を、VPC 側とオンプレミス側の両方にあるルートテーブルに結び付ける Hybrid Nodes の前提条件図。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

これらの図はプライベート接続とルーティングを示すものであり、オンプレミスのすべてのルート、ファイアウォールルール、または AWS サービスエンドポイントが自動的に作成されることを意味するものではありません。

セキュリティチームによるレビューには、[ネットワーク分離レビューガイド](11-network-separation-security.md)を使用してください。このガイドは、プライベートクラスターエンドポイント、EKS ENI、AWS サービスの PrivateLink エンドポイントを区別し、DX をまたぐ管理接続とデータ境界の証跡を特定します。

## ユースケースとデータ境界

オンプレミス GPU、大規模なローカルデータセット、エッジ処理、既存ハードウェアは、Hybrid Nodes を使用する理由となり得ます。データローカリティの要件には、引き続きアプリケーション、ストレージ、egress、ログ記録の制御が必要です。Kubernetes API オブジェクトと control-plane メタデータは AWS で管理されます。ノードセレクターだけでは、データ主権や規制コンプライアンスを確立できません。

`on-premises` という名前の AWS zone が存在すると想定するのではなく、実際の hybrid コンピューティングラベルと、明示的に維持管理される組織ラベルを配置に使用してください。

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

このフラグメントは、ラベル、完全なアプリケーション、セキュリティ境界、またはデータ保持ポリシーを作成するものではありません。イメージ/ランタイムの互換性と実際のデータパスを検証してください。

## アーキテクチャと責任範囲

| コンポーネント | 場所 | 責任範囲 |
|-----------|----------|----------------|
| EKS API server, etcd, controllers, scheduler | AWS | AWS が管理する control plane |
| nodeadm | オンプレミスのサポート対象 Linux ホスト | インストール/ブートストラップ/アップグレード用 CLI。長時間稼働するノードエージェントではない |
| kubelet / containerd | オンプレミス | ホスト所有者が運用するノードエージェント / CRI ランタイム |
| Cilium or Calico | オンプレミスとクラスター | 互換性のある CNI 設定。VPC CNI は hybrid ノードを管理しない |
| SSM Agent or Roles Anywhere signing helper | オンプレミス | 対応する AWS サービスから一時的な認証情報を取得 |
| SSM / IAM Roles Anywhere service | AWS | 認証情報サービス。ローカルのオフライン CA の代替ではない |
| VPN / Direct Connect and routing | 両方の環境 | 双方向接続。Direct Connect 単体は暗号化を意味しない |

Bottlerocket のサポート対象 VMware バリアントは独自のブートストラップパスを使用し、nodeadm は使用しません。その他のサポート対象ホストでは、`nodeadm install` が依存関係をインストールし、`nodeadm init` がノードを設定して参加させます。SSM ベースの新規インストール/アップグレードには、SSM 署名キーの変更により **nodeadm 1.0.19 以降**が必要です。レビュー済みの現行リリースは **1.0.20** です。

## 考慮すべき制約

- **接続環境:** AWS への信頼性の高いプライベートな双方向接続が必要です。Hybrid Nodes は、切断された環境や断続的な DDIL 運用を想定していません。このガイドにおける「エアギャップ」とは、必要な AWS 接続を維持しつつインターネットアクセスを制限することであり、AWS からの分離を意味しません。
- **アドレス:** リモートのノード/Pod、VPC、サービス CIDR の間で重複しない IPv4 RFC1918 または CGNAT 範囲。クラスターあたり最大 **15 個のノード CIDR と 15 個の Pod CIDR** がサポートされます。
- **認証:** `API` または `API_AND_CONFIG_MAP` を使用し、Hybrid Nodes の IAM role/access entries を準備します。
- **API endpoint:** AWS は public-only または private-only を推奨しています。両方を有効にした場合、VPC 外のノードは public endpoint アドレスを解決します。想定するパス/アクセスルールが private である場合、これは参加を妨げる**可能性があります**。これは普遍的な API の禁止事項ではありません。public API endpoint を使用しても、control-plane からノードへのプライベート接続要件はなくなりません。
- **リージョン:** 現在の概要によれば、AWS GovCloud (US) および AWS China Regions を除き利用できます。
- **ホストのサポート:** OS、アーキテクチャ、CNI、カーネルをまとめて確認してください。AL2023 はオンプレミスの仮想化環境向けであり、汎用的なベアメタルの推奨ではありません。
- **料金:** Hybrid 料金は、ノードが接続されている間に報告される vCPU 時間に基づきます。ハイパースレッディング対応のベアメタルコアは、2 vCPU として報告される場合があります。アイドル状態のワークロードであってもノード料金が自動的に停止するわけではありません。クラスター料金およびその他のサービス料金は別です。

## 認証情報プロバイダー {#credential-providers}

どちらのプロバイダーも、認証情報を更新するために AWS サービスエンドポイントへのアクセスが必要です。ローカル CA を使用しても、IAM Roles Anywhere で AWS 認証情報をオフライン発行することはできません。混在させることにレビュー済みの理由がない限り、フリート全体で一貫して 1 つのプロバイダーを使用してください。

| トピック | SSM hybrid activations | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| ブートストラップ | Activation ID/code と、準備済みの SSM を信頼する role | PKI、ノードごとの certificate/key、trust anchor、profile、role |
| 命名 | SSM が生成する `mi-...` 名 | 証明書アイデンティティにバインドされたカスタムノード名 |
| セッション期間 | 固定 1 時間。SSM により更新 | デフォルトは 1 時間。サポート対象の request/profile 期間は 15 分～12 時間で、実効期間および role の最大値に従う |
| 切断 | 更新できない。retry backoff によりネットワーク復旧後の再接続が遅延する場合がある | オフラインでは新しい認証情報を取得できない。credential-process は接続性が戻ったときにオンデマンドで取得する |
| スケール / コスト | SSM のノード登録料金またはノード単位の管理料金は不要。機能使用料金は別 | IAM Roles Anywhere の quota と PKI 運用要件を確認 |
| 一般的な選択 | 既存の PKI がない場合。より簡単な登録 | 既存の PKI と管理された証明書ライフサイクル |

**料金確認日: 2026年9月16日:** SSM は 2026 年 6 月 30 日付で Advanced Instances Tier を廃止しました。Session Manager および Run Command の利用規約については[最新の SSM 料金](https://aws.amazon.com/systems-manager/pricing/)を確認してください。[EKS Hybrid Nodes の vCPU 料金](https://aws.amazon.com/eks/pricing/)は別です。

Roles Anywhere profile はカスタム role session name を受け入れる必要があり、trust policy は選択した certificate attribute にそれをバインドする必要があります。その実効セッション期間は IAM role の最大値を**超えてはなりません**。CreateSession API では同じ値が許可されます。[前提条件](01-prerequisites.md)で、これらの契約と安全な準備について詳しく説明しています。

## ワークロード例

1. 検証済みのランタイムと復旧計画を備えたローカル GPU トレーニングまたは推論。
2. AWS のメタデータ/テレメトリ/egress パスを個別にレビューしたローカルデータ処理。
3. 信頼性の高い接続性とテスト済みの切断時動作を備えた工場/エッジアプリケーション。
4. 大規模な既存データセットの近くで行うメディア処理。

## 次のステップ

まず [前提条件とシステム要件](01-prerequisites.md)を確認し、環境が EKS Hybrid Nodes に対応していることを確かめてください。

## クイズ

EKS Hybrid Nodes に関する理解を確認するには、次のクイズに挑戦してください。

* [EKS Hybrid Nodes 前提条件クイズ](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodes ネットワーク設定クイズ](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodes 制限されたインターネット環境のセットアップクイズ](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodes ノードブートストラップクイズ](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid Nodes GPU 統合クイズ](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodes ワークロード配置クイズ](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [ノードライフサイクル管理クイズ](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodes 運用クイズ](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [ベアメタルサーバー OS インストールおよび移行クイズ](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodes Gateway クイズ](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [ネットワーク分離セキュリティレビュークイズ](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)

## 関連ドキュメント

* [EKS レジリエンシーガイド](../eks/10-eks-resiliency.md) - hybrid 環境における高可用性設定
* [EKS コスト最適化](../eks/07-eks-cost-optimization.md) - コスト管理戦略
* [EKS モニタリングとログ記録](../eks/06-eks-monitoring-logging.md) - 統合モニタリング設定

## 公式ドキュメント

* [AWS EKS Hybrid Nodes 公式ドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [EKS Kubernetes バージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
* [nodeadm ユーザーガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor 公式ドキュメント](https://goharbor.io/docs/)
* [NVIDIA GPU Operator ドキュメント](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Hybrid Nodes ネットワーキングガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Hybrid Nodes CNI 設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Hybrid Nodes トラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Hybrid オペレーティングシステム互換性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybrid 認証情報と IAM role](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [ネットワーク切断中のホスト認証情報](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles Anywhere CreateSession のセマンティクス](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKS 料金](https://aws.amazon.com/eks/pricing/)
