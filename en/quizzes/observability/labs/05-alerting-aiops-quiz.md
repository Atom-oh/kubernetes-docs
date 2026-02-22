# Observability Lab Part 5: Alerting and AIOps Quiz

> **Last Updated**: February 2025

Test your understanding of alerting and AIOps concepts covered in the Observability End-to-End Lab Part 5.

---

1. What does the `for` field in an Alertmanager PrometheusRule specify?
   - A) The time between alert evaluations
   - B) The duration a condition must remain true before the alert fires, transitioning from pending to firing state
   - C) How long the alert stays active after the condition clears
   - D) The maximum alert lifetime before automatic resolution

<details>
<summary>Show Answer</summary>

**Answer: B) The duration a condition must remain true before the alert fires, transitioning from pending to firing state**

**Explanation:**
The `for` field sets a duration threshold for alert firing. When the alert condition becomes true, the alert enters "pending" state. Only if the condition remains true for the entire `for` duration does the alert transition to "firing" and trigger notifications. This prevents alerting on brief transient spikes. For example, `for: 5m` means the condition must be true for 5 continuous minutes before alerting, reducing noise from momentary fluctuations.

</details>

---

2. How does Alertmanager's routing tree determine which receiver handles an alert?
   - A) Alerts are randomly distributed across receivers
   - B) Routes are evaluated top-to-bottom; alerts match based on labels and are sent to the first matching route's receiver, with child routes for more specific matching
   - C) All receivers get all alerts simultaneously
   - D) Routes are selected based on alert severity score

<details>
<summary>Show Answer</summary>

**Answer: B) Routes are evaluated top-to-bottom; alerts match based on labels and are sent to the first matching route's receiver, with child routes for more specific matching**

**Explanation:**
Alertmanager's routing tree is hierarchical. The root route catches all alerts, then child routes use `match` or `match_re` on alert labels to filter. Routes can have nested children for increasingly specific matching. By default, alerts match the first route they satisfy, but `continue: true` allows matching multiple routes. This enables sophisticated routing: critical alerts to PagerDuty, warnings to Slack, team-specific alerts to different channels, all based on labels like `severity`, `team`, or `service`.

</details>

---

3. How does a Grafana OnCall Escalation Chain work?
   - A) It randomly selects a team member to notify
   - B) It defines a sequence of notification steps with wait times, escalating through different users or groups until someone acknowledges the alert
   - C) It only sends email notifications
   - D) Escalation chains are only for calendar management

<details>
<summary>Show Answer</summary>

**Answer: B) It defines a sequence of notification steps with wait times, escalating through different users or groups until someone acknowledges the alert**

**Explanation:**
Grafana OnCall Escalation Chains define the incident response workflow: Step 1 might notify the on-call engineer via Slack and phone, wait 5 minutes, then Step 2 escalates to the backup engineer, wait 10 minutes, then Step 3 pages the team lead. Each step can use different notification channels (Slack, SMS, phone call, email) and target different users or schedules. The chain stops when someone acknowledges, preventing alert fatigue while ensuring coverage.

</details>

---

4. What do the evaluation period and datapoints settings control in CloudWatch Alarms?
   - A) They control the alarm name and description
   - B) Evaluation period sets how often metrics are checked; datapoints-to-alarm specifies how many periods must breach the threshold to trigger the alarm
   - C) They only affect alarm visualization in dashboards
   - D) These settings are deprecated in favor of metric math

<details>
<summary>Show Answer</summary>

**Answer: B) Evaluation period sets how often metrics are checked; datapoints-to-alarm specifies how many periods must breach the threshold to trigger the alarm**

**Explanation:**
CloudWatch Alarms use two key settings: Period (evaluation period) defines the time granularity for metric aggregation (e.g., 1 minute, 5 minutes), and "Datapoints to Alarm" specifies how many of the last N periods must exceed the threshold. For example, "3 out of 5" with 1-minute periods means the alarm triggers if 3 of the last 5 minutes exceeded the threshold. This combination allows tuning between responsiveness and noise reduction.

</details>

---

5. How does CloudWatch Investigations perform AI-based root cause analysis?
   - A) It only provides static runbooks
   - B) It analyzes correlated metrics, logs, and traces using ML models to identify anomalies and suggest potential root causes with supporting evidence
   - C) It requires manual investigation trigger for each incident
   - D) It only works with EC2 instances

<details>
<summary>Show Answer</summary>

**Answer: B) It analyzes correlated metrics, logs, and traces using ML models to identify anomalies and suggest potential root causes with supporting evidence**

**Explanation:**
CloudWatch Investigations (part of Amazon CloudWatch Application Signals) uses machine learning to automatically investigate issues. When triggered by an alarm or manually, it correlates telemetry signals across metrics, logs, and traces to identify anomalies coinciding with the incident. It analyzes related resources, detects patterns, and presents findings with confidence scores and evidence links. This accelerates mean-time-to-diagnosis by surfacing relevant data that humans might miss when manually investigating.

</details>

---

6. In what order does a Lambda-based AIOps Agent typically collect telemetry for incident analysis?
   - A) Logs first, then metrics, then traces sequentially
   - B) Telemetry collection happens in parallel for metrics, logs, and traces to minimize total collection time
   - C) Only traces are collected; metrics and logs are ignored
   - D) Collection order is random and unpredictable

<details>
<summary>Show Answer</summary>

**Answer: B) Telemetry collection happens in parallel for metrics, logs, and traces to minimize total collection time**

**Explanation:**
An effective AIOps agent collects telemetry in parallel to minimize latency. When an incident triggers the Lambda function, it concurrently queries: Prometheus/AMP for metrics (error rates, latency), Loki/CloudWatch for relevant logs (error messages, stack traces), and Tempo/X-Ray for distributed traces (request flows, bottlenecks). Parallel collection ensures the agent has comprehensive context quickly, enabling faster AI analysis and response. This is implemented using async/await patterns or concurrent API calls.

</details>

---

7. What are key principles for designing a system prompt when using Bedrock Claude as an SRE expert?
   - A) Make the prompt as short as possible
   - B) Define the role clearly, provide context about the system architecture, specify output format, and include domain-specific knowledge about common failure patterns
   - C) System prompts should only contain generic instructions
   - D) Avoid mentioning specific technologies in the prompt

<details>
<summary>Show Answer</summary>

**Answer: B) Define the role clearly, provide context about the system architecture, specify output format, and include domain-specific knowledge about common failure patterns**

**Explanation:**
Effective SRE system prompts include: clear role definition ("You are an SRE expert analyzing Kubernetes incidents"), system context (architecture, tech stack, typical issues), structured output format (hypothesis, evidence, recommended actions, runbook links), and domain knowledge (common failure patterns, escalation criteria, service dependencies). Including examples of past incidents and resolutions improves response quality. The prompt should guide the model to provide actionable, specific recommendations rather than generic advice.

</details>

---

8. How does an Alertmanager webhook connect to API Gateway and Lambda for automated incident response?
   - A) Lambda directly receives Alertmanager alerts via SDK
   - B) Alertmanager sends POST requests to an API Gateway HTTP endpoint, which triggers a Lambda function with the alert payload for processing
   - C) API Gateway polls Alertmanager for new alerts
   - D) The connection requires a dedicated EC2 instance as proxy

<details>
<summary>Show Answer</summary>

**Answer: B) Alertmanager sends POST requests to an API Gateway HTTP endpoint, which triggers a Lambda function with the alert payload for processing**

**Explanation:**
The integration flow: Alertmanager's webhook receiver is configured with an API Gateway endpoint URL. When alerts fire, Alertmanager POSTs JSON payloads containing alert details (labels, annotations, status, timestamps) to this endpoint. API Gateway receives the request and triggers an integrated Lambda function, passing the alert payload as the event. The Lambda function processes the alert—enriching with context, running AI analysis, triggering remediations, or forwarding to incident management systems.

</details>

---

9. How can you trigger a HighLatency alert using Fault Injection for testing alert pipelines?
   - A) Manually edit alert status in Alertmanager
   - B) Inject artificial latency into service responses using tools like Chaos Mesh, Litmus, or application-level fault injection, causing latency metrics to exceed alert thresholds
   - C) Directly modify Prometheus metric values
   - D) Fault injection cannot trigger Prometheus alerts

<details>
<summary>Show Answer</summary>

**Answer: B) Inject artificial latency into service responses using tools like Chaos Mesh, Litmus, or application-level fault injection, causing latency metrics to exceed alert thresholds**

**Explanation:**
Fault injection validates alerting pipelines end-to-end. Tools like Chaos Mesh or Litmus can inject network latency at the pod or service level. Application-level injection might add sleep delays to handlers. When injected latency causes metrics (e.g., `histogram_quantile(0.99, http_request_duration_seconds_bucket)`) to exceed thresholds defined in PrometheusRules, alerts fire naturally through the pipeline. This tests that metrics collection, alert rules, Alertmanager routing, and notification delivery all work correctly.

</details>

---

10. What role does a Collaborator Agent play in the A2A (Agent-to-Agent) pattern for AIOps?
    - A) It replaces human operators entirely
    - B) It acts as a specialized agent that the primary agent can delegate subtasks to, such as querying specific data sources, executing remediation actions, or providing domain expertise
    - C) It only handles logging and monitoring
    - D) Collaborator agents are identical copies of the primary agent

<details>
<summary>Show Answer</summary>

**Answer: B) It acts as a specialized agent that the primary agent can delegate subtasks to, such as querying specific data sources, executing remediation actions, or providing domain expertise**

**Explanation:**
In A2A patterns, a primary agent (orchestrator) coordinates with specialized collaborator agents. For AIOps: a Metrics Agent queries Prometheus/CloudWatch, a Logs Agent searches and analyzes log data, a Traces Agent investigates distributed traces, a Remediation Agent executes safe recovery actions, and a Knowledge Agent retrieves runbooks and past incident data. The primary agent synthesizes collaborator outputs into coherent incident analysis. This division enables specialized prompts, parallel execution, and separation of concerns, improving overall system capability.

</details>
