# ArgoCD 应用

> **支持的版本**: ArgoCD v2.9+
> **最后更新**: February 22, 2026

## 目录
- [Application CRD 概览](#application-crd-overview)
- [源类型](#source-types)
- [多个源](#multiple-sources)
- [目标配置](#destination-configuration)
- [健康状态评估](#health-assessment)
- [资源 Hook](#resource-hooks)
- [忽略差异](#ignore-differences)
- [App of Apps 模式](#app-of-apps-pattern)

## Application CRD 概览

Application CRD 是 ArgoCD 中的核心资源，用于定义如何以及在何处部署应用程序。它将源代码仓库连接到目标 Kubernetes 集群。

### 完整规范

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-application
  namespace: argocd
  labels:
    app.kubernetes.io/name: my-application
    environment: production
  annotations:
    argocd.argoproj.io/sync-wave: "5"
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default

  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: manifests/production

  destination:
    server: https://kubernetes.default.svc
    namespace: my-app

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas

  info:
    - name: Documentation
      value: https://wiki.example.com/my-app
    - name: Owner
      value: platform-team

  revisionHistoryLimit: 10
```

### 关键字段说明

| 字段 | 描述 |
|-------|-------------|
| `project` | 此应用程序所属的 AppProject |
| `source` | 获取 manifests 的位置 |
| `destination` | 目标集群和 namespace |
| `syncPolicy` | 自动同步和重试行为 |
| `ignoreDifferences` | 比较时要忽略的字段 |
| `info` | 用于显示的自定义元数据 |
| `revisionHistoryLimit` | 要保留的部署修订版本数量 |

## 源类型

ArgoCD 支持多种源类型来获取 Kubernetes manifests。

### 纯 YAML/JSON 目录

最简单的源类型——包含 Kubernetes manifests 的目录：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
    directory:
      recurse: true
      exclude: '{*.txt,*.md}'
      include: '*.yaml'
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
```

### Helm Chart

#### 来自 Git 仓库

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-helm-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/helm-charts.git
    targetRevision: HEAD
    path: charts/my-app
    helm:
      releaseName: my-app
      valueFiles:
        - values.yaml
        - values-production.yaml
      values: |
        replicaCount: 3
        image:
          tag: v1.2.3
      parameters:
        - name: service.type
          value: LoadBalancer
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### 来自 Helm 仓库

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: prometheus
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 55.5.0
    helm:
      releaseName: prometheus
      values: |
        prometheus:
          prometheusSpec:
            retention: 30d
            storageSpec:
              volumeClaimTemplate:
                spec:
                  storageClassName: gp3
                  resources:
                    requests:
                      storage: 100Gi
        grafana:
          enabled: true
          adminPassword: admin
        alertmanager:
          enabled: true
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
```

#### 使用外部文件中的 Values

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app-with-external-values
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://charts.bitnami.com/bitnami
    chart: nginx
    targetRevision: 15.4.0
    helm:
      valueFiles:
        - $values/production/nginx-values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: web
```

### Kustomize

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kustomize-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: overlays/production
    kustomize:
      namePrefix: prod-
      nameSuffix: -v1
      namespace: production
      commonLabels:
        environment: production
        team: platform
      commonAnnotations:
        owner: platform-team@example.com
      images:
        - myregistry/myapp:v1.2.3
        - name: myregistry/sidecar
          newTag: v2.0.0
      replicas:
        - name: my-deployment
          count: 5
      patches:
        - target:
            kind: Deployment
            name: my-deployment
          patch: |-
            - op: replace
              path: /spec/template/spec/containers/0/resources/limits/memory
              value: 2Gi
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

### OCI 工件（v2.8+）

从兼容 OCI 的注册表进行部署：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: oci-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-manifests
    targetRevision: v1.0.0
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

### Jsonnet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: jsonnet-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/jsonnet-configs.git
    targetRevision: HEAD
    path: environments/production
    directory:
      jsonnet:
        extVars:
          - name: environment
            value: production
          - name: replicas
            value: "3"
        tlas:
          - name: config
            value: |
              {
                "namespace": "production"
              }
        libs:
          - vendor/
          - lib/
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

## 多个源

ArgoCD v2.6+ 支持在单个应用程序中使用多个源，从而实现复杂的部署场景。

### 将 Helm Chart 与 Git 中的 Values 结合

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: multi-source-app
  namespace: argocd
spec:
  project: default
  sources:
    # Primary source: Helm chart from registry
    - repoURL: https://charts.bitnami.com/bitnami
      chart: postgresql
      targetRevision: 14.0.0
      helm:
        valueFiles:
          - $values/environments/production/postgresql-values.yaml

    # Values source: Git repository
    - repoURL: https://github.com/myorg/helm-values.git
      targetRevision: HEAD
      ref: values

  destination:
    server: https://kubernetes.default.svc
    namespace: database
```

### 在一个应用程序中部署多个应用程序

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-stack
  namespace: argocd
spec:
  project: default
  sources:
    # Monitoring stack
    - repoURL: https://prometheus-community.github.io/helm-charts
      chart: kube-prometheus-stack
      targetRevision: 55.5.0
      helm:
        releaseName: monitoring

    # Logging stack
    - repoURL: https://grafana.github.io/helm-charts
      chart: loki-stack
      targetRevision: 2.10.0
      helm:
        releaseName: logging

    # Custom dashboards from Git
    - repoURL: https://github.com/myorg/dashboards.git
      targetRevision: HEAD
      path: grafana-dashboards

  destination:
    server: https://kubernetes.default.svc
    namespace: observability
```

## 目标配置

### 使用服务器 URL

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### 使用集群名称

```yaml
destination:
  name: production-cluster  # Must match registered cluster name
  namespace: my-app
```

### 自动创建 Namespace

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## 健康状态评估

ArgoCD 使用内置和自定义检查来评估应用程序的健康状态。

### 内置健康检查

ArgoCD 包含针对标准 Kubernetes 资源的健康检查：

| 资源 | 健康状态条件 |
|----------|--------------|
| Deployment | 所有副本均可用 |
| StatefulSet | 所有副本均已就绪 |
| DaemonSet | 期望数量等于已调度数量 |
| ReplicaSet | 所有副本均可用 |
| Service | Endpoints 存在 |
| Ingress | 已分配负载均衡器 |
| PersistentVolumeClaim | 已绑定 |
| Pod | 正在运行且已就绪 |
| Job | 已成功完成 |

### 自定义健康检查（Lua）

在 `argocd-cm` 中定义自定义健康检查：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.customizations.health.certmanager.io_Certificate: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.conditions ~= nil then
        for i, condition in ipairs(obj.status.conditions) do
          if condition.type == "Ready" and condition.status == "False" then
            hs.status = "Degraded"
            hs.message = condition.message
            return hs
          end
          if condition.type == "Ready" and condition.status == "True" then
            hs.status = "Healthy"
            hs.message = "Certificate is ready"
            return hs
          end
        end
      end
    end
    hs.status = "Progressing"
    hs.message = "Waiting for certificate"
    return hs

  resource.customizations.health.argoproj.io_Rollout: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.phase == "Healthy" then
        hs.status = "Healthy"
        hs.message = "Rollout is healthy"
      elseif obj.status.phase == "Paused" then
        hs.status = "Suspended"
        hs.message = "Rollout is paused"
      elseif obj.status.phase == "Progressing" then
        hs.status = "Progressing"
        hs.message = "Rollout in progress"
      else
        hs.status = "Degraded"
        hs.message = obj.status.message or "Rollout degraded"
      end
    else
      hs.status = "Progressing"
      hs.message = "Waiting for rollout status"
    end
    return hs
```

### AWS 资源的健康检查（ACK）

```yaml
resource.customizations.health.s3.services.k8s.aws_Bucket: |
  hs = {}
  if obj.status ~= nil then
    if obj.status.ackResourceMetadata ~= nil and obj.status.ackResourceMetadata.arn ~= nil then
      hs.status = "Healthy"
      hs.message = "Bucket created: " .. obj.status.ackResourceMetadata.arn
    else
      hs.status = "Progressing"
      hs.message = "Waiting for bucket creation"
    end
  else
    hs.status = "Progressing"
    hs.message = "Waiting for status"
  end
  return hs
```

## 资源 Hook

资源 Hook 允许在同步期间的特定时机运行 Job。

### Hook 类型

| Hook | 执行时机 |
|------|---------------|
| `PreSync` | 同步开始前 |
| `Sync` | 同步期间（在 PreSync 之后） |
| `PostSync` | 同步成功后 |
| `SyncFail` | 同步失败后 |
| `Skip` | 同步期间跳过 |

### Hook 删除策略

| 策略 | 行为 |
|--------|----------|
| `HookSucceeded` | Hook 成功后删除 |
| `HookFailed` | Hook 失败后删除 |
| `BeforeHookCreation` | 新 Hook 运行前删除 |

### 数据库迁移 Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
    argocd.argoproj.io/sync-wave: "-5"
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: myapp/migrations:v1.2.3
          command: ["./migrate.sh"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
```

### Slack 通知 Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: notify-deployment
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              curl -X POST $SLACK_WEBHOOK \
                -H 'Content-Type: application/json' \
                -d '{"text":"Deployment completed successfully!"}'
          env:
            - name: SLACK_WEBHOOK
              valueFrom:
                secretKeyRef:
                  name: slack-webhook
                  key: url
```

### 健康检查 Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: smoke-test
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              for i in $(seq 1 10); do
                if curl -sf http://my-service:8080/health; then
                  echo "Health check passed"
                  exit 0
                fi
                echo "Attempt $i failed, retrying..."
                sleep 5
              done
              echo "Health check failed"
              exit 1
```

## 忽略差异

将 ArgoCD 配置为在比较期间忽略特定差异。

### 按 JSON Pointer

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
      - /spec/replicas
      - /spec/template/spec/containers/0/image
```

### 按 JQ 路径表达式

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jqPathExpressions:
      - .spec.template.spec.containers[].resources
      - .metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
```

### 按名称

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
      - /spec/replicas
```

### 托管字段（Kubernetes Server-Side Apply）

```yaml
ignoreDifferences:
  - group: "*"
    kind: "*"
    managedFieldsManagers:
      - kube-controller-manager
      - cluster-autoscaler
```

### argocd-cm 中的全局忽略

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.compareoptions: |
    ignoreAggregatedRoles: true
    ignoreResourceStatusField: all

  resource.customizations.ignoreDifferences.all: |
    managedFieldsManagers:
      - kube-controller-manager
    jsonPointers:
      - /metadata/annotations/kubectl.kubernetes.io~1last-applied-configuration
```

## App of Apps 模式

App of Apps 模式允许通过单个父应用程序管理多个应用程序。

### 目录结构

```
├── apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── namespace.yaml
│       ├── monitoring.yaml
│       ├── logging.yaml
│       ├── ingress.yaml
│       └── cert-manager.yaml
```

### 父应用程序

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-apps
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/platform.git
    targetRevision: HEAD
    path: apps
    helm:
      values: |
        environment: production
        cluster: prod-us-west-2
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 子应用程序模板

```yaml
# apps/templates/monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monitoring-{{ .Values.environment }}
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 55.5.0
    helm:
      values: |
        prometheus:
          prometheusSpec:
            retention: {{ .Values.monitoring.retention | default "15d" }}
            replicas: {{ .Values.monitoring.replicas | default 2 }}
        grafana:
          enabled: true
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Values 文件

```yaml
# apps/values.yaml
environment: production
cluster: prod-us-west-2

monitoring:
  retention: 30d
  replicas: 3

logging:
  retention: 7d

ingress:
  enabled: true
  class: alb
```

### App of Apps 的同步波次

控制子应用程序的部署顺序：

```yaml
# apps/templates/cert-manager.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cert-manager
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-3"  # Deploy first
spec:
  # ...

# apps/templates/ingress.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ingress-controller
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-2"  # Deploy second
spec:
  # ...

# apps/templates/monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monitoring
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "0"  # Deploy last
spec:
  # ...
```

## 修订历史和回滚

### 查看历史记录

```bash
# CLI
argocd app history my-app

# Output
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ghi9012
```

### 回滚

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### 声明式回滚

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: abc1234  # Specific commit for rollback
    path: manifests
```

## 测验

要测试所学内容，请尝试 [ArgoCD 应用程序测验](../../quizzes/gitops/argocd/02-applications-quiz.md)。
