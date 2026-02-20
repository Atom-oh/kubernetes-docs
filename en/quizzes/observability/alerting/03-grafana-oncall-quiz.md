# Grafana OnCall Quiz

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
Grafana OnCall is an on-call management and incident response tool that provides the following features:
- On-call schedule management (rotations, overrides)
- Escalation chain configuration
- Alert grouping and routing
- ChatOps integration (Slack, MS Teams, Telegram)
- Mobile app notifications

Metric collection and storage is the role of other tools like Prometheus or Grafana Mimir. OnCall receives and processes alerts generated from these tools.

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
In escalation chains, the `wait` type sets a wait time between the current step and the next step. For example:
1. Step 1: Notify current on-call responder
2. Step 2: wait 900 seconds (15 minutes)
3. Step 3: If no response, notify secondary responder

This gives the primary responder time to respond, and escalation only proceeds if there is no response.

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
Override is a feature that temporarily changes the responder for a specific period in a regular on-call schedule. Main use cases:
- Responder replacement due to vacation
- Temporary change due to emergency situations
- Temporary swap due to training/meetings

Override designates a different responder for a specific period while maintaining the existing schedule.

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
Alertmanager and Grafana OnCall integration is done through webhooks:
```yaml
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
```

When Alertmanager fires an alert, it sends an HTTP POST request to the configured webhook URL, and OnCall receives and processes it.

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
Alert grouping manages multiple alerts caused by the same problem as a single group. For example, if multiple pod alerts occur due to a node failure, they are grouped together so the responder receives one grouped alert instead of dozens of individual alerts. A grouping key (e.g., alertname + namespace) is defined to determine which alerts are grouped together.

</details>

---

6. What happens when the `important` flag is true for `notify_on_call_from_schedule` in Grafana OnCall's escalation policy?
   - A) Alert is marked as highest priority
   - B) Alert is sent via all configured channels (phone, SMS, push, etc.)
   - C) Escalation chain is skipped and alert is sent immediately to supervisor
   - D) Alert is permanently stored

<details>
<summary>Show Answer</summary>

**Answer: B) Alert is sent via all configured channels (phone, SMS, push, etc.)**

**Explanation:**
The meaning of the `important` flag:
- `important: true`: Send alert via all notification channels configured by the user (phone, SMS, mobile push, Slack, etc.)
- `important: false`: Send alert via default channels only (e.g., Slack)

This allows adjusting alert intensity based on severity. Critical alerts can be set to important=true to include phone/SMS, while Warning can be set to important=false to use only Slack.

</details>

---

7. Which is NOT a command available when using Slack integration with Grafana OnCall?
   - A) /oncall ack (acknowledge alert)
   - B) /oncall resolve (resolve alert)
   - C) /oncall deploy (execute deployment)
   - D) /oncall silence 2h (silence for 2 hours)

<details>
<summary>Show Answer</summary>

**Answer: C) /oncall deploy (execute deployment)**

**Explanation:**
Grafana OnCall Slack commands:
- `/oncall` - Check current on-call responder
- `/oncall schedule` - View schedule
- `/oncall ack` - Acknowledge alert
- `/oncall resolve` - Resolve alert
- `/oncall silence 2h` - Silence for 2 hours
- `/oncall unsilence` - Remove silence
- `/oncall escalate` - Escalate alert

Deployment execution is not an OnCall feature. OnCall focuses on alert management and on-call management.

</details>

---

8. What is NOT an advantage of Grafana OnCall compared to PagerDuty/OpsGenie?
   - A) Open source and can be self-hosted
   - B) Native integration with Grafana stack
   - C) Support for 700+ integrations
   - D) Free to use (OSS version)

<details>
<summary>Show Answer</summary>

**Answer: C) Support for 700+ integrations**

**Explanation:**
700+ integrations is an advantage of PagerDuty. Comparison:
- **Grafana OnCall**: 30+ integrations, open source, self-hosting possible, Grafana native integration, free (OSS)
- **PagerDuty**: 700+ integrations, SaaS only, advanced analytics/reporting, AIOps features
- **OpsGenie**: 200+ integrations, SaaS only, Atlassian ecosystem integration

OnCall is a cost-effective choice for environments using the Grafana stack, but PagerDuty may be more suitable when diverse external system integrations are needed.

</details>

---

9. What is the recommended configuration for high availability in Grafana OnCall production deployment?
   - A) A single instance is sufficient
   - B) Increase API server and Celery worker replica counts and use external PostgreSQL/Redis
   - C) Distributed deployment across multiple clusters
   - D) Only add read-only replicas

<details>
<summary>Show Answer</summary>

**Answer: B) Increase API server and Celery worker replica counts and use external PostgreSQL/Redis**

**Explanation:**
Grafana OnCall Production HA configuration:
- **API server**: 3+ replicas, Pod Anti-Affinity settings
- **Celery workers**: 3+ replicas, Pod Anti-Affinity settings
- **PostgreSQL**: Use external managed DB (AWS RDS, etc.)
- **Redis**: Use external managed Redis (AWS ElastiCache, etc.)

This configuration eliminates single points of failure, allowing the service to continue operating even when individual components fail.

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
Routes connect incoming alerts to appropriate escalation chains based on their attributes (labels, severity, team, etc.):
- `severity=critical` -> Critical escalation chain (includes phone/SMS)
- `team=infra` -> Infrastructure team escalation chain
- `namespace=production` -> Production on-call schedule

Routing rules are defined using regular expressions and match based on the alert payload content. This allows applying appropriate responders and escalation policies for different alert types.

</details>

---

## Additional Learning Resources

- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)
