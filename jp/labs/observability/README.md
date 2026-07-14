# ラボシリーズの紹介

> **難易度**: 上級 **最終更新**: February 23, 2026

## 概要

このラボシリーズでは、Kubernetes ベースのマイクロサービス向けフルスタック Observability プラットフォームを構築する包括的なハンズオンを提供します。2 つの EKS Cluster にわたって複数の Observability ツールをデプロイおよび統合し、実践的なパターンを用いて Observability の 3 本柱（Metrics、Logs、Traces）を実装します。

このアーキテクチャは、Observability Stack をホストする **Managed Cluster** と、OTel instrumentation を備えた MSA アプリケーションを実行する **Service Cluster** で構成される、本番グレードの環境をシミュレートします。

![アーキテクチャ概要](../../.gitbook/assets/architecture-overview.png)

## アーキテクチャ図

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

## 前提条件

このラボシリーズを開始する前に、以下を準備してください。

| 要件 | バージョン  | 確認コマンド          |
| ----------- | -------- | ----------------------------- |
| AWS Account | -        | `aws sts get-caller-identity` |
| AWS CLI     | >= 2.15  | `aws --version`               |
| eksctl      | >= 0.175 | `eksctl version`              |
| kubectl     | >= 1.29  | `kubectl version --client`    |
| Helm        | >= 3.14  | `helm version`                |
| Terraform   | >= 1.7   | `terraform version`           |
| k6          | >= 0.49  | `k6 version`                  |
| Docker      | >= 24.0  | `docker --version`            |

### 必要な IAM Permissions

AWS user/role には以下の Permissions が必要です。

* EKS のフルアクセス
* EC2 のフルアクセス（node groups 用）
* VPC のフルアクセス
* IAM の限定アクセス（IRSA 用）
* CloudFormation のフルアクセス
* SQS/SNS のフルアクセス
* RDS のフルアクセス（Aurora 用）
* OpenSearch のフルアクセス
* Managed Prometheus/Grafana のフルアクセス
* MWAA のフルアクセス

## コスト見積もり

> **警告**: このラボシリーズでは多くの AWS リソースを作成します。推定コストを以下に示します。

| Service                   | 構成                     | 時間あたりのコスト（USD） |
| ------------------------- | --------------------------------- | ----------------- |
| EKS Control Plane         | 2 clusters                        | $0.20             |
| EC2 (Managed Cluster)     | 3x m5.xlarge                      | $0.58             |
| EC2 (Service Cluster)     | 3x m5.large (+ Karpenter scaling) | $0.29+            |
| Aurora PostgreSQL         | db.r6g.large (multi-AZ)           | $0.52             |
| OpenSearch                | m6g.large.search (2 nodes)        | $0.25             |
| Amazon Managed Prometheus | インジェスト量に基づく                | \~$0.10           |
| Amazon Managed Grafana    | 1 workspace                       | $0.15             |
| MWAA                      | mw1.small                         | $0.31             |
| SQS/SNS                   | 使用量に基づく                    | \~$0.01           |
| **合計見積もり**        |                                   | **\~$2.50/時間**  |

**ヒント**: コストを最小限に抑えるため、ラボは 1 回のセッションで完了し、すぐに cleanup を実行してください。

## ラボの順序

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

| パート | タイトル                                                    | 所要時間 | 主なトピック                                      |
| ---- | -------------------------------------------------------- | -------- | ----------------------------------------------- |
| 1    | [Infrastructure Setup](01-infrastructure-setup-lab.md)   | 60 分   | EKS clusters、AWS services、ArgoCD              |
| 2    | [Observability Stack](02-observability-stack-lab.md)     | 90 分   | OTel、Prometheus、Loki、Tempo、Grafana          |
| 3    | [MSA Deployment & Canary](03-msa-deployment-lab.md)      | 60 分   | ArgoCD、Argo Rollouts、OTel instrumentation     |
| 4    | [Load Testing & Scaling](04-load-testing-scaling-lab.md) | 45 分   | k6、KEDA、Karpenter                             |
| 5    | [Alerting & AIOps](05-alerting-aiops-lab.md)             | 60 分   | Alertmanager、OnCall、CloudWatch Investigations |
| 6    | [Distributed Tracing](06-distributed-tracing-lab.md)     | 45 分   | Tempo、TraceQL、Log-Trace 相関           |

## MSA アプリケーションの概要

このラボでは、5 つの Service で構成されるサンプル E コマース MSA アプリケーションを使用します。

| Service              | 言語           | 役割                            | 依存関係              |
| -------------------- | ------------------ | ------------------------------- | ------------------------- |
| API Gateway          | Go                 | リクエストルーティング、認証 | Order、Payment            |
| Order Service        | Python (FastAPI)   | 注文管理、在庫管理     | Aurora、SQS               |
| Payment Service      | Java (Spring Boot) | 決済処理              | Aurora                    |
| Notification Service | Node.js (Express)  | Email/SMS 通知         | SQS consumer              |
| Analytics Batch      | Python             | 日次分析の集計     | Aurora、MWAA によりトリガー |

### Service 呼び出しフロー

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

## Observability ツールの対象範囲

このラボでは、以下の Observability ツールを扱います。

| カテゴリ          | 対象ツール                      | AWS 統合             |
| ----------------- | ---------------------------------- | --------------------------- |
| **Metrics**       | Prometheus、VictoriaMetrics、Mimir | AMP (remote write)          |
| **Logging**       | Loki、ClickHouse、Fluent Bit       | CloudWatch Logs、OpenSearch |
| **Tracing**       | Tempo、OTel Collector              | X-Ray (via OTel)            |
| **Visualization** | Grafana                            | AMG                         |
| **Alerting**      | Alertmanager、Grafana OnCall       | CloudWatch Alarms、SNS      |
| **AIOps**         | CloudWatch Investigations          | Bedrock Claude integration  |

> **注記**: このラボは、オープンソースおよび AWS ネイティブのツールに焦点を当てています。Datadog や Dynatrace などの商用ソリューションは別のドキュメントで扱いますが、このラボではデプロイしません。

## 学習成果

このラボシリーズを完了すると、以下のことができるようになります。

1. Kubernetes 向けの本番グレード Observability アーキテクチャを **設計**する
2. OTel を使用して完全な LGTM Stack（Loki、Grafana、Tempo、Mimir）を **デプロイ**する
3. OTel Collector を使用したマルチバックエンド Telemetry Pipeline を **設定**する
4. Observability 主導の分析を用いた Canary Deployment を **実装**する
5. CloudWatch Investigations と Bedrock を使用した AIOps Workflow を **構築**する
6. 分散 Trace を **分析**してパフォーマンスのボトルネックを特定する
7. 根本原因分析のために Metrics、Logs、Traces を **相関付け**る

## 参考資料

* [Observability の概要](../../observability/)
* [Prometheus ドキュメント](../../observability/metrics/01-prometheus.md)
* [Grafana Dashboard](../../observability/grafana/)
* [Loki ドキュメント](../../observability/logging/01-loki.md)
* [Tempo ドキュメント](../../observability/tracing/01-tempo.md)
* [OpenTelemetry ドキュメント](../../observability/tracing/03-opentelemetry.md)
* [ArgoCD ドキュメント](../../gitops/argocd/)
* [KEDA ドキュメント](../../autoscaling/01-keda.md)
* [Karpenter ドキュメント](../../autoscaling/02-karpenter.md)

***

**開始する準備はできましたか？** [Part 1: Infrastructure Setup](01-infrastructure-setup-lab.md) から始めましょう
