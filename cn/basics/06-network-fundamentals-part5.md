# 网络基础知识第 5 部分：网络设备、LAN 和 WAN 基础

> **最后更新**：2026年11月19日

::: tip 这是一个由五部分组成的系列
[第 1 部分：分层模型、链路层和路由层](./06-network-fundamentals-part1.md) ·
[第 2 部分：传输层和 TLS](./06-network-fundamentals-part2.md) ·
[第 3 部分：应用协议](./06-network-fundamentals-part3.md) ·
[第 4 部分：请求的旅程与云](./06-network-fundamentals-part4.md) ·
**第 5 部分：网络设备、LAN 和 WAN** *（本文档）*
:::

第 1 至第 4 部分逐层介绍了协议。本部分介绍处理这些协议的**设备**，以及连接这些设备的 **LAN 和 WAN 设计**。以太网帧、ARP、最长前缀匹配和 NAT 的基本定义已在[第 1 部分](./06-network-fundamentals-part1.md)中说明，因此这里不再重复。本部分将重点讲解每种设备会查看什么、会做出什么决策，以及冗余和地址转换会在哪些地方出问题。

本部分的范围对应 CCNA (200-301) 的网络基础、网络接入和 IP 服务领域，以及 CompTIA Network+ (N10-009) 的领域 1。考试大纲仅用于确定目录结构。文末参考资料中的标准、厂商文档和 AWS 文档用于核对数值和协议行为；集线器和 AP 等设备的基本行为则作为一般定义给出。

与第 1 部分类似，每项都遵循**定义 → 工作原理 → 实际中的问题**这一结构。

---

<a id="device-roles"></a>

## 1. 设备的角色：各自会查看什么

区分设备最清楚的方法是询问：设备决定如何转发端口收到的数据时，**会查阅哪张表**。

| 设备 | 主要输入 | 查阅的表 | 决策 |
|---|---|---|---|
| 集线器（中继器） | 无（比特信号） | 无 | 将信号从其他所有端口转发出去 |
| L2 交换机 | 目标 MAC + VLAN | MAC 地址表 | 已知单播帧发往一个端口；广播帧和目标未知的帧在 VLAN 内泛洪 |
| L3 交换机 | VLAN 内的 MAC，跨子网时的目标 IP | MAC 表 + 路由（FIB） | 在 VLAN 内交换数据，通过充当网关的每 VLAN 虚拟接口（SVI）在 VLAN 之间路由 |
| 路由器 | 目标 IP | 根据路由表构建的 FIB | 按最长前缀路由转发到下一跳，将 TTL 减 1，并写入新的 L2 首部 |
| 有状态防火墙 / NGFW | 五元组和连接状态；NGFW 还会识别应用 | 策略规则 + 状态（连接）表 | 按规则检查新连接；后续返回数据包与状态表匹配时放行 |
| 负载均衡器 | L4 的五元组；L7 的 HTTP 主机名、路径和标头 | 监听器规则、目标组健康状态 | 选择一个健康目标并将流量转发给它 |
| 无线 AP | 终端 MAC、SSID | 已关联终端列表、SSID 到 VLAN 的映射 | 将 802.11 帧桥接到有线分发网络 |

各设备值得注意的要点：

- **集线器**是 L1 设备，不会查看地址。所有连接到集线器的设备共用一个半双工介质，因此同时传输会发生冲突。
- **L2 交换机**根据入口端口和 VLAN 学习每个帧的**源 MAC**，并根据**目标 MAC**选择出口端口。它不会更改帧（在 Trunk 上添加或移除 802.1Q 标签是例外）。
- **L3 交换机**是内置路由功能的交换硬件。正如 Cisco 的示例所示，为每个 VLAN 创建一个 SVI，并将其地址用作该 VLAN 的默认网关。
- **路由器**不会将作为 L2 广播接收的数据包转发到其他接口（目标为 IP 多播地址的情况除外；RFC 1812 §5.3.4），也不会转发受限广播地址 `255.255.255.255`（§5.3.5.1），因此路由器接口（或 SVI）就是广播域的边界。经过路由的数据包 TTL 会减小，源 MAC 和目标 MAC 会更新；除非涉及 NAT，否则 IP 地址保持不变。
- **有状态防火墙**会跟踪连接，因此无需为返回数据包单独编写规则。NIST SP 800-41 区分了数据包过滤器、有状态检测（为每个连接保留一条状态表记录）以及应用防火墙和代理网关，并将捆绑了恶意软件检测等类似功能的防火墙称为 UTM。“NGFW”不是 NIST 术语，而是厂商对捆绑了应用识别、用户识别、入侵防御等类似功能的产品所用的称谓。
- **负载均衡器**会根据所在层做出不同决策。在 AWS 上，ALB 按优先级顺序评估监听器规则，然后从规则对应的目标组中选择目标；NLB 根据协议、源/目标 IP 和端口以及 TCP 序列号计算流哈希来选择目标，并在每条 TCP 连接的整个生命周期内将其保持在同一目标上。
- **AP**是无线网络与有线网络之间的桥接设备。通常会将不同的 SSID 映射到不同的 VLAN，因此无线终端会经过上文所述的同一套交换机和路由器决策。

**实际应用**：排查故障时，重点查看“此设备会查阅的表”。在 Linux 上，`bridge fdb show` 可显示网桥学习到的 MAC 地址，`ip route get <destination>` 可显示路由决策，而 conntrack 工具可显示连接跟踪（状态和 NAT）表。如果预期的条目不存在，原因就在该设备之前的某个步骤。

### 冲突域和广播域

**定义：****冲突域**是共享介质中同时传输会发生冲突的范围；**广播域**是 L2 广播帧能够到达的范围。

**工作原理：**

- 集线器的所有端口都属于同一个冲突域。
- 交换机为每个端口划分一个冲突域。在全双工链路上，发送和接收彼此独立，完全不会发生冲突（参见[第 1 部分中的以太网](./06-network-fundamentals-part1.md#ethernet)）。
- 一个 VLAN 就是一个广播域。如果同一个 VLAN 通过 Trunk 跨越多台交换机，整个范围仍然是**一个**广播域。
- 路由器接口和 SVI 不会转发广播，因此会划分广播域。

**用示例计数**：一台交换机承载 VLAN 10、20 和 30，并通过一条 Trunk 连接到一台路由器（有三个子接口）。交换机的一个端口连接着一台集线器，集线器上有四台 PC。

| 问题 | 答案 | 原因 |
|---|---|---|
| 广播域的数量 | 3 | 每个 VLAN 一个；路由器会阻止广播跨越 VLAN |
| 集线器上四台 PC 的冲突域数量 | 1 | 集线器是共享介质，因此四台 PC 共用一个冲突域 |
| 每个交换机端口连接一台主机 | 每个端口 1 个 | 交换机端口会划分冲突域，而全双工意味着不会实际发生冲突 |

**实际应用**：在大型广播域中，ARP 和 DHCP 等广播会唤醒每台主机的 CPU，而环路会影响更多主机。这就是 VLAN 应保持较小规模，并通过路由转发 VLAN 间流量的原因。

---

<a id="vlan-trunk"></a>

## 2. VLAN 和 802.1Q Trunk

[VLAN in Part 1](./06-network-fundamentals-part1.md#vlan)介绍了 VLAN 的定义，以及 VLAN 间流量需要经过 L3 设备的规则。本节将介绍标签实际包含的内容，以及 Trunk 上可能出现的问题。

### 802.1Q 标签

**定义**：IEEE 802.1Q 会在以太网帧的源 MAC 后插入一个 4 字节标签，以标记该帧所属的 VLAN。

**工作原理**：标签包含四个字段。

| 字段 | 大小 | 含义 |
|---|---|---|
| TPID | 16 位 | 值为 `0x8100`：标记该帧带有 802.1Q 标签 |
| PCP | 3 位 | 优先级 0 到 7（802.1p） |
| DEI（以前称为 CFI） | 1 位 | 标记拥塞时可优先丢弃的帧 |
| VID | 12 位 | VLAN ID。取值范围为 0 到 4095，但 0 和 4095 为保留值，因此实际 VLAN 使用 1 到 4094 |

标签会增加 4 字节，因此带标签的帧最长可达 1522 字节；插入标签的设备会重新计算 FCS。

### Access 端口、Trunk 端口和 Native VLAN

**定义：**

- **Access 端口**属于一个 VLAN，并与主机交换未标记的帧。
- **Trunk 端口**通过一条链路承载多个 VLAN，并为每个帧添加 VID 标签。
- **Native VLAN**是通过 Trunk **不带标签**传输的 VLAN。

**工作原理**：根据 Cisco Catalyst 文档，Native VLAN 默认为 **VLAN 1**；设备会将从 Trunk 收到的未标记帧放入 Native VLAN，并将 Native VLAN 的帧以未标记形式发出。Trunk 两端的 Native VLAN **必须匹配**。如果不匹配，一侧 VLAN 中的未标记帧会落入另一侧的不同 VLAN，从而破坏 VLAN 隔离；Cisco 还警告这可能导致生成树环路。默认情况下，Trunk 允许 VLAN 1 到 4094。

**实际应用：**

- 将每条 Trunk 的允许 VLAN 列表缩减到实际需要的范围，将 Native VLAN 改为一个未使用的 VLAN，并确保两端设置一致。
- Linux 可以使用 `ip link add link eth0 name eth0.10 type vlan id 10` 创建带标签的子接口。虚拟机管理程序和裸金属 Kubernetes 节点接入 Trunk 端口时会采用这种方式。

### VLAN 间路由：单臂路由

在一条 Trunk 上为每个 VLAN 配置一个路由器子接口，就能让一台路由器充当多个 VLAN 的网关。下面的动画展示了一个帧如何从 VLAN 10 中的 PC-A 到达 VLAN 20 中的 PC-B。关键在于，它会沿着同一条线缆上行，然后再返回。

![VLAN 间路由动画。① PC-A（VLAN 10，10.0.10.5）发现目标位于另一个子网，因此将帧发往网关 10.0.10.1 的 MAC 地址。② L2 接入交换机在 VLAN 10 中的端口 1 上学习源 MAC，并将带有 VLAN 10 标签的帧通过 802.1Q Trunk 向上发送。③ 路由器查询到 10.0.20.0/24 的路由后选择 .20 子接口，将 TTL 从 64 减至 63，并写入新的 L2 首部（IP 地址不变）。④ 帧带着 VLAN 20 标签沿同一条 Trunk 返回。⑤ 交换机移除标签，将帧从 VLAN 20 的 Access 端口转发出去，PC-B（10.0.20.7）收到该帧。](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-0.svg)

如果由 L3 交换机执行相同的工作，它会在交换机内部通过 SVI 在 VLAN 之间路由，而不必沿 Trunk 上下传输。VLAN 间流量不再两次占用 Trunk 带宽，因此在 VLAN 间流量较大的场景中会使用 L3 交换机。

---

<a id="stp-lacp-fhrp"></a>

## 3. 防环路与冗余：STP、LACP、FHRP

冗余链路和设备可以提高可用性，但它们会在 L2 引发环路，并在 L3 网关处带来“谁是默认网关？”的问题。三种技术分别解决其中一种问题。

### STP 和 RSTP

**定义**：生成树协议（STP，IEEE 802.1D）会阻塞部分冗余交换机链路，使 L2 拓扑成为无环树。RSTP（802.1w，后来并入 802.1D-2004）是其快速收敛版本。

**为何需要**：IP 首部包含 TTL，但**以太网首部不包含**。交换机之间一旦形成环路，广播帧就不会消失：它会持续循环并不断增多（形成广播风暴）；同一个源 MAC 还会出现在多个端口上，导致 MAC 表不断变化。

**工作原理：**

1. **根桥选举**：桥 ID（优先级 + MAC）最低的交换机成为根桥。默认优先级为 32768，因此在未配置的情况下，MAC 地址最低的交换机（通常也是最旧的交换机）会成为根桥。
2. **端口角色**：每台非根交换机将通往根桥的最佳端口设为**根端口**；在每个网段上，发送最佳 BPDU 的端口成为**指定端口**。其余端口会被阻塞（RSTP 中的替代端口和备份端口角色）。
3. **收敛**：802.1D 由计时器驱动。默认值为 Hello 2 秒、Max Age 20 秒、Forward Delay 15 秒；端口会经过两个 Forward Delay 时段，即约 30 秒的侦听和学习状态。RSTP 将状态缩减为丢弃、学习和转发；在点对点链路上，它通过提议/同意交换进入转发状态，而不必等待计时器。主机端口会配置为边缘端口（Cisco PortFast），并立即进入转发状态。

**实际应用**：不要让根桥保持默认设置；应降低核心或分发交换机的优先级，将根桥固定在预期位置。如果任意一台交换机成为根桥，流量就会绕道经过它。还要记住，正常运行时被阻塞的链路不会承载任何流量。下文的 LACP 和第 4 节的 Spine-Leaf 会以不同方式绕过这一限制。

### LACP 和 EtherChannel

**定义**：链路聚合（IEEE 802.1AX）将两个设备之间的多条并行全双工点对点链路捆绑为一条逻辑链路（LAG）。LACP 是两端用于协商捆绑的控制协议；Cisco 将该捆绑称为 EtherChannel。

**工作原理**：STP 会将 LAG 视为一条链路，因此不会阻塞捆绑的链路。帧会根据地址和端口等值的哈希结果分配到某一条成员链路上，因此**同一个流始终使用同一条链路**。Cisco 文档说明最多可捆绑八个兼容端口。

**实际应用**：捆绑四条 10 Gbps 链路，并不意味着**一个** TCP 连接就能超过 10 Gbps；只有多个流才能利用聚合带宽。遇到“单个备份任务速度很慢”时，增加 LAG 成员可能无济于事。AWS Direct Connect LAG 也使用 LACP 在同一个端点捆绑连接（不支持多机箱 LAG）；详情见[专家练习册 07：WAN 和混合连接](../networking/expert/07-wan-hybrid-connectivity.md#dx-lag)。

### FHRP：VRRP 和 HSRP

**定义**：第一跳冗余协议（FHRP）让多台路由器共享一个**虚拟 IP 和虚拟 MAC**，这样即使路由器发生故障，主机也无需更改默认网关设置。

**为何需要**：主机只有一个默认网关地址。如果该路由器宕机，即使同一子网上还有另一台路由器，主机也无法离开自己的子网。

**VRRPv3 的工作原理（RFC 9568，取代了 RFC 5798）：**

- 在虚拟路由器 ID（VRID）相同的路由器中，一台会成为 **Active**（RFC 5798 中称为 Master），并处理发往虚拟 IP 的流量。IPv4 虚拟 MAC 为 `00-00-5E-00-01-{VRID}`，IPv6 虚拟 MAC 为 `00-00-5E-00-02-{VRID}`。
- Active 路由器会向 IPv4 多播地址 `224.0.0.18` 发送通告，使用的 IP 协议号为 112。默认通告间隔为 100 厘秒（1 秒）。
- 实际拥有虚拟 IP 的路由器优先级为 255；备份路由器的默认优先级为 100。Active 路由器的优先级为 0，表示它已停止参与 VRRP，因此备份路由器只需等待 Skew_Time 就会接管，而不必等待完整的宕机间隔。Preempt 默认启用。
- 备份路由器在漏收通告后，会在 `Active_Down_Interval = 3 × advertisement interval + Skew_Time` 时成为 Active，其中 `Skew_Time = ((256 − priority) × advertisement interval) / 256`。当优先级为 100、间隔为 1 秒时，Skew_Time 约为 0.61 秒，因此约 **3.61 秒**后接管。

**HSRP**：Cisco 的 FHRP，作为 RFC 2281（信息性文档）发布。默认 Hello 间隔为 3 秒，Hold 间隔为 10 秒；v1 虚拟 MAC 为 `0000.0c07.acXX`（XX 是组号）。

**实际应用**：故障切换后，虚拟 MAC 会迁移到新的 Active 路由器，因此邻居和交换机必须立即学习它的新位置（参见[第 1 部分 ARP 中的免费 ARP](./06-network-fundamentals-part1.md#arp)）。测量故障切换时间时，应将 FHRP 计时器、STP 收敛以及上游路由收敛的时间都计算在内。

---

<a id="lan-topologies"></a>

## 4. LAN 拓扑：分层架构和 Spine-Leaf

### 园区网络：两层和三层架构

**定义**：传统上，园区 LAN 分为接入层、分发层和核心层。

| 层 | 作用 |
|---|---|
| 接入层 | 网络边缘，主机在此接入 |
| 分发层 | 汇聚接入交换机，并提供 L2/L3 边界、访问策略和冗余路径 |
| 核心层 | 连接所有网络区块以及数据中心和 WAN 的骨干网 |

**工作原理**：Cisco 的设计指南建议在单栋楼等小型站点采用**两层**（核心合并）设计，将分发层与核心层合并；指南还指出，**三层**设计适用于有多个分发区块的大型站点，分层有助于隔离故障和控制变更。

### 数据中心：Spine-Leaf

**定义**：在 Spine-Leaf（Clos）网络结构中，**每个 Leaf 都连接到每个 Spine**（两层之间构成全网状连接），服务器则连接到 Leaf。本文假设采用基本的两层网络结构，其中 Leaf 之间互不连接，Spine 之间也互不连接；也存在其他变体，例如 Cisco ACI 的多层设计会在第一层 Leaf 下再挂接第二层 Leaf。

**工作原理：**

- Leaf 到 Spine 的链路是 L3 链路，ECMP 会将流量分散到所有 Spine 路径上。STP 不会阻塞任何链路，因此所有上行链路会同时承载流量。
- 在这一假设下，发往另一台 Leaf 上服务器的流量始终沿着 **Leaf → Spine → Leaf** 路径传输：经过三台交换机（两段交换机间链路）。任意一对服务器之间的距离都相同，因此具有一致的延迟，这正是 Cisco 所指出的该设计优势之一。
- 增加 Leaf 可扩展端口数量，增加 Spine 可提高带宽。

| 比较项 | 传统三层架构（L2 + STP） | Spine-Leaf（L3 + ECMP） |
|---|---|---|
| 冗余链路 | STP 会阻塞部分链路 | ECMP 会使用所有链路 |
| 服务器之间的距离 | 取决于部署位置 | 固定：Leaf → Spine → Leaf |
| L2 扩展 | 大范围延伸 VLAN | 需要时采用 VXLAN/EVPN 覆盖网络 |

**实际应用**：如果 Spine-Leaf 网络结构中的某个 VLAN 必须跨越多个 Leaf，可在 L3 Underlay 上运行 VXLAN/EVPN 覆盖网络。如何通过证据验证标识符、路由和数据平面，详见[专家练习册 03：数据中心 EVPN](../networking/expert/03-datacenter-evpn.md)。

---

<a id="nat-pat-cgnat"></a>

## 5. NAT、SNAT、PAT 和 CGNAT

[NAT in Part 1](./06-network-fundamentals-part1.md#nat)介绍了 NAT 的基本定义，以及“L3 设备会处理 L4 端口”这一事实。本节将厘清相关术语，展示转换表的实际填充过程，以及转换资源何时会耗尽。

### 术语

| 术语 | 改写内容 | 示例 |
|---|---|---|
| 基本 NAT（包括静态 1:1 NAT） | 仅 IP 地址 | 一个私有 IP ↔ 一个公有 IP；AWS Internet Gateway 处理公有 IPv4 地址的方式 |
| NAPT / PAT | IP 地址 + 传输层标识符（TCP/UDP 端口、ICMP 查询 ID） | 多台内网主机共享一个公有 IP |
| SNAT | 源地址（和端口） | 发往互联网的流量 |
| DNAT | 目标地址（和端口） | 端口转发、负载均衡器将流量转发到目标 |

RFC 3022 将基本 NAT 和 NAPT 定义为“传统 NAT”。会话从私有网络内部发起，第一个出站数据包会创建映射。SNAT 和 DNAT 这两个名称来自 Linux netfilter 目标名；PAT 通常以 SNAT 的一种形式实现。

### 跟踪 PAT 转换表

示例中的内网主机使用 RFC 1918 私有地址空间，公有 IP 和服务器使用 RFC 5737 文档示例地址段（`203.0.113.0/24`、`198.51.100.0/24`）。在下面的动画中，两台内网主机特意使用**相同的源端口 50000**。只有一个公有 IP 时，NAT 设备通过不同的公有**端口**来区分它们。

![PAT 动画。① 私有网络 10.0.1.0/24 上的 Host-A（10.0.1.10）发送数据包，源地址为 10.0.1.10:50000，目标地址为服务器 198.51.100.20:443。② NAT 设备添加转换记录 10.0.1.10:50000 → 203.0.113.10:30001，并以源地址 203.0.113.10:30001 将数据包发出。③ Host-B（10.0.1.20）也使用源端口 50000，因此 NAT 会在同一个公有 IP 上为它分配另一个端口，添加记录 10.0.1.20:50000 → 203.0.113.10:30002。④ 服务器的回复返回时，目标地址为 203.0.113.10:30002，NAT 按公有端口查找表项并匹配到第 2 条记录。⑤ NAT 将目标地址改写回 10.0.1.20:50000，并将数据包交付给 Host-B。](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-1.svg)

返回途中，NAT 会查看**目标地址（公有 IP:端口）**。如果没有匹配的记录，例如连接是从外部发起的，或者映射已过期，数据包就无法发送给任何内网主机。这就是从外部访问 NAT 后方的服务器需要单独的静态映射（DNAT）的原因。

### 端口耗尽

**工作原理**：端口字段为 16 位，因此一个公有 IP 对同一个目标只能承载有限数量的并发连接。AWS NAT Gateway 明确公布了其限制：

- 每个公有 IPv4 地址对每个唯一目标（目标 IP、目标端口和协议），最多支持 **55,000** 个并发连接
- 每个 NAT Gateway 最多支持 8 个 IPv4 地址（1 个主地址 + 7 个辅助地址），因此对同一个目标最多支持 440,000 个连接；公有 NAT Gateway 默认最多只能使用 2 个 Elastic IP，因此需要申请提高配额
- 无法分配源端口时，CloudWatch 指标 `ErrorPortAllocation` 会大于零
- 空闲 350 秒的连接会超时；之后再通过该连接发送数据，NAT Gateway 会返回 RST

**实际应用**：当数百个 Kubernetes 节点上的 Pod 调用**同一个外部 API**（一个 IP:443）时，由于只有一个目标，会首先触及该限制。可依次考虑复用连接（Keep-Alive、连接池）、添加辅助 IP、将子网分散到多个 NAT Gateway 上，以及使用 VPC Endpoint 将受支持的 AWS 服务流量移出 NAT 路径（参见[第 4 部分](./06-network-fundamentals-part4.md)中对出站路径的讨论）。对于长时间空闲的连接，应将 TCP Keepalive 设置为低于 350 秒。

### CGNAT 和 100.64.0.0/10

**定义**：运营商级 NAT（CGNAT）是一种大规模 NAT，运营商通过它让许多订户共用一个公有 IPv4 地址。流量通常先在订户的路由器上转换一次，然后在运营商的 CGN 上再次转换。

**工作原理：**

- RFC 6598 为 CGN 与客户驻地设备（CPE）**之间的网段分配了`100.64.0.0/10` 共享地址空间**。它与 RFC 1918 私有地址段（`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`）**相互独立**，因此不会与订户在内部使用的任何 RFC 1918 地址段冲突。
- 此地址范围的数据包和路由信息不得跨越运营商边界，运营商必须过滤针对该范围的入站通告。
- RFC 6888 要求 CGN 支持限制每个订户使用的外部端口；资源耗尽时，必须丢弃新数据包，而不能删除现有映射。要根据日志识别订户，需要外部地址、外部端口和时间戳。

**实际应用：**

- 移动网络和部分住宅用户可能共用一个公有 IP。仅按 IP 封锁或限速可能会影响无关用户；调查事件时，除了 IP，还需要**端口和准确时间**。
- CGNAT 后方的分支机构无法接受从外部发起的连接，因此应设计由分支机构一侧发起的站点到站点 VPN。
- AWS 允许将来自 `100.64.0.0/10` 的 CIDR 地址段关联到 VPC。当私有地址空间不足时，这一地址段可以作为候选方案，但首先要确认必须访问的本地网络或运营商网段没有使用相同范围。

---

<a id="wan-types"></a>

## 6. WAN 类型

**定义**：WAN 用于连接地理位置分散的站点（总部、分支机构、数据中心、云）。WAN 的大部分服务由运营商提供，因此选择的关键是“我们要购买哪种服务？”

| 类型 | 购买的服务 | 路由和寻址 | 优势 | 注意事项 |
|---|---|---|---|---|
| 专线 | 两个站点之间带宽固定的点对点电路 | 两端的路由器直接交换路由 | 带宽和延迟稳定，且不与其他客户共享 | 每对站点都需要一条电路，成本高 |
| MPLS L3VPN | 运营商 MPLS 网络中的客户专用虚拟路由 | 运营商 PE 路由器将客户接入绑定到 VRF；CE 与 PE 之间可使用静态路由、RIP、OSPF 或 BGP | 站点之间任意互通，运营商提供 SLA | 受限于运营商，成本高于互联网电路 |
| 宽带互联网 | 光纤、同轴电缆或类似的互联网接入 | 公有地址或 CGNAT 地址，无法控制路径 | 单位带宽成本低 | 尽力而为的服务质量；机密性需要依靠自己的覆盖网络，例如 IPsec |
| LTE/5G | 移动数据接入 | 通常位于运营商 NAT 后方，难以从外部发起连接 | 无需布线即可快速开通，适合作为备份 | 延迟和带宽不稳定，资费模式各异 |
| SD-WAN | 构建在上述电路之上的托管覆盖网络 | 按应用流策略选择隧道路径 | 结合多种电路并按应用选择路径 | 仍受 Underlay 质量限制 |

**工作原理：**

- 在 **MPLS L3VPN**（RFC 4364）中，运营商的 PE 路由器除了默认转发表外，还会维护名为 VRF 的路由表，并将每个客户接入电路绑定到一个 VRF。通过 BGP 传递的客户路由会带有 8 字节的 Route Distinguisher 前缀，使其成为 VPN-IPv4 地址，因此使用相同私有地址段的不同客户不会相互混淆。CE 和 PE 之间通过静态路由、RIP、OSPF 或 BGP 交换路由。
- **SD-WAN**是一种服务模式，而不是电路类型。MEF 70.2 将 SD-WAN 服务与其下方的 Underlay Connectivity Services（互联网接入、MPLS 等）分别定义，将站点间隧道定义为 Tunnel Virtual Connections（TVC），并将按应用流制定的路径规则定义为 Policy。
- 云端的 WAN 接入点包括 AWS Site-to-Site VPN 和 Direct Connect（参见[第 4 部分](./06-network-fundamentals-part4.md)中的云端映射）。冗余设计、BGP 路径选择、隧道 MTU 和成本比较，详见[专家练习册 07：WAN 和混合连接](../networking/expert/07-wan-hybrid-connectivity.md)。

**实际应用**：选择 WAN 时，除带宽外还应记录延迟和抖动、故障切换方式，以及电路是否由不同运营商通过不同路径接入（物理路径多样性）。如果两条电路共用一条管道，一台挖掘机就可能同时切断两条电路。

---

## 7. 云中的网络

[第 4 部分](./06-network-fundamentals-part4.md)对传统概念与 AWS 做了广泛比较。下表仅涉及本文介绍的**设备和决策**，并说明哪些方面相同、哪些方面不同。

| 传统设备或功能 | AWS 对应项 | 差异 |
|---|---|---|
| 子网默认网关（路由器、SVI） | VPC 路由器和 VPC 路由表 | AWS 将子网网络地址 + 1 保留给 VPC 路由器；路由表会自动包含一条指向 VPC CIDR 的 `local` 路由 |
| FHRP（VRRP、HSRP） | 无需自行配置 | 网关地址就是 VPC 路由器，而 VPC 不支持广播，因此不存在虚拟 IP 和 MAC 的 L2 切换；应通过多个 AZ 和负载均衡器健康检查设计冗余 |
| 互联网边缘路由器 + 静态 1:1 NAT | Internet Gateway（IGW） | 这是一个横向扩展、具有冗余能力的 VPC 组件，可为具有公有 IPv4 地址的实例提供逻辑上的 1:1 NAT |
| PAT 设备 | NAT Gateway | 每个 IP 对每个目标支持 55,000 个并发连接，最多支持 8 个 IP；容量会自动从 5 Gbps 扩展到 100 Gbps；不能附加安全组；空闲超时时间为 350 秒 |
| 核心路由器、WAN 中心节点 | Transit Gateway | 区域级虚拟路由器；每个附件关联一个路由表，并可向多个路由表传播路由 |
| 有状态防火墙 | 安全组 | 有状态；仅允许规则，评估所有规则；作用于实例（网络接口）级别 |
| 路由器接口上的无状态 ACL | 网络 ACL | 无状态；按规则编号升序评估允许和拒绝规则，应用第一个匹配项；作用于子网级别；必须显式允许使用临时端口的返回流量 |

**安全组与 NACL 的差异如何导致中断**：NACL 不会自动允许返回流量。当子网中的实例充当客户端时，回复会返回到该实例操作系统选择的**临时端口**，因此入站 NACL 必须允许该端口范围。根据 AWS 文档，许多 Linux 内核使用 32768–61000，Windows Server 2008 及更高版本使用 49152–65535，而 NAT Gateway、ELB 和 Lambda 使用 1024–65535。仅使用安全组时，回复会自动获准，因此不会出现这个问题。

---

## 总结

归根结底，设备就是通过查阅表格来做出决策的机器：交换机读取 MAC 表，路由器读取 FIB，防火墙读取状态表，负载均衡器读取监听器规则，NAT 设备读取转换表。每一层的冗余设计都有各自的权衡：L2 环路（STP）、捆绑链路上的按流分配（LACP），以及网关处虚拟地址所有权的切换（FHRP）。

调查故障时，应检查“最后一台正确处理该数据包的设备，其表中有哪些内容”。直接显示表项的证据，例如 MAC 地址的学习位置、路由查询结果、状态表或 NAT 表条目，或 NAT Gateway 的 `ErrorPortAllocation`，都比猜测更可靠。

---

## 后续文档

- [专家练习册 03：数据中心 EVPN](../networking/expert/03-datacenter-evpn.md)：Spine-Leaf 上的 VXLAN/EVPN 覆盖网络
- [专家网络学习路径](../networking/expert/README.md)：完整的练习册目录，包括 WAN 和混合连接、CDN 和边缘网络
- [网络学习路径](../networking/README.md#learning-path)：从容器和 Services 到 CNI 实现
- [第 4 部分：请求的旅程与云](./06-network-fundamentals-part4.md)：AWS 和 Kubernetes 的完整映射

## 参考资料

标准和 RFC

- [IEEE 802.1Q-2022：网桥和桥接网络](https://standards.ieee.org/ieee/802.1Q/10323/)
- [IEEE 802.1AX：链路聚合](https://1.ieee802.org/tsn/802-1ax-rev/)
- [RFC 9568：适用于 IPv4 和 IPv6 的 VRRP 版本 3](https://www.rfc-editor.org/rfc/rfc9568.html)（取代 RFC 5798），[RFC 5798](https://www.rfc-editor.org/rfc/rfc5798.html)
- [RFC 2281：Cisco 热备份路由器协议（HSRP）](https://www.rfc-editor.org/rfc/rfc2281.html)
- [RFC 3022：传统 IP 网络地址转换器](https://www.rfc-editor.org/rfc/rfc3022.html)
- [RFC 6598：为共享地址空间保留的 IANA IPv4 前缀](https://www.rfc-editor.org/rfc/rfc6598.html)
- [RFC 6888：运营商级 NAT 的通用要求](https://www.rfc-editor.org/rfc/rfc6888.html)
- [RFC 1918：私有互联网的地址分配](https://www.rfc-editor.org/rfc/rfc1918.html)
- [RFC 1812：IPv4 路由器要求](https://www.rfc-editor.org/rfc/rfc1812.html)
- [RFC 4364：BGP/MPLS IP 虚拟专用网络](https://www.rfc-editor.org/rfc/rfc4364.html)
- [RFC 5737：为文档示例保留的 IPv4 地址块](https://www.rfc-editor.org/rfc/rfc5737.html)
- [NIST SP 800-41 Rev. 1：防火墙和防火墙策略指南](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
- [MEF 70.2：SD-WAN 服务属性和服务框架](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)（[PDF](https://www.mplify.net/wp-content/uploads/MEF-70.2.pdf)）

厂商文档

- [Cisco：交换机间链路和 IEEE 802.1Q 帧格式](https://www.cisco.com/c/en/us/support/docs/lan-switching/8021q/17056-741-4.html)
- [Cisco Catalyst 9300：配置 VLAN Trunk](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-12/configuration_guide/vlan/b_1712_vlan_9300_cg/configuring_vlan_trunks.html)
- [Cisco：使用 Catalyst 交换机配置 VLAN 间路由](https://www.cisco.com/c/en/us/support/docs/lan-switching/inter-vlan-routing/41260-189.html)
- [Cisco：了解快速生成树协议（802.1w）](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html)
- [Cisco：了解并调整生成树协议计时器](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/19120-122.html)
- [Cisco Meraki：确定 RSTP/STP 根桥](https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Determining_the_RSTP%2F%2F%2F%2FSTP_Root_Bridge_on_an_MS_Switch_network)
- [Cisco：了解 EtherChannel 负载均衡和冗余](https://www.cisco.com/c/en/us/support/docs/lan-switching/etherchannel/12023-4.html)
- [Cisco：中型企业设计概述，LAN 设计](https://www.cisco.com/en/US/docs/solutions/Enterprise/Medium_Enterprise_Design_Profile%28MEDP%29/chap2.html)
- [Cisco：大规模可扩展数据中心网络结构白皮书](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-743245.html)，[Cisco ACI 多层架构白皮书](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-742214.html)
- [Linux ip-link(8)](https://man7.org/linux/man-pages/man8/ip-link.8.html)、[bridge(8)](https://man7.org/linux/man-pages/man8/bridge.8.html)、[iptables-extensions(8)：SNAT 和 DNAT 目标](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html)

AWS 文档

- [NAT Gateway 基础知识](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html)、[排查 NAT Gateway 问题](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html)、[NAT Gateway CloudWatch 指标](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html)
- [Internet Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [AWS Transit Gateway 的工作原理](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)
- [比较安全组和网络 ACL](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html#VPC_Security_Comparison)、[自定义网络 ACL 和临时端口](https://docs.aws.amazon.com/vpc/latest/userguide/custom-network-acl.html)
- [VPC CIDR 地址块](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)、[子网大小调整（保留地址）](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [Elastic Load Balancing 的工作原理](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)
- [Direct Connect 链路聚合组](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)
