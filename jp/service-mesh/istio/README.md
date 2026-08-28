# Istio

> **最終更新**: August 24, 2026

Amazon EKS で Istio Service Mesh を活用するための実践ガイドです。

### 2026年8月アップデート: Istio 1.31 が RC に移行

2026年8月19日、1.31.0-beta.2 に続いて同日中に最初のリリース候補版である [1.31.0-rc.0](https://github.com/istio/istio/releases) がリリースされ、次のマイナーバージョン 1.31 はリリース候補段階に移行しました。RC は GA 直前の最終検証のためのプレリリースであり、公式リリースが近いことを示すシグナルです。本番環境では引き続き GA リリースを使用してください。

### 2026年8月アップデート: Istio 1.31 が Beta に移行

次のマイナーバージョンである Istio 1.31 のリリースプロセスが進行中です。2026年8月11日に 1.31.0-alpha.2 が公開され、8月13日に 1.31.0-beta.0、8月14日に 1.31.0-beta.1 が続きました。Alpha/Beta ビルドは早期検証のためのプレリリースであり、本番利用向けではありません。GA リリース前に新機能をテストしたい場合にのみ使用してください。詳細は [Istio releases page](https://github.com/istio/istio/releases) を参照してください。

### 2026年7月アップデート: Istio 1.30.3 / 1.29.6 パッチリリース

2026年7月16日、Istio 1.30.3 および 1.29.6 のパッチリリースが公開されました。1.30.3 の主な変更点は次のとおりです。

- workload/service のアドレス変更による XDS push の対象を影響を受ける waypoint のみに絞ることで、ambient mode における istiod のスケーラビリティを改善
- 再起動されるまで istiod が更新済みのリモートクラスター Secret（例: credential/token rotation 中）を取得しない問題を修正
- pilot node untaint controller の taint 名を、`PILOT_NODE_UNTAINT_CONTROLLERS_TAINT_NAME` 環境変数でカスタマイズ可能に変更

詳細は [official announcement](https://istio.io/latest/news/releases/1.30.x/announcing-1.30.3/) を参照してください。

## 目次

1. [Service Mesh は本当に必要か？](#do-you-really-need-a-service-mesh)
2. [インストールと初期セットアップ](01-installation.md)
3. [基本概念](02-basic-concepts.md)
4. [アーキテクチャ](03-architecture.md)
5. [AWS 統合](04-aws-integration.md)
6. [用語集](glossary.md)
7. [Traffic Management](traffic-management/README.md)
8. [セキュリティ](security/README.md)
9. [Observability](observability/README.md)
10. [Resilience](resilience/README.md)
11. [高度な機能](advanced/README.md)
12. [トラブルシューティング](troubleshooting/common-errors.md)
13. [ベストプラクティス](best-practices.md)
14. [代替手段の比較](comparison/README.md)

## Istio とは？

Istio は、マイクロサービスを接続、保護、制御、監視するためのオープンソース Service Mesh プラットフォームです。複雑なマイクロサービスアーキテクチャにおけるサービス間通信を管理し、トラフィック制御、セキュリティ、可観測性を提供します。

### Service Mesh の概念

<div align="center"><img src="https://istio.io/latest/img/service-mesh.svg" alt="Istio Service Mesh" width="800"></div>

Service Mesh は、マイクロサービス間の通信を管理するインフラストラクチャレイヤーです。Istio は各サービスに Sidecar Proxy（Envoy）を併置して、すべてのネットワークトラフィックをインターセプトおよび制御します。これにより、アプリケーションコードを変更せずに次の機能を提供します。

* **Traffic Routing**: インテリジェントルーティング、ロードバランシング、Canary デプロイメント
* **セキュリティ**: 自動 mTLS、認証、認可
* **Observability**: メトリクス、ログ、分散トレーシング
* **Resilience**: Circuit Breaking、Retry、Timeout

### 実践的な使用例

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/noistio.svg" alt="Application without Istio"><br><em>Application without Istio</em></p>

<p align="center"><img src="https://istio.io/latest/docs/examples/bookinfo/withistio.svg" alt="Application with Istio"><br><em>Application with Istio - Envoy Proxy deployed as Sidecar to each service</em></p>

Istio を適用すると、Envoy Proxy が Sidecar コンテナとして各マイクロサービスに自動的にデプロイされ、すべてのネットワークトラフィックを透過的にインターセプトおよび制御します。

## Service Mesh は本当に必要か？

Service Mesh は強力なツールですが、すべての状況に適しているわけではありません。導入前に慎重な検討が必要です。

### 判断フロー

```mermaid
flowchart TD
    Start[Consider Service Mesh<br/>Adoption]

    Q1{Microservices<br/>Architecture?}
    Q2{More than<br/>10 services?}
    Q3{Complex traffic<br/>management needed?}
    Q4{Zero Trust<br/>security needed?}
    Q5{Distributed tracing/<br/>observability needed?}
    Q6{Operations resources<br/>available?}

    NoNeed[Service Mesh<br/>Not Needed]
    Consider[Consider<br/>Adoption]
    NeedMesh[Service Mesh<br/>Recommended]

    Alternatives[Consider Alternatives<br/>- Kubernetes NetworkPolicy<br/>- Ingress Controller<br/>- CNI plugins<br/>- Application-level implementation]

    Start --> Q1
    Q1 -->|No| NoNeed
    Q1 -->|Yes| Q2
    Q2 -->|No| Alternatives
    Q2 -->|Yes| Q3
    Q3 -->|No| Q4
    Q3 -->|Yes| Q6
    Q4 -->|No| Q5
    Q4 -->|Yes| Q6
    Q5 -->|No| Consider
    Q5 -->|Yes| Q6
    Q6 -->|No| Consider
    Q6 -->|Yes| NeedMesh

    %% Style definitions
    classDef question fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef no fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef maybe fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef yes fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef alternative fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Q1,Q2,Q3,Q4,Q5,Q6 question;
    class NoNeed no;
    class Consider maybe;
    class NeedMesh yes;
    class Alternatives alternative;
```

### Service Mesh が必要な場合 ✅

#### 1. 複雑なマイクロサービス環境

```mermaid
flowchart LR
    subgraph WithoutMesh["Without Service Mesh"]
        A1[Service A] -.->|Manual implementation| B1[Service B]
        A1 -.->|Manual implementation| C1[Service C]
        B1 -.->|Manual implementation| D1[Service D]
        C1 -.->|Manual implementation| D1

        Note1[For each service<br/>- Manual mTLS implementation<br/>- Retry logic<br/>- Logging/metrics<br/>- Circuit Breaker<br/>Increased duplicate code]
    end

    subgraph WithMesh["With Service Mesh"]
        A2[Service A] -->|Automatic handling| B2[Service B]
        A2 -->|Automatic handling| C2[Service C]
        B2 -->|Automatic handling| D2[Service D]
        C2 -->|Automatic handling| D2

        SM[Service Mesh<br/>- Automatic mTLS<br/>- Centralized policies<br/>- Unified observability<br/>- Standardized security]

        SM -.->|Control| A2
        SM -.->|Control| B2
        SM -.->|Control| C2
        SM -.->|Control| D2
    end

    %% Style definitions
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class A1,B1,C1,D1,A2,B2,C2,D2 service;
    class SM mesh;
    class Note1 note;
```

**推奨基準**:

* ✅ マイクロサービスが 10 個以上
* ✅ サービス間通信（East-West トラフィック）が頻繁
* ✅ 複数のプログラミング言語を使用（Polyglot）
* ✅ 複数のチームがサービスを独立して開発

#### 2. Zero Trust セキュリティ要件

**Service Mesh が提供するもの**:

* サービス間の自動 mTLS 暗号化
* SPIFFE ベースの Identity 管理
* きめ細かな認証/認可ポリシー
* 暗号化通信の保証

**代替手段では実現が難しいこと**:

* 各サービスにおけるセキュリティロジック実装の重複
* 手動証明書管理の複雑さ
* 一貫性のないセキュリティポリシー

#### 3. 高度な Traffic Management

```yaml
# Canary Deployment (Traffic Distribution)
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
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10  # Only 10% to new version
```

**必要となる場合**:

* Canary デプロイメント、A/B テスト
* Header/path ベースのルーティング
* Traffic Mirroring（Shadow Testing）
* Fault Injection（Chaos Engineering）
* Circuit Breaking、Retry、Timeout

#### 4. 統合された Observability

**Service Mesh の利点**:

* アプリケーションコードを変更せずにメトリクスを自動収集
* 分散トレーシングを自動実装
* 統一されたログ形式
* サービストポロジーの可視化（Kiali）

### Service Mesh が不要な場合 ❌

#### 1. シンプルなアーキテクチャ

```mermaid
flowchart LR
    User[User] --> LB[Load Balancer]
    LB --> App[Monolithic<br/>Application]
    App --> DB[(Database)]

    Note["Service Mesh Not Needed<br/>- Single application<br/>- Simple communication patterns<br/>- Ingress is sufficient"]

    %% Style definitions
    classDef simple fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef note fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class User,LB,App,DB simple;
    class Note note;
```

**代わりに使用するもの**:

* Kubernetes Ingress Controller（NGINX、Traefik）
* シンプルなロードバランサー
* アプリケーションレベルの実装

#### 2. 少数のマイクロサービス（<10）

**オーバーヘッドのほうが大きい**:

* Service Mesh の運用複雑性 > 得られる利点
* 5～10 個のサービスは手動で管理可能
* NetworkPolicy で十分なセキュリティを提供

**代替手段**:

```yaml
# Kubernetes NetworkPolicy is sufficient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

#### 3. 運用リソースの不足

**Service Mesh の運用要件**:

* Istio/Envoy の専門知識
* Control Plane の監視と管理
* Upgrade とパッチ管理
* トラブルシューティング能力（デバッグの複雑性増加）

**必要なチーム準備**:

* Service Mesh の専門家が少なくとも 1～2 名
* 継続的な学習とアップデートの追跡
* 十分なテスト環境

#### 4. パフォーマンスが極めて重要な場合

**Service Mesh のオーバーヘッド**:

* レイテンシー: +1～3ms（P50）、+5～10ms（P99）
* CPU: Pod あたり +10～20%
* メモリ: Pod あたり +50～100MB（Sidecar mode）

**検討すべき代替手段**:

* Ambient Mode（リソース使用量を 90% 削減）
* CNI ベースのソリューション（Cilium）
* アプリケーションレベルの最適化

### 代替ソリューションの比較

| 機能                    | Service Mesh                                 | CNI (Cilium)    | Ingress Controller | アプリレベル                |
| -------------------------- | -------------------------------------------- | --------------- | ------------------ | ------------------------ |
| **L7 Traffic Management**  | ✅ 完全対応                               | ⚠️ 限定的      | ⚠️ Ingress のみ    | ✅ 可能               |
| **mTLS 自動化**        | ✅ 完全対応                               | ✅ 可能      | ❌ 非対応    | ❌ 手動実装  |
| **分散トレーシング**    | ✅ 自動                                  | ❌ 非対応 | ❌ 非対応    | ⚠️ 手動実装 |
| **L3/L4 ポリシー**         | ✅ 対応                                  | ✅ 完全対応  | ❌ 非対応    | ❌ 非対応          |
| **運用の複雑性** | 🔴 高                                      | 🟡 中       | 🟢 低             | 🟡 中                |
| **リソースオーバーヘッド**      | <p>🔴 高（Sidecar）<br>🟢 低（Ambient）</p> | 🟢 低          | 🟢 低             | 🟢 なし                  |
| **適切な規模**         | 10+ サービス                                 | すべての規模      | 小規模        | 小規模              |

### CNI ベースのソリューション（Cilium）

Cilium は、eBPF に基づき **ネットワークレベル** で多くの機能を提供します。

```mermaid
flowchart TB
    subgraph Comparison["Feature Comparison"]
        subgraph ServiceMesh["Service Mesh (Istio)"]
            SM1[L7 Proxy-based<br/>Envoy Sidecar]
            SM2[Application-level<br/>Traffic Control]
            SM3[Rich L7 Features<br/>Retry, Timeout, etc.]
        end

        subgraph CNI["CNI (Cilium)"]
            CN1[eBPF-based<br/>Kernel Level]
            CN2[Network-level<br/>Policy Enforcement]
            CN3[High Performance<br/>Low Overhead]
        end

        subgraph UseCases["Usage Scenarios"]
            UC1[Service Mesh:<br/>Complex L7 Logic]
            UC2[Cilium:<br/>Network Policy, Performance]
            UC3[Both:<br/>Large-scale Enterprise]
        end
    end

    %% Style definitions
    classDef mesh fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef cni fill:#F8B52A,stroke:#333,stroke-width:2px,color:black;
    classDef usecase fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class SM1,SM2,SM3 mesh;
    class CN1,CN2,CN3 cni;
    class UC1,UC2,UC3 usecase;
```

**Cilium がより適している場合**:

* L3/L4 ネットワークポリシーが主な目的
* 高パフォーマンスが中核要件
* Service Mesh の運用負荷を回避したい
* シンプルな mTLS と Observability のみが必要

**参考**: [Cilium Documentation](../../networking/cilium/README.md)

### 判断チェックリスト

導入前に次の質問に答えてください。

**アーキテクチャ**:

* [ ] マイクロサービスが 10 個以上ありますか？
* [ ] サービス間通信は複雑ですか？
* [ ] 複数のプログラミング言語を使用していますか？

**セキュリティ**:

* [ ] Zero Trust セキュリティモデルが必要ですか？
* [ ] サービス間の mTLS 暗号化は必須ですか？
* [ ] きめ細かなアクセス制御が必要ですか？

**Traffic Management**:

* [ ] Canary デプロイメント、A/B テストが必要ですか？
* [ ] 高度なルーティングルールが必要ですか？
* [ ] 多くのサービスで Circuit Breaking、Retry が必要ですか？

**Observability**:

* [ ] 分散トレーシングは必須ですか？
* [ ] 統一されたメトリクス収集が必要ですか？
* [ ] サービストポロジーの可視化が必要ですか？

**運用**:

* [ ] Service Mesh の専門家がいますか？
* [ ] 運用の複雑性に対応できますか？
* [ ] リソースオーバーヘッドを受け入れられますか？

**結果**:

* ✅ 10 個以上にチェック: Service Mesh を強く推奨
* 🟡 5～9 個にチェック: 慎重な評価が必要。小さく始める（Ambient Mode を推奨）
* ❌ 4 個以下にチェック: 代替ソリューション（CNI、Ingress、アプリレベル）を検討

### 段階的な導入戦略

Service Mesh が必要と判断した場合は、段階的に導入してください。

```mermaid
flowchart LR
    Phase1[Phase 1<br/>Observability<br/>Metric collection only]
    Phase2[Phase 2<br/>Security<br/>Apply mTLS]
    Phase3[Phase 3<br/>Traffic Management<br/>Canary Deployment]
    Phase4[Phase 4<br/>Advanced Features<br/>Utilize all features]

    Phase1 -->|After validation| Phase2
    Phase2 -->|After validation| Phase3
    Phase3 -->|After validation| Phase4

    %% Style definitions
    classDef phase fill:#326CE5,stroke:#333,stroke-width:2px,color:white;

    %% Apply classes
    class Phase1,Phase2,Phase3,Phase4 phase;
```

**推奨順序**:

1. **パイロットプロジェクト**（1～2 namespaces）
2. **Observability を優先**（メトリクス、ログ、トレース）
3. **セキュリティを適用**（mTLS PERMISSIVE → STRICT）
4. **Traffic Management**（VirtualService、DestinationRule）
5. **全社展開**

### 主な機能

1.  **Traffic Management**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/traffic-management/request-routing.svg" alt="Traffic Routing" width="500"></div>

    * インテリジェントルーティングとロードバランシング
    * A/B テスト、Canary デプロイメント、Blue/Green デプロイメント
    * Circuit Breaking、Retry、Timeout の制御
    * Traffic Mirroring と Fault Injection
2.  **セキュリティ**

    <div align="center"><img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Security Architecture" width="600"></div>

    * サービス間の自動 mTLS 暗号化
    * 強力な認証と認可
    * きめ細かなアクセス制御ポリシー
    * ネットワーク分離とセキュリティポリシー
3.  **Observability**

    <div align="center"><img src="https://istio.io/latest/docs/tasks/observability/kiali/kiali-graph.png" alt="Kiali Service Graph" width="700"></div>

    * メトリクス、ログ、トレースの自動生成
    * Prometheus、Grafana、Jaeger、Kiali 統合
    * サービストポロジーの可視化
    * リアルタイムトラフィック監視
4. **Resilience**
   * Circuit Breaker パターン
   * Rate Limiting
   * Outlier Detection
   * Zone Aware Routing

### Istio アーキテクチャ

<div align="center"><img src="https://istio.io/latest/docs/ops/deployment/architecture/arch.svg" alt="Istio Architecture" width="700"></div>

Istio は Control Plane と Data Plane で構成されます。

```mermaid
flowchart TB
    subgraph ControlPlane["Control Plane (istiod)"]
        Pilot[Pilot<br/>Service Discovery & Traffic Management]
        Citadel[Citadel<br/>Certificate Management & Security]
        Galley[Galley<br/>Configuration Management]
    end

    subgraph DataPlane["Data Plane"]
        subgraph Pod1["Pod 1"]
            App1[Application]
            Envoy1[Envoy Proxy]
        end

        subgraph Pod2["Pod 2"]
            App2[Application]
            Envoy2[Envoy Proxy]
        end

        subgraph Pod3["Pod 3"]
            App3[Application]
            Envoy3[Envoy Proxy]
        end
    end

    Pilot -.->|Configuration delivery| Envoy1
    Pilot -.->|Configuration delivery| Envoy2
    Pilot -.->|Configuration delivery| Envoy3

    Citadel -.->|Certificate issuance| Envoy1
    Citadel -.->|Certificate issuance| Envoy2
    Citadel -.->|Certificate issuance| Envoy3

    Envoy1 <-->|mTLS| Envoy2
    Envoy2 <-->|mTLS| Envoy3
    Envoy1 <-->|mTLS| Envoy3

    App1 -->|Request| Envoy1
    App2 -->|Request| Envoy2
    App3 -->|Request| Envoy3

    %% Style definitions
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef dataPlane fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Pilot,Citadel,Galley controlPlane;
    class App1,App2,App3 app;
    class Envoy1,Envoy2,Envoy3 proxy;
```

**Control Plane（istiod）**:

* **Pilot**: Service Discovery、トラフィックルーティングルールの管理
* **Citadel**: 証明書の生成と管理、mTLS の有効化
* **Galley**: 設定の検証とデプロイ

**Data Plane**:

* **Envoy Proxy**: 各 Pod に Sidecar としてデプロイされ、すべてのネットワークトラフィックをインターセプトおよび制御

### Amazon EKS で Istio を使用する利点

1. **容易なマイクロサービス管理**
   * アプリケーションコードを変更しない Traffic Management
   * 宣言的な設定による一貫したポリシー適用
   * Kubernetes Native API を使用
2. **セキュリティの強化**
   * サービス間の自動暗号化
   * AWS IAM と統合された認証
   * きめ細かな権限制御
3. **Observability の向上**
   * Amazon CloudWatch との統合
   * AWS X-Ray による分散トレーシング
   * 詳細なメトリクスとログ
4. **AWS サービスとの統合**
   * Application Load Balancer（ALB）との統合
   * AWS Certificate Manager（ACM）との統合
   * Amazon EBS CSI Driver と互換

### はじめに

<div align="center"><img src="https://istio.io/latest/docs/tasks/traffic-management/ingress/ingress-gateway-example/gateway-api-topology.svg" alt="Gateway API Architecture" width="600"></div>

Istio を初めて使用する場合は、次の順序でドキュメントを読んでください。

1. [**インストールと初期セットアップ**](01-installation.md): EKS クラスターに Istio をインストール
2. [**基本概念**](02-basic-concepts.md): Istio のコアコンセプトを理解
3. [**Traffic Management**](traffic-management/README.md): Gateway、VirtualService、DestinationRule を学習
4. [**セキュリティ**](security/README.md): mTLS、認証、認可を設定
5. [**Observability**](observability/README.md): メトリクス、ログ、トレースを収集
6. [**ベストプラクティス**](best-practices.md): 本番環境向けの推奨事項

### ハンズオン例

各セクションには動作する YAML の例が含まれています。すべての例はクリックしてコピーできるように構成されています。

```yaml
# Example VirtualService
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
```

### 参考資料

* [Istio Official Documentation](https://istio.io/latest/docs/)
* [Istio GitHub](https://github.com/istio/istio)
* [AWS EKS Workshop - Istio](https://www.eksworkshop.com/intermediate/330_servicemesh_using_istio/)
* [Istio Community](https://discuss.istio.io/)

### クイズ

この章で学んだ内容を確認するために、次のクイズに挑戦してください。

* [Traffic Management クイズ](../../quizzes/service-mesh/istio/traffic-management.md)
* [セキュリティクイズ](../../quizzes/service-mesh/istio/security.md)
* [Observability クイズ](../../quizzes/service-mesh/istio/observability.md)
* [Resilience クイズ](../../quizzes/service-mesh/istio/resilience.md)
* [高度な機能クイズ](../../quizzes/service-mesh/istio/advanced.md)
