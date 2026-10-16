# Istio

> **最終更新**: October 12, 2026 · Istio 1.31 guidance

この概要では、以前の章の URL を引き続き使用できます。詳細な手順および互換性マトリクスは、保守されている [Istio documentation index](istio/README.md) と [installation guide](istio/01-installation.md) で管理されています。現在のセットアップについては、そちらを使用してください。

## 目次

- [はじめに](#introduction)
- [主な機能](#key-features)
- [アーキテクチャの概要](#architecture-overview)
- [詳細ドキュメント](#detailed-documentation)
- [クイックスタート](#quick-start)
- [学習リソース](#learning-resources)

## はじめに

Istio は、マイクロサービスアプリケーション向けのオープンソースの service mesh プラットフォームです。service mesh は、サービス間通信を処理するインフラストラクチャ層であり、サービス通信をインフラストラクチャレベルで制御および観測できます。アプリケーションの trace-context 伝播、グレースフルシャットダウン、ビジネス上の冪等性には、引き続きアプリケーション側の対応が必要です。

### Service Mesh とは？

service mesh は、次の中核的な機能を提供します。

1. **Traffic Management**: サービス間のトラフィックフローを制御
2. **Security**: サービス間通信の暗号化と認証
3. **Observability**: サービス間通信の可視化

### Istio の主な利点

- **Platform Independence**: さまざまな環境（Kubernetes、VM など）で動作
- **Transparent Integration**: アプリケーションのビジネスロジックを変更せずに、多くのネットワーク制御を追加可能
- **Workload mTLS**: mesh に参加したパスでの管理されたアイデンティティとトランスポート保護。強制適用と例外を確認してください
- **Advanced Traffic Management**: ルーティング、load balancing、fault injection など
- **Detailed Metrics**: サービス間通信に関する詳細なメトリクス
- **Policy Enforcement**: アクセス制御と、明示的に構成されたローカル／グローバルの rate limiting

## 主な機能

### 1. Traffic Management

Istio は強力な Traffic Management 機能を提供します。

- **Gateways**: 外部トラフィックをルーティング。Istio Gateway リソースと Kubernetes Gateway API を区別します
- **VirtualService / HTTPRoute**: 選択した data plane および controller でサポートされる API を使用してルーティングを構成
- **DestinationRule**: load balancing と connection pool を構成
- **Traffic Splitting**: Canary deployment と A/B testing をサポート
- **Argo Rollouts Integration**: 個別に構成された分析および障害処理による progressive delivery

### 2. Security

包括的な Security 機能：

- **mTLS**: 参加済み workload のトランスポートに対するアイデンティティ認証と暗号化
- **Authorization Policy**: きめ細かなアクセス制御
- **Request Authentication**: JWT 検証。JWT が必須の場合は AuthorizationPolicy を使用
- **Peer Authentication**: inbound workload の mTLS ポリシー

### 3. Observability

選択したモード用に構成された Telemetry および backend 統合：

- **Metrics**: Prometheus 統合
- **Distributed Tracing**: Jaeger を備えた OpenTelemetry など、構成済みの trace provider/backend。アプリケーションが context を伝播します
- **Logging**: access log と structured logging
- **Visualization**: Kiali dashboard

### 4. Resilience

サービスの Resilience パターン：

- **Circuit Breaker**: connection/request-pool の上限。overload を防ぐ保証ではありません
- **Retry**: retry-safe 操作に対する明示的な予算。あいまいな write retry は無効化
- **Timeout**: request timeout の構成
- **Outlier Detection**: 正常でない instance を除外
- **Rate Limiting**: 構成済みのローカル token bucket またはグローバル rate-limit service

## アーキテクチャの概要

Istio は **Control Plane** と **Data Plane** で構成されます。次の図は sidecar 形式を示しており、ambient トポロジーではありません。

![Control Plane 内の Istiod は、3 つの Data Plane Pod の application container とともに実行される Envoy sidecar proxy に構成をプッシュし、それらの proxy は相互に直接 mTLS 接続を確立します。](../.gitbook/assets/en-service-mesh-02-istio-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-02-istio-0.html)

### Control Plane (istiod)

istiod は Istio の中央 Control コンポーネントで、次を提供します。

- **Service Discovery**: mesh の service registry を維持
- **Configuration Management**: 構成を監視し、変換して proxy 設定を配布。Kubernetes は API リソースを永続化します
- **Certificate Management**: 構成済みの CA を使用して workload certificate のリクエストとローテーションを管理

### Data Plane: Sidecar と Ambient

sidecar モードでは、Envoy は参加済みの各 application Pod とともに実行されます。

- **Traffic Routing**: サービス間のトラフィックを制御
- **Load Balancing**: service instance 間でトラフィックを分散
- **Security**: mTLS の暗号化と認証
- **Observability**: metrics、logs、traces を収集

Ambient は、L4 トランスポートに node レベルの ztunnel を使用し、サポートされる L7 機能には任意で Envoy waypoint を使用します。すべての application Pod に Envoy を inject するわけではありません。機能サポート、policy のアタッチ、リソース使用量はモードによって異なります。このトポロジーから、固定的なリソース削減率や普遍的なパフォーマンス優位性が導かれるわけではありません。[Ambient Mode](istio/advanced/01-ambient-mode.md) を参照してください。

## 詳細ドキュメント

以下のリンクは、保守されているサブツリーを学ぶためのマップです。その index には、追加および新規トピックが含まれます。

### 📚 基本ドキュメント

| ドキュメント | 説明 |
|----------|-------------|
| [Installation Guide](istio/01-installation.md) | Istio のインストールと初期セットアップ |
| [Core Concepts](istio/02-basic-concepts.md) | Istio の基本概念と用語 |
| [Components](istio/03-architecture.md) | Istio のアーキテクチャとコンポーネント |

### 🚦 Traffic Management

| ドキュメント | 説明 |
|----------|-------------|
| [Gateway & VirtualService](istio/traffic-management/01-gateway-virtualservice.md) | Ingress/Egress Gateway の構成 |
| [Routing](istio/traffic-management/02-routing.md) | VirtualService の routing rules |
| [DestinationRule](istio/traffic-management/03-destination-rule.md) | service traffic policy |
| [Traffic Splitting](istio/traffic-management/04-traffic-splitting.md) | Canary deployment と A/B testing |
| [Timeout and Retry](istio/traffic-management/05-retry-timeout.md) | timeout と retry policy |
| [Load Balancing](istio/traffic-management/06-load-balancing.md) | さまざまな load balancing strategy |
| [Circuit Breaker](istio/traffic-management/07-circuit-breaker.md) | Circuit Breaker パターンの実装 |
| [Fault Injection](istio/traffic-management/08-fault-injection.md) | chaos engineering |
| [Traffic Mirroring](istio/traffic-management/09-traffic-mirror.md) | traffic mirroring と shadow testing |
| [Session Affinity](istio/traffic-management/10-session-affinity.md) | session affinity の構成 |

### 🔐 Security

| ドキュメント | 説明 |
|----------|-------------|
| [mTLS](istio/security/01-mtls.md) | サービス間 mTLS の構成 |
| [Authorization Policy](istio/security/03-authorization.md) | access control policy |
| [Request Authentication](istio/security/02-authentication.md) | JWT ベースの認証 |
| [Peer Authentication](istio/security/01-mtls.md) | サービス間認証 |

### 📊 Observability

| ドキュメント | 説明 |
|----------|-------------|
| [Metrics](istio/observability/01-metrics.md) | Prometheus metrics の収集 |
| [Distributed Tracing](istio/observability/02-tracing.md) | Jaeger/Zipkin 統合 |
| [Logging](istio/observability/03-logging.md) | access log と structured logging |
| [Visualization](istio/observability/04-dashboards.md) | Kiali、Grafana dashboard |

### 💪 Resilience

| ドキュメント | 説明 |
|----------|-------------|
| [Outlier Detection](istio/resilience/01-outlier-detection.md) | 正常でない instance の検出 |
| [Rate Limiting](istio/resilience/02-rate-limiting.md) | ローカルおよびグローバルの rate limiting |
| [Zone Aware Routing](istio/resilience/03-zone-aware-routing.md) | locality-aware routing |

### 🚀 高度なトピック

| ドキュメント | 説明 |
|----------|-------------|
| [Ambient Mode](istio/advanced/01-ambient-mode.md) | sidecar を使用しない service mesh |
| [Multi-cluster](istio/advanced/02-multi-cluster.md) | multi-cluster mesh の構成 |
| [EnvoyFilter](istio/advanced/03-envoy-filter.md) | Envoy のカスタマイズ |
| [DNS Capture and Caching](istio/advanced/04-dns-cache.md) | DNS capture、resolution、および測定済み cache の動作 |
| [gRPC](istio/advanced/05-grpc.md) | gRPC protocol のサポート |
| [WebSocket](istio/advanced/06-websocket.md) | WebSocket connection のサポート |
| [Sidecar Injection](istio/advanced/07-sidecar-injection.md) | sidecar injection mechanism |
| [Argo Rollouts](istio/advanced/08-argo-rollouts.md) | progressive delivery 統合 |

### ✅ ベストプラクティス

| ドキュメント | 説明 |
|----------|-------------|
| [Best Practices](istio/best-practices.md) | 本番運用のチェックリストと推奨事項 |

## クイックスタート

1. [installation guide](istio/01-installation.md) で、正確な Istio/Kubernetes/EKS の互換性の共通範囲を確認してください。一般的な「Kubernetes 1.28+」という前提条件だけでは、現在の Istio release に対して十分ではありません。
2. sidecar または ambient を選択し、その guide の固定された CLI/chart、分離された namespace、およびプラットフォームの前提条件に従ってください。指定されていない latest CLI をダウンロードしてから、古い version directory に移動しないでください。
3. 保守されている guide にある、対応 version の Bookinfo 手順および Gateway 手順を使用してください。default profile は ingress gateway Deployment を自動的に提供せず、Gateway configuration object だけで各インストールに必要な gateway/LoadBalancer がすべて作成されるわけではありません。
4. 実際の gateway address、Service port、route status、および HTTP response を確認してください。load balancer は IP または hostname を公開する場合があります。AWS 専用の hostname field や特定の port name を想定しないでください。
5. dashboard command を使用する前に、選択した [observability backends](istio/observability/README.md) をインストール／構成してください。Prometheus、Grafana、Kiali、および tracing storage は、デフォルトの Istio profile では自動的にインストールされません。

その手順を完了した後の基本的な検証：

```bash
istioctl version
istioctl analyze -A
istioctl proxy-status
```

Proxy status は診断入力の一つにすぎません。Ambient enrollment と ztunnel には独自の確認が必要であり、analyzer の結果が正常であっても end-to-end traffic test ではありません。

## 学習リソース

### 公式ドキュメント

- [Istio Official Documentation](https://istio.io/latest/docs/)
- [Istio GitHub Repository](https://github.com/istio/istio)
- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)

### AWS とコミュニティ

- [Istio on Amazon EKS](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Maintained AWS integration guide](istio/04-aws-integration.md)
- [AWS App Mesh lifecycle notice](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html): AWS は September 30, 2026 にサポートを終了しました。移行要件を評価してください。これは新規デプロイメントの推奨ではありません。
- [Istio community, channels and working groups](https://istio.io/latest/get-involved/)

### 追加リソース

- [Service Mesh Patterns (O'Reilly)](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
- [Istio in Action (Manning)](https://www.manning.com/books/istio-in-action)
- [Istio Performance Optimization Guide](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)

## クイズ

Istio の理解度を確認するには、[Istio Quiz](../quizzes/service-mesh/02-istio-quiz.md) に挑戦してください。

このクイズでは、次のトピックを扱います。

- service mesh の基本概念
- Istio アーキテクチャ
- Traffic Management（Canary deployment）
- Security（mTLS）
- Gateway と Ingress
- Observability ツール
- sidecar および ambient モード
- Rate Limiting
- locality routing
- Amazon EKS 統合

---

**次のステップ**: [Installation Guide](istio/01-installation.md) を参照して Istio をインストールし、[Core Concepts](istio/02-basic-concepts.md) で基本概念を学んでください。