# 7. First Steps in Network Monitoring and Performance

> **Learning baseline**: Ubuntu Server 24.04 LTS, with an alternate Rocky Linux 9 path
>
> **Last Updated**: September 15, 2026

**Prerequisites:** Complete [lessons 1–6](README.md#course-map). The two VMs communicate through their lab NICs, and TCP 8000 on the server is allowed only from the lab client. If another lab server owns port 8000, identify it and stop it using that exercise's procedure.

**Outcomes:** Distinguish listeners, connections, queues, packets and traffic volumes, and turn “it is slow” into a testable question. Allow approximately 2–3 hours including practice.

## Tools and observation points {#observation-tools}

| Question | Tool | What it cannot establish |
|---|---|---|
| Which address and port is a program listening on? | `ss -ltnp` | Whether an external client can reach it |
| What are the connection states and queues? | `ss -tinm` | The cause of loss from one snapshot |
| Which packets crossed this NIC? | `tcpdump` | Activity on other, uncaptured NICs or namespaces |
| Which host pairs use bandwidth? | `iftop` | Application processing time or exact billed traffic |
| Where does an HTTP request spend time? | `curl -w` | Timing inside individual server functions |

Older material may use `netstat`. This course uses `ss` for socket observation. `netstat -lnt` and `ss -ltn` answer similar questions, but their formats and fields are not identical. Missing `netstat` is not a reason to remove newer tools or reconfigure the system.

Check the required packages on the server. On Ubuntu:

```bash
sudo apt update
sudo apt install iproute2 tcpdump python3
```

On Rocky:

```bash
sudo dnf install iproute tcpdump python3
```

The client needs `curl`; install it using the package-manager instructions in [lesson 1](01-linux-cli.md).

## Generate a small HTTP workload {#small-http-workload}

**Server console A:** Create one exercise file in an empty temporary directory.

```bash
LAB_WEB=$(mktemp -d /tmp/net-web.XXXXXX)
printf 'network lesson\n' > "$LAB_WEB/index.html"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

This server exposes the selected directory and stops after five minutes. Exit status 124 means `timeout` reached its limit. This is not a production web server with TLS and user authentication. Do not put other files or symbolic links in the exercise directory.

**Client:** Send one request, then ten more at one-second intervals.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
for n in $(seq 1 10); do
  curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
    -sS -o /dev/null http://192.0.2.20:8000/
  sleep 1
done
```

**Pass criteria:** The first response is HTTP 200 with `network lesson` in its body. Subsequent requests finish without errors and appear in the server log. If they fail, return to the [lesson 4 diagnosis sequence](04-dns-connectivity.md) instead of increasing load.

## Read socket states and queues {#socket-observation}

**Server console B:** Use another terminal.

```bash
sudo ss -ltnp 'sport = :8000'
ss -tinm '( sport = :8000 or dport = :8000 )'
```

Find the `192.0.2.20:8000` listener in the first command. Repeat the second observation while requests run. Short connections can finish between snapshots; the absence of an ESTABLISHED row does not establish request failure. Correlate server logs and packet captures.

| State or field | Interpretation |
|---|---|
| LISTEN `Recv-Q` / `Send-Q` | Connections awaiting acceptance / maximum accept backlog |
| ESTABLISHED `Recv-Q` | In-order bytes not yet read by the application |
| ESTABLISHED `Send-Q` | Unacknowledged stream bytes, including data not yet sent |
| `rtt` | TCP's round-trip estimate, not total HTTP duration |
| `cwnd` | Sender congestion window, usually shown in segments by `ss` |
| `skmem` | Socket memory accounting including overhead, not simply queued payload bytes |

Zero queues are normal with these small requests. Building a large queue is not a success condition. The [Linux TCP queue exercise](../07-linux-network-diagnostics.md#tcp-buffer-lab) uses a longer-lived connection and provides further interpretation.

## Capture packets on a selected NIC {#packet-capture}

**Server console B:** Match the lab NIC against its MAC address recorded in the hypervisor.

```bash
ip -br link
```

Substitute the verified name below. `enp0s8` is an example, not an instruction to select your management NIC.

```bash
LAB_IF=enp0s8
ip -br address show dev "$LAB_IF"
sudo timeout 15 tcpdump -ni "$LAB_IF" -c 20 \
  'host 192.0.2.10 and tcp port 8000'
```

Start the capture, then **repeat the curl request from the client**. `-n` avoids name lookups, `-i` selects the interface, and `-c 20` limits the captured packet count. The 15-second limit may finish first.

Illustrative TCP flags include `[S]` for SYN, `[S.]` for SYN+ACK, `[.]` for ACK, and `[F.]` for FIN+ACK. Data and acknowledgments can be combined in different ways. Do not memorize a fixed rule such as “one HTTP request is exactly three packets”.

To save evidence, capture only your exercise traffic for a short period.

```bash
LAB_CAPTURE=$(mktemp -d /tmp/net-capture.XXXXXX)
sudo timeout 15 tcpdump -Z "$(id -un)" -ni "$LAB_IF" -c 20 \
  -w "$LAB_CAPTURE/http.pcap" 'host 192.0.2.10 and tcp port 8000'
sudo tcpdump -nn -r "$LAB_CAPTURE/http.pcap"
```

Send the client request again while the write command runs. `-Z "$(id -un)"` drops to the current regular user after opening the capture device, allowing the file to be written in that user's temporary directory. A PCAP can contain addresses and real payloads. Use only the exercise string, not SSH credentials or real user traffic. The read command uses `sudo` to accommodate file-permission differences.

**Interpretation:** Identify request and response addresses and ports. If the capture is empty, first check its NIC, filter and time window. NIC offload can make host-observed packet sizes and checksums differ from the wire. A checksum warning in one capture does not establish a network fault.

## Bandwidth and request timing {#bandwidth-and-time}

`iftop` is optional. Ubuntu can install it with `sudo apt install iftop`. If Rocky's configured repositories do not provide it, skip this exercise or first check the [EPEL prerequisites in lesson 6](06-firewalls-host-security.md). A failed `sudo dnf install iftop` is not a reason to run an arbitrary external installation script.

**Server:** In the terminal where the verified `LAB_IF` is set:

```bash
sudo iftop -nNP -i "$LAB_IF" -f 'host 192.0.2.10'
```

Repeat client requests, read directional rates, and press `q` to exit. Small, short requests may appear close to zero. This is not a link-capacity or internet-throughput test.

**Client:** Observe HTTP timing separately.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -sS -o /dev/null \
  -w 'dns=%{time_namelookup} connect=%{time_connect} first_byte=%{time_starttransfer} total=%{time_total}\n' \
  http://192.0.2.20:8000/
```

Values are seconds elapsed from the start. This request uses an IP literal and does not measure DNS performance. Time to first byte includes earlier steps and server preparation; do not add all fields as though they were independent intervals.

| Measurement | Meaning | Conditions to control |
|---|---|---|
| Latency | Duration of an operation or round trip | Request size, route, server load |
| Throughput | Amount delivered per unit time | Concurrency, direction, bytes versus bits, duration |
| Loss/retransmission | Observed missing packets or TCP recovery | Capture location/drops, route changes, time window |
| Resource use | CPU, memory and I/O activity or waiting | Process, VM allocation, other workload |

`1 byte = 8 bits`. Do not equate `100 Mbit/s` with `100 MB/s`. For repeated measurements, record conditions and minimum/median/maximum values or another suitable distribution.

## Kernel and I/O study comes next {#kernel-next}

These commands **only observe**:

```bash
uname -r
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem
lsblk -o NAME,TYPE,SIZE
```

The buffer policy values returned by `sysctl` are not each socket's current usage. Before increasing them, distinguish [socket buffers, windows and BDP](../../kernel/02-network-stack.md#tcp-buffer-policy). After identifying a disk with `lsblk`, reading `/sys/block/DEVICE/queue/scheduler` shows supported/selected block I/O schedulers; not every virtual device offers the same choices.

A block I/O scheduler handles storage requests, while a network qdisc handles network transmit queuing. Sharing the word “scheduler” does not make them interchangeable tuning controls. This lesson does not change sysctls, MTU, qdiscs or I/O schedulers. Advanced work requires a separate experiment with one changed variable, measurements and rollback.

## Cleanup and completion {#completion}

Stop the server in console A with Ctrl+C or its time limit. In **that same terminal**, remove only your exercise file and directory.

```bash
rm -- "${LAB_WEB:?}/index.html"
rmdir -- "${LAB_WEB:?}"
```

In the capture terminal, remove the capture too.

```bash
sudo rm -- "${LAB_CAPTURE:?}/http.pcap"
rmdir -- "${LAB_CAPTURE:?}"
```

`${VARIABLE:?}` stops the command when the variable is unset or empty. If a directory is not empty, investigate instead of using a broad recursive deletion.

- Explain why a listener, a TCP connection and HTTP success are different evidence.
- Identify both directions' addresses/ports in a PCAP and record the capture point.
- Explain queue/bandwidth units and the DNS-measurement limit of an IP-literal request.
- Distinguish observation from tuning that needs a separate controlled experiment.

## References and next lesson

- [iproute2 ss manual](https://man7.org/linux/man-pages/man8/ss.8.html)
- [tcpdump manual](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [iftop author's manual](https://www.ex-parrot.com/pdw/iftop/iftop.8.html)
- [curl manual](https://curl.se/docs/manpage.html)
- [Python 3.12 http.server](https://docs.python.org/3.12/library/http.server.html)
- [Linux block multi-queue](https://docs.kernel.org/block/blk-mq.html)

[Previous: Firewalls and host security](06-firewalls-host-security.md) · [Quiz](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) · [Next: Capstone](08-container-cloud-capstone.md)
