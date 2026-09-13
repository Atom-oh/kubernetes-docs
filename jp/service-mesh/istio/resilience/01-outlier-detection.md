# 外れ値検出

> **最終更新**: September 11, 2026 · Istio 1.31。独立したサイドカー例です。テスト前に指定名前空間と実ワークロード/エンドポイントを作成してください。同一hostの例は選択肢です。値は例示で、負荷テストはしていません。

外れ値検出は異常動作するサービスインスタンスを自動検出し、通信プールから外すサーキットブレーカーパターンの一種です。

## 目次

1. [概要](#overview)
2. [動作](#how-it-works)
3. [基本設定](#basic-configuration)
4. [高度な設定](#advanced-configuration)
5. [外部サービス保護（ServiceEntry）](#protecting-external-services-serviceentry)
6. [実践例](#practical-examples)
7. [監視](#monitoring)
8. [トラブルシューティング](#troubleshooting)

## 概要 {#overview}

外れ値検出は受動的で、観測プロキシごとにローカルです。HTTP可視性があれば対象上流応答とローカル接続失敗を計数します。DestinationRuleの遅延しきい値や定期復旧プローブは使いません。除外はそのプロキシの負荷分散選択可否を変え、Pod削除やサービス修復はしません。


### 主な機能

1. **検出**: 設定した連続HTTP/転送失敗を計数。
2. **除外**: 上限と適用設定が許す場合にホストを外す。
3. **復帰**: 除外期間後に再選択可能にする。実復旧には通信成功が必要。

## 動作 {#how-it-works}

### 外れ値検出処理

成功で該当連続エラー列がリセットされます。対象失敗がしきい値に達すると`interval`を待たずその場で除外し得ます。再除外で期間が増えます（基本期間×倍率、Envoy上限あり）。固定30秒プローブや指数的倍増ではありません。


### 検出方法

| 方法 | 説明 | 用途 |
|--------|-------------|--------------|
| **連続エラー** | 連続5xxを検出 | アプリクラッシュ |
| **ゲートウェイエラー** | 502、503、504を検出 | サービス過負荷 |
| **接続失敗** | TCP接続失敗を検出 | ネットワーク問題 |
| **レイテンシー** | DestinationRuleの外れ値しきい値ではない | 遅延を観察し、アプリ/ルートタイムアウトは別設定 |

## 基本設定 {#basic-configuration}

### 連続エラーに基づく検出

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-outlier
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### 主なパラメーター

#### consecutive5xxErrors
- **説明**: 連続エラー回数のしきい値
- **デフォルト**: 5
- **調整範囲例**: 3-10（サービス特性による）

```yaml
# Sensitive service (fast detection)
consecutive5xxErrors: 3

# General service
---
consecutive5xxErrors: 5

# Lenient setting (prevent false positives)
---
consecutive5xxErrors: 10
```

#### interval
- **説明**: 定期除外走査間隔。連続エラー検出はその場で動作
- **デフォルト**: 10s
- **調整範囲例**: 10s-60s

```yaml
# Fast detection (high load)
interval: 10s

# General case
---
interval: 30s

# Stable service
---
interval: 60s
```

#### baseEjectionTime
- **説明**: インスタンスの最小除外時間
- **デフォルト**: 30s
- **調整範囲例**: 30s-300s

```yaml
# Fast recovery attempt
baseEjectionTime: 30s

# General case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

#### maxEjectionPercent
- **説明**: 同時除外できるインスタンスの最大割合
- **デフォルト**: 10%
- **調整範囲例**: 10%-50%

```yaml
# Conservative (stability first)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (quality first)
---
maxEjectionPercent: 50
```

## 高度な設定 {#advanced-configuration}

### ゲートウェイエラーに基づく検出

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-gateway-errors
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveGatewayErrors: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

### 正常プールのパニックしきい値

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-panic-threshold-example
  namespace: default
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      minHealthPercent: 50
      maxEjectionPercent: 30
```

`minHealthPercent: 50`はfail-open/パニックの選択です。正常ホスト割合がしきい値未満なら異常ホストも使用できます。最小要求数、正常容量保証、スプリットブレイン防止ではありません。Istioデフォルトは0で、他例も0で無効にします。除外上限は残るエンドポイントを正常にはしません。

### 接続失敗に基づく検出

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-connection-errors
  namespace: default
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
      consecutiveLocalOriginFailures: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

### 成功率に基づく検出（高度）

Envoyには最小ホスト/要求量と偏差パラメーターを持つ統計的成功率検出があり、単純な「95%未満」ではありません。Istio1.31 DestinationRuleは`enforcingConsecutiveErrors`/`enforcingSuccessRate`やその統計しきい値を公開しません。[リリース実装](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go)は成功率適用を明示無効にします。`splitExternalLocalOriginErrors`はエラー区分の分離で最小要求数ではありません。ここでは対応する連続エラー設定を使います。高度EnvoyFilter変更には版固有設定と実行時検証が必要です。

## 外部サービス保護（ServiceEntry） {#protecting-external-services-serviceentry}

外部APIや従来システムをServiceEntryとして登録し、外れ値検出で障害伝播を防ぎます。

### 外部API保護アーキテクチャ

![アプリのEnvoyがServiceEntryの3外部APIへ外れ値検出を適用し、エラーを返す1つを除外して正常2つへ送り続ける。](../../../.gitbook/assets/en-service-mesh-istio-resilience-01-outlier-detection-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-01-outlier-detection-2.html)

HTTPを認識する外部API例では、アプリが**HTTP port80**を呼び、サイドカーがtarget443へTLSを開始する必要があります。SNI/SANとプロキシOS信頼ストアを使い、非公開CAなら適切なCAバンドルをマウントします。アプリ→サイドカーは平文なので、そのホップも暗号化必須なら不適切です。アプリ開始HTTPSでは追加SIMPLE TLSなしのパススルーを使います。その場合Envoyに見えるのは転送失敗で、HTTP状態/遅延やHTTP再試行ルールではありません。認証情報送信前に参加、経路、証明書検証を確認します。host/IPは例で、作成済みサービスではありません。許可されたエンドポイントへ置換してください。

### 例1: 単一外部API（DNSベース）

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
  namespace: payment
spec:
  host: api.payment-provider.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.payment-provider.com
        subjectAltNames:
        - api.payment-provider.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-payment-api
  namespace: payment
spec:
  hosts:
  - api.payment-provider.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.payment-provider.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**使用例**:
```go
package payment

import (
    "bytes"
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

var paymentClient = &http.Client{
    Timeout: 5 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        return http.ErrUseLastResponse
    },
}

// payload, authentication and payment-provider idempotency are application concerns.
// Requires the port80-to443 sidecar TLS-origination policy above.
func processPayment(ctx context.Context, payload []byte) error {
    req, err := http.NewRequestWithContext(ctx, http.MethodPost,
        "http://api.payment-provider.com/v1/charge", bytes.NewReader(payload))
    if err != nil { return err }
    req.Header.Set("Content-Type", "application/json")
    resp, err := paymentClient.Do(req)
    if err != nil { return fmt.Errorf("payment transport failed: %w", err) }
    defer resp.Body.Close()
    _, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 1<<20))
    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        return fmt.Errorf("payment endpoint returned HTTP %d", resp.StatusCode)
    }
    return nil
}
```

外れ値検出は後のホスト選択に影響し、決済の再試行/重複排除はしません。VirtualServiceはメッシュ再試行を明示無効にします。DNS名がEnvoyホスト1つしか公開しない場合もあり、除外後の代替先は保証されません。転送エラーでは遠隔トランザクションのコミット有無は分かりません。

### 例2: 複数外部APIエンドポイント

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  resolution: STATIC
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  endpoints:
  - address: 203.0.113.10
    labels:
      region: us-east-1
    locality: us-east-1
  - address: 203.0.113.20
    labels:
      region: us-west-2
    locality: us-west-2
  - address: 203.0.113.30
    labels:
      region: eu-central-1
    locality: eu-central-1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-weather-api
  namespace: weather
spec:
  host: weather.api.com
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 5s
      http:
        http1MaxPendingRequests: 20
        maxRequestsPerConnection: 5
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 60s
      maxEjectionPercent: 33
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: weather.api.com
        subjectAltNames:
        - weather.api.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-weather-api
  namespace: weather
spec:
  hosts:
  - weather.api.com
  http:
  - name: no-retries
    route:
    - destination:
        host: weather.api.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

3つの文書用IPは同一上流プールのメンバーです。`maxEjectionPercent`はプール上限で「リージョンごと1つ」ではありません。ラベルはメタデータで、トポロジーは`locality`が提供します。丸め、検出ホスト数、現在の除外が実際に外れる対象へ影響します。

### 例3: レガシーDBの保護

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: database
spec:
  hosts:
  - legacy-db.company.internal
  resolution: DNS
  ports:
  - number: 5432
    name: tcp-postgres
    protocol: TCP
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: legacy-postgres
  namespace: database
spec:
  host: legacy-db.company.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 10s
    outlierDetection:
      consecutive5xxErrors: 10
      consecutiveLocalOriginFailures: 5
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
```

TCP例は接続/転送失敗を観測し、SQLエラー、ロック、クエリ遅延は観測しません。ServiceEntryが宛先を一意に特定するようにします。共有TCPポートにはDNS捕捉/VIP設計が必要な場合があります。書き込み可能DB primaryを選出したり、レプリカ切り替えを安全にしたりはしません。

### 例4: 再試行付き外部API

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  hosts:
  - maps.googleapis.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: maps.googleapis.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-geocoding-api
  namespace: location
spec:
  host: maps.googleapis.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: maps.googleapis.com
        subjectAltNames:
        - maps.googleapis.com
```

geocoding例は一致する冪等readだけを再試行します。メソッドを見られるようHTTP port80を呼びます。HTTPSパススルーではこのHTTPポリシーは使えません。合計5sで各試行が2sなら、最初の試行と3再試行をすべて完了できません。

### 例5: レート制限付き外部サービス

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: api
data:
  config.yaml: "domain: external-api-ratelimit\ndescriptors:\n- key: destination_cluster\n  value: outbound|80||api.third-party.com\n  rate_limit:\n    unit: second\n    requests_per_unit: 100\n"
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  host: api.third-party.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveGatewayErrors: 2
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 50
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.third-party.com
        subjectAltNames:
        - api.third-party.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-rate-limited-api
  namespace: api
spec:
  hosts:
  - api.third-party.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.third-party.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

ConfigMapはレート制限サービスの設定断片だけです。backing store、送信Envoyフィルター、一致する`destination_cluster` descriptorを持つ互換サービスへマウントする必要があります。単体では何も強制しません。gateway errorは502/503/504で429ではなく、標準5xx検出は429を含めません。除外時間は提供者クォータリセットと同期しません。正常だがクォータ制限された全ホストを除外するより、クォータを考慮した処理とRetry-After/アプリバックオフを優先します。

### 外部サービス外れ値検出のベストプラクティス

#### 1. エラータイプを区別

```yaml
outlierDetection:
  # Gateway errors (502, 503, 504)
  consecutiveGatewayErrors: 2  # Detect quickly

  # 5xx errors (500, 501, etc.)
  consecutive5xxErrors: 3

  # Local errors (timeout, connection failure)
  consecutiveLocalOriginFailures: 3

  # Track local and remote errors separately
  splitExternalLocalOriginErrors: true
```

**重要**: `splitExternalLocalOriginErrors: true`の場合:
- **ローカル起因失敗**: 上流ホストに帰属する接続timeout/reset/refusal。DNS解決失敗では除外ホストが存在しない場合あり
- **上流失敗**: 外部APIが返す5xx

より正確に検出するため別々に計数します。

#### 2. タイムアウト設定

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
  - timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
  - name: other-methods-no-retry
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 3s
    outlierDetection:
      consecutiveLocalOriginFailures: 3
      splitExternalLocalOriginErrors: true
      minHealthPercent: 0
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
```

#### 3. 外部サービス監視

```promql
# Outlier Detection metrics
# 1. Ejected external endpoints
envoy_cluster_outlier_detection_ejections_active{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}

# 2. Local errors (timeout, connection failure)
rate(envoy_cluster_upstream_rq_timeout{
  namespace="default", cluster_name=~"outbound.*api\\.external\\.com.*"
}[5m])

# 3. External API 5xx errors
rate(istio_requests_total{
  reporter="source", source_workload_namespace="default",
  destination_service="api.external.com",
  response_code=~"5.."
}[5m])

# 4. External API response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{
    reporter="source", source_workload_namespace="default",
    destination_service="api.external.com"
  }[5m])) by (le)
)
```

#### 4. アラート設定

Prometheusルールファイル断片で、Kubernetesリソースではありません。Prometheusでマウント/選択するか、groupsを選択済みPrometheusRuleに包みます。しきい値は通信量、no-data、スクレイプ健全性の処理が必要で、検証済みSLOではありません。遅延はミリ秒、rateは毎秒です。


```yaml
# Prometheus Alert Rules
groups:
- name: external_api_alerts
  interval: 1m
  rules:
  # High external API error rate
  - alert: ExternalAPIHighErrorRate
    expr: |
      (sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*",
        response_code=~"5.."
      }[5m])) by (destination_service)
      /
      sum(rate(istio_requests_total{
        reporter="source", source_workload_namespace="default",
        destination_service=~".*external.*"
      }[5m])) by (destination_service))
      * 100 > 5
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate for external API {{ $labels.destination_service }}"
      description: "Error rate is {{ $value }}%"

  # External API instance ejected
  - alert: ExternalAPIInstanceEjected
    expr: |
      envoy_cluster_outlier_detection_ejections_active{
        namespace="default", cluster_name=~"outbound.*external.*"
      } > 0
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "External API instance ejected"
      description: "{{ $value }} instances ejected from {{ $labels.cluster_name }}"

  # Increased external API timeouts
  - alert: ExternalAPIHighTimeout
    expr: |
      rate(envoy_cluster_upstream_rq_timeout{
        namespace="default", cluster_name=~"outbound.*external.*"
      }[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High timeout rate for external API"
      description: "Timeout rate is {{ $value }} req/s"
```

#### 5. トラブルシューティング

呼び出し元プロキシで診断します。接続コマンドは許可されたアプリ/テストコンテナのcurlと実読み取り専用health endpointが必要です。`istio-proxy`内のcurlはアプリ通信経路を迂回する場合があります。汎用監視クエリは別の`default`/`api.external.com`例を参照するため、他例では範囲を調整します。


```bash
# 1. Check ServiceEntry
kubectl get serviceentry -A
kubectl describe serviceentry external-api -n <namespace>

# 2. Verify DestinationRule application
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn api.external.com -o json | \
  jq '.[] | {name: .name, outlierDetection: .outlierDetection}'

# 3. Test external API connection
kubectl exec <client-pod> -n default -c <app-container> -- \
  curl --max-time 5 -v http://api.external.com/health

# 4. Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep "outbound.*external"

# 5. Outlier Detection status
istioctl x envoy-stats <pod-name> -n <namespace> --type clusters
```

### 外部サービス障害シナリオ

#### シナリオ1: 一時的な外部API障害

```yaml
# Configuration: Fast detection and recovery
outlierDetection:
  consecutive5xxErrors: 3           # 3 consecutive errors
  consecutiveGatewayErrors: 2    # 2 gateway errors
  interval: 10s                  # Evaluate every 10 seconds
  baseEjectionTime: 30s          # Recovery attempt after 30 seconds
  maxEjectionPercent: 50         # Maximum 50% ejection
```

**実効制限に従う期待動作**:

1. 対象502/503応答がgatewayしきい値へ計数される。
2. 連続2回に達すると適用/上限が許す場合にホスト除外。
3. 除外期間後に再選択可能。能動プローブは設定していない。
4. 再除外でEnvoy倍率/上限により期間増加。プール復帰は提供者の復旧証明ではない。

#### シナリオ2: 外部API全停止

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      tier: primary
  - address: 203.0.113.20
    labels:
      tier: secondary
  - address: 203.0.113.30
    labels:
      tier: tertiary
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-ha
  namespace: default
spec:
  host: api.external.com
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 66
      minHealthPercent: 0
      splitExternalLocalOriginErrors: true
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE
        sni: api.external.com
        subjectAltNames:
        - api.external.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-ha
  namespace: default
spec:
  hosts:
  - api.external.com
  http:
  - name: no-retries
    route:
    - destination:
        host: api.external.com
        port:
          number: 80
    retries:
      attempts: 0
    timeout: 5s
```

**解釈**:

3エンドポイントは同一プールです。`tier: primary/secondary/tertiary`ラベルはフェイルオーバー優先順位を定めず、通常の負荷分散は任意の適格先を選べます。失敗先をローカル除外し別を選ぶことはできますが、完全停止した外部サービスはルーティングで直りません。`minHealthPercent: 0`は異常ホストのパニック使用を無効にし、割合上限は正常な1つの生存を保証しません。順序付き切り替えが必要なら明示的locality優先度かアプリ/提供者の機構を使います。接続テスト前に文書用IPを置き換えます。

## 実践例 {#practical-examples}

### 例1: マイクロサービスチェーン

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-outlier
  namespace: default
spec:
  host: backend
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: database-outlier
  namespace: default
spec:
  host: database
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 300s
      maxEjectionPercent: 20
      minHealthPercent: 0
```

### 例2: カナリアデプロイとの併用

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
  namespace: default
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
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s
        maxEjectionPercent: 100
        minHealthPercent: 0
```

全v2を除外しても10%のルート重みはv1へ移りません。空カナリアsubsetに選ばれた要求は失敗し得ます。Rolloutコントローラーが健全性から重み変更/ロールバックする必要があります。ワークロードラベルは両subsetに一致する必要があります。

### 例3: マルチリージョンデプロイ

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
  namespace: default
spec:
  host: api
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 80
            us-west-2/*: 20
    outlierDetection:
      consecutive5xxErrors: 10
      interval: 60s
      baseEjectionTime: 120s
      maxEjectionPercent: 30
      minHealthPercent: 0
```

80/20は正常な両地域へ意図的に送ります。待機フェイルオーバーではなく、実地域localityメタデータ、地域間接続、容量が必要です。地域名だけでマルチクラスターメッシュは作られません。

### 例4: 接続プール + 外れ値検出

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-full-protection
  namespace: default
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
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 3
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

## 監視 {#monitoring}

### Prometheusメトリクス

[耐障害性概要](README.md#resilience-metrics)のように任意統計とスクレイプラベルを有効にします。例は各プロキシの`pod`/`cluster_name`を保持し、呼び出し元間の除外合計は一意server Pod数ではありません。リリースbootstrapは`cluster_name`を使います。collector relabel後を確認してください。`enforced_*`は実除外を数え、上限で止まっても`detected_*`は増え得ます。

```promql
# Current ejections, not a cumulative event counter
envoy_cluster_outlier_detection_ejections_active{namespace="default"}

# Enforced ejection events per second
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m])

# Percentage of the total observed pool, excluding zero-size pools
100 * envoy_cluster_outlier_detection_ejections_active{namespace="default"} /
(envoy_cluster_membership_total{namespace="default"} > 0)

rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure{namespace="default"}[5m])
rate(envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure{namespace="default"}[5m])
```

### Grafanaダッシュボード例

[ファイルプロビジョニング](../observability/04-dashboards.md)で保存します。UID `prometheus`と実`namespace`/`pod`/`cluster_name`ラベルを期待します。ConfigMapだけでは読み込まれません。

```json
{
  "uid": "istio-outlier-detection",
  "title": "Istio Outlier Detection",
  "panels": [
    {
      "id": 1,
      "title": "Ejected Hosts",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"}",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 2,
      "title": "Enforced Ejections per Second",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace=\"default\"}[5m])",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "short"
        }
      }
    },
    {
      "id": 3,
      "title": "Ejected Pool Percentage",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * envoy_cluster_outlier_detection_ejections_active{namespace=\"default\"} / (envoy_cluster_membership_total{namespace=\"default\"} > 0)",
          "legendFormat": "{{pod}} / {{cluster_name}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 16,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### リアルタイム監視

```bash
# Check Envoy statistics
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier

# Key metrics:
# envoy_cluster_outlier_detection_ejections_active: Currently ejected instances
# envoy_cluster_outlier_detection_ejections_enforced_total: Total ejection count
# envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx: Ejections due to 5xx errors
```

### Kialiで確認

```bash
# Access Kiali
istioctl dashboard kiali

# Things to check:
# 1. Graph → Select service → Traffic tab
# 2. Graph health is aggregate telemetry, not every caller proxy’s ejection state
# 3. Check Outlier Detection metrics
```

## トラブルシューティング {#troubleshooting}

### 外れ値検出が動かない

```bash
# 1. Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 2. Check Envoy cluster configuration
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn <service-fqdn> -o json | \
  jq '.[] | .outlierDetection'

# 3. Check Envoy logs
kubectl logs -n <namespace> <pod-name> -c istio-proxy | grep outlier

# 4. Validate control-plane configuration (istiod does not perform per-proxy ejections)
istioctl analyze -n <namespace>
```

### 除外インスタンスが多すぎる

変更前にenforced/detected/overflow、残存容量、実エラー種別を確認します。観測失敗に耐えられるなら連続エラーしきい値を上げます。上限を下げるのは可用性上のトレードオフを明示した場合だけです。`interval`を増やしてもその場の連続エラー除外は遅れません。

```yaml
# DestinationRule trafficPolicy fragment; illustrative values
outlierDetection:
  consecutive5xxErrors: 10
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 30
  minHealthPercent: 0
```

### 正常な上流ホストがない

DBスプリットブレインではありません。準備、検出、経路、エンドポイント健全性、呼び出し元ローカル除外を確認します。`minHealthPercent: 50`は異常先へfail-openする場合がありますが復旧はしません。100%除外カナリアはルートロールバックが必要な場合があります。YAMLやKialiアイコンだけでなく実効endpoint/cluster状態を使います。

### 除外後の復帰が遅い

再除外履歴とEnvoy実効期間上限を確認します。`baseEjectionTime`削減は異常先への再試行を早め得ますが修復ではありません。能動ヘルスチェックは別機能で、このDestinationRuleでは有効になりません。

### 一時エラーによる誤検知

接続失敗とアプリ失敗を区別し、再試行が増幅していないか確認します。5xxは意図した応答の場合もあり、遅い成功応答だけでは遅延外れ値ではありません。範囲を限定して変更設定を検証します。デフォルトログに外れ値イベントがあるとは限りません。

## ベストプラクティス

### 1. サービス種別ごとの設定

```yaml
# Critical service (fast detection)
outlierDetection:
  consecutive5xxErrors: 3
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50

# General service
---
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 60s
  maxEjectionPercent: 30

# Stable service (lenient settings)
---
outlierDetection:
  consecutive5xxErrors: 10
  interval: 60s
  baseEjectionTime: 120s
  maxEjectionPercent: 20
```

### 2. 必要時に接続プールと併用

```yaml
# Independent limits; size against measured caller/endpoint capacity
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
  outlierDetection:
    consecutive5xxErrors: 5
    interval: 30s
```

### 3. パニック動作を意図的に選ぶ

`minHealthPercent: 0`がIstioデフォルトで、異常ホストのパニックしきい値を無効にします。非ゼロは可用性と分離のトレードオフを許し、一部ホストの健全性を保証しません。接続プールブレーカーと外れ値検出は独立制御です。

### 4. 段階的ロールアウト

基準を収集し、実効mesh/namespace/workloadポリシーを確認して、隔離テスト群へ測定設定を適用し検証後に拡大します。`maxEjectionPercent: 0`を監視専用スイッチにしないでください。[Istio1.31実装](https://github.com/istio/istio/blob/1.31.0/pilot/pkg/networking/core/cluster_traffic_policy.go)では0超だけがEnvoyフィールドを設定するため、0は除外無効でなくEnvoyデフォルトを残します。省略値はメッシュデフォルトを継承する場合もあります。拡大前に実適用イベントと残存先を観察します。

### 5. 監視とアラート

```yaml
# Prometheus Alerting Rule
groups:
- name: istio_outlier_detection
  rules:
  - alert: HighEjectionRate
    expr: rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="default"}[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High outlier ejection rate"
      description: "{{ $labels.cluster_name }} has enforced ejection rate > 0.1 events/s"
```

## 参考資料

- [Istio外れ値検出](https://istio.io/latest/docs/reference/config/networking/destination-rule/#OutlierDetection)
- [Envoy外れ値検出](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier)
- [サーキットブレーカー](https://istio.io/latest/docs/tasks/traffic-management/circuit-breaking/)
