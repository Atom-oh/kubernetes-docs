# Calico 网络模式测验

> **相关文档**: [Calico Networking Modes](../../../networking/calico/03-networking-modes.md)
> **最后更新**: February 22, 2026

## 测验

1. IPIP 封装会增加多少字节的开销？
   - A) 8 字节
   - B) 20 字节
   - C) 50 字节
   - D) 100 字节

<details>
<summary>显示答案</summary>

**答案：B) 20 字节**

**说明：**
IPIP（IP-in-IP）封装会为每个数据包增加 20 字节的开销。这是用于封装原始数据包的额外 IP header 的大小。与会增加 50 字节开销的 VXLAN 相比，它效率更高，因此在需要封装时，IPIP 的性能更好。

</details>

2. VXLAN 封装会增加多少字节的开销？
   - A) 20 字节
   - B) 30 字节
   - C) 50 字节
   - D) 64 字节

<details>
<summary>显示答案</summary>

**答案：C) 50 字节**

**说明：**
VXLAN 封装会为每个数据包增加约 50 字节的开销。这包括外层 Ethernet header（14 字节）、外层 IP header（20 字节）、UDP header（8 字节）以及 VXLAN header（8 字节）。尽管这比 IPIP 的 20 字节更多，但 VXLAN 与各种网络环境具有更好的兼容性。

</details>

3. Calico 中的 CrossSubnet 模式有什么作用？
   - A) 始终使用封装
   - B) 从不使用封装
   - C) 仅对跨子网流量使用封装
   - D) 仅对同一子网流量使用封装

<details>
<summary>显示答案</summary>

**答案：C) 仅对跨子网流量使用封装**

**说明：**
CrossSubnet 模式是一种优化方式，仅当流量跨越子网边界时才应用封装（IPIP 或 VXLAN）。同一子网中节点之间的流量使用不带封装的直接路由。这兼具两者的优点：在可能时使用直接路由，仅在必要时使用封装。

</details>

4. Direct（未封装）路由模式有哪些要求？
   - A) 专用硬件 NIC
   - B) 底层网络必须能够路由 Pod CIDR 流量
   - C) Kernel 版本为 5.0 或更高
   - D) 必须启用 eBPF 模式

<details>
<summary>显示答案</summary>

**答案：B) 底层网络必须能够路由 Pod CIDR 流量**

**说明：**
Direct 路由模式要求底层网络基础设施能够在节点之间路由 Pod CIDR 流量。这通常意味着使用 BGP 向网络基础设施通告 Pod 路由，或者配置静态路由。否则，目标为其他节点上 Pod IP 的数据包会被网络丢弃。

</details>

5. 哪种网络模式通常能提供更好的性能：IPIP 还是 VXLAN？
   - A) VXLAN 始终更快
   - B) IPIP 通常更快，因为其开销更低
   - C) 两者性能相同
   - D) 性能取决于 Kubernetes 版本

<details>
<summary>显示答案</summary>

**答案：B) IPIP 通常更快，因为其开销更低**

**说明：**
IPIP 通常比 VXLAN 性能更好，因为它的封装开销更低（20 字节对 50 字节）。更低的开销意味着实际有效负载数据有更多空间，并且封装/解封装所需的处理更少。不过，VXLAN 具有更广泛的兼容性和更好的硬件卸载支持。

</details>

6. IPPool 中 ipipMode 的有效选项是什么？
   - A) On, Off
   - B) True, False
   - C) Always, CrossSubnet, Never
   - D) Enabled, Disabled, Auto

<details>
<summary>显示答案</summary>

**答案：C) Always, CrossSubnet, Never**

**说明：**
IPPool 中的 ipipMode 字段接受三个值：`Always`（始终使用 IPIP 封装）、`CrossSubnet`（仅对跨子网流量使用 IPIP）和 `Never`（禁用 IPIP）。vxlanMode 也提供这些相同的选项，用于配置 VXLAN 封装行为。

</details>

7. IPPool 中的 natOutgoing 设置控制什么？
   - A) Pod 是否可以接收传入的 NAT 流量
   - B) 离开集群的 Pod 流量是否会被伪装
   - C) 是否在 Pod 之间应用 NAT
   - D) 节点是否为外部 Service 执行 NAT

<details>
<summary>显示答案</summary>

**答案：B) 离开集群的 Pod 流量是否会被伪装**

**说明：**
`natOutgoing` 设置控制来自此 IP pool 的 Pod 流量在离开集群时是否会被伪装（SNAT）。设为 true 时，出站流量的源 IP 会更改为节点的 IP，使 Pod 即使其 IP 无法在集群外路由，也能与外部资源通信。

</details>

8. VXLAN 默认使用哪个 UDP port？
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>显示答案</summary>

**答案：A) 4789**

**说明：**
按照 IANA 的规定，VXLAN 默认使用 UDP port 4789。这是在不同 VXLAN 实现中使用的标准 port。某些较早的实现（例如早期 Flannel 版本）使用 port 8472，但 Calico 遵循标准 port 4789。

</details>

9. 为什么在 Azure 环境中 VXLAN 可能比 IPIP 更受推荐？
   - A) Azure 提供 VXLAN 硬件加速
   - B) Azure 对 IPIP（IP protocol 4）的支持不佳
   - C) Azure policy 要求使用 VXLAN
   - D) Azure 会自动配置 VXLAN

<details>
<summary>显示答案</summary>

**答案：B) Azure 对 IPIP（IP protocol 4）的支持不佳**

**说明：**
Azure 对 IPIP 封装的支持有限，因为 IP protocol 4 可能会在 Azure 的网络中被阻止或出现问题。由于基于 UDP，VXLAN 在 Azure 环境中运行得更可靠。在 Azure Kubernetes Service（AKS）或 Azure VM 上部署 Calico 时，这是一个常见建议。

</details>

10. 在网络 MTU 标准为 1500 字节时使用 VXLAN 封装，应如何优化 MTU？
    - A) 将 Pod MTU 设为 1500
    - B) 将 Pod MTU 设为 1450（1500 - 50 字节开销）
    - C) MTU 调整是自动的
    - D) 将 Pod MTU 设为 1400

<details>
<summary>显示答案</summary>

**答案：B) 将 Pod MTU 设为 1450（1500 - 50 字节开销）**

**说明：**
当网络 MTU 为 1500 字节时使用 VXLAN，应将 Pod MTU 设为约 1450 字节（1500 - 50 字节 VXLAN 开销），以避免分片。对于 IPIP，Pod MTU 应为 1480 字节（1500 - 20 字节开销）。正确的 MTU 配置可避免由数据包分片导致的性能问题。

</details>

11. 启用 IPIP 模式时，会在节点上创建哪个 interface？
    - A) vxlan.calico
    - B) tunl0
    - C) cali0
    - D) ipip0

<details>
<summary>显示答案</summary>

**答案：B) tunl0**

**说明：**
启用 IPIP 模式后，Calico 会在每个节点上创建 `tunl0` tunnel interface。该 interface 用于节点之间流量的 IPIP 封装。tunl0 interface 会在数据包进入和离开 IPIP tunnel 时处理其封装和解封装。

</details>

12. 在运行中的集群中从 IPIP 迁移到 VXLAN 模式的最佳实践是什么？
    - A) 直接更改 IPPool 配置
    - B) 使用 VXLAN 创建新的 IPPool，迁移 workloads，然后删除旧 pool
    - C) 同时重启所有节点
    - D) 不支持迁移；重新构建集群

<details>
<summary>显示答案</summary>

**答案：B) 使用 VXLAN 创建新的 IPPool，迁移 workloads，然后删除旧 pool**

**说明：**
在封装模式之间迁移的推荐方法是：使用所需设置创建新的 IPPool，逐步将 workloads 迁移到使用新 pool（通过重新创建 Pod 或使用 node selector），然后在迁移完成后删除旧 pool。这种方法可最大限度减少中断，并能在发生问题时进行回滚。

</details>

---

[返回学习资料](../../../networking/calico/03-networking-modes.md) | [上一测验：架构](./02-architecture-quiz.md) | [下一测验：BGP 深入探讨](./04-bgp-deep-dive-quiz.md)
