# Part 11: BGP Control Plane、Load Balancer IP、Egress

> **レビュー基準**: Cilium 1.20.2（stable、2026-09-16）、Cilium CLI 0.20.1、Hubble CLI 1.20.2。**[1.21 pre-release]** と記した項目は v1.21.0-pre.3 に基づき、GA 前に変更される可能性があります。
> **最終更新日**: 2026年10月15日

この章では、Cilium cluster を Pod network の**外側**につなぐ機能を扱います。BGP Control Plane による route 広報、LoadBalancer IP の割り当てと広報（LB IPAM、L2 announcements、Node IPAM）、送信 traffic の経路制御（Egress Gateway）、node 内 backend Pod への traffic interception（Local Redirect Policy）、近い backend の優先（traffic distribution）、L7 の入口（Ingress、Gateway API）を説明します。最後に、BGP を使うオンプレミス ToR switch と、CloudFront の背後に置く EKS の2つの構成例を示します。

関連章：[IPAM deep dive](10-ipam-deep-dive.md)（BGP が広報できる範囲を決める Pod IPAM）、[overlay and native routing](09-overlay-native-routing.md)、[eBPF datapath internals](08-ebpf-datapath-internals.md)（後述の Service load balancing が依存する kube-proxy replacement）、[ClusterMesh and upgrade](13-clustermesh-install-upgrade.md)。

## 1. north-south traffic の位置づけ

「load balancer」とひとまとめにされがちですが、役割は3つに分かれます。

| 役割 | 答える問い | Cilium の component |
|---|---|---|
| Address allocation | Service にどの IP を割り当てるか | LB IPAM（`CiliumLoadBalancerIPPool`）、Node IPAM、cloud controller |
| 到達性 | 外部 network は、その IP がどの node にあると知るか | BGP Control Plane、L2 announcements、cloud load balancer |
| Load balancing | packet が node に到着した後、どの backend Pod に送るか | eBPF Service load balancing（kube-proxy replacement）、L7 用 Envoy |

したがって BGP Control Plane、L2 announcements、LB IPAM は**独立した**機能であり、組み合わせて使います。オンプレミスでよく使う組み合わせは、VIP を割り当てる `LB IPAM`、それを広報する `BGP Control Plane`、traffic を分配する eBPF kube-proxy replacement です。どの機能が Service を管理するかは、Service の `loadBalancerClass` で決まります（section 6）。

**BGP が行わないこと。** BGP Control Plane の役割は route の *広報* だけです。local datapath を設定せず、peer から学習した route を kernel や eBPF map にインストールしません。cluster 内の到達性を作る機能でもありません（[upstream overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)）。node 間の Pod-to-Pod routing は overlay routing または native routing の役割です（[Part 9](09-overlay-native-routing.md)）。

## 2. BGP Control Plane v2

**成熟度**: 1.19、1.20、1.21-pre では v2（`cilium.io/v2` CRD）のみが BGP Control Plane として使えます。v1 の `CiliumBGPPeeringPolicy` は1.19で削除されました（section 2.9）。

### 2.1 アーキテクチャ

```
                     user-authored (cluster-scoped, cilium.io/v2)
   +--------------------+   +-------------------+   +----------------------+
   | CiliumBGPCluster   |-->| CiliumBGPPeer     |   | CiliumBGPAdvertise-  |
   | Config             |   | Config            |<--| ment (matched by     |
   |  nodeSelector      |   |  timers, GR, MD5, |   |  LABEL from PeerCfg) |
   |  bgpInstances[]    |   |  families[]       |   +----------------------+
   |  peers[] -> ref    |   +-------------------+
   +---------+----------+
             | watched by cilium-operator
             v
   +--------------------+   (one per selected node, name == node name,
   | CiliumBGPNodeConfig|    read-only for users; status reports sessions)
   +---------+----------+   +--------------------------+
             | watched by   | CiliumBGPNodeConfig-     |  optional per-node
             | the node's   | Override (name == node)  |  routerID/ASN/source
             v agent        +--------------------------+
   +--------------------------------------------+
   | cilium-agent: BGP "router manager"         |
   |   one embedded GoBGP instance per bgpInstance
   |   inputs: NodeConfig, PeerConfig, Advert., |
   |   Secret, Services/EndpointSlices/backends,|
   |   CiliumNode PodCIDRs / CiliumPodIPPool    |
   +----------------------+---------------------+
                          | TCP/179 (agent dials out; active-only by default)
                          v
                    ToR / upstream router
```

制御フロー（[`pkg/bgp/README.md`](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/README.md) に基づく）：operator は `CiliumBGPClusterConfig` と、そこから参照される `CiliumBGPPeerConfig`／`CiliumBGPAdvertisement` object を監視します。cluster config の `nodeSelector` に一致する node ごとに `CiliumBGPNodeConfig` を作成・更新・削除します。各 agent が監視するのは、自身の `CiliumBGPNodeConfig`、peer／advertisement config、Secret、Service、および multi-pool の場合は `CiliumPodIPPool` で、それらをもとに GoBGP instance を reconcile します。そのため、config の変更を反映するには operator が稼働している必要があります。

speaker は agent に組み込まれた GoBGP です。router 実装としてサポートされるのは GoBGP のみです。組み込み library は1.19の `gobgp/v3` から1.20.2および1.21.0-pre.3の `gobgp/v4` に移行しました（各 tag の `go.mod` を参照）。IPv4／IPv6、single stack／dual stack をサポートしますが、agent 自身で有効な address family だけを広報できます。

### 2.2 有効化

```yaml
bgpControlPlane:
  enabled: true              # default false
  statusReport:
    enabled: true            # default true; disable on very large clusters to cut API load
  routerIDAllocation:
    mode: default            # default | ip-pool
```

```bash
helm upgrade cilium cilium/cilium -n kube-system --reuse-values \
  --set bgpControlPlane.enabled=true
kubectl -n kube-system rollout restart ds/cilium deploy/cilium-operator
```

| Helm value | Agent／operator flag | Default | 意味 |
|---|---|---|---|
| `bgpControlPlane.enabled` | `--enable-bgp-control-plane` | `false` | 機能を有効にする |
| `bgpControlPlane.secretsNamespace.name`／`.create` | `--bgp-secrets-namespace` | `kube-system`／`false` | `authSecretRef` の Secret を読み取る namespace。chart で作成可能 |
| `bgpControlPlane.statusReport.enabled` | `--enable-bgp-control-plane-status-report` | `true` | session 状態を `CiliumBGPNodeConfig.status` に書き込む。無効にすると status を消去 |
| `bgpControlPlane.routerIDAllocation.mode`／`.ipPool` | `--bgp-router-id-allocation-mode`／`-ip-pool` | `default`／空 | Router ID の選択方法（section 2.7） |
| `bgpControlPlane.legacyOriginAttribute.enabled` | `--enable-bgp-legacy-origin-attribute` | `false` | `LoadBalancerIP` route の ORIGIN を `IGP` ではなく `INCOMPLETE` にする（MetalLB 互換） |
| `enableNoServiceEndpointsRoutable` | `--enable-no-service-endpoints-routable` | `true` | backend が0件の Cluster-policy VIP の広報を維持するか（section 2.5） |

`bgpControlPlane.*` value は1.18.14、1.19.8、1.20.2、1.21.0-pre.3で同じです（各 tag の `values.yaml` を比較）。**[1.21 pre-release]** では BGP flag が `pkg/bgp/config` module に移され、router ID flag を含む同じ flag が operator にも追加されました。Helm の設定方法は変わりません。

TCP/179 で listen する設定は任意です。既定では `bgpInstance` に `localPort` がなく、agent は **active-only** で peer への発信接続だけを行います。`localPort: 179` を設定する場合、chart の `securityContext.capabilities.ciliumAgent` list から `CAP_NET_BIND_SERVICE` を付与する必要があります。高い port 番号を使えば capability は不要です。

### 2.3 5種類の CRD

すべて cluster-scoped の `cilium.io/v2` です。同じ kind の `cilium.io/v2alpha1` 版は**非推奨**です（`+kubebuilder:deprecatedversion` が付いており、1.20.2と1.21.0-pre.3では引き続き serve されています）。新規 manifest はすべて `cilium.io/v2` で記述してください。

| Kind | Short name | 作成者 | 目的 |
|---|---|---|---|
| `CiliumBGPClusterConfig` | `cbgpcluster` | user | BGP instance と peer を動かす node を指定 |
| `CiliumBGPPeerConfig` | `cbgppeer` | user | session parameter と、peer に送る advertisement を指定 |
| `CiliumBGPAdvertisement` | `cbgpadvert` | user | 広報内容と attribute を指定 |
| `CiliumBGPNodeConfig` | `cbgpnode` | operator（user は read-only） | node ごとに解決された config と session status |
| `CiliumBGPNodeConfigOverride` | `cbgpnodeoverride` | user | node ごとの Router ID、ASN、port、source address |

object 間の関連付けには2種類の方法があり、間違いやすい点です。

```
CiliumBGPClusterConfig.spec.bgpInstances[].peers[].peerConfigRef.name  --by NAME-->  CiliumBGPPeerConfig
CiliumBGPPeerConfig.spec.families[].advertisements (label selector)    --by LABELS-> CiliumBGPAdvertisement.metadata.labels
```

peer config は `CiliumBGPAdvertisement` object の **label** と照合して advertisement を選びます。spec の内容とは照合しません。複数の advertisement object が1つの peer に一致する場合があります。一致する advertisement がない場合、session は確立しても何も広報されません。

#### CiliumBGPClusterConfig

| Field | Type／制限 | 説明 |
|---|---|---|
| `spec.nodeSelector` | LabelSelector | nil または空なら**全 node**を選択。node が一致できる `CiliumBGPClusterConfig` は1つだけ |
| `spec.bgpInstances[]` | 1～16件、key は `name` | それぞれ GoBGP instance を1つ作成 |
| `.name` | 1～255文字、一意 | override から参照し、metric では `instance_name` として表示 |
| `.localASN` | 1～4294967295 | 省略可能。node ごとの値を override で指定可 |
| `.localPort` | 1～65535 | 未設定なら instance は listen しない |
| `.peers[]` | key は `name` | |
| `.peers[].peerAddress` | IPv4 または IPv6 | `autoDiscovery` 使用時のみ省略可 |
| `.peers[].peerASN` | 0～4294967295、default 0 | 0なら peer の OPEN message に対する ASN 検証を省略 |
| `.peers[].autoDiscovery` | `mode: DefaultGateway`、`defaultGateway.addressFamily: ipv4\|ipv6` | node の default gateway を peer にする（下記参照） |
| `.peers[].peerConfigRef.name` | string | `cilium.io/v2` に存在するのは `name` のみ。`group`／`kind` は非推奨の v2alpha1 CRD にのみ存在 |

cluster config の status condition：`cilium.io/NoMatchingNode`、`cilium.io/MissingPeerConfigs`、`cilium.io/ConflictingClusterConfig`（複数 config が同じ node を選択した場合、operator は後から適用された方を拒否）。

**Auto-discovery（`DefaultGateway`）。** 固定の `peerAddress` ではなく node の default gateway と peer 接続します。ToR は dynamic neighbor（FRR の `bgp listen range`）を使い、すべての ToR で同じ local ASN を使う必要があります。link-local の default gateway は非対応です。複数の default route がある場合（multihoming）、Cilium は address family ごとに1つの session を作成し、metric が低い route を使います。障害時にはもう一方へ切り替えますが、この方法では同じ family に2つの session を維持できません。2つの session が必要なら固定の `peerAddress` entry を使ってください。

#### CiliumBGPPeerConfig

| Field | Default／制限 | 説明 |
|---|---|---|
| `spec.transport.peerPort` | 179（1～65535） | remote port |
| `spec.transport.sourceInterface` | なし | この interface の source IP を使う。family ごとに有効な address は最大1つ（loopback、multicast、IPv6 link-local を除く）。interface がない場合、Cilium は egress interface を自動検出する。1.18の文書にはなく、1.19以降に存在 |
| `spec.timers.connectRetryTimeSeconds` | 120（最小1） | jitter を加えるため実効 retry は `[N, 2N)` |
| `spec.timers.holdTimeSeconds` | 90（3～65535） | hold または keepalive の変更で session が reset |
| `spec.timers.keepAliveTimeSeconds` | 30（1～65535） | CRD rule: keepalive <= holdTime |
| `spec.authSecretRef` | なし | BGP secrets namespace にある Secret 名。key は `password`（RFC 2385 TCP MD5） |
| `spec.gracefulRestart.enabled` | block を指定する場合は必須 | |
| `spec.gracefulRestart.restartTimeSeconds` | 120（1～4095） | |
| `spec.ebgpMultihop` | 1（1～255） | default TTL は1。iBGP では無視 |
| `spec.families[]` | afi、safi、`advertisements` selector | 対応 family は `ipv4/unicast` と `ipv6/unicast` のみ。`families` を省略すると両方の unicast family を交渉するが、advertisement は行わない |

Status condition：`cilium.io/MissingAuthSecret`。

> **上流資料の補足。** 上流の設定ページには、最小の「possible」値として `holdTimeSeconds=9`、`keepAliveTimeSeconds=3` と記載されています。CRD の最小値は hold >= 3、keepalive >= 1（かつ keepalive <= hold）です。9/3は低遅延向けに推奨される値であり、下限ではありません。

#### CiliumBGPAdvertisement

`spec.advertisements[]` の entry：

| Field | 説明 |
|---|---|
| `advertisementType` | `PodCIDR`、`CiliumPodIPPool`、`Service`、`Interface` |
| `service.addresses[]` | `LoadBalancerIP`、`ClusterIP`、`ExternalIP` のいずれか1つ以上。type が `Service` の場合は必須 |
| `service.aggregationLengthIPv4`／`IPv6` | 0～31／0～127。/32、/128ではなく集約する prefix length |
| `interface.name` | type が `Interface` の場合は必須 |
| `selector` | Service（または pool）を選択する LabelSelector。未設定なら `PodCIDR` 以外は何も選択しない。`PodCIDR` では設定不可 |
| `attributes.communities` | `standard[]`、`wellKnown[]`、`large[]` |
| `attributes.localPreference` | iBGP peer にのみ送信 |

CEL validation は `Service` に `service`、`Interface` に `interface` が必要であること、および `PodCIDR` に `selector` を設定できないことを検証します。

#### CiliumBGPNodeConfig（operator の出力）

`spec` は解決済み config を反映し、`routerID` と `localAddress` を追加します。`status.bgpInstances[].peers[]` には `name`、`peerAddress`、`peerASN`、`peeringState`、`establishedTime`、`timers.appliedHoldTimeSeconds`／`appliedKeepaliveSeconds`、`routeCount[]`（afi、safi、received、advertised）が含まれます。reconcile の失敗は `cilium.io/BGPReconcileError` condition に表示されます。agent 内で exec せずに済むため、自動化や alerting ではこれを参照してください。

#### CiliumBGPNodeConfigOverride

`metadata.name` は node 名と**同じでなければなりません**。instance 名と peer 名は cluster config の名前に一致させてください。

| Field | 説明 |
|---|---|
| `spec.bgpInstances[].name` | cluster config の instance 名に一致 |
| `.routerID` | IPv4 address string |
| `.localPort` | listen port の上書き |
| `.localASN` | 1～4294967295。node／rack ごとの ASN を有効化 |
| `.peers[].name` | cluster config の peer 名に一致 |
| `.peers[].localAddress` | source address（したがって egress link）を固定。default は peer 宛ての route lookup |
| `.peers[].localPort` | 接続時に使う source port |

### 2.4 Peer 設定の実際

**Timer。** default は connect-retry／hold／keepalive の順に120／90／30です。BFD がない場合、直接接続されていない peer の唯一の障害検出手段は hold time です。そのため ToR link では9/3などの短い値をよく使います。trade-off は keepalive load の増加と、agent の CPU 停止への感度上昇です。

**Graceful Restart。** `gracefulRestart.enabled: true` の場合、Cilium は Restarting Speaker として動作します（RFC 4724、および Notification 対応の RFC 8538 graceful restart）。agent 再起動時、peer は `restartTimeSeconds` が経過するまで学習済み route を保持します。eBPF datapath は動作を続けるので、agent の upgrade 中に traffic が blackhole になるのを防げます。`restartTimeSeconds` は image pull を含む最悪時の agent restart より長く設定し、upgrade 前に image を pull してください。欠点として、node が実際に停止しても GR は restart time まで route を残すため、その間 `externalTrafficPolicy: Cluster` の VIP traffic が停止済み node に送られることがあります。

**Multihop。** `ebgpMultihop: N` は1 hop より遠い peer（loopback 接続の ToR や route server）との eBGP session の TTL を設定します。iBGP には影響しません。

**MD5。**

```bash
kubectl -n kube-system create secret generic bgp-auth \
  --from-literal=password='<value from your secret store>'
```

`authSecretRef: bgp-auth` で参照します。password が誤っていても authentication error ではなく `dial: i/o timeout` と表示されます。kernel が署名不正の segment を破棄するためです。Secret が存在しなくても session は止まりません。Cilium は**空の** password で処理を続行し、error を log に記録して `cilium.io/MissingAuthSecret` を設定します。session が NAT を通過する場合、MD5 は動作しません。

**BFD 非対応。** 1.18から1.21-preまで、Cilium は BFD をサポートしていません。代替策は hold timer を短くすること、直接接続 link を使うこと（link down 時に TCP が即座に閉じる）、agent 再起動に Graceful Restart を使うこと、resilient hashing／Maglev を使うこと（後述）です。

### 2.5 Route advertisement

#### PodCIDR

node に割り当てられた PodCIDR（pool 全体ではない）を広報します。各 node に PodCIDR を割り当てる IPAM mode、つまり `cluster-pool` と Kubernetes host scope でのみ有効です。**ENI、Azure などの cloud IPAM では `PodCIDR` advertisement は効果がありません**。Pod IP は VPC（または VNet）の address であり、Cilium 所有の node 単位 prefix ではなく、cloud fabric がすでに routing しているためです。[IPAM deep dive](10-ipam-deep-dive.md) を参照してください。

#### CiliumPodIPPool

multi-pool IPAM 用です。`selector` は pool label と照合します。特別な key `io.cilium.podippool.namespace` と `io.cilium.podippool.name` を使うと pool の identity で選択できます。実際に `CiliumNode` に割り当てられた CIDR だけが広報されます。1.20.2では BGP code は `v2alpha1.CiliumPodIPPool` を監視します。**[1.21 pre-release]** では `CiliumPodIPPool` が `cilium.io/v2` に昇格し、BGP も追従します（v1.21.0-pre.3 の `pkg/bgp/manager/reconciler/pod_ip_pool.go`）。

#### Service

default では正確な `/32` または `/128` route を広報します。

| Source | 値の取得元 | 適用する traffic policy |
|---|---|---|
| `LoadBalancerIP` | `.status.loadBalancer.ingress[].ip` | `externalTrafficPolicy` のみ |
| `ExternalIP` | `.spec.externalIPs`（KPR 使用時は `externalIPs.enabled` が必要） | `externalTrafficPolicy` のみ |
| `ClusterIP` | `.spec.clusterIP(s)`（外部からの access には BPF setting「External access to ClusterIP services」が必要） | `internalTrafficPolicy` のみ |

selector の特別な key：`io.kubernetes.service.namespace`、`io.kubernetes.service.name`。

**Traffic policy との連動。**

| Policy | 広報する node |
|---|---|
| `Cluster` | cluster config で選択されたすべての node |
| `Local` | local に ready backend が1つ以上ある node のみ。route は Pod に追従 |

**backend が0件の場合**：`externalTrafficPolicy: Cluster` では、`--enable-no-service-endpoints-routable=true`（default）のとき VIP の広報をすべての node で維持し、false なら取り下げます。`Local` では取り下げます。

**`loadBalancerClass`。** Service class が未設定、または `io.cilium/bgp-control-plane` の場合だけ Cilium が広報します。`service.k8s.aws/nlb` など、別 class が所有する Service は無視します。

**複数 advertisement の一致（1.18以降）。** 1つの Service に複数の advertisement が一致すると、community は**和集合**、`localPreference` は**最大値**になります。1.18より前は最後に一致した値が採用されました。

**Aggregation。** `Local` traffic policy では `aggregationLengthIPv4/6` を無視します。既知の問題は、集約 range 内の未割り当て VIP による routing loop、および異なる attribute を持つ2つの advertisement が同じ aggregate を生成した場合の未定義動作です（[cilium/cilium#37623](https://github.com/cilium/cilium/pull/37623)、[#40585](https://github.com/cilium/cilium/issues/40585)）。

**ECMP。** 同じ VIP を複数 node から広報できますが、router の ECMP path 数上限が適用されます。router が resilient hashing を使わない場合、node 障害で flow が再配置されます。Cilium の Maglev を使うと、`Cluster` policy では node 間で backend の選択を一貫させられます。

#### Interface（1.19以降）

local interface の address を `/32` と `/128` route として広報します。loopback range、multicast、IPv6 link-local、v4-mapped は除外されます。interface は administratively up で、operational status が `up` または `unknown` でなければなりません。Cilium は address を設定しません。node 固有または anycast の安定した address を載せた dummy interface が典型的な用途です。

#### Attribute

| Attribute | 値 |
|---|---|
| `communities.standard` | `"65000:99"` または4-byte decimal |
| `communities.wellKnown` | `internet`、`planned-shut`、`accept-own`、`route-filter-translated-v4`、`route-filter-v4`、`route-filter-translated-v6`、`route-filter-v6`、`llgr-stale`、`no-llgr`、`blackhole`、`no-export`、`no-advertise`、`no-export-subconfed`、`no-peer` |
| `communities.large` | `"A:B:C"` |
| `localPreference` | iBGP のみ。eBGP peer には attribute を含めない |

Cilium は（peer、family、advertisement type）ごとに GoBGP export policy（例：`65000-ipv4-PodCIDR`）と `allow-local` import policy を生成します。これらは内部実装です。v2 CRD には user が使える route-policy、prefix-list、AS-prepend、MED、next-hop の設定は**ありません**。community を接点として使い、ToR 側で community に基づく route-map を実装してください。

### 2.6 完全な設定例：rack ごとに2台の ToR へ eBGP 接続

address と ASN は例です。

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata: {name: rack0}
spec:
  nodeSelector: {matchLabels: {rack: rack0}}
  bgpInstances:
  - name: instance-65001
    localASN: 65001
    peers:
    - {name: tor1, peerASN: 65000, peerAddress: 10.10.0.1, peerConfigRef: {name: tor-peer}}
    - {name: tor2, peerASN: 65000, peerAddress: 10.10.0.2, peerConfigRef: {name: tor-peer}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata: {name: tor-peer}
spec:
  timers: {connectRetryTimeSeconds: 5, holdTimeSeconds: 9, keepAliveTimeSeconds: 3}
  gracefulRestart: {enabled: true, restartTimeSeconds: 120}
  authSecretRef: bgp-auth
  families:
  - afi: ipv4
    safi: unicast
    advertisements: {matchLabels: {advertise: bgp}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata: {name: svc-and-pods, labels: {advertise: bgp}}
spec:
  advertisements:
  - advertisementType: PodCIDR
    attributes: {communities: {standard: ["65001:100"]}}
  - advertisementType: Service
    service: {addresses: [LoadBalancerIP]}
    selector: {matchLabels: {bgp: "true"}}
    attributes: {communities: {large: ["65001:1:100"]}}
```

node ごとの override（node 名を `metadata.name` に指定）：

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPNodeConfigOverride
metadata: {name: <node-name>}
spec:
  bgpInstances:
  - name: instance-65001
    routerID: "192.168.10.1"
    localPort: 1790
    localASN: 65010
    peers:
    - {name: tor1, localAddress: 10.10.0.11}
```

### 2.7 Router ID

| Mode | ID の選択方法 |
|---|---|
| `default` | node の IPv4 address（IPv4／dual-stack）、または IPv6-only node では `cilium_host` MAC の下位32 bit |
| `ip-pool` | `bgpControlPlane.routerIDAllocation.ipPool` の IPv4 CIDR から割り当て |
| 手動（`NodeConfigOverride.routerID`） | `default` mode では検証されない。`ip-pool` mode で pool 内の値なら重複不可 |

### 2.8 状態の確認

**まず status を確認**（exec 不要）：

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements,ciliumbgpnodeconfigs
kubectl get ciliumbgpnodeconfigs <node> \
  -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'
kubectl describe ciliumbgpclusterconfig rack0
```

**CLI。** `cilium bgp peers [-o json|summary] [--node N]` および `cilium bgp routes <available|advertised|received> <afi> <safi>` は1.20.2で動作します。agent REST API を呼び出しますが、これは**1.20で非推奨**です（下記参照）。1.21.0-pre.3 の in-tree source でも CLI は agent pod 内で `cilium bgp peers -o json` を exec します。

**Hive shell（1.20以降に推奨）。** 1.20の upgrade note では、local REST API と `cilium-dbg bgp` command による BGP peer、route、route policy の一覧表示は非推奨になり、BGP hive shell command が推奨されています。agent binary は `cilium-dbg` です。

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/peers
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/routes out ipv4 unicast
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/route-policies
```

| Command | 意味 |
|---|---|
| `bgp/peers [-f table\|table-json\|json\|detailed] [-o file] [--no-uptime]` | session table |
| `bgp/routes <loc\|in\|out> <afi> <safi> [-a\|--with-attrs] [--no-age] [-f ...]` | `loc` = Loc-RIB、`in` = Adj-RIB-In、`out` = Adj-RIB-Out |
| `bgp/route-policies [-i instance]` | Cilium が生成した export／import policy |

同じ3つの command が1.20.2と1.21.0-pre.3にあります（`pkg/bgp/commands/cell.go`）。`cilium` CLI に `shell` subcommand はありません。agent pod 内で `cilium-dbg` を使ってください。

**Log。** Agent は `subsys=bgp-control-plane`、operator は `subsys=bgp-cp-operator`。

**Metric**（agent、prefix `cilium_bgp_control_plane_`）：`session_state`（1 = established）、`advertised_routes`、`received_routes`（label は `instance_name`、`local_asn`、`neighbor`、`neighbor_asn`、`afi`、`safi`）、`reconcile_errors_total{instance_name}`、`reconcile_run_duration_seconds{instance_name}`。Operator metric：`cilium_operator_bgp_control_plane_reconcile_errors_total{resource_kind,resource_name}` と `..._reconcile_run_duration_seconds`。

> **Metric label の変更。** 1.19.8の metric page は `vrouter` label を記載していますが、1.20.2では `instance_name` です。1.20 upgrade note に rename の記載がないため、1.19から1.20へ upgrade すると `vrouter` を使う dashboard と alert は一致しなくなります。upgrade 時に更新してください。

### 2.9 v1 の削除と CRD version の推移

| Release | 状態 |
|---|---|
| 1.18 | `CiliumBGPPeeringPolicy`（v1）は非推奨。v1とv2が同じ node に一致すると PeeringPolicy が優先。v2alpha1 BGP v2 CRD も `cilium.io/v2` に置き換えられるため非推奨 |
| 1.19 | v1 CRD と control plane（`pkg/bgpv1`）を**削除**。upgrade 前に移行が必要 |
| 1.20 | v2 BGP CRD の v2alpha1 版は引き続き serve されるが非推奨 |
| 1.21-pre | 同上 |

1.19より前の v2alpha1 PeerConfig にあった `spec.transport.localPort` field は削除されました。port は cluster config の instance（`localPort`）と override で設定します。

### 2.10 運用と障害シナリオ

| Event | 動作 | 対応 |
|---|---|---|
| Agent 再起動／upgrade | speaker が agent 内にあるため session は切れるが、datapath の forwarding は継続 | Graceful Restart を設定し、`restartTimeSeconds` を agent 起動時間より長くする。新 image を事前 pull |
| Node crash | peer は hold time（GR 使用時は restart time も）待つ | hold timer を短縮し、resilient hashing と ECMP を使う |
| 直接接続 link down | TCP が即時に閉じる | 該当なし |
| multihop link down | hold timer（default 90秒）で検出 | hold time 短縮。BFD は利用不可 |
| Operator 停止 | 新しい `CiliumBGPNodeConfig` が作成されない。operator による PodCIDR と LB IP の割り当ても停止 | operator を HA 構成にする |
| Service の backend がすべて消失 | section 2.5 を参照 | policy を意図どおり選ぶ |

**Node 停止手順。** node を drain し、label を変更して `nodeSelector` に一致しないよう cluster config から外します（session は Notification を受信して閉じます）。peer が route を取り下げるまで待ちます（即時、または RFC 8538 の stale timer 経過後）。ECMP の再配置により一部 flow が reset されることを見込みます。

**[1.21 pre-release]** BGP controller は route を広報する前に host datapath の BPF program が attach され、LB map が設定されるのを待ちます（`pkg/bgp/agent/datapath_waiter.go`）。これにより agent 起動直後、route が traffic を処理できる前に広報される時間帯をなくします。1.20にはありません。

### 2.11 オンプレミス ToR の構成例

```
            [ upstream L3 / firewall ]
                 |            |
             ToR-A (AS65000) ToR-B (AS65000)    static neighbors or `bgp listen range`
              |  \  /  |     ECMP, resilient hashing, GR helper
      node1..N (Cilium AS65001, one CiliumBGPClusterConfig per rack)
        advertise: PodCIDR (cluster-pool / host-scope IPAM)
                 + Service LoadBalancerIP (from an LB IPAM pool)
        eTP: Cluster (all nodes; add Maglev) or Local (only nodes with backends)
```

設計時の確認事項：rack ごとに cluster config を1つ作成（1 node が一致できるのは1つだけ）、rack ごとに peer を2つ設定、hold 9／keepalive 3 と agent 起動時間を超える restart time の GR、`authSecretRef` による MD5、community で Pod route と Service route を区別する ToR route-map、ToR の ECMP path 上限を確認、BFD は使わない。

### 2.12 BGP と AWS

ENI IPAM の EKS cluster では Pod IP が VPC address であり、VPC fabric がすでに routing しています。node は PodCIDR を所有しないため、PodCIDR advertisement は効果がなく、VPC に node route を受信する BGP speaker もありません。そのため AWS で BGP が関係するのは主にオンプレミス上で稼働する EKS Hybrid Nodes です（[hybrid nodes network configuration](../../eks-hybrid-nodes/02-network-configuration.md)）。この場合、peer はオンプレミス ToR です。この repository の既存 hybrid-node 例は1.18 build に固定されているため `v2alpha1` API を使っていますが、1.19以降では `cilium.io/v2` を使ってください。

## 3. LB IPAM

**成熟度**: 安定版 CRD `cilium.io/v2` の `CiliumLoadBalancerIPPool`（1.18.14では v2 が storage version で、v2alpha1 も引き続き serve。v2alpha1 が初めて非推奨になったのは1.19.8）。LB IPAM は operator に組み込まれ、最初の pool が作成されるまでは休止しています（`--enable-lb-ipam`、default true）。IP を割り当てるだけで、広報はしません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata: {name: blue-pool}
spec:
  blocks:
  - cidr: "10.0.10.0/24"
  - start: "10.0.20.100"
    stop: "10.0.20.200"
  serviceSelector:
    matchLabels: {bgp: "true"}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: example, labels: {bgp: "true"}}
spec:
  type: LoadBalancer
  loadBalancerClass: io.cilium/bgp-control-plane
  ports: [{port: 80}]
  selector: {app: web}
```

`serviceSelector` は `blocks` の下ではなく `spec` の直下に置きます（上流 doc の例は indent が誤っています）。

| Pool field | 説明 |
|---|---|
| `blocks[]` | `cidr` または `start` + `stop` |
| `serviceSelector` | 特別な key は `io.kubernetes.service.namespace`／`.name` |
| `disabled` | default false |
| `allowFirstLastIPs` | `Yes` または `No`。`No` は CIDR block の先頭・末尾 address のみを予約。/31、/32、/127、/128 と start／stop block では無視 |

知っておくべき動作：

- CIDR が重複すると後から作成した pool は conflicting とマークされます（`cilium.io/PoolConflict`）。Status condition は `cilium.io/IPsTotal`、`IPsAvailable`、`IPsUsed`。`kubectl get ippools` で確認できます。
- pool を編集すると既存 Service の IP が再割り当てされることがあります。
- Class の扱い：class のない `LoadBalancer` Service は default で LB IPAM が処理します。Helm `defaultLBServiceIPAM` は `lbipam`（default）、`nodeipam`、`none`。`none` の場合、認識済み class を持つ Service だけに IP を割り当てます。Cilium が認識しない class は通知なしで無視されます。Service に `cilium.io/IPAMRequestSatisfied` condition が設定されます。
- IP family は `ipFamilyPolicy` に従います：SingleStack（両方が利用できる場合は IPv4）、PreferDualStack、RequireDualStack。
- 特定 address の要求には `lbipam.cilium.io/ips: "a,b"` を使います（pool selector の条件も満たす必要があります。`.spec.loadBalancerIP` は非推奨）。pool の先頭／末尾 address は要求しないでください。
- **Shared IP**：`lbipam.cilium.io/sharing-key` と `lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"|"*"` を使います。1.20.2では port／protocol の conflict がなければ Service 間で共有できます。**[1.21 pre-release]** では条件が厳格化され、同じ port と protocol、同じ `externalTrafficPolicy` が必要です。policy が `Local` なら同じ Pod を選択する必要があります。ただし全 Service に `lbipam.cilium.io/sharing-permit-different-pods: "true"` を設定した場合は異なる Pod も許可されます（BGP と L2 は L4 を認識しないため traffic が drop する可能性があります）。cross-namespace を許可しない限り、同じ namespace 内で共有します。
- **1.19 の datapath 変更**：LB IPAM address 宛ての north-south TCP／UDP は、Service に定義されていない port では drop されます。
- Gateway API：`Gateway.spec.addresses` は LB IPAM に渡されます。`spec.infrastructure.annotations` の `io.cilium/lb-ipam-ips` annotation はそちらより優先され、将来 deprecated になる予定です。

Pod IPAM は別の機能です。[IPAM deep dive](10-ipam-deep-dive.md) を参照してください。

## 4. L2 announcements

**成熟度**: 1.20.2と1.21.0-pre.3で beta。CRD は引き続き `cilium.io/v2alpha1` の `CiliumL2AnnouncementPolicy` です。

Service ごとに選出された node が Service の external IP または LoadBalancer IP に対する ARP（IPv4）／NDP（IPv6）へ応答し、その後 eBPF で load balance します。BGP を使わないオンプレミス LAN を対象とします。**AWS VPC 内では利用できません**。VPC では VIP の L2 broadcast semantics や gratuitous ARP failover が使えないためです。オンプレミスまたは hybrid site で使用してください。

```yaml
l2announcements:
  enabled: true
  leaseDuration: 3s
  leaseRenewDeadline: 1s
  leaseRetryPeriod: 200ms
kubeProxyReplacement: true
k8sClientRateLimit: {qps: 32, burst: 64}
```

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata: {name: policy1}
spec:
  serviceSelector: {matchLabels: {color: blue}}
  nodeSelector:
    matchExpressions:
    - {key: node-role.kubernetes.io/control-plane, operator: DoesNotExist}
  interfaces: ["^eth[0-9]+"]
  externalIPs: true
  loadBalancerIPs: true
```

| Field | 説明 |
|---|---|
| `nodeSelector`、`serviceSelector` | 広報する node と対象 Service を選ぶ |
| `interfaces[]` | Go regex（OR 条件）。security control ではありません。device は Cilium の `--devices` にも含める必要あり |
| `externalIPs`、`loadBalancerIPs` | bool、どちらも default false |

Service の `loadBalancerClass` は未設定、または `io.cilium/l2-announcer` でなければなりません。

**Leader election。** Cilium の namespace に Service ごとの `coordination.k8s.io` Lease（`cilium-l2announce-<ns>-<svc>`）を作成します。先着順のため負荷は均等になりません。leader が切り替わると gratuitous ARP を送信します。default は `leaseDuration` 15秒、`leaseRenewDeadline` 5秒、`leaseRetryPeriod` 2秒です。制約は duration > renewDeadline、かつ renewDeadline は1.2（leader-election JitterFactor）× retryPeriod より厳密に大きいことです。満たさない場合、agent は warning を log に出して timer を上書きします。failover は `leaseDuration - leaseRenewDeadline` から `leaseDuration + leaseRenewDeadline` の間で発生します。default 値では10～20秒、3秒／1秒／200ms では2～4秒です。

**API load。** Service ごとの Lease はおよそ `leaseRenewDeadline` ごとに更新されます。QPS の概算は `Service 数 × (1 / leaseRenewDeadline)` です（retry と read は考慮しない概算）。agent の client limit は default で10 QPS／burst 20で、他の agent API traffic と共有されます。default の5秒設定では Service あたり約0.2 QPS なので、数十個の Service で budget の大部分を消費します。1秒 timer では約10 Service で上限に達します。timer を短縮する前に `k8sClientRateLimit` を増やしてください。RBAC には Lease の create／get／update／list／delete が必要です。

**制約。** `externalTrafficPolicy: Local` とは併用できません（選出 node に Pod がなければ traffic が drop）。1つの IP の traffic は単一 node に入るため、cluster 到達前の load balancing はありません。

**L2 Pod announcements** は別機能です：`l2podAnnouncements.enabled` と `.interfacePattern`（regex）で local Pod IP の GARP／NA を送信します。旧 `--l2-pod-announcements-interface` flag は1.19で削除されました。

確認には `kubectl -n kube-system get lease | grep cilium-l2announce`、`cilium-dbg shell -- db/show l2-announce`、`cilium-dbg shell -- db/show devices`、LAN 上の別 host から実行する `arping` を使います。

## 5. Node IPAM

Helm の `nodeIPAM.enabled=true`（default false、operator flag `--enable-node-ipam`）を設定し、operator を再起動します。`loadBalancerClass: io.cilium/node`（または `defaultLBServiceIPAM: nodeipam`）を持つ Service は、node address を `.status.loadBalancer` に公開します。ExternalIP があればそれを使い、なければ InternalIP を使います。`ipFamilies` も反映します。`Cluster` policy はすべての node、`Local` は EndpointSlice Pod がある node のみを公開します。`node.kubernetes.io/exclude-from-external-load-balancers` label または `ToBeDeletedByClusterAutoscaler` taint を持つ node は除外されます。`io.cilium.nodeipam/match-node-labels` annotation で node を絞り込めます。Cilium Ingress／Gateway Service の `Local` policy では動作しません（synthetic EndpointSlice を使うため）。BGP と L2 が使えない場合に限り、private node address の環境で使ってください。public node IP を公開すると CloudFront のみを入口にする規則の外側に public entry point ができます。

## 6. Service を所有する機能

| `loadBalancerClass` | Owner | 必要なもの |
|---|---|---|
| 未設定 | default では LB IPAM（`defaultLBServiceIPAM`） | pool、および到達性のための BGP または L2 |
| `io.cilium/bgp-control-plane` | LB IPAM + BGP advertisement | BGP Control Plane |
| `io.cilium/l2-announcer` | LB IPAM + L2 announcement | L2 announcements |
| `io.cilium/node` | Node IPAM | `nodeIPAM.enabled` |
| `service.k8s.aws/nlb` | AWS Load Balancer Controller | Cilium BGP／LB IPAM は無視 |

## 7. Egress Gateway

**成熟度**: `CiliumEgressGatewayPolicy` は cluster-scoped の `cilium.io/v2`（short name `cegp`）です。1.20 doc では beta とされていません。

選択した Pod から選択した destination CIDR への traffic を gateway node に転送し、安定した source IP に SNAT します。外部 firewall からは予測可能な address に見えます。

要件：`egressGateway.enabled=true`、`bpf.masquerade=true`、`kubeProxyReplacement=true`。agent と operator の両方を再起動してください。identity mode `kvstore`（`crd` を使う）、ClusterMesh（gateway は同じ cluster 内であること）、CiliumEndpointSlice とは併用できません。`--enable-ipv4-egress-gateway` flag は1.19で削除されました。

```yaml
apiVersion: cilium.io/v2
kind: CiliumEgressGatewayPolicy
metadata: {name: egress-sample}
spec:
  selectors:
  - podSelector:
      matchLabels: {org: empire, class: mediabot, io.kubernetes.pod.namespace: default}
  destinationCIDRs: ["192.0.2.0/24"]
  egressGateway:
    nodeSelector: {matchLabels: {egress-node: "true"}}
    egressIP: 10.168.60.100
```

| Field | 説明 |
|---|---|
| `selectors[]` | `podSelector` または `namespaceSelector`（namespace は `io.kubernetes.pod.namespace` label で選択）。`nodeSelector` 単独は不可 |
| `destinationCIDRs[]`、`excludedCIDRs[]` | IPv4／IPv6。excluded は destination の subset であること。Pod、node、API server など内部 address は常に EGW の対象外 |
| `egressGateway.nodeSelector` | 必須。一致する node が複数なら node 名順で先頭を選択。**一致なし：destination CIDR 宛て traffic は drop** |
| `egressGateway.interface`／`egressIP` | 相互排他（両方指定すると policy は無視）。`interface` は最初の IPv4／IPv6 address を使う。`egressIP` は Cilium 管理 device 上に存在する必要あり。両方省略すると default-route interface とその最初の IPv4／IPv6 address を使う |
| `egressGateways[]` | 最大64 entry。空でなければ `egressGateway` は無視 |

制約：

- **1.20.2と1.21.0-pre.3には HA がありません。** `egressGateways[]` は静的な複数 gateway 設定です。各 source endpoint は CiliumEndpoint UID の hash により1つの gateway に固定されます。集合を変更すると endpoint が再配置され、既存 connection が切断されます（cilium/cilium#39245）。どちらの version の source（`pkg/egressgateway` を検索）にも、health check や停止した gateway への自動 failover はありません。1.21-pre CRD で1.20.2と異なるのは CIDR type のみです。
- 選択後に gateway の IP 変更を追跡しません。policy を再適用してください。
- 指定 IP が存在しないと、`No Egress IP configured` の reason で traffic が drop します。
- 新しい Pod は policy が設定されるまでの短時間、自身の IP または node IP で traffic を送ることがあります。
- `(egress IP, remote IP:port)` ごとの SNAT port budget は約65535から node-port range の上限（default 32767）を引いた数、つまり約32768 connection です。`cilium-dbg shell -- db/show nat-stats` で確認します。

確認：`kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf egress list`（source IP、destination CIDR、egress IP、gateway IP）。

**EKS の場合。** gateway node は attach 済み ENI 上に egress address（追加 ENI または secondary private IP）を持つ必要があります。Egress IP は private VPC address です。そこから internet に接続するには NAT gateway 経由にします。gateway node に public IP または EIP を attach しないでください。ENI IPAM では `--egress-multi-home-ip-rule-compat` が1.19で削除されたため、1.18を使用中なら upgrade 前にこの flag を外してください。

## 8. Local Redirect Policy

`CiliumLocalRedirectPolicy`（namespaced の `cilium.io/v2`）は Service ClusterIP、または任意の IP:port 宛て traffic を node-local backend Pod に redirect します。

`localRedirectPolicies.enabled=true` で有効化します（旧 key `localRedirectPolicy` は非推奨）。operator と agent を再起動してください。cluster 全体の任意 allow-list は `localRedirectPolicies.addressMatcherCIDRs` です（上流 doc の YAML では key の綴りが異なりますが、正しい Helm key は `addressMatcherCIDRs`）。

```yaml
apiVersion: cilium.io/v2
kind: CiliumLocalRedirectPolicy
metadata: {name: lrp-svc}
spec:
  redirectFrontend:
    serviceMatcher: {serviceName: my-service, namespace: default}
  redirectBackend:
    localEndpointSelector: {matchLabels: {app: proxy}}
    toPorts: [{port: "80", protocol: TCP}]
```

| Matcher | 用途 |
|---|---|
| `serviceMatcher` | ClusterIP Service のみ。Service entry を `LocalRedirect` type に置き換え、node-local backend のみへ送信 |
| `addressMatcher{ip, toPorts[]}` | Service ではない IP。既存の ClusterIP frontend を上書きしない |

規則：backend Pod は policy と同じ namespace 内にあること。複数 port を使う場合は named port が必要です。redirect 対象は**新しい** connection のみなので、client を再起動してください。policy の更新はできません（削除して再作成）。対応する kube-proxy-replacement 構成は full KPR、`socketLB.hostNamespaceOnly=true` の KPR、`socketLB.enabled=true` の KPR off、または KPR 単独 off（Pod から ClusterIP の場合のみ）です。主な用途は node-local DNS です（kube-dns frontend を独自 network namespace の node-local-dns Pod に redirect）。`cilium-dbg lrp list` で確認します。

## 9. Service traffic distribution

`loadBalancer.serviceTopology`（default `false`、flag `--enable-service-topology`）を有効にすると kube-proxy replacement は Topology Aware Routing hint と `spec.trafficDistribution` の両方を反映します。`PreferSameZone`（および非推奨 alias `PreferClose`）は EndpointSlice の zone hint と node の `topology.kubernetes.io/zone` label を使います。`PreferSameNode` は local node の backend を優先し、条件に合うものがなければ default に戻ります。**[1.21 pre-release]** では ready 状態の backend だけを優先候補として扱います。これは制限をかける `externalTrafficPolicy`／`internalTrafficPolicy: Local` とは異なり、近い backend を優先する機能です。multi-AZ EKS では `serviceTopology: true` と `trafficDistribution: PreferSameZone` の組み合わせで AZ 間 traffic を減らせます。Gateway API では `CiliumGatewayClassConfig.spec.service.trafficDistribution` が生成された Service に引き継がれます。

## 10. L7 の入口：Ingress と Gateway API

前提条件：`kubeProxyReplacement=true`、`l7Proxy=true`（default）、TPROXY 対応（default は iptables。`bpf.tproxy=true` は beta で iptables 依存を解消）、および LoadBalancer Service（または1.16以降の host-network mode）。

**Traffic flow。** eBPF は Service port 宛て packet を intercept し、TPROXY で node ごとの Envoy に redirect します。traffic には特別な `ingress` identity が付くため、policy は2回適用されます：world から ingress、ingress から backend。どちらの `externalTrafficPolicy` でも source IP を保持します。`Local` の場合、Cilium は health check port で全 node の health check を通します。`CiliumNetworkPolicy` で両方の経路を許可してください。TLS passthrough では backend から Envoy の IP が見えます。

### Ingress

| Helm value | Default |
|---|---|
| `ingressController.enabled`／`.default` | `false`／`false` |
| `ingressController.loadbalancerMode` | `dedicated`（`shared` または `dedicated`。Ingress ごとの annotation は `ingress.cilium.io/loadbalancer-mode`） |
| `ingressController.enforceHttps` | `true` |
| `ingressController.useRemoteAddress`、`.xffNumTrustedHops` | `true`、`0` |
| `ingressController.ingressLBAnnotationPrefixes` | `lbipam.cilium.io`、`nodeipam.cilium.io`、`service.beta.kubernetes.io`、`service.kubernetes.io`、`cloud.google.com`（Ingress から Service に伝播） |
| `ingressController.service.*`（shared） | `name: cilium-ingress`、`type: LoadBalancer`、`externalTrafficPolicy: Cluster`、annotation、`loadBalancerClass` |
| `ingressController.hostNetwork.*` | `enabled: false`、`sharedListenerPort: 8080` |

### Gateway API

Cilium 1.20.2と1.21.0-pre.3は **Gateway API v1.6.1** を使用します（1.19.8は v1.4.1、1.18.14は v1.3.0）。対応 kind：GatewayClass、Gateway、HTTPRoute、GRPCRoute、TLSRoute、BackendTLSPolicy、ReferenceGrant、ListenerSet、TCPRoute、UDPRoute。必須 CRD：GatewayClass、Gateway、HTTPRoute、GRPCRoute、ReferenceGrant、BackendTLSPolicy、TLSRoute。TCPRoute、UDPRoute、ListenerSet は任意で、不足するとその feature は無効です。`kubectl apply --server-side` で install します。

> **Upgrade 時の注意：Gateway API v1.6.1 と TLSRoute。** v1.6.1で TLSRoute は `v1alpha2` から `v1` に昇格しました。1.20 upgrade note は v1.6.1以降を必須としています。既存の TLSRoute object がある場合は、`v1alpha2` version も含む v1.6.1 の **experimental-channel** TLSRoute CRD を install してください。**standard-channel** の v1.6 TLSRoute CRD を install すると既存の `v1alpha2` object を読めなくなり、etcd から消えたように見えます。TLSRoute を backup し、Cilium 1.20 に upgrade **する前に** Gateway API CRD を upgrade してください。

| Helm value | Default |
|---|---|
| `gatewayAPI.enabled` | `false` |
| `gatewayAPI.gatewayClass.create` | `auto` |
| `gatewayAPI.enableProxyProtocol`、`.enableAppProtocol`、`.enableAlpn` | `false` |
| `gatewayAPI.useRemoteAddress`、`.xffNumTrustedHops` | `true`、`0` |
| `gatewayAPI.externalTrafficPolicy` | `Cluster`（host network では無視） |
| `gatewayAPI.secretsNamespace` | `create: true`、`name: cilium-secrets`、`sync: true` |
| `gatewayAPI.hostNetwork.enabled`／`.nodes.matchLabels` | `false`／`{}` |

生成される Service 名は `cilium-gateway-<gateway>` で、default type は `LoadBalancer` です。`CiliumGatewayClassConfig`（namespaced の `cilium.io/v2alpha1`。`GatewayClass.parametersRef` から参照する alpha API）で調整できます。`spec.service{type, externalTrafficPolicy, loadBalancerClass, ipFamilies, ipFamilyPolicy, allocateLoadBalancerNodePorts, loadBalancerSourceRanges, loadBalancerSourceRangesPolicy, trafficDistribution}`、`envoy.serverHeaderTransformation`、`httpOptions.grpcWebTranslation.enabled` を指定します。Gateway ごとの `spec.infrastructure.annotations` と `labels` は生成 Service にコピーされるので、`service.beta.kubernetes.io/aws-load-balancer-*` annotation の引き渡しに使えます。`spec.infrastructure.parametersRef` は非対応です。

Host-network mode（`gatewayAPI.hostNetwork.enabled=true`）では Envoy が node interface で listen します。1023より大きい port を使うか `NET_BIND_SERVICE` を付与してください。LoadBalancer Service mode とは併用できず、TCPRoute／UDPRoute にも対応しません。Service type は NodePort になり、Gateway status に表示できる address は最大16個です。

### EKS 構成：CloudFront VPC origin → internal NLB → Cilium

外部公開の入口は CloudFront だけです。ここに記載する構成要素は internet-facing にしません。

```
Internet --> CloudFront --(VPC origin)--> INTERNAL NLB (private subnets)
         --> node NodePort --> Cilium Envoy (Ingress or Gateway) --> Pods
```

```yaml
kubeProxyReplacement: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-<nlb-sg>
      service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules: "true"
```

Gateway API variant では `CiliumGatewayClassConfig.spec.service.loadBalancerClass: service.k8s.aws/nlb` を設定し、同じ `aws-load-balancer-*` annotation を `Gateway.spec.infrastructure.annotations` に指定します。

この構成のルール：

- `scheme: internal` は必須です。`internet-facing` にしないでください。
- `target-type: instance` を使います。Cilium の共有 Ingress Service は synthetic EndpointSlice を使うため、`ip` target は Pod に解決されません。[Ingress and Gateway API](../../service-mesh/cilium-service-mesh/05-ingress-gateway.md) を参照してください。
- Load balancer の security group は CloudFront のみを許可します。選択肢は VPC origin 作成後に作られる service-managed security group `CloudFront-VPCOrigins-Service-SG`（より限定的で推奨。独自 group 名にこの prefix を使わない）か、CloudFront managed prefix list `com.amazonaws.global.cloudfront.origin-facing`（dual stack では `com.amazonaws.global.ipv6.cloudfront.origin-facing` も追加）です。`0.0.0.0/0`／`::/0` を ingress source にせず、node に public IP／EIP を付けないでください（[AWS: VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)）。
- Node security group では internet 全体の CIDR ではなく、NLB の security group から NodePort range への traffic のみを許可します。

## 11. SRv6 と static routing

SRv6 は本章で扱う version ではサポートされていません。1.20.2と1.21.0-pre.3の source に documentation page、Helm key、CRD はありません。agent の非公開 `--enable-srv6` flag、BPF hook、確認用の `cilium-dbg bpf srv6` command だけが残っており、OSS control plane はありません。利用計画に含めないでください。static routing には native routing の `autoDirectNodeRoutes` または cloud route table を使います（[Part 9](09-overlay-native-routing.md)）。Cilium BGP が peer から受信する route は kernel／eBPF routing table に install されません。

## Labs

> Lab 1～4では、FRR などの router container を含む local lab（kind または複数 VM）が必要です。Lab 5は `--profile <SANDBOX_PROFILE>` を使う破棄可能な sandbox AWS account が対象です。期待される結果は文章で説明しています。実行時の出力は記録していません。

### Lab 1: FRR ToR と BGP session を確立

**前提条件**：Docker network を FRR container と共有する worker 2台の kind cluster。FRR は AS 65000、node IP を neighbor として設定し、remote AS は65001にします。Cilium の `bgpControlPlane.enabled=true` を設定します。section 2.6の manifest を node IP に合わせます（`authSecretRef` を削除するか、先に Secret を作成）。

1. worker に `rack=rack0` label を付け、ClusterConfig、PeerConfig、Advertisement を適用します。
2. `kubectl get ciliumbgpnodeconfigs` に label 付き node ごとに1つ表示されることを確認します。
3. `kubectl get ciliumbgpnodeconfigs <node> -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'` と `cilium-dbg shell -- bgp/peers` が `established` を返すことを確認します。FRR の `show bgp summary` で neighbor が up であることも確認します。
4. `cilium-dbg shell -- bgp/routes out ipv4 unicast` に node の PodCIDR、FRR の `show ip route bgp` に学習した route が表示されることを確認します。
5. 片方の node で agent Pod を削除します。GR が有効なら FRR は restart time まで route を stale として保持し、無効ならすぐ消えます。結果を比較します。

**Rollback／後片付け**：3つの BGP resource を削除し、node label を外します。ClusterConfig を削除すると operator は NodeConfig を削除し、session を閉じます。

### Lab 2: LB IPAM と BGP、traffic policy の関係

**前提条件**：Lab 1が稼働していること。

1. section 3の pool と Service を作成します（FRR container が受け入れる range 内の block を使います）。
2. `kubectl get svc web -n example` に pool から割り当てられた EXTERNAL-IP、`kubectl get ippools` に `IPsUsed` が1と表示されることを確認します。
3. `bgp/routes out ipv4 unicast` に選択された各 node からの `/32` が表示されることを確認します。FRR container から `curl <VIP>` を実行します。
4. `kubectl patch svc web -n example -p '{"spec":{"externalTrafficPolicy":"Local"}}'` を実行します。ready Pod がある node だけで route が残ります。Deployment を scale し、route が Pod に追従することを確認します。

**後片付け**：Service、Deployment、pool を削除します。

### Lab 3: L2 announcements

**前提条件**：Linux bridge 上の kind cluster、KPR 有効、`l2announcements.enabled=true` と3秒／1秒／200ms の timer、増加させた client rate limit。同じ bridge 上の client container。

1. L2 policy と pool を使う `LoadBalancer` Service を適用します。
2. `kubectl -n kube-system get lease | grep cilium-l2announce` に Service の Lease が表示されることを確認します。client から `arping` を実行すると leader node の MAC が応答します。
3. leader node の Cilium agent Pod を削除（または node container を停止）し、`arping` が失敗する時間を測ります。この timer では数秒程度、default では10～20秒程度になるはずです。

**後片付け**：policy と Service を削除します。rollback する場合、Lease 値を default に戻します。

### Lab 4: Egress Gateway

**前提条件**：KPR、`bpf.masquerade=true`、`egressGateway.enabled=true`、再起動済みの agent と operator、client IP を記録する外部 web server container、device 上に secondary address を持つ `egress-node=true` label の node。

1. section 7の例をもとに、その address と server の CIDR を指定した policy を適用します。
2. 選択された Pod から server へ `curl` します。server log に node IP や Pod IP ではなく egress IP が記録されます。
3. source node で `cilium-dbg bpf egress list` を実行して entry を確認します。node label を削除すると gateway がなくなるため、CIDR 宛て traffic は drop されます。

**後片付け／rollback**：policy を削除し、label を外します。適用中は選択された traffic に影響します。

### Lab 5: CloudFront の背後にある EKS internal NLB（sandbox account）

**前提条件**：`aws sts get-caller-identity --profile <SANDBOX_PROFILE>` が想定した sandbox account `<ACCOUNT_ID>` と利用する assumed role を返すこと。Cilium と AWS Load Balancer Controller のある EKS cluster、および作成済みの CloudFront VPC origin。

1. section 10の Helm value で install します（必要なら Gateway API 構成を使います）。
2. `aws elbv2 describe-load-balancers --profile <SANDBOX_PROFILE> --query 'LoadBalancers[].[LoadBalancerName,Scheme]'` で新しい NLB の scheme が `internal` であることを確認します。
3. `aws ec2 describe-security-groups --profile <SANDBOX_PROFILE> --group-ids <nlb-sg> --query 'SecurityGroups[].IpPermissions'` を実行し、source が CloudFront VPC origin の security group または prefix list のみであることを確認します。`0.0.0.0/0` や `::/0` は許可しません。
4. NLB を VPC origin の target に設定し、CloudFront domain 経由で request します。

**後片付け**：Ingress または Gateway を削除します（controller が NLB を削除）。単に `deleting` 状態になっただけではなく、実際に not-found response が返ることを確認してください。

## Version 差分

| 領域 | 1.18 | 1.19 | 1.20 | 1.21-pre |
|---|---|---|---|---|
| BGP v1 `CiliumBGPPeeringPolicy` | 非推奨 | **削除** | 削除済み | 削除済み |
| BGP CRD | v2（および v2alpha1） | `cilium.io/v2` が storage、v2alpha1 は非推奨 | 同左 | 同左 |
| BGP `Interface` advertisement、`transport.sourceInterface` | 文書になし | 追加 | あり | あり |
| GoBGP | 本レビュー対象ではなし | gobgp v3（1.19.8） | gobgp v4 | gobgp v4 |
| BGP metric label | 本レビュー対象ではなし | `vrouter`（doc） | `instance_name` | `instance_name` |
| `cilium-dbg bgp`／REST での一覧表示 | 対応 | 対応 | **非推奨**。hive shell `bgp/*` を使う | 非推奨と明記 |
| datapath ready 後に BGP 広報を開始 | なし | なし | なし | **あり** |
| `CiliumLoadBalancerIPPool` | v2（storage）、v2alpha1 も引き続き提供 | `cilium.io/v2`（v2alpha1 非推奨） | v2 | v2。sharing rule 厳格化 |
| Gateway API CRD | v1.3.0 | v1.4.1 | **v1.6.1**（TLSRoute の注意あり） | v1.6.1 |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | **v2** |
| Egress Gateway | CRD v2 | `--enable-ipv4-egress-gateway`、`--egress-multi-home-ip-rule-compat` を削除 | HA なし | HA なし |
| L2 announcements | beta | beta | beta（CRD v2alpha1） | beta |
| SRv6 | なし | なし | なし | なし（非公開 flag のみ） |

## Troubleshooting

| 症状 | 主な原因 | 確認方法 |
|---|---|---|
| `CiliumBGPNodeConfig` が作成されない | operator 停止、または `nodeSelector` が何も選択しない | ClusterConfig condition `NoMatchingNode`、operator log の `subsys=bgp-cp-operator` |
| Cluster config が拒否される | 別の cluster config が同じ node を選択 | `ConflictingClusterConfig` |
| Session が `dial: i/o timeout` のまま | MD5 password、ACL、source address の誤り | `authSecretRef`、`cilium.io/MissingAuthSecret`、`localAddress`／`sourceInterface` |
| Session は up だが route がない | PeerConfig の `families[].advertisements` label が advertisement label と不一致 | label を比較し `bgp/route-policies` を確認 |
| EKS で PodCIDR が広報されない | ENI IPAM には node ごとの PodCIDR がない | [IPAM](10-ipam-deep-dive.md) |
| Service VIP が広報されない | `loadBalancerClass` が `io.cilium/bgp-control-plane`／未設定ではない、selector 不一致、`Local` policy で ready backend がない | Service YAML、`bgp/routes out` |
| agent upgrade 時に route が消える | Graceful Restart なし、または restart time が短い | PeerConfig の GR、新 image を事前 pull |
| 1.20 upgrade 後に Grafana の BGP panel が空 | label `vrouter` が `instance_name` に rename | query を更新 |
| LB IP が `<pending>` のまま | pool なし、selector 不一致、pool conflict、未認識 class | `kubectl get ippools`、Service condition |
| L2 VIP が flap または応答しない | `Local` policy、Lease API throttling | Lease object、`k8sClientRateLimit` を増加 |
| Egress traffic が drop | `nodeSelector` に一致する gateway node がない、または device 上に IP がない | `bpf egress list`、drop reason |
| Gateway API CRD upgrade 後 TLSRoute が消えた | standard-channel v1.6 CRD を v1alpha2 data に適用 | backup から復元し、experimental-channel CRD を使う |
| Gateway Service が停止したまま | 必須 Gateway API CRD 不足、KPR 無効 | operator log、`cilium status` |

## 検証範囲と情報源

このレビューでは lab を実 cluster 上で実行していません。command syntax は上流 source と文書で確認しました。`bgp/peers` と `bgp/routes` の command syntax は `pkg/bgp/commands` で検証しましたが、実際の table output は取得していないため掲載していません。EKS-native（非 hybrid）cluster における BGP、Transit Gateway Connect、VPC Route Server peering などは調査対象外です。未検証事項：Egress Gateway が1.21 GA で health-based failover を得るか、metric label の rename が1.19から1.20のどの release で行われたか（1.20.2で確認済み、1.19.8の doc には記載なし）。

情報源（特記がなければ tag v1.20.2）：

- [BGP Control Plane overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)、[configuration](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)、[operation](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [BGP CRD types](https://github.com/cilium/cilium/tree/v1.20.2/pkg/k8s/apis/cilium.io/v2)、[hive shell commands](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/commands/cell.go)
- [LB IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst)、[L2 announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst)、[Node IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst)
- [Egress Gateway](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst)、[Local Redirect Policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/local-redirect-policy.rst)
- [Upgrade notes 1.20](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)、[Gateway API](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/servicemesh/gateway-api)
- [v1.21.0-pre.3 BGP datapath waiter](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/bgp/agent/datapath_waiter.go)、[v1.21.0-pre.3 LB IPAM](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst)

## Quiz

[Part 11 quiz](../../quizzes/networking/cilium/11-bgp-lb-egress-edge-quiz.md) で理解を確認してください。
