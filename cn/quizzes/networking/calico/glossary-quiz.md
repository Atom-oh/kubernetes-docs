# Calico 术语测验

> **相关文档**: [Calico 术语表](../../../networking/calico/glossary.md)
> **最后更新**: 2026 年 9 月 12 日

## 测验

1. Felix 在 Calico 架构中的主要职责是什么？
   - A) 管理 etcd 数据库
   - B) 在每个节点上编写网络策略规则和路由
   - C) 对服务流量进行负载均衡
   - D) 为服务解析 DNS

<details>
<summary>显示答案</summary>

**答案：B) 在每个节点上编写网络策略规则和路由**

**说明：**
Felix 会在每个节点上配置所选策略数据平面及相关路由。CNI 插件负责创建和配置普通 Pod 网络接口，并调用 IPAM；Felix 跟踪端点状态并配置规则，而不是在用户空间转发每个数据包。

</details>

2. BIRD 代表什么？它在 Calico 中的作用是什么？
   - A) Binary Internet Routing Daemon（互联网路由守护进程）——管理容器 DNS
   - B) BIRD Internet Routing Daemon（BIRD 互联网路由守护进程）——通过 BGP 分发路由信息
   - C) Basic Internal Route Distribution（基本内部路由分发）——处理服务发现
   - D) Broadcast IP Routing Distributor（广播 IP 路由分发器）——管理组播流量

<details>
<summary>显示答案</summary>

**答案：B) BIRD Internet Routing Daemon（BIRD 互联网路由守护进程）——通过 BGP 分发路由信息**

**说明：**
在启用了 BGP 的 Calico 配置中，BIRD 负责通过 BGP 交换路由。路由和封装设计决定流量采用直接路由还是隧道传输；仅仅存在 BGP 并不代表没有覆盖网络。

</details>

3. Typha 在 Calico 部署中的作用是什么？
   - A) 加密 Pod 之间的流量
   - B) 缓存数据存储更新，并将其分发给各个 Felix 实例
   - C) 提供入口流量负载均衡
   - D) 管理证书轮换

<details>
<summary>显示答案</summary>

**答案：B) 缓存数据存储更新，并将其分发给各个 Felix 实例**

**说明：**
Typha 会缓存并分发数据存储中的变更，从而减少每个客户端的 watch 负载。它可以有多个副本，也支持不同的同步器和 watch 类型；它并非统一的单一 watch，也不是策略联邦服务。Typha 的扩缩容由已安装配置中的 operator 管理。

</details>

4. Calico 中 IPPool 与 IPAM 有什么区别？
   - A) 两者只是同一事物的不同名称
   - B) IPPool 定义可用的 CIDR 范围；IPAM 管理从这些范围中分配地址
   - C) IPPool 用于 IPv4，IPAM 用于 IPv6
   - D) IPPool 已弃用，现由 IPAM 取代

<details>
<summary>显示答案</summary>

**答案：B) IPPool 定义可用的 CIDR 范围；IPAM 管理从这些范围中分配地址**

**说明：**
IPPool 定义地址范围，以及封装、NAT 和分配资格等设置。Calico IPAM 会从符合条件的池中为受支持的用途分配地址。它不是 VPC CNI 仅策略模式使用的地址分配器，IPPool 也不是 Kubernetes Node PodCIDR 的别名。

</details>

5. GlobalNetworkPolicy 与 Kubernetes NetworkPolicy 有什么区别？
   - A) GlobalNetworkPolicy 仅适用于 IPv6
   - B) GlobalNetworkPolicy 的作用域是集群，并支持 tier 和拒绝规则等其他功能
   - C) GlobalNetworkPolicy 与 Kubernetes NetworkPolicy 一样，作用域仅限命名空间
   - D) GlobalNetworkPolicy 已弃用

<details>
<summary>显示答案</summary>

**答案：B) GlobalNetworkPolicy 的作用域是集群，并支持 tier 和拒绝规则等其他功能**

**说明：**
GlobalNetworkPolicy 的作用域是集群，选择器决定它会影响哪些工作负载或主机端点。它还支持 Calico 的动作、顺序和 tier；但它不会自动影响所有 Pod，也不会在缺少所需集成时启用 L7 检查。

</details>

6. Calico 策略模型中的 Tier 是什么？
   - A) 用于隔离流量的网络分段
   - B) 控制策略评估顺序的分层分组
   - C) Calico Enterprise 的定价级别
   - D) 一种网络加密类型

<details>
<summary>显示答案</summary>

**答案：B) 控制策略评估顺序的分层分组**

**说明：**
Tier 按优先级组织策略。数值较小的 tier order 会先评估；随后再按 tier 内的策略 order 评估。Allow 和 Deny 是终止动作；Pass 会将处理交给下一个适用的 tier，最终继续到 profiles。安全、平台或应用等 tier 名称由用户定义，并非必需的默认层级。

</details>

7. Calico 中的 WorkloadEndpoint 表示什么？
   - A) Kubernetes Service 的端点
   - B) 与 Pod 或 VM 工作负载关联的网络接口
   - C) 外部 API 端点
   - D) 存储挂载点

<details>
<summary>显示答案</summary>

**答案：B) 与 Pod 或 VM 工作负载关联的网络接口**

**说明：**
WorkloadEndpoint 表示工作负载的网络接口，包含 IP、MAC 和接口信息、标签以及用于计算策略的 profile 引用。其生命周期通常由插件或编排器管理。它不是 Service 的 EndpointSlice，也不是已存储的全部有效策略决策清单。

</details>

8. Calico 中 BGPPeer 与 BGPConfiguration 有什么关系？
   - A) 两者是同一资源的别名
   - B) BGPConfiguration 设置全局 BGP 参数；BGPPeer 定义特定的对等会话
   - C) BGPPeer 用于内部对等体，BGPConfiguration 用于外部对等体
   - D) BGPConfiguration 已弃用，现由 BGPPeer 取代

<details>
<summary>显示答案</summary>

**答案：B) BGPConfiguration 设置全局 BGP 参数；BGPPeer 定义特定的对等会话**

**说明：**
默认 BGPConfiguration 定义集群级默认值，例如 ASN、网格和服务通告设置；受支持的节点级覆盖项则单独配置。BGPPeer 用于通过对等体地址或选择器指定预期的对等关系，但它不保证会话或所需路由已经建立。

</details>

9. Calico 中的 NetworkSet 是什么？它在 Cilium 中的对应概念是什么？
   - A) 一组 Service；对应 Cilium ServiceGroup
   - B) 带标签的 IP/CIDR 集合；CiliumCIDRGroup 与之相关
   - C) 一组命名空间；对应 Cilium ClusterPolicy
   - D) DNS 区域配置；对应 Cilium DNSPolicy

<details>
<summary>显示答案</summary>

**答案：B) 带标签的 IP/CIDR 集合；CiliumCIDRGroup 与之相关**

**说明：**
NetworkSet 的作用域是命名空间，而 GlobalNetworkSet 的作用域是集群；两者都提供带标签的 IP/CIDR 集合。CiliumCIDRGroup 的作用域是集群，可在 Cilium CIDR 规则中通过 cidrGroupRef 或 cidrGroupSelector 引用。两者属于相关概念，但 API 不同，清单不能互换。

</details>

10. Calico 中 HostEndpoint 的用途是什么？
    - A) 定义容器端点
    - B) 将网络策略应用于主机接口（非 Pod 流量）
    - C) 为主机配置 DNS
    - D) 管理节点标签

<details>
<summary>显示答案</summary>

**答案：B) 将网络策略应用于主机接口（非 Pod 流量）**

**说明：**
HostEndpoint 表示主机接口，可用于对主机流量以及配置后的转发流量应用策略。在创建或启用 HostEndpoint 前，应检查 profiles、failsafe 规则和管理路径。工作负载策略与主机策略的作用域不同，但转发的 Pod 流量也可能受到影响。

</details>
