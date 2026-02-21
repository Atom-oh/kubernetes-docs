# Datadog Quiz

A quiz to test your understanding of Datadog.

---

1. What is Datadog's primary deployment model?
   - A) Self-hosted only
   - B) SaaS (Software as a Service)
   - C) On-premises only
   - D) Hybrid required

<details>
<summary>Show Answer</summary>

**Answer: B) SaaS (Software as a Service)**

**Explanation:**
Datadog is a unified observability platform provided as a SaaS model. Users only need to deploy the Datadog Agent, while data storage, processing, and visualization are handled by Datadog's cloud infrastructure. This allows using powerful monitoring capabilities without operational overhead.

</details>

---

2. What is the role of Datadog Cluster Agent?
   - A) Container log collection
   - B) Cluster-level metrics and event collection
   - C) APM trace processing
   - D) Dashboard rendering

<details>
<summary>Show Answer</summary>

**Answer: B) Cluster-level metrics and event collection**

**Explanation:**
Datadog Cluster Agent collects cluster-level metrics and events from Kubernetes clusters. It also provides a custom metrics server role for HPA (Horizontal Pod Autoscaler) and automatic APM instrumentation injection through Admission Controller.

</details>

---

3. How do you enable automatic APM instrumentation in Datadog?
   - A) Application code modification required
   - B) Use Admission Controller and pod labels
   - C) Deploy separate APM server
   - D) Manually inject libraries

<details>
<summary>Show Answer</summary>

**Answer: B) Use Admission Controller and pod labels**

**Explanation:**
When Datadog Admission Controller is enabled, APM instrumentation libraries are automatically injected into pods with the `admission.datadoghq.com/enabled: "true"` label. It supports major languages including Java, Python, Node.js, .NET, and Ruby, allowing you to start tracing without code modifications.

</details>

---

4. What is the role of DogStatsD?
   - A) Log collection
   - B) Custom metrics collection (StatsD compatible)
   - C) Dashboard creation
   - D) Alert routing

<details>
<summary>Show Answer</summary>

**Answer: B) Custom metrics collection (StatsD compatible)**

**Explanation:**
DogStatsD is a StatsD-compatible metrics collection daemon included in the Datadog Agent. Applications can send custom metrics (counters, gauges, histograms, distributions) via UDP. It's compatible with the StatsD protocol with added tag functionality.

</details>

---

5. How do you connect traces and logs in Datadog?
   - A) Manually upload log files
   - B) Include trace_id and span_id in logs
   - C) Deploy separate connection service
   - D) Match log and trace timestamps

<details>
<summary>Show Answer</summary>

**Answer: B) Include trace_id and span_id in logs**

**Explanation:**
To connect traces and logs in Datadog, logs must include `dd.trace_id` and `dd.span_id`. Datadog APM libraries can automatically inject this information through MDC (Mapped Diagnostic Context). This allows viewing related logs directly from APM.

</details>

---

6. What is the billing unit for infrastructure monitoring in Datadog's cost structure?
   - A) Number of metrics
   - B) Number of hosts
   - C) Number of API calls
   - D) Data transfer volume

<details>
<summary>Show Answer</summary>

**Answer: B) Number of hosts**

**Explanation:**
Datadog infrastructure monitoring is billed based on the number of hosts. Each node, instance, and container host is a billable item. APM, log management, and other features have separate billing structures, with host-based billing making cost prediction easier.

</details>

---

7. What is the function of Datadog Watchdog?
   - A) Manual alert configuration
   - B) AI-based automatic anomaly detection
   - C) Log search
   - D) Dashboard creation

<details>
<summary>Show Answer</summary>

**Answer: B) AI-based automatic anomaly detection**

**Explanation:**
Watchdog is Datadog's AI/ML-based automatic anomaly detection feature. It automatically detects abnormal patterns in infrastructure, APM, and log data and generates alerts. You can identify anomalies without manually setting thresholds.

</details>

---

8. How do you collect Prometheus metrics with Datadog Agent?
   - A) Separate Prometheus server required
   - B) Configure auto-discovery with pod annotations
   - C) Manually register each endpoint
   - D) Replace Prometheus with Datadog

<details>
<summary>Show Answer</summary>

**Answer: B) Configure auto-discovery with pod annotations**

**Explanation:**
Datadog Agent uses `ad.datadoghq.com/<container>.checks` annotations to automatically discover and collect Prometheus metric endpoints. Configuration is similar to Prometheus scrape settings, and metrics can be collected without a separate Prometheus server.

</details>

---

9. What types of metrics can be used when setting up SLO (Service Level Objective) in Datadog?
   - A) Log events only
   - B) Metric-based, monitor-based, time slice-based
   - C) APM traces only
   - D) Infrastructure metrics only

<details>
<summary>Show Answer</summary>

**Answer: B) Metric-based, monitor-based, time slice-based**

**Explanation:**
Datadog SLO supports three types: metric-based (success/failure counts), monitor-based (existing monitor status), and time slice-based (status per time interval). Various data sources including APM traces, custom metrics, and log-based metrics can be utilized.

</details>

---

10. Which is NOT a valid Datadog cost optimization strategy?
    - A) Adjust APM trace sampling rate
    - B) Filter unnecessary logs
    - C) Collect all metrics at highest resolution
    - D) Manage custom metric cardinality

<details>
<summary>Show Answer</summary>

**Answer: C) Collect all metrics at highest resolution**

**Explanation:**
For Datadog cost optimization, APM trace sampling, log filtering, and custom metric cardinality management are important. Collecting all metrics at highest resolution causes costs to surge. Selectively collect only necessary metrics and apply appropriate sampling.

</details>
