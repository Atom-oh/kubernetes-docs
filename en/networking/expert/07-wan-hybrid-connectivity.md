# 07. WAN and Hybrid Connectivity Design

> **Last Updated**: November 19, 2026
> **Lab boundary**: Design review (desk check) only. This workbook does not create circuits, VPNs, Direct Connect connections or Transit Gateways.
> **Verification status**: AWS Direct Connect, Site-to-Site VPN and Transit Gateway user guides and the cited RFCs were checked; no connection was **configured or measured** while writing this chapter.

After this workbook, you should be able to **predict the path in each direction** between on-premises sites and an AWS Region, and explain, with evidence, which rule picks the next path when one link fails, how long that takes and what shrinks (bandwidth, MTU).

Complete [Routing Policy and Measured Convergence](02-routing-policy-convergence.md) first. That chapter covers what LOCAL_PREF, AS_PATH, MED and communities mean; this one only asks **how far** AWS honors them. Review circuit types in [Network Fundamentals Part 5: WAN Types](../../basics/06-network-fundamentals-part5.md#wan-types) and NAT/CGNAT in [Part 5: NAT, PAT and CGNAT](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat).

**Readiness:** no account or circuit is needed. Every task is judged against the tables in this chapter and the official documentation. Building the same design for real incurs Direct Connect port, VPN connection, Transit Gateway attachment and data transfer charges; **that cost and the cleanup are the learner's own**. Do not create resources outside an existing, approved lab account.

## 1. Read with a question to answer

Exam scope only decides what to read. Numbers and behaviors come from the official documents in the first column.

| Reading | Exam scope it maps to | Question to answer in your own words |
|---|---|---|
| [MEF 70.2](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/), [Cisco Catalyst SD-WAN High Availability guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html) | ENCOR 350-401 Architecture: SD-WAN control and data plane elements | What happens to the data tunnels when the overlay's control plane is unreachable? |
| [Site-to-Site VPN tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html) | ANS-C01 Domain 1 Network Design, Domain 2 Network Implementation | Which of the two tunnels does AWS send on, and what changes that choice? |
| [Direct Connect routing policies and BGP communities](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html) | ANS-C01 Domains 1 and 2 | In what order does AWS compare the same prefix advertised over two VIFs? |
| [How Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) | ANS-C01 Domains 1 and 2 | When the same CIDR arrives over DX and VPN, which wins, and does AS_PATH matter? |
| [Direct Connect quotas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html), [VPN quotas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html), [TGW quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) | ANS-C01 Domain 1 | Which limit does the design hit first: bandwidth, route count or MTU? |
| [RFC 5880 (BFD)](https://www.rfc-editor.org/rfc/rfc5880.html), [RFC 7296 (IKEv2)](https://www.rfc-editor.org/rfc/rfc7296.html) | Protocol principles | Which two values multiply into a failure detection time? |

After reading, draw the sites, circuits and AWS components, with **BGP sessions** and **links that packets actually traverse** as different line styles. As [workbook 02](02-routing-policy-convergence.md) showed, a session does not mean data flows over it; the Direct Connect gateway below is the standard example.

## 2. Underlay and overlay

Record a WAN design in two layers. The **underlay** is the circuit that actually carries packets (MPLS, internet access, Direct Connect); the **overlay** is the tunnels and policy built on top (IPsec VPN, SD-WAN). An overlay cannot change the underlay's latency, loss or shared physical path: two tunnels over two circuits in the same conduit still share one point of failure.

| Model | Control plane (who decides the path) | Data plane (what packets ride) | What to check in a design |
|---|---|---|---|
| MPLS L3VPN | Provider PEs separate customer routes into VRFs and exchange them over BGP; CE–PE uses static, OSPF, BGP and so on | The provider's MPLS network; the customer never sees labels | CE–PE protocol, provider SLA, physical separation from other carriers |
| Internet + IPsec | Both endpoints, using static routes or BGP inside the tunnel | ESP over the public internet, best effort | Number of tunnels, NAT traversal, algorithm-dependent MTU |
| SD-WAN | A central controller distributes policy and routes | IPsec tunnels between WAN edges, several underlays at once | Behavior when controllers are unreachable, per-tunnel path measurement, per-application policy |

**Reading SD-WAN as control and data planes:** MEF 70.2 defines the SD-WAN service separately from the underlay connectivity services beneath it, and defines site-to-site tunnels (TVCs) and per-application-flow policy as distinct attributes (terms in [Part 5](../../basics/06-network-fundamentals-part5.md#wan-types)). In Cisco Catalyst SD-WAN, the SD-WAN Controllers orchestrate the control plane and exchange control information over OMP peering sessions; the Validator authenticates devices and orchestrates the control connections between Controllers and routers. Data flows over IPsec connections between routers, and BFD runs automatically on those connections to detect failures. So "SD-WAN detects failures quickly" is a statement about **BFD on the data tunnels**; controller redundancy is a separate design item.

On AWS, an SD-WAN appliance in a VPC peers with a Transit Gateway over BGP through a Connect attachment. One Connect peer (GRE tunnel) carries up to 5 Gbps, and an attachment can have up to 4 peers. This chapter's exercise does not use Connect, but section 8 includes it in the bandwidth comparison.

## 3. IPsec Site-to-Site VPN

**Definition:** every AWS Site-to-Site VPN connection has **two tunnels**, each with a unique public IP address and each terminating in a different Availability Zone. Configure both for redundancy; when one tunnel becomes unavailable (for example, during maintenance), traffic moves to the other tunnel of that connection automatically.

**Behavior:**

- **IKE version:** tunnels can permit IKEv1 and IKEv2. AWS strongly recommends IKEv2 and IKEv1 only when the device lacks IKEv2.
- **Tunnel use by direction:** on-premises-to-AWS traffic uses both tunnels. AWS-to-on-premises traffic prefers one tunnel and fails over to the other on an AWS-side failure, so the customer gateway must **allow asymmetric routing**. On a virtual private gateway (VGW), one tunnel across all of the gateway's VPN connections is selected as the egress path, and ECMP is not supported.
- **Static vs BGP:** choose dynamic routing when the device supports BGP. AWS recommends BGP-capable devices because BGP liveness checks help failover to the second tunnel. With BGP selected, you cannot also specify static routes.
- **ECMP:** VPNs on a Transit Gateway can aggregate tunnels with ECMP **only with dynamic routing**; static-routing VPNs do not support ECMP.
- **Bandwidth:** a standard tunnel carries up to 1.25 Gbps (up to 140,000 PPS). A Large Bandwidth Tunnel carries up to 5 Gbps but is available only for VPNs attached to a Transit Gateway or Cloud WAN, both tunnels must use the same bandwidth setting, and Accelerated VPN is not supported with it.
- **Liveness:** the Dead Peer Detection timeout is 30 seconds or higher, and the timeout action is `Clear` (end the IKE session, stop the tunnel and clear the routes), `None` or `Restart`. The AWS Knowledge Center gives 30 seconds as the default BGP hold time for VPN.
- **Customer gateway behind NAT:** a gateway behind NAT uses NAT traversal (NAT-T, RFC 3948), which wraps ESP in UDP. The MTU table in section 7 shows that enabling NAT-T lowers the MTU for the same algorithm. A branch behind CGNAT cannot accept an inbound session first (see [Part 5](../../basics/06-network-fundamentals-part5.md#nat-pat-cgnat)), so design that branch to initiate the tunnel.

**In practice:** do not report "two tunnels, so redundancy is done." The two tunnels make the AWS endpoint redundant; if they share one customer gateway and one internet circuit, those two are the single points of failure. For customer-side redundancy, add a second customer gateway and a second VPN connection.

## 4. Direct Connect

**Definition:** Direct Connect links your network to an AWS router at a Direct Connect location over a standard Ethernet fiber-optic cable. You create **virtual interfaces (VIFs)** on it to reach VPCs or public AWS services, bypassing internet service providers in the path. Your device must support 802.1Q VLANs, BGP and BGP MD5 authentication.

**Connection types:**

| Type | Speed | VIFs | Notes |
|---|---|---|---|
| Dedicated | 1, 10, 100, 400 Gbps | Up to 50 public/private VIFs plus up to 4 transit VIFs, 51 in total (cannot be increased) | Single-mode fiber, fixed transceiver standard per port speed |
| Hosted | Partner-provisioned values from 50 Mbps to 25 Gbps | 1 (cannot be increased) | Only qualifying partners offer 1 Gbps and above; 25 Gbps only where 100 Gbps ports exist. AWS polices traffic and drops the excess |

**VIF types:**

- **Private VIF:** reaches a VPC using private IPs. Attached directly to a VGW it reaches one VPC in the same Region; attached to a Direct Connect gateway it reaches VGWs across accounts and Regions.
- **Public VIF:** reaches public AWS services using public IPs. The public prefixes you advertise must be yours, and AWS filters inbound traffic to check that its source is one of your advertised prefixes.
- **Transit VIF:** reaches Transit Gateways associated with a Direct Connect gateway, on any dedicated or hosted connection of any speed.

**Direct Connect gateway:** a global resource associated with VGWs, Transit Gateways or a Cloud WAN core network. AWS describes it as a **distributed set of BGP route reflectors** that operates outside the data traffic path, so it does not create a single point of failure. Like the route reflector in workbook 02, it reflects routes and does not carry packets. One gateway supports up to 20 VGWs, 6 Transit Gateways and 30 private or transit VIFs.

**Route limits:** these turn directly into outages, so put them in the design table.

- On-premises to AWS over a private or transit VIF, one BGP session accepts a default of 100 routes each for IPv4 and IPv6, raisable with prefix controls to 1,000 each. **Advertising more than the allocation puts the BGP session into idle, reported as DOWN.**
- A public VIF BGP session accepts 1,000 routes.
- AWS to on-premises over a transit VIF, each Transit Gateway advertises up to 200 prefixes, IPv4 and IPv6 combined.

**Allowed prefixes:** for a Transit Gateway association, the Direct Connect gateway advertises **exactly** the allowed prefixes you enter. With VPC CIDR `10.20.0.0/16` and an allowed prefix of `10.0.0.0/8`, on-premises receives only `10.0.0.0/8`. For a VGW association, by contrast, allowed prefixes act as a filter that passes the same or smaller CIDRs. The trap in section 6 starts here.

<a id="dx-lag"></a>

**LAG:** a link aggregation group uses LACP to bundle several connections at a single Direct Connect endpoint into one logical connection. The rules:

- All connections must be dedicated and use the same bandwidth.
- A LAG holds up to 4 connections below 100 Gbps, or up to 2 connections at 100 or 400 Gbps.
- All connections must terminate at the same Direct Connect endpoint; multi-chassis LAG (MLAG) is not supported.
- All connections run active/active. A LAG has a minimum-links attribute (default 0); when set, the whole LAG goes down if fewer connections are operational, which prevents overloading the survivors.

A LAG adds **capacity**, but it ends on the same device at the same location and does not survive a location failure. As Part 5 noted, one flow still cannot exceed one member link. Design location redundancy with the Resiliency Toolkit models: **Maximum resiliency** targets a 99.99% SLA and **High resiliency** 99.9%, both only when every requirement in the Direct Connect SLA is met; **Development and test** spreads connections across separate devices in one location.

**MACsec:** supported on 10, 100 and 400 Gbps **dedicated** connections at selected locations; not on 1 Gbps dedicated or any hosted connection. It is hop-by-hop L2 encryption, so your device needs direct L2 adjacency with the AWS device and any last-mile segment must be transparent to L2. Only 256-bit keys are supported, and 100/400 Gbps connections require extended packet numbering (XPN). On a LAG, a single MACsec key is used across all links at any time.

## 5. Transit Gateway

**Definition:** a Transit Gateway is a Regional virtual router for traffic between VPCs and on-premises networks. An attachment is both a source and a destination of packets; you can attach VPCs, VPN connections, VPN Concentrators, Direct Connect gateways, Connect attachments and peering connections.

**Route table rules:**

- An attachment is **associated with one** route table and can **propagate to many**. Propagated routes cannot be filtered.
- A dynamic-routing VPN advertises the routes of its associated route table to the customer gateway over BGP. A Direct Connect gateway attachment advertises its allowed prefixes.
- For the same destination, a static route beats a propagated route, and the propagated route is not shown in the table.
- The Transit Gateway shows only the preferred route. When the same route arrives over DX and VPN, the table shows the DX route; the VPN route appears only after the DX route is no longer advertised.
- Peering attachments support static routes only.

**Route evaluation order:** the most specific route wins first. For the same CIDR from different attachment types, priority is:

1. Static routes (for example, Site-to-Site VPN static routes)
2. System routes (for 1:1 NAT)
3. Prefix-list-referenced routes
4. VPC-propagated routes
5. Direct Connect gateway-propagated routes
6. Transit Gateway Connect-propagated routes
7. Site-to-Site VPN over private Direct Connect-propagated routes
8. Site-to-Site VPN-propagated routes
9. Site-to-Site VPN Concentrator-propagated routes
10. Client VPN-propagated routes
11. Transit Gateway peering (Cloud WAN)-propagated routes

Only for the same CIDR from the **same attachment type** are BGP attributes compared: shorter AS_PATH, then lower MED, then eBGP over iBGP where supported. Routes advertised without MED get a default of 0 on Direct Connect attachments and 100 on VPN and Connect attachments. ECMP is not supported between different attachment types (for example, VPN and VPC); the evaluation order above picks one route instead.

**MTU and bandwidth:** traffic between VPCs, Direct Connect, Connect and peering attachments has an 8500-byte MTU; traffic over VPN has 1500. The Transit Gateway applies MSS clamping to all packets. Path MTU Discovery is supported only for traffic entering on VPC and Connect attachments, not on VPN, Direct Connect or peering attachments. Bandwidth for a VPC attachment and for a Direct Connect gateway is up to 100 Gbps per direction per Availability Zone.

<a id="failover-design"></a>

## 6. Failover design: DX primary, VPN backup

Read this section **per direction**. The on-premises-to-AWS path is chosen by **your router's policy**; the AWS-to-on-premises path is chosen by **AWS's evaluation order**. Change only one side and the paths go asymmetric, and a stateful firewall may drop the replies.

![Hybrid failover animation. ① The on-premises router (AS 65010, 10.10.0.0/16) learns two BGP paths to VPC 10.20.0.0/16, over DX and over VPN, picks the DX path with LOCAL_PREF 200, and sends a packet to 10.20.1.10 on the DX connection's 802.1Q VLAN 101 (transit VIF). ② Past the DX location the packet reaches the Transit Gateway with its destination unchanged, and the TGW route table forwards it to the VPC attachment. The DX gateway only reflects BGP routes and is not in the data path. ③ The DX link is cut. When BFD misses three replies at 300 ms intervals, the BGP session goes down, the DX routes are withdrawn on both sides, and the on-premises best path changes to the VPN tunnel with LOCAL_PREF 100. ④ The next packet takes the VPN path: IPsec adds ESP and an outer IP header (source 203.0.113.10, destination 198.51.100.10) and the packet crosses the internet. ⑤ On the Transit Gateway's VPN attachment the ESP is removed and the original packet to 10.20.1.10 is forwarded to the VPC. Return traffic also uses the VPN-propagated route because the DX route is gone.](../../.gitbook/assets/en-networking-expert-07-wan-hybrid-connectivity-anim-0.svg)

### AWS to on-premises: the path AWS picks

**On a Transit Gateway**, the evaluation order from section 5 applies as written:

1. **Longest prefix first.** If on-premises advertises `10.10.1.0/24` over VPN and `10.10.0.0/16` over DX, traffic to `10.10.1.0/24` goes over the VPN. To keep DX primary, advertise **identical prefixes** on both paths.
2. **For the same CIDR, attachment type beats AS_PATH.** DX gateway-propagated routes always outrank VPN-propagated routes, so prepending AS_PATH on the VPN advertisements does nothing for the DX-versus-VPN choice. Conversely, a **static route** on the VPN outranks the DX-propagated route and silently makes the VPN primary. Build the backup VPN with BGP.
3. **BGP attributes are compared only within one type**, for example between several DX VIFs or between several VPN connections.

**On a VGW**, the list is different: for the same prefix, Direct Connect BGP routes beat VPN static routes, which beat VPN BGP routes; among VPN BGP routes the shorter AS_PATH wins, then the lower MED when the first AS matches. Do not merge the two lists.

**Between several DX VIFs**, AWS compares private and transit VIF routes in this order:

| Order | Criterion | How designs use it |
|---|---|---|
| 1 | Longest prefix | Express active/passive with more-specific routes |
| 2 | Local preference community | `7224:7300` (high), `7224:7200` (medium), `7224:7100` (low); standard communities, evaluated before AS_PATH. Extended communities such as route targets are not evaluated for preference and may be removed |
| 3 | AS_PATH length | Prepend when prefix and local preference are equal |
| 4 | MED | Lowest priority; AWS does not recommend relying on it |
| Tie | ECMP | Same AS_PATH length and attributes load-share across VIFs |

Without communities, an AWS Region prefers Direct Connect locations **associated with that Region**. For active/active, apply the same community (for example `7224:7200`) to all VIFs; for active/passive, apply `7224:7300` to the primary VIF and `7224:7100` to the backup. These communities set the preference for traffic **returning** to on-premises.

**Loop prevention:** AWS treats a route whose AS_PATH contains the Direct Connect ASN `7224` two or more times as a loop and does not install it. That happens when routes learned from AWS over one VIF are re-advertised over another; filter AWS-learned routes out of what you advertise to AWS.

### On-premises to AWS: the path your router picks

AWS advertises the same VPC route over DX (the allowed prefixes) and over VPN (the routes in the TGW route table). Your router compares them with the BGP selection rules from workbook 02, so a higher LOCAL_PREF on DX-learned routes makes DX primary. The animation's LOCAL_PREF 200/100 is that policy.

**The allowed-prefix trap:** if the allowed prefix is summarized as `10.0.0.0/8` while the VPN advertises `10.20.0.0/16` from the TGW route table, your router picks the **longer VPN prefix**. LOCAL_PREF only compares paths for the same prefix and cannot fix this. Match the allowed prefix length to the VPN side, or summarize the VPN-learned routes the same way on your router.

### Detection time budget

| Mechanism | Value | Nature of the source |
|---|---|---|
| BFD on DX | Asynchronous BFD is enabled automatically on the AWS side but takes effect only when configured on your router; minimum interval 300 ms, multiplier 3 | Direct Connect FAQ and user guide |
| DX BGP without BFD | The session drops after a 90-second hold time without keepalives | AWS Knowledge Center |
| VPN BGP | Default hold time 30 seconds | AWS Knowledge Center |
| VPN DPD | 30 seconds or higher; timeout action `Clear`, `None` or `Restart` | VPN user guide |

When BFD detects a failure, the BGP neighbor relationship is torn down quickly instead of waiting for the hold time to expire. Under RFC 5880, BFD detection time is the remote multiplier times the negotiated interval, so 300 ms × 3 is about 0.9 seconds. But **detection time is not recovery time.** Recovery adds route withdrawal and propagation, FIB programming on both routers and the reverse-direction switch, and AWS publishes no fixed values for those. In a design document, cite the detection values and label the rest **assumptions until measured**, using workbook 02's measurement points (action time, first change, FIB change, sustained recovery).

## 7. MTU and MSS across tunnels

| Segment | MTU | Notes |
|---|---|---|
| Site-to-Site VPN | Up to 1446 bytes, MSS 1406 | No jumbo frames and no Path MTU Discovery; smaller with some algorithms and NAT-T |
| Private VIF | 1500 or 9001 | Link-layer frames of 1522 or 9023 bytes |
| Transit VIF | 1500 or 8500 | Jumbo frames on Transit Gateways support only 8500 |
| Transit Gateway | 8500 between VPC, DX, Connect, peering; 1500 over VPN | MSS clamping on all packets; PMTUD only for VPC and Connect ingress |

AWS's recommended VPN MTU/MSS values, for example (IPv4 MSS):

| Encryption | Integrity | NAT-T | MTU | MSS |
|---|---|---|---|---|
| AES-GCM-16 | N/A | disabled | 1446 | 1406 |
| AES-GCM-16 | N/A | enabled | 1438 | 1398 |
| AES-CBC | SHA1/SHA2-256 | disabled | 1438 | 1398 |
| AES-CBC | SHA2-512 | enabled | 1406 | 1366 |

**Behavior:**

- AWS recommends that the customer gateway fragment **before encryption**. The VPN reassembles fragments before forwarding, so also check that the reassembled packet fits the next segment (for example, Direct Connect).
- Changing a VIF to jumbo MTU can update the underlying connection, which disrupts every VIF on it for up to 30 seconds; make the change in a maintenance window.
- If two private VIFs advertise the same route with different MTUs, or a Site-to-Site VPN advertises the same route, 1500 MTU is used.

**Design point:** in a failover design, **the MTU that matters is the backup path's.** A TCP connection established over DX with a large MSS that moves to the VPN can have its large DF-set packets dropped without notice on segments that do not support PMTUD. In this exercise, compare two options: clamp the MSS of hybrid flows on your router to the VPN value for the chosen algorithm, or keep the VIF at 1500 while VPN is the backup.

## 8. Bandwidth, latency and cost trade-offs

| Connection | Bandwidth (official limit) | Latency and quality | Redundancy unit | Cost elements |
|---|---|---|---|---|
| DX dedicated | 1/10/100/400 Gbps, bundled with LAG | Dedicated path that bypasses internet service providers | Connection, device, location (Resiliency Toolkit models) | Port hours, outbound data transfer |
| DX hosted | 50 Mbps to 25 Gbps | Crosses the partner network; AWS polices to the contracted rate | Per hosted connection, partner network | Same AWS elements plus partner charges |
| VPN standard tunnel | Up to 1.25 Gbps, 140,000 PPS per tunnel | Internet path, best effort | Two tunnels (AWS side); customer gateway and circuit are separate | Connection hours, outbound data transfer, public IPv4 per tunnel |
| VPN Large Bandwidth Tunnel | Up to 5 Gbps per tunnel (TGW and Cloud WAN only) | As standard; same MTU limit | As above | Separate connection-hour price |
| VPN ECMP on TGW | Sum of several dynamic-routing tunnels | Per-flow distribution; one flow is capped by one tunnel | Per tunnel and connection | VPN charges plus TGW attachment hours and per-GB processing |
| Connect (SD-WAN) | 5 Gbps per peer, 4 peers per attachment | Follows the transport underneath (VPC or DX) | Per peer and attachment | TGW attachment hours plus the transport attachment's processing |

A Transit Gateway charges per attachment hour and per GB of data processed from VPC, Direct Connect and VPN attachments. Unit prices vary by Region and over time, so the design records **cost elements** only; compute amounts from the pricing pages on the day you check them.

## 9. Design exercise: two sites and one region

This is a desk check that creates no resources. Label results **design review**.

**Inputs:**

| Location | Addresses and ASN | Connectivity |
|---|---|---|
| Site A (headquarters data center) | `10.10.0.0/16`, AS 65010 | One 10 Gbps dedicated connection at each of two different DX locations (DX-1, DX-2), one transit VIF on each; one internet circuit with one customer gateway |
| Site B (branch) | `10.30.0.0/16`, AS 65030 | Two internet circuits from different carriers, one customer gateway and one VPN connection per circuit; no DX |
| Region | VPC `10.20.0.0/16`, a Transit Gateway (example Amazon ASN 64512), a Direct Connect gateway (example ASN 64513) | The DX gateway and three VPNs attach to the same TGW |

Site A to Site B traffic uses the existing MPLS service and is out of scope. Assume every VPN uses BGP, IKEv2 and AES-GCM with NAT-T disabled.

**Service level objectives:** these are the learner's design targets, not AWS SLAs.

- Site A → VPC: keep at least 5 Gbps through the failure of any one DX connection, device or location, and aim for both-direction data path recovery within 5 seconds of failure detection. If both DX connections fail, degraded operation over VPN is acceptable.
- Site B → VPC: stay connected through the failure of one circuit or customer gateway; switching within the BGP hold time is acceptable.

**Tasks:**

1. **Advertisement table:** for every path, record who advertises which prefixes: the DX gateway's allowed prefixes, the TGW route table routes each VPN receives, and what Sites A and B advertise to AWS. Compare against quotas (100 per DX BGP session by default, 200 per TGW).
2. **Policy table:** set Site A's LOCAL_PREF (DX-1, DX-2, VPN), the local preference communities on the DX VIFs, and the TGW route table associations and propagations. Decide active/active or active/passive for the two DX connections from the 5 Gbps objective.
3. **Path prediction:** for each scenario below, record the Site A → VPC, VPC → Site A, Site B → VPC and VPC → Site B paths, with **the rule step** that picks each (for example, "TGW evaluation order step 5, DX gateway-propagated").
4. **Time budget:** for each scenario, record the detection mechanism and its value, list the items you hold as assumptions until measured, and judge the objective met or missed.
5. **MTU decision:** choose the transit VIF MTU and Site A's MSS clamp, with the reason.

| Scenario | Site A → VPC | VPC → Site A | Rule applied | Detection | Bandwidth left | Verdict |
|---|---|---|---|---|---|---|
| Normal | | | | | | |
| DX-1 connection fails | | | | | | |
| DX location 1 fails entirely | | | | | | |
| DX-1 and DX-2 both fail | | | | | | |
| DX-1 fails with BFD not configured on Site A's router | | | | | | |
| One Site B circuit fails | | | | | | |
| DX-1 recovers | | | | | | |

**Review criteria:** every cell cites at least one rule from the source documents. Check yourself:

- Did you explain why VPC → Site A uses DX in the normal state with the TGW evaluation order, not with "DX is faster"?
- Did you avoid static routes on the VPN? If you used one, did you find that the VPN wins even in the normal state?
- Are the allowed prefixes and the VPN-advertised prefixes the same length? If not, which direction leaks onto the VPN?
- Did you find that the missing-BFD scenario misses the 5-second objective (90-second BGP hold time)?
- With both DX connections down, did you record that bandwidth drops to VPN limits (1.25 Gbps per standard tunnel, the tunnel sum with ECMP) and that one flow cannot exceed one tunnel?
- Did you size the MTU from the backup path?

## 10. Observing failure and recovery

Without a real environment, this section is practice in deciding **what evidence would settle each verdict**. If you later get to reproduce a scenario in an approved existing environment, collect this evidence.

| Layer | What to look at | What that evidence alone does not establish |
|---|---|---|
| Your router's BGP table | Both candidate paths, LOCAL_PREF, best-path marker | The AWS-side return path |
| Your router's FIB and a capture | The actual egress interface, ESP on the tunnel interface | Success of every application flow |
| TGW route table | The single preferred route; the backup VPN route appears only after the DX route is withdrawn | The path packets actually took |
| CloudWatch | VPN `TunnelState`, DX VIF `VirtualInterfaceBgpStatus` | When data-plane loss started and ended |
| Source-specific probes | Loss interval, start of sustained recovery | Large packets or every port |

**Failback is a failure too.** When DX returns and BGP re-establishes, the DX gateway-propagated route wins again on the TGW and the higher-LOCAL_PREF DX route wins again on your router, so traffic moves back **automatically**, with another path change and MTU change. An unstable link can make the path flip repeatedly; define the sustained-recovery criterion (for example, consecutive replies and an observation window) in advance. As in workbook 02, zero observed loss only means the sampling resolution did not catch an interruption.

## 11. Deliverables and completion criteria

| Deliverable | Done when |
|---|---|
| Topology drawing | Sessions and data links are distinct, and the DX gateway sits outside the data path |
| Advertisement and policy tables | Allowed prefixes, VPN advertisements, LOCAL_PREF, communities and TGW associations/propagations are all recorded and checked against quotas |
| Scenario table | All seven scenarios have both-direction paths, the rule applied, detection values, remaining bandwidth and a verdict |
| MTU decision | An MSS value sized from the backup path, with its source table |
| Unknowns list | Items without published fixed values, such as route propagation and FIB programming time, are labelled assumptions until measured |

You are done when you can explain, with sources, the per-direction selection rules, how attachment-type order relates to AS_PATH, the allowed-prefix trap, the difference between detection and recovery time, and why the backup path sets the MTU. Feed the result tables into the change review of the [automation capstone](06-automation-capstone.md), and continue with in-cloud paths in [Cloud and CNI Design](05-cloud-cni-design.md). For cross-organization VPC options see [Cross-Org VPC Connectivity](../05-cross-org-vpc-connectivity.md), and for EKS Hybrid Nodes network requirements see [Hybrid Nodes Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md). Finally, take the [quiz](../../quizzes/networking/expert/07-wan-hybrid-connectivity-quiz.md).

## References

AWS Direct Connect

- [What is Direct Connect?](https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html) (VIF types, network requirements, BFD, pricing elements)
- [Direct Connect quotas](https://docs.aws.amazon.com/directconnect/latest/UserGuide/limits.html)
- [Hosted connections](https://docs.aws.amazon.com/directconnect/latest/UserGuide/hosted_connection.html)
- [Virtual interfaces and MTU](https://docs.aws.amazon.com/directconnect/latest/UserGuide/WorkingWithVirtualInterfaces.html)
- [Routing policies and BGP communities](https://docs.aws.amazon.com/directconnect/latest/UserGuide/routing-and-bgp.html)
- [Direct Connect gateways](https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html), [Allowed prefixes interactions](https://docs.aws.amazon.com/directconnect/latest/UserGuide/allowed-to-prefixes.html)
- [Link aggregation groups](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html), [MAC Security](https://docs.aws.amazon.com/directconnect/latest/UserGuide/MACsec.html), [Resiliency Toolkit](https://docs.aws.amazon.com/directconnect/latest/UserGuide/resiliency_toolkit.html)
- [Direct Connect FAQ](https://aws.amazon.com/directconnect/faqs/) (BFD defaults, MACsec-capable connections)
- [AWS Knowledge Center: Enable BFD for Direct Connect](https://repost.aws/knowledge-center/enable-bfd-direct-connect) (90-second BGP hold time without BFD)
- [CloudWatch metrics for Direct Connect virtual interface BGP health](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudwatch-metrics-for-aws-direct-connect-virtual-interface-bgp-health-and-prefix-count/)

AWS Site-to-Site VPN

- [Tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html), [Configure tunnel options](https://docs.aws.amazon.com/vpn/latest/s2svpn/tunnel-configure.html)
- [Routing options](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html), [Static and dynamic routing](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-static-dynamic.html), [Route tables and route priority](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-route-priority.html)
- [Site-to-Site VPN quotas](https://docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html) (bandwidth, PPS, MTU, route counts)
- [Best practices for a customer gateway device](https://docs.aws.amazon.com/vpn/latest/s2svpn/cgw-best-practice.html) (IKEv2, fragmenting before encryption, per-algorithm MTU/MSS)
- [Monitor VPN tunnels using CloudWatch](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [AWS Knowledge Center: Troubleshoot a VPN tunnel with BGP logs](https://repost.aws/knowledge-center/vpn-bgp-logs-troubleshoot-tunnel) (30-second default hold time)
- [AWS VPN pricing](https://aws.amazon.com/vpn/pricing/)

AWS Transit Gateway

- [How AWS Transit Gateway works](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html) (attachments, association and propagation, route evaluation order, ECMP)
- [Transit Gateway quotas](https://docs.aws.amazon.com/vpc/latest/tgw/transit-gateway-quotas.html) (bandwidth, MTU, MSS clamping, PMTUD)
- [AWS Transit Gateway pricing](https://aws.amazon.com/transit-gateway/pricing/)

Standards and vendor documents

- [RFC 5880: Bidirectional Forwarding Detection](https://www.rfc-editor.org/rfc/rfc5880.html)
- [RFC 7296: IKEv2](https://www.rfc-editor.org/rfc/rfc7296.html), [RFC 4303: ESP](https://www.rfc-editor.org/rfc/rfc4303.html), [RFC 3948: UDP Encapsulation of IPsec ESP Packets](https://www.rfc-editor.org/rfc/rfc3948.html)
- [RFC 4271: BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html), [RFC 1997: BGP Communities](https://www.rfc-editor.org/rfc/rfc1997.html), [RFC 6996: Autonomous System Reservation for Private Use](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html), [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) (example addresses)
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/)
- [Cisco Catalyst SD-WAN High Availability Configuration Guide](https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/ha-scaling/ios-xe-17/high-availability-book-xe/m-high-availability-and-scaling.html)

Exam scope (used only to choose topics)

- [AWS Certified Advanced Networking - Specialty (ANS-C01) exam guide](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
- [Cisco 350-401 ENCOR](https://www.cisco.com/site/us/en/learn/training-certifications/exams/encor.html)
