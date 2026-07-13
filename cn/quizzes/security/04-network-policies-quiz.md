# Network Policies 测验

本测验测试你对 Kubernetes Network Policies、Cilium Network Policies 和微分段的理解。

## 测验问题

### 1. Kubernetes NetworkPolicy 的默认行为是什么？

A. 阻止所有流量
B. 允许所有流量
C. 仅阻止入站流量
D. 仅阻止出站流量

<details>
<summary>显示答案</summary>

**答案：B. 允许所有流量**

**解释：**
在没有 NetworkPolicy 的情况下，Kubernetes 默认允许 Pods 之间的所有流量。当你创建 NetworkPolicy 时，它会为匹配该策略的 podSelector 的 Pods 启用“默认拒绝”行为。

</details>

### 2. NetworkPolicy 中哪个字段用于选择特定的 Pods？

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>显示答案</summary>

**答案：B. podSelector**

**解释：**
NetworkPolicy 中的 `spec.podSelector` 字段选择该策略适用的 Pods：
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

空的 podSelector (`{}`) 会选择该命名空间中的所有 Pods。

</details>

### 3. NetworkPolicy 中哪些字段定义入站和出站规则？

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>显示答案</summary>

**答案：B. ingress/egress**

**解释：**
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

### 4. CiliumNetworkPolicy 中的 L7 HTTP 规则在哪里定义？

A. spec.http
B. spec.ingress.toPorts.rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>显示答案</summary>

**答案：B. spec.ingress.toPorts.rules.http**

**解释：**
CiliumNetworkPolicy 中的 L7 规则在 toPorts 内的 rules 部分定义：
```yaml
spec:
  ingress:
    - toPorts:
        - ports:
            - port: "80"
          rules:
            http:
              - method: GET
                path: "/api/.*"
```

</details>

### 5. 实现默认拒绝策略的正确 NetworkPolicy 是什么？

A. 在 policyTypes 中仅指定 Ingress
B. 将 podSelector 设置为空，并在 policyTypes 中指定 Ingress 和 Egress
C. 将 ingress 和 egress 规则留空
D. B 和 C 都正确

<details>
<summary>显示答案</summary>

**答案：D. B 和 C 都正确**

**解释：**
默认拒绝策略示例：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # Select all Pods
  policyTypes:
    - Ingress
    - Egress
  # No ingress and egress rules = block all traffic
```

空的 podSelector 会选择所有 Pods，而没有规则时，该流量类型会被阻止。

</details>

### 6. CiliumClusterwideNetworkPolicy 的特点是什么？

A. 仅适用于特定命名空间
B. 适用于整个集群
C. 仅控制外部流量
D. 仅支持 L7 策略

<details>
<summary>显示答案</summary>

**答案：B. 适用于整个集群**

**解释：**
CiliumClusterwideNetworkPolicy 会应用于整个集群，不受命名空间限制。它适合用于实现通用安全规则（例如，阻止所有命名空间访问元数据服务）。

</details>

### 7. 如何在 NetworkPolicy 中允许来自特定命名空间的所有 Pods？

A. 仅使用 namespaceSelector
B. 仅使用 podSelector
C. 将 namespaceSelector 与空的 podSelector 结合使用
D. 使用 namespace 字段

<details>
<summary>显示答案</summary>

**答案：A. 仅使用 namespaceSelector**

**解释：**
```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
```

仅使用 namespaceSelector 会允许来自该命名空间的所有 Pods。与 podSelector 一起使用时，只会选择该命名空间中的特定 Pods。

</details>

### 8. CiliumNetworkPolicy 中哪个字段定义基于 FQDN 的 egress 规则？

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>显示答案</summary>

**答案：A. toFQDNs**

**解释：**
CiliumNetworkPolicy 的 toFQDNs 允许基于 DNS 名称的 egress 流量：
```yaml
spec:
  egress:
    - toFQDNs:
        - matchName: "api.example.com"
        - matchPattern: "*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
```

</details>

### 9. 哪些流量不受 NetworkPolicy 影响？

A. Pods 之间的流量
B. 同一 Pod 中容器之间的流量 (localhost)
C. 通过 Services 的流量
D. 来自外部来源的流量

<details>
<summary>显示答案</summary>

**答案：B. 同一 Pod 中容器之间的流量 (localhost)**

**解释：**
NetworkPolicy 适用于 Pods 之间的网络流量。同一 Pod 中容器之间的 localhost 通信不属于 NetworkPolicy 的范围。此外，使用节点 hostNetwork 的 Pods 存在一些限制。

</details>

### 10. Cilium 的基于 Identity 的策略有什么优势？

A. 不受 IP 地址变化影响
B. 处理速度更快
C. 内存使用更少
D. 不需要 DNS 查询

<details>
<summary>显示答案</summary>

**答案：A. 不受 IP 地址变化影响**

**解释：**
Cilium Identity 是基于 Pod 标签生成的。即使 Pod 重启并且其 IP 发生变化，只要它具有相同的标签，就会保持相同的 Identity。这克服了基于 IP 的策略的局限性。

</details>

### 11. 在三层架构中，backend 层的正确网络策略是什么？

A. 允许所有流量
B. 仅允许来自 frontend 的 ingress
C. 允许来自 frontend 的 ingress，允许到 database 的 egress
D. 仅允许到 database 的 egress

<details>
<summary>显示答案</summary>

**答案：C. 允许来自 frontend 的 ingress，允许到 database 的 egress**

**解释：**
在三层微分段中，对于 backend：
- **Ingress**：仅允许来自 frontend 层
- **Egress**：仅允许到 database 层

这遵循最小权限原则，并清晰地控制层之间的流量流向。

</details>

### 12. 在 NetworkPolicy 中使用 ipBlock 指定 CIDR 范围时，哪个字段会排除特定 IP？

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>显示答案</summary>

**答案：B. except**

**解释：**
ipBlock 的 except 字段可以排除特定 CIDRs：
```yaml
ingress:
  - from:
      - ipBlock:
          cidr: 10.0.0.0/8
          except:
            - 10.0.1.0/24
            - 10.0.2.0/24
```

这允许来自 10.0.0.0/8 范围的流量，但不包括 10.0.1.0/24 和 10.0.2.0/24。

</details>
