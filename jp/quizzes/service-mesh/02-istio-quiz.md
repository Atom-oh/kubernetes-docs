# Istio クイズ

> **対応バージョン**: Istio 1.28.0
> **EKS バージョン**: 1.34 (Kubernetes 1.28+)
> **最終更新**: February 19, 2026

このクイズでは、Istio service mesh に関する理解を確認します。

## 問題 1: Service Mesh の基本概念

<details>
<summary>service mesh とは何ですか？また、その主な機能は何ですか？</summary>

**回答:**
service mesh は service-to-service communication を処理するインフラストラクチャレイヤーであり、application code を変更せずにサービス間の通信を制御および可観測化できます。

**主な機能:**
1. **Traffic Management**: サービス間のトラフィックフローを制御
   - Routing、load balancing、canary deployment
   - Timeout、Retry、Circuit Breaker
   - Traffic mirroring と shadow testing

2. **Security**: service-to-service communication の暗号化と認証
   - 自動 mTLS (mutual TLS)
   - Authorization Policy (access control)
   - Request Authentication (JWT)

3. **Observability**: service-to-service communication の可視化
   - Metrics 収集 (Prometheus)
   - Distributed tracing (Jaeger/Zipkin)
   - Logging と可視化 (Kiali、Grafana)

**Istio の特性:**
- 既存の分散 application に透過的にレイヤーとして追加
- sidecar proxy パターン (Envoy) を使用
- Ambient Mode (sidecar-less architecture) をサポート
- 宣言型設定による Policy 管理
</details>

## 問題 2: Istio アーキテクチャ

<details>
<summary>Istio 1.28.0 の主なコンポーネントと役割は何ですか？</summary>

**回答:**
**Control Plane:**
- **Istiod**: 単一バイナリに統合された Control Plane
  - **Service Discovery**: mesh service registry を維持
  - **Configuration Management**: Istio 設定を保存および配布
  - **Certificate Management**: mTLS 用の証明書を生成およびローテーション

**Data Plane:**
- **Envoy Proxy**: sidecar としてデプロイされ、すべてのネットワーク通信を仲介
  - Traffic routing と load balancing
  - mTLS 暗号化と認証
  - Metrics、logs、traces の収集

**Ambient Mode (オプション):**
- **ztunnel**: Node レベルの proxy (L4)
- **waypoint proxy**: オプションの L7 proxy

**主な機能:**
- 単一バイナリ (Istiod) の統合 Control Plane
- スケーラブルで高可用性のアーキテクチャ
- Kubernetes-native の CRD ベース設定
- Ambient Mode により 85% 以上のリソース削減が可能
</details>

## 問題 3: Traffic Management と Argo Rollouts の統合

<details>
<summary>Istio と Argo Rollouts を使用して、自動化された canary deployment をどのように実装しますか？</summary>

**回答:**
Argo Rollouts は Istio と統合し、Metrics ベースの自動 canary deployment を提供します。

**1. Rollout Resource の定義:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: reviews
spec:
  replicas: 5
  strategy:
    canary:
      # Istio traffic control
      trafficRouting:
        istio:
          virtualService:
            name: reviews-vsvc
            routes:
            - primary
          destinationRule:
            name: reviews-destrule
            canarySubsetName: canary
            stableSubsetName: stable

      # Staged deployment
      steps:
      - setWeight: 10    # 10% Canary
      - pause: {duration: 2m}
      - setWeight: 25    # 25% Canary
      - pause: {duration: 2m}
      - setWeight: 50    # 50% Canary
      - pause: {duration: 2m}

      # Automatic metrics analysis
      analysis:
        templates:
        - templateName: success-rate
        - templateName: latency
        startingStep: 1
```

**2. AnalysisTemplate - 自動ロールバック:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    successCondition: result >= 0.95  # 95% or higher
    failureLimit: 2  # Auto-rollback after 2 failures
    provider:
      prometheus:
        query: |
          sum(rate(istio_requests_total{
            response_code!~"5.*"
          }[2m])) / sum(rate(istio_requests_total[2m]))
```

**主な機能:**
- Metrics ベースの自動進行/ロールバック
- 段階的なトラフィック増加 (10% → 25% → 50% → 100%)
- リアルタイムの Prometheus Metrics 分析
- 失敗時の即時自動ロールバック
</details>

## 問題 4: Security 機能

<details>
<summary>Istio 1.28.0 の mTLS と Authorization Policy の機能は何ですか？</summary>

**回答:**
**mTLS の利点:**
- service-to-service communication の自動暗号化
- 相互認証によるセキュリティの強化
- application code の変更なしで適用
- 証明書の自動発行と更新

**1. PeerAuthentication - mTLS Policy:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**2. AuthorizationPolicy - きめ細かな Access Control:**
```yaml
# Deny by default
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec: {}  # Deny all requests

---
# Allow specific
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]
```

**3. RequestAuthentication - JWT Validation:**
```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
```

**ベストプラクティス:**
- deny-by-default Policy を使用
- 最小権限の原則を適用
- Service Account ベースの認証
- Namespace の分離
</details>

## 問題 5: Gateway と Ingress

<details>
<summary>Istio Gateway の役割は何ですか？また、TLS をどのように設定しますか？</summary>

**回答:**
**Gateway の役割:**
- cluster 内部サービスへの外部トラフィックのエントリポイント
- Ingress/Egress トラフィックの制御
- TLS termination と証明書管理
- Load Balancer との統合

**設定例:**
```yaml
# Gateway Definition
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTPS (443)
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com

  # HTTP (80) - Redirect to HTTPS
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
    tls:
      httpsRedirect: true

---
# VirtualService - Connect to Gateway
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: bookinfo-vs
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - bookinfo-gateway
  http:
  - match:
    - uri:
        prefix: /productpage
    route:
    - destination:
        host: productpage
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
```

**TLS 証明書の作成:**
```bash
# Create TLS certificate as Kubernetes Secret
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## 問題 6: Observability ツール

<details>
<summary>Istio 1.28.0 が提供する Observability ツールとその役割は何ですか？</summary>

**回答:**
**1. Prometheus - Metrics 収集:**
```promql
# Golden Signals Monitoring
# 1. Latency (P95)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/ sum(rate(istio_requests_total[5m]))

# 4. Saturation (CPU usage)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

**2. Jaeger - Distributed Tracing:**
```yaml
# Enable Tracing
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
```

**3. Kiali - Service Mesh の可視化:**
- リアルタイムのトポロジー可視化
- トラフィックフローの分析
- 設定の検証
- Performance Metrics の表示

**4. Grafana - Dashboard:**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- カスタム Dashboard の作成

**アクセス方法:**
```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```
</details>

## 問題 7: Ambient Mode

<details>
<summary>Istio 1.28.0 の Ambient Mode とは何ですか？また、Sidecar Mode とどのように異なりますか？</summary>

**回答:**
**Ambient Mode の概念:**
- sidecar-less service mesh アーキテクチャ
- ztunnel (Node レベルの L4 proxy) + waypoint (オプションの L7 proxy)
- 85% 以上のリソース削減

**アーキテクチャの比較:**

| 機能 | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| デプロイメント | Pod ごとの Envoy injection | Node ごとに 1 つの ztunnel |
| リソース使用量 | 高い (Pod ごとに 50-100MB) | 低い (Node ごとに 50MB) |
| デプロイメントの複雑さ | 高い (再デプロイが必要) | 低い (透過的な適用) |
| L4 機能 | サポート | ztunnel 経由でサポート |
| L7 機能 | 完全サポート | waypoint が必要 |
| Performance | やや遅い | 高速 (L4 のみ) |

**Ambient Mode の有効化:**
```bash
# Install Ambient Mode
istioctl install --set profile=ambient -y

# Enable Ambient Mode on Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**ユースケース:**
- リソースが制約された環境
- 大規模 cluster (1000+ Pod)
- L4 機能のみが必要な場合
- 段階的な Istio 導入
</details>

## 問題 8: Resilience パターン

<details>
<summary>Istio における Outlier Detection、Circuit Breaker、Rate Limiting の違いは何ですか？</summary>

**回答:**
**1. Outlier Detection - 異常なインスタンスを除外:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5       # 5 consecutive failures
      interval: 30s              # Evaluate every 30s
      baseEjectionTime: 30s      # 30s ejection
      maxEjectionPercent: 50     # Max 50% ejection
```

**2. Circuit Breaker - 過負荷を防止:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
```

**3. Rate Limiting - Request レート制御:**
```yaml
# Local Rate Limiting
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit
spec:
  configPatches:
  - applyTo: HTTP_FILTER
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
```

**違い:**
- **Outlier Detection**: リアクティブ (失敗後に除外)
- **Circuit Breaker**: 予防的 (connection を制限)
- **Rate Limiting**: Request レート制御 (token bucket)

**組み合わせての使用:**
```yaml
trafficPolicy:
  connectionPool:     # Circuit Breaker
    tcp:
      maxConnections: 100
  outlierDetection:   # Outlier Detection
    consecutiveErrors: 5
```
</details>

## 問題 9: Locality Load Balancing (Zone Aware Routing)

<details>
<summary>Istio の Locality Load Balancing 機能とは何ですか？また、AWS EKS でどのように使用しますか？</summary>

**回答:**
**Locality Load Balancing の概念:**
- 同じ Availability Zone (AZ) 内のサービスへの優先 Routing
- ネットワークレイテンシーの削減
- cross-AZ data transfer コストの削減 (~85%)

**設定:**
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Same AZ priority, other AZ for failover
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ 80%
            "us-east-1/us-east-1b/*": 20  # Other AZ 20%

        # Failover policy
        failover:
        - from: us-east-1
          to: us-west-2
```

**AWS EKS での使用:**
1. **コスト削減:**
   - cross-AZ traffic: $0.01/GB
   - 同一 AZ traffic: 無料
   - 80% の同一 AZ Routing による大幅なコスト削減

2. **Performance の改善:**
   - intra-AZ latency: ~1ms
   - cross-AZ latency: ~2-3ms

3. **自動フェイルオーバー:**
   - AZ 障害時に別の AZ へ自動フェイルオーバー
   - Outlier Detection と組み合わせて使用

**Pod topology の設定:**
```yaml
# EKS nodes automatically set topology labels
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## 問題 10: Amazon EKS 統合とベストプラクティス

<details>
<summary>Istio 1.28.0 を Amazon EKS 1.34 と統合する際の考慮事項とベストプラクティスは何ですか？</summary>

**回答:**
**1. インストールと設定:**
```bash
# Install Istioctl
curl -L https://istio.io/downloadIstio | sh -
cd istio-1.28.0
export PATH=$PWD/bin:$PATH

# Install with production profile
istioctl install --set profile=production -y
```

**2. AWS Load Balancer 統合:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    # Network Load Balancer
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

    # TLS termination (ACM certificate)
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: "arn:aws:acm:region:account:certificate/id"
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"
spec:
  type: LoadBalancer
```

**3. リソース最適化:**
```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5

  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1024Mi
```

**4. Security 設定:**
```yaml
# VPC Security Group settings
# - Istiod: 15010, 15012, 8080
# - Envoy: 15001, 15006, 15021, 15090
# - Gateway: 80, 443

# IAM Role (IRSA)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: istio-ingressgateway
  namespace: istio-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::account:role/istio-gateway
```

**5. Monitoring 統合:**
```yaml
# CloudWatch Container Insights
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  output.conf: |
    [OUTPUT]
        Name cloudwatch_logs
        Match *
        region us-east-1
        log_group_name /aws/eks/cluster/istio
```

**6. ベストプラクティス:**
- production profile を使用
- Control Plane HA (replica >= 3)
- mTLS STRICT mode
- PodDisruptionBudget の設定
- Locality Load Balancing を有効化
- Prometheus + Grafana による monitoring
- 定期的なバージョンアップグレード (Canary アプローチ)

**7. コスト最適化:**
- Ambient Mode を検討 (85% のリソース削減)
- Locality Load Balancing (cross-AZ コスト削減)
- Sidecar Scope の制限 (30-50% のメモリ削減)
</details>

## ボーナス問題: Progressive Delivery

<details>
<summary>Istio + Argo Rollouts を使用して、完全に自動化された Progressive Delivery をどのように実装しますか？</summary>

**回答:**
Progressive Delivery は、Metrics に基づいて deployment を自動的に進行またはロールバックするアプローチです。

**完全自動化の例:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  replicas: 10
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary

      steps:
      # Stage 1: 10% Canary
      - setWeight: 10
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 2: 25% Canary (auto-progress)
      - setWeight: 25
      - pause: {duration: 1m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 3: 50% Canary (auto-progress)
      - setWeight: 50
      - pause: {duration: 2m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency

      # Stage 4: 100% Canary (auto-complete)
```

**自動ロールバックの条件:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 30s
    count: 4
    successCondition: result >= 0.95
    failureLimit: 2  # Immediate rollback after 2 failures
    provider:
      prometheus:
        query: |
          # Success rate < 95% or
          # Latency > 500ms or
          # Error rate > 5%
          # → Auto rollback
```

**主な利点:**
- 完全自動化 (人による介入は不要)
- 即時ロールバック (障害検出から数秒以内)
- 安全な deployment (Metrics ベースの検証)
- 一貫したプロセス (標準化)
</details>

---

**スコア:**
- 10-11 問正解: 優秀 (Istio エキスパートレベル)
- 8-9 問正解: 良好 (production 運用が可能)
- 6-7 問正解: 平均 (追加学習を推奨)
- 4-5 問正解: 不十分 (基本概念の見直しが必要)
- 0-3 問正解: 再学習が必要

**学習リソース:**
- [Istio 公式ドキュメント](https://istio.io/latest/docs/)
- [Argo Rollouts ドキュメント](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [このガイドの詳細ドキュメント](../../service-mesh/istio/README.md)
