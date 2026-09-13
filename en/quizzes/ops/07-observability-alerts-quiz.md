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
CPU throttling can occur when available CFS quota is exhausted; interpret it with the workload's quota and performance context. The `container_cpu_cfs_throttled_seconds_total` metric tracks time spent throttled. A positive rate indicates active throttling that may impact application performance.

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

### 3. Which metric helps observe a Kubernetes Node's readiness?

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` with condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>Show Answer</summary>

**Answer: B) `kube_node_status_condition` with condition="Ready"**

**Explanation:**
The Ready condition reports readiness of an observed Node. False or unknown can have several causes and does not prove termination or replacement. Correlate inventory, Node/NodeClaim conditions and actual events/audit logs.

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
continue: true allows matching subsequent sibling routes. If a child already matched, the root receiver is not automatically a fallback. Test the complete tree, including critical alerts without a matching team route.

</details>

### 9. Which expression helps measure network transmit throughput?

- A) `container_cpu_usage_seconds_total`
- B) `rate(node_network_transmit_bytes_total[5m])` with units matched to the actual capacity contract
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>Show Answer</summary>

**Answer: B) `rate(node_network_transmit_bytes_total[5m])` with units matched to the actual capacity contract**

**Explanation:**
`node_network_transmit_bytes_total` and `node_network_receive_bytes_total` track network I/O. The rate is bytes/s; multiply by eight for bits/s and compare with verified baseline/burst and path limits. The cumulative counter alone, an advertised virtual-NIC speed, or an assumed universal 10Gbps limit does not establish saturation.

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
Inhibition suppresses matching notifications according to configured source/target matchers and equal labels. It does not automatically establish root cause. Require nonempty cluster/entity identifiers so missing labels do not suppress unrelated alerts; Prometheus evaluation continues.

</details>
