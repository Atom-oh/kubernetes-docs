# Network Fundamentals Part 1 Quiz — Layer Model, Link and Routing

> **Last Updated**: August 28, 2026

Tests your understanding of the 11 link-layer and internet/routing-layer protocols.

## Multiple Choice Questions

1. On a VPN or overlay network, you hit a failure where "ping works, but large responses hang." What should you suspect first?
   - A) The DNS TTL is too long
   - B) Reduced effective MTU from encapsulation headers plus blocked ICMP (an MTU black hole)
   - C) Mismatched TCP congestion control algorithms
   - D) ARP cache expiry

<details>
<summary>Show Answer</summary>

**Answer: B) Reduced effective MTU from encapsulation headers plus blocked ICMP (an MTU black hole)**

**Explanation:**
Overlay/VPN encapsulation headers shrink the effective MTU. Small packets (pings) get through, but packets above the MTU need fragmentation — and if ICMP Fragmentation Needed (Type 3 Code 4) is blocked, Path MTU Discovery cannot work, so large responses silently disappear.

</details>

2. In a VIP-based HA setup, why does the new active node send a Gratuitous ARP right after failover?
   - A) To re-register its IP address with the DHCP server
   - B) To refresh the MAC tables/ARP caches of switches and neighboring hosts to point at the new node
   - C) To force the gateway to recompute its routing table
   - D) To renegotiate TLS sessions

<details>
<summary>Show Answer</summary>

**Answer: B) To refresh the MAC tables/ARP caches of switches and neighboring hosts to point at the new node**

**Explanation:**
The VIP stays the same but the node (MAC) that owns it has changed, so the new active node broadcasts a Gratuitous ARP to update the caches of surrounding devices. If this refresh is delayed, failover cutover is slow.

</details>

3. Which statement most accurately describes the difference between OSPF and BGP?
   - A) OSPF does policy-based path selection, while BGP focuses on shortest-path computation
   - B) OSPF is for inter-AS routing, while BGP is for intra-AS routing
   - C) OSPF computes shortest paths with Dijkstra inside an AS, while BGP selects paths between ASes based on policy
   - D) Both are link-state protocols and differ only in where they are used

<details>
<summary>Show Answer</summary>

**Answer: C) OSPF computes shortest paths with Dijkstra inside an AS, while BGP selects paths between ASes based on policy**

**Explanation:**
OSPF is a link-state IGP: every router in an area shares the same topology and computes shortest paths on it. BGP is a path-vector protocol that picks "the path policy prefers" using attributes such as AS_PATH, Local Preference, and MED. Route exchange over Direct Connect and Site-to-Site VPN is also BGP.

</details>

4. Which best explains why NAT is said to "violate the layering model"?
   - A) Because it directly modifies link-layer frames
   - B) Because it is an L3 device that rewrites L4 ports, and it breaks the premise of end-to-end connectivity
   - C) Because it decrypts encrypted packets
   - D) Because it does not use routing tables

<details>
<summary>Show Answer</summary>

**Answer: B) Because it is an L3 device that rewrites L4 ports, and it breaks the premise of end-to-end connectivity**

**Explanation:**
NAT (PAT/NAPT) rewrites not just IP addresses but ports, and depends on a per-session mapping table. As a result direct P2P connections became hard, and WebRTC works around it with STUN/TURN (ICE). In the cloud, NAT Gateway port exhaustion and data processing charges are the practical issues.

</details>

5. In an organization adopting IPv6 via dual stack, what is the most common security gap?
   - A) IPv6 does not support encryption
   - B) Only IPv4 firewall rules are maintained, and rules for the IPv6 path are missing
   - C) IPv6 addresses are easier to scan
   - D) SLAAC disables the DHCP server

<details>
<summary>Show Answer</summary>

**Answer: B) Only IPv4 firewall rules are maintained, and rules for the IPv6 path are missing**

**Explanation:**
Dual stack means maintaining two sets of firewall rules and security policies. Missing rules on the IPv6 path is a common gap — and note that in the cloud IPv6 works without NAT, so "directly reachable from the internet" becomes the default posture.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part1.md) | [Next Quiz: Part 2](./06-network-fundamentals-part2-quiz.md)
