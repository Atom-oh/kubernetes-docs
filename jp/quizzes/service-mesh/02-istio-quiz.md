# Istio クイズ

> **サポート対象バージョン**: Istio 1.28.0
> **EKS バージョン**: 1.34 (Kubernetes 1.28+)
> **最終更新**: February 19, 2026

このクイズでは、Istio Service Meshについての理解を確認します。

## 問題 1: Service Meshの基本概念

<details>
<summary>Service Meshとは何ですか。また、主な機能は何ですか？</summary>

**回答:**
Service Meshは、サービス間通信を処理するインフラストラクチャレイヤーであり、アプリケーションコードを変更することなくサービス間の通信を制御および可観測化できます。

**主な機能:**
1. **トラフィック管理**: サービス間のトラフィックフローを制御
   - ルーティング、ロードバランシング、Canary Deployment
   - Timeout、Retry、Circuit Breaker
   - トラフィックミラーリングとシャドーテスト

2. **セキュリティ**: サービス間通信の暗号化と認証
   - 自動 mTLS (mutual TLS)
   - Authorization Policy (アクセス制御)
   - Request Authentication (JWT)

3. **可観測性**: サービス間通信の可視化
   - メトリクス収集 (Prometheus)
   - 分散トレーシング (Jaeger/Zipkin)
   - ロギングと可視化 (Kiali、Grafana)

**Istioの特性:**
- 既存の分散アプリケーションに透過的にレイヤー化
- Sidecar Proxyパターン (Envoy) を使用
- Ambient Mode (Sidecarを使用しないアーキテクチャ) をサポート
- 宣言的設定によるポリシー管理
</details>

## 問題 2: Istio アーキテクチャ

<details>
<summary>Istio 1.28.0の主なコンポーネントと役割は何ですか？</summary>

**回答:**
**Control Plane:**
- **Istiod**: 単一バイナリで統合されたControl Plane
  - **Service Discovery**: MeshのService Registryを維持
  - **Configuration Management**: Istio設定を保存および配布
  - **Certificate Management**: mTLS用の証明書を生成およびローテーション

**Data Plane:**
- **Envoy Proxy**: Sidecarとしてデプロイされ、すべてのネットワーク通信を仲介
  - トラフィックルーティングとロードバランシング
  - mTLSの暗号化と認証
  - メトリクス、ログ、トレースの収集

**Ambient Mode (オプション):**
- **ztunnel**: NodeレベルのProxy (L4)
- **waypoint proxy**: オプションのL7 Proxy

**主な機能:**
- 単一バイナリ (Istiod) による統合Control Plane
- スケーラブルかつ高可用性のアーキテクチャ
- KubernetesネイティブなCRDベースの設定
- Ambient Modeにより85%以上のリソース削減が可能
</details>

## 問題 3: トラフィック管理とArgo Rolloutsの統合

<details>
<summary>IstioとArgo Rolloutsを使用して、自動化されたCanary Deploymentをどのように実装しますか？</summary>

**回答:**
Argo RolloutsはIstioと統合し、メトリクスベースの自動Canary Deploymentを提供します。

**1. Rolloutリソースの定義:**
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
- メトリクスベースの自動進行/ロールバック
- 段階的なトラフィック増加 (10% → 25% → 50% → 100%)
- リアルタイムのPrometheusメトリクス分析
- 障害発生時の即時自動ロールバック
</details>

## 問題 4: セキュリティ機能

<details>
<summary>Istio 1.28.0におけるmTLSとAuthorization Policyの機能は何ですか？</summary>

**回答:**
**mTLSの利点:**
- サービス間通信の自動暗号化
- 相互認証によるセキュリティ強化
- アプリケーションコードの変更なしで適用
- 証明書の自動発行と更新

**1. PeerAuthentication - mTLSポリシー:**
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

**2. AuthorizationPolicy - きめ細かなアクセス制御:**
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

**3. RequestAuthentication - JWT検証:**
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
- デフォルト拒否ポリシーを使用
- 最小権限の原則を適用
- Service Accountベースの認証
- Namespaceの分離
</details>

## 問題 5: GatewayとIngress

<details>
<summary>Istio Gatewayの役割は何ですか。また、TLSをどのように設定しますか？</summary>

**回答:**
**Gatewayの役割:**
- 外部トラフィックからクラスタ内部Serviceへのエントリポイント
- Ingress/Egressトラフィックの制御
- TLS終端と証明書管理
- Load Balancerとの統合

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

**TLS証明書の作成:**
```bash
# Create TLS certificate as Kubernetes Secret
kubectl create -n istio-system secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo.crt
```
</details>

## 問題 6: 可観測性ツール

<details>
<summary>Istio 1.28.0はどのような可観測性ツールを提供し、それぞれの役割は何ですか？</summary>

**回答:**
**1. Prometheus - メトリクス収集:**
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

**2. Jaeger - 分散トレーシング:**
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

**3. Kiali - Service Meshの可視化:**
- リアルタイムのトポロジー可視化
- トラフィックフロー分析
- 設定検証
- パフォーマンスメトリクスの表示

**4. Grafana - ダッシュボード:**
- Istio Service Dashboard
- Istio Workload Dashboard
- Istio Performance Dashboard
- カスタムダッシュボードの作成

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
<summary>Istio 1.28.0のAmbient Modeとは何ですか。また、Sidecar Modeとの違いは何ですか？</summary>

**回答:**
**Ambient Modeの概念:**
- Sidecarを使用しないService Meshアーキテクチャ
- ztunnel (NodeレベルのL4 Proxy) + waypoint (オプションのL7 Proxy)
- 85%以上のリソース削減

**アーキテクチャの比較:**

| 機能 | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| デプロイ | PodごとのEnvoy Injection | Nodeごとに1つのztunnel |
| リソース使用量 | 高い (Podごとに50-100MB) | 低い (Nodeごとに50MB) |
| デプロイの複雑さ | 高い (再デプロイが必要) | 低い (透過的なアプリケーション) |
| L4機能 | サポート | ztunnel経由でサポート |
| L7機能 | 完全サポート | waypointが必要 |
| パフォーマンス | やや低速 | 高速 (L4のみ) |

**Ambient Modeの有効化:**
```bash
# Install Ambient Mode
istioctl install --set profile=ambient -y

# Enable Ambient Mode on Namespace
kubectl label namespace default istio.io/dataplane-mode=ambient
```

**ユースケース:**
- リソース制約のある環境
- 大規模クラスタ (1000以上のPod)
- L4機能のみが必要な場合
- 段階的なIstio導入
</details>

## 問題 8: レジリエンスパターン

<details>
<summary>IstioにおけるOutlier Detection、Circuit Breaker、Rate Limitingの違いは何ですか？</summary>

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

**3. Rate Limiting - リクエストレート制御:**
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
- **Outlier Detection**: 事後対応型 (障害発生後に除外)
- **Circuit Breaker**: 予防型 (接続数を制限)
- **Rate Limiting**: リクエストレート制御 (トークンバケット)

**組み合わせて使用:**
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
<summary>IstioのLocality Load Balancing機能とは何ですか。また、AWS EKSでどのように使用しますか？</summary>

**回答:**
**Locality Load Balancingの概念:**
- 同一Availability Zone (AZ) 内のServiceへの優先ルーティング
- ネットワークレイテンシーの削減
- クロスAZデータ転送コストの削減 (約85%)

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

**AWS EKSでの使用:**
1. **コスト削減:**
   - クロスAZトラフィック: $0.01/GB
   - 同一AZトラフィック: 無料
   - 80%の同一AZルーティングによる大幅なコスト削減

2. **パフォーマンス改善:**
   - AZ内レイテンシー: 約1ms
   - クロスAZレイテンシー: 約2-3ms

3. **自動フェイルオーバー:**
   - AZ障害時に他のAZへ自動フェイルオーバー
   - Outlier Detectionと組み合わせて使用

**Podトポロジー設定:**
```yaml
# EKS nodes automatically set topology labels
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```
</details>

## 問題 10: Amazon EKSとの統合とベストプラクティス

<details>
<summary>Istio 1.28.0をAmazon EKS 1.34と統合する際の考慮事項とベストプラクティスは何ですか？</summary>

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

**2. AWS Load Balancer統合:**
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

**4. セキュリティ設定:**
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

**5. モニタリング統合:**
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
- production profileを使用
- Control Plane HA (replica >= 3)
- mTLS STRICTモード
- PodDisruptionBudgetの設定
- Locality Load Balancingを有効化
- Prometheus + Grafanaによるモニタリング
- 定期的なバージョンアップグレード (Canaryアプローチ)

**7. コスト最適化:**
- Ambient Modeを検討 (85%のリソース削減)
- Locality Load Balancing (クロスAZコスト削減)
- Sidecar Scopeの制限 (30-50%のメモリ削減)
</details>

## ボーナス問題: Progressive Delivery

<details>
<summary>Istio + Argo Rolloutsで完全に自動化されたProgressive Deliveryをどのように実装しますか？</summary>

**回答:**
Progressive Deliveryは、メトリクスに基づいてDeploymentを自動的に進行またはロールバックするアプローチです。

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
- 完全自動化 (人の介入が不要)
- 即時ロールバック (障害検出から数秒以内)
- 安全なDeployment (メトリクスベースの検証)
- 一貫したプロセス (標準化)
</details>

---

**採点:**
- 10-11問正解: 優秀 (Istioエキスパートレベル)
- 8-9問正解: 良好 (本番運用が可能)
- 6-7問正解: 平均 (追加学習を推奨)
- 4-5問正解: 不十分 (基本概念の復習が必要)
- 0-3問正解: 再学習が必要

**学習リソース:**
- [Istio公式ドキュメント](https://istio.io/latest/docs/)
- [Argo Rolloutsドキュメント](https://argo-rollouts.readthedocs.io/)
- [EKS Workshop - Istio](https://www.eksworkshop.com/docs/security/servicemesh/)
- [このガイドの詳細ドキュメント](../../service-mesh/istio/)
