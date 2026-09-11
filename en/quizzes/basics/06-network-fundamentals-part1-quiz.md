# Network Fundamentals Part 1 Quiz — Layer Model, Link and Routing

> **Last Updated**: September 11, 2026

Tests your understanding of the 11 link-layer and internet/routing-layer protocols and mechanisms.

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
Encapsulation reduces the inner packet size that fits the path. IPv4 packets with DF set cannot be fragmented by routers; classical PMTUD needs ICMP Type 3 Code 4. IPv6 routers never fragment and use ICMPv6 Packet Too Big (Type 2). Blocking those messages can cause black holes, although PLPMTUD can probe sizes without relying on ICMP.

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
The VIP remains, but its owner or MAC/port location changes. Gratuitous ARP announces the IP-to-MAC mapping to neighbors, while the switch can learn the source MAC on its new port. Some HA designs keep the same virtual MAC. If this refresh is delayed, failover cutover is slow.

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
OSPF is a link-state IGP: every router in an area shares the same topology and computes shortest paths on it. BGP is a path-vector protocol that picks "the path policy prefers" using attributes such as AS_PATH, Local Preference, and MED. Direct Connect uses BGP; Site-to-Site VPN supports BGP or static routing in supported configurations. BGP also has intra-AS iBGP sessions.

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
Port-translating NAT (PAT/NAPT) rewrites not just IP addresses but ports, and depends on a per-session mapping table. As a result direct P2P connections became hard, and WebRTC works around it with STUN/TURN (ICE). In the cloud, NAT Gateway port exhaustion and data processing charges are the practical issues.

</details>

5. In an organization adopting IPv6 via dual stack, which security gap should be checked?
   - A) IPv6 does not support encryption
   - B) Only IPv4 firewall rules are maintained, and rules for the IPv6 path are missing
   - C) IPv6 addresses are easier to scan
   - D) SLAAC disables the DHCP server

<details>
<summary>Show Answer</summary>

**Answer: B) Only IPv4 firewall rules are maintained, and rules for the IPv6 path are missing**

**Explanation:**
Dual stack means maintaining two sets of firewall rules and security policies. Missing IPv6 rules is a risk, but an IPv6 address alone does not imply internet reachability. Routes, security groups and NACLs still apply; an egress-only internet gateway can prevent unsolicited inbound IPv6 connections.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part1.md) | [Next Quiz: Part 2](./06-network-fundamentals-part2-quiz.md)

## Verification References

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html
- https://www.rfc-editor.org/rfc/rfc894
- https://www.rfc-editor.org/rfc/rfc6691
- https://www.rfc-editor.org/rfc/rfc4638
- https://www.rfc-editor.org/rfc/rfc5227
- https://www.rfc-editor.org/rfc/rfc792
- https://www.rfc-editor.org/rfc/rfc8899
- https://www.rfc-editor.org/rfc/rfc2328
- https://www.rfc-editor.org/rfc/rfc6811
- https://docs.kernel.org/networking/bridge.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html
- https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
