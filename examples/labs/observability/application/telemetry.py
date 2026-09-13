"""Shared trace/log/metric contracts for the synthetic observability lab."""

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone

from opentelemetry import propagate, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.openmetrics.exposition import generate_latest


class Telemetry:
    def __init__(self, service, revision, *, exporter=None, otlp_endpoint=None, log_stream=sys.stdout):
        self.service = service
        self.revision = revision
        self.log_stream = log_stream
        self.provider = TracerProvider(resource=Resource.create({"service.name": service}))
        if exporter is not None:
            self.provider.add_span_processor(SimpleSpanProcessor(exporter))
        elif otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            self.provider.add_span_processor(BatchSpanProcessor(
                OTLPSpanExporter(endpoint=otlp_endpoint, timeout=5),
                max_queue_size=256, max_export_batch_size=64,
                schedule_delay_millis=1000,
            ))
        self.tracer = self.provider.get_tracer("observability-lab", "1.0")
        self.registry = CollectorRegistry()
        labels = ["service", "route", "status", "revision"]
        self.requests = Counter(
            "lab_http_requests_total", "Completed synthetic HTTP requests.",
            labels, registry=self.registry,
        )
        self.duration = Histogram(
            "lab_http_request_duration_seconds", "Synthetic HTTP request duration.",
            labels, registry=self.registry,
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
        )

    def server_span(self, route, headers):
        context = propagate.extract(dict(headers))
        return self.span(route, context=context, kind=SpanKind.SERVER)

    @contextmanager
    def span(self, name, *, kind, context=None):
        # SDK defaults include exception text/stacktraces and status descriptions.
        # Those can contain SQL parameters or upstream request contents.
        with self.tracer.start_as_current_span(
            name, context=context, kind=kind,
            record_exception=False, set_status_on_exception=False,
        ) as span:
            try:
                yield span
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                raise

    @staticmethod
    def inject():
        carrier = {}
        propagate.inject(carrier)
        return carrier

    def record_http(self, route, status, seconds, span):
        span.set_attribute("http.route", route.split(" ", 1)[-1])
        span.set_attribute("http.request.method", route.split(" ", 1)[0])
        span.set_attribute("http.response.status_code", status)
        if status >= 500:
            span.set_status(Status(StatusCode.ERROR))
        context = span.get_span_context()
        exemplar = {"trace_id": f"{context.trace_id:032x}"} if context.is_valid else None
        labels = (self.service, route, str(status), self.revision)
        self.requests.labels(*labels).inc(exemplar=exemplar)
        self.duration.labels(*labels).observe(seconds, exemplar=exemplar)

    def log(self, level, event, span=None):
        context = (span or trace.get_current_span()).get_span_context()
        # No request body, customer ID, payment details or raw exceptions.
        print(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service, "level": level, "event": event,
            "trace_id": f"{context.trace_id:032x}" if context.is_valid else None,
            "span_id": f"{context.span_id:016x}" if context.is_valid else None,
        }), file=self.log_stream, flush=True)

    def metrics(self):
        return generate_latest(self.registry)

    def close(self):
        self.provider.shutdown()
