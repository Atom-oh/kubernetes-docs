# Istioのベストプラクティス

このドキュメントでは、本番環境でIstioを正常に運用するためのベストプラクティスと推奨事項について説明します。

## 目次

1. [パフォーマンスの最適化](#performance-optimization)
2. [セキュリティ強化](#security-hardening)
3. [運用ガイド](#operations-guide)
4. [モニタリングと可観測性](#monitoring-and-observability)
5. [本番環境チェックリスト](#production-checklist)

## パフォーマンスの最適化

### 1. Control Planeリソースの最適化

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
          limits:
            cpu: 1000m
            memory: 4Gi
        hpaSpec:
          minReplicas: 2
          maxReplicas: 5
          metrics:
          - type: Resource
            resource:
              name: cpu
              target:
                type: Utilization
                averageUtilization: 80
```

**推奨事項**:
- Istiodには少なくとも2つのレプリカを設定する必要があります
- CPU: クラスターのサイズに基づいて調整します
- Memory: Serviceあたり約10KBと見積もります

### 2. Data Planeリソースの最適化

```yaml
apiVersion: v1
kind: Pod
metadata:
  annotations:
    # Sidecar resource optimization
    sidecar.istio.io/proxyCPU: "100m"
    sidecar.istio.io/proxyMemory: "128Mi"
    sidecar.istio.io/proxyCPULimit: "200m"
    sidecar.istio.io/proxyMemoryLimit: "256Mi"
spec:
  containers:
  - name: myapp
    image: myapp:latest
```

**推奨事項**:
- 通常のワークロード: CPU 100m、Memory 128Mi
- 高トラフィックのワークロード: CPU 500m、Memory 512Mi
- Sidecarの同時実行数: `concurrency: 2`（デフォルト）

### 3. Connection Poolの最適化

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: optimized-pool
spec:
  host: myapp
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30ms
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
        maxRequestsPerConnection: 2
        idleTimeout: 300s
```

**推奨事項**:
- `maxConnections`: ワークロードの同時接続数を考慮します
- `maxRequestsPerConnection`: HTTP/1.1では1～2、HTTP/2ではより高い値にします
- `idleTimeout`: 長時間接続が必要な場合は増やします

### 4. Locality Load Balancing

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: locality-lb
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80  # Same AZ priority
            "us-east-1/us-east-1b/*": 20
```

**利点**:
- クロスAZコストの削減（約85%）
- ネットワークレイテンシーの削減
- アベイラビリティーゾーン障害の自動処理

### 5. Sidecarスコープの制限

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "default/*"
    - "istio-system/*"
```

**利点**:
- Envoy設定サイズの削減
- Memory使用量の削減
- 設定プッシュの高速化

## セキュリティ強化

### 1. Strict mTLSの適用

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # STRICT recommended for production
```

**チェックリスト**:
- すべてのServiceにSTRICT mTLSを適用する
- PERMISSIVEは移行期間中のみ使用する
- 外部ServiceにはDISABLEを使用する（ServiceEntryで処理する）

### 2. Authorization Policy

```yaml
# Deny by default
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # Deny all requests
---
# Allow specific
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
```

**ベストプラクティス**:
- デフォルト拒否ポリシーを使用する
- 最小権限の原則を適用する
- Service Accountベースの認証を使用する
- Namespaceを分離する

### 3. Egressトラフィック制御

```yaml
# Block external traffic
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    outboundTrafficPolicy:
      mode: REGISTRY_ONLY  # Allow only explicit ServiceEntries
---
# Allowed external services
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 4. JWT認証

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[iss]
      values: ["https://auth.example.com"]
```

## 運用ガイド

### 1. Deployment戦略

#### 段階的なIstio導入

```mermaid
flowchart LR
    Start[Start]
    Phase1[Phase 1<br/>Observability]
    Phase2[Phase 2<br/>mTLS PERMISSIVE]
    Phase3[Phase 3<br/>mTLS STRICT]
    Phase4[Phase 4<br/>Advanced Features]
    End[Full Adoption]

    Start --> Phase1
    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> End

    %% Style definition
    classDef phase fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Class application
    class Start,Phase1,Phase2,Phase3,Phase4,End phase;
```

**フェーズ1: 可観測性（1～2週間）**
```bash
# Enable sidecar injection only
kubectl label namespace default istio-injection=enabled

# Verify metrics, logs, traces
# Evaluate performance impact
```

**フェーズ2: mTLS PERMISSIVE（1～2週間）**
```yaml
# Enable PERMISSIVE mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: PERMISSIVE
```

**フェーズ3: mTLS STRICT（1週間）**
```yaml
# Switch to STRICT mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**フェーズ4: 高度な機能（継続的）**
- Traffic Management（Canary、Circuit Breaker）
- Authorization Policy
- Rate Limiting

### 2. アップグレード戦略

#### Canaryアップグレード

```bash
# 1. Install new version Control Plane
istioctl install --set revision=1-28-0 -y

# 2. Move test namespace
kubectl label namespace test istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n test

# 3. Move production after verification
kubectl label namespace prod istio.io/rev=1-28-0 --overwrite
kubectl rollout restart deployment -n prod

# 4. Remove previous version
istioctl uninstall --revision=1-27-0 -y
```

### 3. 高可用性

```yaml
# Control Plane HA
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        replicaCount: 3
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: istiod
            topologyKey: kubernetes.io/hostname
```

**推奨事項**:
- Istiod: 最低3レプリカ
- AZ全体に均等に分散する
- PodDisruptionBudgetを設定する

### 4. バックアップとリカバリ

```bash
# Backup Istio configuration
kubectl get istiooperator -A -o yaml > istio-operator-backup.yaml
kubectl get vs,dr,gw,se,pa,ra,ap -A -o yaml > istio-config-backup.yaml

# Recovery
kubectl apply -f istio-operator-backup.yaml
kubectl apply -f istio-config-backup.yaml
```

## モニタリングと可観測性

### 1. Golden Signals

```promql
# 1. Latency (P50, P95, P99)
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
)

# 2. Traffic (Request count)
sum(rate(istio_requests_total[5m]))

# 3. Errors (Error rate)
sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
/
sum(rate(istio_requests_total[5m]))

# 4. Saturation (Resource utilization)
sum(rate(container_cpu_usage_seconds_total{pod=~".*istio-proxy.*"}[5m]))
```

### 2. Control Planeのモニタリング

```promql
# Pilot configuration push time
pilot_proxy_convergence_time

# xDS connection count
pilot_xds_pushes

# Memory usage
process_resident_memory_bytes{app="istiod"}
```

### 3. Data Planeのモニタリング

```promql
# Envoy connection count
envoy_cluster_upstream_cx_active

# Circuit Breaker open
envoy_cluster_circuit_breakers_default_rq_open

# Outlier Detection
envoy_cluster_outlier_detection_ejections_active
```

### 4. アラートルール

```yaml
groups:
- name: istio
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: |
      (sum(rate(istio_requests_total{response_code=~"5.."}[5m]))
      /
      sum(rate(istio_requests_total[5m]))) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  # High latency
  - alert: HighLatency
    expr: |
      histogram_quantile(0.95,
        sum(rate(istio_request_duration_milliseconds_bucket[5m])) by (le)
      ) > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High latency detected (P95 > 1s)"

  # Pilot not ready
  - alert: PilotNotReady
    expr: up{job="pilot"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Pilot is not ready"
```

## 本番環境チェックリスト

### インストール前

- [ ] Kubernetesバージョンの互換性を確認する（1.28+）
- [ ] Istioバージョンを選択する（安定版を推奨）
- [ ] リソース要件を計算する
- [ ] ネットワークポリシーを確認する
- [ ] バックアップおよびリカバリ計画を策定する

### インストール

- [ ] 本番プロファイルを使用する
- [ ] Control Plane HAを構成する（レプリカ数 >= 3）
- [ ] リソース制限を設定する
- [ ] PodDisruptionBudgetを設定する
- [ ] モニタリングスタックを準備する

### セキュリティ

- [ ] mTLS STRICTモードを有効にする
- [ ] Authorization Policyを適用する
- [ ] Egressトラフィックを制御する
- [ ] JWT認証を構成する（必要な場合）
- [ ] Network Policyを統合する

### Traffic Management

- [ ] VirtualServiceを構成する
- [ ] DestinationRuleを構成する
- [ ] Circuit Breakerを設定する
- [ ] Retry/Timeoutを設定する
- [ ] Rate Limitingを構成する

### 可観測性

- [ ] Prometheusを統合する
- [ ] Grafanaダッシュボードを設定する
- [ ] Jaeger/Zipkinトレーシングを設定する
- [ ] Kialiをインストールする
- [ ] アラートルールを設定する

### 運用

- [ ] アップグレード計画を策定する
- [ ] バックアップを自動化する
- [ ] ドキュメントを作成する
- [ ] オンコールガイドを作成する
- [ ] ランブックを準備する

### パフォーマンス

- [ ] Sidecarリソースを最適化する
- [ ] Connection Poolをチューニングする
- [ ] Locality Load Balancingを構成する
- [ ] Sidecarスコープを制限する
- [ ] パフォーマンステストを実施する

### テスト

- [ ] 機能テスト
- [ ] パフォーマンステスト
- [ ] ディザスターリカバリテスト
- [ ] カオスエンジニアリング
- [ ] アップグレードシナリオテスト

## よくあるアンチパターン

### 避けるべきこと

1. **一度にすべてを導入すること**
   ```
   Don't enable all Istio features on Day 1
   Do add features gradually (Observability -> Security -> Traffic Management)
   ```

2. **リソース制限を設定しないこと**
   ```yaml
   Don't leave Sidecar without resource limits
   Do set appropriate requests/limits
   ```

3. **PERMISSIVEモードを長期間使用すること**
   ```
   Don't keep using PERMISSIVE
   Do transition to STRICT quickly
   ```

4. **ワイルドカード一致の乱用**
   ```yaml
   Don't: hosts: ["*"]  # All services
   Do: hosts: ["myapp.default.svc.cluster.local"]  # Explicit
   ```

5. **モニタリングなしでデプロイすること**
   ```
   Don't deploy to production without checking metrics
   Do require Golden Signals monitoring
   ```

## コスト最適化

### 1. Ambient Modeを検討する

```yaml
# Resource usage comparison
# Sidecar Mode: 100 pods x 50MB = 5GB
# Ambient Mode: 10 nodes x 50MB = 500MB

# 85%+ reduction possible
```

### 2. Locality Load Balancing

```yaml
# Cross-AZ cost savings
# AWS: $0.01-0.02 per GB
# Significant savings with 80% same AZ routing
```

### 3. Sidecarスコープの制限

```yaml
# Remove unnecessary configuration
# 30-50% memory usage reduction possible
```

## 参考資料

### 公式ドキュメント
- [Istio Best Practices](https://istio.io/latest/docs/ops/best-practices/)
- [Performance and Scalability](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)

### コミュニティ
- [Istio Discuss](https://discuss.istio.io/)
- [Istio Slack](https://istio.slack.com/)
- [GitHub Issues](https://github.com/istio/istio/issues)

### 追加リソース
- [Istio in Production](https://www.tetrate.io/blog/istio-in-production/)
- [Service Mesh Patterns](https://www.oreilly.com/library/view/service-mesh-patterns/9781492086444/)
