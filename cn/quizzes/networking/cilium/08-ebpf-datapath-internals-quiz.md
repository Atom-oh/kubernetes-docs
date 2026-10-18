# 第 8 部分：eBPF 数据路径内部机制测验

> **Cilium 1.20.2 · 2026-10-15**

1. **在 Cilium 1.20 中，内核支持时每设备程序使用哪种挂载机制？如果内核不支持会怎样？**
   - A) 始终使用传统 `clsact` 过滤器；tcx 仅用于 netkit
   - B) 使用 tcx `bpf_link`（内核 6.6 或更高版本）；否则使用 `clsact` + `cls_bpf` direct-action
   - C) 在每个 veth 上使用 XDP；否则代理会拒绝启动
   - D) 在每个接口上使用 cgroup hook；否则使用 iptables

   <details>
   <summary>显示答案</summary>

   **答案：B) 使用 tcx `bpf_link`（内核 6.6 或更高版本）；否则使用 `clsact` + `cls_bpf` direct-action**

   `bpf.enableTCX` 默认值为 true。该链接会固定在 `/sys/fs/bpf/cilium/...` 下，并在重新加载时以原子方式更新。只有在 tc-bpf 和 tcx 均不可用时，代理才会失败。

   </details>

2. **同一节点上 Pod 到 Pod 的流量使用 BPF 主机路由和 `bpf_redirect_peer`。目标 Pod 的入站策略在哪里强制执行？**
   - A) 在发送方的 `bpf_lxc` 程序中，该程序会 tail-call `cilium_call_policy[destination endpoint ID]`
   - B) 在目标 veth 的 tc egress hook 中，使用为发送方端点固定的策略映射
   - C) 在目标 netns 的 iptables 链中，由代理为每个端点安装
   - D) 在数据包到达任何 veth 之前，由节点 NIC 上的 XDP 程序执行

   <details>
   <summary>显示答案</summary>

   **答案：A) 在发送方的 `bpf_lxc` 程序中，该程序会 tail-call `cilium_call_policy[destination endpoint ID]`**

   `redirect_peer` 会跳过目标的 tc egress hook，因此目标的 `cil_lxc_policy` 存储在全局 prog array 中，并由发送方调用。空槽会产生 `DROP_EP_NOT_READY`。

   </details>

3. **每个端点的策略映射 `cilium_policy_v3_<id>` 类型是什么，键由哪些字段组成？**
   - A) 以远端 Pod IP 地址和目标端口为键的 HASH
   - B) 以端口号为索引、每种协议占一个槽位的 ARRAY
   - C) 以策略规则编号为索引、每条规则 tail-call 一个程序的 PROG_ARRAY
   - D) 以身份、方向、协议和端口前缀为键的 LPM_TRIE

   <details>
   <summary>显示答案</summary>

   **答案：D) 以身份、方向、协议和端口前缀为键的 LPM_TRIE**

   键包含 `sec_label`、一个 `egress` 位、`protocol` 和 `dport`。端口前缀可以用少量条目存储端口范围，而 `sec_label` 为 0 时表示 L3 通配符。

   </details>

4. **某教程建议在 Cilium 1.20 中检查 `cilium_tunnel_map`，以查找 overlay 目标的远端节点。正确做法是什么？**
   - A) 使用 `cilium-dbg bpf tunnel list` 导出节点到端点的映射表
   - B) 该映射存在，但只有在启用 IPsec 或 WireGuard 加密时才会填充
   - C) 该映射已不存在；隧道端点现在是 `cilium_ipcache_v2` 值中的一个字段
   - D) 该映射现在按端点区分，名为 `cilium_tunnel_map_<id>`，每个节点对应一个条目

   <details>
   <summary>显示答案</summary>

   **答案：C) 该映射已不存在；隧道端点现在是 `cilium_ipcache_v2` 值中的一个字段**

   1.20 的 BPF 代码中没有引用 `cilium_tunnel_map`。`cilium_ipcache_v2`（LPM_TRIE）会返回带有 `flag_has_tunnel_ep` 的 `sec_identity` 和 `tunnel_endpoint`。使用 `cilium-dbg bpf ipcache list`。

   </details>

5. **1.20.2 中 `--bpf-map-dynamic-size-ratio` 的默认值是什么？它会调整哪些映射的大小？**
   - A) RAM 的 0.0025；CT、NAT、NodePort neighbor 和 socket reverse-NAT 映射
   - B) 0（禁用）；仅策略映射，由 `--bpf-policy-map-max` 调整大小
   - C) RAM 的 0.25；所有 BPF 映射，包括 LB 映射和 ipcache
   - D) RAM 的 0.0025；仅 ipcache 和策略映射

   <details>
   <summary>显示答案</summary>

   **答案：A) RAM 的 0.0025；CT、NAT、NodePort neighbor 和 socket reverse-NAT 映射**

   默认启用动态调整大小。设置 `--bpf-ct-global-tcp-max` 等大小标志后，只会为相应映射禁用动态调整。LB 映射使用 `--bpf-lb-map-max`。

   </details>

6. **`--bpf-lb-map-max`（默认值为 65536）控制什么？**
   - A) 仅控制 `cilium_lb4_services_v2` 映射，后端和 rev-NAT 映射仍使用各自默认值
   - B) 每个 Service 的后端数量，超过后会拒绝额外端点
   - C) Maglev 查找表大小，且必须是固定列表中的质数
   - D) 六个逐 LB 映射标志（services、backends、rev-NAT、affinity、source-range、Maglev）的回退大小

   <details>
   <summary>显示答案</summary>

   **答案：D) 六个逐 LB 映射标志（services、backends、rev-NAT、affinity、source-range、Maglev）的回退大小**

   六个逐映射标志的默认值均为 0，表示“使用 `lb-map-max`”。Maglev 表大小由单独的标志控制。调整大小会重建映射，直到重新填充前会中断连接。

   </details>

7. **启用 socket-LB 时，ClusterIP 在哪里转换？应用如何在回复中仍看到 Service 地址？**
   - A) 每个数据包都在 veth 处执行 DNAT；回复路径由 `cilium_lb4_reverse_nat` 还原
   - B) 通过 cgroup hook 在 `connect()`/`sendmsg()` 时转换；`recvmsg`/`getpeername` hook 使用 `cilium_lb4_reverse_sk` 还原
   - C) 由主机 netns 中 kube-proxy 的 iptables 执行 DNAT；conntrack 还原原始地址
   - D) 在协议栈看到数据包前由 NIC 上的 XDP 转换；由 Hubble relay 还原

   <details>
   <summary>显示答案</summary>

   **答案：B) 通过 cgroup hook 在 `connect()`/`sendmsg()` 时转换；`recvmsg`/`getpeername` hook 使用 `cilium_lb4_reverse_sk` 还原**

   线路上不会发生 DNAT，因此 Pod 内的 `tcpdump` 会显示后端 IP。仅在 socket-LB 不适用时（例如仅限主机命名空间模式、L7 LB、SCTP），才会使用通过 `cilium_lb4_reverse_nat` 进行的逐数据包路径。

   </details>

8. **overlay 模式下，数据包到达 `cilium_vxlan`。`cil_from_overlay` 如何获知源身份？**
   - A) 使用 `bpf_skb_get_tunnel_key` 读取隧道 ID（VNI），该值由发送方设置为其源身份
   - B) 在 `cilium_lxc` 中查找外层源 IP，该映射会将节点 IP 对应到身份
   - C) 读取本地 Envoy 代理注入请求中的 HTTP 标头
   - D) 使用端点标签缓存，根据源 Pod 名称解析身份

   <details>
   <summary>显示答案</summary>

   **答案：A) 使用 `bpf_skb_get_tunnel_key` 读取隧道 ID（VNI），该值由发送方设置为其源身份**

   如果隧道 ID 中包含主机身份，则会被 `DROP_INVALID_IDENTITY` 拒绝。原生路由模式没有 VNI，因此源身份来自 `cilium_ipcache_v2` 中按源 IP 查找的结果（或在 IPsec/WireGuard 模式下来自标记）。

   </details>

9. **管理员编辑了 CiliumNetworkPolicy。代理会如何更新数据路径？**
   - A) 对每个受影响端点使用 clang 重新编译 `bpf_lxc.c`，并在其 veth 上重新加载程序
   - B) 替换所有设备上固定的 tcx 链接，使新策略原子生效
   - C) 更新 `cilium_policy_v3_<id>` 中的条目；只有端点或节点配置哈希发生变化时才会重新加载程序
   - D) 重启 Cilium 代理 Pod，使所有端点重新生成程序

   <details>
   <summary>显示答案</summary>

   **答案：C) 更新 `cilium_policy_v3_<id>` 中的条目；只有端点或节点配置哈希发生变化时才会重新加载程序**

   策略变更通过映射操作进行（`RegenerateWithoutDatapath`）。模板对象会按模板配置哈希缓存，每个端点的值位于 `.rodata.config` 中。

   </details>

10. **关于 1.20 中的 Hubble 事件流水线，哪项说法正确？**
    - A) BPF 写入 ring buffer，Hubble Relay 直接从每个节点的 BPF 文件系统读取
    - B) 事件进入 `cilium_events`（perf array），然后经过代理 monitor 和 Hubble 队列，进入内存 ring（4095 个 flow）
    - C) 代理会将 flow 持久化到磁盘，并在重启后重放给 Hubble Relay
    - D) L7 事件由 `bpf_lxc` tail 程序在代理重定向映射匹配时发出

    <details>
    <summary>显示答案</summary>

    **答案：B) 事件进入 `cilium_events`（perf array），然后经过代理 monitor 和 Hubble 队列，进入内存 ring（4095 个 flow）**

    丢失可能发生在 perf buffer（`perf_event_ring_buffer`）或 observer 队列（`observer_events_queue`）。L7 记录由 Envoy 和 DNS 代理作为代理事件生成，而不是由 BPF 生成。

    </details>
