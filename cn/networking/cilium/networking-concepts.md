# 深入了解网络概念

> **审查基线**：Cilium 1.20.3。
> **最后审阅日期**：2026 年 10 月 16 日。

本文深入解释了理解 Cilium 所需的核心网络概念，涵盖容器网络、Overlay、NAT、路由、DNS、负载均衡和策略。示例是概念性示例，或为预先准备的测试环境提供的部分 Helm/API 配置，并非完整的安装或迁移方案。请在 [Cilium 概览](README.md)中核实平台和版本前提条件；并非所有托管平台都支持相同的 CNI 功能。

## 学习目标

阅读本文后，你将了解：
- OSI 模型和 TCP/IP 协议栈的基本结构，以及各层的作用
- 容器网络的基本原理和实现方式
- Overlay 网络与 Underlay 网络的区别
- NAT、路由和 DNS 等核心网络概念在 Cilium 中的应用方式

## 目录

1. [OSI 模型和 TCP/IP 协议栈](#osi-model-and-tcp-ip-stack)
2. [容器网络基础](#container-networking-basics)
3. [Overlay 网络](#overlay-networks)
4. [网络地址转换（NAT）](#network-address-translation-nat)
5. [路由协议](#routing-protocols)
6. [DNS 和服务发现](#dns-and-service-discovery)
7. [负载均衡概念](#load-balancing-concepts)
8. [网络安全基础](#network-security-basics)

## OSI 模型和 TCP/IP 协议栈

> **关键概念**：OSI 模型是一个概念框架，将网络通信划分为 7 个抽象层，从而更容易理解复杂的网络处理过程。

OSI（开放系统互连）模型是一个概念框架，将网络通信划分为 7 个抽象层。每一层负责特定的网络功能，因此可以将复杂的网络处理过程拆分开来，以便于理解。

### OSI 模型与 TCP/IP 模型对照

![示意图展示了 OSI 七个参考层与 TCP/IP 协议栈四层之间的映射，并在每个 OSI 层下方列出了代表性协议。](../../.gitbook/assets/en-networking-cilium-networking-concepts-0.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-0.html)

这种映射是用于教学的近似表示，并非协议实现规范。图中的 SSL 是过时的标签；当前系统应使用受支持的 TLS 版本。

### OSI 七层模型

1. **物理层**
   - 将比特流转换为电信号、光信号或无线信号
   - 包括电缆、收发器和物理信号传输；交换机也实现更高层的功能
   - 数据单元：比特

2. **数据链路层**
   - 负责物理网络中节点之间的数据传输
   - 使用 MAC（媒体访问控制）地址标识设备
   - 错误检测，以及在链路协议提供相应能力时进行恢复；以太网的错误检测本身不会修复受损帧
   - 数据单元：帧
   - 以太网和 Wi-Fi 协议在此层运行

3. **网络层**
   - 负责不同网络之间的数据包路由
   - 逻辑寻址（IP 地址）
   - 路径确定和数据包转发
   - 数据单元：数据包
   - IP（互联网协议）是此层的核心协议

4. **传输层**
   - 端到端通信控制
   - 数据分段和重组
   - TCP 提供流量控制和重传；UDP 不提供这些保证
   - 数据单元：TCP 段或 UDP 数据报
   - TCP（传输控制协议）和 UDP（用户数据报协议）是此层的主要协议

5. **会话层**
   - 建立、维护和终止通信会话
   - 同步和对话控制
   - 设置检查点和恢复
   - 可以从此层讨论会话管理；实际的 RPC 实现不一定映射到单个 OSI 层

6. **表示层**
   - 数据格式转换和加密
   - 字符编码、数据压缩、加密/解密
   - 编码/压缩可用于说明此层的职责；TLS 是一种互联网协议，并非字面意义上的 OSI 表示层实现

7. **应用层**
   - 为应用提供网络服务，不一定是图形用户界面
   - 电子邮件、文件传输、网页浏览等服务
   - HTTP、FTP、SMTP、DNS 是此层的示例

### Cilium 与 OSI 模型的关系

Cilium 在多个 OSI 层运行：

| OSI 层 | Cilium 功能 | 示例 |
|-----------|----------------|---------|
| L2（数据链路层） | 链路级可达性；可选的 L2 Announcements | 对已配置的 Service VIP 做出 ARP/NDP 响应 |
| L3（网络层） | IP 路由、基于 CIDR 的策略 | Pod 之间的 IP 路由 |
| L4（传输层） | 基于端口的过滤、连接跟踪 | Service 端口访问控制 |
| L7（应用层） | 受支持的 HTTP/gRPC 和 DNS 代理规则 | HTTP 路径策略或 DNS 查询策略 |

在此基线版本中，L2 Announcements 仍处于 Beta 阶段，并且需要配置其控制器/设备。它不同于通用的 MAC 地址安全策略接口。

### TCP/IP 协议栈

TCP/IP 协议栈是一组构成互联网基础的协议。这种架构通常描述为四层，并与 OSI 模型进行对照；它并非七层模型的直接实现。

1. **网络接口层**
   - 对应 OSI 模型的物理层和数据链路层
   - 负责与物理网络介质连接
   - 包括以太网和 Wi-Fi 等协议

2. **互联网层**
   - 对应 OSI 模型的网络层
   - 使用 IP（互联网协议）进行数据包路由
   - 包括 ICMP（互联网控制消息协议）；ARP 在链路边界解析 IPv4 下一跳的链路层地址，而 IPv6 使用邻居发现

3. **传输层**
   - 与 OSI 模型的传输层相同
   - 包括 TCP 和 UDP 协议
   - 提供面向连接（TCP）和无连接（UDP）通信

4. **应用层**
   - 整合 OSI 模型的会话层、表示层和应用层
   - 包括 HTTP、SMTP、FTP、DNS 等协议
   - 为用户应用与网络之间提供接口

### Cilium 各层功能

Cilium 在多个网络层提供功能：

- **L2（数据链路层）**：链路可达性和可选的 L2 Service 通告；这不是通用的 MAC 地址 NetworkPolicy API，也不提供普遍适用的 ARP 欺骗防护
- **L3（网络层）**：基于 IP 地址的路由和过滤、IPAM
- **L4（传输层）**：基于端口的过滤、负载均衡、连接跟踪
- **L7（应用层）**：已配置的 HTTP/gRPC 代理功能和 DNS 策略；早期的 Kafka L7 策略 API 已移除

## 容器网络基础

容器网络是一种机制，允许容器化应用彼此通信并与外部世界通信。Kubernetes 等容器编排平台使用各种网络模型和解决方案。

### 容器网络接口（CNI）

CNI（容器网络接口）定义了容器运行时与网络插件之间的标准接口。当前的 Kubernetes 使用 CRI 容器运行时来调用 CNI 插件。该接口允许采用多种网络实现；CNI 规范并未要求每个插件都实现 Kubernetes NetworkPolicy。

#### CNI 的主要组件：

1. **插件**：负责创建和配置网络接口的可执行程序
2. **配置文件**：用于定义插件行为的 JSON 格式文件
3. **IPAM（IP 地址管理）**：负责分配和管理 IP 地址的模块

#### CNI 插件的主要职责：

- 在容器网络命名空间中添加/移除网络接口
- 分配和释放 IP 地址
- 配置路由表
- 网络实现可以另外提供策略控制器/数据路径强制执行功能；策略并非 CNI 执行操作的必选项

### 容器网络模型

容器网络模型有多种，分别适用于不同的使用场景和需求。

#### 1. Bridge 网络

- 在主机上创建虚拟网桥以连接容器
- 每个容器通过虚拟以太网（veth）对连接到网桥
- 同一主机上的容器之间可以高效通信
- 默认网桥是独立 Linux Docker 的一个示例；它不是 Kubernetes 或 Cilium 的网络模型

![示意图展示了两个容器分别通过一对 veth 连接到 Docker 主机上的 Linux 网桥 docker0，网桥再通过 eth0 将流量转发到主机网络。](../../.gitbook/assets/en-networking-cilium-networking-concepts-1.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-1.html)

这是使用示例地址的 Linux Docker 网桥示例。主机的路由/NAT 路径经过简化；这不是 Cilium 的默认网桥拓扑。

#### 2. Host 网络

- 容器直接使用主机的网络命名空间
- 没有单独的网络隔离
- 无需单独的容器网络命名空间；性能仍取决于实际工作负载和路径
- 可能发生端口冲突

![示意图展示了同一主机中的两个容器直接共享主机网络栈（eth0，192.168.1.10），两者之间没有单独的网络命名空间或隔离层。](../../.gitbook/assets/en-networking-cilium-networking-concepts-2.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-2.html)

此处的“无隔离”是指共享网络命名空间，并不表示进程、文件系统或其他容器隔离边界都被移除。

#### 3. Overlay 网络

- 支持多个主机上的容器相互通信
- 使用 VXLAN 和 GENEVE 等封装协议
- 适用于大规模集群
- Cilium、Calico、Flannel 等均支持

![示意图展示了两台主机，每台主机都运行一个位于 10.0.0.0/24 Overlay 网络中的容器。数据包在主机 A 的 eth0 上进行封装，经由物理网络中的 VXLAN 隧道传输，然后在主机 B 的 eth0 上解封装并交付给对端容器。](../../.gitbook/assets/en-networking-cilium-networking-concepts-3.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-3.html)

这个通用 VXLAN 示意图使用标准 UDP 4789 端口和共享 L2 子网。Cilium 的默认 VXLAN 端口是 8472；其 Pod CIDR 分配必须遵循所选的 IPAM 模式，而不能照搬此图。

#### 4. Underlay 网络（直接路由）

- 直接利用物理网络基础设施
- 没有封装开销
- 需要控制网络基础设施
- 可以集成 BGP 等路由协议

![示意图展示了两台主机，它们通过本地路由表将容器流量直接路由到物理网络，不进行封装。](../../.gitbook/assets/en-networking-cilium-networking-concepts-4.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-4.html)

图中的条目展示的是主机路由。实际部署仍然需要可达的下一跳，以及适用于 Pod 地址的有效正向/返回路由。

### Kubernetes 网络模型

Kubernetes 网络模型提供 Pod 之间的直接连接，**除非有意进行网络分段**：

1. Pod 可以在 Pod 网络中直接与其他 Pod 通信，无需强制经过代理或 NAT。
2. 节点代理必须能够与**该节点上的 Pod**通信。这并不意味着要求每台主机都能访问每个 Pod。
3. 外部连接遵循集群的路由和安全策略；不要求能够不受限制地访问互联网。

NetworkPolicy 是否生效取决于网络实现是否具备相应能力。即使已安装的插件不执行策略，API 仍可能存在。

#### Kubernetes 网络组件：

1. **Pod 网络**：连接集群中所有 Pod 的网络
2. **Service 网络**：为一组 Pod 提供稳定端点
3. **集群 DNS**：用于服务发现的 DNS 服务
4. **Ingress/Egress**：管理与集群外部的通信

### Cilium 的容器网络方案

Cilium 利用 eBPF 提供高性能、可扩展的容器网络解决方案：

1. **基于 eBPF 的数据路径**：在内核中直接处理数据包
2. **支持多种网络模式**：Overlay（VXLAN、Geneve）和原生路由；通用 Helm 默认使用 VXLAN 隧道模式，但平台配置可能会覆盖此默认值
3. **高级负载均衡**：kube-proxy replacement 功能
4. **网络策略**：L3-L7 层的细粒度策略
5. **集成 IPAM**：支持多种 IP 地址分配策略

不带平台覆盖项的通用 Helm 安装默认使用 cluster-pool IPAM：operator 分配节点 CIDR，agent 从各自节点的地址池中分配 Pod IP。`ipam.mode: kubernetes` 使用 Node 的 `spec.podCIDR`/`spec.podCIDRs`。ENI 模式使用 EC2 接口和 VPC 地址；这并非适用于所有 EKS 计算模式的通用建议。请参阅 [IPAM 和策略](04-ipam-policy.md)。

## Overlay 网络

Overlay 网络是一种在现有网络基础设施之上构建虚拟网络层的技术。这项技术允许在不受物理网络拓扑影响的情况下创建虚拟网络拓扑。在容器环境中，它被广泛用于实现跨多个主机的容器通信。

### Overlay 网络的工作原理

Overlay 网络通过封装技术运行。原始数据包会被封装在其他数据包中，并通过物理网络传输。

1. **数据包封装**：在原始数据包（内部数据包）外添加新的报头，有时也会添加新的尾部。
2. **隧道传输**：封装后的数据包通过物理网络传输到目标主机。
3. **数据包解封装**：在目标主机上移除外层报头并提取原始数据包。
4. **数据包转发**：将原始数据包转发到目标容器。

### 主要 Overlay 网络协议

#### VXLAN（可扩展虚拟局域网）

VXLAN 是容器网络中最广泛使用的 Overlay 协议之一。

- **VXLAN 隧道端点（VTEP）**：负责数据包的封装和解封装
- **VXLAN 网络标识符（VNI）**：一个 24 位字段，可表示 16,777,216 个值；这并不代表 Cilium 支持的租户/端点容量
- **UDP 封装**：标准 VXLAN 使用 UDP 4789 端口；Cilium 默认的 VXLAN 隧道端口是 UDP 8472
- **MAC-in-UDP 封装**：将原始 L2 帧封装进 UDP 数据包

VXLAN 数据包结构：

![VXLAN 封装数据包示意图，展示了外层以太网、IP 和 UDP 报头包裹着 VXLAN 报头，而 VXLAN 报头又包裹着原始以太网帧、IP 报头、TCP/UDP 报头和负载。](../../.gitbook/assets/en-networking-cilium-networking-concepts-5.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-5.html)

这是通用 VXLAN 在线格式。UDP 4789 和 24 位 VNI 描述的是标准；Cilium 默认使用 UDP 8472，并使用 Overlay 元数据表示身份。字段宽度并不保证集群容量。

#### GENEVE（通用网络虚拟化封装）

GENEVE 是一种更灵活的 Overlay 协议，旨在克服 VXLAN 的局限性。

- **可扩展选项报头**：支持各种元数据
- **与协议无关**：可用于各种虚拟化技术
- **UDP 封装**：通过 UDP 6081 端口传输
- **灵活的隧道**：支持各种网络虚拟化需求

#### IPsec

IPsec 是一套在 IP 数据包层提供安全服务的协议。

- **身份验证和加密**：IPsec 提供完整性/身份验证机制，并可根据所选模式提供机密性
- **传输模式和隧道模式**：支持各种部署场景
- **安全关联（SA）**：定义通信双方之间的安全参数
- **互联网密钥交换（IKE）**：一种通用的 IPsec 协商机制。Cilium 的 IPsec 配置则使用管理员提供的 Secret 密钥，并遵循其文档说明的轮换流程

### Overlay 网络的优缺点

#### 优点：

- **灵活性**：可以独立于物理网络拓扑配置虚拟网络
- **可扩展性**：支持大型网络网段和大量端点
- **隔离性**：正确配置后，逻辑网段可以隔离流量；仅有封装并不等于身份验证、加密或完整的策略边界
- **兼容性**：可以与现有网络基础设施配合使用

#### 缺点：

- **开销**：封装会增加数据包大小和处理开销
- **MTU 注意事项**：封装会降低最大传输单元（MTU）
- **复杂性**：故障排查和调试可能更复杂
- **延迟**：封装会增加处理工作；应针对所选实现和卸载功能测量实际影响

### Cilium 中的 Overlay 网络

Cilium 支持 VXLAN 和 Geneve 等 Overlay 协议，并利用 eBPF 高效处理数据包。

- **eBPF 辅助的 VXLAN 处理**：BPF 程序本身不会构建 VXLAN 报头；它们会设置隧道元数据（`bpf_skb_set_tunnel_key`）并重定向到基于流的 `cilium_vxlan`（或 `cilium_geneve`）设备，由内核的 VXLAN/Geneve 驱动进行封装和解封装。请参阅 [Overlay 和原生路由](09-overlay-native-routing.md)
- **高效路由**：通过优化路径转发数据包
- **加密选项**：通过 IPsec 或 WireGuard 加密 Overlay
- **模式选择**：选择受支持的路由模式。隧道模式下启用自动直接节点路由会被拒绝；它不是回退机制

#### Cilium VXLAN 配置示例：

以下 Helm values 适用于**新建且已准备好的 IPv4 测试安装**；请选择互不重叠的 Pod CIDR。这不是在线 IPAM 迁移，也不是用于替换 ConfigMap 的配置。

```yaml
# vxlan-values.yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
```

## 网络地址转换（NAT）

网络地址转换（NAT）是修改 IP 数据包源地址或目标地址的过程。NAT 主要用于使私有网络中的设备能够与公共互联网通信，或使两个网络地址空间重叠的网络能够互相通信。

### NAT 的主要类型

#### 1. 源 NAT（SNAT）

源 NAT 会修改数据包的源 IP 地址。它通常用于私有网络中的设备访问互联网。

- **工作原理**：重写源地址，有时也会重写端口；将私有地址转换为公共地址是一种常见用途
- **使用场景**：互联网访问、出站连接
- **跟踪**：在 NAT 表中存储连接状态

![示意图展示了内部网络中的客户端（10.0.0.2:1234）通过 NAT 路由器发送流量；路由器的 SNAT 在流量到达互联网服务器（203.0.113.5）之前，将源地址改写为公共 IP 198.51.100.1:5678。](../../.gitbook/assets/en-networking-cilium-networking-concepts-6.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-6.html)

文档专用地址范围用于说明一种从私有地址到公共地址的 SNAT 情况。SNAT 表示源地址转换；替换后的地址不一定总是公共地址。

#### 2. 目标 NAT（DNAT）

目标 NAT 会修改数据包的目标 IP 地址。它通常用于从公共互联网访问私有网络中的服务。

- **工作原理**：重写目标地址/端口；从公共网络转发到私有网络是一种示例
- **使用场景**：端口转发、负载均衡、入站连接
- **配置**：为特定端口或端口范围定义映射

![示意图展示了互联网客户端通过 NAT 路由器发送流量；路由器重写目标地址后，流量到达内部网络中具有私有 IP 地址的服务器。](../../.gitbook/assets/en-networking-cilium-networking-concepts-7.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-7.html)

此图使用文档专用地址展示了一种从公共网络到私有网络的 DNAT 情况。DNAT 是目标地址转换，也可用于其他地址域。

#### 3. 端口地址转换（PAT）

PAT 会同时修改 IP 地址和端口号，从而使多个内部主机能够共享一个公共 IP 地址。

- **工作原理**：将内部主机的 IP:端口组合转换为单个公共 IP 上的不同端口
- **使用场景**：节省 IP 地址、支持大量内部主机
- **局限性**：端口和状态资源有限；同时流的数量还取决于协议、目标元组和映射复用情况，并不存在普遍适用的 65,000 个连接上限

![示意图展示了两个内部主机通过 PAT 路由器共享一个公共 IP（198.51.100.1）；连接互联网服务器时，路由器将两个主机分别映射到不同的公共端口（5000 和 5001）。](../../.gitbook/assets/en-networking-cilium-networking-concepts-8.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-8.html)

此示例针对同一远程服务器使用不同的转换后端口。约 65,000 个端口的空间并非所有 NAT 连接的通用上限；协议、目标元组、映射行为和状态容量都会影响结果。

#### 4. 两次 NAT 和双向 NAT

**两次 NAT** 是指流量跨越地址域时同时更改源地址和目标地址，有助于协调重叠的地址空间。地址映射、DNS/应用假设和返回路径都必须一并设计。

RFC 2663 中的**双向 NAT**则指允许从任一地址域发起会话。根据定义，它并不表示在每个数据包中同时更改两个地址。

### NAT 的优缺点

#### 优点：

- **节省 IP 地址**：使用有限数量的公共 IP 地址支持大量内部主机
- **隐藏地址**：可能隐藏内部地址，但 NAT 不能替代防火墙策略或身份验证
- **协调地址域**：适当的转换可以连接重叠的地址域；这本身并不提供隔离
- **灵活的网络设计**：可以更换 ISP，而无需重新配置内部网络

#### 缺点：

- **连接跟踪开销**：维护状态表需要资源
- **特定协议问题**：某些协议可能与 NAT 不兼容
- **端到端连接能力降低**：难以直接进行点对点通信
- **故障排查复杂**：与 NAT 相关的问题可能难以调试

### Kubernetes 和 Cilium 中的 NAT

#### Kubernetes 中的 NAT

Kubernetes 在各种场景中使用 NAT：

1. **与集群外部通信**：根据地址可达性、伪装排除项和所选数据路径，可能会使用 SNAT
2. **Service 实现**：基于数据包的实现可以转换 Service 目标地址；基于套接字的负载均衡可能会在此类数据包出现之前选择后端
3. **NodePort Service**：实现会将节点 IP:端口转发到选定后端；返回路径行为取决于 SNAT/DSR 和流量策略
4. **LoadBalancer Service**：不同提供商/控制器的行为各不相同，并不一定是从公共地址到 Pod 的单次 DNAT 转换

#### Cilium 中的 NAT

Cilium 利用 eBPF 高效实现 NAT：

1. **基于 eBPF 的 NAT**：直接在内核中执行 NAT
2. **高性能连接跟踪**：使用经过优化的 BPF map 跟踪连接状态
3. **NAT 控制项**：受支持的伪装排除项、Service 转发和 Egress Gateway 功能各自具有不同的配置和前提条件
4. **伪装**：在已配置的路径/设备上进行有条件的源地址转换；排除的 CIDR 和受支持的模式会影响结果

Egress Gateway 是一项独立功能，会将匹配的出站流量导向选定节点，并将其 SNAT 为已配置的网关地址。它会更改原始源 IP；必须预先准备接口、地址和返回路径。新建的 Pod 可能会在策略收敛前发送流量，因此它无法立即保证源 IP 失效关闭。

#### Cilium NAT 配置示例：

此 Helm 片段假定已准备好 kube-proxy replacement/BPF 伪装环境，并且 API 端点可达。请先检查实际关联的设备和路由。将 CIDR 排除在 SNAT 之外不会自动创建返回路由；此处的 NAT 大小仅为示例，并非通用建议容量。

```yaml
# masquerade-values.yaml
enableIPv4Masquerade: true
kubeProxyReplacement: true
bpf:
  masquerade: true
  natMax: 262144
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    masqLinkLocal: false
```

## 路由协议

路由协议定义了相关规则和过程，用于确定数据包从源到目的地的最佳网络路径。这些协议在适应网络拓扑变化、高效转发流量和绕过网络故障方面发挥着重要作用。

### 路由协议分类

#### 1. 内部网关协议（IGP）

内部网关协议用于在单个自治系统（AS）内交换路由信息。

##### 距离矢量协议

- **RIP（路由信息协议）**
  - 使用跳数作为度量值
  - 有效度量值范围为 1 到 15 跳；度量值 16 表示不可达
  - 实现简单，适用于小型网络
  - 定期更新约每 30 秒一次；更新间隔带有随机化，并会针对变化发送触发更新

- **EIGRP（增强型内部网关路由协议）**
  - 可配置的复合度量值；默认系数使用吞吐量/带宽和延迟，而不是负载或可靠性
  - 仅发送部分更新
  - 收敛速度快
  - 该协议源自 Cisco，并记录在信息类 RFC 7868 中；该 RFC 并不属于 IETF 标准轨道

##### 链路状态协议

- **OSPF（开放式最短路径优先）**
  - 使用 Dijkstra 算法计算最短路径
  - 基于区域的分层结构
  - 收敛速度快
  - 支持大规模网络
  - 通过链路状态通告（LSA）交换拓扑信息

- **IS-IS（中间系统到中间系统）**
  - 与 OSPF 类似的链路状态协议
  - 广泛应用于大型服务提供商网络
  - 支持多个网络层
  - 高效的路由更新

#### 2. 外部网关协议（EGP）

外部网关协议用于在不同自治系统之间交换路由信息。

- **BGP（边界网关协议）**
  - 互联网的核心路由协议
  - 路径矢量协议
  - 基于策略的路由决策
  - 通过 TCP 建立可靠会话
  - 通过路径属性进行路径选择（AS 路径、本地优先级等）
  - 包括 iBGP（内部 BGP）和 eBGP（外部 BGP）两种形式

### 容器网络中的路由协议

在容器环境中，传统路由协议会与容器专用路由机制配合使用。

#### 1. 使用 BGP 的容器网络

BGP 在容器网络中日益普及，原因如下：

- **可达性通告**：向路由器通告 Pod 或 Service 前缀；本地转发实现仍然决定流量的实际路径
- **可扩展性**：支持大规模集群和多集群环境
- **与现有网络集成**：与数据中心网络基础设施集成
- **高可用性**：多路径和收敛取决于路由器策略、计时器和正常运行的数据路径；仅建立会话并不能保证快速故障切换

#### 2. 容器网络路由机制

- **基于主机的路由**：主机维护 Pod 路由，并可参与单独配置的路由通告机制
- **集中式路由**：由控制器集中管理路由决策
- **分布式路由**：节点之间直接交换路由信息
- **基于策略的路由**：根据流量特征做出路由决策

### Cilium 中的路由

Cilium 使用 eBPF 实现路由，并支持不同的数据路径模式。**主机路由是另一个独立维度**：BPF 主机路由可优化节点内的转发，并绕过主机网络栈/netfilter 的部分路径。它需要兼容的 kube-proxy replacement/BPF 伪装，并且存在集成方面的限制。这并不意味着在节点间路由时选择原生路由而非隧道模式。

#### 1. 原生路由（直接路由）

在原生路由模式下，Cilium 直接路由 Pod IP，不进行 Overlay 封装。

- **工作原理**：Pod 流量通过 Underlay 路由传输，不进行 Overlay 封装；启用原生模式不会自动启用 BGP
- **优点**：避免 Overlay 封装开销；实际性能仍需测量
- **要求**：相关 Pod 地址及其返回流量都必须有有效路由，而不仅仅是节点 IP 之间可达
- **使用场景**：对性能要求高的工作负载、单子网集群

原生路由需要有效的 Pod 路由，但选择 `routingMode: native` 并不会自动通过 BGP 通告这些路由。请配置 Underlay/返回路由，或配置适当的路由分发机制。前面的主机路由示意图展示了转发原理。

#### 2. BGP 路由

Cilium 支持通过 BGP 路由将 Pod IP 集成到物理网络基础设施中。

- **工作原理**：Cilium 通过 BGP 对等连接通告 Pod CIDR
- **优点**：与现有网络基础设施集成，具有高可用性
- **组件**：BGP 对等连接、路由过滤、团体属性
- **使用场景**：与数据中心网络集成、多集群环境

#### 3. Overlay 路由

Cilium 可以使用 VXLAN 或 Geneve 等 Overlay 协议，在节点之间路由 Pod 流量。

- **工作原理**：封装 Pod 数据包，以便在节点之间传输
- **优点**：最大限度降低对网络基础设施的要求，部署灵活
- **使用场景**：云环境、复杂网络拓扑

#### 4. 混合路由

不要假设 Cilium 会在原生路由可达时自动使用原生路由，否则就回退到 Overlay。当前的隧道模式不能与 `autoDirectNodeRoutes: true` 结合使用；agent 会拒绝此配置。请选择受支持的数据路径，并准备相应的 Underlay。

名为 `hybrid` 的有效负载均衡模式是另一项功能：TCP 使用 DSR，而 UDP 使用 SNAT。它不是原生路由/Overlay 路由之间的回退机制。

### Cilium 路由配置示例

#### 原生路由配置：

此原生路由片段假设目标 Pod CIDR 和节点位于同一 L2 网络，以便自动创建直接路由。其他拓扑需要合适的路由机制。不能将其与隧道模式组合使用，也不能将其用作自动回退。

```yaml
# native-values.yaml
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16
```

#### BGP 路由配置：

以下功能标志只是众多前提条件之一。请按照[高级主题](07-advanced-topics.md)中的说明配置当前的 `CiliumBGPClusterConfig`、`CiliumBGPPeerConfig` 和 `CiliumBGPAdvertisement` 资源，以及外部路由器。BGP 通告和数据路径路由模式是彼此独立的选择。

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```

#### Overlay 路由配置：

请使用上面的完整 VXLAN values 示例。在 agent 状态中核实运行模式和端口；不要使用小型 ConfigMap 覆盖安装设置。

## DNS 和服务发现

DNS（域名系统）和服务发现对现代网络应用至关重要，尤其是在动态容器环境中。这些机制可以抽象服务位置，并允许应用适应网络拓扑变化。

### DNS（域名系统）

DNS 是一种分布式系统，可将人类可读的域名转换为 IP 地址。

#### DNS 的工作原理

1. **分层命名空间**：域名按层级结构组织，各级之间以点号分隔（例如 www.example.com）
2. **分布式数据库**：由全球分布的 DNS 服务器组成的网络
3. **迭代查询和递归查询**：处理客户端请求的两种主要方式
4. **缓存**：临时存储查询结果，以提升性能

#### DNS 记录类型

- **A 记录**：将域名映射到 IPv4 地址
- **AAAA 记录**：将域名映射到 IPv6 地址
- **CNAME 记录**：域名的别名（规范名称）
- **MX 记录**：指定邮件服务器
- **SRV 记录**：指定提供特定服务的服务器
- **TXT 记录**：存储文本信息（主要用于验证和策略）
- **PTR 记录**：将 IP 地址反向映射到域名（反向 DNS）

#### DNS 解析过程

常见的未缓存查询会经过应用的存根解析器和递归解析器：

| 步骤 | 查询/响应 |
| --- | --- |
| 1 | 存根解析器向其配置的递归解析器查询 `www.example.com`。 |
| 2 | 递归解析器查询根服务器，并收到指向 `.com` 服务器的转介。 |
| 3 | 递归解析器查询 `.com` 服务器，并收到指向 `example.com` 权威服务器的转介。 |
| 4 | 递归解析器查询权威服务器并获取相关答案。 |
| 5 | 递归解析器根据 TTL 缓存结果，并将答案返回给存根解析器。 |

权威服务器通常不会在彼此之间转发这一查询序列。缓存、别名和配置的转发器可能会改变实际查询过程。

### 容器环境中的服务发现

服务发现是自动检测可用服务并在网络中定位这些服务的过程。在容器环境中，服务发现对于有效管理动态创建和删除的服务尤其重要。

#### 服务发现方式

1. **基于 DNS 的服务发现**
   - 服务注册时创建 DNS 记录
   - 客户端通过标准 DNS 查询发现服务
   - 简单且广泛支持
   - 示例：Kubernetes DNS、CoreDNS

2. **基于键值存储的服务发现**
   - 在集中式键值存储中保存服务信息
   - 客户端查询存储以发现服务
   - 支持丰富的元数据
   - 示例：etcd、Consul、ZooKeeper

3. **基于 API 的服务发现**
   - 通过专用 API 提供服务信息
   - 客户端调用 API 以发现服务
   - 支持复杂查询和过滤
   - 示例：Kubernetes API Server

4. **基于 Service Mesh 的服务发现**
   - 由 Service Mesh 基础设施处理服务发现
   - 支持客户端负载均衡和路由
   - 提供高级流量管理功能
   - 示例：Istio、Linkerd

### Kubernetes 中的 DNS 和服务发现

Kubernetes 提供了用于集群内服务发现的内置机制。

#### Kubernetes Services

Kubernetes Services 为一组 Pod 提供稳定端点：

- **ClusterIP**：Service 虚拟 IP，通常在集群内部使用；任何外部可路由性都需要明确的网络设计，并非其固有安全边界
- **NodePort**：在符合条件的节点地址上公开的节点端口，受流量策略、路由和防火墙规则约束
- **LoadBalancer**：请求提供商/控制器实现，结果可能是公共的，也可能是内部的
- **ExternalName**：外部服务的 DNS 别名

#### Kubernetes DNS

Kubernetes 运行集群 DNS 服务（通常为 CoreDNS）以支持服务发现：

- **Service DNS**：`<service-name>.<namespace>.svc.<cluster-domain>`；`cluster.local` 是常见的配置域名，并非普遍适用的固定值
- **Pod DNS**：旧版基于地址的 `pod.<cluster-domain>` 形式取决于具体实现/属于遗留形式。稳定的 Pod 名称通常使用 hostname/subdomain 以及相应的无头 Service
- **无头 Service**：DNS 可以返回端点地址，而不是 VIP；就绪状态和 `publishNotReadyAddresses` 会影响发布哪些记录

DNS 查询和 Service 转发是两个独立过程：

| 阶段 | 职责 |
| --- | --- |
| DNS 查询 | CoreDNS 根据 Kubernetes 对象状态，将普通 Service 名称解析为其 ClusterIP。它不会为该连接选择应用后端。 |
| 连接 | 客户端向返回的 Service 地址发送流量。 |
| 转发 | Service 实现（例如 Cilium 的数据路径）使用由 Service/EndpointSlice 状态派生的信息选择符合条件的后端。 |
| 无头 Service | DNS 返回端点地址，而不是 Service VIP；客户端行为决定使用哪个地址。 |

对象监视和数据路径更新是异步的；DNS 响应不是后端健康检查。

#### Kubernetes 服务发现机制

1. **环境变量**：Service links 可以反映创建 Pod 时已经存在的 Services；它们不是实时发现信息源，也可以禁用
2. **DNS**：通过集群 DNS 解析 Service 名称
3. **API Server**：通过直接查询 Kubernetes API 获取服务信息
4. **EndpointSlice 对象**：为 Service 实现提供后端地址、端口和就绪状态信息

### Cilium 中的 DNS 和服务发现

Cilium 与 Kubernetes 服务发现机制集成，并提供其他功能。

#### Cilium 的基于 DNS 的策略

Cilium 可以定义基于 DNS 名称的网络策略：

- **基于 DNS 名称的过滤**：控制对特定域名的访问
- **通配符支持**：`*.example.com` 匹配一级子域名；此版本中的 `**.example.com` 支持多级子域名，并且两者都不会在没有明确匹配项的情况下包含域名顶点
- **FQDN 策略**：基于完全限定域名（FQDN）的策略

此策略示例要求相应命名空间、带标签的工作负载和经过验证的解析器路径已经存在。DNS 观测和 TCP 443 目标许可是相互独立的。DNS `*` 允许所有查询名称；toFQDNs 并非主机名身份验证。

```yaml
# dns-policy.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: cilium-fqdn-demo
spec:
  endpointSelector:
    matchLabels:
      app: myapp
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.api.example.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

#### Cilium 的服务发现增强功能

Cilium 提供多项功能以增强 Kubernetes 服务发现：

1. **基于 eBPF 的 Service 实现**：
   - kube-proxy replacement
   - 在内核中直接进行 Service 负载均衡
   - 提升性能并提供更多功能

2. **Global Services**：
   - 跨多个集群发现服务
   - 跨集群负载均衡
   - 匹配 Service 名称/命名空间，并进行显式共享/ClusterMesh 配置

3. **Service 亲和性**：
   - 支持会话亲和性
   - ClientIP 亲和性与负载均衡算法相互独立；基于套接字的路径可以使用网络命名空间 cookie
   - 支持有状态连接

4. **健康检查集成**：
   - 后端状态遵循 Kubernetes 就绪状态/EndpointSlice 信息和已配置的代理检查
   - 更改会异步传播
   - 不要假设每个 Cilium Service 都会主动探测应用，或能实现即时故障切换

#### Cilium Service 配置示例：

会话亲和性在 Service 上配置；Global Services 使用注解，并要求 ClusterMesh 正常运行。对等 Service 必须具有相同的名称和命名空间。此示例不会创建应用、ClusterMesh 或外部负载均衡器。

```yaml
# global-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: cilium-service-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
  - name: http
    port: 80
    targetPort: 8080
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

## 负载均衡概念

负载均衡是一种将网络流量分配到多个服务器或后端服务的技术，可优化资源利用率，并在配合适当的容量和后端健康状态处理时，支持吞吐量、延迟和可用性目标。在容器环境中，对动态变化的后端实例有效分配流量尤为重要。

### 负载均衡类型

#### 1. L4（传输层）负载均衡

L4 负载均衡根据 IP 地址和端口号等传输层信息分配流量。

- **工作原理**：根据 TCP/UDP 报头信息做出路由决策
- **优点**：处理速度快、开销低，并可处理加密流量
- **缺点**：无法根据应用层信息进行高级路由
- **使用场景**：基于 TCP/UDP 的服务、对性能要求高的场景

![示意图展示了客户端请求如何由传输层负载均衡器根据 TCP/UDP 报头信息，路由到两个后端服务器中的一个。](../../.gitbook/assets/en-networking-cilium-networking-concepts-12.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-12.html)

图中的分支表示可能选择的后端，并不表示将一个连接广播到两台服务器。L4 转发可以承载 TLS，而不检查加密的 HTTP 负载。

#### 2. L7（应用层）负载均衡

L7 负载均衡根据 HTTP 报头、URL 和 Cookie 等应用层信息分配流量。

- **工作原理**：通过检查 HTTP/HTTPS 请求内容做出路由决策
- **优点**：基于内容的路由、高级流量管理、安全功能
- **缺点**：代理处理开销；要检查 HTTPS 的 HTTP 内容，需要适当终止 TLS
- **使用场景**：Web 应用、微服务、API 网关

![示意图展示了客户端 HTTP 请求如何由应用层负载均衡器根据 URL 路径和报头检查结果，路由到两个后端服务中的一个。](../../.gitbook/assets/en-networking-cilium-networking-concepts-13.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-13.html)

选择的路由取决于请求属性。通过 HTTPS 进行 HTTP 内容路由需要合适的 TLS 终止/检查路径。

### 负载均衡算法

负载均衡算法决定如何将流量分配到后端服务器。

#### 1. 轮询

- **工作原理**：按顺序将请求依次分配给每台后端服务器
- **优点**：顺序简单；请求数量相同并不意味着后端工作量相同
- **缺点**：不考虑服务器容量差异或当前负载
- **变体**：加权轮询（根据服务器容量分配权重）

#### 2. 最少连接数

- **工作原理**：将新请求转发到活动连接数最少的服务器
- **优点**：考虑服务器负载，对长连接有效
- **缺点**：连接数量并不总能准确反映负载
- **变体**：加权最少连接数（根据服务器容量分配权重）

#### 3. IP 哈希

- **工作原理**：对客户端 IP 地址进行哈希，以一致地选择后端服务器
- **优点**：在输入和后端成员保持稳定时，可以提供稳定的选择；它不是永久性会话存储
- **缺点**：分配可能不均，特定服务器可能过载
- **变体**：源-目标 IP 哈希（同时考虑源 IP 和目标 IP）

#### 4. 最短响应时间

- **工作原理**：将请求转发到响应时间最短的服务器
- **优点**：考虑性能和可用性，适用于对延迟敏感的应用
- **缺点**：测量响应时间会产生开销，也会受到网络波动的影响
- **变体**：加权响应时间（同时考虑服务器容量和响应时间）

#### 5. 随机选择

- **工作原理**：随机选择后端服务器
- **优点**：实现简单，无需跟踪特殊状态
- **缺点**：分配可能不均
- **变体**：加权随机选择（根据服务器容量调整选择概率）

### 负载均衡器部署模型

#### 1. 硬件负载均衡器

- **特点**：专用物理设备
- **优点**：性能高、可靠性高，拥有专用硬件加速
- **缺点**：成本高、可扩展性有限、灵活性不足
- **示例**：应用交付控制器设备；一些产品系列也提供虚拟/软件版本

#### 2. 软件负载均衡器

- **特点**：运行在通用服务器上的软件
- **优点**：灵活、成本效益高、可编程
- **缺点**：容量取决于实现、硬件和工作负载；软件并非天生就比所有设备慢
- **示例**：NGINX、HAProxy、Envoy

#### 3. 云负载均衡器

- **特点**：由云提供商管理的服务
- **优点**：减少管理开销、自动扩展、高可用性
- **缺点**：供应商锁定、定制能力有限
- **示例**：AWS ELB/ALB/NLB、Google Cloud Load Balancing、Azure Load Balancer

#### 4. 容器原生负载均衡器

- **特点**：针对容器环境优化的负载均衡
- **优点**：与容器编排集成、动态服务发现
- **缺点**：专用于容器环境
- **示例**：Kubernetes Services、Istio、Cilium

### Kubernetes 中的负载均衡

Kubernetes 提供多个层级的负载均衡：

#### 1. Service 负载均衡

- **ClusterIP**：集群内部负载均衡
- **NodePort**：通过节点端口提供外部访问
- **LoadBalancer**：配置外部负载均衡器
- **ExternalName**：外部服务的 DNS 别名

#### 2. Ingress 控制器

- L7 负载均衡和路由
- 基于 URL 的路由和 TLS 终止；身份验证能力取决于控制器和配置
- 实现包括 Traefik、HAProxy 和基于 Istio 的控制器。社区版 `ingress-nginx` 于 2026 年 3 月退役；剩余的制品不应被视为受维护的安装建议

#### 3. Service Mesh

- 微服务之间的高级流量管理
- 细粒度路由、流量拆分、故障注入
- 示例：Istio、Linkerd 和 Consul service mesh；它们的流量管理和安全功能各不相同

### Cilium 中的负载均衡

Cilium 使用 eBPF 实现高效负载均衡：

#### 1. 基于 eBPF 的负载均衡

- **kube-proxy Replacement**：在内核中直接进行 Service 负载均衡
- **性能**：受支持的 BPF 路径可以绕过传统网络栈的部分路径；应针对实际工作负载量化结果
- **可扩展性**：支持大规模 Services 和端点
- **连接跟踪优化**：高效管理状态

![Cilium 基于 eBPF 的负载均衡示意图：Pod A 发送到 Service IP 的数据包会经过内核中由 eBPF 执行的四步处理流程（数据包拦截、Service map 查询、后端选择、数据包转发），随后直接交付给 Pod B，不经过 kube-proxy。](../../.gitbook/assets/en-networking-cilium-networking-concepts-14.png)

[🔍 查看交互式示意图](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-networking-concepts-14.html)

此图展示的是基于数据包路径的 Service 地址转换。基于套接字的负载均衡可以在 Service-IP 数据包出现之前选择后端。必须针对实际路径测量延迟改进情况。

#### 2. 负载均衡算法

BPF Service 算法包括**随机**（默认）和 **Maglev**。Maglev 对流信息进行哈希；它并非单纯的源 IP 亲和性。普通的基于套接字的东西向选择与应用 Maglev 的外部数据包路径不同。

`ClientIP` 会话亲和性在 Service 上单独配置。其超时不是“Maglev 超时”；Maglev 没有定期重新均衡会话的计时器。成员关系、种子或表发生变化时，选择结果可能会重新映射；即使哈希保持一致，已移除的后端也无法继续服务连接。

#### 3. L7 负载均衡

Cilium 还支持 L7（应用层）负载均衡：

- **基于 HTTP 报头的路由**：根据特定报头值进行路由
- **基于 URL 路径的路由**：根据 URL 模式分配流量
- **gRPC 路由**：根据 gRPC 方法和元数据进行路由
- **Kafka**：当前 Cilium 不提供早期的 Kafka topic L7 策略/路由功能；请使用适用于代理的控制措施

#### 4. Global Service 负载均衡

Cilium 支持跨多个集群进行负载均衡：

- **跨集群负载均衡**：在多个集群的后端之间分配流量
- **本地性优先**：配置的本地/远程亲和性不会自动测量网络延迟
- **故障处理**：取决于端点状态和远程缓存行为；默认的零缓存 TTL 可能会保留过期的远程状态，因此必须测试应用故障切换

#### Cilium 负载均衡配置示例：

以下是适用于已准备好安装环境的 Helm values。所示哈希种子是一个有效的**12 字节 Base64 演示值**。用于部署时，请为参与的节点生成并持久化一个共同的随机种子，并将种子/表更改视为可能影响连接的操作。请参阅[预先准备的负载均衡配置](05-l2-l7-networking.md)。

```yaml
# load-balancing-values.yaml
kubeProxyReplacement: true
loadBalancer:
  algorithm: maglev
maglev:
  tableSize: 16381
  hashSeed: AAECAwQFBgcICQoL
```

## 网络安全基础

网络安全是保护网络基础设施、应用和数据免遭未经授权的访问、滥用、故障或修改的实践。在容器环境中，由于其动态分布式特性，网络安全更加重要。

### 网络安全核心概念

#### 1. 纵深防御

纵深防御通过组合多种控制措施，降低单点故障的影响。共享依赖项或共同的配置错误仍可能影响多个层面。

- **多层安全防护**：在网络、主机、应用和数据层提供保护
- **冗余控制措施**：组合使用多种安全机制
- **故障隔离**：设计并测试边界；故障彼此独立并非必然
- **威胁检测和响应**：在每个层面进行监控和响应

#### 2. 最小权限原则

最小权限原则是一种安全实践，只向用户、进程或应用授予完成任务所需的最低权限。

- **细粒度访问控制**：将访问限制在必需的资源范围内
- **权限分离**：分离不同功能所需的权限
- **默认拒绝**：拒绝所有未明确允许的访问
- **定期审查**：定期审计并调整权限

#### 3. 网络分段

网络分段是一种将网络划分为更小网段或区域的技术，用于增强安全性并限制威胁的横向移动。

- **安全区域**：将具有相似安全要求的系统归为一组
- **微分段**：在工作负载级别进行细粒度控制
- **边界保护**：控制并监控区域之间的流量
- **威胁隔离**：限制安全事件的影响范围

#### 4. 加密

加密是转换数据，使其无法被未授权方读取的过程。

- **传输中加密**：保护通过网络传输的数据（例如受支持的 TLS）
- **静态加密**：保护存储在磁盘或数据库中的数据
- **端到端加密**：保护整个通信路径上的数据
- **密钥管理**：安全地生成、存储和轮换加密密钥

### 容器网络安全威胁

容器环境具有独特的安全挑战：

#### 1. 基于网络的攻击

- **DDoS（分布式拒绝服务）攻击**：通过大量流量破坏服务可用性
- **端口扫描**：探测开放端口和漏洞
- **ARP 欺骗**：操纵地址解析协议以拦截网络流量
- **DNS 污染**：将 DNS 查询重定向到恶意目的地

#### 2. 应用层攻击

- **SQL 注入**：插入恶意 SQL 代码
- **XSS（跨站脚本攻击）**：插入客户端脚本
- **CSRF（跨站请求伪造）**：通过已认证用户执行恶意操作
- **命令注入**：通过恶意输入执行系统命令

#### 3. 容器特有的威胁

- **镜像漏洞**：容器镜像中包含易受攻击的组件
- **权限提升**：在某个边界内或跨越边界获取权限；它并不总是与容器逃逸同时发生
- **横向移动**：未经授权地从一个容器访问另一个容器
- **卷挂载利用**：访问敏感的主机路径

### 网络安全控制措施

#### 1. 防火墙

防火墙是一种根据已定义的安全规则过滤网络流量的网络安全系统。

- **数据包过滤**：根据 IP 地址、端口和协议进行过滤
- **有状态检测**：根据连接状态跟踪上下文并做出决策
- **应用层过滤**：识别和检查应用协议
- **下一代防火墙（NGFW）**：提供高级威胁检测和防护功能

#### 2. 入侵检测和防御系统（IDS/IPS）

IDS/IPS 是监控网络流量并检测或阻止恶意活动的系统。

- **基于签名的检测**：匹配已知攻击模式
- **异常检测**：识别偏离正常行为的活动
- **行为监控**：分析可疑活动模式
- **自动响应**：实时响应检测到的威胁

#### 3. 网络策略

网络策略是一组定义网络内允许通信的规则。

- **入站控制**：限制入站流量
- **出站控制**：限制出站流量
- **细粒度策略**：在工作负载级别控制通信
- **基于标签的策略**：在动态环境中灵活应用策略

#### 4. 加密协议

加密协议为网络通信提供安全保护。

- **TLS**：保护 Web 流量和 API 通信；SSL 协议已经过时
- **IPsec**：网络层加密
- **WireGuard**：现代且高效的 VPN 协议
- **mTLS（双向 TLS）**：对客户端和服务器双方进行身份验证

### Kubernetes 中的网络安全

Kubernetes 为容器化应用的网络安全提供多种机制：

#### 1. Network Policies

Kubernetes NetworkPolicy 为选定的 Pod 指定 L3/L4 允许规则。它需要一个能够强制执行策略的网络实现；适用策略中的允许规则会合并，而现有路径/host-network 路径有其各自的语义。

- **Pod 选择器**：根据标签选择适用策略的 Pod
- **Ingress 规则**：控制入站流量
- **Egress 规则**：控制出站流量
- **基于 CIDR 的规则**：根据 IP 范围进行过滤

此 L4 示例使用独立命名空间，并假设存在匹配的前端/API/数据库工作负载以及所述 CoreDNS 标签。示例包含 DNS 出站流量。请将其与后面的 L7 示例分开：范围较广的 L4 允许规则可能会绕过重叠的 L7 限制。

```yaml
# api-l4-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: cilium-policy-l4-demo
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

#### 2. Service Mesh 安全

Service Mesh 是用于管理和保护微服务之间通信的基础设施层。

- **mTLS**：服务之间的加密通信
- **身份验证和授权**：验证服务身份并控制访问
- **流量策略**：细粒度路由和访问控制
- **可观测性**：查看服务间通信情况

#### 3. 安全上下文

安全上下文定义 Pod 和容器的权限与访问控制设置。

- **权限限制**：以非 root 用户身份运行
- **能力限制**：只允许必需的 Linux capabilities
- **只读根文件系统**：限制对容器根文件系统的写入；挂载卷仍可能可写
- **seccomp 和 AppArmor**：限制系统调用和应用行为

### Cilium 的网络安全功能

Cilium 利用 eBPF 提供强大的网络安全功能：

#### 1. 基于身份的安全

除了在已配置时显式控制 CIDR/IP 外，Cilium 还支持根据与安全相关的标签推导工作负载身份策略。

- **基于标签的策略**：在动态环境中保持一致的安全控制
- **基于 Service Account 的策略**：根据 Kubernetes service account 控制访问
- **基于 DNS 的策略**：根据 FQDN 控制出站流量
- **感知 API 的安全**：根据 HTTP 方法和路径进行过滤

`toCIDR` 用于选择目标范围，但默认情况下，CIDR 选择器不会匹配由系统管理的集群内 Pod/节点；此版本提供了一个显式的 Beta 选项以支持这些情况。`world` 实体涵盖外部端点，而不是所有已知的集群/ClusterMesh 身份。请使用适当的身份/实体范围，不要将 `world` 当作允许所有集群的同义词。

#### 2. 透明加密

Cilium 可以在不更改应用的情况下加密受支持的路径。节点隧道不会覆盖同节点流量或所有外部目标。单独的 SPIRE 双向身份验证握手本身并不会加密应用流量；Beta ztunnel 工作负载 mTLS 也有自己的前提条件。

- **IPsec**：对节点间流量进行网络层加密
- **WireGuard**：现代且高效的加密协议
- **透明集成**：无需更改应用即可应用加密
- **密钥轮换**：遵循所选模式的密钥生命周期；Cilium IPsec 要求预先配置密钥材料，并遵循文档说明的 Secret 轮换流程

#### 3. 威胁检测和可见性

Cilium/Hubble 提供的网络观测数据可用于调查。完整的 IDS/WAF、运行时强制执行或警报/响应工作流需要适当的单独配置或集成。

- **Hubble**：监控和分析网络流
- **流日志**：记录 Pod 到 Pod 通信的详细日志
- **异常检测**：外部检测规则可以分析已观测的模式；Hubble 不会自动识别所有攻击
- **安全事件警报**：配置警报/SIEM 集成，并考虑事件丢失、噪声和观测不完整等情况

#### 4. L3-L7 策略强制执行

Cilium 提供从网络层到应用层的全面策略强制执行功能。

- **L3/L4 策略**：基于 IP 和端口的过滤
- **L7 HTTP 过滤**：基于 URL、方法和报头进行控制
- **L7 gRPC 过滤**：基于 gRPC 方法和元数据进行控制
- **DNS 策略**：针对 FQDN 规则进行查询过滤和 DNS 观测；当前不支持 Kafka topic L7 策略

#### Cilium 网络安全配置示例：

此替代的 L7 策略使用与 L4 示例不同的命名空间。它要求可见的明文 HTTP 流量或适当的 TLS 检查路径、真实且带标签的依赖项，以及可达的解析器。外部名称 `.example` 是占位符；此处不会配置可运行的外部服务。

```yaml
# api-l7-policy.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: secure-api
  namespace: cilium-policy-l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-policy-l7-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-policy-l7-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
  - toFQDNs:
    - matchName: api.external-service.example
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### 网络安全最佳实践

#### 1. 默认拒绝策略

- 实施默认拒绝策略，只允许明确许可的流量
- 只开放必需的通信路径
- 定期审查策略并移除不必要的规则
- 保留策略变更的审计记录

#### 2. 纵深防御方法

- 实施多层安全防护
- 结合网络、主机和应用层保护
- 组合使用多种安全机制，设置冗余控制措施
- 消除单点故障

#### 3. 最小权限网络

- 只允许最低限度的必要网络访问
- 为每项服务定义细粒度策略
- 阻止不必要的端口和协议
- 定期审查和调整访问权限

#### 4. 持续监控和审计

- 监控网络流量和策略违规情况
- 检测异常和潜在威胁
- 对安全事件发出警报并进行响应
- 定期进行安全审计和漏洞评估

## 主要参考资料

- [Cilium 路由](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/concepts/routing.rst)
- [Cilium chart values](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Kube-proxy replacement](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)
- [伪装](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/concepts/masquerading.rst)
- [BGP 控制平面](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Global Services](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/clustermesh/global-services.rst)
- [策略语言](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/layer3.rst)
- [DNS 策略](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/dns.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/services-networking/)
- [Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Services 和 Pods 的 DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [CNI 规范](https://raw.githubusercontent.com/containernetworking/cni/main/SPEC.md)
- [Docker Bridge 网络](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker Host 网络](https://docs.docker.com/engine/network/drivers/host/)
- [Ingress NGINX 退役](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [互联网架构 / RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.txt)
- [DNS / RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.txt)
- [NAT 术语 / RFC 2663](https://www.rfc-editor.org/rfc/rfc2663.txt)
- [NAT 映射行为 / RFC 4787](https://www.rfc-editor.org/rfc/rfc4787.txt)
- [RIP v2 / RFC 2453](https://www.rfc-editor.org/rfc/rfc2453.txt)
- [EIGRP / RFC 7868](https://www.rfc-editor.org/rfc/rfc7868.txt)

## 测验

要测试你对本章内容的掌握情况，请尝试[主题测验](../../quizzes/networking/cilium/networking-concepts-quiz.md)。
