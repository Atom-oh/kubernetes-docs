# Network Policies Quiz

This quiz tests your understanding of Kubernetes Network Policies, Cilium Network Policies, and microsegmentation.

## Quiz Questions

### 1. What is the default behavior of Kubernetes NetworkPolicy?

A. Block all traffic
B. Allow all traffic
C. Block inbound only
D. Block outbound only

<details>
<summary>Show Answer</summary>

**Answer: B. Allow all traffic**

**Explanation:**
Without NetworkPolicy, Kubernetes allows all traffic between Pods by default. When you create a NetworkPolicy, it enables "default deny" behavior for Pods matching that policy's podSelector.

</details>

### 2. Which field selects specific Pods in a NetworkPolicy?

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>Show Answer</summary>

**Answer: B. podSelector**

**Explanation:**
The `spec.podSelector` field in NetworkPolicy selects Pods to which the policy applies:
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

An empty podSelector (`{}`) selects all Pods in the namespace.

</details>

### 3. Which fields define inbound and outbound rules in NetworkPolicy?

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>Show Answer</summary>

**Answer: B. ingress/egress**

**Explanation:**
- **ingress**: Inbound traffic rules
- **egress**: Outbound traffic rules

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

### 4. Where are L7 HTTP rules defined in CiliumNetworkPolicy?

A. spec.http
B. spec.ingress.toPorts.rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>Show Answer</summary>

**Answer: B. spec.ingress.toPorts.rules.http**

**Explanation:**
L7 rules in CiliumNetworkPolicy are defined in the rules section within toPorts:
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

### 5. What is the correct NetworkPolicy for implementing a default deny policy?

A. Specify only Ingress in policyTypes
B. Set podSelector to empty, specify Ingress and Egress in policyTypes
C. Leave ingress and egress rules empty
D. Both B and C

<details>
<summary>Show Answer</summary>

**Answer: D. Both B and C**

**Explanation:**
Default deny policy example:
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

An empty podSelector selects all Pods, and without rules, that traffic type is blocked.

</details>

### 6. What is the characteristic of CiliumClusterwideNetworkPolicy?

A. Applies only to specific namespace
B. Applies across the entire cluster
C. Controls only external traffic
D. Supports only L7 policies

<details>
<summary>Show Answer</summary>

**Answer: B. Applies across the entire cluster**

**Explanation:**
CiliumClusterwideNetworkPolicy applies across the entire cluster regardless of namespace. It's useful for implementing common security rules (e.g., blocking metadata service access from all namespaces).

</details>

### 7. How do you allow all Pods from a specific namespace in NetworkPolicy?

A. Use only namespaceSelector
B. Use only podSelector
C. Combine namespaceSelector with empty podSelector
D. Use namespace field

<details>
<summary>Show Answer</summary>

**Answer: A. Use only namespaceSelector**

**Explanation:**
```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
```

Using only namespaceSelector allows all Pods from that namespace. Using podSelector together selects only specific Pods within that namespace.

</details>

### 8. Which field defines FQDN-based egress rules in CiliumNetworkPolicy?

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>Show Answer</summary>

**Answer: A. toFQDNs**

**Explanation:**
CiliumNetworkPolicy's toFQDNs allows egress traffic based on DNS names:
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

### 9. Which traffic is NOT affected by NetworkPolicy?

A. Traffic between Pods
B. Traffic between containers in the same Pod (localhost)
C. Traffic through Services
D. Traffic from external sources

<details>
<summary>Show Answer</summary>

**Answer: B. Traffic between containers in the same Pod (localhost)**

**Explanation:**
NetworkPolicy applies to network traffic between Pods. Localhost communication between containers in the same Pod is outside the scope of NetworkPolicy. Also, Pods using the node's hostNetwork have some limitations.

</details>

### 10. What is the advantage of Cilium's Identity-based policy?

A. Not affected by IP address changes
B. Faster processing speed
C. Less memory usage
D. No DNS lookup required

<details>
<summary>Show Answer</summary>

**Answer: A. Not affected by IP address changes**

**Explanation:**
Cilium Identity is generated based on Pod labels. Even if a Pod restarts and its IP changes, it maintains the same Identity if it has the same labels. This overcomes the limitations of IP-based policies.

</details>

### 11. What is the correct network policy for the backend tier in a 3-tier architecture?

A. Allow all traffic
B. Allow ingress only from frontend
C. Allow ingress from frontend, allow egress to database
D. Allow egress only to database

<details>
<summary>Show Answer</summary>

**Answer: C. Allow ingress from frontend, allow egress to database**

**Explanation:**
In 3-tier microsegmentation, for the backend:
- **Ingress**: Allow only from frontend tier
- **Egress**: Allow only to database tier

This follows the principle of least privilege and clearly controls traffic flow between tiers.

</details>

### 12. Which field excludes specific IPs when specifying CIDR ranges with ipBlock in NetworkPolicy?

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>Show Answer</summary>

**Answer: B. except**

**Explanation:**
The ipBlock's except field can exclude specific CIDRs:
```yaml
ingress:
  - from:
      - ipBlock:
          cidr: 10.0.0.0/8
          except:
            - 10.0.1.0/24
            - 10.0.2.0/24
```

This allows traffic from 10.0.0.0/8 range except 10.0.1.0/24 and 10.0.2.0/24.

</details>
