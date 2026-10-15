# レジリエンス クイズ

> **最終更新**: October 12, 2026
>
> **バージョン**: Istio 1.31（Kubernetes 1.32–1.37 をサポート）。
> EKS の互換性についてはインストール章を参照してください。

このクイズでは、Istio のレジリエンス機能についての理解を確認します。

各例は独立しており、名前付きの Service、ラベル、namespace、および sidecar HTTP8080 workload が存在することを前提としています。値は説明用です。オフラインのスキーマ／クエリ検証は、本番／負荷テストではありません。ローカリティの例では、別の `zoneAwareLbSetting` API ではなく `localityLbSetting` を使用します。

## 選択問題（1～5）

### 問題 1: Outlier Detection の基本概念

次のうち、Outlier Detection の主な目的**ではない**ものはどれですか？

A. 異常に動作するインスタンスを自動的に検出する\
B. 設定済みの障害しきい値および排出上限が許す場合、一時的に排出する\
C. 削除されたインスタンスを永続的に削除する\
D. 一時的に排出されたホストを、排出期間後に再び適格にする

<details>

<summary>回答を表示</summary>

**回答: C**

Outlier Detection は**インスタンスを削除せず**、トラフィックプールから一時的に除外します。

**解説:**

**Outlier Detection の動作:**


**主な機能:**

1. **自動検出**: 設定された連続する該当 HTTP／トランスポート障害をカウントする
2. **自動排出**: しきい値を超えるとトラフィックプールから一時的に除外する
3. **再参加**: 排出は期限切れになります。これはアクティブプローブを送信したり、復旧を証明したりするものではありません
4. **一時的な対策**: インスタンスを削除せず、トラフィックのみを遮断する

**選択肢 C が誤りである理由:**

* Outlier Detection は Circuit Breaker パターンです
* インスタンスを削除せずに**一時的に排出**します
* 後続の成功トラフィックが復旧を確認します。繰り返される障害はより長い排出を引き起こす可能性があります

**参照:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 問題 2: Rate Limiting の種類の比較

Local Rate Limiting と Global Rate Limiting を正しく比較している記述はどれですか？

A. Local Rate Limiting は精度が高い\
B. Global Rate Limiting はパフォーマンスが速い\
C. Local Rate Limiting は各 Envoy proxy で独立してリクエストを制限する\
D. Global Rate Limiting は外部サービスなしで動作する

<details>

<summary>回答を表示</summary>

**回答: C**

Local Rate Limiting は**各 Envoy proxy で独立して**リクエストを制限します。

**解説:**

**Local Rate Limiting と Global Rate Limiting の比較:**

| 特性  | Local Rate Limiting | Global Rate Limiting             |
| --------------- | ------------------- | -------------------------------- |
| **クォータ範囲** | ローカルに設定されたバケット | 共有ドメイン／descriptor とウィンドウ |
| **パフォーマンス** | 非常に高速           | やや低速                  |
| **複雑さ**  | 低                 | 高（外部サービスが必要） |
| **ユースケース**    | 一般的な保護  | 正確な制限が必要な場合  |

**Local Rate Limiting の特性:**

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

表示したバケットは100 token で開始し、10/s で補充されます。3 replica では、適切な負荷分散の下で個別のバースト許容量を持ち、合計で約30/s を維持できます。これは共有された30/s の上限ではありません。

**Global Rate Limiting の特性:**

```yaml
# Configured shared descriptor quota:100 per backend second-window
# Actual enforcement depends on the shared backend, window and failure policy
# Requires an actual gRPC rate-limit service plus shared counter storage such as Redis
```

**Token Bucket アルゴリズム:**

![トークンバケット rate limiter のワークフロー: 上限 100 token のバケットが毎秒 10 token 補充され、到着した各リクエストは token を 1 つ消費して許可されるか、残りがない場合は HTTP 429 で拒否されます。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-resilience-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-resilience-1.html)

**参照:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

### 問題 3: Zone Aware Routing の利点

Zone Aware Routing を使用する利点**ではない**ものはどれですか？

A. 同一 AZ 間通信によるレイテンシの削減\
B. AZ 間データ転送コストの削減\
C. すべての Service replica を 1 つの AZ に配置することによる可用性の保証された向上\
D. 適切なポリシーと容量がある場合、到達可能で正常な endpoint へのフェイルオーバー

<details>

<summary>回答を表示</summary>

**回答: C**

C は保証ではありません。ローカリティは各呼び出し元に対して相対的であり、呼び出し元のトラフィックをローカル zone に集中させることがあります。すべての replica を 1 つの AZ に移動すると、共有障害ドメインが作られ、その zone に負荷が集中する可能性があります。

**解説:**

**Zone Aware Routing の正しい動作:**


**Zone Aware Routing の実際の利点:**

同一 zone へのルーティングは、レイテンシのネットワーク部分と課金対象の zone 間バイト数を削減できますが、正確なレイテンシ／価格／削減額はデプロイメントに依存します。Weighted80/10/10 では、通常トラフィックは正常な 3 つの zone すべてに送信されます。10% の部分は待機フェイルオーバーではありません。他の zone には、実際に到達可能な endpoint と予備容量が必要です。

**DestinationRule の設定例:**

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

**参照:**

* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)

</details>

***

### 問題 4: Outlier Detection のパラメータ

次の Outlier Detection 設定でインスタンスを排出する条件は何ですか？

```yaml
outlierDetection:
  consecutive5xxErrors: 5
  interval: 30s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

A. エラーが 5 秒間発生したとき\
B. 連続する該当 5xx 障害が 5 回になりしきい値に達したとき（排出上限の対象）\
C. 30 秒間のエラー率が 50% を超えたとき\
D. 無条件で 30 秒ごとに排出する

<details>

<summary>回答を表示</summary>

**回答: B**

B はトリガーを示しています。連続する 5 回の該当障害はインラインで排出をトリガーできます。`interval` は定期的なスイープ間隔であり、`maxEjectionPercent` により適用が抑止される場合があります。低速な成功レスポンスだけはレイテンシ outlier ではありません。

**解説:**

**主な Outlier Detection パラメータ:**

| パラメータ              | 説明                 | デフォルト | 例の範囲 |
| ---------------------- | --------------------------- | ------- | ----------- |
| **consecutive5xxErrors**  | 連続エラーしきい値 | 5       | 3-10        |
| **interval**           | 分析間隔           | 10s     | 10s-60s     |
| **baseEjectionTime**   | 最小排出時間       | 30s     | 30s-300s    |
| **maxEjectionPercent** | 最大排出割合      | 10%     | 10%-50%     |

**パラメータの詳細説明:**

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

**完全な DestinationRule の例:**

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

成功は該当する連続シーケンスをリセットします。ホストがしきい値に達した場合、上限が許せば排出できます。実際の排出期間の後で再び適格になります。繰り返しの排出は Envoy の multiplier/cap により期間を長くします。`minHealthPercent` は panic/fail-open のしきい値であり、正常な Pod の割合を保証するものではありません。0 はこのしきい値を無効にします。

**参照:**

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)

</details>

***

### 問題 5: Token Bucket アルゴリズム

リクエストあたり 1 token、かつ継続的な需要の場合、初期バースト後の長期的な補充制限による許可レートは何ですか？

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

<summary>回答を表示</summary>

**回答: A**

`tokens_per_fill: 10` および `fill_interval: 1s` では、**毎秒 10 token が追加**されるため、平均は **10 req/s** です。

**解説:**

**Token Bucket アルゴリズムのパラメータ:**

* **max\_tokens**: バケットに保存できる最大 token 数（バースト許容量）
* **tokens\_per\_fill**: fill\_interval ごとに追加する token 数（**平均スループット**）
* **fill\_interval**: token の追加間隔

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

**実践的な設定例:**

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

**完全な EnvoyFilter の例:**

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

**参照:**

* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)

</details>

***

## 記述問題（6～10）

### 問題 6: Outlier Detection の実装

本番環境で稼働する `product-service` が断続的に低速化し、timeout が発生しています。問題のあるインスタンスを自動的に排出するために Outlier Detection を実装したいと考えています。次の要件を満たす DestinationRule を作成してください。

**要件:**

* 連続 3 回のエラー後に排出する
* 20 秒の定期スイープを使用する。連続障害はインラインで検出できる
* 初期 base ejection duration を 60 秒に設定する
* 最大 30% の排出を許可する
* 502、503、504 の gateway error も検出する

<details>

<summary>回答を表示</summary>

低速なレスポンスだけは outlier の基準ではありません。この例では HTTP エラーとローカルで観測されたトランスポート障害を分けています。timeout を観測するには、実際の route/client timeout が必要です。

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

Gateway の 502/503/504 サブセットはすでに 5xx に含まれます。3 という同じしきい値は冗長ですが有効です。より低い gateway しきい値では、そのサブセットでより早く排出されます。`interval: 20s` は連続エラーの検出を遅らせません。`baseEjectionTime: 60s` は初期の最小期間であり、アクティブなヘルスプローブではありません。30% の上限は排出を制限しますが、残りの endpoint を正常に保つことはできません。`minHealthPercent: 70` はしきい値未満で panic 動作を有効にしますが、70% の正常容量を維持するものではありません。サポートされない `enforcing*` フィールドは Envoy の内部要素であり、この DestinationRule API のものではありません。

10 host の例では、3 回の排出後に上限に達する可能性がありますが、検出されたプールサイズ、丸め、および現在の正常性が重要です。実際に適用／検出／overflow された counter を確認してください。復帰した host は、復旧を示すために成功トラフィックを受け取る必要があります。

```bash
istioctl proxy-config clusters <caller-pod> -n production --fqdn product-service.production.svc.cluster.local -o json
istioctl x envoy-stats <caller-pod> -n production --output prom | grep outlier_detection
```

```promql
envoy_cluster_outlier_detection_ejections_active{namespace="production"}
rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m])
```

[outlier 章](../../../service-mesh/istio/resilience/01-outlier-detection.md)の説明に従い、オプションの統計／scraping を有効にします。しきい値は測定したエラーと予備容量から調整してください。普遍的な「本番」値はありません。

</details>

***

### 問題 7: Local Rate Limiting の適用

sidecar が注入された `api-gateway` というアプリケーションが過剰な HTTP トラフィックを受けています。各 Envoy proxy を毎秒 50 リクエスト、最大 200 のバーストに制限する Local Rate Limiting を適用したいと考えています。EnvoyFilter を作成してください。

追加要件:

* rate limit が適用されたときに `X-RateLimit-Limit` header を追加する
* 429 レスポンスに `Retry-After: 1` header を含める

<details>

<summary>回答を表示</summary>

`api-gateway` は、`production` の HTTP8080 上に注入された sidecar を持つアプリケーションであると仮定します。これは選択した HTTP リクエストが Envoy に到達した後に保護します。完全な DDoS または connection/TLS 保護ではありません。実際の Istio ingress gateway では、rate-limit 章にあるように、その namespace/selector と `GATEWAY` context を使用してください。

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

満杯のバケットは直ちに最大 200 リクエストを許可し、その後は 50 token/s で補充されます。枯渇後に継続して 100 リクエスト/s の場合、リクエストあたり 1 token で他の制限がないと仮定すると、約 50/s を許可できます。40/s の滑らかな需要は収まる可能性がありますが、40/s という平均だけではすべてのバーストが受け入れられることを保証しません。許可は backend 処理の成功を保証しません。

この filter はデフォルトで HTTP429 を返し、これらの header は強制された rate-limit レスポンスにのみ追加します。通常の 200 レスポンスには、この設定からこれらの header は付与されません。`Retry-After: 1` は助言的な遅延であり、1 秒後の予約や成功の保証ではありません。この例では `tokens_remaining` dynamic metadata は作成されないため、作り物の Remaining header は省いています。

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 50
X-Local-Rate-Limit: true
Retry-After: 1
```

異なる path-prefix バケットには、重複する 2 番目の filter ではなく、次の**代替案**を使用してください。明示的な descriptor generator は Istio1.31 に固定された Envoy API でサポートされます。不一致または欠落した path は、上限付きのデフォルトバケットを使用します。prefix 一致には、指定テキストで始まる長い path も含まれます。

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

オプション統計の収集、global service／Redis の前提条件、および信頼できる identity の処理については、[rate limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)を参照してください。

</details>

***

### 問題 8: Zone Aware Routing の設定

AWS EKS cluster は 3 つの AZ（us-east-1a、us-east-1b、us-east-1c）に分散しています。AZ 間データ転送コストを削減するため、`order-service` に Zone Aware Routing を設定したいと考えています。

**要件:**

* トラフィックの 70% を同一 AZ の pod に送信する
* 他の AZ にはそれぞれ 15% を分配する
* 別の priority-failover の代替案と、AZ 全体の障害の制限を説明する
* minHealthPercent50 が 50% 正常の保証でも、ローカリティの有効化スイッチでもない理由を説明する

<details>

<summary>回答を表示</summary>

これらの要件には weighted distribution、priority failover、および正常な容量の保証が混在しています。これらすべてを 1 つの locality policy のフィールドの組み合わせで表現することはできません。通常の 70/15/15 トラフィックには、次の distribution policy を使用してください。`minHealthPercent` は Pod の半分が正常なときにのみローカリティを有効化するスイッチではありません。

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

代わりにローカル zone の優先度と spillover が必要な場合は、両方の policy ではなく、この**代替案**を適用してください。`localityLbSetting.failover` は `region/zone` path ではなく region 名を受け入れます。この API では `distribute` と priority mode は相互排他的です。

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

zone 全体の障害は、その zone の client にも影響します。別の場所にある存続／再作成済みの client または entry point が必要です。残存する正常 endpoint の容量、検出、connection reuse、およびネットワーク到達可能性がフェイルオーバーを決定します。policy は zoneB への 100% や即時復旧を約束しません。`minHealthPercent: 0` は正常でない host の panic 使用を無効にし、100% の上限ではすべてが障害時にすべての endpoint の排出を許可します。どちらも正常な容量を生み出しません。

Node→Pod のトポロジーチェック、一致する topologySpreadConstraints、EKS node group、および EDS 診断については、[zone-aware 章](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)を使用してください。例に一致させる目的だけで cloud topology label を手動で割り当てないでください。標準の Istio metrics には `source_cluster_zone`／`destination_cluster_zone` は含まれません。zone クエリには、ルーティングとは別に検証済みの enrichment が必要です。

**説明用のコスト計算**: decimal の 1TB=1000GB、課金対象 GB あたりの実効料金 $0.01、baseline の zone 間割合 2/3、変更後の割合 0.30 と仮定します。これは簡略化した仮定であり、AWS の価格見積、測定した削減額、または完全なネットワーク請求額ではありません。

| 月間トラフィック | 変更前 | 変更後 | 月間削減額 | 年間削減額 |
|---|---:|---:|---:|---:|
|1TB|$6.67|$3.00|$3.67|$44.00|
|100TB|$666.67|$300.00|$366.67|$4,400.00|

モデル上の削減率は 55% です。正確な割合から計算し、表示する通貨のみを丸めてください。年間削減額は、早まって丸めた月間 $367 を掛けてはなりません。実際の課金対象方向、バイト量、region、および Service 処理料金には、請求／flow の証拠が必要です。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
istioctl proxy-config bootstrap <caller-pod> -n production -o json
istioctl proxy-config all <caller-pod> -n production -o json
```

</details>

***

### 問題 9: 複合レジリエンス戦略

`payment-service` は外部 payment API を呼び出す重要な Service です。次の複合レジリエンス戦略を実装してください。

1. **Outlier Detection**: 連続 3 回のエラー後にインスタンスを排出する
2. **Retry**: 検証済みの冪等な読み取りで 502/503/504 に対して最大 3 回の retry を許可し、書き込みの retry は明示的に無効にする
3. **Timeout**: リクエストあたり 5 秒の timeout
4. **Circuit Breaker**: 「エラーが 50% を超えたら Service 全体を遮断する」がこの API の pool breaker ではない理由を説明し、代わりにサポートされる concurrency limit を示す

DestinationRule と VirtualService を作成してください。

<details>

<summary>回答を表示</summary>

DestinationRule は、列挙した success-rate フィールドを通じて「この Service をグローバルに 50% を超えるエラーで遮断する」ことを実装できません。これらのフィールドはここではサポートされず、統計的偏差も固定エラー率のしきい値ではありません。pool circuit breaker は、各 caller proxy の upstream cluster における同時 connection/request を制約します。outlier detection は host の適格性を変更します。協調した Service 全体の error-ratio breaker には、別途設計された application/controller の仕組みが必要です。

この回答は **caller→payment-service HTTP8080** に適用されます。Service の送信 payment API 呼び出しには、[outlier 章](../../../service-mesh/istio/resilience/01-outlier-detection.md)で説明されている独自の destination policy と TLS の可視性が必要です。Mesh retry は payment の冪等性を提供できません。

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

明示的な書き込み／fallback rule は、継承した Mesh retry を無効にします。application semantics 上、繰り返しても安全な一致済みの読み取りだけを retry してください。`gateway-error` は 502/503/504 を対象にします。広範な reset/5xx/4xx 条件は payment の書き込みに追加しません。トランスポートエラーでは、payment が確定したかどうかは分かりません。

`attempts: 3` は、初回試行**後に**最大 3 回 retry することを意味します。完全な 2s の試行 4 回に backoff を加えると 5s には収まらないため、合計 route budget により早く停止します。application deadline は upload/streaming と downstream 作業もカバーする必要があります。これは正確な障害タイムラインや、特定の最終 HTTP status の約束ではありません。

`maxRetries: 3` は、その proxy/cluster の同時に未完了な retry を制限するものであり、リクエストごとの retry 数ではありません。`http2MaxRequests` は HTTP/1.1 にも適用されます。`maxRequestsPerConnection: 0` は、その request-count 上限なしの reuse を許可します。pending/active request の overflow は HTTP request を拒否できますが、connection-limit に 1 回達した場合は最初に queue が発生することがあります。これらの設定はどれもグローバルな 50% エラー circuit ではありません。

| 観測 | 正しい解釈 |
|---|---|
|安全な読み取りが 502 を受けた後、retry で成功する|retry は役立つ場合があります。host を再訪する可能性があり、成功は保証されません|
|host が障害しきい値に達する|上限が許す場合、その caller は排出できます。他の caller は独自の状態を維持します|
|すべての endpoint が障害になる|正常な destination が残らない場合があります。排出 timer は Service を修復せず、協調した half-open test を実装しません|

```promql
sum(rate(envoy_cluster_upstream_rq_retry{namespace="production"}[5m]))
envoy_cluster_circuit_breakers_default_rq_pending_open{namespace="production"}
sum(rate(envoy_cluster_outlier_detection_ejections_enforced_total{namespace="production"}[5m]))
sum(rate(istio_requests_total{reporter="source",destination_service_name="payment-service",destination_service_namespace="production",response_flags=~".*UT.*"}[5m]))
```

`_open` series は 0/1 gauge であり、`rate` に渡す counter ではありません。Envoy cluster label を scope し、関連する統計を有効にしてください。安全な運用上のトレードオフについては、[retry/timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)および [circuit breaking](../../../service-mesh/istio/traffic-management/07-circuit-breaker.md)を参照してください。

</details>

***

### 問題 10: パフォーマンス最適化とコスト削減

大規模な microservices 環境で、月間ネットワークコストは $5,000 です。Istio のレジリエンス機能を使用してパフォーマンスを最適化し、コストを削減する包括的な戦略を策定してください。

**現在の状況:**

* 3 つの AZ に均等に分散された 100 Service
* 月間トラフィック: 500TB
* 平均レスポンス時間: 150ms
* エラー率: 3%

**目標:**

* AZ 間コストを 50% 削減
* 平均レスポンス時間を 100ms 未満にする
* エラー率を 1% 未満にする

<details>

<summary>回答を表示</summary>

与えられた 100 Service、500TB/月、$5,000 の請求額、150ms のレイテンシ、および 3% のエラーを、この監査で測定した結果ではなく**仮説上の baseline**として扱います。まず課金対象トラフィックの構成要素と、ユーザー向け SLI の境界を特定してください。proxy hop のレイテンシは自動的に end-to-end request のレイテンシにはなりません。

**1. レビュー済み Service ごとに 1 つの destination policy に統合する**

代表的な `api-service` の例は、pool limit、locality weighting、およびサポートされる outlier detection を 1 つの DestinationRule に組み合わせます。複数の競合する wildcard rule を適用したり、すべての Service を 1 つの汎用 backend に route したりしないでください。値は caller と destination ごとにサイズ設定してください。このサンプルは本番のデフォルトではありません。

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

**2. 測定された admission control としての rate limit**

これらは `production` の HTTP8080 における、proxy ごとに独立した bucket です。tier label と容量を検証してください。「critical」label だけでは特定の rate を正当化しません。これらは共有された Service/account quota を課すものでも、edge 保護を置き換えるものでもありません。

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

**3. 説明用モデルと実際の請求額を分離する**

decimal の 500TB=500,000GB、baseline の AZ 間割合 2/3、変更後の割合 0.20、および課金対象 GB あたりの**想定実効**料金 $0.015 と仮定します。モデル化された変動要素は次のとおりです。

| モデル | 計算 | 月額 |
|---|---|---:|
|変更前|500,000 × 2/3 × 0.015|$5,000|
|変更後|500,000 × 0.20 × 0.015|$1,500|
|差額|5,000 − 1,500|$3,500 (70%)|

この結果が $5,000 の baseline 全体に一致するのは、請求額全体がこの変動要素である場合のみです。実際のネットワーク請求には、他の方向、load-balancer/NAT 処理、インターネット／region 転送、および固定コストが含まれる場合があります。request と response のサイズが異なる場合、request の重みは必ずしも byte の割合と一致しません。モデル化した削減を、課金対象 flow/CUR データと現在の価格に照らして検証してください。請求額全体の 70% 削減を約束してはいけません。

説明用に、1 hop のネットワークレイテンシを同一 AZ では 0.3ms、AZ 間では 1.5ms とします。等しい 3 zone の baseline では 0.3×1/3+1.5×2/3=1.10ms、80/20 では 0.54ms です。この 0.56ms の構成要素の変化では、150ms→100ms の end-to-end 改善を確立できません。実際の critical path、database/pool wait、application の作業、および retry amplification を trace してください。

**4. 段階的な変更を検証する**

| 説明用の段階 | 範囲を拡大する前に必要な証拠 |
|---|---|
|Weeks1–2: topology/locality|実際の Node/Pod/EDS mapping、zone の容量、request と課金対象 byte の分布、障害時の動作|
|Weeks3–4: outlier/pool limit|適用された排出、残存 endpoint、overflow、レイテンシ、および application error の原因|
|Weeks5–6: rate limit|許容できない正当リクエストの拒否なしに、真の過負荷が拒否されること。client retry の動作を観測する|

このスケジュールは説明用です。変更ごとに rollback/stop の基準を定義し、測定してください。Outlier detection は容量を除外したり、根本的な障害を表面化させたりする可能性があります。エラーが 1% 未満になることを保証するものではありません。timeout を変更すると、作業を速くする代わりに障害を増やすことがあります。

**5. 正しく型付けされ scope された metrics を使用する**

次の Service ごとのクエリは、代表的な Service を診断します。ユーザー向け SLI は別に測定してください。平均レイテンシには P50 ではなく histogram sum/count を使用します。active ejection は gauge であり、enforced ejection event は counter です。

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

オプション統計を有効にし、トラフィックなし／scrape 障害を扱ってください。AZ 間クエリには実際の zone enrichment が必要です。`source_cluster_zone!=destination_cluster_zone` は有効な PromQL ではありません。明示的に scope された条件付きクエリについては、[zone 章](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)を参照してください。

**目標は引き続き測定対象です**: AZ 間コスト−50%、平均ユーザー向けレイテンシ≤100ms、エラー<1% は予測結果ではなく受け入れ基準です。cache の配置は距離を減らせますが、それ自体で hit ratio を高めるものではありません。overhead を比較する前に ambient の機能／容量要件を評価してください。一般的な 30–50% の削減は確立されていません。multi-zone Deployment 上の 1 つの HPA は、各 zone を独立して scale しません。独立した zone ごとの scaling には、明示的な workload/controller 設計が必要です。

参照: [Outlier detection](../../../service-mesh/istio/resilience/01-outlier-detection.md), [rate limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md), [EKS network cost optimization](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html).

</details>

***

## スコア計算

* 選択問題 1～5: 各 10 点（合計 50 点）
* 記述問題 6～10: 各 10 点（合計 50 点）
* **合計: 100 点**

**評価基準:**

* 90～100 点: 優秀（Istio レジリエンス エキスパート）
* 80～89 点: 十分な理解。デプロイメント検証は別途必要
* 70～79 点: 平均（追加学習を推奨）
* 60～69 点: 平均未満（基本概念の復習が必要）
* 0～59 点: 再学習が必要

## 学習リソース

* [Outlier Detection](../../../service-mesh/istio/resilience/01-outlier-detection.md)
* [Rate Limiting](../../../service-mesh/istio/resilience/02-rate-limiting.md)
* [Zone Aware Routing](../../../service-mesh/istio/resilience/03-zone-aware-routing.md)
