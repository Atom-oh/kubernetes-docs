# Istio 日志

> **支持版本**：Istio 1.31
> **最后更新**：2026 年 9 月 11 日

> **验证范围**：这些实验配置依据官方参考和离线验证器检查，未部署集群。各示例注明命名空间、身份、存储、后端和负载假设，必须针对目标环境验证。

配置的访问日志记录观测请求/连接的元数据。它们独立于 Envoy/istiod 诊断和应用日志；不捕获全部网格活动或完整请求/响应正文。示例使用 Sidecar；Ambient L7 日志需要 waypoint 附加，而 ztunnel 有独立 L4 日志。

## 目录

1. [日志概述](#logging-overview)
2. [访问日志配置](#access-log-configuration)
3. [使用 Telemetry API 自定义日志](#log-customization-with-telemetry-api)
4. [日志过滤和采样](#log-filtering-and-sampling)
5. [调整 Envoy 日志级别](#envoy-log-level-adjustment)
6. [Alloy + Loki 集成](#alloy--loki-integration)
7. [Grafana 日志仪表板](#grafana-log-dashboard)
8. [日志与指标/追踪集成](#log-integration-with-metricstraces)
9. [性能优化](#performance-optimization)
10. [故障排除](#troubleshooting)

## 日志概述 {#logging-overview}

### Istio 日志层

Envoy → 结构化 stdout → Alloy Kubernetes 日志采集 → Loki → Grafana。另一方案是 Envoy OTLP 访问日志提供程序向 OpenTelemetry Collector 发送。相同日志选择一条交付路径，避免重复。Istiod 分发所选 Telemetry/提供程序设置。

### 日志类型

1. **访问日志**：配置的 HTTP 请求或 TCP 连接元数据
2. **Envoy 代理日志**：Envoy 内部运行日志
3. **Istiod 日志**：控制平面日志
4. **应用日志**：应用自身日志

## 访问日志配置 {#access-log-configuration}

### 1. 定义访问日志提供程序

使用 `istioctl install -f logging-install.yaml`，将以下一种提供程序定义合并到现有 Istio 安装配置。保留其他网格设置/提供程序。这些是安装输入，不是 Kubernetes IstioOperator 资源。通过下方 Telemetry 选择已安装提供程序；文本和 JSON 是备选格式。

#### 基本文本格式

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

#### JSON 格式（Loki 示例使用）

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

提供程序格式创建 JSON 字段；Telemetry 过滤器选择写入哪些事件。日志中的 `duration` 为毫秒，而 CEL `request.duration` 是持续时间值。追踪提供时，`trace_id` 是实际活动 trace ID；`request_id` 是独立请求关联值。查询字符串已省略；记录额外标头前应审核。

日志更新通过代理配置交付；全面重启 istiod/工作负载不是正常激活步骤。检查有效监听器和测试请求。后文引导日志级别更改需要滚动更新选定代理。

### 2. 使用 Telemetry API 精细控制

Telemetry 按命名空间/工作负载选择日志。这些示例是备选：合并设置，使每命名空间仅一个无选择器资源。本指南对服务入站日志使用 SERVER 模式，避免客户端/服务器重复跳点计数。网关/出站诊断可使用独立 CLIENT 策略，不得混入服务请求速率计算。使用 `mesh-text` 时选择该提供程序，而非 `mesh-json`。

#### 为整个网格启用 JSON 访问日志

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

#### 按命名空间日志配置

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

#### 按工作负载详细日志

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

## 使用 Telemetry API 自定义日志 {#log-customization-with-telemetry-api}

### 自定义日志提供程序

#### 1. 通过 OpenTelemetry 发送日志

这是用 Alloy 采集相同 stdout 日志的替代方案。先安装提供程序，再在命名空间 Telemetry 资源中选择：

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

[追踪指南](02-tracing.md)中的 Collector 已定义 OTLP 接收器、内存限制器和批处理器。将此日志管道/导出器合并到配置，并重新加载/部署。Loki 3.7.7 在 `/otlp/v1/logs` 接受 OTLP/HTTP 日志（导出器追加 `/v1/logs`）。其 TSDB v13 模式支持结构化元数据。OTLP 属性成为元数据，而非 stdout JSON 正文，因此应调整查询，不要盲目复用 `| json` 示例。

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

#### 2. 文件日志和共享卷

提供程序中的文件路径不创建或挂载卷。此可选 Pod 示例将有界 `emptyDir` 挂载到注入代理；替换应用镜像。独立读取器必须挂载相同卷并处理轮换/发送。`kubectl logs` 不返回这些文件，`emptyDir` 随 Pod 丢失。主要采集示例改用 stdout。

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

### 日志格式自定义

#### 使用 CEL 过滤事件

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

**可用变量**：

| 变量 | 描述 | 示例 |
|----------|-------------|---------|
| `request.method` | HTTP 方法 | GET、POST |
| `request.path` | 请求路径 | /api/v1/users |
| `request.url_path` | URL 路径（不含查询） | /api/v1/users |
| `request.headers` | 请求标头 | `request.headers['user-agent']` |
| `response.code` | HTTP 状态码 | 200、404、500 |
| `response.headers` | 响应标头 | `response.headers['content-type']` |
| `response.flags` | 整数位掩码 | `response.flags != 0` |
| `request.duration` | 请求持续时间值 | `duration("1s")` |
| `connection.mtls` | mTLS 使用情况 | true、false |
| `connection.uri_san_peer_certificate` | 下游对等证书 URI SAN（存在时） | spiffe://... |
| `connection.uri_san_local_certificate` | 下游本地证书 URI SAN | spiffe://... |

## 日志过滤和采样 {#log-filtering-and-sampling}

### 1. 条件日志

#### 仅记录错误和慢请求

HTTP 属性过滤器适用于 HTTP 流量。TCP 日志应使用连接属性，或显式保护缺失 HTTP 字段的表达式。CEL 选择事件；不定义 JSON 字段格式。

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

#### 排除特定路径

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

#### HTTP 方法过滤

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

#### 仅记录非 mTLS 流量（安全审计）

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

### 2. 在采集器中采样

使用 Alloy 支持的 `stage.sampling`；Telemetry CEL 接口没有文档规定的 `random()` 采样函数。在 `loki.process` 内添加以下阶段，以均匀保留 10%：

```alloy
stage.sampling {
  rate = 0.1
  drop_counter_reason = "uniform_sampling"
}
```

若要保留成功且不足一秒访问日志的 1%，同时保留错误/慢/未分类日志，应解析 JSON 提供程序输出的整数字段，使用临时标签分类、采样，写入前再移除标签。用此替代方案替换主处理阶段（保留其 `forward_to`）：

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

`stage.match` 支持流选择器和行过滤器，不支持完整 LogQL 标签过滤管道。临时 duration 标签不会到达 Loki。采集器采样减少写入/存储，不减少代理日志生成成本。从保留日志计算的数量、分位数和错误比率有偏；全流量 SLI 使用未采样 Istio 指标，下方仪表板/警报示例要求未采样访问日志。

### 3. 按命名空间差异化日志

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

## 调整 Envoy 日志级别 {#envoy-log-level-adjustment}

### 动态更改日志级别

#### Envoy 整体日志级别

```bash
# Change to Debug level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Restore to Info level
istioctl proxy-config log <pod-name> -n <namespace> --level info

# Change to Warning level
istioctl proxy-config log <pod-name> -n <namespace> --level warning
```

#### 各组件日志级别

```bash
# Debug HTTP connections only
istioctl proxy-config log <pod-name> -n <namespace> --level http:debug

# Debug Router and Connection components only
istioctl proxy-config log <pod-name> -n <namespace> --level router:debug,connection:debug

# Multiple component combinations
istioctl proxy-config log <pod-name> -n <namespace> \
  --level http:debug,router:info,upstream:debug,connection:trace
```

使用 `istioctl proxy-config log <pod-name> -n <namespace>` 列出该代理版本支持的组件；并非每个构建都暴露下方所有示例组件。

### Envoy 主要日志组件

| 组件 | 描述 | 使用场景 |
|-----------|-------------|----------|
| `admin` | 管理接口 | 管理 API 调试 |
| `aws` | AWS 集成 | AWS 服务问题 |
| `connection` | TCP 连接 | 连接问题调试 |
| `filter` | HTTP 过滤器 | 过滤器链分析 |
| `forward_proxy` | 正向代理 | 代理行为跟踪 |
| `grpc` | gRPC | gRPC 通信问题 |
| `hc` | 健康检查 | 健康检查失败 |
| `http` | HTTP | HTTP 请求/响应跟踪 |
| `http2` | HTTP/2 | HTTP/2 协议问题 |
| `jwt` | JWT 身份验证 | JWT 令牌验证 |
| `lua` | Lua 脚本 | Lua 过滤器调试 |
| `main` | 主逻辑 | Envoy 一般运行 |
| `router` | 路由 | 路由决策跟踪 |
| `runtime` | 运行时配置 | 动态配置更改 |
| `upstream` | 上游集群 | 后端连接问题 |
| `client` | HTTP 客户端 | 出站请求 |
| `pool` | 连接池 | 连接池管理 |
| `rbac` | RBAC 过滤器 | 权限问题调试 |

### 持久日志级别配置

合并这些安装 values 并滚动更新选定代理；临时更改前检查现有组件级别，之后恢复。日志级别不启用访问日志。

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

### 仅为特定工作负载应用调试日志

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



## Alloy + Loki 集成 {#alloy--loki-integration}

Promtail 于 **2026 年 3 月 2 日**结束生命周期。新部署使用 Alloy 或其他受支持客户端。此示例以 Alloy Kubernetes API 日志采集替换旧 Promtail 文件跟踪配置；不需要 Docker 路径、特权容器或节点文件系统挂载。

### 1. 安装 Loki（单二进制）

以下是全新单副本、单租户示例，使用 Loki 3.7.7、TSDB v13 和文件系统存储。它是**单二进制**，不是 Simple Scalable 模式。先创建 `observability` 命名空间。在 EKS 上，`gp3` StorageClass 必须存在且 EBS CSI 驱动正常；其他平台使用自己的持久 StorageClass。Fargate 无法挂载 EBS 卷，因此此 Loki 存储工作负载应运行于合适 EC2 节点，或使用外部受支持 Loki 服务。

`auth_enabled: false` 下，网络访问即意味着可访问租户日志。保持端点私有，生产配置受支持身份验证网关/TLS。升级现有 Loki 安装时保留历史模式条目；下方 2024 模式开始日期有效，不是发布日期。Compactor 保留删除要求持久状态和 `delete_request_store`。

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

### 2. 使用 Alloy 采集 Pod 日志

应用 RoleBinding 前创建下方列出的应用命名空间，或将发现及绑定同时缩小到已存在命名空间。Alloy 仅在这些命名空间读取 Pod 元数据和 `pods/log`。API 源已获得不带 CRI/Docker 封装的容器日志内容；文件源则需要运行时解析和节点本地文件目标路径。

单副本示例采集 Sidecar、istiod 和应用日志，排除初始化容器。仅以 namespace/pod/container/app/version 和有界 `log_type` 为标签；请求 ID、trace ID、路径和持续时间保留为字段，不是 Loki 索引标签。上方 JSON 提供程序输出 `log_type="access"`，区分同一容器中的访问日志与代理诊断。

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

此 API 采集路径也避免 Fargate 应用 Pod 的 DaemonSet 限制，但不采集节点日志。它增加 Kubernetes API/kubelet 工作量；大型安装应评估节点本地采集或协调目标所有权的 Alloy 集群。不要简单添加跟踪每个 Pod 的相同副本。示例 `emptyDir` 状态和有界重试不保证跨重启/故障无损交付；生产应配置持久缓冲/WAL 并测试恢复。

### 3. LogQL 查询示例

以下使用 stdout JSON 提供程序及未采样 SERVER 访问日志。仅容器选择器会包含代理诊断；`log_type="access"` 选择访问记录。HTTP 统计还排除空/`-` 方法，因为 TCP 连接日志不是 HTTP 请求。数值比较使用数字，`__error__=""` 在指标聚合前排除解析/转换失败。

#### 基本查询

```logql
{namespace="production"}

{app="payment-service"}

{container="istio-proxy",log_type="access"}

{namespace="production"} |~ "(?i)error"

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__=""
```

#### 高级过滤

```logql
{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | method="POST" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | duration > 1000 | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*UO.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_flags=~".*URX.*" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | downstream_tls_version=~"(-)?" | __error__=""

{container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | path=~"/api/v1/.*" | __error__=""
```

`UO` 是上游溢出；`URX` 表示重试/连接尝试耗尽。`downstream_tls_version` 区分记录连接的明文/TLS；`peer_uri_san` 在可用时提供经过验证的对等信息。两者都不是通用 TLS 握手失败计数器，握手失败可能发生在 HTTP 访问记录产生前。旧 `connection_security_policy` 查询引用了这些日志记录中不存在的指标标签。

#### 聚合和统计

```logql
sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

sum by (response_code) (count_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

quantile_over_time(0.95, {container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)

sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | response_code >= 500 | response_code < 600 | __error__="" [5m])) / sum by (namespace, app) (rate({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | __error__="" [5m]))

avg_over_time({container="istio-proxy",log_type="access"} | json | method!="" | method!="-" | unwrap duration | __error__="" [5m]) by (namespace, app)
```

这些描述保留的日志条目。选择性日志、采样、交付丢失、不同调用路径和网关日志会影响结果；全服务 SLO 使用指标章节的标准指标。

## Grafana 日志仪表板 {#grafana-log-dashboard}

### 1. 添加 Loki 数据源

将数据源文件挂载到 Grafana `provisioning/datasources`，或使用 chart 支持的预置配置。仅 ConfigMap 不会自动使用。`tempo` UID 必须引用现有 Tempo 数据源。JSON 提供程序的 `trace_id` 用于关联；请求 UUID 不是 trace ID。空 ID 不产生追踪链接。

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

### 2. Istio 访问日志仪表板

#### 仪表板 JSON

导入下方仪表板对象，或通过仪表板提供程序挂载。它是仪表板文件，不是 HTTP API 包装层。数据源 UID `loki` 和 `prometheus` 必须存在；对齐日志 `app` 标签和指标规范服务值。热图使用真实 Prometheus 直方图桶；原始日志持续时间不含 `le` 桶标签。

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

### 3. Loki Ruler 警报

Prometheus 风格 `groups`/`alert`/`expr` YAML 是 Loki ruler 配置。Grafana 管理的警报预置使用文档规定的 UID、condition 和 query-data 格式；选择该路径时从 Grafana 导出规则。对于 Loki ruler 评估，创建此 ConfigMap，将 ruler 设置合并到 `loki.yaml`，再将卷片段合并到现有 StatefulSet，保留配置/存储挂载。配置地址上的 Alertmanager 必须已存在。

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

单租户 Loki 使用租户 ID `fake`，所以本地规则文件放在 `fake/` 下。本地规则存储通过 ruler API 只读。这些警报要求完整访问日志流；仅错误或采样流不能提供无偏错误比例或延迟分位数。单独规划无数据和交付失败监控。



## 日志与指标/追踪集成 {#log-integration-with-metricstraces}

### 1. 从日志跳转到追踪

使用上方 Loki 数据源的 `trace_id` 派生字段。仅当启用追踪、ID 存在且相同追踪被 Tempo 保留时才链接。请求 `x-request-id` 不能与 W3C trace ID 互换。采样和后端保留可能使有效日志没有可检索追踪。

### 2. 指标关联

存在实际 exemplar trace ID 标签时，Prometheus 样例将**指标链接到追踪**；不创建指标到日志的链接。将 `exemplarTraceIdDestinations.name` 配置为实际观察的样例标签（通常 `trace_id`），不要虚构 `TraceID` 字段。指标到日志导航应配置 Grafana 关联/数据链接，匹配命名空间/服务标签。仅数据源设置不会制造样例。

### 3. 集成仪表板查询

使用 Prometheus 面板展示全流量请求速率，Loki 面板展示所选工作负载访问记录。一致配置仪表板变量；Istio 使用 `destination_canonical_service`/工作负载命名空间，不是通用 `app` 指标标签。

```promql
sum(rate(istio_requests_total{reporter="destination",destination_workload_namespace="$namespace",destination_canonical_service="$service"}[5m]))
```

```logql
{container="istio-proxy",log_type="access",namespace="$namespace",app="$service"} | json | __error__=""
```

使用 Grafana 生成的 Explore 链接或关联，不要在 URL 嵌入未编码 JSON。确保 Loki app 标签和指标服务标签标识同一工作负载。

## 性能优化 {#performance-optimization}

### 1. 减少日志量

选择过滤器或 Alloy 采样前，测量健康检查、错误和常规流量实际比例。不存在通用 50–90% 或 30–50% 减少。代理端过滤减少生成日志；采集器端采样减少下游写入/存储。完整流量指标和关键审计事件应独立于采样日志流。

可将 HTTP 健康路径排除合并到现有 Telemetry 过滤器；记录 TCP 连接时考虑缺失 HTTP 字段：

```yaml
filter:
  expression: '!has(request.url_path) || !(request.url_path.startsWith("/health") || request.url_path.startsWith("/ready")
    || request.url_path.startsWith("/live") || request.url_path == "/metrics" || request.url_path == "/favicon.ico")'
```

### 2. Loki 性能调优

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

### 3. Alloy 批处理和重试

```alloy
// loki.write endpoint fragment: merge with the endpoint's existing URL.
batch_wait = "1s"
batch_size = "1MiB"
min_backoff_period = "500ms"
max_backoff_period = "5m"
max_backoff_retries = 10
remote_timeout = "10s"
```

## 故障排除 {#troubleshooting}

### 访问日志不可见

检查有效动态监听器、选定提供程序和一个已知测试请求。内部代理日志不能证明已配置访问日志，首行容器日志也不一定是 JSON：

```bash
kubectl get telemetry -A
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("accessLog")) | .accessLog'
kubectl logs <pod-name> -n <namespace> -c istio-proxy --tail=100 | \
  jq -R 'fromjson? | select(.log_type == "access")'
```

### 采集器或存储交付失败

检查 Alloy 目标发现、RoleBinding 和 Pod 日志权限。其 API 源不需要主机日志文件。检查 Alloy 自身日志及指标中的丢弃/重试批次，再使用范围查询端点查询 Loki 日志流。在独立终端运行端口转发：

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

### 日志量和基数

`kubectl top` 测量资源消耗，不测日志量。从保留日志统计字节速率，并在有界间隔检查实际流集合。`/labels` 统计标签名，不是流；大型安装避免无界高基数 `/series` 查询。

```logql
topk(10, sum by (namespace, app) (bytes_rate({container="istio-proxy"} [5m])))

topk(10, sum by (namespace, app) (count_over_time({container="istio-proxy"} [1h])))
```

使用数值过滤器前检查已解析字段。`unwrap` 后，聚合前排除 `__error__`。采样/过滤/丢失条目无法从保留日志重建。

## 参考资料

- [Istio 访问日志](https://istio.io/latest/docs/tasks/observability/logs/access-log/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Envoy 访问日志](https://www.envoyproxy.io/docs/envoy/latest/configuration/observability/access_log/usage)
- [Grafana Loki 文档](https://grafana.com/docs/loki/latest/)
- [Alloy Kubernetes 日志源](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.kubernetes/)
- [Promtail 生命周期](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [LogQL 查询语言](https://grafana.com/docs/loki/latest/query/)
- [CEL 表达式语言](https://github.com/google/cel-spec)
