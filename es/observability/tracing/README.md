# Descripción general de Distributed Tracing

> **Última actualización**: February 20, 2026

## Introducción

Distributed Tracing es una técnica para rastrear la ruta completa de las solicitudes a medida que atraviesan múltiples servicios en arquitecturas de microservicios. En los sistemas modernos, donde una sola solicitud puede pasar por decenas de servicios, Distributed Tracing es esencial para identificar cuellos de botella de rendimiento y solucionar problemas.

## La necesidad de Distributed Tracing

### Limitaciones del monitoreo tradicional

En entornos de microservicios, el logging y las métricas tradicionales por sí solos no pueden responder estas preguntas:

- ¿Por qué servicios pasó la solicitud?
- ¿Cuánto tiempo tardó cada servicio?
- ¿Dónde ocurrieron los errores?
- ¿Cuáles son las dependencias entre los servicios?

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

## Conceptos principales

### 1. Trace

Un Trace representa el recorrido completo de una única solicitud. Es la colección de todas las operaciones generadas a medida que una solicitud pasa por el sistema.

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

Un Span representa una única unidad de trabajo. Cada Span contiene la siguiente información:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **TraceID** | Identificador único para todo el trace | `abc123def456` |
| **SpanID** | Identificador único para el Span individual | `span789` |
| **ParentSpanID** | Identificador del Span padre | `span456` |
| **Operation Name** | Nombre de la operación | `HTTP GET /api/users` |
| **Start Time** | Marca de tiempo de inicio | `2025-02-15T10:30:00Z` |
| **Duration** | Tiempo empleado | `150ms` |
| **Tags** | Metadatos | `http.status_code=200` |
| **Logs** | Registros de eventos | `error: connection timeout` |

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

### 3. Relaciones y jerarquía de Span

Los Spans forman relaciones padre-hijo que crean una estructura de árbol:

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

SpanContext es la información de trace que se propaga entre servicios:

```yaml
# SpanContext Components
SpanContext:
  trace_id: "abc123def456789"      # Trace identifier
  span_id: "span789"               # Current Span identifier
  trace_flags: "01"                # Sampling flag
  trace_state: "vendor=value"      # Vendor-specific additional info
```

## Propagación de contexto

El método para transmitir el contexto de trace entre servicios.

### W3C Trace Context (recomendado)

Propagación mediante headers estándar de W3C:

```http
# HTTP Request Headers
traceparent: 00-abc123def456789012345678901234-span12345678-01
tracestate: rojo=00f067aa0ba902b7,congo=t61rcWkgMzE
```

**formato de traceparent:**
```
version-trace_id-parent_id-trace_flags
00     -abc123...-span1234...-01
```

### Propagación B3 (compatible con Zipkin)

Formato de propagación utilizado por Zipkin:

```http
# Single header format
b3: abc123def456789-span12345678-1-parent12345678

# Multi-header format
X-B3-TraceId: abc123def456789
X-B3-SpanId: span12345678
X-B3-ParentSpanId: parent12345678
X-B3-Sampled: 1
```

### Comparación de formatos de propagación

| Formato | Headers | Ventajas | Desventajas |
|--------|---------|------------|---------------|
| **W3C Trace Context** | `traceparent`, `tracestate` | Estándar, extensible | Relativamente nuevo |
| **B3 Single** | `b3` | Simple, un solo header | Específico de Zipkin |
| **B3 Multi** | `X-B3-*` | Depuración sencilla | Muchos headers |
| **Jaeger** | `uber-trace-id` | Optimizado para Jaeger | Dependencia del proveedor |

## Estrategias de sampling

Rastrear todas las solicitudes genera problemas de costo y rendimiento. El sampling los gestiona.

### Head-based Sampling

Decisión de sampling al inicio de la solicitud:

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

**Ventajas:**
- Implementación sencilla
- Baja sobrecarga
- Decisiones de sampling coherentes

**Desventajas:**
- Puede omitir solicitudes importantes
- Puede omitir solicitudes con errores o latencia

**Ejemplo de configuración:**
```yaml
# OpenTelemetry SDK Configuration
sampling:
  type: parentbased_traceidratio
  ratio: 0.1  # 10% sampling
```

### Tail-based Sampling

Decisión de sampling tras la finalización de la solicitud, basada en los resultados:

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

**Ventajas:**
- Nunca omite solicitudes importantes (errores, latencia)
- Sampling más inteligente
- Rentable

**Desventajas:**
- Implementación compleja
- Mayor uso de memoria
- Debe almacenar temporalmente todos los Spans

**Configuración de Tail Sampling de OTEL Collector:**
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

### Comparación de estrategias de sampling

| Estrategia | Punto de decisión | Uso de recursos | Precisión | Caso de uso |
|----------|---------------|----------------|----------|----------|
| **Head-based** | Inicio de la solicitud | Bajo | Media | La mayoría de los casos |
| **Tail-based** | Finalización de la solicitud | Alto | Alta | Enfocado en errores/latencia |
| **Adaptive** | Dinámico | Medio | Alta | Alta variabilidad de tráfico |

## Correlación entre Trace, log y métrica

### Vinculación de logs mediante TraceID

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

### Vinculación de métricas mediante Exemplars

```yaml
# Linking TraceID to Prometheus metrics
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
http_request_duration_seconds_bucket{le="1.0"} 1500 # {traceID="def456"}
```

### Correlación en Grafana

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

## Comparación de soluciones

### Comparación de soluciones de Distributed Tracing

| Característica | Tempo | X-Ray | Jaeger | Datadog APM | Dynatrace |
|---------|-------|-------|--------|-------------|-----------|
| **Tipo** | Open Source | Administrado por AWS | Open Source | SaaS comercial | SaaS comercial |
| **Almacenamiento** | Object Storage | Interno de AWS | Cassandra/ES | Datadog | Dynatrace |
| **Lenguaje de consulta** | TraceQL | Expresiones de filtro | - | - | DQL |
| **Sampling** | Head/Tail | Basado en reglas | Head | Dinámico | Dinámico |
| **Compatibilidad con OTEL** | Nativa | Nativa | Nativa | Nativa | Nativa |
| **Mapa de servicios** | Integración con Grafana | Integrado | Integrado | Integrado | Integrado |
| **Análisis de AI** | Ninguno | Ninguno | Ninguno | Watchdog | Davis AI |
| **Costo** | Solo costo de almacenamiento | Basado en el uso | Costo de infraestructura | Basado en host/span | Basado en host |
| **Integración con EKS** | Configuración manual | Nativa | Configuración manual | Despliegue de Agent | OneAgent |

### Guía de selección

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

## Mejores prácticas

### 1. Estrategia de instrumentación

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

### 2. Convenciones de nomenclatura de Span

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

### 3. Estandarización de tags

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

## Próximos pasos

Una vez que comprenda los conceptos de Distributed Tracing, aprenda el uso de herramientas específicas en las siguientes secciones:

- [Grafana Tempo](./01-tempo.md): backend de Distributed Tracing del stack de Grafana
- [AWS X-Ray](./02-xray.md): Distributed Tracing nativo de AWS
- [OpenTelemetry](./03-opentelemetry.md): framework de instrumentación estandarizado
- [Dynatrace](./04-dynatrace.md): solución de APM impulsada por AI

## Cuestionario

Evalúe sus conocimientos con los cuestionarios específicos de cada herramienta:
- [Cuestionario de Tempo](../../quizzes/observability/tracing/01-tempo-quiz.md)
- [Cuestionario de X-Ray](../../quizzes/observability/tracing/02-xray-quiz.md)
- [Cuestionario de OpenTelemetry](../../quizzes/observability/tracing/03-opentelemetry-quiz.md)
- [Cuestionario de Dynatrace](../../quizzes/observability/tracing/04-dynatrace-quiz.md)
