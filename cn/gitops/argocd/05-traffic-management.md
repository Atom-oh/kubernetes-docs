# ArgoCD 流量管理

> **审阅依据**：Argo CD 3.5.2、Argo Rollouts 1.10.0、Helm chart 2.43.1；经发布说明审阅后更新至 Argo CD 3.5.4 和 chart 2.43.6（Rollouts 仍为 1.10.0；未重新运行示例）
> **最后更新**：October 12, 2026

## 目录
- [Argo Rollouts 概述](#argo-rollouts-overview)
- [安装](#installation)
- [蓝绿部署](#blue-green-deployments)
- [金丝雀部署](#canary-deployments)
- [分析与验证](#analysis-and-verification)
- [Ingress 集成](#ingress-integration)
- [回滚策略](#rollback-strategies)
- [实验](#experiments)
- [通知](#notifications)

## Argo Rollouts 概述

Argo Rollouts 是一个 Kubernetes 控制器，提供高级部署功能，包括蓝绿部署、金丝雀部署和渐进式交付。

### 为什么使用 Argo Rollouts？

Kubernetes Deployments 支持 RollingUpdate 和 Recreate，也支持暂停/恢复。下表比较的是原生控制器行为；其他模式可通过额外的控制器或多个 Deployments 实现：

| 功能 | K8s Deployment | Argo Rollouts |
|---------|----------------|---------------|
| 滚动更新 | 是 | 是 |
| 蓝绿部署 | 否 | 是 |
| 金丝雀部署 | 否 | 是 |
| 流量拆分 | 否 | 是 |
| 自动回滚 | 否 | 是 |
| 分析/验证 | 否 | 是 |
| 暂停/恢复 | 是 | 是 |
| 实验 | 否 | 是 |

### 架构

![Argo Rollouts 控制器执行蓝绿、金丝雀和实验策略，通过 ingress 控制器和服务网格切换流量，并查询分析提供程序；查询结果会推进、中止或暂停发布。](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-0.html)

## 安装

### 安装 Argo Rollouts 控制器

```bash
set -euo pipefail
ROLLOUTS_VERSION=v1.10.0
kubectl create namespace argo-rollouts --dry-run=client -o yaml | kubectl apply -f -
kubectl apply --server-side -n argo-rollouts \
  -f "https://github.com/argoproj/argo-rollouts/releases/download/${ROLLOUTS_VERSION}/install.yaml"
kubectl rollout status deployment/argo-rollouts -n argo-rollouts --timeout=180s
```

### 安装 kubectl 插件

```bash
set -euo pipefail
ROLLOUTS_VERSION=v1.10.0
case "$(uname -s)" in
  Linux) plugin_os=linux ;;
  Darwin) plugin_os=darwin ;;
  *) echo "Use the Windows release asset for Windows" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64) plugin_arch=amd64 ;;
  aarch64|arm64) plugin_arch=arm64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac
plugin_asset="kubectl-argo-rollouts-${plugin_os}-${plugin_arch}"
plugin_dir="$(mktemp -d)"
trap 'rm -rf "$plugin_dir"' EXIT
plugin_base="https://github.com/argoproj/argo-rollouts/releases/download/${ROLLOUTS_VERSION}"
curl --fail --location --retry 3 "$plugin_base/$plugin_asset" -o "$plugin_dir/$plugin_asset"
curl --fail --location --retry 3 "$plugin_base/argo-rollouts-checksums.txt" -o "$plugin_dir/checksums.txt"
awk -v artifact="$plugin_asset" '$2 == artifact { print }' "$plugin_dir/checksums.txt" > "$plugin_dir/selected.sha256"
test -s "$plugin_dir/selected.sha256"
(
  cd "$plugin_dir"
  if [ "$plugin_os" = darwin ]; then
    shasum -a 256 -c selected.sha256
  else
    sha256sum -c selected.sha256
  fi
)
install -d "$HOME/.local/bin"
install -m 0755 "$plugin_dir/$plugin_asset" "$HOME/.local/bin/kubectl-argo-rollouts"
export PATH="$HOME/.local/bin:$PATH"
kubectl argo rollouts version
```

### 通过 Helm 安装

请在上述清单安装方式和 Helm 之间选择一种来管理控制器归属。将这些设置保存为 `rollouts-values.yaml`。`AWS_REGION` 应设置在查询 CloudWatch 的 **Rollouts 控制器**上；如果未使用该提供程序，可以省略。

```yaml
controller:
  replicas: 2
  metrics:
    enabled: true
    serviceMonitor:
      enabled: false  # Enable after installing/configuring Prometheus Operator
  pdb:
    enabled: true
    minAvailable: 1
  extraEnv:
    - name: AWS_REGION
      value: ap-northeast-2

dashboard:
  enabled: false
```

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade --install argo-rollouts argo/argo-rollouts \
  --version 2.43.6 --namespace argo-rollouts --create-namespace \
  --values rollouts-values.yaml --wait --timeout 5m
```

只有在配置好 CRD 和 Prometheus 选择器后，才启用 ServiceMonitor。共享 Dashboard 需要单独的身份验证/授权层。1.10.0 CLI 的 `dashboard` 命令会绑定所有网络接口，并使用你的 kubeconfig 权限；它打印的 localhost URL 并不会限制访问。

### Dashboard 访问（Helm 安装）

对于 Helm 安装，可启用只读 ClusterIP Dashboard，并通过端口转发绑定到回环地址：

```bash
helm upgrade --install argo-rollouts argo/argo-rollouts \
  --version 2.43.6 --namespace argo-rollouts --create-namespace \
  --values rollouts-values.yaml \
  --set dashboard.enabled=true --set dashboard.readonly=true \
  --set dashboard.service.type=ClusterIP --set dashboard.ingress.enabled=false \
  --wait --timeout 5m
kubectl port-forward --address 127.0.0.1 -n argo-rollouts \
  service/argo-rollouts-dashboard 3100:3100
```

打开 `http://127.0.0.1:3100/rollouts`。共享访问需要单独经过身份验证和授权的代理。

## 蓝绿部署

请根据应用配置替换示例中的 `myapp`/registry 镜像、ECR 账户/标签和指标名称。准备命名空间、镜像访问权限、就绪探针响应、指标采集和 AnalysisTemplates；每个场景应独立运行。初始部署没有之前的稳定 ReplicaSet。先成功部署 v1，然后在 Git 中将镜像改为 v2，以观察发布过程。

Argo CD 从 Git 应用 Rollout spec；单独的 Rollouts 控制器管理 ReplicaSets 和流量。中止发布并将流量切回稳定版本，不会回退 Git 提交或数据库迁移。

蓝绿部署会保留 Rollout 的旧 ReplicaSet 和新 ReplicaSet，然后更改活动 Service 的选择器。它不会复制整个集群环境。数据平面传播和连接排空都需要时间。

### 基本蓝绿 Rollout

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
        args:
        - name: service-name
          value: myapp-active
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

`previewReplicaCount` 限制预览容量；新 ReplicaSet 会在晋级前扩展到 `spec.replicas`。当 `autoPromotionEnabled` 为 false 时，`autoPromotionSeconds` 会被忽略。所需的晋级前分析示例也省略了 `autoPromotionSeconds`，使其与基于时间的自动晋级示例相互独立。此示例省略了 `scaleDownDelaySeconds`，避免固定的缩容截止时间取消晋级后分析。ALB 目标注册/注销和连接排空仍可能造成中断；请验证实际数据平面。

### 蓝绿流程

![蓝绿切换前，负载均衡器将流量发送到 Blue v1.0.0，而 Green v2.0.0 作为预览版本等待；切换后，活动 Service 选择器改为指向 Green v2.0.0，之前的 Blue v1.0.0 则根据分析和延迟设置缩容。](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-1.html)

### 自动晋级的蓝绿部署

```yaml
strategy:
  blueGreen:
    activeService: myapp-active
    previewService: myapp-preview
    autoPromotionEnabled: true
    autoPromotionSeconds: 60  # Wait 60s before auto-promoting
    previewReplicaCount: 3
```

## 金丝雀部署

配置了 trafficRouting 时，`setWeight` 会更改路由器的相对权重。没有路由器时，它会通过 ReplicaSet 数量近似实现流量比例；但不能保证请求百分比精确。使用路由器时，稳定版本的副本容量与流量权重相互独立。

金丝雀部署会逐步将流量切换到新版本。

默认情况下，基于流量路由的金丝雀会保留 100% 的稳定版本容量，因此需要同时规划稳定版本和金丝雀版本的容量。对于未配置 trafficRouting 的基本金丝雀部署，maxSurge 控制期望副本数的计算；在基于流量路由的模式下，它不是 Pod 总数上限。maxUnavailable 仍可能限制旧 ReplicaSet 的缩容速度。

### 基本金丝雀 Rollout

此示例需要 Gateway API 插件 0.17.0、`myapp-route` HTTPRoute、就绪的 Gateway，以及后文展示的匹配稳定版/金丝雀版 Services。请检查 HTTPRoute 的 Accepted/ResolvedRefs 状态以及数据平面的就绪情况。

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
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
  strategy:
    canary:
      canaryService: myapp-canary
      stableService: myapp-stable
      trafficRouting:
        plugins:
          argoproj-labs/gatewayAPI:
            httpRoute: myapp-route
            namespace: myapp
      steps:
      - setWeight: 5
      - pause:
          duration: 2m
      - setWeight: 10
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: myapp-canary
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 75
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency-check
          args:
          - name: service-name
            value: myapp-canary
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

### 金丝雀步骤说明

| 步骤类型 | 描述 |
|-----------|-------------|
| `setWeight` | 设置发送到金丝雀版本的流量百分比 |
| `pause` | 等待指定时长或人工批准 |
| `analysis` | 运行 AnalysisTemplate |
| `setCanaryScale` | 设置金丝雀副本数 |
| `setHeaderRoute` | 按标头路由（用于流量路由器） |

### 带人工关卡的金丝雀部署

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

手动晋级：

```bash
# Promote to next step
kubectl argo rollouts promote myapp-canary -n myapp

# Promote fully (skip remaining steps)
# Deliberate override only: skips remaining steps and analysis gates
# kubectl argo rollouts promote myapp-canary -n myapp --full
```

### 金丝雀流量流程

![图示显示客户端请求在负载均衡器处分流：在默认流量路由容量策略下的示例 10% 步骤中，相对权重 90 的流量发往有 10 个 Pod 的稳定 Service，权重 10 的流量发往有 1 个 Pod 的金丝雀 Service。](../../.gitbook/assets/en-gitops-argocd-05-traffic-management-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-05-traffic-management-2.html)

## 分析与验证

AnalysisTemplates 定义如何验证部署健康状况。

http_requests_total/http_request_duration_seconds_bucket 指标和 service/version 标签需要应用埋点和抓取配置。请将 prometheus.monitoring.svc.cluster.local:9090 替换为实际的 Service。阈值/窗口仅作示例；还应定义最低流量和 SLO 要求。

failureLimit 计算可容忍的**失败测量次数**：值为 3 时，第 4 次失败测量会超出限制。提供程序错误使用 consecutiveErrorLimit，不确定结果使用 inconclusiveLimit。以下条件可防止缺失值、空向量、NaN 和 Infinity 通过关卡。count 表示测量次数，而非 HTTP 请求数；重叠的查询窗口并非独立样本。

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
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] >= 0.95
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (sum(rate(
            http_requests_total{
              service="{{args.service-name}}",
              status=~"2.."
            }[5m]
          )) or vector(0)) /
          sum(rate(
            http_requests_total{
              service="{{args.service-name}}"
            }[5m]
          ))
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] < 0.95
    inconclusiveLimit: 0
```

### 延迟分析

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
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <
      500
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          histogram_quantile(0.99,
            sum(rate(
              http_request_duration_seconds_bucket{
                service="{{args.service-name}}"
              }[5m]
            )) by (le)
          ) * 1000
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      500
    inconclusiveLimit: 0
```

### Web 分析（HTTP 端点）

Service 必须返回成功的 HTTP 响应，且 JSON 内容为 `{"status":"OK"}`。jsonPath 会提取 status 字符串，因此应直接比较 result，而不是 result.status。请根据实际响应约定调整条件。

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
    successCondition: result == "OK"
    failureLimit: 1
    provider:
      web:
        url: http://{{ args.service-name }}.myapp.svc.cluster.local/health
        jsonPath: '{$.status}'
        timeoutSeconds: 10
    failureCondition: result != nil && result != "OK"
```

### Datadog 分析

Datadog v2 公式使用单独的查询和公式字段。请通过密钥管理流程，在此 AnalysisTemplate 所在命名空间中配置包含 address/api-key/app-key 的 datadog Secret。asFloat(default(result, -1)) 可将缺失数据与有效的零错误率区分开，并避免将 nil 传递给类型化函数。

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
    successCondition: |
      let rate = asFloat(default(result, -1));
      !isNaN(rate) && !isInf(rate) && rate >= 0 && rate <= 1 && rate < 0.05
    failureLimit: 2
    provider:
      datadog:
        apiVersion: v2
        interval: 5m
        aggregator: sum
        secretRef:
          name: datadog
          namespaced: true
        queries:
          a: sum:http.requests{service:{{args.service-name}},status:5xx}.as_count()
          b: sum:http.requests{service:{{args.service-name}}}.as_count()
        formula: a / b
    failureCondition: |
      let rate = asFloat(default(result, -1));
      !isNaN(rate) && !isInf(rate) && rate >= 0 && rate <= 1 && rate >= 0.05
    inconclusiveLimit: 0
```

### 基于 Job 的分析

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
                image: myregistry/integration-tests:v1.0.0
                env:
                - name: TARGET_URL
                  value: '{{args.service-url}}'
                command:
                - /bin/sh
                - -ec
                - exec npm run test:integration
              automountServiceAccountToken: false
          activeDeadlineSeconds: 300
```

### ClusterAnalysisTemplate

在多个命名空间之间共享分析模板：

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
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] >= 0.95
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (sum(rate(
            http_requests_total{
              namespace="{{args.namespace}}",
              service="{{args.service-name}}",
              status=~"2.."
            }[5m]
          )) or vector(0)) /
          sum(rate(
            http_requests_total{
              namespace="{{args.namespace}}",
              service="{{args.service-name}}"
            }[5m]
          ))
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] <= 1 && result[0] < 0.95
    inconclusiveLimit: 0
```

## Ingress 集成

Argo Rollouts 支持原生流量提供程序和插件扩展。Kong 等没有原生集成的提供程序，可通过 **Gateway API 插件**支持。

| 提供程序 | 集成方式 | 备注 |
|---|---|---|
| NGINX Ingress | 原生（`trafficRouting.nginx`） | 直接操作 `canary-weight` 注解 |
| AWS ALB | 原生（`trafficRouting.alb`） | Ingress 后端端口必须是 `use-annotation`；参见 [验证结果](#verification-results-on-eks) |
| Istio | 原生（`trafficRouting.istio`） | 直接操作 VirtualService/DestinationRule |
| SMI | 原生（`trafficRouting.smi`） | SMI 项目本身实际上已无人维护，不建议新采用 |
| Ambassador、Apache APISIX、Traefik | 原生 | 本文档未涵盖；请参阅[官方文档](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/) |
| **Kong** 和其他兼容 Gateway API 的实现（kgateway 等） | **Gateway API 插件**（`trafficRouting.plugins`） | 没有原生的 `trafficRouting.kong` 字段 |

### NGINX Ingress（现有安装）

社区版 ingress-nginx 已于 2026 年 3 月退役；此处内容是为现有安装提供的迁移参考。新示例使用 Gateway API 路径。每个路由示例都需要在其所在命名空间中配置相应的稳定版/金丝雀版 Services。

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
            canary-by-header-value: 'true'
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
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
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
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
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
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
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
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
  ingressClassName: alb
```

> **ALB 配置检查**：Rollout 的 rootService（或省略时的 stableService）、action 注解名称和 Ingress 后端名称必须一致。后端端口 `name: use-annotation` 会选择加权 action。数值端口则会选择普通 Service 后端；根据该 Service 的配置，协调可能失败，也可能产生不同的路由结果。请使用 `aws elbv2 describe-rules` 检查控制器事件和实际的 ForwardConfig。

### Istio 流量拆分

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
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 100
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
        image: myregistry/myapp:v2.0.0
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: networking.istio.io/v1
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
        port:
          number: 80
      weight: 100
    - destination:
        host: myapp-canary
        port:
          number: 80
      weight: 0
```

### Gateway API 插件（HTTPRoute）

Kong、kgateway 和其他兼容实现的 Gateway API 路径使用由 argoproj-labs 维护的 [Gateway API 插件](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi)。Traefik 也有原生的 TraefikService 集成；其 Gateway API 路径可以使用此插件。本章使用于 2026-09-01 发布的插件 0.17.0。它会更新 HTTPRoute 后端权重。其他 Route 类型和标头路由取决于已安装的 CRD 和实现能力；请验证 Route 状态和实际请求分布。

下面的二进制文件适用于**运行控制器 Pod 的 Linux amd64 节点**。在 arm64 上，请使用 gatewayapi-plugin-linux-arm64 和 SHA256 `5221279f7bf2c9b2c0ff6ed7ff12718ecce1d4892f1ff5e5224bb723cfd0fd92`。对于 Helm 安装，请在 controller.trafficRouterPlugins 下管理相同条目。对于清单安装，请合并到现有 ConfigMap 数据中并重启控制器。下方展示的 Role 将 HTTPRoute 权重更新权限限定在一个命名空间内；其他 Route 类型/标头路由的创建还需要额外审查权限。

在 `argo-rollouts-config` ConfigMap 中注册插件，使控制器在启动时下载二进制文件：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-config
  namespace: argo-rollouts
data:
  trafficRouterPlugins: |
    - name: argoproj-labs/gatewayAPI
      location: https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/download/v0.17.0/gatewayapi-plugin-linux-amd64
      sha256: 1904ca787d33107c140521899d61fff030ee75d99908bd175fca5a4647759061
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: argo-rollouts-gateway-api-plugin
  namespace: myapp
rules:
- apiGroups:
  - ''
  resources:
  - services
  verbs:
  - get
- apiGroups:
  - gateway.networking.k8s.io
  resources:
  - httproutes
  verbs:
  - get
  - list
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: argo-rollouts-gateway-api-plugin
  namespace: myapp
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: argo-rollouts-gateway-api-plugin
subjects:
- kind: ServiceAccount
  name: argo-rollouts
  namespace: argo-rollouts
```

Rollout 通过 `trafficRouting.plugins` 引用 HTTPRoute：

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
      - pause:
          duration: 1m
      - setWeight: 50
      - pause:
          duration: 1m
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

在每个 `setWeight` 步骤中，插件会直接更新这两个 `backendRefs[].weight` 值。

### Kong（通过 Gateway API 插件）

Kong Ingress Controller (KIC) 没有原生的 Argo Rollouts 集成；它使用上述 Gateway API 插件。以下配置适用于独立运行的 KIC，它管理现有 Kong Gateway 数据平面，且未使用 Kong Operator。该设置使用 unmanaged 注解；由 Kong Operator 管理的 Gateways 生命周期不同：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: kong
  annotations:
    konghq.com/gatewayclass-unmanaged: "true"   # required: without it the Gateway stays stuck on "Waiting for controller"
spec:
  controllerName: konghq.com/kic-gateway-controller   # note: different from KIC's IngressClass controller string
```

接下来，应用与上述相同的 [Gateway API 插件](#gateway-api-plugin-httproute)配置；Rollout 和 HTTPRoute YAML 完全相同。

### EKS 上的验证结果

之前的文档报告了在 EKS 1.36、Rollouts 1.9.0、AWS Load Balancer Controller 3.2.1、Istio 1.30、KIC 3.5 和 plugin0.16.0 下的以下结果。未附原始日志、请求数、测量时长和已执行的清单，因此本次静态审阅无法复现这些报告。以下是历史观察结果，并非 1.10.0/0.17.0 的新测试结果，也不保证能够即时、零停机地完成切换。

| 提供程序 | 检查内容 | 结果 |
|---|---|---|
| NGINX | `canary-weight` 注解从 20→50→100% 的变化 | ✅ 已确认：实时 curl 流量比例与注解值相符 |
| Istio | VirtualService 权重从 20→50→100% 的变化，以及 `abort` 后立即恢复到 0% | ✅ 已确认：curl 流量比例与权重相符，且 abort 后流量立即切回先前的稳定版本 |
| AWS ALB | Listener rule forward 权重变化，并通过 `aws elbv2 describe-rules` 与实时 AWS 状态交叉核对 | ✅ 已确认（但需要遵循上文 [`use-annotation` 注意事项](#aws-alb-ingress)） |
| Kong（Gateway API 插件） | `HTTPRoute.backendRefs[].weight` 变化，以及经过 Kong 数据平面的真实流量 | ✅ 已确认，但 `gatewayclass-unmanaged` 注解和准确的 `controllerName` 很容易配置错误（见上文） |

当 Argo CD 管理路由资源时，请审查针对 Rollouts 所拥有字段的精确 diff 排除项：相关 ALB action 注解、Istio 路由权重、HTTPRoute 后端权重以及 Service 的 rollouts-pod-template-hash 选择器。避免忽略整个 spec 或整个管理器。同步期间保留这些值还需要 RespectIgnoreDifferences=true，且此功能对现有资源存在限制。

## 回滚策略

### 分析失败时自动回滚

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

### 手动回滚

```bash
# Abort current rollout and rollback
kubectl argo rollouts abort myapp -n myapp

# Undo to previous version
kubectl argo rollouts undo myapp -n myapp

# Undo to specific revision
kubectl argo rollouts undo myapp -n myapp --to-revision=2
```

Abort 会将流量切回稳定版本，但不会更改期望的 Pod 模板。undo 会更改实时 Pod 模板；对于由 Argo CD 管理的工作负载，还需要经过审查的 Git 更改，以免 self-heal 恢复到有问题的版本。这两种操作都不会回滚数据库影响。分析结果为 Inconclusive 时会暂停以供调查；这与 Failed/Error 不同。

### 回滚配置

这是一个现有且配置了 trafficRouting 的 Rollout 的 spec 片段。dynamicStableScale 会降低稳定版本的容量，abort 时可能需要重新扩容；此设置是在恢复容量和资源使用之间进行权衡。内联分析块只会暂停当前步骤，而后台分析则配置在 strategy.canary.analysis 下。

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
          args:
          - name: service-name
            value: myapp-canary
```

## 实验

在 1.10.0 中，所有 `requiredForCompletion: true` 的分析都成功后，Experiment 可能会在 `duration` 到期前结束。不要将 duration 视为验证时间的下限。请明确验证用于隔离实验流量的 Service/路由器选择器。有关状态转换和清理延迟，请参阅[深入介绍](10-rollouts-experiment.md)。

同时运行多个版本以进行 A/B 测试。

> 有关详细行为（资源创建链、命名规则、流量隔离和 AnalysisRun 判定），请参阅 [Rollouts Experiments 深入介绍](10-rollouts-experiment.md)。

**前提条件：** Experiment 不会生成用户流量。请提供测试流量和抓取配置，并将 Pod 的 `rollouts-pod-template-hash` 作为指标标签 `rollouts_pod_template_hash` 暴露出来。以下比较示例使用错误率增加一个百分点作为说明；它不能替代显著性检验或最低样本量验证。缺失数据会保持 Inconclusive。`progressDeadlineSeconds` 限制的是 ReplicaSet 可用时间，而不是分析开始前的延迟。

在同一命名空间中创建所引用的 AnalysisTemplate：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: compare-analysis
  namespace: myapp
spec:
  args:
  - name: baseline-hash
  - name: canary-hash
  metrics:
  - name: canary-error-rate-increase
    interval: 30s
    count: 5
    failureLimit: 0
    inconclusiveLimit: 0
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <=
      0.01
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >
      0.01
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}"}[5m]))
          -
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.baseline-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.baseline-hash }}"}[5m]))
  - name: canary-absolute-error-rate
    interval: 30s
    count: 5
    failureLimit: 0
    inconclusiveLimit: 0
    successCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0 && result[0] < 0.05
    failureCondition: result != nil && len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >=
      0.05
    provider:
      prometheus:
        address: http://prometheus.monitoring.svc.cluster.local:9090
        query: |
          (
            sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}",status=~"5.."}[5m]))
            or vector(0)
          ) / sum(rate(http_requests_total{rollouts_pod_template_hash="{{ args.canary-hash }}"}[5m]))
```

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
        app: myapp-experiment
        variant: baseline
    template:
      metadata:
        labels:
          app: myapp-experiment
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
        app: myapp-experiment
        variant: canary
    template:
      metadata:
        labels:
          app: myapp-experiment
          variant: canary
      spec:
        containers:
        - name: myapp
          image: myregistry/myapp:v2.0.0
          ports:
          - containerPort: 8080
  analyses:
  - name: compare-metrics
    templateName: compare-analysis
    args:
    - name: baseline-hash
      value: '{{templates.baseline.podTemplateHash}}'
    - name: canary-hash
      value: '{{templates.canary.podTemplateHash}}'
    requiredForCompletion: true
```

## 通知

将 Rollout 事件集成到通知系统中。

### 在现有 Rollout 中配置通知

以下是要合并到现有 Rollout 中的 metadata 片段，而不是完整的资源清单。

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.slack: deployments
    notifications.argoproj.io/subscribe.on-rollout-aborted.slack: deployments
    notifications.argoproj.io/subscribe.on-analysis-run-failed.slack: alerts
```

### 通知触发器和模板

请通过密钥管理流程，在控制器命名空间中配置包含 slack-token 的 argo-rollouts-notification-secret。内置 Rollout 事件会选择这些触发器名称；仅 Degraded 并不能证明 Rollout 已中止。请配置所有引用的触发器/模板，包括分析失败通知。

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
    - send: [rollout-completed]
  trigger.on-rollout-aborted: |
    - send: [rollout-aborted]
  template.rollout-completed: |
    message: |
      Rollout {{.rollout.metadata.name}} completed successfully!
      Revision: {{.rollout.status.currentPodHash}}
      Image: {{(index .rollout.spec.template.spec.containers 0).image}}
  template.rollout-aborted: |
    message: |
      Rollout {{.rollout.metadata.name}} was aborted!
      Reason: {{.rollout.status.message}}
  trigger.on-analysis-run-failed: |
    - send: [analysis-run-failed]
  template.analysis-run-failed: |
    message: |
      Analysis failed for Rollout {{.rollout.metadata.name}}. Inspect its AnalysisRun.
```

## 参考资料

- [Argo Rollouts 1.10.0](https://github.com/argoproj/argo-rollouts/releases/tag/v1.10.0)
- [分析语义](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/docs/features/analysis.md)
- [分析控制器阈值](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/analysis/analysis.go)
- [CloudWatch 提供程序实现](https://github.com/argoproj/argo-rollouts/blob/v1.10.0/metricproviders/cloudwatch/cloudwatch.go)
- [Gateway API 插件 0.17.0](https://github.com/argoproj-labs/rollouts-plugin-trafficrouter-gatewayapi/releases/tag/v0.17.0)

## 测验

要测试你学到的内容，请尝试 [ArgoCD 流量管理测验](../../quizzes/gitops/argocd/05-traffic-management-quiz.md)。
