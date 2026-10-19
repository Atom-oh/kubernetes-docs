# 网络策略

> **审查基线**：Kubernetes 1.35 OpenAPI、Cilium 1.20.3、Calico 3.32.2 和当前 AWS 文档。离线检查无法证明与集群兼容。
> **最后更新**：2026 年 10 月 16 日

Kubernetes NetworkPolicy 是用于控制 Pod 之间流量的防火墙规则。本文介绍基本 NetworkPolicy 以及 Cilium/Calico 扩展。各部分是彼此独立的示例；合并所有策略会改变实际生效的权限。未执行集群/云部署或实时连通性测试。

## 目录

1. [网络策略概述](#network-policy-overview)
2. [Kubernetes NetworkPolicy 规范](#kubernetes-networkpolicy-spec)
3. [默认拒绝策略](#default-deny-policies)
4. [策略顺序与评估](#policy-order-and-evaluation)
5. [Cilium 网络策略扩展](#cilium-network-policy-extensions)
6. [Calico 网络策略扩展](#calico-network-policy-extensions)
7. [设计模式](#design-patterns)
8. [测试网络策略](#testing-network-policies)
9. [EKS 注意事项](#eks-considerations)
10. [可视化工具](#visualization-tools)

---

## 网络策略概述 {#network-policy-overview}

### 什么是网络策略？

Kubernetes NetworkPolicy 会选择其所在命名空间中的 Pod，并控制受支持的入站和出站流量。对于某个方向，如果没有策略选择某个 Pod，该 Pod 在该方向上不会受到 NetworkPolicy 隔离；但路由、安全组、NACL 和其他策略引擎仍可能阻止连接。

**Pod 到 Pod 的连接必须由两端都允许**：源端的有效出站规则和目标端的有效入站规则都必须允许连接。已允许连接的返回流量会隐式放行。策略由支持它的网络插件异步实施；仅有 API 对象并不能证明策略已生效。对于节点/hostNetwork 流量以及 TCP/UDP/SCTP 之外的协议，需要根据具体实现进行审查。下图展示的是策略意图，不保证一定可达。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    No Network Policy (Default State)                     │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │◀──────▶│  Pod B  │◀──────▶│  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│         ▲                  ▲                  ▲                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│              Free communication between all Pods                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    With Network Policy Applied                           │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │───────▶│  Pod B  │        │  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│                            ▲                                            │
│                            │ Allowed                                    │
│                       ┌────┴────┐                                       │
│                       │Controlled│                                      │
│                       │by Policy │                                      │
│                       └─────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 网络策略的特性

| 属性 | 说明 |
|----------|-------------|
| **命名空间范围** | NetworkPolicy 适用于某个命名空间内的资源 |
| **累加式** | 对于每个方向，选择 Pod 的 Kubernetes NetworkPolicy 的允许规则会形成并集；Cilium 拒绝规则、Calico 层级以及 AWS 管理策略有各自独立的语义 |
| **选择性应用** | 通过 podSelector 指定目标 Pod |
| **方向控制** | 分别控制 Ingress（入站）和 Egress（出站） |
| **依赖 CNI** | CNI 插件必须支持 NetworkPolicy |

### CNI 对 NetworkPolicy 的支持

| CNI | 基本 NetworkPolicy | 扩展 | L7 策略 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy、CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy、NetworkSet、Tier | 可选的 Istio/Dikastes 集成；请验证已部署的产品和版本 |
| **Weave Net（已归档项目）** | 历史上支持 | 仅供参考的旧版实现；新部署应评估仍在维护的实现 | ✗ |
| **仅 Flannel** | 自身不执行策略 | 需要单独使用受支持的策略引擎 | ✗ |
| **Amazon VPC CNI** | ✓ 在受支持的 EC2 Linux 节点上启用后 | 标准 NetworkPolicy；VPC CNI 1.21+ 支持 ClusterNetworkPolicy | EKS Auto Mode 节点上的 DNS 出站；参见 EKS 注意事项 |

---

## Kubernetes NetworkPolicy 规范 {#kubernetes-networkpolicy-spec}

### 基本结构

请显式指定 `policyTypes`。如果省略，Kubernetes 默认使用 Ingress；当至少有一条出站规则时，还会添加 Egress。仅有空规则数组并不表示两个方向都包含在内。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
spec:
  # Select Pods to apply policy
  podSelector:
    matchLabels:
      app: web

  # Policy types (auto-inferred if omitted)
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (inbound traffic)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
        - namespaceSelector:
            matchLabels:
              project: myproject
        - ipBlock:
            cidr: 172.17.0.0/16
            except:
              - 172.17.1.0/24
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

  # Egress rules (outbound traffic)
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - protocol: TCP
          port: 5432
```

### podSelector

选择策略在其所在命名空间中适用的 Pod。以下是可相互替代的 spec 片段，并非独立的 API 资源。

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

---
# Apply to all Pods (empty selector)
spec:
  podSelector: {}

---
# Using matchExpressions
spec:
  podSelector:
    matchExpressions:
      - key: app
        operator: In
        values:
          - api
          - web
      - key: environment
        operator: NotIn
        values:
          - development
```

### namespaceSelector

按标签选择命名空间；如果当前命名空间符合条件，也会被选中。`name` 并不是自动分配的命名空间标签。要精确匹配命名空间名称，请使用内置且不可变的 `kubernetes.io/metadata.name` 标签；并限制可更改自定义租户标签的用户。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        # Allow all Pods from monitoring namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              role: frontend
```

**注意**：同时使用 `namespaceSelector` 和 `podSelector` 时，AND 与 OR 的区别：

```yaml
# OR condition (two separate peer entries)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            kubernetes.io/metadata.name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

---
# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            kubernetes.io/metadata.name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

`ipBlock` 会允许该规则中 CIDR 范围内、但不属于其 `except` 范围的地址。例外范围不是全局拒绝；其他策略仍可允许该流量。Service/负载均衡器的地址转换可能改变 CNI 可见的源地址或目标地址；请验证实际流量路径。以下文档 CIDR 仅作示例，并非可访问的生产端点。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: public-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        # Example private source range; not a guarantee of the load balancer source IP
        - ipBlock:
            cidr: 10.0.0.0/8
        # Allow specific external IP
        - ipBlock:
            cidr: 203.0.113.0/24
  egress:
    - to:
        # Allow external API server access
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8      # Exclude internal networks
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### ports

指定允许的端口和协议。`endPort` 要求起始端口为数字，并且 CNI 支持端口范围；命名端口不能用作范围的起始端口。API 接受配置并不能证明每个插件都会执行该规则。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-specific-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        # Specific ports
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
        # Port range (Kubernetes 1.25+)
        - protocol: TCP
          port: 8000
          endPort: 8080
        # Named port
        - protocol: TCP
          port: http
```

---

## 默认拒绝策略 {#default-deny-policies}

空白基线本身不提供任何允许规则；其他选择该 Pod 的策略仍可允许流量。策略变更后，已有连接的行为取决于具体实现，必须单独测试。

### 默认拒绝 Ingress

不包含任何自身允许规则的 Ingress 隔离基线。其他选择该 Pod 的策略仍可允许 Ingress：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Apply to all Pods
  policyTypes:
    - Ingress
  # No ingress rules = block all inbound traffic
```

### 默认拒绝 Egress

不包含任何自身允许规则的 Egress 隔离基线。其他选择该 Pod 的策略仍可允许 Egress：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  # No egress rules = block all outbound traffic
```

### 完全拒绝（Ingress + Egress）

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 默认拒绝但允许 DNS

此配置假定 `kube-system` 中运行基于 Pod 的 CoreDNS，且标签为 `k8s-app=kube-dns`。它同时允许 TCP 和 UDP 53 端口。如果 DNS 本身受到 Ingress 隔离，其策略也必须允许客户端。NodeLocal DNSCache 和 Auto Mode 节点本地 CoreDNS 需要使用其实际解析器路径/IP 配置；不要在这些场景中原样套用此 Pod 选择器。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress-allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### 零信任架构默认策略

已分别配置 frontend→API 的两个方向。此配置不允许对 frontend 或 API→database 的入站流量；请仅添加经过审查的流量。DNS 使用上述基于 Pod 的假设。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zero-trust-default
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
```

## 策略顺序与评估 {#policy-order-and-evaluation}

### 策略评估规则

对于每个端点和方向，按下文评估选择该端点的**Kubernetes NetworkPolicy**。然后检查另一端的相应方向以及所有其他网络控制措施。仅包含 ingress 的策略不会隔离 egress。

```
┌─────────────────────────────────────────────────────────────────┐
│                  NetworkPolicy Evaluation Flow                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Are there policies that apply to the Pod?                   │
│     │                                                           │
│     ├─ No → Allow all traffic (default behavior)                │
│     │                                                           │
│     └─ Yes → Start policy evaluation                            │
│              │                                                  │
│              ▼                                                  │
│  2. Is there a policy for this direction (Ingress/Egress)?      │
│     │                                                           │
│     ├─ No → Allow traffic in that direction                     │
│     │                                                           │
│     └─ Yes → Start rule matching                                │
│              │                                                  │
│              ▼                                                  │
│  3. Does traffic match one or more rules?                       │
│     │                                                           │
│     ├─ Matched → Allow traffic                                  │
│     │                                                           │
│     └─ Not matched → Block traffic                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 合并多个策略

当多个 NetworkPolicy 适用于同一个 Pod 时，所有策略规则会合并（取并集）：

```yaml
---
# Policy 1: Allow traffic from frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
# Policy 2: Allow traffic from monitoring
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**结果**：API 的 ingress 允许 frontend Pod 使用 8080 端口，也允许 monitoring 命名空间中的 Pod 使用 8080/9090 端口。其 egress 规则、实际监听器和其他网络控制措施也必须允许该连接。

### 策略评估顺序

Kubernetes NetworkPolicy API 没有优先级或显式拒绝规则。其允许规则并集并不涵盖 Calico 策略顺序/层级操作、Cilium 显式拒绝规则或 AWS 管理策略评估：

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Policy A    Policy B    Policy C                              │
│   (allow X)   (allow Y)   (allow Z)                             │
│       │           │           │                                 │
│       └───────────┼───────────┘                                 │
│                   │                                             │
│                   ▼                                             │
│           ┌───────────────┐                                     │
│           │     Union     │                                     │
│           │ (X OR Y OR Z) │                                     │
│           └───────────────┘                                     │
│                   │                                             │
│                   ▼                                             │
│           Final allowed traffic:                                │
│           X, Y, Z all allowed                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cilium 网络策略扩展 {#cilium-network-policy-extensions}

这些示例使用已发布的 Cilium 1.20.3 策略架构，并非要求所有集群都升级。HTTP 规则需要受支持的 L7 代理路径。AWS VPC CNI 链接模式对高级功能有文档说明的限制，包括 L7 策略；不要假设这些 HTTP 示例在该模式下可用。Cilium 数字安全身份是为一组标签分配的标识，不是永久的应用 ID。

### CiliumNetworkPolicy

Cilium 在基本 NetworkPolicy 的基础上扩展了更强大的功能。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cilium-l7-policy
  namespace: production
spec:
  # Endpoint selection
  endpointSelector:
    matchLabels:
      app: api

  # L3/L4 rules (similar to basic NetworkPolicy)
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          # L7 rules (Cilium extension)
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/users"
                headers:
                  - 'Content-Type: application/json'
```

### L7 HTTP 策略

Cilium HTTP 规则会过滤其 L7 代理可见的请求；它们不会验证 API 密钥或设置管理员角色。调用方可以自行提供 `X-User-Role` 标头。此示例会筛选请求方法、路径和完全匹配的 `Content-Type`。请在应用或经过身份验证的网关中实施身份验证和授权。系统不会自动解密端到端 TLS 以进行 HTTP 检查。请审查其他可能在 L4 允许相同流量的策略。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-api-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
        - method: GET
          path: /api/v1/products/[0-9]+
        - method: POST
          path: /api/v1/orders
          headerMatches:
          - name: Content-Type
            value: application/json
```

[HTTP API（Cilium 1.20.3）](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/http.go)

### L7 Kafka 策略

已发布的 Cilium 1.20.3 CNP 架构支持 HTTP 和 DNS L7 规则，但没有 `rules.kafka`。旧版的 `role`、`topic` 和 `clientID` 配置示例不是当前可部署的 API。请使用网络策略限制 Broker 连接，然后通过 Kafka 身份验证和 ACL 控制对 `orders` 和 `events` 的生产者/消费者权限。客户端 ID 不是经过身份验证的主体。

此 L4 示例假定已配置 TCP 9093 上的 TLS Broker 监听器、同一命名空间中的客户端，以及已单独授权客户端的 egress/DNS。它不会配置 TLS、Broker ACL 或主题权限。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-client-network-access
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: producer
    - matchLabels:
        app: consumer
    toPorts:
    - ports:
      - port: '9093'
        protocol: TCP
```

[CNP 架构（Cilium 1.20.3）](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### L7 DNS 策略

此示例使用基于 Pod 的 CoreDNS。端口 53 上的 `ANY` 同时涵盖 UDP 和 TCP。DNS 查询权限与连接到返回 IP 的权限是分开的：解析下面的数据库名称并不允许连接数据库。请替换示例域名，并考虑 DNS 搜索后缀、缓存和 TTL；同时验证实际解析器配置。FQDN 规则会从 DNS 中学习 IP；它们不会验证 SaaS 租户身份，也不能取代 TLS/应用授权。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchName: api.example.com
        - matchName: database.production.svc.cluster.local
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### CiliumClusterwideNetworkPolicy

该资源的作用范围是整个集群，但其选择器明确将范围限制为 `production/app=api`。它允许 gateway Pod 使用 TCP 8080。它只控制 ingress；egress 隔离/DNS 以及 gateway 自身的 egress 需要配置相应策略。之前允许所有端点/所有外部流量的集群范围示例并不是默认拒绝策略。

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-api-from-edge
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: gateway-system
        app: edge-proxy
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

### 基于 Cilium 实体的策略

`host` 包括本地节点及其 host-network 容器；`cluster` 包含的对象不止应用 Pod。`world` 涵盖集群外部的端点，并不是细粒度的 Internet/SaaS 允许列表。需要收紧外部访问时，请使用显式 CIDR/FQDN 规则。此示例仅允许带标签的 Kubernetes API 客户端访问 TCP 443；请另行配置 API 端点、TLS 信任、凭证和 RBAC。在托管控制平面网络路径中，源身份可能发生变化，因此请检查实际流量身份，而不是将 ingress 范围扩大到整个集群。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kubernetes-api-client
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: kubernetes-api-client
  egress:
  - toEntities:
    - kube-apiserver
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

## Calico 网络策略扩展 {#calico-network-policy-extensions}

策略/Tier 示例遵循 Calico Open Source 3.32.2 资源的规范。`projectcalico.org/v3` 需要受支持的 Calico API server 或匹配的 `calicoctl` 工作流；它不是原始 Kubernetes `crd.projectcalico.org/v1` 存储 API。应用前请验证已安装的数据存储/API。Calico 的有序操作和 Tier 委派与累加式 Kubernetes NetworkPolicy API 不同。

当前 Open Source 文档还介绍了 [Istio/Dikastes 应用层集成](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)。HTTPMatch API 需要单独配置，并支持 Ingress Allow 规则。以下 Calico 示例涵盖 L3/L4 策略；本次审查未部署或测试 L7 集成。

### Calico NetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: calico-policy
  namespace: production
spec:
  # Policy order (lower = evaluated first)
  order: 100

  selector: app == 'api'

  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### GlobalNetworkPolicy

以下两个全局资源只选择 `production` 命名空间中的工作负载。没有范围限制的 `selector: all()` 也可能影响 host endpoint；没有明确范围和恢复途径时，不要应用集群范围的拒绝策略。在同一 Tier 中，较小的 `order` 值先评估。此示例允许基于 Pod 的 DNS，并提供默认拒绝基线；请添加经过审查的应用流量，并考虑高优先级 Tier 的操作。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-default-deny
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 1000
  types:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-allow-dns
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 100
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

### NetworkSet

NetworkSet 选择器匹配 `metadata.labels`，而不是资源名称。第一个集合属于命名空间范围；被阻止的集合是全局集合，供下面的 security-tier 示例使用。这里所有 CIDR 都是文档示例范围，必须替换为经过审查的目标。此 egress 示例允许 TCP 443 访问带标签的命名空间范围集合；DNS 需要单独配置规则。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
  labels:
    network-role: external-api
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.10/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    network-role: blocked
spec:
  nets:
  - 192.0.2.0/24
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-apis
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      selector: network-role == 'external-api'
      ports:
      - 443
```

### 基于 Tier 的策略

引用的 Calico Open Source 版本提供 Tier 功能，并非仅 Enterprise 版才有。当 Tier 选择了端点且没有任何规则匹配时，默认操作为 `Deny`。因此，deny-known-threats Tier 会显式使用 `defaultAction: Pass`，使不相关的流量继续进入后续策略。`Pass` 表示委派，不表示允许。`global()` 应放在 `namespaceSelector` 中；单独的标签选择器用于识别 GlobalNetworkSet。在部署前，请填充 application-tier 策略，并验证任何最终 profile/default-tier 行为；创建一个空 Tier 并不是完整的应用隔离策略。

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300
  defaultAction: Deny
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Ingress
  ingress:
  - action: Deny
    source:
      selector: network-role == 'blocked'
      namespaceSelector: global()
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

## 设计模式 {#design-patterns}

这些是**彼此可替代的策略配置**，不是可一起应用的一组配置。重复使用 `production` 并不会让互不相关的示例彼此兼容：它们的允许规则会累加。请先准备好命名空间、工作负载标签、监听端口和实际 DNS 配置。这些示例仅在本地进行了架构/意图检查，未在集群上运行。

### 微分段

此配置允许 frontend→API 的 TCP 8080 和 API→database 的 TCP 5432，并在两端均配置规则，同时允许 DNS。它特意不包含 Internet egress 或外部 frontend ingress。如有需要，请添加经批准的目标 CIDR/端口或经过身份验证的 egress gateway 配置；从 0.0.0.0/0 中排除 RFC1918 地址并不等于 SaaS 允许列表。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

### 命名空间隔离

团队配置包含同团队之间的 ingress **和 egress**，以及 DNS。共享服务还需要在目标端配置允许 team-a 的 ingress 规则，并提供实际的 TLS 443 监听器。请限制命名空间标签的管理权限；团队标签本身并不是独立的信任边界。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - &id001
      namespaceSelector:
        matchLabels:
          team: team-a
  egress:
  - to:
    - *id001
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-services
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          shared-services: 'true'
      podSelector:
        matchLabels:
          exposed: 'true'
    ports:
    - protocol: TCP
      port: 443
```

### 数据库保护

`database` 命名空间必须存在。生产环境调用方和 monitoring Pod 需要各自配置 egress 允许规则。TCP 5432 对等规则只允许假设的 PostgreSQL 复制传输；数据库身份验证/TLS 需要单独配置。TCP 9187 假设已单独安装 exporter。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-protection
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
      podSelector:
        matchLabels:
          database-access: 'true'
    ports:
    - protocol: TCP
      port: 5432
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9187
  - from:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### 三层架构策略

假定存在 `gateway-system/app=edge-proxy` 工作负载，该工作负载终止客户端 TLS，并可通过 TCP 80 访问 web Pod。gateway 的 egress 策略不在此命名空间内。数据层对等 ingress 和 egress 使用 TCP 5432/6379；额外的复制/集群总线/备份端口取决于所选数据库，此处未包含。实际部署中应拆分 PostgreSQL 和 Redis 选择器。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: gateway-system
      podSelector:
        matchLabels:
          app: edge-proxy
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: data
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-dns
  namespace: production
spec:
  podSelector:
    matchExpressions:
    - key: tier
      operator: In
      values:
      - web
      - app
      - data
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

---

## 测试网络策略 {#testing-network-policies}

### 使用 netshoot 进行测试

使用已获批准且预先配置的诊断 Pod，并为其固定镜像和审查权限。选择实际会测试该策略的源标签/命名空间/节点位置；通用的无标签 Pod 并不能代表应用。配置 netshoot 会创建工作负载，并可能与 Pod Security 准入冲突。不要在观察脚本中创建/删除固定的共享 `test-pod` 名称。仅对自有测试端点运行探测。

### 使用 kubectl exec 进行测试

请明确设置 context、命名空间、现有 Pod 和容器。DNS 成功不等于 TCP 成功；连接被拒、监听器不健康、TLS 错误和策略丢弃是不同结果。这些命令仅测试连通性，不会打印响应正文。本次审查期间未在集群上运行这些命令。

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Cilium 连通性测试

`cilium connectivity test` 会创建测试资源并生成流量；它不是只读的状态命令。请使用获准的隔离集群/命名空间、兼容的 CLI 和镜像、明确指定的外部目标以及清理计划。请查阅 `cilium connectivity test --help` 中已安装 CLI 的筛选器，不要假设历史测试名称仍然存在。测试套件通过并不能证明每个应用策略或 CNI 链接功能都有效。

### 自动化测试脚本

此脚本只会在两个现有 Pod 中执行有界 curl 探测；不会创建或删除集群资源。请设置 `CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER` 和一个以 `/health` 结尾的非机密 `TARGET_URL`。两个容器都需要包含 `sh` 和 `curl`。第一个 Pod 是针对同一目标的已知允许正向控制。即使 HTTP 返回错误响应，也仍能证明网络可达，因为此测试不验证应用健康状况。

exit1 表示被阻止的对象意外建立了连接；exit2 表示未知/错误；exit3 表示超时，需要进一步佐证。超时**绝不会**自动变成 PASS：请将精确的源/目标/端口/时间与 CNI 策略丢弃判定关联，同时检查端点健康状况、路由和 SG/NACL 控制。本地模拟测试不代表策略已在实时环境中生效。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
: "${NAMESPACE:?Set the test namespace}"
: "${ALLOW_POD:?Set an existing positive-control Pod}"
: "${DENIED_POD:?Set a different existing policy-subject Pod}"
: "${PROBE_CONTAINER:?Set a container with sh and curl in both Pods}"
: "${TARGET_URL:?Set the same non-secret health URL for both probes}"
if [[ "$ALLOW_POD" == "$DENIED_POD" ||
      ! "$TARGET_URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?/health$ ]]; then
  echo "Invalid probe inputs: use different Pods and a plain /health URL." >&2
  exit 2
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-probe.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
probe() {
  local pod=$1 result
  if ! result=$(kubectl --context="$CONTEXT" --request-timeout=15s \
      -n "$NAMESPACE" exec "$pod" -c "$PROBE_CONTAINER" -- \
      sh -c 'rc=0
        curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$1" || rc=$?
        printf "PROBE_EXIT=%s\n" "$rc"' sh "$TARGET_URL" \
      2>"$work/transport-error"); then
    echo "UNKNOWN: kubectl exec/authorization/transport failed." >&2
    return 2
  fi
  if [[ ! "$result" =~ ^PROBE_EXIT=([0-9]+)$ ]]; then
    echo "UNKNOWN: missing or malformed remote probe result." >&2
    return 2
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}
allowed=$(probe "$ALLOW_POD") || exit 2
if [[ "$allowed" != 0 ]]; then
  echo "UNKNOWN: positive control could not reach the target." >&2
  exit 2
fi
denied=$(probe "$DENIED_POD") || exit 2
case "$denied" in
  0) echo "FAIL: the intended blocked Pod reached the target."; exit 1 ;;
  28) echo "INCONCLUSIVE: timeout; correlate an actual policy-drop verdict."; exit 3 ;;
  *) echo "UNKNOWN: DNS/TLS/refused/tool error is not proof of a policy drop."; exit 2 ;;
esac
```

## EKS 注意事项 {#eks-considerations}

### Amazon VPC CNI 和 NetworkPolicy

启用后，Amazon VPC CNI 支持网络策略。AWS 当前指南要求标准策略和管理策略都使用 VPC CNI 1.21+、兼容的 EKS 平台以及 Linux 内核 5.10+。策略仅在受支持的 EC2 Linux 节点上生效，不适用于 Fargate 或 Windows。请使用当前受支持的 EKS 版本，并验证其兼容的插件版本；不要根据上游 Kubernetes 版本推断 EKS 支持情况。

对于**由 EKS 管理**的 VPC CNI 插件，请保留现有配置，同时设置文档所述字符串 `"enableNetworkPolicy": "true"`。以下操作会更改选定集群，但不会升级插件版本。如果已安装版本不兼容，请停止操作，并先遵循文档中的升级流程。

```bash
# Requires AWS CLI, kubectl and jq; use an approved test cluster.
set -euo pipefail
: "${CLUSTER_NAME:?Set the approved test-cluster name}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --output json > vpc-cni-before.json
jq -e '(.addon.configurationValues // "{}") | if . == "" then {} else fromjson end
  | .enableNetworkPolicy = "true"' vpc-cni-before.json > vpc-cni-network-policy.json
# Review the saved current version/configuration and the complete merged JSON first.
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --configuration-values file://vpc-cni-network-policy.json --resolve-conflicts PRESERVE
```

部署前请检查更新状态和策略行为。`--resolve-conflicts PRESERVE` 不会替你合并替换后的 JSON 文档；此示例会显式保留现有值。请保留快照以便恢复。使用 Helm 管理的安装应通过审查过的 Chart/values 配置，并设置 `enableNetworkPolicy: true`；不要通过此托管插件命令接管其所有权。设置虚构的 `ENABLE_NETWORK_POLICY` 环境变量并不是启用流程。

在标准启动模式下，新 Pod 刚启动时可能暂时允许流量，直到其策略完成配置。`NETWORK_POLICY_ENFORCING_MODE=strict` 会让符合条件的 Pod 以拒绝状态启动，并要求提供完整的允许矩阵，包括 DNS；更改此设置可能中断工作负载。由控制器管理的 Pod 是可靠的测试目标。策略在 Pod 的主接口上生效，因此请单独检查额外接口、IPv6 到 IPv4 的出站流量、host networking 和 NAT。不要安装两个引擎来管理相同的标准策略，也不要把删除 `aws-node` 当作迁移捷径。

### EKS 增强网络安全策略（2025 年 12 月）

> **公告日期**：2025 年 12 月 15 日 · [来源](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

此功能确实存在，但其资源使用 **`networking.k8s.aws/v1alpha1`**。`ClusterNetworkPolicy` 的作用范围是整个集群，且必须指定 `tier`；下面的命名空间示例使用 `ApplicationNetworkPolicy` 配置基于 DNS 的 egress。EC2 Linux 上支持标准/管理型 VPC CNI 策略，不代表所有计算模式都支持这些策略。DNS 规则仅在 **Auto Mode 启动的 EC2 实例**上强制执行，即使集群是混合模式也如此。

**Auto Mode 前置条件**：应用以下策略之前，先启用其 Network Policy Controller。更新由 EKS 管理的 `vpc-cni` 插件属于另一种路径，并不会为纯 Auto Mode 集群启用策略强制执行。所需设置为 ConfigMap `kube-system/amazon-vpc-cni` 中的 `data.enable-network-policy-controller: "true"`。以下工作流使用 merge patch 保留其他 ConfigMap 数据；仅在 ConfigMap 不存在时才创建，并在读取或写入失败时停止。运行前请检查集群 context 和现有配置。

```bash
set -euo pipefail
config="$(kubectl get configmap amazon-vpc-cni -n kube-system --ignore-not-found -o name)"
if [ -n "$config" ]; then
  kubectl patch configmap amazon-vpc-cni -n kube-system --type merge \
    -p '{"data":{"enable-network-policy-controller":"true"}}'
else
  kubectl create configmap amazon-vpc-cni -n kube-system \
    --from-literal=enable-network-policy-controller=true
fi
kubectl get configmap amazon-vpc-cni -n kube-system -o json \
  | jq -e '.data["enable-network-policy-controller"] == "true"'
```

启用后，请检查相应的 `PolicyEndpoints` 对象，并在选定的 Auto Mode 节点上测试允许和拒绝的流量。已存储的标志或已接受的策略对象并不能证明策略已生效。请参见 [Auto Mode 网络策略设置](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)。本次文档审计未进行集群策略生效测试。

此 Admin-tier 示例会拒绝从 namespace-selected Pod 到 `isolated-demo` 的入站流量，包括来自同一命名空间中 Pod 的流量。它不是完整的外部/host-network 防火墙，也不是 DNS 允许策略。namespace NetworkPolicy 无法覆盖 Admin Deny。添加其他操作之前，请检查实际安装的 CRD：当前上游 AWS 控制器架构将其允许操作命名为 `Accept`，而用户指南的正文使用“Allow”。

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: isolate-demo-namespace
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces:
      matchLabels:
        kubernetes.io/metadata.name: isolated-demo
  ingress:
  - name: deny-pod-ingress
    action: Deny
    from:
    - namespaces:
        matchLabels: {}
```

FQDN 示例选择 `production` 中的 `app=backend`。**请将 `10.100.0.10/32` 替换为集群实际的 Auto Mode CoreDNS IP**：它是 Service CIDR 网络地址加 10（IPv6 使用 `::a/128`）。纯 Auto Mode 的 CoreDNS 在节点上运行；传统 CoreDNS Pod 选择器不能与之互换。请同时允许 TCP 和 UDP DNS。请使用不会与该命名空间中的 NetworkPolicy 冲突的唯一资源名称。

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ApplicationNetworkPolicy
metadata:
  name: approved-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.100.0.10/32
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - domainNames:
      - api.stripe.com
    ports:
    - protocol: TCP
      port: 443
```

DNS 代理会观察获准的应答及其 TTL，随后数据路径允许访问已学习到的目标 IP/端口。这不会验证 SaaS 账户身份，也不能证明对端的 HTTP 身份；共享 IP 和 DNS 行为需要测试。TLS 证书验证、应用授权、路由以及任何 Route 53 DNS Firewall 规则仍然相关。必须一并审查其他适用策略和直连后端的路径。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode 策略](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Pod 的安全组

此绑定示例假定使用 EKS VPC Resource Controller、其**集群角色**权限、受支持且兼容 trunking 的 EC2 Linux 节点，以及经过审查的 VPC CNI 配置。AWS 当前指南排除 Windows 和 EKS Auto Mode。Fargate 使用单独的 Pod-SG 模型；仅配置安全组并不会让它获得 VPC-CNI NetworkPolicy 支持。请通过工作负载的所属控制器将绑定应用于新建的匹配工作负载 Pod；现有 Pod 不会自动补齐绑定。

对于与 Pod SG 配合使用的 Calico，AWS 文档要求 VPC CNI 1.11.0+ 和 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`；同时还应遵循当前 CNI 要求，而不要将该最低版本视为推荐版本。在标准模式下，外部 SNAT 可能使用节点 SG，而不是 Pod SG。请验证具体流量路径。旧版简单的 PostgreSQL Pod 没有凭证/存储，并不是可正常运行的数据库部署。

```yaml
# Binding example only: use an existing reviewed security group.
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Terraform 片段允许来自一个经过审查的应用 SG 的数据库入站流量，不会发起新的出站连接。借助 SG 跟踪，有状态返回流量会被允许；请另行添加所需的 DNS、复制、备份或外部 egress。变量是现有的运维人员输入；未执行 Terraform plan/apply。

```hcl
# Fragment for an existing reviewed Terraform configuration.
# Supply the actual VPC and application SG; this is not a standalone module.
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group_id]
  }
  egress = []
}
```

### 将 VPC 层控制与 NetworkPolicy 结合使用

NetworkPolicy、实际应用的 SG 和 NACL 都必须允许相关路径。此 ingress-only NetworkPolicy 不会限制数据库 egress；请添加选定的 egress 配置以及源 Pod 的 egress 规则。多个 SG 的允许规则会合并。NACL 是**无状态的**，因此允许入站 5432 的子网规则还需要匹配返回客户端临时端口的路径，并且客户端子网也需要配置适当的规则。以下片段不能替代经过完整审查的 ACL 规则集。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Fragments for a DB subnet NACL and an explicitly reviewed client CIDR.
# Choose the client's actual ephemeral port range; also review its subnet NACL.
resource "aws_network_acl_rule" "database_inbound" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "database_return" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = var.client_ephemeral_port_start
  to_port        = var.client_ephemeral_port_end
}
```

### 在 EKS 上使用 Cilium

请选择 **AWS VPC CNI 链接模式**，或另行设计完整的 CNI/IPAM 迁移。在链接模式下，AWS VPC CNI 仍负责 ENI/IPAM，Cilium 则连接其数据路径。请保留 `aws-node`；删除它并不是安装捷径。请检查现有的插件/Helm 管理方式，并避免让策略强制执行引擎相互重叠。现有 Pod 需要经过控制地重新创建，链接模式的策略才能生效；请规划中断和回滚方案。

官方 1.20.3 链接指南提供了以下 values，但也说明了 L7/IPsec 的限制。指南中包含的是较早的示例输出；这些输出不能验证当前 EKS 环境。请先准备 Chart 仓库/软件包，验证来源并进行渲染：

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI 链接模式（Cilium 1.20.3）](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## 可视化工具 {#visualization-tools}

### Cilium Network Policy 编辑器

策略编辑器可辅助编写策略；**Hubble UI 用于可视化已观测到的服务流量**。它们是不同的工具。启用 Hubble/UI 会更改集群配置，应由安装管理方负责。若已安装经过身份验证的 Hubble 服务，请检查现有服务并使用本地端口转发。不要为了调试而将 UI 暴露到公网。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### 检查 Cilium 策略判定

请使用经过身份验证的 Hubble 连接。`DROPPED` 也可能表示策略之外的其他原因；请检查丢弃原因、端点身份、时间和方向。在某个观察点看到 `FORWARDED` 并不保证端到端交付。


```bash
# Inspect observed policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### Calico Enterprise UI

Enterprise 管理 UI 需要许可产品及其实际的服务/TLS/身份验证配置；它不会随 Calico Open Source 自动安装。进行端口转发前，请检查已安装的服务名称/端口和访问策略。不要假设每种安装中都存在 `cnx-manager`。

### 网络策略可视化工具

使用 `kubectl get networkpolicy -n <namespace>` 和 `kubectl describe networkpolicy <name> -n <namespace>` 检查 Kubernetes 策略选择器/规则，并使用已安装引擎经过身份验证的流量工具检查策略实施情况。必须根据相应项目的当前版本检查第三方查看器/插件是否可用以及支持哪些标志。仅根据 YAML 绘制的图表无法证明数据平面策略已生效。

### 使用 Kube-hunter 进行安全测试

kube-hunter 是集群暴露面/安全扫描器，不是用于验证 NetworkPolicy 允许/拒绝行为的工具。其扫描可能产生侵入性流量；请使用明确获批的目标/范围以及经过审查的版本/镜像。不要在通用策略教程中把未固定版本的扫描器部署到生产命名空间。本次审查未运行扫描器。

## 最佳实践

### 1. 应用默认拒绝策略

```yaml
# Applies only to this production namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. 最小权限原则

仅显式允许必需的流量：

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
          protocol: TCP
```

### 3. 记录策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    review-ticket: "REPLACE_WITH_APPROVED_CHANGE"
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### 4. 定期审计策略

此只读清单会分别列出命名空间范围内 ingress 和 egress 的空允许基线。它会处理空的 `[]` 和缺失的规则数组，而规则 `{}` 表示允许流量，并不是拒绝基线。API/授权错误会导致命令失败，而不是被当作策略数量为零。列出基线**并不能证明已实现隔离**：仍需审查其他允许规则、扩展策略、未覆盖的 Pod 和 CNI 状态。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-inventory.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
if ! kubectl --context="$CONTEXT" --request-timeout=15s get namespaces -o json >"$work/namespaces.json"; then
  echo "UNKNOWN: namespace inventory failed." >&2
  exit 2
fi
if ! kubectl --context="$CONTEXT" --request-timeout=15s get networkpolicies -A -o json >"$work/policies.json"; then
  echo "UNKNOWN: policy inventory failed." >&2
  exit 2
fi
jq -n --slurpfile ns "$work/namespaces.json" --slurpfile np "$work/policies.json" '
  def directions:
    (.spec.policyTypes // []) as $types |
    if ($types | length) > 0 then $types
    else ["Ingress"] + (if ((.spec.egress // []) | length) > 0 then ["Egress"] else [] end)
    end;
  def selects_all:
    ((.spec.podSelector.matchLabels // {}) | length) == 0 and
    ((.spec.podSelector.matchExpressions // []) | length) == 0;
  def empty_baseline($direction; $rules):
    select(selects_all and ((directions | index($direction)) != null) and
           ((.spec[$rules] // []) | length) == 0) | .metadata.name;
  {
    note: "Inventory only: other allow rules, extension policies and CNI enforcement are not evaluated.",
    namespaces: [
      $ns[0].items[] | .metadata.name as $name |
      [$np[0].items[] | select(.metadata.namespace == $name)] as $policies |
      {
        namespace: $name,
        policyCount: ($policies | length),
        ingressBaselines: [$policies[] | empty_baseline("Ingress"; "ingress")],
        egressBaselines: [$policies[] | empty_baseline("Egress"; "egress")]
      }
    ]
  }
'
```

## 将 NetworkPolicy 与边界检查关联起来

NetworkPolicy 通过受支持的 CNI 强制实施 Pod 连接策略；它不会自动创建所有 WAF 或中央防火墙路径。不要假设同节点、VPC 内部、PrivateLink、对等连接或 IPv6 流量会自动经过中央 TGW 检查。

将公共应用连接到 [WAF/源站保护](./14-waf-edge-api-security.md)，并将出站/VPC 间流量连接到 [Palo Alto/Fortinet](./15-ngfw-paloalto-fortinet.md) 和 [GWLB/GENEVE](./16-gwlb-geneve-inspection.md)。请验证 Pod/节点 SNAT 和请求/响应五元组，并分别测试策略结果与设备转发路径。有关 webhook 和 Secret 权限调查，请参见[纵深防御与事件响应](./13-defense-in-depth-incident-response.md)。

## 总结

Kubernetes NetworkPolicy 是控制集群内 Pod 通信的核心安全机制：

1. **基本 NetworkPolicy**：命名空间范围，支持 podSelector/namespaceSelector/ipBlock
2. **Cilium 扩展**：L7 策略、基于 DNS FQDN 的策略、集群范围策略
3. **Calico 扩展**：GlobalNetworkPolicy、NetworkSet、基于 Tier 的策略
4. **EKS 注意事项**：启用 VPC CNI NetworkPolicy、Pod 的安全组、ClusterNetworkPolicy 和基于 DNS（FQDN）的 egress 控制

### 建议

- 对所有生产命名空间应用默认拒绝策略
- 遵循最小权限原则，只允许必需的流量
- 定期审计并测试策略
- 需要 L7 策略时可考虑使用 Cilium

---

## 参考资料

- [Kubernetes Network Policies 官方文档](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium 网络策略文档](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico 网络策略文档](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS 安全最佳实践 - 网络安全](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS 增强网络安全策略（2025-12-15）](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod 安全组](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
