# Istio 分布式追踪

> **支持版本**：Istio 1.31
> **最后更新**：2026 年 9 月 11 日

> **验证范围**：这些实验配置依据官方参考和离线验证器检查，未部署集群。各示例注明命名空间、身份、存储、后端和负载假设，必须针对目标环境验证。

分布式追踪跟踪并可视化微服务间请求流程，帮助识别延迟瓶颈、分析错误根因和理解服务依赖。

## 目录

1. [分布式追踪概述](#distributed-tracing-overview)
2. [OpenTelemetry 集成](#opentelemetry-integration)
3. [Jaeger 集成](#jaeger-integration)
4. [Zipkin 集成](#zipkin-integration)
5. [上下文传播](#context-propagation)
6. [采样策略](#sampling-strategies)
7. [追踪分析](#trace-analysis)
8. [添加自定义 span](#adding-custom-spans)
9. [性能优化](#performance-optimization)
10. [故障排除](#troubleshooting)

## 分布式追踪概述 {#distributed-tracing-overview}

### W3C 追踪上下文

Istio 通过兼容追踪提供程序支持 W3C 追踪上下文。应用仍须在自身请求间传播上下文；图中应用 span 需要已初始化 SDK 或代理。示例涵盖 Sidecar/waypoint：ztunnel 不生成 HTTP 追踪 span。

![客户端请求通过 Service A、Service B 的 Envoy Sidecar 和应用容器传播 W3C 追踪上下文，各 Envoy Sidecar 和应用异步向 Jaeger Collector 导出 span 的时序图。](../../../.gitbook/assets/en-service-mesh-istio-observability-02-tracing-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-observability-02-tracing-0.html)

### 核心概念

#### Trace

表示单次请求在系统中完整路径的一组 span

#### Span

表示特定操作开始和结束的单元
- **Span ID**：唯一标识符
- **父 Span ID**：对父 span 的引用
- **Trace ID**：整个追踪的标识符
- **操作名**：操作名称（如 `HTTP GET /api/products`）
- **持续时间**：操作所需时间
- **标签**：元数据（服务名、HTTP 状态等）
- **日志**：带时间戳的事件

#### Baggage

应用/传播器支持 baggage 时传播的上下文键值对。Baggage 不自动成为 span 属性，且不得携带密钥。

## OpenTelemetry 集成 {#opentelemetry-integration}

OpenTelemetry 提供插桩、协议和采集器；不是追踪存储后端。此示例先向 Collector 发送 OTLP，再发往 Jaeger。Zipkin 和 Tempo 是替代后端。

### 1. 安装 OpenTelemetry Collector

测试前创建 `observability` 命名空间并部署下方 Jaeger 后端。这是使用内存尾部采样状态的单副本 Collector 示例。普通 Kubernetes Service 将流量分到多个尾部采样器时，不能让同一追踪的所有 span 保持在一起；生产扩展需要基于 trace ID 的路由、容量规划和迟到 span 处理。本实验内部 OTLP 为明文：部署时限制网络访问或配置 TLS/mTLS。健康扩展和内部指标监听器显式启用。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
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
        limit_mib: 1024
      resource:
        attributes:
        - key: k8s.cluster.name
          value: production-k8s
          action: upsert
        - key: deployment.environment.name
          value: production
          action: upsert
      filter/health:
        error_mode: ignore
        trace_conditions:
        - span.name == "/health" or span.name == "/readiness" or span.name == "/liveness"
      tail_sampling:
        decision_wait: 30s
        num_traces: 50000
        policies:
        - name: errors
          type: status_code
          status_code:
            status_codes:
            - ERROR
        - name: slow
          type: latency
          latency:
            threshold_ms: 1000
        - name: baseline
          type: probabilistic
          probabilistic:
            sampling_percentage: 10
      batch:
        timeout: 10s
        send_batch_size: 1024
        send_batch_max_size: 2048
    exporters:
      otlp_grpc/jaeger:
        endpoint: jaeger-collector.observability.svc.cluster.local:4317
        tls:
          insecure: true
      debug:
        verbosity: basic
    service:
      extensions:
      - health_check
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - memory_limiter
          - resource
          - filter/health
          - tail_sampling
          - batch
          exporters:
          - otlp_grpc/jaeger
          - debug
      telemetry:
        logs:
          level: info
        metrics:
          readers:
          - pull:
              exporter:
                prometheus:
                  host: 0.0.0.0
                  port: 8888
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 4317
          name: otlp-grpc
          protocol: TCP
        - containerPort: 4318
          name: otlp-http
          protocol: TCP
        - containerPort: 8888
          name: metrics
          protocol: TCP
        - containerPort: 13133
          name: health
        volumeMounts:
        - name: config
          mountPath: /etc/otel
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /
            port: 13133
        readinessProbe:
          httpGet:
            path: /
            port: 13133
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
  labels:
    app: otel-collector
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
  type: ClusterIP
```

已退役 `jaeger` 导出器由 OTLP/gRPC 替代，`logging` 由 `debug` 替代。过滤器匹配实际观测的精确 span 名称；按插桩调整，并考虑丢弃 span 对追踪完整性的影响。尾部策略保留实际到达的合格追踪；无法恢复上游丢弃的 span。验证后移除诊断导出。

### 2. 在 Istio 中启用 OpenTelemetry

#### MeshConfig 配置

用 `istioctl install -f` 将此提供程序合并到现有安装设置；不要覆盖整个 `istio` ConfigMap。`maxTagLength` 限制路径标签，不限制每个 span 属性。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel-tracing
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        maxTagLength: 256
```

#### 使用 Telemetry API 启用追踪

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0
    customTags:
      cluster_id:
        literal:
          value: "production-cluster"
      environment:
        literal:
          value: "production"
```

每命名空间使用一个适用的无选择器 Telemetry 资源；合并追踪和日志设置，不要应用冲突示例。标头标签是不可信请求元数据，不是经过验证的身份。仅使用获准的假名化用户关联值。环境标签读取代理环境，不是应用环境变量。

### 3. 按命名空间追踪配置

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: namespace-tracing
  namespace: production
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0
    customTags:
      namespace:
        literal:
          value: "production"
      team:
        literal:
          value: "backend-team"
      # Add request headers as tags
      user_id:
        header:
          name: x-user-id
          defaultValue: "unknown"
      request_id:
        header:
          name: x-request-id
      # Add environment variables as tags
      pod_name:
        environment:
          name: POD_NAME
          defaultValue: "unknown"
```

## Jaeger 集成 {#jaeger-integration}

### Jaeger 2 开发部署

Jaeger 2 使用 `jaegertracing/jaeger` 镜像及显式配置文件。以下内存实例用于开发；重启丢失追踪。查询和 OTLP 端点保持集群内部；通过端口转发访问 UI。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jaeger-config
  namespace: observability
data:
  config.yaml: |
    extensions:
      jaeger_storage:
        backends:
          traces:
            memory:
              max_traces: 50000
      jaeger_query:
        storage:
          traces: traces
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      batch: {}
    exporters:
      jaeger_storage_exporter:
        trace_storage: traces
    service:
      extensions:
      - jaeger_storage
      - jaeger_query
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - batch
          exporters:
          - jaeger_storage_exporter
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/jaeger:2.20.0
        args:
        - --config=/etc/jaeger/config.yaml
        ports:
        - containerPort: 4317
          name: otlp-grpc
        - containerPort: 4318
          name: otlp-http
        - containerPort: 16686
          name: query-http
        volumeMounts:
        - name: config
          mountPath: /etc/jaeger
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
      volumes:
      - name: config
        configMap:
          name: jaeger-config
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-collector
  namespace: observability
spec:
  selector:
    app: jaeger
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-query
  namespace: observability
spec:
  selector:
    app: jaeger
  ports:
  - name: query-http
    port: 16686
    targetPort: query-http
  type: ClusterIP
```

### 生产存储和扩缩容

持久存储使用受支持的托管 Elasticsearch/OpenSearch 部署及匹配 Jaeger 存储驱动。Jaeger 2.20 公布的 Elasticsearch 矩阵列出 **7.x/8.x**；不要因 Elasticsearch 最新发布就推断支持更新主版本。现有 ECK 部署也需检查 Operator/集群兼容性；EKS `gp3` 存储需要 EBS CSI 驱动和实际 StorageClass。

对于 Elasticsearch，用此片段替换 `jaeger-config` 中内存后端；保留 receiver、exporter、query 和 pipeline 设置，使用存储名称 `traces`。创建 Secret `jaeger-es-client`，包含受限 `jaeger` 用户的 `password` 及匹配服务器证书的公有 `ca.crt`。服务器主机名验证保持启用。

```yaml
extensions:
  jaeger_storage:
    backends:
      traces:
        elasticsearch:
          server_urls:
          - https://jaeger-es-es-http.observability.svc.cluster.local:9200
          auth:
            basic:
              username: jaeger
              password_file: /etc/jaeger/es/password
          tls:
            ca_file: /etc/jaeger/es/ca.crt
          indices:
            index_prefix: production
```

将下方 Deployment 片段合并到现有 `jaeger` Deployment（保留镜像、参数、配置挂载和其他字段）。使用共享持久存储时，这些合并 collector/query 实例无状态，可多副本运行。需要独立扩缩容时，可用相同 Jaeger 2 二进制配置独立 collector/query 角色。

```yaml
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: jaeger
        volumeMounts:
        - name: es-client
          mountPath: /etc/jaeger/es
          readOnly: true
      volumes:
      - name: es-client
        secret:
          secretName: jaeger-es-client
```

使用 [Jaeger Elasticsearch 指南](https://www.jaegertracing.io/docs/2.20/storage/elasticsearch/)和发布模式配置存储初始化、索引轮换/保留、备份及存储端权限。旧 1.x 环境变量/镜像部署不是 Jaeger 2 配置。迁移现有存储追踪前审核发布说明。

### 直接 Istio → Jaeger OTLP 替代方案

此方式绕过独立 Collector，因此也绕过其尾部采样策略。使用适合工作负载的头部采样。它是替代提供程序选择：合并到现有安装，并在适用 Telemetry 资源中仅选择预期提供程序。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: jaeger
      opentelemetry:
        service: jaeger-collector.observability.svc.cluster.local
        port: 4317
        maxTagLength: 256
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: jaeger-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: jaeger
    randomSamplingPercentage: 1
```

## Zipkin 集成 {#zipkin-integration}

### Zipkin 开发部署

此替代方案使用 Zipkin 3.6.1 和内存存储测试；重启丢失数据。生产需要受支持持久存储后端、身份验证/TLS 和已配置网络访问。根据 [Zipkin 服务器配置](https://github.com/openzipkin/zipkin/blob/3.6.1/zipkin-server/README.md)选择后端；不要指向未部署的 `elasticsearch:9200`。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zipkin
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: zipkin
  template:
    metadata:
      labels:
        app: zipkin
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: zipkin
        image: openzipkin/zipkin:3.6.1
        ports:
        - containerPort: 9411
          name: http
        env:
        - name: STORAGE_TYPE
          value: mem
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: zipkin
  namespace: observability
spec:
  selector:
    app: zipkin
  ports:
  - name: http
    port: 9411
    targetPort: http
  type: ClusterIP
```

### 配置 Istio 提供程序

Telemetry 引用前，提供程序必须存在。合并此安装输入，并将此 Telemetry 作为 Collector/Jaeger 选择的替代方案。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: zipkin
      zipkin:
        service: zipkin.observability.svc.cluster.local
        port: 9411
        maxTagLength: 256
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: zipkin-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: zipkin
    randomSamplingPercentage: 1
```

## 上下文传播 {#context-propagation}

分布式追踪的关键是在服务间正确传播追踪上下文。

### 必需 HTTP 标头

传播为代理/后端配置的格式；W3C 和 B3 是备选，或显式配置多格式传播。同时转发 `x-request-id`。B3 仍受支持；不得无差别启用调试 `X-B3-Flags: 1`。

#### W3C 追踪上下文（推荐）

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
tracestate: congo=t61rcWkgMzE
```

#### B3 标头

**单标头格式（推荐）**：
```
b3: 80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1-05e3ac9a4f6e3b90
```

**多标头格式**：
```
X-B3-TraceId: 80f198ee56343ba864fe8b2a57d3eff7
X-B3-SpanId: e457b5a2e4d86bd1
X-B3-ParentSpanId: 05e3ac9a4f6e3b90
X-B3-Sampled: 1
```

### 应用中的上下文传播

以下示例假定已有 Collector 和 `service-b:8080/api/service-b` 端点。安装兼容 API/SDK/导出器/插桩依赖，并在**处理请求前**初始化 SDK。实验端点在集群内使用明文 OTLP；真实部署应配置可信 TLS/mTLS 和网络限制。SDK 自动插桩与手动传播不应创建重复客户端 span。单独保留 `x-request-id`，供 Istio 请求关联。

#### Python（Flask + OpenTelemetry）

在应用环境安装 Flask、requests、`opentelemetry-sdk`、`opentelemetry-exporter-otlp-proto-grpc`、`opentelemetry-instrumentation-flask` 和 `opentelemetry-instrumentation-requests`。Flask/requests 插桩管理提取和注入；手动传播 API 为 `opentelemetry.propagate.extract`，不是原先格式错误的导入。

```python
import atexit
import requests
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

provider = TracerProvider(resource=Resource.create({"service.name": "service-a"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint="otel-collector.observability.svc.cluster.local:4317", insecure=True
)))
trace.set_tracer_provider(provider)
set_global_textmap(TraceContextTextMapPropagator())
atexit.register(provider.shutdown)
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
tracer = trace.get_tracer(__name__)

@app.get("/api/service-a")
def service_a():
    # Flask instrumentation extracted the parent; requests instrumentation injects its child.
    with tracer.start_as_current_span("process-request"):
        headers = {}
        if request.headers.get("x-request-id"):
            headers["x-request-id"] = request.headers["x-request-id"]
        response = requests.get("http://service-b:8080/api/service-b",
                                headers=headers, timeout=3)
        response.raise_for_status()
        return response.text, response.status_code, {
            "Content-Type": response.headers.get("Content-Type", "text/plain")
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

Flask 开发服务器仅用于本地测试；部署时使用应用生产服务器和 SDK 关闭生命周期。

#### Go（Gin + OpenTelemetry）

初始化真实 tracer provider 和 W3C propagator。下游请求使用 `Start` 返回的上下文，处理错误并关闭响应正文。将导入模块添加到应用 `go.mod`；不要丢弃上下文/错误返回值。

```go
package main

import (
	"context"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func main() {
	exporter, err := otlptracegrpc.New(context.Background(),
		otlptracegrpc.WithEndpoint("otel-collector.observability.svc.cluster.local:4317"),
		otlptracegrpc.WithInsecure())
	if err != nil {
		log.Fatal(err)
	}
	provider := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(resource.NewSchemaless(attribute.String("service.name", "service-a"))))
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := provider.Shutdown(ctx); err != nil {
			log.Print(err)
		}
	}()
	client := &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport), Timeout: 3 * time.Second}
	router := gin.Default()
	router.Use(otelgin.Middleware("service-a"))
	router.GET("/api/service-a", func(c *gin.Context) {
		ctx, span := otel.Tracer("service-a").Start(c.Request.Context(), "process-request")
		defer span.End()
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, "http://service-b:8080/api/service-b", nil)
		if err != nil {
			c.Status(http.StatusInternalServerError)
			return
		}
		if id := c.GetHeader("x-request-id"); id != "" {
			req.Header.Set("x-request-id", id)
		}
		resp, err := client.Do(req)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, "downstream request failed")
			c.Status(http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()
		// Bound this demonstration response to 1 MiB.
		body, err := io.ReadAll(io.LimitReader(resp.Body, (1<<20)+1))
		if err != nil || len(body) > 1<<20 {
			c.Status(http.StatusBadGateway)
			return
		}
		c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), body)
	})
	if err := router.Run(":8080"); err != nil {
		log.Print(err)
	}
}
```

#### Java（Spring WebFlux + OpenTelemetry Java Agent）

使用兼容 OpenTelemetry Java agent 和 OTLP 端点启动 Spring WebFlux 应用。代理为响应式服务器/客户端生命周期及上下文传播插桩。`try (Scope ...) { return Mono... } finally { span.end(); }` 在订阅完成前结束 span，对异步工作不正确。此控制器依赖代理受支持的 WebFlux/Reactor 插桩：

```bash
OTEL_SERVICE_NAME=service-a \
OTEL_EXPORTER_OTLP_PROTOCOL=grpc \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317 \
java -javaagent:/opt/otel/opentelemetry-javaagent.jar -jar app.jar
```

```java
import java.time.Duration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@RestController
public class ServiceAController {
    private final WebClient webClient;
    public ServiceAController(WebClient.Builder builder) {
        this.webClient = builder.baseUrl("http://service-b:8080").build();
    }

    @GetMapping("/api/service-a")
    public Mono<String> serviceA(@RequestHeader(value = "x-request-id", required = false) String requestId) {
        return webClient.get().uri("/api/service-b")
                .headers(headers -> { if (requestId != null) headers.set("x-request-id", requestId); })
                .retrieve().bodyToMono(String.class)
                .timeout(Duration.ofSeconds(3));
    }
}
```

#### Node.js（CommonJS Express + OpenTelemetry）

安装 `express`、`axios`、`@opentelemetry/api`、`@opentelemetry/sdk-node`、`@opentelemetry/auto-instrumentations-node` 和 `@opentelemetry/exporter-trace-otlp-grpc`。在应用导入前加载插桩；仅导入 API 不会配置 SDK 或导出器。

```javascript
// instrumentation.cjs: load before Express, HTTP clients, or application modules.
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter(),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
process.once('SIGTERM', () => sdk.shutdown().finally(() => process.exit(0)));
```

```javascript
// app.cjs
const express = require('express');
const axios = require('axios');
const { trace, SpanStatusCode } = require('@opentelemetry/api');
const app = express();
const tracer = trace.getTracer('service-a');
app.get('/api/service-a', async (req, res) => {
  await tracer.startActiveSpan('process-request', async (span) => {
    try {
      const headers = {};
      if (req.headers['x-request-id']) headers['x-request-id'] = req.headers['x-request-id'];
      const response = await axios.get('http://service-b:8080/api/service-b', {headers, timeout: 3000});
      res.json({result: response.data});
    } catch (error) {
      span.recordException(error);
      span.setStatus({code: SpanStatusCode.ERROR});
      res.status(502).json({error: 'Downstream request failed'});
    } finally {
      span.end();
    }
  });
});
app.listen(8080);
```

```bash
OTEL_SERVICE_NAME=service-a \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317 \
node --require ./instrumentation.cjs app.cjs
```

### 追踪上下文验证

验证测试请求在后端产生相同 trace ID 且父子关系符合预期的 span。在受控应用测试中检查入站/出站标头。默认 Envoy 访问日志不包含每个追踪标头；启用代理调试日志不会启用访问日志，也不保证输出标头。需要标头时显式配置访问日志格式，并避免记录凭证/baggage。

```bash
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
istioctl proxy-config clusters <pod-name> -n <namespace> \
  --fqdn otel-collector.observability.svc.cluster.local
kubectl logs -n observability deployment/otel-collector --tail=100
```

## 采样策略 {#sampling-strategies}

### 采样层级

#### 1. 头部采样（初始采样）

头部采样提前决定。以下百分比是备选；上游采样决策和 SDK 采样器也影响到达的 span。如果 Collector 必须评估每条追踪的错误/延迟，应发送所有合格 span，而不是尾部采样前先丢弃 90%。

**网格范围级别**：
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-head-sampling
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 10.0
```

**命名空间级别**：
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: sampling-config
  namespace: production
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 25.0  # 25% sampling
```

**工作负载级别**：
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-service-tracing
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0  # 100% sampling for critical services
```

#### 2. 尾部采样（事后采样）

尾部采样根据决策窗口中积累的 span 决定，不基于保证完整的追踪。按预期时长/数据量规划窗口和缓冲，将同一追踪路由到同一 Collector，并考虑迟到 span、重启和溢出。以下策略保留到达 Collector 的匹配追踪。将此处理器合并到 traces 管道中，放在 batch 处理器前。

```yaml
# OpenTelemetry Collector's tail_sampling processor
processors:
  tail_sampling:
    decision_wait: 10s  # Wait time for trace completion
    num_traces: 100000  # Number of traces to keep in memory
    expected_new_traces_per_sec: 1000
    policies:
      # Keep all traces with errors
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep all slow requests (> 1 second)
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 1000

      # 100% sampling for specific services
      - name: critical-services
        type: string_attribute
        string_attribute:
          key: service.name
          values:
          - payment-service
          - auth-service

      # Keep all HTTP 5xx errors
      - name: http-errors
        type: numeric_attribute
        numeric_attribute:
          key: http.response.status_code
          min_value: 500
          max_value: 599
      - name: legacy-http-errors
        type: numeric_attribute
        numeric_attribute:
          key: http.status_code
          min_value: 500
          max_value: 599

      # 5% sampling for the rest
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

### 限速采样

限速策略是按 span 速率的令牌桶，不是自动调优的错误/延迟采样器。这是替代策略列表；将其放在其他保留策略旁，不会对那些策略保留的追踪施加全局上限。突发和完整追踪决策影响短时间间隔。

```yaml
processors:
  tail_sampling:
    policies:
      - name: rate-limited-sampling
        type: rate_limiting
        rate_limiting:
          spans_per_second: 1000  # Keep maximum 1000 spans per second
```

### 采样策略指南

| 目标 | 头部输入 | Collector/存储决策 |
|------|------------|----------------------------|
| 小型开发测试 | 100% | 全部保留，验证传播 |
| 限制生产数据量 | 实测百分比 | 存储收到的样本 |
| 保留错误/慢追踪 | 所有合格 span | 尾部策略保留匹配追踪及基线样本 |
| 限制保留量 | 为尾部决策提供所有合格 span | 明确速率/复合策略和容量限制 |

这些是设计选择，不是通用环境默认值。低比例头部采样加尾部采样不保证保留所有错误。检查实际 span 状态和属性名（当前 OpenTelemetry 约定为 `http.response.status_code`，部分代理/旧 span 为 `http.status_code`）。

## 追踪分析 {#trace-analysis}

### 在 Jaeger UI 搜索追踪

```bash
# Access Jaeger UI
kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Browser: http://localhost:16686
```

**搜索选项**：
- **Service**：服务名
- **Operation**：操作名（如 `GET /api/products`）
- **Tags**：标签过滤（如 `http.status_code=500`）
- **Min Duration**：最小延迟
- **Max Duration**：最大延迟
- **Limit Results**：结果数量限制

### 实用追踪查询

#### 1. 查找带错误的追踪

```
Tags: error=true
```

或

```
Tags: http.status_code=500
```

#### 2. 查找慢请求

```
Min Duration: 1s
```

#### 3. 跟踪特定用户请求

```
Tags: user_id=12345
```

#### 4. 分析特定 API 端点

```
Operation: GET /api/products/{id}
```

### Jaeger UI API 诊断

完成上方端口转发后，这些 UI 查询端点可辅助交互诊断。它们是内部 UI API，不是稳定应用约定；持久集成使用 Jaeger 文档规定的查询 API。

```bash
# Query traces for a specific service
curl "http://localhost:16686/api/traces?service=productpage&limit=10"

# Query specific trace ID
curl "http://localhost:16686/api/traces/0af7651916cd43dd8448eb211c80319c"

# Query service list
curl "http://localhost:16686/api/services"

# Query operations for a specific service
curl "http://localhost:16686/api/services/productpage/operations"
```

### 识别延迟瓶颈

1. **检查瀑布图和独占时间**：父 span 包含子级时间；仅最长父级不能定位瓶颈。
2. **检查关键路径**：对整体请求时间影响最大的路径
3. **并行与顺序执行**：检查可并行任务是否在顺序运行

### Grafana Tempo 集成

Tempo 是替代追踪后端。默认 HTTP **查询**端口为 3200；OTLP 写入使用独立配置的接收器，如 4317。将以下文件挂载到 Grafana `provisioning/datasources` 目录（或配置 chart 数据源预置）。仅 ConfigMap 不会自动加载。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  tempo.yaml: |
    apiVersion: 1
    datasources:
    - name: Tempo
      uid: tempo
      type: tempo
      access: proxy
      url: http://tempo.observability.svc.cluster.local:3200
      jsonData:
        tracesToLogsV2:
          datasourceUid: loki
          tags:
          - key: service.name
            value: app
          filterByTraceID: false
          filterBySpanID: false
        tracesToMetrics:
          datasourceUid: prometheus
          tags:
          - key: service.name
            value: destination_canonical_service
          queries:
          - name: Request rate
            query: sum(rate(istio_requests_total{reporter="destination",$$__tags}[5m]))
        nodeGraph:
          enabled: true
```

示例要求现有数据源 UID `loki` 和 `prometheus`。对齐 SDK `service.name`、Loki `app` 和 Istio `destination_canonical_service`；实际值不同时更改映射。服务名冲突时添加命名空间/集群映射。Grafana 预置将 `$$__tags` 转为字面查询变量 `$__tags`。仅日志含 trace ID 时启用 trace ID 过滤。Tempo 服务图还要求 Prometheus 中有生成的 service-graph/span 指标；仅普通 Istio 请求指标不提供这些序列。

## 添加自定义 span {#adding-custom-spans}

在应用代码添加自定义 span，以获得更详细追踪。

### Python 示例

此函数属于已初始化应用；`check_inventory`、`process_payment` 和 `PaymentError` 是应用定义的回调/类型。

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def process_order(order_id):
    with tracer.start_as_current_span("process-order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.amount", 99.99)

        # Check inventory
        with tracer.start_as_current_span("check-inventory") as inventory_span:
            inventory = check_inventory(order_id)
            inventory_span.set_attribute("inventory.available", inventory)

        # Process payment
        with tracer.start_as_current_span("process-payment", record_exception=False,
                                          set_status_on_exception=False) as payment_span:
            try:
                payment_result = process_payment(order_id)
                payment_span.set_attribute("payment.status", "success")
            except PaymentError as e:
                payment_span.set_status(Status(StatusCode.ERROR))
                payment_span.record_exception(e)
                raise

        # Record event
        span.add_event("Order processed successfully", {
            "order.id": order_id
        })

        return {"status": "success"}
```

### Go 示例

此函数是应用片段；`checkInventory` 和 `processPayment` 是应用函数。两个子 span 都使用父处理上下文，避免 payment 意外成为已结束 inventory span 的子级。

```go
import (
    "context"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/codes"
)

func processOrder(ctx context.Context, orderID string) error {
    tracer := otel.Tracer("order-service")

    ctx, span := tracer.Start(ctx, "process-order")
    defer span.End()

    span.SetAttributes(
        attribute.String("order.id", orderID),
        attribute.Float64("order.amount", 99.99),
    )

    // Check inventory
    inventoryCtx, inventorySpan := tracer.Start(ctx, "check-inventory")
    inventory, err := checkInventory(inventoryCtx, orderID)
    if err != nil {
        inventorySpan.RecordError(err)
        inventorySpan.SetStatus(codes.Error, err.Error())
        inventorySpan.End()
        return err
    }
    inventorySpan.SetAttributes(attribute.Bool("inventory.available", inventory))
    inventorySpan.End()

    // Process payment
    paymentCtx, paymentSpan := tracer.Start(ctx, "process-payment")
    err = processPayment(paymentCtx, orderID)
    if err != nil {
        paymentSpan.RecordError(err)
        paymentSpan.SetStatus(codes.Error, err.Error())
        paymentSpan.End()
        return err
    }
    paymentSpan.SetAttributes(attribute.String("payment.status", "success"))
    paymentSpan.End()

    // Record event
    span.AddEvent("Order processed successfully")

    return nil
}
```

## 性能优化 {#performance-optimization}

### 追踪数据大小优化

使用上方提供程序 `maxTagLength` 和 Telemetry 自定义标签。按需在 SDK/Collector 限制属性/事件；截断路径不会对 URL 或标签中的密钥脱敏。仅存储所需属性，尽可能使用路由模板而非原始标识符。

### Collector 性能调优

```yaml
processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
    send_batch_max_size: 2048

  memory_limiter:
    check_interval: 1s
    limit_mib: 1024
    spike_limit_mib: 256
```

### 存储优化

对于持久 Jaeger 部署，为实际 `production` 索引前缀和所选轮换模式配置保留策略。按实测写入和查询负载规划分片/副本。使用版本兼容的 Jaeger 索引初始化和 Elasticsearch ILM（或存储后端生命周期机制），使数据过期前验证备份和查询回看范围。七天是示例保留决策，不是通用默认值。

旧独立 Curator 方案不匹配已配置索引前缀，并遗漏存储凭证/TLS 和轮换前提条件。遵循 [Jaeger 2.20 存储生命周期流程](https://www.jaegertracing.io/docs/2.20/storage/elasticsearch/)和发布模式；不要将宽泛索引删除命令作为追踪诊断运行。

## 故障排除 {#troubleshooting}

### 追踪缺失

检查有效 HTTP connection-manager 追踪配置和提供程序集群，再区分接收、导出和后端存储。仅 `.bootstrap.tracing` 检查会遗漏动态配置追踪。使用以下只读检查：

```bash
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
istioctl proxy-config clusters <pod-name> -n <namespace> \
  --fqdn otel-collector.observability.svc.cluster.local
kubectl logs -n observability deployment/otel-collector --tail=100
kubectl logs -n observability deployment/jaeger --tail=100
# Keep this running; use a second terminal for the curl command below.
kubectl port-forward -n observability svc/otel-collector 8888:8888
```

```bash
curl -fsS http://localhost:8888/metrics | \
  rg 'otelcol_(receiver_accepted|exporter_sent|exporter_send_failed)_spans'
```

接受 span 不能证明导出或持久存储。检查导出器错误、后端连通性/身份验证和已存储 trace ID。尾部采样和内存存储有意减少保留数据。指标后缀可能因 Collector 遥测配置而异。

### 上下文传播中断

为每个独立请求使用新的测试 trace ID，并在后端检查应用/服务器 span。应用发起新出站调用时必须注入活动子上下文。检查 W3C/B3 格式匹配已配置提供程序和 SDK 传播器，并确保 HTTP 库加载前启动插桩。更改代理日志级别不启用访问日志；需要时显式配置 Telemetry 访问日志提供程序。

### 非预期采样

```bash
kubectl get telemetry -A
kubectl describe telemetry <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
```

同时审核根/命名空间/工作负载策略继承、上游 sampled 标志、SDK 采样器和 Collector 策略。Collector 无法重建头部采样丢弃的追踪。

## 参考资料

- [Istio 分布式追踪](https://istio.io/latest/docs/tasks/observability/distributed-tracing/)
- [OpenTelemetry 文档](https://opentelemetry.io/docs/)
- [Jaeger 文档](https://www.jaegertracing.io/docs/)
- [Zipkin 文档](https://zipkin.io/)
- [W3C 追踪上下文](https://www.w3.org/TR/trace-context/)
- [B3 传播](https://github.com/openzipkin/b3-propagation)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
