# Network Policies

> **Review baseline**: Kubernetes 1.35 OpenAPI, Cilium 1.20.1, Calico 3.32.2 and current AWS documentation. Offline checks do not establish cluster compatibility.
> **Last Updated**: September 13, 2026

Kubernetes Network Policies are firewall rules that control traffic between Pods. This document covers basic NetworkPolicy and Cilium/Calico extensions. Sections are independent examples; merging every policy would change the effective permissions. No cluster/cloud deployment or live connectivity test was performed.

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

## Network Policy Overview {#network-policy-overview}

### What is a Network Policy?

Kubernetes NetworkPolicy selects Pods in its own namespace and controls supported ingress and egress traffic. A Pod with no selecting policy for a direction is not isolated by NetworkPolicy in that direction; routing, security groups, NACLs and other policy engines can still prevent connectivity.

**Both endpoints must permit** a Pod-to-Pod connection: the source's effective egress rules and the destination's effective ingress rules must allow it. Return traffic for an allowed connection is implicitly allowed. Policies are implemented asynchronously by a supporting network plugin; an API object alone does not prove enforcement. Node/hostNetwork traffic and protocols outside TCP/UDP/SCTP require implementation-specific review. The diagrams below show policy intent, not a reachability guarantee.

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
| **Additive** | Allow rules from selecting Kubernetes NetworkPolicies form a union for each direction; Cilium denies, Calico tiers and AWS administrative policies have separate semantics |
| **Selective Application** | Target Pods specified via podSelector |
| **Directional Control** | Separate control for Ingress (inbound) and Egress (outbound) |
| **CNI Dependent** | CNI plugin must support NetworkPolicy |

### CNI NetworkPolicy Support

| CNI | Basic NetworkPolicy | Extensions | L7 Policy |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | Optional Istio/Dikastes integration; verify the deployed product and versions |
| **Weave Net (archived project)** | Historical support | Legacy reference; evaluate a maintained implementation for new deployments | ✗ |
| **Flannel alone** | No policy enforcement by itself | A separate supported policy engine is needed | ✗ |
| **Amazon VPC CNI** | ✓ when enabled on supported EC2 Linux nodes | Standard NetworkPolicy; ClusterNetworkPolicy with VPC CNI 1.21+ | DNS egress on EKS Auto Mode nodes; see EKS considerations |

---

## Kubernetes NetworkPolicy Spec {#kubernetes-networkpolicy-spec}

### Basic Structure

Specify `policyTypes` explicitly. If omitted, Kubernetes defaults to Ingress and adds Egress when there is at least one egress rule. Empty rule arrays alone do not imply both directions.

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

Selects the Pods to which the policy applies in its own namespace. The following are alternative spec fragments, not standalone API resources.

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

Selects namespaces by labels, including the current namespace if it matches. `name` is not an automatically assigned namespace label. Use the built-in immutable `kubernetes.io/metadata.name` label for an exact namespace name; restrict who may change custom tenancy labels.

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

**Note:** AND vs OR distinction when using `namespaceSelector` and `podSelector` together:

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

An `ipBlock` permits a CIDR minus its `except` ranges in that rule. An exception is not a global deny and another policy can allow it. Service/load-balancer address translation can change the source or destination visible to the CNI; verify the actual path. The documentation CIDRs below are illustrative, not reachable production endpoints.

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

Specify allowed ports and protocols. `endPort` requires a numeric starting port and CNI range support; a named port cannot be the start of a range. API acceptance alone does not prove enforcement by every plugin.

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

## Default Deny Policies {#default-deny-policies}

An empty baseline contributes no allows; other selecting policies can still allow traffic. Existing-connection behavior after a policy change depends on the implementation and must be tested separately.

### Default Deny Ingress

An ingress isolation baseline with no allows of its own. Other selecting policies can still permit ingress:

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

An egress isolation baseline with no allows of its own. Other selecting policies can still permit egress:

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

This profile assumes Pod-based CoreDNS in `kube-system` with `k8s-app=kube-dns`. It allows both TCP and UDP 53. If DNS itself has ingress isolation, its policy must also allow the clients. NodeLocal DNSCache and Auto Mode node-local CoreDNS need their actual resolver path/IP profile; do not apply this Pod selector unchanged there.

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

### Zero Trust Architecture Default Policy

Both directions of frontend→API are present. This does not allow inbound traffic to the frontend or API→database; add only the reviewed flows. Use the Pod-based DNS assumption above.

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

## Policy Order and Evaluation {#policy-order-and-evaluation}

### Policy Evaluation Rules

For each endpoint and direction, evaluate only selecting **Kubernetes NetworkPolicies** as below. Then check the other endpoint's direction and all other network controls. An ingress-only policy does not isolate egress.

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
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**Result:** The API's ingress allows frontend Pods on 8080 and monitoring namespace Pods on 8080/9090. Their egress rules, actual listeners and other network controls must also permit the connection.

### Policy Evaluation Order

The Kubernetes NetworkPolicy API has no priority or explicit deny rule. Its allow union does not describe Calico policy order/tier actions, Cilium explicit denies, or AWS administrative policy evaluation:

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

## Cilium Network Policy Extensions {#cilium-network-policy-extensions}

These examples use the released Cilium 1.20.1 policy schema, not an instruction to upgrade every cluster. HTTP rules need a supported L7 proxy path. AWS VPC CNI chaining has documented advanced-feature limitations, including L7 policies; do not assume these HTTP examples work in that mode. A numeric Cilium security identity is an allocation for a label set, not a permanent application ID.

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

Cilium HTTP rules filter requests visible to its L7 proxy; they do not authenticate API keys or establish administrator roles. A caller can supply an `X-User-Role` header. This example filters methods, paths and an exact `Content-Type`. Enforce authentication and authorization in the application or an authenticated gateway. End-to-end TLS is not automatically decrypted for HTTP inspection. Review other policies that may allow the same traffic at L4.

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

### L7 Kafka Policy

The released Cilium 1.20.1 CNP schema supports HTTP and DNS L7 rules, but has no `rules.kafka`. The former `role`, `topic` and `clientID` recipe is not a current deployable API. Restrict broker connectivity with network policy, then enforce producer/consumer permissions for `orders` and `events` using Kafka authentication and ACLs. A client ID is not an authenticated principal.

This L4 example assumes an already configured TLS broker listener on TCP 9093, same-namespace clients, and separately authorized client egress/DNS. It does not configure TLS, broker ACLs or topic permissions.

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

### L7 DNS Policy

This example uses Pod-based CoreDNS. `ANY` on port53 covers UDP and TCP. DNS query permission and permission to connect to a returned IP are separate: resolving the database name below does not allow database connections. Replace the example domain, account for DNS search suffixes/cache/TTL, and verify the actual resolver profile. FQDN rules learn IPs from DNS; they do not authenticate a SaaS tenant or replace TLS/application authorization.

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

The resource is cluster-scoped, while its selector explicitly limits it to `production/app=api`. It permits gateway Pods on TCP8080. It controls ingress only; egress isolation/DNS and the gateway's own egress require their corresponding policies. The previous all-endpoint cluster/world allow example was not a default-deny policy.

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

### Cilium Entity-Based Policy

`host` includes the local node and its host-network containers; `cluster` includes more than application Pods. `world` covers endpoints outside the cluster and is not a fine-grained Internet/SaaS allowlist. Use explicit CIDR/FQDN rules when narrowing external access. This example gives only a labeled Kubernetes API client TCP443 access; configure its API endpoint, TLS trust, credentials and RBAC separately. Source identity can change across managed-control-plane network paths, so inspect actual flow identity rather than broadening ingress to the entire cluster.

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

## Calico Network Policy Extensions {#calico-network-policy-extensions}

The policy/Tier examples follow Calico Open Source3.32.2 resources. `projectcalico.org/v3` requires the supported Calico API server or matching `calicoctl` workflow; it is not the raw Kubernetes `crd.projectcalico.org/v1` storage API. Verify the installed datastore/API before applying. Ordered Calico actions and tier delegation differ from the additive Kubernetes NetworkPolicy API.

Current Open Source documentation also describes [Istio/Dikastes application-layer integration](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy). The HTTPMatch API requires that separate setup and supports ingress Allow rules. The Calico examples below cover L3/L4 policy; this review did not deploy or test the L7 integration.

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

These two global resources select only workloads in the `production` namespace. An unconstrained `selector: all()` can also affect host endpoints; do not apply a cluster-wide deny without an explicit scope and recovery path. Lower `order` is evaluated first within the tier. The example permits Pod-based DNS and otherwise supplies a deny baseline; add the reviewed application flows and account for higher-tier actions.

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

NetworkSet selectors match `metadata.labels`, not the resource's name. The first set is namespaced; the blocked set is global and is consumed by the security-tier example below. All CIDRs here are documentation ranges and must be replaced with reviewed destinations. The egress example permits TCP443 to the labeled namespaced set; DNS is a separate rule.

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

### Tier-Based Policies

Tiers are available in the referenced Calico Open Source release, not only Enterprise. A selecting tier defaults to `Deny` when no rule acts. The deny-known-threats tier therefore explicitly uses `defaultAction: Pass` so unrelated traffic can reach subsequent policy. `Pass` is delegation, not permission. `global()` belongs in `namespaceSelector`; the separate label selector identifies the GlobalNetworkSet. Populate application-tier policies and verify any final profile/default-tier behavior before deployment; creating an empty Tier is not a complete application isolation policy.

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

## Design Patterns {#design-patterns}

These are **alternative policy profiles**, not a bundle to apply together. Reusing `production` does not make unrelated examples compatible: their allow rules would accumulate. Prepare namespaces, workload labels, listening ports and the real DNS profile first. The examples were schema/intent checked locally, not exercised on a cluster.

### Microsegmentation

This profile permits frontend→API TCP8080 and API→database TCP5432 on both sides, plus DNS. It deliberately has no Internet egress or external frontend ingress. If required, add an approved destination CIDR/port or an authenticated egress gateway profile; excluding RFC1918 from 0.0.0.0/0 is not a SaaS allowlist.

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

### Namespace Isolation

The team profile includes same-team ingress **and egress**, plus DNS. Shared services additionally need destination ingress allowing team-a and a real TLS443 listener. Restrict namespace label administration; a team label is not an independent trust boundary.

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

### Database Protection

The `database` namespace must exist. Production callers and monitoring Pods need their own egress allows. TCP5432 peer rules permit the assumed PostgreSQL replication transport only; configure database authentication/TLS separately. TCP9187 assumes a separately installed exporter.

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

### 3-Tier Architecture Policy

Assume an existing `gateway-system/app=edge-proxy` workload that terminates client TLS and may reach the web Pods on TCP80. The gateway's egress policy is outside this namespace. Data peer ingress and egress use TCP5432/6379; additional replication/cluster-bus/backup ports depend on the chosen database and are not implied. Split PostgreSQL and Redis selectors in a real deployment.

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

## Testing Network Policies {#testing-network-policies}

### Testing with netshoot

Use approved, already provisioned diagnostic Pods with pinned images and reviewed permissions. Select source labels/namespace/node placement that actually exercise the policy; a generic unlabeled Pod does not represent the application. Provisioning netshoot creates a workload and may conflict with Pod Security admission. Do not create/delete a fixed shared `test-pod` name as part of an observation script. Only run probes against owned test endpoints.

### Testing with kubectl exec

Set the context, namespace, existing Pod and container explicitly. DNS success is not TCP success; connection refusal, an unhealthy listener, a TLS error and a policy drop are different outcomes. These commands test connectivity only and do not print response bodies. They were not run against a cluster during this review.

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Cilium Connectivity Test

`cilium connectivity test` creates test resources and traffic; it is not a read-only status command. Use an approved isolated cluster/namespace, compatible CLI and images, defined external destinations, and a cleanup plan. Consult `cilium connectivity test --help` for the installed CLI's filters instead of assuming historical test names still exist. A passing suite does not prove every application policy or CNI chaining feature.

### Automated Test Script

This script only executes bounded curl probes in two existing Pods; it creates or deletes no cluster resources. Set `CONTEXT`, `NAMESPACE`, `ALLOW_POD`, `DENIED_POD`, `PROBE_CONTAINER` and a non-secret `TARGET_URL` ending in `/health`. Both containers need `sh` and `curl`. The first Pod is a known allowed positive control for the same destination. HTTP error responses still establish network reachability because this test is not application-health validation.

Exit1 means the blocked subject unexpectedly connected; exit2 means unknown/error; exit3 means timeout requiring corroboration. A timeout **never** becomes automatic PASS: correlate the exact source/destination/port/time with a CNI policy-drop verdict, while checking endpoint health, routes and SG/NACL controls. No live enforcement is claimed by the local mock tests.

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

## EKS Considerations {#eks-considerations}

### Amazon VPC CNI and NetworkPolicy

Amazon VPC CNI supports network policy after enablement. The current AWS guide requires VPC CNI 1.21+ for both standard and admin policies, a compatible EKS platform and Linux kernel 5.10+. Enforcement applies to supported EC2 Linux nodes, not Fargate or Windows. Use a currently supported EKS version and verify its compatible add-on release; do not infer EKS support from upstream Kubernetes releases.

For an **EKS-managed** VPC CNI add-on, preserve its existing configuration while setting the documented string `"enableNetworkPolicy": "true"`. The following changes the selected cluster after review; it does not upgrade the add-on version. If the installed version is incompatible, stop and follow the documented upgrade procedure first.

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

Check the update status and policy behavior before rollout. `--resolve-conflicts PRESERVE` does not merge a replacement JSON document for you; the example explicitly carries forward the existing values. Keep the snapshot for recovery. A Helm-owned installation uses its reviewed chart/values and `enableNetworkPolicy: true`; do not take ownership of it through this managed-add-on command. Setting the invented `ENABLE_NETWORK_POLICY` environment variable is not the enablement procedure.

Standard startup mode can initially allow a new Pod until its policy is programmed. `NETWORK_POLICY_ENFORCING_MODE=strict` starts eligible Pods denied and requires a complete allow matrix, including DNS; changing it can interrupt workloads. Controller-managed Pods are the reliable testing target. Enforcement is on the primary Pod interface, so inspect extra interfaces, IPv6-to-IPv4 egress, host networking and NAT separately. Do not install two engines to manage the same standard policies or delete `aws-node` as a migration shortcut.

### EKS Enhanced Network Security Policies (December 2025)

> **Announced**: December 15, 2025 · [Source](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

The feature is real, but its resources use **`networking.k8s.aws/v1alpha1`**. `ClusterNetworkPolicy` is cluster scoped and has a required `tier`; DNS-based egress uses `ApplicationNetworkPolicy` for the namespace example below. Standard/admin VPC CNI policy support on EC2 Linux does not mean every compute mode supports it. DNS rules are enforced only on **Auto Mode-launched EC2 instances**, including in a mixed cluster.

**Auto Mode prerequisite:** enable its Network Policy Controller before applying the policies below. Updating an EKS-managed `vpc-cni` add-on is a separate path and does not enable policy enforcement for a pure Auto Mode cluster. The required setting is ConfigMap `kube-system/amazon-vpc-cni`, `data.enable-network-policy-controller: "true"`. The workflow below preserves other ConfigMap data with a merge patch, creates only when absent, and stops on a failed read or write. Review the cluster context and existing configuration before running it.

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

After enabling it, inspect the corresponding `PolicyEndpoints` objects and test both allowed and denied traffic on the selected Auto Mode nodes. A stored flag or an accepted policy object is not proof of enforcement. See the [Auto Mode network policy setup](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html). No cluster enforcement test was performed for this documentation audit.

This Admin-tier example denies incoming traffic from namespace-selected Pods to `isolated-demo`, including Pods in that same namespace. It is not a complete external/host-network firewall or a DNS allow policy. Admin Deny cannot be overridden by a namespace NetworkPolicy. Review the actual installed CRD before adding other actions: the current upstream AWS controller schema names its permitting action `Accept`, while the user-guide prose uses “Allow”.

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

The FQDN example selects `app=backend` in `production`. **Replace `10.100.0.10/32` with your cluster's actual Auto Mode CoreDNS IP**: it is Service CIDR network address plus 10 (`::a/128` for IPv6). Pure Auto Mode CoreDNS runs on the node; a conventional CoreDNS Pod selector is not interchangeable. Allow both TCP and UDP DNS. Use a unique resource name that does not collide with a NetworkPolicy in that namespace.

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

The DNS proxy observes permitted answers and their TTLs, then the data path permits the learned destination IPs/ports. This does not authenticate a SaaS account or prove the peer's HTTP identity; shared IPs and DNS behavior require testing. TLS certificate verification, application authorization, routes and any Route 53 DNS Firewall rules remain relevant. Other applicable policies and direct backend paths must be reviewed together.

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode policies](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Security Groups for Pods

This binding example assumes the EKS VPC Resource Controller, its **cluster-role** permissions, supported trunking-compatible EC2 Linux nodes and a reviewed VPC CNI configuration. The current AWS guide excludes Windows and EKS Auto Mode. Fargate uses a separate Pod-SG model and does not gain VPC-CNI NetworkPolicy support merely from having a security group. Apply the binding to new matching workload Pods through their owner; existing Pods are not retrofitted automatically.

For Calico plus Pod SGs, AWS documents VPC CNI1.11.0+ with `POD_SECURITY_GROUP_ENFORCING_MODE=standard`; use the current CNI requirements as well, rather than treating that minimum as a recommended version. Standard-mode external SNAT can use the node SG instead of the Pod SG. Verify the exact path. The old bare PostgreSQL Pod lacked credentials/storage and was not a functioning database deployment.

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

The Terraform fragment permits DB ingress from one reviewed app SG and initiates no new egress connections. Stateful return traffic is allowed by SG tracking; add only the required DNS, replication, backup or external egress separately. Variables are existing operator inputs; no Terraform plan/apply was executed.

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

### Combining VPC-Level Controls with NetworkPolicy

NetworkPolicy, the actually applied SGs and NACLs must all allow the relevant path. This ingress-only NetworkPolicy does not restrict database egress; add the selected egress profile and source-Pod egress. Multiple SGs combine their allows. NACLs are **stateless**, so a subnet rule allowing inbound5432 needs a matching return path to the client's ephemeral ports, plus appropriate rules on the client's subnet. The fragments below do not replace a complete reviewed ACL rule set.

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

### Using Cilium on EKS

Choose **AWS VPC CNI chaining** or a separately designed full CNI/IPAM migration. In chaining mode AWS VPC CNI keeps ENI/IPAM responsibility and Cilium attaches its datapath. Preserve `aws-node`; deleting it is not an installation shortcut. Review the existing add-on/Helm owner and avoid overlapping policy-enforcement engines. Existing Pods need a controlled recreation before chaining policy applies; plan disruption and rollback.

The official1.20.1 chaining guide supplies these values, but also documents L7/IPsec limitations. It contains old illustrative outputs; those are not validation of your current EKS environment. Prepare the chart repository/package, verify provenance and render first:

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

## Visualization Tools {#visualization-tools}

### Cilium Network Policy Editor

A policy editor helps author policy; **Hubble UI visualizes observed service flows**. They are different tools. Enabling Hubble/UI changes cluster configuration and belongs to the installation owner. With an already installed, authenticated Hubble service, inspect the existing service and use a local port-forward. Do not expose the UI publicly as a debugging shortcut.

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium Policy Verdict Check

Use an authenticated Hubble connection. `DROPPED` includes reasons other than policy; inspect drop reason, endpoint identity, time and direction. A `FORWARDED` observation at one point is not an end-to-end delivery guarantee.


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

The Enterprise management UI requires the licensed product and its actual service/TLS/authentication configuration; it is not automatically installed by Calico Open Source. Inspect the installed service name/port and access policy before forwarding. Do not assume `cnx-manager` exists in every installation.

### Network Policy Visualization Tools

Use `kubectl get networkpolicy -n <namespace>` and `kubectl describe networkpolicy <name> -n <namespace>` to inspect Kubernetes policy selectors/rules, and the installed engine's authenticated flow tools to inspect enforcement. Third-party viewer/plugin availability and flags must be checked against that project's current release. A graph of YAML alone cannot prove dataplane enforcement.

### Security Testing with Kube-hunter

kube-hunter is a cluster exposure/security scanner, not a NetworkPolicy allow/deny verifier. Its scans can generate intrusive traffic; use an explicitly approved target/scope and a reviewed release/image. Do not deploy an unpinned scanner into a live namespace from a general policy tutorial. This review did not execute a scanner.

## Best Practices

### 1. Apply Default Deny Policy

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

### 2. Principle of Least Privilege

Explicitly allow only required traffic:

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

### 4. Regular Policy Audits

This read-only inventory lists namespace-wide empty allow baselines separately for ingress and egress. Empty `[]` and absent rule arrays are handled, while a rule `{}` allows traffic and is not a deny baseline. API/authorization errors fail instead of appearing as zero policies. A listed baseline is **not proof of isolation**: other allow rules, extension policies, uncovered Pods and CNI state still require review.

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

## Summary

Kubernetes Network Policies are a core security mechanism for controlling Pod communication within clusters:

1. **Basic NetworkPolicy**: Namespace-scoped, supports podSelector/namespaceSelector/ipBlock
2. **Cilium Extensions**: L7 policies, DNS FQDN-based policies, cluster-wide policies
3. **Calico Extensions**: GlobalNetworkPolicy, NetworkSet, Tier-based policies
4. **EKS Considerations**: VPC CNI NetworkPolicy activation, Security Groups for Pods, ClusterNetworkPolicy and DNS (FQDN)-based egress control

### Recommendations

- Apply default deny policy to all production namespaces
- Allow only required traffic following least privilege principle
- Regular policy audits and testing
- Consider Cilium when L7 policies are needed

---

## References

- [Kubernetes Network Policies Official Documentation](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy Documentation](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy Documentation](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS Security Best Practices - Network Security](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS Enhanced Network Security Policies (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod security groups](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
