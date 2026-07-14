# Flagger プログレッシブデリバリー

> **サポート対象バージョン**: Flagger v1.38+, Flux v2.4+
> **最終更新**: June 2025

Flagger は Kubernetes 向けのプログレッシブデリバリー operator であり、Service Mesh ルーティング、Ingress Controller、または Gateway API を使用したトラフィックシフトと、canary 分析用の Prometheus メトリクスにより、canary Deployment の昇格を自動化します。元々 Weaveworks によって作成され、現在は Flux ファミリーの CNCF プロジェクトである Flagger は、主要業績評価指標を測定しながら新バージョンへ段階的にトラフィックを移行し、異常が検出された場合は自動的にロールバックすることで、本番環境への新しいソフトウェアバージョン導入のリスクを低減します。

## 目次

- [概要と学習目標](#overview-and-learning-objectives)
- [Flagger アーキテクチャ](#flagger-architecture)
- [EKS のインストールと設定](#eks-installation-and-configuration)
- [Canary Deployment 戦略](#canary-deployment-strategy)
- [Blue-Green Deployment 戦略](#blue-green-deployment-strategy)
- [A/B テスト戦略](#ab-testing-strategy)
- [カスタムメトリクスと Webhook](#custom-metrics-and-webhooks)
- [GitOps 統合（Flux + Flagger）](#gitops-integration-flux--flagger)
- [可観測性とアラート](#observability-and-alerting)
- [本番環境のベストプラクティス](#production-best-practices)
- [参考資料](#references)

---

## 概要と学習目標

### 学習目標

このドキュメントを完了すると、以下のことができるようになります。

1. プログレッシブデリバリー戦略（Canary、Blue-Green、A/B Testing）とそれぞれを使用するタイミングを説明する
2. さまざまな mesh および ingress provider を使用して、Amazon EKS 上に Flagger をデプロイおよび設定する
3. カスタムメトリクス分析と自動ロールバック条件を備えた Canary リソースを定義する
4. トラフィックミラーリングと手動ゲートを備えた Blue-Green Deployment を実装する
5. ヘッダーベースおよび Cookie ベースのルーティングによる A/B Testing を設定する
6. 完全に自動化された GitOps プログレッシブデリバリー pipeline のために Flagger を FluxCD と統合する
7. Flagger Deployment 用の可観測性ダッシュボードとアラートを設定する

### プログレッシブデリバリーとは？

プログレッシブデリバリーは、変更をユーザーベース全体に提供する前に、ユーザーの一部に対して制御された段階的なロールアウトを可能にする高度な Deployment 戦略の総称です。すべての Pod を同時に置き換える従来の rolling update とは異なり、プログレッシブデリバリーはトラフィック分散、リアルタイム分析、自動ロールバックをきめ細かく制御できます。

主なプログレッシブデリバリー戦略は次の 3 つです。

| 戦略 | トラフィック制御 | ユースケース | 複雑さ |
|----------|----------------|----------|------------|
| **Canary** | パーセンテージベースの weight シフト | 汎用的で段階的なロールアウト | 中 |
| **Blue-Green** | 2 つの環境間の完全切り替え | ダウンタイムゼロ、即時ロールバック | 低 |
| **A/B Testing** | ヘッダー/Cookie ベースのルーティング | 特定のユーザーセグメントでの機能テスト | 高 |

### Flagger と Argo Rollouts の比較

Flagger と Argo Rollouts はいずれも Kubernetes 向けのプログレッシブデリバリーという課題を解決しますが、そのアプローチは根本的に異なります。

| 機能 | Flagger | Argo Rollouts |
|---------|---------|---------------|
| **エコシステム** | Flux / CNCF | Argo / CNCF |
| **リソースモデル** | ネイティブの Deployment/DaemonSet をラップ | Deployment を Rollout CRD に置き換え |
| **トラフィック Provider** | Istio、Linkerd、Contour、Nginx、Gateway API、AWS App Mesh、Gloo、Traefik | Istio、Nginx、ALB、SMI、Gateway API |
| **メトリクス分析** | 組み込みの Prometheus、Datadog、CloudWatch、カスタム Webhook | 複数 provider に対応する組み込み AnalysisTemplate |
| **GitOps 統合** | ネイティブの Flux 統合 | ネイティブの Argo CD 統合 |
| **Webhook サポート** | pre/post-rollout、rollout、confirm-rollout、load-test | pre/post analysis、anti-affinity |
| **Blue-Green** | Canary CRD によりサポート | ファーストクラスの Rollout 戦略 |
| **A/B Testing** | ヘッダーを備えた Canary CRD によりサポート | Experiment CRD によりサポート |
| **CNCF ステータス** | Incubating（Flux ファミリー） | Graduated（Argo ファミリー） |
| **採用パターン** | 追加型（Deployment の変更なし） | 置換型（Rollout が Deployment を置き換え） |

**主な差別化要因**: Flagger では、既存の Deployment リソースを変更する必要がありません。primary と canary の CloneSet バリアントを自動的に作成し、mesh/ingress レイヤーを通じてトラフィックシフトを管理します。Argo Rollouts では、`Deployment` kind を `Rollout` kind に置き換える必要があります。

### Flux エコシステムにおける Flagger

Flagger は、Flux GitOps toolkit のプログレッシブデリバリーコンポーネントとして設計されています。

```mermaid
graph TB
    subgraph "Flux GitOps Toolkit"
        SC["Source Controller<br/>(Git, Helm, OCI)"]
        KC["Kustomize Controller"]
        HC["Helm Controller"]
        NC["Notification Controller"]
        IAC["Image Automation<br/>Controller"]
        FL["Flagger<br/>(Progressive Delivery)"]
    end

    subgraph "External Systems"
        GIT[("Git Repository")]
        PROM["Prometheus"]
        MESH["Service Mesh /<br/>Ingress Controller"]
    end

    subgraph "Kubernetes Cluster"
        DEP["Deployments"]
        SVC["Services"]
        VS["VirtualServices /<br/>HTTPRoutes"]
    end

    GIT --> SC
    SC --> KC
    SC --> HC
    KC --> DEP
    HC --> DEP
    IAC --> GIT

    FL -->|"Watches"| DEP
    FL -->|"Queries"| PROM
    FL -->|"Manages"| SVC
    FL -->|"Manages"| VS
    NC -->|"Alerts"| FL

    classDef flux fill:#5468FF,stroke:#333,color:white
    classDef ext fill:#FF9900,stroke:#333,color:white
    classDef k8s fill:#326CE5,stroke:#333,color:white

    class SC,KC,HC,NC,IAC,FL flux
    class GIT,PROM,MESH ext
    class DEP,SVC,VS k8s
```

---

## Flagger アーキテクチャ

### 制御ループ

Flagger は、メトリクスを分析し、conformance test を実行し、トラフィックルーティングを管理することで、アプリケーションの新バージョンを段階的に進める制御ループを実装します。コアの reconciliation ループは次のとおりです。

```mermaid
stateDiagram-v2
    [*] --> Initialized: Canary created
    Initialized --> Progressing: Deployment change detected
    Progressing --> WaitingPromotion: All steps passed
    Progressing --> Progressing: Advance step<br/>(increase weight)
    Progressing --> Failed: Metrics check failed<br/>or threshold exceeded
    WaitingPromotion --> Promoting: Auto or manual gate
    WaitingPromotion --> Failed: Timeout exceeded
    Promoting --> Finalising: Traffic shifted to primary
    Finalising --> Succeeded: Primary updated, canary scaled down
    Failed --> Initialized: Rollback complete
    Succeeded --> Initialized: Waiting for next change
```

### 詳細な制御ループのステップ

対象 workload（例: 新しい container image）で変更が検出されると、Flagger は次のシーケンスを実行します。

1. **変更の検出**: Flagger は対象 Deployment の spec 変更（image tag、環境変数、リソースなど）を監視します
2. **Canary の初期化**: 新バージョンで canary Deployment をスケールアップし、primary は旧バージョンを維持します
3. **Pre-Rollout Webhook の実行**: conformance test、smoke test、その他の事前条件を実行します
4. **トラフィックのシフト**: `stepWeight` と `maxWeight` に従って canary のトラフィック weight を段階的に増やします
5. **メトリクスの分析**: Prometheus（または他の provider）に成功率、レイテンシ、カスタムメトリクスを問い合わせます
6. **前進またはロールバック**: メトリクスがしきい値を満たす場合は次のステップへ進み、それ以外の場合はロールバックを開始します
7. **昇格の確認**: 必要に応じて Webhook による手動ゲート承認を待機します
8. **昇格**: canary spec を primary にコピーし、canary をスケールダウンして、すべてのトラフィックを primary にルーティングします
9. **通知の送信**: Slack、Teams、その他の設定済み provider を通じてアラートを送信します

### Mesh および Ingress Provider のサポート

Flagger は幅広いトラフィック管理 provider をサポートしており、それぞれで利用可能な機能が異なります。

| Provider | Canary | Blue-Green | A/B Testing | ミラーリング | Gateway API |
|----------|--------|------------|-------------|-----------|-------------|
| **Istio** | Yes | Yes | Yes | Yes | Yes |
| **Linkerd** | Yes | Yes | No | No | Yes |
| **AWS App Mesh** | Yes | Yes | No | No | No |
| **Contour** | Yes | Yes | Yes | No | Yes |
| **Nginx Ingress** | Yes | Yes | Yes | No | No |
| **Gloo Edge** | Yes | Yes | No | No | No |
| **Traefik** | Yes | Yes | No | No | No |
| **Gateway API** | Yes | Yes | Yes | No | Yes |
| **Kuma** | Yes | Yes | No | No | No |
| **Open Service Mesh** | Yes | Yes | No | No | No |

### Prometheus メトリクス分析

Flagger のメトリクス分析 engine は Prometheus にクエリを実行して、canary リリースが健全かどうかを評価します。組み込みメトリクスは次の 2 つです。

- **request-success-rate**: 分析 interval における成功した HTTP request（5xx 以外）の割合
- **request-duration**: 分析 interval における HTTP request の P99 レイテンシ

どちらのメトリクスも、Service Mesh または Ingress Controller の Prometheus メトリクス（例: `istio_requests_total`、`istio_request_duration_milliseconds_bucket`）から取得されます。

```mermaid
sequenceDiagram
    participant F as Flagger
    participant P as Prometheus
    participant M as Mesh/Ingress
    participant C as Canary Pod

    F->>M: Set canary weight (e.g., 10%)
    M->>C: Route 10% traffic to canary
    Note over C: Handle requests
    C->>M: Return responses
    M->>P: Report metrics<br/>(latency, status codes)
    F->>P: Query: request-success-rate?
    P-->>F: 99.5% (threshold: 99%)
    F->>P: Query: request-duration P99?
    P-->>F: 250ms (threshold: 500ms)
    F->>F: All checks passed
    F->>M: Advance: set weight to 20%
```

---

## EKS のインストールと設定

### 前提条件

Amazon EKS に Flagger をインストールする前に、次の前提条件を満たしていることを確認してください。

- Kubernetes v1.27+ を実行している Amazon EKS cluster
- インストール済みの Helm v3.12+
- デプロイ済みの Service Mesh（Istio）または Ingress Controller（Nginx、Contour）
- デプロイ済みの Prometheus stack（kube-prometheus-stack を推奨）
- bootstrapped 済みの FluxCD v2.4+（GitOps 統合用）

### Prometheus を使用する Helm インストール

Prometheus metrics server を有効にして Helm で Flagger をインストールします。

```bash
# Add Flagger Helm repository
helm repo add flagger https://flagger.app
helm repo update

# Install Flagger with Prometheus metrics server
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  --set meshProvider=istio \
  --set metricsServer=http://prometheus-kube-prometheus-prometheus.monitoring:9090 \
  --set prometheus.install=true
```

IRSA（IAM Roles for Service Accounts）を使用する EKS では、Service Account を設定します。

```yaml
# flagger-values.yaml
meshProvider: istio
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

serviceAccount:
  create: true
  name: flagger
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/FlaggerRole

prometheus:
  install: true
  retention: 2h

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 1000m
    memory: 512Mi

# Enable leader election for HA
leaderElection:
  enabled: true
  replicaCount: 2
```

```bash
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  -f flagger-values.yaml
```

### Flagger Loadtester のインストール

Flagger loadtester は、canary 分析中に自動化された load test と Webhook を実行するためのコンパニオンツールです。

```bash
helm upgrade -i flagger-loadtester flagger/loadtester \
  --namespace flagger-system \
  --set cmd.timeout=1h \
  --set resources.requests.cpu=100m \
  --set resources.requests.memory=64Mi
```

### Istio Provider の設定

Istio を mesh provider として使用する場合、Flagger は VirtualService および DestinationRule リソースを自動的に管理します。

```yaml
# flagger-values-istio.yaml
meshProvider: istio
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

# Istio-specific settings
istio:
  # The Istio ingress gateway name
  gateway: istio-system/public-gateway

# Namespace selector for Flagger to watch
namespace: ""  # Empty means all namespaces

# Log level
logLevel: info
```

対象 namespace に対して Istio sidecar injection が有効になっていることを確認します。

```bash
kubectl label namespace production istio-injection=enabled
kubectl get namespace production --show-labels
```

### Gateway API Provider の設定

Flagger は provider として Kubernetes Gateway API をサポートしており、完全な Service Mesh なしでプログレッシブデリバリーを実現できます。

```yaml
# flagger-values-gatewayapi.yaml
meshProvider: gatewayapi
metricsServer: http://prometheus-kube-prometheus-prometheus.monitoring:9090

# Gateway API specific configuration
gatewayApi:
  # Reference to the Gateway resource
  gateway: istio-system/main-gateway
```

```bash
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --create-namespace \
  -f flagger-values-gatewayapi.yaml
```

Flagger が参照する Gateway リソースを作成します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: istio-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    port: 80
    protocol: HTTP
    allowedRoutes:
      namespaces:
        from: All
  - name: https
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-secret
    allowedRoutes:
      namespaces:
        from: All
```

### Slack および Teams の通知設定

Flagger は AlertProvider CRD を使用して、Slack、Microsoft Teams、その他の provider に Deployment 通知を送信できます。

```yaml
# Slack AlertProvider
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack
  namespace: production
spec:
  type: slack
  channel: deployments
  username: flagger
  # Webhook URL stored in a Kubernetes Secret
  secretRef:
    name: slack-webhook
---
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: production
stringData:
  address: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

```yaml
# Microsoft Teams AlertProvider
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: msteams
  namespace: production
spec:
  type: msteams
  secretRef:
    name: msteams-webhook
---
apiVersion: v1
kind: Secret
metadata:
  name: msteams-webhook
  namespace: production
stringData:
  address: https://outlook.office.com/webhook/XXXXXXXX
```

Canary リソースでは複数の alert provider を参照できます。

```yaml
spec:
  analysis:
    alerts:
    - name: "slack-notification"
      severity: info
      providerRef:
        name: slack
        namespace: production
    - name: "teams-notification"
      severity: error
      providerRef:
        name: msteams
        namespace: production
```

---

## Canary Deployment 戦略

### Canary CRD の詳細な説明

Canary CRD は、プログレッシブデリバリー戦略を定義する Flagger の主要リソースです。対象 Deployment を参照し、トラフィックのシフト方法、分析するメトリクス、ロールバックのタイミングを指定します。

**Canary リソースのコア構造:**

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: app-name
  namespace: production
spec:
  # ---- Target Reference ----
  targetRef:              # The Deployment to manage
  autoscalerRef:          # Optional HPA/KEDA reference
  ingressRef:             # Optional Ingress reference
  
  # ---- Service Configuration ----
  service:                # Service mesh / ingress settings
  
  # ---- Analysis Configuration ----
  analysis:               # Metrics, webhooks, alerts
  
  # ---- Promotion Policy ----
  progressDeadlineSeconds: 600
  skipAnalysis: false
```

### 段階的なトラフィックシフト

Flagger は 2 つの主要パラメータを使用して canary のトラフィックシフトを管理します。

- **`stepWeight`**: 各分析 interval で canary に追加するトラフィックの割合
- **`maxWeight`**: 昇格前に canary が受信するトラフィックの最大割合

たとえば、`stepWeight: 10` と `maxWeight: 50` の場合:

```
Step 1: Canary 10%, Primary 90%  ->  Analyze metrics
Step 2: Canary 20%, Primary 80%  ->  Analyze metrics
Step 3: Canary 30%, Primary 70%  ->  Analyze metrics
Step 4: Canary 40%, Primary 60%  ->  Analyze metrics
Step 5: Canary 50%, Primary 50%  ->  Analyze metrics
Step 6: Promote -> Canary spec copied to Primary, all traffic to Primary
```

```mermaid
graph LR
    subgraph "Traffic Shifting Progress"
        S1["Step 1<br/>10%"] --> S2["Step 2<br/>20%"]
        S2 --> S3["Step 3<br/>30%"]
        S3 --> S4["Step 4<br/>40%"]
        S4 --> S5["Step 5<br/>50%"]
        S5 --> PROMOTE["Promote<br/>100%"]
    end

    subgraph "At Each Step"
        METRIC1["Check: request-success-rate<br/>>= 99%"]
        METRIC2["Check: request-duration P99<br/><= 500ms"]
        WH["Run: webhooks<br/>(load test, conformance)"]
    end

    S3 -.->|"Analyze"| METRIC1
    S3 -.->|"Analyze"| METRIC2
    S3 -.->|"Execute"| WH

    classDef step fill:#28a745,stroke:#333,color:white
    classDef check fill:#ffc107,stroke:#333,color:black
    classDef promote fill:#5468FF,stroke:#333,color:white

    class S1,S2,S3,S4,S5 step
    class METRIC1,METRIC2,WH check
    class PROMOTE promote
```

`stepWeights`（配列）を使用して、非線形のトラフィックステップを定義することもできます。

```yaml
analysis:
  stepWeights: [1, 2, 5, 10, 25, 50, 80]
  # Traffic progression: 1% -> 2% -> 5% -> 10% -> 25% -> 50% -> 80% -> promote
```

### メトリクス分析

Flagger の組み込みメトリクスは、Service Mesh または Ingress Controller が Prometheus メトリクスを公開することに依存します。

```yaml
analysis:
  metrics:
  # Built-in metric: request success rate
  - name: request-success-rate
    # Minimum percentage of successful (non-5xx) requests
    thresholdRange:
      min: 99
    interval: 1m

  # Built-in metric: request duration (latency)
  - name: request-duration
    # Maximum P99 latency in milliseconds
    thresholdRange:
      max: 500
    interval: 1m
```

`interval` フィールドは、各分析ステップ中に Flagger が Prometheus へクエリする頻度を決定します。`thresholdRange` は許容範囲を指定します。

- `min`: メトリクス値はこの値**以上**である必要があります（例: 成功率 >= 99%）
- `max`: メトリクス値はこの値**以下**である必要があります（例: レイテンシ <= 500ms）

### 自動ロールバック条件

Flagger は、次の場合に canary Deployment を自動的にロールバックします。

1. **メトリクス失敗しきい値の超過**: 分析ステップ内でメトリクスチェックが `threshold` 回を超えて失敗した場合
2. **進行期限の超過**: canary が `progressDeadlineSeconds` 内に進行しない場合
3. **Webhook の失敗**: pre-rollout または rollout Webhook が 2xx 以外の status を返した場合

```yaml
analysis:
  # Number of consecutive metric check failures before rollback
  threshold: 5
  
  # Maximum number of failed metric checks before rollback
  # (across all steps, not just consecutive)
  maxWeight: 50
  
  # Analysis interval
  interval: 1m
  
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99
    interval: 1m
  - name: request-duration
    thresholdRange:
      max: 500
    interval: 1m
```

ロールバックが発生すると、Flagger は次を実行します。
1. すべてのトラフィックを primary（旧バージョン）へ戻す
2. canary をゼロまでスケールダウンする
3. Canary status を `Failed` に設定する
4. アラート通知を送信する

### 完全な Canary YAML の例

以下は、Istio を使用して EKS 上にデプロイされた Web アプリケーション向けの、本番環境対応 Canary リソースです。

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  # Reference to the target Deployment
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  # Reference to the HPA (optional, Flagger will manage scaling)
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app

  # Maximum time in seconds for the canary to progress
  progressDeadlineSeconds: 600

  service:
    # Container port
    port: 8080
    # Port name (must match Istio conventions)
    portName: http
    # Target port on the container
    targetPort: 8080
    # Istio gateway references
    gateways:
    - istio-system/public-gateway
    # Hostnames
    hosts:
    - app.example.com
    # Istio traffic policy
    trafficPolicy:
      tls:
        mode: ISTIO_MUTUAL
    # Retries
    retries:
      attempts: 3
      perTryTimeout: 1s
      retryOn: "gateway-error,connect-failure,refused-stream"

  analysis:
    # Analysis interval
    interval: 1m
    # Number of analysis cycles before promotion
    iterations: 10
    # Max traffic weight shifted to canary
    maxWeight: 50
    # Traffic weight step
    stepWeight: 10
    # Number of failed checks before rollback
    threshold: 5

    # Prometheus metrics
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    # Webhooks for load testing and conformance
    webhooks:
    - name: smoke-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: bash
        cmd: "curl -sd 'test' http://web-app-canary.production:8080/healthz | grep ok"

    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"

    # Alert providers
    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

この Canary リソースは次を実行します。
1. `web-app` Deployment の変更を監視する
2. `web-app-primary` および `web-app-canary` Deployment を作成する
3. `web-app`、`web-app-primary`、`web-app-canary` ClusterIP Service を作成する
4. トラフィックルーティング用の Istio VirtualService を作成する
5. rollout 開始前に smoke test を実行する
6. トラフィックを 10% ずつ 50% までシフトする
7. 各分析ステップ中に load test を実行する
8. request の成功率（>= 99%）と P99 レイテンシ（<= 500ms）を確認する
9. 連続する 5 回のメトリクスチェックが失敗した場合にロールバックする
10. すべてのステップが成功した後、canary spec を primary にコピーして昇格する

**canary Deployment の監視:**

```bash
# Watch Canary status
kubectl get canaries -n production -w

# Describe the Canary for detailed events
kubectl describe canary web-app -n production

# Check Flagger logs
kubectl logs -n flagger-system deploy/flagger -f | jq

# Trigger a canary deployment by updating the image
kubectl set image deployment/web-app web-app=myregistry/web-app:v2.0.0 -n production
```

---

## Blue-Green Deployment 戦略

### Blue-Green Canary CRD

Flagger は、同じ Canary CRD を通じて Blue-Green Deployment をサポートします。`stepWeight` と `maxWeight` を省略し、`iterations` を使用して、旧（blue）バージョンから新（green）バージョンへトラフィックを切り替える前に実行する分析サイクル数を定義します。

Blue-Green モードでは:
- 分析中、canary は live traffic を受信しません（ミラーリングが有効な場合を除く）
- Flagger は load tester またはミラーリングされたトラフィックを使用して、canary に対するメトリクスチェックを実行します
- すべての iteration が成功すると、1 ステップでトラフィックは primary から canary へ 100% 切り替えられます
- いずれかの iteration が失敗した場合、canary は本番トラフィックに影響を与えずにスケールダウンされます

```mermaid
sequenceDiagram
    participant U as Users
    participant P as Primary (Blue)
    participant C as Canary (Green)
    participant F as Flagger
    participant LT as Load Tester

    Note over P: Serving 100% traffic
    F->>C: Deploy new version (Green)
    F->>LT: Run pre-rollout tests
    LT->>C: Synthetic traffic
    LT-->>F: Tests passed

    loop Analysis Iterations
        F->>LT: Generate test traffic
        LT->>C: Synthetic requests
        F->>F: Check metrics (success rate, latency)
        Note over F: Iteration passed
    end

    F->>U: Switch: 100% traffic to Green
    F->>P: Update Primary with Green spec
    F->>C: Scale down canary
    Note over P: Now serving new version
```

### トラフィックのミラーリング

Istio を使用する場合、Flagger は Blue-Green 分析中に本番トラフィックを canary へミラーリングできます。ミラーリングされたトラフィックは fire-and-forget であり、canary からの response は破棄されるため、ユーザーへの影響はゼロです。

```yaml
spec:
  analysis:
    # Number of analysis cycles
    iterations: 10
    # Enable traffic mirroring (Istio only)
    mirror: true
    # Percentage of traffic to mirror (default: 100)
    mirrorWeight: 100
```

### 手動ゲーティング

高リスクの Deployment では、Flagger が canary を昇格する前に手動承認を必須にできます。これは、Flagger が各ステップでクエリする confirm-rollout Webhook を通じて実現します。

```yaml
spec:
  analysis:
    webhooks:
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve
```

手動で承認または拒否するには:

```bash
# Approve the promotion
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget --post-data='{}' -q -O- http://localhost:8080/gate/open/web-app.production

# Reject the promotion (close the gate)
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget --post-data='{}' -q -O- http://localhost:8080/gate/close/web-app.production

# Check gate status
kubectl exec -n flagger-system deploy/flagger-loadtester -- \
  wget -q -O- http://localhost:8080/gate/check/web-app.production
```

### 完全な Blue-Green YAML の例

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app

  progressDeadlineSeconds: 600

  service:
    port: 8080
    portName: http
    targetPort: 8080
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com

  analysis:
    # Blue-Green: use iterations, no stepWeight/maxWeight
    interval: 1m
    iterations: 10
    threshold: 2

    # Mirror production traffic to the canary (Istio only)
    mirror: true
    mirrorWeight: 100

    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    webhooks:
    # Pre-rollout conformance test
    - name: conformance-test
      type: pre-rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 120s
      metadata:
        type: bash
        cmd: "curl -sd 'test' http://web-app-canary.production:8080/healthz | grep ok"

    # Load test for generating metrics
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"

    # Manual gate for production approval
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve

    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

---

## A/B テスト戦略

### ヘッダーおよび Cookie ベースのルーティング

Flagger の A/B Testing は、HTTP ヘッダーまたは Cookie を使用して特定のユーザーを canary バージョンにルーティングします。weighted routing を使用する canary Deployment とは異なり、A/B Testing では request 属性に基づく決定論的なルーティングを保証します。

この戦略は、次の用途に最適です。
- 特定のユーザーセグメントを対象とした feature flag テスト
- request ヘッダーに基づくリージョナルロールアウト
- 公開リリース前の内部テスト
- 特定のユーザーコホートに対するビジネスメトリクス（コンバージョン率、エンゲージメント）の測定

### Istio VirtualService 統合

Istio を使用する場合、Flagger は HTTP ヘッダーまたは Cookie に一致する VirtualService ルールを生成します。

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app

  progressDeadlineSeconds: 600

  service:
    port: 8080
    portName: http
    targetPort: 8080
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com

  analysis:
    interval: 1m
    iterations: 20
    threshold: 5

    # A/B testing match conditions
    # Users matching ANY of these conditions see the canary
    match:
    # Route based on a custom header
    - headers:
        x-canary:
          exact: "insider"
    # Route based on a cookie value
    - headers:
        cookie:
          regex: "^(.*?;)?(canary=always)(;.*)?$"

    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m

    webhooks:
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 5 -c 2 -H 'x-canary: insider' http://web-app-canary.production:8080/"

    alerts:
    - name: "slack"
      severity: info
      providerRef:
        name: slack
        namespace: production
```

生成される Istio VirtualService は次のようになります。

```yaml
# Auto-generated by Flagger
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: web-app
  namespace: production
spec:
  gateways:
  - istio-system/public-gateway
  hosts:
  - app.example.com
  http:
  # A/B test route: matched users go to canary
  - match:
    - headers:
        x-canary:
          exact: "insider"
    - headers:
        cookie:
          regex: "^(.*?;)?(canary=always)(;.*)?$"
    route:
    - destination:
        host: web-app-canary
  # Default route: everyone else goes to primary
  - route:
    - destination:
        host: web-app-primary
```

### メトリクスベースの自動昇格

A/B Testing 中も、Flagger は canary トラフィックのメトリクス分析を実行します。すべてのメトリクスがしきい値内に収まった状態で設定済みの `iterations` 数が成功すると、Flagger は canary を自動的に昇格します。

```bash
# Test A/B routing with header
curl -H "x-canary: insider" http://app.example.com/

# Test A/B routing with cookie
curl -b "canary=always" http://app.example.com/

# Verify routing (should return the canary version)
for i in $(seq 1 10); do
  curl -s -H "x-canary: insider" http://app.example.com/version
done
```

---

## カスタムメトリクスと Webhook

### Prometheus カスタムメトリクスクエリ

2 つの組み込みメトリクスに加えて、Flagger は MetricTemplate CRD を通じてカスタム Prometheus クエリをサポートします。これにより、canary Deployment 中に任意の Prometheus メトリクスを分析できます。

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: error-rate
  namespace: production
spec:
  provider:
    type: prometheus
    address: http://prometheus-kube-prometheus-prometheus.monitoring:9090
  query: |
    100 - sum(
      rate(
        http_requests_total{
          namespace="{{ namespace }}",
          job="{{ target }}-canary",
          status!~"5.*"
        }[{{ interval }}]
      )
    )
    /
    sum(
      rate(
        http_requests_total{
          namespace="{{ namespace }}",
          job="{{ target }}-canary"
        }[{{ interval }}]
      )
    ) * 100
```

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: latency-p95
  namespace: production
spec:
  provider:
    type: prometheus
    address: http://prometheus-kube-prometheus-prometheus.monitoring:9090
  query: |
    histogram_quantile(0.95,
      sum(
        rate(
          http_request_duration_seconds_bucket{
            namespace="{{ namespace }}",
            job="{{ target }}-canary"
          }[{{ interval }}]
        )
      ) by (le)
    )
```

Canary 分析でカスタムメトリクスを参照します。

```yaml
analysis:
  metrics:
  - name: error-rate
    templateRef:
      name: error-rate
      namespace: production
    thresholdRange:
      max: 1
    interval: 1m
  - name: latency-p95
    templateRef:
      name: latency-p95
      namespace: production
    thresholdRange:
      max: 0.5
    interval: 1m
```

### Datadog Metrics Provider

Flagger は外部 metrics provider として Datadog をサポートします。

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: dd-request-duration
  namespace: production
spec:
  provider:
    type: datadog
    secretRef:
      name: datadog-api
  query: |
    avg:trace.http.request.duration{
      service:{{ target }}-canary,
      kube_namespace:{{ namespace }}
    }.rollup(avg, 60)
---
apiVersion: v1
kind: Secret
metadata:
  name: datadog-api
  namespace: production
stringData:
  datadog_api_key: YOUR_DATADOG_API_KEY
  datadog_application_key: YOUR_DATADOG_APP_KEY
  datadog_site: datadoghq.com
```

### CloudWatch Metrics Provider

EKS 上の Amazon CloudWatch メトリクスの場合:

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: cw-error-rate
  namespace: production
spec:
  provider:
    type: cloudwatch
    region: us-west-2
  query: |
    [
      {
        "Id": "e1",
        "Expression": "m1 / m2 * 100",
        "Label": "ErrorRate"
      },
      {
        "Id": "m1",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "5xxErrors",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}-canary"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      },
      {
        "Id": "m2",
        "MetricStat": {
          "Metric": {
            "Namespace": "MyApp",
            "MetricName": "TotalRequests",
            "Dimensions": [
              {
                "Name": "Service",
                "Value": "{{ target }}-canary"
              }
            ]
          },
          "Period": 60,
          "Stat": "Sum"
        },
        "ReturnData": false
      }
    ]
```

Flagger Service Account に CloudWatch をクエリするための適切な IAM 権限があることを確認します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

### Pre/Post Rollout Webhook

Flagger は、rollout の異なるフェーズで実行される複数の Webhook type をサポートします。

| Webhook Type | 実行タイミング | ユースケース |
|-------------|---------------|----------|
| `confirm-rollout` | トラフィックシフトの開始前 | ゲート: 外部承認を必須にする |
| `pre-rollout` | 各分析ステップの前 | Smoke test、conformance test |
| `rollout` | 各分析ステップ中 | Load test、synthetic traffic |
| `confirm-promotion` | 最終昇格の前 | 手動ゲート、ビジネス承認 |
| `post-rollout` | 昇格またはロールバックの後 | クリーンアップ、通知、監査 |
| `rollback` | rollout 失敗後 | インシデント通知、クリーンアップ |
| `event` | すべての Flagger event 発生時 | 監査ログ |

### Webhook YAML の例

**hey を使用した load testing Webhook:**

```yaml
webhooks:
- name: load-test-hey
  type: rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 60s
  metadata:
    type: cmd
    cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"
    logCmdOutput: "true"
```

**bash を使用した conformance test:**

```yaml
webhooks:
- name: smoke-test
  type: pre-rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 120s
  metadata:
    type: bash
    cmd: |
      set -e
      # Check health endpoint
      curl -sf http://web-app-canary.production:8080/healthz

      # Check readiness
      curl -sf http://web-app-canary.production:8080/readyz

      # Verify API response
      response=$(curl -sf http://web-app-canary.production:8080/api/v1/status)
      echo "$response" | jq -e '.status == "ok"'
```

**Grafana k6 を使用した load testing:**

```yaml
webhooks:
- name: load-test-k6
  type: rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 120s
  metadata:
    type: bash
    cmd: |
      k6 run --vus 5 --duration 1m - <<'EOF'
      import http from 'k6/http';
      import { check, sleep } from 'k6';

      export default function () {
        const res = http.get('http://web-app-canary.production:8080/');
        check(res, {
          'status is 200': (r) => r.status === 200,
          'duration < 500ms': (r) => r.timings.duration < 500,
        });
        sleep(0.5);
      }
      EOF
```

**Post-rollout クリーンアップ Webhook:**

```yaml
webhooks:
- name: post-deploy-cleanup
  type: post-rollout
  url: http://flagger-loadtester.flagger-system/
  timeout: 60s
  metadata:
    type: bash
    cmd: |
      # Notify external system of deployment
      curl -X POST https://api.internal.example.com/deployments \
        -H 'Content-Type: application/json' \
        -d '{"service": "web-app", "status": "promoted", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}'
```

**手動ゲーティング用の外部 Webhook:**

```yaml
webhooks:
- name: manual-gate
  type: confirm-promotion
  url: https://deploy-approval.internal.example.com/api/approve
  timeout: 30s
  metadata:
    service: web-app
    environment: production
```

---

## GitOps 統合（Flux + Flagger）

### FluxCD HelmRelease + Flagger Canary ワークフロー

最も強力なパターンは、アプリケーション Deployment 用の Flux HelmRelease と、プログレッシブデリバリー用の Flagger Canary を組み合わせることです。Flux は Git から desired state を管理し、Flagger は変更の rollout 方法を管理します。

```mermaid
sequenceDiagram
    participant D as Developer
    participant G as Git Repository
    participant FC as Flux Controllers
    participant FL as Flagger
    participant K as Kubernetes

    D->>G: Push new image tag
    G->>FC: Source Controller detects change
    FC->>K: Helm Controller updates HelmRelease
    K->>FL: Deployment spec changed
    FL->>FL: Initialize canary
    FL->>K: Create canary pods
    FL->>FL: Run analysis (metrics + webhooks)

    alt Metrics Pass
        FL->>K: Promote canary to primary
        FL->>D: Notify: deployment succeeded
    else Metrics Fail
        FL->>K: Rollback to primary
        FL->>D: Notify: deployment failed
    end
```

**Flux + Flagger のリポジトリ構成:**

```
fleet-infra/
├── clusters/
│   └── production/
│       ├── flux-system/         # Flux bootstrap
│       │   ├── gotk-components.yaml
│       │   └── gotk-sync.yaml
│       ├── infrastructure.yaml  # Infrastructure Kustomization
│       └── apps.yaml            # Apps Kustomization
├── infrastructure/
│   ├── flagger/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── helmrepository.yaml
│   │   └── helmrelease.yaml
│   └── istio/
│       └── ...
└── apps/
    └── web-app/
        ├── kustomization.yaml
        ├── deployment.yaml
        ├── hpa.yaml
        ├── canary.yaml          # Flagger Canary resource
        └── alerts.yaml          # Flagger AlertProviders
```

**アプリケーション用の Flux HelmRelease:**

```yaml
# apps/web-app/helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: web-app
  namespace: production
spec:
  interval: 5m
  chart:
    spec:
      chart: web-app
      version: "1.x"
      sourceRef:
        kind: HelmRepository
        name: internal-charts
        namespace: flux-system
  values:
    image:
      repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
      tag: v2.0.0
    replicaCount: 3
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
```

**HelmRelease と並べて配置する Flagger Canary リソース:**

```yaml
# apps/web-app/canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-app
  namespace: production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  autoscalerRef:
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    name: web-app
  progressDeadlineSeconds: 600
  service:
    port: 8080
    portName: http
    gateways:
    - istio-system/public-gateway
    hosts:
    - app.example.com
  analysis:
    interval: 1m
    maxWeight: 50
    stepWeight: 10
    threshold: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: load-test
      type: rollout
      url: http://flagger-loadtester.flagger-system/
      timeout: 60s
      metadata:
        type: cmd
        cmd: "hey -z 1m -q 10 -c 2 http://web-app-canary.production:8080/"
```

### Kustomization ベースの Deployment

HelmRelease の代わりに Flux Kustomization を使用するチーム向け:

```yaml
# clusters/production/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: web-app
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: production
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  path: ./apps/web-app
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: web-app
    namespace: production
  timeout: 5m
```

```yaml
# apps/web-app/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: production
resources:
- deployment.yaml
- service.yaml
- hpa.yaml
- canary.yaml
- alert-providers.yaml

images:
- name: web-app
  newName: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
  newTag: v2.0.0
```

### Image Automation + Canary Automation Pipeline

完全に自動化された pipeline では、Flux Image Automation を使用して新しい container image を検出し、更新された tag を Git に commit し、Flagger にプログレッシブ rollout を処理させます。

```mermaid
flowchart LR
    subgraph CI["CI Pipeline"]
        BUILD["Build & Push<br/>Image"]
    end

    subgraph ECR["Amazon ECR"]
        IMG["web-app:v2.0.0"]
    end

    subgraph GIT["Git Repository"]
        MANIFEST["deployment.yaml<br/>image: web-app:v2.0.0"]
    end

    subgraph FLUX["Flux Controllers"]
        IR["Image Repository<br/>(scan ECR)"]
        IP["Image Policy<br/>(semver filter)"]
        IU["Image Update<br/>Automation"]
        KC["Kustomize<br/>Controller"]
    end

    subgraph FLAGGER["Flagger"]
        CANARY["Canary<br/>Controller"]
        ANALYSIS["Metrics<br/>Analysis"]
    end

    subgraph K8S["Kubernetes"]
        PRIMARY["Primary<br/>Deployment"]
        CANARY_DEP["Canary<br/>Deployment"]
    end

    BUILD --> IMG
    IMG --> IR
    IR --> IP
    IP --> IU
    IU -->|"git commit"| MANIFEST
    MANIFEST --> KC
    KC --> PRIMARY
    PRIMARY --> CANARY
    CANARY --> CANARY_DEP
    CANARY_DEP --> ANALYSIS
    ANALYSIS -->|"Promote"| PRIMARY

    classDef ci fill:#dc3545,stroke:#333,color:white
    classDef ecr fill:#FF9900,stroke:#333,color:white
    classDef git fill:#f05033,stroke:#333,color:white
    classDef flux fill:#5468FF,stroke:#333,color:white
    classDef flagger fill:#28a745,stroke:#333,color:white
    classDef k8s fill:#326CE5,stroke:#333,color:white

    class BUILD ci
    class IMG ecr
    class MANIFEST git
    class IR,IP,IU,KC flux
    class CANARY,ANALYSIS flagger
    class PRIMARY,CANARY_DEP k8s
```

**Flux Image Automation リソース:**

```yaml
# Image repository: scan ECR for new tags
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: web-app
  namespace: flux-system
spec:
  image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app
  interval: 5m
  provider: aws
---
# Image policy: select the latest semver tag
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: web-app
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: web-app
  policy:
    semver:
      range: ">=1.0.0"
---
# Image update automation: commit new tag to Git
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: web-app
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@example.com
        name: flux
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $_ := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
        {{ end -}}
    push:
      branch: main
  update:
    path: ./apps/web-app
    strategy: Setters
```

Deployment の image フィールドに setter comment を付けます。

```yaml
# apps/web-app/deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: web-app
        image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app:v1.0.0 # {"$imagepolicy": "flux-system:web-app"}
```

新しい image（例: `v2.0.0`）が ECR に push されると:
1. Flux Image Repository が ECR をスキャンし、新しい tag を検出する
2. Flux Image Policy が semver range に基づいて `v2.0.0` を選択する
3. Flux Image Update Automation が新しい tag を Git に commit する
4. Flux Kustomize Controller が更新された Deployment を適用する
5. Flagger が Deployment の変更を検出し、canary rollout を開始する
6. Flagger がトラフィックを段階的にシフトし、メトリクスを分析して、昇格またはロールバックする

---

## 可観測性とアラート

### Grafana Dashboard（Flagger メトリクス）

Flagger は Grafana で可視化できる Prometheus メトリクスをエクスポートします。主なメトリクスは次のとおりです。

| メトリクス | 種類 | 説明 |
|--------|------|-------------|
| `flagger_canary_status` | Gauge | Canary status（0=Initialized、1=Progressing、2=WaitingPromotion、3=Promoting、4=Finalising、5=Succeeded、6=Failed） |
| `flagger_canary_weight` | Gauge | 現在の canary トラフィック weight |
| `flagger_canary_total` | Counter | canary 分析の総数 |
| `flagger_canary_duration_seconds` | Histogram | canary 分析の秒単位の所要時間 |
| `flagger_canary_metric_analysis` | Gauge | 最後のメトリクス分析結果（1=成功、0=失敗） |

**公式 Flagger Grafana dashboard をインポートする:**

```bash
# The official Flagger dashboard ID for Grafana is 16527
# Import via Grafana UI: Dashboards > Import > Enter 16527
```

**カスタム Grafana dashboard JSON model（簡略版）:**

```json
{
  "title": "Flagger Canary Deployments",
  "panels": [
    {
      "title": "Canary Status",
      "type": "stat",
      "targets": [
        {
          "expr": "flagger_canary_status{namespace=\"production\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    },
    {
      "title": "Canary Traffic Weight",
      "type": "timeseries",
      "targets": [
        {
          "expr": "flagger_canary_weight{namespace=\"production\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    },
    {
      "title": "Request Success Rate",
      "type": "timeseries",
      "targets": [
        {
          "expr": "flagger_canary_metric_analysis{namespace=\"production\", metric=\"request-success-rate\"}",
          "legendFormat": "{{ name }}"
        }
      ]
    }
  ]
}
```

### Prometheus アラートルール

Flagger canary の失敗に対する Prometheus アラートルールを設定します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: flagger-alerts
  namespace: monitoring
spec:
  groups:
  - name: flagger
    rules:
    # Alert when a canary deployment fails
    - alert: CanaryDeploymentFailed
      expr: flagger_canary_status == 6
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Canary deployment failed for {{ $labels.name }}"
        description: >
          The canary deployment for {{ $labels.name }} in namespace
          {{ $labels.namespace }} has failed. Flagger has rolled back
          to the previous version.

    # Alert when a canary is stuck progressing
    - alert: CanaryProgressStalled
      expr: flagger_canary_status == 1 and flagger_canary_weight == flagger_canary_weight offset 10m
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: "Canary progress stalled for {{ $labels.name }}"
        description: >
          The canary weight for {{ $labels.name }} has not changed in
          the last 15 minutes. Check Flagger logs for analysis failures.

    # Alert when canary metric analysis fails
    - alert: CanaryMetricCheckFailed
      expr: flagger_canary_metric_analysis == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Canary metric check failing for {{ $labels.name }}"
        description: >
          The {{ $labels.metric }} metric check for {{ $labels.name }}
          is failing. If this continues, Flagger will rollback.

    # Alert on high canary analysis duration
    - alert: CanaryAnalysisSlow
      expr: histogram_quantile(0.99, rate(flagger_canary_duration_seconds_bucket[1h])) > 600
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Canary analysis taking too long for {{ $labels.name }}"
        description: >
          The canary analysis P99 duration exceeds 10 minutes.
          Consider tuning the analysis interval or metrics thresholds.
```

### Slack および Teams の通知設定

severity ベースのルーティングで包括的なアラートを設定します。

```yaml
# Alert provider for informational messages (deployments started, promoted)
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack-info
  namespace: production
spec:
  type: slack
  channel: deploy-notifications
  username: flagger
  secretRef:
    name: slack-webhook
---
# Alert provider for critical messages (failures, rollbacks)
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: slack-critical
  namespace: production
spec:
  type: slack
  channel: deploy-incidents
  username: flagger
  secretRef:
    name: slack-webhook
---
# Alert provider for PagerDuty integration
apiVersion: flagger.app/v1beta1
kind: AlertProvider
metadata:
  name: pagerduty
  namespace: production
spec:
  type: slack
  # PagerDuty Slack integration or Events API v2
  secretRef:
    name: pagerduty-webhook
```

Canary で異なる severity を持つ複数の provider を参照します。

```yaml
spec:
  analysis:
    alerts:
    - name: "info-slack"
      severity: info
      providerRef:
        name: slack-info
    - name: "error-slack"
      severity: error
      providerRef:
        name: slack-critical
    - name: "critical-pagerduty"
      severity: error
      providerRef:
        name: pagerduty
```

### Deployment 履歴の追跡

Flagger event と Kubernetes event を通じて Deployment 履歴を追跡します。

```bash
# View Flagger events for a canary
kubectl describe canary web-app -n production

# Query Flagger events via kubectl
kubectl get events -n production \
  --field-selector involvedObject.kind=Canary,involvedObject.name=web-app \
  --sort-by='.lastTimestamp'

# Export deployment history from Prometheus
# Query: changes(flagger_canary_status{name="web-app"}[7d])
```

長期的な Deployment 履歴については、Flux Notification Controller と統合して、event を外部システムへ転送します。

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: deployment-tracker
  namespace: flux-system
spec:
  type: generic
  address: https://deploy-tracker.internal.example.com/api/events
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: flagger-events
  namespace: flux-system
spec:
  providerRef:
    name: deployment-tracker
  eventSources:
  - kind: Canary
    name: "*"
    namespace: production
  eventSeverity: info
```

---

## 本番環境のベストプラクティス

### 段階的な導入戦略

組織全体で Flagger を段階的に導入します。

**フェーズ 1: 非クリティカルな Service**
- 内部ツールまたは staging 環境から開始する
- 保守的な分析設定（高いしきい値、多数の iteration）を使用する
- メトリクス収集と Webhook 統合を検証する

**フェーズ 2: 低リスクの本番 Service**
- blast radius が小さい本番 Service に適用する
- アラートおよび通知 channel を設定する
- 手動介入のための runbook を確立する

**フェーズ 3: ミッションクリティカルな Service**
- 高トラフィックで顧客向けの Service に適用する
- 安全性をさらに高めるため手動ゲーティングを使用する
- ビジネス KPI 固有のカスタムメトリクスを実装する

**フェーズ 4: 組織全体へのロールアウト**
- チーム全体で Canary template を標準化する
- Flux + Flagger を使用してセルフサービス platform を構築する
- image から本番環境までの end-to-end pipeline を自動化する

### メトリクスしきい値のチューニング

適切なメトリクスしきい値の選択は、Deployment 速度と安全性のバランスを取るうえで重要です。

```yaml
# Conservative (recommended for initial rollout)
analysis:
  interval: 2m
  maxWeight: 30
  stepWeight: 5
  threshold: 3
  iterations: 15
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99.9
    interval: 2m
  - name: request-duration
    thresholdRange:
      max: 200
    interval: 2m

# Balanced (recommended for most production services)
analysis:
  interval: 1m
  maxWeight: 50
  stepWeight: 10
  threshold: 5
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 99
    interval: 1m
  - name: request-duration
    thresholdRange:
      max: 500
    interval: 1m

# Aggressive (for high-confidence, frequently deployed services)
analysis:
  interval: 30s
  maxWeight: 80
  stepWeight: 20
  threshold: 10
  metrics:
  - name: request-success-rate
    thresholdRange:
      min: 95
    interval: 30s
  - name: request-duration
    thresholdRange:
      max: 1000
    interval: 30s
```

**しきい値チューニングのガイドライン:**

| パラメータ | 保守的 | バランス型 | 積極的 |
|-----------|-------------|----------|------------|
| `interval` | 2m | 1m | 30s |
| `stepWeight` | 5 | 10 | 20 |
| `maxWeight` | 30 | 50 | 80 |
| `threshold`（失敗） | 3 | 5 | 10 |
| 成功率の最小値 | 99.9% | 99% | 95% |
| レイテンシ P99 の最大値 | 200ms | 500ms | 1000ms |
| ロールアウトの総所要時間 | 約 20 分 | 約 10 分 | 約 4 分 |

### ロールバック戦略

ロールバック動作を理解することは、本番運用に不可欠です。

**自動ロールバック**（デフォルト動作）:
- Flagger がしきい値を超えるメトリクス失敗を検出する
- すべてのトラフィックが即座に primary へルーティングされる
- Canary Pod がゼロまでスケールされる
- status が `Failed` に設定される

**手動ロールバック**:
```bash
# Force a rollback by setting the skipAnalysis annotation
kubectl annotate canary web-app -n production \
  flagger.app/rollback="true"

# Skip analysis for emergency deploys (not recommended for production)
kubectl annotate canary web-app -n production \
  flagger.app/skipAnalysis="true"
```

自動化されたインシデント対応のための**Rollback Webhook**:

```yaml
webhooks:
- name: rollback-handler
  type: rollback
  url: http://incident-handler.production:8080/api/rollback
  timeout: 30s
  metadata:
    service: web-app
    team: platform
    pagerduty_service: web-app-prod
```

### マルチ cluster Flagger

複数の EKS cluster を運用する組織では、hub-and-spoke パターンで Flagger をデプロイできます。

```mermaid
graph TB
    subgraph HUB["Management Cluster"]
        FLUX_HUB["Flux Controllers"]
        GIT[("Git Repository")]
    end

    subgraph SPOKE1["Production Cluster - us-east-1"]
        FL1["Flagger"]
        ISTIO1["Istio"]
        APP1["web-app"]
    end

    subgraph SPOKE2["Production Cluster - us-west-2"]
        FL2["Flagger"]
        ISTIO2["Istio"]
        APP2["web-app"]
    end

    subgraph SPOKE3["Production Cluster - eu-west-1"]
        FL3["Flagger"]
        ISTIO3["Istio"]
        APP3["web-app"]
    end

    GIT --> FLUX_HUB
    FLUX_HUB -->|"Kustomization"| SPOKE1
    FLUX_HUB -->|"Kustomization"| SPOKE2
    FLUX_HUB -->|"Kustomization"| SPOKE3

    classDef hub fill:#FF9900,stroke:#333,color:white
    classDef spoke fill:#326CE5,stroke:#333,color:white

    class FLUX_HUB,GIT hub
    class FL1,FL2,FL3,ISTIO1,ISTIO2,ISTIO3,APP1,APP2,APP3 spoke
```

**マルチ cluster Flagger に関する主な考慮事項:**

1. **独立した Flagger instance**: 各 cluster に Flagger をデプロイします。各 instance はローカルリソースのみを管理します
2. **共有 Canary 定義**: cluster 固有の設定には overlay を使用した Flux Kustomization を使用します
3. **順次ロールアウト**: Flux dependency を使用して、本番 cluster より先に staging へロールアウトします
4. **一元化された可観測性**: すべての cluster から Flagger メトリクスを中央の Prometheus/Thanos/Mimir に集約します

```yaml
# clusters/production-us-east-1/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: web-app
  namespace: flux-system
spec:
  # Deploy to us-east-1 only after staging succeeds
  dependsOn:
  - name: web-app
    namespace: flux-system
  # This refers to the staging cluster Kustomization
  sourceRef:
    kind: GitRepository
    name: fleet-infra
  path: ./apps/web-app/overlays/production-us-east-1
  interval: 10m
  prune: true
```

### その他のベストプラクティス

1. **canary 分析中は常に load test を実行してください。** canary へのトラフィックがなければ、Prometheus には分析するメトリクスがありません。Flagger loadtester を使用するか、synthetic traffic を生成してください。

2. **`progressDeadlineSeconds` を適切に設定してください。** これは安全網です。この時間内に canary が進行できない場合、自動的にロールバックされます。想定されるロールアウト総所要時間の少なくとも 2 倍に設定してください。

3. **`skipAnalysis` は慎重に使用してください。** 緊急 Deployment は可能になりますが、すべての安全チェックをバイパスします。基本的な検証がなお必要な緊急変更には、手動ゲーティングを優先してください。

4. **Flagger と provider のバージョンを固定してください。** 自動アップグレードによる予期しない動作を回避するため、Flux HelmRelease では特定の Helm chart バージョンを使用してください。

5. **ロールバック動作を定期的にテストしてください。** staging に既知の不良バージョンをデプロイし、Flagger が失敗を正しく検出してロールバックすることを検証してください。

6. **Git では Canary 定義を Deployment から分離してください。** これにより Deployment リソースをクリーンでポータブルに保ち、プログレッシブデリバリーに関する関心事を Canary リソースに分離できます。

7. **namespace スコープの AlertProvider を使用してください。** これにより namespace 間の Webhook credential 漏えいを防ぎ、マルチテナント環境をサポートします。

8. **Flagger controller の健全性を監視してください。** Flagger Pod の再起動、高いメモリ使用量、reconciliation error に対するアラートを設定してください。

---

## 参考資料

### 公式ドキュメント

- [Flagger 公式ドキュメント](https://docs.flagger.app/)
- [Flagger GitHub リポジトリ](https://github.com/fluxcd/flagger)
- [Flagger Helm Chart](https://artifacthub.io/packages/helm/flagger/flagger)
- [FluxCD 公式ドキュメント](https://fluxcd.io/docs/)
- [Flagger FAQ](https://docs.flagger.app/faq)

### 関連する内部ドキュメント

| トピック | リンク |
|-------|------|
| FluxCD | [FluxCD GitOps](./02-fluxcd.md) |
| GitOps ツールの比較 | [ArgoCD vs FluxCD vs Others](./03-gitops-comparison.md) |
| ArgoCD | [ArgoCD ドキュメント](./argocd/README.md) |
| Istio トラフィック分割 | [Traffic Splitting](../service-mesh/istio/traffic-management/04-traffic-splitting.md) |
| Argo Rollouts + Istio | [Argo Rollouts 統合](../service-mesh/istio/advanced/08-argo-rollouts.md) |
| Prometheus | [Prometheus Monitoring](../observability/metrics/01-prometheus.md) |
| Grafana | [Grafana ダッシュボード](../observability/grafana/README.md) |
| Gateway API | [Gateway API](../networking/04-gateway-api.md) |
| KEDA Autoscaling | [KEDA](../autoscaling/01-keda.md) |

### 外部リソース

- [Flagger を使用したプログレッシブデリバリー（CNCF Webinar）](https://www.cncf.io/online-programs/progressive-delivery-with-flagger/)
- [Flux と Flagger による GitOps およびプログレッシブデリバリー](https://fluxcd.io/blog/)
- [Flagger と Istio を使用した Canary Deployment](https://docs.flagger.app/tutorials/istio-progressive-delivery)
- [AWS App Mesh 上の Flagger](https://docs.flagger.app/tutorials/appmesh-progressive-delivery)
- [Gateway API Canary Deployment](https://docs.flagger.app/tutorials/gatewayapi-progressive-delivery)

---

## ナビゲーション

| 前へ | 上へ | 次へ |
|----------|----|----- |
| [GitOps ツールの比較](./03-gitops-comparison.md) | [GitOps 概要](./README.md) | なし |
