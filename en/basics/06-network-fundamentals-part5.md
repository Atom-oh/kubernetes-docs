# Network Fundamentals Part 5: Network Devices, LAN and WAN Basics

> **Last Updated**: November 19, 2026

::: tip This is a five-part series
[Part 1: The Layer Model, Link and Routing Layers](./06-network-fundamentals-part1.md) ·
[Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md) ·
[Part 3: Application Protocols](./06-network-fundamentals-part3.md) ·
[Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md) ·
**Part 5: Network Devices, LAN and WAN** *(this document)*
:::

Parts 1 to 4 walked through the protocols layer by layer. This part covers the **devices** that process those protocols and the **LAN and WAN designs** that connect them. Ethernet frames, ARP, longest-prefix match and the basic definition of NAT are already explained in [Part 1](./06-network-fundamentals-part1.md), so they are not repeated here. Instead, this part focuses on what each device looks at, what decision it makes, and where redundancy and address translation break.

The scope maps to the CCNA (200-301) Network Fundamentals, Network Access and IP Services areas and to CompTIA Network+ (N10-009) domain 1. The exam outlines only shaped the table of contents. Numbers and protocol behavior were checked against the standards, vendor and AWS documents in References at the end; the basic behavior of devices such as hubs and APs is given as a general definition.

As in Part 1, each item follows **definition → how it works → where it bites in practice**.

---

<a id="device-roles"></a>

## 1. Device Roles: Who Looks at What

The clearest way to tell devices apart is to ask **which table the device consults** when it decides where to send what arrived on a port.

| Device | Main input | Table consulted | Decision |
|---|---|---|---|
| Hub (repeater) | Nothing (bit signals) | None | Repeats the signal out of every other port |
| L2 switch | Destination MAC + VLAN | MAC address table | Known unicast goes to one port; broadcast and unknown destinations flood within the VLAN |
| L3 switch | MAC within a VLAN, destination IP across subnets | MAC table + routing (FIB) | Switches inside a VLAN, routes between VLANs through per-VLAN virtual interfaces (SVIs) acting as gateways |
| Router | Destination IP | FIB built from the routing table | Forwards to the next hop of the longest-prefix route, decrements TTL by 1, writes a new L2 header |
| Stateful firewall / NGFW | 5-tuple and connection state; an NGFW also identifies the application | Policy rules + state (connection) table | New connections are judged by rules; later return packets pass when they match the state table |
| Load balancer | 5-tuple at L4; HTTP host, path and headers at L7 | Listener rules, target group health | Picks one healthy target and forwards to it |
| Wireless AP | Station MAC, SSID | Associated-station list, SSID-to-VLAN mapping | Bridges 802.11 frames onto the wired distribution network |

Points worth noting per device:

- A **hub** is an L1 device and never looks at addresses. Everything attached to it shares one half-duplex medium, so simultaneous transmissions collide.
- An **L2 switch** learns each frame's **source MAC** against the ingress port and VLAN, and picks the egress port from the **destination MAC**. It does not change the frame (adding or removing an 802.1Q tag on a trunk is the exception).
- An **L3 switch** is switching hardware with routing built in. As in Cisco's example, you create one SVI per VLAN and use its address as that VLAN's default gateway.
- A **router** does not forward a packet it received as an L2 broadcast to other interfaces (RFC 1812 §5.3.4, except for IP multicast destinations), and it does not forward the limited broadcast `255.255.255.255` (§5.3.5.1), so a router interface (or SVI) is the boundary of a broadcast domain. A routed packet gets a lower TTL and new source/destination MACs, but its IP addresses stay the same unless NAT is involved.
- A **stateful firewall** tracks connections, so you do not write separate rules for return packets. NIST SP 800-41 distinguishes packet filters, stateful inspection (which keeps a state-table entry per connection) and application firewalls and proxy gateways, and calls a firewall bundled with malware detection and similar functions a UTM. "NGFW" is not a NIST term; it is a vendor term for products that bundle application identification, user identification, intrusion prevention and similar functions.
- A **load balancer** decides differently depending on its layer. On AWS, an ALB evaluates listener rules in priority order and then picks a target from the rule's target group; an NLB picks a target with a flow hash over protocol, source/destination IP and port and the TCP sequence number, and keeps each TCP connection on one target for its lifetime.
- An **AP** is a bridge between wireless and wired. Mapping each SSID to a different VLAN is common, so wireless stations go through the same switch and router decisions described above.

**In practice:** when narrowing down a fault, look at "the table this device consults." On Linux, `bridge fdb show` shows a bridge's learned MACs, `ip route get <destination>` shows the routing decision, and the conntrack tools show the connection-tracking (state and NAT) table. If the entry you expect is missing, the cause lies in a step before that device.

### Collision Domains and Broadcast Domains

**Definition:** a **collision domain** is the extent of a shared medium where simultaneous transmissions collide; a **broadcast domain** is the extent an L2 broadcast frame reaches.

**How it works:**

- A hub puts all of its ports in one collision domain.
- A switch gives each port its own collision domain. On full-duplex links, transmit and receive are separate and collisions do not occur at all (see [Ethernet in Part 1](./06-network-fundamentals-part1.md#ethernet)).
- One VLAN is one broadcast domain. If the same VLAN spans several switches over trunks, the whole span is still **one** broadcast domain.
- Router interfaces and SVIs do not forward broadcasts, so they split broadcast domains.

**Counting with an example:** one switch carries VLANs 10, 20 and 30 and connects to a router (three subinterfaces) over one trunk. One switch port has a hub with four PCs on it.

| Question | Answer | Why |
|---|---|---|
| Number of broadcast domains | 3 | One per VLAN; the router stops broadcasts between VLANs |
| Collision domains for the four PCs on the hub | 1 | A hub is a shared medium, so the four PCs share one collision domain |
| One host per switch port | 1 per port | Switch ports separate collision domains, and full duplex means no actual collisions |

**In practice:** in a large broadcast domain, broadcasts such as ARP and DHCP wake every host's CPU, and a loop damages more hosts. That is why VLANs are kept small and traffic between them is routed.

---

<a id="vlan-trunk"></a>

## 2. VLANs and 802.1Q Trunks

The definition of a VLAN and the rule that inter-VLAN traffic needs an L3 device are in [VLAN in Part 1](./06-network-fundamentals-part1.md#vlan). This section looks at what the tag actually contains and what can go wrong on a trunk.

### The 802.1Q Tag

**Definition:** IEEE 802.1Q inserts a 4-byte tag after the source MAC of an Ethernet frame to mark the VLAN the frame belongs to.

**How it works:** the tag has four fields.

| Field | Size | Meaning |
|---|---|---|
| TPID | 16 bits | Value `0x8100`: marks the frame as 802.1Q-tagged |
| PCP | 3 bits | Priority 0 to 7 (802.1p) |
| DEI (formerly CFI) | 1 bit | Marks frames that may be dropped first under congestion |
| VID | 12 bits | VLAN ID. Values run 0 to 4095, but 0 and 4095 are reserved, so real VLANs use 1 to 4094 |

The tag adds 4 bytes, so a tagged frame can be up to 1522 bytes, and the device that inserts the tag recomputes the FCS.

### Access Ports, Trunk Ports and the Native VLAN

**Definition:**

- An **access port** belongs to one VLAN and exchanges untagged frames with the host.
- A **trunk port** carries many VLANs over one link and tags each frame with its VID.
- The **native VLAN** is the VLAN that crosses a trunk **untagged**.

**How it works:** per Cisco Catalyst documentation, the native VLAN defaults to **VLAN 1**; the device places untagged frames received on a trunk into the native VLAN and sends native-VLAN frames out untagged. The native VLAN **must match** on both ends of the trunk. If it does not, untagged frames from one side's VLAN land in a different VLAN on the other side, which breaks VLAN separation, and Cisco warns that spanning-tree loops may result. By default a trunk allows all VLANs 1 to 4094.

**In practice:**

- Trim each trunk's allowed-VLAN list to what it needs, move the native VLAN to an unused VLAN, and keep both ends consistent.
- Linux can create a tagged subinterface with `ip link add link eth0 name eth0.10 type vlan id 10`. This is how hypervisors and bare-metal Kubernetes nodes attach to a trunk port.

### Inter-VLAN Routing: Router-on-a-Stick

Placing one router subinterface per VLAN on a single trunk lets one router act as the gateway for several VLANs. The animation below follows one frame from PC-A in VLAN 10 to PC-B in VLAN 20. The key point is that it goes up and back down the same cable.

![Inter-VLAN routing animation. ① PC-A (VLAN 10, 10.0.10.5) sees the destination is on another subnet, so it addresses the frame to the MAC of gateway 10.0.10.1. ② The L2 access switch learns the source MAC on port 1 in VLAN 10 and sends the frame up the 802.1Q trunk with a VLAN 10 tag. ③ The router's route lookup for 10.0.20.0/24 picks the .20 subinterface, decrements TTL from 64 to 63 and writes a new L2 header (IP addresses unchanged). ④ The frame comes back down the same trunk tagged VLAN 20. ⑤ The switch strips the tag and forwards it out the VLAN 20 access port, and PC-B (10.0.20.7) receives it.](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-0.svg)

When an L3 switch does the same job, it routes between SVIs inside the switch instead of going up and down a trunk. Inter-VLAN traffic no longer uses the trunk's bandwidth twice, which is why L3 switches are used where inter-VLAN traffic is heavy.

---

<a id="stp-lacp-fhrp"></a>

## 3. Loop Prevention and Redundancy: STP, LACP, FHRP

Redundant links and devices raise availability, but they create loops at L2 and a "who is the default gateway?" problem at the L3 gateway. Three technologies each solve one of these.

### STP and RSTP

**Definition:** the Spanning Tree Protocol (STP, IEEE 802.1D) blocks some redundant switch links so that the L2 topology becomes a loop-free tree. RSTP (802.1w, later folded into 802.1D-2004) is its fast-converging version.

**Why it is needed:** IP headers carry a TTL, but **Ethernet headers do not.** With a loop between switches, a broadcast frame never dies: it keeps circulating and multiplying (a broadcast storm), and the same source MAC appears on several ports, so MAC tables keep changing.

**How it works:**

1. **Root bridge election:** the switch with the lowest bridge ID (priority + MAC) becomes root. The default priority is 32768, so with no configuration the switch with the lowest MAC, often the oldest one, becomes root.
2. **Port roles:** each non-root switch makes its best port toward the root its **root port**, and on each segment the port sending the best BPDU becomes the **designated port**. The remaining ports block (the alternate and backup roles in RSTP).
3. **Convergence:** 802.1D is timer driven. Defaults are hello 2 s, max age 20 s and forward delay 15 s; a port spends two forward delays, about 30 s, in listening and learning. RSTP reduces the states to discarding, learning and forwarding, and on point-to-point links it moves to forwarding through a proposal/agreement exchange instead of waiting for timers. Host ports are configured as edge ports (Cisco PortFast) and forward immediately.

**In practice:** do not leave the root bridge to defaults; lower the priority on core or distribution switches to pin it where you intend. If an arbitrary switch becomes root, traffic detours through it. Also remember that blocked links carry nothing in normal operation. LACP below and spine-leaf in section 4 work around this limit in different ways.

### LACP and EtherChannel

**Definition:** link aggregation (IEEE 802.1AX) bundles several parallel full-duplex point-to-point links between two devices into one logical link (a LAG). LACP is the control protocol both ends use to negotiate the bundle; Cisco calls the bundle an EtherChannel.

**How it works:** STP sees the LAG as one link, so the bundled links are not blocked. Frames are assigned to one member link by hashing values such as addresses and ports, so **one flow always uses the same link**. Cisco documents bundling up to eight compatible ports.

**In practice:** bundling four 10 Gbps links does not let **one** TCP connection exceed 10 Gbps; the aggregate is only usable with many flows. Answering "a single backup job is slow" by adding LAG members may not help. AWS Direct Connect LAGs also use LACP to bundle connections at the same endpoint (multi-chassis LAG is not supported); details come in [expert workbook 07: WAN and Hybrid Connectivity](../networking/expert/07-wan-hybrid-connectivity.md#dx-lag).

### FHRP: VRRP and HSRP

**Definition:** a first-hop redundancy protocol (FHRP) lets several routers share a **virtual IP and virtual MAC** so that hosts survive a router failure without changing their default gateway setting.

**Why it is needed:** a host has a single default gateway address. If that router dies, the host cannot leave its subnet even when another router sits on the same subnet.

**How VRRPv3 works (RFC 9568, which obsoletes RFC 5798):**

- Among routers with the same virtual router ID (VRID), one becomes **Active** (Master in RFC 5798) and handles traffic sent to the virtual IP. The IPv4 virtual MAC is `00-00-5E-00-01-{VRID}` and the IPv6 one is `00-00-5E-00-02-{VRID}`.
- The Active router sends advertisements to IPv4 multicast `224.0.0.18` with IP protocol number 112. The default advertisement interval is 100 centiseconds (1 s).
- The router that actually owns the virtual IP has priority 255; the default for backups is 100. Priority 0 from the Active router signals that it has stopped participating in VRRP, so a backup takes over after only Skew_Time instead of the full down interval. Preempt defaults to true.
- A backup becomes Active after missing advertisements for `Active_Down_Interval = 3 × advertisement interval + Skew_Time`, where `Skew_Time = ((256 − priority) × advertisement interval) / 256`. With priority 100 and a 1 s interval, Skew_Time is about 0.61 s, so takeover happens after about **3.61 s**.

**HSRP:** Cisco's FHRP, published as RFC 2281 (Informational). Defaults are hello 3 s and hold 10 s, and the v1 virtual MAC is `0000.0c07.acXX` (XX is the group number).

**In practice:** the virtual MAC moves to the new Active router, so neighbors and switches must learn its new location right after failover (see Gratuitous ARP under [ARP in Part 1](./06-network-fundamentals-part1.md#arp)). Measure failover time as FHRP timers plus STP convergence plus upstream routing convergence.

---

<a id="lan-topologies"></a>

## 4. LAN Topologies: Hierarchical and Spine-Leaf

### Campus: Two-Tier and Three-Tier

**Definition:** campus LANs are traditionally split into access, distribution and core layers.

| Layer | Role |
|---|---|
| Access | The network edge where hosts connect |
| Distribution | Aggregates access switches and provides the L2/L3 boundary, access policy and redundant paths |
| Core | The backbone that connects all blocks plus the data center and WAN |

**How it works:** Cisco's design guide recommends a **two-tier (collapsed core)** design, which merges distribution and core, for small sites such as a single building, and describes a **three-tier** design as suited to large sites with several distribution blocks, where the separation eases fault isolation and change control.

### Data Center: Spine-Leaf

**Definition:** in a spine-leaf (Clos) fabric, **every leaf connects to every spine** (a full mesh between the tiers), and servers attach to leaves. This document assumes the basic two-tier fabric in which leaves are not linked to each other and neither are spines; variants exist, such as Cisco ACI's multi-tier design that hangs a second tier of leaves below the first.

**How it works:**

- Leaf-to-spine links are L3, and ECMP spreads flows over all spine paths. STP blocks nothing, so all uplinks carry traffic at once.
- Under that assumption, traffic to a server on another leaf always goes **leaf → spine → leaf**: three switches (two switch-to-switch links). Every server pair is the same distance apart, which gives the consistent latency Cisco cites as a benefit of this design.
- Add leaves for more ports and spines for more bandwidth.

| Comparison | Traditional three-tier (L2 + STP) | Spine-leaf (L3 + ECMP) |
|---|---|---|
| Redundant links | STP blocks some | ECMP uses all |
| Server-to-server distance | Depends on placement | Constant: leaf → spine → leaf |
| L2 extension | Stretch VLANs widely | VXLAN/EVPN overlay when needed |

**In practice:** when a VLAN must span several leaves in a spine-leaf fabric, run a VXLAN/EVPN overlay on the L3 underlay. How to prove identifiers, routes and the data plane with evidence continues in [Expert workbook 03: Datacenter EVPN](../networking/expert/03-datacenter-evpn.md).

---

<a id="nat-pat-cgnat"></a>

## 5. NAT, SNAT, PAT and CGNAT

The basic definition of NAT and the fact that "an L3 device touches L4 ports" are covered in [NAT in Part 1](./06-network-fundamentals-part1.md#nat). This section sorts out the terms, shows how a translation table actually fills, and when it runs out.

### Terms

| Term | What it rewrites | Example |
|---|---|---|
| Basic NAT (including static 1:1) | IP address only | One private IP ↔ one public IP; how an AWS internet gateway handles public IPv4 |
| NAPT / PAT | IP address + transport identifier (TCP/UDP port, ICMP query ID) | Many inside hosts share one public IP |
| SNAT | Source address (and port) | Traffic leaving for the internet |
| DNAT | Destination address (and port) | Port forwarding, a load balancer forwarding to a target |

RFC 3022 defines Basic NAT and NAPT as "traditional NAT." Sessions start outbound from the private network, and the first outbound packet creates the mapping. SNAT and DNAT come from the Linux netfilter target names; PAT is usually implemented as a form of SNAT.

### Following a PAT Translation Table

The example uses RFC 1918 private space for the inside hosts and RFC 5737 documentation ranges (`203.0.113.0/24`, `198.51.100.0/24`) for the public IP and the server. In the animation below, the two inside hosts deliberately use **the same source port, 50000**. With only one public IP, the NAT device tells them apart by public **port**.

![PAT animation. ① Host-A (10.0.1.10) on private network 10.0.1.0/24 sends a packet from source 10.0.1.10:50000 to server 198.51.100.20:443. ② The NAT device adds the translation row 10.0.1.10:50000 → 203.0.113.10:30001 and sends the packet out with source 203.0.113.10:30001. ③ Host-B (10.0.1.20) also uses source port 50000, so the NAT assigns a different port on the same public IP, adding the row 10.0.1.20:50000 → 203.0.113.10:30002. ④ The server's reply returns to destination 203.0.113.10:30002, and the NAT looks up the table by public port and matches row 2. ⑤ The NAT rewrites the destination back to 10.0.1.20:50000 and delivers the packet to Host-B.](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-1.svg)

On the way back, the NAT looks at the **destination (public IP:port)**. If no row matches, for example because the connection was opened from outside or the mapping already expired, the packet cannot go to any inside host. That is why reaching a server behind NAT from outside needs a separate static mapping (DNAT).

### Port Exhaustion

**How it works:** the port field is 16 bits, so one public IP can hold only so many simultaneous connections to the same destination. AWS NAT gateway publishes its limit explicitly:

- Up to **55,000** simultaneous connections **per public IPv4 address, per unique destination** (destination IP, destination port and protocol)
- Up to 8 IPv4 addresses per NAT gateway (1 primary + 7 secondary), so up to 440,000 to the same destination; a public NAT gateway is limited to 2 Elastic IPs by default, so you need a quota increase
- When a source port cannot be allocated, the CloudWatch `ErrorPortAllocation` metric goes above zero
- A connection idle for 350 s times out; sending on it afterwards gets an RST from the NAT gateway

**In practice:** when Pods on hundreds of Kubernetes nodes call **one external API** (one IP:443), there is only one destination, so that limit is hit first. Work through connection reuse (keep-alive, connection pools), adding secondary IPs, splitting subnets across several NAT gateways, and moving supported AWS service traffic off the NAT path with VPC endpoints (see the outbound path discussion in [Part 4](./06-network-fundamentals-part4.md)). For connections that sit idle, set TCP keepalive below 350 s.

### CGNAT and 100.64.0.0/10

**Definition:** CGNAT (carrier-grade NAT) is large-scale NAT in which a carrier puts many subscribers behind one public IPv4 address. Traffic is often translated once in the subscriber's router and again in the carrier's CGN.

**How it works:**

- RFC 6598 allocates **`100.64.0.0/10`, the Shared Address Space**, for the segment between the CGN and the customer premises equipment (CPE). It is **separate** from the RFC 1918 private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), so it does not collide with whatever RFC 1918 range the subscriber uses inside.
- Packets and routing information for this range must not cross provider boundaries, and providers must filter incoming advertisements for it.
- RFC 6888 requires a CGN to support limiting external ports per subscriber, and when resources run out it must drop the new packet rather than delete existing mappings. Identifying a subscriber from logs takes the external address, external port and timestamp.

**In practice:**

- Mobile and some residential users may share a public IP. Blocking or rate-limiting by IP alone can hit unrelated users, and incident investigation needs the **port and exact time** along with the IP.
- A branch behind CGNAT cannot accept connections opened from outside, so design site-to-site VPNs to be initiated from the branch side.
- AWS lets you associate CIDR blocks from `100.64.0.0/10` with a VPC. That makes it a candidate when private address space runs short, but first check that no on-premises network or carrier segment you must reach uses the same range.

---

<a id="wan-types"></a>

## 6. WAN Types

**Definition:** a WAN connects geographically separate sites (headquarters, branches, data centers, cloud). Most of it is bought from carriers, so the choice is "which service do we buy?"

| Type | What you buy | Routing and addressing | Strengths | Caveats |
|---|---|---|---|---|
| Leased line | A fixed-bandwidth point-to-point circuit between two sites | Routers at both ends exchange routes directly | Consistent bandwidth and latency, not shared with other customers | One circuit per site pair, high cost |
| MPLS L3VPN | Customer-dedicated virtual routing inside the carrier's MPLS network | Carrier PE routers bind customer attachments to VRFs; static, RIP, OSPF or BGP between CE and PE | Any-to-any between sites, carrier SLA | Tied to the carrier, more expensive than internet circuits |
| Broadband internet | Fiber, cable or similar internet access | Public or CGNAT address, no control of the path | Cheap per unit of bandwidth | Best-effort quality; confidentiality comes from your own overlay such as IPsec |
| LTE/5G | Mobile data access | Usually behind carrier NAT, inbound hard | Fast to turn up without cabling, good as backup | Variable latency and bandwidth, tariff model |
| SD-WAN | A managed overlay on top of the circuits above | Per-application-flow policy picks the tunnel path | Combines circuits with per-application path selection | Underlay quality limits remain |

**How it works:**

- In **MPLS L3VPN** (RFC 4364), the carrier's PE routers keep routing tables called VRFs alongside the default forwarding table and bind each customer attachment circuit to a VRF. Customer routes carried in BGP get an 8-byte Route Distinguisher prefix that turns them into VPN-IPv4 addresses, so two customers using the same private range do not mix. CE and PE exchange routes with static routing, RIP, OSPF or BGP.
- **SD-WAN** is a service model, not a circuit type. MEF 70.2 defines the SD-WAN service separately from the Underlay Connectivity Services beneath it (internet access, MPLS and so on), defines the tunnels between sites as Tunnel Virtual Connections (TVCs), and defines the per-application-flow path rules as Policy.
- The WAN entry points into the cloud are AWS Site-to-Site VPN and Direct Connect (see the cloud mapping in [Part 4](./06-network-fundamentals-part4.md)). Redundancy design, BGP path selection, tunnel MTU and cost comparison are covered in [expert workbook 07: WAN and Hybrid Connectivity](../networking/expert/07-wan-hybrid-connectivity.md).

**In practice:** when choosing a WAN, record more than bandwidth: latency and jitter, how failover works, and whether circuits arrive from different carriers over different paths (physical diversity). Two circuits sharing one conduit fail together with a single backhoe.

---

## 7. In the Cloud

[Part 4](./06-network-fundamentals-part4.md) compared traditional concepts with AWS broadly. This table is limited to the **devices and decisions** covered here and states what is the same and what differs.

| Traditional device or function | AWS counterpart | What differs |
|---|---|---|
| Subnet default gateway (router, SVI) | VPC router and VPC route tables | AWS reserves the subnet's network address + 1 for the VPC router; route tables automatically carry a `local` route for the VPC CIDR |
| FHRP (VRRP, HSRP) | Not configured by you | The gateway address is the VPC router and VPCs do not support broadcast, so there is no L2 hand-over of a virtual IP and MAC; design redundancy with multiple AZs and load balancer health checks |
| Internet edge router + static 1:1 NAT | Internet gateway (IGW) | A horizontally scaled, redundant VPC component that logically provides 1:1 NAT for instances with public IPv4 addresses |
| PAT device | NAT gateway | 55,000 simultaneous connections per IP per destination, up to 8 IPs, 5 Gbps scaling automatically to 100 Gbps, no security group attachment, 350 s idle timeout |
| Core router, WAN hub | Transit Gateway | A Regional virtual router; each attachment is associated with one route table and can propagate routes to several |
| Stateful firewall | Security group | Stateful; allow rules only, all rules evaluated; instance (network interface) level |
| Stateless ACL on a router interface | Network ACL | Stateless; allow and deny rules evaluated in ascending rule number, first match applies; subnet level; return traffic on ephemeral ports must be allowed explicitly |

**Where the security group vs NACL difference shows up as an outage:** a NACL does not allow return traffic automatically. When an instance in the subnet acts as a client, the reply returns to an **ephemeral port** chosen by that instance's OS, so the inbound NACL must allow that range. Per AWS documentation, many Linux kernels use 32768–61000, Windows Server 2008 and later use 49152–65535, and NAT gateways, ELB and Lambda use 1024–65535. With security groups alone, replies are allowed automatically and this problem does not arise.

---

## Wrapping Up

Devices are, in the end, machines that consult a table to make a decision: a switch reads its MAC table, a router its FIB, a firewall its state table, a load balancer its listener rules and a NAT device its translation table. Redundancy brings its own trade-off at each level: loops at L2 (STP), per-flow distribution on bundled links (LACP), and handing over ownership of a virtual address at the gateway (FHRP).

When investigating a failure, check "what was in the table of the last device that handled the packet correctly." Evidence that shows the table directly, such as where a MAC was learned, the result of a route lookup, a state or NAT table entry, or a NAT gateway's `ErrorPortAllocation`, beats guessing.

---

## Next Documents

- [Expert workbook 03: Datacenter EVPN](../networking/expert/03-datacenter-evpn.md): VXLAN/EVPN overlays on spine-leaf
- [Expert networking study path](../networking/expert/README.md): the full workbook map, including WAN and hybrid connectivity, CDN and edge
- [Networking learning path](../networking/README.md#learning-path): from containers and Services to CNI implementations
- [Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md): the full AWS and Kubernetes mapping

## References

Standards and RFCs

- [IEEE 802.1Q-2022: Bridges and Bridged Networks](https://standards.ieee.org/ieee/802.1Q/10323/)
- [IEEE 802.1AX: Link Aggregation](https://1.ieee802.org/tsn/802-1ax-rev/)
- [RFC 9568: VRRP Version 3 for IPv4 and IPv6](https://www.rfc-editor.org/rfc/rfc9568.html) (obsoletes RFC 5798), [RFC 5798](https://www.rfc-editor.org/rfc/rfc5798.html)
- [RFC 2281: Cisco Hot Standby Router Protocol (HSRP)](https://www.rfc-editor.org/rfc/rfc2281.html)
- [RFC 3022: Traditional IP Network Address Translator](https://www.rfc-editor.org/rfc/rfc3022.html)
- [RFC 6598: IANA-Reserved IPv4 Prefix for Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598.html)
- [RFC 6888: Common Requirements for Carrier-Grade NATs](https://www.rfc-editor.org/rfc/rfc6888.html)
- [RFC 1918: Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918.html)
- [RFC 1812: Requirements for IP Version 4 Routers](https://www.rfc-editor.org/rfc/rfc1812.html)
- [RFC 4364: BGP/MPLS IP Virtual Private Networks](https://www.rfc-editor.org/rfc/rfc4364.html)
- [RFC 5737: IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737.html)
- [NIST SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/) ([PDF](https://www.mplify.net/wp-content/uploads/MEF-70.2.pdf))

Vendor documentation

- [Cisco: Inter-Switch Link and IEEE 802.1Q Frame Format](https://www.cisco.com/c/en/us/support/docs/lan-switching/8021q/17056-741-4.html)
- [Cisco Catalyst 9300: Configuring VLAN Trunks](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-12/configuration_guide/vlan/b_1712_vlan_9300_cg/configuring_vlan_trunks.html)
- [Cisco: Configure InterVLAN Routing with Catalyst Switches](https://www.cisco.com/c/en/us/support/docs/lan-switching/inter-vlan-routing/41260-189.html)
- [Cisco: Understand Rapid Spanning Tree Protocol (802.1w)](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html)
- [Cisco: Understand and Tune Spanning Tree Protocol Timers](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/19120-122.html)
- [Cisco Meraki: Determining the RSTP/STP Root Bridge](https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Determining_the_RSTP%2F%2F%2F%2FSTP_Root_Bridge_on_an_MS_Switch_network)
- [Cisco: Understand EtherChannel Load Balance and Redundancy](https://www.cisco.com/c/en/us/support/docs/lan-switching/etherchannel/12023-4.html)
- [Cisco: Medium Enterprise Design Profile, LAN Design](https://www.cisco.com/en/US/docs/solutions/Enterprise/Medium_Enterprise_Design_Profile%28MEDP%29/chap2.html)
- [Cisco: Massively Scalable Data Center Network Fabric White Paper](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-743245.html), [Cisco ACI Multi-tier Architecture White Paper](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-742214.html)
- [Linux ip-link(8)](https://man7.org/linux/man-pages/man8/ip-link.8.html), [bridge(8)](https://man7.org/linux/man-pages/man8/bridge.8.html), [iptables-extensions(8): SNAT and DNAT targets](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html)

AWS documentation

- [NAT gateway basics](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html), [Troubleshoot NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html), [NAT gateway CloudWatch metrics](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html)
- [Internet gateways](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [How AWS Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)
- [Compare security groups and network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html#VPC_Security_Comparison), [Custom network ACLs and ephemeral ports](https://docs.aws.amazon.com/vpc/latest/userguide/custom-network-acl.html)
- [VPC CIDR blocks](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html), [Subnet sizing (reserved addresses)](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [How Elastic Load Balancing works](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)
- [Direct Connect link aggregation groups](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)
