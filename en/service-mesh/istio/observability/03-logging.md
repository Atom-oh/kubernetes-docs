# Istio Logging

> **Supported Versions**: Istio 1.31
> **Last Reviewed**: September 11, 2026

> **Validation scope**: These lab configurations were checked against official references and offline validators, without deploying a cluster. Namespace, identity, storage, backend and load assumptions are stated with each example and must be verified for the target environment.

Configured access logs record metadata for observed requests/connections. They are separate from Envoy/istiod diagnostics and application logs; they do not capture all mesh activity or full request/response bodies. These examples use sidecars; ambient L7 logging needs waypoint attachment, while ztunnel has separate L4 logs.

## Table of Contents

1. [Logging Overview](#logging-overview)
2. [Access Log Configuration](#access-log-configuration)
3. [Log Customization with Telemetry API](#log-customization-with-telemetry-api)
4. [Log Filtering and Sampling](#log-filtering-and-sampling)
5. [Envoy Log Level Adjustment](#envoy-log-level-adjustment)
6. [Alloy + Loki Integration](#alloy--loki-integration)
7. [Grafana Log Dashboard](#grafana-log-dashboard)
8. [Log Integration with Metrics/Traces](#log-integration-with-metricstraces)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

## Logging Overview

### Istio Log Layers

Envoy → structured stdout → Alloy Kubernetes log collection → Loki → Grafana. As an alternative, an Envoy OTLP access-log provider sends to an OpenTelemetry Collector. Choose one delivery path for the same logs to avoid duplicates. Istiod distributes the selected Telemetry/provider settings.

### Log Types

1. **Access Log**: Configured HTTP request or TCP connection metadata
2. **Envoy Proxy Log**: Internal Envoy operation logs
3. **Istiod Log**: Control plane logs
4. **Application Log**: Application's own logs

## Access Log Configuration

### 1. Define an Access-Log Provider

Merge one of the following provider definitions into the existing Istio install configuration using `istioctl install -f logging-install.yaml`. Preserve other mesh settings/providers. These are installation inputs, not Kubernetes IstioOperator resources. Select the installed provider with Telemetry below; text and JSON are alternative formats.

#### Basic Text Format

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-text
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          text: '[%START_TIME%] "%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %PROTOCOL%" %RESPONSE_CODE%
            %RESPONSE_FLAGS% %DURATION% trace=%TRACE_ID% request=%REQ(X-REQUEST-ID)%'
```

#### JSON Format (Used by the Loki Examples)

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: mesh-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

The provider's format creates JSON fields; the Telemetry filter selects which events are written. `duration` is milliseconds in the log, while CEL `request.duration` is a duration value. `trace_id` is the actual active trace ID when tracing provides one; `request_id` is a separate request correlation value. Query strings are omitted; review any additional headers before logging them.

Logging updates are delivered in proxy configuration; a blanket istiod/workload restart is not the normal activation step. Check effective listeners and a test request. Bootstrap log-level changes discussed later require a selected proxy rollout.

### 2. Fine-grained Control with Telemetry API

Telemetry selects logging per namespace/workload. These examples are alternatives: merge settings so there is only one selector-free resource per namespace. The guide uses SERVER mode for service inbound logs, avoiding client/server duplicate hop counts. Gateway/outbound diagnostics can use separate CLIENT policies and must not be mixed into a service request-rate calculation. With `mesh-text`, select that provider instead of `mesh-json`.

#### Enable JSON Access Log for Entire Mesh

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-logging
  namespace: istio-system
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
```

#### Per-Namespace Log Configuration

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log only errors and slow requests
    filter:
      expression: |
        response.code >= 400 ||
        request.duration > duration("1s")
```

#### Per-Workload Detailed Logging

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: payment-service-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    # Log all requests + additional custom fields
    filter:
      expression: "true"
```

## Log Customization with Telemetry API

### Custom Log Provider

#### 1. Send Logs via OpenTelemetry

This is an alternative to collecting the same stdout logs with Alloy. Install the provider, then select it in a namespace Telemetry resource:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: otel-logging
      envoyOtelAls:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        logFormat:
          text: '%REQ(:METHOD)% %REQ_WITHOUT_QUERY(:PATH)% %RESPONSE_CODE%'
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-access-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: otel-logging
```

The collector from the [tracing guide](02-tracing.md) already defines the OTLP receiver, memory limiter and batch processor. Merge this logs pipeline/exporter into its configuration and reload/redeploy it. Loki 3.7.7 accepts OTLP/HTTP logs at `/otlp/v1/logs` (the exporter appends `/v1/logs`). Its TSDB v13 schema supports structured metadata. OTLP attributes become metadata rather than the stdout JSON body, so adapt queries instead of blindly reusing `| json` examples.

```yaml
exporters:
  otlp_http/loki:
    endpoint: http://loki.observability.svc.cluster.local:3100/otlp
service:
  pipelines:
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_http/loki
```

#### 2. File Logging and Shared Volume

A file path in a provider does not create or mount a volume. This optional pod example mounts a bounded `emptyDir` into the injected proxy; replace the application image. A separate reader must mount the same volume and handle rotation/shipping. Files are not returned by `kubectl logs`, and `emptyDir` is lost with the pod. The main collection example uses stdout instead.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: logging
spec:
  meshConfig:
    extensionProviders:
    - name: envoy-file-logger
      envoyFileAccessLog:
        path: /var/log/istio/access.log
        logFormat:
          labels:
            log_type: access
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(X-ENVOY-ORIGINAL-PATH?:PATH)%'
            protocol: '%PROTOCOL%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            bytes_received: '%BYTES_RECEIVED%'
            bytes_sent: '%BYTES_SENT%'
            duration: '%DURATION%'
            request_id: '%REQ(X-REQUEST-ID)%'
            trace_id: '%TRACE_ID%'
            authority: '%REQ(:AUTHORITY)%'
            upstream_host: '%UPSTREAM_HOST%'
            upstream_cluster: '%UPSTREAM_CLUSTER%'
            route_name: '%ROUTE_NAME%'
            downstream_tls_version: '%DOWNSTREAM_TLS_VERSION%'
            peer_uri_san: '%DOWNSTREAM_PEER_URI_SAN%'
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: file-logging-example
  namespace: production
  labels:
    app: file-logging-example
  annotations:
    sidecar.istio.io/inject: 'true'
    sidecar.istio.io/userVolumeMount: '[{"name":"istio-logs","mountPath":"/var/log/istio"}]'
spec:
  securityContext:
    fsGroup: 1337
  containers:
  - name: app
    image: registry.example.com/team/app:REPLACE_WITH_TESTED_TAG
  volumes:
  - name: istio-logs
    emptyDir:
      sizeLimit: 100Mi
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: file-logging
  namespace: production
spec:
  selector:
    matchLabels:
      app: file-logging-example
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: envoy-file-logger
```

### Log Format Customization

#### Event Filtering with CEL

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: custom-log-format
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
```

**Available Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `request.method` | HTTP method | GET, POST |
| `request.path` | Request path | /api/v1/users |
| `request.url_path` | URL path (excluding query) | /api/v1/users |
| `request.headers` | Request headers | `request.headers['user-agent']` |
| `response.code` | HTTP status code | 200, 404, 500 |
| `response.headers` | Response headers | `response.headers['content-type']` |
| `response.flags` | Integer bitmask | `response.flags != 0` |
| `request.duration` | Request duration value | `duration("1s")` |
| `connection.mtls` | mTLS usage | true, false |
| `connection.uri_san_peer_certificate` | Downstream peer URI SAN, when present | spiffe://... |
| `connection.uri_san_local_certificate` | Downstream local certificate URI SAN | spiffe://... |

## Log Filtering and Sampling

### 1. Conditional Logging

#### Log Only Errors and Slow Requests

HTTP attribute filters apply to HTTP traffic. TCP logging should use connection attributes or an explicitly guarded expression for missing HTTP fields. CEL selects events; it does not define JSON field formatting.

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: error-slow-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        response.code >= 400 ||
        response.code == 0 ||
        request.duration > duration("1s")
```

#### Exclude Specific Paths

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: filter-health-checks
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !(request.url_path.startsWith('/health') ||
          request.url_path.startsWith('/ready') ||
          request.url_path.startsWith('/live') ||
          request.url_path == '/metrics')
```

#### HTTP Method Filtering

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-methods-only
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
```

#### Log Only Non-mTLS Traffic (Security Audit)

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: non-mtls-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: |
        !connection.mtls
```

### 2. Sampling in the Collector

Use Alloy's supported `stage.sampling`; the Telemetry CEL interface has no documented `random()` sampling function. Add the following stage inside `loki.process` for uniform 10% retention:

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

For 1% of successful, sub-second access logs while retaining errors/slow/unclassified logs, parse the integer fields emitted by the JSON provider, classify with temporary labels, sample, then remove those labels before writing. Replace the main process stages with this alternative (keep its `forward_to`):

```alloy
stage.json {
  expressions = { log_type = "log_type", response_code = "response_code", duration = "duration" }
}
stage.labels {
  values = { log_type = "log_type", sample_status = "response_code", sample_duration_ms = "duration" }
}
stage.match {
  selector = "{log_type=\"access\", sample_status=~\"[123][0-9]{2}\", sample_duration_ms=~\"[0-9]{1,3}\"}"
  stage.sampling {
    rate = 0.01
    drop_counter_reason = "normal_access_sampled"
  }
}
stage.label_drop {
  values = ["sample_status", "sample_duration_ms"]
}
```

`stage.match` supports stream selectors and line filters, not a full LogQL label-filter pipeline. The temporary duration label never reaches Loki. Collector sampling reduces ingestion/storage, not proxy log-generation cost. Counts, quantiles and error ratios from these retained logs are biased; use unsampled Istio metrics for whole-traffic SLIs and the dashboard/alert examples below require unsampled access logs.

### 3. Differentiated Logging by Namespace

```yaml
# Production: Log only errors
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: production-logging
  namespace: production
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "response.code >= 400"
---
# Staging: Log all requests
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: staging-logging
  namespace: staging
spec:
  accessLogging:
  - match:
      mode: SERVER
    providers:
    - name: mesh-json
    filter:
      expression: "true"
---
# Development: Disable logging
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: dev-logging
  namespace: development
spec:
  accessLogging:
  - disabled: true
```

## Envoy Log Level Adjustment

### Dynamically Change Log Level

#### Overall Envoy Log Level

```bash
# Change to Debug level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Restore to Info level
istioctl proxy-config log <pod-name> -n <namespace> --level info

# Change to Warning level
istioctl proxy-config log <pod-name> -n <namespace> --level warning
```

#### Per-Component Log Level

```bash
# Debug HTTP connections only
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug

# Debug Router and Connection components only
istioctl proxy-config log <pod-name> -n <namespace> --level router:debug,connection:debug

# Multiple component combinations
istioctl proxy-config log <pod-name> -n <namespace> \
  --level http:debug,router:info,upstream:debug,connection:trace
```

Use `istioctl proxy-config log <pod-name> -n <namespace>` to list the components supported by that proxy version; not every build exposes every example component below.

### Key Envoy Log Components

| Component | Description | Use Case |
|-----------|-------------|----------|
| `admin` | Admin interface | Admin API debugging |
| `aws` | AWS integration | AWS service issues |
| `connection` | TCP connections | Connection problem debugging |
| `filter` | HTTP filters | Filter chain analysis |
| `forward_proxy` | Forward proxy | Proxy behavior tracking |
| `grpc` | gRPC | gRPC communication issues |
| `hc` | Health check | Health check failures |
| `http` | HTTP | HTTP request/response tracking |
| `http2` | HTTP/2 | HTTP/2 protocol issues |
| `jwt` | JWT authentication | JWT token verification |
| `lua` | Lua scripts | Lua filter debugging |
| `main` | Main logic | General Envoy operation |
| `router` | Routing | Routing decision tracking |
| `runtime` | Runtime configuration | Dynamic configuration changes |
| `upstream` | Upstream clusters | Backend connection issues |
| `client` | HTTP client | Outbound requests |
| `pool` | Connection pool | Connection pool management |
| `rbac` | RBAC filter | Permission issue debugging |

### Persistent Log Level Configuration

Merge these install values and roll the selected proxies; inspect existing component levels before a temporary change and restore those values afterwards. Log levels do not enable access logging.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: proxy-log-levels
spec:
  values:
    global:
      proxy:
        logLevel: info
        componentLogLevel: http:debug,router:info,upstream:debug
```

### Apply Debug Logs to Specific Workload Only

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    sidecar.istio.io/componentLogLevel: "http:debug,router:debug"
    sidecar.istio.io/logLevel: "debug"
spec:
  containers:
  - name: app
    image: registry.example.com/team/my-app:REPLACE_WITH_TESTED_TAG
```

## Alloy + Loki Integration

Promtail reached end of life on **March 2, 2026**. Use Alloy or another supported client for new deployments. This example replaces the old Promtail file-tail configuration with Alloy's Kubernetes API log collection; it does not need Docker paths, privileged containers or node filesystem mounts.

### 1. Install Loki (Single Binary)

The following is a fresh, single-replica, single-tenant example using Loki 3.7.7, TSDB v13 and filesystem storage. It is **single binary**, not Simple Scalable mode. Create namespace `observability` first. The `gp3` StorageClass must exist with a working EBS CSI driver on EKS; use your platform's persistent StorageClass elsewhere. Fargate cannot mount EBS volumes, so run this Loki storage workload on suitable EC2 nodes or use an external supported Loki service.

With `auth_enabled: false`, network access grants access to the tenant's logs. Keep endpoints private and configure a supported authentication gateway/TLS for production. Preserve historical schema entries when upgrading an existing Loki installation; the 2024 schema start date below is valid and is not a release date. Compactor retention requires persistent state and `delete_request_store`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: observability
data:
  loki.yaml: |
    auth_enabled: false
    server:
      http_listen_port: 3100
      grpc_listen_port: 9096
    common:
      path_prefix: /loki
      storage:
        filesystem:
          chunks_directory: /loki/chunks
          rules_directory: /loki/rules
      replication_factor: 1
      ring:
        kvstore:
          store: inmemory
    schema_config:
      configs:
      - from: 2024-01-01
        store: tsdb
        object_store: filesystem
        schema: v13
        index:
          prefix: index_
          period: 24h
    limits_config:
      retention_period: 168h
      ingestion_rate_mb: 16
      ingestion_burst_size_mb: 32
      max_query_length: 721h
      max_query_lookback: 721h
      max_streams_per_user: 10000
      max_global_streams_per_user: 0
      reject_old_samples: true
      reject_old_samples_max_age: 168h
    compactor:
      working_directory: /loki/compactor
      compaction_interval: 10m
      retention_enabled: true
      retention_delete_delay: 2h
      retention_delete_worker_count: 150
      delete_request_store: filesystem
    querier:
      max_concurrent: 4
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: observability
spec:
  serviceName: loki-headless
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: loki
        image: grafana/loki:3.7.7
        args:
        - -config.file=/etc/loki/loki.yaml
        ports:
        - containerPort: 3100
          name: http
        - containerPort: 9096
          name: grpc
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: storage
          mountPath: /loki
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: loki-config
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        runAsNonRoot: true
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 100Gi
      storageClassName: gp3
---
apiVersion: v1
kind: Service
metadata:
  name: loki
  namespace: observability
spec:
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: 3100
  - name: grpc
    port: 9096
    targetPort: 9096
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: loki-headless
  namespace: observability
spec:
  clusterIP: None
  selector:
    app: loki
  ports:
  - name: http
    port: 3100
    targetPort: http
```

### 2. Collect Pod Logs with Alloy

Create the application namespaces listed below before applying their RoleBindings, or narrow both discovery and bindings to namespaces that exist. Alloy reads pod metadata and `pods/log` only in those namespaces. The API source already receives container log content without CRI/Docker framing; a file-based source would need runtime parsing and node-local file target paths.

The one-replica example collects sidecar, istiod and application logs while excluding init containers. It labels only namespace/pod/container/app/version and a bounded `log_type`; request IDs, trace IDs, paths and duration remain fields, not Loki index labels. The JSON provider above emits `log_type="access"`, distinguishing access logs from proxy diagnostics in the same container.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: alloy-pod-logs
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: app
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: alloy-pod-logs
  namespace: istio-system
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: alloy-pod-logs
subjects:
- kind: ServiceAccount
  name: alloy
  namespace: observability
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: alloy-config
  namespace: observability
data:
  config.alloy: |
    discovery.kubernetes "pods" {
      role = "pod"
      namespaces {
        names = ["default", "app", "production", "staging", "istio-system"]
      }
    }

    discovery.relabel "logs" {
      targets = discovery.kubernetes.pods.targets
      rule {
        source_labels = ["__meta_kubernetes_pod_phase"]
        regex = "Running"
        action = "keep"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        regex = "istio-init"
        action = "drop"
      }
      rule {
        source_labels = ["__meta_kubernetes_namespace"]
        target_label = "namespace"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_name"]
        target_label = "pod"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_container_name"]
        target_label = "container"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_app"]
        target_label = "app"
      }
      rule {
        source_labels = ["__meta_kubernetes_pod_label_version"]
        target_label = "version"
      }
    }

    loki.source.kubernetes "pods" {
      targets = discovery.relabel.logs.output
      forward_to = [loki.process.logs.receiver]
    }

    loki.process "logs" {
      stage.json {
        expressions = { log_type = "log_type" }
      }
      stage.labels {
        values = { log_type = "log_type" }
      }
      forward_to = [loki.write.local.receiver]
    }

    loki.write "local" {
      endpoint {
        url = "http://loki.observability.svc.cluster.local:3100/loki/api/v1/push"
        batch_wait = "1s"
        batch_size = "1MiB"
        min_backoff_period = "500ms"
        max_backoff_period = "5m"
        max_backoff_retries = 10
        remote_timeout = "10s"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alloy
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alloy
  template:
    metadata:
      labels:
        app: alloy
        sidecar.istio.io/inject: 'false'
    spec:
      serviceAccountName: alloy
      containers:
      - name: alloy
        image: grafana/alloy:v1.19.2
        args:
        - run
        - --server.http.listen-addr=0.0.0.0:12345
        - --storage.path=/var/lib/alloy
        - /etc/alloy/config.alloy
        ports:
        - containerPort: 12345
          name: http-metrics
        volumeMounts:
        - name: config
          mountPath: /etc/alloy
          readOnly: true
        - name: state
          mountPath: /var/lib/alloy
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
      volumes:
      - name: config
        configMap:
          name: alloy-config
      - name: state
        emptyDir:
          sizeLimit: 256Mi
```

This API collection path also avoids DaemonSet restrictions for application pods on Fargate, but it does not collect node logs. It increases Kubernetes API/kubelet work; large installations should evaluate node-local collection or Alloy clustering with coordinated target ownership. Do not simply add identical replicas that tail every pod. The example's `emptyDir` state and bounded retries do not guarantee lossless delivery across restarts/outages; configure persistent buffering/WAL and test recovery for production.

### 3. LogQL Query Examples

The following use the stdout JSON provider and unsampled SERVER access logs. A container selector alone includes proxy diagnostics; `log_type="access"` selects access records. HTTP statistics additionally exclude empty/`-` methods, because TCP connection logs are not HTTP requests. Numeric comparisons use numbers, and `__error__=""` excludes parse/conversion failures before metric aggregation.

#### Basic Queries

```logql
{namespace="production"}

{app="payment-service"}

{container="istio-proxy",log_type="access"}

{namespace="production"} |~ "(?i)error"

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__=""
```

#### Advanced Filtering

```logql
{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | method="POST" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | duration > 1000 | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*UO.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*URX.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | path=~"/api/v1/.*" | __error__=""
```

`UO` is upstream overflow; `URX` means retry/connect-attempt exhaustion. `downstream_tls_version` identifies plaintext versus TLS for the logged connection; `peer_uri_san` gives authenticated peer information when available. Neither is a universal TLS-handshake failure counter, and handshake failures can occur before an HTTP access record exists. The old `connection_security_policy` query referenced a metric label absent from these log records.

#### Aggregation and Statistics

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

These describe retained log entries. Selective logging, sampling, delivery loss, different call paths and gateway logs affect the result; use the standard metrics from the metrics chapter for whole-service SLOs.

## Grafana Log Dashboard

### 1. Add Loki Datasource

Mount the datasource file under Grafana's `provisioning/datasources`, or use the chart's supported provisioning configuration. A ConfigMap alone is not consumed automatically. The `tempo` UID must refer to an existing Tempo datasource. The JSON provider's `trace_id` is used for correlation; request UUIDs are not trace IDs. Empty IDs do not produce a trace link.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  loki.yaml: |
    apiVersion: 1
    datasources:
    - name: Loki
      uid: loki
      type: loki
      access: proxy
      url: http://loki.observability.svc.cluster.local:3100
      jsonData:
        maxLines: 1000
        derivedFields:
        - datasourceUid: tempo
          matcherRegex: '"trace_id"\s*:\s*"([0-9a-fA-F]{32})"'
          name: TraceID
          url: $${__value.raw}
          urlDisplayLabel: View trace
```

### 2. Istio Access Log Dashboard

#### Dashboard JSON

Import the dashboard object below, or mount it through a dashboard provider. It is a dashboard file, not an HTTP API wrapper. Datasource UIDs `loki` and `prometheus` must exist; align the log `app` label with the metric canonical-service value. The heatmap uses real Prometheus histogram buckets; raw log durations do not contain an `le` bucket label.

```json
{
  "title": "Istio Access Logs",
  "tags": [
    "istio",
    "logs"
  ],
  "timezone": "browser",
  "panels": [
    {
      "title": "Logged HTTP Request Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Response Code Distribution",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (response_code) (count_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "P50/P95/P99 Latency",
      "type": "timeseries",
      "targets": [
        {
          "expr": "quantile_over_time(0.5, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P50",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.95, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P95",
          "refId": "B",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        },
        {
          "expr": "quantile_over_time(0.99, {container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app)",
          "legendFormat": "P99",
          "refId": "C",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Error Fraction in Retained Logs",
      "type": "stat",
      "targets": [
        {
          "expr": "sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 500 | response_code < 600 | __error__=\"\" [5m])) / sum by (namespace, app) (rate({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | __error__=\"\" [5m]))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 16
      },
      "id": 4,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Top 10 Routes by Average Logged Duration",
      "type": "table",
      "targets": [
        {
          "expr": "topk(10, avg_over_time({container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | unwrap duration | __error__=\"\" [5m]) by (namespace, app, route_name, method))",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 20
      },
      "id": 5,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Error Logs",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_code >= 400 | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 20
      },
      "id": 6,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "Upstream Overflow Events",
      "type": "logs",
      "targets": [
        {
          "expr": "{container=\"istio-proxy\",log_type=\"access\",namespace=\"$namespace\",app=\"$service\"} | json | method!=\"\" | method!=\"-\" | response_flags=~\".*UO.*\" | __error__=\"\"",
          "refId": "A",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 28
      },
      "id": 7,
      "datasource": {
        "type": "loki",
        "uid": "loki"
      }
    },
    {
      "title": "HTTP Duration Histogram (Prometheus)",
      "type": "heatmap",
      "targets": [
        {
          "expr": "sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter=\"destination\",destination_workload_namespace=\"$namespace\",destination_canonical_service=\"$service\"}[5m]))",
          "format": "heatmap",
          "refId": "A",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 36
      },
      "id": 8,
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      }
    }
  ],
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\"}, namespace)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      },
      {
        "name": "service",
        "type": "query",
        "query": "label_values({container=\"istio-proxy\", namespace=\"$namespace\"}, app)",
        "datasource": {
          "type": "loki",
          "uid": "loki"
        }
      }
    ]
  },
  "uid": "istio-access-logs"
}
```

### 3. Loki Ruler Alerts

Prometheus-style `groups`/`alert`/`expr` YAML is Loki ruler configuration. Grafana-managed alert provisioning instead uses its documented UID, condition and query-data format; export those rules from Grafana when using that route. For Loki ruler evaluation, create this ConfigMap, merge the ruler settings into `loki.yaml`, and merge the volume fragment into the existing StatefulSet while preserving its config/storage mounts. An Alertmanager at the configured address must already exist.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-rules
  namespace: observability
data:
  istio-logging-alerts.yaml: |
    groups:
    - name: istio-logging-alerts
      interval: 1m
      rules:
      - alert: HighHTTPErrorFractionInLogs
        expr: sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!=""
          | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace,
          app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__=""
          [5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Retained HTTP logs show more than 5% server errors
      - alert: CircuitBreakerOverflow
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | response_flags=~".*UO.*" | __error__="" [1m])) > 10
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: Upstream overflow events in access logs
      - alert: SlowLoggedRequests
        expr: quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-"
          | unwrap duration | __error__="" [5m]) by (namespace, app) > 2000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: P95 of logged HTTP durations exceeds 2000ms
      - alert: PlaintextHTTPObserved
        expr: sum by (namespace, app) (count_over_time({container="istio-proxy",log_type="access"} | json
          | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__="" [5m])) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: HTTP access logs show a plaintext downstream connection
```

```yaml
ruler:
  storage:
    type: local
    local:
      directory: /etc/loki/rules
  rule_path: /loki/ruler-scratch
  alertmanager_url: http://alertmanager.observability.svc.cluster.local:9093
  ring:
    kvstore:
      store: inmemory
  enable_api: true
```

```yaml
spec:
  template:
    spec:
      containers:
      - name: loki
        volumeMounts:
        - name: loki-rules
          mountPath: /etc/loki/rules
          readOnly: true
      volumes:
      - name: loki-rules
        configMap:
          name: loki-rules
          items:
          - key: istio-logging-alerts.yaml
            path: fake/istio-logging-alerts.yaml
```

Single-tenant Loki uses tenant ID `fake`, which is why the local rule file is placed under `fake/`. Local rule storage is read-only through the ruler API. These alerts require the full access-log stream; an errors-only or sampled stream cannot provide an unbiased error fraction or latency quantile. Plan no-data and delivery-failure monitoring separately.

## Log Integration with Metrics/Traces

### 1. Jump from Logs to Traces

Use the `trace_id` derived field from the Loki datasource above. It links only when tracing is enabled, the ID is present, and the same trace was retained in Tempo. A request's `x-request-id` is not interchangeable with a W3C trace ID. Sampling and backend retention can leave a valid log without a retrievable trace.

### 2. Metrics Correlation

Prometheus exemplars link **metrics to traces** when an actual exemplar trace-ID label is present; they do not create a metrics-to-logs link. Configure `exemplarTraceIdDestinations.name` to the observed exemplar label (commonly `trace_id`), not an invented `TraceID` field. For metrics-to-logs navigation, configure Grafana correlations/data links with matching namespace/service labels. Datasource settings alone do not manufacture exemplars.

### 3. Integrated Dashboard Queries

Use a Prometheus panel for whole-traffic request rate and a Loki panel for the selected workload's access records. Configure dashboard variables consistently; Istio uses `destination_canonical_service`/workload namespace rather than a universal `app` metric label.

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

Use Grafana-generated Explore links or correlations rather than embedding unencoded JSON in a URL. Ensure the Loki app label and metric service label identify the same workload.

## Performance Optimization

### 1. Reduce Log Volume

Measure the actual proportion of health checks, errors and routine traffic before selecting filters or Alloy sampling. There is no universal 50–90% or 30–50% reduction. Proxy-side filtering reduces generated logs; collector-side sampling reduces downstream ingestion/storage. Keep full traffic metrics and critical audit events independent of a sampled log stream.

An HTTP health-path exclusion can be merged into the existing Telemetry filter; account for missing HTTP fields when logging TCP connections:

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Loki Performance Tuning

```yaml
limits_config:
  # Ingestion limits; these do not directly set chunk size
  ingestion_rate_strategy: global
  ingestion_rate_mb: 32  # Example, size for the workload
  ingestion_burst_size_mb: 64  # Example burst budget

  # Query performance
  max_query_parallelism: 32
  max_query_series: 10000
  max_query_lookback: 720h

  # Stream limits
  max_streams_per_user: 10000
  max_global_streams_per_user: 0

  # Label cardinality limits
  max_label_names_per_series: 30
  max_label_value_length: 2048
```

### 3. Alloy Batching and Retries

```alloy
// loki.write endpoint fragment: merge with the endpoint's existing URL.
batch_wait = "1s"
batch_size = "1MiB"
min_backoff_period = "500ms"
max_backoff_period = "5m"
max_backoff_retries = 10
remote_timeout = "10s"
```

## Troubleshooting

### Access Logs Not Visible

Inspect effective dynamic listeners, selected providers and one known test request. Internal proxy logs do not prove access logging is configured, and the first container log line need not be JSON:

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### Collector or Storage Delivery Failure

Check Alloy target discovery, RoleBindings and pod-log permission. Its API source requires no host log files. Inspect Alloy's own logs and metrics for dropped/retried batches, then query Loki using the range-query endpoint for log streams. Run port-forwards in separate terminals:

```bash
kubectl logs -n observability deployment/alloy --tail=100
kubectl port-forward -n observability deployment/alloy 12345:12345
# Another terminal:
curl -fsS http://localhost:12345/metrics | rg 'loki_(write|process)_'
# Separate terminal:
kubectl port-forward -n observability svc/loki 3100:3100
```

```bash
curl -fsSG http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={container="istio-proxy",log_type="access"}' \
  --data-urlencode 'limit=20' | jq '.data.result'
```

### Log Volume and Cardinality

`kubectl top` measures resource consumption, not log volume. Count byte rate from retained logs and inspect actual stream sets for a bounded interval. `/labels` counts label names, not streams; avoid unbounded high-cardinality `/series` queries on a large installation.

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

Inspect parsed fields before using numeric filters. After `unwrap`, exclude `__error__` before aggregating. Sampled/filtered/lost entries cannot be reconstructed from the retained logs.

## References

- [Istio Access Logging](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Envoy Access Logging](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Alloy Kubernetes log source](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/query/)
- [CEL Expression Language](https://github.com/google/cel-spec)
