# Grafana Dashboard Quiz

> **Last Updated**: September 13, 2026

Test your understanding of Grafana 13.2.1 configuration and operation.

---

1. Which is NOT a method used for data source provisioning in Grafana?
   - A) ConfigMap with sidecar
   - B) Grafana API
   - C) Environment variables
   - D) provisioning directory

<details>
<summary>Show Answer</summary>

**Answer: C) Environment variables**

**Explanation:**
Grafana data sources can be provisioned through YAML files in the provisioning directory, sidecar approach using ConfigMaps, or the Grafana API. Environment variables can supply grafana.ini settings and values such as URLs or credentials inside data source provisioning YAML. Variables alone do not create a data source object.

</details>

---

2. What do 'R', 'E', 'D' stand for in the RED Method?
   - A) Resource, Error, Duration
   - B) Rate, Error, Duration
   - C) Request, Exception, Delay
   - D) Response, Event, Data

<details>
<summary>Show Answer</summary>

**Answer: B) Rate, Error, Duration**

**Explanation:**
The RED Method is a methodology for analyzing service-level metrics. It monitors three key metrics: Rate (request processing rate), Error (error rate), and Duration (response time). This is an effective framework for understanding microservice health.

</details>

---

3. What configuration is needed to implement trace-to-log correlation by connecting Tempo and Loki in Grafana?
   - A) Use the same database
   - B) Configure tracesToLogsV2 in Tempo data source
   - C) Install a separate plugin
   - D) Grafana Enterprise license

<details>
<summary>Show Answer</summary>

**Answer: B) Configure tracesToLogsV2 in Tempo data source**

**Explanation:**
Configuring the tracesToLogsV2 section in the Tempo data source settings allows direct navigation from traces to related logs. Specify Loki with datasourceUid and map actual trace attributes to Loki labels using tags. Log fields such as trace_id must match the pipeline contract. This is a built-in Grafana feature that doesn't require additional plugins.

</details>

---

4. What do 'U', 'S', 'E' stand for in the USE Method?
   - A) User, Service, Event
   - B) Utilization, Saturation, Errors
   - C) Uptime, Status, Exceptions
   - D) Usage, Speed, Efficiency

<details>
<summary>Show Answer</summary>

**Answer: B) Utilization, Saturation, Errors**

**Explanation:**
The USE Method is a methodology for analyzing system resources. It monitors Utilization, Saturation, and Errors. By analyzing these three metrics for each resource (CPU, memory, disk, network), you can identify bottlenecks.

</details>

---

5. What is the role of evaluation interval in Grafana Alerting?
   - A) Alert message delivery interval
   - B) Alert rule evaluation frequency
   - C) Data retention period
   - D) Dashboard refresh interval

<details>
<summary>Show Answer</summary>

**Answer: B) Alert rule evaluation frequency**

**Explanation:**
Evaluation interval determines how often alert rules are evaluated. For example, setting it to 1m checks conditions every minute. This affects alert sensitivity and resource usage. Too short increases resource usage; too long delays problem detection.

</details>

---

6. Which is NOT included in Google SRE's 4 Golden Signals?
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>Show Answer</summary>

**Answer: C) Availability**

**Explanation:**
The 4 Golden Signals are Latency, Traffic, Errors, and Saturation. Availability is an important metric but is not included in the 4 Golden Signals. Availability is related to Errors but is a separate concept.

</details>

---

7. What is the main benefit of using dashboard variables in Grafana?
   - A) Improved dashboard loading speed
   - B) Increased dashboard reusability through dynamic filtering
   - C) Reduced data storage capacity
   - D) Enhanced security

<details>
<summary>Show Answer</summary>

**Answer: B) Increased dashboard reusability through dynamic filtering**

**Explanation:**
Using dashboard variables allows monitoring multiple clusters, namespaces, and services with a single dashboard. When you select a value from the dropdown, all panel queries are dynamically updated. This reduces the number of dashboards and simplifies maintenance.

</details>

---

8. What is the role of the Exemplar feature when integrating Grafana with Prometheus?
   - A) Metric data compression
   - B) Linking metrics and trace data
   - C) Query caching
   - D) Data backup

<details>
<summary>Show Answer</summary>

**Answer: B) Linking metrics and trace data**

**Explanation:**
Exemplars link selected metric observations to TraceIDs; they do not capture every request. By storing sample TraceIDs in histogram or counter metrics, clicking a specific point on a metric graph in Grafana allows you to immediately query the trace data from that moment.

</details>

---

9. Which is a correct difference between Grafana Cloud and Self-hosted Grafana?
   - A) Grafana Cloud is free
   - B) Self-hosted cannot install plugins
   - C) Grafana Cloud is managed and its SLA depends on the contract
   - D) Self-hosted has data source limitations

<details>
<summary>Show Answer</summary>

**Answer: C) Grafana Cloud is managed and its SLA depends on the contract**

**Explanation:**
Check the actual Cloud plan and service agreement for its SLA, usage limits and features. Self-hosted operators manage databases, backups, upgrades and plugin compatibility/signature policy. Do not assume a fixed 99.9% SLA applies to every Cloud plan.

</details>

---

10. Which ConfigMap label does this chapter’s sidecar profile (label=grafana_dashboard, labelValue="true") select?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) grafana_dashboard: "true"**

**Explanation:**
This profile selects `grafana_dashboard: "true"`. Both label and labelValue are configurable rather than universal Grafana requirements. The optional profile watches only ConfigMaps in the monitoring namespace.

</details>

---
