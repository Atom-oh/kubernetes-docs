# ArgoCD Projects 和 RBAC

> **审阅依据**：Argo CD 3.5.2；经发布说明审阅后更新至补丁版本 3.5.5（未重新运行示例）
> **最后更新**：October 16, 2026

## 目录
- [AppProject 概述](#appproject-overview)
- [默认 Project](#default-project)
- [自定义 Project](#custom-projects)
- [RBAC 配置](#rbac-configuration)
- [多租户模式](#multi-tenancy-patterns)
- [CI/CD 的 JWT Token](#jwt-tokens-for-cicd)
- [孤立资源监控](#orphaned-resource-monitoring)

## AppProject 概述 {#appproject-overview}

AppProject 为 Applications 提供逻辑分组，并定义访问控制，规定可以部署哪些资源、部署到哪里，以及谁可以管理它们。

AppProject 会限制来源、目标、渲染后的资源类型以及 Argo CD API 权限。它不能取代 Kubernetes RBAC、Pod Security Admission、NetworkPolicy 或 ResourceQuota。禁止 Pod 类型并不能阻止 Deployment 创建特权 Pod。

请提供真实的仓库 URL、组、已注册集群和命名空间。平台管理员应预先创建应用程序命名空间，并负责其安全和配额策略。下面的团队/环境 Project 不允许集群范围的资源；单独的平台 Project 供受信任的管理员使用。完整的 Project 示例彼此独立，可作为替代方案使用，其中也包括名称相同的示例。

### 主要功能

| 功能 | 说明 |
|---------|-------------|
| 来源限制 | 限制可使用的 Git 仓库 |
| 目标限制 | 限制目标集群和命名空间 |
| 资源允许列表/拒绝列表 | 控制可以创建哪些 K8s 资源 |
| 角色定义 | 定义特定于 Project 的 RBAC 角色 |
| 同步窗口 | 定义 Applications 可以同步的时间 |

### AppProject 配置示例

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  description: Project description
  sourceRepos:
  - https://github.com/myorg/*
  - https://stefanprodan.github.io/podinfo
  destinations:
  - namespace: my-app-*
    server: https://kubernetes.default.svc
  - namespace: my-project-*
    server: https://production.k8s.local
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
  - group: '*'
    kind: '*'
  namespaceResourceBlacklist:
  - group: ''
    kind: LimitRange
  - group: ''
    kind: ResourceQuota
  roles:
  - name: developer
    description: Developer access
    policies:
    - p, proj:my-project:developer, applications, get, my-project/*, allow
    - p, proj:my-project:developer, applications, sync, my-project/*, allow
    groups:
    - my-org:developers
  syncWindows:
  - kind: allow
    schedule: 0 9 * * 1-5
    duration: 8h
    applications:
    - '*'
    timeZone: Asia/Seoul
  orphanedResources:
    warn: true
    ignore:
    - group: ''
      kind: ConfigMap
      name: kube-root-ca.crt
```

## 默认 Project {#default-project}

ArgoCD 会创建一个允许所有来源、目标和资源类型的默认 Project。可以对其进行限制，但不能删除。

### 默认 Project 规范

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  description: Default project
  sourceRepos:
  - '*'
  destinations:
  - namespace: '*'
    server: '*'
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
```

### 何时使用默认 Project

- 开发环境
- 快速测试
- 不需要多租户的团队

### 限制默认 Project

在生产环境中，应限制默认 Project：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  description: Restricted default project
  sourceRepos: []
  destinations: []
  sourceNamespaces: []
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
  - group: '*'
    kind: '*'
```

## 自定义 Project {#custom-projects}

### 基于团队的 Project

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-frontend
  namespace: argocd
spec:
  description: Frontend team project
  sourceRepos:
  - https://github.com/myorg/frontend-*
  - https://github.com/myorg/shared-libs
  destinations:
  - namespace: frontend-*
    server: https://kubernetes.default.svc
  - namespace: frontend-*
    server: https://staging.k8s.local
  - namespace: frontend-*
    server: https://production.k8s.local
  clusterResourceWhitelist: []
  roles:
  - name: admin
    description: Project admin
    policies:
    - p, proj:team-frontend:admin, applications, *, team-frontend/*, allow
    - p, proj:team-frontend:admin, repositories, *, team-frontend/*, allow
    groups:
    - myorg:frontend-leads
  - name: developer
    description: Developer access
    policies:
    - p, proj:team-frontend:developer, applications, get, team-frontend/*, allow
    - p, proj:team-frontend:developer, applications, sync, team-frontend/*, allow
    - p, proj:team-frontend:developer, applications, action/apps/Deployment/restart, team-frontend/*, allow
    groups:
    - myorg:frontend-devs
  - name: viewer
    description: Read-only access
    policies:
    - p, proj:team-frontend:viewer, applications, get, team-frontend/*, allow
    groups:
    - myorg:frontend-viewers
```

### 基于环境的 Project

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production environment project
  sourceRepos:
  - https://github.com/myorg/gitops-prod
  destinations:
  - namespace: prod-*
    server: https://production.k8s.local
  - namespace: prod-*
    server: https://production-dr.k8s.local
  clusterResourceWhitelist: []
  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange
  syncWindows:
  - kind: allow
    schedule: 0 9 * * 1-5
    duration: 8h
    applications:
    - '*'
    manualSync: true
    timeZone: Asia/Seoul
  roles:
  - name: sre
    description: SRE team with full access
    policies:
    - p, proj:production:sre, applications, *, production/*, allow
    groups:
    - myorg:sre-team
  - name: deployer
    description: CI/CD deployment access
    policies:
    - p, proj:production:deployer, applications, sync, production/*, allow
    - p, proj:production:deployer, applications, get, production/*, allow
```

### 平台基础设施 Project

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: platform
  namespace: argocd
spec:
  description: Platform infrastructure components
  sourceRepos:
  - https://github.com/myorg/platform-*
  - https://prometheus-community.github.io/helm-charts
  - https://grafana-community.github.io/helm-charts
  - https://charts.jetstack.io
  - docker.io/envoyproxy
  destinations:
  - namespace: kube-system
    server: https://dev-cluster.example.com
  - namespace: kube-system
    server: https://staging-cluster.example.com
  - namespace: kube-system
    server: https://prod-cluster.example.com
  - namespace: monitoring
    server: https://dev-cluster.example.com
  - namespace: monitoring
    server: https://staging-cluster.example.com
  - namespace: monitoring
    server: https://prod-cluster.example.com
  - namespace: logging
    server: https://dev-cluster.example.com
  - namespace: logging
    server: https://staging-cluster.example.com
  - namespace: logging
    server: https://prod-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://dev-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://staging-cluster.example.com
  - namespace: envoy-gateway-system
    server: https://prod-cluster.example.com
  - namespace: cert-manager
    server: https://dev-cluster.example.com
  - namespace: cert-manager
    server: https://staging-cluster.example.com
  - namespace: cert-manager
    server: https://prod-cluster.example.com
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
  roles:
  - name: platform-admin
    description: Platform team admin
    policies:
    - p, proj:platform:platform-admin, applications, *, platform/*, allow
    - p, proj:platform:platform-admin, clusters, *, platform/*, allow
    - p, proj:platform:platform-admin, repositories, *, platform/*, allow
    groups:
    - myorg:platform-team
```

### 范围解读与验证

- AppProject 的 destination 匹配 `(server OR registered name) AND namespace`；同时指定两个集群标识并不会增加 AND 约束。这些示例仅使用 server。Application 的 destination 则要求在 server 或 name 中选择其一。
- ResourceQuota 和 LimitRange 属于命名空间范围；clusterResourceBlacklist 无法阻止它们。对于 Argo CD 部署路径，应使用 namespaceResourceBlacklist。
- 如果省略 namespaceResourceWhitelist，默认允许命名空间范围的类型；显式的允许/拒绝列表会一起评估。集群范围的类型需要通过允许列表放行。Argo CD 3.5.4 还支持在集群资源列表中使用名称模式。
- 如果委派 Namespace 管理权限，也要限制其名称（group:'', kind:Namespace, name:team-a-*）。这仍允许更改 Namespace 标签；预先创建命名空间并使用准入控制，对租户边界而言更安全。
- manualSync 允许在允许窗口之外手动例外同步；它不会禁用自动同步，也不会将例外限制为值班角色。请在同步章节中审查重叠的拒绝窗口和显式时区。
- 限制 default 之前，应将现有 Applications 移至显式指定的 Project，并验证访问权限。

## RBAC 配置 {#rbac-configuration}

ArgoCD RBAC 在 `argocd-rbac-cm` ConfigMap 中配置。

### RBAC 策略语法

```
p, <subject>, <resource>, <action>, <object>, <effect>
g, <subject>, <role>
```

| 字段 | 说明 |
|-------|-------------|
| `subject` | 用户、组或角色 |
| `resource` | applications、clusters、repositories 等 |
| `action` | get、create、update、delete、sync 等 |
| `object` | 资源标识符（project/app 或 *） |
| `effect` | allow 或 deny |

### 内置角色

| 角色 | 说明 |
|------|-------------|
| `role:readonly` | 对所有资源的只读访问权限 |
| `role:admin` | 对所有资源的完全访问权限 |

### 完整 RBAC 配置

此示例不授予隐式的 Application 访问权限，而是分配显式的组权限。开发人员的权限限定在 team-frontend 范围内。role:authenticated 不要添加策略条目。默认策略授予的权限无法通过用户级 deny 移除；将默认角色设为 role:readonly 会暴露跨 Project 的读取权限。不要在 policy.csv 中复制/重新定义内置角色规则。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  policy.default: role:authenticated
  policy.matchMode: glob
  scopes: '[groups]'
  policy.csv: |
    # Built-in role:admin and role:readonly are already provided by Argo CD.
    p, role:developer, applications, get, team-frontend/*, allow
    p, role:developer, applications, sync, team-frontend/*, allow
    p, role:developer, applications, action/apps/Deployment/restart, team-frontend/*, allow
    p, role:developer, logs, get, team-frontend/*, allow
    p, role:viewer, applications, get, team-frontend/*, allow
    p, role:frontend-admin, applications, *, team-frontend/*, allow
    p, role:frontend-admin, logs, get, team-frontend/*, allow
    p, role:backend-admin, applications, *, team-b/*, allow
    p, role:backend-admin, logs, get, team-b/*, allow
    p, role:sre, applications, get, production/*, allow
    p, role:sre, applications, sync, production/*, allow
    p, role:sre, applications, action/apps/Deployment/restart, production/*, allow
    p, role:sre, logs, get, production/*, allow
    p, role:sre, exec, create, production/*, allow
    p, role:security-auditor, applications, get, */*, allow
    p, role:security-auditor, projects, get, *, allow
    p, role:security-auditor, repositories, get, *, allow
    g, platform-team, role:admin
    g, developers, role:developer
    g, frontend-team, role:frontend-admin
    g, backend-team, role:backend-admin
    g, viewers, role:viewer
    g, sre-team, role:sre
    g, security-team, role:security-auditor
    p, role:developer, projects, get, team-frontend, allow
    p, role:viewer, projects, get, team-frontend, allow
    p, role:frontend-admin, projects, get, team-frontend, allow
    p, role:backend-admin, projects, get, team-b, allow
    p, role:sre, projects, get, production, allow
```

使用 Kustomize/Helm 将其他策略片段合并到现有 ConfigMap 数据中。Argo CD 会将 policy.example-N.csv 键追加到 policy.csv。不要将每个片段作为整个 ConfigMap 的替代内容来应用，也不要累积互不相关、范围过宽的 allow 示例。

Argo CD API RBAC 与 Kubernetes RBAC 相互独立。object project/app 无法标识目标命名空间；位于控制平面命名空间之外的 Applications 也使用 project/application-namespace/app。Glob 匹配不会把斜杠视为分隔符，因此应包含完整的资源操作路径。

在 3.x 默认行为下，Application 的 update/delete 权限不会自动授予对其子 Kubernetes 资源执行相同操作的权限。对于这些操作，请使用 `update/<group>/<kind>/<namespace>/<name>` 或 `delete/...`，并考虑 `server.rbac.disableApplicationFineGrainedRBACInheritance`。

sync 可以创建、更新和修剪已部署的资源。禁止删除 Application 并不能阻止通过 sync/prune 删除资源。rollback API 也会检查 sync；没有独立的 action/rollback 或仅限 rollback 的权限。override 允许替换来源（例如使用本地清单），而不只是强制同步。当提供修订版本时，application.sync.requireOverridePrivilegeForRevisionSync 可以要求具备 override 权限。

### 特定资源的权限

```yaml
policy.example-1.csv: |
  # Applications - fine-grained permissions
  p, role:deployer, applications, get, production/*, allow
  p, role:deployer, applications, sync, production/*, allow
  p, role:deployer, applications, update, production/*, deny
  p, role:deployer, applications, delete, production/*, deny

  # Cluster management
  p, role:cluster-admin, clusters, *, *, allow
  p, role:cluster-viewer, clusters, get, *, allow

  # Repository management
  p, role:repo-admin, repositories, *, *, allow
  p, role:repo-viewer, repositories, get, *, allow

  # Project-specific permissions
  p, role:team-a-admin, applications, *, team-a/*, allow
  p, role:team-a-admin, projects, get, team-a, allow

  # Exec into running pods (debugging)
  p, role:debugger, exec, create, production/*, allow
  p, role:debugger, applications, get, production/*, allow
```

### Application 特定操作

```yaml
policy.example-2.csv: |
  # Sync-only role (for CI/CD)
  p, role:sync-only, applications, get, production/*, allow
  p, role:sync-only, applications, sync, production/*, allow

  # Explicit Deployment restart resource action
  p, role:operator, applications, action/apps/Deployment/restart, production/*, allow

  # Rollback API requires sync; update is for changing the Application
  p, role:operator, applications, sync, production/*, allow
  p, role:operator, applications, get, production/*, allow
```

## 多租户模式 {#multi-tenancy-patterns}

### 每个团队使用一个命名空间

![团队 A、团队 B 和平台团队在 ArgoCD AppProject 中获得应用角色；该 AppProject 的 destination 将 Argo CD 部署限制在各自的命名空间 team-a、team-b 以及共享的 monitoring 和 logging 命名空间中。](../../.gitbook/assets/en-gitops-argocd-06-projects-rbac-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-06-projects-rbac-0.html)

实现方式：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/team-a-*
  destinations:
  - namespace: team-a
    server: https://kubernetes.default.svc
  - namespace: team-a-*
    server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  roles:
  - name: admin
    policies:
    - p, proj:team-a:admin, applications, *, team-a/*, allow
    groups:
    - team-a-admins
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-b
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/team-b-*
  destinations:
  - namespace: team-b
    server: https://kubernetes.default.svc
  - namespace: team-b-*
    server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  roles:
  - name: admin
    policies:
    - p, proj:team-b:admin, applications, *, team-b/*, allow
    groups:
    - team-b-admins
```

### 每个环境使用一个集群

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: development
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/dev-*
  destinations:
  - namespace: dev-*
    server: https://dev.k8s.local
  clusterResourceWhitelist: []
---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/gitops-prod
  destinations:
  - namespace: prod-*
    server: https://prod.k8s.local
  clusterResourceWhitelist: []
  syncWindows:
  - kind: deny
    schedule: 0 0 * * 6
    duration: 48h
    applications:
    - '*'
    timeZone: Asia/Seoul
  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange
```

<span id="jwt-tokens-for-cicd"></span>

## CI/CD 的 JWT Token

为自动化创建 Project 范围的 Token。

### 创建 JWT Token

有权更新 Project 的操作员负责签发/撤销 Token；CI 角色本身仅拥有 get/sync 权限。请先准备好 my-project、其 ci-deployer 角色以及 my-app Application。应在 Token 过期前轮换；CLI 默认不设置过期时间。

```bash
set -euo pipefail
umask 077
# Run as an operator authorized to update my-project.
argocd proj role create-token my-project ci-deployer \
  --expires-in 24h --token-only > ./argocd-ci.token
# Store this file's value in the approved CI secret store; do not commit or print it.
```

需要显式标识符时请使用 `--id UNIQUE_ID`；--token-id 不是 3.5.4 的标志。expires-in 接受诸如 24h 的时长。签名后的 Token 值会在签发时返回，不会被存储以供日后检索。

### 在 CI/CD 中使用 Token

将此角色合并到现有的 my-project AppProject 中；它本身不会创建来源/目标权限或 Application：

```yaml
spec:
  roles:
  - name: ci-deployer
    policies:
    - p, proj:my-project:ci-deployer, applications, get, my-project/*, allow
    - p, proj:my-project:ci-deployer, applications, sync, my-project/*, allow
```

此工作流会同步 Application 声明的修订版本，而不是强制使用工作流 SHA。需要不可变修订版本时，请在 Git 中固定 targetRevision。使用 --revision 之前，请检查服务器的 override 设置。请另行配置 production Environment 的审批/保护规则。

```yaml
name: Sync declared Argo CD application
'on':
  push:
    branches:
    - main
  workflow_dispatch: {}
permissions: {}
concurrency:
  group: argocd-my-project-my-app
  cancel-in-progress: false
jobs:
  sync:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    environment: production
    steps:
    - name: Install verified CLI
      shell: bash
      run: |
        set -euo pipefail
        ARGOCD_VERSION=v3.5.5
        case "$(uname -m)" in
          x86_64) cli_arch=amd64 ;;
          aarch64|arm64) cli_arch=arm64 ;;
          *) echo "Unsupported runner architecture" >&2; exit 1 ;;
        esac
        cli_asset="argocd-linux-${cli_arch}"
        cli_dir="$(mktemp -d)"
        trap 'rm -rf "$cli_dir"' EXIT
        cli_base="https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}"
        curl --fail --location --retry 3 "$cli_base/$cli_asset" -o "$cli_dir/$cli_asset"
        curl --fail --location --retry 3 "$cli_base/cli_checksums.txt" -o "$cli_dir/checksums.txt"
        awk -v artifact="$cli_asset" '$2 == artifact { print }' "$cli_dir/checksums.txt" > "$cli_dir/selected.sha256"
        test -s "$cli_dir/selected.sha256"
        (cd "$cli_dir" && sha256sum --check selected.sha256)
        install -m 0755 "$cli_dir/$cli_asset" "$RUNNER_TEMP/argocd"
    - name: Sync and wait
      shell: bash
      env:
        ARGOCD_SERVER: ${{ secrets.ARGOCD_SERVER }}
        ARGOCD_AUTH_TOKEN: ${{ secrets.ARGOCD_TOKEN }}
      run: |
        set -euo pipefail
        "$RUNNER_TEMP/argocd" app sync my-app --server "$ARGOCD_SERVER" --grpc-web --timeout 300
        "$RUNNER_TEMP/argocd" app wait my-app --server "$ARGOCD_SERVER" --grpc-web --sync --health --timeout 300
```

### Token 管理

Token 元数据会存储/规范化在 Project 的角色/状态记录中。手动声明 iat/exp/id 并不会签发签名 Token。角色策略的更改会影响已签发的 Token。使用操作员凭据，通过 Token 的 ISSUED AT 整数值而非其 ID 标签来撤销单个 Token：

```bash
argocd proj role list-tokens my-project ci-deployer --unixtime

# Select one token's ISSUED AT value from the list, using operator credentials.
: "${SELECTED_ISSUED_AT:?Set the selected integer ISSUED AT value}"
argocd proj role delete-token my-project ci-deployer "$SELECTED_ISSUED_AT"
```

### 在集群内 CI 中存储 Token

Kubernetes Secret 可以为 CI 作业存储先前签发的 Token。它不是 Argo CD Token 签发器，也没有特殊的 argocd-token Secret 类型。请使用 CI 作业所在的命名空间，并通过安全文件输入传入 Token，例如：

```bash
kubectl create secret generic argocd-ci-token -n ci \
  --from-file=token=./argocd-ci.token
```

请先创建 ci 命名空间并配置作业 RBAC。仅在获授权的 CI 作业中挂载/读取 Secret，并在 Token 过期前轮换其值。不要将 Token 值放入 Git。

## 孤立资源监控 {#orphaned-resource-monitoring}

检测目标命名空间中未由 ArgoCD 管理的资源。

### 启用孤立资源监控

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
spec:
  orphanedResources:
    warn: true
    ignore:
    - group: ''
      kind: ConfigMap
      name: kube-root-ca.crt
    - group: ''
      kind: ServiceAccount
      name: default
    - group: ''
      kind: Secret
      name: default-token-*
  clusterResourceWhitelist: []
```

### 查看孤立资源

```bash
argocd app resources my-app --orphaned

: "${ARGOCD_AUTH_TOKEN:?Provide an authorized token securely}"
curl --fail --silent --show-error --max-time 30 \
  -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" \
  https://argocd.example.com/api/v1/applications/my-app/resource-tree \
  | jq '.orphanedNodes'
```

警告是可选的：即使 warn:false，仍可查看疑似孤立资源。被 Project 拒绝的资源和内置默认对象有例外；请缩小监控的命名空间范围，避免扫描大量 kube-system 资源。

### 清理前审查

孤立资源监控会报告未由 Argo CD Application 跟踪的顶层命名空间资源。它们仍可能属于其他操作器，或者是有意在 GitOps 之外管理的资源。标签选择器 `managed-by!=argocd` 也会匹配不带此类标签的资源，并不实现 Argo CD 跟踪机制。不要将该选择器转变为 PostSync 删除作业。

在判断资源是否已过时之前，请检查孤立资源列表、所有者引用、实际的 Argo CD 跟踪元数据以及所属控制器。使用范围严格限定的孤立资源监控忽略规则排除合法资源。任何删除操作都应使用经过明确审查的资源列表，并遵循相应的备份/恢复流程；此处的示例仅报告疑似资源。

## 策略验证

将基本 ConfigMap 示例保存为 argocd-rbac-cm.yaml。CLI 也会初始化有效的 kubeconfig，但策略文件检查不会修改实时设置。请分别检查动态 AppProject 角色、实际的 SSO 声明和 Kubernetes 准入控制。

```bash
argocd admin settings rbac validate --policy-file ./argocd-rbac-cm.yaml
argocd admin settings rbac can developers sync applications team-frontend/my-app \
  --policy-file ./argocd-rbac-cm.yaml
# Expected: No (exit 1)
argocd admin settings rbac can developers get applications team-b/my-app \
  --policy-file ./argocd-rbac-cm.yaml
```

validate 可能会警告用户 CSV 中缺少内置 role:admin。can 默认包含内置策略；不要为了消除警告而重复定义内置角色。请检查本地用户/SSO 组冲突和实际的组声明。exec 策略本身不会启用终端：还要检查 exec.enabled 和底层 Kubernetes 权限。

## 参考资料

- [Argo CD 3.5.4 RBAC](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/rbac.md)
- [Project 匹配与验证](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/app_project_types.go)
- [来源完整性](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/source-integrity-git-gpg.md)
- [Project Token CLI](https://github.com/argoproj/argo-cd/blob/v3.5.4/cmd/argocd/commands/project_role.go)

## 测验

检验你学到的内容，请尝试 [ArgoCD Projects 和 RBAC 测验](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md)。
