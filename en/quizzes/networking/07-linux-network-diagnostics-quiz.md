# Linux Network Diagnostics Quiz

> **Last Updated**: September 14, 2026

Use these 12 questions to interpret the local HTTP, socket, routing and MTU exercises. Values in the questions are illustrative; they are not recorded measurements.

## Multiple Choice Questions {#questions}

1. Your shell selects a remote Docker context, but you want to run the routing helper. Which preparation matches its contract?
   - A) The helper automatically uses the selected remote daemon
   - B) Prepare the pinned image in the local Linux Engine at `/var/run/docker.sock` and pass the subnet-collision preflight
   - C) Enable privileged containers and publish the router's ports
   - D) Start several copies simultaneously because their subnet ranges are random

<details>
<summary>Show Answer</summary>

**Answer: B) Prepare the pinned image in the local Linux Engine at `/var/run/docker.sock` and pass the subnet-collision preflight**

**Explanation:**
The helper fixes the local Unix socket and ignores remote host/context environment selections. It uses fixed documentation subnets, so runs must not overlap. The image must already be present. The dedicated bridges disable masquerading; only the three owned containers lose their IPv4 default routes. Docker still creates host bridges and manages network rules.

</details>

2. GET `/lesson` returns the body `b"hello\n"`. Which Content-Length is correct?
   - A) 5, because only visible letters count
   - B) 7, because every newline in a body must be CRLF
   - C) 6, because the five ASCII letters and the final LF are six bytes
   - D) The length of the response headers plus the body

<details>
<summary>Show Answer</summary>

**Answer: C) 6, because the five ASCII letters and the final LF are six bytes**

**Explanation:**
The body is `68 65 6c 6c 6f 0a` in hexadecimal. HTTP/1.1 header-line CRLF rules do not convert a body LF into CRLF. Content-Length counts content bytes, excluding the start line, headers and separator. The echo helper likewise preserves bytes supplied with `--data-binary`.

</details>

3. `curl --http1.1 -I` receives `Content-Length: 6` from `/lesson` but displays no body. What happened?
   - A) curl sent HEAD; the response has no body, and the length describes the corresponding GET representation
   - B) curl sent GET and discarded six body bytes after receiving them
   - C) The server violated framing by failing to send six required bytes
   - D) HEAD always requires Content-Length to be zero

<details>
<summary>Show Answer</summary>

**Answer: A) curl sent HEAD; the response has no body, and the length describes the corresponding GET representation**

**Explanation:**
`-I` selects HEAD. A HEAD response has no message body even when it includes a permitted representation length. This differs from `-i`, which includes headers in normal output. Treating HEAD metadata as body framing can make a client misread the next response on a persistent connection.

</details>

4. A curl trace shows readable HTTP headers for an HTTPS request. What does that prove?
   - A) The headers crossed the network without encryption
   - B) Each trace line corresponds to one TCP packet
   - C) HTTP/2 and HTTP/3 use HTTP/1.1 text lines on the wire
   - D) The client can display HTTP data it handles; this is not a passive packet capture

<details>
<summary>Show Answer</summary>

**Answer: D) The client can display HTTP data it handles; this is not a passive packet capture**

**Explanation:**
Curl debug output is generated at the client and can expose data protected on the network by TLS. Its annotations are not wire encoding or segment boundaries. HTTP/2 and HTTP/3 also use binary framing. A capture's visibility depends on its observation point and available session secrets.

</details>

5. An illustrative `ss` snapshot shows LISTEN `Recv-Q=3`, `Send-Q=128`, and ESTABLISHED `Recv-Q=6`. Which interpretation is correct?
   - A) The listener holds three payload bytes in a 128-byte send buffer
   - B) The listener has three incomplete SYNs, and the established socket has six queued connections
   - C) The listener has three connections waiting for accept with a maximum backlog of 128; the established socket has six unread in-order bytes
   - D) All three numbers are congestion-window sizes

<details>
<summary>Show Answer</summary>

**Answer: C) The listener has three connections waiting for accept with a maximum backlog of 128; the established socket has six unread in-order bytes**

**Explanation:**
Queue-column units depend on socket state. LISTEN columns describe the accept queue, not the incomplete SYN queue. ESTABLISHED columns describe stream bytes; its Send-Q includes bytes not yet acknowledged. Filter on the test port and distinguish the client and server endpoints.

</details>

6. The persistent client is succeeding, both stream queues often show zero, and `skmem` still shows nonzero memory values. What should you conclude?
   - A) The connection is broken because empty queues require zero socket memory
   - B) Memory accounting and budgets differ from stream occupancy; the small workload can drain between observations
   - C) Increase every TCP buffer sysctl until the stream queues remain nonzero
   - D) `rb` is the exact receive window advertised to the peer

<details>
<summary>Show Answer</summary>

**Answer: B) Memory accounting and budgets differ from stream occupancy; the small workload can drain between observations**

**Explanation:**
The client consumes each six-byte response before its next request. This is an observation exercise, not forced buffer saturation. `skmem` includes kernel accounting and budgets, while receive and congestion windows are separate quantities. Read-only policy values and repeated observations do not justify a universal tuning setting.

</details>

7. The client is `192.0.2.2/29`, and its route to `198.51.100.3` uses gateway `192.0.2.3`. Which ARP result is expected?
   - A) A MAC for `192.0.2.3`, with no client neighbor entry needed for `198.51.100.3`
   - B) A direct MAC mapping for the remote server on the client's left network
   - C) ARP changes the IP destination to `192.0.2.3`
   - D) DNS supplies the Ethernet destination, so ARP is unnecessary

<details>
<summary>Show Answer</summary>

**Answer: A) A MAC for `192.0.2.3`, with no client neighbor entry needed for `198.51.100.3`**

**Explanation:**
Route lookup selects the on-link next hop before neighbor resolution. The Ethernet frame targets the router's MAC, while the IP destination remains the server. At the right network, the router performs its own lookup and neighbor resolution. The server also needs its explicit return route.

</details>

8. A TTL-1 ping exits unsuccessfully, while the router capture contains ICMP Type 11 Code 0 quoting that probe. How should the lab interpret this?
   - A) The destination completed an HTTP request
   - B) The router reported a TCP MSS mismatch
   - C) All later application packets must fail at the same router
   - D) The deliberately short TTL expired at the router, producing the intended diagnostic response

<details>
<summary>Show Answer</summary>

**Answer: D) The deliberately short TTL expired at the router, producing the intended diagnostic response**

**Explanation:**
The outgoing Echo Request and returning Time Exceeded are different messages. Matching the captured error to the probe establishes the intended event. A timeout alone would not: filtering, response rate limiting or return-path loss can also prevent a reply. The helper uses an actual router-namespace capture for this check.

</details>

9. Router egress MTU is 1280. An IPv4 DF ping uses 1372 data bytes; another uses 1200. With base IPv4 and ICMP headers, which result is expected?
   - A) Both fit because only ICMP data counts toward MTU
   - B) The first is 1372 bytes and the second is 1200 bytes on the IP layer
   - C) The 1400-byte IP packet triggers Fragmentation Needed; the 1228-byte packet fits
   - D) The larger probe negotiates TCP MSS down to 1200

<details>
<summary>Show Answer</summary>

**Answer: C) The 1400-byte IP packet triggers Fragmentation Needed; the 1228-byte packet fits**

**Explanation:**
Add 20 IPv4-header and 8 ICMP-header bytes. DF prevents router fragmentation, so the first failure should be accompanied by ICMP Type 3 Code 4; the smaller probe succeeds. After PMTU feedback is cached, a later oversized send may fail locally instead of generating another router capture.

</details>

10. `ss -i` on the loopback HTTP connection reports an MSS larger than 1460. Which conclusion is justified?
   - A) The helper must have enabled jumbo Ethernet frames on a physical interface
   - B) The 1460 calculation assumes Ethernet MTU 1500 and base IPv4/TCP headers; loopback has different conditions
   - C) The ICMP probe data size is the actual TCP MSS
   - D) Every captured unit larger than 1500 proves a physical wire MTU violation

<details>
<summary>Show Answer</summary>

**Answer: B) The 1460 calculation assumes Ethernet MTU 1500 and base IPv4/TCP headers; loopback has different conditions**

**Explanation:**
MSS describes TCP data, not ICMP data or an entire frame. Interface MTU, options and path behavior matter. TSO/GSO/GRO can also make host-side observations differ from physical-link packets. The loopback exercise does not establish a physical Ethernet MTU.

</details>

11. Docker DNS resolves the router name correctly, but the normal client-to-server ping fails. What has been established?
   - A) Name lookup works; route selection, forwarding and the return path still need examination
   - B) The server application is healthy
   - C) The two dedicated bridges provide working Internet NAT
   - D) The host's loopback HTTP server must be reachable through `127.0.0.1` in every container

<details>
<summary>Show Answer</summary>

**Answer: A) Name lookup works; route selection, forwarding and the return path still need examination**

**Explanation:**
DNS and forwarding test different mechanisms. This fixture uses explicit routing between dedicated bridges with masquerading disabled and does not benchmark Internet NAT. Each network namespace has its own loopback; the host's loopback server is not a container-local service. Correlate observations in the namespace where each lookup occurs.

</details>

12. The routing JSON has some successful observations, but its status is failed or cleanup is incomplete. What is the correct outcome?
   - A) Count the whole run as passed because route lookup worked
   - B) Ignore cleanup if the image is still cached locally
   - C) Run a broad Docker prune to guarantee a clean host
   - D) Keep the run failed, inspect the failing stage, and identify only the created IDs for any needed cleanup

<details>
<summary>Show Answer</summary>

**Answer: D) Keep the run failed, inspect the failing stage, and identify only the created IDs for any needed cleanup**

**Explanation:**
A passing run requires successful completion, all eight checks true and reported cleanup, including empty IPv4 default-route lists in the three containers. The helper tracks created IDs rather than deleting unrelated named resources. Abrupt termination can prevent cleanup. Preserve the evidence, use a new output path for a later run, and do not bypass shared network controls to force a pass.

</details>

---

[Back to the diagnostics guide](../../networking/07-linux-network-diagnostics.md) · [HTTP](../../networking/07-linux-network-diagnostics.md#http-message-lab) · [TCP buffers](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab) · [Routing and ICMP](../../networking/07-linux-network-diagnostics.md#routing-icmp-lab) · [MTU and MSS](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab)
