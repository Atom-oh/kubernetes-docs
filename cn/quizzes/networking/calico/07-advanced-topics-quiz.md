# 高级主题测验

> **相关文档**: [高级主题](../../../networking/calico/07-advanced-topics.md)
> **最后更新**: February 22, 2026

## 测验

1. 在 Calico 基于块的 IPAM 中，一个 /26 CIDR 块提供多少个 IP 地址？
   - A) 32 个 IP
   - B) 64 个 IP
   - C) 128 个 IP
   - D) 256 个 IP

<details>
<summary>显示答案</summary>

**答案：B) 64 个 IP**

**说明：**
一个 /26 CIDR 块提供 64 个 IP 地址 (2^(32-26) = 2^6 = 64)。Calico 向 Node 分配可配置大小的 IP 块，然后从这些块中为 Pod 分配单独的 IP。默认块大小为 /26，可在效率与 IP 利用率之间取得平衡。

</details>

2. Calico 的 IPAM 中的 IP 块亲和性是什么？
   - A) 具有相同标签的 Pod 始终从同一块获取 IP
   - B) Node 认领并优先使用特定 IP 块
   - C) 为 Service 分配靠近其端点的 IP
   - D) 按可用区对 IP 地址分组

<details>
<summary>显示答案</summary>

**答案：B) Node 认领并优先使用特定 IP 块**

**说明：**
IP 块亲和性意味着，当 Node 需要分配 Pod IP 时，它会认领一个或多个 IP 块，并优先从这些块中进行分配。这可提高路由效率，因为一个 Node 上的所有 Pod 通常共享相同的 IP 前缀，从而能够进行路由聚合。

</details>

3. 如何在 Calico 中激活 WireGuard 加密？
   - A) 安装单独的 WireGuard operator
   - B) 在 FelixConfiguration 中设置 wireguardEnabled: true
   - C) 应用 WireGuard NetworkPolicy
   - D) 在 Kubernetes API server 标志中启用它

<details>
<summary>显示答案</summary>

**答案：B) 在 FelixConfiguration 中设置 wireguardEnabled: true**

**说明：**
通过在 FelixConfiguration 资源中设置 `wireguardEnabled: true` 启用 WireGuard 加密。Calico 会自动管理 Node 之间的 WireGuard 密钥生成和分发，为跨 Node 的 Pod 间流量创建加密隧道。

</details>

4. 与使用 IPsec 加密 Pod 流量相比，WireGuard 的一项关键优势是什么？
   - A) WireGuard 支持更多加密算法
   - B) WireGuard 配置更简单且 CPU 开销更低
   - C) WireGuard 无需内核支持即可工作
   - D) WireGuard 提供更好的压缩

<details>
<summary>显示答案</summary>

**答案：B) WireGuard 配置更简单且 CPU 开销更低**

**说明：**
与 IPsec 相比，WireGuard 提供更简单的配置和更少的选项（可降低配置错误风险），并且通常具有更低的 CPU 开销。它使用现代加密原语，代码库更小，因此更易于审计和维护。

</details>

5. Calico 的 Egress Gateway 功能的主要使用场景是什么？
   - A) 对进入 Service 的流量进行负载均衡
   - B) 为访问外部 Service 的 Pod 提供一致的源 IP
   - C) 缓存 DNS 响应以加快解析
   - D) 限制出站 API 调用的速率

<details>
<summary>显示答案</summary>

**答案：B) 为访问外部 Service 的 Pod 提供一致的源 IP**

**说明：**
Egress Gateway 允许 Pod 使用一致且可预测的源 IP 地址访问外部 Service。当外部 Service 使用基于 IP 的允许列表时，这一点至关重要，因为它可确保来自特定 Pod 的流量始终显示为来自已知的网关 IP。

</details>

6. Calico 的多集群联邦提供什么能力？
   - A) 在集群之间自动故障转移
   - B) 跨集群共享网络策略和 Service 发现
   - C) 为所有集群提供集中式日志记录
   - D) 跨集群统一计费

<details>
<summary>显示答案</summary>

**答案：B) 跨集群共享网络策略和 Service 发现**

**说明：**
多集群联邦使 Calico 能够共享网络策略、启用跨集群 Service 发现，并在多个 Kubernetes 集群中提供一致的网络。这使不同集群中的工作负载能够使用统一策略安全通信。

</details>

7. 关于 Calico 的 Windows 支持，哪项陈述是正确的？
   - A) Windows Node 需要不同的 CNI plugin
   - B) Calico 支持 Windows Node，但存在一些功能限制
   - C) Windows 支持仅在 Calico Enterprise 中提供
   - D) Windows Node 无法参与 BGP peering

<details>
<summary>显示答案</summary>

**答案：B) Calico 支持 Windows Node，但存在一些功能限制**

**说明：**
Calico 支持 Kubernetes 集群中的 Windows Node，从而支持混合 Linux/Windows 环境。不过，由于操作系统差异，Windows 上不支持 eBPF dataplane 等部分功能。Windows 支持涵盖基本网络和网络策略执行。

</details>

8. Calico Enterprise 与 Calico Open Source 之间的一项关键差异是什么？
   - A) Enterprise 使用不同的 dataplane 技术
   - B) Enterprise 包含额外的安全性、合规性和可观测性功能
   - C) Enterprise 仅适用于特定 Kubernetes 发行版
   - D) Enterprise 不支持 BGP

<details>
<summary>显示答案</summary>

**答案：B) Enterprise 包含额外的安全性、合规性和可观测性功能**

**说明：**
Calico Enterprise 构建于开源项目之上，并添加了分层策略层级、流量可视化、合规性报告、威胁防御和企业支持等功能。两个版本使用相同的核心网络 dataplane。

</details>

9. 大型 Calico 部署的 Typha 容量规划公式是什么？
   - A) 每 100 个 Node 使用 1 个 Typha
   - B) 每 500 个 Node 使用 1 个 Typha，HA 至少使用 3 个
   - C) Typha 副本数 = Node 数 / 200，建议用于 1000+ Node 集群
   - D) 无论集群大小如何，固定为 5 个副本

<details>
<summary>显示答案</summary>

**答案：C) Typha 副本数 = Node 数 / 200，建议用于 1000+ Node 集群**

**说明：**
对于拥有 1000+ 个 Node 的集群，Typha 对于可扩展性至关重要。通用容量规划公式约为每 200 个 Node 配置 1 个 Typha 副本，且高可用性至少需要 3 个副本。Typha 将 datastore 更新扇出到 Felix 实例，从而降低 API server 负载。

</details>

10. Calico 支持 IPv6 和双栈网络需要什么？
    - A) 单独进行特定于 IPv6 的安装
    - B) 为 IPv4 和 IPv6 地址范围配置 IPPool
    - C) 仅使用 eBPF dataplane
    - D) 禁用网络策略执行

<details>
<summary>显示答案</summary>

**答案：B) 为 IPv4 和 IPv6 地址范围配置 IPPool**

**说明：**
Calico 中的双栈支持要求同时为 IPv4 和 IPv6 CIDR 范围配置 IPPool。之后，Pod 可以从两个池中获取地址。集群还必须在 Kubernetes 层面启用双栈，底层基础设施也必须支持 IPv6。

</details>

11. 如何检测 Calico IPAM 中的 IP 地址耗尽？
    - A) 检查 kube-apiserver 日志
    - B) 使用 calicoctl ipam show 查看分配状态
    - C) 监控 Node 内存使用情况
    - D) 检查 Pod 重启次数

<details>
<summary>显示答案</summary>

**答案：B) 使用 calicoctl ipam show 查看分配状态**

**说明：**
`calicoctl ipam show` 命令显示 IPAM 分配状态，包括所有池和块中的 IP 总数、已分配 IP 和可用 IP。`--show-blocks` 标志提供详细的每 Node 块分配信息，有助于识别耗尽问题。

</details>

12. 何时应选择 etcd 作为 Calico 的 datastore，而不是 Kubernetes API？
    - A) 对于少于 100 个 Node 的集群
    - B) 在托管 Kubernetes Service 中运行时
    - C) 对于非常大的集群或非 Kubernetes 部署
    - D) 使用 eBPF dataplane 时

<details>
<summary>显示答案</summary>

**答案：C) 对于非常大的集群或非 Kubernetes 部署**

**说明：**
etcd datastore 建议用于 Kubernetes API server 负载令人担忧的超大型集群，或非 Kubernetes 部署（裸机、VM）。对于大多数 Kubernetes 部署，Kubernetes datastore 更简单，因为无需管理单独的 etcd 集群。

</details>
