# 网络策略测验

> **最后更新**：2026年9月13日

本测验测试您对 Kubernetes 网络策略、Cilium 网络策略和微分段的理解。

## 测验问题

### 1. Kubernetes NetworkPolicy 的默认行为是什么？

A. 阻止所有流量
B. 某方向没有选中该 Pod 的策略时，不在该方向实施 NetworkPolicy 隔离
C. 仅阻止入站流量
D. 仅阻止出站流量

<details>
<summary>显示答案</summary>

**答案：B. 某方向没有选中该 Pod 的策略时，不在该方向实施 NetworkPolicy 隔离**

**说明：**
分别评估入站（ingress）和出站（egress）。某个方向没有选中该 Pod 的策略时，NetworkPolicy 不会隔离该方向；CNI/路由/SG/NACL 或其他策略仍可能阻止连接。选中该 Pod 的仅入站策略不会同时隔离出站流量。对于 Pod 到 Pod 的流量，源端出站和目标端入站都必须允许该连接。

</details>

### 2. NetworkPolicy 中的哪个字段用于选择特定的 Pod？

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>显示答案</summary>

**答案：B. podSelector**

**说明：**
NetworkPolicy 中的 `spec.podSelector` 字段选择策略所适用的 Pod：
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

空的 podSelector（`{}`）会选择该命名空间中的所有 Pod。

</details>

### 3. NetworkPolicy 中哪些字段定义入站和出站规则？

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>显示答案</summary>

**答案：B. ingress/egress**

**说明：**
- **ingress**：入站流量规则
- **egress**：出站流量规则

```yaml
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
```

</details>

### 4. CiliumNetworkPolicy 中的 L7 HTTP 规则定义在哪里？

A. spec.http
B. spec.ingress[].toPorts[].rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>显示答案</summary>

**答案：B. spec.ingress[].toPorts[].rules.http**

**说明：**
HTTP 规则嵌套在入站规则的 `toPorts[].rules.http` 下（或嵌套在用于出站过滤的出站规则下）。它们需要受支持的 L7 代理路径；端到端 TLS 不会被自动检查，且用户提供的角色/API 密钥标头不能作为身份验证。Cilium 的 AWS VPC CNI 链式模式对 L7 存在已记录的限制。

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. 什么可以为两个方向创建覆盖整个命名空间的默认拒绝基线？

A. 在 policyTypes 中仅指定 Ingress
B. 将 podSelector 设为空，并在 policyTypes 中指定 Ingress 和 Egress
C. 将 ingress 和 egress 规则留空
D. B 和 C 都是

<details>
<summary>显示答案</summary>

**答案：D. B 和 C 都是**

**说明：**
要在**两个方向**建立覆盖整个命名空间的基线，请结合 B 和 C。空选择器会选择策略自身命名空间中的所有 Pod，显式指定 Ingress/Egress 类型但不设置允许规则会隔离两个方向。其他选中相应 Pod 的 Kubernetes NetworkPolicy 可以添加允许规则；基线不会覆盖它们。若目标范围更窄，也可以仅建立入站基线。

</details>

### 6. CiliumClusterwideNetworkPolicy 的特点是什么？

A. 需要 metadata.namespace 来选择其作用域
B. 这是一个集群作用域的资源，其端点选择器控制目标
C. 仅控制外部流量
D. 仅支持 L7 策略

<details>
<summary>显示答案</summary>

**答案：B. 这是一个集群作用域的资源，其端点选择器控制目标**

**说明：**
CiliumClusterwideNetworkPolicy 不属于任何命名空间。其端点选择器可以覆盖多个命名空间，也可以将目标明确限定为一个命名空间/应用。集群作用域并不表示每个端点都会被选中，也不表示宽泛的 `cluster`/`world` 允许规则就是默认拒绝。

</details>

### 7. 如何在 NetworkPolicy 中允许来自特定命名空间的所有 Pod？

A. 仅使用 namespaceSelector
B. 仅使用 podSelector
C. 组合使用 namespaceSelector 和要求 app=api 的 podSelector
D. 使用 namespace 字段

<details>
<summary>显示答案</summary>

**答案：A. 仅使用 namespaceSelector**

**说明：**
使用 `namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` 选择该命名空间中的所有 Pod。在同一个对端（peer）条目中添加**空的** podSelector 也会选择其中所有 Pod；选项 C 则会将 Pod 限制为 `app=api`。同一对端条目中的选择器采用 AND 逻辑；不同的对端条目采用 OR 逻辑。不会自动创建自定义的 `name` 标签。

</details>

### 8. CiliumNetworkPolicy 中哪个字段定义基于 FQDN 的出站规则？

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>显示答案</summary>

**答案：A. toFQDNs**

**说明：**
`toFQDNs` 将从 DNS 获取的 IP 与指定的端口规则结合使用。请分别允许实际的解析器路径和所需的 DNS 查询，包括 TCP 和 UDP53。还需考虑缓存/TTL、搜索后缀、共享的目标 IP 以及 TLS/应用层授权。域名匹配并不能证明 SaaS 租户身份。

</details>

### 9. 哪种流量不受 NetworkPolicy 影响？

A. Pod 之间的流量
B. 同一 Pod 中容器之间的流量（localhost）
C. 通过 Service 的流量
D. 来自外部来源的流量

<details>
<summary>显示答案</summary>

**答案：B. 同一 Pod 中容器之间的流量（localhost）**

**说明：**
同一个 Pod 中的容器共享网络命名空间；它们的 localhost 通信不受普通 Kubernetes NetworkPolicy 的约束。节点/hostNetwork 的处理方式和非 TCP/UDP/SCTP 协议存在特定于实现的限制。不要根据 Pod 策略推断已实现完全的主机隔离。

</details>

### 10. Cilium 的基于身份的策略有什么优势？

A. 不受 IP 地址变化影响
B. 处理速度更快
C. 内存使用更少
D. 不需要 DNS 查询

<details>
<summary>显示答案</summary>

**答案：A. 不受 IP 地址变化影响**

**说明：**
基于标签的端点策略避免对临时 Pod IP 进行硬编码。数据路径会将当前端点映射到其相关标签集对应的安全身份。数字身份可以被重新分配，并不是永久的应用标识符；仍须考虑标签变化、命名空间/集群上下文和信息传播。

</details>

### 11. 三层架构中后端层的正确网络策略是什么？

A. 允许所有流量
B. 仅允许来自前端的入站流量
C. 允许来自前端的入站流量，并允许到数据库的出站流量
D. 仅允许到数据库的出站流量

<details>
<summary>显示答案</summary>

**答案：C. 允许来自前端的入站流量，并允许到数据库的出站流量**

**说明：**
C 描述了后端的应用流量路径：在已审查的端口上允许来自前端的入站流量和到数据库的出站流量。还应允许前端的出站流量和数据库的入站流量，以及所需的 DNS/健康检查/监控路径。否则，另一端点上的默认拒绝策略仍可能阻止连接。已获允许的连接会隐式允许其返回流量。

</details>

### 12. 在 NetworkPolicy 中使用 ipBlock 指定 CIDR 范围时，哪个字段用于排除特定 IP？

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>显示答案</summary>

**答案：B. except**

**说明：**
`except` 从该 ipBlock 的允许规则中排除指定的 CIDR。它不是全局拒绝：另一个选中相应 Pod 的策略可以允许被排除的地址。地址转换可能会改变插件评估的 IP，因此请验证实际的 CNI 和负载均衡器/Service 路径。

</details>

---

[网络策略指南](../../security/04-network-policies.md)
