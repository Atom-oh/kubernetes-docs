# Observability Overview

> **Last Updated**: February 2025

## Introduction

In modern distributed systems, especially Kubernetes-based microservices architectures, the ability to observe and understand the internal state of systems from external outputs is essential. This is called **Observability**.

## Observability vs Monitoring

Observability and monitoring are often used interchangeably, but there are fundamental differences:

| Aspect | Monitoring | Observability |
|--------|-----------|---------------|
| **Approach** | Based on predefined metrics and thresholds | Inferring internal state through system outputs |
| **Question Type** | "What went wrong?" (What) | "Why did it go wrong?" (Why) |
| **Data Scope** | Detecting known issues | Exploring unknown issues |
| **Flexibility** | Predefined dashboards | Dynamic queries and exploration |
| **Complexity** | Suitable for simple systems | Essential for complex distributed systems |

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

## The Three Pillars of Observability

Observability consists of three core data types:

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

Logs are records of individual events occurring in a system.

**Characteristics:**
- Discrete and immutable event records
- Include timestamps and context information
- Structured (JSON) or unstructured format
- Essential for debugging and auditing

**Use Cases:**
- Error and exception tracking
- Security auditing
- Compliance
- Detailed debugging

**Tools:** Loki, Elasticsearch, CloudWatch Logs, Fluent Bit

### 2. Metrics

Metrics are numeric measurements over time.

**Characteristics:**
- Stored as time series data
- Support aggregation and mathematical operations
- High storage efficiency
- Suitable for trend analysis

**Key Metric Types:**
- **Counter**: Cumulative increasing values (e.g., request count)
- **Gauge**: Current state values (e.g., CPU usage)
- **Histogram**: Distribution measurements (e.g., response time)
- **Summary**: Quantile calculations

**Tools:** Prometheus, VictoriaMetrics, CloudWatch Metrics, Datadog

### 3. Traces

Traces track the complete path of requests across distributed systems.

**Characteristics:**
- Visualize request flow between services
- Measure latency at each step
- Identify bottlenecks
- Dependency analysis

**Components:**
- **Trace**: The complete journey of a single request
- **Span**: A single unit of work
- **SpanContext**: Context propagated between services

**Tools:** Tempo, Jaeger, X-Ray, Zipkin, Datadog APM

## Correlation Between the Three Pillars

The three pillars are not independent but interconnected, providing powerful analytical capabilities:

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

### Trace-to-Log Correlation

Include TraceID in logs to track all logs related to a specific request:

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

### Metric-to-Trace Correlation (Exemplars)

Link TraceID to metrics to trace requests when anomalies occur:

```yaml
# Prometheus Exemplar
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
```

## OpenTelemetry and Standardization

OpenTelemetry (OTel) is the industry standard for observability data collection:

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

**Benefits of OpenTelemetry:**
- Vendor-neutral standard
- Support for multiple language SDKs
- Auto-instrumentation capabilities
- Multi-backend support
- Active community

## Observability Strategy for EKS Environments

Strategies for implementing effective observability in Amazon EKS:

### 1. Layer-based Observability

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

### 2. Recommended Tool Stack

| Function | Open Source | AWS Native | Commercial |
|----------|-------------|------------|------------|
| Metrics | Prometheus, VictoriaMetrics | CloudWatch, AMP | Datadog, New Relic |
| Logs | Loki, Elasticsearch | CloudWatch Logs | Splunk, Datadog |
| Traces | Tempo, Jaeger | X-Ray | Datadog APM, Dynatrace |
| Visualization | Grafana | CloudWatch Dashboards | Datadog, Dynatrace |

### 3. Cost Optimization Strategies

- **Sampling**: Reduce costs through trace data sampling
- **Retention Policies**: Optimize data retention periods
- **Tiered Storage**: Move older data to cheaper storage
- **Aggregation**: Store aggregated data instead of detailed data

## Observability Maturity Model

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

| Level | Characteristics | Example Tools |
|-------|-----------------|---------------|
| Level 1 | Basic log/metric collection | kubectl logs, CloudWatch |
| Level 2 | Centralized observability | Loki, Prometheus, Grafana |
| Level 3 | Three-pillar correlation | Tempo, Exemplars, TraceID |
| Level 4 | AIOps, automatic anomaly detection | Datadog Watchdog, Dynatrace Davis |

## Section Guide

This observability section is organized as follows:

### [Logging](./logging/)
Tools and strategies for log collection, storage, and analysis:
- Loki: Lightweight log aggregation system
- Fluent Bit: High-performance log collector
- CloudWatch Logs: AWS native logging

### [Metrics](./metrics/)
Time series metric collection and analysis:
- Prometheus: Industry standard metrics system
- VictoriaMetrics: High-performance Prometheus alternative
- CloudWatch Metrics: AWS native metrics

### [Tracing](./tracing/)
Distributed tracing and request flow analysis:
- Tempo: Grafana's distributed tracing backend
- X-Ray: AWS native distributed tracing
- OpenTelemetry: Standardized instrumentation
- Dynatrace: AI-powered APM

### [Grafana (Dashboards)](./grafana/)
Unified visualization and dashboards:
- Data source integration
- Dashboard design patterns
- Alert configuration

## Getting Started

To start implementing observability, the following order is recommended:

1. **Set up metric collection**: Deploy Prometheus or VictoriaMetrics
2. **Set up log collection**: Deploy Loki and Fluent Bit
3. **Set up tracing**: Deploy Tempo or X-Ray
4. **Visualization**: Connect all data sources in Grafana
5. **Correlation**: Configure TraceID-based linking

## References

- [OpenTelemetry Official Documentation](https://opentelemetry.io/docs/)
- [Grafana LGTM Stack](https://grafana.com/oss/lgtm-stack/)
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [SRE Workbook - Monitoring](https://sre.google/workbook/monitoring/)
