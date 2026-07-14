# Cilium 高级测验

> **支持的版本**: Cilium 1.17
> **最后更新**: February 22, 2026

## eBPF 技术

1. **eBPF 程序在何处运行？**
   - A) 用户空间
   - B) 内核空间
   - C) 容器内部
   - D) 虚拟机内部

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 内核空间</p>
   <p><strong>说明</strong>: eBPF 程序在 Linux 内核中安全运行，并且可以扩展和修改内核功能。</p>
   </details>

2. **哪种机制确保 eBPF 程序的安全性？**
   - A) 虚拟化
   - B) 容器化
   - C) 静态验证器
   - D) 加密

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 静态验证器</p>
   <p><strong>说明</strong>: eBPF 验证器会在程序加载前检查其安全性，以防止无限循环或内核崩溃。</p>
   </details>

3. **以下哪项不是在 Cilium 中使用 eBPF 的主要优势？**
   - A) 无需内核模块即可实现网络功能
   - B) 高性能和低开销
   - C) 细粒度网络策略执行
   - D) 必须使用硬件加速

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) 必须使用硬件加速</p>
   <p><strong>说明</strong>: eBPF 无需硬件加速，便可基于软件提供高性能。</p>
   </details>

## 网络模型

4. **Cilium 不支持哪种数据路径模式？**
   - A) VXLAN
   - B) Geneve
   - C) 直接路由
   - D) MPLS

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) MPLS</p>
   <p><strong>说明</strong>: Cilium 支持 VXLAN、Geneve 和直接路由，但不支持 MPLS。</p>
   </details>

5. **Cilium 在 kube-proxy 替代模式中使用什么技术？**
   - A) iptables
   - B) IPVS
   - C) 基于 eBPF 的 XDP
   - D) netfilter

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 基于 eBPF 的 XDP</p>
   <p><strong>说明</strong>: Cilium 使用 eBPF 和 XDP (eXpress Data Path) 替代 kube-proxy，并提供更高性能。</p>
   </details>

6. **在 Cilium 的网络模型中，哪个功能会跟踪 Pod 到 Pod 通信期间的数据包路径？**
   - A) tcpdump
   - B) Hubble 流量监控
   - C) Wireshark
   - D) Prometheus

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Hubble 流量监控</p>
   <p><strong>说明</strong>: Hubble 是 Cilium 的网络流量监控工具，可实时跟踪并可视化 Pod 到 Pod 通信。</p>
   </details>

## IPAM 和网络策略

7. **Cilium 中哪种 IPAM (IP Address Management) 模式可与 AWS EKS 集成？**
   - A) Cluster Pool
   - B) Kubernetes Host Scope
   - C) AWS ENI
   - D) 基于 CRD

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) AWS ENI</p>
   <p><strong>说明</strong>: Cilium 通过 AWS ENI (Elastic Network Interface) 模式与 EKS 集成，从而将 VPC IP 地址直接分配给 Pod。</p>
   </details>

8. **Cilium 网络策略中的 'toFQDNs' 规则允许什么？**
   - A) 到特定 IP 地址的流量
   - B) 到特定端口的流量
   - C) 到特定域名的流量
   - D) 特定协议的流量

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 到特定域名的流量</p>
   <p><strong>说明</strong>: toFQDNs 规则允许到特定域名 (FQDN) 的流量，Cilium 会监控 DNS 查询，以动态允许这些域名对应的 IP 地址。</p>
   </details>

9. **Cilium CiliumNetworkPolicy 不支持哪个选择器？**
   - A) endpointSelector
   - B) nodeSelector
   - C) namespaceSelector
   - D) serviceSelector

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) serviceSelector</p>
   <p><strong>说明</strong>: Cilium 支持 endpointSelector、nodeSelector 和 namespaceSelector，但不直接支持 serviceSelector。</p>
   </details>

## L2-L7 网络

10. **Cilium 的 L7 策略无法针对 HTTP 请求的哪项属性进行过滤？**
    - A) 路径
    - B) 方法
    - C) 标头
    - D) 响应时间

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 响应时间</p>
    <p><strong>说明</strong>: Cilium 的 L7 策略可以过滤路径、方法和标头等 HTTP 请求属性，但响应时间不是过滤目标。</p>
    </details>

11. **Cilium 的 Service Mesh 功能不提供什么？**
    - A) 双向 TLS (mTLS)
    - B) 流量拆分
    - C) Service 发现
    - D) 用户认证

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 用户认证</p>
    <p><strong>说明</strong>: Cilium Service Mesh 提供双向 TLS、流量拆分和 Service 发现，但用户认证通常由独立的认证系统处理。</p>
    </details>

12. **Cilium 的 Envoy 集成提供哪些功能？**
    - A) L7 负载均衡
    - B) L7 可观测性
    - C) L7 策略执行
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>说明</strong>: Cilium 与 Envoy 代理集成，以提供 L7 负载均衡、可观测性和策略执行。</p>
    </details>

## 安全性和可观测性

13. **Hubble UI 不提供哪个功能？**
    - A) Service 依赖关系图
    - B) 网络流量可视化
    - C) 策略违规告警
    - D) 代码部署管理

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 代码部署管理</p>
    <p><strong>说明</strong>: Hubble UI 提供 Service 依赖关系图、网络流量可视化和策略违规告警，但不提供代码部署管理。</p>
    </details>

14. **Cilium 可使用哪些协议进行网络流量加密？**
    - A) IPsec 和 WireGuard
    - B) TLS 和 SSH
    - C) SSL 和 HTTPS
    - D) DTLS 和 QUIC

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) IPsec 和 WireGuard</p>
    <p><strong>说明</strong>: Cilium 可以使用 IPsec 和 WireGuard 协议加密节点间网络流量。</p>
    </details>

15. **以下描述与哪项 Cilium 安全功能相符？“基于特定应用层协议的特定字段或模式过滤流量”**
    - A) 网络策略
    - B) L7 策略
    - C) 加密
    - D) 入侵检测

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) L7 策略</p>
    <p><strong>说明</strong>: L7（应用层）策略可以基于 HTTP、gRPC 和 Kafka 等协议中的特定字段或模式过滤流量。</p>
    </details>

## 高级主题和实际应用场景

16. **以下哪项不是 Cilium Cluster Mesh 的主要功能？**
    - A) 跨集群 Service 发现
    - B) 跨集群网络策略
    - C) 跨集群负载均衡
    - D) 跨集群存储共享

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 跨集群存储共享</p>
    <p><strong>说明</strong>: Cilium Cluster Mesh 提供跨集群 Service 发现、网络策略和负载均衡，但不提供存储共享。</p>
    </details>

17. **Cilium 的 Bandwidth Manager 功能提供什么？**
    - A) 网络带宽监控
    - B) 网络带宽限制和 QoS
    - C) 网络带宽优化
    - D) 网络带宽预测

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 网络带宽限制和 QoS</p>
    <p><strong>说明</strong>: Cilium 的 Bandwidth Manager 使用 eBPF 提供按 Pod 设置的网络带宽限制和 QoS (Quality of Service)。</p>
    </details>

18. **Cilium 的 Host Firewall 功能保护什么？**
    - A) 仅容器到容器通信
    - B) 仅节点到节点通信
    - C) 主机自身的网络接口
    - D) 外部云服务

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) 主机自身的网络接口</p>
    <p><strong>说明</strong>: Cilium 的 Host Firewall 保护主机自身的网络接口，从而增强主机级安全性。</p>
    </details>

19. **Cilium 的 Egress Gateway 功能的主要用途是什么？**
    - A) 保留外部流量的源 IP 地址
    - B) 更改外部流量的目标 IP 地址
    - C) 加密外部流量
    - D) 阻止外部流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) 保留外部流量的源 IP 地址</p>
    <p><strong>说明</strong>: Cilium 的 Egress Gateway 会将从 Pod 发往集群外部的出站流量 SNAT 为特定 IP，从而提供一致的源 IP。</p>
    </details>

20. **通过 Cilium 的 BGP 支持无法实现什么？**
    - A) 与外部路由器交换路由
    - B) 为 LoadBalancer Service 通告外部 IP
    - C) 集群之间的直接路由
    - D) 自动创建 DNS 记录

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 自动创建 DNS 记录</p>
    <p><strong>说明</strong>: Cilium 的 BGP 支持提供与外部路由器交换路由、为 LoadBalancer Service 通告外部 IP 以及集群之间的直接路由，但不提供自动创建 DNS 记录的功能。</p>
    </details>

## 性能和故障排除

21. **哪项 Cilium 性能优化技术可以显著降低数据包处理延迟？**
    - A) TCP BBR
    - B) XDP (eXpress Data Path)
    - C) DPDK
    - D) TSO (TCP Segmentation Offload)

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) XDP (eXpress Data Path)</p>
    <p><strong>说明</strong>: XDP 在网络驱动程序层处理数据包，绕过内核网络栈，从而显著降低延迟。</p>
    </details>

22. **在 Cilium 中诊断网络连接问题的命令是什么？**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium monitor`
    - D) `cilium endpoint list`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) `cilium connectivity test`</p>
    <p><strong>说明</strong>: `cilium connectivity test` 命令会测试集群内的各种网络连接场景，以诊断问题。</p>
    </details>

23. **在 Cilium 中检查特定 Pod 的网络策略状态的命令是什么？**
    - A) `cilium endpoint list`
    - B) `cilium policy get`
    - C) `cilium endpoint get <endpoint-id>`
    - D) `cilium status --all-endpoints`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) <code>cilium endpoint get &lt;endpoint-id&gt;</code></p>
    <p><strong>说明</strong>: <code>cilium endpoint get &lt;endpoint-id&gt;</code> 命令会显示特定 endpoint (Pod) 的详细信息和已应用的网络策略状态。</p>
    </details>

24. **在 Cilium 中检查 BPF map 状态的命令是什么？**
    - A) `cilium map list`
    - B) `cilium bpf maps`
    - C) `cilium status --maps`
    - D) `cilium bpf map list`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) `cilium bpf maps`</p>
    <p><strong>说明</strong>: `cilium bpf maps` 命令会显示 Cilium 使用的所有 BPF map 的列表和状态。</p>
    </details>

25. **在 Cilium 中用于网络数据包捕获和分析的命令是什么？**
    - A) `cilium tcpdump`
    - B) `cilium capture`
    - C) `cilium monitor`
    - D) `cilium packet-capture`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) `cilium monitor`</p>
    <p><strong>说明</strong>: `cilium monitor` 命令可以实时捕获和分析通过 Cilium eBPF 数据路径的数据包。</p>
    </details>
