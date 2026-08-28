# Introducción a la serie de laboratorios

> **Dificultad**: Avanzado **Última actualización**: February 23, 2026

## Descripción general

Esta serie de laboratorios proporciona un recorrido completo y práctico para crear una plataforma de observabilidad full-stack para microservicios basados en Kubernetes. Desplegarás e integrarás múltiples herramientas de observabilidad en dos clústeres EKS, implementando los tres pilares de la observabilidad (Metrics, Logs, Traces) con patrones del mundo real.

La arquitectura simula un entorno de nivel de producción con un **Managed Cluster** que aloja la pila de observabilidad y un **Service Cluster** que ejecuta aplicaciones MSA con instrumentación OTel.

![Descripción general de la arquitectura](../../.gitbook/assets/architecture-overview.png)

## Diagrama de arquitectura

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

## Requisitos previos

Antes de comenzar esta serie de laboratorios, asegúrate de contar con lo siguiente:

| Requisito | Versión  | Comando de verificación        |
| --------- | -------- | ------------------------------ |
| Cuenta de AWS | -        | `aws sts get-caller-identity` |
| AWS CLI   | >= 2.15  | `aws --version`               |
| eksctl    | >= 0.175 | `eksctl version`              |
| kubectl   | >= 1.29  | `kubectl version --client`    |
| Helm      | >= 3.14  | `helm version`                |
| Terraform | >= 1.7   | `terraform version`           |
| k6        | >= 0.49  | `k6 version`                  |
| Docker    | >= 24.0  | `docker --version`            |

### Permisos de IAM necesarios

Tu usuario/rol de AWS necesita los siguientes permisos:

* Acceso completo a EKS
* Acceso completo a EC2 (para grupos de nodos)
* Acceso completo a VPC
* Acceso limitado a IAM (para IRSA)
* Acceso completo a CloudFormation
* Acceso completo a SQS/SNS
* Acceso completo a RDS (para Aurora)
* Acceso completo a OpenSearch
* Acceso completo a Managed Prometheus/Grafana
* Acceso completo a MWAA

## Estimación de costos

> **Advertencia**: Esta serie de laboratorios crea recursos de AWS significativos. A continuación se proporcionan los costos estimados.

| Servicio                  | Configuración                     | Costo por hora (USD) |
| ------------------------- | --------------------------------- | -------------------- |
| Plano de control de EKS   | 2 clústeres                       | $0.20                |
| EC2 (Managed Cluster)     | 3x m5.xlarge                      | $0.58                |
| EC2 (Service Cluster)     | 3x m5.large (+ escalado de Karpenter) | $0.29+            |
| Aurora PostgreSQL         | db.r6g.large (multi-AZ)           | $0.52                |
| OpenSearch                | m6g.large.search (2 nodos)        | $0.25                |
| Amazon Managed Prometheus | Según la ingesta                  | \~$0.10             |
| Amazon Managed Grafana    | 1 espacio de trabajo              | $0.15                |
| MWAA                      | mw1.small                         | $0.31                |
| SQS/SNS                   | Según el uso                      | \~$0.01             |
| **Total estimado**        |                                   | **\~$2.50/hora**    |

**Consejo**: Completa el laboratorio en una sola sesión y ejecuta la limpieza de inmediato para minimizar los costos.

## Secuencia de laboratorios

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

| Parte | Título                                                   | Duración | Temas clave                                     |
| ----- | -------------------------------------------------------- | -------- | ----------------------------------------------- |
| 1     | [Configuración de infraestructura](01-infrastructure-setup-lab.md) | 60 min   | Clústeres EKS, servicios de AWS, ArgoCD         |
| 2     | [Pila de observabilidad](02-observability-stack-lab.md) | 90 min   | OTel, Prometheus, Loki, Tempo, Grafana          |
| 3     | [Despliegue MSA y Canary](03-msa-deployment-lab.md)     | 60 min   | ArgoCD, Argo Rollouts, instrumentación OTel     |
| 4     | [Pruebas de carga y escalado](04-load-testing-scaling-lab.md) | 45 min   | k6, KEDA, Karpenter                             |
| 5     | [Alerting y AIOps](05-alerting-aiops-lab.md)            | 60 min   | Alertmanager, OnCall, investigaciones de CloudWatch |
| 6     | [Tracing distribuido](06-distributed-tracing-lab.md)    | 45 min   | Tempo, TraceQL, correlación Log-Trace           |

## Descripción general de la aplicación MSA

El laboratorio utiliza una aplicación MSA de comercio electrónico de ejemplo con 5 servicios:

| Servicio             | Lenguaje           | Función                         | Dependencias             |
| -------------------- | ------------------ | ------------------------------- | ------------------------ |
| API Gateway          | Go                 | Enrutamiento de solicitudes, autenticación | Order, Payment   |
| Order Service        | Python (FastAPI)   | Gestión de pedidos, inventario  | Aurora, SQS              |
| Payment Service      | Java (Spring Boot) | Procesamiento de pagos          | Aurora                   |
| Notification Service | Node.js (Express)  | Notificaciones por correo electrónico/SMS | Consumidor de SQS |
| Analytics Batch      | Python             | Agregación diaria de analíticas | Aurora, activado por MWAA |

### Flujo de llamadas de servicios

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

## Cobertura de herramientas de observabilidad

Este laboratorio cubre las siguientes herramientas de observabilidad:

| Categoría         | Herramientas cubiertas             | Integración con AWS          |
| ----------------- | ---------------------------------- | ---------------------------- |
| **Metrics**       | Prometheus, VictoriaMetrics, Mimir | AMP (remote write)           |
| **Logging**       | Loki, ClickHouse, Fluent Bit       | CloudWatch Logs, OpenSearch  |
| **Tracing**       | Tempo, OTel Collector              | X-Ray (mediante OTel)        |
| **Visualización** | Grafana                            | AMG                          |
| **Alerting**      | Alertmanager, Grafana OnCall       | CloudWatch Alarms, SNS       |
| **AIOps**         | CloudWatch Investigations          | Integración con Bedrock Claude |

> **Nota**: Este laboratorio se centra en herramientas de código abierto y nativas de AWS. Las soluciones comerciales como Datadog y Dynatrace se tratan en documentación independiente, pero no se despliegan en este laboratorio.

## Resultados de aprendizaje

Al completar esta serie de laboratorios, podrás:

1. **Diseñar** una arquitectura de observabilidad de nivel de producción para Kubernetes
2. **Desplegar** la pila LGTM completa (Loki, Grafana, Tempo, Mimir) con OTel
3. **Configurar** pipelines de telemetría multi-backend mediante OTel Collector
4. **Implementar** despliegues Canary con análisis impulsado por observabilidad
5. **Crear** flujos de trabajo de AIOps con CloudWatch Investigations y Bedrock
6. **Analizar** trazas distribuidas para identificar cuellos de botella de rendimiento
7. **Correlacionar** métricas, logs y trazas para el análisis de causa raíz

## Referencias

* [Descripción general de observabilidad](../../observability/README.md)
* [Documentación de Prometheus](../../observability/metrics/01-prometheus.md)
* [Dashboard de Grafana](../../observability/grafana/README.md)
* [Documentación de Loki](../../observability/logging/01-loki.md)
* [Documentación de Tempo](../../observability/tracing/01-tempo.md)
* [Documentación de OpenTelemetry](../../observability/tracing/03-opentelemetry.md)
* [Documentación de ArgoCD](../../gitops/argocd/README.md)
* [Documentación de KEDA](../../autoscaling/01-keda.md)
* [Documentación de Karpenter](../../autoscaling/02-karpenter.md)

***

**¿Listo para comenzar?** Comienza con [Parte 1: Configuración de infraestructura](01-infrastructure-setup-lab.md)
