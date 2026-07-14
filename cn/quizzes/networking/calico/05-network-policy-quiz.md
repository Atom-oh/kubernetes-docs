# Network Policy 测验

> **相关文档**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **最后更新**: February 22, 2026

## 测验

1. Calico 解决了 Kubernetes 标准 NetworkPolicy 的哪项主要限制？
   - A) 无法指定端口号
   - B) 不支持 egress 规则
   - C) 没有 Deny 规则、没有全局策略、selector 选项有限
   - D) 无法按 labels 选择 Pod

<details>
<summary>显示答案</summary>

**答案：C) 没有 Deny 规则、没有全局策略、selector 选项有限**

**说明：**
Kubernetes 标准 NetworkPolicy 有多项限制：它仅支持 Allow 规则（没有显式 Deny），无法创建集群范围的全局策略，selector 选项有限，并且不支持 L7（应用层）过滤。Calico 通过显式 Deny/Allow/Log/Pass 操作、GlobalNetworkPolicy、高级 selector 和 L7 策略支持扩展了 NetworkPolicy。

</details>

2. Calico NetworkPolicy 中 selector 的语法是什么？
   - A) 类似标准 Kubernetes 的 YAML 键值对
   - B) 类似 `app == 'frontend'` 的基于表达式的语法
   - C) 正则表达式
   - D) JSON 路径表达式

<details>
<summary>显示答案</summary>

**答案：B) 类似 `app == 'frontend'` 的基于表达式的语法**

**说明：**
Calico 使用基于表达式的 selector 语法，支持 `==`、`!=`、`in`、`not in`、`has()` 和 `!has()` 等运算符。例如：`app == 'frontend'`、`environment in {'prod', 'staging'}`、`has(role)`。与标准 Kubernetes label selector 相比，这提供了更高的灵活性。

</details>

3. Calico NetworkPolicy 规则中有效的操作类型有哪些？
   - A) Accept, Reject
   - B) Allow, Deny, Log, Pass
   - C) Permit, Block, Audit
   - D) Enable, Disable, Monitor

<details>
<summary>显示答案</summary>

**答案：B) Allow, Deny, Log, Pass**

**说明：**
Calico NetworkPolicy 支持四种操作类型：`Allow`（允许流量）、`Deny`（丢弃流量）、`Log`（记录流量并继续评估）和 `Pass`（跳至下一个 Tier 进行评估）。这些操作可对流量处理进行细粒度控制。

</details>

4. Calico 中 GlobalNetworkPolicy 和 NetworkPolicy 有什么区别？
   - A) GlobalNetworkPolicy 更快
   - B) NetworkPolicy 需要 namespace，GlobalNetworkPolicy 应用于整个集群
   - C) GlobalNetworkPolicy 仅适用于 eBPF 模式
   - D) NetworkPolicy 支持更多功能

<details>
<summary>显示答案</summary>

**答案：B) NetworkPolicy 需要 namespace，GlobalNetworkPolicy 应用于整个集群**

**说明：**
Calico NetworkPolicy 是 namespace 范围的，仅应用于该 namespace 中的 Pod，类似于 Kubernetes NetworkPolicy。GlobalNetworkPolicy 是集群范围的，可以应用于所有 namespace 中的全部 Pod，因此非常适合安全基线、合规要求，以及默认拒绝策略等集群范围的规则。

</details>

5. Calico 中 NetworkSet 的用途是什么？
   - A) 对网络接口进行分组
   - B) 定义可复用的 IP 地址/CIDR 集合
   - C) 配置 network namespace
   - D) 管理网络插件

<details>
<summary>显示答案</summary>

**答案：B) 定义可复用的 IP 地址/CIDR 集合**

**说明：**
NetworkSet 是一种 Calico 资源，用于定义可在网络策略中引用的一组 IP 地址或 CIDR 块。这样，您可以一次定义外部 IP 组（例如数据库服务器或可信合作伙伴），并在多个策略中引用它们，使策略管理更简单、更易维护。

</details>

6. Calico 的策略模型如何评估 Tiers？
   - A) 按名称的字母顺序
   - B) 按 order 字段，数值较小的先评估
   - C) 随机
   - D) 按创建时间戳

<details>
<summary>显示答案</summary>

**答案：B) 按 order 字段，数值较小的先评估**

**说明：**
Tiers 会根据其 `order` 字段按顺序进行评估，数值较小的先评估。在每个 Tier 中，策略也按其 order 字段进行评估。这种层级结构使组织能够分离安全策略（低 order）、平台策略（中等 order）和应用策略（高 order）。

</details>

7. Calico 策略规则中的 Pass 操作有什么作用？
   - A) 立即允许流量
   - B) 静默丢弃流量
   - C) 跳至下一个 Tier 继续评估
   - D) 记录流量并允许它

<details>
<summary>显示答案</summary>

**答案：C) 跳至下一个 Tier 继续评估**

**说明：**
`Pass` 操作会使策略评估跳过当前 Tier 中剩余的策略，并继续到下一个 Tier。当较高优先级的 Tier（如安全）希望让特定流量由较低优先级的 Tiers（如应用策略）进一步评估，而不是作出最终决定时，这非常有用。

</details>

8. 如何在 Calico 中实现基于 FQDN（域名）的策略？
   - A) 在 ingress 规则中使用 `hosts` 字段
   - B) 在 destination specification 中使用 `domains` 字段
   - C) 不支持 FQDN 策略
   - D) 使用 DNS NetworkPolicy CRD

<details>
<summary>显示答案</summary>

**答案：B) 在 destination specification 中使用 `domains` 字段**

**说明：**
Calico 使用 egress 规则中的 `domains` 字段支持基于 FQDN 的策略。您可以指定诸如 `"*.amazonaws.com"` 的域名模式或精确域名。Calico 会将这些域名解析为 IP 地址并创建相应规则。此功能在 Calico Enterprise 中可用，并且在开源 Calico 中需要 DNS proxy 配置。

</details>

9. GlobalNetworkPolicy 中的 applyOnForward 设置控制什么？
   - A) 策略是否应用于通过主机转发/路由的流量
   - B) 策略是按正序还是倒序应用
   - C) 是否将策略违规转发给 SIEM
   - D) 策略是否应用于端口转发

<details>
<summary>显示答案</summary>

**答案：A) 策略是否应用于通过主机转发/路由的流量**

**说明：**
`applyOnForward` 设置决定策略是否应用于经由主机转发的流量（而非以主机本身为目的地或源头的流量）。这对于 Host Endpoint 策略以及节点充当其他 endpoint 之间流量路由器的场景非常重要。

</details>

10. Calico 策略中 doNotTrack 的用途是什么？
    - A) 禁用策略日志记录
    - B) 在连接跟踪之前应用策略（无状态）
    - C) 防止在审计日志中跟踪策略
    - D) 禁用 endpoint 跟踪

<details>
<summary>显示答案</summary>

**答案：B) 在连接跟踪之前应用策略（无状态）**

**说明：**
`doNotTrack` 选项会在 Linux 连接跟踪（conntrack）之前应用策略规则。这会创建不跟踪连接状态的无状态规则，适用于高性能场景，或需要在流量进入连接跟踪系统之前应用规则的情况。必须显式允许请求和响应流量。

</details>

11. Calico 策略中 preDNAT 的用途是什么？
    - A) 在 DNS 解析之前应用策略
    - B) 在 Destination NAT 之前应用策略，以查看原始目的地
    - C) 阻止发生 DNAT
    - D) 仅将策略应用于 DNS 流量

<details>
<summary>显示答案</summary>

**答案：B) 在 Destination NAT 之前应用策略，以查看原始目的地**

**说明：**
`preDNAT` 选项会在发生 Destination NAT 之前应用策略，使策略能够在原始目的 IP/端口被转换之前查看它。这对于 Host Endpoint 上的策略很有用：您希望根据原始目的地（如外部 IP）过滤流量，然后再由 DNAT 将其转换为 Pod IP。

</details>

12. 如何在 Calico 中为所有 Pod 实现默认拒绝策略？
   - A) 在 FelixConfiguration 中设置集群范围的标志
   - B) 创建 selector 为 `all()` 且没有规则的 GlobalNetworkPolicy
   - C) 删除所有现有的 NetworkPolicies
   - D) 在 IPPool 中配置默认拒绝

<details>
<summary>显示答案</summary>

**答案：B) 创建 selector 为 `all()` 且没有规则的 GlobalNetworkPolicy**

**说明：**
要实现默认拒绝，请创建一个选择所有 Pod（`selector: all()`）且具有 `types: [Ingress, Egress]`、但没有 allow 规则的 GlobalNetworkPolicy。该策略应具有较高的 order 值，以便最后进行评估。未被其他策略显式允许的任何流量，都会被此兜底策略拒绝。

</details>

13. Calico 策略中的 order 字段控制什么？
    - A) 选择 Pod 的顺序
    - B) Tier 内的评估优先级（数值越小越早）
    - C) 策略内规则应用的顺序
    - D) NetworkSets 中 IP 地址的顺序

<details>
<summary>显示答案</summary>

**答案：B) Tier 内的评估优先级（数值越小越早）**

**说明：**
`order` 字段决定一个 Tier 内策略的评估优先级。order 值较低的策略会先评估。如果策略匹配并采取终止操作（Allow 或 Deny），评估将停止。这样，您可以在通用规则之前创建高优先级例外。

</details>

14. Calico 中的 Host Endpoint 是什么？
    - A) 运行在 host network 上的 Pod
    - B) 用于策略强制执行的主机网络接口表示
    - C) API server endpoint
    - D) 主机上的 Service endpoint

<details>
<summary>显示答案</summary>

**答案：B) 用于策略强制执行的主机网络接口表示**

**说明：**
Host Endpoint 表示主机节点上的一个网络接口，允许 Calico 策略应用于进入或离开主机本身的流量（而不仅是 Pod 流量）。这使得可以保护主机网络接口、控制哪些流量能够访问节点 Service，并实现主机级防火墙规则。

</details>

15. 如何调试网络策略未按预期工作的问题？
    - A) 仅通过阅读策略 YAML
    - B) 检查 workload endpoint、使用 calicoctl 评估策略，以及查看 Felix 日志
    - C) 重启所有 Calico 组件
    - D) 不支持网络策略调试

<details>
<summary>显示答案</summary>

**答案：B) 检查 workload endpoint、使用 calicoctl 评估策略，以及查看 Felix 日志**

**说明：**
要调试网络策略：1) 使用 `calicoctl get workloadendpoint -n <namespace>` 验证 endpoint 存在且具有正确的 labels，2) 使用 `calicoctl get networkpolicy -A` 和 `globalnetworkpolicy` 列出所有策略，3) 检查 Felix 日志中的策略相关消息，4) 验证 selector 表达式与 endpoint labels 匹配，5) 在 eBPF 模式中，使用 `tc filter show` 检查已应用的规则。

</details>

---

[返回学习资料](../../../networking/calico/05-network-policy.md) | [上一测验：BGP 深入解析](./04-bgp-deep-dive-quiz.md)
