# Network Fundamentals Part 2 — The Transport Layer and TLS

> **Last Updated**: September 11, 2026

::: tip This is a four-part series
[Part 1: The Layer Model, Link and Routing Layers](./06-network-fundamentals-part1.md) ·
**Part 2: The Transport Layer and TLS** *(this document)* ·
[Part 3: Application Protocols](./06-network-fundamentals-part3.md) ·
[Part 4: A Request's Journey and the Cloud](./06-network-fundamentals-part4.md)
:::

Part 1 delivered packets to the destination host. This part compares reliable streams (TCP and QUIC) with UDP datagrams, then explains how TLS protects communication. UDP itself does not supply reliability or TLS; applications choose an appropriate security protocol, such as DTLS, or use a transport such as QUIC that integrates TLS 1.3.

One picture summarizes the heart of this part:

![Typical fresh connection: TCP plus a full TLS 1.3 handshake takes about 2 RTTs before a request, while QUIC combines these into about 1 RTT. Eligible resumption can send 0-RTT early data before handshake completion.](../.gitbook/assets/en-basics-06-network-fundamentals-part2-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part2-0.html)

---

## 3. Transport Layer — End-to-End Delivery

From here on, your conversation partner is not a "network" but a "process." That is why port numbers appear.

### TCP

**Definition:** A connection-oriented transport protocol providing a reliable, ordered byte stream.

**How it works:** A 3-way handshake (SYN → SYN+ACK → ACK) establishes the connection. Sequence numbers preserve order, ACKs and retransmission recover losses, sliding windows control flow, and congestion control adapts to network load. To the application, TCP presents a clean abstraction: a gapless stream of bytes.

**In practice:** Ordered delivery causes **head-of-line (HOL) blocking**: a missing TCP segment prevents delivery of bytes beyond the gap. With HTTP/2, this can delay multiple streams sharing that connection; data already delivered and independent application work can still progress. QUIC removes this particular cross-stream transport ordering dependency.

For a typical fresh connection without optimizations, TCP setup costs about 1 RTT, followed by a full TLS 1.3 handshake of 1 RTT (typically 2 RTTs for TLS 1.2). Connection reuse, resumption, early data and TCP Fast Open change the timing; retries can add delay. Assess connection pooling against the actual workload.

**A short lineage of congestion control:** Congestion control influences throughput along with bandwidth, latency, buffers and application behavior. Classic **Reno** reduces its congestion window on loss. **CUBIC**, a common Linux default, uses a cubic window-growth function to improve scalability on high-bandwidth paths. **BBR** models bottleneck bandwidth and propagation RTT to guide sending; its use of loss and ECN also depends on the implementation/version. No algorithm guarantees higher throughput on every long-haul or mobile path. `sysctl net.ipv4.tcp_congestion_control` only **reads** the configured default; changing the default affects new connections and requires separate configuration and measurement.

**TIME_WAIT and port exhaustion:** In a normal graceful close, the active closer generally enters TIME_WAIT; simultaneous close can put both peers there. High connection churn can contribute to exhaustion of available connection tuples, ephemeral ports or NAT mappings, depending on the implementation and destination pattern. A TIME_WAIT entry does not universally reserve that port against every remote endpoint. Diagnose the actual limit and consider connection reuse before changing kernel settings; TIME_WAIT also protects against delayed packets from an old connection.

### UDP

**Definition:** A minimal transport protocol that sends datagrams with no connection setup.

**How it works:** The 8-byte header carries only source port, destination port, length, and checksum. No handshake, no retransmission, no ordering, no congestion control. It is essentially "IP with port numbers."

**In practice:** Real-time applications can prefer timely delivery over retransmitting stale data, and DNS commonly uses UDP for small exchanges. Applications must implement any required reliability and appropriate congestion control themselves, or use a protocol such as QUIC that provides them.

The caveat: being stateless makes UDP easy to abuse for spoofing and amplification attacks. When exposing UDP services externally, plan for response-size limits and request-rate control.

### QUIC

**Definition:** A secure, multiplexed transport protocol implemented on top of UDP.

**How it works:** QUIC redesigns, from scratch on UDP, everything TCP+TLS used to do. Four key properties:

1. **Independent stream delivery** — each stream has its own byte ordering, so loss on one stream need not prevent delivery of another stream’s available data. Packet recovery and congestion control still operate across the connection/path; a stream can block on its own missing bytes, and application or HTTP/3 QPACK dependencies can also cause blocking.
2. **Built-in encryption** — QUIC integrates the TLS 1.3 handshake and uses its own packet protection rather than TLS records. A normal full handshake takes about 1 RTT. Eligible, accepted resumption can carry **0-RTT early data**, but the handshake still completes later; Retry or additional handshake exchanges can increase latency.
3. **Connection IDs** — these support connection continuity through address changes, with path validation and endpoint support. Migration restrictions or unavailable paths can still interrupt a Wi-Fi-to-cellular transition; continuity is not guaranteed.
4. **Implementation flexibility** — QUIC is commonly implemented in user space, allowing transport changes to ship with an application or library. User-space implementation is not a protocol requirement.

**In practice:** HTTP/3 usually uses UDP 443. If that path is blocked, an HTTP client can try HTTP/2 or HTTP/1.1 over TCP when the server supports them; QUIC itself does not turn into TCP. Check reachability, negotiated protocol and implementation/offload behavior before attributing a performance result to QUIC. CPU cost depends on the implementation and workload.

One security caveat: **0-RTT data can be replayed.** Replaying an early-data exchange can make an application process a request more than once; transport packet deduplication alone does not provide application replay protection. Permit only operations the application has explicitly assessed as replay-safe. A GET name or an idempotency claim alone is insufficient. Servers can reject early data; HTTP servers can use `425 Too Early` so the client retries after the handshake. Configure this policy across the client, CDN and origin.

---

## 4. Security — TLS

### TLS

**Definition:** The protocol providing confidentiality, integrity, and authentication for data in transit.

**How it works:** TLS negotiates cryptographic parameters and establishes keys during a handshake. Certificate-based handshakes authenticate the server using a certificate and proof of key possession; PSK-based handshakes can authenticate using a previously established or externally provisioned key instead. TLS records protect application data. TLS 1.3 uses authenticated encryption (AEAD) for confidentiality and integrity.

A normal full TLS 1.3 handshake takes about 1 RTT; resumption permits optional early data under additional conditions. TLS 1.3 removed static RSA key exchange and legacy cipher suites, but RSA certificate signatures are still supported. Ephemeral (EC)DHE key exchange provides forward secrecy, including when combined with a PSK. **PSK-only key exchange and 0-RTT data do not provide the same forward-secrecy guarantee.**

**In practice:** Three things go wrong over and over.

- **Certificate expiry** — automate renewal and separately monitor expiry and successful certificate deployment.
- **SNI exposure** — TLS 1.3 alone leaves the ClientHello SNI visible. ECH (Encrypted Client Hello, RFC 9849) can protect the inner ClientHello when supported and configured by both endpoints. QUIC Initial packet keys are publicly derivable, so Initial encryption alone does not hide SNI. ECH also does not hide the destination IP or all traffic metadata.
- **Termination point design** — document every hop: client to load balancer, load balancer to application, and any service-to-service connection. TLS termination does not automatically encrypt the next hop. Use TLS there when required; use mTLS when both peers must authenticate with certificates. A service mesh can automate this, but is not required for every design.

**Certificate chains and OCSP stapling:** Typical X.509 validation builds a path from the leaf certificate, through any required intermediates, to a configured trust anchor. The server should send the needed intermediate certificates; the root is normally already trusted by the client. Missing intermediates can cause client-dependent failures, although not every valid chain contains an intermediate. Revocation handling depends on the issuer and client. Where OCSP is supported, stapling lets the server attach a signed status response and can reduce direct client lookups. It is not universal: Let’s Encrypt ended OCSP service in August 2025 and uses CRLs. Match certificate and revocation configuration to the actual CA and clients.

> 📎 For how Istio automates this, see [Istio mTLS](../service-mesh/istio/security/01-mtls.md).


**Primary references**: [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html), [QUIC transport](https://www.rfc-editor.org/rfc/rfc9000.html), [QUIC/TLS](https://www.rfc-editor.org/rfc/rfc9001.html), [HTTP early data](https://www.rfc-editor.org/rfc/rfc8470.html), [ECH](https://www.rfc-editor.org/rfc/rfc9849.html), [Linux TCP settings](https://docs.kernel.org/networking/ip-sysctl.html), [Let’s Encrypt OCSP retirement](https://letsencrypt.org/2025/08/06/ocsp-service-has-reached-end-of-life/).
---

**Next:** [Part 3: Application Protocols](./06-network-fundamentals-part3.md)
