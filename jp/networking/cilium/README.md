# Cilium 詳細解説：クラウドネイティブネットワーキングの未来

## 概要とレビュー済みベースライン

このセクションでは、Ciliumのネットワーキング、ポリシー、可観測性について説明します。各例は、**Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1**、Hubble CLI **1.20.2**を基準にレビューしています。Cilium 1.20のKubernetes互換性ページでは、**1.33～1.36**がテスト済みとして記載されています。上流の1.37リリースが出ても、この対応表が自動的に拡張されるわけではありません。サポート対象ホストは、カーネル**5.10以降**を搭載したAMD64/AArch64 Linux、またはRHEL 8.10のバックポート版4.18カーネルなど、文書に記載されたディストリビューション相当の環境です。機能ごとに追加要件があります。

> **最終更新日**: 2026年10月19日

### 過去のリリースノート

以下の日付はGitHubでの公開日（UTC）であり、それぞれのリリースを示すものです。現在のインストール時に指定するバージョンではありません。バックポートされる機能はリリース系列によって異なります。

| 日付 | リリース | 確認済みの主な内容 |
| --- | --- | --- |
| 2026年7月14日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20最初のリリース候補 |
| 2026年7月16日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6)、[1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12)、[1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gatewayのアクセスログ設定は1.19.6/1.18.12に記載されています。ここで挙げている再起動ポリシーとClusterMeshのアフィニティ修正は1.19.6に記載されており、3つすべてのリリースに含まれているわけではありません |
| 2026年7月21日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20の2つ目のリリース候補 |
| 2026年7月29日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GAリリース。主な変更点は以下を参照 |
| 2026年8月3日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 次期サイクルのプレリリース。このガイドのデプロイベースラインではありません |
| 2026年8月18日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | ClusterMeshのドキュメントとバグ修正。再起動/CIDRポリシーの処理などを含みます |
| 2026年8月18日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENIインターフェイスのタイミング、Service/LBなどの修正を含みます |
| 2026年8月18日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMPのホストファイアウォール対応と関連修正 |
| 2026年9月9日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | プレリリース。**1.21.0-pre.1は公開されなかった**ため、変更履歴はpre.0からpre.2までを対象としています |
| 2026年9月16日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | ENI IPAMのプレフィックス委譲における割り当て/解放とセカンダリVPC CIDRの処理、ClusterMesh、ポリシー変更直後に作成されたPodのポリシーリビジョン、LocalRedirectPolicyのリグレッション、v1.15以前に作成されたクラスターのアップグレード（`CiliumNodeConfig v2alpha1` CRDバージョン）などのバグ修正 |
| 2026年9月16日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8)、[1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 旧サポート系列のパッチリリース |
| 2026年10月2日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新の1.21プレリリース。**1.21はプレリリースのみ**（GAはまだありません）であり、このガイドで1.21と記載している項目は変更される可能性があります |
| 2026年10月15日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API依存関係v1.6.3、conntrack GC、`nodeSelector`を含むCNPの処理などの修正。このガイドで現在レビューしているベースライン |
| 2026年10月15日 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9)、[1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | 旧サポート系列のパッチリリース |

2026年9月14日、CNCFブログは[ Cilium 1.20の機能まとめ](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAMなど）を公開しました。内容は、以下に示す1.20.0の発表概要と同じ範囲を扱っています。

1.20.0の発表では、**2,660件を超える新規コミット**が報告されており、**1,100人を超えるコントリビューターのコミュニティ**に支えられています。後者はコミュニティの規模であり、このリリースにおける作者数ではありません。主な内容は次のとおりです。

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth、CORS対応。ただし、機能ごとの設定とAPIの成熟度に依存します。
- Datapathプラグインとオプトインの`bpf.datapathMode=auto`。発表時点でのデフォルトは引き続きvethです。デュアルスタッククラスターでは、IPv6のegress gatewayアドレスを設定できます。
- **ベータ**のIPv6 ENI IPAMと、クラスターを再構築せずにcluster-poolからmulti-poolへ移行する機能。インプレース移行でも、中断が発生しないとは限りません。
- トラフィック分散ヒント、重み付きMaglevバックエンド、安定したMCS統合、Kubernetes ClusterNetworkPolicyのサポート、**ベータ**のztunnelベースのワークロードID。
- `cilium-cni`バイナリが約**77 MBから16 MB**に縮小したとの報告。ADS/Delta xDSの改善は1.20の発表に記載されています。1.18.13のパッチノートの内容として扱わないでください。これらは上流リリースの発表内容であり、この監査で再測定した値ではありません。

相互認証（**1.20で非推奨**、1.21プレリリースで削除）、削除/置換されたEnvoy Go拡張機能、Kafka対応ポリシー、旧CiliumNodeConfig API、libnetwork統合、カスタムCNI設定の変更については、[1.20アップグレードノート](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)を確認してください。

### NetworkPolicyセキュリティアドバイザリ

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r)のプロジェクトアドバイザリ公開日は**2026年7月6日**です。プロジェクトAPIとGitHubのグローバルアドバイザリAPIでは異なる日付が表示されます。後者には9月3日と記録されています。このリリース年表ではプロジェクトの開示日を使用してください。グローバルレコードの日付は、より後の修正リリースを意味するものではありません。この問題は、アドバイザリに記載されたカスタムクラスター名の条件下で**1.19.0～1.19.4**に影響します。標準的なKubernetes NetworkPolicyのpeerに`ipBlock`だけが含まれていると、選択されたPodと同じnamespace内のワークロードからのingressが意図せず許可される可能性があります。**1.19.5**で修正されています。デプロイには、適切な現行のパッチ適用済みリリースを使用してください。このアドバイザリによると、CiliumNetworkPolicy/ClusterwideNetworkPolicy、および1.19.0未満のリリースは、この特定のバグの影響を受けません。

## はじめに

Ciliumは、サポート対象のLinux Kubernetes環境向けにネットワーキング、セキュリティ、可観測性を提供します。ルーティング、IPAM、暗号化、Service処理はそれぞれ別の選択肢です。eBPFを選択しただけでは、すべての機能が有効になるわけでも、性能が保証されるわけでもありません。従来のDocker libnetwork統合は1.20で削除されたため、Docker/Mesosを現行のインストール対象としてここに同列に記載するべきではありません。

### eBPFと主な機能

カーネルはeBPFプログラムをロード前に検証し、サポート対象のフックで実行できるようJITコンパイルする場合があります。これにより、カスタムカーネルモジュールなしでパケット処理や可観測性を実現できます。ただし、検証器はアプリケーションやポリシーの正しさを保証するものではありません。実際のスループット、レイテンシ、メモリ使用量は、プログラム、プラットフォーム、ワークロードによって異なります。

Ciliumは、L3/L4ポリシー、Envoy/DNS proxy統合によるL7ポリシー、オプションのWireGuard/IPsec、Serviceロードバランシング、Hubbleによるフローの可視化、ClusterMesh、BGP広告を提供します。XDPアクセラレーションはオプションで、デバイスや設定に依存します。L7機能ではノードごとのEnvoyを使用する場合があります。ztunnelによるワークロードIDには、別途ベータ版の設定が必要です。エージェントをインストールしただけでは、すべてのメッシュ、暗号化、マルチクラスターの動作が有効になるわけではありません。

### 他のネットワーキングプロジェクトとの比較

| プロジェクト | 接続性 / IPAM | ポリシーと関連機能 |
| --- | --- | --- |
| Cilium | ネイティブルーティングまたはオーバーレイルーティング。クラウドENIを含むIPAMモード | eBPF dataplane、Cilium/Kubernetesポリシー、L7統合、Hubble、オプションの暗号化 |
| Calico | Calicoまたは外部IPAMを使用するネイティブ/IPIP/VXLANプロファイル | LinuxのIptables/Nftables/BPF、サポート対象のWindows HNS、OSS版WireGuard、段階的なポリシー適用、個別のL7統合 |
| Flannel | VXLAN/host-gw/WireGuardなど、選択したバックエンドを介したPod接続 | ルーティングデーモン自体はNetworkPolicyを適用しません。チャートで`netpol.enabled`を設定し、SIGsのnetwork-policy controllerをデプロイすることも、別のポリシー実装と組み合わせることもできます |
| AWS VPC CNI | VPC ENIによるアドレス割り当て/ネットワーキング | サポート対象のEC2 Linuxノードでのネイティブネットワークポリシーと、独立したSG-for-Pods機能。EKS Auto Modeは別のマネージド実装です |

ルーティングモードとパケット処理の実装方式は、同じ分類ではありません。Calicoはiptables/IPVSだけに限定されず、Flannelは暗号化バックエンドを使用でき、AWSのポリシーがセキュリティグループと同義というわけでもありません。Service meshはオプションのレイヤーであり、クラスター間のVPC接続がTransit Gatewayに限定されるわけでもありません。普遍的な性能ランキングではなく、実測したワークロードと明示的なサポートマトリクスを使用してください。

## アーキテクチャ

**Kubernetes API server**はKubernetes/Ciliumリソースを保存します。Cilium agentは関連する状態を監視し、各ノードのdataplaneを設定します。Cilium Operatorは、選択されたIPAMやID/コントローラー関連の作業など、クラスター全体に関わる責務を担います。この基本アーキテクチャに、クラスター全体で必須となる別個の「Cilium API Server」デプロイはありません。agentにはローカルAPIがあり、オプションのClusterMesh API serverは別の目的で使われます。

| コンポーネント | 役割 |
| --- | --- |
| Cilium Agent | ノードローカルのエンドポイント、ポリシー、ルーティング/Serviceの状態、eBPFの管理 |
| Cilium Operator | クラスター全体の調整、およびモードに応じた割り当て/コントローラー処理 |
| Envoy | 有効化されたL7ポリシー、ingress/Gateway、関連機能向けのユーザー空間プロキシ |
| Hubble server | agentと統合されたノードローカルのフローAPI |
| Hubble Relay / UI | フローストリームの集約 / Serviceマップやフローの表示 |
| Prometheusメトリクスエンドポイント | 独立した統計情報の収集。Relay/UIはメトリクスのスクレイピング経路ではありません |
| cilium / cilium-dbg / hubble | それぞれクラスター管理CLI / agent診断 / フロークライアント |

### ネットワーキングとパケット経路

ネイティブルーティングには到達可能なunderlayが必要です。トンネリングではVXLANまたはGeneveを使用します。AWS ENIとAzure IPAMは割り当て/統合方式の選択肢で、それぞれ独自のプラットフォーム要件があります。CiliumのBGP Control Planeはルーターに到達可能性を広告しますが、**datapathを設定したり、クラスター内部のルーティングを提供したりするものではありません**。

XDP→TC→Podという一律の順序はありません。socket load balancingはパケットが存在する前に動作する場合があり、TC/netkitフックはdatapathに依存します。オプションのXDPは選択したトラフィックを高速化し、L7トラフィックはEnvoyを経由する場合があります。戻りトラフィックもNAT、conntrack、DSRの選択に依存します。選択したプロファイルについては、ネットワーキングとeBPFの各章を参照してください。

## Amazon EKSとの統合

インストールを始める前に、実際に使用するネットワーキングとコンピューティングのプロファイルを選択してください。例にあるアドオン名/バージョン`cilium` / `v1.17.0-eksbuild.1`は、AWSの配布物として確認されたものではなく、ここではインストールコマンドとして扱いません。パッケージ化されたベンダーアドオンを検討する場合は、対象リージョンの実際のアドオンカタログ、発行元、ライセンス、サポート対象のコンピューティングタイプを確認してください。

| EKSプロファイル | 確認事項 |
| --- | --- |
| 通常のEC2ノード、Cilium ENIでVPC CNIを置き換える | 上流/パートナー管理のCNI。AWSがサポートするEC2 CNIはVPC CNIです。CNIの所有者、IAM、アドレス指定、ルート、ブートストラップ、ノード移行を計画してください |
| 通常のEC2ノード、AWS VPC CNI chaining | VPC CNIがインターフェイス/IPAMを管理し、その後Ciliumがdataplaneを接続します。既存のPodは再作成が必要で、L7/IPsecには文書化された制約があります |
| Hybrid Nodes | AWSの専用CNIガイドと、AWSが保守するCiliumビルドマトリクスに従ってください。上流の1.20.3が自動的にサポート対象のAWSビルドになるわけではありません |
| Auto Mode | 代替CNI/ポリシープラグインはサポートされません。マネージドのNodeClass/ネットワーキング機能を使用してください |
| Fargate | 代替CNI/DaemonSetのインストールはサポートされません |
| Windows | Cilium agentの要件はLinuxです。この手順をWindowsワーカーに適用しないでください |

AWSの一般的な代替CNIページと専用のHybridガイドでは、Calicoのサポートに関する記述が異なります。リポジトリの移動例があるからといって、サポート終了が確定するわけではありません。Hybrid Nodesでは、正確な配布物、機能セット、サポート担当者を確認してください。Auto Modeでは、ノードローカルのCoreDNS/システムネットワーキングもこのガイドの通常のEC2構成とは異なります。Auto Mode以外のノードが混在する場合は、従来型のDNS Deploymentも引き続き必要です。

### Cilium ENIを使用する準備済みEC2クラスター

以下は**準備済みのIPv4 EC2クラスター向けCilium Helm values**であり、クラスター作成やインプレース移行の手順一式ではありません。使用前に次の点を確認してください。

1. サポート対象のEKS/KubernetesバージョンとLinux AMIを選び、CNIの管理主体を1つに決めます。既存のワークロードクラスターで、安易な方法として`aws-node`を削除しないでください。
2. Ciliumがノードを管理するまでワークロードが待機するよう、ノードのtaint/スケジューリングを準備します。上流のEKSガイダンスでは`node.cilium.io/agent-not-ready=true:NoExecute`が使われています。実際のノードライフサイクルで、退避やブートストラップへの影響を評価してください。
3. サブネット容量、ENIクォータ/セキュリティグループ、ノードのメタデータアクセス、Operatorに必要なEC2権限を準備します。以下のロールARNは、適切に信頼関係が設定された**cilium-operator ServiceAccount**用ロールのプレースホルダーであり、valuesファイルによって作成されるロールではありません。
4. この`kubeProxyReplacement: false`の例では、動作中のkube-proxyとDNSを維持してください。置換モードでは、APIへの直接アクセス/ブートストラップDNSに関する別の要件に従ってください。max-Podsは一律に110とせず、実際のインスタンス/IPAM容量に基づいて選択してください。

`cilium-eni-values.yaml`として保存し、ロール/インターフェイスの選択をレビュー済みの値に置き換えてください。

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

これらの設定は、インストールの管理主体を通じて管理してください。必要な設定がほかにもあるのに、数個のキーだけを含む`cilium-config`に置き換えると、それらが削除される場合があります。旧式の`tunnel=disabled`は`routingMode: native`に置き換えられています。ENIの割り当て/権限とSNATの動作は、引き続き実環境で検証が必要です。レンダリングに成功しても、EC2ネットワーキングが利用可能だと証明されたことにはなりません。

**IPv6に関する補足:** 1.20.3のENI IPAMリファレンスではIPv6をベータと記載していますが、EKSの前提条件ページでは引き続きIPv4のみのENI統合とされています。このガイドではIPv4の例を示し、どちらか一方の記述を本番環境でのEKS IPv6互換性の証明とみなすのではなく、ドキュメント間の不整合を記録しています。IPv6を別途設計する場合は、最新のENI/デュアルスタックサブネット要件を確認してください。

### VPC CNI chainingの代替案

上流のchainingガイドではVPC CNI 1.11.2以降が必要とされており、次のプロファイルが説明されています。

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

これは、ENI置換用のvaluesに重ねて適用するのではなく、**別の設定**として使用してください。割り当ては引き続きVPC CNIが行います。過去の上流DaemonSetを適用するのではなく、実際のマネージドアドオンをその管理主体を通じてアップグレードしてください。同じエンドポイントでポリシーエンジンが競合しないようにしてください。CNIチェーンを変更しても、既存のPodが遡ってCiliumに接続されることはありません。計画したリリースのもとでPodを再作成し、エンドポイントが管理されていることを確認してください。chainingにはL7ポリシー/IPsecの文書化された制約があるため、このページ後半の例がすべてそのプロファイルで動作すると想定しないでください。

### ClusterMesh

ClusterMeshには、一意のクラスターID、互換性のあるバージョン、到達可能で重複しないPodネットワーク、認証されたAPI接続、適切な公開方式が必要です。LoadBalancer Serviceを使うとクラウドリソースが作成される場合があるため、意図的なネットワーク/セキュリティ設計が必要です。パブリックエンドポイントを2つ作るだけでは、クラスターを安全に接続できません。選択したトポロジーに応じて、保守されている[ClusterMeshガイド](13-clustermesh-install-upgrade.md)と詳細解説の章に従ってください。

## インストールと設定

### クライアントツール

ワークステーションのOS/アーキテクチャに適した公式Cilium CLI 0.20.1とHubble CLI 1.20.2のアセットを使用し、展開前に提供されたチェックサムを検証してください。Linux ARM64とAMD64ではアセットが異なり、macOSでは対応するDarwinアセットを使います。CLIのバージョンはCilium agent/chartのバージョンとは別です。[確認済みのCLIインストールガイダンス](../../service-mesh/cilium-service-mesh/README.md)を参照してください。

```bash
cilium version --client
hubble version
```

### クラウド以外のcluster-poolの例

次の**代替例**は、kube-proxyとDNSがすでに動作している準備済みの通常のLinuxクラスター向けです。例で使われている`10.244.0.0/16`のPod範囲がクラスターと互換性があり、Service、ノード、VPC、接続ネットワークの範囲と重複していないことを確認してください。ENIモードでは、このpool設定を使用しないでください。

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

`cilium-values.yaml`として保存し、固定したバージョンのchartをレンダリングしてから、準備済みのクラスターにのみインストールしてください。

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

既存のリリースでは、そのアップグレード/GitOpsプロセスを使用し、管理対象のvaluesを維持して、バージョン固有のアップグレード手順に従ってください。`cilium install`の例を繰り返すのは、個別の設定を変更する一般的な方法ではありません。

| 選択肢 | 現行の設定と前提条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel`と`tunnelProtocol`を設定します。選択したカプセル化方式を許可し、経路に合わせてMTUを設定してください |
| ネイティブルーティング | `routingMode: native`を設定します。underlayはPodアドレスをルーティングできる必要があります。`autoDirectNodeRoutes`には適切な直接接続性が必要で、任意のマルチサブネットルーティングに対応するものではありません |
| kube-proxy置換 | レガシーの`strict`ではなく、`kubeProxyReplacement: true`または`false`を使用します。置換には到達可能な`k8sServiceHost`/`k8sServicePort`と、文書に記載されたブートストラップ計画が必要です |
| WireGuard | カーネル/プラットフォームとpeer間の経路を確認したうえで、サポート対象の暗号化モードを有効にします。あらゆるトラフィック経路が自動的に暗号化されるわけではありません |
| IPsec | 文書に記載された鍵Secret、鍵の配布/ローテーション、互換性のあるモードが必要です。Helmの有効化フラグだけでは不十分です |
| XDP/DSR/BBR | 個別のデバイス/カーネル/トポロジーに依存する選択肢であり、汎用のインストールプリセットではありません |

## NetworkPolicy

Kubernetesの`networking.k8s.io/v1` NetworkPolicyとCiliumの`cilium.io/v2`ポリシーは別々のAPIです。複数のallowポリシーは組み合わされる場合があります。以下の例では、L4のallowによってL7の制限が気付かないうちに迂回されないよう、**事前に準備した別々のテストnamespace**を使用しています。結論を出す前に、実際のエンドポイントを選択するすべてのポリシーを確認してください。

### L4の例

`cilium-l4-demo`では、バックエンドPodを選択し、同じnamespaceのフロントエンドPodからのTCP 8080へのingressを許可します。

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

別の`cilium-l7-demo`namespaceでは、バックエンドPodを選択し、そのnamespace内のフロントエンドPodからの平文HTTPについて、TCP 8080上で指定されたメソッド/パスのみを許可します。選択したCNIモードでL7プロキシが利用できる必要があります。サポート対象の終端設定がなければ、暗号化されたHTTPが自動的に検査されることはありません。

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

同じpeer/ポートに対して、該当する無制限のL4 allowを追加しないでください。Ciliumの説明によると、そのようなallowを設定すると、より限定的なL7制限の効果がなくなります。L7で拒否した場合、パケットをドロップするのではなくHTTP 403を返すことがあります。実際のエンドポイントIDを使って、許可されるGETリクエストと拒否されるメソッド/パスをテストしてください。

### DNS/FQDNの例

`cilium-dns-demo`では、通常のCoreDNS PodへのDNSクエリと、`api.example.com`について学習したアドレスへのTCP 443を許可します。ドメインは例です。承認済みの宛先に置き換えてください。広範な`*.amazonaws.com`ワイルドカードはアカウント/リソースの境界にはならないため、省略しています。

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

DNSワイルドカードで許可されるのは選択したresolverへのクエリであり、応答されたすべてのアドレスへの接続ではありません。ただし、任意のDNS名を問い合わせられる可能性はあるため、必要に応じてDNS search suffixを考慮しながらクエリ名を制限してください。NodeLocal DNSや別のresolverを使用する場合は、適切な宛先選択が必要です。FQDNポリシーはDNSから導出したIPアドレスに対する認可であり、TLSホスト名の検証やHTTP URLの認可ではありません。共有IPが使われる場合や、アプリケーションのTLS/認証がある場合も考慮してください。

## Hubbleによる可観測性

上記のcluster-pool valuesでは、Relay/UIとコンポーネントのメトリクスが有効になります。既存のインストールでは、意図したHubbleのvaluesを設定の管理主体を通じて適用してください。`cilium hubble enable --ui`はサポート対象の便利なコマンドですが、`cilium hubble enable --metrics=...`は0.20.1 CLIでサポートされているフラグではありません。代わりに、Helm valuesで`hubble.metrics.enabled`を設定してください。レガシーの`http`と`httpV2`ハンドラーを同時に有効化しないでください。

1つ目のターミナルでは、Relayのポートフォワードを実行したままにします。

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

このローカルの例では、デフォルトのRelay server設定を前提としています。TLS有効のRelayでは、対応するクライアント側の信頼設定/認証が必要です。HTTPイベントが生成されるには、設定済みのL7プロキシをトラフィックが通過する必要があります。`DROPPED`はdatapathの判定であり、アプリケーションの失敗すべてを示すものではありません。UIのポートフォワードには`cilium hubble ui`を使用し、メトリクスについてはPrometheusのターゲット検出を別途設定してください。Hubbleのフローストリーミングだけでは、分散アプリケーションのトレーシングにはなりません。

## テストと運用

接続性/性能のコマンドはテスト用ワークロードを作成する場合があり、ポリシーを変更したり、大量のトラフィックを生成したりする可能性があります。レビュー済みのテストnamespace/環境と適切な権限を使用してください。この監査では、クラスターに対してこれらのコマンドを実行していません。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能サブコマンドは`cilium connectivity perf`です。`connectivity test --test=performance`はテスト名のフィルターを指定するだけで、性能テストの実行コマンドではありません。スループット/レイテンシを比較する前に、ソフトウェアバージョン、トポロジー、トラフィック、未加工の結果を記録してください。

調査では、管理CLIと**agent側の`cilium-dbg`を区別してください**。

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

`cilium endpoint list`、`cilium bpf maps list`、`cilium metrics list`は、管理CLIにおける同等のコマンドではありません。`cilium sysdump`で診断情報を収集できます。生成されたインフラストラクチャ/ログデータは適切に保護してください。agentがReadyであることやスクレイピングに成功したことは、アプリケーションテストや拒否側のポリシーテストの代わりにはなりません。

### 運用上の優先事項

- mapの事前割り当て、XDP、DSR、BBR、固定デバイスパターンを有効にする前に測定してください。これらはリソースを消費したりパケット経路を変えたりするため、機能ごとの確認が必要です。
- デフォルト拒否は、DNS、API、ID、アプリケーションの依存関係を明示的に許可したうえで、対象範囲を選んで導入してください。確立済みの接続だけでなく、新しいPodやアップグレード時の移行も確認してください。
- 暗号化、証明書/鍵のローテーション、ポリシー適用、可観測性は別々の受け入れ確認項目として扱ってください。利用可能な管理/復旧経路を維持してください。
- 最新のプラットフォームマトリクスとサポート対象のアップグレード経路を確認してください。過去のリリース発表だけでは、現在のデプロイ互換性は確認できません。

## 詳細解説の目次

**[Ciliumの概要と基本概念](01-introduction.md)**
- Ciliumの概要と歴史
- コンテナネットワーキングの基本
- CNI（Container Network Interface）を理解する
- Ciliumの差別化要因

**[eBPF技術の詳細解説](02-ebpf.md)**
- eBPF技術の概要と歴史
- カーネル内部でのeBPFの動作
- eBPFプログラムの種類とマップ
- CiliumでのeBPFの活用

**[ネットワーキングモデルとVXLAN](03-networking.md)**
- コンテナネットワーキングモデルの比較
- VXLAN技術の詳細解説
- Ciliumのオーバーレイネットワーキング
- 性能最適化の手法
- ルーティング方式（カプセル化とネイティブルーティング）
- クラウドプロバイダーのネットワーキング（AWS ENI、Google Cloud）

**[IPAMとネットワークポリシー](04-ipam-policy.md)**
- IPアドレス管理（IPAM）の方式
- KubernetesとCiliumのIPAM統合
- ネットワークポリシーの設計と実装
- マルチクラスターのシナリオ
- IPAMモードの詳細（Cluster Scope、Kubernetes Host Scope、Multi-Pool）
- クラウドプロバイダーのIPAM（Azure IPAM、AWS ENI、GKE）
- CRDベースのIPAM

**[L2-L7ネットワーキングとロードバランシング](05-l2-l7-networking.md)**
- OSI参照モデルの各レイヤー（L2、L3、L4、L7）
- Ciliumのレイヤー別機能
- Service meshとの統合
- ロードバランシングのアーキテクチャ
- マスカレードの設定と実装モード
- IPv4フラグメントの処理

**[セキュリティと可視性](06-security-visibility.md)**
- Ciliumのセキュリティ機能
- ネットワークの可視性と監視
- Hubbleのアーキテクチャと使い方
- リアルタイムの脅威検出

**[高度なトピックと実際の事例](07-advanced-topics.md)**
- 性能のチューニングとトラブルシューティング
- 大規模デプロイ戦略
- 実際のユースケース事例
- 今後のロードマップと開発の方向性

**[eBPF datapathの内部](08-ebpf-datapath-internals.md)**
- プログラムセット、アタッチポイント、tail call
- BPF mapの一覧、サイズ設定、コンパイル/ロードの流れ
- ポリシー適用の経路とHubbleイベントのパイプライン

**[オーバーレイとネイティブルーティング](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI内のID、MTU、パケットの経路
- ネイティブルーティング、マスカレード、ホストルーティング、DSR、netkit
- EKSの選択表：オーバーレイ、ENI、VPC CNI chaining

**[IPAM詳細解説](10-ipam-deep-dive.md)**
- すべてのIPAMモード、サイズ計算、選択マトリクス
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 枯渇時のトラブルシューティングと1.21のAPI変更

**[BGP、ロードバランサーIP、egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、広告、確認
- L2アナウンス、Egress Gateway、Local Redirect Policy
- Gateway APIの要件とEKSでの内部向け公開

**[mTLS、暗号化、ID](12-mtls-encryption-identity.md)**
- IDモデル、ポリシーの意味、監査モード
- 相互認証の変遷、ztunnelによるワークロードmTLS
- WireGuard、IPsec、Hubble、証明書管理

**[バージョン、インストール/アップグレード、Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17～1.21の機能マトリクス、アップグレードとロールバックのルール
- EKSへのインストールの詳細、Cluster Mesh、MCS-API

## 追加リソース

- [ネットワーキング概念の詳細解説](networking-concepts.md)
- [用語集と略語](glossary.md)

## 参考資料

- [Cilium 1.20とKubernetesの互換性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Ciliumのシステム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKSの前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWSの代替CNIサポート](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7ポリシーの仕様](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubbleプロジェクト](https://github.com/cilium/hubble)
- [Flannelのネットワーキングとポリシー統合](https://github.com/flannel-io/flannel)
- [Calico比較用語集](../calico/glossary.md)

## クイズ

このセクションで学んだ内容を確認するには、[Cilium詳細解説クイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。
