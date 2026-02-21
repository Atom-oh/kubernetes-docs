# Prometheus Alertmanager Quiz

A quiz to test your understanding of Prometheus Alertmanager.

---

1. What is the intermediate state an alert goes through before firing in Alertmanager?
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>Show Answer</summary>

**Answer: B) Pending**

**Explanation:**
Prometheus alerts have three states: Inactive, Pending, and Firing. When an alert rule's condition (expr) is met, it first transitions to the Pending state, and if the condition persists for the duration specified in the `for` clause, it transitions to the Firing state and is sent to Alertmanager. This mechanism prevents unnecessary alerts from temporary spikes.

</details>

---

2. Which statement correctly describes the roles of `group_wait`, `group_interval`, and `repeat_interval` in Alertmanager's routing configuration?
   - A) group_wait: Wait time before sending the first notification of an alert group
   - B) group_interval: Interval for resending identical alerts
   - C) repeat_interval: Wait time when new alerts are added to a group
   - D) All perform the same function

<details>
<summary>Show Answer</summary>

**Answer: A) group_wait: Wait time before sending the first notification of an alert group**

**Explanation:**
- `group_wait`: Time to wait after a new alert group is created before sending the first notification. During this period, other alerts belonging to the same group are collected and sent together.
- `group_interval`: Time to wait before sending the next notification when new alerts are added to the same group.
- `repeat_interval`: Interval for resending the same alert when it hasn't been resolved yet.

</details>

---

3. Which statement correctly describes Alertmanager's Inhibition feature?
   - A) A feature to ignore all alerts for a specific period
   - B) A feature to suppress related alerts when a specific alert fires
   - C) A feature to automatically lower the severity of alerts
   - D) A feature to merge duplicate alerts

<details>
<summary>Show Answer</summary>

**Answer: B) A feature to suppress related alerts when a specific alert fires**

**Explanation:**
Inhibition is a feature that suppresses related alerts (target) when a specific condition alert (source) fires. For example, when a node goes down, all pod-related alerts from that node can be suppressed to prevent alert storms. Silencing is a separate feature that ignores alerts for a specific period.

</details>

---

4. What does the following alert rule in PrometheusRule CRD mean?
   ```yaml
   - alert: HighCPU
     expr: node_cpu_usage > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) Alert fires immediately when CPU usage exceeds 80%
   - B) Alert fires when CPU usage exceeds 80% for 5 minutes continuously
   - C) CPU usage is checked every 5 minutes and alert fires if over 80%
   - D) Alert notification is sent 5 minutes after CPU exceeds 80%

<details>
<summary>Show Answer</summary>

**Answer: B) Alert fires when CPU usage exceeds 80% for 5 minutes continuously**

**Explanation:**
The `for: 5m` setting means the alert condition (expr) must be met continuously for 5 minutes before transitioning to the Firing state. When the condition is first met, the state becomes Pending, and if it continues to be met for 5 minutes, it transitions to Firing and is sent to Alertmanager. This prevents unnecessary alerts from temporary spikes.

</details>

---

5. What does `send_resolved: true` mean in Alertmanager's receiver configuration?
   - A) Send resolved alerts to the receiver as well
   - B) Include resolution method in the alert message
   - C) Automatically change alert to resolved state
   - D) Grant receiver permission to resolve alerts

<details>
<summary>Show Answer</summary>

**Answer: A) Send resolved alerts to the receiver as well**

**Explanation:**
The `send_resolved: true` setting sends a resolution notification to the receiver when an alert is resolved (when the condition is no longer met). This allows responders to know that the problem has been resolved. The default value varies by receiver type, but enabling it is generally recommended.

</details>

---

6. What protocol is used to synchronize state between cluster members in Alertmanager high availability configuration?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>Show Answer</summary>

**Answer: C) Gossip**

**Explanation:**
Alertmanager clusters use the Gossip protocol to synchronize state between members. This allows Silence information and notification logs (nflog) to be shared across all instances, preventing duplicate alert notifications. When configuring a cluster, use the `--cluster.peer` flag to specify other members.

</details>

---

7. In the following Alertmanager routing configuration, which receiver will an alert with `severity=critical` and `team=infra` be sent to?
   ```yaml
   route:
     receiver: 'default'
     routes:
       - match:
           severity: critical
         receiver: 'critical-receiver'
       - match:
           team: infra
         receiver: 'infra-team'
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) Both critical-receiver and infra-team

<details>
<summary>Show Answer</summary>

**Answer: B) critical-receiver**

**Explanation:**
Alertmanager routing operates as a tree structure, and by default, processing ends at the first matching route. In this case, the `severity=critical` condition matches first, so the alert is sent to `critical-receiver`. To send to multiple routes, the `continue: true` setting is required.

</details>

---

8. What is the main purpose of the AlertmanagerConfig CRD?
   - A) Define Alertmanager's global configuration
   - B) Separate alert configuration by namespace
   - C) Define Prometheus alert rules
   - D) Configure Alertmanager cluster

<details>
<summary>Show Answer</summary>

**Answer: B) Separate alert configuration by namespace**

**Explanation:**
AlertmanagerConfig CRD is a resource provided by Prometheus Operator that allows managing Alertmanager configuration (receivers, routes, inhibition rules, etc.) separately by namespace. This allows each team to independently manage alert configuration in their own namespace.

</details>

---

9. Which is NOT an appropriate use case for creating a Silence in Alertmanager?
   - A) Suppress alerts during planned maintenance
   - B) Prevent repeated alerts from known issues
   - C) Permanently disable specific alerts
   - D) Suppress alerts during deployment

<details>
<summary>Show Answer</summary>

**Answer: C) Permanently disable specific alerts**

**Explanation:**
Silence is a feature that temporarily suppresses alerts and must always specify an end time. To permanently disable alerts, you need to modify or delete the alert rule itself. Main use cases for Silence are temporary situations such as maintenance, deployment, or investigating known issues.

</details>

---

10. Which of the following is NOT valid Go template syntax that can be used in Alertmanager templates?
    - A) `{{ .Labels.alertname }}`
    - B) `{{ if eq .Status "firing" }}Danger{{ end }}`
    - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
    - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>Show Answer</summary>

**Answer: D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

**Explanation:**
Go templates do not support the ternary operator (`? :`). Instead, you must use `{{ if }}` statements. The correct syntax would be:
```
{{ if gt (len .Annotations.description) 100 }}
  {{ slice .Annotations.description 0 100 }}...
{{ else }}
  {{ .Annotations.description }}
{{ end }}
```
Go templates support pipes (`|`), conditionals (`if`/`else`), loops (`range`), built-in functions, etc.

</details>

---

## Additional Learning Resources

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Prometheus Operator - AlertmanagerConfig](https://prometheus-operator.dev/docs/user-guides/alerting/)
