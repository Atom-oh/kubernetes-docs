# Prometheus Alertmanager Quiz

> **Last Updated**: September 13, 2026

---

1. When a Prometheus alert rule has a positive `for` duration, which state precedes Firing?
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>Show Answer</summary>

**Answer: B) Pending**

Pending belongs to Prometheus rule evaluation, not an Alertmanager evaluation stage. The condition must remain present at successive evaluations for the configured duration. With no `for` (or zero), it can fire at the first matching evaluation. Notification grouping adds separate delays; `keep_firing_for` can retain Firing after the expression stops matching.

</details>

---

2. Which statement about grouping timers is correct?
   - A) `group_wait` delays the first notification for a new group.
   - B) `group_interval` is only the repeat interval for unchanged alerts.
   - C) `repeat_interval` is the first delay for newly added alerts.
   - D) All three timers are identical.

<details>
<summary>Show Answer</summary>

**Answer: A) `group_wait` delays the first notification for a new group.**

`group_interval` schedules subsequent group checks, including changes and resolved alerts. `repeat_interval` controls repeat notifications for unchanged firing alerts, checked on group intervals; use a multiple of `group_interval`. Notification-log retention can cause an earlier repeat. These timers are independent of a Prometheus rule’s `for`.

</details>

---

3. What does inhibition do?
   - A) Ignore every alert for a time window.
   - B) Suppress matching target notifications while a matching source alert is active.
   - C) Change the alert severity automatically.
   - D) Delete duplicate alerts from Prometheus.

<details>
<summary>Show Answer</summary>

**Answer: B) Suppress matching target notifications while a matching source alert is active.**

Inhibition changes notification eligibility, not the underlying alert condition. Source/target matchers and equality labels must represent the intended dependency. Missing equality labels compare like empty values, so require non-empty correlation labels such as `cluster` and `node` to avoid suppressing unrelated alerts. Rule-list order is not a priority system.

</details>

---

4. What does this rule’s `for` mean?

   ```yaml
   - alert: HighCPU
     expr: 100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) Notify immediately when CPU exceeds 80%.
   - B) Enter Firing after the condition persists for five minutes across evaluations.
   - C) Evaluate CPU only once every five minutes.
   - D) Guarantee delivery exactly five minutes after the physical CPU increase.

<details>
<summary>Show Answer</summary>

**Answer: B) Enter Firing after the condition persists for five minutes across evaluations.**

This assumes scraped node-exporter CPU counters and an appropriate evaluation interval. `for` does not set the scrape/evaluation interval or guarantee a delivery deadline. A changed label set identifies a different alert; recovery resets Pending unless separate firing-retention behavior applies.

</details>

---

5. What does `send_resolved: true` enable?
   - A) Resolution notifications for that integration.
   - B) Automatic remediation instructions.
   - C) Changing the alert condition to healthy.
   - D) Permission for the receiver to repair the cluster.

<details>
<summary>Show Answer</summary>

**Answer: A) Resolution notifications for that integration.**

It controls resolved notifications for the chosen integration; defaults differ by receiver. Resolved is an alert lifecycle state, not independent proof that a service recovered. Expression changes, missing data or client update/expiry behavior can also affect that state.

</details>

---

6. Which protocol is used for Alertmanager cluster state synchronization?
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>Show Answer</summary>

**Answer: C) Gossip**

Gossip shares silences and notification-log state with eventual consistency. Send the same alerts to every replica; the gossip layer does not replace that fan-out. Deduplication is best effort, and network partitions can produce duplicates. This is not exactly-once delivery or a guarantee against all notification loss.

</details>

---

7. For `severity=critical, team=infra`, which route is selected below?

   ```yaml
   route:
     receiver: default
     routes:
       - matchers: ['severity="critical"']
         receiver: critical-receiver
       - matchers: ['team="infra"']
         receiver: infra-team
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) Both child routes

<details>
<summary>Show Answer</summary>

**Answer: B) critical-receiver**

With default `continue: false`, the first matching sibling stops sibling traversal. Set `continue: true` on it to consider later siblings. This tests label routing only: an inactive/muted route can still stop traversal, so time-window behavior needs separate checks. Multiple integrations inside one receiver do not require `continue`.

</details>

---

8. What does namespace-owned AlertmanagerConfig enable?
   - A) Automatically bypass all namespace restrictions.
   - B) Manage structured routes/receivers selected by an Alertmanager instance.
   - C) Define PromQL recording and alert rules.
   - D) Replace gossip peer configuration.

<details>
<summary>Show Answer</summary>

**Answer: B) Manage structured routes/receivers selected by an Alertmanager instance.**

The Operator must select the object’s labels and namespace, and referenced Secrets must exist in the required namespace. Its matcher strategy controls namespace enforcement. The reviewed Operator 0.93.1 chart serves `v1alpha1`; do not invent a required API upgrade. Global-configuration use is a separate option, and namespace label matching is not authentication of alert senders.

</details>

---

9. Which is not an appropriate purpose for a Silence?
   - A) Planned maintenance.
   - B) A bounded investigation window.
   - C) Permanently disable an alert rule.
   - D) A reviewed deployment window.

<details>
<summary>Show Answer</summary>

**Answer: C) Permanently disable an alert rule.**

A silence requires a finite end time and affects notifications. Expiration ends suppression; it is not immediate deletion from stored silence history. Permanent rule/routing changes need separate review. Record the owner, reason and approved scope; expiry reminders need an explicitly configured workflow.

</details>

---

10. Which expression is invalid Go template syntax?
   - A) `{{ .CommonLabels.alertname }}`
   - B) `{{ if eq .Status "firing" }}Danger{{ end }}`
   - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
   - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>Show Answer</summary>

**Answer: D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

Go templates do not support this ternary expression. At the root, Alertmanager supplies Data with CommonLabels/CommonAnnotations; Labels/Annotations/StartsAt belong to an individual Alert inside `range .Alerts`. The example below formats at most 100 runes per description, avoiding a byte slice that could split Korean text. This is output formatting, not sensitive-data redaction.

```text
{{ range .Alerts }}
{{ printf "%.100s" .Annotations.description }}
{{ end }}
```

</details>

---

## Additional Learning Resources

- [Alertmanager 0.34 configuration](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md)
- [Notification template reference](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/notifications.md)
- [Prometheus Operator alerting](https://prometheus-operator.dev/docs/developer/alerting/)

[Return to the guide](../../../observability/alerting/01-alertmanager.md)
