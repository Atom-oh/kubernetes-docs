# 可观测性分析：日志、指标和追踪

> **审查基线**：OTel Go 1.46.0 / otelhttp 0.71.0，Python SDK 1.44.0 / instrumentation 0.65b0，Collector 0.162.0，Alloy 1.20.1，Loki 3.7.8，Tempo 3.0.3，Grafana 13.2.4\
> **最后审查时间**：2026 年 10 月 16 日。SDK/日志/exemplar 行为通过内存导出器和 HTTP 测试替身进行了测试；LogQL 则针对本地 Loki 中的合成日志进行了测试。没有向真实集群或外部遥测后端导出数据。

< [上一章：运维告警](07-observability-alerts.md) | [目录](README.md) | [下一章：堆栈运维](09-observability-stack.md) >

关联分析将关于同一时间、服务和请求的证据联系起来。仅仅同时发生并不能确定根本原因。请检查数据缺失、采样和保留情况，然后验证假设。

## 1. 标识符和实际传输路径

| 信号 | 本章使用的路径 | 关联约定 |
|---|---|---|
| 追踪 | SDK → OTLP/HTTP Collector → Tempo | W3C 上下文和 `service.name` |
| 日志 | JSON stdout → Alloy Kubernetes 日志源 → Loki | JSON `trace_id` 和 `span_id` |
| 指标 | Prometheus client → `/metrics` OpenMetrics 抓取 | Exemplar `trace_id` |
| 查询 | Grafana → 各数据源 | 显式 UID 和标签映射 |

追踪导出器不会自动将 stdout 日志或 Prometheus-client 指标转换为 OTLP。若要通过 OTLP 发送每种信号，都需要相应的 SDK 导出器/Collector 及管道。Tempo 也不会自动关联日志存储和指标存储。

### W3C 和 B3

```text
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

W3C trace ID 使用 32 个十六进制字符，parent span ID 使用 16 个；全零标识符无效。标志位包含诸如 sampled 位之类的信息。有效 ID 或 sampled 标志并不保证后端会存储数据或保留数据。

B3 是另一种受支持的传播格式，trace ID 有 64 位和 128 位两种。如果要接受多种格式，应为冲突的请求头和入口信任边界定义优先级。这些示例仅使用 W3C TraceContext。不要不加区分地在 baggage 中传播敏感值。

## 2. 可执行的 SDK 示例

Go 和 Python 是同一日志/指标约定的**替代实现**。不要在同一端口上同时启动二者。它们的主入口是绑定到 loopback 的本地演示；部署时请使用适当的应用服务器、Service 和绑定配置。

共享服务为 `correlation-api`。JSON 包含 `timestamp`、`level`、`message`、`service_name`、有界的 `route`、`status_code`、`latency_ms` 以及有效的 trace/span ID。不要将原始 URL 或用户标识符转化为普通指标标签。

### Go

请使用受支持且已打补丁的 Go 1.25+ 环境。本次审查中的本地编译使用了 Go 1.25.0；这与选择合适的生产补丁版本是两回事。

```text
module example.com/correlation-demo

go 1.25.0

require (
	github.com/prometheus/client_golang v1.24.1
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.71.0
	go.opentelemetry.io/otel v1.46.0
	go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp v1.46.0
	go.opentelemetry.io/otel/sdk v1.46.0
	go.opentelemetry.io/otel/trace v1.46.0
)

require (
	github.com/beorn7/perks v1.0.1 // indirect
	github.com/cenkalti/backoff/v5 v5.0.3 // indirect
	github.com/cespare/xxhash/v2 v2.3.0 // indirect
	github.com/felixge/httpsnoop v1.1.0 // indirect
	github.com/go-logr/logr v1.4.4 // indirect
	github.com/go-logr/stdr v1.2.2 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/grpc-ecosystem/grpc-gateway/v2 v2.30.0 // indirect
	github.com/munnerz/goautoneg v0.0.0-20191010083416-a7dc8b61c822 // indirect
	github.com/prometheus/client_model v0.6.2 // indirect
	github.com/prometheus/common v0.70.1 // indirect
	github.com/prometheus/procfs v0.21.1 // indirect
	go.opentelemetry.io/auto/sdk v1.2.1 // indirect
	go.opentelemetry.io/otel/exporters/otlp/otlptrace v1.46.0 // indirect
	go.opentelemetry.io/otel/metric v1.46.0 // indirect
	go.opentelemetry.io/proto/otlp v1.11.0 // indirect
	golang.org/x/net v0.58.0 // indirect
	golang.org/x/sys v0.47.0 // indirect
	golang.org/x/text v0.41.0 // indirect
	google.golang.org/genproto/googleapis/api v0.0.0-20260819154853-08b0e4226688 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20260819154853-08b0e4226688 // indirect
	google.golang.org/grpc v1.83.1 // indirect
	google.golang.org/protobuf v1.36.12 // indirect
)
```

```go
// main.go
package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

const serviceName = "correlation-api"

func newLogger(writer io.Writer) *slog.Logger {
	return slog.New(slog.NewJSONHandler(writer, &slog.HandlerOptions{
		ReplaceAttr: func(groups []string, attr slog.Attr) slog.Attr {
			if len(groups) == 0 {
				if attr.Key == slog.TimeKey {
					attr.Key = "timestamp"
				}
				if attr.Key == slog.MessageKey {
					attr.Key = "message"
				}
			}
			return attr
		},
	}))
}

func newProvider(exporter sdktrace.SpanExporter, ratio float64) *sdktrace.TracerProvider {
	// Explicit resource attributes avoid mixing incompatible schema URLs.
	return sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(resource.NewSchemaless(
			attribute.String("service.name", serviceName),
			attribute.String("service.version", "1.0.0"),
			attribute.String("deployment.environment.name", "demo"),
		)),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(ratio))),
	)
}

func newHandler(tp *sdktrace.TracerProvider, logger *slog.Logger, downstream string, transport http.RoundTripper) http.Handler {
	registry := prometheus.NewRegistry()
	requests := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total", Help: "Completed requests",
	}, []string{"method", "route", "status"})
	duration := prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Name: "http_request_duration_seconds", Help: "HTTP duration in seconds", Buckets: prometheus.DefBuckets,
	}, []string{"method", "route", "status"})
	registry.MustRegister(requests, duration)
	propagator := propagation.TraceContext{}
	client := &http.Client{
		Transport: otelhttp.NewTransport(transport, otelhttp.WithTracerProvider(tp), otelhttp.WithPropagators(propagator)),
		Timeout:   5 * time.Second,
	}
	tracer := tp.Tracer("correlation-demo")
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{EnableOpenMetrics: true}))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) })
	mux.Handle("GET /api/orders", otelhttp.NewHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		status := http.StatusOK
		ctx, span := tracer.Start(r.Context(), "prepare-order-response")
		span.SetAttributes(attribute.String("app.operation", "orders.list"))
		if downstream != "" {
			// Trusted configuration only; never derive the destination from request input.
			req, err := http.NewRequestWithContext(ctx, http.MethodGet, downstream, nil)
			if err == nil {
				var response *http.Response
				response, err = client.Do(req)
				if err == nil {
					_, _ = io.Copy(io.Discard, io.LimitReader(response.Body, 4096))
					_ = response.Body.Close()
					if response.StatusCode >= 400 {
						err = errors.New("dependency returned unsuccessful status")
					}
				}
			}
			if err != nil {
				span.RecordError(err)
				span.SetStatus(codes.Error, "dependency unavailable")
				status = http.StatusBadGateway
			}
		}
		span.End()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_ = json.NewEncoder(w).Encode(map[string]bool{"ok": status == http.StatusOK})
		seconds := time.Since(started).Seconds()
		statusLabel := strconv.Itoa(status)
		method := r.Method // The GET ServeMux pattern accepts GET and HEAD.
		requests.WithLabelValues(method, "/api/orders", statusLabel).Inc()
		context := trace.SpanContextFromContext(r.Context())
		observer := duration.WithLabelValues(method, "/api/orders", statusLabel)
		if context.IsValid() && context.IsSampled() {
			observer.(prometheus.ExemplarObserver).ObserveWithExemplar(seconds, prometheus.Labels{"trace_id": context.TraceID().String()})
		} else {
			observer.Observe(seconds)
		}
		attributes := []any{
			"service_name", serviceName, "method", method, "route", "/api/orders",
			"status_code", status, "latency_ms", seconds * 1000,
		}
		if context.IsValid() {
			attributes = append(attributes, "trace_id", context.TraceID().String(), "span_id", context.SpanID().String())
		}
		level := slog.LevelInfo
		if status >= 500 {
			level = slog.LevelError
		}
		logger.Log(r.Context(), level, "request completed", attributes...)
	}), "orders", otelhttp.WithTracerProvider(tp), otelhttp.WithPropagators(propagator),
		otelhttp.WithSpanNameFormatter(func(_ string, r *http.Request) string {
			return r.Method + " /api/orders"
		})))
	return mux
}

func main() {
	logger := newLogger(os.Stdout)
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	// Standard OTEL exporter variables configure the real endpoint and TLS/auth.
	exporter, err := otlptracehttp.New(ctx, otlptracehttp.WithTimeout(5*time.Second))
	if err != nil {
		logger.Error("cannot configure trace exporter", "error", err)
		os.Exit(1)
	}
	provider := newProvider(exporter, 0.1)
	server := &http.Server{
		Addr:              "127.0.0.1:8080",
		Handler:           newHandler(provider, logger, os.Getenv("DEMO_DOWNSTREAM_URL"), http.DefaultTransport),
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	failed := make(chan error, 1)
	go func() { failed <- server.ListenAndServe() }()
	select {
	case err := <-failed:
		if !errors.Is(err, http.ErrServerClosed) {
			logger.Error("HTTP server failed", "error", err)
		}
	case <-ctx.Done():
	}
	shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(shutdown); err != nil {
		logger.Error("HTTP shutdown incomplete", "error", err)
	}
	// Use a fresh deadline so HTTP draining does not consume the exporter budget.
	flush, cancelFlush := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancelFlush()
	if err := provider.Shutdown(flush); err != nil {
		logger.Error("trace shutdown incomplete", "error", err)
	}
}
```

显式使用 `resource.NewSchemaless` 属性，避免语义约定 SchemaURL 冲突被悄然忽略。Provider/propagator 配置会传入 handler 和 transport。HTTP shutdown 与 exporter shutdown 使用独立的截止时间。依赖故障会记录错误 span 并返回 HTTP 502。

### Python

在 Python 3.12 上验证过的直接依赖：

```text
opentelemetry-sdk==1.44.0
opentelemetry-exporter-otlp-proto-http==1.44.0
opentelemetry-instrumentation-flask==0.65b0
opentelemetry-instrumentation-requests==0.65b0
Flask==3.1.3
requests==2.34.2
prometheus-client==0.26.0
```

```python
# app.py
"""Local correlation demo: OTLP traces, JSON stdout logs, OpenMetrics metrics."""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests
from flask import Flask, Response, g, jsonify, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST, generate_latest

SERVICE_NAME = "correlation-api"


class CorrelatedJSON(logging.Formatter):
    def format(self, record):
        result = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service_name": SERVICE_NAME,
        }
        context = trace.get_current_span().get_span_context()
        # Unsampled context can still be valid. Do not invent all-zero IDs.
        if context.is_valid:
            result.update(trace_id=f"{context.trace_id:032x}", span_id=f"{context.span_id:016x}")
        for key in ("method", "route", "status_code", "latency_ms"):
            if hasattr(record, key):
                result[key] = getattr(record, key)
        return json.dumps(result, ensure_ascii=False, allow_nan=False)


def make_provider(exporter, sample_ratio=0.1):
    if not 0 <= sample_ratio <= 1:
        raise ValueError("sample_ratio must be between zero and one")
    provider = TracerProvider(
        resource=Resource({
            "service.name": SERVICE_NAME,
            "service.version": "1.0.0",
            "deployment.environment.name": "demo",
        }),
        sampler=ParentBased(TraceIdRatioBased(sample_ratio)),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


def create_app(provider, log_stream=None, session=None, downstream_url=None):
    app = Flask(__name__)
    registry = CollectorRegistry()
    counts = Counter("http_requests_total", "Completed HTTP requests", ["method", "route", "status"], registry=registry)
    duration = Histogram("http_request_duration_seconds", "HTTP duration in seconds", ["method", "route", "status"], registry=registry)
    logger = logging.getLogger("correlation-demo")
    logger.handlers.clear()
    logger.propagate = False
    handler = logging.StreamHandler(log_stream if log_stream is not None else sys.stdout)
    handler.setFormatter(CorrelatedJSON())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    set_global_textmap(TraceContextTextMapPropagator())
    FlaskInstrumentor().instrument_app(app, tracer_provider=provider, excluded_urls="metrics,healthz")
    RequestsInstrumentor().instrument(tracer_provider=provider)
    tracer = provider.get_tracer("correlation-demo")
    client = session if session is not None else requests.Session()

    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def observe(response):
        route = request.url_rule.rule if request.url_rule is not None else "unmatched"
        if route in {"/metrics", "/healthz"}:
            return response
        elapsed = time.perf_counter() - g.started
        method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "_OTHER"
        status = str(response.status_code)
        context = trace.get_current_span().get_span_context()
        exemplar = {"trace_id": f"{context.trace_id:032x}"} if context.is_valid and context.trace_flags.sampled else None
        counts.labels(method, route, status).inc()
        duration.labels(method, route, status).observe(elapsed, exemplar=exemplar)
        logger.log(logging.ERROR if response.status_code >= 500 else logging.INFO, "request completed",
                   extra={"method": method, "route": route, "status_code": response.status_code, "latency_ms": round(elapsed * 1000, 3)})
        return response

    @app.get("/api/orders")
    def orders():
        with tracer.start_as_current_span("prepare-order-response") as span:
            span.set_attribute("app.operation", "orders.list")
            if downstream_url is not None:
                try:
                    # This URL comes from trusted configuration, not request input.
                    with client.get(downstream_url, timeout=(2, 5)) as response:
                        response.raise_for_status()
                except requests.RequestException as error:
                    span.record_exception(error)
                    span.set_status(Status(StatusCode.ERROR))
                    return jsonify(error="dependency unavailable"), 502
            # Demonstration data, not a real database query.
            return jsonify(orders=[{"id": "demo-1", "state": "ready"}])

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    return app, client


if __name__ == "__main__":
    # Configure the real OTLP endpoint/TLS/auth through standard exporter settings.
    provider = make_provider(OTLPSpanExporter(), sample_ratio=0.1)
    app, session = create_app(provider, downstream_url=os.environ.get("DEMO_DOWNSTREAM_URL"))
    try:
        # Local demonstration server. Use a proper WSGI server for deployment.
        app.run(host="127.0.0.1", port=8080, debug=False, use_reloader=False)
    finally:
        session.close()
        RequestsInstrumentor().uninstrument()
        provider.shutdown()
```

格式化器和 INFO 级别已实际配置。单独调用 `logging.info(..., extra=...)` 可能会被默认日志设置丢弃，也可能不会包含额外字段。有效但未采样的上下文仍会保留在日志中；没有上下文时不会生成虚构的全零 ID。

HTTP 语义属性取决于 instrumentation 版本和选择启用的设置。本次 Python 执行默认输出了 `http.method` 和 `http.status_code` 等兼容名称。应检查实际 span 属性，而不要仅仅因为 SDK 较新就更改所有查询。

标准 OTel exporter 设置用于指定真实端点。对于 HTTP/protobuf：

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc:4318
```

此地址假定已有 Collector Service。请另行配置部署所需的 TLS、身份验证和网络控制。请区分基础 endpoint 与已包含 `/v1/traces` 的特定信号 endpoint。

### Java JSON 日志

此 encoder 配置已使用 Logback 1.6.3、logstash-logback-encoder 9.0 和 JDK 21 进行检查。

```xml
<configuration>
  <!-- A configured OTel Java agent or MDC bridge must supply these MDC keys. -->
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <fieldNames>
        <timestamp>timestamp</timestamp>
      </fieldNames>
      <customFields>{"service_name":"correlation-api"}</customFields>
      <includeMdcKeyName>trace_id</includeMdcKeyName>
      <includeMdcKeyName>span_id</includeMdcKeyName>
    </encoder>
  </appender>
  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

必须先由已配置的 OTel Java agent 或 MDC bridge 填充 `trace_id`/`span_id`；仅靠 XML 不会启用 instrumentation。请确保 Java agent 的 service.name 与日志中使用的实际服务名称一致。测试通过提供 MDC 值验证了 encoder、允许列表中的键以及经过转义的多行 JSON。测试未执行 Java-agent 传播。

## 3. Collector 和后端连接

这些是**已部署组件的配置文件**。单独一个 ConfigMap 不会创建 Deployment、Service、RBAC 或后端。请使实际的 namespace、Service 名称和身份验证配置保持一致。

### Trace Collector

```yaml
# collector.yaml
# Trace gateway configuration only. Deploy a matching Collector Service and
# constrain network/authentication separately; this file does not install it.
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
    limit_mib: 256
    spike_limit_mib: 64
  batch:
    timeout: 1s
    send_batch_size: 512
exporters:
  otlphttp/tempo:
    endpoint: http://tempo-distributor.observability.svc:4318
    timeout: 5s
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlphttp/tempo]
```

此 gateway 仅处理 traces，采用内存限制和批处理，不配置不必要的通配符 CORS。若要进行 Kubernetes enrichment，请在批处理之前添加正确的 `k8sattributes` processor、Pod 关联和 RBAC。经由中间代理后的连接地址不一定能识别原始应用 Pod。

资源属性和传播请求头需要适当的信任边界；它们不能替代身份验证/授权身份。

### stdout 日志和 Alloy

Promtail 已于 2026 年 3 月 2 日结束生命周期（EOL）。此示例使用 Alloy 的 Kubernetes API 日志源。

```yaml
# log-reader-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: correlation-log-reader
  namespace: observability
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: correlation-log-reader
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
  name: correlation-log-reader
  namespace: observability
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: correlation-log-reader
subjects:
  - kind: ServiceAccount
    name: correlation-log-reader
    namespace: observability
```

在 namespace `observability` 中运行 Alloy，使用 `correlation-log-reader`，并将此配置放在实际配置路径下。目标 Pod 必须带有 `app=correlation-api` 标签。

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
    url = "http://loki.observability.svc:3100/loki/api/v1/push"
  }
}
```

Kubernetes API 日志与主机文件 tailing 是不同的输入。文件 tailing 需要适当处理 CRI/Docker framing、部分行和多行日志。将堆栈跟踪作为经过转义的换行符保存在同一个 JSON 事件中，可避免错误地拼接无关记录。

将 trace/request/user ID 保存在日志正文或适当的 structured metadata 中，而不要设为已索引的 Loki stream label。也应考虑 Pod/instance 标签带来的基数变化和保留问题。

不要重新使用已移除的 Collector `loki` exporter。对于原生 OTLP 日志，可选择使用指向 `http://<loki>/otlp` 的 `otlphttp` exporter，并将其连接到 logs pipeline，同时使用兼容的 Loki structured-metadata/schema 设置。这与上面的 stdout 日志路径不同。

### 指标和 exemplar 存储

```yaml
# prometheus.yaml
# Direct application scrape. HTTP/2 does not enable exemplar storage.
global:
  scrape_interval: 15s
rule_files:
  - recording-rules.yaml
scrape_configs:
  - job_name: correlation-api
    scrape_protocols: [OpenMetricsText1.0.0, PrometheusText0.0.4]
    static_configs:
      - targets: [correlation-api.observability.svc:8080]
        labels:
          service: correlation-api
          namespace: observability
storage:
  exemplars:
    max_exemplars: 10000
```

Prometheus 3.15 还需要设置 exemplar-storage feature。`enable_http2` 不会启用它。

```bash
prometheus --config.file=prometheus.yaml --enable-feature=exemplar-storage
```

将 recording-rule 文件放在配置文件旁边。应用会暴露 OpenMetrics，并且仅在上下文有效且已采样时附加 exemplars。采样、缓冲区替换和 Tempo 保留策略都可能导致找不到匹配的 trace。Exemplar 并不代表每次观测，也不一定对应确切的 P99 请求。

## 4. LogQL

查询使用此示例中的 `service_name`、大写 JSON 日志级别和已完成请求记录约定。通用的子串错误率并不自动等于失败请求率。

### 过滤和聚合

```logql
{service_name="correlation-api"} | json | level="ERROR" | __error__=""
```

```logql
sum by (service_name) (rate({service_name="correlation-api"} | json | message="request completed" | status_code>=500 | status_code<600 | __error__="" [5m]))
```

```logql
sum by (service_name) (count_over_time({service_name="correlation-api"} | json | level="ERROR" | __error__="" [1h]))
```

`rate` 返回行/秒；`count_over_time` 统计每个范围内的行数。需要汇总多个 stream 时进行聚合。`|=` 是区分大小写的子串匹配，并非结构化严重性检查。

### 延迟和解析器错误

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

JSON 解析、数值比较和 unwrap 都可能产生错误，因此必须在正确的位置添加 `__error__=""` 过滤器。这些查询会先验证 `latency_ms>=0`。针对 Loki 3.7.8 中有效的 10ms/800ms 值、一个非数值值和格式错误的 JSON 进行测试后，修正后的查询返回了平均值 405ms 和 P95 760.5ms。

这些是对 unwrap 值进行的范围聚合，不是 Prometheus 直方图 bucket。按不受限制的 message 或原始 URL 分组也可能导致查询结果的基数过高。

### Trace 查询

```logql
{service_name="correlation-api"} | json | trace_id="0af7651916cd43dd8448eb211c80319c" | __error__=""
```

请检查 regex/pattern/JSON parser 的错误。第二个 `| json` 不会自动解析某个特定的嵌套 JSON 字符串；应提取目标字段，或在再次解析前转换日志行。

### Loki Ruler

```yaml
# loki-rules.yaml
# Native Loki Ruler file. Store through the configured Ruler backend/API.
# This is not a PrometheusRule CRD and not a Grafana Alerting provisioning file.
groups:
  - name: correlation.logs
    rules:
      - alert: CompletedRequestErrorLogsHigh
        expr: |
          sum by (service_name) (
            rate({service_name="correlation-api"} | json
              | message="request completed" | status_code>=500 | __error__="" [5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High completed-request error log rate
          description: '{{ $labels.service_name }} emitted {{ printf "%.2f" $value }} matching log lines/s.'
```

将此原生规则文件连接到 Loki Ruler storage/API。Prometheus 无法评估放在 PrometheusRule CRD 中的 LogQL。Grafana Alerting provisioning 使用另一套 schema 和 `apiVersion` 约定。

累计摄取计数器等于零，并不能检测摄取是否停滞。应结合近期速率、预期输入、Collector 错误、背压和存储故障进行分析。在没有预期输入时，存储活动为零本身不能证明发生了中断。

## 5. PromQL 和指标单位

```yaml
# recording-rules.yaml
groups:
  - name: correlation.red
    interval: 30s
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (namespace, service) (rate(http_requests_total[5m]))
      - record: service:http_errors:rate5m
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[5m]))
          or on (namespace, service) (0 * service:http_requests:rate5m)
      - record: service:http_error_ratio:rate5m
        expr: service:http_errors:rate5m / (service:http_requests:rate5m > 0)
      - record: service:http_latency_p99:seconds
        expr: |
          histogram_quantile(0.99,
            sum by (namespace, service, le) (rate(http_request_duration_seconds_bucket[5m]))
          )
      - record: service:http_latency_mean:seconds
        expr: |
          sum by (namespace, service) (rate(http_request_duration_seconds_sum[5m]))
          /
          (sum by (namespace, service) (rate(http_request_duration_seconds_count[5m])) > 0)
```

聚合经典直方图 bucket 时保留 `le`。如果错误 series 不存在，请针对该服务实际的请求 series 补零。如果请求数也为零，不要虚构一个健康的零错误率。使 recording-rule 单位与 dashboard 的 `s`、`percentunit` 和 `reqps` 保持一致。

根据问题选择适当的 counter rate/increase。对累计计数器求 30 天平均值，得不出平均 RPS。平均值、样本百分位数和直方图分位数是不同的统计量。

Istio 的 source 和 destination reporter 可能会重复观测。请选择所需视角，例如：

```promql
sum by (cluster, destination_service_namespace, destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)
```

请区分 Istio 的毫秒级 duration 与应用的秒级 duration。根据观测到的 L7 请求计算出的 mTLS 比率，不能证明所有 L4 流量都遵循加密策略。Ambient 安装需要实际的 L7 telemetry 路径，并在适用时满足 waypoint 要求。

CloudWatch exporter 的 `_sum` 可能是周期统计 gauge，而不是单调递增的 counter。不要盲目应用 `rate()`。将 60 秒 RequestCount Sum 转换为 RPS 时，必须检查周期、exporter 时间戳/延迟和重复 series。不同 exporter 的前缀和标签可能不同。

AMP 查询的是已摄取到某个 workspace 的数据。它不会自动摄取 CloudWatch 数据、联邦连接 workspace/Region，也不会创建 `up{job="amp-remote-write"}` target。请检查实际的 remote-write 队列/错误以及受支持的 AMP 摄取 telemetry。

## 6. TraceQL

这些查询已根据 Tempo 3.0.3 文档和 Grafana 官方语法进行了检查。属性名称必须与实际 instrumentation schema 一致。

```traceql
{ resource.service.name = "correlation-api" }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 500ms }
```

```traceql
{ trace:duration > 2s }
```

`span:duration` 表示 span 持续时间；`trace:duration` 覆盖整个 trace。`span:name` 等 intrinsic 与名为 `span.name` 的用户属性不同。

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span.http.status_code >= 500 }
```

Go 执行输出了 `http.request.method` 和 `http.response.status_code`。Go 后端请使用以下查询。

```traceql
{ resource.service.name = "correlation-api" && span.http.response.status_code >= 500 }
```

错误状态并不等同于 HTTP 500。Python 演示默认输出 `http.status_code`；若选择启用较新的约定，请将查询更新为实际属性，例如 `http.response.status_code`。

### 关系和聚合

```traceql
{ span:kind = server } > { span:name = "prepare-order-response" }
```

```traceql
{ span:kind = server } >> { span:status = error }
```

```traceql
{ span:name = "check-stock" } ~ { span:name = "check-payment" }
```

`>` 选择直接子项，`>>` 选择任意深度的后代，`<` 选择直接父项，`~` 选择共享同一父项的兄弟项。仅选择某个服务的 client/server span，不会自动映射每个 peer。

```traceql
{ resource.service.name = "correlation-api" } | by(span:name) | count() > 1
```

span 名称重复本身并不能证明发生了重试。避免使用 `{ }*` 等不受支持的重复语法；应使用 trace ID 查询和显式结构查询。

```traceql
{ resource.service.name = "correlation-api" } | quantile_over_time(duration, 0.99)
```

这会返回 TraceQL metric series，而不是慢速独立 trace 的列表。请验证查询模式以及 Tempo 部署的功能/数据路径。服务图需要受支持的生成方式/processor，以及相应的存储/查询配置。

对于 `traces_service_graph_request_total` 等生成的指标，应在指标后端使用 **PromQL** 查询。client/server span 配对和采样可能导致图表不完整。旧的 `processor.*.enabled=true` 片段并不构成完整的当前 Tempo 配置。

## 7. Grafana 数据源和 Dashboard

```yaml
# datasources.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: http://prometheus.observability.svc:9090
    jsonData:
      httpMethod: POST
      exemplarTraceIdDestinations:
        - name: trace_id
          datasourceUid: tempo
          urlDisplayLabel: View trace
  - name: Loki
    uid: loki
    type: loki
    access: proxy
    url: http://loki.observability.svc:3100
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"trace_id"\s*:\s*"([0-9a-f]{32})"'
          datasourceUid: tempo
          url: '$${__value.raw}'
          urlDisplayLabel: View trace
  - name: Tempo
    uid: tempo
    type: tempo
    access: proxy
    url: http://tempo-query-frontend.observability.svc:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        spanStartTimeShift: "-5m"
        spanEndTimeShift: "5m"
        tags:
          - key: service.name
            value: service_name
        filterByTraceID: true
        filterBySpanID: false
        customQuery: false
      tracesToMetrics:
        datasourceUid: prometheus
        spanStartTimeShift: "-5m"
        spanEndTimeShift: "5m"
        tags:
          - key: service.name
            value: service
        queries:
          - name: Request rate
            query: 'sum(rate(http_requests_total{$$__tags}[5m]))'
```

三个 UID 都是显式指定的，且引用相互匹配。Exemplar `trace_id`、JSON `trace_id` 和 Loki derived field 采用相同的命名约定。此 regex 接受 JSON 空格，并且只捕获恰好 32 个十六进制字符。

在 provisioning YAML 中，对于 `${__value.raw}` 和 `__tags` 等宏，应将 `$` 写成 `$$`。内部 Tempo 链接接收原始 trace ID 查询；不要将它与无关的手工构造 Explore URL 混用。

`tracesToLogsV2` 将 trace resource `service.name` 映射到 Loki 标签 `service_name`。查看整个 trace 的日志时，避免不必要地按 span ID 限制结果。请为部署配置 tenancy、TLS/身份验证和真实 Service URL。

### 文件 provisioning 格式

```yaml
# dashboard-provider.yaml
apiVersion: 1
providers:
  - name: correlation
    orgId: 1
    folder: Observability
    type: file
    disableDeletion: true
    allowUiUpdates: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards/correlation
```

将 datasource 文件挂载到 Grafana 的 datasource provisioning 路径，将 provider 文件挂载到其 dashboard provisioning 路径，并将 JSON 挂载到 provider 配置的目录中。仅创建 ConfigMap 不会将这些文件接入 Grafana。

```json
{
  "id": null,
  "uid": "correlation-demo",
  "title": "Service correlation demo",
  "tags": [
    "observability",
    "correlation"
  ],
  "timezone": "browser",
  "schemaVersion": 41,
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [
    {
      "id": 1,
      "title": "Request rate",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "service:http_requests:rate5m{service=\"correlation-api\",namespace=\"observability\"}",
          "legendFormat": "{{service}}",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps",
          "min": 0
        },
        "overrides": []
      },
      "options": {
        "legend": {
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      }
    },
    {
      "id": 2,
      "title": "HTTP error ratio",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": {
        "x": 8,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "service:http_error_ratio:rate5m{service=\"correlation-api\",namespace=\"observability\"}",
          "legendFormat": "{{service}}",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0
        },
        "overrides": []
      },
      "options": {
        "legend": {
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      }
    },
    {
      "id": 3,
      "title": "P99 latency",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": {
        "x": 16,
        "y": 0,
        "w": 8,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "service:http_latency_p99:seconds{service=\"correlation-api\",namespace=\"observability\"}",
          "legendFormat": "{{service}}",
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s",
          "min": 0
        },
        "overrides": []
      },
      "options": {
        "legend": {
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      }
    },
    {
      "id": 4,
      "title": "Request histogram with trace exemplars",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (le) (rate(http_request_duration_seconds_bucket{service=\"correlation-api\",namespace=\"observability\"}[5m]))",
          "legendFormat": "le={{le}}",
          "exemplar": true,
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          }
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps",
          "min": 0
        },
        "overrides": []
      },
      "options": {
        "legend": {
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      }
    },
    {
      "id": 5,
      "title": "Correlated application logs",
      "type": "logs",
      "datasource": {
        "type": "loki",
        "uid": "loki"
      },
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 24,
        "h": 9
      },
      "targets": [
        {
          "refId": "A",
          "expr": "{namespace=\"observability\",service_name=\"correlation-api\"}",
          "queryType": "range",
          "datasource": {
            "type": "loki",
            "uid": "loki"
          }
        }
      ],
      "options": {
        "showTime": true,
        "showLabels": false,
        "wrapLogMessage": true,
        "sortOrder": "Descending"
      }
    }
  ],
  "templating": {
    "list": []
  },
  "annotations": {
    "list": []
  }
}
```

文件 provisioning 直接使用 dashboard 对象本身，不需要 HTTP API 的 `{"dashboard": ...}` 包装。此示例使用固定服务和显式 UID，而不是未定义变量。

请使用当前的 `timeseries` panel，而非旧版 `graph` panel。累计直方图 bucket 曲线与 heatmap 的逐 bucket 分布不同。不要将原始 trace 搜索结果标记为“Active Traces”计数，也不要假定它们是 service-map data frame。

添加变量时，请使用实际指标中存在的标签。多选/All 值需要适当的 regex 转义/运算符，不能假定它们是单字符串。请测试每个数据源的查询语法。

## 验证范围

SDK 测试构造了显式的内存导出器和伪造 HTTP transport，没有使用外部 OTLP exporter。仅在这些隔离测试中启用了 recording，且没有继承个人 endpoint 或资源属性。

已检查 Collector/Alloy 原生配置验证、本地 Loki 查询结果、Prometheus recording-rule 计算、Java 编码、Trace-ID regex 和 UID 引用。TraceQL 语法验证不能代替实际的 Tempo ingest/search；Grafana UI、后端身份验证和部署也需要单独在目标环境中验证。

## 参考资料

- [OpenTelemetry Go 1.46](https://github.com/open-telemetry/opentelemetry-go/releases/tag/v1.46.0)
- [Loki 原生 OTLP](https://grafana.com/docs/loki/latest/send-data/otel/)
- [Promtail EOL](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3.0.3 TraceQL](https://github.com/grafana/tempo/blob/v3.0.3/docs/sources/tempo/traceql/construct-traceql-queries.md)
- [Grafana Tempo provisioning](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/provision/)
- [Grafana Loki 配置](https://grafana.com/docs/grafana/latest/datasources/loki/configure/)
- [章节测验](../quizzes/ops/08-observability-analysis-quiz.md)

< [上一章：运维告警](07-observability-alerts.md) | [目录](README.md) | [下一章：堆栈运维](09-observability-stack.md) >
