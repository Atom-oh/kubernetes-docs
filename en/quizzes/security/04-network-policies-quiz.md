# Network Policies Quiz

> **Last Updated**: September 13, 2026

This quiz tests your understanding of Kubernetes Network Policies, Cilium Network Policies, and microsegmentation.

## Quiz Questions

### 1. What is the default behavior of Kubernetes NetworkPolicy?

A. Block all traffic
B. No NetworkPolicy isolation in a direction with no selecting policy
C. Block inbound only
D. Block outbound only

<details>
<summary>Show Answer</summary>

**Answer: B. No NetworkPolicy isolation in a direction with no selecting policy**

**Explanation:**
Evaluate ingress and egress separately. No selecting policy for a direction means NetworkPolicy does not isolate it; CNI/route/SG/NACL or other policies can still block connectivity. A selecting ingress-only policy does not also isolate egress. For Pod-to-Pod traffic, source egress and destination ingress must both permit the connection.

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
B. spec.ingress[].toPorts[].rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>Show Answer</summary>

**Answer: B. spec.ingress[].toPorts[].rules.http**

**Explanation:**
HTTP rules are nested under an ingress rule's `toPorts[].rules.http` (or an egress rule for outbound filtering). They require a supported L7 proxy path; end-to-end TLS is not automatically inspected, and user-supplied role/API-key headers are not authentication. Cilium's AWS VPC CNI chaining mode has documented L7 limitations.

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. What creates a namespace-wide default-deny baseline for both directions?

A. Specify only Ingress in policyTypes
B. Set podSelector to empty, specify Ingress and Egress in policyTypes
C. Leave ingress and egress rules empty
D. Both B and C

<details>
<summary>Show Answer</summary>

**Answer: D. Both B and C**

**Explanation:**
For a namespace-wide baseline in **both directions**, combine B and C. An empty selector selects all Pods in the policy's own namespace, and explicit Ingress/Egress types with no allows isolate both directions. Other selecting Kubernetes NetworkPolicies can add allows; a baseline does not override them. An ingress-only baseline is also possible when that narrower scope is intended.

</details>

### 6. What is the characteristic of CiliumClusterwideNetworkPolicy?

A. Requires metadata.namespace to select its scope
B. A cluster-scoped resource whose endpoint selector controls its targets
C. Controls only external traffic
D. Supports only L7 policies

<details>
<summary>Show Answer</summary>

**Answer: B. A cluster-scoped resource whose endpoint selector controls its targets**

**Explanation:**
CiliumClusterwideNetworkPolicy is not namespaced. Its endpoint selector can cover several namespaces or explicitly narrow the target to one namespace/application. Cluster scope does not mean every endpoint is selected, nor that broad `cluster`/`world` allow rules are default deny.

</details>

### 7. How do you allow all Pods from a specific namespace in NetworkPolicy?

A. Use only namespaceSelector
B. Use only podSelector
C. Combine namespaceSelector with podSelector requiring app=api
D. Use namespace field

<details>
<summary>Show Answer</summary>

**Answer: A. Use only namespaceSelector**

**Explanation:**
Use `namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` to select all Pods in that namespace. Adding an **empty** podSelector in the same peer would also select all of them; option C instead restricts the Pods to `app=api`. In one peer the selectors are ANDed; separate peer entries are ORed. A custom `name` label is not created automatically.

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
`toFQDNs` uses DNS-derived IPs with the specified port rules. Permit the actual resolver path and the needed DNS queries separately, including TCP as well as UDP53. Cache/TTL, search suffixes, shared destination IPs and TLS/application authorization still matter. A domain match is not proof of SaaS tenant identity.

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
Containers in one Pod share the network namespace; their localhost communication is outside ordinary Kubernetes NetworkPolicy enforcement. Node/hostNetwork handling and non-TCP/UDP/SCTP protocols have implementation-specific limits. Do not infer full host isolation from a Pod policy.

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
Label-based endpoint policy avoids hardcoding transient Pod IPs. The datapath maps current endpoints to security identities for their relevant label sets. A numeric identity can be reallocated and is not a permanent application identifier; label changes, namespace/cluster context and propagation must still be considered.

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
C describes the backend's application path: frontend ingress and database egress on the reviewed ports. Also permit frontend egress and database ingress, plus the chosen DNS/health/monitoring paths where required. Otherwise a default-deny policy at the other endpoint can still block the connection. Return traffic on an allowed connection is implicitly permitted.

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
`except` subtracts CIDRs from that ipBlock's allow rule. It is not a global deny: another selecting policy can permit the excluded address. Address translation can change which IP a plugin evaluates, so verify the actual CNI and load-balancer/Service path.

</details>

---

[Network policies guide](../../security/04-network-policies.md)
