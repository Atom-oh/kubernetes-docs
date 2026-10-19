# Cilium 安全与可见性测验

> **审查基线**：Cilium 1.20.3；Hubble CLI 1.20.2。
> **上次审查时间**：2026 年 10 月 16 日。

[返回指南](../../../networking/cilium/06-security-visibility.md)

## 网络策略基础

1. **CiliumNetworkPolicy 如何扩展标准 Kubernetes NetworkPolicy？**

   - A) 它无法选择 Pod
   - B) 它可以添加受支持的 L7 协议规则
   - C) 它只保护节点
   - D) 它保证更低的延迟

   <details>
   <summary>显示答案</summary>

   **答案：B) 它可以添加受支持的 L7 协议规则**

   标准 NetworkPolicy 控制 L3/L4 连通性。Cilium 添加了 HTTP 和 DNS 策略等功能；选择哪种 API 并不能保证性能。

   </details>

2. **CiliumNetworkPolicy 使用哪个 API 版本？**

   - A) networking.k8s.io/v1
   - B) cilium.io/v2
   - C) policy.cilium.io/v1
   - D) network.cilium.io/v1

   <details>
   <summary>显示答案</summary>

   **答案：B) cilium.io/v2**

   该 API 组为 cilium.io，本章使用的策略 API 版本为 v2。

   </details>

3. **在带有命名空间的 CiliumNetworkPolicy 中，endpointSelector 会选择什么？**

   - A) 策略命名空间中匹配的端点
   - B) 所有 Kubernetes 节点
   - C) Prometheus 服务器
   - D) 仅限 LoadBalancer Service

   <details>
   <summary>显示答案</summary>

   **答案：A) 策略命名空间中匹配的端点**

   它用于标识受策略管理的端点。节点策略使用单独的集群范围 nodeSelector 机制。

   </details>

4. **对于 policyTypes: [Ingress] 的标准 NetworkPolicy，哪个值不包含任何 Ingress 允许规则？**

   - A) ingress: [{}]
   - B) ingress: []
   - C) ingress: [{from: [{}]}]
   - D) 允许所有源地址的规则

   <details>
   <summary>显示答案</summary>

   **答案：B) ingress: []**

   空列表不包含任何允许规则；空规则对象则允许所有 Ingress 流量。其他适用的允许策略仍然会叠加生效。

   </details>

5. **针对选定的 Pod，egress 策略控制哪个方向？**

   - A) 仅限入站连接
   - B) 出站连接
   - C) 仅限进程内部的流量
   - D) 仅限 API 服务器的响应

   <details>
   <summary>显示答案</summary>

   **答案：B) 出站连接**

   Egress 控制出站连通性。处于隔离状态的 Pod 需要明确允许访问其依赖项，例如实际使用的 DNS 解析器。

   </details>

## L7 策略

6. **以下哪项不是 Cilium HTTP 策略中的请求匹配字段？**

   - A) Path
   - B) Method
   - C) Headers
   - D) 响应延迟

   <details>
   <summary>显示答案</summary>

   **答案：D) 响应延迟**

   HTTP 策略会匹配受支持的请求属性。能够观察响应持续时间，并不意味着延迟是 HTTP 允许规则的字段。

   </details>

7. **示例中的 toFQDNs 策略需要什么才能学习 DNS 答案？**

   - A) 仅需 TCP 443 规则
   - B) 仅需任意外部 IP
   - C) 可访问的解析器和匹配的 DNS 代理规则
   - D) Kafka 主题规则

   <details>
   <summary>显示答案</summary>

   **答案：C) 可访问的解析器和匹配的 DNS 代理规则**

   允许 DNS 流量/通过代理观察 DNS，以及随后允许访问目标 IP，是两个不同的环节。该示例涵盖了到已验证解析器端点的 UDP 和 TCP DNS 流量。

   </details>

8. **DNS matchPattern 提供什么功能？**

   - A) 端口分配
   - B) 域名通配符匹配
   - C) JWT 签名验证
   - D) 自动识别恶意域名的信誉

   <details>
   <summary>显示答案</summary>

   **答案：B) 域名通配符匹配**

   它使用受支持的通配符语法匹配查询/域名，但不会获取威胁情报源。

   </details>

9. **此处讨论的 HTTP 规则由哪个代理实现？**

   - A) kube-proxy
   - B) Envoy
   - C) Prometheus
   - D) Hubble Relay

   <details>
   <summary>显示答案</summary>

   **答案：B) Envoy**

   Cilium 集成 Envoy 来实现 HTTP 策略。DNS 策略使用 DNS 代理，因此不应将所有 L7 规则都描述为 Envoy 规则。

   </details>

10. **以下哪项曾是 Cilium 的 L7 策略功能，但已不在当前 API 中？**

   - A) HTTP 方法匹配
   - B) HTTP 路径匹配
   - C) Kafka 主题规则
   - D) DNS 名称规则

   <details>
   <summary>显示答案</summary>

   **答案：C) Kafka 主题规则**

   Kafka L7 策略已移除。不要将旧的 kafka 规则复制到当前的 CiliumNetworkPolicy 资源中。

   </details>

## 加密与安全

11. **哪一组选项是 Cilium 节点传输加密的两种替代模式？**

   - A) IPsec 和 WireGuard
   - B) HTTP 和 DNS
   - C) Relay 和 Grafana
   - D) SYN 和 ACK

   <details>
   <summary>显示答案</summary>

   **答案：A) IPsec 和 WireGuard**

   请选择所需的模式及其前提条件。SPIRE 双向身份验证和 Beta 版 ztunnel 工作负载 mTLS 是范围不同的独立功能。

   </details>

12. **本章默认的 WireGuard 节点隧道配置涵盖什么流量？**

   - A) 所有数据包，包括任意外部流量
   - B) 跨节点传输的、由 Cilium 管理且受支持的 Pod 流量
   - C) 所有经过隧道的同节点 Pod 流量
   - D) 所有主机流量，无一例外

   <details>
   <summary>显示答案</summary>

   **答案：B) 跨节点传输的、由 Cilium 管理且受支持的 Pod 流量**

   同节点流量不会经过这些节点隧道。节点间加密是单独的 Beta 选项，并且不包括控制平面流量；仍可能需要应用 TLS。

   </details>

13. **Cilium Host Firewall 的用途是什么？**

   - A) 仅保护浏览器 JavaScript
   - B) 保护主机的网络流量
   - C) 自动保护所有容器系统调用
   - D) 保护 Grafana 密码数据库

   <details>
   <summary>显示答案</summary>

   **答案：B) 保护主机的网络流量**

   主机策略是一种网络控制。运行时进程/系统调用强制执行属于单独的机制，例如已配置的 Tetragon 策略；还必须检查加密兼容性。

   </details>

14. **匹配 Authorization 标头能否验证其持有者的身份？**

   - A) 能，任何存在的标头都是经过验证的 JWT
   - B) 能，看起来像正则表达式的值可以验证签名
   - C) 不能；标头匹配不会验证令牌
   - D) 能，只要 HTTP 使用端口 8443

   <details>
   <summary>显示答案</summary>

   **答案：C) 不能；标头匹配不会验证令牌**

   应使用实际的身份验证/授权逻辑。带值的 headers 字符串会进行字面匹配，而 TLS 端口号不会解密有效载荷。

   </details>

15. **Cilium 安全身份主要由什么决定？**

   - A) 永远唯一且有保证的 Pod IP
   - B) 与安全相关的标签集
   - C) 用户的浏览器 Cookie
   - D) 最近观察到的 HTTP 响应

   <details>
   <summary>显示答案</summary>

   **答案：B) 与安全相关的标签集**

   共享与安全相关标签的端点可以共用一个身份。仅基于身份的策略不能提供最终用户身份验证或流量加密。

   </details>

## 可见性与监控

16. **Hubble 的主要作用是什么？**

   - A) 网络流可观测性
   - B) 容器镜像部署
   - C) 无需规则的完整 WAF
   - D) 自动隔离每个可疑 Pod

   <details>
   <summary>显示答案</summary>

   **答案：A) 网络流可观测性**

   Hubble 会公开流元数据、判定结果和受支持协议的观测信息。检测规则和响应集成需要单独配置。

   </details>

17. **以下哪项是 Hubble UI 的功能？**

   - A) 轮换应用凭据
   - B) Service 依赖关系图和流量探索
   - C) 自动发送 Slack 事件通知
   - D) 安装运行时系统调用策略

   <details>
   <summary>显示答案</summary>

   **答案：B) Service 依赖关系图和流量探索**

   该 UI 通过 Relay 可视化网络观测信息。它不是通知、部署或运行时策略控制器。

   </details>

18. **以下哪个命令会跟踪任一端点匹配前端 Pod 的流事件？**

   - A) `hubble observe --pod cilium-security-demo/frontend --follow`
   - B) `hubble watch --pod frontend`
   - C) `cilium hubble status`
   - D) `hubble observe --pod app=frontend`

   <details>
   <summary>显示答案</summary>

   **答案：A) `hubble observe --pod cilium-security-demo/frontend --follow`**

   使用带命名空间的 Pod 名称，并使用 --follow 获取流式输出。Pod 名称不是标签选择器；方向和标签过滤器是单独的标志。

   </details>

19. **示例中的 Hubble 指标插件不提供以下哪项？**

   - A) HTTP 响应状态计数
   - B) TCP 标志计数
   - C) 观测到的丢弃计数
   - D) 容器 CPU 使用量

   <details>
   <summary>显示答案</summary>

   **答案：D) 容器 CPU 使用量**

   这些插件会观测网络/代理事件。TCP 插件不提供通用的并发连接数或 RTT 指标，而且必须考虑观测缺失/丢失的情况。

   </details>

20. **安装 Prometheus Operator 后，要通过 ServiceMonitor 抓取 Hubble 指标，还需要什么？**

   - A) 仅导入 Grafana 仪表板
   - B) 一个静态公共目标 hubble-metrics.cilium.io:9091
   - C) 启用指标，并由 Prometheus 选中 ServiceMonitor
   - D) 仅创建一个无关的 ConfigMap

   <details>
   <summary>显示答案</summary>

   **答案：C) 启用指标，并由 Prometheus 选中 ServiceMonitor**

   chart 的无头 Service 会公开名为 hubble-metrics 的端口，通常为 9965。Prometheus 的命名空间/标签选择器和端点可达性都必须匹配。

   </details>
