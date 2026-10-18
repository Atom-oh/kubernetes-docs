# 第 9 部分：Overlay 与原生路由深入解析

> **审查基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标记为 **[1.21 预发布版]** 的内容来自 v1.21.0-pre.3，正式发布前可能变化。
> **最后更新**：2026 年 10 月 15 日

本章深入介绍[网络模型与 VXLAN](03-networking.md)中的模式切换。我们将解释在隧道模式和原生路由模式下，两个位于不同节点的 Pod 之间的数据包会经历什么、各个 BPF 程序的职责、安全身份如何随封装传递、MTU 与伪装如何确定，以及哪些配置组合会导致 agent 拒绝启动。本章也会将 kube-proxy 替换、DSR、Maglev、socket-LB、主机路由、netkit、带宽管理器和加密放入同一数据路径中讨论，最后提供 EKS 选型指南和故障排查手册。

相关章节：[eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)（程序挂载点、映射）、[IPAM 深入解析](10-ipam-deep-dive.md)（Pod CIDR 的来源）、[BGP、负载均衡、出口与边缘](11-bgp-lb-egress-edge.md)（通告 Pod CIDR、外部负载均衡器）、[mTLS、加密与身份](12-mtls-encryption-identity.md)（WireGuard/IPsec 详情）、[ClusterMesh、安装与升级](13-clustermesh-install-upgrade.md)。

## 目录

1. 路由模式矩阵
2. Cilium 中的 VXLAN 与 Geneve
3. 身份如何随 VNI 传递
4. 控制平面：从 CiliumNode 到隧道端点
5. 数据包路径：同节点、隧道、原生路由
6. 原生路由：由谁提供路由
7. 启动校验：硬失败与静默回退
8. MTU 计算
9. 伪装
10. 主机路由：传统模式与 BPF 模式
11. 数据路径设备：veth 与 netkit
12. 数据路径中的 Service 负载均衡
13. 带宽管理器、BBR 与 BIG TCP
14. 加密之间的相互影响
15. VTEP 与多播（Beta）
16. EKS 选型指南
17. 检查速查表
18. 实验
19. 版本差异
20. 故障排查
21. 验证限制与来源

---

## 1. 路由模式矩阵

在 1.20 中，`routingMode` 只接受两个值：`tunnel`（默认值）和 `native`。本章介绍的其他行为都由这一选择以及少数自行请求隧道设备的功能决定。

| 场景 | Helm | 不同节点间的 Pod 到 Pod 通信 | 谁必须路由 Pod CIDR |
|---|---|---|---|
| 隧道（默认） | `routingMode: tunnel`，`tunnelProtocol: vxlan`（默认）或 `geneve` | BPF 设置隧道元数据，内核通过 `cilium_vxlan`/`cilium_geneve` 使用 UDP 封装 | 无需额外路由；底层网络只需提供节点间 IP 连通性以及 UDP 8472/6081 |
| 原生 | `routingMode: native` | 数据包保留 Pod IP 发出，由内核路由（或在启用 BPF 主机路由时通过 BPF FIB 重定向） | 网络负责：云路由器/ENI、`autoDirectNodeRoutes`、BGP 或静态路由 |
| 原生 + 功能启用的隧道 | `routingMode: native`，并启用 Egress Gateway 或带 `dsrDispatch: geneve` 的 DSR | 普通 Pod 流量走原生路由；该功能为自己的数据包创建隧道设备 | 与原生模式相同；隧道只承载该功能的流量 |

第三行对于检查 `ip link` 的结果很重要：在原生路由集群中看到 `cilium_geneve` 设备并不代表配置错误。代码中，Egress Gateway 和使用 Geneve 的 DSR 都是“隧道启用器”；即使 `routingMode` 为 `native`，它们也会请求创建该设备（参见 agent 的 `tunnel` 包 `pkg/datapath/tunnel/tunnel.go`）。

成熟度（按 1.20.2 文档所述）：VXLAN/Geneve 隧道模式和原生路由均为稳定功能。BGP 是路由通告机制，不是转发模式；参见[BGP、负载均衡、出口与边缘](11-bgp-lb-egress-edge.md)。

> **1.21 关注项。** v1.21.0-pre.3 源码包含尚未完成且未记录文档的另一种路由模式框架，但 Helm chart 尚未开放此模式。本章不会为其命名或描述。假设 1.21 GA 中 `routingMode` 仍然只有两个值之前，请重新查阅 1.21 GA 路由文档。

## 2. Cilium 中的 VXLAN 与 Geneve

二者都是 UDP 封装。无论使用哪一种，Cilium 都会使用基于流量、采用 collect-metadata 模式的内核 netdev。这意味着内核驱动会根据 BPF 附加的逐包元数据构造外层头部；Cilium 不会在 BPF 中构造外层头部。

| 属性 | VXLAN | Geneve |
|---|---|---|
| Helm 值 | `tunnelProtocol: vxlan`（默认） | `tunnelProtocol: geneve` |
| 默认 UDP 目标端口 | 8472 | 6081 |
| 设备 | `cilium_vxlan` | `cilium_geneve` |
| 身份传递位置 | VNI（24 位） | VNI（24 位）；机制相同 |
| Cilium 使用的选项/TLV | 无 | 仅 DSR Service 地址/端口选项（class `0x014B`，type `0x81`） |
| DSR 支持 | 不支持；使用 VXLAN 隧道时，agent 会拒绝 `dsr`/`hybrid` | `dsrDispatch: geneve` |
| 内核配置 | `CONFIG_VXLAN` | `CONFIG_GENEVE` |

二者还都需要 `CONFIG_FIB_RULES`。端口 8472 是 Linux 内核历史上的 VXLAN 默认端口，不是 IANA 分配的 4789；Cilium 为兼容性继续使用 8472。可通过 `tunnelPort` 覆盖，但更改端口会重建设备并造成短暂中断；更改 MTU 则会原地修改设备。

相关可调参数：

- `tunnelSourcePortRange: "0-0"`（默认值）让内核驱动选择外层 UDP 源端口范围。缩小范围会限制底层网络 ECMP/过滤器看到的熵，但不会影响身份。
- `underlayProtocol: auto|ipv4|ipv6`（1.18 新增）。`auto` 在启用 IPv4 时优先选择 IPv4，否则选择 IPv6。IPv6 底层会使隧道开销增至 70 字节，并禁止 XDP 加速；Egress Gateway 要求使用 IPv4 底层网络。
- 切换 `tunnelProtocol` 会删除原设备并创建新设备，因此应按节点逐个进行，并预留中断窗口。

安全组/防火墙要求：所有节点之间允许 UDP 8472（VXLAN）或 UDP 6081（Geneve），并允许 TCP 4240 进行健康检查以及 ICMP echo。在 AWS 中，应通过安全组之间的引用来配置（节点安全组引用自身），绝不要向互联网开放 CIDR。WireGuard 需要 UDP 51871；IPsec 需要 ESP（IP 协议 50），而 AWS 安全组默认不允许该协议。

```yaml
# values: Geneve overlay (needed if you later want DSR dispatch via Geneve)
routingMode: tunnel
tunnelProtocol: geneve
```

## 3. 身份如何随 VNI 传递

每个由 Cilium 封装的数据包，其 24 位隧道 ID（VNI）就是发送端点的**源安全身份**。VXLAN 和 Geneve 都遵循此规则。Geneve 选项不用于传递身份。

以下规则来自 v1.20.2 的 `bpf/lib/identity.h`、`bpf/lib/encap.h` 和 `bpf/bpf_overlay.c`：

- 在双栈集群中，保留身份 `world-ipv4`（9）和 `world-ipv6`（10）都会作为 `world`（2）发送；接收端根据内部 L3 协议还原正确身份。
- `host` 身份（1）不会发送。发送端会在封装前将其改写为 `local-node`/`remote-node`（6）。如果通过隧道收到声明身份为 `host` 的数据包，该包会以 `DROP_INVALID_IDENTITY` 丢弃。
- 接收端仍然维护 ipcache。上游将身份随包传递描述为一种优化，可避免在远端节点上进行一次身份查找，而不是唯一的事实来源。对于来自远端节点的流量，`bpf_overlay.c` 会通过 ipcache 进一步确定身份。

由此可得：

1. 在线路上，VNI 等于 `cilium-dbg endpoint list`（IDENTITY 列）或 `cilium-dbg identity list` 中看到的身份编号。实验 1 会验证这一点。
2. 入口策略决策在目标节点上根据携带的身份执行，因此入口策略无需再次将源 IP 解析为 Pod。
3. VTEP 集成（第 15 节）依赖此行为：外部 VTEP 流量必须携带 VNI 2（`world`）。

Geneve 中只有 DSR 会用到选项：负载均衡节点会插入一个包含原始 Service 地址和端口的 Geneve 选项，供后端节点改写响应。该选项增加 12 字节开销，由数据路径处理（参见第 8 节）。

## 4. 控制平面：从 CiliumNode 到隧道端点

隧道模式下，对于任意目标 Pod IP，发送端都需要知道：(a) 它的安全身份；(b) 承载该 Pod 的节点 IP（隧道端点）。二者都保存在同一个 BPF LPM 映射中：

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

- `cilium_ipcache_v2` 是一个 LPM 映射。其值包含身份、隧道端点（远端节点 IPv4 或 IPv6 地址）、加密密钥索引，以及 `skip_tunnel` 等标记。只有当主机 IP 与本地节点 IP 不同时，监听器才会设置隧道端点。
- 对于每个远端 PodCIDR，agent 还会安装一条经过 `cilium_host` 的内核路由（`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`）。BPF 封装决策使用 ipcache；此路由则作为主机发起流量时的回退路径。
- **`cilium_tunnel_map` 已不存在。** 1.17 中它仍位于 BPF（`bpf/lib/encap.h`），`cilium-dbg bpf tunnel list` 会导出该映射。1.18 中它已从数据路径移除（1.18.14 BPF 源码树中没有引用；agent 只会取消固定遗留映射），Go 包则在 1.19 移除。隧道端点现在位于 ipcache 值中；可通过 `cilium-dbg bpf ipcache list`（隧道端点列）、`cilium-dbg bpf nodeid list` 和 `cilium-dbg node list` 检查。

## 5. 数据包路径：同节点、隧道、原生路由

程序名称来自 v1.20.2 的 `bpf/bpf_lxc.c`、`bpf/bpf_overlay.c` 和 `bpf/lib/local_delivery.h`。挂载机制请参见[eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)。

### 5.1 节点 1 上的 Pod A 到节点 2 上的 Pod B：隧道模式

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

- **由内核封装，BPF 负责引导。** BPF 设置隧道键（`BPF_F_ZERO_CSUM_TX`、TTL 64），并将数据包重定向到隧道设备。这纠正了常见的简化说法“eBPF 自己封装数据包”。
- 加密在**封装之后**应用（IPsec 从 1.18 起如此；WireGuard 使用独立设备），因此启用加密后，物理 NIC 看到的是 ESP 或 WireGuard 流量，而不是 VXLAN。
- 响应流量根据 conntrack 条目对称返回；目标节点封装时使用 Pod B 的身份作为 VNI。
- 发往**远端节点**地址的 Pod 流量不会经过隧道。在隧道模式中，此类流量会被伪装（第 9 节）。

### 5.2 同节点通信

`__lookup_ip4_endpoint` 查找目标本地端点；`ipv4_local_delivery` 会 tail-call 到 `cilium_call_policy`（目标端点的入口策略），再通过 `bpf_redirect_peer`（使用 BPF 主机路由时的 veth）或 `bpf_redirect` 投递数据包。使用 netkit 时，Pod 到 Pod 的流量会通过从出口到入口的普通 `redirect` 转发。此路径不进行封装。

### 5.3 Pod A 到 Pod B：原生路由

步骤 1–4 相同；步骤 5 不经过隧道：

- 使用**BPF 主机路由**（启用 KPR 和 BPF 伪装时的默认行为）时，`fib_redirect_v4` 会执行 FIB 查找并直接从 NIC 重定向出去（类似 `bpf_redirect_neigh`），绕过 netfilter 和上层协议栈。
- 使用**传统主机路由**时，程序返回 `CTX_ACT_OK`（交给协议栈处理），Linux 内核根据现有路由转发数据包：AWS ENI/每端点路由、`autoDirectNodeRoutes`、通过 BGP 学习的路由或云路由器。

外部网络会看到原始 Pod IP，因此必须能够路由这些地址；反欺骗检查（例如非 ENI 实例上的 EC2 源/目标检查）和安全组也必须允许这些流量。对于由 ENI 提供的 Pod IP，这些地址由 VPC 自身管理。

## 6. 原生路由：由谁提供路由

`routing-mode: native` 会将非本地数据包交给内核，并由 Cilium 启用 IP 转发。Cilium 不会向网络通告 Pod CIDR 的位置；路由由以下某一种方式提供：

| 路由提供方 | Helm | 说明 |
|---|---|---|
| 云网络 | `eni.enabled`（AWS）、`gke.enabled`、Azure IPAM | Pod IP 是云网络原生地址；chart 会设置每端点路由（`enable-endpoint-routes`） |
| 直接节点路由 | `autoDirectNodeRoutes: true` | 安装 `<remote podCIDR> via <remote node IP>`；所有节点必须位于同一个 L2 网段 |
| BGP | Cilium BGP 控制平面或外部守护进程 | 参见[第 11 章](11-bgp-lb-egress-edge.md) |
| 静态路由 | 无 | 由 operator 管理 |

`directRoutingSkipUnreachable`（默认值为 false）会跳过到非直连节点的直接路由安装；它**要求**启用 `autoDirectNodeRoutes`，否则 agent 会退出。这不会回退到隧道模式。

Helm 防护校验：原生路由下若将 `enableIPv4Masquerade` 设为真值，除非满足下列任一条件，否则 `helm template` 会因“原生路由模式必须设置 ipv4NativeRoutingCIDR”而失败：`ipam.mode` 为 `eni` 或 `alibabacloud`、启用了 ip-masq-agent，或设置 `nativeRoutingCIDRFromClusterPool: true`（1.20 新增；要求 `ipam.mode=cluster-pool` 且恰好配置一个池 CIDR）。chart 中 `enableIPv4Masquerade` 的默认值为 null（agent 自身默认值为 true），所以即使 agent 随后进行伪装，只要该值保持未设置，就**不会**触发此校验。IPv6 的校验逻辑相同，涉及 `ipv6.enabled`、`enableIPv6Masquerade`（chart 默认值为 true）和 `ipv6NativeRoutingCIDR`。

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

原生路由 CIDR 的语义：目的地址位于该 CIDR 内时不会被伪装，而是交给协议栈。如果未设置该值，默认使用本地节点的 PodCIDR。对于 ENI/Azure/AlibabaCloud，operator 会从云环境中推导 CIDR（仅使用主 VPC CIDR）；如果手动指定的值不包含在任一 VPC CIDR 中，agent 会报错：“None of the VPC CIDRs contains the specified native routing CIDR”。

### AWS ENI 数据路径（路由方式）

使用 ENI IPAM 时，Pod IP 是 ENI 上的辅助 IP 或前缀。agent 会安装每端点路由，并为每个 Pod IP 安装两条 ip 规则：入口规则 `to <podIP> lookup main`（优先级 20，`RulePriorityIngress`），以及出口规则 `from <podIP> lookup <ENI table>`（优先级 111，`RulePriorityEgressv2`；只有在 Azure IPAM 模式下才使用较早的优先级 110）。仅当启用伪装时，出口规则才会增加 `to <VPC CIDR>` 选择器（每个 VPC CIDR 一条规则）；ENI 默认关闭伪装，因此默认的出口规则没有 `to` 选择器。ENI 路由表中包含一条经由 ENI 子网路由器的默认路由。路由器 IP 取自 ENI 地址空间，以便生成 ICMP packet-too-big 消息。自 1.18 起，operator 需要 `ec2:DescribeRouteTables` 权限。地址分配详情参见[IPAM 深入解析](10-ipam-deep-dive.md)。

## 7. 启动校验：硬失败与静默回退

有些错误配置组合会让 agent 停止运行，另一些只会记录一条日志并以较弱的数据路径继续运行，这常让运维人员浪费排查时间。需要区分二者。

### 硬失败（agent 退出或 Helm 渲染失败）

| 配置 | 结果 |
|---|---|
| `routingMode: tunnel` + `autoDirectNodeRoutes: true` | 致命错误：“auto-direct-node-routes cannot be used with tunneling. Packets must be routed through the tunnel device.”（1.20.2） |
| `ipam: eni` + 隧道模式 | 致命错误：“Cannot specify IPAM mode eni in tunnel mode.” |
| 未设置 `autoDirectNodeRoutes` 却启用 `directRoutingSkipUnreachable` | 致命错误 |
| DSR 或 hybrid 模式 + VXLAN 隧道 | 错误：Node Port `dsr` 模式不能与 `vxlan` 隧道一起使用 |
| 隧道 + DSR/hybrid，但未设置 `dsrDispatch: geneve` | 错误：要求使用 `geneve` dispatch |
| 设置 `dsrDispatch: geneve`，但未设置 `tunnelProtocol: geneve` | 错误：要求使用 Geneve 隧道协议 |
| XDP 加速 + IPv6 底层网络 | 错误 |
| 原生路由 + `enableIPv4Masquerade` 为真值 + 未设置原生 CIDR 且无例外配置 | Helm 模板失败（值未设置、chart 默认值为 null 时不会失败） |
| 显式设置 `bpf.datapathMode: netkit`，但未满足前置条件 | 硬失败（第 11 节） |
| 内核 5.18 缺少 `skb_set_tstamp` 时启用 BBR，或未使用 BPF 主机路由却为 Pod 启用 BBR | Agent 报错（第 13 节） |
| 未启用 BPF 主机路由/KPR/BPF 伪装却启用 BIG TCP，或与 IPsec/DSR IPIP 组合 | 启动错误 |
| 未启用 BPF 伪装却设置 `enable-remote-node-masquerade` | 错误 |
| 未启用 BPF 伪装却使用 `ip-masq-agent` | 错误 |

在 VXLAN 和每 Service 注解模式（`bpf.lbModeAnnotation=true`）下，校验器只接受 `dsrDispatch: ipip`；全局默认模式必须保持为 `snat`。

**[1.21 预发布版]** `autoDirectNodeRoutes` 的错误信息变为“auto-direct-node-routes requires native routing mode.”。实际条件仍是“已启用隧道”。

### 静默回退（agent 继续运行，但数据路径能力较弱）

| 配置 | 行为 |
|---|---|
| 默认启用 BPF 主机路由，但使用 iptables 伪装或关闭 KPR | 记录日志“BPF host routing requires bpf-masquerade / kube-proxy-replacement ... Falling back to legacy host routing”；改用传统路由 |
| 设置 `bpf.datapathMode: auto`，但未满足 netkit 前置条件 | 记录日志“datapath autodiscovery failed, reverting from netkit to veth”；改用 veth |
| 带宽管理器 + IPsec | 发出警告并禁用管理器 |
| 内核不支持 BIG TCP | 发出警告并禁用 |
| 内核缺少所需 BPF helper，却启用了多播 | 记录“Disabled support for BPF Multicast”，并保持关闭 |
| CNI chaining | chart 强制使用传统主机路由，并禁用无 conntrack 的 iptables 规则 |

代码有意采用这种不对称行为：主机路由和 `auto` 属于“尽力而为”，而显式指定的功能（netkit、BBR、BIG TCP）无法实现时会直接失败。每次变更后都应验证实际生效状态（第 17 节），不能只相信配置值。

## 8. MTU 计算

**检测。** 基础 MTU 是 Cilium 选定的原生设备中最小的 MTU，不包括 `cilium_vxlan`、`cilium_geneve`、IPIP 和 dummy 设备。`MTU: 0`（默认值）表示“自动检测”；非零 Helm `MTU` 是**底层网络 MTU**，不是最终 Pod MTU。CNI 配置中的 MTU 也会覆盖此值。本地检测不能证明路由器之间的路径 MTU。

**Pod 设备 MTU 与路由 MTU。** Pod 的 veth/netkit 设备 MTU 等于基础 MTU；Pod 内路由的 MTU 则是基础值减去封装开销。因此 Pod 中 `ip link` 可能显示 1500，而 `ip route` 显示 `mtu 1450`。

以下开销数据来自 v1.20.2 的 `pkg/mtu/mtu.go`：

| 组件 | 字节数 | 组成 |
|---|---:|---|
| 隧道，IPv4 底层网络 | 50 | 20 IP + 8 UDP + 8 VXLAN + 14 内层 Ethernet |
| 隧道，IPv6 底层网络 | 70 | 40 IP + 8 + 8 + 14 |
| IPsec（128 位 GCM，默认密钥大小） | 77 | 随密钥大小调整 |
| WireGuard | 95 | 固定值 |
| Geneve DSR 选项 | 12 | 在数据路径中应用，不计入路由 MTU |

| 场景（底层 MTU 1500） | Pod 内路由 MTU | 计算 |
|---|---:|---|
| 原生路由，无加密 | 1500 | 基础值 |
| 隧道 VXLAN，IPv4 底层网络 | 1450 | 1500 - 50 |
| 隧道 VXLAN，IPv6 底层网络 | 1430 | 1500 - 70 |
| 原生路由 + WireGuard | 1405 | 1500 - 95 |
| 原生路由 + IPsec | 1423 | 1500 - 77 |
| 隧道 + IPsec | 1373 | 1500 - (50 + 77) |
| 隧道 + WireGuard | 1355 | 1500 - (95 + 50) |

这些数值由常量和 `getRouteMTU` 函数计算得出，并非在集群中实测。巨型帧下绝对开销相同，因此占比会小得多（底层 MTU 为 9001 时，IPv4 上的 VXLAN MTU 为 8951）。

注意事项：

- **Geneve DSR** 会增加 12 字节选项。该选项由负载均衡节点插入，因此大数据包可能超过路径 MTU；TCP hybrid 模式（仅对 TCP SYN 元数据使用 DSR，UDP 使用 SNAT）部分就是为限制此问题而存在。
- **`pmtuDiscovery.enabled`**（默认 false）会向客户端发送 ICMP fragmentation-needed 消息。`pmtuDiscovery.packetizationLayerPMTUDMode`（1.19 新增；取值 `always|blackhole|disabled|unset`；默认 `blackhole`）控制 Pod netns 中的内核 RFC 4821 探测。已知 MTU 时可设为 `disabled`。
- **CNI chaining**：`cni.enableRouteMTUForCNIChaining: true` 会将路由 MTU 推送给链式插件的 Pod（例如 aws-cni 上运行 WireGuard 时需要）。
- **IPv4/IPv6 分片**默认会跟踪（`enable-ipv4-fragment-tracking`、`enable-ipv6-fragment-tracking`；映射表 `bpf-fragments-map-max` 默认 8192；上游标记为 Beta）。参见[L2/L7 网络](05-l2-l7-networking.md)。
- **AWS 上的 XDP** 要求 MTU 足够低，以满足 ENA 原生 XDP（上游示例使用 3498）；巨型帧节点若不降低 MTU 就无法使用 XDP。

在 Pod 中通过 `kubectl exec <pod> -- ip route` 和 `ip link` 检查；使用 `ping -M do -s <size>` 双向测试。

## 9. 伪装

伪装会将离开集群的 Pod 流量源地址改写为节点 IP。Cilium 提供两种实现。

| | iptables（默认） | BPF（`bpf.masquerade: true`） |
|---|---|---|
| 依赖 | iptables/ipset 模块 | KPR（BPF NodePort）、设备检测 |
| 范围 | 经非 Cilium 设备发出的所有流量，除非用 `egressMasqueradeInterfaces` 限制 | 由设备检测或 `devices` 选择的设备；可按 CIDR 排除 |
| 主机路由 | 强制回退到传统主机路由（静默回退） | 与 BPF 主机路由兼容 |
| 协议 | netfilter 支持的全部协议 | TCP、UDP、ICMP（echo、echo-reply、frag-needed）；IPv4 为生产就绪，IPv6 为 Beta |
| 其他 | `enableMasqueradeRouteSource` | ip-masq-agent、`enableRemoteNodeMasquerade` |
| 端口范围 | 内核 | NodePort 最大端口 + 1 到 65535（`bpf/lib/nat.h`）；NAT 表 `bpf.natMax` 默认 524288 |

默认值：`enableIPv4Masquerade: true`，但 `eni.enabled=true` 时默认**为 false**（自 1.18 起）。`enableIPv6Masquerade: true`；**[1.21 预发布版]** ENI IPAM 下默认变为“除 ENI IPAM 外均为 true”。`egressMasqueradeInterfaces` 只影响 iptables 伪装，因此在伪装关闭的 ENI 配置中不起作用。

### BPF 伪装的决策顺序

以下顺序来自 v1.20.2 的 `bpf/lib/nat.h`，每个出口数据包都按此顺序评估：

1. 命中 Egress Gateway 策略：SNAT 为网关 IP。
2. 目标位于 SNAT 排除 CIDR（原生路由 CIDR；未设置时为本地 PodCIDR）：不伪装。
3. 本地端点带有 `SKIP_MASQ` 标记（多池 IPAM）：不伪装。
4. 目标位于 `cilium_ipmasq_v4`（ip-masq-agent 的 LPM 映射）：不伪装。
5. 目标身份是**远端节点**：
   - `enable-remote-node-masquerade=true`：执行 SNAT。
   - 否则使用原生路由：不伪装。
   - 否则使用隧道模式：执行 SNAT，除非 ipcache 条目设置了 `skip_tunnel`。
6. 源是本地端点：SNAT 为出口设备的节点地址；否则原样通过。

由此有两个结果。首先，原生路由下 Pod 到远端节点的流量保留 Pod IP，而隧道模式下会被伪装；这会改变主机防火墙和节点级 `NetworkPolicy`/host policy 看到的源地址。其次，上游伪装页面对第 5 步的表述较宽泛（“发往其他集群节点的数据包”会被排除）；上表以 BPF 代码为准。

`enable-remote-node-masquerade`（1.19 新增）在 1.20.2 中没有专用 Helm 键。需通过 `extraConfig: {enable-remote-node-masquerade: "true"}` 设置。它要求启用 BPF 伪装，并会削弱主机防火墙的入口执法能力，因为源地址会变成节点地址。

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

chart 会在 release namespace 中渲染名为 `ip-masq-agent` 的 ConfigMap，其中 `config` 键保存 JSON；agent 通过 fsnotify 监视挂载文件。空配置表示使用内置的非伪装 CIDR：10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、100.64.0.0/10、192.0.0.0/24、192.0.2.0/24、192.88.99.0/24、198.18.0.0/15、198.51.100.0/24、203.0.113.0/24、240.0.0.0/4；除非启用 `masqLinkLocal`，还包括 169.254.0.0/16；除非启用 `masqLinkLocalIPv6`，还包括 fe80::/10。`cilium_ipmasq_v4/v6` 映射各有 16384 个条目。启用 ip-masq-agent 后，不再强制要求设置原生路由 CIDR。

可通过 `cilium-dbg status | grep Masquerading` 检查（例如 `BPF (ip-masq-agent) [eth0] <cidr> [IPv4: Enabled, IPv6: Disabled]`），也可运行 `cilium-dbg bpf ipmasq list`。

已知限制：BPF 伪装不会伪装 Pod 到节点 External IP 的流量（上游 issue 17177）。**[1.21 预发布版]** `nodePort.extendedNATPortRange`（`--node-port-nat-range-ext`）可扩展大型 NAT 表的 SNAT 端口范围。

启动时强制执行的不兼容项：设备选择（类似 `--masquerade-interfaces`）和 `enable-masquerade-to-route-source` 不能与 BPF 伪装同时使用。

## 10. 主机路由：传统模式与 BPF 模式

| | 传统主机路由 | BPF 主机路由 |
|---|---|---|
| 标志 | `bpf.hostLegacyRouting: true` | 满足前置条件时默认启用 |
| 路径 | Pod -> veth -> 主机 netfilter/路由 -> NIC | Pod -> BPF FIB 查找 -> NIC；通过 `redirect_peer` 进入 Pod netns |
| netfilter/iptables | 位于路径中 | 绕过 |
| 依赖 | 无特殊要求 | KPR 为 true 且启用 BPF 伪装（否则会静默回退） |
| 依赖该模式的功能 | 不适用 | netkit、Pod BBR、BIG TCP、通过 FIB 表注解进行动态出口路由 |

BPF 主机路由会跳过 netfilter 和上层协议栈，因此依赖主机 namespace 中 netfilter 的功能会失效。已知不兼容项包括 Istio sidecar 重定向（上游 issue 36022）和依赖 netfilter 的云服务商功能，例如 GKE Workload Identity。解决方法是设置 `bpf.hostLegacyRouting: true` 或使用 Local Redirect Policy。1.19 及之后版本中，启用 KPR 和 BPF 伪装时，IPsec 会自动启用主机路由；内核必须包含 CVE-2025-37959 的修复。

传统模式下，可通过 `installNoConntrackIptablesRules: true` 降低 conntrack 开销（原生路由、IPv4、搭配 socket-LB 的 KPR、BPF 伪装）。对于 eni、azure、gke 和 CNI chaining，chart 会强制关闭此设置。

在 `cilium-dbg status` 的 `Routing:` 行检查 `Host:` 字段（`Host: BPF` 或 `Host: Legacy`）。Cilium 1.20.2 不会单独打印“Host Routing”行。

## 11. 数据路径设备：veth 与 netkit

`bpf.datapathMode` 接受 `veth`（默认）、`netkit`、`netkit-l2`，以及 1.20 新增的 `auto`。

- `netkit`（L3 模式、不使用 ARP、上游推荐的变体）和 `netkit-l2` 会在对端内部挂载 BPF 并使用 tcx；支持 BIG TCP。1.20.2 文档将其标为**Beta**；文档要求内核 6.8+（`CONFIG_NETKIT`），但代码注释写的是 6.7+。应以文档版本作为最低要求，并以运行时探测结果为准。
- 前置条件（`canUseNetkit`）：netkit 探测通过、未设置 `bpf.hostLegacyRouting`、启用 BPF 伪装（而非 iptables）、`kubeProxyReplacement: true`、未启用 `bpf.tproxy`（自 1.19 起不兼容）；若启用 `enableEndpointRoutes`，驱动还必须支持 scrub 属性（内核 6.13 或有相应回移补丁的内核）。
- 显式设置 `netkit`/`netkit-l2` 却未满足前置条件时会**硬失败**；`auto` 则会发出警告并降级为 veth，`cilium-dbg status` 会显示类似“Device Mode: netkit [Configured: auto]”的输出，以区分配置模式与实际运行模式。
- 如果节点上已有使用 veth 的 Pod，切换模式（包括使用 `auto`）会报错。应使用逐节点配置（`CiliumNodeConfig`）或先排空节点。

```yaml
# values: safe netkit probe
bpf:
  datapathMode: auto
  masquerade: true
kubeProxyReplacement: true
routingMode: native
```

运行 `cilium-dbg status | grep -E "Device Mode|Routing|Attach Mode"` 验证（主机路由会在 `Routing:` 行显示 `Host: BPF|Legacy`）。上游指出，当新内核普及后 veth 可能会弃用，默认值也可能改变；不要假设默认值永久不变。

## 12. 数据路径中的 Service 负载均衡

以下内容说明各项 Service 功能相对于第 5 节 Pod 到 Pod 数据包路径的位置：

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

**kube-proxy 替换（KPR）。** 这是一个布尔值：`kubeProxyReplacement: true|false`（strict/partial 已移除）。设为 `true` 会强制启用 socket-LB。由于没有 kube-proxy 解析 API ClusterIP，应设置 `k8sServiceHost`/`k8sServicePort`。KPR 涵盖 ClusterIP、NodePort、LoadBalancer、externalIPs 和 hostPort，可用于隧道模式和原生模式。即使 KPR=false，ClusterIP 仍会逐包执行负载均衡。1.19 移除了 `--enable-node-port`、`--enable-host-port`、`--enable-external-ips`；1.20 移除了 `--node-port-mode`、`--node-port-algorithm`（改用 `loadBalancer.mode`/`loadBalancer.algorithm`）。

**Socket-LB。** `socketLB.enabled`（启用 KPR 时开启）会挂钩 `connect`/`sendmsg`/`recvmsg`/`getpeername`。`socketLB.hostNamespaceOnly: true` 会限制其作用范围为主机 namespace；Istio sidecar、KubeVirt、Kata 和 gVisor 需要此设置（启用 `gatewayAPI.enabled` 时会强制设置）。`socketLB.terminatePodConnections`（默认 true）要求内核启用 `CONFIG_INET_DIAG*`。**1.20 行为变化**：关闭 socket-LB 或设置 `hostNamespaceOnly=true` 时，Pod 到 NodePort 的连接会在客户端 Pod 出口处执行 DNAT，因此出口 NetworkPolicy 必须允许访问后端，而不只是允许 NodePort。

**算法。** `loadBalancer.algorithm: random|maglev`。Maglev 会在 map-in-map `cilium_lb4_maglev`/`cilium_lb6_maglev` 中为每个 Service 构建查找表，并对五元组取哈希（启用 ClientIP 亲和性时源端口会置零），再对表大小取模。它只适用于南北向流量；通过 socket-LB 的东西向流量会绕过它。`maglev.tableSize` 必须为 251、509、1021、2039、4093、8191、16381、32749、65521 或 131071 之一（默认 16381，约可为每个 Service 配置 160 个后端）；所有 agent 的 `maglev.hashSeed` 必须相同。

```bash
SEED=$(head -c12 /dev/urandom | base64 -w0)   # generate once, store it in your values/secret store
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set kubeProxyReplacement=true \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set maglev.hashSeed=$SEED
```

每 Service 覆盖：设置 `bpf.lbAlgorithmAnnotation=true`，并添加注解 `service.cilium.io/lb-algorithm: maglev`（仅在创建时生效）。1.20 新增 EndpointSlice 注解 `service.cilium.io/weight`（0–65535，仅 Maglev 使用；0 表示维护状态）。

**转发模式。** `loadBalancer.mode: snat|dsr|hybrid`。

- `snat`：接收请求的节点改写源地址，因此响应会经由该节点返回。
- `dsr`：后端直接向客户端响应；Service IP/端口会传给后端。`hybrid` 对 TCP 使用 DSR（仅在 SYN 中编码 Service 地址），对 UDP 使用 SNAT。
- Dispatch（`loadBalancer.dsrDispatch`，默认 `opt`）：用于携带信息的方式。

| `dsrDispatch` | 原生路由 | 隧道（Geneve） | 隧道（VXLAN） |
|---|---|---|---|
| `opt`（IP option / IPv6 destination option） | 支持 | 不支持 | 不支持 |
| `geneve` | 支持（会创建 Geneve 设备） | 支持 | 不支持（VXLAN 不支持 DSR） |
| `ipip`（1.20 文档所述） | 支持 | 不支持 | 仅注解模式下有校验器例外；不是文档认可的可用配置 |

IPIP 会创建 `cilium_ipip4/6`，要求 Service 端口与目标端口相同，可选配置 RSS 源 CIDR（`--bpf-lb-rss-ipv4-src-cidr`），并且不兼容 BIG TCP。云网络可能丢弃携带 IP options（`opt`）的数据包；此时优先使用 `geneve` 或 `ipip`。AWS 上使用 DSR 时必须关闭 EC2 源/目标检查。因此隧道模式下的 DSR 要求设置 `tunnelProtocol: geneve` 和 `dsrDispatch: geneve`。

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

注解模式：`bpf.lbModeAnnotation=true` 会允许通过 `service.cilium.io/forwarding-mode: dsr|snat` 为每个 Service 单独配置转发模式，并要求显式设置 `loadBalancer.dsrDispatch`。在 EKS 上添加该注解的 LoadBalancer Service 必须保持为内部 Service（`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`）；如需对外发布，只能经由 CloudFront 和 VPC origin。

**XDP 加速。** `loadBalancer.acceleration: disabled|native|best-effort`。所有选定设备都需要原生 XDP 驱动（否则使用 `best-effort`）；只有直连路由设备会加速；它与 IPv6 底层网络不兼容，并会自动启用 L2 neighbor discovery。被 XDP 弹回的数据包不会显示在 `tcpdump` 中。由 XDP 加速的南北向流量或使用非 Geneve DSR 的流量不会由 WireGuard 加密。

**值得了解的已知问题**：反向 socket 映射耗尽、socket-LB 所需的 NFS/SMB 内核补丁、后端终止竞态（添加 `preStop` 延迟），TCP Fast Open 导致 DSR 故障，以及多设备 DSR 的 rp_filter 警告。比较表参见[L2/L7 网络](05-l2-l7-networking.md)。

## 13. 带宽管理器、BBR 与 BIG TCP

**带宽管理器。** `bandwidthManager.enabled`（默认 false）、`bandwidthManager.bbr`、`bandwidthManager.bbrHostNamespaceOnly`。注解 `kubernetes.io/egress-bandwidth`（使用 FQ 的 EDT，在 Pod 主机侧设备和隧道设备出口处各应用一次）和 `kubernetes.io/ingress-bandwidth`（BPF token bucket）。值使用 Kubernetes 的**位**单位：`"10M"` 表示 10 Mbit/s，而不是 10 MB/s。限速针对单个 Pod，不针对副本集。

副作用：设置主机 sysctl `net.core.default_qdisc=fq` 和 `net.ipv4.tcp_congestion_control`（`cubic` 或 `bbr`），提高 `netdev_max_backlog`（至少 1000）、`somaxconn` 和 `tcp_max_syn_backlog`（至少 4096）的基线，并在外部设备上安装 FQ。前置条件：BBR 要求内核 5.18；Pod 使用 BBR 要求启用 BPF 主机路由（否则报错，除非设置 `bbrHostNamespaceOnly`）；使用 IPsec 时管理器会静默禁用。已有 Pod 保留旧的拥塞控制算法；BBR 只应用于新 Pod。

运行 `cilium-dbg status | grep BandwidthManager` 验证（例如 `EDT with BPF [BBR] [eth0]`），并运行 `cilium-dbg bpf bandwidth list`。

**BIG TCP。** `enableIPv4BIGTCP`、`enableIPv6BIGTCP`（默认均为 false）。内核要求：IPv6 5.19+、IPv4 6.3+；上游列出的 NIC 驱动包括 mlx4、mlx5 和 ice。要求启用 BPF 主机路由、KPR 和 BPF 伪装；与 IPsec 和 DSR IPIP 不兼容。它会将 GSO/GRO 最大尺寸提高至 192 KB，但不改变 MTU；切换后需重启 Pod。上游文档称“隧道模式下禁用”，但代码允许在 VXLAN/Geneve 上使用 BIG TCP，前提是内核探测确认支持 UDP 隧道 BIG TCP；否则会报错“BIG TCP in tunneling mode requires pending kernel support”。实际建议是使用原生路由。

**上游推荐的性能配置**（不要原地升级；使用逐节点配置）：

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

如需启用带宽管理器，可增加 `bandwidthManager.enabled=true` 和 `bandwidthManager.bbr=true`。注意与第 7 节的关系：此配置中的 netkit 和 BIG TCP 都要求 BPF 主机路由，因此只有启用 KPR 和 BPF 伪装时才能使用。

## 14. 加密之间的相互影响

此处只介绍对数据路径的影响；密钥管理参见[第 12 章](12-mtls-encryption-identity.md)。

| | WireGuard | IPsec |
|---|---|---|
| 传输 | UDP 51871 | ESP（IP 协议 50） |
| 隧道模式下 | 双重封装：先 VXLAN/Geneve，再 WireGuard | 在 overlay 封装**之后**进行加密（自 1.18 起一直如此） |
| 路由 MTU @1500 | 隧道 1355，原生路由 1405 | 隧道 1373，原生路由 1423 |
| Strict mode | `encryption.strictMode.ingress.enabled`（1.19+）要求使用 WireGuard（不能用 IPsec），且支持隧道和原生路由；`strictMode.egress.allowRemoteNodeIdentities` 是出口选项，在隧道模式下或直接路由中节点与 Pod CIDR 重叠时必需；`strictMode.egress.*` 替代已于 1.20 移除的旧键 | 不适用 |
| 带宽管理器 | 可用 | 静默禁用 |
| BIG TCP | 有限制地支持 | 启动时报错 |
| CNI chaining | 不支持加密 | 不支持加密 |

其他事实：IPsec `encryptedOverlay` 从 1.18 起无实际作用，并在 1.20 移除。任何直接路由配置都要求 IPsec 设置 `ipv4NativeRoutingCIDR`；最多支持少于 65535 个节点，并且每条隧道只在单个 CPU 核上解密。WireGuard 不覆盖经 XDP 加速的南北向流量，也不覆盖 Geneve 以外的 DSR；Geneve DSR 受支持。

抓包时请记住顺序：NIC 上看到的是 UDP 51871 或 ESP，而不是 VXLAN/Geneve；Pod 主机侧设备上看到的是明文。下结论说加密或封装缺失之前，应在这两个位置都抓包。

## 15. VTEP 与多播（Beta）

**VTEP 集成**让 Pod 可以与外部 VXLAN 端点（例如硬件 VTEP）交换流量。

- Helm：`vtep.enabled`、`vtep.endpoint`、`vtep.cidr`、`vtep.mask`、`vtep.mac`；`vtep.endpoint`、`vtep.cidr` 和 `vtep.mac` 是以空格分隔且长度相同的列表（每个 VTEP 一个条目）；`vtep.mask` 是应用于所有 CIDR 的单个掩码。
- 限制：最多 8 个 VTEP；仅 IPv4；同步间隔 `--vtep-sync-interval`（1m）；不能与 IPsec 同用；VTEP 设备 MTU 硬编码为 1500 - 50。
- VTEP 设备必须使用 **VNI 2**（`world`）。如果 VTEP 源地址发出的 overlay 数据包携带的身份不是 world，BPF 会丢弃这些数据包（`DROP_INVALID_VNI`）。出口时 `bpf_lxc` 会查找 `cilium_vtep_map`，并以目标身份 `world` 进行封装。
- 使用 `cilium-dbg bpf vtep list` 检查。Geneve 是否支持 VTEP 尚无文档说明，也未经验证；文档中的配置使用 VXLAN 隧道模式。

**多播。**

- 使用 `cilium config set multicast-enabled true` 或 `extraConfig: {multicast-enabled: "true"}` 启用；1.20.2 中没有专用 Helm 值。
- 文档要求使用 VXLAN 模式；amd64 内核 5.10+ 或 arm64 内核 6.0+。代码还会探测 `bpf_for_each_map_elem` helper（Linux 5.13+）；若缺少该 helper，agent 会记录“Disabled support for BPF Multicast”并保持禁用。5.10–5.12 上实际以哪个规则为准尚未核实。
- 仅支持 IPv4；`bpf_lxc` 处理 IGMP v2/v3；上限为 1024 个组、每组 1024 个订阅者；不能与 IPsec 同用；且必须在每个节点上配置（运行 `cilium-dbg bpf multicast group add <group>` 和 `... subscriber add <group> <remote CiliumInternalIP>`，或按上游 `multicast.rst` 所示使用 `cilium multicast add --group-ip` 在集群范围添加；该 CLI 命令未对照 cilium-cli 源码核实）。

## 16. EKS 选型指南

| 方案 | 配置 | 适用情况 | 注意事项 |
|---|---|---|---|
| **Cilium ENI IPAM**（替代 VPC CNI） | `eni.enabled=true`、`ipam.mode=eni`、`routingMode: native`（启用 ENI 时默认），通过 IRSA/Pod Identity 提供 operator 权限，添加污点 `node.cilium.io/agent-not-ready=true:NoExecute` | Pod 需要可由 VPC 路由的 IP、VPC 内无需 SNAT、按 Pod IP 使用安全组/流日志 | ENI 模式禁止隧道；IPv4 伪装默认关闭（1.18+）；Pod 密度受 ENI/IP 容量限制；operator 需要 `ec2:DescribeRouteTables`；AWS 支持仅覆盖 EC2 节点上的 VPC CNI |
| **EKS 上的 Overlay** | `ipam.mode=cluster-pool`、`routingMode: tunnel`、`eni.enabled=false` | VPC 中 Pod IP 地址空间不足，或需要隧道功能 | Pod IP 无法由 VPC 路由，因此托管控制平面无法访问这些 IP：**webhook 后端（admission、conversion）必须使用 `hostNetwork`**。节点安全组需自引用，开放 UDP 8472（或 6081）。MTU 为 1450（底层 MTU 为 9001 时为 8951） |
| **VPC CNI chaining** | `cni.chainingMode=aws-cni`、`cni.exclusive=false`、`enableIPv4Masquerade=false`、`routingMode=native` | 保留 VPC CNI IPAM 和 ENI，同时添加 Cilium policy、LB 和 Hubble | chart 强制使用传统主机路由并禁用无 conntrack 的 iptables 规则；不支持 IPsec/WireGuard；L7 能力有限；aws-node 版本需为 1.11.2 或更高；启用后需重启 Pod |
| **EKS Auto Mode / Fargate** | 不适用 | 不适用 | 不支持替代 CNI |
| **EKS Hybrid Nodes** | Cilium 是受支持的 CNI | 本地部署节点 | webhook 使用的 Pod CIDR 必须可路由；参见本仓库的 EKS Hybrid Nodes 章节 |

关于 overlay webhook 的说明，依据 AWS 对 Hybrid Nodes 的指南（webhook 的 Pod CIDR 必须可路由）以及 Kubernetes 控制平面对 webhook 的调用方式推导而来；依赖此结论前请先完成实验 5 验证。

Cilium ENI 配置（有意省略无效的 `egressMasqueradeInterfaces` 键：伪装关闭时它不起作用）：

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

EKS 注意事项：

- 将 Cilium 作为 CNI 安装前应删除 `aws-node` DaemonSet（aws-node 会清空路由表），否则需在之后重启 Pod。
- 次要 VPC CIDR（例如 100.64.0.0/16）：自动检测到的原生路由 CIDR 仅包含**主** VPC CIDR。如果启用了伪装，且 Pod 使用次要地址范围，则应将 `ipv4NativeRoutingCIDR` 设为覆盖该范围的 CIDR，并检查 `cilium-dbg status | grep Masquerading`。这是根据代码推导，未经测试。
- ENI IPv6：`eni.rst` 记录每节点一个 /80 前缀和双栈子网，而 EKS 要求页面仍写为仅支持 IPv4。上游对 ENI IPv6 的说明尚不明确，请在所在区域确认。
- 源/目标检查：文档要求 DSR 必须关闭此检查。对于非 ENI EC2 实例上的原生路由，原则上也有相同限制（Pod IP 不属于实例）；后半部分是推断。
- 公网访问路径策略：只有 CloudFront 可以通过 CloudFront VPC origin 后方的内部 ALB/NLB 访问工作负载。本章的 Cilium 示例不需要公网 listener 或 `0.0.0.0/0` 规则。

## 17. 检查速查表

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

`cilium-dbg status` 会输出类似 `Network: Tunnel [vxlan]  Host: BPF` 的 `Routing:` 行。不同版本显示映射内容的命令可能采用不同列布局；不要依赖列的位置编写脚本。

## 18. 实验

仅在可随时销毁的集群上运行（kind，或使用安全组自引用规则的双节点 EKS 测试集群）。本章所有内容都依据上游源码和文档核对过，但本次审查没有在实时集群中执行任何实验。文中描述的是预期结果，并非实际捕获的结果。

### 实验 1：Overlay 结构与 VNI

**前置条件**：两个可调度的 Linux 节点；Cilium 1.20.2，设置 `routingMode: tunnel`；可登录节点的 shell；节点间允许 UDP 8472。

1. 在 agent 上运行 `cilium-dbg status | grep Routing`：预期网络模式为隧道，协议为 vxlan。
2. 在节点上运行 `ip -d link show cilium_vxlan`：预期是 flow-based（external 属性）的 vxlan 设备，目标端口为 8472。
3. 在节点 1 上启动 server Pod，在节点 2 上启动 client Pod（使用 nodeName 或反亲和性）。client curl server 时，在节点上运行 `sudo tcpdump -nni <nic> -vv 'udp port 8472' -c 20`。
4. 记录解码结果中的 `vni`，并与节点 2 上 `cilium-dbg endpoint list` 显示的 client Pod 身份比较。预期 client 到 server 的数据包使用 client 身份，响应则使用 server 身份。
5. 运行 `helm upgrade ... --set tunnelProtocol=geneve`，重启 agents；观察到 `cilium_vxlan` 消失、`cilium_geneve` 出现，且抓包过滤器需改为端口 6081。

**清理/回滚**：将 `tunnelProtocol` 设回 `vxlan` 并重启 agents。更改协议会重建设备，期间节点间连接预计会短暂中断。

### 实验 2：隧道上的 WireGuard 与 MTU

**前置条件**：实验 1 使用的集群；节点间允许 UDP 51871（安全组自引用）。

1. 启用 `encryption.enabled=true`、`encryption.type=wireguard`；保持 `MTU: 0`。
2. 在 Pod 中运行 `ip route` 和 `ip link`。预期设备 MTU 等于底层网络 MTU；底层 MTU 为 1500 时，路由 MTU 为 1355（95 + 50 字节开销）。
3. 在某个 Pod 中运行 `ping -M do -s 1327 <other pod ip>` 和 `-s 1328`。预期前者成功（1327 + 28 = 1355），后者因需要分片而失败。
4. `cilium-dbg status | grep Encryption` 应报告 WireGuard。

**清理**：关闭加密并重启 agents；新 Pod 的路由 MTU 应恢复为 1450（已有 Pod 在重建前会保留其 MTU）。

### 实验 3：伪装决策树

**前置条件**：启用 KPR 和 `bpf.masquerade=true`；在同一 VPC 中运行测试 echo server，记录收到的源 IP；该 server 只能通过引用节点安全组的安全组规则访问。

1. 从 Pod 访问 echo server，检查对端观察到的源地址：如果 server IP 位于原生路由 CIDR 和 ip-masq-agent 列表之外，源地址应是节点 IP。
2. 启用 `ipMasqAgent`，将 server 的地址范围加入 `nonMasqueradeCIDRs`，重启 agents 后重试。预期保留 Pod IP（VPC 必须能够将返回流量路由到 Pod IP；overlay 中的 Pod IP 无法做到，因此会访问失败，这正是要验证的现象）。
3. `cilium-dbg bpf ipmasq list` 会列出 CIDR；`cilium-dbg bpf nat list` 会显示活动的 SNAT 条目。
4. Pod 到远端节点的流量：原生模式下源地址仍为 Pod IP，隧道模式下则为节点 IP。设置 `extraConfig: {enable-remote-node-masquerade: "true"}`，观察原生模式现在也会伪装。

**清理/回滚**：移除 ip-masq-agent 配置段和 extraConfig 键。更改伪装模式会改变防火墙看到的源地址；应逐节点操作。

### 实验 4：无 kube-proxy 的 Service、Maglev 与 Geneve DSR

**前置条件**：安装时未启用 kube-proxy；`routingMode: tunnel`、`tunnelProtocol: geneve`、KPR 为 true、`loadBalancer.mode: dsr`、`dsrDispatch: geneve`、`maglev` 设置参见第 12 节；VPC 内的客户端主机；一个后端位于不同节点上的 NodePort Service。仅使用内部网络路径。

1. 在接收请求的节点上运行 `iptables-save | grep KUBE-SVC`，预期没有结果。
2. `cilium-dbg bpf lb list` 显示 Service；`cilium-dbg bpf lb maglev list` 显示查找表。
3. 在后端节点 NIC 上使用 tcpdump 抓包：请求应以 Geneve（UDP 6081）到达，并携带 DSR 选项；响应应直接发往客户端，源地址为 Service IP。
4. 在一次性集群中设置 `tunnelProtocol: vxlan` 和 `loadBalancer.mode: dsr`，验证 agent 会在启动时失败，然后还原配置。

**清理**：还原 Helm 值。在运行中的集群切换模式会中断 DSR 流量。

### 实验 5：netkit/auto、主机路由与 EKS ENI

**前置条件：**(a) 一个内核版本 6.8 或更高的节点和一个较旧节点；(b) ENI 部分需使用一个未安装 `aws-node` 的一次性 EKS 集群。

1. 设置 `bpf.datapathMode=auto`、`bpf.masquerade=true`、`kubeProxyReplacement=true`，比较新旧内核上的 `cilium-dbg status | grep -E "Device Mode|Routing"`。预期新内核的 `Device Mode` 显示 netkit，旧内核显示 veth 并记录回退日志；两者的 `Routing:` 行都显示 `Host: BPF`。不要在已有 veth Pod 的节点上直接切换；先排空节点。
2. 设置 `bpf.masquerade=false`：`Routing:` 行应以 `Host: Legacy` 结尾，agent 日志也应显示已回退。之后还原。
3. 为已启用带宽管理器的 Pod 添加 `kubernetes.io/egress-bandwidth: "10M"`，并确认 `cilium-dbg bpf bandwidth list` 列出该 Pod。
4. ENI：按照第 16 节的 ENI 配置安装。对每个 Pod IP，`ip rule` 应显示入口规则 `to <podIP> lookup main`（优先级 20）和出口规则 `from <podIP> lookup <ENI table>`（优先级 111），并且存在每 ENI 路由表；由于 ENI 默认关闭伪装，出口规则不包含 `to <VPC CIDR>`，除非启用伪装。在临时集群中尝试启用 ENI 和 `routingMode: tunnel`：预期 agent 拒绝启动。
5. EKS 上的 Overlay：在 overlay 集群部署一个后端为普通 Pod 的 validating webhook，观察 API server 是否可访问；然后将后端改为 `hostNetwork`。

**清理**：删除测试工作负载，还原 Helm 值并终止临时集群。本章不涉及在已有工作负载的集群中替换 CNI，也不支持这种原地迁移。

## 19. 版本差异

| 主题 | 1.18 | 1.19 | 1.20 | 1.21-pre.3 |
|---|---|---|---|---|
| 内核最低版本 | 5.10（RHEL 8.10 为 4.18） | 相同 | 相同 | 相同 |
| `cilium_tunnel_map` | 从数据路径移除（agent 取消固定遗留映射）；CLI 命令消失 | Go 包**移除**；隧道端点位于 ipcache 值中 | 不适用 | 不适用 |
| `underlayProtocol`（IPv6 底层网络） | **新增** | 稳定 | 相同 | IPv6 开销计算使用隧道标志 |
| ENI 下的 `enableIPv4Masquerade` | 默认**为 false** | 相同 | 相同 | 相同；IPv6 伪装默认值改为除 ENI 外均启用 |
| `bpf.datapathMode` | veth、netkit、netkit-l2 | netkit 与 tproxy 不兼容 | 新增 **`auto`**；status 显示配置模式和运行模式 | 相同 |
| BPF 主机路由 + IPsec | 不适用 | IPsec + KPR + BPF 伪装时自动启用（要求包含 CVE-2025-37959 修复） | 相同 | 相同 |
| `enable-remote-node-masquerade` | 不适用 | **新增** | 相同 | 相同 |
| `packetizationLayerPMTUDMode` | 不适用 | **新增**，默认 `blackhole` | 相同 | 相同 |
| WireGuard strict mode | 旧键 | 新增 `strictMode.ingress` | 移除旧的 `strictMode.enabled/cidr` 键 | 相同 |
| IPsec `encryptedOverlay` | 无操作 | 弃用 | **移除** | 不适用 |
| DSR dispatch | 有 `opt`/`ipip`/`geneve` 标志，但 IPIP 未记录文档 | 相同 | 记录 IPIP；新增每 Service 的 DSR/algorithm 注解、`bpf-lb-rss-*`、`service.cilium.io/weight` | 相同 |
| 已移除标志 | 不适用 | `--enable-node-port/host-port/external-ips` | `--node-port-mode`、`--node-port-algorithm` | 不适用 |
| socket-LB 与 Pod 到 NodePort | 不适用 | 跟踪格式变化 | 关闭 socketLB 或设 `hostNamespaceOnly` 时在客户端出口 DNAT | 相同 |
| `nativeRoutingCIDRFromClusterPool`、`nodePort.enableDynamicSourceLookup` | 不适用 | 不适用 | **新增** | 相同 |
| `nodePort.extendedNATPortRange` | 不适用 | 不适用 | 不适用 | **[1.21 预发布版] 新增** |
| `l2NeighDiscovery.enabled` 默认值 | false（原来为 true） | 相同 | 相同 | 相同 |
| autoDirectNodeRoutes + 隧道的错误信息 | “cannot be used with tunneling” | 相同 | 相同 | “requires native routing mode” |

成熟度：稳定功能包括隧道、原生路由、BPF 伪装（IPv4）、KPR、Maglev、DSR、XDP 加速、带宽管理器、BBR 和 BIG TCP。Beta 功能包括 netkit、IPv6 BPF 伪装、VTEP、多播和分片跟踪。已移除：`cilium_tunnel_map`、`encryptedOverlay`、`--node-port-mode`。

## 20. 故障排查

| 症状 | 可能原因 | 检查/修复 |
|---|---|---|
| Agent 启动时退出并提示“cannot be used with tunneling” | 隧道模式下启用了 `autoDirectNodeRoutes` | 使用原生路由，或移除此标志 |
| Agent 退出并提示“Cannot specify IPAM mode eni in tunnel mode” | ENI IPAM 与隧道模式组合 | 设置 `routingMode: native` |
| 跨节点 Pod 流量失败，但同节点正常 | UDP 8472/6081 被阻止、隧道端口错误或节点 SG 缺少自引用规则 | 在两节点上运行 `tcpdump -nni <nic> 'udp port 8472'`；检查 SG/NACL；确认 `Routing:` 行 |
| 大传输卡住，小请求正常 | MTU 黑洞（隧道开销、ICMP 被过滤） | 比较 Pod 的 `ip route` MTU 与路径 MTU；运行 `ping -M do -s`；检查 `pmtuDiscovery` 设置 |
| 原生 Pod 可访问外部，但源地址是 Pod IP 且响应无法返回 | 伪装关闭（ENI 默认值），或目标位于原生路由 CIDR 内 | `cilium-dbg status \| grep Masquerading`；按需启用伪装或 ip-masq-agent |
| 不同集群中 Pod 到远端节点使用的源 IP 不同 | 隧道模式会伪装，原生模式不会（第 9 节） | 明确选择所需行为；需要统一时启用 `enable-remote-node-masquerade` |
| Agent 日志显示“Falling back to legacy host routing” | 使用 iptables 伪装或关闭 KPR | 启用 `bpf.masquerade` 和 KPR，或接受传统路由 |
| Istio sidecar 流量绕过策略或异常 | BPF 主机路由/socket-LB 在 Pod namespace 中生效 | 设置 `socketLB.hostNamespaceOnly=true` 或 `bpf.hostLegacyRouting=true` |
| `bpf.datapathMode=netkit` 失败 | 缺少所需内核、使用传统路由、iptables 伪装、KPR 关闭或启用了 tproxy | 使用 `auto` 探测，或满足前置条件 |
| Agent 拒绝 DSR | 使用 VXLAN 隧道或未设置 Geneve dispatch | 设置 `tunnelProtocol: geneve` 和 `dsrDispatch: geneve` |
| 节点变更后 Service 流量偶发重置 | Agents 的 Maglev seed 不一致 | 确保所有位置的 `maglev.hashSeed` 完全相同 |
| `tcpdump` 看不到 NodePort 流量 | 启用了 XDP 加速 | 在其他位置抓包，或为排查临时关闭加速 |
| EKS overlay 上 webhook 超时 | API server 无法访问非 VPC Pod IP | 将 webhook 后端设为 `hostNetwork` |
| NIC 上没有加密数据包 | 带宽管理器与 IPsec/WireGuard 组合，或流量经过 XDP/非 Geneve DSR 路径 | 检查 `cilium-dbg status \| grep Encryption` 和第 14 节的加密表 |

通用排查流程：(1) 运行 `cilium-dbg status --verbose` 查看实际生效配置；(2) 运行 `cilium-dbg monitor --type drop` 查看丢弃原因（查找 `DROP_INVALID_IDENTITY`、`DROP_INVALID_VNI`）；(3) 在 `cilium-dbg bpf ipcache list` 中确认目标条目及其隧道端点正确；(4) 在两个节点的 NIC 以及 `cilium_vxlan`/`cilium_geneve` 上抓包；(5) 检查 agent 启动日志中的回退信息。

## 21. 验证限制与来源

本章实验均未在实时集群中执行。本章中的实验和行为说明都依据以下版本标签的上游源码和文档核对过。部分内容是推断，且已在文中标注：EKS overlay webhook 可达性、非 ENI EC2 实例原生路由时的 EC2 源/目标检查、次要 VPC CIDR 下的原生路由行为、Geneve 上的 VTEP，以及内核 5.10 至 5.13 之间的多播最低版本（未经核实）。1.21 预发布版中已有框架代码但未正式说明的另一种路由模式，本章有意不作描述。

计算值（MTU 表）由源码常量推算，并非实测数据。

来源（除非特别注明，均为 v1.20.2）：

- [路由](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst)、[伪装](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst)、[调优](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst)、[系统要求](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [kube-proxy 替换](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst)、[带宽管理器](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst)、[VTEP](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/vtep.rst)、[多播](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst)、[ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)、[AWS CNI chaining](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/cni-chaining-aws-cni.rst)
- [隧道/overlay BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_overlay.c)、[lxc BPF](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_lxc.c)、[身份辅助函数](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/identity.h)、[NAT](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/nat.h)、[隧道选项](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/tunnel.h)、[MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go)、[启动校验](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go)、[KPR 校验](https://github.com/cilium/cilium/blob/v1.20.2/pkg/kpr/initializer/kube_proxy_replacement.go)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- 预发布版：[v1.21.0-pre.3 的 daemon_main.go](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/daemon/cmd/daemon_main.go)、[v1.21.0-pre.3 的 values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- AWS：[EKS 替代 CNI 插件](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)

## 测验

[检查你对 Overlay 和原生路由的理解](../../quizzes/networking/cilium/09-overlay-native-routing-quiz.md)。

[返回主页](README.md)
