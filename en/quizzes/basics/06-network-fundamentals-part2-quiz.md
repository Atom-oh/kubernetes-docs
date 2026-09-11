# Network Fundamentals Part 2 Quiz — Transport and TLS

> **Last Updated**: September 11, 2026

Tests your understanding of TCP, UDP, QUIC, and TLS.

## Multiple Choice Questions

1. How does QUIC avoid TCP’s cross-stream head-of-line (HOL) delivery dependency?
   - A) Re-establish the entire connection on packet loss
   - B) Maintain independent byte ordering for each stream within one connection
   - C) Give up ordering guarantees entirely
   - D) Handle retransmission at the kernel level

<details>
<summary>Show Answer</summary>

**Answer: B) Maintain independent byte ordering for each stream within one connection**

**Explanation:**
TCP cannot deliver bytes beyond a missing segment, which can delay several HTTP/2 streams. QUIC can deliver available data from another stream independently. A stream can still wait for its own missing bytes; connection/path congestion control, packet recovery and application dependencies are shared concerns.

</details>

2. Which statement about TLS 1.3 is NOT correct?
   - A) A normal full handshake takes about 1 RTT; eligible resumption can carry optional 0-RTT early data
   - B) RSA key exchange and weak cipher suites were removed
   - C) TLS 1.3 alone encrypts SNI without ECH
   - D) Ephemeral (EC)DHE provides forward secrecy, but PSK-only exchange and 0-RTT data have exceptions

<details>
<summary>Show Answer</summary>

**Answer: C) TLS 1.3 alone encrypts SNI without ECH**

**Explanation:**
TLS 1.3 alone does not hide ClientHello SNI. ECH (RFC 9849) protects the inner ClientHello when supported and configured. TLS 1.3 permits PSK-only key exchange, and 0-RTT data lacks forward secrecy, so it is incorrect to describe forward secrecy as unconditional. Early data also does not mean that the handshake is already complete.

</details>

3. What characterizes BBR’s approach to congestion control?
   - A) Because it ignores packet loss and always sends at maximum speed
   - B) It models bottleneck bandwidth and propagation RTT to guide sending, with loss/ECN behavior depending on the version
   - C) Because it runs in user space instead of the kernel
   - D) Because it delegates retransmission to the link layer

<details>
<summary>Show Answer</summary>

**Answer: B) It models bottleneck bandwidth and propagation RTT to guide sending, with loss/ECN behavior depending on the version**

**Explanation:**
BBR uses a bandwidth/RTT model rather than relying only on a loss-driven congestion window. It still needs loss recovery and version-specific congestion responses. Performance depends on implementation, competing traffic and path conditions; higher throughput is not guaranteed.

</details>

4. What rule must you follow when sending requests over TLS 1.3/QUIC 0-RTT session resumption?
   - A) Send only POST requests
   - B) 0-RTT data can be replayed, so allow only operations explicitly assessed as replay-safe by the application
   - C) Certificate validation is skipped in 0-RTT, so use it only on internal networks
   - D) 0-RTT only works over UDP, so block TCP fallback

<details>
<summary>Show Answer</summary>

**Answer: B) 0-RTT data can be replayed, so allow only operations explicitly assessed as replay-safe by the application**

**Explanation:**
Early-data exchanges can be replayed and cause repeated application processing. A GET method name or a claim of idempotency alone is not proof of replay safety. Restrict early data to approved operations across the client/CDN/origin. An HTTP server can respond with 425 Too Early so the request is retried after the handshake.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part2.md) | [Next Quiz: Part 3](./06-network-fundamentals-part3-quiz.md)
