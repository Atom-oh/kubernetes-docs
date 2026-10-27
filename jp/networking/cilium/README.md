# Ciliumの詳細解説：クラウドネイティブネットワーキングの未来

## 概要とレビュー済みベースライン

このセクションでは、Ciliumのネットワーキング、ポリシー、可観測性を取り上げます。各例は **Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1**、Hubble CLI **1.20.2** に照らしてレビューしています。Cilium 1.20のKubernetes互換性ページでは、テスト済みバージョンとして **1.33～1.36** が記載されています。上流の1.37リリースがあっても、この対応範囲が自動的に拡張されるわけではありません。サポート対象のホストは、カーネル **5.10以降**を搭載したAMD64/AArch64 Linux、またはRHEL 8.10のバックポート版4.18カーネルのように、文書に記載されたディストリビューション固有の同等環境です。個々の機能には、追加の要件があります。

> **最終更新日**: 2026年10月26日

### 過去のリリースノート

以下の日付はUTCでのGitHub公開日であり、現在のインストール時の固定バージョンではなく、それぞれのリリースについて記載しています。機能のバックポート内容はリリース系列によって異なります。

| 日付 | リリース | 確認済みの主な内容 |
| --- | --- | --- |
| 2026年7月14日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20の最初のリリース候補 |
| 2026年7月16日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gatewayのアクセスログ設定は1.19.6/1.18.12に記載されています。ここで取り上げる再起動ポリシーとClusterMeshのアフィニティ修正は、3つすべてのリリースではなく、1.19.6に記載されています |
| 2026年7月21日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20の2番目のリリース候補 |
| 2026年7月29日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GAリリース。主な変更点は以下を参照 |
| 2026年8月3日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 次のサイクルのプレリリース。このガイドのデプロイベースラインではありません |
| 2026年8月18日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | 再起動/CIDRポリシー処理などのClusterMeshに関するドキュメントとバグ修正 |
| 2026年8月18日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENIインターフェースのタイミング、Service/LBなどの修正を含む |
| 2026年8月18日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMPのホストファイアウォールサポートと関連する修正 |
| 2026年9月9日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | プレリリース。変更履歴の対象はpre.0からpre.2までです。**1.21.0-pre.1は公開されていません** |
| 2026年9月16日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | ENI IPAMのプレフィックス委任における割り当て/解放とセカンダリVPC CIDR処理、ClusterMesh、ポリシー変更直後に作成されたPodに対するポリシーリビジョン、LocalRedirectPolicyのリグレッション、v1.15以前で作成されたクラスターのアップグレード（`CiliumNodeConfig v2alpha1` CRDバージョン）などのバグ修正 |
| 2026年9月16日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | サポート対象の旧系列のパッチリリース |
| 2026年10月2日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 1.21の最新プレリリース。**1.21はプレリリースのみ**（GAはまだありません）で、このガイドで1.21と記載されている項目は変更される可能性があります |
| 2026年10月15日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API依存関係のv1.6.3、conntrack GC、`nodeSelector`を含むCNPの処理などの修正。このガイドで現在レビュー済みのベースライン |
| 2026年10月15日 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9), [1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | サポート対象の旧系列のパッチリリース |
| 2026年10月23日 | [1.20.4](https://github.com/cilium/cilium/releases/tag/v1.20.4), [1.19.10](https://github.com/cilium/cilium/releases/tag/v1.19.10), [1.18.16](https://github.com/cilium/cilium/releases/tag/v1.18.16) | CVE-2026-111943に対する臨時セキュリティパッチリリース。Goを1.26.10にアップグレードし、侵害されたeMudhra中間CA証明書が信頼されなくなったほか、依存関係のパッチ更新とバックポート修正を含む |

2026年9月14日、CNCFブログで[ Cilium 1.20の機能まとめ](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)が公開されました（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAMなど）。その内容は、以下の1.20.0発表の概要と同じ範囲を扱っています。

1.20.0の発表によると、新しいコミットは **2,660件以上**で、**1,100人以上の貢献者からなるコミュニティ**に支えられています。後者はコミュニティの規模であり、このリリースの著者数ではありません。主な内容は以下のとおりです。

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth、CORSサポート。ただし、それぞれの機能の設定やAPIの成熟度によって利用条件が異なります。
- データパスプラグインと、オプトインの`bpf.datapathMode=auto`。発表時点のデフォルトは引き続きvethです。デュアルスタッククラスターでは、IPv6のegress gatewayアドレスを設定できます。
- **ベータ版**のIPv6 ENI IPAMと、クラスターを再構築せずにcluster-poolからmulti-poolへ移行する機能。インプレース移行でも中断が発生しないとは限りません。
- トラフィック分散ヒント、重み付きMaglevバックエンド、安定版のMCS統合、Kubernetes ClusterNetworkPolicyサポート、**ベータ版**のztunnelベースのワークロードID。
- `cilium-cni`バイナリが約 **77 MBから16 MBに縮小した**との報告。ADS/Delta xDSの改善は1.20の発表に記載されており、1.18.13のパッチノートの内容として扱わないでください。これらは上流リリースの発表内容であり、この監査で再計測した値ではありません。

相互認証（**1.20で非推奨**、1.21のプレリリースで削除）、削除または置き換えられたEnvoy Go拡張、Kafka対応ポリシー、旧CiliumNodeConfig API、libnetwork統合、カスタムCNI設定の変更については、[1.20のアップグレードノート](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)を確認してください。

### NetworkPolicyセキュリティ勧告

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r)のプロジェクト勧告公開日は **2026年7月6日**です。プロジェクトAPIとGitHubのグローバル勧告APIでは、異なる日付が公開されています。後者には9月3日と記録されています。このリリース年表ではプロジェクトの開示日を使用してください。グローバル記録の日付は、より後の修正リリースを意味するものではありません。この問題は、勧告に記載されたカスタムクラスター名の条件下で **1.19.0～1.19.4** に影響します。`ipBlock`のみを含む標準のKubernetes NetworkPolicyのピアにより、選択されたPodと同じnamespaceにあるワークロードからのingressが意図せず許可される可能性があります。**1.19.5**で修正されています。デプロイには、適切な最新のパッチ適用済みリリースを使用してください。この勧告によると、CiliumNetworkPolicy/ClusterwideNetworkPolicyと1.19.0未満のリリースは、この特定のバグの影響を受けません。

## はじめに

Ciliumは、サポート対象のLinux Kubernetes環境向けに、ネットワーキング、セキュリティ、可観測性を提供します。ルーティング、IPAM、暗号化、Service処理はそれぞれ別の選択項目です。eBPFを選択しただけでは、すべての機能や性能が保証されるわけではありません。従来のDocker libnetwork統合は1.20で削除されたため、Docker/Mesosを現在の同等なインストール対象としてここに列挙すべきではありません。

### eBPFと主な機能

カーネルはeBPFプログラムをロード前に検証し、サポート対象のフックで実行できるようJITコンパイルすることがあります。これにより、カスタムカーネルモジュールなしでパケット処理や可観測性を実現できます。ただし、verifierはアプリケーションやポリシーの正しさを保証するものではありません。実際のスループット、レイテンシ、メモリ使用量は、プログラム、プラットフォーム、ワークロードによって異なります。

Ciliumは、L3/L4ポリシー、Envoy/DNSプロキシ統合によるL7ポリシー、オプションのWireGuard/IPsec、Serviceのロードバランシング、Hubbleによるフロー可視化、ClusterMesh、BGPアドバタイズメントを提供します。XDPアクセラレーションはオプションで、デバイスや設定に依存します。L7機能ではノードごとのEnvoyを使用する場合があります。ztunnelによるワークロードIDには、別途ベータ機能の設定が必要です。エージェントをインストールしただけでは、すべてのメッシュ、暗号化、マルチクラスター機能が有効になるわけではありません。

### 他のネットワーキングプロジェクトとの比較

| プロジェクト | 接続性 / IPAM | ポリシーと関連機能 |
| --- | --- | --- |
| Cilium | ネイティブまたはオーバーレイルーティング。クラウドENIを含むIPAMモード | eBPFデータプレーン、Cilium/Kubernetesポリシー、L7統合、Hubble、オプションの暗号化 |
| Calico | Calicoまたは外部IPAMを使うネイティブ/IPIP/VXLANプロファイル | Linux Iptables/Nftables/BPF、サポート対象のWindows HNS、OSS WireGuard、段階的なポリシー、個別のL7統合 |
| Flannel | VXLAN/host-gw/WireGuardなど、選択したバックエンドによるPod接続 | ルーティングデーモンはNetworkPolicyを適用しません。chartでは`netpol.enabled`を使ってSIGs network-policy controllerをデプロイできます。または、別のポリシー実装と組み合わせることもできます |
| AWS VPC CNI | VPC ENIのアドレス割り当て/ネットワーキング | サポート対象のEC2 Linuxノード上でのネイティブネットワークポリシーと、独立したSG-for-Pods機能。EKS Auto Modeは異なるマネージド実装です |

ルーティングモードとパケット処理の実装は、同じカテゴリではありません。Calicoはiptables/IPVSに限られず、Flannelは暗号化バックエンドを使用でき、AWSのポリシーはセキュリティグループと同義ではありません。Service meshはオプションのレイヤーであり、クラスター間のVPC接続がTransit Gatewayに限られるわけでもありません。普遍的な性能ランキングではなく、実測したワークロードと明示的なサポートマトリクスを使用してください。

## アーキテクチャ

**Kubernetes API server**はKubernetes/Ciliumリソースを保存します。Cilium agentは関連する状態を監視し、各ノードのデータプレーンを設定します。Cilium Operatorは、選択したIPAMやID/コントローラー関連の処理など、クラスター単位の責務を担います。この基本アーキテクチャに、クラスター全体で必須となる独立した「Cilium API Server」のデプロイはありません。エージェントはローカルAPIを備えており、オプションのClusterMesh API serverは別の目的で使用されます。

| コンポーネント | 役割 |
| --- | --- |
| Cilium Agent | ノードローカルのエンドポイント、ポリシー、ルーティング/Service状態、eBPFの管理 |
| Cilium Operator | クラスター単位の調整と、モードに応じた割り当て/コントローラー処理 |
| Envoy | 有効化されたL7ポリシー、ingress/Gateway、関連機能向けのユーザー空間プロキシ |
| Hubble server | エージェントと統合されたノードローカルのフローAPI |
| Hubble Relay / UI | フローストリームの集約 / Serviceマップとフローの表示 |
| Prometheus metrics endpoints | 独立した統計情報収集。Relay/UIはメトリクスのスクレイピングパイプラインではありません |
| cilium / cilium-dbg / hubble | それぞれクラスター管理CLI / エージェントの診断 / フロークライアント |

### ネットワーキングとパケット経路

ネイティブルーティングには到達可能なアンダーレイが必要です。トンネリングにはVXLANまたはGeneveを使用します。AWS ENIやAzure IPAMは、独自のプラットフォーム要件を持つ割り当て/統合方式です。CiliumのBGP Control Planeはルーターに到達可能性をアドバタイズしますが、**データパスを設定するものでも、クラスター内部のルーティングを提供するものでもありません**。

XDP→TC→Podという一律の順序はありません。ソケットロードバランシングはパケットが生成される前に動作する場合があり、TC/netkitフックはデータパスによって異なります。オプションのXDPは選択したトラフィックを高速化し、L7トラフィックはEnvoyを経由する場合があります。戻りトラフィックも、NAT、conntrack、DSRの選択に依存します。選択したプロファイルについては、ネットワーキングとeBPFの各章を参照してください。

## Amazon EKSとの統合

何かをインストールする前に、実際のネットワーキングとコンピューティングのプロファイルを選択してください。アドオン名/バージョンの例である`cilium` / `v1.17.0-eksbuild.1`は、AWSのディストリビューションとして確認されておらず、ここではインストールコマンドとして扱いません。ベンダーパッケージのアドオンを検討する場合は、対象リージョンの実際のアドオンカタログ、公開元、ライセンス、サポート対象のコンピューティングタイプを確認してください。

| EKSプロファイル | 確認事項 |
| --- | --- |
| 通常のEC2ノードで、Cilium ENIがVPC CNIを置き換える | 上流/パートナー管理のCNI。AWSがサポートするEC2 CNIはVPC CNIです。CNIの管理主体、IAM、アドレス指定、ルート、ブートストラップ、ノード移行を計画してください |
| 通常のEC2ノードで、AWS VPC CNIとチェーン接続する | VPC CNIがインターフェース/IPAMを管理し、その後Ciliumがデータプレーンを追加します。既存のPodは再作成が必要で、L7/IPsecには文書化された制限があります |
| Hybrid Nodes | AWSの専用CNIガイドとAWSが管理するCiliumビルドマトリクスに従ってください。上流の1.20.3が、自動的にAWSのサポート対象ビルドになるわけではありません |
| Auto Mode | 代替のCNI/ポリシープラグインはサポートされていません。マネージドNodeClass/ネットワーキング機能を使用してください |
| Fargate | 代替のCNI/DaemonSetのインストールはサポートされていません |
| Windows | Cilium agentの要件はLinuxです。この手順をWindowsワーカーに適用しないでください |

AWSの一般的な代替CNIページと専用のHybridガイドでは、Calicoのサポートに関する記述が異なります。リポジトリを移動する例があっても、サポート終了を意味するわけではありません。Hybrid Nodesでは、正確なディストリビューション、機能セット、サポート担当者を確認してください。Auto Modeでは、ノードローカルのCoreDNS/システムネットワーキングも、このガイドに記載する通常のEC2構成とは異なります。Auto Mode以外のノードが混在する場合は、従来型のDNS Deploymentも引き続き必要です。

### Cilium ENIを使う、準備済みEC2クラスター

以下は、**準備済みのIPv4 EC2クラスター向けCilium Helm values**であり、クラスター作成手順やインプレース移行手順を網羅するものではありません。使用する前に、次の点を確認してください。

1. サポート対象のEKS/KubernetesバージョンとLinux AMIを選び、CNIの管理主体を1つに定めます。既存のワークロードクラスターから`aws-node`を削除することを近道にしないでください。
2. Ciliumがノードを管理するまでワークロードが待機するよう、ノードのtaintとスケジューリングを準備します。上流のEKSガイダンスでは`node.cilium.io/agent-not-ready=true:NoExecute`を使用します。実際のノードライフサイクルにおける退避とブートストラップへの影響を評価してください。
3. サブネット容量、ENIクォータ/セキュリティグループ、ノードのメタデータアクセス、Operatorに必要なEC2権限を準備します。以下のロールARNは、適切に信頼関係を設定した**cilium-operator ServiceAccount**用ロールのプレースホルダーであり、valuesファイルで作成されるロールではありません。
4. `kubeProxyReplacement: false`のこの例では、動作中のkube-proxyとDNSを維持してください。置き換えモードでは、APIへの直接アクセスとブートストラップDNSに関する別の要件に従ってください。max-Podsは一律に110とせず、実際のインスタンス/IPAM容量から選択してください。

`cilium-eni-values.yaml`として保存し、ロールとインターフェースの選択をレビュー済みの値に置き換えてください。

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
# egressMasqueradeInterfaces is intentionally omitted: it only affects iptables masquerade,
# and ENI mode leaves IPv4 masquerade off by default since 1.18.
serviceAccounts:
  operator:
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/CiliumOperatorENI
```

```bash
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-eni-values.yaml
```

これらの設定は、インストールの管理主体を通じて管理してください。必要な設定がほかにもあるのに、少数のキーだけを含む`cilium-config`で置き換えると、それらが失われる可能性があります。従来の`tunnel=disabled`は`routingMode: native`に置き換えられています。ENIの割り当て/権限とSNATの動作については、引き続き実行時の検証が必要です。設定のrenderに成功しただけでは、EC2ネットワーキングが使用可能である証明にはなりません。

**IPv6に関する補足:** 1.20.3のENI IPAMリファレンスではIPv6をベータ版と記載していますが、EKSの前提条件ページにはIPv4のみのENI統合と記載されたままです。このガイドではIPv4の例を示し、どちらの記述も本番環境でのEKS IPv6互換性の証明として扱わず、ドキュメント間の不整合を記録しています。IPv6を別途設計する前に、現在のENI/デュアルスタックのサブネット要件を確認してください。

### VPC CNIとのチェーン接続を使う代替構成

上流のチェーン接続ガイドでは、VPC CNI 1.11.2以降が必要とされ、次のプロファイルが記載されています。

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

これは**別の設定**として使用し、ENI置き換えの値に重ねないでください。割り当ては引き続きVPC CNIが行います。実際のマネージドアドオンは、過去の上流DaemonSetを適用するのではなく、その管理主体を通じてアップグレードしてください。同じエンドポイントで複数のポリシーエンジンが競合しないようにしてください。CNIチェーンを変更しても、既存のPodが遡ってCiliumに接続されるわけではありません。計画したロールアウトのもとでPodを再作成し、エンドポイントが管理されていることを確認してください。チェーン接続にはL7ポリシー/IPsecに関する文書化された制限があるため、このページの後半にあるすべての例がそのプロファイルで動作するとは限りません。

### ClusterMesh

ClusterMeshには、一意のクラスターID、互換性のあるバージョン、相互に到達可能で重複しないPodネットワーク、認証されたAPI接続、適切な公開モデルが必要です。LoadBalancer Serviceを使用するとクラウドリソースが作成されることがあり、意図的なネットワーク/セキュリティ設計が必要です。2つの公開エンドポイントを作成するだけでは、クラスターを安全に接続できません。選択したトポロジーについて、メンテナンスされている[ClusterMeshガイド](13-clustermesh-install-upgrade.md)と詳細解説の章に従ってください。

## インストールと設定

### クライアントツール

ワークステーションのOS/アーキテクチャに合った公式Cilium CLI 0.20.1およびHubble CLI 1.20.2のアセットを使用し、展開前に提供されたチェックサムを検証してください。Linux ARM64とAMD64ではアセットが異なります。macOSでは対応するDarwinアセットを使用します。CLIのバージョンはCilium agent/chartのバージョンとは別です。[検証済みCLIインストールガイダンス](../../service-mesh/cilium-service-mesh/README.md)を参照してください。

```bash
cilium version --client
hubble version
```

### クラウドを使わないcluster-poolの例

以下の**別の構成例**は、kube-proxyとDNSがすでに動作している、準備済みの通常のLinuxクラスター向けです。例の`10.244.0.0/16` Pod範囲がクラスターと互換性があり、Service、ノード、VPC、接続されたネットワークの範囲と重複しないことを確認してください。ENIモードではこのpool設定を使用しないでください。

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

`cilium-values.yaml`として保存し、固定したchartをrenderしてから、準備済みのクラスターにのみインストールしてください。

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

既存のリリースでは、そのアップグレード/GitOpsプロセスを使用し、管理対象の値を保持して、バージョンごとのアップグレード手順に従ってください。`cilium install`を繰り返し実行する例は、個々の設定を変更するための汎用的な方法ではありません。

| 選択項目 | 現行の設定と前提条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel`と`tunnelProtocol`を設定し、選択したカプセル化方式を許可して、経路に合わせてMTUを設定 |
| ネイティブルーティング | `routingMode: native`を設定。アンダーレイがPodアドレスをルーティングできる必要があります。`autoDirectNodeRoutes`には適切な直接接続性が必要であり、任意の複数サブネット間ルーティングに対応するものではありません |
| kube-proxyの置き換え | 従来の`strict`ではなく、`kubeProxyReplacement: true`または`false`を設定。置き換えには、到達可能な`k8sServiceHost`/`k8sServicePort`と、文書化されたブートストラップ計画が必要です |
| WireGuard | カーネル/プラットフォームとピア間の経路を確認してから、サポート対象の暗号化モードを有効化します。あらゆるトラフィック経路が自動的に暗号化されるわけではありません |
| IPsec | 文書化された鍵Secret、鍵の配布/ローテーション、互換性のあるモードが必要です。Helmの有効化フラグだけでは不十分です |
| XDP/DSR/BBR | デバイス/カーネル/トポロジーに依存する個別の選択肢であり、どの環境にも使えるインストールプリセットではありません |

## ネットワークポリシー

Kubernetesの`networking.k8s.io/v1` NetworkPolicyとCiliumの`cilium.io/v2`ポリシーは、別個のAPIです。複数のallowポリシーは組み合わさることがあります。以下の例では、L4のallowによってL7制限が意図せず迂回されないよう、**事前に準備した別々のテストnamespace**を使用します。結論を出す前に、実際のエンドポイントを選択するすべてのポリシーを確認してください。

### L4の例

`cilium-l4-demo`では、バックエンドPodを選択し、同じnamespace内のフロントエンドPodからTCP 8080へのingressを許可します。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: cilium-l4-demo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
      protocol: TCP
```

### HTTPの例

別の`cilium-l7-demo` namespaceでは、バックエンドPodを選択し、そのnamespace内のフロントエンドPodから、指定されたメソッド/パスに対するTCP 8080上の平文HTTPのみを許可します。選択したCNIモードでL7プロキシを利用できる必要があります。サポート対象の終端設定がなければ、暗号化されたHTTPは自動的に検査されません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-product-read
  namespace: cilium-l7-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-l7-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/api/v1/products$
```

同じピア/ポートに対して、対応する制限のないL4 allowを追加しないでください。そのようなallowを設定すると、より限定的なL7制限の効果が失われるとCiliumのドキュメントに記載されています。L7で拒否した場合、パケットをdropするのではなくHTTP 403を返すことがあります。実際のエンドポイントIDを使って、許可されるGETリクエストと拒否されるメソッド/パスをテストしてください。

### DNS/FQDNの例

`cilium-dns-demo`では、通常のCoreDNS PodへのDNSクエリと、`api.example.com`について学習されたアドレスへのTCP 443を許可します。このドメイン名は例です。承認済みの宛先に置き換えてください。広範な`*.amazonaws.com`ワイルドカードは、アカウント/リソースの境界を表すものではないため省略しています。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-api-domain
  namespace: cilium-dns-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:k8s-app: kube-dns
        k8s:io.kubernetes.pod.namespace: kube-system
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

DNSのワイルドカードは、選択されたリゾルバーへのクエリを許可するもので、返されるすべてのアドレスへの接続を許可するものではありません。それでも任意のDNS名を問い合わせられる可能性があるため、必要に応じてDNS検索サフィックスを考慮しながら、クエリ名を制限してください。NodeLocal DNSや別のリゾルバーを使う場合は、宛先を正しく選択する必要があります。FQDNポリシーはDNSから導出したIPの認可であり、TLSホスト名の検証やHTTP URLの認可ではありません。共有IPやアプリケーションのTLS/認証も引き続き重要です。

## Hubbleによる可観測性

上記のcluster-pool valuesでは、Relay/UIとコンポーネントメトリクスが有効になります。既存のインストールでは、Hubbleのvaluesを設定の管理主体を通じて適用してください。`cilium hubble enable --ui`はサポート対象の便利なコマンドですが、`cilium hubble enable --metrics=...`は0.20.1 CLIでサポートされているフラグではありません。代わりに、Helm valuesで`hubble.metrics.enabled`を設定してください。従来の`http`と`httpV2`のハンドラーを同時に有効にしないでください。

一方のターミナルでRelayへのport-forwardを実行したままにします。

```bash
cilium hubble port-forward --port-forward 4245
```

Hubble CLIをインストールした別のターミナルで、次のコマンドを実行します。

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

このローカルの例は、デフォルトのRelay server設定を前提としています。TLSを有効にしたRelayでは、対応するクライアントの信頼設定/認証が必要です。HTTPイベントを取得するには、トラフィックが設定済みのL7プロキシを通過する必要があります。`DROPPED`はデータパスの判定であり、アプリケーションリクエストの失敗すべてを示すものではありません。UIへのport-forwardには`cilium hubble ui`を使用し、Prometheusのターゲット検出はメトリクス用に別途設定してください。Hubbleによるフローのストリーミングだけでは、分散アプリケーショントレーシングにはなりません。

## テストと運用

接続性/性能のコマンドはテスト用ワークロードを作成する場合があり、ポリシーを変更したり、大量のトラフィックを発生させたりする可能性があります。レビュー済みのテストnamespace/環境と権限を使用してください。この監査では、クラスターに対してこれらのコマンドを実行していません。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能サブコマンドは`cilium connectivity perf`です。`connectivity test --test=performance`はテスト名のフィルターを指定するだけで、性能テストを実行するコマンドではありません。スループット/レイテンシを比較する前に、ソフトウェアのバージョン、トポロジー、トラフィック、生データを記録してください。

調査時には、管理CLIと**エージェント側の`cilium-dbg`を区別してください**。

```bash
cilium status --verbose
kubectl get cnp,ccnp -A
kubectl get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent Pod on the affected node.
CILIUM_POD=replace-with-actual-cilium-pod
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl exec -n kube-system "$CILIUM_POD" -c cilium-agent -- cilium-dbg metrics list
kubectl logs -n kube-system "$CILIUM_POD" -c cilium-agent --since=15m --tail=200 --timestamps
```

`cilium endpoint list`、`cilium bpf maps list`、`cilium metrics list`は、管理CLIの同等のコマンドではありません。`cilium sysdump`で診断資料を収集できます。生成されたインフラストラクチャ/ログデータは保護してください。エージェントがReadyであることやスクレイピングに成功したことは、アプリケーションテストやポリシーの否定テストの代わりにはなりません。

### 運用上の優先事項

- mapの事前確保、XDP、DSR、BBR、固定デバイスパターンを有効にする前に測定してください。これらはリソースを消費したりパケット経路を変更したりするため、機能ごとの確認が必要です。
- DNS、API、ID、アプリケーションの依存関係を明示的に許可したうえで、対象範囲を選んでdefault-denyを導入してください。既存の接続だけでなく、新しいPodやアップグレード時の移行も確認してください。
- 暗号化、証明書/鍵のローテーション、ポリシー適用、可観測性は、それぞれ別の受け入れ確認項目として扱ってください。利用可能な管理/復旧経路を維持してください。
- 現在のプラットフォームマトリクスとサポート対象のアップグレード経路を確認してください。過去のリリース発表は、現在のデプロイとの互換性を証明するものではありません。

## 詳細解説の目次

**[Ciliumの概要と基本概念](01-introduction.md)**
- Ciliumの概要と歴史
- コンテナネットワーキングの基礎
- CNI（Container Network Interface）の理解
- Ciliumの差別化要因

**[eBPF技術の詳細解説](02-ebpf.md)**
- eBPF技術の概要と歴史
- カーネル内部でのeBPFの動作
- eBPFプログラムの種類とマップ
- CiliumでのeBPF活用

**[ネットワーキングモデルとVXLAN](03-networking.md)**
- コンテナネットワーキングモデルの比較
- VXLAN技術の詳細解説
- Ciliumのオーバーレイネットワーキング
- 性能最適化手法
- ルーティング方式（カプセル化とネイティブルーティング）
- クラウドプロバイダーのネットワーキング（AWS ENI、Google Cloud）

**[IPAMとネットワークポリシー](04-ipam-policy.md)**
- IPアドレス管理（IPAM）の戦略
- KubernetesとCiliumのIPAM統合
- ネットワークポリシーの設計と実装
- マルチクラスターのシナリオ
- IPAMモードの詳細解説（Cluster Scope、Kubernetes Host Scope、Multi-Pool）
- クラウドプロバイダーのIPAM（Azure IPAM、AWS ENI、GKE）
- CRDベースのIPAM

**[L2-L7ネットワーキングとロードバランシング](05-l2-l7-networking.md)**
- OSIモデルの各レイヤー（L2、L3、L4、L7）の理解
- Ciliumのレイヤー別機能
- Service meshとの統合
- ロードバランシングのアーキテクチャ
- マスカレードの設定と実装モード
- IPv4フラグメントの処理

**[セキュリティと可視性](06-security-visibility.md)**
- Ciliumのセキュリティ機能
- ネットワークの可視化と監視
- Hubbleのアーキテクチャと使い方
- リアルタイムの脅威検出

**[高度なトピックと実際の事例](07-advanced-topics.md)**
- 性能チューニングとトラブルシューティング
- 大規模デプロイ戦略
- 実際のユースケースの事例研究
- 今後のロードマップと開発の方向性

**[eBPFデータパスの内部](08-ebpf-datapath-internals.md)**
- プログラムセット、アタッチポイント、テールコール
- BPFマップの一覧、サイズ設定、コンパイル/ロードの流れ
- ポリシー適用経路とHubbleイベントパイプライン

**[オーバーレイとネイティブルーティング](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI内のID、MTU、パケット経路
- ネイティブルーティング、マスカレード、ホストルーティング、DSR、netkit
- EKSの判断表：オーバーレイ、ENI、VPC CNIチェーン接続の比較

**[IPAMの詳細解説](10-ipam-deep-dive.md)**
- すべてのIPAMモード、サイズ計算、判断マトリクス
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 枯渇時のトラブルシューティングと1.21のAPI変更

**[BGP、ロードバランサーのIP、egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、アドバタイズメント、調査
- L2 announcements、Egress Gateway、Local Redirect Policy
- Gateway APIの要件と、外部に公開しないEKSの公開方式

**[mTLS、暗号化、ID](12-mtls-encryption-identity.md)**
- IDモデル、ポリシーの意味、監査モード
- 相互認証の経緯、ztunnelのワークロードmTLS
- WireGuard、IPsec、Hubble、証明書管理

**[バージョン、インストール/アップグレード、Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17～1.21の機能マトリクス、アップグレードとロールバックのルール
- EKSのインストール固有事項、Cluster Mesh、MCS-API

## 追加リソース

- [ネットワーキング概念の詳細解説](networking-concepts.md)
- [用語集と略語](glossary.md)

## 参考資料

- [Cilium 1.20のKubernetes互換性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Ciliumのシステム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKSの前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWSの代替CNIサポート](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7ポリシーの意味](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubbleプロジェクト](https://github.com/cilium/hubble)
- [Flannelのネットワーキングとポリシー統合](https://github.com/flannel-io/flannel)
- [Calicoの比較用語](../calico/glossary.md)

## クイズ

このセクションで学んだ内容を確認するには、[Cilium詳細解説クイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。
