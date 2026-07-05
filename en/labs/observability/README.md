# Lab Series Introduction

> **Difficulty**: Advanced **Last Updated**: February 23, 2026

## Overview

This lab series provides a comprehensive, hands-on journey through building a full-stack observability platform for Kubernetes-based microservices. You will deploy and integrate multiple observability tools across two EKS clusters, implementing the three pillars of observability (Metrics, Logs, Traces) with real-world patterns.

The architecture simulates a production-grade environment with a **Managed Cluster** hosting the observability stack and a **Service Cluster** running MSA applications with OTel instrumentation.

![Architecture Overview](../../.gitbook/assets/architecture-overview.png)

## Architecture Diagram

```mermaid
flowchart TB
    subgraph MC["Managed Cluster (EKS)"]
        ArgoCD["ArgoCD + Argo Rollouts"]
        subgraph ObsStack["Observability Stack"]
            Metrics["Metrics: Prometheus, VictoriaMetrics, Mimir"]
            Logs["Logs: Loki, ClickHouse"]
            Traces["Traces: Tempo, OTel Collector"]
            Alert["Alert: Alertmanager, Grafana OnCall"]
            Viz["Viz: Grafana"]
        end
        LoadTest["Load Testing: k6 / Locust"]
    end
    subgraph SC["Service Cluster (EKS)"]
        subgraph MSA["MSA Application (OTel Instrumented)"]
            APIGW["API Gateway (Go)"]
            Order["Order Service (Python)"]
            Payment["Payment Service (Java)"]
            Notif["Notification Service (Node.js)"]
            Batch["Analytics Batch (Python)"]
        end
        Karpenter["Karpenter"]
        KEDA["KEDA"]
        OTelAgent["OTel Agent (DaemonSet)"]
    end
    subgraph AWS["AWS Managed Services"]
        AMP & AMG & CW["CloudWatch"] & OS["OpenSearch"]
        SQS_SNS["SQS/SNS"] & Aurora & MWAA
    end
    ArgoCD -->|deploys| MSA
    APIGW --> Order --> Payment
    Order --> Aurora
    Payment --> Aurora
    Order -->|publish| SQS_SNS
    SQS_SNS -->|consume| Notif
    MWAA -->|trigger| Batch
    OTelAgent -->|send| ObsStack
    Metrics -->|remote write| AMP
    Logs -->|ship| OS
    Logs -->|ship| CW
    Traces -->|export| CW
    Alert -->|notify| SQS_SNS
```

## Prerequisites

Before starting this lab series, ensure you have the following:

| Requirement | Version  | Verification Command          |
| ----------- | -------- | ----------------------------- |
| AWS Account | -        | `aws sts get-caller-identity` |
| AWS CLI     | >= 2.15  | `aws --version`               |
| eksctl      | >= 0.175 | `eksctl version`              |
| kubectl     | >= 1.29  | `kubectl version --client`    |
| Helm        | >= 3.14  | `helm version`                |
| Terraform   | >= 1.7   | `terraform version`           |
| k6          | >= 0.49  | `k6 version`                  |
| Docker      | >= 24.0  | `docker --version`            |

### Required IAM Permissions

Your AWS user/role needs the following permissions:

* EKS full access
* EC2 full access (for node groups)
* VPC full access
* IAM limited access (for IRSA)
* CloudFormation full access
* SQS/SNS full access
* RDS full access (for Aurora)
* OpenSearch full access
* Managed Prometheus/Grafana full access
* MWAA full access

## Cost Estimate

> **Warning**: This lab series creates significant AWS resources. Estimated costs are provided below.

| Service                   | Configuration                     | Hourly Cost (USD) |
| ------------------------- | --------------------------------- | ----------------- |
| EKS Control Plane         | 2 clusters                        | $0.20             |
| EC2 (Managed Cluster)     | 3x m5.xlarge                      | $0.58             |
| EC2 (Service Cluster)     | 3x m5.large (+ Karpenter scaling) | $0.29+            |
| Aurora PostgreSQL         | db.r6g.large (multi-AZ)           | $0.52             |
| OpenSearch                | m6g.large.search (2 nodes)        | $0.25             |
| Amazon Managed Prometheus | Based on ingestion                | \~$0.10           |
| Amazon Managed Grafana    | 1 workspace                       | $0.15             |
| MWAA                      | mw1.small                         | $0.31             |
| SQS/SNS                   | Based on usage                    | \~$0.01           |
| **Total Estimate**        |                                   | **\~$2.50/hour**  |

**Tip**: Complete the lab in a single session and run cleanup immediately to minimize costs.

## Lab Sequence

```mermaid
flowchart LR
    P1["Part 1<br/>Infrastructure<br/>Setup"]
    P2["Part 2<br/>Observability<br/>Stack"]
    P3["Part 3<br/>MSA Deployment<br/>& Canary"]
    P4["Part 4<br/>Load Testing<br/>& Scaling"]
    P5["Part 5<br/>Alerting<br/>& AIOps"]
    P6["Part 6<br/>Distributed<br/>Tracing"]

    P1 --> P2 --> P3 --> P4 --> P5 --> P6

    classDef infra fill:#FF9900,stroke:#333,stroke-width:1px,color:black
    classDef obs fill:#326CE5,stroke:#333,stroke-width:1px,color:white
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white
    classDef test fill:#E6522C,stroke:#333,stroke-width:1px,color:white
    classDef alert fill:#9B59B6,stroke:#333,stroke-width:1px,color:white
    classDef trace fill:#F8B52A,stroke:#333,stroke-width:1px,color:black

    class P1 infra
    class P2 obs
    class P3 app
    class P4 test
    class P5 alert
    class P6 trace
```

| Part | Title                                                    | Duration | Key Topics                                      |
| ---- | -------------------------------------------------------- | -------- | ----------------------------------------------- |
| 1    | [Infrastructure Setup](01-infrastructure-setup-lab.md)   | 60 min   | EKS clusters, AWS services, ArgoCD              |
| 2    | [Observability Stack](02-observability-stack-lab.md)     | 90 min   | OTel, Prometheus, Loki, Tempo, Grafana          |
| 3    | [MSA Deployment & Canary](03-msa-deployment-lab.md)      | 60 min   | ArgoCD, Argo Rollouts, OTel instrumentation     |
| 4    | [Load Testing & Scaling](04-load-testing-scaling-lab.md) | 45 min   | k6, KEDA, Karpenter                             |
| 5    | [Alerting & AIOps](05-alerting-aiops-lab.md)             | 60 min   | Alertmanager, OnCall, CloudWatch Investigations |
| 6    | [Distributed Tracing](06-distributed-tracing-lab.md)     | 45 min   | Tempo, TraceQL, Log-Trace correlation           |

## MSA Application Overview

The lab uses a sample e-commerce MSA application with 5 services:

| Service              | Language           | Role                            | Dependencies              |
| -------------------- | ------------------ | ------------------------------- | ------------------------- |
| API Gateway          | Go                 | Request routing, authentication | Order, Payment            |
| Order Service        | Python (FastAPI)   | Order management, inventory     | Aurora, SQS               |
| Payment Service      | Java (Spring Boot) | Payment processing              | Aurora                    |
| Notification Service | Node.js (Express)  | Email/SMS notifications         | SQS consumer              |
| Analytics Batch      | Python             | Daily analytics aggregation     | Aurora, triggered by MWAA |

### Service Call Flow

```mermaid
sequenceDiagram
    participant Client
    participant APIGW as API Gateway<br/>(Go)
    participant Order as Order Service<br/>(Python)
    participant Payment as Payment Service<br/>(Java)
    participant Aurora as Aurora PostgreSQL
    participant SQS as SQS Queue
    participant Notif as Notification<br/>(Node.js)

    Client->>APIGW: POST /orders
    APIGW->>Order: CreateOrder()
    Order->>Aurora: INSERT order
    Order->>Payment: ProcessPayment()
    Payment->>Aurora: INSERT payment
    Payment-->>Order: PaymentResult
    Order->>SQS: PublishOrderEvent
    Order-->>APIGW: OrderResponse
    APIGW-->>Client: 201 Created

    SQS-->>Notif: ConsumeEvent
    Notif->>Notif: SendNotification
```

## Observability Tool Coverage

This lab covers the following observability tools:

| Category          | Tools Covered                      | AWS Integration             |
| ----------------- | ---------------------------------- | --------------------------- |
| **Metrics**       | Prometheus, VictoriaMetrics, Mimir | AMP (remote write)          |
| **Logging**       | Loki, ClickHouse, Fluent Bit       | CloudWatch Logs, OpenSearch |
| **Tracing**       | Tempo, OTel Collector              | X-Ray (via OTel)            |
| **Visualization** | Grafana                            | AMG                         |
| **Alerting**      | Alertmanager, Grafana OnCall       | CloudWatch Alarms, SNS      |
| **AIOps**         | CloudWatch Investigations          | Bedrock Claude integration  |

> **Note**: This lab focuses on open-source and AWS-native tools. Commercial solutions like Datadog and Dynatrace are covered in separate documentation but not deployed in this lab.

## Learning Outcomes

By completing this lab series, you will be able to:

1. **Design** a production-grade observability architecture for Kubernetes
2. **Deploy** the complete LGTM stack (Loki, Grafana, Tempo, Mimir) with OTel
3. **Configure** multi-backend telemetry pipelines using OTel Collector
4. **Implement** canary deployments with observability-driven analysis
5. **Build** AIOps workflows with CloudWatch Investigations and Bedrock
6. **Analyze** distributed traces to identify performance bottlenecks
7. **Correlate** metrics, logs, and traces for root cause analysis

## References

* [Observability Overview](../../observability/)
* [Prometheus Documentation](../../observability/metrics/01-prometheus.md)
* [Grafana Dashboard](../../observability/grafana/)
* [Loki Documentation](../../observability/logging/01-loki.md)
* [Tempo Documentation](../../observability/tracing/01-tempo.md)
* [OpenTelemetry Documentation](../../observability/tracing/03-opentelemetry.md)
* [ArgoCD Documentation](../../gitops/argocd/)
* [KEDA Documentation](../../autoscaling/01-keda.md)
* [Karpenter Documentation](../../autoscaling/02-karpenter.md)

***

**Ready to begin?** Start with [Part 1: Infrastructure Setup](01-infrastructure-setup-lab.md)
