# 网络基础知识第 1 部分测验：分层模型、链路与路由

> **最后更新**：2026 年 9 月 14 日

测试你对 11 种链路层和互联网/路由层协议与机制的理解。

## 选择题

1. 在 VPN 或覆盖网络上遇到“ping 正常，但大型响应会挂起”的故障时，首先应怀疑什么？
   - A) DNS TTL 过长
   - B) 封装标头降低有效 MTU，并且 ICMP 被阻止（MTU 黑洞）
   - C) TCP 拥塞控制算法不匹配
   - D) ARP 缓存过期

<details>
<summary>显示答案</summary>

**答案：B) 封装标头降低有效 MTU，并且 ICMP 被阻止（MTU 黑洞）**

**说明：**
封装会降低路径上可容纳的内层数据包大小。设置 DF 标志的 IPv4 数据包不能由路由器分片；传统 PMTUD 需要 ICMP Type 3 Code 4。IPv6 路由器从不分片，而是使用 ICMPv6 Packet Too Big（Type 2）。阻止这些消息可能导致黑洞，但 PLPMTUD 可以在不依赖 ICMP 的情况下探测数据包大小。

</details>

2. 在基于 VIP 的高可用设置中，发生故障转移后，新的活动节点为什么要立即发送 Gratuitous ARP？
   - A) 向 DHCP 服务器重新注册其 IP 地址
   - B) 刷新交换机的 MAC 表和相邻主机的 ARP 缓存，使其指向新节点
   - C) 强制网关重新计算路由表
   - D) 重新协商 TLS 会话

<details>
<summary>显示答案</summary>

**答案：B) 刷新交换机的 MAC 表和相邻主机的 ARP 缓存，使其指向新节点**

**说明：**
VIP 保持不变，但其所有者或 MAC/端口位置发生变化。Gratuitous ARP 会向邻居通告 IP 到 MAC 的映射，同时交换机可以在新端口学习源 MAC。有些高可用设计会保留相同的虚拟 MAC。如果刷新延迟，故障转移切换就会变慢。

</details>

3. 哪项最准确地描述了 OSPF 与 BGP 的区别？
   - A) OSPF 基于策略选择路径，而 BGP 专注于最短路径计算
   - B) OSPF 用于自治系统间路由，而 BGP 用于自治系统内路由
   - C) OSPF 在自治系统内使用 Dijkstra 算法计算最短路径，而 BGP 根据策略选择自治系统间的路径
   - D) 两者都是链路状态协议，区别仅在于使用场景

<details>
<summary>显示答案</summary>

**答案：C) OSPF 在自治系统内使用 Dijkstra 算法计算最短路径，而 BGP 根据策略选择自治系统间的路径**

**说明：**
OSPF 是链路状态型 IGP：区域中的每台路由器共享相同的拓扑，并据此计算最短路径。BGP 是路径向量协议，会使用 AS_PATH、Local Preference 和 MED 等属性，选择“路径策略偏好的路径”。Direct Connect 使用 BGP；Site-to-Site VPN 在受支持的配置中支持 BGP 或静态路由。BGP 也有自治系统内的 iBGP 会话。

</details>

4. 哪项最能解释为什么说 NAT“违反了分层模型”？
   - A) 因为它会直接修改链路层帧
   - B) 因为它是会改写 L4 端口的 L3 设备，破坏了端到端连通性的前提
   - C) 因为它会解密加密的数据包
   - D) 因为它不使用路由表

<details>
<summary>显示答案</summary>

**答案：B) 因为它是会改写 L4 端口的 L3 设备，破坏了端到端连通性的前提**

**说明：**
端口转换 NAT（PAT/NAPT）不仅会改写 IP 地址，还会改写端口，并依赖逐会话映射表。因此，直接的 P2P 连接变得困难，而 WebRTC 会通过 STUN/TURN（ICE）来处理这一问题。在云环境中，实际问题包括 NAT Gateway 端口耗尽和数据处理费用。

</details>

5. 组织通过双栈方式采用 IPv6 时，应检查哪项安全缺口？
   - A) IPv6 不支持加密
   - B) 只维护了 IPv4 防火墙规则，缺少 IPv6 路径规则
   - C) IPv6 地址更容易被扫描
   - D) SLAAC 会禁用 DHCP 服务器

<details>
<summary>显示答案</summary>

**答案：B) 只维护了 IPv4 防火墙规则，缺少 IPv6 路径规则**

**说明：**
双栈意味着需要维护两套防火墙规则和安全策略。缺失 IPv6 规则是一种风险，但仅有 IPv6 地址并不代表该地址可以从互联网访问。路由、安全组和 NACL 仍然适用；仅出站互联网网关可以阻止非请求发起的 IPv6 入站连接。

</details>

6. 对于普通 IPv4 广播子网上的 `192.0.2.130/26`，哪组网络地址、广播地址和主机范围正确？
   - A) 网络地址 `.0`，广播地址 `.255`，主机为 `.1`–`.254`
   - B) 网络地址 `.130`，广播地址 `.193`，主机为 `.131`–`.192`
   - C) 网络地址 `.128`，广播地址 `.191`，主机为 `.129`–`.190`
   - D) 网络地址 `.128`，广播地址 `.190`，主机为 `.129`–`.189`

<details>
<summary>显示答案</summary>

**答案：C) 网络地址 `.128`，广播地址 `.191`，主机为 `.129`–`.190`**

**说明：**
子网掩码为 `255.255.255.192`。6 个主机位提供 64 个地址，而 `.130` 位于 `.128`–`.191` 这个地址块中。扣除网络地址和广播地址后，剩余 62 个普通主机地址。这里所有地址都共享 `192.0.2` 前缀，属于文档示例地址。

</details>

7. 主机 `192.0.2.130/26` 有一条通往其子网的直连路由。其已选路由表还包含经由 `.129` 的 `198.51.100.0/24`、经由 `.190` 的 `198.51.100.128/25`，以及经由 `.129` 的默认路由（网关均位于 `192.0.2` 网段）。对于目标 `198.51.100.140`，如果邻居项不存在，会使用哪条路由以及哪个 ARP 目标？
   - A) 默认路由；ARP 查询 `192.0.2.129`
   - B) `/25` 路由；ARP 查询 `192.0.2.190`
   - C) `/24` 路由；ARP 查询 `198.51.100.140`
   - D) `/25` 路由；ARP 查询 `198.51.100.140`

<details>
<summary>显示答案</summary>

**答案：B) `/25` 路由；ARP 查询 `192.0.2.190`**

**说明：**
三条远程路由都匹配，但 `/25` 前缀最长。ARP 会解析链路上的网关，因此帧会发送到该网关的 MAC 地址，而 IP 目标仍为 `198.51.100.140`（未发生 NAT 时）。较低的默认路由度量值不会覆盖更具体的匹配项。

</details>

8. 主机 `192.0.2.130/26` 有一条直连的 `192.0.2.128/26` 路由，以及一条经由 `192.0.2.129` 的默认路由。没有更具体的路由或已缓存的邻居项时，它如何向 `192.0.2.150` 发送数据？
   - A) 对 `192.0.2.150` 发送 ARP 请求，然后直接发送到其 MAC 地址
   - B) 对 `192.0.2.129` 发送 ARP 请求，因为所有 IP 流量都需要经过网关
   - C) 对 `192.0.2.191` 发送 ARP 请求，然后广播 IP 数据包
   - D) 不指定任何链路层目标，直接发送到默认网关

<details>
<summary>显示答案</summary>

**答案：A) 对 `192.0.2.150` 发送 ARP 请求，然后直接发送到其 MAC 地址**

**说明：**
选定的 `/26` 路由将该目标标记为链路上目标。目标主机本身就是下一跳。只有在路由查找选中默认路由时，才会使用已配置的默认网关；仅仅配置了网关，并不会强制本地流量经过它。

</details>

9. 哪项说法正确处理了普通“总地址数减二”计算的例外情况？
   - A) `/31` 始终没有可用端点
   - B) `/32` 始终提供一个主机地址和一个独立的网关地址
   - C) 每个云环境中的 `/26` 都允许分配全部 62 个普通主机地址
   - D) 受支持的点对点 `/31` 会使用两个地址；`/32` 标识单个地址；云环境的地址保留规则需单独检查

<details>
<summary>显示答案</summary>

**答案：D) 受支持的点对点 `/31` 会使用两个地址；`/32` 标识单个地址；云环境的地址保留规则需单独检查**

**说明：**
RFC 3021 允许将 `/31` 的两个地址用作点对点端点。`/32` 主机路由只匹配一个地址，本身并不能建立链路上可达性。标准 AWS VPC IPv4 子网会保留 5 个地址，因此 `/26` 有 59 个可分配地址；BYOIP 等模式遵循不同规则。

</details>

10. UDP traceroute 先从中间路由器收到 ICMP Type 11 Code 0，之后从目标收到 Type 3 Code 3。这通常表示什么？
   - A) 某个探测包在传输途中 TTL 过期；后续探测包到达目标处一个未使用的 UDP 端口
   - B) 目标在每一跳都返回了 UDP 数据
   - C) 路由器报告了路径 MTU 问题，随后目标完成了 TLS
   - D) traceroute 会静默地将所有出站探测包改为 ICMP Echo Request

<details>
<summary>显示答案</summary>

**答案：A) 某个探测包在传输途中 TTL 过期；后续探测包到达目标处一个未使用的 UDP 端口**

**说明：**
探测协议和响应协议不同：UDP 探测包可以触发 ICMP 错误。ICMP Echo 和 TCP SYN traceroute 变体在中间跳也会收到 Time Exceeded，但最终响应可以是 Echo Reply 或 TCP SYN/ACK/RST。Fragmentation Needed 是 Type 3 Code 4，并非本题中的任一代码。

</details>

11. traceroute 的某一跳显示 `* * *`，但后续跳和目标都有响应。可以得出哪项结论？
   - A) 静默的路由器会丢弃所有端到端流量
   - B) 等待期间没有收到与这些探测包匹配的响应；要断定存在端到端丢包还需要更多证据
   - C) 正向路径和返回路径相同
   - D) 所有应用数据包大小都适合该路径 MTU

<details>
<summary>显示答案</summary>

**答案：B) 等待期间没有收到与这些探测包匹配的响应；要断定存在端到端丢包还需要更多证据**

**说明：**
过滤、抑制响应/速率限制或返回路径上的丢包都可能造成超时。应将重复探测结果与目标端及应用层结果进行比较。RTT 包含返回路径，而且小探测包成功并不能排除较大数据包遇到 PMTU 黑洞。

</details>

---

[返回学习材料](../../basics/06-network-fundamentals-part1.md) | [下一个测验：第 2 部分](./06-network-fundamentals-part2-quiz.md)

请复习 [CIDR 示例](../../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet)、[下一跳判断](../../basics/06-network-fundamentals-part1.md#longest-prefix-next-hop)和 [ICMP 解读](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation)，包括其中引用的主要参考资料。

## 验证参考资料

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html
- https://www.rfc-editor.org/rfc/rfc894
- https://www.rfc-editor.org/rfc/rfc6691
- https://www.rfc-editor.org/rfc/rfc4638
- https://www.rfc-editor.org/rfc/rfc5227
- https://www.rfc-editor.org/rfc/rfc792
- https://www.rfc-editor.org/rfc/rfc8899
- https://www.rfc-editor.org/rfc/rfc2328
- https://www.rfc-editor.org/rfc/rfc6811
- https://docs.kernel.org/networking/bridge.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html
- https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
