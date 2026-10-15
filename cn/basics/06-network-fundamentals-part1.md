# 网络基础第 1 部分 —— 分层模型、链路层与路由层

> **最后更新**: September 14, 2026

::: tip 这是一个四部分系列
**第 1 部分：分层模型、链路层与路由层** *(本文档)* ·
[第 2 部分：传输层与 TLS](./06-network-fundamentals-part2.md) ·
[第 3 部分：应用协议](./06-network-fundamentals-part3.md) ·
[第 4 部分：一次请求的旅程与云](./06-network-fundamentals-part4.md)
:::

浏览器请求依赖多个相互协作的协议。确切顺序取决于缓存、连接复用、IP 版本和 HTTP 版本，因此排查问题时不能只检查 HTTP。

本系列将按**自底向上、逐层**讲解 25 种网络协议和机制。从底层开始构建的原因很简单：每一层的设计都假定其下层已经正常工作。自顶向下阅读时，你会不断遇到“但*那一部分*是如何工作的？”的问题。

每个条目均遵循相同结构：**一句话定义 → 工作原理 → 实践中的影响**。

---

## 0. 一页分层图

| 层 | 职责 | 此处涵盖的协议 |
|---|---|---|
| 应用 | 实际服务语义 | HTTP/3, WebSocket, WebRTC, gRPC, DNS, DoH, DHCP, MQTT, SSH, SMTP |
| 安全 | 加密和认证（运行于传输层之上） | TLS |
| 传输 | 端到端数据传递 | TCP, UDP, QUIC |
| Internet / 路由 | 选择网络之间的路径 | IPv4, IPv6, ICMP, BGP, OSPF, NAT |
| 链路 | 在同一物理网段内传递 | Ethernet, Wi-Fi, VLAN, PPP, ARP |

有些条目不遵循清晰的分层边界。TLS 卡在传输层与应用层之间，QUIC 运行在 UDP 之上却承担传输层的工作，而 ARP 连接 IP 与链路层。NAT 与其说是一种协议，不如说是一项功能。这些“例外”涵盖了现实世界中大多数排障场景。

---

![展示了从笔记本电脑经由 L2 交换机和家庭路由器到 ISP 边缘、由 BGP 驱动的互联网核心、OSPF 数据中心路由器，最终到达服务器的链路层/路由层路径，并标出各网段的协议和 MTU。](../.gitbook/assets/en-basics-06-network-fundamentals-part1-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part1-0.html)

---

## 1. 链路层 —— 在同一网段内移动比特

链路层只关心一件事：**如何将比特交给紧邻你的设备。**无论最终目的地是下一排机架还是地球的另一端，这一层只负责下一跳。

### Ethernet

**定义：**在有线局域网中承载帧的链路层标准。

**工作原理：**数据被封装为帧，前部带有目的和源 MAC 地址。对于已知单播，交换机使用其 MAC 表选择目的端口。广播和未知单播帧通常在 VLAN 内泛洪；多播行为取决于配置。早期 Ethernet 依赖冲突检测（CSMA/CD），但在现代交换式全双工网络中，冲突实际上已消失。

**实践中：**对于 Ethernet IP 流量，MTU 为 1500 意味着帧内有一个 1500 字节的 IP 数据包，不包括 Ethernet 头部/FCS。巨型 MTU 取决于设备/路径；9001 是 EC2 支持的值，而非通用的 Ethernet 大小。在云中，在其上叠加 VPN 或覆盖网络会增加封装头，从而缩小有效 MTU；MTU 发现失败可能造成黑洞，表现为“ping 正常，但大响应挂起”。这是最难诊断的故障模式之一。

**MTU 与 MSS：**MSS 限制的是 TCP 数据字节，而不是完整帧。对于 MTU 1500，基础头部计算得出 IPv4 为 1460（1500−20−20），IPv6 为 1440（1500−40−20）。发送端还会因其包含的任何 IP/TCP 选项而进一步减少实际数据量。TCP 会在握手期间交换 MSS，因此当 MTU 问题在隧道中反复出现时，在路由器上进行 MSS 钳制（强制使用较低的 TCP MSS）是一种广泛使用的变通方案。

### Wi-Fi

**定义：**通过无线网段承载 LAN 帧的链路层标准（IEEE 802.11）。

**工作原理：**由于空中是共享介质，Wi-Fi 与 Ethernet 有根本区别。Wi-Fi 在传输时避免依赖冲突检测，而使用 CSMA/CA：发送前检查信道是否空闲，然后对普通单播流量使用 ACK/重试；广播/多播行为则不同。换言之，重传已内置于链路层。

**实践中：**叠加在 TCP 重传之上的链路层重传会增大延迟波动（jitter）。实际问题出在客户端无线网段时，实时质量问题却常被归咎为“服务器的问题”。仅凭服务器 RTT 无法定位原因；应将其与应用处理时间以及客户端/AP 重试、信号和队列指标关联分析。

### VLAN

**定义：**将共享交换机基础设施划分为逻辑 L2 网络的技术（IEEE 802.1Q）。

**工作原理：**带有 802.1Q 标签的帧携带一个 4 字节 VLAN 标签。接入端口可承载未打标签的帧，由交换机将其分配给某个 VLAN。广播只会到达同一 VLAN 内的主机，因此无需改动布线即可划分网络。VLAN 之间的流量必须通过 L3 设备（路由器或 L3 交换机）。

**实践中：**VLAN 提供逻辑 L2 分段，而非物理隔离或加密隔离。路由和防火墙控制决定允许的跨网段流量。VPC、子网和安全组承担不同的云网络角色；它们并非 VLAN 的一一对应替代品。

> 📎 有关 EKS 如何构建其 VPC，请参阅 [EKS 网络基础](../eks/03-eks-networking-part1.md)。

### PPP

**定义：**一种在恰好连接两个节点的点对点链路上传输数据包的协议。

**工作原理：**与 Ethernet 不同，无需寻址——链路每端只有一个节点。相反，PPP 提供链路建立、可选认证和上层协议协商（LCP/NCP）。

**实践中：**它看似是拨号时代的遗物，但作为 PPPoE 仍存在于很大比例的家庭互联网线路中。对于标准的 1500 字节 Ethernet 负载，通常的 6 字节 PPPoE 头部加 2 字节 PPP 协议字段会为 IP 留下 1492 字节；经过协商的更大底层网络可保留 1500。未被考虑的降至 1492 可能导致上述 MTU 问题。

### ARP

**定义：**将链路内 IPv4 下一跳地址解析为 MAC 地址的协议。

**工作原理：**IP 层会说“将此发送到 10.0.1.5”，但 Ethernet 只理解 MAC 地址。因此主机会广播“谁拥有 10.0.1.5？”，拥有该地址的主机会响应。结果会以操作系统特定的邻居状态/超时值进行缓存。对于链路外目的地，主机解析的是其网关的 MAC，而非远程主机的 MAC。

**实践中：**ARP 没有认证。任何人都可以回答“那个 IP 是我的”，这正是 ARP 欺骗成为可能的原因。相同属性也有合法用途：故障转移时，新的活动节点会广播 Gratuitous ARP，向邻居宣布 VIP 到 MAC 的映射；交换机也会从帧中学习源 MAC 的位置。当基于 VIP 的 HA 设置故障转移缓慢时，缓存刷新延迟是首要怀疑对象。

> 📎 有关 Cilium 如何将 L2/路由行为与 eBPF 集成，请参阅 [Cilium 网络](../networking/cilium/03-networking.md)。

---

## 2. Internet 与路由层 —— 跨越网络

如果链路层让你到达“隔壁”，这一层让你到达“地球另一端”。核心问题是：**这个数据包下一步应去哪里？**

### IPv4

**定义：**基于 32 位地址的 Internet 层协议。

**工作原理：**每个数据包携带源和目的 IP；每台路由器在其路由表中查找最具体的路由（最长前缀匹配），然后转发至下一跳。传递是尽力而为的——不保证可靠性，也不保证顺序。这些保证由上一层（TCP）负责。

**实践中：**IPv4 大约有 43 亿个可用地址，地址稀缺使 NAT 被广泛使用，并使私有地址范围（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）成为内部网络标准。大型组织在云迁移期间遇到的第一堵墙，是这些私有地址范围的重叠：本地/VPC CIDR 重叠会阻止通过 VPN 或 Direct Connect 直接路由，除非设计重新编号、转换或代理方案。IP 地址设计应在项目启动时确定。

#### IPv4、CIDR 和一个子网示例 {#ipv4-cidr-subnet}

IPv4 有四个 8 位八位组。在 CIDR 表示法中，`/26` 将前 26 位固定为网络前缀，并留下 `32 − 26 = 6` 个主机位。以下地址是来自 [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) 的文档示例，而不是公开测试端点。

对于接口地址 **`192.0.2.130/26`**：

| 步骤 | 计算或结果 |
|---|---|
| 子网掩码 | `255.255.255.192`；最后一个八位组的二进制为 `11000000` |
| 每个块中的地址数 | `2^6 = 64`；最后一个八位组的块从 `0`、`64`、`128`、`192` 开始 |
| 网络地址 | `130 AND 192 = 128`（`10000010 AND 11000000 = 10000000`），因此为 `192.0.2.128/26` |
| 广播地址 | 将六个主机位设为 1：`192.0.2.191` |
| 普通主机范围 | `192.0.2.129`–`192.0.2.190`：62 个地址 |

该接口拥有 `.130`；`.128/26` 标识其子网。在普通广播子网中，全零和全一主机部分分别标识网络地址和广播地址。若已配置网关，它会占用主机范围内的一个地址；CIDR 并不要求它是第一个主机地址。

不要对每个前缀都套用“减去两个”。[RFC 3021](https://www.rfc-editor.org/rfc/rfc3021.html) 允许在受支持的点对点链路上使用 `/31` 的两个地址。`/32` 标识一个地址，通常作为主机路由；它不意味着存在直接连接的 Ethernet 对端。云分配规则另行计算：标准 AWS VPC IPv4 子网保留前四个地址和最后一个地址，在 `/26` 中留下 **59 个可分配地址**，但 BYOIP 等情况除外。有关分配模式，请查看 [VPC 子网规则](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)。

#### 最长前缀、下一跳与 ARP {#longest-prefix-next-hop}

路由查找发生在邻居解析**之前**。考虑 Linux 主机上的以下示例路由表，其 `eth0` 上配置了 `192.0.2.130/26`：

| 目的前缀 | 下一跳 / 接口 |
|---|---|
| `192.0.2.128/26` | 直接通过 `eth0`（链路内） |
| `198.51.100.0/24` | 经由 `eth0` 上的 `192.0.2.129` |
| `198.51.100.128/25` | 经由 `eth0` 上的 `192.0.2.190` |
| `0.0.0.0/0` | 默认经由 `eth0` 上的 `192.0.2.129` |

在选定的表中，选择匹配路由中具有**最长前缀**的路由（[RFC 1812 §5.2.4.3](https://www.rfc-editor.org/rfc/rfc1812.html#section-5.2.4.3)）：

- 对于 `192.0.2.150`，`/26` 路由为链路内：若其邻居条目缺失，使用 ARP 解析**`.150` 本身**。
- 对于 `198.51.100.140`，`/24`、`/25` 和 `/0` 均匹配；`/25` 胜出。使用 ARP 解析网关 **`192.0.2.190`**，而非远程目的地。
- 对于 `203.0.113.10`，仅 `/0` 匹配：使用网关 **`192.0.2.129`**。

对于被路由的数据包，Ethernet 目的地址是网关的 MAC，而 IP 目的地址仍是远程主机（没有 NAT 时）。默认路由上更低的度量值无法胜过匹配的 `/25`。Linux 策略规则可以选择不同的表；请按 [ip-route(8) 手册](https://man7.org/linux/man-pages/man8/ip-route.8.html)的说明，在相关网络命名空间中使用 `ip route get` 检查实际查找结果。主机和容器可能具有不同的路由和邻居表。

### IPv6

**定义：**采用 128 位地址的下一代 Internet 层协议。

**工作原理：**使用 128 位地址后，地址耗尽不再是问题。基础头部采用固定的 40 字节布局，且没有头部校验和；路由器不会分片 IPv6 数据包。SLAAC 让主机无需 DHCP 即可自行配置地址，ARP 则由 NDP（Neighbor Discovery Protocol）替代。

**实践中：**IPv6 与 IPv4 不向后兼容，因此实际部署会运行双栈——这意味着要维护两套防火墙规则和安全策略。IPv6 路径上缺失规则是一种常见安全缺口。全局 IPv6 地址本身并不会让工作负载可从互联网访问。AWS 仍要求路由以及被允许的安全组/NACL 流量；仅出口 Internet 网关可以允许 IPv6 出站，而不允许未经请求的入站连接。

**过渡机制：**与 IPv4 共存有三种实用方法：**双栈**（同时运行两者——最常见，但会导致策略重复）、**隧道**（将 IPv6 数据包封装在 IPv4 中以跨越仅支持 v4 的网段）以及 **NAT64/DNS64**（进行转换，让仅 IPv6 的客户端访问 IPv4 服务器——移动运营商以 464XLAT 大规模使用此方式）。Kubernetes 也支持双栈 Service，因此集群 CIDR 设计可以从一开始就考虑 IPv6 范围。

### ICMP

**定义：**报告网络错误和状态的控制协议。

**工作原理：**ICMP 承载控制信息，可包含 Echo 负载或被引用的原始数据包数据：目的地不可达、TTL 超时、需要分片等。`ping` 使用 Echo Request/Reply；`traceroute` 每次将 TTL（或 IPv6 Hop Limit）递增一跳，并读取返回的 Time Exceeded 消息。

**实践中：**出于“安全”考虑而完全阻止 ICMP 的做法很常见——这正是前文提到的 MTU 黑洞的直接原因。经典 IPv4 PMTUD 使用 ICMP Type 3 Code 4，而 IPv6 使用 ICMPv6 Packet Too Big Type 2。阻止必要的消息可能导致黑洞；PLPMTUD 则可以在不依赖 ICMP 的情况下探测数据包大小。根据 IP 版本和策略保留必要的错误/发现流量。

> 📎 有关此故障如何在 EKS 中出现，请参阅 [EKS 网络深度解析](../eks/03-eks-networking-part3.md)。

#### 解读 ICMP 和 traceroute 证据 {#icmp-traceroute-interpretation}

对于 IPv4 转发，路由器会减少数据包的 TTL；如果 TTL 到期，路由器会丢弃该探测包，通常返回 **ICMP Time Exceeded (Type 11, Code 0)**。对于刻意设置短 TTL 的探测包，这是预期现象，并不能证明普通应用数据包失败。该错误会引用部分原始数据包，使发送端能将响应与其探测包关联（[RFC 792](https://www.rfc-editor.org/rfc/rfc792.html)）。

将**发出的探测包**与**返回的响应**分开看待。以下常见 traceroute 方法都可以从中间路由器收到 ICMP Time Exceeded：

| 发送的探测包 | 到达目的地时的典型响应 |
|---|---|
| 发送至未使用目的端口的 UDP | ICMP Destination Unreachable, Port Unreachable (IPv4 Type 3, Code 3) |
| ICMP Echo Request | ICMP Echo Reply |
| 发往选定端口的 TCP SYN | 监听端口返回 TCP SYN/ACK，关闭端口返回 RST |

默认值和选项因实现而异；[Linux traceroute(8) 手册](https://man7.org/linux/man-pages/man8/traceroute.8.html)记录了 UDP、ICMP 和 TCP 方法。TCP 探测包可测试该端口的处理情况，但即使收到 SYN/ACK 也不能证明 TLS 或 HTTP 正常工作。

`*` 表示**在等待超时前未收到匹配的响应**。探测包可能被过滤，路由器可能抑制或限速其响应，或响应可能在返回路径上丢失。一个无响应跳点之后仍有后续跳点响应，并不能证明存在端到端丢包。每个显示的 RTT 都包含一条可能不同于前向路径的返回路径；负载均衡也可能使不同探测包经过不同路由器。定位故障之前，请将重复观测结果与目的地和应用结果进行比较。

traceroute 主要探查跳点；小型探测包的成功并不能验证路径 MTU。设置 DF 的更大 IPv4 数据包可能仍需 **Fragmentation Needed (Type 3, Code 4)** 才能发现更小的 MTU。请将该消息与 Time Exceeded 和 Port Unreachable 区分开；并保留上文关于 IPv6 和 PLPMTUD 的区别。

> 📎 请在 [Linux 路由和 ICMP 实验](../networking/07-linux-network-diagnostics.md#routing-icmp-lab)中应用路由和探测推理，然后将其用于容器和 Kubernetes 排障。

### OSPF

**定义：**一种链路状态路由协议，用于在单个自治系统内计算最优路径。

**工作原理：**每台路由器在区域内泛洪其链路状态，使同一区域中的路由器收敛到一致的链路状态信息，随后各自运行 Dijkstra 算法计算最短路径。接口开销由配置决定（通常从带宽派生），网络则被划分为区域以实现扩展。

**实践中：**OSPF 是 IGP——用于内部网络。其收敛快速并自动找到路径，但每台路由器都会维护其连接区域的链路状态信息，因此在大规模场景中，区域设计决定性能。

### BGP

**定义：**一种路径向量路由协议，用于在自治系统（AS）之间交换可达性信息。

**工作原理：**BGP 的目标不同于 OSPF：它选择的不是“最快的路径”，而是“策略偏好的路径”。每个 AS 宣告其可达的前缀以及 AS 路径；接收方按 AS_PATH 长度、Local Preference 和 MED 等属性对路由排序。整个互联网的路由都建立在此基础上。

**实践中：**BGP 默认信任宣告，因此错误的前缀宣告可能导致大范围中断。RPKI 起源验证会检查前缀起源是否获得授权；它不验证完整 AS 路径，也无法阻止所有路由泄漏。从云的角度看，Direct Connect 使用 BGP；Site-to-Site VPN 可以使用 BGP 或受支持的静态路由，因此 AS 编号、宣告前缀设计以及用于冗余的路径偏好（AS_PATH 预置及类似机制）都会成为实际设计事项。

> 📎 有关 Calico 如何在集群内使用 BGP，请参阅 [Calico BGP 深度解析](../networking/calico/04-bgp-deep-dive.md)。

### NAT

**定义：**一种转换 IP 地址，并在 NAPT/PAT 场景下转换传输端口的功能。

**工作原理：**常见情况是许多私有主机通过 PAT/NAPT 共享一个公共地址。转换也可以是私有到私有；它并非总是共享公共互联网地址。转换表维护每会话映射，因此返回数据包可以找到正确的内部主机。

**实践中：**NAT 是违反分层原则的典型案例：L3 设备重写 L4 端口，并破坏端到端连通性——这正是互联网最初的前提。因此 P2P 变得困难，STUN/TURN 等变通方案也成为必要（见下文 WebRTC）。在云中，NAT Gateway 端口耗尽和数据处理费用才是实际问题。对于出站密集型工作负载，VPC 端点可减少受支持 AWS 服务的 NAT 处理；在假定能节省费用之前，请比较其每小时/数据费用和流量路径。

---

**下一篇：**[第 2 部分：传输层与 TLS](./06-network-fundamentals-part2.md)

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
