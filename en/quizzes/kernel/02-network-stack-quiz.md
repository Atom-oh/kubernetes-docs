# Kernel Networking Stack Quiz

This quiz tests your understanding of socket/VFS entry paths, TCP buffers and windows, state-dependent queue observations, hook points, and Pod-to-Pod routing.

## Multiple Choice Questions

1. Which component queues outgoing packets before the NIC and exposes its drops through `tc -s qdisc`?
   - A) The NIC's physical layer
   - B) The qdisc — a drop inside the node, visible as `dropped` in `tc -s qdisc`
   - C) The VPC network
   - D) The application's socket buffer

<details>

<summary>Show Answer</summary>

**Answer: B) The qdisc — a drop inside the node, visible as `dropped` in `tc -s qdisc`**

**Explanation:**
A qdisc can queue and schedule outgoing packets and drop due to queue limits or active queue management. A rising `dropped` counter attributes drops to that qdisc, not every loss on the path. Correlate the affected interval and traffic with interface, driver, stack, and remote evidence. `overlimits` can reflect shaping without a drop; it is not interchangeable with `dropped`.
</details>

2. Which XDP mode distinction matters when discussing early packet-drop performance?
   - A) It runs in hardware rather than as a kernel module
   - B) Native/driver XDP runs before skb allocation; generic XDP already uses skb
   - C) It is JIT-compiled
   - D) It does not need to consult conntrack

<details>

<summary>Show Answer</summary>

**Answer: B) Native/driver XDP runs before skb allocation; generic XDP already uses skb**

**Explanation:**
The early-drop advantage is mode-specific. BPF maps can maintain state, and performance depends on the kernel, program, driver and hardware rather than a universal fastest-path guarantee.
</details>

3. With heavy receive traffic, only one CPU is at 100% while the rest idle. Which possible cause and related mechanisms should you investigate?
   - A) Insufficient qdisc queue — increase queue length
   - B) Concentrated receive processing — inspect RSS queue/IRQ distribution, RPS software steering, and RFS cache locality
   - C) Insufficient socket buffer — raise `tcp_rmem`
   - D) A TCP congestion control mismatch — switch to bbr

<details>

<summary>Show Answer</summary>

**Answer: B) Concentrated receive processing — inspect RSS queue/IRQ distribution, RPS software steering, and RFS cache locality**

**Explanation:**
RSS hashes flows to receive queues; IRQ affinity influences which CPUs handle them. RPS steers later receive processing in software, and RFS aims to place it near the consuming application. They do not all move hardware interrupts, and a single flow can remain on one queue. Inspect `/proc/interrupts` and per-CPU `%soft` in `mpstat -P ALL`, along with application CPU use, before assigning a cause.
</details>

4. How can ordinary interrupt-driven NAPI reduce per-packet overhead?
   - A) The kernel automatically raises CPU frequency
   - B) The driver masks the relevant queue interrupt and schedules bounded polling, amortizing work across a batch
   - C) It compresses packets before processing
   - D) GRO is enabled automatically

<details>

<summary>Show Answer</summary>

**Answer: B) The driver masks the relevant queue interrupt and schedules bounded polling, amortizing work across a batch**

**Explanation:**
Batching can amortize interrupt and processing overhead. The driver masks the relevant interrupt while polling is scheduled and can unmask it when polling completes; it does not turn off all CPU interrupts. Polling has a work budget, and overload can still increase latency or drops. Busy polling and threaded NAPI use other execution arrangements.
</details>

5. Why did same-node Pod-to-Pod traffic reach 29.97 Gbps on a single flow with CPU as the bottleneck?
   - A) There is a dedicated high-speed network inside the node
   - B) In the illustrated ordinary veth/routed same-node path, packets can stay in kernel memory without traversing the physical NIC
   - C) The kernel compresses the packets
   - D) Same-node traffic does not use TCP

<details>

<summary>Show Answer</summary>

**Answer: B) In the illustrated ordinary veth/routed same-node path, packets can stay in kernel memory without traversing the physical NIC**

**Explanation:**
Virtual devices still have driver processing. Different CNIs, SR-IOV, overlays or service/policy detours can change the path, so tie the claim to the actual configuration.
</details>

6. Small handshake packets pass, but larger IPv4 packets with DF set are dropped at a lower-MTU hop and the returning ICMP is blocked. Which mechanism explains the stall?
   - A) conntrack exhaustion
   - B) PMTUD failure — the ICMP that reports path MTU is blocked, so only large packets are dropped
   - C) A TCP congestion control mismatch
   - D) Insufficient socket receive buffer

<details>

<summary>Show Answer</summary>

**Answer: B) PMTUD failure — the ICMP that reports path MTU is blocked, so only large packets are dropped**

**Explanation:**
With DF set, an IPv4 router cannot fragment the oversized packet and normally returns ICMP "fragmentation needed." Blocking that feedback can break PMTUD and create a black hole. IPv6 routers do not fragment and use ICMPv6 "Packet Too Big." Without the evidence given in the question, a working handshake followed by a stall is only a clue, not proof; probing may also allow recovery.
</details>

7. What is the recommended order for diagnosing a network problem?
   - A) Top to bottom — from the application down to the NIC in order
   - B) Start with drop counters — `insert_failed` in `conntrack -S`, `dropped` in `tc -s qdisc`, NIC drops in `ethtool -S`
   - C) Always capture packets with `tcpdump` first
   - D) Start with CPU utilization

<details>

<summary>Show Answer</summary>

**Answer: B) Start with drop counters — `insert_failed` in `conntrack -S`, `dropped` in `tc -s qdisc`, NIC drops in `ethtool -S`**

**Explanation:**
These counters identify candidates to investigate, not a complete diagnosis. Correlate changes with the affected flow and time window; for conntrack, also inspect count/max and kernel logs because `insert_failed` is not unique to exhaustion. Aggregate counters can include unrelated traffic. Unchanged local counters do not exclude remote drops, authentication or application failures. Follow the symptom with checks such as RTT and cwnd in `ss -tin`, returned errors and evidence from the rest of the path.
</details>

8. Which comparison of `cubic` and `bbr` is justified without a workload benchmark?
   - A) cubic is for UDP and bbr is for TCP
   - B) cubic adjusts a congestion window following events such as loss/ECN; bbr uses delivery-rate and RTT estimates, with results depending on implementation and path
   - C) bbr is always faster than cubic
   - D) cubic was removed in kernel 6.x

<details>

<summary>Show Answer</summary>

**Answer: B) cubic adjusts a congestion window following events such as loss/ECN; bbr uses delivery-rate and RTT estimates, with results depending on implementation and path**

**Explanation:**
The models explain different control behavior, not a guaranteed performance ranking. BBR still has loss/recovery behavior, and neither algorithm removes receive-window or application limits. Identify the kernel implementation, active algorithm, RTT/cwnd, workload, and path before interpreting a comparison.
</details>

9. A process uses both `write(fd, ...)` and `send(fd, ...)` on a TCP socket. Which description matches Linux's socket/VFS bridge?
   - A) Both calls must reach a disk filesystem before entering TCP
   - B) `send()` always calls `vfs_write()` and the socket is a disk file
   - C) The FD references a `struct file` linked to a socket; `write()` uses VFS socket file operations, while `send()` uses a socket-specific entry path
   - D) A socket has no file descriptor table entry

<details>

<summary>Show Answer</summary>

**Answer: C) The FD references a `struct file` linked to a socket; `write()` uses VFS socket file operations, while `send()` uses a socket-specific entry path**

**Explanation:**
In the versioned Linux example, `file->private_data` links to `struct socket`. VFS `write()` dispatches through `socket_file_ops.write_iter` to `sock_write_iter`; `send()` resolves the socket from the FD through its own syscall path. Both reach socket/protocol operations. Sharing the file abstraction does not imply disk I/O, and successful sending does not prove consumption by the peer application. Review the [VFS bridge](../../kernel/02-network-stack.md#socket-vfs-bridge).
</details>

10. An established TCP connection has unread payload, and `ss -m` shows more receive memory than `Recv-Q`. Which explanation is valid?
   - A) Memory accounting includes allocation overhead and potentially out-of-order data; `Recv-Q` counts unread in-order stream bytes
   - B) Each `sk_buff` is the entire socket receive buffer
   - C) Receive memory, `Recv-Q`, `rwnd`, and `cwnd` are always equal
   - D) Every skb must represent exactly one wire packet

<details>

<summary>Show Answer</summary>

**Answer: A) Memory accounting includes allocation overhead and potentially out-of-order data; `Recv-Q` counts unread in-order stream bytes**

**Explanation:**
An skb describes packet data and metadata; it can refer to fragments, be cloned, or represent coalesced/segmented data. Socket memory budgets, application payload, the receiver's advertised window, and the sender's congestion window describe different limits or quantities. An `ss -m` memory value cannot be substituted for `rwnd`, nor does increasing a local buffer directly increase `cwnd`. Review [queue observations](../../kernel/02-network-stack.md#ss-tcp-queues).
</details>

11. `ss` shows `Recv-Q=3, Send-Q=128` for `LISTEN`, and `Recv-Q=4096, Send-Q=8192` for `ESTABLISHED`. What do these values mean?
   - A) Both rows count packets currently in the NIC ring
   - B) The listener has received 3 bytes and sent 128 bytes
   - C) The listener has 3 incomplete SYNs, and all 8192 established bytes are known to be on the wire
   - D) The listener has 3 connections awaiting accept and a maximum backlog of 128; the established socket has 4096 unread in-order bytes and 8192 written bytes not yet cumulatively acknowledged

<details>

<summary>Show Answer</summary>

**Answer: D) The listener has 3 connections awaiting accept and a maximum backlog of 128; the established socket has 4096 unread in-order bytes and 8192 written bytes not yet cumulatively acknowledged**

**Explanation:**
For a listener the columns count connections and do not report SYN-queue occupancy. For established TCP they count stream bytes; `Send-Q` can include both unsent and sent/unacknowledged bytes. These are neither configured socket memory budgets nor proof of packet loss. Review [state-dependent TCP queues](../../kernel/02-network-stack.md#ss-tcp-queues).
</details>

12. An application explicitly sets `SO_RCVBUF` and `SO_SNDBUF`. An operator later raises only `tcp_rmem[2]` and `tcp_wmem[2]`. Which expectation is correct?
   - A) All existing sockets immediately allocate both new maxima
   - B) The explicit socket settings remain locked against normal automatic adjustment in their respective directions
   - C) Linux doubles `tcp_rmem[2]` and advertises it directly as `rwnd`
   - D) Changing the send-buffer policy directly enlarges the peer's receive window

<details>

<summary>Show Answer</summary>

**Answer: B) The explicit socket settings remain locked against normal automatic adjustment in their respective directions**

**Explanation:**
The socket options set `SOCK_RCVBUF_LOCK` and `SOCK_SNDBUF_LOCK`; they are policy flags, not mutexes. Ordinary option requests are subject to `net.core.rmem_max`/`wmem_max`. Linux normally doubles the accepted request for bookkeeping and reports that value through `getsockopt()`, but this does not mean the memory is all allocated or usable as payload. Sysctl automatic-sizing maxima and explicit option limits are different controls. Review [TCP buffer policy](../../kernel/02-network-stack.md#tcp-buffer-policy).
</details>

13. A hypothetical path offers 1 Gbit/s at 40 ms RTT. Which BDP calculation and conclusion are sound?
   - A) 40 MB; set every socket's send buffer to this exact value
   - B) 5 bytes; latency in milliseconds can be multiplied directly by bits per second
   - C) 5,000,000 bytes (about 4.77 MiB); compare this scale with byte-normalized windows, application progress, and memory overhead
   - D) 5 MB; therefore every host has a proven buffer bottleneck

<details>

<summary>Show Answer</summary>

**Answer: C) 5,000,000 bytes (about 4.77 MiB); compare this scale with byte-normalized windows, application progress, and memory overhead**

**Explanation:**
`1,000,000,000 bit/s × 0.040 s ÷ 8 bit/byte = 5,000,000 bytes`. This uses RTT and estimates payload in flight under an idealized steady-state model. `ss` normally reports `cwnd` in segments, so use MSS to compare byte quantities. Receive-window constraints, pacing, loss, CPU, and application behavior still matter; BDP is not a universal tuning instruction. See [BDP reasoning](../../kernel/02-network-stack.md#tcp-bdp-reasoning) and the [TCP buffer lab](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab).
</details>

14. An interface has IP MTU 1500, but a host capture shows a TCP unit larger than 1500 bytes with an apparent bad transmit checksum. What should you conclude first?
   - A) Check the capture point and offloads; without options, IPv4 TCP payload fits within 1460 bytes, but host GSO/GRO units and unfinished checksums can differ from wire packets
   - B) TCP MSS must be 1500 bytes because it includes the IP header
   - C) The remote IPv6 router must have fragmented the packet
   - D) The capture proves on-wire corruption and invalidates PMTUD

<details>

<summary>Show Answer</summary>

**Answer: A) Check the capture point and offloads; without options, IPv4 TCP payload fits within 1460 bytes, but host GSO/GRO units and unfinished checksums can differ from wire packets**

**Explanation:**
MSS excludes IP/TCP headers, and PMTU depends on the complete path. With no options, `1500 - 20 - 20 = 1460` for IPv4; IPv6's base header leaves 1440. Offloads can defer segmentation/checksum completion or coalesce received packets. A host capture alone does not establish wire packet size or corruption. Continue to the [MTU/MSS lab](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab).
</details>
