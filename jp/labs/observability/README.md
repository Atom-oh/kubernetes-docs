# ラボシリーズの紹介

> **難易度**: 上級 **最終更新**: February 23, 2026

## 概要

このラボシリーズでは、Kubernetes ベースのマイクロサービス向けフルスタック Observability プラットフォームを構築するための包括的なハンズオンを提供します。2 つの EKS クラスターに複数の Observability ツールをデプロイして統合し、実際のパターンで Observability の 3 本柱（Metrics、Logs、Traces）を実装します。

このアーキテクチャは、Observability スタックをホストする **Managed Cluster** と、OTel instrumentation を備えた MSA アプリケーションを実行する **Service Cluster** から成る本番グレードの環境をシミュレートします。

![Management Cluster の GitOps および Observability スタックから Service Cluster の MSA アプリまで、さらに AWS マネージド Observability バックエンドまでを示すラボ環境アーキテクチャ。](../../.gitbook/assets/en-labs-observability-overview-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-overview-0.html)

## アーキテクチャ図

![OTel instrumentation を備えた MSA アプリケーションを Argo CD が Service Cluster にデプロイし、その autoscaler と OTel agent が telemetry を Managed Cluster の Observability スタックに送信する様子を示すアーキテクチャ図。アプリケーションと Observability スタックはいずれも Aurora、SQS/SNS、MWAA、AMP、CloudWatch、OpenSearch などの AWS マネージドサービスと統合されます。](../../.gitbook/assets/en-labs-observability-README-0.png)

## 前提条件

このラボシリーズを開始する前に、以下がそろっていることを確認してください。

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

### 必要な IAM 権限

AWS user/role には以下の権限が必要です。

* EKS へのフルアクセス
* EC2 へのフルアクセス（node group 用）
* VPC へのフルアクセス
* IAM への限定アクセス（IRSA 用）
* CloudFormation へのフルアクセス
* SQS/SNS へのフルアクセス
* RDS へのフルアクセス（Aurora 用）
* OpenSearch へのフルアクセス
* Managed Prometheus/Grafana へのフルアクセス
* MWAA へのフルアクセス

## コスト見積もり

> **警告**: このラボシリーズでは多くの AWS リソースが作成されます。以下に推定コストを示します。

| サービス                   | 設定                     | 時間あたりのコスト (USD) |
| ------------------------- | --------------------------------- | ----------------- |
| EKS Control Plane         | 2 クラスター                        | $0.20             |
| EC2 (Managed Cluster)     | 3x m5.xlarge                      | $0.58             |
| EC2 (Service Cluster)     | 3x m5.large (+ Karpenter scaling) | $0.29+            |
| Aurora PostgreSQL         | db.r6g.large (multi-AZ)           | $0.52             |
| OpenSearch                | m6g.large.search (2 nodes)        | $0.25             |
| Amazon Managed Prometheus | 取り込み量に基づく                | \~$0.10           |
| Amazon Managed Grafana    | 1 workspace                       | $0.15             |
| MWAA                      | mw1.small                         | $0.31             |
| SQS/SNS                   | 使用量に基づく                    | \~$0.01           |
| **合計見積もり**        |                                   | **\~$2.50/時間**  |

**ヒント**: コストを最小限に抑えるため、ラボは 1 回のセッションで完了し、すぐに cleanup を実行してください。

## ラボの順序

![インフラストラクチャのセットアップから Observability スタック、canary rollout を伴う MSA のデプロイ、load testing と scaling、alerting と AIOps、distributed tracing へと進む、6 部構成の直線的なロードマップ。](../../.gitbook/assets/en-labs-observability-README-1.png)

| パート | タイトル                                                    | 所要時間 | 主なトピック                                      |
| ---- | -------------------------------------------------------- | -------- | ----------------------------------------------- |
| 1    | [インフラストラクチャのセットアップ](01-infrastructure-setup-lab.md)   | 60 分   | EKS クラスター、AWS サービス、ArgoCD              |
| 2    | [Observability スタック](02-observability-stack-lab.md)     | 90 分   | OTel、Prometheus、Loki、Tempo、Grafana          |
| 3    | [MSA のデプロイと Canary](03-msa-deployment-lab.md)      | 60 分   | ArgoCD、Argo Rollouts、OTel instrumentation     |
| 4    | [Load Testing と Scaling](04-load-testing-scaling-lab.md) | 45 分   | k6、KEDA、Karpenter                             |
| 5    | [Alerting と AIOps](05-alerting-aiops-lab.md)             | 60 分   | Alertmanager、OnCall、CloudWatch Investigations |
| 6    | [Distributed Tracing](06-distributed-tracing-lab.md)     | 45 分   | Tempo、TraceQL、Log-Trace の相関           |

## MSA アプリケーションの概要

このラボでは、5 つのサービスから成るサンプル e-commerce MSA アプリケーションを使用します。

| サービス              | 言語           | 役割                            | 依存先              |
| -------------------- | ------------------ | ------------------------------- | ------------------------- |
| API Gateway          | Go                 | リクエストルーティング、認証 | Order、Payment            |
| Order Service        | Python (FastAPI)   | Order 管理、inventory     | Aurora、SQS               |
| Payment Service      | Java (Spring Boot) | Payment 処理              | Aurora                    |
| Notification Service | Node.js (Express)  | Email/SMS 通知         | SQS consumer              |
| Analytics Batch      | Python             | 日次 analytics 集計     | Aurora、MWAA によりトリガー |

### サービス呼び出しフロー

![クライアントの order リクエストが API gateway を経由して Order Service に流れ、Aurora に書き込み、Payment Service を呼び出して課金と支払いの記録を行うシーケンス図。その後、order event を publish し、Notification Service が非同期に consume する一方で、Order Service と gateway はクライアントに成功を返します。](../../.gitbook/assets/en-labs-observability-README-2.png)

## Observability ツールの対象範囲

このラボでは、以下の Observability ツールを扱います。

| カテゴリー          | 対象ツール                      | AWS 統合             |
| ----------------- | ---------------------------------- | --------------------------- |
| **Metrics**       | Prometheus、VictoriaMetrics、Mimir | AMP (remote write)          |
| **Logging**       | Loki、ClickHouse、Fluent Bit       | CloudWatch Logs、OpenSearch |
| **Tracing**       | Tempo、OTel Collector              | X-Ray (via OTel)            |
| **Visualization** | Grafana                            | AMG                         |
| **Alerting**      | Alertmanager、Grafana OnCall       | CloudWatch Alarms、SNS      |
| **AIOps**         | CloudWatch Investigations          | Bedrock Claude integration  |

> **注記**: このラボでは、オープンソースおよび AWS ネイティブのツールに焦点を当てます。Datadog や Dynatrace などの商用ソリューションは別のドキュメントで扱いますが、このラボではデプロイしません。

## 学習成果

このラボシリーズを完了すると、以下ができるようになります。

1. Kubernetes 向けの本番グレード Observability アーキテクチャを **設計** する
2. OTel とともに完全な LGTM スタック（Loki、Grafana、Tempo、Mimir）を **デプロイ** する
3. OTel Collector を使用して multi-backend telemetry pipeline を **構成** する
4. Observability 主導の分析を用いた canary deployment を **実装** する
5. CloudWatch Investigations と Bedrock による AIOps workflow を **構築** する
6. distributed trace を **分析** して performance bottleneck を特定する
7. root cause analysis のために metrics、logs、traces を **相関付ける**

## 参考資料

* [Observability の概要](../../observability/README.md)
* [Prometheus ドキュメント](../../observability/metrics/01-prometheus.md)
* [Grafana Dashboard](../../observability/grafana/README.md)
* [Loki ドキュメント](../../observability/logging/01-loki.md)
* [Tempo ドキュメント](../../observability/tracing/01-tempo.md)
* [OpenTelemetry ドキュメント](../../observability/tracing/03-opentelemetry.md)
* [ArgoCD ドキュメント](../../gitops/argocd/README.md)
* [KEDA ドキュメント](../../autoscaling/01-keda.md)
* [Karpenter ドキュメント](../../autoscaling/02-karpenter.md)

***

**開始する準備はできましたか？** [パート 1: インフラストラクチャのセットアップ](01-infrastructure-setup-lab.md)から開始してください
