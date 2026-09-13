# Kernel Networking Stack Quiz

This quiz tests your understanding of the packet path, hook points, and Pod-to-Pod routing.

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
A qdisc queues packets before handing them to the NIC and decides order and rate. When its queue fills, packets are discarded — and that is not a NIC or network problem but **a drop inside the node.** It is easy to waste time looking outside, believing "the network lost packets." The `dropped` counter in `tc -s qdisc show dev <iface>` is the evidence; also check transmit drops in `ip -s link`.
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

3. With heavy receive traffic, only one CPU is at 100% while the rest idle. What is the cause and at what layers is it solved?
   - A) Insufficient qdisc queue — increase queue length
   - B) Receive interrupts pinned to one CPU — distribute with RSS (hardware), RPS (software), RFS (cache locality)
   - C) Insufficient socket buffer — raise `tcp_rmem`
   - D) A TCP congestion control mismatch — switch to bbr

<details>

<summary>Show Answer</summary>

**Answer: B) Receive interrupts pinned to one CPU — distribute with RSS (hardware), RPS (software), RFS (cache locality)**

**Explanation:**
Receive interrupts are delivered to a specific CPU, so with a single queue or no distribution configured that core saturates while overall CPU utilization looks low and throughput plateaus. Three layers solve it — RSS has the NIC distribute across receive queues by hash, RPS has the kernel hand processing to another CPU, and RFS sends to the CPU where the reading process runs for better cache locality. Diagnose with the distribution in `/proc/interrupts` and `%soft` in `mpstat -P ALL`.
</details>

4. Why does NAPI become *more* efficient under higher load?
   - A) The kernel automatically raises CPU frequency
   - B) After the first interrupt it disables interrupts and switches to polling, harvesting in batches — larger batches mean lower per-packet overhead
   - C) It compresses packets before processing
   - D) GRO is enabled automatically

<details>

<summary>Show Answer</summary>

**Answer: B) After the first interrupt it disables interrupts and switches to polling, harvesting in batches — larger batches mean lower per-packet overhead**

**Explanation:**
Interrupting per packet leads under high load to livelock, where the system does nothing but handle interrupts. NAPI turns interrupts off on the first one and polls, harvesting many queued packets at once, re-enabling interrupts when the queue empties. Polling mode engages automatically under load, and because larger batches lower per-packet overhead, efficiency improves.
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

6. What is the classic cause of "the handshake works but data transfer stalls"?
   - A) conntrack exhaustion
   - B) PMTUD failure — the ICMP that reports path MTU is blocked, so only large packets are dropped
   - C) A TCP congestion control mismatch
   - D) Insufficient socket receive buffer

<details>

<summary>Show Answer</summary>

**Answer: B) PMTUD failure — the ICMP that reports path MTU is blocked, so only large packets are dropped**

**Explanation:**
Packets larger than the path's minimum MTU are fragmented or dropped. PMTUD reports path MTU via ICMP; if that ICMP is blocked, the sender keeps sending large packets, they get dropped mid-path, and the connection appears to hang. The symptom is distinctive because **small packets (the handshake) pass while only large packets drop.** Watch for this with jumbo frames or mixed-MTU paths.
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

8. What is the difference between `cubic` and `bbr`, and where does bbr help?
   - A) cubic is for UDP and bbr is for TCP
   - B) cubic treats packet loss as the congestion signal while bbr estimates bandwidth and RTT. bbr helps where loss occurs unrelated to congestion, or on long-delay paths
   - C) bbr is always faster than cubic
   - D) cubic was removed in kernel 6.x

<details>

<summary>Show Answer</summary>

**Answer: B) cubic treats packet loss as the congestion signal while bbr estimates bandwidth and RTT. bbr helps where loss occurs unrelated to congestion, or on long-delay paths**

**Explanation:**
cubic's premise is "loss = congestion," reasonable on wired paths but causing unnecessary backoff where loss has other causes (wireless, shallow-buffer paths). bbr judges from measured bandwidth and minimum RTT instead. Intra-VPC traffic is a high-quality path with rare loss, so cubic is usually fine; **bbr's advantage shows on long-delay, lossy paths like cross-region or internet transit.**
</details>
