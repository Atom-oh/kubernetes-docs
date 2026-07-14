# ArgoCD Sync 戦略

> **サポート対象バージョン**: ArgoCD v2.9+
> **最終更新**: February 22, 2026

## 目次
- [手動 Sync と自動 Sync](#手動-sync-と自動-sync)
- [Auto-Sync ポリシー](#auto-sync-ポリシー)
- [Sync オプション](#sync-オプション)
- [Sync Wave と Phase](#sync-wave-と-phase)
- [Sync Window](#sync-window)
- [差分検出のカスタマイズ](#差分検出のカスタマイズ)
- [Retry ポリシー](#retry-ポリシー)
- [選択的 Sync](#選択的-sync)

## 手動 Sync と自動 Sync

ArgoCD は、手動と自動の 2 つの同期モードをサポートしています。

### 手動 Sync

手動モードでは、ユーザーが明示的に同期をトリガーする必要があります。

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

手動 Sync をトリガーする方法:

```bash
# Via CLI
argocd app sync my-app

# Sync specific resources only
argocd app sync my-app --resource ':Deployment:my-deployment'

# Sync with options
argocd app sync my-app --prune --force
```

### 自動 Sync

自動モードでは、変更が検出されると ArgoCD が自動的に Sync を実行します。

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

```mermaid
flowchart LR
    subgraph DETECT["Change Detection"]
        GIT["Git Repository"]
        WEBHOOK["Webhook"]
        POLL["Polling (3min)"]
    end

    subgraph SYNC["Sync Process"]
        COMPARE["Compare States"]
        APPLY["Apply Changes"]
    end

    subgraph CLUSTER["Target Cluster"]
        RESOURCES["K8s Resources"]
    end

    GIT -->|"push"| WEBHOOK
    GIT -->|"check"| POLL
    WEBHOOK --> COMPARE
    POLL --> COMPARE
    COMPARE -->|"drift detected"| APPLY
    APPLY --> RESOURCES
    RESOURCES -->|"status"| COMPARE

    classDef detect fill:#f9f9f9,stroke:#333,color:black
    classDef sync fill:#EB6E85,stroke:#333,color:white
    classDef cluster fill:#326CE5,stroke:#333,color:white

    class GIT,WEBHOOK,POLL detect
    class COMPARE,APPLY sync
    class RESOURCES cluster
```

## Auto-Sync ポリシー

### Prune

Git に存在しなくなったリソースを自動的に削除します。

```yaml
syncPolicy:
  automated:
    prune: true
```

**ユースケース**: Cluster の状態を Git リポジトリと完全に一致させます。孤立したリソースを削除します。

**警告**: Cluster スコープのリソースには注意してください。より安全に Prune を実行するには `PruneLast` オプションを使用します。

### Self-Heal

Cluster に手動で加えられた変更を自動的に元に戻します。

```yaml
syncPolicy:
  automated:
    selfHeal: true
```

**ユースケース**: 手動の kubectl 変更や他のツールによる設定ドリフトを防止します。

```mermaid
sequenceDiagram
    participant User
    participant K8s as Kubernetes
    participant ArgoCD
    participant Git

    User->>K8s: kubectl scale deployment --replicas=5
    K8s-->>ArgoCD: State changed
    ArgoCD->>Git: Get desired state
    Git-->>ArgoCD: replicas: 3
    ArgoCD->>K8s: Apply replicas: 3
    Note over K8s: Self-healed back to<br/>desired state
```

### Allow Empty

リソースを持たない Application を許可します。

```yaml
syncPolicy:
  automated:
    allowEmpty: true
```

**ユースケース**: リソースが条件付きで生成される Application、または初期セットアップ時に使用します。

### 完全な Auto-Sync 設定

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
      allowEmpty: false  # Fail if no resources
```

## Sync オプション

Sync オプションにより、同期動作をきめ細かく制御できます。

### 使用可能な Sync オプション

| オプション | 説明 | デフォルト |
|--------|-------------|---------|
| `Validate` | スキーマに対してリソースを検証 | true |
| `CreateNamespace` | 存在しない場合に Namespace を作成 | false |
| `PrunePropagationPolicy` | 削除の伝播ポリシー | foreground |
| `PruneLast` | 他のすべての Sync の後に Prune を実行 | false |
| `Replace` | apply ではなく replace を使用 | false |
| `FailOnSharedResource` | リソースが他で管理されている場合は失敗 | false |
| `ApplyOutOfSyncOnly` | OutOfSync のリソースだけに apply を実行 | false |
| `ServerSideApply` | server-side apply を使用 | false |
| `RespectIgnoreDifferences` | Sync 時に ignoreDifferences を尊重 | false |

### Application レベルのオプション

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
      - Validate=true
      - ApplyOutOfSyncOnly=true
```

### リソースレベルのオプション

アノテーションを通じて、特定のリソースに Sync オプションを適用します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  annotations:
    argocd.argoproj.io/sync-options: Replace=true,Validate=false
spec:
  # ...
```

### Server-Side Apply

競合をより適切に検出するには、Kubernetes の server-side apply を使用します。

```yaml
syncPolicy:
  syncOptions:
    - ServerSideApply=true
```

またはリソース単位で設定します。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

**利点**:
- フィールド所有権の追跡が向上
- API server によるマージ競合の検出
- CRD および Webhook と適切に連携

### Force Replace

リソースを強制的に置換します（イミュータブルなフィールドに有用です）。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: Replace=true
```

**ユースケース**:
- Job（イミュータブルな spec）
- PVC のストレージクラスの変更
- イミュータブルな ConfigMap/Secret フィールド

## Sync Wave と Phase

Sync Wave は、リソースを適用する順序を制御します。

### Wave の仕組み

リソースは Wave 番号ごとにグループ化され、順に Sync されます。
1. 最も小さい Wave 番号から開始します（負の値も使用可能）
2. Wave 内では、最初に Hook、次にリソースが実行されます
3. 前の Wave が完了した後にのみ、次の Wave が開始されます

```mermaid
flowchart LR
    subgraph WAVE_N2["Wave -2"]
        CRD["CRDs"]
    end

    subgraph WAVE_N1["Wave -1"]
        NS["Namespaces"]
        SA["ServiceAccounts"]
    end

    subgraph WAVE_0["Wave 0 (default)"]
        CFG["ConfigMaps"]
        SEC["Secrets"]
        DEP["Deployments"]
    end

    subgraph WAVE_1["Wave 1"]
        SVC["Services"]
        ING["Ingress"]
    end

    WAVE_N2 --> WAVE_N1 --> WAVE_0 --> WAVE_1

    classDef wave fill:#f9f9f9,stroke:#333,color:black

    class CRD,NS,SA,CFG,SEC,DEP,SVC,ING wave
```

### Sync Wave の設定

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "0"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

### Wave と Hook の組み合わせ

```yaml
# PreSync hook in wave -5
apiVersion: batch/v1
kind: Job
metadata:
  name: db-init
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/sync-wave: "-5"
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: init
          image: myapp/db-init:latest
          command: ["./init-db.sh"]
      restartPolicy: Never
---
# PreSync hook in wave -3 (runs after db-init)
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/sync-wave: "-3"
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: myapp/migrations:latest
          command: ["./migrate.sh"]
      restartPolicy: Never
```

### 完全な順序付けの例

```yaml
# Order: CRDs -> Namespaces -> RBAC -> ConfigMaps -> Deployments -> Services -> Ingress

# Wave -5: Custom Resource Definitions
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: myresources.example.com
  annotations:
    argocd.argoproj.io/sync-wave: "-5"
spec:
  group: example.com
  names:
    kind: MyResource
    plural: myresources
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
---
# Wave -4: Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-4"
---
# Wave -3: RBAC
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-3"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-3"
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
---
# Wave -2: Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
data:
  config.yaml: |
    server:
      port: 8080
---
# Wave 0: Application (default)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  # No wave annotation = wave 0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app
      containers:
        - name: app
          image: myapp:v1.0.0
          ports:
            - containerPort: 8080
---
# Wave 1: Networking
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
---
# Wave 2: External access
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "2"
spec:
  ingressClassName: nginx
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-app
                port:
                  number: 80
```

## Sync Window

Sync Window は、Application が Sync を実行できる時間を制限します。

### Allow Window

特定の時間帯にのみ Sync を許可します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  syncWindows:
    # Allow sync weekdays 9am-5pm UTC
    - kind: allow
      schedule: '0 9 * * 1-5'
      duration: 8h
      applications:
        - '*'
      namespaces:
        - 'production'
      clusters:
        - 'https://production-cluster'

    # Allow emergency sync window (can be manually activated)
    - kind: allow
      schedule: '0 0 * * *'
      duration: 24h
      applications:
        - '*'
      manualSync: true
```

### Deny Window

特定の時間帯の Sync をブロックします。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  syncWindows:
    # Deny sync during peak hours
    - kind: deny
      schedule: '0 12 * * *'
      duration: 2h
      applications:
        - 'critical-*'

    # Deny sync during weekends
    - kind: deny
      schedule: '0 0 * * 0,6'
      duration: 24h
      applications:
        - '*'
      namespaces:
        - 'production'
```

### Window 設定

```yaml
syncWindows:
  - kind: allow                    # allow or deny
    schedule: '0 22 * * *'         # Cron expression (UTC)
    duration: 1h                   # Duration: Ns, Nm, Nh
    applications:                  # Application name patterns
      - 'prod-*'
      - 'frontend'
    namespaces:                    # Target namespaces
      - 'production'
    clusters:                      # Target clusters
      - 'https://production.k8s'
    manualSync: false              # Allow manual sync override
    timeZone: 'America/New_York'   # Optional timezone (default UTC)
```

### Sync Window のオーバーライド

緊急時には、手動 Sync により deny Window をオーバーライドできます。

```bash
# Force sync even in deny window (requires manualSync: true in allow window)
argocd app sync my-app --force
```

## 差分検出のカスタマイズ

### 差分を無視する

特定のフィールドを無視するよう ArgoCD を設定します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  ignoreDifferences:
    # Ignore all annotations
    - group: ""
      kind: Service
      jsonPointers:
        - /metadata/annotations

    # Ignore specific field by JQ expression
    - group: apps
      kind: Deployment
      jqPathExpressions:
        - .spec.template.spec.containers[].resources

    # Ignore for specific named resource
    - group: apps
      kind: Deployment
      name: my-deployment
      namespace: production
      jsonPointers:
        - /spec/replicas

    # Ignore managed fields from specific controllers
    - group: "*"
      kind: "*"
      managedFieldsManagers:
        - kube-controller-manager
        - cluster-autoscaler
```

### グローバルな差分検出設定

`argocd-cm` 内:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # Ignore aggregated cluster roles
  resource.compareoptions: |
    ignoreAggregatedRoles: true

  # Global ignore patterns
  resource.customizations.ignoreDifferences.all: |
    managedFieldsManagers:
      - kube-controller-manager
    jsonPointers:
      - /metadata/annotations/kubectl.kubernetes.io~1last-applied-configuration

  # Ignore for specific resource type
  resource.customizations.ignoreDifferences.admissionregistration.k8s.io_MutatingWebhookConfiguration: |
    jqPathExpressions:
      - .webhooks[]?.clientConfig.caBundle
```

### リソースステータスの無視

すべての status フィールドを無視します。

```yaml
resource.compareoptions: |
  ignoreResourceStatusField: all
```

または特定の kind のみを対象にします。

```yaml
resource.compareoptions: |
  ignoreResourceStatusField: crd
```

## Retry ポリシー

Sync の失敗時に自動 Retry を設定します。

### 基本的な Retry 設定

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  syncPolicy:
    retry:
      limit: 5          # Maximum retry attempts
      backoff:
        duration: 5s    # Initial delay
        factor: 2       # Multiplier for each retry
        maxDuration: 3m # Maximum delay
```

### Retry フロー

```mermaid
sequenceDiagram
    participant App as Application
    participant Ctrl as Controller
    participant K8s as Kubernetes

    Ctrl->>K8s: Sync attempt 1
    K8s-->>Ctrl: Failed
    Note over Ctrl: Wait 5s

    Ctrl->>K8s: Sync attempt 2
    K8s-->>Ctrl: Failed
    Note over Ctrl: Wait 10s (5s * 2)

    Ctrl->>K8s: Sync attempt 3
    K8s-->>Ctrl: Failed
    Note over Ctrl: Wait 20s (10s * 2)

    Ctrl->>K8s: Sync attempt 4
    K8s-->>Ctrl: Success
    Ctrl->>App: Update status: Synced
```

### 特定のエラー時のみ Retry

現在、ArgoCD はすべての Sync 失敗に対して Retry を実行します。より詳細に制御するには、Hook を使用します。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: check-prerequisites
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 5  # Job-level retries
  template:
    spec:
      containers:
        - name: check
          image: busybox
          command:
            - sh
            - -c
            - |
              # Check if external dependency is ready
              until nc -z external-service 443; do
                echo "Waiting for external-service..."
                sleep 5
              done
              echo "Prerequisites met"
      restartPolicy: Never
```

## 選択的 Sync

Application 内の特定のリソースのみを Sync します。

### CLI 経由

```bash
# Sync specific resource by kind and name
argocd app sync my-app --resource ':Deployment:my-deployment'

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

### 選択的 Sync の Sync オプション

```bash
# Apply only out-of-sync resources
argocd app sync my-app --apply-out-of-sync-only

# Preview what would be synced
argocd app sync my-app --dry-run

# Sync with prune
argocd app sync my-app --prune
```

### リソースパス形式

```
<group>:<kind>:<name>

Examples:
:ConfigMap:my-config                 # Core API group
apps:Deployment:my-deployment        # apps API group
networking.k8s.io:Ingress:my-ingress # networking.k8s.io group
*:*:*                                # All resources
```

## クイズ

学習内容を確認するには、[ArgoCD Sync 戦略クイズ](../../quizzes/gitops/argocd/03-sync-strategies-quiz.md)に挑戦してください。
