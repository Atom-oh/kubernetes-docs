# Calico 术语测验

> **相关文档**: [Calico 术语表](../../../networking/calico/glossary.md)
> **最后更新**: February 22, 2026

## 测验

1. Felix 在 Calico 架构中的主要职责是什么？
   - A) 管理 etcd 数据库
   - B) 在每个 node 上配置 network policy rules 和 routes
   - C) 对 Service traffic 进行负载均衡
   - D) 为 Service 提供 DNS resolution

<details>
<summary>显示答案</summary>

**答案：B) 在每个 node 上配置 network policy rules 和 routes**

**说明：**
Felix 是 Calico 的每 node agent（作为 DaemonSet 运行），负责在每个 node 上配置 network policy rules（iptables 或 eBPF）、routes 和 ACLs。它会监视 datastore 中的 policy 和 endpoint 更新，并将其转换为 kernel-level rules。

</details>

2. BIRD 代表什么，它在 Calico 中的功能是什么？
   - A) Binary Internet Routing Daemon - 管理 container DNS
   - B) BIRD Internet Routing Daemon - 通过 BGP 分发 routing information
   - C) Basic Internal Route Distribution - 处理 Service discovery
   - D) Broadcast IP Routing Distributor - 管理 multicast traffic

<details>
<summary>显示答案</summary>

**答案：B) BIRD Internet Routing Daemon - 通过 BGP 分发 routing information**

**说明：**
BIRD（BIRD Internet Routing Daemon - 一个递归首字母缩略词）是 Calico 用于在 nodes 之间分发 routing information 的 BGP daemon。它建立 BGP peering sessions 并通告 Pod CIDR routes，从而无需 overlay encapsulation 即可实现直接的 Pod-to-Pod communication。

</details>

3. Typha 在 Calico deployments 中的功能是什么？
   - A) 加密 Pod-to-Pod traffic
   - B) 缓存 datastore updates 并将其扇出到 Felix instances
   - C) 提供 ingress load balancing
   - D) 管理 certificate rotation

<details>
<summary>显示答案</summary>

**答案：B) 缓存 datastore updates 并将其扇出到 Felix instances**

**说明：**
Typha 作为 Felix instances 与 datastore（Kubernetes API 或 etcd）之间的 caching proxy。它通过将多个 Felix instances 的 watches 聚合为单个 watch 来减少 datastore load，然后将 updates 分发给所有已连接的 Felix daemons。

</details>

4. Calico 中 IPPool 与 IPAM 的区别是什么？
   - A) 它们是同一事物的不同名称
   - B) IPPool 定义可用的 CIDR ranges；IPAM 管理从这些 ranges 中进行 allocation
   - C) IPPool 用于 IPv4，IPAM 用于 IPv6
   - D) IPPool 已弃用，由 IPAM 取代

<details>
<summary>显示答案</summary>

**答案：B) IPPool 定义可用的 CIDR ranges；IPAM 管理从这些 ranges 中进行 allocation**

**说明：**
IPPool 是一种 Calico resource，用于定义可供 Pod allocation 的 IP address range（CIDR），以及 NAT 和 encapsulation settings 等配置。IPAM（IP Address Management）是负责将这些 pools 中的 individual IP 实际分配给 Pods 和 nodes 的系统。

</details>

5. GlobalNetworkPolicy 与 Kubernetes NetworkPolicy 有何不同？
   - A) GlobalNetworkPolicy 仅适用于 IPv6
   - B) GlobalNetworkPolicy 具有 cluster scope，并支持 tiers 和 deny rules 等附加功能
   - C) GlobalNetworkPolicy 与 Kubernetes NetworkPolicy 一样具有 namespace scope
   - D) GlobalNetworkPolicy 已弃用

<details>
<summary>显示答案</summary>

**答案：B) GlobalNetworkPolicy 具有 cluster scope，并支持 tiers 和 deny rules 等附加功能**

**说明：**
GlobalNetworkPolicy 是一种 Calico-specific resource，可在没有 namespace restrictions 的情况下应用于整个 cluster。与 Kubernetes NetworkPolicy 不同，它支持显式 deny rules、用于排序的 policy tiers、application-layer（L7）rules，以及用于 HostEndpoints 等 non-namespaced resources 的 selectors。

</details>

6. Calico policy model 中的 Tier 是什么？
   - A) 用于隔离 traffic 的 network segment
   - B) 控制 policy evaluation order 的 hierarchical grouping
   - C) Calico Enterprise 的 pricing level
   - D) 一种 network encryption

<details>
<summary>显示答案</summary>

**答案：B) 控制 policy evaluation order 的 hierarchical grouping**

**说明：**
Tiers 提供了一种组织和排序 Calico network policies 的方式。较高 order tiers 中的 policies 会在较低 order tiers 之前进行 evaluation。这支持诸如优先于 application-team policies 的 platform-level security policies 等模式，并支持 multi-tenant policy management。

</details>

7. WorkloadEndpoint 在 Calico 中代表什么？
   - A) 一个 Kubernetes Service endpoint
   - B) 与 Pod 或 VM workload 关联的 network interface
   - C) 一个 external API endpoint
   - D) 一个 storage mount point

<details>
<summary>显示答案</summary>

**答案：B) 与 Pod 或 VM workload 关联的 network interface**

**说明：**
WorkloadEndpoint 表示附加到 workload（Pod、VM 或 container）的 network interface。它包含有关 interface 的 IP addresses、其运行所在的 host、用于 policy selection 的 labels，以及应用于它的 profile/policies 的信息。Calico 会自动为 Pods 创建 WorkloadEndpoints。

</details>

8. Calico 中 BGPPeer 与 BGPConfiguration 的关系是什么？
   - A) 它们是同一 resource 的别名
   - B) BGPConfiguration 设置全局 BGP settings；BGPPeer 定义特定的 peering sessions
   - C) BGPPeer 用于 internal peers，BGPConfiguration 用于 external peers
   - D) BGPConfiguration 已弃用，由 BGPPeer 取代

<details>
<summary>显示答案</summary>

**答案：B) BGPConfiguration 设置全局 BGP settings；BGPPeer 定义特定的 peering sessions**

**说明：**
BGPConfiguration 是一种 global resource，用于定义 cluster-wide BGP settings，例如 AS number、node-to-node mesh enablement 和 logging。BGPPeer resources 用于定义与 external routers 或 route reflectors 的特定 BGP peering relationships，包括其 IP addresses、AS numbers 和 node selectors。

</details>

9. Calico 中的 NetworkSet 是什么，它在 Cilium 中的等价物是什么？
   - A) 一组 Services；等价于 Cilium ServiceGroup
   - B) 用于 policies 的命名 IP addresses/CIDRs 集合；类似于具有 CIDR rules 的 Cilium CiliumNetworkPolicy
   - C) 一组 namespaces；等价于 Cilium ClusterPolicy
   - D) 一个 DNS zone configuration；等价于 Cilium DNSPolicy

<details>
<summary>显示答案</summary>

**答案：B) 用于 policies 的命名 IP addresses/CIDRs 集合；类似于具有 CIDR rules 的 Cilium CiliumNetworkPolicy**

**说明：**
NetworkSet 是一种 Calico resource，用于定义可在 network policies 中引用的命名 IP addresses、CIDRs 或 domains 集合。当同一组 external IPs 出现在多个 policies 中时，这可简化 policy management。Cilium 通过 CiliumNetworkPolicy 中基于 CIDR 的 rules 实现类似功能。

</details>

10. Calico 中 HostEndpoint 的用途是什么？
    - A) 定义 container endpoints
    - B) 将 network policies 应用于 host interfaces（non-Pod traffic）
    - C) 为 host 配置 DNS
    - D) 管理 node labels

<details>
<summary>显示答案</summary>

**答案：B) 将 network policies 应用于 host interfaces（non-Pod traffic）**

**说明：**
HostEndpoint 表示 host node 本身上的 network interface（不是 Pod）。它使 Calico network policies 能够控制进出 host processes 的 traffic，从而保护 kubelet、SSH 或其他不作为 Pods 运行的 system daemons 等 node-level services。

</details>
