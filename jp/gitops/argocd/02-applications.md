# ArgoCD Applications

> **レビュー基準**: Argo CD 3.5.2。リリースノートの確認後にパッチ 3.5.4 へ更新（例は再実行していません）
> **最終更新**: October 12, 2026

## 目次
- [Application CRD の概要](#application-crd-overview)
- [ソースの種類](#source-types)
- [複数のソース](#multiple-sources)
- [宛先設定](#destination-configuration)
- [ヘルス評価](#health-assessment)
- [リソースフック](#resource-hooks)
- [差分の無視](#ignore-differences)
- [App of Apps パターン](#app-of-apps-pattern)

## Application CRD の概要

例はそれぞれ独立した設定です。myorg/accounts/clusters/paths は実際に認可されたソースに置き換えてください。すべての代替案を一度に有効にするのではなく、シナリオに応じて source/sources、renderer、destination.server/name を選択してください。

Application CRD は、アプリケーションをデプロイする方法と場所を定義する ArgoCD の中核リソースです。ソースリポジトリを対象の Kubernetes cluster に接続します。

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

Application.status は controller が報告する状態です。control-plane namespace 外に Application を作成するには、管理者が application.namespaces と AppProject の sourceNamespaces、および適切な RBAC を有効にする必要があります。

### 主要フィールドの説明

| フィールド | 説明 |
|-------|-------------|
| `project` | このアプリケーションが属する AppProject |
| `source` | manifest の取得元 |
| `destination` | 対象の cluster と namespace |
| `syncPolicy` | 自動 sync と再試行の動作 |
| `ignoreDifferences` | 比較時に無視するフィールド |
| `info` | 表示用のカスタムメタデータ |
| `revisionHistoryLimit` | 保持するデプロイ revision の数 |

## ソースの種類

ArgoCD は Kubernetes manifest の取得に複数のソースタイプをサポートしています。

### プレーン YAML/JSON ディレクトリ

最も単純なソースタイプは、Kubernetes manifest を含むディレクトリです。

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
          value: ClusterIP
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### Helm リポジトリから

固定された小規模な podinfo chart は、ソース形式を示します。parameters が valuesObject を上書きするため、最終的な replicaCount は 3 です。valuesObject は構造化されたインライン値を提供します。environment variable を自動的に読み込むことはありません。

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

優先順位は parameters → valuesObject → values → valueFiles → chart defaults です。インライン表現は 1 つを推奨します。valuesObject が存在する場合は、インライン値を提供します。他の domain に credentials を転送する可能性があるため、passCredentials は必要な場合にのみ有効にしてください。このベースラインは同梱の Helm 4 を使用します。v2/v3 を任意に選択しないでください。

#### 外部ファイルの Values を使用

$values 参照には、spec.sources 内の対応する ref ソースが必要です。values の repository/file は存在し、認可されている必要があります。

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

### OCI Artifact

一般的な OCI ソースは oci:// URI と、展開された artifact 内のパスを使用します。この account/repository/tag は公開済み artifact に置き換えてください。通常の container image は自動的に manifest ソースにはなりません。

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

Argo CD 3.5.4 では、サポートされる media type を持つ layer が 1 つ必要です。デフォルトでは application/vnd.oci.image.layer.v1.tar+gzip または Helm chart content tar+gzip です。その他の type は ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES および artifact 構造で検証してください。3.5.4 以降、4 MiB を超える OCI manifest は拒否されます（GHSA-w996-f2wq-x9c6）。

Helm OCI 形式では chart フィールドと、**oci:// を含まない** repository URL を使用します。これは Application.spec 配下のソースフラグメントです。

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

credentials はソースタイプに合わせてください。一般的な OCI は type: oci と oci:// URL を使用します。Helm OCI は type: helm、enableOCI: "true"、および scheme なしの URL を使用します。ECR には registry permissions と 12 時間トークンの更新/application が必要です。IRSA permissions を付与しても、Secret は自動的には更新されません。

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

## 複数のソース

sources が存在する場合、単数形の source は無視されます。chart と values repository など、関連する 1 つの application の設定を組み合わせます。独立して管理される platform stack には ApplicationSet/App of Apps を使用してください。

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

ref: values は $values をその Git repository root にマッピングします。path がない場合は values のみを提供します。path がある場合は、そこでも manifest を生成します。ref ソースに chart を指定することはできません。group/kind/name/namespace が重複するリソースでは最後のソースが使用され、RepeatedResourceWarning が発生します。これはフィールド単位の自動 merge ではありません。

## 宛先設定

登録済みの宛先には server または name を選択してください。destination.namespace は、独自の namespace を持たない namespaced resource のデフォルトを提供します。CreateNamespace はその宛先のみを作成し、chart に明示的に埋め込まれたすべての namespace を作成するわけではありません。namespace 作成時は managedNamespaceMetadata を使用し、既存 namespace を更新する前に ownership を確認してください。

### Server URL を使用

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### Cluster 名を使用

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

Synced は、service が request を処理できることの証明ではなく、比較した desired/live field を示します。Healthy は resource ごとに設定された check に従います。check のない custom resource は application health から除外される場合があり、適切な定義が必要です。

### 組み込み Health Check

以下は、単一の replica counter に基づく完全な predicate ではなく、重要な 3.5.4 実装 check の要約です。

| Resource | 重要な check |
|---|---|
| Deployment | Observed generation、rollout の進行/失敗、更新済み/利用可能な replica |
| StatefulSet | Generation、update strategy/partition、revision と replica state |
| DaemonSet | Generation と desired/updated/available Pod 数 |
| Pod | Phase、readiness、container の終了/失敗 |
| Service | LoadBalancer は address を待機します。他の type は endpoint を検証しません |
| Ingress | controller が報告した loadBalancer address の状態 |
| PVC | Bound 状態 |
| Job | 未完了は Progressing、失敗は Degraded、完了は Healthy、suspended は Suspended |

### カスタム Health Check

同梱の Rollout/cert-manager Certificate check を単純な phase 比較に置き換えないでください。Certificate group は cert-manager.io です。同梱 check は Ready の前に Issuing を処理します。以下の ACK 例は、status/conditions がない場合に Progressing を返し、ARN の存在を Healthy と同一視しません。使用している ACK version から提供される Ready/ACK.ResourceSynced および error conditions を検証してください。この例では、Ready が存在する場合はそれを優先し、それ以外は ACK.ResourceSynced にフォールバックします。

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

これは controller が報告した状態を解釈するものであり、AWS を直接 query しません。既存の argocd-cm に key を merge し、実際の CR で missing/waiting/ready/error/new-spec の状態をテストしてください。EKS managed Argo CD は ACK/kro check を提供するため、まず既存の check とサポートされる設定を確認してください。

## リソースフック

PostSync は、成功した Sync と関連する Healthy resource を待機します。明示的な resource-selective sync では hook は実行されません。3.5.4 では、ApplyOutOfSyncOnly は引き続き hook を実行し、history を記録します。SyncFail は対象となる synchronization failure を処理します。manifest-generation failure を含むすべての error に対する保証された cleanup/backup path として依存しないでください。

Resource hook を使用すると、sync 中の特定の時点で Job を実行できます。

### Hook の種類

| Hook | 実行タイミング |
|------|---------------|
| `PreSync` | sync 開始前 |
| `Sync` | sync 中（PreSync の後） |
| `PostSync` | Sync の成功後かつ resource が Healthy のとき |
| `SyncFail` | sync の失敗後 |
| `Skip` | Manifest の適用をスキップ |
| `PreDelete` | Application とともに resource が削除される前 |
| `PostDelete` | Application resource が削除された後 |

### Hook 削除ポリシー

| Policy | 動作 |
|--------|----------|
| `HookSucceeded` | hook の成功後に削除 |
| `HookFailed` | hook の失敗後に削除 |
| `BeforeHookCreation` | 新しい hook の実行前に削除 |

### データベース移行 Hook

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

### Health Check Hook

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

固定名の Job では、繰り返し実行のために BeforeHookCreation などの lifecycle rule が必要です。cleanup 前に failure log を外部に保存してください。HookSucceeded cleanup は Argo sync phase/result semantics に従います。migration image、database Secret、ServiceAccount を準備し、idempotence、locking、rollback compatibility を別途検証してください。hook の失敗で database や既存 Deployment が自動的に revert されることはありません。PreDelete/PostDelete は通常の sync pruning ではなく、Application の削除に適用されます。

## 差分の無視

既知の別 controller が所有する特定のフィールドのみを除外してください。この Application.spec フラグメントは、production の my-deployment で HPA が管理する replica を無視します。

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

ignoreDifferences は通常、比較に影響します。RespectIgnoreDifferences=true はその影響を synchronization に拡張しますが、live resource がない初回作成では引き続き desired manifest が適用されます。広範な image、secret、resource 全体、または全 manager の rule は、重要な drift を隠す可能性があります。

webhook array では固定 index ではなく name で選択し、resource name も scope してください。これは、CA-injection controller と webhook identity が既知の場合にのみ使用してください。

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

グローバルな resource.customizations.ignoreDifferences 設定は、すべての Application に影響します。application-scoped rule を優先してください。managedFieldsManagers は、その manager が実際に所有する field を確認してから選択してください。

## App of Apps パターン

App of Apps は管理用の bootstrap pattern です。親ソースの writer は management namespace 内の強力な Application/AppProject に影響を与えられます。write/review/destination privileges を制限してください。親/子 finalizer と pruning は削除を連鎖させる可能性があります。子 Application を順番に作成しても、それ自体では子 workload の readiness は保証されません。Application health propagation、sync policy、wave behavior を検証してください。

App of Apps パターンを使用すると、単一の親 application から複数の application を管理できます。

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

### 親 Application

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

### 子 Application テンプレート

この monitoring の子は kube-prometheus-stack 90.0.0 に固定されています。その chart の upgrade/CRD 要件を確認し、monitoring capacity は別途用意してください。namespace monitoring に admin-user/admin-password key を持つ保護済みの grafana-admin Secret を事前に作成してください。admin credentials を親 Git values に入れないでください。

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

### App of Apps の Sync Wave

以下は metadata のみのフラグメントです。完全な子 spec と組み合わせてください。子 Application の作成順序は、子 workload の readiness を保証するものではありません。子 Application health propagation と sync policy を設定・検証してください。

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

## Revision History と Rollback

automated sync が有効な間は history rollback を使用できません。最初に実際の Git/ApplicationSet owner の policy を確認してください。rollback は Git を更新しないため、後の reconciliation で Git state が復元される可能性があります。意図した変更は承認済みの Git revert/revision change を通じて永続化してください。database/external-state recovery は別の作業です。

### History を表示

```bash
# CLI
argocd app history my-app

```

出力例（shell command ではありません）：

```text
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ab89012
```

### Rollback

実際の history から ID を選択してください。以前の manifest revision の適用と余分な resource の pruning は別々の判断です。

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### 宣言的 Rollback

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

## クイズ

学んだ内容をテストするには、[ArgoCD applications クイズ](../../quizzes/gitops/argocd/02-applications-quiz.md)を試してください。

## バージョン付きレビューソース

- [3.5.4 のソースと Helm](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/helm.md)
- [複数のソース](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/multiple_sources.md)
- [OCI ソースのルール](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/oci.md)
- [Sync オプション](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [フェーズ、wave、hook](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [Service health の実装](https://github.com/argoproj/argo-cd/blob/v3.5.4/gitops-engine/pkg/health/health_service.go)
- [ACK condition の定義](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
