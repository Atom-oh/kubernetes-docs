# Network Fundamentals Part 3 Quiz — Application Protocols

> **Last Updated**: August 28, 2026

Tests your understanding of the 10 application-layer protocols, from DNS to MQTT.

## Multiple Choice Questions

1. When investigating "we enabled HTTP/3, why isn't it faster?", what should you check first?
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

2. What is the main reason DNS-based failover cuts over far more slowly than expected?
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

3. From an enterprise network perspective, why is DoH (DNS over HTTPS) a "headache"?
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

4. You put an L4 load balancer in front of a gRPC service and traffic piles onto specific backends. Why?
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

5. Which problem→response pairing for operating WebSocket services is WRONG?
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

6. Which correctly pairs the three email-domain authentication mechanisms (SPF, DKIM, DMARC) with their roles?
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

[Back to Study Material](../../basics/06-network-fundamentals-part3.md) | [Next Quiz: Part 4](./06-network-fundamentals-part4-quiz.md)
