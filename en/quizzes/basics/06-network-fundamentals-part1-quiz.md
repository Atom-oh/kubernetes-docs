# Network Fundamentals Part 1 Quiz — Layer Model, Link and Routing

> **Last Updated**: September 14, 2026

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

6. For `192.0.2.130/26` on an ordinary IPv4 broadcast subnet, which network, broadcast and host range are correct?
   - A) Network `.0`, broadcast `.255`, hosts `.1`–`.254`
   - B) Network `.130`, broadcast `.193`, hosts `.131`–`.192`
   - C) Network `.128`, broadcast `.191`, hosts `.129`–`.190`
   - D) Network `.128`, broadcast `.190`, hosts `.129`–`.189`

<details>
<summary>Show Answer</summary>

**Answer: C) Network `.128`, broadcast `.191`, hosts `.129`–`.190`**

**Explanation:**
The mask is `255.255.255.192`. Six host bits give 64 addresses, and `.130` lies in the block `.128`–`.191`. Reserving the network and broadcast addresses leaves 62 ordinary host addresses. All addresses here share the `192.0.2` prefix and are documentation examples.

</details>

7. A host at `192.0.2.130/26` has an on-link route for its subnet. Its selected routing table also has `198.51.100.0/24` via `.129`, `198.51.100.128/25` via `.190`, and a default via `.129` (gateways are in `192.0.2`). For destination `198.51.100.140`, which route and ARP target apply if the neighbor entry is missing?
   - A) Default route; ARP for `192.0.2.129`
   - B) `/25` route; ARP for `192.0.2.190`
   - C) `/24` route; ARP for `198.51.100.140`
   - D) `/25` route; ARP for `198.51.100.140`

<details>
<summary>Show Answer</summary>

**Answer: B) `/25` route; ARP for `192.0.2.190`**

**Explanation:**
All three remote routes match, but `/25` is the longest prefix. ARP resolves the on-link gateway, so the frame goes to that gateway's MAC while the IP destination remains `198.51.100.140` (absent NAT). A lower default-route metric would not override the more specific match.

</details>

8. A host at `192.0.2.130/26` has an on-link `192.0.2.128/26` route and a default via `192.0.2.129`. With no more specific route or cached neighbor entry, how does it send to `192.0.2.150`?
   - A) ARP for `192.0.2.150`, then send directly to its MAC
   - B) ARP for `192.0.2.129`, because all IP traffic requires a gateway
   - C) ARP for `192.0.2.191`, then broadcast the IP packet
   - D) Send to the default gateway without any link-layer destination

<details>
<summary>Show Answer</summary>

**Answer: A) ARP for `192.0.2.150`, then send directly to its MAC**

**Explanation:**
The selected `/26` route marks this destination as on-link. The destination host itself is the next hop. A configured default gateway is used only when the route lookup selects it; merely having one does not force local traffic through it.

</details>

9. Which statement correctly handles exceptions to the ordinary “total addresses minus two” calculation?
   - A) A `/31` always has zero usable endpoints
   - B) A `/32` always provides a host and a separate gateway address
   - C) Every cloud `/26` allows assignment of all 62 ordinary host addresses
   - D) A supported point-to-point `/31` uses both addresses; a `/32` identifies one address; cloud reservations require a separate check

<details>
<summary>Show Answer</summary>

**Answer: D) A supported point-to-point `/31` uses both addresses; a `/32` identifies one address; cloud reservations require a separate check**

**Explanation:**
RFC 3021 permits the two `/31` addresses as point-to-point endpoints. A `/32` host route matches one address and does not itself establish on-link reachability. Standard AWS VPC IPv4 subnets reserve five addresses, so a `/26` has 59 assignable addresses; modes such as BYOIP have different rules.

</details>

10. A UDP traceroute receives ICMP Type 11 Code 0 from an intermediate router, then Type 3 Code 3 from the destination. What does this normally mean?
   - A) A probe's TTL expired in transit; a later probe reached an unused UDP port at the destination
   - B) The destination replied with UDP data at every hop
   - C) The router reported a path-MTU problem, then the destination completed TLS
   - D) Traceroute silently changed all outgoing probes to ICMP Echo Requests

<details>
<summary>Show Answer</summary>

**Answer: A) A probe's TTL expired in transit; a later probe reached an unused UDP port at the destination**

**Explanation:**
The probe protocol and response protocol differ: UDP probes can elicit ICMP errors. ICMP Echo and TCP SYN traceroute variants also use Time Exceeded at intermediate hops, but their final responses can be Echo Reply or TCP SYN/ACK/RST. Fragmentation Needed is Type 3 Code 4, not either code in this question.

</details>

11. One traceroute hop shows `* * *`, while later hops and the destination reply. Which conclusion is justified?
   - A) The silent router drops all end-to-end traffic
   - B) No matching response arrived for those probes within the wait; more evidence is needed to claim end-to-end loss
   - C) The forward and return paths are identical
   - D) Every application packet size fits the path MTU

<details>
<summary>Show Answer</summary>

**Answer: B) No matching response arrived for those probes within the wait; more evidence is needed to claim end-to-end loss**

**Explanation:**
Filtering, response suppression/rate limiting or loss on the return path can produce timeouts. Compare repeated probes with destination and application results. RTT includes the return path, and success with small probes does not rule out a PMTU black hole for larger packets.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part1.md) | [Next Quiz: Part 2](./06-network-fundamentals-part2-quiz.md)

Review the [CIDR example](../../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet), [next-hop reasoning](../../basics/06-network-fundamentals-part1.md#longest-prefix-next-hop) and [ICMP interpretation](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation), including their primary references.

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
