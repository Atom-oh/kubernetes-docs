# ネットワークモデルと VXLAN

> **レビュー基準**: Cilium 1.20.3、テスト済み Kubernetes 1.33～1.36、Linux 5.10以降または文書化された同等のバックポート（RHEL 8.10の4.18カーネルなど）。
> **最終確認**: 2026年10月16日

## ラボ環境の準備

[インストールガイド](README.md)を参照し、使い捨てクラスタとアーキテクチャに適したCilium CLIを準備してください。kubectlのバージョンはAPIサーバーのマイナーバージョンから1つ以内にしてください。「v1.31以上」は互換性を示す基準ではありません。

以下の汎用モードの例では、スケジュール可能なLinuxノードが2台以上あり、競合するPod CNIがなく、kube-proxyが動作し、Pod CIDRがほかの範囲と重複しないことを前提とします。ネイティブルーティングの例では、さらに各ノードが同じL2セグメントに接続されている必要があります。これらはEKS ENI、GKE Dataplane V2、AKS管理Cilium、稼働中クラスタでのCNI移行の手順ではありません。

### ネットワーク解析ツール

tcpdump/Wiresharkは、解析を行うホストでサポートされているパッケージソースからインストールしてください。ノードのパケットキャプチャは、kubectlを実行するだけのノートPCではなく、対象ノードのネットワーク名前空間で行う必要があります。agent monitorが報告するのは出力されたBPFイベントであり、完全なパケットキャプチャではありません。

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type trace -v
```

明示的なVXLANプロファイルでは、対象ワーカー上で次のコマンドを使って上限付きのサンプルをキャプチャします。

```bash
sudo tcpdump -nn -i any -c 50 'udp port 8472'
```

VXLANポートが異なる場合は、設定したポートを指定してください。ノードをまたぐPod通信を生成します。同じノード内の通信はOverlayを通らない場合があります。キャプチャが空でも、誤ったノード、インターフェイス、ポート、通信経路を選んだ可能性があり、ネットワーク障害とは限りません。

## コンテナネットワーキングモデルの比較

Host namespace、bridge、ノード間transportは、ネットワーキングの異なる側面を表し、併用できます。これらに普遍的な性能順位やセキュリティ順位はありません。

| モデル | 仕組み | 主なトレードオフ |
|---|---|---|
| Host network | Podがノードのネットワーク名前空間を共有する | ポートが競合し、ネットワーク名前空間による分離が弱まる。アプリケーション性能が自動的に最高になるわけではない |
| Bridge | 仮想L2 bridgeでインターフェイスを接続する | ノード間通信には引き続きルーティング/transportが必要。Ciliumの各endpointにLinux bridgeが必須というわけではない |
| Overlay | カプセル化した通信をIP underlay上で転送する | ヘッダーと処理のオーバーヘッドが増える一方、underlayにすべてのPod prefixへのルートは不要 |
| Native/underlay routing | ネットワークがワークロードのアドレスをルーティングする | 正しいforwarding/戻りルートとアドレス設計が必要。NetworkPolicyや暗号化を自動的に提供したり取り除いたりはしない |

### Ciliumのネットワーキングモード

Ciliumの`routingMode`は`tunnel`または`native`です。VXLAN/Geneveはトンネルプロトコルの選択肢です。Cloud IPAMとの統合は多くの場合native datapathと組み合わせる別の設定軸であり、3つ目の`routingMode`の値ではありません。BGPはルートを広報する仕組みであり、別のパケット転送モードではありません。

## VXLAN技術の詳細

VXLANは内側のEthernet frameをUDP/IPネットワークにカプセル化します。VTEPがカプセル化/デカプセル化を行い、24 bitのVNIは理論上2^24個の識別子を表現できます。Kubernetes環境が1,600万テナントをサポートするという意味ではありません。

標準化されたVXLANの宛先ポートはUDP 4789です。**CiliumのVXLAN既定値はUDP 8472、Geneveの既定値はUDP 6081**です。どちらも変更できます。Ciliumはカプセル化にセキュリティIDのメタデータを含めることがあるため、一般的なVXLAN segment数をCiliumのtenant/ポリシー境界と同一視しないでください。

### VXLANパケットの構造

```text
Outer Ethernet
  Outer IP (IPv4 or IPv6)
    Outer UDP (Cilium VXLAN default destination 8472; standard 4789)
      VXLAN header (8 bytes, including VNI)
        Inner Ethernet
          Inner IP packet and transport/application payload
```

IPがUDPを運びます。外側のIPヘッダーが外側のUDPヘッダー内に含まれるわけではありません。VXLAN segmentは暗号化や完全性を提供せず、NetworkPolicyによる分離も自動では行いません。underlay経路を適切に制限し、ポリシー/暗号化は別途設定してください。

### MTUの上限

追加のカプセル化/オプションがない一般的なVXLANでは、内側IPのMTU上限は次のように減少します。

| Underlay IPの種類 | 外側IP + UDP + VXLAN + 内側Ethernet | Underlay IP MTUが1,500 bytesの場合の内側IP上限 |
|---|---|---|
| IPv4 | 20 + 8 + 8 + 14 = 50 bytes | 1,450 bytes |
| IPv6 | 40 + 8 + 8 + 14 = 70 bytes | 1,430 bytes |

外側Ethernetヘッダーはunderlay IP MTUの対象外です。暗号化、Geneveオプション、その他の経路で上限が変わることがあります。有効な経路MTUとPod vethデバイスのMTUは同一とは限りません。

Cilium 1.20.3では、**Helmの`MTU`はunderlying networkのMTUを上書き**し、Ciliumが経路のoverheadを計算します。`MTU: 0`は自動検出を選択します。`MTU: 1450`を「最終的なPod payloadのMTU」と考えて設定すると、トンネルoverheadがさらに差し引かれる場合があります。ローカルインターフェイスでの検出だけでは、経路全体の最小MTUを確認できません。

### VXLANとその他のカプセル化方式

| 技術 | 運搬対象/識別子 | プロトコルまたはポート | 境界・制約 |
|---|---|---|---|
| VXLAN | UDP上のEthernet、24 bit VNI | UDP 4789が標準、Ciliumの既定値は8472 | 固定の基本ヘッダー。暗号化ではない |
| Geneve | 拡張可能なオプションを持つ汎用ネットワーク仮想化、24 bit VNI | UDP 6081 | オプション長によってoverheadが変わる |
| GRE | 汎用カプセル化。基本GREにVXLAN形式のVNIはない | TCP/UDPのポート47ではなく、IP protocol 47 | 拡張機能を考慮する。「無制限のネットワーク」は定義された容量ではない |
| NVGRE | GRE上のEthernet。GRE key内に24 bit VSID | IP protocol 47 | 識別子/flowの意味が異なる。サポート状況は実装による |

## CiliumのOverlayネットワーキング

プラットフォーム/profileによる設定上書きがない場合、CiliumはVXLANによるtunnel routingを使用します。ノードをまたぐPod通信には、到達可能なノードアドレス、許可されたtunnel UDP通信、利用可能なMTUが必要です。OverlayでPodアドレス範囲の重複は解決できず、接続されていないノードに到達可能性を与えるものでもありません。パケットの経路、tunnel device、MTU計算、native routingの例は[Overlayとnative routing](09-overlay-native-routing.md)を参照してください。

![ノード間Overlayの通信経路: endpoint処理、送信元VTEPでのカプセル化、underlay上の転送、宛先側でのデカプセル化、endpointへの配送。](../../.gitbook/assets/en-networking-cilium-03-networking-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-03-networking-2.html)

図は概念上の通信経路を示すものです。図中のアドレスはノードごとのIPAM割り当て計画ではありません。実環境では、ノードのPodブロックを重複なく一貫して割り当てる必要があります。ポリシーは設定された箇所で適用され、送信元/宛先のhookは異なる場合があります。

1. Ciliumはcontrol-planeとdatapathの状態から、リモートendpoint/ノードを特定します。
2. 送信元は対象Podのpacketをカプセル化し、underlay上のノードアドレスを使って送信します。
3. 宛先は内側のpacketをデカプセル化し、処理して配送します。
4. 障害箇所の特定にはdatapath event、ルート状態、packet captureを使います。イベントが1つ欠けているだけでは原因を特定できません。

## ルーティングの仕組み

### カプセル化

underlayにはPod prefixごとのルートではなく、ノード/tunnelへの経路だけが必要です。カプセル化にはヘッダーと処理のコストがかかります。大きなframeで相対的なoverheadを減らせるのは、経路全体が選択したMTUに対応している場合だけです。

### ネイティブルーティング

ノードとunderlayは、戻り通信を含めてPodアドレスをルーティングできなければなりません。ルートはクラウドネットワーク、ルーター、静的設定、その他のrouting componentから提供できます。native modeを有効にしても、BGPが自動で開始されたり、すべてのPod CIDRが広報されたりはしません。

`autoDirectNodeRoutes: true`は、同じL2ネットワークを共有するノードに対し直接PodCIDRルートを設定します。複数のL2 segmentがある場合、`directRoutingSkipUnreachable`で到達不能な直接ルートをスキップし、別途動作するルーティング経路に処理させることができます。Overlay tunnelへのfallbackは行いません。

**トンネルルーティングと`autoDirectNodeRoutes: true`を組み合わせないでください。Cilium 1.20.3は起動時にこの組み合わせを明示的に拒否します。以前の**「hybrid mode」手順は無効でした。設定済みGeneve DSR経路など、機能固有のカプセル化とnative routingを併用できる場合がありますが、これは別のサービス機能です。

Cilium BGP Control Planeは、設定したPod/Service prefixをpeerへ広報します。**ローカルdatapathを設定するものではなく、クラスター内に不足しているルートを自動的に提供するコンポーネントとして扱ってはいけません。**

## パフォーマンスの最適化

モードを比較する際は、同じプロトコル、payloadサイズ、並列度、ノード配置、ポリシー、暗号化、proxy設定で測定してください。カプセル化ヘッダーを1つ取り除いても、アプリケーションのレイテンシーが下がるとは限りません。

- **Datapath**: socket load balancing、対応するXDP高速化、DSRは特定の経路に適用されます。VXLAN/native routingだけで自動的に有効にはなりません。
- **Connection tracking**: CiliumのBPF connection trackingとLinux netfilter conntrackは別の状態管理機構です。netfilter経路を迂回しても、確立済み通信がCiliumの接続状態を使わなくなるわけではありません。
- **Maps**: 実際の容量とmemory pressureに基づいてmapのサイズを決めます。LRU evictionはcacheには有用ですが、すべてのmapに対する汎用最適化ではありません。
- **Hostの調整**: CPU/NUMA配置、IRQ配分/coalescing、queue設定は、特定のworkloadを改善することも悪化させることもあります。Huge pageはCilium全般を高速化するスイッチではありません。実際の利用者と環境について根拠を確認してください。

## クラウドプロバイダー固有のネットワーク

| 環境 | 正しい区別 |
|---|---|
| AWS ENI IPAM | CiliumはVPCでルーティング可能なENIアドレスを割り当てます。operatorのIAM/API/subnet/instance capacityが必要です。ENI Security GroupとCilium policyは相互補完します。AWS VPC CNIのPodごとのbranch ENI機能が自動で有効になるわけではありません |
| EKSプラットフォーム | 通常のEC2ノードで別CNIを使う場合、個別のサポート責任があります。FargateとEKS Auto Modeでは、この汎用ラボ設定で組み込みCNIを置き換えられません。Hybrid Nodesには別のサポート対象インストール経路があります |
| Google Cloud | 自己管理のupstream CiliumはKubernetes host-scope IPAMとルーティング可能なalias rangeを使用できます。管理型GKE Dataplane V2ではGoogle管理のCilium/`anetd`を使います。その上に別のupstream datapathを入れたり、公開機能が同一と仮定したりしないでください |
| Azure | Azure CNI Powered by Ciliumは委任されたIPAMとともにAKSが管理します。Upstream Azure IPAMは自己管理のAzure VM/VMSSクラスター向けです。AKS BYOCNIは別途選択するデプロイモデルです |

Cloud firewall/Security Groupは、どのCilium policyを使っても自動的に作成されるものではありません。最初にプラットフォームのガイドとサポートモデルを選択してください。

## ラボ: Ciliumネットワーキングモードの設定と性能テスト

### 準備済みの新規クラスタでモードを1つ選ぶ

共通ファイルを保存する前に、Pod CIDRがノード、Service、VPC、接続ネットワークの範囲と重複していないか確認し、必要なら変更してください。選択した範囲はクラスター/kube-proxy設定とnative profileの`ipv4NativeRoutingCIDR`で一致させます。片方のファイルだけを変更しても不十分です。`kubeProxyReplacement: false`はkube-proxyが動作していることを意図的に前提にします。以下はHelm valuesであり、kubectlで適用するConfigMapではありません。

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

次のモードファイルから必ず1つだけ選択します。比較時は稼働中クラスタにCNIを繰り返し再インストールせず、個別の使い捨てクラスタを使用してください。

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

VXLANの例では、次のように実行します。

```bash
kubectl config current-context
cilium install --version 1.20.3 --values lab-common.yaml --values mode-vxlan.yaml
cilium status --wait
```

ネットワークの前提条件を満たす場合のみ、`mode-geneve.yaml`または`mode-native.yaml`を選んでください。古い`tunnel: vxlan`、`ipv4-range`、`ipv4-service-range`のConfigMap例は適用しないでください。IPAMはサポートされているHelm fieldで設定します。

### ネットワーク性能テスト

`netperf-client`と`netperf-server`を作成するとは限らない無関係なmanifestではなく、CLIで保守されている性能テストworkloadを使用します。準備した使い捨てクラスタで次を実行します。

```bash
cilium connectivity perf --test-namespace cilium-net-perf \
  --namespace-labels docs-audit-lab=cilium-networking-03 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-net-perf-results
```

期間は合計10秒ではなく、各test case/sampleあたりの時間です。この操作でテストworkloadとネットワーク負荷が発生します。CLI 0.20.1はnamespaceに連番suffixを付けます（既定の単一suiteでは`cilium-net-perf-1`）。バージョン、配置、設定を結果と一緒に記録してください。スループット/レイテンシーの数値は保証されません。

TCPのrequest/response、connection-rate、streamテストは、それぞれ異なる問いに答えます。個別に用意したiperf3環境でUDPを試す場合も、TCP control接続とUDP data経路が必要です。TCP 5201だけを公開するServiceでは足りません。指定したUDP送信レートは実測スループットではありません。

例は現行の公式values、API schema、CLI sourceと照合しました。この監査では、ホスト再起動後にHelm templateのレンダリング、クラスターのデプロイ、ネットワークbenchmarkは実施していません。結果を利用する前に、プラットフォームとラボ環境全体を検証してください。

## 参考資料

- [Cilium 1.20.3のrouting](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/routing.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)、[起動時の検証](https://github.com/cilium/cilium/blob/v1.20.3/daemon/cmd/daemon_main.go)、[MTU計算](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/mtu.go)、[MTU設定項目](https://github.com/cilium/cilium/blob/v1.20.3/pkg/mtu/cell.go)
- [VXLAN RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)、[Geneve RFC 8926](https://www.rfc-editor.org/rfc/rfc8926.txt)、[GRE RFC 2784](https://www.rfc-editor.org/rfc/rfc2784.txt)、[NVGRE RFC 7637](https://www.rfc-editor.org/rfc/rfc7637.txt)
- [BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)、[AWS ENI](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)、[EKS alternate CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)、[GKE Dataplane V2](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2)、[Azure IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/azure.rst)
- [CLI 0.20.1のconnectivity/perfオプション](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go)、[iperf3の実行方法](https://software.es.net/iperf/invoking.html)、[kubectlのバージョンskew](https://kubernetes.io/releases/version-skew-policy/)

[メインページに戻る](README.md)

## クイズ

[ネットワーク検証の演習と期待される結果](../../quizzes/networking/cilium/03-networking-quiz.md)を使って学習内容を確認してください。
