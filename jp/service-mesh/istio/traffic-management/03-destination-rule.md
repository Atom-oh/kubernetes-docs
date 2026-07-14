# DestinationRule

> **サポート対象バージョン**: Istio 1.28+
> **API バージョン**: `networking.istio.io/v1`
> **最終更新**: February 19, 2026

DestinationRule は、VirtualService がトラフィックを宛先にルーティングした後の処理方法を定義する、Istio の中核リソースです。

## 目次

1. [DestinationRule とは？](#what-is-destinationrule)
2. [VirtualService と DestinationRule](#virtualservice-vs-destinationrule)
3. [Subset の概念](#subset-concept)
4. [基本構造](#basic-structure)
5. [Subset の定義](#defining-subsets)
6. [Traffic Policy の概要](#traffic-policy-overview)
7. [VirtualService との使用](#using-with-virtualservice)
8. [実践例](#practical-examples)
9. [ベストプラクティス](#best-practices)
10. [トラブルシューティング](#troubleshooting)

## DestinationRule とは？

DestinationRule は**ルーティング後のトラフィックポリシー**を定義します。VirtualService がトラフィックの送信先（「どこに」）を決定するなら、DestinationRule はその処理方法（「どのように」）を決定します。

```mermaid
flowchart LR
    Client[Client Request]

    subgraph VS[VirtualService]
        Route[Routing Decision<br/>Where?]
    end

    subgraph DR[DestinationRule]
        Policy[Traffic Policy<br/>How?]
    end

    subgraph Services[Services]
        V1[Version 1]
        V2[Version 2]
    end

    Client --> Route
    Route -->|90%| Policy
    Route -->|10%| Policy
    Policy --> V1
    Policy --> V2

    %% Style definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef routing fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef policy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Client client;
    class Route routing;
    class Policy policy;
    class V1,V2 service;
```

### DestinationRule の主な役割

| 役割 | 説明 | 例 |
|------|-------------|---------|
| **Subset 定義** | Service バージョンをグループ化 | v1, v2, canary, stable |
| **Load Balancing** | 負荷分散アルゴリズム | ROUND_ROBIN, LEAST_REQUEST |
| **Connection Pool** | コネクションプールの設定 | 最大コネクション数、Timeout |
| **Circuit Breaker** | 障害の隔離 | Outlier Detection |
| **TLS 設定** | 暗号化ポリシー | mTLS, SIMPLE TLS |

## VirtualService と DestinationRule

この 2 つのリソースは連携して、完全なトラフィック管理を提供します。

### 役割の比較

```mermaid
flowchart TD
    Request[HTTP Request<br/>Host: reviews]

    subgraph VS[VirtualService Role]
        Match{Condition Matching}
        Route[Routing Decision]
    end

    subgraph DR[DestinationRule Role]
        Subset[Subset Selection]
        Policy[Policy Application]
    end

    subgraph Pods[Pods]
        P1[reviews-v1-pod1]
        P2[reviews-v1-pod2]
        P3[reviews-v2-pod1]
    end

    Request --> Match
    Match -->|headers, path, etc.| Route
    Route -->|subset: v1<br/>weight: 90%| Subset
    Route -->|subset: v2<br/>weight: 10%| Subset
    Subset --> Policy
    Policy -->|load balancing| P1
    Policy -->|load balancing| P2
    Policy -->|load balancing| P3

    %% Style definitions
    classDef request fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef vs fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dr fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Request request;
    class Match,Route vs;
    class Subset,Policy dr;
    class P1,P2,P3 pod;
```

### 責務の分離

**VirtualService（どこに？）**:
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

**DestinationRule（どのように？）**:
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

## Subset の概念

Subset は Service の**論理グループ**を定義します。通常、バージョン、デプロイステージ、リージョンなどで区別されます。

### Subset の本質

```mermaid
flowchart TB
    Service[Kubernetes Service<br/>reviews]

    subgraph DR[DestinationRule Subset Definition]
        S1[Subset: v1<br/>labels: version=v1]
        S2[Subset: v2<br/>labels: version=v2]
    end

    subgraph Pods[Actual Pods]
        P1[reviews-v1-abc<br/>version=v1]
        P2[reviews-v1-def<br/>version=v1]
        P3[reviews-v2-xyz<br/>version=v2]
    end

    Service --> S1
    Service --> S2
    S1 -.->|Label Matching| P1
    S1 -.->|Label Matching| P2
    S2 -.->|Label Matching| P3

    %% Style definitions
    classDef service fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef subset fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Service service;
    class S1,S2 subset;
    class P1,P2,P3 pod;
```

### Subset のユースケース

#### 1. バージョンベースのルーティング

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
# Pod labels
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: reviews
    version: v1  # ← Matches Subset
```

#### 2. デプロイステージの分離

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

#### 3. リージョンの分離

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

#### 4. 環境の分離

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

## 基本構造

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

### Host の指定方法

**1. Service 名（同じ Namespace）**
```yaml
spec:
  host: reviews
```

**2. FQDN（異なる Namespace）**
```yaml
spec:
  host: reviews.production.svc.cluster.local
```

**3. ワイルドカード**
```yaml
spec:
  host: "*.example.com"
```

**4. 外部 Service（ServiceEntry 使用）**
```yaml
spec:
  host: api.external.com
```

## Subset の定義

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

### Subset 固有のポリシー

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

### 複合ラベルマッチング

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

## Traffic Policy の概要

DestinationRule の `trafficPolicy` は、多様なトラフィック制御機能を提供します。

### Traffic Policy の階層

```mermaid
flowchart TD
    DR[DestinationRule]

    subgraph Global[Global Traffic Policy]
        GP[Applied to all subsets]
    end

    subgraph Subset1[Subset: v1]
        SP1[v1-specific policy<br/>Overrides global policy]
    end

    subgraph Subset2[Subset: v2]
        SP2[Inherits global policy]
    end

    DR --> Global
    Global --> Subset1
    Global --> Subset2

    %% Style definitions
    classDef dr fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef global fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef subset fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class DR dr;
    class GP global;
    class SP1,SP2 subset;
```

### Traffic Policy のコンポーネント

#### 1. Load Balancer

```yaml
trafficPolicy:
  loadBalancer:
    simple: ROUND_ROBIN  # LEAST_REQUEST, RANDOM, PASSTHROUGH
```

詳細は [Load Balancing](06-load-balancing.md) を参照してください。

#### 2. Connection Pool

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

詳細は [Circuit Breaker](07-circuit-breaker.md) を参照してください。

#### 3. Outlier Detection

```yaml
trafficPolicy:
  outlierDetection:
    consecutiveErrors: 5
    interval: 30s
    baseEjectionTime: 30s
    maxEjectionPercent: 50
```

詳細は [Circuit Breaker](07-circuit-breaker.md) を参照してください。

#### 4. TLS 設定

```yaml
trafficPolicy:
  tls:
    mode: ISTIO_MUTUAL  # DISABLE, SIMPLE, MUTUAL
```

詳細は [Security](../security/01-mtls.md) を参照してください。

#### 5. ポートレベル設定

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

## VirtualService との使用

VirtualService と DestinationRule は連携して、完全なトラフィック制御を提供します。

### 基本パターン: Canary Deployment

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

### ヘッダーベースのルーティング

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

### URI ベースのルーティング + Subset 固有のポリシー

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

## 実践例

### 例 1: Microservice のバージョン管理

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

**ユースケース**:
- v1: 安定版（大半のトラフィック）
- v2: Canary バージョン（トラフィックの 10%）
- v3: テストバージョン（開発者のみ）

### 例 2: マルチリージョンデプロイ

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

### 例 3: デプロイステージポリシー

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
        consecutiveErrors: 3
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
        consecutiveErrors: 5
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
        consecutiveErrors: 10
        interval: 60s
        baseEjectionTime: 30s
```

### 例 4: 外部 Service の統合

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
  - number: 443
    name: https
    protocol: HTTPS
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
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 120s
    tls:
      mode: SIMPLE
```

### 例 5: データベースの Connection Pool

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
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 100
    outlierDetection:
      consecutiveErrors: 3
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

## ベストプラクティス

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

# ❌ Bad example: Vague names
subsets:
- name: subset1
- name: test
- name: new
```

### 2. デフォルトポリシー + オーバーライドパターン

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

### 3. Circuit Breaker は必須

```yaml
# ✅ Always set outlierDetection
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service
spec:
  host: api-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:  # Required
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

### 4. Connection Pool の設定

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

### 5. 段階的ロールアウト

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

## トラブルシューティング

### Subset が動作しない

**症状**:
```bash
# VirtualService exists but traffic isn't routed
kubectl get virtualservice reviews -o yaml
```

**原因と解決策**:

```bash
# 1. Check DestinationRule
kubectl get destinationrule reviews -o yaml

# 2. Verify subset names match
# VirtualService: subset: v2
# DestinationRule: name: v2

# 3. Check pod labels
kubectl get pods --show-labels | grep reviews

# 4. Verify pods have version=v2 label
kubectl label pod reviews-v2-xxx version=v2
```

### Traffic Policy が適用されない

```bash
# Check Envoy configuration
istioctl proxy-config cluster <pod-name> --fqdn reviews.default.svc.cluster.local -o json

# Check Circuit Breaker settings
istioctl proxy-config cluster <pod-name> -o json | jq '.[] | select(.name=="outbound|9080||reviews.default.svc.cluster.local") | .circuitBreakers'
```

### Subset の競合

**問題**:
```yaml
# Multiple DestinationRules for the same host cause conflicts
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
# ❌ Conflict occurs
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

### istioctl の分析

```bash
# Validate DestinationRule
istioctl analyze

# Specific namespace
istioctl analyze -n production

# Example output
# Error [IST0101] (DestinationRule reviews.default) Referenced host not found: "reviews"
```

## 次のステップ

DestinationRule を理解したら、次のトピックに進んでください。

1. **[Traffic Splitting](04-traffic-splitting.md)**: Canary、Blue/Green デプロイ
2. **[Load Balancing](06-load-balancing.md)**: 多様なアルゴリズムとポリシー
3. **[Circuit Breaker](07-circuit-breaker.md)**: 障害の隔離とレジリエンス
4. **[Retry and Timeout](05-retry-timeout.md)**: Retry と Timeout の設定

## 参考資料

- [Istio DestinationRule Reference](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [Envoy Cluster Configuration](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/upstream)
