# Protocol Projects: Explain the Bytes and the Missing Replies

> **Lab baseline**: Owned Ubuntu Server 24.04 LTS or Rocky Linux 9 guest; offline analysis and bounded loopback traffic
>
> **Last Updated**: September 15, 2026

## Purpose and entry criteria {#purpose}

An expert protocol investigation connects an application claim to a specific exchange and states what the evidence cannot establish.
This workbook produces a probe-correlation ledger, an HTTP/TCP evidence bundle, and a protocol-boundary report.
These are original exercises, not solutions to graded university projects.

Complete the [eight beginner lessons](../beginner/README.md) first, including restoration and the final service diagnosis.
You should be able to distinguish an address, next hop, DNS answer, listening socket, and HTTP status.
You also need basic Python reading, byte/hex notation, and the ability to compare two files.

Read these existing guides before collecting evidence:

- [IP, ICMP and traceroute](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation): identify the sender of an error and the packet it quotes.
- [TCP and TLS](../../basics/06-network-fundamentals-part2.md): separate transport delivery from authentication.
- [HTTP/1.1 message structure](../../basics/06-network-fundamentals-part3.md#http11-message-structure): locate the header terminator and count content bytes.
- [Linux network diagnostics](../07-linux-network-diagnostics.md): understand the existing bounded HTTP helper and recorded routing exercise.

## Public curriculum map {#readings}

Availability was checked on **September 15, 2026**.
The [Fall 2026 CS168 site](https://fa26.cs168.io/) is under construction.
Use the accessible [Summer 2026 official archive](https://su26.cs168.io/) for the following reading order; its dates are historical.
An accessible specification does not promise enrollment, every recording, or access to an institutional grader.

| Public material | Read for | Original deliverable here |
|---|---|---|
| Archive Intro 1–3; [CS168 textbook](https://textbook.cs168.io/) layers, headers and design | Demultiplexing and best-effort delivery | Label each header and the component interpreting it |
| [Project 1 guide](https://su26.cs168.io/proj1/guide/) and [Project 1A instructions](https://su26.cs168.io/proj1/proj1a/) | TTL-limited UDP probes and quoted packets | Project A: correlate replies with a send ledger |
| [Project 1B instructions](https://su26.cs168.io/proj1/proj1b/) | Incomplete, unrelated and repeated replies | Reject misleading evidence without inventing hops |
| Archive Routing 1–7; [Project 2 instructions](https://su26.cs168.io/proj2/) | Routing state versus forwarding behavior | Continue in [routing policy and convergence](02-routing-policy-convergence.md) |
| Archive Transport 1–4; [Project 3 instructions](https://su26.cs168.io/proj3/) | Sequence space, receive windows, retransmission and timers | Project B: separate stream delivery, framing and congestion |
| Archive DNS, HTTP/CDNs and end-to-end TLS readings | Naming, security and application boundaries | Project C: choose the evidence needed at each boundary |

CS168 Project 3 implements a **subset of TCP without congestion control**.
Read the congestion lectures separately; a passing transport assignment is not evidence of a production congestion controller.
The archived setup contains Python 3.7 testing notes and mixed semester directory names.
If choosing that optional assignment, follow its own setup and record the exact downloaded revision; do not downgrade this workbook's guest Python.
The textbook calls itself beta: use protocol specifications to resolve implementation details.

Optional continuation: **CS144 in C++** is suitable after you can reason about byte streams, ownership, build tools and debugging.
The historical `cs144.github.io` entry was unavailable during this check; the reported 404 is not a usable lab prerequisite.
Recheck an official Stanford course listing and its current instructions before selecting a term.
Record which starter repository, license, compiler and tests are actually accessible.
This workbook promises neither a free current repository/grader nor an enrollment route.
Its completion criteria do not require CS144, and no graded implementation code is reproduced here.

## Tool readiness and evidence contract {#readiness}

Return to [beginner guest tools](../beginner/README.md#guest-tools); command availability is a gate, not an assumption.
Use that page's selected-package preview/install workflow only inside your disposable guest.
Keep an existing Rocky `curl-minimal` provider if it works.

| Role in this workbook | Ubuntu package/provider | Rocky package/provider | Required here |
|---|---|---|---|
| HTTP client and version report | Existing `curl` | Existing `curl-minimal` or `curl` | Yes |
| Bounded server and analysis | `python3`, version 3.9+ | `python3`, version 3.9+ | Yes |
| Socket/address observations | `iproute2` | `iproute` | Yes |
| Capture and offline decode | `tcpdump` | `tcpdump` | For measured packet evidence |
| Wall-time bound and hashing | `coreutils` | `coreutils` | Yes |
| Optional future path probes | `traceroute`; beginner `tracepath` is a different tool | `traceroute`; `tracepath` comes from `iputils` | No, Project A is offline |
| Optional DNS investigation | `bind9-dnsutils` | `bind-utils` | No live DNS query required |

In the guest, from a checkout of this repository:

```bash
command -v python3 curl ip ss timeout sha256sum tcpdump
python3 --version
curl --version
ip -Version
ss -V
tcpdump --version
sha256sum examples/networking/foundations/http_lab.py
```

Record the guest release, kernel, repository revision, helper hash, tool versions and curl feature list.
An HTTP2/HTTP3 feature missing from curl is a client capability limit, not a server failure.
Check `ss -ltn 'sport = :18080'` before starting; if any listener exists, stop and choose a different free port consistently.
Never terminate an unrelated listener.

Use one evidence directory per attempt, created with `mkdir -m 700 protocol-evidence-01`; if it exists, choose a new name.
The examples use that name from the repository root.
Only synthetic lesson content belongs in captures; credentials, cookies and real user traffic are unnecessary.
Label each item `measured`, `imported`, `synthetic` or `design-only`, with time, observer, namespace and capture filter.
A supplied transcript is not a measurement made on your guest.

## Concepts to carry into every project {#concepts}

| Boundary | Invariant or distinction | Evidence that is insufficient |
|---|---|---|
| IP → transport | Protocol/Next Header selects the next parser | Port 443 alone does not establish HTTPS or QUIC |
| Probe → ICMP error | The error quotes the triggering packet | The outer router address alone does not identify a probe |
| TCP → application | TCP delivers an ordered byte stream | A `send()` or `recv()` boundary is not an HTTP message boundary |
| Receiver → sender | Advertised receive window limits receiver pressure | Receive-buffer allocation is not the congestion window |
| Network → sender | Congestion control limits load on the path | A retransmission alone does not locate congestion |
| Application → user | HTTP status/body describe an application result | TCP establishment does not prove the requested operation succeeded |

Use [TCP RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) for stream semantics and sequence space.
For a window-based explanation, the effective in-flight allowance depends on both `cwnd` and the receive window, after accounting for outstanding bytes.
Pacing, available application data and implementation details also constrain sends.
A pure ACK consumes no sequence space; SYN and FIN each consume one position.

## Project A: A probe-correlation ledger {#probe-project}

**Purpose:** Explain an incomplete route observation without turning unrelated replies into hops.
**Environment:** Paper or a local editor; no packets are sent and no router is created.
Read the CS168 traceroute guide, then [ICMP RFC 792](https://www.rfc-editor.org/rfc/rfc792.html).
Reuse the [routing/ICMP guide](../07-linux-network-diagnostics.md#routing-icmp-lab) to recognize its ICMP Echo probe method; that differs from CS168's UDP method.

Create this original **synthetic send ledger**. Addresses below are documentation addresses, not probe targets:

```text
run,probe,ttl,src,dst,protocol,sport,dport
paper-01,A,1,192.0.2.10,198.51.100.20,UDP,41000,33451
paper-01,B,2,192.0.2.10,198.51.100.20,UDP,41000,33452
paper-01,C,3,192.0.2.10,198.51.100.20,UDP,41000,33453
```

Treat the following as decoded records, **not a pcap and not measured timing**:

| Record, in receive order | Outer reply | Quoted original packet | Assignment |
|---|---|---|---|
| R1 | `192.0.2.1`, ICMP 11/0 | Full IPv4 + UDP header for A | Fill in |
| R2 | `192.0.2.1`, ICMP 11/0 | Identical quote to R1 | Fill in |
| R3 | `203.0.113.7`, ICMP 11/0 | B's tuple except destination `198.51.100.99` | Fill in |
| R4 | `198.51.100.20`, ICMP 3/3 | Full IPv4 + UDP header for C | Fill in |
| R5 | `203.0.113.8`, ICMP 11/0 | Quoted IPv4 header ends before UDP ports | Fill in |

Write a ledger containing `record`, `candidate_probe`, `decision`, `reason`, `confidence` and `missing_fields`.
Use separate decisions for matched, duplicate, unrelated and insufficient evidence.
Do not fabricate a reply for B to make the diagram continuous.

Then add three cases of your own:

1. A late reply from a previous run that reused the same ports.
2. A valid quoted IPv4 header with options, so its length exceeds 20 bytes.
3. A reply received after the declared observation deadline.

State which identifiers and send/receive windows would disambiguate each case and when the available quote cannot do so.
An ICMP quote may be too short to include an application nonce; do not depend on unavailable bytes.
For an ICMP Echo probe, correlate quoted identifier/sequence instead of inventing UDP ports.

**Expected observations:** A supports one TTL-1 response; C's correlated Port Unreachable supports destination arrival for this UDP probe.
**Negative observations:** R2 is no new probe result; R3 cannot satisfy B; R5 cannot uniquely identify a tuple.
No matching B reply means unknown within the collection window, even when a later hop responds.
It does not establish that B's router drops forwarded application traffic.

Traceroute RTT includes the reply path and router response behavior.
Changing probe ports may change ECMP selection; a list of responding addresses is not a proof of one stable application path.
**Restoration:** Keep the original records immutable; discard only your derived scratch ledger if restarting.
**Completion:** Every decision cites quoted fields or a specific missing field, and the three extra cases have explicit rejection/uncertainty rules.

## Project B: HTTP boundaries on one TCP stream {#stream-project}

**Purpose:** Show that application length, TCP bytes and observed segments answer different questions.
**Environment:** One owned guest, client/server on `127.0.0.1:18080`, no external target or proxy.
Only capture requires sudo; the server and clients run as your normal user.
Limit the exercise to the requests below, one at a time; no more than ten requests and no request body above 4096 bytes.

Start the existing helper in terminal A from the repository root:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

After the listener appears, start this capture in terminal B, also from the repository root:

```bash
sudo timeout --signal=INT --kill-after=2s 20s \
  tcpdump -i lo -p -nn -U -s 512 -c 120 -w - \
  'tcp port 18080' > protocol-evidence-01/http.pcap \
  2> protocol-evidence-01/capture.log
```

Wait for the capture's “listening on” line in the log before sending requests in terminal C.
The shell creates the output file as your user; tcpdump writes pcap bytes to stdout.
The capture stops at 120 packets or 20 seconds; timeout exit 124 is a timer outcome, not proof of a broken network.
Keep the exit status and final capture counters. A 512-byte snap length can truncate payload; record that limit.

```bash
curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 3 --http1.1 -I \
  http://127.0.0.1:18080/lesson
printf 'phase=one\nphase=two\n' | \
  curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  --data-binary @- http://127.0.0.1:18080/echo
curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  http://127.0.0.1:18080/missing
```

The echo input is **20 bytes**, including both LF characters.
Save each response separately in your notes and locate the status, Content-Length and actual content.
GET `/lesson` has six content bytes; HEAD describes that representation without returning its body.
The missing path should produce HTTP 404; without `--fail`, curl can exit successfully for that HTTP error.
That is successful HTTP communication carrying an unsuccessful resource lookup.

Decode the completed capture without privileges:

```bash
tcpdump -nn -tttt -vv -r protocol-evidence-01/http.pcap \
  'tcp port 18080'
sha256sum protocol-evidence-01/http.pcap
```

Use the [tcpdump manual](https://www.tcpdump.org/manpages/tcpdump.1.html) to explain flags, sequence ranges and capture drops.
Choose one connection by its two endpoint pairs and identify SYN, SYN-ACK, ACK, payload ranges and closure if captured.
Do not require a particular packet count or one segment per request; annotate missing handshake/closure as collection limits.
For raw HTTP byte rules, consult [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html) and the [curl manual](https://curl.se/docs/manpage.html).

**Original framing exercise, offline:** Design a parser for two-byte unsigned big-endian length followed by that many payload bytes, capped at 64 bytes.
Its synthetic input is `00 03 63 61 74 00 02 6f 6b`; this is your own protocol, not HTTP.
Trace these delivery partitions: all bytes at once; one byte at a time; split after the first length byte; split in the first body.
Record buffered bytes, needed bytes and emitted records after each delivery.
Add EOF midway through a body and a length of 65; define a bounded failure, not an indefinite wait or unbounded allocation.
You may implement your own offline parser, but a state table and complete cases satisfy this exercise.

**Original window exercise, offline:** Assume MSS 1000 bytes, `cwnd` 4 segments, receive window 9000 bytes and 3000 bytes already outstanding.
Calculate the additional allowance using `max(0, min(cwnd × MSS, rwnd) − outstanding)`, ignoring pacing and assuming application data is ready.
Repeat with only `rwnd` changed to 3500 bytes, then with `rwnd` zero; identify the limiting side in each case.
Explain why a zero receive window does not establish network congestion, and why a retransmission alone does not establish receiver exhaustion.
These are synthetic state snapshots, not a simulation of a complete TCP sender or measured performance.

**Expected observations:** Two identical logical records emerge under every complete partition; the HTTP echo retains its 20 input bytes.
**Negative observations:** An incomplete record must not be reported as complete, and the oversized frame must not be accepted.
The window snapshots permit 1000, 500 and zero additional bytes respectively under the stated simplified model; a negative allowance is clamped to zero.
Apparent outgoing checksum errors can reflect offload observation; a capture drop is not automatically path loss.
**Restoration:** Stop only your foreground helper with Ctrl+C, or let its 180-second timer expire; the capture has its own bound.
Recheck the listener filter. Retain the evidence; remove only the specifically named files/directory if you choose to discard it.

## Project C: Prove a boundary, not a port number {#boundary-project}

**Purpose:** Plan the minimum evidence that distinguishes naming, transport, security and application failure.
**Environment:** Offline report using existing owned traces if available; no public-site probing is required.

| Case | Evidence to request | Wrong conclusion to reject |
|---|---|---|
| DNS returns an A record; TCP connect fails | Resolver result, selected address, connect error and endpoint capture | “DNS success proves the service works” |
| AAAA exists but the guest has no usable IPv6 route | Family-specific route/address state and client selection | “IPv6 DNS answer proves IPv6 reachability” |
| TCP connects; TLS certificate verification fails | Intended hostname, trust/verification error, TLS endpoint identity | “Disable certificate validation to prove recovery” |
| HTTPS request negotiates HTTP/1.1 | Client features and negotiated HTTP version | “Port 443 or `--http2` proves HTTP/2” |
| HTTP/2 has several streams over TCP | Stream IDs plus connection/transport loss evidence | “Multiplexing eliminates TCP head-of-line blocking” |
| HTTP/3 is suspected | QUIC/version and application negotiation evidence from an endpoint | “Every UDP/443 packet is HTTP/3” |

Read [HTTP/2 RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [QUIC RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html) and [HTTP/3 RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html).
HTTP/2 multiplexes application streams on TCP; missing TCP bytes can delay delivery across those streams.
QUIC provides streams, reliability and congestion control above UDP, integrating TLS; HTTP/3 maps HTTP onto QUIC.
Loss affecting one QUIC stream need not block delivery on another, but shared congestion limits and application dependencies remain.
A passive encrypted capture usually cannot supply HTTP content; endpoint plaintext logs are a different observation point.

For each case, draw the relevant boundary and write one positive assertion, one negative assertion and one next observation.
Explain how curl's `--resolve` could isolate address lookup while preserving a URL hostname for TLS, without claiming it tests DNS.
Distinguish `--http3` fallback behavior from `--http3-only`; check local support before designing such a test.
The IPv4-only helper in Project B cannot become an IPv6/TLS/HTTP2 server by changing a client flag.

Use [IPv6 RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html) and [ICMPv6 RFC 4443](https://www.rfc-editor.org/rfc/rfc4443.html) to extend Project A on paper.
Replace TTL with Hop Limit, IPv4 header-length parsing with IPv6/extension-header parsing, and IPv4 ICMP types with ICMPv6 types.
IPv6 routers do not fragment forwarded packets; Packet Too Big evidence has a different role from Time Exceeded.
Include address family and scope in the ledger; IPv6 neighbor discovery is not ARP.

**Expected observations:** Your report distinguishes an authenticated application response from reachability and capability.
**Negative observations:** Unsupported tools and absent traces are marked unavailable, never measured failures of the remote protocol.
**Restoration:** No runtime state changes; preserve original imported evidence and its provenance.

## Completion and portfolio handoff {#completion}

- [ ] Record the reading URLs/term, access date, guest/tool versions and helper revision/hash.
- [ ] Explain Project A's five records and three added cases without inventing missing hops.
- [ ] Preserve measured HTTP evidence with status, content lengths, one TCP connection and capture limitations.
- [ ] Demonstrate framing invariance and both malformed/incomplete negative cases.
- [ ] Explain receive flow control versus congestion control and why this small workload cannot benchmark either.
- [ ] Complete all six boundary cases and the IPv6 extension.
- [ ] Show listener/capture termination and identify any unfinished observation.
- [ ] Answer the [quiz](../../quizzes/networking/expert/01-protocol-projects-quiz.md), explaining the rejected alternatives.

If capture privileges are unavailable, finish the offline work and label packet collection pending.
An imported capture may support analysis, but cannot be presented as a newly reproduced experiment.
The portfolio proves observation and failure reasoning; it is not a certificate or proof of universal protocol expertise.

Return to the [expert course map](README.md), proceed to [routing](02-routing-policy-convergence.md), or deepen host evidence in [Linux performance](04-linux-performance.md).
Carry the evidence contract into the [automation capstone](06-automation-capstone.md).
