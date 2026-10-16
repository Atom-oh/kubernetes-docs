# 网络策略

> **审查基线**：Kubernetes 1.35 OpenAPI、Cilium 1.20.1、Calico 3.32.2 以及当前 AWS 文档。离线检查无法确认集群兼容性。
> **最后更新**：October 15, 2026

Kubernetes Network Policy 是控制 Pod 之间流量的防火墙规则。本文档涵盖基础 NetworkPolicy 以及 Cilium/Calico 扩展。各章节均为独立示例；合并所有策略会改变实际生效的权限。未执行任何集群/云部署或实时连通性测试。

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

Kubernetes NetworkPolicy 会选择其自身 namespace 中的 Pod，并控制受支持的入站和出站流量。如果某个方向上没有选择该 Pod 的策略，则该方向上的 Pod 不会被 NetworkPolicy 隔离；路由、安全组、NACL 及其他策略引擎仍然可以阻止连通性。

Pod 到 Pod 的连接必须**两端都允许**：源端的有效 egress 规则和目标端的有效 ingress 规则都必须允许该连接。已允许连接的返回流量会被隐式允许。策略由支持它的网络插件异步实现；仅有 API 对象并不证明已实施强制执行。节点/hostNetwork 流量以及 TCP/UDP/SCTP 之外的协议需要进行特定于实现的审查。下面的图表展示的是策略意图，并非可达性保证。

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
| **Namespace 范围** | NetworkPolicy 适用于 namespace 内的资源 |
| **累加性** | 选择该对象的 Kubernetes NetworkPolicy 的允许规则会在每个方向上形成并集；Cilium 拒绝、Calico 层级和 AWS 管理策略具有独立的语义 |
| **选择性应用** | 通过 podSelector 指定目标 Pod |
| **方向控制** | 分别控制 Ingress（入站）和 Egress（出站） |
| **依赖 CNI** | CNI 插件必须支持 NetworkPolicy |

### CNI NetworkPolicy 支持

| CNI | 基础 NetworkPolicy | 扩展 | L7 策略 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | 可选的 Istio/Dikastes 集成；请验证已部署的产品和版本 |
| **Weave Net（已归档项目）** | 历史支持 | 旧版参考；对于新部署，请评估受维护的实现 | ✗ |
| **仅 Flannel** | 自身不实施策略 | 需要单独的受支持策略引擎 | ✗ |
| **Amazon VPC CNI** | 在受支持的 EC2 Linux 节点上启用时 ✓ | 标准 NetworkPolicy；使用 VPC CNI 1.21+ 的 ClusterNetworkPolicy | EKS Auto Mode 节点上的 DNS egress；请参阅 EKS 注意事项 |

---

## Kubernetes NetworkPolicy 规范 {#kubernetes-networkpolicy-spec}

### 基本结构

请显式指定 `policyTypes`。如果省略，Kubernetes 默认使用 Ingress，并且当至少存在一条 egress 规则时添加 Egress。仅有空规则数组并不意味着两个方向都适用。

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

选择策略在其自身 namespace 中适用的 Pod。以下是可替代的规范片段，不是独立的 API 资源。

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

按标签选择 namespace，如果当前 namespace 匹配，也会包含在内。`name` 不是自动分配的 namespace 标签。若要精确匹配 namespace 名称，请使用内置且不可变的 `kubernetes.io/metadata.name` 标签；应限制可更改自定义租户标签的人员。

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

`ipBlock` 会允许该规则中 CIDR 减去其 `except` 范围后的地址。例外并非全局拒绝，其他策略仍可允许它。Service/load-balancer 地址转换可能改变 CNI 可见的源地址或目标地址；请验证实际路径。下面的文档 CIDR 仅作说明，不是可达的生产端点。

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

指定允许的端口和协议。`endPort` 需要数值型起始端口和 CNI 的范围支持；命名端口不能作为范围的起始端口。仅被 API 接受并不证明每个插件都会实施强制执行。

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

空基线不提供任何允许；其他选择该对象的策略仍可以允许流量。策略变更后现有连接的行为取决于实现，必须单独测试。

### 默认拒绝 Ingress

自身不提供任何允许的 ingress 隔离基线。其他选择该对象的策略仍可允许 ingress：

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

自身不提供任何允许的 egress 隔离基线。其他选择该对象的策略仍可允许 egress：

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

### 允许 DNS 的默认拒绝

此配置假定 `kube-system` 中存在基于 Pod 的 CoreDNS，并带有 `k8s-app=kube-dns`。它允许 TCP 和 UDP 53。如果 DNS 本身具有 ingress 隔离，其策略也必须允许客户端。NodeLocal DNSCache 和 Auto Mode 节点本地 CoreDNS 需要其实际的解析器路径/IP 配置；请勿在这些环境中不加修改地应用此 Pod selector。

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

frontend→API 的两个方向均已包含。这不会允许到 frontend 的入站流量或 API→database；仅添加经审查的流。请使用上述基于 Pod 的 DNS 假设。

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

对于每个端点和方向，仅按如下方式评估选择该对象的 **Kubernetes NetworkPolicies**。随后检查另一个端点的方向以及所有其他网络控制。仅 ingress 的策略不会隔离 egress。

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

当多个 NetworkPolicy 应用于同一 Pod 时，所有策略规则会合并（并集）：

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

**结果：**API 的 ingress 允许 frontend Pod 访问 8080，也允许 monitoring namespace 的 Pod 访问 8080/9090。其 egress 规则、实际监听器和其他网络控制也必须允许该连接。

### 策略评估顺序

Kubernetes NetworkPolicy API 没有优先级或显式拒绝规则。其允许并集并不描述 Calico 策略顺序/Tier 操作、Cilium 显式拒绝或 AWS 管理策略评估：

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

这些示例使用已发布的 Cilium 1.20.1 策略 schema，并非要求升级每个集群。HTTP 规则需要受支持的 L7 proxy 路径。AWS VPC CNI chaining 存在已记录的高级功能限制，包括 L7 策略；不要假定这些 HTTP 示例在该模式中可用。数值型 Cilium security identity 是标签集的分配结果，而非永久的应用 ID。

### CiliumNetworkPolicy

Cilium 通过更强大的功能扩展基础 NetworkPolicy。

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

Cilium HTTP 规则会过滤其 L7 proxy 可见的请求；它们不会对 API key 进行身份验证，也不会建立管理员角色。调用方可以提供 `X-User-Role` header。此示例过滤方法、路径和精确的 `Content-Type`。请在应用程序或经身份验证的 gateway 中实施认证和授权。不会自动解密端到端 TLS 以进行 HTTP 检查。审查可能在 L4 层允许相同流量的其他策略。

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

已发布的 Cilium 1.20.1 CNP schema 支持 HTTP 和 DNS L7 规则，但没有 `rules.kafka`。以前的 `role`、`topic` 和 `clientID` 配方不是当前可部署的 API。使用网络策略限制 broker 连通性，然后使用 Kafka authentication 和 ACL 为 `orders` 和 `events` 实施 producer/consumer 权限。client ID 不是已认证的主体。

此 L4 示例假定 TCP 9093 上已有配置 TLS broker listener、客户端位于同一 namespace，并且 client egress/DNS 已单独获得授权。它不配置 TLS、broker ACL 或 topic 权限。

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

此示例使用基于 Pod 的 CoreDNS。端口 53 上的 `ANY` 同时涵盖 UDP 和 TCP。DNS 查询权限与连接返回 IP 的权限是分开的：解析下面的 database 名称不会允许 database 连接。请替换示例域名，考虑 DNS search suffix、cache/TTL，并验证实际解析器配置。FQDN 规则会从 DNS 学习 IP；它们不会认证 SaaS tenant，也不会替代 TLS/应用授权。

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

该资源具有 cluster 范围，而其 selector 明确将其限定为 `production/app=api`。它允许 gateway Pod 通过 TCP8080 访问。它仅控制 ingress；egress 隔离/DNS 以及 gateway 自身的 egress 需要相应策略。之前针对所有 endpoint/cluster/world 的允许示例不是默认拒绝策略。

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

`host` 包含本地节点及其 host-network 容器；`cluster` 包含的内容多于应用 Pod。`world` 涵盖集群外的 endpoint，并非细粒度的 Internet/SaaS allowlist。缩小外部访问范围时，请使用显式 CIDR/FQDN 规则。此示例仅为带标签的 Kubernetes API client 提供 TCP443 访问；请单独配置其 API endpoint、TLS trust、credentials 和 RBAC。托管 control-plane 网络路径中的源 identity 可能发生变化，因此应检查实际流 identity，而不是将 ingress 扩大至整个 cluster。

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

策略/Tier 示例遵循 Calico Open Source3.32.2 资源。`projectcalico.org/v3` 需要受支持的 Calico API server 或匹配的 `calicoctl` 工作流；它不是原始 Kubernetes `crd.projectcalico.org/v1` storage API。应用前请验证已安装的 datastore/API。有序的 Calico action 和 Tier delegation 不同于累加式 Kubernetes NetworkPolicy API。

当前 Open Source 文档还描述了 [Istio/Dikastes 应用层集成](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)。HTTPMatch API 需要该单独设置，并支持 ingress Allow 规则。以下 Calico 示例涵盖 L3/L4 策略；本审查未部署或测试 L7 集成。

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

这两个全局资源仅选择 `production` namespace 中的 workload。不受约束的 `selector: all()` 还可能影响 host endpoint；请勿在没有明确范围和恢复路径的情况下应用 cluster-wide deny。较低的 `order` 会在 Tier 内优先评估。该示例允许基于 Pod 的 DNS，否则提供拒绝基线；请添加经过审查的应用流，并考虑更高层级的操作。

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

NetworkSet selector 匹配 `metadata.labels`，而非资源名称。第一个集合具有 namespace 范围；被阻止的集合是全局的，并由下面的 security-tier 示例使用。此处所有 CIDR 均为文档范围，必须替换为经过审查的目标。egress 示例允许到带标签 namespace 集合的 TCP443；DNS 是单独的规则。

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

Tier 在所引用的 Calico Open Source 版本中可用，并非仅限 Enterprise。当没有规则生效时，选择该对象的 Tier 默认 `Deny`。因此 deny-known-threats Tier 显式使用 `defaultAction: Pass`，使不相关流量能进入后续策略。`Pass` 是委托，不是许可。`global()` 属于 `namespaceSelector`；单独的 label selector 用于标识 GlobalNetworkSet。部署前请填充 application-tier 策略并验证任何最终 profile/default-tier 行为；创建空 Tier 并非完整的应用隔离策略。

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

这些是**可替代的策略配置**，并非要一起应用的捆绑包。重复使用 `production` 并不会使不相关的示例兼容：它们的允许规则会累积。请先准备 namespace、workload 标签、监听端口和实际 DNS 配置。这些示例已在本地检查 schema/意图，但未在 cluster 上执行。

### 微分段

此配置在两端允许 frontend→API TCP8080 和 API→database TCP5432，并允许 DNS。它有意不包含 Internet egress 或外部 frontend ingress。如有需要，请添加经批准的目标 CIDR/端口或经身份验证的 egress gateway 配置；从 0.0.0.0/0 中排除 RFC1918 并不是 SaaS allowlist。

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

团队配置包括同团队的 ingress **和 egress**，以及 DNS。共享服务还需要允许 team-a 的目标 ingress 以及真实的 TLS443 listener。应限制 namespace 标签管理；team 标签不是独立信任边界。

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

`database` namespace 必须存在。生产调用方和 monitoring Pod 需要各自的 egress 允许规则。TCP5432 peer 规则仅允许假定的 PostgreSQL replication transport；请单独配置 database authentication/TLS。TCP9187 假定已单独安装 exporter。

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

假定存在一个现有的 `gateway-system/app=edge-proxy` workload，它终止 client TLS，并可通过 TCP80 访问 web Pod。gateway 的 egress 策略不在此 namespace 中。数据 peer ingress 和 egress 使用 TCP5432/6379；额外的 replication/cluster-bus/backup 端口取决于所选 database，并不由此隐含。请在真实部署中拆分 PostgreSQL 和 Redis selector。

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

请使用已获批准、已预配且使用固定镜像并具有经过审查权限的诊断 Pod。选择能实际触发策略的源标签/namespace/node placement；通用的无标签 Pod 并不代表应用程序。预配 netshoot 会创建 workload，且可能与 Pod Security admission 冲突。不要在观测脚本中创建/删除固定的共享 `test-pod` 名称。仅对自有的测试 endpoint 运行探测。

### 使用 kubectl exec 测试

显式设置 context、namespace、现有 Pod 和 container。DNS 成功不等于 TCP 成功；连接拒绝、不健康的 listener、TLS 错误和策略丢弃是不同结果。这些命令仅测试连通性，不会打印响应正文。本审查期间未针对 cluster 运行它们。

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

`cilium connectivity test` 会创建测试资源和流量；它不是只读状态命令。请使用经批准的隔离 cluster/namespace、兼容的 CLI 和镜像、定义好的外部目标以及清理计划。请查阅 `cilium connectivity test --help` 以获取已安装 CLI 的过滤器，而不要假定历史测试名称仍然存在。通过的测试套件并不能证明每项应用策略或 CNI chaining 功能。

### 自动化测试脚本

此脚本仅在两个现有 Pod 中执行有界 curl 探测；不会创建或删除 cluster 资源。设置 `CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER` 以及以 `/health` 结尾的非机密 `TARGET_URL`。两个 container 都需要 `sh` 和 `curl`。第一个 Pod 是到相同目标的已知允许正向对照。HTTP 错误响应仍可确定网络可达性，因为此测试不是应用健康验证。

Exit1 表示被阻止的主体意外连接；exit2 表示未知/错误；exit3 表示需要佐证的超时。超时**绝不**会自动变为 PASS：应将精确的源/目标/端口/时间与 CNI 策略丢弃判定关联，同时检查 endpoint 健康状态、路由和 SG/NACL 控制。本地 mock 测试并不声称已实施实时强制执行。

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

Amazon VPC CNI 在启用后支持网络策略。当前 AWS 指南要求标准和管理策略均使用 VPC CNI 1.21+、兼容的 EKS platform 和 Linux kernel 5.10+。强制执行适用于受支持的 EC2 Linux 节点，不适用于 Fargate 或 Windows。请使用当前受支持的 EKS 版本，并验证兼容的 add-on release；不要从上游 Kubernetes release 推断 EKS 支持情况。

对于 **EKS-managed** VPC CNI add-on，在设置文档化的字符串 `"enableNetworkPolicy": "true"` 时保留其现有配置。以下操作会在审查后更改选定 cluster；它不会升级 add-on 版本。如果已安装的版本不兼容，请停止并先遵循文档化的升级流程。

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

在 rollout 前检查更新状态和策略行为。`--resolve-conflicts PRESERVE` 不会为你合并替换 JSON 文档；该示例明确保留了现有值。保留 snapshot 以便恢复。Helm-owned 安装应使用其经过审查的 chart/values 和 `enableNetworkPolicy: true`；不要通过此 managed-add-on 命令接管其所有权。设置虚构的 `ENABLE_NETWORK_POLICY` 环境变量并非启用流程。

标准启动模式最初可能允许新 Pod，直到其策略被编程。`NETWORK_POLICY_ENFORCING_MODE=strict` 会使符合条件的 Pod 在启动时处于拒绝状态，并需要完整的允许矩阵（包括 DNS）；更改它可能中断 workload。controller-managed Pod 是可靠的测试目标。强制执行位于主要 Pod interface 上，因此请单独检查额外 interface、IPv6-to-IPv4 egress、host networking 和 NAT。不要安装两个引擎来管理相同的标准策略，也不要将删除 `aws-node` 作为迁移捷径。

### EKS 增强网络安全策略（2025 年 12 月）

> **已发布**：December 15, 2025 · [来源](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

该功能确实存在，但其资源使用 **`networking.k8s.aws/v1alpha1`**。`ClusterNetworkPolicy` 具有 cluster 范围，且必须提供 `tier`；基于 DNS 的 egress 对下面的 namespace 示例使用 `ApplicationNetworkPolicy`。EC2 Linux 上的标准/管理 VPC CNI 策略支持并不表示每种 compute mode 都受支持。DNS 规则仅在 **Auto Mode 启动的 EC2 instance** 上强制执行，包括混合 cluster 中的实例。

**Auto Mode 前提条件：**在应用以下策略前，启用其 Network Policy Controller。更新 EKS-managed `vpc-cni` add-on 是另一条路径，不会为纯 Auto Mode cluster 启用策略强制执行。所需设置为 ConfigMap `kube-system/amazon-vpc-cni` 的 `data.enable-network-policy-controller: "true"`。以下工作流使用 merge patch 保留其他 ConfigMap data，仅在不存在时创建，并在读取或写入失败时停止。运行前请审查 cluster context 和现有配置。

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

启用后，请检查相应的 `PolicyEndpoints` 对象，并在所选 Auto Mode 节点上测试允许和拒绝的流量。已存储的 flag 或已接受的策略对象并不证明已实施强制执行。请参阅 [Auto Mode 网络策略设置](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)。本次文档审计未执行 cluster 强制执行测试。

此 Admin-tier 示例拒绝 namespace-selected Pod 到 `isolated-demo` 的传入流量，包括同一 namespace 中的 Pod。它不是完整的 external/host-network firewall 或 DNS allow 策略。Admin Deny 不能被 namespace NetworkPolicy 覆盖。在添加其他 action 前审查实际安装的 CRD：当前上游 AWS controller schema 将其允许 action 命名为 `Accept`，而 user-guide prose 使用“Allow”。

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

FQDN 示例会选择 `production` 中的 `app=backend`。**请将 `10.100.0.10/32` 替换为 cluster 实际的 Auto Mode CoreDNS IP**：它是 Service CIDR network address 加 10（IPv6 为 `::a/128`）。纯 Auto Mode CoreDNS 在 node 上运行；传统 CoreDNS Pod selector 不可互换。允许 TCP 和 UDP DNS。使用不会与该 namespace 中 NetworkPolicy 冲突的唯一资源名称。

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

DNS proxy 观察获准的答案及其 TTL，然后数据路径允许学习到的目标 IP/端口。这并不认证 SaaS account，也不能证明对端的 HTTP identity；共享 IP 和 DNS 行为需要测试。TLS certificate verification、application authorization、routes 以及任何 Route 53 DNS Firewall 规则仍然相关。必须一并审查其他适用策略和直连 backend 路径。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode 策略](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Pod 的安全组

此绑定示例假定使用 EKS VPC Resource Controller、其 **cluster-role** 权限、受支持的 trunking-compatible EC2 Linux 节点以及经过审查的 VPC CNI 配置。当前 AWS 指南排除 Windows 和 EKS Auto Mode。Fargate 使用单独的 Pod-SG 模型，并不会仅因具有 security group 而获得 VPC-CNI NetworkPolicy 支持。通过其 owner 将绑定应用于新的匹配 workload Pod；现有 Pod 不会自动被改造。

对于 Calico 加 Pod SG，AWS 文档要求 VPC CNI1.11.0+ 且 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`；还应使用当前 CNI 要求，而不要将该最低版本当作建议版本。标准模式的 external SNAT 可以使用 node SG 而不是 Pod SG。请验证确切路径。旧的裸 PostgreSQL Pod 缺少 credentials/storage，并非可用的 database deployment。

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

Terraform 片段允许来自一个经审查 app SG 的 DB ingress，且不会发起新的 egress 连接。stateful return traffic 由 SG tracking 允许；仅单独添加必需的 DNS、replication、backup 或 external egress。变量是现有 operator 输入；未执行 Terraform plan/apply。

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

### 将 VPC 层控制与 NetworkPolicy 结合

NetworkPolicy、实际应用的 SG 和 NACL 都必须允许相关路径。此仅 ingress 的 NetworkPolicy 不限制 database egress；请添加选定的 egress 配置和源 Pod egress。多个 SG 会合并其允许。NACL 是**无状态的**，因此允许 inbound5432 的 subnet 规则需要有到 client ephemeral ports 的匹配返回路径，以及 client subnet 上适当的规则。以下片段不能替代完整且经过审查的 ACL rule set。

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

选择 **AWS VPC CNI chaining** 或单独设计的完整 CNI/IPAM migration。在 chaining mode 中，AWS VPC CNI 保留 ENI/IPAM 职责，Cilium 附加其 datapath。保留 `aws-node`；删除它不是安装捷径。审查现有 add-on/Helm owner，并避免重叠的 policy-enforcement engine。现有 Pod 需要受控重建后才能应用 chaining policy；请规划中断和 rollback。

官方1.20.1 chaining 指南提供这些值，但也记录了 L7/IPsec 限制。它包含旧的示例输出；这些并不是对当前 EKS 环境的验证。准备 chart repository/package，验证 provenance，并先进行 render：

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

策略编辑器有助于编写策略；**Hubble UI 会可视化观察到的 service flow**。二者是不同工具。启用 Hubble/UI 会更改 cluster 配置，应由安装 owner 负责。对于已安装且已认证的 Hubble service，请检查现有 service 并使用本地 port-forward。不要将 UI 公开暴露作为调试捷径。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium 策略判定检查

使用经过身份验证的 Hubble 连接。`DROPPED` 包含策略以外的原因；请检查 drop reason、endpoint identity、时间和方向。某一时刻的 `FORWARDED` 观测并非端到端交付保证。


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

Enterprise management UI 需要获得许可的产品及其实际的 service/TLS/authentication 配置；它不会随 Calico Open Source 自动安装。转发前请检查已安装的 service 名称/端口和访问策略。不要假定每个安装中都存在 `cnx-manager`。

### 网络策略可视化工具

使用 `kubectl get networkpolicy -n <namespace>` 和 `kubectl describe networkpolicy <name> -n <namespace>` 检查 Kubernetes policy selector/rule，并使用已安装引擎经过身份验证的 flow tool 检查强制执行。第三方 viewer/plugin 的可用性和 flags 必须根据该项目当前 release 进行检查。仅有 YAML 图表无法证明 dataplane 强制执行。

### 使用 Kube-hunter 进行安全测试

kube-hunter 是 cluster exposure/security scanner，而非 NetworkPolicy allow/deny verifier。其 scan 可能产生侵入性流量；请使用明确批准的 target/scope 和经过审查的 release/image。不要从通用策略教程中将未固定版本的 scanner 部署到 live namespace。本审查未执行 scanner。

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

仅显式允许所需流量：

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

此只读清单会分别列出 namespace 范围内的 ingress 和 egress 空允许基线。会处理空 `[]` 和不存在的规则数组，而规则 `{}` 允许流量，因而不是拒绝基线。API/authorization 错误会失败，而不会显示为零策略。列出的基线**不证明隔离**：仍需审查其他允许规则、扩展策略、未覆盖的 Pod 和 CNI 状态。

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

## 将 NetworkPolicy 连接至外围检查

NetworkPolicy 通过受支持的 CNI 实施 Pod 连接；它不会创建每一条 WAF 或 central-firewall 路径。不要假定 same-node、VPC-local、PrivateLink、peering 或 IPv6 流量会自动经过中央 TGW 检查。

将公共应用连接至 [WAF/origin protection](./14-waf-edge-api-security.md)，并将 outbound/inter-VPC 流量连接至 [Palo Alto/Fortinet](./15-ngfw-paloalto-fortinet.md) 和 [GWLB/GENEVE](./16-gwlb-geneve-inspection.md)。验证 Pod/node SNAT 和 request/response tuple，并分别测试策略结果与 appliance traversal。有关 webhook 和 Secret-permission 调查，请参阅[深度防御与事件响应](./13-defense-in-depth-incident-response.md)。

## 总结

Kubernetes Network Policy 是控制 cluster 内 Pod 通信的核心安全机制：

1. **基础 NetworkPolicy**：具有 Namespace 范围，支持 podSelector/namespaceSelector/ipBlock
2. **Cilium 扩展**：L7 策略、基于 DNS FQDN 的策略、cluster-wide 策略
3. **Calico 扩展**：GlobalNetworkPolicy、NetworkSet、基于 Tier 的策略
4. **EKS 注意事项**：VPC CNI NetworkPolicy 激活、Pod 的安全组、ClusterNetworkPolicy 和基于 DNS（FQDN）的 egress 控制

### 建议

- 对所有生产 namespace 应用默认拒绝策略
- 遵循最小权限原则，仅允许所需流量
- 定期进行策略审计和测试
- 需要 L7 策略时考虑 Cilium

---

## 参考资料

- [Kubernetes 网络策略官方文档](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium 网络策略文档](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico 网络策略文档](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS 安全最佳实践 - 网络安全](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS 增强网络安全策略（2025-12-15）](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod 安全组](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)