# Network Policies

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 22, 2026

Kubernetes Network Policies are firewall rules that control traffic between Pods. This document covers everything from basic NetworkPolicy to Cilium and Calico extensions.

## Table of Contents

1. [Network Policy Overview](#network-policy-overview)
2. [Kubernetes NetworkPolicy Spec](#kubernetes-networkpolicy-spec)
3. [Default Deny Policies](#default-deny-policies)
4. [Policy Order and Evaluation](#policy-order-and-evaluation)
5. [Cilium Network Policy Extensions](#cilium-network-policy-extensions)
6. [Calico Network Policy Extensions](#calico-network-policy-extensions)
7. [Design Patterns](#design-patterns)
8. [Testing Network Policies](#testing-network-policies)
9. [EKS Considerations](#eks-considerations)
10. [Visualization Tools](#visualization-tools)

---

## Network Policy Overview

### What is a Network Policy?

Network Policies act as Pod-level firewalls in Kubernetes. By default, Kubernetes Pods can communicate freely with all other Pods, but Network Policies allow you to restrict this traffic.

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

### Network Policy Characteristics

| Property | Description |
|----------|-------------|
| **Namespace Scoped** | NetworkPolicy applies to resources within a namespace |
| **Additive** | When multiple policies exist, the union of all policies applies |
| **Selective Application** | Target Pods specified via podSelector |
| **Directional Control** | Separate control for Ingress (inbound) and Egress (outbound) |
| **CNI Dependent** | CNI plugin must support NetworkPolicy |

### CNI NetworkPolicy Support

| CNI | Basic NetworkPolicy | Extensions | L7 Policy |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet | ✓ (Enterprise) |
| **Weave Net** | ✓ | Limited | ✗ |
| **Flannel** | ✗ | ✗ | ✗ |
| **Amazon VPC CNI** | ✗ (requires separate installation) | Security Groups for Pods | ✗ |

---

## Kubernetes NetworkPolicy Spec

### Basic Structure

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

Selects the Pods to which the policy applies.

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

# Apply to all Pods (empty selector)
spec:
  podSelector: {}

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

Selects Pods from other namespaces.

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
              name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              name: production
          podSelector:
            matchLabels:
              role: frontend
```

**Note:** AND vs OR distinction when using `namespaceSelector` and `podSelector` together:

```yaml
# OR condition (two separate rules)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

Allow or block specific IP ranges.

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
        # Allow external load balancer IP range
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

Specify allowed ports and protocols.

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

## Default Deny Policies

### Default Deny Ingress

Default policy that blocks all inbound traffic:

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

### Default Deny Egress

Default policy that blocks all outbound traffic:

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

### Full Deny (Ingress + Egress)

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

### Default Deny with DNS Allowed

Common pattern to allow DNS lookups when blocking egress:

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
    # Allow kube-dns/CoreDNS access
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

### Zero Trust Architecture Default Policy

```yaml
---
# 1. Default deny all traffic
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
---
# 2. Allow DNS only
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. Explicitly allow only required communication
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
```

---

## Policy Order and Evaluation

### Policy Evaluation Rules

NetworkPolicy is evaluated according to the following rules:

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

### Combining Multiple Policies

When multiple NetworkPolicies apply to the same Pod, all policy rules are combined (Union):

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
              name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**Result:** The `app: api` Pod allows both frontend Pod access on 8080 and monitoring namespace access on 8080 and 9090.

### Policy Evaluation Order

NetworkPolicy has no priority concept. All policies are treated equally:

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

## Cilium Network Policy Extensions

### CiliumNetworkPolicy

Cilium extends basic NetworkPolicy with more powerful features.

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

### L7 HTTP Policy

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
            - port: "8080"
              protocol: TCP
          rules:
            http:
              # Allow only GET requests
              - method: GET
                path: "/api/v1/products"

              # Allow specific path patterns
              - method: GET
                path: "/api/v1/products/[0-9]+"

              # POST only allowed with specific headers
              - method: POST
                path: "/api/v1/orders"
                headers:
                  - "X-API-Key: .*"
                  - "Content-Type: application/json"

              # PUT/DELETE only for admin
              - method: "PUT|DELETE"
                path: "/api/v1/.*"
                headers:
                  - "X-User-Role: admin"
```

### L7 Kafka Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-policy
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka

  ingress:
    - fromEndpoints:
        - matchLabels:
            app: producer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # Allow produce only to specific topics
              - role: produce
                topic: "orders"
              - role: produce
                topic: "events"

    - fromEndpoints:
        - matchLabels:
            app: consumer
      toPorts:
        - ports:
            - port: "9092"
              protocol: TCP
          rules:
            kafka:
              # Allow consume only from specific topics
              - role: consume
                topic: "orders"
                clientID: "order-processor-.*"
```

### L7 DNS Policy

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
    # Allow DNS lookups
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s-app: kube-dns
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
          rules:
            dns:
              # Allow only specific domain lookups
              - matchPattern: "*.amazonaws.com"
              - matchPattern: "api.example.com"
              - matchName: "database.production.svc.cluster.local"

    # Allow connections to looked up domains
    - toFQDNs:
        - matchPattern: "*.amazonaws.com"
        - matchName: "api.example.com"
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP
```

### CiliumClusterwideNetworkPolicy

Cluster-wide policy:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: cluster-default-deny
spec:
  # Apply to all endpoints
  endpointSelector: {}

  ingress:
    - fromEntities:
        - cluster  # Allow only internal cluster traffic

  egress:
    - toEntities:
        - cluster
        - world  # Allow external traffic (if needed)
    - toEndpoints:
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
      toPorts:
        - ports:
            - port: "53"
              protocol: UDP
```

### Cilium Entity-Based Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: entity-based-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web

  ingress:
    - fromEntities:
        - world      # Outside cluster
        - cluster    # Inside cluster

  egress:
    - toEntities:
        - world      # Internet
      toPorts:
        - ports:
            - port: "443"
              protocol: TCP

    - toEntities:
        - host       # Node itself
      toPorts:
        - ports:
            - port: "10250"  # kubelet
              protocol: TCP

    - toEntities:
        - kube-apiserver  # API server
```

---

## Calico Network Policy Extensions

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

Calico policy that applies cluster-wide:

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-all
spec:
  # Full selector instead of namespace
  selector: all()

  order: 1000  # Low priority (other policies evaluated first)

  types:
    - Ingress
    - Egress

  # No rules = block all traffic

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-dns
spec:
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

Define reusable IP sets:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
spec:
  nets:
    - 203.0.113.0/24     # External API servers
    - 198.51.100.10/32   # Specific service

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
spec:
  nets:
    - 192.0.2.0/24       # IP range to block
    - 10.0.0.5/32        # Specific blocked IP
```

Using NetworkSet:

```yaml
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
      destination:
        selector: projectcalico.org/name == 'external-apis'
        namespaceSelector: projectcalico.org/name == 'production'
```

### Tier-Based Policies

Hierarchical policies supported in Calico Enterprise:

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200

---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300

---
# Security Tier policy (evaluated first)
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  types:
    - Ingress
  ingress:
    - action: Deny
      source:
        selector: global(name == 'blocked-ips')

---
# Platform Tier policy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  types:
    - Egress
  egress:
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - 53
```

---

## Design Patterns

### Microsegmentation

Isolate each service individually:

```yaml
---
# 1. Namespace default deny
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
---
# 2. Allow DNS
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
      ports:
        - protocol: UDP
          port: 53
---
# 3. Frontend -> API
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
# 4. API -> Database
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
# 5. API external access (if needed)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-external-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### Namespace Isolation

```yaml
---
# 1. Set namespace labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
# 2. Allow communication only within same team
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              team: team-a
---
# 3. Allow access to specific services from other teams
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
              shared-services: "true"
          podSelector:
            matchLabels:
              exposed: "true"
```

### Database Protection

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
    # Allow access only from application
    - from:
        - namespaceSelector:
            matchLabels:
              environment: production
          podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
    # Allow monitoring access
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9187  # postgres_exporter
  egress:
    # Access other DB instances for replication
    - to:
        - podSelector:
            matchLabels:
              app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### 3-Tier Architecture Policy

```yaml
---
# Web Tier
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
    # Allow access from external (Ingress Controller)
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80
  egress:
    # Communicate only with App Tier
    - to:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 8080
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# App Tier
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
    # Allow access only from Web Tier
    - from:
        - podSelector:
            matchLabels:
              tier: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Communicate only with Data Tier
    - to:
        - podSelector:
            matchLabels:
              tier: data
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# Data Tier
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
    # Allow access only from App Tier
    - from:
        - podSelector:
            matchLabels:
              tier: app
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
  egress:
    # Replication communication within same tier
    - to:
        - podSelector:
            matchLabels:
              tier: data
```

---

## Testing Network Policies

### Testing with netshoot

```bash
# Deploy netshoot Pod
kubectl run netshoot --image=nicolaka/netshoot -it --rm -- /bin/bash

# Connection tests
curl -v http://api-service:8080/health
nc -zv database-service 5432
nslookup api-service.production.svc.cluster.local

# TCP connection test
curl --connect-timeout 5 http://target-service:8080
```

### Testing with kubectl exec

```bash
# Test connection from Pod to another service
kubectl exec -it frontend-pod -- curl -v http://api-service:8080

# DNS verification
kubectl exec -it frontend-pod -- nslookup api-service

# Port scan
kubectl exec -it frontend-pod -- nc -zv api-service 8080
```

### Cilium Connectivity Test

```bash
# Run Cilium connectivity test
cilium connectivity test

# Run specific tests only
cilium connectivity test --test pod-to-pod
cilium connectivity test --test pod-to-service

# Policy tests
cilium connectivity test --test to-entities-world
cilium connectivity test --test to-cidr-external
```

### Automated Test Script

```bash
#!/bin/bash
# network-policy-test.sh

echo "=== Network Policy Test Suite ==="

# Create test Pod
kubectl run test-pod --image=nicolaka/netshoot --restart=Never --labels="app=test" -- sleep 3600

# Wait for Pod to be ready
kubectl wait --for=condition=Ready pod/test-pod --timeout=60s

# Run test cases
run_test() {
    local name=$1
    local command=$2
    local expected=$3

    echo -n "Testing: $name... "
    result=$(kubectl exec test-pod -- timeout 5 sh -c "$command" 2>&1)

    if [[ "$expected" == "success" && $? -eq 0 ]]; then
        echo "PASS"
    elif [[ "$expected" == "fail" && $? -ne 0 ]]; then
        echo "PASS (correctly blocked)"
    else
        echo "FAIL"
        echo "  Result: $result"
    fi
}

# Test cases
run_test "DNS resolution" "nslookup kubernetes.default" "success"
run_test "API server access" "curl -k https://kubernetes.default/healthz" "success"
run_test "External access blocked" "curl -s --connect-timeout 3 http://example.com" "fail"
run_test "Database access" "nc -zv database-service 5432" "success"

# Cleanup
kubectl delete pod test-pod --force --grace-period=0
```

---

## EKS Considerations

### Amazon VPC CNI and NetworkPolicy

Amazon VPC CNI does not support NetworkPolicy by default. Additional configuration is required to use NetworkPolicy:

```bash
# Option 1: Enable VPC CNI NetworkPolicy support (v1.14.0+)
kubectl set env daemonset aws-node -n kube-system ENABLE_NETWORK_POLICY=true

# Check VPC CNI version
kubectl describe daemonset aws-node -n kube-system | grep Image

# Option 2: Install Calico policy engine separately
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-operator.yaml
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/calico-crs.yaml
```

### Security Groups for Pods

In EKS, you can apply Security Groups directly to Pods:

```yaml
# SecurityGroupPolicy definition
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
      - sg-0123456789abcdef0  # Database Security Group
---
# Pod automatically gets Security Group applied
apiVersion: v1
kind: Pod
metadata:
  name: database-pod
  namespace: production
  labels:
    app: database
spec:
  containers:
    - name: postgres
      image: postgres:15
```

Security Group example configuration:

```hcl
# Define Security Group with Terraform
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_pods.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### Combining VPC-Level Controls with NetworkPolicy

```yaml
# NetworkPolicy (Pod level)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
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
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Security Group (VPC level)
# Provides additional network isolation
resource "aws_security_group" "database_pods" {
  # ... (see example above)
}

# NACL (Subnet level)
# Controls traffic between subnets
resource "aws_network_acl_rule" "database_subnet" {
  network_acl_id = aws_network_acl.database.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/16"
  from_port      = 5432
  to_port        = 5432
}
```

### Using Cilium on EKS

```bash
# Remove VPC CNI (optional)
kubectl delete daemonset aws-node -n kube-system

# Install Cilium
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.15.0 \
    --namespace kube-system \
    --set eni.enabled=true \
    --set ipam.mode=eni \
    --set egressMasqueradeInterfaces=eth0 \
    --set routingMode=native
```

---

## Visualization Tools

### Cilium Network Policy Editor

Cilium provides a web-based policy editor:

```bash
# Enable Cilium Hubble UI
cilium hubble enable --ui

# Access Hubble UI
cilium hubble ui

# Or port forward
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

### Cilium Policy Verdict Check

```bash
# Check real-time policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### Calico Enterprise UI

Calico Enterprise provides a policy visualization UI:

```bash
# Access Calico Enterprise dashboard
kubectl port-forward -n calico-system svc/cnx-manager 9443:443
```

### Network Policy Visualization Tools

```bash
# Install kubectl-np-viewer
kubectl krew install np-viewer

# Visualize policies
kubectl np-viewer -n production

# Check policies for specific Pod
kubectl np-viewer -n production --pod api-server
```

### Security Testing with Kube-hunter

```bash
# Cluster security scan
kubectl run kube-hunter --image=aquasec/kube-hunter --restart=Never -- --pod

# Check results
kubectl logs kube-hunter
```

---

## Best Practices

### 1. Apply Default Deny Policy

```yaml
# Apply to all production namespaces
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

### 2. Principle of Least Privilege

Explicitly allow only required traffic:

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
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

### 3. Document Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    last-reviewed: "2026-02-21"
spec:
  # ...
```

### 4. Regular Policy Audits

```bash
#!/bin/bash
# audit-network-policies.sh

echo "=== Network Policy Audit ==="

# Find namespaces without policies
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    policies=$(kubectl get networkpolicies -n "$ns" --no-headers 2>/dev/null | wc -l)
    if [[ $policies -eq 0 ]]; then
        echo "WARNING: No NetworkPolicy in namespace: $ns"
    fi
done

# Check for default deny policies
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    deny_policy=$(kubectl get networkpolicies -n "$ns" -o json | jq -r '.items[] | select(.spec.podSelector == {} and .spec.ingress == null) | .metadata.name')
    if [[ -z "$deny_policy" ]]; then
        echo "INFO: No default-deny policy in namespace: $ns"
    fi
done
```

---

## Summary

Kubernetes Network Policies are a core security mechanism for controlling Pod communication within clusters:

1. **Basic NetworkPolicy**: Namespace-scoped, supports podSelector/namespaceSelector/ipBlock
2. **Cilium Extensions**: L7 policies, DNS FQDN-based policies, cluster-wide policies
3. **Calico Extensions**: GlobalNetworkPolicy, NetworkSet, Tier-based policies
4. **EKS Considerations**: VPC CNI NetworkPolicy activation, Security Groups for Pods

### Recommendations

- Apply default deny policy to all production namespaces
- Allow only required traffic following least privilege principle
- Regular policy audits and testing
- Consider Cilium when L7 policies are needed

---

## References

- [Kubernetes Network Policies Official Documentation](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy Documentation](https://docs.cilium.io/en/stable/security/policy/)
- [Calico Network Policy Documentation](https://docs.tigera.io/calico/latest/network-policy/)
- [EKS Security Best Practices - Network Security](https://aws.github.io/aws-eks-best-practices/security/docs/network/)
