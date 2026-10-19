# Análisis de observabilidad: logs, métricas y trazas

> **Base de revisión**: OTel Go 1.46.0 / otelhttp 0.71.0, Python SDK 1.44.0 / instrumentation 0.65b0, Collector 0.162.0, Alloy 1.20.1, Loki 3.7.8, Tempo 3.0.3, Grafana 13.2.4\
> **Última revisión**: 16 de octubre de 2026. El comportamiento del SDK, los logs y los exemplars se probó con exportadores en memoria y dobles de prueba HTTP; LogQL se ejecutó con logs sintéticos en una instancia local de Loki. No se exportaron datos a un clúster real ni a un backend de telemetría externo.

< [Anterior: Alertas operativas](07-observability-alerts.md) | [Contenido](README.md) | [Siguiente: Operaciones del stack](09-observability-stack.md) >

La correlación conecta evidencias del mismo momento, servicio y solicitud. La coincidencia por sí sola no demuestra la causa raíz. Comprueba si faltan datos, revisa el muestreo y la retención, y después valida una hipótesis.

## 1. Identificadores y rutas de transporte reales

| Señal | Ruta usada en este capítulo | Contrato de correlación |
|---|---|---|
| Trazas | SDK → OTLP/HTTP Collector → Tempo | Contexto W3C y `service.name` |
| Logs | stdout JSON → fuente de logs de Alloy para Kubernetes → Loki | `trace_id` y `span_id` en JSON |
| Métricas | cliente Prometheus → scrape OpenMetrics de `/metrics` | `trace_id` del exemplar |
| Consultas | Grafana → cada fuente de datos | UID explícitos y asignaciones de etiquetas |

Un exportador de trazas no convierte automáticamente los logs de stdout ni las métricas del cliente Prometheus a OTLP. Para enviar todas las señales mediante OTLP se necesitan los exportadores y las canalizaciones correspondientes del SDK y del Collector. Tempo tampoco combina automáticamente los almacenes de logs y métricas.

### W3C y B3

```text
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

Los identificadores de traza W3C tienen 32 caracteres hexadecimales y los identificadores de span padre, dieciséis; los identificadores compuestos solo por ceros no son válidos. Las banderas incluyen información como el bit de muestreo. Un ID válido o una bandera de muestreo activa no garantizan que el backend almacene los datos ni que los conserve.

B3 es otro formato de propagación compatible, con identificadores de traza de 64 o 128 bits. Si aceptas varios formatos, define la precedencia cuando los encabezados entren en conflicto y delimita la frontera de confianza de entrada. Estos ejemplos usan solo W3C TraceContext. No propagues indiscriminadamente valores sensibles en baggage.

## 2. Ejemplos ejecutables del SDK

Go y Python son **implementaciones alternativas** del mismo contrato de logs y métricas. No inicies ambas en el mismo puerto. Sus puntos de entrada principales son demostraciones locales enlazadas a loopback; al desplegarlas, usa la configuración adecuada del servidor de aplicaciones, el Service y la dirección de enlace.

El servicio compartido se llama `correlation-api`. El JSON contiene `timestamp`, `level`, `message`, `service_name`, `route` con cardinalidad acotada, `status_code`, `latency_ms` e identificadores válidos de traza y span. No uses URL sin procesar ni identificadores de usuario como etiquetas de métricas ordinarias.

### Go

Usa un entorno Go 1.25+ con parches compatibles. La compilación local de esta revisión usó Go 1.25.0; eso no determina qué versión de parche debes elegir para producción.

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

Los atributos explícitos de `resource.NewSchemaless` evitan que se ignoren silenciosamente los conflictos entre SchemaURLs de convenciones semánticas. La configuración del proveedor y del propagador se pasa al handler y al transporte. El apagado HTTP y el apagado del exportador tienen plazos independientes. Si falla una dependencia, se registra un span de error y se devuelve HTTP 502.

### Python

Dependencias directas validadas con Python 3.12:

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

El formateador y el nivel INFO sí están configurados. `logging.info(..., extra=...)` por sí solo puede descartarse con la configuración de logging predeterminada o puede omitir los campos adicionales. El contexto válido sin muestrear se conserva en los logs; si falta contexto, no se inventan IDs compuestos solo por ceros.

Los atributos semánticos HTTP dependen de la versión de instrumentación y de la configuración optativa. De forma predeterminada, esta ejecución de Python emitió nombres compatibles como `http.method` y `http.status_code`. Inspecciona los atributos reales del span en vez de cambiar todas las consultas solo porque el SDK sea nuevo.

La configuración estándar del exportador OTel proporciona el endpoint real. Para HTTP/protobuf:

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc:4318
```

La dirección presupone que ya existe un Service del Collector. Configura por separado TLS, la autenticación y los controles de red del despliegue. Distingue el endpoint base de los endpoints específicos de señal que ya incluyen `/v1/traces`.

### Logs JSON de Java

Esta configuración del encoder se comprobó con Logback 1.6.3, logstash-logback-encoder 9.0 y JDK 21.

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

Antes, un agente Java de OTel o un puente MDC configurado debe rellenar `trace_id`/`span_id`; el XML por sí solo no activa la instrumentación. Haz coincidir el service.name del agente Java con el nombre real del servicio registrado en los logs. La prueba proporcionó valores MDC para validar el encoder, las claves permitidas y el JSON multilínea escapado. No ejecutó la propagación del agente Java.

## 3. Collectors y conexión con los backends

Estos son **archivos de configuración para componentes desplegados**. Un ConfigMap por sí solo no crea un Deployment, Service, RBAC ni backend. Usa los namespaces, nombres de Service y métodos de autenticación reales.

### Collector de trazas

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

Esta pasarela procesa solo trazas y aplica límites de memoria y agrupación por lotes sin recurrir innecesariamente a CORS con comodines. Para enriquecer datos de Kubernetes, añade el procesador `k8sattributes` correcto, la asociación de pods y el RBAC antes de agrupar por lotes. Una dirección de conexión observada después de un proxy intermediario no necesariamente identifica el Pod original de la aplicación.

Los atributos de recurso y los encabezados de propagación requieren una frontera de confianza adecuada; no sustituyen las identidades de autenticación ni de autorización.

### Logs de stdout y Alloy

Promtail llegó al final de su vida útil el 2 de marzo de 2026. El ejemplo usa la fuente de logs de la API de Kubernetes de Alloy.

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

Ejecuta Alloy en el namespace `observability` con `correlation-log-reader` y proporciona esta configuración en la ruta real del archivo de configuración. Los Pods de destino deben llevar `app=correlation-api`.

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

Los logs obtenidos mediante la API de Kubernetes y la lectura de archivos del host son entradas distintas. La lectura de archivos requiere el encuadre CRI/Docker adecuado y el tratamiento de líneas parciales y multilínea. Mantener una pila de llamadas como saltos de línea escapados dentro de un único evento JSON evita unir por error registros que no están relacionados.

Conserva los ID de traza, solicitud y usuario en el cuerpo del log o en los metadatos estructurados apropiados, no en las etiquetas indexadas del stream de Loki. Ten en cuenta también la rotación y la retención de las etiquetas de Pod e instancia.

No reutilices el exportador `loki` del Collector, que se eliminó. Para logs OTLP nativos, una alternativa es un exportador `otlphttp` con destino `http://<loki>/otlp`, conectado a una canalización de logs y usado con una configuración compatible de metadatos estructurados y esquema de Loki. Esa ruta es distinta de la ruta de logs de stdout descrita arriba.

### Métricas y almacenamiento de exemplars

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

Prometheus 3.15 también requiere configurar la opción de almacenamiento de exemplars. `enable_http2` no la activa.

```bash
prometheus --config.file=prometheus.yaml --enable-feature=exemplar-storage
```

Mantén el archivo de reglas de grabación junto a la configuración. Las aplicaciones exponen OpenMetrics y adjuntan exemplars solo cuando el contexto es válido y está muestreado. El muestreo, el reemplazo del búfer y la retención de Tempo pueden hacer que no haya una traza coincidente. Un exemplar no representa cada observación ni necesariamente la solicitud exacta del P99.

## 4. LogQL

Las consultas usan el contrato de registro de solicitudes completadas de este ejemplo, con `service_name` y niveles JSON en mayúsculas. Un cociente genérico de errores basado en coincidencias de subcadena no equivale automáticamente a un cociente de solicitudes fallidas.

### Filtrado y agregación

```logql
{service_name="correlation-api"} | json | level="ERROR" | __error__=""
```

```logql
sum by (service_name) (rate({service_name="correlation-api"} | json | message="request completed" | status_code>=500 | status_code<600 | __error__="" [5m]))
```

```logql
sum by (service_name) (count_over_time({service_name="correlation-api"} | json | level="ERROR" | __error__="" [1h]))
```

`rate` devuelve líneas/s; `count_over_time` cuenta las líneas de cada intervalo. Agrega cuando necesites los totales de varios streams. `|=` busca subcadenas distinguiendo mayúsculas y minúsculas; no comprueba de forma estructurada el nivel de severidad.

### Latencia y errores del parser

```logql
quantile_over_time(0.95, {service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

```logql
avg_over_time({service_name="correlation-api"} | json | latency_ms>=0 | __error__="" | unwrap latency_ms | __error__="" [5m]) by (route)
```

El análisis de JSON, las comparaciones numéricas y el operador unwrap pueden producir errores, por lo que los filtros `__error__=""` deben colocarse correctamente. Estas consultas validan primero `latency_ms>=0`. Con Loki 3.7.8, valores válidos de 10 ms y 800 ms, un valor no numérico y JSON mal formado, las consultas corregidas devolvieron una media de 405 ms y un P95 de 760.5 ms.

Son agregaciones de rango de valores extraídos, no buckets de un histograma de Prometheus. Agrupar por mensajes sin restricciones o URL sin procesar también puede elevar la cardinalidad de los resultados de la consulta.

### Búsqueda de trazas

```logql
{service_name="correlation-api"} | json | trace_id="0af7651916cd43dd8448eb211c80319c" | __error__=""
```

Comprueba los errores de los parsers regex, de patrones y JSON. Un segundo `| json` no parsea automáticamente una cadena JSON anidada concreta; extrae el campo deseado o transforma la línea antes de volver a parsearla.

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

Conecta este archivo de reglas nativo al almacenamiento o la API de Loki Ruler. Prometheus no puede evaluar LogQL dentro de un recurso CRD PrometheusRule. El aprovisionamiento de Grafana Alerting usa otro esquema y otro contrato de `apiVersion`.

Un contador acumulativo de ingesta igual a cero no detecta que la ingesta se haya detenido. Correlaciona las tasas recientes, la entrada esperada, los errores del Collector, la contrapresión y los fallos de almacenamiento. La actividad de almacenamiento nula sin entrada esperada no demuestra por sí sola una interrupción.

## 5. PromQL y unidades de las métricas

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

Conserva `le` al agregar buckets de histogramas clásicos. Si no existe una serie de errores, completa con cero usando la serie real de solicitudes de ese servicio. Si tampoco hay solicitudes, no inventes un cociente de errores saludable igual a cero. Haz coincidir las unidades de las reglas de recording con `s`, `percentunit` y `reqps` en los dashboards.

Usa tasas o incrementos de contadores adecuados a la pregunta. Promediar un contador acumulativo durante treinta días no produce el RPS promedio. Las medias, los percentiles de muestra y los cuantiles de histograma son estadísticas distintas.

Los datos que Istio registra desde las perspectivas de origen y destino pueden duplicar observaciones. Selecciona el punto de vista deseado, por ejemplo:

```promql
sum by (cluster, destination_service_namespace, destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)
```

Distingue las duraciones de Istio expresadas en milisegundos de las de la aplicación expresadas en segundos. Un cociente de mTLS sobre solicitudes L7 observadas no demuestra que todo el tráfico L4 cumpla la política de cifrado. Las instalaciones Ambient necesitan la ruta real de telemetría L7, incluidos los requisitos de waypoint cuando corresponda.

El `_sum` de un exportador de CloudWatch puede ser un gauge de una estadística del período, no un contador monótono. No apliques `rate()` a ciegas. Para convertir a RPS un RequestCount Sum de 60 segundos, comprueba el período, la marca de tiempo o demora del exportador y las series duplicadas. Los prefijos y las etiquetas varían según el exportador.

Las consultas de AMP abarcan los datos ingeridos en un espacio de trabajo. AMP no ingiere CloudWatch automáticamente, no federa espacios de trabajo ni regiones y no crea un destino `up{job="amp-remote-write"}`. Inspecciona la cola real de remote write, sus errores y la telemetría de ingesta compatible con AMP.

## 6. TraceQL

Estas consultas se comprobaron con la documentación de Tempo 3.0.3 y la gramática oficial de Grafana. Los nombres de atributos deben coincidir con el esquema real de instrumentación.

```traceql
{ resource.service.name = "correlation-api" }
```

```traceql
{ resource.service.name = "correlation-api" && span:duration > 500ms }
```

```traceql
{ trace:duration > 2s }
```

`span:duration` es la duración de un span; `trace:duration` abarca la traza completa. Los elementos intrínsecos como `span:name` son distintos de un atributo de usuario llamado `span.name`.

```traceql
{ resource.service.name = "correlation-api" && span:status = error }
```

```traceql
{ resource.service.name = "correlation-api" && span.http.status_code >= 500 }
```

La ejecución de Go emitió `http.request.method` y `http.response.status_code`. Usa la siguiente consulta para ese backend de Go.

```traceql
{ resource.service.name = "correlation-api" && span.http.response.status_code >= 500 }
```

El estado de error no equivale a HTTP 500. La demostración de Python emitió `http.status_code` de forma predeterminada; si optas por convenciones más recientes, actualiza las consultas según los atributos reales, como `http.response.status_code`.

### Relaciones y agregaciones

```traceql
{ span:kind = server } > { span:name = "prepare-order-response" }
```

```traceql
{ span:kind = server } >> { span:status = error }
```

```traceql
{ span:name = "check-stock" } ~ { span:name = "check-payment" }
```

`>` selecciona hijos directos, `>>` descendientes a cualquier profundidad, `<` padres directos y `~` spans hermanos que comparten un padre. Seleccionar spans cliente/servidor de un servicio no asigna automáticamente todos los pares.

```traceql
{ resource.service.name = "correlation-api" } | by(span:name) | count() > 1
```

Que se repitan los nombres de span no demuestra que haya reintentos. Evita sintaxis de repetición no compatible, como `{ }*`; usa la búsqueda por ID de traza y consultas estructurales explícitas.

```traceql
{ resource.service.name = "correlation-api" } | quantile_over_time(duration, 0.99)
```

Esto devuelve series de métricas de TraceQL, no una lista de trazas lentas individuales. Comprueba el modo de consulta y la ruta de datos o las funciones habilitadas en el despliegue de Tempo. Los gráficos de servicios requieren un generador o procesador compatible, además de configuración de almacenamiento y consulta.

Las métricas generadas, como `traces_service_graph_request_total`, se consultan con **PromQL** en el backend de métricas. El emparejamiento de spans cliente/servidor y el muestreo pueden dejar incompletos los gráficos. Los fragmentos antiguos `processor.*.enabled=true` no constituyen una configuración completa y actual de Tempo.

## 7. Fuentes de datos y dashboards de Grafana

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

Los tres UID se especifican explícitamente y las referencias coinciden. El `trace_id` del exemplar, el `trace_id` JSON y el campo derivado de Loki comparten el mismo contrato de nombres. La regex acepta espacios en el JSON y captura exactamente 32 caracteres hexadecimales.

En el YAML de aprovisionamiento, conserva `$` como `$$` para macros como `${__value.raw}` y `__tags`. Un enlace interno de Tempo recibe una consulta con el ID de traza sin procesar; no lo combines con una URL de Explore construida manualmente y sin relación.

`tracesToLogsV2` asigna el recurso de traza `service.name` a la etiqueta de Loki `service_name`. Al consultar los logs de una traza completa, evita restringir innecesariamente el ID de span. Configura la tenancy, TLS/autenticación y las URL reales de Service para el despliegue.

### Formato de aprovisionamiento desde archivos

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

Monta el archivo de fuentes de datos en la ruta de aprovisionamiento de fuentes de datos de Grafana, el archivo del proveedor en la ruta de aprovisionamiento de dashboards y el JSON en el directorio configurado para el proveedor. Crear un ConfigMap por sí solo no conecta estos archivos con Grafana.

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

El aprovisionamiento desde archivos consume directamente el objeto del dashboard, sin el wrapper `{"dashboard": ...}` de la API HTTP. El ejemplo usa un servicio fijo y UID explícitos en vez de variables sin definir.

Usa paneles `timeseries` actuales en vez del panel `graph` heredado. Las curvas acumulativas de buckets de un histograma son distintas de la distribución por bucket de un heatmap. No etiquetes los resultados de una búsqueda de trazas sin procesar como un recuento de «trazas activas» ni des por sentado que son un data frame de mapa de servicios.

Al añadir variables, usa etiquetas que existan en las métricas reales. Los valores múltiples o All requieren operadores y escape regex adecuados; no presupongas que son una única cadena. Comprueba la sintaxis de consulta de cada fuente de datos.

## Alcance de la validación

Las pruebas del SDK construyeron exportadores explícitos en memoria y transportes HTTP falsos, sin exportadores OTLP externos. La grabación se habilitó solo dentro de esas pruebas aisladas, sin endpoints personales heredados ni atributos de recursos.

Se validaron la configuración nativa de Collector/Alloy, los resultados de consultas locales de Loki, los cálculos de reglas de recording de Prometheus, la codificación Java, las regex de ID de traza y las referencias de UID. Validar la gramática de TraceQL no sustituye la ingesta o búsqueda real en Tempo; la UI de Grafana, la autenticación del backend y el despliegue requieren validar el entorno por separado.

## Referencias

- [OpenTelemetry Go 1.46](https://github.com/open-telemetry/opentelemetry-go/releases/tag/v1.46.0)
- [OTLP nativo de Loki](https://grafana.com/docs/loki/latest/send-data/otel/)
- [Fin de vida útil de Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [TraceQL de Tempo 3.0.3](https://github.com/grafana/tempo/blob/v3.0.3/docs/sources/tempo/traceql/construct-traceql-queries.md)
- [Aprovisionamiento de Tempo en Grafana](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/provision/)
- [Configuración de Loki en Grafana](https://grafana.com/docs/grafana/latest/datasources/loki/configure/)
- [Cuestionario del capítulo](../quizzes/ops/08-observability-analysis-quiz.md)

< [Anterior: Alertas operativas](07-observability-alerts.md) | [Contenido](README.md) | [Siguiente: Operaciones del stack](09-observability-stack.md) >
