# Part 12: mTLS、透過暗号化、Identity

> **レビュー基準**: Cilium 1.20.2（stable、2026-09-16）、Cilium CLI 0.20.1、Hubble CLI 1.20.2。**[1.21 pre-release]** と記した項目は v1.21.0-pre.3 に基づき、GA 前に変わる可能性があります。
> **最終更新日**: 2026年10月15日

Cilium の security model には、混同しやすい3つの層があります。**Identity と policy** は IP ではなく label に基づいて通信可能な相手を決めます。**透過暗号化**（WireGuard、IPsec）は node 間で送られる byte を保護します。**Workload mTLS**（ztunnel）は暗号化 channel を workload identity に結び付けます。この章では各機能の仕組みから説明し、削除済み Mutual Authentication、service mesh の選択肢、Hubble／Tetragon、証明書管理を扱います。

関連章：[eBPF datapath internals](08-ebpf-datapath-internals.md)、[overlay and native routing](09-overlay-native-routing.md)（tunnel と MTU の関係）、[IPAM](10-ipam-deep-dive.md)、[BGP、LB、egress](11-bgp-lb-egress-edge.md)、[ClusterMesh、install、upgrade](13-clustermesh-install-upgrade.md)。policy の基礎は [IPAM and Network Policies](04-ipam-policy.md) にあり、この章ではさらに詳しく扱います。可視化の入門は [Security and Visibility](06-security-visibility.md) を参照してください。

## 機能の成熟度と timeline

| Feature | 1.18 | 1.19 | 1.20（stable） | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication（SPIFFE／SPIRE、`authentication.mode: required`） | Beta | Beta、`authentication.enabled` の default は false | **Deprecated**（doc title は「Beta」のまま） | **削除** |
| ztunnel 透過暗号化（`encryption.type=ztunnel`） | - | Beta（導入） | Beta、`ca.type` を追加 | Beta |
| WireGuard | Stable | Stable | Stable | Stable |
| IPsec | Stable | Stable | Stable | Stable |
| WireGuard `encryption.nodeEncryption` | 未確認 | 未確認 | Beta | **Deprecated、1.22で削除予定** |
| Double Write identity migration | 文書化済み | 文書化済み | 文書化済み | 代わりに `cilium-dbg preflight migrate-identity` が非推奨 |
| `identityManagementMode` | 未確認 | 未確認 | Beta | Beta |
| CiliumEndpointSlice | 未確認 | 未確認 | Beta | Beta |
| Kubernetes ClusterNetworkPolicy 対応 | - | - | 新規、alpha API（v1alpha2） | alpha |

特に誤って伝えられがちなのが Mutual Authentication です。確認できる事実は次のとおりです。

- 1.18、1.19、1.20を通じて **Beta** でした（1.20の doc page title も「Mutual Authentication (Beta)」のままです）。
- **1.20で deprecated** になりました。1.20 upgrade note は「deprecated となり、将来の version で削除」とし、ztunnel を案内しています。
- **1.21で削除** されました。1.21 upgrade note は deprecated 後に削除したと記載し、upgrade 前の設定削除を求めています。
- 1.21でも policy API の `authentication` field は CRD 互換性のため残っていますが、使われません。

## Identity model

### Label から numeric identity へ

Cilium は IP address に対して policy を適用しません。各 endpoint（Pod）に、identity に関係する label から導出した numeric ID、**security identity** を割り当てます。同じ label set の endpoint は同じ ID を共有します。Deployment の replica 全体に1つの policy map entry を適用でき、Pod IP が変化しても policy 判定を維持できます。

```
Pod labels (k8s:app=web, k8s:io.kubernetes.pod.namespace=shop, ...)
        |  filter by identity-relevant labels
        v
label set  -->  allocator (CRD or kvstore)  -->  numeric identity, e.g. 31337
        |
        +--> CiliumEndpoint.status.identity (published)
        +--> ipcache:  podIP -> identity   (every node learns it)
        +--> source node stamps identity into the packet (tunnel metadata)
                or the destination node resolves srcIP via ipcache
        +--> destination node: policy map lookup (local endpoint, remote identity, port, proto)
```

宛先側の lookup key は local endpoint、remote identity、port、protocol です。identity は packet と一緒に届きます（overlay では tunnel metadata 内）。native routing では source IP から ipcache を引いて復元します。このため ipcache entry の stale／欠落は policy 関連の症状になります。

### 32-bit numeric identity の構成

scope は bit 24～31に格納されます。

| Scope | Value | 用途 |
|---|---|---|
| Global | 0 | CRD／kvstore allocator で割り当てる identity。bit 0～23を identity と cluster ID に分割 |
| Local | `1<<24` | 1 node にのみ存在する identity。CIDR と FQDN 由来 |
| Remote-node | `2<<24` | node-based policy selection に使う node identity |

ClusterMesh では下位24 bit を identity と cluster ID で共有します。`max-connected-clusters` が255なら identity に16 bit、cluster ID に8 bit、511なら15 bitと9 bitを使います。256未満の identity は予約済みです（`MinimalIdentity=256`）。定数は v1.21.0-pre.3 の `pkg/identity/numericidentity.go` を参照してください。ClusterMesh の sizing は [Part 13](13-clustermesh-install-upgrade.md) で扱います。

### Reserved identity と well-known identity

datapath constant（v1.21.0-pre.3 の `pkg/datapath/types/types_generated.go`）にある reserved identity：

| ID | Name | 意味 |
|---|---|---|
| 0 | unknown | identity を解決できていない |
| 1 | host | local node |
| 2 | world | cluster 外（`0.0.0.0/0` の CIDR identity でもある） |
| 3 | unmanaged | Cilium 管理外の endpoint |
| 4 | health | Cilium health endpoint |
| 5 | init | label が未確定の endpoint（Pod 起動中） |
| 6 | remote-node | cluster 内の他 node |
| 7 | kube-apiserver | Kubernetes API server |
| 8 | ingress | Cilium 管理の ingress／Envoy |
| 9／10 | world-ipv4／world-ipv6 | world を address family で分割 |
| 11～14 | aggregate identity（cluster、clustermesh、world、remote-node） | policy map の aggregation 用。traffic には割り当てない |

上流の terminology page は ID 0～8だけを載せているため、9と10は source で確認できます。kvstore や CRD への往復なしで存在する well-known identity には `kube-dns`（102）、EKS の `kube-dns`（103）、`coredns`（104）、`cilium-operator`（105）、EKS の `coredns`（106）があります（terminology page と `numericidentity.go`）。EKS の default DNS Pod は固定 ID を使うため、これらは EKS で重要です。

覚えておく動作：label が解決されるまで Pod は `reserved:init` です。north-south Service traffic が backend に届くと、tunnel mode では `reserved:world` になります。native routing では backend を持つ node に packet が直接届く場合は `world`、それ以外は `remote-node` です（このため `fromEntities: cluster` が一致します）。`Documentation/security/policy/caveats.rst` を参照してください。

### Identity に関係する label と identity churn

default では、除外 list にあるものを除くすべての label が identity に関係します。除外例は `io.kubernetes`、`kubernetes.io`、StatefulSet の Pod name、`pod-template-hash`、`controller-revision-hash`、`annotation.*`、`topology.kubernetes.io` です。pattern は label の先頭に anchor する regular expression です。

- inclusive pattern を1つでも追加すると agent は allow-list mode になり、`reserved:`、Pod namespace、namespace label、`policy.cluster`、service account、`app.kubernetes.io` が自動的に追加されます。
- Helm `labels:` は default に**追加**されます。list を完全に置き換える場合は `--label-prefix-file` を使います（agent flag は `--labels` と `--label-prefix-file`）。
- 既存 identity は agent を再起動するまで変わりません。その後 operator が旧 identity を garbage-collect します。
- release や Pod ごとに変化する label（build SHA、timestamp など）は値ごとに identity を作ります。identity、ipcache entry、policy-map entry が増えるため、そのような label は identity 対象から除外してください。

Source：`Documentation/operations/performance/scalability/identity-relevant-labels.rst`。

### Allocation mode

| Helm `identityAllocationMode` | 保存先 | 説明 |
|---|---|---|
| `crd`（chart default） | `CiliumIdentity`（cluster-scoped の cilium.io/v2） | 外部依存なし |
| `kvstore` | etcd | etcd をすでに実行している大規模 cluster 向け |
| `doublewrite-readkvstore` | 両方に書き込み、kvstore から読み込み | migration step |
| `doublewrite-readcrd` | 両方に書き込み、CRD から読み込み | migration step |

Writer に関する注意：**agent flag** の default は `kvstore` ですが、**Helm chart** は `crd` を設定します。`cilium-agent --help` ではなく ConfigMap にある実効値を確認してください。

**Double Write migration（beta）** は identity の空白期間なしで backend 間を移行します。kvstore から CRD に移るには、`doublewrite-readkvstore`、次に `doublewrite-readcrd`、最後に `crd` を設定します。最初に Operator、次に Agent を deploy してください（最終段階で `crd` に戻すときは、upgrade guide に従い Agent、次に Operator の順で変更します）。手順は逆方向にも実行できます。operator gauge `doublewrite_{crd,kvstore,crd_only,kvstore_only}_identities`、すなわち `cilium_operator_doublewrite_crd_identities`、`cilium_operator_doublewrite_kvstore_identities`、`cilium_operator_doublewrite_crd_only_identities`、`cilium_operator_doublewrite_kvstore_only_identities` で収束を確認できます（v1.20.2 `operator/doublewrite/metrics.go:13-33`。`Documentation/observability/metrics.rst` にも同じ名称があります）。v1.20.2 upgrade guide（`Documentation/operations/upgrade.rst`）には、code で登録されなくなった旧名称 `cilium_operator_identity_*_count` が残っています。これらを alert 対象にしないでください。次の段階へ進む前に2つの `*_only_identities` が0になるのを待ちます。1.21では `cilium-dbg preflight migrate-identity` が Double Write に置き換えられ、deprecated です。Source：`Documentation/operations/upgrade.rst`。

### Operator 管理 identity（beta）

Helm `identityManagementMode` は `agent`（default）、`operator`、`both`（migration 中のみ）を選びます。`operator` では operator が identity を割り当てるため、多数の agent が同時に作成する CIDR identity の重複を避けられます。

1. Agent から operator に移行：`both` にし、operator を再起動。次に `operator` に変更し、agent を再起動。
2. Downgrade：agent を `both` にし、その後 operator を `agent` に戻す。
3. identity-relevant label pattern を変更した後は operator と agent の両方を再起動。

関連設定：chart の `operator.identityGCInterval`（15m0s）と `identityHeartbeatTimeout`（30m0s）、agent flag の `identity-allocation-timeout`（2m）、`identity-change-grace-period`（5s）、`identity-restore-grace-period`（30s）。

### CiliumEndpoint、CiliumEndpointSlice、ipcache

- **CiliumEndpoint（CEP）**：Cilium 管理 Pod ごとに1つ。同じ name と namespace を使います。status には label、identity ID、適用中の policy が入ります。`kube-system` には `cilium-health-<node>` CEP もあります。
- **CiliumEndpointSlice（CES、beta。CRD は引き続き cilium.io/v2alpha1）**：operator が簡略化した CEP を CES object にまとめ、agent は CES を監視します。新しい endpoint identity の学習に遅延が入る代わりに API server load を削減します。Helm `ciliumEndpointSlice.enabled`（default false）と `rateLimits` を使います。namespace annotation `cilium.io/ces-namespace: priority` は namespace を優先します。Egress Gateway と非互換です。移行では operator を先に、次に agent を更新し、downgrade は agent を先に行います。`--ces-slice-mode` flag は1.20で削除されました。
- **ipcache**：BPF map `cilium_ipcache_v2` は IP または CIDR を identity に対応付けます。`cilium-dbg bpf ipcache list|get|match` および `cilium-dbg identity list|get` で確認します。
- endpoint ごとに policy map があり、size は `--bpf-policy-map-max`（default 16384）で設定します。

policy 内に異なる CIDR が多数あると、CIDR selector ごとに local-scope identity が作られて増加します。そのため後述の `CiliumCIDRGroup` の使用を検討してください。

### Identity state の確認

```bash
kubectl get ciliumidentities
kubectl get cep -A -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ipcache list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
```

## Policy model の詳細

### Policy resource

| Resource | Scope | 説明 |
|---|---|---|
| Kubernetes `NetworkPolicy` | namespace | L3／L4 |
| `CiliumNetworkPolicy`（CNP、cilium.io/v2） | namespace | L3～L7、entity、FQDN、deny |
| `CiliumClusterwideNetworkPolicy`（CCNP） | cluster | `nodeSelector` による host policy も設定可 |
| `ClusterNetworkPolicy`（policy.networking.k8s.io、v1alpha2） | cluster | **1.20で追加**、alpha API、opt-in が必要 |
| `CiliumCIDRGroup` | cluster | rule から参照する名前付き CIDR set |

Semantics：rule は allow-list であり、複数 rule の効果は union です。enforcement は stateful なので reply traffic は許可されます。ある direction で endpoint を選択する rule が1つでもあると、その direction は default-deny に切り替わります。

### Enforcement mode、default deny、audit mode

| Control | Setting | 効果 |
|---|---|---|
| `policyEnforcementMode`（flag `enable-policy`） | `default`／`always`／`never` | `default`：選択されるまで endpoint は open。`always`：全体で default deny。`never`：policy 無効 |
| rule 内の `enableDefaultDeny: {ingress, egress}` | per-rule | rule が選択しても、その direction は default-deny にしない |
| Helm `enableNonDefaultDenyPolicies` | true | そのような rule の chart-level enablement |
| Audit mode | agent flag `--policy-audit-mode=true`（ConfigMap `policy-audit-mode`）、または endpoint ごと | drop されるはずの packet は drop されず、verdict `AUDIT` で log に記録 |
| `policyDenyResponse` | `none`／`icmp` | `icmp` は experimental で egress のみ |

重要：`enableDefaultDeny: false` は L7 に適用されません。L7 rule に allow-all を併記しないと、その port の他の traffic は引き続き drop されます。

cluster-wide と endpoint ごとの audit mode：

```bash
kubectl -n kube-system patch cm cilium-config --type merge \
  -p '{"data":{"policy-audit-mode":"true"}}'
kubectl -n kube-system rollout restart ds/cilium
# or for one endpoint (host endpoint included):
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled
hubble observe --verdict AUDIT
```

default-deny rollout の最初の段階で audit mode を使います。Hubble の `AUDIT` verdict から、enforce 時に drop される traffic を把握できます。Source：`Documentation/security/policy-creation.rst`。

### Entity

`host`、`remote-node`、`kube-apiserver`、`ingress`、`cluster`、`cluster-mesh`、`init`、`health`、`unmanaged`、`world`、`all`。`world` は `0.0.0.0/0` と同じです。managed platform の一部（上流資料では AKS、GKE）では `kube-apiserver` ingress が動作しないことがあります。agent flag `--allow-localhost=policy` は host から local Pod への暗黙の allow を無効にします。

### Node selector と CIDR

- `fromNodes`／`toNodes` には `nodeSelectorLabels: true`（flag `--enable-node-selector-labels`）が必要です。有効にすると node は remote-node scope identity を持ちます。上流の sizing は `policy-cidr-match-mode=nodes` で1000 node あたり約1 MB です。
- CIDR rule（`fromCIDR`、`toCIDR`、`fromCIDRSet`、`except` 付き `toCIDRSet`）は default では Pod や node に一致しません。`policyCIDRMatchMode`（`--policy-cidr-match-mode`、beta）で `pods` または `nodes` を選ぶと有効になります。`pods` は追加 identity を消費します。`values.yaml` の inline comment には `nodes` のみ記載されていますが、doc は両方を認めています。doc を正としてください。Kubernetes ClusterNetworkPolicy conformance setup は `pods,nodes` を使います。
- **CiliumCIDRGroup** は多数の CIDR を名前付き object にまとめ、group ごとに概ね1 identity を使い、Hubble flow に group 名を表示します。CRD storage version は1.18～1.21で `cilium.io/v2`（v2alpha1 も引き続き serve）。上流 doc の例は v2alpha1 ですが、v2 を使ってください。

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: vpn-example-1
  labels:
    role: vpn
spec:
  externalCIDRs:
  - 10.48.0.0/24
  - 10.16.0.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: from-vpn-example
  namespace: demo
spec:
  endpointSelector: {}
  ingress:
  - fromCIDRSet:
    - cidrGroupRef: vpn-example-1
```

`cidrGroupRef: <name>` または `cidrGroupSelector.matchLabels` で参照します。

### FQDN policy と DNS proxy

`toFQDNs` は `matchName` または `matchPattern` を使います（`*` は1 label に一致、`**.` は複数 label の prefix、`*.cilium.io` は `cilium.io` 自体に一致しません）。agent 内の DNS proxy が DNS response を監視し、解決した IP を FQDN 由来の local-scope identity として登録します。そのため、次の点に注意してください。

- proxy が response を監視できるよう、cluster DNS 宛て egress DNS rule（`toPorts.rules.dns`）が必要です。
- 同じ rule 内で `toFQDNs` と他の L3 selector は併用できません。
- agent 再起動中は DNS proxy が利用できず、DNS request に影響します。
- FQDN は name allow-list であり、reputation check ではありません。IPsec と L7 proxy を併用する場合は `--dnsproxy-enable-transparent-mode=true` が必要です。
- hostname ごとの IP 数上限は doc と code で値が一致しません。説明文にある値を信用するのではなく、利用 version の agent flag `tofqdns-endpoint-max-ip-per-hostname` と Helm `dnsProxy.endpointMaxIpPerHostname` で実効値を確認してください。
- `dnsProxy.preCache`／`--tofqdns-pre-cache` は1.20で deprecated、1.21で削除予定です。standalone DNS proxy は alpha です。

### Deny policy と優先順位

`ingressDeny`／`egressDeny` は CNP、CCNP、Kubernetes NetworkPolicy のすべての allow rule より優先されます。L7 deny と `toFQDNs` deny はありません。実際の評価順は次のとおりです。

| 順序 | Rule class | 結果 |
|---|---|---|
| 1 | Deny rule に一致 | allow rule に関係なく drop |
| 2 | Allow rule に一致 | forward |
| 3 | この direction で endpoint が選択され、どの rule にも一致しない | default deny で drop |
| 4 | この direction で endpoint が選択されない | enforcement mode が `always` でなければ forward |

Kubernetes ClusterNetworkPolicy の tier は Admin、NetworkPolicy（Kubernetes NetworkPolicy、CNP、CCNP）、Baseline の順です。`k8sClusterNetworkPolicy.enabled=true`（default false、flag `--enable-k8s-cluster-network-policy`）で有効化し、network-policy-api project の `release-0.2` CRD を install します。Cilium 1.20では alpha API です。

### Policy の設定例

**DNS と FQDN egress を許可する default deny**（namespace `demo`）。egress rule で endpoint を選択すると egress は default-deny になります。DNS proxy が response を監視できるよう DNS を明示して許可します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-fqdn
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY
      rules:
        dns:
        - matchPattern: "*"
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

EKS の DNS Pod は `k8s-app: kube-dns` label を持つ `coredns` です。distribution によって label が異なる場合は selector を調整してください。

**cluster 内からの traffic のみを許可し、`world` は常に拒否**（Transparent Encryption で説明する平文漏えいの時間帯も塞ぎます）：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cluster-only-ingress
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingress:
  - fromEntities:
    - cluster
```

**default-deny にせず DNS をすべて intercept**（上流 introduction page の記載例そのまま）：`enableDefaultDeny: {egress: false, ingress: false}` を設定し、`kube-system` と `kube-dns` 以外の全 Pod を選択する `CiliumClusterwideNetworkPolicy` で `kube-dns` 宛てに `matchPattern: "*"` の DNS を許可します。これにより DNS proxy が経路上に入り（Hubble で DNS name が見える）、他の traffic の default-deny は有効になりません。

**allow rule に関係なく identity を deny**：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-untrusted
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingressDeny:
  - fromEndpoints:
    - matchLabels:
        trust: low
```

**Host policy の骨組み**（`hostFirewall.enabled=true` が必要です。host endpoint で audit mode から始め、SSH／SSM、kubelet、API server への経路を先に必ず許可してください）：

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: host-ingress-from-cluster
spec:
  nodeSelector:
    matchLabels:
      node-role: worker
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "10250"
        protocol: TCP
```

host endpoint を ingress rule で1つでも選択すると default-deny が適用されるため、このような policy は一致 node 上で SSH を含むその他の traffic をすべて drop します。`cilium-dbg endpoint get -l reserved:host -o jsonpath='{[0].id}'` で host endpoint ID を取得し、先に `PolicyAuditMode=Enabled` を設定します。`hubble observe --verdict AUDIT` を確認してから enforce してください。

### Policy 判定の読み方

```
cilium-dbg endpoint list                       # endpoint ID, identity, ingress/egress enforcement
cilium-dbg endpoint get <ID> -o json           # labels, identity, policy revision
cilium-dbg bpf policy get <ID>                 # the per-endpoint policy map (identity, port, proto, deny flag)
cilium-dbg policy selectors                    # which identities each selector currently matches
hubble observe --pod demo/server --verdict DROPPED -o json   # drop reason and (with correlation) the policy that matched
```

selector の一致 identity 数が想定より少ない場合、identity から除外された label など identity-relevant label の不一致、または namespace-scoped CNP が selector に namespace を暗黙追加していることがよくある原因です。

### CEL による空 policy の拒否（1.20）

1.20の CNP と CCNP CRD には、message が「spec or specs must be provided」の CEL rule `has(self.spec) || has(self.specs)` があります。両 field を指定せず policy を作成または更新すると admission で拒否されます。既存の空 policy は更新するまで影響を受けません。関連する先行変更：`FromRequires`／`ToRequires` は1.19以降空である必要があり、Kafka／proxylib L7 policy は1.20で削除されました。

### Host policy

`nodeSelector` を持つ `CiliumClusterwideNetworkPolicy` は host policy になります。`hostFirewall.enabled=true`（任意で `devices`）が必要です。host namespace と host-network Pod に適用され、L3／L4 と beta の L7 DNS をサポートします。VRRP、IGMP、GRE、IPIP、IPV6、ESP、AH には `--enable-extended-ip-protocols` が必要です。上流の既知問題：IPsec と併用できず、host WireGuard interface には適用されません。また有効化すると未知の L2 protocol は drop されます。L7 DNS host policy は kubelet image pull や agent 再起動を壊す可能性があるため、audit mode から始めてください。

### 1.21 pre-release の追加機能 **[1.21 pre-release]**

CNP egress の `toPorts[].listener` は port を CEC／CCEC Envoy listener に redirect します（同じ port の L7 rule とは併用できません。上流は代わりに Gateway API／GAMMA を推奨）。`--fixed-identity-mapping` は deprecated です。

## Mutual Authentication の timeline（削除済み）

### 仕組み（1.18～1.20）

rule に `authentication: {mode: required}` を設定しました。datapath はこの flag に一致する policy を評価すると BPF map `cilium_auth_map`（524288 entry。key は local identity、remote identity、remote node、auth type）を参照します。有効期限内の entry がない場合、packet を drop（`DROP_POLICY_AUTH_REQUIRED`、-189）して agent に signal を送ります。agent の `pkg/auth` manager は port 4250（`authentication.mutual.port`）で**remote node の agent 宛て**に out-of-band の TLS 1.3 connection を開始し、SPIRE agent socket から取得した SPIFFE SVID（identity は `spiffe://spiffe.cilium/identity/<numeric-id>`）を提示し、peer certificate を検証して最も早い expiry を auth map に保存しました。再送された packet はその後通過します。重要なのは handshake が**agent 間**で行われ、connection ごとでも data path 上でもなかった点です。WireGuard または IPsec も有効にしない限り、application traffic は暗号化されません。既知の制限：ClusterMesh 非対応、SPIRE のみ検証済み、外部 mTLS との相互運用なし。

### Timeline と対応

| Release | 状態 | 対応 |
|---|---|---|
| 1.18、1.19 | Beta。1.19では `authentication.enabled` の default が false で、`authentication` 付き policy は validation warning を出しつつ auth なしで通過 | 現状維持または移行 |
| 1.20 | Deprecated（doc 上では引き続き Beta） | ztunnel（`encryption.type=ztunnel`）または network encryption と identity policy への移行を計画 |
| 1.21 | 削除。agent の `pkg/auth` と `mesh-auth-*` flag はなくなり、`authentication` policy field は受理されるが未使用 | upgrade **前に** `authentication.*` Helm value と SPIRE mutual-auth config を削除 |

移行手順：

1. `authentication` を使う policy を洗い出します：`kubectl get cnp,ccnp -A -o yaml | grep -n "authentication"`。
2. 本当に必要だった要件を確認します。「通信時に暗号化」が目的なら WireGuard または IPsec（[下記](#transparent-encryption)）、「workload identity の認証」なら ztunnel mTLS または mesh（Istio）を使います。
3. 1.21で field が enforce されると考えてはいけません。上流によると互換性のため受理されますが未使用です。したがって `required` に依存していた policy も認証を要求しなくなります。runtime で agent がどう通知するかは未検証です。
4. 1.21でも `authentication.mutual.spire.*` chart value が残るのは、SPIRE install と operator の SPIRE client を ztunnel `ca.type=spire` が再利用するためです。mutual authentication の設定にはなりません。
5. Hubble `dropEventEmitter.reasons` には1.21から `auth_required` がありません。

## ztunnel workload mTLS（1.19からBeta）

### Architecture

`encryption.type=ztunnel` は Cilium 自身を control plane として、Istio の node ごとの L4 proxy（ztunnel の考え方）を実行します。

```
 enrolled Pod A (netns)                         enrolled Pod B (netns)
  app --> iptables (in-pod) --> :15001           :15008 (HBONE in) --> ztunnel --> :15006 --> app
                                   |                  ^
                                   v                  |
                    node A ztunnel (DaemonSet, hostNetwork)  ==HBONE: HTTP/2 CONNECT over mTLS, TCP 15008==> node B ztunnel
                                   ^   xDS (workloads)   ^ CSR to Cilium CA
                                   |                     |
                     Cilium agent: xDS/ADS server, ZDS unix socket (/var/run/cilium/ztunnel.sock),
                                   built-in CA (IstioCertificateService), enrollment reconciler
```

- 各 node で `ztunnel-cilium` DaemonSet（hostNetwork、container は `istio-proxy`）が動きます。1.20／1.21 の image は `quay.io/cilium/ztunnel:v1.0.0`、1.19では `docker.io/istio/ztunnel` 1.28.0-distroless でした。
- agent は CEP から workload data を xDS で提供し、Pod network namespace の file descriptor と metadata を ZDS unix socket 経由で渡します。node 上に endpoint がある service account 用に、URI SAN が `spiffe://<trust domain>/ns/<ns>/sa/<sa>` の workload CSR に署名します。
- iptables rule は**enroll 済み Pod ごとの netns 内**に入ります。outbound は15001、平文 inbound は15006へ redirect し、HBONE inbound の15008は redirect しません（mark 0x539）。wire protocol は **TCP 15008** 上の HBONE（mTLS 上の HTTP/2 CONNECT）です。
- Istio ambient との違い：istiod、waypoint、L7 feature がありません。enrollment は `istio.io/dataplane-mode=ambient` ではなく label `io.cilium/mtls-enabled=true` で行います。CA は Cilium 内蔵 CA または SPIRE です。同じ Pod に両方を適用しないでください。

### Secret、CA type、enrollment

install 前に bootstrap と CA の key material を生成してください（upstream repository の `examples/kubernetes-ztunnel/generate-secrets.sh`）。`kube-system` の `cilium-ztunnel-secrets` Secret は `bootstrap-private.key`、`bootstrap-root.crt`、`ca-private.key`、`ca-root.crt` を保持します。上流の説明では、bootstrap pair は ztunnel から Cilium の xDS／certificate server への connection を保護します。CA pair は memory 内で生成する短命 workload certificate の root です。

```yaml
# values-ztunnel.yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal   # default; "spire" is new in 1.20
```

| `encryption.ztunnel.ca.type` | 動作 |
|---|---|
| `internal`（default） | Cilium 内蔵 CA が workload certificate に署名。SPIRE reconciler は不要 |
| `spire`（1.20以降） | 外部 SPIRE server が identity を発行。operator は enroll 済み namespace の service account ごとに entry を登録（parent `/ztunnel`、path `/ns/<ns>/sa/<sa>`） |

`spire` mode は上流の encryption guide には記載されていません。このレビューでは operator code path のみ確認し、end-to-end deployment は検証していません。高度な option として扱い、別途テストしてください。

namespace を enrollment／解除する方法：

```bash
kubectl label namespace demo io.cilium/mtls-enabled=true
kubectl label namespace demo io.cilium/mtls-enabled-      # disenroll
```

ztunnel Pod を除く namespace 内の既存 Pod と、今後作成する Pod がすべて enroll されます。enrollment は namespace 単位のみで、host-network Pod は対象外です。

### 制限

| 制限 | 詳細 |
|---|---|
| 両 peer の enrollment | enroll 済みから未登録への traffic は非対応 |
| TCP のみ | UDP などは redirect されない |
| Policy との関係 | Pod を出る前に暗号化するため L4 policy は inner port を確認できない。対象にできるのは HBONE port 15008のみ |
| Kernel | iptables 対応が必要 |
| ClusterMesh | 非互換。有効化を両立すると validation error |
| Enrollment | namespace label のみ。Pod 単位では設定不可 |

EKS では peer が同じ VPC 内にあるため、node security group で node 間の TCP 15008 を許可してください。node security group 自身を source として相互参照し、public CIDR は使わないでください。

### 確認

```bash
kubectl -n kube-system describe cm cilium-config | grep enable-ztunnel -A2
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system exec ds/cilium -- cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'
# inside a Cilium Pod on the node hosting an enrolled Pod (install tcpdump first)
tcpdump -i eth0 port 15008      # use cilium_vxlan when tunnelling
```

## 透過暗号化 {#transparent-encryption}

default では Cilium 管理の Pod traffic のうち node 間を通過するものだけを暗号化します。同じ node 内の traffic は暗号化しません。node がまだ学習していない endpoint への egress は平文で送られる場合があります。判定には同じ ipcache／policy mechanism を使うためです。strict mode、または `world` を deny する egress policy で対処します。

### Encryption packet walk

```
Pod A (node 1) -> Pod B (node 2), WireGuard, tunnel mode

 Pod A veth --> bpf_lxc: policy ok, ipcache says dst is remote Cilium endpoint
            --> encryption marks the packet (dst is a managed remote endpoint)
            --> VXLAN/Geneve encapsulation (cilium_vxlan / cilium_geneve)
            --> routed into cilium_wg0 (WireGuard: UDP 51871, peer chosen by CiliumNode pubkey)
            --> NIC (outer IP: node 1 -> node 2)
 NIC (node 2) --> cilium_wg0 decrypt --> tunnel decapsulation --> bpf_lxc ingress policy --> Pod B

Native routing: the VXLAN/Geneve steps are absent; the inner packet is Pod A -> Pod B directly
inside WireGuard. IPsec uses the same decision point but the XFRM state for (src node, dst node)
applies ESP after encapsulation.
```

これは概念上の要約であり、BPF program が実行される厳密な順序を trace したものではありません。program layout は [Part 8](08-ebpf-datapath-internals.md) を参照してください。ここから2つの帰結があります。第1に「宛先は管理対象の remote endpoint か」という判定は ipcache から得るため、未学習宛先は外部として扱われ、平文漏えいの時間帯が生まれます。第2に encryption は policy 適用と encapsulation の後に行うため、物理 NIC 上で host capture すると ciphertext のみが見え、`cilium_wg0` 上では inner packet を確認できます。

### WireGuard（stable）

仕組み：各 agent が key pair を生成し、公開 key を `CiliumNode` annotation `network.cilium.io/wg-pub-key` に公開します。device `cilium_wg0` 上に他 node ごとの WireGuard peer を作成します。全 node で UDP port **51871** を使います。kernel WireGuard（`CONFIG_WIREGUARD`、Linux 5.6以降、または out-of-tree module）が必要です。tunnel mode では Pod traffic は二重 encapsulation されます。最初に VXLAN／Geneve、次に WireGuard であり、これが MTU に影響します（[Part 9](09-overlay-native-routing.md)）。

```yaml
encryption:
  enabled: true
  type: wireguard
  wireguard:
    persistentKeepalive: 0s
```

- CNI chaining（AWS VPC CNI）では `cni.enableRouteMTUForCNIChaining=true` を設定してください。そうしないと暗号化 Pod traffic が fragment される場合があります。
- ClusterMesh では全 cluster で WireGuard を有効にし、cluster 間で UDP 51871 を許可します。
- device の設定中に packet が drop する既知の問題があります（upstream gh-33159）。
- **Node 間暗号化**（`encryption.nodeEncryption`、beta）は host traffic に範囲を広げます。control-plane node は `node-encryption-opt-out-labels` で除外できます。XDP または Geneve ではない DSR を使う north-south path に穴があります。**[1.21 pre-release]** deprecated、1.22で削除予定です。

### Strict mode

| Helm value | 意味 |
|---|---|
| `encryption.strictMode.egress.enabled` | strict CIDR 宛てに node から出る平文 traffic を drop |
| `encryption.strictMode.egress.cidr` | 適用する Pod CIDR（IPv4 のみ。IPv6 は保護しない） |
| `encryption.strictMode.egress.allowRemoteNodeIdentities` | tunneling 使用時、または node／Pod CIDR が重複する場合に必要 |
| `encryption.strictMode.ingress.enabled` | WireGuard 経由で到着しない cluster 内 ingress を drop。**WireGuard のみ** |

Ingress strict mode（1.19以降）は1.20.2 doc では tunnel と native routing の両方に対応します（1.19 upgrade note では tunnel が必要とされていました）。制限：CNI chaining 非対応、node 間 traffic は保護しません。また Pod traffic を運べる全 interface に Cilium BPF が attach されていることが前提です。

**1.20の flag rename**：旧 flag `--enable-encryption-strict-mode`、`--encryption-strict-mode-cidr`、`--encryption-strict-mode-allow-remote-node-identities`（1.19でdeprecated）は**削除**されました。`--enable-encryption-strict-mode-egress`、`--encryption-strict-egress-cidr`、`--encryption-strict-egress-allow-remote-node-identities`、`--enable-encryption-strict-mode-ingress` を使ってください。Helm value は `encryption.strictMode.{enabled,cidr,allowRemoteNodeIdentities}` から `encryption.strictMode.egress.*` に移りました。1.20 upgrade note では CIDR key を `cidrs` としていますが、1.20.2 chart `values.yaml` は `cidr` です。chart を正としてください。

### IPsec（stable）

仕組み：agent は Secret の pre-shared key を使って Linux XFRM state と policy を設定します。packet は overlay encapsulation があればその後に ESP encapsulation されます（順序は1.18以降修正済みで、`encryptedOverlay` option は削除）。

```bash
kubectl create -n kube-system secret generic cilium-ipsec-keys \
  --from-literal=keys="3+ rfc4106(gcm(aes)) $(dd if=/dev/urandom count=20 bs=1 2>/dev/null | xxd -p -c 64) 128"
```

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyWatcher: true
    keyRotationDuration: 5m
```

- Secret value の format は `key-id algorithm PSK-hex key-size` です。key ID の後の `+` は**tunnel ごとに派生する key**を強制します。global key は1.16で非推奨になりました（GHSA-pwqm-x5x6-5586）。
- Rotation では key ID 1～15を使い、再 keying のたびに増やします。15の次は1に戻ります（`encryption-ipsec.rst:206-218`。上流 snippet は15以上で `KEYID` を0に戻します）。単純に「IDを増やす」だけでは wrap 時に失敗します。ID 15の次の Secret は1にしてください。Secret を次の ID に更新すると agent が監視します（`keyWatcher`）。agent は `keyRotationDuration` に最大その1/10の jitter を加えた時間が経過してから旧 key を削除します。upgrade 中に rotation しないでください。ClusterMesh では全 cluster で rotation します。
- direct routing には `ipv4NativeRoutingCIDR` が必要です。CNI chaining 非対応。最大65535 node で、tunnel の decryption は1 CPU core に bind されます。
- `cilium-dbg encrypt status`（使用中の key、XFRM error counter）と `tcpdump -l -n -i eth0 esp` で確認します。security group では node 間 ESP（IP protocol 50）を node security group 自身の参照で許可します。UDP 500／4500 の要否はこのレビューでは検証していません。
- **1.20で削除**：`encryption.ipsec.interface`（`--encrypt-interface`。1.18以降 no-op）と `encryption.ipsec.encryptedOverlay`。1.20.2 chart `values.yaml` と IPsec guide には `interface` が残るため上流に不整合があります。設定しないでください。
- **Host policy は IPsec と併用できません**（upstream gh-41854）。

### MTU overhead

暗号化 header 分だけ使用可能な Pod MTU が減り、tunnel mode ではさらに tunnel header が加わります。Cilium は route MTU を自動計算します。CNI chaining では `cni.enableRouteMTUForCNIChaining` を設定してください。Part 9 では v1.20.2 の `pkg/mtu/mtu.go` から byte 数を計算しています：WireGuard 95、default key size の IPsec 77、IPv4 underlay 上の VXLAN 50。[MTU の計算](09-overlay-native-routing.md) を参照してください。実測値ではないため、Pod 間で `ping -M do -s <size>` を実行し、Cilium device 上で `ip link` を確認してください。

### 選択

| 要件 | 選択肢 |
|---|---|
| key 管理不要のシンプルな Pod-to-Pod network encryption | WireGuard |
| FIPS／compliance または WireGuard 非対応 kernel。key rotation の運用は許容 | IPsec |
| 暗号化 channel を workload identity に紐付け、namespace 単位で opt-in。TCP のみ | ztunnel |
| cluster 間（ClusterMesh） | WireGuard または IPsec（ztunnel 非互換） |
| L7-aware mTLS、authorization、waypoint | Istio |

## Service Mesh の TLS option

| Option | 機能 | 注意点 |
|---|---|---|
| Istio sidecar | sidecar 間 mTLS、Istio の L7 policy | Cilium と Istio で HTTP rule を二重適用しないでください。対象 Pod で Cilium L7 を使う場合は Istio `PeerAuthentication` の mTLS を `DISABLE` にします |
| Istio ambient | ztunnel／HBONE 15008、任意の waypoint | Cilium からは15008上の暗号化 L4 のみ見えます。Cilium L7 を適用するには `istio.io/dataplane-mode` を削除するか、Pod に `ambient.istio.io/redirection: disabled` annotation を付けます |
| Cilium ztunnel | L4 mTLS のみ | 上記参照 |
| Cilium の Envoy TLS（CEC／Gateway API） | Envoy で TLS terminate／originate | ingress／egress の可視化向け。east-west の mesh mTLS ではありません |

Istio との共存（upstream `network/servicemesh/istio.rst`）：`kubeProxyReplacement=false` を推奨します。replacement を有効にする場合は `socketLB.hostNamespaceOnly=true` と `cni.exclusive=false` を設定します。overlay 上で sidecar を使う場合、istiod は `hostNetwork: true` が必要です。[Part 5](05-l2-l7-networking.md) も参照してください。

**TLS interception**（CNP `toPorts` の `terminatingTLS`／`originatingTLS`）：Envoy は internal CA の certificate で client TLS を terminate します。client はその CA を信頼する必要があり、その後 Envoy は宛先へ再接続します。Secret は SDS で渡されます（1.17以降の default）。Helm `tls.secretsNamespace.name` の default は `cilium-secrets`、`tls.readSecretsOnlyFromSecretsNamespace` は true です。operator は参照された Secret をその namespace にコピーします。暗号化 egress に対する L7 policy の可視性を提供しますが、mesh mTLS の代わりではありません。

**Gateway API TLS**：HTTPS listener の terminate には Secret を使います。`BackendTLSPolicy`（gateway.networking.k8s.io/v1。Service を指定する `targetRefs`、ConfigMap を指定する `validation.caCertificateRefs`、および `hostname`）は Envoy から backend までの traffic を暗号化します。Cilium 1.20は Gateway API v1.6.1 CRD が必要です。TLSRoute は v1 であり、以前の object がある場合は experimental channel が必要です。そうしないと既存 object が消えたように見えます。cert-manager は `cert-manager.io/issuer` annotation で連携します。**公開範囲に関する規則**：上流の Gateway／Ingress 例は `Service` type `LoadBalancer` を作成します。EKS では CloudFront VPC origin の背後に internal scheme（`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`）を使い、internet-facing にしないでください。この項目は今回 Cilium chart で検証していません。[Part 11](11-bgp-lb-egress-edge.md) を参照してください。

## Hubble と Tetragon

### Hubble component

Hubble server は各 agent 内で動きます（`hubble.listenAddress` 上の gRPC、default `:4244`、および unix socket `/var/run/cilium/hubble.sock`）。**Relay**（`hubble.relay.enabled`、default false、port 4245で listen）は全 node を1つの API に集約します。**UI**（`hubble.ui.enabled`、default false）は Relay を使います。Server と Relay は default で mTLS を使います（`hubble.tls.enabled: true`）。Relay と UI は ClusterIP（または CloudFront VPC origin の背後にある internal LB）にし、外部公開しないでください。

Event path：datapath event、agent ごとの ring buffer（`hubble.eventBufferCapacity`、default 4095、2^n-1から最大65535）、observer（CLI、Relay、exporter、metric）の順です。`hubble.networkPolicyCorrelation.enabled`（default true）は flow に allow／deny した policy を追加します。

### Metric

`hubble.metrics.enabled` には handler の list を指定します。例：`dns`、`drop`、`tcp`、`flow`、`port-distribution`、`icmp`、`httpV2`、`flows-to-world`、`policy`。`sctp` は1.20で追加（v1.19.8では handler なし）。endpoint port は9965です。Dynamic metric（`hubble.metrics.dynamic.enabled`、ConfigMap `cilium-dynamic-metrics-config`）は agent 再起動なしで再設定できます。L7 handler が出力するのは L7 visibility を設定した Pod の data のみです。Kafka handler は1.20で削除されました。`hubble.metrics.portName` **は[1.21 pre-release]** の新機能です。

### Exporter

- Static：`hubble.export.static.enabled`、`filePath`（default `/var/run/cilium/hubble/events.log`。`stdout` も可）、`fileMaxSizeMb`、`fileMaxBackups`、`fileCompress`、`allowList`、`denyList`、`fieldMask`。`fieldAggregate` と `aggregationInterval` は1.19以降。agent lifecycle に従います。
- Dynamic：`hubble.export.dynamic.enabled` と `config.content[]` entry（`name`、`filePath`、`fieldMask`、`includeFilters`、`excludeFilters`、`end`、rotation field）を使います。ConfigMap `cilium-flowlog-config` に保存され、再起動なしで適用（変更は約1分で反映）されます。

### Redaction（L7）

`hubble.redact.enabled`（default false）、`http.urlQuery`（false）、`http.userInfo`（true）、および `http.headers.allow` または `deny`（併用不可）を設定します。例として `Authorization` と `Proxy-Authorization` を deny できます。Kafka 対応とともに Kafka `apiKey` の redaction は1.20で削除されました。

```yaml
hubble:
  redact:
    enabled: true
    http:
      urlQuery: true
      userInfo: true
      headers:
        deny:
        - Authorization
        - Proxy-Authorization
```

### Drop event

`hubble.dropEventEmitter`（alpha）は drop された traffic の Kubernetes Event を送信します。`interval` は2分。1.20.2での `reasons` default は `auth_required` と `policy_denied` ですが、1.21では `auth_required` は含まれません。

### Tetragon（概要のみ）

Tetragon は Cilium repository に含まれない別 project です。`TracingPolicy` resource で設定する、process execution、file、network activity 向けの eBPF runtime security 可視化と enforcement を提供します。Cilium threat-model doc は runtime visibility 用に Tetragon を推奨しています。CRD version と enforcement action の詳細は**このレビューで未検証**のため、この節は概要のみです。具体的な情報は Tetragon project の doc を参照してください。

## Certificate 管理

| Component | Certificate source | Rotation |
|---|---|---|
| Hubble server、Relay、metric | `hubble.tls.auto.method`：`helm`（default）、`cronJob`、`certmanager` | `helm`：Helm render 時のみ再生成（自動更新なし）。`cronJob`：certgen CronJob、schedule は `0 0 1 */4 *`。`certmanager`：cert-manager が更新。`certManagerIssuerRef` を指定 |
| ClusterMesh API server | 同じ3方式を `clustermesh.apiserver.tls.auto` 以下で指定 | [Part 13](13-clustermesh-install-upgrade.md) を参照 |
| ztunnel workload | internal CA または SPIRE | memory 内で短命 |
| IPsec／WireGuard | PSK Secret／自動 key pair | IPsec は手動 rotation、WireGuard は自動 |

知っておくべき value（1.20.2 `values.yaml`）：`hubble.tls.auto.certValidityDuration` の default は **365日**、共有 auto-generated CA の `tls.ca.certValidityDuration` は **1095日**です。他の上流 prose では leaf certificate も3年とされていますが、適用されるのは chart value です。Server、Relay certificate と CA は hot-reload されます。

1.20での変更：

- ClusterMesh の auto certificate の default は1年になりました（`clustermesh.apiserver.tls.auto.certValidityDuration: 365`。1.19では1095）。`helm` method では chart render 時にだけ更新されるため、少なくとも毎年 upgrade してください。`cronJob` と `certmanager` は自動更新します（ClusterMesh の cronJob は4か月ごとに再生成）。
- `certgen.enforceCAValidityThroughoutLeavesDuration` の default は true です。CA の期限が leaf certificate より先に切れる場合、certgen は失敗します。false にすると無効化できます。
- Helm value から手動で certificate を渡す機能が削除されました。Secret を事前作成し、`tls.auto.enabled=false` にします。
- `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` は `...tls.auto.server.*` に移りました。

user 提供の Hubble certificate に必要な SAN：`*.<cluster>.hubble-grpc.cilium.io`（server）、`*.hubble-relay.cilium.io`（Relay）、`*.hubble-ui.cilium.io`、`<cluster>.hubble-metrics.cilium.io`。Secret は `tls.crt`、`tls.key`、`ca.crt` を持ちます。**[1.21 pre-release]** Pod ごとの certificate では `hubble.tls.disableDefaultVolumes`、`hubble.relay.tls.disableDefaultVolumes`、`hubble.ui.tls.disableDefaultVolumes` と `extraInitContainers` を使い、Vault、cert-manager CSI、SPIFFE などの source を利用できます。`clustermesh.apiserver.tls.authMode` の default は `cluster` になります。

```yaml
hubble:
  tls:
    auto:
      enabled: true
      method: certmanager
      certManagerIssuerRef:
        group: cert-manager.io
        kind: ClusterIssuer
        name: hubble-issuer
```

## Labs

このレビューでは live cluster で lab を実行していません（Validation Limits 参照）。使い捨て cluster を使ってください。security group に関する記載は node security group 自身を参照する node 間 rule を前提とします。どの port も `0.0.0.0/0` や `::/0` に対して開けないでください。

### Lab 1: Identity、ipcache、label exclusion

前提条件：Cilium 1.20.2 cluster、kubectl、agent Pod 経由の `cilium-dbg`。

1. namespace を作成し、`web`（`app=web`）と `db`（`app=db`）の Deployment を1つずつ配置し、それぞれ replica を2つにします。
2. `kubectl get ciliumidentities` を実行します。`web` と `db` の label set ごとに identity が1つずつあり、各 replica が共有することを確認します。
3. `kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list` で `web` と `db` の ID を記録します。
4. `web` Pod IP を1つ選び、`cilium-dbg bpf ipcache list | grep <podIP>` を実行します。entry の identity が `web` identity と同じです。
5. `kubectl label pod <pod> release=r2 --overwrite` で `web` Pod 1つの label を変更します。その Pod 用の新しい identity が作られ、`kubectl get ciliumidentities` が1増えることを確認し、label churn を観察します。
6. 後片付け：namespace を削除します。Helm で identity-relevant label を変更した場合は `helm upgrade` で戻し、agent を再起動します（identity が変わるのは agent 再起動後です）。`--reuse-values` が有効なのは cluster がすでにこの chart version 1.20.2 の場合のみです。それ以外では保存済み value を明示してください。

### Lab 2: strict ingress を伴う WireGuard

前提条件：kernel WireGuard を使える node。node security group で node security group 自身からの UDP 51871 を許可します。

1. `helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values --set encryption.enabled=true --set encryption.type=wireguard` を実行します。rollout が進まなければ agent を再起動します。`--reuse-values` は cluster がすでに chart 1.20.2 を使う場合のみ有効です（chart version は変えてはいけません。upstream `upgrade.rst:206-221`）。別 version の場合は `helm get values cilium -n kube-system -o yaml` で保存し、rename された value を確認して `-f` で渡します。
2. `kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep Encryption` を実行します。node 数から1を引いた値が N に入る `Wireguard [cilium_wg0 (...Port: 51871, Peers: N)]` の行が表示されるはずです。
3. 異なる node 上の Pod 間で traffic を発生させ、agent Pod 内で `tcpdump -n -i cilium_wg0` を実行します。`cilium_wg0` では平文の Pod-to-Pod flow、物理 interface では UDP 51871 の暗号化 packet のみ確認できます。
4. `--set encryption.strictMode.egress.enabled=true --set encryption.strictMode.egress.cidr=<podCIDR> --set encryption.strictMode.ingress.enabled=true` で strict mode を有効にします。tunneling 使用時は `allowRemoteNodeIdentities=true` も設定します。
5. 通常の Pod traffic は継続します。WireGuard を迂回する平文 Pod traffic は drop されます（そのような packet の注入には host-level tool が必要なため任意）。
6. Rollback：strict value を先に false にしてから `encryption.enabled=false` とし、agent を再起動します。device の再設定中に短い drop が発生することがあります（上流の既知問題）。

### Lab 3: ztunnel enrollment

前提条件：ClusterMesh なし、iptables 対応 node、node security group で node 間 TCP 15008 を許可。

1. 同じ tag の Cilium source tree で `bash examples/kubernetes-ztunnel/generate-secrets.sh` を実行します（`kube-system` に `cilium-ztunnel-secrets` を作成）。
2. `encryption.enabled=true`、`encryption.type=ztunnel` で upgrade します。`kubectl -n kube-system get ds ztunnel-cilium` と `describe cm cilium-config | grep enable-ztunnel -A2` で確認します。
3. `mtls-on` と `mtls-off` namespace を作成し、それぞれに HTTP server と curl client を置きます。`kubectl label ns mtls-on io.cilium/mtls-enabled=true` で `mtls-on` のみ label を付けます。既存 Pod は自動で enroll され、再起動は不要です。
4. `cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'` に `mtls-on` が出ることを確認します。
5. 別 node 上にある `mtls-on` の client から同 namespace の server に接続し、node 上で `tcpdump -i eth0 port 15008` を実行すると HBONE packet が見えます。
6. `mtls-on` の client から `mtls-off` の server への接続は、enroll 済み／未登録間の traffic が非対応のため失敗する想定です。
7. 後片付け：`kubectl label ns mtls-on io.cilium/mtls-enabled-`、namespace を削除し、その後 `encryption.enabled=false` にして `cilium-ztunnel-secrets` を削除します。

### Lab 4: Policy audit、CIDR group、deny

1. namespace `pol` を作り、`client` と `server` Pod（8080で HTTP）を起動します。
2. server endpoint の audit mode を有効にします：`cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled`。
3. `app=client` からの8080 ingress のみを server に許可する CNP を適用します。3つ目の Pod から server に curl し、`hubble observe --verdict AUDIT -n pol` を実行します。第三の Pod は `AUDIT` verdict になりますが request は成功するはずです。
4. `PolicyAuditMode=Disabled` にし、再実行します。今度は request が drop され、`hubble observe --verdict DROPPED` に出ます。
5. 上記 manifest の `CiliumCIDRGroup` と `cidrGroupRef` を使う `toCIDRSet` egress rule を追加します。`cilium-dbg identity list` に CIDR 由来 identity が出て、flow に group が注釈されることを確認します。
6. `app=client` に対する `ingressDeny` rule を追加します。allow rule があっても deny が優先され、client が drop されます。
7. 後片付け：namespace と CCG を削除します。

### Lab 5: Hubble export、redaction、cert-manager

前提条件：cert-manager と ClusterIssuer が install 済み。

1. Relay と dynamic export を有効にします：`hubble.relay.enabled=true`、`hubble.export.dynamic.enabled=true`、`hubble.redact.enabled=true`、`hubble.redact.http.urlQuery=true`、および `certManagerIssuerRef` を使った `hubble.tls.auto.method=certmanager`。
2. `cilium-flowlog-config` ConfigMap を編集し、`source_pod: ["kube-system/"]` などの `includeFilters` を含む exporter を追加します。agent 再起動なしで agent Pod 内の Hubble export directory に新しい file が現れます（約1分待ちます）。
3. query string と `Authorization` header を使う L7-visible HTTP traffic を発生させます（可視化には Pod の L7 policy が必要です）。`hubble observe -o json` に query／header value が redacted で表示されます。
4. `kubectl get certificate -n kube-system` を実行し、Hubble certificate が ClusterIssuer から発行されたことを確認します。
5. Rollback：exporter entry を削除し、`hubble.redact.enabled=false` にして certificate method を戻します。

## Version 差分

| Topic | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication | Beta | Beta、default で無効（`authentication.enabled=false`） | Deprecated | 削除。policy の `authentication` field は未使用 |
| ztunnel | - | 導入（beta）。起動 validation はすでに ClusterMesh を拒否（`pkg/ztunnel/cell.go:46`） | `ca.type` は internal／spire、image は `quay.io/cilium/ztunnel` | Beta。`ca.type=spire` 用に SPIRE chart を再利用 |
| Strict mode flag | `strictMode.{enabled,cidr,allowRemoteNodeIdentities}` のみ | `strictMode.egress.*` と `strictMode.ingress.*` を追加。旧 flag はdeprecated | 旧 flag（`...-egress-*` 名）を削除 | 変更なし |
| IPsec | `encryptedOverlay` は no-op | - | `encryptedOverlay` と `ipsec.interface` を削除 | - |
| WireGuard `nodeEncryption` | 未確認 | 未確認 | beta | Deprecated、1.22で削除予定 |
| Policy | Kafka／proxylib deprecated | `FromRequires`／`ToRequires` は空が必須 | Kafka／proxylib 削除。CEL は空 CNP／CCNP を拒否。ClusterNetworkPolicy | `toPorts[].listener` redirect |
| Hubble | - | export の `fieldAggregate`／`aggregationInterval` | Kafka metric と redaction を削除。ClusterMesh cert default 1年。certgen CA-validity check | Pod ごとの certificate、`portName`、UI `httpRoute` |
| Identity | Double Write を文書化 | 文書化 | 文書化 | `preflight migrate-identity` はdeprecated |

## Troubleshooting

| 症状 | 主な原因 | 確認 |
|---|---|---|
| 新しい Pod からの traffic が一時的に policy drop | Pod がまだ `reserved:init`、または ipcache が未伝播 | `cilium-dbg endpoint list`、`cilium-dbg bpf ipcache get <ip>` |
| `fromEntities: cluster` が NodePort traffic に予想外に一致／不一致 | routing mode によって source identity が `world` または `remote-node` | 上記 entity の注意点、identity を `hubble observe` で確認 |
| Identity 数が増え続ける | 変動する label が identity 対象 | `kubectl get ciliumidentities \| wc -l`、label を除外 |
| CNP の `kubectl apply` が「spec or specs must be provided」で拒否 | 1.20の CEL rule | `spec` または `specs` を指定 |
| WireGuard peer 数が不正、または `cilium_wg0` がない | kernel module 不足、または node 間 UDP 51871 が遮断 | `cilium-dbg status \| grep Encryption`、node security group |
| 暗号化中に大きな packet が停止 | encryption と tunnel の header 分を引いた MTU を超過 | `ping -M do` で確認し CNI chaining flag を確認 |
| IPsec error counter が増加 | key 不一致または stale XFRM state | `cilium-dbg encrypt status`。key rotation で stale state を消去 |
| IPsec 使用時に host policy が効かない | 非対応の組み合わせ | WireGuard を使うか host policy を外す |
| namespace を enroll したが HBONE packet がない | peer の片方しか enrollment されていない、host-network Pod、または UDP traffic | `statedb dump`、Pod type、protocol |
| ztunnel 有効化後に agent が起動しない | ClusterMesh が有効 | どちらかを無効化 |
| 1年後に Hubble Relay certificate error | `helm` method は自動更新しない | `cronJob`／`certmanager` に変更するか年1回 Helm upgrade |
| 1.21後 `authentication` policy が認証しない | feature 削除済み | 上記の移行手順を実施 |

## 検証範囲と情報源

このレビューでは live cluster 上で lab を実行せず、下記 tag の上流 source と文書に照らして確認しました。Tetragon、ztunnel `ca.type=spire` の end-to-end flow、IPsec ESP／UDP の firewall 要件、残存 `authentication` policy field の runtime 動作は未検証で、その旨を本文に記載しています。**[1.21 pre-release]** は v1.21.0-pre.3 に基づき、GA 前に変わる可能性があります。上流内の不一致として、FQDN hostname ごとの IP 上限（doc と code の default）、prose と `values.yaml` における Hubble certificate default lifetime、storage は v2 なのに `CiliumCIDRGroup` doc が v2alpha1 を示す点、`policyCIDRMatchMode` の values comment は採用していません。

- [1.20 upgrade notes](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)、[Mutual Authentication (1.20)](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)、[policy overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/policy.rst)
- [Transparent encryption](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption.rst)、[WireGuard](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-wireguard.rst)、[IPsec](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-ipsec.rst)、[CNP CEL rule](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/v2/cnp_types.go)
- [1.21 upgrade notes (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc)、[ztunnel guide (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/network/encryption-ztunnel.rst)、[identity allocation and Double Write](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade.rst)、[numeric identity](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/identity/numericidentity.go)、[policy layer 3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/policy/layer3.rst)、[Hubble TLS](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/tls.rst)、[Hubble export](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/export.rst)

## Quiz

[mTLS、暗号化、identity の理解度を確認](../../quizzes/networking/cilium/12-mtls-encryption-identity-quiz.md)。

[Main Page に戻る](README.md)
