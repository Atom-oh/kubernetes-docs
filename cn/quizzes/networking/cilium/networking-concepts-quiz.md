# Cilium 网络概念测验

> **支持版本**: Cilium 1.17
> **最后更新**: February 22, 2026

## OSI 模型和基本概念

1. **Cilium 主要在哪个 OSI 模型层级运行？**
   - A) L2（数据链路层）
   - B) L3/L4（网络/传输层）
   - C) L7（应用层）
   - D) 从 L3 到 L7 的所有层级

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) 从 L3 到 L7 的所有层级</p>
   <p><strong>解释</strong>: Cilium 不仅在 L3/L4（IP 地址、端口）层提供网络和安全功能，还可支持到 L7（HTTP、gRPC、Kafka 等）层。</p>
   </details>

2. **以下哪项是 L2（数据链路层）地址？**
   - A) IP 地址
   - B) MAC 地址
   - C) 端口号
   - D) URL

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) MAC 地址</p>
   <p><strong>解释</strong>: MAC（媒体访问控制）地址是网络接口卡的唯一标识符，并在 L2 层使用。</p>
   </details>

3. **以下哪项是 L3（网络层）协议？**
   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) IP</p>
   <p><strong>解释</strong>: IP（互联网协议）是负责在网络层（L3）进行数据包路由的协议。</p>
   </details>

## 容器网络

4. **Cilium 的默认网络模型是什么？**
   - A) Bridge 模式
   - B) Overlay 网络
   - C) Underlay 网络
   - D) Host 网络

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Overlay 网络</p>
   <p><strong>解释</strong>: Cilium 默认使用基于 VXLAN 或 Geneve 的 Overlay 网络模型。</p>
   </details>

5. **Cilium 使用的默认 Overlay 协议是什么？**
   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) VXLAN</p>
   <p><strong>解释</strong>: Cilium 默认使用 VXLAN（虚拟可扩展局域网）协议来配置 Overlay 网络。</p>
   </details>

6. **Cilium 的 Direct Routing 模式的主要优势是什么？**
   - A) 更高的安全性
   - B) 更好的兼容性
   - C) 更低的延迟和更高的吞吐量
   - D) 更容易设置

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 更低的延迟和更高的吞吐量</p>
   <p><strong>解释</strong>: Direct Routing 模式不使用 Overlay 封装，因此可提供更低的延迟和更高的吞吐量。</p>
   </details>

## IP 地址管理 (IPAM)

7. **Cilium 的默认 IPAM 模式是什么？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) 基于 CRD
   - D) AWS ENI

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Cluster Scope</p>
   <p><strong>解释</strong>: Cilium 的默认 IPAM 模式是 Cluster Scope，它会在整个集群中集中分配 IP 地址。</p>
   </details>

8. **在 AWS EKS 上使用 Cilium 时，推荐使用哪种 IPAM 模式？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) 基于 CRD

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) AWS ENI</p>
   <p><strong>解释</strong>: 在 AWS EKS 上，建议使用 AWS ENI IPAM 模式，直接将 VPC IP 地址分配给 Pod。</p>
   </details>

9. **Cilium 的 IPAM `PodCIDR` 模式利用了哪个 Kubernetes 功能？**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>解释</strong>: Cilium 的 PodCIDR IPAM 模式利用 Kubernetes 为每个节点分配的 NodeSpec.PodCIDR 字段。</p>
   </details>

## Service 和负载均衡

10. **Cilium 的 kube-proxy 替代模式不提供以下哪项功能？**
    - A) ClusterIP Service 支持
    - B) NodePort Service 支持
    - C) LoadBalancer Service 支持
    - D) Service mesh 功能

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) Service mesh 功能</p>
    <p><strong>解释</strong>: Cilium 的 kube-proxy 替代模式支持基本 Kubernetes Service 类型，但 Service mesh 功能通过独立的 Cilium Service Mesh 功能提供。</p>
    </details>

11. **Cilium 使用哪些算法进行 Service 负载均衡？**
    - A) 轮询
    - B) 最少连接数
    - C) IP 哈希
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>解释</strong>: Cilium 支持多种负载均衡算法，包括轮询、最少连接数和 IP 哈希。</p>
    </details>

12. **Cilium 的 Global Service 功能实现了什么？**
    - A) 全球分布式 Service 访问
    - B) 跨多个集群的 Service 负载均衡
    - C) 全局 IP 地址分配
    - D) 全局网络策略应用

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 跨多个集群的 Service 负载均衡</p>
    <p><strong>解释</strong>: Cilium 的 Global Service 功能通过 Cluster Mesh 为多个集群中的同一 Service 实现负载均衡。</p>
    </details>

## 网络策略

13. **Cilium 网络策略中的 `toCIDR` 规则允许什么？**
    - A) 发往特定 IP 地址范围的流量
    - B) 发往特定域名的流量
    - C) 发往特定 Service 的流量
    - D) 发往特定端口的流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) 发往特定 IP 地址范围的流量</p>
    <p><strong>解释</strong>: `toCIDR` 规则用于允许发往特定 IP 地址范围（采用 CIDR 表示法）的流量。</p>
    </details>

14. **Cilium 网络策略 `toEntities` 规则中的 `world` 实体表示什么？**
    - A) 集群中的所有内部端点
    - B) 所有外部网络
    - C) 所有节点
    - D) 所有命名空间

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 所有外部网络</p>
    <p><strong>解释</strong>: `world` 实体表示集群外部的所有网络。</p>
    </details>

15. **Cilium 的 L7 策略不支持以下哪种协议？**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) SMTP</p>
    <p><strong>解释</strong>: Cilium 支持 HTTP、gRPC 和 Kafka 等 L7 协议，但默认不支持 SMTP。</p>
    </details>

## 高级网络概念

16. **Cilium 的 Transparent Encryption 功能可以使用哪些协议？**
    - A) IPsec
    - B) WireGuard
    - C) A 和 B 两者
    - D) TLS

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) A 和 B 两者</p>
    <p><strong>解释</strong>: Cilium 可使用 IPsec 和 WireGuard 对节点之间的流量进行加密。</p>
    </details>

17. **Cilium 的 Multi-cluster 功能使用什么技术？**
    - A) Cluster Federation
    - B) Cluster Mesh
    - C) Multi-cluster Networking
    - D) Global Cluster

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) Cluster Mesh</p>
    <p><strong>解释</strong>: Cilium 使用 Cluster Mesh 技术提供多个 Kubernetes 集群之间的连接能力。</p>
    </details>

18. **通过 Cilium 的 BGP 支持可以实现什么？**
    - A) 与外部路由器交换路由
    - B) 为 LoadBalancer Service 通告外部 IP
    - C) 集群之间的直接路由
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>解释</strong>: Cilium 的 BGP 支持可实现与外部路由器交换路由、为 LoadBalancer Service 通告外部 IP，以及集群之间的直接路由。</p>
    </details>

19. **Cilium 的 Egress Gateway 功能的主要目的是什么？**
    - A) 保留外部流量的源 IP 地址
    - B) 更改外部流量的目标 IP 地址
    - C) 加密外部流量
    - D) 阻止外部流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) 保留外部流量的源 IP 地址</p>
    <p><strong>解释</strong>: Egress Gateway 会将从 Pod 发往集群外部的流量 SNAT 为特定 IP，从而提供一致的源 IP。</p>
    </details>

20. **关于 Cilium 的 Host Routing 功能，以下哪项说法正确？**
    - A) Host 网络与 Pod 网络之间的路由
    - B) Host 之间的直接路由
    - C) Host 网络接口保护
    - D) 基于 Host 的负载均衡

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) Host 之间的直接路由</p>
    <p><strong>解释</strong>: Cilium 的 Host Routing 可在不使用 Overlay 网络的情况下提供 Host 之间的直接路由。</p>
    </details>
