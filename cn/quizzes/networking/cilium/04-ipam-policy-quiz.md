# Cilium IPAM 和网络策略测验

> **支持的版本**: Cilium 1.17
> **最后更新**: February 22, 2026

## IPAM（IP 地址管理）

1. **Cilium 的默认 IPAM 模式是什么？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Cluster Scope</p>
   <p><strong>说明</strong>: Cilium 的默认 IPAM 模式是 Cluster Scope，它会在整个集群中集中分配 IP 地址。</p>
   </details>

2. **哪种 Cilium IPAM 模式使每个节点从其自身的 CIDR 范围分配 IP？**
   - A) Cluster Scope
   - B) Kubernetes Host Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) Kubernetes Host Scope</p>
   <p><strong>说明</strong>: 在 Kubernetes Host Scope IPAM 模式中，每个节点从其自身的 CIDR 范围分配 IP 地址。</p>
   </details>

3. **在 AWS EKS 上使用 Cilium 时，推荐的 IPAM 模式是什么？**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) AWS ENI</p>
   <p><strong>说明</strong>: 在 AWS EKS 上，建议使用 AWS ENI IPAM 模式，直接为 Pod 分配 VPC IP 地址。</p>
   </details>

4. **Cilium 的“PodCIDR”IPAM 模式使用了哪项 Kubernetes 功能？**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>说明</strong>: Cilium 的 PodCIDR IPAM 模式使用 Kubernetes 分配给每个节点的 NodeSpec.PodCIDR 字段。</p>
   </details>

5. **使用什么命令检查 Cilium 的 IPAM 配置？**
   - A) `cilium status --ipam`
   - B) `cilium ipam`
   - C) `cilium config get ipam`
   - D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) `kubectl -n kube-system get configmap cilium-config -o yaml | grep -E 'ipam|allocator'`</p>
   <p><strong>说明</strong>: Cilium 的 IPAM 配置存储在 cilium-config ConfigMap 中，可以使用此命令验证。</p>
   </details>

## Network Policy 基础

6. **Cilium NetworkPolicy 的 API 版本是什么？**
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) cilium.io/v2</p>
   <p><strong>说明</strong>: Cilium NetworkPolicy 使用 cilium.io/v2 API 版本。</p>
   </details>

7. **Cilium NetworkPolicy 中“endpointSelector”的作用是什么？**
   - A) 选择要应用策略的目标 Pod
   - B) 选择要应用策略的目标节点
   - C) 选择要应用策略的目标命名空间
   - D) 选择要应用策略的目标 Service

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 选择要应用策略的目标 Pod</p>
   <p><strong>说明</strong>: endpointSelector 用于选择策略适用的目标 Pod（端点）。</p>
   </details>

8. **Cilium NetworkPolicy 中的“ingress”规则控制什么？**
   - A) 进入所选 Pod 的流量
   - B) 从所选 Pod 发出的流量
   - C) 所选 Pod 内部的流量
   - D) 到集群外部的流量

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 进入所选 Pod 的流量</p>
   <p><strong>说明</strong>: Ingress 规则控制进入所选 Pod 的流量。</p>
   </details>

9. **Cilium NetworkPolicy 中的“egress”规则控制什么？**
   - A) 进入所选 Pod 的流量
   - B) 从所选 Pod 发出的流量
   - C) 所选 Pod 内部的流量
   - D) 来自集群外部的流量

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 从所选 Pod 发出的流量</p>
   <p><strong>说明</strong>: Egress 规则控制从所选 Pod 发出的流量。</p>
   </details>

10. **Cilium NetworkPolicy 中“labels”字段的作用是什么？**
    - A) 选择要应用策略的 Pod
    - B) 策略本身的标识符
    - C) 选择要应用策略的命名空间
    - D) 选择要应用策略的节点

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 策略本身的标识符</p>
    <p><strong>说明</strong>: labels 字段用作策略本身的标识符，并在其他策略引用此策略时使用。</p>
    </details>

## 高级 Network Policy

11. **Cilium NetworkPolicy 中的“toCIDR”规则允许什么？**
    - A) 到特定 IP 地址范围的流量
    - B) 到特定域名的流量
    - C) 到特定 Service 的流量
    - D) 到特定端口的流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) 到特定 IP 地址范围的流量</p>
    <p><strong>说明</strong>: toCIDR 规则用于允许到特定 IP 地址范围（CIDR 表示法）的流量。</p>
    </details>

12. **Cilium NetworkPolicy 中的“toFQDNs”规则允许什么？**
    - A) 到特定 IP 地址的流量
    - B) 到特定端口的流量
    - C) 到特定域名的流量
    - D) 特定协议的流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) 到特定域名的流量</p>
    <p><strong>说明</strong>: toFQDNs 规则允许到特定域名（FQDN）的流量，Cilium 会监控 DNS 查找，以动态允许这些域名对应的 IP 地址。</p>
    </details>

13. **Cilium NetworkPolicy 的“toEntities”规则中的“world”实体表示什么？**
    - A) 所有集群内部端点
    - B) 所有外部网络
    - C) 所有节点
    - D) 所有命名空间

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 所有外部网络</p>
    <p><strong>说明</strong>: “world”实体指集群外部的所有网络。</p>
    </details>

14. **Cilium NetworkPolicy 中的“toServices”规则允许什么？**
    - A) 到特定 Kubernetes Service 的流量
    - B) 到特定外部 Service 的流量
    - C) 到特定端口的流量
    - D) 特定协议的流量

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) 到特定 Kubernetes Service 的流量</p>
    <p><strong>说明</strong>: toServices 规则用于允许到特定 Kubernetes Service 的流量。</p>
    </details>

15. **Cilium NetworkPolicy 中“nodeSelector”的作用是什么？**
    - A) 选择要应用策略的目标 Pod
    - B) 选择要应用策略的目标节点
    - C) 选择要应用策略的目标命名空间
    - D) 选择要应用策略的目标 Service

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 选择要应用策略的目标节点</p>
    <p><strong>说明</strong>: nodeSelector 用于选择策略适用的目标节点。</p>
    </details>

## L7 策略

16. **可以在 Cilium 的 L7 HTTP 策略中筛选哪些属性？**
    - A) 路径
    - B) 方法
    - C) 标头
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>说明</strong>: Cilium 的 L7 HTTP 策略可以筛选多种 HTTP 请求属性，包括路径、方法和标头。</p>
    </details>

17. **可以在 Cilium 的 L7 Kafka 策略中筛选哪些属性？**
    - A) 主题
    - B) API Key
    - C) 客户端 ID
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>说明</strong>: Cilium 的 L7 Kafka 策略可以筛选多种 Kafka 请求属性，包括主题、API Key 和客户端 ID。</p>
    </details>

18. **Cilium 的 L7 DNS 策略中的“matchPattern”规则允许什么？**
    - A) 精确域名匹配
    - B) 使用通配符进行域名模式匹配
    - C) IP 地址匹配
    - D) 端口号匹配

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 使用通配符进行域名模式匹配</p>
    <p><strong>说明</strong>: matchPattern 规则可以匹配包含通配符（*）的域名模式。示例：*.example.com</p>
    </details>

19. **可以在 Cilium 的 L7 gRPC 策略中筛选哪些属性？**
    - A) 方法名称
    - B) Service 名称
    - C) 元数据
    - D) 以上全部

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 以上全部</p>
    <p><strong>说明</strong>: Cilium 的 L7 gRPC 策略可以筛选多种 gRPC 请求属性，包括方法名称、Service 名称和元数据。</p>
    </details>

20. **应用 Cilium 的 L7 策略需要哪个组件？**
    - A) kube-proxy
    - B) Envoy Proxy
    - C) NGINX Ingress Controller
    - D) HAProxy

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) Envoy Proxy</p>
    <p><strong>说明</strong>: Cilium 使用 Envoy Proxy 应用 L7 策略。</p>
    </details>
