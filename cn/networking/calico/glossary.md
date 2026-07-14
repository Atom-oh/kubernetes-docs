# Calico 术语表

> **最后更新**: February 22, 2026

本文档提供与 Calico 网络和安全相关的关键术语与概念的定义。理解这些术语对于在 Kubernetes 环境中有效部署和运行 Calico 至关重要。

## 术语类别

术语按以下类别组织：
- **网络术语** - 通用网络概念
- **Calico 组件** - Calico 特有的组件和服务
- **策略术语** - 网络策略和安全概念
- **运维术语** - 运维和管理概念

---

## 网络术语

### A

**AS (Autonomous System)**
- 由单个组织控制、并向 Internet 呈现统一路由策略的一组 IP 网络和路由器。在 Calico 中，AS 编号用于 BGP 对等配置。

**ASN (Autonomous System Number)**
- 分配给 Autonomous System 的唯一标识符。Calico 节点可以配置私有 ASN（64512-65534）用于内部 BGP 路由。

### B

**BGP (Border Gateway Protocol)**
- 用于在自治系统之间交换路由信息的标准外部网关协议。Calico 使用 BGP 在节点之间及向外部网络分发 Pod IP 地址的路由。

**Block Affinity**
- IP 地址块与特定节点之间的关联关系。Calico 将 IP 块分配给节点，以提高路由效率并减少集群中的路由数量。

### C

**CIDR (Classless Inter-Domain Routing)**
- 一种分配 IP 地址和进行 IP 路由的方法。示例：10.244.0.0/16 表示包含 65,536 个 IP 地址的范围。

**CNI (Container Network Interface)**
- 用于在 Linux 容器中配置网络接口的规范和库集合。Calico 实现 CNI 规范，为 Kubernetes Pod 提供网络功能。

**Conntrack (Connection Tracking)**
- 用于跟踪网络连接以进行有状态数据包检查的 Linux 内核功能。Calico 使用 conntrack 实现网络策略和 NAT。

### D

**DNAT (Destination NAT)**
- 修改数据包目标 IP 地址的网络地址转换。用于 Kubernetes 中的 Service 负载均衡。

**Direct Routing**
- 一种网络模式，其中不同节点上的 Pod 之间的流量无需封装即可直接路由。要求底层网络支持 Pod CIDR 路由。

**DSR (Direct Server Return)**
- 一种负载均衡技术，其中响应流量绕过负载均衡器，直接从服务器发送到客户端。Calico 的 eBPF 数据平面支持 DSR，从而提升性能。

### E

**eBPF (extended Berkeley Packet Filter)**
- 一种允许在内核空间运行沙箱程序的 Linux 内核技术。Calico 使用 eBPF 作为 iptables 的替代数据平面，以提高性能。

**Encapsulation**
- 将网络数据包封装在其他数据包中的过程。Calico 支持用于 Overlay 网络的 IPIP 和 VXLAN 封装。

### F

**FQDN (Fully Qualified Domain Name)**
- 指定主机在 DNS 层级中确切位置的完整域名。Calico 支持基于 FQDN 的网络策略来控制 Egress。

**Full Mesh**
- 一种 BGP 拓扑，其中每个节点都与其他所有节点建立对等关系。适合小型集群，但在超过 100 个节点后扩展性不佳。

### I

**IPAM (IP Address Management)**
- 负责分配、跟踪和管理 IP 地址的系统。Calico 包含一个使用基于块分配的内置 IPAM 系统。

**IPIP (IP-in-IP)**
- 一种将 IP 数据包封装在其他 IP 数据包中的封装协议。其开销低于 VXLAN，但云提供商支持有限。

**IPset**
- 用于存储 IP 地址、网络或端口集合的 Linux 内核功能。Calico 使用 ipset 高效地将流量与多个地址进行匹配。

**iptables**
- 在网络层运行的 Linux 内核防火墙。Calico 在标准数据平面中使用 iptables（或 nftables）进行数据包过滤和 NAT。

### M

**MTU (Maximum Transmission Unit)**
- 可在网络段上传输的最大数据包大小。封装会降低有效 MTU（IPIP：-20 bytes，VXLAN：-50 bytes）。

### N

**NAT (Network Address Translation)**
- 修改数据包头中 IP 地址信息的过程。Calico 使用 NAT 实现 Pod Egress 和 Service。

**nftables**
- iptables 的后继者，提供用于数据包分类的现代框架。Calico 支持将 nftables 作为 iptables 的替代方案。

### O

**Overlay Network**
- 构建在现有物理网络之上的虚拟网络。Calico 为无法进行直接路由的环境支持 IPIP 和 VXLAN Overlay 模式。

### R

**Route Reflector**
- 在客户端之间反射路由的 BGP 路由器，无需建立 Full Mesh 对等关系。对于在大型 Calico 集群中扩展 BGP 至关重要。

**Routing Table**
- 存储到网络目标路由的数据结构。Calico 将 Pod CIDR 的路由写入 Linux 内核路由表。

### S

**SNAT (Source NAT)**
- 修改数据包源 IP 地址的网络地址转换。用于 Pod Egress 流量和伪装。

### V

**veth (Virtual Ethernet)**
- 用于连接网络命名空间的一对虚拟网络接口。每个 Calico Pod 都有一对 veth，用于将其连接到主机网络。

**VXLAN (Virtual Extensible LAN)**
- 一种通过 Layer 3 基础设施扩展 Layer 2 网络的封装协议。与 IPIP 相比具有更好的云兼容性，但开销更高。

### W

**WireGuard**
- 一种提供快速且安全加密的现代 VPN 协议。Calico 使用 WireGuard 加密节点之间的 Pod 到 Pod 流量。

**Workload Endpoint**
- Calico 对工作负载（Pod、VM 或容器）网络接口的表示。存储 IP 地址、标签和策略关联。

---

## Calico 组件

### B

**BIRD (BIRD Internet Routing Daemon)**
- Calico 用于路由分发的 BGP 守护进程。BIRD 管理 BGP 对等、路由通告和 Route Reflector 功能。

### C

**calicoctl**
- 用于管理 Calico 资源的命令行工具。用于查看状态、配置策略、管理 IPAM 和故障排除。

**Calico API Server**
- 为 Calico 资源提供 Kubernetes API 扩展的可选组件。支持通过 kubectl 访问 Calico CRD。

**CNI Plugin**
- 为 Calico 实现 CNI 规范的二进制文件。负责设置 Pod 网络（veth 对、路由、IP 分配）。

**confd**
- 一种配置管理工具，可根据 Calico datastore 生成 BIRD 配置文件。监视变更并动态更新 BIRD。

### D

**Dikastes**
- 用于在 Calico 中实施 L7 策略的 Sidecar 代理（主要在 Calico Enterprise 中）。提供应用层可见性和控制能力。

### F

**Felix**
- 运行在每个节点上的主要 Calico Agent。负责配置路由、iptables/eBPF 规则并实施网络策略。

### K

**kube-controllers**
- 一组在 Kubernetes 与 Calico datastore 之间同步数据的 controller。包括 policy、namespace、serviceaccount、workloadendpoint 和 node controller。

### T

**Tigera Operator**
- 管理 Calico 安装和生命周期的 Kubernetes Operator。通过 CRD 提供声明式配置。

**Typha**
- 位于 Felix 和 datastore 之间的扇出代理。通过缓存和复用连接来降低 API server 的负载。

---

## 策略术语

### A

**Action**
- 策略规则评估的结果：Allow、Deny、Log 或 Pass。决定如何处理匹配的流量。

**applyOnForward**
- 将规则应用于转发流量（通过主机的流量）的策略设置。用于控制 Pod 与外部网络之间的流量。

### D

**Default Deny**
- 一种安全态势，除非显式允许，否则所有流量都会被阻止。使用不含 allow 规则的全匹配策略实现。

**DoNotTrack**
- 针对匹配流量绕过连接跟踪的策略选项。适用于可接受无状态处理的高吞吐量场景。

### E

**Egress**
- 来自 Pod 的出站网络流量。Egress 策略控制 Pod 可以与哪些目标通信。

### G

**GlobalNetworkPolicy**
- 一种适用于集群中所有 Namespace 的 Calico 策略资源。用于集群范围的安全规则。

**GlobalNetworkSet**
- 一组集群范围的 IP 地址或 CIDR。由 GlobalNetworkPolicy 引用，以便一致地定义外部 Endpoint。

### H

**Host Endpoint**
- 表示主机网络接口的 Calico 资源。支持将网络策略应用于主机级流量。

### I

**Ingress**
- 到达 Pod 的入站网络流量。Ingress 策略控制哪些来源可以与 Pod 通信。

### N

**NetworkPolicy**
- 一种 Kubernetes 或 Calico 资源，用于指定允许 Pod 如何通信。在 L3-L4 层运行（使用 Calico Enterprise 时也可在 L7 层运行）。

**NetworkSet**
- 一组 Namespace 范围的 IP 地址或 CIDR。提供对外部 Endpoint 分组的方法，以便在网络策略中使用。

### O

**Order**
- 决定策略评估顺序的数值。较小的数值先进行评估。具有相同 Order 的策略按字母顺序评估。

### P

**Pass**
- 一种跳转到下一个 Tier 而不做决定的策略动作。用于分层策略模型中委托决策。

**Policy Selector**
- 一种基于标签的表达式，用于确定策略适用于哪些 Endpoint。使用 Calico 的选择器语法（例如，`app == 'web'`）。

**PreDNAT**
- 在目标 NAT 之前应用的策略类型。用于控制对 NodePort 和 LoadBalancer Service 的访问。

### S

**Staged Policy**
- 一种预览模式的策略，会记录将发生的情况但不会实际实施。Calico Enterprise 提供此功能用于策略测试。

**Selector**
- 一种基于标签匹配资源的表达式。Calico 同时将选择器用于策略目标以及源/目标匹配。

### T

**Tier**
- 一种提供分层策略评估的策略分组机制。较低 Order 的 Tier 中的策略先进行评估。

---

## 运维术语

### A

**APIServer (Calico)**
- 提供对 Calico 资源 API 访问的组件。可启用以集成 kubectl。

### B

**Block**
- Calico IPAM 中的 IP 地址分配单元。默认大小为 /26（64 个地址）。将 Block 分配给节点以实现高效路由。

**Block Affinity**
- IP 块与节点之间的绑定关系。确保节点上的 Pod 从分配给该节点的 Block 中获取 IP。

### D

**Dataplane**
- 负责数据包转发和策略实施的组件。Calico 支持 iptables 和 eBPF 数据平面。

**Datastore**
- Calico 配置的后端存储。支持 Kubernetes API（默认）或 etcd。

### F

**FelixConfiguration**
- 用于配置整个集群中 Felix 行为的 CRD。控制日志、指标、数据平面设置等。

**Flow Logs**
- Calico 处理的网络连接记录。包括源、目标、动作和元数据。

### H

**Health Check**
- 用于 Calico 组件的存活和就绪探针。Felix 在端口 9099 上公开健康检查 Endpoint。

### I

**Installation**
- 定义 Calico Deployment 配置的 Tigera Operator CRD。指定网络模式、资源和组件设置。

### M

**Metrics**
- 由 Calico 组件公开的 Prometheus 格式统计信息。Felix（9091）、Typha（9093）和 kube-controllers 公开运维指标。

### P

**Pod CIDR**
- 为集群中的 Pod 分配的 IP 地址范围。在 Calico 的 IPPool 资源中配置。

### R

**Rollout**
- 更新 Calico 组件的过程。Operator 管理滚动更新以最大限度减少中断。

### T

**TigeraStatus**
- 用于报告 Calico 组件状态的 CRD。显示 Deployment 健康状况和配置状态。

---

## Calico 与 Kubernetes 术语对照

| Kubernetes 术语 | Calico 对应项 | 说明 |
|-----------------|-------------------|-------|
| NetworkPolicy | NetworkPolicy | Calico 使用附加功能扩展 K8s NetworkPolicy |
| - | GlobalNetworkPolicy | 集群范围策略（Calico 特有） |
| - | Tier | 策略层级（Calico 特有） |
| Service CIDR | N/A | Calico 遵循 K8s Service CIDR |
| Pod CIDR | IPPool | Calico 管理 Pod IP 分配 |
| Node | Node | Calico 镜像 K8s Node 资源 |
| Namespace | Namespace | Calico 策略可按 Namespace 选择 |
| Labels | Labels | 相同的标签语法，用于选择器 |
| Endpoint | WorkloadEndpoint | Calico 的内部 Endpoint 表示 |
| - | HostEndpoint | 主机接口策略（Calico 特有） |

---

## Calico 与 Cilium 术语对照

| Calico 术语 | Cilium 对应项 | 描述 |
|-------------|-------------------|-------------|
| Felix | Cilium Agent | 主要节点 Agent |
| BIRD | BGP Control Plane | BGP 路由守护进程 |
| Typha | - | 连接扇出代理（Calico 特有） |
| IPPool | IPAM Pool | IP 地址分配池 |
| NetworkPolicy | CiliumNetworkPolicy | Namespace 范围策略 |
| GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy | 集群范围策略 |
| NetworkSet | CiliumIPSet | IP 地址分组 |
| Tier | - | 策略层级（Calico 特有） |
| WorkloadEndpoint | CiliumEndpoint | Pod 网络 Endpoint |
| HostEndpoint | - | 主机策略（Calico 特有） |
| eBPF Dataplane | eBPF Dataplane | 高性能数据包处理 |
| WireGuard | WireGuard | 节点之间的加密 |
| - | Hubble | 可观测性平台（Cilium 特有） |
| Flow Logs | Hubble Flows | 网络流可见性 |
| kube-controllers | Cilium Operator | Kubernetes 同步 |
| calicoctl | cilium CLI | 管理命令行工具 |

---

## 交叉引用

### 架构深入解析
- **Felix**: 请参阅 [Part 2: Architecture](02-architecture.md)
- **BGP Configuration**: 请参阅 [Part 4: BGP Deep Dive](04-bgp-deep-dive.md)
- **Typha Scaling**: 请参阅 [Part 7: Advanced Topics](07-advanced-topics.md#typha-sizing-formula)

### 网络策略
- **Kubernetes NetworkPolicy**: 请参阅 [Part 5: Network Policy](05-network-policy.md)
- **GlobalNetworkPolicy**: 请参阅 [Part 5: Network Policy](05-network-policy.md)
- **Tier-Based Policies**: 请参阅 [Part 5: Network Policy](05-network-policy.md)

### 运维
- **Installation Methods**: 请参阅 [Part 9: Operations](09-operations.md#installation-guide)
- **calicoctl Commands**: 请参阅 [Part 9: Operations](09-operations.md#calicoctl-command-reference)
- **Troubleshooting**: 请参阅 [Part 9: Operations](09-operations.md#troubleshooting)

### EKS 集成
- **VPC CNI + Calico**: 请参阅 [Part 8: EKS Integration](08-eks-integration.md#vpc-cni--calico-architecture)
- **Installation Methods**: 请参阅 [Part 8: EKS Integration](08-eks-integration.md#installation-methods-comparison)

---

## 测验

要测试你在本章学到的内容，请尝试 [术语表测验](../../quizzes/networking/calico/glossary-quiz.md)。
