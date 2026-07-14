# 基本概念

このドキュメントでは、Istio の中核となる概念とアーキテクチャを説明します。Istio を効果的に使用するには、これらの基本概念を理解することが重要です。

## 目次

1. [背景と歴史](02-basic-concepts.md#background-and-history)
2. [Istio を選ぶ理由](02-basic-concepts.md#why-istio)
3. [Istio アーキテクチャ](02-basic-concepts.md#istio-architecture)
4. [デプロイメントモード: Sidecar と Ambient](02-basic-concepts.md#deployment-modes-sidecar-vs-ambient)
5. [コアリソース](02-basic-concepts.md#core-resources)
6. [トラフィック管理の概念](02-basic-concepts.md#traffic-management-concepts)
7. [セキュリティの概念](02-basic-concepts.md#security-concepts)
8. [可観測性の概念](02-basic-concepts.md#observability-concepts)
9. [Namespace と Service Mesh](02-basic-concepts.md#namespaces-and-service-mesh)
10. [次のステップ](02-basic-concepts.md#next-steps)

## 背景と歴史

### Service Mesh の誕生

#### Microservices の課題

2010 年代初頭、企業はモノリシックアプリケーションを Microservices に分割し始めました。

```mermaid
flowchart TB
    subgraph Before[Monolithic Era]
        M[Monolithic<br/>Application]
        M -->|Single process| M
    end

    subgraph After[Microservices Era]
        S1[Service A]
        S2[Service B]
        S3[Service C]
        S4[Service D]
        S5[Service E]

        S1 --> S2
        S1 --> S3
        S2 --> S4
        S3 --> S4
        S4 --> S5
    end

    Before -.->|Transition| After

    %% Style definitions
    classDef monolith fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef micro fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class M monolith;
    class S1,S2,S3,S4,S5 micro;
```

**新たな問題**:

| 問題                            | 説明                                         | 影響                           |
| ------------------------------- | -------------------------------------------- | ------------------------------ |
| **サービス間通信**              | ネットワーク呼び出しの増加                   | レイテンシー、障害伝播         |
| **可観測性**                    | 分散トレーシングが必要                       | デバッグの困難さ               |
| **セキュリティ**                | サービス間の認証・暗号化                     | mTLS 実装の複雑さ              |
| **トラフィック制御**            | Canary デプロイ、A/B テスト                  | アプリケーションコードの変更   |
| **障害処理**                    | Circuit Breaker、Retry                       | サービスごとの実装             |

#### 初期の解決策: ライブラリ

**問題点**:

* 言語ごとにライブラリを開発する必要がある（Java 用の Hystrix、Go 用の別ライブラリなど）
* アプリケーションコードとの密結合
* 更新時にはすべてのサービスを再デプロイする必要がある
* 複雑なバージョン管理

```mermaid
flowchart LR
    subgraph App1[Java Service]
        J[Application Code]
        H[Hystrix<br/>Netflix OSS]
    end

    subgraph App2[Go Service]
        G[Application Code]
        L[Go Library]
    end

    subgraph App3[Python Service]
        P[Application Code]
        R[Requests + Retry]
    end

    J --- H
    G --- L
    P --- R

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lib fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class J,G,P app;
    class H,L,R lib;
```

**Service Mesh の考え方**: ネットワークロジックをアプリケーションからインフラストラクチャ層へ移動する

### Envoy Proxy の誕生

#### Lyft の課題

**2015 年の Lyft** は、次の問題を抱えていました。

* 200 以上の Microservices を運用
* 多様な言語とフレームワーク（Python、Go、Java など）
* 既存の Proxy（HAProxy、NGINX）では不十分
  * 動的な設定変更が困難
  * 可観測性が不足
  * 高度なルーティング機能が限定的

#### Matt Klein と Envoy

**Matt Klein**（Lyft のエンジニア）は、2016 年に Envoy をオープンソース化しました。

**Envoy が解決した問題**:

```mermaid
flowchart TB
    subgraph Problems[Existing Proxy Problems]
        P1[Static configuration<br/>File-based]
        P2[Limited<br/>metrics]
        P3[Complex<br/>restart]
        P4[Simple<br/>routing]
    end

    subgraph Solutions[Envoy's Solutions]
        S1[Dynamic API<br/>xDS Protocol]
        S2[Rich<br/>statistics/tracing]
        S3[Hot Restart<br/>Zero downtime]
        S4[Advanced L7<br/>routing]
    end

    P1 -.->|Solved| S1
    P2 -.->|Solved| S2
    P3 -.->|Solved| S3
    P4 -.->|Solved| S4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef solution fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class S1,S2,S3,S4 solution;
```

**Envoy の主な機能**:

1. **プロセス外アーキテクチャ**: アプリケーションとは別プロセス
2. **xDS API**: 動的な設定更新
3. **L7 Proxy**: HTTP/2、gRPC、WebSocket をサポート
4. **可観測性**: 詳細なメトリクス、トレーシング、ログ
5. **パフォーマンス**: C++ で記述され、高性能

#### CNCF への採用

**タイムライン**:

* **2016 年 9 月**: Envoy をオープンソース化
* **2017 年 9 月**: CNCF プロジェクト（Incubating）として採用
* **2018 年 11 月**: CNCF Graduated プロジェクトに昇格

### Istio の誕生と歴史

#### Google、IBM、Lyft の協業

**2017 年 5 月**、Google、IBM、Lyft は協力して Istio を発表しました。

```mermaid
flowchart LR
    subgraph Companies[Participating Companies]
        G[Google<br/>Kubernetes experience]
        I[IBM<br/>Enterprise requirements]
        L[Lyft<br/>Envoy Proxy]
    end

    subgraph Istio[Istio Service Mesh]
        CP[Control Plane<br/>Google led]
        DP[Data Plane<br/>Envoy-based]
    end

    G --> CP
    I --> CP
    L --> DP

    %% Style definitions
    classDef company fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class G,I,L company;
    class CP,DP component;
```

**各社の貢献**:

| 企業       | 主な貢献             | 理由                           |
| ---------- | -------------------- | ------------------------------ |
| **Google** | Control Plane の設計 | Borg、Kubernetes の経験        |
| **IBM**    | Enterprise 機能      | Enterprise 顧客の要件          |
| **Lyft**   | Envoy Proxy          | 本番環境で実証済みの Proxy     |

#### Istio のバージョン履歴

**主なマイルストーン**:

```mermaid
timeline
    title Istio Major Version History
    2017-05 : Istio 0.1 announced
    2018-07 : Istio 1.0 : Production ready
    2019-03 : Istio 1.1 : Performance improvements
    2020-03 : Istio 1.5 : Istiod consolidation
    2021-05 : Istio 1.10 : Discovery Selectors
    2022-02 : Istio 1.13 : Gateway API support
    2023-11 : Istio 1.20 : Ambient Mode
    2024-05 : Istio 1.22 : Stability improvements
    2025-01 : Istio 1.28 : Current version
```

**バージョン 1.5（2020 年 3 月）- 重要な転換点**:

以前のアーキテクチャ（Istio 1.4 以前）:

```
Separated into individual components:
- Mixer (policy/telemetry)
- Pilot (traffic management)
- Citadel (certificate management)
- Galley (configuration validation)
```

新しいアーキテクチャ（Istio 1.5 以降、現在の 1.28）:

```
Istiod (consolidated into single binary)
├── Pilot functionality (Service Discovery, Traffic Management)
├── Citadel functionality (Certificate Authority, Identity)
└── Galley functionality (Configuration Validation)

Mixer completely removed (functionality moved to Envoy)
```

**変更の理由**:

* 複雑性の削減（4 コンポーネント → 1）
* パフォーマンスの向上（Mixer の削除によりレイテンシーを 50% 削減）
* 運用の簡素化（単一プロセスの管理）
* リソース効率（メモリ、CPU 使用量の削減）

## Istio を選ぶ理由

Kubernetes はコンテナオーケストレーションを提供しますが、Microservices 間の複雑な通信管理には制限があります。Istio は、これらの問題を解決するための Service Mesh ソリューションです。

### Microservices の課題

```mermaid
flowchart TB
    subgraph Problems["Microservices Challenges"]
        P1[Traffic Management<br/>Complex routing]
        P2[Security<br/>Inter-service encryption]
        P3[Observability<br/>Difficult debugging]
        P4[Resilience<br/>Failure handling]
    end

    subgraph Without["Without Istio"]
        W1[Direct implementation<br/>in application code]
        W2[Duplicate code<br/>in each service]
        W3[Inconsistent<br/>implementation]
        W4[Difficult<br/>maintenance]
    end

    subgraph With["Using Istio"]
        I1[Automatic handling<br/>at infrastructure level]
        I2[Central management<br/>with declarative config]
        I3[Consistent<br/>policy application]
        I4[Add features<br/>without code changes]
    end

    P1 & P2 & P3 & P4 -->|Traditional approach| W1
    W1 --> W2 --> W3 --> W4

    P1 & P2 & P3 & P4 -->|Istio| I1
    I1 --> I2 --> I3 --> I4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef without fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef with fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class W1,W2,W3,W4 without;
    class I1,I2,I3,I4 with;
```

### Istio が提供する中核的な価値

#### 1. トラフィック管理

**問題**: 新しいバージョンをデプロイする際に、トラフィックを安全に移行したい。

**Istio のソリューション**:

```yaml
# Canary deployment without code changes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # Existing version 90%
    - destination:
        host: reviews
        subset: v2
      weight: 10  # New version 10%
```

**利点**:

* アプリケーションコードの変更が不要
* トラフィック分割をリアルタイムで調整可能
* 自動ロールバックが可能
* A/B テスト、Blue/Green デプロイをサポート

#### 2. セキュリティ

**問題**: サービス間通信を暗号化および認証したい。

**Istio のソリューション**:

```yaml
# Automatic mTLS enablement
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Automatic encryption for all inter-service communication
```

**利点**:

* 証明書の自動発行と更新
* Service Identity の自動検証
* きめ細かな権限制御
* Zero Trust ネットワークの実装

#### 3. 可観測性

**問題**: 数十の Microservices にまたがるリクエストフローの追跡が困難。

**Istio のソリューション**:

* メトリクスの自動生成（Latency、Traffic、Errors、Saturation）
* 分散トレーシング
* Service トポロジーの可視化

**利点**:

* ボトルネックの自動特定
* エラーの根本原因を迅速に特定
* Service ステータスのリアルタイム監視

#### 4. レジリエンス

**問題**: 1 つの Service の障害がシステム全体に伝播する。

**Istio のソリューション**:

```yaml
# Automatic Circuit Breaker configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**利点**:

* 障害の分離（Circuit Breaker）
* 自動 Retry と Timeout
* 異常なインスタンスの自動除外
* トラフィック制限（Rate Limiting）

### Istio を使用するタイミング

**✅ Istio が適している場合:**

1. **Microservices アーキテクチャ**
   * 10 個以上の Service
   * Service 間の複雑な依存関係
   * 頻繁なデプロイ
2. **高度なトラフィック管理が必要**
   * Canary デプロイ、A/B テスト
   * きめ細かなルーティング制御
   * Traffic Mirroring
3. **強力なセキュリティ要件**
   * サービス間暗号化が必須
   * きめ細かなアクセス制御
   * 規制遵守
4. **可観測性とデバッグ**
   * 複雑なサービス間問題の追跡
   * パフォーマンスボトルネックの特定
   * SLO/SLA の監視

**❌ Istio が過剰となる可能性がある場合:**

1. **シンプルなアプリケーション**
   * 少数の Service（5 未満）
   * シンプルな要件
   * Kubernetes Ingress で十分
2. **リソース制約**
   * 小規模な Cluster
   * リソースオーバーヘッドを許容できない
   * Sidecar のメモリコストが負担
3. **運用能力の不足**
   * 学習時間が不足
   * 専任の Platform Team がいない
   * よりシンプルなソリューションを優先

### 代替手段との比較

#### Kubernetes Ingress と Istio

| 機能              | Kubernetes Ingress | Istio                             |
| ----------------- | ------------------ | --------------------------------- |
| **対象範囲**      | 外部 → Cluster     | 外部 + 内部のサービス間通信       |
| **ルーティング**  | 基本（Path、Host） | 高度（Header、Cookie など）       |
| **mTLS**          | 手動設定           | 自動                              |
| **可観測性**      | 限定的             | 豊富                              |
| **複雑性**        | 低                 | 高                                |
| **ユースケース**  | シンプルなアプリ   | Microservices                     |

#### AWS VPC Lattice と Istio

詳細な比較については、[AWS 統合](04-aws-integration.md#istio-vs-other-solutions-comparison)ドキュメントを参照してください。

**概要**:

* **VPC Lattice**: AWS マネージド、シンプル、VPC/Account をまたぐ通信
* **Istio**: オープンソース、強力な機能、Kubernetes 専用、きめ細かな制御

#### Linkerd と Istio

| 特性               | Istio     | Linkerd            |
| ------------------ | --------- | ------------------ |
| **複雑性**         | 高        | 低                 |
| **機能**           | 非常に豊富 | コア機能のみ       |
| **リソース**       | 高        | 低                 |
| **学習曲線**       | 急        | 緩やか             |
| **コミュニティ**   | 大        | 小                 |

**選択ガイド**:

* 高度な機能と柔軟性が必要 → **Istio**
* シンプルで軽量な Mesh が必要 → **Linkerd**

## デプロイメントモード: Sidecar と Ambient

Istio は、**Sidecar Mode** と **Ambient Mode** の 2 つのデプロイメントモードをサポートします。

### Sidecar Mode（デフォルト）

各アプリケーション Pod に Envoy Proxy を Sidecar コンテナとして注入します。

```mermaid
flowchart LR
    subgraph Pod["Pod"]
        App[Application<br/>Container]
        Envoy[Envoy Proxy<br/>Sidecar]
    end

    External[External Request] -->|Traffic| Envoy
    Envoy -->|Local| App
    App -->|Outbound call| Envoy
    Envoy -->|Network| Target[Target Service]

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class External,Target default;
```

**利点:**

* 成熟しており安定している
* すべての Istio 機能をサポート
* Pod ごとのきめ細かな制御

**欠点:**

* リソースオーバーヘッド（Pod ごとに Envoy）
* 起動時間の増加（Init Container）
* 複雑な権限設定（iptables）

### Ambient Mode（新しいアプローチ）

Sidecar を使用せず、Node レベルでトラフィックを処理します。

```mermaid
flowchart TB
    subgraph Node["Worker Node"]
        subgraph Pod1["Pod 1"]
            App1[Application<br/>No sidecar]
        end

        subgraph Pod2["Pod 2"]
            App2[Application<br/>No sidecar]
        end

        Ztunnel[ztunnel<br/>1 per node<br/>L4 proxy]
        Waypoint[Waypoint Proxy<br/>L7 proxy<br/>Optional]
    end

    App1 <-->|Transparent redirect| Ztunnel
    App2 <-->|Transparent redirect| Ztunnel
    Ztunnel <-->|When L7 needed| Waypoint

    %% Style definitions
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2 userApp;
    class Ztunnel,Waypoint proxy;
```

**利点:**

* 低いリソース使用量（Node ごとに 1 つ）
* Pod の高速な起動
* シンプルな運用
* L7 機能を段階的に適用可能

**欠点:**

* 比較的新しい技術（成熟度が低い）
* 一部の高度な機能に制限がある
* Pod ごとのきめ細かな制御が難しい

### 比較表

| 特性                       | Sidecar Mode                | Ambient Mode                   |
| -------------------------- | --------------------------- | ------------------------------ |
| **リソース使用量**         | 高（Pod ごと）              | 低（Node ごと）                |
| **起動時間**               | 遅い（Init Container）      | 速い                           |
| **運用の複雑性**           | 高                          | 低                             |
| **L4 機能**                | サポート済み                | サポート済み                   |
| **L7 機能**                | 完全サポート                | 任意（Waypoint）               |
| **成熟度**                 | 高                          | 中                             |
| **移行**                   | -                           | 既存の Sidecar から移行可能    |
| **推奨用途**               | 高度な L7 機能が必要        | リソース効率を優先             |

### 選択ガイド

**Sidecar Mode を選択する場合:**

* すべての Istio 機能を活用する必要がある
* Pod ごとのきめ細かなポリシー制御が必要
* 本番環境で実証済みの安定性が必要

**Ambient Mode を選択する場合:**

* リソース効率が重要
* シンプルな L4 機能のみが必要
* L7 機能を段階的に追加する予定

**詳細**については、[Advanced: Ambient Mode](advanced/01-ambient-mode.md)ドキュメントを参照してください。

## Istio アーキテクチャ

Istio は、**Control Plane** と **Data Plane** の 2 つの主要コンポーネントで構成されます。

| コンポーネント                | 説明                                                                                               |
| ---------------------------- | -------------------------------------------------------------------------------------------------- |
| **Control Plane (istiod)**   | Service Discovery、設定配布、証明書管理を担う中央制御システム                                      |
| **Data Plane (Envoy Proxy)** | 各 Pod に Sidecar としてデプロイされ、実際のトラフィック（ルーティング、mTLS、メトリクス）を処理   |

**詳細なアーキテクチャ構造、内部動作原理、トラフィックインターセプトの仕組み**については、[アーキテクチャドキュメント](03-architecture.md)を参照してください。

## コアリソース

Istio は、設定を管理するために Kubernetes Custom Resource Definitions（CRD）を使用します。

### 1. VirtualService

VirtualService は、リクエストを Service にルーティングする方法を定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews  # Target service
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2  # Route specific user to v2
  - route:
    - destination:
        host: reviews
        subset: v1  # Route to v1 by default
```

**主な機能**:

* Path ベースのルーティング（Path、Header、Query Parameter）
* トラフィック分割（Canary、A/B テスト）
* Retry、Timeout、Fault Injection
* URL Rewrite、Header 操作

### 2. DestinationRule

DestinationRule は、Service の Subset（バージョン）を定義し、トラフィックポリシーを適用します。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # Load balancing algorithm
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: v3
    labels:
      version: v3
```

**主な機能**:

* Service バージョン（Subset）の定義
* Load Balancing アルゴリズム
* Connection Pool の設定
* Circuit Breaker（Outlier Detection）
* TLS 設定

### 3. Gateway

Gateway は、Mesh に流入する外部トラフィックを管理します。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pod
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "bookinfo.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-credential  # TLS certificate
    hosts:
    - "bookinfo.example.com"
```

**主な機能**:

* 外部トラフィックのエントリポイントを定義
* Host、Port、Protocol の設定
* TLS 終端
* SNI ルーティング

### 4. ServiceEntry

ServiceEntry により、Mesh 外部の Service を内部 Service と同様に使用できます。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**主な機能**:

* 外部 Service の登録
* 外部 Service のトラフィック制御
* Egress トラフィック管理

### 5. PeerAuthentication

PeerAuthentication は、Service 間の認証ポリシーを定義します。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, DISABLE
```

### 6. AuthorizationPolicy

AuthorizationPolicy は、Service へのアクセス権限を定義します。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-ratings
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]
    to:
    - operation:
        methods: ["GET"]
```

## トラフィック管理の概念

### トラフィックルーティングフロー

```mermaid
flowchart LR
    Client[Client] -->|1. HTTP Request| Gateway[Gateway<br/>Ingress]
    Gateway -->|2. VirtualService<br/>Apply routing rules| VS[VirtualService]
    VS -->|3. Determine destination| DR[DestinationRule]
    DR -->|4. Select subset<br/>Apply traffic policy| Service[Kubernetes<br/>Service]
    Service -->|5. Endpoint<br/>routing| Pod1[Pod v1]
    Service -->|5. Endpoint<br/>routing| Pod2[Pod v2]

    %% Style definitions
    classDef gateway fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef istioResource fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef k8sResource fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Gateway gateway;
    class VS,DR istioResource;
    class Service,Pod1,Pod2 k8sResource;
    class Client default;
```

### トラフィック分割（Canary デプロイ）

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # 90% of traffic
    - destination:
        host: reviews
        subset: v2
      weight: 10  # 10% of traffic (canary)
```

### Circuit Breaker

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## セキュリティの概念

### mTLS（相互 TLS）

Istio は、Service 間通信を自動的に暗号化します。

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[App]
        Envoy1[Envoy]
    end

    subgraph Pod2["Pod B"]
        Envoy2[Envoy]
        App2[App]
    end

    App1 -->|Plaintext| Envoy1
    Envoy1 <-->|mTLS Encrypted| Envoy2
    Envoy2 -->|Plaintext| App2

    Citadel[istiod<br/>Citadel] -.->|Certificate issuance| Envoy1
    Citadel -.->|Certificate issuance| Envoy2

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Citadel controlPlane;
```

**mTLS モード**:

* **STRICT**: mTLS のみ許可
* **PERMISSIVE**: mTLS と平文の両方を許可（移行用）
* **DISABLE**: mTLS を無効化

### 認証と認可

```yaml
# JWT Authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
---
# Authorization Policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  action: DENY
  rules:
  - from:
    - source:
        notRequestPrincipals: ["*"]
```

## 可観測性の概念

Istio は、メトリクス、ログ、トレースを自動的に生成します。

### 自動生成されるメトリクス

```mermaid
flowchart TB
    subgraph Pod["Pod"]
        App[Application]
        Envoy[Envoy Proxy]
    end

    App <-->|Traffic| Envoy

    Envoy -->|Metrics| Prometheus[Prometheus<br/>Metric Collection]
    Envoy -->|Traces| Jaeger[Jaeger<br/>Distributed Tracing]
    Envoy -->|Logs| Logging[Logging System]

    Prometheus -->|Visualization| Grafana[Grafana<br/>Dashboard]
    Jaeger -->|Analysis| JaegerUI[Jaeger UI]

    Kiali[Kiali<br/>Service Mesh Dashboard] -->|Query| Prometheus

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef monitoring fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef visualization fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class Prometheus,Jaeger,Logging monitoring;
    class Grafana,JaegerUI,Kiali visualization;
```

### 主なメトリクス

| メトリクス                            | 説明                 |
| ------------------------------------- | -------------------- |
| `istio_requests_total`                | 総リクエスト数       |
| `istio_request_duration_milliseconds` | リクエストレイテンシー |
| `istio_request_bytes`                 | リクエストサイズ     |
| `istio_response_bytes`                | レスポンスサイズ     |
| `istio_tcp_connections_opened_total`  | TCP 接続数           |

### 分散トレーシング

```yaml
# Enable tracing in Envoy
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
        zipkin:
          address: jaeger-collector.istio-system:9411
```

## Namespace と Service Mesh

### Namespace の分離

```yaml
# Per-namespace mTLS policy
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
---
# Per-namespace authorization policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  action: DENY
  rules:
  - {}
```

### Service Mesh のスコープ

```bash
# Include only specific namespaces in the mesh
kubectl label namespace default istio-injection=enabled
kubectl label namespace staging istio-injection=enabled

# Exclude specific namespace
kubectl label namespace kube-system istio-injection=disabled
```

### マルチテナンシー

```yaml
# Restrict mesh scope with Sidecar resource
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: production
spec:
  egress:
  - hosts:
    - "production/*"  # Only production namespace accessible
    - "istio-system/*"
```

## VM Workload の登録

Istio では、Kubernetes Pod だけでなく **Virtual Machine（VM）Workload** も Service Mesh に登録できます。これにより、レガシーアプリケーションや Cluster 外部の Service でも、Istio のトラフィック管理、セキュリティ、可観測性機能を利用できます。

### VM Workload が必要な理由

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        VM3[VM<br/>External Service]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod1[Pod]
            App1[New App]
            Envoy1[Envoy]
        end

        subgraph Pod2[Pod]
            App2[Microservice]
            Envoy2[Envoy]
        end
    end

    subgraph Istiod[Control Plane]
        CP[istiod]
    end

    VM1 -->|Before migration<br/>Direct communication| App1
    App1 -.->|After mesh registration<br/>mTLS, policy applied| VM1

    CP -.->|Configuration delivery| Envoy1
    CP -.->|Configuration delivery| Envoy2
    CP -.->|VM can also be registered| VM1

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**ユースケース**:

* レガシーアプリケーションの段階的な移行
* Database Server を Mesh に含める
* Cluster 外部の Service の統合
* ハイブリッドクラウド環境の構成

### VM 登録アーキテクチャ

```mermaid
flowchart LR
    subgraph VM[Virtual Machine]
        LegacyApp[Legacy<br/>Application]
        EnvoyVM[Envoy<br/>Sidecar]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            App[Application]
            EnvoyPod[Envoy<br/>Sidecar]
        end

        Istiod[istiod<br/>Control Plane]
    end

    LegacyApp <-->|Local communication| EnvoyVM
    App <-->|Local communication| EnvoyPod

    EnvoyVM <-->|mTLS| EnvoyPod

    Istiod -.->|xDS configuration| EnvoyVM
    Istiod -.->|xDS configuration| EnvoyPod
    Istiod -.->|Certificate issuance| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class LegacyApp vmApp;
    class App k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### WorkloadEntry リソース

VM Workload は、**WorkloadEntry** リソースで登録します。

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-database
  namespace: default
spec:
  address: 192.168.1.100  # VM IP address
  labels:
    app: mysql
    version: v5.7
  serviceAccount: database-sa
  ports:
    mysql: 3306
```

**WorkloadEntry の主要フィールド**:

* `address`: VM IP アドレス
* `labels`: Service Selector と一致
* `serviceAccount`: mTLS 認証用の Service Account
* `ports`: 公開する Port の定義

### ServiceEntry との統合

WorkloadEntry は ServiceEntry とともに使用し、VM Service を Mesh に登録します。

```yaml
# Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-database
spec:
  hosts:
  - database.legacy.com
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_INTERNAL  # Register as internal mesh service
  resolution: STATIC
  workloadSelector:
    labels:
      app: mysql
---
# Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: mysql-vm-1
  namespace: default
spec:
  address: 192.168.1.100
  labels:
    app: mysql
    version: v5.7
  serviceAccount: mysql-sa
```

### VM 登録と Multi-Cluster の比較

| 機能                       | VM Workload 登録          | Multi-Cluster                  | Kubernetes Pod      |
| -------------------------- | ------------------------- | ------------------------------ | ------------------- |
| **Workload の場所**        | Cluster 外部の VM         | 別の Kubernetes Cluster        | Cluster 内部        |
| **Envoy のインストール**   | 手動インストール          | 自動（Sidecar）                | 自動（Sidecar）     |
| **登録方法**               | WorkloadEntry             | ServiceEntry + EndpointSlice   | Service + Pod       |
| **mTLS**                   | サポート済み              | サポート済み                   | サポート済み        |
| **Service Discovery**      | 手動（IP 指定）           | 自動                           | 自動                |
| **ユースケース**           | レガシーアプリ、DB        | Multi-cloud、災害復旧          | Cloud-native アプリ |
| **運用の複雑性**           | 高                        | 中                             | 低                  |

### VM 登録の利点

#### 1. 段階的な移行

```mermaid
flowchart LR
    subgraph Phase1[Phase 1: Legacy Environment]
        VM1[VM<br/>Monolith App]
    end

    subgraph Phase2[Phase 2: VM Mesh Registration]
        VM2[VM<br/>Monolith App<br/>+ Envoy]
    end

    subgraph Phase3[Phase 3: Hybrid]
        VM3[VM<br/>Legacy Module]
        K8S1[K8s<br/>New Microservices]
        VM3 <-->|mTLS| K8S1
    end

    subgraph Phase4[Phase 4: Complete Migration]
        K8S2[K8s<br/>All Microservices]
    end

    Phase1 -->|VM registration| Phase2
    Phase2 -->|Partial migration| Phase3
    Phase3 -->|Complete| Phase4

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8s fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class K8S1,K8S2 k8s;
```

**利点**:

* 既存の VM アプリケーションを変更せずに Mesh へ統合
* Kubernetes へ段階的に移行
* 移行中も一貫したセキュリティと可観測性を維持

#### 2. 統一されたセキュリティポリシー

```yaml
# mTLS policy applied to both VMs and pods
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # Enforce mTLS for both VMs and pods
---
# VM database access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-access
  namespace: default
spec:
  selector:
    matchLabels:
      app: mysql  # WorkloadEntry label
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/app-sa"]
    to:
    - operation:
        methods: ["*"]
```

#### 3. 一貫した可観測性

VM Workload は、Kubernetes Pod と同じメトリクス、ログ、分散トレーシングを提供します。

```promql
# Unified metric query for VMs and pods
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))

# Error rate from VM
sum(rate(istio_requests_total{destination_workload="mysql-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))
```

### VM 登録の制限事項

1. **Envoy の手動インストール**: VM に Envoy Proxy を手動でインストールして設定する必要がある
2. **ネットワーク接続性**: VM と Kubernetes Cluster 間のネットワーク接続が必要
3. **証明書管理**: Service Account 証明書を VM にデプロイする必要がある
4. **運用負荷**: VM 上の Envoy のバージョン管理と更新が必要
5. **Auto-scaling の制限**: Kubernetes HPA のような Auto-scaling はない

### 実践的な使用例

#### シナリオ: レガシー Database の統合

```yaml
# 1. Define database service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: production
spec:
  hosts:
  - postgres.production.svc.cluster.local
  addresses:
  - 240.240.1.10  # Virtual IP
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
---
# 2. Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: production
spec:
  address: 10.0.1.100  # Actual VM IP
  labels:
    app: postgres
    tier: database
    version: v13
  serviceAccount: postgres-sa
  ports:
    postgresql: 5432
---
# 3. Access control policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access-control
  namespace: production
spec:
  selector:
    matchLabels:
      app: postgres
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production"]
        principals: ["cluster.local/ns/production/sa/api-service"]
    to:
    - operation:
        ports: ["5432"]
```

**結果**:

* Kubernetes Pod は `postgres.production.svc.cluster.local` 経由で Database にアクセス
* VM と Pod 間の mTLS 暗号化を自動化
* アクセス制御ポリシーを適用
* メトリクスと分散トレーシングを自動収集

### Workload 登録の比較まとめ

```mermaid
flowchart TB
    subgraph Types[Workload Types]
        K8S[Kubernetes Pod<br/>Inside cluster]
        MC[Multi-Cluster<br/>Different cluster]
        VM[Virtual Machine<br/>Outside cluster]
    end

    subgraph Features[Common Features]
        mTLS[mTLS Encryption]
        Traffic[Traffic Management]
        Policy[Security Policy]
        Metrics[Metrics & Tracing]
    end

    K8S & MC & VM --> mTLS
    K8S & MC & VM --> Traffic
    K8S & MC & VM --> Policy
    K8S & MC & VM --> Metrics

    %% Style definitions
    classDef workload fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class K8S,MC,VM workload;
    class mTLS,Traffic,Policy,Metrics feature;
```

Istio の柔軟な Workload 登録機能により、次を実現できます。

* **Kubernetes Pod**: Cloud-native アプリケーション
* **Multi-Cluster**: Multi-cloud、リージョン分散、災害復旧
* **Virtual Machine**: レガシーアプリ、Database、ハイブリッド環境

すべての Workload は、一貫したセキュリティ、トラフィック管理、可観測性機能を利用できます。

## 次のステップ

これで Istio の基本概念を理解できました。次のドキュメントを通じて、実際の使用方法を学びましょう。

### コア機能

1. [**トラフィック管理**](traffic-management/)
   * Gateway と VirtualService の使用方法
   * DestinationRule と Subset の定義
   * ServiceEntry と WorkloadEntry（VM 登録）
   * 高度なルーティングパターン（Canary、A/B テスト）
   * Traffic Mirroring と Shadowing
2. [**セキュリティ**](security/)
   * mTLS 設定と PeerAuthentication
   * 認証（RequestAuthentication、JWT）
   * 認可（AuthorizationPolicy）
   * セキュリティポリシー管理
   * 外部認証の統合
3. [**可観測性**](/broken/pages/HT0uW6gT7EfVN0LF8wU5)
   * メトリクス収集（Prometheus）
   * 分散トレーシング（Jaeger、Zipkin）
   * ログ設定
   * Kiali Service Mesh の可視化
   * Grafana Dashboard
4. [**レジリエンス**](resilience/)
   * Circuit Breaker パターン
   * Retry と Timeout の設定
   * Rate Limiting
   * Outlier Detection
   * Fault Injection テスト

### 高度なトピック

5. [**高度なトピック**](advanced/)
   * Ambient Mode（Sidecar なしの Mesh）
   * Multi-Cluster の設定
   * EnvoyFilter のカスタマイズ
   * DNS Proxy と Caching
   * VM Workload の詳細設定
   * WASM Plugin の開発

## 参考資料

* [Istio 公式ドキュメント - 概念](https://istio.io/latest/docs/concepts/)
* [Istio 公式ドキュメント - トラフィック管理](https://istio.io/latest/docs/concepts/traffic-management/)
* [Istio 公式ドキュメント - セキュリティ](https://istio.io/latest/docs/concepts/security/)
* [Istio 公式ドキュメント - 可観測性](https://istio.io/latest/docs/concepts/observability/)
* [Envoy Proxy 公式ドキュメント](https://www.envoyproxy.io/docs/envoy/latest/)
