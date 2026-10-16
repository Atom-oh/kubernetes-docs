# Cilium 詳説: Cloud Native Networking の未来

## 概要とレビュー済みベースライン

このセクションでは、Cilium のネットワーキング、ポリシー、オブザーバビリティを扱います。例は **Cilium/Helm chart 1.20.2**、Cilium CLI **0.20.1**、Hubble CLI **1.20.2** でレビューしています。Cilium 1.20 の Kubernetes 互換性ページでは、テスト済みとして **1.33–1.36** が示されています。upstream の 1.37 リリースは、このマトリックスを自動的に拡張するものではありません。サポートされるホストは、カーネル **5.10+** を備えた AMD64/AArch64 Linux、または RHEL 8.10 のバックポート済み 4.18 カーネルなど、文書化された同等のディストリビューションです。個々の機能には追加要件があります。

> **最終更新**: October 15, 2026

### 過去のリリースノート

以下の日付は UTC の GitHub 公開日であり、現在のインストール固定バージョンではなく、該当リリースを説明しています。機能のバックポートはリリースラインごとに異なります。

| 日付 | リリース | 検証済みのハイライト |
| --- | --- | --- |
| July 14, 2026 | [1.20.0-rc.0](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.0) | 最初の 1.20 リリース候補 |
| July 16, 2026 | [1.19.6](https://github.com/cilium/cilium/releases/tag/v1.19.6), [1.18.12](https://github.com/cilium/cilium/releases/tag/v1.18.12), [1.17.18](https://github.com/cilium/cilium/releases/tag/v1.17.18) | Gateway アクセスログ設定は 1.19.6/1.18.12 向けに記載されています。ここで引用する restart-policy および ClusterMesh affinity の修正は、3 リリースすべてではなく 1.19.6 に記載されています |
| July 21, 2026 | [1.20.0-rc.1](https://github.com/cilium/cilium/releases/tag/v1.20.0-rc.1) | 2 番目の 1.20 リリース候補 |
| July 29, 2026 | [1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0) | GA リリース。以下の選択した変更を含みます |
| August 3, 2026 | [1.21.0-pre.0](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.0) | 次サイクルのプレリリースであり、このガイドのデプロイメントベースラインではありません |
| August 18, 2026 | [1.20.1](https://github.com/cilium/cilium/releases/tag/v1.20.1) | restart/CIDR-policy 処理を含む ClusterMesh のドキュメントおよびバグ修正 |
| August 18, 2026 | [1.19.7](https://github.com/cilium/cilium/releases/tag/v1.19.7) | ENI インターフェイスのタイミング、Service/LB、その他の修正を含みます |
| August 18, 2026 | [1.18.13](https://github.com/cilium/cilium/releases/tag/v1.18.13) | VRRP/IGMP host-firewall サポートおよび関連修正 |
| September 9, 2026 | [1.21.0-pre.2](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.2) | プレリリース。**1.21.0-pre.1 は公開されなかった**ため、その changelog は pre.0 から pre.2 を対象としています |
| September 16, 2026 | [1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2) | 本ガイドの現在の安定ベースライン。ENI prefix-delegation と secondary-VPC-CIDR の修正、ClusterMesh の修正、および v1.15 以前で作成された cluster のアップグレードに対する修正（`CiliumNodeConfig v2alpha1` CRD version） |
| September 16, 2026 | [1.19.8](https://github.com/cilium/cilium/releases/tag/v1.19.8), [1.18.14](https://github.com/cilium/cilium/releases/tag/v1.18.14) | 以前のサポート対象ラインのパッチリリース |
| October 2, 2026 | [1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3) | 最新の 1.21 プレリリース。**1.21 はプレリリースのみ（GA はまだありません）**であり、本ガイドで 1.21 と記した項目は変更される可能性があります |

1.20.0 の発表では、**2,660+ 件の新規コミット**と、**1,100+ 人のコントリビューターから成るコミュニティ**が報告されています。後者はこのリリースの著者数ではなく、コミュニティの規模です。主な内容は次のとおりです。

- Gateway API **1.6.1**、TCPRoute/UDPRoute、BackendTLSPolicy、ListenerSets、ExternalAuth、CORS のサポート。ただし各機能の設定と API の成熟度が条件となります。
- Datapath plugins とオプトインの `bpf.datapathMode=auto`。発表されたデフォルトは引き続き veth です。Dual-stack cluster では IPv6 egress gateway address を設定できます。
- **Beta** の IPv6 ENI IPAM、および cluster を再構築せずに cluster-pool から multi-pool へ移行する機能。インプレース移行では中断がないことは保証されません。
- Traffic distribution hints、weighted Maglev backends、安定した MCS 統合、Kubernetes ClusterNetworkPolicy サポート、および **beta** の ztunnel ベース workload identity。
- `cilium-cni` binary のおよそ **77 MB から 16 MB** への削減報告。ADS/Delta xDS の改善は 1.20 の発表に含まれます。これを 1.18.13 パッチノートの内容として扱わないでください。これらは upstream リリースの主張であり、本監査で再測定したものではありません。

Mutual Authentication（**1.20 で非推奨**、1.21 プレリリースで削除）、削除または置換された Envoy Go extensions、Kafka-aware policies、旧 CiliumNodeConfig API、libnetwork 統合、カスタム CNI 設定の変更については、[1.20 upgrade notes](https://docs.cilium.io/en/v1.20/operations/upgrade/#upgrade-notes) を確認してください。

### NetworkPolicy セキュリティアドバイザリ

[GHSA-fm8w-2m5w-9j7r / CVE-2026-56743](https://github.com/cilium/cilium/security/advisories/GHSA-fm8w-2m5w-9j7r) のプロジェクトアドバイザリ公開日は **July 6, 2026** です。プロジェクト API と GitHub global advisory API は異なる日付を公開しており、後者は September 3 を記録しています。このリリース時系列ではプロジェクト開示日を使用してください。global record の日付は後続の修正リリースではありません。この問題は、アドバイザリの custom-cluster-name 条件下で **1.19.0–1.19.4** に影響します。`ipBlock` のみを含む標準 Kubernetes NetworkPolicy peer が、選択された Pod の namespace 内の workload からの ingress を意図せず許可する可能性があります。**1.19.5** でこの問題は修正されています。デプロイメントには適切な現在のパッチ済みリリースを使用してください。アドバイザリによると、CiliumNetworkPolicy/ClusterwideNetworkPolicy と 1.19.0 未満のリリースは、この特定のバグの影響を受けません。

## はじめに

Cilium は、サポート対象の Linux Kubernetes 環境向けにネットワーキング、セキュリティ、オブザーバビリティを提供します。Routing、IPAM、暗号化、Service 処理は個別の選択肢です。eBPF を選択しただけでは、すべての機能や性能保証が成立するわけではありません。旧 Docker libnetwork 統合は 1.20 で削除されたため、Docker/Mesos を代替可能な現在のインストール対象としてここに挙げるべきではありません。

### eBPF と主要機能

カーネルは eBPF プログラムをロード前に検証し、サポートされる hook で実行するために JIT コンパイルできます。これにより、カスタムカーネルモジュールなしでパケット処理とオブザーバビリティが可能になります。ただし verifier はアプリケーションやポリシーの正しさを証明するものではありません。実際の throughput、latency、memory は、プログラム、platform、workload に依存します。

Cilium は L3/L4 policy、Envoy/DNS proxy 統合による L7 policy、オプションの WireGuard/IPsec、Service load balancing、Hubble flow visibility、ClusterMesh、BGP advertisement を提供します。XDP acceleration はオプションで、device/configuration に依存します。L7 機能では node ごとの Envoy を使用することがあります。ztunnel による workload identity には別の beta 設定があります。agent をインストールしただけでは、すべての mesh、encryption、multi-cluster 動作は有効になりません。

### 他の Networking Project との比較

| Project | Connectivity / IPAM | Policy と関連機能 |
| --- | --- | --- |
| Cilium | Native または overlay routing、cloud ENI を含む IPAM modes | eBPF dataplane、Cilium/Kubernetes policies、L7 integration、Hubble、オプションの encryption |
| Calico | Calico または external IPAM による Native/IPIP/VXLAN profiles | Linux Iptables/Nftables/BPF、サポート対象の Windows HNS、OSS WireGuard、staged policy、個別の L7 integration |
| Flannel | VXLAN/host-gw/WireGuard など、選択された backends による Pod connectivity | routing daemon は NetworkPolicy を強制しません。chart では `netpol.enabled` を使用して SIGs network-policy controller をデプロイでき、別の policy implementation と組み合わせることもできます |
| AWS VPC CNI | VPC ENI address allocation/networking | サポート対象 EC2 Linux nodes 上の Native network policy と、個別の SG-for-Pods 機能。EKS Auto Mode は異なる managed implementation です |

routing mode は packet-processing implementation と同じカテゴリではありません。Calico は iptables/IPVS に限定されず、Flannel は暗号化された backend を使用でき、AWS policy は security groups と同義ではありません。Service mesh はオプションのレイヤーであり、cross-cluster VPC connectivity は Transit Gateway に限定されません。普遍的な性能ランキングではなく、測定した workload と明示的な support matrix を使用してください。

## アーキテクチャ

**Kubernetes API server** は Kubernetes/Cilium resources を保存します。Cilium agents は関連する state を監視し、各 node の dataplane をプログラムします。Cilium Operator は、選択された IPAM や identity/controller 作業など、cluster レベルの責務を処理します。この基本アーキテクチャには、個別の必須 cluster-wide “Cilium API Server” deployment はありません。agents には local APIs があり、オプションの ClusterMesh API server は別の目的を果たします。

| Component | 役割 |
| --- | --- |
| Cilium Agent | Node-local endpoint、policy、routing/Service state、eBPF management |
| Cilium Operator | Cluster-level reconciliation と mode 依存の allocation/controller 作業 |
| Envoy | 有効な L7 policy、ingress/Gateway、および関連機能のための Userspace proxy |
| Hubble server | agent と統合された Node-local flow API |
| Hubble Relay / UI | flow stream の集約 / service maps と flows の表示 |
| Prometheus metrics endpoints | 個別の statistics collection。Relay/UI は metrics scraping pipeline ではありません |
| cilium / cilium-dbg / hubble | それぞれ Cluster management CLI / agent diagnostics / flow client |

### Networking と Packet Paths

Native routing には到達可能な underlay が必要です。tunneling には VXLAN または Geneve を使用します。AWS ENI と Azure IPAM は allocation/integration の選択肢であり、それぞれ独自の platform requirements があります。Cilium の BGP Control Plane は router に reachability を advertisement しますが、**datapath をプログラムせず、internal cluster routing も提供しません**。

普遍的な XDP→TC→Pod の sequence はありません。Socket load balancing は packet が存在する前に動作でき、TC/netkit hooks は datapath に依存し、オプションの XDP は選択された traffic を加速し、L7 traffic は Envoy を通過することがあります。return traffic も NAT、conntrack、DSR の選択に依存します。選択した profile については networking および eBPF の章を参照してください。

## Amazon EKS との統合

何かをインストールする前に、実際の networking と compute profile を選択してください。example addon name/version の `cilium` / `v1.17.0-eksbuild.1` は検証済みの AWS distribution ではなく、ここでの installation command でもありません。packaged vendor add-on を検討する場合は、Region の実際の add-on catalog、publisher、license、supported compute types を確認してください。

| EKS profile | 検証事項 |
| --- | --- |
| Ordinary EC2 nodes、Cilium ENI が VPC CNI を置換 | Upstream/partner-managed CNI。AWS がサポートする EC2 CNI は VPC CNI です。CNI ownership、IAM、addressing、routes、bootstrap、node migration を計画します |
| Ordinary EC2 nodes、AWS VPC CNI chaining | VPC CNI が interfaces/IPAM を所有し、その後に Cilium が dataplane を接続します。既存の Pods は再作成が必要で、L7/IPsec には文書化された制限があります |
| Hybrid Nodes | AWS の specialized CNI guide と AWS-maintained Cilium build matrix に従います。upstream 1.20.2 は自動的にサポート対象 AWS build になるわけではありません |
| Auto Mode | 代替 CNI/policy plugins はサポートされません。managed NodeClass/networking features を使用します |
| Fargate | 代替 CNI/DaemonSet installation はサポートされません |
| Windows | Cilium agent の要件は Linux です。この recipe を Windows workers に適用しないでください |

AWS の一般的な alternate-CNI ページと specialized Hybrid guide では Calico のサポートに関する表現が異なります。repository を移動する例はサポート終了を意味するものではありません。Hybrid Nodes では、正確な distribution、capability set、support owner を確認してください。Auto Mode では、node-local CoreDNS/system networking も本ガイドの通常の EC2 setup と異なります。混在する non-Auto nodes には、従来の DNS Deployment が引き続き必要です。

### Cilium ENI を使用する準備済み EC2 Cluster

これらは **準備済み IPv4 EC2 cluster 用の Cilium Helm values** であり、完全な cluster-creation または in-place migration recipe ではありません。使用前に次を行ってください。

1. サポート対象の EKS/Kubernetes version と Linux AMI を選択し、単一の CNI owner を確立します。近道として、既存 workload cluster から `aws-node` を削除しないでください。
2. Cilium が node を管理するまで workloads が待機するよう、node taints/scheduling を準備します。upstream EKS guidance では `node.cilium.io/agent-not-ready=true:NoExecute` を使用します。実際の node lifecycle における eviction と bootstrap の影響を評価してください。
3. subnet capacity、ENI quotas/security groups、node metadata access、operator に必要な EC2 permissions を準備します。以下の role ARN は、values file で作成される role ではなく、正しく信頼された **cilium-operator ServiceAccount** role の placeholder です。
4. この `kubeProxyReplacement: false` の例では、動作する kube-proxy と DNS を維持します。replacement mode では、別途 direct API/bootstrap-DNS requirements に従ってください。普遍的な 110 ではなく、実際の instance/IPAM capacity から max-Pods を選択します。

`cilium-eni-values.yaml` として保存し、role/interface の選択をレビュー済みの値に置き換えてください。

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
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml > cilium-eni-rendered.yaml

# After preparing the cluster and reviewing the rendered configuration:
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-eni-values.yaml
```

これらの設定は installation owner を通じて管理してください。数個の key だけを含む replacement `cilium-config` は、ほかの必須設定を削除する可能性があります。旧 `tunnel=disabled` value は `routingMode: native` に置き換えられます。ENI allocation/permissions と SNAT behavior には引き続き runtime validation が必要です。render の成功は、使用可能な EC2 networking の証明ではありません。

**IPv6 の適格性:** 1.20.2 の ENI IPAM reference は IPv6 を beta と説明していますが、EKS prerequisites ページでは依然として IPv4-only ENI integration と記載されています。このガイドでは IPv4 の例を維持し、どちらの記述も production EKS IPv6 compatibility の証明として扱うのではなく、このドキュメント上の不整合を記録します。別の IPv6 design を行う前に、現在の ENI/dual-stack subnet requirements を確認してください。

### VPC CNI Chaining の代替

upstream chaining guide では VPC CNI 1.11.2+ が必要で、以下の profile を文書化しています。

```yaml
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
kubeProxyReplacement: false
```

これは ENI-replacement values に重ねるものではなく、**異なる設定**として使用してください。VPC CNI が allocator のままです。歴史的な upstream DaemonSet を適用するのではなく、実際の managed add-on をその owner を通じて upgrade してください。同じ endpoints で競合する policy engines を避けてください。CNI chain が変更されても既存の Pods は Cilium に遡及して接続されません。計画的な rollout で再作成し、endpoint management を検証してください。chaining には文書化された L7 policy/IPsec の制限があるため、このページ後半のすべての例がその profile で動作すると想定しないでください。

### ClusterMesh

ClusterMesh には、一意の cluster identities、互換性のある versions、到達可能かつ非重複の Pod networks、認証済み API connectivity、適切な exposure model が必要です。LoadBalancer Service は cloud resources を作成する場合があり、意図的な network/security design を必要とします。2 つの public endpoints を作成するだけでは、clusters を安全に接続するには不十分です。選択した topology については、保守されている [ClusterMesh guide](13-clustermesh-install-upgrade.md) と advanced chapter に従ってください。

## インストールと設定

### Client Tools

workstation OS/architecture に適した公式 Cilium CLI 0.20.1 および Hubble CLI 1.20.2 assets を使用し、展開前に提供された checksums を検証してください。Linux ARM64 と AMD64 は異なります。macOS では対応する Darwin assets を使用します。CLI versions は Cilium agent/chart version とは別です。[検証済み CLI installation guidance](../../service-mesh/cilium-service-mesh/README.md) を参照してください。

```bash
cilium version --client
hubble version
```

### Non-Cloud Cluster-Pool の例

以下の**代替**は、kube-proxy と DNS がすでに動作している準備済みの通常 Linux cluster 向けです。例の `10.244.0.0/16` Pod range が cluster と互換性を持ち、Service、node、VPC、接続先 network ranges と重複しないことを確認してください。この pool configuration を ENI mode に使用しないでください。

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

`cilium-values.yaml` として保存し、固定した chart を render した後、準備済み cluster にのみインストールしてください。

```bash
helm template cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml > cilium-rendered.yaml
helm install cilium cilium/cilium --version 1.20.2 \
  --namespace kube-system -f cilium-values.yaml
cilium status --wait
```

既存 release では、その upgrade/GitOps process を使用し、owner が持つ values を維持して、version 固有の upgrade procedure に従ってください。繰り返し示される `cilium install` の例は、個別設定を変更するための一般的な方法ではありません。

| 選択 | 現在の設定と前提条件 |
| --- | --- |
| VXLAN/Geneve | `routingMode: tunnel` と `tunnelProtocol`。選択した encapsulation を許可し、path に対して MTU を設定します |
| Native routing | `routingMode: native`。underlay が Pod addresses を route する必要があります。`autoDirectNodeRoutes` には任意の multi-subnet routing ではなく、適切な direct connectivity が必要です |
| kube-proxy replacement | `kubeProxyReplacement: true` または `false` であり、legacy `strict` ではありません。replacement には到達可能な `k8sServiceHost`/`k8sServicePort` と文書化された bootstrap plan が必要です |
| WireGuard | kernel/platform と peer paths を確認した後に、サポートされる encryption mode を有効にしてください。あらゆる可能な traffic path を自動的に暗号化するわけではありません |
| IPsec | 文書化された key Secret、key distribution/rotation、互換性のある mode が必要です。Helm の enable flag のみでは不完全です |
| XDP/DSR/BBR | 個別の device/kernel/topology 依存の選択肢であり、普遍的な install preset ではありません |

## Network Policies

Kubernetes `networking.k8s.io/v1` NetworkPolicy と Cilium `cilium.io/v2` policies は異なる APIs です。複数の allow policies は組み合わせることができます。これらの例では、L4 allow が L7 restriction を暗黙に bypass しないよう、**個別に準備した test namespaces** を使用しています。結論を出す前に、実際の endpoints を選択するすべての policies を確認してください。

### L4 の例

`cilium-l4-demo` では、backend Pods を選択し、同一 namespace の frontend Pods から TCP 8080 上の ingress を許可します。

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

別の `cilium-l7-demo` では、backend Pods を選択し、その namespace の frontend Pods からの、指定した method/path に対する TCP 8080 上の plaintext HTTP を制限します。選択した CNI mode で L7 proxy support が利用可能である必要があります。暗号化された HTTP は、サポートされる termination configuration なしに自動で検査されることはありません。

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

同じ peers/port に対して一致する unrestricted L4 allow を追加しないでください。Cilium では、そのような allow によってより狭い L7 restrictions の効果がなくなることを文書化しています。L7 denial は packet drop ではなく HTTP 403 を返す場合があります。実際の endpoint identities を使用して、許可された GET requests と拒否された methods/paths をテストしてください。

### DNS/FQDN の例

`cilium-dns-demo` では、通常の CoreDNS Pods への DNS queries と、`api.example.com` に対して学習した addresses への TCP 443 を許可します。domain は例です。承認済みの destination に置き換えてください。広範な `*.amazonaws.com` wildcard は account/resource boundary ではないため、省略しています。

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

DNS wildcard は、選択した resolver への queries を許可するものであり、返されたすべての address への connections を許可するものではありません。ただし任意の DNS names を運ぶことはできます。必要に応じて DNS search suffixes を考慮し、query names を制限してください。NodeLocal DNS または別の resolver には、正しい destination selection が必要です。FQDN policy は DNS 由来の IP authorization であり、TLS hostname verification や HTTP URL authorization ではありません。shared IPs と application TLS/authentication は引き続き重要です。

## Hubble によるオブザーバビリティ

上記の cluster-pool values は Relay/UI と component metrics を有効にします。既存 installation では、意図する Hubble values を configuration owner を通じて適用してください。`cilium hubble enable --ui` はサポートされる convenience command ですが、`cilium hubble enable --metrics=...` はサポート対象の 0.20.1 CLI flag ではありません。代わりに Helm values の `hubble.metrics.enabled` を設定してください。legacy の `http` と `httpV2` handlers を同時に有効にしないでください。

一方の terminal で Relay port-forward を実行したままにします。

```bash
cilium hubble port-forward --port-forward 4245
```

Hubble CLI をインストールした別の terminal で実行します。

```bash
hubble observe --server 127.0.0.1:4245 --namespace cilium-l7-demo
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --from-label k8s:app=frontend --to-label k8s:app=backend
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
hubble observe --server 127.0.0.1:4245 --http-status 403
```

この local example はデフォルトの Relay server configuration を前提としています。TLS-enabled Relay には、対応する client trust/authentication が必要です。HTTP events には、traffic が設定済み L7 proxy を通過することが必要です。`DROPPED` は datapath verdict であり、失敗したすべての application request を意味するものではありません。UI の port-forward には `cilium hubble ui` を使用し、metrics 用の Prometheus target discovery は個別に設定してください。Hubble flow streaming 単体は distributed application tracing ではありません。

## テストと運用

connectivity/performance commands は test workloads を作成し、policy を変更したり、大量の traffic を生成したりすることがあります。レビュー済みの test namespace/environment と permissions を使用してください。この監査では cluster に対して実行していません。

```bash
cilium connectivity test --help
cilium connectivity perf --help
```

performance subcommand は `cilium connectivity perf` です。`connectivity test --test=performance` は test-name filter を指定するだけであり、performance runner ではありません。throughput/latency を比較する前に、software versions、topology、traffic、raw results を記録してください。

調査では、management CLI と **agent-side `cilium-dbg`** を区別してください。

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

`cilium endpoint list`、`cilium bpf maps list`、`cilium metrics list` は management CLI では等価な commands ではありません。`cilium sysdump` は diagnostic material を収集できます。結果として得られる infrastructure/log data を保護してください。Ready agent や scrape の成功は、application と negative policy tests の代わりにはなりません。

### 運用上の優先事項

- map preallocation、XDP、DSR、BBR、固定 device pattern を有効にする前に測定してください。これらは resources を消費するか packet paths を変更するため、機能固有の checks が必要です。
- DNS、API、identity、application dependencies を明示的に許可したうえで、選択した scope に default-deny を導入してください。established connections だけでなく、新しい Pods と upgrade transitions を確認してください。
- encryption、certificate/key rotation、policy enforcement、observability を個別の acceptance checks として扱ってください。使用可能な management/recovery path を維持してください。
- 現在の platform matrix とサポートされる upgrade path をレビューしてください。過去のリリース発表は、現在の deployment compatibility を確立するものではありません。

## 詳説の目次

**[Cilium の紹介と基本概念](01-introduction.md)**
- Cilium の概要と歴史
- Container Networking の基礎
- CNI (Container Network Interface) の理解
- Cilium の差別化機能

**[eBPF 技術の詳説](02-ebpf.md)**
- eBPF 技術と歴史の紹介
- カーネル内部での eBPF の動作
- eBPF Program Types と Maps
- Cilium での eBPF 活用

**[Networking Models と VXLAN](03-networking.md)**
- Container Networking Models の比較
- VXLAN 技術の詳説
- Cilium の Overlay Networking
- Performance Optimization Techniques
- Routing Mechanisms (Encapsulation vs Native-Routing)
- Cloud Provider Networking (AWS ENI, Google Cloud)

**[IPAM と Network Policies](04-ipam-policy.md)**
- IP Address Management (IPAM) Strategies
- Kubernetes と Cilium の IPAM Integration
- Network Policy の設計と実装
- Multi-Cluster Scenarios
- IPAM Mode 詳説 (Cluster Scope, Kubernetes Host Scope, Multi-Pool)
- Cloud Provider IPAM (Azure IPAM, AWS ENI, GKE)
- CRD-based IPAM

**[L2-L7 Networking と Load Balancing](05-l2-l7-networking.md)**
- OSI Model Layers (L2, L3, L4, L7) の理解
- Cilium の Layer-specific Features
- Service Mesh Integration
- Load Balancing Architecture
- Masquerading Configuration and Implementation Modes
- IPv4 Fragment Handling

**[セキュリティと可視性](06-security-visibility.md)**
- Cilium の Security Features
- Network Visibility と Monitoring
- Hubble Architecture と Usage
- Real-time Threat Detection

**[Advanced Topics と実運用ケース](07-advanced-topics.md)**
- Performance Tuning と Troubleshooting
- Large-Scale Deployment Strategies
- Real-World Use Case Studies
- Future Roadmap と Development Direction

**[eBPF Datapath Internals](08-ebpf-datapath-internals.md)**
- Program set、attach points、tail calls
- BPF map catalog、sizing、compile/load flow
- Policy enforcement path と Hubble event pipeline

**[Overlay と Native Routing](09-overlay-native-routing.md)**
- VXLAN/Geneve、VNI 内の identity、MTU、packet walks
- Native routing、masquerading、host routing、DSR、netkit
- EKS decision table: overlay vs ENI vs VPC CNI chaining

**[IPAM 詳説](10-ipam-deep-dive.md)**
- すべての IPAM modes、sizing math、decision matrix
- Multi-pool、`CiliumPodIPPool`、ENI、LB IPAM、Node IPAM
- Exhaustion troubleshooting と 1.21 API changes

**[BGP、Load Balancer IPs、Egress](11-bgp-lb-egress-edge.md)**
- BGP Control Plane v2 CRDs、advertisement、inspection
- L2 announcements、Egress Gateway、Local Redirect Policy
- Gateway API requirements と internal-only EKS exposure

**[mTLS、Encryption、Identity](12-mtls-encryption-identity.md)**
- Identity model、policy semantics、audit mode
- Mutual Authentication timeline、ztunnel workload mTLS
- WireGuard、IPsec、Hubble、certificate management

**[Versions、Install/Upgrade、Cluster Mesh](13-clustermesh-install-upgrade.md)**
- Feature matrix 1.17-1.21、upgrade と rollback rules
- EKS install specifics、Cluster Mesh、MCS-API

## 追加リソース

- [Networking Concepts 詳説](networking-concepts.md)
- [用語集と略語](glossary.md)

## 参考資料

- [Cilium 1.20 Kubernetes compatibility](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/compatibility.rst)
- [Cilium system requirements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [EKS prerequisites](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [Cilium ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [AWS alternate CNI support](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [AWS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium L7 policy semantics](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst)
- [Hubble project](https://github.com/cilium/hubble)
- [Flannel networking and policy integration](https://github.com/flannel-io/flannel)
- [Calico comparison terminology](../calico/glossary.md)

## クイズ

このセクションで学んだ内容を確認するには、[Cilium 詳説クイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)に挑戦してください。