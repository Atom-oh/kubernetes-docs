# 网络策略

> **审查基线**：Kubernetes 1.35 OpenAPI、Cilium 1.20.1、Calico 3.32.2 以及当前 AWS 文档。离线检查不能确定集群兼容性。
> **最后更新**：September 13, 2026

Kubernetes NetworkPolicy 是控制 Pod 之间流量的防火墙规则。本文介绍基础 NetworkPolicy 及 Cilium/Calico 扩展。各节是独立示例；合并每项策略会改变实际生效的权限。未执行集群/云部署或实时连通性测试。

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

Kubernetes NetworkPolicy 在其自身 namespace 中选择 Pod，并控制受支持的入站和出站流量。某方向上没有选择该 Pod 的策略时，该方向上的 Pod 不会被 NetworkPolicy 隔离；路由、安全组、NACL 和其他策略引擎仍可阻止连通性。

Pod 到 Pod 的连接**两端都必须允许**：源端的有效出站规则和目标端的有效入站规则都必须允许该连接。允许连接的返回流量会被隐式允许。策略由支持它的网络插件异步实施；仅有 API 对象并不能证明已实施。节点/hostNetwork 流量以及 TCP/UDP/SCTP 之外的协议需要针对具体实现进行审查。下图展示的是策略意图，并非可达性保证。

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

### 网络策略特征

| 属性 | 说明 |
|----------|-------------|
| **Namespace 范围** | NetworkPolicy 适用于某个 namespace 内的资源 |
| **可累加** | 选择 Kubernetes NetworkPolicy 的允许规则会在每个方向上形成并集；Cilium 拒绝、Calico tier 和 AWS 管理策略具有不同语义 |
| **选择性应用** | 通过 podSelector 指定目标 Pod |
| **方向控制** | 分别控制 Ingress（入站）和 Egress（出站） |
| **依赖 CNI** | CNI 插件必须支持 NetworkPolicy |

### CNI NetworkPolicy 支持

| CNI | 基础 NetworkPolicy | 扩展 | L7 策略 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy、CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy、NetworkSet、Tier | 可选的 Istio/Dikastes 集成；请验证已部署的产品和版本 |
| **Weave Net（已归档项目）** | 曾提供支持 | 遗留参考；新部署应评估受维护的实现 | ✗ |
| **仅 Flannel** | 本身不实施策略 | 需要单独的受支持策略引擎 | ✗ |
| **Amazon VPC CNI** | 在受支持 EC2 Linux 节点上启用时 ✓ | 标准 NetworkPolicy；VPC CNI 1.21+ 支持 ClusterNetworkPolicy | EKS Auto Mode 节点上的 DNS egress；请参阅 EKS 注意事项 |

---

## Kubernetes NetworkPolicy 规范 {#kubernetes-networkpolicy-spec}

### 基本结构

请显式指定 `policyTypes`。如果省略，Kubernetes 默认为 Ingress，并在至少存在一项 egress 规则时添加 Egress。仅有空规则数组并不表示两个方向都适用。

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

选择其自身 namespace 中应用策略的 Pod。以下是可选的 spec 片段，而非独立 API 资源。

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

通过标签选择 namespace；如果当前 namespace 匹配，也会包含在内。`name` 不是自动分配的 namespace 标签。对于精确的 namespace 名称，请使用内置且不可变的 `kubernetes.io/metadata.name` 标签；应限制能够修改自定义租户标签的人员。

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

`ipBlock` 在该规则中允许一个 CIDR，但排除其 `except` 范围。例外不是全局拒绝，其他策略仍可允许它。Service/load-balancer 地址转换可能改变 CNI 可见的源地址或目标地址；请验证实际路径。下面的文档 CIDR 仅用于说明，并非可达的生产端点。

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

指定允许的端口和协议。`endPort` 需要数值型起始端口和 CNI 的范围支持；命名端口不能作为范围的起点。仅 API 接受并不能证明每个插件都会实施。

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

空基线本身不会贡献允许规则；其他选择该 Pod 的策略仍可允许流量。策略变更后现有连接的行为取决于实现，必须单独测试。

### 默认拒绝入站

一个自身没有允许规则的入站隔离基线。其他选择该 Pod 的策略仍可允许入站：

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

### 默认拒绝出站

一个自身没有允许规则的出站隔离基线。其他选择该 Pod 的策略仍可允许出站：

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

此配置假定 `kube-system` 中使用了基于 Pod 的 CoreDNS，且标签为 `k8s-app=kube-dns`。它允许 TCP 和 UDP 53。如果 DNS 本身具有入站隔离，其策略也必须允许客户端。NodeLocal DNSCache 和 Auto Mode 节点本地 CoreDNS 需要其实际的解析器路径/IP 配置；不要在这些环境中不作修改地应用此 Pod selector。

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

包含 frontend→API 的两个方向。这不会允许到 frontend 的入站流量或 API→database；只添加经过审查的流量。请采用以上基于 Pod 的 DNS 假定。

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

对于每个端点和方向，仅按如下方式评估选择它的 **Kubernetes NetworkPolicy**。然后检查另一端点的相应方向以及所有其他网络控制。仅入站策略不会隔离出站。

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

**结果：**API 的入站允许 frontend Pod 访问 8080，并允许 monitoring namespace 中的 Pod 访问 8080/9090。其出站规则、实际 listener 及其他网络控制也必须允许该连接。

### 策略评估顺序

Kubernetes NetworkPolicy API 没有优先级或显式拒绝规则。其允许规则的并集并不能描述 Calico 策略顺序/tier 操作、Cilium 显式拒绝或 AWS 管理策略评估：

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

这些示例使用已发布的 Cilium 1.20.1 策略 schema，并非要求升级每个集群。HTTP 规则需要受支持的 L7 proxy 路径。AWS VPC CNI chaining 存在有文档记录的高级功能限制，包括 L7 策略；不要假定这些 HTTP 示例在该模式下可用。数值型 Cilium security identity 是为标签集分配的标识，而不是永久的应用 ID。

### CiliumNetworkPolicy

Cilium 在基础 NetworkPolicy 上扩展了更强大的功能。

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

Cilium HTTP 规则会过滤其 L7 proxy 可见的请求；它们不会验证 API key 或建立管理员角色。调用方可以提供 `X-User-Role` header。此示例过滤方法、路径和精确的 `Content-Type`。请在应用程序或经身份验证的 gateway 中实施认证和授权。端到端 TLS 不会自动解密以进行 HTTP 检查。请审查可能在 L4 层允许相同流量的其他策略。

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

已发布的 Cilium 1.20.1 CNP schema 支持 HTTP 和 DNS L7 规则，但不包含 `rules.kafka`。原有的 `role`、`topic` 和 `clientID` 配方不是当前可部署的 API。使用网络策略限制 broker 连通性，然后使用 Kafka 认证和 ACL 对 `orders` 和 `events` 实施 producer/consumer 权限。client ID 不是经过认证的主体。

此 L4 示例假定 TCP 9093 上已配置 TLS broker listener、客户端位于同一 namespace，且客户端 egress/DNS 已另行授权。它不配置 TLS、broker ACL 或 topic 权限。

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

此示例使用基于 Pod 的 CoreDNS。端口 53 上的 `ANY` 同时涵盖 UDP 和 TCP。DNS 查询权限与连接返回 IP 的权限是不同的：解析下面的 database 名称并不允许 database 连接。请替换示例域名，考虑 DNS search suffix/cache/TTL，并验证实际的 resolver 配置。FQDN 规则从 DNS 学习 IP；它们不会认证 SaaS tenant，也不能替代 TLS/应用程序授权。

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

该资源的范围是 cluster，但其 selector 明确将其限制为 `production/app=api`。它允许 gateway Pod 通过 TCP8080 访问。它仅控制 ingress；egress isolation/DNS 和 gateway 自身的 egress 需要相应的策略。此前针对所有 endpoint/世界的 cluster allow 示例不是默认拒绝策略。

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

`host` 包含本地节点及其 host-network container；`cluster` 包含的内容不仅是应用 Pod。`world` 覆盖 cluster 外的 endpoint，不是细粒度 Internet/SaaS allowlist。缩小外部访问范围时请使用明确的 CIDR/FQDN 规则。此示例仅为带标签的 Kubernetes API client 提供 TCP443 访问；请单独配置其 API endpoint、TLS trust、凭证和 RBAC。托管 control-plane 网络路径中的源 identity 可能变化，因此应检查实际 flow identity，而不要将 ingress 扩大到整个 cluster。

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

策略/Tier 示例遵循 Calico Open Source 3.32.2 资源。`projectcalico.org/v3` 需要受支持的 Calico API server 或匹配的 `calicoctl` 工作流；它不是原始 Kubernetes `crd.projectcalico.org/v1` 存储 API。应用前请验证已安装的数据存储/API。Calico 有序 action 和 tier delegation 与可累加的 Kubernetes NetworkPolicy API 不同。

当前 Open Source 文档还描述了 [Istio/Dikastes 应用层集成](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)。HTTPMatch API 需要单独的设置，并支持 ingress Allow 规则。以下 Calico 示例涵盖 L3/L4 策略；本次审查未部署或测试 L7 集成。

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

这两个 global 资源仅选择 `production` namespace 中的 workload。不受约束的 `selector: all()` 也可能影响 host endpoint；不要在没有明确范围和恢复路径的情况下应用 cluster-wide deny。在 tier 中，较低 `order` 会先被评估。该示例允许基于 Pod 的 DNS，否则提供拒绝基线；请添加经过审查的应用流量并考虑更高 tier 的 action。

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

NetworkSet selector 匹配 `metadata.labels`，而不是资源名称。第一个 set 具有 namespace 范围；blocked set 是 global 的，并由下方 security-tier 示例使用。此处所有 CIDR 均为文档范围，必须替换为经过审查的目标。egress 示例允许 TCP443 到带标签的 namespaced set；DNS 是单独的规则。

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

Tier 在所引用的 Calico Open Source 版本中可用，并非仅 Enterprise 可用。当没有规则生效时，选择该 tier 的流量默认为 `Deny`。因此 deny-known-threats tier 显式使用 `defaultAction: Pass`，让无关流量可以到达后续策略。`Pass` 是委派，而不是许可。在部署前填充 application-tier 策略，并验证任何最终 profile/default-tier 行为；创建空 Tier 并不构成完整的应用隔离策略。 `global()` 应放在 `namespaceSelector` 中；另一个标签选择器用于标识 `GlobalNetworkSet`。

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

这些是**可选的策略配置**，并非要一起应用的 bundle。复用 `production` 并不使无关示例兼容：它们的允许规则会累积。请先准备 namespace、workload label、监听端口和实际 DNS 配置。这些示例仅在本地检查 schema/意图，未在 cluster 上执行。

### 微分段

此配置在源端 egress 与目标端 ingress 均允许 frontend→API TCP8080 和 API→database TCP5432 这两类连接，同时允许 DNS。它有意不允许 Internet egress 或外部 frontend ingress。如有需要，请添加获批的目标 CIDR/port 或经身份验证的 egress gateway 配置；从 0.0.0.0/0 排除 RFC1918 并不是 SaaS allowlist。

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

team 配置包括同 team 的 ingress **和 egress**，以及 DNS。共享服务还需要 destination ingress 允许 team-a，并有真实的 TLS443 listener。请限制 namespace 标签管理；team 标签并不是独立的信任边界。

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

`database` namespace 必须存在。production 调用方和 monitoring Pod 需要各自的 egress allow。TCP5432 peer 规则仅允许假定的 PostgreSQL replication transport；请单独配置 database authentication/TLS。TCP9187 假定已单独安装 exporter。

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

假定已存在一个终止客户端 TLS 的 `gateway-system/app=edge-proxy` workload，它可在 TCP80 上访问 web Pod。gateway 的 egress 策略不在此 namespace 中。data peer ingress 和 egress 使用 TCP5432/6379；额外的 replication/cluster-bus/backup 端口取决于所选 database，不能由此推断。在实际部署中应拆分 PostgreSQL 和 Redis selector。

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

请使用经批准、已预配的 diagnostic Pod，配合固定版本的 image 和经过审查的权限。选择实际会触发策略的 source label/namespace/node placement；通用的无标签 Pod 并不代表应用。预配 netshoot 会创建 workload，且可能与 Pod Security admission 冲突。不要在观察脚本中创建/删除固定的共享 `test-pod` 名称。仅对自有测试 endpoint 执行 probe。

### 使用 kubectl exec 测试

请显式设置 context、namespace、现有 Pod 和 container。DNS 成功不代表 TCP 成功；连接被拒绝、不健康的 listener、TLS 错误和策略丢弃是不同结果。这些命令仅测试连通性，并不打印 response body。本次审查未针对 cluster 运行它们。

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

`cilium connectivity test` 会创建测试资源和流量；它不是只读状态命令。请使用获批的隔离 cluster/namespace、兼容的 CLI 和 image、明确的外部目标及清理计划。请查阅 `cilium connectivity test --help` 以了解已安装 CLI 的 filter，而不要假定历史测试名称仍然存在。通过的 suite 并不能证明每项应用策略或 CNI chaining 功能。

### 自动化测试脚本

此脚本仅在两个现有 Pod 中执行受限的 curl probe；不会创建或删除 cluster 资源。设置 `CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER` 和以 `/health` 结尾的非机密 `TARGET_URL`。两个 container 都需要 `sh` 和 `curl`。第一个 Pod 是同一目标的已知允许 positive control。HTTP error response 仍能建立网络可达性，因为此测试并非应用健康验证。

Exit1 表示被阻止的 subject 意外连接；exit2 表示未知/错误；exit3 表示需要佐证的 timeout。timeout **绝不会**自动变为 PASS：应将精确的 source/destination/port/time 与 CNI policy-drop verdict 关联，同时检查 endpoint health、route 和 SG/NACL control。局部 mock test 不主张已实施实时 enforcement。

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

### Amazon VPC CNI 与 NetworkPolicy

Amazon VPC CNI 在启用后支持 network policy。当前 AWS 指南要求标准和 admin policy 均使用 VPC CNI 1.21+、兼容的 EKS platform 和 Linux kernel 5.10+。实施适用于受支持的 EC2 Linux 节点，不适用于 Fargate 或 Windows。请使用当前受支持的 EKS 版本并验证其兼容的 add-on release；不要根据上游 Kubernetes release 推断 EKS 支持。

对于 **EKS-managed** VPC CNI add-on，请在设置文档所述字符串 `"enableNetworkPolicy": "true"` 时保留其现有配置。以下操作会在审查后更改所选 cluster；不会升级 add-on 版本。如果已安装版本不兼容，请停止操作并先遵循文档规定的升级流程。

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

在 rollout 前检查 update status 和策略行为。`--resolve-conflicts PRESERVE` 不会为你合并 replacement JSON document；此示例显式保留现有值。请保留 snapshot 以便恢复。Helm-owned installation 应使用其经过审查的 chart/values 和 `enableNetworkPolicy: true`；不要通过此 managed-add-on command 接管其所有权。设置虚构的 `ENABLE_NETWORK_POLICY` environment variable 并非启用流程。

标准 startup mode 起初可能允许新 Pod，直至其策略被编程。`NETWORK_POLICY_ENFORCING_MODE=strict` 会让符合条件的 Pod 以拒绝状态启动，并要求完整的 allow matrix（包括 DNS）；改变它可能中断 workload。controller-managed Pod 是可靠的测试目标。enforcement 位于 primary Pod interface，因此请单独检查 extra interface、IPv6-to-IPv4 egress、host networking 和 NAT。不要让两个 engine 管理相同的标准策略，也不要将删除 `aws-node` 作为 migration shortcut。

### EKS 增强网络安全策略（2025 年 12 月）

> **发布公告**：December 15, 2025 · [来源](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

该功能真实存在，但其资源使用 **`networking.k8s.aws/v1alpha1`**。`ClusterNetworkPolicy` 是 cluster scoped，且必需指定 `tier`；DNS-based egress 使用下方 namespace 示例中的 `ApplicationNetworkPolicy`。EC2 Linux 上的标准/admin VPC CNI policy 支持并不意味着每种 compute mode 都受支持。DNS 规则仅在 **Auto Mode-launched EC2 instances** 上实施，包括在 mixed cluster 中。

**Auto Mode 前提条件：**在应用下方策略前，请启用其 Network Policy Controller。更新 EKS-managed `vpc-cni` add-on 是独立路径，不会为纯 Auto Mode cluster 启用策略实施。所需设置为 ConfigMap `kube-system/amazon-vpc-cni` 中的 `data.enable-network-policy-controller: "true"`。下面的工作流通过 merge patch 保留其他 ConfigMap data，仅在不存在时创建，并在读取或写入失败时停止。运行前请审查 cluster context 和现有配置。

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

启用后，检查相应的 `PolicyEndpoints` 对象，并在所选 Auto Mode 节点上测试允许和拒绝流量。存储的 flag 或被接受的 policy object 并不能证明实施。请参阅 [Auto Mode network policy setup](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)。本次文档审计未执行 cluster enforcement test。

此 Admin-tier 示例拒绝来自由 namespace 选择的 Pod 到 `isolated-demo` 的入站流量，包括该 namespace 中的 Pod。它不是完整的 external/host-network firewall 或 DNS allow policy。Admin Deny 不能被 namespace NetworkPolicy 覆盖。在添加其他 action 前审查实际安装的 CRD：当前 upstream AWS controller schema 将允许 action 命名为 `Accept`，而 user-guide prose 使用“Allow”。

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

FQDN 示例在 `production` 中选择 `app=backend`。**请将 `10.100.0.10/32` 替换为 cluster 实际的 Auto Mode CoreDNS IP**：即 Service CIDR network address 加 10（IPv6 为 `::a/128`）。纯 Auto Mode CoreDNS 运行于节点上；常规 CoreDNS Pod selector 不能互换。允许 TCP 和 UDP DNS。请使用不会与该 namespace 中 NetworkPolicy 冲突的唯一资源名称。

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

DNS proxy 观察允许的 answer 及其 TTL，随后 data path 允许学习到的 destination IP/port。这不会认证 SaaS account 或证明 peer 的 HTTP identity；shared IP 和 DNS behavior 需要测试。TLS certificate verification、application authorization、route 及任何 Route 53 DNS Firewall rule 仍然相关。其他适用策略和直接 backend path 必须一并审查。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode 策略](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Pod 的安全组

此 binding 示例假定具备 EKS VPC Resource Controller、其 **cluster-role** 权限、受支持的 trunking-compatible EC2 Linux node 和经过审查的 VPC CNI 配置。当前 AWS 指南排除 Windows 和 EKS Auto Mode。Fargate 使用独立的 Pod-SG model；仅拥有 security group 并不会获得 VPC-CNI NetworkPolicy 支持。通过 owner 将 binding 应用于新的匹配 workload Pod；现有 Pod 不会自动改造。

对于 Calico 加 Pod SG，AWS 文档指出需要 VPC CNI1.11.0+ 且 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`；同时也应采用当前 CNI 要求，而不是将该最小版本视为推荐版本。标准模式 external SNAT 可以使用 node SG 而不是 Pod SG。请验证精确路径。旧的 bare PostgreSQL Pod 缺少 credentials/storage，并非可用的 database deployment。

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

Terraform fragment 允许来自一个经过审查的 app SG 的 DB ingress，且不发起新的 egress connection。stateful return traffic 由 SG tracking 允许；请单独添加所需的 DNS、replication、backup 或 external egress。variable 是现有 operator input；未执行 Terraform plan/apply。

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

NetworkPolicy、实际应用的 SG 和 NACL 都必须允许相关路径。此仅 ingress 的 NetworkPolicy 不会限制 database egress；请添加所选 egress 配置和 source-Pod egress。多个 SG 会合并其 allow。NACL 是**无状态的**，因此允许 inbound5432 的 subnet rule 需要有到 client ephemeral port 的匹配返回路径，并在 client subnet 上设置适当规则。以下 fragment 不能代替完整且经过审查的 ACL rule set。

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

请选择 **AWS VPC CNI chaining** 或单独设计的完整 CNI/IPAM migration。chaining mode 中，AWS VPC CNI 保留 ENI/IPAM 职责，而 Cilium 挂接其 datapath。请保留 `aws-node`；删除它不是 installation shortcut。审查现有 add-on/Helm owner，并避免重叠的 policy-enforcement engine。现有 Pod 需要受控重建后 chaining policy 才会生效；请规划 disruption 和 rollback。

官方 1.20.1 chaining guide 提供这些 value，但也记录了 L7/IPsec limitation。它包含旧的 illustrative output；它们并不验证当前 EKS environment。请准备 chart repository/package、验证 provenance 并先 render：

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

policy editor 有助于编写策略；**Hubble UI 可视化已观察到的 service flow**。它们是不同的工具。启用 Hubble/UI 会更改 cluster configuration，应由 installation owner 负责。对于已安装且已认证的 Hubble service，请检查现有 service 并使用 local port-forward。不要将 UI 公开暴露为 debugging shortcut。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium 策略 Verdict 检查

使用经过认证的 Hubble connection。`DROPPED` 包含策略以外的原因；请检查 drop reason、endpoint identity、time 和 direction。在某个点观察到 `FORWARDED` 并不能保证端到端交付。


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

Enterprise management UI 需要已授权产品及其实际 service/TLS/authentication configuration；它不会随 Calico Open Source 自动安装。转发前请检查已安装的 service name/port 和 access policy。不要假定每个 installation 都存在 `cnx-manager`。

### 网络策略可视化工具

使用 `kubectl get networkpolicy -n <namespace>` 和 `kubectl describe networkpolicy <name> -n <namespace>` 检查 Kubernetes policy selector/rule，并使用已安装 engine 的 authenticated flow tool 检查 enforcement。第三方 viewer/plugin 的可用性和 flag 必须根据该项目当前 release 进行检查。仅有 YAML graph 不能证明 dataplane enforcement。

### 使用 Kube-hunter 进行安全测试

kube-hunter 是 cluster exposure/security scanner，而非 NetworkPolicy allow/deny verifier。其 scan 可能生成侵入性流量；请使用明确获批的 target/scope 和经过审查的 release/image。不要根据通用策略教程将未固定版本的 scanner 部署到 live namespace。本次审查未执行 scanner。

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

此只读 inventory 会分别列出 namespace-wide 的空 allow baseline，针对 ingress 和 egress。它处理空 `[]` 和不存在的 rule array，而规则 `{}` 允许流量，不是 deny baseline。API/authorization error 会失败，而不会显示为零策略。列出的 baseline **不是隔离证明**：其他 allow rule、extension policy、未覆盖的 Pod 和 CNI state 仍需审查。

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

## 总结

Kubernetes NetworkPolicy 是控制 cluster 内 Pod 通信的核心安全机制：

1. **基础 NetworkPolicy**：具备 namespace 范围，支持 podSelector/namespaceSelector/ipBlock
2. **Cilium 扩展**：L7 策略、基于 DNS FQDN 的策略、cluster-wide 策略
3. **Calico 扩展**：GlobalNetworkPolicy、NetworkSet、基于 Tier 的策略
4. **EKS 注意事项**：VPC CNI NetworkPolicy 激活、Pod 的安全组、ClusterNetworkPolicy 和基于 DNS（FQDN）的 egress control

### 建议

- 对所有 production namespace 应用默认拒绝策略
- 遵循最小权限原则，仅允许必需流量
- 定期进行策略审计和测试
- 需要 L7 策略时考虑 Cilium

---

## 参考资料

- [Kubernetes Network Policies 官方文档](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy 文档](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy 文档](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS 安全最佳实践 - 网络安全](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS 增强网络安全策略（2025-12-15）](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod 安全组](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
