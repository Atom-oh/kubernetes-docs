# Pod Network Benchmark Quiz

1. Measured with `ping -c 200 -i 0.05`, how did the average Pod-to-Pod RTT change from same node → different node in the same AZ → different AZ?
   - A) 0.040 ms → 0.544 ms → 0.339 ms — cross-AZ was faster than same-AZ
   - B) All three paths sat within noise of about 0.3 ms
   - C) 0.040 ms → 0.339 ms → 0.544 ms — leaving the node adds +0.30 ms and leaving the AZ adds another +0.21 ms, a ladder
   - D) 0.040 ms → 0.339 ms → 5.4 ms — the AZ boundary pushed RTT into whole milliseconds
<details>
<summary>Show Answer</summary>

**Answer: C) 0.040 ms → 0.339 ms → 0.544 ms — leaving the node adds +0.30 ms and leaving the AZ adds another +0.21 ms, a ladder**

**Explanation:**
The ping averages (200 probes at 50 ms, 0/200 loss) were 0.040 ms same-node, 0.339 ms same-AZ and 0.544 ms cross-AZ. Same-AZ − same-node = +0.30 ms, cross-AZ − same-AZ = +0.21 ms, cross-AZ − same-node = +0.50 ms. fortio HTTP (100 qps, 4 connections, keepalive) p50 drew the same ladder at 0.259 → 0.461 → 0.704 ms (+0.20 / +0.24 ms), and HTTP p50 − ping average was about 0.22 / 0.12 / 0.16 ms per path — the client+server user-space stack. The 5.4 ms figure is the sender's TCP RTT during an iperf3 run that saturated a single flow (queueing in the shaper), not the idle cross-AZ RTT (D is wrong). For scale, this repo's Istio comparison page puts one sidecar hop at +1.29 ms p50 — a mesh hop costs more than an AZ hop.

</details>

2. A single iperf3 TCP stream (`-P 1`) stopped at 4.96 Gbps on both the same-AZ and the cross-AZ path, and 8 streams (`-P 8`) reached 9.94 Gbps on both. What best explains the two numbers?
   - A) 4.96 Gbps is one client CPU core saturating; 8 streams are faster because they use more cores
   - B) 4.96 Gbps is EC2's documented 5 Gbps single-flow limit (outside a cluster placement group) and 9.94 Gbps is the m5.xlarge "Up to 10 Gigabit" instance peak — to use the instance's bandwidth you must parallelise flows
   - C) 4.96 Gbps is the m5.xlarge baseline bandwidth, and 8 streams spent burst credits to reach the peak
   - D) Jumbo frames (MTU 9001) were inactive for the single stream
<details>
<summary>Show Answer</summary>

**Answer: B) 4.96 Gbps is EC2's documented 5 Gbps single-flow limit (outside a cluster placement group) and 9.94 Gbps is the m5.xlarge "Up to 10 Gigabit" instance peak — to use the instance's bandwidth you must parallelise flows**

**Explanation:**
A single flow between Pods on different nodes was identical on both paths — 4.96 Gbps same-AZ (cli→srv-a) and 4.96 Gbps cross-AZ (cli→srv-b) — which is the 5 Gbps single-flow limit AWS documents. iperf3 reported client CPU of only 19.5 % / 20.0 % (of one core) during those runs, so CPU was not the limit (A is wrong); the CPU-bound case is the same-node single stream at 29.97 Gbps with the client at 99.8 %. The m5.xlarge baseline is 1.25 Gbps and its peak 10 Gbps (C is wrong) — the 8-stream 9.94 Gbps is that peak. MSS 8949 (MTU 9001) applied equally to every run (D is wrong). With a single flow pinned at the cap, the sender's TCP RTT grew from an idle ping RTT of 0.34 ms (same-AZ) / 0.54 ms (cross-AZ) to 5.6 ms / 5.4 ms with a congestion window of about 4.3 MB, and retransmits went from 4 / 2 at one stream to 5,874 / 5,979 at eight streams once the instance ceiling was hit — the indirect signature of ENA allowance shaping (the counters themselves were not collected). In practice one gRPC stream or one Kafka replica fetch between Pods on different nodes can never exceed about 5 Gbps.

</details>

3. Eight-stream iperf3 bandwidth was an identical 9.94 Gbps for same-AZ and cross-AZ, yet fortio's closed-loop maximum (`-qps 0`, 16 connections, 20 s) fell from 38,507 qps same-AZ to 25,602 qps cross-AZ. Why?
   - A) The inter-AZ link halves bandwidth for request/response traffic
   - B) Errors and retries increased on the cross-AZ path
   - C) The node hosting srv-b had a slower CPU than srv-a's node
   - D) Little's law — with 16 connections fixed, throughput = concurrency ÷ latency, so 16 ÷ 0.000624 s ≈ 25,641 qps is the ceiling; the roughly +0.2 ms of latency the AZ hop adds cut throughput by 34 %. Cross-AZ costs latency, not bandwidth
<details>
<summary>Show Answer</summary>

**Answer: D) Little's law — with 16 connections fixed, throughput = concurrency ÷ latency, so 16 ÷ 0.000624 s ≈ 25,641 qps is the ceiling; the roughly +0.2 ms of latency the AZ hop adds cut throughput by 34 %. Cross-AZ costs latency, not bandwidth**

**Explanation:**
Closed-loop average latency was 0.355 ms same-node, 0.415 ms same-AZ and 0.624 ms cross-AZ, and Little's law holds on all three paths: 16 ÷ 0.000355 = 45,070 (measured 44,991), 16 ÷ 0.000415 = 38,554 (measured 38,507), 16 ÷ 0.000624 = 25,641 (measured 25,602). Every run had 0 errors (B is wrong) and the response body is about 75 bytes, so bandwidth is irrelevant (A is wrong) — the same 8-stream test showed the identical 9.94 Gbps on both paths. srv-a and srv-b run on the same m5.xlarge type (C is wrong). For a request/response service with a fixed connection pool, the AZ hop takes 34 % of throughput (38.5k → 25.6k qps), and the cause is latency. Note that same-node p99 1.695 ms / max 13.593 ms is worse than same-AZ (0.728 / 4.502 ms) because client and server share one node's 4 vCPUs — CPU contention at 45k qps, not the network.

</details>

4. At the same 100 qps / 4 connections, switching to `-keepalive=false` (a new TCP connection per request) changed the cross-AZ HTTP p50 how?
   - A) 0.704 ms → 1.517 ms (+0.813 ms), more than doubling — a new connection costs roughly one RTT for the TCP handshake plus about 0.3 ms of socket setup/teardown, so the longer the path's RTT the bigger the penalty
   - B) No change — the kernel reuses connections anyway
   - C) 0.704 ms → 0.813 ms, a small increase
   - D) p50 was unchanged; only p99 got worse
<details>
<summary>Show Answer</summary>

**Answer: A) 0.704 ms → 1.517 ms (+0.813 ms), more than doubling — a new connection costs roughly one RTT for the TCP handshake plus about 0.3 ms of socket setup/teardown, so the longer the path's RTT the bigger the penalty**

**Explanation:**
With keepalive=false (30 s, 3,000 requests) p50 was 0.664 ms same-node (+0.405), 1.079 ms same-AZ (+0.618) and 1.517 ms cross-AZ (+0.813): the extra cost grows with the path's RTT, and it amounts to roughly one RTT (the TCP handshake) plus about 0.3 ms of socket setup/teardown. Adding about 0.3 ms to the cross-AZ ping average of 0.544 ms lands roughly on the measured +0.813 ms. 0.813 ms is the increase, not the new p50 (C is wrong), and p50 itself more than doubled (D is wrong). For a service that crosses AZs, keeping a connection pool alive saves more latency than the AZ hop itself (+0.24 ms) costs.

</details>

5. The 180-second sustained run (4 streams) pushed 223.4 GB across the AZ boundary. Using the verified price (`APN2-DataTransfer-Regional-Bytes`), what did that single run cost?
   - A) $0 — traffic inside a Region is free
   - B) $2.23 — $0.01 per GB, charged once
   - C) About $4.47 — $0.01/GB is charged on both the sending AZ's "out" and the receiving AZ's "in", so $2.23 per direction, $4.47 total (effectively $0.02/GB)
   - D) Traffic up to the 1.25 Gbps baseline is free; only the burst above it is billed
<details>
<summary>Show Answer</summary>

**Answer: C) About $4.47 — $0.01/GB is charged on both the sending AZ's "out" and the receiving AZ's "in", so $2.23 per direction, $4.47 total (effectively $0.02/GB)**

**Explanation:**
`aws pricing get-products` returns usagetype `APN2-DataTransfer-Regional-Bytes` ("Regional Data Transfer - in/out/between AZs …") at $0.0100 per GB. Inter-AZ transfer is charged on data leaving each AZ, so even a one-way bulk transfer within one account pays $0.01/GB "out" in the sending AZ plus $0.01/GB "in" in the receiving AZ — effectively $0.02/GB. The run sent 223,376,179,200 bytes (223.4 GB at 9.93 Gbps) in 180 s, so 223.4 × $0.01 = $2.23 per direction, $4.47 total. All cross-AZ bytes in the throughput tests came to 12.41 + 24.85 + 223.38 = 260.6 GB, about $5.21. The 18 intervals of that run stayed flat at 9.92–9.94 Gbps with no step-down toward the 1.25 Gbps baseline, but the bill is per byte regardless of bandwidth tier (D is wrong).

</details>

6. In the default `ndots:5` Pod (glibc 2.41), one cold resolution of `sts.ap-northeast-2.amazonaws.com` (3 dots) produced how many DNS queries and NXDOMAIN answers in tcpdump?
   - A) 2 queries, 0 NXDOMAIN — with 3 dots the name is queried as absolute straight away
   - B) 10 queries, 8 NXDOMAIN — A+AAAA for each of the 4 search-list candidates returns 8 NXDOMAINs before the 5th candidate (the absolute name) gets an A answer
   - C) 5 queries, 4 NXDOMAIN — one A query per candidate
   - D) 4 queries, 2 NXDOMAIN
<details>
<summary>Show Answer</summary>

**Answer: B) 10 queries, 8 NXDOMAIN — A+AAAA for each of the 4 search-list candidates returns 8 NXDOMAINs before the 5th candidate (the absolute name) gets an A answer**

**Explanation:**
An EKS Pod's resolv.conf reads `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` with `options ndots:5`. A name with fewer than 5 dots is tried with each of the 4 search suffixes first, and glibc sends A and AAAA in parallel for every candidate (C is wrong). The capture shows `….bench-net.svc.cluster.local.` → `….svc.cluster.local.` → `….cluster.local.` (all three authoritative NXDomain from the CoreDNS kubernetes plugin) → `….ap-northeast-2.compute.internal.` (forwarded to the VPC resolver, NXDomain) → finally `sts.ap-northeast-2.amazonaws.com.` answered with A 10.0.3.84 / 10.0.2.129: 10 queries, 8 NXDOMAIN, 5 sequential round trips, 4.37 ms from the first packet, with the useful answer arriving in the last 0.38 ms. The warm median over 20 repeats was still 3.78 ms, whereas the trailing-dot form `sts.ap-northeast-2.amazonaws.com.` took 2 queries and a 0.80 ms median. CoreDNS `cache 30` caches the NXDOMAINs too, so the warm cost is the 5 sequential Pod↔CoreDNS round trips themselves, not upstream lookups. Derived arithmetic: an application resolving one external name per request at 1,000 resolutions/s cluster-wide sends CoreDNS 10,000 queries/s instead of 2,000, 8,000 of them answered NXDOMAIN. 4 queries / 2 NXDOMAIN is the result for `kubernetes.default` (1 dot), not this name (D is wrong).

</details>

7. In the same `ndots:5` Pod, the FQDN-looking `kubernetes.default.svc.cluster.local` (no trailing dot) also produced 10 queries and 8 NXDOMAINs. Why did it walk the whole search list?
   - A) CoreDNS's `kubernetes` plugin answers immediately only for names outside the `cluster.local` zone
   - B) glibc always treats names ending in `svc.cluster.local` as Service names
   - C) The `.ap-northeast-2.compute.internal` suffix is first in the search list and is tried first
   - D) The name has only 4 dots, fewer than ndots 5, so to glibc it is a "short" name: all 4 search suffixes are appended and tried before the name is sent as-is — a trailing dot makes it 2 queries
<details>
<summary>Show Answer</summary>

**Answer: D) The name has only 4 dots, fewer than ndots 5, so to glibc it is a "short" name: all 4 search suffixes are appended and tried before the name is sent as-is — a trailing dot makes it 2 queries**

**Explanation:**
`kubernetes.default.svc.cluster.local` contains 4 dots, below ndots 5. glibc therefore tries `….bench-net.svc.cluster.local`, `….svc.cluster.local`, `….cluster.local` and `….ap-northeast-2.compute.internal` first, collecting 8 NXDOMAINs (the compute.internal candidate alone took 2.2 ms because CoreDNS forwarded it upstream), and only the fifth candidate — the original name — gets the A answer: 5.6 ms for the cold walk, 3.63 ms warm median. The same name with one trailing dot, `kubernetes.default.svc.cluster.local.`, is 2 queries and 0 NXDOMAIN — 0.4–0.5 ms cold, 0.46 ms warm median. In the `ndots:1` Pod the dotless form was also 2 queries (0.97 ms median). The search list runs namespace domain → `svc.cluster.local` → `cluster.local` → node domain, so C is wrong, and A and B do not describe how glibc or CoreDNS behave. When a Service FQDN goes into a config file, writing the trailing dot is the safe choice.

</details>

8. In the Pod configured with `dnsConfig.options` `ndots:1`, external names dropped from 10 to 2 queries, but the short in-cluster name `kubernetes.default` got worse (6 queries, 4 NXDOMAIN, median 2.04 ms vs 1.71 ms under ndots:5). What happened?
   - A) With 1 dot ≥ ndots 1, glibc first sent `kubernetes.default.` as an absolute name; CoreDNS has no zone for it and forwarded it to the VPC resolver (NXDomain), and only then walked the search list to get the answer on the `svc.cluster.local` candidate — cluster-internal names leak to the upstream resolver
   - B) ndots:1 disables the CoreDNS cache
   - C) `kubernetes.default` did not resolve at all under ndots:1
   - D) glibc sends A and AAAA sequentially, doubling the time
<details>
<summary>Show Answer</summary>

**Answer: A) With 1 dot ≥ ndots 1, glibc first sent `kubernetes.default.` as an absolute name; CoreDNS has no zone for it and forwarded it to the VPC resolver (NXDomain), and only then walked the search list to get the answer on the `svc.cluster.local` candidate — cluster-internal names leak to the upstream resolver**

**Explanation:**
In the ndots:1 Pod, `kubernetes.default` (1 dot) went out first as the absolute name `kubernetes.default.`; CoreDNS has no zone for it, forwarded it to the VPC resolver and got NXDomain back after 1.6 ms. Then came `kubernetes.default.bench-net.svc.cluster.local` (NXDOMAIN) and finally `kubernetes.default.svc.cluster.local`, answered with 172.20.0.1 — 6 queries, 4 NXDOMAIN, 2.04 ms warm median, worse than the 4 queries / 2 NXDOMAIN / 1.71 ms under ndots:5 (C is wrong). External names, by contrast, gain a lot: `sts.ap-northeast-2.amazonaws.com` and `www.amazon.com` went from 10 to 2 queries and from a 3.5–3.8 ms to a 0.5–0.9 ms median (about 4–7× faster, 5× fewer queries). glibc sends A and AAAA in parallel by default (D is wrong), and the CoreDNS cache has nothing to do with the Pod's ndots (B is wrong). If you use ndots:1, write in-cluster Services as FQDNs of the form `service.namespace.svc.cluster.local`; the trailing-dot form works regardless of ndots — always 2 queries and about 0.4–0.8 ms.

</details>

9. Every fortio latency table on the page comes from a rerun with `-r 0.00001` (10 µs histogram resolution). Why was the first run discarded?
   - A) The first run had a high error rate
   - B) fortio's default `-r 0.001` means 1 ms buckets, so every sub-millisecond response landed in a single bucket and the percentiles were linear interpolations inside it (e.g. p50 = 0.5 ms for everything below 1 ms) — the averages were valid, the percentiles were meaningless
   - C) At the default resolution fortio does not compute p99.9
   - D) The first run had accidentally been made without keepalive
<details>
<summary>Show Answer</summary>

**Answer: B) fortio's default `-r 0.001` means 1 ms buckets, so every sub-millisecond response landed in a single bucket and the percentiles were linear interpolations inside it (e.g. p50 = 0.5 ms for everything below 1 ms) — the averages were valid, the percentiles were meaningless**

**Explanation:**
The real p50 values in this benchmark are all below 1 ms — 0.259–0.704 ms for keepalive HTTP. With fortio's default `-r 0.001` the histogram bucket is 1 ms, so all of those samples pile into the first bucket and the percentiles are linearly interpolated inside it, producing fake values such as p50 = 0.5 ms regardless of path. The averages were valid, but the percentiles were discarded and every fortio run was repeated with `-r 0.00001` (10 µs buckets). Every run had 0 errors (A is wrong) and the request/response setup was unchanged (D is wrong). The lesson: check your tool's histogram resolution before measuring a sub-millisecond network.

</details>

10. Which statement correctly describes why the page did NOT measure the ClusterIP (kube-proxy iptables) hop or `trafficDistribution: PreferClose`?
   - A) fortio cannot target a Service DNS name
   - B) kube-proxy was in IPVS mode, so there was no iptables hop to measure
   - C) The cluster's aws-load-balancer-controller webhook (`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`) intercepts every Service CREATE, but the controller Pods had been in CrashLoopBackOff for 48 days waiting for a Gateway API `ListenerSet` CRD, so the webhook had zero endpoints and no Service could be created anywhere in the cluster — the webhook was not bypassed and the fixture used Pod IPs only
   - D) It was measured but left out of the tables because it matched the Pod-IP numbers
<details>
<summary>Show Answer</summary>

**Answer: C) The cluster's aws-load-balancer-controller webhook (`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`) intercepts every Service CREATE, but the controller Pods had been in CrashLoopBackOff for 48 days waiting for a Gateway API `ListenerSet` CRD, so the webhook had zero endpoints and no Service could be created anywhere in the cluster — the webhook was not bypassed and the fixture used Pod IPs only**

**Explanation:**
Every `kubectl apply` of a Service in the benchmark namespace was rejected with `Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`. A read-only diagnosis found aws-load-balancer-controller v3.2.1 (kube-system, 2 replicas) in CrashLoopBackOff for 48 days with 9,250 restarts: each container logged `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"` repeatedly and exited after about 2m18s on a cache-sync timeout. Its `MutatingWebhookConfiguration` `aws-load-balancer-webhook` matches CREATE on every Service cluster-wide (`namespaceSelector: {}`) with `failurePolicy: Fail`, so with zero ready endpoints no Service can be created in any namespace. Rather than bypass the webhook or repair the controller, the fixture used Pod IPs only, which is why the page has no numbers for the ClusterIP hop or for `PreferClose` (beta in Kubernetes 1.31, GA in 1.33) (D is wrong). kube-proxy was in `mode: "iptables"` (B is wrong). Also not collected: the ENA allowance counters (`ethtool -S`, which needs a hostNetwork Pod); and every cell is n = 1 from a single day, so the figures are order-of-magnitude anchors, not SLAs.

</details>

---

[Return to Learning Materials](../../networking/06-pod-network-benchmark.md) | [Back to Networking Home](../../networking/README.md)
