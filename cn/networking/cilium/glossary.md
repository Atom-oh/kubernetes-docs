# 术语表和缩略语

> **最后更新**: February 22, 2026

本文档提供与 Cilium 相关的关键术语和缩略语说明。本术语表有助于理解 Cilium、eBPF、Kubernetes 和网络概念。

## 术语类别

术语分为以下类别：
- 蓝色 **与 Cilium 相关的术语**
- 橙色 **与 eBPF 相关的术语**
- 绿色 **与 Kubernetes 相关的术语**
- 紫色 **与网络相关的术语**
- 白色 **通用术语**

## A

**API (Application Programming Interface)** - 通用
- 使应用程序能够相互通信的一组接口定义

**AWS ENI (Elastic Network Interface)** - 网络
- 由 Amazon Web Services 提供的虚拟网络接口
- 用于 Cilium 的 AWS ENI IPAM 模式

**ARP (Address Resolution Protocol)** - 网络
- 将 IP 地址转换为 MAC 地址的协议
- L2 网络通信必不可少的协议

## B

**BGP (Border Gateway Protocol)** - 网络
- 用于在 Internet 上交换路由信息的标准外部网关协议
- 可在 Cilium 中用作原生路由模式

**BPF (Berkeley Packet Filter)** - eBPF
- 用于数据包过滤的技术，是 eBPF 的前身
- 最初为网络数据包捕获而开发

**BPF Maps** - eBPF
- 用于在 eBPF 程序中存储和检索数据的键值存储
- 用于在用户空间和内核空间之间共享数据

## C

**CGroup (Control Group)** - Kubernetes
- 限制并隔离进程组资源使用的 Linux 内核功能
- 用于限制容器资源

**CIDR (Classless Inter-Domain Routing)** - 网络
- 用于 IP 地址分配和路由聚合的方法
- 示例：192.168.1.0/24 表示从 192.168.1.0 到 192.168.1.255 的 IP 地址范围

**CNI (Container Network Interface)** - Kubernetes
- 容器运行时与网络插件之间的标准接口
- Cilium 是 CNI 实现之一

**CoreDNS** - Kubernetes
- Kubernetes 集群中常用的 DNS 服务器
- 在服务发现中发挥重要作用

**CRD (Custom Resource Definition)** - Kubernetes
- 通过扩展 Kubernetes API 来定义自定义资源的方法
- Cilium 使用 CRD 定义网络策略等

**Cilium** - Cilium
- 基于 eBPF 的开源网络、安全和可观测性解决方案
- 用作 Kubernetes CNI 实现

## D

**DNAT (Destination Network Address Translation)** - 网络
- 修改数据包目标 IP 地址的 NAT 类型
- 用于负载均衡和端口转发

**DNS (Domain Name System)** - 网络
- 将域名转换为 IP 地址的系统
- Cilium 支持基于 DNS 的网络策略

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF
- 允许在 Linux 内核中安全执行程序的技术
- Cilium 使用的核心技术

**Endpoint** - Cilium
- 在 Cilium 中应用网络策略的工作负载单元
- 通常对应于 Kubernetes Pod

**Envoy** - Cilium
- L7 代理和 Service Mesh 组件
- 用于在 Cilium 中执行 L7 策略

## H

**Hubble** - Cilium
- Cilium 的可观测性层
- 用于实时监控和分析网络流的工具

## I

**IPAM (IP Address Management)** - 网络
- 负责分配、跟踪和管理 IP 地址的系统
- Cilium 支持多种 IPAM 模式

**IPsec** - 网络
- 通过加密 IP 数据包提供安全通信的协议套件
- 可用于 Cilium 中的节点间流量加密

## K

**kube-proxy** - Kubernetes
- 实现 Kubernetes Service 抽象的网络代理
- Cilium 可以替代 kube-proxy

## V

**VXLAN (Virtual Extensible LAN)** - 网络
- 在 L3 网络上覆盖 L2 网络的网络虚拟化技术
- Cilium 的覆盖网络模式之一

## W

**WireGuard** - 网络
- 现代且快速的 VPN 协议
- 可用于 Cilium 中的节点间流量加密

## X

**XDP (eXpress Data Path)** - eBPF
- 在网络驱动程序级别处理数据包的 eBPF 功能
- 提供极高性能的数据包处理

**DaemonSet**
- 在所有节点上运行一个 Pod 副本的 Kubernetes 资源

## E

**eBPF (extended Berkeley Packet Filter)**
- 允许在 Linux 内核中安全执行程序的技术

**Endpoint**
- 在 Cilium 中应用网络策略的网络端点（通常为 Pod）

**Envoy**
- 用作 L7 代理和通信总线的开源边缘及服务代理

## F

**FQDN (Fully Qualified Domain Name)**
- 主机的完整域名（例如，www.example.com）

## G

**GENEVE (Generic Network Virtualization Encapsulation)**
- 用于网络虚拟化的封装协议

**gRPC (gRPC Remote Procedure Call)**
- 由 Google 开发的高性能 RPC（Remote Procedure Call）框架

## H

**Hubble**
- Cilium 的网络可见性和监控组件

## I

**IPAM (IP Address Management)**
- IP 地址的规划、跟踪和管理

**IPsec (Internet Protocol Security)**
- 用于 IP 通信安全的协议套件

**Istio**
- 实现 Service Mesh 的开源平台

## K

**Kafka**
- 分布式流处理平台

**kube-proxy**
- 实现 Kubernetes Service 抽象的网络代理

**Kubernetes**
- 用于自动部署、扩缩容和管理容器化应用程序的开源平台

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
- 在多个服务器之间分配流量的设备或服务

## M

**MAC (Media Access Control) Address**
- 分配给网络接口的唯一标识符

**MTU (Maximum Transmission Unit)**
- 可通过网络传输的最大数据包大小

**mTLS (mutual TLS)**
- TLS 的扩展，其中客户端和服务器均使用证书相互验证身份

## N

**NAT (Network Address Translation)**
- 修改 IP 数据包中 IP 地址信息的过程

**NodePort**
- 在每个节点的 IP 上公开静态端口的 Kubernetes Service 类型

## O

**OSI (Open Systems Interconnection) Model**
- 将网络通信划分为 7 个抽象层的概念模型

**Overlay Network**
- 构建在现有网络之上的虚拟网络

## P

**Pod**
- Kubernetes 中最小的可部署计算单元

**Proxy**
- 充当客户端与服务器之间中介的服务器

## R

**RBAC (Role-Based Access Control)**
- 基于角色控制对系统资源访问的方法

## S

**Service**
- Kubernetes 中为一组 Pod 提供稳定端点的抽象

**SNAT (Source Network Address Translation)**
- 修改数据包源 IP 地址的 NAT 类型

**Socket**
- 网络上进程间通信的端点

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
- 虚拟以太网设备，通常成对创建

**VNI (VXLAN Network Identifier)**
- 用于标识 VXLAN 网络的 24 位标识符

**VTEP (VXLAN Tunnel Endpoint)**
- 负责封装和解封装 VXLAN 数据包的端点

**VXLAN (Virtual Extensible LAN)**
- 在 L3 网络上覆盖 L2 网络的网络虚拟化技术

## W

**WireGuard**
- 现代、快速且安全的 VPN 隧道协议

## X

**XDP (eXpress Data Path)**
- 基于 eBPF 的超高速网络数据包处理技术

## Quiz

要测试本章所学内容，请尝试 [Topic Quiz](../../quizzes/networking/cilium/glossary-quiz.md)。
