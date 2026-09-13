# Network Policy Quiz

> **Related Document**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **Last Updated**: September 12, 2026

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
The standard Kubernetes NetworkPolicy object provides namespaced, additive L3/L4 allow rules. It already supports named ports and numeric ranges with endPort when the plugin implements them. Calico adds explicit actions, global policy, tiers and expression selectors. Open Source HTTP policy requires the Istio/Dikastes integration; DNS domains are a commercial extension.

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
Allow and Deny finish this endpoint/direction’s normal policy decision. Log continues evaluation and can still be followed by a deny. Pass skips all remaining policies in the current tier and goes to the next applicable tier; after the last tier, Profiles are considered. The other endpoint’s policy still applies.

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
NetworkPolicy selects workloads in its namespace. GlobalNetworkPolicy is non-namespaced and can select workloads across namespaces and HostEndpoints. It does not automatically mean every endpoint is selected; use explicit target scope and preserve host/system connectivity.

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
A NetworkSet groups labeled IP/CIDR ranges for reuse. A namespaced NetworkSet and a GlobalNetworkSet have different selection scope. Use a separate namespaceSelector: global() when selecting global resources from a namespaced policy; global(label-expression) is not valid syntax.

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
Lower tier orders are evaluated first, then lower policy orders within each tier. Only tiers with a policy selecting the endpoint and direction apply. No rule match in an applicable tier uses its defaultAction, normally Deny. The built-in default tier is fixed at 1,000,000; it is not an implicit infinity.

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
Pass skips the remaining policies in its tier, including any later security restrictions. To check all deny-only guardrails before delegation, a tier-level defaultAction: Pass can be more appropriate than an early unconditional Pass rule.

</details>

8. Where does Calico Enterprise 3.23 specify allowed egress domain names?
   - A) Using the `hosts` field in ingress rules
   - B) Using the `domains` field in destination specification
   - C) FQDN policies are not supported
   - D) Using DNS NetworkPolicy CRD

<details>
<summary>Show Answer</summary>

**Answer: B) Using the `domains` field in destination specification**

**Explanation:**
Calico Enterprise supports destination.domains on egress Allow rules with trusted DNS learning. This field is absent from the Open Source 3.32 CRD; enabling policySyncPathPrefix or an arbitrary DNS proxy does not add it. A prefix wildcard matches one or more domain components, and IP-based matching is not HTTPS hostname authentication.

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
For HostEndpoint policy, applyOnForward: true also applies to forwarded traffic. It is required when doNotTrack or preDNAT is true. A host Allow does not bypass the applicable workload endpoint policy.

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
doNotTrack is a host-policy option, requires applyOnForward: true and applies before connection tracking. An untracked Allow prevents tracking of matching traffic; requests and responses need explicit rules. It is not a universal speed improvement and can conflict with Service/NAT paths that depend on conntrack.

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
preDNAT evaluates ingress host traffic using the original destination IP/port before DNAT. It requires applyOnForward: true, cannot contain egress rules and cannot be combined with doNotTrack. A miss does not automatically drop at this stage; later host/workload policy still applies.

</details>

12. Which baseline selects both directions for demo-namespace workloads after earlier explicit allow policies?
   - A) Set a cluster-wide flag in FelixConfiguration
   - B) Create a scoped GlobalNetworkPolicy with `types: [Ingress, Egress]` and empty rules
   - C) Delete all existing NetworkPolicies
   - D) Configure default deny in the IPPool

<details>
<summary>Show Answer</summary>

**Answer: B) Create a scoped GlobalNetworkPolicy with `types: [Ingress, Egress]` and empty rules**

**Explanation:**
Select the intended namespace/workloads, explicitly set both types, and leave rules empty. An omitted order follows explicitly ordered policies. The baseline does not override earlier terminal Allows, and selector: all() alone can include HostEndpoints. Do not apply an unscoped catch-all to system traffic as a generic tutorial step.

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
HostEndpoint represents an interface on a managed host for policy enforcement. Manual endpoints can introduce default-deny behavior; automatic endpoints normally have a default-allow profile, and failsafe ports still matter. Installation.hostPorts does not create automatic HostEndpoints.

</details>

15. How can you debug why a network policy is not working as expected?
    - A) Only by reading the policy YAML
    - B) Check endpoint labels, all applicable tiers, backend/logs and actual connections
    - C) Restart all Calico components
    - D) Network policy debugging is not supported

<details>
<summary>Show Answer</summary>

**Answer: B) Check endpoint labels, all applicable tiers, backend/logs and actual connections**

**Explanation:**
List both Kubernetes and Calico policies, explicitly inspect all relevant tiers, verify endpoint labels and test allowed/denied new connections. Felix readiness is not a latency benchmark. iptables Log actions use kernel logs. Service/NAT behavior in kube-proxy or its replacement can also explain failures; a tc program listing alone is not an effective-policy trace.

</details>

16. Which permission structure implements Calico application-tier editing through the standard API server?
    - A) Ordinary networkpolicies with resourceNames: ["application.*"] alone
    - B) Get on the application Tier plus tier.networkpolicies with application.* and the intended namespace binding
    - C) Any Role containing verbs: ["*"]
    - D) A namespace named application

<details>
<summary>Show Answer</summary>

**Answer: B) Get on the application Tier plus tier.networkpolicies with application.* and the intended namespace binding**

**Explanation:**
Calico checks its tier.networkpolicies pseudo-resource, a synthetic application.* or policy name, and get permission on the Tier. This is not a generic Kubernetes resourceNames glob. Broader additive bindings and native-v3 read limitations must also be considered.

</details>

17. A client uses source port 49152 to connect to backend port 8080. Which ingress port match expresses the server listener?
    - A) source.ports: [8080]
    - B) source.ports: [49152] for every client
    - C) destination.ports: [8080] with protocol TCP
    - D) No protocol and a source-port range covering every port

<details>
<summary>Show Answer</summary>

**Answer: C) destination.ports: [8080] with protocol TCP**

**Explanation:**
The service listens on destination port 8080. Client source ports vary. Numeric port matches require a supported port-bearing protocol. A source-port match is appropriate in different cases, such as an explicitly defined untracked DNS response rule.

</details>


---

[Return to Learning Materials](../../../networking/calico/05-network-policy.md) | [Previous Quiz: BGP Deep Dive](./04-bgp-deep-dive-quiz.md)
