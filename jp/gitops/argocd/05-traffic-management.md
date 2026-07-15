# ArgoCD トラフィック管理

> **対応バージョン**: Argo Rollouts v1.6+, ArgoCD v2.9+
> **最終更新**: July 15, 2026

## 目次
- [Argo Rollouts の概要](#argo-rollouts-overview)
- [インストール](#installation)
- [Blue-Green デプロイメント](#blue-green-deployments)
- [Canary デプロイメント](#canary-deployments)
- [分析と検証](#analysis-and-verification)
- [Ingress 統合](#ingress-integration)
- [ロールバック戦略](#rollback-strategies)
- [実験](#experiments)
- [通知](#notifications)

## Argo Rollouts の概要

Argo Rollouts は、Blue-Green デプロイメント、Canary デプロイメント、プログレッシブデリバリー機能などの高度なデプロイメント機能を提供する Kubernetes controller です。

### Argo Rollouts を使用する理由

標準の Kubernetes Deployment はローリングアップデートのみをサポートします。Argo Rollouts はこれを次のように拡張します。

| 機能 | K8s Deployment | Argo Rollouts |
|---------|----------------|---------------|
| ローリングアップデート | はい | はい |
| Blue-Green | いいえ | はい |
| Canary | いいえ | はい |
| トラフィック分割 | いいえ | はい |
| 自動ロールバック | いいえ | はい |
| 分析/検証 | いいえ | はい |
| 一時停止/再開 | いいえ | はい |
| 実験 | いいえ | はい |

### アーキテクチャ

```mermaid
flowchart TB
    subgraph ROLLOUTS["Argo Rollouts"]
        CTRL["Rollouts Controller"]
        ANALYSIS["Analysis Controller"]
    end

    subgraph TRAFFIC["Traffic Management"]
        INGRESS["Ingress Controller"]
        MESH["Service Mesh"]
    end

    subgraph WORKLOADS["Workloads"]
        ACTIVE["Active ReplicaSet"]
        PREVIEW["Preview/Canary ReplicaSet"]
    end

    subgraph METRICS["Metrics"]
        PROM["Prometheus"]
        DD["Datadog"]
        NR["New Relic"]
    end

    CTRL --> ACTIVE
    CTRL --> PREVIEW
    CTRL --> INGRESS
    CTRL --> MESH
    ANALYSIS --> PROM
    ANALYSIS --> DD
    ANALYSIS --> NR
    ANALYSIS -->|"Pass/Fail"| CTRL

    classDef rollouts fill:#EB6E85,stroke:#333,color:white
    classDef traffic fill:#326CE5,stroke:#333,color:white
    classDef workload fill:#28a745,stroke:#333,color:white
    classDef metrics fill:#6c757d,stroke:#333,color:white

    class CTRL,ANALYSIS rollouts
    class INGRESS,MESH traffic
    class ACTIVE,PREVIEW workload
    class PROM,DD,NR metrics
```

## インストール

### Argo Rollouts Controller のインストール

```bash
# Create namespace
kubectl create namespace argo-rollouts

# Install controller
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Verify installation
kubectl get pods -n argo-rollouts
```

### kubectl Plugin のインストール

```bash
# macOS
brew install argoproj/tap/kubectl-argo-rollouts

# Linux
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x kubectl-argo-rollouts-linux-amd64
sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# Verify
kubectl argo rollouts version
```

### Helm によるインストール

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

helm install argo-rollouts argo/argo-rollouts \
  --namespace argo-rollouts \
  --create-namespace \
  --set dashboard.enabled=true
```

### 本番環境向け Helm Values

```yaml
controller:
  replicas: 2
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true

dashboard:
  enabled: true
  ingress:
    enabled: true
    ingressClassName: nginx
    hosts:
      - rollouts.example.com
```

## Blue-Green デプロイメント

Blue-green デプロイメントは、2 つの同一環境を維持し、それらの間でトラフィックを切り替えます。

### 基本的な Blue-Green Rollout

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 5
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myregistry/myapp:v1.0.0
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
  strategy:
    blueGreen:
      activeService: myapp-active
      previewService: myapp-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 30
      previewReplicaCount: 2
      prePromotionAnalysis:
        templates:
          - templateName: smoke-tests
        args:
          - name: service-name
            value: myapp-preview
      postPromotionAnalysis:
        templates:
          - templateName: success-rate
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-active
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-preview
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

### Blue-Green フロー

```mermaid
sequenceDiagram
    participant User
    participant Rollout
    participant Active as Active Service
    participant Preview as Preview Service
    participant Analysis

    Note over Rollout: Current: v1 (Blue)

    User->>Rollout: Update image to v2
    Rollout->>Preview: Create v2 pods (Green)
    Rollout->>Preview: Route preview traffic

    Note over Preview: v2 receiving preview traffic

    Rollout->>Analysis: Run pre-promotion analysis
    Analysis-->>Rollout: Analysis passed

    alt Auto-promotion enabled
        Rollout->>Active: Switch traffic to v2
    else Manual approval required
        User->>Rollout: Promote
        Rollout->>Active: Switch traffic to v2
    end

    Note over Active: v2 now receiving production traffic

    Rollout->>Analysis: Run post-promotion analysis
    Analysis-->>Rollout: Analysis passed

    Rollout->>Rollout: Scale down v1 pods

    Note over Rollout: Deployment complete
```

### 自動昇格を使用した Blue-Green

```yaml
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: true
    autoPromotionSeconds: 60  # Wait 60s before auto-promoting
    previewReplicaCount: 3
```

## Canary デプロイメント

Canary デプロイメントは、新しいバージョンへ徐々にトラフィックを移行します。

### 基本的な Canary Rollout

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp-canary
  namespace: myapp
spec:
  replicas: 10
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myregistry/myapp:v1.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      canaryService: myapp-canary
      stableService: myapp-stable
      trafficRouting:
        nginx:
          stableIngress: myapp-ingress
      steps:
        # Step 1: 5% traffic to canary
        - setWeight: 5
        - pause: {duration: 2m}

        # Step 2: 10% traffic, run analysis
        - setWeight: 10
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: myapp-canary

        # Step 3: 25% traffic
        - setWeight: 25
        - pause: {duration: 5m}

        # Step 4: 50% traffic
        - setWeight: 50
        - pause: {duration: 5m}

        # Step 5: 75% traffic
        - setWeight: 75
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency-check

        # Step 6: 100% traffic (full promotion)
        - setWeight: 100
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-stable
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-canary
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

### Canary ステップの説明

| ステップタイプ | 説明 |
|-----------|-------------|
| `setWeight` | Canary に割り当てるトラフィックの割合を設定 |
| `pause` | 指定時間または手動承認を待機 |
| `analysis` | AnalysisTemplate を実行 |
| `setCanaryScale` | Canary の replica 数を設定 |
| `setHeaderRoute` | header によるルーティング（traffic router 用） |

### 手動ゲートを使用した Canary

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - pause: {}  # Indefinite pause - requires manual promotion

      - setWeight: 50
      - pause: {duration: 10m}

      - setWeight: 100
```

手動で昇格します。

```bash
# Promote to next step
kubectl argo rollouts promote myapp-canary

# Promote fully (skip remaining steps)
kubectl argo rollouts promote myapp-canary --full
```

### Canary トラフィックフロー

```mermaid
flowchart TB
    subgraph TRAFFIC["Incoming Traffic (100%)"]
        REQ["Requests"]
    end

    subgraph INGRESS["Ingress Controller"]
        SPLIT["Traffic Split"]
    end

    subgraph STABLE["Stable Version (v1)"]
        S1["Pod 1"]
        S2["Pod 2"]
        S3["Pod 3"]
    end

    subgraph CANARY["Canary Version (v2)"]
        C1["Pod 1"]
    end

    REQ --> SPLIT
    SPLIT -->|"90%"| STABLE
    SPLIT -->|"10%"| CANARY

    classDef traffic fill:#f9f9f9,stroke:#333,color:black
    classDef stable fill:#28a745,stroke:#333,color:white
    classDef canary fill:#ffc107,stroke:#333,color:black

    class REQ,SPLIT traffic
    class S1,S2,S3 stable
    class C1 canary
```

## 分析と検証

AnalysisTemplate は、デプロイメントの健全性を検証する方法を定義します。

### Prometheus 分析

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: myapp
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result[0] >= 0.95
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(
              http_requests_total{
                service="{{args.service-name}}",
                status=~"2.."
              }[5m]
            )) /
            sum(rate(
              http_requests_total{
                service="{{args.service-name}}"
              }[5m]
            ))
```

### レイテンシー分析

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-check
  namespace: myapp
spec:
  args:
    - name: service-name
  metrics:
    - name: p99-latency
      interval: 2m
      count: 3
      successCondition: result[0] < 500  # 500ms threshold
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            histogram_quantile(0.99,
              sum(rate(
                http_request_duration_seconds_bucket{
                  service="{{args.service-name}}"
                }[5m]
              )) by (le)
            ) * 1000
```

### Web 分析（HTTP Endpoint）

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: smoke-tests
  namespace: myapp
spec:
  args:
    - name: service-name
  metrics:
    - name: smoke-test
      interval: 30s
      count: 3
      successCondition: result.status == "healthy"
      failureLimit: 1
      provider:
        web:
          url: "http://{{args.service-name}}/health"
          jsonPath: "{$.status}"
          timeoutSeconds: 10
```

### Datadog 分析

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: datadog-success-rate
  namespace: myapp
spec:
  args:
    - name: service-name
  metrics:
    - name: error-rate
      interval: 5m
      count: 3
      successCondition: result < 0.05
      failureLimit: 2
      provider:
        datadog:
          apiVersion: v2
          interval: 5m
          query: |
            sum:http.requests{service:{{args.service-name}},status:5xx}.as_count() /
            sum:http.requests{service:{{args.service-name}}}.as_count()
```

### Job ベースの分析

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: integration-tests
  namespace: myapp
spec:
  args:
    - name: service-url
  metrics:
    - name: integration-tests
      provider:
        job:
          spec:
            backoffLimit: 1
            template:
              spec:
                restartPolicy: Never
                containers:
                  - name: test-runner
                    image: myregistry/integration-tests:latest
                    env:
                      - name: TARGET_URL
                        value: "{{args.service-url}}"
                    command:
                      - /bin/sh
                      - -c
                      - |
                        npm run test:integration
                        if [ $? -eq 0 ]; then
                          exit 0
                        else
                          exit 1
                        fi
```

### ClusterAnalysisTemplate

namespace をまたいで分析テンプレートを共有します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ClusterAnalysisTemplate
metadata:
  name: global-success-rate
spec:
  args:
    - name: service-name
    - name: namespace
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result[0] >= 0.95
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(
              http_requests_total{
                namespace="{{args.namespace}}",
                service="{{args.service-name}}",
                status=~"2.."
              }[5m]
            )) /
            sum(rate(
              http_requests_total{
                namespace="{{args.namespace}}",
                service="{{args.service-name}}"
              }[5m]
            ))
```

## Ingress 統合

Argo Rollouts は 10 種類を超える traffic provider をサポートします。Kong のようにネイティブ統合を持たない provider は、代わりに **Gateway API plugin** を通じてサポートされます。

| Provider | 統合 | 注記 |
|---|---|---|
| NGINX Ingress | ネイティブ（`trafficRouting.nginx`） | `canary-weight` annotation を直接操作 |
| AWS ALB | ネイティブ（`trafficRouting.alb`） | Ingress backend port は `use-annotation` である必要があります。詳細は[検証結果](#verification-results-on-eks)を参照 |
| Istio | ネイティブ（`trafficRouting.istio`） | VirtualService/DestinationRule を直接操作 |
| SMI | ネイティブ（`trafficRouting.smi`） | SMI プロジェクト自体は実質的にメンテナンスされていません。新規採用には非推奨です |
| Ambassador、Apache APISIX、Traefik、Google Cloud | ネイティブ | このドキュメントでは扱いません。[公式ドキュメント](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/)を参照 |
| **Kong** およびその他の Gateway API 準拠実装（kgateway など） | **Gateway API plugin**（`trafficRouting.plugins`） | ネイティブの `trafficRouting.kong` field はありません |

### NGINX Ingress

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        nginx:
          stableIngress: myapp-ingress
          additionalIngressAnnotations:
            canary-by-header: X-Canary
            canary-by-header-value: "true"
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-stable
                port:
                  number: 80
```

### AWS ALB Ingress

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        alb:
          ingress: myapp-ingress
          rootService: myapp-root
          servicePort: 80
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.myapp-root: |
      {
        "type": "forward",
        "forwardConfig": {
          "targetGroups": [
            {
              "serviceName": "myapp-stable",
              "servicePort": 80,
              "weight": 100
            },
            {
              "serviceName": "myapp-canary",
              "servicePort": 80,
              "weight": 0
            }
          ]
        }
      }
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-root
                port:
                  name: use-annotation
```

> ⚠️ **テストで検証済み**: Ingress backend port が `name: use-annotation` ではなく実際の port 番号（例: `number: 80`）に誤って設定されている場合、AWS Load Balancer Controller は `alb.ingress.kubernetes.io/actions.*` annotation を**警告もエラーもなく無視します**。重み付き forward rule ではなく、単純な単一 target group rule が維持されます。そのため、実際の ALB トラフィックはまったく移行していないのに、`kubectl get rollout` では `SetWeight` が正常に上昇しているように見えます。常に、ライブ listener rule の `ForwardConfig.TargetGroups` weight を `aws elbv2 describe-rules` でクロスチェックしてください。

### Istio トラフィック分割

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
              - primary
          destinationRule:
            name: myapp-destrule
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
        - setWeight: 10
        - pause: {duration: 5m}
        - setWeight: 50
        - pause: {duration: 5m}
        - setWeight: 100
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: myapp-vsvc
  namespace: myapp
spec:
  hosts:
    - myapp.example.com
  gateways:
    - myapp-gateway
  http:
    - name: primary
      route:
        - destination:
            host: myapp-stable
          weight: 100
        - destination:
            host: myapp-canary
          weight: 0
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp-destrule
  namespace: myapp
spec:
  host: myapp
  subsets:
    - name: stable
      labels:
        app: myapp
    - name: canary
      labels:
        app: myapp
```

### Gateway API Plugin（汎用）

ネイティブの Argo Rollouts 統合を持たない Gateway API 準拠実装（Kong、Traefik、kgateway など）は、argoproj-labs が保守する [Gateway API plugin](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi) を通じてサポートされます。この plugin は標準 `HTTPRoute` の `backendRefs[].weight` field を直接操作するため、Gateway API を実装する任意の controller に同じように適用できます。また、TLSRoute と header ベースのルーティングもサポートします。2026 年時点の最新リリースは v0.16.0 です。

controller が起動時に binary をダウンロードできるよう、`argo-rollouts-config` ConfigMap に登録して plugin をインストールします。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-config
  namespace: argo-rollouts
data:
  trafficRouterPlugins: |-
    - name: "argoproj-labs/gatewayAPI"
      location: "https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/download/v0.16.0/gatewayapi-plugin-linux-amd64"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argo-rollouts-gateway-api-plugin
rules:
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get"]
  - apiGroups: ["gateway.networking.k8s.io"]
    resources: ["httproutes", "grpcroutes", "tcproutes", "tlsroutes"]
    verbs: ["get", "list", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argo-rollouts-gateway-api-plugin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: argo-rollouts-gateway-api-plugin
subjects:
  - kind: ServiceAccount
    name: argo-rollouts
    namespace: argo-rollouts
```

Rollout は `trafficRouting.plugins` を通じて HTTPRoute を参照します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 5
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: app
          image: myapp:v2.0.0
          ports:
            - containerPort: 8080
  strategy:
    canary:
      stableService: myapp-stable
      canaryService: myapp-canary
      trafficRouting:
        plugins:
          argoproj-labs/gatewayAPI:
            httpRoute: myapp-route
            namespace: myapp
      steps:
        - setWeight: 20
        - pause: {duration: 1m}
        - setWeight: 50
        - pause: {duration: 1m}
        - setWeight: 100
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: myapp-route
  namespace: myapp
spec:
  parentRefs:
    - name: myapp-gateway
  rules:
    - backendRefs:
        - name: myapp-stable
          kind: Service
          port: 80
          weight: 100
        - name: myapp-canary
          kind: Service
          port: 80
          weight: 0
```

各 `setWeight` ステップで、plugin はこの 2 つの `backendRefs[].weight` 値を直接更新します。

### Kong（Gateway API Plugin 経由）

Kong Ingress Controller（KIC）にはネイティブの Argo Rollouts 統合がありません。上記の Gateway API plugin を使用します。Gateway API モードで KIC をインストールした後、GatewayClass を**unmanaged gateway** としてマークする必要があります。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: kong
  annotations:
    konghq.com/gatewayclass-unmanaged: "true"   # required — without it the Gateway stays stuck on "Waiting for controller"
spec:
  controllerName: konghq.com/kic-gateway-controller   # note: different from KIC's IngressClass controller string
```

以降は、上記と同じ [Gateway API plugin](#gateway-api-plugin-universal) 設定を適用します。Rollout と HTTPRoute の YAML は同一です。

### EKS での検証結果

隔離されたテスト namespace 内で、EKS 1.36 cluster（Argo Rollouts v1.9.0、AWS Load Balancer Controller v3.2.1、Istio 1.30、Kong Ingress Controller 3.5 + Gateway API plugin v0.16.0）を使用して、4 つすべての provider を検証しました。すべてのテストリソース（namespace、Helm release、ALB、GatewayClass）は、検証後に削除されました。

| Provider | 確認内容 | 結果 |
|---|---|---|
| NGINX | `canary-weight` annotation の 20→50→100% への遷移 | ✅ 確認済み — 実際の curl トラフィック比率が annotation 値と一致 |
| Istio | VirtualService weight の 20→50→100% への遷移、および `abort` 時の 0% への即時復帰 | ✅ 確認済み — curl 比率が weight と一致し、abort の直後にトラフィックが以前の stable version に戻る |
| AWS ALB | listener rule の forward weight 遷移。`aws elbv2 describe-rules` によるライブ AWS state とのクロスチェック | ✅ 確認済み（ただし上記の [`use-annotation` に関する注意](#aws-alb-ingress)が必要） |
| Kong（Gateway API plugin） | `HTTPRoute.backendRefs[].weight` の遷移、および Kong の data plane を通る実トラフィック | ✅ 確認済み — ただし、`gatewayclass-unmanaged` annotation と正確な `controllerName` は間違えやすいため注意が必要です（上記参照） |

## ロールバック戦略

### 分析失敗時の自動ロールバック

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - analysis:
          templates:
            - templateName: success-rate
          args:
            - name: service-name
              value: myapp-canary
    # Analysis failure automatically triggers rollback
```

### 手動ロールバック

```bash
# Abort current rollout and rollback
kubectl argo rollouts abort myapp

# Undo to previous version
kubectl argo rollouts undo myapp

# Undo to specific revision
kubectl argo rollouts undo myapp --to-revision=2
```

### ロールバック設定

```yaml
spec:
  strategy:
    canary:
      abortScaleDownDelaySeconds: 30
      dynamicStableScale: true
      steps:
        - setWeight: 10
        - analysis:
            templates:
              - templateName: success-rate
            # Analysis runs continuously
            # Failure at any point triggers rollback
```

## 実験

複数のバージョンを同時に使用して A/B テストを実行します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Experiment
metadata:
  name: myapp-experiment
  namespace: myapp
spec:
  duration: 1h
  progressDeadlineSeconds: 300
  templates:
    - name: baseline
      replicas: 2
      selector:
        matchLabels:
          app: myapp
          variant: baseline
      template:
        metadata:
          labels:
            app: myapp
            variant: baseline
        spec:
          containers:
            - name: myapp
              image: myregistry/myapp:v1.0.0
              ports:
                - containerPort: 8080
    - name: canary
      replicas: 2
      selector:
        matchLabels:
          app: myapp
          variant: canary
      template:
        metadata:
          labels:
            app: myapp
            variant: canary
        spec:
          containers:
            - name: myapp
              image: myregistry/myapp:v2.0.0
              ports:
                - containerPort: 8080
  analyses:
    - name: compare-metrics
      templateName: compare-experiment
      args:
        - name: baseline-hash
          valueFrom:
            podTemplateHashValue: baseline
        - name: canary-hash
          valueFrom:
            podTemplateHashValue: canary
```

## 通知

Rollout イベントを通知システムと統合します。

### Rollout での通知設定

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: myapp
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.slack: deployments
    notifications.argoproj.io/subscribe.on-rollout-aborted.slack: deployments
    notifications.argoproj.io/subscribe.on-analysis-run-failed.slack: alerts
spec:
  # ...
```

### 通知トリガーとテンプレート

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-notification-configmap
  namespace: argo-rollouts
data:
  service.slack: |
    token: $slack-token

  trigger.on-rollout-completed: |
    - when: rollout.status.phase == 'Healthy'
      send: [rollout-completed]

  trigger.on-rollout-aborted: |
    - when: rollout.status.phase == 'Degraded'
      send: [rollout-aborted]

  template.rollout-completed: |
    message: |
      Rollout {{.rollout.metadata.name}} completed successfully!
      Revision: {{.rollout.status.currentPodHash}}
      Image: {{(index .rollout.spec.template.spec.containers 0).image}}

  template.rollout-aborted: |
    message: |
      Rollout {{.rollout.metadata.name}} was aborted!
      Reason: {{.rollout.status.message}}
```

## クイズ

学習内容を確認するには、[ArgoCD トラフィック管理クイズ](../../quizzes/gitops/argocd/05-traffic-management-quiz.md)に挑戦してください。
