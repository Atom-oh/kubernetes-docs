# 可观测性堆栈配置与运维

> **最后更新**：October 16, 2026：Loki 3.7.8、Tempo 3.0.3、Alloy 1.20.1、
> OpenTelemetry Collector Contrib 0.162.0、kube-prometheus-stack 92.9.0。

本章介绍采集、存储、权限、保留期限和跨信号导航的配置。
请使用上一章中的[完整 Go/Python 插桩和 Java JSON 日志示例](./08-observability-analysis.md)。
仅安装 Grafana 并不能关联这三种信号。

## 范围和先决条件

| 信号 | 采集路径 | 存储和查询 |
|---|---|---|
| 日志 | 应用程序 JSON stdout → Alloy Kubernetes logs API source | Loki → Grafana |
| Trace | 应用程序 OTLP → Collector → Tempo | Tempo → Grafana |
| 指标 | Prometheus 抓取；可选地远程写入 Tempo 生成的指标 | Prometheus；可选 AMP |

示例使用 `observability` namespace。请准备该 namespace、Prometheus Operator CRD
以及可用的 `gp3` StorageClass。EKS Auto Mode 和普通 EBS CSI 驱动程序使用不同的
StorageClass provisioner；StorageClass 名称相同并不能证明它们兼容。
S3 bucket 和 IRSA 角色是单独的先决条件。请替换账户、角色、bucket 和 workspace
占位符。按用途使用不同的 bucket，并阻止公共访问。将 Loki/Tempo 角色的权限范围
限制为所需的 bucket 列表以及对象读/写/删操作；使用 SSE-KMS 时，还要包含所选 KMS
密钥的权限。

这些设置是配置起点。内部未认证 HTTP、Kafka 连接、资源大小和保留期限并非通用的生产默认值。请针对你的环境验证网络访问、TLS/身份验证、容量和恢复能力。`ClusterIP` 不提供身份验证。

Chart 版本与应用程序版本不同。Loki 和 Tempo 示例使用当前的 `grafana-community`
仓库。向早期的 `grafana/tempo` 单体 Chart 提供分布式配置值，并不会将其变成分布式部署。

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki：部署模式和 S3 存储

Loki 会为流标签建立索引，并以 chunk 形式存储日志内容。内容搜索仍需读取所选流中的数据，因此标签选择、时间范围以及 chunk/index 缓存都会影响查询成本。压缩率和固定的每日流量阈值需要针对具体工作负载进行测量。

| 模式 | 用途和限制 |
|---|---|
| Monolithic | 所有组件运行在一个进程中；HA 需要共享对象存储、复制和路由 |
| SimpleScalable | 分离的 read/write/backend target；已弃用，计划在 Loki 4.0 中移除 |
| Distributed | 独立组件；需要额外的网络、ring、查询路径和存储运维 |

示例使用 Distributed 模式，配置三个 ingester 和一个 compactor。
`zoneAwareReplication: false` 表示仅有三个副本并不能保证 AZ 隔离。
请一并验证 AZ/节点放置、quorum、PDB 和滚动更新。缓存已禁用，以减少初始验证所需的资源；请通过生产负载测试确定缓存容量。

Schema 日期适用于新存储。请勿替换现有安装中的历史 schema 条目：保留这些条目，并遵循添加未来日期条目的流程。
`auth_enabled: false` 表示此内部示例使用单一 `fake` tenant。启用多租户并不会增加用户身份验证；身份验证代理必须验证并设置 tenant header。

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.8
  auth_enabled: false
  commonConfig:
    replication_factor: 3
  schemaConfig:
    configs:
    - from: '2026-09-01'
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h
  storage:
    type: s3
    bucketNames:
      chunks: REPLACE_WITH_UNIQUE_LOKI_CHUNKS_BUCKET
      ruler: REPLACE_WITH_UNIQUE_LOKI_RULER_BUCKET
    s3:
      region: ap-northeast-2
  ingester:
    chunk_encoding: snappy
  compactor:
    retention_enabled: true
    delete_request_store: s3
    retention_delete_delay: 2h
  limits_config:
    retention_period: 720h
    allow_structured_metadata: true
  analytics:
    reporting_enabled: false
serviceAccount:
  create: true
  name: loki
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-loki-s3
singleBinary:
  replicas: 0
read:
  replicas: 0
write:
  replicas: 0
backend:
  replicas: 0
ingester:
  replicas: 3
  zoneAwareReplication:
    enabled: false
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: &id001
      - ReadWriteOnce
      size: 20Gi
      storageClass: gp3
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
queryScheduler:
  replicas: 2
indexGateway:
  replicas: 2
compactor:
  replicas: 1
  persistence:
    enabled: true
    claims:
    - name: data
      accessModes: *id001
      size: 20Gi
      storageClass: gp3
gateway:
  enabled: true
  replicas: 2
chunksCache:
  enabled: false
resultsCache:
  enabled: false
sidecar:
  rules:
    enabled: false
```

```bash
helm template loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml > loki-rendered.yaml
helm upgrade --install loki grafana-community/loki --version 18.12.2   --namespace observability -f loki-values.yaml
```

对于 Chart 18.12.2，请通过 `persistence.claims` 配置 ingester 和 compactor PVC。
替换列表时请包含 `accessModes`。请检查渲染后的 `volumeClaimTemplates` 和实际 PVC 绑定情况，而不仅仅是 Helm 的退出状态。gateway Service 使用端口 **80**；Loki 进程的 HTTP 端口是 **3100**。

### 保留期限

请同时配置 TSDB v13 schema、24 小时索引周期、`compactor.retention_enabled`、
`delete_request_store` 和 `limits_config.retention_period`。删除是异步的，
并会遵循 `retention_delete_delay`。重启时请保留 compactor 删除标记和状态。
不要假设更改保留期限会追溯性地重新组织现有数据。

各 tenant 的覆盖设置应放在 Chart 的 `loki.runtimeConfig.overrides` 下。
单租户示例使用 `fake`。以下片段将默认的 30 天覆盖为 7 天；仅在检查保留需求后应用。

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

对整个 bucket 设置对象生命周期过期策略可能会损坏索引、删除请求和 ruler 配置。如果需要生命周期安全网，请将其范围限定为 chunk 前缀，并将过期时间设置为长于保留期限加删除延迟。请分别评估版本控制/备份成本和删除需求；启用版本控制并不等于完成了恢复测试。

## Alloy 日志采集和标签

Promtail 已于 2026-03-02 结束生命周期（EOL）。新示例使用 Alloy。
此配置通过 Kubernetes logs API，从[上一章](./08-observability-analysis.md)中的
`observability` namespace 读取 `app=correlation-api` 的 Pod。
它不会跟踪节点文件，也不需要 hostPath 挂载或 `stage.cri`。

使用 `Recreate` 的单副本 Deployment 可避免稳定运行和滚动更新期间的重复采集。
但它并非 HA，更新可能中断采集。若要扩展，请同时配置 Alloy clustering 和 source 的 clustering 支持，或限制每个节点的目标范围。若 DaemonSet 中的每个 Pod 都发现所有应用 Pod，就会造成重复采集。

```yaml
# alloy-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy-logs
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: alloy-logs
  namespace: observability
rules:
  - apiGroups: [""]
    resources: [pods]
    verbs: [get, list, watch]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-logs
  namespace: observability
subjects:
  - kind: ServiceAccount
    name: alloy-logs
    namespace: observability
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: alloy-logs
```

```alloy
// logs.alloy
// Kubernetes API log source: configure its ServiceAccount permissions first.
discovery.kubernetes "application" {
  role = "pod"
  namespaces {
    names = ["observability"]
  }
  selectors {
    role  = "pod"
    label = "app=correlation-api"
  }
}

discovery.relabel "application_logs" {
  targets = discovery.kubernetes.application.targets
  rule {
    source_labels = ["__meta_kubernetes_namespace"]
    target_label  = "namespace"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_label_app"]
    target_label  = "service_name"
  }
  rule {
    source_labels = ["__meta_kubernetes_pod_container_name"]
    target_label  = "container"
  }
}

loki.source.kubernetes "application" {
  targets    = discovery.relabel.application_logs.output
  forward_to = [loki.process.application.receiver]
}

loki.process "application" {
  stage.json {
    expressions = {
      level = "level",
    }
  }
  stage.labels {
    values = {
      level = "",
    }
  }
  // Keep the complete JSON body, including trace_id/span_id. They are not
  // indexed stream labels and remain available for parsing/correlation.
  forward_to = [loki.write.backend.receiver]
}

loki.write "backend" {
  endpoint {
    url = "http://loki-gateway.observability.svc:80/loki/api/v1/push"
  }
}
```

将这些值保存为 `alloy-values.yaml`，并通过 `--set-file` 注入前面的文件。
这样可以避免在 YAML 字符串中重复 Alloy 配置。

```yaml
controller:
  type: deployment
  replicas: 1
  updateStrategy:
    type: Recreate
alloy:
  enableReporting: false
  configMap:
    content: ''
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 512Mi
rbac:
  create: false
serviceAccount:
  create: false
  name: alloy-logs
crds:
  create: false
```

```bash
kubectl apply -f alloy-rbac.yaml
helm upgrade --install alloy grafana/alloy --version 1.13.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

优先使用 `namespace`、`service_name` 和 `container` 等取值范围有限的标签。
将 `trace_id` 和 `request_id` 保存在 JSON 内容或结构化元数据中。
Pod 名称并非在所有情况下都禁止使用，但其生命周期和变化频率会影响流数量。
标签组合的乘积才是关键；标签数量固定并不能保证安全。
此示例保留完整的 JSON 行，并额外为 `level` 建立索引。请规范取值范围不受限的 level 值，并在应用程序或采集层移除个人数据。

### LogQL 和日志告警

在数值聚合之前，先排除 JSON 解析错误和无效的数值字段。
以下 latency 字段以毫秒为单位。
`rate` 统计每秒日志行数；要统计每秒字节数，请使用 `bytes_rate`。

```logql
{service_name="correlation-api"} | json | __error__="" | level="ERROR"
```

```logql
sum(rate({service_name="correlation-api"}[5m]))
```

```logql
sum(bytes_rate({service_name="correlation-api"}[5m]))
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms >= 0 | __error__="" | unwrap latency_ms | __error__="" [5m])
```

Loki Ruler 会评估 LogQL 规则并向 Alertmanager 发送告警。将 LogQL 放入 PrometheusRule，或添加任意的 `loki_rule` ConfigMap 标签，都不会加载规则。上述基线配置的 ruler 副本数为零。在测试评估前，请先配置 ruler 部署、其规则存储/API 或挂载、评估间隔和 Alertmanager endpoint。

出现通用的 `"error"` 或 `"unauthorized"` 文本，并不能证明发生了故障或攻击。请检查 kube-state-metrics 中的容器状态以确认 CrashLoopBackOff，而不要只依赖应用程序日志。
比率告警需要对齐分子/分母的范围，并处理解析错误、零流量和错误序列缺失等情况。请将它们连接到[告警路由和抑制测试](./07-observability-alerts.md)。

## Tempo 3：单体和分布式运维

Tempo 支持按 trace ID 查询和 TraceQL 属性搜索。
metrics-generator 会从所选 trace 派生指标；它并不是启用搜索的开关。

| 组件 | Tempo 3 分布式模式下的职责 |
|---|---|
| Distributor | 将传入的 span 写入 Kafka |
| Block-builder | 消费 Kafka 并创建对象存储 block |
| Live-store | 为近期数据查询提供服务 |
| Backend-scheduler / backend-worker | Block 维护、压缩和保留 |
| Query-frontend / querier | 查询近期数据和对象存储 |

2.x 的 ingester 和 compactor target 以及可扩展单二进制模式已被移除。
单进程单体模式不需要 Kafka。
增加其 `replicas` 并不是受支持的分布式 HA 转换方式。

### 单实例实验环境

`tempo-lab-values.yaml` 使用本地 PVC，不使用 Kafka。进程/PVC 故障可能中断可用性；请勿将此配置与分布式 S3 部署配置混用。
对于 Chart 3.0.0，请使用 `null` 禁用单个 Jaeger 协议，而不要移除其父级，否则会导致 Chart 渲染失败。Service 可保留旧端口；请根据实际 receiver 配置和网络策略限制访问。

```yaml
# tempo-lab-values.yaml
replicas: 1
tempo:
  tag: 3.0.3
  reportingEnabled: false
  retention: 336h
  receivers:
    jaeger:
      protocols:
        grpc: null
        thrift_binary: null
        thrift_compact: null
        thrift_http: null
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      memory: 2Gi
  metricsGenerator:
    enabled: true
    storage:
      path: /var/tempo/metrics
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
  overrides:
    defaults:
      metrics_generator:
        processors:
        - service-graphs
        - span-metrics
persistence:
  enabled: true
  storageClassName: gp3
  size: 20Gi
```

```bash
helm upgrade --install tempo grafana-community/tempo --version 3.0.0   --namespace observability -f tempo-lab-values.yaml
```

### 供审查的分布式配置

此文件是单实例 Chart 的替代方案，而不是用于叠加到它上面的配置。Kafka 和 S3 必须已存在。此示例在隔离的验证环境中使用内部 Kafka endpoint。请先根据 Tempo 3.0.3 的客户端支持确认生产环境的 Kafka TLS/身份验证要求。此版本的 `ingest.kafka` 不支持任意的 `tls` 或 MSK IAM 字段。支持 SASL 用户名/密码并不意味着传输加密。

使用默认的 `partitions_per_instance: 1` 时，三个 Kafka partition 需要三个 block-builder。
此 Chart 示例也使用三个 live-store。更改 `auto_create_topic_default_partitions` 不会调整现有 topic 的大小。禁用自动创建时，请另行配置实际的 partition 数量、副本数、最小 ISR、保留期限和容量。
向 block-builder/live-store 配置值添加不受支持的 `persistence` 键不会创建 PVC。
请根据 Chart 的实际存储行为和 Kafka 重放窗口测试恢复能力。

```yaml
# tempo-distributed-values.yaml
reportingEnabled: false
multitenancyEnabled: false
tempo:
  image:
    tag: 3.0.3
ingest:
  kafka:
    address: kafka.kafka.svc.cluster.local:9092
    topic: tempo-traces
    auto_create_topic_enabled: false
    auto_create_topic_default_partitions: 3
blockBuilder:
  replicas: 3
liveStore:
  replicas: 3
backendScheduler:
  enabled: true
  config:
    provider:
      compaction:
        compaction:
          block_retention: 336h
  persistence:
    enabled: true
    size: 20Gi
    storageClass: gp3
backendWorker:
  replicas: 2
  podDisruptionBudget:
    enabled: true
distributor:
  replicas: 2
querier:
  replicas: 2
queryFrontend:
  replicas: 2
traces:
  otlp:
    grpc:
      enabled: true
    http:
      enabled: true
storage:
  trace:
    backend: s3
    s3:
      bucket: REPLACE_WITH_UNIQUE_TEMPO_BUCKET
      endpoint: s3.ap-northeast-2.amazonaws.com
      region: ap-northeast-2
serviceAccount:
  create: true
  name: tempo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-tempo-s3
metricsGenerator:
  enabled: true
  kind: StatefulSet
  persistence:
    enabled: true
    storageClass: gp3
    size: 20Gi
  config:
    storage:
      remote_write:
      - url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090/api/v1/write
        send_exemplars: true
overrides:
  defaults:
    metrics_generator:
      processors:
      - service-graphs
      - span-metrics
gateway:
  enabled: true
```

```bash
helm template tempo grafana-community/tempo-distributed --version 3.5.1   --namespace observability -f tempo-distributed-values.yaml > tempo-rendered.yaml
```

显式设置 `backendWorker.podDisruptionBudget.enabled`，以避免 3.5.1 PDB 模板中的默认值缺失。渲染仍无法测试 Kafka 连接、S3 权限、调度或端到端写入/查询。分布式写入使用 `tempo-distributor:4318`，查询使用 `tempo-query-frontend:3200`；请更新下文 Collector 和 Grafana 实验环境的 URL。

### 从 2.x 迁移到 3.x

对于单体模式，请检查 `tempo-cli migrate config --mode=monolithic` 的输出。
对于分布式模式，请采用并行部署、验证和流量迁移。
移除 `ingester`、`ingester_client`、`compactor`、`metrics_generator_client` 和已移除的
`local_blocks` 配置。历史存储必须使用 vParquet4 或更新版本的 block。

不要同时对共享存储启用两个压缩系统。
在 3.x 默认值和每个 tenant 覆盖项中设置 `compaction_disabled`，然后在停止 2.x compactor 后将其移除。Tenant 覆盖项不会简单地继承未显式填写的默认字段。切换流量前，请验证历史和新 trace ID。
TraceQL metrics 存在迁移限制，例如 RF1 block 覆盖范围；历史 trace 可用并不自动意味着历史指标覆盖范围相同。

## Collector 和采样

此配置用于在单个 Collector 中验证 tail sampling。应用程序必须在其 resource 中设置 `service.name`。它不会自动添加 Kubernetes 元数据；添加 k8sattributes 需要 Pod 关联策略和单独的 RBAC。
Kubernetes event 属于日志信号；`k8s_events` 不是 trace receiver。

敏感属性删除步骤在 tail buffer 之前执行。它只涵盖列出的键，并不涵盖所有可能包含敏感数据的日志、event 或属性。仅对 `db.statement` 做哈希处理并不能确保隐私或机密信息受到保护。

```yaml
# collector.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 768
    spike_limit_mib: 128
  attributes/remove-secrets:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  tail_sampling:
    decision_wait: 30s
    num_traces: 20000
    expected_new_traces_per_sec: 500
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 2000
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    send_batch_size: 512
    send_batch_max_size: 1024
    timeout: 1s
exporters:
  otlphttp/tempo:
    endpoint: http://tempo.observability.svc:4318
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true
      queue_size: 1000
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, attributes/remove-secrets, tail_sampling, batch]
      exporters: [otlphttp/tempo]
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
```

```yaml
# collector-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      automountServiceAccountToken: false
      containers:
        - name: collector
          image: otel/opentelemetry-collector-contrib:0.162.0
          args: ["--config=/etc/otel/collector.yaml"]
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 1Gi
          ports:
            - {name: otlp-grpc, containerPort: 4317}
            - {name: otlp-http, containerPort: 4318}
            - {name: metrics, containerPort: 8888}
            - {name: health, containerPort: 13133}
          readinessProbe:
            httpGet:
              path: /
              port: health
          livenessProbe:
            httpGet:
              path: /
              port: health
          volumeMounts:
            - {name: config, mountPath: /etc/otel, readOnly: true}
      volumes:
        - name: config
          configMap:
            name: otel-collector
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
    - {name: otlp-grpc, port: 4317, targetPort: otlp-grpc}
    - {name: otlp-http, port: 4318, targetPort: otlp-http}
    - {name: metrics, port: 8888, targetPort: metrics}
```

```bash
kubectl create configmap otel-collector --namespace observability   --from-file=collector.yaml --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f collector-deployment.yaml
```

Collector Contrib 0.162.0 使用 `service.telemetry.metrics.readers` 提供内部指标。
不要保留旧的 `metrics.address`、不存在的独立 `rate_limiting` processor，或已移除的 `loki` exporter。这些清单会关联 ConfigMap、Service 和端口。此单实例实验环境使用 `Recreate`；更新可能导致缓冲中的 trace 和内存队列丢失。

| 设置 | 含义 |
|---|---|
| Head sampling | 在开始时做出决定；无法根据尚未知晓的最终错误/延迟进行选择 |
| Tail sampling | 根据 `decision_wait` 内收到的 span 做出决定；无法保证数据完整 |
| Error/latency/baseline 策略 | 在此处以 OR 方式组合；单独的速率限制策略并非全局上限 |
| `spans_per_second` | 每秒 span 数，而非 trace 数；不是独立的 processor |
| `num_traces` | 待处理 trace 缓冲区容量；溢出、延迟数据和重启都可能导致 span 丢失 |
| `send_batch_size` | 发送触发阈值；`send_batch_max_size` 是 batch 大小上限 |

多个 tail sampler 需要按 trace ID 路由，以确保某个 trace 的所有 span 都到达同一个 sampler。普通的随机 Service 负载均衡可能会拆分 trace。Tail sampling 无法恢复被 head sampling 丢弃的 span。队列限制、延迟 span 和接收失败都意味着无法保证保留每个错误 trace。`UNSET` 并非错误状态；将其纳入可能会保留大量正常 span。Service graph 和生成的指标依赖采样；若需要完整请求总体的测量结果，请使用单独插桩的指标。

## TraceQL、service graph 和日志关联

以下是单条 trace 的搜索查询。`span:duration` 测量的是 span，而非整个 trace。
HTTP 属性取决于 SDK 的语义约定版本：上一章经过测试的 Go 示例使用
`http.response.status_code`，而默认的 Python 插桩使用 `http.status_code`。

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 2s }
```

```traceql
{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }
```

```traceql
{ resource.service.name = "correlation-api" } | by(span:status) | count() > 1
```

`>>` 表示后代；`>` 表示直接子级。`| by(...) | count()` 会聚合 span 集。
TraceQL metrics 函数（例如 `rate()`）返回时间序列，与单条 trace 搜索不同。对于已知 ID，请使用 Grafana 的 trace-ID 模式或 Tempo 的 trace API；不要使用无效的内置字段和不完整的 ID，例如 `{ trace:id = "abc123" }`。

Tempo 示例在部署配置和覆盖项中均连接了 service-graphs 和 span-metrics，并将结果发送到 Prometheus remote-write receiver。
Service graph 需要恰当的 client/server SpanKind 和一致的 service name。
将原始 `http.target`、完整 URL 或用户 ID 添加为维度可能会扩大基数。

请复用经过测试的 [Java MDC/Logback 和 Go/Python trace/exemplar 示例](./08-observability-analysis.md)。
当 `is_recording()` 为 false 时，仍可能存在有效的未采样上下文。没有 span 时不要丢弃普通日志，也不要用 `MDC.clear()` 清除无关的 MDC 值。

## Prometheus 和 Grafana

以下 kube-prometheus-stack 配置值启用了用于 Tempo 生成指标的 remote-write receiver 和 exemplar 存储。请将 receiver 的访问范围限制为 Tempo 等受信任的发送方。
应用程序指标仍需配置抓取目标/ServiceMonitor，以及上一章中 `correlation-api` 使用的指标/标签约定。

Grafana 使用显式的 `prometheus`、`loki` 和 `tempo` UID、`tracesToLogsV2`、
可容忍空白字符的 32 字符小写 trace-ID 正则表达式，以及 provisioning `$` 转义。
`serviceMap` target 必须实际包含生成的 service-graph 指标。

```yaml
# prometheus-values.yaml
prometheus:
  prometheusSpec:
    enableFeatures:
    - exemplar-storage
    exemplars:
      maxSize: 100000
    enableRemoteWriteReceiver: true
    retention: 7d
    walCompression: true
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 50Gi
grafana:
  sidecar:
    dashboards:
      enabled: true
      label: grafana_dashboard
      labelValue: '1'
      searchNamespace: observability
    datasources:
      enabled: true
      defaultDatasourceEnabled: false
      alertmanager:
        enabled: false
  additionalDataSources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus-kube-prometheus-prometheus.observability.svc:9090
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
      - name: trace_id
        datasourceUid: tempo
        urlDisplayLabel: View trace
    isDefault: true
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki-gateway.observability.svc:80
    jsonData:
      derivedFields:
      - name: TraceID
        matcherRegex: '"trace_id"\s*:\s*"([0-9a-f]{32})"'
        datasourceUid: tempo
        url: $${__value.raw}
        urlDisplayLabel: View trace
  - name: Tempo
    uid: tempo
    type: tempo
    access: proxy
    url: http://tempo.observability.svc:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service_name
        filterByTraceID: true
        filterBySpanID: false
        customQuery: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: -5m
        spanEndTimeShift: 5m
        tags:
        - key: service.name
          value: service
        queries:
        - name: Request rate
          query: sum(rate(http_requests_total{$$__tags}[5m]))
      serviceMap:
        datasourceUid: prometheus
```

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 92.9.0 --namespace observability -f prometheus-values.yaml
```

Exemplar 需要插桩建立 trace/span 关联、使用 OpenMetrics 暴露、Prometheus 存储支持和 Grafana UID 映射。仅配置 HTTP/2 或 histogram 并不会生成 exemplar。采样、保留期限、租户设置或权限仍可能导致关联的 trace 无法访问。

要自动化配置 dashboard，请将 dashboard JSON 本身放入所选 ConfigMap 的值中。不要使用 API 响应中的 `dashboard` 封装，也不要将 provider YAML 当作 dashboard JSON。这些值会在 `observability` 中选择带有 `grafana_dashboard: "1"` 的 ConfigMap。避免将手动管理的 provider/挂载与重叠的 sidecar 配置混用。上一章中的完整 dashboard JSON 可放入此 ConfigMap。

## AMP：分离写入者和读取者权限

AMP 提供兼容 Prometheus 的存储和查询功能。如果未配置采集器或托管 scraper，它不会采集集群指标。以下 Terraform 会创建 workspace，并创建分离的 IRSA 写入者/读取者角色；EKS OIDC provider 必须已存在。如果没有单独的采集路径，CloudWatch 指标也不会自动包含在内。

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_issuer" {
  type        = string
  description = "EKS OIDC issuer without https:// or a trailing slash."
  validation {
    condition     = can(regex("^oidc\\.eks\\.[a-z0-9-]+\\.amazonaws\\.com/id/[A-Za-z0-9]+$", var.oidc_issuer))
    error_message = "Use the cluster's exact OIDC issuer host/path without https://."
  }
}

resource "aws_prometheus_workspace" "docs" {
  alias = "docs-observability"
}

locals {
  clients = {
    writer = {
      service_account = "prometheus-amp"
      actions         = ["aps:RemoteWrite"]
    }
    reader = {
      service_account = "grafana-amp"
      actions         = ["aps:QueryMetrics", "aps:GetLabels", "aps:GetSeries", "aps:GetMetricMetadata"]
    }
  }
}

resource "aws_iam_role" "amp" {
  for_each = local.clients
  name     = "docs-amp-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:observability:${each.value.service_account}"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "amp" {
  for_each = local.clients
  role     = aws_iam_role.amp[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = aws_prometheus_workspace.docs.arn
    }]
  })
}

output "workspace_id" {
  value = aws_prometheus_workspace.docs.id
}

output "workspace_endpoint" {
  value = aws_prometheus_workspace.docs.prometheus_endpoint
}

output "client_role_arns" {
  value = { for k, v in aws_iam_role.amp : k => v.arn }
}
```

`oidc_provider_arn` 和不含 scheme 的 `oidc_issuer` 必须指向同一个 EKS 集群。
写入者信任 `observability:prometheus-amp`，读取者信任 `observability:grafana-amp`，
二者都将 `aud=sts.amazonaws.com` 作为约束。策略仅针对此 workspace ARN。
Grafana 角色若有 RemoteWrite 权限但没有 QueryMetrics 权限，就无法查询指标。

以下是 `prometheus-values.yaml` 的 AMP 核心叠加配置。
Helm 会替换整个 `additionalDataSources` 列表，因此添加 AMP 前请保留三个基础条目。示例仍会使用本地 Prometheus。

```yaml
prometheus:
  serviceAccount:
    create: true
    name: prometheus-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-writer
  prometheusSpec:
    replicas: 2
    replicaExternalLabelName: __replica__
    externalLabels:
      cluster: production-seoul-prometheus
    remoteWrite:
    - url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/api/v1/remote_write
      sigv4:
        region: ap-northeast-2
      queueConfig:
        maxSamplesPerSend: 1000
        capacity: 5000
        maxShards: 20
grafana:
  serviceAccount:
    create: true
    name: grafana-amp
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/docs-amp-reader
  env:
    GF_AUTH_SIGV4_AUTH_ENABLED: 'true'
  additionalDataSources:
  - name: AMP
    uid: amp
    type: prometheus
    access: proxy
    url: https://aps-workspaces.ap-northeast-2.amazonaws.com/workspaces/REPLACE_WORKSPACE_ID/
    jsonData:
      httpMethod: POST
      sigV4Auth: true
      sigV4AuthType: default
      sigV4Region: ap-northeast-2
```

将该片段保存为 `amp-overlay.yaml`，然后使用已安装 PyYAML 的 Python 显式组装数据源列表。此程序只组合该列表；它不会重新实现 Helm 的通用合并行为。应用之前请替换 IAM 角色 ARN 和 workspace endpoint。

```python
import yaml
from pathlib import Path

base = yaml.safe_load(Path("prometheus-values.yaml").read_text())
overlay = yaml.safe_load(Path("amp-overlay.yaml").read_text())
overlay["grafana"]["additionalDataSources"] = (
    base["grafana"]["additionalDataSources"]
    + overlay["grafana"]["additionalDataSources"]
)
Path("amp-values.yaml").write_text(yaml.safe_dump(overlay, sort_keys=False))
```

```bash
helm template prometheus prometheus-community/kube-prometheus-stack   --version 92.9.0 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### HA、队列和保留期限

AMP HA 去重使用 `cluster` 和 `__replica__`。同一数据的副本需要使用相同的
`cluster` 和不同的 `__replica__` 值。将抓取覆盖范围不同的独立 Prometheus 实例
归入同一个 HA 组可能导致数据丢失。请检查是否与指标自身的 `cluster` 标签冲突。规划各集群之间的 workspace 和 HA 组标签；不同 workspace 不会自动联合查询。

队列的 shard 数量和容量会影响吞吐量和内存。WAL 和重试并非无限缓冲，也不保证交付。本地保留 7 天并不能保证远程写入中断时可以重放 7 天的数据。请监控延迟、故障、拒绝情况和 WAL 行为，并测试恢复。Namespace keep-filter 可能会移除没有该标签的节点/集群指标；`labeldrop` 可能导致原本不同的序列发生冲突。Recording rule 会增加聚合序列，但不会自动移除源基数。

AMP workspace 的保留期限最高可配置为 1,095 天。声称 150 天是硬性上限且必须使用 Thanos 的说法不正确。延长保留期限无法恢复已过期的指标。

| 方面 | AMP | Thanos |
|---|---|---|
| 存储和运维 | 托管存储；用户仍负责采集、IAM、配额、成本和规则 | 运维对象存储集成以及 query/store/compactor 组件 |
| 保留期限 | Workspace 配置和服务限制 | Compactor 策略、对象存储和预算 |
| HA 和多集群 | 显式 HA 标签和 workspace 设计 | 副本标签、去重和 store 连接 |
| 降采样 | 不要假设会像 Thanos 一样自动降采样 | 检查 compactor 分辨率/保留期限和查询行为 |

SigV4 用于验证 AWS 请求；它不能替代 TLS 加密。请一并验证 Grafana 进程的 SigV4 启用状态、凭证、IRSA 信任和 workspace 查询权限。
Amazon Managed Grafana 和自托管 Grafana 使用不同的角色配置流程。

## 应用后

1. 检查渲染后的镜像、PVC、Service 端口、ConfigMap 挂载和 ServiceAccount。
2. 在各自后端查询一条日志、一条 trace 和一个直接插桩的指标。
3. 检查 Grafana 中 trace 到日志、日志到 trace 以及 exemplar 链接的功能，包括租户设置和时间范围。
4. 在生产环境之外测试 Collector 重启、Kafka 重放、S3 权限故障以及远程写入中断/恢复。
5. 观察 Loki 保留期限删除、Tempo block 维护、警告、配额和成本。

本次审查使用了固定版本的 Chart 渲染、Loki/Tempo/Collector/Alloy 原生配置解析器、渲染后 PVC/Service/身份检查以及 Terraform mock 测试。
它没有部署 EKS/Kafka/S3，也未验证 Grafana 实际登录和 AWS 读/写访问。

## 官方参考资料

- [Loki 部署模式](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki 保留期限](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Grafana 社区 Helm Chart](https://github.com/grafana-community/helm-charts)
- [Promtail 生命周期](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3 迁移](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Tempo 3.0.3 Kafka 配置](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Collector tail sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.162.0/processor/tailsamplingprocessor)
- [Collector batch processor](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.162.0/processor/batchprocessor)
- [AMP workspace 配置](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [AMP 高可用性](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [上一章：可观测性分析](./08-observability-analysis.md) | [目录](./README.md) | [下一章：资源优化](./10-resource-optimization.md) >
