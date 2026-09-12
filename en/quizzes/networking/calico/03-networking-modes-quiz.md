# Calico Networking Modes Quiz

> **Related Document**: [Calico Networking Modes](../../../networking/calico/03-networking-modes.md)
> **Last Updated**: September 12, 2026

## Quiz

1. For Calico IPIP with an outer IPv4 header without options, how much header overhead is added?
   - A) 8 bytes
   - B) 20 bytes
   - C) 50 bytes
   - D) 100 bytes

<details>
<summary>Show Answer</summary>

**Answer: B) 20 bytes**

**Explanation:**
The added IPv4 header is 20 bytes without options. Calico IPIP is IPv4-only. Smaller headers leave more payload space but do not independently prove lower latency or higher throughput on every NIC/kernel/workload.

</details>

2. For outer-IPv4 VXLAN without extra inner VLAN tags, what overhead is added above the Pod IP packet?
   - A) 20 bytes
   - B) 30 bytes
   - C) 50 bytes
   - D) 64 bytes

<details>
<summary>Show Answer</summary>

**Answer: C) 50 bytes**

**Explanation:**
The 50 bytes are outer IPv4 20 + UDP 8 + VXLAN 8 + inner Ethernet 14. The outer Ethernet header is outside the underlay IP MTU. Outer IPv6 changes the overhead to 70 bytes. TCP and UDP also have different inner transport-header sizes.

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
CrossSubnet compares the relevant node addresses and configured subnet masks. Same-subnet inter-node traffic can avoid encapsulation, while a different node subnet uses the selected IPIP/VXLAN encapsulation. It is not an AZ/Region detector or a service that creates inter-site connectivity.

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
The underlay and return path must route Pod addresses. BGP is one approach, but static routing and supported Felix cluster-route programming can also be used. Calico 3.32's operator clusterRoutingMode can select Felix for non-VXLAN cluster routes; external BGP advertisements still require BGP.

</details>

5. Which performance comparison between IPIP and VXLAN is justified?
   - A) VXLAN is always faster
   - B) Performance depends on the actual NIC/offloads, kernel/data plane, packet sizes, routes and workload
   - C) They have identical performance
   - D) Only the Kubernetes version determines performance

<details>
<summary>Show Answer</summary>

**Answer: B) Performance depends on the actual NIC/offloads, kernel/data plane, packet sizes, routes and workload**

**Explanation:**
IPIP has a smaller IPv4 encapsulation header, while offloads and implementation details can change performance. Neither mode is universally fastest. The earlier bilingual benchmark records disagree and lack complete provenance, so they are retained as reports rather than used as performance guarantees.

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
ipipMode and vxlanMode accept Always, CrossSubnet and Never. Always concerns eligible inter-node traffic, not a same-node physical tunnel. The operator pool's separate encapsulation field uses values such as IPIPCrossSubnet or VXLANCrossSubnet; do not mix the two APIs.

</details>

7. What does the natOutgoing setting control in an IPPool?
   - A) Whether pods can receive incoming NAT traffic
   - B) Whether eligible traffic from this pool to destinations outside all Calico IPPools is source-NATed
   - C) Whether NAT is applied between pods
   - D) Whether the node performs NAT for external services

<details>
<summary>Show Answer</summary>

**Answer: B) Whether eligible traffic from this pool to destinations outside all Calico IPPools is source-NATed**

**Explanation:**
The usual predicate is destination outside all Calico IPPools, not simply outside the cluster. A disabled pool can still define a no-NAT destination range, and additional Felix exclusions can include host IPs. NAT does not authorize traffic or guarantee external return routing.

</details>

8. What is Calico's default VXLAN UDP port?
   - A) 4789
   - B) 8472
   - C) 8080
   - D) 5473

<details>
<summary>Show Answer</summary>

**Answer: A) 4789**

**Explanation:**
Calico's default is UDP 4789 and it is configurable. Other current VXLAN implementations can use 8472; it is not only an obsolete-port convention. IPIP uses IP protocol 4, which is not a TCP/UDP port.

</details>

9. Why does the Calico overlay guide prefer a suitable VXLAN configuration over IPIP for Calico-owned networking on Azure?
   - A) Azure provides VXLAN hardware acceleration
   - B) The Calico overlay guide identifies Azure as an environment where VXLAN is supported and IPIP is not
   - C) VXLAN is required by Azure policy
   - D) Azure automatically configures VXLAN

<details>
<summary>Show Answer</summary>

**Answer: B) The Calico overlay guide identifies Azure as an environment where VXLAN is supported and IPIP is not**

**Explanation:**
This is a Calico networking support boundary, not proof that every AKS deployment should install a Calico overlay. Select the actual provider CNI/policy integration. Adding a UDR does not make an unsupported IPIP encapsulation pattern supported.

</details>

10. With a real 1500-byte underlay IP MTU, outer IPv4 and no other encapsulation, what is the VXLAN Pod IP MTU budget?
   - A) Set pod MTU to 1500
   - B) 1450 bytes: 1500 minus 50
   - C) 1500, because automatic detection eliminates encapsulation overhead
   - D) Set pod MTU to 1400

<details>
<summary>Show Answer</summary>

**Answer: B) 1450 bytes: 1500 minus 50**

**Explanation:**
The IPv4 VXLAN overhead is 50, leaving 1450 bytes for the Pod IP packet under these assumptions. Outer IPv6, encryption, a smaller physical path or an eBPF Service path can change the budget. Automatic MTU detection can choose a value, but it must reflect the real modes and paths.

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
tunl0 is the usual Linux IPIP tunnel interface in this configuration. It is relevant only where IPIP is enabled/supported. It does not provide encryption and is not the interface for all Calico networking modes.

</details>

12. When migrating addresses to a different Calico IPPool, which principle is appropriate?
   - A) Directly change the IPPool configuration
   - B) Verify a compatible non-overlapping pool, control new allocations, migrate workloads/dependencies and retire the old pool only after checks
   - C) Restart all nodes simultaneously
   - D) Migration is not supported; rebuild the cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Verify a compatible non-overlapping pool, control new allocations, migrate workloads/dependencies and retire the old pool only after checks**

**Explanation:**
A CIDR/IPPool migration is different from an encapsulation-only change. Plan owner, cluster-CIDR compatibility, MTU, old explicit pool requests, remaining allocations and application rollout. Operator nodeSelector !all does not block explicit requested pools. Do not delete a pool merely because a few replacement Pods have new addresses; tunnel/other allocations and NAT/routing effects can remain.

</details>

---

[Learning material](../../../networking/calico/03-networking-modes.md) | [Previous quiz](02-architecture-quiz.md) | [Next quiz](04-bgp-deep-dive-quiz.md)
