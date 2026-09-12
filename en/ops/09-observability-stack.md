# Observability stack configuration and operations

> Reviewed 2026-09-11: Loki 3.7.7, Tempo 3.0.3, Alloy 1.19.2,
> OpenTelemetry Collector Contrib 0.160.0, kube-prometheus-stack 90.1.1.

This chapter configures collection, storage, permissions, retention and cross-signal navigation.
Use the [complete Go/Python instrumentation and Java JSON logging examples](./08-observability-analysis.md)
from the previous chapter. Installing Grafana alone does not correlate the three signals.

## Scope and prerequisites

| Signal | Collection path | Storage and queries |
|---|---|---|
| Logs | Application JSON stdout → Alloy Kubernetes logs API source | Loki → Grafana |
| Traces | Application OTLP → Collector → Tempo | Tempo → Grafana |
| Metrics | Prometheus scrape; optional remote write of Tempo-generated metrics | Prometheus; optional AMP |

Examples use the `observability` namespace. Prepare that namespace, Prometheus Operator CRDs
and a working `gp3` StorageClass. EKS Auto Mode and the ordinary EBS CSI driver use different
StorageClass provisioners; a matching class name does not establish compatibility.
S3 buckets and IRSA roles are separate prerequisites. Replace account, role, bucket and workspace
placeholders. Use separate buckets by purpose with public access blocked. Scope Loki/Tempo roles
to the required bucket listing and object read/write/delete operations; include the selected KMS
key permissions when using SSE-KMS.

These settings are a configuration starting point. Internal unauthenticated HTTP, the Kafka
connection, resource sizes and retention are not universal production defaults. Validate network
access, TLS/authentication, capacity and recovery for your environment. `ClusterIP` does not
provide authentication.

Chart versions differ from application versions. The Loki and Tempo examples use the current
`grafana-community` repository. Supplying distributed values to the former `grafana/tempo`
monolithic chart does not turn it into a distributed deployment.

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

## Loki: deployment modes and S3 storage

Loki indexes stream labels and stores log content in chunks. Content searches still read data
from selected streams, so label selection, time ranges and chunk/index caches affect query cost.
Compression ratios and fixed daily-volume cutoffs require workload-specific measurements.

| Mode | Purpose and constraints |
|---|---|
| Monolithic | Components in one process; HA requires shared object storage, replication and routing |
| SimpleScalable | Separate read/write/backend targets; deprecated and scheduled for removal in Loki 4.0 |
| Distributed | Independent components; additional network, ring, query-path and storage operations |

The example uses Distributed mode with three ingesters and one compactor.
`zoneAwareReplication: false` means three replicas alone do not guarantee AZ isolation.
Validate AZ/node placement, quorum, PDBs and rolling updates together. Caches are disabled to
reduce the initial validation footprint; choose cache capacity through production load tests.

The schema date is for a new store. Do not replace historical schema entries on an existing
installation: preserve them and follow the procedure for adding a future-dated entry.
`auth_enabled: false` selects the single `fake` tenant for this internal example. Enabling
multitenancy does not add user authentication; an authenticating proxy must validate and set tenant headers.

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

For chart 18.12.2, configure ingester and compactor PVCs through `persistence.claims`.
Include `accessModes` when replacing the list. Check rendered `volumeClaimTemplates` and actual
PVC binding, not just Helm's exit status. The gateway Service uses port **80**; Loki's process
HTTP port is **3100**.

### Retention

Configure a TSDB v13 schema with a 24-hour index period, `compactor.retention_enabled`,
`delete_request_store` and `limits_config.retention_period` together. Deletion is asynchronous
and respects `retention_delete_delay`. Preserve compactor deletion markers and state across restarts.
Do not assume a retention change retroactively reorganizes existing data.

Per-tenant overrides belong under the chart's `loki.runtimeConfig.overrides`.
The single-tenant example uses `fake`. The following fragment overrides the 30-day default
with seven days; apply it only after checking your retention requirements.

```yaml
loki:
  runtimeConfig:
    overrides:
      fake:
        retention_period: 168h
```

A bucket-wide object lifecycle expiration can damage indexes, deletion requests and ruler
configuration. If a lifecycle safety net is needed, scope it to chunk prefixes and set expiration
longer than retention plus deletion delay. Assess versioning/backup costs and deletion requirements
separately; enabling versioning is not a recovery test.

## Alloy log collection and labels

Promtail reached EOL on 2026-03-02. New examples use Alloy.
This configuration reads `app=correlation-api` pods in `observability` from the
[previous chapter](./08-observability-analysis.md) through the Kubernetes logs API.
It does not tail node files and does not require hostPath mounts or `stage.cri`.

A single Deployment replica with `Recreate` avoids steady-state and rollout duplication.
It is not HA and updates can interrupt collection. To scale, configure Alloy clustering and
the source's clustering support together, or constrain targets per node. A DaemonSet whose
every pod discovers every application pod duplicates collection.

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

Save these values as `alloy-values.yaml` and inject the preceding file with `--set-file`.
This avoids duplicating the Alloy configuration inside a YAML string.

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

Prefer bounded labels such as `namespace`, `service_name` and `container`.
Keep `trace_id` and `request_id` in JSON content or structured metadata.
Pod names are not universally forbidden, but their lifetime and churn affect stream count.
The product of label combinations matters; a fixed label count is not a safety guarantee.
This example preserves the complete JSON line and additionally indexes `level`. Normalize
unbounded level values and remove personal data at the application or collection layer.

### LogQL and log alerts

Remove JSON parsing errors and invalid numeric fields before numeric aggregation.
The following latency field is measured in milliseconds.
`rate` counts log lines per second; use `bytes_rate` for bytes per second.

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

Loki Ruler evaluates LogQL rules and sends alerts to Alertmanager. Putting LogQL in a
PrometheusRule or adding an arbitrary `loki_rule` ConfigMap label does not load rules.
The baseline above has zero ruler replicas. Configure a ruler deployment, its rule store/API
or mounts, evaluation interval and Alertmanager endpoint before testing evaluation.

The presence of generic `"error"` or `"unauthorized"` text does not prove an outage or attack.
Check kube-state-metrics container state for CrashLoopBackOff rather than relying on application logs.
Ratio alerts need matching numerator/denominator scope, parsing-error handling, zero-traffic
handling and missing-error-series behavior. Connect them to the
[alert routing and inhibition tests](./07-observability-alerts.md).

## Tempo 3: monolithic and distributed operation

Tempo supports trace-ID lookup and TraceQL attribute search.
The metrics-generator derives metrics from selected traces; it is not the switch that enables search.

| Component | Tempo 3 distributed responsibility |
|---|---|
| Distributor | Write incoming spans to Kafka |
| Block-builder | Consume Kafka and create object-store blocks |
| Live-store | Serve recent-data queries |
| Backend-scheduler / backend-worker | Block maintenance, compaction and retention |
| Query-frontend / querier | Query recent data and object storage |

The 2.x ingester and compactor targets and scalable single binary mode have been removed.
Monolithic single-process mode does not require Kafka.
Increasing its `replicas` is not a supported conversion to distributed HA.

### Single-instance lab

`tempo-lab-values.yaml` uses a local PVC without Kafka. A process/PVC failure can interrupt
availability; do not mix this configuration with distributed S3 deployment values.
For chart 3.0.0, disable individual Jaeger protocols with `null` rather than removing the parent,
which breaks chart rendering. The Service can retain legacy ports; restrict access according
to actual receiver configuration and network policies.

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

### Distributed configuration for review

This file is an alternative to the single-instance chart, not an overlay for it.
Kafka and S3 must already exist. The example uses an internal Kafka endpoint in an isolated
validation environment. Confirm your production Kafka TLS/authentication requirements against
Tempo 3.0.3's client support first. Arbitrary `tls` or MSK IAM fields are not supported under
this version's `ingest.kafka`. SASL username/password support does not imply transport encryption.

With the default `partitions_per_instance: 1`, three Kafka partitions require three block-builders.
This chart example also uses three live-stores. Changing `auto_create_topic_default_partitions`
does not resize an existing topic. With auto-creation disabled, configure the actual partition
count, replication, minimum ISR, retention and capacity separately.
Adding unsupported `persistence` keys to block-builder/live-store values does not create PVCs.
Test recovery using the chart's actual storage behavior and Kafka replay window.

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

`backendWorker.podDisruptionBudget.enabled` is explicit to avoid a missing default in the
3.5.1 PDB template. Rendering still does not test Kafka connectivity, S3 permissions,
scheduling or end-to-end writes/queries. Distributed ingestion uses `tempo-distributor:4318`
and queries use `tempo-query-frontend:3200`; update both the Collector and Grafana lab URLs below.

### Migrating 2.x to 3.x

For monolithic mode, review the output of `tempo-cli migrate config --mode=monolithic`.
For distributed mode, use parallel deployment, validation and traffic migration.
Remove `ingester`, `ingester_client`, `compactor`, `metrics_generator_client` and the removed
`local_blocks` configuration. Historical storage must use vParquet4 or newer blocks.

Do not enable two compaction systems against shared storage concurrently.
Set `compaction_disabled` in 3.x defaults and every tenant override, then remove it after
stopping the 2.x compactors. Tenant overrides do not simply inherit omitted default fields.
Verify both historical and new trace IDs before switching traffic.
TraceQL metrics have migration constraints such as RF1 block coverage; historical trace
availability does not automatically imply identical historical metrics coverage.

## Collector and sampling

This configuration validates tail sampling in one Collector. Applications must set
`service.name` in their resource. It does not automatically add Kubernetes metadata;
adding k8sattributes requires a pod-association strategy and separate RBAC.
Kubernetes events are a logs signal; `k8s_events` is not a traces receiver.

Sensitive-attribute deletion precedes the tail buffer. It covers only the listed keys,
not every log, event or attribute that might contain sensitive data. Hashing `db.statement`
alone does not establish privacy or secret protection.

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

Collector Contrib 0.160.0 uses `service.telemetry.metrics.readers` for internal metrics.
Do not retain the former `metrics.address`, a nonexistent standalone `rate_limiting` processor,
or the removed `loki` exporter. The manifests connect the ConfigMap, Service and ports.
This single-instance lab uses `Recreate`; updates can lose buffered traces and in-memory queues.

| Setting | Meaning |
|---|---|
| Head sampling | Decides at the beginning; cannot select by a final error/latency that is not yet known |
| Tail sampling | Decides from spans received within `decision_wait`; completeness is not guaranteed |
| Error/latency/baseline policies | OR-combined here; a separate rate-limit policy is not a global ceiling |
| `spans_per_second` | Spans per second, not traces; not a standalone processor |
| `num_traces` | Pending trace-buffer capacity; overflow, late data and restarts can lose spans |
| `send_batch_size` | Sending trigger; `send_batch_max_size` is the batch-size ceiling |

Multiple tail samplers require trace-ID routing so every span of a trace reaches the same
sampler. Ordinary random Service balancing can split traces. Tail sampling cannot recover
head-dropped spans. Queue limits, late spans and receive failures prevent a guarantee of
preserving every error trace. `UNSET` is not an error status; including it can retain large
volumes of normal spans. Service graphs and generated metrics are sampling-dependent;
use separately instrumented metrics when you need full request-population measurements.

## TraceQL, service graphs and log correlation

These are individual-trace search queries. `span:duration` measures a span, not the whole trace.
HTTP attributes depend on the SDK's semantic-convention version: the tested Go example in
the preceding chapter uses `http.response.status_code`, while default Python instrumentation
uses `http.status_code`.

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

`>>` means descendant; `>` means direct child. `| by(...) | count()` aggregates span sets.
TraceQL metrics functions such as `rate()` return time series and differ from individual-trace
search. Use Grafana's trace-ID mode or Tempo's trace API for a known ID; do not use an invalid
intrinsic and incomplete ID such as `{ trace:id = "abc123" }`.

The Tempo examples connect service-graphs and span-metrics in both deployment configuration
and overrides, then send results to the Prometheus remote-write receiver.
Service graphs need appropriate client/server SpanKind and consistent service names.
Adding raw `http.target`, complete URLs or user IDs as dimensions can inflate cardinality.

Reuse the tested [Java MDC/Logback and Go/Python trace/exemplar examples](./08-observability-analysis.md).
A valid unsampled context can exist when `is_recording()` is false. Do not drop ordinary logs
when no span exists, and do not erase unrelated MDC values with `MDC.clear()`.

## Prometheus and Grafana

The following kube-prometheus-stack values enable the remote-write receiver for Tempo-generated
metrics and exemplar storage. Restrict the receiver to trusted senders such as Tempo.
Application metrics still need a scrape target/ServiceMonitor and the metric/label contract
used by the preceding chapter's `correlation-api`.

Grafana uses explicit `prometheus`, `loki` and `tempo` UIDs, `tracesToLogsV2`,
a whitespace-tolerant 32-character lowercase trace-ID regex and provisioning `$` escaping.
The `serviceMap` target must actually contain generated service-graph metrics.

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

Exemplars require instrumentation trace/span association, OpenMetrics exposition, Prometheus
storage support and Grafana UID mapping. HTTP/2 or histogram configuration alone does not
create exemplars. Sampling, retention, tenancy or permissions can still make a linked trace unavailable.

For dashboard automation, put the dashboard JSON itself in the selected ConfigMap value.
Do not use an API response's `dashboard` wrapper or treat provider YAML as dashboard JSON.
These values select `grafana_dashboard: "1"` ConfigMaps in `observability`.
Avoid mixing a manually managed provider/mount with an overlapping sidecar setup.
The complete dashboard JSON from the preceding chapter can be placed in this ConfigMap.

## AMP: separate writer and reader permissions

AMP provides Prometheus-compatible storage and queries. It does not collect cluster metrics
without a configured collector or managed scraper. The Terraform below creates a workspace
and separate IRSA writer/reader roles; the EKS OIDC provider must already exist.
CloudWatch metrics are not automatically included without a separate collection path.

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

`oidc_provider_arn` and scheme-free `oidc_issuer` must identify the same EKS cluster.
The writer trusts `observability:prometheus-amp`, the reader trusts `observability:grafana-amp`,
and both constrain `aud=sts.amazonaws.com`. Policies target only this workspace ARN.
A Grafana role with RemoteWrite but no QueryMetrics cannot query metrics.

The following is the core AMP overlay for `prometheus-values.yaml`.
Helm replaces the entire `additionalDataSources` list, so retain the three base entries before
adding AMP. The example continues to use local Prometheus as well.

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

Save the fragment as `amp-overlay.yaml`, then explicitly assemble the datasource list using
Python with PyYAML installed. This program only combines that list; it does not reimplement
Helm's general merge behavior. Replace IAM role ARNs and the workspace endpoint before applying.

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

### HA, queues and retention

AMP HA deduplication uses `cluster` and `__replica__`. Replicas of the same data need the same
`cluster` and distinct `__replica__` values. Grouping independent Prometheus instances with
different scrape coverage into one HA group can lose data. Check conflicts with a metric's own
`cluster` label. Plan workspace and HA-group labels across clusters; separate workspaces do not
automatically federate.

Queue shard counts and capacities affect throughput and memory. WAL and retries are not
unlimited buffering or a delivery guarantee. Seven days of local retention does not guarantee
seven days of remote-write outage replay. Monitor lag, failures, rejections and WAL behavior
and test recovery. Namespace keep-filters can remove node/cluster metrics without that label;
`labeldrop` can collide previously distinct series. Recording rules add aggregated series
and do not automatically remove source cardinality.

AMP workspace retention is configurable up to 1,095 days. The assertion that 150 days is a hard
limit requiring Thanos is incorrect. Increasing retention cannot restore expired metrics.

| Area | AMP | Thanos |
|---|---|---|
| Storage and operations | Managed storage; users still own collection, IAM, quotas, cost and rules | Operate object storage integration and query/store/compactor components |
| Retention | Workspace configuration and service limits | Compactor policies, object storage and budget |
| HA and multiple clusters | Explicit HA labels and workspace design | Replica labels, deduplication and store connections |
| Downsampling | Do not assume Thanos-style automatic downsampling | Review compactor resolution/retention and query behavior |

SigV4 authenticates AWS requests; it does not replace TLS encryption. Verify Grafana process
SigV4 enablement, credentials, IRSA trust and workspace query permissions together.
Amazon Managed Grafana and self-hosted Grafana use different role-configuration workflows.

## After applying

1. Check rendered images, PVCs, Service ports, ConfigMap mounts and ServiceAccounts.
2. Query one log, one trace and one directly instrumented metric in their respective backends.
3. Check Grafana trace-to-log, log-to-trace and exemplar links, including tenancy and time ranges.
4. Test Collector restart, Kafka replay, S3 permission failures and remote-write interruption/recovery outside production.
5. Observe Loki retention deletion, Tempo block maintenance, warnings, quotas and cost.

This review used pinned chart rendering, native Loki/Tempo/Collector/Alloy configuration parsers,
rendered PVC/Service/identity checks and Terraform mock tests.
It did not deploy EKS/Kafka/S3 or prove live Grafana login and AWS read/write access.

## Official references

- [Loki deployment modes](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki retention](https://grafana.com/docs/loki/latest/operations/storage/retention/)
- [Grafana community Helm charts](https://github.com/grafana-community/helm-charts)
- [Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3 migration](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/migrate-to-3/)
- [Tempo 3.0.3 Kafka configuration](https://github.com/grafana/tempo/blob/v3.0.3/pkg/ingest/config.go)
- [Collector tail sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Collector batch processor](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/batchprocessor)
- [AMP workspace configuration](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-workspace-configuration.html)
- [AMP high availability](https://docs.aws.amazon.com/prometheus/latest/userguide/Send-high-availability-data.html)

---

< [Previous: Observability analysis](./08-observability-analysis.md) | [Contents](./README.md) | [Next: Resource optimization](./10-resource-optimization.md) >
