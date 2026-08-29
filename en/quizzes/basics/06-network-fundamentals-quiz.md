# Network Fundamentals Quiz

> **Last Updated**: August 28, 2026

This quiz tests your understanding of the 25 core protocols — from the link layer up to the application layer — that Kubernetes networking is built on.

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

4. What approach did QUIC adopt to structurally eliminate TCP's head-of-line (HOL) blocking?
   - A) Re-establish the entire connection on packet loss
   - B) Recover losses independently per stream within a single connection
   - C) Give up ordering guarantees entirely
   - D) Handle retransmission at the kernel level

<details>
<summary>Show Answer</summary>

**Answer: B) Recover losses independently per stream within a single connection**

**Explanation:**
TCP guarantees the order of a single byte stream, so a lost early segment blocks delivery of later data too (the reason all HTTP/2 streams stalled together). QUIC delivers and recovers per stream, so loss on one stream does not block the others.

</details>

5. When investigating "we enabled HTTP/3, why isn't it faster?", what should you check first?
   - A) The server certificate's expiry date
   - B) Whether the firewall blocks UDP 443, forcing a fallback to TCP
   - C) The DNS TTL settings
   - D) The HTTP/2 header compression (HPACK) settings

<details>
<summary>Show Answer</summary>

**Answer: B) Whether the firewall blocks UDP 443, forcing a fallback to TCP**

**Explanation:**
HTTP/3 runs on QUIC (UDP 443). In environments with strict UDP policies (such as regulated financial networks), QUIC is blocked and traffic falls back to TCP-based HTTP/2, so HTTP/3's benefits never arrive. Also remember that on paths with near-zero loss and short RTTs, the improvement is small to begin with.

</details>

6. Which best explains why NAT is said to "violate the layering model"?
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

7. Which statement about TLS 1.3 is NOT correct?
   - A) The handshake dropped to 1 RTT, and 0 RTT is possible on session resumption
   - B) RSA key exchange and weak cipher suites were removed
   - C) SNI is encrypted by default, so the target domain is not exposed
   - D) Forward secrecy became effectively mandatory

<details>
<summary>Show Answer</summary>

**Answer: C) SNI is encrypted by default, so the target domain is not exposed**

**Explanation:**
Even in TLS 1.3, SNI (the target domain) travels in plaintext. ECH (Encrypted Client Hello) is the attempt to hide it — which partly conflicts with regulated environments that require traffic visibility. The other options are all genuine TLS 1.3 characteristics.

</details>

8. What is the main reason DNS-based failover cuts over far more slowly than expected?
   - A) DNS uses only TCP, so handshake costs are high
   - B) Even with a short TTL, some clients and intermediate resolvers do not honor it
   - C) The root nameservers must approve the update
   - D) A records cannot be changed

<details>
<summary>Show Answer</summary>

**Answer: B) Even with a short TTL, some clients and intermediate resolvers do not honor it**

**Explanation:**
DNS caches expire based on TTL, but some clients and resolvers ignore the TTL and cache longer. If you need fast cutover, handle it in front of DNS — at the anycast or load-balancer level.

</details>

9. From an enterprise network perspective, why is DoH (DNS over HTTPS) a "headache"?
   - A) Because DNS responses grow larger and waste bandwidth
   - B) Because DNS-based filtering and logging stop working, and browsers can bypass the organization's internal DNS
   - C) Because UDP port 53 gets overloaded
   - D) Because it is incompatible with DNSSEC

<details>
<summary>Show Answer</summary>

**Answer: B) Because DNS-based filtering and logging stop working, and browsers can bypass the organization's internal DNS**

**Explanation:**
DoH wraps DNS queries in HTTPS, making them indistinguishable from ordinary web traffic. Privacy improves, but organizational DNS filtering/logging is neutralized, and a browser's own DoH resolver can break internal-domain resolution — so in regulated environments, browser policy controls plus enforcing the organization's resolver usually go together.

</details>

10. You put an L4 load balancer in front of a gRPC service and traffic piles onto specific backends. Why?
    - A) Because Protocol Buffers serialization is asymmetric
    - B) Because gRPC keeps one long-lived TCP connection and multiplexes requests over it, so per-connection balancing cannot spread requests evenly
    - C) Because HTTP/2 header compression breaks at the load balancer
    - D) Because gRPC is UDP-based, so L4 balancing is impossible

<details>
<summary>Show Answer</summary>

**Answer: B) Because gRPC keeps one long-lived TCP connection and multiplexes requests over it, so per-connection balancing cannot spread requests evenly**

**Explanation:**
An L4 load balancer distributes per connection only. gRPC multiplexes many requests over a single long-lived connection, so requests are not balanced individually. The fixes are L7 load balancing, client-side load balancing, or a service mesh (such as Istio).

</details>

11. Which problem→response pairing for operating WebSocket services is WRONG?
    - A) Disconnects from load balancer idle timeouts → keep alive with ping/pong frames
    - B) Reconnection storms during deployments → exponential backoff with jitter
    - C) Sharing connection state across instances when scaling out → use Redis Pub/Sub or similar
    - D) Proxy blocking the Upgrade header → raise to QoS 2

<details>
<summary>Show Answer</summary>

**Answer: D) Proxy blocking the Upgrade header → raise to QoS 2**

**Explanation:**
QoS levels are an MQTT concept and have nothing to do with WebSocket. Whether proxies/firewalls pass the HTTP `Upgrade` handshake is something to verify and allow in proxy configuration. The other options are real operational issues — and correct responses — arising from WebSocket being a stateful, long-lived connection.

</details>

12. Which correctly pairs the three email-domain authentication mechanisms (SPF, DKIM, DMARC) with their roles?
    - A) SPF: message signing / DKIM: publishing allowed sender IPs / DMARC: enforcing encryption
    - B) SPF: publish allowed sender IPs in DNS / DKIM: sign messages with a domain key / DMARC: declare failure policy and reporting
    - C) SPF: receiving-server authentication / DKIM: transport encryption / DMARC: spam filtering
    - D) SPF: mail queue management / DKIM: MX record validation / DMARC: enforcing TLS

<details>
<summary>Show Answer</summary>

**Answer: B) SPF: publish allowed sender IPs in DNS / DKIM: sign messages with a domain key / DMARC: declare failure policy and reporting**

**Explanation:**
SMTP's original design has no authentication, so sender forgery is free. SPF publishes the domain's allowed sender IPs in DNS, DKIM detects forgery and tampering via domain-key signatures, and DMARC declares the handling policy and reporting for SPF/DKIM failures. Without all three, deliverability drops and you cannot stop domain impersonation.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals.md) | [Next Quiz: Cluster Architecture](../core/01-cluster-architecture-quiz.md)
