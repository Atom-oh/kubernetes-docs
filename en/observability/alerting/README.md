# Alerting Overview

> **Last Updated**: February 20, 2026

## Table of Contents

- [The Role and Importance of Alerting](#the-role-and-importance-of-alerting)
- [Alert Lifecycle](#alert-lifecycle)
- [Alert Design Principles](#alert-design-principles)
- [Alert Routing and Escalation](#alert-routing-and-escalation)
- [On-Call Rotation](#on-call-rotation)
- [Alerting Strategy for EKS Environments](#alerting-strategy-for-eks-environments)
- [Solution Comparison](#solution-comparison)

---

## The Role and Importance of Alerting

### Alerting's Position in the Three Pillars of Observability

Modern observability consists of three core pillars:

![Architecture diagram showing metrics, logs, and traces feeding a shared alert-rules engine that notifies and escalates to responders.](../../.gitbook/assets/en-observability-alerting-readme-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-0.html)

- **Metrics**: Quantitative state of the system (CPU, memory, request count, etc.)
- **Logs**: Detailed records of events
- **Traces**: Request flow in distributed systems

**Alerting** detects anomalies based on these three data sources and notifies the responsible personnel in a timely manner, enabling rapid response.

### Why Alerting is Necessary

1. **Proactive Problem Response**: Detect issues before users experience problems
2. **Minimize Downtime**: Improve service availability through fast detection and response
3. **Cost Reduction**: Reduce labor costs through automated monitoring
4. **SLA/SLO Compliance**: Essential component for achieving service level objectives
5. **Incident Recording**: Track and analyze problem occurrence history

### Good Alerts vs Bad Alerts

| Aspect | Good Alerts | Bad Alerts |
|--------|-------------|------------|
| **Actionability** | Requires immediate action | Information only, no action needed |
| **Clarity** | Clear what the problem is | Vague and unclear |
| **Urgency** | Urgency matches severity | Everything is urgent |
| **Frequency** | Appropriate frequency | Too frequent or too rare |
| **Duplication** | Related alerts grouped | Dozens of alerts for same issue |

---

## Alert Lifecycle

Alerts go through the following lifecycle:

![State machine showing an alert moving from inactive through pending, firing, notification, and acknowledgment to resolution, with early-return paths back to inactive.](../../.gitbook/assets/en-observability-alerting-readme-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-1.html)

### 1. Detection

- **Threshold-based**: When a specific value exceeds a configured threshold
- **Rate of change-based**: When the rate of change is abnormal
- **Anomaly detection**: Machine learning-based abnormal pattern detection
- **Log patterns**: When specific log patterns occur

```yaml
# Prometheus alert rule example
groups:
  - name: node-alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m  # Alert fires if condition persists for 5 minutes
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for 5 minutes on {{ $labels.instance }}"
```

### 2. Notification

- **Channel selection**: Slack, Email, SMS, PagerDuty, etc.
- **Routing**: Deliver to appropriate receivers based on alert type
- **Grouping**: Bundle related alerts together
- **Deduplication**: Prevent repeated sending of identical alerts

### 3. Escalation

- **Time-based**: Escalate to next responder if no response within specified time
- **Severity-based**: Different escalation paths based on severity
- **Automatic escalation**: Automatic escalation according to defined rules

![Flowchart showing an alert escalating every 15 minutes from the primary on-call through secondary and team-lead responders to a full-team page, until any responder acts.](../../.gitbook/assets/en-observability-alerting-readme-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-2.html)

### 4. Resolution

- **Manual resolution**: Responder closes alert after fixing the problem
- **Auto-resolution**: Automatically closes when metrics return to normal range
- **Resolution notification**: Send resolution notification when problem is fixed

---

## Alert Design Principles

### 1. Actionable Alerts

All alerts should enable the receiver to take immediate action.

**Bad example:**
```
Alert: Database connection count increased
```

**Good example:**
```
Alert: Database connection pool exhausted
Action Required: Scale up database or investigate connection leaks
Runbook: https://wiki.company.com/db-connection-exhausted
```

### 2. Preventing Alert Fatigue

Too many alerts can cause important alerts to be missed.

![Two reinforcing cycles: a vicious cycle where excessive alerts get ignored and cause missed incidents that add even more alerts, alongside a prevention cycle where refining alerts into better thresholds and grouping is sustained by regular review.](../../.gitbook/assets/en-observability-alerting-readme-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-3.html)

**Alert fatigue prevention strategies:**

1. **Threshold adjustment**: Don't set too sensitive thresholds
2. **Alert grouping**: Bundle related alerts into one
3. **Inhibition**: Suppress child alerts when parent alert fires
4. **Regular review**: Remove unnecessary alerts
5. **Gradual introduction**: Start new alerts with low severity first

### 3. Severity Levels

Define and follow a consistent severity system:

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **Critical** | Complete service outage | Immediate (within 5 min) | Full service down, data loss risk |
| **High** | Major function failure | Within 15 min | Payment system error, login failure |
| **Warning** | Potential problem | Within 1 hour | 80% disk usage, increased response latency |
| **Info** | Informational alert | Within business hours | Deployment complete, backup success |

```yaml
# Alert rules by severity example
groups:
  - name: disk-alerts
    rules:
      - alert: DiskSpaceCritical
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space critical"

      - alert: DiskSpaceWarning
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 20
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Disk space low"
```

### 4. Alert Documentation

All alerts should include the following information:

- **Description**: What the alert means
- **Impact**: How this problem affects the service
- **Action steps**: Step-by-step guide for resolving the problem
- **Runbook link**: Detailed response procedure document

```yaml
annotations:
  summary: "High memory usage on {{ $labels.instance }}"
  description: |
    Memory usage is above 90% on {{ $labels.instance }}.
    Current value: {{ $value | printf "%.2f" }}%
  impact: "Application may experience OOM kills and service degradation"
  action: |
    1. Check for memory leaks: kubectl top pods -n {{ $labels.namespace }}
    2. Review recent deployments
    3. Consider scaling horizontally
  runbook_url: "https://wiki.company.com/runbooks/high-memory"
```

---

## Alert Routing and Escalation

### Routing Strategy

Alerts should be delivered to appropriate receivers based on various criteria:

![Architecture diagram grouping Amazon EKS alerting targets into four areas: control plane (API server, etcd, scheduler/controller manager), data plane (node, pod, container status), networking (VPC CNI, Service/Ingress, CoreDNS), and storage (EBS/EFS CSI, PV/PVC).](../../.gitbook/assets/en-observability-alerting-readme-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-4.html)

### Routing Tree Design

```yaml
# Alertmanager routing configuration example
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # Critical alerts - immediate phone call
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true

    # Infrastructure team alerts
    - match_re:
        alertname: ^(Node|Disk|CPU|Memory).*
      receiver: 'sre-team'
      routes:
        - match:
            severity: critical
          receiver: 'sre-oncall'

    # Application team alerts
    - match_re:
        namespace: ^(app|api|web).*
      receiver: 'dev-team'

    # Database alerts
    - match_re:
        alertname: ^(MySQL|PostgreSQL|Redis|MongoDB).*
      receiver: 'dba-team'
```

### Escalation Policy

Set up time-based escalation policies to ensure alerts are not ignored:

| Step | Time | Target | Channel |
|------|------|--------|---------|
| 1 | 0 min | Primary on-call | Slack, PagerDuty |
| 2 | 15 min | Secondary on-call | Slack, PagerDuty, SMS |
| 3 | 30 min | Team Lead | Slack, PagerDuty, Phone |
| 4 | 45 min | Engineering Manager | Phone |
| 5 | 60 min | CTO/VP Engineering | Phone |

---

## On-Call Rotation

### On-Call Concept

On-call refers to a designated responder responsible for system issues during a specified period.

![Gantt chart showing four SRE engineers each taking a sequential seven-day on-call shift over four weeks.](../../.gitbook/assets/en-observability-alerting-readme-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-8.html)

![Flowchart showing an alert routed first by severity to a phone, PagerDuty, Slack, or email channel, then, for the three actionable severities, routed again by owning team to SRE, dev, DBA, or security.](../../.gitbook/assets/en-observability-alerting-readme-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-5.html)

### On-Call Best Practices

1. **Clear handoff schedule**: Weekly or bi-weekly rotation
2. **Handoff process**: Transfer ongoing issues during shift change
3. **Backup responder**: Backup when primary is unavailable
4. **Appropriate compensation**: On-call allowance or compensatory time off
5. **Burnout prevention**: Appropriate rotation cycle

### On-Call Tool Requirements

- **Schedule management**: Calendar integration, shift management
- **Override**: Temporary responder changes
- **Escalation**: Automatic escalation
- **Mobile support**: Receive alerts anytime, anywhere
- **Reporting**: On-call activity analysis

---

## Alerting Strategy for EKS Environments

### EKS-Specific Alerting Areas

![Flowchart guiding the choice of an alerting solution: whether on-call management is needed, then AWS-native preference or budget, ending at CloudWatch Alarms, Alertmanager, Grafana OnCall, PagerDuty, or OpsGenie.](../../.gitbook/assets/en-observability-alerting-readme-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-6.html)

### Alerting Strategy by Layer

#### 1. Cluster-Level Alerts

```yaml
# Cluster-level alert examples
groups:
  - name: eks-cluster
    rules:
      - alert: EKSAPIServerDown
        expr: up{job="kubernetes-apiservers"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "EKS API Server is down"

      - alert: EKSNodeNotReady
        expr: kube_node_status_condition{condition="Ready",status="true"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Node {{ $labels.node }} is not ready"

      - alert: EKSClusterAutoscalerError
        expr: cluster_autoscaler_errors_total > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cluster Autoscaler is experiencing errors"
```

#### 2. Workload-Level Alerts

```yaml
# Workload-level alert examples
groups:
  - name: eks-workloads
    rules:
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} is crash looping"

      - alert: PodNotReady
        expr: |
          sum by (namespace, pod) (
            kube_pod_status_phase{phase=~"Pending|Unknown"}
          ) > 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} has been pending for 15 minutes"

      - alert: DeploymentReplicasMismatch
        expr: |
          kube_deployment_spec_replicas != kube_deployment_status_replicas_available
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Deployment {{ $labels.deployment }} has replica mismatch"
```

#### 3. Resource-Level Alerts

```yaml
# Resource-level alert examples
groups:
  - name: eks-resources
    rules:
      - alert: ContainerCPUThrottling
        expr: |
          rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0.25
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} is being CPU throttled"

      - alert: ContainerMemoryNearLimit
        expr: |
          (container_memory_working_set_bytes / container_spec_memory_limit_bytes) > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} memory usage is near limit"

      - alert: PVCAlmostFull
        expr: |
          (kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes) > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PVC {{ $labels.persistentvolumeclaim }} is almost full"
```

### AWS Service Integration Alerts

EKS integrates with various AWS services, so alerts for these are also needed:

| AWS Service | Monitoring Items | Alert Tool |
|-------------|------------------|------------|
| EKS Control Plane | API Server availability, authentication errors | CloudWatch |
| EC2 (Nodes) | Instance status, system checks | CloudWatch |
| EBS | Volume status, IOPS usage | CloudWatch |
| EFS | Throughput, connection count | CloudWatch |
| ALB/NLB | Request count, error rate, latency | CloudWatch |
| VPC | Network traffic, NAT Gateway | CloudWatch/VPC Flow Logs |

---

## Solution Comparison

### Major Alerting Solution Comparison Table

| Feature | Alertmanager | CloudWatch Alarms | Grafana OnCall | PagerDuty | OpsGenie |
|---------|--------------|-------------------|----------------|-----------|----------|
| **Type** | Open Source | AWS Native | Open Source/SaaS | SaaS | SaaS |
| **Cost** | Free | Per-alarm pricing | Free/Paid | Paid | Paid |
| **EKS Integration** | Prometheus integration | Native | Alertmanager integration | Various integrations | Various integrations |
| **On-Call Management** | None | None | Yes | Yes | Yes |
| **Escalation** | Basic | None | Yes | Advanced | Advanced |
| **Mobile App** | None | None | Yes | Yes | Yes |
| **ChatOps** | Webhook | SNS | Slack, Teams | Various | Various |
| **Complexity** | Medium | Low | Medium | Low | Low |

### Solution Selection Guide

#### Recommended Solutions by Situation

1. **Small team, cost-conscious**: Alertmanager + Slack
2. **All-in AWS environment**: CloudWatch Alarms + SNS + Lambda
3. **Mid-size, need on-call**: Grafana OnCall
4. **Large organization, complex escalation**: PagerDuty
5. **Atlassian ecosystem**: OpsGenie

### Hybrid Approach

Most production environments use a combination of solutions:

![Architecture diagram of a hybrid alerting pipeline: Prometheus and CloudWatch feed Alertmanager, which routes to Grafana OnCall and PagerDuty for on-call management, fanning out to Slack, email, and SMS notification channels.](../../.gitbook/assets/en-observability-alerting-readme-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-readme-7.html)

**Recommended Architecture:**

1. **Prometheus + Alertmanager**: Metric collection and primary alert processing
2. **CloudWatch**: AWS service metric collection
3. **Grafana OnCall or PagerDuty**: On-call management and escalation
4. **Slack**: Real-time alerts and collaboration

---

## Next Steps

This section covered the basic concepts and strategies of alerting. For detailed configuration methods for each solution, refer to the following documents:

- [Prometheus Alertmanager](./01-alertmanager.md): Open source alert management
- [CloudWatch Alarms](./02-cloudwatch-alarms.md): AWS native alerting
- [Grafana OnCall](./03-grafana-oncall.md): On-call and incident management

---

## References

- [Prometheus Alerting Best Practices](https://prometheus.io/docs/practices/alerting/)
- [Google SRE Book - Practical Alerting](https://sre.google/sre-book/practical-alerting/)
- [AWS CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [PagerDuty Operations Guide](https://www.pagerduty.com/resources/operations/)
