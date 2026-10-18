# Cilium 高级测验

> **复习基准版本**：Cilium 1.20.3；Cilium CLI 0.20.1；Hubble CLI 1.20.2。
> **最后审阅日期**：2026年10月16日。

[返回指南](../../../networking/cilium/07-advanced-topics.md)

## eBPF 技术

1. **本课程讨论的 Linux eBPF 数据路径程序在哪里执行？**

   - A) 仅在浏览器中
   - B) 在 Linux 内核支持的钩子处
   - C) 仅在 Envoy 内部
   - D) 在 Kubernetes API 服务器中

   <details>
   <summary>显示答案</summary>

   **答案：B) 在 Linux 内核支持的钩子处**

   Cilium 会将 eBPF 程序附加到内核钩子上。用户空间组件负责加载和管理这些程序。

   </details>

2. **内核接受 eBPF 程序前，会使用哪种机制检查程序？**

   - A) 加密
   - B) 容器调度
   - C) 验证器
   - D) DNS

   <details>
   <summary>显示答案</summary>

   **答案：C) 验证器**

   验证器会检查内存访问、执行是否有界等属性。但它并不能绝对保证不会出现实现漏洞或任何内核故障。

   </details>

3. **以下哪项不是 Cilium 软件 eBPF 数据路径的一般要求？**

   - A) 受支持的内核功能
   - B) 适当的权限
   - C) 兼容的网络配置
   - D) 专用硬件卸载

   <details>
   <summary>显示答案</summary>

   **答案：D) 专用硬件卸载**

   硬件卸载不是必需的。性能取决于实际路径、工作负载、内核和硬件。

   </details>

## 网络模型

4. **以下哪项不是本课程介绍的 Cilium 原生路由/隧道选项？**

   - A) VXLAN
   - B) Geneve
   - C) 原生路由
   - D) MPLS 数据路径模式

   <details>
   <summary>显示答案</summary>

   **答案：D) MPLS 数据路径模式**

   这里介绍的是 Cilium 的配置选项，并不禁止使用基于 MPLS 的外部底层网络。

   </details>

5. **Cilium kube-proxy 替代功能由什么实现？**

   - A) 仅使用 iptables 链
   - B) 仅使用 IPVS 规则
   - C) eBPF Service 处理，可选用 XDP 加速
   - D) 必须使用外部硬件交换机

   <details>
   <summary>显示答案</summary>

   **答案：C) eBPF Service 处理，可选用 XDP 加速**

   Service 处理由套接字和数据包路径上的 eBPF 实现。XDP 可加速符合条件的外部转发路径，并非每个 Service 都必须使用。

   </details>

6. **哪个 Cilium 可观测性组件会公开具有 Kubernetes 感知能力的流记录？**

   - A) Helm
   - B) Hubble
   - C) kube-scheduler
   - D) etcdctl

   <details>
   <summary>显示答案</summary>

   **答案：B) Hubble**

   Hubble 提供有限范围的观测结果，并非对每个数据包进行无损捕获。其他数据包分析工具的用途各不相同。

   </details>

## IPAM 和网络策略

7. **哪种 Cilium IPAM 模式使用 EC2 ENI 分配 VPC 地址？**

   - A) 集群池
   - B) Kubernetes 主机范围
   - C) ENI
   - D) 通用 CRD 支持模式

   <details>
   <summary>显示答案</summary>

   **答案：C) ENI**

   ENI 模式使用 AWS 网络接口和地址分配。这并不意味着每种 EKS 计算模式都支持替代 CNI；请检查平台的先决条件。

   </details>

8. **toFQDNs 使用什么来允许出站连接？**

   - A) 已验证的 JWT
   - B) 仅限固定的 Service 端口
   - C) 根据匹配的 DNS 名称学习到的目标 IP
   - D) 自动解密 TLS

   <details>
   <summary>显示答案</summary>

   **答案：C) 根据匹配的 DNS 名称学习到的目标 IP**

   允许 DNS 查询/通过代理观测 DNS，与之后的 IP 连通性是两回事。该规则不会对远端应用进行身份验证。

   </details>

9. **在 CiliumClusterwideNetworkPolicy 中，主机策略使用哪个选择器？**

   - A) 用于所有节点的 endpointSelector
   - B) nodeSelector
   - C) 顶层 serviceSelector
   - D) 顶层 namespaceSelector

   <details>
   <summary>显示答案</summary>

   **答案：B) nodeSelector**

   nodeSelector 是集群范围主机策略的字段。不要将所有 Kubernetes 选择器形式都描述为可互换的 CiliumNetworkPolicy 顶层字段。

   </details>

## L2–L7 网络

10. **以下哪项不是 Cilium HTTP 策略中的请求匹配字段？**

   - A) 路径
   - B) 方法
   - C) 标头
   - D) 响应延迟

   <details>
   <summary>显示答案</summary>

   **答案：D) 响应延迟**

   当 HTTP 内容可见时，HTTP 规则会检查受支持的请求字段。测量延迟并不会新增基于延迟的允许规则字段。

   </details>

11. **仅使用基于身份的网络策略，无法提供什么？**

   - A) 端点选择
   - B) 网络访问限制
   - C) 按方向划分的规则
   - D) 终端用户令牌身份验证

   <details>
   <summary>显示答案</summary>

   **答案：D) 终端用户令牌身份验证**

   用户身份验证需要适当的应用或网关逻辑。SPIRE 双向身份验证和 Beta ztunnel 工作负载 mTLS 是分别配置的功能，且各自都有局限性。

   </details>

12. **在适当路径上配置后，Cilium 的 Envoy 集成可以提供什么？**

   - A) HTTP 负载均衡
   - B) HTTP 可见性
   - C) HTTP 策略实施
   - D) 以上全部

   <details>
   <summary>显示答案</summary>

   **答案：D) 以上全部**

   这些能力取决于所选的代理路径和配置；启用无关的网络功能并不会激活所有 L7 能力。

   </details>

## 安全和可见性

13. **以下哪项是 Hubble UI 的功能？**

   - A) 自动创建 Slack 事件
   - B) 服务依赖关系图和流探索
   - C) 源代码部署管理
   - D) JWT 签名密钥轮换

   <details>
   <summary>显示答案</summary>

   **答案：B) 服务依赖关系图和流探索**

   通知和自动响应需要单独集成。该 UI 可将观测到的网络流可视化。

   </details>

14. **以下哪些是 Cilium 节点传输加密的可选模式？**

   - A) IPsec 和 WireGuard
   - B) HTTP 和 DNS
   - C) Relay 和 Prometheus
   - D) TCP 和 UDP

   <details>
   <summary>显示答案</summary>

   **答案：A) IPsec 和 WireGuard**

   必须检查它们的覆盖范围和先决条件。同一节点上的流量不会通过节点隧道加密，而工作负载 mTLS 是另一项独立功能。

   </details>

15. **哪个策略层用于匹配 HTTP 方法和路径？**

   - A) 仅匹配 L2 地址
   - B) L7 策略
   - C) 仅匹配 L3 CIDR
   - D) 传输加密

   <details>
   <summary>显示答案</summary>

   **答案：B) L7 策略**

   当前的 Cilium HTTP 策略可以检查这些字段；Kafka 主题规则已被移除。匹配标头不等于令牌身份验证。

   </details>

## 高级主题和用例

16. **以下哪项不是 ClusterMesh 的能力？**

   - A) 跨集群服务发现
   - B) 策略使用远端端点身份
   - C) 跨集群服务负载均衡
   - D) 共享持久存储

   <details>
   <summary>显示答案</summary>

   **答案：D) 共享持久存储**

   ClusterMesh 负责网络元数据和连通性。它不提供共享存储，也不会自动复制所有策略资源。

   </details>

17. **以下哪项对 Bandwidth Manager 的描述正确？**

   - A) 它只绘制带宽图表
   - B) 它会强制执行配置的每个 Pod 带宽限制
   - C) 它保证为每个 Pod 预留物理链路带宽
   - D) 它使用机器学习预测未来流量

   <details>
   <summary>显示答案</summary>

   **答案：B) 它会强制执行配置的每个 Pod 带宽限制**

   出站流量使用 EDT，入站流量使用 eBPF 令牌桶。限制按 Pod 设置，并存在已记录的出站 L7 和 kind 限制；这些限制不等于保证的容量预留。

   </details>

18. **Cilium Host Firewall 的作用范围是什么？**

   - A) 仅限容器到容器的 HTTP 流量
   - B) 仅限存储加密
   - C) 主机的网络流量
   - D) 外部 SaaS 授权

   <details>
   <summary>显示答案</summary>

   **答案：C) 主机的网络流量**

   Host Firewall 是针对节点/主机的网络策略，并非通用的运行时系统调用控制系统。

   </details>

19. **Egress Gateway 会如何处理匹配的出站流量？**

   - A) SNAT 为选定的、可预测的网关 IP
   - B) 始终保留原始 Pod 源 IP
   - C) 自动加密所有外部连接
   - D) 无需任何先决条件，就在每个云环境中创建一个公网 IP

   <details>
   <summary>显示答案</summary>

   **答案：A) SNAT 为选定的、可预测的网关 IP**

   必须预先配置网关 IP、接口和路由。新 Pod 可能会在策略生效前发送流量；此外还存在 ClusterMesh 和 CiliumEndpointSlice 不兼容的情况。

   </details>

20. **Cilium BGP Control Plane 会执行以下哪项操作？**

   - A) 将所有学习到的路由安装到本地 Linux 数据路径中
   - B) 向对等体通告选定的 Pod 或 Service 前缀
   - C) 为所有 Service 创建 DNS 记录
   - D) 分配外部路由器接口

   <details>
   <summary>显示答案</summary>

   **答案：B) 向对等体通告选定的 Pod 或 Service 前缀**

   BGP 通告与本地数据路径路由、地址分配和 DNS 相互独立。请验证外部路由器以及实际的正向/返回路径。

   </details>

## 性能和故障排查

21. **哪种机制可以在原生驱动钩子处处理受支持的外部 Service 转发？**

   - A) Grafana 仪表板
   - B) XDP 加速
   - C) DNS 搜索后缀
   - D) 更大的应用日志文件

   <details>
   <summary>显示答案</summary>

   **答案：B) XDP 加速**

   XDP 需要受支持的 NIC/驱动程序和路径。不能假设任意工作负载都能获得固定的延迟或吞吐量提升。

   </details>

22. **哪个独立的 Cilium CLI 命令会主动创建工作负载以测试连通性场景？**

   - A) `cilium status`
   - B) `cilium connectivity test`
   - C) `hubble status`
   - D) `kubectl get nodes`

   <details>
   <summary>显示答案</summary>

   **答案：B) `cilium connectivity test`**

   这是会创建资源并产生流量的主动测试，并非只读状态查询。请使用隔离的测试范围，并检查清理情况。

   </details>

23. **在所属的 Cilium agent 内，哪个命令可以检查某个端点的详细信息？**

   - A) `cilium endpoint list`
   - B) `cilium policy get`
   - C) `cilium-dbg endpoint get ENDPOINT_ID`
   - D) `cilium status --all-endpoints`

   <details>
   <summary>显示答案</summary>

   **答案：C) `cilium-dbg endpoint get ENDPOINT_ID`**

   请从该 agent 的端点列表中获取节点本地端点 ID。另一个 agent 上的 ID 不一定对应同一工作负载。

   </details>

24. **哪个 agent 本地命令会列出 map manager 已知的已打开 BPF map？**

   - A) `cilium-dbg map list`
   - B) `cilium bpf maps`
   - C) `cilium status --maps`
   - D) `cilium bpf map list`

   <details>
   <summary>显示答案</summary>

   **答案：A) `cilium-dbg map list`**

   这并不是内核中所有 BPF map 的清单。之前给出的 cilium bpf maps 并非有效命令。

   </details>

25. **哪个命令可以显示由 Cilium BPF 程序发出的本地事件？**

   - A) `cilium tcpdump`
   - B) `cilium capture`
   - C) `cilium-dbg monitor`
   - D) `cilium packet-capture`

   <details>
   <summary>显示答案</summary>

   **答案：C) `cilium-dbg monitor`**

   它会显示受支持的事件/跟踪类型。聚合、抑制和缓冲区都会影响可见性；它不能保证捕获每个数据包。

   </details>
