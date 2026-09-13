# 可观测性技术栈配置与运维

> **最后更新**：2026 年 9 月 11 日：Loki 3.7.7、Tempo 3.0.3、Alloy 1.19.2，
> OpenTelemetry Collector Contrib 0.160.0、kube-prometheus-stack 90.1.1。

本章配置采集、存储、权限、保留策略和跨信号导航。
使用上一章的[完整 Go/Python 插桩和 Java JSON 日志示例](./08-observability-analysis.md)。
仅安装 Grafana 不会关联这三种信号。

## 范围和前提条件

| 信号 | 采集路径 | 存储和查询 |
|---|---|---|
| 日志 | 应用 JSON stdout → Alloy Kubernetes 日志 API 源 | Loki → Grafana |
| 追踪 | 应用 OTLP → Collector → Tempo | Tempo → Grafana |
| 指标 | Prometheus 抓取；可选远程写入 Tempo 生成的指标 | Prometheus；可选 AMP |

示例使用 `observability` 命名空间。准备该命名空间、Prometheus Operator CRD 和可用的 `gp3` StorageClass。EKS Auto Mode 与普通 EBS CSI 驱动使用不同的 StorageClass 预置器；类名匹配不能证明兼容。S3 桶和 IRSA 角色是独立前提条件。替换账户、角色、桶和工作区占位符。按用途使用独立桶并阻止公有访问。将 Loki/Tempo 角色限制到所需桶列举和对象读取/写入/删除操作；使用 SSE-KMS 时包含所选 KMS 密钥权限。

这些设置是配置起点。内部未经身份验证的 HTTP、Kafka 连接、资源大小和保留期不是通用生产默认值。应验证环境中的网络访问、TLS/身份验证、容量和恢复。`ClusterIP` 不提供身份验证。

Chart 版本不同于应用版本。Loki 和 Tempo 示例使用当前 `grafana-community` 仓库。向旧 `grafana/tempo` 单体 chart 提供分布式 values，不会将其变为分布式部署。

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki：部署模式和 S3 存储

Loki 为流标签建立索引，并将日志内容存储在块中。内容搜索仍需读取所选流的数据，因此标签选择、时间范围和块/索引缓存影响查询成本。压缩比及固定日数据量阈值需要工作负载专属测量。

| 模式 | 用途和约束 |
|---|---|
| 单体 | 组件位于一个进程；高可用需要共享对象存储、复制和路由 |
| SimpleScalable | 分离读/写/后端目标；已弃用，计划在 Loki 4.0 移除 |
| 分布式 | 独立组件；增加网络、环、查询路径和存储运维 |

示例使用分布式模式，包含三个 ingester 和一个 compactor。`zoneAwareReplication: false` 表示仅有三个副本不能保证可用区隔离。应一并验证可用区/节点放置、法定人数、PDB 和滚动更新。为减小初始验证占用，缓存被禁用；通过生产负载测试选择缓存容量。

模式日期适用于新存储。不要替换现有安装的历史模式条目：应保留它们，并遵循添加未来日期条目的流程。`auth_enabled: false` 为此内部示例选择单一 `fake` 租户。启用多租户不会添加用户身份验证；身份验证代理必须验证并设置租户标头。

```yaml
# loki-values.yaml
deploymentMode: Distributed
loki:
  image:
    tag: 3.7.7
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

对于 chart 18.12.2，通过 `persistence.claims` 配置 ingester 和 compactor PVC。替换列表时包含 `accessModes`。检查渲染的 `volumeClaimTemplates` 和实际 PVC 绑定，不要只看 Helm 退出状态。网关 Service 使用端口 **80**；Loki 进程 HTTP 端口为 **3100**。

### 保留策略

同时配置采用 24 小时索引周期的 TSDB v13 模式、`compactor.retention_enabled`、`delete_request_store` 和 `limits_config.retention_period`。删除是异步的，并遵循 `retention_delete_delay`。重启时保留 compactor 删除标记和状态。不要假定更改保留期会追溯性地重组现有数据。

每租户覆盖设置位于 chart 的 `loki.runtimeConfig.overrides`。单租户示例使用 `fake`。以下片段将默认 30 天覆盖为七天；仅在检查保留要求后应用。

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

桶范围的对象生命周期到期可能损坏索引、删除请求和 ruler 配置。如果需要生命周期兜底，应将范围限制到块前缀，并将到期时间设为长于保留期加删除延迟。单独评估版本控制/备份成本和删除要求；启用版本控制不是恢复测试。

## Alloy 日志采集和标签

Promtail 于 2026-03-02 结束生命周期。新示例使用 Alloy。此配置通过 Kubernetes 日志 API 读取[上一章](./08-observability-analysis.md)中 `observability` 内的 `app=correlation-api` Pod。它不跟踪节点文件，不需要 hostPath 挂载或 `stage.cri`。

使用 `Recreate` 的单副本 Deployment 避免稳态和滚动发布期间重复采集。它不具备高可用，更新可能中断采集。扩展时，应同时配置 Alloy 集群和源的集群支持，或按节点限制目标。若 DaemonSet 每个 Pod 都发现所有应用 Pod，就会重复采集。

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

将这些 values 保存为 `alloy-values.yaml`，并通过 `--set-file` 注入前面的文件。这样避免在 YAML 字符串内重复 Alloy 配置。

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
helm upgrade --install alloy grafana/alloy --version 1.12.1   --namespace observability -f alloy-values.yaml   --set-file alloy.configMap.content=logs.alloy
```

优先使用 `namespace`、`service_name` 和 `container` 等取值有界标签。将 `trace_id` 和 `request_id` 保留在 JSON 内容或结构化元数据中。Pod 名称并非一律禁止，但生命周期和变动影响流数量。标签组合的乘积很重要；固定标签数不是安全保证。此示例保留完整 JSON 行，并额外为 `level` 建立索引。在应用或采集层规范化无界 level 值并移除个人数据。

### LogQL 和日志警报

数值聚合前，移除 JSON 解析错误和无效数值字段。以下延迟字段以毫秒计。`rate` 统计每秒日志行数；每秒字节数使用 `bytes_rate`。

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

Loki Ruler 评估 LogQL 规则并向 Alertmanager 发送警报。将 LogQL 放入 PrometheusRule，或添加任意 `loki_rule` ConfigMap 标签，不会加载规则。上方基线的 ruler 副本数为零。测试评估前，配置 ruler 部署、规则存储/API 或挂载、评估间隔和 Alertmanager 端点。

出现通用 `"error"` 或 `"unauthorized"` 文本不能证明发生故障或攻击。检查 kube-state-metrics 容器状态中的 CrashLoopBackOff，不要依赖应用日志。比例警报需要匹配的分子/分母范围、解析错误处理、零流量处理及错误序列缺失行为。将其接入[警报路由和抑制测试](./07-observability-alerts.md)。

## Tempo 3：单体与分布式运维

Tempo 支持按 trace ID 查找和 TraceQL 属性搜索。metrics-generator 从选定追踪派生指标；它不是启用搜索的开关。

| 组件 | Tempo 3 分布式职责 |
|---|---|
| Distributor | 将收到的 span 写入 Kafka |
| Block-builder | 消费 Kafka 并创建对象存储块 |
| Live-store | 提供近期数据查询 |
| Backend-scheduler / backend-worker | 块维护、压缩整理和保留 |
| Query-frontend / querier | 查询近期数据和对象存储 |

2.x ingester、compactor 目标及可扩展单二进制模式已移除。单体单进程模式不需要 Kafka。增加其 `replicas` 不是转为分布式高可用的受支持方法。

### 单实例实验

`tempo-lab-values.yaml` 使用本地 PVC，不使用 Kafka。进程/PVC 故障可中断可用性；不要将此配置与分布式 S3 部署 values 混用。对于 chart 3.0.0，使用 `null` 禁用各 Jaeger 协议，不要移除父项，否则会破坏 chart 渲染。Service 可保留旧端口；根据实际接收器配置和网络策略限制访问。

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

### 供审核的分布式配置

此文件是单实例 chart 的替代方案，不是其覆盖配置。Kafka 和 S3 必须已存在。示例在隔离验证环境中使用内部 Kafka 端点。先对照 Tempo 3.0.3 客户端支持确认生产 Kafka TLS/身份验证要求。此版本的 `ingest.kafka` 不支持任意 `tls` 或 MSK IAM 字段。SASL 用户名/密码支持不意味着传输加密。

默认 `partitions_per_instance: 1` 下，三个 Kafka 分区需要三个 block-builder。此 chart 示例也使用三个 live-store。更改 `auto_create_topic_default_partitions` 不会调整现有主题大小。禁用自动创建时，单独配置实际分区数、复制、最小 ISR、保留期和容量。向 block-builder/live-store values 添加不受支持的 `persistence` 键不会创建 PVC。根据 chart 的实际存储行为和 Kafka 重放窗口测试恢复。

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

显式设置 `backendWorker.podDisruptionBudget.enabled`，以避免 3.5.1 PDB 模板缺失默认值。渲染仍不测试 Kafka 连通性、S3 权限、调度或端到端写入/查询。分布式写入使用 `tempo-distributor:4318`，查询使用 `tempo-query-frontend:3200`；更新下方 Collector 和 Grafana 的两个实验 URL。

### 从 2.x 迁移到 3.x

对于单体模式，审核 `tempo-cli migrate config --mode=monolithic` 的输出。对于分布式模式，采用并行部署、验证和流量迁移。移除 `ingester`、`ingester_client`、`compactor`、`metrics_generator_client` 和已移除的 `local_blocks` 配置。历史存储必须使用 vParquet4 或更新的块。

不要同时启用两个压缩整理系统操作共享存储。在 3.x 默认配置及每个租户覆盖中设置 `compaction_disabled`，停止 2.x compactor 后再移除它。租户覆盖不会简单继承省略的默认字段。切换流量前，验证历史和新的 trace ID。TraceQL 指标存在 RF1 块覆盖等迁移约束；历史追踪可用不自动意味着历史指标覆盖相同。

## Collector 和采样

此配置在一个 Collector 中验证尾部采样。应用必须在资源中设置 `service.name`。它不会自动添加 Kubernetes 元数据；添加 k8sattributes 需要 Pod 关联策略和独立 RBAC。Kubernetes 事件属于日志信号；`k8s_events` 不是追踪接收器。

敏感属性删除发生在尾部缓冲之前。它仅覆盖所列键，不覆盖所有可能含敏感数据的日志、事件或属性。仅对 `db.statement` 哈希不能确保隐私或密钥保护。

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
          image: otel/opentelemetry-collector-contrib:0.160.0
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

Collector Contrib 0.160.0 使用 `service.telemetry.metrics.readers` 配置内部指标。不要保留旧 `metrics.address`、不存在的独立 `rate_limiting` 处理器或已移除的 `loki` 导出器。清单连接 ConfigMap、Service 和端口。此单实例实验使用 `Recreate`；更新可能丢失缓冲追踪和内存队列。

| 设置 | 含义 |
|---|---|
| 头部采样 | 在开始时决定；不能根据尚未知晓的最终错误/延迟选择 |
| 尾部采样 | 根据 `decision_wait` 内收到的 span 决定；不保证完整性 |
| 错误/延迟/基线策略 | 此处按 OR 组合；独立限速策略不是全局上限 |
| `spans_per_second` | 每秒 span 数，不是 trace 数；不是独立处理器 |
| `num_traces` | 待决追踪缓冲容量；溢出、迟到数据和重启可能丢失 span |
| `send_batch_size` | 发送触发值；`send_batch_max_size` 是批大小上限 |

多个尾部采样器需要按 trace ID 路由，确保同一追踪的所有 span 到达同一采样器。普通随机 Service 均衡可拆散追踪。尾部采样无法恢复头部丢弃的 span。队列限制、迟到 span 和接收失败使其不能保证保留每条错误追踪。`UNSET` 不是错误状态；包含它可能保留大量正常 span。服务图和生成指标受采样影响；需要完整请求总体测量时，使用独立插桩指标。

## TraceQL、服务图和日志关联

这些是单条追踪搜索查询。`span:duration` 测量一个 span，不是整个追踪。HTTP 属性取决于 SDK 语义约定版本：上一章已测试 Go 示例使用 `http.response.status_code`，而默认 Python 插桩使用 `http.status_code`。

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

`>>` 表示后代；`>` 表示直接子级。`| by(...) | count()` 聚合 span 集合。`rate()` 等 TraceQL 指标函数返回时间序列，不同于单条追踪搜索。对已知 ID 使用 Grafana trace ID 模式或 Tempo 追踪 API；不要使用 `{ trace:id = "abc123" }` 这样的无效内在属性和不完整 ID。

Tempo 示例在部署配置和覆盖设置中同时连接 service-graphs 和 span-metrics，再将结果发送到 Prometheus 远程写入接收器。服务图需要适当的客户端/服务器 SpanKind 及一致服务名。添加原始 `http.target`、完整 URL 或用户 ID 作为维度可能导致基数膨胀。

复用已测试的 [Java MDC/Logback 和 Go/Python 追踪/样例示例](./08-observability-analysis.md)。`is_recording()` 为 false 时仍可能存在有效的未采样上下文。没有 span 时不要丢弃普通日志，也不要用 `MDC.clear()` 清除无关 MDC 值。

## Prometheus 和 Grafana

以下 kube-prometheus-stack values 为 Tempo 生成指标启用远程写入接收器和样例存储。将接收器限制为 Tempo 等可信发送方。应用指标仍需要抓取目标/ServiceMonitor，以及上一章 `correlation-api` 使用的指标/标签约定。

Grafana 使用显式 `prometheus`、`loki` 和 `tempo` UID、`tracesToLogsV2`、容忍空白的 32 字符小写 trace ID 正则表达式，以及预置配置中的 `$` 转义。`serviceMap` 目标必须实际包含生成的服务图指标。

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
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability -f prometheus-values.yaml
```

样例需要插桩中的 trace/span 关联、OpenMetrics 暴露格式、Prometheus 存储支持和 Grafana UID 映射。仅 HTTP/2 或直方图配置不会创建样例。采样、保留、租户或权限仍可能使链接的追踪不可用。

仪表板自动化时，将仪表板 JSON 本身放入选定 ConfigMap 值。不要使用 API 响应的 `dashboard` 包装层，也不要将提供程序 YAML 当作仪表板 JSON。这些 values 选择 `observability` 中带 `grafana_dashboard: "1"` 的 ConfigMap。避免将手动管理的提供程序/挂载与重叠 Sidecar 设置混用。上一章的完整仪表板 JSON 可放入此 ConfigMap。

## AMP：分离写入和读取权限

AMP 提供兼容 Prometheus 的存储和查询。没有配置的采集器或托管抓取器，它不会采集集群指标。以下 Terraform 创建工作区及独立 IRSA 写入/读取角色；EKS OIDC 提供程序必须已存在。没有独立采集路径，CloudWatch 指标不会自动包含在内。

```hcl
# amp.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.64.0"
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

`oidc_provider_arn` 和不带协议的 `oidc_issuer` 必须标识同一 EKS 集群。写入方信任 `observability:prometheus-amp`，读取方信任 `observability:grafana-amp`，两者均约束 `aud=sts.amazonaws.com`。策略仅针对该工作区 ARN。具有 RemoteWrite 但没有 QueryMetrics 的 Grafana 角色无法查询指标。

以下是 `prometheus-values.yaml` 的核心 AMP 覆盖配置。Helm 替换整个 `additionalDataSources` 列表，因此添加 AMP 前保留三个基础条目。示例继续同时使用本地 Prometheus。

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

将片段保存为 `amp-overlay.yaml`，再使用已安装 PyYAML 的 Python 显式组装数据源列表。此程序仅合并该列表，不重新实现 Helm 通用合并行为。应用前替换 IAM 角色 ARN 和工作区端点。

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
helm template prometheus prometheus-community/kube-prometheus-stack   --version 90.1.1 --namespace observability   -f prometheus-values.yaml -f amp-values.yaml > amp-rendered.yaml
```

### 高可用、队列和保留

AMP 高可用去重使用 `cluster` 和 `__replica__`。相同数据的副本需要相同 `cluster` 及不同 `__replica__` 值。将抓取覆盖不同的独立 Prometheus 实例归入同一高可用组可能丢失数据。检查与指标自身 `cluster` 标签的冲突。跨集群规划工作区和高可用组标签；独立工作区不会自动联邦化。

队列分片数和容量影响吞吐量与内存。WAL 和重试不是无限缓冲或交付保证。本地保留七天不保证可以重放七天远程写入中断的数据。监控积压、失败、拒绝和 WAL 行为，并测试恢复。命名空间保留过滤器可能移除没有该标签的节点/集群指标；`labeldrop` 可能使原本不同的序列冲突。记录规则添加聚合序列，不会自动降低源基数。

AMP 工作区保留期可配置，最长 1,095 天。声称 150 天是必须使用 Thanos 才能突破的硬限制是不正确的。延长保留期不能恢复已过期指标。

| 领域 | AMP | Thanos |
|---|---|---|
| 存储和运维 | 托管存储；用户仍负责采集、IAM、配额、成本和规则 | 运维对象存储集成及 query/store/compactor 组件 |
| 保留 | 工作区配置和服务限制 | Compactor 策略、对象存储和预算 |
| 高可用与多集群 | 显式高可用标签和工作区设计 | 副本标签、去重和存储连接 |
| 降采样 | 不要假定具有 Thanos 式自动降采样 | 审核 compactor 分辨率/保留和查询行为 |

SigV4 验证 AWS 请求；不替代 TLS 加密。同时验证 Grafana 进程 SigV4 启用、凭证、IRSA 信任和工作区查询权限。Amazon Managed Grafana 与自托管 Grafana 使用不同角色配置流程。

## 应用后

1. 检查渲染的镜像、PVC、Service 端口、ConfigMap 挂载和 ServiceAccount。
2. 在各自后端查询一条日志、一条追踪和一个直接插桩指标。
3. 检查 Grafana 追踪到日志、日志到追踪和样例链接，包括租户及时间范围。
4. 在生产环境之外测试 Collector 重启、Kafka 重放、S3 权限失败和远程写入中断/恢复。
5. 观察 Loki 保留删除、Tempo 块维护、警告、配额和成本。

本次审查使用固定版本 chart 渲染、原生 Loki/Tempo/Collector/Alloy 配置解析器、渲染后的 PVC/Service/身份检查和 Terraform 模拟测试。未部署 EKS/Kafka/S3，也未证明实际 Grafana 登录及 AWS 读写访问成功。

## 官方参考资料

- [Loki 部署模式](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki 保留策略](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Grafana 社区 Helm chart](https://github.com/grafana-community/helm-charts)
- [Promtail 生命周期](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3 迁移](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Tempo 3.0.3 Kafka 配置](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Collector 尾部采样](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Collector 批处理器](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/batchprocessor)
- [AMP 工作区配置](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [AMP 高可用](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [上一篇：可观测性分析](./08-observability-analysis.md) | [目录](./README.md) | [下一篇：资源优化](./10-resource-optimization.md) >
