# 第 8 部分：eBPF 数据路径内部机制

> **审查基线**：Cilium 1.20.2（稳定版，2026-09-16）；Cilium CLI 0.20.1；Hubble CLI 1.20.2。标记为 **[1.21 预发布版]** 的内容来自 v1.21.0-pre.3，在 GA 前仍可能变化。
> **最后更新**：2026 年 10 月 15 日

本章介绍 Cilium 数据路径：哪些 BPF 程序会运行、挂载位置、程序之间的调用关系、读取哪些 map、agent 如何编译和加载程序，以及单个数据包逐跳经过的处理过程。通用 eBPF 入门（历史、verifier、map 类型）仍在[第 2 部分：eBPF](02-ebpf.md)。Overlay 和路由行为见[第 9 部分](09-overlay-native-routing.md)；IPAM 见[第 10 部分](10-ipam-deep-dive.md)。

> **过时博客警告：`cilium_tunnel_map` 已不存在。旧文章和部分上游示例清单仍会显示** `cilium_tunnel_map`，它曾用于把 Pod CIDR 映射到远程节点 IP。Cilium 1.17 的 BPF 代码中仍有此 map（`bpf/lib/encap.h`），而且 `cilium-dbg bpf tunnel list` 可以导出它。它在 1.18 从数据路径中移除（1.18.14 的 BPF 树中已无引用；agent 只会解除遗留 map 的 pin），其 Go 包则在 1.19 移除。Cilium 1.20.2 中没有任何 BPF 程序引用它。远程节点（隧道端点）现在存储在 `cilium_ipcache_v2` 的**值**中（字段 `tunnel_endpoint`，标志 `flag_has_tunnel_ep`）。1.18 和 1.20 均没有 `cilium-dbg bpf tunnel list` 命令。如果指南让你用 `bpftool map dump` 导出 tunnel map 来排查 Overlay 路由，应改为导出 ipcache（`cilium-dbg bpf ipcache list`）。某篇上游开发文档仍在示例输出中列出此 map，并不意味着它仍在使用。

## 学习目标

- 说出各个 Cilium BPF 对象、其入口程序，以及各程序挂载的设备或 cgroup hook。
- 解释 Cilium 使用 tail call 的原因，以及发送端程序如何执行目标端点的策略。
- 读取策略、ipcache、conntrack 和 service map 的键值布局，并使用正确标志设置其大小。
- 描述 agent 侧的流程：ELF 模板缓存、`.rodata.config` 常量、map pinning、挂载和提交。
- 跟踪 Pod → ClusterIP → Pod 连接，并列出每一跳的 map 查询。
- 使用 `cilium-dbg bpf ...` 和 `bpftool` 检查运行中的节点。

## 1. 程序集合和挂载点

Cilium 会编译 `bpf/` 下的少量 C 源文件。每个源文件生成一个 ELF 对象；每个对象包含一个或多个**入口程序**（ELF section `tc/entry`、`xdp/entry`、`cgroup/...`）和多个 **tail 程序**（section `tc/tail`）。`bpftool prog show` 中显示的程序名带有 `cil_` 前缀。

### 1.1 1.20.2 中的入口程序

| ELF 对象（源文件） | 入口程序 | 挂载位置 | 用途 |
|---|---|---|---|
| `bpf_lxc.o` | `cil_from_container` | 主机侧 `lxc*` veth 的 ingress（即流出 Pod 的流量）；使用 netkit 时，挂载于 netkit 对端的主 hook | 每端点出口路径：身份、CT、出口策略、service LB（逐包模式）、转发 |
| `bpf_lxc.o` | `cil_to_container` | 主机侧 `lxc*` 的 egress（经协议栈送往 Pod 的流量） | 对经协议栈送达的流量执行 ingress 策略（端点路由、L7 代理返回流量）。只有端点需要 egress 程序时才挂载 |
| `bpf_lxc.o` | `cil_lxc_policy`、`cil_lxc_policy_egress` | **不挂载到设备**；存入全局程序数组 `cilium_call_policy` / `cilium_egresscall_policy` | 供其他程序调用的目标 ingress 策略和源 egress 策略 |
| `bpf_host.o` | `cil_from_netdev` | 每个原生/外部设备的 ingress | 面向主机及转发流量、NodePort、来自 ipcache 的身份、主机防火墙 |
| `bpf_host.o` | `cil_to_netdev` | 原生设备的 egress（仅 masquerading、NodePort、WireGuard 或 IPsec 需要时挂载） | BPF masquerade、NodePort SNAT、EDT/带宽、加密标记 |
| `bpf_host.o` | `cil_from_host` | `cilium_host` 的 egress | 从主机协议栈到 Pod 的流量 |
| `bpf_host.o` | `cil_to_host` | `cilium_host` 和 `cilium_net` 的 ingress | Pod 到主机的流量、主机防火墙 |
| `bpf_host.o` | `cil_host_policy` | 程序数组槽位（host endpoint policy） | 主机防火墙策略 |
| `bpf_overlay.o` | `cil_from_overlay`、`cil_to_overlay` | `cilium_vxlan` 或 `cilium_geneve` 的 ingress / egress | 从隧道 ID 读取源身份 |
| `bpf_wireguard.o` | `cil_from_wireguard`、`cil_to_wireguard` | `cilium_wg0` 的 ingress（始终挂载）/ egress（仅需要时挂载） | 标记已解密流量 |
| `bpf_xdp.o` | `cil_xdp_entry` | 原生设备上的 XDP | CIDR 预筛选和 NodePort/DSR 加速 |
| `bpf_sock.o` | `cil_sock4_connect`、`cil_sock4_sendmsg`、`cil_sock4_recvmsg`、`cil_sock4_getpeername`、`cil_sock4_pre_bind`、`cil_sock4_post_bind`、IPv6 对应程序、`cil_sock_release` | **cgroup v2** 根目录下的 sock_addr / sock hook | socket 级负载均衡 |
| `bpf_sock_term.o` | `cil_sock_{tcp,udp}_destroy_v{4,6}` | 调用 `bpf_sock_destroy` kfunc 的 BPF iterator（`iter/tcp`、`iter/udp`） | 终止连接到已删除后端的 socket；若 kfunc 不可用，agent 会回退到 netlink `sock_diag` |
| `bpf_probes.o`、`bpf_alignchecker.o` | 不适用 | 启动时各通过 `BPF_PROG_RUN` 执行一次 | 内核能力探测；检查 C/Go 结构体布局 |

`bpf_network.c`（`cil_from_network`，原生设备 ingress 上的 IPsec 解密）在 1.18.14 和 1.19.8 中存在，**在 1.20 中已移除**。

```
                       node A                                   node B
 pod C eth0 ----veth---- lxc_C           lxc_B ----veth---- pod B eth0
   |  cgroup/connect4          |             ^                     
   |  (bpf_sock.o)             | tcx ingress |  redirect_peer
   |                           v cil_from_container                 
   |                    +-------------------+   (tail calls, maps)
   |                    |   bpf_lxc.o       |-------+
   |                    +-------------------+       | encap / FIB redirect
   |                           |                     v
   |        cilium_host  <-----+          cilium_vxlan (cil_to_overlay)  ==underlay==>
   |        cil_from_host/cil_to_host        eth0 (cil_from_netdev / cil_to_netdev)
   |                                         eth0 XDP (cil_xdp_entry, optional)
```

### 1.2 tcx、传统 tc 和 netkit

对于按设备挂载的程序，loader（`pkg/datapath/loader/tc.go`）按以下顺序选择机制：

1. **tcx**（Helm `bpf.enableTCX: true`，默认值）：通过 `link.AttachTCX` 在 tail anchor 处挂载 `bpf_link`。链接 pin 在 `/sys/fs/bpf/cilium/endpoints/<id>/links/`（端点）或 `/sys/fs/bpf/cilium/devices/<dev>/links/`（设备）下。更新程序时会原子更新链接，因此重新加载期间不会出现程序缺失的窗口。需要 Linux 6.6 或更新内核。tcx 成功挂载后，会移除过时的传统 tc filter。
2. **传统 tc**：如果内核返回“不支持”，或 `enableTCX: false`，loader 会使用 `clsact` qdisc 和 direct-action 模式的 `cls_bpf`，并卸载过时的 tcx link。
3. **硬性失败**：只有两种机制都不可用时才会失败；agent 会报告需要 tc-bpf 支持或 tcx（Linux 6.6 或更新版本）。

**netkit**（成熟度：**Beta**）：`bpf.datapathMode: veth | netkit | netkit-l2 | auto`，默认值为 `veth`。使用 netkit 时，Pod 专属程序挂载在 netkit **对端**设备中；其他设备仍使用 tcx，选择 netkit 时会自动启用 tcx。源码强制要求（`canUseNetkit`）：内核探测通过（上游文档称 6.8 或更新；源码探测错误文本提到 6.7）、使用 BPF host routing（不能启用 `bpf.hostLegacyRouting`）、BPF masquerade、kube-proxy replacement，且**不能启用 `bpf.tproxy`**（它依赖 `bpf_sk_assign`，而此 helper 只允许用于 tc ingress）。`auto` 在 1.20 新增：执行探测，失败时警告并退回 veth。Pod 一旦使用 veth，就不能再切换为 netkit 或 `auto`；应改用新的节点组。

| 机制 | 内核 | Pin 的对象 | 重新加载行为 | Cilium 成熟度 |
|---|---|---|---|---|
| 传统 tc（`clsact` + `cls_bpf`） | 基线 5.10 | 设备上的 filter | 替换 filter | 稳定，作为回退 |
| tcx | 6.6+ | `/sys/fs/bpf/cilium/...` 下的 `bpf_link` | 原子更新 link | 稳定；可用时默认使用 |
| netkit | 6.8+（文档要求） | 对端上的 netkit link | 原子更新 link | Beta |

### 1.3 XDP 和 cgroup hook

- **XDP**（`cil_xdp_entry`）在 `loadBalancer.acceleration` 为 `native` 或 `best-effort` 时挂载。它运行 CIDR 预筛选（`cilium_cidr_v4_fix`/`dyn` LPM map）以及 NodePort/DSR 快速路径。如果驱动返回 `EINVAL`，loader 最多尝试四种挂载组合（attach 类型和 `XDP_HAS_FRAGS` 标志）。
- **cgroup hook** 使用 `bpf_link` 挂载一次，位置在 cgroup 根目录（agent flag `--cgroup-root`，默认 `/run/cilium/cgroupv2`），pin 在 `/sys/fs/bpf/cilium/socketlb/links/cgroup` 下。除非设置 `socketLB.hostNamespaceOnly=true`，否则它们会在每个 Pod netns 中运行。

## 2. Tail call 和策略程序结构

### 2.1 为什么使用 tail call

Tail call 会用另一个程序替换当前程序，不再返回。Cilium 使用它有三个原因：单个程序复杂度受 verifier 限制（100 万条指令）、栈仅有 512 字节，以及能让大型可选功能不进入常见处理路径。tail call 链最多可包含 33 次调用。将 BPF-to-BPF 调用与 tail call 混用需要内核 5.10，这也是基线设为 5.10 的原因之一。

Tail call 之间的状态通过两处传递：`skb->cb[]`（`CB_SRC_LABEL` 等 `CB_*` 槽位）以及 per-CPU scratch map `cilium_tail_call_buffer4/6`，其中可以保存例如 CT tail 程序计算出的 conntrack tuple 和结果。

### 2.2 每端点调用数组

每个端点都有一个私有 `PROG_ARRAY`，名为 `cilium_calls_<endpoint-id, 5 digits>`（例如 `cilium_calls_00312`）。host endpoint 使用 `cilium_calls_hostns_<id>`，每个原生设备使用 `cilium_calls_netdev_<ifindex>`。其他 loader 使用 `cilium_calls_overlay_2`（overlay 设备以保留的 `world` 身份 2 命名）、`cilium_calls_wireguard_<ifindex>` 和 `cilium_calls_xdp_<ifindex>`。这些数组声明了 `CILIUM_CALL_SIZE` 个条目，并使用一种 pin 标志，含义是“每次加载时替换 pin；绝不复用旧数组”。

| 版本 | `CILIUM_CALL_SIZE` |
|---|---|
| 1.18.14 | 48 |
| 1.19.8 | 49 |
| 1.20.2 | 50 |
| 1.21.0-pre.3 | 50 |

槽位是**静态**的：调用点使用内联汇编，槽位编号是常量。loader 会读取每个 `tc/tail` 程序中的 BTF decl-tag（`tail:cilium_calls/<idx>`），填充数组，并在应用常量后**剪除不可达的 tail 程序**（见第 5 节）。1.20 中槽位分组如下：

| 槽位 | 用途 |
|---|---|
| 1–2、4–5 | 丢弃/错误通知、ICMPv6 邻居请求、TTL 超时 |
| 6 | ARP |
| 3 | 未使用（保留编号空隙以避免回移植冲突） |
| 7、10 | IPv4 / IPv6 from-LXC（作为 netdev、overlay、WireGuard 入口的别名） |
| 8–9 | IPv4 到 IPv6 及 IPv6 到 IPv4 转换（`CILIUM_CALL_IPV46_RFC6052`、`CILIUM_CALL_IPV64_RFC6052`；NAT46/NAT64） |
| 11–14 | 仅 to-LXC policy、to-endpoint |
| 15–25、36–39 | NodePort NAT、rev-NAT、DSR、SNAT 转发；from-host |
| 26–27 | from-LXC 后续处理（出口路径的第二部分，用于拆分 verifier 复杂度） |
| 28–33 | CT ingress / 仅 CT ingress policy / CT egress，IPv4 和 IPv6 |
| 34–35、40 | SRv6、跨集群 rev-SNAT |
| 41–47 | 来自主机/netdev 的后续处理、“no service” ICMP unreachable、多播投递 |
| 48–49 | 策略拒绝时的 ICMP 响应（1.20 新增，启用 `policy_deny_response` 时使用） |

### 2.3 全局策略程序数组

策略程序不在每端点调用数组中。`cil_lxc_policy` 和 `cil_lxc_policy_egress` 会按端点 ID 插入两个**全局**程序数组，数组大小为 `ENDPOINTS_MAP_SIZE`：

| 数组 | 索引 | 执行内容 |
|---|---|---|
| `cilium_call_policy` | 目标端点 ID | 目标 ingress 策略 |
| `cilium_egresscall_policy` | 源端点 ID | 源 egress 策略 |

loader 会在挂载 tc/tcx 程序之前写入这些槽位（`PolicyMap.Update(ep id, PolicyProg)`）。发送端完成本地目标的 L3 改写后，会调用 `tail_call_policy(ep->lxc_id)`。这一点很重要：使用 BPF host routing 时，数据包会通过 `bpf_redirect_peer` 移入目标 Pod 的 netns，**跳过目标端的 tc egress hook**。因此发送端直接调用目标策略程序，才能仍然对同节点 ingress 流量执行策略。如果槽位为空（端点正在终止），数据包会以 `DROP_EP_NOT_READY` 丢弃。

对于经协议栈送达的流量，`cil_to_container` 仍然存在，因此目标 ingress 策略可以通过发送端的 tail call 或该 egress hook 执行。

## 3. 策略执行路径

### 3.1 策略 map

每个端点都有 `cilium_policy_v3_<id>`（1.20；1.18/1.19 使用 `cilium_policy_v2_`）。类型为 `LPM_TRIE`，标志为 `BPF_F_NO_PREALLOC | BPF_F_RDONLY_PROG_COND`，大小由 `--bpf-policy-map-max` 控制（默认每个端点 16384）。

```
policy_key  { lpm prefixlen; u32 sec_label;   /* remote identity, 0 = wildcard */
              u8 egress:1;  u8 protocol;      /* 0 = any */
              be16 dport; }                   /* prefix match => port ranges */
policy_entry{ be16 proxy_port;                /* != 0 => redirect to L7 proxy */
              deny:1; lpm_prefix_length:5; auth_type:7; has_explicit_auth_type:1;
              u32 precedence; u32 cookie; }
```

LPM 前缀中，`sec_label` 和 `egress` 字段必须完全匹配；`protocol` 字段只能完全匹配或不匹配；`dport` 按位前缀匹配，这正是将端口范围压缩成少量条目的方式。

### 3.2 查询算法

对于远端身份为 `R`、协议为 `P`、端口为 `D` 的流：

1. 先使用 `sec_label = R` 执行精确查询。如果命中项具有最高优先级（deny），则立即停止。
2. 再执行聚合查询：先查身份所属的聚合项（例如 CIDR group），再以 `sec_label = 0` 查询（L3 通配）。
3. 先选择 `precedence` 较高的结果（deny 高于 proxy redirect，proxy redirect 高于 allow），再选择 LPM 前缀较长的结果。没有命中项则返回 `DROP_POLICY`。

事件会报告匹配类型（L3+L4、仅 L3、仅 L4、仅协议、全部）。启用 ICMP 规则时，ICMP 类型存放在 `dport` 字段中；“需要分片”消息始终允许。

### 3.3 判定和副作用

- Deny：返回 `DROP_POLICY_DENY` 并产生丢弃事件。若 allow 且 `proxy_port != 0`，则重定向到代理（见 3.5 节）。若 allow 且 `auth_type != 0`，但 `cilium_auth_map` 中没有有效条目，则返回 `DROP_POLICY_AUTH_REQUIRED`。
- **出口策略由源端点执行**（`handle_ipv4_from_lxc`），仅适用于 `CT_NEW` 和 `CT_ESTABLISHED`；回复（`CT_REPLY`、`CT_RELATED`）跳过策略。**入口策略由目标端点执行**（其策略程序中的 `ipv4_policy()`），allow 后会创建 ingress CT 条目。
- Deny 和新建的 allow 连接都会发出 policy-verdict 事件。Hairpin 流量（Pod 访问自己的 Service IP）跳过策略。
- 可选的逐条目计数器写入 `cilium_policystats`（`--bpf-policy-stats-map-max` 为 65536）。

### 3.4 更新策略不会重新编译

策略更新只会操作 `cilium_policy_v3_<id>` map（`applyPolicyMapChangesLocked`）。仅当端点或节点配置 hash 改变时，才会重新构建并加载对象。因此编辑 `CiliumNetworkPolicy` 不会触发 clang。

### 3.5 L7 和 FQDN 重定向

当 `proxy_port != 0` 时，`ctx_redirect_to_proxy4()` 会将流量送往 Envoy 或 DNS proxy。存在两种实现方式：

| 方式 | 工作原理 | 成熟度 |
|---|---|---|
| iptables TPROXY（默认） | 数据路径设置 `mark = MARK_MAGIC_TO_PROXY \| proxy_port << 16` 并返回 OK；`CILIUM_PRE_mangle` 规则通过 `xt_socket`/`TPROXY` 将流量导向监听器 | 稳定 |
| `bpf.tproxy: true` | 在 tc ingress 处由 `bpf_sk_assign` 指定监听 socket | Beta，默认关闭，**与 netkit 不兼容**（agent 在 1.19.8、1.20 和 1.21.0-pre.3 中会拒绝启动；在 1.18.14 源码中未发现此检查） |

代理端口来自 `--proxy-portrange-min/max`（10000–20000）。CT 条目记录 `proxy_redirect`，使回复流量返回代理。L7 事件不是由 BPF 产生的；Envoy 和 DNS proxy 会将 access log 记录报告给 agent。

双向认证（`auth_type`）在 **1.20 已弃用**（请改用 ztunnel）；**[1.21 预发布版]移除** `--bpf-auth-map-max` 和 `cilium_auth_map`，条目中的 auth 位将保留备用。

## 4. Map 目录

全局 map 按名称 pin 在 `/sys/fs/bpf/tc/globals/` 下；link 和 plugin 对象在 `/sys/fs/bpf/cilium/` 下。Helm 配置项：`bpf.root`（默认 `/sys/fs/bpf`）、`bpf.autoMount.enabled`。

### 4.1 核心 map

| Map | 类型 | 键 → 值（主要字段） | 备注 |
|---|---|---|---|
| `cilium_lxc` | HASH | 端点 IP（及地址族、cluster_id）→ `{ifindex, lxc_id, flags, mac, node_mac, sec_id, parent_ifindex}` | 本地端点和主机 IP；65535 个条目（`lxcmap.MaxEntries`） |
| `cilium_ipcache_v2` | LPM_TRIE | `{cluster_id, family, ip/prefix}` → `{sec_identity, tunnel_endpoint, key, flag_skip_tunnel, flag_has_tunnel_ep, flag_ipv6_tunnel_ep, flag_remote_cluster}` | **身份和隧道端点**；512000 个条目（`ipcachemap.MaxEntries`） |
| `cilium_policy_v3_<id>` | LPM_TRIE | 见 3.1 | 每个端点一个 |
| `cilium_calls_<id>`、`_hostns_`、`_netdev_` | PROG_ARRAY | 槽位 → 程序 | 私有；每次加载都会替换 |
| `cilium_call_policy`、`cilium_egresscall_policy` | PROG_ARRAY | 端点 ID → 策略程序 | 全局 |
| `cilium_ct4_global`、`cilium_ct6_global` | LRU_HASH | 五元组 + 方向标志 → `ct_entry` | TCP |
| `cilium_ct_any4_global`、`cilium_ct_any6_global` | LRU_HASH | 同上 | 非 TCP |
| `cilium_snat_v4_external`（及 `v6`） | LRU_HASH | CT tuple → NAT 条目（`to_saddr/to_sport` 或 `to_daddr/to_dport`） | masquerade、NodePort SNAT |
| `cilium_nodeport_neigh4/6` | LRU_HASH | 下一跳 IP → MAC | |
| `cilium_node_map_v2` | HASH | `{family, ip}` → `{node id, spi}` | IPsec/WireGuard/ClusterMesh 节点 ID（v1 于 1.19 移除） |
| `cilium_devices`（1.20 新增） | HASH | ifindex → `{mac, l3}` | 由 agent 同步 |
| `cilium_runtime_config` | ARRAY | 索引 → u64（时间偏移、agent 存活状态） | `cilium-dbg bpf config list` |
| `cilium_metrics` | PERCPU_HASH | `{reason, direction, line, file}` → `{count, bytes}` | 为 forward/drop 计数器提供数据 |
| `cilium_events` | PERF_EVENT_ARRAY | CPU → perf fd | monitor 和 Hubble 的来源（见第 8 节） |
| `cilium_signals` | PERF_EVENT_ARRAY | 数据路径 → agent 信号 | 例如 CT 满时触发 GC |

Conntrack 地址相对于数据包中的地址将源和目标互换存储；`ct_entry` 保存 lifetime、`rx/tx_closing`、`rev_nat_index`、`proxy_redirect`、`from_l7lb`、`from_tunnel`、`src_sec_id` 和已观察到的 TCP 标志。单个 map 中存放出口、入口和 Service 范围的条目，通过 `tuple.flags` 区分。Cluster Mesh 会增加按集群划分的内层 map（`cilium_per_cluster_ct_*`），以处理 IP 重叠。

超时值（agent flags，1.20.2）：TCP established 为 2 小时 13 分 20 秒，SYN 为 1 分钟，FIN 为 10 秒，非 TCP 为 1 分钟，Service TCP 为 2 小时 13 分 20 秒，Service grace 为 1 分钟。

### 4.2 负载均衡 map

| Map | 类型 | 键 → 值 | 备注 |
|---|---|---|---|
| `cilium_lb4_services_v2`（及 `6`） | HASH | `{address, dport, backend_slot, proto, scope}` → `{backend_id or affinity/algorithm, count, rev_nat_index, flags, qcount}` | 槽位 0 是 frontend；槽位 1..count 存放 backend ID；`scope` 区分外部和内部流量（externalTrafficPolicy） |
| `cilium_lb4_backends_v3`（及 `6`） | HASH | `backend_id` → `{address, port, proto, flags, cluster_id, zone}` | |
| `cilium_lb4_reverse_nat`（及 `6`） | HASH | `rev_nat_index` → `{address, port}` | 逐包 LB 的回复地址恢复 |
| `cilium_lb4_reverse_sk` | LRU_HASH | `{socket cookie, backend addr, port}` → `{original service addr, port, rev_nat_index}` | socket-LB 反向转换 |
| `cilium_lb4_affinity`、`cilium_lb_affinity_match` | LRU_HASH / HASH | 客户端（IP 或 netns cookie）+ rev_nat → backend | `sessionAffinity` |
| `cilium_lb4_source_range` | LPM_TRIE | `{rev_nat_id, cidr}` → flag | `loadBalancerSourceRanges` |
| `cilium_lb4_maglev` | HASH_OF_MAPS | `rev_nat_id` → 查找表数组 | `--bpf-lb-algorithm maglev`；表大小由 `--bpf-lb-maglev-table-size` 控制 |
| `cilium_lb4_health` | LRU_HASH | socket cookie → 对端 backend | LB health datapath；内核 5.12 |

Service 的 `affinity_timeout` 字段最高 8 位用于保存选择算法（random 或 maglev）。

### 4.3 功能 map（每项一行）

`cilium_ipmasq_v4/v6`（不执行 masquerade 的 CIDR）、`cilium_ipv4_frag_datagrams`（默认 8192）、`cilium_vtep_map`、`cilium_srv6_*`、`cilium_egress_gw_policy_v4_v2`（1.20 中从 `_v4` 改名）、`cilium_l2_responder_v4/v6`、`cilium_mcast_*`、`cilium_cidr_v4_fix/dyn`（XDP 预筛选）、`cilium_encrypt_state`、`cilium_auth_map`、`cilium_policystats`、`cilium_ratelimit`、`cilium_throttle`、`cilium_lb_act`/`cilium_lb_fct`（活动连接跟踪，默认关闭），以及 per-CPU scratch map（`cilium_tail_call_buffer4/6`、`cilium_nodeport_nat_buffer`、`cilium_xdp_scratch`、`cilium_percpu_trace_id`）。

### 4.4 容量设置 flags

| Flag（Helm） | 默认值（1.20.2） | 影响 |
|---|---|---|
| `--bpf-map-dynamic-size-ratio`（`bpf.mapDynamicSizeRatio`） | 0.0025（RAM 的 0.25%）；**默认启用动态大小调整** | CT TCP/any、NAT、socket reverse-NAT；NodePort neighbor map 沿用 NAT 大小（flag 帮助文本称“CT、NAT 和 policy BPF map”，但容量调整代码并未调整 policy map） |
| `--bpf-ct-global-tcp-max`（`bpf.ctTcpMax`） | 524288 | TCP CT |
| `--bpf-ct-global-any-max`（`bpf.ctAnyMax`） | 262144 | 非 TCP CT |
| `--bpf-nat-global-max`（`bpf.natMax`） | 524288 | NAT；若超过 CT 总和的 2/3，会发出警告并截断 |
| `--bpf-neigh-global-max`（`bpf.neighMax`） | 524288 | NodePort neighbor |
| `--bpf-policy-map-max`（`bpf.policyMapMax`） | 每端点 16384（最大 65536） | policy |
| `--bpf-fragments-map-max` | 8192 | 分片 |
| `--bpf-node-map-max` | 16384 | node map |
| `--bpf-lb-map-max`（`bpf.lbMapMax`） | 65536 | 六个 per-LB-map flag 的默认值（`--bpf-lb-service-map-max`、`-service-backend-map-max`、`-rev-nat-map-max`、`-affinity-map-max`、`-source-range-map-max`、`-maglev-map-max`）；各项默认 0，表示使用 `lb-map-max`。源码中存在（`pkg/loadbalancer/config.go`），但生成的 cmdref 未列出这些项，只展示 `--bpf-lb-map-max` |
| `--bpf-sock-rev-map-max` | 动态；默认与 CT-any 大小相同 | socket reverse map |
| `bpf.distributedLRU.enabled` | false | per-CPU LRU 空闲列表；适用于较大的 map |
| `bpf.preallocateMaps` | false | 用额外内存换取较低插入延迟 |

动态大小的计算方式为 `entries = default_entries * (ratio * RAM) / total_default_bytes`，并限制在每个 map 的下限（CT TCP 128Ki、CT any 64Ki、NAT 128Ki、socket reverse 64Ki）和 16Mi（2^24）的上限之间。**显式设置某个 map 的 flag，只会对该 map 关闭动态容量调整**。动态调整生效时 agent 会记录 `option <name> set by dynamic sizing to <N>`。上游性能调优配置使用的 ratio 为 0.08。

> 调整 map 大小时会重新创建 map，在重新填入数据前会丢失其中条目。在运行中的节点调整 LB map 或 CT map 会中断已建立连接。应将容量调整安排为滚动节点操作。

通过 `cilium_bpf_map_pressure{map_name}`（高于 `--bpf-policy-map-pressure-metrics-threshold` 时发出，默认 0.1）、`cilium_bpf_map_capacity` 和 `cilium_bpf_map_ops_total` 监控 map。

## 5. 从 Agent 到内核：编译、加载和挂载

### 5.1 流程

```
agent start
  |  write node headers  (StateDir/globals: node_config.h, netdev_config.h, ...)
  |  hash node config -> if changed, wipe template cache (StateDir/templates)
  v
template config hash (compile-time #defines only)
  |  cache hit?  -> reuse StateDir/templates/<sha>/bpf_lxc.o
  |  miss        -> clang -O2 --target=bpf -mcpu=v3|v2|v1 ... -> new ELF template
  v
LoadCollection (per endpoint / device)
  |  copy spec -> patch maps -> rename maps (cilium_calls -> cilium_calls_<id>, cilium_policy -> cilium_policy_v3_<id>)
  |  write .rodata.config (endpoint ID, IPs, MAC, ifindex, feature switches)
  |  dead-code analysis -> remove unused tail calls and maps
  |  fill tail-call arrays from BTF decl tags
  |  load into kernel (verifier); reuse pinned global maps, replace incompatible ones
  v
attach: policy progs into cilium_call_policy/egresscall_policy
        -> tcx/tc/netkit entry programs -> commit() map pins -> endpoint routes
```

### 5.2 ELF 模板和 `.rodata.config`

编译开销较大的步骤仍在 agent 中执行（容器镜像包含 clang/LLVM；原生运行 agent 需要 LLVM 18.1 或更新版本）。为避免每个 Pod 都重新编译，Cilium 只对**模板配置**计算 hash：改变代码形态的 `#define ENABLE_*` flags。具有相同 flags 的所有端点共享 `StateDir/templates/<sha>/` 下的同一个对象。使用 `cilium-dbg bpf sha list` 列出模板。

每端点各自的值不会在编译时写入，而是作为 `.rodata.config` section 中的全局变量，以 `DECLARE_CONFIG(type, name, desc)` 声明并通过 `CONFIG(name)` 读取。加载前 agent 会把这些值写入 spec 的副本；内核会冻结只读数据，因此 verifier 能将这些值视为常量并**剪除无效分支**。这需要死代码消除支持（内核 5.1 或更新版本）。Go 侧结构由 `dpgen` 根据 BTF decl-tag 生成（`pkg/datapath/config/*_config.go`）。每个端点/设备的有效常量会以 JSON（例如 `bpf_lxc.json`）保存到状态目录，并包含在 `cilium sysdump` 中。

每个版本都会把更多 `#define` 开关移入 `.rodata.config`，从而减少不同模板数量和重新编译次数。在各版本源码 checkout 的 BPF 树中用 grep 统计 `DECLARE_CONFIG`/`NODE_CONFIG` 声明，结果分别为 1.18.14 的 18 个、1.19.8 的 43 个、1.20.2 的 73 个以及 **[1.21 预发布版]**（v1.21.0-pre.3）的 104 个；统计命令为 `grep -rE '^\s*(DECLARE_CONFIG|NODE_CONFIG)\(' bpf --include=*.h --include=*.c | wc -l`。这些数字只能用作大致趋势，并非 API。

### 5.3 重新生成

每次重新生成端点时，agent 会计算端点 header hash。如果与上次相同，就只同步 map（`RegenerateWithoutDatapath`，即策略变更场景）。否则会写入 headers 并重新加载数据路径。相关指标包括：`cilium_endpoint_regenerations_total`、`endpoint_regeneration_time_stats_seconds`（包含 `bpfCompilation`、`bpfLoadProg`、`bpfWaitForELF` 等阶段）以及 1.20 新增的 `cilium_endpoint_component_status`。

顺序很重要：必须等所有入口程序都挂载之后，才能执行 map pin 的 `commit()`；否则新程序可能会 tail call 到旧数组，从而“漏掉” tail call。

### 5.4 Verifier 测试

Cilium 会针对内核 5.10、6.1 和 net-next 对启用最多功能的构建执行编译测试（`bpf/complexity-tests/`）。程序加载时发生 verifier 失败，会在日志中输出完整的 verifier 信息。

## 6. 内核和功能矩阵

### 6.1 强制启动条件（1.20.2）

如果缺少下列条件，agent 会拒绝启动：`bpf()` 和 JIT；tc-bpf 或 tcx；`bpf_skb_change_tail`；`bpf_get_socket_cookie`；`bpf_get_current_cgroup_id`；`bpf_fib_lookup`；死代码消除；可写的 `skb->queue_mapping`；大型（100 万条指令）程序；带 `BPF_ADJ_ROOM_MAC` 的 `bpf_skb_adjust_room`；`bpf_jiffies64`；`BPF_MAP_LOOKUP_BATCH`；`bpf_get_netns_cookie`；`bpf_sk_assign`；`bpf_get_cgroup_classid`；cgroup sock_addr 中的 `bpf_perf_event_output`；`bpf_csum_level`；`bpf_skb_change_head`；`bpf_redirect_neigh`；`bpf_redirect_peer`。因此文档要求的最低版本是**内核 5.10**（RHEL 8.10 的 4.18 是明确例外，因为 Red Hat 回移了相关补丁）。现在每个 helper 的传统 header 探测为空；5.10 基线假定这些 helper 全部可用。

上游列出的内核配置选项包括 `BPF`、`BPF_SYSCALL`、`BPF_JIT`、`NET_CLS_BPF`、`NET_CLS_ACT`、`NET_SCH_INGRESS`、`CGROUPS`、`CGROUP_BPF`、`DEBUG_INFO_BTF`，以及 `VXLAN`、`GENEVE`、带宽管理器的 `NET_SCH_FQ` 和 `NETKIT` 等功能附加项。

### 6.2 可选加速功能

| 功能 | 最低内核 | 成熟度 / 备注 |
|---|---|---|
| tcx link | 6.6 | 可用时默认启用；否则用传统 tc |
| netkit（`bpf.datapathMode`） | 6.8（文档要求；源码探测文本称 6.7） | Beta |
| IPv6 BIG TCP | 5.19 | 需要受支持的 NIC 驱动 |
| IPv4 BIG TCP | 6.3 | |
| 带宽管理器使用 BBR | 5.18 | |
| LB health-check 数据路径 | 5.12 | |
| Multicast | AMD64 为 5.10；AArch64 为 6.0 | |
| `bpf_sock_destroy` kfunc | 源码未说明 | 自动回退到 netlink `sock_diag` |

数据路径不使用 CO-RE relocation helper（搜索 1.20.2 的 `bpf/` 树，`preserve_access_index` 只出现在一条 UAPI header 注释中）：它针对自身的 headers 和 UAPI `__sk_buff` 编译。BTF 用于 map 定义、`.rodata.config` 数据段和 decl-tag，而且必须设置 `CONFIG_DEBUG_INFO_BTF=y`。

在 EKS 上启用依赖 tcx 或 netkit 的设置前，先用 `uname -r` 和 `cilium-dbg status` 检查真实节点内核；本章不假定任何 AMI 自带的内核版本。

## 7. 工作示例：Pod → Service → Pod

说明性设置（数字仅为示例；结构来自源码）：客户端 Pod `C` 为 `10.0.1.10`，身份 `4711`，端点 ID `312`，位于节点 A。Service `web` 的 ClusterIP 为 `10.100.0.20:80/TCP`，`rev_nat_index` 为 `42`，有两个后端：B1 `10.0.1.55`（节点 A，端点 87）和 B2 `10.0.2.77`（节点 B），两者身份均为 `9001`。设置为：IPv4、veth、tcx、BPF host routing、`kubeProxyReplacement: true`（这会强制启用 socket-LB）、`socketLB.hostNamespaceOnly=false`。

### 第 0 跳：Pod 中的 `connect()`，`cgroup/connect4`（`cil_sock4_connect`）

1. 使用 `{10.100.0.20, 80, TCP, slot 0, scope 0}` 查询 `cilium_lb4_services_v2`。未命中则保持 sockaddr 不变；命中项的 `count=2`。
2. 选择一个槽位：TCP 随机选择（UDP 使用 socket cookie）。使用该槽位查询 service key，取得 `backend_id`，再查询 `cilium_lb4_backends_v3[backend_id]`，得到 `10.0.2.77:80`。如果配置了 `sessionAffinity`，先查询 `cilium_lb4_affinity`。
3. 写入 `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}] = {10.100.0.20, 80, 42}`。
4. 在系统调用中改写 `user_ip4/user_port`。**线上不会发生 DNAT**。Pod 内部执行 `tcpdump` 会看到后端 IP，这往往令人意外。启用 socket-LB tracing 时会产生 `trace_sock_notify` 事件。

### 第 1 跳：SYN 离开 Pod，主机侧 veth 上的 `cil_from_container`（tcx ingress）

| 步骤 | 操作 | 使用的 map |
|---|---|---|
| 1 | 清除 metadata，调用 `send_trace_notify(TRACE_FROM_LXC)`（受聚合设置影响） | `cilium_events` |
| 2 | tail call 到槽位 7（IPv4 from-LXC） | `cilium_calls_00312` |
| 3 | 跳过逐包 LB（socket-LB 已完成转换） | 无 |
| 4 | tail call 到槽位 30（CT egress）：查询 `CT_NEW`，并将 tuple 存入 per-CPU buffer | `cilium_ct4_global`、`cilium_tail_call_buffer4` |
| 5 | tail call 到槽位 26（`handle_ipv4_from_lxc`） | `cilium_calls_00312` |
| 6 | 解析目标身份：LPM 查询 `10.0.2.77` 得到身份 9001；使用 overlay 时同时得到节点 B 的隧道端点。未命中表示 `world` | `cilium_ipcache_v2` |
| 7 | 出口策略：查询 `{egress=1, sec_label=9001, TCP, 80}`，执行两阶段查询；允许或丢弃。新允许的流会产生 policy-verdict 事件 | `cilium_policy_v3_00312`、`cilium_events`；丢弃时写入 `cilium_metrics` |
| 8 | 若 `proxy_port != 0`：标记为代理流量，给 CT 设置 `proxy_redirect` 标志，并交给协议栈（见 3.5 节） | |
| 9 | `ct_create4(CT_EGRESS)`：插入条目；SYN 的生命周期为 1 分钟，收到 ACK 后为 2 小时 13 分 20 秒 | `cilium_ct4_global`（相关 ICMP 还会用 CT-any） |
| 10 | 选择转发路径（见下文） | |

第 10 步的转发选项：

- **目标位于同一节点**（B1）：`cilium_lxc[dst]` 返回 `{ifindex, lxc_id=87, mac, node_mac}`；改写 L2 header，设置 metadata（`CB_SRC_LABEL=4711` 和投递标志）；随后通过 `cilium_call_policy` 中的 `tail_call_policy(87)` 执行 B1 的 `cil_lxc_policy`（第 3 跳）。
- **远端，使用 overlay**：ipcache 值中设置了 `flag_has_tunnel_ep`，因此 `bpf_skb_set_tunnel_key` 会将 `tunnel_id` 设为源身份 4711，并将 `remote_ipv4` 设为节点 B；数据包重定向到 `cilium_vxlan`/`cilium_geneve`，由内核封装前执行 `cil_to_overlay`。Pod 到 Pod 的流量不会执行 masquerade。
- **远端，使用原生路由和 BPF host routing**：执行 `bpf_fib_lookup`，然后重定向到 NIC。若启用 `bpf.hostLegacyRouting=true`，数据包则以 OK 返回内核协议栈和 netfilter。此路径没有 VNI；接收端会通过源 IP 在 ipcache 中重新解析源身份（或通过 IPsec/WireGuard 的标记解析）。

### 第 2 跳（仅远端）：节点 B 接收数据包

- Overlay：`cil_from_netdev` 将 UDP 8472（VXLAN）/6081（Geneve）交给协议栈；内核解封装到 `cilium_vxlan`；`cil_from_overlay` 读取 `bpf_skb_get_tunnel_key`，将 `tunnel_id` 映射为**源身份**（若为 host identity，则通过 `DROP_INVALID_IDENTITY` 拒绝），将身份存入 `CB_SRC_LABEL`，发出 `TRACE_FROM_OVERLAY`，然后查询 `cilium_lxc[10.0.2.77]` 并调用 `tail_call_policy(ep)`。
- 原生路由：`cil_from_netdev` 使用 `cilium_ipcache_v2[src ip]` 中的源身份执行相同步骤。

### 第 3 跳：目标 ingress 策略和投递

1. `cil_lxc_policy` 执行 CT-ingress tail call：查询 `cilium_ct4_global`，结果为 `CT_NEW`。
2. 入口策略：使用 `{egress=0, sec_label=4711, TCP, 80}` 查询 `cilium_policy_v3_00087`。发出 verdict 事件。
3. `ct_create4(CT_INGRESS)` 记录 `src_sec_id=4711`、`from_tunnel` 和 `proxy_redirect`。
4. 通过 `bpf_redirect_peer` 将流量送入 Pod netns（veth），或使用 `redirect`（netkit），并产生 `TRACE_TO_LXC` 事件。后端协议栈以 `10.0.2.77` 为源地址回复；它不会看到 ClusterIP。

### 第 4 跳：回复和关闭

- B 的 `cil_from_container` 将 ingress CT 条目识别为 `CT_REPLY`，因此**跳过策略**；数据包以 VNI 9001 封装返回（或使用原生路由）。在节点 A 上执行 `tail_call_policy(312)`，客户端 C 的策略程序发现 `CT_REPLY` 后跳过策略，再通过 `redirect_peer` 将数据包交给 C。
- Socket-LB 反向转换：应用认为自己连接的是 `10.100.0.20`。`getpeername` 和 `recvmsg` hook 查询 `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}]`，并返回 Service 地址。
- 不使用 socket-LB 时（host-namespace-only 模式、L7 LB、SCTP），第 1 跳会在 `bpf_lxc` 中执行 DNAT，并将 `rev_nat_index` 存入 CT 条目；回复会通过 `cilium_lb4_reverse_nat[rev_nat_index]` 恢复源地址。
- FIN/RST 会设置 `tx/rx_closing`，并将生命周期缩短到 FIN timeout（10 秒）；agent 的 CT GC 会删除过期条目。`cilium_lb4_reverse_sk` 条目会保留到 LRU 淘汰或 `cil_sock_release`。

### 逐跳查询检查表

| 跳 | 程序 | 查询/写入 |
|---|---|---|
| 0 | `cil_sock4_connect` | `lb4_services_v2` 查询两次、`lb4_backends_v3`、可选的 `lb4_affinity`、写入 `lb4_reverse_sk` |
| 1 | `cil_from_container` 及 tail 程序 | `calls_<id>` 三次、`tail_call_buffer4`、`ct4_global`（查询和创建）、`ipcache_v2`、`policy_v3_<src>`（egress）、`cilium_lxc`、`call_policy`、`events`、`metrics` |
| 2 | `cil_from_overlay` / `cil_from_netdev` | tunnel key 或 `ipcache_v2`、`cilium_lxc`、`call_policy` |
| 3 | `cil_lxc_policy`（目标端） | `ct4_global`、`policy_v3_<dst>`（ingress）、创建 `ct4_global` 条目、`events` |
| 4 | 反向路径、`recvmsg` | `ct4_global`（回复）、`lb4_reverse_sk` 或 `lb4_reverse_nat` |

### 影响此示例路径的 1.20 行为变化

启用 kube-proxy replacement，且设置 `socketLB.enabled=false` 或 `socketLB.hostNamespaceOnly=true` 时，集群内部 Pod 到 NodePort 的连接现在会在**客户端 Pod**的 tc hook 上进行负载均衡。因此客户端 egress 和后端 ingress NetworkPolicy 都必须允许相应流量。

## 8. Hubble 事件流水线

```
BPF program --ctx_event_output--> cilium_events (PERF_EVENT_ARRAY, per CPU)
      |   trace_notify / drop_notify / policy_verdict_notify / debug / capture / trace_sock_notify
      v
agent monitor (pkg/monitor/agent): perf reader, 64 pages per CPU, opened only if a consumer exists
      |-- lost samples (kernel buffer overrun) -> MonitorStatus.Lost
      |-- unix-socket listeners (cilium-dbg monitor), queue --monitor-queue-size
      v
Hubble consumer -> observer queue (--hubble-event-queue-size)
      |   full => LostEvent source=OBSERVER_EVENTS_QUEUE, hubble_lost_events_total
      v
Hubble parser (identity/endpoint/service enrichment) -> ring buffer (--hubble-event-buffer-capacity)
      v
gRPC: hubble observe / Relay / UI
```

需要记住的事实：

- 在 1.20 和 1.21-pre.3 中，事件 map 是 **perf event array**，不是 BPF ring buffer。
- 数据路径中的事件量控制项是 `bpf.monitorAggregation`（Helm 默认 `medium`；agent flag 默认 `None`）。设置为 `medium` 或更高时，会抑制节点内 receive trace；已建立连接只有在 `bpf.monitorInterval`（5 秒）到期或检测到 `bpf.monitorFlags` 指定的标志时才上报。各类开关包括 `bpf.events.drop.enabled`、`bpf.events.policyVerdict.enabled`、`bpf.events.trace.enabled`（默认全为 true），以及实验性限速项 `bpf.events.default.rateLimit` / `burstLimit`（两者必须同时设置，或同时为零）。
- `hubble observe` 中的流量事件保存在内存 ring（`hubble.eventBufferCapacity` 必须是 `2^n - 1`；默认 4095，最大 65535）。这是尽力而为：perf-buffer 溢出和 observer 队列溢出都会丢事件，但分别计入不同的 `source` 标签（`perf_event_ring_buffer`、`observer_events_queue`）。
- L7 事件并非来自 BPF；它们以 proxy 事件的形式送达 agent。

## 9. 检查工具

### 9.1 cilium-dbg

```bash
CILIUM_POD=$(kubectl -n kube-system get pod -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}')
kc() { kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- "$@"; }

kc cilium-dbg status --verbose         # KPR, datapath mode (configured vs operational), BPF map pressure
kc cilium-dbg bpf fs show              # bpffs mount
kc cilium-dbg map list -v              # pinned maps and sizes
kc cilium-dbg bpf endpoint list        # cilium_lxc
kc cilium-dbg bpf ipcache list         # identity + tunnel endpoint per IP/CIDR
kc cilium-dbg bpf ct list global       # conntrack
kc cilium-dbg bpf nat list             # SNAT maps
kc cilium-dbg bpf lb list --frontends  # also --backends, --revnat, --source-ranges
kc cilium-dbg bpf lb maglev list       # only with Maglev
kc cilium-dbg bpf policy get --all -n  # every cilium_policy_v3_*, numeric identities
kc cilium-dbg bpf metrics list         # cilium_metrics
kc cilium-dbg bpf config list          # cilium_runtime_config
kc cilium-dbg bpf sha list             # compiled ELF templates
kc cilium-dbg monitor -t drop -t policy-verdict --related-to <ENDPOINT_ID>
```

`cilium-dbg map get <name>` 显示 agent 的缓存视图，不一定反映内核中的实际状态；`cilium-dbg map events <name>` 显示更新日志。不存在 `bpf tunnel` 和 `bpf calls` 子命令。

### 9.2 bpftool（在节点上运行）

```bash
sudo bpftool net show                                     # tcx/tc/xdp/netkit attachments per device
sudo bpftool prog show | grep -E 'cil_|tail_'             # entry and tail programs
sudo bpftool map show pinned /sys/fs/bpf/tc/globals/cilium_ct4_global
sudo bpftool cgroup tree /run/cilium/cgroupv2             # socket-LB hooks
sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links
```

将 pin 的 map 视为只读。不要向 Cilium map 写入原始字节，否则 agent 的缓存状态会不一致。agent 镜像可能不含 `bpftool`；本次审查没有验证其是否包含该工具。如镜像中没有，请从节点或 debug Pod 中运行。

**[1.21 预发布版]启用** `--enable-bpf-stats`（Helm `bpf.stats.enabled`，默认 false）后会打开内核运行时统计，并新增 `bpf/stats/report` hive 命令，对外提供 `cilium-dbg bpf stats report`（参数 `--sort avg|total|runs`、`--pod`、`--device`、`--json`），显示各程序运行次数和平均耗时。

## 10. 数据路径插件（Beta，1.20 新增）

数据路径插件允许外部组件在 Cilium 入口点周围运行自己的 BPF 程序，而无需 fork 数据路径。

- 使用 Helm `datapathPlugins.enabled=true` 启用（默认 false；agent flag 为 `--enable-datapath-plugins`）；状态目录为 `datapathPlugins.stateDir`（默认 `/var/run/cilium/plugins`）。
- 通过 `CiliumDatapathPlugin` CRD（`cilium.io/v2alpha1`）注册插件：`spec.attachmentPolicy: Always | BestEffort` 和 `spec.version`。
- agent 通过 gRPC 与各插件通信，socket 路径为 `<stateDir>/<name>/plugin.sock`，调用 `PrepareCollection` 和 `InstrumentCollection`。Cilium 会生成 dispatcher，使类型为 `BPF_PROG_TYPE_EXT`（freplace）的插件程序在 tc、XDP 和 cgroup sock hook 的 Cilium 入口程序之前或之后运行。
- 插件 Pod 需要 `SYS_ADMIN`。每次创建、更新或删除 plugin CR，都会完整重新初始化数据路径。不保证跨版本兼容。1.18 和 1.19 没有此功能。

目前应用于实验和供应商集成，不应作为生产变更的通用扩展点。

## 11. 实验

所有实验的前置条件：一个可丢弃的 Linux 集群，运行 Cilium 1.20.2 并启用了 kube-proxy replacement；可访问节点 Shell（SSM 或等效方式）及 `kubectl`。以下操作不会向集群外暴露内容。

### 实验 1：列出节点上的所有 Cilium 程序

1. 在节点上运行 `sudo bpftool net show` 和 `sudo bpftool prog show | grep cil_`。
2. 使用 `sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links` 列出 pin 的 link。
3. 运行 `kc cilium-dbg bpf sha list`。

预期结果：每个原生设备上都有 `cil_from_netdev`，每个 `lxc*` 设备上都有 `cil_from_container`，`cilium_host` 上有 `cil_to_host`/`cil_from_host`；使用 overlay 时，`cilium_vxlan` 或 `cilium_geneve` 上有 `cil_from_overlay`/`cil_to_overlay`。内核版本为 6.6 或更新时，每个端点都存在 link pin；更旧内核则可通过 `tc filter show dev <lxc> ingress` 查看传统 filter。清理：无需清理（只读）。

### 实验 2：策略变更不会触发重新编译

1. 记录 `kc cilium-dbg bpf sha list` 的输出，并通过 `kc cilium-dbg bpf policy get <ENDPOINT_ID>` 查看端点 map。
2. 应用 `CiliumNetworkPolicy`，允许带客户端标签的流量访问测试后端 TCP/80。
3. 再次运行上述两条命令。

预期结果：后端端点策略 map 中出现带有客户端数字身份的新 ingress 条目；模板列表不变。添加明确的 deny 规则，并观察带 deny 标志的条目。清理：删除策略对象。应在没有其他策略的命名空间中演练，因为集群级默认拒绝策略会相互影响。

### 实验 3：跟踪一次连接的 map 查询

1. 在测试命名空间中创建一个有两个副本的 Deployment、ClusterIP Service 和客户端 Pod。
2. 从客户端运行 `curl` 访问 ClusterIP；另开终端，在客户端所在节点上运行 `cilium-dbg monitor -t trace -t policy-verdict --related-to <CLIENT_ENDPOINT_ID>`。
3. 运行 `bpf lb list --frontends`、`--backends`，并运行 `bpf ct list global | grep <backend ip>`。
4. 比较客户端 netns 内 `tcpdump -ni eth0 port 80` 捕获结果和 Service IP。

预期结果：Service frontend 列出了各 backend；选中 backend 有对应 CT 条目；启用 socket-LB 时，抓包显示 backend IP 而不是 ClusterIP。可选：设置 `socketLB.hostNamespaceOnly=true` 后，抓包会显示 ClusterIP（逐包 LB）。此开关会改变整个集群的负载均衡方式，因此只应在测试集群应用，并通过恢复先前 Helm 值回滚。

### 实验 4：核对 Hubble 丢失事件

1. 在测试集群中将 `hubble.eventQueueSize` 设为刻意较小的值（回滚：恢复旧值，这会重启 agent）。
2. 在测试命名空间中使用流量工具产生负载。
3. 按 `source` 查询 agent 指标 `hubble_lost_events_total`。

预期结果：队列溢出时 `observer_events_queue` 增加，agent 日志出现“hubble events queue is full”。Perf-buffer 溢出则会显示为 `perf_event_ring_buffer`。

### 实验 5（进阶）：在新节点组上测试 netkit

仅在内核支持 netkit 的节点上进行。安装或升级一个新节点组，并设置 `bpf.datapathMode=auto`；随后通过 `cilium-dbg status` 检查 configured 与 operational mode，通过 `ip -d link show` 检查设备类型，并通过 `bpftool net show` 检查 netkit 挂载。如果同时设置 `bpf.tproxy=true` 和 netkit，1.19 及之后版本的 agent 会拒绝使用 netkit（`auto` 会回退到 veth）。回滚：不要原地切换现有 veth Pod；应排空并替换节点。

## 版本差异

| 项目 | 1.18.14 | 1.19.8 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|---|---|
| 最低内核版本（文档要求） | 5.10（RHEL 8.10 使用 4.18） | 5.10 | 5.10 | 5.10 |
| `bpf_network.c` | 存在 | 存在 | **已移除** | 已移除 |
| `CILIUM_CALL_SIZE` | 48 | 49 | 50 | 50 |
| 配置变量（grep 数量） | 18 | 43 | 73 | 104 |
| Policy map 名称 | `cilium_policy_v2_` | `cilium_policy_v2_` | `cilium_policy_v3_` | `cilium_policy_v3_`（auth 位保留） |
| Node map | v1 + v2 | 仅 v2 | v2 | v2 |
| Egress gateway map | `..._v4` | `..._v4` | `..._v4_v2` | `..._v4_v2` |
| `cilium_devices` map | 否 | 否 | 是 | 是 |
| `--datapath-mode` 取值 | veth、netkit、netkit-l2 | 相同 | 新增 `auto` | 新增 `auto` |
| `bpf.tproxy` | Beta（未发现 netkit 检查） | Beta；拒绝 netkit | Beta；拒绝 netkit | Beta；拒绝 netkit |
| 数据路径插件 | 否 | 否 | 是（Beta） | 是 |
| 双向认证 map（`--bpf-auth-map-max`） | 有 | 有 | 有；双向认证已弃用 | 已移除 |
| `--enable-bpf-stats` | 否 | 否 | 否 | 是 |
| `--node-port-mode`、`--node-port-algorithm` | 存在 | 存在 | 已移除（使用 `--bpf-lb-mode`、`--bpf-lb-algorithm`） | 已移除 |
| 策略拒绝时返回 ICMP | 否 | 否 | 是（tail 槽位 48–49） | 是 |

1.21 预发布代码树中的升级说明仍包含 1.20 的文本，因此目前还没有权威的 1.21 差异资料。

## 故障排查

| 症状 | 可能原因 | 检查方法 |
|---|---|---|
| 出现 `DROP_EP_NOT_READY`（代码 -203）丢弃 | 创建或删除端点期间策略槽位为空 | `cilium-dbg endpoint list`；端点变更时可能暂时出现，持续存在表示重新生成失败 |
| 出现 “Missed tail call” 丢弃 | 加载失败后数组未填充，或 commit 顺序错误 | 检查 agent 的加载错误日志；运行 `cilium-dbg endpoint log <id>`；重启 agent Pod |
| 新建连接失败，CT map 的 `cilium_bpf_map_pressure` 接近 1 | CT/NAT map 已满 | `cilium-dbg map list -v`；增大 `bpf.mapDynamicSizeRatio` 或显式上限；NAT 不能超过 CT 的 2/3；注意调整大小会丢失条目 |
| 扩容后 Service 不再匹配 | LB map 达到上限 | 检查 `bpf.lbMapMax`（影响六个 map）；调整会造成中断 |
| Agent 无法启动，并提示 “Require support for tcx links” 或 helper 错误 | 内核低于最低要求 | `uname -r`、`cilium-dbg status`；迁移到受支持的 AMI |
| 程序使用传统 tc 而不是 tcx | 内核低于 6.6 或 `enableTCX: false` | `bpftool net show`、`tc filter show` |
| netkit 被拒绝 | 缺少前置条件（host routing、BPF masquerade、KPR、tproxy 或内核能力） | 查看 agent 日志中的原因；在 `cilium-dbg status` 中比较 configured 与 operational mode |
| 加载时 verifier 拒绝程序 | 特殊功能组合或内核限制 | 查看 agent stderr 中的完整 verifier 日志；与通过测试的 5.10/6.1/net-next 构建比较 |
| `hubble observe` 漏掉流量 | perf-buffer 或 observer 队列丢失、聚合等级过高、ring 太小 | 按 `source` 检查 `hubble_lost_events_total`；检查 `bpf.monitorAggregation` 和 `hubble.eventBufferCapacity` |
| 旧指南要求导出 `cilium_tunnel_map` | 该 map 已移除 | 改用 `cilium-dbg bpf ipcache list` |
| 升级到 1.20 后，在关闭 socket-LB 或仅限 host namespace 时 Pod → NodePort 失败 | LB 现在在客户端 Pod 的 tc hook 上执行 | 在客户端 egress 和后端 ingress policy 中放行流量 |

## 验证限制和来源

本次审查没有在运行中的集群执行这些实验；命令和 flags 依据上游源码和文档核对。跟踪示例中的 ID、IP 和身份均为说明性数据。源码事实来自 Cilium v1.20.2 源码树（例如 `bpf/bpf_lxc.c`、`bpf/lib/tailcall.h`、`bpf/lib/policy.h`、`bpf/lib/eps.h`、`pkg/datapath/loader/tc.go`、`pkg/bpf/collection.go`、`Documentation/cmdref/cilium-agent.md`）；入口代码行号会随版本变化，应针对你使用的 tag 核实。尚未验证：agent 镜像是否包含 `bpftool`；引入 `bpf_sock_destroy` kfunc 的确切内核版本；**[1.21 预发布版]的** stats report 已从源码（`cilium-dbg/cmd/bpf_stats_report.go`）阅读，但未实际运行。

- Cilium v1.20.2 系统要求：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst
- Maps 参考：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/ebpf/maps.rst（注意：文档写的是 `cilium_ct_{4,6}_global`；实际名称为 `cilium_ct4_global` 和 `cilium_ct6_global`）
- BPF 源码：https://github.com/cilium/cilium/tree/v1.20.2/bpf
- 数据路径 loader：https://github.com/cilium/cilium/tree/v1.20.2/pkg/datapath/loader
- Agent flags：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/cmdref/cilium-agent.md
- 数据路径插件：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/contributing/development/plugins.rst
- 升级说明：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc
- 性能调优（netkit、BIG TCP）：https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst
- **[1.21 预发布版]** BPF stats：https://github.com/cilium/cilium/tree/v1.21.0-pre.3/pkg/bpf/stats

## 测验

通过[第 8 部分测验](../../quizzes/networking/cilium/08-ebpf-datapath-internals-quiz.md)检查对本章内容的理解。
