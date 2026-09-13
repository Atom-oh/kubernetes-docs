# 耐障害性クイズ

> **最終更新**: September 11, 2026 · Istio1.31 · Kubernetes1.32–1.36。EKS互換性はインストールの章を参照してください。

このクイズはIstioの耐障害性機能の理解を確認します。

各例は独立し、指定Service、ラベル、名前空間、サイドカー付きHTTP8080ワークロードが存在する前提です。値は例示です。オフラインスキーマ/クエリ確認は本番/負荷テストではありません。ローカリティ例は別の`zoneAwareLbSetting` APIでなく`localityLbSetting`を使います。

## 選択問題（1-5）

### 問1: 外れ値検出の基本概念

外れ値検出の主な目的**ではない**ものはどれですか？

A. 異常動作するインスタンスを自動検出\
B. 設定失敗しきい値と除外上限が許す場合に一時除外\
C. 除外インスタンスを永久削除\
D. 除外期間後、一時除外したホストを再び選択可能にする

<details>

<summary>解答を表示</summary>

**正解: C**

外れ値検出は**インスタンスを削除せず**、通信対象プールから一時的に外します。

**解説:**

**外れ値検出の動作:**


**主な機能:**

1. **自動検出**: 設定された対象HTTP/転送失敗の連続数を計数
2. **自動除外**: しきい値超過時に通信対象プールから一時除外
3. **復帰**: 除外が期限切れになる。能動プローブの送信や復旧の証明はしない
4. **一時措置**: インスタンスを削除せず通信だけを遮断

**選択肢Cが誤りの理由:**

* 外れ値検出はサーキットブレーカーパターン
* インスタンスを削除せず**一時的に除外**する
* その後の通信成功で復旧を確認する。失敗が続くと除外が長くなる場合がある

**参考資料:**

* [外れ値検出](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 問2: レート制限タイプの比較

ローカルレート制限とグローバルレート制限を正しく比較したものはどれですか？

A. ローカルレート制限の方が精度が高い\
B. グローバルレート制限の方が速い\
C. ローカルレート制限は各Envoyプロキシで独立して要求を制限する\
D. グローバルレート制限は外部サービスなしで動く

<details>

<summary>解答を表示</summary>

**正解: C**

ローカルレート制限は**各Envoyプロキシで独立して**要求を制限します。

**解説:**

**ローカルとグローバルのレート制限比較:**

| 特性 | ローカルレート制限 | グローバルレート制限 |
| --------------- | ------------------- | -------------------------------- |
| **クォータ範囲** | ローカル設定バケット | 共有domain/descriptorと時間窓 |
| **性能** | 非常に速い | やや遅い |
| **複雑さ** | 低い | 高い（外部サービスが必要） |
| **用途** | 一般的保護 | 厳密な制限が必要な場合 |

**ローカルレート制限の特性:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

図のバケットは100トークンで開始し、10/sで補充します。適切な負荷分散下で3レプリカはそれぞれのバースト枠を持ち、合計約30/sを維持できますが、共有30/s上限ではありません。

**グローバルレート制限の特性:**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**トークンバケットアルゴリズム:**

![上限100トークンのバケットを毎秒10トークン補充し、到着要求は1トークン消費で許可、残数0ならHTTP 429で拒否するトークンバケット型レート制限の流れ。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**参考資料:**

* [レート制限](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 問3: ゾーンを考慮したルーティングの利点

ゾーンを考慮したルーティングの利点**ではない**ものはどれですか？

A. 同一AZ通信によるレイテンシー削減\
B. AZ間データ転送料の節約\
C. 全サービスレプリカを1 AZに置くことによる可用性向上の保証\
D. 適切なポリシーと容量がある場合、到達可能で正常なエンドポイントへフェイルオーバー

<details>

<summary>解答を表示</summary>

**正解: C**

Cは保証ではありません。ローカリティは各呼び出し元からの相対的なもので、その通信をローカルゾーンに集中させ得ます。全レプリカを1 AZに移すと共通障害ドメインができ、そのゾーンが過負荷になる場合があります。

**解説:**

**ゾーンを考慮したルーティングの正しい動作:**


**実際の利点:**

同一ゾーンルーティングはレイテンシーのネットワーク成分と課金対象AZ間バイトを減らせますが、正確な遅延/料金/節約はデプロイに依存します。重み80/10/10は通常通信を正常な全3ゾーンへ送り、10%部分は待機フェイルオーバーではありません。他ゾーンには実際に到達可能なエンドポイントと予備容量が必要です。

**DestinationRule設定例:**

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

**参考資料:**

* [ゾーンを考慮したルーティング](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 問4: 外れ値検出パラメーター

次の外れ値検出設定でインスタンスが除外される条件は何ですか？

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. 5秒間エラーが発生した場合\
B. 対象5xx失敗が5回連続し、除外上限の範囲内でしきい値に達した場合\
C. 30秒間のエラー率が50%超の場合\
D. 30秒ごとに無条件除外

<details>

<summary>解答を表示</summary>

**正解: B**

Bがトリガーです。対象失敗5回連続で即時に除外を引き起こし得ます。`interval`は定期走査間隔で、`maxEjectionPercent`が適用を防ぐ場合があります。遅い成功応答だけではレイテンシー外れ値にはなりません。

**解説:**

**主な外れ値検出パラメーター:**

| パラメーター | 説明 | デフォルト | 範囲例 |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors** | 連続エラーしきい値 | 5 | 3-10 |
| **interval** | 分析間隔 | 10s | 10s-60s |
| **baseEjectionTime** | 最小除外時間 | 30s | 30s-300s |
| **maxEjectionPercent** | 最大除外割合 | 10% | 10%-50% |

**パラメーターの詳細:**

**consecutive5xxErrors**

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

**interval**

```yaml
# Fast detection (high load)
interval: 10s

# Typical case
---
interval: 30s

# Stable service
---
interval: 60s
```

**baseEjectionTime**

```yaml
# Quick recovery attempt
baseEjectionTime: 30s

# Typical case
---
baseEjectionTime: 60s

# Cautious recovery
---
baseEjectionTime: 300s
```

**maxEjectionPercent**

```yaml
# Conservative (stability priority)
maxEjectionPercent: 10

# Balanced setting
---
maxEjectionPercent: 30

# Aggressive (performance priority)
---
maxEjectionPercent: 50
```

**完全なDestinationRule例:**

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

**動作例:**

成功は該当する連続失敗列をリセットします。ホストがしきい値に達すると、上限が許せば除外され、実際の除外期間後に再選択可能になります。再除外ではEnvoyの倍率/上限によって期間が増えます。`minHealthPercent`はパニック/fail-openしきい値で、正常Pod割合の保証ではありません。0はそのしきい値を無効にします。

**参考資料:**

* [外れ値検出](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 問5: トークンバケットアルゴリズム

1要求1トークン、需要が継続する場合、初期バースト後の補充量に制約される長期的な受け入れレートは何ですか？

```yaml
token_bucket:
  max_tokens: 100
  tokens_per_fill: 10
  fill_interval: 1s
```

A. 10 req/s\
B. 100 req/s\
C. 110 req/s\
D. 1000 req/s

<details>

<summary>解答を表示</summary>

**正解: A**

`tokens_per_fill: 10`と`fill_interval: 1s`なら**毎秒10トークンが追加**され、平均は**10 req/s**です。

**解説:**

**トークンバケットのパラメーター:**

* **max\_tokens**: バケットに保存できる最大トークン数（バースト枠）
* **tokens\_per\_fill**: fill\_intervalごとに追加するトークン数（**平均スループット**）
* **fill\_interval**: トークン追加間隔

**計算方法:**

```
Average request rate = tokens_per_fill / fill_interval
                     = 10 / 1s
                     = 10 req/s

Burst throughput = max_tokens
                 = 100 req (for a brief moment)
```

**時間経過に伴う動作:**

```
T=0: 100 tokens in bucket (initial state)
     Can admit up to100 immediate requests if the bucket is full; backend concurrency is separate

T=0.1s: Bucket empty (0 tokens)
        Additional requests rejected

T=1s: 10 tokens added (Refill)
      Can handle 10 requests

T=2s: 10 tokens added
      Can handle 10 requests

Average: 10 req/s (sustainable throughput)
Burst allowance:100 requests from a full bucket, not a sustained req/s rate
```

**実用的な設定例:**

```yaml
# Scenario 1: General API endpoint
token_bucket:
  max_tokens: 100        # Allow burst of 100
  tokens_per_fill: 10    # Average 10 req/s
  fill_interval: 1s

# Scenario 2: High-performance API
---
token_bucket:
  max_tokens: 1000       # Allow burst of 1000
  tokens_per_fill: 100   # Average 100 req/s
  fill_interval: 1s

# Scenario 3: Limited resource
---
token_bucket:
  max_tokens: 10         # Only 10 burst
  tokens_per_fill: 1     # Average 1 req/s
  fill_interval: 1s
```

**完全なEnvoyFilter例:**

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**参考資料:**

* [レート制限](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 短答問題（6-10）

### 問6: 外れ値検出の実装

本番の`product-service`が断続的に遅くなり、タイムアウトしています。外れ値検出で問題インスタンスを自動除外したいと考えています。次の要件を満たすDestinationRuleを書いてください。

**要件:**

* 3回連続エラー後に除外
* 定期走査は20秒。連続失敗はその場で検出可能
* 初期の基本除外期間は60秒
* 最大30%の除外を許可
* 502、503、504ゲートウェイエラーも検出

<details>

<summary>解答を表示</summary>

遅い応答だけでは外れ値基準になりません。例はHTTPエラーとローカル観測の転送失敗を分離します。タイムアウトを観測するには実ルート/クライアントのタイムアウトが必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-service-outlier
  namespace: production
spec:
  host: product-service
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 20s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 3
```

ゲートウェイの部分集合502/503/504はすでに5xxに含まれます。同じしきい値3は冗長ですが有効です。ゲートウェイしきい値を低くするとその部分集合で早く除外します。`interval: 20s`は連続エラー検出を遅らせません。`baseEjectionTime: 60s`は初期最小期間で、能動ヘルスプローブではありません。30%上限は除外を制限しますが、残るエンドポイントを正常に保つことはできません。`minHealthPercent: 70`はしきい値未満でパニック動作を有効にし、70%の正常容量を維持するものではありません。未対応`enforcing*`フィールドはEnvoy内部であり、このDestinationRule APIではありません。

10ホストの例は3除外で上限に達し得ますが、検出プール数、丸め、現健全性が関係します。実際のenforced/detected/overflowカウンターを調べます。復帰ホストは通信が成功して初めて復旧を示せます。

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

[外れ値検出の章](../../../service-mesh/istio/resilience/01-outlier-detection.md)に従って任意の統計/スクレイプを有効にします。実測エラーと予備容量からしきい値を調整します。普遍的な「本番」値を意味しません。

</details>

***

### 問7: ローカルレート制限の適用

サイドカーを注入した`api-gateway`というアプリが過剰なHTTP通信を受けています。Envoyプロキシごとに毎秒50要求、最大200のバーストに制限するローカルレート制限を適用したいと考えています。EnvoyFilterを書いてください。

追加要件:

* レート制限時に`X-RateLimit-Limit`ヘッダーを追加
* 429応答に`Retry-After: 1`ヘッダーを含める

<details>

<summary>解答を表示</summary>

`api-gateway`は`production`内のHTTP8080にサイドカーを注入したアプリとします。Envoy到達後の選択HTTP要求を保護し、完全なDDoS対策や接続/TLS保護ではありません。実際のIstio Ingress Gatewayでは、レート制限章のようにその名前空間/セレクターと`GATEWAY`コンテキストを使います。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: api-gateway-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          response_headers_to_add:
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-RateLimit-Limit
              value: '50'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: X-Local-Rate-Limit
              value: 'true'
          - append_action: OVERWRITE_IF_EXISTS_OR_ADD
            header:
              key: Retry-After
              value: '1'
```

満杯バケットは即座に最大200要求を受け入れ、その後50トークン/sを補充します。枯渇後に100要求/sが続けば、1要求1トークン、他制限なしの前提で約50/sを受け入れられます。平滑な40/s需要は収まりますが、平均40/sだけでは全バーストの受け入れは保証されません。受け入れはバックエンド処理成功を保証しません。

フィルターのデフォルトはHTTP429で、これらのヘッダーは適用したレート制限応答だけに付きます。通常200応答にはこの設定からは付きません。`Retry-After: 1`は推奨待機時間で、予約や1秒後の成功保証ではありません。例は`tokens_remaining`動的メタデータを作らないため、架空のRemainingヘッダーは省略します。

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

パスプレフィックス別バケットには、重複する第2フィルターでなくこの**代替**を使います。明示descriptor生成器はIstio1.31に固定されたEnvoy APIでサポートされます。欠損/不一致パスは制限付きデフォルトバケットを使い、プレフィックス一致は指定文字列で始まる長いパスも含みます。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: path-based-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-gateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 30
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
          always_consume_default_token_bucket: false
          descriptors:
          - entries:
            - key: header_match
              value: /api/login
            token_bucket:
              max_tokens: 30
              tokens_per_fill: 10
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /api/search
            token_bucket:
              max_tokens: 300
              tokens_per_fill: 100
              fill_interval: 1s
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: /api/login
                headers:
                - name: :path
                  string_match:
                    prefix: /api/login
          - actions:
            - header_value_match:
                descriptor_value: /api/search
                headers:
                - name: :path
                  string_match:
                    prefix: /api/search
```

```promql
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

任意統計収集、グローバルサービス/Redis前提条件、信頼するIDの扱いは[レート制限](../../../service-mesh/istio/resilience/02-rate-limiting.md)を参照してください。

</details>

***

### 問8: ゾーンを考慮したルーティングの設定

AWS EKSクラスターが3 AZ（us-east-1a、us-east-1b、us-east-1c）に分散しています。`order-service`にゾーンを考慮したルーティングを設定し、AZ間データ転送料を減らしたいと考えています。

**要件:**

* 70%の通信を同じAZのPodへ送る
* 他のAZへ各15%を分配
* 別の優先順位フェイルオーバー方式とAZ全停止の制約を説明
* minHealthPercent50が50%正常保証でもローカリティ有効化スイッチでもない理由を説明

<details>

<summary>解答を表示</summary>

要件には重み付き分配、優先フェイルオーバー、正常容量保証が混在しています。1つのローカリティポリシーでフィールドを組み合わせても全部は表せません。通常70/15/15通信には次の分配ポリシーを使います。`minHealthPercent`は半数のPodが正常な時だけローカリティを有効にするスイッチではありません。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-locality
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 70
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 70
            us-east-1/us-east-1c/*: 15
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 15
            us-east-1/us-east-1b/*: 15
            us-east-1/us-east-1c/*: 70
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

ローカルゾーン優先と他ゾーンへの流出を使うなら、両ポリシーでなくこの**代替**を適用します。`localityLbSetting.failover`は`region/zone`パスでなくリージョン名を受け入れます。このAPIでは`distribute`と優先モードは排他的です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: order-service-failover
  namespace: production
spec:
  host: order-service
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

AZ全停止はそのゾーンのクライアントにも影響するため、別の場所の生存/再作成クライアントか入口が必要です。残存正常容量、検出、接続再利用、ネットワーク到達性でフェイルオーバーが決まり、ポリシーはzoneBへの100%転送や即時復旧を約束しません。`minHealthPercent: 0`は異常ホストのパニック使用を無効にし、上限100%は全失敗時の全エンドポイント除外を許可します。どちらも正常容量を出現させません。

Node→Podトポロジー確認、対応topologySpreadConstraints、EKSノードグループ、EDS診断は[ゾーン対応の章](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)を使います。例に合わせるためだけにクラウドトポロジーラベルを手動付与しないでください。標準Istioメトリクスに`source_cluster_zone`/`destination_cluster_zone`はありません。ゾーンクエリにはルーティングと別の検証済み付加情報が必要です。

**費用計算例**: 10進1TB=1000GB、課金対象GBあたり実効$0.01、基準AZ間割合2/3、変更後0.30と仮定します。簡略仮定であり、AWS価格の提示、実測節約、完全ネットワーク請求ではありません。

| 月間通信量 | 変更前 | 変更後 | 月間節約 | 年間節約 |
|---|---:|---:|---:|---:|
|1TB|$6.67|$3.00|$3.67|$44.00|
|100TB|$666.67|$300.00|$366.67|$4,400.00|

モデル削減率は55%です。正確な分数から計算し、表示金額だけを丸めます。早く丸めた月額$367を掛けて年間節約にしてはいけません。実課金方向、バイト量、リージョン、サービス処理料には請求/フローの証拠が必要です。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### 問9: 複合的な耐障害性戦略

`payment-service`は外部決済APIを呼ぶ重要サービスです。次の複合戦略を実装してください。

1. **外れ値検出**: 3回連続エラー後にインスタンスを除外
2. **再試行**: 冪等と検証済みの読み取りで502/503/504に最大3再試行を許可し、書き込み再試行を明示無効化
3. **タイムアウト**: 要求ごとに5秒
4. **サーキットブレーカー**: 「エラー50%超でサービス全体を遮断」がこのAPIのプールブレーカーでない理由を説明し、対応する同時実行制限を示す

DestinationRuleとVirtualServiceを書いてください。

<details>

<summary>解答を表示</summary>

DestinationRuleの列挙された成功率フィールドでは「50%超エラーでサービス全体をグローバル遮断」は実装できません。それらのフィールドはここでは未対応で、統計的偏差も固定エラー割合しきい値ではありません。プールのサーキットブレーカーは呼び出し元プロキシの上流クラスターごとに同時接続/要求を制限し、外れ値検出はホストの選択可否を変えます。協調したサービス全体のエラー比率ブレーカーには、別設計のアプリ/コントローラー機構が必要です。

解答は**呼び出し元→payment-service HTTP8080**に適用します。サービスから外部決済APIへの呼び出しには、[外れ値検出の章](../../../service-mesh/istio/resilience/01-outlier-detection.md)のような独自の宛先ポリシーとTLSの可視性が必要です。メッシュ再試行は決済の冪等性を提供できません。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-service-resilience
  namespace: production
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-service-retry
  namespace: production
spec:
  hosts:
  - payment-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 5s
    retries:
      attempts: 0
```

明示write/fallbackルールは継承するメッシュ再試行を無効にします。繰り返して安全なアプリ意味を持つ一致readだけを再試行します。`gateway-error`は502/503/504を対象とし、決済書き込みに広いreset/5xx/4xx条件は加えません。転送エラーでは決済がコミットしたかは分かりません。

`attempts: 3`は最初の試行の**後に**最大3再試行を意味します。2sの完全試行4回とバックオフは5sに収まらないため、ルート全体予算が先に止めます。アプリ期限はアップロード/ストリーミングと下流処理も含める必要があります。正確な失敗タイムラインや特定の最終HTTP状態の約束ではありません。

`maxRetries: 3`はそのプロキシ/クラスターの同時未完了再試行数を制限し、要求ごとの再試行数ではありません。`http2MaxRequests`はHTTP/1.1にも適用されます。`maxRequestsPerConnection: 0`は要求数上限なしの再利用を許可します。保留/アクティブ要求の超過はHTTP要求を拒否し得ますが、接続上限への到達ではまずキュー待ちになる場合があります。いずれも全体50%エラーのブレーカーではありません。

| 観測 | 正しい解釈 |
|---|---|
|安全な読み取りが502後、再試行で成功|再試行が役立つ場合がある。同じホストに再訪する場合もあり、成功保証はない|
|ホストが失敗しきい値に到達|上限が許せばその呼び出し元は除外できる。他の呼び出し元は独自状態を持つ|
|全エンドポイント失敗|正常宛先が残らない場合がある。除外タイマーはサービスを修復せず、協調的半開テストも実装しない|

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

`_open`系列は0/1ゲージで、`rate`に渡すカウンターではありません。Envoyクラスターラベルの範囲を限定し、関連統計を有効化します。安全な運用上のトレードオフは[再試行/タイムアウト](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)と[サーキットブレーカー](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)を参照してください。

</details>

***

### 問10: 性能最適化とコスト削減

大規模マイクロサービス環境で月間ネットワーク費用は$5,000です。Istioの耐障害性機能で性能を最適化し費用を減らす包括的な戦略を作成してください。

**現状:**

* 100サービスを3 AZに均等配置
* 月間通信量: 500TB
* 平均応答時間: 150ms
* エラー率: 3%

**目標:**

* AZ間費用を50%削減
* 平均応答時間100ms未満
* エラー率1%未満

<details>

<summary>解答を表示</summary>

提示された100サービス、500TB/月、$5,000請求、150ms遅延、3%エラーは**仮定の基準**で、この監査の実測結果ではありません。まず課金対象通信の成分と利用者向けSLI境界を特定します。プロキシホップ遅延は自動的にエンドツーエンド要求遅延にはなりません。

**1. レビューしたサービスごとに宛先ポリシーを1つに統合**

代表的`api-service`例はプール制限、ローカリティ重み付け、対応外れ値検出を1つのDestinationRuleにまとめます。競合するワイルドカードルールを複数適用したり、全サービスを汎用バックエンド1つへ送ったりしないでください。各呼び出し元と宛先に応じて値を決めます。サンプルは本番デフォルトではありません。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-resilience
  namespace: production
spec:
  host: api-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 1s
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 0
        maxRetries: 3
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 80
    outlierDetection:
      consecutive5xxErrors: 3
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 3
      interval: 10s
      baseEjectionTime: 60s
      maxEjectionPercent: 30
      minHealthPercent: 0
      consecutiveGatewayErrors: 2
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-routing
  namespace: production
spec:
  hosts:
  - api-service
  http:
  - name: writes-no-retry
    match:
    - method:
        regex: ^(POST|PUT|PATCH|DELETE)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
  - name: idempotent-reads
    match:
    - method:
        regex: ^(GET|HEAD|OPTIONS)$
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: gateway-error,connect-failure,refused-stream
  - name: other-methods-no-retry
    route:
    - destination:
        host: api-service
        port:
          number: 8080
    timeout: 3s
    retries:
      attempts: 0
```

**2. 測定に基づく受け入れ制御としてのレート制限**

これらは`production`のHTTP8080にある独立したプロキシごとのバケットです。tierラベルと容量を確認します。「critical」ラベルだけでは特定レートを正当化できません。共有サービス/アカウントクォータを課したり、エッジ保護を代替したりしません。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: critical-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: critical
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 500
            tokens_per_fill: 100
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
---
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: standard-service-ratelimit
  namespace: production
spec:
  workloadSelector:
    labels:
      tier: standard
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 8080
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 200
            tokens_per_fill: 50
            fill_interval: 1s
          filter_enabled:
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            default_value:
              numerator: 100
              denominator: HUNDRED
```

**3. 例示モデルと実請求を区別**

10進500TB=500,000GB、基準AZ間割合2/3、変更後0.20、課金GBあたり**仮定の実効料金**$0.015とします。モデル化された変動成分は次のとおりです。

| モデル | 計算 | 月額 |
|---|---|---:|
|変更前|500,000 × 2/3 × 0.015|$5,000|
|変更後|500,000 × 0.20 × 0.015|$1,500|
|差|5,000 − 1,500|$3,500（70%）|

請求全体がこの変動成分である場合だけ、基準$5,000全額と一致します。実際には他方向、ロードバランサー/NAT処理、インターネット/リージョン転送、固定費などが含まれ得ます。要求/応答サイズが違えば要求重みとバイト割合は一致しません。課金対象フロー/CURデータと現料金でモデル節約を検証し、総請求70%削減を約束しないでください。

1ホップ遅延を同一AZ 0.3ms、AZ間1.5msと例示すると、均等3ゾーン基準は0.3×1/3+1.5×2/3=1.10ms、80/20は0.54msです。この成分の0.56ms変化では、エンドツーエンド150ms→100ms改善は示せません。実クリティカルパス、DB/プール待ち、アプリ処理、再試行増幅を追跡します。

**4. 段階的変更を検証**

| 例示段階 | 範囲拡大前に必要な証拠 |
|---|---|
|1–2週: トポロジー/ローカリティ|実Node/Pod/EDS対応、ゾーン容量、要求と課金バイト分布、障害動作|
|3–4週: 外れ値/プール制限|適用除外、残存エンドポイント、超過、遅延、アプリエラー原因|
|5–6週: レート制限|許容できない正当要求拒否なしに実過負荷を拒否。クライアント再試行動作を観察|

予定は例です。ロールバック/停止基準を定め、各変更後に測定します。外れ値検出は容量を減らしたり根底の障害を表面化させたりし、1%未満のエラーを保証しません。タイムアウト変更は処理を速めず、失敗を増やす場合があります。

**5. 型と範囲が正しいメトリクスを使う**

以下のサービスごとのクエリは代表サービスを診断します。利用者向けSLIは別途測定します。平均遅延はP50でなくヒストグラムsum/countです。アクティブ除外はゲージ、適用した除外イベントはカウンターです。

```promql
# Per-service mean request duration, milliseconds
sum(rate(istio_request_duration_milliseconds_sum{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m])) /
sum(rate(istio_request_duration_milliseconds_count{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

# Per-service HTTP5xx percentage (define gRPC/application failures separately)
100 * sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{reporter="destination",destination_service_name="api-service",destination_service_namespace="production"}[5m]))

envoy_cluster_outlier_detection_ejections_active{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum by (pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="production"}[5m]))
```

任意統計を有効にし、無通信/スクレイプ失敗を処理します。AZ間クエリには実ゾーン情報の付加が必要で、`source_cluster_zone!=destination_cluster_zone`は有効なPromQLではありません。範囲を明示した条件付きクエリは[ゾーンの章](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)を参照します。

**目標はこれから測定するもの**です。AZ間費用−50%、利用者向け平均遅延≤100ms、エラー<1%は受け入れ基準で、予測結果ではありません。キャッシュ配置は距離を減らせても、それ自体でヒット率を上げません。負荷比較前にambientの機能/容量要件を評価します。一般的30–50%節約は裏付けられていません。複数ゾーンDeployment上の1 HPAは各ゾーンを独立スケールしません。独立ゾーンスケーリングには明示ワークロード/コントローラー設計が必要です。

参考資料: [外れ値検出](../../../service-mesh/istio/resilience/01-outlier-detection.md)、[レート制限](../../../service-mesh/istio/resilience/02-rate-limiting.md)、[EKSネットワーク費用最適化](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)。

</details>

***

## 得点計算

* 選択問題1-5: 各10点（合計50点）
* 短答問題6-10: 各10点（合計50点）
* **合計: 100点**

**評価基準:**

* 90-100点: 優秀（Istio耐障害性の専門家）
* 80-89点: よく理解。デプロイ検証は別
* 70-79点: 平均的（追加学習を推奨）
* 60-69点: 平均未満（基本概念の復習が必要）
* 0-59点: 再学習が必要

## 学習資料

* [外れ値検出](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [レート制限](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [ゾーンを考慮したルーティング](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
