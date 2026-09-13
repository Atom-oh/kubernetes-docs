# Observability Lab Part5 Alerting and AIOps Quiz

<span id="observability-lab-part-5-alerting-and-aiops-quiz"></span>

> **Last Updated**: September 13, 2026

1. Which component evaluates PrometheusRule alerts?
   - A) Alertmanager
   - B) Prometheus
   - C) SNS
   - D) The Lambda DLQ

<details>
<summary>Show answer</summary>

**Answer: B) Prometheus**

Prometheus evaluates; Alertmanager handles grouping, routing and notification.

</details>

---

2. What do DatapointsToAlarm=2 and EvaluationPeriods=3 mean?
   - A) Exactly two consecutive breaches are required.
   - B) Two of three evaluated datapoints must breach; they need not be consecutive.
   - C) Two notifications every three seconds.
   - D) Use two Regions.

<details>
<summary>Show answer</summary>

**Answer: B) Two of three evaluated datapoints must breach; they need not be consecutive.**

Period is metric aggregation granularity, not a synonym for evaluation frequency.

</details>

---

3. What matters when evaluating the old Grafana OnCall OSS installation step?
   - A) It has perpetual support.
   - B) Account for archival and Cloud Connection termination on 2026-03-24.
   - C) SMS support is always free forever.
   - D) Applying arbitrary YAML makes it operational.

<details>
<summary>Show answer</summary>

**Answer: B) Account for archival and Cloud Connection termination on 2026-03-24.**

Validate a supported incident/notification path and actual delivery for the organization.

</details>

---

4. Why separate the SNS input and output topics?
   - A) To change metric units.
   - B) To prevent the reporter from processing its own results in a loop.
   - C) Because SNS supports only one topic.
   - D) To publish logs publicly.

<details>
<summary>Show answer</summary>

**Answer: B) To prevent the reporter from processing its own results in a loop.**

Constrain subscriptions and IAM publish permissions to the same boundary.

</details>

---

5. What must the parser account for with Alertmanager `{{ . | toJson }}` output?
   - A) It is always plain text.
   - B) Capitalized template Data fields versus lowercase webhook fields.
   - C) JSON never needs parsing.
   - D) All SNS messages have identical fields.

<details>
<summary>Show answer</summary>

**Answer: B) Capitalized template Data fields versus lowercase webhook fields.**

The actual0.34.0 template serialization and valid/invalid payloads were tested.

</details>

---

6. How should absent metrics or failed queries be reported?
   - A) Convert them to zero errors.
   - B) Label missing/no_data/error instead of inventing measurements.
   - C) Present query strings as measured values.
   - D) Always report healthy status.

<details>
<summary>Show answer</summary>

**Answer: B) Label missing/no_data/error instead of inventing measurements.**

The model call can be skipped when evidence is insufficient.

</details>

---

7. What does Powertools idempotency provide in this sample?
   - A) End-to-end exactly-once SNS delivery.
   - B) Suppresses repeated successful work for the same message ID within24hours.
   - C) Every new message ID is the same operation.
   - D) Atomically combines publication and the DB commit.

<details>
<summary>Show answer</summary>

**Answer: B) Suppresses repeated successful work for the same message ID within24hours.**

Distinguish the publish/commit duplicate window and SNS/Lambda retry layers.

</details>

---

8. How is a Converse diagnostic response accepted?
   - A) Any response is success.
   - B) Set maxTokens and require end_turn with nonempty text.
   - C) A max_tokens stop is a completed diagnosis.
   - D) Immediately execute model-generated commands.

<details>
<summary>Show answer</summary>

**Answer: B) Set maxTokens and require end_turn with nonempty text.**

The reporter creates hypotheses for human review and has no remediation tools.

</details>

---

9. How is an alarm configured to initiate CloudWatch Investigations?
   - A) Call list-dashboards.
   - B) Add the prepared investigation-group ARN as an alarm action.
   - C) Only call put-insight-rule.
   - D) Only enable Application Signals discovery.

<details>
<summary>Show answer</summary>

**Answer: B) Add the prepared investigation-group ARN as an alarm action.**

Prepare the group, permissions, retention, encryption and actual alarm action.

</details>

---

10. Does calling multiple analysis modules implement the A2A protocol?
   - A) Two functions automatically implement A2A.
   - B) No; discovery, authentication and task/message contracts require separate implementation.
   - C) SNS always implies A2A.
   - D) DynamoDB alone is enough.

<details>
<summary>Show answer</summary>

**Answer: B) No; discovery, authentication and task/message contracts require separate implementation.**

Specialist decomposition is a design pattern, distinct from conformance to an agent protocol.

</details>

---

[Return to the guide](../../../labs/observability/05-alerting-aiops-lab.md)
