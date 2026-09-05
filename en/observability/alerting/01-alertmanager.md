# Prometheus Alertmanager

> **Supported Versions**: Alertmanager 0.27.x
> **Last Updated**: February 20, 2026

## Table of Contents

- [Alertmanager Overview](#alertmanager-overview)
- [Architecture](#architecture)
- [Installation and Configuration](#installation-and-configuration)
- [Defining Alert Rules](#defining-alert-rules)
- [Routing Configuration](#routing-configuration)
- [Receiver Configuration](#receiver-configuration)
- [Inhibition Rules](#inhibition-rules)
- [Silencing](#silencing)
- [Template Customization](#template-customization)
- [High Availability Configuration](#high-availability-configuration)
- [AlertmanagerConfig CRD](#alertmanagerconfig-crd)
- [Production Alert Rule Examples](#production-alert-rule-examples)
- [Troubleshooting](#troubleshooting)

---

## Alertmanager Overview

Prometheus Alertmanager is a component that processes alerts sent from Prometheus servers. It provides features such as deduplication, grouping, routing, inhibition, and silencing of alerts.

### Key Features

1. **Grouping**: Bundle similar alerts into one notification
2. **Inhibition**: Suppress related alerts when specific alerts fire
3. **Silencing**: Ignore alerts for a specific period
4. **Routing**: Deliver alerts to appropriate receivers
5. **High Availability**: Redundancy through clustering

### Prometheus Alert Flow

![Sequence diagram showing Prometheus evaluating an alert rule through Pending to Firing, posting it to Alertmanager, which runs deduplication, grouping, routing and inhibition/silence checks before notifying a receiver that returns a delivery result.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-0.html)

---

## Architecture

### Alertmanager Internal Structure

![Alerts from Prometheus enter the Alertmanager API, pass through the Dispatcher, Inhibitor, Silencer, Aggregation Group and Notification Pipeline to receivers, while the Gossip Protocol syncs the Silences and nflog stores across cluster nodes.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-1.html)

### Component Description

| Component | Role |
|-----------|------|
| **Dispatcher** | Routes alerts to appropriate receivers based on routing tree |
| **Inhibitor** | Suppresses related alerts according to inhibition rules |
| **Silencer** | Filters alerts matching silence rules |
| **Aggregation Group** | Groups alerts in the same group for processing |
| **Notification Pipeline** | Handles actual alert sending |
| **nflog** | Records sent alerts (for deduplication) |

---

## Installation and Configuration

### Installation via Helm (kube-prometheus-stack)

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack (includes Alertmanager)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set alertmanager.enabled=true
```

### Alertmanager Dedicated Helm Chart

```bash
# Install Alertmanager separately
helm install alertmanager prometheus-community/alertmanager \
  --namespace monitoring \
  --create-namespace \
  -f alertmanager-values.yaml
```

### values.yaml Example

```yaml
# alertmanager-values.yaml
alertmanager:
  enabled: true

  config:
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'

    route:
      receiver: 'default-receiver'
      group_by: ['alertname', 'namespace']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

      routes:
        - match:
            severity: critical
          receiver: 'critical-receiver'

    receivers:
      - name: 'default-receiver'
        slack_configs:
          - channel: '#alerts'
            send_resolved: true

      - name: 'critical-receiver'
        slack_configs:
          - channel: '#critical-alerts'
            send_resolved: true
        pagerduty_configs:
          - service_key: '<pagerduty-service-key>'

    inhibit_rules:
      - source_match:
          severity: 'critical'
        target_match:
          severity: 'warning'
        equal: ['alertname', 'namespace']

  persistence:
    enabled: true
    size: 10Gi

  resources:
    requests:
      memory: 256Mi
      cpu: 100m
    limits:
      memory: 512Mi
      cpu: 200m

  replicas: 3  # High availability
```

### Direct Configuration via ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m

    route:
      receiver: 'default'
      group_by: ['alertname']

    receivers:
      - name: 'default'
        webhook_configs:
          - url: 'http://webhook-receiver:8080/alerts'
```

---

## Defining Alert Rules

### PrometheusRule CRD

When using Prometheus Operator, alert rules can be defined through the `PrometheusRule` CRD.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
  labels:
    release: prometheus  # Prometheus selects rules with this label
spec:
  groups:
    - name: kubernetes.rules
      interval: 30s  # Rule evaluation interval
      rules:
        # Node alerts
        - alert: NodeNotReady
          expr: kube_node_status_condition{condition="Ready",status="true"} == 0
          for: 5m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "Node {{ $labels.node }} is not ready"
            description: "Node {{ $labels.node }} has been not ready for more than 5 minutes."
            runbook_url: "https://wiki.company.com/runbooks/node-not-ready"

        # Pod alerts
        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 3
          for: 5m
          labels:
            severity: warning
            team: dev
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
            description: "Pod has restarted {{ $value | printf \"%.0f\" }} times in the last 15 minutes."
```

### Alert Rule Components

```yaml
rules:
  - alert: AlertName           # Alert name (required)
    expr: <PromQL expression>  # Alert condition (required)
    for: 5m                    # Duration condition must persist (optional, default 0)
    labels:                    # Additional labels (optional)
      severity: warning
      team: sre
    annotations:               # Metadata (optional)
      summary: "Summary"
      description: "Detailed description"
      runbook_url: "Runbook URL"
```

### Alert States

![State machine showing an alert rule moving from Inactive to Pending once its expr condition is met, then to Firing (sent to Alertmanager) once the 'for' duration elapses, with both Pending and Firing returning to Inactive when the condition clears.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-2.html)

---

## Routing Configuration

### Routing Tree Structure

Alertmanager routing is configured as a tree structure.

```yaml
route:
  # Default receiver (required)
  receiver: 'default-receiver'

  # Grouping criteria
  group_by: ['alertname', 'cluster', 'namespace']

  # Wait time before first notification
  group_wait: 30s

  # Wait time for additional alerts in the same group
  group_interval: 5m

  # Resend interval for identical alerts
  repeat_interval: 4h

  # Child routes
  routes:
    - match:
        severity: critical
      receiver: 'critical-receiver'
      group_wait: 10s

    - match_re:
        service: ^(foo|bar)$
      receiver: 'service-team'
      routes:
        - match:
            owner: team-a
          receiver: 'team-a'
```

### Routing Flow

![Alertmanager routing tree decision flow: a received alert is checked against the severity=critical, service=foo|bar and owner=team-a matchers in turn and delivered to critical-receiver, default-receiver, team-a or service-team.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-3.html)

### Matchers

```yaml
routes:
  # Exact match
  - match:
      severity: critical
      namespace: production
    receiver: 'prod-critical'

  # Regex match
  - match_re:
      service: ^(api|web|worker).*$
      environment: ^prod.*$
    receiver: 'prod-team'

  # Multiple conditions (AND)
  - matchers:
      - severity = critical
      - namespace =~ "prod.*"
    receiver: 'prod-critical'
```

### Advanced Routing Example

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'namespace']
  routes:
    # Send only Critical outside business hours
    - match:
        severity: critical
      receiver: 'oncall'
      active_time_intervals:
        - offhours

    # Send all alerts during business hours
    - receiver: 'team-slack'
      active_time_intervals:
        - business-hours
      routes:
        - match:
            team: infra
          receiver: 'infra-team'
        - match:
            team: dev
          receiver: 'dev-team'

# Time interval definitions
time_intervals:
  - name: business-hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '18:00'
        location: 'Asia/Seoul'

  - name: offhours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '18:00'
            end_time: '09:00'
      - weekdays: ['saturday', 'sunday']
```

---

## Receiver Configuration

### Slack Receiver

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/T00/B00/XXX'
        channel: '#alerts'
        username: 'Alertmanager'
        icon_emoji: ':warning:'
        send_resolved: true

        # Message title
        title: '{{ template "slack.default.title" . }}'

        # Message body
        text: |
          {{ range .Alerts }}
          *Alert:* {{ .Labels.alertname }}
          *Severity:* {{ .Labels.severity }}
          *Description:* {{ .Annotations.description }}
          *Details:*
          {{ range .Labels.SortedPairs }}• *{{ .Name }}:* `{{ .Value }}`
          {{ end }}
          {{ end }}

        # Color (resolved: good, firing: danger)
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'

        # Add fields
        fields:
          - title: Severity
            value: '{{ .CommonLabels.severity }}'
            short: true
          - title: Namespace
            value: '{{ .CommonLabels.namespace }}'
            short: true
```

### PagerDuty Receiver

```yaml
receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<integration-key>'
        severity: '{{ .CommonLabels.severity }}'
        description: '{{ .CommonAnnotations.summary }}'
        client: 'Alertmanager'
        client_url: 'https://alertmanager.example.com'

        details:
          alertname: '{{ .CommonLabels.alertname }}'
          namespace: '{{ .CommonLabels.namespace }}'
          description: '{{ .CommonAnnotations.description }}'

        # Add links
        links:
          - href: '{{ .CommonAnnotations.runbook_url }}'
            text: 'Runbook'
          - href: 'https://grafana.example.com/d/xxx?var-namespace={{ .CommonLabels.namespace }}'
            text: 'Dashboard'
```

### Email Receiver

```yaml
receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: '<password>'
        send_resolved: true

        # HTML template
        html: '{{ template "email.default.html" . }}'

        # Subject
        headers:
          Subject: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
```

### OpsGenie Receiver

```yaml
receivers:
  - name: 'opsgenie-alerts'
    opsgenie_configs:
      - api_key: '<api-key>'
        api_url: 'https://api.opsgenie.com/'
        message: '{{ .CommonLabels.alertname }}'
        description: '{{ .CommonAnnotations.description }}'
        priority: '{{ if eq .CommonLabels.severity "critical" }}P1{{ else if eq .CommonLabels.severity "warning" }}P3{{ else }}P5{{ end }}'

        # Tags
        tags: 'kubernetes,{{ .CommonLabels.namespace }}'

        # Team assignment
        teams:
          - name: 'sre-team'

        # Details
        details:
          alertname: '{{ .CommonLabels.alertname }}'
          namespace: '{{ .CommonLabels.namespace }}'
          severity: '{{ .CommonLabels.severity }}'
```

### Webhook Receiver

```yaml
receivers:
  - name: 'webhook-receiver'
    webhook_configs:
      - url: 'http://webhook-handler.monitoring:8080/alerts'
        send_resolved: true
        max_alerts: 10

        # HTTP configuration
        http_config:
          basic_auth:
            username: 'alertmanager'
            password: '<password>'
          tls_config:
            insecure_skip_verify: false
```

### Multiple Receiver Configuration

```yaml
receivers:
  - name: 'team-all'
    slack_configs:
      - channel: '#alerts'
        api_url: '<slack-webhook-url>'
    email_configs:
      - to: 'team@example.com'
    pagerduty_configs:
      - service_key: '<integration-key>'
```

---

## Inhibition Rules

### Inhibition Concept

Inhibition is a feature that suppresses related alerts when a specific alert fires.

![Side-by-side comparison of alert delivery without inhibition, where NodeDown, PodNotReady and ServiceUnavailable all reach the receiver, and with inhibition, where only NodeDown is sent and the two related alerts are blocked.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-4.html)

### Inhibition Rule Configuration

```yaml
inhibit_rules:
  # Suppress pod alerts when node is down
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: ^(PodNotReady|PodCrashLooping|ContainerOOMKilled)$
    equal: ['node']

  # Suppress warning when critical alert exists
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'namespace']

  # Suppress all node alerts when cluster is down
  - source_match:
      alertname: ClusterDown
    target_match_re:
      alertname: ^Node.*$
    equal: ['cluster']

  # Suppress connection error alerts when database is down
  - source_matchers:
      - alertname = DatabaseDown
    target_matchers:
      - alertname =~ "DatabaseConnection.*|DatabaseTimeout.*"
    equal: ['instance']
```

### Inhibition Priority

```yaml
inhibit_rules:
  # Priority 1: Infrastructure failure
  - source_match:
      alertname: InfrastructureFailure
    target_match_re:
      alertname: .*
    equal: ['datacenter']

  # Priority 2: Node failure
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: ^(Pod|Container).*$
    equal: ['node']

  # Priority 3: Service failure
  - source_match:
      alertname: ServiceDown
    target_match_re:
      alertname: ^Endpoint.*$
    equal: ['service', 'namespace']
```

---

## Silencing

### Creating Silences

Silences can be created through the Alertmanager UI or API.

#### Using amtool CLI

```bash
# Create silence (2 hours)
amtool silence add alertname=PodCrashLooping namespace=development \
  --duration=2h \
  --comment="Deployment in progress in dev environment" \
  --author="ops@example.com"

# Silence until specific time
amtool silence add alertname=NodeDown node="worker-1" \
  --end="2025-02-21T18:00:00+09:00" \
  --comment="Node maintenance" \
  --author="ops@example.com"

# List silences
amtool silence query

# Expire silence
amtool silence expire <silence-id>
```

#### Creating Silence via API

```bash
curl -X POST http://alertmanager:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "alertname", "value": "HighCPU", "isRegex": false},
      {"name": "namespace", "value": "dev.*", "isRegex": true}
    ],
    "startsAt": "2025-02-20T10:00:00Z",
    "endsAt": "2025-02-20T14:00:00Z",
    "createdBy": "ops@example.com",
    "comment": "Dev environment load testing"
  }'
```

### Silence Management Best Practices

![Flowchart showing a silence's duration set by its type — maintenance (planned window), deployment (until the deploy completes), investigation (max 4 hours), or known issue (until the fix lands) — followed by a mandatory comment, regular review, and either automatic removal on expiry or a manual review.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-5.html)

**Recommendations:**

1. **Always write comments**: Record why the silence was created
2. **Set minimum duration**: Only silence for as long as needed
3. **Regular review**: Periodically review long-term silences
4. **Set up notifications**: Alert before silence expires

---

## Template Customization

### Go Template Basics

Alertmanager uses Go templates.

```yaml
# Template file definition
templates:
  - '/etc/alertmanager/templates/*.tmpl'
```

### Slack Template Example

```go
{{ define "slack.custom.title" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .CommonLabels.alertname }}
{{ end }}

{{ define "slack.custom.text" }}
{{ range .Alerts }}
*Alert:* {{ .Labels.alertname }}
*Severity:* `{{ .Labels.severity }}`
*Namespace:* `{{ .Labels.namespace }}`
*Description:* {{ .Annotations.description }}
*Started:* {{ .StartsAt.Format "2006-01-02 15:04:05 MST" }}
{{ if .Annotations.runbook_url }}*Runbook:* <{{ .Annotations.runbook_url }}|Link>{{ end }}
---
{{ end }}
{{ end }}

{{ define "slack.custom.color" }}
{{ if eq .Status "firing" }}
{{ if eq .CommonLabels.severity "critical" }}#ff0000{{ else if eq .CommonLabels.severity "warning" }}#ff9900{{ else }}#439fe0{{ end }}
{{ else }}#36a64f{{ end }}
{{ end }}
```

### Template Functions

```go
{{ define "custom.message" }}
{{ /* String manipulation */ }}
{{ .Labels.alertname | title }}
{{ .Labels.namespace | toUpper }}

{{ /* Conditionals */ }}
{{ if eq .Labels.severity "critical" }}Urgent{{ else }}Normal{{ end }}

{{ /* Loops */ }}
{{ range .Alerts }}
- {{ .Labels.alertname }}
{{ end }}

{{ /* Date format */ }}
{{ .StartsAt.Format "2006-01-02 15:04" }}

{{ /* Number format */ }}
{{ $value := 95.5 }}
{{ printf "%.2f%%" $value }}

{{ /* Label sorting */ }}
{{ range .Labels.SortedPairs }}
{{ .Name }}: {{ .Value }}
{{ end }}
{{ end }}
```

### Managing Templates via ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-templates
  namespace: monitoring
data:
  slack.tmpl: |
    {{ define "slack.custom.title" }}
    [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
    {{ end }}

    {{ define "slack.custom.text" }}
    {{ range .Alerts }}
    *Severity:* {{ .Labels.severity }}
    *Description:* {{ .Annotations.description }}
    {{ end }}
    {{ end }}
```

---

## High Availability Configuration

### Clustering Architecture

![Diagram showing Prometheus sending the same alerts to all three Alertmanager replicas, the replicas syncing their notification log over gossip on port 9094 to deduplicate, and one replica delivering the final notification to the receivers.](../../.gitbook/assets/en-observability-alerting-01-alertmanager-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-01-alertmanager-6.html)

### StatefulSet Configuration

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  serviceName: alertmanager
  replicas: 3
  selector:
    matchLabels:
      app: alertmanager
  template:
    metadata:
      labels:
        app: alertmanager
    spec:
      containers:
        - name: alertmanager
          image: quay.io/prometheus/alertmanager:v0.27.0
          args:
            - '--config.file=/etc/alertmanager/alertmanager.yml'
            - '--storage.path=/alertmanager'
            - '--cluster.listen-address=0.0.0.0:9094'
            - '--cluster.peer=alertmanager-0.alertmanager:9094'
            - '--cluster.peer=alertmanager-1.alertmanager:9094'
            - '--cluster.peer=alertmanager-2.alertmanager:9094'
          ports:
            - containerPort: 9093
              name: http
            - containerPort: 9094
              name: cluster
          volumeMounts:
            - name: config
              mountPath: /etc/alertmanager
            - name: storage
              mountPath: /alertmanager
          resources:
            requests:
              memory: 256Mi
              cpu: 100m
            limits:
              memory: 512Mi
              cpu: 200m
      volumes:
        - name: config
          configMap:
            name: alertmanager-config
  volumeClaimTemplates:
    - metadata:
        name: storage
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: alertmanager
  namespace: monitoring
spec:
  type: ClusterIP
  clusterIP: None  # Headless service
  ports:
    - port: 9093
      name: http
    - port: 9094
      name: cluster
  selector:
    app: alertmanager
```

### Prometheus Integration Configuration

```yaml
# Prometheus configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager-0.alertmanager:9093
            - alertmanager-1.alertmanager:9093
            - alertmanager-2.alertmanager:9093
      # Or DNS-based
    - dns_sd_configs:
        - names:
            - alertmanager.monitoring.svc
          type: A
          port: 9093
```

---

## AlertmanagerConfig CRD

### Namespace-Scoped Configuration

Prometheus Operator's `AlertmanagerConfig` CRD allows you to separate alert configurations by namespace.

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: team-a-config
  namespace: team-a
  labels:
    alertmanagerConfig: team-a
spec:
  route:
    receiver: 'team-a-slack'
    groupBy: ['alertname']
    matchers:
      - name: namespace
        value: team-a
    routes:
      - receiver: 'team-a-critical'
        matchers:
          - name: severity
            value: critical

  receivers:
    - name: 'team-a-slack'
      slackConfigs:
        - apiURL:
            name: slack-webhook-secret
            key: webhook-url
          channel: '#team-a-alerts'
          sendResolved: true

    - name: 'team-a-critical'
      slackConfigs:
        - apiURL:
            name: slack-webhook-secret
            key: webhook-url
          channel: '#team-a-critical'
      pagerdutyConfigs:
        - routingKey:
            name: pagerduty-secret
            key: routing-key

  inhibitRules:
    - sourceMatch:
        - name: severity
          value: critical
      targetMatch:
        - name: severity
          value: warning
      equal: ['alertname']
```

### Secret Reference

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook-secret
  namespace: team-a
type: Opaque
stringData:
  webhook-url: "https://hooks.slack.com/services/xxx/yyy/zzz"
---
apiVersion: v1
kind: Secret
metadata:
  name: pagerduty-secret
  namespace: team-a
type: Opaque
stringData:
  routing-key: "<pagerduty-routing-key>"
```

### Alertmanager AlertmanagerConfig Selection

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Alertmanager
metadata:
  name: main
  namespace: monitoring
spec:
  replicas: 3
  alertmanagerConfigSelector:
    matchLabels:
      alertmanagerConfig: enabled
  alertmanagerConfigNamespaceSelector: {}  # All namespaces
```

---

## Production Alert Rule Examples

### Node Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-alerts
  namespace: monitoring
spec:
  groups:
    - name: node.rules
      rules:
        - alert: NodeDown
          expr: up{job="node-exporter"} == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Node {{ $labels.instance }} is down"
            description: "Node exporter is not responding for more than 5 minutes."

        - alert: NodeHighCPU
          expr: |
            100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High CPU usage on {{ $labels.instance }}"
            description: "CPU usage is {{ $value | printf \"%.2f\" }}%"

        - alert: NodeHighMemory
          expr: |
            (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High memory usage on {{ $labels.instance }}"
            description: "Memory usage is {{ $value | printf \"%.2f\" }}%"

        - alert: NodeDiskPressure
          expr: |
            (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes) * 100 < 15
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Low disk space on {{ $labels.instance }}"
            description: "Disk {{ $labels.mountpoint }} has only {{ $value | printf \"%.2f\" }}% free"

        - alert: NodeNetworkErrors
          expr: |
            rate(node_network_receive_errs_total[5m]) > 10
            or
            rate(node_network_transmit_errs_total[5m]) > 10
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Network errors on {{ $labels.instance }}"
```

### Pod and Container Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-alerts
  namespace: monitoring
spec:
  groups:
    - name: pod.rules
      rules:
        - alert: PodNotReady
          expr: |
            kube_pod_status_phase{phase=~"Pending|Unknown"} > 0
          for: 15m
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready"

        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total[15m]) * 60 * 15 > 3
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping"
            description: "Pod has restarted {{ $value | printf \"%.0f\" }} times in 15 minutes"

        - alert: ContainerOOMKilled
          expr: |
            kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} > 0
          for: 0m
          labels:
            severity: warning
          annotations:
            summary: "Container {{ $labels.container }} in {{ $labels.namespace }}/{{ $labels.pod }} was OOM killed"

        - alert: ContainerCPUThrottled
          expr: |
            rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0.5
          for: 10m
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
            description: "Memory usage is {{ $value | printf \"%.2f\" }}% of limit"
```

### API Server Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: apiserver-alerts
  namespace: monitoring
spec:
  groups:
    - name: apiserver.rules
      rules:
        - alert: KubeAPIServerDown
          expr: |
            absent(up{job="kubernetes-apiservers"} == 1)
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Kubernetes API server is down"

        - alert: KubeAPIServerLatencyHigh
          expr: |
            histogram_quantile(0.99,
              sum(rate(apiserver_request_duration_seconds_bucket{verb!~"WATCH|CONNECT"}[5m]))
              by (verb, resource, le)
            ) > 1
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "API server latency is high"
            description: "99th percentile latency for {{ $labels.verb }} {{ $labels.resource }} is {{ $value | printf \"%.2f\" }}s"

        - alert: KubeAPIServerErrors
          expr: |
            sum(rate(apiserver_request_total{code=~"5.."}[5m])) /
            sum(rate(apiserver_request_total[5m])) > 0.01
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "API server error rate is high"
            description: "Error rate is {{ $value | printf \"%.2f\" }}%"

        - alert: KubeClientCertificateExpiration
          expr: |
            apiserver_client_certificate_expiration_seconds_count > 0
            and
            apiserver_client_certificate_expiration_seconds_bucket{le="604800"} > 0
          for: 0m
          labels:
            severity: warning
          annotations:
            summary: "Client certificate will expire within 7 days"
```

### etcd Alerts

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: etcd-alerts
  namespace: monitoring
spec:
  groups:
    - name: etcd.rules
      rules:
        - alert: EtcdMembersDown
          expr: |
            count(etcd_server_id) < 3
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "etcd cluster has less than 3 members"

        - alert: EtcdNoLeader
          expr: |
            etcd_server_has_leader == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "etcd cluster has no leader"

        - alert: EtcdHighCommitDuration
          expr: |
            histogram_quantile(0.99, rate(etcd_disk_backend_commit_duration_seconds_bucket[5m])) > 0.25
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "etcd commit duration is high"
            description: "99th percentile commit duration is {{ $value | printf \"%.3f\" }}s"

        - alert: EtcdHighFsyncDuration
          expr: |
            histogram_quantile(0.99, rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])) > 0.5
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "etcd fsync duration is high"

        - alert: EtcdDatabaseSizeLarge
          expr: |
            etcd_mvcc_db_total_size_in_bytes > 6e+9
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "etcd database size is large"
            description: "Database size is {{ $value | humanize1024 }}B"
```

---

## Troubleshooting

### Common Problems and Solutions

#### Alerts Not Being Sent

```bash
# 1. Check Alertmanager logs
kubectl logs -n monitoring alertmanager-main-0

# 2. Check configuration
kubectl exec -n monitoring alertmanager-main-0 -- cat /etc/alertmanager/config/alertmanager.yaml

# 3. Check alert status (API)
curl http://alertmanager:9093/api/v2/alerts

# 4. Check silences
curl http://alertmanager:9093/api/v2/silences

# 5. Check alerts firing from Prometheus
curl http://prometheus:9090/api/v1/alerts
```

#### Duplicate Alerts

```yaml
# Check group_by configuration
route:
  group_by: ['alertname', 'namespace', 'pod']  # Set appropriate grouping keys
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h  # Set sufficient interval
```

#### Alerts Sent to Wrong Receiver

```bash
# Test routing
amtool config routes test \
  --config.file=/etc/alertmanager/alertmanager.yml \
  alertname=HighCPU severity=warning namespace=production

# Output: Shows which receiver the alert would be routed to
```

### amtool Command Reference

```bash
# Validate configuration
amtool check-config /etc/alertmanager/alertmanager.yml

# List alerts
amtool alert query

# Query specific alerts
amtool alert query alertname=HighCPU

# Create silence
amtool silence add alertname=HighCPU --duration=2h --comment="Testing"

# List silences
amtool silence query

# Expire silence
amtool silence expire <silence-id>

# Test routing
amtool config routes test --config.file=config.yml alertname=Test severity=warning
```

### Metric Verification

```promql
# Alertmanager metrics

# Received alerts count
alertmanager_alerts_received_total

# Invalid alerts count
alertmanager_alerts_invalid_total

# Failed sends count
alertmanager_notifications_failed_total

# Successful sends count
alertmanager_notifications_total

# Current active alerts count
alertmanager_alerts

# Current silences count
alertmanager_silences

# Cluster status
alertmanager_cluster_members
```

### Debugging Tips

```yaml
# 1. Add debug receiver
receivers:
  - name: 'debug'
    webhook_configs:
      - url: 'http://localhost:5001/'  # Use webhook.site etc.
        send_resolved: true

# 2. Increase log level
containers:
  - name: alertmanager
    args:
      - '--log.level=debug'

# 3. Send test alert
curl -X POST http://alertmanager:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning"
    },
    "annotations": {
      "summary": "This is a test alert"
    }
  }]'
```

---

## Quiz

Test your knowledge with the [Alertmanager Quiz](../../quizzes/observability/alerting/01-alertmanager-quiz.md).
