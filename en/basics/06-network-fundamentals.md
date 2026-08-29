# Network Fundamentals — 25 Protocols

> **Last Updated**: August 28, 2026

::: tip Where this document fits
This covers the network fundamentals you need before reading the Cilium, Calico, and Istio deep dives.
If you already know BGP, TLS, and gRPC, feel free to skip ahead to those documents. If eBPF is new to you, read [eBPF Fundamentals](./05-ebpf-fundamentals.md) alongside this one.
:::

The moment you type an address into a browser and press Enter, at least ten protocols fire in sequence. We usually only think about one of them — HTTP — but when something breaks, the failure is almost always in the other nine.

This document walks through the 25 protocols that actually keep the internet running, **layer by layer, from the bottom up**. The reason for building from the bottom is simple: every upper layer is designed on the assumption that the layers below it already work. Read top-down and you keep hitting "but how does *that* part work?"

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

## 1. Link Layer — Moving Bits Within One Segment

The link layer cares about exactly one thing: **how to hand bits to the device sitting right next to you.** Whether the final destination is the next rack or the other side of the planet, this layer is only responsible for the next hop.

### Ethernet

**Definition:** The link-layer standard that carries frames on wired local networks.

**How it works:** Data is wrapped into frames, with destination and source MAC addresses in front. A switch consults its MAC address table and forwards the frame only to the matching port. Early Ethernet relied on collision detection (CSMA/CD), but in modern switched full-duplex networks collisions have essentially disappeared.

**In practice:** MTU is decided here. The default is 1500 bytes; jumbo frames are 9001. In the cloud, layering a VPN or overlay network on top adds encapsulation headers that shrink the effective MTU, and the resulting MTU black hole shows up as "ping works, but large responses hang." It is one of the failure modes that takes the longest to diagnose.

### Wi-Fi

**Definition:** The link-layer standard that carries LAN frames over a wireless segment (IEEE 802.11).

**How it works:** Because the air is a shared medium, Wi-Fi is fundamentally different from Ethernet. Collisions cannot be *detected*, so they are *avoided* (CSMA/CA): check that the channel is clear before sending, then wait for an ACK afterward. In other words, retransmission is already built into the link layer.

**In practice:** Link-layer retransmission stacked on top of TCP retransmission inflates latency variance (jitter). Real-time quality problems get reported as "the server's fault" when the actual culprit is the client's wireless segment. To tell them apart from logs, look at the server-side RTT distribution.

### VLAN

**Definition:** A technique for slicing one physical switch into multiple logical L2 networks (IEEE 802.1Q).

**How it works:** A 4-byte tag inserted into the Ethernet frame carries the VLAN ID. Broadcasts only reach hosts in the same VLAN, so you can segment a network without touching the cabling. Traffic between VLANs must pass through an L3 device (a router or L3 switch).

**In practice:** VLANs have long been the basic tool for network separation in regulated industries such as finance. But a VLAN is logical separation, not physical — where regulation demands physical isolation, a VLAN does not qualify on its own. In the cloud, this role is taken over by VPCs, subnets, and security groups.

> 📎 For how EKS structures its VPC, see [EKS Networking Fundamentals](../eks/03-eks-networking-part1.md).

### PPP

**Definition:** A protocol that carries packets over a point-to-point link connecting exactly two nodes.

**How it works:** Unlike Ethernet, no addressing is needed — there is only one node at each end of the link. Instead, PPP provides link establishment, authentication, and upper-protocol negotiation (LCP/NCP).

**In practice:** It looks like a relic of the dial-up era, but it survives as PPPoE on a large share of residential internet lines. The 8-byte PPPoE header shaves the MTU down to 1492 — one of the classic causes of the MTU problems described above.

### ARP

**Definition:** The protocol that resolves an IP address to a MAC address on the same network.

**How it works:** The IP layer says "send this to 10.0.1.5," but Ethernet only understands MAC addresses. So the host broadcasts "who has 10.0.1.5?" and the owning host replies. The result is cached in the ARP cache for a few minutes.

**In practice:** ARP has no authentication. Anyone can answer "that IP is mine," which is exactly what makes ARP spoofing possible. The same property is also used legitimately: on failover, the new active node broadcasts a Gratuitous ARP to refresh the switches' MAC tables. When a VIP-based HA setup fails over slowly, delayed cache refresh is a prime suspect.

> 📎 For how Cilium replaces this layer with eBPF, see [Cilium Networking](../networking/cilium/03-networking.md).

---

## 2. Internet and Routing Layer — Crossing Networks

If the link layer gets you "next door," this layer gets you "to the other side of the planet." The central question is: **where should this packet go next?**

### IPv4

**Definition:** The internet-layer protocol built on 32-bit addresses.

**How it works:** Every packet carries source and destination IPs; each router finds the most specific route (longest prefix match) in its routing table and forwards to the next hop. Delivery is best-effort — no guarantees, no ordering. Those guarantees are the job of the layer above (TCP).

**In practice:** The address space — about 4.3 billion — is long exhausted. That made NAT effectively mandatory and turned the private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) into the internal-network standard. The first wall large organizations hit during cloud migration is overlap in these private ranges: if on-premises and VPC CIDRs collide, routing cannot work over VPN or Direct Connect. IP address design is something to lock down at project kickoff.

### IPv6

**Definition:** The next-generation internet-layer protocol with 128-bit addresses.

**How it works:** With 128-bit addresses, exhaustion is a non-issue. The header is simpler, cutting router processing overhead, and in-router fragmentation was abolished. SLAAC lets hosts self-configure addresses without DHCP, and ARP is replaced by NDP (Neighbor Discovery Protocol).

**In practice:** IPv6 is not backward-compatible with IPv4, so real deployments run dual stack — which means maintaining two sets of firewall rules and security policies. Missing rules on the IPv6 path is a common security gap. Also note that in the cloud IPv6 works without NAT, so "directly reachable from the internet" becomes the default posture.

### ICMP

**Definition:** The control protocol that reports network errors and state.

**How it works:** ICMP carries no user data — only control messages: destination unreachable, TTL exceeded, fragmentation needed, and so on. `ping` uses Echo Request/Reply; `traceroute` increments TTL one hop at a time and reads the returning Time Exceeded messages.

**In practice:** Blanket-blocking ICMP "for security" is common — and it is the direct cause of the MTU black hole mentioned earlier. Path MTU Discovery depends on ICMP Fragmentation Needed messages; block them and there is no way to learn the path MTU. At minimum, let Type 3 Code 4 through.

> 📎 For how this failure shows up in EKS, see [EKS Networking Deep Dive](../eks/03-eks-networking-part3.md).

### OSPF

**Definition:** A link-state routing protocol that computes optimal paths inside a single autonomous system.

**How it works:** Every router floods its link state across the area, so all routers hold an identical topology database, then each runs Dijkstra's algorithm to compute shortest paths. Costs are bandwidth-based, and networks are split into areas to scale.

**In practice:** OSPF is an IGP — for internal networks. Convergence is fast and paths are found automatically, but every router must hold the full topology, so at scale, area design determines performance.

### BGP

**Definition:** A path-vector routing protocol that exchanges reachability between autonomous systems (ASes).

**How it works:** BGP's goal differs from OSPF's: it picks not "the fastest path" but "the path policy prefers." Each AS advertises the prefixes it can reach along with the AS path; receivers rank routes by attributes such as AS_PATH length, Local Preference, and MED. Routing for the entire internet rests on this.

**In practice:** BGP trusts advertisements by default, which is why a single bad prefix advertisement has repeatedly caused continent-scale outages; RPKI-based route validation is spreading as the countermeasure. From a cloud perspective, Direct Connect and Site-to-Site VPN exchange routes over BGP, so AS numbers, advertised prefix design, and path preference for redundancy (AS_PATH prepending and friends) become real design items.

> 📎 For how Calico uses BGP inside a cluster, see [Calico BGP Deep Dive](../networking/calico/04-bgp-deep-dive.md).

### NAT

**Definition:** A network function that rewrites the IP addresses and ports of packets.

**How it works:** NAT translates private IPs to public ones, letting many internal hosts share a single public IP (PAT/NAPT). A translation table keeps per-session mappings so return packets find their way back to the right internal host.

**In practice:** NAT is the poster child for layering violations: an L3 device that rewrites L4 ports, and it breaks end-to-end connectivity — the internet's original premise. As a result P2P becomes hard, and workarounds such as STUN/TURN become necessary (see WebRTC below). In the cloud, NAT Gateway port exhaustion and data processing charges are the practical issues. For outbound-heavy workloads, routing around NAT with VPC endpoints makes a meaningful cost difference.

---

## 3. Transport Layer — End-to-End Delivery

From here on, your conversation partner is not a "network" but a "process." That is why port numbers appear.

### TCP

**Definition:** A connection-oriented transport protocol providing a reliable, ordered byte stream.

**How it works:** A 3-way handshake (SYN → SYN+ACK → ACK) establishes the connection. Sequence numbers preserve order, ACKs and retransmission recover losses, sliding windows control flow, and congestion control adapts to network load. To the application, TCP presents a clean abstraction: a gapless stream of bytes.

**In practice:** The price of that abstraction is **head-of-line (HOL) blocking**. Guaranteeing order means that if an earlier segment is lost, later data — even if already received — cannot be delivered to the application. When HTTP/2 multiplexed many streams over one TCP connection, a single lost packet stalled *all* streams. That is precisely why QUIC exists.

Handshake cost is not negligible either: 1 RTT per connection, plus 1–2 more RTTs for TLS. On high-latency paths, connection reuse and connection-pool tuning dominate performance.

### UDP

**Definition:** A minimal transport protocol that sends datagrams with no connection setup.

**How it works:** The 8-byte header carries only source port, destination port, length, and checksum. No handshake, no retransmission, no ordering, no congestion control. It is essentially "IP with port numbers."

**In practice:** The missing features are a choice, not a flaw. For real-time audio/video, "an imperfect frame on time" beats "a perfect frame late." For one-shot exchanges like DNS queries, a handshake is wasted cost. And any reliability you do need, the application can build itself — which is exactly the road QUIC took.

The caveat: being stateless makes UDP easy to abuse for spoofing and amplification attacks. When exposing UDP services externally, plan for response-size limits and request-rate control.

### QUIC

**Definition:** A secure, multiplexed transport protocol implemented on top of UDP.

**How it works:** QUIC redesigns, from scratch on UDP, everything TCP+TLS used to do. Four key properties:

1. **Independent streams** — one connection carries many streams, each recovering losses independently. TCP's HOL blocking disappears structurally.
2. **Built-in encryption** — TLS 1.3 is part of the protocol itself. With no separate negotiation phase, connection setup is 1 RTT, and 0 RTT on resumption.
3. **Connection IDs** — the connection survives IP or port changes. Switching from Wi-Fi to cellular does not drop the session.
4. **User-space implementation** — it lives in the application, not the kernel, so congestion-control improvements ship without OS updates.

**In practice:** Where firewalls block UDP 443, QUIC cannot run and falls back to TCP. In environments with strict UDP policies — regulated financial networks are a typical example — HTTP/3's benefits often never materialize, so "we enabled HTTP/3, why isn't it faster?" starts with checking this. Also, user-space processing costs more CPU than kernel TCP.

---

## 4. Security — TLS

### TLS

**Definition:** The protocol providing confidentiality, integrity, and authentication for data in transit.

**How it works:** TLS has a handshake phase and a record phase. The handshake negotiates a cipher suite, verifies the server's identity via its certificate, and derives session keys through key exchange. The record phase then encrypts data with those session keys and verifies integrity with MACs.

TLS 1.3 was a major cleanup: the handshake dropped to 1 RTT (0 RTT on session resumption), RSA key exchange and weak cipher suites were removed, and forward secrecy became effectively mandatory.

**In practice:** Three things go wrong over and over.

- **Certificate expiry** — still a top-tier outage cause. Automate renewal *and* monitor expiry as two separate safeguards.
- **SNI exposure** — even in TLS 1.3, the target domain travels in plaintext. ECH tries to hide it — which, ironically, collides with regulated environments that require traffic visibility.
- **Termination point design** — terminate TLS at the load balancer and go plaintext behind it, or encrypt end to end? Where regulation demands encryption of internal segments too (common in finance), mTLS or a service mesh (such as Istio) is the increasingly standard answer.

> 📎 For how Istio automates this, see [Istio mTLS](../service-mesh/istio/security/01-mtls.md).

---

## 5. Application Layer — Actual Services

### DNS

**Definition:** The distributed directory system that resolves domain names into IP addresses and other records.

**How it works:** DNS is hierarchical delegation. A resolver walks down from root → TLD → authoritative nameserver, caching each step's answer for its TTL. Record types map to purposes: A/AAAA for IPs, CNAME for aliases, MX for mail servers, TXT for verification strings.

**In practice:** DNS is close to being the internet's single point of failure — a large share of major outages start there. The part that matters most in operations is **TTL and caching**. If your failover plan relies on DNS, know that even with a short TTL, some clients and intermediate resolvers simply do not honor it, so cutover takes far longer than expected. If you need fast failover, handle it in front of DNS — at the anycast or load-balancer level.

### DoH

**Definition:** DNS queries wrapped in and transported over HTTPS.

**How it works:** Traditional DNS goes out in plaintext over UDP 53 — anyone on the path can see who is looking up what. DoH turns the query into an HTTPS request, encrypting it and making it indistinguishable from ordinary web traffic.

**In practice:** A privacy improvement and a management headache at the same time: enterprise DNS-based filtering and logging stop working. When a browser uses its own DoH resolver, it bypasses the organization's internal DNS and internal-domain resolution can break. In regulated environments, the usual pairing is browser policy that disables DoH plus enforcement of the organization's resolver.

### DHCP

**Definition:** The protocol that automatically assigns hosts an IP address and network configuration.

**How it works:** Four steps — DORA: Discover (client broadcast) → Offer (server proposal) → Request (client's choice) → Acknowledge (server's confirmation). It hands out not just an IP but also the subnet mask, default gateway, and DNS server addresses. Assignments carry a lease and are renewed before expiry.

**In practice:** In the cloud it is mostly abstracted away, but you meet it again in the VPC DHCP option set, which is where DNS servers and domain names are configured. When name resolution breaks in a hybrid setup that uses on-premises DNS, this is the setting to check.

### SSH

**Definition:** The protocol providing encrypted remote shell access and tunneling.

**How it works:** The server authenticates itself with its host key, a key exchange derives session keys, and then the user authenticates (public key or password). All subsequent traffic is encrypted. Beyond remote shells, SSH supports port forwarding, SFTP, and agent forwarding.

**In practice:** The convenient tunneling features are also its security holes. Local/remote forwarding can bypass firewalls, and agent forwarding exposes your keys if an intermediate server is compromised. SSH keys never expire, so keys belonging to long-departed employees staying alive for years is a recurring incident.

This is why cloud practice trends toward eliminating SSH altogether: replace it with a session manager or IAM-based access and you open no port 22, distribute no keys, and every session lands in the audit log. In audit-heavy environments that difference is decisive.

### SMTP

**Definition:** The protocol that relays messages between mail servers.

**How it works:** The sending client submits a message to its server; servers look up MX records and relay the message hop by hop to its destination. Receiving mail is not SMTP's job — that belongs to IMAP/POP3.

**In practice:** The original design had no authentication, so sender forgery was free — the foundation of spam and phishing. What matters in practice today is not SMTP itself but the **three authentication layers** on top of it:

- **SPF** — publish in DNS the list of IPs allowed to send for this domain
- **DKIM** — sign messages with a domain key to detect forgery and tampering
- **DMARC** — declare the policy and reporting for SPF/DKIM failures

Skip any of the three and your deliverability drops — and you cannot stop your domain from being impersonated.

### HTTP/3

**Definition:** The third major version of HTTP, running on QUIC.

**How it works:** The semantics — methods, status codes, headers — are essentially those of HTTP/2; only the transport changed, from TCP+TLS to QUIC. The gains are exactly what QUIC provides: HOL blocking gone via independent streams, 1-RTT connection setup, connections that survive network switches. Header compression moved from HPACK to QPACK (to cope with out-of-order delivery).

**In practice:** There is a discovery problem: how does the client learn HTTP/3 is available? The default is the server advertising it via the `Alt-Svc` header, so the first visit usually happens over TCP and gets upgraded later. HTTPS DNS records can remove that round trip.

The biggest wins come on **lossy, high-latency mobile networks**. Conversely, inside a data center — near-zero loss, short RTTs — the improvement is small and the CPU overhead can make it a net negative. Decide based on your actual users' network profile.

### WebSocket

**Definition:** An application protocol for bidirectional messaging over a single connection.

**How it works:** It starts as an HTTP request and switches protocols via the `Upgrade` header. After the switch, the request-response model is gone: server and client send frames symmetrically. Server push no longer requires polling.

**In practice:** Everything hard about operating WebSockets stems from one fact: it is a stateful, long-lived connection. Load balancer idle timeouts kill it (keep-alive with ping/pong frames), deployments sever every connection at once and trigger reconnection storms (exponential backoff with jitter), and scaling out requires sharing per-instance connection state (Redis Pub/Sub or similar). Whether proxies and firewalls pass the `Upgrade` handshake correctly is another standing checklist item.

### WebRTC

**Definition:** A framework for browsers to exchange real-time media and data peer-to-peer.

**How it works:** Here the NAT problem meets you head-on: if both peers sit behind NAT, neither can connect directly to the other. The ICE framework gathers candidate paths — learn your public IP and port via a STUN server, attempt hole punching with it, and if that fails, relay traffic through a TURN server. Media travels over SRTP; data channels use SCTP over DTLS.

**In practice:** The TURN relay ratio drives your costs. When P2P succeeds, server cost is near zero; behind symmetric NAT, relaying is unavoidable and bandwidth bills follow. Enterprise networks with strict firewall policies push this ratio up. For meetings with many participants, the standard answer is an SFU, not a P2P mesh.

### gRPC

**Definition:** A schema-based RPC framework running over HTTP/2.

**How it works:** Define services and messages in Protocol Buffers, and client/server code is generated. Binary serialization is smaller and faster than JSON, and on top of HTTP/2 multiplexing it supports unary calls plus server, client, and bidirectional streaming.

**In practice:** A great fit for internal service-to-service communication, a weaker fit for public APIs: browsers cannot call it directly (you need gRPC-Web and a proxy), and it is not human-readable, which makes debugging tedious.

Load balancing is the classic trap. gRPC holds one long-lived TCP connection and multiplexes requests over it, so an L4 load balancer — which balances per connection — piles traffic onto a few backends. You need L7 load balancing, client-side load balancing, or a service mesh. Also respect schema-evolution rules (never reuse field numbers, etc.), or compatibility breaks depending on deployment order.

> 📎 For gRPC handling in Istio, see [Istio gRPC Advanced](../service-mesh/istio/advanced/05-grpc.md).

### MQTT

**Definition:** A lightweight publish-subscribe messaging protocol.

**How it works:** Clients connect to a broker and publish or subscribe to topics; publishers and subscribers never need to know each other. The header is as small as 2 bytes, three QoS levels are offered (at most once / at least once / exactly once), and a Last Will message notifies others when a client disappears.

**In practice:** MQTT was designed for narrow bandwidth, flaky connectivity, and constrained power — in other words, IoT. Choosing a QoS level is choosing a cost/complexity trade-off: QoS 2 requires a 4-way handshake and is expensive, so QoS 1 plus application-level idempotency is usually the practical answer. Plan broker clustering so the broker is not a single point of failure, and prefer TLS client certificates for device authentication.

---

## 6. Following One Request All the Way Through

Here is how the pieces above actually interlock, using a visit to `https://example.com` as the example:

1. **DHCP** — at boot, the host receives its IP, gateway, and DNS server addresses.
2. **DNS (or DoH)** — resolve the A/AAAA records for `example.com`; on a cache miss, walk down from the root.
3. **ARP** — the destination is external, so resolve the default gateway's MAC address.
4. **Ethernet / Wi-Fi** — put the packet in a frame and send it to the gateway.
5. **IP + BGP/OSPF** — routers forward hop by hop, each consulting a routing table learned via OSPF internally and BGP externally.
6. **NAT** — at the boundary, the private IP is translated to a public one.
7. **TCP or QUIC** — establish the end-to-end transport connection.
8. **TLS** — verify the certificate and derive session keys. With QUIC, this merges into step 7.
9. **HTTP/3** — send the request, receive the response.
10. **WebSocket / gRPC / WebRTC** — if the page uses real-time features, extra connections open here.

And if anything goes wrong anywhere along the way, **ICMP** tells you — provided you left it open to do so.

---

## 7. Where These Concepts Go in the Cloud

On-premises networking knowledge does not become useless in the cloud — it survives under new names. Mapped to AWS:

| Traditional concept | AWS counterpart |
|---|---|
| VLAN / subnet separation | VPC, subnets, security groups, NACLs |
| Routing tables | VPC route tables, Transit Gateway |
| BGP peering | Direct Connect, Site-to-Site VPN |
| NAT appliance | NAT Gateway, VPC endpoints (to bypass it) |
| DNS servers | Route 53, Resolver endpoints |
| DHCP | VPC DHCP option sets |
| TLS termination | ALB/NLB, ACM, CloudFront |
| L7 load balancing | ALB, App Mesh, Istio |
| SSH access | Systems Manager Session Manager |
| Internal-segment encryption | Service mesh mTLS |

**Three decisions to make first** when designing:

1. **IP address plan** — fix organization-wide CIDRs that do not overlap with on-premises. This is the single most expensive thing to change later.
2. **Outbound path** — through a NAT Gateway, or around it via VPC endpoints? At high traffic volumes the cost difference is substantial.
3. **Encryption termination point** — where does TLS end? This maps directly to regulatory requirements.

---

## Wrapping Up

After walking through all 25, one pattern stands out: **every protocol is a trade — it gives something up to gain something else.**

TCP buys reliability and pays in latency; UDP is the mirror image. QUIC judged TCP's terms a bad deal for modern networks and renegotiated from scratch on top of UDP. NAT solved address exhaustion at the cost of end-to-end connectivity — and WebRTC is still paying that bill via STUN/TURN. DoH gained privacy and lost organizational visibility.

That is why understanding **what trade each protocol made** outlasts memorizing them. When an incident hits, if you can recall "what does this layer guarantee, and what does it not," you can usually narrow the fault domain fast.

---

## Next Documents

From this foundation, move on to cluster networking:

- [eBPF Fundamentals](./05-ebpf-fundamentals.md) — how packets are processed in the kernel
- [Cilium Networking](../networking/cilium/03-networking.md) — the eBPF-based CNI
- [Calico BGP Deep Dive](../networking/calico/04-bgp-deep-dive.md) — BGP routing inside the cluster
- [Amazon VPC CNI](../networking/01-vpc-cni.md) — the VPC CNI and IP allocation

## References

The protocol list was seeded by ByteByteGo's "What Keeps the Internet Running?"
infographic; the explanations and practical commentary were written independently.
