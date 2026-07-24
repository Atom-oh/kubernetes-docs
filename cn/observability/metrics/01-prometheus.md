# Prometheus

> **支持的版本**: Prometheus 2.x / 3.x
> **最后更新**: July 21, 2026

## 目录

- [简介](#introduction)
- [架构](#architecture)
- [核心组件](#core-components)
- [PromQL 查询语言](#promql-query-language)
- [服务发现](#service-discovery)
- [Prometheus Operator](#prometheus-operator)
- [kube-prometheus-stack 安装](#kube-prometheus-stack-installation)
- [Alertmanager 集成](#alertmanager-integration)
- [Remote Write 和 AMP 集成](#remote-write-and-amp-integration)
- [性能调优](#performance-tuning)
- [最佳实践](#best-practices)
- [故障排除](#troubleshooting)

## 简介

Prometheus 是一个开源系统监控和告警工具包，最初由 SoundCloud 开发并捐赠给 CNCF (Cloud Native Computing Foundation)。它已成为 Kubernetes 环境中的事实标准监控解决方案。

### 主要功能

1. **多维数据模型**：通过指标名称和键值对（标签）标识时间序列
2. **PromQL**：利用多维数据的灵活查询语言
3. **基于拉取的采集**：通过 HTTP 定期从目标抓取指标
4. **服务发现**：在 Kubernetes 等动态环境中自动发现监控目标
5. **告警管理**：通过 Alertmanager 进行基于规则的告警定义和路由
6. **独立服务器**：作为单一服务器运行，无需依赖分布式存储

### 适合使用 Prometheus 的场景

- 记录纯数值时间序列
- 以机器为中心的监控和高度动态的面向服务架构
- 多维数据采集和查询
- 系统概览比 100% 准确性更重要的场景

### 不适合使用 Prometheus 的场景

- 事件日志或追踪
- 需要 100% 准确性的场景，例如按请求计费
- 长期数据保留（需要单独的长期存储）

## 架构

```mermaid
flowchart TD
    subgraph PROM["Prometheus Server"]
        R[Retrieval<br/>Metric Collection]
        T[TSDB<br/>Time Series DB]
        H[HTTP Server<br/>Query API]
        A[Alert Rules]
    end

    subgraph TARGETS["Scrape Targets"]
        J1[Jobs/Exporters]
        J2[Short-lived Jobs]
        PG[Pushgateway]
    end

    subgraph SD["Service Discovery"]
        K8S[Kubernetes]
        DNS[DNS]
        FILE[File SD]
        CONSUL[Consul]
    end

    subgraph ALERT["Alert Processing"]
        AM[Alertmanager]
        EM[Email]
        SL[Slack]
        PD[PagerDuty]
    end

    subgraph VIS["Visualization/API"]
        GF[Grafana]
        API[API Clients]
        UI[Prometheus UI]
    end

    SD --> R
    R -->|scrape| J1
    J2 -->|push| PG
    R -->|scrape| PG
    R --> T
    T --> H
    T --> A
    A -->|alerts| AM
    AM --> EM
    AM --> SL
    AM --> PD
    H --> GF
    H --> API
    H --> UI

    classDef prometheus fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef targets fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef sd fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef alert fill:#EB6E85,stroke:#333,stroke-width:1px,color:white
    classDef vis fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class R,T,H,A prometheus
    class J1,J2,PG targets
    class K8S,DNS,FILE,CONSUL sd
    class AM,EM,SL,PD alert
    class GF,API,UI vis
```

### 数据流

1. **服务发现**：从 Kubernetes API、DNS、文件等发现抓取目标
2. **指标采集**：通过 HTTP 从目标的 `/metrics` 端点抓取指标
3. **数据存储**：将采集的指标存储在本地 TSDB 中
4. **规则评估**：根据存储的数据评估告警和记录规则
5. **告警分发**：将触发的告警发送到 Alertmanager
6. **查询服务**：通过 HTTP API 处理 PromQL 查询

## 核心组件

### TSDB（时间序列数据库）

Prometheus 的内置时间序列数据库专为高效存储时间序列数据而设计。

```yaml
# TSDB-related configuration
storage:
  tsdb:
    path: /prometheus               # Data storage path
    retention.time: 15d             # Data retention period
    retention.size: 50GB            # Maximum storage size
    wal-compression: true           # Enable WAL compression
    min-block-duration: 2h          # Minimum block size
    max-block-duration: 36h         # Maximum block size (10% of retention recommended)
```

**TSDB 块结构**：
```
data/
├── 01BKGV7JBM69T2G1BGBGM6KB12/   # 2-hour block
│   ├── chunks/                    # Time series data
│   │   └── 000001
│   ├── tombstones                 # Deleted data
│   ├── index                      # Label index
│   └── meta.json                  # Block metadata
├── 01BKGV7JC0RY8A6MACW02A2PJD/   # Another block
├── chunks_head/                   # Currently writing data
│   └── 000001
├── wal/                          # Write-Ahead Log
│   ├── 00000000
│   └── 00000001
└── lock                          # Process lock
```

### kube-state-metrics

一个生成 Kubernetes API 对象相关指标的服务。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-state-metrics
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kube-state-metrics
  template:
    metadata:
      labels:
        app: kube-state-metrics
    spec:
      serviceAccountName: kube-state-metrics
      containers:
      - name: kube-state-metrics
        image: registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.10.1
        ports:
        - name: http-metrics
          containerPort: 8080
        - name: telemetry
          containerPort: 8081
        resources:
          requests:
            cpu: 10m
            memory: 128Mi
          limits:
            cpu: 100m
            memory: 256Mi
```

**关键指标**：
```promql
# Pod status metrics
kube_pod_status_phase{phase="Running"}
kube_pod_container_status_restarts_total
kube_pod_container_resource_requests{resource="cpu"}
kube_pod_container_resource_limits{resource="memory"}

# Deployment metrics
kube_deployment_spec_replicas
kube_deployment_status_replicas_available
kube_deployment_status_replicas_unavailable

# Node metrics
kube_node_status_condition{condition="Ready"}
kube_node_status_allocatable{resource="cpu"}
```

### node-exporter

一个公开主机级硬件和操作系统指标的 exporter。

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        args:
          - --path.procfs=/host/proc
          - --path.sysfs=/host/sys
          - --path.rootfs=/host/root
          - --collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+)($|/)
          - --collector.netclass.ignored-devices=^(veth.*|docker.*|br-.*)$
        ports:
        - name: metrics
          containerPort: 9100
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
          mountPropagation: HostToContainer
        resources:
          requests:
            cpu: 10m
            memory: 32Mi
          limits:
            cpu: 100m
            memory: 64Mi
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
      tolerations:
      - operator: Exists
```

**关键指标**：
```promql
# CPU metrics
node_cpu_seconds_total{mode="idle"}
rate(node_cpu_seconds_total{mode!="idle"}[5m])

# Memory metrics
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes
node_memory_Buffers_bytes
node_memory_Cached_bytes

# Disk metrics
node_filesystem_size_bytes
node_filesystem_avail_bytes
node_disk_io_time_seconds_total

# Network metrics
node_network_receive_bytes_total
node_network_transmit_bytes_total
```

### 2026 年 7 月更新：编写自定义指标 Exporter

2026 年 7 月 14 日，Kubernetes 博客发布了 [为 Kubernetes 构建自定义指标 Exporter](https://kubernetes.io/blog/2026/07/14/custom-metrics-exporter-kubernetes/)，其中介绍了当 kube-state-metrics 或 node-exporter 未涵盖所需信号（队列深度、批处理时长、活动连接数等）时，如何从头编写 exporter。要点包括：exporter 只是一个在 `/metrics` 上公开纯文本指标的 HTTP 服务器；根据信号形态选择指标类型（总量使用 counter、升降值使用 gauge、延迟分布使用 histogram）；以及以 `snake_case` 格式将指标命名为 `<namespace>_<name>_<unit>`。该文章还介绍了如何将 exporter 打包为容器并进行连接，以便 Prometheus，以及最终的 HorizontalPodAutoscaler，都能使用它。

## PromQL 查询语言

PromQL（Prometheus 查询语言）是 Prometheus 的函数式查询语言。

### 基本查询

```promql
# Instant vector: value at current time
http_requests_total

# Label filtering
http_requests_total{method="GET"}
http_requests_total{status=~"2.."}           # Regex match
http_requests_total{status!~"5.."}           # Negative regex

# Range vector: values over time range
http_requests_total[5m]                       # All samples in last 5 minutes
http_requests_total[1h:5m]                    # Samples at 5 minute intervals over 1 hour

# Offset modifier
http_requests_total offset 1h                 # Value from 1 hour ago
rate(http_requests_total[5m] offset 1h)       # 5 minute rate from 1 hour ago
```

### 聚合运算符

```promql
# sum: Total
sum(http_requests_total)
sum by (method)(http_requests_total)          # Sum by method
sum without (instance)(http_requests_total)   # Sum excluding instance

# avg: Average
avg(node_cpu_seconds_total)

# count: Count
count(kube_pod_status_phase{phase="Running"})

# min/max: Minimum/Maximum
max(node_memory_MemAvailable_bytes)

# topk/bottomk: Top/bottom k
topk(5, sum by (pod)(rate(container_cpu_usage_seconds_total[5m])))

# quantile: Quantile
quantile(0.95, http_request_duration_seconds)

# stddev/stdvar: Standard deviation/variance
stddev(rate(http_requests_total[5m]))
```

### Rate 和 Increase 函数

```promql
# rate: Average per-second rate of increase (for Counters)
rate(http_requests_total[5m])

# irate: Instant rate between last two samples
irate(http_requests_total[5m])

# increase: Total increase over time range
increase(http_requests_total[1h])

# delta: Difference between first and last values (for Gauges)
delta(temperature_celsius[1h])

# deriv: Per-second rate of change (for Gauges, linear regression)
deriv(temperature_celsius[1h])
```

### 预测函数

```promql
# predict_linear: Linear regression based future value prediction
predict_linear(node_filesystem_avail_bytes[6h], 24*60*60)  # Predict 24 hours ahead

# Disk space exhaustion prediction alert
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 24*60*60) < 0
```

### 实用查询示例

```promql
# CPU usage (%)
100 - (avg by (instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage (%)
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# Pod restart count increase
increase(kube_pod_container_status_restarts_total[1h]) > 3

# HTTP error rate (%)
100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
/ sum(rate(http_requests_total[5m]))

# p95 latency
histogram_quantile(0.95,
  sum by (le)(rate(http_request_duration_seconds_bucket[5m]))
)

# Disk usage
100 - (node_filesystem_avail_bytes{mountpoint="/"}
/ node_filesystem_size_bytes{mountpoint="/"} * 100)
```

## 服务发现

### Kubernetes 服务发现

Prometheus 通过 Kubernetes API 自动发现监控目标。

```yaml
scrape_configs:
  # Pod auto-discovery
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Only scrape pods with prometheus.io/scrape annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      # Custom metrics path
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      # Custom port
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      # Add labels
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

### 基于 Pod Annotation 的抓取

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    prometheus.io/scrape: "true"       # Enable scraping
    prometheus.io/port: "8080"         # Metrics port
    prometheus.io/path: "/metrics"     # Metrics path
    prometheus.io/scheme: "http"       # http or https
spec:
  containers:
  - name: app
    image: my-app:latest
    ports:
    - containerPort: 8080
```

## Prometheus Operator

Prometheus Operator 是一个用于在 Kubernetes 中以声明方式管理 Prometheus 的 controller。

### 自定义资源定义（CRD）

```mermaid
flowchart TD
    PO[Prometheus Operator] --> P[Prometheus]
    PO --> AM[Alertmanager]
    PO --> TM[ThanosRuler]

    P --> SM[ServiceMonitor]
    P --> PM[PodMonitor]
    P --> PR[PrometheusRule]
    P --> SC[ScrapeConfig]
    P --> PB[Probe]

    AM --> AMC[AlertmanagerConfig]

    classDef operator fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef resource fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef config fill:#00C7B7,stroke:#333,stroke-width:1px,color:white

    class PO operator
    class P,AM,TM resource
    class SM,PM,PR,SC,PB,AMC config
```

### ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: example-app
  namespace: monitoring
  labels:
    team: frontend
spec:
  # Target service selection
  selector:
    matchLabels:
      app: example-app

  # Target namespaces
  namespaceSelector:
    matchNames:
    - production
    - staging

  # Endpoint configuration
  endpoints:
  - port: web
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
    scheme: http

    # Label rewriting
    relabelings:
    - sourceLabels: [__meta_kubernetes_pod_name]
      targetLabel: pod
    - sourceLabels: [__meta_kubernetes_namespace]
      targetLabel: namespace

    # Metric filtering
    metricRelabelings:
    - sourceLabels: [__name__]
      regex: 'go_.*'
      action: drop
```

### PrometheusRule

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
  labels:
    role: alert-rules
spec:
  groups:
  - name: kubernetes-system
    interval: 30s
    rules:
    # Node memory high alert
    - alert: NodeMemoryHigh
      expr: |
        (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
        / node_memory_MemTotal_bytes * 100 > 90
      for: 5m
      labels:
        severity: warning
        team: infrastructure
      annotations:
        summary: "Node {{ $labels.instance }} memory usage is high"
        description: "Memory usage is {{ printf \"%.2f\" $value }}%"
        runbook_url: "https://wiki.example.com/runbooks/node-memory-high"

    # Pod restart alert
    - alert: PodRestartingFrequently
      expr: increase(kube_pod_container_status_restarts_total[1h]) > 5
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is restarting frequently"
        description: "Pod has restarted {{ $value }} times in the last hour"
```

## kube-prometheus-stack 安装

kube-prometheus-stack 是一个综合性 Helm chart，其中包含 Prometheus、Alertmanager、Grafana 和相关组件。

### 使用 Helm 安装

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Basic installation
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Installation with custom values
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f values.yaml
```

### values.yaml 示例

```yaml
# Prometheus configuration
prometheus:
  prometheusSpec:
    # Replicas
    replicas: 2

    # Retention period
    retention: 15d
    retentionSize: 50GB

    # Storage
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 100Gi

    # Resources
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 8Gi

    # Remote Write
    remoteWrite:
    - url: http://victoriametrics:8428/api/v1/write
      queueConfig:
        maxSamplesPerSend: 10000
        batchSendDeadline: 5s

    # External labels
    externalLabels:
      cluster: production

    # Collect ServiceMonitors from all namespaces
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    ruleSelectorNilUsesHelmValues: false

# Alertmanager configuration
alertmanager:
  alertmanagerSpec:
    replicas: 3
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi

# Grafana configuration
grafana:
  enabled: true
  replicas: 1

  persistence:
    enabled: true
    storageClassName: gp3
    size: 10Gi

  # Additional data sources
  additionalDataSources:
  - name: VictoriaMetrics
    type: prometheus
    url: http://victoriametrics:8428
    access: proxy
    isDefault: false
```

## Alertmanager 集成

### AlertmanagerConfig

```yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: main-config
  namespace: monitoring
  labels:
    alertmanagerConfig: main
spec:
  # Routing configuration
  route:
    receiver: 'default'
    groupBy: ['alertname', 'namespace', 'severity']
    groupWait: 30s
    groupInterval: 5m
    repeatInterval: 4h

    routes:
    # Critical alerts -> PagerDuty
    - receiver: 'pagerduty-critical'
      matchers:
      - name: severity
        matchType: =
        value: critical
      groupWait: 10s
      repeatInterval: 1h

    # Warning alerts -> Slack
    - receiver: 'slack-warnings'
      matchers:
      - name: severity
        matchType: =
        value: warning
      groupWait: 1m
      repeatInterval: 4h

  # Receivers
  receivers:
  - name: 'default'
    emailConfigs:
    - to: 'alerts@example.com'
      from: 'alertmanager@example.com'
      smarthost: 'smtp.example.com:587'
      authUsername: 'alertmanager'
      authPassword:
        name: alertmanager-smtp
        key: password
      requireTLS: true

  - name: 'slack-warnings'
    slackConfigs:
    - apiURL:
        name: alertmanager-slack
        key: webhook-url
      channel: '#alerts'
      sendResolved: true

  - name: 'pagerduty-critical'
    pagerdutyConfigs:
    - routingKey:
        name: alertmanager-pagerduty
        key: routing-key
      sendResolved: true
```

## Remote Write 和 AMP 集成

### Amazon Managed Prometheus（AMP）集成

```yaml
# Prometheus configuration
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
  namespace: monitoring
spec:
  # IRSA service account
  serviceAccountName: prometheus-amp

  # Remote Write to AMP
  remoteWrite:
  - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/ws-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/api/v1/remote_write
    sigv4:
      region: ap-northeast-2
    queueConfig:
      maxSamplesPerSend: 1000
      maxShards: 200
      capacity: 2500
    writeRelabelConfigs:
    # Exclude unnecessary metrics
    - sourceLabels: [__name__]
      regex: 'go_.*'
      action: drop
```

### IRSA 设置

```bash
# Create IAM policy
cat <<EOF > amp-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "aps:RemoteWrite",
                "aps:QueryMetrics",
                "aps:GetSeries",
                "aps:GetLabels",
                "aps:GetMetricMetadata"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
  --policy-name AmazonManagedPrometheusPolicy \
  --policy-document file://amp-policy.json

# Create service account (using eksctl)
eksctl create iamserviceaccount \
  --name prometheus-amp \
  --namespace monitoring \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::123456789012:policy/AmazonManagedPrometheusPolicy \
  --approve
```

## 性能调优

### 内存优化

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  # Memory limits
  resources:
    requests:
      memory: 2Gi
    limits:
      memory: 8Gi

  # Query limits
  query:
    maxConcurrency: 20          # Max concurrent queries
    maxSamples: 50000000        # Max samples per query
    timeout: 2m                 # Query timeout

  # WAL compression
  walCompression: true
```

### 抓取优化

```yaml
scrape_configs:
- job_name: 'high-cardinality-app'
  scrape_interval: 60s           # Increase interval
  scrape_timeout: 30s
  sample_limit: 10000            # Limit sample count

  metric_relabel_configs:
  # Remove unnecessary metrics
  - source_labels: [__name__]
    regex: 'go_.*|process_.*'
    action: drop

  # Remove high cardinality labels
  - regex: 'pod_template_hash|controller_revision_hash'
    action: labeldrop
```

## 最佳实践

### 高可用配置

```yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  # Run 2 replicas
  replicas: 2

  # Pod anti-affinity
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app.kubernetes.io/name: prometheus
        topologyKey: kubernetes.io/hostname

  # Sharding (for large environments)
  shards: 2

  # External labels (for deduplication)
  externalLabels:
    cluster: production
    replica: $(POD_NAME)
```

### 告警规则指南

```yaml
# Good alert rule example
- alert: HighErrorRate
  # Meaningful threshold
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
    / sum(rate(http_requests_total[5m])) by (service) > 0.01
  # Appropriate wait time (noise prevention)
  for: 5m
  labels:
    # Severity level
    severity: warning
    # Owning team
    team: backend
  annotations:
    # Clear summary
    summary: "High error rate on {{ $labels.service }}"
    # Detailed description
    description: |
      Service {{ $labels.service }} has error rate of {{ printf "%.2f" $value }}%.
      This is above the 1% threshold.
    # Runbook link
    runbook_url: "https://wiki.example.com/runbooks/high-error-rate"
```

## 故障排除

### 常见问题

#### 1. 内存不足（OOMKilled）

```bash
# Check current memory usage
kubectl top pod -n monitoring prometheus-prometheus-0

# Check TSDB status
curl -s http://prometheus:9090/api/v1/status/tsdb | jq .

# Solution: Increase memory limit or reduce retention period
```

#### 2. 高基数

```promql
# Find high cardinality metrics
topk(10, count by (__name__)({__name__=~".+"}))

# Check label combinations for specific metric
count(http_requests_total)

# Solution: Use metric_relabel_configs to remove unnecessary labels/metrics
```

#### 3. 抓取失败

```bash
# Check target status
curl -s http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Directly check target metrics
kubectl exec -it prometheus-prometheus-0 -n monitoring -- \
  wget -qO- http://target-service:8080/metrics | head -20

# Solution: Check network policies, RBAC, service endpoints
```

### 调试命令

```bash
# Check Prometheus logs
kubectl logs -f prometheus-prometheus-0 -n monitoring

# Prometheus API status
curl http://prometheus:9090/api/v1/status/config
curl http://prometheus:9090/api/v1/status/flags
curl http://prometheus:9090/api/v1/status/runtimeinfo

# TSDB status
curl http://prometheus:9090/api/v1/status/tsdb

# Target metadata
curl http://prometheus:9090/api/v1/targets/metadata

# Rule status
curl http://prometheus:9090/api/v1/rules

# Alert status
curl http://prometheus:9090/api/v1/alerts
```

## 参考资料

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Prometheus Operator 文档](https://prometheus-operator.dev/)
- [PromQL 速查表](https://promlabs.com/promql-cheat-sheet/)
- [kube-prometheus-stack Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Prometheus 最佳实践](https://prometheus.io/docs/practices/)

## 测验

若要测试你对本章的理解，请尝试 [Prometheus 测验](../../quizzes/observability/metrics/01-prometheus-quiz.md)。
