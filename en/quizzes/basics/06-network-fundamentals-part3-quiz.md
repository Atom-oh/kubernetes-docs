# Network Fundamentals Part 3 Quiz — Application Protocols

> **Last Updated**: September 14, 2026

Tests your understanding of the 10 application-layer protocols, from DNS to MQTT.

## Multiple Choice Questions

1. When HTTP/3 is enabled but shows no speedup, which transport-level check is useful?
   - A) The server certificate's expiry date
   - B) Whether UDP 443 is reachable and HTTP/3 was actually negotiated
   - C) The DNS TTL settings
   - D) The HTTP/2 header compression (HPACK) settings

<details>
<summary>Show Answer</summary>

**Answer: B) Whether UDP 443 is reachable and HTTP/3 was actually negotiated**

**Explanation:**
HTTP/3 commonly uses QUIC over UDP 443. If that path is blocked, a client may use TCP-based HTTP/2 or HTTP/1.1 when available. Verify the negotiated protocol before comparing performance. Loss, RTT, workload, implementation and CPU/offload behavior all influence the result; this question does not establish the cause of a real incident.

</details>

2. Which factor can delay DNS failover after an authoritative record changes?
   - A) DNS uses only TCP, so handshake costs are high
   - B) Previously cached answers, application caching and existing connections can outlive the record change
   - C) The root nameservers must approve the update
   - D) A records cannot be changed

<details>
<summary>Show Answer</summary>

**Answer: B) Previously cached answers, application caching and existing connections can outlive the record change**

**Explanation:**
A newly reduced TTL does not shorten the lifetime of an answer already cached with an older TTL. Failure detection, record updates, application caching and connection reuse also affect recovery. Resolvers may serve stale data under defined failure conditions (RFC 8767). DNS, load balancer and anycast designs each require measured failure/convergence behavior.

</details>

3. What policy issue can arise when a browser chooses an unapproved public DoH resolver?
   - A) Because DNS responses grow larger and waste bandwidth
   - B) It can bypass the organization’s resolver policies and fail to resolve private names
   - C) Because UDP port 53 gets overloaded
   - D) Because it is incompatible with DNSSEC

<details>
<summary>Show Answer</summary>

**Answer: B) It can bypass the organization’s resolver policies and fail to resolve private names**

**Explanation:**
DoH protects the client–resolver hop with HTTPS, including integrity. A separate public resolver can bypass controls at the organizational resolver, but managed DoH can itself provide policy and logging. Select approved resolvers with endpoint policy and test split DNS. Encryption does not make the resolver endpoint or all traffic metadata invisible.

</details>

4. Why can an L4 load balancer concentrate gRPC traffic on a few backends?
    - A) Because Protocol Buffers serialization is asymmetric
    - B) Many RPCs can share long-lived connections, while L4 balancing selects backends per connection
    - C) Because HTTP/2 header compression breaks at the load balancer
    - D) Because gRPC is UDP-based, so L4 balancing is impossible

<details>
<summary>Show Answer</summary>

**Answer: B) Many RPCs can share long-lived connections, while L4 balancing selects backends per connection**

**Explanation:**
A gRPC channel can use zero or more HTTP/2 connections. A small number of long-lived connections can carry many RPCs, and an L4 balancer does not redistribute each RPC. A suitable client-side policy or gRPC-aware L7 proxy can improve request distribution; an established stream remains on its backend.

</details>

5. Which problem→response pairing for operating WebSocket services is WRONG?
    - A) Disconnects from load balancer idle timeouts → keep alive with ping/pong frames
    - B) Reconnection storms during deployments → exponential backoff with jitter
    - C) Delivering application events across instances → use messaging such as Redis Pub/Sub, with each socket still owned locally
    - D) Proxy blocking the Upgrade header → raise to QoS 2

<details>
<summary>Show Answer</summary>

**Answer: D) Proxy blocking the Upgrade header → raise to QoS 2**

**Explanation:**
QoS levels belong to MQTT and do not repair WebSocket handshakes. HTTP/1.1 uses Upgrade, while HTTP/2 and HTTP/3 use Extended CONNECT when supported. Heartbeats must match idle-timeout behavior; backoff and draining reduce reconnection spikes. Pub/Sub can distribute application events, but does not migrate sockets or by itself provide durable message delivery.

</details>

6. Which correctly pairs the three email-domain authentication mechanisms (SPF, DKIM, DMARC) with their roles?
    - A) SPF: message signing / DKIM: publishing allowed sender IPs / DMARC: enforcing encryption
    - B) SPF: authorize hosts for envelope/HELO identities / DKIM: sign covered content with a domain key / DMARC: align the visible From domain with passing SPF or DKIM and publish policy
    - C) SPF: receiving-server authentication / DKIM: transport encryption / DMARC: spam filtering
    - D) SPF: mail queue management / DKIM: MX record validation / DMARC: enforcing TLS

<details>
<summary>Show Answer</summary>

**Answer: B) SPF: authorize hosts for envelope/HELO identities / DKIM: sign covered content with a domain key / DMARC: align the visible From domain with passing SPF or DKIM and publish policy**

**Explanation:**
SPF checks the envelope/HELO domain and DKIM verifies covered content for its signing domain. DMARC requires at least one passing mechanism aligned with the visible From domain; it does not require both to pass. These mechanisms help domain protection but do not guarantee delivery or prevent display-name/lookalike-domain impersonation.

</details>

7. An HTTP/1.1 request begins `POST /echo HTTP/1.1`, and its response begins `HTTP/1.1 200 OK`. Which interpretation is correct?
   - A) `POST` is a header field and `/echo` is the response status
   - B) `200` is the body length and `OK` determines whether the request succeeded
   - C) The request line contains method, target and version; the status line contains version, status code and an optional reason phrase
   - D) The first blank line terminates the entire message, including any body

<details>
<summary>Show Answer</summary>

**Answer: C) The request line contains method, target and version; the status line contains version, status code and an optional reason phrase**

**Explanation:**
POST asks the target to process supplied content; 200 is a success status. Header field lines follow the start line, then a blank line ends the header section. A body follows only when message rules permit it. HTTP/1.1 uses CRLF for these wire line endings even when an illustrative display uses LF.

</details>

8. The only content of an HTTP/1.1 message body is the five ASCII bytes `hello`, with no trailing newline, no content coding and no transfer coding. What does `Content-Length: 5` count?
   - A) The entire message, including start line and headers
   - B) Only the five body bytes; `Content-Type` separately describes their media type
   - C) Five Unicode characters, regardless of their byte encoding
   - D) The number of TCP packets that carry the body

<details>
<summary>Show Answer</summary>

**Answer: B) Only the five body bytes; `Content-Type` separately describes their media type**

**Explanation:**
Content-Length counts bytes, excluding the start line, headers and blank-line separator. ASCII `hello` is five bytes; a real added LF would make it six. Non-ASCII UTF-8 characters can occupy multiple bytes. Content-Type tells the recipient how to interpret the representation, not where the message ends.

</details>

9. A valid HTTP/1.1 `200` response to GET uses `Transfer-Encoding: chunked` and keeps the TCP connection open. How is the body delimited?
   - A) By the boundaries of the TCP packets
   - B) By Content-Type alone
   - C) By a required Content-Length sent alongside Transfer-Encoding
   - D) By chunk framing, ending with the zero-size chunk, any trailers and the final blank line

<details>
<summary>Show Answer</summary>

**Answer: D) By chunk framing, ending with the zero-size chunk, any trailers and the final blank line**

**Explanation:**
Chunk framing identifies the end without closing the connection. A sender must not send Content-Length with Transfer-Encoding. TCP is a byte stream: a message can span packets, and a packet can carry bytes from more than one message.

</details>

10. A valid HTTP/1.1 response to HEAD includes `Content-Length: 500`. Should the client read 500 body bytes after the header section?
   - A) No; a HEAD response has no message body, and the field describes the length a corresponding GET response would have
   - B) Yes; Content-Length always overrides the method
   - C) Yes, but only if Content-Type is text/plain
   - D) No; Content-Length is forbidden in every HEAD response

<details>
<summary>Show Answer</summary>

**Answer: A) No; a HEAD response has no message body, and the field describes the length a corresponding GET response would have**

**Explanation:**
The method/status rules precede generic length framing. HEAD responses carry no body; the permitted length field is metadata. Responses with 1xx, 204 or 304 status also have no body, with separate restrictions on which fields are permitted.

</details>

11. A client tool displays readable headers for an HTTPS request negotiated as HTTP/2. What should you expect in a passive capture without session secrets?
   - A) The same plaintext `GET ... HTTP/1.1` request line
   - B) Visible plaintext headers, with only the body encrypted
   - C) Protected application data; HTTP/2 uses binary frames, and the tool is displaying decoded fields
   - D) HTTP/1.1 chunk sizes separating every HTTP/2 stream

<details>
<summary>Show Answer</summary>

**Answer: C) Protected application data; HTTP/2 uses binary frames, and the tool is displaying decoded fields**

**Explanation:**
TLS protects HTTP/2 headers and content on an HTTPS connection. HTTP/2 uses HEADERS/DATA frames on TCP; HTTP/3 uses its own frames on protected QUIC streams. Both preserve HTTP semantics, but neither uses HTTP/1.1 textual start lines or chunked transfer coding. Observe decoded messages at an authorized endpoint or termination point.

</details>

---

[Back to Study Material](../../basics/06-network-fundamentals-part3.md) | [Next Quiz: Part 4](./06-network-fundamentals-part4-quiz.md)

Review [HTTP message structure, framing and visibility](../../basics/06-network-fundamentals-part3.md#http11-message-structure), including its primary references.
