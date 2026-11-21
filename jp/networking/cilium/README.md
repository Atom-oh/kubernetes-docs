# Cilium 詳細解説：クラウドネイティブネットワーキングの未来

## 概要とレビュー済みのベースライン

このセクションでは、Cilium のネットワーキング、ポリシー、可観測性について説明します。例は **Cilium/Helm chart 1.20.3**、Cilium CLI **0.20.1**、Hubble CLI **1.20.2** を基準にレビューしています。Cilium 1.20 の Kubernetes 互換性ページでは、テスト済みバージョンとして **1.33–1.36** が記載されています。上流の 1.37 リリースがあっても、この対応範囲が自動的に拡張されるわけではありません。サポート対象のホストは、カーネル **5.10+** を搭載した AMD64/AArch64 Linux、または RHEL 8.10 のバックポート版 4.18 カーネルなど、ドキュメントに記載されたディストリビューション相当の環境です。機能ごとに追加の要件があります。

> **最終更新日**: 2026年11月19日

### 過去のリリースノート

以下の日付は GitHub での公開日（UTC）であり、各リリースについて記載したもので、現在のインストール時に固定すべきバージョンを示すものではありません。機能のバックポート状況はリリース系列によって異なります。

| 日付 | リリース | 確認済みの主な変更 |
| --- | --- | --- |
| 2026年7月14日 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 1.20 の最初のリリース候補 |
| 2026年7月16日 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gateway のアクセスログ設定は 1.19.6/1.18.12 に記載されています。ここで挙げている再起動ポリシーと ClusterMesh のアフィニティに関する修正は、3 つすべてのリリースではなく、1.19.6 に記載されています |
| 2026年7月21日 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 1.20 の 2 つ目のリリース候補 |
| 2026年7月29日 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA リリース。主な変更点は以下のとおり |
| 2026年8月3日 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 次期サイクルのプレリリース。このガイドのデプロイベースラインではありません |
| 2026年8月18日 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | 再起動/CIDR ポリシーの処理を含む ClusterMesh のドキュメントとバグ修正 |
| 2026年8月18日 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENI インターフェースのタイミング、Service/LB などの修正を含む |
| 2026年8月18日 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP のホストファイアウォール対応と関連する修正 |
| 2026年9月9日 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | プレリリース。**1.21.0-pre.1 は公開されなかった**ため、変更履歴は pre.0 から pre.2 までを対象としています |
| 2026年9月16日 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | ENI IPAM のプレフィックス委任における割り当て/解放とセカンダリ VPC CIDR の処理、ClusterMesh、ポリシー変更直後に作成された Pod のポリシーリビジョン、LocalRedirectPolicy のリグレッション、v1.15 以前に作成されたクラスターのアップグレード（`CiliumNodeConfig v2alpha1` CRD バージョン）などのバグ修正 |
| 2026年9月16日 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 旧サポート系列のパッチリリース |
| 2026年10月2日 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 1.21 のプレリリース |
| 2026年10月15日 | [1.20.3](https://github.com/cilium/cilium/releases/tag/v1.20.3) | Gateway API 依存関係 v1.6.3、conntrack GC、`nodeSelector` を含む CNP の処理などの修正。このガイドで現在レビュー済みのベースライン |
| 2026年10月15日 | [1.19.9](https://github.com/cilium/cilium/releases/tag/v1.19.9), [1.18.15](https://github.com/cilium/cilium/releases/tag/v1.18.15) | 旧サポート系列のパッチリリース |
| 2026年10月23日 | [1.20.4](https://github.com/cilium/cilium/releases/tag/v1.20.4), [1.19.10](https://github.com/cilium/cilium/releases/tag/v1.19.10), [1.18.16](https://github.com/cilium/cilium/releases/tag/v1.18.16) | CVE-2026-111943 に対する臨時のセキュリティパッチリリース。Go を 1.26.10 にアップグレードして侵害された eMudhra 中間 CA 証明書を信頼対象から除外し、依存関係のパッチ更新とバックポート修正を追加 |
| 2026年11月2日 | [1.21.0-pre.4](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.4) | 最新の 1.21 プレリリース：インターフェースベースの BGP unnumbered ピアリング、BPF masquerading のデフォルト有効化、Gateway API のフロントエンドにおけるクライアント証明書検証（mTLS）とリスナー TLS バージョンのオプション、agent/operator でのマルチプール Resource IPAM、Gateway API Inference Extension のサポート。**1.21 はプレリリースのみ**（GA は 2027 年初頭を予定）であり、このガイドで 1.21 として記載した項目は変更される可能性があります |

2026年9月14日、CNCF ブログに [Cilium 1.20 の機能紹介](https://www.cncf.io/blog/2026/09/14/cilium-1-20-gateway-api-externalauth-tcproute-udproute-eni-ipam-for-ipv6-and-more/)（Gateway API ExternalAuth、TCPRoute/UDPRoute、IPv6 ENI IPAM など）が公開されました。これは、以下の 1.20.0 発表概要と同じ範囲を取り上げています。

1.20.0 の発表では、**2,660 件以上の新規コミット**と、それを支えた**1,100 人以上のコントリビューターからなるコミュニティ**が報告されています。後者はコミュニティの規模であり、このリリースにおける作者数ではありません。主な変更点は次のとおりです。

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth、CORS のサポート。ただし、各機能の設定と API の成熟度によります。
- Datapath プラグインと、オプトインで使用する `bpf.datapathMode=auto`。発表時点でのデフォルトは引き続き veth です。デュアルスタッククラスターでは IPv6 egress gateway アドレスを設定できます。
- **Beta** の IPv6 ENI IPAM と、クラスターを再構築せずに cluster-pool から multi-pool へ移行する機能。インプレース移行でも中断が発生しないとは限りません。
- トラフィック分散ヒント、重み付け Maglev バックエンド、安定した MCS 統合、Kubernetes ClusterNetworkPolicy のサポート、**beta** の ztunnel ベースのワークロード ID。
- `cilium-cni` バイナリを約 **77 MB から 16 MB に縮小**したとの報告。ADS/Delta xDS の改善は 1.20 の発表に含まれています。これを 1.18.13 のパッチノートに帰属させないでください。これらは上流リリースの主張であり、この監査で再測定した結果ではありません。

相互認証（1.20 で**非推奨**となり、1.21 のプレリリースで削除）、削除または置き換えられた Envoy Go 拡張、Kafka を考慮したポリシー、旧 CiliumNodeConfig API、libnetwork 統合、カスタム CNI 設定の変更については、[1.20 アップグレードノート](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes)を確認してください。

### NetworkPolicy セキュリティアドバイザリ

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) のプロジェクトアドバイザリ公開日は **2026年7月6日**です。プロジェクト API と GitHub のグローバルアドバイザリ API では日付が異なり、後者には9月3日と記録されています。このリリースの時系列にはプロジェクトの開示日を使用してください。グローバルレコードの日付は、修正リリースがそれ以降に出たことを意味しません。この問題は、アドバイザリに記載されたカスタムクラスター名の条件下で **1.19.0–1.19.4** に影響します。`ipBlock` だけを含む標準の Kubernetes NetworkPolicy ピアによって、選択された Pod と同じ名前空間内のワークロードからの ingress が意図せず許可される可能性があります。**1.19.5** で修正されています。デプロイには適切な最新のパッチ適用済みリリースを使用してください。このアドバイザリによると、CiliumNetworkPolicy/ClusterwideNetworkPolicy と 1.19.0 より前のリリースは、この特定のバグの影響を受けません。

## はじめに

Cilium は、サポート対象の Linux Kubernetes 環境向けにネットワーキング、セキュリティ、可観測性を提供します。ルーティング、IPAM、暗号化、Service の処理はそれぞれ別の選択項目です。eBPF を選ぶだけで、すべての機能が有効になったり、性能が保証されたりするわけではありません。古い Docker libnetwork 統合は 1.20 で削除されたため、Docker/Mesos を現在のインストール対象と同列に記載すべきではありません。

### eBPF と主な機能

カーネルは eBPF プログラムをロードする前に検証し、サポート対象のフックで実行できるよう JIT コンパイルできます。これにより、カスタムカーネルモジュールを使わずにパケット処理と可観測性を実現できます。ただし、検証器はアプリケーションやポリシーが正しいことを証明するものではありません。実際のスループット、レイテンシ、メモリ使用量は、プログラム、プラットフォーム、ワークロードによって異なります。

Cilium は、L3/L4 ポリシー、Envoy/DNS プロキシ統合による L7 ポリシー、オプションの WireGuard/IPsec、Service 負荷分散、Hubble によるフロー可視化、ClusterMesh、BGP 広告を提供します。XDP アクセラレーションは任意であり、デバイスと設定に依存します。L7 機能ではノードごとの Envoy を使用する場合があります。ztunnel によるワークロード ID には別途 beta 設定が必要です。agent をインストールしただけでは、すべてのメッシュ、暗号化、マルチクラスター動作が有効になるわけではありません。

### 他のネットワーキングプロジェクトとの比較

| プロジェクト | 接続性 / IPAM | ポリシーおよび関連機能 |
| --- | --- | --- |
| Cilium | ネイティブまたはオーバーレイルーティング。クラウド ENI を含む IPAM モード | eBPF dataplane、Cilium/Kubernetes ポリシー、L7 統合、Hubble、オプションの暗号化 |
| Calico | Calico または外部 IPAM によるネイティブ/IPIP/VXLAN プロファイル | Linux Iptables/Nftables/BPF、サポート対象の Windows HNS、OSS WireGuard、段階的なポリシー適用、独立した L7 統合 |
| Flannel | VXLAN/host-gw/WireGuard など、選択したバックエンドによる Pod 接続 | ルーティングデーモン自体は NetworkPolicy を適用しません。chart で `netpol.enabled` を指定して SIGs network-policy controller をデプロイするか、別のポリシー実装と組み合わせられます |
| AWS VPC CNI | VPC ENI のアドレス割り当て/ネットワーキング | サポート対象の EC2 Linux ノードにおけるネイティブのネットワークポリシーと、独立した SG-for-Pods 機能。EKS Auto Mode は別のマネージド実装です |

ルーティングモードとパケット処理の実装方法は、同じ分類ではありません。Calico は iptables/IPVS に限定されず、Flannel は暗号化バックエンドを使用でき、AWS のポリシーはセキュリティグループと同義ではありません。Service mesh は任意のレイヤーであり、クラスター間 VPC 接続も Transit Gateway に限定されません。万能な性能ランキングではなく、実測したワークロードと明示的なサポートマトリックスを使用してください。

## アーキテクチャ

**Kubernetes API server** は Kubernetes/Cilium リソースを保存します。Cilium agent は関連する状態を監視し、各ノードの dataplane を設定します。Cilium Operator は、選択した IPAM や ID/コントローラー関連の処理など、クラスター全体の責務を担います。この基本アーキテクチャに、独立したクラスター全体向けの「Cilium API Server」デプロイメントは必須ではありません。agent にはローカル API があり、オプションの ClusterMesh API server は別の目的で使用されます。

| コンポーネント | 役割 |
| --- | --- |
| Cilium Agent | ノードローカルのエンドポイント、ポリシー、ルーティング/Service 状態、eBPF の管理 |
| Cilium Operator | クラスター単位の調整と、モードに応じた割り当て/コントローラー処理 |
| Envoy | 有効化された L7 ポリシー、Ingress/Gateway、関連機能で使用されるユーザー空間プロキシ |
| Hubble server | agent と統合されたノードローカルのフロー API |
| Hubble Relay / UI | フローストリームの集約 / Service マップとフローの表示 |
| Prometheus metrics endpoints | 独立した統計情報収集。Relay/UI はメトリクスのスクレイピング経路ではありません |
| cilium / cilium-dbg / hubble | クラスター管理 CLI / agent の診断 / フロークライアント |

### ネットワーキングとパケット経路

ネイティブルーティングには到達可能なアンダーレイが必要です。トンネリングでは VXLAN または Geneve を使用します。AWS ENI と Azure IPAM は、各プラットフォーム固有の要件を持つ割り当て/統合方式です。Cilium の BGP Control Plane はルーターに到達可能性を広告しますが、**datapath を設定したり、内部クラスターのルーティングを提供したりするものではありません**。

XDP→TC→Pod という汎用的な処理順序はありません。Socket load balancing はパケットが存在する前に動作することがあり、TC/netkit フックは datapath に依存します。オプションの XDP は選択したトラフィックを高速化し、L7 トラフィックは Envoy を通る場合があります。戻りトラフィックの処理も NAT、conntrack、DSR の選択によって異なります。選択したプロファイルについては、ネットワーキングと eBPF の各章を参照してください。

## Amazon EKS との統合

何かをインストールする前に、実際に使用するネットワーキングとコンピュートのプロファイルを選択してください。アドオン名/バージョンの例 `cilium` / `v1.17.0-eksbuild.1` は、AWS のディストリビューションとして検証されておらず、ここではインストールコマンドとして示していません。パッケージ化されたベンダーアドオンを検討する場合は、対象リージョンの実際のアドオンカタログ、発行元、ライセンス、サポート対象のコンピュートタイプを確認してください。

| EKS プロファイル | 確認事項 |
| --- | --- |
| 通常の EC2 ノードで、Cilium ENI が VPC CNI を置き換える構成 | 上流/パートナー管理の CNI。AWS が EC2 向けにサポートする CNI は VPC CNI です。CNI の管理主体、IAM、アドレス指定、ルート、ブートストラップ、ノード移行を計画してください |
| 通常の EC2 ノードで、AWS VPC CNI chaining を使用する構成 | VPC CNI がインターフェース/IPAM を管理し、その後 Cilium が dataplane を接続します。既存 Pod は再作成が必要で、L7/IPsec にはドキュメントに記載された制限があります |
| Hybrid Nodes | AWS の専用 CNI ガイドと AWS が管理する Cilium ビルドマトリックスに従ってください。上流の 1.20.3 が自動的に AWS のサポート対象ビルドになるわけではありません |
| Auto Mode | 代替 CNI/ポリシープラグインはサポートされていません。マネージド NodeClass/ネットワーキング機能を使用してください |
| Fargate | 代替 CNI/DaemonSet のインストールはサポートされていません |
| Windows | Cilium agent の要件は Linux です。この手順を Windows ワーカーに適用しないでください |

AWS の一般的な代替 CNI ページと Hybrid 専用ガイドでは、Calico のサポートに関する記述が異なります。リポジトリ移行の例だけでは、サポート終了が確定したとはいえません。Hybrid Nodes では、正確なディストリビューション、機能セット、サポート責任者を確認してください。Auto Mode では、ノードローカルの CoreDNS/システムネットワーキングも、このガイドの通常の EC2 構成とは異なります。Auto Mode 以外のノードが混在する場合は、従来の DNS Deployment も引き続き必要です。

### Cilium ENI 用に準備した EC2 クラスター

以下は、**準備済みの IPv4 EC2 クラスター向け Cilium Helm values**であり、クラスター作成やインプレース移行の手順一式ではありません。使用する前に、次の点を確認してください。

1. サポート対象の EKS/Kubernetes バージョンと Linux AMI を選び、CNI の管理主体を 1 つに定めます。既存のワークロードクラスターで、手っ取り早い方法として `aws-node` を削除しないでください。
2. Cilium がノードを管理するまでワークロードが待機するよう、ノードの taint/スケジューリングを準備します。上流の EKS ガイダンスでは `node.cilium.io/agent-not-ready=true:NoExecute` を使用しています。実際のノードライフサイクルにおける退避とブートストラップへの影響を評価してください。
3. サブネット容量、ENI クォータ/セキュリティグループ、ノードのメタデータアクセス、Operator に必要な EC2 権限を準備します。以下のロール ARN は、適切な信頼関係を設定した **cilium-operator ServiceAccount** 用ロールのプレースホルダーであり、values ファイルによって作成されるロールではありません。
4. この `kubeProxyReplacement: false` の例では、動作中の kube-proxy と DNS を維持してください。置き換えモードを使用する場合は、API への直接アクセス/ブートストラップ DNS の要件を別途確認してください。max-Pods は一律に 110 とせず、実際のインスタンスタイプ/IPAM 容量に基づいて選択してください。

`cilium-eni-values.yaml` として保存し、ロール/インターフェースの選択をレビュー済みの値に置き換えてください。

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

これらの設定はインストールの管理主体を通じて管理してください。必要な設定がほかにもあるのに、わずかなキーだけを含む `cilium-config` で置き換えると、それらの設定が削除される場合があります。古い `tunnel=disabled` の値は `routingMode: native` に置き換えられています。ENI の割り当て/権限と SNAT の動作は、実行時にも検証が必要です。レンダリングに成功しても、EC2 ネットワーキングが使用可能である証明にはなりません。

**IPv6 に関する注記：** 1.20.3 の ENI IPAM リファレンスでは IPv6 は beta とされていますが、EKS の前提条件ページでは ENI 統合は IPv4 のみと記載されています。このガイドでは IPv4 の例を示し、どちらの記述も本番 EKS での IPv6 互換性の証明と見なさず、ドキュメント間の不一致として記録します。IPv6 の設計を別途行う前に、現在の ENI/デュアルスタックサブネットの要件を確認してください。

### VPC CNI chaining の代替構成

上流の chaining ガイドでは、VPC CNI 1.11.2 以降が必要とされ、以下のプロファイルが記載されています。

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

これは ENI 置き換え用 values に重ねるのではなく、**別の設定**として使用してください。割り当ては引き続き VPC CNI が行います。実際のマネージドアドオンは、過去の上流 DaemonSet を適用するのではなく、その管理主体を通じてアップグレードしてください。同じエンドポイント上でポリシーエンジンが競合しないようにしてください。CNI chain を変更しても、既存 Pod が遡って Cilium に接続されることはありません。計画的なロールアウトで Pod を再作成し、エンドポイントが管理されていることを確認してください。chaining にはドキュメントに記載された L7 ポリシー/IPsec の制限があります。このページの後半にあるすべての例がこのプロファイルで動作すると想定しないでください。

### ClusterMesh

ClusterMesh には、一意なクラスター ID、互換性のあるバージョン、到達可能で重複しない Pod ネットワーク、認証済みの API 接続、適切な公開方法が必要です。LoadBalancer Service はクラウドリソースを作成する場合があり、意図的なネットワーク/セキュリティ設計が必要です。2 つのパブリックエンドポイントを作成するだけでは、クラスターを安全に接続できません。選択したトポロジーに応じて、メンテナンスされている [ClusterMesh ガイド](13-clustermesh-install-upgrade.md)と詳細解説の章に従ってください。

## インストールと設定

### クライアントツール

ワークステーションの OS/アーキテクチャに適した公式 Cilium CLI 0.20.1 と Hubble CLI 1.20.2 のアセットを使用し、展開前に提供されたチェックサムを検証してください。Linux ARM64 と AMD64 ではアセットが異なり、macOS では対応する Darwin アセットを使用します。CLI のバージョンは Cilium agent/chart のバージョンとは別です。[検証済み CLI インストールガイダンス](../../service-mesh/cilium-service-mesh/README.md)を参照してください。

```bash
cilium version --client
hubble version
```

### 非クラウドの cluster-pool の例

以下は、kube-proxy と DNS がすでに動作している、準備済みの通常の Linux クラスター向けの**別の構成例**です。例で使用している `10.244.0.0/16` の Pod 範囲がクラスターと互換性を持ち、Service、ノード、VPC、接続先ネットワークの範囲と重複しないことを確認してください。ENI モードではこの pool 設定を使用しないでください。

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

`cilium-values.yaml` として保存し、バージョンを固定した chart をレンダリングしてから、準備済みのクラスターにのみインストールしてください。

```bash
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

既存のリリースでは、アップグレード/GitOps のプロセスを使用し、管理対象の values を保持して、バージョン固有のアップグレード手順に従ってください。`cilium install` を繰り返す例は、個々の設定を変更する一般的な方法ではありません。

| 選択肢 | 現在の設定と前提条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` と `tunnelProtocol` を設定します。選択したカプセル化方式を許可し、経路に合わせて MTU を設定してください |
| ネイティブルーティング | `routingMode: native` を設定します。アンダーレイで Pod アドレスをルーティングする必要があります。`autoDirectNodeRoutes` には適切な直接接続が必要で、任意のマルチサブネットルーティングには対応しません |
| kube-proxy replacement | 従来の `strict` ではなく、`kubeProxyReplacement: true` または `false` を使用します。置き換えには、到達可能な `k8sServiceHost`/`k8sServicePort` と、ドキュメントに記載されたブートストラップ計画が必要です |
| WireGuard | カーネル/プラットフォームとピア間の経路を確認したうえで、サポート対象の暗号化モードを有効にします。すべてのトラフィック経路が自動的に暗号化されるわけではありません |
| IPsec | ドキュメントに記載されたキー Secret、キーの配布/ローテーション、互換性のあるモードが必要です。Helm の有効化フラグだけでは不十分です |
| XDP/DSR/BBR | デバイス/カーネル/トポロジーに依存する個別の選択肢であり、汎用的なインストールプリセットではありません |

## NetworkPolicy

Kubernetes `networking.k8s.io/v1` NetworkPolicy と Cilium `cilium.io/v2` ポリシーは別々の API です。複数の許可ポリシーが組み合わさることがあります。以下の例では、L4 の許可によって L7 の制限が意図せず迂回されないよう、**準備済みの別々のテスト名前空間**を使用します。結論を出す前に、実際のエンドポイントを選択しているすべてのポリシーを確認してください。

### L4 の例

`cilium-l4-demo` では、次の設定がバックエンド Pod を選択し、同じ名前空間のフロントエンド Pod からの TCP 8080 ingress を許可します。

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

### HTTP の例

別の `cilium-l7-demo` 名前空間では、次の設定がバックエンド Pod を選択し、その名前空間内のフロントエンド Pod から、指定したメソッド/パスへの TCP 8080 上の平文 HTTP のみを許可します。選択した CNI モードで L7 プロキシが利用可能である必要があります。サポート対象の終端設定がなければ、暗号化された HTTP が自動的に検査されることはありません。

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

同じピア/ポートに対して制限のない L4 許可を追加しないでください。Cilium のドキュメントによると、そのような許可を追加すると、より限定的な L7 制限の効果が失われます。L7 で拒否された場合、パケットがドロップされる代わりに HTTP 403 が返ることがあります。実際のエンドポイント ID を使って、許可される GET リクエストと拒否されるメソッド/パスをテストしてください。

### DNS/FQDN の例

`cilium-dns-demo` では、次の設定により、通常の CoreDNS Pod への DNS クエリと、`api.example.com` に対して学習されたアドレスへの TCP 443 を許可します。このドメイン名は例です。承認済みの接続先に置き換えてください。広範囲に許可する `*.amazonaws.com` ワイルドカードは、アカウント/リソースの境界を示すものではないため省略しています。

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

DNS ワイルドカードで許可されるのは、選択したリゾルバーへのクエリであり、返されたすべてのアドレスへの接続ではありません。ただし、任意の DNS 名を問い合わせることはできるため、必要に応じて DNS サフィックスの検索も考慮しながら、クエリ名を制限してください。NodeLocal DNS や別のリゾルバーを使用する場合は、正しい宛先を選択する必要があります。FQDN ポリシーは DNS から取得した IP に対する認可であり、TLS ホスト名検証や HTTP URL 認可ではありません。共有 IP とアプリケーションの TLS/認証も引き続き重要です。

## Hubble による可観測性

上記の cluster-pool values では Relay/UI とコンポーネントメトリクスが有効になります。既存のインストールでは、Hubble の values をその設定の管理主体を通じて適用してください。`cilium hubble enable --ui` はサポート対象の便利なコマンドですが、`cilium hubble enable --metrics=...` は 0.20.1 CLI でサポートされているフラグではありません。代わりに Helm values で `hubble.metrics.enabled` を設定してください。従来の `http` と `httpV2` のハンドラーを同時に有効化しないでください。

1 つ目のターミナルで Relay のポートフォワードを起動したままにします。

```bash
cilium hubble port-forward --port-forward 4245
```

Hubble CLI をインストールした別のターミナルで、次のコマンドを実行します。

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

このローカルの例は、デフォルトの Relay server 設定を前提としています。TLS 対応の Relay では、対応するクライアント側の信頼/認証設定が必要です。HTTP イベントが記録されるのは、トラフィックが設定済みの L7 プロキシを通過する場合です。`DROPPED` は datapath の判定であり、アプリケーションリクエストの失敗すべてを示すものではありません。UI のポートフォワードには `cilium hubble ui` を使用し、メトリクス用の Prometheus ターゲット検出は別途設定してください。Hubble のフローストリーミングだけでは、分散アプリケーションのトレーシングにはなりません。

## テストと運用

接続性/性能のコマンドはテスト用ワークロードを作成し、ポリシーを変更したり、大量のトラフィックを生成したりする場合があります。レビュー済みのテスト用名前空間/環境と権限を使用してください。この監査では、クラスターに対してこれらのコマンドを実行していません。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

性能測定用サブコマンドは `cilium connectivity perf` です。`connectivity test --test=performance` はテスト名のフィルターを指定するだけであり、性能測定の実行コマンドではありません。スループット/レイテンシを比較する前に、ソフトウェアのバージョン、トポロジー、トラフィック、生の測定結果を記録してください。

調査の際は、管理 CLI と**agent 側の `cilium-dbg`を区別してください**。

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

`cilium endpoint list`、`cilium bpf maps list`、`cilium metrics list` は、管理 CLI において同等のコマンドではありません。`cilium sysdump` で診断資料を収集できますが、生成されたインフラストラクチャ/ログデータを保護してください。agent が Ready であることやスクレイピングが成功することは、アプリケーションテストやポリシーの否定テストの代わりにはなりません。

### 運用上の優先事項

- map の事前割り当て、XDP、DSR、BBR、固定デバイスパターンを有効にする前に測定してください。これらはリソースを消費したり、パケット経路を変更したりするため、機能ごとの確認が必要です。
- 対象範囲を限定して default-deny を導入し、DNS、API、ID、アプリケーションの依存関係を明示的に許可してください。確立済みの接続だけでなく、新しい Pod とアップグレード時の移行も確認してください。
- 暗号化、証明書/キーのローテーション、ポリシー適用、可観測性は、それぞれ別の受け入れ確認項目として扱ってください。使用可能な管理/復旧経路を確保してください。
- 現在のプラットフォームマトリックスとサポート対象のアップグレード経路を確認してください。過去のリリース発表は、現在のデプロイ互換性を証明するものではありません。

## 詳細解説の目次

**[Cilium の概要と基本概念](01-introduction.md)**
- Cilium の概要と歴史
- コンテナネットワーキングの基礎
- CNI（Container Network Interface）を理解する
- Cilium の差別化要因となる機能

**[eBPF テクノロジーの詳細解説](02-ebpf.md)**
- eBPF テクノロジーの概要と歴史
- カーネル内部での eBPF の動作
- eBPF プログラムの種類とマップ
- Cilium で eBPF を活用する

**[ネットワーキングモデルと VXLAN](03-networking.md)**
- コンテナネットワーキングモデルの比較
- VXLAN テクノロジーの詳細解説
- Cilium のオーバーレイネットワーキング
- パフォーマンス最適化手法
- ルーティング方式（カプセル化とネイティブルーティング）
- クラウドプロバイダーのネットワーキング（AWS ENI、Google Cloud）

**[IPAM とネットワークポリシー](04-ipam-policy.md)**
- IP アドレス管理（IPAM）の戦略
- Kubernetes と Cilium の IPAM 統合
- ネットワークポリシーの設計と実装
- マルチクラスターのシナリオ
- IPAM モードの詳細（Cluster Scope、Kubernetes Host Scope、Multi-Pool）
- クラウドプロバイダーの IPAM（Azure IPAM、AWS ENI、GKE）
- CRD ベースの IPAM

**[L2-L7 ネットワーキングと負荷分散](05-l2-l7-networking.md)**
- OSI モデルの各レイヤー（L2、L3、L4、L7）の理解
- Cilium のレイヤー別機能
- Service mesh の統合
- 負荷分散のアーキテクチャ
- Masquerading の設定と実装モード
- IPv4 フラグメントの処理

**[セキュリティと可視性](06-security-visibility.md)**
- Cilium のセキュリティ機能
- ネットワークの可視性と監視
- Hubble のアーキテクチャと使用方法
- リアルタイムの脅威検出

**[高度なトピックと実例](07-advanced-topics.md)**
- パフォーマンス調整とトラブルシューティング
- 大規模デプロイ戦略
- 実際のユースケース
- 今後のロードマップと開発方針

**[eBPF datapath の内部](08-ebpf-datapath-internals.md)**
- プログラムセット、アタッチポイント、tail call
- BPF map のカタログ、サイズ設定、コンパイル/ロードの流れ
- ポリシー適用経路と Hubble のイベントパイプライン

**[オーバーレイとネイティブルーティング](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 内の ID、MTU、パケットの経路
- ネイティブルーティング、masquerading、ホストルーティング、DSR、netkit
- EKS の選択表：オーバーレイ、ENI、VPC CNI chaining

**[IPAM の詳細解説](10-ipam-deep-dive.md)**
- すべての IPAM モード、容量計算、選択マトリックス
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- 枯渇時のトラブルシューティングと 1.21 API の変更

**[BGP、ロードバランサー IP、Egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRD、広告、確認方法
- L2 announcement、Egress Gateway、Local Redirect Policy
- Gateway API の要件と EKS での内部限定公開

**[mTLS、暗号化、ID](12-mtls-encryption-identity.md)**
- ID モデル、ポリシーの意味、監査モード
- 相互認証の変遷、ztunnel によるワークロード mTLS
- WireGuard、IPsec、Hubble、証明書管理

**[バージョン、インストール/アップグレード、Cluster Mesh](13-clustermesh-install-upgrade.md)**
- 1.17–1.21 の機能マトリックス、アップグレードとロールバックのルール
- EKS のインストール固有の事項、Cluster Mesh、MCS-API

## 追加リソース

- [ネットワーキングの概念を詳しく解説](networking-concepts.md)
- [用語集と略語](glossary.md)

## 参考資料

- [Cilium 1.20 の Kubernetes 互換性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [Cilium のシステム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [EKS の前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [AWS の代替 CNI サポート](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 ポリシーの意味](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Hubble プロジェクト](https://github.com/cilium/hubble)
- [Flannel のネットワーキングとポリシー統合](https://github.com/flannel-io/flannel)
- [Calico 比較用語](../calico/glossary.md)

## クイズ

このセクションで学んだ内容を確認するには、[Cilium 詳細解説クイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。
