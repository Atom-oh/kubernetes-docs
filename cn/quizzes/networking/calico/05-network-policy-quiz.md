# 网络策略测验

> **相关文档**：[网络策略](../../../networking/calico/05-network-policy.md)
> **最后更新**：2026 年 9 月 12 日

## 测验

1. Kubernetes 标准 NetworkPolicy 的哪项关键限制可由 Calico 弥补？
   - A) 无法指定端口号
   - B) 不支持出站规则
   - C) 没有 Deny 规则、没有全局策略，且选择器选项有限
   - D) 无法按标签选择 Pod

<details>
<summary>显示答案</summary>

**答案：C) 没有 Deny 规则、没有全局策略，且选择器选项有限**

**解释：**
标准 Kubernetes NetworkPolicy 对象提供的是命名空间范围、可叠加的 L3/L4 允许规则。只要网络插件实现了相应功能，它本身就支持命名端口，以及通过 endPort 指定的数字端口范围。Calico 增加了显式操作、全局策略、策略层和表达式选择器。开源版的 HTTP 策略需要集成 Istio/Dikastes；域名 DNS 策略则是商业扩展。

</details>

2. Calico NetworkPolicy 使用什么选择器语法？
   - A) 与标准 Kubernetes 相同的 YAML 键值对
   - B) 类似 `app == 'frontend'` 的表达式语法
   - C) 正则表达式
   - D) JSONPath 表达式

<details>
<summary>显示答案</summary>

**答案：B) 类似 `app == 'frontend'` 的表达式语法**

**解释：**
Calico 使用基于表达式的选择器语法，支持 `==`、`!=`、`in`、`not in`、`has()` 和 `!has()` 等运算符。例如：`app == 'frontend'`、`environment in {'prod', 'staging'}`、`has(role)`。与标准 Kubernetes 标签选择器相比，它提供了更灵活的匹配方式。

</details>

3. Calico NetworkPolicy 规则有哪些有效操作类型？
   - A) Accept、Reject
   - B) Allow、Deny、Log、Pass
   - C) Permit、Block、Audit
   - D) Enable、Disable、Monitor

<details>
<summary>显示答案</summary>

**答案：B) Allow、Deny、Log、Pass**

**解释：**
对于当前端点和流量方向，Allow 和 Deny 会结束常规策略判定。Log 会继续后续评估，之后仍可能被拒绝。Pass 会跳过当前 Tier 中剩余的所有策略，转到下一个适用的 Tier；经过最后一个 Tier 后，还会评估 Profiles。另一个端点上的策略仍然适用。

</details>

4. Calico 中 GlobalNetworkPolicy 和 NetworkPolicy 有什么区别？
   - A) GlobalNetworkPolicy 速度更快
   - B) NetworkPolicy 必须属于某个命名空间，GlobalNetworkPolicy 可作用于集群范围
   - C) GlobalNetworkPolicy 仅适用于 eBPF 模式
   - D) NetworkPolicy 支持更多功能

<details>
<summary>显示答案</summary>

**答案：B) NetworkPolicy 必须属于某个命名空间，GlobalNetworkPolicy 可作用于集群范围**

**解释：**
NetworkPolicy 选择其命名空间内的工作负载。GlobalNetworkPolicy 不属于任何命名空间，可以跨命名空间选择工作负载，也可以选择 HostEndpoint。但这并不表示它会自动选择每个端点；应明确指定目标范围，并保留主机及系统流量所需的连通性。

</details>

5. Calico 中 NetworkSet 有什么用途？
   - A) 对网络接口分组
   - B) 定义可重复使用的 IP 地址/CIDR 集合
   - C) 配置网络命名空间
   - D) 管理网络插件

<details>
<summary>显示答案</summary>

**答案：B) 定义可重复使用的 IP 地址/CIDR 集合**

**解释：**
NetworkSet 将带标签的 IP/CIDR 范围归为一组，以便重复使用。命名空间范围的 NetworkSet 与 GlobalNetworkSet 的选择范围不同。在命名空间策略中选择全局资源时，应单独使用 namespaceSelector: global()；global(label-expression) 不是有效语法。

</details>

6. Calico 策略模型如何评估 Tier？
   - A) 按名称的字母顺序
   - B) 按 order 字段，数值较小的先评估
   - C) 随机评估
   - D) 按创建时间戳

<details>
<summary>显示答案</summary>

**答案：B) 按 order 字段，数值较小的先评估**

**解释：**
先评估 order 较小的 Tier，然后再评估每个 Tier 中 order 较小的策略。只有当某个 Tier 中的策略选择了该端点和流量方向时，这个 Tier 才适用。适用的 Tier 中若没有规则匹配，则会采用它的 defaultAction，通常为 Deny。内置 default Tier 的固定顺序为 1,000,000，并非隐含的无穷大。

</details>

7. Calico 策略规则中的 Pass 操作有什么作用？
   - A) 立即允许流量
   - B) 静默丢弃流量
   - C) 跳至下一个 Tier 继续评估
   - D) 记录流量并允许通过

<details>
<summary>显示答案</summary>

**答案：C) 跳至下一个 Tier 继续评估**

**解释：**
Pass 会跳过当前 Tier 中剩余的策略，包括之后可能适用的安全限制。如果需要在授权下放之前检查所有“仅拒绝”类防护规则，那么采用 Tier 级别的 defaultAction: Pass，可能比提前使用无条件 Pass 规则更合适。

</details>

8. Calico Enterprise 3.23 在何处指定允许出站访问的域名？
   - A) 在入站规则的 `hosts` 字段中
   - B) 在目标说明的 `domains` 字段中
   - C) 不支持 FQDN 策略
   - D) 使用 DNS NetworkPolicy CRD

<details>
<summary>显示答案</summary>

**答案：B) 在目标说明的 `domains` 字段中**

**解释：**
Calico Enterprise 支持在 egress Allow 规则中使用 destination.domains，并结合可信 DNS 学习。该字段不存在于开源版 3.32 CRD 中；启用 policySyncPathPrefix 或任意 DNS 代理都不会增加此字段。带前缀的通配符会匹配一个或多个域名组件；基于 IP 的匹配不等同于 HTTPS 主机名身份验证。

</details>

9. Calico GlobalNetworkPolicy 中的 applyOnForward 设置控制什么？
   - A) 策略是否适用于经主机转发/路由的流量
   - B) 策略按正序还是反序应用
   - C) 是否将策略违规转发给 SIEM
   - D) 策略是否适用于端口转发

<details>
<summary>显示答案</summary>

**答案：A) 策略是否适用于经主机转发/路由的流量**

**解释：**
对于 HostEndpoint 策略，设置 applyOnForward: true 后，策略也会应用于经过转发的流量。设置 doNotTrack 或 preDNAT 时，此项为必需配置。主机策略中的 Allow 不会绕过适用的工作负载端点策略。

</details>

10. Calico 策略中 doNotTrack 有什么作用？
    - A) 禁用策略日志记录
    - B) 在连接跟踪之前应用策略（无状态）
    - C) 阻止策略记录在审计日志中
    - D) 禁用端点跟踪

<details>
<summary>显示答案</summary>

**答案：B) 在连接跟踪之前应用策略（无状态）**

**解释：**
doNotTrack 是仅用于主机策略的选项，要求同时设置 applyOnForward: true，并且会在连接跟踪之前应用。不跟踪的 Allow 会阻止对匹配流量进行连接跟踪；请求和响应都需要显式规则。它并非普遍适用的性能优化，还可能与依赖 conntrack 的 Service/NAT 路径冲突。

</details>

11. Calico 策略中 preDNAT 有什么作用？
    - A) 在 DNS 解析前应用策略
    - B) 在目标 NAT 前应用策略，以便看到原始目标地址
    - C) 阻止执行 DNAT
    - D) 仅将策略用于 DNS 流量

<details>
<summary>显示答案</summary>

**答案：B) 在目标 NAT 前应用策略，以便看到原始目标地址**

**解释：**
preDNAT 会在 DNAT 之前，根据原始目标 IP/端口评估入站主机流量。它要求设置 applyOnForward: true，不能包含 egress 规则，也不能与 doNotTrack 组合使用。在此阶段未匹配并不会自动丢弃流量；后续主机/工作负载策略仍会生效。

</details>

12. 在已有显式允许策略之后，哪种基线策略会同时选择 demo-namespace 工作负载的两个流量方向？
    - A) 在 FelixConfiguration 中设置集群范围的标志
    - B) 创建一个 `types: [Ingress, Egress]` 且规则为空的、范围受限的 GlobalNetworkPolicy
    - C) 删除所有现有 NetworkPolicy
    - D) 在 IPPool 中配置默认拒绝

<details>
<summary>显示答案</summary>

**答案：B) 创建一个 `types: [Ingress, Egress]` 且规则为空的、范围受限的 GlobalNetworkPolicy**

**解释：**
选择目标命名空间和工作负载，明确设置两个 types，并将规则留空。省略 order 时，此策略会按顺序排在显式设置了 order 的策略之后。该基线不会覆盖此前已终止评估的 Allow；仅使用 selector: all() 还可能选中 HostEndpoint。不要在通用教程中对系统流量应用无范围限制的兜底策略。

</details>

13. Calico 策略中的 order 字段控制什么？
    - A) 选择 Pod 的顺序
    - B) Tier 内的评估优先级（数值越小，越早评估）
    - C) 策略内规则的应用顺序
    - D) NetworkSet 中 IP 地址的排列顺序

<details>
<summary>显示答案</summary>

**答案：B) Tier 内的评估优先级（数值越小，越早评估）**

**解释：**
`order` 字段决定策略在所属 Tier 中的评估优先级。order 值较小的策略先评估。如果策略匹配并执行 Allow 或 Deny 等终止操作，评估就会停止。这样可以在通用规则之前设置优先级更高的例外规则。

</details>

14. Calico 中的 HostEndpoint 是什么？
    - A) 运行在主机网络上的 Pod
    - B) 用于执行策略的主机网络接口表示
    - C) API server 端点
    - D) 主机上的 Service 端点

<details>
<summary>显示答案</summary>

**答案：B) 用于执行策略的主机网络接口表示**

**解释：**
HostEndpoint 表示受管理主机上的一个接口，供策略执行使用。手动创建的端点可能引入默认拒绝行为；自动创建的端点通常具有默认允许的 Profile，但仍须考虑 failsafe 端口。Installation.hostPorts 不会自动创建 HostEndpoint。

</details>

15. 如何调试网络策略未按预期工作的原因？
    - A) 只阅读策略 YAML
    - B) 检查端点标签、所有适用 Tier、后端/日志和实际连接
    - C) 重启所有 Calico 组件
    - D) 不支持网络策略调试

<details>
<summary>显示答案</summary>

**答案：B) 检查端点标签、所有适用 Tier、后端/日志和实际连接**

**解释：**
列出 Kubernetes 和 Calico 策略，明确检查所有相关 Tier，并验证端点标签及新建连接的允许/拒绝结果。Felix 就绪状态不能作为延迟基准。iptables 的 Log 操作写入内核日志。kube-proxy 或其替代方案中的 Service/NAT 行为也可能解释故障；仅列出 tc 程序无法有效追踪实际生效的策略。

</details>

16. 哪种权限结构可通过标准 API server 实现编辑 Calico application Tier？
    - A) 仅给普通 networkpolicies 配置 resourceNames: ["application.*"]
    - B) 对 application Tier 授予 Get 权限，并允许 tier.networkpolicies 使用 application.*，同时绑定预期命名空间
    - C) 任意包含 verbs: ["*"] 的 Role
    - D) 名为 application 的命名空间

<details>
<summary>显示答案</summary>

**答案：B) 对 application Tier 授予 Get 权限，并允许 tier.networkpolicies 使用 application.*，同时绑定预期命名空间**

**解释：**
Calico 会检查其 tier.networkpolicies 伪资源、合成的 application.* 或策略名称，以及对 Tier 的 get 权限。这不是通用 Kubernetes 资源的 resourceNames 通配符。还必须考虑更宽泛的叠加绑定，以及原生 v3 读取方面的限制。

</details>

17. 客户端使用源端口 49152 连接后端的 8080 端口。哪种入站端口匹配表示服务器监听的端口？
    - A) source.ports: [8080]
    - B) 对每个客户端都使用 source.ports: [49152]
    - C) 使用 protocol TCP 的 destination.ports: [8080]
    - D) 不指定协议，并用涵盖所有端口的源端口范围

<details>
<summary>显示答案</summary>

**答案：C) 使用 protocol TCP 的 destination.ports: [8080]**

**解释：**
服务监听的是目标端口 8080。客户端源端口会变化。数字端口匹配要求使用受支持且携带端口信息的协议。在其他场景中，例如明确配置无状态 DNS 响应规则时，才适合匹配源端口。

</details>

---

[返回学习资料](../../../networking/calico/05-network-policy.md) | [上一测验：BGP 深入解析](./04-bgp-deep-dive-quiz.md)
