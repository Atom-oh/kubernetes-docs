# Distributed Tracing Overview

> **Last Updated**: February 2025

## Introduction

Distributed Tracing is a technique for tracking the complete path of requests as they traverse multiple services in microservices architectures. In modern systems where a single request can pass through dozens of services, distributed tracing is essential for identifying performance bottlenecks and troubleshooting issues.

## The Need for Distributed Tracing

### Limitations of Traditional Monitoring

In microservices environments, traditional logging and metrics alone cannot answer these questions:

- Which services did the request pass through?
- How long did each service take?
- Where did errors occur?
- What are the dependencies between services?

```mermaid
flowchart TD
    subgraph Problem["Problem: Complex Request Flow"]
        U[User] --> A[API Gateway]
        A --> B[Auth Service]
        A --> C[Product Service]
        C --> D[Inventory Service]
        C --> E[Pricing Service]
        A --> F[Order Service]
        F --> G[Payment Service]
        F --> H[Notification Service]
        G --> I[Fraud Detection]
    end

    Q1[Where did latency occur?]
    Q2[What's the root cause of errors?]
    Q3[What are the service dependencies?]

    Problem -.-> Q1
    Problem -.-> Q2
    Problem -.-> Q3

    classDef user fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef service fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef question fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class U user
    class A,B,C,D,E,F,G,H,I service
    class Q1,Q2,Q3 question
```

## Core Concepts

### 1. Trace

A Trace represents the complete journey of a single request. It is the collection of all operations generated as a request passes through the system.

```mermaid
flowchart LR
    subgraph Trace["Trace: Complete Request Journey"]
        direction LR
        S1[API Gateway<br/>150ms]
        S2[User Service<br/>50ms]
        S3[Order Service<br/>200ms]
        S4[Payment Service<br/>300ms]
        S5[Notification<br/>100ms]
    end

    S1 --> S2
    S1 --> S3
    S3 --> S4
    S3 --> S5

    Total[Total Duration: 500ms]

    Trace --> Total

    classDef span fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef total fill:#34A853,stroke:#333,stroke-width:1px,color:white

    class S1,S2,S3,S4,S5 span
    class Total total
```

### 2. Span

A Span represents a single unit of work. Each Span contains the following information:

| Field | Description | Example |
|-------|-------------|---------|
| **TraceID** | Unique identifier for the entire trace | `abc123def456` |
| **SpanID** | Unique identifier for the individual Span | `span789` |
| **ParentSpanID** | Identifier of the parent Span | `span456` |
| **Operation Name** | Name of the operation | `HTTP GET /api/users` |
| **Start Time** | Start timestamp | `2025-02-15T10:30:00Z` |
| **Duration** | Time taken | `150ms` |
| **Tags** | Metadata | `http.status_code=200` |
| **Logs** | Event records | `error: connection timeout` |

```mermaid
flowchart TD
    subgraph SpanStructure["Span Structure"]
        direction TB

        subgraph Header["Header Information"]
            TID[TraceID: abc123]
            SID[SpanID: span001]
            PID[ParentSpanID: null]
        end

        subgraph Timing["Timing Information"]
            ST[Start: 10:30:00.000]
            DUR[Duration: 150ms]
        end

        subgraph Metadata["Metadata"]
            OP[Operation: HTTP GET /users]
            TAGS[Tags: service=api, http.method=GET]
            LOGS[Logs: request received, response sent]
        end

        subgraph Status["Status"]
            CODE[Status: OK]
        end
    end

    Header --> Timing
    Timing --> Metadata
    Metadata --> Status

    classDef header fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef timing fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef metadata fill:#34A853,stroke:#333,stroke-width:1px,color:white
    classDef status fill:#E6522C,stroke:#333,stroke-width:1px,color:white

    class TID,SID,PID header
    class ST,DUR timing
    class OP,TAGS,LOGS metadata
    class CODE status
```

### 3. Span Relationships and Hierarchy

Spans form parent-child relationships creating a tree structure:

```mermaid
flowchart TD
    subgraph TraceTree["Trace Tree Structure"]
        ROOT[Root Span<br/>API Gateway<br/>TraceID: abc123<br/>SpanID: span001]

        CHILD1[Child Span<br/>Auth Service<br/>SpanID: span002<br/>Parent: span001]

        CHILD2[Child Span<br/>Order Service<br/>SpanID: span003<br/>Parent: span001]

        GRANDCHILD1[Grandchild Span<br/>Payment Service<br/>SpanID: span004<br/>Parent: span003]

        GRANDCHILD2[Grandchild Span<br/>Inventory Service<br/>SpanID: span005<br/>Parent: span003]
    end

    ROOT --> CHILD1
    ROOT --> CHILD2
    CHILD2 --> GRANDCHILD1
    CHILD2 --> GRANDCHILD2

    classDef root fill:#E6522C,stroke:#333,stroke-width:2px,color:white
    classDef child fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef grandchild fill:#34A853,stroke:#333,stroke-width:1px,color:white

    class ROOT root
    class CHILD1,CHILD2 child
    class GRANDCHILD1,GRANDCHILD2 grandchild
```

### 4. SpanContext

SpanContext is the trace information propagated between services:

```yaml
# SpanContext Components
SpanContext:
  trace_id: "abc123def456789"      # Trace identifier
  span_id: "span789"               # Current Span identifier
  trace_flags: "01"                # Sampling flag
  trace_state: "vendor=value"      # Vendor-specific additional info
```

## Context Propagation

The method of passing trace context between services.

### W3C Trace Context (Recommended)

Propagation using W3C standard headers:

```http
# HTTP Request Headers
traceparent: 00-abc123def456789012345678901234-span12345678-01
tracestate: rojo=00f067aa0ba902b7,congo=t61rcWkgMzE
```

**traceparent format:**
```
version-trace_id-parent_id-trace_flags
00     -abc123...-span1234...-01
```

### B3 Propagation (Zipkin Compatible)

Propagation format used by Zipkin:

```http
# Single header format
b3: abc123def456789-span12345678-1-parent12345678

# Multi-header format
X-B3-TraceId: abc123def456789
X-B3-SpanId: span12345678
X-B3-ParentSpanId: parent12345678
X-B3-Sampled: 1
```

### Propagation Format Comparison

| Format | Headers | Advantages | Disadvantages |
|--------|---------|------------|---------------|
| **W3C Trace Context** | `traceparent`, `tracestate` | Standard, extensible | Relatively new |
| **B3 Single** | `b3` | Simple, single header | Zipkin-specific |
| **B3 Multi** | `X-B3-*` | Easy debugging | Many headers |
| **Jaeger** | `uber-trace-id` | Jaeger optimized | Vendor lock-in |

## Sampling Strategies

Tracing all requests causes cost and performance issues. Sampling manages this.

### Head-based Sampling

Sampling decision at request start:

```mermaid
flowchart LR
    subgraph HeadBased["Head-based Sampling"]
        REQ[Request Received]
        DEC{Sampling<br/>Decision}
        TRACE[Collect Trace]
        SKIP[Skip Trace]
    end

    REQ --> DEC
    DEC -->|10% Sample| TRACE
    DEC -->|90% Skip| SKIP

    classDef request fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef decision fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef trace fill:#34A853,stroke:#333,stroke-width:1px,color:white
    classDef skip fill:#E8E8E8,stroke:#333,stroke-width:1px,color:black

    class REQ request
    class DEC decision
    class TRACE trace
    class SKIP skip
```

**Advantages:**
- Simple implementation
- Low overhead
- Consistent sampling decisions

**Disadvantages:**
- May miss important requests
- May skip requests with errors or latency

**Configuration Example:**
```yaml
# OpenTelemetry SDK Configuration
sampling:
  type: parentbased_traceidratio
  ratio: 0.1  # 10% sampling
```

### Tail-based Sampling

Sampling decision after request completion based on results:

```mermaid
flowchart LR
    subgraph TailBased["Tail-based Sampling"]
        REQ[Request Received]
        COLLECT[Collect All Spans]
        ANALYZE{Analyze<br/>Error? Latency?}
        KEEP[Keep]
        DROP[Drop]
    end

    REQ --> COLLECT
    COLLECT --> ANALYZE
    ANALYZE -->|Error or Latency| KEEP
    ANALYZE -->|Normal| DROP

    classDef request fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef collect fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef analyze fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef keep fill:#34A853,stroke:#333,stroke-width:1px,color:white
    classDef drop fill:#E8E8E8,stroke:#333,stroke-width:1px,color:black

    class REQ request
    class COLLECT collect
    class ANALYZE analyze
    class KEEP keep
    class DROP drop
```

**Advantages:**
- Never miss important requests (errors, latency)
- More intelligent sampling
- Cost effective

**Disadvantages:**
- Complex implementation
- Higher memory usage
- Must temporarily store all Spans

**OTEL Collector Tail Sampling Configuration:**
```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      # Collect all error requests
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      # Collect slow requests
      - name: slow-requests
        type: latency
        latency:
          threshold_ms: 1000
      # 10% sampling for the rest
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

### Sampling Strategy Comparison

| Strategy | Decision Point | Resource Usage | Accuracy | Use Case |
|----------|---------------|----------------|----------|----------|
| **Head-based** | Request start | Low | Medium | Most cases |
| **Tail-based** | Request completion | High | High | Error/latency focused |
| **Adaptive** | Dynamic | Medium | High | High traffic variability |

## Trace-Log-Metric Correlation

### Linking Logs via TraceID

```java
// Java logging example (SLF4J + MDC)
import org.slf4j.MDC;
import io.opentelemetry.api.trace.Span;

public void processOrder(Order order) {
    Span span = Span.current();
    MDC.put("traceId", span.getSpanContext().getTraceId());
    MDC.put("spanId", span.getSpanContext().getSpanId());

    logger.info("Processing order: {}", order.getId());
    // Log output: {"traceId": "abc123", "spanId": "span456", "message": "Processing order: 12345"}
}
```

### Linking Metrics via Exemplars

```yaml
# Linking TraceID to Prometheus metrics
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
http_request_duration_seconds_bucket{le="1.0"} 1500 # {traceID="def456"}
```

### Correlation in Grafana

```mermaid
flowchart LR
    subgraph Correlation["Grafana Correlation"]
        M[Metrics Dashboard<br/>Response Time Spike]
        E[Exemplar<br/>TraceID: abc123]
        T[Tempo<br/>Trace Details]
        L[Loki<br/>Related Logs]
    end

    M -->|Click Exemplar| E
    E -->|View Trace| T
    T -->|Log Link| L
    L -->|Metric Link| M

    classDef metric fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef exemplar fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef trace fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef log fill:#34A853,stroke:#333,stroke-width:1px,color:white

    class M metric
    class E exemplar
    class T trace
    class L log
```

## Solution Comparison

### Distributed Tracing Solution Comparison

| Feature | Tempo | X-Ray | Jaeger | Datadog APM | Dynatrace |
|---------|-------|-------|--------|-------------|-----------|
| **Type** | Open Source | AWS Managed | Open Source | Commercial SaaS | Commercial SaaS |
| **Storage** | Object Storage | AWS Internal | Cassandra/ES | Datadog | Dynatrace |
| **Query Language** | TraceQL | Filter Expressions | - | - | DQL |
| **Sampling** | Head/Tail | Rule-based | Head | Dynamic | Dynamic |
| **OTEL Support** | Native | Native | Native | Native | Native |
| **Service Map** | Grafana Integration | Built-in | Built-in | Built-in | Built-in |
| **AI Analysis** | None | None | None | Watchdog | Davis AI |
| **Cost** | Storage cost only | Usage-based | Infrastructure cost | Host/span-based | Host-based |
| **EKS Integration** | Manual config | Native | Manual config | Agent deployment | OneAgent |

### Selection Guide

```mermaid
flowchart TD
    START[Select Distributed Tracing Solution]

    Q1{Need AWS Native<br/>Integration?}
    Q2{Cost Priority?}
    Q3{Need AI Analysis?}
    Q4{Using Grafana<br/>Stack?}

    XRAY[AWS X-Ray]
    TEMPO[Grafana Tempo]
    JAEGER[Jaeger]
    DATADOG[Datadog APM]
    DYNATRACE[Dynatrace]

    START --> Q1
    Q1 -->|Yes| XRAY
    Q1 -->|No| Q2
    Q2 -->|Yes| Q4
    Q4 -->|Yes| TEMPO
    Q4 -->|No| JAEGER
    Q2 -->|No| Q3
    Q3 -->|Yes| DYNATRACE
    Q3 -->|No| DATADOG

    classDef question fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef solution fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef aws fill:#FF9900,stroke:#333,stroke-width:1px,color:black

    class Q1,Q2,Q3,Q4 question
    class TEMPO,JAEGER,DATADOG,DYNATRACE solution
    class XRAY aws
```

## Best Practices

### 1. Instrumentation Strategy

```yaml
# Recommended instrumentation scope
instrumentation:
  # Always instrument
  always:
    - HTTP requests/responses
    - gRPC calls
    - Database queries
    - Message queue operations
    - External API calls

  # Optional instrumentation
  optional:
    - Internal function calls
    - Cache operations
    - File I/O
```

### 2. Span Naming Conventions

```yaml
# Good examples
- "HTTP GET /api/users/{id}"
- "PostgreSQL SELECT users"
- "Redis GET user:123"
- "Kafka SEND orders"

# Bad examples
- "http call"
- "db query"
- "process"
- "span1"
```

### 3. Tag Standardization

```yaml
# OpenTelemetry Semantic Conventions
tags:
  # HTTP
  http.method: GET
  http.url: https://api.example.com/users
  http.status_code: 200

  # Database
  db.system: postgresql
  db.statement: SELECT * FROM users
  db.operation: SELECT

  # Service
  service.name: user-service
  service.version: 1.2.3
```

## Next Steps

Once you understand distributed tracing concepts, learn specific tool usage in the following sections:

- [Grafana Tempo](./01-tempo.md): Grafana stack's distributed tracing backend
- [AWS X-Ray](./02-xray.md): AWS native distributed tracing
- [OpenTelemetry](./03-opentelemetry.md): Standardized instrumentation framework
- [Dynatrace](./04-dynatrace.md): AI-powered APM solution

## Quiz

Test your knowledge with the tool-specific quizzes:
- [Tempo Quiz](../../quizzes/observability/tracing/01-tempo-quiz.md)
- [X-Ray Quiz](../../quizzes/observability/tracing/02-xray-quiz.md)
- [OpenTelemetry Quiz](../../quizzes/observability/tracing/03-opentelemetry-quiz.md)
- [Dynatrace Quiz](../../quizzes/observability/tracing/04-dynatrace-quiz.md)
