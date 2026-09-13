# レート制限

> **最終更新**: September 11, 2026 · Istio 1.31。独立例です。ワークロード/リスナーごとにローカルポリシーを1つ選びます。サイドカーアプリは`default`のHTTP 8080、Gateway例は`istio-system`の`istio: ingressgateway`を持つ専用Gatewayです。適用前に実ラベル/リスナーを確認してください。デプロイ/負荷テストはしていません。

レート制限は要求レートを制限し、サービスを過負荷から保護し、公平なリソース利用と費用制御を図る機能です。

## 目次

1. [概要](#overview)
2. [レート制限の種類](#rate-limiting-types)
3. [ローカルレート制限](#local-rate-limiting)
4. [グローバルレート制限](#global-rate-limiting)
5. [実践例](#practical-examples)
6. [監視](#monitoring)
7. [トラブルシューティング](#troubleshooting)

## 概要 {#overview}

次のような状況でレート制限が必要です。

![3クライアントの通信をトークンバケットで制限し、許可要求を2サービスPodへ転送、超過を429で拒否する図。](../../../.gitbook/assets/en-service-mesh-istio-resilience-02-rate-limiting-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-02-rate-limiting-0.html)

### レート制限の目的

1. **サービス保護**: 過負荷防止
2. **公平性**: 意図的なdescriptor/IDモデルが必要。共有バケットだけではクライアント別公平性にならない。
3. **費用制御**: 外部API呼び出し費用の管理
4. **不正利用の削減**: 選択HTTP要求を制限。エッジ/DDoS保護の代わりや接続/TLS枯渇防止にはならない。

## レート制限の種類 {#rate-limiting-types}

### 1. ローカルレート制限

**特性**:
- Envoyごとに独立制限
- 高速応答（追加ネットワーク呼び出しなし）
- 分散環境では上限はインスタンスごとに適用

```yaml
# 100 req/s limit per pod
# Three independently configured buckets can sustain roughly 300 req/s in aggregate,
# subject to traffic distribution; each bucket also has its own burst allowance.
```

### 2. グローバルレート制限

**特性**:
- 中央レート制限サーバーを使用
- 定義domain/descriptorと時間窓の共有カウンター。backend/障害動作が重要
- 若干の遅延（外部サービス呼び出し）

```yaml
# Shared descriptor quota:100 per backend second-window
# Replicas must use the same counter; test window boundaries and backend failures.
```

### 比較

| 特性 | ローカルレート制限 | グローバルレート制限 |
|----------------|---------------------|----------------------|
| **クォータ範囲** | 設定ローカルバケットごと | 共有domain/descriptor |
| **性能** | 非常に速い | やや遅い |
| **複雑さ** | 低い | 高い（外部サービスが必要） |
| **用途** | 一般的保護 | 厳密な制限が必要な場合 |

## ローカルレート制限 {#local-rate-limiting}

### トークンバケットアルゴリズム

![毎秒バケットにトークンを補充し、到着要求にトークンがあれば1つ消費して許可し、なければ429で拒否する流れ。](../../../.gitbook/assets/en-service-mesh-istio-resilience-02-rate-limiting-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-02-rate-limiting-1.html)

### 基本設定

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
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
        portNumber: 8080
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
          response_headers_to_add:
          - header:
              key: x-local-rate-limit
              value: 'true'
            append_action: OVERWRITE_IF_EXISTS_OR_ADD
```

**主なパラメーター**:
- `max_tokens`: バケットの最大保持トークン（バースト許可）
- `tokens_per_fill`: fill_intervalごとの追加トークン
- `fill_interval`: トークン追加間隔

**例**:
```yaml
# 10 requests per second, 100 burst allowed
token_bucket:
  max_tokens: 100
  tokens_per_fill: 10
  fill_interval: 1s

# Result:
# - Average: 10 req/s
# - Burst: up to100 immediately available tokens, not a second sustained rate
```

### パスベースのレート制限

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: path-based-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
        portNumber: 8080
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          descriptors:
          - entries:
            - key: header_match
              value: /api/v1/users
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 100
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /api/v1/admin
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
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          always_consume_default_token_bucket: false
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: /api/v1/users
                headers:
                - name: :path
                  string_match:
                    prefix: /api/v1/users
          - actions:
            - header_value_match:
                descriptor_value: /api/v1/admin
                headers:
                - name: :path
                  string_match:
                    prefix: /api/v1/admin
```

`rate_limits`が`header_match`エントリを生成し、`descriptors`が一致バケットを選びます。Istio 1.31に固定されたEnvoy APIにあるフィールドで、ここで設定するとローカルフィルターによるroute/vhostレート制限アクション検索を置き換えます。path値はリテラルdescriptorキーで、実前方一致は`headers`内です。接頭辞はその文字列で始まる長いパスも含みます。fallbackは不一致要求を制限します。`always_consume_default_token_bucket: false`で、一致した100 req/sユーザーが追加で10 req/s fallbackに制限されるのを避けます。

### ヘッダーベースのレート制限

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: user-based-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
        portNumber: 8080
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          descriptors:
          - entries:
            - key: header_match
              value: x-user-tier:premium
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 100
              fill_interval: 1s
          - entries:
            - key: header_match
              value: x-user-tier:free
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
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          always_consume_default_token_bucket: false
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: x-user-tier:premium
                headers:
                - name: x-user-tier
                  string_match:
                    exact: premium
          - actions:
            - header_value_match:
                descriptor_value: x-user-tier:free
                headers:
                - name: x-user-tier
                  string_match:
                    exact: free
```

tier descriptorはローカルプロキシ内のtier共有バケットで、ユーザー別ではありません。認証済み上流が呼び出し元tierヘッダーを削除して信頼tierを挿入し、サービスはその経路の迂回を防ぐ必要があります。欠損/不明tierは上限付きfallbackを使います。premiumヘッダーだけでは誰も認証されません。

## グローバルレート制限 {#global-rate-limiting}

共有判断サービスにdomain/descriptorを問い合わせます。Gatewayレプリカ間に範囲を広げられますが、自動的にクラスター全要求が対象にはなりません。カウンター保存、窓境界、フェイルオーバー、障害方針が実保証に影響します。

### アーキテクチャ

![クライアント要求がIstio Ingress Gatewayを通り、メモリキャッシュを背後に持つ中央レート制限サーバーへ確認してから許可通信をbackendへ送る構成。](../../../.gitbook/assets/en-service-mesh-istio-resilience-02-rate-limiting-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-02-rate-limiting-2.html)

### 設定方法

グローバル制限には外部Rate LimitサービスのデプロイとEnvoyFilter統合が必要です。

図のキャッシュにはRedisなど共有カウンターストアが必要で、独立プロセス内キャッシュでは全体クォータになりません。以下は隔離演習の`redis-ratelimit.istio-system.svc.cluster.local:6379`に**Redis TCPサービスが利用可能**な前提です。作成、認証/TLS、永続化/HA、切り替えは別要件で、以下では作りません。保護backendには適切なSecret/マウントで固定サービスのREDIS_AUTH/REDIS_TLS/証明書設定を行います。

イメージは公開コミット8fe6ea42（August 24, 2026）で、manifest digest固定、linux/amd64とlinux/arm64対応です。上流はv1.4.0後にsemverリリースでなくコミットタグを使います。認定された安定/本番版という主張ではありません。更新をレビュー・テストします。Deploymentはサイドカー注入を明示要求するためinjector一致と、実メッシュ/ネットワークポリシー下でGatewayがgRPC Serviceへ届くことを確認します。

#### 1. Rate Limitサービスのデプロイ

**注**: Istioは[envoyproxy/ratelimit](https://github.com/envoyproxy/ratelimit)を外部依存として使います。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: "domain: production-ratelimit\ndescriptors:\n  # Global limit: 100 per second\n  - key: generic_key\n    value: \"global\"\n    rate_limit:\n      unit: second\n      requests_per_unit: 100\n\n  # Per-path limit\n  - key: header_match\n    value: \"/api/v1/*\"\n    rate_limit:\n      unit: second\n      requests_per_unit: 50\n\n  # Per-user limit (per minute)\n  - key: remote_address\n    rate_limit:\n      unit: minute\n      requests_per_unit: 1000\n"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ratelimit
  template:
    metadata:
      labels:
        app: ratelimit
      annotations:
        sidecar.istio.io/inject: 'true'
    spec:
      containers:
      - name: ratelimit
        image: docker.io/envoyproxy/ratelimit:8fe6ea42@sha256:a61547259607d40aff153050c2a87873ca1676d1d9f5f06937d412000dcc2df1
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8081
          name: grpc
        env:
        - name: LOG_LEVEL
          value: info
        - name: CONFIG_TYPE
          value: FILE
        - name: RUNTIME_ROOT
          value: /data
        - name: RUNTIME_SUBDIRECTORY
          value: ratelimit
        - name: RUNTIME_APPDIRECTORY
          value: config
        - name: RUNTIME_WATCH_ROOT
          value: 'false'
        - name: RUNTIME_IGNOREDOTFILES
          value: 'true'
        - name: USE_STATSD
          value: 'false'
        - name: REDIS_SOCKET_TYPE
          value: tcp
        - name: REDIS_URL
          value: redis-ratelimit.istio-system.svc.cluster.local:6379
        - name: HOST
          value: '::'
        - name: GRPC_HOST
          value: '::'
        - name: HEALTHY_WITH_AT_LEAST_ONE_CONFIG_LOADED
          value: 'true'
        volumeMounts:
        - name: config-volume
          mountPath: /data/ratelimit/config
          readOnly: true
        command:
        - /bin/ratelimit
        resources:
          requests:
            memory: 128Mi
            cpu: 100m
          limits:
            memory: 512Mi
            cpu: 500m
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: ratelimit-config
---
apiVersion: v1
kind: Service
metadata:
  name: ratelimit
  namespace: istio-system
spec:
  ports:
  - port: 8080
    name: http
    targetPort: 8080
  - port: 8081
    name: grpc
    targetPort: 8081
  selector:
    app: ratelimit
```

#### 2. EnvoyFilterでグローバル制限を設定

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
          domain: production-ratelimit
          failure_mode_deny: true
          timeout: 0.1s
          rate_limit_service:
            grpc_service:
              envoy_grpc:
                cluster_name: outbound|8081||ratelimit.istio-system.svc.cluster.local
                authority: ratelimit.istio-system.svc.cluster.local
            transport_api_version: V3
```

#### 3. Gateway VirtualHostのレート制限アクション追加

フィルターと同じ専用Gatewayに一度だけ適用します。意図的に全HTTP virtual hostを対象とするため、共有Gatewayなら検証済み生成vhostに絞ります。ConfigMapに対応するglobal、path-prefix、client-IP descriptorを生成します。`remote_address`は信頼する下流IPでユーザーIDではありません。クォータに使う前に実プロキシ/XFF信頼チェーンとNATを考慮します。


```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-ratelimit-actions
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: VIRTUAL_HOST
    match:
      context: GATEWAY
    patch:
      operation: MERGE
      value:
        rate_limits:
        - actions:
          - generic_key:
              descriptor_value: global
        - actions:
          - header_value_match:
              descriptor_value: /api/v1/*
              headers:
              - name: :path
                string_match:
                  prefix: /api/v1/
        - actions:
          - remote_address: {}
```

フィルターはIstio生成gRPCクラスターを使い、通常の検出とメッシュTLSポリシーが適用されます。手作業の平文クラスターは追加しません。`failure_mode_deny: true`は通常、判断サービスエラーでHTTP 500、上限超過で429を返し、falseならfail-openし得ます。100ms予算は例です。Redis timeout、遅延、呼び出し元期限を合わせます。窓境界、Redis再起動/切り替え、サービスレプリカ変更でカウンターを検証します。ConfigMap変更後は再読み込み/再起動を確認し、PodがRunningだけでポリシー読込を推定しないでください。

### 主なパラメーター

| パラメーター | 説明 |
|-----------|-------------|
| `domain` | Rate Limitサービスの設定domain（ConfigMapと一致が必要） |
| `failure_mode_deny` | サービス失敗時に要求を拒否するか |
| `timeout` | サービス応答待ち時間 |
| `rate_limit_service` | 外部サービスのgRPCエンドポイント |

### グローバルとローカルの選択基準

**ローカルを使う場合**:
- 単純な設定
- 高速応答
- 外部依存なし
- バケットごとの範囲。レプリカ数/分散が総スループットに影響

**グローバルを使う場合**:
- 選択descriptorの共有上限
- 複雑なルール（ユーザー別、IP別、パス別）
- 中央管理
- 外部サービスが必要（複雑さ増加）
- 若干の遅延（gRPC呼び出し）

**推奨**:
- **本番API Gateway**: グローバル（厳密制御が必要）
- **マイクロサービス保護**: ローカル（高速応答）
- **ハイブリッド**: Gatewayにグローバル、内部サービスにローカル

## 実践例 {#practical-examples}

### 例1: API Gatewayのレート制限

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: api-gateway-ratelimit
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
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
          descriptors:
          - entries:
            - key: header_match
              value: /api/v1/public/*
            token_bucket:
              max_tokens: 100
              tokens_per_fill: 10
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /api/v1/protected/*
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 100
              fill_interval: 1s
          - entries:
            - key: header_match
              value: /graphql
            token_bucket:
              max_tokens: 500
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
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          always_consume_default_token_bucket: false
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: /api/v1/public/*
                headers:
                - name: :path
                  string_match:
                    prefix: /api/v1/public/
          - actions:
            - header_value_match:
                descriptor_value: /api/v1/protected/*
                headers:
                - name: :path
                  string_match:
                    prefix: /api/v1/protected/
          - actions:
            - header_value_match:
                descriptor_value: /graphql
                headers:
                - name: :path
                  string_match:
                    prefix: /graphql
```

ローカルGateway例はパス接頭辞を分類します。`/protected`自体は認証を強制しません。Gatewayレプリカごとに独立バケットがあり、不明パスはfallbackを使います。独自`rate_limits`で推測した生成ルート名への依存を避けます。

### 例2: ユーザー階層別レート制限

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: tiered-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
        portNumber: 8080
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          descriptors:
          - entries:
            - key: header_match
              value: x-api-tier:enterprise
            token_bucket:
              max_tokens: 10000
              tokens_per_fill: 1000
              fill_interval: 1s
          - entries:
            - key: header_match
              value: x-api-tier:premium
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 100
              fill_interval: 1s
          - entries:
            - key: header_match
              value: x-api-tier:free
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
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          always_consume_default_token_bucket: false
          rate_limits:
          - actions:
            - header_value_match:
                descriptor_value: x-api-tier:enterprise
                headers:
                - name: x-api-tier
                  string_match:
                    exact: enterprise
          - actions:
            - header_value_match:
                descriptor_value: x-api-tier:premium
                headers:
                - name: x-api-tier
                  string_match:
                    exact: premium
          - actions:
            - header_value_match:
                descriptor_value: x-api-tier:free
                headers:
                - name: x-api-tier
                  string_match:
                    exact: free
```

以下のenterprise/premium/freeクォータは設定プロキシバケット内のtier別共有です。先のヘッダー例と同じ信頼ヘッダー/迂回防止が必要です。1000 req/sを企業ユーザー1人ごとの割り当てと解釈しないでください。

### 例3: 外部API保護

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: external-api-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
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
          stat_prefix: egress_rate_limiter
  - applyTo: VIRTUAL_HOST
    match:
      context: SIDECAR_OUTBOUND
      routeConfiguration:
        vhost:
          name: api.external.com:80
    patch:
      operation: MERGE
      value:
        typed_per_filter_config:
          envoy.filters.http.local_ratelimit:
            '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
            stat_prefix: egress_rate_limiter
            token_bucket:
              max_tokens: 1000
              tokens_per_fill: 10
              fill_interval: 1s
            response_headers_to_add:
            - header:
                key: x-rate-limit-exceeded
                value: 'true'
              append_action: OVERWRITE_IF_EXISTS_OR_ADD
            filter_enabled:
              default_value:
                numerator: 100
                denominator: HUNDRED
            filter_enforced:
              default_value:
                numerator: 100
                denominator: HUNDRED
```

Egress例は[外部の外れ値保護](01-outlier-detection.md#protecting-external-services-serviceentry)の`api.external.com` HTTP 80→TLS 443 ServiceEntry/DestinationRuleを前提とします。生成vhostが`api.external.com:80`か確認します。リスナーには無効フィルターを入れ、そのvhostだけに有効バケットを与えます。他送信HTTP hostは制限されません。不透明なアプリHTTPSはHTTPフィルターで分類できません。呼び出し元ごとのバケットなので提供者/アカウント共有クォータではありません。応答ヘッダーは拒否応答を示し、ログ設定はしません。

## 監視 {#monitoring}

### Prometheusメトリクス

関連アプリ/Gateway Podテンプレートへアノテーションをマージして新プロキシをロールアウトします。[メトリクス](../observability/01-metrics.md)の収集設定を使います。クエリは`namespace`/`pod`スクレイプラベルとプロキシごと1収集を前提とします。ローカル接頭辞は`stat_prefix`に依存するため実名を確認します。

```yaml
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          proxyStatsMatcher:
            inclusionRegexps:
            - ".*http_local_rate_limit.*"
            - ".*ratelimit.*"
```

順に、ローカル適用拒否/s、上限内判断/s、照会要求の適用割合、グローバルのover-limit/OK/error/fail-open結果/sです。`rate_limited`は適用無効でもトークン不足判断を数え、`enforced`は適用拒否を数えます。`over_limit`は全グローバル呼び出し数ではありません。グローバルフィルターカウンターはルーティング先クラスターに属し、必ずしもレート制限サービスのクラスターではありません。

```promql
sum by (namespace, pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="default"}[5m]))

sum by (namespace, pod) (rate({__name__=~"envoy_.*http_local_rate_limit_ok",namespace="default"}[5m]))

100 * sum by (namespace, pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enforced",namespace="default"}[5m])) / sum by (namespace, pod) (rate({__name__=~"envoy_.*http_local_rate_limit_enabled",namespace="default"}[5m]))

rate(envoy_cluster_ratelimit_over_limit{namespace="istio-system"}[5m])

rate(envoy_cluster_ratelimit_ok{namespace="istio-system"}[5m])

rate(envoy_cluster_ratelimit_error{namespace="istio-system"}[5m])

rate(envoy_cluster_ratelimit_failure_mode_allowed{namespace="istio-system"}[5m])
```

Gatewayローカルには`namespace="istio-system"`を使い、選択ポリシーのPod/cluster/prefixを絞ります。ゼロ分母、統計欠損、収集失敗には明示no-data処理が必要です。アプリが独自に429を返すこともあり、HTTP 429だけではこのフィルターの適用は証明されません。

### Grafanaダッシュボード

UID `prometheus`と上のラベルが必要です。[ファイルプロビジョニング](../observability/04-dashboards.md)を使います。ConfigMapラベルだけではローダーになりません。

```json
{
  "uid": "istio-rate-limiting",
  "title": "Istio Rate Limiting",
  "panels": [
    {
      "id": 1,
      "title": "Local Enforced Rejections per Second",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum by (namespace, pod) (rate({__name__=~\"envoy_.*http_local_rate_limit_enforced\",namespace=\"default\"}[5m]))",
          "legendFormat": "{{namespace}} / {{pod}}",
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
      "title": "Local Enforced Fraction",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * sum by (namespace, pod) (rate({__name__=~\"envoy_.*http_local_rate_limit_enforced\",namespace=\"default\"}[5m])) / sum by (namespace, pod) (rate({__name__=~\"envoy_.*http_local_rate_limit_enabled\",namespace=\"default\"}[5m]))",
          "legendFormat": "{{namespace}} / {{pod}}",
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

## トラブルシューティング {#troubleshooting}

### レート制限が動かない

```bash
# 1. Check EnvoyFilter
kubectl get envoyfilter -A

# 2. Check Envoy configuration
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(.name? == "envoy.filters.http.local_ratelimit" or .name? == "envoy.filters.http.ratelimit")'

# 3. Check route/vhost overrides and actual optional counters
istioctl proxy-config routes <pod-name> -n <namespace> -o json
istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep -E "rate_limit|ratelimit"
```

### グローバルレート制限の接続失敗

```bash
# Check Rate Limit Service
kubectl get pods -n istio-system -l app=ratelimit
kubectl logs -n istio-system -l app=ratelimit

# Check Redis connection
kubectl exec <redis-client-pod> -n istio-system -c <client-container> -- \
  redis-cli -h redis-ratelimit.istio-system.svc.cluster.local -p 6379 PING

# Check the gateway-to-service cluster and ready backend endpoints
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn ratelimit.istio-system.svc.cluster.local
kubectl get endpointslice -n istio-system -l kubernetes.io/service-name=ratelimit
```

Redisコマンドにはredis-cliとbackend TLS/認証設定を持つ既存の許可クライアントコンテナが必要です。固定イメージはdistrolessで、シェルもredis-cliもありません。サービスログ、`/healthcheck`、読込設定、名前空間セレクター、メッシュポリシー、descriptor一致を確認します。緑のPodや空のデフォルトプロキシログは適用の証明ではありません。

## 参考資料

- [Istioレート制限](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/)
- [Envoyレート制限](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/local_rate_limit_filter)
- [Envoyグローバルレート制限](https://github.com/envoyproxy/ratelimit)
