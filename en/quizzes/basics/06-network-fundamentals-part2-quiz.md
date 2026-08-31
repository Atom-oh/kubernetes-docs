# Network Fundamentals Part 2 Quiz — Transport and TLS

> **Last Updated**: August 28, 2026

Tests your understanding of TCP, UDP, QUIC, and TLS.

## Multiple Choice Questions

1. What approach did QUIC adopt to structurally eliminate TCP's head-of-line (HOL) blocking?
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

2. Which statement about TLS 1.3 is NOT correct?
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

3. Why does BBR achieve higher throughput than loss-based algorithms like CUBIC on long-haul or mobile paths with a little persistent loss?
   - A) Because it ignores packet loss and always sends at maximum speed
   - B) Because instead of treating loss as the congestion signal, it models bandwidth and RTT directly to set the sending rate
   - C) Because it runs in user space instead of the kernel
   - D) Because it delegates retransmission to the link layer

<details>
<summary>Show Answer</summary>

**Answer: B) Because instead of treating loss as the congestion signal, it models bandwidth and RTT directly to set the sending rate**

**Explanation:**
Loss-based algorithms (Reno, CUBIC) interpret loss as congestion and slow down. On paths where a little loss unrelated to congestion is always present (e.g. wireless segments), that interpretation causes excessive slowdown. BBR measures bottleneck bandwidth and RTT to set its rate, which wins on such paths.

</details>

4. What rule must you follow when sending requests over TLS 1.3/QUIC 0-RTT session resumption?
   - A) Send only POST requests
   - B) 0-RTT data can be replayed, so send only idempotent requests
   - C) Certificate validation is skipped in 0-RTT, so use it only on internal networks
   - D) 0-RTT only works over UDP, so block TCP fallback

<details>
<summary>Show Answer</summary>

**Answer: B) 0-RTT data can be replayed, so send only idempotent requests**

**Explanation:**
An on-path attacker can copy 0-RTT resumption data and send it again, making the server process the same request twice (a replay attack). So only idempotent requests such as GET belong in 0-RTT, and servers/CDNs should explicitly restrict what 0-RTT may carry.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part2.md) | [Next Quiz: Part 3](./06-network-fundamentals-part3-quiz.md)
