# Observability Stack Operations: Loki, Tempo, Prometheus Configuration Guide

> **Supported Versions**: Loki 3.x, Tempo 2.x, Prometheus 2.x, Grafana 10.x, Amazon Managed Prometheus
> **Last Updated**: February 23, 2026

< [Previous: Observability Analysis](./08-observability-analysis.md) | [Table of Contents](./README.md) | [Next: Resource Optimization](./10-resource-optimization.md) >

---

## Table of Contents

- [Observability Stack Architecture](#observability-stack-architecture)
- [Loki Operations Guide](#loki-operations-guide)
- [Tempo Operations Guide](#tempo-operations-guide)
- [Prometheus/AMP Operations](#prometheusamazon-managed-prometheus-operations)
- [Grafana Integration](#grafana-integration)

---

## Observability Stack Architecture

### Full Stack Overview

A production-grade observability stack combines **metrics**, **logs**, and **traces** into a unified platform. The LGTM stack (Loki, Grafana, Tempo, Mimir/Prometheus) provides this capability with cost-effective storage and powerful correlation features.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Observability Data Sources                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Applications    │    Kubernetes    │    Infrastructure    │    AWS Services │
│  (instrumented)  │    (pods/nodes)  │    (load balancers)  │    (EKS, RDS)   │
└────────┬─────────┴────────┬─────────┴─────────┬────────────┴────────┬───────┘
         │                  │                   │                     │
         ▼                  ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Collection Layer                                   │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│  OTEL Collector  │  Promtail/Alloy  │  Prometheus      │  CloudWatch Agent  │
│  (traces+metrics)│  (logs)          │  (metrics)       │  (AWS metrics)     │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴────────┬───────────┘
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Storage Layer                                      │
├──────────────────┬──────────────────┬───────────────────────────────────────┤
│  Grafana Tempo   │  Grafana Loki    │  Amazon Managed Prometheus (AMP)      │
│  (traces → S3)   │  (logs → S3)     │  (metrics → AWS managed storage)      │
└────────┬─────────┴────────┬─────────┴────────┬──────────────────────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Visualization Layer                                │
│                              Grafana                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Dashboards  │  │  Explore    │  │   Alerts    │  │   Correlations      │ │
│  │ (metrics)   │  │  (logs)     │  │  (all)      │  │   (trace↔log↔metric)│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Role | Data Type | Storage Backend |
|-----------|------|-----------|-----------------|
| **Prometheus/AMP** | Metrics collection and storage | Time-series metrics | AMP (managed) or local TSDB |
| **Loki** | Log aggregation and querying | Log streams | S3 (chunks + index) |
| **Tempo** | Distributed trace storage | Trace spans | S3 (trace blocks) |
| **Grafana** | Unified visualization | All data types | PostgreSQL/MySQL (metadata) |
| **OTEL Collector** | Telemetry collection/routing | Traces, metrics, logs | N/A (pass-through) |
| **Promtail/Alloy** | Log shipping | Logs | N/A (pass-through) |

### Storage Architecture Choices

| Storage Option | Use Case | Cost | Performance | Operations |
|----------------|----------|------|-------------|------------|
| **S3 (recommended)** | Production workloads | Low | High (with caching) | Minimal |
| **EBS gp3** | Small clusters, testing | Medium | Very High | Moderate |
| **EFS** | Shared storage needs | High | Medium | Low |
| **DynamoDB** | Loki index (legacy) | Variable | High | Low |

**Recommended Architecture for EKS**:
- **Loki**: S3 for chunks and TSDB index
- **Tempo**: S3 for trace blocks
- **Prometheus**: Remote write to AMP (150-day retention)
- **Grafana**: Managed Amazon Grafana or self-hosted with RDS backend

---

## Loki Operations Guide

### Deployment Modes

Loki supports multiple deployment modes based on scale requirements:

| Mode | Components | Scale | Use Case |
|------|------------|-------|----------|
| **Monolithic** | Single binary | < 100GB/day | Development, small clusters |
| **SimpleScalable** | Read/Write/Backend | 100GB-1TB/day | Most production workloads |
| **Distributed** | All separate | > 1TB/day | Large-scale, multi-tenant |

### Helm Installation: SimpleScalable Mode

```bash
# Add Grafana Helm repository
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create namespace
kubectl create namespace loki

# Install with custom values
helm upgrade --install loki grafana/loki \
  --namespace loki \
  --version 6.6.0 \
  --values loki-values.yaml
```

**Full Production values.yaml (SimpleScalable)**:

```yaml
# loki-values.yaml - SimpleScalable mode for EKS
loki:
  # Authentication disabled for internal use
  auth_enabled: false

  # Schema configuration - TSDB is recommended for new deployments
  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: s3
        schema: v13
        index:
          prefix: loki_index_
          period: 24h

  # Storage configuration for S3
  storage:
    type: s3
    bucketNames:
      chunks: my-loki-chunks-bucket
      ruler: my-loki-ruler-bucket
      admin: my-loki-admin-bucket
    s3:
      region: us-west-2
      # Use IRSA for authentication (recommended)
      # insecure: false
      # s3ForcePathStyle: false

  # Ingester configuration
  ingester:
    chunk_encoding: snappy
    chunk_idle_period: 30m
    chunk_block_size: 262144
    chunk_retain_period: 1m
    max_transfer_retries: 0
    wal:
      enabled: true
      dir: /var/loki/wal

  # Limits configuration
  limits_config:
    enforce_metric_name: false
    reject_old_samples: true
    reject_old_samples_max_age: 168h
    max_cache_freshness_per_query: 10m
    split_queries_by_interval: 15m
    # Per-tenant limits
    ingestion_rate_mb: 10
    ingestion_burst_size_mb: 20
    max_streams_per_user: 10000
    max_line_size: 256kb
    max_entries_limit_per_query: 5000
    max_query_parallelism: 32

  # Compactor configuration
  compactor:
    working_directory: /var/loki/compactor
    shared_store: s3
    compaction_interval: 10m
    retention_enabled: true
    retention_delete_delay: 2h
    retention_delete_worker_count: 150
    delete_request_store: s3

  # Query scheduler
  query_scheduler:
    max_outstanding_requests_per_tenant: 2048

  # Frontend configuration
  frontend:
    max_outstanding_per_tenant: 2048
    compress_responses: true

  # Ruler configuration for alerting
  rulerConfig:
    storage:
      type: s3
      s3:
        bucketnames: my-loki-ruler-bucket
        region: us-west-2
    alertmanager_url: http://alertmanager.monitoring:9093

# Deployment mode
deploymentMode: SimpleScalable

# Backend (compactor + ruler)
backend:
  replicas: 2
  persistence:
    size: 10Gi
    storageClass: gp3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi

# Read path (query-frontend + querier)
read:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80

# Write path (distributor + ingester)
write:
  replicas: 3
  persistence:
    size: 50Gi
    storageClass: gp3
  resources:
    requests:
      cpu: 500m
      memory: 2Gi
    limits:
      cpu: 2
      memory: 8Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80

# Gateway (nginx)
gateway:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 128Mi

# Service account for IRSA
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/LokiS3Role

# Monitoring
monitoring:
  selfMonitoring:
    enabled: true
    grafanaAgent:
      installOperator: false
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus

# Disable test pods
test:
  enabled: false
```

### Distributed Mode values.yaml

For large-scale deployments (> 1TB/day):

```yaml
# loki-distributed-values.yaml
loki:
  auth_enabled: true  # Required for multi-tenant

  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb
        object_store: s3
        schema: v13
        index:
          prefix: loki_index_
          period: 24h

  storage:
    type: s3
    bucketNames:
      chunks: my-loki-chunks-bucket
      ruler: my-loki-ruler-bucket
    s3:
      region: us-west-2

deploymentMode: Distributed

# Individual component scaling
distributor:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20

ingester:
  replicas: 6
  persistence:
    enabled: true
    size: 100Gi
    storageClass: gp3
  resources:
    requests:
      cpu: 1
      memory: 4Gi
  autoscaling:
    enabled: true
    minReplicas: 6
    maxReplicas: 30

querier:
  replicas: 4
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
  autoscaling:
    enabled: true
    minReplicas: 4
    maxReplicas: 20

queryFrontend:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi

compactor:
  replicas: 1
  persistence:
    enabled: true
    size: 20Gi
  resources:
    requests:
      cpu: 1
      memory: 2Gi

ruler:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
```

### Log Collection: Promtail vs Grafana Alloy

| Feature | Promtail | Grafana Alloy |
|---------|----------|---------------|
| **Scope** | Loki-only | OTEL-native (logs, metrics, traces) |
| **Configuration** | Promtail-specific | River language (declarative) |
| **Processing** | Pipeline stages | Flow components |
| **Memory usage** | Lower | Higher (more features) |
| **Future direction** | Maintenance mode | Active development |

**Promtail DaemonSet Configuration**:

```yaml
# promtail-values.yaml
config:
  clients:
    - url: http://loki-gateway.loki.svc:80/loki/api/v1/push
      tenant_id: default
      batchwait: 1s
      batchsize: 1048576
      timeout: 10s

  positions:
    filename: /run/promtail/positions.yaml

  scrape_configs:
    # Kubernetes pod logs
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
        - role: pod
      pipeline_stages:
        - cri: {}
        - labeldrop:
            - filename
            - stream
        - match:
            selector: '{app="nginx"}'
            stages:
              - regex:
                  expression: '^(?P<remote_addr>[\d\.]+) - (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<request>[^"]+)" (?P<status>\d+) (?P<body_bytes_sent>\d+)'
              - labels:
                  status:
        - match:
            selector: '{app=~"java-.*"}'
            stages:
              - multiline:
                  firstline: '^\d{4}-\d{2}-\d{2}'
                  max_lines: 128
                  max_wait_time: 3s
      relabel_configs:
        - source_labels: [__meta_kubernetes_pod_node_name]
          target_label: node
        - source_labels: [__meta_kubernetes_namespace]
          target_label: namespace
        - source_labels: [__meta_kubernetes_pod_name]
          target_label: pod
        - source_labels: [__meta_kubernetes_pod_container_name]
          target_label: container
        - source_labels: [__meta_kubernetes_pod_label_app]
          target_label: app
        - source_labels: [__meta_kubernetes_pod_label_version]
          target_label: version
        # Drop pods without app label
        - source_labels: [__meta_kubernetes_pod_label_app]
          action: drop
          regex: ''

    # System logs
    - job_name: journal
      journal:
        max_age: 12h
        labels:
          job: systemd-journal
      relabel_configs:
        - source_labels: [__journal__systemd_unit]
          target_label: unit

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

tolerations:
  - operator: Exists

serviceMonitor:
  enabled: true
```

**Grafana Alloy Configuration** (recommended for new deployments):

```yaml
# alloy-config.yaml (River language)
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: monitoring
data:
  config.alloy: |
    // Kubernetes discovery
    discovery.kubernetes "pods" {
      role = "pod"
    }

    // Relabel for Kubernetes metadata
    discovery.relabel "pods" {
      targets = discovery.kubernetes.pods.targets

      rule {
        source_labels = ["__meta_kubernetes_namespace"]
        target_label  = "namespace"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_name"]
        target_label  = "pod"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        target_label  = "container"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        target_label  = "app"
      }
      // Drop pods without app label
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        action        = "drop"
        regex         = ""
      }
    }

    // Log collection
    loki.source.kubernetes "pods" {
      targets    = discovery.relabel.pods.output
      forward_to = [loki.process.default.receiver]
    }

    // Log processing pipeline
    loki.process "default" {
      forward_to = [loki.write.default.receiver]

      // Parse JSON logs
      stage.json {
        expressions = {
          level   = "level",
          message = "msg",
          trace_id = "trace_id",
        }
      }

      // Add trace_id label for correlation
      stage.labels {
        values = {
          level = "",
        }
      }

      // Structured metadata for trace correlation
      stage.structured_metadata {
        values = {
          trace_id = "",
        }
      }
    }

    // Write to Loki
    loki.write "default" {
      endpoint {
        url = "http://loki-gateway.loki.svc:80/loki/api/v1/push"
        tenant_id = "default"
      }
    }
```

### Label Design Strategy

Labels are critical for query performance. Loki indexes only labels, not log content.

**Recommended Labels**:

| Label | Cardinality | Purpose |
|-------|-------------|---------|
| `namespace` | Low (10-50) | Environment/team isolation |
| `app` | Low (50-200) | Application identification |
| `container` | Low | Container differentiation |
| `node` | Medium | Node-level debugging |
| `level` | Very Low (5) | Log severity filtering |

**High-Cardinality Labels to Avoid**:

| Label | Problem | Alternative |
|-------|---------|-------------|
| `pod` | Changes with each restart | Use structured metadata |
| `request_id` | Unique per request | Store in log line, use filter |
| `user_id` | Millions of values | Store in log line |
| `trace_id` | Unique per trace | Use structured metadata |
| `timestamp` | Never use as label | Built-in to Loki |

**Structured Metadata** (Loki 3.x):

```yaml
# Use structured metadata for high-cardinality data
stage.structured_metadata {
  values = {
    trace_id = "",
    request_id = "",
    user_id = "",
  }
}
```

### Retention Policy Configuration

**Global Retention**:

```yaml
loki:
  compactor:
    retention_enabled: true
    retention_delete_delay: 2h
    retention_delete_worker_count: 150

  limits_config:
    retention_period: 720h  # 30 days global default
```

**Per-Tenant Retention**:

```yaml
loki:
  limits_config:
    retention_period: 720h  # Default 30 days

  # Per-tenant overrides
  overrides:
    production:
      retention_period: 2160h  # 90 days for production
    development:
      retention_period: 168h   # 7 days for development
    compliance:
      retention_period: 8760h  # 365 days for compliance logs
```

**Stream-Level Retention** (Loki 3.x):

```yaml
limits_config:
  retention_stream:
    - selector: '{namespace="kube-system"}'
      priority: 1
      period: 168h  # 7 days for system logs
    - selector: '{app="audit-service"}'
      priority: 2
      period: 8760h  # 1 year for audit logs
```

### Index and Chunk Optimization

**TSDB Index Configuration** (recommended):

```yaml
loki:
  schemaConfig:
    configs:
      - from: "2024-01-01"
        store: tsdb  # Modern index format
        object_store: s3
        schema: v13
        index:
          prefix: loki_index_
          period: 24h
```

**Chunk Optimization**:

```yaml
loki:
  ingester:
    # Compression - snappy offers best balance
    chunk_encoding: snappy  # Options: none, gzip, lz4-64k, snappy, lz4-256k, lz4-1M, lz4, flate, zstd

    # Chunk timing
    chunk_idle_period: 30m      # Flush chunks after 30m of inactivity
    chunk_retain_period: 1m     # Keep chunks in memory after flush
    max_chunk_age: 2h           # Maximum chunk age before forced flush

    # Chunk sizing
    chunk_target_size: 1572864  # Target ~1.5MB chunks
    chunk_block_size: 262144    # 256KB blocks

    # WAL for durability
    wal:
      enabled: true
      dir: /var/loki/wal
      replay_memory_ceiling: 4GB
```

**Compression Comparison**:

| Algorithm | Compression Ratio | CPU Usage | Query Speed |
|-----------|-------------------|-----------|-------------|
| none | 1.0x | Lowest | Fastest |
| snappy | 2-3x | Low | Fast |
| lz4 | 2-4x | Low | Fast |
| gzip | 4-6x | Medium | Medium |
| zstd | 4-7x | Medium | Medium |

### LogQL Query Patterns

**Basic Queries**:

```logql
# Filter by labels
{namespace="production", app="api-gateway"}

# Filter by content
{namespace="production"} |= "error"
{namespace="production"} |~ "error|warn"
{namespace="production"} != "healthcheck"

# JSON parsing
{app="api-service"} | json | status >= 400

# Line format extraction
{app="nginx"} | pattern `<ip> - - [<_>] "<method> <path> <_>" <status> <size>`
```

**Aggregation Queries**:

```logql
# Error rate over time
sum(rate({app="api-gateway"} |= "error" [5m])) by (namespace)

# Top 10 error paths
topk(10, sum by (path) (
  count_over_time({app="nginx"} | json | status >= 500 [1h])
))

# Latency percentiles from logs
quantile_over_time(0.99,
  {app="api-service"}
  | json
  | unwrap duration
  [5m]
) by (endpoint)

# Bytes processed per namespace
sum by (namespace) (bytes_over_time({namespace=~".+"} [1h]))
```

**Performance Queries**:

```logql
# Request duration analysis
{app="api-service"}
| json
| duration > 1s
| line_format "{{.method}} {{.path}} took {{.duration}}"

# Error context with surrounding lines
{app="payment-service"} |= "PaymentFailed"
| json
| line_format "{{.timestamp}} [{{.level}}] {{.message}} trace={{.trace_id}}"
```

### Alert Rule Configuration

**Ruler Setup**:

```yaml
# loki-ruler-config.yaml
loki:
  rulerConfig:
    storage:
      type: s3
      s3:
        bucketnames: my-loki-ruler-bucket
        region: us-west-2
    rule_path: /var/loki/rules
    alertmanager_url: http://alertmanager.monitoring.svc:9093
    ring:
      kvstore:
        store: memberlist
    enable_api: true
    enable_alertmanager_v2: true
```

**Alert Rules ConfigMap**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-alerting-rules
  namespace: loki
  labels:
    loki_rule: "true"
data:
  error-alerts.yaml: |
    groups:
      - name: application-errors
        interval: 1m
        rules:
          - alert: HighErrorRate
            expr: |
              sum(rate({app=~".+"} |= "error" [5m])) by (namespace, app)
              / sum(rate({app=~".+"} [5m])) by (namespace, app)
              > 0.05
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High error rate in {{ $labels.app }}"
              description: "Error rate is {{ $value | humanizePercentage }} in {{ $labels.namespace }}/{{ $labels.app }}"
              runbook_url: "https://wiki.example.com/runbooks/high-error-rate"

          - alert: CriticalErrorSpike
            expr: |
              sum(rate({app=~".+"} |= "CRITICAL" [1m])) by (namespace, app) > 10
            for: 1m
            labels:
              severity: critical
            annotations:
              summary: "Critical error spike in {{ $labels.app }}"
              description: "{{ $value }} critical errors per second in {{ $labels.namespace }}/{{ $labels.app }}"

          - alert: PodCrashLoopDetected
            expr: |
              count_over_time({namespace=~".+", container=~".+"}
                |= "CrashLoopBackOff" [5m]) > 5
            for: 2m
            labels:
              severity: warning
            annotations:
              summary: "Pod crash loop detected"
              description: "CrashLoopBackOff detected in logs"

      - name: security-alerts
        interval: 30s
        rules:
          - alert: AuthenticationFailures
            expr: |
              sum(count_over_time(
                {app=~".*auth.*"} |= "authentication failed" [5m]
              )) by (app) > 50
            for: 2m
            labels:
              severity: warning
            annotations:
              summary: "High authentication failure rate"
              description: "{{ $value }} authentication failures in {{ $labels.app }}"

          - alert: SuspiciousActivity
            expr: |
              count_over_time({namespace="production"}
                |~ "SQL injection|XSS|unauthorized" [5m]) > 0
            labels:
              severity: critical
            annotations:
              summary: "Suspicious activity detected"
              description: "Potential security threat detected in production logs"

      - name: performance-alerts
        interval: 1m
        rules:
          - alert: SlowRequests
            expr: |
              quantile_over_time(0.95,
                {app="api-gateway"}
                | json
                | unwrap response_time_ms [5m]
              ) > 5000
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Slow API response times"
              description: "95th percentile response time is {{ $value }}ms"
```

---

## Tempo Operations Guide

### Architecture Overview

Tempo is a distributed tracing backend that stores traces in object storage without indexing. It relies on trace ID lookup and service graphs for discovery.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trace Data Flow                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Applications ──► OTEL Collector ──► Tempo Distributor          │
│  (instrumented)   (sampling)         (validation)                │
│                                           │                      │
│                                           ▼                      │
│                                      Tempo Ingester              │
│                                      (batching)                  │
│                                           │                      │
│                                           ▼                      │
│                                      S3 Storage                  │
│                                      (trace blocks)              │
│                                           │                      │
│                                           ▼                      │
│  Grafana ◄────────────────────── Tempo Querier                  │
│  (visualization)                  (trace lookup)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Helm Installation

```bash
# Install Tempo
helm upgrade --install tempo grafana/tempo \
  --namespace tempo \
  --create-namespace \
  --version 1.10.0 \
  --values tempo-values.yaml
```

**Full Production values.yaml**:

```yaml
# tempo-values.yaml
tempo:
  # Multitenancy (optional)
  multitenancyEnabled: false

  # Storage configuration
  storage:
    trace:
      backend: s3
      s3:
        bucket: my-tempo-traces-bucket
        endpoint: s3.us-west-2.amazonaws.com
        region: us-west-2
        # IRSA handles authentication
      wal:
        path: /var/tempo/wal
      block:
        version: vParquet4  # Latest format
      pool:
        max_workers: 100
        queue_depth: 10000

  # Receiver configuration
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: "0.0.0.0:4317"
        http:
          endpoint: "0.0.0.0:4318"
    jaeger:
      protocols:
        thrift_http:
          endpoint: "0.0.0.0:14268"
        grpc:
          endpoint: "0.0.0.0:14250"
    zipkin:
      endpoint: "0.0.0.0:9411"

  # Distributor configuration
  distributor:
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    log_received_spans:
      enabled: false

  # Ingester configuration
  ingester:
    max_block_duration: 5m
    max_block_bytes: 1073741824  # 1GB
    flush_check_period: 10s
    trace_idle_period: 10s
    lifecycler:
      ring:
        kvstore:
          store: memberlist
        replication_factor: 3

  # Compactor configuration
  compactor:
    compaction:
      block_retention: 336h  # 14 days
      compacted_block_retention: 1h
      compaction_window: 1h
      max_compaction_objects: 6
      max_block_bytes: 107374182400  # 100GB
      retention_concurrency: 10

  # Querier configuration
  querier:
    frontend_worker:
      frontend_address: tempo-query-frontend:9095
    max_concurrent_queries: 20
    search:
      external_endpoints: []
      prefer_self: 10
    trace_by_id:
      query_timeout: 30s

  # Query frontend
  query_frontend:
    max_retries: 2
    search:
      concurrent_jobs: 1000
      target_bytes_per_job: 104857600
    trace_by_id:
      hedge_requests_at: 2s
      hedge_requests_up_to: 2

  # Metrics generator (for RED metrics from traces)
  metrics_generator:
    registry:
      external_labels:
        source: tempo
        cluster: production
    storage:
      path: /var/tempo/generator/wal
      remote_write:
        - url: http://prometheus:9090/api/v1/write
          send_exemplars: true
    processor:
      service_graphs:
        dimensions:
          - service.namespace
          - http.method
        histogram_buckets: [0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        max_items: 10000
        wait: 10s
        workers: 10
      span_metrics:
        dimensions:
          - service.name
          - span.name
          - span.kind
          - status.code
        histogram_buckets: [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.512, 1.024, 2.048, 4.096, 8.192, 16.384]

  # Overrides
  overrides:
    defaults:
      metrics_generator:
        processors:
          - service-graphs
          - span-metrics

# Global settings
global:
  clusterDomain: cluster.local

# Service account for IRSA
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/TempoS3Role

# Component resources
distributor:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 1Gi

ingester:
  replicas: 3
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi

querier:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 1
      memory: 2Gi

queryFrontend:
  replicas: 2
  resources:
    requests:
      cpu: 200m
      memory: 256Mi

compactor:
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2
      memory: 4Gi

metricsGenerator:
  enabled: true
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi

# Monitoring
serviceMonitor:
  enabled: true
  labels:
    release: prometheus
```

### OTEL Collector Configuration

**Full ConfigMap**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: monitoring
data:
  otel-collector.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
            max_recv_msg_size_mib: 4
          http:
            endpoint: 0.0.0.0:4318

      # Kubernetes events as traces (optional)
      k8s_events:
        namespaces: [default, production]

    processors:
      # Memory limiter to prevent OOM
      memory_limiter:
        check_interval: 1s
        limit_mib: 1500
        spike_limit_mib: 512

      # Batch processing
      batch:
        send_batch_size: 10000
        send_batch_max_size: 11000
        timeout: 10s

      # Resource detection for Kubernetes
      resourcedetection:
        detectors: [env, eks, ec2]
        timeout: 5s
        override: false

      # Add Kubernetes metadata
      k8sattributes:
        auth_type: serviceAccount
        passthrough: false
        extract:
          metadata:
            - k8s.namespace.name
            - k8s.pod.name
            - k8s.pod.uid
            - k8s.deployment.name
            - k8s.node.name
          labels:
            - tag_name: app
              key: app
              from: pod
            - tag_name: version
              key: version
              from: pod
        pod_association:
          - sources:
              - from: resource_attribute
                name: k8s.pod.ip
          - sources:
              - from: resource_attribute
                name: k8s.pod.uid

      # Tail-based sampling (process after batch)
      tail_sampling:
        decision_wait: 30s
        num_traces: 100000
        expected_new_traces_per_sec: 1000
        policies:
          # Always sample errors
          - name: errors-policy
            type: status_code
            status_code:
              status_codes: [ERROR]

          # Always sample slow traces (> 2s)
          - name: latency-policy
            type: latency
            latency:
              threshold_ms: 2000

          # Sample 10% of successful traces
          - name: probabilistic-policy
            type: probabilistic
            probabilistic:
              sampling_percentage: 10

          # Always sample specific services
          - name: critical-services
            type: string_attribute
            string_attribute:
              key: service.name
              values: [payment-service, order-service]
              enabled_regex_matching: false
              invert_match: false

          # Rate limiting fallback
          - name: rate-limiting
            type: rate_limiting
            rate_limiting:
              spans_per_second: 1000

      # Attributes processing
      attributes:
        actions:
          - key: environment
            value: production
            action: insert
          - key: db.statement
            action: hash  # Hash sensitive data
          - key: http.request.header.authorization
            action: delete  # Remove auth headers

    exporters:
      # Export to Tempo
      otlp/tempo:
        endpoint: tempo-distributor.tempo.svc:4317
        tls:
          insecure: true
        retry_on_failure:
          enabled: true
          initial_interval: 5s
          max_interval: 30s
          max_elapsed_time: 300s

      # Export metrics to Prometheus
      prometheus:
        endpoint: 0.0.0.0:8889
        namespace: otel
        const_labels:
          source: otel-collector

      # Debug logging (disable in production)
      # debug:
      #   verbosity: detailed

    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
      pprof:
        endpoint: 0.0.0.0:1777
      zpages:
        endpoint: 0.0.0.0:55679

    service:
      extensions: [health_check, pprof, zpages]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, resourcedetection, k8sattributes, batch, tail_sampling, attributes]
          exporters: [otlp/tempo]
        metrics:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [prometheus]
      telemetry:
        logs:
          level: info
        metrics:
          address: 0.0.0.0:8888
```

**OTEL Collector Deployment**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      serviceAccountName: otel-collector
      containers:
        - name: otel-collector
          image: otel/opentelemetry-collector-contrib:0.100.0
          command:
            - "/otelcol-contrib"
            - "--config=/etc/otel/otel-collector.yaml"
          ports:
            - containerPort: 4317  # OTLP gRPC
            - containerPort: 4318  # OTLP HTTP
            - containerPort: 8888  # Metrics
            - containerPort: 8889  # Prometheus exporter
            - containerPort: 13133 # Health check
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
          volumeMounts:
            - name: config
              mountPath: /etc/otel
          livenessProbe:
            httpGet:
              path: /
              port: 13133
          readinessProbe:
            httpGet:
              path: /
              port: 13133
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
```

### Sampling Strategies

#### Head-Based Sampling

Applied at the source (application or first collector):

**Probabilistic Sampling**:

```yaml
# In application SDK or collector
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # Sample 10% of traces
    hash_seed: 22
```

**Rate Limiting**:

```yaml
processors:
  rate_limiting:
    spans_per_second: 1000  # Maximum 1000 spans/sec
```

#### Tail-Based Sampling

Applied after seeing the complete trace:

```yaml
processors:
  tail_sampling:
    decision_wait: 30s
    num_traces: 100000
    policies:
      # Error-based: always capture errors
      - name: error-policy
        type: status_code
        status_code:
          status_codes: [ERROR, UNSET]

      # Latency-based: capture slow traces
      - name: latency-policy
        type: latency
        latency:
          threshold_ms: 2000

      # Attribute-based: specific operations
      - name: database-queries
        type: string_attribute
        string_attribute:
          key: db.system
          values: [postgresql, mysql, mongodb]

      # Composite policy
      - name: composite-policy
        type: composite
        composite:
          max_total_spans_per_second: 1000
          policy_order: [error-policy, latency-policy, probabilistic-fallback]
          composite_sub_policy:
            - name: error-policy
              type: status_code
              status_code:
                status_codes: [ERROR]
            - name: latency-policy
              type: latency
              latency:
                threshold_ms: 1000
            - name: probabilistic-fallback
              type: probabilistic
              probabilistic:
                sampling_percentage: 5
          rate_allocation:
            - policy: error-policy
              percent: 50
            - policy: latency-policy
              percent: 30
            - policy: probabilistic-fallback
              percent: 20
```

### TraceQL Query Examples

**Basic Queries**:

```
# Find trace by ID
{ trace:id = "abc123" }

# Find traces by service name
{ resource.service.name = "api-gateway" }

# Find traces with errors
{ status = error }

# Find traces by span name
{ name = "HTTP GET /api/users" }

# Find slow database queries
{ span.db.system = "postgresql" && duration > 100ms }
```

**Advanced Queries**:

```
# Find traces with specific attribute patterns
{ resource.service.name =~ "order-.*" && span.http.status_code >= 500 }

# Duration analysis
{ duration > 2s && resource.service.name = "payment-service" }

# Find traces with specific span hierarchy
{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }

# Aggregate queries
{ resource.service.name = "api-gateway" } | rate()

# Count by status
{ } | count() by (status)

# Histogram of durations
{ resource.service.name = "api-gateway" } | histogram_over_time(duration)
```

### Service Graph Configuration

```yaml
# In Tempo config
tempo:
  metrics_generator:
    processor:
      service_graphs:
        dimensions:
          - service.namespace
          - http.method
          - http.target
        histogram_buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        max_items: 10000
        wait: 10s
        workers: 10
```

### Trace-to-Log Integration

**Application-Side Configuration (Java)**:

```java
// Add trace ID to MDC for logging
import io.opentelemetry.api.trace.Span;
import org.slf4j.MDC;

public class TracingFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) {
        Span currentSpan = Span.current();
        String traceId = currentSpan.getSpanContext().getTraceId();
        String spanId = currentSpan.getSpanContext().getSpanId();

        MDC.put("trace_id", traceId);
        MDC.put("span_id", spanId);
        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove("trace_id");
            MDC.remove("span_id");
        }
    }
}
```

**Logback Configuration**:

```xml
<configuration>
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>trace_id</includeMdcKeyName>
      <includeMdcKeyName>span_id</includeMdcKeyName>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

**Grafana Data Source Configuration**:

```yaml
# In Grafana datasource provisioning
apiVersion: 1
datasources:
  - name: Tempo
    type: tempo
    url: http://tempo-query-frontend.tempo.svc:3100
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['app', 'namespace']
        mappedTags: [{ key: 'service.name', value: 'app' }]
        mapTagNamesEnabled: true
        spanStartTimeShift: '-1h'
        spanEndTimeShift: '1h'
        filterByTraceID: true
        filterBySpanID: false
        lokiSearch: true
      tracesToMetrics:
        datasourceUid: prometheus
        tags: [{ key: 'service.name', value: 'service' }]
        queries:
          - name: 'Request rate'
            query: 'sum(rate(http_server_requests_seconds_count{$$__tags}[5m]))'
          - name: 'Error rate'
            query: 'sum(rate(http_server_requests_seconds_count{$$__tags,status=~"5.."}[5m]))'
      serviceMap:
        datasourceUid: prometheus
```

### Span Metrics Generator

Generate RED (Rate, Errors, Duration) metrics from trace data:

```yaml
tempo:
  metrics_generator:
    registry:
      external_labels:
        source: tempo
        cluster: production
    storage:
      path: /var/tempo/generator/wal
      remote_write:
        - url: http://prometheus:9090/api/v1/write
          send_exemplars: true
    processor:
      span_metrics:
        dimensions:
          - service.name
          - span.name
          - span.kind
          - status.code
          - http.method
          - http.status_code
        histogram_buckets: [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128, 0.256, 0.512, 1.024, 2.048, 4.096, 8.192, 16.384]
        intrinsic_dimensions:
          service: true
          span_name: true
          span_kind: true
          status_code: true
          status_message: false
```

**Generated Metrics**:

```promql
# Request rate by service
sum(rate(traces_spanmetrics_calls_total[5m])) by (service)

# Error rate
sum(rate(traces_spanmetrics_calls_total{status_code="STATUS_CODE_ERROR"}[5m])) by (service)
/ sum(rate(traces_spanmetrics_calls_total[5m])) by (service)

# Latency percentiles
histogram_quantile(0.99, sum(rate(traces_spanmetrics_latency_bucket[5m])) by (le, service))
```

---

## Prometheus/Amazon Managed Prometheus Operations

### AMP Workspace Terraform

```hcl
# amp.tf
resource "aws_prometheus_workspace" "main" {
  alias = "eks-production-metrics"

  logging_configuration {
    log_group_arn = "${aws_cloudwatch_log_group.amp.arn}:*"
  }

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "amp" {
  name              = "/aws/prometheus/eks-production"
  retention_in_days = 30
}

# IAM role for remote write
resource "aws_iam_role" "prometheus_remote_write" {
  name = "prometheus-remote-write-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = module.eks.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${module.eks.oidc_provider}:sub" = "system:serviceaccount:monitoring:prometheus"
            "${module.eks.oidc_provider}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "prometheus_remote_write" {
  role       = aws_iam_role.prometheus_remote_write.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonPrometheusRemoteWriteAccess"
}

# Output for Prometheus configuration
output "amp_workspace_endpoint" {
  value = aws_prometheus_workspace.main.prometheus_endpoint
}

output "prometheus_role_arn" {
  value = aws_iam_role.prometheus_remote_write.arn
}
```

### Remote Write Configuration

```yaml
# prometheus-values.yaml with AMP remote write
prometheus:
  prometheusSpec:
    # Remote write to AMP
    remoteWrite:
      - url: https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/api/v1/remote_write
        sigv4:
          region: us-west-2
        queueConfig:
          maxSamplesPerSend: 1000
          maxShards: 200
          capacity: 2500
          batchSendDeadline: 5s
          minBackoff: 100ms
          maxBackoff: 5s
        writeRelabelConfigs:
          # Drop high-cardinality metrics
          - sourceLabels: [__name__]
            regex: 'go_.*|process_.*'
            action: drop
          # Keep only needed labels
          - regex: 'pod_template_hash|controller_revision_hash'
            action: labeldrop

    # WAL configuration for reliability
    walCompression: true

    # Retention for local storage (before remote write)
    retention: 2h
    retentionSize: 10GB

    # Resources
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2
        memory: 8Gi

    # Storage for WAL
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi

  # Service account with IRSA
  serviceAccount:
    create: true
    name: prometheus
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/prometheus-remote-write-role
```

### Recording Rules Optimization

```yaml
# recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
    - name: kubernetes.rules
      interval: 30s
      rules:
        # Pre-aggregate CPU usage
        - record: namespace:container_cpu_usage_seconds_total:sum_rate
          expr: |
            sum by (namespace) (
              rate(container_cpu_usage_seconds_total{container!="",pod!=""}[5m])
            )

        # Pre-aggregate memory usage
        - record: namespace:container_memory_working_set_bytes:sum
          expr: |
            sum by (namespace) (
              container_memory_working_set_bytes{container!="",pod!=""}
            )

        # Pre-aggregate network traffic
        - record: namespace:container_network_receive_bytes_total:sum_rate
          expr: |
            sum by (namespace) (
              rate(container_network_receive_bytes_total[5m])
            )

    - name: application.rules
      interval: 30s
      rules:
        # Request rate by service
        - record: service:http_requests_total:rate5m
          expr: |
            sum by (service, namespace) (
              rate(http_requests_total[5m])
            )

        # Error rate by service
        - record: service:http_requests_errors:rate5m
          expr: |
            sum by (service, namespace) (
              rate(http_requests_total{status=~"5.."}[5m])
            )

        # Latency percentiles
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum by (service, namespace, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )

        - record: service:http_request_duration_seconds:p95
          expr: |
            histogram_quantile(0.95,
              sum by (service, namespace, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )

        - record: service:http_request_duration_seconds:p50
          expr: |
            histogram_quantile(0.50,
              sum by (service, namespace, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )
```

### Long-Term Retention: Thanos vs AMP

| Feature | Thanos | Amazon Managed Prometheus |
|---------|--------|---------------------------|
| **Retention** | Unlimited (S3) | 150 days |
| **Scaling** | Manual | Automatic |
| **Cost** | S3 + compute | Per-sample ingested + queried |
| **Operations** | High (multiple components) | None (managed) |
| **Query Federation** | Native (Querier) | Cross-workspace queries |
| **Downsampling** | Automatic (5m, 1h) | Not supported |
| **Global View** | Multi-cluster native | Cross-region requires setup |
| **HA** | Deduplication built-in | Managed |

**When to choose Thanos**:
- Need >150 days retention
- Require downsampling for cost optimization
- Multi-cloud or hybrid deployments
- Complex federation requirements

**When to choose AMP**:
- Want zero operations overhead
- 150 days retention is sufficient
- AWS-native stack
- Predictable, usage-based pricing

### Multi-Cluster Federation

**With AMP**:

```yaml
# Each cluster writes to shared AMP workspace with cluster label
prometheus:
  prometheusSpec:
    externalLabels:
      cluster: production-us-west-2
    remoteWrite:
      - url: https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-shared/api/v1/remote_write
        sigv4:
          region: us-west-2
```

**Query across clusters**:

```promql
# Aggregate CPU across all clusters
sum by (cluster) (
  namespace:container_cpu_usage_seconds_total:sum_rate
)

# Compare error rates between clusters
sum by (cluster, service) (
  service:http_requests_errors:rate5m
)
```

---

## Grafana Integration

### Datasource Provisioning

```yaml
# grafana-datasources.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
  labels:
    grafana_datasource: "1"
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      # Amazon Managed Prometheus
      - name: AMP
        type: prometheus
        uid: prometheus
        url: https://aps-workspaces.us-west-2.amazonaws.com/workspaces/ws-xxxxxxxx/
        access: proxy
        isDefault: true
        jsonData:
          httpMethod: POST
          sigV4Auth: true
          sigV4AuthType: default
          sigV4Region: us-west-2
        editable: false

      # Loki
      - name: Loki
        type: loki
        uid: loki
        url: http://loki-gateway.loki.svc:80
        access: proxy
        jsonData:
          maxLines: 1000
          derivedFields:
            - datasourceUid: tempo
              matcherRegex: '"trace_id":"(\w+)"'
              name: TraceID
              url: '$${__value.raw}'
        editable: false

      # Tempo
      - name: Tempo
        type: tempo
        uid: tempo
        url: http://tempo-query-frontend.tempo.svc:3100
        access: proxy
        jsonData:
          httpMethod: GET
          tracesToLogs:
            datasourceUid: loki
            tags: ['app', 'namespace', 'pod']
            mappedTags: [{ key: 'service.name', value: 'app' }]
            mapTagNamesEnabled: true
            spanStartTimeShift: '-1h'
            spanEndTimeShift: '1h'
            filterByTraceID: true
            lokiSearch: true
          tracesToMetrics:
            datasourceUid: prometheus
            tags: [{ key: 'service.name', value: 'service' }]
            queries:
              - name: 'Request rate'
                query: 'sum(rate(http_server_requests_seconds_count{$$__tags}[5m]))'
              - name: 'Error rate'
                query: 'sum(rate(http_server_requests_seconds_count{$$__tags,status=~"5.."}[5m]))'
              - name: 'P99 latency'
                query: 'histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{$$__tags}[5m])) by (le))'
          serviceMap:
            datasourceUid: prometheus
          nodeGraph:
            enabled: true
          lokiSearch:
            datasourceUid: loki
        editable: false
```

### Loki to Tempo: Derived Fields

Configure in Loki datasource to link trace IDs to Tempo:

```yaml
jsonData:
  derivedFields:
    # JSON logs with trace_id field
    - datasourceUid: tempo
      matcherRegex: '"trace_id":"([a-f0-9]+)"'
      name: TraceID
      url: '$${__value.raw}'
      urlDisplayLabel: 'View Trace'

    # Structured logs with traceID field
    - datasourceUid: tempo
      matcherRegex: 'traceID=([a-f0-9]+)'
      name: TraceID
      url: '$${__value.raw}'

    # OpenTelemetry format
    - datasourceUid: tempo
      matcherRegex: 'trace_id=([a-f0-9]{32})'
      name: TraceID
      url: '$${__value.raw}'
```

### Tempo to Loki: Trace-to-Logs

```yaml
jsonData:
  tracesToLogs:
    datasourceUid: loki
    tags: ['app', 'namespace', 'pod', 'container']
    mappedTags:
      - key: 'service.name'
        value: 'app'
      - key: 'k8s.namespace.name'
        value: 'namespace'
      - key: 'k8s.pod.name'
        value: 'pod'
    mapTagNamesEnabled: true
    spanStartTimeShift: '-5m'
    spanEndTimeShift: '5m'
    filterByTraceID: true
    filterBySpanID: false
    lokiSearch: true
```

### Exemplars Setup

**Prometheus Configuration**:

```yaml
prometheus:
  prometheusSpec:
    enableFeatures:
      - exemplar-storage
    exemplars:
      maxSize: 100000
```

**Application Instrumentation (Java)**:

```java
// Micrometer with OpenTelemetry exemplars
@Bean
public MeterRegistryCustomizer<PrometheusMeterRegistry> exemplarCustomizer() {
    return registry -> {
        registry.config().meterFilter(new MeterFilter() {
            @Override
            public DistributionStatisticConfig configure(Meter.Id id, DistributionStatisticConfig config) {
                return DistributionStatisticConfig.builder()
                    .percentilesHistogram(true)
                    .build()
                    .merge(config);
            }
        });
    };
}
```

**Query with Exemplars in Grafana**:

```promql
# Enable exemplars in panel options, then query
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

### Dashboard Provisioning Automation

```yaml
# grafana-dashboard-provisioning.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-provider
  namespace: monitoring
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
      - name: 'default'
        orgId: 1
        folder: 'Kubernetes'
        folderUid: 'kubernetes'
        type: file
        disableDeletion: false
        editable: true
        updateIntervalSeconds: 30
        options:
          path: /var/lib/grafana/dashboards/kubernetes

      - name: 'applications'
        orgId: 1
        folder: 'Applications'
        folderUid: 'applications'
        type: file
        disableDeletion: false
        editable: true
        updateIntervalSeconds: 30
        options:
          path: /var/lib/grafana/dashboards/applications

      - name: 'slos'
        orgId: 1
        folder: 'SLOs'
        folderUid: 'slos'
        type: file
        disableDeletion: false
        editable: true
        updateIntervalSeconds: 30
        options:
          path: /var/lib/grafana/dashboards/slos
```

**Dashboard ConfigMap Example**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-k8s-overview
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  k8s-overview.json: |
    {
      "uid": "k8s-overview",
      "title": "Kubernetes Overview",
      "tags": ["kubernetes"],
      "timezone": "browser",
      "panels": [
        {
          "title": "Cluster CPU Usage",
          "type": "timeseries",
          "datasource": { "uid": "prometheus" },
          "targets": [
            {
              "expr": "sum(namespace:container_cpu_usage_seconds_total:sum_rate)",
              "legendFormat": "Total CPU"
            }
          ]
        }
      ]
    }
```

---

## Related Documentation

- [Monitoring Stack Overview](../observability/README.md) - VictoriaMetrics, Prometheus, and Grafana fundamentals
- [Logging Stack Overview](../observability/logging/README.md) - Loki and Tempo introduction

---

< [Previous: Observability Analysis](./08-observability-analysis.md) | [Table of Contents](./README.md) | [Next: Resource Optimization](./10-resource-optimization.md) >
