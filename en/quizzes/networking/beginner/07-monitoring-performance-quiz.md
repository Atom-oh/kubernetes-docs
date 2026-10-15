# Monitoring and Performance Quiz

[Lesson](../../../networking/beginner/07-monitoring-performance.md)

Six questions. Explain each answer in your own words.

1. A LISTEN socket shows Recv-Q 3 and Send-Q 128. What does this mean?

   - A) 3 body bytes received and 128 body bytes sent
   - B) 3 connections awaiting accept; maximum accept backlog 128
   - C) 3 retransmissions and 128ms RTT
   - D) 128 connections currently exist

<details>
<summary>Show Answer</summary>

**Answer: B) 3 connections awaiting accept; maximum accept backlog 128**

**Explanation:** LISTEN queues count connections. Their units differ from stream bytes on ESTABLISHED sockets, so read the state first.

</details>

2. An IP-address curl request has a very small time_namelookup. What can you conclude?

   - A) Organizational DNS is always fast
   - B) Every DNS cache is empty
   - C) This request is unsuitable for validating DNS performance
   - D) Server processing took zero time

<details>
<summary>Show Answer</summary>

**Answer: C) This request is unsuitable for validating DNS performance**

**Explanation:** An IP literal does not test lookup of a service name. Also avoid adding cumulative timing fields as independent intervals.

</details>

3. curl succeeds but tcpdump captures nothing. What should you check first?

   - A) Selected NIC, filter and capture time window
   - B) Reset every host routing table
   - C) Enable SSH password login
   - D) Increase maximum TCP buffers

<details>
<summary>Show Answer</summary>

**Answer: A) Selected NIC, filter and capture time window**

**Explanation:** A capture depends on observation location and conditions. Align request and capture times and verify the lab NIC selection.

</details>

4. How do 100 Mbit/s and 100 MB/s compare?

   - A) They are always equal
   - B) The Mbit/s value is eight times larger
   - C) They are equal only for HTTP
   - D) 100 MB/s represents a rate equivalent to 800 Mbit/s

<details>
<summary>Show Answer</summary>

**Answer: D) 100 MB/s represents a rate equivalent to 800 Mbit/s**

**Explanation:** One byte is eight bits. Comparing real application throughput also requires protocol overhead, observation points and execution conditions.

</details>

5. One Send-Q snapshot is greater than zero. What is the appropriate next action?

   - A) Confirm network loss
   - B) Double every buffer sysctl
   - C) Correlate state, time changes, application progress and packets
   - D) Disable the remote firewall

<details>
<summary>Show Answer</summary>

**Answer: C) Correlate state, time changes, application progress and packets**

**Explanation:** Send-Q can include both unacknowledged and unsent bytes. A single snapshot does not establish the cause.

</details>

6. Which distinction between a block I/O scheduler and a network qdisc is correct?

   - A) They handle storage requests and network transmit queues respectively
   - B) Both are DNS caches
   - C) Both validate SSH keys
   - D) Both use the same single sysctl

<details>
<summary>Show Answer</summary>

**Answer: A) They handle storage requests and network transmit queues respectively**

**Explanation:** Locate the bottleneck first. Sharing a scheduling concept does not mean they control the same resources or have the same tuning effects.

</details>
