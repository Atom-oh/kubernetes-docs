# Observability Analysis: Logs, Metrics and Traces

> **Review baseline**: OTel Go 1.46.0 / otelhttp 0.71.0, Python SDK 1.44.0 / instrumentation 0.65b0, Collector 0.160.0, Alloy 1.19.2, Loki 3.7.7, Tempo 3.0.3, Grafana 13.2.1\
> **Last reviewed**: September 11, 2026. SDK/log/exemplar behavior was tested with in-memory exporters and HTTP test doubles; LogQL was exercised against synthetic logs in local Loki. No data was exported to a real cluster or external telemetry backend.

< [Previous: Operational Alerts](07-observability-alerts.md) | [Contents](README.md) | [Next: Stack Operations](09-observability-stack.md) >

Correlation connects evidence about the same time, service and request. Coincidence alone does not establish root cause. Check missing data, sampling and retention, then validate a hypothesis.

## 1. Identifiers and Actual Transport Paths

| Signal | Path used in this chapter | Correlation contract |
|---|---|---|
| Traces | SDK → OTLP/HTTP Collector → Tempo | W3C context and `service.name` |
| Logs | JSON stdout → Alloy Kubernetes log source → Loki | JSON `trace_id` and `span_id` |
| Metrics | Prometheus client → `/metrics` OpenMetrics scrape | Exemplar `trace_id` |
| Queries | Grafana → each data source | Explicit UIDs and label mappings |

A trace exporter does not automatically turn stdout logs or Prometheus-client metrics into OTLP. Sending every signal through OTLP requires the corresponding SDK exporters/collectors and pipelines. Tempo also does not automatically join the log and metric stores.

### W3C and B3

```text
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

W3C trace IDs use 32 hex characters and parent span IDs use sixteen; all-zero identifiers are invalid. Flags carry information such as the sampled bit. A valid ID or sampled flag does not guarantee backend storage or retention.

B3 is another supported propagation format, with 64-bit and 128-bit trace IDs. If accepting multiple formats, define precedence for conflicting headers and the ingress trust boundary. These examples use W3C TraceContext only. Do not indiscriminately propagate sensitive values in baggage.

## 2. Executable SDK Examples

Go and Python are **alternative implementations** of the same log/metric contract. Do not start both on the same port. Their main entry points are loopback-bound local demos; use the appropriate application server, Service and binding configuration when deploying.

The shared service is `correlation-api`. JSON contains `timestamp`, `level`, `message`, `service_name`, bounded `route`, `status_code`, `latency_ms`, and valid trace/span IDs. Do not turn raw URLs or user identifiers into ordinary metric labels.

### Go

Use a supported patched Go 1.25+ environment. Local compilation in this review used Go 1.25.0, which is separate from choosing an appropriate production patch release.

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

Explicit `resource.NewSchemaless` attributes avoid silently ignoring conflicts between semantic-convention SchemaURLs. Provider/propagator configuration is passed to the handler and transport. HTTP shutdown and exporter shutdown have separate deadlines. Dependency failure records error spans and returns HTTP 502.

### Python

Direct dependencies validated on Python 3.12:

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

The formatter and INFO level are actually configured. `logging.info(..., extra=...)` alone can be dropped by default logging settings or omit the extra fields. Valid unsampled context is retained in logs; absent context does not produce invented all-zero IDs.

HTTP semantic attributes depend on instrumentation version and opt-in settings. This Python execution emitted compatibility names such as `http.method` and `http.status_code` by default. Inspect actual span attributes rather than changing every query merely because the SDK is new.

Standard OTel exporter settings supply the real endpoint. For HTTP/protobuf:

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc:4318
```

The address assumes an existing Collector Service. Configure the deployment's TLS, authentication and network controls separately. Distinguish the base endpoint from signal-specific endpoints already containing `/v1/traces`.

### Java JSON logging

This encoder configuration was checked with Logback 1.6.3, logstash-logback-encoder 9.0 and JDK 21.

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

A configured OTel Java agent or MDC bridge must first populate `trace_id`/`span_id`; the XML alone does not enable instrumentation. Align the Java agent service.name with the actual service name used by the logs. The test supplied MDC values to validate the encoder, allowlisted keys and escaped multiline JSON. It did not execute Java-agent propagation.

## 3. Collectors and Backend Wiring

These are **configuration files for deployed components**. A ConfigMap alone does not create a Deployment, Service, RBAC or backend. Align actual namespaces, Service names and authentication.

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

This gateway handles traces only, using memory limiting and batching without unnecessary wildcard CORS. For Kubernetes enrichment, add the correct `k8sattributes` processor, pod association and RBAC before batching. A connection address after an intermediary proxy does not necessarily identify the original application Pod.

Resource attributes and propagation headers require an appropriate trust boundary; they do not replace authentication/authorization identities.

### Stdout logs and Alloy

Promtail reached EOL on March 2, 2026. The example uses Alloy's Kubernetes API log source.

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

Run Alloy in namespace `observability` using `correlation-log-reader`, with this configuration supplied at the actual config path. Target Pods must carry `app=correlation-api`.

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

Kubernetes API logs and host-file tailing are different inputs. File tailing needs the appropriate CRI/Docker framing, partial-line and multiline handling. Keeping a stack trace as escaped newlines inside one JSON event avoids incorrectly joining unrelated records.

Keep trace/request/user IDs in log bodies or appropriate structured metadata, not indexed Loki stream labels. Consider churn and retention for Pod/instance labels too.

Do not reuse the removed Collector `loki` exporter. An alternative for native OTLP logs is an `otlphttp` exporter targeting `http://<loki>/otlp`, connected to a logs pipeline and compatible Loki structured-metadata/schema settings. That is distinct from the stdout-log path above.

### Metrics and exemplar storage

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

Prometheus 3.14 also requires the exemplar-storage feature setting. `enable_http2` does not enable it.

```bash
prometheus --config.file=prometheus.yaml --enable-feature=exemplar-storage
```

Keep the recording-rule file beside the configuration. The applications expose OpenMetrics and attach exemplars only for valid sampled context. Sampling, buffer replacement and Tempo retention can leave no matching trace. An exemplar does not represent every observation or necessarily the exact P99 request.

## 4. LogQL

Queries use this example's `service_name`, uppercase JSON levels and completed-request record contract. A generic substring-error ratio is not automatically a failed-request ratio.

### Filtering and aggregation

```logql
{service_name="correlation-api"} | json | level="ERROR" | __error__=""
```

```logql
sum by (service_name) (rate({service_name="correlation-api"} | json | message="request completed" | status_code>=500 | status_code<600 | __error__="" [5m]))
```

```logql
sum by (service_name) (count_over_time({service_name="correlation-api"} | json | level="ERROR" | __error__="" [1h]))
```

`rate` returns lines/s; `count_over_time` counts lines within each range. Aggregate when totals across streams are required. `|=` is case-sensitive substring matching, not a structured severity check.

### Latency and parser errors

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

JSON parsing, numeric comparison and unwrap can introduce errors, requiring correctly placed `__error__=""` filters. These queries first validate `latency_ms>=0`. Against Loki 3.7.7 with valid 10ms/800ms values, a nonnumeric value and malformed JSON, the corrected queries returned mean 405ms and P95 760.5ms.

These are range aggregations of unwrapped values, not Prometheus histogram buckets. Grouping by unrestricted messages or raw URLs can also cause high query-result cardinality.

### Trace lookup

```logql
{service_name="correlation-api"} | json | trace_id="0af7651916cd43dd8448eb211c80319c" | __error__=""
```

Check errors from regex/pattern/JSON parsers. A second `| json` does not automatically parse a particular nested JSON string; extract the intended field or transform the line before parsing it again.

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

Connect this native rule file to Loki Ruler storage/API. Prometheus cannot evaluate LogQL placed in a PrometheusRule CRD. Grafana Alerting provisioning uses another schema and `apiVersion` contract.

A cumulative ingestion counter equal to zero does not detect stalled ingestion. Correlate recent rates, expected input, collector errors, backpressure and storage failures. Zero storage activity without expected input does not alone establish an outage.

## 5. PromQL and Metric Units

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

Preserve `le` when aggregating classic histogram buckets. If an error series does not exist, fill zero against that service's actual request series. If requests are also zero, do not invent a healthy zero error ratio. Match recording-rule units with dashboard `s`, `percentunit` and `reqps`.

Use counter rates/increases appropriate to the question. Averaging a cumulative counter over thirty days does not yield average RPS. Means, sample percentiles and histogram quantiles are different statistics.

Istio source and destination reporters can duplicate observations. Select the desired viewpoint, for example:

```promql
sum by (cluster, destination_service_namespace, destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)
```

Distinguish Istio duration milliseconds from application seconds. An mTLS ratio over observed L7 requests is not proof of encryption policy for all L4 traffic. Ambient installations need the actual L7 telemetry path, including waypoint requirements where applicable.

A CloudWatch exporter's `_sum` may be a period-statistic gauge rather than a monotonic counter. Do not blindly apply `rate()`. Converting a 60-second RequestCount Sum to RPS requires checking the period, exporter timestamp/delay and duplicate series. Prefixes and labels vary by exporter.

AMP queries data ingested into a workspace. It does not automatically ingest CloudWatch, federate workspaces/Regions, or create an `up{job="amp-remote-write"}` target. Inspect actual remote-write queue/errors and supported AMP ingestion telemetry.

## 6. TraceQL

These queries were checked against Tempo 3.0.3 documentation and Grafana's official grammar. Attribute names must match the real instrumentation schema.

```traceql
{ resource.service.name = "correlation-api" }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 500ms }
```

```traceql
{ trace:duration > 2s }
```

`span:duration` is a span duration; `trace:duration` covers the whole trace. Intrinsics such as `span:name` differ from a user attribute named `span.name`.

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span.http.status_code >= 500 }
```

The Go execution emitted `http.request.method` and `http.response.status_code`. Use the following query for that Go backend.

```traceql
{ resource.service.name = "correlation-api" && span.http.response.status_code >= 500 }
```

Error status is not identical to HTTP 500. The Python demo emitted `http.status_code` by default; when opting into newer conventions, update queries to actual attributes such as `http.response.status_code`.

### Relationships and aggregations

```traceql
{ span:kind = server } > { span:name = "prepare-order-response" }
```

```traceql
{ span:kind = server } >> { span:status = error }
```

```traceql
{ span:name = "check-stock" } ~ { span:name = "check-payment" }
```

`>` selects direct children, `>>` descendants at arbitrary depth, `<` direct parents and `~` siblings sharing a parent. Selecting client/server spans of one service does not automatically map every peer.

```traceql
{ resource.service.name = "correlation-api" } | by(span:name) | count() > 1
```

Repeated span names alone do not prove retries. Avoid unsupported repetition syntax such as `{ }*`; use trace-ID lookup and explicit structural queries.

```traceql
{ resource.service.name = "correlation-api" } | quantile_over_time(duration, 0.99)
```

This returns TraceQL metric series, not a list of slow individual traces. Verify the query mode and the Tempo deployment's feature/data path. Service graphs require a supported generation/processor and storage/query configuration.

Generated metrics such as `traces_service_graph_request_total` are queried with **PromQL** in the metric backend. Client/server span pairing and sampling can make graphs incomplete. Old `processor.*.enabled=true` fragments do not constitute a complete current Tempo configuration.

## 7. Grafana Data Sources and Dashboard

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

All three UIDs are explicit and references match. The exemplar `trace_id`, JSON `trace_id` and Loki derived field share a naming contract. The regex accepts JSON spacing and captures exactly 32 hex characters.

Preserve `$` as `$$` in provisioning YAML for macros such as `${__value.raw}` and `__tags`. An internal Tempo link receives a raw trace-ID query; do not combine that with an unrelated hand-built Explore URL.

`tracesToLogsV2` maps trace resource `service.name` to Loki label `service_name`. Avoid unnecessarily restricting span ID when viewing an entire trace's logs. Configure tenancy, TLS/authentication and real Service URLs for the deployment.

### File provisioning format

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

Mount the datasource file into Grafana's datasource provisioning path, the provider file into its dashboard provisioning path, and the JSON into the provider's configured directory. Creating a ConfigMap alone does not wire these files into Grafana.

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

File provisioning consumes the dashboard object itself, without the HTTP API's `{"dashboard": ...}` wrapper. The example uses a fixed service and explicit UIDs instead of undefined variables.

Use current `timeseries` panels rather than the legacy `graph` panel. Cumulative histogram bucket curves differ from a heatmap's per-bucket distribution. Do not label raw trace-search results as an “Active Traces” count or assume they are a service-map data frame.

When adding variables, use labels that exist in the actual metrics. Multi/All values need appropriate regex escaping/operators rather than single-string assumptions. Test each data source's query syntax.

## Validation Scope

The SDK tests constructed explicit in-memory exporters and fake HTTP transports, without external OTLP exporters. Recording was enabled only inside those isolated tests, with no inherited personal endpoints or resource attributes.

Collector/Alloy native validation, local Loki query results, Prometheus recording-rule calculations, Java encoding, Trace-ID regexes and UID references were checked. TraceQL grammar validation does not substitute for actual Tempo ingest/search, and Grafana UI, backend authentication and deployment require separate environment validation.

## References

- [OpenTelemetry Go 1.46](https://github.com/open-telemetry/opentelemetry-go/releases/tag/v1.46.0)
- [Loki native OTLP](https://grafana.com/docs/loki/latest/send-data/otel/)
- [Promtail EOL](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3.0.3 TraceQL](https://github.com/grafana/tempo/blob/v3.0.3/docs/sources/tempo/traceql/construct-traceql-queries.md)
- [Grafana Tempo provisioning](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/provision/)
- [Grafana Loki configuration](https://grafana.com/docs/grafana/latest/datasources/loki/configure/)
- [Chapter quiz](../quizzes/ops/08-observability-analysis-quiz.md)

< [Previous: Operational Alerts](07-observability-alerts.md) | [Contents](README.md) | [Next: Stack Operations](09-observability-stack.md) >
