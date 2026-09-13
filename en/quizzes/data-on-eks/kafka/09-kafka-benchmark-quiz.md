# Part 9: Kafka Benchmark Review Quiz

Distinguish reported measurements, causal claims and reproduction checks.

## 1. What is the storage model for three brokers with RF3, and how should F1's 134.74 MiB/s be interpreted?

<details>
<summary>Show answer</summary>

Each broker holds one copy of every partition. Encoded-log and client-payload rates differ; F1 is a short single-run client report. Reconcile cache, writeback, windows and units before claiming a validated sustained 130–135 MiB/s ceiling.

</details>

## 2. Do low IOPS and high byte rates prove that volume throughput is the only bottleneck?

<details>
<summary>Show answer</summary>

No. They are consistent with sequential I/O/throughput pressure, but instance EBS baseline/burst, cache, clients and sampling uncertainty also matter. Do not equate a 135 peak sample with a provisioned 125 MiB/s value. Test the hypothesis with controlled changes.

</details>

## 3. With B1/B2 p50 at 3 ms and p99 at 126/17 ms, can you conclude that acks affects only the tail?

<details>
<summary>Show answer</summary>

No. The p99 ratio is about 7.412, but means also differ at 5.27/2.58 ms. Equal sampled integer-ms medians do not prove equal underlying latency, and one pair is not universal. An acks=0 callback is not a broker durability acknowledgement.

</details>

## 4. Why is F4/F1's 337.81/134.74=2.507 ratio not a pure replication-cost measurement?

<details>
<summary>Show answer</summary>

Both RF and acks change, from RF3/acks=all to RF1/acks=1, and omitted idempotence defaults differ too. Duration, per-broker data, cache and client constraints also differ. Preserve the observed ratio without presenting it as an isolated RF effect.

</details>

## 5. How should F6 be described when batch size, linger and record count all change?

<details>
<summary>Show answer</summary>

148.38 MiB/s is 10.12% above 134.74, with a lower reported CPU range. The 39.19% CPU-midpoint difference is arithmetic, not a batch-only effect. Without repeated variance measurements, the throughput difference cannot be classified as noise.

</details>

## 6. Can the padded JSON's compression ratios and codec ordering be transferred unchanged to other logs?

<details>
<summary>Show answer</summary>

No. About 63.2% x padding makes the distribution unusual; neither ratios nor ordering are universal bounds/rankings. Regenerating the AWK with another implementation can change hashes and compression. Retain the original payload, image and tool versions.

</details>

## 7. Which confounders matter for E4's slowdown and the EC2 network counters?

<details>
<summary>Show answer</summary>

The producer falls 44.49%, from 103.36 to 57.37 MiB/s, but shares a 1.9-CPU client/NIC with the consumer. Low broker CPU does not exclude client contention. EC2 rx/tx credits are separate: F1 rx136 MiB/s≈1.141 Gbps and tx108≈0.906 Gbps are each below 1.25 Gbps. Do not add them to claim bursting.

</details>

## 8. How should a new reproduction validate units, steady state and successful delivery?

<details>
<summary>Show answer</summary>

30M×1024 B is 28.610 GiB, and no universal ten-GiB/one-minute steady-state threshold exists. Record warmup, long windows, drain, repeats, common denominators and actual device/timestamps. Check modern options, fresh populated topics, final successful producer count/stderr and consumed contents. Callback failures may not be captured by exit status alone; a cost estimate is not a bill.

</details>

---

[Return to learning material](../../../data-on-eks/kafka/09-kafka-benchmark.md) | [Kafka deep-dive home](../../../data-on-eks/kafka/README.md)
