# ArgoCD ベストプラクティス

> **レビューのベースライン**: Argo CD 3.5.2 / Helm Chart 10.8.4 / Kustomize 5.8.1。リリースノートを確認したうえで、マニフェスト例をパッチ 3.5.5 向けに更新しました（引き続き Kustomize 5.8.1 をバンドル）。例は再実行していません。
> **最終更新**: 2026年10月16日

## 目次

- [リポジトリ構造](#repository-structure)
- [環境プロモーション](#environment-promotion)
- [リソース管理](#resource-management)
- [パフォーマンスチューニング](#performance-tuning)
- [障害復旧](#disaster-recovery)
- [アップグレード戦略](#upgrade-strategies)
- [トラブルシューティング](#troubleshooting)
- [EKS のベストプラクティス](#eks-best-practices)
- [本番環境チェックリスト](#production-checklist)

## リポジトリ構造 {#repository-structure}

### モノレポパターン

すべてのアプリケーションと環境を単一のリポジトリで管理します。

```
gitops-repo/
├── apps/
│   ├── app-a/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       ├── staging/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       └── production/
│   │           ├── kustomization.yaml
│   │           └── patch.yaml
│   └── app-b/
│       └── ...
├── platform/
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
└── clusters/
    ├── dev/
    ├── staging/
    └── production/
```

**長所:**
- 信頼できる唯一の情報源
- アプリケーション横断の変更が容易
- CI/CD を簡素化
- 1 つの原子的な Git コミットで複数アプリを記述できる。ただし、それらのクラスターへのデプロイは単一の原子的トランザクションではない

**短所:**
- 大規模になり得る
- アクセス制御が複雑
- 単一障害点

![1 つの Git リポジトリに app-a、app-b、infra ディレクトリを保持するモノレポと、同じコンポーネントを app-a-repo、app-b-repo、infra-repo という 3 つの独立した Git リポジトリに分割するポリレポを比較した図。](../../.gitbook/assets/en-gitops-argocd-09-best-practices-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-09-best-practices-0.html)

### ポリレポパターン

アプリケーションまたはチームごとにリポジトリを分離します。

```
Organization:
├── gitops-platform/          # Platform team
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
├── gitops-team-a/            # Team A applications
│   ├── app-a/
│   └── app-b/
├── gitops-team-b/            # Team B applications
│   ├── app-c/
│   └── app-d/
└── gitops-infra/             # Infrastructure
    ├── terraform/
    └── clusters/
```

**長所:**
- 明確なオーナーシップ
- 独立したデプロイ
- きめ細かなアクセス制御
- リポジトリサイズが小さい

**短所:**
- 変更の調整がより困難
- 管理すべきリポジトリが増える
- 乖離が発生する可能性

### App of Apps のリポジトリ構造

```
gitops-root/
├── argocd-apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-staging.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml
│       ├── project.yaml
│       ├── app-a.yaml
│       ├── app-b.yaml
│       └── platform-apps.yaml
└── bootstrap/
    └── root-app.yaml
```

### 推奨される命名規則

| 種類 | パターン | 例 |
|------|---------|---------|
| Application | `{app}-{env}` | `frontend-production` |
| Project | `{team}` または `{env}` | `platform`, `production` |
| Namespace | `{app}` または `{app}-{env}` | `frontend`, `frontend-prod` |
| リポジトリ | `gitops-{scope}` | `gitops-platform` |

## 環境プロモーション {#environment-promotion}

### Git ブランチ戦略

長期間存続する環境ブランチも選択肢の 1 つですが、共有の main ブランチ上のディレクトリベースのオーバーレイは、ブランチの乖離を抑えられる場合がよくあります。App of Apps は管理機能です。ルートリポジトリへのアクセスと子 Application の作成を制限してください。手動の本番同期は、レビュー済みの Git 変更とは別のゲートです。

### ディレクトリベースのプロモーション

環境ごとに再ビルドせず、同じテスト済みアーティファクトをプロモートします。これらの例は既存の base と、レジストリによって強制されるイミュータブルなタグを前提としています。タグのイミュータビリティが保証されない場合は digest を優先してください。可変タグの内容を変更しても、Git や Deployment の Pod template 自体は更新されません。base のイメージ名は `my-app` です。オーバーレイでは name/tag の変換を一緒に適用してください。以前の名前に一致するオーバーレイでは、base によってすでに名前変更されたイメージは更新されません。

```yaml
# overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3

---
# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3

---
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3
```

### 自動プロモーションパイプライン

このワークフローは、**すでにテスト済みの digest** に対する PR を作成します。例のレジストリとオーバーレイパスは適宜変更してください。対象リポジトリへの contents/pull requests の書き込み権限をスコープしたトークン、または GitHub App トークンを使用して `GITOPS_PR_TOKEN` を指定します。デフォルトの GITHUB_TOKEN による変更には、後続ワークフローのトリガー制限があります。必要なチェックを実行できることを確認してください。リポジトリの ruleset/branch protection を通じて、レビュー、テスト、アーティファクトポリシーを強制します。

```yaml
name: Promote tested image to production
on:
  workflow_dispatch:
    inputs:
      digest:
        description: 'Tested image digest (sha256: followed by 64 hex characters)'
        required: true
        type: string
permissions:
  contents: read
concurrency:
  group: promote-production
  cancel-in-progress: false
jobs:
  promote:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Install verified Kustomize
        shell: bash
        run: |
          set -euo pipefail
          tool_dir="$RUNNER_TEMP/kustomize-bin"
          mkdir -p "$tool_dir"
          cd "$tool_dir"
          curl -fsSL -o kustomize.tar.gz \
            https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v5.8.1/kustomize_v5.8.1_linux_amd64.tar.gz
          echo "029a7f0f4e1932c52a0476cf02a0fd855c0bb85694b82c338fc648dcb53a819d  kustomize.tar.gz" | sha256sum -c -
          tar -xzf kustomize.tar.gz kustomize
          echo "$tool_dir" >> "$GITHUB_PATH"
      - name: Update production overlay
        env:
          IMAGE_DIGEST: ${{ inputs.digest }}
        shell: bash
        run: |
          set -euo pipefail
          [[ "$IMAGE_DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]] || exit 1
          cd overlays/production
          kustomize edit set image "my-app=my-registry/my-app@${IMAGE_DIGEST}"
          kustomize build . > /dev/null
      - name: Create reviewed promotion PR
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          token: ${{ secrets.GITOPS_PR_TOKEN }}
          branch: promote-production
          title: 'Promote tested image to production'
          commit-message: 'chore: promote tested image digest'
          add-paths: overlays/production/kustomization.yaml
          body: |
            Promote the already tested image digest: ${{ inputs.digest }}
            Require the repository's validation and approval checks before merging.
```

## リソース管理 {#resource-management}

### コンポーネントリソース

これらの Chart 10.8.4 の値は、保証されたサイジング表ではなく、**測定の出発点**です。既存の values にマージし、デプロイのオーナーを 1 つに維持してください。Chart は正しいコンテナ名とワークロードタイプを提供します。意図せずコンテナを追加してしまう不完全な Deployment patch は避けてください。

```yaml
fullnameOverride: argocd
controller:
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: '2'
      memory: 4Gi
server:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: '1'
      memory: 2Gi
```

| 測定項目 | チューニングの方向性 |
|---|---|
| マニフェスト時間、同時リクエスト、リポジトリサイズ | repo-server の CPU/メモリ、並列度、ディスク |
| クラスターあたりのリソース数と watch/cache メモリ | Controller のメモリとクラスター分散 |
| reconciliation/sync キューの遅延と API スロットリング | ターゲット API 容量と併せた processor の同時実行数 |
| CPU スロットリング、OOM、再起動 | 同時実行と併せた requests/limits |

Application 数だけでは、100/500 Application での sharding 閾値は決まりません。Redis は再構築可能なキャッシュですが、キャッシュの喪失により再計算の負荷とレイテンシーが生じることがあります。[HA インストールのセクション](01-installation.md#high-availability-setup)にある node/anti-affinity/PDB の前提条件を適用してください。すべてのコンポーネントを無条件にレプリケートしないでください。

### 任意の repo-server HPA

これには Metrics Server と CPU requests が必要です。HPA を有効にすると、レプリカ数は HPA が管理します。CPU スケーリングでは、すべてのマニフェスト生成のボトルネックを説明できません。持続的なキャッシュメモリだけに基づくスケーリングは、不要なレプリカを実行し続ける可能性があります。

```yaml
repoServer:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: null
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
```

## パフォーマンスチューニング {#performance-tuning}

### 設定の配置場所と意味

これらを同じ Helm values にマージしてください。`configs.params` は `argocd-cmd-params-cm` を、`configs.cm` は `argocd-cm` を生成します。コマンドライン/環境設定を通じて利用される値には、影響を受ける controller/repo-server/server の rollout が必要です。レンダリングされた Pod と起動ログを確認してください。

```yaml
configs:
  params:
    controller.status.processors: '20'
    controller.operation.processors: '10'
    controller.repo.server.timeout.seconds: '180'
    server.repo.server.timeout.seconds: '180'
    reposerver.parallelism.limit: '2'
    reposerver.repo.cache.expiration: 24h
    reposerver.git.request.timeout: 30s
    reposerver.git.lsremote.parallelism.limit: '5'
  cm:
    timeout.reconciliation: 300s
    timeout.reconciliation.jitter: 60s
    application.resourceTrackingMethod: annotation
repoServer:
  env:
  - name: ARGOCD_EXEC_TIMEOUT
    value: 2m
```

- Status/operation processor はポーリング頻度ではなく同時実行数を制御します。20/10 はデフォルトの同時実行値です。
- 180 秒の repo-server RPC timeout、2 分間のツール実行 timeout、30 秒の Git request timeout は異なる制限です。これらを増やす前に、遅いステージとキャンセルの動作を特定してください。
- `reposerver.parallelism.limit` はキャッシュ TTL ではなく、同時マニフェスト生成数を制限します。メモリ/process 制限に対して負荷テストしてください。
- デフォルトの定期 reconciliation は 120 秒に最大 60 秒の jitter を加えたものです。この例では 300 + 60 秒（5～6 分）を使用しています。webhook やその他の refresh 要因は別です。
- `application.resourceTrackingMethod` は refresh 頻度ではなくリソース追跡を設定します。既存の追跡方式を変更する前に、移行の影響を確認してください。

### 複数の宛先クラスターのシャーディング

デフォルトの sharding 単位は宛先 **cluster** です。レプリカ数を増やしても、1 つの cluster を対象とするすべての Application が均等に分散されるわけではありません。Chart は StatefulSet のレプリカを `ARGOCD_CONTROLLER_REPLICAS` と連携させます。このバージョンでは round-robin/consistent-hashing と動的クラスター分散は experimental です。これらを普遍的な本番デフォルトとして示さないでください。

```yaml
controller:
  replicas: 3
configs:
  params:
    controller.sharding.algorithm: legacy
```

### Application の境界と HPA

大規模な Application は、オーナーシップとライフサイクルの境界に沿って分割してください。任意のリソース種別で分割すると、Secret/Service/Deployment の依存関係と削除順序が複雑になります。App of Apps の子 Application は、単一の原子的なデプロイではありません。

この例は既存の `workloads` Project、宛先 Namespace、および Deployment `my-app` を制御する HPA を前提としています。Git から replicas を省略することを推奨します。必要な場合は、diff/apply の除外対象をそのリソースに限定してください。`ignoreDifferences.name` は Kustomize の prefix/suffix 適用後の最終名に一致させます。`ApplyOutOfSyncOnly` は apply 対象を最適化しますが、sync 頻度は変えません。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: large-app
  namespace: argocd
spec:
  project: workloads
  source:
    repoURL: https://github.com/myorg/gitops.git
    targetRevision: main
    path: overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-production
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - ApplyOutOfSyncOnly=true
    - RespectIgnoreDifferences=true
  ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-app
    namespace: my-app-production
    jsonPointers:
    - /spec/replicas
```

## 障害復旧 {#disaster-recovery}

### バックアップ範囲

`argocd admin export` は Applications/AppProjects/ApplicationSets、4 つのコア ConfigMaps、および選択された Argo CD Secrets をエクスポートします。これは**完全な Namespace バックアップではありません**。cmd-params、Notifications/CMP 設定、個別に管理される TLS/notification Secrets のすべてが含まれると想定しないでください。設定済みの追加 Application/ApplicationSet Namespace も確認してください。

一致する CLI バージョン、検証済みの kubecontext、`age` ツール、承認済みの公開 recipient を使用してください。秘密の identity は別に保管し、復号と復旧をテストしてください。補足スナップショットは、Helm release Secrets を含む可能性のある Namespace 内の全 ConfigMaps/Secrets を暗号化します。復旧時に必要なオブジェクトを選択してください。補足スナップショット全体を無条件に apply しないでください。

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${ARGO_BACKUP_RECIPIENT:?Set the approved age public recipient}"
ARGO_BACKUP_DIR="./argocd-backup-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$ARGO_BACKUP_DIR"
kubectl config current-context
kubectl get configmap argocd-cm -n argocd -o name

argocd admin export -n argocd |
  age --recipient "$ARGO_BACKUP_RECIPIENT" --output "$ARGO_BACKUP_DIR/data.yaml.age.tmp"
mv "$ARGO_BACKUP_DIR/data.yaml.age.tmp" "$ARGO_BACKUP_DIR/data.yaml.age"

# Supplement: all namespace ConfigMaps/Secrets, including custom configuration.
kubectl get configmaps,secrets -n argocd -o yaml |
  age --recipient "$ARGO_BACKUP_RECIPIENT" --output "$ARGO_BACKUP_DIR/namespace-config.yaml.age.tmp"
mv "$ARGO_BACKUP_DIR/namespace-config.yaml.age.tmp" "$ARGO_BACKUP_DIR/namespace-config.yaml.age"
```

pin されたインストールマニフェスト/Helm values、CRD と extension controller、外部 secrets/KMS、SSO、DNS、証明書の復旧手順も保持してください。Application のデータベース/PV には別途バックアップが必要です。RPO/RTO とアクセスポリシーに基づいて、バックアップ頻度と保持期間を選択してください。

### Velero 設定バックアップの代替手段

この Schedule は Velero がインストール済みで、`aws-s3` BackupStorageLocation が利用可能であることを前提としています。スケジュールのタイムゾーン、暗号化、アクセス制御を確認してください。part-of ラベルセレクターではユーザー作成の Applications が除外される可能性があるため、この例にはそのようなフィルターを設定していません。CRD/インストール/PV の復旧は引き続き DR の別の部分です。

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: argocd-config-backup
  namespace: velero
spec:
  schedule: 0 2 * * *
  template:
    includedNamespaces:
    - argocd
    includedResources:
    - applications.argoproj.io
    - applicationsets.argoproj.io
    - appprojects.argoproj.io
    - secrets
    - configmaps
    includeClusterResources: false
    storageLocation: aws-s3
    ttl: 720h0m0s
```

### 段階的な復旧

まず、元のバージョンとインストール方法で**隔離された復旧用インストール**を準備します。プライマリと復旧インスタンスが同じワークロードを同時に変更しないよう、アクティブな manager を 1 つにしてください。デフォルトの StatefulSet レイアウトでは、import の変更を検査する間は Application と ApplicationSet controller を停止します。動的分散の場合は、ワークロードタイプを適合させてください。

```bash
set -euo pipefail
umask 077
: "${ARGO_BACKUP_FILE:?Set the encrypted data.yaml.age path}"
: "${ARGO_BACKUP_IDENTITY:?Set the protected age identity file}"

# Fresh, isolated recovery installation: default StatefulSet controller layout.
kubectl config current-context
kubectl scale statefulset/argocd-application-controller -n argocd --replicas=0
kubectl scale deployment/argocd-applicationset-controller -n argocd --replicas=0

ARGO_RESTORE_DIR="$(mktemp -d)"
trap 'rm -rf "$ARGO_RESTORE_DIR"' EXIT
age --decrypt --identity "$ARGO_BACKUP_IDENTITY" "$ARGO_BACKUP_FILE" \
  > "$ARGO_RESTORE_DIR/data.yaml"
argocd admin import -n argocd --dry-run "$ARGO_RESTORE_DIR/data.yaml"
# Keep controllers stopped while reviewing the recovery copy and destinations.
```

同じ shell で保護された復旧ファイルをレビューしてください。宛先 cluster/Namespace、リポジトリ/cluster 認証情報、削除 finalizer、自動 sync ポリシー、保存された `operation` フィールドを確認します。自動 sync を保留するには、Applications と ApplicationSet templates の両方を更新し、復旧コピーから保留中の operation を削除してください。controller を再起動する前に、Git/Helm source がこれらの保留を元に戻さないか確認してください。

```bash
argocd admin import -n argocd "$ARGO_RESTORE_DIR/data.yaml"
```

必要な補足 ConfigMaps/Secrets と外部依存関係を復旧した後、レビュー済みのインストール設定から controller のレプリカを復元します。個別にデプロイを再開する前に、代表的な Application の diff/health を検査してください。全 Application の sync、import の `--prune`、または Namespace の削除は、デフォルトの復旧手順ではありません。

## アップグレード戦略 {#upgrade-strategies}

### バージョンとインストールのオーナーシップ

この例は、2.x または古い minor からの無条件な移行ではなく、レビュー済みの 3.5.x パッチを 3.5.5 へアップデートすることを対象としています。非本番環境で、間にあるすべての minor/major の移行ノート、テスト済み Kubernetes の組み合わせ、CRD/RBAC/SSO/CMP の変更を確認してください。既存の manifest/Helm/GitOps オーナーを維持してください。この自己管理手順を、EKS managed Argo CD capability に適用しないでください。

```bash
# Example: reviewed 3.5.x patch upgrade to 3.5.5, manifest-managed non-HA install.
kubectl config current-context
argocd version
kubectl apply --server-side -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml
kubectl rollout status deployment/argocd-server -n argocd --timeout=5m
kubectl rollout status deployment/argocd-repo-server -n argocd --timeout=5m
kubectl rollout status statefulset/argocd-application-controller -n argocd --timeout=5m
kubectl rollout status deployment/argocd-applicationset-controller -n argocd --timeout=5m
kubectl rollout status deployment/argocd-notifications-controller -n argocd --timeout=5m
argocd version
argocd app list
```

HA manifest インストールには `manifests/ha/install.yaml` を使用します。カスタムオーバーレイでは、pin された base を更新してレンダリングしてください。server-side apply は大きな CRD を処理します。まず field-ownership の競合を検査してください。意図したオーナーシップ移譲に対してのみ、公式ガイドの `--force-conflicts` を使用します。Pod rollout の成功だけでは、移行、SSO、diff、sync の検証は完了しません。

### Helm 管理インストールの代替手段

レビュー済みの Chart 10.8.4 は Argo CD v3.5.2 をデプロイするため、この Helm パスでは上記で使用した 3.5.5 パッチには到達しません。Argo CD 3.5.5 は Chart 10.10.3 で初めて提供されますが、これはここではレビューしていない Chart minor アップデートです。

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd -f reviewed-values.yaml --dry-run=server --hide-secret
# After reviewing the dry run and the version-specific migration notes:
helm upgrade argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd -f reviewed-values.yaml --wait --timeout 10m
```

`--hide-secret` は dry-run 出力の Secret manifests を抑制します。ほかの場所に埋め込まれた機密値についても確認してください。CRD、永続データ、統合の変更はイメージのロールバックで元に戻らない可能性があるため、テスト済みのバックアップ/復旧計画を保持してください。

### 並行検証の制約

1 つの cluster 上の 2 つの Namespace は、依然として CRD とその他の cluster スコープのリソースを共有します。インストール Namespace だけを変更しても、ClusterRoleBinding の subject は書き換えられません。Kubernetes には `kubectl rename namespace` コマンドはありません。別の cluster で検証し、認証情報、tracking/instance ID、アクティブな controller、トラフィック切り替えを明示的に計画することを推奨します。古い Namespace を削除すると、Application finalizer を介して管理対象ワークロードにカスケードする可能性があります。

## トラブルシューティング {#troubleshooting}

### Sync と差分の検査

```bash
argocd app get my-app
argocd app diff my-app
argocd app history my-app
argocd app resources my-app
kubectl describe application my-app -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100

# Re-check desired state after identifying the cause; this does not apply resources.
argocd app get my-app --refresh
# Invalidates the cached target manifests for this Application; use sparingly.
argocd app get my-app --hard-refresh
```

`--force` は汎用的なトラブルシューティングオプションではなく、リソースを再作成する可能性があります。hard refresh はワークロードを apply またはロールバックしませんが、マニフェストを再生成します。すべての app に対して繰り返し実行することは避けてください。

### リポジトリと Webhook

```bash
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repository
kubectl logs -n argocd deployment/argocd-server --tail=100 | grep -i webhook
```

TLS/SSH の信頼、認証情報のスコープ、DNS/egress、プロバイダーの webhook signature、URL、配信ログを確認してください。Secret 名の一覧取得に、認証情報の値を出力する必要はありません。`argocd repo update --repo-cache-expiration` は有効な cache 設定コマンドではありません。

### OOM と処理遅延

```bash
kubectl top pods -n argocd
kubectl get pods -n argocd
kubectl describe pods -n argocd -l app.kubernetes.io/name=argocd-repo-server
argocd app get my-app -o json |
  jq '.status.operationState | {phase, startedAt, finishedAt}'
```

OOMKilled を CPU throttling、clone-disk pressure、大規模な manifests、Git timeout、API throttling と区別してください。Helm/Git のオーナーを通じて resources/concurrency を調整します。すべての repo-server Pod を削除しても Redis manifest cache はクリアされず、中断/clone の負荷が増えます。

### 追加の確認

```bash
argocd app manifests my-app
argocd app list -o wide
argocd cluster list
argocd cluster get https://my-target-cluster.example.com
kubectl logs -n argocd statefulset/argocd-application-controller --tail=100
kubectl logs -n argocd deployment/argocd-server --tail=100
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
```

レンダリングされた manifests には生成された Secrets が含まれる可能性があります。共有ログに含めないでください。デフォルトの controller は StatefulSet です。動的分散が有効な場合は、実際の Deployment を検査してください。一時的な debug logging は影響を受けるコンポーネントに限定し、その rollout と削除を管理してください。

## EKS のベストプラクティス {#eks-best-practices}

### AWS 認証情報

ServiceAccount の role ARN だけでは、対象 EKS へのアクセスは完了しません。controller/server の EKS authentication、assume-role permissions、対象 EKS の access entries または legacy auth mapping、Kubernetes RBAC を設定してください。S3/OCI/CMP アクセスで必要な場合にのみ、repo-server には別の最小権限 role を付与してください。IRSA OIDC trust または Pod Identity association も必要です。これは image-pull authorization と同じものではありません。実際の宛先と service accounts については、[EKS インストールのセクション](01-installation.md#argocd-on-amazon-eks)に従ってください。

### HTTPS を使用する内部 ALB

これには AWS Load Balancer Controller、VPC への管理者接続、一致する DNS/ACM certificate、制限された security groups、SSO が必要です。certificate ARN と hostname を置き換えてください。backend は `server.insecure=false` で HTTPS のままです。この単一 HTTP target group を介した CLI アクセスでは、`--grpc-web` を使用します。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd
  namespace: argocd
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:123456789012:certificate/REPLACE_WITH_CERTIFICATE_ID
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
spec:
  ingressClassName: alb
  rules:
  - host: argocd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
```

レビュー済みのリージョン WAF Web ACL を、同じリージョンの別の annotation を通じてアタッチしてください。ALB access-log bucket policy とリージョンを確認してください。Shield Advanced のようなサブスクリプション/コスト発生オプションを、デフォルトで有効にしないでください。

### EKS バージョンアップグレード

テスト済みの現在/対象 EKS と Argo CD の組み合わせ、add-on/CRD/node/kubelet の互換性、削除された API を確認してください。EKS control plane は一度に 1 minor ずつアップグレードします。node/add-on の更新は別です。インプレースのバージョンアップデートでは、既存の API endpoint を変更する必要はありません。置換 cluster では endpoint/CA/access の更新が必要です。

自動 sync を保留する場合は、元の設定を記録し、その Git/ApplicationSet オーナーを変更してください。CLI のみで子 Application を変更しても、親によって元に戻される可能性があります。connectivity、diff、sample-sync の検証後は、無条件に automation を有効にするのではなく、元の prune/selfHeal/automated ポリシーを復元してください。

## 本番環境チェックリスト {#production-checklist}

- [ ] デフォルト admin を無効にする前に、SSO/RBAC/TLS と復旧アクセスを確認する
- [ ] secrets を暗号化/外部化し、リポジトリ/cluster 認証情報をスコープする
- [ ] resources、concurrency、cluster sharding が必要かどうかを測定する
- [ ] HA node/anti-affinity/PDB とコンポーネント固有の replicas/leader election を確認する
- [ ] metrics/ServiceMonitor の選択と alert 配信を検証し、JSON logs と Kubernetes audit/events を収集する
- [ ] AppProject の source/destination、sync windows、レビュー済みの promotion PR を強制する
- [ ] 暗号化バックアップの復号、補足設定の復旧、single-manager DR をテストする
- [ ] バージョン固有のアップグレード、トラブルシューティング、設定復元の runbook を維持する

## 参考資料

- [ベストプラクティス](https://argo-cd.readthedocs.io/en/release-3.5/user-guide/best_practices/)
- [高可用性とスケーリング](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/high_availability/)
- [バックアップの実装と範囲](https://github.com/argoproj/argo-cd/blob/v3.5.5/cmd/argocd/commands/admin/backup.go)
- [アップグレードガイド](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/upgrading/overview/)
- [Chart 10.8.4 の values](https://github.com/argoproj/argo-helm/blob/argo-cd-10.8.4/charts/argo-cd/values.yaml)
- [Kustomize のバンドルバージョン](https://github.com/argoproj/argo-cd/blob/v3.5.5/hack/tool-versions.sh)
- [Velero スケジュール](https://velero.io/docs/main/backup-reference/#schedule-a-backup)

## クイズ

[ベストプラクティスのクイズ](../../quizzes/gitops/argocd/09-best-practices-quiz.md)を試してください。
