# ArgoCD Projects 和 RBAC

> **支持的版本**: ArgoCD v2.9+
> **最后更新**: February 22, 2026

## 目录
- [AppProject 概览](#appproject-overview)
- [默认项目](#default-project)
- [自定义项目](#custom-projects)
- [RBAC 配置](#rbac-configuration)
- [多租户模式](#multi-tenancy-patterns)
- [用于 CI/CD 的 JWT Token](#jwt-tokens-for-cicd)
- [孤立资源监控](#orphaned-resource-monitoring)

## AppProject 概览

AppProject 为 Applications 提供逻辑分组，并定义访问控制：可部署哪些资源、可部署到何处以及谁可以管理它们。

### 关键功能

| 功能 | 说明 |
|---------|-------------|
| 源限制 | 限制可使用的 Git 仓库 |
| 目标限制 | 限制目标集群和 Namespace |
| 资源允许列表/拒绝列表 | 控制可创建哪些 K8s 资源 |
| 角色定义 | 定义项目专属的 RBAC 角色 |
| 同步窗口 | 定义应用程序可以同步的时间 |

### AppProject CRD 结构

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  description: "Project description"

  # Source repositories
  sourceRepos:
    - https://github.com/myorg/*
    - https://charts.helm.sh/stable

  # Allowed destinations
  destinations:
    - namespace: my-app-*
      server: https://kubernetes.default.svc
    - namespace: '*'
      server: https://production.k8s.local

  # Cluster resource allowlist
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: rbac.authorization.k8s.io
      kind: ClusterRole
    - group: rbac.authorization.k8s.io
      kind: ClusterRoleBinding

  # Cluster resource denylist
  clusterResourceBlacklist:
    - group: ''
      kind: ResourceQuota

  # Namespace resource allowlist (default: allow all)
  namespaceResourceWhitelist:
    - group: '*'
      kind: '*'

  # Namespace resource denylist
  namespaceResourceBlacklist:
    - group: ''
      kind: LimitRange

  # Project roles
  roles:
    - name: developer
      description: Developer access
      policies:
        - p, proj:my-project:developer, applications, get, my-project/*, allow
        - p, proj:my-project:developer, applications, sync, my-project/*, allow
      groups:
        - my-org:developers

  # Sync windows
  syncWindows:
    - kind: allow
      schedule: '0 9 * * 1-5'
      duration: 8h
      applications:
        - '*'

  # Orphaned resource monitoring
  orphanedResources:
    warn: true
    ignore:
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
```

## 默认项目

ArgoCD 随附一个 `default` 项目，该项目允许所有源、目标和资源。

### 默认项目规范

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

### 何时使用默认项目

- 开发环境
- 快速测试
- 没有多租户要求的小型团队

### 限制默认项目

对于生产环境，请限制默认项目：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  description: Restricted default project
  sourceRepos: []  # No repos allowed
  destinations: []  # No destinations allowed
```

## 自定义项目

### 基于团队的项目

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

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace

  namespaceResourceBlacklist:
    # Prevent privileged workloads
    - group: ''
      kind: Pod
    # Use Deployments instead

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
        - p, proj:team-frontend:developer, applications, action/*, team-frontend/*, allow
      groups:
        - myorg:frontend-devs

    - name: viewer
      description: Read-only access
      policies:
        - p, proj:team-frontend:viewer, applications, get, team-frontend/*, allow
      groups:
        - myorg:frontend-viewers
```

### 基于环境的项目

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
    - namespace: '*'
      server: https://production.k8s.local
    - namespace: '*'
      server: https://production-dr.k8s.local

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: networking.k8s.io
      kind: IngressClass
    - group: storage.k8s.io
      kind: StorageClass

  # Restrict certain namespaced resources in production
  namespaceResourceBlacklist:
    - group: ''
      kind: Pod  # Force use of controllers
    - group: batch
      kind: Job  # Jobs should go through CI/CD

  syncWindows:
    # Only allow sync during business hours
    - kind: allow
      schedule: '0 9 * * 1-5'
      duration: 8h
      applications:
        - '*'
      manualSync: true

    # Emergency window (manual only)
    - kind: allow
      schedule: '0 0 * * *'
      duration: 24h
      applications:
        - '*'
      manualSync: true

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

### 平台基础设施项目

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
    - https://grafana.github.io/helm-charts
    - https://charts.jetstack.io
    - https://kubernetes.github.io/ingress-nginx

  destinations:
    - namespace: kube-system
      server: '*'
    - namespace: monitoring
      server: '*'
    - namespace: logging
      server: '*'
    - namespace: ingress-nginx
      server: '*'
    - namespace: cert-manager
      server: '*'

  # Platform needs cluster-wide resources
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'

  roles:
    - name: platform-admin
      description: Platform team admin
      policies:
        - p, proj:platform:platform-admin, applications, *, platform/*, allow
        - p, proj:platform:platform-admin, clusters, *, *, allow
        - p, proj:platform:platform-admin, repositories, *, *, allow
      groups:
        - myorg:platform-team
```

## RBAC 配置

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

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  # Default policy for authenticated users
  policy.default: role:readonly

  # Scope RBAC policies to specific AppProjects
  scopes: '[groups]'

  policy.csv: |
    # Built-in admin role (full access)
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    p, role:admin, projects, *, *, allow
    p, role:admin, accounts, *, *, allow
    p, role:admin, gpgkeys, *, *, allow
    p, role:admin, certificates, *, *, allow
    p, role:admin, logs, *, *, allow
    p, role:admin, exec, *, */*, allow

    # Built-in readonly role
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, clusters, get, *, allow
    p, role:readonly, repositories, get, *, allow
    p, role:readonly, projects, get, *, allow
    p, role:readonly, logs, get, */*, allow

    # Custom organization roles
    # Org admins
    p, role:org-admin, applications, *, */*, allow
    p, role:org-admin, clusters, get, *, allow
    p, role:org-admin, repositories, *, *, allow
    p, role:org-admin, projects, *, *, allow

    # Developers (can sync and view, but not delete)
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, */*, allow
    p, role:developer, applications, action/*, */*, allow
    p, role:developer, logs, get, */*, allow
    p, role:developer, exec, create, */*, allow

    # Viewers
    p, role:viewer, applications, get, */*, allow
    p, role:viewer, logs, get, */*, allow

    # Group to role mappings
    g, myorg:admins, role:admin
    g, myorg:org-admins, role:org-admin
    g, myorg:developers, role:developer
    g, myorg:viewers, role:viewer

    # User to role mappings
    g, admin@example.com, role:admin
    g, ci-bot, role:developer

    # Project-scoped roles (defined in AppProject)
    # These are auto-generated: proj:<project>:<role>
```

### 资源专属权限

```yaml
policy.csv: |
  # Applications - fine-grained permissions
  p, role:deployer, applications, get, */*, allow
  p, role:deployer, applications, sync, */*, allow
  p, role:deployer, applications, update, */*, deny
  p, role:deployer, applications, delete, */*, deny

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
  p, role:debugger, exec, create, */*, allow
  p, role:debugger, applications, get, */*, allow
```

### 应用程序专属操作

```yaml
policy.csv: |
  # Sync-only role (for CI/CD)
  p, role:sync-only, applications, get, */*, allow
  p, role:sync-only, applications, sync, */*, allow

  # Override action (allows syncing with force)
  p, role:operator, applications, action/apps/Deployment/restart, */*, allow

  # Rollback permission
  p, role:operator, applications, update, */*, allow
```

## 多租户模式

### 每个团队一个 Namespace

```mermaid
flowchart TB
    subgraph ARGOCD["ArgoCD"]
        PROJ_A["Project: team-a"]
        PROJ_B["Project: team-b"]
        PROJ_P["Project: platform"]
    end

    subgraph CLUSTER["Kubernetes Cluster"]
        NS_A["Namespace: team-a"]
        NS_B["Namespace: team-b"]
        NS_P["Namespaces: kube-system, monitoring"]
    end

    PROJ_A -->|"can deploy to"| NS_A
    PROJ_B -->|"can deploy to"| NS_B
    PROJ_P -->|"can deploy to"| NS_P

    classDef project fill:#EB6E85,stroke:#333,color:white
    classDef namespace fill:#326CE5,stroke:#333,color:white

    class PROJ_A,PROJ_B,PROJ_P project
    class NS_A,NS_B,NS_P namespace
```

实现：

```yaml
# Team A Project
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
  clusterResourceWhitelist: []  # No cluster resources
  roles:
    - name: admin
      policies:
        - p, proj:team-a:admin, applications, *, team-a/*, allow
      groups:
        - team-a-admins
---
# Team B Project
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

### 每个环境一个集群

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: development
  namespace: argocd
spec:
  sourceRepos:
    - '*'
  destinations:
    - namespace: '*'
      server: https://dev.k8s.local
  # Relaxed for development
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'
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
    - namespace: '*'
      server: https://prod.k8s.local
  # Strict for production
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
  syncWindows:
    - kind: deny
      schedule: '0 0 * * 0,6'  # No weekend deploys
      duration: 48h
      applications:
        - '*'
```

## 用于 CI/CD 的 JWT Token

为自动化创建项目范围的 Token。

### 创建 JWT Token

```bash
# Create token for project role
argocd proj role create-token my-project deployer

# Create token with expiration
argocd proj role create-token my-project deployer --expires-in 24h

# Create token with ID (for revocation)
argocd proj role create-token my-project deployer --token-id ci-pipeline-1
```

### 在 CI/CD 中使用 Token

```yaml
# GitHub Actions example
name: Deploy to ArgoCD
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install ArgoCD CLI
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          sudo mv argocd /usr/local/bin/

      - name: Login to ArgoCD
        run: |
          argocd login ${{ secrets.ARGOCD_SERVER }} \
            --auth-token ${{ secrets.ARGOCD_TOKEN }} \
            --grpc-web

      - name: Sync Application
        run: |
          argocd app sync my-app --prune
          argocd app wait my-app --health
```

### Token 管理

```bash
# List tokens
argocd proj role list-tokens my-project deployer

# Delete token
argocd proj role delete-token my-project deployer <token-id>
```

### 通过 Secret 使用 Token

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-ci-token
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: argocd-token
stringData:
  token: <jwt-token>
```

## 孤立资源监控

检测目标 Namespace 中未由 ArgoCD 管理的资源。

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
      # Ignore specific resources
      - group: ''
        kind: ConfigMap
        name: kube-root-ca.crt
      - group: ''
        kind: ServiceAccount
        name: default
      # Ignore by pattern
      - group: ''
        kind: Secret
        name: 'default-token-*'
```

### 查看孤立资源

```bash
# Via CLI
argocd app resources my-app --orphaned

# Via API
curl -s https://argocd.example.com/api/v1/applications/my-app/resource-tree | jq '.orphanedNodes'
```

### 自动清理

目前，ArgoCD 仅会对孤立资源发出警告。如需自动清理，请使用 post-sync hook：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cleanup-orphans
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      serviceAccountName: orphan-cleaner
      restartPolicy: Never
      containers:
        - name: cleaner
          image: bitnami/kubectl:latest
          command:
            - /bin/sh
            - -c
            - |
              # Custom cleanup logic
              kubectl get configmaps -n my-namespace -l managed-by!=argocd -o name | xargs -r kubectl delete -n my-namespace
```

## 测验

为检验所学内容，请尝试 [ArgoCD Projects 和 RBAC 测验](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md)。
