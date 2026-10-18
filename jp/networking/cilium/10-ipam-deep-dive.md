# Part 10: IPAM 詳細

> **レビュー基準**: Cilium 1.20.2（安定版、2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。**[1.21 pre-release]** と記した項目は v1.21.0-pre.3 に基づいており、GA 前に変更される可能性があります。
> **最終更新**: 2026年10月15日

[Part 4](04-ipam-policy.md) では IPAM mode と Helm の設定例を紹介しました。この章では内部の動きを扱います。各 address を管理する主体、`cilium-cni ADD` から endpoint 稼働までの処理、インストール前の pool サイズ計算、ENI allocator が EC2 API を呼び出す判断、LB IPAM と Node IPAM が Pod IPAM とどう違うかを説明します。[Overlay と Native Routing](09-overlay-native-routing.md)（address の route 方法）および [BGP、Load Balancing、Egress、Edge](11-bgp-lb-egress-edge.md)（LB address の広報方法）と対になる章です。

## IPAM とは何か、何ではないか

Kubernetes cluster では4種類の address をそれぞれ異なる主体が割り当てます。これらの混同が「IPAM」関連の問題を引き起こす最も一般的な原因です。

| Address | 管理主体 | Cilium の関与 |
|---|---|---|
| Pod（endpoint）IP | Cilium IPAM（この章と各 mode の subsection） | 割り当て、追跡、解放 |
| Service ClusterIP | kube-apiserver（`--service-cluster-ip-range`） | なし。Cilium は datapath に登録するだけ |
| LoadBalancer Service IP | LB IPAM（`CiliumLoadBalancerIPPool`）または cloud controller | Operator が割り当てるだけ。広報は別（BGP Control Plane または L2 Announcements） |
| LoadBalancer として使う node address | Node IPAM（`loadBalancerClass: io.cilium/node`） | Operator が node address を Service status にコピー |

`CiliumPodIPPool` は ClusterIP を割り当てず、`CiliumLoadBalancerIPPool` は Pod IP を割り当てません。`CiliumCIDRGroup`（以下の CiliumCIDRGroup を参照）は何も割り当てません。policy から参照する名前付き CIDR 集合です。

## 全体像：CiliumNode の handshake

ほとんどの mode は、node ごとに1つある `CiliumNode` custom resource（node と同じ名前）を介して2つの component がやり取りします。

```
                        +-----------------------------+
                        |        CiliumNode <node>    |
                        |  spec.ipam.podCIDRs         |  cluster-pool
                        |  spec.ipam.pools.requested  |  multi-pool / eni (agent writes)
                        |  spec.ipam.pools.allocated  |  multi-pool / eni (operator writes)
                        |  spec.ipam.pool             |  crd (external allocator writes)
                        |  status.ipam.*              |  used IPs, operator-status.error
                        |  status.eni.enis            |  eni (operator writes)
                        +--------------+--------------+
                 watch/update          |          watch/update
        +------------------------+     |     +--------------------------+
        |  cilium-agent (node)   |<----+---->|  cilium-operator         |
        |  local pod-IP allocator|           |  node CIDRs, EC2/Azure   |
        |  CNI /ipam REST        |           |  API calls, pool alloc   |
        +------------------------+           +--------------------------+
```

Agent は現在 node が所有する範囲から個々の Pod IP を割り当てます。node が何を所有するかは mode に応じて operator、Kubernetes、または外部 system が決定します。`cluster-pool`、`multi-pool`、`eni` mode では agent 自身が `CiliumNode` を作成します（agent option `auto-create-cilium-node-resource`、デフォルト true）。`ipam.cilium.io/ignore: "true"` が annotation された `CiliumNode` は operator が無視します。別の仕組みで管理される node 用の回避策です。

### Mode 別 Agent allocator の接続先（1.20.2）

| `ipam.mode` | Node capacity の提供元 | Agent 側 allocator |
|---|---|---|
| `kubernetes` | `Node.spec.podCIDRs`（または annotation） | node CIDR を使う host-scope allocator |
| `cluster-pool`（デフォルト） | operator 経由の `CiliumNode.spec.ipam.podCIDRs` | node CIDR を使う host-scope allocator |
| `multi-pool` | operator 経由の `spec.ipam.pools.allocated` | multi-pool manager |
| `eni` | operator（EC2 API）。`status.eni.enis` を `spec.ipam.pools.allocated` に変換 | **ENI multi-pool allocator（1.20で追加）** |
| `crd`、`azure`、`alibabacloud` | `CiliumNode.spec.ipam.pool` | CRD allocator |
| `delegated-plugin` | 別の CNI IPAM plugin | no-op allocator |

Helm との関係：`eni.enabled=true` では `ipam.mode` の値にかかわらず `ipam: eni` を強制します。`eni.enabled` なしで `ipam.mode=eni` を使うと chart validation が失敗します。`gke` value はありません。self-managed GKE では `kubernetes` を使います。

### Node 内で Cilium が使う address

各 node range から Cilium 自身が address を取得します。`cilium_host` router IP、health endpoint IP、Ingress 有効時の ingress IP です。`cilium-dbg status --all-addresses` では `(router)`、`(health)`、`(ingress)` と表示されます。host-scope allocator は node CIDR の先頭（network）と末尾（broadcast）の address も除外します。容量計算（Sizing math を参照）からこれらを差し引いてください。

## Pod IP のライフサイクル

`delegated-plugin` 以外の全 mode で、kubelet から稼働 endpoint まで次の経路を通ります。

```
kubelet -> CRI -> cilium-cni ADD
                     |
                     | 1. remove stale host-side interface name, if any
                     | 2. POST /ipam   (unix socket to cilium-agent)
                     |       owner = <namespace>/<pod>, expiration = true
                     v
                 cilium-agent: IpamPostIpamHandler
                     | 3. empty pool?  -> pick pool (annotations/selectors, multi-pool)
                     | 4. AllocateNextWithExpiration
                     |       -> response: IPv4/IPv6, pool, cidrs, gateway,
                     |          master-mac, interface-number, skip-masquerade,
                     |          expiration-uuid, host-addressing (router IP)
                     |       -> start 10 minute expiration timer
                     v
                 cilium-cni: create veth (or netkit), set IPs/routes in the pod netns
                     | 5. PUT /endpoint/{id}
                     v
                 cilium-agent: build endpoint, identity, datapath
                     | 6. endpoint creation stops the expiration timer
                     v
                 pod Running

 failure at any point after step 4 -> deferred DELETE /ipam/{ip}?pool=<pool>
 CNI DEL -> endpoint delete -> agent releases the IP (metric ipam_events_total{action="release"})
```

1.20.2 の source で確認した重要な動作：

- **REST call** は agent API（`api/v1/openapi.yaml`）の `POST /ipam`、`POST /ipam/{ip}`、`DELETE /ipam/{ip}` です。CNI plugin は `IPAMAllocate("", podName, "", true)` を呼びます。最後の引数が expiration flag です。
- **Expiration timer**：expiration 付きで割り当てられた IP は、endpoint 作成で timer を停止しなければ `defaults.IPAMExpiration` の10分後に自動解放されます。CNI plugin が IP を割り当ててから endpoint を作る前に crash した場合、agent 再起動まで address が漏れる状態を防ぎます。
- **復元**：agent 再起動時、稼働中 endpoint が使う IP を再確保します（`cilium-dbg status --all-addresses` に `[restored]` と表示）。`--bypass-ip-availability-upon-restore` option は ENI／Azure の upgrade 用にのみ存在します。
- **ENI 系 mode**（`eni`、`azure`、`alibabacloud`）：response には ENI MAC、gateway、CIDR も含まれます。plugin は MAC から parent interface index を設定します（ENI のみ）。agent は host 上に endpoint ごとの routing rule を作成します。このためこれらの mode では endpoint route が強制されます。
- **`delegated-plugin`**：CNI plugin が設定された IPAM binary（例：AKS の Azure `azure-ipam`）に対して `DelegateAdd` を実行し、endpoint に `ExternalIpam` を設定します。agent はこの IP を解放しません。DEL 時に plugin が `DelegateDel` を呼びます。ここで Cilium は Pod IP を計上しません。

確認方法：

```bash
# All addresses the agent knows, with owners (ns/pod); multi-pool shows pool/ip
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status --all-addresses

# Allocation summary line, for example "IPAM: IPv4: N/M allocated from <cidr>"
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -i ipam
```

CNI error `unable to allocate IP via local cilium agent` が表示され Pod が `ContainerCreating` で停止する場合、手順2〜4で失敗しています。Troubleshooting 節で mode ごとに原因を確認できます。

## Mode 一覧と選択表

### 機能比較

1.20.2 向け upstream IPAM concepts page を基にしています。

| 機能 | Kubernetes host scope | Cluster scope（デフォルト） | Multi-pool | CRD 使用 | AWS ENI | Azure IPAM | GKE（host scope） |
|---|---|---|---|---|---|---|---|
| Tunnel routing | あり | あり | あり | なし | なし | なし | なし |
| Direct routing | あり | あり | あり | あり | あり | あり | あり |
| CIDR 設定元 | Kubernetes | Cilium | Cilium | 外部 | AWS | Azure | GCP |
| Cluster 内の複数 CIDR | なし | あり | あり | 該当なし | 該当なし | 該当なし | 該当なし |
| Node ごとの複数 CIDR | なし | なし | あり | 該当なし | 該当なし | 該当なし | 該当なし |
| CIDR／IP の動的割り当て | なし | なし | あり | あり | あり | あり | なし |

成熟度：cluster-pool、kubernetes、crd、eni は stable です。multi-pool は1.18では「Beta」banner があり、1.19以降はなくなりました（この章では1.19から stable と扱います。上流は「GA」とは表現していません）。ENI IPv6 は1.20で **beta** です。cluster-pool から multi-pool へのオンライン移行は1.20で追加されました。

### 選択表

上流資料と各 platform の制約からまとめた指針であり、上流公式の表ではありません。

| 環境 | 推奨 IPAM | 理由と注意点 |
|---|---|---|
| EKS、VPC 内で route できる Pod IP が必要（security group の宛先、ALB／NLB IP target、SNAT 不要） | `eni` と Nitro 上の prefix delegation | Operator IAM 権限、native routing、`aws-node` 削除が必要。prefix delegation を使わない場合、密度は instance ENI／IP 上限に制限。IPv6 は beta。Fargate／EKS Auto Mode node には適用不可 |
| EKS、VPC IP が不足または高密度が必要 | VXLAN の `cluster-pool`（Helm default）または `multi-pool` | Pod は node IP に SNAT される。EKS control plane は Pod IP に到達できないため、admission webhook は host network 上で動かすか Service 経由で接続 |
| EKS Hybrid Nodes（on-prem node） | VXLAN の `cluster-pool`。pool list は EKS の「remote pod networks」に合わせ、node ごとの Pod 数で mask を決定 | AWS 対応構成は IPv4、VXLAN、cluster-scope IPAM、BGP Control Plane のみ。deploy 後に pool list／mask を変更しない。`eni` は on-prem では使えない |
| On-prem、シンプルな構成 | tunnel の `cluster-pool` | Operator 管理。kube-controller-manager の node CIDR に依存しない |
| On-prem、route 可能な Pod と site／tenant ごとの複数 range | `multi-pool` + BGP `CiliumPodIPPool` 広報、site ごとの default pool は `CiliumNodeConfig` で設定 | `kubeProxyReplacement=true` と `bpf.masquerade=true` が必要。pool CIDR を重複させない |
| Control plane が node CIDR を割り当てる cluster（`--allocate-node-cidrs` を使う kubeadm、GKE） | `kubernetes` | 静的。node と address family ごとに CIDR 1つ |
| 外部 system が address を提供 | `crd` | 個別 IP のみ、direct routing のみ |
| AKS | Azure CNI Powered by Cilium（`delegated-plugin`）または BYOCNI と任意の Cilium IPAM | AKS で upstream の `azure` IPAM は使わない |
| Self-managed Azure VM | `azure` | Resource group と identity の flag。1.21 pre-release で再設計 |

### 稼働中の cluster で mode を変更する

上流の方針：文書化された移行方法がある場合を除き、稼働中 cluster の IPAM mode を変更しないこと。「最も安全なのは新しい cluster」です。文書化されたオンライン移行は**cluster-pool から multi-pool**のみです（migration subsection を参照）。それ以外（kubernetes から cluster-pool、任意 mode から ENI、overlay から ENI）は、新 cluster または blue／green node group が必要です。Pod IP range、routing、EKS では webhook 到達性も変わるためです。node group ごとに `CiliumNodeConfig` で IPAM mode を混在させる方法は上流で文書化されておらず、この章では推奨しません。

## Kubernetes host scope と cluster scope

### Kubernetes host scope（`ipam.mode=kubernetes`）

起動時に agent は、有効な address family ごとに node の PodCIDR が設定されるのを待ちます。値は `Node.spec.podCIDRs`／`spec.podCIDR`、または `network.cilium.io/ipv4-pod-cidr`、`network.cilium.io/ipv6-pod-cidr` annotation（加えて `ipv4/6-cilium-host`、`ipv4/6-health-ip`、`ipv4/6-Ingress-ip`）から取得します。`kube-controller-manager` は `--allocate-node-cidrs`（および `--cluster-cidr`、`--node-cidr-mask-size`）を指定して起動する必要があります。

```yaml
ipam:
  mode: kubernetes
k8s:
  requireIPv4PodCIDR: true     # only effective with ipam.mode=kubernetes
  requireIPv6PodCIDR: false
```

この mode で IPv4 が有効なら agent は `k8s-require-ipv4-pod-cidr` を自動で有効にするため、明示指定は主に説明用です。制約：node／family ごとに CIDR は1つで、node 登録時に固定。動的拡張はできません。self-managed GKE ではこの mode と cluster CIDR に設定した `ipv4NativeRoutingCIDR` を使います。

### Cluster scope／cluster-pool（デフォルト）

Operator が node prefix の割り当てを管理します。各 node に CIDR を割り当て、`CiliumNode.spec.ipam.podCIDRs` に書き込みます。有効な各 family の field が埋まるまで agent は起動時に待機し、その後、同じ host-scope allocator で CIDR を使います。Operator は再起動後も既存割り当てを再利用します。競合すると `node has CIDRs allocated (...) that conflict with requested CIDRs` が出ます。

Helm 値（1.20.2 のデフォルト）：

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]   # default
    clusterPoolIPv4MaskSize: 24                  # default
    clusterPoolIPv6PodCIDRList: ["fd00::/104"]   # default
    clusterPoolIPv6MaskSize: 120                 # Helm default (operator flag default is 112)
```

生成される ConfigMap key は `cluster-pool-ipv4-cidr`（空白区切り list）、`cluster-pool-ipv4-mask-size`、`cluster-pool-ipv6-cidr`、`cluster-pool-ipv6-mask-size` です。IPv4 有効時に list が空（「cluster-pool-ipv4-cidr must be provided when using ClusterPool」）、または無効 family 向けに list が指定されている場合、operator は起動を拒否します。

### Sizing 計算

Node CIDR allocator は `pkg/ipam/cidrset` です。pool CIDR の prefix length を P、node mask を M とします。

```
nodes per pool CIDR      = 2^(M - P)
addresses per node       = 2^(32 - M)          (IPv4)     2^(128 - M) (IPv6)
usable Pod IPs per node  = addresses - 2 (network, broadcast) - up to 3 (router, health, ingress)
```

Source にある制約：IPv6 では allocator が圧縮されていない bitmap を保持するため、`M - P` は16を超えてはいけません（`clusterSubnetMaxDiff = 16`、error `ErrCIDRSetSubNetTooBig`）。IPv4 は `M <= 32` のみ必要です。上流の推奨では node mask の最小は `/30`、`/29` またはそれより大きい block を推奨しています。

| Pool CIDR | Node mask | Node 数 | Node ごとの address 数 | 備考 |
|---|---|---:|---:|---|
| `10.0.0.0/8`（デフォルト） | `/24` | 65,536 | 256 | `2^(24-8)`。使用可能数は約251 |
| `10.244.0.0/16` | `/24` | 256 | 256 | 小規模 cluster で一般的 |
| `10.244.0.0/16` | `/26` | 1,024 | 64 | `2^(26-16)`。使用可能数は約59 |
| `10.244.0.0/16` | `/28` | 4,096 | 16 | 検証環境向け。使用可能数は約11 |
| `fd00::/104`（デフォルト） | `/120` | 65,536 | 256 | IPv6 default。差分はちょうど16 |
| `fd00:10:244::/96` | `/112` | 65,536 | 65,536 | 許容差分の最大16 |

最初の4行は上記の式で算出しました。「使用可能数」では予約 address 2つと Cilium が使う3 address を差し引いており、上限の目安です。node ごとの Pod 密度は kubelet の `maxPods` にも依存します。rolling update 中は旧 Pod と新 Pod が重なるため、`maxPods` に余裕を足して mask を選んでください。

変更ルール（上流。validation ではなく動作によって強制）：

- `clusterPoolIPv4PodCIDRList` の既存項目は編集／削除せず、追加して拡張します。
- 稼働中 cluster の `clusterPoolIPv4MaskSize` は変更できません。
- Allocator の error（`allocator full`）は `CiliumNode.status.ipam.operator-status.error` に表示されます。

```bash
kubectl get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ipam.podCIDRs}{"\t"}{.status.ipam.operator-status}{"\n"}{end}'
```

範囲重複の危険：デフォルト `10.0.0.0/8` は社内 network や VPC の多くと重複します。node network と重なると node 接続を失います。常に list を明示してください。

**`nativeRoutingCIDRFromClusterPool`**（Helm、デフォルト false。1.20で追加：1.18.14／1.19.8 の `values.yaml` にはなく、1.20.2／1.21 には存在）は pool から native-routing CIDR を導出します。cluster-pool であり、有効な各 family の CIDR が1つだけの場合に限り有効です。それ以外は template が失敗します。

### Dual-stack

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList: ["fd00:10:244::/96"]
    clusterPoolIPv6MaskSize: 112       # 112 - 96 = 16, the maximum allowed
ipv4: { enabled: true }
ipv6: { enabled: true }
```

`ipv6.enabled` を設定しても IPv6 Service CIDR や underlay IPv6 接続は作成されません。mode ごとの違い：host scope には `podCIDRs` の両 entry と `k8s.requireIPv6PodCIDR` が必要です。multi-pool は `ipv4`、`ipv6` または両方を持てます。family 固有の `ipam.cilium.io/ipv4-pool`／`ipam.cilium.io/ipv6-pool` annotation が使えます。ENI IPv6 は beta（Release、use-primary-address、IPv6 を参照）。LB IPAM は Service の `ipFamilyPolicy` に従います（以下の LB IPAM）。AWS 対応の EKS Hybrid Nodes 構成は IPv4 のみです。

## Multi-pool IPAM

### 概念

Multi-pool では cluster 全体で「CIDR list 1つ」を使う代わりに、それぞれ名前を持つ `CiliumPodIPPool` **pool** を使います。node は複数 pool の block を同時に持て、agent の要求に応じて割り当てられます。tenant ごとに異なる range を設ける、BGP で pool ごとに広報する route 可能な Pod 群を分ける、site 単位の range を使う、source IP を保持する pool を設ける、といった用途に使います。

### 前提条件とインストール

上流 tutorial では `kubeProxyReplacement=true` と `bpf.masquerade=true` が必要です。既知の制限：iptables ベースの masquerading では `egressMasqueradeInterfaces` が必要なため（上流 issue 22273）、サポートされる方式は eBPF masquerade です。pool CIDR を互いに重複させてはいけません（IP cache では prefix が1つの identity に対応するため）。

```yaml
ipam:
  mode: multi-pool
  multiPoolPreAllocation: "default=8,mars=4"
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4: { cidrs: ["10.10.0.0/16"], maskSize: 27 }
      mars:
        ipv4: { cidrs: ["10.20.0.0/16"], maskSize: 27 }
kubeProxyReplacement: true
bpf: { masquerade: true }
```

`autoCreateCiliumPodIPPools` は存在しない pool を作成するだけで、既存 pool は更新しません。対応する operator flag は `--auto-create-cilium-pod-ip-pools <pool>=ipv4-cidrs:...;ipv4-mask-size:...[;allow-first-ip:...][;allow-last-ip:...]` です。この構文では `podSelector`、`namespaceSelector`、または（1.21の）`pool[].reservedRanges` を指定できません。これらを使う pool は custom resource として作成してください。

### CiliumPodIPPool

```yaml
apiVersion: cilium.io/v2alpha1      # 1.20.x; use cilium.io/v2 from 1.21 [1.21 pre-release]
kind: CiliumPodIPPool
metadata:
  name: mars
spec:
  # allowFirstIP / allowLastIP are fields of spec (not of spec.ipv4); default false,
  # ignored for /31 /32 /127 /128
  ipv4:
    cidrs: ["10.20.0.0/16"]
    maskSize: 27
  podSelector:
    matchLabels:
      io.kubernetes.pod.namespace: tenant-mars   # synthetic label
  namespaceSelector:
    matchLabels:
      tenant: mars
```

Cluster-scoped で short name は `cpip` です。`maskSize`、`allowFirstIP`、`allowLastIP` は immutable（CEL `self == oldSelf`）です。`allowFirstIP`／`allowLastIP` を指定しなければ、**node ごとに割り当てられた各 block** の先頭と末尾の address を予約します。ある family の block を持たない pool は、その family では無視されます。

**API version の注意。** 1.20.2 は `cilium.io/v2alpha1` を提供します。**[1.21 pre-release]** では `cilium.io/v2` が storage version になり、`v2alpha1` は非推奨です。v2 は `cidrs` を最大32項目に制限し、`spec.ipv4.pool[]`／`spec.ipv6.pool[]` を追加します（Updating pools safely を参照）。1.21 に移行する場合は manifest と tooling を v2 に更新してください。

### Pool 選択

Pod 作成時に1回だけ評価します（稼働中 Pod の annotation を変更しても反映されません）。source（`pkg/ipam/metadata/manager.go`）とドキュメントに基づく優先順位：

1. **Pod annotation**：family ごとの `ipam.cilium.io/ipv4-pool`／`ipam.cilium.io/ipv6-pool` は `ipam.cilium.io/ip-pool` より優先。
2. **Namespace annotation**：同じ key を Pod の namespace から取得。
3. **`CiliumPodIPPool` selector**：`podSelector` と `namespaceSelector` の両方が設定されていれば、双方に一致する必要があります。family ごとに一致する pool はちょうど1つでなければなりません。それ以外は error と event が発生し、割り当ては**失敗**します。
4. **Default pool**：`ipam-default-ip-pool`（デフォルト `default`）。ただし Pod または namespace に `ipam.cilium.io/require-pool-match: "true"` があれば default を使わず、割り当てを停止します。

正しい annotation key は `ipam.cilium.io/ip-pool`（`pkg/annotation/k8s.go`）です。一部の upstream tutorial にある `ipam.cilium.io/ipam-pool` は何も起こしません。

```bash
kubectl annotate namespace tenant-mars ipam.cilium.io/ip-pool=mars
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
  annotations:
    ipam.cilium.io/ip-pool: mars
spec:
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
```

### Agent による capacity 要求

Agent は `CiliumNode.spec.ipam.pools.requested[] {pool, needed{ipv4-addrs, ipv6-addrs}}` に需要を書き込みます。Operator は node の空き address が `needed` を満たすまで pool の `maskSize` 単位で block を切り出し、`spec.ipam.pools.allocated[] {pool, cidrs[], allowFirstIP, allowLastIP}` に追加します。需要を超え、空き切った block は agent が削除します。Error は `status.ipam.operator-status.error` に記録されます。

文書化されている式は `neededIPs = roundUp(inUse + pending + preAlloc, preAlloc)` です。code 内の `pkg/ipam/multipool_manager.go` にある `neededIPCeil` は、次の次の倍数に切り上げます。`preAlloc = P` の場合、需要0なら `P`、1から`P`なら`2P`、`P+1`なら`3P` を要求します。少なくとも1回分の pre-allocation buffer を持つ動作です。Agent flag は `--ipam-multi-pool-pre-allocation`（Helm `ipam.multiPoolPreAllocation`）。空の場合 `default=8`、その他の pool はデフォルト0です。件数は有効な family ごとに適用されます。

Block は `maskSize` 単位で割り当てるため、block の大きさが `preAlloc` の数倍になるようにします（例：`/27` は32 address で `preAlloc=8`）。小さすぎる block では node が小さな block を何度も取得／解放することになります。

### Node ごとの default pool、masquerade、routing

`CiliumNodeConfig`（`cilium.io/v2`、namespace `kube-system`）で**node 単位の default pool**を設定できます。変更が反映されるのは agent Pod を再起動した後です。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  name: ip-pool-dc1
  namespace: kube-system
spec:
  defaults:
    ipam-default-ip-pool: dc1-pool
  nodeSelector:
    matchLabels:
      topology.kubernetes.io/zone: dc1
```

Cluster-pool migration 用の名前を持つ pool には、この上書きを使わないでください（cluster-pool から multi-pool への移行 subsection を参照）。

**Masquerade。** Agent option `--only-masquerade-default-pool`（eBPF masquerade が必要）または `CiliumPodIPPool` 上の per-pool annotation `ipam.cilium.io/skip-masquerade="true"` により、default 以外の pool では Pod source IP を保持できます。影響するのは新規 Pod です。Agent option 用の専用 Helm key はありません。`extraConfig.only-masquerade-default-pool: "true"` を使います（この正確な設定 path は今回のレビューでは実行していません）。

**Routing。** BGP Control Plane の `CiliumPodIPPool` advertisement（[Part 11](11-bgp-lb-egress-edge.md) 参照）、または同じ L2 segment 上の `autoDirectNodeRoutes` で pool CIDR を到達可能にできます。

### Pool の安全な更新と `reservedRanges`（[1.21 pre-release]）

規則：新しい pool と追加 CIDR は稼働中でも追加できます。node が使用中の CIDR は削除できません。使用中の pool も削除できません（operator は `CIDR from pool still in use by node` を log に出します）。1.20で CIDR を入れ替えるには、pool を編集して operator を再起動し、node group ごとに cordon、drain、`CiliumNode` object 削除、agent 再起動、uncordon を順番に行います。

**[1.21 pre-release]** `cilium.io/v2` に CIDR ごとの `reservedRanges` 設定が追加され、割り当てを orphan にせず CIDR を廃止できます。

```yaml
apiVersion: cilium.io/v2
kind: CiliumPodIPPool
metadata:
  name: default
spec:
  ipv4:
    cidrs: ["10.10.0.0/16", "10.20.0.0/16"]
    maskSize: 24
    pool:
    - cidr: 10.10.0.0/16
      reservedRanges:
      - start: 10.10.0.0
        end: 10.10.255.255
```

`10.10.0.0/16` から既存 node に割り当てた block は使い続けられ、新しい block は `10.20.0.0/16` からだけ割り当てます。すべての node group の移行後に、`cidrs` から旧 CIDR と対応する `pool` entry を削除します。`pool[].cidr` は必ず `cidrs` のいずれかである必要があり、CEL で検証されます。

### Cluster-pool から multi-pool へのオンライン移行（1.20以降）

1.19以前にはありません。Operator option は `enable-cluster-pool-to-multi-pool-migration`（デフォルト false）、`multi-pool-migration-workers`（デフォルト16）、`ipam-default-ip-pool` です。

前提条件：移行は一方向であり rollback 不可。既存 Pod はすべて**default pool**を使う必要があります。Operator を再起動する前に default pool が存在し（custom resource または `autoCreateCiliumPodIPPools`）、割り当て済み node CIDR をすべて包含し、同じ mask size でなければなりません。node ごとに default pool 名を上書きしないでください。

```bash
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set ipam.mode=multi-pool \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.cidrs='{10.0.0.0/8}' \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.maskSize=24 \
  --set-string extraConfig.enable-cluster-pool-to-multi-pool-migration=true \
  --set operator.rollOutPods=true \
  --set rollOutCiliumPods=false
```

続いて、各 `CiliumNode` の `spec.ipam.pools.allocated` に既存 PodCIDR が表示されるのを待ちます。BGP Control Plane が PodCIDR を広報している場合は、**agent 再起動の前に** default pool を選ぶ `CiliumBGPAdvertisement` を `advertisementType: PodCIDR` から `CiliumPodIPPool` に変更します（agent がまだ cluster-pool mode の間は移行済み allocation の広報が止まるため、一時的に route withdrawal が発生します）。


その後、agent を一斉または段階的に再起動します。rollout 中に cluster-pool mode と multi-pool mode の agent が混在していても、接続は維持されます。すべての agent が再起動するまでは、default 以外の pool を使う Pod を scheduling しないでください。

### 制限と BGP との関係

Pool 間で CIDR を重複させないでください。`egressMasqueradeInterfaces` なしの iptables masquerade は非対応です。分離した pool には `ip-masq-agent` を検討してください。使用中 range の pool CIDR を変更するには上記の drain 手順が必要です。

## CRD 使用 IPAM（`ipam.mode=crd`）

Agent は node 名と同じ名前の `CiliumNode` を監視します。`spec.ipam.pool` は利用可能な**個別 IP**を表す `ip -> {owner, resource}` の map です（CIDR は非対応）。使用中 IP は `status.ipam.used` で報告され、status 更新は最大15秒に1回です（Helm `ipam.ciliumNodeUpdateRate`）。IPv6 は `spec.ipam.ipv6-pool` と `status.ipam.ipv6-used` を使います。direct routing のみです。

起動時に `Waiting for initial IP to become available in '<node>' custom resource` を log に出します。少なくとも1つ（health check 有効時は少なくとも2つ）の IP が必要です。RBAC では `ciliumnodes` と `ciliumnodes/status` への完全な access が必要です。上流本文には `available`／`inuse` とありますが、schema 上の field は `pool`／`used` です。インストール済み CRD を正としてください。

## AWS ENI IPAM

### Architecture（1.20.2）

EC2 API を呼び出すのは operator のみです。Operator は ENI inventory を `CiliumNode.status.eni.enis` に書き込みます。Agent はその inventory を `spec.ipam.pools.allocated` の CIDR に変換し、pool `default` に登録します。Secondary IP は `/32`、委任 prefix は IPv4 `/28`、IPv6 `/80` です。Agent がローカルで Pod IP を割り当て、`spec.ipam.pools.requested` で需要を報告します。1.20 ENI mode には `CiliumPodIPPool` も `ip-pool` annotation もありません。1.19／1.18では ENI が代わりに CRD allocator（`spec.ipam.pool`、`status.ipam.used`）を使っていました。1.19から1.20への rolling upgrade はサポートされます。Operator は `spec.ipam.pools.requested` の有無と `status.ipam.used` の有無で新旧 agent を判別します。

ENI mode は native routing と endpoint route を強制します（`eni.enabled=true` がすでに有効化するため、values file 内の `routingMode: native` と `endpointRoutes.enabled` は重複設定です）。ENI と tunneling の併用は拒否されます。ENI mode での `enableIPv4Masquerade` は1.18以降デフォルト false です。**[1.21 pre-release]** では `enableIPv6Masquerade` も ENI mode でデフォルト false になります。

### インストールと node の準備

VPC CNI（`aws-node`）を、存在し得ない `nodeSelector`（上流例：`io.cilium/aws-node-enabled=true`）で DaemonSet を patch して無効化し、`eni.enabled=true` でインストールします。Agent が稼働するまで workload が待つよう、node group 作成時に startup taint `node.cilium.io/agent-not-ready=true:NoExecute` を設定してください。`eth0` 以外の `eth*` interface を NetworkManager／systemd-networkd に管理させないでください。そうしないと OS が secondary IP を除去することがあります（Amazon Linux 2023 で関係します）。VPC CNI を置き換える場合は iptables chain `AWS-SNAT-CHAIN-*` と `AWS-CONNMARK-CHAIN-*` を flush します。

Operator に必要な IAM 権限（上流記載。可能なら resource tag で scope を制限）：`ec2:DeleteNetworkInterface`、`DescribeInstanceTypes`、`DescribeNetworkInterfaces`、`DescribeSubnets`、`DescribeVpcs`、`DescribeRouteTables`（1.18以降必須）、`DescribeSecurityGroups`、`CreateNetworkInterface`、`AttachNetworkInterface`、`ModifyNetworkInterfaceAttribute`、`AssignPrivateIpAddresses`、`CreateTags`。加えて `DescribeTags`（ENI garbage collection、デフォルト有効）、`UnassignPrivateIpAddresses`（release）、`AssignIpv6Addresses`（IPv6）、`DescribeInstances`（`--instance-tags-filter` 使用時）。**[1.21 pre-release]** では任意の `GetSecurityGroupsForVpc`（利用不可時は警告1回で fallback）と `DescribeManagedPrefixLists`／`GetManagedPrefixListEntries` があります。Prefix 操作に必要な IAM action として上流が文書化するのは assign／unassign の private-IP action のみです。最小権限 policy を作成する前に AWS documentation で正確な IAM action を確認してください。Credential は `eni.iamRole`（IRSA）または `cilium-aws` secret から渡します。

### Helm values

```yaml
eni:
  enabled: true
  iamRole: arn:aws:iam::<account-id>:role/cilium-operator
  awsEnablePrefixDelegation: true
  awsReleaseExcessIPs: true
  eniTags:
    team: platform
  gcInterval: 5m                        # "0s" disables ENI garbage collection
  nodeSpec:                             # per-node settings, since 1.19
    firstInterfaceIndex: 1              # keep eth0 for node traffic
    subnetTags: ["pod-subnet=true"]
    securityGroupTags: ["cilium-pod-sg=true"]
    excludeInterfaceTags: ["no-cilium=true"]
    deleteOnTermination: true
ipam:
  nodeSpec:
    ipamMinAllocate: 16
    ipamPreAllocate: 8
  operator:
    externalAPILimitQPS: 8
    externalAPILimitBurstSize: 40
```

Tag list の entry は ConfigMap 内で `key=value` を comma 区切りにして出力されます（例：`eni-subnet-tags`）。混同してはいけない filter が2種類あります。Operator level の `eni.subnetIDsFilter`、`eni.subnetTagsFilter`、`eni.instanceTagsFilter` は、operator が管理する instance／subnet を限定します。deploy 時に instance が一致する subnet の ENI をすでに持つことを前提とします。Cilium が**新規作成する** ENI だけを誘導する場合は、node ごとの `eni.nodeSpec` value を使います（または custom CNI config の `eni` section。Helm と同じ field があれば CNI config が優先）。Operator API limiter のデフォルトは4 QPS、burst 20です。

把握しておきたい operator flag（cmdref `cilium-operator-aws`）：`--aws-enable-prefix-delegation`、`--aws-release-excess-ips`、`--excess-ip-release-delay`（デフォルト180秒）、`--eni-gc-interval`（5分）、`--eni-tags`、`--parallel-alloc-workers`（50）、`--limit-ipam-api-qps`、`--limit-ipam-api-burst`、`--aws-max-results-per-call`。

### Allocation algorithm

Node 単位の設定（`CiliumNode.spec.ipam`）：`min-allocate`、`pre-allocate`（0 の場合は8として扱う）、`max-allocate`、`max-above-watermark`（agent flag と Helm key はない。`CiliumNode` または CNI config の `ipam` section で設定）、`static-ip-tags`。式は `operator/pkg/ipam/nodemanager/node.go` に基づきます。

```
deficit (needed) = max( preAllocate + used - available ,  minAllocate - available )
                   clamped to maxAllocate if set;  floor 0
excess  (only with --aws-release-excess-ips)
                 = max( available - used - preAllocate - maxAboveWatermark , 0 )
                   (while used is small, keep available >= minAllocate + maxAboveWatermark)
per-cycle allocation on the chosen ENI
                 = min( AvailableOnSubnet,
                        min( AvailableOnENI, needed + maxAboveWatermark + surgeAllocate ) )
   where surgeAllocate = pendingPods - needed
```

計算例：`preAllocate=8`、`minAllocate=16`、空き10、使用中4の node では、deficit = max(8 + 4 - 10, 16 - 10) = 6 です。そのため operator は少なくとも6つ追加で割り当てます。小さな instance では pre-allocate が `min(8, (adapters - firstIndex) x (ipsPerENI - 1))` に自動調整されます。デフォルトの `max-allocate` は instance 上限の `(adapters - firstInterfaceIndex) x (ipv4PerENI - 1)` で、prefix delegation 有効時は16倍です。`usePrimaryAddress` では ENI ごとに address が1つ増えます。

Scheduling：すべての `CiliumNode` 更新時に deficit を評価し、さらに1分ごとに全体を走査します。work queue は demand ごとに処理しますが、最大1秒に1回、deficit が最大のものから実行します。Release より allocation を先に行います。

IP の割り当て元：operator は空き capacity と subnet address がある、index が `first-interface-index` 以上の attach 済み ENI を走査します。利用可能な ENI がなければ作成します。Subnet 候補は同じ VPC／AZ 内に限定され、`subnet-ids`（優先）または `subnet-tags`（すべて一致）で絞ります。空き address が最も多い subnet を選びます。どちらもなければ node の primary ENI subnet、同じ route table の subnet、VPC／AZ 内で最大の subnet の順に選びます。Security group は `spec.eni.security-groups`、それがなければ `security-group-tags`、さらにそれもなければ eth0 の group を継承します。ENI は `Cilium-CNI (<instance-id>)` と命名され、cluster tag と `--eni-tags` で tag 付けされます。API call：`CreateNetworkInterface`、`AttachNetworkInterface`、`ModifyNetworkInterfaceAttribute`（delete-on-termination、デフォルト true）、`AssignPrivateIpAddresses`。

### Prefix delegation

`eni.awsEnablePrefixDelegation=true`（node 単位で無効にする場合は `eni.nodeSpec.disablePrefixDelegation`）にすると、単一 secondary IP の代わりに `/28` prefix（16 address）を割り当てます。ENI ごとの capacity は16倍になります。Source にある制約：

- **Nitro または bare-metal** instance type のみ有効。
- Mixed mode は不可。いずれかの ENI に secondary `/32` IP がすでにある node では使いません（primary ENI IP はこの検査から除外）。
- `AssignENIPrefixes` を使い、個数は `ceil(needed / 16)`。Subnet が `InsufficientPrefixesInSubnet` を返すと、この node には以後 prefix を割り当てないと operator が log に記録し、`/32` secondary IP に fallback します。
- Subnet に空き `/28` block が連続して必要です。fragmented subnet は address が残っていても prefix が先に枯渇する場合があります（AWS 側の動作。AWS prefix-delegation 文書を参照）。

### Release、use-primary-address、IPv6

**Release**（IPv4 のみ。`--aws-release-excess-ips=true` が必要）：agent は完全に空いた CIDR を `spec.ipam.pools.allocated` から削除します。Operator は `--excess-ip-release-delay`（デフォルト180秒）待ってから `UnassignPrivateIpAddresses`（`/32`）または prefix unassign（`/28`）を呼び出します。Release では ENI を detach／delete **しません**。古い ENI は ENI GC が削除します（tag `io.cilium/cilium-managed=true` と `io.cilium/cluster-name=<name>`）。1.19形式の `status.ipam.release-ips` handshake は古い CRD allocator agent にのみ適用されます。

**`usePrimaryAddress`**：ENI の primary private IP を Pod に割り当てられるようにします（ENI ごとに +1）。**[1.21 pre-release]** Operator flag `--aws-use-primary-address` は**削除**されます。代わりに `eni.nodeSpec.usePrimaryAddress=true` を設定します（agent flag `--eni-use-primary-address`。`CiliumNode.spec.eni.use-primary-address` に保存）。chart が agent 側のみ接続しているため Helm user には影響しません。

**IPv6（1.20では beta。agent が beta warning を記録）**：`ipam.mode=eni`、`eni.enabled=true`、`ipv6.enabled=true` にします。各 node に委任 `/80` prefix を正確に1つ割り当てます。ENI 作成時または `AssignIpv6Addresses` で設定し、解放はしません。watermark はありません。Subnet は dual-stack が必須です。各 ENI に primary IPv4 address が必要なため、IPv6-only subnet は非対応です。上流の EKS requirements page は ENI を IPv4 のみと記載したままですが、ENI page と実行時 beta warning の方が新しい情報です。

### ENI に関する注意事項

Pod 密度は `(ENIs - firstIndex) x (IPs per ENI - 1)` で上限が決まり（prefix の場合は ×16）、Pod は node ENI の security group を共有します。Node group ごとに `spec.eni.security-groups` を設定すると分離できます。Cluster ID 128〜255 の Cluster Mesh と ENI を併用すると、既知の policy-drop issue が発生します（[Part 13](13-clustermesh-install-upgrade.md)）。1.20で削除済み（1.19には存在）：`CiliumNode.spec.eni.min-allocate`、`pre-allocate`、`max-above-watermark`、`instance-id`。同じ値は `spec.ipam` 以下にあります。VPC CNI の上に chaining する設計は別方式であり、この章では扱いません。

## Azure、AKS、Alibaba Cloud

**AKS。** Azure CNI Powered by Cilium は managed 構成です。CNI configuration を `"ipam": {"type": "azure-ipam"}`、`local-router-ipv4: 169.254.23.0` とする `ipam: delegated-plugin` を使います。Cilium は Pod IP を割り当てません。BYOCNI cluster では任意の Cilium IPAM を使えます。Helm `azure.enabled` は BYOCNI と非互換です。`aksbyocni.enabled` を使ってください。

**Self-managed Azure（upstream `--ipam=azure`）。** Operator flag は `--azure-subscription-id`、`--azure-resource-group`（VMSS では VMSS の resource group。異なる group を指定すると address が取得されない）、`--azure-user-assigned-identity-id`（resource ID ではなく client ID）、`--azure-use-primary-address` です。認証には DefaultAzureCredential chain を使います。Node 単位の設定は `azure.nodeSpec.azureInterfaceName`。1.20で operator は `status.azure.interfaces[]` に新しい `subnet{id,cidr}` object を公開します（flat `cidr` と `addresses[].subnet` は非推奨）。**[1.21 pre-release]** Azure は ENI と共通の cloud multi-pool framework に移行します。`succeeded` になったすべての address は default pool の host prefix となり、余分な IP は解放されません。`--ipv4-native-routing-cidr` が未設定なら、agent は有効な IPv4 subnet CIDR を最大5分待って、それを native-routing CIDR として使います。

**Alibaba Cloud。** `alibabacloud.enabled` と node ごとの `alibabacloud.nodeSpec.{vSwitches,vSwitchTags,securityGroups,securityGroupTags}` を使う `ipam.mode=alibabacloud`。CRD allocator です。Installation guide は Terway／Flannel を置き換え、`cilium-alibabacloud` secret を使います。ここではそれ以上扱いません。Alibaba の制限と IPv6 の動作は調べていません。

## Pod IP 以外：LB IPAM、Node IPAM、CiliumCIDRGroup

### LB IPAM と `CiliumLoadBalancerIPPool`

LB IPAM は `type: LoadBalancer` Service 向け address を割り当てます。Operator（`operator/pkg/lbipam`）内で実行され、常に compile 済みです（Helm `enableLBIPAM`、デフォルト true）。最初の pool が作成されるまで休止します。LB IPAM は address を**割り当てるだけ**です。到達可能にするには BGP Control Plane（`loadBalancerClass: io.cilium/bgp-control-plane`）または L2 Announcements（`io.cilium/l2-announcer`）も必要で、[Part 11](11-bgp-lb-egress-edge.md) で扱います。

> **Security scope。** LB IPAM pool には private range を使ってください。BGP／routing 連携なしでは VPC 内から LB IPAM VIP に到達できないため、EKS では internal AWS load balancer を使います。外部公開経路は常に CloudFront から internal ALB／NLB です。LB IPAM は BGP または L2 広報を行う on-prem／hybrid site に適しています。上流例には `20.0.0.0/8` のような public に見える range が使われていますが、この章では RFC 1918 range を使います。

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: blue-pool
spec:
  blocks:
  - cidr: 10.0.10.0/24
  - start: 10.0.20.100        # start and stop form ONE block; keep them in one list item
    stop: 10.0.20.200
  serviceSelector:
    matchLabels:
      color: blue
  allowFirstLastIPs: "No"     # default "Yes"; "No" reserves network/broadcast; cidr blocks only
  # disabled: true            # stop new allocations, keep existing ones
```

事実：API `cilium.io/v2`（`v2alpha1` は1.19.8で初めて非推奨と明記）、cluster-scope。Short name は `ippools`、`ippool`、`lbippool`、`lbippools`。表示列は Disabled、Conflicting、IPs Available。`serviceSelector` は label のほか、合成 label `io.kubernetes.service.namespace` と `io.kubernetes.service.name` に対応します。pool が重なる場合、後から作成した方に Conflicting condition（`cilium.io/PoolConflict`）が付いて何も割り当てません。Pool condition には `cilium.io/IPsTotal`、`IPsAvailable`、`IPsUsed` もあります。Pool を編集すると既存 Service IP を再割り当てする場合があるため（上流 issue 40358）、新しい pool の追加か `disabled: true` を推奨します。

Service の扱い：`loadBalancerClass` のない `LoadBalancer` Service は、Helm `defaultLBServiceIPAM` が `none` でない限り LB IPAM が処理します（値：`lbipam`、`nodeipam`、`none`）。不明な class の Service は無視します。Service condition `cilium.io/IPAMRequestSatisfied` の reason は `satisfied` または `no_pool` です。Address family はデフォルトで single-stack（両方有効なら IPv4）。`PreferDualStack` は両方を試し、`RequireDualStack` は family が1つでも無効なら未充足のままです。

特定 address を要求：annotation `lbipam.cilium.io/ips: "10.0.10.100,10.0.10.101"` を使います（legacy `.spec.loadBalancerIP` は非推奨）。Pool の `serviceSelector` も引き続き一致する必要があります。また `allowFirstLastIPs: "No"` の pool では先頭／末尾 address を要求しないでください。

Service 間で IP を共有：

```yaml
metadata:
  annotations:
    lbipam.cilium.io/sharing-key: "web-vip"
    lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"   # or "*"
```

1.20では同じ sharing key を持つ2つの Service が、port／protocol の conflict がなければ1つの IP を共有します。競合する場合は同じ key の address set から別々の IP を割り当てます。**[1.21 pre-release]** では互換性検査が厳格になり、同じ `externalTrafficPolicy` を要求します。`Local` の場合は同じ Pod を選択する必要があります。新 annotation `lbipam.cilium.io/sharing-permit-different-pods: "true"` でこの安全確認を無効化できますが、Cilium BGP／L2 Announcements と併用するのは危険です（L4 を認識しないため、異なる node が同じ IP への応答を返す可能性があります）。

Metric（document 上の prefix は `cilium_`。Controller は operator 内で動作し、registry が namespace を上書きする場合、runtime prefix は `cilium_operator_lbipam_*` かもしれません。実行時検証はしていません。実際の名前は scrape で確認してください）：`cilium_lbipam_conflicting_pools`、`cilium_lbipam_ips_available{pool}`、`cilium_lbipam_ips_used{pool}`、`cilium_lbipam_services_matching`、`cilium_lbipam_services_unsatisfied`。

Datapath に関する補足（1.19）：LB IPAM または ClusterIP address 宛ての north-south TCP／UDP は、登録済み Service と一致しない port なら drop されます。

### Node IPAM

`nodeIPAM.enabled=true`（デフォルト false。`enable-node-ipam` を設定）にすると、`loadBalancerClass: io.cilium/node`（または `defaultLBServiceIPAM: nodeipam`）の Service の load balancer ingress に node address を載せます。既存 install で有効化した後は operator を再起動してください（`kubectl -n kube-system rollout restart deployment/cilium-operator`）。Operator は各 node の ExternalIP があればそれを、なければ InternalIP を `status.loadBalancer.ingress` に設定し、`ipFamilies` に従います。`externalTrafficPolicy: Cluster` はすべての node を使います。`Local` は選択された Pod がある node を使います（EndpointSlice が必要。Cilium Ingress／Gateway の dummy endpoint とは併用不可）。`node.kubernetes.io/exclude-from-external-load-balancers` label のある node と `ToBeDeletedByClusterAutoscaler` taint のある node は除外されます。Service annotation `io.cilium.nodeipam/match-node-labels` で label による絞り込みもできます。

Node IPAM は node address を Service address として公開します。AWS で public exposure に使わず、node IP が private な環境に限定してください。

### CiliumCIDRGroup

`CiliumCIDRGroup` は名前付き CIDR list（`spec.externalCIDRs`）です。Policy では CIDR を直接書く代わりに `cidrGroupRef` または `cidrGroupSelector` で参照します。CIDR 数が多い場合でも group には1つの security identity だけが付き、規模を拡張しやすくなります。Hubble は flow に group 名を付加します。Cluster-scoped で short name は `ccg`。`cilium.io/v2` を使用してください。`v2alpha1` は非推奨ですが、上流例にはまだ残っています。

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: corp-ranges
  labels:
    tier: internal
spec:
  externalCIDRs:
  - 10.30.0.0/16
  - 192.168.100.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-corp
spec:
  endpointSelector:
    matchLabels:
      app: batch
  egress:
  - toCIDRSet:
    - cidrGroupRef: corp-ranges
```

## 運用：確認、Metric、Upgrade

```bash
# per-node view of what each node owns
kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs
kubectl get ciliumnode <node> -o yaml        # .spec.ipam, .status.ipam, .status.eni.enis
kubectl get ciliumpodippools                 # multi-pool; short name cpip
kubectl get ippools                          # LB IPAM pools
kubectl -n kube-system logs deploy/cilium-operator | grep -i ipam
```

**Agent metric：** `cilium_ipam_capacity{family,cidr}`（`cidr` label は cluster-pool／kubernetes mode では node CIDR、それ以外では空）、`cilium_ipam_events_total{action,family}`、`cilium_ip_addresses{family}`。

**Operator metric**（prefix `cilium_operator_`。`operator.prometheus.enabled` で有効化）：`ipam_available_ips{target_node}`、`ipam_used_ips`、`ipam_needed_ips`、`ipam_ip_allocation_ops{subnet_id}`、`ipam_ip_release_ops`、`ipam_interface_creation_ops`、`ipam_interface_candidates`、`ipam_empty_interface_slots`、`ipam_available_ips_per_subnet{subnet_id,availability_zone}`、`ipam_nodes{category=total|in-deficit|at-capacity}`、`ipam_resync_total`、`ipam_allocation_duration_seconds`、`ipam_release_duration_seconds`、`ipam_background_sync_duration_seconds`。上流 metric 表は古く、`interface_candidates`、`empty_interface_slots`、`available_ips_per_subnet`、`background_sync_duration_seconds` が載っていません。上記は source に基づきます。Cloud API call metric は `ipam_` 以下ではありません。subsystem は cloud 名なので、AWS では `cilium_operator_ec2_api_duration_seconds{operation,response_code}` と `cilium_operator_ec2_api_rate_limit_duration_seconds{operation}` です（Azure／Alibaba Cloud はそれぞれの subsystem）。1.20で `ipam_ips` と `ipam_available_interfaces` を削除しました。

Alert の例：`ipam_nodes{category="at-capacity"} > 0`、`ipam_nodes{category="in-deficit"}` の増加、AZ ごとの閾値を下回る `ipam_available_ips_per_subnet`、継続する `ec2_api_rate_limit_duration_seconds`、`lbipam_conflicting_pools > 0`。

**Upgrade に関する注意。** 1.19から1.20への rolling upgrade は ENI でサポートされます。**[1.21 pre-release]** Operator ClusterRole に `ciliumpodippools` の list／patch 権限が追加されます（storage-version migration）。Operator flag `--aws-use-primary-address` は削除されます（Release、use-primary-address、IPv6 を参照）。Helm ではなく operator に直接設定している場合は、upgrade 前に `eni.nodeSpec.usePrimaryAddress=true` に切り替えてください。

## 演習

> このレビューでは live cluster で演習を実行していません。上流 source と文書で確認しました（検証範囲を参照）。同じ表示形式を期待するのではなく、観察内容と期待動作を文章で照合してください。

### Lab 1: Cluster-pool のサイズ設定と枯渇（kind）

前提条件：worker 2台の kind cluster、Helm default の `cluster-pool` で導入済み Cilium、kubectl、Helm。

1. node mask を意図的に小さくして install：

   ```bash
   helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
     --set ipam.mode=cluster-pool \
     --set ipam.operator.clusterPoolIPv4PodCIDRList='{10.244.0.0/16}' \
     --set ipam.operator.clusterPoolIPv4MaskSize=28
   ```
2. `kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs` で各 node の block を確認します。各 node が `/28`（16 address）を持ちます。
3. `nodeSelector` で1つの worker に固定した Deployment を作り、replica を20まで増やします。
4. 期待する動作：最初の Pod は起動します。node の使用可能 address（16から network、broadcast、router／health／ingress address を引いた数）を使い切ると、残りの Pod は CNI allocation error で `ContainerCreating` のままになります。`cilium-dbg status` では node range が割り当て済みと表示されます。
5. Sizing math の式から上限を計算し、実際の Pod 数と比較します。

後片付け：Deployment を削除します。ロールバック：稼働中 cluster では mask は immutable です。値を編集せず cluster を再インストールしてください。

### Lab 2: Multi-pool の選択（kind）

前提条件：kind、`ipam.mode=multi-pool`、`kubeProxyReplacement=true`、`bpf.masquerade=true` の Cilium 1.20.2、および multi-pool install 値で `default` と `mars` pool を作成済み。

1. Namespace を2つ作成します。片方に `kubectl annotate namespace ns-a ipam.cilium.io/ip-pool=mars` を設定します。
2. 各 namespace に Pod を起動し、`kubectl get pods -A -o wide` を確認します。annotation がある方の Pod は `10.20.0.0/16`、もう一方は `10.10.0.0/16` から address を取得するはずです。
3. annotation のない namespace に `ipam.cilium.io/ip-pool: mars` Pod annotation 付きの Pod を起動します。Pod annotation は namespace default より優先されます。
4. 第3 namespace に、pool と一致しない `ipam.cilium.io/require-pool-match: "true"` を設定して Pod を起動します。pool-match error で起動待ちになるはずです。
5. `kubectl get ciliumnode <n> -o yaml` の `spec.ipam.pools.requested` と `allocated` を確認します。`cilium-dbg status --all-addresses` には `pool/ip` entry が表示されます。

後片付け：namespace と、必要なら cluster を削除します。

### Lab 3: Cluster-pool から multi-pool への移行（kind）

前提条件：cluster-pool と稼働中 Pod を持つ Cilium 1.20.2 の kind cluster。一方向の移行なので使い捨て cluster を使用します。

1. `kubectl get ciliumnodes -o yaml | grep -A3 podCIDRs` の結果を保存します。
2. cluster-pool から multi-pool への migration subsection に従って Helm upgrade します。保存した CIDR 全体を含み、同じ mask を使う default pool を用意します。
3. 各 node の PodCIDR が `spec.ipam.pools.allocated` に表示されるまで待ちます。
4. Agent を再起動します（`kubectl -n kube-system rollout restart ds/cilium`）。既存 Pod は address を維持し restored として表示され、再起動中も node 間の通信を続けられるはずです。

ロールバック：非対応です。cluster を再作成します。

### Lab 4: L2 Announcements と LB IPAM（kind、private range）

前提条件：`l2announcements.enabled=true` と `kubeProxyReplacement=true` の kind。kind Docker network 内の空き private RFC 1918 range を選びます。

1. 小さな `start`／`stop` block と `serviceSelector` を持つ `CiliumLoadBalancerIPPool` を適用します。
2. L2 announcement policy（Part 11 参照）と、selector に一致する label 付き `LoadBalancer` Service を適用します。
3. `kubectl get ippools` の利用可能 IP 数が減り、Service に block 内の external IP が付き、Service condition `cilium.io/IPAMRequestSatisfied` が `satisfied` を返すはずです。
4. 重複する block を持つ第2 pool を作成します。Conflicting と表示され、IP は割り当てられません。
5. 最初の pool に `disabled: true` を設定し、別 Service を作成します。既存 Service は IP を保持し、新しい割り当ては行われないはずです。

後片付け：Service、pool、policy を削除します。

### Lab 5: Prefix delegation を使う EKS ENI mode（sandbox account）

前提条件：private subnet のみの使い捨て EKS cluster、Nitro instance type の node、node に public IP なし、VPC／cluster security group の参照だけを許可する node SG（`0.0.0.0/0`、`::/0` は許可しない）、install と node preparation 節の operator IAM、対象 sandbox account の AWS CLI profile。

1. `node.cilium.io/agent-not-ready=true:NoExecute` taint 付きで node group を作成します。VPC CNI を無効にします（managed add-on を install しないか、実現不可能な node selector で `aws-node` を patch）。
2. `eni.enabled=true`、`eni.awsEnablePrefixDelegation=true`、`eni.awsReleaseExcessIPs=true`、`eni.iamRole`、Helm values 節の他の値で Cilium を install します。
3. Inventory を確認します。`kubectl get ciliumnode <n> -o jsonpath='{.status.eni.enis}'` に prefix を持つ ENI が表示され、`aws ec2 describe-network-interfaces --filters Name=description,Values='Cilium-CNI*'` でも同じ ENI が返ります。`spec.ipam.pools.allocated` に `/28` block があるはずです。
4. node ごとに `/28` を超える（16 Pod より多い）まで Deployment を scale します。Operator が別の prefix を割り当て、`cilium_operator_ipam_available_ips` は `used + preAllocate` より大きい値を保つはずです。
5. Scale down して180秒以上待ちます。未使用 prefix は解放され、ENI は attach されたままです。

後片付け：scale を0にし、Cilium を uninstall、node group を削除し、残った `Cilium-CNI` ENI を削除します（有効な場合は ENI GC が tag 付き orphan を削除）。ロールバック：新しい node group に VPC CNI add-on を再度有効化します。同じ稼働中 node 上で IPAM を切り替えないでください。

### Lab 6: Node IPAM（kind）

前提条件：Cilium と `nodeIPAM.enabled=true` を設定した kind（有効化後に operator を再起動）。

1. `loadBalancerClass: io.cilium/node` の `LoadBalancer` Service を作成します。
2. `status.loadBalancer.ingress` に node InternalIP が出ます（kind node に ExternalIP はありません）。
3. node に `node.kubernetes.io/exclude-from-external-load-balancers` label を付けます。その node address が list から消えるはずです。

後片付け：Service と label を削除します。

## バージョン差分

| 項目 | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Multi-pool 成熟度 | Beta banner | banner 削除 | stable | stable |
| Pool 選択 | `ip-pool` annotation のみ | `ipv4-pool`／`ipv6-pool` annotation と `podSelector`／`namespaceSelector` を追加（1.18.14ですでに存在）。`require-pool-match`、`skip-masquerade`、`--only-masquerade-default-pool` も初登場 | `allowFirstIP`／`allowLastIP` 追加 | 同じ。さらに `pool[].reservedRanges` |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | v2 storage、v2alpha1 非推奨、`cidrs` 最大32 |
| cluster-pool から multi-pool への移行 | なし | なし | 追加（`enable-cluster-pool-to-multi-pool-migration`） | 同じ |
| ENI agent model | CRD allocator | CRD allocator | multi-pool allocator。IPv6 beta（`/80`）、`pools.allocated` で release | Azure と共通の cloud multi-pool framework |
| ENI node ごとの Helm（`eni.nodeSpec`、`ipam.nodeSpec`） | CNI conf のみ | 追加 | 同じ | 同じ |
| ENI masquerade default | `enableIPv4Masquerade` false（追加） |  |  | `enableIPv6Masquerade` false（追加） |
| ENI IAM | `DescribeRouteTables` 追加 |  |  | 任意の `GetSecurityGroupsForVpc`、`DescribeManagedPrefixLists`、`GetManagedPrefixListEntries` 追加 |
| Operator `--aws-use-primary-address` | あり | あり | あり | **削除** |
| `CiliumNode.spec.eni.{min,pre}-allocate`、`max-above-watermark`、`instance-id` | あり | あり | 削除 | 削除 |
| Operator IPAM metric | node ごとの `available/used/needed_ips` と `interface_candidates` はすでに存在 | 同じ | `ipam_ips`、`ipam_available_interfaces` 削除 |  |
| Azure IPAM | CRD allocator | CRD allocator | `status.azure.interfaces[].subnet` | multi-pool protocol。余剰 IP を解放しない |
| `CiliumLoadBalancerIPPool` API | v2 | v2alpha1 非推奨 | v2 | v2 |
| `CiliumCIDRGroup` API | v2alpha1 非推奨 | v2 | v2 | v2 |
| LB IPAM sharing | key + cross-namespace |  | port conflict 規則 | 互換性検査強化 + `sharing-permit-different-pods` |

## トラブルシューティング

症状：Pod が `ContainerCreating` のまま。`kubectl describe pod` に `unable to allocate IP via local cilium agent` が出ます。

| Mode | 考えられる原因 | 確認 | 対処 |
|---|---|---|---|
| cluster-pool／kubernetes | node range 枯渇（`IPAM: IPv4: N/M allocated`） | `cilium-dbg status`、`--all-addresses` | 密度を下げるか node を追加。mask は immutable なので、拡張には新しい pool／cluster を計画 |
| cluster-pool | pool 枯渇 | `status.ipam.operator-status.error` が `allocator full` | CIDR list の既存項目は編集せず、末尾に追加 |
| cluster-pool | Agent 未起動 | CiliumNode に `spec.ipam.podCIDRs` がない | operator log、CIDR 重複、競合 error を確認 |
| kubernetes | node PodCIDR なし | `kubectl get node -o jsonpath='{.spec.podCIDRs}'` | `--allocate-node-cidrs` を有効化 |
| multi-pool | `needed` が pool 空き容量を超える | `operator-status.error`：`failed to allocate ipv4 address for node ... from pool ...` | pool に CIDR または新規 pool を追加 |
| multi-pool | pool が存在しない／未同期 | `kubectl get cpip`。`ErrPoolNotReadyYet`、`ErrManagerPoolsNotSynced` error | Pod より先に pool を作成。default pool の存在も確認 |
| multi-pool | 2つの pool に一致 | `multiple CiliumPodIPPools match pod` error | Selector を厳密にする |
| multi-pool | `require-pool-match` | Pod または namespace annotation | 一致する pool または annotation を追加 |
| ENI | Instance の ENI／IP 上限 | `ipam_nodes{category="at-capacity"}` | より大きな instance または prefix delegation |
| ENI | Subnet の IP 枯渇 | `ipam_available_ips_per_subnet` | tag／ID で subnet を追加。PD では断片化を確認（`/32` へ fallback） |
| ENI | EC2 throttling | `ec2_api_rate_limit_duration_seconds` | `externalAPILimitQPS`／`externalAPILimitBurstSize` を調整 |
| ENI | IAM action 不足 | Operator log | Install と node preparation 節の action を追加 |
| ENI | OS が secondary IP を削除 | NetworkManager／systemd-networkd log | `eth0` 以外の `eth*` を管理対象から外す |
| 任意 | CNI crash による IP 漏れ | endpoint にないのに使用中の IP | 10分の expiration を待つか、agent 再起動で reconcile |

LB IPAM の場合：Service に external IP がないなら pool の Conflicting flag、`cilium.io/IPAMRequestSatisfied` condition、`serviceSelector` の一致、BGP／L2 による address 広報を確認します。IPAM mode は単純な toggle ではありません。変更後に稼働中 mode と Helm 値が不一致なら ConfigMap を編集せず停止し、migration を計画してください。

## 検証範囲と情報源

このレビューでは live cluster で演習を実行していません。Command、field 名、default、式、flag は引用した tag の Cilium source と文書で確認しました。未検証：prefix 割り当て／解放に必要な IAM action 名（上流にあるのは private-IP action のみ）、`only-masquerade-default-pool` の Helm path（`extraConfig` を使用）、Alibaba Cloud の制限、v1.21.0-pre.3 に由来する1.21項目。Azure、`reservedRanges`、cloud multi-pool framework の version 情報は GA 前に変更される場合があります。ENI の例は private-subnet sandbox 用です。security group をインターネットに開放する例、internet-facing load balancer の作成、compute への public IP 割り当てはありません。

情報源（特記がない限り v1.20.2）：

- IPAM concepts: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst
- Cluster scope: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst
- Multi-pool: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst
- Cluster-pool to multi-pool migration: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst
- AWS ENI: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst
- LB IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst
- Node IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst
- Annotation（`ip-pool` key）: https://github.com/cilium/cilium/blob/v1.20.2/pkg/annotation/k8s.go
- Node CIDR allocator: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/cidrset/cidr_set.go
- Multi-pool manager: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/multipool_manager.go
- ENI node manager formula: https://github.com/cilium/cilium/blob/v1.20.2/operator/pkg/ipam/nodemanager/node.go
- Metrics: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/observability/metrics.rst
- **[1.21 pre-release]** multi-pool と `reservedRanges`: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/concepts/ipam/multi-pool.rst
- **[1.21 pre-release]** upgrade note: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc
- **[1.21 pre-release]** LB IPAM sharing: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst
- AWS、EKS Hybrid Nodes CNI: https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html

## クイズ

[Part 10 のクイズ](../../quizzes/networking/cilium/10-ipam-deep-dive-quiz.md)で理解度を確認してください。
