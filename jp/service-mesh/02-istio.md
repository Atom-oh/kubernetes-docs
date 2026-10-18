# Istio

> **最終更新**: 2026年10月12日 · Istio 1.31 に関するガイダンス

この概要ページは、以前の章の URL からも引き続きアクセスできるようにしています。詳細な手順と互換性マトリクスは、保守されている [Istio documentation index](istio/README.md) と [installation guide](istio/01-installation.md) で管理しています。現在の構築手順については、そちらを参照してください。

## 目次

- [はじめに](#introduction)
- [主な機能](#key-features)
- [アーキテクチャの概要](#architecture-overview)
- [詳細ドキュメント](#detailed-documentation)
- [クイックスタート](#quick-start)
- [学習リソース](#learning-resources)

## はじめに {#introduction}

Istio は、マイクロサービスアプリケーション向けのオープンソースのサービスメッシュプラットフォームです。サービスメッシュは、サービス間通信を処理するインフラストラクチャ層であり、その通信をインフラストラクチャレベルで制御、観測できます。アプリケーションの trace-context 伝播、グレースフルシャットダウン、ビジネス上の冪等性には、引き続きアプリケーション側の対応が必要です。

### Service Mesh とは？

サービスメッシュは、次の中核的な機能を提供します。

1. **トラフィック管理**: サービス間のトラフィックフローを制御
2. **セキュリティ**: サービス間通信の暗号化と認証
3. **可観測性**: サービス間通信の可視化

### Istio の主な利点

- **プラットフォーム非依存**: さまざまな環境（Kubernetes、VM など）で動作
- **透過的な統合**: アプリケーションのビジネスロジックを変更せずに、多くのネットワーク制御を追加可能
- **Workload mTLS**: メッシュに参加した通信経路での管理されたアイデンティティとトランスポート保護。強制適用と例外を確認してください
- **高度なトラフィック管理**: ルーティング、負荷分散、障害注入など
- **詳細なメトリクス**: サービス間通信に関する詳細な指標
- **ポリシー適用**: アクセス制御と、明示的に構成されたローカル／グローバルのレート制限

## 主な機能 {#key-features}

### 1. Traffic Management

Istio は高度なトラフィック管理機能を提供します。

- **Gateways**: 外部トラフィックをルーティング。Istio Gateway リソースと Kubernetes Gateway API を区別します
- **VirtualService / HTTPRoute**: 選択した data plane および controller でサポートされる API を使用してルーティングを構成
- **DestinationRule**: 負荷分散と接続プールを構成
- **Traffic Splitting**: カナリアデプロイと A/B テストをサポート
- **Argo Rollouts Integration**: 個別に構成された分析および障害処理による progressive delivery

### 2. Security

主なセキュリティ機能は次のとおりです。

- **mTLS**: 参加済み workload のトランスポートに対するアイデンティティ認証と暗号化
- **Authorization Policy**: きめ細かなアクセス制御
- **Request Authentication**: JWT 検証。JWT が必須の場合は AuthorizationPolicy を使用
- **Peer Authentication**: inbound workload の mTLS ポリシー

### 3. Observability

選択したモードに応じてテレメトリとバックエンドを構成します。

- **Metrics**: Prometheus 統合
- **Distributed Tracing**: Jaeger を備えた OpenTelemetry など、構成済みのトレースプロバイダー／バックエンド。アプリケーションがコンテキストを伝播します
- **Logging**: アクセスログと構造化ログ
- **Visualization**: Kiali dashboard

### 4. Resilience

サービスの耐障害性を高めるパターン：

- **Circuit Breaker**: 接続数／リクエストプールの上限。過負荷を防ぐ保証ではありません
- **Retry**: 再試行しても安全な操作に対する明示的な予算。あいまいな書き込みリクエストの再試行は無効化
- **Timeout**: リクエストのタイムアウト設定
- **Outlier Detection**: 異常なインスタンスを除外
- **Rate Limiting**: 構成済みのローカル token bucket またはグローバルなレート制限サービス

## アーキテクチャの概要 {#architecture-overview}

Istio は **Control Plane** と **Data Plane** で構成されます。次の図は sidecar 形式を示しており、ambient トポロジーではありません。

![Control Plane 内の Istiod は、3 つの Data Plane Pod のアプリケーションコンテナとともに実行される Envoy sidecar proxy に構成をプッシュし、それらのプロキシは相互に直接 mTLS 接続を確立します。](../.gitbook/assets/en-service-mesh-02-istio-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-02-istio-0.html)

### Control Plane (istiod)

istiod は Istio の中央 Control コンポーネントで、次を提供します。

- **Service Discovery**: メッシュのサービスレジストリを維持
- **Configuration Management**: 構成を監視し、変換して proxy 設定を配布。Kubernetes は API リソースを永続化します
- **Certificate Management**: 構成済みの CA を使用して workload certificate のリクエストとローテーションを管理

### Data Plane: Sidecar と Ambient

sidecar モードでは、Envoy は参加済みの各アプリケーション Pod とともに実行されます。

- **Traffic Routing**: サービス間のトラフィックを制御
- **Load Balancing**: サービスインスタンス間でトラフィックを分散
- **Security**: mTLS の暗号化と認証
- **Observability**: メトリクス、ログ、トレースを収集

Ambient は、L4 トランスポートにノードレベルの ztunnel を使用し、サポートされる L7 機能には任意で Envoy waypoint を使用します。すべてのアプリケーション Pod に Envoy を inject するわけではありません。機能サポート、policy のアタッチ、リソース使用量はモードによって異なります。このトポロジーから、固定的なリソース削減率や普遍的なパフォーマンス優位性が導かれるわけではありません。[Ambient Mode](istio/advanced/01-ambient-mode.md) を参照してください。

## 詳細ドキュメント {#detailed-documentation}

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
| [Routing](istio/traffic-management/02-routing.md) | VirtualService のルーティング規則 |
| [DestinationRule](istio/traffic-management/03-destination-rule.md) | サービスのトラフィックポリシー |
| [Traffic Splitting](istio/traffic-management/04-traffic-splitting.md) | カナリアデプロイと A/B テスト |
| [Timeout and Retry](istio/traffic-management/05-retry-timeout.md) | タイムアウトとリトライのポリシー |
| [Load Balancing](istio/traffic-management/06-load-balancing.md) | さまざまな負荷分散方式 |
| [Circuit Breaker](istio/traffic-management/07-circuit-breaker.md) | サーキットブレーカーの実装 |
| [Fault Injection](istio/traffic-management/08-fault-injection.md) | カオスエンジニアリング |
| [Traffic Mirroring](istio/traffic-management/09-traffic-mirror.md) | トラフィックミラーリングとシャドーテスト |
| [Session Affinity](istio/traffic-management/10-session-affinity.md) | セッションアフィニティの構成 |

### 🔐 Security

| ドキュメント | 説明 |
|----------|-------------|
| [mTLS](istio/security/01-mtls.md) | サービス間 mTLS の構成 |
| [Authorization Policy](istio/security/03-authorization.md) | アクセス制御ポリシー |
| [Request Authentication](istio/security/02-authentication.md) | JWT ベースの認証 |
| [Peer Authentication](istio/security/01-mtls.md) | サービス間認証 |

### 📊 Observability

| ドキュメント | 説明 |
|----------|-------------|
| [Metrics](istio/observability/01-metrics.md) | Prometheus メトリクスの収集 |
| [Distributed Tracing](istio/observability/02-tracing.md) | Jaeger／Zipkin との統合 |
| [Logging](istio/observability/03-logging.md) | アクセスログと構造化ログ |
| [Visualization](istio/observability/04-dashboards.md) | Kiali、Grafana のダッシュボード |

### 💪 Resilience

| ドキュメント | 説明 |
|----------|-------------|
| [Outlier Detection](istio/resilience/01-outlier-detection.md) | 異常なインスタンスの検出 |
| [Rate Limiting](istio/resilience/02-rate-limiting.md) | ローカル／グローバルのレート制限 |
| [Zone Aware Routing](istio/resilience/03-zone-aware-routing.md) | ローカリティを考慮したルーティング |

### 🚀 高度なトピック

| ドキュメント | 説明 |
|----------|-------------|
| [Ambient Mode](istio/advanced/01-ambient-mode.md) | サイドカーを使わないサービスメッシュ |
| [Multi-cluster](istio/advanced/02-multi-cluster.md) | マルチクラスタメッシュの構成 |
| [EnvoyFilter](istio/advanced/03-envoy-filter.md) | Envoy のカスタマイズ |
| [DNS Capture and Caching](istio/advanced/04-dns-cache.md) | DNS キャプチャ、名前解決、測定済みのキャッシュ動作 |
| [gRPC](istio/advanced/05-grpc.md) | gRPC プロトコルのサポート |
| [WebSocket](istio/advanced/06-websocket.md) | WebSocket 接続のサポート |
| [Sidecar Injection](istio/advanced/07-sidecar-injection.md) | サイドカー注入の仕組み |
| [Argo Rollouts](istio/advanced/08-argo-rollouts.md) | プログレッシブデリバリーとの統合 |

### ✅ ベストプラクティス

| ドキュメント | 説明 |
|----------|-------------|
| [Best Practices](istio/best-practices.md) | 本番運用のチェックリストと推奨事項 |

## クイックスタート {#quick-start}

1. [installation guide](istio/01-installation.md) で、Istio、Kubernetes、EKS で共通してサポートされるバージョンの組み合わせを確認してください。「Kubernetes 1.28 以降」のような一般的な前提条件だけでは、現在の Istio リリースには不十分です。
2. sidecar または ambient を選び、ガイドで指定されたバージョン固定の CLI／chart、分離された namespace、プラットフォームの前提条件に従ってください。バージョンが指定されていない最新の CLI をダウンロードしてから、古いバージョンのディレクトリに移動することは避けてください。
3. 保守されているガイドにある、対応バージョンの Bookinfo 手順と Gateway 手順を使用してください。デフォルト profile では ingress gateway の Deployment は自動作成されません。また、Gateway 設定オブジェクトだけで、各インストールに必要な gateway／LoadBalancer がすべて作成されるわけでもありません。
4. 実際の gateway アドレス、Service の port、route の状態、HTTP response を確認してください。load balancer が公開するのは IP の場合も hostname の場合もあります。AWS 固有の hostname フィールドや特定の port 名を前提にしないでください。
5. dashboard のコマンドを使う前に、選択した [observability backends](istio/observability/README.md) をインストール／構成してください。Prometheus、Grafana、Kiali、トレース保存先は、Istio のデフォルト profile では自動インストールされません。

その手順を完了した後の基本的な検証：

```bash
istioctl version
istioctl analyze -A
istioctl proxy-status
```

Proxy の状態は診断材料の一つにすぎません。ambient への参加状況と ztunnel はそれぞれ別途確認が必要です。また、analyzer の結果に問題がなくても、エンドツーエンドの通信テストを代替するものではありません。

## 学習リソース {#learning-resources}

### 公式ドキュメント

- [Istio Official Documentation](https://istio.io/latest/docs/)
- [Istio GitHub Repository](https://github.com/istio/istio)
- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)

### AWS とコミュニティ

- [Istio on Amazon EKS](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/)
- [Maintained AWS integration guide](istio/04-aws-integration.md)
- [AWS App Mesh lifecycle notice](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html): AWS は 2026年9月30日にサポートを終了しました。移行要件を評価してください。この案内は新規デプロイを推奨するものではありません。
- [Istio community, channels and working groups](https://istio.io/latest/get-involved/)

### 追加リソース

- [Service Mesh Patterns (O'Reilly)](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
- [Istio in Action (Manning)](https://www.manning.com/books/istio-in-action)
- [Istio Performance Optimization Guide](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)

## クイズ

[Istio Quiz](../quizzes/service-mesh/02-istio-quiz.md) に挑戦して、Istio の理解度を確認してください。

このクイズでは、次のトピックを扱います。

- サービスメッシュの基本概念
- Istio アーキテクチャ
- トラフィック管理（カナリアデプロイ）
- セキュリティ（mTLS）
- Gateway と Ingress
- Observability ツール
- sidecar および ambient モード
- レート制限
- ローカリティを考慮したルーティング
- Amazon EKS 統合

---

**次のステップ**: [Installation Guide](istio/01-installation.md) に従って Istio をインストールし、[Core Concepts](istio/02-basic-concepts.md) で基本概念を学んでください。
