# 网络基础第 4 部分测验：请求旅程与云

> **最后更新**：2026 年 9 月 11 日

测试你对请求完整路径以及云/Kubernetes 对应关系的理解。

## 单选题

1. 建立新的 HTTPS 连接时（不考虑缓存和现有连接），以下哪项描述了正确的概念性依赖顺序？
   - A) TLS → DNS → ARP → TCP → HTTP
   - B) 解析服务器地址 → 使用链路/IP 连通性 → 完成 TCP+TLS 或 QUIC 握手 → 发送 HTTP 请求
   - C) ARP → TLS → DNS → NAT → HTTP
   - D) 建立 TCP 连接 → 查询 DNS → TLS → 路由 → HTTP

<details>
<summary>显示答案</summary>

**答案：B) 解析服务器地址 → 使用链路/IP 连通性 → 完成 TCP+TLS 或 QUIC 握手 → 发送 HTTP 请求**

**解释：**
这是对依赖关系的概述，并非数据包传输跟踪。DNS 消息本身也使用链路/IP 连通性；ARP 或 IPv6 邻居发现可能发生在 DNS 通信期间，也可能发生在后续流量期间。NAT 是可选的，而路由适用于每个相关数据包。HTTP/3 使用集成了 TLS 1.3 的 QUIC；HTTPS 中的 HTTP/1.1 和 HTTP/2 通常使用 TCP，并单独执行 TLS 握手。

</details>

2. 在使用 kube-proxy 的集群中，哪组对应关系描述了普通 ClusterIP Service 的转发方式？
   - A) CoreDNS：DHCP
   - B) kube-proxy：NAT + L4 负载均衡
   - C) CNI 插件：TLS 终止
   - D) NetworkPolicy：BGP 路由

<details>
<summary>显示答案</summary>

**答案：B) kube-proxy：NAT + L4 负载均衡**

**解释：**
在 Linux 上，kube-proxy 会配置 iptables 或 nftables；自 Kubernetes 1.35 起，IPVS 模式已弃用。基于 eBPF 的 Service 实现可以替代 kube-proxy，但这并不是 kube-proxy 的一种 eBPF 模式。Service/EndpointSlice 状态会提供符合条件的端点。Headless Service 不使用 ClusterIP，而 NetworkPolicy 需要由支持它的实现来执行。

</details>

3. 在检查端点依赖关系和总成本之后，哪种方式可以减少受支持 AWS 服务流量的 NAT Gateway 处理量？
   - A) 每个区域只部署一个 NAT Gateway
   - B) 为受支持的服务流量使用合适的 VPC 端点，并配置所需的 DNS、路由和访问策略
   - C) 为每个 Pod 分配公有 IP
   - D) 禁用 IPv6

<details>
<summary>显示答案</summary>

**答案：B) 为受支持的服务流量使用合适的 VPC 端点，并配置所需的 DNS、路由和访问策略**

**解释：**
端点可以让匹配的服务流量绕过 NAT 路径，但接口端点会产生按小时和数据量计费的费用，拓扑结构也会影响结果。S3/DynamoDB 网关端点不收取额外端点费用。私有 ECR 镜像拉取通常需要 ecr.api 和 ecr.dkr 接口端点，以及 S3 访问路径、私有 DNS 和适当的访问权限。首次通过拉取缓存获取镜像或外部 Windows 层仍可能需要互联网访问。应计算总成本并保留必要的出站流量；节省费用和消除端口耗尽问题都不是普遍保证。

</details>

---

[返回学习资料](../../basics/06-network-fundamentals-part4.md) | [下一测验：集群架构](../core/01-cluster-architecture-quiz.md)
