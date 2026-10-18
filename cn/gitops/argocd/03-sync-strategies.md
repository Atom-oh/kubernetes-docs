# ArgoCD 同步策略

> **审查基线**：Argo CD 3.5.2；在审阅发行说明后更新至补丁版本 3.5.4（未重新运行示例）
> **最后更新**：October 16, 2026

## 目录
- [手动同步与自动同步](#manual-vs-automated-sync)
- [自动同步策略](#auto-sync-policies)
- [同步选项](#sync-options)
- [同步波次与阶段](#sync-waves-and-phases)
- [同步窗口](#sync-windows)
- [差异比较自定义](#diffing-customization)
- [重试策略](#retry-policies)
- [选择性同步](#selective-sync)

## 手动同步与自动同步 {#manual-vs-automated-sync}

以下示例是相互独立的策略片段。请保留实际 Application 的 source、destination 和 project，并且只选择需要的选项。Sync 会应用更改；Refresh 会根据来源/缓存更新比较结果。Synced 与健康状态及实际服务可用性相互独立。

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

在自动模式下，检测到更改时 ArgoCD 会自动同步：

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

![Argo CD 持续比较 Git 仓库中的期望状态与 Kubernetes 集群中的实际状态；检测到 OutOfSync 差异时，会应用更改，使实际状态再次与 Git 一致。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-0.html)

## 自动同步策略 {#auto-sync-policies}

automated: {} 或省略/null 的 enabled 标志会启用自动同步；enabled: false 会禁用自动同步。只有设置 selfHeal 才会纠正仅存在于实际状态中的偏差，prune 则是独立选项。默认情况下，相同提交/参数组合的失败不会无限重试；请配置重试策略。对于由 ApplicationSet 管理的 Application，应修改其所属模板。

### Prune

自动删除 Git 中已不存在的资源：

```yaml
syncPolicy:
  automated:
    prune: true
```

**适用场景**：确保集群状态与 Git 仓库完全一致。删除孤立资源。

Prune 仅作用于 Application 跟踪的资源，而不是集群中的所有孤立资源。PruneLast 会改变顺序；它不能保护数据，也不能取代对删除操作的审查。

### Self-Heal

自动还原对集群所做的手动更改：

```yaml
syncPolicy:
  automated:
    selfHeal: true
```

**适用场景**：防止通过手动 kubectl 更改或其他工具造成配置偏差。

![时序图展示用户如何手动使用 kubectl 扩缩 Deployment、Argo CD 如何检测状态变化、从 Git 读取期望副本数，并重新应用该值，使 Kubernetes 自愈回到 Git 声明的状态。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-1.html)

### Allow Empty

允许没有任何资源的应用：

```yaml
syncPolicy:
  automated:
    allowEmpty: true
```

启用自动 prune 后，当渲染结果为空时，allowEmpty 可能允许删除所有受管理资源。它不是通用的引导部署要求。

### 完整的自动同步配置

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

## 同步选项 {#sync-options}

同步选项可以精细控制同步行为。

### 可用的同步选项

| 选项 | 说明 | 默认值 |
|--------|-------------|---------|
| `Validate` | 根据架构验证资源 | true |
| `CreateNamespace` | 如果命名空间不存在则创建 | false |
| `PrunePropagationPolicy` | 删除传播策略 | foreground |
| `PruneLast` | 在所有其他同步操作之后执行 prune | false |
| `Replace` | 使用 replace 而不是 apply | false |
| `FailOnSharedResource` | 如果另一个 Argo CD Application 跟踪该资源则失败 | false |
| `ApplyOutOfSyncOnly` | 仅应用不同步的资源 | false |
| `ServerSideApply` | 使用服务器端 apply | false |
| `RespectIgnoreDifferences` | 在同步时遵循 ignoreDifferences | false |

`Validate=false` 会跳过 apply 时的架构验证；它不会安装缺失的 CRD。如果 CR 的 CRD 在同一次同步中安装，Argo CD 会自动跳过该 CR 的 dry run。只有在有充分理由时（例如 CRD 由另一个控制器创建）才使用 `SkipDryRunOnMissingResource=true`，并确认 CRD 已可用。

`PruneLast=true` 会将 prune 安排在最后一个隐式波次中，并在其他资源部署且达到 Healthy 状态后执行。`FailOnSharedResource=true` 会检查是否有另一个 Argo CD Application 跟踪该资源；它不会检测与其他 Kubernetes 控制器或 Flux 之间的所有权冲突。

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

通过注解将同步选项应用于特定资源：

```yaml
# Merge into an existing complete resource manifest.
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

### 服务器端 Apply

Argo CD 3.5.4 会调用 --server-side --force-conflicts。系统会跟踪字段所有权，但这不保证冲突会被拒绝；请审查可能发生的所有权接管。

使用 Kubernetes 服务器端 apply，以更好地检测冲突：

```yaml
syncPolicy:
  syncOptions:
    - ServerSideApply=true
```

或者按资源设置：

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

**优点**：
- 更好地跟踪字段所有权
- Argo CD 可以强制解决所有权冲突；请检查预期的管理器边界
- 适用于 CRD 和 webhook

### Replace 和 Force

Replace 会选择 kubectl replace/create。它不会自动使不可变字段变为可编辑。Force=true 与 Replace=true 配合使用时可能会删除并重新创建对象，这是一个独立且具有破坏性的选择：

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: Replace=true
```

更改不可变字段需要针对具体资源制定迁移/重新创建计划。不要将此用作 PVC 存储类迁移的捷径。删除前请审查保留策略、数据和可用性。Replace 的优先级高于 ServerSideApply。

## 同步波次与阶段 {#sync-waves-and-phases}

同步波次控制资源的应用顺序。

### 波次的工作方式

资源按波次编号分组，并依次同步：
1. 按阶段、波次、kind 和名称排序。
2. 负数 Sync 波次不会在 PreSync 阶段之前运行。
3. 波次推进取决于同步/健康状态；不要依赖同一波次内的实际并发来满足依赖关系。如果需要通过就绪状态阻止后续操作，Custom Resource 必须配置有意义的健康检查。

![Argo CD 按升序应用同步波次的工作流图：波次 -2 为 CRD，波次 -1 为 Namespace 和 ServiceAccount，默认波次 0 为 ConfigMap、Secret 和 Deployment，随后波次 1 为 Service 和 Ingress；每个波次都会等待前一波次达到健康状态。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-2.html)

### 设置同步波次

将此片段合并到完整资源清单的 metadata 中。后面会给出一个完整示例。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
```

### 将波次与 Hook 结合使用

PreSync 会在每个普通 Sync 波次之前运行。下面的现有服务、命名空间、DB Secret 和迁移镜像都必须事先准备好；PreSync 不能假定可以访问在后续 Sync 波次中创建的数据库。

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
        image: curlimages/curl:8.23.0
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

仅将 pg_dump 输出到 stdout 的 Job 并不是可恢复的备份流程。请使用持久化加密存储，并验证备份完成且进行恢复测试。请验证迁移的幂等性、锁定和恢复能力；PostSync 失败不会自动回滚。

### 最简可用的排序示例

此最简示例会在同一 Sync 阶段内按 Namespace → ConfigMap → Service → 带就绪检查的 Deployment 排序。Healthy 状态的 Service 对象并不能证明端点已就绪；Deployment 探针会检查工作负载是否就绪。请提前准备 Argo Project/RBAC 和镜像仓库访问权限。

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

对于数据库，应先准备身份验证、持久化、Service 和实际就绪检查。HPA 需要 CPU requests 和可用的指标。不要将就绪检查所需的 Service/ConfigMap 放在后续波次中。

## 同步窗口 {#sync-windows}

此示例允许 production 项目中名称匹配 prod-* 的应用在韩国标准时间星期日 02:00–06:00 进行同步，并在 03:00–04:00 冻结同步。请将仓库/目标位置替换为实际授权的范围。

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

1. 没有匹配的窗口表示不受窗口限制。
2. 如果匹配的 deny 窗口当前处于活动状态，则会阻止同步。
3. 否则，如果匹配的 allow 窗口当前处于活动状态，则允许同步。
4. 如果所有匹配的 allow 窗口都未处于活动状态，则会阻止同步。
5. 没有 allow 窗口且只有未处于活动状态的 deny 窗口时，则允许同步。

Application/namespace/cluster 选择器默认按 OR 关系处理；没有特定性排序。需要所有给定选择器都匹配时，请使用 andOperator: true。默认时区是 UTC；注释中的 KST 不会改变时区。

手动例外取决于所有相关阻止窗口是否都允许 manualSync，以及调用方是否拥有同步权限。--force 不能绕过限制。始终处于活动状态的 24 小时 allow 窗口并不是手动激活的紧急开关，也可能允许自动同步。跨越窗口边界继续执行取决于 syncOverrun、开始时间和相关窗口；它不能保证完成或回滚。

```bash
argocd proj windows list production -o yaml
argocd app get my-app
```



![新建自动同步的决策流程图，展示匹配窗口、活动的 deny/allow 窗口以及未活动的 allow 窗口。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-4.html)

## 差异比较自定义 {#diffing-customization}

仅忽略由其他控制器实际管理的字段，并按名称/命名空间限定范围。例如，排除由 HPA 管理的某个 Deployment 的 replicas。不要默认广泛排除镜像、所有注解/资源或所有管理器。

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

ignoreDifferences 控制比较；RespectIgnoreDifferences 会将其扩展到同步过程，但在没有实际对象的情况下进行首次创建时，仍会使用期望清单。选择管理器前，请检查实际管理字段。全局/状态比较排除项不会禁用健康状态评估，也不应掩盖镜像篡改。

有关限定范围的规则，请参见 [Application ignore-difference 示例](02-applications.md#ignore-differences)。

## 重试策略 {#retry-policies}

limit: 5 表示初始尝试之后最多重试五次，总计最多六次。延迟从 5s、10s、20s、40s、80s 递增；maxDuration 限制的是单次退避时长，而不是整个同步或 Hook 的时长。Application 重试与 Job 的 backoffLimit/activeDeadlineSeconds 属于不同层级。

配置同步失败时自动重试。

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

limit: 5 表示初始尝试之后最多可重试五次。duration 为 5s、factor 为 2 时，延迟依次从 5s、10s、20s、40s、80s 开始。maxDuration 限制的是单次退避延迟，不是整个同步/Hook 的超时时间。

### 有界依赖项预检

预检 Hook 可以在有限的截止时间内失败；它不会添加按错误代码筛选 Argo 重试的功能。以下依赖项必须事先存在。

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
        image: curlimages/curl:8.23.0
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

## 选择性同步 {#selective-sync}

显式使用 --resource/--label 选择会跳过 Hook 和历史记录。ApplyOutOfSyncOnly/--apply-out-of-sync-only 在 3.5.4 中会保留 Hook 和历史记录。--label 用于选择资源；--selector(-l) 用于选择 Application。

仅同步应用中的特定资源。

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

想要检验所学内容，请尝试 [ArgoCD 同步策略测验](../../quizzes/gitops/argocd/03-sync-strategies-quiz.md)。

## 版本审查资料

- [3.5.4 同步选项](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [同步窗口](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync_windows.md)
- [窗口匹配与 CanSync](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/types.go)
- [阶段与波次](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [CLI 资源/Application 选择器](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/commands/argocd_app_sync.md)
