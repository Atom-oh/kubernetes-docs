# ArgoCD ApplicationSets

> **対応バージョン**: ArgoCD v2.9+, ApplicationSet Controller v0.4+
> **最終更新**: February 22, 2026

## 目次
- [ApplicationSet の概要](#applicationset-overview)
- [Generator](#generators)
- [Go テンプレート](#go-templating)
- [段階的同期](#progressive-sync)
- [マルチクラスターのパターン](#multi-cluster-patterns)
- [テンプレートパッチ](#template-patches)

## ApplicationSet の概要

ApplicationSet は、テンプレートから ArgoCD Application を生成する機能を追加する Kubernetes controller です。クラスター、環境、またはリポジトリ全体で類似した設定を持つ複数のアプリケーションを管理できます。

### ApplicationSet を使用する場合

| シナリオ | ApplicationSet を使用するか？ |
|----------|---------------------|
| 複数のクラスターにまたがる同じアプリ | はい |
| 複数の環境（dev/staging/prod） | はい |
| 多数のサービスを含むモノレポ | はい |
| PR からの動的な環境 | はい |
| 単一アプリケーションのデプロイ | いいえ（Application を使用） |

### 基本構造

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

## Generator

Generator は、Application を作成するためにテンプレートへ置換されるパラメータを生成します。

### 1. List Generator

最もシンプルな Generator で、静的な値のリストを定義します。

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

登録済みの ArgoCD クラスターを自動的に対象にします。

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

#### ターゲティングのためのクラスターラベル

まず、クラスター Secret にラベルを追加します。

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

次に、ラベルでクラスターを選択します。

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

### 3. Git Generator - ディレクトリ

Git リポジトリ内のディレクトリをスキャンします。

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

#### Directory Generator のリポジトリ構造

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

### 4. Git Generator - ファイル

Git 内の JSON/YAML ファイルから設定を読み取ります。

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

#### 設定ファイルの例

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

2 つの Generator を組み合わせて、デカルト積を作成します。

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

#### Matrix の可視化

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

複数の Generator からの出力をマージし、パラメータを結合します。

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

GitHub/GitLab 組織のリポジトリをスキャンします。

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

Pull Request 用の環境を作成します。

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

クラスターの選択を外部リソースに委譲します。

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

外部決定リソース:

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

ConfigMap を介してカスタム Generator ロジックを実行します。

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

## Go テンプレート

ApplicationSet は、パラメータ置換に Go テンプレートを使用します。

### 基本構文

```yaml
template:
  metadata:
    name: '{{cluster}}-{{app}}'           # Simple substitution
    labels:
      env: '{{values.environment}}'       # Nested values
```

### 関数

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

### 高度なテンプレート

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

## 段階的同期

RollingSync を使用して、アプリケーション間のロールアウトを制御します。

### RollingSync 戦略

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

### 段階的同期フロー

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

## マルチクラスターのパターン

### Hub-and-Spoke パターン

複数のクラスターを管理する中央の ArgoCD:

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

### 環境昇格パターン

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

設定ファイル:

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

## テンプレートパッチ

Generator の出力に基づいてテンプレートフィールドを上書きします。

### 基本パッチ

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

## クイズ

学習内容を確認するには、[ArgoCD ApplicationSets クイズ](../../quizzes/gitops/argocd/04-applicationsets-quiz.md)に挑戦してください。
