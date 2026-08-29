# Network Fundamentals Part 3 — Ten Application Protocols

> **Last Updated**: August 28, 2026

::: tip This is a four-part series
[Part 1: The Layer Model, Link and Routing Layers](./06-network-fundamentals-part1.md) ·
[Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md) ·
**Part 3: Application Protocols** *(this document)* ·
[Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
:::

The transport layer built a trustworthy pipe; now **actual services** flow through it. This part covers name resolution (DNS·DoH), bootstrapping (DHCP), operational access (SSH), mail (SMTP), and the protocols of the modern web: HTTP/3, WebSocket, WebRTC, gRPC, and MQTT.

---

## 5. Application Layer — Actual Services

### DNS

**Definition:** The distributed directory system that resolves domain names into IP addresses and other records.

**How it works:** DNS is hierarchical delegation. A resolver walks down from root → TLD → authoritative nameserver, caching each step's answer for its TTL. Record types map to purposes: A/AAAA for IPs, CNAME for aliases, MX for mail servers, TXT for verification strings.

**In practice:** DNS is close to being the internet's single point of failure — a large share of major outages start there. The part that matters most in operations is **TTL and caching**. If your failover plan relies on DNS, know that even with a short TTL, some clients and intermediate resolvers simply do not honor it, so cutover takes far longer than expected. If you need fast failover, handle it in front of DNS — at the anycast or load-balancer level.

**Common record types at a glance:**

| Type | Purpose | Field note |
|---|---|---|
| A / AAAA | Domain → IPv4 / IPv6 | The basics |
| CNAME | Alias → canonical name | Not allowed at the zone apex → ALIAS/ANAME or Route 53 Alias |
| MX | Mail-receiving server | Lower priority number wins |
| TXT | Arbitrary strings | SPF/DKIM/DMARC, domain-ownership verification |
| NS | Delegated nameservers | Sub-zone delegation |
| SRV | Service location (host+port) | Discovery for some protocols |
| CAA | Restrict which CAs may issue | Prevents mis-issuance |

**DNSSEC and DoH solve different problems.** DNSSEC verifies via signatures that a response was not forged (integrity); DoH encrypts the query (confidentiality). DNSSEC hides nothing, and DoH prevents no forgery — they are complements you can run together.

![Shows recursive DNS resolution: the stub resolver's query walks through the recursive resolver down the root, TLD, and authoritative nameservers, with the answer cached for its TTL.](../.gitbook/assets/en-basics-06-network-fundamentals-part3-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part3-0.html)

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

**The three generations side by side:**

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC (UDP) |
| Requests per connection | Sequential (pipelining unused in practice) | Multiplexed | Multiplexed |
| HOL blocking | At the application level | Still present at the TCP level | Structurally gone |
| Header compression | None | HPACK | QPACK |
| Encryption | Optional (HTTPS) | Effectively mandatory | Built into the protocol |

The direction is consistent: raise parallelism, push blocking down a layer — until finally the transport itself was replaced.

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

**Next:** [Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
