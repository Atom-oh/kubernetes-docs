# Linux Network Performance: Measure Before Explaining

> **Lab baseline**: Owned Ubuntu Server 24.04 LTS or Rocky Linux 9 guest; bounded loopback observations
>
> **Last Updated**: September 15, 2026

## Purpose and prerequisites {#purpose}

This workbook asks whether a slow transaction is waiting on the application, the transport, the kernel or the path.
The deliverable is a reproducible measurement report with competing explanations, negative evidence and restoration.
No fixed latency, throughput gain or benchmark score is promised.

Complete the [beginner course](../beginner/README.md), especially its [monitoring lesson](../beginner/07-monitoring-performance.md).
Read [the kernel network stack](../../kernel/02-network-stack.md) from socket/VFS through transmit, receive and hook placement.
Then review [Linux network diagnostics](../07-linux-network-diagnostics.md#tcp-buffer-lab) for the existing HTTP helper and socket-state interpretation.
[Protocol projects](01-protocol-projects.md) supply the byte-stream and evidence vocabulary.
Read the [existing Pod benchmark guide](../06-pod-network-benchmark.md) later; loopback numbers are not a CNI benchmark.

You need Linux process/file skills, basic Python, TCP sequence/window knowledge, and arithmetic with bits, bytes and seconds.
C and driver development are optional extensions, not prerequisites for the bounded Python exercise.
The authoring of this chapter ran no network/cloud experiment; the criteria below are instructions for a future owned guest run.

## Bootlin and primary reading map {#readings}

The [Bootlin Linux networking training page](https://bootlin.com/training/networking/) was accessible on **September 15, 2026**.
Its freely downloadable [slides](https://bootlin.com/doc/training/networking/networking-slides.pdf) and [EspressoBin lab instructions](https://bootlin.com/doc/training/networking/networking-espressobin-labs.pdf) support study.
Public documents do not include free instructor access, a supplied board or guaranteed compatibility with arbitrary hardware.

| Reading | Needed background | Question to answer here |
|---|---|---|
| Bootlin network stack and userspace interface sections | Linux administration, sockets and protocol layering | Where do application bytes become queued kernel work? |
| Bootlin driver, NAPI and hardware labs | Solid C, kernel/module development, interrupts, DMA and the lab's board/toolchain setup | Which claims require a real driver and NIC? |
| [Kernel NAPI documentation](https://docs.kernel.org/networking/napi.html) | Interrupt/poll distinction | What work is polled and under which budget/context? |
| [Kernel scaling documentation](https://docs.kernel.org/networking/scaling.html) | CPU queues and flow hashing | Does RSS or RPS select the processing CPU? |
| [Segmentation offloads](https://docs.kernel.org/networking/segmentation-offloads.html) | MTU/MSS and packet observation points | Why might a capture show larger units than the wire? |
| [TCP sysctl documentation](https://docs.kernel.org/networking/ip-sysctl.html) | Socket memory, windows and autotuning | Which limit is policy, and which is a per-flow observation? |
| [iproute2 ss source manual](https://github.com/iproute2/iproute2/blob/main/man/man8/ss.8) and [tc source manual](https://github.com/iproute2/iproute2/blob/main/man/man8/tc.8) | TCP states and queue counters | What exactly does each displayed quantity count? |

For the Bootlin hardware track, record the lab PDF revision, required board, serial console, bootloader, kernel tree/configuration and cross-toolchain.
The checked course uses an EspressoBin with a Marvell Armada 3720 ARM64 processor; do not assume the beginner VM substitutes for that documented environment.
If that setup is unavailable, complete the packet-path analysis and label hardware observations unavailable.
Training enrollment and certificates are separate from this workbook's evidence-based completion.

## Measurement design before commands {#measurement-design}

Write this experiment card before starting. Blank fields are work to do, not permission to invent results.

| Field | Core exercise choice |
|---|---|
| Hypothesis | Delaying the client body read increases application completion time without requiring path loss |
| Resource owner / observer | Your user in one disposable guest; record guest name and network namespace |
| Client / server | Python client and repository HTTP helper; `127.0.0.1:18080` only |
| Variables | Request/echo body 64 or 4096 bytes; client read pause 0 or 0.15 seconds |
| Fixed controls | One request at a time, new TCP connection per request, same endpoint/helper |
| Budget | One warm-up plus 15 measured requests; fewer than 42 KiB payload in each direction |
| Deadline | Client 60 seconds overall, 2-second socket-operation timeout; server 180 seconds |
| Observers | Client monotonic durations; scoped `ss`; interface/qdisc counters before and after |
| Failure rule | Stop on content/status failure, unexpected listener, missing tool or deadline expiration |
| Recovery | Close own clients, stop own foreground server, verify listener removal |

A 0.15-second pause is an **input parameter**, not a measured network delay.
The workload is intentionally too small to force receiver-window exhaustion or saturate loopback.
Do not use its goodput to claim NIC capacity, Internet latency or routing convergence.
Keep the guest idle where practical and note other workloads; loopback counters include other processes.

## Tools, roles and scope {#readiness}

Follow [beginner guest-tools preparation](../beginner/README.md#guest-tools) for missing packages, including transaction preview and recovery records.
Install only tools needed for the selected path on the owned guest; the base image does not guarantee they exist.

| Tool | Ubuntu provider | Rocky provider | Role / privilege |
|---|---|---|---|
| `python3` 3.9+ | `python3` | `python3` | Client/server, normal user |
| `ip`, `ss` | `iproute2` | `iproute` | Scoped observations, normal user |
| `tc` | `iproute2` | `iproute-tc` | Read qdisc counters, normal user where allowed |
| `timeout`, `sha256sum` | `coreutils` | `coreutils` | Bound execution and identify helper |
| `tcpdump` | `tcpdump` | `tcpdump` | Optional packet capture, sudo for capture only |
| `ethtool` | `ethtool` | `ethtool` | Optional existing NIC inspection; some queries need privileges |
| `pidstat` | `sysstat` | `sysstat` | Optional process CPU sampling |
| `bpftool`, `bpftrace` | Kernel/distribution-dependent packages | Kernel/distribution-dependent packages | Optional; verify provider, kernel support and authorization separately |

Do not install kernel packages or enable tracing just to satisfy an optional row.
For BPF tooling, record the installed package owner, tool/kernel versions, BTF availability and access error if any.
Presence of a command alone does not establish usable BPF permissions.

From the repository root in the guest:

```bash
command -v python3 ip ss tc timeout sha256sum
python3 --version
uname -r
ip -Version
ss -V
tc -V
sha256sum examples/networking/foundations/http_lab.py
ss -ltn 'sport = :18080'
```

If the listener filter returns any listener, stop and select another free port consistently; never stop an unrelated service.
Create a new private directory with `mkdir -m 700 linux-evidence-01`; use a new name if it already exists.
Record repository revision, OS release, tool versions, namespace and start/end UTC times in that directory.
All client/server commands below run as a normal user in the same guest and namespace.

## Follow the processing path {#packet-path}

Use the existing kernel chapter's diagram, then annotate it with these distinctions.
The common native-driver receive path is NIC queue → NAPI poll → optional native XDP → stack/transport → socket → application.
Driver/device offload modes and generic XDP have different placement; label the mode rather than drawing every hook at the same point.
Transmit work passes from socket/transport through routing and applicable queueing to the device.

| Mechanism | What it changes | Observation and counterexample |
|---|---|---|
| NAPI | Driver event processing via polling, often coordinated with interrupts | A polling budget is not an application latency guarantee |
| RSS | Hardware distributes flows among receive queues | One flow may still hash to one queue; more queues do not split every flow |
| RPS | Software selects CPUs for receive processing | CPU distribution is not proof that the NIC performed RSS |
| GSO / TSO | Software / device segmentation of larger transmit units | A large host-captured unit is not necessarily an oversized wire frame |
| GRO | Combines receive work before higher-layer processing | A capture's unit count need not equal physical frame count |
| qdisc | Queues/schedules applicable egress work | `noqueue` on loopback is not proof that physical NIC queueing is absent elsewhere |
| Socket windows | Receiver flow control and sender congestion allowances | Large configured buffers do not prove either window is fully usable |

Loopback has no physical RSS queues, link serialization or switch path to benchmark.
Avoid projecting its processing details onto a physical driver.

For a **pre-existing owned VM flow**, substitute a written observation plan: identify both endpoints, existing interface/route, flow tuple, owner and original traffic budget.
Take read-only `ethtool -k`, `ethtool -l`, `ethtool -x` and `ethtool -S` observations only on that identified lab interface where supported.
Record “unsupported” or “permission denied” rather than changing drivers, channel counts or offloads.
No broad interface commands or new VM/cloud resources are needed for the core path.

## Bounded loopback experiment {#bounded-experiment}

Save the pre-state before starting the helper:

```bash
ip -s link show dev lo > linux-evidence-01/link-before.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-before.txt
ss -ltn 'sport = :18080' > linux-evidence-01/listener-before.txt
```

Start terminal A's owned server and wait for its ready message:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

In terminal C, start the bounded socket observer just before the client:

```bash
timeout 25s bash -c '
  for sample in {1..40}; do
    date -u +%FT%T.%NZ
    ss -tinm state established "( sport = :18080 or dport = :18080 )"
    sleep 0.5
  done
' > linux-evidence-01/sockets.txt
```

In terminal B, run this original measurement client. It makes no DNS query and reads no proxy configuration.
Its maximum request count is 16, including the warm-up; each connection closes in `finally`.
The 0.25-second pause between requests also bounds request frequency.

```bash
timeout --signal=INT --kill-after=2s 60s python3 - <<'PY' \
  > linux-evidence-01/transactions.jsonl
import datetime
import http.client
import json
import time

phases = [("warmup", 64, 0.0, 1),
          ("small", 64, 0.0, 5),
          ("large", 4096, 0.0, 5),
          ("reader_pause", 4096, 0.15, 5)]
for phase, size, pause, count in phases:
    for sample in range(count):
        connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
        payload = b"x" * size
        row = {"phase": phase, "sample": sample, "bytes": size,
               "pause_s": pause,
               "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start = time.perf_counter()
        try:
            connection.request("POST", "/echo", body=payload,
                               headers={"Content-Type": "application/octet-stream"})
            response = connection.getresponse()
            headers_at = time.perf_counter()
            time.sleep(pause)
            body = response.read()
            finished = time.perf_counter()
            if response.status != 200 or body != payload:
                raise ValueError("Unexpected status or echo content")
            row.update(status=response.status, ok=True,
                       headers_ms=(headers_at - start) * 1000,
                       read_ms=(finished - headers_at) * 1000,
                       total_ms=(finished - start) * 1000)
        except Exception as error:
            row.update(ok=False, error=type(error).__name__,
                       detail=str(error))
            print(json.dumps(row), flush=True)
            raise SystemExit(1)
        finally:
            connection.close()
        print(json.dumps(row), flush=True)
        time.sleep(0.25)
PY
```

Save the client exit status immediately. An interrupted run or fewer than 16 successful rows is incomplete.
The outer timeout can expire without a final JSON row; missing data is not zero latency.
`headers_ms` includes connection/request work up to parsed response headers; it is not a pure RTT or a curl TTFB metric.
`read_ms` includes the deliberate pause and body consumption; library buffering may already hold some content.
`total_ms` measures through response consumption, excluding the later inter-request pause.

After the client and observer finish, collect post-state:

```bash
ip -s link show dev lo > linux-evidence-01/link-after.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-after.txt
ss -tinm state established '( sport = :18080 or dport = :18080 )' \
  > linux-evidence-01/sockets-after.txt
```

**Expected observations:** All completed requests return identical echo bytes; the reader-pause phase should include the configured delay in completion time.
**Negative observations:** Empty `ss` samples are possible because connections are brief; zero queues do not prove a broken observer.
The small echo may not produce visible backpressure or any retransmission.
Counter deltas cover the whole loopback interface, so do not attribute every increment to this client.
If the echo fails, preserve the failing row and server state before diagnosing; do not silently retry until only successes remain.

For optional packet evidence, use [Project B's bounded capture](01-protocol-projects.md#stream-project) in a new evidence directory.
Its 20-second/120-packet limits can omit this run's connections; record partial coverage rather than treating omitted packets as loss.
Do not disable checksum/segmentation offloads to make the capture look familiar.

**Restoration:** Stop only your foreground server with Ctrl+C or allow its 180-second deadline to expire.
The client/observer terminate through their bounds; interrupt only those foreground processes if needed.
Verify `ss -ltn 'sport = :18080'` returns no listener; TIME_WAIT sockets may legitimately remain.
Keep the evidence directory or remove only its named files after review.
No qdisc, sysctl, NIC offload, route or BPF attachment was changed by this exercise.

## Interpret windows, loss and latency {#interpretation}

Compare [socket queue semantics](../../kernel/02-network-stack.md#ss-tcp-queues) with the raw `ss` samples.
ESTABLISHED `Recv-Q` counts received data awaiting application consumption; `Send-Q` counts unacknowledged data, including data not yet sent.
LISTEN columns instead concern the accept queue/backlog, not payload occupancy.
`skmem` accounts for memory and overhead; it need not equal stream bytes, advertised window or `cwnd`.
If printed, `cwnd` is normally in segments; use the corresponding MSS and units before comparing with bytes.

For a **hypothetical** 100 Mbit/s path with 40 ms RTT:
`BDP = 100,000,000 bit/s × 0.040 s ÷ 8 = 500,000 bytes`.
This is an arithmetic example, not a measurement or a command to set buffers.
Relate it to [BDP and socket policy](../../kernel/02-network-stack.md#tcp-bdp-reasoning).
A smaller effective window can constrain throughput, but raising a global limit is not evidence that windows caused this run's delay.

Exclude warm-up; report each phase's sample count, failures, minimum, median and maximum from actual rows.
Five samples cannot support a credible p99 service objective or a production capacity claim.
Response payload bits divided by transaction seconds is application goodput for that operation, including connection/processing delay.
It is neither Ethernet line rate nor a direct measure of congestion.

| Observation | Candidate explanation | Evidence needed to separate alternatives |
|---|---|---|
| High completion time, ordinary header time | Client consumption delay | Client phase/timestamps; do not blame the route from total time alone |
| Persistent receive queue | Slow application reader or scheduling | Reader progress, CPU evidence and repeated per-flow samples |
| Persistent send queue | Unsent data, missing ACKs or receiver limitation | Window/retransmission fields and paired endpoint evidence |
| Retransmissions increase | Loss, reordering or spurious retransmission | Sequence/timing evidence; one counter does not locate a drop |
| tcpdump capture drops | Observer cannot keep up | Capture statistics; these are not directly TCP/path loss |
| qdisc drops increase | Local queue policy/pressure | Same interval/interface and traffic attribution |

## eBPF/XDP observation and failure design {#bpf-observation}

Read [kernel BPF documentation](https://docs.kernel.org/bpf/) and Bootlin's hook discussion before selecting a tool.
For an already provisioned, owned lab with permission, `bpftool prog show` and `bpftool net show` can inventory existing programs/attachments.
These are optional read-only observations; unavailable permissions mean “not observed,” not “no BPF.”
Program existence alone does not prove this flow executed it or that it improved throughput.

Design, without loading, one tracepoint/kprobe observation: name the hook, tuple/namespace filter, fields, duration, event cap and overhead check.
Determine from that kernel's event format/BTF whether the needed fields exist; never invent a universal probe signature.
Specify event loss accounting and how you would match timestamps to client samples.
A tracepoint, TC program and native XDP program observe different stages; absence at one hook is not absence everywhere.
No BPF program is attached, detached or replaced in this workbook.

**Optional netem extension is design-only here.** Do not execute host-global qdisc/sysctl/offload commands.
Write a separate owned namespace/VM proposal with management outside the affected interface.
Record namespace/VM identity, interface, original qdisc hierarchy/handles/options, routes, offloads and all proposed changes.
Specify one variable, an exact finite flow/duration, a baseline and an expected negative result.
Require an exact restoration plan before execution: deleting a root qdisc does not recreate an arbitrary original hierarchy.
For a fresh disposable environment, destruction of only its recorded resource IDs can be the restoration boundary.
If pre-state cannot be reconstructed or ownership is uncertain, the proposal stays design-only.

## Completion and handoff {#completion}

- [ ] Explain the Bootlin public-material/hardware boundary and record source/tool/helper versions.
- [ ] Preserve experiment card, raw rows, failure/exit status, observer coverage and pre/post counters.
- [ ] Distinguish input delay from measured duration, queue bytes from memory and BDP from configured buffers.
- [ ] Give at least two plausible explanations for a slow result and evidence that would reject each.
- [ ] Label absent NIC/BPF/packet observations and avoid claims of unmeasured throughput gains.
- [ ] Confirm server termination and no persistent configuration changes.
- [ ] Complete the [quiz](../../quizzes/networking/expert/04-linux-performance-quiz.md) with explanations.

Deliver these artifacts to the [automation capstone](06-automation-capstone.md).
Use [datacenter EVPN](03-datacenter-evpn.md) for overlay/MTU context and [cloud/CNI design](05-cloud-cni-design.md) for additional path boundaries.
Return to the [expert course map](README.md) to choose the next specialization.
