# Flagger 渐进式交付

> **支持的版本**: Flagger v1.38+，Flux v2.4+
> **最后更新**: June 2025

Flagger 是 Kubernetes 的渐进式交付 operator，它使用 service mesh 路由、ingress controller 或 Gateway API 进行流量迁移，并使用 Prometheus 指标进行金丝雀分析，从而自动推进金丝雀 Deployment。Flagger 最初由 Weaveworks 创建，现为 Flux 家族旗下的 CNCF 项目；它通过在测量关键性能指标的同时逐步将流量迁移到新版本，并在检测到异常时自动回滚，降低在生产环境引入新软件版本的风险。

## 目录

- [概述和学习目标](#overview-and-learning-objectives)
- [Flagger 架构](#flagger-architecture)
- [EKS 安装和配置](#eks-installation-and-configuration)
- [金丝雀 Deployment 策略](#canary-deployment-strategy)
- [蓝绿 Deployment 策略](#blue-green-deployment-strategy)
- [A/B 测试策略](#ab-testing-strategy)
- [自定义指标和 Webhook](#custom-metrics-and-webhooks)
- [GitOps 集成（Flux + Flagger）](#gitops-integration-flux--flagger)
- [可观测性和告警](#observability-and-alerting)
- [生产环境最佳实践](#production-best-practices)
- [参考资料](#references)

---

## 概述和学习目标

### 学习目标

完成本文档后，您将能够：

1. 说明渐进式交付策略（Canary、Blue-Green、A/B Testing）及各自的适用场景
2. 在 Amazon EKS 上使用各种 mesh 和 ingress provider 部署并配置 Flagger
3. 使用自定义指标分析和自动回滚条件定义 Canary 资源
4. 通过流量镜像和手动门控实现 Blue-Green 部署
5. 配置基于 header 和 cookie 的 A/B 测试路由
6. 将 Flagger 与 FluxCD 集成，以实现完全自动化的 GitOps 渐进式交付流水线
7. 为 Flagger 部署设置可观测性仪表板和告警

### 什么是渐进式交付？

渐进式交付是高级部署策略的统称，可在将变更提供给全部用户群之前，受控且逐步地向部分用户推出变更。与同时替换所有 Pod 的传统滚动更新不同，渐进式交付提供对流量分配、实时分析和自动回滚的细粒度控制。

三种主要的渐进式交付策略是：

| 策略 | 流量控制 | 使用场景 | 复杂度 |
|----------|----------------|----------|------------|
| **Canary** | 基于百分比的权重迁移 | 通用的渐进式发布 | 中 |
| **Blue-Green** | 在两个环境之间完全切换 | 零停机、即时回滚 | 低 |
| **A/B Testing** | 基于 Header/Cookie 的路由 | 面向特定用户群的功能测试 | 高 |

### Flagger 与 Argo Rollouts

Flagger 和 Argo Rollouts 都解决 Kubernetes 的渐进式交付问题，但它们采用根本不同的方法：

| 特性 | Flagger | Argo Rollouts |
|---------|---------|---------------|
| **生态系统** | Flux / CNCF | Argo / CNCF |
| **资源模型** | 包装原生 Deployment/DaemonSet | 使用 Rollout CRD 替代 Deployment |
| **流量 Provider** | Istio、Linkerd、Contour、Nginx、Gateway API、AWS App Mesh、Gloo、Traefik | Istio、Nginx、ALB、SMI、Gateway API |
| **指标分析** | 内置 Prometheus、Datadog、CloudWatch、自定义 Webhook | 内置支持多个 provider 的 AnalysisTemplate |
| **GitOps 集成** | 原生 Flux 集成 | 原生 Argo CD 集成 |
| **Webhook 支持** | pre/post-rollout、rollout、confirm-rollout、load-test | pre/post analysis、anti-affinity |
| **Blue-Green** | 通过 Canary CRD 支持 | 一等 Rollout 策略 |
| **A/B Testing** | 通过带 Header 的 Canary CRD 支持 | 通过 Experiment CRD 支持 |
| **CNCF 状态** | 孵化中（Flux 家族） | 已毕业（Argo 家族） |
| **采用模式** | 增量式（无需更改 Deployment） | 替代式（Rollout 替代 Deployment） |

**关键差异**：Flagger 不要求您更改现有的 Deployment 资源。它会自动创建 primary 和 canary CloneSet 变体，并通过 mesh/ingress 层管理流量迁移。Argo Rollouts 则要求将 `Deployment` kind 替换为 `Rollout` kind。

### Flux 生态系统中的 Flagger

Flagger 被设计为 Flux GitOps 工具包的渐进式交付组件：

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

## Flagger 架构

### 控制循环

Flagger 实现了一个控制循环，通过分析指标、运行一致性测试并管理流量路由，逐步推进应用程序的新版本。其核心协调循环为：

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

### 控制循环详细步骤

当目标 workload 中检测到变更（例如新的容器镜像）时，Flagger 会执行以下序列：

1. **检测变更**：Flagger 监视目标 Deployment 的 spec 变更（镜像 tag、环境变量、资源等）
2. **初始化 Canary**：使用新版本扩容 canary Deployment；primary 保留旧版本
3. **运行 Pre-Rollout Webhook**：执行一致性测试、冒烟测试或其他前置条件
4. **迁移流量**：根据 `stepWeight` 和 `maxWeight` 逐步增加 canary 流量权重
5. **分析指标**：查询 Prometheus（或其他 provider）以获取成功率、延迟和自定义指标
6. **推进或回滚**：如果指标通过阈值，则推进到下一步；否则发起回滚
7. **确认提升**：可选择通过 webhook 等待手动门控批准
8. **提升**：将 canary spec 复制到 primary，缩容 canary，并将全部流量路由到 primary
9. **发送通知**：通过 Slack、Teams 或其他已配置的 provider 发出告警

### Mesh 和 Ingress Provider 支持

Flagger 支持广泛的流量管理 provider，每个 provider 都具有不同的功能：

| Provider | Canary | Blue-Green | A/B Testing | 镜像 | Gateway API |
|----------|--------|------------|-------------|-----------|-------------|
| **Istio** | 是 | 是 | 是 | 是 | 是 |
| **Linkerd** | 是 | 是 | 否 | 否 | 是 |
| **AWS App Mesh** | 是 | 是 | 否 | 否 | 否 |
| **Contour** | 是 | 是 | 是 | 否 | 是 |
| **Nginx Ingress** | 是 | 是 | 是 | 否 | 否 |
| **Gloo Edge** | 是 | 是 | 否 | 否 | 否 |
| **Traefik** | 是 | 是 | 否 | 否 | 否 |
| **Gateway API** | 是 | 是 | 是 | 否 | 是 |
| **Kuma** | 是 | 是 | 否 | 否 | 否 |
| **Open Service Mesh** | 是 | 是 | 否 | 否 | 否 |

### Prometheus 指标分析

Flagger 的指标分析引擎查询 Prometheus，以评估 Canary 发布是否健康。两个内置指标为：

- **request-success-rate**：在分析间隔内成功 HTTP 请求（非 5xx）的百分比
- **request-duration**：在分析间隔内 HTTP 请求的 P99 延迟

这两个指标均源自 service mesh 或 ingress controller 的 Prometheus 指标（例如 `istio_requests_total`、`istio_request_duration_milliseconds_bucket`）。

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

## EKS 安装和配置

### 前提条件

在 Amazon EKS 上安装 Flagger 前，请确保满足以下前提条件：

- 运行 Kubernetes v1.27+ 的 Amazon EKS 集群
- 已安装 Helm v3.12+
- 已部署 service mesh（Istio）或 ingress controller（Nginx、Contour）
- 已部署 Prometheus stack（建议使用 kube-prometheus-stack）
- 已引导 FluxCD v2.4+（用于 GitOps 集成）

### 使用 Prometheus 进行 Helm 安装

使用 Helm 安装 Flagger，并启用 Prometheus metrics server：

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

对于使用 IRSA（IAM Roles for Service Accounts）的 EKS，请配置 service account：

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

### 安装 Flagger Loadtester

Flagger loadtester 是一个配套工具，用于在 canary 分析期间运行自动化负载测试和 Webhook：

```bash
helm upgrade -i flagger-loadtester flagger/loadtester \
  --namespace flagger-system \
  --set cmd.timeout=1h \
  --set resources.requests.cpu=100m \
  --set resources.requests.memory=64Mi
```

### Istio Provider 配置

使用 Istio 作为 mesh provider 时，Flagger 会自动管理 VirtualService 和 DestinationRule 资源：

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

验证是否已为目标 namespace 启用 Istio sidecar 注入：

```bash
kubectl label namespace production istio-injection=enabled
kubectl get namespace production --show-labels
```

### Gateway API Provider 配置

Flagger 支持将 Kubernetes Gateway API 作为 provider，从而无需完整的 service mesh 即可实现渐进式交付：

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

创建 Flagger 将引用的 Gateway 资源：

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

### Slack 和 Teams 通知设置

Flagger 可以使用 AlertProvider CRD 向 Slack、Microsoft Teams 和其他 provider 发送部署通知：

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

可以在 Canary 资源中引用多个 alert provider：

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

## Canary Deployment 策略

### Canary CRD 详细说明

Canary CRD 是 Flagger 用于定义渐进式交付策略的主要资源。它引用目标 Deployment，并指定应如何迁移流量、分析哪些指标以及何时回滚。

**Canary 资源的核心结构：**

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

### 分步流量迁移

Flagger 通过两个关键参数管理 canary 流量迁移：

- **`stepWeight`**：每个分析间隔中添加到 canary 的流量百分比
- **`maxWeight`**：提升前 canary 接收的最大流量百分比

例如，使用 `stepWeight: 10` 和 `maxWeight: 50`：

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

也可以使用 `stepWeights`（数组）定义非线性的流量步进：

```yaml
analysis:
  stepWeights: [1, 2, 5, 10, 25, 50, 80]
  # Traffic progression: 1% -> 2% -> 5% -> 10% -> 25% -> 50% -> 80% -> promote
```

### 指标分析

Flagger 的内置指标依赖 service mesh 或 ingress controller 暴露 Prometheus 指标：

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

`interval` 字段决定 Flagger 在每个分析步骤期间查询 Prometheus 的频率。`thresholdRange` 指定可接受的边界：

- `min`：指标值必须**大于或等于**此值（例如，成功率 >= 99%）
- `max`：指标值必须**小于或等于**此值（例如，延迟 <= 500ms）

### 自动回滚条件

在以下情况下，Flagger 会自动回滚 canary Deployment：

1. **超过指标失败阈值**：某个指标检查在一个分析步骤中失败的次数超过 `threshold`
2. **超过推进截止时间**：canary 未在 `progressDeadlineSeconds` 内推进
3. **Webhook 失败**：pre-rollout 或 rollout webhook 返回非 2xx 状态

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

发生回滚时，Flagger 会：
1. 将所有流量路由回 primary（旧版本）
2. 将 canary 缩容至零
3. 将 Canary 状态设置为 `Failed`
4. 发送告警通知

### 完整 Canary YAML 示例

以下是一个生产就绪的 Canary 资源，用于部署在带有 Istio 的 EKS 上的 Web 应用程序：

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

此 Canary 资源将：
1. 监视 `web-app` Deployment 的变更
2. 创建 `web-app-primary` 和 `web-app-canary` Deployment
3. 创建 `web-app`、`web-app-primary` 和 `web-app-canary` ClusterIP Service
4. 创建用于流量路由的 Istio VirtualService
5. 在开始 rollout 前运行冒烟测试
6. 每次迁移 10% 流量，直至 50%
7. 在每个分析步骤中运行负载测试
8. 检查请求成功率（>= 99%）和 P99 延迟（<= 500ms）
9. 如果连续 5 次指标检查失败则回滚
10. 所有步骤通过后，将 canary spec 复制到 primary 以完成提升

**监视 canary Deployment：**

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

## Blue-Green Deployment 策略

### Blue-Green Canary CRD

Flagger 通过同一个 Canary CRD 支持 Blue-Green 部署：省略 `stepWeight` 和 `maxWeight`，并使用 `iterations` 定义在将流量从旧（蓝色）版本切换到新（绿色）版本前要运行的分析周期数。

在 Blue-Green 模式中：
- canary 在分析期间不会接收实时流量（除非启用镜像）
- Flagger 使用 loadtester 或镜像流量针对 canary 运行指标检查
- 所有迭代通过后，流量会在一个步骤中从 primary 100% 切换到 canary
- 如果任何一次迭代失败，canary 将被缩容，不会影响生产流量

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

### 镜像流量

使用 Istio 时，Flagger 可以在 Blue-Green 分析期间将生产流量镜像到 canary。镜像流量是 fire-and-forget；canary 的响应会被丢弃，确保对用户零影响：

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

### 手动门控

对于高风险部署，您可以要求在 Flagger 提升 canary 前进行手动批准。这通过 confirm-rollout webhook 实现，Flagger 会在每个步骤查询该 webhook：

```yaml
spec:
  analysis:
    webhooks:
    - name: confirm-promotion
      type: confirm-promotion
      url: http://flagger-loadtester.flagger-system/gate/approve
```

要手动批准或拒绝：

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

### 完整 Blue-Green YAML 示例

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

## A/B 测试策略

### 基于 Header 和 Cookie 的路由

Flagger 中的 A/B 测试使用 HTTP header 或 cookie 将特定用户路由到 canary 版本。不同于使用加权路由的 canary Deployment，A/B 测试根据请求属性确保确定性的路由。

此策略非常适合：
- 面向特定用户群的 feature flag 测试
- 基于请求 header 的区域性发布
- 公开发布前的内部测试
- 针对特定用户群测量业务指标（转化率、参与度）

### Istio VirtualService 集成

使用 Istio 时，Flagger 会生成匹配 HTTP header 或 cookie 的 VirtualService 规则：

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

生成的 Istio VirtualService 将如下所示：

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

### 基于指标的自动提升

在 A/B 测试期间，Flagger 仍会对 canary 流量执行指标分析。配置数量的 `iterations` 在所有指标都处于阈值范围内的情况下通过后，Flagger 会自动提升 canary：

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

## 自定义指标和 Webhook

### Prometheus 自定义指标查询

除两个内置指标外，Flagger 还通过 MetricTemplate CRD 支持自定义 Prometheus 查询。这允许您在 canary Deployment 期间分析任意 Prometheus 指标：

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

在 Canary 分析中引用自定义指标：

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

### Datadog 指标 Provider

Flagger 支持将 Datadog 作为外部指标 provider：

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

### CloudWatch 指标 Provider

对于 EKS 上的 Amazon CloudWatch 指标：

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

确保 Flagger service account 具有查询 CloudWatch 所需的适当 IAM 权限：

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

Flagger 支持多种 Webhook 类型，它们会在 rollout 的不同阶段执行：

| Webhook 类型 | 执行时间 | 使用场景 |
|-------------|---------------|----------|
| `confirm-rollout` | 流量迁移开始前 | 门控：要求外部批准 |
| `pre-rollout` | 每个分析步骤前 | 冒烟测试、一致性测试 |
| `rollout` | 每个分析步骤期间 | 负载测试、合成流量 |
| `confirm-promotion` | 最终提升前 | 手动门控、业务批准 |
| `post-rollout` | 提升或回滚后 | 清理、通知、审计 |
| `rollback` | rollout 失败后 | 事件通知、清理 |
| `event` | 每个 Flagger 事件发生时 | 审计日志 |

### Webhook YAML 示例

**使用 hey 的负载测试 Webhook：**

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

**使用 bash 的一致性测试：**

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

**使用 Grafana k6 进行负载测试：**

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

**Post-rollout 清理 Webhook：**

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

**用于手动门控的外部 Webhook：**

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

## GitOps 集成（Flux + Flagger）

### FluxCD HelmRelease + Flagger Canary 工作流

最强大的模式是将用于应用程序部署的 Flux HelmRelease 与用于渐进式交付的 Flagger Canary 结合使用。Flux 从 Git 管理期望状态，而 Flagger 管理变更的 rollout 方式。

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

**Flux + Flagger 的仓库结构：**

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

**应用程序的 Flux HelmRelease：**

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

**与 HelmRelease 一同使用的 Flagger Canary 资源：**

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

### 基于 Kustomization 的部署

对于使用 Flux Kustomization 而非 HelmRelease 的团队：

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

### Image Automation + Canary 自动化流水线

全自动流水线使用 Flux Image Automation 检测新的容器镜像，将更新后的 tag 提交到 Git，并让 Flagger 处理渐进式 rollout：

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

**Flux Image Automation 资源：**

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

使用 setter 注释标记 Deployment 中的镜像字段：

```yaml
# apps/web-app/deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: web-app
        image: 123456789012.dkr.ecr.us-west-2.amazonaws.com/web-app:v1.0.0 # {"$imagepolicy": "flux-system:web-app"}
```

当新的镜像（例如 `v2.0.0`）被推送到 ECR 时：
1. Flux Image Repository 扫描 ECR 并检测新 tag
2. Flux Image Policy 根据 semver 范围选择 `v2.0.0`
3. Flux Image Update Automation 将新 tag 提交到 Git
4. Flux Kustomize Controller 应用更新后的 Deployment
5. Flagger 检测 Deployment 变更并开始 canary rollout
6. Flagger 逐步迁移流量，分析指标，并进行提升或回滚

---

## 可观测性和告警

### Grafana 仪表板（Flagger 指标）

Flagger 导出可在 Grafana 中可视化的 Prometheus 指标。关键指标如下：

| 指标 | 类型 | 描述 |
|--------|------|-------------|
| `flagger_canary_status` | Gauge | Canary 状态（0=Initialized、1=Progressing、2=WaitingPromotion、3=Promoting、4=Finalising、5=Succeeded、6=Failed） |
| `flagger_canary_weight` | Gauge | 当前 canary 流量权重 |
| `flagger_canary_total` | Counter | canary 分析总次数 |
| `flagger_canary_duration_seconds` | Histogram | canary 分析持续时间（秒） |
| `flagger_canary_metric_analysis` | Gauge | 最近一次指标分析的结果（1=通过、0=失败） |

**导入官方 Flagger Grafana 仪表板：**

```bash
# The official Flagger dashboard ID for Grafana is 16527
# Import via Grafana UI: Dashboards > Import > Enter 16527
```

**自定义 Grafana 仪表板 JSON 模型（简化版）：**

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

### Prometheus 告警规则

为 Flagger canary 失败配置 Prometheus 告警规则：

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

### Slack 和 Teams 通知配置

配置基于严重性路由的全面告警：

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

在 Canary 中引用具有不同严重性的多个 provider：

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

### Deployment 历史记录跟踪

通过 Flagger event 和 Kubernetes event 跟踪 Deployment 历史记录：

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

对于长期 Deployment 历史记录，请与 Flux Notification Controller 集成，以将 event 转发到外部系统：

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

## 生产环境最佳实践

### 渐进式采用策略

在整个组织中逐步采用 Flagger：

**阶段 1：非关键服务**
- 从内部工具或 staging 环境开始
- 使用保守的分析设置（较高阈值、更多迭代）
- 验证指标收集和 Webhook 集成

**阶段 2：低风险生产服务**
- 应用于影响范围较小的生产服务
- 配置告警和通知渠道
- 建立用于手动干预的运行手册

**阶段 3：关键任务服务**
- 应用于高流量、面向客户的服务
- 使用手动门控来增强安全性
- 实施特定于业务 KPI 的自定义指标

**阶段 4：全组织 rollout**
- 跨团队标准化 Canary 模板
- 使用 Flux + Flagger 构建自助服务平台
- 自动化从镜像到生产环境的端到端流水线

### 指标阈值调优

选择合适的指标阈值对于平衡部署速度与安全性至关重要：

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

**阈值调优指南：**

| 参数 | 保守 | 平衡 | 激进 |
|-----------|-------------|----------|------------|
| `interval` | 2m | 1m | 30s |
| `stepWeight` | 5 | 10 | 20 |
| `maxWeight` | 30 | 50 | 80 |
| `threshold`（失败次数） | 3 | 5 | 10 |
| 最低成功率 | 99.9% | 99% | 95% |
| 最大 P99 延迟 | 200ms | 500ms | 1000ms |
| 总 rollout 时间 | ~20 分钟 | ~10 分钟 | ~4 分钟 |

### 回滚策略

了解回滚行为对于生产环境操作至关重要：

**自动回滚**（默认行为）：
- Flagger 检测到超过阈值的指标失败
- 所有流量立即路由回 primary
- Canary Pod 缩容至零
- 状态设置为 `Failed`

**手动回滚**：
```bash
# Force a rollback by setting the skipAnalysis annotation
kubectl annotate canary web-app -n production \
  flagger.app/rollback="true"

# Skip analysis for emergency deploys (not recommended for production)
kubectl annotate canary web-app -n production \
  flagger.app/skipAnalysis="true"
```

**用于自动化事件响应的回滚 Webhook：**

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

### 多集群 Flagger

对于运行多个 EKS 集群的组织，可以采用 hub-and-spoke 模式部署 Flagger：

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

**多集群 Flagger 的关键注意事项：**

1. **独立的 Flagger 实例**：在每个集群中部署 Flagger；它仅管理本地资源
2. **共享 Canary 定义**：使用带 overlay 的 Flux Kustomization 进行特定于集群的配置
3. **顺序 rollout**：使用 Flux dependency 在生产集群之前发布到 staging
4. **集中式可观测性**：将所有集群的 Flagger 指标聚合到中央 Prometheus/Thanos/Mimir

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

### 其他最佳实践

1. **始终在 canary 分析期间运行负载测试。** 如果没有流量进入 canary，Prometheus 就没有可分析的指标。请使用 Flagger loadtester 或生成合成流量。

2. **适当设置 `progressDeadlineSeconds`。** 这是您的安全网。如果 canary 无法在此时间内推进，将自动回滚。应将其设置为至少是预期总 rollout 时间的 2 倍。

3. **谨慎使用 `skipAnalysis`。** 虽然它允许紧急部署，但会绕过所有安全检查。对于仍需基本验证的紧急变更，优先使用手动门控。

4. **固定 Flagger 和 provider 版本。** 在 Flux HelmRelease 中使用特定 Helm chart 版本，以避免自动升级导致的意外行为。

5. **定期测试回滚行为。** 在 staging 中部署已知错误的版本，以验证 Flagger 能够正确检测失败并回滚。

6. **在 Git 中将 Canary 定义与 Deployment 分离。** 这使 Deployment 资源保持整洁且可移植，并将渐进式交付相关内容隔离在 Canary 资源中。

7. **使用 namespace 作用域的 AlertProvider。** 这可防止 Webhook 凭证跨 namespace 泄露，并支持多租户环境。

8. **监控 Flagger controller 健康状况。** 为 Flagger Pod 重启、高内存使用率和协调错误设置告警。

---

## 参考资料

### 官方文档

- [Flagger 官方文档](https://docs.flagger.app/)
- [Flagger GitHub 仓库](https://github.com/fluxcd/flagger)
- [Flagger Helm Chart](https://artifacthub.io/packages/helm/flagger/flagger)
- [FluxCD 官方文档](https://fluxcd.io/docs/)
- [Flagger FAQ](https://docs.flagger.app/faq)

### 相关内部文档

| 主题 | 链接 |
|-------|------|
| FluxCD | [FluxCD GitOps](./02-fluxcd.md) |
| GitOps 工具对比 | [ArgoCD vs FluxCD vs 其他](./03-gitops-comparison.md) |
| ArgoCD | [ArgoCD 文档](./argocd/README.md) |
| Istio 流量拆分 | [流量拆分](../service-mesh/istio/traffic-management/04-traffic-splitting.md) |
| Argo Rollouts + Istio | [Argo Rollouts 集成](../service-mesh/istio/advanced/08-argo-rollouts.md) |
| Prometheus | [Prometheus 监控](../observability/metrics/01-prometheus.md) |
| Grafana | [Grafana 仪表板](../observability/grafana/README.md) |
| Gateway API | [Gateway API](../networking/04-gateway-api.md) |
| KEDA 自动扩缩容 | [KEDA](../autoscaling/01-keda.md) |

### 外部资源

- [使用 Flagger 进行渐进式交付（CNCF Webinar）](https://www.cncf.io/online-programs/progressive-delivery-with-flagger/)
- [使用 Flux 和 Flagger 实现 GitOps 与渐进式交付](https://fluxcd.io/blog/)
- [使用 Flagger 和 Istio 进行 Canary Deployment](https://docs.flagger.app/tutorials/istio-progressive-delivery)
- [AWS App Mesh 上的 Flagger](https://docs.flagger.app/tutorials/appmesh-progressive-delivery)
- [Gateway API Canary Deployment](https://docs.flagger.app/tutorials/gatewayapi-progressive-delivery)

---

## 导航

| 上一篇 | 上级 | 下一篇 |
|----------|----|----- |
| [GitOps 工具对比](./03-gitops-comparison.md) | [GitOps 概述](./README.md) | 无 |
