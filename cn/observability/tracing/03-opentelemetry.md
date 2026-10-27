# OpenTelemetry

> **审查基线**：Collector Contrib 0.160.0；Operator 0.158.0；下文列出的语言版本
> **最后更新**：2026年10月26日

## 简介

OpenTelemetry（OTel）是面向云原生软件的可观测性框架。它提供与供应商无关的标准，用于生成、收集和管理三种信号：追踪、指标和日志。CNCF 于2026年7月24日发表的回顾文章称，其贡献速度仅次于 Kubernetes。项目成熟度与各 SDK/组件的稳定性是两回事。

### 2026年7月更新：CNCF 毕业

OpenTelemetry 于 **2026年5月** 达到 CNCF **毕业**级别；7月24日的文章是一篇回顾。这是基金会的最高成熟度级别，Kubernetes 和 Prometheus 等项目也已达到这一水平。毕业意味着该项目的治理、安全实践和采用情况已通过生产使用方面的审核。回顾文章讨论了 GenAI 语义约定、浏览器/移动端可观测性、Schema 治理和发布工具。背景和路线图请参阅 CNCF 博客文章 ["OpenTelemetry has graduated… Now what?"](https://www.cncf.io/blog/2026/07/24/opentelemetry-has-graduated-now-what/)。

## 什么是 OpenTelemetry？

OpenTelemetry 源自 OpenTracing 和 OpenCensus 项目的合并：

![历史里程碑包括 OpenTracing 于2016年加入 CNCF、OpenCensus Go 仓库于2017年建立，以及 OpenTelemetry 于2019年合并；之后依次推出规范、SDK、Collector 和协议。](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-0.html)

## 核心概念

### 三种信号

本章重点介绍追踪、指标和日志。性能剖析是另一种不断发展的信号；不同实现的支持情况和稳定性各不相同。追踪/日志 ID 和指标示例值需要相应的检测和后端配置。

| 信号 | 描述 | 使用场景 |
|--------|-------------|-----------|
| **追踪** | 分布式请求追踪 | 延迟分析、依赖关系映射 |
| **指标** | 数值测量 | 资源使用情况、SLI/SLO |
| **日志** | 事件记录 | 调试、审计 |

### 核心组件

![应用代码通过 OTel API 和 SDK 发出遥测数据，进入接收-处理-导出流水线，再分发到五个可观测性后端：Tempo、Prometheus、Loki、X-Ray 和 Datadog。](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-2.html)

该图按信号列出了后端选项。只有已配置的导出器才会启用；下面的基础示例不会自动启用所有供应商。

## OpenTelemetry SDK

Collector、Operator、Java agent 和各语言 SDK 使用各自独立的版本号。这些 Linux 工作负载模板已根据 Kubernetes 1.35 Schema 检查：应用镜像、命名空间、证书和目标 Service 必须由其所有者准备。更广泛的 Operator 兼容矩阵不会免除配方特定的要求，例如原生 sidecar。本地检查无法证明 EKS 上已部署应用可正常运行。

| 组件 | 基线和范围 |
|---|---|
| 独立 Collector Contrib | 0.160.0；使用其实际二进制文件检查组件和 Schema |
| Operator | 0.158.0；其兼容性表列出了 Kubernetes 1.25–1.36 和 cert-manager v1 |
| Java agent | 2.31.1，目标 SDK 版本为 1.65.0；与 Operator 的默认 Java 镜像版本不同 |
| Python | SDK/exporter 1.44.0 和 instrumentation/distro 0.65b0；Python ≥3.10 |
| Node.js CommonJS 示例 | SDK-node 0.220.0、auto-instrumentations-node 0.78.0、resources 2.9.0、API 1.9.1 |

Operator 默认使用 Collector 0.158.0。下面的独立 0.160.0 工作负载并非由 Operator 管理的 Collector 升级。请检查与受支持 EKS 版本的交集；最新 Kubernetes 版本不一定包含在 Operator 兼容矩阵中。

### 自动检测

截至2026年10月12日，EKS 标准支持版本包括 1.34–1.37。1.35 Schema 基线在此列表和 Operator 矩阵范围之内；但这仍不能取代对实际平台/附加组件的验收检查。

零代码检测可挂接受支持的库；它不会发现任意业务操作。对于一个进程，应选择直接准备 agent/启动器，或由 Operator 注入。不要在已配置的 provider 上再次初始化 SDK。以下应用镜像是占位示例，请替换为自己的构建产物，包括启动命令和依赖项。

准备 `ecommerce` 命名空间，并在其中创建 `otel-client-tls` Secret，包含 `ca.crt`、`tls.crt` 和 `tls.key`。Collector 必须接受客户端证书，且其证书必须匹配 `otel-collector.otel.svc.cluster.local`。Secret 文件以只读方式挂载；请根据镜像调整 UID/GID 访问权限。环境变量中只包含证书**路径**，不包含密钥内容或 bearer token。这些模板通过 TLS 端口 4318 使用 OTLP HTTP/protobuf。

#### Java 自动检测

在应用构建中下载固定版本的 agent，并验证发布资源校验和。2.31.1 JAR 大小为 25,107,554 字节，超过 Kubernetes ConfigMap 的 1 MiB 限制。请将其包含在镜像中，或使用 Operator 注入；ConfigMap 不是分发 agent 二进制文件的机制。

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

将 agent 选项与任何现有的 `JAVA_TOOL_OPTIONS` 合并；不要丢弃应用的 JVM 选项。Deployment 选择器和 Pod 标签必须匹配。

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

#### Python 自动检测

对于 Flask 应用，请在其构建环境中安装匹配的软件包，并锁定解析后的应用依赖项。其他框架需要安装相应的检测软件包。此示例显式选择 HTTP exporter，而不是让 Python 的 HTTP 默认配置将数据发送到 gRPC 端口 4317。

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

#### Node.js 自动检测

```bash
npm install --save-exact \
  @opentelemetry/api@1.9.1 @opentelemetry/resources@2.9.0 \
  @opentelemetry/sdk-node@0.220.0 \
  @opentelemetry/auto-instrumentations-node@0.78.0
# Commit package-lock.json and use npm ci for subsequent application builds.
```

将其保存为 `tracing.cjs`，并在应用/框架模块之前加载。这是 CommonJS 示例；ESM 加载需要按照语言指南单独设置。SDK 会读取下面明确设置的 OTEL exporter/TLS 环境变量。对于通过代码配置的指标读取器，当前配置使用 `metricReaders`，取代已弃用的单数选项。请在应用自身的请求排空步骤之后集成 `shutdownTelemetry()`。

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

这些示例有意设置 `OTEL_LOGS_EXPORTER=none`。启用日志 exporter 并不会采集应用标准输出：请安装相应的日志桥接程序/处理器或日志采集器，并先检查有效载荷暴露情况。`parentbased_always_on` 采样器仍会遵循未采样的父级。如果改用 10% 的头部采样，尾部 Collector 就无法恢复已丢弃的 Span。

### 手动检测

重用 agent 或应用已初始化的 OpenTelemetry 实例/provider。如果没有 SDK provider，API 调用可能会成为空操作。这些业务工作流 Span 的类型为 INTERNAL：经过检测的 HTTP/数据库客户端会创建自己的 CLIENT Span 并传播上下文。单独手动创建 CLIENT Span 既不会发送请求，也不会注入追踪上下文。

#### Java 手动检测

应用负责提供库存/支付回调。不会记录订单/客户 ID、金额、交易 ID 或原始异常消息。这些是应用操作，并非支付服务实现，也不是经过测试的 Spring 部署。

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

#### Python 手动检测

同步装饰器会保留结果和错误，同时结束嵌套 Span。它只记录错误类型，避免重复记录原始异常事件。异步函数需要支持异步的包装器。请提供自己的参数化数据库查询、验证、持久化和事件发布回调；本地验证使用了合成回调和内存 exporter。

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

对于实际的数据库/消息检测，请遵循已实现的约定版本，例如 `db.system.name`、`db.operation.name` 和 `messaging.destination.name`。不要将用户 ID 写入 SQL 遥测字符串，也不要将原始查询用作指标标签。上述业务回调不能证明 PostgreSQL 或 Kafka 已执行。

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

下方配置的信号路由。追踪预处理框概括了两个独立追踪流水线中的等效处理。Span 指标在尾部采样之前分支；输入指标和日志使用各自的流水线。

### Collector 配置

保存为 `otel-collector-config.yaml`。这是实验环境中一个启用了状态化采样/聚合的实例，不代表高可用或容量保证。独立的追踪流水线会在**尾部采样之前**派生指标。头部采样或经过过滤的 Span 仍不会出现在这些指标中。这些计数器统计的是观测到的 Span，而不是唯一终端用户请求；请为请求 SLI 选择合适的 Span 类型和有限的维度。0.160.0 中，累积型 Span 指标计数器最初导出为零；在将第一个值解读为没有流量之前，请评估后续刷新结果。

准备好启用了 OTLP 的 Tempo、兼容 Prometheus 的 remote-write 接收器，以及 Loki 的原生 OTLP 接收功能，并由运维人员提供 TLS/身份验证网关。下方示例中的网关名称并非本指南创建的 Service。Prometheus 需要启用 remote-write 接收器（如果使用 Prometheus 本身，则需设置 `--web.enable-remote-write-receiver`）。Loki exporter 的基础端点以 `/otlp` 结尾；HTTP exporter 会附加 `/v1/logs`。请根据需要配置 Loki 结构化元数据和受信任的租户映射；租户标头不等于身份验证。

环境变量用于标识现有证书和端点。所有已配置的接收器都使用双向 TLS；未启用允许所有来源的浏览器 CORS，也未启用公开的性能剖析端点。指定的属性删除操作只是有限的控制措施，并未完整遮蔽日志正文、Span 事件、资源属性或任意有效载荷。还应在 SDK 处尽量减少数据。

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

正向采样策略之间是 OR 条件，而非按顺序排列的优先级阶梯。即使不满足基线概率，选定的服务也可以被保留。延迟采用严格的 `>1000 ms` 比较。基于计时器的决策不能证明追踪已完成；健康检查过滤器会有意移除匹配的 Span，即使它们带有错误也不例外。过滤单个 Span 可能会留下不完整的追踪。

硬内存限制为 384 MiB，软限制为 288 MiB，在模板的 512 MiB 容器限制内留有余量。拒绝、重试、队列和突发流量仍需测量。这里的批处理/追踪/基数限制是演示设置，不是基准测试结果。

### 单实例工作负载和配置

准备 `otel` 命名空间以及 `otel-ingest-tls` / `otel-backend-tls` Secrets，其中包含 `tls.crt`、`tls.key`、`ca.crt`。证书 SAN 必须与相应的 Service/网关名称匹配，并使用适当的信任包和具备正确服务器端/客户端用途的证书。请为 UID/GID 10001 调整文件访问权限。ConfigMap 包含文本配置，不包含私钥。`Recreate` 可避免此单实例采样器在常规滚动更新期间出现重叠，但代价是停机；它不会在重启时保留内存中的追踪。

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

### 可选的采集与丰富处理

| 需求 | 需要单独配置 |
|---|---|
| 旧版 Jaeger/Zipkin 客户端 | 它们的接收器组件仍可用；仅启用所需协议/端口，并在流水线中匹配接收器 ID。通过 OTLP 导出到 Jaeger，而不要使用已移除的 Jaeger exporter。 |
| Collector 自身指标 | `service.telemetry.metrics.readers` 用于配置当前的 Prometheus reader。旧的 `address` 字段已移除。通过经过专门设计的监控路径抓取环回端点。 |
| Kubernetes 集群指标 | 运行一个活动的 `k8s_cluster` 接收器，或配置其 leader-elector 扩展。提供 API 凭证和经过审核的 RBAC，然后将其连接到指标流水线。上方默认不使用 token 的工作负载不具备这些前提条件。 |
| 节点/容器日志或主机指标 | 添加相应的接收器、挂载和权限；仅部署 DaemonSet 并不会自动采集这些数据。 |
| EC2/EKS 资源检测 | 配置所需的检测器及其元数据/API 访问权限；不要用 Collector 主机身份替换工作负载身份。 |
| 基于 Span 派生指标 | 使用 `span_metrics` connector，并显式指定时长单位和有限的维度。旧版 spanmetrics processor 已移除。 |

请参阅[Collector 指南](../logging/05-collectors.md)和 [Kubernetes 集群接收器](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/receiver/k8sclusterreceiver)。不要仅仅声明一个未使用的接收器/处理器，就认为它已启用。

## EKS 部署模式

这些是可选的部署模式，不是可以不加区分地一并应用的整套配置。无状态 relay 会将全部三种信号转发到上方的单一采样层。不要在任意负载均衡的节点/sidecar/HPA 层中执行尾部采样和 Span 聚合。多个采样实例需要基于 trace ID 的路由，并需要规划端点变更、处理中追踪、重启和存储；单靠 Service 或 HPA 无法提供这些能力。

保存 `otel-relay-config.yaml`，并按照相同的客户端 ConfigMap 生成流程创建 `otel-relay-config`。`OTEL_UPSTREAM_ENDPOINT` 和客户端证书用于标识单独准备的上游 Collector。relay 对采样决策而言是无状态的；其内存中的批处理/导出队列仍有故障和关闭限制。

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

DaemonSet 会运行在符合条件的 Linux 节点上，不会运行在 EKS Fargate 上。请为获准的节点配置选择器/容忍项；此处没有设置一概适用的容忍项或 hostPort 预留。`internalTrafficPolicy: Local` 会将此 Service 的流量仅路由到调用方所在节点上的就绪端点；如果没有这样的端点，流量就会被丢弃。它不是 Fargate 客户端的回退机制。应用必须显式将遥测数据发送到此端点。

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

请使用单独的 `otel-sidecar-config` ConfigMap，并填入下方配置。只有同一 Pod 会使用其环回明文 OTLP 接收器；上游流量使用双向 TLS。此规格对 256 MiB sidecar 设置 192 MiB 硬限制 / 144 MiB 软限制。应用镜像必须包含所选的 SDK/agent；仅设置端点变量本身不会添加检测。此 Kubernetes 1.35 Schema 示例使用原生 sidecar（`initContainers` 搭配 `restartPolicy: Always`，该功能在 1.33 中 GA）。应用启动前会先运行启动探针；正常关闭时会先停止应用容器，再停止 sidecar。后端数据交付和突发故障恢复仍需分别检查。

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

此 HPA 扩展的是无状态 **relay**，而非有状态采样器。前提条件包括 Metrics Server 以及合适的 requests/容量。三个副本、首选反亲和性和 3–10 的范围都只是示例设置，不能证明具备高可用性或吞吐能力。只有在检查执行、存储、网络和接收器要求之后，才可考虑在 Fargate 或 Auto Mode 中使用基于 Deployment 的 Collector。

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

Operator 0.158.0 有单独的兼容矩阵。其发布清单假设已准备好 cert-manager v1；请使用 [cert-manager 指南](../../security/10-cert-manager.md)中仍受维护且兼容的版本，而不要安装过时的 1.13.3 示例。升级现有的由所有者管理的安装之前，请检查 0.158.0 中的 CRD 变更和默认网络策略。

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

资源和示例应用都位于 `ecommerce`。固定版本的 Operator 会提供其版本化的默认检测镜像；请检查注入的镜像，不要将它们全部替换为 `latest`。其 Java/Python 默认版本与上方直接安装的版本不同。每个进程只使用一种检测方式。TLS Secret 的挂载仍由应用负责。

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

此处选择了 W3C Trace Context 和 baggage。只有在相应语言的 propagator 软件包和通信对端均支持 B3 时，B3 才是可选的互操作方案。不要在 baggage 中放入凭证或个人数据；传播可能跨越服务边界和信任边界。

### 自动检测注入

注解应放在 Pod 模板上，而不只是 Deployment 元数据中。`otel-instrumentation` 会选择 Pod 命名空间中的同名资源；也可以用 `namespace/name` 显式选择另一个命名空间。虽然可以使用命名空间级注解，但不要对每个 Pod 不加区分地启用 Java、Python 和 Node.js 检测。注入发生在新 Pod 被准入时，不会追溯应用到正在运行的 Pod。

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

Java、Python、Node.js、.NET、Go、Apache HTTPD 和 Nginx 各有不同的前提条件。在此版本中，Go 自动检测需要目标可执行文件路径，并会注入一个具有 UID 0 特权的组件；它并非适用于通用 Restricted-PSS/Fargate 场景的配方。请检查 Operator 功能设置和各语言指南。若未配置匹配的协议，Python/.NET/Go 的 HTTP 默认设置不得指向 gRPC 端点。

## 多后端配置

将此片段合并到经过审核的基础配置中；它不能独立使用。每个后端都需要自己的端点、信任配置和授权。AWS X-Ray 使用配置的 Region 和工作负载身份；有关确切的 IAM 信任/权限，请参阅 [X-Ray 指南](./02-xray.md)。禁用属性索引并不等于遮蔽数据。Datadog 的 api 对象来自由 Secret 管理的 api.yaml，其中包含 key（带引号的字符串）和 site。请向工作负载添加该 Secret 的只读挂载；基础工作负载并未挂载它。任何 key 都不会放入环境变量。本次审计未执行任何 AWS/Datadog/Jaeger 服务调用。

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

扇出导出无法保证原子交付，也无法保证各后端采用相同的保留策略。

### 2026年7月更新：观测 AI agent 流量的网络边界

[7月8日的 CNCF 文章](https://www.cncf.io/blog/2026/07/08/network-boundary-for-ai-agents-using-nginx-and-opentelemetry/)介绍了一个使用 NGINX 和 OTel 的单节点原型。其边界依赖于阻止其他出站路径的网络规则，而不只是设置代理变量。Span 描述的是配置代理可见的流量；TLS 处理、采样、Collector 保留策略和代理安全仍然重要。这只是网络控制的一层，并不能证明 agent 的决策正确或安全。

### 2026年8月更新：将慢 SQL 查询提炼为可靠性指标

[8月21日的 CNCF 文章](https://www.cncf.io/blog/2026/08/21/how-to-turn-slow-queries-into-actionable-reliability-metrics-with-opentelemetry/)及其[实验](https://github.com/causely-oss/slow-query-lab)比较了查询时长、按流量加权的影响，以及基于 Span 的指标与异常基线。请将文章中的历史示例视为示例，而非集群容量测量结果。文章本身提醒不要在指标标签中放入原始 SQL，并指出敏感参数、基数和基线预热等问题。采用实验配置之前，请对维度进行清理并限制其范围；延迟异常是症状，不是根因的证明。

### 2026年10月更新：将软件碳强度（SCI）作为 OTel 信号

在一篇[10月15日的 CNCF 文章](https://www.cncf.io/blog/2026/10/15/carbon-as-a-first-class-signal-bringing-software-carbon-intensity-to-opentelemetry/)中，Kepler 维护者兼 CNCF 大使 Diana Todea 以她在 Observability Summit Europe 2026 上的主题演讲为基础，提出将 Green Software Foundation 的软件碳强度（SCI）标准视为 OpenTelemetry 语义约定，把碳排放与工作负载和服务关联起来，作为一种可观测信号。这是一项引导发展方向的提议，目前仍在标准化讨论中，并非某个特定 OTel 版本已发布的功能，也不是已经完成的语义约定；在规划采用之前，请关注上游进展。

### 2026年10月更新：基于 OTel 数据流重建事件检测

在[9月30日的 CNCF 文章](https://www.cncf.io/blog/2026/09/30/from-40-seconds-to-under-10-rebuilding-incident-detection-on-opentelemetry-apache-kafka-and-apache-flink-on-kubernetes/)中，Atlassian 介绍了其历时18个月，基于 Kubernetes 上的 OpenTelemetry、Apache Kafka 和 Apache Flink 重建自动事件创建平台的过程，并将事件到指标的延迟从超过40秒降至不足10秒。正如文章本身所述，范围内召回率从约60%升至86%，但在表现不佳的一个月又回落至64%，而精确率仍低于目标。请将这些数字视为该组织的测量结果，而非此架构能够保证的结果；文章最有参考价值的是其权衡讨论，例如如何隔离共享队列中的噪声邻居以及成本问题。

### 2026年10月更新：在 Collector 中过滤 AI agent 遥测数据

[10月22日的 CNCF 文章](https://www.cncf.io/blog/2026/10/22/filtering-and-reducing-ai-agent-telemetry-with-the-opentelemetry-collector/)介绍了如何在 OpenTelemetry Collector 中整理 AI 编码 agent 的原生遥测数据，再将其发送到后端。在作者的示例中，针对一个 Claude Code 小任务启用所有内容标记后，生成了181条遥测记录（289 KB JSON），其中大部分是提示词和文件内容有效载荷，而仪表板、告警和查询都不会读取这些内容。建议的做法是先明确需要回答的问题——例如运行次数、成本、token 用量和工具调用结果等计数器及简短属性——然后在 Collector 流水线中丢弃其余数据。这些数字只是作者对一个 agent 执行一个任务时的测量结果，不是容量规划指南；哪些字段可以安全丢弃，取决于你自己的查询和保留要求。

## 最佳实践

### 1. 标准化资源属性

| 属性 | 示例 / 来源 |
|---|---|
| `service.name`、`service.version`、`service.namespace` | `order-service`、`1.2.3`、`ecommerce`；应用配置 |
| `deployment.environment.name` | `demo`；用于替代已弃用的 `deployment.environment` |
| `cloud.provider`、`cloud.region`、`cloud.availability_zone` | 经验证的部署元数据，而不是根据 Collector 主机猜测 |
| `k8s.cluster.name`、`k8s.namespace.name`、`k8s.pod.name`、`k8s.deployment.name` | 正确配置的 Kubernetes 丰富处理或工作负载元数据 |

这是属性清单，不是 Collector 处理器 YAML。Resource 用于标识数据的生成者。避免将每个资源属性都复制到指标标签中；Pod 名称、用户 ID 和原始查询文本可能导致高基数。性能剖析是另一种不断发展的信号；本指南重点介绍追踪、指标和日志，并不声称各 SDK 具有一致的稳定性。

### 2. 采样策略

对于一个高级示例（错误、延迟 >2 秒、关键服务条件为50%，以及5%基线），请将每条正向规则视为 OR 条件，而不是首个匹配规则优先，也不是预留配额。其他规则也可能保留某条追踪。如果需要互斥类别或 Span 速率预算，请专门设计并测试该策略。头部采样、已丢弃的 Span、分片变更和延迟到达仍是需要分别处理的限制。

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

没有 `client_ca_file` 的服务器 TLS 并不等于要求客户端证书。请保护两个方向的通信，验证证书名称和生命周期，并限制 Service/网络/后端访问。sidecar 示例中的同 Pod 环回明文通信属于另一个信任边界。浏览器遥测需要单独设计来源验证/身份验证/速率限制，而不是设置允许所有来源的 CORS。

attributes 处理器的 `hash` 操作使用 SHA-1。对可预测 ID 或 SQL 文本进行哈希并不等于匿名化；仍可能通过字典恢复数据，也仍可关联不同记录。应优先避免收集敏感值，然后在导出前删除明确标识的字段。请分别检查日志正文、Span 事件和资源属性。详细调试 exporter 或性能剖析端点可能会暴露数据，因此应将其用作临时且受控的诊断手段。

### 验证与限制

本地验证使用了真实的 Collector 0.160.0、合成 OTLP 流量和双向 TLS 环回端点，包括追踪/日志处理和尾部采样前的 Span 指标。remote-write 检查证明数据已通过 HTTPS 发送到测试接收端，并未证明实时 Prometheus 已接收数据。Python 手动 Span 使用 SDK 1.44.0 和内存 exporter。已检查 Kubernetes/Instrumentation Schema 和 Node.js 语法；未执行 Java/Node 应用启动、零代码注入、真实后端产品、EKS、IAM 或自动扩缩。

### 官方参考资料

- [Collector 0.160.0 组件](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.160.0/distributions/otelcol-contrib/manifest.yaml)
- [Operator 0.158.0 兼容性](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/getting-started/compatibility.md)
- [Operator 自动检测](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/auto-instrumentation/README.md)
- [Java agent 2.31.1](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/tag/v2.31.1)
- [OTLP exporter 配置](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Collector 扩缩容](https://opentelemetry.io/docs/collector/scaling/)
- [尾部采样](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Span 指标 connector](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/connector/spanmetricsconnector)
- [内存限制器](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/memorylimiterprocessor)
- [Loki 原生 OTLP](https://grafana.com/docs/loki/latest/send-data/otel/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Kubernetes 原生 sidecar](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [EKS Kubernetes 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [OpenTracing CNCF 里程碑](https://www.cncf.io/projects/opentracing/)
- [OpenCensus Go 仓库](https://github.com/census-instrumentation/opencensus-go)

## 测验

通过 [OpenTelemetry 测验](../../quizzes/observability/tracing/03-opentelemetry-quiz.md)检验你的知识。
