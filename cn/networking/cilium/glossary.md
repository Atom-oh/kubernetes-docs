# 词汇表和缩略语

> **审阅基线**: Cilium 1.20.2.
> **最后审阅**: October 15, 2026.

按字母顺序列出的 Cilium、eBPF、Kubernetes 和网络参考。重复条目已合并。

## A

**API (Application Programming Interface)** - 通用

- 一组用于实现应用程序之间通信的接口定义

**ARP (Address Resolution Protocol)** - 网络

- 将 IPv4 地址解析为本地链路上的链路层地址，通常为 Ethernet MAC 地址。
- 对于远程目标，主机会解析其下一跳。IPv6 使用 Neighbor Discovery 而非 ARP。

**AWS ENI (Elastic Network Interface)** - 网络

- 由 Amazon Web Services 提供的虚拟网络接口
- 用于 Cilium 的 AWS ENI IPAM 模式

## B

**BGP (Border Gateway Protocol)** - 网络

- 用于在对等方之间通告可达性的域间路由协议。
- Cilium BGP Control Plane 通告选定的前缀；它不是原生路由模式，也不会编程本地数据路径路由。

**BPF (Berkeley Packet Filter)** - eBPF

- 用于数据包过滤的技术，是 eBPF 的前身
- 最初为网络数据包捕获而开发

**BPF Maps** - eBPF

- 由内核管理的数据结构，供 BPF 程序和用户空间共享状态或事件。
- 许多类型使用键和值；环形缓冲区、队列和栈具有不同的操作。BPF 环形缓冲区不支持 map 查找/更新/删除。

## C

**CGroup (Control Group)** - Kubernetes

- Linux 控制组可组织进程，并统计或控制 CPU 和内存等资源。
- 容器运行时使用 cgroups；它们本身并不提供进程/网络命名空间隔离。

**CIDR (Classless Inter-Domain Routing)** - 网络

- 用于 IP 地址分配和路由聚合的方法
- 示例：192.168.1.0/24 表示从 192.168.1.0 到 192.168.1.255 的 IP 地址范围

**Cilium** - Cilium

- 基于 eBPF 的开源网络、安全和可观测性解决方案
- 用作 Kubernetes CNI 实现

**Cilium Agent** - Cilium

- 节点本地的 Cilium 组件，负责管理端点、BPF 程序以及策略/数据路径状态。它运行在由 Cilium 管理的符合条件的节点上。

**Cilium Operator** - Cilium

- 集群级控制器，负责 CRD 注册、依模式而定的 IPAM/LB IPAM、垃圾回收以及已启用的 Ingress/Gateway 控制器等任务。
- 副本数量可配置。可选的身份管理和 ClusterMesh 同步取决于已启用的功能；它不是节点数据包转发组件。

**ClusterMesh** - Cilium

- Cilium 的多集群网络元数据/连通性功能，用于服务发现、负载均衡和远程身份策略。
- 需要兼容的地址规划、信任关系和可达路径；它既不提供共享存储，也不会自动复制每个策略资源。

**CNI (Container Network Interface)** - Kubernetes

- Container Network Interface：用于配置容器网络连通性的规范和插件。
- 在当前 Kubernetes 中，CRI 容器运行时加载/调用 CNI 插件。kubelet 以前直接管理 CNI 的标志已在 Kubernetes 1.24 中移除。

**CoreDNS** - Kubernetes

- Kubernetes 集群中常用的 DNS 服务器
- 在服务发现中发挥重要作用

**CRD (Custom Resource Definition)** - Kubernetes

- 通过扩展 Kubernetes API 定义自定义资源的方法
- Cilium 使用 CRD 定义网络策略等资源

## D

**DaemonSet**

- Kubernetes 控制器，根据其调度约束在符合条件的节点上运行守护 Pod；不一定覆盖每个节点。

**DNAT (Destination Network Address Translation)** - 网络

- 修改数据包目标 IP 地址的 NAT 类型
- 用于负载均衡和端口转发

**DNS (Domain Name System)** - 网络

- 一种分布式命名系统，发布 A/AAAA 地址、CNAME 别名和 SRV 服务信息等记录。
- Cilium DNS 策略和基于已学习 IP 的 FQDN 策略是相关但不同的控制机制。

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- Extended Berkeley Packet Filter：由 Cilium 使用的可编程内核钩子及相关基础设施。
- 验证器会在接受程序前检查程序属性。它并不保证内核或验证器实现不存在漏洞。

**Endpoint** - Cilium

- 由 Cilium 管理的网络端点，通常为 Pod，具有本地数据路径/策略状态。
- 其端点 ID 对 Agent 本地有效，且不同于可由多个端点共享的安全身份。

**Envoy** - Cilium

- Cilium 用于已配置的 HTTP/gRPC 策略、L7 可见性和基于代理的服务路由的开源代理。
- DNS 策略使用 Cilium 的 DNS 代理。Kafka L7 策略已不再受支持；并非每条 L7 规则都会自动部署 Envoy 实例。

## F

**FQDN (Fully Qualified Domain Name)**

- Fully Qualified Domain Name：用于标识其在 DNS 树中完整位置的绝对名称，通常以最终的根点书写，例如 `www.example.com.`。
- Cilium `toFQDNs` 允许已学习的目标 IP。它本身不会验证 HTTPS 服务器身份，也不会约束共享 IP 上的所有 HTTP Host 值。

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- 用于网络虚拟化的封装协议

**gRPC (gRPC Remote Procedure Call)**

- 由 Google 开发的高性能 RPC (Remote Procedure Call) 框架

## H

**Hubble** - Cilium

- Cilium 的网络可观测性层：流事件、受支持的协议元数据、指标和查询接口。
- 历史记录有边界，观测可能丢失或被过滤。告警、持久化存储和自动响应需要配置集成。

## I

**Identity** - Cilium

- 从与安全相关的标签派生出的数字安全标识符。多个端点可以在适用的分配范围内共享它。
- 在 CRD 分配模式下，CiliumIdentity 的 `security-labels` 字段是事实来源。保留身份和节点本地身份并非都由这些集群范围对象表示。

**IPAM (IP Address Management)** - 网络

- IP Address Management：地址分配、跟踪和回收。
- Cilium 模式具有不同的分配所有者和数据源，包括 cluster-pool、multi-pool、Kubernetes host-scope 和云特定模式。平台名称不一定是独立的 `ipam.mode` 值。

**IPsec** - 网络

- Internet Protocol Security：一套用于 IP 层身份验证/完整性，以及在适当配置下用于保密性的机制。
- Cilium 使用 IPsec 对受支持的节点间流量进行加密；密钥管理和特定路径的限制仍然适用。

**Istio**

- 实现服务网格的开源平台

## K

**Kafka**

- 分布式事件流平台。它仍可作为工作负载使用，但当前 Cilium 不提供以前的 Kafka 主题 L7 策略 API。

**kube-proxy** - Kubernetes

- 通过受支持的节点网络机制实现 Service 虚拟 IP/端口转发的 Kubernetes 组件。
- Cilium 可使用 eBPF 替代该功能；XDP 加速是可选的，并且平台必须支持所选配置。

**Kubernetes**

- 用于自动部署、扩缩和管理容器化应用程序的开源平台

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

- 一种流量分配功能。Kubernetes `type: LoadBalancer` 会向控制器/提供商请求实现；若没有此类实现，则不保证存在外部负载均衡器。

## M

**MAC (Media Access Control) Address**

- Media Access Control 地址：与接口关联的链路层地址。
- 地址可能是本地管理的或会发生变化；不应假定其唯一性和真实性。

**mTLS (mutual TLS)**

- Mutual TLS：双方对等方均进行身份验证的 TLS，通常通过验证彼此的证书实现。
- 对等方身份验证不同于应用程序授权。Cilium 的带外双向身份验证和 Beta ztunnel 工作负载 mTLS 是具有不同流量保护属性的独立功能。

**MTU (Maximum Transmission Unit)**

- Maximum Transmission Unit：在链路/接口上无需分片即可承载的最大网络层数据包，包括其 IP 头部，但不包括链路层头部。
- 路径 MTU 受路径限制；隧道/加密开销会影响可用的内部数据包大小。它不是 TCP MSS 或应用程序负载大小。

## N

**NAT (Network Address Translation)**

- 修改 IP 数据包中 IP 地址信息的过程

**NodePort**

- 一种 Kubernetes Service 暴露方法，在符合条件的节点地址上使用已分配的节点端口。
- 地址选择、流量策略、防火墙和平台路由决定可达性；声明 NodePort 不保证公共访问。

## O

**OSI (Open Systems Interconnection) Model**

- 将网络通信分类为 7 个抽象层的概念模型

**Overlay Network**

- 构建在现有网络之上的虚拟网络

## P

**Pod**

- Kubernetes 中最小的可部署计算单元

**Proxy**

- 在对等方之间调解通信的组件；不一定是独立的物理服务器。

## R

**RBAC (Role-Based Access Control)**

- 基于角色控制对系统资源访问的方法

## S

**Service**

- 用于访问逻辑后端集合（通常是由标签选择的 Pods）的 Kubernetes 抽象。
- 普通 ClusterIP Services 具有虚拟 IP；无头 Services 没有。ExternalName 使用 DNS 别名，而无选择器 Services 可以使用手动管理的 EndpointSlices。

**SNAT (Source Network Address Translation)**

- 修改数据包源 IP 地址的 NAT 类型

**Socket**

- 用于网络或本地进程间通信的操作系统通信端点。

## T

**TCP (Transmission Control Protocol)**

- 提供可靠字节流的面向连接传输协议

**TLS (Transport Layer Security)**

- 保护网络通信的加密协议

## U

**UDP (User Datagram Protocol)**

- 无连接传输协议

## V

**VETH (Virtual Ethernet)**

- 虚拟 Ethernet 设备，通常成对创建

**VNI (VXLAN Network Identifier)**

- VXLAN Network Identifier：VXLAN 头部中的一个 24 位字段。
- Cilium 可在覆盖网络元数据中携带身份信息；该字段宽度并不承诺可独立配置数百万个租户网络。

**VTEP (VXLAN Tunnel Endpoint)**

- 负责封装和解封装 VXLAN 数据包的端点

**VXLAN (Virtual Extensible LAN)** - 网络

- 在 Layer 3 网络之上覆盖 Layer 2 网络的网络虚拟化技术
- Cilium 的覆盖网络模式之一

## W

**WireGuard** - 网络

- Cilium 用于受支持跨节点流量的 VPN 隧道协议。
- 同一节点上的 Pod 流量不会由其节点隧道加密；外部流量和可选节点加密具有各自的限制。相对于 IPsec 的性能需要进行可比测量。

## X

**XDP (eXpress Data Path)** - eBPF

- eXpress Data Path：一种数据包处理钩子；原生 XDP 在受支持网络驱动程序的接收路径中运行。
- PASS 会继续进入网络栈；其他操作可丢弃、传输或重定向。Cilium 受支持的 XDP 加速是可选功能，而非通用吞吐量或 DDoS 防护保证。

## 主要参考资料

- [Cilium 身份](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/security-identities.rst)
- [CiliumIdentity 模式](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/internals/cilium_operator.rst)
- [身份管理模式](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF 环形缓冲区](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC 寻址 / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## 测验

[主题测验](../../quizzes/networking/cilium/glossary-quiz.md)
