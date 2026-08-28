# Grafana Dashboards

> **Supported Versions**: Grafana 11.x
> **Last Updated**: February 20, 2026

## Introduction

Grafana is an open-source platform for visualizing and analyzing metrics, logs, and trace data. By integrating various data sources, you can monitor the entire system status from a single dashboard.

## Key Features

| Feature | Description |
|---------|-------------|
| **Multiple Data Sources** | Support for Prometheus, Loki, Tempo, CloudWatch, etc. |
| **Rich Visualizations** | Graphs, heatmaps, tables, stat panels, etc. |
| **Alerting** | Condition-based alerts and various notification channels |
| **Dashboard Templates** | Reusable dashboards and panels |
| **Plugin Ecosystem** | Extensible plugin architecture |
| **Team Collaboration** | Folders, permissions, team features |

## Architecture

![Architecture diagram of Grafana: browsers and API clients hit the Frontend, which calls the Backend; the Backend persists to PostgreSQL/MySQL and Redis/Memcached and drives a Plugin System that queries six data sources (Prometheus, VictoriaMetrics, Loki, Tempo, CloudWatch, Elasticsearch), while a separate Alerting Engine fires notifications to Slack, PagerDuty, Email, and Webhook.](../../.gitbook/assets/en-observability-grafana-README-0.png)

## Helm Deployment

### Basic Installation

```bash
# Add Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace monitoring
```

### values.yaml Configuration

```yaml
# grafana-values.yaml
replicas: 2

image:
  repository: grafana/grafana
  tag: 11.0.0

# Admin credentials
adminUser: admin
adminPassword: ""  # Auto-generated, managed in Secret

# Use existing Secret
admin:
  existingSecret: grafana-admin-credentials
  userKey: admin-user
  passwordKey: admin-password

# Service configuration
service:
  type: ClusterIP
  port: 80

# Ingress configuration
ingress:
  enabled: true
  ingressClassName: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
  hosts:
    - grafana.example.com
  tls:
    - hosts:
        - grafana.example.com

# Persistent storage
persistence:
  enabled: true
  type: pvc
  storageClassName: gp3
  size: 10Gi
  accessModes:
    - ReadWriteOnce

# Resource configuration
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi

# Grafana configuration
grafana.ini:
  server:
    domain: grafana.example.com
    root_url: https://grafana.example.com

  database:
    type: postgres
    host: postgres.monitoring.svc.cluster.local:5432
    name: grafana
    user: grafana
    ssl_mode: require

  security:
    admin_user: admin
    secret_key: $__env{GF_SECURITY_SECRET_KEY}
    cookie_secure: true
    strict_transport_security: true

  users:
    allow_sign_up: false
    auto_assign_org: true
    auto_assign_org_role: Viewer

  alerting:
    enabled: true
    execute_alerts: true

  unified_alerting:
    enabled: true
    min_interval: 10s

  analytics:
    reporting_enabled: false
    check_for_updates: false

  log:
    mode: console
    level: info

  metrics:
    enabled: true

# Sidecar configuration (dashboard/datasource provisioning)
sidecar:
  dashboards:
    enabled: true
    label: grafana_dashboard
    labelValue: "true"
    searchNamespace: ALL
    folderAnnotation: grafana_folder
    provider:
      foldersFromFilesStructure: true
  datasources:
    enabled: true
    label: grafana_datasource
    labelValue: "true"
    searchNamespace: ALL
  alerts:
    enabled: true
    label: grafana_alert
    searchNamespace: ALL

# Plugin installation
plugins:
  - grafana-piechart-panel
  - grafana-worldmap-panel
  - grafana-clock-panel
  - grafana-polystat-panel
  - yesoreyeram-infinity-datasource

# ServiceMonitor (Prometheus Operator)
serviceMonitor:
  enabled: true
  interval: 30s
  labels:
    release: prometheus

# PodDisruptionBudget
podDisruptionBudget:
  minAvailable: 1

# Anti-affinity
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: grafana
          topologyKey: kubernetes.io/hostname
```

### Run Installation

```bash
# Install
helm upgrade --install grafana grafana/grafana \
  --namespace monitoring \
  --values grafana-values.yaml \
  --wait

# Verify
kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana
kubectl get svc -n monitoring -l app.kubernetes.io/name=grafana
```

## Data Source Integration

### Data Source Provisioning via ConfigMap

```yaml
# grafana-datasources.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
  labels:
    grafana_datasource: "true"
data:
  datasources.yaml: |-
    apiVersion: 1
    deleteDatasources:
      - name: Old-Prometheus
        orgId: 1

    datasources:
      # Prometheus
      - name: Prometheus
        type: prometheus
        uid: prometheus
        url: http://prometheus-operated.monitoring.svc.cluster.local:9090
        access: proxy
        isDefault: true
        jsonData:
          httpMethod: POST
          manageAlerts: true
          prometheusType: Prometheus
          prometheusVersion: 2.47.0
          exemplarTraceIdDestinations:
            - name: traceID
              datasourceUid: tempo
              urlDisplayLabel: "View Trace"
        editable: false

      # VictoriaMetrics
      - name: VictoriaMetrics
        type: prometheus
        uid: victoriametrics
        url: http://vmsingle.monitoring.svc.cluster.local:8428
        access: proxy
        jsonData:
          httpMethod: POST

      # Loki
      - name: Loki
        type: loki
        uid: loki
        url: http://loki-gateway.loki.svc.cluster.local
        access: proxy
        jsonData:
          maxLines: 1000
          derivedFields:
            # Extract TraceID from logs
            - name: TraceID
              matcherRegex: '"traceId":"([a-f0-9]+)"'
              url: '$${__value.raw}'
              datasourceUid: tempo
              urlDisplayLabel: "View Trace"

      # Tempo
      - name: Tempo
        type: tempo
        uid: tempo
        url: http://tempo-query-frontend.tempo.svc.cluster.local:3100
        access: proxy
        jsonData:
          httpMethod: GET
          tracesToLogs:
            datasourceUid: loki
            tags: ['job', 'namespace', 'pod']
            mappedTags:
              - key: service.name
                value: app
            mapTagNamesEnabled: true
            spanStartTimeShift: '-1h'
            spanEndTimeShift: '1h'
            filterByTraceID: true
            filterBySpanID: true
          tracesToMetrics:
            datasourceUid: prometheus
            tags:
              - key: service.name
                value: service
            queries:
              - name: 'Request Rate'
                query: 'sum(rate(http_requests_total{service="$${__tags}"}[5m]))'
              - name: 'Error Rate'
                query: 'sum(rate(http_requests_total{service="$${__tags}",status=~"5.."}[5m]))'
          serviceMap:
            datasourceUid: prometheus
          nodeGraph:
            enabled: true
          search:
            hide: false
          lokiSearch:
            datasourceUid: loki

      # CloudWatch
      - name: CloudWatch
        type: cloudwatch
        uid: cloudwatch
        jsonData:
          authType: default
          defaultRegion: ap-northeast-2
          assumeRoleArn: arn:aws:iam::123456789012:role/grafana-cloudwatch-role
```

## Dashboard Design Patterns

### USE Method (Utilization, Saturation, Errors)

Methodology for analyzing system resources:

```yaml
# use-method-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: use-method-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "true"
  annotations:
    grafana_folder: "System"
data:
  use-method.json: |-
    {
      "title": "USE Method - System Resources",
      "uid": "use-method",
      "panels": [
        {
          "title": "CPU Utilization",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
          "targets": [
            {
              "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
              "legendFormat": "{{instance}}"
            }
          ]
        },
        {
          "title": "CPU Saturation (Load Average)",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
          "targets": [
            {
              "expr": "node_load1 / count without(cpu, mode) (node_cpu_seconds_total{mode=\"idle\"})",
              "legendFormat": "{{instance}}"
            }
          ]
        },
        {
          "title": "Memory Utilization",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 0, "y": 8},
          "targets": [
            {
              "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
              "legendFormat": "{{instance}}"
            }
          ]
        }
      ]
    }
```

### RED Method (Rate, Errors, Duration)

Methodology for analyzing service requests:

```yaml
# red-method-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: red-method-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "true"
  annotations:
    grafana_folder: "Services"
data:
  red-method.json: |-
    {
      "title": "RED Method - Service Metrics",
      "uid": "red-method",
      "templating": {
        "list": [
          {
            "name": "service",
            "type": "query",
            "query": "label_values(http_requests_total, service)",
            "refresh": 2
          }
        ]
      },
      "panels": [
        {
          "title": "Request Rate",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
          "targets": [
            {
              "expr": "sum(rate(http_requests_total{service=\"$service\"}[5m])) by (method, path)",
              "legendFormat": "{{method}} {{path}}"
            }
          ]
        },
        {
          "title": "Error Rate",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
          "targets": [
            {
              "expr": "sum(rate(http_requests_total{service=\"$service\", status=~\"5..\"}[5m])) / sum(rate(http_requests_total{service=\"$service\"}[5m])) * 100",
              "legendFormat": "Error %"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percent",
              "thresholds": {
                "mode": "absolute",
                "steps": [
                  {"color": "green", "value": null},
                  {"color": "yellow", "value": 1},
                  {"color": "red", "value": 5}
                ]
              }
            }
          }
        },
        {
          "title": "Request Duration (p50, p90, p99)",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
          "targets": [
            {
              "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{service=\"$service\"}[5m])) by (le))",
              "legendFormat": "p50"
            },
            {
              "expr": "histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{service=\"$service\"}[5m])) by (le))",
              "legendFormat": "p90"
            },
            {
              "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=\"$service\"}[5m])) by (le))",
              "legendFormat": "p99"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "s"
            }
          }
        }
      ]
    }
```

### 4 Golden Signals

Core metrics from the Google SRE Handbook:

```yaml
# golden-signals-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: golden-signals-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "true"
  annotations:
    grafana_folder: "SRE"
data:
  golden-signals.json: |-
    {
      "title": "4 Golden Signals",
      "uid": "golden-signals",
      "panels": [
        {
          "title": "1. Latency - Request Duration",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
          "targets": [
            {
              "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))",
              "legendFormat": "{{service}} p99"
            }
          ],
          "fieldConfig": {
            "defaults": {"unit": "s"}
          }
        },
        {
          "title": "2. Traffic - Request Rate",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
          "targets": [
            {
              "expr": "sum(rate(http_requests_total[5m])) by (service)",
              "legendFormat": "{{service}}"
            }
          ],
          "fieldConfig": {
            "defaults": {"unit": "reqps"}
          }
        },
        {
          "title": "3. Errors - Error Rate",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
          "targets": [
            {
              "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service) * 100",
              "legendFormat": "{{service}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            }
          }
        },
        {
          "title": "4. Saturation - Resource Usage",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
          "targets": [
            {
              "expr": "sum(container_memory_working_set_bytes{container!=\"\"}) by (pod) / sum(kube_pod_container_resource_limits{resource=\"memory\"}) by (pod) * 100",
              "legendFormat": "{{pod}} Memory"
            }
          ],
          "fieldConfig": {
            "defaults": {"unit": "percent"}
          }
        }
      ]
    }
```

## Alert Rules (Grafana Alerting)

### Alert Rule Configuration

```yaml
# grafana-alerts.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-alerts
  namespace: monitoring
  labels:
    grafana_alert: "true"
data:
  alerts.yaml: |-
    apiVersion: 1
    groups:
      - orgId: 1
        name: kubernetes-alerts
        folder: Alerts
        interval: 1m
        rules:
          - uid: high-cpu-usage
            title: High CPU Usage
            condition: C
            data:
              - refId: A
                relativeTimeRange:
                  from: 600
                  to: 0
                datasourceUid: prometheus
                model:
                  expr: |
                    100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
                  instant: false
                  range: true
              - refId: B
                datasourceUid: __expr__
                model:
                  conditions:
                    - evaluator:
                        params: [80]
                        type: gt
                      operator:
                        type: and
                      query:
                        params: [A]
                      reducer:
                        type: avg
                  refId: B
                  type: classic_conditions
              - refId: C
                datasourceUid: __expr__
                model:
                  expression: B
                  type: threshold
            noDataState: NoData
            execErrState: Error
            for: 5m
            annotations:
              summary: "High CPU usage detected on {{ $labels.instance }}"
              description: "CPU usage is above 80% for more than 5 minutes."
            labels:
              severity: warning

          - uid: pod-crash-looping
            title: Pod CrashLooping
            condition: C
            data:
              - refId: A
                datasourceUid: prometheus
                model:
                  expr: |
                    increase(kube_pod_container_status_restarts_total[1h]) > 5
              - refId: C
                datasourceUid: __expr__
                model:
                  expression: A
                  type: threshold
            for: 0s
            annotations:
              summary: "Pod {{ $labels.pod }} is crash looping"
            labels:
              severity: critical
```

## Grafana Cloud vs Self-hosted Comparison

| Feature | Self-hosted | Grafana Cloud |
|---------|-------------|---------------|
| **Management Overhead** | High | Low |
| **Cost** | Infrastructure cost | Usage-based |
| **Scalability** | Manual management | Automatic |
| **High Availability** | Manual configuration | Built-in |
| **Plugins** | All plugins | Approved plugins only |
| **Data Location** | Internal | Cloud |
| **Customization** | Full control | Limited |
| **SLA** | None | 99.9% |

## Best Practices

### 1. Dashboard Organization

```
Folders/
├── Overview/           # Overall system overview
│   ├── Executive Summary
│   └── SLO Dashboard
├── Infrastructure/     # Infrastructure metrics
│   ├── Nodes
│   ├── Storage
│   └── Network
├── Kubernetes/         # K8s resources
│   ├── Cluster
│   ├── Workloads
│   └── Networking
├── Applications/       # Per-application
│   ├── Service A
│   └── Service B
└── Alerts/            # Alert related
    ├── Active Alerts
    └── Alert History
```

### 2. Variable Usage

```json
{
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus"
      },
      {
        "name": "cluster",
        "type": "query",
        "query": "label_values(kube_node_info, cluster)",
        "refresh": 2,
        "multi": true,
        "includeAll": true
      },
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values(kube_namespace_labels{cluster=~\"$cluster\"}, namespace)",
        "refresh": 2
      }
    ]
  }
}
```

### 3. Performance Optimization

```yaml
# grafana.ini performance settings
[database]
max_idle_conn = 25
max_open_conn = 100
conn_max_lifetime = 14400

[dataproxy]
timeout = 30
keep_alive_seconds = 30

[dashboards]
min_refresh_interval = 10s

[caching]
enabled = true
ttl = 60s
```

## Quiz

Test your knowledge with the [Grafana Quiz](../../quizzes/observability/grafana/grafana-quiz.md).
