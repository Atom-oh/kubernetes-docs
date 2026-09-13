# Calico Glossary Quiz

> **Related Document**: [Calico Glossary](../../../networking/calico/glossary.md)
> **Last Updated**: September 12, 2026

## Quiz

1. What is Felix's primary role in Calico's architecture?
   - A) Managing the etcd database
   - B) Programming network policy rules and routes on each node
   - C) Load balancing service traffic
   - D) Providing DNS resolution for services

<details>
<summary>Show Answer</summary>

**Answer: B) Programming network policy rules and routes on each node**

**Explanation:**
Felix programs the selected policy dataplane and relevant routes on each node. The CNI plugin creates/configures ordinary Pod interfaces and invokes IPAM; Felix tracks endpoint state and programs rules rather than forwarding each packet in userspace.

</details>

2. What does BIRD stand for and what is its function in Calico?
   - A) Binary Internet Routing Daemon - manages container DNS
   - B) BIRD Internet Routing Daemon - distributes routing information via BGP
   - C) Basic Internal Route Distribution - handles service discovery
   - D) Broadcast IP Routing Distributor - manages multicast traffic

<details>
<summary>Show Answer</summary>

**Answer: B) BIRD Internet Routing Daemon - distributes routing information via BGP**

**Explanation:**
BIRD exchanges routes in BGP-enabled Calico profiles. The routing/encapsulation design determines whether traffic uses direct routing or a tunnel; BGP presence alone does not mean there is no overlay.

</details>

3. What is Typha's function in Calico deployments?
   - A) Encrypting pod-to-pod traffic
   - B) Caching and fanning out datastore updates to Felix instances
   - C) Providing ingress load balancing
   - D) Managing certificate rotation

<details>
<summary>Show Answer</summary>

**Answer: B) Caching and fanning out datastore updates to Felix instances**

**Explanation:**
Typha caches and distributes datastore changes to Felix, reducing per-client watch load. It can have multiple replicas and syncer/watch types; it is not a single universal watch or a policy-federation service. The operator manages scaling for the installed profile.

</details>

4. What is the difference between an IPPool and IPAM in Calico?
   - A) They are the same thing with different names
   - B) IPPool defines available CIDR ranges; IPAM manages allocation from those ranges
   - C) IPPool is for IPv4, IPAM is for IPv6
   - D) IPPool is deprecated in favor of IPAM

<details>
<summary>Show Answer</summary>

**Answer: B) IPPool defines available CIDR ranges; IPAM manages allocation from those ranges**

**Explanation:**
IPPool defines an address range plus encapsulation, NAT and allocation eligibility. Calico IPAM allocates from eligible pools for supported uses. This is not the allocator used by VPC CNI policy-only, and an IPPool is not a Kubernetes Node PodCIDR alias.

</details>

5. How does GlobalNetworkPolicy differ from Kubernetes NetworkPolicy?
   - A) GlobalNetworkPolicy only works with IPv6
   - B) GlobalNetworkPolicy is cluster-scoped and supports additional features like tiers and deny rules
   - C) GlobalNetworkPolicy is namespace-scoped like Kubernetes NetworkPolicy
   - D) GlobalNetworkPolicy is deprecated

<details>
<summary>Show Answer</summary>

**Answer: B) GlobalNetworkPolicy is cluster-scoped and supports additional features like tiers and deny rules**

**Explanation:**
GlobalNetworkPolicy is cluster-scoped, with selectors defining which workloads or host endpoints it affects. It adds Calico actions/order/tiers; it does not automatically affect every Pod or enable L7 inspection without the required integration.

</details>

6. What is a Tier in Calico's policy model?
   - A) A network segment for isolating traffic
   - B) A hierarchical grouping that controls policy evaluation order
   - C) A pricing level for Calico Enterprise
   - D) A type of network encryption

<details>
<summary>Show Answer</summary>

**Answer: B) A hierarchical grouping that controls policy evaluation order**

**Explanation:**
Tiers group policies by priority. Lower numeric tier order is evaluated first, then policy order within the tier. Allow/Deny is terminal; Pass delegates to the next applicable tier and eventually profiles. Example security/platform/application names are user-defined, not a required default hierarchy.

</details>

7. What does a WorkloadEndpoint represent in Calico?
   - A) A Kubernetes Service endpoint
   - B) A network interface associated with a pod or VM workload
   - C) An external API endpoint
   - D) A storage mount point

<details>
<summary>Show Answer</summary>

**Answer: B) A network interface associated with a pod or VM workload**

**Explanation:**
A WorkloadEndpoint represents a workload interface with IP/MAC/interface information, labels and profile references used to calculate policy. Its lifecycle is normally plugin/orchestrator-managed. It is not a Service EndpointSlice or a stored list of all effective policy decisions.

</details>

8. What is the relationship between BGPPeer and BGPConfiguration in Calico?
   - A) They are aliases for the same resource
   - B) BGPConfiguration sets global BGP settings; BGPPeer defines specific peering sessions
   - C) BGPPeer is for internal peers, BGPConfiguration for external
   - D) BGPConfiguration is deprecated in favor of BGPPeer

<details>
<summary>Show Answer</summary>

**Answer: B) BGPConfiguration sets global BGP settings; BGPPeer defines specific peering sessions**

**Explanation:**
BGPConfiguration default defines cluster defaults such as ASN and mesh/service advertisement settings; supported node overrides are separate. BGPPeer identifies intended peering relationships by peer address or selectors. It does not guarantee the session or required routes are established.

</details>

9. What is a NetworkSet in Calico, and what is its Cilium equivalent?
   - A) A group of Services; equivalent to Cilium ServiceGroup
   - B) A labeled IP/CIDR set; CiliumCIDRGroup with CIDR policy references is a related concept
   - C) A collection of namespaces; equivalent to Cilium ClusterPolicy
   - D) A DNS zone configuration; equivalent to Cilium DNSPolicy

<details>
<summary>Show Answer</summary>

**Answer: B) A labeled IP/CIDR set; CiliumCIDRGroup with CIDR policy references is a related concept**

**Explanation:**
Calico NetworkSet is namespaced, while GlobalNetworkSet is cluster-scoped; both provide labeled IP/CIDR sets. CiliumCIDRGroup is cluster-scoped and can be referenced through cidrGroupRef or cidrGroupSelector in Cilium CIDR rules. These are related concepts with different APIs, not DNS rules or interchangeable manifests.

</details>

10. What is the purpose of a HostEndpoint in Calico?
    - A) To define container endpoints
    - B) To apply network policies to host interfaces (non-pod traffic)
    - C) To configure DNS for the host
    - D) To manage node labels

<details>
<summary>Show Answer</summary>

**Answer: B) To apply network policies to host interfaces (non-pod traffic)**

**Explanation:**
A HostEndpoint represents a host interface for policy on host traffic and, when configured, forwarded traffic. Review profiles, failsafes and management paths before creating/enforcing one. Workload and host policy scopes are distinct but forwarded Pod traffic can also be affected.

</details>
