# OpenTelemetry

> **审阅基线**：Collector Contrib 0.160.0；Operator 0.158.0；语言版本见下文
> **最后更新**：2026年10月19日

## 简介

OpenTelemetry（OTel）是面向云原生软件的可观测性框架。它提供与供应商无关的标准，用于生成、收集和管理三种信号：Trace、Metrics 和 Logs。CNCF 于 2026 年 7 月 24 日发布的回顾文章称，OpenTelemetry 的贡献速度仅次于 Kubernetes。项目成熟度与各个 SDK/组件的稳定性是两个不同的方面。

### 2026 年 7 月更新：CNCF 毕业

OpenTelemetry 于 **2026 年 5 月**达到 CNCF **毕业**级别；7 月 24 日的文章是一篇回顾。这是基金会的最高成熟度级别，Kubernetes 和 Prometheus 等项目也已达到这一水平。毕业意味着该项目的治理、安全实践和采用情况已通过生产环境使用方面的审查。回顾文章讨论了 GenAI 语义约定、浏览器/移动端可观测性、Schema 治理和部署工具。有关背景和路线图，请参阅 CNCF 博客文章 ["OpenTelemetry has graduated… Now what?"](https://www.cncf.io/blog/2026/07/24/opentelemetry-has-graduated-now-what/)。

## 什么是 OpenTelemetry？

OpenTelemetry 源于 OpenTracing 与 OpenCensus 两个项目的合并：

![历史里程碑包括 OpenTracing 于 2016 年加入 CNCF、2017 年创建 OpenCensus Go 仓库，以及 2019 年 OpenTelemetry 合并；随后推出规范、SDK、Collector 和协议。](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-0.html)

## 核心概念

### 三种信号

本章重点介绍 Trace、Metrics 和 Logs。Profiling 是另一种仍在发展的信号；不同实现的支持情况和稳定性各不相同。Trace/Log ID 和 Metric exemplar 需要相应的插桩和后端配置。

| 信号 | 描述 | 使用场景 |
|--------|-------------|-----------|
| **Traces** | 分布式请求跟踪 | 延迟分析、依赖关系映射 |
| **Metrics** | 数值测量 | 资源使用情况、SLI/SLO |
| **Logs** | 事件记录 | 调试、审计 |

### 核心组件

![应用代码通过 OTel API 和 SDK 发出遥测数据，进入接收、处理和导出流水线，再分发到五个可观测性后端：Tempo、Prometheus、Loki、X-Ray 和 Datadog。](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-2.html)

图中按信号列出了后端选项。只有已配置的 exporter 才会启用；下方的基础示例不会自动启用所有供应商。


## OpenTelemetry SDK

Collector、Operator、Java agent 和各语言 SDK 的版本号彼此独立。这些 Linux 工作负载模板已根据 Kubernetes 1.35 Schema 检查：应用镜像、命名空间、证书和目标 Service 必须由各自所有者准备。更广泛的 Operator 兼容性矩阵并不会免除特定示例的要求，例如原生 sidecar。通过本地检查并不能证明已部署的 EKS 应用可正常运行。

| 组件 | 基线和范围 |
|---|---|
| 独立版 Collector Contrib | 0.160.0；使用其实际二进制文件检查组件和 Schema |
| Operator | 0.158.0；其兼容性表列出 Kubernetes 1.25–1.36 和 cert-manager v1 |
| Java agent | 2.31.1，目标 SDK 为 1.65.0；与 Operator 默认 Java 镜像的版本不同 |
| Python | SDK/exporter 1.44.0，instrumentation/distro 0.65b0；Python ≥3.10 |
| Node.js CommonJS 示例 | SDK-node 0.220.0、auto-instrumentations-node 0.78.0、resources 2.9.0、API 1.9.1 |

Operator 默认使用 Collector 0.158.0。下方的独立版 0.160.0 工作负载并不是由 Operator 管理的 Collector 升级。请检查其与受支持 EKS 版本的交集；最新的 Kubernetes 版本并不一定包含在 Operator 兼容性矩阵中。

### 自动插桩

截至 2026 年 10 月 12 日，EKS 标准支持版本包括 1.34–1.37。1.35 Schema 基线处于此列表和 Operator 矩阵的范围内；但这仍不能替代对实时平台和附加组件的验收检查。

零代码插桩会对受支持的库进行 hook；它不会发现任意业务操作。对于一个进程，请选择直接准备 agent/launcher，或使用 Operator 注入。不要在已配置的 provider 上再初始化第二个 SDK。以下应用镜像是占位符，应替换为你自己的构建，包括启动命令和依赖项。

准备 `ecommerce` 命名空间，并在其中创建 `otel-client-tls` Secret，包含 `ca.crt`、`tls.crt` 和 `tls.key`。客户端证书必须能被 Collector 接受，且 Collector 的证书必须匹配 `otel-collector.otel.svc.cluster.local`。Secret 文件以只读方式挂载；请根据镜像调整 UID/GID 访问权限。环境变量中只包含证书**路径**，不包含密钥内容或 bearer token。这些模板通过 TLS 端口 4318 使用 OTLP HTTP/protobuf。

#### Java 自动插桩

将固定版本的 agent 下载到应用构建中，并验证发布资源的校验和。2.31.1 JAR 大小为 25,107,554 字节，超过 Kubernetes ConfigMap 的 1 MiB 限制。请将它包含在镜像中或使用 Operator 注入；ConfigMap 并不是分发 agent 二进制文件的机制。


```bash
curl --fail --location --output opentelemetry-javaagent.jar \
  https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.31.1/opentelemetry-javaagent.jar
printf '%s  %s\n' \
  bbf83c151b6400709e2f225bdd07a04f839d9d13b8b93464241333fd25d3e3ba \
  opentelemetry-javaagent.jar | sha256sum --check -
```

```dockerfile
# Add to the application's existing Dockerfile; not a complete image build.
COPY opentelemetry-javaagent.jar /opt/otel/opentelemetry-javaagent.jar
```
将 agent 选项与任何现有的 `JAVA_TOOL_OPTIONS` 合并；不要丢弃应用 JVM 选项。Deployment selector 必须与 Pod 标签匹配。


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/order-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        - name: JAVA_TOOL_OPTIONS
          value: -javaagent:/opt/otel/opentelemetry-javaagent.jar
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
#### Python 自动插桩

对于 Flask 应用，请在其构建环境中安装匹配的包，并锁定解析后的应用依赖。其他框架需要安装对应的插桩包。本示例显式选择 HTTP exporter，而不是将 Python 默认使用的 HTTP 协议发送到 gRPC 端口 4317。


```bash
python -m pip install \
  opentelemetry-api==1.44.0 opentelemetry-sdk==1.44.0 \
  opentelemetry-distro==0.65b0 \
  opentelemetry-instrumentation-flask==0.65b0 \
  opentelemetry-exporter-otlp-proto-http==1.44.0
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/payment-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: payment-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
        command:
        - opentelemetry-instrument
        - python
        - app.py
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
#### Node.js 自动插桩


```bash
npm install --save-exact \
  @opentelemetry/api@1.9.1 @opentelemetry/resources@2.9.0 \
  @opentelemetry/sdk-node@0.220.0 \
  @opentelemetry/auto-instrumentations-node@0.78.0
# Commit package-lock.json and use npm ci for subsequent application builds.
```
将其保存为 `tracing.cjs`，并在应用/框架模块加载前加载。这是一个 CommonJS 示例；ESM 加载需要按照语言指南进行单独配置。SDK 会读取下方明确设置的 OTEL exporter/TLS 环境变量。对于以编程方式配置的 metric reader，当前配置使用 `metricReaders`，取代已弃用的单数选项。请在应用自身完成请求排空步骤后调用 `shutdownTelemetry()`。


```javascript
// Load before application/framework modules in a CommonJS application.
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { envDetector } = require('@opentelemetry/resources');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

const sdk = new NodeSDK({
  resourceDetectors: [envDetector],
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': { enabled: false },
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingRequestHook: (request) =>
          String(request.url || '').split('?')[0] === '/health',
      },
    }),
  ],
});

// OTEL_* variables configure exporters, protocol, TLS and metric interval.
sdk.start();

// Call after the application's own request-draining step on shutdown.
module.exports = { shutdownTelemetry: () => sdk.shutdown() };
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: notification-service
  template:
    metadata:
      labels:
        app: notification-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/notification-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: notification-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
        command:
        - node
        - --require
        - ./tracing.cjs
        - app.cjs
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
这些示例有意设置 `OTEL_LOGS_EXPORTER=none`。启用 log exporter 并不会读取应用的 stdout：请安装适当的日志桥接器/处理器或日志收集器，并先审查有效载荷暴露情况。`parentbased_always_on` 采样器仍会遵循未采样的父级。如果改用 10% 的头部采样，tail Collector 就无法找回已丢弃的 span。

### 手动插桩

复用 agent 或应用已初始化的 OpenTelemetry 实例/provider。如果没有 SDK provider，API 调用可能不会执行任何操作。以下业务工作流 span 的类型为 INTERNAL：经过插桩的 HTTP/数据库客户端会创建自己的 CLIENT span 并传播上下文。仅手动创建 CLIENT span 既不会发送请求，也不会注入 trace 上下文。

#### Java 手动插桩

应用需提供库存/支付回调。不会记录订单/客户 ID、金额、交易 ID 或原始异常消息。这些是应用操作示例，并非支付服务实现，也不是经过测试的 Spring 部署。


```java
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Scope;

public final class OrderTelemetry {
    private final Tracer tracer;

    public OrderTelemetry(OpenTelemetry telemetry) {
        this.tracer = telemetry.getTracer("example.order-workflow", "1.0.0");
    }

    public void processOrder(Runnable validateInventory, Runnable processPayment) {
        Span parent = tracer.spanBuilder("processOrder")
                .setSpanKind(SpanKind.INTERNAL).startSpan();
        try (Scope ignored = parent.makeCurrent()) {
            parent.addEvent("validation.started");
            child("checkInventory", validateInventory);
            child("processPayment", processPayment);
            parent.addEvent("processing.completed");
        } catch (RuntimeException error) {
            parent.setStatus(StatusCode.ERROR);
            parent.setAttribute("error.type", error.getClass().getName());
            throw error;
        } finally {
            parent.end();
        }
    }

    private void child(String name, Runnable operation) {
        Span span = tracer.spanBuilder(name).setSpanKind(SpanKind.INTERNAL).startSpan();
        try (Scope ignored = span.makeCurrent()) {
            operation.run();
        } catch (RuntimeException error) {
            span.setStatus(StatusCode.ERROR);
            span.setAttribute("error.type", error.getClass().getName());
            throw error;
        } finally {
            span.end();
        }
    }
}
```
#### Python 手动插桩

这个同步装饰器会保留返回值和错误，并在结束时关闭嵌套 span。它只记录错误类型，避免重复记录原始异常事件。异步函数需要使用支持异步的封装器。请提供自己的参数化数据库查找、验证、持久化和事件发布回调；本地验证使用了合成回调和内存 exporter。


```python
"""Manual spans for synchronous application callbacks; no database is created."""
from functools import wraps
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

# Reuse the SDK provider initialized by auto-instrumentation or the application.
tracer = trace.get_tracer("example.user-workflow", "1.0.0")

@contextmanager
def operation(name):
    with tracer.start_as_current_span(
        name, kind=SpanKind.INTERNAL,
        record_exception=False, set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except Exception as error:
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", type(error).__name__)
            raise

def traced(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with operation(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate

@traced("get_user")
def get_user(user_id, lookup):
    # lookup is supplied by the application, with parameterized queries.
    # The ID and SQL text are not added to telemetry.
    with operation("lookup_user"):
        result = lookup(user_id)
    trace.get_current_span().set_attribute("app.user.found", result is not None)
    return result

@traced("create_user")
def create_user(user_data, validate, save, publish):
    # These callbacks are the application's own implementations.
    with operation("validate_user_data"):
        validate(user_data)
    with operation("save_user"):
        result = save(user_data)
    with operation("publish_user_event"):
        publish(result)
    return result
```
对于实际的数据库/消息插桩，请遵循已实现的约定版本，例如 `db.system.name`、`db.operation.name` 和 `messaging.destination.name`。不要将用户 ID 复制到 SQL 遥测字符串中，也不要将原始查询用作指标标签。上述业务回调并不能证明 PostgreSQL 或 Kafka 确实执行过。

## OTEL Collector

### 架构


```mermaid
flowchart TD
    R["OTLP receiver / mTLS"]
    R -->|traces| P["Trace preprocessing: memory, resource, redaction, health filter"]
    P --> S["tail_sampling"]
    S --> B["batch"]
    B --> T["Tempo / OTLP gRPC mTLS"]
    P --> C["span_metrics before tail sampling"]
    C --> M["Metrics: memory, resource, batch"]
    R -->|metrics| M
    M --> W["Prometheus remote write / HTTPS"]
    R -->|logs| L["Logs: memory, resource, attribute redaction, batch"]
    L --> K["Loki native OTLP HTTP / mTLS"]
```

以下配置中的信号路由。Trace 预处理框概述了两个独立 trace 流水线中的等效处理。Span metrics 在 tail sampling 之前分流；传入的 metrics 和 logs 则使用各自的流水线。

### Collector 配置

保存为 `otel-collector-config.yaml`。这是用于实验环境的单个有状态采样/聚合实例，并不保证高可用或容量充足。单独的 trace 流水线会在 **tail sampling 之前**生成 metrics。经过头部采样或过滤的 span 仍不会出现在这些 metrics 中。这些计数器统计的是观测到的 span，而非唯一终端用户请求；请为请求 SLI 选择合适的 span kind 和有界维度。0.160.0 中 span-metric 累积计数器最初会导出零值；请评估后续刷新结果，再判断第一个值是否意味着没有流量。

准备启用了 OTLP 的 Tempo、兼容 Prometheus 的 remote-write 接收端，以及 Loki 原生 OTLP 接收端，并配置由运维方提供的 TLS/身份验证网关。下方的网关名称并非本指南创建的 Service。Prometheus 需要启用 remote-write 接收端（直接使用 Prometheus 时可设置 `--web.enable-remote-write-receiver`）。Loki exporter 的基础 URL 以 `/otlp` 结尾；HTTP exporter 会追加 `/v1/logs`。请根据需要配置 Loki 结构化元数据和可信租户映射；租户 header 并不等同于身份验证。

环境变量指向现有证书和端点。所有已配置的 receiver 均使用双向 TLS；未启用允许任意来源的浏览器 CORS，也未启用公开的 profiling 端点。此处列出的属性删除操作只是有限的控制措施，并不能完整清除日志正文、span 事件、资源属性或任意有效载荷中的敏感信息。还应在 SDK 端尽量减少数据收集。


```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 16
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 384
    spike_limit_mib: 96
  resource/cluster:
    attributes:
      - key: k8s.cluster.name
        value: ${env:K8S_CLUSTER_NAME}
        action: insert
  attributes/redact:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: user.email
        action: delete
      - key: user.id
        action: delete
      - key: customer.id
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  filter/health:
    error_mode: propagate
    traces:
      span:
        - 'attributes["http.route"] == "/health"'
        - 'attributes["http.route"] == "/ready"'
        - 'attributes["http.route"] == "/metrics"'
  tail_sampling:
    decision_wait: 10s
    num_traces: 10000
    expected_new_traces_per_sec: 100
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 1000
      - name: selected-services
        type: string_attribute
        string_attribute:
          key: service.name
          values: [payment-service, order-service]
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024

connectors:
  span_metrics:
    histogram:
      unit: s
      explicit:
        buckets: [5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2s, 5s]
    dimensions:
      - name: http.request.method
      - name: http.response.status_code
    aggregation_cardinality_limit: 1000
    metrics_flush_interval: 15s

exporters:
  otlp_grpc/tempo:
    endpoint: ${env:TEMPO_OTLP_GRPC_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
  prometheus_remote_write:
    endpoint: ${env:PROMETHEUS_REMOTE_WRITE_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
  otlp_http/loki:
    endpoint: ${env:LOKI_OTLP_HTTP_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, filter/health, tail_sampling, batch]
      exporters: [otlp_grpc/tempo]
    traces/span-metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, filter/health]
      exporters: [span_metrics]
    metrics:
      receivers: [otlp, span_metrics]
      processors: [memory_limiter, resource/cluster, batch]
      exporters: [prometheus_remote_write]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, batch]
      exporters: [otlp_http/loki]
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 127.0.0.1
                port: 8888
```
正向采样策略之间是 OR 条件，而不是按顺序排列的优先级阶梯。即使不满足基线概率，选定服务的 trace 仍可单独保留。延迟判断使用严格的 `>1000 ms` 比较。基于计时器的决策无法证明 trace 已完成；健康检查过滤器会有意移除匹配的 span，即使这些 span 存在错误也是如此。过滤单个 span 可能导致 trace 不完整。

硬内存限制为 384 MiB，软限制为 288 MiB，在模板的 512 MiB 容器限制下留有余量。仍需测量拒绝、重试、队列和突发流量。此处的批处理、trace 和基数限制只是演示设置，并非基准测试结果。

### 单实例工作负载和配置

准备 `otel` 命名空间以及 `otel-ingest-tls` / `otel-backend-tls` Secret，并包含 `tls.crt`、`tls.key`、`ca.crt`。使用与相应 Service/网关名称匹配的证书 SAN、合适的信任包，以及服务端/客户端用途正确的证书。请调整对 UID/GID 10001 的文件访问权限。ConfigMap 包含文本配置，不包含私钥。对于此单实例采样器，`Recreate` 可避免正常滚动更新期间出现重叠，但代价是停机；它无法在重启期间保留内存中的 trace。


```bash
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
kubectl --context "$KUBE_CONTEXT" -n otel create configmap otel-collector-config \
  --from-file=otel-collector-config.yaml --dry-run=client -o yaml > otel-collector-configmap.yaml
# Inspect the namespace, Secrets, endpoints and workloads before any real apply.
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-collector
  namespace: otel
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: otel
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
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-collector-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        - name: K8S_CLUSTER_NAME
          value: REPLACE_WITH_CLUSTER_NAME
        - name: TEMPO_OTLP_GRPC_ENDPOINT
          value: tempo-gateway.tempo.svc.cluster.local:4317
        - name: PROMETHEUS_REMOTE_WRITE_ENDPOINT
          value: https://prometheus-gateway.monitoring.svc.cluster.local/api/v1/write
        - name: LOKI_OTLP_HTTP_ENDPOINT
          value: https://loki-gateway.loki.svc.cluster.local/otlp
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
  replicas: 1
  strategy:
    type: Recreate
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-collector
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
```
### 可选的收集与丰富处理

| 要求 | 所需的独立配置 |
|---|---|
| 旧版 Jaeger/Zipkin 客户端 | 其 receiver 组件仍可用；只启用所需协议/端口，并在流水线中匹配 receiver ID。通过 OTLP 导出到 Jaeger，不要使用已移除的 Jaeger exporter。 |
| Collector 自身的指标 | `service.telemetry.metrics.readers` 用于配置当前的 Prometheus reader。旧的 `address` 字段已移除。通过经过专门设计的监控路径抓取 loopback 端点。 |
| Kubernetes 集群指标 | 仅运行一个处于活动状态的 `k8s_cluster` receiver，或配置其 leader-elector 扩展。提供 API 凭据和经过审查的 RBAC，然后将其接入 metrics 流水线。上述默认的无 token 工作负载并不具备这些前提条件。 |
| 节点/容器日志或主机指标 | 添加相应的 receiver、挂载和权限；仅使用 DaemonSet 并不会收集这些数据。 |
| EC2/EKS 资源检测 | 有意配置所需的 detector 及其元数据/API 访问；不要用 Collector 主机身份替换工作负载身份。 |
| 基于 Span 派生的指标 | 使用 `span_metrics` connector，并明确指定持续时间单位和有界维度。旧的 spanmetrics processor 已移除。 |

请参阅[Collector 指南](../logging/05-collectors.md)和 [Kubernetes 集群 receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/receiver/k8sclusterreceiver)。不要仅仅声明一个未使用的 receiver/processor，就认为它已处于启用状态。

## EKS 部署模式

以下是不同的部署模式，并非要不加区分地全部应用的一套堆栈。无状态 relay 会将三种信号全部转发到上述单一采样层。不要在任意负载均衡的节点/sidecar/HPA 层中执行 tail sampling 和 span 聚合。多个采样实例需要基于 trace ID 的路由，并需要针对端点变更、处理中 trace、重启和存储制定方案；仅有 Service 或 HPA 无法提供这些能力。

保存为 `otel-relay-config.yaml`，并按相同的客户端 ConfigMap 生成流程创建 `otel-relay-config`。`OTEL_UPSTREAM_ENDPOINT` 和客户端证书指向单独准备的上游 Collector。relay 不会保存采样决策状态；但其内存中的批处理/导出队列仍有故障和关闭方面的限制。


```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 16
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 384
    spike_limit_mib: 96
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024
exporters:
  otlp_grpc/upstream:
    endpoint: ${env:OTEL_UPSTREAM_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health
service:
  extensions:
  - health_check
  pipelines:
    traces:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    metrics:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
      - pull:
          exporter:
            prometheus:
              host: 127.0.0.1
              port: 8888
```
### DaemonSet 模式

DaemonSet 会在符合条件的 Linux 节点上运行，不会运行在 EKS Fargate 上。请为获准的节点配置 selector/toleration；此处没有宽泛的 toleration，也没有预留 hostPort。`internalTrafficPolicy: Local` 仅会将此 Service 的流量路由到调用方所在节点上的就绪端点；如果不存在此类端点，流量就会被丢弃。它不能作为 Fargate 客户端的备用机制。应用必须明确将遥测数据发送到此端点。


```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-agent
  namespace: otel
spec:
  selector:
    matchLabels:
      app: otel-agent
  template:
    metadata:
      labels:
        app: otel-agent
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-relay-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-relay-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
---
apiVersion: v1
kind: Service
metadata:
  name: otel-agent
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-agent
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
  internalTrafficPolicy: Local
```
### Sidecar 模式

使用单独的 `otel-sidecar-config` ConfigMap，其中包含以下配置。只有同一 Pod 会使用其 loopback 明文 OTLP receiver；上游流量使用双向 TLS。此配置适用于硬限制为 192 MiB、软限制为 144 MiB 的 256 MiB sidecar。应用镜像必须包含所选 SDK/agent；仅设置端点变量本身不会添加插桩。此 Kubernetes 1.35 Schema 示例使用原生 sidecar（`initContainers` 中设置 `restartPolicy: Always`，该功能于 1.33 达到 GA）。它的启动探针会先于应用启动；正常关闭时，会先停止应用容器，再停止 sidecar。后端交付和突发故障恢复仍需单独检查。


```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 192
    spike_limit_mib: 48
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024
exporters:
  otlp_grpc/upstream:
    endpoint: ${env:OTEL_UPSTREAM_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health
service:
  extensions:
  - health_check
  pipelines:
    traces:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    metrics:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
      - pull:
          exporter:
            prometheus:
              host: 127.0.0.1
              port: 8888
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-with-sidecar
  namespace: otel
spec:
  selector:
    matchLabels:
      app: order-with-sidecar
  template:
    metadata:
      labels:
        app: order-with-sidecar
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: registry.example.com/order-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-service
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: http://127.0.0.1:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
      volumes:
      - name: config
        configMap:
          name: otel-sidecar-config
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
      initContainers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-sidecar-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 192MiB
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 256Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
        restartPolicy: Always
        startupProbe:
          httpGet:
            path: /health
            port: 13133
          periodSeconds: 2
          failureThreshold: 30
  replicas: 1
```
### 网关模式

此 HPA 扩展的是无状态 **relay**，而非有状态采样器。使用 Metrics Server 并具备适当的 requests/容量是前提条件。三个副本、优先反亲和性以及 3–10 的范围都是示例选择，并不能证明具备高可用性或足够的吞吐量。Deployment 方式的 Collector 可用于 Fargate 或 Auto Mode，但应先检查其执行、存储、网络和 receiver 要求。


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-relay
  namespace: otel
spec:
  selector:
    matchLabels:
      app: otel-relay
  template:
    metadata:
      labels:
        app: otel-relay
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-relay-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-relay-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: otel-relay
              topologyKey: kubernetes.io/hostname
  replicas: 3
---
apiVersion: v1
kind: Service
metadata:
  name: otel-relay
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-relay
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: otel-relay
  namespace: otel
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: otel-relay
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Kubernetes Operator

Operator 0.158.0 有单独的兼容性矩阵。其发布清单假定已准备好 cert-manager v1；请使用 [cert-manager 指南](../../security/10-cert-manager.md)中仍受维护且兼容的版本，而不要安装已过时的 1.13.3 示例。升级现有的、由所有者管理的安装之前，请审查 0.158.0 中的 CRD 变更和默认网络策略。

### 安装 Operator


```bash
curl --fail --location --output opentelemetry-operator.yaml \
  https://github.com/open-telemetry/opentelemetry-operator/releases/download/v0.158.0/opentelemetry-operator.yaml
printf '%s  %s\n' \
  3c258efb3d64834a857ce4ed5256af2883dc9c77a300eee465df833ab2354c8e \
  opentelemetry-operator.yaml | sha256sum --check -
# After prerequisites and ownership/upgrade review; this changes the cluster:
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
kubectl --context "$KUBE_CONTEXT" apply -f opentelemetry-operator.yaml
```
### Instrumentation CR

资源和应用示例都位于 `ecommerce`。固定版本的 Operator 会提供其对应版本的默认插桩镜像；请检查注入的镜像，不要将它们全部替换为 `latest`。它的 Java/Python 默认版本与上方直接安装的版本不同。每个进程只使用一种插桩方式。TLS Secret 挂载仍由应用负责。


```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: otel-instrumentation
  namespace: ecommerce
spec:
  exporter:
    endpoint: https://otel-collector.otel.svc.cluster.local:4318
  propagators:
  - tracecontext
  - baggage
  sampler:
    type: parentbased_always_on
  env:
  - name: OTEL_RESOURCE_ATTRIBUTES
    value: service.namespace=ecommerce,deployment.environment.name=demo
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: http/protobuf
  - name: OTEL_EXPORTER_OTLP_CERTIFICATE
    value: /var/run/otel-client/ca.crt
  - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
    value: /var/run/otel-client/tls.crt
  - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
    value: /var/run/otel-client/tls.key
  - name: OTEL_TRACES_EXPORTER
    value: otlp
  - name: OTEL_METRICS_EXPORTER
    value: otlp
  - name: OTEL_LOGS_EXPORTER
    value: none
  - name: OTEL_METRIC_EXPORT_INTERVAL
    value: '60000'
```
此处选择了 W3C Trace Context 和 baggage。仅当语言的 propagator 包和对端都支持 B3 时，才将其作为可选的互操作方案。不要在 baggage 中放入凭据或个人数据；传播可能跨越 Service 和信任边界。

### 自动插桩注入

注解应放在 Pod 模板上，而不只是 Deployment 元数据中。`otel-instrumentation` 会在 Pod 所属命名空间中选择具名资源；也可以使用 `namespace/name` 显式选择其他命名空间。也可以使用命名空间级注解，但不要不加区分地为每个 Pod 启用 Java、Python 和 Node.js。注入发生在新 Pod 获准创建时，不会追溯应用到正在运行的 Pod。


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-injected
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-injected
  template:
    metadata:
      labels:
        app: order-injected
      annotations:
        instrumentation.opentelemetry.io/inject-java: otel-instrumentation
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/order-injected:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-injected
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
Java、Python、Node.js、.NET、Go、Apache HTTPD 和 Nginx 各有不同的前置要求。在此版本中，Go 自动插桩需要目标可执行文件的路径，并会注入特权 UID-0 组件；它并不是适用于通用 Restricted-PSS/Fargate 场景的配置方案。请核实 Operator 功能设置和各语言指南。如果没有匹配的协议配置，不要将 Python/.NET/Go 的 HTTP 默认配置指向 gRPC 端点。

## 多后端配置

将此片段合并到经过审查的基础配置中；它不能独立运行。每个后端都需要自己的端点、信任设置和授权配置。AWS X-Ray 使用已配置的 Region 和工作负载身份；具体 IAM 信任关系/权限请参阅 [X-Ray 指南](./02-xray.md)。禁用属性索引并不等于清除敏感信息。Datadog 的 api 对象来自由 Secret 管理的 api.yaml，其中包含 key（带引号的字符串）和 site。请将该 Secret 以只读方式挂载到工作负载中；基础工作负载并未挂载它。环境变量中不包含任何密钥。本次审计未执行任何 AWS/Datadog/Jaeger 服务调用。


```yaml
exporters:
  awsxray:
    region: ap-northeast-2
    index_all_attributes: false
    telemetry:
      enabled: false
  datadog:
    api: ${file:/var/run/secrets/datadog/api.yaml}
  otlp_grpc/jaeger:
    endpoint: ${env:JAEGER_OTLP_GRPC_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
service:
  pipelines:
    traces:
      exporters:
      - otlp_grpc/tempo
      - awsxray
      - datadog
      - otlp_grpc/jaeger
```
扇出并不能保证各后端原子交付，也不能保证各后端的保留策略相同。

### 2026 年 7 月更新：观测 AI Agent 流量的网络边界

[7 月 8 日的 CNCF 文章](https://www.cncf.io/blog/2026/07/08/network-boundary-for-ai-agents-using-nginx-and-opentelemetry/)介绍了一个使用 NGINX 和 OTel 的单节点原型。其边界依赖于阻止其他出口路径的网络规则，而不仅仅是设置代理变量。Span 描述的是配置的代理可见的流量；TLS 处理、采样、Collector 保留策略和代理安全仍然很重要。这只是网络控制的一层，并不能证明 agent 的决策正确或安全。

### 2026 年 8 月更新：将慢 SQL 查询提炼为可靠性指标

[8 月 21 日的 CNCF 文章](https://www.cncf.io/blog/2026/08/21/how-to-turn-slow-queries-into-actionable-reliability-metrics-with-opentelemetry/)及其[实验](https://github.com/causely-oss/slow-query-lab)对比了查询耗时、按流量加权的影响，以及基于 span 的指标与异常基线。请将文章中的历史示例视为示例，而非你集群的容量测量值。文章本身也提醒了原始 SQL 被用作指标标签、敏感参数、基数和基线预热等问题。在采用实验配置之前，请对维度进行清理和限界；延迟异常是症状，并不能证明根本原因。

### 2026 年 10 月更新：将软件碳强度（SCI）作为 OTel 信号

在[10 月 15 日的 CNCF 文章](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/)中，Kepler 维护者兼 CNCF 大使 Diana Todea 以其在 Observability Summit Europe 2026 上的主题演讲为基础，提出将 Green Software Foundation 的软件碳强度（SCI）标准视为 OpenTelemetry 语义约定，把碳排放与工作负载和 Service 关联起来，作为一种可观测信号。这是一项方向性提案，目前仍在标准化讨论中，并非特定 OTel 版本中已发布的功能，也不是已完成的语义约定；制定采用计划前请关注上游进展。

### 2026 年 10 月更新：基于 OTel 数据流重建事件检测

在[9 月 30 日的 CNCF 文章](https://www.cncf.io/blog/2026/09/30/from-40-seconds-to-under-10-rebuilding-incident-detection-on-opentelemetry-apache-kafka-and-apache-flink-on-kubernetes/)中，Atlassian 介绍了其历时 18 个月，基于 Kubernetes 上的 OpenTelemetry、Apache Kafka 和 Apache Flink 重建自动化事件创建平台的过程，将事件到指标的延迟从 40 多秒缩短至不到 10 秒。正如文章本身所述，范围内召回率从约 60% 上升到 86%，但在某个糟糕的月份又回落到 64%，且精确率仍低于目标。应将这些数字视为该组织的测量结果，而不是该架构所保证的结果；文章最有价值之处在于对权衡的讨论，例如在共享队列中隔离嘈杂邻居和控制成本。

## 最佳实践

### 1. 统一资源属性

| 属性 | 示例 / 来源 |
|---|---|
| `service.name`、`service.version`、`service.namespace` | `order-service`、`1.2.3`、`ecommerce`；应用配置 |
| `deployment.environment.name` | `demo`；用于取代已弃用的 `deployment.environment` |
| `cloud.provider`、`cloud.region`、`cloud.availability_zone` | 经过验证的部署元数据，而非根据 Collector 主机猜测 |
| `k8s.cluster.name`、`k8s.namespace.name`、`k8s.pod.name`、`k8s.deployment.name` | 正确配置的 Kubernetes 丰富处理或工作负载元数据 |

这是属性清单，并非 Collector processor YAML。Resource 用于标识数据生成方。避免将每个资源属性都复制到指标标签中；Pod 名称、用户 ID 和原始查询文本可能导致高基数。Profiles 是另一种仍在发展的信号；本指南重点介绍 traces、metrics 和 logs，并不声称所有 SDK 都具有统一的稳定性。

### 2. 采样策略

对于一个高级示例（错误、延迟 >2 秒、关键服务的 50% 条件以及 5% 基线），请将每条正向规则视为 OR 条件，而不是优先匹配顺序或预留配额。其他规则也可能保留某个 trace。如果需要互斥分类或 span 速率预算，应明确设计并测试该策略。头部采样、已丢弃的 span、分片变更和迟到数据仍是需要分别处理的限制。


```yaml
# Replace the base policies list; positive rules are OR conditions, not priorities.
processors:
  tail_sampling:
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 2000
    - name: critical-services
      type: and
      and:
        and_sub_policy:
        - name: service-name
          type: string_attribute
          string_attribute:
            key: service.name
            values:
            - payment-service
            - order-service
        - name: probabilistic
          type: probabilistic
          probabilistic:
            sampling_percentage: 50
    - name: default
      type: probabilistic
      probabilistic:
        sampling_percentage: 5
```
### 3. 安全注意事项

如果没有 `client_ca_file`，仅配置服务端 TLS 并不等同于要求客户端证书。请保护通信的两个方向、验证证书名称和生命周期，并限制对 Service/网络/后端的访问。sidecar 示例中的同 Pod loopback 明文通信属于另一个信任边界。浏览器遥测需要单独设计来源、身份验证和速率限制，而不是使用允许任意来源的 CORS。

attributes processor 的 `hash` 操作使用 SHA-1。对可预测的 ID 或 SQL 文本进行哈希并不能实现匿名化；仍可能通过字典恢复数据，也仍可进行关联。应优先避免收集敏感值，然后在导出前显式删除已识别的字段。请分别审查日志正文、span 事件和资源属性。详细的 debug exporter 或 profiling 端点可能暴露数据，应仅作为临时、受控的诊断手段。

### 验证与限制

本地验证使用了实际的 Collector 0.160.0，并通过合成 OTLP 流量和 mTLS loopback 端点进行，包括 trace/log 处理和 tail sampling 前的 span metrics。remote-write 检查只验证了向测试接收端通过 HTTPS 交付数据，并非实时 Prometheus 接收结果。Python 手动 span 使用 SDK 1.44.0 和内存 exporter。已检查 Kubernetes/Instrumentation Schema 和 Node.js 语法；未执行 Java/Node 应用启动、零代码注入、真实后端产品、EKS、IAM 或自动扩缩容。

### 官方参考资料

- [Collector 0.160.0 组件](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.160.0/distributions/otelcol-contrib/manifest.yaml)
- [Operator 0.158.0 兼容性](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/getting-started/compatibility.md)
- [Operator 自动插桩](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/auto-instrumentation/README.md)
- [Java agent 2.31.1](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/tag/v2.31.1)
- [OTLP exporter 配置](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Collector 扩缩容](https://opentelemetry.io/docs/collector/scaling/)
- [Tail sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Span metrics connector](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/connector/spanmetricsconnector)
- [Memory limiter](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/memorylimiterprocessor)
- [Loki 原生 OTLP](https://grafana.com/docs/loki/latest/send-data/otel/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Kubernetes 原生 sidecar](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [EKS Kubernetes 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [OpenTracing CNCF 里程碑](https://www.cncf.io/projects/opentracing/)
- [OpenCensus Go 仓库](https://github.com/census-instrumentation/opencensus-go)

## 测验

通过 [OpenTelemetry 测验](../../quizzes/observability/tracing/03-opentelemetry-quiz.md)检验你的知识。
