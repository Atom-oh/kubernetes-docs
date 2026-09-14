# Linux Network Diagnostics — HTTP, TCP Queues, Routing and MTU

> **Supported environment**: Linux, Python 3.9+, curl and iproute2; local Docker Engine for the routing exercise
> **Last Updated**: September 14, 2026

Start with a request on Linux, identify the socket and next hop, then explain the same packet path across container namespaces. These exercises prepare you to distinguish application, transport and routing evidence before investigating Kubernetes or AWS networking.

Read [IPv4 and next-hop foundations](../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet) and [HTTP message structure](../basics/06-network-fundamentals-part3.md#http11-message-structure) alongside the exercises.

- [HTTP messages](#http-message-lab)
- [TCP queues and buffers](#tcp-buffer-lab)
- [Routing and ICMP](#routing-icmp-lab)
- [MTU, PMTU and MSS](#mtu-mss-lab)
- [The Docker packet path](#docker-packet-path)

## Scope and preparation {#lab-scope}

Run commands from a checkout of this repository. Use separate terminals where indicated.

| Exercise | Requirements | Scope |
|---|---|---|
| HTTP | Python 3.9+, curl | One server on `127.0.0.1:18080`, automatically stopped |
| TCP observation | The HTTP server, Python, `ss` from iproute2 | Read-only observations of the local test port |
| Routing and MTU | Linux Docker Engine, Docker CLI, host iproute2, pre-pulled image | Three temporary containers and two dedicated bridges |

The helpers are [http_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/http_lab.py) and [routing_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/routing_lab.py). Read their contracts and the [examples README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md) before running them.

Commands describe the procedure; the HTTP response excerpt is **illustrative**. Explicitly labeled routing excerpts come from a recorded reference run, not your machine. Judge your run by the stated criteria and the routing helper's JSON record.

The HTTP helper is a small educational HTTP/1.1 server, not a production server or complete RFC implementation. It accepts at most 4096 request-body bytes and only its supported `Content-Length` framing; it rejects transfer coding.

The routing helper uses only `unix:///var/run/docker.sock`, ignoring remote Docker host/context environment selections. It requires a local Linux Engine and access to that socket; a remote context or a differently located rootless socket is not interchangeable.

Its `IMAGE` constant pins this reference, which must already be present in that Engine:

```text
nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
```

The helper does not pull the image. Before creating resources, it checks its fixed subnets against visible host IPv4 routes and existing Docker network ranges. Run one routing exercise at a time; stop on a collision instead of changing shared host routes.

## Lab 1: Read HTTP messages {#http-message-lab}

**Purpose:** Separate the request/status line, fields, header terminator and content bytes.

In terminal A, start the server:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

It binds only to `127.0.0.1` and exits after 120 seconds; the maximum allowed duration is 600 seconds. If the port is occupied, use another free local port consistently in the commands and filters. Do not stop an unrelated listener.

In terminal B, issue a GET and a HEAD:

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 -i http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 5 --http1.1 -I http://127.0.0.1:18080/lesson
```

`--disable` as the first option skips the default curl configuration; `--noproxy '*'` avoids configured proxies. `-i` includes response headers; `-I` sends HEAD, not an ordinary GET with its body hidden.

An illustrative GET response excerpt follows; generated `Date` and `Server` fields are omitted:

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 6

hello
```

The actual body is `b"hello\n"`: hexadecimal `68 65 6c 6c 6f 0a`. The final LF is the sixth byte. Header lines and the header/body separator use CRLF on the HTTP/1.1 wire; this Markdown display uses LF.

Now send those same six bytes to the echo endpoint:

```bash
printf 'hello\n' | curl --disable --noproxy '*' --max-time 5 --http1.1 -i \
  -H 'Content-Type: text/plain' --data-binary @- \
  http://127.0.0.1:18080/echo
```

`--data-binary @-` reads stdin without removing the LF and selects POST. The helper returns the bytes unchanged with `Content-Type: application/octet-stream`; it does not parse text, JSON or forms.

| Observation | Expected criterion | Interpretation |
|---|---|---|
| GET `/lesson` | HTTP/1.1 200, length 6, six content bytes | The length excludes the start line and headers |
| HEAD `/lesson` | HTTP/1.1 200 and length 6, no response body | The field describes the corresponding GET representation |
| POST `/echo` | HTTP/1.1 200, length 6, unchanged `hello` plus LF | Byte preservation is separate from media-type interpretation |

A non-ASCII character can occupy several UTF-8 bytes. Count the encoded bytes sent, including actual newlines, rather than counting visible characters.

Inspect the client's debug trace for the request line and outgoing fields:

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 --trace-ascii - \
  --output /dev/null http://127.0.0.1:18080/lesson
```

This is **curl's client-side debug output**, not a packet capture. Its annotations are not wire bytes, TCP segment boundaries or proof of a router's view. Use only the demonstration data when collecting traces.

With HTTPS, the client can display HTTP plaintext that a passive network capture cannot read without session secrets. HTTP/2 and HTTP/3 also use different binary framing; readable tool output is not their raw encoding.

**Cleanup:** Stop this server with Ctrl+C in terminal A, or let its timer expire. It creates no persistent application data. Restart it for the next exercise if the timer has expired.

## Lab 2: Observe TCP queues and buffers {#tcp-buffer-lab}

**Purpose:** Associate one persistent connection with socket state, stream queues and memory accounting.

Start the same 120-second server in terminal A. In terminal B, run this bounded client:

```bash
python3 - <<'PY'
import http.client
import time

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
try:
    for number in range(30):
        connection.request("GET", "/lesson")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == "6"
        assert body == b"hello\n"
        if number == 0:
            print("Client endpoint:", connection.sock.getsockname(), flush=True)
        time.sleep(1)
finally:
    connection.close()
PY
```

The client consumes each response before reusing the connection. It issues 30 small GETs at one-second intervals, making the established socket easier to observe than separate short curl processes.

While it runs, use terminal C:

```bash
ss -ltn 'sport = :18080'
ss -tinm state established '( sport = :18080 or dport = :18080 )'
```

Repeat the second command a few times. These commands inspect the current network namespace and filter on the test port. Both local ends of this loopback connection can appear; distinguish the server port from the client's ephemeral port.

**Expected criterion:** A listener exists on `127.0.0.1:18080`, and an established connection is visible while the client runs. Exact queue, RTT and memory values vary; a zero queue is normal for this small workload.

| Field/state | Meaning |
|---|---|
| ESTABLISHED `Recv-Q` | In-order received bytes not yet consumed by the application |
| ESTABLISHED `Send-Q` | Stream bytes not yet acknowledged, including bytes not yet sent |
| LISTEN `Recv-Q` | Connections queued for `accept()`, not payload bytes |
| LISTEN `Send-Q` | Maximum accept backlog, not a send-buffer size |
| `skmem` `r` / `rb` | Receive memory accounting / receive memory budget |
| `skmem` `w` / `tb` | Queued send memory / send memory budget |
| `rtt`, `mss`, `cwnd` | RTT, TCP data size and congestion-window information; `cwnd` is normally in segments |

Socket memory includes bookkeeping and need not equal the stream queue columns. Listener backlog is also different from the incomplete SYN queue. The [ss(8) manual](https://man7.org/linux/man-pages/man8/ss.8.html) describes the available fields.

Read the current buffer policy without changing it:

```bash
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.ipv4.tcp_moderate_rcvbuf
```

The `tcp_*mem` triples describe minimum/default/automatic-sizing limits, not each socket's current occupancy. Receive autotuning and explicit application socket options affect the result; a budget is not the advertised receive window or `cwnd`.

A growing receive queue suggests investigating reader progress; a persistent send queue needs application, acknowledgment and path evidence. Neither one snapshot nor a larger buffer proves a throughput improvement.

This six-byte workload observes normal operation; it does not deliberately create backpressure or measure maximum throughput. Continue with [socket and buffer reasoning](../kernel/02-network-stack.md#tcp-buffer-policy) before proposing tuning changes.

**Cleanup:** The client closes its connection after 30 iterations, or through `finally` on interruption. Stop the server in terminal A or let its timer expire. No sysctl changes need reversing.

## Lab 3: Follow routing and ICMP {#routing-icmp-lab}

**Purpose:** Prove the selected next hop, distinguish name lookup from forwarding, and match a TTL-limited probe to an ICMP response.

The routing helper builds this temporary topology:

```text
client namespace          router namespace                 server namespace
192.0.2.2/29 --- left --- 192.0.2.3/29
                          198.51.100.2/29 --- right --- 198.51.100.3/29
left bridge: 192.0.2.0/29             right bridge: 198.51.100.0/29
```

Both dedicated bridges set `com.docker.network.bridge.enable_ip_masquerade=false`. The helper removes **all default IPv4 routes inside its three containers**, retaining connected routes, before adding the explicit lab routes.

Containers drop all capabilities, then add only `NET_ADMIN` and `NET_RAW`; forwarding is enabled inside the router namespace. The helper uses neither privileged containers nor host networking, publishes no ports, and creates no AWS resources.

Docker creates host bridges and manages its normal network rules. The helper does not manually change host routes, sysctls or iptables rules; this does not mean the host is untouched or establish an air gap.

It adds a client route for `198.51.100.0/29` via `192.0.2.3` and a server return route for `192.0.2.0/29` via `198.51.100.2`.

Choose an output path that does not exist:

```bash
python3 examples/networking/foundations/routing_lab.py \
  --output ./routing-observation-01.json
```

The helper refuses to overwrite an existing file. This **one invocation also performs the MTU exercise below**; do not start a second concurrent run for that section.

The following are commands the helper executes in the **client namespace**, shown for interpretation rather than as host-shell instructions:

```text
ip -j route get 198.51.100.3
ip -j neigh show to 192.0.2.3
ip -j neigh show to 198.51.100.3
ping -n -c 1 -W 1 -t 1 198.51.100.3
traceroute -n -I -m 4 -q 1 -w 1 198.51.100.3
```

It also resolves the generated router container name using Docker DNS. The target name varies with the run prefix; a DNS answer is not itself a reachability test.

| JSON observation | Expected criterion | Interpretation |
|---|---|---|
| `defaultRoutes` | Empty lists for client, router and server | None of the three containers retains an IPv4 default route |
| `route` | Gateway `192.0.2.3`, source `192.0.2.2` | The destination is reached through the router |
| `dns` | Router name resolves to `192.0.2.3` on the left network | Docker's name lookup is working |
| `nextHopNeighbor` | A MAC address for `192.0.2.3` | ARP resolved the next hop |
| `remoteNeighbor` | Empty | The remote server is not an Ethernet neighbor of the client |
| `ttlOne` | Probe fails; capture contains ICMP Time Exceeded | TTL expires at the router as intended |
| `traceroute` | First hop `192.0.2.3`, destination `198.51.100.3` | An ICMP-probe trace reaches two IP hops |

For `ttlOne`, the helper starts actual `tcpdump` in the router namespace with filter `icmp[0] == 11`, waits for capture readiness, then sends the TTL-1 ping. The intended reply is IPv4 ICMP Type 11 Code 0, quoting the original probe.

The ping failing here is a successful diagnostic stimulus when matched by that capture. The probe is ICMP Echo; Time Exceeded is a separate return message.

Traceroute `-I` uses ICMP Echo probes. UDP and TCP methods can encounter different filtering and have different destination replies. A `*` only records no matching reply within the wait; it does not by itself prove end-to-end loss. RTT includes the response's return path.

Inspect your evidence file after the helper finishes:

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(Path("routing-observation-01.json").read_text())
print("Status:", record["status"])
print("Checks:", record.get("checks", {}))
print("Cleanup:", record.get("cleanup", "not reported"))
PY
```

**Success criterion:** The helper exits successfully, records `status: passed`, all eight named checks are true, and cleanup is reported. Route and DNS success alone cannot substitute for failed packet observations.

**Cleanup:** On normal completion, observation failures and handled interruption, the helper attempts to remove the container and network IDs it created. A cleanup error is a failed run. Abrupt termination can prevent cleanup; use the recorded IDs to identify leftovers, never a broad prune of shared Docker resources. Retain the JSON while interpreting the next section.

### Recorded reference run {#routing-reference-run}

The September 14, 2026 run, linked from the [examples validation record](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md#validation), passed on Linux Docker Engine 25.0.16: all eight checks passed, all three default-route lists were empty, and created IDs were removed. Traceroute observed `192.0.2.3` followed by `198.51.100.3`.

Measured TTL-error packet detail, with the timestamp and interface prefix omitted:

```text
IP 192.0.2.3 > 192.0.2.2: ICMP time exceeded in-transit, length 92
```

This is functional evidence for that environment. It does not guarantee identical timings, interface names, MAC addresses or compatibility on another host.

## Lab 4: Separate MTU, PMTU and MSS {#mtu-mss-lab}

**Purpose:** Explain a size-dependent failure using an actual ICMP error, without mistaking an ICMP payload size for TCP MSS.

Use the same routing invocation and JSON record. The helper finds the router's interface toward the server using route lookup, then sets **that container interface's MTU to 1280**. It does not assume the egress interface is named `eth1`.

For the first client probe, it captures `icmp[0] == 3 and icmp[1] == 4` at the router. It then sends the smaller probe:

```text
ping -n -c 1 -W 1 -M do -s 1372 198.51.100.3
ping -n -c 1 -W 1 -M do -s 1200 198.51.100.3
```

`-M do` requests IPv4 Don't Fragment behavior. With the ordinary 20-byte IPv4 header and 8-byte ICMP header used here:

| Probe | IP packet size | Expected criterion |
|---|---|---|
| 1372-byte ICMP data | `1372 + 8 + 20 = 1400` bytes | Too large for the 1280-byte egress; failure with captured ICMP Type 3 Code 4 |
| 1200-byte ICMP data | `1200 + 8 + 20 = 1228` bytes | Fits that egress; Echo Reply succeeds |

Inspect `pmtu.probeOutput`, `pmtu.capture`, `smallerPacket` and `routeAfterFeedback`. The important evidence is **Fragmentation Needed feedback plus success with a smaller packet**, not a particular RTT or exact output wording.

The same recorded run produced this measured ping line:

```text
From 192.0.2.3 icmp_seq=1 Frag needed and DF set (mtu = 1280)
```

Its 1200-byte data probe received a reply, and `routeAfterFeedback` reported MTU 1280. These are observations from that run, not fixed timing or cache-expiry guarantees.

After feedback, Linux may cache the destination PMTU. A later oversized send can fail locally with “message too long” instead of reaching the router again. `routeAfterFeedback` may show learned MTU information; fields and expiry behavior vary.

The helper's capture corresponds to the deliberately induced first failure in its temporary client namespace. A missing later ICMP message alone does not invalidate earlier feedback.

**MSS is different:** It limits TCP data bytes. For Ethernet MTU 1500 and base IPv4/TCP headers, `1500 − 20 − 20 = 1460` is the base MSS calculation. IP/TCP options and path conditions can reduce actual data per packet.

The 1372 and 1200 numbers above are ICMP data sizes, **not measured MSS values**. Nor should the loopback TCP exercise necessarily show MSS 1460: loopback has its own MTU and kernel behavior.

TSO/GSO/GRO and checksum offload can make a host capture differ from packets on a physical link. Check the interface, namespace and observation point before treating a large captured unit or an apparent checksum error as a wire fault.

IPv6 routers do not fragment forwarded packets and use ICMPv6 Packet Too Big. Classical PMTUD and packetization-layer probing have different feedback dependencies; see [ICMP foundations](../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation).

**Cleanup:** The routing helper removes the temporary router, including its MTU change, with the other created IDs. The host's physical-interface MTU is not changed. Keep or remove only your own evidence file after analysis.

## Explain the Docker packet path {#docker-packet-path}

**Purpose:** Connect the observations to Linux namespaces, virtual Ethernet links and route lookup.

Use the existing routing record; no additional containers are needed. Compare `route`, the neighbor observations, the ICMP captures and the recorded commands:

1. The client namespace selects `198.51.100.0/29 via 192.0.2.3`; the explicit route determines the next hop.
2. The client resolves the router's left-side MAC with ARP. The IP destination remains `198.51.100.3`.
3. A veth pair and the left bridge carry the Ethernet frame to the router. L2 bridging does not consume an IP TTL hop.
4. The router namespace performs IPv4 forwarding: reduce TTL, look up the server route and check the egress MTU.
5. On the right network, the router resolves the server's MAC and sends a new Ethernet frame. The intended routed path does not translate these source/destination IPs.
6. The server's explicit return route uses `198.51.100.2`. Successful request delivery does not eliminate the need for a working reply path.

**Expected criterion:** You can identify each lookup's namespace, its IP destination, the local ARP target and the reply route from the record. Do not infer interface names or MAC values from a different run.

Docker DNS name resolution and Linux packet forwarding are separate observations. A correct DNS answer can coexist with a broken route, forwarding policy or return path.

Each network namespace also has its own loopback device. `127.0.0.1` inside a container does not reach the host's HTTP helper; this exercise does not use host-network mode to change that.

These are two **dedicated user-defined bridges with an explicit router**, masquerading disabled and no IPv4 default routes in the three containers. This defines the intended lab path, not a general security-isolation guarantee. The exercise does not measure default Docker Internet NAT, published-port forwarding or Internet throughput.

**Cleanup:** Reuse the completed record; the routing helper has already attempted resource cleanup. A failed or incomplete record is a prompt to inspect the failing stage, not to disable shared firewall controls.

Continue with [container technology](../basics/03-container-technology.md), then the [Core Services and Networking Lab](../labs/core/03-services-networking-lab.md). Kubernetes CNI, Service translation and AWS VPC routing add their own rules; inspect each at the appropriate layer instead of copying the Docker topology.

## References and review {#references}

- [HTTP semantics: RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) and [HTTP/1.1 framing: RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)
- [curl manual](https://curl.se/docs/manpage.html): HTTP version, HEAD, binary request data and tracing
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html), [socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html) and [Linux TCP buffer policy](https://docs.kernel.org/networking/ip-sysctl.html)
- [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html), [ip-neighbour(8)](https://man7.org/linux/man-pages/man8/ip-neighbour.8.html) and [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [iputils ping manual](https://github.com/iputils/iputils/blob/master/doc/ping.xml) and [traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [ICMP: RFC 792](https://www.rfc-editor.org/rfc/rfc792.html), [IPv4 router behavior: RFC 1812](https://www.rfc-editor.org/rfc/rfc1812.html) and [MSS: RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)
- [Docker bridge networking and driver options](https://docs.docker.com/engine/network/drivers/bridge/)

[Check your understanding](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
