# Istio 指标

> **支持版本**：Istio 1.31
> **最后更新**：2026 年 9 月 11 日

> **验证范围**：这些实验配置依据官方参考和离线验证器检查，未部署集群。各示例注明命名空间、身份、存储、后端和负载假设，必须针对目标环境验证。

Istio 代理为观测流量生成指标。本指南涵盖 Sidecar/Envoy HTTP 和 TCP 指标，以及通过 Prometheus 或 OpenTelemetry Collector 抓取。Ambient ztunnel 具有不同 L4 指标；HTTP 指标需要 waypoint。

## 目录

1. [指标概述](#metrics-overview)
2. [Istio 标准指标](#istio-standard-metrics)
3. [断路器指标](#circuit-breaker-metrics)
4. [韧性指标](#resilience-metrics)
5. [OpenTelemetry 集成](#opentelemetry-integration)
6. [Prometheus 集成](#prometheus-integration)
7. [使用 Telemetry API 自定义](#customization-with-telemetry-api)
8. [实用指标查询](#practical-metric-queries)
9. [指标优化](#metrics-optimization)
10. [故障排除](#troubleshooting)

## 指标概述 {#metrics-overview}

### 黄金信号

结合代理遥测和节点/容器导出器测量黄金信号：

1. **延迟**：请求处理时间
2. **流量**：系统吞吐量（RPS、带宽）
3. **错误**：失败率和错误类型
4. **饱和度**：队列/连接压力，加 Kubernetes 导出器提供的 CPU/内存

### 指标采集架构

Envoy 暴露 Prometheus 指标 → Prometheus 直接抓取，或 OpenTelemetry Collector Prometheus 接收器抓取 → 配置的指标后端 → Grafana/Kiali。Istio OpenTelemetry 扩展提供程序配置追踪；不是 OTLP 指标发送器。

## Istio 标准指标 {#istio-standard-metrics}

### HTTP/gRPC 指标

Envoy 为识别出的 HTTP/gRPC 流量生成这些指标。每个报告代理都会输出指标，因此应针对具体问题选择一个报告方。目标报告避免重复观察一个跳点，而从未到达目标的上游失败需要源报告。按命名空间（及适用集群）对服务名分组。

#### istio_requests_total

**类型**：计数器
**描述**：已处理请求总数

```promql
istio_requests_total{
  reporter="destination",  # Peer security policy populated at destination
  source_workload="productpage-v1",
  source_workload_namespace="default",
  source_principal="spiffe://cluster.local/ns/default/sa/bookinfo-productpage",
  source_app="productpage",
  source_version="v1",
  source_canonical_service="productpage",
  source_canonical_revision="v1",
  destination_workload="reviews-v1",
  destination_workload_namespace="default",
  destination_principal="spiffe://cluster.local/ns/default/sa/bookinfo-reviews",
  destination_app="reviews",
  destination_version="v1",
  destination_service="reviews.default.svc.cluster.local",
  destination_service_name="reviews",
  destination_service_namespace="default",
  destination_canonical_service="reviews",
  destination_canonical_revision="v1",
  request_protocol="http",
  response_code="200",
  response_flags="-",
  connection_security_policy="mutual_tls",
  grpc_response_status="",
  destination_cluster="",
  source_cluster=""
}
```

**关键标签**：
- `response_code`：HTTP 状态码（200、404、500 等）
- `response_flags`：Envoy 响应标志
  - `UH`：没有健康上游
  - `UF`：上游连接失败
  - `UR`：上游远程重置；`UT`：上游请求超时
  - `DC`：下游连接终止
  - `LR`：本地重置
  - `URX`：超过上游重试限制（或 TCP 最大连接尝试次数）
- `connection_security_policy`：mTLS 状态（`mutual_tls`、`none`；源报告可为 `unknown`）

#### istio_request_duration_milliseconds

**类型**：直方图
**描述**：请求处理时间（毫秒）

```promql
istio_request_duration_milliseconds_bucket{le="10"}  # 10ms or less
istio_request_duration_milliseconds_bucket{le="50"}  # 50ms or less
istio_request_duration_milliseconds_bucket{le="100"} # 100ms or less
istio_request_duration_milliseconds_bucket{le="500"} # 500ms or less
istio_request_duration_milliseconds_sum            # Total time
istio_request_duration_milliseconds_count          # Total request count
```

#### istio_request_bytes

**类型**：直方图
**描述**：请求正文大小（字节）

```promql
istio_request_bytes_bucket  # Inspect actual le bounds
istio_request_bytes_bucket{le="+Inf"}  # All body sizes
istio_request_bytes_sum
istio_request_bytes_count
```

#### istio_response_bytes

**类型**：直方图
**描述**：响应正文大小（字节）

```promql
istio_response_bytes_bucket
istio_response_bytes_bucket{le="+Inf"}
istio_response_bytes_sum
istio_response_bytes_count
```

### TCP 指标

#### istio_tcp_connections_opened_total

**类型**：计数器
**描述**：已打开 TCP 连接数

```promql
istio_tcp_connections_opened_total{
  reporter="source",
  source_workload="mongodb-v1",
  destination_service="mongodb.default.svc.cluster.local"
}
```

#### istio_tcp_connections_closed_total

**类型**：计数器
**描述**：已关闭 TCP 连接数

#### istio_tcp_sent_bytes_total

**类型**：计数器
**描述**：发送字节数

#### istio_tcp_received_bytes_total

**类型**：计数器
**描述**：接收字节数

## 断路器指标 {#circuit-breaker-metrics}

抓取前通过 `proxyStatsMatcher` 启用所需 Envoy 统计。默认 Istio 引导配置提取 `cluster_name`；自定义引导可能改变标签。断路器 `_open` 指标是 0/1 gauge，不是事件计数器。部分计数器仅在有流量后出现。

### 关键断路器指标

#### 1. 上游连接池溢出

```promql
# Requests rejected due to connection pool overflow
envoy_cluster_upstream_cx_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**含义**：超过 `maxConnections` 限制

#### 2. 断路器打开（Gauge）

```promql
# Gauge: 1 at capacity, 0 below limit
envoy_cluster_circuit_breakers_default_rq_open{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 3. 待处理请求溢出

```promql
# Pending request count exceeded
envoy_cluster_upstream_rq_pending_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

**含义**：待处理/活动请求断路拒绝。检查 `rq_pending_open`、`rq_open` 和生成阈值，区分队列压力与活动请求限制。

#### 4. 重试预算耗尽

```promql
# Retry budget exhausted
envoy_cluster_upstream_rq_retry_overflow{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 5. 通过响应标志检测断路器

```promql
# Requests rejected by circuit breaker (response_flags="UO")
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UO.*",
  destination_service="httpbin.default.svc.cluster.local"
}[5m]))
```

**响应标志详情**：
- `UO`：上游溢出（断路器打开）
- `URX`：超过上游重试限制（或 TCP 最大连接尝试次数）
- `UF`：上游连接失败
- `UH`：没有健康上游

### 断路器监控仪表板查询

```promql
# Fraction of observed samples at capacity over five minutes (%).
100 * avg_over_time(envoy_cluster_circuit_breakers_default_rq_open[5m])

# Active connections and pending requests (per proxy/cluster).
envoy_cluster_upstream_cx_active
envoy_cluster_upstream_rq_pending_active

# Rejected request events over five minutes.
sum by (namespace, pod, cluster_name) (
  increase(envoy_cluster_upstream_rq_pending_overflow[5m])
)
```

没有标准 `circuit_breakers_default_cx_max` 或 `rq_pending_max` gauge。应从生成集群配置读取限制。可选 `remaining_cx`/`remaining_pending` gauge 需要 Envoy `track_remaining`；仅包含指标名不会启用。利用率分母必须来自已知匹配的配置限制。

### 断路器警报规则

```yaml
groups:
- name: istio_circuit_breaker
  rules:
  - alert: CircuitBreakerAtCapacity
    expr: envoy_cluster_circuit_breakers_default_rq_open == 1
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: Request breaker remains at capacity for {{ $labels.cluster_name }}
  - alert: ConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_cx_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Connection limit exceeded for {{ $labels.cluster_name }}
  - alert: PendingRequestsOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: Request circuit-breaking rejection for {{ $labels.cluster_name }}
```

## 韧性指标 {#resilience-metrics}

### 异常检测指标

#### 1. 被剔除主机

```promql
# Number of hosts ejected by outlier detection
envoy_cluster_outlier_detection_ejections_active{
  cluster_name="outbound|80||httpbin.default.svc.cluster.local"
}
```

#### 2. 剔除事件

```promql
# Ejection event rate
rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m])
```

**按剔除类型**：
```promql
# Consecutive 5xx errors
envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx

# Success rate based
envoy_cluster_outlier_detection_ejections_enforced_success_rate

# Failure percentage based
envoy_cluster_outlier_detection_ejections_enforced_failure_percentage
```

检测到的剔除与实际执行剔除不同：执行概率或最大剔除百分比可能阻止剔除，使检测到的异常主机仍提供服务。部分 Envoy 算法不由 Istio DestinationRule 暴露；缺失序列不能证明配置算法健康。

### 重试指标

```promql
# Number of retried requests
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry success rate
rate(envoy_cluster_upstream_rq_retry_success[5m])
/
rate(envoy_cluster_upstream_rq_retry[5m])

# Retry budget exhausted
rate(envoy_cluster_upstream_rq_retry_overflow[5m])
```

### 超时指标

```promql
# Requests that timed out
sum(rate(istio_requests_total{reporter="source",
  response_flags=~".*UT.*"
}[5m])) by (destination_service)

# Timeout rate
sum(rate(istio_requests_total{reporter="source",response_flags=~".*UT.*"}[5m]))
/
sum(rate(istio_requests_total{reporter="source"}[5m]))
* 100
```

## OpenTelemetry 集成 {#opentelemetry-integration}

### 用于 Istio 指标的 Prometheus 接收器

Istio `opentelemetry` 扩展提供程序导出**追踪**。采集标准网格指标时，保留 Prometheus 指标提供程序，让 OpenTelemetry Collector 的 **Prometheus 接收器抓取**暴露端点。Collector 随后可经 OTLP 向支持指标的后端导出；Tempo 是追踪后端，不是指标目的地。

此示例使用 Collector Contrib 0.160.0 和 Prometheus 导出器，提供可观察演示路径。先创建 `observability` 命名空间。使用一个副本，因为相同抓取配置的副本会重复每个目标；生产扩展需要目标分配/分片。ServiceAccount 仅可读取 Pod，满足 Pod 发现任务要求。配置明文代理指标 15090 和 istiod 15014 的网络访问；此示例不抓取应用指标或 Ambient ztunnel。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-metrics
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-metrics-pod-reader
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-metrics-pod-reader
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-metrics-pod-reader
subjects:
- kind: ServiceAccount
  name: otel-metrics
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-metrics-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      prometheus:
        config:
          global:
            scrape_interval: 15s
            evaluation_interval: 15s
          scrape_configs:
          - job_name: envoy-stats
            metrics_path: /stats/prometheus
            kubernetes_sd_configs:
            - role: pod
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_phase
              action: keep
              regex: Running
            - source_labels:
              - __meta_kubernetes_pod_container_name
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istio-proxy;.*-envoy-prom
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
          - job_name: istiod
            metrics_path: /metrics
            kubernetes_sd_configs:
            - role: pod
              namespaces:
                names:
                - istio-system
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_label_app
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: istiod;http-monitoring
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 512
      batch:
        timeout: 10s
        send_batch_size: 1024
    exporters:
      prometheus:
        endpoint: 0.0.0.0:8889
        const_labels:
          environment: production
      debug:
        verbosity: basic
    service:
      pipelines:
        metrics:
          receivers:
          - prometheus
          processors:
          - memory_limiter
          - batch
          exporters:
          - prometheus
          - debug
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-metrics
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-metrics
  template:
    metadata:
      labels:
        app: otel-metrics
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: otel-metrics
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 8889
          name: prometheus
        volumeMounts:
        - name: config
          mountPath: /etc/otel
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
      volumes:
      - name: config
        configMap:
          name: otel-metrics-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-metrics
  namespace: observability
  labels:
    app: otel-metrics
spec:
  selector:
    app: otel-metrics
  ports:
  - name: prometheus
    port: 8889
    targetPort: prometheus
```

已退役 `logging` 导出器由 `debug` 替代。验证后移除诊断导出。不添加 `namespace: istio` 前缀，避免给现有指标名再加一个 `istio_`。复用 Kiali 仪表板前检查 Collector 输出标签/名称。使用 Prometheus Operator 时，选择带标签的 Service：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: otel-metrics
  namespace: observability
spec:
  selector:
    matchLabels:
      app: otel-metrics
  endpoints:
  - port: prometheus
    interval: 15s
    path: /metrics
    honorLabels: true
```

Prometheus 资源必须选择此 ServiceMonitor 及其命名空间。`honorLabels` 保留原始目标 `job`/`instance`；Collector 必须是可信来源。相同序列只使用此 Collector 路径或下方直接代理抓取，不要同时使用。此 ServiceMonitor 不安装 Prometheus。

### 验证采集

```bash
kubectl logs -n observability deployment/otel-metrics
# Keep this running in one terminal.
kubectl port-forward -n observability svc/otel-metrics 8889:8889
```

```bash
# In a second terminal, after generating test mesh traffic:
curl -fsS http://localhost:8889/metrics | rg '^istio_'
```

追踪 OTLP 接收器和导出器在[追踪章节](02-tracing.md)单独配置；代理调试日志不能证明指标交付。

## Prometheus 集成 {#prometheus-integration}

### Prometheus 配置

在已安装、具有 Pod list/watch 权限的 Prometheus 服务器中使用以下配置。仅 ConfigMap 不部署或重新加载 Prometheus。这些 Pod 发现任务保留 Kubernetes 发现地址（含 IPv6），并精确选择 Envoy 指标端口或 istiod 监控端口。它们包含 Sidecar 和网关，因此独立网关任务会重复序列。已移除 Mixer `istio-telemetry` Service 不是抓取目标。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: istio-system
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
    - job_name: envoy-stats
      metrics_path: /stats/prometheus
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_phase
        action: keep
        regex: Running
      - source_labels:
        - __meta_kubernetes_pod_container_name
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istio-proxy;.*-envoy-prom
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
    - job_name: istiod
      metrics_path: /metrics
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - istio-system
      relabel_configs:
      - source_labels:
        - __meta_kubernetes_pod_label_app
        - __meta_kubernetes_pod_container_port_name
        action: keep
        regex: istiod;http-monitoring
      - source_labels:
        - __meta_kubernetes_namespace
        target_label: namespace
      - source_labels:
        - __meta_kubernetes_pod_name
        target_label: pod
```

仅代理抓取使用 15090 `/stats/prometheus`。默认合并代理/应用指标使用 15020 `/stats/prometheus` 和 `prometheus.io` 注解，需要不同且不重复的抓取任务。代理证书指标需要该代理端点。即使应用流量使用 STRICT mTLS，这些指标监听器仍为明文；限制其网络暴露。抓取独立应用端点遵循自身身份验证策略。

### Prometheus Operator 替代方案

使用这些资源替代手动任务。确保 Prometheus 资源选择其标签/命名空间。`namespaceSelector.any: true` 让 PodMonitor 检查应用命名空间；`port: http-envoy-prom` 选择实际指标容器端口。自定义网关应调整端口名。ServiceMonitor 选择 Service，不是 Deployment 标签。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-component-monitor
  namespace: istio-system
spec:
  selector:
    matchLabels:
      app: istiod
  endpoints:
  - port: http-monitoring
    interval: 15s
    path: /metrics
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: envoy-stats-monitor
  namespace: istio-system
spec:
  namespaceSelector:
    any: true
  selector:
    matchExpressions:
    - key: istio-prometheus-ignore
      operator: DoesNotExist
  podMetricsEndpoints:
  - port: http-envoy-prom
    path: /stats/prometheus
    interval: 15s
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_container_name
      action: keep
      regex: istio-proxy
```

### Prometheus 查询优化

```yaml
# Recording Rules to pre-compute frequently used queries
groups:
- name: istio_recording_rules
  interval: 30s
  rules:
  # Request rate by service
  - record: istio:service:request_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # Error rate by service
  - record: istio:service:error_rate:5m
    expr: |
      sum(rate(istio_requests_total{reporter="destination",response_code=~"5.."}[5m])) by (destination_service_name, destination_service_namespace)
      /
      sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

  # P95 latency by service
  - record: istio:service:latency_p95:5m
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m]))
        by (destination_service_name, destination_service_namespace, le)
      )

  # Circuit breaker state gauge
  - record: istio:circuit_breaker:at_capacity
    expr: |
      envoy_cluster_circuit_breakers_default_rq_open
```

## 使用 Telemetry API 自定义 {#customization-with-telemetry-api}

### 指标自定义

#### 1. 仅启用特定指标

覆盖按顺序评估。先禁用 ALL_METRICS，再重新启用两个所需 HTTP 指标。`mode` 位于 `match` 内。将相关设置合并为每个选择范围一个 Telemetry，不要同时应用所有独立示例。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
        mode: CLIENT_AND_SERVER
      disabled: true
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      disabled: false
    - match:
        metric: REQUEST_DURATION
        mode: CLIENT_AND_SERVER
      disabled: false
```

#### 2. 添加自定义标签

在 HTTP 指标上使用取值有界的 CEL 表达式。请求 ID、任意 User-Agent 值和时间标头会创建无界标签。`x-envoy-upstream-service-time` 是持续时间，不是上游集群身份。CEL 不使用示例中 shell 风格 `| split()` 语法。

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-tags
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        api_version:
          value: 'request.url_path.startsWith("/api/v1/") ? "v1" : (request.url_path.startsWith("/api/v2/")
            ? "v2" : "other")'
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method
            : "OTHER"'
```

#### 3. 命名空间专属指标配置

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: namespace-metrics
  namespace: production
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
        mode: CLIENT_AND_SERVER
      tagOverrides:
        environment:
          value: '"production"'
```

#### 4. 通过禁用指标提高性能

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: disable-tcp-metrics
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    # Completely disable TCP metrics
    - match:
        metric: TCP_OPENED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_CLOSED_CONNECTIONS
      disabled: true
    - match:
        metric: TCP_SENT_BYTES
      disabled: true
    - match:
        metric: TCP_RECEIVED_BYTES
      disabled: true
```

## 实用指标查询 {#practical-metric-queries}

基于 HTTP 状态的错误比例不能捕获每个 gRPC 失败。对于 gRPC，检查 `grpc_response_status` 及应用失败定义；HTTP 200 可承载非零 gRPC 状态。

### 黄金信号仪表板

#### 1. 延迟

```promql
# P50 latency
histogram_quantile(0.50,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P95 latency
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# P99 latency
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{reporter="destination",
    destination_service_name="reviews", destination_service_namespace="default"
  }[5m])) by (le)
)

# Average latency by service
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_request_duration_milliseconds_count{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
```

#### 2. 流量

```promql
# Request rate by service (RPS)
sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Total request rate
sum(rate(istio_requests_total{reporter="destination"}[1m]))

# Inbound traffic by service (bytes/sec)
sum(rate(istio_request_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Outbound traffic by service (bytes/sec)
sum(rate(istio_response_bytes_sum{reporter="destination"}[1m])) by (destination_service_name, destination_service_namespace)

# Request distribution by protocol (not HTTP method)
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (request_protocol, destination_service_name, destination_service_namespace)
```

#### 3. 错误

```promql
# Error rate (5xx errors)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
/
sum(rate(istio_requests_total{reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
* 100

# Separate 4xx vs 5xx
sum(rate(istio_requests_total{response_code=~"4..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)
sum(rate(istio_requests_total{response_code=~"5..", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Track specific error codes
sum(rate(istio_requests_total{response_code="503", reporter="destination"}[5m])) by (destination_service_name, destination_service_namespace)

# Analyze error types via response flags
sum(rate(istio_requests_total{response_flags!~"-", reporter="destination"}[5m])) by (response_flags, destination_service_name, destination_service_namespace)
```

#### 4. 饱和度

```promql
# Connection count and breaker state (not a utilization percentage).
envoy_cluster_upstream_cx_active
envoy_cluster_circuit_breakers_default_cx_open

# Active and pending requests.
envoy_cluster_upstream_rq_active
envoy_cluster_upstream_rq_pending_active

# Allocated proxy memory in bytes; compare with the container memory limit separately.
envoy_server_memory_allocated
```

### mTLS 监控

```promql
# mTLS usage rate
sum(rate(istio_requests_total{
  connection_security_policy="mutual_tls",
  reporter="destination"
}[5m]))
/
sum(rate(istio_requests_total{reporter="destination"}[5m]))
* 100

# Detect non-mTLS traffic
sum(rate(istio_requests_total{
  connection_security_policy="none",
  reporter="destination"
}[5m])) by (source_workload, destination_workload)

# HTTP 401 observed on authenticated mesh traffic; this is not a TLS handshake failure.
sum by (destination_service_name, destination_service_namespace) (
  rate(istio_requests_total{reporter="destination",response_code="401",connection_security_policy="mutual_tls"}[5m])
)
```

### 服务网格健康仪表板

```promql
# Scrape health, not a complete control-plane health check.
up{job="istiod"}

# Istiod xDS build/send error rate, by type.
sum by (type) (rate(pilot_xds_pushes{type=~".*(builderr|senderr)"}[5m]))

# Configuration convergence time, seconds (not push count).
histogram_quantile(0.95,
  sum by (le) (rate(pilot_proxy_convergence_time_bucket[5m]))
)

# Recently started Envoy process; uptime is elapsed seconds, not a timestamp.
envoy_server_uptime < 300
```

使用 `istioctl version` 检查实际代理版本，用 `istioctl proxy-status` 诊断同步/NACK。进程年龄不衡量配置新鲜度，Envoy 数值版本 gauge 也不是版本标签分布。mTLS 失败应按 [mTLS 指南](../security/01-mtls.md)检查 TLS 验证计数器和证书。

## 指标优化 {#metrics-optimization}

### 解决高基数问题

#### 1. 移除不必要标签

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: reduce-cardinality
  namespace: istio-system
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: ALL_METRICS
      tagOverrides:
        # Remove high cardinality labels
        request_id:
          operation: REMOVE
        user_agent:
          operation: REMOVE
```

#### 2. 规范化标签值

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: normalize-labels
  namespace: prod
spec:
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
      tagOverrides:
        # Normalize HTTP methods (GET, POST, PUT, DELETE, OTHER)
        request_method:
          value: 'request.method in ["GET", "POST", "PUT", "DELETE"] ? request.method : "OTHER"'
```

### 选择 Envoy 统计

`proxyStatsMatcher` 选择创建哪些 Envoy 统计；不采样请求。仅包含所需指标族，保留必要的现有匹配，并在更改引导设置后滚动更新选定代理。此示例启用前述查询所需统计：

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      proxyStatsMatcher:
        inclusionRegexps:
        - ".*upstream_rq_timeout.*"
        - ".*upstream_cx_connect_timeout.*"
        - ".*upstream_cx_connect_fail.*"
        - ".*upstream_rq_pending_overflow.*"
        - ".*circuit_breakers.*"
        - ".*outlier_detection.*"
        - ".*upstream_cx_(active|overflow).*"
        - ".*upstream_rq_(active|retry|pending).*"
```

### Prometheus 性能调优

Prometheus 默认抓取间隔为 1 分钟；15s/30s 是有意选择。这是需与现有抓取任务合并的配置片段。`metric_relabel_configs` 位于各抓取任务内，丢弃样本，不只是标签。必须为所选后端配置远程写入端点、身份验证/TLS 和持久化。

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
remote_write:
- url: http://victoria-metrics:8428/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 5
    min_shards: 1
    max_samples_per_send: 5000
scrape_configs:
- job_name: envoy-stats
  metrics_path: /stats/prometheus
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels:
    - __meta_kubernetes_pod_phase
    action: keep
    regex: Running
  - source_labels:
    - __meta_kubernetes_pod_container_name
    - __meta_kubernetes_pod_container_port_name
    action: keep
    regex: istio-proxy;.*-envoy-prom
  - source_labels:
    - __meta_kubernetes_namespace
    target_label: namespace
  - source_labels:
    - __meta_kubernetes_pod_name
    target_label: pod
  metric_relabel_configs:
  - source_labels:
    - __name__
    regex: istio_tcp_.*
    action: drop
```

## 故障排除 {#troubleshooting}

exec/curl 示例要求代理镜像包含 curl。否则使用 `kubectl port-forward pod/<pod-name> 15090:15090`（代理端点使用 15020），并从第二终端查询。此处 Telemetry 示例针对 Envoy；Ambient L7 策略使用 waypoint 附加，并单独采集 ztunnel L4 指标。

### 未采集到指标时

#### 1. 检查 Envoy 指标端点

```bash
# Check Envoy admin port
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | head -20

# Check metrics filter
istioctl proxy-config bootstrap <pod-name> -o json | jq '.bootstrap.statsConfig'
```

#### 2. 检查 Prometheus 是否发现目标

```bash
# Check Targets page in Prometheus UI
kubectl port-forward -n istio-system svc/prometheus 9090:9090

# In browser: http://localhost:9090/targets
```

#### 3. 验证 Telemetry API 配置

```bash
# Check Telemetry resources
kubectl get telemetry -A

# Check specific Telemetry details
kubectl describe telemetry <name> -n <namespace>

# Check if reflected in Envoy config
istioctl proxy-config listeners <pod-name> -n <namespace> -o json
```

### 指标标签缺失时

```bash
# 1. Check if Envoy generates correct labels
kubectl exec -it <pod-name> -c istio-proxy -- curl localhost:15000/stats/prometheus | grep istio_requests_total | head -1

# 2. Check Prometheus relabeling rules
kubectl get configmap prometheus-config -n istio-system -o yaml

# 3. Check ServiceMonitor/PodMonitor
kubectl get servicemonitor,podmonitor -n istio-system
```

### 指标基数爆炸

在另一终端端口转发 Prometheus 后，查询活动序列和 TSDB 统计。统计指标名称不等于统计时间序列。TSDB 状态端点也报告每标签/值基数。

```bash
curl -fsS http://localhost:9090/api/v1/status/tsdb | jq '.data'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=count(istio_requests_total)' | jq '.data.result'
curl -fsSG http://localhost:9090/api/v1/query \
  --data-urlencode 'query=topk(10, count by (__name__) ({__name__=~"istio_.*"}))' | jq '.data.result'
```

### 断路器指标不可见时

```bash
# 1. Check Envoy cluster statistics
istioctl proxy-config cluster <pod-name> --fqdn <service-fqdn> -o json | \
  jq '.[] | .circuitBreakers'

# 2. Check directly from Envoy admin
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl "localhost:15000/clusters" | grep -A 10 "outbound|80||<service>"

# 3. Verify DestinationRule is correctly applied
istioctl analyze -n <namespace>
```

## 参考资料

- [Istio 指标](https://istio.io/latest/docs/reference/config/metrics/)
- [Istio 可观测性](https://istio.io/latest/docs/tasks/observability/)
- [Prometheus 查询示例](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Envoy 统计](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Istio 仪表板](https://grafana.com/grafana/dashboards/?search=istio)
