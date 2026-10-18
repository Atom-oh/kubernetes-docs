# 高级主题测验

> **相关文档**: [高级主题](../../../networking/calico/07-advanced-topics.md)
> **最后更新**: 2026 年 9 月 12 日

## 测验

1. 在 Calico 基于块的 IPAM 中，一个 /26 CIDR 块提供多少个 IP 地址？
   - A) 32 个 IP 地址
   - B) 64 个 IP 地址
   - C) 128 个 IP 地址
   - D) 256 个 IP 地址

<details>
<summary>显示答案</summary>

**答案：B) 64 个 IP 地址**

**说明：**
一个 IPv4 /26 包含 64 个地址，但这并不总是表示有 64 个可用的 Pod 地址：Calico Windows 会在自己拥有的每个块中预留四个地址。IPv6 默认使用 /122，同样包含 64 个地址。创建地址池时设置 blockSize；不能通过原地修改来调整它。

</details>

2. Calico IPAM 中的 IP 块亲和性是什么？
   - A) 具有相同标签的 Pod 始终从同一个块获取 IP
   - B) 节点认领特定 IP 块，并优先从中分配地址
   - C) 为 Service 分配靠近其端点的 IP
   - D) 按可用区对 IP 地址分组

<details>
<summary>显示答案</summary>

**答案：B) 节点认领特定 IP 块，并优先从中分配地址**

**说明：**
节点会优先从与自己具有关联关系的块中分配地址，但仍受地址池选择和限制约束。一个节点可以有多个块；允许借用地址时也可能生成更具体的路由。块亲和性不等同于 Node.spec.podCIDR，也不保证节点上的每个 Pod 都使用同一个前缀。

</details>

3. 如何在 Calico 中启用 WireGuard 加密？
   - A) 安装单独的 WireGuard operator
   - B) 在 FelixConfiguration 中设置 wireguardEnabled: true
   - C) 应用 WireGuard NetworkPolicy
   - D) 在 Kubernetes API server 参数中启用

<details>
<summary>显示答案</summary>

**答案：B) 在 FelixConfiguration 中设置 wireguardEnabled: true**

**说明：**
wireguardEnabled 启用受支持的 IPv4 路径；wireguardEnabledV6 是单独的设置。两端节点都需要兼容的内核和网络支持。Calico 会管理节点密钥并发布公钥。同一节点内的流量和不受支持的对端，不会自动通过节点间隧道加密。

</details>

4. 哪项描述符合 WireGuard 的设计，同时没有宣称其性能普遍优越？
   - A) WireGuard 支持更多加密算法
   - B) WireGuard 使用刻意精简的密码学设计和密钥配置
   - C) Calico WireGuard 无需节点或运行时前置条件
   - D) WireGuard 提供更好的压缩

<details>
<summary>显示答案</summary>

**答案：B) WireGuard 使用刻意精简的密码学设计和密钥配置**

**说明：**
WireGuard 刻意限制了可选的密码学方案。CPU 成本、吞吐量、漫游和卸载方面的比较取决于具体实现和工作负载。未经版本限定的代码行数，以及本章中未经验证的性能范围，都不能作为普遍的安全性或速度排名。

</details>

5. 文档所述 Calico Enterprise Egress Gateway 的主要用途是什么？
   - A) 对进入 Service 的流量进行负载均衡
   - B) 为访问外部 Service 的 Pod 提供稳定一致的源 IP
   - C) 缓存 DNS 响应以加快解析
   - D) 限制出站 API 调用的速率

<details>
<summary>显示答案</summary>

**答案：B) 为访问外部 Service 的 Pod 提供稳定一致的源 IP**

**说明：**
transit gateway Pod 会为所选客户端执行 SNAT，从而暴露一组受控的源地址。实际观察到的地址取决于地址池、上游 NAT 和可用性。NetworkPolicy Allow 和 BGP serviceExternalIPs 并不会创建这种路由/SNAT 行为。按源地址设置允许列表并不等于满足完整的合规要求或实现应用授权。

</details>

6. 当前 Calico Enterprise Federation 功能提供什么？
   - A) 自动复制应用数据库并实现故障转移
   - B) 远端端点身份和所选 Service 发现，同时仍在本地应用策略
   - C) 为所有集群集中记录日志
   - D) 跨集群统一计费

<details>
<summary>显示答案</summary>

**答案：B) 远端端点身份和所选 Service 发现，同时仍在本地应用策略**

**说明：**
Federated endpoint identity 会将远端端点信息纳入本地策略计算；它不会把远端策略复制到本地端点。单独的 Federated Services Controller 会读取远端 Kubernetes API。使用该功能的前提包括可路由且保留源地址的 Pod 路径，以及控制器凭证和配置；Typha 不是共享的 Federation Controller。

</details>

7. 关于 Calico 对 Windows 的支持，哪项说法正确？
   - A) Windows 节点必须使用不同的 CNI 插件
   - B) Calico 支持 Windows 节点，但部分功能受限
   - C) 只有 Calico Enterprise 支持 Windows
   - D) Windows 节点不能参与 BGP 对等连接

<details>
<summary>显示答案</summary>

**答案：B) Calico 支持 Windows 节点，但部分功能受限**

**说明：**
Calico Windows 使用 HNS/HostProcess，并有平台和版本限制。可使用 IPv4 VXLAN 或受支持的非 overlay BGP；当前审查的 Windows 指南不支持 IPv6/双栈、eBPF、WireGuard、HostEndpoint 策略和 Service 宣告。应匹配操作系统/容器版本，并确认实际供应商配置。

</details>

8. Calico Enterprise 与 Calico Open Source 的主要区别是什么？
   - A) Enterprise 使用不同的数据平面技术
   - B) Enterprise 提供额外的安全、合规和可观测性功能
   - C) Enterprise 只能用于特定 Kubernetes 发行版
   - D) Enterprise 不支持 BGP

<details>
<summary>显示答案</summary>

**答案：B) Enterprise 提供额外的安全、合规和可观测性功能**

**说明：**
Open Source 3.32 已包含策略层级、Whisker/流量可视化、暂存策略，以及通过 Istio/Dikastes 实现的 HTTP 策略。商业版本会增加特定产品功能，例如域策略、出口网关、远端身份/服务和报告。具体功能与支持条款取决于所选产品及版本。

</details>

9. Tigera Operator 1.42.6 对 1,000 个计数节点计算出的 Typha 副本目标是多少？
   - A) 5 个副本
   - B) 3 个副本
   - C) 7 个副本
   - D) 10 个副本

<details>
<summary>显示答案</summary>

**答案：C) 7 个副本**

**说明：**
对于 N>4，经审查的 Operator 使用 max(3, floor(N/200)+2)，因此 N 为 1,000 时计算结果为 7。N<=2 时为 1，N<=4 时为 2。这是带有节点计数和放置条件的实现目标，并不保证“每 200 个节点配一个 Typha”就能达到某种实测容量。

</details>

10. 使用 Calico-IPAM 部署双栈时，需要满足哪项地址池前置条件？
    - A) 单独进行 IPv6 专用安装
    - B) 为 IPv4 和 IPv6 地址范围都配置 IPPool
    - C) 只能使用 eBPF 数据平面
    - D) 禁用网络策略执行

<details>
<summary>显示答案</summary>

**答案：B) 为 IPv4 和 IPv6 地址范围都配置 IPPool**

**说明：**
Calico-IPAM 双栈需要 IPv4 和 IPv6 地址池；Kubernetes、CNI、节点寻址和底层网络也必须同时支持这两个地址族。仅 IPv6 部署不需要 IPv4 地址池。Felix ipv6Support 是布尔值；只添加该标志或地址池，不能把现有集群的 IP 地址族配置转换为双栈。

</details>

11. 如何检测 Calico IPAM 的 IP 地址耗尽？
    - A) 检查 kube-apiserver 日志
    - B) 使用 calicoctl ipam show 查看分配状态
    - C) 监控节点内存用量
    - D) 检查 Pod 重启次数

<details>
<summary>显示答案</summary>

**答案：B) 使用 calicoctl ipam show 查看分配状态**

**说明：**
ipam show 会报告地址分配用量；添加 --show-blocks 可查看块详情。可以通过 BlockAffinity 查看节点关联情况，并同时考虑符合条件的地址池、预留地址和亲和性/主机限制。其他地址池有空闲地址不代表本次分配一定成功。只有在生成最新的恢复报告并确认分配确实陈旧后才能清理，不能照抄示例 IP。

</details>

12. 哪种情况适合考虑 Calico 直接使用 etcd 的配置？
    - A) 集群少于 100 个节点时
    - B) 使用托管 Kubernetes 服务时
    - C) 在受支持的非 Kubernetes 部署中，并有明确的 etcd 运维与恢复计划
    - D) 使用 eBPF 数据平面时

<details>
<summary>显示答案</summary>

**答案：C) 在受支持的非 Kubernetes 部署中，并有明确的 etcd 运维与恢复计划**

**说明：**
对于单独设计且受支持的部署，直接使用 etcd 可能合适。对许多 Kubernetes 安装而言，Kubernetes datastore 更简单；当前 eBPF 数据平面也要求使用它。是否采用 etcd 不由固定的 5,000 节点门槛或所谓通用读取速度对比决定。

</details>
