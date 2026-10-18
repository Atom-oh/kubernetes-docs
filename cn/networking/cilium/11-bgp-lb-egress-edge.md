# 第 11 部分：BGP 控制平面、负载均衡器 IP 与出口流量

> **审查基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标记为 **[1.21 预发布版]** 的项目来自 v1.21.0-pre.3，正式发布前可能变化。
> **最后更新**：2026 年 10 月 15 日

本章介绍 Cilium 集群如何连接到 **Pod 网络以外**的网络：使用 BGP Control Plane 通告路由；分配并通告 LoadBalancer IP（LB IPAM、L2 announcements、Node IPAM）；引导出口流量（Egress Gateway）；拦截发往节点本地后端的流量（Local Redirect Policy）；优先选择附近的后端（traffic distribution）；以及 L7 入口（Ingress 和 Gateway API）。最后介绍两种参考拓扑：通过 BGP 连接本地机房 ToR 交换机，以及通过 CloudFront 连接 EKS。

相关章节：[IPAM 深入解析](10-ipam-deep-dive.md)（Pod IPAM 决定 BGP 可通告哪些前缀）、[Overlay 与原生路由](09-overlay-native-routing.md)、[eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)（以下 Service 负载均衡依赖 kube-proxy 替换）、[ClusterMesh 与升级](13-clustermesh-install-upgrade.md)。

## 1. 南北向流量中的功能分工

“负载均衡器”常被用来笼统指代以下三个不同工作：

| 工作 | 要回答的问题 | Cilium 组件 |
|---|---|---|
| 地址分配 | 这个 Service 会获得哪个 IP？ | LB IPAM（`CiliumLoadBalancerIPPool`）、Node IPAM、云控制器 |
| 可达性 | 外部网络如何知道这个 IP 位于哪些节点上？ | BGP Control Plane、L2 announcements、云负载均衡器 |
| 负载均衡 | 数据包到达节点后，应发给哪个后端 Pod？ | eBPF Service 负载均衡（kube-proxy 替换）；L7 使用 Envoy |

因此，BGP Control Plane、L2 announcements 和 LB IPAM 是相互**独立**的功能，需要组合使用。本地机房常见组合是 `LB IPAM`（分配 VIP）+ `BGP Control Plane`（通告 VIP）+ eBPF kube-proxy 替换（执行负载均衡）。Service 上的 `loadBalancerClass` 决定由哪个功能负责（第 6 节）。

**BGP 不负责什么。** BGP Control Plane 只会*通告*路由，不会配置本地数据路径；从 peer 学到的路由不会安装到内核或 eBPF 映射中。它无法创建集群内部可达性（参见[上游概览](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)）。节点间 Pod 到 Pod 的路由应由 Overlay 或原生路由负责（[第 9 部分](09-overlay-native-routing.md)）。

## 2. BGP Control Plane v2

**成熟度**：在 1.19、1.20 和 1.21-pre 中，v2（`cilium.io/v2` CRD）是唯一的 BGP Control Plane。v1 `CiliumBGPPeeringPolicy` 已在 1.19 移除（第 2.9 节）。

### 2.1 架构

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

控制流（参见 [`pkg/bgp/README.md`](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/README.md)）：operator 会监视 `CiliumBGPClusterConfig`，以及它引用的 `CiliumBGPPeerConfig`/`CiliumBGPAdvertisement` 对象；然后为匹配集群配置 `nodeSelector` 的每个节点创建、更新或删除一个 `CiliumBGPNodeConfig`。每个 agent 只监视自己的 `CiliumBGPNodeConfig`，以及 peer/advertisement 配置、Secrets、Services 和（多池 IPAM 时）`CiliumPodIPPool`，并协调自己的 GoBGP 实例。因此，配置变更必须由运行中的 operator 负责传播。

speaker 是嵌入在 agent 中的 GoBGP。GoBGP 是唯一受支持的路由器实现。内嵌库在 1.19 中从 `gobgp/v3` 升级为 `gobgp/v4`（1.20.2 和 1.21.0-pre.3；可查阅各版本 tag 的 `go.mod`）。支持 IPv4、IPv6、单栈和双栈，但只能通告 agent 自身已启用的地址族。

### 2.2 启用

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

| Helm 值 | Agent/operator 标志 | 默认值 | 含义 |
|---|---|---|---|
| `bgpControlPlane.enabled` | `--enable-bgp-control-plane` | `false` | 启用此功能 |
| `bgpControlPlane.secretsNamespace.name` / `.create` | `--bgp-secrets-namespace` | `kube-system` / `false` | 读取 `authSecretRef` 所引用 Secret 的 namespace；chart 可创建该 namespace |
| `bgpControlPlane.statusReport.enabled` | `--enable-bgp-control-plane-status-report` | `true` | 将会话状态写入 `CiliumBGPNodeConfig.status`；禁用时会清除状态 |
| `bgpControlPlane.routerIDAllocation.mode` / `.ipPool` | `--bgp-router-id-allocation-mode` / `-ip-pool` | `default` / 空 | Router-ID 分配策略（第 2.7 节） |
| `bgpControlPlane.legacyOriginAttribute.enabled` | `--enable-bgp-legacy-origin-attribute` | `false` | `LoadBalancerIP` 路由携带 ORIGIN `INCOMPLETE`（兼容 MetalLB），而非 `IGP` |
| `enableNoServiceEndpointsRoutable` | `--enable-no-service-endpoints-routable` | `true` | 没有后端时，Cluster-policy VIP 是否仍保持通告（第 2.5 节） |

`bgpControlPlane.*` 值在 1.18.14、1.19.8、1.20.2 和 1.21.0-pre.3 中相同（对比各版本 tag 中的 `values.yaml` 得出）。**[1.21 预发布版]** BGP 标志已移入 `pkg/bgp/config` 模块，因此同一组标志（包括 router-ID 标志）现在也出现在 operator 的 flag 集合中；Helm 用法没有变化。

监听 TCP/179 是可选的。默认情况下，`bgpInstance` 没有 `localPort`，所以 agent 仅主动向 peer 发起连接，不监听入站连接。若设置 `localPort: 179`，则需通过 chart 的 `securityContext.capabilities.ciliumAgent` 列表为 agent 授予 `CAP_NET_BIND_SERVICE`；使用高位端口可避免此能力要求。

### 2.3 五种 CRD

所有资源都是集群范围的 `cilium.io/v2`。同名 kind 的 `cilium.io/v2alpha1` 版本**已弃用**（在 1.20.2 和 1.21.0-pre.3 中仍提供，并标记 `+kubebuilder:deprecatedversion`）；新 manifest 一律使用 `cilium.io/v2`。

| Kind | 简称 | 由谁编写 | 用途 |
|---|---|---|---|
| `CiliumBGPClusterConfig` | `cbgpcluster` | 用户 | 指定哪些节点运行哪些 BGP 实例和 peer |
| `CiliumBGPPeerConfig` | `cbgppeer` | 用户 | 会话参数，以及向 peer 通告哪些内容 |
| `CiliumBGPAdvertisement` | `cbgpadvert` | 用户 | 通告的内容及其属性 |
| `CiliumBGPNodeConfig` | `cbgpnode` | operator（用户只读） | 解析后的逐节点配置和会话状态 |
| `CiliumBGPNodeConfigOverride` | `cbgpnodeoverride` | 用户 | 逐节点配置 router ID、ASN、端口和源地址 |

资源之间的关联使用两种不同机制，容易因此配置错误：

```
CiliumBGPClusterConfig.spec.bgpInstances[].peers[].peerConfigRef.name  --by NAME-->  CiliumBGPPeerConfig
CiliumBGPPeerConfig.spec.families[].advertisements (label selector)    --by LABELS-> CiliumBGPAdvertisement.metadata.labels
```

peer 配置通过匹配 `CiliumBGPAdvertisement` 对象上的**标签**来选择 advertisement，而不是匹配其 spec。一个 peer 可以匹配多个 advertisement 对象。如果没有匹配的 advertisement，会话仍可建立，但不会通告任何路由。

#### CiliumBGPClusterConfig

| 字段 | 类型/限制 | 说明 |
|---|---|---|
| `spec.nodeSelector` | LabelSelector | nil 或空值表示选择**所有**节点。每个节点最多只能匹配一个 `CiliumBGPClusterConfig` |
| `spec.bgpInstances[]` | 1 至 16 项，键为 `name` | 每项对应一个 GoBGP 实例 |
| `.name` | 1 至 255 个字符，且唯一 | 被 override 引用；指标中显示为 `instance_name` |
| `.localASN` | 1 至 4294967295 | 此处可选；可通过 override 为每个节点单独设置 |
| `.localPort` | 1 至 65535 | 未设置时实例不监听 |
| `.peers[]` | 键为 `name` | |
| `.peers[].peerAddress` | IPv4 或 IPv6 | 仅在使用 `autoDiscovery` 时可选 |
| `.peers[].peerASN` | 0 至 4294967295，默认 0 | 为 0 时跳过对 peer OPEN 消息的 ASN 校验 |
| `.peers[].autoDiscovery` | `mode: DefaultGateway`、`defaultGateway.addressFamily: ipv4\|ipv6` | peer 是节点的默认网关（见下文） |
| `.peers[].peerConfigRef.name` | 字符串 | `cilium.io/v2` 中**只有 `name` 字段**；`group`/`kind` 仅存在于已弃用的 v2alpha1 CRD 中 |

集群配置的状态条件包括：`cilium.io/NoMatchingNode`、`cilium.io/MissingPeerConfigs`、`cilium.io/ConflictingClusterConfig`（两个集群配置选择了同一节点时，operator 会拒绝后创建的配置）。

**自动发现（`DefaultGateway`）。** agent 会与节点默认网关建立 peer，而不是固定的 `peerAddress`。ToR 必须支持动态邻居（FRR 中的 `bgp listen range`），并且所有 ToR 使用相同的本地 ASN。不支持 link-local 默认网关。存在多条默认路由（多宿主）时，Cilium 会针对每个地址族创建**一个**会话，使用 metric 较低的路由；故障时会切换到另一条路由，但不能通过此方式同时为同一地址族维持两个会话。如需两个会话，请配置静态 `peerAddress` 条目。

#### CiliumBGPPeerConfig

| 字段 | 默认值/限制 | 说明 |
|---|---|---|
| `spec.transport.peerPort` | 179（1 至 65535） | 远端端口 |
| `spec.transport.sourceInterface` | 无 | 从此接口选择源 IP。每个地址族最多只能有一个符合条件的地址（不能是 loopback、multicast 或 IPv6 link-local）。接口不存在时，Cilium 会回退到出口接口自动检测。1.18 文档未提及；1.19+ 已有说明 |
| `spec.timers.connectRetryTimeSeconds` | 120（最小 1） | 带随机抖动；实际重试间隔为 [N, 2N) |
| `spec.timers.holdTimeSeconds` | 90（3 至 65535） | 更改 hold 或 keepalive 会重置会话 |
| `spec.timers.keepAliveTimeSeconds` | 30（1 至 65535） | CRD 规则：keepalive <= holdTime |
| `spec.authSecretRef` | 无 | BGP secrets namespace 中 Secret 的名称；使用 `password` 键（RFC 2385 TCP MD5） |
| `spec.gracefulRestart.enabled` | 存在该配置块时必需 | |
| `spec.gracefulRestart.restartTimeSeconds` | 120（1 至 4095） | |
| `spec.ebgpMultihop` | 1（1 至 255） | 默认 TTL 为 1；iBGP 会忽略 |
| `spec.families[]` | afi + safi + `advertisements` selector | 仅支持 `ipv4/unicast` 和 `ipv6/unicast`。省略 `families` 时会协商两个单播地址族，但**不会**通告任何内容 |

状态条件：`cilium.io/MissingAuthSecret`。

> **上游文档更正。** 上游配置页面称 `holdTimeSeconds=9` 和 `keepAliveTimeSeconds=3` 是最低“可用”值，但 CRD 的最小值实际为 hold >= 3、keepalive >= 1（且 keepalive <= hold）。9/3 是建议的激进设置，不是下限。

#### CiliumBGPAdvertisement

`spec.advertisements[]` 项：

| 字段 | 说明 |
|---|---|
| `advertisementType` | `PodCIDR`、`CiliumPodIPPool`、`Service`、`Interface` |
| `service.addresses[]` | 至少指定一个 `LoadBalancerIP`、`ClusterIP`、`ExternalIP`；`Service` 类型必需 |
| `service.aggregationLengthIPv4` / `IPv6` | 0 至 31 / 0 至 127；聚合前缀，而不是逐个通告 /32 和 /128 |
| `interface.name` | `Interface` 类型必需 |
| `selector` | 匹配 Service（或 pool）的 LabelSelector。未设置时，除 PodCIDR 类型外都不选择任何对象；`PodCIDR` 不得设置此字段 |
| `attributes.communities` | `standard[]`、`wellKnown[]`、`large[]` |
| `attributes.localPreference` | 仅发送给 iBGP peer |

CEL 校验要求：`Service` 必须设置 `service`，`Interface` 必须设置 `interface`，`PodCIDR` 不得设置 `selector`。

#### CiliumBGPNodeConfig（operator 输出）

`spec` 镜像已解析的配置（增加了 `routerID` 和 `localAddress`）。`status.bgpInstances[].peers[]` 包含 `name`、`peerAddress`、`peerASN`、`peeringState`、`establishedTime`、`timers.appliedHoldTimeSeconds`/`appliedKeepaliveSeconds` 和 `routeCount[]`（afi、safi、received、advertised）。`cilium.io/BGPReconcileError` 条件会报告协调失败。这是自动化和告警的正确数据来源，无需 exec 进入 agent。

#### CiliumBGPNodeConfigOverride

`metadata.name` **必须与节点名相同**；实例名和 peer 名必须与集群配置中的名称匹配。

| 字段 | 说明 |
|---|---|
| `spec.bgpInstances[].name` | 与集群配置中的实例匹配 |
| `.routerID` | IPv4 地址字符串 |
| `.localPort` | 覆盖监听端口 |
| `.localASN` | 1 至 4294967295；可按节点/机架配置 ASN |
| `.peers[].name` | 与集群配置中的 peer 匹配 |
| `.peers[].localAddress` | 强制指定源地址（因此也决定出口链路）；默认根据到 peer 的路由查询选择 |
| `.peers[].localPort` | 发起连接时使用的源端口 |

### 2.4 实际 peer 设置

**计时器。** 默认值为 120/90/30（connect-retry/hold/keepalive）。没有 BFD 时，hold time 是检测非直连 peer 故障的唯一机制，因此 ToR 链路常使用 9/3 这样的激进值。代价是 keepalive 负载更高，也更容易受到 agent CPU 停顿影响。

**Graceful Restart。** 设置 `gracefulRestart.enabled: true` 后，Cilium 会作为 Restarting Speaker 工作（RFC 4724，以及支持 Notification 的 RFC 8538 graceful restart）。agent 重启时，peer 会在 `restartTimeSeconds` 到期前保留已学到的路由，因此 agent 升级期间 eBPF 中仍运行的数据平面不会出现黑洞。`restartTimeSeconds` 应大于 agent 最坏情况下的重启时间（包括拉取镜像）；升级前先预拉镜像。代价是节点真正宕机时，GR 会保留其路由直到重启时间到期，因此 `externalTrafficPolicy: Cluster` 的 VIP 流量在此期间仍可能发往已宕机节点。

**多跳。** `ebgpMultihop: N` 为 eBGP 会话设置 TTL，用于连接相隔多跳的 peer（例如通过 loopback 建立邻接的 ToR 或 route server）。不影响 iBGP。

**MD5。**

```bash
kubectl -n kube-system create secret generic bgp-auth \
  --from-literal=password='<value from your secret store>'
```

通过 `authSecretRef: bgp-auth` 引用此 Secret。密码错误时会显示 `dial: i/o timeout`，而非认证错误，因为内核会丢弃签名错误的报文。Secret 缺失不会阻止会话建立：Cilium 会使用**空密码**继续运行，记录错误并设置 `cilium.io/MissingAuthSecret`。会话经过 NAT 时 MD5 无法工作。

**不支持 BFD。** Cilium 在 1.18 到 1.21-pre 的所有版本中都不支持 BFD。缓解方式包括：较短的 hold timer、直连链路（链路断开时 TCP 会立即关闭）、用于 agent 重启情形的 Graceful Restart，以及弹性哈希/Maglev（见下文）。

### 2.5 路由通告

#### PodCIDR

通告节点已分配的 PodCIDR（不是整个地址池）。只有按节点分配 PodCIDR 的 IPAM 模式才有作用：`cluster-pool` 和 Kubernetes host scope。**ENI、Azure 等云 IPAM 模式下，`PodCIDR` 通告没有作用**：Pod IP 是 VPC（或 VNet）地址，不是由 Cilium 为每个节点管理的前缀；云网络本身已经会路由这些地址。参见[IPAM 深入解析](10-ipam-deep-dive.md)。

#### CiliumPodIPPool

用于多池 IPAM。`selector` 会匹配 pool 标签；特殊键 `io.cilium.podippool.namespace` 和 `io.cilium.podippool.name` 可按 pool 身份选择。只会通告实际分配给 `CiliumNode` 的 CIDR。1.20.2 中 BGP 代码监视 `v2alpha1.CiliumPodIPPool`；**[1.21 预发布版]** `CiliumPodIPPool` 升级到 `cilium.io/v2`，BGP 也随之调整（v1.21.0-pre.3 的 `pkg/bgp/manager/reconciler/pod_ip_pool.go`）。

#### Service

默认使用精确的 `/32` 或 `/128` 路由。


| 来源 | 取值位置 | 是否遵循流量策略 |
|---|---|---|
| `LoadBalancerIP` | `.status.loadBalancer.ingress[].ip` | 仅 `externalTrafficPolicy` |
| `ExternalIP` | `.spec.externalIPs`（使用 KPR 时要求 `externalIPs.enabled`） | 仅 `externalTrafficPolicy` |
| `ClusterIP` | `.spec.clusterIP(s)`（外部访问需要 BPF 设置“External access to ClusterIP services”） | 仅 `internalTrafficPolicy` |

Selector 特殊键：`io.kubernetes.service.namespace`、`io.kubernetes.service.name`。

**流量策略的影响。**

| 策略 | 从哪些节点通告 |
|---|---|
| `Cluster` | 集群配置选中的所有节点 |
| `Local` | 仅至少有一个本地就绪后端的节点；路由随 Pod 所在节点变化 |

**没有后端时**：若 `externalTrafficPolicy: Cluster` 且 `--enable-no-service-endpoints-routable=true`（默认值），所有节点仍会通告 VIP；否则撤回该路由。`Local` 会撤回路由。

**`loadBalancerClass`。仅当** Service class 未设置或为 `io.cilium/bgp-control-plane` 时，Cilium 才会通告该 Service。由其他 class 管理的 Service（例如 `service.k8s.aws/nlb`）会被忽略。

**重叠的通告（1.18 及之后**）。若多个 advertisement 匹配同一个 Service，则 communities 取**并集**，`localPreference` 取**最大值**。1.18 之前采用最后一个匹配项。

**聚合**。本地流量策略下会忽略 `aggregationLengthIPv4/6`。已知问题：聚合范围内尚未分配的 VIP 可能造成路由环路；两个 advertisement 生成相同聚合路由但属性不同时，行为未定义（[cilium/cilium#37623](https://github.com/cilium/cilium/pull/37623)、[cilium/cilium#40585](https://github.com/cilium/cilium/issues/40585)）。

**ECMP**。从多个节点通告相同 VIP，受路由器的 ECMP 路径数上限影响。节点故障会使流量重分布，除非路由器使用 resilient hashing；对于 `Cluster` 策略，Cilium 中的 Maglev 可让不同节点选择的后端保持一致。

#### Interface（1.19 及之后）

将本地接口的地址作为 /32 和 /128 路由通告。排除项：loopback 范围、multicast、IPv6 link-local 和 v4-mapped 地址。接口必须在管理层面和运行层面均为 `up`（或运行状态为 `unknown`）。Cilium 不会配置接口地址；常见用途是使用 dummy 接口承载稳定的节点地址或 anycast 地址。

#### 属性

| 属性 | 取值 |
|---|---|
| `communities.standard` | `"65000:99"` 或 4 字节十进制值 |
| `communities.wellKnown` | `internet`、`planned-shut`、`accept-own`、`route-filter-translated-v4`、`route-filter-v4`、`route-filter-translated-v6`、`route-filter-v6`、`llgr-stale`、`no-llgr`、`blackhole`、`no-export`、`no-advertise`、`no-export-subconfed`、`no-peer` |
| `communities.large` | `"A:B:C"` |
| `localPreference` | 仅 iBGP 使用；对 eBGP peer 会省略该属性 |

Cilium 会按（peer、地址族、advertisement 类型）生成 GoBGP 导出策略，例如 `65000-ipv4-PodCIDR`，并创建一个 `allow-local` 导入策略。这些都是内部策略。v2 **没有面向用户的路由策略、prefix-list、AS-prepend、MED 或 next-hop CRD**；可利用 communities 作为挂钩，并在 ToR 上通过基于 community 的 route-map 实现策略。

### 2.6 完整示例：每个机架通过 eBGP 连接两台 ToR

地址和 ASN 均为示例值。

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

逐节点 override（节点名称填入 `metadata.name`）：

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

| 模式 | ID 的选择方式 |
|---|---|
| `default` | 节点 IPv4 地址（IPv4 和双栈）；仅 IPv6 节点则使用 `cilium_host` MAC 的低 32 位 |
| `ip-pool` | 从 `bgpControlPlane.routerIDAllocation.ipPool`（IPv4 CIDR）中分配 |
| 手动设置（`NodeConfigOverride.routerID`） | `default` 模式下不校验；`ip-pool` 模式下，若地址位于池内则不得冲突 |

### 2.8 检查状态

**先看状态**（无需 exec）：

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements,ciliumbgpnodeconfigs
kubectl get ciliumbgpnodeconfigs <node> \
  -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'
kubectl describe ciliumbgpclusterconfig rack0
```

**CLI。**`cilium bgp peers [-o json|summary] [--node N]` 和 `cilium bgp routes <available|advertised|received> <afi> <safi>` 在 1.20.2 中可用。这些命令调用 agent REST API，该 API 已在 **1.20 弃用**（见下文）；1.21.0-pre.3 仓库内的 CLI 源码仍通过 exec 在 agent Pod 中运行 `cilium bgp peers -o json`。

**Hive shell（从 1.20 起优先使用**）。上游 1.20 升级说明指出，通过本地 REST API 和 `cilium-dbg bgp` 命令列出 BGP peer、路由和 route policy 的功能已弃用，应改用 BGP hive shell 命令。agent 使用的二进制文件是 `cilium-dbg`：

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/peers
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/routes out ipv4 unicast
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/route-policies
```

| 命令 | 含义 |
|---|---|
| `bgp/peers [-f table\|table-json\|json\|detailed] [-o file] [--no-uptime]` | 会话表 |
| `bgp/routes <loc\|in\|out> <afi> <safi> [-a\|--with-attrs] [--no-age] [-f ...]` | `loc` = Loc-RIB，`in` = Adj-RIB-In，`out` = Adj-RIB-Out |
| `bgp/route-policies [-i instance]` | Cilium 生成的导出/导入策略 |

1.20.2 和 1.21.0-pre.3 中都有上述三个命令（`pkg/bgp/commands/cell.go`）。`cilium` CLI 没有 `shell` 子命令；请在 agent Pod 中使用 `cilium-dbg`。

**日志**。Agent 日志使用 `subsys=bgp-control-plane`；operator 日志使用 `subsys=bgp-cp-operator`。

**指标**（agent 前缀为 `cilium_bgp_control_plane_`）：`session_state`（1 表示 established）、`advertised_routes`、`received_routes`（标签为 `instance_name`、`local_asn`、`neighbor`、`neighbor_asn`、`afi`、`safi`）、`reconcile_errors_total{instance_name}`、`reconcile_run_duration_seconds{instance_name}`。Operator 指标：`cilium_operator_bgp_control_plane_reconcile_errors_total{resource_kind,resource_name}` 和 `..._reconcile_run_duration_seconds`。

> **指标标签变化**。1.19.8 指标页使用标签 `vrouter`，1.20.2 改为 `instance_name`。1.20 升级说明没有提及此重命名，因此从 1.19 升级到 1.20 后，按 `vrouter` 匹配的 dashboard 和告警会静默失效。升级时应一并更新。

### 2.9 v1 移除与 CRD 版本时间线

| 版本 | 状态 |
|---|---|
| 1.18 | `CiliumBGPPeeringPolicy`（v1）弃用；若 v1 和 v2 都匹配某节点，PeeringPolicy 优先。v2alpha1 BGP v2 CRD 弃用，改用 `cilium.io/v2` |
| 1.19 | v1 CRD **和**控制平面（`pkg/bgpv1`）**均移除**；升级前必须迁移 |
| 1.20 | v2 BGP CRD 的 v2alpha1 副本仍提供，但已弃用 |
| 1.21-pre | 相同 |

1.19 之前，v2alpha1 PeerConfig 中的 `spec.transport.localPort` 字段已移除；端口现在由集群配置实例（`localPort`）和 override 配置。

### 2.10 运维与故障情景

| 事件 | 行为 | 缓解措施 |
|---|---|---|
| Agent 重启或升级 | 会话断开（speaker 位于 agent 中）；数据路径继续转发 | 使用 Graceful Restart；`restartTimeSeconds` 应长于 agent 启动时间；预拉取新镜像 |
| 节点崩溃 | peer 等待 hold time（启用 GR 时还要等待 restart time） | 缩短 hold timer；结合 resilient hashing 使用 ECMP |
| 直连链路断开 | TCP 立即关闭 | 不适用 |
| 多跳链路断开 | 等待 hold timer（默认 90s） | 缩短 hold time；当前不支持 BFD |
| Operator 停止 | 不再生成新的 `CiliumBGPNodeConfig`；operator 也负责 PodCIDR 和 LB IP 分配 | Operator 高可用 |
| Service 失去所有后端 | 参见第 2.5 节 | 有意选择所需策略 |

**节点关闭操作步骤**。先 drain 节点；更改节点标签，使其不再匹配 `nodeSelector`，从集群配置中移除该节点（会话会发送 Notification 并关闭）；等待 peer 撤回路由（立即撤回，或等待 RFC 8538 stale timer 到期）；预计 ECMP 流会出现一些重置。

**[1.21 预发布版]** BGP controller 会等待主机数据路径 BPF 程序挂载且 LB 映射填充完毕后才通告路由（`pkg/bgp/agent/datapath_waiter.go`），从而关闭 agent 启动后“路由先通告、但尚不可服务”的时间窗口。1.20 中没有此行为。

### 2.11 本地机房 ToR 参考拓扑

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

设计检查清单：每个机架配置一个集群配置（节点只能匹配一个）；每个机架配置两个 peer；hold 9 / keepalive 3，并使用长于 agent 启动时间的 GR restart time；通过 `authSecretRef` 配置 MD5；使用 communities 区分 Pod 路由与 Service 路由，再由 ToR route-map 处理；核实 ToR 的最大 ECMP 路径数；不使用 BFD。

### 2.12 BGP 与 AWS

使用 ENI IPAM 的 EKS 集群中，Pod IP 是 VPC 地址，VPC 网络本身已经负责路由；节点没有自己的 PodCIDR，因此通告 PodCIDR 没有作用，且 VPC 没有接收节点路由的 BGP speaker。因此，AWS 上的 BGP 主要适用于在本地机房运行的 EKS Hybrid Nodes（参见[Hybrid Nodes 网络配置](../../eks-hybrid-nodes/02-network-configuration.md)），由本地 ToR 作为 peer。本仓库中现有的 Hybrid Nodes 示例使用 `v2alpha1` API，因为它们固定使用 1.18 构建版本；1.19 及之后版本请改用 `cilium.io/v2`。

## 3. LB IPAM

**成熟度**：稳定的 `cilium.io/v2` CRD `CiliumLoadBalancerIPPool`（1.18.14 中 v2 为存储版本且仍提供 v2alpha1；v2alpha1 首次在 1.19.8 标记弃用）。LB IPAM 内置于 operator，只有创建第一个 pool 后才开始工作（`--enable-lb-ipam`，默认 true）。它只负责分配地址，不负责通告。

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

注意：`serviceSelector` 位于 `spec` 下，而不是 `blocks` 下（上游文档示例的缩进有误）。

| Pool 字段 | 说明 |
|---|---|
| `blocks[]` | `cidr`，或 `start` + `stop` |
| `serviceSelector` | 特殊键 `io.kubernetes.service.namespace`/`.name` |
| `disabled` | 默认 false |
| `allowFirstLastIPs` | `Yes` 或 `No`；`No` 仅为 CIDR block 保留首尾地址；对 /31、/32、/127、/128 和 start/stop block 无效 |

需要了解的行为：

- CIDR 重叠时，后创建的 pool 会标记冲突（`cilium.io/PoolConflict`）。状态条件为 `cilium.io/IPsTotal`、`IPsAvailable`、`IPsUsed`；可用 `kubectl get ippools` 查看。
- 修改 pool 可能会重新分配已有 Service 的 IP。
- class 处理：默认情况下，没有 class 的 `LoadBalancer` Service 由 LB IPAM 管理。Helm `defaultLBServiceIPAM` 可设为 `lbipam`（默认）、`nodeipam` 或 `none`；选择 `none` 时，只有带可识别 class 的 Service 才会获得 IP。Cilium 无法识别的 class 会被静默忽略。Service 会得到 `cilium.io/IPAMRequestSatisfied` 条件。
- 地址族遵循 `ipFamilyPolicy`：SingleStack（IPv4 可用时优先）、PreferDualStack、RequireDualStack。
- 使用 `lbipam.cilium.io/ips: "a,b"` 请求指定地址（仍需匹配 pool selector；`.spec.loadBalancerIP` 已弃用）。不要请求 pool 的首尾地址。
- **共享地址**：使用 `lbipam.cilium.io/sharing-key` 和 `lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"|"*"`。1.20.2 中，只要端口/协议没有冲突，Service 就可以共享。**[1.21 预发布版]** 兼容条件更严格：不能有相同的端口+协议；必须使用相同的 `externalTrafficPolicy`；`Local` 模式下必须选择相同 Pod，除非所有 Service 都设置 `lbipam.cilium.io/sharing-permit-different-pods: "true"`（BGP 和 L2 不感知 L4，因此流量可能被丢弃）；除非允许跨 namespace，否则必须位于相同 namespace。
- **1.19 数据路径变化**：南北向 TCP/UDP 流量若发往 LB-IPAM IP 上未被 Service 定义的端口，会被丢弃。
- Gateway API：`Gateway.spec.addresses` 会传给 LB IPAM；`spec.infrastructure.annotations` 中的 `io.cilium/lb-ipam-ips` 注解优先级更高，并计划在后续弃用。

Pod IPAM 是独立主题，参见[IPAM 深入解析](10-ipam-deep-dive.md)。

## 4. L2 announcements

**成熟度**：在 1.20.2 和 1.21.0-pre.3 中为 Beta。CRD 仍为 `cilium.io/v2alpha1` `CiliumL2AnnouncementPolicy`。

每个 Service 会选出一个节点，由该节点通过 ARP（IPv4）或 NDP（IPv6）响应 Service 的 external IP 或 LoadBalancer IP，然后由 eBPF 执行负载均衡。该功能面向不使用 BGP 的本地 LAN。**不适用于 AWS VPC 内部**：VPC 不为 VIP 提供 L2 广播语义，也不支持通过 gratuitous ARP 故障转移。仅适用于本地机房或混合网络场景。

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

| 字段 | 说明 |
|---|---|
| `nodeSelector`、`serviceSelector` | 允许通告的节点；要处理的 Service |
| `interfaces[]` | Go regex，按 OR 处理；不是安全控制。设备也必须包含在 Cilium 的 `--devices` 集合中 |
| `externalIPs`、`loadBalancerIPs` | 布尔值，默认均为 false |

Service 必须未设置 `loadBalancerClass`，或 class 为 `io.cilium/l2-announcer`。

**Leader election**。每个 Service 使用一个 `coordination.k8s.io` Lease，名称为 `cilium-l2announce-<ns>-<svc>`，位于 Cilium 的 namespace。选举先到先得，因此负载可能不均。新 leader 会发送 gratuitous ARP。默认值：`leaseDuration` 15s、`leaseRenewDeadline` 5s、`leaseRetryPeriod` 2s。约束：duration > renewDeadline；renewDeadline 必须严格大于 1.2（leader election 的 JitterFactor）× retryPeriod，否则 agent 会记录警告并覆盖计时器。故障转移时间介于 `leaseDuration - leaseRenewDeadline` 和 `leaseDuration + leaseRenewDeadline` 之间：使用默认值时为 10 到 20 秒；使用 3s/1s/200ms 时为 2 到 4 秒。

**API 负载**。每个 Service lease 大约每隔 `leaseRenewDeadline` 续约一次，因此 QPS 可粗略估算为 `QPS ~ number_of_services x (1 / leaseRenewDeadline)`（忽略重试和读取）。Agent API 客户端默认限额是 10 QPS / burst 20，且与所有其他 agent API 流量共享：默认 5s 时，每个 Service 约占 0.2 QPS，因此几十个被 leader 管理的 Service 就会消耗大部分预算；计时器设为 1s 时，约 10 个 Service 就会耗尽预算。缩短计时器前，先提高 `k8sClientRateLimit`。RBAC 需要 lease 的 create/get/update/list/delete 权限。

**限制**。不兼容 `externalTrafficPolicy: Local`（当选节点上可能没有 Pod，流量会被丢弃）。每个 IP 的所有流量都到达同一个节点，因此集群前面没有额外的负载均衡。

**L2 Pod announcements** 是另一项独立功能：`l2podAnnouncements.enabled` 和 `.interfacePattern`（regex）会为本地 Pod IP 发送 GARP/NA。旧标志 `--l2-pod-announcements-interface` 在 1.19 移除。

检查方式：运行 `kubectl -n kube-system get lease | grep cilium-l2announce`、`cilium-dbg shell -- db/show l2-announce`、`cilium-dbg shell -- db/show devices`；也可从 LAN 上另一台主机运行 `arping`。

## 5. Node IPAM

Helm 设置 `nodeIPAM.enabled=true`（默认 false；operator 标志 `--enable-node-ipam`；设置后需重启 operator）。带 `loadBalancerClass: io.cilium/node`（或设置 `defaultLBServiceIPAM: nodeipam`）的 Service 会将节点地址写入 `.status.loadBalancer`：存在 ExternalIP 时使用它，否则使用 InternalIP，并遵循 `ipFamilies`。`Cluster` 策略发布所有节点；`Local` 仅发布有 EndpointSlice Pod 的节点。带有标签 `node.kubernetes.io/exclude-from-external-load-balancers` 或污点 `ToBeDeletedByClusterAutoscaler` 的节点会跳过；注解 `io.cilium.nodeipam/match-node-labels` 可限制节点范围。Cilium Ingress/Gateway Service 的 EndpointSlice 是合成的，因此 Node IPAM 不支持其 `Local` 策略。仅在 BGP 和 L2 均无法使用时采用，而且只使用私有节点地址：发布公共节点 IP 会创建 CloudFront-only 规则之外的公网入口。

## 6. 哪个功能负责 Service？

| `loadBalancerClass` | 负责人 | 依赖 |
|---|---|---|
| 未设置 | 默认由 LB IPAM（`defaultLBServiceIPAM`）管理 | 需要 pool；还需要 BGP 或 L2 提供可达性 |
| `io.cilium/bgp-control-plane` | LB IPAM + BGP 通告 | BGP Control Plane |
| `io.cilium/l2-announcer` | LB IPAM + L2 announcement | L2 announcements |
| `io.cilium/node` | Node IPAM | `nodeIPAM.enabled` |
| `service.k8s.aws/nlb` | AWS Load Balancer Controller | Cilium 的 BGP/LB IPAM 会忽略 |

## 7. Egress Gateway

**成熟度**：`CiliumEgressGatewayPolicy` 为 `cilium.io/v2`（集群范围，简称 `cegp`）；1.20 文档未将其标为 Beta。

选定 Pod 发往选定目标 CIDR 的流量会被转发到 gateway 节点，并 SNAT 为稳定源 IP，因此外部防火墙看到可预测的地址。

依赖条件：`egressGateway.enabled=true`、`bpf.masquerade=true`、`kubeProxyReplacement=true`；需要同时重启 agents **和** operator。与 `kvstore` 身份模式不兼容（应使用 `crd`）、与 ClusterMesh 不兼容（gateway 必须位于同一集群），也不兼容 CiliumEndpointSlice。`--enable-ipv4-egress-gateway` 在 1.19 移除。

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

| 字段 | 说明 |
|---|---|
| `selectors[]` | `podSelector` 和/或 `namespaceSelector`（通过 `io.kubernetes.pod.namespace` 标签选择 namespace）；不允许只设置 `nodeSelector` |
| `destinationCIDRs[]`、`excludedCIDRs[]` | IPv4 和 IPv6；excluded CIDR 必须是 destination CIDR 的子集。内部地址（Pod、节点、API server）始终从 EGW 中排除 |
| `egressGateway.nodeSelector` | 必填。匹配多个节点时按节点名称排序后取第一个。**没有匹配节点：发往目标 CIDR 的流量会被丢弃** |
| `egressGateway.interface` / `egressIP` | 互斥（两者都设置时会忽略该策略）。`interface` 使用该接口的第一个 IPv4/IPv6 地址；`egressIP` 必须位于 Cilium 管理的设备上；两者都省略时，使用默认路由接口及其第一个 IPv4/IPv6 地址 |
| `egressGateways[]` | 最多 64 项；非空时忽略 `egressGateway` |

限制：

- **1.20.2 和 1.21.0-pre.3 均无高可用。**`egressGateways[]` 是静态多 gateway 配置：按 CiliumEndpoint UID 的哈希将每个源端点固定到一个 gateway。更改集合会重新分配端点并中断现有连接（cilium/cilium#39245）。这两个版本的源码（检索 `pkg/egressgateway`）都没有健康检查或死 gateway 自动故障转移。1.21-pre CRD 相较 1.20.2 只改变了 CIDR 类型。
- 选定 gateway 后，不会跟踪 IP 变化；需要重新应用策略。
- 配置的 IP 不存在时，流量会因 “No Egress IP configured” 而被丢弃。
- 新 Pod 在策略完成配置前，可能短暂使用自己的 IP 或节点 IP 发流量。
- 对每个（egress IP、远端 IP:port）组合，SNAT 端口预算约为 65535 减去 NodePort 范围上限（默认 32767），即 32768 个连接。可通过 `cilium-dbg shell -- db/show nat-stats` 监控。

检查：运行 `kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf egress list`（显示源 IP、目标 CIDR、egress IP、gateway IP）。

**在 EKS 上**。Gateway 节点的附加 ENI 上必须配置出口地址（额外 ENI 或辅助私有 IP）。Egress IP 是 VPC 私有地址；要从这些地址访问互联网，需通过 NAT gateway 路由。不要为 gateway 节点分配公共 IP 或 EIP。使用 ENI IPAM 时，`--egress-multi-home-ip-rule-compat` 在 1.19 移除，应先在 1.18 中迁移并停止使用。

## 8. Local Redirect Policy

`CiliumLocalRedirectPolicy`（namespaced 的 `cilium.io/v2`）会将发往 Service ClusterIP 或任意 IP:port 的流量重定向到节点本地的后端 Pod。

设置 `localRedirectPolicies.enabled=true` 启用（旧键 `localRedirectPolicy` 已弃用）；之后重启 operator 和 agent。可选的集群级 allow-list 为 `localRedirectPolicies.addressMatcherCIDRs`（上游文档 YAML 中该键拼写不同；Helm 键为 `addressMatcherCIDRs`）。

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

| 匹配器 | 用途 |
|---|---|
| `serviceMatcher` | 仅匹配 ClusterIP Service；将 Service 条目替换为 `LocalRedirect` 类型，且只使用节点本地后端 |
| `addressMatcher{ip, toPorts[]}` | 匹配非 Service IP；拒绝覆盖现有 ClusterIP frontend |

规则：后端 Pod 必须位于策略的 namespace；多端口场景必须使用命名端口；仅重定向**新建**连接（需重启客户端）；策略不可更新（需删除后重建）。支持的 kube-proxy-replacement 配置包括：完整 KPR；KPR 且 `socketLB.hostNamespaceOnly=true`；关闭 KPR 但启用 `socketLB.enabled=true`；仅关闭 KPR（仅适用于 Pod 到 ClusterIP）。主要用途是节点本地 DNS（将 kube-dns frontend 重定向到其独立网络 namespace 中的 node-local-dns Pod）。通过 `cilium-dbg lrp list` 检查。

## 9. Service 流量分布

`loadBalancer.serviceTopology`（默认 `false`，标志为 `--enable-service-topology`）会让 kube-proxy 替换同时遵循 Topology Aware Routing 提示和 `spec.trafficDistribution`。`PreferSameZone`（及已弃用的别名 `PreferClose`）会根据 EndpointSlice zone hint 匹配节点的 `topology.kubernetes.io/zone` 标签；`PreferSameNode` 优先选择本地节点的后端，若没有符合条件的后端则回退到默认选择。**[1.21 预发布版]** 只有活跃（ready）的后端才作为优先候选。这不同于会限制流量范围而非仅给出优先选择的 `externalTrafficPolicy`/`internalTrafficPolicy: Local`。对于多 AZ EKS，启用 `serviceTopology: true` 并设置 `trafficDistribution: PreferSameZone` 可减少跨 AZ 流量。Gateway API 中，`CiliumGatewayClassConfig.spec.service.trafficDistribution` 会传递到生成的 Service。

## 10. L7 入口：Ingress 与 Gateway API

依赖条件：`kubeProxyReplacement=true`、`l7Proxy=true`（默认）、TPROXY 支持（默认通过 iptables；Beta `bpf.tproxy=true` 可移除 iptables 依赖），以及 LoadBalancer Service 支持（或使用 1.16+ 的 host-network 模式）。

**流量路径**。eBPF 会拦截发往 Service 端口的数据包，并将其（TPROXY）重定向到每节点的 Envoy。流量会获得特殊的 `ingress` 身份，因此策略会应用两次：world 到 ingress、ingress 到后端。无论 `externalTrafficPolicy` 取何值，都会保留源 IP；设置 `Local` 时，Cilium 会让每个节点都能在健康检查端口通过健康检查。你的 `CiliumNetworkPolicy` 必须允许这两段流量。TLS passthrough 时，后端看到的源地址是 Envoy IP。

### Ingress

| Helm 值 | 默认值 |
|---|---|
| `ingressController.enabled` / `.default` | `false` / `false` |
| `ingressController.loadbalancerMode` | `dedicated`（`shared` 或 `dedicated`；可通过每个 Ingress 的注解 `ingress.cilium.io/loadbalancer-mode` 设置） |
| `ingressController.enforceHttps` | `true` |
| `ingressController.useRemoteAddress`、`.xffNumTrustedHops` | `true`、`0` |
| `ingressController.ingressLBAnnotationPrefixes` | `lbipam.cilium.io`、`nodeipam.cilium.io`、`service.beta.kubernetes.io`、`service.kubernetes.io`、`cloud.google.com`（从 Ingress 传递到 Service） |
| `ingressController.service.*`（shared） | `name: cilium-ingress`、`type: LoadBalancer`、`externalTrafficPolicy: Cluster`、annotations、`loadBalancerClass` |
| `ingressController.hostNetwork.*` | `enabled: false`、`sharedListenerPort: 8080` |

### Gateway API

Cilium 1.20.2 和 1.21.0-pre.3 使用 **Gateway API v1.6.1**（1.19.8 使用 v1.4.1；1.18.14 使用 v1.3.0）。支持的类型包括：GatewayClass、Gateway、HTTPRoute、GRPCRoute、TLSRoute、BackendTLSPolicy、ReferenceGrant、ListenerSet、TCPRoute、UDPRoute。必需 CRD：GatewayClass、Gateway、HTTPRoute、GRPCRoute、ReferenceGrant、BackendTLSPolicy、TLSRoute。TCPRoute、UDPRoute 和 ListenerSet 为可选项（CRD 不存在时相应功能禁用）。使用 `kubectl apply --server-side` 安装。

> **升级陷阱：Gateway API v1.6.1 与 TLSRoute**。在 v1.6.1 中，TLSRoute 从 `v1alpha2` 升级到 `v1`。1.20 升级说明要求至少使用 v1.6.1。如果已有 TLSRoute 对象，应安装 v1.6.1 **experimental-channel** 的 TLSRoute CRD（其中仍保留 `v1alpha2` 版本）。若将现有 `v1alpha2` 数据覆盖为 **standard-channel** 的 v1.6 TLSRoute CRD，已有对象将无法读取，并且会像是从 etcd 消失。升级 Cilium 到 1.20 **之前**，请备份 TLSRoute 并升级 Gateway API CRD。

| Helm 值 | 默认值 |
|---|---|
| `gatewayAPI.enabled` | `false` |
| `gatewayAPI.gatewayClass.create` | `auto` |
| `gatewayAPI.enableProxyProtocol`、`.enableAppProtocol`、`.enableAlpn` | `false` |
| `gatewayAPI.useRemoteAddress`、`.xffNumTrustedHops` | `true`、`0` |
| `gatewayAPI.externalTrafficPolicy` | `Cluster`（使用 host network 时忽略） |
| `gatewayAPI.secretsNamespace` | `create: true`、`name: cilium-secrets`、`sync: true` |
| `gatewayAPI.hostNetwork.enabled` / `.nodes.matchLabels` | `false` / `{}` |

默认生成的 Service 名为 `cilium-gateway-<gateway>`，类型为 `LoadBalancer`。可通过 `CiliumGatewayClassConfig` 自定义（namespaced、alpha 版 `cilium.io/v2alpha1`，由 `GatewayClass.parametersRef` 引用）：`spec.service{type, externalTrafficPolicy, loadBalancerClass, ipFamilies, ipFamilyPolicy, allocateLoadBalancerNodePorts, loadBalancerSourceRanges, loadBalancerSourceRangesPolicy, trafficDistribution}`、`envoy.serverHeaderTransformation`、`httpOptions.grpcWebTranslation.enabled`。每个 Gateway 的 `spec.infrastructure.annotations` 和 `labels` 会复制到生成的 Service，可借此传递 `service.beta.kubernetes.io/aws-load-balancer-*` 注解。不支持 `spec.infrastructure.parametersRef`。

Host-network 模式（`gatewayAPI.hostNetwork.enabled=true`）：Envoy 监听节点接口；使用 1023 以上的端口，或授予 `NET_BIND_SERVICE`；不能与 LoadBalancer Service 模式同时使用；不兼容 TCPRoute/UDPRoute；Gateway status 最多显示 16 个地址。

### EKS 模式：CloudFront VPC origin → 内部 NLB → Cilium

唯一公网入口是 CloudFront，本方案中没有任何直接面向互联网的资源。

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

对于 Gateway API 方案，将 `CiliumGatewayClassConfig.spec.service.loadBalancerClass: service.k8s.aws/nlb` 设为该项，并在 `Gateway.spec.infrastructure.annotations` 中加入相同的 `aws-load-balancer-*` 注解。

此方案的规则：

- 必须使用 `scheme: internal`，绝不能用 `internet-facing`。
- 使用 `target-type: instance`。Cilium 的 shared Ingress Service 使用合成的 EndpointSlice，因此 `ip` target 不会解析为 Pod；参见[Ingress 与 Gateway API](../../service-mesh/cilium-service-mesh/05-ingress-gateway.md)。
- 负载均衡器的安全组只允许 CloudFront：可使用 Service 管理的安全组 `CloudFront-VPCOrigins-Service-SG`（创建 VPC origin 后生成；限制更严格，优先采用；不要为自己的安全组使用此前缀），或 CloudFront 托管 prefix list `com.amazonaws.global.cloudfront.origin-facing`（双栈时再加 `com.amazonaws.global.ipv6.cloudfront.origin-facing`）。不得允许 `0.0.0.0/0` 或 `::/0` 入站，也不得为节点分配公网 IP 或 EIP（参见 [AWS：VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)）。
- 节点安全组只允许来自 NLB 安全组的 NodePort 范围流量，不要开放 CIDR 给互联网。

## 11. SRv6 与静态路由

SRv6 **并非受支持的功能**。1.20.2 和 1.21.0-pre.3 源码中都没有 SRv6 文档页、Helm 键或 CRD；只剩下隐藏的 agent 标志 `--enable-srv6`、BPF hook 和 `cilium-dbg bpf srv6` 检查命令，没有 OSS 控制平面。不要将其纳入方案。静态路由应使用原生路由配合 `autoDirectNodeRoutes` 或云路由表（[第 9 部分](09-overlay-native-routing.md)）。

## 实验

> 实验 1–4 需要本地实验环境（kind 或若干 VM）和 FRR 等路由器容器；实验 5 使用一次性 AWS sandbox account 和 `--profile <SANDBOX_PROFILE>`。预期结果以文字描述，未提供实际捕获输出。

### 实验 1：与 FRR ToR 建立 BGP 会话

**前置条件**：包含 2 个 worker 的 kind 集群；worker 与 FRR 容器位于共享 Docker 网络（FRR ASN 为 65000，已为节点 IP 配置 neighbor，remote AS 为 65001）；Cilium 配置 `bgpControlPlane.enabled=true`；按节点 IP 修改第 2.6 节的 manifest（移除 `authSecretRef`，或先创建 Secret）。

1. 为 worker 添加标签 `rack=rack0`；应用 ClusterConfig、PeerConfig 和 Advertisement。
2. `kubectl get ciliumbgpnodeconfigs` 应为每个带标签节点列出一个对象。
3. `kubectl get ciliumbgpnodeconfigs <node> -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'` 和 `cilium-dbg shell -- bgp/peers` 应显示 `established`；FRR 上的 `show bgp summary` 应显示 neighbor 已建立。
4. `cilium-dbg shell -- bgp/routes out ipv4 unicast` 应显示节点 PodCIDR；FRR 上的 `show ip route bgp` 应显示已学习到该路由。
5. 删除其中一个节点上的 agent Pod。启用 GR 时，FRR 应保留路由并标记为 stale，直到 restart time 到期；未启用 GR 时，路由应立即消失。比较两种情况。

**回滚/清理**：删除三个 BGP 资源；移除节点标签。删除 ClusterConfig 后，operator 会移除 NodeConfig 并关闭会话。

### 实验 2：LB IPAM、BGP 与流量策略交互

**前置条件**：实验 1 正在运行。

1. 创建第 3 节中的 pool 和 Service（地址块必须处于 FRR 容器可接受的范围内）。
2. `kubectl get svc web -n example` 应显示从 pool 分配的 EXTERNAL-IP；`kubectl get ippools` 中 `IPsUsed` 应为 1。
3. `bgp/routes out ipv4 unicast` 应显示每个选中节点通告 /32。通过 FRR 容器运行 `curl <VIP>`。
4. 运行 `kubectl patch svc web -n example -p '{"spec":{"externalTrafficPolicy":"Local"}}'`。路由应仅保留在有就绪 Pod 的节点上；扩缩 Deployment 并观察通告跟随 Pod 位置变化。

**清理**：删除 Service、Deployment 和 pool。

### 实验 3：L2 announcements

**前置条件**：运行在 Linux bridge 上的 kind 集群；启用 KPR 和 `l2announcements.enabled=true`，计时器设为 3s/1s/200ms，并提高 client rate limit；同一 bridge 上有客户端容器。

1. 应用 L2 policy 以及从 pool 获取地址的 `LoadBalancer` Service。
2. `kubectl -n kube-system get lease | grep cilium-l2announce` 应显示 Service 对应的 lease；客户端的 `arping` 应返回 leader 节点的 MAC。
3. 删除 leader 节点上的 Cilium agent Pod（或停止节点容器），测量 `arping` 失败持续时间：上述计时器设置下应为数秒，使用默认值时应为 10 到 20 秒。

**清理**：删除 policy 和 Service。回滚时将 lease 值恢复为默认值。

### 实验 4：Egress Gateway

**前置条件**：启用 KPR、`bpf.masquerade=true`、`egressGateway.enabled=true`，并重启 agents 和 operator；外部 web server 容器会记录客户端 IP；某节点带标签 `egress-node=true`，且其设备上有辅助地址。

1. 应用与第 7 节类似的策略，将该地址和 server CIDR 填入。
2. 从选中 Pod `curl` server；日志应显示 egress IP，而不是节点 IP 或 Pod IP。
3. 在源节点运行 `cilium-dbg bpf egress list` 查看条目。移除节点标签后，发往该 CIDR 的流量应被丢弃（没有匹配的 gateway）。

**清理/回滚**：删除 policy 并移除标签。策略生效期间，受影响流量会被中断。

### 实验 5：CloudFront 后的 EKS 内部 NLB（sandbox account）

**前置条件**：运行 `aws sts get-caller-identity --profile <SANDBOX_PROFILE>`，确认输出的是预期 sandbox account `<ACCOUNT_ID>` 和计划使用的 assumed role；EKS 集群已安装 Cilium 和 AWS Load Balancer Controller；CloudFront VPC origin 已创建。

1. 使用第 10 节中的 Helm 值安装（也可选择 Gateway API 方案）。
2. `aws elbv2 describe-load-balancers --profile <SANDBOX_PROFILE> --query 'LoadBalancers[].[LoadBalancerName,Scheme]'` 应显示新 NLB 的 scheme 为 `internal`。
3. `aws ec2 describe-security-groups --profile <SANDBOX_PROFILE> --group-ids <nlb-sg> --query 'SecurityGroups[].IpPermissions'` 应只显示 CloudFront VPC-origin 安全组或 prefix list 作为来源，不能包含 `0.0.0.0/0` 或 `::/0`。
4. 将 NLB 设为 VPC origin 的目标；通过 CloudFront 域名发起请求。

**清理**：删除 Ingress 或 Gateway（controller 会删除 NLB），然后等待 NLB 消失；必须通过真实的 not-found 响应确认，不能只看见 `deleting` 状态就认为已删除。

## 版本差异

| 领域 | 1.18 | 1.19 | 1.20 | 1.21-pre |
|---|---|---|---|---|
| BGP v1 `CiliumBGPPeeringPolicy` | 弃用 | **移除** | 已移除 | 已移除 |
| BGP CRD | v2（及 v2alpha1） | 使用 `cilium.io/v2` 存储；v2alpha1 弃用 | 相同 | 相同 |
| BGP `Interface` advertisement、`transport.sourceInterface` | 文档未提及 | 已存在 | 已存在 | 已存在 |
| GoBGP | 本次审查未涉及 | gobgp v3（1.19.8） | gobgp v4 | gobgp v4 |
| BGP 指标标签 | 本次审查未涉及 | 文档使用 `vrouter` | `instance_name` | `instance_name` |
| `cilium-dbg bgp` / REST 路由列表 | 支持 | 支持 | **弃用**；改用 hive shell `bgp/*` | 标记为弃用 |
| 等待数据路径就绪后才通告 BGP | 否 | 否 | 否 | **是** |
| `CiliumLoadBalancerIPPool` | v2（存储），仍提供 v2alpha1 | 使用 `cilium.io/v2`（v2alpha1 弃用） | v2 | v2；共享规则更严格 |
| Gateway API CRD | v1.3.0 | v1.4.1 | **v1.6.1**（注意 TLSRoute 陷阱） | v1.6.1 |
| `CiliumPodIPPool` API | v2alpha1 | v2alpha1 | v2alpha1 | **v2** |
| Egress Gateway | CRD v2 | 移除 `--enable-ipv4-egress-gateway`、`--egress-multi-home-ip-rule-compat` | 无高可用 | 无高可用 |
| L2 announcements | Beta | Beta | Beta（CRD v2alpha1） | Beta |
| SRv6 | 不存在 | 不存在 | 不存在 | 不存在（仅隐藏标志） |

## 故障排查

| 症状 | 可能原因 | 检查方式 |
|---|---|---|
| 没有创建 `CiliumBGPNodeConfig` | Operator 未运行，或 `nodeSelector` 未匹配任何节点 | 检查 ClusterConfig 条件 `NoMatchingNode`；查看 operator 日志 `subsys=bgp-cp-operator` |
| 集群配置被拒绝 | 另一个集群配置选择了同一节点 | 检查 `ConflictingClusterConfig` |
| 会话卡住，显示 `dial: i/o timeout` | MD5 密码错误、ACL 问题或源地址错误 | 检查 `authSecretRef`、`cilium.io/MissingAuthSecret`、`localAddress`/`sourceInterface` |
| 会话已建立但没有路由 | PeerConfig 的 `families[].advertisements` 标签与 advertisement 标签不匹配 | 比较标签；检查 `bgp/route-policies` |
| EKS 上没有通告 PodCIDR | ENI IPAM 没有逐节点 PodCIDR | 参见[IPAM](10-ipam-deep-dive.md) |
| 没有通告 Service VIP | `loadBalancerClass` 不是 `io.cilium/bgp-control-plane`/未设置、selector 未匹配，或 `Local` 策略下没有就绪后端 | 检查 Service YAML 和 `bgp/routes out` |
| Agent 升级时路由消失 | 未启用 Graceful Restart，或 restart time 太短 | 检查 PeerConfig GR；升级前预拉镜像 |
| 升级到 1.20 后 Grafana BGP 面板为空 | 标签 `vrouter` 已改名为 `instance_name` | 更新查询 |
| LB IP 一直是 `<pending>` | 没有 pool、selector 不匹配、pool 冲突或 class 不识别 | `kubectl get ippools`；检查 Service condition |
| L2 VIP 不稳定或不可用 | 使用 `Local` 策略，或 lease API 被限流 | 检查 Lease 对象；提高 `k8sClientRateLimit` |
| Egress 流量被丢弃 | 没有节点匹配 gateway `nodeSelector`，或设备上没有该 IP | 检查 `bpf egress list` 和 drop reason |
| 升级 Gateway API CRD 后 TLSRoute 消失 | 使用 standard-channel v1.6 CRD 覆盖了 v1alpha2 数据 | 从备份恢复；使用 experimental-channel CRD |
| Gateway Service 卡住 | 缺少必需 Gateway API CRD，或关闭了 KPR | 查看 operator 日志；运行 `cilium status` |

## 验证限制与来源

本章实验未在实时集群中执行；内容依据上游源码和文档核对。通过 `pkg/bgp/commands` 核对了 `bgp/peers` 和 `bgp/routes` 的命令语法，但没有捕获实际表格输出，因此文中没有展示此类输出。未研究 EKS 原生（非 hybrid）集群上的 BGP 用例，例如 Transit Gateway Connect 或 VPC Route Server peer，因此未纳入。未经验证的事项包括：Egress Gateway 是否会在 1.21 GA 加入基于健康状态的故障转移；指标标签具体在哪个 1.19 至 1.20 版本间更名（已确认 1.20.2 使用新名称，1.19.8 文档中未出现）。

来源（除非另有说明，均为 v1.20.2 tag）：

- [BGP Control Plane 概览](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)、[配置](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)、[运维](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [BGP CRD 类型](https://github.com/cilium/cilium/tree/v1.20.2/pkg/k8s/apis/cilium.io/v2)、[hive shell 命令](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/commands/cell.go)
- [LB IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst)、[L2 announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst)、[Node IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst)
- [Egress Gateway](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst)、[Local Redirect Policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/local-redirect-policy.rst)
- [1.20 升级说明](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)、[Gateway API](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/servicemesh/gateway-api)
- [v1.21.0-pre.3 BGP 数据路径等待器](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/bgp/agent/datapath_waiter.go)、[v1.21.0-pre.3 LB IPAM](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst)

## 测验

完成[第 11 部分测验](../../quizzes/networking/cilium/11-bgp-lb-egress-edge-quiz.md)检验理解。
