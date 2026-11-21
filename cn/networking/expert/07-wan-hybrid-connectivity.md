# 07. WAN 与混合连接设计

> **最后更新**：2026年11月19日
> **实验边界**：仅进行设计审查（桌面检查）。本工作簿不会创建线路、VPN、Direct Connect 连接或 Transit Gateway。
> **验证状态**：已核对 AWS Direct Connect、Site-to-Site VPN 和 Transit Gateway 用户指南以及引用的 RFC；编写本章时未**配置或测量**任何连接。

完成本工作簿后，你应能够**预测本地站点与 AWS 区域之间两个方向的路径**，并通过证据说明：当一条链路故障时，哪条规则会选择下一条路径、需要多长时间，以及哪些指标会降低（带宽、MTU）。

请先完成[路由策略与实测收敛](02-routing-policy-convergence.md)。该章介绍 LOCAL_PREF、AS_PATH、MED 和社区的含义；本章只关注 AWS 对它们的认可范围。请复习[网络基础第 5 部分：WAN 类型](../../basics/06-network-fundamentals-part5.md#wan-types)中的线路类型，以及[第 5 部分：NAT、PAT 和 CGNAT](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)中的 NAT/CGNAT。

**准备情况**：无需账户或线路。所有任务均依据本章表格和官方文档进行评判。若要实际构建相同设计，会产生 Direct Connect 端口、VPN 连接、Transit Gateway 附件和数据传输费用；**费用和清理工作均由学习者自行负责**。不要在现有且已获批准的实验账户之外创建资源。

## 1. 带着问题阅读

考试范围只决定阅读内容。数值和行为均来自第一列中的官方文档。

| 阅读材料 | 对应的考试范围 | 用自己的话回答的问题 |
|---|---|---|
| [MEF 70.2](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)、[Cisco Catalyst SD-WAN 高可用性指南](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html) | ENCOR 350-401 架构：SD-WAN 控制平面和数据平面元素 | 当覆盖网络的控制平面不可达时，数据隧道会发生什么？ |
| [Site-to-Site VPN 隧道选项](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)、[路由选项](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html) | ANS-C01 域 1 网络设计、域 2 网络实施 | AWS 会通过两条隧道中的哪一条发送流量？什么因素会改变这一选择？ |
| [Direct Connect 路由策略和 BGP 社区](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html) | ANS-C01 域 1 和域 2 | 同一前缀通过两个 VIF 通告时，AWS 会按什么顺序进行比较？ |
| [Transit Gateway 的工作原理](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) | ANS-C01 域 1 和域 2 | 同一个 CIDR 分别通过 DX 和 VPN 到达时，哪一个优先？AS_PATH 是否重要？ |
| [Direct Connect 配额](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)、[VPN 配额](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html)、[TGW 配额](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) | ANS-C01 域 1 | 设计会先触及哪项限制：带宽、路由数量还是 MTU？ |
| [RFC 5880（BFD）](https://www.rfc-editor.org/rfc/rfc5880.html)、[RFC 7296（IKEv2）](https://www.rfc-editor.org/rfc/rfc7296.html) | 协议原理 | 哪两个数值相乘得出故障检测时间？ |

阅读后，绘制站点、线路和 AWS 组件，并用**不同线型**标出 **BGP 会话**和**数据包实际经过的链路**。正如[工作簿 02](02-routing-policy-convergence.md)所示，会话并不意味着数据会经过该会话；下面的 Direct Connect 网关就是一个典型示例。

## 2. Underlay 和 Overlay

请分两层记录 WAN 设计。**Underlay** 是实际承载数据包的线路（MPLS、互联网接入、Direct Connect）；**Overlay** 是在其上构建的隧道和策略（IPsec VPN、SD-WAN）。Overlay 无法改变 Underlay 的延迟、丢包或共享的物理路径：即便两条隧道分别通过两条线路，如果它们经过同一条管道，仍会共享一个故障点。

| 模型 | 控制平面（由谁决定路径） | 数据平面（数据包经过什么） | 设计中要检查的内容 |
|---|---|---|---|
| MPLS L3VPN | 提供商 PE 将客户路由隔离到 VRF，并通过 BGP 交换这些路由；CE–PE 使用静态路由、OSPF、BGP 等 | 提供商的 MPLS 网络；客户看不到标签 | CE–PE 协议、提供商 SLA、与其他运营商的物理隔离 |
| 互联网 + IPsec | 两端通过静态路由或隧道内的 BGP 进行控制 | 通过公共互联网传输 ESP，尽力而为 | 隧道数量、NAT 穿越、受算法影响的 MTU |
| SD-WAN | 中央控制器分发策略和路由 | WAN 边缘设备之间的 IPsec 隧道，可同时使用多个 Underlay | 控制器不可达时的行为、逐隧道路径测量、逐应用策略 |

**从控制平面和数据平面的角度理解 SD-WAN**：MEF 70.2 将 SD-WAN 服务与其下方的 Underlay 连接服务分开定义，并将站点到站点隧道（TVC）和逐应用流策略定义为不同的属性（术语见[第 5 部分](../../basics/06-network-fundamentals-part5.md#wan-types)）。在 Cisco Catalyst SD-WAN 中，SD-WAN Controllers 负责协调控制平面，并通过 OMP 对等会话交换控制信息；Validator 对设备进行身份验证，并协调 Controllers 与路由器之间的控制连接。数据通过路由器之间的 IPsec 连接传输，BFD 会在这些连接上自动运行以检测故障。因此，“SD-WAN 能快速检测故障”说的是**数据隧道上的 BFD**；控制器冗余是另一个独立的设计事项。

在 AWS 上，VPC 中的 SD-WAN 设备通过 Connect 附件使用 BGP 与 Transit Gateway 对等连接。一个 Connect 对等体（GRE 隧道）最多承载 5 Gbps，一个附件最多可有 4 个对等体。本章练习不使用 Connect，但第 8 节会在带宽比较中将其纳入。

## 3. IPsec Site-to-Site VPN

**定义**：每个 AWS Site-to-Site VPN 连接都有**两条隧道**，每条隧道都有唯一的公共 IP 地址，并分别终止于不同的可用区。请将两条隧道都配置为冗余；当其中一条隧道不可用时（例如在维护期间），流量会自动转移到该连接的另一条隧道。

**行为：**

- **IKE 版本**：隧道可以允许 IKEv1 和 IKEv2。AWS 强烈建议使用 IKEv2；只有当设备不支持 IKEv2 时才使用 IKEv1。
- **按方向使用隧道**：从本地到 AWS 的流量会使用两条隧道。从 AWS 到本地的流量优先使用一条隧道，并在 AWS 侧发生故障时切换到另一条，因此客户网关必须**允许非对称路由**。在虚拟私有网关（VGW）上，会从该网关的所有 VPN 连接中选出一条隧道作为出站路径，并且不支持 ECMP。
- **静态路由与 BGP**：如果设备支持 BGP，请选择动态路由。AWS 建议使用支持 BGP 的设备，因为 BGP 存活性检查有助于故障转移到第二条隧道。选择 BGP 后，不能同时指定静态路由。
- **ECMP**：只有在使用动态路由时，Transit Gateway 上的 VPN 才能通过 ECMP 汇聚隧道；使用静态路由的 VPN 不支持 ECMP。
- **带宽**：标准隧道最多承载 1.25 Gbps（最多 140,000 PPS）。大带宽隧道最多承载 5 Gbps，但仅适用于连接到 Transit Gateway 或 Cloud WAN 的 VPN；两条隧道必须使用相同的带宽设置，而且不能与加速 VPN 配合使用。
- **存活性**：死对等体检测（DPD）超时时间为 30 秒或更长，超时操作可以是 `Clear`（结束 IKE 会话、停止隧道并清除路由）、`None` 或 `Restart`。AWS Knowledge Center 将 VPN 的默认 BGP 保持时间列为 30 秒。
- **NAT 后的客户网关**：位于 NAT 后的网关使用 NAT 穿越（NAT-T，RFC 3948），即用 UDP 封装 ESP。第 7 节的 MTU 表显示，对相同算法启用 NAT-T 会降低 MTU。位于 CGNAT 后的分支无法首先接受入站会话（见[第 5 部分](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)），因此应将该分支设计为主动发起隧道。

**实践要点**：不要说“有两条隧道，所以冗余就完成了”。两条隧道使 AWS 端点具备冗余；但如果它们共用一个客户网关和一条互联网线路，这两者仍是单点故障。要实现客户侧冗余，请增加第二个客户网关和第二个 VPN 连接。

## 4. Direct Connect

**定义**：Direct Connect 通过标准以太网光纤，将你的网络连接到 Direct Connect 站点的 AWS 路由器。你需要在其上创建**虚拟接口（VIF）**，以访问 VPC 或 AWS 公共服务，从而绕过路径中的互联网服务提供商。你的设备必须支持 802.1Q VLAN、BGP 和 BGP MD5 身份验证。

**连接类型：**

| 类型 | 速度 | VIF | 备注 |
|---|---|---|---|
| 专用 | 1、10、100、400 Gbps | 最多 50 个公有/私有 VIF，另加最多 4 个 Transit VIF；总计 51 个（不能增加） | 单模光纤，每个端口速率采用固定的收发器标准 |
| 托管 | 合作伙伴提供的速率，从 50 Mbps 到 25 Gbps | 1 个（不能增加） | 只有符合条件的合作伙伴才提供 1 Gbps 及以上速率；只有在存在 100 Gbps 端口的站点才提供 25 Gbps。AWS 会对流量进行限速，并丢弃超出部分 |

**VIF 类型：**

- **私有 VIF**：使用私有 IP 访问 VPC。直接连接到 VGW 时，可访问同一区域中的一个 VPC；连接到 Direct Connect 网关时，可跨账户和区域访问 VGW。
- **公有 VIF**：使用公有 IP 访问 AWS 公共服务。你通告的公有前缀必须属于你，AWS 会筛选入站流量，以检查其源地址是否属于你通告的前缀。
- **Transit VIF**：可访问与 Direct Connect 网关关联的 Transit Gateway，适用于任意速率的专用或托管连接。

**Direct Connect 网关**：这是一个与 VGW、Transit Gateway 或 Cloud WAN 核心网络关联的全局资源。AWS 将其描述为一组位于数据流量路径之外的**分布式 BGP 路由反射器**，因此不会形成单点故障。与工作簿 02 中的路由反射器一样，它负责反射路由，不承载数据包。一个网关最多支持 20 个 VGW、6 个 Transit Gateway，以及 30 个私有或 Transit VIF。

**路由限制**：这些限制会直接导致中断，因此应将其纳入设计表。

- 在通过私有或 Transit VIF 从本地到 AWS 的方向上，每个 BGP 会话对 IPv4 和 IPv6 分别默认接受 100 条路由；通过前缀控制可分别提高到 1,000 条。**通告数量超过分配限额会导致 BGP 会话进入空闲状态，并报告为 DOWN。**
- 公有 VIF BGP 会话接受 1,000 条路由。
- 在通过 Transit VIF 从 AWS 到本地的方向上，每个 Transit Gateway 最多通告 200 个前缀，IPv4 和 IPv6 合计。

**允许前缀**：对于 Transit Gateway 关联，Direct Connect 网关会**精确地**通告你输入的允许前缀。如果 VPC CIDR 为 `10.20.0.0/16`，允许前缀为 `10.0.0.0/8`，则本地只会收到 `10.0.0.0/8`。相比之下，对于 VGW 关联，允许前缀相当于一个过滤器，会放行相同或更小的 CIDR。第 6 节的陷阱由此开始。

<a id="dx-lag"></a>

**LAG**：链路聚合组使用 LACP，将同一 Direct Connect 端点上的多条连接捆绑成一个逻辑连接。规则如下：

- 所有连接都必须是专用连接且带宽相同。
- 一个 LAG 最多包含 4 条低于 100 Gbps 的连接，或者最多包含 2 条 100 或 400 Gbps 的连接。
- 所有连接都必须终止于同一个 Direct Connect 端点；不支持多机箱 LAG（MLAG）。
- 所有连接均以 active/active 模式运行。LAG 有一个最小链路数属性（默认为 0）；设置该属性后，如果运行中的连接数量低于设定值，整个 LAG 就会断开，从而避免剩余连接过载。

LAG 增加的是**容量**，但它仍终止于同一位置的同一设备，因此无法抵御站点故障。正如第 5 部分所述，单个流量仍无法超过一条成员链路的带宽。请使用 Resiliency Toolkit 模型设计站点冗余：**最大韧性**的目标 SLA 为 99.99%，**高韧性**为 99.9%；前提是满足 Direct Connect SLA 中的所有要求。**开发和测试**模型则将连接分布到同一站点的不同设备上。

**MACsec**：在选定站点支持 10、100 和 400 Gbps 的**专用**连接；不支持 1 Gbps 专用连接或任何托管连接。它是逐跳的 L2 加密，因此你的设备必须与 AWS 设备直接进行 L2 邻接，并且任何最后一公里线路段都必须对 L2 透明。只支持 256 位密钥，100/400 Gbps 连接还必须使用扩展分组编号（XPN）。在 LAG 上，任何时候所有链路都使用同一个 MACsec 密钥。

## 5. Transit Gateway

**定义**：Transit Gateway 是一个区域级虚拟路由器，用于在 VPC 与本地网络之间转发流量。附件既是数据包的源，也是其目的地；可以连接 VPC、VPN 连接、VPN Concentrator、Direct Connect 网关、Connect 附件和对等连接。

**路由表规则：**

- 一个附件只能**关联一个**路由表，但可以**向多个路由表传播**路由。传播的路由无法过滤。
- 动态路由 VPN 会通过 BGP 向客户网关通告其关联路由表中的路由。Direct Connect 网关附件会通告其允许前缀。
- 对于同一目的地，静态路由优先于传播路由，而且传播路由不会显示在表中。
- Transit Gateway 只显示优选路由。相同路由通过 DX 和 VPN 到达时，表中显示 DX 路由；只有在 DX 路由不再通告后，VPN 路由才会出现。
- 对等附件仅支持静态路由。

**路由评估顺序**：首先由最长前缀匹配的路由胜出。对于来自不同附件类型的相同 CIDR，优先级如下：

1. 静态路由（例如 Site-to-Site VPN 静态路由）
2. 系统路由（用于 1:1 NAT）
3. 前缀列表引用路由
4. VPC 传播路由
5. Direct Connect 网关传播路由
6. Transit Gateway Connect 传播路由
7. 经由私有 Direct Connect 的 Site-to-Site VPN 传播路由
8. Site-to-Site VPN 传播路由
9. Site-to-Site VPN Concentrator 传播路由
10. Client VPN 传播路由
11. Transit Gateway 对等连接（Cloud WAN）传播路由

只有在来自**同一附件类型**且 CIDR 相同的情况下，才会比较 BGP 属性：先比较较短的 AS_PATH，然后是较低的 MED，最后是在支持的情况下优先 eBGP 而非 iBGP。未通告 MED 的路由，在 Direct Connect 附件上默认使用 0，在 VPN 和 Connect 附件上默认使用 100。不同附件类型之间不支持 ECMP（例如 VPN 和 VPC）；此时会依据上述评估顺序选出一条路由。

**MTU 和带宽**：VPC、Direct Connect、Connect 和对等附件之间的流量 MTU 为 8500 字节；通过 VPN 的流量 MTU 为 1500。Transit Gateway 会对所有数据包执行 MSS 钳制。路径 MTU 发现（PMTUD）仅支持从 VPC 和 Connect 附件进入的流量，不支持从 VPN、Direct Connect 或对等附件进入的流量。每个可用区中，VPC 附件和 Direct Connect 网关的带宽均最高可达每个方向 100 Gbps。

<a id="failover-design"></a>

## 6. 故障转移设计：DX 主用，VPN 备用

请**按方向**阅读本节。从本地到 AWS 的路径由**你的路由器策略**决定；从 AWS 到本地的路径由**AWS 的评估顺序**决定。只更改一侧会导致路径不对称，有状态防火墙可能会丢弃响应流量。

![混合网络故障转移动画。① 本地路由器（AS 65010，10.10.0.0/16）通过 DX 和 VPN 学到两条通往 VPC 10.20.0.0/16 的 BGP 路径，选择 LOCAL_PREF 为 200 的 DX 路径，并通过 DX 连接的 802.1Q VLAN 101（Transit VIF）向 10.20.1.10 发送数据包。② 数据包经过 DX 站点后到达 Transit Gateway，目的地址保持不变，TGW 路由表将其转发到 VPC 附件。DX 网关只反射 BGP 路由，不在数据路径中。③ DX 链路被切断。当 BFD 在 300 毫秒间隔内连续漏掉三次响应后，BGP 会话断开，DX 路由在两侧撤销，本地路由器的最佳路径切换到 LOCAL_PREF 为 100 的 VPN 隧道。④ 下一个数据包经 VPN 路径传输：IPsec 添加 ESP 和外层 IP 标头（源地址 203.0.113.10，目的地址 198.51.100.10），数据包经过互联网。⑤ 在 Transit Gateway 的 VPN 附件上，ESP 被移除，原始目的地址为 10.20.1.10 的数据包被转发到 VPC。由于 DX 路由已不存在，返回流量也使用 VPN 传播路由。](../../.gitbook/assets/en-networking-expert-07-wan-hybrid-connectivity-anim-0.svg)

### AWS 到本地：AWS 选择的路径

**在 Transit Gateway 上**，第 5 节中的评估顺序照常适用：

1. **先匹配最长前缀**。如果本地通过 VPN 通告 `10.10.1.0/24`，通过 DX 通告 `10.10.0.0/16`，发往 `10.10.1.0/24` 的流量会经 VPN 传输。要保持 DX 为主用路径，必须在两条路径上通告**相同的前缀**。
2. **对于相同 CIDR，附件类型优先于 AS_PATH**。DX 网关传播的路由始终优先于 VPN 传播的路由，因此在 VPN 通告中添加 AS_PATH 前缀不会改变 DX 与 VPN 之间的选择。反过来，VPN 上的**静态路由**优先于 DX 传播路由，会在不易察觉的情况下使 VPN 成为主用路径。请使用 BGP 构建备用 VPN。
3. **只有在同一类型内部才比较 BGP 属性**，例如在多个 DX VIF 之间或多个 VPN 连接之间比较。

**在 VGW 上**，顺序有所不同：对于相同前缀，Direct Connect BGP 路由优先于 VPN 静态路由，后者又优先于 VPN BGP 路由；在 VPN BGP 路由之间，较短的 AS_PATH 优先，然后在第一个 AS 相同的情况下比较较低的 MED。不要混淆这两套顺序。

**在多个 DX VIF 之间**，AWS 按以下顺序比较私有和 Transit VIF 路由：

| 顺序 | 条件 | 设计中的用法 |
|---|---|---|
| 1 | 最长前缀 | 使用更具体的路由表达主用/备用关系 |
| 2 | 本地优先级社区 | `7224:7300`（高）、`7224:7200`（中）、`7224:7100`（低）；标准社区，在 AS_PATH 之前评估。路由目标等扩展社区不会用于优先级评估，并且可能会被移除 |
| 3 | AS_PATH 长度 | 前缀和本地优先级相同时，通过添加 AS_PATH 前缀进行调整 |
| 4 | MED | 优先级最低；AWS 不建议依赖 MED |
| 平局 | ECMP | AS_PATH 长度和属性相同时，通过多个 VIF 分担负载 |

如果没有社区，AWS 会优先选择**与该区域关联的** Direct Connect 站点。对于 active/active，请为所有 VIF 设置相同的社区（例如 `7224:7200`）；对于 active/passive，请为主用 VIF 设置 `7224:7300`，为备用 VIF 设置 `7224:7100`。这些社区决定**返回本地**流量的优先级。

**环路预防**：如果路由的 AS_PATH 中包含 Direct Connect ASN `7224` 两次或更多次，AWS 会将其视为环路且不会安装该路由。当从 AWS 通过一个 VIF 学到的路由又经由另一个 VIF 重新通告时，就会出现这种情况；请在向 AWS 通告的路由中滤除从 AWS 学到的路由。

### 本地到 AWS：路由器选择的路径

AWS 会通过 DX（允许前缀）和 VPN（TGW 路由表中的路由）通告相同的 VPC 路由。你的路由器会根据工作簿 02 中的 BGP 选路规则进行比较，因此提高从 DX 学到的路由的 LOCAL_PREF 会使 DX 成为主用路径。动画中的 LOCAL_PREF 200/100 就是这一策略。

**允许前缀陷阱**：如果允许前缀汇总为 `10.0.0.0/8`，而 VPN 从 TGW 路由表通告 `10.20.0.0/16`，你的路由器会选择**更长的 VPN 前缀**。LOCAL_PREF 只会比较同一前缀的路径，无法解决此问题。请使允许前缀的长度与 VPN 侧相同，或者在路由器上以相同方式汇总从 VPN 学到的路由。

### 检测时间预算

| 机制 | 数值 | 来源性质 |
|---|---|---|
| DX 上的 BFD | AWS 侧会自动启用异步 BFD，但只有在路由器上配置后才会生效；最小间隔为 300 毫秒，乘数为 3 | Direct Connect 常见问题和用户指南 |
| DX BGP（未启用 BFD） | 在没有 keepalive 的情况下，会话在 90 秒保持时间后断开 | AWS Knowledge Center |
| VPN BGP | 默认保持时间为 30 秒 | AWS Knowledge Center |
| VPN DPD | 30 秒或更长；超时操作为 `Clear`、`None` 或 `Restart` | VPN 用户指南 |

BFD 检测到故障时，BGP 邻居关系会快速断开，而不必等待保持时间到期。根据 RFC 5880，BFD 检测时间等于远端乘数乘以协商出的间隔，因此 300 毫秒 × 3 约为 0.9 秒。但**检测时间并非恢复时间**。恢复时间还包括路由撤销和传播、两台路由器上的 FIB 编程，以及反向流量的路径切换；AWS 没有公布这些环节的固定数值。在设计文档中，请引用检测数值，并将其余部分标记为**测量前的假设**，同时采用工作簿 02 中的测量点（操作时间、首次变化、FIB 变化、持续恢复）。

## 7. 隧道中的 MTU 和 MSS

| 网段 | MTU | 备注 |
|---|---|---|
| Site-to-Site VPN | 最多 1446 字节，MSS 1406 | 不支持巨型帧和路径 MTU 发现；使用某些算法和 NAT-T 时数值更低 |
| 私有 VIF | 1500 或 9001 | 链路层帧为 1522 或 9023 字节 |
| Transit VIF | 1500 或 8500 | Transit Gateway 上的巨型帧只支持 8500 |
| Transit Gateway | VPC、DX、Connect、对等连接之间为 8500；VPN 上为 1500 | 对所有数据包执行 MSS 钳制；只有从 VPC 和 Connect 入口进入的流量支持 PMTUD |

例如，AWS 推荐的 VPN MTU/MSS 数值如下（IPv4 MSS）：

| 加密 | 完整性 | NAT-T | MTU | MSS |
|---|---|---|---|---|
| AES-GCM-16 | 不适用 | 禁用 | 1446 | 1406 |
| AES-GCM-16 | 不适用 | 启用 | 1438 | 1398 |
| AES-CBC | SHA1/SHA2-256 | 禁用 | 1438 | 1398 |
| AES-CBC | SHA2-512 | 启用 | 1406 | 1366 |

**行为：**

- AWS 建议客户网关在**加密之前**进行分片。VPN 会在转发前重新组装分片，因此还要检查重新组装后的数据包是否适合下一网段（例如 Direct Connect）。
- 将 VIF 改为巨型 MTU 可能会更新底层连接，从而导致该连接上的每个 VIF 中断最多 30 秒；请在维护窗口内进行更改。
- 如果两个私有 VIF 通告相同路由但 MTU 不同，或者 Site-to-Site VPN 通告相同路由，则会使用 MTU 1500。

**设计要点**：在故障转移设计中，**真正重要的是备用路径的 MTU**。通过较大 MSS 的 DX 建立的 TCP 连接切换到 VPN 后，如果路径网段不支持 PMTUD，设置了 DF 标志的大数据包可能会被悄然丢弃。在本练习中，请比较两种方案：在路由器上将混合流量的 MSS 钳制为所选算法对应的 VPN 数值，或者在 VPN 作为备用路径时将 VIF 保持在 1500。

## 8. 带宽、延迟和成本权衡

| 连接 | 带宽（官方限制） | 延迟和质量 | 冗余单位 | 成本项目 |
|---|---|---|---|---|
| 专用 DX | 1/10/100/400 Gbps，可通过 LAG 捆绑 | 专用路径，绕过互联网服务提供商 | 连接、设备、站点（Resiliency Toolkit 模型） | 端口使用时长、出站数据传输 |
| 托管 DX | 50 Mbps 至 25 Gbps | 经过合作伙伴网络；AWS 会限制到合同速率 | 每个托管连接、合作伙伴网络 | 相同的 AWS 费用项目，另加合作伙伴费用 |
| 标准 VPN 隧道 | 每条隧道最高 1.25 Gbps、140,000 PPS | 互联网路径，尽力而为 | 两条隧道（AWS 侧）；客户网关和线路是独立的 | 连接使用时长、出站数据传输、每条隧道的公有 IPv4 地址 |
| VPN 大带宽隧道 | 每条隧道最高 5 Gbps（仅适用于 TGW 和 Cloud WAN） | 与标准隧道相同；MTU 限制相同 | 同上 | 单独的连接使用时长价格 |
| TGW 上的 VPN ECMP | 多条动态路由隧道的带宽总和 | 按流分配；单个流受单条隧道带宽限制 | 每条隧道和连接 | VPN 费用，加上 TGW 附件使用时长和按 GB 计费的处理费用 |
| Connect（SD-WAN） | 每个对等体 5 Gbps，每个附件 4 个对等体 | 取决于下层传输（VPC 或 DX） | 每个对等体和附件 | TGW 附件使用时长，加上传输附件的处理费用 |

Transit Gateway 按附件使用时长收费，并按从 VPC、Direct Connect 和 VPN 附件处理的数据 GB 数收费。单位价格会随区域和时间变化，因此设计中只记录**成本项目**；请在核对当日根据定价页面计算金额。

## 9. 设计练习：两个站点和一个区域

这是一次不会创建任何资源的桌面检查。请将结果标记为**设计审查**。

**输入：**

| 位置 | 地址和 ASN | 连接方式 |
|---|---|---|
| 站点 A（总部数据中心） | `10.10.0.0/16`，AS 65010 | 在两个不同的 DX 站点（DX-1、DX-2）各有一条 10 Gbps 专用连接，每条连接上各有一个 Transit VIF；一条互联网线路和一个客户网关 |
| 站点 B（分支） | `10.30.0.0/16`，AS 65030 | 两条来自不同运营商的互联网线路，每条线路各有一个客户网关和一个 VPN 连接；无 DX |
| 区域 | VPC `10.20.0.0/16`、一个 Transit Gateway（示例 Amazon ASN 64512）、一个 Direct Connect 网关（示例 ASN 64513） | DX 网关和三个 VPN 均连接到同一个 TGW |

站点 A 到站点 B 的流量使用现有 MPLS 服务，不在本练习范围内。假设所有 VPN 都使用 BGP、IKEv2 和禁用 NAT-T 的 AES-GCM。

**服务级目标**：这些是学习者的设计目标，不是 AWS SLA。

- 站点 A → VPC：任何一条 DX 连接、设备或站点故障时，仍保持至少 5 Gbps 的带宽；并力争在检测到故障后 5 秒内恢复两个方向的数据路径。如果两条 DX 连接都故障，允许通过 VPN 降级运行。
- 站点 B → VPC：一条线路或一个客户网关发生故障时仍保持连接；在 BGP 保持时间内完成切换即可接受。

**任务：**

1. **通告表**：对于每条路径，记录由谁通告哪些前缀：DX 网关的允许前缀、每个 VPN 接收的 TGW 路由表路由，以及站点 A 和 B 向 AWS 通告的内容。与配额进行比较（每个 DX BGP 会话默认 100 条、每个 TGW 200 条）。
2. **策略表**：设置站点 A 的 LOCAL_PREF（DX-1、DX-2、VPN）、DX VIF 上的本地优先级社区，以及 TGW 路由表的关联和传播。根据 5 Gbps 目标，决定两条 DX 连接采用 active/active 还是 active/passive。
3. **路径预测**：对于下列每种情形，记录站点 A → VPC、VPC → 站点 A、站点 B → VPC 和 VPC → 站点 B 的路径，以及选中该路径的**规则步骤**（例如，“TGW 评估顺序第 5 步，DX 网关传播路由”）。
4. **时间预算**：对于每种情形，记录检测机制及其数值，列出在测量前暂作假设的项目，并判断是否达到目标。
5. **MTU 决策**：选择 Transit VIF 的 MTU 和站点 A 的 MSS 钳制值，并说明理由。

| 情形 | 站点 A → VPC | VPC → 站点 A | 应用的规则 | 检测 | 剩余带宽 | 结论 |
|---|---|---|---|---|---|---|
| 正常 | | | | | | |
| DX-1 连接故障 | | | | | | |
| DX 站点 1 完全故障 | | | | | | |
| DX-1 和 DX-2 均故障 | | | | | | |
| DX-1 故障，但站点 A 路由器未配置 BFD | | | | | | |
| 站点 B 一条线路故障 | | | | | | |
| DX-1 恢复 | | | | | | |

**审查标准**：每个单元格至少引用一条源文档中的规则。请自查：

- 是否依据 TGW 评估顺序，而不是“DX 更快”来解释正常状态下 VPC → 站点 A 使用 DX？
- 是否避免在 VPN 上使用静态路由？如果使用了，是否发现即使在正常状态下 VPN 也会胜出？
- 允许前缀和 VPN 通告的前缀长度是否相同？如果不同，哪个方向的流量会转移到 VPN？
- 是否发现未启用 BFD 的情形无法达到 5 秒目标（BGP 保持时间为 90 秒）？
- 两条 DX 连接都断开时，是否记录了带宽会降到 VPN 限制（每条标准隧道 1.25 Gbps，使用 ECMP 时为隧道带宽总和），且单个流不能超过一条隧道的带宽？
- 是否根据备用路径确定了 MTU？

## 10. 观察故障和恢复

如果没有真实环境，本节用于练习判断**哪些证据能够确定每个结论**。如果之后有机会在获批的现有环境中复现某种情形，请收集这些证据。

| 层 | 查看内容 | 单凭这些证据无法确定的事项 |
|---|---|---|
| 你的路由器的 BGP 表 | 两条候选路径、LOCAL_PREF、最佳路径标记 | AWS 侧的返回路径 |
| 你的路由器 FIB 和数据包捕获 | 实际出口接口、隧道接口上的 ESP | 所有应用流量是否都成功 |
| TGW 路由表 | 唯一的优选路由；只有 DX 路由撤销后，备用 VPN 路由才会出现 | 数据包实际经过的路径 |
| CloudWatch | VPN `TunnelState`、DX VIF `VirtualInterfaceBgpStatus` | 数据平面丢包的开始和结束时间 |
| 源地址特定探测 | 丢包时段、持续恢复的开始时间 | 大数据包或所有端口 |

**故障恢复切回也算一次故障**。DX 恢复且 BGP 重新建立后，TGW 上 DX 网关传播路由会再次胜出，你的路由器上 LOCAL_PREF 较高的 DX 路由也会再次胜出，因此流量会**自动**切回，并再次发生路径和 MTU 变化。链路不稳定可能导致路径反复切换；请预先定义持续恢复的判据（例如连续收到响应以及观察窗口）。与工作簿 02 一样，观测到零丢包只表示采样分辨率未捕捉到中断。

## 11. 交付成果和完成标准

| 交付成果 | 完成条件 |
|---|---|
| 拓扑图 | 会话和数据链路有所区分，且 DX 网关位于数据路径之外 |
| 通告表和策略表 | 已记录并根据配额核验允许前缀、VPN 通告、LOCAL_PREF、社区以及 TGW 关联/传播 |
| 情形表 | 七种情形均列出了两个方向的路径、应用的规则、检测数值、剩余带宽和结论 |
| MTU 决策 | 根据备用路径确定了 MSS 数值，并注明其来源表格 |
| 未知项列表 | 对于未公布固定数值的项目（例如路由传播时间和 FIB 编程时间），均标记为测量前的假设 |

当你能够结合来源解释每个方向的选路规则、附件类型顺序与 AS_PATH 的关系、允许前缀陷阱、检测时间与恢复时间的区别，以及为什么备用路径决定 MTU 时，就算完成了。将结果表用于[自动化综合项目](06-automation-capstone.md)的变更审查，然后继续学习[云和 CNI 设计](05-cloud-cni-design.md)中的云内路径。跨组织 VPC 选项请参阅[跨组织 VPC 连接](../05-cross-org-vpc-connectivity.md)，EKS Hybrid Nodes 网络要求请参阅[Hybrid Nodes 网络配置](../../eks-hybrid-nodes/02-network-configuration.md)。最后，请完成[测验](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md)。

## 参考资料

AWS Direct Connect

- [什么是 Direct Connect？](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html)（VIF 类型、网络要求、BFD、定价项目）
- [Direct Connect 配额](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)
- [托管连接](https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html)
- [虚拟接口和 MTU](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)
- [路由策略和 BGP 社区](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)
- [Direct Connect 网关](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html)、[允许前缀交互](https://docs.aws.amazon.com/directconnect/latest/UserGuide/allowed-to-prefixes.html)
- [链路聚合组](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)、[MAC 安全](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html)、[Resiliency Toolkit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)
- [Direct Connect 常见问题](https://aws.amazon.com/directconnect/faqs/)（BFD 默认值、支持 MACsec 的连接）
- [AWS Knowledge Center：为 Direct Connect 启用 BFD](https://repost.aws/knowledge-center/enable-bfd-direct-connect)（未启用 BFD 时的 90 秒 BGP 保持时间）
- [Direct Connect 虚拟接口 BGP 健康状况的 CloudWatch 指标](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudwatch-metrics-for-aws-direct-connect-virtual-interface-bgp-health-and-prefix-count/)

AWS Site-to-Site VPN

- [隧道选项](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html)、[配置隧道选项](https://docs.aws.amazon.com/vpn/latest/s2svpn/tunnel-configure.html)
- [路由选项](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html)、[静态路由和动态路由](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-static-dynamic.html)、[路由表和路由优先级](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-route-priority.html)
- [Site-to-Site VPN 配额](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html)（带宽、PPS、MTU、路由数量）
- [客户网关设备最佳实践](https://docs.aws.amazon.com/vpn/latest/s2svpn/cgw-best-practice.html)（IKEv2、加密前分片、逐算法的 MTU/MSS）
- [使用 CloudWatch 监控 VPN 隧道](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [AWS Knowledge Center：使用 BGP 日志排查 VPN 隧道问题](https://repost.aws/knowledge-center/vpn-bgp-logs-troubleshoot-tunnel)（默认保持时间为 30 秒）
- [AWS VPN 定价](https://aws.amazon.com/vpn/pricing/)

AWS Transit Gateway

- [AWS Transit Gateway 的工作原理](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)（附件、关联和传播、路由评估顺序、ECMP）
- [Transit Gateway 配额](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html)（带宽、MTU、MSS 钳制、PMTUD）
- [AWS Transit Gateway 定价](https://aws.amazon.com/transit-gateway/pricing/)

标准和供应商文档

- [RFC 5880：双向转发检测](https://www.rfc-editor.org/rfc/rfc5880.html)
- [RFC 7296：IKEv2](https://www.rfc-editor.org/rfc/rfc7296.html)、[RFC 4303：ESP](https://www.rfc-editor.org/rfc/rfc4303.html)、[RFC 3948：IPsec ESP 数据包的 UDP 封装](https://www.rfc-editor.org/rfc/rfc3948.html)
- [RFC 4271：BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html)、[RFC 1997：BGP 社区](https://www.rfc-editor.org/rfc/rfc1997.html)、[RFC 6996：私有用途的自治系统编号保留](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)、[RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)（示例地址）
- [MEF 70.2：SD-WAN 服务属性和服务框架](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)
- [Cisco Catalyst SD-WAN 高可用性配置指南](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html)

考试范围（仅用于选择主题）

- [AWS Certified Advanced Networking - Specialty (ANS-C01) 考试指南](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
- [Cisco 350-401 ENCOR](https://www.cisco.com/site/us/en/learn/training-certifications/exams/encor.html)
