# Kubernetes 网络概览测验

本测验用于检验您对 Kubernetes 网络基础知识、CNI (Container Network Interface) 以及各种 CNI 解决方案的理解。

## 测验题目

### 1. 以下哪项不是 Kubernetes 网络模型的核心要求？

A. 每个 Pod 无需 NAT 即可与其他任何 Pod 通信
B. 每个 Node 无需 NAT 即可与每个 Pod 通信
C. Pod 看到的自身 IP 与其他对象看到的该 Pod IP 相同
D. 每个 Pod 都必须拥有在重启后仍保持不变的静态 IP 地址

<details>
<summary>显示答案</summary>

**答案：D. 每个 Pod 都必须拥有在重启后仍保持不变的静态 IP 地址**

**说明：**
Kubernetes 网络模型的核心要求有以下三项：
1. 每个 Pod 无需 NAT 即可与其他任何 Pod 通信
2. 每个 Node 无需 NAT 即可与每个 Pod 通信
3. Pod 看到的自身 IP 与其他对象看到的该 Pod IP 相同

Pod IP 地址是临时性的——当 Pod 重启时，它会获得一个新的 IP。这正是需要 Service 的原因。

</details>

### 2. CNI (Container Network Interface) 的主要作用是什么？

A. 与 Kubernetes API server 通信以作出 Pod 调度决策
B. 创建容器网络接口并分配 IP 地址
C. 为 Kubernetes Service 实现负载均衡
D. 下载和缓存容器镜像

<details>
<summary>显示答案</summary>

**答案：B. 创建容器网络接口并分配 IP 地址**

**说明：**
CNI 是用于容器网络连接的标准接口。其主要职责包括：
- 在创建容器时创建网络接口（veth pairs）
- 分配 IP 地址（IPAM）
- 设置路由规则
- 在删除容器时清理网络资源

Kubelet 调用 CNI plugin 来设置 Pod 网络。

</details>

### 3. Overlay 网络与 Underlay（Native Routing）网络之间的正确区别是什么？

A. Overlay 提供更高性能，而 Underlay 会带来更多开销
B. Overlay 在现有网络之上构建虚拟网络，而 Underlay 直接在物理网络上路由
C. Overlay 使用 BGP，而 Underlay 使用 VXLAN
D. Overlay 仅适用于 AWS，而 Underlay 仅适用于本地部署

<details>
<summary>显示答案</summary>

**答案：B. Overlay 在现有网络之上构建虚拟网络，而 Underlay 直接在物理网络上路由**

**说明：**
- **Overlay Network**：使用 VXLAN、IPIP 等封装技术，在现有网络之上构建虚拟网络。配置简单，但会产生封装开销。
- **Underlay (Native Routing)**：直接在物理网络上路由以获得更高性能。使用 BGP 等技术，需要与网络基础设施集成。

</details>

### 4. 哪种 Kubernetes Service 类型只能从集群内部访问？

A. NodePort
B. LoadBalancer
C. ClusterIP
D. ExternalName

<details>
<summary>显示答案</summary>

**答案：C. ClusterIP**

**说明：**
Kubernetes Service 类型的特性：
- **ClusterIP**：分配一个只能在集群内部访问的虚拟 IP（默认）
- **NodePort**：通过所有 Node 上的特定端口（30000-32767）提供外部访问
- **LoadBalancer**：为外部访问配置云负载均衡器
- **ExternalName**：为外部 DNS 名称创建 CNAME 记录

</details>

### 5. 哪个 CNI 将 eBPF 技术作为其核心？

A. Flannel
B. Weave Net
C. Cilium
D. AWS VPC CNI

<details>
<summary>显示答案</summary>

**答案：C. Cilium**

**说明：**
Cilium 是以 eBPF（extended Berkeley Packet Filter）为核心技术的 CNI。eBPF 的优势：
- 通过内核级网络处理实现高性能
- 与 iptables 相比具有更高效的数据包处理能力
- L7 可见性和策略执行
- 可以替代 kube-proxy

虽然 Calico 也支持 eBPF 模式，但 Cilium 从一开始就是以 eBPF 为核心设计的。

</details>

### 6. 以下哪项不是 AWS VPC CNI 的特性？

A. 为每个 Pod 分配实际的 VPC IP 地址
B. 使用 EC2 实例的 ENI（Elastic Network Interfaces）
C. 每个 Pod 可分配的 IP 数量受实例类型限制
D. 原生支持 L7 Network Policy

<details>
<summary>显示答案</summary>

**答案：D. 原生支持 L7 Network Policy**

**说明：**
AWS VPC CNI 的特性：
- 为 Pod 分配实际的 VPC IP 地址（VPC native）
- 使用 EC2 ENI 的 Secondary IP
- 最大 Pod 数量受实例类型限制（ENI 数量 × 每个 ENI 的 IP 数量）
- 默认仅支持 L3-L4 Network Policy（L7 需要 Calico 或 Cilium）

对于 L7 Network Policy，您需要 Cilium 等额外解决方案。

</details>

### 7. 以下哪种 CNI 组合支持 BGP（Border Gateway Protocol）？

A. Flannel, Weave Net
B. Calico, Cilium
C. AWS VPC CNI, Flannel
D. Weave Net, AWS VPC CNI

<details>
<summary>显示答案</summary>

**答案：B. Calico, Cilium**

**说明：**
支持 BGP 的 CNI：
- **Calico**：BGP 是核心功能，支持 ToR switch peering、Route Reflector
- **Cilium**：支持 BGP（v1.10+），适用于多集群环境

不支持 BGP 的 CNI：
- **Flannel**：简单的 Overlay 网络，不支持 BGP
- **Weave Net**：使用自身的路由协议，不支持 BGP
- **AWS VPC CNI**：使用 VPC native routing，不支持 BGP

</details>

### 8. 哪种流量不受 Kubernetes Network Policy 的约束？

A. 从一个 Pod 到另一个 Pod 的流量
B. 从 Pod 到外部互联网的流量
C. 同一 Pod 中容器之间的 localhost 流量
D. 从外部来源进入 Pod 的流量

<details>
<summary>显示答案</summary>

**答案：C. 同一 Pod 中容器之间的 localhost 流量**

**说明：**
Network Policy 控制 Pod 之间的流量。同一 Pod 内的容器：
- 共享相同的网络命名空间
- 通过 localhost（127.0.0.1）通信
- 不受 Network Policy 约束

受 Network Policy 约束的流量：
- Pod 之间的 Ingress/Egress 流量
- 从 Pod 到外部的 Egress 流量
- 从外部到 Pod 的 Ingress 流量

</details>

### 9. 为大规模 Kubernetes 集群（500+ Node）选择 CNI 时，最重要的考量是什么？

A. 是否提供 UI dashboard
B. Control plane 可扩展性和数据同步效率
C. Logo 设计和文档质量
D. 新版本发布频率

<details>
<summary>显示答案</summary>

**答案：B. Control plane 可扩展性和数据同步效率**

**说明：**
为大型集群选择 CNI 时的考量：

1. **Control Plane 可扩展性**：
   - Calico：Typha 组件可降低 API server 负载
   - Cilium：通过 Operator 模式实现高效同步

2. **数据同步**：
   - 每个 Node agent 的资源使用情况
   - Policy 更新传播时间

3. **性能**：
   - 基于 eBPF 的解决方案比基于 iptables 的方案扩展性更好
   - 规则数量增加时的性能下降情况

</details>

### 10. Ingress 与 Service 之间的正确区别是什么？

A. Ingress 在 L4 运行，而 Service 在 L7 运行
B. Ingress 定义 HTTP/HTTPS 路由规则，而 Service 为一组 Pod 提供网络端点
C. Ingress 仅支持集群内部通信，而 Service 仅支持外部通信
D. Ingress 仅支持 TCP，而 Service 仅支持 UDP

<details>
<summary>显示答案</summary>

**答案：B. Ingress 定义 HTTP/HTTPS 路由规则，而 Service 为一组 Pod 提供网络端点**

**说明：**
- **Service**：为一组 Pod 提供稳定的网络端点（L4）
  - ClusterIP、NodePort、LoadBalancer 类型
  - 支持 TCP/UDP 协议

- **Ingress**：定义 HTTP/HTTPS 流量路由规则（L7）
  - 基于 Host 的路由
  - 基于 Path 的路由
  - TLS 终止
  - Ingress Controller 提供实际实现

Ingress 最终将流量转发到后端 Service。

</details>

---

## 补充学习资源

- [Kubernetes Networking Model](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [CNI Specification](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Network Policy Guide](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
