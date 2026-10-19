# 可観測性分析：ログ、メトリクス、トレース

> **確認対象の基準バージョン**: OTel Go 1.46.0 / otelhttp 0.71.0、Python SDK 1.44.0 / instrumentation 0.65b0、Collector 0.162.0、Alloy 1.20.1、Loki 3.7.8、Tempo 3.0.3、Grafana 13.2.4\
> **最終確認日**: 2026年10月16日。SDK／ログ／exemplarの動作はメモリ内exporterとHTTPテスト用スタブで検証し、LogQLはローカルLoki上の合成ログで実行しました。実クラスターや外部テレメトリバックエンドにはデータを送信していません。

< [前へ：運用アラート](07-observability-alerts.md) | [目次](README.md) | [次へ：スタック運用](09-observability-stack.md) >

相関付けでは、同じ時刻、サービス、リクエストに関する証拠を結び付けます。同時に起きたというだけでは、根本原因を特定したことにはなりません。データの欠落、サンプリング、保持期間を確認したうえで、仮説を検証してください。

## 1. 識別子と実際のデータ経路

| シグナル | 本章で使用する経路 | 相関付けに使う識別子 |
|---|---|---|
| トレース | SDK → OTLP/HTTP Collector → Tempo | W3C context と `service.name` |
| ログ | JSON stdout → Alloy Kubernetes log source → Loki | JSON の `trace_id` と `span_id` |
| メトリクス | Prometheus client → `/metrics` OpenMetrics scrape | exemplar の `trace_id` |
| クエリ | Grafana → 各データソース | 明示的な UID とラベルの対応付け |

トレースexporterを使っても、stdoutのログやPrometheus clientのメトリクスが自動的にOTLPへ変換されるわけではありません。すべてのシグナルをOTLPで送るには、それぞれに対応するSDK exporter／collectorとpipelineが必要です。Tempoも、ログストアやメトリクスストアを自動的に結合しません。

### W3C と B3

```text
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

W3Cのtrace IDは32桁、親span IDは16桁の16進数で、すべてゼロの識別子は無効です。フラグにはサンプリング済みを示すビットなどが含まれます。有効なIDやサンプリング済みフラグがあっても、バックエンドへの保存やデータ保持が保証されるわけではありません。

B3もサポートされる伝播形式で、64ビットまたは128ビットのtrace IDを使えます。複数形式を受け入れる場合は、ヘッダーが競合したときの優先順位と、ingressでの信頼境界を定義してください。ここでの例はW3C Trace Contextのみを使用します。baggageに機密情報を無差別に含めてはいけません。

## 2. 実行可能な SDK の例

GoとPythonは、同じログ／メトリクス契約を実装する**代替例**です。同じポートで両方を起動しないでください。主なエントリポイントはループバックにbindするローカルデモです。デプロイ時は、適切なアプリケーションサーバー、Service、bind設定を使用してください。

共通のService名は `correlation-api` です。JSONには `timestamp`、`level`、`message`、`service_name`、値を限定した `route`、`status_code`、`latency_ms`、有効なtrace／span IDを含めます。生のURLやユーザー識別子を通常のメトリクスラベルにしないでください。

### Go

サポート対象のパッチが適用されたGo 1.25以降の環境を使用してください。このレビューでローカルコンパイルに使用したのはGo 1.25.0ですが、これは本番環境に適切なパッチリリースを選ぶこととは別です。

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

明示的な `resource.NewSchemaless` 属性を使うと、Semantic ConventionのSchemaURL間にある競合が黙って無視されるのを防げます。Providerとpropagatorの設定はhandlerとtransportに渡します。HTTPサーバーの停止とexporterの停止には、それぞれ別のdeadlineを設定しています。依存サービスの障害時にはエラースパンを記録し、HTTP 502を返します。

### Python

Python 3.12で検証した直接依存関係:

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

formatterとINFOレベルは実際に設定されています。`logging.info(..., extra=...)` を呼ぶだけでは、標準のlogging設定で記録が破棄されたり、追加フィールドが出力されなかったりすることがあります。有効な未サンプリングcontextはログに保持し、contextがない場合にすべてゼロのIDを捏造しません。

HTTPのSemantic Convention属性は、計装のバージョンとopt-in設定によって異なります。このPython実行では、デフォルトで `http.method` や `http.status_code` などの互換名が出力されました。SDKが新しいという理由だけでクエリを一律に変えず、実際のspan属性を確認してください。

標準のOTel exporter設定で実際のendpointを指定します。HTTP/protobufを使う場合:

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc:4318
```

このアドレスは、Collector Serviceがすでに存在することを前提としています。デプロイ時のTLS、認証、ネットワーク制御は別途設定してください。ベースendpointと、すでに `/v1/traces` を含むシグナル別endpointを区別してください。

### Java の JSON ログ

このencoder設定は、Logback 1.6.3、logstash-logback-encoder 9.0、JDK 21で確認しました。

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

設定済みのOTel Java agentまたはMDC bridgeが、まず `trace_id`／`span_id` を設定する必要があります。このXMLだけでは計装は有効になりません。Java agentの service.name を、ログで実際に使うサービス名に合わせてください。テストではMDCの値を設定し、encoder、許可リストに登録したキー、改行をエスケープした複数行JSONを検証しました。Java agentによる伝播は実行していません。

## 3. Collector とバックエンドの接続

以下は**デプロイ済みコンポーネント用の設定ファイル**です。ConfigMapだけではDeployment、Service、RBAC、バックエンドは作成されません。実際のnamespace、Service名、認証設定に合わせてください。

### トレース Collector

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

このgatewayはトレースのみを扱い、不要なワイルドカードCORSを使わずにメモリ制限とbatch処理を行います。Kubernetes情報を付与するには、batch処理の前に適切な `k8sattributes` processor、Pod association、RBACを追加してください。中間proxyを経由した接続元アドレスが、元のアプリケーションPodを示すとは限りません。

Resource属性と伝播ヘッダーには適切な信頼境界が必要です。これらは認証／認可に使うIDの代わりにはなりません。

### stdout ログと Alloy

Promtailは2026年3月2日にEOLを迎えました。この例ではAlloyのKubernetes API log sourceを使います。

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

実際のconfig pathに設定を配置し、namespace `observability` で `correlation-log-reader` を使ってAlloyを実行してください。対象Podには `app=correlation-api` ラベルが必要です。

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

Kubernetes APIから取得するログと、ホスト上のファイルをtailするログは別の入力経路です。ファイルをtailする場合は、適切なCRI／Docker framingと、部分行・複数行の処理が必要です。スタックトレースをエスケープ済み改行を含む1つのJSONイベントとして保持すれば、無関係なレコード同士を誤って結合するのを防げます。

trace／request／user IDはログ本文または適切なstructured metadataに保持し、Lokiのindexed stream labelにはしないでください。Pod／instanceラベルについても、値の変動と保持への影響を考慮してください。

削除されたCollectorの `loki` exporterを再利用しないでください。ネイティブOTLPログを送る方法として、`http://<loki>/otlp` を宛先とする `otlphttp` exporterをlogs pipelineに接続し、Lokiのstructured metadata／schema設定との互換性を確認して使う方法があります。これは前述のstdoutログ経路とは別の方式です。

### メトリクスと exemplar の保存

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

Prometheus 3.15では、exemplar storageのfeature設定も必要です。`enable_http2` を有効にしても、exemplar storageは有効になりません。

```bash
prometheus --config.file=prometheus.yaml --enable-feature=exemplar-storage
```

recording-ruleファイルは設定ファイルの隣に置いてください。アプリケーションはOpenMetricsを公開し、有効なサンプリング済みcontextがある場合に限ってexemplarを付加します。サンプリング、bufferの置き換え、Tempoの保持期間によって、対応するトレースが残らないことがあります。exemplarはすべての観測値を表すものではなく、必ずしもP99のリクエストそのものでもありません。

## 4. LogQL

クエリは、この例の `service_name`、大文字のJSON level、完了済みリクエストのrecord契約に合わせています。部分文字列に対する一般的なerror比率が、失敗したリクエストの比率と一致するとは限りません。

### フィルタリングと集約

```logql
{service_name="correlation-api"} | json | level="ERROR" | __error__=""
```

```logql
sum by (service_name) (rate({service_name="correlation-api"} | json | message="request completed" | status_code>=500 | status_code<600 | __error__="" [5m]))
```

```logql
sum by (service_name) (count_over_time({service_name="correlation-api"} | json | level="ERROR" | __error__="" [1h]))
```

`rate` は1秒あたりのログ行数を返し、`count_over_time` は各時間範囲内の行数を数えます。複数のstream全体の合計が必要な場合は集約してください。`|=` は大文字小文字を区別する部分文字列検索であり、構造化されたseverity判定ではありません。

### レイテンシとパーサーエラー

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

JSON解析、数値比較、unwrapでエラーが発生することがあるため、`__error__=""` を適切な位置でfilterする必要があります。以下のクエリは、まず `latency_ms>=0` を検証します。Loki 3.7.8で10ms／800msの有効値、数値でない値、不正なJSONを使って試したところ、修正後のクエリは平均405ms、P95 760.5msを返しました。

これらはunwrapした値を時間範囲ごとに集約するもので、Prometheusのhistogram bucketではありません。制限のないmessageや生URLでgroup化すると、クエリ結果のcardinalityも高くなる可能性があります。

### トレース検索

```logql
{service_name="correlation-api"} | json | trace_id="0af7651916cd43dd8448eb211c80319c" | __error__=""
```

regex／pattern／JSON parserのエラーを確認してください。2回目の `| json` を追加しても、特定の入れ子JSON文字列が自動的に解析されるわけではありません。必要なfieldを抽出するか、再解析の前に行を変換してください。

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

このネイティブruleファイルをLoki Rulerのstorage／APIに接続してください。PrometheusはPrometheusRule CRDに記述されたLogQLを評価できません。Grafana Alertingのprovisioningは別のschemaと `apiVersion` 契約を使います。

取り込み件数の累積counterがゼロでも、取り込み停止は検出できません。直近のrate、想定入力、collectorエラー、backpressure、storage障害を関連付けて確認してください。期待する入力がなければ、storageの動きがゼロというだけで障害とは判断できません。

## 5. PromQL とメトリクスの単位

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

classic histogram bucketを集約するときは `le` を保持してください。error seriesが存在しない場合は、そのserviceの実リクエストseriesを基準にゼロを補ってください。リクエストもゼロなら、正常を示すゼロのerror比率を捏造してはいけません。recording ruleの単位を、dashboardの `s`、`percentunit`、`reqps` に合わせてください。

質問に合ったcounterのrate／increaseを使ってください。累積counterを30日間で平均しても、平均RPSにはなりません。平均値、サンプルのpercentile、histogram quantileはそれぞれ異なる統計量です。

Istioのsource reporterとdestination reporterは、同じ観測を重複して報告することがあります。たとえば、必要な視点を選択してください:

```promql
sum by (cluster, destination_service_namespace, destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)
```

Istioの所要時間の単位であるミリ秒と、アプリケーション側の秒を区別してください。観測されたL7リクエストに対するmTLS比率は、すべてのL4トラフィックに暗号化ポリシーが適用されている証明にはなりません。Ambient環境では、該当する場合のwaypoint要件を含め、実際のL7 telemetry経路を確認してください。

CloudWatch exporterの `_sum` は、単調増加counterではなく期間統計のgaugeである場合があります。無条件に `rate()` を適用しないでください。60秒間のRequestCount SumをRPSに換算する前に、期間、exporterのtimestamp／遅延、seriesの重複を確認してください。prefixとlabelはexporterによって異なります。

AMPがqueryするのはworkspaceに取り込まれたデータです。CloudWatchデータを自動的に取り込んだり、workspace／Regionをfederateしたり、`up{job="amp-remote-write"}` targetを作成したりするわけではありません。実際のremote-write queue／errorと、AMPでサポートされる取り込みtelemetryを確認してください。

## 6. TraceQL

以下のクエリはTempo 3.0.3のドキュメントとGrafana公式grammarに照らして確認しました。属性名は実際の計装schemaと一致させてください。

```traceql
{ resource.service.name = "correlation-api" }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 500ms }
```

```traceql
{ trace:duration > 2s }
```

`span:duration` はspanの所要時間、`trace:duration` はtrace全体の所要時間です。`span:name` のようなintrinsicは、ユーザー属性名 `span.name` とは異なります。

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span.http.status_code >= 500 }
```

Goの実行では `http.request.method` と `http.response.status_code` が出力されました。Goのバックエンドには次のクエリを使ってください。

```traceql
{ resource.service.name = "correlation-api" && span.http.response.status_code >= 500 }
```

error statusとHTTP 500は同じ意味ではありません。Pythonのデモではデフォルトで `http.status_code` が出力されました。新しいconventionを有効にする場合は、`http.response.status_code` など実際の属性に合わせてクエリを更新してください。

### 関係と集約

```traceql
{ span:kind = server } > { span:name = "prepare-order-response" }
```

```traceql
{ span:kind = server } >> { span:status = error }
```

```traceql
{ span:name = "check-stock" } ~ { span:name = "check-payment" }
```

`>` は直接の子、`>>` は任意の深さの子孫、`<` は直接の親、`~` は同じ親を持つ兄弟spanを選択します。1つのサービスのclient／server spanを選んでも、すべてのpeerが自動的に対応付けられるわけではありません。

```traceql
{ resource.service.name = "correlation-api" } | by(span:name) | count() > 1
```

span名が繰り返されているだけでは、retryが行われた証拠になりません。`{ }*` のような未サポートの反復構文は避け、trace IDによる検索と明示的な構造クエリを使ってください。

```traceql
{ resource.service.name = "correlation-api" } | quantile_over_time(duration, 0.99)
```

これは遅い個々のtrace一覧ではなく、TraceQLのメトリクスseriesを返します。クエリモードとTempoデプロイのfeature／データ経路を確認してください。service graphには、サポートされた生成機能／processorとstorage／query設定が必要です。

`traces_service_graph_request_total` など生成されたメトリクスは、メトリクスバックエンドで **PromQL** を使ってqueryします。client／server spanの対応付けとサンプリングによって、グラフが不完全になることがあります。旧形式の `processor.*.enabled=true` 断片だけでは、現在のTempo設定は完成しません。

## 7. Grafana データソースとダッシュボード

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

3つすべてのUIDが明示され、参照先も一致しています。exemplarの `trace_id`、JSONの `trace_id`、Lokiのderived fieldは、同じ命名契約を使います。regexはJSON内の空白を許容し、32桁の16進数だけを取り出します。

`${__value.raw}` や `__tags` などのmacroをprovisioning YAMLに記述する際は、`$` を `$$` としてエスケープしてください。Tempoへの内部リンクにはtrace IDの値をそのままqueryとして渡します。無関係なExplore URLを手作業で組み合わせないでください。

`tracesToLogsV2` は、trace resourceの `service.name` をLoki labelの `service_name` に対応付けます。trace全体のログを見る際に、span IDで不必要に絞り込まないでください。デプロイ時はtenant、TLS／認証、実際のService URLを設定してください。

### ファイルによるprovisioning形式

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

datasourceファイルをGrafanaのdatasource provisioning pathへ、providerファイルをdashboard provisioning pathへ、JSONをproviderの設定ディレクトリへmountしてください。ConfigMapを作成しただけでは、Grafanaにファイルは接続されません。

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

ファイルprovisioningでは、HTTP APIの `{"dashboard": ...}` wrapperを付けず、dashboard objectそのものを使います。この例では未定義変数ではなく、固定のservice名と明示的なUIDを使用します。

旧 `graph` panelではなく、現在の `timeseries` panelを使ってください。累積histogram bucketの曲線は、heatmapのbucketごとの分布とは異なります。生のtrace検索結果を「Active Traces」の件数と表示したり、service map用のdata frameだと想定したりしないでください。

変数を追加する際は、実際のメトリクスに存在するlabelを使用してください。Multi／Allの値には、単一文字列を前提にせず、適切なregex escapeやoperatorが必要です。各データソースのquery構文をテストしてください。

## 検証範囲

SDKテストでは明示的なメモリ内exporterと偽のHTTP transportを使い、外部OTLP exporterは使っていません。記録は分離されたテスト内でのみ有効にし、個人用endpointやresource属性を引き継いでいません。

Collector／Alloyのネイティブ検証、ローカルLokiでのquery結果、Prometheus recording ruleの計算、Javaのencoding、trace ID regex、UID参照を確認しました。TraceQL grammarの検証は、実際のTempo取り込み／検索の代わりにはなりません。Grafana UI、バックエンド認証、デプロイは、それぞれ実環境で別途検証が必要です。

## 参考資料

- [OpenTelemetry Go 1.46](https://github.com/open-telemetry/opentelemetry-go/releases/tag/v1.46.0)
- [Loki のネイティブ OTLP](https://grafana.com/docs/loki/latest/send-data/otel/)
- [Promtail の EOL](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [Tempo 3.0.3 TraceQL](https://github.com/grafana/tempo/blob/v3.0.3/docs/sources/tempo/traceql/construct-traceql-queries.md)
- [Grafana Tempo の provisioning](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/provision/)
- [Grafana Loki の設定](https://grafana.com/docs/grafana/latest/datasources/loki/configure/)
- [本章のクイズ](../quizzes/ops/08-observability-analysis-quiz.md)

< [前へ：運用アラート](07-observability-alerts.md) | [目次](README.md) | [次へ：スタック運用](09-observability-stack.md) >
