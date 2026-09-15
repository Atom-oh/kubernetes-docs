# Protocol Projects Quiz

> **Last Updated**: September 15, 2026

Read [Protocol Projects](../../../networking/expert/01-protocol-projects.md) first.
Choose one best answer per question, then explain what additional evidence would change your conclusion.

1. Which study plan accurately reflects the September 15, 2026 availability check?
   - A) Treat the unfinished Fall 2026 CS168 site as a complete, fixed assignment schedule.
   - B) Use the official Summer 2026 archive, record its term, and check separate access requirements for assignments.
   - C) Require a freely available current CS144 grader to finish this workbook.
   - D) Replace the guest's Python with Python 3.7 for every exercise.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** The Summer archive is accessible, while the Fall site is under construction. A public specification does not promise institutional grading access. CS144 is optional and its historical entry returned 404. Archived Python testing notes belong to that assignment's environment, not the workbook's Python 3.9+ guest.

</details>

2. A UDP probe uses `192.0.2.10:41000 → 198.51.100.20:33452`. An ICMP Time Exceeded reply quotes destination `198.51.100.99` with the same ports. What should the ledger do?
   - A) Match it because both ports agree.
   - B) Match it if the outer router address looks plausible.
   - C) Mark it unrelated to this probe and preserve the differing destination.
   - D) Rewrite the send ledger to match the response.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Correlation uses the quoted original packet, including its addresses and protocol. Matching ports cannot overcome a different destination. The outer source identifies the error sender, not the original probe. Keep the record as evidence without allowing it to satisfy the expected response.

</details>

3. No reply matches the TTL-2 probe, but a TTL-3 UDP probe has a correlated destination Port Unreachable. What follows?
   - A) The second router drops all application traffic.
   - B) The destination arrival is supported for the TTL-3 probe; TTL-2 remains unobserved.
   - C) The missing router has zero RTT.
   - D) Duplicate TTL-1 responses can fill the missing hop.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** A missing reply within a deadline is an observation limit. Filtering, response rate limits or return-path behavior can hide an intermediate response. Later destination evidence does not identify that intermediate router or prove a fixed application path. Duplicate replies remain duplicates.

</details>

4. Your two-byte-length framing protocol receives the same complete bytes in four different `recv()` partitions. Which result is required?
   - A) One application record per `recv()`.
   - B) The same logical records for every complete partition.
   - C) A split length field must end the connection immediately.
   - D) EOF in a partial body completes that body.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** TCP exposes a byte stream rather than message boundaries. The parser must retain partial headers/bodies and emit complete records consistently. EOF during a body is a truncation failure, and a length above the chosen cap is rejected before unbounded allocation. These are properties of the original exercise protocol, not a university project solution.

</details>

5. A sender has a large advertised receive window but a small congestion window. Why might it send slowly?
   - A) The receiver's available capacity removes all sender limits.
   - B) Congestion control can limit in-flight data independently of receiver flow control.
   - C) The receive window and congestion window are two names for one field.
   - D) CS168 Project 3 implements every congestion controller needed to decide this.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** Receiver flow control protects the receiving side; congestion control constrains load on the path. Outstanding bytes, pacing and available application data also matter. CS168's archived Project 3 explicitly excludes congestion control, so its completion cannot validate a production controller.

</details>

6. A captured connection has a SYN with sequence number 1000 and then six payload bytes starting at 1001. With no gaps, what next-byte ACK corresponds to receiving that payload?
   - A) 1006
   - B) 1007
   - C) 1008 because the pure ACK consumes one position
   - D) The segment count determines the answer

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** SYN consumes one sequence position. The payload occupies positions 1001 through 1006, so the next expected byte is 1007. A pure ACK does not consume sequence space; FIN would consume one additional position if present. The count is based on stream bytes, not how capture software groups packets.

</details>

7. `curl` without `--fail` exits successfully and displays HTTP 404 from `/missing`. What has been shown?
   - A) No HTTP server was reached.
   - B) The requested resource exists.
   - C) HTTP communication completed with an unsuccessful resource lookup.
   - D) The TCP checksum must be wrong.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Transport/tool success and application status are separate. The negative route is an intentional application failure delivered over a working HTTP connection. Inspect status and body instead of treating exit code zero as success of the requested operation. Adding `--fail` changes curl's handling of HTTP error statuses, not the server's result.

</details>

8. Which evidence best supports an HTTP/3 claim?
   - A) An arbitrary UDP packet addressed to port 443.
   - B) A command line containing `--http3`, regardless of fallback or tool support.
   - C) Endpoint evidence of QUIC and negotiated HTTP/3, with client capability recorded.
   - D) HTTP/1.1 output from the loopback lesson server.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** Port numbers and requested modes do not prove the negotiated protocol. `--http3` can fall back; `--http3-only` has different behavior and also needs a capable build. QUIC carries streams above UDP, while HTTP/3 maps HTTP onto those streams. Shared congestion control remains, even though independent streams avoid TCP's cross-stream delivery blocking.

</details>

9. What changes when extending the ICMP ledger to IPv6?
   - A) Rename TTL only; every header offset and ICMP type remains identical.
   - B) Use Hop Limit, account for IPv6 extension headers and ICMPv6 types, and record family/scope.
   - C) Expect routers to fragment forwarded IPv6 packets.
   - D) Treat an AAAA answer as proof that the guest has an IPv6 route.

<details>
<summary>Show Answer</summary>

**Answer: B**

**Explanation:** IPv6 parsing and ICMPv6 error types differ. Routers do not fragment forwarded packets; Packet Too Big supports a different diagnosis from Time Exceeded. AAAA data establishes a naming result, not usable routing. IPv6 neighbor discovery also differs from ARP.

</details>

10. Your capture reaches its 20-second deadline before connection closure appears. What is the correct completion record?
   - A) Declare that the server cannot close connections.
   - B) Hide timeout status and infer missing FIN packets.
   - C) Record the timer outcome and partial coverage, stop your helper, and check the listener.
   - D) Stop every process using TCP and capture again without a limit.

<details>
<summary>Show Answer</summary>

**Answer: C**

**Explanation:** The capture deadline is a collection boundary. Preserve its exit status and capture counters, and mark closure unobserved rather than failed. Stop only the owned foreground helper or let its timer expire, then verify the listener filter. A privilege-limited offline analysis must likewise remain labeled as such.

</details>

Return to the [workbook completion criteria](../../../networking/expert/01-protocol-projects.md#completion) or the [expert course map](../../../networking/expert/README.md).
