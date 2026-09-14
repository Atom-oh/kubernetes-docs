# Network Fundamentals Part 3 — Ten Application Protocols

> **Last Updated**: September 14, 2026

::: tip This is a four-part series
[Part 1: The Layer Model, Link and Routing Layers](./06-network-fundamentals-part1.md) ·
[Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md) ·
**Part 3: Application Protocols** *(this document)* ·
[Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
:::

Transport protocols provide streams or datagrams; application protocols turn them into services. This part covers name resolution (DNS and DoH), bootstrapping (DHCP), operational access (SSH), mail (SMTP), and HTTP/3, WebSocket, WebRTC, gRPC and MQTT.

---

## 5. Application Layer — Actual Services

### DNS

**Definition:** The distributed directory system that resolves domain names into IP addresses and other records.

**How it works:** DNS uses hierarchical delegation. On a cache miss, a recursive resolver follows referrals from root to TLD to authoritative nameservers, or forwards to another resolver. Cached answers can avoid some or all of that work. A/AAAA records contain addresses, CNAME records aliases, MX records mail servers, and TXT records text used by several protocols.

**In practice:** DNS is distributed, but a resolver, provider or configuration can become a shared dependency. For DNS failover, account for failure detection, record updates, the TTL of answers already cached, application caching and existing connections. Reducing TTL now does not shorten the TTL of an old cached answer. Some resolvers also serve stale answers under defined failure conditions (RFC 8767). Measure each stage; short TTL alone is not a failover-time guarantee. Load balancers and anycast can complement DNS, with their own health detection and convergence limits.

**Common record types at a glance:**

| Type | Purpose | Field note |
|---|---|---|
| A / AAAA | Domain → IPv4 / IPv6 | The basics |
| CNAME | Alias → canonical name | Cannot coexist with apex SOA/NS; provider-specific ALIAS/ANAME or Route 53 Alias can offer apex mapping to supported targets |
| MX | Mail-receiving server | Lower priority number wins |
| TXT | Arbitrary strings | SPF/DKIM/DMARC, domain-ownership verification |
| NS | Delegated nameservers | Sub-zone delegation |
| SRV | Service location (host+port) | Discovery for some protocols |
| CAA | Restrict authorized certificate issuers | Requires CA enforcement; does not itself prevent every mis-issuance |

**DNSSEC and DoH solve different problems.** DNSSEC authenticates signed DNS data and its integrity through a validated trust chain; it does not encrypt queries. DoH uses HTTPS to authenticate the chosen resolver and protect confidentiality and integrity on the client–resolver hop. It does not prove that a malicious or mistaken resolver returned authoritative data. They can be used together.

![Shows recursive DNS resolution: the stub resolver's query walks through the recursive resolver down the root, TLD, and authoritative nameservers, with the answer cached for its TTL.](../.gitbook/assets/en-basics-06-network-fundamentals-part3-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part3-0.html)

### DoH

**Definition:** DNS queries wrapped in and transported over HTTPS.

**How it works:** Traditional DNS commonly uses plaintext UDP **and TCP** port 53. DoH carries DNS messages over HTTPS, protecting them from passive inspection and modification on that hop. Resolver endpoints and traffic metadata may still identify DoH use; the chosen resolver can see the queries.

**In practice:** An independently selected public DoH resolver can bypass filtering/logging at the organization’s resolver and fail to resolve private names. DoH does not inherently disable policy: a managed DoH resolver can apply logging/filtering, and browser/OS policies can select approved resolvers. Test split DNS and endpoint policy instead of assuming that disabling encryption is always necessary.

### DHCP

**Definition:** The protocol that automatically assigns hosts an IP address and network configuration.

**How it works:** A common initial **DHCPv4** exchange is DORA: Discover → Offer → Request → Acknowledge. A local broadcast or a DHCP relay locates a server. The lease can include IPv4 address, subnet mask, gateway and DNS configuration. Renewal can use a shorter exchange. DHCPv6 uses different messages; IPv6 default-router information normally comes from Router Advertisements, and SLAAC is another address-configuration mechanism.

**In practice:** In the cloud it is mostly abstracted away, but you meet it again in the VPC DHCP option set, which is where DNS servers and domain names are configured. When name resolution breaks in a hybrid setup that uses on-premises DNS, this is the setting to check.

### SSH

**Definition:** The protocol providing encrypted remote shell access and tunneling.

**How it works:** The server authenticates itself with its host key, a key exchange derives session keys, and then the user authenticates (public key or password). All subsequent traffic is encrypted. Beyond remote shells, SSH supports port forwarding, SFTP, and agent forwarding.

**In practice:** Restrict forwarding according to the access policy and validate server host keys. A compromised host with access to a forwarded agent socket can request signatures/authentication from the agent; forwarding does not ordinarily copy the private key material there. Prefer a jump host (`ProxyJump`) when agent forwarding is unnecessary. Raw keys have no intrinsic expiry, but OpenSSH supports certificate validity periods and `authorized_keys` expiry restrictions. Remove departed users’ access and rotate or revoke credentials.

AWS Systems Manager Session Manager can provide shell access without inbound SSH ports or distributing SSH keys, provided the managed node, IAM permissions and service connectivity are configured. CloudTrail records API activity; shell-content logging to CloudWatch Logs/S3 requires configuration. **Session content logging is unavailable for Session Manager SSH and port-forwarding sessions.** IAM-based access by itself does not imply that every command is recorded.

### SMTP

**Definition:** The protocol that relays messages between mail servers.

**How it works:** Clients submit mail to a submission server, and SMTP servers relay and receive messages, commonly using MX lookup for routing. IMAP and POP3 let users retrieve or access messages already stored in a mailbox; they do not replace SMTP’s server-side receipt.

**In practice:** SMTP authentication and TLS secure submission/transport, but do not by themselves prove the visible sender domain. Three complementary domain mechanisms matter:

- **SPF** — authorize sending hosts for the envelope MAIL FROM or HELO identity; this is not automatically the visible From header.
- **DKIM** — verify a signature over covered message content using the signing domain’s DNS key; the signing domain can differ from the visible From domain.
- **DMARC** — require the visible From domain to align with a passing SPF **or** DKIM identity, and publish requested handling/reporting policy.

Configure SPF, DKIM and DMARC together where appropriate, monitor reports, and account for forwarding/mailing-list behavior. DMARC can pass with one aligned mechanism. These controls neither guarantee delivery nor eliminate display-name or lookalike-domain impersonation; receivers also apply local policy.

### HTTP/3

**Definition:** The third major version of HTTP, running on QUIC.

**How it works:** HTTP semantics are shared across versions, but HTTP/3 uses QUIC streams and its own framing and mapping. It removes TCP’s cross-stream ordering dependency; within-stream loss, QPACK dependencies and shared congestion control can still delay work. A typical full handshake takes about 1 RTT, and supported migration can preserve a connection through an address change. QPACK replaces HPACK to accommodate independently delivered streams.

**In practice:** Clients can discover HTTP/3 through `Alt-Svc`, prior knowledge or HTTPS DNS records advertising a supported protocol. `Alt-Svc` may be learned through an earlier TCP connection; a client that supports the HTTPS record can discover HTTP/3 before that exchange. Neither method guarantees reachability or a particular latency saving.

Independent delivery and integrated handshakes can help on lossy or high-latency paths. Actual latency, throughput and CPU cost depend on implementation, offloads, workload and network conditions. Measure representative mobile and data-center traffic rather than assuming a universal win or loss.

**The three generations side by side:**

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC (UDP) |
| Requests per connection | Sequential, or pipelined with ordered responses | Multiplexed | Multiplexed |
| HOL blocking | Ordered responses and TCP delivery | TCP ordering across streams | No TCP cross-stream ordering; other blocking remains |
| Header compression | None | HPACK | QPACK |
| Encryption | Optional (HTTPS) | TLS for HTTPS; cleartext HTTP/2 also exists | TLS 1.3 integrated into QUIC |

Multiplexing changes where ordering dependencies arise; HTTP/3 reduces one source of blocking without eliminating all scheduling, flow-control or application dependencies.

#### Reading HTTP/1.1 requests and responses {#http11-message-structure}

HTTP versions share methods, status codes and field semantics. HTTP/1.1 makes those concepts visible as a **start line → header field lines → blank line → optional body**. A body can contain text or binary data; “textual HTTP/1.1” describes its start line and headers, not every payload.

These are **illustrative HTTP/1.1 messages, not captured output or a command recipe**. For readability, the display uses LF line breaks. On the wire, the start line and each header line end in **CRLF (`\r\n`)**, and an additional CRLF ends the header section. Each body below is exactly **5 ASCII bytes**, `hello`, with **no trailing newline**; the display newline before the closing fence is not part of the body.

Client → server:

```http
POST /echo HTTP/1.1
Host: example.test
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

Server → client:

```http
HTTP/1.1 200 OK
Date: Mon, 14 Sep 2026 00:00:00 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

| Element | How to read it |
|---|---|
| Request line | `POST` is the method, `/echo` the request target (here a path), and `HTTP/1.1` the version. The required `Host` field supplies the target hostname and optional port (authority). |
| Status line | `HTTP/1.1` is the version, `200` the status code and `OK` an optional reason phrase. Use the code to interpret the result. |
| Header fields | `Name: value` lines carry metadata; field names are case-insensitive. `Content-Type` describes the representation's media type and, here, its charset. |
| Blank line | Ends the header section. It does not specify where a following body ends. |
| Body | The content bytes. Here, `Content-Length: 5` delimits five bytes, excluding the start line, headers and separator. Count bytes, not Unicode characters. |

**Meaning and framing answer different questions.** A method expresses the requested action: GET retrieves a representation, HEAD requests corresponding response metadata without response content, and POST asks the target to process supplied content. Status classes summarize the result: 1xx informational, 2xx success, 3xx redirection, 4xx client error and 5xx server error. `Content-Type` explains how to interpret content; it does not delimit it. See [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) for these shared semantics.

HTTP/1.1 framing determines how many bytes belong to this message on a reusable TCP stream. For an ordinary body-bearing message, a valid `Content-Length` without `Transfer-Encoding` gives its length. With `Transfer-Encoding: chunked`, chunk sizes and the terminating zero-size chunk, followed by any trailers and the final blank line, delimit the body instead. A sender must not send both fields. Some responses use connection close as their delimiter; TCP packet boundaries never delimit HTTP messages.

Method/status rules come first: responses to HEAD and responses with 1xx, 204 or 304 status have no message body, even if permitted metadata describes a representation. A successful CONNECT response starts a tunnel. A request with neither length nor transfer coding has no body. These distinctions prevent reading the next message as content ([RFC 9112 §§2–6](https://www.rfc-editor.org/rfc/rfc9112.html)).

**HTTP/2 and HTTP/3 preserve the meaning, but use binary framing**, including HEADERS and DATA frames, rather than these textual start lines and CRLF boundaries. HTTP/2 uses TCP; HTTP/3 maps messages onto QUIC streams. Neither uses HTTP/1.1 chunked transfer coding. A tool can present decoded fields as readable text without showing their actual wire encoding ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)).

With HTTPS, TLS protects HTTP headers and bodies in transit; a passive capture without session secrets does not expose this plaintext ([RFC 8446 §5](https://www.rfc-editor.org/rfc/rfc8446.html#section-5)). QUIC likewise protects HTTP/3 application data. Inspect decoded messages at an authorized endpoint or TLS termination point, and identify which connection leg is being observed.

> 📎 Continue with the [Linux HTTP message lab](../networking/07-linux-network-diagnostics.md#http-message-lab) before applying the same distinctions to container services, Kubernetes Ingress or AWS load balancers.

### WebSocket

**Definition:** An application protocol for bidirectional messaging over a single connection.

**How it works:** The HTTP/1.1 handshake uses `Upgrade` and a successful `101` response. HTTP/2 and HTTP/3 use Extended CONNECT instead (RFCs 8441 and 9220), when supported. Once established, either peer can send WebSocket messages without repeated HTTP polling.

**In practice:** Plan for long-lived connections: heartbeat traffic within the relevant idle timeout, graceful draining during deployment, and reconnect backoff with jitter. Each socket remains on its owning instance. Shared application state or messaging, such as Redis Pub/Sub, can deliver events across instances but does not transfer live sockets or provide durable delivery by itself. Verify the handshake used by the negotiated HTTP version and the proxy’s support.

### WebRTC

**Definition:** APIs and protocols for real-time media and data between compatible endpoints, including browsers and media servers.

**How it works:** NAT can obstruct direct reachability, but two peers behind NAT may still connect. ICE exchanges and tests host, server-reflexive (learned with STUN) and relayed (TURN) candidates. Application signaling carries session descriptions and candidates. The selected path depends on connectivity checks and policy. Media uses SRTP, commonly with DTLS-SRTP key establishment; data channels use SCTP over DTLS.

**In practice:** TURN relay usage contributes bandwidth and infrastructure cost; signaling, STUN and other service costs remain even with a direct media path. NAT mapping/filtering and firewall behavior influence connectivity, so the label “symmetric NAT” alone is not a universal proof that relay is unavoidable. Budget for TURN fallback and test actual networks. An SFU is a common multiparty design that trades server bandwidth/compute for reduced client upload compared with a full peer mesh.

### gRPC

**Definition:** An RPC framework whose standard native transport uses HTTP/2, commonly with Protocol Buffers service and message schemas.

**How it works:** Protocol Buffers definitions can generate client/server code and support unary, server-streaming, client-streaming and bidirectional-streaming RPCs. Binary encoding can be compact, but size and speed relative to JSON depend on data, implementation and compression; they are not protocol guarantees.

**In practice:** Native gRPC works well for many service APIs. Browser APIs do not expose everything native gRPC requires, so browser clients commonly use gRPC-Web with a compatible server or translating proxy; available streaming modes depend on that implementation. Use schema-aware tools for inspection and debugging.

A gRPC channel can use **zero or more HTTP/2 connections**, and many RPCs can share a long-lived connection. L4 balancing selects a backend per connection, so a small connection pool can concentrate RPC traffic; it does not guarantee per-RPC distribution. Consider a suitable client-side policy or a gRPC-aware L7 proxy (which may be part of a service mesh). Established streams still remain with their selected backend. For schema evolution, reserve deleted Protocol Buffers field numbers/names and never reuse their numbers.

> 📎 For gRPC handling in Istio, see [Istio gRPC Advanced](../service-mesh/istio/advanced/05-grpc.md).

### MQTT

**Definition:** A lightweight publish-subscribe messaging protocol.

**How it works:** Clients connect to a broker and publish/subscribe to topics. A fixed header can be as small as 2 bytes, but real packets can also need variable headers, properties and payloads. QoS 0/1/2 provide at-most-once, at-least-once and exactly-once **protocol delivery on the relevant sender–receiver leg**. Publisher-to-broker and broker-to-subscriber delivery are separate. A configured Will can be published on specified disconnection conditions; MQTT 5 Will Delay and reconnect behavior affect when it appears.

**In practice:** Choose QoS according to loss/duplicate tolerance and cost. Successful QoS 2 delivery normally exchanges PUBLISH, PUBREC, PUBREL and PUBCOMP; it does not make an application’s database side effects or an entire business workflow exactly once. QoS 1 plus application deduplication is one possible trade-off. Plan broker availability, durable session/message state and recovery for the chosen product. Use TLS and an appropriate device authentication/authorization scheme; client certificates are one option, with provisioning and rotation requirements.


**Primary references**: [DoH](https://www.rfc-editor.org/rfc/rfc8484.html), [DNS serve-stale](https://www.rfc-editor.org/rfc/rfc8767.html), [OpenSSH](https://man.openbsd.org/ssh), [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html), [DMARC](https://www.rfc-editor.org/rfc/rfc7489.html), [HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html), [ICE](https://www.rfc-editor.org/rfc/rfc8445.html), [gRPC performance](https://grpc.io/docs/guides/performance/), [MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
---

**Next:** [Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
