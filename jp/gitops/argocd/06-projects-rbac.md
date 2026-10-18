# ArgoCD Projects と RBAC

> **レビュー対象**: Argo CD 3.5.2。リリースノートのレビュー後にパッチ 3.5.5 へ更新（例は再実行していません）
> **最終更新**: 2026年10月16日

## 目次
- [AppProject の概要](#appproject-overview)
- [デフォルト Project](#default-project)
- [カスタム Project](#custom-projects)
- [RBAC 設定](#rbac-configuration)
- [マルチテナンシーのパターン](#multi-tenancy-patterns)
- [CI/CD 用 JWT Token](#jwt-tokens-for-cicd)
- [孤立リソースのモニタリング](#orphaned-resource-monitoring)

## AppProject の概要 {#appproject-overview}

AppProject は Application を論理的にグループ化し、デプロイ可能なリソース、デプロイ先、および管理者を対象とするアクセス制御を定義します。

AppProject はソース、宛先、レンダリングされたリソース種別、および Argo CD API の権限を制限します。Kubernetes RBAC、Pod Security Admission、NetworkPolicy、ResourceQuota を置き換えるものではありません。Pod 種別を拒否しても、Deployment による特権 Pod の作成は防げません。

実際のリポジトリ URL、グループ、登録済み Cluster、Namespace を指定してください。プラットフォーム管理者は Application Namespace を事前作成し、そのセキュリティおよびクォータポリシーを所有します。以下のチーム/環境 Project では Cluster スコープのリソースを許可していません。別のプラットフォーム Project は信頼できる管理者向けです。完全な Project の例は、それぞれ独立した代替案であり、同名のものも含まれます。

### 主な機能

| 機能 | 説明 |
|---------|-------------|
| ソースの制限 | 使用できる Git リポジトリを制限する |
| 宛先の制限 | 対象 Cluster と Namespace を制限する |
| リソースの許可リスト/拒否リスト | 作成できる K8s リソースを制御する |
| Role の定義 | Project 固有の RBAC Role を定義する |
| Sync Window | Application が sync できる時間を定義する |

### AppProject 設定例

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

## デフォルト Project {#default-project}

ArgoCD は、すべてのソース、宛先、およびリソース種別を許可するデフォルト Project を作成します。制限はできますが削除はできません。

### デフォルト Project の仕様

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

### デフォルト Project を使用する場合

- 開発環境
- 簡易テスト
- マルチテナンシー要件のない小規模チーム

### デフォルト Project の制限

本番環境では、デフォルト Project を制限してください。

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

## カスタム Project {#custom-projects}

### チームベースの Project

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

### 環境ベースの Project

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

### プラットフォームインフラストラクチャ Project

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

### スコープの解釈と検証

- AppProject の宛先は、`(server OR registered name) AND namespace` に一致します。両方の Cluster 識別子を指定しても AND 制約は追加されません。これらの例では server のみを使用しています。一方、Application の宛先では server または name のいずれかを選択する必要があります。
- ResourceQuota と LimitRange は Namespace スコープです。`clusterResourceBlacklist` ではこれらをブロックできません。Argo CD のデプロイパスには `namespaceResourceBlacklist` を使用してください。
- `namespaceResourceWhitelist` を省略すると、デフォルトで Namespace スコープの種別が許可されます。明示的な許可/拒否リストはともに評価されます。Cluster スコープの種別には許可リストが必要です。Argo CD 3.5.4 は、Cluster リソースリスト内の name パターンもサポートしています。
- Namespace 管理を委任する場合は、その name も制限してください（`group:'', kind:Namespace, name:team-a-*`）。それでも Namespace label の変更は許可されます。テナント境界には、事前プロビジョニングと Admission Control の方が安全です。
- `manualSync` は許可 Window 外での手動例外を許可します。自動 sync を無効化するものでも、例外をオンコール Role に限定するものでもありません。sync の章で、重複する拒否 Window と明示的な Time Zone を確認してください。
- デフォルトを制限する前に、既存の Application を明示的な Project に移動し、アクセスを検証してください。

## RBAC 設定 {#rbac-configuration}

ArgoCD RBAC は `argocd-rbac-cm` ConfigMap で設定します。

### RBAC ポリシーの構文

```
p, <subject>, <resource>, <action>, <object>, <effect>
g, <subject>, <role>
```

| フィールド | 説明 |
|-------|-------------|
| `subject` | User、group、または Role |
| `resource` | applications、clusters、repositories など |
| `action` | get、create、update、delete、sync など |
| `object` | リソース識別子（project/app または *） |
| `effect` | allow または deny |

### 組み込み Role

| Role | 説明 |
|------|-------------|
| `role:readonly` | すべてのリソースへの読み取り専用アクセス |
| `role:admin` | すべてのリソースへの完全アクセス |

### 完全な RBAC 設定

この例では、暗黙的な Application アクセスを許可せず、明示的な group 権限を割り当てます。Developer は team-frontend にスコープされます。role:authenticated にはポリシーエントリを残さないでください。デフォルトポリシーによって付与された権限は User deny では削除できません。role:readonly をデフォルトにすると、Project をまたいだ読み取りが公開されます。組み込み Role のルールを policy.csv にコピー/再定義しないでください。

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

追加のポリシーフラグメントは、Kustomize/Helm を使用して既存の ConfigMap data に統合してください。Argo CD は policy.example-N.csv キーを policy.csv に追加します。各フラグメントを ConfigMap 全体の置き換えとして適用したり、無関係に広い allow の例を蓄積したりしないでください。

Argo CD API RBAC は Kubernetes RBAC とは別です。object の project/app は宛先 Namespace を識別しません。コントロールプレーン Namespace 外の Application も project/application-namespace/app を使用します。Glob マッチングは slash を区切り文字として扱わないため、完全な resource-action path を含めてください。

3.x のデフォルトでは、Application の update/delete 権限は、子 Kubernetes リソースに対する同じ操作を自動的には付与しません。これらの操作には、`server.rbac.disableApplicationFineGrainedRBACInheritance` を考慮して `update/<group>/<kind>/<namespace>/<name>` または `delete/...` を使用してください。

sync はデプロイ済みリソースの作成、更新、および prune を実行できます。Application の削除を拒否しても、sync/prune による削除は防げません。rollback API も sync を確認します。個別の action/rollback または rollback 専用の権限はありません。override はローカル manifest などのソース置換を許可するもので、単に sync を強制するものではありません。`application.sync.requireOverridePrivilegeForRevisionSync` は、revision が指定された場合に override を要求できます。

### リソース固有の権限

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

### Application 固有のアクション

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

## マルチテナンシーのパターン {#multi-tenancy-patterns}

### チームごとの Namespace

![チーム A、チーム B、およびプラットフォームチームは、宛先によって Argo CD のデプロイ先をそれぞれの Namespace（team-a、team-b、および共有の monitoring と logging Namespace）に制限する ArgoCD AppProject 内で Application Role を受け取ります。](../../.gitbook/assets/en-gitops-argocd-06-projects-rbac-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-06-projects-rbac-0.html)

実装:

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

### 環境ごとの Cluster

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

## CI/CD 用 JWT Token

自動化のために Project スコープの Token を作成します。

### JWT Token の作成

Project を更新する権限を持つ Operator が Token を発行/取り消しします。CI Role 自体には get/sync のみが付与されます。まず my-project、その ci-deployer Role、および my-app Application を準備してください。有効期限前にローテーションしてください。CLI のデフォルトでは有効期限はありません。

```bash
set -euo pipefail
umask 077
# Run as an operator authorized to update my-project.
argocd proj role create-token my-project ci-deployer \
  --expires-in 24h --token-only > ./argocd-ci.token
# Store this file's value in the approved CI secret store; do not commit or print it.
```

明示的な識別子が必要な場合は `--id UNIQUE_ID` を使用してください。--token-id は 3.5.4 の flag ではありません。expires-in は 24h などの duration を受け入れます。署名済み Token の値は発行時に返され、後で取得するためには保存されません。

### CI/CD での Token の使用

この Role を既存の my-project AppProject にマージしてください。これだけではソース/宛先の権限や Application は作成されません。

```yaml
spec:
  roles:
  - name: ci-deployer
    policies:
    - p, proj:my-project:ci-deployer, applications, get, my-project/*, allow
    - p, proj:my-project:ci-deployer, applications, sync, my-project/*, allow
```

workflow は workflow SHA を強制するのではなく、Application で宣言された revision を sync します。不変の revision が必要な場合は Git で targetRevision を pin してください。--revision を使用する前に server override の設定を確認してください。本番 Environment の承認/保護ルールは別途設定してください。

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

Token メタデータは Project の Role/status レコードに保存/正規化されます。iat/exp/id を手動で宣言しても、署名済み Token は発行されません。Role ポリシーの変更は、すでに発行済みの Token に影響します。Operator 認証情報を使用して、ID label ではなく ISSUED AT の整数値により 1 つの Token を取り消してください。

```bash
argocd proj role list-tokens my-project ci-deployer --unixtime

# Select one token's ISSUED AT value from the list, using operator credentials.
: "${SELECTED_ISSUED_AT:?Set the selected integer ISSUED AT value}"
argocd proj role delete-token my-project ci-deployer "$SELECTED_ISSUED_AT"
```

### In-Cluster CI の Token ストレージ

Kubernetes Secret には、CI job 用に以前発行した Token を保存できます。これは Argo CD Token の発行者ではなく、特別な argocd-token Secret type もありません。たとえば、CI job の Namespace と安全なファイル入力を使用してください。

```bash
kubectl create secret generic argocd-ci-token -n ci \
  --from-file=token=./argocd-ci.token
```

先に ci Namespace と job RBAC をプロビジョニングしてください。承認済みの CI job でのみ Secret を mount/read し、Token の有効期限前に値をローテーションしてください。Token の値を Git に置かないでください。

## 孤立リソースのモニタリング {#orphaned-resource-monitoring}

ArgoCD で管理されていない対象 Namespace 内のリソースを検出します。

### 孤立リソースモニタリングを有効にする

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

### 孤立リソースを表示する

```bash
argocd app resources my-app --orphaned

: "${ARGOCD_AUTH_TOKEN:?Provide an authorized token securely}"
curl --fail --silent --show-error --max-time 30 \
  -H "Authorization: Bearer $ARGOCD_AUTH_TOKEN" \
  https://argocd.example.com/api/v1/applications/my-app/resource-tree \
  | jq '.orphanedNodes'
```

警告は任意です。warn:false でも孤立候補の表示は許可されます。Project によって拒否されたリソースと組み込みのデフォルト object には例外があります。大規模な kube-system のスキャンを避けるため、モニタリングする Namespace を絞り込んでください。

### クリーンアップ前の確認

孤立モニタリングは、Argo CD Application によって追跡されていないトップレベルの Namespace スコープリソースを報告します。それらは別の Operator に属している場合や、GitOps 外で意図的に管理されている場合があります。label selector `managed-by!=argocd` はそのような label がないリソースにも一致し、Argo CD の追跡を実装するものではありません。その selector を PostSync の削除 job に変換しないでください。

リソースが廃止済みかどうかを判断する前に、孤立リスト、owner reference、実際の Argo CD 追跡メタデータ、および所有 Controller を確認してください。正当なリソースは、スコープを狭くした孤立モニタリングの ignore ルールで除外してください。削除する場合は、明示的にレビューしたリソースリストと適切なバックアップ/復旧手順を使用する必要があります。ここでの例は候補を報告するだけです。

## ポリシーの検証

ベース ConfigMap の例を argocd-rbac-cm.yaml として保存してください。CLI は有効な kubeconfig も初期化しますが、policy-file チェックは live 設定を変更しません。動的な AppProject Role、実際の SSO claim、および Kubernetes admission は別途確認してください。

```bash
argocd admin settings rbac validate --policy-file ./argocd-rbac-cm.yaml
argocd admin settings rbac can developers sync applications team-frontend/my-app \
  --policy-file ./argocd-rbac-cm.yaml
# Expected: No (exit 1)
argocd admin settings rbac can developers get applications team-b/my-app \
  --policy-file ./argocd-rbac-cm.yaml
```

validate は、組み込み role:admin が User CSV にないという警告を出す場合があります。can はデフォルトで組み込みポリシーを含みます。警告を消すために組み込み Role を複製しないでください。local-user/SSO-group の衝突と実際の group claim を確認してください。exec ポリシーだけでは terminal は有効になりません。exec.enabled と基盤となる Kubernetes 権限も確認してください。

## 参照

- [Argo CD 3.5.4 RBAC](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/rbac.md)
- [Project のマッチングと検証](https://github.com/argoproj/argo-cd/blob/v3.5.4/pkg/apis/application/v1alpha1/app_project_types.go)
- [ソースの整合性](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/source-integrity-git-gpg.md)
- [Project Token CLI](https://github.com/argoproj/argo-cd/blob/v3.5.4/cmd/argocd/commands/project_role.go)

## クイズ

学習内容を確認するには、[ArgoCD Projects と RBAC のクイズ](../../quizzes/gitops/argocd/06-projects-rbac-quiz.md)を試してください。
