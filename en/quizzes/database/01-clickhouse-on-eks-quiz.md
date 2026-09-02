# ClickHouse on EKS Measured Benchmark Quiz

1. In the benchmark, the one-hour `namespace + timestamp` range count (Q1) finished in 4ms against a 100M-row table. What is the key reason?
   - A) The result was already stored in the query cache
   - B) Pruning via PARTITION BY (day) and ORDER BY (namespace, timestamp) meant only 16,385 of 100M rows were read
   - C) The gp3 volume's 3,000 IOPS was high enough
   - D) The LowCardinality type vectorized the comparisons
<details>
<summary>Show Answer</summary>

**Answer: B) Pruning via PARTITION BY (day) and ORDER BY (namespace, timestamp) meant only 16,385 of 100M rows were read**

**Explanation:**
When query conditions line up with the partition key (daily) and the sorting key (namespace, timestamp), ClickHouse prunes at granule granularity using the primary index. In this benchmark only two granules — 16,385 rows, 0.016% — were read. Most of ClickHouse's speed comes from this "don't read it" design.

</details>

2. In the per-column compression results, trace_id compressed at 1.0× (incompressible) while namespace compressed about 201×. What explains the difference?
   - A) Only the trace_id column was missing a compression codec
   - B) namespace strings are shorter
   - C) trace_id is high-entropy (32 random hex chars) with nothing to compress, while namespace is low-cardinality and the first ORDER BY key, so identical values run in long streaks
   - D) Only namespace gets a separate dictionary file
<details>
<summary>Show Answer</summary>

**Answer: C) trace_id is high-entropy (32 random hex chars) with nothing to compress, while namespace is low-cardinality and the first ORDER BY key, so identical values run in long streaks**

**Explanation:**
Random IDs have high information entropy, so no general-purpose compressor can shrink them (3.08 GiB → 3.07 GiB). namespace has only 10 distinct values and is the first sort key, so identical values are stored in contiguous runs: 96 MiB collapsed to 0.5 MiB. This is why "how do we store IDs" is the biggest storage-cost lever in a log schema.

</details>

3. Which statement matches the measured LZ4 (default) vs ZSTD(3) comparison?
   - A) ZSTD(3) won on both storage and scan speed
   - B) ZSTD(3) storage was 47% smaller, but the CPU-bound full scan was about 1.9× slower than LZ4
   - C) The storage difference between the codecs was within 5%
   - D) LZ4 was smaller on disk but slower to scan
<details>
<summary>Show Answer</summary>

**Answer: B) ZSTD(3) storage was 47% smaller, but the CPU-bound full scan was about 1.9× slower than LZ4**

**Explanation:**
Measured: LZ4 7.82 GiB (1.97×) vs ZSTD(3) 4.16 GiB (3.7×) — 47% less storage — while the warm `LIKE '%timeout%'` full scan slowed from 2.63 s to 4.9 s. Hence the canonical log-workload recipe: LZ4 for recent partitions, TTL-driven ZSTD recompression for old ones.

</details>

4. The `LIKE '%timeout%'` full scan (Q3) took 31.5 s when bypassing the page cache. What bottleneck does this number point to?
   - A) ClickHouse's string-search algorithm is inefficient
   - B) Reading the ~4 GiB compressed message column ÷ 31.5 s ≈ 130 MiB/s — pinned at the gp3 baseline throughput (125 MiB/s)
   - C) The m5.xlarge's 4 vCPUs were saturated
   - D) EBS CSI driver overhead dominated
<details>
<summary>Show Answer</summary>

**Answer: B) Reading the ~4 GiB compressed message column ÷ 31.5 s ≈ 130 MiB/s — pinned at the gp3 baseline throughput (125 MiB/s)**

**Explanation:**
The same query served from the page cache finished in 2.63 s (CPU-bound, ~38M rows/s). The 12× slowdown on direct disk reads is measured evidence that full-scan performance can be a volume-throughput setting rather than a database property — gp3 throughput can be raised to 1,000 MiB/s for an extra fee.

</details>

5. What did adding a bloom filter skip index change for the trace_id point lookup (Q5), per the measurements?
   - A) Lookup time 1.13 s → 0.036 s (31×), rows read 100M → 1.08M (98.9% skipped), index size about 1.5% of the table
   - B) Lookup time was unchanged; only memory usage dropped
   - C) Lookup time halved and the index consumed 30% of the table size
   - D) Same effect as changing the ORDER BY key, and storage shrank too
<details>
<summary>Show Answer</summary>

**Answer: A) Lookup time 1.13 s → 0.036 s (31×), rows read 100M → 1.08M (98.9% skipped), index size about 1.5% of the table**

**Explanation:**
The `bloom_filter(0.01) GRANULARITY 4` skip index probabilistically proves "this value is not here" per granule group, letting ClickHouse skip most of them. Data read dropped from 3.82 GiB to 42.6 MiB; the index itself is 119.7 MiB (1.5% of the table) and MATERIALIZE took about 20 seconds.

</details>

6. What caveat must accompany the benchmark's ingest figure (~940K rows/s)?
   - A) It was measured with three replicas
   - B) It was measured via in-server INSERT…SELECT, so network transfer and text parsing are absent — it is an upper bound
   - C) It wrote to memory only, never to disk
   - D) Compression was disabled during the measurement
<details>
<summary>Show Answer</summary>

**Answer: B) It was measured via in-server INSERT…SELECT, so network transfer and text parsing are absent — it is an upper bound**

**Explanation:**
The rows were generated inside the server and inserted directly, which is more favorable than an external client pushing TSV/Native data. Sorting, compression, and disk writes are all included, but the number should be read as the ceiling for external ingest throughput.

</details>

7. Q4 (duration p50/p99 per namespace) scans all 100M rows yet finishes in about 1 second warm. Which property makes that possible?
   - A) The result was precomputed in a materialized view
   - B) Column-oriented storage — it reads only duration_ms (289 MiB) and namespace (0.5 MiB), not the table's full 7.8 GiB
   - C) The quantile function uses sampling
   - D) Partition pruning limited it to one day of data
<details>
<summary>Show Answer</summary>

**Answer: B) Column-oriented storage — it reads only duration_ms (289 MiB) and namespace (0.5 MiB), not the table's full 7.8 GiB**

**Explanation:**
A row-oriented database would have to read entire rows for this query; a columnar engine reads only the columns the aggregation needs. The scan covered the whole time range (so no partition pruning — D is wrong), and the quantiles were computed over the actual values.

</details>

8. Under this guidebook's decision framework, when is running ClickHouse self-hosted on EKS (rather than a managed service) especially defensible?
   - A) When there is no platform team and no database operations experience
   - B) When a standard managed service suffices and there is a single tenant
   - C) When managed offerings are limited or carry a large cost multiple, and a platform team can own operator-based operations including backup and restore rehearsals
   - D) When the data is small — under 100 GiB
<details>
<summary>Show Answer</summary>

**Answer: C) When managed offerings are limited or carry a large cost multiple, and a platform team can own operator-based operations including backup and restore rehearsals**

**Explanation:**
ClickHouse is one of the most commonly self-hosted databases relative to its managed offering. The precondition is a mature operator (Altinity) and a team to run it. Conversely, with scarce operations staffing or an adequate managed option, managed wins — and operating a raw StatefulSet is not one of the options at all.

</details>
