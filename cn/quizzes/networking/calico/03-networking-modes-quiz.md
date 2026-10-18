# Calico 网络模式测验

> **相关文档**：[Calico 网络模式](../../../networking/calico/03-networking-modes.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. 对于没有选项的外层 IPv4 头，Calico IPIP 会增加多少字节的头部开销？
   - A) 8 字节
   - B) 20 字节
   - C) 50 字节
   - D) 100 字节

<details>
<summary>显示答案</summary>

**答案：B) 20 字节**

**说明**：
不含选项的外层 IPv4 头会增加 20 字节。Calico IPIP 仅支持 IPv4。较小的头部会为有效负载留出更多空间，但这本身并不能证明在所有网卡、内核和工作负载上都能降低延迟或提高吞吐量。

</details>

2. 对于外层 IPv4 VXLAN，且没有额外的内层 VLAN 标签，Pod IP 数据包之外会增加多少开销？
   - A) 20 字节
   - B) 30 字节
   - C) 50 字节
   - D) 64 字节

<details>
<summary>显示答案</summary>

**答案：C) 50 字节**

**说明**：
这 50 字节由外层 IPv4 20 字节、UDP 8 字节、VXLAN 8 字节和内层以太网 14 字节组成。外层以太网头不计入 underlay IP MTU。外层使用 IPv6 时开销为 70 字节。TCP 和 UDP 的内层传输层头大小也不同。

</details>

3. Calico 的 CrossSubnet 模式有什么作用？
   - A) 始终使用封装
   - B) 从不使用封装
   - C) 仅对跨子网流量进行封装
   - D) 仅对同一子网内的流量进行封装

<details>
<summary>显示答案</summary>

**答案：C) 仅对跨子网流量进行封装**

**说明**：
CrossSubnet 会比较相关节点地址和配置的子网掩码。同一子网内的节点间流量可以不经过封装；不同节点子网之间的流量则使用所选的 IPIP/VXLAN 封装。它不会检测可用区或区域，也不会建立站点间连接。

</details>

4. Direct（不封装）路由模式需要满足什么条件？
   - A) 需要特殊硬件网卡
   - B) Underlay 网络必须能够路由 Pod CIDR 流量
   - C) 内核版本必须为 5.0 或更高
   - D) 必须启用 eBPF 模式

<details>
<summary>显示答案</summary>

**答案：B) Underlay 网络必须能够路由 Pod CIDR 流量**

**说明**：
Underlay 及其返回路径必须能够路由 Pod 地址。BGP 是一种实现方式，但也可以使用静态路由和 Felix 支持的 cluster route 编程。Calico 3.32 的 operator `clusterRoutingMode` 可选择由 Felix 编程非 VXLAN 的集群路由；对外发布 BGP 路由仍需要 BGP。

</details>

5. 以下哪项 IPIP 与 VXLAN 性能比较有依据？
   - A) VXLAN 总是更快
   - B) 性能取决于实际网卡/卸载能力、内核/数据平面、数据包大小、路由和工作负载
   - C) 两者性能完全相同
   - D) 只有 Kubernetes 版本决定性能

<details>
<summary>显示答案</summary>

**答案：B) 性能取决于实际网卡/卸载能力、内核/数据平面、数据包大小、路由和工作负载**

**说明**：
IPIP 的 IPv4 封装头较小，但卸载能力和实现细节也会影响性能。没有哪种模式在所有情况下都最快。早先的中英双语基准测试记录彼此不一致，且缺少完整来源信息，因此这里只将其视为报告，不把它们作为性能保证。

</details>

6. IPPool 中的 ipipMode 可以使用哪些有效选项？
   - A) On、Off
   - B) True、False
   - C) Always、CrossSubnet、Never
   - D) Enabled、Disabled、Auto

<details>
<summary>显示答案</summary>

**答案：C) Always、CrossSubnet、Never**

**说明**：
ipipMode 和 vxlanMode 都接受 Always、CrossSubnet 和 Never。Always 适用于符合条件的节点间流量，不代表同一节点上的 Pod 也会建立物理隧道。Operator pool 使用单独的封装字段，值例如 IPIPCrossSubnet 或 VXLANCrossSubnet；不要混淆这两种 API。

</details>

7. IPPool 中的 natOutgoing 设置控制什么？
   - A) Pod 是否可以接收经过 NAT 的入站流量
   - B) 是否对该 pool 中发往所有 Calico IPPool 之外目标地址的符合条件的流量执行源 NAT
   - C) 是否在 Pod 之间执行 NAT
   - D) 节点是否为外部 Service 执行 NAT

<details>
<summary>显示答案</summary>

**答案：B) 是否对该 pool 中发往所有 Calico IPPool 之外目标地址的符合条件的流量执行源 NAT**

**说明**：
通常判断条件是目标地址是否位于所有 Calico IPPool 之外，而不只是是否位于集群之外。已禁用的 pool 仍可定义不执行 NAT 的目标地址范围；额外的 Felix 排除项还可以包括主机 IP。NAT 不会授权流量，也不能保证外部返回路由可用。

</details>

8. Calico VXLAN 默认使用哪个 UDP 端口？
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>显示答案</summary>

**答案：A) 4789**

**说明**：
Calico 的默认端口是 UDP 4789，且可以配置。其他当前使用的 VXLAN 实现可能使用 8472；这并非只是一种已过时端口的约定。IPIP 使用 IP 协议 4，而非 TCP/UDP 端口。

</details>

9. 为什么 Calico overlay 指南建议在 Azure 上为 Calico 自主管理网络选择合适的 VXLAN 配置，而不是使用 IPIP？
   - A) Azure 提供 VXLAN 硬件加速
   - B) Calico overlay 指南指出 Azure 支持 VXLAN，但不支持 IPIP
   - C) Azure 策略要求使用 VXLAN
   - D) Azure 会自动配置 VXLAN

<details>
<summary>显示答案</summary>

**答案：B) Calico overlay 指南指出 Azure 支持 VXLAN，但不支持 IPIP**

**说明**：
这是 Calico 网络支持范围的限制，并不代表每个 AKS 部署都应安装 Calico overlay。应根据实际云服务商的 CNI 和策略集成来选择方案。添加 UDR 也不会使原本不受支持的 IPIP 封装方式变为受支持。

</details>

10. Underlay IP MTU 实际为 1500 字节、使用外层 IPv4 且没有其他封装时，VXLAN 的 Pod IP MTU 预算是多少？
   - A) 将 Pod MTU 设为 1500
   - B) 1450 字节：1500 减去 50
   - C) 设为 1500，因为自动检测会消除封装开销
   - D) 将 Pod MTU 设为 1400

<details>
<summary>显示答案</summary>

**答案：B) 1450 字节：1500 减去 50**

**说明**：
在这些假设下，IPv4 VXLAN 的开销为 50 字节，因此 Pod IP 数据包可使用 1450 字节。外层 IPv6、加密、较小的物理路径 MTU 或 eBPF Service 路径都可能改变这一预算。自动 MTU 检测可以选择一个值，但它必须反映实际使用的模式和路径。

</details>

11. 启用 IPIP 模式时，节点上会创建哪个接口？
   - A) vxlan.calico
   - B) tunl0
   - C) cali0
   - D) ipip0

<details>
<summary>显示答案</summary>

**答案：B) tunl0**

**说明**：
在此配置中，tunl0 通常是 Linux IPIP 隧道接口。它只与已启用且受支持的 IPIP 配置有关。该接口不提供加密，也不是所有 Calico 网络模式都会使用的接口。

</details>

12. 将地址迁移到另一个 Calico IPPool 时，应遵循哪项原则？
   - A) 直接更改 IPPool 配置
   - B) 确认新 pool 兼容且 CIDR 不重叠，控制新分配，迁移工作负载及依赖项，并在检查完成后再停用旧 pool
   - C) 同时重启所有节点
   - D) 不支持迁移，必须重建集群

<details>
<summary>显示答案</summary>

**答案：B) 确认新 pool 兼容且 CIDR 不重叠，控制新分配，迁移工作负载及依赖项，并在检查完成后再停用旧 pool**

**说明**：
CIDR/IPPool 迁移不同于只更改封装方式。应规划资源所有者、cluster CIDR 兼容性、MTU、旧的显式 pool 请求、剩余分配和应用发布顺序。Operator 的 nodeSelector `!all` 不会阻止显式请求的 pool。不要仅仅因为少量替换 Pod 已获得新地址就删除旧 pool；隧道或其他地址分配以及 NAT/路由影响可能仍然存在。

</details>

---

[学习材料](../../../networking/calico/03-networking-modes.md) | [上一份测验](02-architecture-quiz.md) | [下一份测验](04-bgp-deep-dive-quiz.md)
