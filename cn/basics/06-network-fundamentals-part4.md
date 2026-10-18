# 网络基础（第 4 部分）：一个请求的完整旅程与云上对应关系

> **最后更新**：October 12, 2026

::: tip 本文属于四篇系列
[第 1 部分：分层模型、链路层与路由层](./06-network-fundamentals-part1.md) ·
[第 2 部分：传输层与 TLS](./06-network-fundamentals-part2.md) ·
[第 3 部分：应用层协议](./06-network-fundamentals-part3.md) ·
**第 4 部分：一个请求的旅程与云**（本文）
:::

本部分通过一个示例请求串联本系列介绍的 25 种协议和机制，并将相关职责映射到 AWS 和 Kubernetes 中。这些是功能上的对照关系，并非一一替代。

![示意请求路径：地址配置和 DNS、本地交付和路由、可选的 NAT，之后使用 TCP 加 TLS 运行 HTTP/1.1 或 HTTP/2，或使用集成 TLS 的 QUIC 运行 HTTP/3。复用缓存或网络配置可能跳过部分步骤。](../.gitbook/assets/en-basics-06-network-fundamentals-part4-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part4-0.html)

---

## 6. 跟踪一个请求的完整路径

对于到 `https://example.com` 的新连接，以下内容是一个概念性的依赖关系指南，并非数据包跟踪：DNS 查询和握手数据包本身也会使用链路层和路由层；缓存状态或已有连接可能跳过某些操作。

1. **地址配置**：主机已经配置好地址、路由和解析器设置，这些信息可能来自 DHCP、静态配置、IPv6 SLAAC/路由器通告或其他托管机制。
2. **DNS（或 DoH）**：在需要时解析目标地址。递归解析器可以使用自身缓存、跟随委派或转发查询；应用程序不需要直接联系根服务器。HTTPS 记录也可能通告连接参数。
3. **邻居解析**：对于通过以太网传输的 IPv4，如果下一跳的 MAC 地址不在缓存中，就使用 ARP 进行解析；IPv6 使用邻居发现。下一跳可以是本地目标，也可以是路由器。
4. **以太网 / Wi-Fi**：将帧发送给该下一跳。只有在所选路由要求时才会使用默认网关。
5. **IP 路由**：路由器根据转发表转发数据包。路由可以是静态路由、直连路由，也可以通过 BGP、OSPF 或其他控制平面学习；路由协议不会针对每个请求都重新协商。
6. **可选的 NAT**：IPv4 出网路径可能会将私有地址转换为公网地址。许多内部路径和 IPv6 路径不会使用 NAT；也存在私有地址到私有地址的 NAT。
7. **TCP 或 QUIC**：建立或复用传输连接。HTTP/1.1 和 HTTP/2 通常使用 TCP；HTTP/3 使用运行在 UDP 之上的 QUIC。
8. **TLS**：根据握手模式验证对端并建立流量密钥。对于 QUIC，TLS 1.3 与第 7 步集成；会话恢复与全新的基于证书的握手有所不同。
9. **HTTP**：使用协商好的版本交换请求和响应。HTTP/3 必须走 QUIC 分支，不能运行在 TCP 分支上。
10. **可选的应用层功能**：WebSocket、兼容浏览器的 gRPC 或 WebRTC 可能会创建额外连接，也可能根据具体实现复用或多路复用现有传输连接。

**ICMP** 可以报告某些 IP 层错误，例如目标不可达，或数据包对于当前路径而言过大。它不会报告所有故障：数据包或 ICMP 错误可能被过滤，而 TLS 或应用层故障则使用各自的机制。应结合允许且相关的 ICMP 信息，以及传输层和应用层日志与测量结果进行判断；没有收到 ICMP 错误并不能证明请求成功。

---

## 7. 这些概念在云中的对应位置

云网络仍然承担寻址、路由、过滤和传输等职责，但边界与传统网络设备有所不同。在 AWS 中：

| 传统概念 | AWS 对应项 |
|---|---|
| 分段与过滤 | VPC / 子网用于划分逻辑网络边界；安全组和网络 ACL 用于过滤，但它们并不等同于 VLAN |
| 路由表 | VPC 路由表、Transit Gateway |
| BGP 对等连接 | Direct Connect 虚拟接口；支持动态路由的 Site-to-Site VPN（也可以使用静态 VPN 路由） |
| NAT / 私有服务访问 | NAT Gateway 转换地址；VPC 端点为受支持的服务提供私有路径 |
| DNS 服务器 | Route 53、Resolver 端点 |
| DHCP | VPC DHCP 选项集 |
| TLS 终止 / 证书 | ALB HTTPS 监听器、NLB TLS 监听器或 CloudFront；ACM 管理受支持的证书，但不转发流量 |
| L7 负载均衡 | ALB；也可以在单独管理的服务网格中使用 Istio / Envoy 等应用代理 |
| SSH 访问 | Systems Manager Session Manager |
| 内部网段加密 | 在应用或代理中配置 TLS / mTLS；网络层加密属于另一项设计选择 |

AWS App Mesh 支持已于 **2026 年 9 月 30 日结束**。AWS 表示，该日期之后将无法再访问 App Mesh 控制台和资源。现有部署已失去其控制与管理路径；请参阅官方的停止支持公告和迁移指南。

设计时应先作出以下三项决定：

1. **IP 地址规划**：为需要互连的网络规划 CIDR，包括本地网络、Pod 和 Service 的地址范围。地址重叠可能需要地址转换或重新设计；重新编号会带来运维成本，但不存在适用于所有情况的统一成本排序。
2. **出站路径**：为每个目标匹配互联网或私有服务路径。比较 NAT 按小时和按数据量计费的费用、接口端点的按小时和按数据量费用、跨可用区传输费用以及可用性要求。S3 / DynamoDB 网关端点不收取额外端点费用，但端点不能替代所有互联网目标。
3. **加密终止点**：记录每一跳上的加密和身份验证方式，包括负载均衡器之后的后端连接。检查工作负载的要求和适用策略；仅在负载均衡器处终止 TLS 并不能保护下一跳。

---

## 8. Kubernetes 中由谁完成这些工作

同样的概念在集群内部会以新的组件名称再次出现。下表将本系列与后续深入介绍的文档联系起来。

| 传统概念 | Kubernetes 对应项 |
|---|---|
| Pod IP 分配 | CNI / IPAM 集成（VPC CNI、Cilium 等）；这不一定意味着每个 Pod 都使用 DHCP |
| 本地交付 / 转发 | 主机接口、邻居处理和 CNI 数据路径；实现可能使用 veth、路由、隧道或 eBPF |
| DNS | 集群 DNS，通常为 CoreDNS；`service.namespace.svc.<cluster-domain>`（`cluster.local` 是常见的已配置域名） |
| Service 虚拟 IP / L4 负载均衡 | Linux 上的 kube-proxy：iptables 或 nftables；IPVS 自 1.35 起已弃用。eBPF 实现可以替代 kube-proxy，但它不是 kube-proxy 的一种模式 |
| Pod 流量策略 | NetworkPolicy；只有支持它的网络控制器 / 插件才会实施策略 |
| L7 路由 / TLS 终止 | Ingress / Gateway API 资源，以及负责实现它们的控制器和数据平面 |
| 服务间 mTLS | 应用 TLS，或配置好的 Istio / Linkerd 等服务网格；仅安装任意 CNI 并不会自动启用 mTLS |
| BGP 路由 / 通告 | 例如，Calico BGP 路由，或 MetalLB 通过 BGP 通告 Service 地址；两者作用不同 |

对于一个由 Pod 提供后端的普通 ClusterIP Service，集群 DNS 通常会解析出 Service IP，然后由 kube-proxy 或其替代实现根据 Service / EndpointSlice 状态选择可用端点。数据路径会将流量转发到该端点，无论它位于本节点还是其他节点。Headless Service 会通过 DNS 暴露端点地址；ExternalName Service 则会返回 CNAME。只有配置了相关对等端和策略时，mTLS 才会生效。因此，假设“每个数据包都必定经过每一层”并不成立。

---

## 总结

走完这 25 种协议和机制后，请仔细考虑其中的权衡，以及各项保证的适用范围。

TCP 提供有序、可靠的传输，但需要承担恢复和排序的开销。UDP 将这些职责留给更高层。QUIC 通过 UDP 提供可靠数据流和集成安全能力。NAT 可以节省公网 IPv4 地址，但会增加主动发起入站连接的难度；ICE / STUN / TURN 可以帮助处理相关问题。DoH 保护的是到解析器这一跳；组织能够看到什么，取决于解析器和端点策略。

排查故障时，应依据每一层实际提供的保证和可观察到的证据来缩小故障范围。在日志、跟踪或测量结果能够排除其他可能性之前，合理的协议层解释仍然只是一个假设。

---

## 后续文档

先将这些协议基础知识与 Linux 上的观测结果联系起来，然后沿着[网络学习路径](../networking/README.md#learning-path)，从容器和 Service 学到 CNI 实现：

- [内核网络栈](../kernel/02-network-stack.md)：套接字 / VFS 入口路径、缓冲区和数据包处理
- [Linux 网络诊断实践](../networking/07-linux-network-diagnostics.md)：解读观测结果并验证假设 | [测验](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
- [eBPF 基础知识](./05-ebpf-fundamentals.md)：内核如何处理数据包
- [Cilium 网络](../networking/cilium/03-networking.md)：基于 eBPF 的 CNI
- [Calico BGP 深入解析](../networking/calico/04-bgp-deep-dive.md)：集群内的 BGP 路由
- [Amazon VPC CNI](../networking/01-vpc-cni.md)：VPC CNI 与 IP 分配

## 参考资料

协议列表最初参考了 ByteByteGo 的“What Keeps the Internet Running?”信息图；具体说明和实践评论均为独立撰写。

主要参考资料：[Kubernetes Service 代理模式](https://kubernetes.io/docs/reference/networking/virtual-ips/)、[Service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)、[NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)、[NAT Gateway 费用指南](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html)、[ECR VPC 端点](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)、[App Mesh 生命周期](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)。
