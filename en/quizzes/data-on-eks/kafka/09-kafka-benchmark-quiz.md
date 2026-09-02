# Part 9: Kafka on EKS Measured Benchmark Quiz

1. In test F1 (RF3, acks=all, 10 M records) the producer reported 134.74 MiB/s of cluster ingest. What did the in-pod sampler show each of the three brokers writing to its own gp3 volume?
   - A) About one third of the ingest (≈ 45 MiB/s), because the six partitions are spread across three brokers
   - B) About the whole ingest — 115.2–117.5 MiB/s average, 135 MiB/s at peak — because with RF3 every broker holds a copy of every partition
   - C) About twice the ingest, because each broker writes the leader copy and a follower copy
   - D) Nothing measurable — writes sat in the page cache for the whole run
<details>
<summary>Show Answer</summary>

**Answer: B) About the whole ingest — 115.2–117.5 MiB/s average, 135 MiB/s at peak — because with RF3 every broker holds a copy of every partition**

**Explanation:**
With replication factor 3 on a 3-broker cluster, each broker is leader for 1/3 of the partitions and follower for the other 2/3, so it writes ≈ X to its own disk for a cluster ingest of X. The F1 window confirms the arithmetic: at 134.74 MiB/s ingest each broker received 134.2–135.8 MiB/s on its NIC, transmitted 80.2–108.1 MiB/s (2/3 × 134.74 ≈ 90 MiB/s expected), and wrote 115.2–117.5 MiB/s average with 134.9–135.1 MiB/s peak 10-s samples. Three volumes therefore behave like one 125 MiB/s volume, which is why the RF3 ceiling was ≈ 130–135 MiB/s.

</details>

2. The benchmark concludes that the RF3 ceiling is set by gp3 *throughput*, not IOPS. Which measurement supports that?
   - A) Write IOPS reached the 3,000 IOPS cap in every test
   - B) The volumes wrote only ≈ 400–520 IOPS at ≈ 240 KiB per write while the write rate sat at 123–124 MiB/s steady / 135 MiB/s peak — far below 3,000 IOPS but at the 125 MiB/s cap
   - C) Broker CPU hit 4 cores before the disks did
   - D) The producer's `buffer.memory` was never full
<details>
<summary>Show Answer</summary>

**Answer: B) The volumes wrote only ≈ 400–520 IOPS at ≈ 240 KiB per write while the write rate sat at 123–124 MiB/s steady / 135 MiB/s peak — far below 3,000 IOPS but at the 125 MiB/s cap**

**Explanation:**
Kafka appends large sequential writes, so its IOPS demand is low: the sampler recorded 426–505 write IOPS across the sustained RF3 acks=all windows (F1, F5, F6, E2; ≈ 240 KiB per write) against a 3,000 IOPS gp3 baseline. Meanwhile the byte rate on each volume — 123–124 MiB/s steady in E2's fine-grained view, 134.5–135.5 MiB/s in the best 10-s samples — was at the volume's 125 MiB/s throughput cap, and CloudWatch independently showed 116.8–121.0 MiB/s per volume in E2's steady minutes. Broker CPU stayed at 0.30–0.84 of 4 cores and the producer *was* blocked on its buffer (avg latency 160–890 ms), so the brokers' disks, not CPU or the client, were the limit.

</details>

3. What did the rate-limited latency test (20,000 rec/s, RF3) show about the cost of `acks=all` compared with `acks=1`?
   - A) p50 doubled, from 3 ms to 6 ms
   - B) Throughput fell by half
   - C) p50 was identical at 3 ms for both settings; the cost appeared in the tail — p99 126 ms vs 17 ms
   - D) There was no measurable difference at any percentile
<details>
<summary>Show Answer</summary>

**Answer: C) p50 was identical at 3 ms for both settings; the cost appeared in the tail — p99 126 ms vs 17 ms**

**Explanation:**
B1 (acks=all) and B2 (acks=1) both ran at 20k rec/s ≈ 19.5 MiB/s with p50 = 3 ms. The difference is entirely in the tail: p99 126 ms vs 17 ms (7.4×), p99.9 173 ms vs 40 ms. The full-rate client-bound runs tell the same story — p99 = 164 / 38 / 26 ms for acks=all / 1 / 0 (A1/A2/A3). acks=all costs tail latency, not median latency. (No acks=0 run was made at 20k rec/s, so the page does not quote one.)

</details>

4. On the same three brokers, switching a topic from RF3 to RF1 (F4 vs F1, 10 M records each) changed the measured producer throughput how?
   - A) It was unchanged, because the producer was the bottleneck
   - B) It rose from 134.74 to 337.81 MiB/s — 2.5× — because each byte now lands on one gp3 volume instead of three
   - C) It rose by exactly 3×, to the theoretical 375 MiB/s
   - D) It dropped, because leaders without followers spend more time on fsync
<details>
<summary>Show Answer</summary>

**Answer: B) It rose from 134.74 to 337.81 MiB/s — 2.5× — because each byte now lands on one gp3 volume instead of three**

**Explanation:**
337.81 / 134.74 = 2.51. With RF1 the replication traffic disappears (broker NIC tx fell to 0.3 MiB/s) and each broker receives only its third of the stream, so the three 125 MiB/s volumes work in parallel: 3 × 125 = 375 MiB/s theoretical, 337.81 measured. The measured figure is also a lower bound, not a disk-bound steady state — it came from a single m5.large client in a 32 s run (≈ 3.2 GiB per broker at RF1), and one 5-s interval reported 481.53 MiB/s, which only the page cache could have absorbed. The "replication tax" is exactly the volume-throughput fan-out, not Kafka overhead.

</details>

5. Test F6 raised `batch.size` from 64 KiB to 256 KiB and `linger.ms` from 5 to 10. What changed compared with F1?
   - A) Throughput tripled because larger batches bypass the page cache
   - B) Throughput stayed within page-cache noise (148.38 vs 134.74 MiB/s), but broker CPU fell from 0.64–0.84 to 0.40–0.50 cores
   - C) Broker CPU rose because larger batches take longer to checksum
   - D) p99 latency rose above 10 s because records waited longer in the producer
<details>
<summary>Show Answer</summary>

**Answer: B) Throughput stayed within page-cache noise (148.38 vs 134.74 MiB/s), but broker CPU fell from 0.64–0.84 to 0.40–0.50 cores**

**Explanation:**
Bigger batches cannot raise a ceiling set by the disks: F6's 148.38 MiB/s over 6 M records versus F1's 134.74 over 10 M is inside the variance the page cache introduces between runs of different lengths, and each volume still peaked at 134.8–135.4 MiB/s. What did change is broker CPU: 0.64–0.84 → 0.40–0.50 cores, roughly 40% less. Fewer, larger produce and replica-fetch requests are the likely reason — request counts were not sampled, so the page presents that as the plausible explanation, not a measured one. Adding a second producer (F5) did the opposite of helping: 129.82 MiB/s combined with average latency roughly doubling from 444 to ~890 ms.

</details>

6. The compression table shows lz4 at 9.0× and zstd at 16.6× smaller on disk. Why does the page insist these ratios are an upper bound?
   - A) `kafka-log-dirs.sh` reports sizes before segment flush
   - B) Each synthetic record is 63.2% `x` padding — trivially compressible filler added to reach ~1 KiB; without it the same corpus compresses 7.8× rather than 18.5× with zlib-6
   - C) The brokers re-compressed the data with a stronger codec
   - D) Only one of the three replicas was measured
<details>
<summary>Show Answer</summary>

**Answer: B) Each synthetic record is 63.2% `x` padding — trivially compressible filler added to reach ~1 KiB; without it the same corpus compresses 7.8× rather than 18.5× with zlib-6**

**Explanation:**
Each payload line is ≈ 362 B of JSON plus a `"pad":"xxx…"` field of ≈ 636 characters. That padding inflates every ratio (whole-corpus zlib-6: 18.5× with pad vs 7.8× without; per 64-record batch 16.2× vs 6.5×). What transfers from the table is the ordering — zstd ≈ gzip ≫ lz4 > snappy on ratio, lz4 > snappy ≈ none > zstd ≫ gzip on client throughput — and the bottleneck shift: uncompressed had 260 ms average latency (broker-bound), while every codec had ≤ 6 ms because the client CPU became the limit (gzip only 51.35 MiB/s on one thread). Brokers store what the producer sent (`compression.type=producer` default), so D and C are wrong; all three replicas were identical in size.

</details>

7. In E4 a consumer replayed the 30 GiB topic from offset 0 while a producer wrote to the same cluster. What happened to the producer compared with its solo run (E0)?
   - A) Nothing — reads and writes use separate EBS budgets
   - B) Throughput fell from 103.36 to 57.37 MiB/s and p99 rose from 82 ms to 2,147 ms, because the cold fetches shared each broker's single gp3 volume with the log appends
   - C) Throughput rose because the consumer warmed the page cache
   - D) The producer was throttled by `min.insync.replicas` shrinking to 1
<details>
<summary>Show Answer</summary>

**Answer: B) Throughput fell from 103.36 to 57.37 MiB/s and p99 rose from 82 ms to 2,147 ms, because the cold fetches shared each broker's single gp3 volume with the log appends**

**Explanation:**
Cold data has to come from EBS: during E3 the volumes read 88.0–111.5 MiB/s each (10-s peaks ≈ 124 MiB/s, the gp3 cap) at 1,315–1,545 read IOPS. In E4 that read traffic shared the single volume per broker with the producer's appends. The window averages (39.4–47.2 MiB/s written plus 28.6–37.7 MiB/s read per broker) look low only because page cache absorbed the first ~20 s; from 02:26:47 to the end of the produce window every ~12-s sample on kafka-1 and kafka-2 ran at a combined 124–129 MiB/s read+write — the gp3 cap. Both sides slowed sharply: producer 57.37 MiB/s (≈ 55.5% of 103.36) with p95/p99/max of 1,587 / 2,147 / 2,569 ms, consumer 299.62 MiB/s of fetch time (288.79 MiB/s overall, about a third lower) versus 438.6 alone. Broker CPU stayed at 0.36–0.42 cores, so the contention was on the volume, not the CPU. A consumer that falls out of the page cache is a producer-latency incident; keep consumers within cache or isolate replay traffic.

</details>

8. Why does the page say that a Kafka benchmark shorter than roughly 10 GiB per broker "measures page cache + network, not EBS"?
   - A) Kafka buffers everything in the JVM heap until the segment closes
   - B) Kafka does not fsync per message, and with `vm.dirty_ratio=20` on a 16 GiB node several GiB of dirty pages sit in RAM — E0's disks wrote only 60–67 MiB/s while the producer reported 103.36, and F4 reported a 481.53 MiB/s interval on volumes that can absorb at most 3 × 125 = 375 MiB/s
   - C) The EBS CSI driver delays volume attachment for the first minute
   - D) `kafka-producer-perf-test` only starts counting after 10 GiB
<details>
<summary>Show Answer</summary>

**Answer: B) Kafka does not fsync per message, and with `vm.dirty_ratio=20` on a 16 GiB node several GiB of dirty pages sit in RAM — E0's disks wrote only 60–67 MiB/s while the producer reported 103.36, and F4 reported a 481.53 MiB/s interval on volumes that can absorb at most 3 × 125 = 375 MiB/s**

**Explanation:**
`log.flush.interval.messages` defaults to `Long.MAX`; durability comes from replication, and the kernel flushes dirty pages in the background. So a 3,000,000-record run (3,000,000 × 1,024 B ≈ 2.86 GiB per copy, ~30 s) finishes before the disks catch up: in E0 the three brokers wrote 60.4 / 63.3 / 67.4 MiB/s during the test and were still draining at 51–71 MiB/s during the following hot-consume window. Only the long runs — F1 (≈ 9.5 GiB × RF3), E2 (30 GiB) — reached the disk-bound steady state that the F1 (134.74 MiB/s) and RF3 ceiling figures rest on. The related tool gotcha: `--record-size` mode measures your client CPU (≈ 105–113 MiB/s on this client); use `--payload-file` for throughput tests.

</details>

---

[Return to Learning Materials](../../../data-on-eks/kafka/09-kafka-benchmark.md) | [Back to Kafka Deep Dive Home](../../../data-on-eks/kafka/README.md)
