# Pod Network Benchmark Quiz

These questions refer to the September 2, 2026 report, not universal performance or billing guarantees.

1. Measured with `ping -c 200 -i 0.05`, how did the average Pod-to-Pod RTT change from same node → different node in the same AZ → different AZ?
   - A) 0.040 ms → 0.544 ms → 0.339 ms — cross-AZ was faster than same-AZ
   - B) All three paths sat within noise of about 0.3 ms
   - C) In this run, 0.040 ms → 0.339 ms → 0.544 ms: about +0.30 ms and +0.21 ms between adjacent placements
   - D) 0.040 ms → 0.339 ms → 5.4 ms — the AZ boundary pushed RTT into whole milliseconds

<details>
<summary>Show Answer</summary>

**Answer: C) In this run, 0.040 ms → 0.339 ms → 0.544 ms: about +0.30 ms and +0.21 ms between adjacent placements**

**Explanation:**
The reported ping means used 200 probes per path with 0/200 loss. The cross-AZ minus same-AZ difference is 0.205 ms, rounded to 0.21 ms; cross-AZ minus same-node is 0.504 ms. HTTP p50 was 0.259 → 0.461 → 0.704 ms. Subtracting an HTTP median from a ping mean does not isolate user-space cost. The 5.4 ms figure belongs to loaded TCP RTT, whose queue location was not measured. The separate Istio report's +1.29 ms is a whole-scenario p50 difference on different hardware and workload, not a measured single-proxy cost that can be added to these values.

</details>

2. A single iperf3 TCP stream (`-P 1`) stopped at 4.96 Gbps on both the same-AZ and the cross-AZ path, and 8 streams (`-P 8`) reached 9.94 Gbps on both. What best explains the two numbers?
   - A) 4.96 Gbps is one client CPU core saturating; 8 streams are faster because they use more cores
   - B) The ordinary 5 Gbps single-flow limit is consistent with 4.96 Gbps; parallel flows approached this m5.xlarge's 10 Gbps burst peak
   - C) 4.96 Gbps is the m5.xlarge baseline bandwidth, and 8 streams spent burst credits to reach the peak
   - D) Jumbo frames (MTU 9001) were inactive for the single stream

<details>
<summary>Show Answer</summary>

**Answer: B) The ordinary 5 Gbps single-flow limit is consistent with 4.96 Gbps; parallel flows approached this m5.xlarge's 10 Gbps burst peak**

**Explanation:**
The m5.xlarge baseline is 1.25 Gbps and its best-effort burst peak is 10 Gbps; the 20 s runs do not prove sustained peak availability. The client process CPU was 19.5 % / 20.0 % on the inter-node paths, versus 99.8 % for the 29.97 Gbps same-node single-flow test. These values support a bandwidth-limit interpretation without ruling out every host bottleneck. Retransmits increased from 4 / 2 to 5,874 / 5,979; ENA counters were not collected, so shaping is not proven. AWS also documents up to 10 Gbps within a cluster placement group and up to 25 Gbps for eligible same-AZ ENA Express flows: 5 Gbps is not universal.

</details>

3. How can the reported fixed-pool HTTP throughput differ even though the two eight-flow iperf3 tests both reached 9.94 Gbps?
   - A) The inter-AZ link halves bandwidth for request/response traffic
   - B) Errors and retries increased on the cross-AZ path
   - C) The node hosting srv-b had a slower CPU than srv-a's node
   - D) A steady closed loop with about 16 in-flight requests is consistent with throughput ≈ 16 / mean latency; the observed rates differ by 33.5 %, without proving a universal AZ penalty

<details>
<summary>Show Answer</summary>

**Answer: D) A steady closed loop with about 16 in-flight requests is consistent with throughput ≈ 16 / mean latency; the observed rates differ by 33.5 %, without proving a universal AZ penalty**

**Explanation:**
The reported means were 0.355 / 0.415 / 0.624 ms. Dividing 16 by those durations gives 45,070 / 38,554 / 25,641 qps, near the reported 44,991 / 38,507 / 25,602. (38,507 − 25,602) / 38,507 ≈ 33.5 %. Little's law describes concurrency, throughput and mean time under the stated steady-state conditions; it does not identify the exclusive cause of delay. The report records zero errors and the same instance type for both servers, not evidence for options B or C. CPU contention could contribute to the worse same-node tail, but was not established by profiling.

</details>

4. At the same 100 qps / 4 connections, switching to `-keepalive=false` (a new TCP connection per request) changed the cross-AZ HTTP p50 how?
   - A) 0.704 ms → 1.517 ms (+0.813 ms), more than double; connection establishment adds work, but this experiment does not isolate each component
   - B) No change — the kernel reuses connections anyway
   - C) 0.704 ms → 0.813 ms, a small increase
   - D) p50 was unchanged; only p99 got worse

<details>
<summary>Show Answer</summary>

**Answer: A) 0.704 ms → 1.517 ms (+0.813 ms), more than double; connection establishment adds work, but this experiment does not isolate each component**

**Explanation:**
The keepalive-disabled medians were 0.664 / 1.079 / 1.517 ms, increases of 0.405 / 0.618 / 0.813 ms. The last number is an increase, not the new median, so C is wrong. Connection establishment contributes, but subtracting a ping RTT does not independently measure a fixed 0.3 ms socket cost. Connection reuse is worth testing with the application. TIME_WAIT was not measured and depends on the closing endpoint and connection termination behavior.

</details>

5. What does the report estimate for 223,376,179,200 payload bytes using its explicit decimal-GB conversion and $0.01/GB at each EC2 endpoint?
   - A) $0 — traffic inside a Region is free
   - B) $2.23 — $0.01 per GB, charged once
   - C) About $4.47 in the report's decimal-GB payload model, applying $0.01/GB at both the sending and receiving end; an actual invoice was not verified
   - D) Traffic up to the 1.25 Gbps baseline is free; only the burst above it is billed

<details>
<summary>Show Answer</summary>

**Answer: C) About $4.47 in the report's decimal-GB payload model, applying $0.01/GB at both the sending and receiving end; an actual invoice was not verified**

**Explanation:**
The exact payload was 223,376,179,200 bytes. The historical model divides by 10⁹ and multiplies by $0.01 twice, giving about $4.47; all three cross-AZ iperf3 runs total 260,633,264,128 bytes and about $5.21 under the same model. One payload direction can incur charges at both ends. Public `get-products` pricing is not an account's paid bill, and this audit did not prove that billed EC2 units equal decimal payload GB. Reconcile CUR metering units, protocol overhead, both endpoints and applicable discounts. The 18 intervals at 9.92–9.94 Gbps do not create a free baseline-transfer tier.

</details>

6. In the default `ndots:5` Pod (glibc 2.41), one cold resolution of `sts.ap-northeast-2.amazonaws.com` (3 dots) produced how many DNS queries and NXDOMAIN answers in tcpdump?
   - A) 2 queries, 0 NXDOMAIN — with 3 dots the name is queried as absolute straight away
   - B) In the recorded lookup, 10 queries and 8 NXDOMAIN: four failed search candidates each used A+AAAA, then the absolute name succeeded
   - C) 5 queries, 4 NXDOMAIN — one A query per candidate
   - D) 4 queries, 2 NXDOMAIN

<details>
<summary>Show Answer</summary>

**Answer: B) In the recorded lookup, 10 queries and 8 NXDOMAIN: four failed search candidates each used A+AAAA, then the absolute name succeeded**

**Explanation:**
This Pod had the recorded four-entry search list and glibc AF_UNSPEC behavior. Its first four candidates failed, producing eight NXDOMAINs, before A records 10.0.3.84 / 10.0.2.129 were returned for the absolute name. The 4.37 ms timeline ends at that A answer, not the whole first-process call; AAAA completion is not timed in the table. The reported warm medians were 3.78 ms versus 0.80 ms with a trailing dot. `cache 30` is a TTL maximum, not proof of no upstream queries. Under the same response pattern, 1,000 resolutions/s would mean 10,000 queries/s and 8,000 NXDOMAINs; that does not mean 80 % of CoreDNS CPU. Other names can succeed earlier, as `kubernetes.default` did with four queries.

</details>

7. In the same `ndots:5` Pod, the FQDN-looking `kubernetes.default.svc.cluster.local` (no trailing dot) also produced 10 queries and 8 NXDOMAINs. Why did it walk the whole search list?
   - A) CoreDNS's `kubernetes` plugin answers immediately only for names outside the `cluster.local` zone
   - B) glibc always treats names ending in `svc.cluster.local` as Service names
   - C) The `.ap-northeast-2.compute.internal` suffix is first in the search list and is tried first
   - D) Four dots are below ndots 5, so this resolver tried the search candidates first; they failed before the original name succeeded, while the trailing-dot lookup skipped expansion

<details>
<summary>Show Answer</summary>

**Answer: D) Four dots are below ndots 5, so this resolver tried the search candidates first; they failed before the original name succeeded, while the trailing-dot lookup skipped expansion**

**Explanation:**
The resolver counts dots; it does not recognize a Kubernetes Service suffix as an instruction to bypass search. All four expanded candidates failed in this sample. The report gives 2.2 ms for the forwarded candidate, 5.6 ms for that wire walk, 3.63 ms warm median without the dot and 0.46 ms with it; the separately reported first-process call was 7.40 ms. A trailing dot makes a DNS name absolute, but putting it into an application URL also requires compatible Host/SNI, certificate and signing behavior. Do not assume it is safe for every HTTPS or AWS SDK endpoint configuration.

</details>

8. In the Pod configured with `dnsConfig.options` `ndots:1`, external names dropped from 10 to 2 queries, but the short in-cluster name `kubernetes.default` got worse (6 queries, 4 NXDOMAIN, median 2.04 ms vs 1.71 ms under ndots:5). What happened?
   - A) This resolver first tried the one-dot name as absolute under ndots:1, then fell back to the search list after NXDOMAIN, disclosing that internal-looking name upstream
   - B) ndots:1 disables the CoreDNS cache
   - C) `kubernetes.default` did not resolve at all under ndots:1
   - D) glibc sends A and AAAA sequentially, doubling the time

<details>
<summary>Show Answer</summary>

**Answer: A) This resolver first tried the one-dot name as absolute under ndots:1, then fell back to the search list after NXDOMAIN, disclosing that internal-looking name upstream**

**Explanation:**
The observed order was `kubernetes.default.` (forwarded, NXDOMAIN after a reported 1.6 ms), then `kubernetes.default.bench-net.svc.cluster.local` (NXDOMAIN), then `kubernetes.default.svc.cluster.local` (172.20.0.1). That gives six queries / four NXDOMAIN versus four / two under ndots:5. `ndots` changes the client's ordering, not whether CoreDNS caching is enabled. This glibc lookup used A/AAAA pairs, but address-family and resolver options can alter that behavior. Full Service names reduce failed absolute attempts under ndots:1. A trailing dot bypasses search, without promising a particular query count or latency for all resolvers and failures.

</details>

9. Which interpretation of the reported Fortio rerun with `-r 0.00001` is correct?
   - A) The first run had a high error rate
   - B) The default 1 ms lowest-bucket resolution was too coarse for the desired comparison; the report reran with 10 µs resolution, but a single bucket does not universally imply p50 = 0.5 ms
   - C) At the default resolution fortio does not compute p99.9
   - D) The first run had accidentally been made without keepalive

<details>
<summary>Show Answer</summary>

**Answer: B) The default 1 ms lowest-bucket resolution was too coarse for the desired comparison; the report reran with 10 µs resolution, but a single bucket does not universally imply p50 = 0.5 ms**

**Explanation:**
In Fortio 1.69.5, `-r` is in seconds: 0.001 is 1 ms and 0.00001 is 10 µs at the smallest buckets. Larger histogram buckets can widen. Percentiles are interpolated within bucket bounds, with the observed minimum and maximum affecting the first and last buckets. Therefore the original claim “all sub-ms responses imply p50 = 0.5 ms” was wrong. The keepalive medians 0.259–0.704 ms are sub-ms, but some tails and new-connection medians exceed 1 ms. Preserve the report's rerun history, averages, full histograms and error counts rather than labelling interpolation intrinsically meaningless.

</details>

10. Why did the historical application benchmark omit a Service/traffic-distribution comparison?
   - A) fortio cannot target a Service DNS name
   - B) kube-proxy was in IPVS mode, so there was no iptables hop to measure
   - C) According to the report, a failed LBC admission webhook rejected the benchmark's Service creation requests; the application tests used Pod IPs without bypassing it
   - D) It was measured but left out of the tables because it matched the Pod-IP numbers

<details>
<summary>Show Answer</summary>

**Answer: C) According to the report, a failed LBC admission webhook rejected the benchmark's Service creation requests; the application tests used Pod IPs without bypassing it**

**Explanation:**
The historical diagnosis reports LBC v3.2.1, two replicas, 48 days of CrashLoopBackOff, 9,250 restarts and `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"`, followed by cache-sync timeout after about 2m18s. These are attributed incident details; this audit did not independently recover the raw logs or inspect a live cluster. A failing `failurePolicy: Fail` webhook rejects requests matching its rules, selectors and conditions; `namespaceSelector: {}` alone does not prove every Service CREATE is intercepted. The application benchmark omitted Services, while DNS used pre-existing `kube-dns`. `PreferClose` is now the deprecated alias of `PreferSameZone`; neither was tested here. ENA counters and independent repetitions were also absent.

</details>

---

[Return to Learning Materials](../../networking/06-pod-network-benchmark.md) | [Back to Networking Home](../../networking/README.md)
