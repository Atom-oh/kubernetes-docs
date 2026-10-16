# ArgoCD 同期戦略

> **レビュー基準**: Argo CD 3.5.2。リリースノートの確認後にパッチ 3.5.4 へ更新（例は再実行していません）
> **最終更新**: October 12, 2026

## 目次
- [Manual vs Automated Sync](#manual-vs-automated-sync)
- [Auto-Sync Policies](#auto-sync-policies)
- [Sync Options](#sync-options)
- [Sync Waves and Phases](#sync-waves-and-phases)
- [Sync Windows](#sync-windows)
- [Diffing Customization](#diffing-customization)
- [Retry Policies](#retry-policies)
- [Selective Sync](#selective-sync)

## 手動同期と自動同期

例はそれぞれ独立したポリシーの断片です。実際の Application の source/destination/project を保持し、必要なオプションだけを選択してください。Sync は変更を適用し、Refresh はソース/キャッシュから比較を更新します。Synced はヘルスおよび実際のサービス可用性とは別のものです。

ArgoCD は、手動と自動の 2 つの同期モードをサポートします。

### 手動同期

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

手動同期をトリガーします。

```bash
# Via CLI
argocd app sync my-app

# Sync specific resources only
argocd app sync my-app --resource 'apps:Deployment:my-deployment'

# Preview changes; pruning and force are separate, potentially destructive decisions
argocd app sync my-app --dry-run
```

### 自動同期

自動モードでは、変更が検出されると ArgoCD が自動的に同期します。

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

![Argo CD は、Git リポジトリ内の目的の状態を Kubernetes クラスターのライブ状態と継続的に比較し、OutOfSync の差分を検出すると変更を適用して、ライブ状態を再び Git と一致させます。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-0.html)

## 自動同期ポリシー

automated: {}、または enabled フラグを省略するか null にすると自動同期が有効になり、enabled: false で無効になります。ライブ状態のみのドリフト修正には selfHeal が必要であり、prune は別の機能です。失敗した同一のコミット/パラメーターの組み合わせは、デフォルトでは無期限に再試行されません。retry ポリシーを設定してください。ApplicationSet で管理される Application では、所有するテンプレートを変更してください。

### Prune

Git に存在しなくなったリソースを自動的に削除します。

```yaml
syncPolicy:
  automated:
    prune: true
```

**ユースケース**: クラスターの状態を Git リポジトリと完全に一致させます。孤立したリソースを削除します。

Prune は Application が追跡するリソースに影響し、クラスター内のすべての孤立リソースに影響するわけではありません。PruneLast は順序を変更しますが、データを保護したり、削除のレビューに置き換わったりはしません。

### Self-Heal

クラスターに対して手動で行われた変更を自動的に元に戻します。

```yaml
syncPolicy:
  automated:
    selfHeal: true
```

**ユースケース**: 手動の kubectl 変更やその他のツールによる設定ドリフトを防止します。

![ユーザーが kubectl で Deployment を手動スケーリングし、Argo CD が状態変更を検出して Git から目的のレプリカ数を読み取り、再適用することで Kubernetes が Git で宣言された状態へ自己修復するまでを示すシーケンス図。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-1.html)

### 空を許可

リソースを持たない Application を許可します。

```yaml
syncPolicy:
  automated:
    allowEmpty: true
```

自動 prune が有効な場合、レンダリングが空集合を返すと、allowEmpty によって管理対象のすべてのリソースの削除が許可される可能性があります。これは汎用的なブートストラップ要件ではありません。

### 完全な自動同期設定

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

## 同期オプション

同期オプションは、同期動作をきめ細かく制御します。

### 使用可能な同期オプション

| オプション | 説明 | デフォルト |
|--------|-------------|---------|
| `Validate` | スキーマに対してリソースを検証 | true |
| `CreateNamespace` | 存在しない場合に namespace を作成 | false |
| `PrunePropagationPolicy` | 削除伝播ポリシー | foreground |
| `PruneLast` | 他のすべての同期後に prune を実行 | false |
| `Replace` | apply の代わりに replace を使用 | false |
| `FailOnSharedResource` | 別の Argo CD Application がリソースを追跡している場合に失敗 | false |
| `ApplyOutOfSyncOnly` | OutOfSync のリソースのみを適用 | false |
| `ServerSideApply` | サーバーサイド apply を使用 | false |
| `RespectIgnoreDifferences` | 同期時に ignoreDifferences を尊重 | false |

`Validate=false` は apply 時のスキーマ検証をスキップします。存在しない CRD をインストールするわけではありません。Argo CD は、CRD が同じ同期内でインストールされる場合、その CR のドライランを自動的にスキップします。別の controller によって CRD が作成される場合など、正当なケースでのみ `SkipDryRunOnMissingResource=true` を使用し、CRD が利用可能であることを確認してください。

`PruneLast=true` は、他のリソースがデプロイされ Healthy になった後、最終的な暗黙の wave で prune をスケジュールします。`FailOnSharedResource=true` は、別の Argo CD Application による追跡を確認します。他の Kubernetes controller や Flux とのすべての所有権競合を検出するわけではありません。

### Application レベルのオプション

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

### リソースレベルのオプション

アノテーションを使用して、特定のリソースに同期オプションを適用します。

```yaml
# Merge into an existing complete resource manifest.
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

### サーバーサイド Apply

Argo CD 3.5.4 は --server-side --force-conflicts を呼び出します。フィールドの所有権は追跡されますが、競合が拒否されることを保証するものではありません。所有権の引き継ぎの可能性をレビューしてください。

より適切に競合を検出するため、Kubernetes のサーバーサイド apply を使用します。

```yaml
syncPolicy:
  syncOptions:
    - ServerSideApply=true
```

または、リソース単位で設定します。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true
```

**利点**:
- フィールド所有権の追跡が向上
- 所有権の競合は Argo CD により強制解決できます。意図する manager の境界を確認してください
- CRD および webhook と適切に連携

### Replace と Force

Replace は kubectl replace/create を選択します。不変フィールドが自動的に編集可能になるわけではありません。Replace=true とともに Force=true を使用すると、オブジェクトを削除/再作成する可能性があり、これは別個の破壊的な選択です。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-options: Replace=true
```

不変の変更には、リソース固有の移行/再作成計画が必要です。PVC の storage-class 移行の近道として使用しないでください。削除前に保持、データ、可用性をレビューしてください。Replace は ServerSideApply より優先されます。

## 同期 Wave とフェーズ

同期 wave はリソースを適用する順序を制御します。

### Wave の仕組み

リソースは wave 番号でグループ化され、順に同期されます。
1. フェーズ、wave、kind、名前の順でソートします。
2. 負の Sync wave は PreSync フェーズより前には実行されません。
3. Wave の進行は同期/ヘルス状態に従います。依存関係について、同一 wave 内の物理的な並行実行に依存しないでください。準備完了状態で後続の作業をブロックする必要がある場合、Custom Resource には意味のあるヘルスチェックが必要です。

![Argo CD の同期 wave が昇順で適用されるワークフロー図。wave -2 の CRD、wave -1 の Namespace と ServiceAccount、デフォルトの wave 0 の ConfigMap、Secret、Deployment、続いて wave 1 の Service と Ingress があり、各 wave は前の wave が健全になるまで待機します。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-2.html)

### 同期 Wave の設定

この断片を完全なリソース manifest の metadata にマージしてください。完全な例は後に続きます。

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
```

### Wave と Hook の組み合わせ

PreSync は通常のすべての Sync wave より前に実行されます。以下の既存の Service、namespace、DB Secret、移行イメージは、あらかじめ準備されている必要があります。PreSync は、後の Sync wave で作成されるデータベースへのアクセスを前提にできません。

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

pg_dump を stdout に出力するだけの Job は、復元可能なバックアップ手順ではありません。永続的な暗号化ストレージ、完了の検証、復元テストを使用してください。移行のべき等性、ロック、リカバリを検証してください。PostSync の失敗は自動ロールバックではありません。

### 最小限の動作する順序付けの例

この最小例では、同じ Sync フェーズ内で Namespace → ConfigMap → Service → readiness を備えた Deployment の順に並べます。Healthy な Service オブジェクトは、準備完了した endpoint を証明するものではありません。Deployment probe がワークロードの準備完了を確認します。Argo Project/RBAC と image-registry へのアクセスを準備してください。

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

データベースでは、まず認証、永続化、Service、実際の準備完了を用意してください。HPA には CPU requests と metrics の可用性が必要です。準備完了に必要な Service/ConfigMap を後の wave に置かないでください。

## Sync Window

この例では、日曜日の 02:00～06:00 KST に本番プロジェクトの prod-* Application を許可し、03:00～04:00 は凍結します。リポジトリ/destination は実際に認可されたスコープに置き換えてください。

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

新しい自動同期リクエストでは、次のようになります。

1. 一致する window がない場合、window による制限はありません。
2. アクティブで一致する deny があれば、ブロックされます。
3. それ以外の場合、アクティブな allow が許可します。
4. 一致する allow window がすべて非アクティブであれば、ブロックされます。
5. allow window がなく、非アクティブな deny のみの場合は許可されます。

Application/namespace/cluster のセレクターのデフォルトは OR です。特異性による順位付けはありません。指定されたセレクターがすべて一致する必要がある場合は、andOperator: true を使用してください。デフォルトのタイムゾーンは UTC です。KST のコメントでは変更されません。

手動例外は、関連するすべてのブロッキング window が manualSync を許可していることと、呼び出し元に同期権限があることに依存します。--force は回避策ではありません。常時アクティブな 24 時間の allow は手動で有効化する緊急スイッチではなく、自動同期も許可できます。window 境界をまたいだ実行継続は syncOverrun、開始時刻、関連する window に依存します。完了またはロールバックを保証するものではありません。

```bash
argocd proj windows list production -o yaml
argocd app get my-app
```



![新しい自動同期の判断フロー。一致する window、アクティブな deny/allow、非アクティブな allow を区別します。](../../.gitbook/assets/en-gitops-argocd-03-sync-strategies-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-03-sync-strategies-4.html)

## 差分カスタマイズ

別の controller が所有する実際のフィールドだけを、名前/namespace でスコープして無視してください。たとえば、1 つの HPA 管理対象 Deployment の replicas を除外します。広範な image、すべての annotation/resources、またはすべての manager の除外をデフォルトにしないでください。

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

ignoreDifferences は比較を制御します。RespectIgnoreDifferences は同期にも拡張しますが、ライブオブジェクトなしで初期作成する場合は、依然として目的の manifest を使用します。manager を選択する前に、実際の管理対象フィールドを確認してください。グローバル/ステータスの比較除外はヘルス評価を無効にせず、image の改ざんを隠すべきではありません。

スコープされたルールについては、[Application ignore-difference の例](02-applications.md#ignore-differences)を参照してください。

## 再試行ポリシー

limit: 5 は、初回試行後に 5 回の再試行、合計で最大 6 回の試行を許可します。遅延は 5s、10s、20s、40s、80s から始まります。maxDuration は同期全体や hook ではなく、個別のバックオフを上限設定します。Application の retry と Job の backoffLimit/activeDeadlineSeconds は別のレイヤーです。

同期失敗時の自動再試行を設定します。

### 基本的な再試行設定

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

### 再試行フロー

limit: 5 は、初回試行後に最大 5 回の再試行を許可します。duration が 5s、factor が 2 の場合、遅延は 5s、10s、20s、40s、80s で始まります。maxDuration は個別のバックオフ遅延を上限設定するものであり、同期/hook 全体のタイムアウトではありません。

### 上限付き依存関係 Preflight

preflight hook は上限のある期限で失敗できます。Argo のエラーコード別 retry フィルターを追加するものではありません。以下の依存関係は、すでに存在している必要があります。

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

## 選択的同期

明示的な --resource/--label 選択では、hook と履歴がスキップされます。ApplyOutOfSyncOnly/--apply-out-of-sync-only は 3.5.4 で hook/履歴を保持します。--label はリソースを選択し、--selector(-l) は Application を選択します。

Application 内の特定のリソースのみを同期します。

### CLI を使用

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

### 選択的同期の同期オプション

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

学習内容を確認するには、[ArgoCD 同期戦略クイズ](../../quizzes/gitops/argocd/03-sync-strategies-quiz.md)を試してください。

## バージョン固定のレビューソース

- [3.5.4 同期オプション](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [Sync window](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync_windows.md)
- [Window の一致と CanSync](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/types.go)
- [フェーズと wave](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [CLI リソース/Application セレクター](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/commands/argocd_app_sync.md)
