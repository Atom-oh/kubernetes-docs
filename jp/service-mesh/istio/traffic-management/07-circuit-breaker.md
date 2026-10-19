# サーキットブレーカー

サーキットブレーカーは、障害が発生したサービスを自動的に切り離し、障害の連鎖を防ぎます。

## 目次

1. [サーキットブレーカーが必要な理由](#why-circuit-breaker)
2. [サーキットブレーカーの概要](#circuit-breaker-overview)
3. [接続プールの設定](#connection-pool-settings)
4. [異常なエンドポイントの検出](#outlier-detection)
5. [リトライポリシーとの組み合わせ](#combination-with-retry-policy)
6. [実践例](#practical-examples)
7. [外部サービス向けサーキットブレーカー](#external-service-circuit-breaker)
8. [モニタリングとデバッグ](#monitoring-and-debugging)
9. [重要な考慮事項](#important-considerations)
10. [ベストプラクティス](#best-practices)

## サーキットブレーカーが必要な理由 {#why-circuit-breaker}

### 障害の連鎖を防ぐ

マイクロサービスアーキテクチャでは、あるサービスの障害がほかのサービスへ波及するのを防ぎます。

![サーキットブレーカーがない場合、障害中のサービスBへのタイムアウトでサービスAのリソースが枯渇し、サービスCとDへ障害が連鎖する。一方、サーキットブレーカーがある場合、Bへの呼び出しは速やかに失敗し、CとDは正常なまま保たれる様子。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-0.html)

### 主な利点

| 課題 | サーキットブレーカーなし | サーキットブレーカーあり |
|---------|------------------------|----------------------|
| **応答時間** | タイムアウト（30秒以上）まで待つ | 設定した上限に達すると速やかに拒否する |
| **リソース使用量** | スレッドや接続が枯渇する | リソースを保護する |
| **障害の波及** | 障害が連鎖する | 障害を隔離する |
| **復旧時間** | 手動対応が必要 | 自動復旧を試みる |

## サーキットブレーカーの概要 {#circuit-breaker-overview}

図は、一般的なライブラリで使われる Closed/Open/Half-Open の状態遷移パターンを示しています。Istio が実装するのは、リソース上限に基づく接続プールのサーキットブレーカーと、エンドポイント単位の受動的な異常検出・切り離しです。メッシュ全体で共有する単一の3状態ブレーカーを公開しているわけではありません。上限や健全性の観測は、各プロキシのアップストリームクラスター／優先度ごとに行われ、同時実行時には上限を超える場合があります。異常と判定されたエンドポイントは一時的に振り分け対象から外されますが、Pod が削除されるわけではありません。以下の例は、それぞれ別の設定方法です。

![連続エラー数がしきい値を超えるとサーキットブレーカーが Closed から Open へ移行し、待機時間の経過後に Half-Open となり、成功すれば Closed、失敗すれば Open に戻る状態遷移図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-1.html)

## 接続プールの設定 {#connection-pool-settings}

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
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
```

## 異常なエンドポイントの検出 {#outlier-detection}

異常検出は、切り離し上限やパニック時の動作に従って、健全でないエンドポイントをロードバランシング対象から一時的に除外します。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5        # 5 consecutive errors
      interval: 30s               # Check every 30 seconds
      baseEjectionTime: 30s       # Minimum; repeated ejection can last longer
      maxEjectionPercent: 50      # Remove up to 50%
      minHealthPercent: 40        # Below this, disable outlier isolation and use all hosts
```

### 高度な異常検出設定

連続エラーの検出では、次の定期スイープを待たずにエンドポイントが切り離されることがあります。`interval` は定期スイープの間隔であり、各切り離しの前に必ず待つ時間ではありません。`minHealthPercent` はフェイルオープンのしきい値であり、健全なエンドポイントを一定割合確保する下限ではありません。`maxEjectionTime` は Envoy のフィールドですが、Istio のこの DestinationRule API では公開されていません。これらのマニフェストに設定しないでください。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: advanced-outlier
spec:
  host: api-service
  trafficPolicy:
    outlierDetection:
      # Consecutive error based
      consecutiveGatewayErrors: 3    # HTTP 502/503/504
      consecutive5xxErrors: 5        # All HTTP 5xx

      # Time intervals
      interval: 10s                  # Check every 10 seconds
      baseEjectionTime: 30s          # First ejection time

      # Rate limits
      maxEjectionPercent: 50         # Remove up to 50%
      minHealthPercent: 30           # Fail-open/panic threshold, not a health guarantee

      # Separate local connection errors from upstream response errors
      splitExternalLocalOriginErrors: true
```

## リトライポリシーとの組み合わせ {#combination-with-retry-policy}

可用性を高めるために、サーキットブレーカーとリトライを組み合わせます。

### 基本的な組み合わせ

```yaml
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
      attempts: 3                    # 3 retries
      perTryTimeout: 2s              # 2 second timeout per attempt
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

### リトライ予算パターン

この予算は、各プロキシのクラスターにおけるアクティブ／保留中リクエスト数に対する同時リトライ数を制限します。リクエスト数／秒の上限ではありません。リトライしても安全な読み取りにはリトライポリシーを使い、それ以外のメソッドではリトライを明示的に無効化します。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-retry-budget
spec:
  hosts:
  - payment-service
  http:
  - match:
    - method:
        regex: "^(GET|HEAD)$"
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 2                    # Minimize retries
      perTryTimeout: 1s              # Fast fail
      retryOn: connect-failure,refused-stream
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    retryBudget:
      percent: 20
      minRetryConcurrency: 3
    connectionPool:
      http:
        http1MaxPendingRequests: 5   # Low queue
        maxRequestsPerConnection: 1  # 1 request per connection
    outlierDetection:
      consecutive5xxErrors: 3           # Fast blocking
      interval: 5s
      baseEjectionTime: 60s          # Long recovery time
```

## 実践例 {#practical-examples}

### 1. メッシュ内サービス向けサーキットブレーカー

#### シナリオ: データベースサービスの保護

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-service-circuit-breaker
  namespace: production
spec:
  host: database-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100          # Maximum 100 connections
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

**ユースケース**:
- データベース接続プールの枯渇を防ぐ
- 遅いクエリによる障害の連鎖を抑える
- 健全でないインスタンスを自動的に振り分け対象から外す

ここで示すネイティブデータベースプロトコルの設定は、TCP 上限と TCP の障害観測だけを対象にします。プロキシ単位の接続上限はデータベース全体のプールサイズではなく、遅い SQL クエリも検出しません。

### 2. `maxConnections: 1` パターン（単一接続）

#### シナリオ: レガシーシステムまたはリソース制約のあるサービス

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-system-protection
spec:
  host: legacy-api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1            # Limit to 1 connection
      http:
        http1MaxPendingRequests: 1   # 1 pending request
        maxRequestsPerConnection: 1  # 1 request per connection
        h2UpgradePolicy: DO_NOT_UPGRADE  # Prevent HTTP/2 upgrade
    outlierDetection:
      consecutive5xxErrors: 1           # Block immediately on 1 error
      interval: 10s
      baseEjectionTime: 60s
```

**ユースケース**:
- レガシーシステムが同時接続を処理できない場合
- 外部 API のレート制限が非常に厳しい場合
- 単一接続による順次処理が必要な場合

`maxConnections: 1` は、メッシュ全体の処理を直列化したり、外部 API のクォータを強制したりしません。複数のプロキシにはそれぞれ別の上限があり、HTTP/2 では1接続上で複数のリクエストを多重化できます。また、`maxRequestsPerConnection: 1` は接続の再利用を無効にする設定であり、実行数を1つに保証するものではありません。メッシュ全体で調整するには、アプリケーションのキューやレートリミッターを使ってください。

### 3. サブセットごとのサーキットブレーカー

#### シナリオ: バージョンごとに異なる設定

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subset-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    # Default policy (all subsets)
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
    # v1 uses default policy

  - name: v2
    labels:
      version: v2
    trafficPolicy:
      # v2 has stricter policy (new version testing)
      connectionPool:
        http:
          http1MaxPendingRequests: 10
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s

  - name: v3-canary
    labels:
      version: v3
    trafficPolicy:
      # v3 Canary is very strict (initial deployment)
      connectionPool:
        http:
          http1MaxPendingRequests: 5
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutive5xxErrors: 1
        interval: 5s
        baseEjectionTime: 120s
```

### 4. 高度な接続プールパターン

#### シナリオ: 高性能サービス

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-performance-service
spec:
  host: api-gateway
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000         # High concurrent connections
        connectTimeout: 3s
        tcpKeepalive:
          time: 7200s
          interval: 75s
          probes: 9
      http:
        http1MaxPendingRequests: 500
        http2MaxRequests: 1000
        maxRequestsPerConnection: 100  # Connection reuse
        idleTimeout: 300s
        h2UpgradePolicy: UPGRADE       # Use HTTP/2
    outlierDetection:
      consecutive5xxErrors: 10          # Lenient setting
      interval: 60s
      baseEjectionTime: 30s
      maxEjectionPercent: 20         # Remove up to 20% only
```

### 5. ヘルスチェックに基づくサーキットブレーカー

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: health-check-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      # HTTP status code based
      consecutiveGatewayErrors: 5    # 502, 503, 504
      consecutive5xxErrors: 3        # 500~599

      # Performance based
      interval: 10s
      baseEjectionTime: 30s

      # Dynamic adjustment
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
```

## 外部サービス向けサーキットブレーカー {#external-service-circuit-breaker}

以下の HTTP 例では、アプリケーションからサイドカーまでは平文 HTTP を使い、サイドカーが実際の外部ホストの 443 番ポートへ検証済み TLS で接続します。アプリケーションがすでに TLS を使用している場合は二重 TLS を避け、該当する通信レイヤーから見えるポリシーだけを設定してください。ネイティブ MongoDB のアプリケーション TLS／認証は、別途クライアントとサーバーで設定する要件です。

外部サービスを保護するには ServiceEntry と組み合わせます。

### 1. 外部 API 向けサーキットブレーカー

```yaml
# ServiceEntry: Register external API
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
spec:
  hosts:
  - api.payment-provider.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
# DestinationRule: Apply Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api-circuit-breaker
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 10           # External API is limited
      http:
        http1MaxPendingRequests: 5
        maxRequestsPerConnection: 1  # Minimize connection reuse
    outlierDetection:
      consecutive5xxErrors: 3           # Fast blocking
      interval: 30s
      baseEjectionTime: 120s         # Long recovery time
      maxEjectionPercent: 100        # Can completely block
    tls:
      mode: SIMPLE
      sni: api.payment-provider.com
      subjectAltNames:
      - api.payment-provider.com
```

### 2. 外部データベース向けサーキットブレーカー

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-mongodb
spec:
  hosts:
  - mongodb.external-cluster.com
  ports:
  - number: 27017
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-mongodb-circuit-breaker
spec:
  host: mongodb.external-cluster.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. レート制限のある外部サービス

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: rate-limited-api
spec:
  hosts:
  - api.rate-limited-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: rate-limited-api-protection
spec:
  host: api.rate-limited-service.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 1   # Minimize queue
        maxRequestsPerConnection: 0  # Reuse connections; not a quota limiter
        idleTimeout: 1s              # Fast connection release
    outlierDetection:
      consecutive5xxErrors: 3           # Default HTTP 5xx detection; not 429
      interval: 60s
      baseEjectionTime: 30s          # Independent of provider Retry-After
    tls:
      mode: SIMPLE
      sni: api.rate-limited-service.com
      subjectAltNames:
      - api.rate-limited-service.com
---
# VirtualService: Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: rate-limited-api-retry
spec:
  hosts:
  - api.rate-limited-service.com
  http:
  - route:
    - destination:
        host: api.rate-limited-service.com
    retries:
      attempts: 0                    # Disable retry (rate limit)
    timeout: 10s
```

HTTP 429 に対応するには、プロバイダー固有のスロットリングと `Retry-After` の処理が必要です。既定の 5xx 異常検出や接続の頻繁な切り替えでは、API クォータを強制できず、リセット時刻も推測できません。

## モニタリングとデバッグ {#monitoring-and-debugging}

### Envoy メトリクスを確認する

```bash
# Check Circuit Breaker status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep circuit_breakers

# Outlier Detection status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier_detection

# Connection Pool status
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep upstream_rq
```

### 主なメトリクス

```promql
# Prometheus queries
# Requests circuit-open gauge (0/1)
envoy_cluster_circuit_breakers_default_rq_open

# Pending-request circuit-open gauge (0/1)
envoy_cluster_circuit_breakers_default_rq_pending_open

# Outlier Detection Ejection
envoy_cluster_outlier_detection_ejections_active

# Connection pool overflow
envoy_cluster_upstream_rq_pending_overflow

# Retry count
envoy_cluster_upstream_rq_retry
```

### Grafana ダッシュボード

```yaml
# Circuit Breaker Dashboard
- expr: envoy_cluster_circuit_breakers_default_rq_open
  legend: "Circuit Breaker Open State"

- expr: envoy_cluster_outlier_detection_ejections_active
  legend: "Ejected Instances"

- expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m])
  legend: "Connection Pool Overflow"
```

### `istioctl` コマンド

```bash
# Check Proxy configuration
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local

# Check Circuit Breaker settings
istioctl proxy-config clusters <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .circuitBreakers'

# Check Outlier Detection settings
istioctl proxy-config clusters <pod-name> -o json | \
  jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .outlierDetection'
```

## 重要な考慮事項 {#important-considerations}

### サーキットブレーカーはデータ整合性を保証しない

**基本原則**: サーキットブレーカーは**障害の隔離**に使うものであり、**リクエストの重複防止**や**データ整合性の保証**を行うものではありません。

#### サーキットブレーカーの役割と限界

![サーキットブレーカーが行うこと（障害中のサービスの隔離、障害の連鎖防止、リソース保護、自動復旧の試行）と、行わないこと（重複防止、データ整合性、トランザクション、冪等性の保証）を線で結んで示す図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-2.html)

#### 問題シナリオ: リトライ + サーキットブレーカー

![応答が失われるたびに Istio プロキシが支払い POST リクエストを再試行し、そのたびに支払い行が挿入されるため、サーキットブレーカーが5回の連続エラーで作動する前に重複行が3つ残るシーケンス図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-07-circuit-breaker-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-07-circuit-breaker-3.html)

**問題**: サーキットブレーカーが作動する（5回連続エラーの後）前に、すでに**3件の重複した支払い**が発生しています。

#### 誤った使用例

```yaml
# Dangerous: POST request + Retry + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-dangerous
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # 3 retries on POST
      perTryTimeout: 2s
      retryOn: 5xx,reset
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s

# Result:
# - attempts: 3 allows up to 4 deliveries per original request; the ejection threshold is not a multiplier
# - Critical operations like payment, inventory deduction get duplicated
# - Data consistency destroyed
```

#### 正しい使用パターン

**パターン1: 読み取りは安全にリトライし、書き込みではメッシュのリトライを無効化する**

```yaml
# Safe: Read-only + Circuit Breaker
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: product-catalog-safe
spec:
  hosts:
  - product-catalog
  http:
  - match:
    - method:
        regex: "GET|HEAD|OPTIONS"  # Read-only only
    route:
    - destination:
        host: product-catalog
    retries:
      attempts: 3  # GET is safe
      perTryTimeout: 2s
      retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
spec:
  host: product-catalog
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

```yaml
# Safe: Disable Retry for POST
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-safe
spec:
  hosts:
  - payment-service
  http:
  - match:
    - method:
        exact: POST
    route:
    - destination:
        host: payment-service
    timeout: 10s
    retries:
      attempts: 0  # Disable Retry for POST
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-circuit-breaker
spec:
  host: payment-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**パターン2: アプリケーションレベルの冪等性 + サーキットブレーカー**

冪等性キーは、認証済みの呼び出し元とリクエスト本文に結び付け、業務上の変更／結果と一緒にアトミックに記録する必要があります。Redis の存在確認後に支払い処理を行い、別々にキャッシュへ書き込む方法には競合があり、安全な実装ではありません。必要に応じて[アトミックな冪等性ワークフロー](05-retry-timeout.md)と、下流サービスの冪等性契約や Outbox を利用してください。それらを整えたうえで次のリトライポリシーを使用します。ヘッダーが存在するだけでは不十分です。



```yaml
# Istio: Retry is safe when Idempotency is guaranteed
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-with-idempotency
spec:
  hosts:
  - payment-service
  http:
  - match:
    - headers:
        x-idempotency-key:
          regex: ".+"  # Idempotency Key required
    route:
    - destination:
        host: payment-service
    retries:
      attempts: 3  # Safe with Idempotency
      perTryTimeout: 2s
      retryOn: 5xx,reset
  - route:  # Disable Retry without Idempotency Key
    - destination:
        host: payment-service
    retries:
      attempts: 0
```

#### サービス種別ごとの安全性戦略

| サービス種別 | リトライ | サーキットブレーカー | 冪等性が必要か |
|-------------|-------|----------------|---------------------|
| **商品カタログ** | 3回 | 必須 | 不要 |
| **ショッピングカート** | 読み取りは既定でリトライ | 必要に応じて調整 | リトライ可能な更新には必要 |
| **注文作成** | 0回 | 必須 | 必須 |
| **支払い** | 0回 | 必須 | 必須 |
| **在庫の差し引き** | 0回 | 必須 | 必須 |
| **ポイントの加算** | 0回 | 必須 | 必須 |
| **通知の送信** | 配信重複排除がある場合のみ | 必要に応じて調整 | 配信／メッセージの冪等性が必要 |

#### 接続プールとデータ整合性

接続プールの設定も**データ整合性を保証しません**。制限するのは同時接続数だけです。

```yaml
# Misconception: Does maxConnections=1 prevent duplicates?
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-single-connection
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1  # Does NOT prevent duplicates
      http:
        http1MaxPendingRequests: 1

# maxConnections=1:
# - Only limits concurrent connections
# - Cannot prevent duplicate requests from Retry
# - Retries after network timeout are separate connections
```

#### 実践チェックリスト

**デプロイ前の確認**:

- [ ] POST/PUT/DELETE/PATCH リクエストのリトライ設定を確認する
- [ ] 検証済みのアプリケーション契約で許可されている場合を除き、冪等でない書き込みには `attempts: 0` を設定する
- [ ] サーキットブレーカーとリトライを組み合わせる際の重複の可能性を確認する
- [ ] 支払いや在庫などの重要な操作には冪等性キーを実装する
- [ ] アプリケーションレベルの検証ロジックがあることを確認する
- [ ] テスト環境で障害シミュレーションを実施する

**モニタリング**:

```bash
# Check Retry occurrence count
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream_rq_retry

# Check Circuit Breaker activation
kubectl exec -n <namespace> <pod> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep circuit_breakers

# Check logs for suspected duplicate requests
kubectl logs -n <namespace> <pod> | grep -i "duplicate\|idempotency"
```

## ベストプラクティス {#best-practices}

### 1. 段階的な設定

```yaml
# Stage 1: Start with lenient settings
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage1
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 10        # Lenient
      interval: 60s
      baseEjectionTime: 30s
```

```yaml
# Stage 2: Adjust after monitoring
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: service-circuit-breaker-stage2
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5         # Moderate
      interval: 30s
      baseEjectionTime: 30s
```

### 2. サービス種別に応じた設定

```yaml
# Frontend service: Lenient
connectionPool:
  http:
    http1MaxPendingRequests: 100
    maxRequestsPerConnection: 10
outlierDetection:
  consecutive5xxErrors: 10
```

```yaml
# Backend service: Moderate
connectionPool:
  http:
    http1MaxPendingRequests: 50
    maxRequestsPerConnection: 5
outlierDetection:
  consecutive5xxErrors: 5
```

```yaml
# Native database/cache TCP example
connectionPool:
  tcp:
    maxConnections: 10
outlierDetection:
  consecutive5xxErrors: 3
```

```yaml
# External API: Very strict
connectionPool:
  http:
    http1MaxPendingRequests: 5
    maxRequestsPerConnection: 1
outlierDetection:
  consecutive5xxErrors: 1
```

### 3. アラートの設定

```yaml
# Prometheus Alert Rules
groups:
- name: circuit-breaker
  rules:
  - alert: CircuitBreakerOpen
    expr: envoy_cluster_circuit_breakers_default_rq_open > 0
    for: 1m
    annotations:
      summary: "Circuit breaker is open"

  - alert: HighConnectionPoolOverflow
    expr: rate(envoy_cluster_upstream_rq_pending_overflow[5m]) > 10
    for: 2m
    annotations:
      summary: "Connection pool overflow rate is high"

  - alert: HighOutlierEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total[5m]) > 5
    for: 3m
    annotations:
      summary: "High outlier ejection rate"
```

### 4. テストシナリオ

負荷テストは、準備済みのテストサービスに対してのみ実施してください。実際のメトリクスは別途確認します。`proxy-config` が示すのは設定済みのしきい値であり、現在サーキットが開いているかどうかではありません。30秒待っても、切り離しが繰り返されたエンドポイントが復旧するとは限りません。

```bash
#!/bin/bash
# Circuit Breaker test

# 1. Normal traffic
echo "=== Normal Traffic ==="
for i in {1..10}; do
  curl -s http://service/api | jq .status
  sleep 0.1
done

# 2. Increased load
echo "=== Increased Load ==="
for i in {1..100}; do
  curl -s http://service/api &
done
wait

# 3. Check Circuit Breaker status
echo "=== Circuit Breaker Status ==="
istioctl proxy-config clusters <pod> -o json | jq '.[] | .circuitBreakers'

# 4. Wait for recovery
echo "=== Waiting for Recovery ==="
sleep 30

# 5. Verify recovery
echo "=== Recovery Check ==="
curl -s http://service/api | jq .status
```

### 5. ドキュメントのテンプレート

以下は例示用の負荷／復旧数値であり、固定された Istio の保証値ではありません。必要な Envoy 統計情報を有効にしてください。プロキシイメージに curl が含まれない場合は、ローカルの admin ポートをポートフォワードするか、`istioctl dashboard envoy` を利用します。


```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: my-service-circuit-breaker
  annotations:
    # Configuration purpose
    purpose: "Protect database connection pool"

    # Threshold rationale
    threshold-rationale: |
      - maxConnections: 100 (DB connection pool size)
      - consecutive5xxErrors: 5 (observed error pattern)
      - baseEjectionTime: 30s (average recovery time)

    # Test results
    test-results: |
      - Load test: 1000 RPS without overflow
      - Failure test: Circuit opens after 5 errors
      - Recovery test: Auto-recovery after 30s

    # Operations guide
    operations: |
      - Monitor: envoy_cluster_circuit_breakers_*
      - Alert: Circuit open > 1min
      - Rollback: restore the reviewed previous DestinationRule configuration
spec:
  host: my-service
```

## 参考資料

- [Istio Circuit Breaker](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
- [Envoy Circuit Breaking](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [Envoy Outlier Detection](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [Netflix Hystrix](https://github.com/Netflix/Hystrix/wiki/How-it-Works)

- [主な参考資料 1](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [主な参考資料 2](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/circuit_breaking)
- [主な参考資料 3](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [主な参考資料 4](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [主な参考資料 5](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [主な参考資料 6](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
