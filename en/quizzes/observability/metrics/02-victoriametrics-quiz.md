# VictoriaMetrics Quiz

> Review baseline: VictoriaMetrics 1.151.0 · stack chart 0.92.1

1. Which statement is correct when migrating Prometheus queries to VictoriaMetrics?
   - A) Every workload has exactly 7× better compression
   - B) All installations have a fixed 100M-series limit
   - C) Compare actual queries because MetricsQL intentionally differs from PromQL
   - D) Prometheus cannot retain more than 15 days

<details>
<summary>Show Answer</summary>

**Answer: C**

Familiar syntax does not establish identical rate/increase, NaN, scalar or API behavior. Benchmarks need actual versions, data and hardware; retention defaults are not maxima.

</details>

---

2. Which is not one of the cluster storage/query data-plane components?
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) VictoriaMetrics Operator

<details>
<summary>Show Answer</summary>

**Answer: D**

vminsert routes writes, vmstorage stores data, and vmselect queries it. The Operator reconciles Kubernetes resources; it is a separate control component.

</details>

---

3. What does vmagent do?
   - A) Replaces all durable storage
   - B) Renders dashboards
   - C) Collects metrics and forwards them to remote-write destinations
   - D) Replaces Alertmanager notification routing

<details>
<summary>Show Answer</summary>

**Answer: C**

Its queue buffers outages but is finite: the configured disk cap drops oldest queued data, and an emptyDir is lost with Pod replacement. Persistence and monitoring remain separate design choices.

</details>

---

4. What does keep_last_value(q) do, and what needs care?
   - A) Returns the maximum stored value
   - B) Fills evaluated gaps with an earlier value, which can conceal missing telemetry
   - C) Restores all lost scrape samples
   - D) Guarantees healthy availability alerts

<details>
<summary>Show Answer</summary>

**Answer: B**

Use gap filling only when its meaning is intended. Keeping an old healthy value can hide missing collection; monitor missing data separately.

</details>

---

5. What does dedup.minScrapeInterval control?
   - A) The target scraper scheduling interval
   - B) Keeping one sample per discrete interval for the same series
   - C) Lossless generic compression
   - D) Alert evaluation frequency

<details>
<summary>Show Answer</summary>

**Answer: B**

The interval can remove legitimate higher-resolution samples, not just byte-identical copies. Align vmstorage/vmselect settings and the chosen storage/scraper replication design.

</details>

---

6. How should single-node and cluster modes be selected?
   - A) Always choose cluster mode
   - B) Measure load, active series/churn, queries, retention and recovery requirements
   - C) Use 100M samples/day as a universal cutoff
   - D) Single-node mode has no query API

<details>
<summary>Show Answer</summary>

**Answer: B**

Assess one-server capacity and the cost of independently scaling insert/storage/select. Replicated storage or two processes alone does not provide tested service HA.

</details>

---

7. What does vminsert replicationFactor=2 request?
   - A) Exactly two total storage members
   - B) Two copies on distinct storage members, subject to actual availability and history
   - C) Queries on exactly two members
   - D) Twice the compression

<details>
<summary>Show Answer</summary>

**Answer: B**

Maintaining two copies during one storage failure needs at least three members plus the relevant capacity and failure-domain conditions. Configure vmselect/dedup consistently; the flag does not backfill history, make degraded writes lossless, or replace backups.

</details>

---

8. What is the scope of the MetricsQL default operator?
   - A) It always creates correct service labels
   - B) It fills missing points from the right-hand expression; missing data is not automatically zero traffic
   - C) It guarantees that every ratio is meaningful
   - D) It changes the metric ingestion interval

<details>
<summary>Show Answer</summary>

**Answer: B**

Do not append default 0 as a universal error-rate fix. Aggregate status labels consistently, fill a missing numerator only for known denominator series, and exclude zero traffic. The native fixture yields 0, 1 and 0.1 for healthy, all-failed and 10%-failed traffic; absent/zero-traffic services remain absent.

</details>

---

9. What is vmalert responsible for?
   - A) Collecting every application metric
   - B) Storing all long-term samples
   - C) Evaluating alert/recording rules and sending alerts to a configured notifier
   - D) Rendering Grafana dashboards

<details>
<summary>Show Answer</summary>

**Answer: C**

Rule inputs/exporters, datasource URLs, state persistence and notifier/routing configuration must exist. A high restart count is not by itself proof of CrashLoopBackOff. Recording derived series does not compact or delete raw data.

</details>

---

10. What is the correct vmbackup workflow?
   - A) Back up only vminsert configuration
   - B) Read a snapshot from the matching storage directory and protect a distinct backup destination
   - C) Mount any RWO PVC on any node without checking
   - D) Treat storage replication as a complete backup

<details>
<summary>Show Answer</summary>

**Answer: B**

Back up every vmstorage member to a separate prefix, or the intended single-node store. S3/GCS/Azure/local destinations are supported. Verify co-location/PVC identity, workload credentials, retention and actual restore; a local snapshot is not an independent copy.

</details>

---

[Return to learning material](../../../observability/metrics/02-victoriametrics.md)
