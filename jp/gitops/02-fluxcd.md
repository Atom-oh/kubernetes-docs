# FluxCD

> **レビュー基準**: 自己管理型 Flux 2.9.5。リリースノートのレビュー後にパッチ版 2.9.6 へ更新（例は再実行していません）
> **最終更新**: 2026年10月12日

FluxCD は、オープンかつ拡張可能な Kubernetes 向け継続的デリバリーおよびプログレッシブデリバリーのソリューション群です。FluxCD は 2022 年 11 月に CNCF を卒業し、クラウドネイティブエコシステムで最も成熟した GitOps ツールの一つとなりました。

この章では**自己管理型 Flux 2.9.6**を対象とします。CLI の事前チェックには少なくとも Kubernetes 1.33 が必要です。ディストリビューションの実際のサポート期間も確認してください。2.6 以前からアップグレードする前に、2.7+ API の移行手順を確認してください。以下の OCIRepository/Bucket/image API では v1 を使用します。Notification Provider/Alert は引き続き v1beta3 です。

例では、プラットフォーム所有で信頼済みの `flux-system` リソースを使用しています。繰り返し出現する Kustomization は、置き換えの連続ではなく、組み合わせるための代替例または断片です。実際のリポジトリ URL、パス、namespace、Secret を準備してください。テナントでの利用には、専用 namespace、`spec.serviceAccountName` を通じた RBAC/なりすまし、およびクロス namespace 参照の制限が必要です。

## はじめに

FluxCD は、Kubernetes クラスターの望ましい状態を定義する信頼できる情報源として Git リポジトリを使用し、GitOps の原則を実装します。ソースの変更とドリフトを定期的にリコンサイルします。認可、可用性、ヘルスチェックの失敗により、収束が遅延または阻害されることがあります。

### 主な機能

- **GitOps Native**: GitOps ワークフロー向けにゼロから構築
- **Multi-tenancy**: 分離された設定で複数チームをサポート
- **Multi-cluster**: 単一の Git リポジトリから複数クラスターを管理
- **Extensible**: 専用 Controller によるモジュラーアーキテクチャ
- **Kubernetes Native**: 設定に Custom Resource Definition（CRD）を使用

## アーキテクチャの概要

FluxCD は、GitOps ワークフローを実装するために連携して動作する専用 Controller 群で構成されます。

![Flux の source、apply/release、notification Controller。任意の image-reflector と image-automation Controller は、レジストリスキャンと Git 更新を分離します。](../.gitbook/assets/en-gitops-02-fluxcd-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-02-fluxcd-0.html)

## コアコンポーネント

デフォルトのインストールには source/kustomize/helm/notification Controller が含まれます。イメージ自動化には、さらに**image-reflector-controller と image-automation-controller**が必要です。任意の source-watcher は、ArtifactGenerator などの API を通じてソース構成を提供します。

| Secret | 必要な内容 |
|---|---|
| git-credentials | HTTPS Git のユーザー名/パスワードまたは対応する認証情報。イメージ更新にはリポジトリへの書き込みアクセスも必要 |
| registry-credentials | プライベート ImageRepository 用の kubernetes.io/dockerconfigjson Secret |
| slack-bot-token | `token` キー配下の Slack Bot OAuth トークン |
| github-webhook-token | GitHub webhook と共有する `token` |

参照する ConfigMap/Secret は、Flux リソースと同じ namespace に準備してください。平文の Git ファイルではなく、保護されたシークレット管理を介して実際の値を指定してください。

### Source Controller

Source Controller は外部ソースからアーティファクトを取得します。複数のソースタイプをサポートします。

#### GitRepository

Git リポジトリを追跡し、他の Controller から使用可能にします。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/my-org/my-app
  ref:
    branch: main
  secretRef:
    name: git-credentials
```

#### HelmRepository

Helm Chart リポジトリを追跡します。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 1h
  url: https://stefanprodan.github.io/podinfo
```

#### OCIRepository

これは、ワークロードのコンテナイメージではなく、**Flux 向けの manifest/Helm コンテンツを含む OCI アーティファクト**を示します。まず互換性のあるアーティファクトを公開し、タグ/ダイジェストを固定してください。

OCI 準拠レジストリ（コンテナレジストリを含む）に保存されたアーティファクトを追跡します。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: my-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/my-org/my-artifacts
  ref:
    tag: v1.0.0
```

#### Bucket

AWS の例では、source-controller の IRSA/Pod Identity など、構成済みのデフォルト認証チェーンを前提としています。以下で説明する EKS 認証と Bucket 権限を準備してください。

S3 互換ストレージに保存されたアーティファクトを追跡します。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: my-bucket
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-bucket
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

### Kustomize Controller

Kustomize Controller は、ソースから Kustomize overlay とプレーンな Kubernetes manifest を適用します。

#### Kustomization CRD

`targetNamespace` は namespace を作成しません。事前に作成するか、その Namespace manifest を Kustomization に含めてください。`prune: true` はソースから削除された以前に管理されていたリソースを削除できるため、ソースの境界と削除ポリシーをレビューしてください。

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: production
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy/production
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: my-app
    namespace: production
  timeout: 2m
```

#### 変数の置換

`substituteFrom` エントリは、前にあるエントリを上書きします。インラインの `substitute` が優先されます。Secret の置換値はレンダリング済み manifest に含まれるため、その出力とアクセスを制御してください。Flux 2.9.6 にバンドルされる kustomize-controller 1.9.6 では、デフォルトで `StrictPostBuildSubstitutions` が有効となり、デフォルト値のない変数が欠けていると失敗します。既存のデプロイメントでこのゲートが明示的に無効化されていないか確認してください。数値フィールドは、引き続き Kubernetes の数値としてレンダリングされる必要があります。

FluxCD は `postBuild` を使用した変数置換をサポートします。

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./deploy
  postBuild:
    substitute:
      ENVIRONMENT: production
      REPLICAS: '3'
    substituteFrom:
    - kind: ConfigMap
      name: cluster-config
    - kind: Secret
      name: cluster-secrets
  prune: true
  targetNamespace: production
```

#### ヘルスチェック

デプロイ済みリソースのカスタムヘルスチェックを定義します。

```yaml
spec:
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: frontend
    namespace: production
  - apiVersion: apps/v1
    kind: StatefulSet
    name: database
    namespace: production
  timeout: 5m
```

### Helm Controller

Helm Controller は Helm Chart リリースを宣言的に管理します。

#### HelmRelease CRD

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: podinfo
      version: 6.15.0
      sourceRef:
        kind: HelmRepository
        name: podinfo
        namespace: flux-system
  targetNamespace: web
  install:
    createNamespace: true
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    replicaCount: 2
    service:
      type: ClusterIP
  releaseName: podinfo
```

#### Values のオーバーライド

後にある valuesFrom エントリは先にあるエントリを上書きし、その後にインライン values が適用されます。targetPath 参照はインライン values さえ上書きできるため、そのケースを明示的に扱ってください。

複数のソースから Helm values をオーバーライドします。

```yaml
spec:
  valuesFrom:
  - kind: ConfigMap
    name: podinfo-values
    valuesKey: values.yaml
  - kind: Secret
    name: podinfo-secrets
    valuesKey: credentials.yaml
  values:
    replicaCount: 3
```

#### ドリフト検出

HPA など別の Controller がレプリカを所有する場合にのみ、それらを無視してください。不必要な無視ルールは手動によるドリフトを隠す可能性があります。

デプロイ済みリソースが望ましい状態と一致するよう、ドリフト検出を有効にします。

```yaml
spec:
  driftDetection:
    mode: enabled
    ignore:
    - paths:
      - /spec/replicas
      target:
        kind: Deployment
```

### Notification Controller

Notification Controller はインバウンドおよびアウトバウンドイベントを処理します。

#### Provider

この例では Slack Bot API を使用します。chat:write を構成し、bot を送信先チャンネルに招待して、channel を実際の ID に置き換えてください。Incoming Webhook URL は Bot トークンではありません。

アラート用の通知 Provider を構成します。

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: C0123456789
  secretRef:
    name: slack-bot-token
  address: https://slack.com/api/chat.postMessage
```

サポートされる Provider には以下が含まれます。
- Slack
- Microsoft Teams Workflows (`msteams`)
- Discord
- PagerDuty
- Opsgenie（既存顧客向け。2027-04-05 にサービス終了予定）
- GitHub
- GitLab
- Grafana
- 汎用 webhook

#### Alert

FluxCD イベントのアラートを定義します。

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: on-call
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: error
  eventSources:
  - kind: GitRepository
    name: '*'
  - kind: Kustomization
    name: '*'
  - kind: HelmRelease
    name: '*'
  eventMetadata:
    summary: Cluster alerts
```

#### Receiver（Webhook）

Receiver を作成してもインターネットエンドポイントは公開されません。webhook-receiver Service に対してレビュー済みの TLS ingress と status.webhookPath を組み合わせ、GitHub に同じトークンを設定し、type: github の署名検証を維持してください。

外部イベント用の webhook を構成します。

```yaml
apiVersion: notification.toolkit.fluxcd.io/v1
kind: Receiver
metadata:
  name: github-receiver
  namespace: flux-system
spec:
  type: github
  events:
  - ping
  - push
  secretRef:
    name: github-webhook-token
  resources:
  - kind: GitRepository
    name: my-app
```

### イメージ自動化

FluxCD は Git リポジトリ内のコンテナイメージタグを自動更新できます。

#### ImageRepository

image-reflector-controller はタグをスキャンし、ImagePolicy を評価します。イメージのビルド、脆弱性のスキャン、ワークロードのイメージ pull は行いません。

新しいタグをコンテナレジストリからスキャンします。

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  image: ghcr.io/my-org/my-app
  interval: 1m
  secretRef:
    name: registry-credentials
```

#### ImagePolicy

イメージタグを選択するポリシーを定義します。

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: my-app
  namespace: flux-system
  labels:
    app: my-app
spec:
  imageRepositoryRef:
    name: my-app
  policy:
    semver:
      range: '>=1.0.0 <2.0.0'
  digestReflectionPolicy: IfNotPresent
```

#### ImageUpdateAutomation

YAML フィールドを更新するにはポリシーマーカーが必要です。IfNotPresent は選択されたタグのダイジェストを反映します。これは署名/脆弱性の検証ではありません。この自動化は専用の flux/image-updates ブランチへ push します。main への PR 作成/承認は、Flux が自動提供するものではなく、別の CI/運用者ワークフローです。このブランチは自動化用に確保し、その Git 認証情報に書き込みアクセスを付与してください。

```yaml
# Deployment Pod-template fragment; the policy marker is required.
spec:
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/my-org/my-app:1.0.0 # {"$imagepolicy": "flux-system:my-app"}
```

新しいイメージが検出されたときに Git commit を自動化します。

```yaml
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageUpdateAutomation
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: my-app
  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@my-org.com
        name: Flux
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $changes := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
          {{- range $_, $change := $changes }}
          {{ $change.OldValue }} -> {{ $change.NewValue }}
          {{- end }}
        {{ end -}}
    push:
      branch: flux/image-updates
  update:
    path: ./deploy
    strategy: Setters
  policySelector:
    matchLabels:
      app: my-app
```

## インストール

### Flux CLI の使用

検証済み Linux amd64/arm64 リリースのインストール例です。他のオペレーティングシステムについては、[公式 CLI インストールガイド](https://fluxcd.io/flux/installation/#install-the-flux-cli)に従い、インストール済みバージョンを確認してください。

```bash
set -euo pipefail
FLUX_VERSION=2.9.6
case "$(uname -m)" in
  x86_64)
    flux_arch=amd64
    flux_sha=b853df82adfd7736f580692f9f734473d571606307139f8fd20c2a80dd1ff473 ;;
  aarch64|arm64)
    flux_arch=arm64
    flux_sha=f3e159af616ec0b9bd0a405c2185cf09d06b74652c1de3c7f377e8166826651a ;;
  *) echo "Use the official installer for this architecture" >&2; exit 1 ;;
esac
flux_tmp="$(mktemp -d)"
trap 'rm -rf "$flux_tmp"' EXIT
curl -fsSL -o "$flux_tmp/flux.tar.gz" \
  "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/flux_${FLUX_VERSION}_linux_${flux_arch}.tar.gz"
printf '%s  %s\n' "$flux_sha" "$flux_tmp/flux.tar.gz" | sha256sum -c -
tar -xzf "$flux_tmp/flux.tar.gz" -C "$flux_tmp" flux
mkdir -p "$HOME/.local/bin"
install -m 0755 "$flux_tmp/flux" "$HOME/.local/bin/flux"
export PATH="$HOME/.local/bin:$PATH"
flux --version
```

### Bootstrap

Bootstrap は設定を Git に書き込み、クラスターに Controller をインストールします。kubecontext とリポジトリの認可を確認し、GitHub または GitLab のいずれかを選んでください。my-org は組織/グループを表します。ユーザーアカウントの場合にのみ --personal を使用してください。トークンは環境変数で安全に指定してください。これらの例には image automation Controller が含まれます。Bootstrap リポジトリ自体を自動化する場合は、その deploy key に対して書き込みアクセスを別途有効にしてください。

```bash
kubectl config current-context
flux check --pre

# Alternative A: GitHub organization; provide authorized GITHUB_TOKEN securely.
flux bootstrap github \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller

# Alternative B: GitLab group; provide authorized GITLAB_TOKEN securely.
flux bootstrap gitlab \
  --owner=my-org \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --version=v2.9.6 \
  --components-extra=image-reflector-controller,image-automation-controller
```

### インストールの検証

```bash
# Check Flux components
flux check --components-extra=image-reflector-controller,image-automation-controller

# Get all Flux resources
flux get all

# Watch for changes
flux get kustomizations --watch
```

## Flux によるマルチクラスター

FluxCD は単一のリポジトリから複数クラスターを管理することをサポートします。

### Fleet リポジトリ構成

```
fleet-infra/
├── clusters/
│   ├── production/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   ├── staging/
│   │   ├── flux-system/
│   │   │   ├── gotk-components.yaml
│   │   │   ├── gotk-sync.yaml
│   │   │   └── kustomization.yaml
│   │   └── apps.yaml
│   └── development/
│       ├── flux-system/
│       │   └── gotk-sync.yaml
│       └── apps.yaml
├── infrastructure/
│   ├── base/
│   │   ├── cert-manager/
│   │   ├── envoy-gateway/
│   │   └── monitoring/
│   └── overlays/
│       ├── production/
│       └── staging/
└── apps/
    ├── base/
    │   ├── frontend/
    │   └── backend/
    └── overlays/
        ├── production/
        └── staging/
```

### 単一 Control Plane における Kustomization の依存関係

`dependsOn` は、この Flux Control Plane が観測する Kustomization オブジェクトの Ready 条件を待機します。これはクロスクラスターのバリアではなく、単一クラスター内の 2 つのオブジェクトです。`wait: true` により、インフラストラクチャの準備完了にはワークロードのヘルスが含まれます。デフォルトの Bootstrap GitRepository は `flux-system` という名前であり、この例では `sourceRef` として使用しています。

それぞれの独立したクラスターを、それぞれの context/path で Bootstrap するか、リモート `kubeConfig` と認可を明示的に構成してください。Flux 2.9.5 以降、Secret kubeconfig は `certificate-authority`、`tokenFile`、`client-certificate`、`client-key` 内のローカルファイル参照を拒否します。必要な認証情報/証明書は保護されたインラインデータとして指定するか、サポートされるワークロードアイデンティティ設定を使用してください。

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1h
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./infrastructure/overlays/production
  prune: true
  wait: true
  timeout: 5m
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  dependsOn:
  - name: infrastructure
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./apps/overlays/production
  prune: true
```

## Amazon EKS 上の FluxCD

### Controller ごとの AWS 認証

この例では**Controller レベルの IRSA**を使用します。まず、EKS OIDC Provider、正確な ServiceAccount subject と sts.amazonaws.com audience に対するロール信頼、およびリソース権限を構成してください。role-ARN アノテーションで信頼やポリシーが作成されるわけではありません。代わりに EKS Pod Identity を使用する場合は、その関連付け/agent のセットアップが必要です。IRSA アノテーションでは構成されません。

| Controller | AWS アクセスの目的 |
|---|---|
| source-controller | OCI/Helm アーティファクト、S3 Bucket、CodeCommit Git ソース |
| image-reflector-controller | ECR ワークロードイメージのタグ/ダイジェストのスキャン |
| image-automation-controller | CodeCommit を直接使用する場合の Git clone/push 権限 |
| kustomize-controller | SOPS KMS 復号またはリモート EKS リコンサイル |
| helm-controller | リモート EKS 上の Helm リリースのリコンサイル |

source-controller にロールを付与しても、他のすべての Controller が認証されるわけではありません。マルチテナンシーでは、サポートされるオブジェクトレベルのワークロードアイデンティティとその feature gate、ServiceAccount、RBAC 設定を別途レビューしてください。

このパッチを Bootstrap パス配下の flux-system/kustomization.yaml にマージし、既存の patches/resources を維持したまま Git で管理してください。ServiceAccount の変更のみでは、既存の Pod に IRSA は再注入されません。リコンサイル後に対象 Controller をロールアウトしてください。

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- gotk-components.yaml
- gotk-sync.yaml
patches:
- target:
    kind: ServiceAccount
    name: source-controller
  patch: |
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: source-controller
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/flux-source-controller
```

```bash
kubectl rollout restart deployment/source-controller -n flux-system
kubectl rollout status deployment/source-controller -n flux-system --timeout=180s
```

### ECR 内の GitOps アーティファクト

この source-controller 権限は、専用の gitops-artifacts リポジトリを読み取ります。GetAuthorizationToken はリポジトリ ARN のスコープ指定をサポートしないため、そのリソースは requested-region 条件付きの * です。コンテンツ読み取りアクションはリポジトリ ARN にスコープされます。アカウント/リージョン/リポジトリの値を置き換えてください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/gitops-artifacts"
    }
  ]
}
```

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: gitops-artifacts
  namespace: flux-system
spec:
  interval: 5m
  url: oci://123456789012.dkr.ecr.us-east-1.amazonaws.com/gitops-artifacts
  ref:
    tag: v1.0.0
  provider: aws
```

OCIRepository は Flux 用の manifest/Helm アーティファクトを読み取ります。ワークロードのコンテナイメージをデプロイしたり、EKS node/Fargate のイメージ pull 権限を付与したりするものではありません。ECR ImageRepository のスキャンには、個別の image-reflector-controller 認証とレジストリ読み取り権限が必要です。

### S3 Bucket ソース

専用のアーティファクト Bucket を使用し、以下の権限を Controller ロールに追加してください。カスタマー管理 KMS 暗号化には、追加でキーポリシーと kms:Decrypt が必要です。クロスアカウントアクセスには Bucket ポリシーも必要です。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: Bucket
metadata:
  name: artifacts
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-artifacts
  endpoint: s3.us-east-1.amazonaws.com
  region: us-east-1
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-flux-artifacts"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-flux-artifacts/*"
    }
  ]
}
```

### CodeCommit HTTPS ソース

これは**既存の Flux インストール向けのソース統合**であり、Bootstrap または IAM 認証情報の作成手順ではありません。source-controller 1.9.6（Flux 2.9.6 にバンドル）は、CodeCommit HTTPS エンドポイントおよび IRSA/Pod Identity を伴う provider: aws をサポートします。読み取り権限をそのロールに追加し、この GitRepository を目的の Kustomization から参照してください。

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: codecommit-manifests
  namespace: flux-system
spec:
  interval: 1m
  provider: aws
  url: https://git-codecommit.us-east-1.amazonaws.com/v1/repos/fleet-infra
  ref:
    branch: main
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "codecommit:GitPull",
      "Resource": "arn:aws:codecommit:us-east-1:123456789012:fleet-infra"
    }
  ]
}
```

ImageUpdateAutomation が CodeCommit に push する場合、その Controller/オブジェクトのアイデンティティにも GitPull/GitPush 権限と専用のブランチ/PR ポリシーが必要です。SSH には、ユーザー名として IAM に登録された SSH キー ID と対応する秘密鍵が必要です。ssh:// URL または CLI のキー生成オプションで IAM キーが登録されるわけではありません。

## ベストプラクティス

### リポジトリ構成

- 小規模チームには monorepo を使用する
- 大規模組織ではインフラストラクチャとアプリケーションに別々のリポジトリを使用する
- Kustomize による環境固有の overlay を実装する

### セキュリティ

- SOPS/Sealed Secrets または External Secrets Operator で Secret/key のライフサイクルを管理する
- テナント namespace、spec.serviceAccountName ベースの RBAC/なりすまし、クロス namespace 参照の制限を構成する
- Receiver の webhook 検証を有効にする

### モニタリング

- リコンサイルの失敗に対するアラートを構成する
- メトリクスを Prometheus にエクスポートする
- Flux コンポーネント用のダッシュボードを設定する

### パフォーマンス

- 変更頻度に基づいてリコンサイル間隔を調整する
- Helm リポジトリにキャッシュを使用する
- 適切な timeout でヘルスチェックを実装する

## 参考資料

- [Flux 2.9.5 リリースおよび kubeconfig 強化に関する通知](https://github.com/fluxcd/flux2/releases/tag/v2.9.5)
- [Flux 2.9.6 リリースノート](https://github.com/fluxcd/flux2/releases/tag/v2.9.6)
- [Flux のインストール](https://fluxcd.io/flux/installation/)
- [AWS 統合](https://fluxcd.io/flux/integrations/aws/)
- [GitRepository v1](https://github.com/fluxcd/source-controller/blob/v1.9.5/docs/spec/v1/gitrepositories.md)
- [ImageUpdateAutomation v1](https://github.com/fluxcd/image-automation-controller/blob/v1.2.5/docs/spec/v1/imageupdateautomations.md)
- [Kustomization v1](https://github.com/fluxcd/kustomize-controller/blob/v1.9.5/docs/spec/v1/kustomizations.md)
- [Notification Provider](https://github.com/fluxcd/notification-controller/blob/v1.9.4/docs/spec/v1beta3/providers.md)
- [Opsgenie のライフサイクル](https://www.atlassian.com/software/opsgenie)

## クイズ

学習内容を確認するには、[FluxCD クイズ](../quizzes/gitops/02-fluxcd-quiz.md)に挑戦してください。
