# 第 5 部分：网络策略

> **审阅基线**：Calico 3.32.2；Calico 3.32 已测试的 Kubernetes 版本范围为 1.34–1.36。**最后更新**：2026 年 9 月 12 日。
>
> 示例假设使用标准 Calico API Server（`projectcalico.org/v3`）、Kubernetes datastore，以及兼容且会执行策略的数据面。在应用策略前，请使用专用的 `calico-demo` namespace、已知的工作负载标签、就绪的 endpoints 和正常工作的基线。各节是彼此独立的模式，不是一组可以整体应用的 manifest。已有的更高优先级策略、DNS 实现、Service NAT、主机策略和应用行为都会影响结果。本次审阅没有运行生产集群、admission server 或数据包转发测试。

## 简介

网络策略控制工作负载与其他端点之间允许建立的连接。Calico 在标准 Kubernetes API 基础上增加了有序策略、显式动作、全局作用域和主机端点控制。功能是否可用取决于产品和执行路径：基于 DNS 域名的策略属于商业扩展；开源版 HTTP 策略则需要按文档配置 Istio/Dikastes 集成。

本深入指南涵盖 Kubernetes 标准策略和 Calico 扩展能力，为企业安全需求提供模式和示例。

***

## Kubernetes 标准 NetworkPolicy

### NetworkPolicy 基础

Kubernetes NetworkPolicy 是按 namespace 作用域生效、用于选择 Pods 的资源。Ingress 和 egress 隔离彼此独立；对于每个已隔离方向，允许的流量是所有匹配 Kubernetes 策略的并集。如果连接两端都处于隔离状态，发起连接的来源端 egress 策略和目标端 ingress 策略都必须允许新连接。已允许连接的响应流量不需要额外的反向方向允许规则。

`from`/`to` 列表中的各项是 **OR** 关系。同一项中的 `namespaceSelector` 和 `podSelector` 是 **AND** 条件。未搭配 namespace selector 的 Pod selector 指向该策略所属的 namespace。

若没有适用的 Kubernetes 策略，该 API 不会隔离相应方向的流量；但这不会覆盖主机防火墙、Calico 策略或其他控制措施。策略变更对现有连接的影响取决于具体实现，因此应使用新连接进行验证。Service 或负载均衡器 NAT 前后观察到的 `ipBlock` 地址也取决于具体实现。

![对比图显示：没有 NetworkPolicy 时，各 Pod 可以彼此自由连接；添加 NetworkPolicy 后，网状连接被收窄为一条明确允许的路径，其余连接均被阻止。](../../.gitbook/assets/en-networking-calico-05-network-policy-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-05-network-policy-0.html)

> 箭头表示图示策略下的新连接，不表示已允许连接的响应包。示例假设没有其他策略、防火墙或路径限制；仅仅存在任何 NetworkPolicy，并不会隔离所有 Pod 或所有方向。

### NetworkPolicy 基本结构

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: calico-demo
spec:
  # Which pods this policy applies to
  podSelector:
    matchLabels:
      app: web

  # Policy types: Ingress, Egress, or both
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (who can connect TO these pods)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
        - namespaceSelector:
            matchLabels:
              purpose: monitoring
        - ipBlock:
            cidr: 10.0.0.0/8
            except:
              - 10.0.1.0/24
      ports:
        - protocol: TCP
          port: 8080

  # Egress rules (where these pods can connect TO)
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

### Kubernetes NetworkPolicy 的限制

| 能力 | Kubernetes NetworkPolicy | Calico 扩展或前提条件 |
| --- | --- | --- |
| 作用域 | namespace 范围的 Pod 策略 | GlobalNetworkPolicy 可跨 namespace 选择工作负载和 HostEndpoints |
| 顺序/动作 | 允许规则采用累加方式；用户不能定义策略顺序 | Tier/顺序，以及 Allow、Deny、Log、Pass 动作 |
| 端口 | TCP/UDP/SCTP、命名端口；通过 `endPort` 指定数值范围（从 1.25 起稳定；需要插件支持） | Calico 端口范围语法，以及额外的 IP 协议/ICMP 匹配 |
| HTTP 方法/路径 | 此 API 不支持 | 开源版 `http` 规则需要配置 Istio/Dikastes 应用层执行 |
| DNS 域名 | 此 API 不支持 | 例如 Calico Enterprise 域名策略功能；开源版 3.32 CRD 中没有 `domains` 字段 |
| 主机接口 | 不是通用的节点防火墙 | HostEndpoint 策略具有独立的本地、转发和 failsafe 语义 |

标准 NetworkPolicy 对象的作用域，与 Kubernetes 较新的集群策略 API 不同；不要假设所有 Kubernetes 网络安全 API 都只适用于 namespace。请检查所选数据面的协议和日志支持情况，不要把 schema 接受配置等同于实际执行。

***

## Calico NetworkPolicy 扩展

### 扩展协议支持

SCTP 示例需要兼容的 classic dataplane：Calico 3.32 eBPF 不支持 SCTP 策略或 Service。

Calico 除 TCP 和 UDP 外，还支持其他协议：

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: extended-protocols
  namespace: calico-demo
spec:
  selector: app == 'network-tools'

  ingress:
    # ICMP ping
    - action: Allow
      protocol: ICMP
      icmp:
        type: 8  # Echo Request
        code: 0

    # ICMPv6
    - action: Allow
      protocol: ICMPv6
      icmp:
        type: 128  # Echo Request

    # SCTP
    - action: Allow
      protocol: SCTP
      destination:
        ports:
          - 3868  # Diameter

    # UDP with port range
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - "5000:6000"  # Port range
```

### 端口范围和命名端口

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: port-examples
  namespace: calico-demo
spec:
  selector: app == 'multi-port-app'

  ingress:
    # Port range
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - "8080:8090"

    # Named ports (from pod spec)
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - http      # References containerPort name
          - metrics   # References containerPort name

    # Mix of specific ports and ranges
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 22
          - 80
          - 443
          - "3000:3100"
```

### 增强的选择器语法

Calico 使用表达式选择器。以下规则展示了不同写法的差异：把所有宽泛的 Allow 合并到同一策略会扩大允许范围。`app != 'untrusted'` 也会匹配没有此标签的资源，不能据此认为它们可信。

`selector: !has(x)` 会匹配作用范围内已知但缺少该标签的资源。`notSelector: has(x)` 会否定数据包匹配条件，也可能匹配选择器中不存在的外部地址。规则中的 `selector: all()` 并不代表匹配所有数据包；若要匹配所有数据包，应省略端点选择器条件。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: selector-examples
  namespace: calico-demo
spec:
  # Label equality
  selector: app == 'web'

  ingress:
    # Set membership
    - action: Allow
      source:
        selector: app in {'frontend', 'api-gateway', 'monitoring'}

    # Negation
    - action: Allow
      source:
        selector: app != 'untrusted'

    # Label existence
    - action: Allow
      source:
        selector: has(security-cleared)

    # Combining conditions (AND)
    - action: Allow
      source:
        selector: app == 'backend' && tier == 'internal'

    # OR inside one selector expression
    - action: Allow
      source:
        selector: (app == 'frontend') || (app == 'api')

    # Namespace selector
    - action: Allow
      source:
        namespaceSelector: environment == 'production'
        selector: app == 'authorized-client'
```

***

## GlobalNetworkPolicy

GlobalNetworkPolicy 不限于 namespace，可跨 namespace 选择工作负载端点或 HostEndpoints。单独使用 `selector: all()` 并不等于“只选择所有应用 Pod”。这些示例会明确将选中的工作负载限制在演示 namespace 内，以免影响系统和主机流量。

### 显式例外的默认拒绝策略

空策略会同时选择 ingress 和 egress。未设置的 `order` 排在已显式设置顺序的策略之后；10,000 不是特殊的“最低优先级”值。空规则不会覆盖先前的终止性 Allow。对于应用策略不能覆盖的限制，应使用单独管理且顺序更靠前的 tier。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-default-deny
spec:
  tier: default
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-essential-egress
spec:
  tier: default
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: needs-platform == 'true'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      destination:
        services:
          name: kubernetes
          namespace: default
```

此示例仅允许带有 `needs-platform=true` 标签的工作负载进行平台 egress。Service 匹配依赖 **Kubernetes datastore** 中实际的 `kubernetes/default` endpoints 和端口；使用 etcd datastore 时会忽略该匹配。不要将此 Service 匹配与目标端口、CIDR 或 selector 混用。网络连通到 API 与 API 身份验证/RBAC 是两回事。

请确认实际 DNS 部署。namespace 和 Pod selector 一起使用，可避免其他带有 `kube-dns` 标签的 Pod 被误认为可信解析器。NodeLocal DNS 需要根据实际路径使用不同的匹配条件。在枚举系统依赖之前就在 `kube-system` 创建空策略可能破坏集群；请在独立的测试 namespace 演示该模式。

### 更早执行的 egress 防护规则

这个独立示例先阻止所选演示工作负载访问 IPv4 metadata 地址，再于当前 tier 末尾将其他流量交由后续 tier 处理。它并不声称能全面防御 SSRF、保护特权进程或使用 host network 的进程，或覆盖所有平台 metadata 端点。

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: egress-guardrail
spec:
  order: 50
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-guardrail.block-imds-v4
spec:
  tier: egress-guardrail
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Deny
      destination:
        nets: [169.254.169.254/32]
```

不要在同一 tier 的后续限制规则之前放置无条件 Pass。保留平台所需的身份和 DNS 路径，并检查工作负载到主机的实际执行行为。

***

## NetworkSet 和 GlobalNetworkSet

NetworkSet 用标签组织可重复使用的 IP/CIDR 组；策略 selector 引用的是这些标签，而不是对象名称。下方地址仅用于说明，并非真实的国家/威胁情报源。标签 selector 也可能匹配带有相同标签的 endpoints，因此应使用受控标签，并确认预期的 namespace 或全局作用域。

在 namespaced policy 的实体匹配中，使用 `namespaceSelector: global()` 来选择 GlobalNetworkSet。Namespaced NetworkSet 仍限于其所属 namespace。如果可信范围与阻止范围重叠，应先评估 deny；较早匹配的 Allow 是终止性动作。

### NetworkSet（namespace 范围）

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: corporate-networks
  namespace: calico-demo
  labels:
    network-type: corporate
spec:
  nets:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16

---
# Reference in policy
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-corporate
  namespace: calico-demo
spec:
  selector: app == 'internal-app'

  ingress:
    - action: Allow
      source:
        selector: network-type == 'corporate'  # References NetworkSet by label
```

### GlobalNetworkSet（集群范围）

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: external-trusted-ips
  labels:
    network-group: external-trusted
spec:
  nets:
    - 203.0.113.0/24     # Partner network
    - 198.51.100.0/24    # CDN network
    - 192.0.2.50/32      # Specific trusted IP

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-blocked-networks
  labels:
    network-group: blocked
spec:
  nets:
    # Illustrative test ranges, not geolocation or threat intelligence
    - 192.0.2.128/25
    - 203.0.113.128/25

---
# Reference in GlobalNetworkPolicy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: external-access-control
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: has(external-facing)
  order: 200
  types:
    - Ingress

  ingress:
    # Deny overlaps before considering trusted ranges.
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'blocked'
    - action: Allow
      source:
        namespaceSelector: global()
        selector: network-group == 'external-trusted'
```

***

## 分层策略

Calico 开源版 3.32 提供 Tiers。它们可以对 namespaced 和 global Calico 策略分组；它们不是从 Kubernetes NetworkPolicy 逐步升级到 GlobalNetworkPolicy 的层级。

### 评估顺序和默认行为

对于常规端点策略，先按 tier 的 `order` 从小到大评估，再按该 tier 内策略的 `order` 从小到大评估。未设置策略顺序的策略排在已显式设置顺序的策略之后。评估时要考虑被选中的端点**及流量方向**。

| 情况 | 结果 |
| --- | --- |
| 此 tier 中没有策略选择该端点/方向 | 跳过此 tier |
| 规则 Allow 或 Deny | 结束该端点/方向的策略判断 |
| 规则 Log | 继续评估下一条规则 |
| 规则 Pass | 跳过此 tier 中剩余的策略，并尝试下一个适用的 tier |
| 适用 tier 中没有匹配到终止规则 | 执行该 tier 的 `defaultAction`，其默认值为 Deny |
| 最后一个适用的 tier 执行 Pass | 评估端点 Profiles；没有 profile 允许则拒绝 |

这不代表“没有规则匹配，就总是进入下一个 tier”。而且一个端点上的 Allow 不能绕过另一端点的策略。下文会介绍具有不同后续处理行为的 Pre-DNAT 和 untracked 主机策略。

内置 `default` tier 的固定顺序是 **1,000,000**，不是 1,000，也不是无穷大。Kubernetes NetworkPolicy 和未显式指定 tier 的 Calico 策略都属于该 tier。目前的 `kube-admin` 和 `kube-baseline` tiers 使用 1,000 和 10,000,000 的顺序，并对相应的 Kubernetes 集群策略集成配置 Pass 默认动作；因此，`default` 并不总是最后一个可能执行的 tier。

### 分别执行安全、平台和应用策略

以下示例使用 tier 末尾的 Pass 动作，让安全和平台 tier 先检查所有适用规则，再将处理交给后续层。创建或重新排序 tier 需要由中心化权限控制。

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
  order: 500
  defaultAction: Deny
```

下方示例先使用一个仅供文档演示的威胁地址，再单独配置受限数据规则。如果第一个安全策略末尾就执行 Pass，就会跳过第二个策略。将委派放在 **tier 末尾**，可以避免这种绕过。受限数据标签展示的是网络分段示例，并不代表已完整满足 PCI DSS。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-threats
  labels:
    network-group: demo-threat
spec:
  nets:
    - 192.0.2.100/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-threats
spec:
  tier: security
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress:
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
  egress:
    - action: Deny
      destination:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.restricted-data
spec:
  tier: security
  order: 20
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: data-scope == 'restricted'
  types: [Ingress]
  ingress:
    - action: Deny
      source:
        notSelector: data-scope == 'restricted'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.dns
spec:
  tier: platform
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: application.frontend
  namespace: calico-demo
spec:
  tier: application
  order: 10
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

`namespaceSelector: global()` 与单独的标签 selector 配合使用，可以选择 GlobalNetworkSet。`global(label == 'value')` 不是有效语法。平台层的 DNS Allow 是为所选工作负载 egress 配置的有意终止例外；应用 tier 的规则不能再收窄此例外。应用策略只管理选中的 frontend，不管理 namespace 中的所有工作负载。

DNS 示例假设使用已确认 namespace 和标签的常规 CoreDNS Pods。NodeLocal DNSCache 或 EKS Auto Mode 节点本地 DNS 需要针对实际解析器路径配置规则，不能直接复制 Pod selector。应保留到所需解析器的访问，并验证 UDP 和 TCP 查询。

### Tier RBAC 集成

Calico tier RBAC 使用伪资源 `tier.networkpolicies` 和 `tier.globalnetworkpolicies`，并要求对目标 Tier 具备 `get` 权限。Calico authorizer 会显式检查 `application.*` 等合成名称。这不等于在普通 `networkpolicies` 资源上使用通用 Kubernetes `resourceNames` 通配符。

下面的完整绑定示例，允许一个 service account 在 application tier 中编辑 namespaced policy；它不会授予创建/重排 tier 或管理全局策略的权限。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: policy-editor
  namespace: calico-demo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: demo-get-application-tier
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tiers"]
    resourceNames: ["application"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: demo-get-application-tier
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: demo-get-application-tier
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tier.networkpolicies"]
    resourceNames: ["application.*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: demo-edit-application-policies
```

全局策略编辑使用 `tier.globalnetworkpolicies`，并通过明确限定范围的 ClusterRole/ClusterRoleBinding 授权。对目标 Tier 的 `get` 权限应与修改 Tier 顺序的权限分开管理。

此示例假设使用标准 Calico 聚合 API Server。原生 v3 CRD 使用 admission webhook 执行 tier 的 create/update/delete 授权；该 webhook 不能限制 GET/LIST/WATCH。不要声称两种模式具有相同的读取隔离效果。普通 `kubectl auth can-i` 无法验证 Calico tier 检查的组合效果：应在隔离环境中使用没有其他宽泛绑定的主体，实际测试允许和禁止的请求。Kubernetes RBAC 权限采用累加方式，已有的宽泛授权可能破坏此处的限制意图。

***

## 基于 FQDN 的 egress 策略

开源版 3.32 CRD 中没有 `destination.domains` 或 Felix `dnsTrustedServers` 字段。设置 `policySyncPathPrefix` 会启用应用层集成所使用的 policy-sync 路径，但不会为开源版增加基于 DNS 域名的策略能力。

Calico Enterprise 3.23 文档说明了如何在 **egress Allow** 规则中按 DNS 域名匹配。控制器从可信 DNS 服务器学习 A/AAAA/CNAME 答案，并允许到相应目标 IP 的流量。这是基于 IP 的执行方式，不是 HTTPS 主机名身份验证，因此还需要考虑目标 IP 共享和应用身份。集群内部服务应使用工作负载/Service selector。

下方商业功能示例假设该功能已启用、可信解析器已验证，且更早执行的终止性 Allow 不会绕过该规则。每条规则只能有一个 `destination` map；重复的 YAML 键可能会悄悄丢弃域名限制。

```yaml
# Calico Enterprise 3.23 example; NOT an Open Source 3.32 resource.
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-approved-domains
  namespace: calico-demo
spec:
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        domains:
          - api.github.com
          - "*.example.com"
        ports: [443]
```

请将文档域名替换为已批准的真实域名。`*.example.com` 会匹配 `api.example.com` 和 `deep.api.example.com`，但不会匹配根域名 `example.com`。通配符必须占据完整的名称组件，且只支持一个通配符。Inline DNS policy 模式支持前缀通配符；非前缀通配符模式需要使用文档所述的其他模式。宽泛后缀（例如 `*.amazonaws.com`）不是 AWS 账户或 IAM 的边界。

保持实际解析器的 UDP 和 TCP 访问畅通，并使其 IP 与可信 DNS 配置相符。Node-local resolver 需要针对具体部署处理。商业指南指出，不应在 egress-gateway Pod 的 egress hook 上执行域名策略，因为节点范围的 DNS 缓存可能导致匹配缺失或间歇性出现。

在开源版中，可使用配置了自身应用授权的显式 egress proxy/gateway；在适用时，也可维护 IP/CIDR NetworkSet。不要用一次性 DNS 查询替代持续执行的域名策略。

***

## HTTP 方法过滤（第 7 层）

Calico 开源版 3.32 通过文档说明的 **Istio + Dikastes** 集成支持 HTTP 策略。仅安装任意 Envoy proxy，或在普通 CNI 策略中加入 `http` 字段，都不会启用第 7 层策略执行。

前提包括 Felix Policy Sync API、Calico CSI socket 挂载、Dikastes 注入，以及相关流量路径上的 Envoy 外部授权。当前集成指南介绍了 Kubernetes 原生 sidecar 的 Istio 注入方式，并建议使用 Istio 1.28.1；这并不意味着对之后所有 Istio 版本都作出了兼容性承诺。选择生产环境版本组合前，请查看维护中的 [Istio 安装指南](../../service-mesh/istio/01-installation.md)、两个项目的支持周期和实际集成。本指南没有部署该集成。

以下是已完成集成的工作负载上用于 **ingress Allow** 的示例。HTTPS 方法/路径规则要求执行代理在 TLS 终止后能够看到 HTTP 请求。来源 Pod 标签标识的是工作负载，不是通过认证的最终用户；请配置集成所需的可信工作负载身份/mTLS 路径，并保留 DNS 和 Istio 控制面所需的网络访问。在依赖这些策略前，请验证允许和拒绝的请求，以及代理/授权服务故障时的行为。

### HTTP 匹配规则

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: l7-http-policy
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'api-server'
  order: 300
  types:
    - Ingress

  ingress:
    # Allow only GET and HEAD for read-only clients
    - action: Allow
      source:
        selector: role == 'reader'
      http:
        methods:
          - GET
          - HEAD
        paths:
          - prefix: /api/v1/

    # Allow the listed methods for admin-labeled workloads
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        methods:
          - GET
          - POST
          - PUT
          - DELETE
          - PATCH

    # Allow health checks
    - action: Allow
      http:
        methods:
          - GET
        paths:
          - exact: /health
          - exact: /ready
```

### 基于路径的过滤

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: path-based-policy
  namespace: calico-demo
spec:
  selector: app == 'web-app'

  ingress:
    # Public endpoints
    - action: Allow
      http:
        paths:
          - prefix: /public/
          - exact: /

    # Admin endpoints - restricted
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        paths:
          - prefix: /admin/

    # API endpoints - authenticated only
    - action: Allow
      source:
        selector: has(api-access)
      http:
        paths:
          - prefix: /api/
```

***

## 主机端点保护

HostEndpoint 表示 Calico 管理的节点接口。创建 HostEndpoint 可能会立即改变主机连通性。`defaultEndpointToHostAction` 控制工作负载到本地主机的行为；它不会创建 HostEndpoints。`Installation.calicoNetwork.hostPorts` 控制 hostPort 支持，不会自动保护主机。

### 手动创建 HostEndpoint 和策略

以下**字段示例不是完整的主机防火墙**。它假设有一个自行管理的测试 worker `demo-worker`，地址为 `10.0.1.10`，bastion 地址为 `10.0.0.100`，控制面来源地址为 `10.0.1.5`，接口为 `eth0`。创建 HostEndpoint 前，请替换为已核实的身份和地址，并预先准备所有必需的管理、DNS、DHCP、BGP、API、健康检查和 egress 规则。此示例不模拟 EKS 管理的控制面节点。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-worker-ingress
spec:
  order: 100
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.100/32]
      destination:
        ports: [22]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.1.5/32]
      destination:
        ports: [10250]
---
apiVersion: projectcalico.org/v3
kind: HostEndpoint
metadata:
  name: demo-worker-eth0
  labels:
    host-demo: "true"
spec:
  node: demo-worker
  interfaceName: eth0
  expectedIPs: [10.0.1.10]
```

kubelet 规则指向 worker 上经过身份验证的 10250 端点。不要默认开放已经过时且未认证的只读端口 10255。示例仅定义 ingress；手动创建的 HostEndpoint 若没有 egress 策略/profile，可能会拒绝主机发起的流量。请先完成实际基线策略。

Calico 默认 failsafe 包括入站 TCP 22 和其他连通性端口。它们会绕过上述 SSH 规则的限制意图，因此这条规则本身**不能**将 SSH 限制到 bastion。修改 failsafe 列表前，请先审查列表并验证恢复路径；不要直接清空列表。

### 自动创建 HostEndpoints

节点控制器的 `KubeControllersConfiguration.spec.controllers.node.hostEndpoint.autoCreate` 控制是否自动创建 HostEndpoints。使用 merge patch 保留其他控制器配置：

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
# Apply only after reviewing existing host endpoints and global policies.
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type=merge \
  -p '{"spec":{"controllers":{"node":{"hostEndpoint":{"autoCreate":"Enabled"}}}}}'
```

此操作可能影响所有符合条件的节点。自动创建的端点通常带有 default-allow profile；该 profile 不会覆盖匹配策略中的 Deny。自定义模板和 `createDefaultHostEndpoint` 可以缩小所生成的端点范围，但在已有部署中修改前，应先审查现有端点和策略。

### 本地流量与转发流量

常规主机策略的 `applyOnForward` 默认值为 false。设为 true 后，策略也会应用于转发流量，而转发流量仍须通过相关工作负载策略。如果没有转发策略选择该端点/方向，则默认允许转发流量；如果选中的转发策略没有 Allow，则会拒绝。主机本地终止流量使用不同的默认拒绝行为（仍受 Profiles/failsafe 影响）。

## DoNotTrack 和 PreDNAT 策略

以下是 Linux 主机策略模式，适用于 HostEndpoints；不能用它们关闭普通所选 Pod 的连接跟踪。请确认所选数据面支持这些功能。`doNotTrack` 和 `preDNAT` 不能同时设为 true，并且任一功能都要求设置 `applyOnForward: true`。

### DoNotTrack

匹配流量的 untracked Allow 会跳过连接跟踪。它不一定能提升性能，并且可能与需要 conntrack 的 Service/NAT 路径冲突。请求和响应都需要显式规则；示例假设测试主机上运行的 DNS 进程直接为可信客户端子网提供服务。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-untracked-dns
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 10
  types: [Ingress, Egress]
  doNotTrack: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: UDP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
  egress:
    - action: Allow
      protocol: UDP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
    - action: Allow
      protocol: TCP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
```

与常规端点策略不同，untracked 阶段未匹配不会触发 tier 末尾的默认丢弃；后续 tracked 策略仍会执行。这不等于自动启用主机的默认拒绝防火墙。

### PreDNAT

Pre-DNAT 策略会在 DNAT 前看到原始目标 IP/端口。它仅适用于 ingress，并会对允许的返回流量使用常规连接跟踪。下例保护所选主机路径上特定的 TCP NodePort 30080：

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-nodeport
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 20
  types: [Ingress]
  preDNAT: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [30080]
    - action: Deny
      protocol: TCP
      destination:
        ports: [30080]
```

Pre-DNAT 阶段没有默认丢弃。未匹配的流量会继续进入后续主机/工作负载策略。第二条显式规则会拒绝到此 NodePort 的不可信流量；该示例不涵盖其他端口。若流量直接到达 Pod、没有经过此主机 NodePort，则此规则不会生效。

***

## 策略调试

检查实际标签、namespace、Service endpoints、所有适用 tiers 和两个流量方向。在标准 Calico API Server 中，没有 tier selector 的列表查询可能默认只查 `default` tier；`-A` 表示所有 namespaces，并不会自动列出所有 tiers。

```bash
kubectl get networkpolicies.networking.k8s.io -n calico-demo -o yaml
kubectl get tiers.projectcalico.org -o yaml
for CALICO_TIER in $(kubectl get tiers.projectcalico.org -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get networkpolicies.projectcalico.org -n calico-demo \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
  kubectl get globalnetworkpolicies.projectcalico.org \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
done
calicoctl get workloadendpoint -n calico-demo \
  --selector="app == 'frontend'" -o yaml
```

```bash
CALICO_NAMESPACE=calico-system
CALICO_NODE=demo-worker
CALICO_POD="$(kubectl -n "$CALICO_NAMESPACE" get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')"
test -n "$CALICO_POD"
kubectl -n "$CALICO_NAMESPACE" logs "$CALICO_POD" -c calico-node --tail=200
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  calico-node -felix-ready
```

```bash
# Assumes named, ready test Pods and an nc binary in the client image.
TARGET_POD=backend-test
TARGET_IP="$(kubectl -n calico-demo get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')"
test -n "$TARGET_IP"
kubectl -n calico-demo exec frontend-client -- nc -z -w 3 "$TARGET_IP" 8080
```

`calico-node -felix-ready` 命令检查就绪状态。它不是策略跟踪命令，也不测量逐数据包策略评估时间。已发布的开源版 `calicoctl` 不再提供以前的 `policy-trace` 命令。列出某个 endpoint 或搜索策略文本，也不能计算完整的有效策略。

使用新的连接测试允许的客户端、不可信客户端、错误端口、跨 namespace 客户端以及解析器访问。检查目标端口，而不是客户端临时分配的源端口。分别测试 Pod 地址和 Service 地址，以区分策略问题与 endpoint/NAT/转发问题；因此 kube-proxy 或其替代组件也可能相关。

使用 iptables 数据面的集群中，应在正确的节点/网络 namespace 检查实际 `cali-` chains；占位符 hash 并不是真实 chain 名称。iptables Log 动作会写入主机 kernel log；Felix stdout 主要是组件/控制器诊断信息。无 stdout 消息或计数为零，都不能证明所有路径上没有使用某策略。eBPF/nftables 需要使用各自后端的诊断方式；仅运行 `tc filter show` 无法解释最终策略判定。

### 执行前先暂存策略

开源版 3.32 提供 `StagedNetworkPolicy`、`StagedGlobalNetworkPolicy` 和 `StagedKubernetesNetworkPolicy`。暂存资源不会实际执行数据包策略判定。配置 flow-log/Whisker pipeline 后，可查看 `policies.pending`，预览其观察到的影响。

```yaml
apiVersion: projectcalico.org/v3
kind: StagedNetworkPolicy
metadata:
  name: default.preview-backend-egress
  namespace: calico-demo
spec:
  tier: default
  order: 100
  selector: app == 'frontend'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

此预览有意只包含后端连接。在创建相应的生效策略前，请检查所需 DNS 或其他流量是否会被拒绝。没有观察到流量，并不能证明不需要某项依赖。单独使用 `action: Log` 并不是通用的仅审计模式：策略评估会继续，最后仍可能 Deny。

***

## 常见策略模式库

### 前端 → 后端 → 数据库

演示假设工作负载已就绪，并带有展示的标签和监听端口。每条服务器端口规则都是**目标端口**；匹配 `source.ports: [8080]` 通常会拒绝使用临时源端口的客户端。所有数值端口规则都指定 TCP。演示中的 gateway 是应用测试组件，并不假设它是某种 ingress controller 的标签。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.frontend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.backend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'backend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports: [5432]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.database
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'database'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'backend'
      destination:
        ports: [5432]
  egress: []
```

对确实需要 DNS 的客户端，使用带有前置标签条件的作用域化 essential-egress 模式，另行允许 DNS。此简化模式中的 database 不会发起新的 egress 连接；有状态响应仍可通过。备份、复制和外部依赖需要各自经过审查的规则。

### 租户隔离

Calico 不会在 selector 内插值 `$(namespace.tenant)`、`${namespace.labels.tenant}` 或 `${namespace.name}`。应为每个明确的租户值生成独立策略；同一 namespace 内的隔离也可以使用 namespaced policy。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.team-a-isolation
spec:
  order: 500
  namespaceSelector: tenant == 'team-a'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        namespaceSelector: tenant == 'team-a'
  egress:
    - action: Allow
      destination:
        namespaceSelector: tenant == 'team-a'
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

此规则允许 team-a 内的所有流量，包括跨 namespace 的流量（只要带有该标签）。必须控制 namespace 标签管理和策略编辑权限；更早执行的 Allow 可能绕过预期隔离。请测试跨租户和未设置标签的 namespace。

### 同一 namespace 加共享服务

在此 namespaced policy 中，没有 namespace selector 的实体 selector 仍只会在 `calico-demo` 内匹配。这是另一种模式，用于替代较严格的微服务模式，不应再叠加到该模式之上。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.namespace-and-shared
  namespace: calico-demo
spec:
  order: 200
  selector: all()
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        selector: all()
  egress:
    - action: Allow
      destination:
        selector: all()
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'logging'
        selector: app == 'log-receiver'
        ports: [24224]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'auth'
        selector: app == 'identity-provider'
        ports: [8080]
```

请单独添加必需的解析器规则，并确保目标端策略允许客户端访问。日志端口或身份提供方标签是明确的演示假设；请确认实际接收方协议/端口以及应用身份验证。

### 开源版 egress 控制

当服务具有固定地址约定时，可使用 NetworkSet 维护已批准的地址。示例 IP 仅用于文档说明；它不是实际 API 端点，也不是永久有效的 DNS 解析结果。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: approved-api-ips
  namespace: calico-demo
  labels:
    destination-group: approved-api
spec:
  nets: [203.0.113.10/32]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.approved-api-egress
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: destination-group == 'approved-api'
        ports: [443]
```

如果应用需要解析名称，请使用前面配置的 DNS 规则。对于动态外部服务，可使用获准的 proxy，或另行记录的商业域名策略。允许全部 RFC1918 地址并不意味着“仅限此集群”，还可能允许访问不相关的私有网络。

### 默认拒绝是整体安全设计的一部分

将作用域明确的默认拒绝基线与明确允许的必要连接、受控标签/RBAC 所有权及应用身份验证结合起来。网络分段本身并不等于完整的零信任或合规实现。强制执行前应先暂存策略并测试负向路径。

***

## 策略性能影响

策略数量本身不是容量基准。开销取决于 endpoint 数量、selector 变更、规则结构、活动流量、更新频率和所选数据面。以前声称“1,000 条策略很慢”或成本呈线性增长，都没有测量环境或原始结果作为依据。

相等匹配、集合成员匹配和标签存在性 selector 都可以利用 Calico selector 优化。不要仅为减少对象数量就合并策略并扩大访问范围。应复用维护良好的 NetworkSet、限制日志量，并在具有代表性的变更下测量收敛情况。

就绪检查、搜索“Policy sync”文本和统计 `iptables -L` 输出的行数，都不能测量规则评估延迟。请启用并抓取文档说明的 Felix metrics endpoint，检查 metric TYPE/HELP 和单位，再将规则编程/更新指标与受控工作负载关联起来：

```bash
# After enabling the documented Felix metrics endpoint through its config owner:
kubectl -n "$CALICO_NAMESPACE" port-forward "pod/$CALICO_POD" 9091:9091
```

```bash
# In another terminal while the localhost port-forward remains active:
curl --fail --silent --show-error http://127.0.0.1:9091/metrics
```

Felix metrics 默认禁用；应先由配置所有者通过 `prometheusMetricsEnabled` 启用。所选节点上的 endpoint 必须可访问。这是指标发现方式，并非已发布的性能结果。变更策略时测试正向和负向流量，并记录精确的 Calico/Kubernetes/kernel 版本、数据面、拓扑、负载和测量结果。

## 运维原则

1. 从隔离的 namespace 开始，盘点必要连接，然后暂存并执行明确规则。
2. 将标签、namespace 标签和策略编辑 RBAC 视为授权边界的一部分。
3. 每当 tier 或其顺序变更时，都要审查终止性 Allow/Pass 的影响。
4. 将主机管理/failsafe、Service 和 DNS 要求与应用规则分开处理。
5. 将网络分段与工作负载/最终用户身份验证结合；不要声称单独的 IP 规则可以阻止所有 SSRF 或满足所有合规要求。

***

## 参考资料

* [Calico NetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [GlobalNetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/globalnetworkpolicy)
* [Tier 评估](https://docs.tigera.io/calico/latest/reference/resources/tier)
* [Tier RBAC](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/rbac-tiered-policies)
* [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
* [Open Source Istio/Dikastes 应用策略](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)
* [Enterprise 域名策略](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)
* [暂存策略](https://docs.tigera.io/calico/latest/network-policy/staged-network-policies)
* [主机 failsafe](https://docs.tigera.io/calico/latest/reference/host-endpoints/failsafe)
* [Pre-DNAT](https://docs.tigera.io/calico/latest/reference/host-endpoints/pre-dnat)
* [转发主机流量](https://docs.tigera.io/calico/latest/reference/host-endpoints/forwarded)
* [KubeControllersConfiguration](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig)
* [策略日志](https://docs.tigera.io/calico/latest/network-policy/policy-rules/log-rules)
* [组件指标](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
* [Calico eBPF 协议支持](https://docs.tigera.io/calico/latest/operations/ebpf/install)
