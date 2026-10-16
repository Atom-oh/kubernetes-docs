# ネットワーキングモデルと VXLAN

> **ベースラインの確認**: Cilium 1.20.2、テスト済み Kubernetes 1.33–1.36、Linux 5.10 以降、または RHEL 8.10 の 4.18 カーネルなど、文書化された同等のバックポート。
> **最終更新**: October 15, 2026

## ラボ環境のセットアップ

使い捨て Cluster とアーキテクチャに適した Cilium CLI を準備するには、[インストールガイド](README.md)を使用してください。kubectl は API server とのマイナーバージョン差を 1 以内に維持してください。「v1.31 以降」は互換性ルールではありません。

以下の汎用モードの例では、少なくとも 2 台のスケジュール可能な Linux node、競合する Pod CNI がないこと、正常に動作する kube-proxy、および重複しない Pod CIDR が必要です。native routing の例では、さらに node が同じ L2 セグメントを共有している必要があります。これらは EKS ENI、GKE Dataplane V2、AKS managed-Cilium、またはインプレース CNI 移行の手順ではありません。

### ネットワーク分析ツール

分析 host でサポートされているパッケージソースから tcpdump/Wireshark をインストールしてください。node のパケットキャプチャは、kubectl を実行する laptop 上だけでなく、該当する node/network namespace 上で実行する必要があります。agent monitor は出力された BPF event を報告するものであり、完全なパケットキャプチャではありません。

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type trace -v
```

以下の明示的な VXLAN profile では、該当する worker で範囲を限定したサンプルをキャプチャしてください。

```bash
sudo tcpdump -nn -i any -c 50 'udp port 8472'
```

異なる場合は設定済みの tunnel port を使用してください。node 間 Pod traffic を生成してください。same-node traffic は overlay を通過する必要がありません。キャプチャが空であっても、ネットワーク障害ではなく、誤った node、interface、port、または traffic path を意味している可能性があります。

## コンテナネットワーキングモデルの比較

host namespace、bridge、node 間 transport はネットワーキングの異なる側面を表し、共存できます。これらは普遍的なパフォーマンスまたはセキュリティのランキングではありません。

| モデル | メカニズム | 重要なトレードオフ |
|---|---|---|
| Host network | Pod が node network namespace を共有する | port 競合と network-namespace isolation の低下。自動的に最良の application performance になるわけではない |
| Bridge | 仮想 L2 bridge が interface を接続する | node 間通信には引き続き routing/transport が必要。Cilium は endpoint ごとに Linux bridge を必要としない |
| Overlay | カプセル化された traffic が IP underlay を横断する | 追加の header と処理が必要だが、underlay はすべての Pod prefix を route する必要がない |
| Native/underlay routing | network が workload address を route できる | 正しい forwarding/return route と address planning が必要。policy/encryption を本質的に提供または除去するものではない |

### Cilium ネットワーキングモード

Cilium の `routingMode` は `tunnel` または `native` です。VXLAN/Geneve は tunnel protocol を選択します。cloud IPAM integration は別の設定次元であり、多くの場合 native datapath と組み合わせられます。これは 3 つ目の `routingMode` 値ではありません。BGP は route advertisement mechanism であり、別個の packet-forwarding mode ではありません。

## VXLAN テクノロジーの詳細

VXLAN は、inner Ethernet frame を IP network 上で UDP に格納して運びます。VTEP は traffic を encapsulate/decapsulate します。24-bit VNI は理論上 2^24 個の identifier 空間を提供します。これは Kubernetes deployment が 1,600 万 tenant をサポートすることを保証するものではありません。

標準化された VXLAN destination port は UDP 4789 です。**Cilium の VXLAN のデフォルトは UDP 8472**、Geneve は UDP 6081 です。どちらも設定可能です。Cilium は encapsulation 内に security-identity metadata を保持できるため、一般的な VXLAN segment 数を Cilium の tenant/policy boundary と同一視しないでください。

### VXLAN パケット構造

```text
Outer Ethernet
  Outer IP (IPv4 or IPv6)
    Outer UDP (Cilium VXLAN default destination 8472; standard 4789)
      VXLAN header (8 bytes, including VNI)
        Inner Ethernet
          Inner IP packet and transport/application payload
```

IP は UDP を運びます。outer IP header 自体は outer UDP header 内に運ばれるものではありません。VXLAN segmentation は encryption、integrity、または自動的な NetworkPolicy isolation を提供しません。underlay path を適切に制限し、policy/encryption は別途設定してください。

### MTU バジェット

追加の encapsulation/options がない通常の VXLAN では、inner IP budget の削減量は次のとおりです。

| Underlay IP family | Outer IP + UDP + VXLAN + inner Ethernet | 1,500-byte underlay IP MTU における inner IP budget |
|---|---|---|
| IPv4 | 20 + 8 + 8 + 14 = 50 bytes | 1,450 bytes |
| IPv6 | 40 + 8 + 8 + 14 = 70 bytes | 1,430 bytes |

outer Ethernet header は、その underlay IP MTU の外側にあります。encryption、Geneve option、その他の path により budget は変わる可能性があります。有効な route MTU と Pod veth の device MTU は同一である必要はありません。

Cilium 1.20.2 では、Helm の **`MTU` は underlying-network MTU を上書き**し、その後 Cilium が route overhead を計算します。`MTU: 0` は検出を選択します。`MTU: 1450` を「最終的な Pod payload MTU」を意味するものとして設定すると、tunnel overhead が再び差し引かれる可能性があります。local interface の検出も、path 全体で最小の MTU を証明するものではありません。

### VXLAN と他のカプセル化方式の比較

| テクノロジー | Carrier / identifier | Protocol または port | Boundary |
|---|---|---|---|
| VXLAN | UDP 内の Ethernet、24-bit VNI | UDP 4789 標準、Cilium 8472 デフォルト | 固定の base header、encryption ではない |
| Geneve | 拡張可能な option を持つ generic network virtualization、24-bit VNI | UDP 6081 | option length により overhead が変化 |
| GRE | Generic encapsulation。base GRE には VXLAN 形式の VNI はない | IP protocol 47、TCP/UDP port 47 ではない | optional extension を考慮する必要がある。「無制限の network」は定義された capacity ではない |
| NVGRE | GRE 上の Ethernet、GRE key 内の 24-bit VSID | IP protocol 47 | identifier/flow semantics が異なる。support は implementation に依存 |

## Cilium の Overlay ネットワーキング

platform/profile configuration による上書きがない場合、Cilium は VXLAN を使用した tunnel routing を使用します。node 間 Pod transport には、到達可能な node address、許可された tunnel UDP traffic、および利用可能な MTU が必要です。overlay は重複する Pod address range を解決せず、切断された node を到達可能にもしません。packet walk、tunnel device、MTU budgeting、native-routing variant については、[Overlay と native routing](09-overlay-native-routing.md)を参照してください。

![node 間 overlay flow: endpoint 処理、source VTEP encapsulation、underlay transit、destination decapsulation、endpoint delivery。](../../.gitbook/assets/en-networking-cilium-03-networking-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-03-networking-2.html)

この図は概念的な flow です。address は node ごとの IPAM allocation plan ではありません。実際の node Pod block は、重複がないよう一貫して割り当てる必要があります。policy は設定された箇所で適用され、source/destination hook は異なる場合があります。

1. Cilium は control-plane と datapath state から remote endpoint/node を特定します。
2. source は該当する Pod packet を encapsulate し、underlay node address を使用して送信します。
3. destination は decapsulate し、inner packet を処理/配信します。
4. Datapath event、route state、capture は障害の特定に役立ちます。1 つの event がないだけでは原因を特定できません。

## Routing メカニズム

### カプセル化

underlay に必要なのは、すべての Pod prefix の route ではなく、node/tunnel path のみです。cost には header と処理が含まれます。より大きな frame は、path 全体が選択した MTU をサポートする場合に限り、相対的な overhead を削減できます。

### Native Routing

node と underlay は、return traffic を含めて Pod address を route する必要があります。route は cloud network、router、static configuration、または別の routing component から取得できます。native mode を有効にしても、BGP が自動的に開始されることや、すべての Pod CIDR が advertise されることはありません。

`autoDirectNodeRoutes: true` は、同じ L2 network を共有する node に direct PodCIDR route をインストールします。複数の L2 segment がある場合、独立して正常動作する routed path がそれらを処理する一方で、`directRoutingSkipUnreachable` は到達不能な direct route を skip できます。overlay tunnel へフォールバックすることはありません。

**tunnel routing と `autoDirectNodeRoutes: true` を組み合わせないでください。Cilium 1.20.2 は startup 時にこの組み合わせを明示的に拒否します。** 以前の「hybrid mode」の手順は無効でした。native routing は、設定された Geneve DSR path など、feature 固有の encapsulation と共存することがあります。これは別の Service feature です。

Cilium BGP Control Plane は、設定済みの Pod/Service prefix を peer に advertise します。これは**local datapath を program しない**ため、不足している intra-cluster route を自動的に提供する component とみなしてはなりません。

## パフォーマンス最適化のテクニック

mode を比較する前に、同じ protocol、payload size、concurrency、node placement、policy、encryption、proxy setting で測定してください。1 つの encapsulation header を除去しても、application latency が低下するとは限りません。

- **Datapath:** socket load balancing、サポートされる XDP acceleration、DSR は特定の path に適用されます。VXLAN または native routing によって自動的に有効になるものではありません。
- **Connection tracking:** Cilium BPF connection tracking と Linux netfilter conntrack は異なる state mechanism です。netfilter path を bypass しても、すべての established traffic が Cilium connection state の使用を停止するわけではありません。
- **Maps:** 実際の capacity と memory pressure に合わせて map の size を設定してください。LRU eviction は cache には有用ですが、すべての map に対する万能な最適化ではありません。
- **Host tuning:** CPU/NUMA placement、IRQ distribution/coalescing、queue configuration は、特定の workload に役立つ場合も悪化させる場合もあります。Huge page は Cilium の一般的な speed switch ではありません。実際の consumer と環境に対する根拠が必要です。

## Cloud Provider 固有のネットワーキング

| 環境 | 正しい区別 |
|---|---|
| AWS ENI IPAM | Cilium は、operator IAM/API/subnet/instance-capacity 要件に基づき、VPC-routable な ENI address を割り当てます。ENI security group と Cilium policy は相互補完します。これは AWS VPC CNI の Pod ごとの branch-ENI feature ではありません |
| EKS platform | 通常の EC2 node における代替 CNI には、別個の support responsibility があります。Fargate と EKS Auto Mode は、この汎用 lab profile で CNI を置き換えることをサポートしていません。Hybrid Nodes には別個のサポート対象 installation path があります |
| Google Cloud | self-managed upstream Cilium は、Kubernetes host-scope IPAM と routable alias range を使用できます。managed GKE Dataplane V2 は Google 管理の Cilium/`anetd` を使用します。その上に別の upstream datapath をインストールしたり、同一の公開 feature を想定したりしないでください |
| Azure | Azure CNI Powered by Cilium は delegated IPAM を使用して AKS により管理されます。upstream Azure IPAM は self-managed Azure VM/VMSS cluster を対象とします。AKS BYOCNI は別に明示的に選択する deployment model です |

cloud firewall/security-group configuration は、すべての Cilium policy によって自動作成されるわけではありません。最初に platform guide と support model を選択してください。

## ラボ: Cilium ネットワーキングモードの設定とパフォーマンステスト

### 新しく準備した Cluster で 1 つのモードを選択する

この共通ファイルを保存します。最初に Pod CIDR が node、Service、VPC、または接続された network range と重複する場合は置き換えてください。選択した range は、cluster/kube-proxy configuration および native profile の `ipv4NativeRoutingCIDR` と一貫させてください。1 つのファイルだけを変更しても不十分です。`kubeProxyReplacement: false` は、意図的に動作する kube-proxy を前提としています。これらは Helm values であり、kubectl で apply する ConfigMap ではありません。

**`lab-common.yaml`**

```yaml
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
MTU: 0
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```


以下の mode file から**ちょうど 1 つ**を選択してください。live cluster 上で CNI を繰り返し再インストールするのではなく、比較には別々の使い捨て Cluster を使用してください。

**`mode-vxlan.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
```

**`mode-geneve.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: geneve
tunnelPort: 6081
autoDirectNodeRoutes: false
```

**`mode-native.yaml`**

```yaml
routingMode: native
ipv4NativeRoutingCIDR: 10.244.0.0/16
autoDirectNodeRoutes: true
```


VXLAN の例では、次を実行します。

```bash
kubectl config current-context
cilium install --version 1.20.2 --values lab-common.yaml --values mode-vxlan.yaml
cilium status --wait
```

network prerequisite を満たす場合に限り、代わりに `mode-geneve.yaml` または `mode-native.yaml` を選択してください。廃止された `tunnel: vxlan`、`ipv4-range`、`ipv4-service-range` の ConfigMap の例を apply しないでください。サポート対象の Helm field を通じて IPAM を設定してください。

### ネットワークパフォーマンステスト

無関係な manifest が `netperf-client` と `netperf-server` を作成すると仮定するのではなく、CLI で保守されている performance workload を使用してください。準備済みの使い捨て Cluster で次を実行します。

```bash
cilium connectivity perf --test-namespace cilium-net-perf \
  --namespace-labels docs-audit-lab=cilium-networking-03 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-net-perf-results
```

この duration はテストケース/sample ごとの時間であり、実行全体で 10 秒ではありません。これは test workload と network load を作成します。CLI 0.20.1 は namespace に sequence suffix を追加します（デフォルトの single suite では `cilium-net-perf-1`）。version、placement、setting を結果とともに保存してください。throughput/latency の数値は保証されません。

TCP request/response、connection-rate、stream test はそれぞれ異なる問いに答えます。独自に準備した iperf3 setup を使用する場合でも、UDP test には TCP control connection と UDP data path が必要です。TCP 5201 のみを公開する Service では不十分です。offered UDP rate は測定された achieved throughput ではありません。

これらの例は、現在の公式 values、API schema、CLI source に対して確認されました。この監査では、host restart 後に Helm template の render、Cluster の deploy、network benchmark の実行は行っていません。結果に依拠する前に、完全な platform/lab environment を検証してください。

## ソース

- [Cilium 1.20.2 routing](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [startup validation](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go), [MTU calculation](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go), [MTU option](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/cell.go)
- [VXLAN RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt), [Geneve RFC 8926](https://www.rfc-editor.org/rfc/rfc8926.txt), [GRE RFC 2784](https://www.rfc-editor.org/rfc/rfc2784.txt), [NVGRE RFC 7637](https://www.rfc-editor.org/rfc/rfc7637.txt)
- [BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [AWS ENI](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [EKS alternate CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html), [GKE Dataplane V2](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2), [Azure IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/azure.rst)
- [CLI 0.20.1 connectivity/perf options](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go), [iperf3 invocation](https://software.es.net/iperf/invoking.html), [kubectl version skew](https://kubernetes.io/releases/version-skew-policy/)


[メインページに戻る](README.md)

## クイズ

[networking validation exercise と期待される結果](../../quizzes/networking/cilium/03-networking-quiz.md)に取り組んでください。
