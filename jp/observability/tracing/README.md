# 分散トレーシングの概要

> **最終更新**: February 20, 2026

## はじめに

分散トレーシング（Distributed Tracing）は、マイクロサービスアーキテクチャにおいて、リクエストが複数の Service を通過する際の完全な経路を追跡する手法です。単一のリクエストが数十の Service を通過する可能性がある現代のシステムでは、分散トレーシングはパフォーマンスのボトルネックを特定し、問題をトラブルシューティングするために不可欠です。

## 分散トレーシングの必要性

### 従来のモニタリングの限界

マイクロサービス環境では、従来のログとメトリクスだけでは次の質問に答えられません。

- リクエストはどの Service を通過したか？
- 各 Service にはどのくらいの時間がかかったか？
- エラーはどこで発生したか？
- Service 間にはどのような依存関係があるか？

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

## コアコンセプト

### 1. Trace

Trace は、単一のリクエストがたどる完全な経路を表します。リクエストがシステムを通過する際に生成されるすべての操作の集合です。

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

Span は、作業の単一単位を表します。各 Span には次の情報が含まれます。

| フィールド | 説明 | 例 |
|-------|-------------|---------|
| **TraceID** | Trace 全体の一意な識別子 | `abc123def456` |
| **SpanID** | 個々の Span の一意な識別子 | `span789` |
| **ParentSpanID** | 親 Span の識別子 | `span456` |
| **Operation Name** | 操作の名前 | `HTTP GET /api/users` |
| **Start Time** | 開始タイムスタンプ | `2025-02-15T10:30:00Z` |
| **Duration** | 所要時間 | `150ms` |
| **Tags** | メタデータ | `http.status_code=200` |
| **Logs** | イベント記録 | `error: connection timeout` |

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

### 3. Span の関係と階層

Span は親子関係を形成し、ツリー構造を作成します。

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

SpanContext は、Service 間で伝播される Trace 情報です。

```yaml
# SpanContext Components
SpanContext:
  trace_id: "abc123def456789"      # Trace identifier
  span_id: "span789"               # Current Span identifier
  trace_flags: "01"                # Sampling flag
  trace_state: "vendor=value"      # Vendor-specific additional info
```

## コンテキスト伝播

Service 間で Trace コンテキストを渡す方法です。

### W3C Trace Context（推奨）

W3C 標準ヘッダーを使用した伝播：

```http
# HTTP Request Headers
traceparent: 00-abc123def456789012345678901234-span12345678-01
tracestate: rojo=00f067aa0ba902b7,congo=t61rcWkgMzE
```

**traceparent の形式：**
```
version-trace_id-parent_id-trace_flags
00     -abc123...-span1234...-01
```

### B3 伝播（Zipkin 互換）

Zipkin で使用される伝播形式：

```http
# Single header format
b3: abc123def456789-span12345678-1-parent12345678

# Multi-header format
X-B3-TraceId: abc123def456789
X-B3-SpanId: span12345678
X-B3-ParentSpanId: parent12345678
X-B3-Sampled: 1
```

### 伝播形式の比較

| 形式 | ヘッダー | 利点 | 欠点 |
|--------|---------|------------|---------------|
| **W3C Trace Context** | `traceparent`, `tracestate` | 標準的、拡張可能 | 比較的新しい |
| **B3 Single** | `b3` | シンプル、単一ヘッダー | Zipkin 固有 |
| **B3 Multi** | `X-B3-*` | デバッグが容易 | ヘッダーが多い |
| **Jaeger** | `uber-trace-id` | Jaeger に最適化 | ベンダーロックイン |

## サンプリング戦略

すべてのリクエストをトレースすると、コストとパフォーマンスの問題が発生します。サンプリングはこれを管理します。

### Head-based Sampling

リクエスト開始時にサンプリングを決定します。

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

**利点：**
- 実装がシンプル
- オーバーヘッドが低い
- 一貫したサンプリング判断

**欠点：**
- 重要なリクエストを見逃す可能性がある
- エラーやレイテンシーを伴うリクエストをスキップする可能性がある

**設定例：**
```yaml
# OpenTelemetry SDK Configuration
sampling:
  type: parentbased_traceidratio
  ratio: 0.1  # 10% sampling
```

### Tail-based Sampling

リクエスト完了後に、結果に基づいてサンプリングを決定します。

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

**利点：**
- 重要なリクエスト（エラー、レイテンシー）を見逃さない
- よりインテリジェントなサンプリング
- コスト効率が高い

**欠点：**
- 実装が複雑
- メモリ使用量が多い
- すべての Span を一時的に保存する必要がある

**OTEL Collector Tail Sampling の設定：**
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

### サンプリング戦略の比較

| 戦略 | 判断時点 | リソース使用量 | 正確性 | ユースケース |
|----------|---------------|----------------|----------|----------|
| **Head-based** | リクエスト開始時 | 低 | 中 | ほとんどのケース |
| **Tail-based** | リクエスト完了時 | 高 | 高 | エラー／レイテンシー重視 |
| **Adaptive** | 動的 | 中 | 高 | トラフィック変動が大きい場合 |

## Trace・Log・Metric の相関

### TraceID による Log の関連付け

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

### Exemplars による Metric の関連付け

```yaml
# Linking TraceID to Prometheus metrics
http_request_duration_seconds_bucket{le="0.5"} 1000 # {traceID="abc123"}
http_request_duration_seconds_bucket{le="1.0"} 1500 # {traceID="def456"}
```

### Grafana での相関

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

## ソリューションの比較

### 分散トレーシングソリューションの比較

| 機能 | Tempo | X-Ray | Jaeger | Datadog APM | Dynatrace |
|---------|-------|-------|--------|-------------|-----------|
| **タイプ** | オープンソース | AWS マネージド | オープンソース | 商用 SaaS | 商用 SaaS |
| **ストレージ** | Object Storage | AWS 内部 | Cassandra/ES | Datadog | Dynatrace |
| **クエリ言語** | TraceQL | Filter Expressions | - | - | DQL |
| **サンプリング** | Head/Tail | ルールベース | Head | 動的 | 動的 |
| **OTEL サポート** | ネイティブ | ネイティブ | ネイティブ | ネイティブ | ネイティブ |
| **Service Map** | Grafana 統合 | 組み込み | 組み込み | 組み込み | 組み込み |
| **AI 分析** | なし | なし | なし | Watchdog | Davis AI |
| **コスト** | ストレージコストのみ | 使用量ベース | インフラストラクチャコスト | Host/span ベース | Host ベース |
| **EKS 統合** | 手動設定 | ネイティブ | 手動設定 | Agent デプロイ | OneAgent |

### 選定ガイド

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

## ベストプラクティス

### 1. Instrumentation 戦略

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

### 2. Span の命名規則

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

### 3. Tag の標準化

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

## 次のステップ

分散トレーシングの概念を理解したら、以下のセクションで特定のツールの使用方法を学びます。

- [Grafana Tempo](./01-tempo.md): Grafana スタックの分散トレーシングバックエンド
- [AWS X-Ray](./02-xray.md): AWS ネイティブの分散トレーシング
- [OpenTelemetry](./03-opentelemetry.md): 標準化された Instrumentation フレームワーク
- [Dynatrace](./04-dynatrace.md): AI 搭載の APM ソリューション

## クイズ

ツール固有のクイズで知識を確認しましょう。
- [Tempo クイズ](../../quizzes/observability/tracing/01-tempo-quiz.md)
- [X-Ray クイズ](../../quizzes/observability/tracing/02-xray-quiz.md)
- [OpenTelemetry クイズ](../../quizzes/observability/tracing/03-opentelemetry-quiz.md)
- [Dynatrace クイズ](../../quizzes/observability/tracing/04-dynatrace-quiz.md)
