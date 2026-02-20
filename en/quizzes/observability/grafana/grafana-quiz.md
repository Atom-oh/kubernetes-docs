# Grafana Dashboard Quiz

Test your understanding of Grafana.

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
Grafana data sources can be provisioned through YAML files in the provisioning directory, sidecar approach using ConfigMaps, or the Grafana API. Environment variables are used for Grafana configuration (grafana.ini) but are not used to directly define data sources.

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
   - B) Configure tracesToLogs in Tempo data source
   - C) Install a separate plugin
   - D) Grafana Enterprise license

<details>
<summary>Show Answer</summary>

**Answer: B) Configure tracesToLogs in Tempo data source**

**Explanation:**
Configuring the tracesToLogs section in the Tempo data source settings allows direct navigation from traces to related logs. Specify Loki with datasourceUid and set labels for connection using tags. This is a built-in Grafana feature that doesn't require additional plugins.

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
Exemplar is a feature that links TraceIDs to Prometheus metrics. By storing sample TraceIDs in histogram or counter metrics, clicking a specific point on a metric graph in Grafana allows you to immediately query the trace data from that moment.

</details>

---

9. Which is a correct difference between Grafana Cloud and Self-hosted Grafana?
   - A) Grafana Cloud is free
   - B) Self-hosted cannot install plugins
   - C) Grafana Cloud provides automatic scaling and SLA
   - D) Self-hosted has data source limitations

<details>
<summary>Show Answer</summary>

**Answer: C) Grafana Cloud provides automatic scaling and SLA**

**Explanation:**
Grafana Cloud is a managed service providing automatic scaling, 99.9% SLA, automatic updates, etc. Self-hosted offers complete control and allows all plugin installations but requires infrastructure management. Both options support various data sources.

</details>

---

10. What label is required on a ConfigMap when using sidecar for Grafana dashboard provisioning?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) grafana_dashboard: "true"**

**Explanation:**
When using the Grafana Helm chart's sidecar feature, you need to add the `grafana_dashboard: "true"` label to ConfigMaps containing dashboard JSON. The sidecar container watches ConfigMaps with this label and automatically provisions dashboards.

</details>

---
