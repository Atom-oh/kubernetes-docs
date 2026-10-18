# Part 13: バージョン、インストール／アップグレード、Cluster Mesh

> **レビュー基準**: Cilium 1.20.2（安定版、2026-09-16）、Cilium CLI 0.20.1、Hubble CLI 1.20.2。**[1.21 プレリリース]** と記した項目は v1.21.0-pre.3 に基づいており、GA までに変更される可能性があります。
> **最終更新日**: 2026年10月15日

この章では、前のパートで概要だけ触れた3つの運用上の疑問に答えます。各機能がどのCiliumバージョンで、どの成熟度で使えるか、安全にインストールおよびアップグレードする方法（EKS固有の詳細を含む）、そしてCluster Meshの仕組みをコントロールプレーンから解説します。以前のリポジトリでは、[IPAMとネットワークポリシー](04-ipam-policy.md)の中に短いCluster Meshの節があるだけでした。この章では詳しく説明します。

関連パート: [はじめに](01-introduction.md)、[ネットワーキング](03-networking.md)、[IPAM](10-ipam-deep-dive.md)、[BGP、ロードバランサー、Egress](11-bgp-lb-egress-edge.md)、[mTLS、暗号化、ID](12-mtls-encryption-identity.md)。

## 目次

1. リリース系列とツールのバージョン
2. バージョン別機能マトリクス（1.17～1.21プレリリース）
3. 1.20.1から1.20.2への変更点
4. 互換性と要件
5. Helmによるインストール（OCIチャート、検証）
6. EKSへのインストール固有の事項
7. アップグレードとロールバックの手順
8. Day 2の設定: ドリフト検出、CiliumNodeConfig、ID移行
9. Cluster Meshのアーキテクチャ
10. Cluster Meshの設定
11. Global Service、アフィニティ、EndpointSlice同期
12. MCS-API（マルチクラスターサービス）
13. クラスター間ポリシー
14. EKS上のCluster Mesh
15. ラボ
16. バージョン差分、トラブルシューティング、検証範囲、参照資料

---

## 1. リリース系列とツールのバージョン

Ciliumには、混同しやすい独立したバージョン体系の成果物が3つあります。

| 成果物 | 今回のレビュー時点 | 備考 |
|---|---|---|
| Cilium（agent、operator、Helm chart） | 1.20.2（2026-09-16） | v1.20.2ツリーの`install/kubernetes/cilium/Chart.yaml`では、チャートの`version`と`appVersion`はいずれも1.20.2です |
| Cilium CLI（`cilium`） | 0.20.1（2026-09-24） | 0.20.1の変更は依存関係とCIのみで、Cilium依存関係をv1.20.2に更新しています |
| Hubble CLI（`hubble`） | 1.20.2（2026-10-07） | 直前のタグは1.19.4で、Hubble CLIの1.20.0／1.20.1タグはありません。1.20.2では、デフォルトのフィールドマスクを使ったポリシー判定イベントに対する`compact`出力が修正されています |
| バックポートブランチ | 1.19.8、1.18.14（いずれも2026-09-16） | 1.20.2と同じ日にリリースされました |
| プレリリース | 1.21.0-pre.3（2026-10-02） | `v1.21.0-pre.1`は公開されていません。pre.2の変更履歴はpre.0からpre.2までを扱います |

Cilium CLIはagentとは別のリリース系列です。特定のagentバージョンを指定する場合は、`--version`を明示してください。

今回のレビュー前後のリリース履歴:

| リリース | 日付 | 備考 |
|---|---|---|
| v1.20.0 | 2026-07-29 | 2660コミット（リリース本文による） |
| v1.20.1 | 2026-08-18 | Cluster Meshドキュメントを大幅改訂。agent再起動後のCIDRポリシー処理に関するendpointの不具合を修正 |
| v1.20.2 | 2026-09-16 | 最新の安定版。3節を参照 |
| v1.21.0-pre.0 | 2026-08-03 | |
| v1.21.0-pre.2 | 2026-09-09 | |
| v1.21.0-pre.3 | 2026-10-02 | 最新のプレリリース |

1.21.0-pre.xはプレビューとして扱ってください。オプション名、デフォルト値、アップグレードに関する注意点は今後変わる可能性があります。

## 2. バージョン別機能マトリクス（1.17～1.21プレリリース）

成熟度を示す語句は、該当バージョンのリリースノートまたはソースツリー内のドキュメント（`.. include:: /beta.rst`のバナー）から引用しています。ダッシュは、その機能がまだ存在しないことを示します。

### 2.1 主な機能

| 機能 | 1.17 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|---|
| 最小カーネル | 5.4 | 5.10（RHEL 8.10では4.18） | 5.10 | 5.10 | 5.10（ネイティブビルドではLLVM >= 21.1） |
| テスト済みKubernetes | 1.17のドキュメントを参照 | 1.33まで（Goライブラリ1.33） | ライブラリ1.35 | 1.33～1.36 | 1.34～1.37 |
| Gateway API CRD | v1.2.1 | v1.3.0 | v1.4 | v1.6.1 | v1.6.1 |
| Helm OCIチャート `quay.io/cilium/charts/cilium` | なし | なし | あり | あり（推奨） | あり |
| MCS-API | ベータ（導入） | ベータ、EndpointSliceミラーリング | ベータ、CRDは`v1alpha1`、CRD自動インストール | 安定版、`v1beta1`（`v1alpha1`も引き続きサポート） | `v1beta1`、ミラーされたEndpointSlice名を修正 |
| Cluster Meshポリシーのデフォルトスコープ | 全クラスター | 全クラスター。`policy-default-local-cluster`フラグを導入（デフォルトはfalse） | ローカルクラスターのみ（デフォルトtrue） | ローカルクラスターのみ、`cluster-mesh`エンティティ | ローカルクラスターのみ |
| `clustermesh.apiserver.tls.authMode` | `legacy`（デフォルト） | `legacy`（デフォルト） | `migration`（デフォルト） | `migration`（デフォルト） | `cluster`（新しい`cluster-strict`もあり） |
| KVStoreMesh | 1.16以降デフォルトで有効 | `kvstoremesh.enabled`は非推奨 | デフォルトで有効 | デフォルトで有効、値は非推奨 | 常に有効、値は削除 |
| Double Write ID割り当て | 導入（ベータ） | ベータ | ベータ | ベータ | ベータ。`cilium-dbg preflight migrate-identity`は非推奨 |
| マルチプールIPAM | ベータ | ベータ（KVStore、IPsec、トンネルにも対応） | 安定版 | 安定版。cluster-poolからmulti-poolへのインプレース移行 | Azure IPAMがmulti-poolへ移行。`CiliumPodIPPool` APIは`cilium.io/v2`と`reservedRanges` |
| ENI IPv6 IPAM | - | - | - | ベータ | ENIモードではIPv6 masqueradeがデフォルトで無効 |
| 相互認証（SPIFFE/SPIRE） | あり | あり | デフォルトで無効 | 非推奨 | 削除（ファイアウォール一覧からポート4250も削除） |
| ztunnel | - | - | ベータ | ベータ（内部CAまたはSPIRE） | ベータ（1.21ツリーの`encryption-ztunnel.rst`には、引き続き`beta.rst`のバナーあり） |
| Kafka対応L7ポリシー | サポート | 非推奨 | 非推奨 | 削除 | 削除 |
| Envoy Go拡張（proxylib） | サポート | 非推奨 | 非推奨 | 削除 | 削除 |
| BGPv1 `CiliumBGPPeeringPolicy` | サポート | 非推奨 | 削除 | - | - |
| ConfigMapドリフト検出（`configDriftDetection`） | - | 1.18.xのパッチリリースにバックポート | 1.19.xのパッチリリースにバックポート | 1.20.0で標準搭載 | 同じ |
| データパスモード | `veth`（デフォルト）、`netkit`（ベータ）、`netkit-l2`、`lb-only` | veth、netkit | トンネル内のBIG TCP、PLPMTUD | `bpf.datapathMode=auto`（対応時はnetkit、非対応時はveth。デフォルトはvethのまま） | 変更なし |

### 2.2 リリースごとの主な変更

**1.17**（2025-02、2761コミット）: QoS用Podアノテーション（Guaranteed／Burstable／BestEffortのegress優先度）、MCS-API導入、プロトコル別（TCP／UDP）サービスロードバランシング、ServiceごとのLBアルゴリズム（maglev／random）、`loadBalancerSourceRanges`のdeny-listモード、タグによるAWS静的IPと単一IPのマルチプール、動的MTU、`CiliumCIDRGroup`によるラベル選択、ポート範囲を対象とするHTTPポリシー、静的Gatewayアドレスに対応したGateway API 1.2.1、動的HubbleメトリクスConfigMap、KVStoreとCRD間の移行に使うDouble Write ID割り当てモード。

**1.18**（3298コミット）: LBコントロールプレーンの再設計、IPsec over VXLAN、複数のegress gateway（IPv6範囲にも対応）、ingress帯域幅のレート制限、トンネルのIPv6 underlay、Hubbleのポリシー名と`policy log`フィールド、`cluster`エンティティをローカルクラスターに限定する機能、`k8s.apiServerURLs`によるAPIサーバーフェイルオーバー、BGP CRD、`CiliumCIDRGroup`と`CiliumLoadBalancerIPPool`を安定版`cilium.io/v2`に昇格、ENIモードのAWS prefix delegation、`CiliumGatewayClassConfig`を含むGateway API 1.3.0、カーネル最小要件を5.10に引き上げ。動作変更: ENIモードで`enableIPv4Masquerade`のデフォルトがtrueからfalseに変更（1.18未満の`upgradeCompatibility`を使うか、明示的に設定）、ENIモードのoperatorに`ec2:DescribeRouteTables`権限が必要、`io.cilium.k8s.policy.serviceaccount`がデフォルトのIDラベルに加わり、アップグレード時に一時的なIDの入れ替わりが発生。

**1.19**（2934コミット）: ポリシーのデフォルトをローカルクラスターに限定、相互認証をデフォルトで無効化、マルチプールIPAMを安定版に昇格、OCI Helmチャート、ztunnelをベータ化、IPsecとWireGuardの厳格な暗号化モード、Kafkaポリシーフィールドを非推奨化して`FromRequires`／`ToRequires`を削除、BGPv1削除、MCS-API CRDの自動インストール（`clustermesh.mcsapi.installCRDs`）、証明書生成を再設計してCronJobをHelm hookではなくしたためArgo CDや`--wait`に適合、Gateway API 1.4、GAMMA GRPCRoute。

**1.20**（2026-07-29）: Gateway API 1.6.1（ListenerSet、BackendTLSPolicy、TCPRoute／UDPRoute、ExternalAuth、CORS）、データパスプラグイン、`bpf.datapathMode=auto`、egress gatewayのIPv6 egress IP、`cilium-dbg shell -- bgp/*`経由のBGPとGoBGP 4.6.1、ENI IPv6（ベータ）、cluster-poolからmulti-poolへのインプレース移行、`PreferSameZone`／`PreferSameNode`トラフィック分散、`service.cilium.io/weight`によるMaglevウェイト（0でdrain）、MCS-API安定版、`cluster-mesh`ポリシーエンティティ、Kubernetes ClusterNetworkPolicyのadmin／baseline階層、ConfigMapドリフト検出、`cilium-cni`バイナリを77 MBから16 MBに縮小、Kubernetes 1.36、Envoy 1.37.x。**1.20で削除**: Envoy Go拡張（proxylib）、Kafka対応L7ポリシー、`CiliumNodeConfig`の`v2alpha1`、`clustermesh.enableMCSAPISupport`（`clustermesh.mcsapi.enabled`を使用）、Cluster Meshの証明書を値として直接指定する方式、`cilium-docker-plugin`、旧`encryption.strictMode.*`フラグ（新しい`encryption.strictMode.egress.*`を使用）、`--node-port-algorithm`／`--node-port-mode`、`--ces-slice-mode`、`encryption.ipsec.interface`。**動作変更**: `bpf.tproxy=true`はnetkitと併用不可。SocketLBを使わないPod（または`socketLB.hostNamespaceOnly=true`のPod）からクラスター内NodePortへアクセスすると、クライアントPod側でロードバランスされるため、クライアントのegressポリシーとバックエンドのingressポリシーの両方で許可が必要。空の`CiliumNetworkPolicy`／`CiliumClusterwideNetworkPolicy`（`spec`／`specs`なし）はadmissionで拒否。Cluster Meshの自動生成証明書は有効期間がデフォルト1年で、4か月ごとにCronJobで再生成。certgenはCAの有効期間がleaf以上であることを検証（`certgen.enforceCAValidityThroughoutLeavesDuration=false`で無効化）。

**1.21プレリリース**（v1.21.0-pre.3）: delta xDS（`envoy.xdsMode=delta-split`）、Cilium Network Driver（DRA、SR-IOV）、Gateway API session persistence、ポリシー内のAWS managed prefix list、KVStoreMeshを常時有効化、Cluster Meshの`authMode`デフォルトを`cluster`に変更、相互認証を削除、`encryption.nodeEncryption`（WireGuard）を非推奨化し1.22で削除予定、operatorの`--aws-use-primary-address`フラグを削除（`eni.nodeSpec.usePrimaryAddress`を使用）、Gateway／GAMMAインフラメタデータの`cec.cilium.io/*`アノテーションを生成先の`CiliumEnvoyConfig`へ伝播しないよう変更、operatorが旧オブジェクトのストレージバージョンを自動移行、Kubernetesライブラリ1.37。pre.2のリリースノートにある「BPF masqueradingをデフォルトで有効化」はpre.3ツリーには反映されていません（「検証範囲」を参照）。

## 3. 1.20.1から1.20.2への変更点

`gh api repos/cilium/cilium/compare/v1.20.1...v1.20.2`では204コミットと報告されます（APIはファイル一覧を300件で打ち切るため、変更ファイル数は信頼できません）。機能に影響するコミットを一覧全体で監査したわけではありません。アップグレードのリスクが低いと決めつけず、リリースノートを確認してください。特定の構成に関係する修正が複数あります。

| 領域 | 修正内容 |
|---|---|
| AWS ENI IPAM | 使用中のprefix-delegated IPをoperatorが個別IPとして解放していた問題、サブネットのprefix枯渇時に割り当てが失敗する問題、`ipv4NativeRoutingCIDR`がセカンダリVPC CIDRの場合にENIモードでagentが起動時にクラッシュする問題を修正。IPv6 ENIルーティング（health endpoint、ingress、IPsec）を修正。masquerade設定変更後のENI endpointルーティング規則を復元し、EC2 IMDSの負荷を軽減 |
| Cluster Mesh | 削除済みのリモートクラスターが接続状態のままになるまれな競合、Cluster Meshから取り込むService backendの検証、設定変更時にclustermesh-apiserverのetcdユーザー管理が古いロールを失効しない問題を修正（Helmチャートのユーザーには影響なし） |
| アップグレード | Cilium 1.15以前で作成したクラスターは、`CiliumNodeConfig`の`v2alpha1` CRDバージョン削除によりアップグレードに失敗。1.20へ上げる際は1.20.2以降を使用 |
| 無視されていたオプション | 受け付けられていたものの黙って無視されていた5つのオプションが動作するように修正: `vtep-sync-interval`、`enable-xt-socket-fallback`、カスタムCNI設定での`eni-delete-on-termination`、chaining mode以外でのHelm `enableIdentityMark`、`lb-retry-backoff-max`。sinkへ届かなかったHubble設定4つも修正 |
| データパス | 分割されたUDPをWireGuardと誤判定する問題、SNAT LB通信のICMPエラーチェックサム、DSR復旧とPMTU ICMP送信元、`externalTrafficPolicy: Local`でのL2 announcement、LocalRedirectPolicyの回帰、egress denyメトリクスの`policy-deny-response: icmp`を修正 |
| ポリシー | NetworkPolicy変更直後に作られたPodで最大2分間古いrevisionが表示される問題、named port利用時の並行policy-mapクラッシュ、想定の2倍の時間identityが残存する問題を修正 |
| Gateway API | 無効な`backendRef`を指定した`HTTPRoute` ExternalAuthをfail-closedに変更。`bpf.tproxy`がfalse（デフォルト）の場合、Gateway APIにはiptablesとnetfilter TPROXYモジュールが必要だとドキュメントに明記 |
| BGP | `defaultGateway` peerの自動検出が誤ったルーティングテーブルを選ぶ問題を修正 |

1.20.2でのイメージおよびチャートの更新: certgen v0.4.9からv0.4.11、Envoy v1.37.5からv1.37.6、hubble-ui v0.13.5からv0.13.6、SPIRE 1.15.2から1.15.3。`values.yaml`の差分はイメージタグとスキーマアノテーション1つだけです。また、`enableIdentityMark`が設定された場合にのみ`enable-identity-mark` ConfigMapキーが出力されるようになりました。

1.20.2のドキュメント変更: `system_requirements.rst`の必須カーネル設定から2項目（`CONFIG_CRYPTO_USER_API_HASH`、`CONFIG_INET_XFRM_MODE_TUNNEL`）を削除。Cluster Meshの導入に「セキュリティ」節を追加し、mesh内のクラスターは単一の信頼ドメインを形成するため、相互に信頼し、同等のセキュリティ態勢を持つクラスターのみ接続するよう説明しています。

推奨: ENI利用者、Cluster Meshのデプロイ、Cilium 1.15以前で作成したクラスターでは、`--version 1.20.2`を使用してください。

## 4. 互換性と要件

### 4.1 バージョン互換性

| 項目 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|
| Kubernetes（テスト済み） | 1.33、1.34、1.35、1.36 | 1.34、1.35、1.36、1.37 |
| Linuxカーネル | >= 5.10（RHEL 8.10: 4.18） | >= 5.10 |
| clang／LLVM（agentのネイティブビルドのみ） | >= 18.1 | >= 21.1 |
| Gateway API CRD | v1.6.1が必須 | v1.6.1 |
| Helm chart `kubeVersion` | `>= 1.21.0-0`（テスト範囲ではなくチャート制約） | 同じ |
| Cilium CLI | 0.20.1 | 該当なし |
| Hubble CLI | 1.20.2 | 該当なし |

1.20.2のシステム要件にある機能別カーネル最小要件: AMD64でのmulticastは>= 5.10、AArch64では>= 6.0、IPv6 BIG TCPは>= 5.19、IPv4 BIG TCPは>= 6.3、netkitは`CONFIG_NETKIT=y`を有効にした>= 6.8。1.19の注意点として、IPsecとkube-proxy replacementとBPF masqueradeを併用するとBPF host routingが自動的に有効になります。これにはCVE-2025-37959に対するカーネル修正が必要です。

Cluster Meshには別の制約があります。接続するすべてのクラスター間で、Ciliumのマイナーバージョン差を1以内にしてください（例: 1.19.xは1.18.xと1.20.xには接続できますが、1.17.xには接続できません）。

### 4.2 ポート

ノード間の通信は、セキュリティグループ参照またはプライベートCIDRに限定して許可してください（`0.0.0.0/0`は絶対に使わないでください）。

| ポート | 用途 |
|---|---|
| UDP 8472 | VXLANトンネル |
| UDP 6081 | Geneveトンネル |
| TCP 4240およびICMP type 8/0 | ヘルスチェック |
| TCP 4244 | Hubble server |
| TCP 4245 | Hubble Relay |
| UDP 51871 | WireGuard |
| ESP（IP protocol 50） | IPsec（AWSセキュリティグループはルールで許可しない限りESPをブロック） |
| TCP 4250 | 相互認証（1.20のドキュメントには記載、1.21のドキュメントでは削除） |
| TCP 2379 | クラスター間のclustermesh-apiserver |

### 4.3 Gateway API CRD

Cilium 1.20にはGateway API CRD v1.6.1が必要です（`Documentation/conf.py`の`gateway_api_version = 'v1.6.1'`、`go.mod`の`sigs.k8s.io/gateway-api v1.6.1`）。Helm chartはCRDをインストールしません。必須CRD: GatewayClass、Gateway、HTTPRoute、GRPCRoute、ReferenceGrant、BackendTLSPolicy、TLSRoute。任意CRD（なければ該当機能は無効）: TCPRoute、UDPRoute、ListenerSet。前提条件は`kubeProxyReplacement=true`、`l7Proxy=true`、およびiptablesとTPROXYモジュールです。ただし`bpf.tproxy=true`（ベータ）の場合は不要です。`kubectl apply --server-side`で適用します。

TLSRouteの注意点: すでにTLSRouteを使っている場合は、`v1alpha2`を引き続き含むexperimental channelのTLSRoute v1.6.1をインストールしてください。standard channelのTLSRoute v1.6をインストールすると、既存のTLSRouteオブジェクトを読み取れなくなり、実質的に消失します。先にオブジェクトをバックアップしてください（`kubectl get tlsroutes -A -o yaml`）。

## 5. Helmによるインストール

Helm chartは次の2か所から取得できます。

| 配布元 | 状態 |
|---|---|
| `oci://quay.io/cilium/charts/cilium` | 1.19以降の推奨として記載。チャートはcosign署名付きで、digestを指定して固定可能 |
| `https://helm.cilium.io/`（`helm repo add cilium`） | 従来のリポジトリ。引き続き完全にサポート |

チャートバージョンには`v`を付けません（`--version 1.20.2`）。イメージタグには付きます。OCIレジストリでは`helm search`を使えません。バージョン一覧には`crane ls quay.io/cilium/charts/cilium`を使用してください。チャート署名を検証します。

```bash
cosign verify \
  --certificate-identity-regexp='https://github.com/cilium/cilium/.*' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  quay.io/cilium/charts/cilium:1.20.2
```

値はバージョン管理下のファイルに保存し、`-f values.yaml`でインストールしてください。大量の`--set`フラグに頼らないでください。7節のとおり、マイナーバージョンを上げるたびに値を再指定する必要があります。

## 6. EKSへのインストール固有の事項

### 6.1 モードの選択

| モード | Helm設定 | データパス／IPAM | 備考 |
|---|---|---|---|
| ENI（EKSでのupstreamデフォルト） | `eni.enabled=true` | ネイティブルーティング（`eni.enabled`時のchartデフォルト）、AWS ENI IPAM、Kubernetes CRD datastore | PodにはVPCでルーティング可能なIPを割り当てます。operatorにEC2 API権限が必要です。Ciliumノードでは`aws-node`を実行しないでください |
| Overlay | `eni.enabled`を省略（chartデフォルトはトンネル／VXLAN） | VXLAN、cluster-pool IPAM | ENIの上限を超えるPodを各ノードで実行可能。PodからVPCへの通信はnode IPにSNATされます。EKS API serverはoverlayのPod IPへルーティングできないため、webhookはhost networkを使うか、Service／Ingress経由で到達できる必要があります。VPC CNIが残した`AWS-SNAT-CHAIN-0/1`と`AWS-CONNMARK-CHAIN-0/1`のiptables chainをflushしてください |
| VPC CNIとのchaining | `cni.chainingMode=aws-cni`、`cni.exclusive=false`、`enableIPv4Masquerade=false`、`routingMode=native` | ネットワーキングはVPC CNI、Ciliumはポリシーと可視性を追加 | VPC CNI >= 1.11.2が必要です。有効化後、既存Podを再起動してください。chainingの制約はupstreamの`cni-chaining-limitations.rst`に記載されています。選択前に確認してください |
| EKS Hybrid Nodes | AWSビルドのchart `oci://public.ecr.aws/eks/cilium/cilium` | VXLAN overlay、cluster-pool | 6.4を参照 |
| EKS Auto Mode | 非対応 | 該当なし | 6.5を参照 |

### 6.2 ENIモードのインストール

CiliumがENIを管理するため、Cilium管理下のノードでVPC CNIが動作しないようにします。upstreamのコマンドをそのまま使い、どのノードにも存在しないnode selectorで`aws-node` DaemonSetをpatchしてください。

```bash
kubectl -n kube-system patch daemonset aws-node --type='strategic' \
  -p='{"spec":{"template":{"spec":{"nodeSelector":{"io.cilium/aws-node-enabled":"true"}}}}}'
```

アプリケーションPodがCiliumの準備前に起動しないよう、managed node groupにtaintを設定します（upstreamの推奨）。

```yaml
# eksctl ClusterConfig fragment
managedNodeGroups:
- name: ng-1
  taints:
  - key: "node.cilium.io/agent-not-ready"
    value: "true"
    effect: "NoExecute"
```

valuesファイル（すべてのキーは1.20.2 chartに存在します。`eni.enabled=true`を設定するとoperatorイメージ、endpoint route、CiliumNode管理、IPv4 masqueradeのデフォルトが設定されます。また、`eni.enabled=true`なしで`ipam.mode=eni`を指定するとchart検証が失敗します）。

```yaml
# values-eks-eni.yaml  (Cilium 1.20.2)
eni:
  enabled: true
kubeProxyReplacement: true
k8sServiceHost: <EKS-API-ENDPOINT-FQDN-without-scheme>
k8sServicePort: 443
cluster:
  name: eks-a
  id: 1   # keep below 128 in ENI mode (see the cluster.id note in the Helm reference)
```

```bash
helm install cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f values-eks-eni.yaml
```

注意点:

- kube-proxy replacementを使う場合、kube-proxyを削除する前に`k8sServiceHost`と`k8sServicePort`を設定してください。そうしないとagentがAPI serverに接続できません。
- operatorにはEC2権限（upstreamの`ec2privileges`節を参照）が必要です。1.18以降は`ec2:DescribeRouteTables`も必要です。
- 1.18でENIモードの`enableIPv4Masquerade`デフォルトがfalseに変わりました。1.18より前のENIクラスターをアップグレードし、masqueradeに依存している場合は、明示的に設定するか`upgradeCompatibility`を使ってください。
- ENI IPv6は1.20ではベータです（`eni.rst`）。upstreamの`requirements-eks.rst`にはENIはIPv4のみとする記述がまだありますが、リリースノートと`eni.rst`に従ってください。
- ENIでは1.20.2を使用してください。prefix delegationの解放、サブネットのprefix不足時の割り当て、セカンダリVPC CIDRを使うネイティブルーティングのクラッシュが修正されています。
- Pod IPは`default` poolから割り当てられます。ENIモードでは`CiliumPodIPPool`と`ipam.cilium.io/ip-pool`アノテーションは使われません（`eni.rst`）。[IPAM](10-ipam-deep-dive.md)も参照してください。

### 6.3 AMI

1.20.2のシステム要件では、Amazon Linux 2とBottlerocket（全バージョン）、Ubuntu >= 20.04、RHEL >= 8.6、Talos >= 1.5.0、Flatcar（ENIではDHCPに注意）をサポート対象としています。Amazon Linux 2023は名前が明記されていません。カーネルは5.10の最小要件より新しいものの、これは推論でありupstreamによる明示ではありません。AWSのHybrid Nodesドキュメントでは、Ubuntu 20.04とRHEL 8はCilium 1.18.3のカーネル要件を満たさないとしています。

### 6.4 EKS Hybrid Nodes

AWSがHybrid NodesでCiliumをサポートするのは、公開ECRリポジトリ`oci://public.ecr.aws/eks/cilium/cilium`にあるAWS保守ビルドのみです（AWSのドキュメントには`1.17.9-0`や`1.18.3-0`などのバージョンが掲載されています。これより新しいAWSビルドの一覧は今回のレビューでは確認していません）。Hybrid NodesではVPC CNIを使えません。AWSのデフォルト構成はVXLAN overlayとcluster-pool IPAMです。pool CIDRはEKSのremote Pod networkと一致させ、node、VPC、Service CIDRと重複させず、デプロイ後に変更しないでください。`eks.amazonaws.com/compute-type In hybrid` affinityでagentとoperatorをHybrid Nodesに固定し、BGP Control Planeを使ってPod CIDRをルーティング可能にします。AWSのサポート表ではCilium IngressとCilium GatewayをHybrid Nodesでサポートしています（デフォルト構成。[CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)と[Ingress](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html)のページを参照）。`envoy.enabled: false`はAWSのベースライン例のvaluesにのみ記載されています。Cilium Ingress／GatewayとL7 network policyにはEnvoyが必要なので、利用する場合はAWSのIngressページに従い有効にしてください。この構成ではAWSクラウド側ノード上のCiliumはサポートされません。

### 6.5 EKS Auto Mode

EKS Auto ModeはCiliumと連携しません。AWSのドキュメントでは、Auto Modeは代替CNIプラグインやネットワークポリシープラグインをサポートしないとしています（EKS User Guideの「alternate CNI plugins」と「auto networking」ページ）。upstream CiliumドキュメントにもAuto Modeのページはありません。Ciliumには通常のmanaged node groupまたはself-managed nodeを使ってください。

### 6.6 このリポジトリの公開範囲のルール

この章の構成にpublic listenerは必要ありません。VPC外のクライアントからアプリケーションへ到達させる場合は、CloudFrontのVPC originからinternal ALB／NLBへ接続してください。clustermesh-apiserver Serviceもinternalにします（14節）。

## 7. アップグレードとロールバックの手順

### 7.1 ルール

1. テスト対象は連続したマイナーバージョン間のアップグレードとロールバックのみです（1.19から1.20への移行とその逆）。マイナーを飛ばさないでください。
2. まず、現在のマイナー系列の最新パッチへ上げ、すべての修正を含むロールバック先を確保してください。
3. agent、operator、Hubble Relay、clustermesh-apiserverをすべて同じバージョンにアップグレードしてください。agentだけを更新してはいけません。
4. L3／L4トラフィックへの影響はほぼないか、わずかです。ユーザー空間proxy（L7 policy、Ingress、Gateway API、Envoy）を経由する接続は中断され、クライアント側で再接続が必要です。各ノードではagentが戻るまで新しいポリシールールの適用が遅れます。
5. マイナーバージョンをまたいで`helm upgrade --reuse-values`を使わないでください。新しいchartのデフォルト値が反映されず、壊れたmanifestが生成される場合があります。chartバージョンが変わらない場合（この章後半のCluster Mesh設定更新など）に限り、`--reuse-values`を使えます。
6. `upgradeCompatibility`にはアップグレード元ではなく、最初にインストールしたマイナーを設定します。出力されるConfigMapのデフォルト値を古いものに固定します。例えば1.18より前のENI masqueradeデフォルトを復元します。
7. Cilium 1.15以前で作成したクラスターは1.20.0／1.20.1ではなく、1.20.2以降へアップグレードしてください。

### 7.2 手順

```bash
# 0. Save and review current values for renamed/removed keys
helm get values cilium -n kube-system -o yaml > old-values.yaml

# 1. Pre-flight: pre-pulls the new image on every node and validates existing CNPs
helm install cilium-preflight oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system \
  --set preflight.enabled=true --set agent=false --set operator.enabled=false
#   (add k8sServiceHost/k8sServicePort when kube-proxy replacement is on)
kubectl -n kube-system get ds cilium-pre-flight-check   # READY must equal the node count
kubectl -n kube-system get deploy cilium-pre-flight-check   # must be 1/1
kubectl -n kube-system logs deployment/cilium-pre-flight-check -c cnp-validator --previous
helm delete cilium-preflight -n kube-system

# 2. Upgrade (NO --reuse-values); 1.19 is the minor you installed originally in this example
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f old-values.yaml --set upgradeCompatibility=1.19

# 3. Watch
kubectl -n kube-system rollout status ds/cilium
kubectl -n kube-system rollout status deploy/cilium-operator
cilium status --wait
```

事前チェック用Deploymentが`READY 0/1`のままの場合、新バージョンで検証に失敗する既存のCiliumNetworkPolicyが少なくとも1つあります。アップグレード前にポリシーを修正してください。

### 7.3 ロールバック

```bash
helm history cilium -n kube-system
helm rollback cilium <REVISION> -n kube-system
# or, for the DaemonSet only:
kubectl -n kube-system rollout undo daemonset/cilium
```

新しいマイナーの機能（新しいCRやConfigMapのopt-in設定など）をすでに使った場合は、ロールバック前にそのバージョンのアップグレードノートを確認してください。ロールバックで古いmanifestは復元されますが、新バージョンが作成したオブジェクトは戻りません。

### 7.4 CRDの扱い

| CRDファミリー | インストール／更新担当 | 対応 |
|---|---|---|
| Cilium CRD（`cilium.io`） | operator／agentが起動時に登録・更新 | 特になし。ただしアップグレード後に`kubectl get crd \| grep cilium.io`で確認。1.20では`CiliumNodeConfig`の`v2alpha1`を削除したため、`cilium.io/v2`を使用 |
| Gateway API | 手動で実施（`kubectl apply --server-side`） | 4.3節にあるバージョンを使用。先にTLSRouteをバックアップ |
| MCS-API（`multicluster.x-k8s.io`） | `clustermesh.mcsapi.enabled=true`ならchartが担当。ただし1.19以降、`clustermesh.mcsapi.installCRDs=false`ならインストールしない | 別のcontrollerが管理する場合は`installCRDs=false`を設定 |
| 廃止されたストレージバージョン | **[1.21 プレリリース]** operatorが自動移行 | `CiliumPodIPPool`の`v2`がストレージバージョンになります |

### 7.5 マイナーごとに確認するアップグレード作業

移行先マイナーの「Upgrade Notes」を必ず確認してください。前述のうち問題になりやすい項目: ENI masqueradeのデフォルトと`ec2:DescribeRouteTables`（1.18）、service-accountラベル追加によるidentityラベルの入れ替わり（1.18）、`policy-default-local-cluster`がtrueに変更（1.19、13節参照）、相互認証がデフォルトで無効（1.19）、オプションおよびKafka／proxylibの削除（1.20）、`bpf.tproxy`とnetkitの併用、NodePortのクライアント側ロードバランシング（1.20）、`authMode=cluster`のデフォルト化と`kvstoremesh.enabled`値の削除（1.21プレリリース）。

## 8. Day 2の設定

### 8.1 ConfigMapドリフト検出

多くのオプションはagentの再起動後にのみ有効になります。`helm upgrade`または`cilium config set`で`cilium-config` ConfigMapを編集すると、実行中のagentとConfigMapの設定が異なる場合があります。ドリフト検出を使うと、その状態を確認できます。1.20.0で標準搭載され、1.18.xと1.19.xのパッチリリースにもバックポートされました（v1.18.14とv1.19.8のchartにはありますが、v1.18.0とv1.19.0のchartにはありません）。

```yaml
configDriftDetection:
  enabled: true        # enable-dynamic-config: watch the ConfigMap
  driftChecker: true   # enable-drift-checker: compare desired vs active
  ignoredKeys: []      # for example ["devices"] for keys that are intentionally different
```

キーごとに不一致を示す警告をagentログへ出力し、ゲージ`cilium_drift_checker_config_delta`を公開します。値が`0`なら同期済み、0より大きければagentは現在のConfigMapを適用しておらず、再起動が必要です。ロールアウト時間を超えて`cilium_drift_checker_config_delta > 0`が続く場合にアラートを出してください。

`cilium config set <key> <value>`はConfigMapを編集し、デフォルトでagentを再起動します。再起動を保留してドリフトゲージに変更待ちを表示するには、`--restart=false`を指定してください。

### 8.2 CiliumNodeConfig（ノード単位の上書き）

`CiliumNodeConfig`（`apiVersion: cilium.io/v2`、namespace `kube-system`）は、`spec.nodeSelector`に一致するノードのConfigMap／agentキーを上書きします（空のselector `{}`は全ノードに一致）。変更を反映するにはagent Podを再作成するか、ノードを再起動する必要があります。`v2alpha1`は1.20で削除されました。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  namespace: kube-system
  name: enable-xdp
spec:
  nodeSelector:
    matchLabels:
      io.cilium.xdp-offload: "true"
  defaults:
    bpf-lb-acceleration: native
```

典型的な用途は、対応ハードウェアを持つノードだけでXDPやIPv6 BIG TCPを有効にすること、kube-proxy replacementを段階的に展開することです。後者では、移行対象ノードに`io.cilium.migration/kube-proxy-replacement=true`ラベルを付け、kube-proxy DaemonSetをそのラベルの`NotIn` affinityでpatchし、CiliumNodeConfigに`kube-proxy-replacement: "true"`を設定したうえで、ノードごとにagent Podを削除します。kube-proxyを停止する前に`k8sServiceHost`と`k8sServicePort`を設定してください。

### 8.3 KVStoreからCRDへのidentity移行（Double Write、ベータ）

1.17で導入され、1.20.2と1.21 pre.3でもベータです。割り当てモードはagentオプション`--identity-allocation-mode`で、Helm値`identityAllocationMode`を使って設定します（chartではConfigMapキー`identity-allocation-mode`として出力）。

| 手順 | モード | ロールアウト順序 | 正とするデータ |
|---|---|---|---|
| 0 | `kvstore` | | KVStore |
| 1 | `doublewrite-readkvstore` | operator、次にagent | KVStore（identityもCRDへ書き込むが、CRDは参照しない） |
| 2 | `doublewrite-readcrd` | operator、次にagent | CRD（迅速なロールバック用にKVStoreにも書き込む） |
| 3 | `crd` | agent、次にoperator | CRDのみ。KVStoreを廃止可能 |

各段階の間でデータが収束するのを待ちます。operatorは`cilium_operator` namespaceにゲージを公開します。upstreamのupgradeページには古い名前`cilium_operator_identity_*_count`がまだ載っていますが、v1.20.2の`operator/doublewrite/metrics.go`では`doublewrite_crd_identities`、`doublewrite_kvstore_identities`、`doublewrite_crd_only_identities`、`doublewrite_kvstore_only_identities`を登録しており、`cilium_operator_doublewrite_*`として表示されます。使用バージョンでの正確な名前は、operatorのmetrics portへ`curl`して確認してください。KVStoreとCRDのガベージコレクションは実行時刻が異なるため、一時的な差は正常です（`--identity-gc-interval`、`--identity-heartbeat-timeout`）。逆方向（CRDからKVStore）への移行は手順を逆に繰り返します。初期状態からの復旧: agentが`crd`モードで動いていない状態で`kubectl delete ciliumid --all`を実行します。

単発の`cilium-dbg preflight migrate-identity`ツールは1.20.2で制約付き（identity churnが許されず、簡単にロールバックできない）として記載され、1.21プレリリースでは非推奨です。Double Writeを使ってください。

## 9. Cluster Meshのアーキテクチャ

Cluster Meshは複数のKubernetesクラスターのコントロールプレーンを接続し、identity、endpoint、node、Serviceを共有します。一方、Podトラフィックはgatewayやproxyを介さず、ノード間を直接流れます。

```
 Cluster 1                                         Cluster 2
 ┌──────────────────────────────┐                  ┌──────────────────────────────┐
 │ clustermesh-apiserver (Deploy)│                 │ clustermesh-apiserver (Deploy)│
 │  ┌────────┐ ┌──────────────┐ │  mTLS etcd 2379  │  ┌────────┐ ┌──────────────┐ │
 │  │ etcd   │◄┤ apiserver    │ │◄────────────────►│  │ etcd   │◄┤ apiserver    │ │
 │  │(local  │ │ (sync local  │ │  (via internal LB│  │        │ │              │ │
 │  │ state) │ │  state -> etcd)│ │   / NodePort)   │  │        │ │              │ │
 │  └───▲────┘ └──────────────┘ │                  │  └───▲────┘ └──────────────┘ │
 │      │      ┌──────────────┐ │                  │      │      ┌──────────────┐ │
 │      └──────┤ kvstoremesh  │─┼─ pulls remote ──►│      └──────┤ kvstoremesh  │ │
 │             └──────▲───────┘ │   cluster state  │             └──────▲───────┘ │
 │   agents read ONLY │ local   │                  │   agents read ONLY │ local   │
 │   ┌────────────────┴─┐       │                  │   ┌────────────────┴─┐       │
 │   │ cilium-agent (DS)│       │                  │   │ cilium-agent (DS)│       │
 │   └─────────┬────────┘       │                  │   └─────────┬────────┘       │
 └─────────────┼────────────────┘                  └─────────────┼────────────────┘
               └──────── Pod -> Pod, node to node (VXLAN/Geneve or native) ───────┘
```

構成要素（v1.20.2の`intro.rst`、`values.yaml`）:

- **clustermesh-apiserver**は3つのコンテナを含むDeploymentです。`etcd`は永続ストレージを使わない単一の組み込みインスタンスです。起動時にKubernetes API serverから状態を再構築し、mTLSで公開されます。`apiserver`はローカルのCiliumとKubernetesの状態（node、endpoint、identity、Service）をそのetcdに同期します（`etcdQPS: 50`）。`kvstoremesh`は各リモートクラスターの状態をローカルetcdキャッシュに取り込みます（`etcdQPS: 100`）。
- **KVStoreMesh**: agentはローカルキャッシュからのみリモート状態を読み取るため、それぞれのagentがすべてのリモートetcdへ個別に接続する必要はありません。1.16からデフォルトで有効です。`clustermesh.apiserver.kvstoremesh.enabled`値は1.18で非推奨になり、**[1.21プレリリース]では無条件に有効となり**、値も削除されます。
- **レプリカ**: `clustermesh.apiserver.replicas`のデフォルトは1です。各レプリカはそれぞれetcdクラスターを実行し、リモートクライアントはService経由で接続先を選びます。`service.enableSessionAffinity`（デフォルト`HAOnly`、ほかに`Always`、`Never`）は、再接続時に全状態を再同期する頻度を減らします。`podDisruptionBudget`はデフォルトで無効です。
- **KVStoreモード**: Ciliumがすでに外部etcdをidentity／状態ストアとして利用している場合、Cluster Meshでも再利用できます（`clustermesh.apiserver.kvstoremesh.kvstoreMode: external`）。`external`と`crd` identity割り当てモードは併用できません。
- **単一の信頼ドメイン**（v1.20.2 `intro.rst`）: 侵害されたクラスターから他のクラスターへ不正な状態を伝播されるおそれがあります。相互に信頼し、同等のセキュリティ態勢を持つクラスターだけを接続してください。

### 9.1 データパス

リモートPodはローカルipcacheに登録され、トンネルendpointとしてリモートノードが指定されます（overlayの場合）。ネイティブルーティングではunderlayによってルーティングされます。identityにはcluster IDが含まれるため、クラスター1でクラスター2のPodからのトラフィックを判定するポリシーは、リモートPodの数値identityを使い、gatewayなしで機能します。このためPod CIDRの重複を避け、node IP間の接続性を確保することが必須です。

## 10. Cluster Meshの設定

### 10.1 前提条件

| 要件 | 詳細 |
|---|---|
| データパスモードを統一 | すべてのクラスターをoverlay、またはすべてをネイティブルーティングにする |
| Ciliumのマイナーバージョン差 | 最大1つ |
| 一意で重複しないPod CIDR | 全クラスターの全ノードで重複を避ける |
| ノード間の到達性 | 各ノードのInternalIPを利用（peering、TGW、VPN） |
| ファイアウォール | TCP 2379（clustermesh-apiserver）、TCP 4240とICMP（health）、UDP 8472／6081（トンネル）、UDP 51871（WireGuard） |
| ネイティブルーティングのみ | `ipv4NativeRoutingCIDR`に全クラスターのPod CIDRが含まれること（例: `10.0.0.0/8`）。Podが全ポートでクラスター間ルーティング可能なこと |

### 10.2 クラスター名とID

| 設定 | ルール |
|---|---|
| `cluster.name` | 最大32文字。正規表現は`^([a-z0-9][-a-z0-9]*)?[a-z0-9]$`（`pkg/clustermesh/types/types.go`）。クラスターごとに一意にする。IDが0以外の場合、`default`は使えません |
| `cluster.id` | デフォルトでは1～255。0は未設定を表し、予約済みです。`maxConnectedClusters: 511`の場合は511まで拡張。**ENIモードとaws-cni chaining**: `extraConfig.allow-unsafe-policy-skb-usage=true`を設定しない限り、chartは128～255（`maxConnectedClusters: 511`の場合は384～511）のIDを拒否します（`templates/validate.yaml:160-168`、cilium/cilium#21330）。EKSのENIモードでは128未満を使用してください |
| `clustermesh.maxConnectedClusters` | `255`（デフォルト）または`511`。すべてのクラスターで同じ値にし、インストール時に設定 |

トレードオフ: cluster IDは数値identityのビットを使用します。255クラスターの場合、クラスター内identityの最大数は65535です。511クラスターでは32767に減ります。稼働中のクラスターで`maxConnectedClusters`を変更すると、接続が中断したりポリシー判定を誤ったりする可能性があります。`values.yaml`の`cluster.id`コメントは現在も1～255と記載されており、511の場合には古い情報です。稼働中にクラスター名やIDを変える場合、identityにcluster IDが埋め込まれているため、すべてのワークロードを再起動する必要があります。

### 10.3 TLSとauthMode

| 値 | 意味 |
|---|---|
| `clustermesh.apiserver.tls.auto.method` | `helm`（証明書は`helm upgrade`時のみ更新されるため、少なくとも年1回アップグレード）、`cronJob`（デフォルトスケジュール`0 0 1 */4 *`、4か月ごと）、`certmanager` |
| `tls.auto.certValidityDuration` | `365`日 |
| 共有CA | すべてのクラスターで同じCAを使う。Cluster Mesh有効化前に`cilium-ca` Secretを他クラスターへコピーするか、`tls.caBundle`を設定 |
| ユーザー指定証明書 | Secretは`clustermesh-apiserver-{server,admin,remote,local}-cert`。CN: serverは`clustermesh-apiserver.<ns>.svc`（SANは`*.mesh.cilium.io`、`127.0.0.1`、`::1`、追加DNS名）、adminは`admin-<cluster>`、localは`local-<cluster>`、remoteは`remote`（1.20）または`remote-<cluster-name>`（`cluster`モード） |

`authMode`は、各クラスターがリモートclustermesh-apiserverに接続する際に使うetcdユーザーを制御します。

| authMode | 動作 | デフォルトのバージョン |
|---|---|---|
| `legacy` | すべてのクラスターがユーザー`remote`を使う | 1.17、1.18（`values.yaml`: v1.17.18の3416行、v1.18.14の3634行） |
| `migration` | クラスターごとのユーザーを作成するが、認証には引き続き`remote`を使う。停止せず`legacy`から`cluster`へ移行するために必要 | 1.19、1.20 |
| `cluster` | 各クラスターが`remote-<cluster-name>`として認証。同じCAを共有する場合に意味がある | **[1.21プレリリース]** |
| `cluster-strict` | **[1.21プレリリース]** 共有`remote`ユーザーなしで`cluster`と同様に動作。すべてのクラスターが`cluster`を使ってから有効化 | - |

1.21での対応: `clustermesh.useAPIServer=true`かつ`tls.auto.enabled=false`の場合、remote証明書をCN `remote-<cluster-name>`で再発行するか、`authMode`を`migration`または`legacy`に戻します。自動証明書を使っていれば移行は透過的に行われる見込みです。`clustermesh.config.enabled=false`の場合は、`clustermesh-remote-users` ConfigMapを自分で作成する必要があります（1.19の注意点）。証明書の有効期間の変更: 1.19で生成方式を改訂し、CronJobをHelm hookではなくしました。1.20ではデフォルトの有効期間は1年で、4か月ごとに再生成され、CAの有効期間がleaf以上であることを検証します。また1.20で`clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}`キーは`clustermesh.apiserver.tls.auto.server.*`へ移動しました。

### 10.4 Helmの設定

クラスターごとのvalues（upstream設定ガイドと同じ形式。internal LBのannotationはAWS Load Balancer Controller標準のscheme annotationです。chartのコメントにも記載があるかは確認していません）:

```yaml
# cluster1.yaml
cluster:
  name: cluster1
  id: 1
clustermesh:
  useAPIServer: true
  config:
    enabled: true
  apiserver:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    tls:
      auto:
        enabled: true
        method: cronJob
        server:
          extraDnsNames:
            - cluster1.example.com
```

```yaml
# clusters.yaml  (shared; the local cluster entry is ignored by each cluster)
clustermesh:
  config:
    clusters:
      cluster1:
        address: cluster1.example.com
        port: 2379
      cluster2:
        address: cluster2.example.com
        port: 2379
```

先にCAをコピーし、インストール済みと同じchartバージョンで適用してください（upstreamガイドと同様に、この場合は`--reuse-values`を使えます）。

```bash
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER1 --reuse-values -f clusters.yaml -f cluster1.yaml

kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | \
  kubectl --context $CLUSTER2 create -f -

helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER2 --reuse-values -f clusters.yaml -f cluster2.yaml
```

Service公開: `clustermesh.apiserver.service.type`のデフォルトは`NodePort`（`nodePort: 32379`）です。upstreamは安定したアドレスを得るため`LoadBalancer`を推奨しています。`NodePort`では安定したnode IPが必要です。`ClusterIP`の場合はClusterIP間をクラスター間でルーティング可能にします。AWSでは`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`（およびpeer VPC CIDRに限定した`loadBalancerSourceRanges`）を必ず使うか、peering／TGW経由でNodePort／ClusterIPを使います。このコントロールプレーンをinternet-facing LBで公開すると、このリポジトリのポリシーに違反し、meshの信頼ドメインを露出します。peerクラスターのnode security groupまたはプライベートCIDRからのみTCP 2379を許可するsecurity groupも併用してください。

部分的なmeshを構成する場合は、各クラスターの`clusters` mapに接続対象のクラスターだけを指定します。クラスターごとの静的な`ips`にも対応しています。**[1.21プレリリース]では**、静的IPを変更してもPodは再起動しなくなり、`clustermesh.apiserver.service.port`も設定可能です。

CLIでの代替方法（Helmのラッパー。ラボで便利）:

```bash
cilium install --set cluster.name=$CLUSTER1 --set cluster.id=1 --context $CLUSTER1
cilium install --set cluster.name=$CLUSTER2 --set cluster.id=2 --context $CLUSTER2
cilium clustermesh enable --context $CLUSTER1
cilium clustermesh enable --context $CLUSTER2
cilium clustermesh connect --context $CLUSTER1 --destination-context $CLUSTER2   # one direction is enough
cilium clustermesh status --context $CLUSTER1 --wait
cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2
```

### 10.5 namespace: `defaultGlobalNamespace`

`clustermesh.defaultGlobalNamespace`（デフォルト`true`。1.20.2 chartにはありますが、1.19.8 chartにはありません）は、namespace内のCiliumEndpoints、CiliumIdentities、Serviceをエクスポートするか制御します。`clustermesh.cilium.io/global: "true"`または`"false"`をnamespaceにannotation付与して上書きできます。クラスター間接続とポリシーには、送信元と送信先の両namespaceをglobalにする必要があります。Global Serviceはglobal namespace内に置き、Service annotationも付与してください。デフォルトを`false`にすると、クラスター間で同期する状態を減らし、スケーラビリティを高められます。

### 10.6 データの古さ: `cacheTTL`

`clustermesh.cacheTTL`のデフォルトは`"0s"`です。接続が切れたリモートクラスターのキャッシュデータは失効しません。接続が指定した時間内（例: `"15m"`）に復旧しなければ古いリモートデータを破棄するよう、期間を設定してください。

## 11. Global Service、アフィニティ、EndpointSlice同期

Global Serviceは、各クラスターで同じService名とnamespaceを使い、`service.cilium.io/global: "true"` annotationを付与します。すべてのクラスターのbackendが統合されます。

| Annotation | 効果 |
|---|---|
| `service.cilium.io/global: "true"` | Serviceをglobalにする。いずれかのクラスターで省略またはfalseにすると、そのクラスターのServiceはローカルにとどまる |
| `service.cilium.io/shared: "false"` | このクラスターのbackendをエクスポートしないが、リモートbackendは利用。両側でglobalかつsharedが有効なら各クラスターからローカルとリモートの両方が見える。`shared: "false"`のクラスターは何もエクスポートしない |
| `service.cilium.io/affinity: none\|local\|remote` | `local`: 正常なローカルbackendを使い、すべて利用不可の場合のみリモートへ切り替え。`remote`は逆。`none`（デフォルト）は優先設定なし |
| `service.cilium.io/global-sync-endpoint-slices: "true"` | **ベータ**。他のcontrollerからも見えるようにリモートbackendのEndpointSliceも作成。Helmの`clustermesh.enableEndpointSliceSynchronization=true`とoperator再起動が必要。headless Global Serviceではデフォルトで有効 |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rebel-base
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/affinity: "local"
spec:
  type: ClusterIP
  ports:
  - port: 80
  selector:
    name: rebel-base
```

`cilium-dbg service list --clustermesh-affinity`でアフィニティを確認できます（優先backendには`(preferred)`が付きます）。制約: Global NodePortとhost-networkクライアントがリモートbackendへロードバランスするには、kube-proxy replacement（または`socketLB.enabled=true`かつ`socketLB.hostNamespaceOnly=true`）が必要です。Cilium ingress controllerはEndpointSlice同期なしでmesh内で動作しますが、他のingress controllerでは同期が必要な場合があります。1.19で追加されたメトリクスは`cilium_agent_clustermesh_remote_cluster_endpoints`です。

## 12. MCS-API（マルチクラスターサービス）

MCS-APIはKubernetes SIG-MulticlusterのAPIです。`ServiceExport`でServiceを公開し、各クラスターにDNS名`<svc>.<ns>.svc.clusterset.local`を持つ`ServiceImport`が作成されます。CiliumはGlobal Serviceの仕組みを再利用する`derived-<hash>`という派生Serviceとしてimportを実装しているため、2つの方式は併用できます。

| 項目 | 値 |
|---|---|
| 成熟度 | 1.19ではベータ（CRDは`multicluster.x-k8s.io/v1alpha1`）。1.20で安定版（`v1beta1`。`v1alpha1`も引き続きサポート） |
| 有効化 | `clustermesh.mcsapi.enabled=true`（削除された`clustermesh.enableMCSAPISupport`を置き換え） |
| CRD | chartがインストール（`clustermesh.mcsapi.installCRDs`、デフォルトtrue） |
| CoreDNS | `clustermesh.mcsapi.corednsAutoConfigure.enabled`を使用（CoreDNS >= 1.12.2が必要。Kubernetes >= 1.35のデフォルト）。手動設定: `serviceimports`のlist／watch権限を持つClusterRole `coredns-mcsapi`と、CoreDNSの`multicluster clusterset.local` plugin |
| Namespace | Serviceのnamespaceがすべてのクラスターに存在すること |

```yaml
apiVersion: multicluster.x-k8s.io/v1beta1
kind: ServiceExport
metadata:
  name: rebel-base
spec:
  exportedLabels:
    app.kubernetes.io/name: rebel-base
  exportedAnnotations:
    service.cilium.io/affinity: local
```

export間で調整されるプロパティ: SessionAffinity、Ports（union）、Type（ClusterSetIPまたはHeadless）、InternalTrafficPolicy、TrafficDistribution、label／annotation。競合時、Ciliumは`ServiceExport`のstatusに競合conditionを設定し、作成日時の古い順に解決します。この解決に頼らず、競合を修正してください。クラスターごとに別のDNS名を使う方法には対応していません。`mysvc-eu`と`mysvc-us`を個別にexportしてください。StatefulSet Podのhostnameは`<hostname>.<cluster>.<svc>.<ns>.svc.clusterset.local`として解決されます。Gateway APIでは`ServiceImport`を`backendRef`として使用できます。**[1.21プレリリース]では**、prefix削除後の名前が40文字を超えるミラーEndpointSliceは、アップグレード中に再作成され短時間の中断が起きる場合があります。

## 13. クラスター間ポリシー

- **デフォルトのスコープ（1.19以降）**: selectorはローカルクラスターのendpointのみに一致します（`policy-default-local-cluster`、Helmの`clustermesh.policyDefaultLocalCluster: true`）。1.18以前のデフォルトは全クラスターでした。1.18からアップグレードする前に`cilium clustermesh inspect-policy-default-local-cluster --all-namespaces`（または`-p <namespace>`）で監査してください。以前の注記ではこのコマンドのCLI不具合が1.21 pre.3ツリーで修正されたとしていましたが、未検証です。使用するCLIバージョンで出力を確認してください。
- **リモートクラスターを選択**するには、ラベル`io.cilium.k8s.policy.cluster`を使います。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cross-cluster
spec:
  endpointSelector:
    matchLabels:
      name: x-wing
  egress:
  - toEndpoints:
    - matchLabels:
        name: rebel-base
        io.cilium.k8s.policy.cluster: cluster2
```

任意のクラスターを選ぶには、代わりに`matchExpressions: [{key: io.cilium.k8s.policy.cluster, operator: Exists}]`を使います。

- **エンティティ**: `cluster`は、ローカルクラスター限定の設定（1.18のオプション）がない限り、mesh内のリモートノードを含みます。1.20では`cluster-mesh`が追加され、mesh内のすべてのクラスターのendpointに加えて`cluster`の対象も含みます。
- ポリシーは複製されません。各クラスターで個別に適用してください。
- 相互認証（SPIRE）はCluster Meshと併用できず、1.21プレリリースでは完全に削除されます。このリポジトリのservice-meshノートによると、ztunnelもCluster Meshと併用できません。[mTLS、暗号化、ID](12-mtls-encryption-identity.md)を参照してください。
- Cluster Meshと併用する場合、host firewallには制約があります（`host.rst`）。データプレーン暗号化はコントロールプレーンで使うmTLSとは別です。WireGuardまたはIPsecをすべてのクラスターで同じように設定し、UDP 51871をクラスター間で許可してください。Cluster Meshと暗号化を組み合わせた場合の正確な注意点は、今回再確認していません。

## 14. EKS上のCluster Mesh

upstreamの`eks-clustermesh-prep.rst`では、`eksctl`、CIDRが重複しない2つのVPC（例: `10.0.0.0/16`と`10.1.0.0/16`。`172.17.0.0/16`は避ける）、VPC peering、同一VPCおよびpeerからの通信を許可するsecurity groupを使います。そのガイドはinternet gatewayを備えたpublic subnetも作成します。このリポジトリでは、次のように適用してください。

- ノードにはprivate subnetのみを使用し、public IPやEIPを割り当てないでください。
- VPCをpeeringする（またはTransit Gatewayを使う）とともに、private route tableにpeer CIDRへのrouteを追加します。
- security group ruleでは両クラスターのnode security group（またはprivate CIDR）を参照します。`0.0.0.0/0`や`::/0`は使わないでください。
- clustermesh-apiserverはinternal NLB（`aws-load-balancer-scheme: internal`）で公開するか、peering経由のNodePortを使います。`loadBalancerSourceRanges`はpeer VPC CIDRに制限します。
- ENIモードではPod IPをVPC内でルーティングできるため、ネイティブルーティングで必要なのは`ipv4NativeRoutingCIDR`に両VPCのPod rangeを含めることだけです。overlayモードではノード間（UDP 8472）の到達性だけが必要です。
- 各EKSクラスターに別々の`cluster.name`／`cluster.id`を設定し、`maxConnectedClusters`は同じ値にします。ENIモードでは`cluster.id`を128未満にしてください。`extraConfig.allow-unsafe-policy-skb-usage=true`を設定しない限り、chartは128～255（`maxConnectedClusters: 511`では384～511）を拒否します（`validate.yaml:160-168`）。

## 15. ラボ

> このレビューでは実クラスターでラボを実行していません。upstreamのソースとドキュメントに照らして確認しました。使い捨てクラスターでのみ実行してください。

### ラボ1: 2クラスターのCluster Mesh

前提条件: ノード間通信可能な使い捨てクラスターが2つ（同じDocker host上で`networking.podSubnet`／`serviceSubnet`を変え、`disableDefaultCNI: true`にしたkindクラスター2つ、またはpeeringしたVPC内のEKSクラスター2つ）、Helm 3、Cilium CLI 0.20.1、`$CLUSTER1`／`$CLUSTER2` context。

1. 各クラスターにCilium 1.20.2をインストールします。`cluster.name`、`cluster.id`をそれぞれ異なる値にし、Pod CIDRが重複しないようにします（cluster-poolのリストも異なる値にします）。
2. CAをコピーします: `kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | kubectl --context $CLUSTER2 create -f -`。
3. 10.4節のvaluesファイルを適用します。ロードバランサーがないkindでは`service.type: NodePort`を使い、`clustermesh.config.clusters.<name>.ips`にnode IPをport `32379`とともに指定します。
4. `cilium clustermesh status --context $CLUSTER1 --wait`を実行し、続けて`cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2`を実行します。

確認: `cilium clustermesh status`でclustermesh-apiserverがready、リモートクラスターが接続済みと表示されること。`kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg status --all-clusters`で、リモートクラスターがcluster IDとともにreadyと表示され、`synchronization status`がすべてtrueであること。`cilium-dbg node list`にリモートノードが含まれること。

後片付け: 両クラスターで`helm uninstall cilium -n kube-system`を実行するか、使い捨てクラスターを削除します。接続に失敗した場合のロールバック: `clusters.yaml`から該当entryを削除し、同じchartバージョンで再度`helm upgrade`します。

### ラボ2: Global Service、`shared`、アフィニティ

前提条件: ラボ1を完了していること。

1. 両クラスターで同じnamespaceを作成し、DeploymentとService `rebel-base`を配置します。`service.cilium.io/global: "true"`を設定し、Podは自身のクラスター名を応答として返すようにします。
2. クラスター1のclient Podからcurlを繰り返し、両クラスターから応答が返ることを確認します。
3. クラスター1のServiceに`service.cilium.io/affinity=local`を付けて再試行します。クラスター1からのみ応答されることを確認します。ローカルbackendを0にスケールし、クラスター2へfailoverすることを確認します。
4. クラスター2で`service.cilium.io/shared: "false"`を設定し、クラスター1からクラスター2のbackendが見えなくなる一方、クラスター2からクラスター1には引き続き到達できることを確認します。

確認: agent内の`cilium-dbg service list --clustermesh-affinity`に優先backendが表示されること。`cilium-dbg bpf lb list`にリモートbackendアドレスが表示されること。

後片付け: 両クラスターでnamespaceを削除します。

### ラボ3: MCS-API

前提条件: ラボ1を完了し、`clustermesh.mcsapi.enabled=true`および`corednsAutoConfigure.enabled=true`を設定していること（手動設定の場合はCoreDNSを再起動）。

1. 両クラスターでnamespaceとServiceを作成し、両方で同名の`ServiceExport`を作成します。
2. Podから`rebel-base.<namespace>.svc.clusterset.local`を名前解決し、curlします。
3. exportするportをクラスター間で変え、`kubectl get serviceexport -o yaml`で競合conditionを確認します。

確認: 両クラスターに`ServiceImport`があり、`derived-<hash>`という派生Serviceが作成されること。DNS名が解決されること。

後片付け: ServiceExport、Service、namespaceを削除します。

### ラボ4: ドリフト検出を使ったアップグレード訓練

前提条件: valuesファイルからインストールした1.19.8の使い捨てクラスターと、Prometheus metrics endpoint（または`cilium-dbg metrics list`）へ到達できること。

1. valuesを保存します: `helm get values cilium -n kube-system -o yaml > old-values.yaml`。
2. 1.20.2向けpre-flight chartを実行してチェックの成功を確認し、その後削除します。
3. `--version 1.20.2 -f old-values.yaml --set upgradeCompatibility=1.19`を指定してupgradeします。
4. agent再起動が必要なConfigMapキーを`cilium config set --restart=false <key> <value>`で変更し、ドリフトメトリクスを読み取ります: `kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg metrics list | grep drift_checker_config_delta`。
5. ロールバックします: `helm history cilium -n kube-system`でrevisionを確認してから、`helm rollback cilium <REVISION> -n kube-system`を実行します。

確認: 手順4の後に`cilium_drift_checker_config_delta`が0以外となり、agent再起動後に0へ戻ること。アップグレード後とロールバック後の両方で`cilium status`が正常であること。

後片付け: 使い捨てクラスターを削除します。注意: このラボはロールバック手順を試します。1.20固有の機能を使ったクラスターでは実行しないでください。

### ラボ5: ノードごとのCiliumNodeConfig上書き

前提条件: 2ノード以上がある任意のCilium 1.20.2クラスター。

1. 1つのノードにラベルを付けます: `kubectl label node <node> io.cilium.test-override=true`。
2. `kube-system`に、そのラベルをselectorに指定した`CiliumNodeConfig`を適用します。`debug: "true"`など影響の小さい`defaults`キーを使います。
3. ラベル付きノードとラベルなしノードの両方でagent Podを削除します。

確認: 再作成されたラベル付きノードのagentでは有効設定（`cilium-dbg config`）にoverrideが現れ、ラベルなしノードでは現れないこと。

後片付け: CiliumNodeConfigを削除し、ラベルを外してagent Podをもう一度再作成します。

## バージョン差分

| 領域 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|
| 最小カーネル | 5.10 | 5.10 | 5.10 | 5.10（LLVM 21.1） |
| Gateway API CRD | 1.3.0 | 1.4 | 1.6.1 | 1.6.1 |
| Helm OCI chart | なし | あり | あり（推奨） | あり |
| MCS-API | ベータ | ベータ（`v1alpha1`、CRD自動インストール） | 安定版（`v1beta1`） | `v1beta1` |
| Cluster Meshポリシーのデフォルト | 全クラスター | ローカルのみ | ローカルのみ、`cluster-mesh` entity | ローカルのみ |
| authModeデフォルト | `legacy` | `migration` | `migration` | `cluster`（および`cluster-strict`） |
| KVStoreMesh | `enabled`が非推奨 | デフォルトで有効 | デフォルトで有効 | 常時有効 |
| 相互認証 | あり | デフォルトで無効 | 非推奨 | 削除 |
| Kafka L7／proxylib | 非推奨 | Kafka非推奨 | 削除 | 削除 |
| BGPv1 | 非推奨 | 削除 | - | - |
| マルチプールIPAM | ベータ | 安定版 | cluster-poolから移行可能 | Azure IPAMがmulti-poolへ移行 |
| Double Write | ベータ | ベータ | ベータ | ベータ、`migrate-identity`は非推奨 |
| configDriftDetection | バックポート | バックポート | 標準搭載 | 同じ |
| ENI masqueradeのデフォルト | IPv4をfalseに変更 | false | false | IPv6 masqueradeは無効 |

## トラブルシューティング

| 症状 | 確認項目 |
|---|---|
| リモートクラスターが接続しない | `cilium clustermesh status --wait`。`kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg troubleshoot clustermesh [cluster...]`でDNS、接続性、TLS、etcd認可などを確認。KVStoreMesh使用時は`kubectl exec -n kube-system deploy/clustermesh-apiserver -c kvstoremesh -- clustermesh-apiserver kvstoremesh-dbg troubleshoot`も確認 |
| リモートごとの状態 | `cilium-dbg status --all-clusters`でnode、endpoint、identity、Service、MCS-API export、再接続、`has-quorum`、`cluster-id`、`kvstoremesh`、同期状態を確認。`... kvstoremesh-dbg status --verbose`も確認 |
| ログ | agent: `New remote cluster configuration`、`Connection to remote cluster established`、`Unable to establish etcd connection to remote cluster`。`kubectl logs -n kube-system deployment/clustermesh-apiserver -c apiserver`も確認 |
| TLSエラー | CAの違い（`cilium-ca`をコピー）、証明書期限切れ（`helm`方式では1年後）、`authMode`に合わないCNを確認。Secret `cilium-clustermesh`と`cilium-kvstoremesh`も確認 |
| `*.mesh.cilium.io`の名前解決 | hostAliasesで`cluster1.mesh.cilium.io`をLB IPに対応付け。KVStoreMeshなしではDaemonSet、KVStoreMeshありではclustermesh-apiserver Deploymentに設定 |
| ポート | security groupでTCP 2379を参照またはprivate CIDRによって許可する必要があります |
| クラスター間通信が拒否される | `cilium-dbg identity list`（ラベル`io.cilium.k8s.policy.cluster`）、`cilium-dbg bpf ipcache list`、`cilium-dbg service list`、`cilium-health status`を確認。1.19以降のローカルクラスター限定ポリシーと、両namespaceがglobalであることにも注意 |
| CIDR重複またはID重複 | `cilium-dbg node list`に重複したnode rangeが表示されます。修正するにはIPの再割り当てとワークロード再起動が必要 |
| 古いクラスターから1.20へのアップグレードが止まる | `CiliumNodeConfig v2alpha1` CRDの不具合を避けるため1.20.2以降を使用 |
| 設定変更が反映されない | `cilium_drift_checker_config_delta > 0`ならagentを再起動 |

## 検証範囲と参照資料

今回のレビューでは実クラスター上でラボを実行していません。以下のタグのupstreamソースとドキュメントで確認しました。確認できなかった事項は、断定せずにここへ記載しています。

- Cilium 1.21でBPF masqueradingがデフォルト有効になるか。pre.2のリリースノートには有効化するとありますが、pre.3ツリーのdaemonデフォルトは`false`、chartの`bpf.masquerade`デフォルトもfalseで、`upgrade-next.inc`の「Changed Options」節は空です。
- WireGuard／IPsecとCluster Meshの正確な注意点は再確認していません。
- EKSのchaining modeの制約、EKS管理下のkube-proxy add-onを削除する正確なコマンド、Amazon Linux 2023が名前付きでサポート対象かどうか。
- 1.17.9-0と1.18.3-0より新しいAWS保守Ciliumビルドのバージョン。
- `bpf.tproxy`とENI IPv6の成熟度。引用した「ベータ」以上の確認はしていません。
- 1.19.0のリリース日、1.17の正確なKubernetesテストマトリクス。
- MCS-APIの「安定版」という表記はv1.20.0のリリース本文に基づきます。ソースで確認したのはベータバナーの削除と`v1beta1` CRDです。
- Double Writeのメトリクス名はupstreamのupgradeページとコードが異なります（8.3節）。v1.20.2のコードに従いました。
- chartの`kubeVersion`デフォルトはチャート制約であり、テスト済みKubernetesバージョン範囲ではありません。

参照資料:

- [Cilium v1.20.2ドキュメント: operations/upgrade.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade.rst)
- [v1.20.2アップグレードノート](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)
- [v1.20.2 Cluster Meshドキュメント](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/clustermesh)
- [v1.20.2 Cluster Meshトラブルシューティング](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/troubleshooting_clustermesh.rst)
- [v1.20.2 HelmインストールとEKS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/k8s-install-helm.rst)、[requirements-eks.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [v1.20.2 ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [v1.20.2システム要件](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [v1.20.2ノード単位設定](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/per-node-config.rst)、[ConfigMapドリフト検出](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/configmap-drift-detection.rst)
- [v1.20.2 Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- [v1.20.2 Double Writeメトリクスのコード](https://github.com/cilium/cilium/blob/v1.20.2/operator/doublewrite/metrics.go)
- [v1.21.0-pre.3アップグレードノート](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc)、[values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- リリースノート: [v1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2)、[v1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0)、[v1.19.0](https://github.com/cilium/cilium/releases/tag/v1.19.0)、[v1.18.0](https://github.com/cilium/cilium/releases/tag/v1.18.0)、[v1.17.0](https://github.com/cilium/cilium/releases/tag/v1.17.0)、[v1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3)
- AWS: 代替CNIプラグイン、Auto Mode networking、Hybrid Nodes CNIに関するEKS User Guideページ

## クイズ

[Part 13のクイズ](../../quizzes/networking/cilium/13-clustermesh-install-upgrade-quiz.md)で理解度を確認してください。
