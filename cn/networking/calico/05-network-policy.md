# 第 5 部分：Network Policy

> **支持的版本**：Calico v3.29+ / Kubernetes 1.28+ **最后更新**：February 23, 2026

## 简介

Network policy 是 Kubernetes 安全的基础，用于控制 Pod、namespace 和外部端点之间的流量。Kubernetes 提供基础的 NetworkPolicy API，而 Calico 在此基础上扩展了强大的功能，包括全局策略、分层策略评估、基于 DNS 的规则以及第 7 层过滤。

本深入讲解涵盖 Kubernetes 标准策略和 Calico 的扩展能力，提供满足企业安全需求的模式和示例。

***

## Kubernetes 标准 NetworkPolicy

### NetworkPolicy 基础

Kubernetes NetworkPolicy 是一种以 namespace 为作用域的资源，可根据标签、namespace 和 IP 块控制进出 Pod 的流量。

![对比图显示：没有 NetworkPolicy 时，每个 Pod 都可以自由访问其他所有 Pod；而 NetworkPolicy 将这种网状连通缩小为一条明确允许的路径，并阻止其余流量。](../../../assets/diagrams/rendered/en-networking-calico-05-network-policy-0.svg)

### 基本 NetworkPolicy 结构

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
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

### Kubernetes NetworkPolicy 限制

| 限制            | 描述                         | Calico 解决方案          |
| --------------------- | ----------------------------------- | ------------------------ |
| 仅限 namespace 作用域 | 无法创建集群范围的策略 | GlobalNetworkPolicy      |
| 没有策略排序    | 所有策略均以相同优先级评估      | 分层策略          |
| 没有拒绝规则         | 仅允许（隐式拒绝）          | 显式 Deny 操作    |
| 有限的 L4 过滤  | 仅支持基本端口/协议            | 端口范围、命名端口 |
| 没有 L7 过滤       | 无法按 HTTP 方法过滤       | HTTP 匹配规则         |
| 不支持 FQDN       | 无法使用域名             | DNS 策略               |
| 仅面向 Pod      | 无法保护节点                | Host endpoint           |

***

## Calico NetworkPolicy 扩展

### 扩展协议支持

Calico 除 TCP 和 UDP 外还支持其他协议：

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: extended-protocols
  namespace: default
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
          - 5000:6000  # Port range
```

### 端口范围和命名端口

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: port-examples
  namespace: default
spec:
  selector: app == 'multi-port-app'

  ingress:
    # Port range
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 8080:8090

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
          - 3000:3100
```

### 增强的选择器语法

Calico 使用比 Kubernetes 更具表达力的选择器语法：

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: selector-examples
  namespace: production
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

    # Complex expression (OR via multiple rules)
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

GlobalNetworkPolicy 应用于所有 namespace，非常适合用于集群范围的安全规则。

### GlobalNetworkPolicy 结构

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: cluster-wide-deny-egress
spec:
  # Applies to all pods (empty selector)
  selector: all()

  # Order determines priority (lower = higher priority)
  order: 1000

  types:
    - Egress

  egress:
    # Block access to metadata service
    - action: Deny
      destination:
        nets:
          - 169.254.169.254/32

    # Block access to internal DNS except kube-dns
    - action: Deny
      protocol: UDP
      destination:
        ports:
          - 53
        notSelector: k8s-app == 'kube-dns'
```

### 常见 GlobalNetworkPolicy 模式

**默认拒绝所有流量：**

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-all
spec:
  selector: all()
  order: 10000  # Lowest priority
  types:
    - Ingress
    - Egress

  # Empty rules = deny all
  ingress: []
  egress: []
```

**允许必要服务：**

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-essential-services
spec:
  selector: all()
  order: 100
  types:
    - Egress

  egress:
    # Allow DNS
    - action: Allow
      protocol: UDP
      destination:
        selector: k8s-app == 'kube-dns'
        ports:
          - 53

    # Allow Kubernetes API
    - action: Allow
      protocol: TCP
      destination:
        nets:
          - 10.96.0.1/32  # ClusterIP of kubernetes service
        ports:
          - 443
```

**阻止敏感 namespace：**

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: protect-kube-system
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
  order: 50
  types:
    - Ingress

  ingress:
    # Only allow from pods with explicit access
    - action: Allow
      source:
        selector: has(kube-system-access)

    # Allow from kube-system itself
    - action: Allow
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'

    # Deny everything else (implicit)
```

***

## NetworkSet 和 GlobalNetworkSet

NetworkSet 将 IP 地址分组，以便跨策略复用。

### NetworkSet（以 namespace 为作用域）

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: corporate-networks
  namespace: default
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
  namespace: default
spec:
  selector: app == 'internal-app'

  ingress:
    - action: Allow
      source:
        selector: network-type == 'corporate'  # References NetworkSet by label
```

### GlobalNetworkSet（以集群为作用域）

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
  name: blocked-countries
  labels:
    network-group: blocked
spec:
  nets:
    # Country IP ranges to block
    - 1.2.3.0/24
    - 5.6.7.0/24

---
# Reference in GlobalNetworkPolicy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: external-access-control
spec:
  selector: has(external-facing)
  order: 200
  types:
    - Ingress

  ingress:
    # Allow trusted external
    - action: Allow
      source:
        selector: network-group == 'external-trusted'

    # Block known bad actors
    - action: Deny
      source:
        selector: network-group == 'blocked'
```

***

## 分层策略

![Calico Network Policy 层级评估：数据包依次经过 Security (100)、Platform (200)、Application (500) 和 Default 层级；任一层级中匹配 Allow 或 Deny 会立即结束评估，Pass 将交由下一层级，而没有匹配时则应用 endpoint profile 的默认操作。](../../.gitbook/assets/en-networking-calico-05-network-policy-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-05-network-policy-2.html)

层级提供分层的策略评估，使平台、安全和应用团队能够分离关注点。

### 策略评估顺序

![流程图显示流量依次经过 Security、Platform 和 Application 层级，每个层级都可以拒绝数据包、允许数据包，或将其交给下一层级；若没有层级匹配，则最终隐式拒绝。](../../../assets/diagrams/rendered/en-networking-calico-05-network-policy-1.svg)

### 创建层级

```yaml
# Security team tier (highest priority)
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100

---
# Platform team tier
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200

---
# Application team tier
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 500

---
# Default tier (lowest priority, auto-created)
# order: 1000
```

### 分层策略示例

```yaml
# Security tier: Block known threats
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-threats
spec:
  tier: security
  order: 100
  selector: all()
  types:
    - Ingress
    - Egress

  ingress:
    - action: Deny
      source:
        selector: network-group == 'threat-intel'

  egress:
    - action: Deny
      destination:
        selector: network-group == 'malware-c2'

    # Pass to next tier for further evaluation
    - action: Pass

---
# Platform tier: Enforce baseline connectivity
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.baseline
spec:
  tier: platform
  order: 100
  selector: all()
  types:
    - Egress

  egress:
    # Allow DNS
    - action: Allow
      protocol: UDP
      destination:
        selector: k8s-app == 'kube-dns'
        ports:
          - 53

    # Allow Kubernetes API
    - action: Allow
      protocol: TCP
      destination:
        services:
          name: kubernetes
          namespace: default

    # Pass to application tier
    - action: Pass

---
# Application tier: Team-specific policies
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: application.frontend-rules
  namespace: production
spec:
  tier: application
  order: 100
  selector: app == 'frontend'
  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      source:
        selector: app == 'ingress-nginx'

  egress:
    - action: Allow
      destination:
        selector: app == 'backend'
        ports:
          - 8080
```

### 层级 RBAC 集成

```yaml
# ClusterRole for security team
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: security-team-policy-admin
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["globalnetworkpolicies", "tiers"]
    verbs: ["*"]
    # Can only manage policies in security tier
    resourceNames: ["security.*"]

---
# ClusterRole for application teams
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: app-team-policy-admin
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["networkpolicies"]
    verbs: ["*"]
  - apiGroups: ["projectcalico.org"]
    resources: ["tiers"]
    verbs: ["get", "list"]
    resourceNames: ["application"]
```

***

## 基于 FQDN 的 Egress 策略

Calico 可以根据域名过滤 Egress 流量，适用于控制对外部服务的访问。

### DNS 策略配置

首先，在 Felix 中启用 DNS 策略：

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  dnsTrustedServers:
    - k8s-service:kube-system/kube-dns
  policySyncPathPrefix: /var/run/nodeagent
```

### FQDN Egress 规则

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-specific-domains
spec:
  selector: app == 'external-api-client'
  order: 500
  types:
    - Egress

  egress:
    # Allow specific domains
    - action: Allow
      destination:
        domains:
          - api.github.com
          - "*.amazonaws.com"
          - registry.npmjs.org
      protocol: TCP
      destination:
        ports:
          - 443

    # Allow Google APIs
    - action: Allow
      destination:
        domains:
          - "*.googleapis.com"
          - "*.google.com"
      protocol: TCP
      destination:
        ports:
          - 443

    # Deny all other external
    - action: Deny
      destination:
        notNets:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16
```

### 通配符域名模式

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: dns-wildcards
spec:
  selector: all()
  egress:
    # Single wildcard - matches any subdomain
    - action: Allow
      destination:
        domains:
          - "*.example.com"     # Matches api.example.com, www.example.com

    # Does NOT match
    # example.com (no subdomain)
    # deep.sub.example.com (multiple levels)
```

***

## HTTP 方法过滤（第 7 层）

Calico Enterprise 和 Calico Cloud 支持用于 HTTP 流量的第 7 层策略。

### HTTP 匹配规则

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: l7-http-policy
spec:
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

    # Allow full access for admin clients
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
  namespace: production
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

## Host Endpoint 保护

Host endpoint 保护进出节点自身的流量，而不仅是 Pod。

### 启用 Host Endpoint

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  defaultEndpointToHostAction: Drop  # or Accept, Return
```

### Host Endpoint 定义

```yaml
apiVersion: projectcalico.org/v3
kind: HostEndpoint
metadata:
  name: node1-eth0
  labels:
    host: node1
    interface: external
spec:
  interfaceName: eth0
  node: node1
  expectedIPs:
    - 10.0.1.10

---
# Policy for host endpoints
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: host-ssh-policy
spec:
  selector: interface == 'external'
  order: 100
  types:
    - Ingress

  ingress:
    # Allow SSH from bastion
    - action: Allow
      protocol: TCP
      source:
        nets:
          - 10.0.0.100/32  # Bastion IP
      destination:
        ports:
          - 22

    # Allow kubelet API from control plane
    - action: Allow
      protocol: TCP
      source:
        selector: has(control-plane)
      destination:
        ports:
          - 10250

    # Allow node exporter metrics
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'monitoring'
        selector: app == 'prometheus'
      destination:
        ports:
          - 9100
```

### 自动 Host Endpoint

为所有节点自动创建 Host endpoint：

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  defaultEndpointToHostAction: Drop

---
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    hostPorts: Enabled  # Creates auto host endpoints
```

***

## DoNotTrack 和 PreDNAT 策略

### DoNotTrack 策略

DoNotTrack 策略会绕过连接跟踪，适用于高吞吐量场景：

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: high-throughput-no-track
spec:
  selector: app == 'load-balancer'
  order: 10
  types:
    - Ingress
    - Egress

  doNotTrack: true
  applyOnForward: true

  ingress:
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 80
          - 443

  egress:
    - action: Allow
```

### PreDNAT 策略

PreDNAT 策略在目标 NAT 之前应用，适用于控制 NodePort 访问：

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: restrict-nodeport-access
spec:
  selector: has(kubernetes.io/os)  # Applies to host endpoints
  order: 100
  types:
    - Ingress

  preDNAT: true
  applyOnForward: true

  ingress:
    # Allow NodePort access only from trusted networks
    - action: Allow
      protocol: TCP
      source:
        nets:
          - 10.0.0.0/8
      destination:
        ports:
          - 30000:32767  # NodePort range

    # Deny NodePort from everywhere else
    - action: Deny
      protocol: TCP
      destination:
        ports:
          - 30000:32767
```

***

## 策略调试

### 使用 calicoctl

```bash
# List all policies
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy

# Get policy details
calicoctl get networkpolicy my-policy -n default -o yaml

# Describe endpoints affected by a policy
calicoctl get workloadendpoint -o wide

# Check policy selectors
calicoctl get networkpolicy -o yaml | grep -A5 selector
```

### 检查 iptables 规则

```bash
# View Calico chains
iptables -L -n -v | grep -i cali

# View filter table
iptables -t filter -L -n -v

# View NAT table
iptables -t nat -L -n -v

# Count packets by rule
iptables -L cali-fw-xxxxx -n -v

# Watch traffic in real-time
watch -n 1 'iptables -L cali-fw-xxxxx -n -v'
```

### Felix 日志

```bash
# View Felix logs
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | grep -i policy

# Increase log verbosity
calicoctl patch felixconfiguration default -p '{"spec":{"logSeverityScreen":"Debug"}}'

# Check policy sync status
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- calico-node -felix-ready
```

### 策略评估流程调试

```bash
# Get workload endpoint details
calicoctl get workloadendpoint -n default --selector='app==web' -o yaml

# Check which policies apply
calicoctl get networkpolicy -A -o yaml | grep -B20 "app.*web"

# Test connectivity
kubectl exec -it test-pod -- nc -zv target-pod 8080
```

***

## 常见策略模式库

### 微服务模式

```yaml
# Frontend -> Backend -> Database
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: production
spec:
  selector: app == 'frontend'
  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      source:
        selector: app == 'ingress-nginx'

  egress:
    - action: Allow
      destination:
        selector: app == 'backend'
        ports:
          - 8080

---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: production
spec:
  selector: app == 'backend'
  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      source:
        selector: app == 'frontend'
        ports:
          - 8080

  egress:
    - action: Allow
      destination:
        selector: app == 'database'
        ports:
          - 5432

---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  selector: app == 'database'
  types:
    - Ingress

  ingress:
    - action: Allow
      source:
        selector: app == 'backend'
        ports:
          - 5432
```

### 多租户隔离

```yaml
# Each tenant namespace is fully isolated
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: tenant-isolation
spec:
  namespaceSelector: has(tenant)
  order: 500
  types:
    - Ingress
    - Egress

  ingress:
    # Allow same-tenant traffic
    - action: Allow
      source:
        namespaceSelector: tenant == "$(namespace.tenant)"

  egress:
    # Allow same-tenant traffic
    - action: Allow
      destination:
        namespaceSelector: tenant == "$(namespace.tenant)"

    # Allow DNS
    - action: Allow
      protocol: UDP
      destination:
        selector: k8s-app == 'kube-dns'
        ports:
          - 53
```

### 零信任模式

```yaml
# Default deny everything
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: zero-trust-default-deny
spec:
  selector: all()
  order: 10000
  types:
    - Ingress
    - Egress
  ingress: []
  egress: []

---
# Explicit allow for each service
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: zero-trust-api-server
  namespace: production
spec:
  selector: app == 'api-server'
  order: 100
  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      source:
        selector: app == 'api-gateway'
        namespaceSelector: kubernetes.io/metadata.name == 'production'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      destination:
        selector: app == 'database'
        namespaceSelector: kubernetes.io/metadata.name == 'production'
        ports:
          - 5432

    # Allow DNS
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports:
          - 53
```

### Egress 控制模式

```yaml
# Control outbound internet access
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-internet-control
spec:
  selector: has(internet-access)
  order: 300
  types:
    - Egress

  egress:
    # Allow approved external services
    - action: Allow
      destination:
        domains:
          - "*.amazonaws.com"
          - api.github.com
          - registry.npmjs.org
      protocol: TCP
      destination:
        ports:
          - 443

    # Allow internal traffic
    - action: Allow
      destination:
        nets:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16

---
# Block internet for unlabeled pods
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-internet-deny
spec:
  selector: "!has(internet-access)"
  order: 400
  types:
    - Egress

  egress:
    # Allow internal only
    - action: Allow
      destination:
        nets:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16

    # Deny external
    - action: Deny
```

### Namespace 隔离模式

```yaml
# Isolate namespaces by default
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: namespace-isolation
spec:
  namespaceSelector: has(kubernetes.io/metadata.name)
  order: 800
  types:
    - Ingress

  ingress:
    # Allow same namespace
    - action: Allow
      source:
        namespaceSelector: kubernetes.io/metadata.name == "$(namespace.name)"

    # Allow monitoring namespace
    - action: Allow
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'monitoring'
        selector: app in {'prometheus', 'grafana'}

    # Allow ingress namespace
    - action: Allow
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'ingress-nginx'
```

***

## 策略性能影响

### 性能注意事项

| 因素              | 影响                  | 缓解措施                              |
| ------------------- | ----------------------- | --------------------------------------- |
| 策略数量  | 规则线性评估  | 使用分层策略，优化选择器 |
| 选择器复杂度 | 匹配时间增加 | 使用简单的标签匹配                |
| IP 集合大小         | 内存使用量            | 聚合 IP 范围                     |
| 日志频率       | CPU 和存储         | 对高流量使用采样            |
| 连接跟踪 | 有状态连接的内存     | 对无状态流量使用 DoNotTrack                |

### 优化建议

1. **使用分层策略**：先评估拒绝规则
2. **最小化选择器复杂度**：优先使用相等比较而非集合操作
3. **聚合 IP 范围**：使用 CIDR 块代替单独的 IP
4. **使用 GlobalNetworkSet**：跨策略复用 IP 组
5. **启用策略缓存**：近期 Calico 版本默认启用

### 对策略性能进行基准测试

```bash
# Measure rule evaluation time
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- \
  calico-node -felix-ready

# Check dataplane programming time
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | \
  grep "Policy sync"

# Monitor iptables rule count
iptables -L -n | wc -l
```

***

## 最佳实践总结

### 设计原则

1. **从默认拒绝开始**：将所需流量列入允许名单
2. **使用最小权限**：仅允许必要的端口和协议
3. **对策略分层**：Security -> Platform -> Application
4. **一致地使用标签**：使用标准标签作为策略目标
5. **记录策略**：加入解释意图的注释

### 运维建议

1. **先在 staging 中测试**：在 production 之前验证策略
2. **使用审计模式**：在强制执行新策略前先记录日志
3. **监控策略命中次数**：识别未使用的规则
4. **定期审查策略**：移除过时规则
5. **自动化策略部署**：使用 GitOps 管理策略

### 安全建议

1. **阻止 metadata service**：防止 SSRF 攻击
2. **控制 Egress**：将外部访问限制为已批准的目标
3. **保护 control plane**：限制对 kube-system 的访问
4. **启用日志记录**：审计被拒绝的连接
5. **使用 FQDN 策略**：按名称控制对外部服务的访问

***

## 参考资料

* [Calico Network Policy 文档](https://docs.tigera.io/calico/latest/network-policy/)
* [Kubernetes Network Policy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Calico 策略教程](https://docs.tigera.io/calico/latest/network-policy/get-started/calico-policy/calico-policy-tutorial)
* [Tigera 策略最佳实践](https://docs.tigera.io/calico/latest/network-policy/policy-best-practices)
