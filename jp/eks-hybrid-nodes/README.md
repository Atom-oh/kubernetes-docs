# EKS Hybrid Nodes

> **サポート対象バージョン**: 現在EKSでサポートされているバージョン。例はEKS 1.36 / nodeadm 1.0.20を対象にレビュー済み
> **最終更新日**: 2026年10月12日

Amazon EKS Hybrid Nodesは、お客様が運用するオンプレミスまたはエッジのノードを、AWSが管理するEKSコントロールプレーンに接続します。ホスト、オペレーティングシステム、接続性、ワークロードの運用は引き続きお客様が担います。このガイドでは、サポートされているインターフェイスと構成例を区別しています。特定のオンプレミスの本番環境へのデプロイがテスト済みであることを示すものではありません。

EKS 1.37は2026年10月1日に利用可能になりました。このガイドの例は引き続きEKS 1.36およびnodeadm 1.0.20を対象にレビューされています。

バージョンを選ぶ前に、[EKSバージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)、Hybrid Nodesのドキュメント、ホストおよびCNIのサポート情報を確認してください。

## 目次

1. [前提条件とシステム要件](01-prerequisites.md)
2. [ネットワーク構成](02-network-configuration.md)
3. [インターネット接続が制限された環境のセットアップ（S3 + VPCエンドポイント）](03-airgap-setup.md)
4. [ノードのブートストラップ](04-node-bootstrap.md)
5. [GPUサーバーの統合](05-gpu-integration.md)
6. [ワークロード配置戦略](06-workload-placement.md)
7. [ノードのライフサイクル管理](07-node-lifecycle.md)
8. [運用とメンテナンス](08-operations.md)
9. [ベアメタルサーバーのOSインストールと移行ガイド](09-bare-metal-os-setup.md)
10. [Hybrid Nodesゲートウェイ](10-hybrid-nodes-gateway.md)
11. [ネットワーク分離のセキュリティレビュー](11-network-separation-security.md)
12. [SNATおよびPrivateLinkを使用しないPod接続](12-connectivity-validation.md)

## Hybrid Nodesとは？

Hybrid Nodesは、通常のAWSコンピューティングノードと同じクラスターを共有できます。クラウドマシンを**hybrid**ノードとして登録することは別の話です。AWSは、AWSリージョン、Local Zones、Outposts、その他のクラウドにおけるhybridノードのインフラストラクチャをサポートしておらず、EC2を使用する場合もhybrid料金が発生します。

![オンプレミスのルーターとゲートウェイから、AWSクラスターVPC内のコントロールプレーンENIまでを示すEKS Hybrid Nodesネットワークの概要図。](../.gitbook/assets/en-eks-hybrid-nodes-highlevel-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-highlevel-0.html)

次の図は、VPC、サブネット、Transit Gateway/Virtual Private Gateway、Remote Node/Pod CIDRの接続性を含む、ネットワークの前提条件を示しています。

![クラスターのRemoteNodeNetworkおよびRemotePodNetworkの設定を、VPC側とオンプレミス側の両方のルートテーブルに関連付けたHybrid Nodesの前提条件図。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

この図が示しているのはプライベート接続とルーティングであり、オンプレミスのすべてのルート、ファイアウォールルール、AWSサービスエンドポイントが自動的に作成されることではありません。

セキュリティチームによるレビューには、[ネットワーク分離レビューガイド](11-network-separation-security.md)を使用してください。このガイドでは、プライベートクラスターエンドポイント、EKS ENI、AWSサービスのPrivateLinkエンドポイントを区別し、DXをまたぐ管理接続とデータ境界について確認すべき証跡を示しています。

## ユースケースとデータ境界

オンプレミスのGPU、大規模なローカルデータセット、エッジ処理、既存のハードウェアは、Hybrid Nodesを利用する理由になり得ます。データローカリティの要件を満たすには、アプリケーション、ストレージ、エグレス、ロギングに関する制御も必要です。Kubernetes APIオブジェクトとコントロールプレーンのメタデータはAWSで管理されます。ノードセレクターだけでは、データ主権や規制遵守は確立されません。

`on-premises`という名前のAWSゾーンが存在すると仮定せず、実際のhybridコンピューティングラベルと、明示的に管理された組織ラベルを配置に使用してください。

```yaml
# Pod spec fragment; set organization labels through the node owner.
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  example.com/data-location: on-premises
```

この断片は、ラベル、完全なアプリケーション、セキュリティ境界、データ保持ポリシーを作成するものではありません。イメージおよびランタイムの互換性と、実際のデータ経路を検証してください。

## アーキテクチャと責任範囲

| コンポーネント | 場所 | 責任 |
|-----------|----------|----------------|
| EKS APIサーバー、etcd、コントローラー、スケジューラー | AWS | AWSが管理するコントロールプレーン |
| nodeadm | オンプレミスのサポート対象Linuxホスト | インストール/ブートストラップ/アップグレード用CLI。長時間稼働するノードエージェントではない |
| kubelet / containerd | オンプレミス | ノードエージェント / CRIランタイム。ホストの所有者が運用 |
| CiliumまたはCalico | オンプレミスおよびクラスター | 互換性のあるCNI構成。VPC CNIはhybridノードを管理しない |
| SSM AgentまたはRoles Anywhere署名ヘルパー | オンプレミス | 対応するAWSサービスから一時的な認証情報を取得 |
| SSM / IAM Roles Anywhereサービス | AWS | 認証情報サービス。ローカルのオフラインCAの代替ではない |
| VPN / Direct Connectおよびルーティング | 両環境 | 双方向接続。Direct Connectだけでは暗号化されているとは限らない |

Bottlerocketのサポート対象VMwareバリアントは独自のブートストラップ手順を使用し、nodeadmは使用しません。その他のサポート対象ホストでは、`nodeadm install`が依存関係をインストールし、`nodeadm init`がノードを構成してクラスターに参加させます。SSMを使用する新規インストール/アップグレードには、SSM署名キーの変更に対応するため、**nodeadm 1.0.19以降**が必要です。レビュー済みの現行リリースは**1.0.20**です。

## 計画時に考慮すべき制約

- **接続環境:** AWSへの信頼性の高いプライベートな双方向接続が必要です。Hybrid Nodesは、接続が切断された状態や断続的なDDIL運用を目的としていません。このガイドでいう「エアギャップ」とは、必要なAWS接続を保ちながらインターネットアクセスを制限した状態であり、AWSからの隔離ではありません。
- **アドレス:** IPv4 RFC1918またはCGNATの範囲を使用し、リモートノード/Pod、VPC、サービスの各CIDR範囲が重複しないようにします。クラスターごとに最大**15個のノードCIDRと15個のPod CIDR**がサポートされています。
- **認証:** `API`または`API_AND_CONFIG_MAP`を使用し、Hybrid Nodes用のIAMロール/アクセスエントリを準備してください。
- **APIエンドポイント:** AWSはパブリックのみ、またはプライベートのみの設定を推奨しています。両方を有効にすると、VPC外のノードはパブリックエンドポイントのアドレスを解決します。想定される経路/アクセスルールがプライベートの場合、これによってノードがクラスターに参加できなくなる**可能性があります**。これはAPI全般の禁止ではありません。APIエンドポイントがパブリックであっても、コントロールプレーンからノードへのプライベート接続要件はなくなりません。
- **リージョン:** 現行の概要によると、AWS GovCloud（米国）およびAWS中国リージョンを除き利用できます。
- **ホストのサポート:** OS、アーキテクチャ、CNI、カーネルを併せて確認してください。AL2023はオンプレミスの仮想化環境向けであり、一般的なベアメタル向けの推奨ではありません。
- **料金:** Hybrid料金は、ノードが接続されている間に報告されるvCPU時間に基づきます。ハイパースレッディングが有効なベアメタルコアは、2つのvCPUとして報告される場合があります。ワークロードがアイドル状態でも、ノード料金が自動的に停止するわけではありません。クラスター料金およびその他のサービス料金は別途発生します。

## 認証情報プロバイダー

どちらのプロバイダーも、認証情報を更新するためにAWSサービスエンドポイントへのアクセスが必要です。ローカルCAがあっても、IAM Roles AnywhereがオフラインでAWS認証情報を発行できるわけではありません。プロバイダーを混在させる理由がレビュー済みでない限り、フリート全体で一貫して同じプロバイダーを使用してください。

| トピック | SSMハイブリッドアクティベーション | IAM Roles Anywhere |
|-------|------------------------|--------------------|
| ブートストラップ | アクティベーションID/コードと、SSMを信頼するように準備されたロール | PKI、ノードごとの証明書/キー、信頼アンカー、プロファイル、ロール |
| 命名 | SSMが生成する`mi-...`形式の名前 | 証明書のIDに関連付けられたカスタムノード名 |
| セッション期間 | 固定の1時間。SSMが更新 | デフォルトは1時間。サポートされるリクエスト/プロファイルの期間は15分～12時間で、有効期間とロールの最大値に従う |
| 切断時 | 更新できない。ネットワーク復旧後、再接続までの再試行バックオフにより遅延が生じる場合がある | オフラインでは新しい認証情報を取得できない。接続が回復すると、credential-processが必要に応じて認証情報を取得する |
| 規模/コスト | SSMのノード登録料金やノードごとの管理料金はない。機能の使用料金は別途 | IAM Roles AnywhereのクォータとPKI運用要件を確認 |
| 一般的な選択基準 | 既存のPKIがなく、登録を簡素化したい場合 | 既存のPKIがあり、証明書のライフサイクルを管理している場合 |

**2026年9月16日確認の料金情報:** SSMのAdvanced Instances Tierは2026年6月30日をもって廃止されました。Session ManagerおよびRun Commandの使用条件については、[現在のSSM料金](https://aws.amazon.com/systems-manager/pricing/)を確認してください。[EKS Hybrid NodesのvCPU料金](https://aws.amazon.com/eks/pricing/)は引き続き別途発生します。

Roles Anywhereプロファイルではカスタムロールセッション名を受け入れる必要があり、信頼ポリシーではその名前を選択した証明書属性に関連付ける必要があります。有効なセッション期間は、IAMロールの最大期間を**超えてはなりません**。CreateSession APIでは、最大期間と同じ値を指定できます。[前提条件](01-prerequisites.md)では、これらの要件と安全な準備について詳しく説明しています。

## ワークロードの例

1. ランタイムと復旧計画を検証済みの、ローカルGPUを使用したトレーニングまたは推論。
2. AWSのメタデータ/テレメトリ/エグレス経路を別途レビューした、ローカルデータの処理。
3. 信頼性の高い接続と、切断時の動作をテスト済みの工場/エッジアプリケーション。
4. 既存の大規模データセットの近くで行うメディア処理。

## 次のステップ

EKS Hybrid Nodesに対応できる環境であることを確認するため、まず[前提条件とシステム要件](01-prerequisites.md)を確認してください。

## クイズ

EKS Hybrid Nodesの理解度を確認するには、次のクイズに挑戦してください。

* [EKS Hybrid Nodesの前提条件クイズ](../quizzes/eks-hybrid-nodes/01-prerequisites-quiz.md)
* [EKS Hybrid Nodesのネットワーク構成クイズ](../quizzes/eks-hybrid-nodes/02-network-configuration-quiz.md)
* [EKS Hybrid Nodesのインターネット接続が制限された環境のセットアップクイズ](../quizzes/eks-hybrid-nodes/03-airgap-setup-quiz.md)
* [EKS Hybrid Nodesのノードブートストラップクイズ](../quizzes/eks-hybrid-nodes/04-node-bootstrap-quiz.md)
* [EKS Hybrid NodesのGPU統合クイズ](../quizzes/eks-hybrid-nodes/05-gpu-integration-quiz.md)
* [EKS Hybrid Nodesのワークロード配置クイズ](../quizzes/eks-hybrid-nodes/06-workload-placement-quiz.md)
* [ノードのライフサイクル管理クイズ](../quizzes/eks-hybrid-nodes/07-node-lifecycle-quiz.md)
* [EKS Hybrid Nodesの運用クイズ](../quizzes/eks-hybrid-nodes/08-operations-quiz.md)
* [ベアメタルサーバーのOSインストールと移行クイズ](../quizzes/eks-hybrid-nodes/09-bare-metal-os-setup-quiz.md)
* [EKS Hybrid Nodesゲートウェイクイズ](../quizzes/eks-hybrid-nodes/10-hybrid-nodes-gateway-quiz.md)
* [ネットワーク分離のセキュリティレビュークイズ](../quizzes/eks-hybrid-nodes/11-network-separation-security-quiz.md)
* [SNATおよびPrivateLinkを使用しないPod接続クイズ](../quizzes/eks-hybrid-nodes/12-connectivity-validation-quiz.md)

## 関連ドキュメント

* [EKSの耐障害性ガイド](../eks/10-eks-resiliency.md) - ハイブリッド環境における高可用性の構成
* [EKSのコスト最適化](../eks/07-eks-cost-optimization.md) - コスト管理戦略
* [EKSのモニタリングとロギング](../eks/06-eks-monitoring-logging.md) - 統合モニタリングの構成

## 公式ドキュメント

* [AWS EKS Hybrid Nodes公式ドキュメント](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-overview.html)
* [EKS Kubernetesバージョンカレンダー](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
* [nodeadmユーザーガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
* [Harbor公式ドキュメント](https://goharbor.io/docs/)
* [NVIDIA GPU Operatorドキュメント](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
* [Hybrid Nodesネットワーキングガイド](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
* [Hybrid NodesのCNI構成](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
* [Hybrid Nodesのトラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-troubleshooting.html)

* [Hybrid Nodesのオペレーティングシステム互換性](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
* [Hybridの認証情報とIAMロール](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
* [ネットワーク切断時のホスト認証情報](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
* [IAM Roles AnywhereのCreateSessionの仕様](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
* [EKSの料金](https://aws.amazon.com/eks/pricing/)
