# ArgoCD 同步策略

> **审查基线**: Argo CD 3.5.2；在审查发行说明后更新至补丁版本 3.5.4（示例未重新运行）
> **最后更新**: October 12, 2026

## 目录
- [手动同步与自动同步](#manual-vs-automated-sync)
- [自动同步策略](#auto-sync-policies)
- [同步选项](#sync-options)
- [同步波次和阶段](#sync-waves-and-phases)
- [同步窗口](#sync-windows)
- [差异比较自定义](#diffing-customization)
- [重试策略](#retry-policies)
- [选择性同步](#selective-sync)

## 手动同步与自动同步

示例是彼此独立的策略片段。请保留实际 Application 的 source/destination/project，并仅选择所需选项。同步会应用变更；刷新会从源/缓存更新比较结果。Synced 与健康状态和实际服务可用性是不同的概念。

ArgoCD 支持两种同步模式：手动和自动。

### 手动同步

在手动模式下，用户必须显式触发同步：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: manual-sync-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  # No syncPolicy.automated = manual sync
```

触发手动同步：

```bash
# Via CLI
argocd app sync my-app

# Sync specific resources only
argocd app sync my-app --resource 'apps:Deployment:my-deployment'

# Preview changes; pruning and force are separate, potentially destructive decisions
argocd app sync my-app --dry-run
```

### 自动同步

在自动模式下，ArgoCD 会在检测到变更时自动同步：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: auto-sync-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated: {}  # Enable auto-sync with defaults
```

![Argo CD 持续比较 Git 仓库中的期望状态与 Kubernetes 集群的实时状态；当检测到 OutOfSync 差异时，它会应用变更，使实时状态再次与 Git 一致。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-0.html)

## 自动同步策略

automated: {} 或省略/null 的 enabled 标志会启用自动同步；enabled: false 会将其禁用。仅实时状态的漂移修复需要 selfHeal，而 prune 是独立的。默认情况下，失败的相同 commit/parameter 组合不会被无限重试；请配置重试策略。对于由 ApplicationSet 管理的 Application，请变更其所属模板。

### 清理

自动删除 Git 中不再存在的资源：

```yaml
syncPolicy:
  automated:
    prune: true
```

**使用场景**：确保集群状态与 Git 仓库完全一致。会移除孤立资源。

清理影响的是 Application 跟踪的资源，而不是集群中的每个孤立资源。PruneLast 会改变排序；它无法保护数据，也不能替代对删除操作的审查。

### 自愈

自动还原对集群所做的手动变更：

```yaml
syncPolicy:
  automated:
    selfHeal: true
```

**使用场景**：防止手动 kubectl 变更或其他工具造成配置漂移。

![序列图：用户使用 kubectl 手动扩缩容一个 Deployment，Argo CD 检测到状态变更，从 Git 读取期望的副本数，并重新应用它，使 Kubernetes 自愈回 Git 声明的状态。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-1.html)

### 允许为空

允许没有资源的应用程序：

```yaml
syncPolicy:
  automated:
    allowEmpty: true
```

启用自动清理时，allowEmpty 可以在渲染结果返回空集合时允许删除所有受管资源。它并非通用的引导要求。

### 完整自动同步配置

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: fully-automated-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true        # Remove orphaned resources
      selfHeal: true     # Revert manual changes
      allowEmpty: false  # Prevent auto-prune from deleting everything on an empty render
```

## 同步选项

同步选项可对同步行为进行细粒度控制。

### 可用同步选项

| 选项 | 描述 | 默认值 |
|--------|-------------|---------|
| `Validate` | 根据 schema 验证资源 | true |
| `CreateNamespace` | 若 namespace 缺失则创建 | false |
| `PrunePropagationPolicy` | 删除传播策略 | foreground |
| `PruneLast` | 在所有其他同步之后清理 | false |
| `Replace` | 使用 replace 而非 apply | false |
| `FailOnSharedResource` | 如果另一个 Argo CD Application 跟踪该资源则失败 | false |
| `ApplyOutOfSyncOnly` | 仅应用不同步的资源 | false |
| `ServerSideApply` | 使用服务器端应用 | false |
| `RespectIgnoreDifferences` | 在同步中遵循 ignoreDifferences | false |

`Validate=false` 会跳过 apply 时的 schema 验证；它不会安装缺失的 CRD。当某个 CR 的 CRD 在同一次同步中安装时，Argo CD 会自动跳过该 CR 的 dry run。仅在合理的情况下（例如 CRD 由其他 controller 创建）使用 `SkipDryRunOnMissingResource=true`，并确认 CRD 可用。

`PruneLast=true` 会在部署其他资源且其处于 Healthy 后，于最后一个隐式波次中安排清理。`FailOnSharedResource=true` 会检查是否被另一个 Argo CD Application 跟踪；它无法检测与其他 Kubernetes controller 或 Flux 的所有所有权冲突。

### Application 级选项

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: main
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
      - Validate=true
      - ApplyOutOfSyncOnly=true
```

### 资源级选项

通过 annotations 将同步选项应用于特定资源：

```yaml
# Merge into an existing complete resource manifest.
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

### 服务器端应用

Argo CD 3.5.4 会调用 --server-side --force-conflicts。会跟踪字段所有权，但这并不保证冲突会被拒绝；请审查可能发生的所有权接管。

使用 Kubernetes 服务器端应用以获得更好的冲突检测：

```yaml
syncPolicy:
  syncOptions:
    - ServerSideApply=true
```

或按资源设置：

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

**优势**：
- 更好的字段所有权跟踪
- Argo CD 可以强制解决所有权冲突；请检查预期的管理者边界
- 与 CRD 和 webhook 配合良好

### Replace 和 Force

Replace 会选择 kubectl replace/create。它不会自动使不可变字段可编辑。Force=true 与 Replace=true 组合可以删除/重建对象，是一项独立的破坏性选择：

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: Replace=true
```

不可变更改需要特定于资源的迁移/重建计划。不要将此作为 PVC storage-class 迁移的捷径。删除前请审查保留策略/数据/可用性。Replace 的优先级高于 ServerSideApply。

## 同步波次和阶段

同步波次控制资源的应用顺序。

### 波次的工作方式

资源按波次编号分组并依序同步：
1. 按阶段、波次、kind 和名称排序。
2. 负数 Sync 波次不会在 PreSync 阶段之前运行。
3. 波次推进遵循同步/健康状态；不要依赖同一波次的物理并发来处理依赖关系。当就绪状态必须阻止后续工作时，自定义资源需要有意义的健康检查。

![Argo CD 同步波次的工作流图，按升序应用：波次 -2 为 CRD，波次 -1 为 Namespace 和 ServiceAccount，默认波次 0 为 ConfigMap、Secret 和 Deployment，然后波次 1 为 Service 和 Ingress；每个波次都会等待前一波次处于健康状态。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-2.html)

### 设置同步波次

将此片段合并到完整资源 manifest 的 metadata 中。后文提供完整示例。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
```

### 将波次与 Hook 结合

PreSync 会在每个普通 Sync 波次之前运行。下方现有的 service、namespace、DB Secret 和迁移 image 必须已准备就绪；PreSync 不能假定可以访问在后续 Sync 波次中创建的数据库。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: dependency-preflight
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/sync-wave: "-5"
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 60
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      containers:
      - name: check
        image: curlimages/curl:8.22.0
        command: ["curl"]
        args: ["--fail", "--show-error", "--silent", "--connect-timeout", "5", "--max-time", "20", "http://existing-data-service:8080/health"]
---
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/sync-wave: "-3"
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 300
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: myapp/migrations:v1.0.0
        command: ["./migrate.sh"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: existing-db-credentials
              key: url
```

仅将 pg_dump 输出到 stdout 的 Job 并不是可恢复的备份流程。请使用持久化加密存储、完成验证和恢复测试。验证迁移的幂等性/锁定/恢复；PostSync 失败不会自动回滚。

### 最小可用排序示例

此最小示例在同一 Sync 阶段内按 Namespace → ConfigMap → Service → 具有就绪检查的 Deployment 排序。处于 Healthy 状态的 Service 对象并不能证明 endpoint 已就绪；Deployment probe 会检查工作负载的就绪状态。请准备 Argo Project/RBAC 和 image-registry 访问权限。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: wave-demo
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: wave-demo-config
  namespace: wave-demo
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
data:
  DEMO_ENVIRONMENT: demo
---
apiVersion: v1
kind: Service
metadata:
  name: wave-demo
  namespace: wave-demo
  annotations:
    argocd.argoproj.io/sync-wave: "0"
spec:
  type: ClusterIP
  selector:
    app: wave-demo
  ports:
  - name: http
    port: 80
    targetPort: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wave-demo
  namespace: wave-demo
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: wave-demo
  template:
    metadata:
      labels:
        app: wave-demo
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: podinfo
        image: ghcr.io/stefanprodan/podinfo:6.15.0
        ports:
        - name: http
          containerPort: 9898
        envFrom:
        - configMapRef:
            name: wave-demo-config
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: [ALL]
```

对于数据库，请先准备身份验证、持久化、Service 和实际就绪状态。HPA 需要 CPU requests 和 metrics 可用性。不要将就绪所需的 Service/ConfigMap 放在后续波次中。

## 同步窗口

此示例允许生产项目 prod-* 的应用程序在 KST 周日 02:00–06:00 同步，其中 03:00–04:00 为冻结期。请将 repository/destination 替换为实际授权范围。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/myapp.git
  destinations:
  - server: https://kubernetes.default.svc
    namespace: production
  syncWindows:
  - kind: allow
    description: Example Sunday maintenance window
    schedule: '0 2 * * 0'
    duration: 4h
    timeZone: Asia/Seoul
    applications: ['prod-*']
    namespaces: [production]
    andOperator: true
    manualSync: false
    syncOverrun: false
  - kind: deny
    description: Example freeze within the maintenance window
    schedule: '0 3 * * 0'
    duration: 1h
    timeZone: Asia/Seoul
    applications: ['prod-*']
    namespaces: [production]
    andOperator: true
    manualSync: false
    syncOverrun: false
```

对于新的自动同步请求：

1. 没有匹配窗口意味着没有窗口限制。
2. 活跃的匹配 deny 会将其阻止。
3. 否则，活跃的 allow 会允许它。
4. 所有处于非活跃状态的匹配 allow 窗口会将其阻止。
5. 没有 allow 窗口且仅有非活跃 deny 时，允许同步。

Application/namespace/cluster 选择器默认使用 OR；不存在特异性排名。当提供的选择器必须全部匹配时，请使用 andOperator: true。默认时区为 UTC；KST 注释不会改变它。

手动例外取决于所有相关阻止窗口是否允许 manualSync，以及调用者是否具有同步权限。--force 不是绕过方式。始终活跃的 24h allow 并非手动激活的紧急开关，并且也可能允许自动同步。跨越窗口边界的持续执行取决于 syncOverrun、开始时间和相关窗口；它不保证完成或回滚。

```bash
argocd proj windows list production -o yaml
argocd app get my-app
```



![新自动同步的决策流程，区分匹配窗口、活跃的 deny/allow 和非活跃的 allow。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-4.html)

## 差异比较自定义

仅忽略由其他 controller 拥有的实际字段，并按名称/namespace 限定范围。例如，排除一个由 HPA 管理的 Deployment 的 replicas。不要默认进行宽泛的 image、所有 annotation/resources 或所有 manager 排除。

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
    syncOptions: [RespectIgnoreDifferences=true]
```

ignoreDifferences 控制比较；RespectIgnoreDifferences 会将其扩展至同步，但在没有实时对象的初始创建时，仍会使用期望的 manifest。在选择 manager 之前，请检查实际受管字段。全局/status 比较排除项不会禁用健康评估，并且不应隐藏 image 篡改。

有关限定范围的规则，请参阅 [Application ignore-difference 示例](02-applications.md#ignore-differences)。

## 重试策略

limit: 5 允许在初始尝试后重试五次，最多共进行六次尝试。延迟从 5s、10s、20s、40s、80s 开始；maxDuration 限制的是单次 backoff，而不是整个同步或 hook。Application 重试与 Job backoffLimit/activeDeadlineSeconds 是不同层级。

为同步失败配置自动重试。

### 基本重试配置

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: main
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    retry:
      limit: 5          # Maximum retry attempts
      backoff:
        duration: 5s    # Initial delay
        factor: 2       # Multiplier for each retry
        maxDuration: 3m # Maximum delay
```

### 重试流程

limit: 5 允许在初始尝试后最多重试五次。使用 duration 5s 和 factor 2 时，延迟从 5s、10s、20s、40s、80s 开始。maxDuration 限制单次 backoff 延迟；它不是整个同步/hook 的超时。

### 有界依赖预检

预检 hook 可以在有限的截止时间内失败；它不会添加按错误代码筛选的 Argo 重试。下方依赖项必须已存在。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: check-prerequisites
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 100
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      containers:
      - name: check
        image: curlimages/curl:8.22.0
        command:
        - sh
        - -c
        - |
          for i in 1 2 3 4 5 6; do
            if curl --fail --silent --show-error --connect-timeout 3 --max-time 10 http://existing-service:8080/readyz; then
              exit 0
            fi
            sleep 5
          done
          exit 1
```

## 选择性同步

显式的 --resource/--label 选择会跳过 hook 和历史记录。ApplyOutOfSyncOnly/--apply-out-of-sync-only 在 3.5.4 中会保留 hook/历史记录。--label 选择资源；--selector(-l) 选择 Application。

仅同步应用程序中的特定资源。

### 通过 CLI

```bash
# Sync specific resource by kind and name
argocd app sync my-app --resource 'apps:Deployment:my-deployment'

# Sync resources by group
argocd app sync my-app --resource 'apps:Deployment:*'

# Sync multiple resources
argocd app sync my-app \
  --resource ':ConfigMap:my-config' \
  --resource ':Secret:my-secret' \
  --resource 'apps:Deployment:my-deployment'

# Sync by label
argocd app sync my-app --label 'app.kubernetes.io/component=backend'
```

### 选择性同步的同步选项

```bash
# Apply only out-of-sync resources
argocd app sync my-app --apply-out-of-sync-only

# Preview what would be synced
argocd app sync my-app --dry-run

# Sync with prune
argocd app sync my-app --prune
```

### 资源路径格式

```
<group>:<kind>:<name>

Examples:
:ConfigMap:my-config                 # Core API group
apps:Deployment:my-deployment        # apps API group
networking.k8s.io:Ingress:my-ingress # networking.k8s.io group
*:*:*                                # All resources
```

## 测验

为了测试所学内容，请尝试 [ArgoCD 同步策略测验](../../quizzes/gitops/argocd/03-sync-strategies-quiz.md)。

## 已版本化的审查来源

- [3.5.4 同步选项](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [同步窗口](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync_windows.md)
- [窗口匹配和 CanSync](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/types.go)
- [阶段和波次](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [CLI resource/app 选择器](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/commands/argocd_app_sync.md)
