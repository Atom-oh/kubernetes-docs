# トラフィック管理

Istio のトラフィック管理機能を使うと、サービスメッシュ内を流れるトラフィックを細かく制御できます。

## 目次

1. [Gateway と VirtualService](01-gateway-virtualservice.md)
2. [ルーティング](02-routing.md)
3. [DestinationRule](03-destination-rule.md) ⭐ 重要な概念
4. [トラフィック分割](04-traffic-splitting.md)
5. [リトライとタイムアウト](05-retry-timeout.md)
6. [ロードバランシング](06-load-balancing.md)
7. [サーキットブレーカー](07-circuit-breaker.md)
8. [フォールトインジェクション](08-fault-injection.md)
9. [トラフィックミラーリング](09-traffic-mirror.md)
10. [セッションアフィニティ](10-session-affinity.md)
11. [Egress 制御](11-egress-control.md)
12. [ServiceEntry（外部サービスの管理）](12-service-entry.md)
13. [WorkloadEntry（VM の登録）](13-workload-entry.md)

## 概要

以下は、サポート対象の Istio リリースで使う sidecar モードの設定例です。Gateway、VirtualService、DestinationRule は proxy が読み取る API オブジェクトであり、それぞれが独立したネットワークホップになるわけではありません。mirror は選択したリクエストの追加コピーであり、90/10 の分割で残る 10% を意味するものではありません。mirror された応答は破棄されます。図は論理的な設定関係を示しています。

各 snippet は個別に使う例であり、すべてを 1 つの manifest として適用するものではありません。先に参照先の Service と DestinationRule の subset を作成してください。VirtualService に `gateways` リストがない場合は mesh 全体に適用されます。Ingress route には明示的な Gateway の関連付けと一致する hostname が必要です。ambient モードでは、サポート対象の Gateway API／waypoint routing を使用してください。

トラフィック管理は Istio の中核機能の 1 つで、コードを変更せずに次のような操作を行えます。

### 主な機能

![クライアントのリクエストが Gateway に入り、VirtualService でルーティングされ、DestinationRule のトラフィックポリシーが適用された後、メインの service、canary、shadow test 用の mirror copy という 3 つの service version に振り分けられます。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-readme-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-readme-0.html)

### 1. インテリジェントなルーティング

- **path ベース**: `/api/v1` → Service A、`/api/v2` → Service B
- **header ベース**: `User-Agent: Mobile` → モバイル版
- **cookie ベース**: 特定のユーザーを特定の version にルーティング
- **weight ベース**: 比率に応じてトラフィックを分散

### 2. デプロイ戦略

**Canary deployment**:
```yaml
# Only 10% to new version
route:
- destination:
    host: reviews
    subset: v1
  weight: 90
- destination:
    host: reviews
    subset: v2
  weight: 10
```

**Blue/Green deployment**:
```yaml
# Instant switch
route:
- destination:
    host: reviews
    subset: v2  # Switch to Green
  weight: 100
```

### 3. レジリエンスパターン

- **サーキットブレーカー**: 障害中の service を隔離
- **リトライ**: 自動的に再試行
- **タイムアウト**: 応答時間に上限を設定
- **レート制限**: リクエスト頻度を制御

### 4. テストとデバッグ

- **トラフィックミラーリング**: テスト用に本番トラフィックを複製
- **フォールトインジェクション**: 意図的に障害を発生させる
- **A/B テスト**: 異なるユーザー群に異なる version を提供

## 主なリソース

### Gateway

メッシュに入る外部トラフィックの入口を定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
```

### VirtualService

リクエストのルーティング方法を定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - uri:
        prefix: "/v2"
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

### DestinationRule

宛先 service に適用するポリシーを定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## 実践例

### 安全な Canary deployment

```yaml
# Step 1: Start with 5% traffic
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
      weight: 95
    - destination:
        host: reviews
        subset: v2
      weight: 5
```

監視して問題がなければ、次のように段階的に比率を上げます。
- 5% → 10% → 25% → 50% → 100%

### header ベースのルーティング（開発者テスト）

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-dev
spec:
  hosts:
  - reviews
  http:
  # Developers use new version
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v2
  # Regular users use stable version
  - route:
    - destination:
        host: reviews
        subset: v1
```

開発者用 header はクライアントが付与するルーティングのヒントであり、認証や認可境界ではありません。

### サーキットブレーカー + リトライ

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-resilient
spec:
  host: reviews
  trafficPolicy:
    # Connection Pool settings
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    # Circuit Breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-retry
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
    timeout: 10s
```

## トラフィックの流れ

![ユーザーのリクエストは ingress Gateway に入り、VirtualService で path、header、weight の順に照合されます。次に DestinationRule のロードバランシング、サーキットブレーカー、接続プールのポリシーが適用され、最終的に 3 つの backing Pod のいずれかに届きます。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-readme-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-readme-1.html)

## 学習の進め方

トラフィック管理を効果的に学ぶには、次の順序がおすすめです。

1. **[Gateway と VirtualService](01-gateway-virtualservice.md)** ⭐ 最初に学ぶ項目
   - 基本概念
   - 外部トラフィックの処理

2. **[ルーティング](02-routing.md)**
   - 応用的なルーティングパターン
   - 条件付きルーティング

3. **[DestinationRule](03-destination-rule.md)** ⭐ 重要な概念
   - subset の概念
   - Traffic Policy の基本
   - VirtualService との連携

4. **[トラフィック分割](04-traffic-splitting.md)**
   - Canary deployment
   - A/B テスト

5. **[リトライとタイムアウト](05-retry-timeout.md)**
   - 障害からの復旧
   - 応答時間の制御

6. **[ロードバランシング](06-load-balancing.md)**
   - 各種アルゴリズム
   - 性能の最適化

7. **[サーキットブレーカー](07-circuit-breaker.md)**
   - 障害の隔離
   - 障害の連鎖を防止

8. **[フォールトインジェクション](08-fault-injection.md)**
   - 障害テスト
   - Chaos Engineering

9. **[トラフィックミラーリング](09-traffic-mirror.md)**
   - 本番環境でのテスト
   - 新 version の検証

10. **[セッションアフィニティ](10-session-affinity.md)**
    - セッションの固定
    - state の維持

11. **[Egress 制御](11-egress-control.md)**
    - 外部 service へのアクセス
    - セキュリティの強化

12. **[ServiceEntry](12-service-entry.md)**
    - 外部 service の登録
    - Egress Gateway との連携

## ベストプラクティス

### 1. 段階的なロールアウト

```yaml
# ❌ Bad example: 100% at once
weight: 100

# ✅ Good example: Gradual increase
# 5% → Monitor → 10% → Monitor → ...
```

### 2. workload に合ったタイムアウトを設定する

```yaml
# ✅ Always set timeout
http:
- route:
  - destination:
      host: reviews
  timeout: 10s
```

streaming request には別のタイムアウト設定が必要な場合があります。短い HTTP deadline が、すべての gRPC stream や長時間の応答に適するとは限りません。

### 3. リトライを慎重に使う

```yaml
# ✅ Only when idempotency is guaranteed
retries:
  attempts: 3
  perTryTimeout: 2s
  retryOn: 5xx,reset,connect-failure
```

### 4. サーキットブレーカーのしきい値を調整する

```yaml
# ✅ Adjust according to service characteristics
outlierDetection:
  consecutive5xxErrors: 5      # Adjust per service
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50    # Maximum 50% ejection
```

### 5. メトリクスを監視する

トラフィック管理を変更するときは、必ず次の項目を監視します。
- **リクエスト数**: リクエスト数の変化
- **エラー率**: エラーの割合
- **レイテンシー**: P50、P95、P99 のレイテンシー
- **成功率**: 成功した割合

## トラブルシューティング

### トラフィックがルーティングされない

```bash
# 1. Check VirtualService
kubectl get virtualservice -n <namespace>
kubectl describe virtualservice <name> -n <namespace>

# 2. Check DestinationRule
kubectl get destinationrule -n <namespace>

# 3. Check pod labels
kubectl get pods --show-labels -n <namespace>

# 4. Analyze Istio configuration
istioctl analyze -n <namespace>
```

### weight が適用されない

```bash
# Check Envoy configuration
istioctl proxy-config routes <pod-name> -n <namespace>

# Check cluster information
istioctl proxy-config clusters <pod-name> -n <namespace>
```

## 次のステップ

1. **[セキュリティ](../security/README.md)**: mTLS と認証／認可
2. **[可観測性](../observability/README.md)**: メトリクス、ログ、トレース
3. **[レジリエンス](../resilience/README.md)**: Rate Limiting、Zone Aware Routing

## 参考資料

- [Istio のトラフィック管理](https://istio.io/latest/docs/concepts/traffic-management/)
- [VirtualService リファレンス](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [DestinationRule リファレンス](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Gateway リファレンス](https://istio.io/latest/docs/reference/config/networking/gateway/)

## クイズ

この章の理解度を確かめるには、[Istio トラフィック管理クイズ](../../../quizzes/service-mesh/istio/traffic-management.md)に挑戦してください。
