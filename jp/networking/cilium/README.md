# Cilium詳説：クラウドネイティブネットワーキングの将来

## 概要とレビュー済み基準

この章ではCiliumのネットワーク、ポリシー、可観測性を扱います。例は**Cilium／Helm chart 1.20.3**、Cilium CLI **0.20.1**、Hubble CLI **1.20.2**を基準にレビューしています。Cilium 1.20のKubernetes互換性ページでは**1.33～1.36**がテスト済みとされています。上流の1.37リリースが出ても、この互換性範囲が自動的に広がるわけではありません。サポート対象のホストは、カーネル**5.10以降**のAMD64／AArch64 Linux、またはRHEL 8.10のバックポート済み4.18カーネルのように文書化されたディストリビューション相当環境です。機能ごとに追加要件があります。

> **最終更新日**：2026年10月16日

### 過去のリリースノート

以下の日付はUTCでのGitHub公開日であり、記載したリリースの日付です。現在のインストールバージョンを示すものではありません。機能のバックポート状況はリリース系列ごとに異なります。

| 日付 | リリース | 確認済みの主な内容 |
| --- | --- | --- |
| 2026年7月14日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20最初のリリース候補 |
| 2026年7月16日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6)、[1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12)、[1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gatewayのアクセスログ設定は1.19.6／1.18.12に記載されています。再起動ポリシーとClusterMeshアフィニティの修正は1.19.6に記載され、3つすべてのリリースに含まれるものではありません。 |
| 2026年7月21日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20の2番目のリリース候補 |
| 2026年7月29日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GAリリース。選択した変更点は下記のとおりです。 |
| 2026年8月3日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 次の開発サイクルのプレリリース。本ガイドのデプロイ基準ではありません。 |
| 2026年8月18日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMeshのドキュメントとバグ修正。再起動／CIDRポリシーの処理を含みます。 |
| 2026年8月18日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENIインターフェースのタイミング、Service／LBなどに関する修正を含みます。 |
| 2026年8月18日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP／IGMPのホストファイアウォール対応と関連修正。 |
| 2026年9月9日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | プレリリース。変更履歴はpre.0からpre.2までを対象とします。**1.21.0-pre.1は公開されていません。** |
| 2026年9月16日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | ENI IPAMのプレフィックス委任の割り当て／解放とセカンダリVPC CIDR処理、ClusterMesh、ポリシー変更直後に作成されたPodのポリシーrevision、LocalRedirectPolicyのリグレッション、v1.15以前に作成されたクラスターのアップグレード（`CiliumNodeConfig v2alpha1` CRDバージョン）などのバグ修正。 |
| 2026年9月16日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8)、[1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 以前からサポートされている系列のパッチリリース。 |
| 2026年10月2日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新の1.21プレリリース。**1.21はまだプレリリースのみで、GAではありません**。本ガイドで1.21と記した項目は変更される可能性があります。 |
| 2026年10月15日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API依存関係v1.6.3、conntrack GC、`nodeSelector`を含むCNPの処理などの修正。本ガイドの現在のレビュー基準です。 |

2026年9月14日、CNCFブログで[Cilium 1.20の機能紹介](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)が公開されました（Gateway API ExternalAuth、TCPRoute／UDPRoute、IPv6 ENI IPAMなど）。内容は下記の1.20.0発表概要と同じ範囲です。

1.20.0の発表では、**2,660件超の新しいコミット**が報告されています。これを支えた**1,100人超の貢献者コミュニティ**という数はコミュニティの規模であり、このリリースの作者数ではありません。主な内容は次のとおりです。

- Gateway API **1.6.1**、TCPRoute／UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth、CORS対応。各機能にはそれぞれ設定とAPI成熟度に関する条件があります。
- データパスプラグインと、オプトインの`bpf.datapathMode=auto`。発表時のデフォルトはvethです。デュアルスタッククラスターではIPv6 egress gatewayアドレスを設定できます。
- **Beta**のIPv6 ENI IPAMと、クラスターを再構築せずにcluster-poolからmulti-poolへ移行する機能。インプレース移行で中断が発生しない保証はありません。
- トラフィック分散ヒント、重み付きMaglevバックエンド、安定版MCS連携、Kubernetes ClusterNetworkPolicy対応、**Beta**のztunnelベースワークロードアイデンティティ。
- `cilium-cni`バイナリを約**77 MBから16 MB**へ縮小したとの報告。ADS／Delta xDSの改善は1.20発表に含まれ、1.18.13のパッチノートの内容ではありません。いずれも上流リリースの発表値であり、この監査で再測定していません。

Mutual Authentication（**1.20で非推奨**、1.21プレリリースで削除）、削除／置換されたEnvoy Go拡張、Kafka対応ポリシー、旧CiliumNodeConfig API、libnetwork連携、カスタムCNI設定を使っている場合は、[1.20アップグレードノート](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)を確認してください。

### NetworkPolicyのセキュリティアドバイザリ

[GHSA-fm8w-2m5w-9j7r／CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r)のプロジェクト側アドバイザリ公開日は**2026年7月6日**です。プロジェクトAPIとGitHub全体のアドバイザリAPIでは日付が異なり、後者には9月3日と記録されています。このリリース年表ではプロジェクトの開示日を使います。全体側の記録日がより後の修正リリースを意味するわけではありません。この問題は、アドバイザリに記載された独自のクラスター名条件下で**1.19.0～1.19.4**に影響します。`ipBlock`だけを含む標準Kubernetes NetworkPolicyのpeerにより、選択されたPodと同じNamespaceのワークロードからIngressが意図せず許可される可能性があります。デプロイ時には適切な現行パッチリリースを使用してください。CiliumNetworkPolicy／ClusterwideNetworkPolicyと1.19.0未満のリリースは、この特定のバグの影響を受けないとアドバイザリに記載されています。

## はじめに

Ciliumは、サポート対象のLinux Kubernetes環境向けにネットワーク、セキュリティ、可観測性を提供します。ルーティング、IPAM、暗号化、Service処理はそれぞれ別の選択肢です。eBPFを選んだだけで、すべての機能が使えることや性能が保証されるわけではありません。旧Docker libnetwork連携は1.20で削除されたため、Docker／Mesosを現在のインストール対象として並列に扱わないでください。

### eBPFと主な機能

カーネルはeBPFプログラムをロード前に検証し、対応するフックで実行するためにJITコンパイルできます。これにより、独自のカーネルモジュールを使わずにパケット処理や可観測性を実現できますが、verifierはアプリケーションやポリシーの正しさを保証しません。実際のスループット、レイテンシー、メモリ使用量は、プログラム、プラットフォーム、ワークロードによって異なります。

CiliumはL3／L4ポリシー、Envoy／DNS proxy連携によるL7ポリシー、任意のWireGuard／IPsec、Serviceロードバランシング、Hubbleによるフロー可視化、ClusterMesh、BGP広告を提供します。XDP高速化は任意で、デバイスや設定に依存します。L7機能ではノードごとのEnvoyを使う場合があります。ztunnelによるワークロードアイデンティティには別途Beta設定が必要です。Agentをインストールしただけで、すべてのメッシュ、暗号化、マルチクラスター機能が有効になるわけではありません。

### 他のネットワークプロジェクトとの比較

| プロジェクト | 接続性／IPAM | ポリシーと関連機能 |
| --- | --- | --- |
| Cilium | ネイティブまたはオーバーレイルーティング。クラウドENIを含むIPAMモード | eBPFデータプレーン、Cilium／Kubernetesポリシー、L7連携、Hubble、任意の暗号化 |
| Calico | Calicoまたは外部IPAMによるNative／IPIP／VXLANプロファイル | Linux iptables／nftables／BPF、サポート対象のWindows HNS、OSS WireGuard、段階的ポリシー、別途L7連携 |
| Flannel | VXLAN／host-gw／WireGuardなど選択したバックエンドによるPod接続 | ルーティングデーモン自体はNetworkPolicyを適用しません。Helm chartで`netpol.enabled`を使ってSIGs network-policy controllerを導入するか、別のポリシー実装と組み合わせられます。 |
| AWS VPC CNI | VPC ENIによるアドレス割り当て／ネットワーク | 対応するEC2 Linuxノード上のネイティブネットワークポリシーと、別機能のSecurity Group for Pods。EKS Auto Modeは異なるマネージド実装です。 |

ルーティングモードとパケット処理の実装は、同じ分類ではありません。Calicoはiptables／IPVSだけに限られず、Flannelは暗号化バックエンドを使えます。また、AWSのポリシーが常にセキュリティグループと同義というわけでもありません。Service meshは任意のレイヤーであり、クラスター間VPC接続がTransit Gatewayだけに限られるわけでもありません。普遍的な性能順位ではなく、測定対象のワークロードと明示的なサポートマトリクスを使ってください。

## アーキテクチャ

**Kubernetes APIサーバー**がKubernetes／Ciliumリソースを保存します。Cilium Agentは関連状態を監視して各ノードのデータプレーンを設定し、Cilium Operatorは選択したIPAMやIdentity／Controller処理などクラスター単位の責務を担います。この基本構成に、クラスター全体で必須となる独立した「Cilium API Server」はありません。AgentにはローカルAPIがあり、任意のClusterMesh API Serverは別の目的で使われます。

| コンポーネント | 役割 |
| --- | --- |
| Cilium Agent | ノード単位のエンドポイント、ポリシー、ルーティング／Service状態、eBPF管理 |
| Cilium Operator | クラスター単位の調整と、モードに応じた割り当て／Controller処理 |
| Envoy | 有効化したL7ポリシー、Ingress／Gatewayなどのユーザー空間Proxy |
| Hubble server | Agentと統合されたノードローカルのフローAPI |
| Hubble Relay／UI | フローの集約／Service mapとフローの表示 |
| Prometheusメトリクスエンドポイント | 独立した統計収集。Relay／UIはメトリクスのスクレイプ経路ではありません。 |
| cilium／cilium-dbg／hubble | クラスター管理CLI／Agent診断／フロー参照クライアント |

### ネットワークとパケット経路

Native routingには到達可能なアンダーレイが必要です。トンネリングではVXLANまたはGeneveを使います。AWS ENIとAzure IPAMは、それぞれ固有のプラットフォーム要件を伴う割り当て／連携方式です。CiliumのBGP Control Planeはルーターに到達性を広告しますが、データパスを設定したりクラスター内部のルーティングを提供したりはしません。

XDP→TC→Podという一律の処理順序はありません。ソケットロードバランシングはパケット生成前に動作する場合があり、TC／netkitのフックはデータパスに依存します。任意のXDPは選択したトラフィックを高速化し、L7トラフィックがEnvoyを通る場合もあります。戻り通信もNAT、conntrack、DSRの選択に依存します。選択したプロファイルについて、ネットワークとeBPFの各章を参照してください。

## Amazon EKSとの連携

インストールする前に、実際のネットワーク／コンピュートプロファイルを選んでください。`cilium`／`v1.17.0-eksbuild.1`という例のアドオン名／バージョンは、AWS配布物として確認できていないため、インストールコマンドではありません。パッケージ済みベンダーアドオンを検討する場合は、リージョンの実際のアドオンカタログ、発行元、ライセンス、対応コンピュートタイプを確認してください。

| EKSプロファイル | 確認事項 |
| --- | --- |
| 通常のEC2ノードでCilium ENIがVPC CNIを置き換える | 上流／パートナー管理のCNIです。AWSがEC2向けにサポートするCNIはVPC CNIです。CNI管理、IAM、アドレス、ルート、ブートストラップ、ノード移行を計画してください。 |
| 通常のEC2ノードでVPC CNIチェーンを使う | VPC CNIがインターフェース／IPAMを管理し、その後Ciliumがデータプレーンをアタッチします。既存Podは再作成が必要です。L7／IPsecには文書化された制限があります。 |
| Hybrid Nodes | AWS固有のCNIガイドとAWS管理のCiliumビルドマトリクスに従います。上流1.20.3がAWSのサポート対象ビルドとは限りません。 |
| Auto Mode | 別のCNI／ポリシープラグインは非対応です。マネージドNodeClass／ネットワーク機能を使ってください。 |
| Fargate | 別のCNI／DaemonSetのインストールは非対応です。 |
| Windows | Cilium Agentの要件はLinuxです。この手順をWindowsワーカーに適用しないでください。 |

AWSの一般的な別CNIページとHybrid向け専用ガイドでは、Calicoの対応状況に関する表現が異なります。リポジトリを移動した例があるだけで、サポート終了が確定するわけではありません。Hybrid Nodesでは、正確な配布物、機能範囲、サポート責任者を確認してください。Auto Modeでは、ノードローカルのCoreDNS／システムネットワークも本ガイドの通常EC2構成とは異なります。Auto Modeではないノードが混在する場合、従来のDNS Deploymentも必要です。

### Cilium ENIを使う準備済みEC2クラスター

以下は**準備済みのIPv4 EC2クラスター向けCilium Helm値**です。クラスター作成や稼働中クラスターの移行手順全体ではありません。適用前に次の点を確認します。

1. サポート対象のEKS／KubernetesバージョンとLinux AMIを選び、CNIの管理者を1つに決めます。既存ワークロードクラスターから`aws-node`を近道として削除しないでください。
2. Ciliumがノードを管理するまでワークロードを待機させるため、taint／スケジューリングを準備します。上流EKSガイドは`node.cilium.io/agent-not-ready=true:NoExecute`を使用します。実際のノードライフサイクルで退避／ブートストラップへの影響を評価してください。
3. サブネット容量、ENI quota／security group、ノードのメタデータアクセス、Operatorに必要なEC2権限を準備します。下記ARNは、Helm値で作成するロールではなく、適切な信頼設定を持つ**cilium-operator ServiceAccount用ロール**のプレースホルダーです。
4. `kubeProxyReplacement: false`のこの例では、稼働中のkube-proxyとDNSを維持します。置き換えモードには、APIへの直接接続／ブートストラップDNSに関する別の前提条件があります。max-Podsは一律の110ではなく、実際のインスタンス／IPAM容量から選択してください。

`cilium-eni-values.yaml`として保存し、ロールとインターフェースの値をレビュー済みの内容に置き換えます。

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

これらの設定はインストール管理者を通じて運用してください。必要な値を数個だけ含む`cilium-config`に置き換えると、他の必須設定を削除する可能性があります。古い`tunnel=disabled`値は`routingMode: native`に置き換わっています。ENI割り当て／権限とSNAT動作は実環境で引き続き検証が必要です。レンダリングに成功しただけではEC2ネットワークが利用可能とは証明できません。

**IPv6に関する補足**：1.20.3のENI IPAMリファレンスはIPv6をBetaと説明していますが、EKS前提条件ページにはIPv4のみのENI連携と記載されています。本ガイドではIPv4の例を示し、この文書間の不一致を記録しています。いずれか一方の記述だけを本番EKSのIPv6互換性の証明として扱わないでください。IPv6を別途設計する前に、現在のENI／dual-stackサブネット要件を確認してください。

### VPC CNIチェーンを使う代替方式

上流のチェーンガイドではVPC CNI 1.11.2以降が必要で、次のプロファイルが記載されています。

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

これはENI置き換え設定への上乗せではなく、**別の設定**として使います。VPC CNIが引き続きIPを割り当てます。実際のマネージドアドオンは、古い上流DaemonSetを適用せず、その管理者を通じてアップグレードしてください。同じエンドポイントで複数のポリシーエンジンが競合しないようにします。CNIチェーンを変更しても既存Podに遡ってCiliumが接続されるわけではありません。計画的なロールアウトでPodを再作成し、エンドポイント管理を確認してください。チェーン方式にはL7ポリシー／IPsecの文書化された制限があるため、後述の例がすべてこのプロファイルでも使えると仮定しないでください。

### ClusterMesh

ClusterMeshには、重複しないクラスターID、互換性のあるバージョン、到達可能で重複しないPodネットワーク、認証されたAPI接続、適切な公開方法が必要です。LoadBalancer Serviceはクラウドリソースを作成する可能性があり、ネットワーク／セキュリティを意図的に設計する必要があります。2つのパブリックエンドポイントを作成するだけでは、安全なクラスター接続にはなりません。選択したトポロジーに応じて、保守されている[ClusterMeshガイド](13-clustermesh-install-upgrade.md)と詳細章に従ってください。

## インストールと設定

### クライアントツール

ワークステーションのOS／アーキテクチャに合った公式Cilium CLI 0.20.1とHubble CLI 1.20.2を使い、展開前に配布されたチェックサムを検証してください。Linux ARM64とAMD64では配布物が異なります。macOSでは対応するDarwin配布物を使います。CLIのバージョンはCilium Agent／chartのバージョンとは別です。[検証済みCLIインストール手順](../../service-mesh/cilium-service-mesh/README.md)を参照してください。

```bash
cilium version --client
hubble version
```

### クラウド以外のCluster-Pool例

以下は、kube-proxyとDNSがすでに機能する準備済みの通常Linuxクラスター向けの**代替設定**です。例のPod範囲`10.244.0.0/16`がクラスターと互換性を持ち、Service、ノード、VPC、接続ネットワークの各範囲と重複しないことを確認してください。ENIモードでこのPool設定を使わないでください。

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

`cilium-values.yaml`として保存し、chartを固定バージョンでレンダリングしてから、準備済みクラスターだけにインストールします。

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

既存リリースでは、そのアップグレード／GitOps手順を使い、管理対象の値を保持し、バージョン固有のアップグレード手順に従ってください。設定を個別に変更する一般的な方法として、`cilium install`を繰り返し実行しないでください。

| 選択項目 | 現在の設定と前提条件 |
| --- | --- |
| VXLAN／Geneve | `routingMode: tunnel`と`tunnelProtocol`を設定します。選択したカプセル化通信を許可し、経路に応じてMTUを設定してください。 |
| Native routing | `routingMode: native`を設定し、アンダーレイがPodアドレスをルーティングできる必要があります。`autoDirectNodeRoutes`には適切な直接接続が必要で、任意の複数サブネット間ルーティング向けではありません。 |
| kube-proxy置き換え | 旧`strict`ではなく、`kubeProxyReplacement: true`または`false`を使います。置き換えには到達可能な`k8sServiceHost`／`k8sServicePort`と文書化されたブートストラップ計画が必要です。 |
| WireGuard | カーネル／プラットフォームとピア経路を確認後、サポート対象の暗号化モードを有効にします。あらゆる通信経路が自動的に暗号化されるわけではありません。 |
| IPsec | 文書化された鍵Secret、鍵の配布／ローテーション、互換性のあるモードが必要です。Helmの有効化フラグだけでは設定は完了しません。 |
| XDP／DSR／BBR | デバイス／カーネル／トポロジーに依存する個別の選択肢です。一律に使うインストールプリセットではありません。 |

## ネットワークポリシー

Kubernetesの`networking.k8s.io/v1` NetworkPolicyとCiliumの`cilium.io/v2`ポリシーは異なるAPIです。複数のallowポリシーは組み合わさる場合があります。以下の例は**別々に準備したテストNamespace**を使うため、L4許可がL7制限を意図せず迂回することはありません。結論を出す前に、実際のエンドポイントを選択するすべてのポリシーを確認してください。

### L4の例

`cilium-l4-demo`では、次のポリシーがバックエンドPodを選択し、同じNamespaceのフロントエンドPodからのTCP 8080 ingressを許可します。

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

別の`cilium-l7-demo` Namespaceでは、次のポリシーがバックエンドPodを選択し、そのNamespace内のフロントエンドPodから指定されたmethod／pathへの平文HTTP（TCP 8080）だけを許可します。選択したCNIモードでL7 proxyが利用可能でなければなりません。対応する終端設定なしに、暗号化されたHTTPが自動的に検査されるわけではありません。

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

同じpeer／ポートに一致する、制限のないL4許可を追加しないでください。Ciliumの説明では、そのような許可がより狭いL7制限の効果をなくします。L7の拒否はパケット破棄ではなくHTTP 403を返す場合があります。実際のエンドポイントIDを使って、許可されるGETと拒否されるmethod／pathをテストしてください。

### DNS／FQDNの例

`cilium-dns-demo`では、通常のCoreDNS PodへのDNS問い合わせと、`api.example.com`で学習したアドレスへのTCP 443を許可します。これは例示用ドメインです。承認された宛先に置き換えてください。広範な`*.amazonaws.com`ワイルドカードはアカウント／リソースの境界ではないため、例から省いています。

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

DNSワイルドカードは、選択されたResolverへの問い合わせを許可するものであり、返されるすべてのアドレスへの接続を許可するものではありません。ただし、任意のDNS名を問い合わせられる可能性はあるため、必要に応じてDNS検索サフィックスを考慮して問い合わせ名を制限してください。NodeLocal DNSや別Resolverでは適切な宛先選択が必要です。FQDNポリシーはDNS由来のIP認可であり、TLSホスト名検証やHTTP URLの認可ではありません。共有IPやアプリケーションのTLS／認証も引き続き考慮してください。

## Hubbleによる可観測性

上記のcluster-pool設定ではRelay／UIとコンポーネントメトリクスが有効になります。既存インストールでは、意図したHubble設定を管理者経由で適用してください。`cilium hubble enable --ui`はサポート対象の簡便コマンドですが、`cilium hubble enable --metrics=...`は0.20.1 CLIのサポート対象フラグではありません。Helm値の`hubble.metrics.enabled`を設定してください。旧`http`と`httpV2`のハンドラーを同時に有効化しないでください。

1つ目の端末でRelayへのport-forwardを実行したままにします。

```bash
cilium hubble port-forward --port-forward 4245
```

Hubble CLIをインストールした別の端末で、次を実行します。

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

このローカル例はRelayのデフォルトサーバー設定を前提とします。RelayでTLSを有効にした場合、対応するクライアントの信頼設定／認証が必要です。HTTPイベントには、設定済みのL7 proxyを通る通信が必要です。`DROPPED`はデータパスの判定であり、アプリケーションリクエストの失敗すべてを意味するわけではありません。UIのport-forwardには`cilium hubble ui`を使い、Prometheusのターゲット検出は別途設定します。Hubbleのフローストリーミングだけで分散アプリケーショントレースが実現するわけではありません。

## テストと運用

接続性／性能のコマンドはテスト用ワークロードを作成し、ポリシーを変更したり大量のトラフィックを生成したりする場合があります。レビュー済みのテストNamespace／環境と必要な権限を使ってください。この監査ではクラスター上で実行していません。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能測定を実行するサブコマンドは`cilium connectivity perf`です。`connectivity test --test=performance`はテスト名のフィルターを渡すだけで、性能測定の実行コマンドではありません。スループット／レイテンシーを比較する前に、ソフトウェアバージョン、トポロジー、トラフィック、生の結果を記録してください。

調査時には、管理CLIと**Agent側の`cilium-dbg`を区別してください**。

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

管理CLIの`cilium endpoint list`、`cilium bpf maps list`、`cilium metrics list`は、それぞれ対応する同等コマンドではありません。`cilium sysdump`は診断資料を収集できます。生成されたインフラ情報／ログを保護してください。AgentがReadyであることやスクレイプに成功したことは、アプリケーション試験や拒否ポリシー試験の代わりにはなりません。

### 運用上の優先事項

- map preallocation、XDP、DSR、BBR、固定デバイスパターンを有効にする前に測定してください。リソース消費やパケット経路の変更があり、機能ごとの確認が必要です。
- 対象範囲を選んでdefault-denyを導入し、DNS、API、Identity、アプリケーションの依存関係を明示的に許可してください。既存接続だけでなく、新しいPodとアップグレード時の移行も確認します。
- 暗号化、証明書／鍵のローテーション、ポリシー適用、可観測性を別々の受け入れ試験として扱います。管理／復旧経路を利用できる状態に保ってください。
- 現行のプラットフォームマトリクスとサポート対象のアップグレード経路を確認してください。過去のリリース発表だけでは、現在のデプロイ互換性は確認できません。

## 詳細目次

**[Ciliumの紹介と基本概念](01-introduction.md)**
- Ciliumの概要と歴史
- コンテナネットワークの基礎
- CNI（Container Network Interface）の理解
- Cilium独自の機能

**[eBPF技術の詳細](02-ebpf.md)**
- eBPF技術の紹介と歴史
- カーネル内でのeBPFの動作
- eBPFプログラムの種類とマップ
- CiliumでのeBPFの利用

**[ネットワークモデルとVXLAN](03-networking.md)**
- コンテナネットワークモデルの比較
- VXLAN技術の詳細
- Ciliumのオーバーレイネットワーク
- 性能の最適化手法
- カプセル化とNative routingのルーティング方式
- クラウド事業者のネットワーク（AWS ENI、Google Cloud）

**[IPAMとネットワークポリシー](04-ipam-policy.md)**
- IPアドレス管理（IPAM）の戦略
- KubernetesとCilium IPAMの連携
- ネットワークポリシーの設計と実装
- マルチクラスターの構成
- IPAMモードの詳細（Cluster Scope、Kubernetes Host Scope、Multi-Pool）
- クラウドIPAM（Azure IPAM、AWS ENI、GKE）
- CRDベースのIPAM

**[L2～L7ネットワークとロードバランシング](05-l2-l7-networking.md)**
- OSIモデルの各層（L2、L3、L4、L7）
- Ciliumのレイヤー別機能
- Service Meshとの連携
- ロードバランシングのアーキテクチャ
- マスカレードの設定と実装モード
- IPv4フラグメントの処理

**[セキュリティと可視性](06-security-visibility.md)**
- Ciliumのセキュリティ機能
- ネットワークの可視性と監視
- Hubbleのアーキテクチャと利用方法
- リアルタイム脅威検出

**[高度なトピックと実例](07-advanced-topics.md)**
- 性能調整とトラブルシューティング
- 大規模デプロイメントの戦略
- 実際のユースケース
- 今後のロードマップと開発方針

**[eBPFデータパス内部](08-ebpf-datapath-internals.md)**
- プログラムセット、アタッチポイント、テールコール
- BPFマップ一覧、サイズ設定、コンパイル／ロードの流れ
- ポリシー適用経路とHubbleイベントパイプライン

**[オーバーレイとNative routing](09-overlay-native-routing.md)**
- VXLAN／Geneve、VNI内のIdentity、MTU、パケット経路
- Native routing、マスカレード、ホストルーティング、DSR、netkit
- EKSの選択表：overlay、ENI、VPC CNI chaining

**[IPAMの詳細](10-ipam-deep-dive.md)**
- すべてのIPAMモード、容量計算、選定表
- Multi-Pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- IP枯渇のトラブルシューティングと1.21 API変更

**[BGP、LoadBalancer IP、egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、広告、確認方法
- L2 announcements、Egress Gateway、Local Redirect Policy
- Gateway APIの要件とEKSでの内部限定公開

**[mTLS、暗号化、Identity](12-mtls-encryption-identity.md)**
- Identityモデル、ポリシーの意味、監査モード
- Mutual Authenticationの時系列、ztunnelワークロードmTLS
- WireGuard、IPsec、Hubble、証明書管理

**[バージョン、インストール／アップグレード、Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17～1.21の機能マトリクス、アップグレード／ロールバック規則
- EKSのインストール詳細、Cluster Mesh、MCS-API

## 追加リソース

- [ネットワーク概念の詳細](networking-concepts.md)
- [用語集と略語](glossary.md)

## 参考資料

- [Cilium 1.20のKubernetes互換性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Ciliumシステム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKSの前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWSの代替CNIサポート](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7ポリシーの仕様](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubbleプロジェクト](https://github.com/cilium/hubble)
- [Flannelのネットワークとポリシー連携](https://github.com/flannel-io/flannel)
- [Calico比較用語](../calico/glossary.md)

## クイズ

このセクションの理解度を確認するには、[Cilium詳説クイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。
