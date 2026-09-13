# Prometheus Quiz

> **Last Updated**: September 12, 2026

1. What is Prometheus's normal metric collection path?

   - A) Applications must push every sample directly
   - B) Prometheus scrapes configured targets over HTTP
   - C) Only a streaming event log
   - D) Only periodic CSV imports

<details>
<summary>Show answer</summary>

**Answer: B**

The normal path is pull/scrape. Remote write and optional batch integrations add other delivery paths. up reports scrape success, not complete application availability.

</details>

2. Which expression gives a Counter's average per-second rate over five minutes?

   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>Show answer</summary>

**Answer: B**

rate() uses a range vector and handles observed resets/extrapolation. increase() estimates total increase, not the per-second rate. Apply rate before aggregation and do not interpret it as recovery of every missed increment.

</details>

3. What must a working ServiceMonitor describe?

   - A) A Grafana dashboard
   - B) Only a Prometheus container image
   - C) Selected Services and scrape endpoints, with selectors/port names matching the Prometheus setup
   - D) A complete application Deployment

<details>
<summary>Show answer</summary>

**Answer: C**

Prometheus first selects the monitor's namespace and labels; the monitor selects target Services. Its endpoint port is the Service port name. RBAC, TLS/network access and an instrumented application are additional requirements.

</details>

4. What does histogram_quantile() return for classic histograms?

   - A) An exact Summary percentile
   - B) A bucket-based quantile estimate
   - C) An exact percentile independent of bucket resolution
   - D) A Counter's request rate

<details>
<summary>Show answer</summary>

**Answer: B**

Aggregate compatible classic buckets while retaining le. The result interpolates within buckets. Summary quantiles also have algorithm/window-dependent error and cannot be averaged into a fleet percentile.

</details>

5. Which component is not part of the kube-prometheus-stack package?

   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>Show answer</summary>

**Answer: C**

The chart packages Prometheus/Alertmanager, Operator, Grafana and exporters, subject to enabled values. VictoriaMetrics is a separate deployment. Pin the inspected chart cohort rather than mixing arbitrary image versions.

</details>

6. What is remote write used for?

   - A) Sending Alertmanager notifications
   - B) Asynchronous sample delivery to a configured external receiver
   - C) Guaranteeing unlimited outage buffering
   - D) Synchronizing Grafana dashboards

<details>
<summary>Show answer</summary>

**Answer: B**

Receivers include AMP, VictoriaMetrics and Mimir. Each has its own endpoint, identity, quotas and HA contract. WAL buffering is finite, and local Prometheus retention itself is configurable rather than universally capped at 30 days.

</details>

7. What does an alert rule's for duration control?

   - A) Metric retention
   - B) How long the same alert condition/label set remains pending before firing
   - C) Alertmanager's repeat interval
   - D) The number of Prometheus replicas

<details>
<summary>Show answer</summary>

**Answer: B**

The condition must remain satisfied through evaluations for that alert identity. Missing data or label changes can interrupt pending state. Notification grouping and timing are separate Alertmanager settings.

</details>

8. How should predict_linear() be interpreted?

   - A) A guaranteed disk failure deadline
   - B) A fitted Gauge trend extrapolated into the future
   - C) Seasonal triple-exponential prediction
   - D) A replacement for all capacity measurements

<details>
<summary>Show answer</summary>

**Answer: B**

It projects the observed linear trend. Workload changes, cleanup, sparse data and non-linear behavior can invalidate it. The old holt_winters name is replaced in Prometheus 3 by an explicitly experimental double-exponential smoothing function; that is not a seasonal model.

</details>

9. What does AlertmanagerConfig groupBy do?

   - A) Automatically authorizes alerts from every namespace
   - B) Groups notifications by selected labels
   - C) Defines Prometheus's for duration
   - D) Makes every matching sibling route run

<details>
<summary>Show answer</summary>

**Answer: B**

groupBy becomes group_by in native configuration. Routes normally stop at the first sibling match unless continue is configured. Inhibition needs meaningful resource-identity equal labels to avoid suppressing unrelated service/node warnings.

</details>

10. What does the TSDB WAL provide?

   - A) A query-result cache
   - B) Sequential recording that supports crash recovery before block persistence
   - C) A backup that survives losing the volume
   - D) An unlimited remote-write delivery queue

<details>
<summary>Show answer</summary>

**Answer: B**

WAL replay is a durability mechanism, not a promise of zero loss under corruption, volume failure or long remote outages. Retention and WAL/head/compaction disk requirements are separate; preserve verified backups and recovery procedures.

</details>

[Return to the guide](../../../observability/metrics/01-prometheus.md)
