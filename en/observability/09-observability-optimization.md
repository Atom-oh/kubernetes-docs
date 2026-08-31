# EKS Observability Optimization Guide

> **Supported versions**: Amazon EKS 1.29+, OpenTelemetry 0.90+
> **Last updated**: February 2025

---

## Table of Contents

1. [Overview of the Three Pillars of Observability](#1-overview-of-the-three-pillars-of-observability)
2. [Logging Solution Comparison](#2-logging-solution-comparison)
3. [Metrics Collection and Storage](#3-metrics-collection-and-storage)
4. [Distributed Tracing](#4-distributed-tracing)
5. [eBPF-Based No-Code Monitoring](#5-ebpf-based-no-code-monitoring)
6. [Cost Monitoring](#6-cost-monitoring)
7. [Unified Observability Dashboard](#7-unified-observability-dashboard)
8. [Operational Challenges and Solutions](#8-operational-challenges-and-solutions)
9. [Best Practices and Next Steps](#9-best-practices-and-next-steps)

---

## 1. Overview of the Three Pillars of Observability

In modern cloud-native environments, **observability** is the ability to understand the internal state of a system through its external outputs. To implement effective observability in EKS environments, you need to understand three key pillars.

### 1.1 Relationship Between Logging, Metrics, and Tracing

![Logging, Metrics, and Tracing shown as three peer pillars, each with its own data shape and best-fit question, linked by a dashed cycle of correlation signals — exemplars, trace context, and correlation IDs — that let an engineer jump between them.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-0.svg)

### 1.2 Role of Each Pillar and Selection Criteria

| Pillar | Primary Role | Question Type | Data Volume | Cost Characteristics |
|---|---|---|---|---|
| **Logging** | Event recording, auditing, debugging | "What happened?" | High | High storage costs |
| **Metrics** | System state monitoring, alerting | "Is the system healthy?" | Medium | Sensitive to cardinality |
| **Tracing** | Request flow tracking, bottleneck analysis | "Why is it slow?" | High (sampling required) | Proportional to sampling rate |

### 1.3 Overall EKS Observability Architecture

![Application pods emit data to Fluent Bit and the OTel Collector, which fan out to log, metrics, and trace storage backends alongside Prometheus, all converging into Grafana as the single-pane-of-glass dashboard.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-1.svg)

---

## 2. Logging Solution Comparison

### 2.1 Log Storage Comparison

| Criteria | CloudWatch Logs | OpenSearch | Loki | ClickHouse |
|---|---|---|---|---|
| **Cost** | Ingestion: $0.50/GB<br/>Storage: $0.03/GB/month | Instance cost + EBS<br/>r6g.large: ~$150/month | Object storage cost<br/>S3: $0.023/GB/month | Instance + storage<br/>Reduced by high compression |
| **Performance** | Excellent for small scale<br/>Latency at large scale | Optimized for full-text search<br/>Strong for complex queries | Fast label-based filtering<br/>Limited full-text search | Optimized for analytical queries<br/>Excellent real-time aggregation |
| **Operational Complexity** | Fully managed<br/>Minimal operational burden | Cluster management required<br/>Complex tuning | Simple architecture<br/>Easy to operate | Schema management required<br/>Medium complexity |
| **Query Capabilities** | Logs Insights<br/>Basic analysis | Lucene query<br/>Powerful full-text search | LogQL<br/>Label-based filtering | SQL-based<br/>Complex analytical queries |
| **Scalability** | Auto-scaling<br/>Unlimited | Manual sharding<br/>Node addition required | Easy horizontal scaling<br/>Leverages object storage | Sharding support<br/>Petabyte scale |
| **Suitable Use Cases** | AWS-native environments<br/>Simple logging | Complex search requirements<br/>Security/compliance | Cost-efficiency focused<br/>Grafana integration | Log analysis/aggregation<br/>Long-term retention |

### 2.2 Log Agent Comparison

| Criteria | Fluent Bit | Fluentd | Vector |
|---|---|---|---|
| **Memory Usage** | ~15MB | ~60MB | ~30MB |
| **CPU Usage** | Low | Medium | Low |
| **Throughput** | Up to ~200K msg/s | Up to ~50K msg/s | Up to ~300K msg/s |
| **Language** | C | Ruby/C | Rust |
| **Plugin Ecosystem** | Limited but core support | Very rich | Growing |
| **Configuration Complexity** | Low | Medium | Medium |
| **EKS Integration** | Native support | Supported | Supported |

### 2.3 Fluent Bit + Loki Configuration Example for EKS

```yaml
# fluent-bit-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf
        HTTP_Server   On
        HTTP_Listen   0.0.0.0
        HTTP_Port     2020

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            docker
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

    [OUTPUT]
        Name                   loki
        Match                  *
        Host                   loki-gateway.logging.svc.cluster.local
        Port                   80
        Labels                 job=fluent-bit
        Label_Keys             $kubernetes['namespace_name'],$kubernetes['pod_name'],$kubernetes['container_name']
        Remove_Keys            kubernetes,stream
        Auto_Kubernetes_Labels on
        Line_Format            json

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L
        Time_Keep   On

    [PARSER]
        Name        json
        Format      json
        Time_Key    timestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%L
---
# fluent-bit-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          effect: NoSchedule
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:2.2
          resources:
            limits:
              memory: 200Mi
              cpu: 200m
            requests:
              memory: 100Mi
              cpu: 100m
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
              readOnly: true
            - name: config
              mountPath: /fluent-bit/etc/
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
        - name: config
          configMap:
            name: fluent-bit-config
```

```bash
# Install Loki (Helm)
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Loki in Simple Scalable mode
helm install loki grafana/loki \
  --namespace logging \
  --create-namespace \
  --set loki.auth_enabled=false \
  --set loki.storage.type=s3 \
  --set loki.storage.s3.endpoint=s3.ap-northeast-2.amazonaws.com \
  --set loki.storage.s3.region=ap-northeast-2 \
  --set loki.storage.s3.bucketnames=my-loki-bucket \
  --set loki.storage.s3.insecure=false \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT:role/LokiS3Role
```

---

## 3. Metrics Collection and Storage

### 3.1 Metrics Storage Comparison

| Criteria | Prometheus | VictoriaMetrics | AMP (Amazon Managed Prometheus) |
|---|---|---|---|
| **Scalability** | Single node<br/>Vertical scaling only | Cluster mode<br/>Horizontal scaling | Auto-scaling<br/>Unlimited |
| **Cost** | Infrastructure cost only<br/>EC2/EBS | Infrastructure cost<br/>Savings vs Prometheus | Ingestion: $0.90/10M samples<br/>Storage: $0.03/GB/month |
| **HA** | Separate configuration required<br/>Thanos/Cortex | Built-in replication<br/>Automatic failover | Fully managed HA<br/>Multi-AZ |
| **Operational Overhead** | High<br/>Storage/scaling management | Medium<br/>Simple operations | Low<br/>AWS managed |
| **Long-term Storage** | Separate solution required | Built-in support | Unlimited retention |
| **Query Performance** | Excellent | Very excellent<br/>(Optimized engine) | Excellent |
| **PromQL Compatibility** | Native | Fully compatible + extensions | Fully compatible |

### 3.2 Cardinality Management Strategy

**Cardinality** refers to the number of unique time series. High cardinality directly impacts memory usage and query performance.

```yaml
# prometheus-config.yaml - Metric dropping and label optimization
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s
      evaluation_interval: 30s

    scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          # Collect only specific namespaces
          - source_labels: [__meta_kubernetes_namespace]
            regex: 'kube-system|monitoring|production'
            action: keep

          # Remove unnecessary labels
          - regex: '__meta_kubernetes_pod_label_(.+)'
            action: labeldrop

          # Remove Pod UID (high cardinality cause)
          - regex: 'pod_template_hash|controller_revision_hash'
            action: labeldrop

        metric_relabel_configs:
          # Drop unnecessary metrics
          - source_labels: [__name__]
            regex: 'go_.*|promhttp_.*'
            action: drop

          # Limit histogram buckets (major high cardinality culprit)
          - source_labels: [__name__, le]
            regex: '.*_bucket;(0\.001|0\.005|0\.01|0\.05|0\.1|0\.5|1|5|10|30|60|120|300)'
            action: keep
```

### 3.3 Improving Query Performance with Recording Rules

Recording Rules pre-compute complex queries and store the results.

```yaml
# prometheus-recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: recording-rules
  namespace: monitoring
spec:
  groups:
    - name: k8s.rules
      interval: 30s
      rules:
        # Pre-compute CPU utilization per node
        - record: node:cpu_utilization:ratio
          expr: |
            1 - avg by (node) (
              rate(node_cpu_seconds_total{mode="idle"}[5m])
            )

        # Memory utilization per node
        - record: node:memory_utilization:ratio
          expr: |
            1 - (
              node_memory_MemAvailable_bytes
              / node_memory_MemTotal_bytes
            )

        # CPU usage per namespace
        - record: namespace:container_cpu_usage_seconds_total:sum_rate
          expr: |
            sum by (namespace) (
              rate(container_cpu_usage_seconds_total{container!=""}[5m])
            )

        # Pod restart count (hourly)
        - record: namespace:pod_restarts:sum_increase1h
          expr: |
            sum by (namespace) (
              increase(kube_pod_container_status_restarts_total[1h])
            )

    - name: slo.rules
      interval: 30s
      rules:
        # Error rate per service
        - record: service:http_requests:error_rate5m
          expr: |
            sum by (service) (
              rate(http_requests_total{status=~"5.."}[5m])
            )
            /
            sum by (service) (
              rate(http_requests_total[5m])
            )

        # P99 latency per service
        - record: service:http_request_duration_seconds:p99
          expr: |
            histogram_quantile(0.99,
              sum by (service, le) (
                rate(http_request_duration_seconds_bucket[5m])
              )
            )
```

### 3.4 Long-term Storage Strategy

![Prometheus's 7-day local storage remote-writes to three long-term backend choices — Thanos, VictoriaMetrics, or AMP — each with its own query layer, all converging on Grafana as the single query surface.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-2.svg)

---

## 4. Distributed Tracing

### 4.1 OpenTelemetry Overview and Architecture

OpenTelemetry (OTel) is a vendor-neutral standard for collecting and exporting observability data (traces, metrics, logs).

![Application services send OTLP data through the OTel Collector's receive, batch, and attribute stages into tail sampling, which decides what survives and routes surviving spans to Tempo/Jaeger, AWS X-Ray, or a Prometheus exporter.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-3.svg)

### 4.2 Tracing Backend Comparison

| Criteria | Grafana Tempo | Jaeger | AWS X-Ray |
|---|---|---|---|
| **Architecture** | Object storage-based<br/>No index | Elasticsearch/Cassandra<br/>Index-based | AWS managed<br/>Serverless |
| **Cost** | S3 storage cost only<br/>Very inexpensive | Infrastructure cost<br/>Index storage | Per-trace pricing<br/>$5/million traces |
| **Scalability** | Unlimited<br/>Horizontal scaling | Node addition required<br/>Index management | Auto-scaling<br/>Unlimited |
| **Query Method** | Direct TraceID lookup<br/>Exemplars integration | Tag-based search<br/>Time range search | Service map<br/>Filter search |
| **Grafana Integration** | Native | Supported | Limited |
| **AWS Integration** | Separate configuration | Separate configuration | Native<br/>Lambda, ECS, etc. |
| **Suitable Use Cases** | Cost-efficiency focused<br/>Grafana stack | Complex search requirements<br/>Self-hosted infrastructure | AWS-native<br/>Serverless environments |

### 4.3 Sampling Strategies

```yaml
# otel-collector-config.yaml - Sampling strategy configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

    processors:
      # Batch processing - performance optimization
      batch:
        timeout: 5s
        send_batch_size: 1000
        send_batch_max_size: 1500

      # Memory limit - OOM prevention
      memory_limiter:
        check_interval: 1s
        limit_mib: 1000
        spike_limit_mib: 200

      # Probabilistic sampling - Head Sampling
      probabilistic_sampler:
        hash_seed: 22
        sampling_percentage: 10  # 10% sampling

      # Tail Sampling - condition-based sampling
      tail_sampling:
        decision_wait: 10s
        num_traces: 100000
        policies:
          # Keep 100% of traces with errors
          - name: errors
            type: status_code
            status_code:
              status_codes: [ERROR]

          # Keep 100% of high-latency traces
          - name: slow-traces
            type: latency
            latency:
              threshold_ms: 1000

          # Keep 100% of traces from specific services
          - name: critical-services
            type: string_attribute
            string_attribute:
              key: service.name
              values: [payment-service, order-service]

          # Sample only 5% of the rest
          - name: default
            type: probabilistic
            probabilistic:
              sampling_percentage: 5

      # Add/remove attributes
      attributes:
        actions:
          - key: environment
            value: production
            action: upsert
          - key: sensitive_data
            action: delete

    exporters:
      otlp:
        endpoint: tempo-distributor.observability:4317
        tls:
          insecure: true

      awsxray:
        region: ap-northeast-2

      debug:
        verbosity: detailed

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch, tail_sampling, attributes]
          exporters: [otlp, awsxray]
```

### 4.4 OTel Collector DaemonSet Configuration for EKS

```yaml
# otel-collector-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-collector
  namespace: observability
  labels:
    app: otel-collector
spec:
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
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.92.0
          args:
            - --config=/conf/config.yaml
          ports:
            - containerPort: 4317  # OTLP gRPC
              hostPort: 4317
            - containerPort: 4318  # OTLP HTTP
              hostPort: 4318
            - containerPort: 8888  # Metrics
          resources:
            limits:
              memory: 1Gi
              cpu: 500m
            requests:
              memory: 200Mi
              cpu: 100m
          volumeMounts:
            - name: config
              mountPath: /conf
          env:
            - name: K8S_NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
            - name: K8S_POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: K8S_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
      volumes:
        - name: config
          configMap:
            name: otel-collector-config
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          effect: NoSchedule
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  selector:
    app: otel-collector
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
    - name: metrics
      port: 8888
      targetPort: 8888
```

Auto-instrumentation configuration with OTel SDK for applications:

```yaml
# Adding auto-instrumentation to application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
spec:
  template:
    metadata:
      annotations:
        # Enable OTel Operator auto-instrumentation
        instrumentation.opentelemetry.io/inject-java: "true"
        # Or for Python, Node.js, etc.
        # instrumentation.opentelemetry.io/inject-python: "true"
        # instrumentation.opentelemetry.io/inject-nodejs: "true"
    spec:
      containers:
        - name: app
          image: my-app:latest
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://otel-collector.observability:4317"
            - name: OTEL_SERVICE_NAME
              value: "my-app"
            - name: OTEL_RESOURCE_ATTRIBUTES
              value: "service.namespace=production,deployment.environment=prod"
```

---

## 5. eBPF-Based No-Code Monitoring

### 5.1 Why eBPF Monitoring

**eBPF (extended Berkeley Packet Filter)** is a technology that allows safe program execution within the Linux kernel. The biggest advantage of eBPF-based monitoring is achieving observability **without code modifications**.

![Traditional code-based instrumentation requires adding an SDK and redeploying code before data collection begins, while eBPF instrumentation reaches the same data collection through kernel-level hooks without any change to the running application.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-4.svg)

| Characteristic | Traditional Instrumentation | eBPF Instrumentation |
|---|---|---|
| **Code Modification** | Required | Not required |
| **Deployment Impact** | Redeployment required | Separate deployment |
| **Overhead** | Application level | Kernel level (very low) |
| **Language Dependency** | SDK support needed per language | Language agnostic |
| **Coverage** | Only instrumented parts | Entire system |
| **Maintenance** | Managed with code | Independent |

### 5.2 Coroot: Automatic Service Maps and Latency Analysis

Coroot uses eBPF to automatically generate service maps and analyze latency.

```yaml
# coroot-helm-values.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: coroot
---
# Install Coroot via Helm
# helm repo add coroot https://coroot.github.io/helm-charts
# helm install coroot coroot/coroot -n coroot -f coroot-helm-values.yaml

coroot:
  replicas: 1
  resources:
    requests:
      cpu: 200m
      memory: 1Gi
    limits:
      cpu: 1
      memory: 2Gi

  # Prometheus integration
  prometheus:
    url: "http://prometheus-server.monitoring:9090"

  # ClickHouse storage (logs/traces)
  clickhouse:
    enabled: true
    persistence:
      size: 100Gi
      storageClass: gp3

node-agent:
  # eBPF-based agent
  ebpf:
    enabled: true

  resources:
    requests:
      cpu: 100m
      memory: 100Mi
    limits:
      cpu: 500m
      memory: 500Mi

  tolerations:
    - operator: Exists
```

**Coroot Key Features:**

- **Automatic Service Discovery**: Detects network connections via eBPF to auto-generate service maps
- **Latency Analysis**: Automatically measures latency between each service
- **Resource Usage Tracking**: Analyzes CPU, memory, disk I/O per service
- **Log Collection**: Collects application logs without code modifications

### 5.3 Pixie (Now New Relic): Kubernetes-Specific Observability

Pixie is an eBPF-based observability platform specialized for Kubernetes environments.

```bash
# Install Pixie CLI
bash -c "$(curl -fsSL https://withpixie.ai/install.sh)"

# Deploy Pixie
px deploy

# Check cluster status
px get viziers

# Real-time HTTP traffic monitoring
px live http_data

# Per-service latency analysis
px live service_stats
```

**Pixie Key Features:**

- **Ready-to-use Dashboards**: Automatic monitoring of HTTP, DNS, MySQL, PostgreSQL, etc. immediately after deployment
- **PxL Scripts**: Custom analysis with Python-like query language
- **Local Data Storage**: Sensitive data never leaves the cluster
- **Automatic Encryption Analysis**: Decrypts TLS traffic via eBPF for analysis

### 5.4 Cilium Hubble: Network Flow Observation

For EKS clusters using Cilium CNI, Hubble provides network visibility.

```yaml
# cilium-hubble-values.yaml
hubble:
  enabled: true

  relay:
    enabled: true
    resources:
      requests:
        cpu: 100m
        memory: 128Mi

  ui:
    enabled: true
    replicas: 1
    ingress:
      enabled: true
      annotations:
        kubernetes.io/ingress.class: nginx
      hosts:
        - hubble.example.com

  metrics:
    enabled:
      - dns
      - drop
      - tcp
      - flow
      - icmp
      - http
    serviceMonitor:
      enabled: true
```

```bash
# Real-time flow observation with Hubble CLI
hubble observe --namespace production

# Filter traffic to specific service
hubble observe --to-service production/api-server

# Monitor DNS requests
hubble observe --protocol dns

# Analyze dropped packets
hubble observe --verdict DROPPED
```

### 5.5 Kepler: Energy Consumption Monitoring

Kepler (Kubernetes Efficient Power Level Exporter) uses eBPF to measure workload energy consumption.

```yaml
# kepler-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kepler
  namespace: kepler
spec:
  selector:
    matchLabels:
      app: kepler
  template:
    metadata:
      labels:
        app: kepler
    spec:
      serviceAccountName: kepler
      containers:
        - name: kepler
          image: quay.io/sustainable_computing_io/kepler:release-0.7
          securityContext:
            privileged: true
          ports:
            - containerPort: 9102
              name: metrics
          volumeMounts:
            - name: lib-modules
              mountPath: /lib/modules
            - name: tracing
              mountPath: /sys/kernel/tracing
            - name: kernel-src
              mountPath: /usr/src/kernels
          env:
            - name: NODE_NAME
              valueFrom:
                fieldRef:
                  fieldPath: spec.nodeName
      volumes:
        - name: lib-modules
          hostPath:
            path: /lib/modules
        - name: tracing
          hostPath:
            path: /sys/kernel/tracing
        - name: kernel-src
          hostPath:
            path: /usr/src/kernels
```

**Kepler Metrics Examples:**

```promql
# Energy consumption by namespace (joules)
sum by (namespace) (kepler_container_joules_total)

# Power consumption by Pod (watts)
rate(kepler_container_joules_total[5m]) * 1000

# Top 10 Pods consuming the most energy
topk(10, sum by (pod_name) (rate(kepler_container_joules_total[5m])))
```

---

## 6. Cost Monitoring

### 6.1 KubeCost / OpenCost Installation and Configuration

OpenCost is a CNCF project and the open-source standard for Kubernetes cost monitoring.

```bash
# Install OpenCost
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.prometheus.internal.enabled=false \
  --set opencost.prometheus.external.enabled=true \
  --set opencost.prometheus.external.url="http://prometheus-server.monitoring:9090" \
  --set opencost.ui.enabled=true
```

```yaml
# opencost-values.yaml - Detailed configuration
opencost:
  exporter:
    defaultClusterId: "eks-production"

    # AWS cost integration
    aws:
      spotDataRegion: ap-northeast-2
      spotDataBucket: "my-spot-data-bucket"
      athenaProjectID: "my-aws-project"
      athenaRegion: ap-northeast-2
      athenaDatabase: "athenacurcfn_my_cur"
      athenaTable: "my_cur"
      masterPayerARN: "arn:aws:iam::ACCOUNT:role/OpenCostRole"

  prometheus:
    external:
      enabled: true
      url: "http://prometheus-server.monitoring:9090"

  ui:
    enabled: true
    ingress:
      enabled: true
      annotations:
        kubernetes.io/ingress.class: nginx
      hosts:
        - host: opencost.example.com
          paths:
            - path: /
              pathType: Prefix
```

### 6.2 Cost Allocation by Namespace/Team

```yaml
# cost-allocation-labels.yaml
# Label standardization for team cost tracking
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
  labels:
    cost-center: "engineering"
    team: "alpha"
    environment: "production"
---
# Apply cost labels to Pods
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: team-alpha
spec:
  template:
    metadata:
      labels:
        cost-center: "engineering"
        team: "alpha"
        component: "api"
    spec:
      containers:
        - name: api
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
```

**Cost Query via OpenCost API:**

```bash
# Cost by namespace (last 7 days)
curl -s "http://opencost.opencost:9003/allocation/compute?window=7d&aggregate=namespace" | jq '.'

# Cost by team label
curl -s "http://opencost.opencost:9003/allocation/compute?window=7d&aggregate=label:team" | jq '.'

# Daily cost trend
curl -s "http://opencost.opencost:9003/allocation/compute?window=30d&step=1d&aggregate=namespace" | jq '.'
```

### 6.3 CloudWatch Cost Optimization

```yaml
# cloudwatch-log-retention.yaml
# Cost reduction through log retention period optimization
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-cloudwatch-config
  namespace: logging
data:
  fluent-bit.conf: |
    [OUTPUT]
        Name                cloudwatch_logs
        Match               *
        region              ap-northeast-2
        log_group_name      /eks/production/application
        log_stream_prefix   ${HOSTNAME}-
        auto_create_group   true
        # Set log retention period (cost optimization)
        log_retention_days  14

        # Batch settings for API call optimization
        log_format          json
        max_batch_size      1048576
        max_batch_put_limit 100
```

```bash
# Batch set CloudWatch Logs retention period
aws logs describe-log-groups --query 'logGroups[*].logGroupName' --output text | \
while read log_group; do
  aws logs put-retention-policy \
    --log-group-name "$log_group" \
    --retention-in-days 14
done

# Clean up unused log groups
aws logs describe-log-groups --query 'logGroups[?storedBytes==`0`].logGroupName' --output text | \
while read log_group; do
  echo "Deleting empty log group: $log_group"
  aws logs delete-log-group --log-group-name "$log_group"
done
```

### 6.4 Log/Metrics Storage Cost Reduction Strategies

![Collected data is classified by priority — high-priority data gets full storage and long-term retention in Glacier, medium-priority data is sampled into Standard-IA, and low-priority data is aggregated only and kept in fast local memory.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-5.svg)

| Strategy | Target | Expected Savings |
|---|---|---|
| **Log Level Filtering** | Drop DEBUG/TRACE logs | 40-60% |
| **Sampling** | High-frequency events | 30-50% |
| **Compression** | All logs/metrics | 60-80% |
| **Tiered Storage** | Old data | 70-90% |
| **Retention Period Optimization** | Low-priority data | 50-70% |

---

## 7. Unified Observability Dashboard

### 7.1 Grafana-Based Unified Dashboard Configuration

```yaml
# grafana-datasources.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      # Prometheus - Metrics
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus-server:9090
        isDefault: true
        jsonData:
          httpMethod: POST
          exemplarTraceIdDestinations:
            - name: traceID
              datasourceUid: tempo

      # Loki - Logs
      - name: Loki
        type: loki
        access: proxy
        url: http://loki-gateway:80
        jsonData:
          derivedFields:
            - name: TraceID
              matcherRegex: '"traceId":"([a-f0-9]+)"'
              url: '$${__value.raw}'
              datasourceUid: tempo

      # Tempo - Traces
      - name: Tempo
        type: tempo
        access: proxy
        url: http://tempo-query-frontend:3100
        uid: tempo
        jsonData:
          httpMethod: GET
          tracesToLogs:
            datasourceUid: loki
            tags: ['service.name', 'pod']
          serviceMap:
            datasourceUid: prometheus
          nodeGraph:
            enabled: true
          lokiSearch:
            datasourceUid: loki
```

### 7.2 Log -> Metrics -> Trace Correlation (Exemplars)

Exemplars is a feature that links trace IDs to metric data points.

```yaml
# prometheus-exemplars-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      # Enable Exemplars
      enable_features:
        - exemplar-storage

    scrape_configs:
      - job_name: 'application'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            regex: 'true'
            action: keep
```

Exporting Exemplars from applications (Go example):

```go
// Adding Exemplars to Prometheus histograms
import (
    "github.com/prometheus/client_golang/prometheus"
    "go.opentelemetry.io/otel/trace"
)

var httpDuration = prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request duration",
        Buckets: prometheus.DefBuckets,
    },
    []string{"method", "path", "status"},
)

func recordMetric(ctx context.Context, method, path, status string, duration float64) {
    span := trace.SpanFromContext(ctx)
    traceID := span.SpanContext().TraceID().String()

    httpDuration.WithLabelValues(method, path, status).(prometheus.ExemplarObserver).
        ObserveWithExemplar(duration, prometheus.Labels{"traceID": traceID})
}
```

### 7.3 Alerting Strategy: Preventing Alert Fatigue

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m

    # Routing rules
    route:
      receiver: 'default'
      group_by: ['alertname', 'namespace', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

      routes:
        # Routing by severity
        - match:
            severity: critical
          receiver: 'critical-alerts'
          group_wait: 10s
          repeat_interval: 1h

        - match:
            severity: warning
          receiver: 'warning-alerts'
          group_wait: 1m
          repeat_interval: 4h

        # Suppress alerts outside business hours
        - match:
            severity: info
          receiver: 'info-alerts'
          mute_time_intervals:
            - off-hours

    # Alert inhibition rules
    inhibit_rules:
      # Suppress individual service alerts when cluster is down
      - source_match:
          alertname: ClusterDown
        target_match_re:
          alertname: '.+'
        equal: ['cluster']

      # Suppress Pod alerts when node is down
      - source_match:
          alertname: NodeDown
        target_match_re:
          alertname: 'Pod.*'
        equal: ['node']

    # Define off-hours
    time_intervals:
      - name: off-hours
        time_intervals:
          - weekdays: ['saturday', 'sunday']
          - times:
              - start_time: '00:00'
                end_time: '09:00'
              - start_time: '18:00'
                end_time: '24:00'

    receivers:
      - name: 'default'
        slack_configs:
          - channel: '#alerts-default'

      - name: 'critical-alerts'
        slack_configs:
          - channel: '#alerts-critical'
        pagerduty_configs:
          - service_key: '<pagerduty-key>'

      - name: 'warning-alerts'
        slack_configs:
          - channel: '#alerts-warning'

      - name: 'info-alerts'
        slack_configs:
          - channel: '#alerts-info'
```

### 7.4 SLO/SLI-Based Monitoring

```yaml
# slo-recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: slo-rules
  namespace: monitoring
spec:
  groups:
    - name: slo.rules
      rules:
        # Availability SLI: Successful request ratio
        - record: sli:availability:ratio
          expr: |
            sum(rate(http_requests_total{status!~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))

        # Latency SLI: P99 < 500ms ratio
        - record: sli:latency:ratio
          expr: |
            sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
            /
            sum(rate(http_request_duration_seconds_count[5m]))

        # Error budget burn rate (30-day basis)
        - record: slo:error_budget:remaining
          expr: |
            1 - (
              (1 - sli:availability:ratio)
              /
              (1 - 0.999)  # 99.9% SLO target
            )

    - name: slo.alerts
      rules:
        # Warning when 50% of error budget consumed
        - alert: ErrorBudgetBurnRateHigh
          expr: slo:error_budget:remaining < 0.5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "More than 50% of error budget consumed"
            description: "Remaining error budget: {{ $value | humanizePercentage }}"

        # Critical when 80% of error budget consumed
        - alert: ErrorBudgetBurnRateCritical
          expr: slo:error_budget:remaining < 0.2
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "More than 80% of error budget consumed"
            description: "Remaining error budget: {{ $value | humanizePercentage }}"
```

---

## 8. Operational Challenges and Solutions

### 8.1 Responding to Exploding Log/Metrics Storage Costs

| Problem | Cause | Solution |
|---|---|---|
| Log cost spike | Excessive DEBUG logs | Log level filtering, sampling |
| Metric cardinality explosion | Pod UID, timestamp labels | Label cleanup, metric dropping |
| Trace storage cost | 100% sampling | Apply Tail Sampling |
| Long-term retention cost | Same retention for all data | Tiered Storage |

```yaml
# cost-optimization-config.yaml
# Fluent Bit log filtering
[FILTER]
    Name     grep
    Match    *
    Exclude  log ^.*DEBUG.*$
    Exclude  log ^.*TRACE.*$

# High-frequency log sampling (10%)
[FILTER]
    Name          throttle
    Match         kube.var.log.containers.nginx*
    Rate          10
    Window        60
    Print_Status  true
```

### 8.2 EKS Auto Mode Node Monitoring

In EKS Auto Mode, nodes are automatically managed, requiring special monitoring strategies.

```yaml
# auto-mode-monitoring.yaml
# Managed Node Pool monitoring
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: auto-mode-nodes
  namespace: monitoring
spec:
  selector:
    matchLabels:
      eks.amazonaws.com/managed: "true"
  namespaceSelector:
    any: true
  podMetricsEndpoints:
    - port: metrics
      interval: 30s
---
# Enable CloudWatch Container Insights
# Recommended for use with EKS Auto Mode
apiVersion: v1
kind: ConfigMap
metadata:
  name: cwagent-config
  namespace: amazon-cloudwatch
data:
  cwagentconfig.json: |
    {
      "logs": {
        "metrics_collected": {
          "kubernetes": {
            "cluster_name": "eks-auto-cluster",
            "metrics_collection_interval": 60
          }
        }
      }
    }
```

### 8.3 Cross-Tool Data Correlation Analysis

![A user's slow-API investigation flows entirely through Grafana, which queries Prometheus for a P99 exemplar, follows the trace ID into Tempo to find the bottleneck service, then filters Loki logs by that same trace ID before returning one unified answer.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-6.svg)

### 8.4 Maintaining Monitoring System Performance at Large Scale

```yaml
# high-scale-prometheus.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 2
  retention: 7d
  retentionSize: 100GB

  # Sharding for load distribution
  shards: 3

  resources:
    requests:
      cpu: 2
      memory: 8Gi
    limits:
      cpu: 4
      memory: 16Gi

  # Offload to external storage
  remoteWrite:
    - url: "http://victoriametrics:8428/api/v1/write"
      queueConfig:
        capacity: 10000
        maxShards: 30
        maxSamplesPerSend: 5000

  # Query performance optimization
  queryLogFile: /prometheus/query.log

  additionalArgs:
    # Query concurrency limit
    - name: query.max-concurrency
      value: "20"
    # Query timeout
    - name: query.timeout
      value: "2m"
```

### 8.5 High Availability Observability Stack Configuration

![Multiple Fluent Bit agents fan into a load balancer that spreads work across a redundant pair of OTel Collectors, which write logs to an HA Loki-write pair backed by shared S3 and metrics to an HA vminsert pair backed by replicated vmstorage.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-7.svg)

---

## 9. Best Practices and Next Steps

### 9.1 Phased Adoption Strategy

![A three-phase adoption path: Phase 1 uses CloudWatch-only basics, Phase 2 layers on the Prometheus/Grafana and Loki/X-Ray stack, and Phase 3 arrives at OpenTelemetry, eBPF monitoring, and cost monitoring as the advanced end state.](../../assets/diagrams/rendered/en-observability-09-observability-optimization-8.svg)

| Phase | Components | Duration | Cost | Operational Complexity |
|---|---|---|---|---|
| **Phase 1 (Basic)** | CloudWatch-based | 1-2 days | Low | Low |
| **Phase 2 (Intermediate)** | Grafana stack | 1-2 weeks | Medium | Medium |
| **Phase 3 (Advanced)** | OpenTelemetry + eBPF | 2-4 weeks | High | High |

### 9.2 Cost-Benefit Analysis

| Tool Combination | Est. Monthly Cost (100 nodes) | Feature Coverage | ROI |
|---|---|---|---|
| CloudWatch full | $500-1,000 | Basic | Low |
| Prometheus + Loki + Grafana | $200-400 (infrastructure) | Intermediate | Medium |
| AMP + Tempo + eBPF | $300-600 | Advanced | High |
| Commercial solutions (Datadog, etc.) | $2,000-5,000 | Complete | Varies |

### 9.3 Checklist

**Observability Implementation Checklist:**

- [ ] Implement all three pillars: logging, metrics, tracing
- [ ] Set up data correlation between pillars
- [ ] Establish cardinality management policies
- [ ] Define and apply sampling strategies
- [ ] Deploy cost monitoring tools
- [ ] Optimize alerting rules (prevent alert fatigue)
- [ ] Define SLO/SLI and configure dashboards
- [ ] Establish long-term storage strategy
- [ ] Complete high availability configuration
- [ ] Documentation and team training

### 9.4 Related Documents and Quizzes

**Related Documents:**

- [Prometheus Operations Guide](./metrics/01-prometheus.md)
- [Grafana Dashboard Configuration](./grafana/README.md)

**Related Quiz:**

- [Observability Optimization Quiz](../quizzes/observability/09-observability-optimization-quiz.md)

---

## References

- [OpenTelemetry Official Documentation](https://opentelemetry.io/docs/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [OpenCost Project](https://www.opencost.io/)
- [eBPF.io](https://ebpf.io/)
