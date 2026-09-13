# Grafana OnCall Quiz

> **Last Updated**: September 13, 2026

This quiz covers review/migration of archived OnCall OSS installations.

A quiz to test your understanding of Grafana OnCall.

---

1. Which is NOT a key feature of Grafana OnCall?
   - A) On-call schedule management
   - B) Escalation chain configuration
   - C) Metric collection and storage
   - D) ChatOps integration (Slack, Teams)

<details>
<summary>Show Answer</summary>

**Answer: C) Metric collection and storage**

**Explanation:**
OnCall receives and manages alerts, schedules, routing and responder actions; it is not a metrics database. OSS was archived on2026-03-24. Channel/API availability in an existing installation must be checked separately from maintained Cloud IRM.

</details>

---

2. What is the role of the `wait` type in Grafana OnCall's escalation policy?
   - A) Wait for data collection before sending alerts
   - B) Wait before proceeding to the next escalation step
   - C) Wait for user response then auto-resolve
   - D) Wait for alert grouping

<details>
<summary>Show Answer</summary>

**Answer: B) Wait before proceeding to the next escalation step**

**Explanation:**
A wait step delays the next escalation step. It neither acknowledges nor resolves an incident. The inspected public serializer accepts one-minute-to24-hour waits, in seconds; actual stop/re-page behavior depends on the chain and alert-group state.

</details>

---

3. What is an "Override" in Grafana OnCall's on-call schedule?
   - A) Completely deleting and recreating the schedule
   - B) Temporarily changing the responder for a specific period in the existing schedule
   - C) Changing the schedule's time zone
   - D) Modifying the rotation cycle

<details>
<summary>Show Answer</summary>

**Answer: B) Temporarily changing the responder for a specific period in the existing schedule**

**Explanation:**
An override changes coverage for a defined period. In the inspected API it is an on_call_shifts type, with an explicit timezone and the required association to the intended schedule. Verify existing shift IDs, priorities, gaps and final responders; do not assume the old nested overrides endpoint.

</details>

---

4. What method is used when integrating Grafana OnCall with Alertmanager?
   - A) Alertmanager directly collects OnCall's metrics
   - B) Send alerts to OnCall via Alertmanager's webhook_configs
   - C) OnCall periodically polls Alertmanager's API
   - D) Both systems share a database

<details>
<summary>Show Answer</summary>

**Answer: B) Send alerts to OnCall via Alertmanager's webhook_configs**

**Explanation:**
Use webhook_configs with the generated URL for the actual integration type, stored in a protected url_file when suitable. Define every referenced receiver and use current matchers. Public API raw-token authentication is separate from a webhook URL; send_resolved does not make OnCall update the source rule.

</details>

---

5. What is the main purpose of alert grouping in Grafana OnCall?
   - A) Sort alerts by time
   - B) Group related alerts into one to reduce alert fatigue
   - C) Classify alerts by severity
   - D) Automatically delete duplicate alerts

<details>
<summary>Show Answer</summary>

**Answer: B) Group related alerts into one to reduce alert fatigue**

**Explanation:**
Grouping can reduce duplicate responder work but must use a key scoped to the incident domain. Too few labels merge unrelated incidents; unbounded IDs fragment groups. Source Alertmanager timing and OnCall grouping/resolution templates are distinct, and delivery is not guaranteed exactly once.

</details>

---

6. What happens when the `important` flag is true for `notify_on_call_from_schedule` in Grafana OnCall's escalation policy?
   - A) Alert is marked as highest priority
   - B) The user's configured important notification-rule set is selected
   - C) Escalation chain is skipped and alert is sent immediately to supervisor
   - D) Alert is permanently stored

<details>
<summary>Show Answer</summary>

**Answer: B) The user's configured important notification-rule set is selected**

**Explanation:**
Important selects the user's important personal notification-rule set. The configured rule order, waits, channels and availability still apply. It does not automatically send through all channels; default rules are not universally Slack-only.

</details>

---

7. Which is the correct way to use Slack actions with an existing OnCall installation?
   - A) Assume every installation supports /oncall ack
   - B) Treat slash commands as Bash
   - C) Verify the installed app's commands, permissions and action buttons
   - D) Assume acknowledgment resolves the source monitor

<details>
<summary>Show Answer</summary>

**Answer: C) Verify the installed app's commands, permissions and action buttons**

**Explanation:**
Check the installed Slack app's actual root command/help and authorized action buttons. The inspected source uses a configurable root command and /grafana examples, not the old asserted /oncall command catalogue. Acknowledge, Resolve and Silence are distinct actions; deployment execution is not implied.

</details>

---

8. What is the appropriate basis for a new on-call tool or migration decision?
   - A) Choose only by old integration counts
   - B) Assume OSS has no operating cost
   - C) Check maintenance, required features, actual cost and migration/recovery
   - D) Install archived OnCall OSS by default

<details>
<summary>Show Answer</summary>

**Answer: C) Check maintenance, required features, actual cost and migration/recovery**

**Explanation:**
Use current maintenance/lifecycle, required features, operating cost and contracts. Fixed old integration counts or per-user prices are insufficient. OnCall OSS is archived; Opsgenie has an announced2027-04-05 service/support end. Review a maintained destination and test migration/recovery.

</details>

---

9. What must be verified for availability of an existing OnCall deployment?
   - A) Three API replicas guarantee availability
   - B) Dependencies, state, delivery, failure and recovery behavior
   - C) Only the number of clusters
   - D) Only a read-only database replica

<details>
<summary>Show Answer</summary>

**Answer: B) Dependencies, state, delivery, failure and recovery behavior**

**Explanation:**
Replica count alone does not remove every failure point. Existing installations require dependency, broker/cache/database, scheduler, key, TLS, delivery and recovery validation. Archived OSS is not a default new production choice; no HA deployment was exercised in this review.

</details>

---

10. What is the main purpose of setting up routes in Grafana OnCall?
    - A) Network traffic distribution
    - B) Apply different escalation chains based on alert conditions
    - C) Database query optimization
    - D) User authentication path configuration

<details>
<summary>Show Answer</summary>

**Answer: B) Apply different escalation chains based on alert conditions**

**Explanation:**
Routes select escalation/notification behavior using the integration's actual payload, matching mode, ordering and fallback. The inspected serializer uses nested slack.channel_id/enabled. Test missing/conflicting fields; arbitrary message-text regex matching is not a universal provider contract.

</details>

---

## Additional Learning Resources

- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana-cold-storage/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana-cold-storage/oncall/tree/af0fbd40558c9a63bcf438589894c440fc434a54/helm/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)

- [Guide](../../../observability/alerting/03-grafana-oncall.md)
