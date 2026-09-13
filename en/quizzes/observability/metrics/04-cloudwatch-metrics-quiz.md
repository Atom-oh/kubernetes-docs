# CloudWatch Metrics Quiz

Reviewed with the 2026-09-13 guide.

1. What does a managed CloudWatch backend remove from the team's responsibilities?

   - A) Every collection and IAM task
   - B) Only the AWS backend operation; collectors, identity, retention and response still need ownership
   - C) Every network prerequisite
   - D) All query and log charges

<details>
<summary>Show Answer</summary>

**Answer: B**

Traditional, enhanced and OTel collection have different naming and billing models. Managed storage is not zero operational work.

</details>

2. Which EKS installation statement is correct?

   - A) update-cluster-logging installs Container Insights
   - B) Every platform runs the same host DaemonSet
   - C) Select a compatible add-on or owned Helm installation and verify platform/identity prerequisites
   - D) Helm 6.6.0 is necessarily the EKS add-on version

<details>
<summary>Show Answer</summary>

**Answer: C**

Control-plane logging is separate. Fargate does not run the shown host DaemonSet; Auto Mode/mixed compute needs compatibility checks. Pod Identity/IRSA still needs real setup.

</details>

3. What produces a top-ten dashboard view from SEARCH?

   - A) SEARCH alone always limits results to ten
   - B) SLICE(SORT(SEARCH(...), AVG, DESC), 0, 10)
   - C) PERCENTILE(SEARCH(...), 10)
   - D) An ordinary alarm on the SEARCH array

<details>
<summary>Show Answer</summary>

**Answer: B**

SEARCH returns matching series. Sort and slice explicitly; the ranking uses the evaluated range. SEARCH is not directly alarmable.

</details>

4. Which percentile and ratio statement is correct?

   - A) PERCENTILE(METRICS(),95) gives global request p95
   - B) Every zero-traffic period is a healthy zero-error result
   - C) AVG(METRICS()) PERIOD(300) is a moving average
   - D) Use a supported p95 statistic; guard a count ratio against zero traffic and inspect missing telemetry

<details>
<summary>Show Answer</summary>

**Answer: D**

The guide uses Sum for ALB counts and IF(m2>0,100*m1/m2). CloudWatch arithmetic treats missing values as zero and drops division-by-zero results; service p95 values cannot reconstruct a global p95.

</details>

5. What must an ADOT/EMF metric declaration contain in actual telemetry?

   - A) The dimension labels and values, supplied by discovery/relabeling or the application
   - B) Only dimension names in the exporter config
   - C) A secret access key in every label
   - D) A replica on every node scraping every pod

<details>
<summary>Show Answer</summary>

**Answer: A**

awsemf sends log events for extraction into traditional metrics. The example creates ClusterName/Namespace/Service and uses a gauge. Modern direct OTLP paths are a different option.

</details>

6. Which cost action is unsafe or incompatible with this guide?

   - A) Measure ingestion and query usage
   - B) Set approved retention on one owned log group
   - C) Move EMF/Container Insights logs to Infrequent Access and shorten every unbounded log group's retention
   - D) Review duplicate scrapes and unnecessary labels

<details>
<summary>Show Answer</summary>

**Answer: C**

Infrequent Access does not support EMF or Container Insights log ingestion. Retention reduction may expire existing history. High resolution can increase request/alarm cost, not a universal tenfold metric-storage rate.

</details>

7. What is true of the PutMetricData helpers?

   - A) They provision IAM automatically
   - B) They use caller-provided clients and UTC timestamps, and errors must reach the caller
   - C) Retries guarantee exactly-once business counts
   - D) CloudWatch creates every aggregate dimension set

<details>
<summary>Show Answer</summary>

**Answer: B**

The complete dimension set identifies the custom metric. PutMetricData has no idempotency token; ambiguous retries can duplicate samples. The example reports interval counts and uses Sum.

</details>

8. How do traditional metric dimensions and OTel labels differ?

   - A) Both are always unlimited
   - B) The 150-label limit replaces PutMetricData's limit
   - C) Traditional metrics allow 30 dimensions; the documented OTel model supports up to 150 labels
   - D) Labels never affect payload cost or disclosure

<details>
<summary>Show Answer</summary>

**Answer: C**

They are separate ingestion models. Extra labels add payload and metadata exposure; dimension names alone do not measure cardinality.

</details>

9. Which metric interpretation is correct?

   - A) node_network_total_bytes is bytes/second; namespace_number_of_running_pods counts pods
   - B) cluster_cpu_utilization is the standard published metric
   - C) Running containers always equal running pods
   - D) All reserved-capacity metrics are enhanced-only

<details>
<summary>Show Answer</summary>

**Answer: A**

Verify actual metric catalogues and dimension sets. Pod CPU/memory utilization can use node limits as the denominator. Enhanced observability adds metrics/dimensions and has its own billing model.

</details>

10. What must be checked for an anomaly or restart alarm?

   - A) A created alarm proves live telemetry
   - B) A restart total is always a per-window increment
   - C) Remove ReturnData from the observed anomaly series unconditionally
   - D) History, exact metric identity, total-versus-delta meaning, missing data and notification delivery

<details>
<summary>Show Answer</summary>

**Answer: D**

ANOMALY_DETECTION_BAND returns learned expected bounds. The documented anomaly form can return both the observed series and band. A PodName/Namespace/ClusterName restart total is not automatically five new restarts per five minutes.

</details>

---

[Return to the guide](../../../observability/metrics/04-cloudwatch-metrics.md)
