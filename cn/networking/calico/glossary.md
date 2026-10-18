# Calico 术语表

> **审阅基线**：Calico 3.32.2；对照术语已按 Cilium 1.20.1 核验。
> **最后更新**：2026 年 9 月 12 日

本文档定义 Calico 网络与安全中的关键术语和概念。理解这些术语有助于在 Kubernetes 环境中有效部署和运维 Calico。

## 术语分类

术语分为以下类别：
- **网络术语** - 通用网络概念
- **Calico 组件** - Calico 专属组件和服务
- **策略术语** - 网络策略和安全概念
- **运维术语** - 运维和管理概念

---

## 网络术语

### A

**AS (Autonomous System)**
- 由单个组织控制、向 Internet 公布统一路由策略的一组 IP 网络和路由器。在 Calico 中，AS 编号用于配置 BGP 对等关系。

**ASN (Autonomous System Number)**
- BGP 使用的标识符。RFC 6996 规定私有用途范围为 **64512–65534** 和 **4200000000–4294967294**。私有 ASN 可在不同管理域中重复使用，不能视为全球唯一的公共分配编号。

### B

**BGP (Border Gateway Protocol)**
- 既用于自治系统之间（eBGP），也用于单个 AS 内部（iBGP）的路由协议。Calico 可用 BGP 发布 Pod/Service 路由，但并非所有 Calico 数据平面或覆盖网络配置都需要 BGP。

**Block Affinity**
- IPAM 地址块与其所有者（通常是节点）之间的关联。未启用严格亲和性时，符合条件的分配可借用其他节点的地址块。亲和性不保证每个本地 Pod 地址都来自本节点拥有的块；应检查资源类型、状态和实际分配器。

### C

**CIDR (Classless Inter-Domain Routing)**
- 一种 IP 地址分配和 IP 路由方法。例如，10.244.0.0/16 表示包含 65,536 个 IP 地址的范围。

**CNI (Container Network Interface)**
- 用于配置容器网络连接及相关插件的规范。Calico 提供 CNI 实现；Linux 网络与受支持的 Windows HNS 配置在行为上有所不同。

**Conntrack (Connection Tracking)**
- 用于跟踪流状态，以支持有状态策略和 NAT。标准 Linux 数据平面使用内核连接跟踪；Calico BPF 数据平面也维护 BPF conntrack 映射，两者不能视为可互换的调优目标。

### D

**DNAT (Destination NAT)**
- 修改数据包目标 IP 地址的网络地址转换。Kubernetes 使用它实现 Service 负载均衡。

**Direct Routing**
- 一种网络模式：不同节点上的 Pod 之间直接路由流量，不进行封装。底层网络必须支持 Pod CIDR 路由。

**DSR (Direct Server Return)**
- 一种 Service 负载均衡模式：后端返回流量时不经过原转发节点。Calico BPF 在特定网络和源地址限制下支持 DSR；它并非普遍兼容云负载均衡器。

### E

**eBPF (extended Berkeley Packet Filter)**
- 一种 Linux 内核可编程能力，Calico BPF 数据平面用它处理网络、策略和 Service。兼容性与性能取决于内核、平台和工作负载；不能保证每种部署的开销都会降低。

**Encapsulation**
- 将网络数据包封装在其他数据包中的过程。Calico 支持使用 IPIP 和 VXLAN 进行覆盖网络封装。

### F

**FQDN (Fully Qualified Domain Name)**
- 完整的 DNS 名称。文档所述 Calico 域名出站策略功能需要商业版；OSS NetworkSet 中的 CIDR 条目不会因此成为 DNS 规则。不要将其与单独集成的 HTTP 应用层策略混为一谈。

**Full Mesh**
- 一种 BGP 拓扑，其中 N 个参与节点各自与其余每个节点建立对等会话，共有 N(N−1)/2 个会话。容量取决于拓扑变化、路由数量和硬件；100 个节点并非普遍适用的协议上限。

### I

**IPAM (IP Address Management)**
- 负责分配、跟踪和管理 IP 地址的系统。Calico 内置基于地址块分配的 IPAM。

**IPIP (IP-in-IP)**
- 一种 IP 封装。Calico 的 IPv4 IP-in-IP 模式会增加 20 字节的外层 IPv4 标头，并要求底层网络允许 IP 协议 4；它不是 UDP 端口。

**IPset**
- 一种 Linux 内核功能，用于存储 IP 地址、网络或端口集合。Calico 使用 ipset 高效地将流量与多个地址进行匹配。

**iptables**
- 用于配置 Linux Netfilter 数据包过滤和 NAT 规则的用户空间接口。iptables legacy 与 nft 后端不同于 Calico 独立的原生 Nftables 数据平面；更改 iptables 后端不会选择该数据平面。

### M

**MTU (Maximum Transmission Unit)**
- 链路或路径可传输的最大数据包大小。有效底层 MTU 为 1500 字节时，Calico 的示例 MTU 为：IPv4 IPIP 1480，IPv4/IPv6 VXLAN 为 1450/1430，IPv4/IPv6 WireGuard 为 1440/1420。应根据实际最小路径 MTU、所选模式和平台限制计算；这些是计算值，并非实测性能数据。

### N

**NAT (Network Address Translation)**
- 修改数据包标头中 IP 地址信息的过程。Calico 使用 NAT 处理 Pod 出站流量和 Service。

**nftables**
- Calico 原生 Nftables 模式使用的 Linux 数据包过滤框架。这是 Installation 中独立的数据平面选项，与使用 NFT 后端的 Iptables 不同。

### O

**Overlay Network**
- 构建在现有物理网络之上的虚拟网络。当无法直接路由时，Calico 支持 IPIP 和 VXLAN 覆盖模式。

### R

**Route Reflector**
- 将路由反射给客户端的 BGP 发言方。若总节点数为 N（其中 r 个反射器彼此全互联），且每个客户端都与全部 r 个反射器对等，则会话数为 r(N−r)+r(r−1)/2。N=100、r=2 时为 197 个会话，而全互联需要 4950 个；使用一个反射器时为 99 个会话，但反射器没有冗余。

**Routing Table**
- 存储到网络目标路由的数据结构。Calico 会将 Pod CIDR 路由写入 Linux 内核路由表。

### S

**SNAT (Source NAT)**
- 修改数据包源 IP 地址的网络地址转换。用于 Pod 出站流量和伪装。

### V

**veth (Virtual Ethernet)**
- 一对 Linux 虚拟接口，通常由 CNI 插件创建，用于连接 Pod 网络命名空间与主机。并非每个 Pod 的 veth 都由 Felix 创建；hostNetwork Pod、Windows 和其他网络附加类型的情况有所不同。

**VXLAN (Virtual Extensible LAN)**
- 一种通过三层基础设施扩展二层网络的封装协议。与 IPIP 相比，它对云环境的兼容性更好，但开销更高。

### W

**WireGuard**
- Calico 用于已配置且具备能力的节点对之间受支持流量的加密隧道协议。它不会自动加密同节点流量、不受支持对等端的流量或所有外部流量，也不同于应用层 mTLS。

**Workload Endpoint**
- Calico 中带命名空间的工作负载接口表示，包含地址、标签和配置文件引用，供策略计算使用。它通常由编排器或插件管理，并不存储每项生效策略决策的清单。

---

## Calico 组件

### B

**BIRD (BIRD Internet Routing Daemon)**
- 在使用 BGP 的 Calico 配置中承担路由守护进程的组件。Calico 3.32.2 使用经过补丁的 BIRD 1.6.8 系列；任意上游 BIRD 2 配置都不能与之等同。

### C

**calicoctl**
- 用于管理 Calico 资源的命令行工具，可查看状态、配置策略、管理 IPAM 和排查故障。

**Calico API Server**
- Calico 的 API 集成，与 Kubernetes API Server 不同，且 OSS 版本可用。面向用户的 projectcalico.org/v3 API 及其后端 CRD/原生 API 模式取决于已配置的安装方式；应遵循维护中的安装指南，不要将所有 API 组当作别名。

**CNI Plugin**
- 实现 Calico CNI 规范的二进制文件，负责设置 Pod 网络（veth 对、路由和 IP 分配）。

**confd**
- 一种配置管理工具，根据 Calico datastore 生成 BIRD 配置文件。它会监视变更并动态更新 BIRD。

### D

**Dikastes**
- 与 Istio/Envoy 配合使用的应用层策略决策组件。Envoy 处理流量并向 Dikastes 请求授权；Dikastes 本身不是转发代理。该集成有面向 Calico OSS 的文档说明，并有特定版本前提条件。

### F

**Felix**
- 每节点运行的代理，负责配置选定的数据平面、策略和相关路由。CNI 插件负责设置 Pod 接口和 IPAM；Felix 并不是逐数据包转发的用户空间路径。

### G

**Goldmane / Whisker**
- 分别是 OSS 流量聚合 API 和 Web UI。它们的部署、访问控制和预览状态与 Felix 基础指标彼此独立。

### K

**kube-controllers**
- 负责 Kubernetes/Calico 协调的控制器，包括节点/IPAM 工作及依赖 datastore 的同步。启用的控制器集合因安装方式和 datastore 而异；列出控制器类型不表示它们在每个 Kubernetes datastore 部署中都会运行。

### T

**Tigera Operator**
- 管理 Calico 安装及其生命周期的 Kubernetes Operator。它通过 CRD 提供声明式配置。

**Typha**
- datastore 更新扇出和缓存服务，可减少每个 Felix 的 watch 负载。它可使用多种 watch/syncer 类型并运行多个副本；它不是全群集共享的单一 watch，也不会自动提供策略联邦。Typha 扩展方式见高级主题章节。

---

## 策略术语

### A

**Action**
- Calico 规则的结果：Allow 和 Deny 会终止该路径上的策略评估；Log 会继续评估；Pass 会委托给下一个适用 Tier，并最终进入配置文件处理。Log 本身并不代表允许。

**applyOnForward**
- GlobalNetworkPolicy 的选项，用于通过 HostEndpoint 处理转发流量。它不会创建 HostEndpoint；使用 preDNAT/doNotTrack 策略时必须设置此项。工作负载策略与主机转发策略的适用范围不同。

### D

**Default Deny**
- 一种安全态势：在选定范围内，除非有效策略集合明确允许，否则流量会被拒绝。引入时应明确依赖关系并测试命名空间范围，不要不加区分地应用空规则集的全群集策略。

**DoNotTrack**
- doNotTrack GlobalNetworkPolicy 设置会在连接跟踪之前处理 HostEndpoint 流量，并且要求设置 applyOnForward。无状态返回路径需要显式规则；它不能与 preDNAT 组合使用。

### E

**Egress**
- Pod 发出的出站网络流量。Egress 策略控制 Pod 可以与哪些目标通信。

### G

**GlobalNetworkPolicy**
- Calico 的群集级策略，可跨命名空间选择工作负载或选择 HostEndpoint。实际范围由选择器决定；群集级并不表示它会自动影响每个 Pod。

**GlobalNetworkSet**
- 带标签的群集级 IP 地址/CIDR 集合。策略选择器可匹配它；在全局命名空间选择配置适当时，命名空间级 Calico 策略也可引用它。它不限于 GlobalNetworkPolicy 引用。

### H

**Host Endpoint**
- 表示主机接口的资源，可用于主机策略以及配置后的转发流量策略。创建它可能改变流量处理；应先检查策略、配置文件、故障保护规则和管理访问。

### I

**Ingress**
- 进入 Pod 的入站网络流量。Ingress 策略控制哪些来源可以与 Pod 通信。

### N

**NetworkPolicy**
- 这里有两种不同 API：Kubernetes networking.k8s.io/v1 NetworkPolicy 和 Calico projectcalico.org/v3 NetworkPolicy。Calico 另外提供 action、order、tier 和选择器；HTTP 规则需要单独且受支持的应用层集成（包括 OSS Dikastes），而基于域名的规则受版本许可限制。

**NetworkSet**
- 命名空间范围的 IP 地址或 CIDR 集合，可将外部端点分组以供网络策略使用。

### O

**Order**
- 数值型评估优先级：先按 Tier 的 order 排序，再按该 Tier 内的策略 order 排序。需要确定顺序时应使用明确且不同的优先级，不要依赖相同值时的顺序；前面的终止性 action 可能使后续策略不再相关。

### P

**Pass**
- 跳过当前 Tier 剩余策略并继续检查下一个适用 Tier；到达最后一个适用 Tier 后，再评估端点配置文件。Pass 不是最终允许。

**Profile**
- 端点继承的共享标签。Profile 可包含旧式策略规则，但已弃用这种用法，应改用 NetworkPolicy/GlobalNetworkPolicy；不要把 Profile 当作 Kubernetes RBAC。

**Policy Selector**
- 基于标签的表达式，用于确定策略适用的端点。使用 Calico 选择器语法（例如 `app == 'web'`）。

**PreDNAT**
- preDNAT GlobalNetworkPolicy 设置会在目标 NAT 之前评估 HostEndpoint 入站流量。它要求设置 applyOnForward，且不能与 doNotTrack 或 egress 策略方向组合。

### S

**Staged Policy**
- 用于评估拟议变更的非强制执行策略资源。OSS 也支持 Staged Policy，但有文档列明的资源和可观测性前提；仅创建该资源并不能保证获得完整的决策日志。

**Selector**
- 根据标签匹配资源的表达式。Calico 将选择器用于策略目标以及源/目标匹配。

### T

**Tier**
- 按顺序排列的策略组；数值较小的 order 优先。Allow/Deny 是终止操作，Pass 会委托后续处理；选中的 Tier 中没有匹配规则时，会使用其 defaultAction（通常为 Deny）。

---

## 运维术语

### A

**APIServer (Calico)**
- 用于配置 Calico API 集成的 Operator 资源。它不是 Kubernetes 控制平面，也不是仅限 Enterprise 的功能；API 访问仍需正确配置 API 路径和 RBAC。

### B

**Block**
- Calico IPAM 中的分配单元。IPv4 默认块大小为 /26，IPv6 为 /122，每块均包含 64 个地址。预留和分配限制会降低工作负载可用容量，Windows 环境尤其如此。

**Block Affinity**
- IPAM 地址块与其所有者（通常是节点）之间的关联。未启用严格亲和性时，符合条件的分配可借用其他节点的块。亲和性不保证每个本地 Pod 地址都来自本节点拥有的块；应检查资源类型、状态和实际分配器。

### D

**Dataplane**
- 数据包处理实现。Calico 提供 Linux Iptables、Nftables 和 BPF 选项，也支持特定 Windows HNS 配置；其他集成有各自的要求。

**Datastore**
- Calico 配置和状态的存储/API 访问方式，包括 Kubernetes API datastore 或受支持的直接 etcdv3 部署。推荐使用 Kubernetes datastore；BPF 等功能还受额外 datastore 限制。

### F

**FelixConfiguration**
- Felix 设置的 API 资源，包括群集默认值和受支持的逐节点覆盖配置。它可控制指标、日志和数据平面选项；不能替代 Operator 的 Installation API。

**Flow Logs**
- 聚合后的连接流记录，不同于数据包捕获或进程日志。当前 OSS Operator/Helm 安装可使用 Goldmane 和 Whisker；流日志指南将该功能标为技术预览。

### H

**Health Check**
- 组件存活和就绪状态报告。Felix 可在其配置端口（默认 9099）公开健康检查端点；组件健康并不能证明应用可达或策略得到正确执行。

### I

**IPPool**
- 独立的 Calico 资源，用于定义地址范围、封装/NAT 和分配资格。Calico IPAM 可为受支持的 Workload/Tunnel/LoadBalancer 用途分配地址；IPPool 不是 Kubernetes Node PodCIDR 的别名。CIDR 和 blockSize 不可变更。

**Installation**
- 定义 Calico 部署配置的 Tigera Operator CRD，用于指定网络模式、资源和组件设置。

### M

**Metrics**
- Prometheus 格式的统计数据，其启用方式和端口因组件而异。Felix 默认端口为 9091；Typha 默认也是 9091，但通常会显式配置为 9093；kube-controllers 默认端口为 9094。请核对实际设置和指标类型。

### P

**Pod CIDR**
- Pod 地址范围，可指群集范围，也可指 Kubernetes 节点的分配范围。Calico IPPool 是另一个独立对象；两者关系取决于 IPAM。使用 VPC CNI 时，Calico 仅实施策略的模式不会分配 Pod IP。

### R

**Rollout**
- 受控更新 Calico 组件的过程。Operator 协调和滚动更新设置有助于管理可用性，但不能保证流量不中断，也不能保证 schema/data 变更可回滚。

### T

**TigeraStatus**
- 报告 Calico 组件状态的 CRD，用于显示部署健康状况和配置状态。

---

## Calico 与 Kubernetes 术语对照

| Kubernetes 术语 | Calico 对应项 | 说明 |
|-----------------|-------------------|-------|
| NetworkPolicy | Calico NetworkPolicy | API 组/资源不同，规则语义也不同 |
| - | GlobalNetworkPolicy | 群集范围策略（Calico 专属） |
| - | Tier | 策略层级（Calico 专属） |
| Service CIDR | N/A | Calico 遵循 Kubernetes Service CIDR |
| Pod CIDR | 使用 Calico IPAM 时为 IPPool | 不是 Node PodCIDR 的别名，也不一定自动匹配 |
| Node | Calico Node | 关联节点数据；生命周期和表示方式取决于 datastore |
| Namespace | Namespace | Calico 策略可按命名空间选择 |
| Labels | Labels | 标签语法相同，可用于选择器 |
| Pod 网络接口 | WorkloadEndpoint | 不是 Service Endpoint/EndpointSlice，也不包含所有已应用策略的清单 |
| - | HostEndpoint | 主机接口策略（Calico 专属） |

---

## Calico 与 Cilium 术语对照

以下是功能层面的对照，并不表示资源可互换或功能保证。迁移策略前应核对模式、平台和安装版本。

| 概念 | Calico | Cilium 1.20.1 对照 |
| --- | --- | --- |
| 节点代理 | Felix | Cilium Agent |
| BGP | 启用 BGP 的配置中使用 BIRD | 内置 BGP Control Plane 可发布可达性；它不会编程数据路径，也不会建立内部路由 |
| Datastore 扇出 | Typha | 没有完全对应的 Typha 组件/API |
| Pod IP 分配 | IPPool + 所选 IPAM | 取决于 Cilium IPAM 模式，并非单一通用池 API |
| 命名空间级策略 | Calico NetworkPolicy | CiliumNetworkPolicy；两者都不同于标准 Kubernetes NetworkPolicy |
| 群集级策略 | GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy；规则和排序语义不同 |
| 可复用外部 CIDR | NetworkSet / GlobalNetworkSet | 群集级 CiliumCIDRGroup，在 CIDR 规则中通过 cidrGroupRef 或 cidrGroupSelector 引用；不是 CiliumIPSet |
| 策略 Tier | Calico Tier | 没有完全对应的 Calico Tier API；其他策略 API 有自己的排序规则 |
| 工作负载接口 | WorkloadEndpoint | CiliumEndpoint，生命周期/状态语义不同 |
| 主机保护 | HostEndpoint 策略，包括已配置的转发规则 | 使用 nodeSelector 策略的 Linux host firewall；转发范围并不相同 |
| 数据平面 | Linux Iptables/Nftables/BPF；Windows HNS | Linux eBPF 有自身要求；不能据此将 Windows 描述为受支持的 Beta 版本 |
| 加密 | OSS WireGuard，适用于受支持的对等路径 | WireGuard 或 IPsec，限制取决于模式和平台 |
| L7 策略 | 文档记录了面向 OSS 的独立 Istio/Envoy/Dikastes 集成 | 基于 Envoy 的策略功能，各有前提条件 |
| 流可视性 | Goldmane/Whisker 和组件指标 | Hubble 和组件指标 |
| 控制器 | kube-controllers / Tigera Operator | Cilium Operator；职责并非一一对应 |
| CLI | calicoctl | cilium 与节点侧 cilium-dbg 职责不同 |

Calico 支持的 Windows 功能范围小于 Linux；例如，仅限文档所述的 IPv4 HNS 和 VXLAN/BGP 限制，并不具备 WireGuard/eBPF/HostEndpoint 的功能对等性。这里没有证据支持无条件的性能、成熟度或社区规模排名。应针对具体工作负载和运维要求进行比较。

---

## 交叉引用

### 架构深入解析
- **Felix**：请参阅 [第 2 部分：架构](02-architecture.md)
- **BGP 配置**：请参阅 [第 4 部分：BGP 深入解析](04-bgp-deep-dive.md)
- **Typha 扩展**：请参阅 [第 7 部分：高级主题](07-advanced-topics.md)

### 网络策略
- **Kubernetes NetworkPolicy**：请参阅 [第 5 部分：网络策略](05-network-policy.md)
- **GlobalNetworkPolicy**：请参阅 [第 5 部分：网络策略](05-network-policy.md)
- **基于 Tier 的策略**：请参阅 [第 5 部分：网络策略](05-network-policy.md)

### 运维
- **安装方式**：请参阅 [第 9 部分：运维](09-operations.md)
- **calicoctl 命令**：请参阅 [第 9 部分：运维](09-operations.md)
- **故障排查**：请参阅 [第 9 部分：运维](09-operations.md)

### EKS 集成
- **VPC CNI + Calico**：请参阅 [第 8 部分：EKS 集成](08-eks-integration.md)
- **安装方式**：请参阅 [第 8 部分：EKS 集成](08-eks-integration.md)

---

## 主要参考资料

- [Calico 资源参考](https://docs.tigera.io/calico/latest/reference/resources/)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu)
- [RFC 6996 私有 ASN](https://www.rfc-editor.org/rfc/rfc6996.txt)
- [Cilium CIDR group API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/v2/cidrgroups_types.go)
- [Cilium BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Cilium host firewall](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/host-firewall.rst)

## 测验

要测试你在本章学到的内容，请尝试[术语表测验](../../quizzes/networking/calico/glossary-quiz.md)。
