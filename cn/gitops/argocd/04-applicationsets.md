# ArgoCD ApplicationSets

> **支持的版本**: ArgoCD v2.9+, ApplicationSet Controller v0.4+
> **最后更新**: February 22, 2026

## 目录
- [ApplicationSet 概览](#applicationset-overview)
- [生成器](#generators)
- [Go 模板](#go-templating)
- [渐进式同步](#progressive-sync)
- [多集群模式](#multi-cluster-patterns)
- [模板补丁](#template-patches)

## ApplicationSet 概览

ApplicationSet 是一个 Kubernetes controller，用于支持从模板生成 ArgoCD Application。它能够管理跨集群、环境或仓库中具有相似配置的多个应用程序。

### 何时使用 ApplicationSet

| 场景 | 使用 ApplicationSet？ |
|----------|---------------------|
| 同一应用跨多个集群 | 是 |
| 多个环境（dev/staging/prod） | 是 |
| 包含多个服务的 Monorepo | 是 |
| 来自 PR 的动态环境 | 是 |
| 单个应用程序部署 | 否（使用 Application） |

### 基本结构

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-appset
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: dev
            url: https://dev.k8s.local
          - cluster: prod
            url: https://prod.k8s.local
  template:
    metadata:
      name: '{{cluster}}-myapp'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myrepo.git
        targetRevision: HEAD
        path: 'overlays/{{cluster}}'
      destination:
        server: '{{url}}'
        namespace: myapp
```

## 生成器

生成器会生成参数，这些参数将被替换到模板中以创建 Application。

### 1. List Generator

最简单的生成器——定义一个静态值列表：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: list-example
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: dev
            url: https://kubernetes.default.svc
            namespace: dev
            values:
              replicas: "1"
              logLevel: debug
          - cluster: staging
            url: https://staging.k8s.local
            namespace: staging
            values:
              replicas: "2"
              logLevel: info
          - cluster: production
            url: https://production.k8s.local
            namespace: production
            values:
              replicas: "5"
              logLevel: warn
  template:
    metadata:
      name: 'myapp-{{cluster}}'
      labels:
        environment: '{{cluster}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: HEAD
        path: manifests
        helm:
          parameters:
            - name: replicaCount
              value: '{{values.replicas}}'
            - name: logging.level
              value: '{{values.logLevel}}'
      destination:
        server: '{{url}}'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 2. Cluster Generator

自动将已注册的 ArgoCD 集群作为目标：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-example
  namespace: argocd
spec:
  generators:
    - clusters:
        # Select all clusters
        selector: {}

        # Or select by labels
        # selector:
        #   matchLabels:
        #     environment: production
        #     region: us-west-2

        # Available built-in variables:
        # {{name}} - cluster name
        # {{server}} - cluster API server URL
        # {{metadata.labels.<key>}} - cluster labels
        # {{metadata.annotations.<key>}} - cluster annotations

        # Add custom values per cluster
        values:
          clusterName: '{{name}}'
  template:
    metadata:
      name: '{{name}}-guestbook'
    spec:
      project: default
      source:
        repoURL: https://github.com/argoproj/argocd-example-apps.git
        targetRevision: HEAD
        path: guestbook
      destination:
        server: '{{server}}'
        namespace: guestbook
```

#### 用于定位的 Cluster 标签

首先，向集群 Secret 添加标签：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: production-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    environment: production
    region: us-west-2
    tier: critical
type: Opaque
stringData:
  name: production
  server: https://production.k8s.local
  config: |
    {
      "tlsClientConfig": {
        "insecure": false,
        "caData": "..."
      }
    }
```

然后按标签选择集群：

```yaml
generators:
  - clusters:
      selector:
        matchLabels:
          environment: production
        matchExpressions:
          - key: tier
            operator: In
            values:
              - critical
              - high
```

### 3. Git Generator - Directories

扫描 Git 仓库中的目录：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: git-directories
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/gitops-repo.git
        revision: HEAD
        directories:
          # Include all directories under apps/
          - path: apps/*
          # Exclude specific directories
          - path: apps/excluded-app
            exclude: true
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/gitops-repo.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
```

#### Directory Generator 的仓库结构

```
gitops-repo/
├── apps/
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── database/
│   │   ├── statefulset.yaml
│   │   └── service.yaml
│   └── excluded-app/    # Excluded via generator
│       └── ...
```

### 4. Git Generator - Files

从 Git 中的 JSON/YAML 文件读取配置：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: git-files
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/gitops-repo.git
        revision: HEAD
        files:
          - path: "config/**/config.json"
  template:
    metadata:
      name: '{{cluster.name}}-{{app.name}}'
      labels:
        environment: '{{cluster.environment}}'
    spec:
      project: default
      source:
        repoURL: '{{app.repoURL}}'
        targetRevision: '{{app.revision}}'
        path: '{{app.path}}'
        helm:
          valueFiles:
            - values.yaml
            - 'values-{{cluster.environment}}.yaml'
      destination:
        server: '{{cluster.server}}'
        namespace: '{{app.namespace}}'
```

#### 配置文件示例

```json
// config/production/us-west-2/config.json
{
  "cluster": {
    "name": "prod-us-west-2",
    "server": "https://prod-usw2.k8s.local",
    "environment": "production"
  },
  "app": {
    "name": "myapp",
    "repoURL": "https://github.com/myorg/myapp.git",
    "revision": "v1.2.3",
    "path": "charts/myapp",
    "namespace": "myapp-prod"
  }
}
```

### 5. Matrix Generator

组合两个生成器以创建笛卡尔积：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: matrix-example
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          # First generator: clusters
          - clusters:
              selector:
                matchLabels:
                  environment: production
          # Second generator: applications
          - git:
              repoURL: https://github.com/myorg/apps.git
              revision: HEAD
              directories:
                - path: apps/*
  template:
    metadata:
      # Combines cluster name with app name
      name: '{{name}}-{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/apps.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'
```

#### Matrix 可视化

```mermaid
flowchart TB
    subgraph GEN1["Generator 1: Clusters"]
        C1["prod-us-west"]
        C2["prod-us-east"]
        C3["prod-eu-west"]
    end

    subgraph GEN2["Generator 2: Apps"]
        A1["frontend"]
        A2["backend"]
        A3["api"]
    end

    subgraph RESULT["Generated Applications (3x3=9)"]
        R1["prod-us-west-frontend"]
        R2["prod-us-west-backend"]
        R3["prod-us-west-api"]
        R4["prod-us-east-frontend"]
        R5["prod-us-east-backend"]
        R6["prod-us-east-api"]
        R7["prod-eu-west-frontend"]
        R8["prod-eu-west-backend"]
        R9["prod-eu-west-api"]
    end

    GEN1 --> RESULT
    GEN2 --> RESULT
```

### 6. Merge Generator

合并多个生成器的输出，并组合参数：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: merge-example
  namespace: argocd
spec:
  generators:
    - merge:
        mergeKeys:
          - cluster
        generators:
          # Base configuration for all clusters
          - list:
              elements:
                - cluster: dev
                  replicas: "1"
                - cluster: staging
                  replicas: "2"
                - cluster: production
                  replicas: "5"

          # Override specific cluster settings
          - list:
              elements:
                - cluster: production
                  replicas: "10"  # Override for production
                  enableHA: "true"
  template:
    metadata:
      name: 'myapp-{{cluster}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: HEAD
        path: manifests
        helm:
          parameters:
            - name: replicas
              value: '{{replicas}}'
            - name: highAvailability
              value: '{{enableHA}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{cluster}}'
```

### 7. SCM Provider Generator

扫描 GitHub/GitLab 组织中的仓库：

#### GitHub

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: github-org-apps
  namespace: argocd
spec:
  generators:
    - scmProvider:
        github:
          organization: myorg
          # Optional: filter by topics
          # allBranches: false
          # tokenRef:
          #   secretName: github-token
          #   key: token
        filters:
          - repositoryMatch: "^service-.*"
          - pathsExist:
              - kubernetes/
          - labelMatch: "deploy-to-k8s"
  template:
    metadata:
      name: '{{repository}}'
    spec:
      project: default
      source:
        repoURL: '{{url}}'
        targetRevision: '{{branch}}'
        path: kubernetes
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{repository}}'
```

#### GitLab

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: gitlab-group-apps
  namespace: argocd
spec:
  generators:
    - scmProvider:
        gitlab:
          group: mygroup
          includeSubgroups: true
          # tokenRef:
          #   secretName: gitlab-token
          #   key: token
        filters:
          - pathsExist:
              - deploy/
  template:
    metadata:
      name: '{{repository}}'
    spec:
      project: default
      source:
        repoURL: '{{url}}'
        targetRevision: '{{branch}}'
        path: deploy
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{repository}}'
```

### 8. Pull Request Generator

为 Pull Request 创建环境：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: pr-environments
  namespace: argocd
spec:
  generators:
    - pullRequest:
        github:
          owner: myorg
          repo: myapp
          tokenRef:
            secretName: github-token
            key: token
          labels:
            - preview
        requeueAfterSeconds: 180
  template:
    metadata:
      name: 'pr-{{number}}-{{branch_slug}}'
      labels:
        preview: "true"
        pr-number: '{{number}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: '{{head_sha}}'
        path: kubernetes
        kustomize:
          nameSuffix: '-pr-{{number}}'
          images:
            - 'myapp:pr-{{number}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: 'preview-{{number}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

### 9. Cluster Decision Resource Generator

将集群选择委托给外部资源：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-decision
  namespace: argocd
spec:
  generators:
    - clusterDecisionResource:
        configMapRef: cluster-decision-cm
        name: selected-clusters
        requeueAfterSeconds: 180
  template:
    metadata:
      name: '{{clusterName}}-app'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: HEAD
        path: manifests
      destination:
        server: '{{clusterServer}}'
        namespace: myapp
```

外部决策资源：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-decision-cm
  namespace: argocd
data:
  ducktypeVersion: v1
  statusListKey: clusters
---
apiVersion: external.decision/v1
kind: ClusterDecision
metadata:
  name: selected-clusters
  namespace: argocd
status:
  clusters:
    - clusterName: prod-us-west
      clusterServer: https://prod-usw.k8s.local
    - clusterName: prod-eu-west
      clusterServer: https://prod-euw.k8s.local
```

### 10. Plugin Generator

通过 ConfigMap 执行自定义生成器逻辑：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: plugin-example
  namespace: argocd
spec:
  generators:
    - plugin:
        configMapRef:
          name: plugin-generator
        input:
          parameters:
            environment: production
            region: us-west-2
        requeueAfterSeconds: 300
  template:
    metadata:
      name: '{{name}}'
    spec:
      project: default
      source:
        repoURL: '{{repoURL}}'
        targetRevision: '{{revision}}'
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{namespace}}'
```

## Go 模板

ApplicationSet 使用 Go 模板进行参数替换。

### 基本语法

```yaml
template:
  metadata:
    name: '{{cluster}}-{{app}}'           # Simple substitution
    labels:
      env: '{{values.environment}}'       # Nested values
```

### 函数

```yaml
template:
  metadata:
    # Normalize strings
    name: '{{normalize .cluster}}'

    # String manipulation
    labels:
      lower: '{{.cluster | lower}}'
      upper: '{{.cluster | upper}}'
      trimmed: '{{.cluster | trim}}'

    annotations:
      # Conditional
      tier: '{{if eq .env "prod"}}critical{{else}}standard{{end}}'
```

### 高级模板

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: advanced-template
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
    - missingkey=error
  generators:
    - list:
        elements:
          - name: app1
            env: prod
            regions:
              - us-west-2
              - us-east-1
  template:
    metadata:
      name: '{{.name}}-{{.env}}'
      annotations:
        regions: '{{range $i, $r := .regions}}{{if $i}},{{end}}{{$r}}{{end}}'
```

## 渐进式同步

使用 RollingSync 控制跨应用程序的 rollout。

### RollingSync 策略

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: progressive-rollout
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            environment: production
  strategy:
    type: RollingSync
    rollingSync:
      steps:
        # Step 1: Deploy to canary cluster
        - matchExpressions:
            - key: tier
              operator: In
              values:
                - canary
          maxUpdate: 1

        # Step 2: Wait for manual approval
        - matchExpressions:
            - key: tier
              operator: In
              values:
                - production
          maxUpdate: 0  # Pause here

        # Step 3: Deploy to 25% of prod clusters
        - matchExpressions:
            - key: tier
              operator: In
              values:
                - production
          maxUpdate: 25%

        # Step 4: Deploy to remaining prod clusters
        - matchExpressions:
            - key: tier
              operator: In
              values:
                - production
  template:
    metadata:
      name: '{{name}}-myapp'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: HEAD
        path: manifests
      destination:
        server: '{{server}}'
        namespace: myapp
```

### 渐进式同步流程

```mermaid
flowchart TB
    subgraph STEP1["Step 1: Canary"]
        CANARY["canary-cluster"]
    end

    subgraph STEP2["Step 2: Manual Gate"]
        PAUSE["⏸️ Paused"]
    end

    subgraph STEP3["Step 3: 25% Rollout"]
        P1["prod-1"]
        P2["prod-2"]
    end

    subgraph STEP4["Step 4: Full Rollout"]
        P3["prod-3"]
        P4["prod-4"]
        P5["prod-5"]
        P6["prod-6"]
    end

    STEP1 -->|"Success"| STEP2
    STEP2 -->|"Approved"| STEP3
    STEP3 -->|"Success"| STEP4

    classDef canary fill:#ffc107,stroke:#333,color:black
    classDef pause fill:#6c757d,stroke:#333,color:white
    classDef prod fill:#28a745,stroke:#333,color:white

    class CANARY canary
    class PAUSE pause
    class P1,P2,P3,P4,P5,P6 prod
```

## 多集群模式

### Hub-and-Spoke 模式

中央 ArgoCD 管理多个集群：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: hub-spoke-platform
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  managed-by: hub
          - list:
              elements:
                - app: monitoring
                  chart: kube-prometheus-stack
                  repo: https://prometheus-community.github.io/helm-charts
                  version: "55.5.0"
                - app: logging
                  chart: loki-stack
                  repo: https://grafana.github.io/helm-charts
                  version: "2.10.0"
                - app: ingress
                  chart: ingress-nginx
                  repo: https://kubernetes.github.io/ingress-nginx
                  version: "4.9.0"
  template:
    metadata:
      name: '{{name}}-{{app}}'
    spec:
      project: platform
      source:
        repoURL: '{{repo}}'
        chart: '{{chart}}'
        targetRevision: '{{version}}'
      destination:
        server: '{{server}}'
        namespace: '{{app}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

### 环境晋级模式

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: environment-promotion
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/env-config.git
        revision: HEAD
        files:
          - path: "environments/*/config.yaml"
  template:
    metadata:
      name: 'myapp-{{environment}}'
      annotations:
        argocd.argoproj.io/sync-wave: '{{syncWave}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/myapp.git
        targetRevision: '{{gitRevision}}'
        path: kubernetes
        kustomize:
          images:
            - 'myapp:{{imageTag}}'
      destination:
        server: '{{clusterUrl}}'
        namespace: '{{namespace}}'
```

配置文件：

```yaml
# environments/dev/config.yaml
environment: dev
namespace: myapp-dev
clusterUrl: https://dev.k8s.local
gitRevision: HEAD
imageTag: latest
syncWave: "0"

# environments/staging/config.yaml
environment: staging
namespace: myapp-staging
clusterUrl: https://staging.k8s.local
gitRevision: release-candidate
imageTag: rc-1.2.3
syncWave: "1"

# environments/production/config.yaml
environment: production
namespace: myapp-prod
clusterUrl: https://production.k8s.local
gitRevision: v1.2.3
imageTag: v1.2.3
syncWave: "2"
```

## 模板补丁

根据生成器输出覆盖模板字段。

### 基本补丁

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: patched-apps
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - name: app1
            env: dev
          - name: app2
            env: prod
  template:
    metadata:
      name: '{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/apps.git
        targetRevision: HEAD
        path: '{{name}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{name}}'
  templatePatch: |
    {{- if eq .env "prod" }}
    spec:
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
    {{- end }}
```

### Strategic Merge Patch

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: strategic-patch
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: dev
            autoSync: "false"
          - cluster: prod
            autoSync: "true"
  template:
    metadata:
      name: 'app-{{cluster}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/apps.git
        targetRevision: HEAD
        path: app
      destination:
        server: https://kubernetes.default.svc
        namespace: app-{{cluster}}
  templatePatch: |
    spec:
      {{- if eq .autoSync "true" }}
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
      {{- else }}
      syncPolicy: {}
      {{- end }}
```

## 测验

为检验所学内容，请尝试 [ArgoCD ApplicationSets 测验](../../quizzes/gitops/argocd/04-applicationsets-quiz.md)。
