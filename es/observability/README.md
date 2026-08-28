# Descripción general de Observabilidad

> **Última actualización**: February 20, 2026

## Introducción

En los sistemas distribuidos modernos, especialmente en las arquitecturas de microservicios basadas en Kubernetes, la capacidad de observar y comprender el estado interno de los sistemas a partir de salidas externas es esencial. Esto se denomina **Observabilidad**.

## Observabilidad frente a monitorización

Observabilidad y monitorización se usan con frecuencia de forma indistinta, pero existen diferencias fundamentales:

| Aspecto | Monitorización | Observabilidad |
|--------|-----------|---------------|
| **Enfoque** | Basado en métricas y umbrales predefinidos | Inferir el estado interno mediante las salidas del sistema |
| **Tipo de pregunta** | «¿Qué salió mal?» (Qué) | «¿Por qué salió mal?» (Por qué) |
| **Alcance de los datos** | Detección de problemas conocidos | Exploración de problemas desconocidos |
| **Flexibilidad** | Dashboards predefinidos | Consultas y exploración dinámicas |
| **Complejidad** | Adecuada para sistemas simples | Esencial para sistemas distribuidos complejos |

```mermaid
flowchart LR
    subgraph Monitoring["Monitoring"]
        M1[Predefined Metrics]
        M2[Threshold Alerts]
        M3[Dashboards]
    end

    subgraph Observability["Observability"]
        O1[Logs]
        O2[Metrics]
        O3[Traces]
    end

    M1 --> M2
    M2 --> M3

    O1 <--> O2
    O2 <--> O3
    O3 <--> O1

    Monitoring -->|Evolution| Observability

    classDef monitoring fill:#4285F4,stroke:#333,stroke-width:1px,color:white
    classDef observability fill:#34A853,stroke:#333,stroke-width:1px,color:white

    class M1,M2,M3 monitoring
    class O1,O2,O3 observability
```

## Los tres pilares de la Observabilidad

La Observabilidad consta de tres tipos principales de datos:

```mermaid
flowchart TD
    subgraph Pillars["Three Pillars of Observability"]
        direction TB

        subgraph Logs["Logs"]
            L1[Event Records]
            L2[Structured Data]
            L3[Context Information]
        end

        subgraph Metrics["Metrics"]
            M1[Numeric Measurements]
            M2[Time Series Data]
            M3[Aggregatable]
        end

        subgraph Traces["Traces"]
            T1[Request Path]
            T2[Inter-service Flow]
            T3[Latency Analysis]
        end
    end

    Logs <-->|TraceID Linking| Traces
    Metrics <-->|Exemplar| Traces
    Logs <-->|Label Matching| Metrics

    classDef logs fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef metrics fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef traces fill:#326CE5,stroke:#333,stroke-width:1px,color:white

    class L1,L2,L3 logs
    class M1,M2,M3 metrics
    class T1,T2,T3 traces
```

### 1. Logs

Los Logs son registros de eventos individuales que ocurren en un sistema.

**Características:**
- Registros de eventos discretos e inmutables
- Incluyen marcas de tiempo e información de contexto
- Formato estructurado (JSON) o no estructurado
- Esenciales para la depuración y la auditoría

**Casos de uso:**
- Seguimiento de errores y excepciones
- Auditoría de seguridad
- Cumplimiento normativo
- Depuración detallada

**Herramientas:** Loki, Elasticsearch, CloudWatch Logs, Fluent Bit

### 2. Métricas

Las métricas son mediciones numéricas a lo largo del tiempo.

**Características:**
- Se almacenan como datos de series temporales
- Admiten agregación y operaciones matemáticas
- Alta eficiencia de almacenamiento
- Adecuadas para el análisis de tendencias

**Tipos de métricas principales:**
- **Counter**: Valores acumulativos crecientes (p. ej., número de solicitudes)
- **Gauge**: Valores del estado actual (p. ej., uso de CPU)
- **Histogram**: Mediciones de distribución (p. ej., tiempo de respuesta)
- **Summary**: Cálculos de cuantiles

**Herramientas:** Prometheus, VictoriaMetrics, CloudWatch Metrics, Datadog

### 3. Trazas

Las trazas rastrean la ruta completa de las solicitudes en sistemas distribuidos.

**Características:**
- Visualizan el flujo de solicitudes entre servicios
- Miden la latencia en cada paso
- Identifican cuellos de botella
- Análisis de dependencias

**Componentes:**
- **Trace**: El recorrido completo de una única solicitud
- **Span**: Una unidad de trabajo individual
- **SpanContext**: Contexto propagado entre servicios

**Herramientas:** Tempo, Jaeger, X-Ray, Zipkin, Datadog APM

## Correlación entre los tres pilares

Los tres pilares no son independientes, sino que están interconectados y proporcionan potentes capacidades analíticas:

```mermaid
flowchart TD
    subgraph Request["User Request"]
        R[HTTP Request]
    end

    subgraph Services["Microservices"]
        S1[API Gateway]
        S2[User Service]
        S3[Order Service]
        S4[Payment Service]
    end

    subgraph Correlation["Correlation"]
        C1[TraceID: abc123]
        C2[Metric Exemplar]
        C3[Log Correlation]
    end

    R --> S1
    S1 --> S2
    S1 --> S3
    S3 --> S4

    S1 -.->|Logs/Metrics/Traces| C1
    S2 -.->|Logs/Metrics/Traces| C1
    S3 -.->|Logs/Metrics/Traces| C1
    S4 -.->|Logs/Metrics/Traces| C1

    C1 <--> C2
    C2 <--> C3
    C3 <--> C1

    classDef request fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef service fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef correlation fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class R request
    class S1,S2,S3,S4 service
    class C1,C2,C3 correlation
```

### Correlación de Trace a Log

Incluya el TraceID en los Logs para rastrear todos los Logs relacionados con una solicitud específica:

```json
{
  "timestamp": "2025-02-15T10:30:00Z",
  "level": "ERROR",
  "message": "Payment processing failed",
  "traceId": "abc123def456",
  "spanId": "789xyz",
  "service": "payment-service"
}
```

### Correlación de métricas a Trace (Exemplars)

Vincule el TraceID a las métricas para rastrear solicitudes cuando se produzcan anomalías:

```yaml
# Prometheus Exemplar
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
```

## OpenTelemetry y estandarización

OpenTelemetry (OTel) es el estándar del sector para la recopilación de datos de Observabilidad:

```mermaid
flowchart TD
    subgraph Apps["Applications"]
        A1[Java App]
        A2[Python App]
        A3[Node.js App]
        A4[Go App]
    end

    subgraph SDK["OpenTelemetry SDK"]
        SDK1[Auto-instrumentation]
        SDK2[Manual instrumentation]
    end

    subgraph Collector["OTEL Collector"]
        C1[Receivers]
        C2[Processors]
        C3[Exporters]
    end

    subgraph Backends["Backends"]
        B1[Tempo]
        B2[Prometheus]
        B3[Loki]
        B4[X-Ray]
        B5[Datadog]
    end

    A1 & A2 & A3 & A4 --> SDK1 & SDK2
    SDK1 & SDK2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> B1 & B2 & B3 & B4 & B5

    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef sdk fill:#4285F4,stroke:#333,stroke-width:1px,color:white
    classDef collector fill:#F8B52A,stroke:#333,stroke-width:1px,color:black
    classDef backend fill:#E6522C,stroke:#333,stroke-width:1px,color:white

    class A1,A2,A3,A4 app
    class SDK1,SDK2 sdk
    class C1,C2,C3 collector
    class B1,B2,B3,B4,B5 backend
```

**Beneficios de OpenTelemetry:**
- Estándar independiente de proveedores
- Compatibilidad con SDK para múltiples lenguajes
- Capacidades de instrumentación automática
- Compatibilidad con múltiples backends
- Comunidad activa

## Estrategia de Observabilidad para entornos EKS

Estrategias para implementar una Observabilidad eficaz en Amazon EKS:

### 1. Observabilidad basada en capas

```mermaid
flowchart TD
    subgraph Infra["Infrastructure Layer"]
        I1[EC2/Fargate Metrics]
        I2[VPC Flow Logs]
        I3[EBS Performance]
    end

    subgraph K8s["Kubernetes Layer"]
        K1[kube-state-metrics]
        K2[Node Exporter]
        K3[API Server Metrics]
    end

    subgraph App["Application Layer"]
        A1[Business Metrics]
        A2[Application Logs]
        A3[Distributed Tracing]
    end

    subgraph Tools["Observability Tools"]
        T1[CloudWatch]
        T2[Prometheus/Grafana]
        T3[Tempo/X-Ray]
        T4[Loki]
    end

    I1 & I2 & I3 --> T1
    K1 & K2 & K3 --> T2
    A1 --> T2
    A2 --> T4
    A3 --> T3

    classDef infra fill:#FF9900,stroke:#333,stroke-width:1px,color:black
    classDef k8s fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef tools fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class I1,I2,I3 infra
    class K1,K2,K3 k8s
    class A1,A2,A3 app
    class T1,T2,T3,T4 tools
```

### 2. Stack de herramientas recomendado

| Función | Código abierto | Nativo de AWS | Comercial |
|----------|-------------|------------|------------|
| Métricas | Prometheus, VictoriaMetrics | CloudWatch, AMP | Datadog, New Relic |
| Logs | Loki, Elasticsearch | CloudWatch Logs | Splunk, Datadog |
| Trazas | Tempo, Jaeger | X-Ray | Datadog APM, Dynatrace |
| Visualización | Grafana | CloudWatch Dashboards | Datadog, Dynatrace |

### 3. Estrategias de optimización de costos

- **Sampling**: Reduzca los costos mediante el muestreo de datos de trazas
- **Políticas de retención**: Optimice los períodos de retención de datos
- **Almacenamiento por niveles**: Mueva los datos más antiguos a almacenamiento más económico
- **Agregación**: Almacene datos agregados en lugar de datos detallados

## Modelo de madurez de Observabilidad

```mermaid
flowchart LR
    L1[Level 1<br/>Basic Monitoring]
    L2[Level 2<br/>Centralization]
    L3[Level 3<br/>Correlation]
    L4[Level 4<br/>AIOps]

    L1 -->|Log/Metric Collection| L2
    L2 -->|TraceID Linking| L3
    L3 -->|ML-based Analysis| L4

    classDef level1 fill:#E8E8E8,stroke:#333,stroke-width:1px,color:black
    classDef level2 fill:#B8D4E3,stroke:#333,stroke-width:1px,color:black
    classDef level3 fill:#7FB3D3,stroke:#333,stroke-width:1px,color:white
    classDef level4 fill:#326CE5,stroke:#333,stroke-width:1px,color:white

    class L1 level1
    class L2 level2
    class L3 level3
    class L4 level4
```

| Nivel | Características | Herramientas de ejemplo |
|-------|-----------------|---------------|
| Nivel 1 | Recopilación básica de Logs/métricas | kubectl logs, CloudWatch |
| Nivel 2 | Observabilidad centralizada | Loki, Prometheus, Grafana |
| Nivel 3 | Correlación de tres pilares | Tempo, Exemplars, TraceID |
| Nivel 4 | AIOps, detección automática de anomalías | Datadog Watchdog, Dynatrace Davis |

## Guía de secciones

Esta sección de Observabilidad está organizada de la siguiente manera:

### [Logging](./logging/README.md)
Herramientas y estrategias para la recopilación, el almacenamiento y el análisis de Logs:
- Loki: Sistema ligero de agregación de Logs
- Fluent Bit: Recopilador de Logs de alto rendimiento
- CloudWatch Logs: Logging nativo de AWS

### [Metrics](./metrics/README.md)
Recopilación y análisis de métricas de series temporales:
- Prometheus: Sistema de métricas estándar del sector
- VictoriaMetrics: Alternativa a Prometheus de alto rendimiento
- CloudWatch Metrics: Métricas nativas de AWS

### [Tracing](./tracing/README.md)
Tracing distribuido y análisis del flujo de solicitudes:
- Tempo: Backend de tracing distribuido de Grafana
- X-Ray: Tracing distribuido nativo de AWS
- OpenTelemetry: Instrumentación estandarizada
- Dynatrace: APM con tecnología de IA

### [Grafana (Dashboards)](./grafana/README.md)
Visualización y dashboards unificados:
- Integración de fuentes de datos
- Patrones de diseño de dashboards
- Configuración de alertas

## Primeros pasos

Para comenzar a implementar la Observabilidad, se recomienda el siguiente orden:

1. **Configure la recopilación de métricas**: Despliegue Prometheus o VictoriaMetrics
2. **Configure la recopilación de Logs**: Despliegue Loki y Fluent Bit
3. **Configure el tracing**: Despliegue Tempo o X-Ray
4. **Visualización**: Conecte todas las fuentes de datos en Grafana
5. **Correlación**: Configure la vinculación basada en TraceID

## Referencias

- [Documentación oficial de OpenTelemetry](https://opentelemetry.io/docs/)
- [Stack LGTM de Grafana](https://grafana.com/oss/lgtm-stack/)
- [Prácticas recomendadas de Observabilidad de AWS](https://aws-observability.github.io/observability-best-practices/)
- [SRE Workbook - Monitorización](https://sre.google/workbook/monitoring/)
