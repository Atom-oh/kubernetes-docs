# ArgoCD Applications

> **対応バージョン**: ArgoCD v2.9+
> **最終更新**: February 22, 2026

## 目次
- [Application CRD の概要](#application-crd-overview)
- [ソースタイプ](#source-types)
- [複数のソース](#multiple-sources)
- [宛先設定](#destination-configuration)
- [ヘルス評価](#health-assessment)
- [リソースフック](#resource-hooks)
- [差分の無視](#ignore-differences)
- [App of Apps パターン](#app-of-apps-pattern)

## Application CRD の概要

Application CRD は、アプリケーションをデプロイする方法と場所を定義する ArgoCD の中核リソースです。ソースリポジトリをターゲット Kubernetes クラスタに接続します。

### 完全な仕様

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

### 主要フィールドの説明

| フィールド | 説明 |
|-------|-------------|
| `project` | このアプリケーションが属する AppProject |
| `source` | マニフェストの取得元 |
| `destination` | ターゲットクラスタと namespace |
| `syncPolicy` | 自動同期と再試行の動作 |
| `ignoreDifferences` | 比較時に無視するフィールド |
| `info` | 表示用のカスタムメタデータ |
| `revisionHistoryLimit` | 保持するデプロイメントリビジョン数 |

## ソースタイプ

ArgoCD は Kubernetes マニフェストを取得するために複数のソースタイプをサポートしています。

### プレーン YAML/JSON ディレクトリ

最もシンプルなソースタイプは、Kubernetes マニフェストを含むディレクトリです。

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

### Helm チャート

#### Git リポジトリから

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

#### Helm リポジトリから

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

#### 外部ファイルの Values を使用

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

### OCI アーティファクト (v2.8+)

OCI 準拠レジストリからデプロイします。

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

## 複数のソース

ArgoCD v2.6+ では、1 つのアプリケーションで複数のソースをサポートしており、複雑なデプロイメントシナリオを実現できます。

### Helm チャートと Git の Values を組み合わせる

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

### 1 つに複数のアプリケーション

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

## 宛先設定

### Server URL を使用

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### クラスタ名を使用

```yaml
destination:
  name: production-cluster  # Must match registered cluster name
  namespace: my-app
```

### Namespace の自動作成

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## ヘルス評価

ArgoCD は組み込みおよびカスタムチェックを使用してアプリケーションのヘルスを評価します。

### 組み込みヘルスチェック

ArgoCD には標準 Kubernetes リソース用のヘルスチェックが含まれています。

| リソース | Healthy となる条件 |
|----------|--------------|
| Deployment | すべてのレプリカが利用可能 |
| StatefulSet | すべてのレプリカが ready |
| DaemonSet | 希望数とスケジュール数が一致 |
| ReplicaSet | すべてのレプリカが利用可能 |
| Service | Endpoints が存在 |
| Ingress | ロードバランサーが割り当て済み |
| PersistentVolumeClaim | Bound |
| Pod | Running かつ ready |
| Job | 成功済み |

### カスタムヘルスチェック (Lua)

`argocd-cm` でカスタムヘルスチェックを定義します。

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

### AWS リソース (ACK) のヘルスチェック

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

## リソースフック

リソースフックを使用すると、同期中の特定の時点で Job を実行できます。

### フックタイプ

| フック | 実行タイミング |
|------|---------------|
| `PreSync` | 同期開始前 |
| `Sync` | 同期中 (`PreSync` の後) |
| `PostSync` | 同期成功後 |
| `SyncFail` | 同期失敗後 |
| `Skip` | 同期中にスキップ |

### フック削除ポリシー

| ポリシー | 動作 |
|--------|----------|
| `HookSucceeded` | フックの成功後に削除 |
| `HookFailed` | フックの失敗後に削除 |
| `BeforeHookCreation` | 新しいフックの実行前に削除 |

### データベース移行フック

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

### Slack 通知フック

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

### ヘルスチェックフック

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

## 差分の無視

比較時に特定の差分を無視するよう ArgoCD を設定します。

### JSON Pointer による指定

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
      - /spec/replicas
      - /spec/template/spec/containers/0/image
```

### JQ パス式による指定

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jqPathExpressions:
      - .spec.template.spec.containers[].resources
      - .metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
```

### 名前による指定

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
      - /spec/replicas
```

### 管理対象フィールド (Kubernetes Server-Side Apply)

```yaml
ignoreDifferences:
  - group: "*"
    kind: "*"
    managedFieldsManagers:
      - kube-controller-manager
      - cluster-autoscaler
```

### argocd-cm でのグローバルな無視

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

## App of Apps パターン

App of Apps パターンを使用すると、単一の親アプリケーションから複数のアプリケーションを管理できます。

### ディレクトリ構造

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

### 親アプリケーション

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

### 子アプリケーションテンプレート

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

### Values ファイル

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

### App of Apps の Sync Waves

子アプリケーションのデプロイ順序を制御します。

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

## リビジョン履歴とロールバック

### 履歴を表示

```bash
# CLI
argocd app history my-app

# Output
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ghi9012
```

### ロールバック

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### 宣言的なロールバック

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

## クイズ

学習内容を確認するには、[ArgoCD applications クイズ](../../quizzes/gitops/argocd/02-applications-quiz.md)に挑戦してください。
