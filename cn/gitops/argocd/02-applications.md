# ArgoCD 应用程序

> **审查基线**：Argo CD 3.5.2；经发布说明审查后更新至补丁版本 3.5.4（示例未重新运行）
> **最后更新**：October 12, 2026

## 目录
- [Application CRD 概述](#application-crd-overview)
- [源类型](#source-types)
- [多个源](#multiple-sources)
- [目标配置](#destination-configuration)
- [健康状况评估](#health-assessment)
- [资源 Hook](#resource-hooks)
- [忽略差异](#ignore-differences)
- [App of Apps 模式](#app-of-apps-pattern)

## Application CRD 概述

示例为相互独立的配置。请将 myorg/accounts/clusters/paths 替换为实际已获授权的源。请根据场景选择 source/sources、渲染器和 destination.server/name，而非一次性启用所有替代方案。

Application CRD 是 ArgoCD 中定义如何及在何处部署应用程序的核心资源。它将源代码仓库连接到目标 Kubernetes 集群。

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

Application.status 是由控制器报告的状态。若要在控制平面命名空间外创建 Application，管理员必须启用 application.namespaces 和 AppProject sourceNamespaces，并配置适当的 RBAC。

### 关键字段说明

| 字段 | 说明 |
|-------|-------------|
| `project` | 此应用程序所属的 AppProject |
| `source` | 获取清单的位置 |
| `destination` | 目标集群和命名空间 |
| `syncPolicy` | 自动同步和重试行为 |
| `ignoreDifferences` | 比较时要忽略的字段 |
| `info` | 用于显示的自定义元数据 |
| `revisionHistoryLimit` | 要保留的部署修订版本数量 |

## 源类型

ArgoCD 支持多种用于获取 Kubernetes 清单的源类型。

### 纯 YAML/JSON 目录

最简单的源类型：包含 Kubernetes 清单的目录：

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
          value: ClusterIP
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### 来自 Helm 仓库

固定版本的小型 podinfo chart 用于说明源格式。最终的 replicaCount 为 3，因为 parameters 会覆盖 valuesObject。valuesObject 提供结构化内联值；它不会自动读取环境变量。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-helm
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valuesObject:
        replicaCount: 2
        service:
          type: ClusterIP
        ui:
          message: "Managed by Argo CD"
      parameters:
      - name: replicaCount
        value: "3"
      passCredentials: false
      skipCrds: false
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

优先级为 parameters → valuesObject → values → valueFiles → chart 默认值。首选使用一种内联表示形式；存在 valuesObject 时，它提供内联值。仅在需要时启用 passCredentials，因为它可能会将凭据转发到其他域。此基线使用内置 Helm 4；请勿随意选择 v2/v3。

#### 使用外部文件中的值

$values 引用要求 spec.sources 中存在匹配的 ref 源。值仓库/文件必须存在且已获授权。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-with-values
  namespace: argocd
spec:
  project: default
  sources:
  - repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valueFiles:
      - $values/environments/production/podinfo-values.yaml
  - repoURL: https://github.com/myorg/helm-values.git
    targetRevision: main
    ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
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
      labelWithoutSelector: true
      labelIncludeTemplates: true
      commonLabels:
        environment: production
        team: platform
      commonAnnotations:
        owner: platform-team@example.com
      images:
        - myregistry/myapp:v1.2.3
        - myregistry/sidecar:v2.0.0
      replicas:
        - name: my-deployment
          count: 5
      patches:
        - target:
            kind: Deployment
            name: my-deployment
          patch: |-
            - op: add
              path: /spec/progressDeadlineSeconds
              value: 600
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

### OCI 制品

通用 OCI 源使用 oci:// URI 及已展开制品内部的路径。请将此账户/仓库/tag 替换为已发布的制品。普通容器镜像不会自动成为清单源。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: oci-manifests
  namespace: argocd
spec:
  project: default
  source:
    repoURL: oci://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-manifests
    targetRevision: v1.0.0
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

Argo CD 3.5.4 要求一个具有受支持媒体类型的层：默认是 application/vnd.oci.image.layer.v1.tar+gzip 或 Helm chart 内容 tar+gzip。请使用 ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES 和制品结构验证其他类型。截至 3.5.4，大于 4 MiB 的 OCI 清单会被拒绝（GHSA-w996-f2wq-x9c6）。

Helm OCI 形式使用 chart 字段和**不含 oci:// 的**仓库 URL。这是 Application.spec 下的源片段。

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

请将凭据与源类型相匹配：通用 OCI 使用 type: oci 和 oci:// URL；Helm OCI 使用 type: helm、enableOCI: "true" 和不带 scheme 的 URL。ECR 需要注册表权限以及对其 12 小时 token 的续期/应用；授予 IRSA 权限本身不会更新 Secret。

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
            code: true
        tlas:
          - name: config
            code: true
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

存在 sources 时，会忽略单数形式的 source。请针对一个相关应用程序组合配置，例如 chart 加值仓库；对于独立管理的平台堆栈，请使用 ApplicationSet/App of Apps。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-with-values
  namespace: argocd
spec:
  project: default
  sources:
  - repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valueFiles:
      - $values/environments/production/podinfo-values.yaml
  - repoURL: https://github.com/myorg/helm-values.git
    targetRevision: main
    ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

ref: values 会将 $values 映射到该 Git 仓库根目录。不含 path 时，它只提供值；包含 path 时，它还会在该位置生成清单。ref 源不能同时指定 chart。重复的 group/kind/name/namespace 资源使用最后一个源，并引发 RepeatedResourceWarning；这不是自动逐字段合并。

## 目标配置

为已注册目标选择 server 或 name。destination.namespace 为缺少自身命名空间的命名空间范围资源提供默认值；CreateNamespace 仅创建该目标命名空间，而不是创建 chart 中显式嵌入的每个命名空间。请结合命名空间创建使用 managedNamespaceMetadata，并在更新现有命名空间前审查所有权。

### 使用 Server URL

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

### 自动创建命名空间

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## 健康状况评估

Synced 描述比较后的期望/实时字段，而非服务可处理请求的证明。Healthy 遵循为每个资源配置的检查。没有检查的自定义资源可能会从应用程序健康状况中省略，因此需要适当的定义。

### 内置健康检查

以下总结了重要的 3.5.4 实现检查，而非基于单个副本计数的完整谓词。

| 资源 | 重要检查 |
|---|---|
| Deployment | 已观察的 generation、rollout 进度/失败、已更新/可用副本 |
| StatefulSet | generation、更新策略/partition、修订版本和副本状态 |
| DaemonSet | generation 以及期望/已更新/可用 Pod 数量 |
| Pod | phase、就绪状态以及容器终止/失败 |
| Service | LoadBalancer 等待地址；其他类型不验证端点 |
| Ingress | 由控制器报告的 loadBalancer 地址状态 |
| PVC | Bound 状态 |
| Job | 未完成为 Progressing，失败为 Degraded，完成为 Healthy，暂停为 Suspended |

### 自定义健康检查

请勿用简单的 phase 比较替换内置的 Rollout/cert-manager Certificate 检查。Certificate group 是 cert-manager.io；其内置检查会在 Ready 之前处理 Issuing。以下 ACK 示例会对缺少 status/conditions 的资源返回 Progressing，也不会将 ARN 存在等同于 Healthy。请验证 ACK 版本提供的 Ready/ACK.ResourceSynced 和错误条件。该示例在 Ready 存在时优先使用它，否则回退到 ACK.ResourceSynced。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  resource.customizations.health.s3.services.k8s.aws_Bucket: |
    local hs = {status = "Progressing", message = "Waiting for ACK reconciliation"}
    local conditions = {}
    if obj.status ~= nil and obj.status.conditions ~= nil then
      conditions = obj.status.conditions
    end
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.Terminal" and condition.status == "True" then
        hs.status = "Degraded"
        hs.message = condition.message or "ACK reported a terminal error"
        return hs
      end
    end
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.Recoverable" and condition.status == "True" then
        hs.message = condition.message or "ACK is retrying a recoverable error"
        return hs
      end
    end
    local synchronized = nil
    local ready = nil
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.ResourceSynced" then synchronized = condition end
      if condition.type == "Ready" then ready = condition end
    end
    local reported = ready or synchronized
    if reported ~= nil then
      hs.message = reported.message or hs.message
      if reported.status == "True" then
        hs.status = "Healthy"
        hs.message = reported.message or "ACK reports the resource synchronized"
      end
    end
    return hs
```

这会解释由控制器报告的状态；它不会直接查询 AWS。请将该键合并到现有 argocd-cm 中，并使用真实 CR 测试缺失/等待/就绪/错误/新规范状态。EKS 托管的 Argo CD 提供 ACK/kro 检查，因此请先检查其现有检查和受支持的配置。

## 资源 Hook

PostSync 会等待成功的 Sync 和相关的 Healthy 资源。显式资源选择性同步不会运行 Hook。在 3.5.4 中，ApplyOutOfSyncOnly 仍会运行 Hook 并记录历史记录。SyncFail 处理符合条件的同步失败；请勿将其视为每个错误（包括清单生成失败）的有保障清理/备份路径。

资源 Hook 允许在同步期间的特定时点运行 Job。

### Hook 类型

| Hook | 执行时机 |
|------|---------------|
| `PreSync` | 同步开始之前 |
| `Sync` | 同步期间（PreSync 之后） |
| `PostSync` | Sync 成功且资源为 Healthy 后 |
| `SyncFail` | 同步失败后 |
| `Skip` | 跳过清单应用 |
| `PreDelete` | 随 Application 删除资源之前 |
| `PostDelete` | Application 资源删除后 |

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
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
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
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:8.22.0
          command:
            - sh
            - -c
            - |
              curl --fail --show-error --silent --connect-timeout 5 --max-time 20 -X POST "$SLACK_WEBHOOK" \
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
          image: curlimages/curl:8.22.0
          command:
            - sh
            - -c
            - |
              for i in $(seq 1 10); do
                if curl --fail --show-error --silent --connect-timeout 3 --max-time 10 http://my-service:8080/health; then
                  echo "Health check passed"
                  exit 0
                fi
                echo "Attempt $i failed, retrying..."
                sleep 5
              done
              echo "Health check failed"
              exit 1
```

固定名称的 Job 需要诸如 BeforeHookCreation 的生命周期规则，以支持重复运行。请在清理前于外部保留失败日志；HookSucceeded 清理遵循 Argo 同步阶段/结果语义。请准备迁移镜像、数据库 Secret 和 ServiceAccount，并分别验证幂等性、锁定和回滚兼容性。Hook 失败不会自动还原数据库或现有 Deployment。PreDelete/PostDelete 适用于 Application 删除，而不是常规同步修剪。

## 忽略差异

仅排除由已知其他控制器拥有的特定字段。此 Application.spec 片段会忽略 production 中由 HPA 管理的 my-deployment 副本数。

```yaml
spec:
  ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
    - /spec/replicas
  syncPolicy:
    syncOptions:
    - RespectIgnoreDifferences=true
```

ignoreDifferences 通常会影响比较。RespectIgnoreDifferences=true 将其扩展至同步，但在没有实时资源的初始创建期间，仍会应用期望的清单。广泛的镜像、Secret、整个资源或所有 manager 规则可能隐藏重要的偏差。

对于 webhook 数组，请按名称而非固定索引选择，并同时限定资源名称。仅在已知 CA 注入控制器和 webhook 身份时使用此方法。

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

全局 resource.customizations.ignoreDifferences 设置会影响每个 Application。首选应用程序范围的规则；只有在检查该 manager 实际拥有的字段后，才选择 managedFieldsManagers。

## App of Apps 模式

App of Apps 是一种管理引导模式。父源写入者可影响管理命名空间中权限强大的 Applications/AppProjects；请限制写入/审查/目标权限。父/子 finalizer 和修剪可能会级联删除。按顺序创建子 Application 本身并不能确保子工作负载就绪；请验证 Application 健康状况传播、同步策略和 wave 行为。

App of Apps 模式允许从单个父应用程序管理多个应用程序。

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

### 父 Application

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

### 子 Application 模板

此 monitoring 子项固定使用 kube-prometheus-stack 90.0.0。请审查该 chart 的升级/CRD 要求，并单独配置监控容量。在 namespace monitoring 中预先创建包含 admin-user/admin-password 键且受保护的 grafana-admin Secret；请勿将管理员凭据放入父 Git values 中。

```yaml
---
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
    targetRevision: 90.0.0
    helm:
      values: |
        prometheus:
          prometheusSpec:
            retention: {{ .Values.monitoring.retention | default "15d" }}
            replicas: {{ .Values.monitoring.replicas | default 2 }}
        grafana:
          enabled: true
          admin:
            existingSecret: grafana-admin
            userKey: admin-user
            passwordKey: admin-password
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

### App of Apps 的同步 Wave

以下为仅含元数据的片段；请将它们与完整的子 Application 规范结合使用。对子 Application 创建进行排序并不保证子工作负载就绪：请配置/验证子 Application 健康状况传播和同步策略。

```yaml
# Merge into the corresponding complete child Application metadata.
metadata:
  name: cert-manager
  annotations:
    argocd.argoproj.io/sync-wave: "-3"
---
metadata:
  name: ingress-controller
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
---
metadata:
  name: monitoring
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

## 修订历史和回滚

启用自动同步时，无法使用历史回滚。请先审查其实际的 Git/ApplicationSet 所有者中的策略。回滚不会更新 Git，因此后续协调可能恢复 Git 状态。请通过获批准的 Git revert/修订版本更改来持久化预期变更；数据库/外部状态恢复另行处理。

### 查看历史记录

```bash
# CLI
argocd app history my-app

```

示例输出（不是 shell 命令）：

```text
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ab89012
```

### 回滚

从实际历史记录中选择一个 ID。应用先前的清单修订版本和修剪额外资源是两个独立决策。

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
  project: default
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: abc1234  # Specific commit for rollback
    path: manifests
```

## 测验

为测试所学内容，请尝试 [ArgoCD 应用程序测验](../../quizzes/gitops/argocd/02-applications-quiz.md)。

## 版本化审查来源

- [3.5.4 源和 Helm](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/helm.md)
- [多个源](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/multiple_sources.md)
- [OCI 源规则](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/oci.md)
- [同步选项](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [阶段、wave 和 Hook](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [Service 健康状况实现](https://github.com/argoproj/argo-cd/blob/v3.5.4/gitops-engine/pkg/health/health_service.go)
- [ACK 条件定义](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
