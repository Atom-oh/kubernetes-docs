# Cilium Service Mesh 安全测验

根据 Cilium 1.20.3 审核。[安全指南](../../../service-mesh/cilium-service-mesh/03-security.md)区分了带外身份验证、传输加密和 ztunnel beta，并提供了主要参考资料。

### 1. SPIRE 为 Cilium 的带外双向身份验证提供什么？

- **A.** 为每个 Pod 提供一个 Istio sidecar
- **B.** 为代理身份验证机制提供 SVID 身份凭据
- **C.** 自动加密所有应用程序流量
- **D.** 替代 Kubernetes API 服务器

<details>
<summary>显示答案</summary>

**答案：B. 为代理身份验证机制提供 SVID 身份凭据**

对于带外 beta 机制，SPIRE 提供 SVID 身份凭据，Cilium agent 会独立于应用程序连接对对等方进行身份验证。WireGuard/IPsec 加密是另一项独立选择。Cilium 1.20.3 还提供单独的 ztunnel mTLS beta，它有自己的 CA/引导流程、注册流程和策略限制。

</details>

### 2. 将身份验证模式设为 'required' 时，CiliumNetworkPolicy 会如何工作？

- **A.** 允许所有流量通过，不进行身份验证
- **B.** 只允许通过双向身份验证的流量
- **C.** 身份验证失败时只记录警告
- **D.** 禁用 mTLS

<details>
<summary>显示答案</summary>

**答案：B. 只允许通过双向身份验证的流量**

匹配的 allow 规则要求身份验证成功；这不是集群级开关，也不会自行对应用程序负载进行 TLS 加密。其他授权要求和应用程序身份验证要求仍然有效。API 格式为 authentication: {mode: required}，而不是数组。

</details>

### 3. 哪些流量不会仅由 Cilium WireGuard 加密？

- **A.** 不同节点之间受支持的 Pod 流量
- **B.** 启用节点加密时受支持的远程节点流量
- **C.** 同一节点上的 Pod 流量，以及外部客户端到集群这一段流量
- **D.** 经过 ClusterIP Service 的受支持远程 Pod 流量路径

<details>
<summary>显示答案</summary>

**答案：C. 同一节点上的 Pod 流量，以及外部客户端到集群这一段流量**

Cilium WireGuard 不会加密同一节点上的 Pod 流量，也不会加密外部客户端到集群这一段流量。远程节点的覆盖范围取决于所选模式和文档列出的例外情况。此功能需要内核支持；chart 不提供 userspaceFallback 选项。

</details>

### 4. 在 CiliumNetworkPolicy 中使用 L7 HTTP 规则限制特定路径和方法时，正确的配置方式是什么？

- **A.** 在 toEndpoints 中指定路径和方法
- **B.** 在 toPorts.rules.http 中指定方法和路径
- **C.** 直接在 ingress.http 中指定
- **D.** 在 spec.http 中定义规则

<details>
<summary>显示答案</summary>

**答案：B. 在 toPorts.rules.http 中指定方法和路径**

HTTP 规则位于 ingress/egress toPorts.rules.http 下。它们可以匹配受支持的 method/path/header 字段，但仅检查请求头是否存在，或检查字符串是否看起来像 Bearer 凭据，都不能验证 JWT 或授权最终用户。

</details>

### 5. Cilium 基于身份的策略有什么好处？

- **A.** Pod IP 变更后，策略标签选择器仍可保持稳定
- **B.** 使用 MAC 地址而不是标签
- **C.** 每个数字 ID 在所有重启后都永久不变
- **D.** 无需更新地址到身份的映射

<details>
<summary>显示答案</summary>

**答案：A. Pod IP 变更后，策略标签选择器仍可保持稳定**

策略使用与身份相关的标签集，而不是需要手动维护的 Pod IP 列表。多个 Pod 可以共享同一身份，但 Cilium 仍会更新地址/身份状态，并可能回收/重新分配 ID。重启并不能保证数字标识符永久不变。

</details>

### 6. 在 Cilium 中使用 DNS L7 策略限制外部域名访问时，需要使用哪些规则？

- **A.** 组合使用 toFQDNs 和 dns 规则
- **B.** 仅使用 toEndpoints
- **C.** 仅使用 toCIDR
- **D.** 仅使用 toEntities

<details>
<summary>显示答案</summary>

**答案：A. 组合使用 toFQDNs 和 dns 规则**

DNS 规则会将查询限制到所选解析器；toFQDNs 和端口规则则分别控制与已学习地址的连接。应包含实际的 UDP/TCP 解析器行为和搜索列表中的名称。Service 名称包含 Service 和命名空间标签，而 DNS 权限并不意味着可以连接所有目标。

</details>

### 7. 引入默认拒绝策略时，应该允许哪些流量？

- **A.** 所有外部目标
- **B.** 工作负载明确依赖的流量，包括必要时实际使用的解析器/探测流量
- **C.** 将所有主机流量作为普遍的最低要求
- **D.** DNS 曾经返回过的所有地址

<details>
<summary>显示答案</summary>

**答案：B. 工作负载明确依赖的流量，包括必要时实际使用的解析器/探测流量**

只允许经工作负载和拓扑验证的依赖流量，例如实际 DNS 解析器使用的 UDP/TCP53 流量和必需的探测流量。无条件开放主机网络访问并不是普遍的最低要求。当 Cilium 策略的某个方向规则数组为空时，使用显式的 enableDefaultDeny 标志。

</details>

### 8. SPIRE 中工作负载证明的作用是什么？

- **A.** 颁发证书
- **B.** 验证工作负载身份
- **C.** 应用网络策略
- **D.** 加密流量

<details>
<summary>显示答案</summary>

**答案：B. 验证工作负载身份**

SPIRE Agent 使用已配置的证明器/选择器执行工作负载证明；Server 则对 Agent 进行证明并签署 SVID。Cilium 的带外集成还使用委托式身份获取，并为 Cilium 安全身份创建条目。这不会自动加密应用程序负载。

</details>

### 9. 在审计模式下测试网络策略时，Cilium 会如何运行？

- **A.** 阻止所有流量
- **B.** 记录策略违规，但允许流量通过
- **C.** 完全禁用策略
- **D.** 只发送警报

<details>
<summary>显示答案</summary>

**答案：B. 记录策略违规，但允许流量通过**

实际可变的端点选项 PolicyAuditMode 会改变隔离端点测试中已审计的数据路径策略执行行为。cilium.io/audit-mode 不是受支持的单策略注解。测试后应恢复强制执行，并单独验证 L7 行为；enableDefaultDeny:false 也不是通用审计模式。

</details>

### 10. 三层后端的最小权限策略需要涵盖什么？

- **A.** 不受限制的所有流量
- **B.** 必需的前端入站流量、数据库出站流量，以及 DNS 等明确依赖项
- **C.** 不允许任何入站流量，包括来自前端的流量
- **D.** 不受限制的互联网访问

<details>
<summary>显示答案</summary>

**答案：B. 必需的前端入站流量、数据库出站流量，以及 DNS 等明确依赖项**

后端允许其必需的前端调用方和数据库目标，以及 DNS 等明确依赖项。指南中的数据库策略显式启用了出站默认拒绝，且没有出站 allow 规则。仍允许有状态回复；网络分段并不等同于完整的应用程序授权或数据丢失防护。

</details>

### 11. IPsec keyRotationDuration: 5m 表示什么？

- **A.** 每五分钟生成一个新密钥
- **B.** 每五分钟轮换每个工作负载证书
- **C.** 密钥变更后允许一个过渡/旧密钥清理宽限期
- **D.** 无限期重复使用同一个全局密钥

<details>
<summary>显示答案</summary>

**答案：C. 密钥变更后允许一个过渡/旧密钥清理宽限期**

IPsec keyRotationDuration 用于控制密钥材料变更后的过渡/旧密钥移除宽限期。它不会定期生成密钥。请使用受支持的协调式密钥/ID 轮换流程，以及带有 '+' 的每隧道派生密钥形式。WireGuard 则管理由节点生成的密钥对。

</details>

### 12. 使用哪个 Hubble 命令可以先筛选被丢弃的流，再检查丢弃原因？

- **A.** hubble observe --verdict FORWARDED
- **B.** hubble observe --verdict DROPPED
- **C.** hubble policy list
- **D.** hubble status --violations

<details>
<summary>显示答案</summary>

**答案：B. hubble observe --verdict DROPPED**

DROPPED 会筛选出由多种原因导致的被丢弃流。检查报告为策略拒绝的丢弃流时，添加 --drop-reason-desc POLICY_DENIED；L7/应用程序故障则应单独检查。AUDIT 是单独的 verdict。--last 查询的是有界历史记录，并且通过 Relay 时可能会按每个 Hubble 实例分别返回结果。

</details>
