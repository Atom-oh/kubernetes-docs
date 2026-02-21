# Observability Alerts Quiz

> **Related Document**: [Observability Alerts](../../ops/07-observability-alerts.md)

## Multiple Choice Questions

### 1. What PromQL expression detects CPU throttling in containers?

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>Show Answer</summary>

**Answer: B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**Explanation:**
CPU throttling occurs when a container exceeds its CPU limit. The `container_cpu_cfs_throttled_seconds_total` metric tracks time spent throttled. A positive rate indicates active throttling that may impact application performance.

</details>

### 2. What is the purpose of Alertmanager's `group_by` configuration?

- A) To delete alerts
- B) To aggregate alerts with matching labels into single notifications
- C) To increase alert severity
- D) To route alerts to logs

<details>
<summary>Show Answer</summary>

**Answer: B) To aggregate alerts with matching labels into single notifications**

**Explanation:**
`group_by` combines multiple firing alerts that share specified label values into a single notification. This reduces alert fatigue during incidents that trigger many similar alerts (e.g., all pods in a deployment failing).

</details>

### 3. Which metric is most important for detecting EKS Auto Mode node termination?

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` with condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>Show Answer</summary>

**Answer: B) `kube_node_status_condition` with condition="Ready"**

**Explanation:**
Monitoring `kube_node_status_condition` for Ready=false detects nodes becoming unavailable. In Auto Mode, this indicates node termination or replacement. Combined with labels, you can track node lifecycle and replacement patterns.

</details>

### 4. What does `for` duration in a Prometheus alerting rule specify?

- A) How long to keep alerts in history
- B) How long a condition must be true before firing
- C) The alert evaluation interval
- D) Notification timeout

<details>
<summary>Show Answer</summary>

**Answer: B) How long a condition must be true before firing**

**Explanation:**
The `for` clause specifies the duration a condition must continuously be true before the alert transitions from "pending" to "firing." This prevents alerts on brief spikes and reduces false positives.

</details>

### 5. How should alert severity levels be defined?

- A) All alerts should be critical
- B) Based on business impact and required response time
- C) Randomly assigned
- D) Based on metric name

<details>
<summary>Show Answer</summary>

**Answer: B) Based on business impact and required response time**

**Explanation:**
Severity should reflect impact: critical for customer-facing outages requiring immediate response, warning for degradation needing attention within hours, and info for awareness without action. This enables appropriate routing and on-call escalation.

</details>

### 6. What PromQL function calculates the rate of increase over time?

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>Show Answer</summary>

**Answer: B) `rate()`**

**Explanation:**
`rate()` calculates the per-second average rate of increase over a time range. It's designed for counters and handles counter resets. For example, `rate(http_requests_total[5m])` gives requests per second averaged over 5 minutes.

</details>

### 7. What is the recommended approach for packet drop alerts?

- A) Alert on any single packet drop
- B) Alert when drop rate exceeds a threshold sustained over time
- C) Never alert on packet drops
- D) Only log packet drops

<details>
<summary>Show Answer</summary>

**Answer: B) Alert when drop rate exceeds a threshold sustained over time**

**Explanation:**
Occasional packet drops are normal in networks. Alerts should trigger on sustained elevated drop rates that indicate real issues. Using `rate()` over a window (e.g., 5m) with a threshold prevents alerts on transient spikes.

</details>

### 8. In Alertmanager routing, what does `continue: true` do?

- A) Stops processing further routes
- B) Allows the alert to match additional routes after the current one
- C) Repeats the alert notification
- D) Silences the alert

<details>
<summary>Show Answer</summary>

**Answer: B) Allows the alert to match additional routes after the current one**

**Explanation:**
By default, Alertmanager stops at the first matching route. Setting `continue: true` allows an alert to match multiple routes, enabling scenarios like sending critical alerts to both PagerDuty and Slack simultaneously.

</details>

### 9. What metric indicates network bandwidth exceeded on EKS nodes?

- A) `container_cpu_usage_seconds_total`
- B) `node_network_transmit_bytes_total` approaching instance network limits
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>Show Answer</summary>

**Answer: B) `node_network_transmit_bytes_total` approaching instance network limits**

**Explanation:**
`node_network_transmit_bytes_total` and `node_network_receive_bytes_total` track network I/O. Comparing the rate to EC2 instance network bandwidth limits helps identify when workloads are hitting network constraints.

</details>

### 10. What is the purpose of alert inhibition rules in Alertmanager?

- A) To increase alert priority
- B) To suppress dependent alerts when a parent alert is firing
- C) To route alerts to different receivers
- D) To create new alerts

<details>
<summary>Show Answer</summary>

**Answer: B) To suppress dependent alerts when a parent alert is firing**

**Explanation:**
Inhibition rules prevent alert storms by silencing downstream alerts when a root cause alert fires. For example, when "NodeDown" fires, inhibit all "PodNotReady" alerts for pods on that node since they're symptoms of the same issue.

</details>
