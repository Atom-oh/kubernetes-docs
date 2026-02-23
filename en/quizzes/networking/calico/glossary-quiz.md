# Calico Glossary Quiz

> **Related Document**: [Calico Glossary](../../../networking/calico/glossary.md)
> **Last Updated**: February 22, 2026

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
Felix is Calico's per-node agent (runs as a DaemonSet) responsible for programming network policy rules (iptables or eBPF), routes, and ACLs on each node. It watches the datastore for policy and endpoint updates and translates them into kernel-level rules.

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
BIRD (BIRD Internet Routing Daemon - a recursive acronym) is the BGP daemon used by Calico to distribute routing information between nodes. It establishes BGP peering sessions and advertises pod CIDR routes, enabling direct pod-to-pod communication without overlay encapsulation.

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
Typha acts as a caching proxy between Felix instances and the datastore (Kubernetes API or etcd). It reduces datastore load by aggregating watches from multiple Felix instances into a single watch, then distributing updates to all connected Felix daemons.

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
An IPPool is a Calico resource that defines a range of IP addresses (CIDR) available for pod allocation, along with configuration like NAT and encapsulation settings. IPAM (IP Address Management) is the system that manages the actual allocation of individual IPs from these pools to pods and nodes.

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
GlobalNetworkPolicy is a Calico-specific resource that applies cluster-wide without namespace restrictions. Unlike Kubernetes NetworkPolicy, it supports explicit deny rules, policy tiers for ordering, application-layer (L7) rules, and selectors for non-namespaced resources like HostEndpoints.

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
Tiers provide a way to organize and order Calico network policies. Policies in higher-order tiers are evaluated before lower-order tiers. This enables patterns like platform-level security policies that take precedence over application-team policies, supporting multi-tenant policy management.

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
A WorkloadEndpoint represents a network interface attached to a workload (pod, VM, or container). It contains information about the interface's IP addresses, the host it runs on, labels for policy selection, and the profile/policies applied to it. Calico automatically creates WorkloadEndpoints for pods.

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
BGPConfiguration is a global resource that defines cluster-wide BGP settings like the AS number, node-to-node mesh enablement, and logging. BGPPeer resources define specific BGP peering relationships with external routers or route reflectors, including their IP addresses, AS numbers, and node selectors.

</details>

9. What is a NetworkSet in Calico, and what is its Cilium equivalent?
   - A) A group of Services; equivalent to Cilium ServiceGroup
   - B) A named set of IP addresses/CIDRs for use in policies; similar to Cilium CiliumNetworkPolicy with CIDR rules
   - C) A collection of namespaces; equivalent to Cilium ClusterPolicy
   - D) A DNS zone configuration; equivalent to Cilium DNSPolicy

<details>
<summary>Show Answer</summary>

**Answer: B) A named set of IP addresses/CIDRs for use in policies; similar to Cilium CiliumNetworkPolicy with CIDR rules**

**Explanation:**
A NetworkSet is a Calico resource that defines a named collection of IP addresses, CIDRs, or domains that can be referenced in network policies. This simplifies policy management when the same set of external IPs appears in multiple policies. Cilium achieves similar functionality through CIDR-based rules in CiliumNetworkPolicy.

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
A HostEndpoint represents a network interface on a host node itself (not a pod). It enables Calico network policies to control traffic to and from host processes, protecting node-level services like kubelet, SSH, or other system daemons that don't run as pods.

</details>
