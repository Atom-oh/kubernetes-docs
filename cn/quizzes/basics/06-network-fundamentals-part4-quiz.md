# 网络基础第 4 部分测验：旅程与云

> **最后更新**：2026年9月11日

测试你对请求完整旅程以及云/Kubernetes 对应关系的理解。

## 选择题

1. 对于一个新的 HTTPS 连接，在不考虑缓存和现有连接的情况下，以下哪项是正确的概念性依赖顺序？
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) 解析服务器地址 → 使用链路/IP 连通性 → TCP+TLS 或 QUIC 握手 → HTTP 请求
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) TCP 连接 → DNS 查询 → TLS → 路由 → HTTP

<details>
<summary>显示答案</summary>

**答案：B) 解析服务器地址 → 使用链路/IP 连通性 → TCP+TLS 或 QUIC 握手 → HTTP 请求**

**解释：**
这是对依赖关系的总结，不是数据包跟踪。DNS 消息本身也要使用链路/IP 连通性；ARP 或 IPv6 邻居发现可能发生在 DNS 期间，也可能发生在后续流量传输期间。NAT 是可选的，而路由适用于每个相关数据包。HTTP/3 使用集成了 TLS1.3 的 QUIC；HTTP/1.1 和 HTTP/2 通常使用 TCP，并在 HTTPS 中进行单独的 TLS 握手。

</details>

2. 在使用 kube-proxy 的集群中，哪一项描述了普通 ClusterIP Service 的转发方式？
   - A) CoreDNS：DHCP
   - B) kube-proxy：NAT + L4 负载均衡
   - C) CNI 插件：TLS 终止
   - D) NetworkPolicy：BGP 路由

<details>
<summary>显示答案</summary>

**答案：B) kube-proxy：NAT + L4 负载均衡**

**解释：**
在 Linux 上，kube-proxy 会配置 iptables 或 nftables；自 Kubernetes 1.35 起，其 IPVS 模式已弃用。基于 eBPF 的 Service 实现可以取代 kube-proxy，但它并不是 kube-proxy 的一种 eBPF 模式。Service/EndpointSlice 状态会提供符合条件的端点。Headless Service 不使用 ClusterIP，而 NetworkPolicy 需要有相应的实现支持。

</details>

3. 检查端点依赖关系和总成本后，对于受支持的 AWS 服务流量，哪项做法可以减少 NAT Gateway 的处理量？
   - A) 每个区域仅使用一个 NAT Gateway
   - B) 对受支持的服务流量使用合适的 VPC 端点，并配置所需的 DNS、路由和访问策略
   - C) 为每个 Pod 分配一个公有 IP
   - D) 禁用 IPv6

<details>
<summary>显示答案</summary>

**答案：B) 对受支持的服务流量使用合适的 VPC 端点，并配置所需的 DNS、路由和访问策略**

**解释：**
端点可以将匹配的服务流量从 NAT 路径中移除，但接口端点会产生按小时和按数据量计费的费用，拓扑也会影响结果。S3/DynamoDB 网关端点不收取额外的端点费用。拉取私有 ECR 镜像通常需要 ecr.api 和 ecr.dkr 接口端点，以及一条 S3 路径、私有 DNS 和适当的访问配置。首次通过拉取缓存获取镜像，或获取外部 Windows 层，仍可能需要互联网访问。请计算总成本并保留所需的出站流量；节省成本和消除端口耗尽并非普遍适用的保证。

</details>

---

[返回学习材料](../../basics/06-network-fundamentals-part4.md) | [下一测验：第 5 部分](./06-network-fundamentals-part5-quiz.md)
