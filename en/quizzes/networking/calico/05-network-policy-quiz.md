# Network Policy Quiz

> **Related Document**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **Last Updated**: February 22, 2025

## Quiz

1. What is a key limitation of Kubernetes standard NetworkPolicy that Calico addresses?
   - A) Cannot specify port numbers
   - B) No support for egress rules
   - C) No deny rules, no global policies, limited selector options
   - D) Cannot select pods by labels

<details>
<summary>Show Answer</summary>

**Answer: C) No deny rules, no global policies, limited selector options**

**Explanation:**
Kubernetes standard NetworkPolicy has several limitations: it only supports Allow rules (no explicit Deny), cannot create cluster-wide global policies, has limited selector options, and doesn't support L7 (application layer) filtering. Calico extends NetworkPolicy with explicit Deny/Allow/Log/Pass actions, GlobalNetworkPolicy, advanced selectors, and L7 policy support.

</details>

2. What is the syntax for selectors in Calico NetworkPolicy?
   - A) YAML key-value pairs like standard Kubernetes
   - B) Expression-based syntax like `app == 'frontend'`
   - C) Regular expressions
   - D) JSON path expressions

<details>
<summary>Show Answer</summary>

**Answer: B) Expression-based syntax like `app == 'frontend'`**

**Explanation:**
Calico uses an expression-based selector syntax that supports operators like `==`, `!=`, `in`, `not in`, `has()`, and `!has()`. For example: `app == 'frontend'`, `environment in {'prod', 'staging'}`, `has(role)`. This provides more flexibility than standard Kubernetes label selectors.

</details>

3. What are the valid action types in Calico NetworkPolicy rules?
   - A) Accept, Reject
   - B) Allow, Deny, Log, Pass
   - C) Permit, Block, Audit
   - D) Enable, Disable, Monitor

<details>
<summary>Show Answer</summary>

**Answer: B) Allow, Deny, Log, Pass**

**Explanation:**
Calico NetworkPolicy supports four action types: `Allow` (permit the traffic), `Deny` (drop the traffic), `Log` (log the traffic and continue evaluation), and `Pass` (skip to the next tier for evaluation). These actions provide fine-grained control over traffic handling.

</details>

4. What is the difference between GlobalNetworkPolicy and NetworkPolicy in Calico?
   - A) GlobalNetworkPolicy is faster
   - B) NetworkPolicy requires a namespace, GlobalNetworkPolicy applies cluster-wide
   - C) GlobalNetworkPolicy only works with eBPF mode
   - D) NetworkPolicy supports more features

<details>
<summary>Show Answer</summary>

**Answer: B) NetworkPolicy requires a namespace, GlobalNetworkPolicy applies cluster-wide**

**Explanation:**
Calico NetworkPolicy is namespaced and applies only to pods within that namespace, similar to Kubernetes NetworkPolicy. GlobalNetworkPolicy is cluster-wide and can apply to all pods across all namespaces, making it ideal for security baselines, compliance requirements, and cluster-wide rules like default deny policies.

</details>

5. What is a NetworkSet used for in Calico?
   - A) Grouping network interfaces
   - B) Defining reusable sets of IP addresses/CIDRs
   - C) Configuring network namespaces
   - D) Managing network plugins

<details>
<summary>Show Answer</summary>

**Answer: B) Defining reusable sets of IP addresses/CIDRs**

**Explanation:**
A NetworkSet is a Calico resource that defines a set of IP addresses or CIDR blocks that can be referenced in network policies. This allows you to define groups of external IPs (like database servers or trusted partners) once and reference them in multiple policies, making policy management easier and more maintainable.

</details>

6. How are Tiers evaluated in Calico's policy model?
   - A) Alphabetically by name
   - B) By order field, lower numbers evaluated first
   - C) Randomly
   - D) By creation timestamp

<details>
<summary>Show Answer</summary>

**Answer: B) By order field, lower numbers evaluated first**

**Explanation:**
Tiers are evaluated in order based on their `order` field, with lower numbers evaluated first. Within each tier, policies are also evaluated by their order field. This hierarchical structure allows organizations to separate security policies (low order), platform policies (medium order), and application policies (high order).

</details>

7. What does the Pass action do in a Calico policy rule?
   - A) Allows the traffic immediately
   - B) Drops the traffic silently
   - C) Skips to the next tier for continued evaluation
   - D) Logs the traffic and allows it

<details>
<summary>Show Answer</summary>

**Answer: C) Skips to the next tier for continued evaluation**

**Explanation:**
The `Pass` action causes policy evaluation to skip the remaining policies in the current tier and continue to the next tier. This is useful when a higher-priority tier (like security) wants to allow certain traffic to be further evaluated by lower-priority tiers (like application policies) rather than making a final decision.

</details>

8. How can you implement FQDN-based (domain name) policies in Calico?
   - A) Using the `hosts` field in ingress rules
   - B) Using the `domains` field in destination specification
   - C) FQDN policies are not supported
   - D) Using DNS NetworkPolicy CRD

<details>
<summary>Show Answer</summary>

**Answer: B) Using the `domains` field in destination specification**

**Explanation:**
Calico supports FQDN-based policies using the `domains` field in egress rules. You can specify domain patterns like `"*.amazonaws.com"` or exact domains. Calico resolves these domains to IP addresses and creates the appropriate rules. This feature is available in Calico Enterprise and requires DNS proxy configuration in open-source Calico.

</details>

9. What does the applyOnForward setting control in a GlobalNetworkPolicy?
   - A) Whether the policy applies to forwarded/routed traffic through the host
   - B) Whether the policy is applied in forward or reverse order
   - C) Whether to forward policy violations to a SIEM
   - D) Whether the policy applies to port forwarding

<details>
<summary>Show Answer</summary>

**Answer: A) Whether the policy applies to forwarded/routed traffic through the host**

**Explanation:**
The `applyOnForward` setting determines whether the policy applies to traffic being forwarded through the host (not destined to or originating from the host itself). This is important for host endpoint policies and scenarios where the node is acting as a router for traffic between other endpoints.

</details>

10. What is the purpose of doNotTrack in a Calico policy?
    - A) Disables policy logging
    - B) Applies the policy before connection tracking (stateless)
    - C) Prevents the policy from being tracked in audit logs
    - D) Disables endpoint tracking

<details>
<summary>Show Answer</summary>

**Answer: B) Applies the policy before connection tracking (stateless)**

**Explanation:**
The `doNotTrack` option applies the policy rules before Linux connection tracking (conntrack). This creates stateless rules that don't track connection state, useful for high-performance scenarios or when you need to apply rules to traffic before it enters the connection tracking system. Both request and response traffic must be explicitly allowed.

</details>

11. What is the purpose of preDNAT in a Calico policy?
    - A) Applies policy before DNS resolution
    - B) Applies policy before Destination NAT, seeing original destination
    - C) Prevents DNAT from occurring
    - D) Applies policy only to DNS traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Applies policy before Destination NAT, seeing original destination**

**Explanation:**
The `preDNAT` option applies the policy before Destination NAT occurs, allowing the policy to see the original destination IP/port before it is translated. This is useful for policies on host endpoints where you want to filter traffic based on the original destination (like external IPs) before DNAT translates it to a pod IP.

</details>

12. How do you implement a default deny policy for all pods in Calico?
   - A) Set a cluster-wide flag in FelixConfiguration
   - B) Create a GlobalNetworkPolicy with selector `all()` and no rules
   - C) Delete all existing NetworkPolicies
   - D) Configure default deny in the IPPool

<details>
<summary>Show Answer</summary>

**Answer: B) Create a GlobalNetworkPolicy with selector `all()` and no rules**

**Explanation:**
To implement default deny, create a GlobalNetworkPolicy that selects all pods (`selector: all()`) with `types: [Ingress, Egress]` but no allow rules. This policy should have a high order number so it's evaluated last. Any traffic not explicitly allowed by other policies will be denied by this catch-all policy.

</details>

13. What does the order field in a Calico policy control?
    - A) The order in which pods are selected
    - B) The evaluation priority within a tier (lower = earlier)
    - C) The order of rule application within the policy
    - D) The order of IP addresses in NetworkSets

<details>
<summary>Show Answer</summary>

**Answer: B) The evaluation priority within a tier (lower = earlier)**

**Explanation:**
The `order` field determines the evaluation priority of policies within a tier. Policies with lower order values are evaluated first. If a policy matches and takes a terminal action (Allow or Deny), evaluation stops. This allows you to create high-priority exceptions before general rules.

</details>

14. What is a Host Endpoint in Calico?
    - A) A pod running on the host network
    - B) A representation of a host's network interface for policy enforcement
    - C) The API server endpoint
    - D) A service endpoint on the host

<details>
<summary>Show Answer</summary>

**Answer: B) A representation of a host's network interface for policy enforcement**

**Explanation:**
A Host Endpoint represents a network interface on a host node, allowing Calico policies to be applied to traffic entering or leaving the host itself (not just pod traffic). This enables securing the host's network interfaces, controlling what traffic can reach node services, and implementing host-level firewall rules.

</details>

15. How can you debug why a network policy is not working as expected?
    - A) Only by reading the policy YAML
    - B) Check workload endpoints, policy evaluation with calicoctl, and Felix logs
    - C) Restart all Calico components
    - D) Network policy debugging is not supported

<details>
<summary>Show Answer</summary>

**Answer: B) Check workload endpoints, policy evaluation with calicoctl, and Felix logs**

**Explanation:**
To debug network policies: 1) Use `calicoctl get workloadendpoint -n <namespace>` to verify the endpoint exists and has correct labels, 2) Use `calicoctl get networkpolicy -A` and `globalnetworkpolicy` to list all policies, 3) Check Felix logs for policy-related messages, 4) Verify selector expressions match the endpoint labels, 5) In eBPF mode, use `tc filter show` to inspect applied rules.

</details>

---

[Return to Learning Materials](../../../networking/calico/05-network-policy.md) | [Previous Quiz: BGP Deep Dive](./04-bgp-deep-dive-quiz.md)
