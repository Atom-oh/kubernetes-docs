# Cilium 网络概念测验

> **基线版本**：Cilium 1.20.3。
> **最近审核时间**：2026 年 10 月 16 日。

[返回指南](../../../networking/cilium/networking-concepts.md)

## OSI 和基本概念

1. **关于 Cilium 策略功能，哪种描述是正确的？**

   - A) 仅为通用 MAC 地址防火墙
   - B) 仅支持 L3/L4，不集成代理
   - C) 仅支持 HTTP 策略
   - D) L3/L4 控制以及已配置的受支持 L7 规则

   <details>
   <summary>显示答案</summary>

   **答案：D) L3/L4 控制以及已配置的受支持 L7 规则**

   Cilium 将 L3/L4 策略执行与受支持的 HTTP/gRPC 和 DNS 代理功能结合起来。这并不意味着实现 OSI 的每一层，也不意味着支持已移除的 Kafka L7 API。

   </details>

2. **以下哪项是链路层地址？**

   - A) IP 地址
   - B) MAC 地址
   - C) 端口号
   - D) URL

   <details>
   <summary>显示答案</summary>

   **答案：B) MAC 地址**

   MAC 地址用于标识链路层接口。它可以在本地分配或更改，因此无法保证其全局唯一性和真实性。

   </details>

3. **哪种协议提供网络层 IP 寻址？**

   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>显示答案</summary>

   **答案：C) IP**

   IP 提供逻辑寻址和网络层数据包传输；TCP 和 UDP 具有不同的传输语义。

   </details>

## 容器网络

4. **未被平台特定配置覆盖时，Cilium Helm 的通用默认路由模式是什么？**

   - A) Docker 网桥
   - B) 隧道/覆盖网络模式
   - C) 强制使用 BGP 原生模式
   - D) 所有工作负载都使用主机网络

   <details>
   <summary>显示答案</summary>

   **答案：B) 隧道/覆盖网络模式**

   通用默认值是隧道模式。特定平台的安装配置可以选择其他模式；这不是 EKS 或所有云环境通用的不变规则。

   </details>

5. **Cilium 通用隧道安装配置的默认协议是什么？**

   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>显示答案</summary>

   **答案：A) VXLAN**

   VXLAN 是默认隧道协议，Cilium 默认使用 UDP 8472。标准 VXLAN 分配的 UDP 端口是 4789。

   </details>

6. **原生路由的一项具体特性是什么？**

   - A) 自动加密
   - B) 无需返回路由
   - C) 该路径上没有覆盖网络封装
   - D) 保证获得最佳吞吐量

   <details>
   <summary>显示答案</summary>

   **答案：C) 该路径上没有覆盖网络封装**

   原生路由无需添加覆盖网络头部，但需要确保 Pod 可达且返回路由有效。性能取决于工作负载和具体实现。

   </details>

## IPAM

7. **未被平台特定配置覆盖时，通用 Helm IPAM 的默认模式是什么？**

   - A) kubernetes
   - B) cluster-pool
   - C) 名为 PodCIDR 的模式
   - D) eni

   <details>
   <summary>显示答案</summary>

   **答案：B) cluster-pool**

   在 cluster-pool 模式下，控制器分配节点 CIDR，每个代理在本地分配 Pod IP。请使用实际的模式名称，而不要使用含义不明确的“Cluster Scope”（集群范围）一词。

   </details>

8. **哪种 Cilium IPAM 模式会使用 EC2 ENI 和 VPC 地址？**

   - A) Kubernetes host-scope（主机范围）
   - B) Cluster-pool
   - C) ENI
   - D) 通用的基于 CRD 的模式

   <details>
   <summary>显示答案</summary>

   **答案：C) ENI**

   ENI 模式有 AWS 特定的前置条件。它并非适用于所有 EKS 计算模式或 CNI 链式配置的通用建议。

   </details>

9. **ipam.mode: kubernetes 使用哪些 Node 字段？**

   - A) spec.podCIDR / spec.podCIDRs
   - B) spec.CIDR
   - C) spec.Subnet
   - D) spec.IPRange

   <details>
   <summary>显示答案</summary>

   **答案：A) spec.podCIDR / spec.podCIDRs**

   Kubernetes 会为节点分配 Pod CIDR。Cilium 在 Kubernetes host-scope（主机范围）IPAM 中使用这些 CIDR；PodCIDR 并非 IPAM 模式的实际名称。

   </details>

## Service 和负载均衡

10. **哪项功能不能仅通过替代 kube-proxy 来启用？**

   - A) ClusterIP 转发
   - B) NodePort 转发
   - C) 受支持的 LoadBalancer Service 转发
   - D) 工作负载 mTLS

   <details>
   <summary>显示答案</summary>

   **答案：D) 工作负载 mTLS**

   Service 转发与工作负载身份验证/加密是两回事。创建外部负载均衡器还需要相应的控制器或服务提供商。

   </details>

11. **哪两种是 Cilium 的 BPF Service 负载均衡算法？**

   - A) Random 和 Maglev
   - B) 仅轮询算法
   - C) 默认使用最少连接算法
   - D) 定期轮换 Maglev 超时

   <details>
   <summary>显示答案</summary>

   **答案：A) Random 和 Maglev**

   Random 是默认算法，Maglev 则是在受支持路径上的替代算法。Envoy 算法、ClientIP 亲和性和亲和性超时是独立的概念。

   </details>

12. **配置 Global Service 后可以实现什么？**

   - A) 自动分配全球公共 IP
   - B) 跨已连接集群进行 Service 负载均衡
   - C) 自动复制所有策略
   - D) 共享持久化存储

   <details>
   <summary>显示答案</summary>

   **答案：B) 跨已连接集群进行 Service 负载均衡**

   这需要 ClusterMesh，以及名称和命名空间匹配的 Service。仍需验证端点/缓存行为和故障处理方式。

   </details>

## 网络策略

13. **toCIDR 会选择什么？**

   - A) 目标地址范围
   - B) 经过身份验证的 DNS 主机名
   - C) 仅限按名称指定的 Service
   - D) 仅限 TCP 端口

   <details>
   <summary>显示答案</summary>

   **答案：A) 目标地址范围**

   CIDR 选择器遵循端点分类规则；默认情况下会排除集群内受管理的 Pod/节点，而此版本提供需要显式启用的 Beta 选项。它不是身份验证机制。

   </details>

14. **world 实体代表什么？**

   - A) 所有已知的集群身份
   - B) 外部端点，而非已知的集群/ClusterMesh 身份
   - C) 所有 Kubernetes 节点
   - D) 所有命名空间

   <details>
   <summary>显示答案</summary>

   **答案：B) 外部端点，而非已知的集群/ClusterMesh 身份**

   world 并非所有集群中每个端点的同义词。请选择适当的实体/身份范围和所需端口。

   </details>

15. **Cilium 以前支持的哪项 L7 功能已被移除？**

   - A) HTTP 路径匹配
   - B) DNS 查询规则
   - C) Kafka 主题规则
   - D) HTTP 方法匹配

   <details>
   <summary>显示答案</summary>

   **答案：C) Kafka 主题规则**

   当前策略支持与 HTTP/gRPC 相关的代理功能和 DNS 规则；不要将旧的 Kafka 策略示例复制到当前 API 中。

   </details>

## 高级概念

16. **哪一组选项列出了两种可选的 Cilium 节点传输加密模式？**

   - A) HTTP 和 DNS
   - B) TCP 和 UDP
   - C) IPsec 和 WireGuard
   - D) Relay 和 Prometheus

   <details>
   <summary>显示答案</summary>

   **答案：C) IPsec 和 WireGuard**

   请选择适当的节点加密模式并验证覆盖范围。SPIRE 双向身份验证与 Beta ztunnel 工作负载 mTLS 的作用和前置条件各不相同。

   </details>

17. **Cilium 的多集群网络功能叫什么？**

   - A) Cluster Federation
   - B) ClusterMesh
   - C) Global Cluster
   - D) NodePort Mesh

   <details>
   <summary>显示答案</summary>

   **答案：B) ClusterMesh**

   ClusterMesh 会共享网络元数据并支持配置的跨集群连接；地址分配、信任关系和底层网络前置条件仍需满足。

   </details>

18. **Cilium BGP Control Plane 的作用是什么？**

   - A) 将所有学习到的路由写入本地数据路径
   - B) 向对等端通告选定的 Pod/Service 前缀
   - C) 自动创建 DNS 记录
   - D) 保证所有跨集群流量畅通

   <details>
   <summary>显示答案</summary>

   **答案：B) 向对等端通告选定的 Pod/Service 前缀**

   路由通告与地址分配和实际的数据包转发不同。请检查对等端的路由，并测试两个方向的流量。

   </details>

19. **Egress Gateway 如何处理匹配的出站流量？**

   - A) SNAT 为选定的网关 IP
   - B) 保留所有原始 Pod 源 IP
   - C) 自动加密外部流量
   - D) 无需前置条件即可创建网关接口

   <details>
   <summary>显示答案</summary>

   **答案：A) SNAT 为选定的网关 IP**

   它通过地址转换提供已配置的源地址。必须考虑接口/路由的准备工作，以及针对新 Pod 的策略收敛。

   </details>

20. **BPF 主机路由优化的是什么？**

   - A) 自动回退到原生/覆盖网络路由
   - B) 主机内部数据包转发以及对主机协议栈的使用
   - C) 主机防火墙授权
   - D) 存储加密

   <details>
   <summary>显示答案</summary>

   **答案：B) 主机内部数据包转发以及对主机协议栈的使用**

   在满足前置条件且符合集成限制的情况下，BPF 主机路由可以绕过主机协议栈/netfilter 的部分组件。这与选择节点之间使用原生路由还是隧道路由是两回事。

   </details>
