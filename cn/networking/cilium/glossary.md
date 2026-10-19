# 术语表和缩写

> **审查基线**：Cilium 1.20.3。
> **最近审查日期**：2026 年 10 月 16 日。

Cilium、eBPF、Kubernetes 和网络相关术语的字母顺序参考表。重复条目已合并。

## A

**API (Application Programming Interface)** - 通用

- 一组接口定义，用于实现应用程序之间的通信

**ARP (Address Resolution Protocol)** - 网络

- 将 IPv4 地址解析为本地链路上的链路层地址，通常是以太网 MAC 地址。
- 对于远程目标，主机会解析其下一跳。IPv6 使用邻居发现，而不是 ARP。

**AWS ENI (Elastic Network Interface)** - 网络

- Amazon Web Services 提供的虚拟网络接口
- 用于 Cilium 的 AWS ENI IPAM 模式

## B

**BGP (Border Gateway Protocol)** - 网络

- 一种域间路由协议，用于在对等节点之间通告可达性。
- Cilium BGP Control Plane 会通告选定的前缀；它不是原生路由模式，也不会对本地数据路径的路由进行编程。

**BPF (Berkeley Packet Filter)** - eBPF

- 一种数据包过滤技术，是 eBPF 的前身
- 最初为网络数据包捕获而开发

**BPF Maps** - eBPF

- 由内核管理的数据结构，供 BPF 程序和用户空间共享状态或事件。
- 许多类型使用键和值；环形缓冲区、队列和栈采用不同的操作。BPF 环形缓冲区不支持 map 查找、更新或删除操作。

## C

**CGroup (Control Group)** - Kubernetes

- Linux 控制组用于组织进程，以及统计或控制 CPU 和内存等资源。
- 容器运行时会使用 cgroups；它们本身并不提供进程/网络命名空间隔离。

**CIDR (Classless Inter-Domain Routing)** - 网络

- 一种 IP 地址分配和路由聚合方法
- 示例：192.168.1.0/24 表示从 192.168.1.0 到 192.168.1.255 的 IP 地址范围

**Cilium** - Cilium

- 基于 eBPF 的开源网络、安全和可观测性解决方案
- 用作 Kubernetes CNI 实现

**Cilium Agent** - Cilium

- 在节点本地运行的 Cilium 组件，负责管理端点、BPF 程序以及策略/数据路径状态。它运行在由 Cilium 管理且符合条件的节点上。

**Cilium Operator** - Cilium

- 集群级控制器，负责 CRD 注册、依赖模式的 IPAM/LB IPAM、垃圾回收以及已启用的 Ingress/Gateway 控制器等任务。
- 副本数可配置。可选的身份管理和 ClusterMesh 同步取决于已启用的功能；它不是负责节点数据包转发的组件。

**ClusterMesh** - Cilium

- Cilium 的多集群网络元数据/连通性功能，用于服务发现、负载均衡和远程身份策略。
- 需要兼容的地址配置、信任关系和可达路径；它既不提供共享存储，也不会自动复制所有策略资源。

**CNI (Container Network Interface)** - Kubernetes

- 容器网络接口：用于配置容器网络连通性的规范和插件。
- 在当前版本的 Kubernetes 中，CRI 容器运行时会加载/调用 CNI 插件。kubelet 之前用于直接管理 CNI 的标志已在 Kubernetes 1.24 中移除。

**CoreDNS** - Kubernetes

- Kubernetes 集群中常用的 DNS 服务器
- 在服务发现中发挥重要作用

**CRD (Custom Resource Definition)** - Kubernetes

- 通过扩展 Kubernetes API 来定义自定义资源的方法
- Cilium 使用 CRD 定义网络策略等

## D

**DaemonSet**

- 一种 Kubernetes 控制器，可根据调度约束在符合条件的节点上运行守护 Pod；它不一定会覆盖每个节点。

**DNAT (Destination Network Address Translation)** - 网络

- 一种会修改数据包目标 IP 地址的 NAT 类型
- 用于负载均衡和端口转发

**DNS (Domain Name System)** - 网络

- 一种分布式命名系统，用于发布 A/AAAA 地址、CNAME 别名和 SRV 服务信息等记录。
- Cilium DNS 策略与基于学习到的 IP 的 FQDN 策略相关，但二者是不同的控制机制。

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- 扩展伯克利数据包过滤器：Cilium 使用的可编程内核挂钩及相关基础设施。
- 验证器会在接受程序之前检查其属性。但这并不能保证内核或验证器的实现不存在漏洞。

**Endpoint** - Cilium

- 由 Cilium 管理的网络端点，通常是一个 Pod，具有本地数据路径/策略状态。
- 其端点 ID 仅在本地 Agent 范围内有效，与多个端点共享的安全身份不同。

**Envoy** - Cilium

- Cilium 使用的开源代理，用于已配置的 HTTP/gRPC 策略、L7 可见性和基于代理的服务路由。
- DNS 策略使用 Cilium 的 DNS 代理。Kafka L7 策略已不再受支持；并非每条 L7 规则都会自动部署一个 Envoy 实例。

## F

**FQDN (Fully Qualified Domain Name)**

- 完全限定域名：一个绝对名称，用于标识其在 DNS 树中的完整位置，通常以末尾的根点表示，例如 `www.example.com.`。
- Cilium `toFQDNs` 允许访问学习到的目标 IP。它本身不会对 HTTPS 服务器进行身份验证，也不会限制共享 IP 上的所有 HTTP Host 值。

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- 用于网络虚拟化的封装协议

**gRPC (gRPC Remote Procedure Call)**

- 由 Google 开发的高性能 RPC（远程过程调用）框架

## H

**Hubble** - Cilium

- Cilium 的网络可观测性层：流事件、受支持的协议元数据、指标和查询接口。
- 历史数据有容量限制，观测结果也可能丢失或被过滤。告警、持久化存储和自动响应需要配置相应集成。

## I

**Identity** - Cilium

- 根据与安全相关的标签派生出的数字安全标识符。在适用的分配范围内，多个端点可以共享同一标识符。
- 在 CRD 分配模式下，CiliumIdentity 的 `security-labels` 字段是事实来源。保留身份和节点本地身份并非都由这些集群范围的对象表示。

**IPAM (IP Address Management)** - 网络

- IP 地址管理：地址分配、跟踪和回收。
- Cilium 的不同模式在地址分配责任方和数据源方面各不相同，包括集群池、多池、Kubernetes 主机范围和特定于云平台的模式。平台名称不一定对应单独的 `ipam.mode` 值。

**IPsec** - 网络

- 互联网协议安全：一套用于 IP 层身份验证/完整性保护的机制，并可在适当配置下提供机密性。
- Cilium 使用 IPsec 加密受支持的节点间流量；密钥管理和特定路径的限制仍然适用。

**Istio**

- 实现服务网格的开源平台

## K

**Kafka**

- 一种分布式事件流平台。它仍可用作工作负载，但当前版本的 Cilium 不再提供旧版 Kafka 主题 L7 策略 API。

**kube-proxy** - Kubernetes

- 一种 Kubernetes 组件，通过受支持的节点网络机制实现 Service 虚拟 IP/端口转发。
- Cilium 可以使用 eBPF 替代此功能；XDP 加速是可选的，且平台必须支持所选配置。

**Kubernetes**

- 用于自动化部署、扩展和管理容器化应用的开源平台

## L

**L2 (Layer 2)**

- OSI 模型的数据链路层

**L3 (Layer 3)**

- OSI 模型的网络层

**L4 (Layer 4)**

- OSI 模型的传输层

**L7 (Layer 7)**

- OSI 模型的应用层

**LoadBalancer**

- 一种流量分配功能。Kubernetes `type: LoadBalancer` 会向控制器/提供商请求实现；若没有相应实现，则无法保证存在外部负载均衡器。

## M

**MAC (Media Access Control) Address**

- 媒体访问控制地址：与接口关联的链路层地址。
- 地址可能由本地管理或发生变化；不得假定其唯一性和真实性。

**mTLS (mutual TLS)**

- 双向 TLS：一种 TLS 机制，双方都会进行身份验证，通常通过验证彼此的证书实现。
- 对等方身份验证与应用授权不同。Cilium 的带外双向身份验证和 Beta 版 ztunnel 工作负载 mTLS 是不同的功能，对流量的保护属性也各不相同。

**MTU (Maximum Transmission Unit)**

- 最大传输单元：链路/接口在不进行分片的情况下可承载的最大网络层数据包，包含其 IP 头部，但不包含链路层头部。
- 路径 MTU 受路径限制；隧道/加密开销会影响可用的内部数据包大小。它不是 TCP MSS，也不是应用负载大小。

## N

**NAT (Network Address Translation)**

- 修改 IP 数据包中 IP 地址信息的过程

**NodePort**

- 一种 Kubernetes Service 暴露方式，使用分配给符合条件的节点地址的节点端口。
- 地址选择、流量策略、防火墙和平台路由共同决定可达性；声明 NodePort 并不保证可从公网访问。

## O

**OSI (Open Systems Interconnection) Model**

- 将网络通信划分为 7 个抽象层的概念模型

**Overlay Network**

- 构建在现有网络之上的虚拟网络

## P

**Pod**

- Kubernetes 中最小的可部署计算单元

**Proxy**

- 在对等方之间中介通信的组件；它不一定是独立的物理服务器。

## R

**RBAC (Role-Based Access Control)**

- 根据角色控制对系统资源访问权限的方法

## S

**Service**

- Kubernetes 的一种抽象，用于访问一组逻辑后端，通常是通过标签选择的 Pod。
- 普通 ClusterIP Service 具有虚拟 IP；无头 Service 则没有。ExternalName 使用 DNS 别名，未配置选择器的 Service 可以使用手动管理的 EndpointSlice。

**SNAT (Source Network Address Translation)**

- 一种会修改数据包源 IP 地址的 NAT 类型

**Socket**

- 用于网络通信或本地进程间通信的操作系统通信端点。

## T

**TCP (Transmission Control Protocol)**

- 面向连接的传输协议，提供可靠的字节流

**TLS (Transport Layer Security)**

- 用于保护网络通信的加密协议

## U

**UDP (User Datagram Protocol)**

- 无连接的传输协议

## V

**VETH (Virtual Ethernet)**

- 虚拟以太网设备，通常成对创建

**VNI (VXLAN Network Identifier)**

- VXLAN 网络标识符：VXLAN 头部中的一个 24 位字段。
- Cilium 可以在覆盖网络元数据中携带身份信息；该字段的宽度并不意味着可独立配置数百万个租户网络。

**VTEP (VXLAN Tunnel Endpoint)**

- 负责封装和解封装 VXLAN 数据包的端点

**VXLAN (Virtual Extensible LAN)** - 网络

- 一种网络虚拟化技术，可在三层网络上覆盖二层网络
- Cilium 的覆盖网络模式之一

## W

**WireGuard** - 网络

- Cilium 用于受支持的跨节点流量的 VPN 隧道协议。
- 同一节点上的 Pod 流量不会通过节点隧道加密；外部流量和可选的节点加密有各自的限制。与 IPsec 的性能对比需要采用可比的测量方式。

## X

**XDP (eXpress Data Path)** - eBPF

- eXpress Data Path：一种数据包处理挂钩；原生 XDP 在受支持的网络驱动程序接收路径中运行。
- PASS 会继续进入网络协议栈；其他操作可丢弃、发送或重定向数据包。Cilium 支持的 XDP 加速是可选的，不能保证普遍提升吞吐量或防御 DDoS。

## 主要参考资料

- [Cilium identities](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/security-identities.rst)
- [CiliumIdentity schema](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/internals/cilium_operator.rst)
- [Identity management modes](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC addressing / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## 测验

[主题测验](../../quizzes/networking/cilium/glossary-quiz.md)
