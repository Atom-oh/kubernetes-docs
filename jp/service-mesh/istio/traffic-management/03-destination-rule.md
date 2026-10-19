# DestinationRule

> **確認済みバージョン**: Istio 1.31.0
> **API バージョン**: `networking.istio.io/v1`
> **最終更新日**: 2026年9月11日

DestinationRule は、VirtualService がトラフィックを宛先へルーティングした後の処理方法を定義する、Istio の中核リソースです。

## 目次

1. [DestinationRule とは](#what-is-destinationrule)
2. [VirtualService と DestinationRule の違い](#virtualservice-vs-destinationrule)
3. [Subset の概念](#subset-concept)
4. [基本構造](#basic-structure)
5. [Subset の定義](#defining-subsets)
6. [トラフィックポリシーの概要](#traffic-policy-overview)
7. [VirtualService との併用](#using-with-virtualservice)
8. [実践例](#practical-examples)
9. [ベストプラクティス](#best-practices)
10. [トラブルシューティング](#troubleshooting)

## DestinationRule とは {#what-is-destinationrule}

ここに示す例は、それぞれ独立したサイドカー設定パターンです。DestinationRule と VirtualService は istiod がコンパイルする設定入力であり、別々のトラフィック処理ホップではありません。VirtualService がなくても DestinationRule は適用されます。Subset は、Service についてすでに検出されたエンドポイントを選択するだけです。ワークロードを作成したり、環境を分離したり、トラフィックの割合を割り当てたりはしません。Pod テンプレートのラベルを一致させ、Subset へのルートを明示してください。

DestinationRule は**ルーティング後のトラフィックポリシー**を定義します。VirtualService がトラフィックの「送信先」を決めるのに対し、DestinationRule はトラフィックの「処理方法」を決めます。

![クライアントのリクエストが VirtualService のルーティング判断（どこへ送るか）を通り、DestinationRule のトラフィックポリシーを適用されてから、Subset v1 と v2 の2つのサービスバージョンに到達する図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-03-destination-rule-0.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-03-destination-rule-0.html)

### DestinationRule の主な役割

| 役割 | 説明 | 例 |
|------|-------------|---------|
| **Subset の定義** | サービスのバージョンをグループ化 | v1、v2、canary、stable |
| **負荷分散** | 負荷分散アルゴリズム | ROUND_ROBIN、LEAST_REQUEST |
| **コネクションプール** | 接続プールの設定 | 最大接続数、タイムアウト |
| **サーキットブレーカー** | 障害の分離 | Outlier Detection |
| **TLS 設定** | 暗号化ポリシー | mTLS、SIMPLE TLS |

## VirtualService と DestinationRule の違い {#virtualservice-vs-destinationrule}

この2つのリソースは連携して、トラフィックを包括的に管理します。

### 役割の比較

![HTTP リクエストの条件を VirtualService が評価して名前付き Subset へルーティングし、続いて DestinationRule がその Subset を選択して、ラベルの一致する3つの Pod に負荷分散する図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-03-destination-rule-1.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-03-destination-rule-1.html)

### 責務の分担

**VirtualService（どこへ送るか）**:
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
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2  # ← References subset from DestinationRule
  - route:
    - destination:
        host: reviews
        subset: v1  # ← References subset from DestinationRule
```

**DestinationRule（どのように処理するか）**:
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:  # ← Default policy applied to all subsets
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:  # ← Subset definitions referenced by VirtualService
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
    trafficPolicy:  # ← Policy applied only to v2
      loadBalancer:
        simple: ROUND_ROBIN
```

## Subset の概念 {#subset-concept}

Subset は、サービスの**論理的なグループ**を定義します。通常、バージョン、デプロイ段階、リージョンなどで区別します。

### Subset の基本

![Kubernetes Service が DestinationRule の2つの Subset、v1 と v2 を参照し、それぞれがラベルとの照合によって該当バージョンのラベルを持つ実際の Pod に解決される図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-03-destination-rule-2.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-03-destination-rule-2.html)

### Subset の使用例

#### 1. バージョンに基づくルーティング

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-versions
spec:
  host: reviews
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

```yaml
# Pod-template label excerpt
metadata:
  labels:
    app: reviews
    version: v1  # ← Matches Subset
```

#### 2. デプロイ段階の分離

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-deployment-stages
spec:
  host: reviews
  subsets:
  - name: stable
    labels:
      stage: stable
  - name: canary
    labels:
      stage: canary
  - name: test
    labels:
      stage: test
```

#### 3. リージョンごとの分離

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-regions
spec:
  host: api-service
  subsets:
  - name: us-west
    labels:
      region: us-west
  - name: us-east
    labels:
      region: us-east
  - name: eu-central
    labels:
      region: eu-central
```

#### 4. 環境ごとの分離

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-environments
spec:
  host: payment-service
  subsets:
  - name: production
    labels:
      env: production
  - name: staging
    labels:
      env: staging
```

## 基本構造 {#basic-structure}

### 必須フィールド

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: my-destination-rule
  namespace: default
spec:
  host: my-service  # Required: Target service
  subsets:          # Optional: Subset definitions
  - name: v1
    labels:
      version: v1
  trafficPolicy:    # Optional: Traffic policy
    loadBalancer:
      simple: ROUND_ROBIN
```

### host の指定方法

**1. サービス名（同じ名前空間）**
```yaml
spec:
  host: reviews
```

**2. FQDN（異なる名前空間）**
```yaml
spec:
  host: reviews.production.svc.cluster.local
```

**3. ワイルドカード**
```yaml
spec:
  host: "*.example.com"
```

**4. 外部サービス（ServiceEntry を使用）**
```yaml
spec:
  host: api.external.com
```

## Subset の定義 {#defining-subsets}

### シンプルな Subset

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-simple
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

### Subset ごとのポリシー

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subset-policies
spec:
  host: reviews
  trafficPolicy:  # Default policy (all subsets)
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
  - name: v1
    labels:
      version: v1
    # v1 uses default policy

  - name: v2
    labels:
      version: v2
    trafficPolicy:  # v2-only policy (overrides default)
      loadBalancer:
        simple: ROUND_ROBIN
      connectionPool:
        http:
          http1MaxPendingRequests: 10
```

### 複雑なラベル照合

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-complex
spec:
  host: api-service
  subsets:
  - name: us-west-v2
    labels:
      version: v2
      region: us-west
      tier: premium
  - name: us-east-v1
    labels:
      version: v1
      region: us-east
      tier: standard
```

## トラフィックポリシーの概要 {#traffic-policy-overview}

DestinationRule の `trafficPolicy` では、さまざまなトラフィック制御機能を設定できます。

### トラフィックポリシーの階層

![DestinationRule の全体に設定した trafficPolicy がすべての Subset の既定値となり、Subset v1 はそのまま継承し、Subset v2 は独自の trafficPolicy で上書きするツリー図。](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-03-destination-rule-3.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-03-destination-rule-3.html)

### トラフィックポリシーの構成要素

#### 1. ロードバランサー

```yaml
trafficPolicy:
  loadBalancer:
    simple: ROUND_ROBIN  # LEAST_REQUEST, RANDOM, PASSTHROUGH
```

詳しくは[負荷分散](06-load-balancing.md)を参照してください。

#### 2. コネクションプール

```yaml
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50
      http2MaxRequests: 100
      maxRequestsPerConnection: 2
```

詳しくは[サーキットブレーカー](07-circuit-breaker.md)を参照してください。

#### 3. Outlier Detection

```yaml
trafficPolicy:
  outlierDetection:
    consecutive5xxErrors: 5
    interval: 30s
    baseEjectionTime: 30s
    maxEjectionPercent: 50
```

詳しくは[サーキットブレーカー](07-circuit-breaker.md)を参照してください。

#### 4. TLS 設定

```yaml
trafficPolicy:
  tls:
    mode: ISTIO_MUTUAL  # DISABLE, SIMPLE, MUTUAL
```

詳しくは[セキュリティ](../security/01-mtls.md)を参照してください。

#### 5. ポート単位の設定

```yaml
trafficPolicy:
  portLevelSettings:
  - port:
      number: 80
    loadBalancer:
      simple: ROUND_ROBIN
  - port:
      number: 443
    tls:
      mode: SIMPLE
```

## VirtualService との併用 {#using-with-virtualservice}

VirtualService と DestinationRule を併用して、トラフィックを包括的に制御できます。

### 基本パターン: カナリアデプロイ

本番環境で段階的に切り替える場合は、まず DestinationRule を適用し、新しい Subset がプロキシのクラスタ設定に現れたことを確認してから VirtualService を更新します。複数ドキュメントを1回の apply で適用しても、反映順序は保証されません。Subset を削除する前に、その Subset を参照するルートを削除してください。

```yaml
# DestinationRule: Subset definition
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
# VirtualService: Traffic distribution
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
        subset: v1  # ← References DestinationRule subset
      weight: 90
    - destination:
        host: reviews
        subset: v2  # ← References DestinationRule subset
      weight: 10
```

### ヘッダーに基づくルーティング

```yaml
# DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
# VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  # Developers use v2
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v2
  # Regular users use v1
  - route:
    - destination:
        host: reviews
        subset: v1
```

### URI ルーティングと Subset ごとのポリシー

```yaml
# DestinationRule: Different policies per subset
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service
spec:
  host: api-service
  subsets:
  - name: v1
    labels:
      version: v1
    trafficPolicy:
      loadBalancer:
        simple: ROUND_ROBIN
  - name: v2
    labels:
      version: v2
    trafficPolicy:
      loadBalancer:
        simple: LEAST_REQUEST
      connectionPool:
        http:
          http1MaxPendingRequests: 10
---
# VirtualService: URI-based routing
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  - match:
    - uri:
        prefix: "/api/v2"
    route:
    - destination:
        host: api-service
        subset: v2
  - route:
    - destination:
        host: api-service
        subset: v1
```

## 実践例 {#practical-examples}

### 例1: マイクロサービスのバージョン管理

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-versions
  namespace: production
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
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

**使用例**:
- v1: 安定版（大半のトラフィック）
- v2: カナリア版（トラフィックの10%）
- v3: テスト版（開発者のみ）

### 例2: マルチリージョンデプロイ

この例は、メッシュが各リージョンのエンドポイントをすでに検出でき、到達可能であることを前提とします。独自の `region` Pod ラベルで Subset を選択し、ノードのトポロジーラベルで Envoy の locality を別途設定します。リージョンごとの Subset には明示的なルーティングが必要です。また、locality failover には Outlier Detection と、到達可能な正常容量が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-multi-region
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
  subsets:
  - name: us-west
    labels:
      region: us-west
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 1000
  - name: us-east
    labels:
      region: us-east
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 1000
  - name: eu-central
    labels:
      region: eu-central
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 500
```

### 例3: デプロイ段階ごとのポリシー

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-service-stages
spec:
  host: payment-service
  subsets:
  # Production: Strict policy
  - name: production
    labels:
      stage: production
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 100
        http:
          http1MaxPendingRequests: 10
          maxRequestsPerConnection: 1
      outlierDetection:
        consecutive5xxErrors: 3
        interval: 10s
        baseEjectionTime: 60s

  # Canary: Moderate policy
  - name: canary
    labels:
      stage: canary
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 50
        http:
          http1MaxPendingRequests: 20
      outlierDetection:
        consecutive5xxErrors: 5
        interval: 30s
        baseEjectionTime: 30s

  # Staging: Lenient policy
  - name: staging
    labels:
      stage: staging
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 200
        http:
          http1MaxPendingRequests: 100
      outlierDetection:
        consecutive5xxErrors: 10
        interval: 60s
        baseEjectionTime: 30s
```

### 例4: 外部サービスとの連携

```yaml
# ServiceEntry: Register external API
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-payment-api
spec:
  hosts:
  - api.payment-gateway.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
    targetPort: 443
  location: MESH_EXTERNAL
  resolution: DNS
---
# DestinationRule: External API policy
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-payment-api
spec:
  host: api.payment-gateway.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 10
      http:
        http1MaxPendingRequests: 5
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 120s
    tls:
      mode: SIMPLE
      sni: api.payment-gateway.com
      subjectAltNames:
      - api.payment-gateway.com
```

この例では、アプリケーションは登録されたポート80へ HTTP を送信し、サイドカーがポート443へ検証付き TLS を開始します。例のホスト名は使用するエンドポイントに置き換えてください。アプリケーションがすでに HTTPS を送信する場合は、二重暗号化を避けるため、TLS origination と、その暗号化済み TLS パスには適用できない HTTP 専用のポリシー設定を省きます。

### 例5: データベースのコネクションプール

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-connection-pool
spec:
  host: postgres-primary
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 50  # DB connection limit
        connectTimeout: 5s
        tcpKeepalive:
          time: 7200s
          interval: 75s
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 60s
      baseEjectionTime: 120s
  subsets:
  - name: primary
    labels:
      role: primary
  - name: replica
    labels:
      role: replica
    trafficPolicy:
      connectionPool:
        tcp:
          maxConnections: 100  # More for replicas
```

ここで設定する TCP 接続数の上限は各プロキシに適用されるもので、データベース全体の接続予算ではありません。PostgreSQL は HTTP 接続設定を使用しません。選択する Service のエンドポイントにプライマリ用とレプリカ用の両方の Subset が含まれている必要があり、アプリケーションが読み取り先と書き込み先を正しく選ぶ必要があります。

## ベストプラクティス {#best-practices}

### 1. Subset の命名規則

```yaml
# ✅ Good example: Meaningful names
subsets:
- name: v1
- name: v2
- name: stable
- name: canary
- name: us-west
- name: production
```

```yaml
# ❌ Bad example: Vague names
subsets:
- name: subset1
- name: test
- name: new
```

### 2. 既定ポリシーと上書きのパターン

```yaml
# ✅ Good example: Define default policy and override when needed
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:  # Default policy
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
  - name: v1
    labels:
      version: v1
    # v1 uses default policy
  - name: v2
    labels:
      version: v2
    trafficPolicy:  # Override only for v2
      loadBalancer:
        simple: ROUND_ROBIN
```

### 3. 障害の分離を調整する

```yaml
# Tune outlierDetection for the service and failure model
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:  # Optional policy
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

### 4. コネクションプールの設定

```yaml
# ✅ Connection Pool appropriate for service characteristics
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-traffic-service
spec:
  host: api-gateway
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http2MaxRequests: 1000
        maxRequestsPerConnection: 100
```

### 5. 段階的なロールアウト

```yaml
# ✅ Gradually increase canary ratio
# Step 1: 5%
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary-step1
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

# Step 2: After monitoring, increase to 10%
# Step 3: 25% → 50% → 100%
```

### 6. ドキュメント化

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-service
  annotations:
    description: "Payment service traffic management"
    owner: "payments-team"
    subset-purpose: |
      - production: Main production traffic
      - canary: New version testing (10%)
      - staging: Pre-production testing
spec:
  host: payment-service
  # ...
```

## トラブルシューティング {#troubleshooting}

### Subset が機能しない

**症状**:
```bash
# VirtualService exists but traffic isn't routed
kubectl get virtualservice reviews -o yaml
```

**原因と対処**:

```bash
# 1. Check DestinationRule
kubectl get destinationrule reviews -o yaml

# 2. Verify subset names match
# VirtualService: subset: v2
# DestinationRule: name: v2

# 3. Check pod labels
kubectl get pods --show-labels | grep reviews

# 4. Verify pods have version=v2 label
kubectl get deployment reviews-v2 -o jsonpath='{.spec.template.metadata.labels}'
```

### トラフィックポリシーが適用されない

```bash
# Check Envoy configuration
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local -o json

# Check Circuit Breaker settings
istioctl proxy-config clusters <pod-name> -o json | jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .circuitBreakers'
```

### Subset の競合

Istio は、同じ host に適用される DestinationRule の断片をマージできます。以下のように異なる2つの Subset を定義しても、それだけで競合するわけではありません。同じ名前の Subset が重複している場合、最初の定義だけが使われ、内容はマージされません。また、複数のトップレベル `trafficPolicy` がある場合も、最初に処理されたものだけが残ります。名前空間による検索と可視性も考慮が必要です。所有者が1つのルールを管理するほうが動作を把握しやすくなります。

**問題**:
```yaml
# Same-host DestinationRule fragments can merge with restrictions
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-1
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
---
# Unique subset names can merge; duplicate names/policies are the problem
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-2
spec:
  host: reviews
  subsets:
  - name: v2
    labels:
      version: v2
```

**解決策**:
```yaml
# ✅ Define all subsets in one DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

### istioctl による分析

```bash
# Validate DestinationRule
istioctl analyze

# Specific namespace
istioctl analyze -n production

# Example output
# Inspect actual analyzer messages and confirm subset clusters in proxy-config output
```

## 次のステップ

DestinationRule を理解したら、次のトピックに進みましょう。

1. **[トラフィック分割](04-traffic-splitting.md)**: カナリア、Blue/Green デプロイ
2. **[負荷分散](06-load-balancing.md)**: さまざまなアルゴリズムとポリシー
3. **[サーキットブレーカー](07-circuit-breaker.md)**: 障害の分離と回復力
4. **[再試行とタイムアウト](05-retry-timeout.md)**: 再試行とタイムアウトの設定

## 参考資料

- [Istio DestinationRule リファレンス](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio トラフィック管理](https://istio.io/latest/docs/concepts/traffic-management/)
- [Envoy クラスタ設定](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/upstream)

- [DestinationRule のマージと安全な Subset の段階的ロールアウト](https://istio.io/latest/docs/ops/best-practices/traffic-management/)
- [TLS origination](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
