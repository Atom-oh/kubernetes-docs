# Linux Network Performance Quiz

> **Last Updated**: September 15, 2026

Read [Linux Network Performance](../../../networking/expert/04-linux-performance.md) first.
Choose one best answer. Explain both the interpretation and its measurement limits.

1. Which statement correctly maps Bootlin's public materials to this workbook?
   - A) Downloadable slides guarantee a free supported hardware lab.
   - B) The beginner VM necessarily reproduces every board/driver observation.
   - C) Public slides/labs support study; hardware exercises require their documented board/toolchain and C/kernel background.
   - D) A training certificate substitutes for a missing capture.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Public reading access differs from instruction, hardware and enrollment. Driver labs need low-level knowledge and an appropriate setup. The core Python loopback exercise has a smaller prerequisite set and cannot prove physical NIC behavior. Mark unavailable hardware evidence explicitly instead of replacing it with a certificate.

</details>

2. The client intentionally waits 0.15 seconds after parsing headers. Its total transaction duration grows. Which conclusion is justified?
   - A) The network RTT increased by exactly 150 ms.
   - B) Client consumption delay contributes to completion time; path delay needs separate evidence.
   - C) A qdisc must have dropped packets.
   - D) A larger receive buffer will remove the intentional pause.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The configured pause is part of `read_ms` and `total_ms`, not an injected network delay. Scheduling and buffering affect actual measurements. `headers_ms` also includes connection/request work and is not pure RTT. The experiment tests a competing application explanation without claiming a particular measured duration.

</details>

3. Which interpretation of `ss` is appropriate?
   - A) LISTEN `Recv-Q` always counts unread application payload bytes.
   - B) ESTABLISHED `Send-Q` is the configured send-buffer maximum.
   - C) ESTABLISHED `Recv-Q` concerns unread received data; socket memory and LISTEN backlog are different quantities.
   - D) `skmem`, advertised receive window and `cwnd` must all be numerically equal.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Socket state changes the columns' meaning. ESTABLISHED `Send-Q` concerns unacknowledged bytes, including unsent bytes, while LISTEN columns concern connection acceptance. Memory accounting includes overhead and differs from stream occupancy. Comparing these with `cwnd` also requires checking its segment units and MSS.

</details>

4. A hypothetical path carries 100 Mbit/s with 40 ms RTT. What is its BDP, and what does it establish?
   - A) 4,000,000 bytes, proving that all socket buffers should be set to that number.
   - B) 500,000 bytes, a reasoning input that does not establish the cause of a slow run.
   - C) 500 bytes, a measured loopback capacity.
   - D) 2,500,000 bytes, a mandatory qdisc queue length.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Convert RTT to 0.040 seconds and bits to bytes: `100,000,000 × 0.040 ÷ 8 = 500,000`. This is hypothetical arithmetic. Throughput depends on effective windows, application supply, congestion and other constraints; the calculation alone neither diagnoses the bottleneck nor authorizes global tuning.

</details>

5. A host capture shows a large TCP unit and apparent outgoing checksum errors. What should you do first?
   - A) Disable every NIC offload and repeat at unlimited load.
   - B) Declare that the physical network transmitted corrupt oversized frames.
   - C) Record capture location, direction, offload context and truncation/capture counters.
   - D) Delete the capture because it cannot contain useful evidence.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** GSO/TSO/GRO and checksum offload can change what a host observer sees relative to physical transmission. This does not prove the network is healthy either. Establish the observation point and seek corresponding endpoint/wire evidence where needed. The workbook does not change NIC offloads to normalize appearances.

</details>

6. Which combination is accurate?
   - A) NAPI is a promise that every application meets a latency target.
   - B) RSS always spreads one TCP flow across all CPUs.
   - C) RSS is hardware receive-queue steering, RPS is software CPU steering, and NAPI handles polling of driver events.
   - D) Loopback can directly benchmark the physical NIC's RSS indirection table.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** These mechanisms operate at related but different places. A flow may hash to one RSS queue; software processing can have a different CPU distribution. NAPI processing budgets and context do not guarantee application completion time. Loopback does not traverse physical NIC receive queues.

</details>

7. tcpdump reports capture drops, and an `ss` sample shows retransmissions. What can be concluded?
   - A) Every retransmission was caused by tcpdump losing a packet.
   - B) The qdisc is proven to be the loss location.
   - C) Observer loss and TCP retransmission are distinct signals that need time/flow correlation and further evidence.
   - D) The remote endpoint must have exhausted its receive buffer.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Capture drops describe the observer's delivery/processing limit, not directly the path's packet delivery. TCP may retransmit after loss, reordering or spurious timeout behavior. Neither counter alone identifies a failed component. Compare the same interval/tuple and use both endpoints when the hypothesis requires it.

</details>

8. `bpftool net show` reports an attachment. What additional evidence is needed to claim it accelerated your flow?
   - A) None; attachment implies acceleration.
   - B) Flow/hook correlation, a defined comparison, actual performance measurements and observer-overhead accounting.
   - C) Only the BPF program's name.
   - D) A failed permission check on another host.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Inventory is not execution or performance evidence. Native XDP, generic XDP and TC have different locations. A valid comparison needs a declared workload and measurement contract; trace loss/overhead also matters. Missing permissions mean unobserved, not no BPF. The core workbook loads no programs.

</details>

9. Five requests in a phase succeed, but most periodic `ss` samples are empty. Which report is sound?
   - A) A proven production p99 plus a claim that no sockets existed.
   - B) Actual sample count/minimum/median/maximum, with brief-connection sampling gaps stated.
   - C) Zero latency for every missing socket sample.
   - D) NIC maximum throughput calculated from the largest echo body alone.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Short connections can fit between observation intervals. Five transaction samples support only a small descriptive report, not a credible tail-latency service objective. Missing data is not zero. Payload divided by transaction time is operation-level goodput, including application and connection work, not NIC line rate.

</details>

10. Which restoration plan meets the workbook's requirements?
   - A) Replace the host root qdisc, then delete it and assume its previous hierarchy returns.
   - B) Flush all routes and kill all Python processes.
   - C) Stop only the owned loopback processes and verify listener removal; keep netem design-only until separate ownership, pre-state and exact restoration are defined.
   - D) Disable shared safety controls when an observation is missing.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The core run changes no global network configuration. Its recovery is scoped to its own processes and files; TIME_WAIT may remain normally. Deleting a qdisc does not reconstruct arbitrary prior configuration. A future netem experiment needs its own namespace/VM boundary and exact restoration or disposal of only recorded resources.

</details>

Return to the [workbook completion criteria](../../../networking/expert/04-linux-performance.md#completion) or the [expert course map](../../../networking/expert/README.md).
