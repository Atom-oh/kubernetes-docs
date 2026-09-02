# EBS gp2 vs gp3 Measured Benchmark Quiz

1. What did the measured IOPS of a 100 GiB gp2 volume look like under sustained 4k random reads (qd32)?
   - A) It hovered gently around 300 IOPS from the start
   - B) It matched gp3 at 3,001 IOPS for about 33 minutes (1,999 s), then dropped to 300 IOPS within one second
   - C) It started at 3,000 IOPS and declined gradually to 300 over 45 minutes
   - D) It held 3,000 IOPS for the full 45 minutes
<details>
<summary>Show Answer</summary>

**Answer: B) It matched gp3 at 3,001 IOPS for about 33 minutes (1,999 s), then dropped to 300 IOPS within one second**

**Explanation:**
fio's per-second IOPS log recorded 3,001 at 1,998 s, 2,659 at 1,999 s, and 300 at 2,000 s. While credits remain, gp2 is indistinguishable from gp3; the moment they run out, 90% of the capacity vanishes as if a switch were flipped. The accurate statement is not "gp2 is slow" but "gp2 becomes slow suddenly."

</details>

2. Why is the burst duration of a 100 GiB gp2 volume calculated as roughly 2,000 seconds?
   - A) 5,400,000 credits ÷ (3,000 − 300) IOPS = 2,000 s
   - B) 100 GiB × 20 s/GiB = 2,000 s
   - C) 3,000 IOPS ÷ 1.5 = 2,000 s
   - D) AWS fixes it at 2,000 s regardless of volume size
<details>
<summary>Show Answer</summary>

**Answer: A) 5,400,000 credits ÷ (3,000 − 300) IOPS = 2,000 s**

**Explanation:**
gp2 has a baseline of 3 IOPS/GiB (100 GiB → 300 IOPS) and a 5.4M-credit bucket. Bursting at 3,000 IOPS consumes 2,700 credits per second after subtracting the 300 that the baseline refills, so 5,400,000 ÷ 2,700 = 2,000 s. Larger volumes have higher baselines and drain more slowly; at 1 TiB and above the baseline is already 3,000, so there is no cliff.

</details>

3. After credit exhaustion, gp2's qd32 average latency measured about 106 ms. Which interpretation is correct?
   - A) The EBS device's response time became slower than 100 ms
   - B) Per Little's law, 32 outstanding I/Os ÷ 300 IOPS ≈ 106.7 ms — it is time spent waiting in the queue
   - C) Network latency spiked
   - D) It is a fio measurement error
<details>
<summary>Show Answer</summary>

**Answer: B) Per Little's law, 32 outstanding I/Os ÷ 300 IOPS ≈ 106.7 ms — it is time spent waiting in the queue**

**Explanation:**
Average latency = outstanding I/Os ÷ throughput. Keeping 32 I/Os in flight while only 300 complete per second means each I/O waits 106.7 ms on average. The 10.4 ms at 3,000 IOPS is the same arithmetic (32 ÷ 3,000 = 10.7 ms). Latency in a qd32 benchmark is queueing time; device latency is what the qd1 measurement shows (gp3: 0.56 ms).

</details>

4. Why did a 120-second random write test on gp2, run right after credit depletion, measure 601 IOPS instead of 300?
   - A) Writes do not consume credits
   - B) During the preceding 120 s of rest, gp2 accrued 300 credits/s × 120 s = 36,000 credits, which added 300 IOPS over the 120-second test
   - C) fio counts write IOPS twice
   - D) gp2's write baseline is double its read baseline
<details>
<summary>Show Answer</summary>

**Answer: B) During the preceding 120 s of rest, gp2 accrued 300 credits/s × 120 s = 36,000 credits, which added 300 IOPS over the 120-second test**

**Explanation:**
The gp2 credit bucket is not empty forever once drained; it is a bank account that refills at 3 credits/GiB/s (100 GiB → 300/s) whenever the volume rests. Spending 36,000 credits over 120 s adds 300 IOPS to the 300 baseline for exactly 600 (measured: 601). The 603 IOPS in the qd1 test follows the same arithmetic with 18,000 credits accrued during a 60-second rest. This is why gp2 under intermittent traffic is "fast some days, slow other days."

</details>

5. In the qd1 4k random read test, throttled gp2 showed p50 0.602 ms and p95 3.391 ms. What does this distribution tell you?
   - A) The gp2 device is fundamentally slower than gp3
   - B) The device is the same as gp3 (p50 nearly equals gp3's 0.569 ms), but I/Os beyond the per-second allowance waited in the throttle queue, producing a bimodal distribution
   - C) Another pod shared the volume during the test
   - D) Random reads always show a bimodal distribution
<details>
<summary>Show Answer</summary>

**Answer: B) The device is the same as gp3 (p50 nearly equals gp3's 0.569 ms), but I/Os beyond the per-second allowance waited in the throttle queue, producing a bimodal distribution**

**Explanation:**
Half of gp2's I/Os finished in 0.6 ms, exactly like gp3. The other half landed at 3.4–3.6 ms because I/Os beyond the per-second allowance (about 603 IOPS) were held in the throttle queue. The average alone reads 1.65 ms — "a bit slower" — while p95 jumped 6x. This is why storage dashboards need p50 alongside p95/p99.

</details>

6. Why did both gp2 and gp3 stop at 125–130 MiB/s in the 1 MiB sequential read/write test?
   - A) gp3 hit its 125 MiB/s baseline and gp2 (≤170 GiB) hit its 128 MiB/s cap; the two values happen to be close
   - B) The m5.xlarge instance's network bandwidth limit
   - C) fio's iodepth=8 was the bottleneck
   - D) gp2's credits ran out and slowed both volumes
<details>
<summary>Show Answer</summary>

**Answer: A) gp3 hit its 125 MiB/s baseline and gp2 (≤170 GiB) hit its 128 MiB/s cap; the two values happen to be close**

**Explanation:**
gp3's default throughput is 125 MiB/s; gp2 caps at 128 MiB/s for volumes of 170 GiB or less. gp2's empty credit bucket did not slow the sequential test because EBS counts a 1 MiB I/O as four 256 KiB operations, so 130 MiB/s is only about 520 IOPS — well within the 36,000 credits accrued during the preceding rest. The throughput ceiling engaged before the IOPS ceiling. Note that the m5.xlarge instance EBS bandwidth (≈137 MiB/s) is slightly higher and was not the bottleneck here, but raising gp3 to 250 MiB/s would still stop near 137 MiB/s on this instance.

</details>

7. For a 100 GiB dataset that needs sustained 3,000 IOPS, which cost comparison (Seoul region) is correct?
   - A) gp2 100 GiB ($11.40) is sufficient
   - B) gp3 100 GiB ($9.12) delivers 3,000 IOPS without limit, while getting the same baseline on gp2 requires 1 TiB ($114.00) — roughly a 12x difference
   - C) gp3 requires extra paid IOPS, so it costs more than gp2
   - D) Both volumes cost the same per month
<details>
<summary>Show Answer</summary>

**Answer: B) gp3 100 GiB ($9.12) delivers 3,000 IOPS without limit, while getting the same baseline on gp2 requires 1 TiB ($114.00) — roughly a 12x difference**

**Explanation:**
gp2 100 GiB at $11.40 guarantees only 300 sustained IOPS (the 3,000 burst lasts at most 33 minutes). In the gp2 era, the standard move was to grow the volume to 1 TiB for IOPS, at $114.00. gp3 decouples IOPS from capacity and provides the same 3,000 IOPS at $9.12 for 100 GiB. If needed, 6,000 IOPS (+$17.10) or 250 MiB/s (+$5.70) can be purchased separately.

</details>

8. What is the Kubernetes-native way to convert an existing gp2 PVC with data to gp3 without restarting the pod?
   - A) Edit the StorageClass `type` parameter to gp3 and existing PVs change automatically
   - B) Create a `VolumeAttributesClass` (storage.k8s.io/v1, GA in Kubernetes 1.34) and set the PVC's `volumeAttributesClassName`; the EBS CSI driver calls ModifyVolume
   - C) Delete the PVC and recreate it with the gp3 StorageClass
   - D) Running `aws ec2 modify-volume` on the node is the only option
<details>
<summary>Show Answer</summary>

**Answer: B) Create a `VolumeAttributesClass` (storage.k8s.io/v1, GA in Kubernetes 1.34) and set the PVC's `volumeAttributesClassName`; the EBS CSI driver calls ModifyVolume**

**Explanation:**
StorageClass parameters apply only when new volumes are created; existing PVs are unaffected. VolumeAttributesClass lets you change `type`, `iops`, and `throughput` while the pod runs, using EBS Elastic Volumes underneath. Caveats: EBS allows one modification per volume every six hours, so batch type, IOPS, and throughput changes together, and Kubernetes 1.31–1.33 needs the v1beta1 API plus a feature gate. Running `aws ec2 modify-volume` directly works, but the PV object keeps `gp2` as its StorageClass name, which causes confusion later.

</details>
