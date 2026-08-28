# Observability の概要

> **最終更新**: February 20, 2026

## はじめに

現代の分散システム、特に Kubernetes ベースのマイクロサービスアーキテクチャでは、外部出力からシステムの内部状態を観測・理解する能力が不可欠です。これを **Observability** と呼びます。

## Observability と Monitoring

Observability と Monitoring はしばしば同じ意味で使われますが、両者には根本的な違いがあります。

| 観点 | Monitoring | Observability |
|--------|-----------|---------------|
| **アプローチ** | 事前定義されたメトリクスとしきい値に基づく | システム出力を通じて内部状態を推論する |
| **質問の種類** | 「何が問題だったのか？」（What） | 「なぜ問題が起きたのか？」（Why） |
| **データ範囲** | 既知の問題の検出 | 未知の問題の探索 |
| **柔軟性** | 事前定義されたダッシュボード | 動的なクエリと探索 |
| **複雑性** | 単純なシステムに適している | 複雑な分散システムに不可欠 |

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

## Observability の 3 つの柱

Observability は 3 つの中核となるデータタイプで構成されます。

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

Logs は、システム内で発生する個々のイベントの記録です。

**特徴:**
- 個別かつ不変のイベント記録
- タイムスタンプとコンテキスト情報を含む
- 構造化（JSON）または非構造化形式
- デバッグと監査に不可欠

**ユースケース:**
- エラーと例外の追跡
- セキュリティ監査
- コンプライアンス
- 詳細なデバッグ

**ツール:** Loki, Elasticsearch, CloudWatch Logs, Fluent Bit

### 2. Metrics

Metrics は、時間の経過に伴う数値測定値です。

**特徴:**
- 時系列データとして保存される
- 集計および数学的演算をサポートする
- 高いストレージ効率
- 傾向分析に適している

**主要な Metric タイプ:**
- **Counter**: 累積的に増加する値（例: リクエスト数）
- **Gauge**: 現在の状態を表す値（例: CPU 使用率）
- **Histogram**: 分布の測定値（例: 応答時間）
- **Summary**: 分位数の計算

**ツール:** Prometheus, VictoriaMetrics, CloudWatch Metrics, Datadog

### 3. Traces

Traces は、分散システム全体にわたるリクエストの完全な経路を追跡します。

**特徴:**
- サービス間のリクエストフローを可視化する
- 各ステップのレイテンシーを測定する
- ボトルネックを特定する
- 依存関係を分析する

**コンポーネント:**
- **Trace**: 単一リクエストの完全な経路
- **Span**: 単一の作業単位
- **SpanContext**: サービス間で伝播されるコンテキスト

**ツール:** Tempo, Jaeger, X-Ray, Zipkin, Datadog APM

## 3 つの柱の相関関係

3 つの柱は独立しているのではなく相互に接続されており、強力な分析機能を提供します。

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

### Trace から Log への相関付け

特定のリクエストに関連するすべての Log を追跡するため、Logs に TraceID を含めます。

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

### Metric から Trace への相関付け（Exemplars）

異常発生時にリクエストを追跡できるよう、TraceID を Metrics にリンクします。

```yaml
# Prometheus Exemplar
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
```

## OpenTelemetry と標準化

OpenTelemetry（OTel）は、Observability データ収集の業界標準です。

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

**OpenTelemetry の利点:**
- ベンダー中立の標準
- 複数の言語 SDK をサポート
- Auto-instrumentation 機能
- 複数バックエンドのサポート
- 活発なコミュニティ

## EKS 環境向け Observability 戦略

Amazon EKS で効果的な Observability を実装するための戦略です。

### 1. レイヤーベースの Observability

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

### 2. 推奨ツールスタック

| 機能 | Open Source | AWS Native | 商用 |
|----------|-------------|------------|------------|
| Metrics | Prometheus, VictoriaMetrics | CloudWatch, AMP | Datadog, New Relic |
| Logs | Loki, Elasticsearch | CloudWatch Logs | Splunk, Datadog |
| Traces | Tempo, Jaeger | X-Ray | Datadog APM, Dynatrace |
| 可視化 | Grafana | CloudWatch Dashboards | Datadog, Dynatrace |

### 3. コスト最適化戦略

- **Sampling**: Trace データのサンプリングによりコストを削減する
- **Retention Policies**: データ保持期間を最適化する
- **Tiered Storage**: 古いデータをより低コストなストレージへ移動する
- **Aggregation**: 詳細データではなく集計データを保存する

## Observability 成熟度モデル

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

| レベル | 特徴 | ツール例 |
|-------|-----------------|---------------|
| レベル 1 | 基本的な Log/Metric 収集 | kubectl logs, CloudWatch |
| レベル 2 | 集中型 Observability | Loki, Prometheus, Grafana |
| レベル 3 | 3 つの柱の相関付け | Tempo, Exemplars, TraceID |
| レベル 4 | AIOps、自動異常検出 | Datadog Watchdog, Dynatrace Davis |

## セクションガイド

この Observability セクションは、以下のように構成されています。

### [Logging](./logging/README.md)
Log の収集、保存、分析のためのツールと戦略:
- Loki: 軽量な Log 集約システム
- Fluent Bit: 高性能な Log コレクター
- CloudWatch Logs: AWS ネイティブの Logging

### [Metrics](./metrics/README.md)
時系列 Metric の収集と分析:
- Prometheus: 業界標準の Metrics システム
- VictoriaMetrics: 高性能な Prometheus 代替
- CloudWatch Metrics: AWS ネイティブの Metrics

### [Tracing](./tracing/README.md)
分散 Tracing とリクエストフロー分析:
- Tempo: Grafana の分散 Tracing バックエンド
- X-Ray: AWS ネイティブの分散 Tracing
- OpenTelemetry: 標準化された Instrumentation
- Dynatrace: AI 搭載 APM

### [Grafana (Dashboards)](./grafana/README.md)
統合された可視化とダッシュボード:
- データソース統合
- ダッシュボード設計パターン
- アラート設定

## はじめに

Observability の実装を開始するには、次の順序が推奨されます。

1. **Metric 収集を設定する**: Prometheus または VictoriaMetrics をデプロイする
2. **Log 収集を設定する**: Loki と Fluent Bit をデプロイする
3. **Tracing を設定する**: Tempo または X-Ray をデプロイする
4. **可視化**: Grafana ですべてのデータソースを接続する
5. **相関付け**: TraceID ベースのリンクを設定する

## 参考資料

- [OpenTelemetry 公式ドキュメント](https://opentelemetry.io/docs/)
- [Grafana LGTM Stack](https://grafana.com/oss/lgtm-stack/)
- [AWS Observability ベストプラクティス](https://aws-observability.github.io/observability-best-practices/)
- [SRE Workbook - Monitoring](https://sre.google/workbook/monitoring/)
