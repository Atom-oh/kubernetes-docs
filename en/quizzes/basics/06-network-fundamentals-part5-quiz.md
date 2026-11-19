# Network Fundamentals Part 5 Quiz: Network Devices, LAN and WAN

> **Last Updated**: November 19, 2026

Tests your understanding of device forwarding decisions, VLANs and redundancy, LAN topologies, NAT, WAN types and their cloud counterparts.

## Multiple Choice Questions

1. Which statement correctly describes the decision an L2 switch makes within a VLAN and a router makes between subnets?
   - A) Both look up the longest-prefix route for the destination IP
   - B) The switch looks up the destination MAC in its MAC table to pick a port; the router looks up the destination IP in its FIB, decrements TTL by 1 and writes a new L2 header
   - C) The switch decrements TTL and the router learns source MACs
   - D) The router always replaces IP addresses with its own

<details>
<summary>Show Answer</summary>

**Answer: B) The switch looks up the destination MAC in its MAC table to pick a port; the router looks up the destination IP in its FIB, decrements TTL by 1 and writes a new L2 header**

**Explanation:**
An L2 switch learns source MACs, picks a port by destination MAC and VLAN, and does not change the frame. A router forwards to the next hop of the longest-prefix route, decrements TTL and writes new source and destination MACs. Without NAT the IP addresses stay the same, so D is wrong.

</details>

2. Two switches are connected by an 802.1Q trunk, both have ports in VLAN 10 and VLAN 20, and one router routes between the two VLANs. How many broadcast domains are there?
   - A) 1
   - B) 2
   - C) 4
   - D) One per switch port

<details>
<summary>Show Answer</summary>

**Answer: B) 2**

**Explanation:**
One VLAN is one broadcast domain, and a VLAN that spans several switches over trunks is still one broadcast domain. The router does not forward a packet received as an L2 broadcast to other interfaces (RFC 1812 §5.3.4), so there are two: VLAN 10 and VLAN 20. One per switch port describes collision domains.

</details>

3. Which statement about the native VLAN on an 802.1Q trunk is correct?
   - A) Native VLAN frames always carry a VID 4095 tag
   - B) The native VLAN may differ between the two ends without any problem
   - C) It is the VLAN that crosses the trunk untagged; on Cisco Catalyst it defaults to VLAN 1, and both ends must match
   - D) The native VLAN only applies to access ports

<details>
<summary>Show Answer</summary>

**Answer: C) It is the VLAN that crosses the trunk untagged; on Cisco Catalyst it defaults to VLAN 1, and both ends must match**

**Explanation:**
The device places untagged frames received on a trunk into the native VLAN and sends native-VLAN frames untagged. If the two ends differ, frames from one VLAN land in another, breaking separation, and spanning-tree loops may result. VIDs 0 and 4095 are reserved and are not used for VLANs.

</details>

4. What is the root reason STP is needed, and how is the root bridge elected?
   - A) Ethernet headers have no TTL, so frames in an L2 loop never die; STP blocks some ports, and the switch with the lowest bridge ID (priority + MAC) becomes root
   - B) To raise IP TTL; the switch with the most ports becomes root
   - C) To combine link bandwidth; the switch with the highest MAC becomes root
   - D) To route between VLANs; the switch with the highest priority value becomes root

<details>
<summary>Show Answer</summary>

**Answer: A) Ethernet headers have no TTL, so frames in an L2 loop never die; STP blocks some ports, and the switch with the lowest bridge ID (priority + MAC) becomes root**

**Explanation:**
With a loop, broadcasts keep circulating and multiplying and MAC tables flap. STP blocks some redundant links to form a tree. The default priority is 32768, so with no configuration the switch with the lowest MAC becomes root; in practice you lower the priority on core or distribution switches to pin the root. Combining bandwidth is LACP's job.

</details>

5. In a LAG that bundles four 10 Gbps links with LACP, what is the maximum throughput of a single TCP connection?
   - A) 40 Gbps: a LAG spreads packets evenly over all links
   - B) Up to 10 Gbps: hashing keeps one flow on the same member link
   - C) 20 Gbps: transmit and receive use different links
   - D) 10 Gbps regardless of the LAG, because STP blocks three links

<details>
<summary>Show Answer</summary>

**Answer: B) Up to 10 Gbps: hashing keeps one flow on the same member link**

**Explanation:**
Link aggregation hashes values such as addresses and ports to assign frames to one member link, so a flow stays on one link. The 40 Gbps aggregate is usable only with many flows. STP sees the LAG as one link and does not block its members.

</details>

6. In VRRPv3, a backup router has priority 100 and the default 1 s advertisement interval. Roughly how long after the Active router stops does the backup take over?
   - A) About 1 s
   - B) About 3.61 s
   - C) About 10 s
   - D) About 30 s

<details>
<summary>Show Answer</summary>

**Answer: B) About 3.61 s**

**Explanation:**
`Active_Down_Interval = 3 × advertisement interval + Skew_Time`, with `Skew_Time = ((256 − priority) × advertisement interval) / 256`. (256 − 100) / 256 ≈ 0.61 s, so 3 + 0.61 ≈ 3.61 s. 10 s is HSRP's default hold time and 30 s is 802.1D STP's listening plus learning time.

</details>

7. Thousands of Pods call the same external API (one IP:443) through one AWS NAT gateway with one public IPv4 address, and new connections start failing. What is the most likely cause and response?
   - A) Widen the NAT gateway's security group
   - B) The limit of 55,000 simultaneous connections per public IP per unique destination may have been reached; check `ErrorPortAllocation` and consider connection reuse, secondary IPs and spreading load over NAT gateways
   - C) NAT gateways have no connection limit, so the external API must be failing
   - D) Deny port 443 in the NACL

<details>
<summary>Show Answer</summary>

**Answer: B) The limit of 55,000 simultaneous connections per public IP per unique destination may have been reached; check `ErrorPortAllocation` and consider connection reuse, secondary IPs and spreading load over NAT gateways**

**Explanation:**
A unique destination is a destination IP, port and protocol combination, so traffic concentrated on one API hits the limit first. Up to 8 IPv4 addresses can be associated, and `ErrorPortAllocation` goes above zero when a source port cannot be allocated. You cannot attach a security group to a NAT gateway, so A is wrong.

</details>

8. Which address range is allocated for the segment between a carrier's CGNAT and the customer premises equipment (CPE), and what is it?
   - A) `172.16.0.0/12`: RFC 1918 private space
   - B) `169.254.0.0/16`: link-local space
   - C) `100.64.0.0/10`: the RFC 6598 Shared Address Space, separate from RFC 1918
   - D) `203.0.113.0/24`: a public range reserved for CGNAT

<details>
<summary>Show Answer</summary>

**Answer: C) `100.64.0.0/10`: the RFC 6598 Shared Address Space, separate from RFC 1918**

**Explanation:**
RFC 6598 allocated `100.64.0.0/10` for CGN deployments so that it does not collide with whatever RFC 1918 range the subscriber uses inside. Packets and routes for this range must not cross provider boundaries. `203.0.113.0/24` is an RFC 5737 documentation range.

</details>

9. An instance calls an external HTTPS API. Its security group allows outbound 443; the subnet's custom NACL allows only outbound 443 and denies all inbound by default. Why does the reply not arrive?
   - A) Security groups are stateless, so inbound 443 must be allowed separately
   - B) NACLs are stateless, so the ephemeral ports the reply returns to (for example Linux 32768–61000) must be allowed inbound
   - C) NACLs evaluate every rule and then apply only allow rules
   - D) Deny rules take precedence in security groups

<details>
<summary>Show Answer</summary>

**Answer: B) NACLs are stateless, so the ephemeral ports the reply returns to (for example Linux 32768–61000) must be allowed inbound**

**Explanation:**
Security groups are stateful, allow return traffic automatically and have allow rules only. A NACL is a stateless subnet-level filter that evaluates allow and deny rules in ascending rule number, applies the first match, and needs return traffic allowed explicitly.

</details>

10. In a two-tier spine-leaf fabric where every leaf connects to every spine and leaves are not linked to each other, which switch path does traffic take between two servers on different leaves?
    - A) leaf → leaf
    - B) leaf → spine → leaf (three switches, two switch-to-switch links)
    - C) leaf → spine → spine → leaf
    - D) It depends on server placement and is unpredictable

<details>
<summary>Show Answer</summary>

**Answer: B) leaf → spine → leaf (three switches, two switch-to-switch links)**

**Explanation:**
Because leaves are not linked to each other and neither are spines, traffic to another leaf always crosses exactly one spine. Every server pair is the same distance apart, so latency is predictable, and ECMP uses all spine paths at once.

</details>

11. Two customers both use the private range `10.0.0.0/16`. Why do their routes not mix inside the carrier's MPLS L3VPN?
    - A) The carrier translates customer addresses with CGNAT
    - B) PE routers bind customer attachments to separate VRFs and prefix customer routes with a Route Distinguisher
    - C) An SD-WAN controller blocks duplicate addresses
    - D) Leased lines physically separate customers

<details>
<summary>Show Answer</summary>

**Answer: B) PE routers bind customer attachments to separate VRFs and prefix customer routes with a Route Distinguisher**

**Explanation:**
In RFC 4364 BGP/MPLS IP VPNs, PE routers bind customer attachment circuits to separate routing tables called VRFs, and prefix customer routes carried in BGP with a Route Distinguisher to form distinct VPN-IPv4 addresses, so overlapping private addresses between customers do not mix. SD-WAN is an overlay service model on top of circuits, and a leased line is a point-to-point circuit, a different service from MPLS L3VPN.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part5.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
