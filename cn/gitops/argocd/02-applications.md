# ArgoCD 应用

> **审查基线**：Argo CD 3.5.2；发布说明审查后更新至补丁版本 3.5.4（未重新运行示例）
> **最后更新**：October 16, 2026

## 目录
- [Application CRD 概览](#application-crd-overview)
- [源类型](#source-types)
- [多个源](#multiple-sources)
- [目标配置](#destination-configuration)
- [健康状态评估](#health-assessment)
- [资源钩子](#resource-hooks)
- [忽略差异](#ignore-differences)
- [应用集合模式](#app-of-apps-pattern)

## Application CRD 概览

这些示例是相互独立的配置。请将 myorg/accounts/clusters/paths 替换为实际获准使用的源。根据具体场景选择 source/sources、渲染器和 destination.server/name，而不要一次启用所有备选项。

Application CRD 是 ArgoCD 的核心资源，用于定义如何以及在何处部署应用。它将源代码仓库连接到目标 Kubernetes 集群。

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

Application.status 是由控制器报告的状态。要在控制平面命名空间之外创建 Application，管理员必须启用 application.namespaces 和 AppProject 的 sourceNamespaces，并配置适当的 RBAC。

### 关键字段说明

| 字段 | 说明 |
|-------|-------------|
| `project` | 此应用所属的 AppProject |
| `source` | 从何处获取清单 |
| `destination` | 目标集群和命名空间 |
| `syncPolicy` | 自动同步和重试行为 |
| `ignoreDifferences` | 比较时忽略的字段 |
| `info` | 用于显示的自定义元数据 |
| `revisionHistoryLimit` | 保留的部署修订版本数量 |

## 源类型

ArgoCD 支持多种源类型来获取 Kubernetes 清单。

### 纯 YAML/JSON 目录

最简单的源类型——包含 Kubernetes 清单的目录：

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

固定版本的小型 podinfo Chart 示例展示了源格式。最终的 replicaCount 为 3，因为 parameters 会覆盖 valuesObject。valuesObject 提供结构化内联值；它不会自动读取环境变量。

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

优先级为 parameters → valuesObject → values → valueFiles → Chart 默认值。建议只使用一种内联表示；如果存在 valuesObject，它将提供内联值。只有在确有需要时才启用 passCredentials，因为它可能会将凭据转发到其他域。此基线使用捆绑的 Helm 4；不要随意选择 v2/v3。

#### 使用外部文件中的值

$values 引用需要在 spec.sources 中存在匹配的 ref 源。值仓库/文件必须存在且已获授权。

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

### OCI 工件

通用 OCI 源使用 oci:// URI 和已展开工件中的路径。请将此账号/仓库/标签替换为已发布的工件。普通容器镜像不会自动成为清单源。

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

Argo CD 3.5.4 要求包含一个具有受支持媒体类型的层：默认情况下为 application/vnd.oci.image.layer.v1.tar+gzip 或 Helm Chart 内容 tar+gzip。其他类型请通过 ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES 和工件结构进行验证。截至 3.5.4，超过 4 MiB 的 OCI 清单将被拒绝（GHSA-w996-f2wq-x9c6）。

Helm OCI 格式使用 chart 字段，且仓库 URL **不带 oci://**。这是 Application.spec 下的源片段。

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

凭据配置应与源类型匹配：通用 OCI 使用 type: oci 和 oci:// URL；Helm OCI 使用 type: helm、enableOCI: "true" 和不带协议的 URL。ECR 需要注册表权限，并且需要续期/应用其 12 小时令牌；授予 IRSA 权限本身不会更新 Secret。

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

如果存在 sources，单数形式的 source 将被忽略。可将一个相关应用的配置组合在一起，例如 Chart 加值仓库；对于独立管理的平台栈，请使用 ApplicationSet/App of Apps。

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

ref: values 会将 $values 映射到该 Git 仓库根目录。不设置 path 时，它只提供值；设置 path 时，它也会在该路径下生成清单。ref 源不能同时指定 chart。重复的 group/kind/name/namespace 资源将采用最后一个源，并触发 RepeatedResourceWarning；这不是自动的逐字段合并。

## 目标配置

对于已注册的目标，请选择 server 或 name。destination.namespace 为未指定自身命名空间的命名空间级资源提供默认命名空间；CreateNamespace 只会创建该目标命名空间，不会创建 Chart 中明确嵌入的所有命名空间。使用 managedNamespaceMetadata 时，应同时配置命名空间创建，并在更新现有命名空间前审查其所有权。

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

## 健康状态评估

Synced 表示期望字段与实际字段的比较结果，并不证明服务能够处理请求。Healthy 状态取决于配置的各资源检查。没有检查的自定义资源可能不会纳入应用健康状态，需要为其定义适当的检查。

### 内置健康检查

以下内容概述了 3.5.4 实现中的重要检查，并非仅基于副本计数器的完整判定条件。

| 资源 | 重要检查 |
|---|---|
| Deployment | 已观测到的 generation、发布进度/失败状态、已更新/可用副本 |
| StatefulSet | generation、更新策略/分区、修订版本和副本状态 |
| DaemonSet | generation 以及期望/已更新/可用 Pod 数量 |
| Pod | 阶段、就绪状态和容器终止/失败状态 |
| Service | LoadBalancer 会等待地址；其他类型不会验证端点 |
| Ingress | 控制器报告的 loadBalancer 地址状态 |
| PVC | 绑定状态 |
| Job | 未完成时为 Progressing，失败时为 Degraded，完成时为 Healthy，暂停时为 Suspended |

### 自定义健康检查

不要用简单的阶段比较替换捆绑的 Rollout/cert-manager Certificate 检查。Certificate 组为 cert-manager.io；其捆绑检查会在 Ready 之前处理 Issuing。下面的 ACK 示例会在状态/条件缺失时返回 Progressing，并且不会将 ARN 存在等同于 Healthy。请根据你的 ACK 版本验证其提供的 Ready/ACK.ResourceSynced 和错误条件。示例优先使用 Ready（若存在），否则回退到 ACK.ResourceSynced。

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

此检查解释的是控制器报告的状态；它不会直接查询 AWS。请将此键合并到现有的 argocd-cm 中，并使用真实 CR 测试缺失/等待/就绪/错误/新规格等状态。EKS 托管的 Argo CD 提供 ACK/kro 检查，因此请先检查现有检查项和支持的配置。

## 资源钩子

PostSync 会等待 Sync 成功，并等待相关 Healthy 资源就绪。显式选择资源进行同步时不会运行钩子。在 3.5.4 中，ApplyOutOfSyncOnly 仍会运行钩子并记录历史。SyncFail 用于处理符合条件的同步失败；不要依赖它作为所有错误（包括清单生成失败）的可靠清理/备份路径。

资源钩子可在同步期间的特定阶段运行 Job。

### 钩子类型

| 钩子 | 执行时机 |
|------|---------------|
| `PreSync` | 同步开始前 |
| `Sync` | 同步期间（PreSync 之后） |
| `PostSync` | Sync 成功且资源 Healthy 之后 |
| `SyncFail` | 同步失败后 |
| `Skip` | 跳过清单应用 |
| `PreDelete` | 随 Application 删除资源之前 |
| `PostDelete` | Application 资源删除之后 |

### 钩子删除策略

| 策略 | 行为 |
|--------|----------|
| `HookSucceeded` | 钩子成功后删除 |
| `HookFailed` | 钩子失败后删除 |
| `BeforeHookCreation` | 新钩子运行前删除 |

### 数据库迁移钩子

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

### Slack 通知钩子

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
          image: curlimages/curl:8.23.0
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

### 健康检查钩子

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
          image: curlimages/curl:8.23.0
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

固定名称的 Job 需要 BeforeHookCreation 等生命周期规则才能重复运行。清理前，请将失败日志保存到外部；HookSucceeded 清理遵循 Argo 的同步阶段/结果语义。请准备好迁移镜像、数据库 Secret 和 ServiceAccount，并单独验证幂等性、锁定行为和回滚兼容性。钩子失败不会自动回退数据库或现有 Deployment。PreDelete/PostDelete 适用于删除 Application，不适用于普通同步修剪。

## 忽略差异

仅排除由其他已知控制器管理的特定字段。此 Application.spec 片段会忽略生产环境中 my-deployment 上由 HPA 管理的副本数。

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

ignoreDifferences 通常只影响比较。RespectIgnoreDifferences=true 会将其扩展到同步，但在没有实际资源的情况下首次创建时，仍会应用期望清单。针对镜像、Secret、整个资源或所有管理器设置宽泛规则，可能会掩盖重要的配置漂移。

对于 webhook 数组，请按名称而不是固定索引进行选择，并限定资源名称。只有在已知 CA 注入控制器和 webhook 身份时才使用此规则。

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

全局 resource.customizations.ignoreDifferences 设置会影响每个 Application。优先使用应用级规则；只有在检查过 managedFieldsManagers 实际管理的字段之后，才选择它。

## 应用集合模式

App of Apps 是一种管理性引导模式。父级源的写入者可能会影响管理命名空间中权限强大的 Application/AppProject；请限制写入、审查和目标权限。父级/子级 finalizer 和修剪可能导致级联删除。按顺序创建子 Application 本身并不能确保子工作负载就绪；请验证 Application 健康状态传播、同步策略和 wave 行为。

App of Apps 模式可通过单个父 Application 管理多个应用。

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

此监控子应用固定使用 kube-prometheus-stack 90.0.0。请审查该 Chart 的升级/CRD 要求，并单独配置监控容量。在 monitoring 命名空间中预先创建受保护的 grafana-admin Secret，其中包含 admin-user/admin-password 键；不要将管理员凭据放入父级 Git 值中。

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

### App of Apps 的同步 Waves

以下是仅包含元数据的片段；请将它们与完整的子级 spec 合并。对子 Application 的创建顺序并不能保证子工作负载就绪：请配置/验证子 Application 健康状态传播和同步策略。

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

启用自动同步时不能使用历史回滚。请先在实际的 Git/ApplicationSet 所有者中审查策略。回滚不会更新 Git，因此后续协调可能会恢复 Git 状态。请通过获批的 Git revert/修订版本更改来持久化预期更改；数据库/外部状态恢复需要另行处理。

### 查看历史

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

请从实际历史记录中选择一个 ID。应用先前的清单修订版本与修剪多余资源是两个独立的决定。

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

测试一下你学到的内容，试试 [ArgoCD 应用测验](../../quizzes/gitops/argocd/02-applications-quiz.md)。

## 版本审查来源

- [3.5.4 源和 Helm](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/helm.md)
- [多个源](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/multiple_sources.md)
- [OCI 源规则](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/oci.md)
- [同步选项](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [阶段、Wave 和钩子](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [Service 健康状态实现](https://github.com/argoproj/argo-cd/blob/v3.5.4/gitops-engine/pkg/health/health_service.go)
- [ACK 条件定义](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
