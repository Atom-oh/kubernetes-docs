# 网络策略

> **审查基线**：Kubernetes 1.35 OpenAPI、Cilium 1.20.1、Calico 3.32.2 以及当前 AWS 文档。离线检查无法确认集群兼容性。
> **最后更新**：September 13, 2026

Kubernetes NetworkPolicy 是控制 Pod 间流量的防火墙规则。本文涵盖基础 NetworkPolicy 以及 Cilium/Calico 扩展。各章节均为独立示例；合并所有策略会改变实际生效的权限。未执行任何集群/云部署或实时连通性测试。

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

Kubernetes NetworkPolicy 在其所在的 namespace 中选择 Pod，并控制所支持的入站和出站流量。若某个方向没有选中该 Pod 的策略，该方向不会被 NetworkPolicy 隔离；路由、安全组、NACL 和其他策略引擎仍可阻止连通性。

**两个端点都必须允许** Pod 到 Pod 的连接：源端有效的 egress 规则和目的端有效的 ingress 规则都必须允许该连接。已允许连接的返回流量会被隐式允许。策略由支持它的网络插件异步实施；仅有 API 对象不能证明已实施。Node/hostNetwork 流量以及 TCP/UDP/SCTP 以外的协议需要按实现进行审查。下图展示的是策略意图，而非可达性保证。

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

### 网络策略特性

| 属性 | 说明 |
|----------|-------------|
| **Namespace 作用域** | NetworkPolicy 适用于 namespace 内的资源 |
| **可叠加** | 选中目标的 Kubernetes NetworkPolicy 的允许规则会按方向组成并集；Cilium 拒绝规则、Calico tier 和 AWS 管理策略具有独立语义 |
| **选择性应用** | 通过 podSelector 指定目标 Pod |
| **方向控制** | 分别控制 Ingress（入站）和 Egress（出站） |
| **依赖 CNI** | CNI 插件必须支持 NetworkPolicy |

### CNI NetworkPolicy 支持情况

| CNI | 基础 NetworkPolicy | 扩展 | L7 策略 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | 可选 Istio/Dikastes 集成；请验证已部署的产品和版本 |
| **Weave Net（已归档项目）** | 历史支持 | 旧版参考；新部署应评估仍在维护的实现 | ✗ |
| **仅 Flannel** | 自身不实施策略 | 需要单独受支持的策略引擎 | ✗ |
| **Amazon VPC CNI** | 在受支持的 EC2 Linux Node 上启用时 ✓ | 标准 NetworkPolicy；使用 VPC CNI 1.21+ 的 ClusterNetworkPolicy | EKS Auto Mode Node 上的 DNS egress；请参阅 EKS 注意事项 |

---

## Kubernetes NetworkPolicy 规范 {#kubernetes-networkpolicy-spec}

### 基本结构

请显式指定 `policyTypes`。若省略，Kubernetes 默认使用 Ingress，并在至少存在一条 egress 规则时加入 Egress。仅有空规则数组并不意味着同时包含两个方向。

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

选择其所在 namespace 中应用此策略的 Pod。以下是可选的 spec 片段，而非独立的 API 资源。

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

按标签选择 namespace，若当前 namespace 匹配，也包括它。`name` 不是自动分配的 namespace 标签。请使用内置且不可变的 `kubernetes.io/metadata.name` 标签精确匹配 namespace 名称；应限制可更改自定义租户标签的人员。

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

**注意：**同时使用 `namespaceSelector` 和 `podSelector` 时，AND 与 OR 的区别：

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

`ipBlock` 允许该规则中 CIDR 减去其 `except` 范围。例外不是全局拒绝，其他策略可以允许它。Service/load-balancer 地址转换可能改变 CNI 可见的源地址或目的地址；请验证实际路径。以下文档 CIDR 仅用于说明，并非可访问的生产端点。

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

指定允许的端口和协议。`endPort` 需要数值型起始端口和 CNI 对端口范围的支持；命名端口不能作为范围的起始端口。仅 API 接受并不能证明每个插件都会实施。

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

空基线不会贡献任何允许规则；其他选中目标的策略仍可允许流量。策略变更后现有连接的行为取决于实现，必须单独测试。

### 默认拒绝 Ingress

一个自身不含允许规则的 ingress 隔离基线。其他选中目标的策略仍可允许 ingress：

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

一个自身不含允许规则的 egress 隔离基线。其他选中目标的策略仍可允许 egress：

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

### 默认拒绝且允许 DNS

此配置假设 `kube-system` 中存在基于 Pod 的 CoreDNS，并且带有 `k8s-app=kube-dns`。它同时允许 TCP 和 UDP 53。若 DNS 自身存在 ingress 隔离，其策略也必须允许客户端。NodeLocal DNSCache 和 Auto Mode Node 本地 CoreDNS 需要其实际解析器路径/IP 配置；不要原样应用该 Pod selector。

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

包含 frontend→API 的两个方向。它不允许到 frontend 的入站流量，也不允许 API→database；仅添加已审查的流。使用上述基于 Pod 的 DNS 假设。

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

对于每个端点和方向，仅按如下方式评估选中目标的 **Kubernetes NetworkPolicies**。随后检查另一个端点的方向和所有其他网络控制。仅 ingress 的策略不会隔离 egress。

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

### 组合多个策略

当多个 NetworkPolicy 应用于同一个 Pod 时，所有策略规则会合并（并集）：

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

**结果：**API 的 ingress 允许 frontend Pod 使用 8080，并允许 monitoring namespace 的 Pod 使用 8080/9090。其 egress 规则、实际 listener 和其他网络控制也必须允许该连接。

### 策略评估顺序

Kubernetes NetworkPolicy API 没有优先级或显式拒绝规则。它的允许并集并不描述 Calico 策略顺序/tier 操作、Cilium 显式拒绝或 AWS 管理策略的评估：

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

这些示例使用已发布的 Cilium 1.20.1 策略 schema，并非要求升级每个集群。HTTP 规则需要受支持的 L7 proxy 路径。AWS VPC CNI chaining 具有已记录的高级功能限制，包括 L7 策略；不要假定这些 HTTP 示例可在该模式下工作。数值型 Cilium security identity 是标签集合的分配结果，而不是永久的应用 ID。

### CiliumNetworkPolicy

Cilium 为基础 NetworkPolicy 提供了更强大的功能扩展。

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

Cilium HTTP 规则会过滤其 L7 proxy 可见的请求；它们不会认证 API key 或建立 administrator role。调用者可以提供 `X-User-Role` header。该示例过滤 method、path 和精确的 `Content-Type`。请在应用或经过认证的 gateway 中实施认证和授权。端到端 TLS 不会自动解密以进行 HTTP 检查。审查可能在 L4 层允许相同流量的其他策略。

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

[HTTP API — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/http.go)

### L7 Kafka 策略

已发布的 Cilium 1.20.1 CNP schema 支持 HTTP 和 DNS L7 规则，但不包含 `rules.kafka`。以前的 `role`、`topic` 和 `clientID` 配方不是当前可部署的 API。请使用 network policy 限制 broker 连通性，然后通过 Kafka authentication 和 ACL 为 `orders` 与 `events` 实施 producer/consumer 权限。client ID 不是经过认证的主体。

此 L4 示例假设已在 TCP 9093 上配置 TLS broker listener、使用同 namespace 客户端，并单独授权了客户端 egress/DNS。它不配置 TLS、broker ACL 或 topic 权限。

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

[CNP schema — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### L7 DNS 策略

此示例使用基于 Pod 的 CoreDNS。端口 53 上的 `ANY` 覆盖 UDP 和 TCP。DNS 查询权限与连接返回 IP 的权限是分开的：解析以下 database 名称并不允许 database 连接。请替换示例 domain，考虑 DNS search suffix/cache/TTL，并验证实际解析器配置。FQDN 规则从 DNS 学习 IP；它们不会认证 SaaS tenant，也不能替代 TLS/应用授权。

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

该资源为 cluster scope，而其 selector 明确将其限制为 `production/app=api`。它允许 gateway Pod 通过 TCP8080。它仅控制 ingress；egress isolation/DNS 以及 gateway 自身的 egress 需要相应的策略。此前允许全部 endpoint/cluster/world 的示例并不是默认拒绝策略。

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

### 基于 Cilium Entity 的策略

`host` 包含本地 Node 及其 host-network container；`cluster` 不仅包含应用 Pod。`world` 覆盖 cluster 外的 endpoint，并非细粒度的 Internet/SaaS allowlist。缩小外部访问范围时，请使用显式 CIDR/FQDN 规则。该示例仅向带标签的 Kubernetes API client 提供 TCP443 访问；请单独配置其 API endpoint、TLS trust、credentials 和 RBAC。源 identity 可在 managed-control-plane 网络路径中变化，因此应检查实际流 identity，而非将 ingress 扩大到整个 cluster。

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

策略/Tier 示例遵循 Calico Open Source3.32.2 资源。`projectcalico.org/v3` 需要受支持的 Calico API server 或匹配的 `calicoctl` workflow；它不是原始 Kubernetes `crd.projectcalico.org/v1` storage API。应用前请验证已安装的 datastore/API。Calico 有序 action 和 tier delegation 与可叠加的 Kubernetes NetworkPolicy API 不同。

当前 Open Source 文档还介绍了 [Istio/Dikastes application-layer integration](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)。HTTPMatch API 需要该独立设置，并支持 ingress Allow 规则。以下 Calico 示例涵盖 L3/L4 策略；本次审查未部署或测试 L7 integration。

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

这两个全局资源仅选择 `production` namespace 中的 workload。未受约束的 `selector: all()` 也可能影响 host endpoint；不要在没有明确范围和恢复路径的情况下应用 cluster-wide deny。在 tier 内，较低的 `order` 会先被评估。该示例允许基于 Pod 的 DNS，并在其他方面提供拒绝基线；请加入已审查的应用流并考虑更高 tier 的 action。

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

NetworkSet selector 匹配 `metadata.labels`，而不是资源的名称。第一个 set 有 namespace；被阻止的 set 是全局的，并由下面的 security-tier 示例使用。此处所有 CIDR 都是文档范围，必须替换为已审查的目标。egress 示例允许 TCP443 到带标签的有 namespace 的 set；DNS 是独立规则。

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

所引用的 Calico Open Source 版本中包含 Tier，而不仅仅是 Enterprise。若没有规则 action，选中目标的 tier 默认使用 `Deny`。因此 deny-known-threats tier 明确使用 `defaultAction: Pass`，使不相关的流量可以到达后续策略。`Pass` 是委派，不是权限。`global()` 属于 `namespaceSelector`；单独的 label selector 用于标识 GlobalNetworkSet。在部署前填充 application-tier 策略，并验证任何最终 profile/default-tier 行为；创建空 Tier 并非完整的应用隔离策略。

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

这些是**可选策略配置**，而不是要一起应用的组合包。复用 `production` 并不会使无关示例兼容：它们的允许规则会累积。请先准备 namespace、workload 标签、监听端口和真实 DNS 配置。示例已在本地检查 schema/意图，但未在 cluster 上执行。

### 微分段

此配置在两端允许 frontend→API TCP8080 和 API→database TCP5432，并允许 DNS。它特意不包含 Internet egress 或外部 frontend ingress。如有需要，请添加已批准的目标 CIDR/port 或经过认证的 egress gateway 配置；从 0.0.0.0/0 排除 RFC1918 并不是 SaaS allowlist。

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

### Namespace 隔离

团队配置包含同团队 ingress **和 egress**，以及 DNS。共享服务还需要允许 team-a 的目标 ingress 以及真实的 TLS443 listener。限制 namespace 标签管理；团队标签不是独立的信任边界。

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

`database` namespace 必须存在。Production 调用方和 monitoring Pod 需要其自身的 egress allow。TCP5432 peer 规则只允许假设的 PostgreSQL replication transport；请单独配置 database authentication/TLS。TCP9187 假设另行安装了 exporter。

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

假定存在一个现有的 `gateway-system/app=edge-proxy` workload，它终止客户端 TLS 并可通过 TCP80 访问 web Pod。gateway 的 egress 策略不在此 namespace 中。数据 peer ingress 和 egress 使用 TCP5432/6379；其他 replication/cluster-bus/backup port 取决于所选 database，且不会隐式包含。实际部署中应拆分 PostgreSQL 和 Redis selector。

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

### 使用 netshoot 测试

使用已获批准、已预配且镜像已固定、权限已审查的诊断 Pod。选择能够实际触发策略的源标签/namespace/Node 放置位置；通用的无标签 Pod 不代表应用。预配 netshoot 会创建 workload，可能与 Pod Security admission 冲突。不要在观察脚本中创建/删除固定且共享的 `test-pod` 名称。仅针对自己拥有的测试端点运行探测。

### 使用 kubectl exec 测试

请显式设置 context、namespace、现有 Pod 和 container。DNS 成功并不等于 TCP 成功；连接被拒绝、listener 不健康、TLS 错误和策略丢弃是不同结果。这些命令仅测试连通性，不输出 response body。本次审查未在 cluster 上运行它们。

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

`cilium connectivity test` 会创建测试资源和流量；它不是只读状态命令。使用获批准的隔离 cluster/namespace、兼容的 CLI 和 image、明确的外部目标以及清理计划。请查阅 `cilium connectivity test --help` 以了解所安装 CLI 的 filter，而不要假定历史测试名称仍存在。通过的 suite 不能证明每项应用策略或 CNI chaining 功能。

### 自动化测试脚本

此脚本仅在两个现有 Pod 中执行有界 curl 探测；不创建或删除 cluster 资源。设置 `CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER` 和以 `/health` 结尾的非机密 `TARGET_URL`。两个 container 都需要 `sh` 和 `curl`。第一个 Pod 是到同一目标的已知允许正向对照。HTTP error response 仍可确定网络可达性，因为此测试不是应用健康验证。

Exit1 表示被阻止主体意外连接；exit2 表示未知/错误；exit3 表示需要佐证的超时。超时**绝不能**自动视为 PASS：在检查 endpoint health、route 及 SG/NACL control 的同时，将精确的 source/destination/port/time 与 CNI policy-drop verdict 关联。本地 mock test 不声明实时实施结果。

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

启用后，Amazon VPC CNI 支持 network policy。当前 AWS 指南要求标准和 admin policy 均使用 VPC CNI 1.21+、兼容的 EKS platform 以及 Linux kernel 5.10+。实施适用于受支持的 EC2 Linux Node，不适用于 Fargate 或 Windows。请使用当前受支持的 EKS 版本并验证兼容的 add-on release；不要从上游 Kubernetes release 推断 EKS 支持情况。

对于 **EKS-managed** VPC CNI add-on，在设置已记录的字符串 `"enableNetworkPolicy": "true"` 时保留其现有配置。以下命令会在审查后变更所选 cluster；它不会升级 add-on version。若安装的版本不兼容，请停止操作，先遵循已记录的升级过程。

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

在 rollout 前检查 update status 和策略行为。`--resolve-conflicts PRESERVE` 不会为你合并替换 JSON document；示例显式保留现有值。保留 snapshot 以便恢复。由 Helm 管理的安装应使用其经审查的 chart/values 和 `enableNetworkPolicy: true`；不要通过这个 managed-add-on 命令接管它。设置虚构的 `ENABLE_NETWORK_POLICY` environment variable 不是启用过程。

标准 startup mode 最初可能允许新 Pod，直到其策略被编程。`NETWORK_POLICY_ENFORCING_MODE=strict` 会使符合条件的 Pod 在启动时被拒绝，需要完整的 allow matrix（包括 DNS）；更改它可能中断 workload。由 controller 管理的 Pod 是可靠的测试目标。实施发生在主 Pod interface 上，因此应分别检查额外 interface、IPv6-to-IPv4 egress、host networking 和 NAT。不要安装两个 engine 来管理相同的标准策略，也不要将删除 `aws-node` 作为迁移捷径。

### EKS 增强网络安全策略（December 2025）

> **发布**：December 15, 2025 · [来源](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

该功能确实存在，但其资源使用 **`networking.k8s.aws/v1alpha1`**。`ClusterNetworkPolicy` 为 cluster scoped 且必需包含 `tier`；基于 DNS 的 egress 在以下 namespace 示例中使用 `ApplicationNetworkPolicy`。EC2 Linux 上的标准/admin VPC CNI 策略支持并不表示每种 compute mode 都支持。DNS 规则仅在 **Auto Mode 启动的 EC2 instance** 上实施，包括混合 cluster 中的 instance。

此 Admin-tier 示例拒绝从按 namespace 选择的 Pod 到 `isolated-demo` 的入站流量，包括该 namespace 中的 Pod。它不是完整的 external/host-network firewall 或 DNS allow 策略。Admin Deny 不能被 namespace NetworkPolicy 覆盖。在添加其他 action 前审查实际安装的 CRD：当前上游 AWS controller schema 将允许 action 命名为 `Accept`，而 user-guide prose 使用 “Allow”。

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

FQDN 示例在 `production` 中选择 `app=backend`。**将 `10.100.0.10/32` 替换为 cluster 实际的 Auto Mode CoreDNS IP**：它是 Service CIDR 网络地址加 10（IPv6 为 `::a/128`）。纯 Auto Mode CoreDNS 在 Node 上运行；常规 CoreDNS Pod selector 不可互换。允许 TCP 和 UDP DNS。使用不会与该 namespace 中 NetworkPolicy 冲突的唯一资源名称。

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

DNS proxy 观察被允许的 answer 及其 TTL，然后 data path 允许已学习的 destination IP/port。这不会认证 SaaS account，也不能证明 peer 的 HTTP identity；共享 IP 和 DNS 行为需要测试。TLS certificate verification、application authorization、route 及任何 Route 53 DNS Firewall rule 仍然相关。必须一并审查其他适用的策略和直接 backend path。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode 策略](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Pod 的安全组

此 binding 示例假设具备 EKS VPC Resource Controller、其 **cluster-role** permission、受支持的 trunking-compatible EC2 Linux Node 和已审查的 VPC CNI configuration。当前 AWS guide 排除 Windows 和 EKS Auto Mode。Fargate 使用独立的 Pod-SG model，并不会仅因拥有 security group 就获得 VPC-CNI NetworkPolicy 支持。通过其 owner 将 binding 应用于新的匹配 workload Pod；现有 Pod 不会自动改造。

对于 Calico 加 Pod SG，AWS 记录了 VPC CNI1.11.0+ 和 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`；还应使用当前 CNI requirement，而不要把该最低值当作推荐版本。standard-mode external SNAT 可使用 Node SG 而非 Pod SG。请验证精确路径。旧的裸 PostgreSQL Pod 缺少 credentials/storage，并非可用的 database deployment。

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

该 Terraform fragment 允许来自一个已审查 app SG 的 DB ingress，且不发起新的 egress connection。stateful return traffic 由 SG tracking 允许；仅单独添加所需的 DNS、replication、backup 或 external egress。变量是现有 operator input；未执行 Terraform plan/apply。

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

### 将 VPC 级控制与 NetworkPolicy 结合

NetworkPolicy、实际应用的 SG 和 NACL 都必须允许相关路径。此仅 ingress 的 NetworkPolicy 不限制 database egress；请添加选定的 egress 配置和 source-Pod egress。多个 SG 合并其 allow。NACL 是**无状态的**，因此允许 inbound5432 的 subnet rule 需要到 client ephemeral port 的匹配 return path，以及 client subnet 上适当的 rule。以下 fragment 不能替代完整且经过审查的 ACL rule set。

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

选择 **AWS VPC CNI chaining** 或另行设计完整 CNI/IPAM migration。在 chaining mode 中，AWS VPC CNI 保留 ENI/IPAM responsibility，Cilium 附加其 datapath。保留 `aws-node`；删除它不是安装捷径。审查现有 add-on/Helm owner，并避免重叠的 policy-enforcement engine。现有 Pod 需要受控重建后 chaining policy 才会应用；请规划中断和 rollback。

官方1.20.1 chaining guide 提供了这些 value，但也记录了 L7/IPsec limitation。它包含旧的示例 output；那些并非当前 EKS environment 的验证。准备 chart repository/package、验证 provenance 并先 render：

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI chaining — Cilium 1.20.1](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## 可视化工具 {#visualization-tools}

### Cilium Network Policy Editor

策略 editor 有助于编写 policy；**Hubble UI 可视化观察到的 service flow**。二者是不同工具。启用 Hubble/UI 会变更 cluster configuration，应由 installation owner 完成。对于已安装且已认证的 Hubble service，请检查现有 service 并使用本地 port-forward。不要将 UI 公开暴露作为调试捷径。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium 策略 Verdict 检查

使用已认证的 Hubble connection。`DROPPED` 包含策略以外的原因；请检查 drop reason、endpoint identity、time 和 direction。在一个位置观察到的 `FORWARDED` 并非端到端交付保证。


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

Enterprise management UI 需要已获许可的产品及其实际 service/TLS/authentication configuration；Calico Open Source 不会自动安装它。转发前请检查已安装的 service name/port 和 access policy。不要假定每个安装都存在 `cnx-manager`。

### 网络策略可视化工具

使用 `kubectl get networkpolicy -n <namespace>` 和 `kubectl describe networkpolicy <name> -n <namespace>` 检查 Kubernetes policy selector/rule，并使用已安装 engine 的认证 flow tool 检查实施。必须根据第三方 viewer/plugin 当前 release 检查其可用性和 flag。仅 YAML graph 不能证明 dataplane enforcement。

### 使用 Kube-hunter 进行安全测试

kube-hunter 是 cluster exposure/security scanner，不是 NetworkPolicy allow/deny verifier。其 scan 可能生成侵入性流量；请使用明确批准的 target/scope 和已审查的 release/image。不要从通用策略教程向 live namespace 部署未固定版本的 scanner。本次审查未执行 scanner。

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

### 4. 定期策略审计

此只读 inventory 会分别列出 namespace 范围的 ingress 和 egress 空 allow baseline。它处理空 `[]` 和缺失规则数组，而规则 `{}` 会允许流量，因此不是 deny baseline。API/authorization error 会失败，而不会显示为零策略。列出的 baseline **不是隔离证明**：其他 allow rule、extension policy、未覆盖 Pod 和 CNI 状态仍需审查。

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

## 摘要

Kubernetes Network Policies 是控制 cluster 内 Pod 通信的核心安全机制：

1. **基础 NetworkPolicy**：namespace 作用域，支持 podSelector/namespaceSelector/ipBlock
2. **Cilium 扩展**：L7 策略、基于 DNS FQDN 的策略、cluster-wide 策略
3. **Calico 扩展**：GlobalNetworkPolicy、NetworkSet、基于 Tier 的策略
4. **EKS 注意事项**：VPC CNI NetworkPolicy 激活、Pod 的 Security Groups、ClusterNetworkPolicy 和基于 DNS（FQDN）的 egress control

### 建议

- 对所有 production namespace 应用默认拒绝策略
- 按最小权限原则仅允许必需流量
- 定期进行策略审计和测试
- 需要 L7 策略时考虑 Cilium

---

## 参考资料

- [Kubernetes Network Policies 官方文档](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy 文档](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy 文档](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS Security 最佳实践 - 网络安全](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS 增强网络安全策略（2025-12-15）](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod security groups](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
