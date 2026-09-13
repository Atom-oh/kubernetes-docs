"""Synthetic lab HTTP roles; no external payment or email provider."""

import time
from decimal import Decimal

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from opentelemetry.trace import SpanKind
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError


class OrderInput(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    product_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    quantity: int = Field(ge=1, le=100, strict=True)


class PaymentInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=36, pattern=r"^[A-Za-z0-9-]+$")
    amount: Decimal = Field(gt=0, le=1_000_000, decimal_places=2)
    payment_method: str = Field(pattern=r"^(credit_card|debit_card|bank_transfer)$")


def create_app(role, store, telemetry, *, order_url=None, payment_url=None, delay_ms=0):
    if role not in ("api-gateway", "order-service", "payment-service", "notification", "analytics"):
        raise ValueError("Unknown lab role")
    if not 0 <= delay_ms <= 3000:
        raise ValueError("Lab delay must be between zero and 3000ms")
    app = FastAPI(title=f"Observability lab: {role}")

    @app.middleware("http")
    async def observe(request: Request, call_next):
        if request.url.path in ("/metrics", "/health", "/ready"):
            return await call_next(request)
        started = time.monotonic()
        # The stable route is filled in after routing; raw IDs never become
        # metric labels or log fields.
        with telemetry.server_span(request.method, request.headers) as span:
            status = 500
            try:
                response = await call_next(request)
                status = response.status_code
                return response
            finally:
                route = getattr(request.scope.get("route"), "path", "unmatched")
                name = f"{request.method} {route}"
                span.update_name(name)
                telemetry.record_http(name, status, time.monotonic() - started, span)
                telemetry.log("ERROR" if status >= 500 else "INFO", "request_complete", span)

    @app.get("/health")
    def health():
        return {"status": "ok", "role": role, "synthetic": True}

    @app.get("/ready")
    def ready():
        if store is not None:
            try:
                store.ready()
            except SQLAlchemyError:
                raise HTTPException(503, "Database unavailable or not initialized") from None
        return {"status": "ready", "role": role}

    @app.get("/metrics")
    def metrics():
        return Response(
            content=telemetry.metrics(),
            media_type="application/openmetrics-text; version=1.0.0; charset=utf-8",
        )

    if role == "order-service":
        @app.post("/orders", status_code=201)
        def create_order(body: OrderInput):
            if delay_ms:
                time.sleep(delay_ms / 1000)
            with telemetry.tracer.start_as_current_span("order transaction", kind=SpanKind.CLIENT) as span:
                span.set_attribute("db.system.name", store.engine.dialect.name)
                span.set_attribute("db.operation.name", "INSERT")
                return store.create_order(
                    body.customer_id, body.product_id, body.quantity,
                    telemetry.inject().get("traceparent", ""),
                )

        @app.get("/orders/{order_id}")
        def get_order(order_id: str):
            with telemetry.tracer.start_as_current_span("read order", kind=SpanKind.CLIENT) as span:
                span.set_attribute("db.system.name", store.engine.dialect.name)
                span.set_attribute("db.operation.name", "SELECT")
                result = store.get_order(order_id)
            if result is None:
                raise HTTPException(404, "Order not found")
            return result

    elif role == "payment-service":
        if not order_url:
            raise ValueError("payment-service requires order_url")

        @app.post("/payments")
        def create_payment(body: PaymentInput):
            with telemetry.tracer.start_as_current_span("GET order", kind=SpanKind.CLIENT) as span:
                span.set_attribute("http.request.method", "GET")
                try:
                    result = httpx.get(
                        f"{order_url.rstrip('/')}/orders/{body.order_id}",
                        headers=telemetry.inject(), timeout=5,
                    )
                except httpx.RequestError:
                    raise HTTPException(503, "Order service unavailable") from None
                span.set_attribute("http.response.status_code", result.status_code)
            if result.status_code == 404:
                raise HTTPException(404, "Order not found")
            if result.status_code != 200:
                raise HTTPException(503, "Order service unavailable")
            if delay_ms:
                time.sleep(delay_ms / 1000)
            try:
                return store.record_payment(
                    body.order_id, int(body.amount * 100), body.payment_method,
                    telemetry.inject().get("traceparent", ""),
                )
            except ValueError:
                raise HTTPException(409, "Conflicting synthetic payment") from None

    elif role == "api-gateway":
        if not order_url or not payment_url:
            raise ValueError("api-gateway requires order_url and payment_url")

        def forward(method, base, path, body=None):
            with telemetry.tracer.start_as_current_span(f"{method} upstream", kind=SpanKind.CLIENT) as span:
                span.set_attribute("http.request.method", method)
                try:
                    response = httpx.request(
                        method, base.rstrip("/") + path,
                        json=body, headers=telemetry.inject(), timeout=8,
                    )
                except httpx.RequestError:
                    raise HTTPException(503, "Upstream service unavailable") from None
                span.set_attribute("http.response.status_code", response.status_code)
                try:
                    payload = response.json()
                except ValueError:
                    raise HTTPException(502, "Invalid upstream response") from None
            return JSONResponse(payload, status_code=response.status_code)

        @app.post("/orders")
        def create_order(body: OrderInput):
            return forward("POST", order_url, "/orders", body.model_dump(mode="json"))

        @app.get("/orders/{order_id}")
        def get_order(order_id: str):
            # Quote the path segment to keep IDs from changing the upstream URL.
            from urllib.parse import quote
            return forward("GET", order_url, "/orders/" + quote(order_id, safe=""))

        @app.post("/payments")
        def create_payment(body: PaymentInput):
            return forward("POST", payment_url, "/payments", body.model_dump(mode="json"))

    else:
        @app.get("/stats")
        def stats():
            return {"consumer": role, "processed_events": store.consumed_count(role), "synthetic": True}

    return app
