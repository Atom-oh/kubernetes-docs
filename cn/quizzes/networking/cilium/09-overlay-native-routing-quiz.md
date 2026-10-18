# 第 9 部分：Overlay 与原生路由深入测验

> **Cilium 1.20.2 · 2026-10-15**

## 隧道机制

1. **Cilium 会在封装报文的 24 位 VNI 中放入什么？**
   - A) 目标节点 ID
   - B) 发送端点的源安全身份
   - C) Cilium 集群 ID
   - D) 接收方通过 `cilium_tunnel_map` 映射的每节点随机值

   <details>
   <summary>显示答案</summary>

   **答案：**B) 发送端点的源安全身份

   VNI 携带源身份（`world-ipv4`/`world-ipv6` 会以 `world` 发送，`host` 会改写为 `remote-node`）。接收方也有 ipcache，因此 VNI 是一种优化手段，并非唯一可信来源。`cilium_tunnel_map` 在 1.18 中已从数据路径移除（Agent 只会取消固定残留的 map），其 Go 包在 1.19 中也已删除；隧道端点信息存放在 ipcache 值中。

   </details>

2. **关于 Cilium 中的身份传输，Geneve 与 VXLAN 有何不同？**
   - A) Geneve 通过 TLV 选项携带身份；VXLAN 通过 VNI 携带身份
   - B) Geneve 不携带身份；策略只在发送端评估
   - C) Geneve 使用外层 UDP 源端口携带身份
   - D) 二者相同：身份都在 VNI 中；Geneve 选项只用于 DSR 服务地址和端口

   <details>
   <summary>显示答案</summary>

   **答案：**D) 二者相同：身份都在 VNI 中；Geneve 选项只用于 DSR 服务地址和端口

   Cilium 插入的唯一 Geneve 选项（class `0x014B`，type `0x81`）用于 DSR。外层源端口范围（`tunnelSourcePortRange`）只影响熵，不参与身份传递。

   </details>

3. **隧道模式下，哪个组件会构建外层 UDP/IP 报头？**
   - A) `bpf_lxc` 程序，它会将报头写入报文
   - B) 用户空间中的 cilium-agent
   - C) 流量型 `cilium_vxlan`/`cilium_geneve` 设备后面的内核 vxlan/geneve 驱动；BPF 设置隧道键并重定向到该设备后，由驱动封装
   - D) NIC 固件

   <details>
   <summary>显示答案</summary>

   **答案：**C) 流量型 `cilium_vxlan`/`cilium_geneve` 设备后面的内核 vxlan/geneve 驱动；BPF 设置隧道键并重定向到该设备后，由驱动封装

   BPF 调用 `bpf_skb_set_tunnel_key` 并重定向到隧道设备的 ifindex；封装由内核驱动完成。在接收端，内核负责解封装，然后 `cil_from_overlay` 读取隧道键。

   </details>

4. **在 Cilium 1.20.2 中同时设置 `routingMode: tunnel` 和 `autoDirectNodeRoutes: true` 会发生什么？**
   - A) Agent 会因报文必须经过隧道设备而以致命错误退出
   - B) Cilium 会在同一子网内使用直连路由，在不同子网间使用隧道
   - C) 该标志会被忽略并记录警告
   - D) Cilium 会回退到原生路由

   <details>
   <summary>显示答案</summary>

   **答案：**A) Agent 会因报文必须经过隧道设备而以致命错误退出

   检查逻辑位于 `daemon_main.go` 中的 `TunnelingEnabled() && EnableAutoDirectRouting`。不存在按子网回退的行为。v1.21.0-pre.3 中的消息措辞为“requires native routing mode”，但仍会导致致命错误。

   </details>

## MTU、伪装和主机路由

5. **底层网络 MTU 为 1500 字节，使用 IPv4 底层网络，并同时启用 VXLAN 和 WireGuard 时，Pod 会看到什么路由 MTU？**
   - A) 1450
   - B) 1405
   - C) 1373
   - D) 1355

   <details>
   <summary>显示答案</summary>

   **答案：**D) 1355

   路由 MTU 等于基础 MTU 减去 WireGuard 95 字节和隧道 50 字节。单独使用 VXLAN 时为 1450；原生路由搭配 WireGuard 时为 1405；VXLAN 搭配 IPsec（50 + 77）时为 1373。

   </details>

6. **在 `routingMode: tunnel` 下使用 DSR，需要什么配置？**
   - A) 使用 `dsrDispatch: opt` 的 VXLAN
   - B) 设置 `tunnelProtocol: geneve` 和 `loadBalancer.dsrDispatch: geneve`
   - C) 使用 `loadBalancer.mode: hybrid` 的 VXLAN
   - D) 使用任意隧道协议，设置 `dsrDispatch: ipip`，无需其他修改

   <details>
   <summary>显示答案</summary>

   **答案：**B) 设置 `tunnelProtocol: geneve` 和 `loadBalancer.dsrDispatch: geneve`

   Agent 会拒绝使用 VXLAN 隧道时的 `dsr`/`hybrid`，隧道模式下的 DSR 要求 Geneve dispatch，而 Geneve dispatch 又要求使用 Geneve 隧道协议。

   </details>

7. **在不支持 netkit 的内核节点上设置 `bpf.datapathMode: auto` 会发生什么？**
   - A) Agent 无法启动
   - B) Agent 会切换到 `netkit-l2`
   - C) Agent 会回退到 veth 并记录警告；显式设置 `netkit` 则会直接失败
   - D) Agent 会持续重试 netkit 并阻止创建 Pod

   <details>
   <summary>显示答案</summary>

   **答案：**C) Agent 会回退到 veth 并记录警告；显式设置 `netkit` 则会直接失败

   `auto`（1.20 新增）会进行探测，并记录“datapath autodiscovery failed, reverting from netkit to veth”后回退。Netkit 还需要 BPF masquerade、KPR，并且不能使用旧式主机路由。

   </details>

8. **BPF 主机路由是默认配置，但在启用 kube-proxy replacement 时仍使用 iptables masquerade。Agent 会怎样处理？**
   - A) 记录 BPF 主机路由需要 BPF masquerade，然后静默回退到旧式主机路由
   - B) 拒绝启动
   - C) 自动启用 BPF masquerade
   - D) 禁用 kube-proxy replacement

   <details>
   <summary>显示答案</summary>

   **答案：**A) 记录 BPF 主机路由需要 BPF masquerade，然后静默回退到旧式主机路由

   主机路由属于尽力启用的功能。明确要求使用主机路由的功能（netkit、Pod 的 BBR、BIG TCP）如果无法启用，则会直接失败。可通过 `cilium-dbg status` 中 `Routing:` 行的 `Host:` 字段进行验证（`Host: Legacy`）。

   </details>

9. **启用带宽管理器后，`kubernetes.io/egress-bandwidth: "10M"` 会将 Pod 限制到什么速率？**
   - A) 10 MB/s
   - B) 每个副本集 10 Mbit/s
   - C) 什么也不限制，除非同时启用 BBR
   - D) 10 Mbit/s

   <details>
   <summary>显示答案</summary>

   **答案：**D) 10 Mbit/s

   该值是以 bit 为单位的 Kubernetes quantity。每个 Pod 的出站流量使用 EDT 和 FQ 强制执行；BBR 是可选项。使用 IPsec 时，带宽管理器会被静默禁用。

   </details>

10. **使用 BPF masquerade 和默认设置时，Pod 到远程节点的流量如何处理？**
    - A) 始终进行 masquerade
    - B) 永远不进行 masquerade
    - C) 原生路由模式下不进行 masquerade，隧道模式下会进行 masquerade（除非 ipcache 条目中有 `skip_tunnel`）
    - D) 仅当目标位于 RFC1918 地址范围之外时才进行 masquerade

    <details>
    <summary>显示答案</summary>

    **答案：**C) 原生路由模式下不进行 masquerade，隧道模式下会进行 masquerade（除非 ipcache 条目中有 `skip_tunnel`）

    这是 `bpf/lib/nat.h` 中决策顺序的第 5 步。设置 `enable-remote-node-masquerade=true`（1.19+，通过 `extraConfig` 配置）后，两种模式都会执行 masquerade。

    </details>
