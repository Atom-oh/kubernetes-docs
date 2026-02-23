# Part 5: Calico Network Policy Deep Dive
> **Supported Versions**: Calico v3.29+ / Kubernetes 1.28+
> **Last Updated**: February 22, 2025

## Introduction

Network policies are fundamental to Kubernetes security, controlling traffic flow between pods, namespaces, and external endpoints. While Kubernetes provides a basic NetworkPolicy API, Calico extends this with powerful features including global policies, tiered policy evaluation, DNS-based rules, and Layer 7 filtering.

This deep dive covers both Kubernetes standard policies and Calico's extended capabilities, providing patterns and examples for enterprise security requirements.

---

## Kubernetes Standard NetworkPolicy

### NetworkPolicy Fundamentals

Kubernetes NetworkPolicy is a namespace-scoped resource that controls traffic to and from pods based on labels, namespaces, and IP blocks.

```mermaid
flowchart LR
    subgraph "Without NetworkPolicy"
        A1[Pod A] <--> B1[Pod B]
        A1 <--> C1[Pod C]
        B1 <--> C1
    end

    subgraph "With NetworkPolicy"
        A2[Pod A] --> B2[Pod B]
        A2 -.X.-> C2[Pod C]
        B2 -.X.-> A2
    end
```

### Basic NetworkPolicy Structure

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

### Kubernetes NetworkPolicy Limitations

| Limitation | Description | Calico Solution |
|------------|-------------|-----------------|
| Namespace-scoped only | Cannot create cluster-wide policies | GlobalNetworkPolicy |
| No policy ordering | All policies evaluated equally | Tiered policies |
| No deny rules | Only allow (implicit deny) | Explicit Deny actions |
| Limited L4 filtering | Basic port/protocol only | Port ranges, named ports |
| No L7 filtering | Cannot filter by HTTP methods | HTTP match rules |
| No FQDN support | Cannot use domain names | DNS policy |
| Pod-centric only | Cannot protect nodes | Host endpoints |

---

## Calico NetworkPolicy Extensions

### Extended Protocol Support

Calico supports additional protocols beyond TCP and UDP:

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

### Port Ranges and Named Ports

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

### Enhanced Selector Syntax

Calico uses a more expressive selector syntax than Kubernetes:

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

---

## GlobalNetworkPolicy

GlobalNetworkPolicy applies across all namespaces, ideal for cluster-wide security rules.

### GlobalNetworkPolicy Structure

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

### Common GlobalNetworkPolicy Patterns

**Default Deny All Traffic:**

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

**Allow Essential Services:**

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

**Block Sensitive Namespaces:**

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

---

## NetworkSet and GlobalNetworkSet

NetworkSets group IP addresses for reuse across policies.

### NetworkSet (Namespace-scoped)

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

### GlobalNetworkSet (Cluster-scoped)

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

---

## Tiered Policies

![Calico Network Policy Tier Evaluation](../../../assets/calico_network_policy_tiers.png)

Tiers provide hierarchical policy evaluation, enabling separation of concerns between platform, security, and application teams.

### Policy Evaluation Order

```mermaid
flowchart TD
    T[Traffic] --> SEC[Security Tier<br/>Order: 100]
    SEC -->|Pass| PLAT[Platform Tier<br/>Order: 200]
    PLAT -->|Pass| APP[Application Tier<br/>Order: 500]
    APP -->|Pass| DEF[Default Tier<br/>Order: 1000]
    DEF -->|No Match| DENY[Implicit Deny]

    SEC -->|Deny| DROP1[Drop Packet]
    PLAT -->|Deny| DROP2[Drop Packet]
    APP -->|Deny| DROP3[Drop Packet]

    SEC -->|Allow| ALLOW1[Allow Packet]
    PLAT -->|Allow| ALLOW2[Allow Packet]
    APP -->|Allow| ALLOW3[Allow Packet]
```

### Creating Tiers

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

### Tiered Policy Example

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

### Tier RBAC Integration

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

---

## FQDN-Based Egress Policy

Calico can filter egress traffic based on domain names, useful for controlling access to external services.

### DNS Policy Configuration

First, enable DNS policy in Felix:

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

### FQDN Egress Rules

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

### Wildcard Domain Patterns

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

---

## HTTP Method Filtering (Layer 7)

Calico Enterprise and Calico Cloud support Layer 7 policy for HTTP traffic.

### HTTP Match Rules

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

### Path-Based Filtering

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

---

## Host Endpoint Protection

Host endpoints protect traffic to/from the node itself, not just pods.

### Enabling Host Endpoints

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  defaultEndpointToHostAction: Drop  # or Accept, Return
```

### Host Endpoint Definition

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

### Auto Host Endpoints

Automatically create host endpoints for all nodes:

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

---

## DoNotTrack and PreDNAT Policies

### DoNotTrack Policies

DoNotTrack policies bypass connection tracking, useful for high-throughput scenarios:

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

### PreDNAT Policies

PreDNAT policies apply before destination NAT, useful for controlling NodePort access:

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

---

## Policy Debugging

### Using calicoctl

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

### Checking iptables Rules

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

### Felix Logs

```bash
# View Felix logs
kubectl logs -n kube-system -l k8s-app=calico-node -c calico-node | grep -i policy

# Increase log verbosity
calicoctl patch felixconfiguration default -p '{"spec":{"logSeverityScreen":"Debug"}}'

# Check policy sync status
kubectl exec -n kube-system calico-node-xxxxx -c calico-node -- calico-node -felix-ready
```

### Policy Evaluation Flow Debug

```bash
# Get workload endpoint details
calicoctl get workloadendpoint -n default --selector='app==web' -o yaml

# Check which policies apply
calicoctl get networkpolicy -A -o yaml | grep -B20 "app.*web"

# Test connectivity
kubectl exec -it test-pod -- nc -zv target-pod 8080
```

---

## Common Policy Patterns Library

### Microservices Pattern

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

### Multi-Tenant Isolation

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

### Zero Trust Pattern

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

### Egress Control Pattern

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

### Namespace Isolation Pattern

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

---

## Policy Performance Impact

### Performance Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Number of policies | Linear rule evaluation | Use tiered policies, optimize selectors |
| Selector complexity | Increased matching time | Use simple label matches |
| IP set size | Memory usage | Aggregate IP ranges |
| Log frequency | CPU and storage | Use sampling for high-volume |
| Connection tracking | Memory for stateful | DoNotTrack for stateless |

### Optimization Tips

1. **Use tiered policies**: Evaluate deny rules first
2. **Minimize selector complexity**: Prefer equality over set operations
3. **Aggregate IP ranges**: Use CIDR blocks instead of individual IPs
4. **Use GlobalNetworkSet**: Reuse IP groups across policies
5. **Enable policy caching**: Default in recent Calico versions

### Benchmarking Policy Performance

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

---

## Best Practices Summary

### Design Principles

1. **Start with default deny**: Whitelist required traffic
2. **Use least privilege**: Only allow necessary ports and protocols
3. **Layer your policies**: Security -> Platform -> Application
4. **Label consistently**: Use standard labels for policy targeting
5. **Document policies**: Include comments explaining intent

### Operational Recommendations

1. **Test in staging first**: Validate policies before production
2. **Use audit mode**: Log before enforcing new policies
3. **Monitor policy hit counts**: Identify unused rules
4. **Review policies regularly**: Remove stale rules
5. **Automate policy deployment**: Use GitOps for policy management

### Security Recommendations

1. **Block metadata service**: Prevent SSRF attacks
2. **Control egress**: Limit external access to approved destinations
3. **Protect control plane**: Restrict access to kube-system
4. **Enable logging**: Audit denied connections
5. **Use FQDN policies**: Control access to external services by name

---

## References

- [Calico Network Policy Documentation](https://docs.tigera.io/calico/latest/network-policy/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Calico Policy Tutorial](https://docs.tigera.io/calico/latest/network-policy/get-started/calico-policy/calico-policy-tutorial)
- [Tigera Policy Best Practices](https://docs.tigera.io/calico/latest/network-policy/policy-best-practices)
