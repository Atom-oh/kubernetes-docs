# Network Fundamentals Part 1 — The Layer Model, Link and Routing Layers

> **Last Updated**: September 11, 2026

::: tip This is a four-part series
**Part 1: The Layer Model, Link and Routing Layers** *(this document)* ·
[Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md) ·
[Part 3: Application Protocols](./06-network-fundamentals-part3.md) ·
[Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
:::

A browser request relies on several cooperating protocols. The exact sequence depends on caches, connection reuse, IP version and HTTP version, so troubleshooting needs to examine more than HTTP alone.

This series walks through 25 networking protocols and mechanisms, **layer by layer, from the bottom up**. The reason for building from the bottom is simple: every upper layer is designed on the assumption that the layers below it already work. Read top-down and you keep hitting "but how does *that* part work?"

Each entry follows the same shape: **one-line definition → how it works → where it bites in practice**.

---

## 0. The Layer Map on One Page

| Layer | Job | Protocols covered here |
|---|---|---|
| Application | Actual service semantics | HTTP/3, WebSocket, WebRTC, gRPC, DNS, DoH, DHCP, MQTT, SSH, SMTP |
| Security | Encryption and authentication (rides on transport) | TLS |
| Transport | End-to-end data delivery | TCP, UDP, QUIC |
| Internet / Routing | Choosing paths between networks | IPv4, IPv6, ICMP, BGP, OSPF, NAT |
| Link | Delivery within one physical segment | Ethernet, Wi-Fi, VLAN, PPP, ARP |

A few entries refuse to respect clean layer boundaries. TLS sits wedged between transport and application, QUIC rides on UDP while doing a transport layer's job, and ARP bridges IP and the link layer. NAT is less a protocol than a function. These "exceptions" account for most real-world troubleshooting.

---

![Shows the link/routing-layer path from a laptop through an L2 switch and home router to the ISP edge, the BGP-driven internet core, an OSPF data-center router, and finally the server, with each segment's protocol and MTU.](../.gitbook/assets/en-basics-06-network-fundamentals-part1-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part1-0.html)

---

## 1. Link Layer — Moving Bits Within One Segment

The link layer cares about exactly one thing: **how to hand bits to the device sitting right next to you.** Whether the final destination is the next rack or the other side of the planet, this layer is only responsible for the next hop.

### Ethernet

**Definition:** The link-layer standard that carries frames on wired local networks.

**How it works:** Data is wrapped into frames, with destination and source MAC addresses in front. For known unicast, a switch uses its MAC table to select the destination port. Broadcast and unknown-unicast frames are typically flooded within the VLAN; multicast behavior depends on configuration. Early Ethernet relied on collision detection (CSMA/CD), but in modern switched full-duplex networks collisions have essentially disappeared.

**In practice:** For Ethernet IP traffic, an MTU of 1500 means a 1500-byte IP packet inside the frame, excluding Ethernet header/FCS. Jumbo MTUs are device/path-specific; 9001 is an EC2-supported value, not a universal Ethernet size. In the cloud, layering a VPN or overlay network on top adds encapsulation headers that shrink the effective MTU, and failed MTU discovery can produce a black hole that shows up as "ping works, but large responses hang." It is one of the failure modes that takes the longest to diagnose.

**MTU vs MSS:** MSS limits TCP data bytes, not the full frame. With MTU 1500, the base-header calculation gives 1460 for IPv4 (1500−20−20) or 1440 for IPv6 (1500−40−20). The sender further reduces actual data for any IP/TCP options it includes. TCP exchanges MSS during the handshake, so when MTU problems keep recurring across a tunnel, MSS clamping on the router (forcing a lower TCP MSS) is a widely used workaround.

### Wi-Fi

**Definition:** The link-layer standard that carries LAN frames over a wireless segment (IEEE 802.11).

**How it works:** Because the air is a shared medium, Wi-Fi is fundamentally different from Ethernet. Wi-Fi avoids relying on collision detection while transmitting and uses CSMA/CA: check that the channel is clear before sending, then use ACK/retry for ordinary unicast traffic; broadcast/multicast behavior differs. In other words, retransmission is already built into the link layer.

**In practice:** Link-layer retransmission stacked on top of TCP retransmission inflates latency variance (jitter). Real-time quality problems get reported as "the server's fault" when the actual culprit is the client's wireless segment. Server RTT alone cannot locate the cause; correlate it with application processing time and client/AP retry, signal and queue metrics.

### VLAN

**Definition:** A technique for segmenting shared switch infrastructure into logical L2 networks (IEEE 802.1Q).

**How it works:** An 802.1Q-tagged frame carries a 4-byte VLAN tag. Access ports can carry untagged frames that the switch assigns to a VLAN. Broadcasts only reach hosts in the same VLAN, so you can segment a network without touching the cabling. Traffic between VLANs must pass through an L3 device (a router or L3 switch).

**In practice:** VLANs provide logical L2 segmentation, not physical or cryptographic isolation. Routing and firewall controls determine permitted inter-segment traffic. VPCs, subnets and security groups serve different cloud networking roles; they are not one-for-one replacements for VLANs.

> 📎 For how EKS structures its VPC, see [EKS Networking Fundamentals](../eks/03-eks-networking-part1.md).

### PPP

**Definition:** A protocol that carries packets over a point-to-point link connecting exactly two nodes.

**How it works:** Unlike Ethernet, no addressing is needed — there is only one node at each end of the link. Instead, PPP provides link establishment, optional authentication, and upper-protocol negotiation (LCP/NCP).

**In practice:** It looks like a relic of the dial-up era, but it survives as PPPoE on a large share of residential internet lines. With standard 1500-byte Ethernet payloads, the usual 6-byte PPPoE header plus 2-byte PPP protocol field leaves 1492 bytes for IP; negotiated larger underlays can preserve 1500. An unaccounted-for reduction to 1492 can cause the MTU problems described above.

### ARP

**Definition:** The protocol that resolves an on-link IPv4 next-hop address to a MAC address.

**How it works:** The IP layer says "send this to 10.0.1.5," but Ethernet only understands MAC addresses. So the host broadcasts "who has 10.0.1.5?" and the owning host replies. The result is cached with OS-specific neighbor states/timeouts. For an off-link destination, the host resolves its gateway’s MAC rather than the remote host’s MAC.

**In practice:** ARP has no authentication. Anyone can answer "that IP is mine," which is exactly what makes ARP spoofing possible. The same property is also used legitimately: on failover, the new active node broadcasts a Gratuitous ARP to announce the VIP-to-MAC mapping to neighbors; switches also learn source-MAC location from the frame. When a VIP-based HA setup fails over slowly, delayed cache refresh is a prime suspect.

> 📎 For how Cilium integrates L2/routing behavior with eBPF, see [Cilium Networking](../networking/cilium/03-networking.md).

---

## 2. Internet and Routing Layer — Crossing Networks

If the link layer gets you "next door," this layer gets you "to the other side of the planet." The central question is: **where should this packet go next?**

### IPv4

**Definition:** The internet-layer protocol built on 32-bit addresses.

**How it works:** Every packet carries source and destination IPs; each router finds the most specific route (longest prefix match) in its routing table and forwards to the next hop. Delivery is best-effort — no guarantees, no ordering. Those guarantees are the job of the layer above (TCP).

**In practice:** IPv4 has about 4.3 billion possible addresses, and scarcity made NAT widely used and turned the private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) into the internal-network standard. The first wall large organizations hit during cloud migration is overlap in these private ranges: overlapping on-premises/VPC CIDRs prevent straightforward routing over VPN or Direct Connect without a designed renumbering, translation or proxy solution. IP address design is something to lock down at project kickoff.

### IPv6

**Definition:** The next-generation internet-layer protocol with 128-bit addresses.

**How it works:** With 128-bit addresses, exhaustion is a non-issue. The base header has a fixed 40-byte layout and no header checksum; routers do not fragment IPv6 packets. SLAAC lets hosts self-configure addresses without DHCP, and ARP is replaced by NDP (Neighbor Discovery Protocol).

**In practice:** IPv6 is not backward-compatible with IPv4, so real deployments run dual stack — which means maintaining two sets of firewall rules and security policies. Missing rules on the IPv6 path is a common security gap. A global IPv6 address does not by itself make a workload internet-reachable. AWS still requires routing and permitted security-group/NACL traffic; an egress-only internet gateway can allow outbound IPv6 without unsolicited inbound connections.

**Transition mechanisms:** There are three practical ways to coexist with IPv4: **dual stack** (run both side by side — most common, at the cost of duplicated policy), **tunneling** (wrap IPv6 packets in IPv4 to cross v4-only segments), and **NAT64/DNS64** (translate so IPv6-only clients can reach IPv4 servers — mobile carriers use this at scale as 464XLAT). Kubernetes supports dual-stack Services too, so cluster CIDR design can account for an IPv6 range from the start.

### ICMP

**Definition:** The control protocol that reports network errors and state.

**How it works:** ICMP carries control information and can include Echo payloads or quoted original-packet data: destination unreachable, TTL exceeded, fragmentation needed, and so on. `ping` uses Echo Request/Reply; `traceroute` increments TTL (or IPv6 Hop Limit) one hop at a time and reads the returning Time Exceeded messages.

**In practice:** Blanket-blocking ICMP "for security" is common — and it is the direct cause of the MTU black hole mentioned earlier. Classical IPv4 PMTUD uses ICMP Type 3 Code 4, while IPv6 uses ICMPv6 Packet Too Big Type 2. Blocking required messages can cause black holes; PLPMTUD can instead probe packet sizes without relying on ICMP. Preserve required error/discovery traffic according to the IP version and policy.

> 📎 For how this failure shows up in EKS, see [EKS Networking Deep Dive](../eks/03-eks-networking-part3.md).

### OSPF

**Definition:** A link-state routing protocol that computes optimal paths inside a single autonomous system.

**How it works:** Every router floods its link state across the area, so routers in the same area converge on consistent link-state information, then each runs Dijkstra's algorithm to compute shortest paths. Interface costs are configured (often derived from bandwidth), and networks are split into areas to scale.

**In practice:** OSPF is an IGP — for internal networks. Convergence is fast and paths are found automatically, but each router maintains link-state information for its attached areas, so at scale, area design determines performance.

### BGP

**Definition:** A path-vector routing protocol that exchanges reachability between autonomous systems (ASes).

**How it works:** BGP's goal differs from OSPF's: it picks not "the fastest path" but "the path policy prefers." Each AS advertises the prefixes it can reach along with the AS path; receivers rank routes by attributes such as AS_PATH length, Local Preference, and MED. Routing for the entire internet rests on this.

**In practice:** BGP trusts advertisements by default, which is why bad prefix advertisements can cause widespread outages. RPKI origin validation checks whether the prefix origin is authorized; it does not validate the entire AS path or stop all route leaks. From a cloud perspective, Direct Connect uses BGP; Site-to-Site VPN can use BGP or supported static routing, so AS numbers, advertised prefix design, and path preference for redundancy (AS_PATH prepending and friends) become real design items.

> 📎 For how Calico uses BGP inside a cluster, see [Calico BGP Deep Dive](../networking/calico/04-bgp-deep-dive.md).

### NAT

**Definition:** A function that translates IP addresses and, for NAPT/PAT, transport ports.

**How it works:** A common case is many private hosts sharing a public address through PAT/NAPT. Translation can also be private-to-private; it is not always public-internet address sharing. A translation table keeps per-session mappings so return packets find their way back to the right internal host.

**In practice:** NAT is the poster child for layering violations: an L3 device that rewrites L4 ports, and it breaks end-to-end connectivity — the internet's original premise. As a result P2P becomes hard, and workarounds such as STUN/TURN become necessary (see WebRTC below). In the cloud, NAT Gateway port exhaustion and data processing charges are the practical issues. For outbound-heavy workloads, VPC endpoints can reduce NAT processing for supported AWS services; compare their hourly/data charges and traffic path before assuming savings.

---

**Next:** [Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md)

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
