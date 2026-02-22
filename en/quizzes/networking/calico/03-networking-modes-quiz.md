# Calico Networking Modes Quiz

> **Related Document**: [Calico Networking Modes](../../../networking/calico/03-networking-modes.md)
> **Last Updated**: February 22, 2026

## Quiz

1. What is the overhead in bytes added by IPIP encapsulation?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>Show Answer</summary>

**Answer: B) 20 bytes**

**Explanation:**
IPIP (IP-in-IP) encapsulation adds 20 bytes of overhead to each packet. This is the size of an additional IP header that wraps the original packet. This is more efficient than VXLAN which adds 50 bytes of overhead, making IPIP better for performance when encapsulation is required.

</details>

2. What is the overhead in bytes added by VXLAN encapsulation?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>Show Answer</summary>

**Answer: C) 50 bytes**

**Explanation:**
VXLAN encapsulation adds approximately 50 bytes of overhead to each packet. This includes the outer Ethernet header (14 bytes), outer IP header (20 bytes), UDP header (8 bytes), and VXLAN header (8 bytes). While this is more than IPIP's 20 bytes, VXLAN has better compatibility with various network environments.

</details>

3. What does CrossSubnet mode do in Calico?
   - A) Always uses encapsulation
   - B) Never uses encapsulation
   - C) Uses encapsulation only for cross-subnet traffic
   - D) Uses encapsulation only for same-subnet traffic

<details>
<summary>Show Answer</summary>

**Answer: C) Uses encapsulation only for cross-subnet traffic**

**Explanation:**
CrossSubnet mode is an optimization that only applies encapsulation (IPIP or VXLAN) when traffic crosses subnet boundaries. Traffic between nodes in the same subnet uses direct routing without encapsulation. This provides the best of both worlds: direct routing where possible and encapsulation only when necessary.

</details>

4. What are the requirements for Direct (unencapsulated) routing mode?
   - A) Special hardware NICs
   - B) The underlying network must be able to route pod CIDR traffic
   - C) Kernel version 5.0 or higher
   - D) eBPF mode must be enabled

<details>
<summary>Show Answer</summary>

**Answer: B) The underlying network must be able to route pod CIDR traffic**

**Explanation:**
Direct routing mode requires that the underlying network infrastructure can route the pod CIDR traffic between nodes. This typically means either using BGP to advertise pod routes to the network infrastructure, or having static routes configured. Without this, packets destined for pod IPs on other nodes would be dropped by the network.

</details>

5. Which networking mode generally provides better performance: IPIP or VXLAN?
   - A) VXLAN is always faster
   - B) IPIP is generally faster due to lower overhead
   - C) They have identical performance
   - D) Performance depends on the Kubernetes version

<details>
<summary>Show Answer</summary>

**Answer: B) IPIP is generally faster due to lower overhead**

**Explanation:**
IPIP generally provides better performance than VXLAN because it has lower encapsulation overhead (20 bytes vs 50 bytes). Less overhead means more space for actual payload data and less processing required for encapsulation/decapsulation. However, VXLAN has broader compatibility and better hardware offload support.

</details>

6. What are the valid options for ipipMode in an IPPool?
   - A) On, Off
   - B) True, False
   - C) Always, CrossSubnet, Never
   - D) Enabled, Disabled, Auto

<details>
<summary>Show Answer</summary>

**Answer: C) Always, CrossSubnet, Never**

**Explanation:**
The ipipMode field in an IPPool accepts three values: `Always` (always use IPIP encapsulation), `CrossSubnet` (use IPIP only for cross-subnet traffic), and `Never` (disable IPIP). These same options are also available for vxlanMode to configure VXLAN encapsulation behavior.

</details>

7. What does the natOutgoing setting control in an IPPool?
   - A) Whether pods can receive incoming NAT traffic
   - B) Whether pod traffic leaving the cluster is masqueraded
   - C) Whether NAT is applied between pods
   - D) Whether the node performs NAT for external services

<details>
<summary>Show Answer</summary>

**Answer: B) Whether pod traffic leaving the cluster is masqueraded**

**Explanation:**
The `natOutgoing` setting controls whether traffic from pods in this IP pool is masqueraded (SNAT) when leaving the cluster. When set to true, the source IP of outgoing traffic is changed to the node's IP, allowing pods to communicate with external resources even when pod IPs are not routable outside the cluster.

</details>

8. What UDP port does VXLAN use by default?
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>Show Answer</summary>

**Answer: A) 4789**

**Explanation:**
VXLAN uses UDP port 4789 by default, as specified by IANA. This is the standard port used across different VXLAN implementations. Some older implementations (like early Flannel versions) used port 8472, but Calico follows the standard port 4789.

</details>

9. Why might VXLAN be preferred over IPIP in Azure environments?
   - A) Azure provides VXLAN hardware acceleration
   - B) IPIP (IP protocol 4) is not well supported in Azure
   - C) VXLAN is required by Azure policy
   - D) Azure automatically configures VXLAN

<details>
<summary>Show Answer</summary>

**Answer: B) IPIP (IP protocol 4) is not well supported in Azure**

**Explanation:**
Azure has limited support for IPIP encapsulation because IP protocol 4 may be blocked or have issues in Azure's network. VXLAN, being UDP-based, works more reliably in Azure environments. This is a common recommendation when deploying Calico on Azure Kubernetes Service (AKS) or Azure VMs.

</details>

10. How should MTU be optimized when using VXLAN encapsulation with a standard 1500 byte network MTU?
    - A) Set pod MTU to 1500
    - B) Set pod MTU to 1450 (1500 - 50 bytes overhead)
    - C) MTU adjustment is automatic
    - D) Set pod MTU to 1400

<details>
<summary>Show Answer</summary>

**Answer: B) Set pod MTU to 1450 (1500 - 50 bytes overhead)**

**Explanation:**
When using VXLAN with a 1500 byte network MTU, the pod MTU should be set to approximately 1450 bytes (1500 - 50 bytes VXLAN overhead) to avoid fragmentation. For IPIP, the pod MTU would be 1480 bytes (1500 - 20 bytes overhead). Proper MTU configuration prevents performance issues caused by packet fragmentation.

</details>

11. What interface is created on nodes when IPIP mode is enabled?
    - A) vxlan.calico
    - B) tunl0
    - C) cali0
    - D) ipip0

<details>
<summary>Show Answer</summary>

**Answer: B) tunl0**

**Explanation:**
When IPIP mode is enabled, Calico creates a `tunl0` tunnel interface on each node. This interface is used for IPIP encapsulation of traffic between nodes. The tunl0 interface handles the encapsulation and decapsulation of packets as they enter and leave the IPIP tunnel.

</details>

12. What is the best practice for migrating from IPIP to VXLAN mode in a running cluster?
    - A) Directly change the IPPool configuration
    - B) Create a new IPPool with VXLAN, migrate workloads, then delete the old pool
    - C) Restart all nodes simultaneously
    - D) Migration is not supported; rebuild the cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Create a new IPPool with VXLAN, migrate workloads, then delete the old pool**

**Explanation:**
The recommended approach for migrating between encapsulation modes is to create a new IPPool with the desired settings, gradually migrate workloads to use the new pool (by recreating pods or using node selectors), and then delete the old pool once migration is complete. This approach minimizes disruption and allows for rollback if issues occur.

</details>

---

[Return to Learning Materials](../../../networking/calico/03-networking-modes.md) | [Previous Quiz: Architecture](./02-architecture-quiz.md) | [Next Quiz: BGP Deep Dive](./04-bgp-deep-dive-quiz.md)
