# Cilium 安全性与可观测性测验

> **支持的版本**: Cilium 1.17
> **最后更新**: February 22, 2026

## 网络策略基础

1. **Kubernetes NetworkPolicy 与 Cilium NetworkPolicy 的主要区别是什么？**
   - A) Cilium NetworkPolicy 不支持 L7 策略
   - B) Kubernetes NetworkPolicy 不支持 L7 策略
   - C) Cilium NetworkPolicy 只能应用于特定 Node
   - D) Kubernetes NetworkPolicy 提供更高的性能

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Kubernetes NetworkPolicy 不支持 L7 策略</p>
   <p><strong>说明</strong>: Kubernetes NetworkPolicy 仅支持 L3/L4 层级策略，而 Cilium NetworkPolicy 支持从 L3 到 L7 的更广泛策略。</p>
   </details>

2. **Cilium NetworkPolicy 的 API group 是什么？**
   - A) networking.k8s.io
   - B) cilium.io
   - C) policy.cilium.io
   - D) network.cilium.io

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) cilium.io</p>
   <p><strong>说明</strong>: Cilium NetworkPolicy 使用 cilium.io API group。</p>
   </details>

3. **Cilium NetworkPolicy 中的 'endpointSelector' 的作用是什么？**
   - A) 选择策略适用的目标 Pod
   - B) 选择策略适用的目标 Node
   - C) 选择策略适用的目标 namespace
   - D) 选择策略适用的目标 Service

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 选择策略适用的目标 Pod</p>
   <p><strong>说明</strong>: endpointSelector 用于选择策略适用的目标 Pod（endpoint）。</p>
   </details>

4. **Cilium NetworkPolicy 中的 'ingress' 规则控制什么？**
   - A) 进入所选 Pod 的流量
   - B) 从所选 Pod 发出的流量
   - C) 所选 Pod 内部的流量
   - D) 发往 cluster 外部的流量

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 进入所选 Pod 的流量</p>
   <p><strong>说明</strong>: Ingress 规则控制进入所选 Pod 的流量。</p>
   </details>

5. **Cilium NetworkPolicy 中的 'egress' 规则控制什么？**
   - A) 进入所选 Pod 的流量
   - B) 从所选 Pod 发出的流量
   - C) 所选 Pod 内部的流量
   - D) 从 cluster 外部发出的流量

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 从所选 Pod 发出的流量</p>
   <p><strong>说明</strong>: Egress 规则控制从所选 Pod 发出的流量。</p>
   </details>

## L7 策略

6. **在 Cilium 的 L7 HTTP 策略中，哪个属性无法被过滤？**
   - A) Path
   - B) Method
   - C) Headers
   - D) Response Time

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) Response Time</p>
   <p><strong>说明</strong>: Cilium 的 L7 HTTP 策略可以过滤 path、method 和 headers 等 HTTP request 属性，但 response time 不是过滤目标。</p>
   </details>

7. **在 Cilium 的 L7 Kafka 策略中，哪个属性可以被过滤？**
   - A) Topic
   - B) Partition
   - C) Offset
   - D) 以上全部

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) Topic</p>
   <p><strong>说明</strong>: Cilium 的 L7 Kafka 策略主要可以基于 topic、API key 和类似属性进行过滤。</p>
   </details>

8. **Cilium 的 L7 DNS 策略中的 'matchPattern' 规则允许什么？**
   - A) 精确域名匹配
   - B) 使用通配符的域名模式匹配
   - C) IP address 匹配
   - D) Port number 匹配

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 使用通配符的域名模式匹配</p>
   <p><strong>说明</strong>: matchPattern 规则可以匹配包含通配符 (*) 的域名模式。示例：*.example.com</p>
   </details>

9. **应用 Cilium 的 L7 策略需要哪个组件？**
   - A) kube-proxy
   - B) Envoy proxy
   - C) NGINX ingress controller
   - D) HAProxy

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Envoy proxy</p>
   <p><strong>说明</strong>: Cilium 使用 Envoy proxy 应用 L7 策略。</p>
   </details>

10. **Cilium 的 L7 策略不支持以下哪种协议？**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) SMTP</p>
    <p><strong>说明</strong>: Cilium 支持 HTTP、gRPC 和 Kafka 等 L7 协议，但默认不支持 SMTP。</p>
    </details>

## 加密与安全性

11. **Cilium 可以使用哪些协议对网络流量进行加密？**
    - A) IPsec
    - B) WireGuard
    - C) A 和 B 均可
    - D) TLS

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) A 和 B 均可</p>
    <p><strong>说明</strong>: Cilium 可以同时使用 IPsec 和 WireGuard 加密 Node 间流量。</p>
    </details>

12. **Cilium 的加密功能保护什么流量？**
    - A) 仅 Node 间流量
    - B) 仅 Pod 间流量
    - C) 仅 Node 到 Pod 的流量
    - D) 所有 cluster 流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 仅 Pod 间流量</p>
    <p><strong>说明</strong>: Cilium 的加密功能主要保护 Pod 间流量。</p>
    </details>

13. **Cilium 的 Host Firewall 功能保护什么？**
    - A) Pod 网络接口
    - B) Host 网络接口
    - C) Service endpoint
    - D) Container runtime

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) Host 网络接口</p>
    <p><strong>说明</strong>: Cilium 的 Host Firewall 保护 Host 自身的网络接口，从而增强 Host 层级的安全性。</p>
    </details>

14. **以下描述对应哪项 Cilium 安全功能？“基于特定应用层协议的特定字段或模式过滤流量”**
    - A) 网络策略
    - B) L7 策略
    - C) 加密
    - D) 入侵检测

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) L7 策略</p>
    <p><strong>说明</strong>: L7（应用层）策略可以基于 HTTP、gRPC 和 Kafka 等协议中的特定字段或模式过滤流量。</p>
    </details>

15. **Cilium 基于 Identity 的安全模型基于什么？**
    - A) Pod 名称
    - B) Node 名称
    - C) Labels
    - D) IP address

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) Labels</p>
    <p><strong>说明</strong>: Cilium 的 Identity 基于 Pod labels，即使 IP address 发生变化，也能应用一致的安全策略。</p>
    </details>

## 可观测性与监控

16. **Hubble 是什么？**
    - A) Cilium 的网络可观测性工具
    - B) Cilium 的 load balancer
    - C) Cilium 的加密协议
    - D) Cilium 的 DNS server

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) Cilium 的网络可观测性工具</p>
    <p><strong>说明</strong>: Hubble 是 Cilium 的网络可观测性工具，可以基于 eBPF 观察和分析网络流。</p>
    </details>

17. **Hubble UI 不提供以下哪项功能？**
    - A) Service 依赖关系图
    - B) 网络流可视化
    - C) 策略违规告警
    - D) 代码 Deployment 管理

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 代码 Deployment 管理</p>
    <p><strong>说明</strong>: Hubble UI 提供 Service 依赖关系图、网络流可视化和策略违规告警，但不提供代码 Deployment 管理。</p>
    </details>

18. **使用 Hubble CLI 观察特定 Pod 网络流的命令是什么？**
    - A) `hubble observe --pod <pod-name>`
    - B) `hubble watch --pod <pod-name>`
    - C) `hubble monitor --pod <pod-name>`
    - D) `hubble inspect --pod <pod-name>`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) <code>hubble observe --pod &lt;pod-name&gt;</code></p>
    <p><strong>说明</strong>: <code>hubble observe --pod &lt;pod-name&gt;</code> 命令可以实时观察特定 Pod 的网络流。</p>
    </details>

19. **Hubble 不收集以下哪项指标？**
    - A) HTTP status codes
    - B) TCP connection status
    - C) Dropped packet count
    - D) Container CPU usage

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) Container CPU usage</p>
    <p><strong>说明</strong>: Hubble 收集与网络相关的指标（HTTP status codes、TCP connection status、dropped packet count 等），但不收集 Container CPU usage 等系统指标。</p>
    </details>

20. **如何将 Cilium 与 Prometheus 集成？**
    - A) 向 Cilium Operator 添加 Prometheus annotations
    - B) 在 Prometheus server 上安装 Cilium plugin
    - C) 为 Cilium 创建 ServiceMonitor resource
    - D) 将 Cilium dashboard 导入 Prometheus

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) 为 Cilium 创建 ServiceMonitor resource</p>
    <p><strong>说明</strong>: 使用 Prometheus Operator 时，可以通过为 Cilium 创建 ServiceMonitor resource 来收集 Cilium metrics。</p>
    </details>
