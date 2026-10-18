# Part 9: Overlay と Native Routing 詳解

> **レビュー基準**: Cilium 1.20.2（安定版、2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。**[1.21 pre-release]** と記した項目は v1.21.0-pre.3 に基づいており、GA 前に変わる可能性があります。
> **最終更新**: 2026年10月15日

この章では、[Networking Models and VXLAN](03-networking.md) で説明した mode 切替より詳しく掘り下げます。tunnel mode と native-routing mode のそれぞれで、別ノード上の2つの Pod 間をパケットがどう進み、どの BPF program が何を行い、encapsulation に security identity がどう含まれ、MTU と masquerading がどう決まり、どの組み合わせを agent が拒否するかを説明します。また、kube-proxy replacement、DSR、Maglev、socket-LB、host routing、netkit、bandwidth manager、暗号化を同じ datapath の中で扱い、最後に EKS の選択ガイドとトラブルシューティング手順を示します。

関連する章：[eBPF datapath の内部構造](08-ebpf-datapath-internals.md)（program のアタッチ先、map）、[IPAM 詳細](10-ipam-deep-dive.md)（Pod CIDR の割り当て元）、[BGP、load balancing、egress、edge](11-bgp-lb-egress-edge.md)（Pod CIDR の広報、外部 LB）、[mTLS、暗号化、identity](12-mtls-encryption-identity.md)（WireGuard／IPsec の詳細）、[ClusterMesh、インストール、アップグレード](13-clustermesh-install-upgrade.md)。

## 目次

1. Routing mode の比較表
2. Cilium における VXLAN と Geneve
3. VNI に含まれる identity
4. Control plane：CiliumNode から tunnel endpoint まで
5. パケット経路：同一ノード、tunnel、native
6. Native routing：route の提供元
7. 起動時検証：起動失敗と暗黙の fallback
8. MTU の計算
9. Masquerading
10. Host routing：legacy と BPF
11. Datapath device：veth と netkit
12. Datapath 内の Service load balancing
13. Bandwidth manager、BBR、BIG TCP
14. 暗号化との相互作用
15. VTEP と multicast（beta）
16. EKS の選択ガイド
17. 調査用チートシート
18. 演習
19. バージョン差分
20. トラブルシューティング
21. 検証範囲と情報源

---

## 1. Routing mode の比較表

1.20 で `routingMode` が受け付ける値は `tunnel`（デフォルト）と `native` の2つだけです。この章で説明する他の動作は、この選択と、個別に tunnel device を要求する機能の組み合わせで決まります。

| 状況 | Helm | 別ノード間の Pod-to-Pod 通信 | Pod CIDR を route する主体 |
|---|---|---|---|
| Tunnel（デフォルト） | `routingMode: tunnel`、`tunnelProtocol: vxlan`（デフォルト）または `geneve` | BPF が tunnel metadata を設定し、kernel の `cilium_vxlan`／`cilium_geneve` が UDP で encapsulate | 不要。underlay では node 間 IP 到達性と UDP 8472／6081 のみ必要 |
| Native | `routingMode: native` | Pod IP のまま packet が出て、kernel が route（BPF host routing 時は BPF FIB redirect） | network 側：cloud router／ENI、`autoDirectNodeRoutes`、BGP、static route |
| Native + 機能が tunnel を有効化 | `routingMode: native` と Egress Gateway、または `dsrDispatch: geneve` の DSR | 通常の Pod traffic は native。機能固有 packet 用に tunnel device を作成 | native と同じ。tunnel は機能の通信だけを運ぶ |

3行目は `ip link` の出力を見るときに重要です。native-routing の cluster に `cilium_geneve` device があっても設定ミスではありません。コード上、Egress Gateway と Geneve を使う DSR は「tunnel enabler」であり、`routingMode` が `native` でも device の作成を要求します（agent の `tunnel` package、`pkg/datapath/tunnel/tunnel.go` を参照）。

成熟度（1.20.2 のドキュメント記載）：VXLAN／Geneve tunnel mode と native routing は stable です。BGP は route 広報の方式であり、forwarding mode ではありません。[BGP、load balancing、egress、edge](11-bgp-lb-egress-edge.md) を参照してください。

> **1.21 で確認する点。** v1.21.0-pre.3 tree には、Helm chart からは使えない、未完成で文書化されていない別 routing mode の土台が含まれています。この章では名称も説明も記載しません。1.21 GA の routing 文書を再確認し、`routingMode` が2値のままと決めつけないでください。

## 2. Cilium における VXLAN と Geneve

どちらも UDP encapsulation です。Cilium はいずれにも **flow-based（collect-metadata）kernel netdev** を使います。BPF が packet ごとの metadata を設定し、kernel driver がそれを基に outer header を組み立てます。Cilium が BPF 内で outer header を組み立てるわけではありません。

| 特性 | VXLAN | Geneve |
|---|---|---|
| Helm 値 | `tunnelProtocol: vxlan`（デフォルト） | `tunnelProtocol: geneve` |
| デフォルト UDP destination port | 8472 | 6081 |
| Device | `cilium_vxlan` | `cilium_geneve` |
| Identity の格納先 | VNI（24 bit） | VNI（24 bit）、同じ仕組み |
| Cilium が使う option／TLV | なし | DSR service address／port option のみ（class `0x014B`、type `0x81`） |
| DSR 対応 | 不可。VXLAN tunneling と `dsr`／`hybrid` の併用を agent が拒否 | `dsrDispatch: geneve` |
| Kernel config | `CONFIG_VXLAN` | `CONFIG_GENEVE` |

どちらも `CONFIG_FIB_RULES` が必要です。Port 8472 は Linux kernel が歴史的に使ってきた VXLAN のデフォルトで、IANA 割当の4789ではありません。Cilium は互換性のため8472を維持します。`tunnelPort` で変更できますが、port の変更では device を作り直すため短時間の通信断が発生します。MTU の変更なら device 上で反映されます。

関連する設定値：

- `tunnelSourcePortRange: "0-0"`（デフォルト）では kernel driver が outer UDP source port を選びます。範囲を狭めると underlay の ECMP／filter が見る entropy が小さくなります。identity には影響しません。
- `underlayProtocol: auto|ipv4|ipv6`（1.18で追加）。`auto` は IPv4 が有効なら IPv4、それ以外は IPv6 を優先します。IPv6 underlay では tunnel overhead が70 byte に増え、XDP acceleration は使えません。Egress Gateway には IPv4 underlay が必要です。
- `tunnelProtocol` を切り替えると一方の device を削除し、もう一方を作成します。ノード単位の通信に影響する変更として計画してください。

Security group／firewall の要件：**すべての** node 間で UDP 8472（VXLAN）または UDP 6081（Geneve）を許可します。加えて health check 用の TCP 4240 と ICMP echo が必要です。AWS では security group から security group への参照（node SG 自身を参照）を使い、インターネット向けに CIDR を開放しないでください。WireGuard は UDP 51871、IPsec は ESP（IP protocol 50）が必要で、AWS security group では ESP はデフォルトで許可されません。

```yaml
# values: Geneve overlay (needed if you later want DSR dispatch via Geneve)
routingMode: tunnel
tunnelProtocol: geneve
```

## 3. VNI に含まれる identity

Cilium が encapsulate するすべての packet の24-bit tunnel ID（VNI）は、送信元 endpoint の**source security identity**です。VXLAN と Geneve のどちらでも同じです。identity のために Geneve option は使いません。

`bpf/lib/identity.h`、`bpf/lib/encap.h`、`bpf/bpf_overlay.c`（v1.20.2）にある規則：

- dual-stack cluster では、予約済み identity `world-ipv4`（9）と `world-ipv6`（10）はどちらも `world`（2）として送信されます。受信側が inner L3 protocol から正しい identity を復元します。
- `host` identity（1）は送信しません。encapsulation の前に送信側が `local-node`／`remote-node`（6）に書き換えます。`host` を名乗る packet が tunnel 経由で届くと `DROP_INVALID_IDENTITY` で破棄されます。
- 受信側にも ipcache があります。上流の説明では identity の格納は、リモート node での identity lookup を1回省く最適化であり、唯一の正とする情報源ではありません。remote node からの通信では `bpf_overlay.c` が ipcache を使って identity を詳しく解決します。

この仕組みから次のことが分かります。

1. wire 上の VNI は `cilium-dbg endpoint list` の `IDENTITY` 列、または `cilium-dbg identity list` で確認できる identity 番号と一致します。Lab 1 で検証します。
2. ingress policy は destination node で運ばれてきた identity を使って判断するため、source IP から Pod を改めて探す必要はありません。
3. VTEP 統合（セクション15）もこれに依存します。外部 VTEP の traffic は VNI 2（`world`）を付けて送る必要があります。

Geneve option を使う唯一の箇所が DSR です。load balancing node が元の service address と port を持つ Geneve option を挿入し、backend node が返信を書き換えられるようにします。これは12 byte を追加し、datapath で処理されます（セクション8）。

## 4. Control plane：CiliumNode から tunnel endpoint まで

Tunnel mode では、送信側が宛先 Pod IP ごとに (a) security identity と (b) Pod をホストする node の IP（tunnel endpoint）を把握する必要があります。どちらも1つの BPF LPM map に格納されます。

```text
 Kubernetes API                       cilium-agent                       BPF
 --------------                       ------------                       ---
 CiliumNode (remote node IPs,   -->   node manager: node discovery
              podCIDRs)                 |- kernel route per remote PodCIDR
 CiliumEndpoint(Slice)/identity -->   ipcache listener                 cilium_ipcache_v2
   (Pod IP -> identity)                   writes {identity,   ------>  key: prefix
                                                  tunnel_endpoint,       value: identity,
                                                  encrypt key,                  tunnel endpoint,
                                                  flags}                        flags (skip_tunnel...)
```

- `cilium_ipcache_v2` は LPM map です。value には identity、tunnel endpoint（remote node の IPv4／IPv6 address）、暗号鍵 index、`skip_tunnel` などの flag が入ります。listener が tunnel endpoint を設定するのは、host IP がローカル node IP と異なる場合だけです。
- remote PodCIDR ごとに、agent は `cilium_host` 経由の kernel route も追加します（`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`）。BPF の encapsulation 判断には ipcache を使い、その route は host 起点 traffic の fallback です。
- **`cilium_tunnel_map` は削除済みです。** 1.17 ではまだ BPF にあり（`bpf/lib/encap.h`）、`cilium-dbg bpf tunnel list` で出力できました。1.18で datapath から除かれ（1.18.14 の BPF tree に参照はなく、agent が残った map の pin を解除するだけです）、Go package も1.19で削除されました。tunnel endpoint は ipcache value にあるため、`cilium-dbg bpf ipcache list`（tunnel endpoint 列）、`cilium-dbg bpf nodeid list`、`cilium-dbg node list` で確認します。

## 5. パケット経路：同一ノード、tunnel、native

Program 名は v1.20.2 の `bpf/bpf_lxc.c`、`bpf/bpf_overlay.c`、`bpf/lib/local_delivery.h` に基づきます。アタッチ方式は[eBPF datapath の内部構造](08-ebpf-datapath-internals.md)を参照してください。

### 5.1 Pod A（node 1）から Pod B（node 2）、tunnel mode

```text
 node 1                                                          node 2
 ------                                                          ------
 Pod A eth0
   |  (veth/netkit peer on host)
   v
 [bpf_lxc: cil_from_container]
   1. service DNAT (socket-LB at connect(), or lb4_local per packet)
   2. conntrack lookup (cilium_ct4_global)
   3. ipcache lookup of dst -> dst identity + tunnel endpoint (node 2)
   4. egress policy (per-endpoint policy map, by identity)
   5. dst not local -> TUNNEL_MODE branch:
        set tunnel key { id = src identity, remote = node 2 IP }
        (bpf_skb_set_tunnel_key), redirect to ifindex of cilium_vxlan
   v
 [cilium_vxlan  (flow-based netdev)]
   cil_to_overlay on its egress: identity mark, SNAT handling,
   EDT bandwidth (if bandwidth manager is on)
   kernel vxlan driver builds outer Eth/IP/UDP(8472)/VXLAN(VNI)
   v
 NIC  ==== underlay IP network, UDP 8472 ====>  NIC
                                                  |
                                                  v
                                       kernel vxlan driver decapsulates
                                                  v
                                       [cilium_vxlan ingress: cil_from_overlay]
                                         validate ethertype, read tunnel key
                                         -> src_sec_identity
                                         tail call IPV4_FROM_OVERLAY (handle_ipv4):
                                           VTEP source check (must be world)
                                           remote-node identity refinement (ipcache)
                                           lookup destination endpoint
                                           ipv4_local_delivery(from_tunnel=true)
                                         tail call cilium_call_policy:
                                           ingress policy of Pod B using the carried identity
                                         redirect into Pod B's netns (redirect_peer with veth
                                           when BPF host routing is active)
                                                  v
                                                Pod B eth0
```

要点：

- **Encapsulation は kernel、転送先の指定は BPF。** BPF は tunnel key（`BPF_F_ZERO_CSUM_TX`、TTL 64）を設定し、tunnel device に redirect します。「eBPF が packet を自ら encapsulate する」というよくある単純化を正します。
- 暗号化は encapsulation の**後**に適用されます（1.18以降の IPsec。WireGuard は別 device）。したがって暗号化が有効な場合、物理 NIC には VXLAN ではなく ESP または WireGuard が見えます。
- 返信は conntrack entry を使って対称に戻ります。宛先 node が Pod B の identity を VNI として encapsulate します。
- **remote node** の address 宛て Pod traffic は tunnel を通りません。tunnel mode では masquerade されます（セクション9）。

### 5.2 同一ノード上

`__lookup_ip4_endpoint` が宛先のローカル endpoint を探します。`ipv4_local_delivery` は `cilium_call_policy` に tail call して宛先の ingress policy を実行し、BPF host routing を使う veth では `bpf_redirect_peer`、それ以外では `bpf_redirect` で届けます。netkit では Pod-to-Pod traffic は egress から ingress へ通常の `redirect` を使います。encapsulation はありません。

### 5.3 Pod A から Pod B、native routing

手順1〜4は同じです。手順5では tunnel を使いません。

- **BPF host routing**（KPR と BPF masquerade が有効なときのデフォルト）では、`fib_redirect_v4` が FIB lookup を行い、NIC から直接 redirect します（`bpf_redirect_neigh` 相当）。netfilter と上位 stack を迂回します。
- **Legacy host routing** では program が `CTX_ACT_OK`（stack に渡す）を返します。Linux kernel は利用可能な route（AWS ENI／endpoint route、`autoDirectNodeRoutes`、BGP から学習した route、cloud router など）で packet を route します。

外側の network には raw Pod IP が見えます。そのため network 側でそれらを route できる必要があり、anti-spoofing 検査（ENI 非接続 instance の EC2 source／destination check など）と security group でも許可する必要があります。ENI が持つ Pod IP は VPC が直接所有します。

## 6. Native routing：route の提供元

`routing-mode: native` はローカル宛てでない packet を kernel に渡し、Cilium は IP forwarding を有効化します。Pod CIDR の場所を network に教えるのは Cilium ではなく、次のいずれかです。

| Route の提供元 | Helm | 備考 |
|---|---|---|
| Cloud fabric | `eni.enabled`（AWS）、`gke.enabled`、Azure IPAM | Pod IP は cloud network 上の native address。per-endpoint route（`enable-endpoint-routes`）は chart が設定 |
| Node への直接 route | `autoDirectNodeRoutes: true` | `<remote podCIDR> via <remote node IP>` を設定。全 node が同じ L2 segment 上に必要 |
| BGP | Cilium BGP control plane または外部 daemon | [chapter 11](11-bgp-lb-egress-edge.md) 参照 |
| Static route | なし | 運用者が管理 |

`directRoutingSkipUnreachable`（デフォルト false）は on-link でない node への直接 route を設定しません。この option には `autoDirectNodeRoutes` が**必須**です。未指定なら agent が終了します。tunnel への fallback ではありません。

Helm の検査：native routing で `enableIPv4Masquerade` に truthy 値を設定した場合、次のいずれかを満たさないと `helm template` は「ipv4NativeRoutingCIDR must be set when routingMode is native」で失敗します。`ipam.mode` が `eni` または `alibabacloud`、ip-masq-agent が有効、または `nativeRoutingCIDRFromClusterPool: true`（1.20で追加。`ipam.mode=cluster-pool` で pool CIDR がちょうど1つ必要）です。chart の `enableIPv4Masquerade` デフォルトは null であり、agent 自身のデフォルトは true です。そのため値を未設定にすると agent が masquerade していても検査は**失敗しません**。IPv6 の検査も同じで、`ipv6.enabled`、`enableIPv6Masquerade`（chart default true）、`ipv6NativeRoutingCIDR` を使います。

```yaml
# values: native routing in a single L2 segment
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16   # must cover all Pod CIDRs
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
```

Native-routing CIDR の意味：CIDR 内の宛先は masquerade せず stack に渡します。未設定ならローカル node の PodCIDR がデフォルトです。ENI／Azure／AlibabaCloud では operator が cloud から導出します（primary VPC CIDR のみ）。手動で指定する値は VPC CIDR に含まれていなければなりません。そうでない場合、agent は「None of the VPC CIDRs contains the specified native routing CIDR」で失敗します。

### AWS ENI datapath（route の仕組み）

ENI IPAM では Pod IP は ENI の secondary IP または prefix です。agent は endpoint ごとの route と、Pod IP ごとに2つの ip rule を設定します。ingress rule は `to <podIP> lookup main`（priority 20、`RulePriorityIngress`）、egress rule は `from <podIP> lookup <ENI table>`（priority 111、`RulePriorityEgressv2`。旧 priority 110 は Azure IPAM mode でのみ使用）です。masquerade が有効な場合のみ、egress rule に `to <VPC CIDR>` selector が追加されます（VPC CIDR ごとに1 rule）。ENI ではデフォルトで masquerade が無効なため、通常 egress rule に `to` selector はありません。ENI table には ENI subnet の router 経由の default route が入ります。ICMP packet-too-big を生成できるように router IP は ENI address space から選びます。operator に `ec2:DescribeRouteTables` 権限が必要になったのは1.18以降です。addressing の詳細は[IPAM 詳細](10-ipam-deep-dive.md)を参照してください。

## 7. 起動時検証：起動失敗と暗黙の fallback

不適切な組み合わせでも agent が停止するものと、ログに1行出るだけで能力の低い datapath に移行するものがあります。この違いを把握してください。

### 起動時に失敗（agent 終了または Helm render 失敗）

| 設定 | 結果 |
|---|---|
| `routingMode: tunnel` + `autoDirectNodeRoutes: true` | Fatal：「auto-direct-node-routes cannot be used with tunneling. Packets must be routed through the tunnel device.」（1.20.2） |
| `ipam: eni` + tunnel | Fatal：「Cannot specify IPAM mode eni in tunnel mode.」 |
| `directRoutingSkipUnreachable` を `autoDirectNodeRoutes` なしで設定 | Fatal |
| DSR／hybrid mode + VXLAN tunnel | Error：Node Port の `dsr` mode は `vxlan` tunneling と併用不可 |
| Tunnel + `dsrDispatch: geneve` なしの DSR／hybrid | Error：`geneve` dispatch が必要 |
| `tunnelProtocol: geneve` なしの `dsrDispatch: geneve` | Error：Geneve tunnel protocol が必要 |
| XDP acceleration + IPv6 underlay | Error |
| Native routing + truthy の `enableIPv4Masquerade` + native CIDR なし／例外条件なし | Helm template failure（値が未設定なら chart default が null のため失敗しない） |
| 前提条件未達の明示的な `bpf.datapathMode: netkit` | 起動失敗（セクション11） |
| kernel 5.18 の `skb_set_tstamp` なしの BBR、または BPF host routing なしで Pod 用 BBR | Agent error（セクション13） |
| BPF host routing／KPR／BPF masquerade なし、または IPsec／DSR IPIP 併用の BIG TCP | 起動時 error |
| BPF masquerade なしで `enable-remote-node-masquerade` | Error |
| BPF masquerade なしで `ip-masq-agent` | Error |

VXLAN と per-service annotation mode（`bpf.lbModeAnnotation=true`）を使う場合、validator が受け付けるのは `dsrDispatch: ipip` のみです。global default mode は `snat` のままにします。

**[1.21 pre-release]** `autoDirectNodeRoutes` の message は「auto-direct-node-routes requires native routing mode」です。実際の検査条件は引き続き「tunneling が有効」です。

### 暗黙の fallback（agent は稼働するが datapath 能力が下がる）

| 設定 | 動作 |
|---|---|
| BPF host routing（デフォルト）だが iptables masquerade、または KPR が無効 | 「BPF host routing requires bpf-masquerade / kube-proxy-replacement ... Falling back to legacy host routing」を記録し、legacy routing を使う |
| `bpf.datapathMode: auto` で netkit 前提を満たさない | 「datapath autodiscovery failed, reverting from netkit to veth」を記録し、veth にする |
| Bandwidth manager + IPsec | 警告を出して manager を無効化 |
| 対応外 kernel 上で BIG TCP を有効化 | 警告して無効化 |
| 必要な BPF helper のない kernel で multicast を有効化 | 「Disabled support for BPF Multicast」を記録して無効のままにする |
| CNI chaining | chart が legacy host routing を強制し、no-conntrack iptables rule を無効化 |

コード上の非対称は意図的です。host routing と `auto` は「best effort」ですが、名前を指定して要求する機能（netkit、BBR、BIG TCP）は提供できなければ失敗します。変更の後は値だけを信用せず、実効状態を確認してください（セクション17）。

## 8. MTU の計算

**検出。** Base MTU は Cilium が選んだ native device の MTU の最小値です。ただし `cilium_vxlan`、`cilium_geneve`、IPIP device、dummy device は除外します。`MTU: 0`（デフォルト）は「自動検出」を意味します。0 以外の Helm `MTU` は最終的な Pod MTU ではなく、**underlay network の MTU** です。CNI config の MTU も上書き設定になります。ローカルで MTU を検出しても、router 間の path MTU が同じとは限りません。

**Pod device と route MTU。** Pod の veth／netkit device MTU は base MTU と同じです。Pod 内の route MTU は overhead 分だけ小さくなります。そのため Pod 内の `ip link` では1500、`ip route` では `mtu 1450` と表示される場合があります。

`pkg/mtu/mtu.go`（v1.20.2）の overhead：

| 構成要素 | Byte 数 | 内訳 |
|---|---|---|
| Tunnel、IPv4 underlay | 50 | 20 IP + 8 UDP + 8 VXLAN + 14 inner Ethernet |
| Tunnel、IPv6 underlay | 70 | 40 IP + 8 + 8 + 14 |
| IPsec（128-bit GCM、デフォルトの鍵サイズ） | 77 | 鍵サイズに応じて調整 |
| WireGuard | 95 | 定数 |
| Geneve DSR option | 12 | route MTU ではなく datapath で追加 |

| 条件（underlay 1500） | Pod 内の route MTU | 計算 |
|---|---|---|
| Native、暗号化なし | 1500 | base |
| Tunnel VXLAN、IPv4 underlay | 1450 | 1500 - 50 |
| Tunnel VXLAN、IPv6 underlay | 1430 | 1500 - 70 |
| Native + WireGuard | 1405 | 1500 - 95 |
| Native + IPsec | 1423 | 1500 - 77 |
| Tunnel + IPsec | 1373 | 1500 - (50 + 77) |
| Tunnel + WireGuard | 1355 | 1500 - (95 + 50) |

数値は source の定数と `getRouteMTU` function から計算したもので、cluster 上での実測値ではありません。jumbo frame では overhead の絶対値は同じなので、相対的にずっと小さくなります（underlay 9001 なら、IPv4 上の VXLAN は8951）。

補足：

- **Geneve DSR** は12-byte option を追加します。load balancing node が option を挿入するため、大きな packet は path MTU を超える可能性があります。TCP hybrid mode（TCP の SYN metadata のみ DSR、UDP は SNAT）は、この影響を抑えるためにもあります。
- **`pmtuDiscovery.enabled`**（デフォルト false）を有効にすると、client に ICMP fragmentation-needed を送ります。`pmtuDiscovery.packetizationLayerPMTUDMode`（1.19で追加。値は `always|blackhole|disabled|unset`、デフォルト `blackhole`）で Pod netns 内の kernel RFC 4821 probe を制御します。MTU が分かっている場合は `disabled` にします。
- **CNI chaining**：`cni.enableRouteMTUForCNIChaining: true` で、chain 内 plugin が作成する Pod に route MTU を渡します（例：aws-cni 上の WireGuard で必要）。
- **IPv4／IPv6 fragment** はデフォルトで追跡します（`enable-ipv4-fragment-tracking`、`enable-ipv6-fragment-tracking`。table は `bpf-fragments-map-max`、デフォルト8192。上流では beta）。[L2／L7 networking](05-l2-l7-networking.md) を参照してください。
- AWS で **XDP** を使うには ENA native XDP の上限以下の MTU が必要です（上流の例は3498）。jumbo frame の node は MTU を下げない限り利用できません。

Pod で確認するには `kubectl exec <pod> -- ip route` と `ip link` を実行し、両方向で `ping -M do -s <size>` を試します。

## 9. Masquerading

Cluster 外へ出る Pod traffic の送信元を node IP に書き換えるのが masquerading です。Cilium には2つの実装があります。

| | iptables（デフォルト） | BPF（`bpf.masquerade: true`） |
|---|---|---|
| 必要条件 | iptables／ipset module | KPR（BPF NodePort）、device 検出 |
| 対象 | `egressMasqueradeInterfaces` で制限しない限り、Cilium device 以外から出るすべての通信 | 検出または `devices` で選ばれた device。CIDR で除外可能 |
| Host routing | legacy host routing を強制（暗黙の fallback） | BPF host routing と併用可能 |
| Protocol | netfilter が処理するすべて | TCP、UDP、ICMP（echo、echo-reply、frag-needed）。IPv4 は production、IPv6 は beta |
| 追加機能 | `enableMasqueradeRouteSource` | ip-masq-agent、`enableRemoteNodeMasquerade` |
| Port range | kernel | NodePort max + 1 .. 65535（`bpf/lib/nat.h`）。NAT table `bpf.natMax` のデフォルト524288 |

デフォルト：`enableIPv4Masquerade: true`。ただし1.18以降、`eni.enabled=true` ならデフォルトは**false**です。`enableIPv6Masquerade: true`。**[1.21 pre-release]** では「ENI IPAM 以外なら true」になります。`egressMasqueradeInterfaces` が影響するのは iptables masquerade だけです。masquerade 無効の ENI profile では何も変わりません。

### BPF masquerade の判断順序

v1.20.2 の `bpf/lib/nat.h` に基づき、送信 packet ごとに以下の順で評価します。

1. Egress Gateway policy に一致：gateway IP に SNAT。
2. 宛先が SNAT 除外 CIDR（native-routing CIDR。未指定ならローカル PodCIDR）内：masquerade しない。
3. ローカル endpoint に `SKIP_MASQ` flag がある（multi-pool IPAM）：masquerade しない。
4. 宛先が `cilium_ipmasq_v4`（ip-masq-agent の LPM map）内：masquerade しない。
5. 宛先が**remote node** identity：
   - `enable-remote-node-masquerade=true`：SNAT。
   - それ以外で native routing：masquerade しない。
   - それ以外で tunnel mode：ipcache entry に `skip_tunnel` がなければ SNAT。
6. 送信元がローカル endpoint：egress device の node address に SNAT。それ以外はそのまま通す。

ここから2点が分かります。第一に remote node 宛て Pod traffic は、native routing では Pod IP を保持しますが、tunnel mode では masquerade されます。host firewall と node 単位の `NetworkPolicy`／host policy から見える送信元が変わります。第二に上流の masquerading 文書は手順5を大まかに書いています（「別の cluster node 宛ての packet」は除外と記載）。上表は BPF code を正としています。

`enable-remote-node-masquerade`（1.19で追加）には1.20.2で専用の Helm key がありません。`extraConfig: {enable-remote-node-masquerade: "true"}` を使います。BPF masquerade が必要です。また送信元が node address になるため、host firewall による ingress 制御が弱まります。

### ip-masq-agent

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
    masqLinkLocal: false
```

chart は release namespace に `ip-masq-agent` という ConfigMap と `config` key（JSON）を生成します。agent は mount された file を fsnotify で監視します。空の config では組み込みの非 masquerade CIDR を使います。10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、100.64.0.0/10、192.0.0.0/24、192.0.2.0/24、192.88.99.0/24、198.18.0.0/15、198.51.100.0/24、203.0.113.0/24、240.0.0.0/4 に加え、`masqLinkLocal` を設定しない場合は169.254.0.0/16、`masqLinkLocalIPv6` を設定しない場合は fe80::/10 が含まれます。`cilium_ipmasq_v4/v6` map はそれぞれ16384 entry を保持します。ip-masq-agent を使う場合、native-routing CIDR は必須ではありません。

確認：`cilium-dbg status | grep Masquerading`（例：`BPF (ip-masq-agent) [eth0] <cidr> [IPv4: Enabled, IPv6: Disabled]`）と `cilium-dbg bpf ipmasq list`。

既知の制限：BPF masquerade は node の External IP 宛て Pod traffic を masquerade しません（上流 issue 17177）。**[1.21 pre-release]** `nodePort.extendedNATPortRange`（`--node-port-nat-range-ext`）で大きな NAT table の SNAT port range を広げます。

起動時に検査される非互換性：`--masquerade-interfaces` 相当の device 選択と `enable-masquerade-to-route-source` は BPF masquerade と併用できません。

## 10. Host routing：legacy と BPF

| | Legacy host routing | BPF host routing |
|---|---|---|
| Flag | `bpf.hostLegacyRouting: true` | 前提条件を満たす場合のデフォルト |
| 経路 | Pod -> veth -> host netfilter／routing -> NIC | Pod -> BPF FIB lookup -> NIC。Pod netns 内へ `redirect_peer` |
| netfilter／iptables | 経路上にある | 迂回 |
| 必要条件 | 特になし | KPR と BPF masquerade（満たさないと暗黙の fallback） |
| 必須となる機能 | 該当なし | netkit、Pod 用 BBR、BIG TCP、FIB table annotation による dynamic egress routing |

BPF host routing は netfilter と上位 stack を通らないため、host namespace 内の netfilter に依存する機能は動作しなくなります。既知の非互換性は Istio sidecar の redirect（上流 issue 36022）や、GKE Workload Identity など netfilter に依存する provider 機能です。回避策は `bpf.hostLegacyRouting: true` または Local Redirect Policy です。1.19以降、KPR と BPF masquerade が有効なら IPsec 利用時に host routing を自動的に使えます。kernel には CVE-2025-37959 の修正が必要です。

Legacy mode では `installNoConntrackIptablesRules: true` により conntrack の費用を減らせます（native routing、IPv4、socket-LB を使う KPR、BPF masquerade が必要）。chart は eni、azure、gke、CNI chaining では強制的に無効にします。

`cilium-dbg status` の `Routing:` 行にある `Host:` field を確認します（`Host: BPF` または `Host: Legacy`）。Cilium 1.20.2 は「Host Routing」という独立行を出力しません。

## 11. Datapath device：veth と netkit

`bpf.datapathMode` は `veth`（デフォルト）、`netkit`、`netkit-l2`、1.20で追加された `auto` を受け付けます。

- `netkit`（L3 mode。ARP なしで上流が推奨する variant）と `netkit-l2` は peer 内に BPF をアタッチし、tcx を使います。BIG TCP に対応します。1.20.2 のドキュメントでは**beta**です。kernel 6.8以降（`CONFIG_NETKIT`）が必要との記載ですが、code comment は6.7以降です。最低要件はドキュメントに従い、最終判断は実行時 probe に任せてください。
- 前提条件（`canUseNetkit`）：netkit probe 合格、`bpf.hostLegacyRouting` を使わない、BPF masquerade を有効（iptables ではない）、`kubeProxyReplacement: true`、`bpf.tproxy` を使わない（1.19以降非互換）。`enableEndpointRoutes` を使う場合は driver が scrub attribute に対応していること（kernel 6.13または backport）。
- 明示的に `netkit`／`netkit-l2` を指定して前提条件を満たさない場合は**起動失敗**です。`auto` は警告して veth に切り替え、`cilium-dbg status` は「Device Mode: netkit [Configured: auto]」のように設定値と実効値を示します。
- すでに veth Pod がある node は（`auto` を含めて）mode の切り替え時に error になります。node 単位の設定（`CiliumNodeConfig`）を使うか、先に node を drain してください。

```yaml
# values: safe netkit probe
bpf:
  datapathMode: auto
  masquerade: true
kubeProxyReplacement: true
routingMode: native
```

`cilium-dbg status | grep -E "Device Mode|Routing|Attach Mode"` で確認します（host routing は `Routing:` 行の `Host: BPF|Legacy` に表示）。kernel が一般化したら veth を非推奨にし、デフォルトを変更する可能性があると上流は述べています。現在の default が固定だと思わないでください。

## 12. Datapath 内の Service load balancing

セクション5の Pod-to-Pod 通信経路に各 service 機能がどう組み込まれるかを見ていきます。

```text
 client Pod -> connect()  --[socket-LB: cgroup connect4/sendmsg/recvmsg hooks]--> backend IP:port chosen
                |                                         (E/W, ClusterIP; before any packet exists)
                v
 packet leaves Pod -> bpf_lxc (lb4_local if socket-LB did not already translate)
                |
 external client -> NIC -> [XDP, optional: LB at driver level] -> bpf_host (from-netdev)
                       -> NodePort/LB lookup -> backend selection: random or Maglev
                       -> forward mode: SNAT, DSR (opt/ipip/geneve) or hybrid
                       -> backend local: deliver; remote: native route / tunnel (+Geneve option for DSR)
```

**kube-proxy replacement（KPR）。** boolean 設定です：`kubeProxyReplacement: true|false`（strict／partial は削除済み）。`true` にすると socket-LB も有効になります。API の ClusterIP 解決を kube-proxy が行わなくなるため、`k8sServiceHost`／`k8sServicePort` を設定してください。ClusterIP、NodePort、LoadBalancer、externalIPs、hostPort を扱い、tunnel／native mode の両方で動作します。KPR=false でも ClusterIP の packet 単位 load balancing は行います。1.19で `--enable-node-port`、`--enable-host-port`、`--enable-external-ips` を削除。1.20では `--node-port-mode`、`--node-port-algorithm` を削除（`loadBalancer.mode`／`loadBalancer.algorithm` を使用）。

**Socket-LB。** `socketLB.enabled`（KPR 有効時は on）は `connect`／`sendmsg`／`recvmsg`／`getpeername` に hook します。`socketLB.hostNamespaceOnly: true` では host namespace だけに制限します。Istio sidecar、KubeVirt、Kata、gVisor ではこれが必要です（`gatewayAPI.enabled` 時は強制されます）。`socketLB.terminatePodConnections`（デフォルト true）には kernel `CONFIG_INET_DIAG*` が必要です。**1.20での変更**：socket-LB が無効、または `hostNamespaceOnly=true` の場合、Pod から NodePort への通信は client Pod の egress で DNAT されます。egress NetworkPolicy は NodePort だけでなく backend を許可する必要があります。

**Algorithm。** `loadBalancer.algorithm: random|maglev`。Maglev は map-in-map の `cilium_lb4_maglev`／`cilium_lb6_maglev` に service ごとの lookup table を構築し、5-tuple を hash 化します（ClientIP affinity が有効な場合は source port を0にする）。table size で剰余を取ります。north/south traffic のみ適用し、socket-LB を通る east/west traffic では迂回されます。`maglev.tableSize` は251、509、1021、2039、4093、8191、16381、32749、65521、131071のいずれか（デフォルト16381。service あたり約160 backend を想定）です。`maglev.hashSeed` はすべての agent で同一にします。

```bash
SEED=$(head -c12 /dev/urandom | base64 -w0)   # generate once, store it in your values/secret store
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set kubeProxyReplacement=true \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set maglev.hashSeed=$SEED
```

Service ごとの上書き：`bpf.lbAlgorithmAnnotation=true` と annotation `service.cilium.io/lb-algorithm: maglev` を使います（Service 作成時のみ）。1.20で追加された EndpointSlice annotation `service.cilium.io/weight` は0〜65535で Maglev のみ対応し、0 はメンテナンス中を表します。

**Forwarding mode。** `loadBalancer.mode: snat|dsr|hybrid`。

- `snat`：request を受けた node が送信元を書き換えるため、返信も同じ node を通ります。
- `dsr`：backend が client に直接返信します。service IP／port を backend に伝えます。`hybrid` では TCP は DSR（service address は SYN にだけ格納）、UDP は SNAT にします。
- Dispatch（`loadBalancer.dsrDispatch`、デフォルト `opt`）は情報を渡す方式です。

| `dsrDispatch` | Native routing | Tunnel（Geneve） | Tunnel（VXLAN） |
|---|---|---|---|
| `opt`（IP option／IPv6 destination option） | 対応 | 非対応 | 非対応 |
| `geneve` | 対応（Geneve device を作成） | 対応 | 非対応（VXLAN は DSR 不可） |
| `ipip`（1.20で文書化） | 対応 | 非対応 | annotation mode の validator で例外的に許可されるだけ。動作する構成として文書化されていない |

IPIP は `cilium_ipip4/6` を作成し、service port と target port を同じにする必要があります。任意の RSS source CIDR（`--bpf-lb-rss-ipv4-src-cidr`）に対応しますが、BIG TCP とは非互換です。Cloud fabric は IP option（`opt`）付き packet を破棄する場合があるため、その環境では `geneve` または `ipip` を推奨します。AWS では DSR 用に EC2 source／destination check を無効化する必要があります。tunnel mode の DSR には `tunnelProtocol: geneve` と `dsrDispatch: geneve` が必要です。

```yaml
# values: tunnel mode, kube-proxy-free, DSR via Geneve
routingMode: tunnel
tunnelProtocol: geneve
kubeProxyReplacement: true
k8sServiceHost: <API_SERVER_FQDN>      # host only, no scheme
k8sServicePort: 443
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

Annotation mode では `bpf.lbModeAnnotation=true` とし、Service ごとに `service.cilium.io/forwarding-mode: dsr|snat` を指定できます。`loadBalancer.dsrDispatch` は明示的に設定してください。EKS 上で annotation を付ける LoadBalancer Service は internal（`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`）に保ちます。CloudFront と VPC origin 経由の場合のみ外部公開します。

**XDP acceleration。** `loadBalancer.acceleration: disabled|native|best-effort`。選択したすべての device に native-XDP driver が必要です（未対応 device があれば `best-effort` を使う）。direct-routing device のみを高速化します。IPv6 underlay とは非互換で、L2 neighbor discovery を自動で有効にします。XDP で戻された packet は `tcpdump` に表示されません。XDP で高速化された north/south traffic と Geneve 以外の DSR traffic は WireGuard で暗号化されません。

**把握しておきたい既知の問題：** reverse socket map の枯渇、socket-LB 用 NFS／SMB kernel patch、backend 終了との race（`preStop` sleep を追加）、DSR を壊す TCP Fast Open、複数 device DSR での rp_filter 警告。[L2／L7 networking](05-l2-l7-networking.md) の比較表も参照してください。

## 13. Bandwidth manager、BBR、BIG TCP

**Bandwidth manager。** `bandwidthManager.enabled`（デフォルト false）、`bandwidthManager.bbr`、`bandwidthManager.bbrHostNamespaceOnly` で設定します。`kubernetes.io/egress-bandwidth` annotation（FQ を使う EDT。Pod の host-side device と tunnel device の egress で適用）と、`kubernetes.io/ingress-bandwidth` annotation（BPF token bucket）もあります。値は Kubernetes quantity の**bit 単位**です。`"10M"` は10 Mbit/s で、10 MB/s ではありません。replica set 単位ではなく Pod 単位です。

副作用：host sysctl の `net.core.default_qdisc=fq`、`net.ipv4.tcp_congestion_control`（`cubic` または `bbr`）を設定し、`netdev_max_backlog` の基準値を1000以上、`somaxconn` と `tcp_max_syn_backlog` を4096以上にし、外部 device に FQ を設定します。BBR には kernel 5.18 が必要です。Pod 用 BBR は BPF host routing が必要です（`bbrHostNamespaceOnly` の場合を除き、不足すると error）。IPsec と併用すると manager は通知なしで無効になります。既存 Pod は古い congestion control を維持し、BBR が適用されるのは新しい Pod です。

確認：`cilium-dbg status | grep BandwidthManager`（例：`EDT with BPF [BBR] [eth0]`）と `cilium-dbg bpf bandwidth list`。

**BIG TCP。** `enableIPv4BIGTCP` と `enableIPv6BIGTCP`（どちらもデフォルト false）。必要な kernel は IPv6 で5.19以降、IPv4 で6.3以降です。上流が挙げている NIC driver は mlx4、mlx5、ice などです。BPF host routing、KPR、BPF masquerade が必要です。IPsec と DSR IPIP とは非互換です。MTU を変えずに GSO／GRO の最大サイズを192 KBにします。切り替えた後は Pod を再起動してください。上流文書には「tunneling 無効」とありますが、code 上は UDP-tunnel BIG TCP の kernel probe に合格すれば VXLAN／Geneve 上でも許可されます。不合格なら「BIG TCP in tunneling mode requires pending kernel support」で失敗します。実運用上は native routing を推奨します。

**上流推奨の performance profile**（既存 node への一括適用ではなく、node ごとに設定）：

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set routingMode=native \
  --set bpf.datapathMode=netkit \
  --set bpf.masquerade=true \
  --set bpf.distributedLRU.enabled=true \
  --set bpf.mapDynamicSizeRatio=0.08 \
  --set ipv6.enabled=true --set enableIPv6BIGTCP=true \
  --set ipv4.enabled=true --set enableIPv4BIGTCP=true \
  --set kubeProxyReplacement=true \
  --set bpfClockProbe=true
```

Bandwidth manager を使う場合は `bandwidthManager.enabled=true` と `bandwidthManager.bbr=true` を追加します。セクション7との関連に注意してください。この profile の netkit と BIG TCP には BPF host routing が必要です。そのため KPR と BPF masquerade も必要です。

## 14. 暗号化との相互作用

ここでは datapath への影響だけ扱います。鍵管理は[chapter 12](12-mtls-encryption-identity.md)を参照してください。

| | WireGuard | IPsec |
|---|---|---|
| Transport | UDP 51871 | ESP（IP protocol 50） |
| Tunnel mode 時 | 二重 encapsulation：先に VXLAN／Geneve、次に WireGuard | overlay encapsulation の**後**に暗号化（1.18以降は常にこの順序） |
| MTU @1500 | tunnel 1355、native 1405 | tunnel 1373、native 1423 |
| Strict mode | `encryption.strictMode.ingress.enabled`（1.19以降）は WireGuard を要求し（IPsec 不可）、tunnel／native の両方に対応。`strictMode.egress.allowRemoteNodeIdentities` は egress 設定で、tunneling 使用時または direct routing で node CIDR と Pod CIDR が重複する場合に必要。旧 key を置き換えた `strictMode.egress.*` が1.20で導入され、旧 key は削除済み | なし |
| Bandwidth manager | 対応 | 通知なしで無効化 |
| BIG TCP | 注意事項付きで対応 | 起動 error |
| Chaining | 暗号化非対応 | 暗号化非対応 |

その他の事実：IPsec の `encryptedOverlay` は1.18から何もしなくなり、1.20で削除されました。IPsec は direct-routing のすべての構成で `ipv4NativeRoutingCIDR` が必要です。node 数は65535未満に制限され、各 tunnel の復号は単一 core で行われます。XDP が高速化する north/south traffic と Geneve 以外の DSR traffic は WireGuard 対象外です。Geneve DSR は対象です。

packet capture の順序に注意してください。NIC では VXLAN／Geneve ではなく UDP 51871 または ESP が見え、Pod の host-side device では平文が見えます。暗号化または encapsulation が欠けていると判断する前に、両方の位置で capture してください。

## 15. VTEP と multicast（beta）

**VTEP integration** を使うと、Pod と外部 VXLAN endpoint（hardware VTEP など）の間で traffic を送れます。

- Helm：`vtep.enabled`、`vtep.endpoint`、`vtep.cidr`、`vtep.mask`、`vtep.mac`。`vtep.endpoint`、`vtep.cidr`、`vtep.mac` は同じ長さの空白区切り list（VTEP ごとに1項目）、`vtep.mask` はすべての CIDR に適用する mask 1つです。
- 制限：VTEP は最大8つ、IPv4 のみ、同期間隔は `--vtep-sync-interval`（1分）、IPsec と併用不可。VTEP device の MTU は1500 - 50に固定されています。
- VTEP device は **VNI 2**（`world`）を使用する必要があります。VTEP source address から届いた overlay packet の VNI が world 以外なら、BPF が `DROP_INVALID_VNI` で破棄します。egress では `bpf_lxc` が `cilium_vtep_map` を検索し、宛先 identity を `world` として encapsulate します。
- `cilium-dbg bpf vtep list` で確認します。Geneve 上で VTEP が動作することは文書化も検証もされていません。文書化された構成は VXLAN を使う tunnel mode です。

**Multicast。**

- `cilium config set multicast-enabled true` または `extraConfig: {multicast-enabled: "true"}` で有効にします。1.20.2 には専用の Helm value がありません。
- ドキュメントでは VXLAN mode が必要で、kernel は amd64 で5.10以降、arm64 で6.0以降とされています。さらに code は `bpf_for_each_map_elem` helper（Linux 5.13以降）を検査します。なければ「Disabled support for BPF Multicast」を agent log に出して無効のままにします。5.10〜5.12ではどちらの要件を優先するか、ここでは検証していません。
- IPv4 のみ。`bpf_lxc` が IGMP v2／v3 を処理します。最大1024 group × 1024 subscriber。IPsec と併用不可。全 node で設定が必要です（`cilium-dbg bpf multicast group add <group>`、`... subscriber add <group> <remote CiliumInternalIP>`、または上流 `multicast.rst` にある `cilium multicast add --group-ip` で cluster-wide に設定。この CLI command は cilium-cli source で確認していません）。

## 16. EKS の選択ガイド

| 選択肢 | 設定 | 選ぶ状況 | 注意点 |
|---|---|---|---|
| **Cilium ENI IPAM**（VPC CNI を置き換え） | `eni.enabled=true`、`ipam.mode=eni`、`routingMode: native`（ENI でのデフォルト）、IRSA／Pod Identity による operator 権限、taint `node.cilium.io/agent-not-ready=true:NoExecute` | Pod に VPC 内で route 可能な IP が必要、VPC 内 SNAT が不要、Pod IP 単位の security group／flow log が必要 | ENI では tunnel 不可。IPv4 masquerade は1.18以降デフォルト off。Pod 密度は ENI／IP capacity に制限。operator に `ec2:DescribeRouteTables` が必要。AWS support の対象は EC2 node 上の VPC CNI のみ |
| **EKS 上の overlay** | `ipam.mode=cluster-pool`、`routingMode: tunnel`、`eni.enabled=false` | VPC 内で Pod IP が不足、または tunnel 機能を使用 | Pod IP は VPC 内で route 不可のため、managed control plane から到達できません。**admission／conversion webhook backend は `hostNetwork` を使う必要があります**。Node SG で UDP 8472（または6081）の自己参照を追加。MTU 1450（underlay 9001なら8951） |
| **VPC CNI chaining** | `cni.chainingMode=aws-cni`、`cni.exclusive=false`、`enableIPv4Masquerade=false`、`routingMode=native` | VPC CNI の IPAM と ENI を維持したまま Cilium policy、LB、Hubble を追加 | chart が legacy host routing を強制し、no-conntrack iptables を無効化。IPsec／WireGuard 不可。L7 は制限あり。aws-node 1.11.2以降。有効化後に Pod を再起動 |
| **EKS Auto Mode／Fargate** | 該当なし | 該当なし | 別の CNI はサポートされない |
| **EKS Hybrid Nodes** | Cilium は対応 CNI | On-premises node | webhook 用に Pod CIDR の routing が必要。repository の EKS Hybrid Nodes 節を参照 |

Overlay webhook に関する記述は、webhook 用 Pod CIDR の到達性を求める AWS hybrid-nodes guidance と、Kubernetes control plane が webhook を呼び出す方式から導いたものです。依存する前に Lab 5 で検証してください。

Cilium ENI profile（masquerade 無効時に機能しない `egressMasqueradeInterfaces` key は意図的に省略）：

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
# enableIPv4Masquerade: true   # only if Pods must reach non-VPC destinations without a NAT gateway
```

VPC CNI chaining：

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native
```

EKS に関する補足：

- Cilium を CNI としてインストールする前に `aws-node` DaemonSet を削除します（aws-node は routing table を flush するため）。または、その後で Pod を再起動します。
- Secondary VPC CIDR（例：100.64.0.0/16）：自動検出される native-routing CIDR は**primary** VPC CIDR のみです。masquerade が有効で Pod が secondary range にいる場合は、`ipv4NativeRoutingCIDR` にその range を含む値を設定し、`cilium-dbg status | grep Masquerading` で確認してください。code から導出した内容であり、テストされていません。
- ENI IPv6：`eni.rst` は node ごとの /80 prefix と dual-stack subnet を文書化していますが、EKS requirements page は依然として IPv4 のみと記載しています。上流で扱いが確定していないため、利用する region で確認してください。
- Source／destination check：DSR では無効化必須と文書化されています。ENI 非接続 EC2 の native routing でも、原則は同じ制約です（Pod IP を instance が所有しないため）。この部分は推論です。
- Public path policy：CloudFront VPC origin の背後にある internal ALB／NLB に CloudFront だけが到達します。この章の Cilium 例では public listener や `0.0.0.0/0` rule は不要です。

## 17. 調査用チートシート

```bash
# Effective routing, device, host-routing, masquerade, KPR, bandwidth, BIG TCP, XDP
kubectl -n kube-system exec ds/cilium -c cilium-agent -- \
  cilium-dbg status --verbose | grep -E "Routing|Device Mode|Masquerading|KubeProxyReplacement|BandwidthManager|BIG TCP|XDP"

# Tunnel device (VNI mode, port, metadata-based)
ip -d link show cilium_vxlan        # or cilium_geneve
ip route | grep cilium_host         # remote PodCIDR routes (tunnel mode)

# Tunnel endpoints and node IDs (ipcache, not the old tunnel map)
cilium-dbg bpf ipcache list | grep -i <remote-node-ip>
cilium-dbg bpf nodeid list
cilium-dbg node list

# Identity numbers to compare with the VNI
cilium-dbg endpoint list
cilium-dbg identity list

# NAT and masquerade
cilium-dbg bpf nat list
cilium-dbg bpf ipmasq list

# Services
cilium-dbg service list
cilium-dbg bpf lb list
cilium-dbg bpf lb maglev list
cilium-dbg bpf socknat list

# Bandwidth, VTEP
cilium-dbg bpf bandwidth list
cilium-dbg bpf vtep list

# Datapath events
cilium-dbg monitor -v --type trace      # to-overlay / from-overlay trace points
cilium-dbg monitor --type drop

# Wire capture on the node (not on your laptop)
sudo tcpdump -nni any -c 50 'udp port 8472'      # Geneve: 'udp port 6081'
sudo tcpdump -nni <nic> -vv 'udp port 8472'       # -vv prints the VNI
```

`cilium-dbg status` の `Routing:` 行には、`Network: Tunnel [vxlan]  Host: BPF` のような値が表示されます。map 内容を出力する command の列構成は version により異なる場合があります。列位置に依存する script を作らないでください。

## 18. 演習

使い捨て cluster（kind、または self-referencing security group を設定した2-node EKS test cluster）でのみ実施してください。各項目は上流 source と文書に照らして確認しましたが、このレビューでは live cluster で実行していません。期待する結果を記載しており、実測値ではありません。

### Lab 1: Overlay の構造と VNI

**前提条件：** schedulable な Linux node が2つ、`routingMode: tunnel` の Cilium 1.20.2、node への shell access、node 間 UDP 8472 を許可。

1. agent 上で `cilium-dbg status | grep Routing` を実行します。VXLAN protocol の tunnel network が表示されます。
2. node 上で `ip -d link show cilium_vxlan` を実行します。flow-based（external）attribute と destination port 8472 を持つ VXLAN device が表示されます。
3. node 1 に server Pod、node 2 に client Pod を起動します（`nodeName` または anti-affinity を利用）。client から server に curl している間、node 上で `sudo tcpdump -nni <nic> -vv 'udp port 8472' -c 20` を実行します。
4. decode 結果にある `vni` を確認します。node 2 の `cilium-dbg endpoint list` で client Pod の identity を調べ、値を比較してください。client から server への packet は client の identity と一致し、返信は server の identity と一致します。
5. `helm upgrade ... --set tunnelProtocol=geneve` を実行して agent を再起動します。`cilium_vxlan` が消え、`cilium_geneve` が作られること、capture filter を port 6081 に変える必要があることを確認します。

**後片付け／ロールバック：** `tunnelProtocol` を `vxlan` に戻し、agent を再起動します。protocol の変更は device を作り直すため、その間に node 間の接続が短時間失われます。

### Lab 2: Tunnel 上の WireGuard の MTU

**前提条件：** Lab 1 の cluster。node 間 UDP 51871 を許可（security group で自己参照）。

1. `encryption.enabled=true`、`encryption.type=wireguard` を有効にし、`MTU: 0` のままにします。
2. Pod 内で `ip route` と `ip link` を実行します。device の MTU は underlay 値、underlay 1500の場合の route MTU は1355（overhead は95 + 50）となるはずです。
3. 一方の Pod から `ping -M do -s 1327 <other pod ip>` と `-s 1328` を実行します。前者は成功します（1327 + 28 = 1355）。後者は fragmentation-needed 相当の error で失敗します。
4. `cilium-dbg status | grep Encryption` で WireGuard が表示されることを確認します。

**後片付け：** 暗号化を無効にして agent を再起動します。新しい Pod の route MTU は1450に戻ります（既存 Pod の MTU は再作成するまで変わりません）。

### Lab 3: Masquerade の判断を確認

**前提条件：** KPR 有効、`bpf.masquerade=true`。同じ VPC 内で、node SG を参照する security group 経由でのみ接続でき、観測した source IP を log に記録する test echo server。

1. Pod から echo server に接続します。echo server の IP が native-routing CIDR と ip-masq-agent list の範囲外なら、観測される source は node IP となるはずです。
2. echo server の range を `nonMasqueradeCIDRs` に含む ip-masq-agent を有効にして agent を再起動し、再試行します。Pod IP が維持されるはずです（VPC は Pod IP への戻り traffic を route できる必要があります。overlay の Pod IP では失敗し、これが確認の目的です）。
3. `cilium-dbg bpf ipmasq list` で CIDR を、`cilium-dbg bpf nat list` で有効な SNAT entry を表示します。
4. Pod から remote node に通信します。native mode では source は Pod IP、tunnel mode では node IP です。`extraConfig: {enable-remote-node-masquerade: "true"}` を設定すると native mode でも masquerade されることを確認します。

**後片付け／ロールバック：** ip-masq-agent block と extraConfig key を削除します。masquerade mode の変更は firewall から見える source address を変えるため、node 単位で段階的に行います。

### Lab 4: Maglev と Geneve DSR を使った kube-proxy 不要の Service

**前提条件：** kube-proxy なしで導入した cluster、`routingMode: tunnel`、`tunnelProtocol: geneve`、KPR 有効、`loadBalancer.mode: dsr`、`dsrDispatch: geneve`、セクション12の `maglev` 設定。VPC 内に client host を置き、接続先 node と別の node に backend がある NodePort Service を用意します。内部 network のみを使ってください。

1. 接続先 node 上で `iptables-save | grep KUBE-SVC` を実行し、何も返らないことを確認します。
2. `cilium-dbg bpf lb list` で Service を、`cilium-dbg bpf lb maglev list` で lookup table を確認します。
3. backend node の NIC 上で tcpdump を使います。request は DSR option を持つ Geneve（UDP 6081）で届き、reply は Service IP を source として client へ直接返るはずです。
4. 使い捨て cluster で `tunnelProtocol: vxlan` と `loadBalancer.mode: dsr` を設定すると、agent が起動時に失敗することを確認してから値を戻します。

**後片付け：** Helm 値を戻します。稼働中の cluster で mode を切り替えると DSR flow が中断します。

### Lab 5: netkit／auto、host routing、EKS ENI

**前提条件：** (a) kernel 6.8以降の node と、それより古い node。(b) ENI の項目では `aws-node` なしで作成した使い捨て EKS cluster。

1. `bpf.datapathMode=auto`、`bpf.masquerade=true`、`kubeProxyReplacement=true` を設定し、新旧 kernel の node で `cilium-dbg status | grep -E "Device Mode|Routing"` を比較します。新しい方は `Device Mode` が netkit、古い方は fallback log とともに veth になるはずです。どちらも `Routing:` 行は `Host: BPF` です。veth Pod がすでにある node を切り替えないでください。先に drain します。
2. `bpf.masquerade=false` にすると `Routing:` 行が `Host: Legacy` で終わり、fallback を記録する agent log が表示されるはずです。確認後は元に戻します。
3. bandwidth manager を有効にした Pod に `kubernetes.io/egress-bandwidth: "10M"` を設定し、`cilium-dbg bpf bandwidth list` に表示されることを確認します。
4. ENI：セクション16の ENI profile で導入します。`ip rule` に Pod IP ごとの ingress rule `to <podIP> lookup main`（priority 20）と egress rule `from <podIP> lookup <ENI table>`（priority 111）、ENI ごとの route table が表示されます。ENI はデフォルトで masquerade を無効にするため、masquerade を有効化しない限り egress rule に `to <VPC CIDR>` はありません。scratch cluster で ENI のまま `routingMode: tunnel` を試し、agent が起動を拒否することを確認します。
5. EKS 上の overlay：通常の Pod が backend の validating webhook を使うよう deploy し、API server から到達できるかを確認します。その後 `hostNetwork` に変更します。

**後片付け：** test workload を削除し、Helm 値を戻し、scratch cluster を終了します。稼働中 cluster の CNI を入れ替える作業は対象外であり、ここではサポート対象の in-place 移行とはしていません。

## 19. バージョン差分

| 項目 | 1.18 | 1.19 | 1.20 | 1.21-pre.3 |
|---|---|---|---|---|
| Kernel 最低要件 | 5.10（RHEL 8.10 は4.18） | 同じ | 同じ | 同じ |
| `cilium_tunnel_map` | datapath から削除（agent は残存 map の pin を解除）、CLI も削除 | Go package **削除**。tunnel endpoint は ipcache value | 該当なし | 該当なし |
| `underlayProtocol`（IPv6 underlay） | **追加** | stable | 同じ | IPv6 overhead の MTU 計算で tunneling flag を使用 |
| ENI 時の `enableIPv4Masquerade` | デフォルト **false** | 同じ | 同じ | 同じ。IPv6 masquerade のデフォルトは ENI 以外で true |
| `bpf.datapathMode` | veth、netkit、netkit-l2 | tproxy は netkit と非互換 | **`auto`** 追加。status に設定値と実効値 | 同じ |
| BPF host routing + IPsec | 該当なし | IPsec + KPR + BPF masquerade 時に自動使用（CVE-2025-37959 の修正が必要） | 同じ | 同じ |
| `enable-remote-node-masquerade` | 該当なし | **追加** | 同じ | 同じ |
| `packetizationLayerPMTUDMode` | 該当なし | **追加**。デフォルト `blackhole` | 同じ | 同じ |
| WireGuard strict mode | 旧 key | `strictMode.ingress` **追加** | 旧 `strictMode.enabled/cidr` key **削除** | 同じ |
| IPsec `encryptedOverlay` | no-op | 非推奨 | **削除** | 該当なし |
| DSR dispatch | `opt`／`ipip`／`geneve` flag はあるが、IPIP は未文書化 | 同じ | IPIP を文書化。per-service DSR／algorithm annotation、`bpf-lb-rss-*`、`service.cilium.io/weight` | 同じ |
| 削除された flag | 該当なし | `--enable-node-port/host-port/external-ips` | `--node-port-mode`、`--node-port-algorithm` | 該当なし |
| Pod-to-NodePort と Socket-LB | 該当なし | trace format 変更 | socketLB 無効または `hostNamespaceOnly` 時は client egress で DNAT | 同じ |
| `nativeRoutingCIDRFromClusterPool`、`nodePort.enableDynamicSourceLookup` | 該当なし | 該当なし | **追加** | 同じ |
| `nodePort.extendedNATPortRange` | 該当なし | 該当なし | 該当なし | **[1.21 pre-release] で追加** |
| `l2NeighDiscovery.enabled` のデフォルト | false（以前は true） | 同じ | 同じ | 同じ |
| tunnel + `autoDirectNodeRoutes` の message | 「cannot be used with tunneling」 | 同じ | 同じ | 「requires native routing mode」 |

成熟度：stable は tunnel、native、BPF masquerade（IPv4）、KPR、Maglev、DSR、XDP acceleration、bandwidth manager、BBR、BIG TCP。beta は netkit、IPv6 BPF masquerade、VTEP、multicast、fragment tracking。削除済みは `cilium_tunnel_map`、`encryptedOverlay`、`--node-port-mode`。

## 20. トラブルシューティング

| 症状 | 考えられる原因 | 確認／対処 |
|---|---|---|
| 「cannot be used with tunneling」で agent が起動時に終了 | tunnel と `autoDirectNodeRoutes` の併用 | native routing にするか flag を削除 |
| 「Cannot specify IPAM mode eni in tunnel mode」で agent が終了 | ENI IPAM と tunnel の併用 | `routingMode: native` を使う |
| 別 node 間だけ Pod traffic が失敗し、同一 node 間は動作 | UDP 8472／6081 が遮断、tunnel port 間違い、node SG の自己参照なし | 両 node で `tcpdump -nni <nic> 'udp port 8472'`。SG／NACL と `Routing:` 行を確認 |
| 大きな転送が停止し、小さな request は成功 | MTU black hole（tunnel overhead、ICMP filter） | Pod の `ip route` MTU と path MTU を比較、`ping -M do -s`。`pmtuDiscovery` 設定を検討 |
| native Pod から外部へ通信できるが source IP が Pod IP で、返信が戻らない | masquerade 無効（ENI のデフォルト）、または宛先が native-routing CIDR 内 | `cilium-dbg status | grep Masquerading`。意図した方法で masquerade または ip-masq-agent を有効化 |
| cluster ごとに Pod-to-remote-node の source IP が違う | tunnel mode は masquerade し、native mode はしない（セクション9） | 意図した方式を決める。統一する場合は `enable-remote-node-masquerade` |
| Agent log に「Falling back to legacy host routing」 | iptables masquerade または KPR 無効 | `bpf.masquerade` と KPR を有効にするか、legacy routing を受け入れる |
| Istio sidecar traffic を迂回または破損 | Pod namespace の BPF host routing／socket-LB | `socketLB.hostNamespaceOnly=true` または `bpf.hostLegacyRouting=true` |
| `bpf.datapathMode=netkit` が失敗 | kernel、legacy routing、iptables masquerade、KPR 無効、tproxy などの前提不足 | `auto` で probe するか、前提を満たす |
| Agent が DSR を拒否 | VXLAN tunnel、Geneve dispatch の設定不足 | `tunnelProtocol: geneve` と `dsrDispatch: geneve` を使用 |
| node 変更後に Service flow が断続的に reset | Agent 間の Maglev seed 不一致 | すべての node で `maglev.hashSeed` を一致させる |
| NodePort traffic が `tcpdump` に出ない | XDP acceleration | 別の場所で capture するか、debug 中だけ acceleration を無効にする |
| EKS overlay で webhook timeout | API server から VPC 外の Pod IP に到達できない | webhook backend に `hostNetwork` を使用 |
| NIC 上に暗号化済み packet がない | Bandwidth manager と IPsec／WireGuard の相互作用、または XDP／非 Geneve DSR 経路 | `cilium-dbg status | grep Encryption` とセクション14の表を確認 |

一般的な調査手順：(1) `cilium-dbg status --verbose` で実効設定を確認。(2) `cilium-dbg monitor --type drop` で drop 理由（`DROP_INVALID_IDENTITY`、`DROP_INVALID_VNI` など）を確認。(3) `cilium-dbg bpf ipcache list` に宛先と正しい tunnel endpoint があることを確認。(4) 両 node の NIC と `cilium_vxlan`／`cilium_geneve` 上で capture。(5) 起動時 fallback を含め agent log を確認。

## 21. 検証範囲と情報源

この章の演習は、このレビューでは live cluster に対して実行していません。以下の tag の上流 source とドキュメントで、演習と上記の各動作に関する記述を確認しました。本文中で推論とした項目があります。EKS overlay の webhook 到達性、ENI 非接続 instance における EC2 source／destination check と native routing の関係、secondary VPC CIDR での native-routing behavior、Geneve 上の VTEP、kernel 5.10〜5.13間の multicast 最低条件（未検証）です。1.21 pre-release の tree にある別 routing mode の土台は意図的に説明していません。

MTU 表の値は source の定数から算出したもので、実測値ではありません。

情報源（特記がない限り v1.20.2）：

- [Routing](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst)、[masquerading](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst)、[tuning](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst)、[system requirements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Kube-proxy replacement](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst)、[bandwidth manager](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst)、[VTEP](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/vtep.rst)、[multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst)、[ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)、[AWS CNI chaining](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/cni-chaining-aws-cni.rst)
- [Tunnel／overlay BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_overlay.c)、[lxc BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_lxc.c)、[identity helper](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/identity.h)、[NAT](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/nat.h)、[tunnel option](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/tunnel.h)、[MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go)、[起動時検証](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go)、[KPR 検証](https://github.com/cilium/cilium/blob/v1.20.2/pkg/kpr/initializer/kube_proxy_replacement.go)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- Pre-release：[v1.21.0-pre.3 の daemon_main.go](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/daemon/cmd/daemon_main.go)、[v1.21.0-pre.3 の values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- AWS：[EKS alternate CNI plugins](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)

## クイズ

[Overlay と native routing の理解度を確認](../../quizzes/networking/cilium/09-overlay-native-routing-quiz.md)してください。

[メインページに戻る](README.md)
