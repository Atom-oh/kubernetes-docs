# Network Policies 测验

> **最后更新**: September 13, 2026

本测验测试您对 Kubernetes Network Policies、Cilium Network Policies 和微分段的理解。

## 测验问题

### 1. Kubernetes NetworkPolicy 的默认行为是什么？

A. 阻止所有流量
B. 在没有选择该方向的策略时，不实施 NetworkPolicy 隔离
C. 仅阻止入站流量
D. 仅阻止出站流量

<details>
<summary>显示答案</summary>

**答案：B. 在没有选择该方向的策略时，不实施 NetworkPolicy 隔离**

**说明：**
分别评估 ingress 和 egress。某个方向没有选择该方向的策略意味着 NetworkPolicy 不会隔离该方向；CNI/路由/SG/NACL 或其他策略仍可能阻止连接。仅选择 ingress 的策略不会同时隔离 egress。对于 Pod 到 Pod 的流量，源端 egress 和目标端 ingress 都必须允许该连接。

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

空的 podSelector（`{}`）会选择该 namespace 中的所有 Pod。

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
HTTP 规则嵌套在 ingress 规则的 `toPorts[].rules.http` 下（或嵌套在用于出站过滤的 egress 规则下）。它们需要受支持的 L7 proxy 路径；端到端 TLS 不会被自动检查，且用户提供的 role/API-key headers 不是认证。Cilium 的 AWS VPC CNI chaining mode 对 L7 存在已记录的限制。

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. 什么可以为两个方向创建覆盖整个 namespace 的默认拒绝基线？

A. 在 policyTypes 中仅指定 Ingress
B. 将 podSelector 设为空，并在 policyTypes 中指定 Ingress 和 Egress
C. 将 ingress 和 egress 规则留空
D. B 和 C 都是

<details>
<summary>显示答案</summary>

**答案：D. B 和 C 都是**

**说明：**
要在**两个方向**建立覆盖整个 namespace 的基线，请结合 B 和 C。空 selector 会选择策略自身 namespace 中的所有 Pod，显式指定 Ingress/Egress 类型但不设置允许规则会隔离两个方向。其他选择相应 Pod 的 Kubernetes NetworkPolicies 可以添加允许规则；基线不会覆盖它们。若目标范围更窄，也可以仅建立 ingress 基线。

</details>

### 6. CiliumClusterwideNetworkPolicy 的特点是什么？

A. 需要 metadata.namespace 来选择其作用域
B. 这是一个 cluster-scoped 资源，其 endpoint selector 控制目标
C. 仅控制外部流量
D. 仅支持 L7 策略

<details>
<summary>显示答案</summary>

**答案：B. 这是一个 cluster-scoped 资源，其 endpoint selector 控制目标**

**说明：**
CiliumClusterwideNetworkPolicy 不属于任何 namespace。其 endpoint selector 可以覆盖多个 namespace，也可以将目标明确限定为一个 namespace/application。Cluster scope 并不表示每个 endpoint 都会被选择，也不表示宽泛的 `cluster`/`world` 允许规则就是默认拒绝。

</details>

### 7. 如何在 NetworkPolicy 中允许来自特定 namespace 的所有 Pod？

A. 仅使用 namespaceSelector
B. 仅使用 podSelector
C. 组合使用 namespaceSelector 和要求 app=api 的 podSelector
D. 使用 namespace 字段

<details>
<summary>显示答案</summary>

**答案：A. 仅使用 namespaceSelector**

**说明：**
使用 `namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` 选择该 namespace 中的所有 Pod。在同一个 peer 中添加**空的** podSelector 也会选择其中所有 Pod；选项 C 则会将 Pod 限制为 `app=api`。在一个 peer 中，selectors 使用 AND；独立的 peer 条目使用 OR。不会自动创建自定义的 `name` label。

</details>

### 8. CiliumNetworkPolicy 中哪个字段定义基于 FQDN 的 egress 规则？

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>显示答案</summary>

**答案：A. toFQDNs**

**说明：**
`toFQDNs` 将从 DNS 获取的 IP 与指定的 port 规则结合使用。请分别允许实际的 resolver 路径和所需的 DNS queries，包括 TCP 和 UDP53。还需考虑 cache/TTL、search suffixes、共享的目标 IP 以及 TLS/application authorization。域名匹配并不能证明 SaaS tenant identity。

</details>

### 9. 哪种流量不受 NetworkPolicy 影响？

A. Pod 之间的流量
B. 同一 Pod 中 containers 之间的流量（localhost）
C. 通过 Services 的流量
D. 来自外部来源的流量

<details>
<summary>显示答案</summary>

**答案：B. 同一 Pod 中 containers 之间的流量（localhost）**

**说明：**
同一个 Pod 中的 containers 共享 network namespace；它们的 localhost 通信不受普通 Kubernetes NetworkPolicy enforcement 的约束。Node/hostNetwork 处理和非 TCP/UDP/SCTP protocols 存在特定于实现的限制。不要从 Pod policy 推断完全的 host isolation。

</details>

### 10. Cilium 的基于 Identity 的策略有什么优势？

A. 不受 IP address 变化影响
B. 处理速度更快
C. 内存使用更少
D. 不需要 DNS lookup

<details>
<summary>显示答案</summary>

**答案：A. 不受 IP address 变化影响**

**说明：**
基于 label 的 endpoint policy 避免对临时 Pod IP 进行硬编码。datapath 会将当前 endpoint 映射到与其相关 label sets 对应的 security identities。numeric identity 可以被重新分配，并不是永久的 application identifier；仍须考虑 label changes、namespace/cluster context 和 propagation。

</details>

### 11. 三层架构中 backend tier 的正确网络策略是什么？

A. 允许所有流量
B. 仅允许来自 frontend 的 ingress
C. 允许来自 frontend 的 ingress，并允许到 database 的 egress
D. 仅允许到 database 的 egress

<details>
<summary>显示答案</summary>

**答案：C. 允许来自 frontend 的 ingress，并允许到 database 的 egress**

**说明：**
C 描述了 backend 的 application path：在已审查的 ports 上允许 frontend ingress 和 database egress。还应允许 frontend egress 和 database ingress，以及所需的 DNS/health/monitoring paths。否则，另一 endpoint 上的 default-deny policy 仍可能阻止连接。允许的连接会隐式允许其 return traffic。

</details>

### 12. 在 NetworkPolicy 中使用 ipBlock 指定 CIDR ranges 时，哪个字段用于排除特定 IP？

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>显示答案</summary>

**答案：B. except**

**说明：**
`except` 从该 ipBlock 的允许规则中减去 CIDRs。它不是全局拒绝：另一个选择相应 Pod 的策略可以允许被排除的 address。address translation 可能会改变 plugin 评估的 IP，因此请验证实际的 CNI 和 load-balancer/Service path。

</details>

---

[Network policies 指南](../../security/04-network-policies.md)
