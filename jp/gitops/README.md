# GitOps

> **最終更新**: October 12, 2026

## 目次
- [GitOps とは？](#what-is-gitops)
- [基本原則](#core-principles)
- [Push モデルと Pull モデル](#push-vs-pull-model)
- [GitOps ツールの概要](#gitops-tools-overview)
- [ツール選定ガイド](#tool-selection-guide)
- [Amazon EKS での GitOps](#gitops-on-amazon-eks)
- [はじめに](#getting-started)

## GitOps とは？ {#what-is-gitops}

GitOps は、バージョン管理、コラボレーション、コンプライアンス、CI/CD などのインフラストラクチャ自動化に関する DevOps のベストプラクティスを、インフラストラクチャ管理に適用する運用フレームワークです。この用語は 2017 年に Weaveworks によって提唱され、その後クラウドネイティブアプリケーションデプロイのための CNCF に認められた方法論となりました。

GitOps の中核では、宣言的なインフラストラクチャおよびアプリケーション設定の唯一の信頼できる情報源として Git リポジトリを使用します。望ましい状態への変更は Git コミットを通じて行われ、自動化プロセスにより実際のシステム状態が宣言された状態と一致することが保証されます。

![開発者が変更を Git に Push し、GitOps エージェントがそれを監視して Kubernetes クラスターに反映する一方、クラスターがエージェントにステータスを報告するアーキテクチャ図。](../.gitbook/assets/en-gitops-readme-10.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-10.html)

### 歴史と進化

| マイルストーン | 検証済みのプロジェクト履歴 |
|---|---|
| Flux | CNCF Sandbox: 2019 年 7 月、Incubating: 2021 年 3 月、Graduated: 2022 年 11 月 30 日 |
| Argo project | CNCF Incubating: 2020 年 3 月、Graduated: 2022 年 12 月 6 日 |
| OpenGitOps | バージョニングされた原則を公開。リリース済みドキュメントと作業中の main ブランチを区別 |

### CNCF OpenGitOps の定義

OpenGitOps プロジェクトは、4 つの原則を通じて GitOps を定義しています。

1. **宣言的**: GitOps で管理されるシステムは、望ましい状態が宣言的に表現されていなければならない
2. **バージョン管理され、不変である**: 望ましい状態は、不変性とバージョニングを強制し、完全なバージョン履歴を保持する方法で保存される
3. **自動的に Pull される**: ソフトウェアエージェントが、ソースから望ましい状態の宣言を自動的に Pull する
4. **継続的に調整される**: ソフトウェアエージェントが実際のシステム状態を継続的に監視し、望ましい状態の適用を試みる

## 基本原則 {#core-principles}

Git 履歴は望ましい設定を記録します。Git revert では、データベースマイグレーション、削除されたデータ、または外部状態は復元されません。Argo CD の automated sync、prune、selfHeal は別個の設定です。GitOps は、調整を試みる制御ループを表します。

### 宣言的設定

インフラストラクチャ、アプリケーション、ポリシー、設定など、すべてをコードとして定義します。これにより、次のことが可能になります。

- **再現性**: バージョン管理された設定に利用可能なアーティファクト、シークレット、データを組み合わせることで再作成が可能
- **監査可能性**: 保持された設定履歴。ランタイム/API の監査ログは引き続き収集が必要
- **一貫性**: 明示的でレビュー済みの環境差分を持つ共有ベース

```yaml
# Example: Declarative application state
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
    version: v1.2.3
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: myregistry/web-app:v1.2.3
        ports:
        - containerPort: 8080
```

### 唯一の信頼できる情報源としての Git

Git リポジトリには、システム全体の望ましい状態が保存されます。

- **アプリケーション設定**
- **インフラストラクチャ定義**
- **セキュリティポリシー**
- **環境固有の設定**

### 自動調整

GitOps エージェントは継続的に次を行います。

1. Git リポジトリの変更を監視する
2. 望ましい状態と実際の状態を比較する
3. システムをコンプライアンスに準拠させるために変更を適用する
4. ステータスとドリフトを報告する

### 自己修復システム

調整の試行は、sync/self-heal ポリシー、権限、およびヘルスに依存します。たとえば、Argo CD の automated sync と selfHeal には設定が必要です。インストールだけで、すべての手動変更を revert したり、失われたデータを復旧したりすることはありません。

## Push モデルと Pull モデル {#push-vs-pull-model}

従来の Push デプロイと Pull ベースの GitOps を比較します。CI のみの `kubectl apply` パイプラインは、それ自体では OpenGitOps の自動 Pull および継続的調整の原則を満たしません。

![パイプラインが変更をクラスターに直接適用する従来の Push ベース CI/CD と、エージェントが Git を監視して自ら変更を適用する GitOps Pull モデルを対比するフローチャート。](../.gitbook/assets/en-gitops-readme-11.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-11.html)

### Push モデル

従来の Push モデルでは、次のとおりです。
- CI/CD パイプラインがクラスターに直接アクセスする
- 認証情報が CI システムに保存される
- クラスターの外部から変更が Push される

**欠点:**
- CI システムにクラスターの認証情報が必要
- 誰が変更したかの監査がより困難
- 自動ドリフト検出がない

### Pull モデル（推奨）

GitOps Pull モデルでは、次のとおりです。
- エージェントが対象クラスターまたは別の管理クラスターで実行される
- エージェントが Git から変更を Pull する
- 管理クラスターのエージェントにも、リモートターゲットへの認可されたネットワーク/API アクセスが必要

**利点:**
- CI 内の対象クラスター認証情報を減らせる可能性がある。ただし、エージェントは引き続きソース/API アクセス権を保持する
- Git に完全な監査証跡がある
- 自動ドリフト検出および修正
- ファイアウォールの背後でも動作する

## GitOps ツールの概要 {#gitops-tools-overview}

### ArgoCD

[ArgoCD](argocd/README.md) は、Kubernetes 向けの宣言的 GitOps 継続的デリバリーツールです。

**主な機能:**
- 可視化のための Web UI
- マルチクラスター対応
- SSO 統合
- Rollback 機能
- ヘルスステータス監視
- フリート管理のための ApplicationSet

**最適な対象:** ビジュアル管理、マルチクラスターのデプロイ、エンタープライズ機能を求めるチーム

### FluxCD

FluxCD は、オープンで拡張可能な Kubernetes 向け継続的デリバリーソリューションのセットです。

**主な機能:**
- 軽量かつモジュール型
- ネイティブの Helm および Kustomize 対応
- イメージ自動化
- マルチテナンシー
- Notification controller

**最適な対象:** CLI 優先の軽量ソリューション、イメージ自動化ワークフローを好むチーム

### Jenkins X / JayeX

Jenkins X / JayeX は、Kubernetes 上のクラウドネイティブアプリケーション向けに CI/CD を提供します。

**主な機能:**
- 自動化された CI/CD パイプライン
- プレビュー環境
- GitOps プロモーション
- Tekton ベースのパイプライン

**評価対象:** 統合された CI/CD とプレビュー環境のワークフロー。JayeX/Jenkins X / JayeX は、単に GitOps を有効にした Jenkins ではありません

### 比較マトリクス

| 要件 | Argo CD | Flux |
|---|---|---|
| デフォルト UI | 組み込みの Web UI と CLI | コア controller/CLI、オプションのエコシステム UI |
| Helm の動作 | helm template、Argo CD がリソースライフサイクルを管理 | Helm Controller が Helm release のライフサイクルを管理 |
| イメージ更新 | 別個の Argo CD Image Updater | オプションの Image Reflector/Automation controller |
| マルチテナンシー | AppProjects、RBAC、destination/source 制限 | Kubernetes RBAC、ServiceAccount impersonation、クロス名前空間制限 |
| OCI ソース | 汎用 OCI/Helm ソース、layer/media type を検証 | OCIRepository/Helm ソース、検証/layer 設定を検証 |
| キャパシティ | アプリケーション/クラスター数と調整負荷を測定 | インストール済み controller、ソース、調整負荷を測定 |

## ツール選定ガイド {#tool-selection-guide}

### 次の場合は ArgoCD を選択:

- 運用のためのビジュアルダッシュボードが必要
- マルチクラスター管理が必要
- エンタープライズ SSO/RBAC が重要
- チームが UI ベースのワークフローを好む
- フリート管理のために ApplicationSet が必要

### 次の場合は FluxCD を選択:

- 軽量でモジュール型のアーキテクチャを好む
- イメージ自動化が主要な要件である
- CLI 優先のワークフローが望ましい
- リソース制約が懸念事項である
- Helm controller との緊密な統合が必要

### 意思決定フレームワーク

この図は排他的な機能ではなく、選定に関する質問を示しています。表および代表的な試行とともに、現在の機能、認可境界、運用コストを比較してください。

![Web UI のニーズ、マルチクラスターの範囲、RBAC 要件、イメージ自動化の優先度、軽量なフットプリントの優先度に基づき、ArgoCD、FluxCD、またはいずれかのツールを選ぶための決定木。](../.gitbook/assets/en-gitops-readme-12.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-12.html)

## Amazon EKS での GitOps {#gitops-on-amazon-eks}

### EKS 固有の考慮事項

Amazon EKS で GitOps を実装する場合:

#### IAM 統合

ServiceAccount アノテーションだけでは IAM アクセスは確立されません。IRSA の OIDC provider/trust policy/SDK サポート、または EKS Pod Identity association を設定してください。AWS API の権限と対象 Kubernetes API の認証/RBAC は別個のものです。

セキュアな AWS API アクセスには IAM Roles for Service Accounts (IRSA) を使用します。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitops-controller
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/GitOpsRole
```

#### マルチアカウントアーキテクチャ

![管理アカウントの ArgoCD が Git から読み取り、クロスアカウント接続を介して別個の開発、ステージング、本番アカウントの EKS クラスターを調整するアーキテクチャ図。](../.gitbook/assets/en-gitops-readme-13.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-readme-13.html)

#### AWS サービス統合

GitOps は次を通じて AWS リソースを管理できます。

- **AWS Controllers for Kubernetes (ACK)**: AWS サービス用のネイティブ K8s CRD
- **Crossplane**: マルチクラウドリソースのプロビジョニング
- **Terraform Controller**: GitOps 経由の Terraform state 管理

### 推奨アーキテクチャ

```
├── infrastructure/
│   ├── base/                    # Shared infrastructure
│   │   ├── vpc/
│   │   ├── eks/
│   │   └── iam/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── production/
├── applications/
│   ├── base/                    # Application base configs
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── production/
└── platform/
    ├── argocd/                  # GitOps tooling
    ├── monitoring/              # Observability stack
    └── security/                # Security policies
```

## はじめに {#getting-started}

### ArgoCD クイックスタート

互換性のある Kubernetes バージョン、空の専用 namespace、および CRD/RBAC のクラスター権限を使用してください。この非 HA インストール例では Argo CD 3.5.4 を固定しています。本番環境の前に完全な[インストールガイド](argocd/01-installation.md)を確認してください。初期 admin 認証情報は変更し、bootstrap Secret は使用後に削除する必要があります。

1. **ArgoCD をインストール:**
   ```bash
   kubectl create namespace argocd
   kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml
   ```

2. **UI にアクセス:**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **初期パスワードを取得:**
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

詳細な ArgoCD セットアップについては、[ArgoCD ドキュメント](argocd/README.md)を参照してください。

### FluxCD クイックスタート

`GITHUB_ORG`/`GITOPS_REPOSITORY`、ドキュメント化された GitHub 認証、および Kubernetes 権限を準備してください。Bootstrap は Git に書き込み、クラスター controller をインストールします。個人所有者の場合にのみ `--personal` を追加し、必要に応じてオプションのイメージ自動化 controller を明示的に選択してください。

1. **Flux CLI をインストール:**
   ```bash
   curl --fail --location https://fluxcd.io/install.sh -o install-flux.sh
   # Review the script and select a supported version before running it.
   sudo bash install-flux.sh
   ```

2. **Flux を Bootstrap:**
   ```bash
   flux bootstrap github \
     --owner="$GITHUB_ORG" \
     --repository="$GITOPS_REPOSITORY" \
     --path=clusters/my-cluster
   ```

詳細な FluxCD セットアップについては、FluxCD ドキュメントを参照してください。

## セクションナビゲーション

| トピック | 説明 |
|-------|-------------|
| [ArgoCD](argocd/README.md) | インストール、アプリケーション、sync 戦略などを含む完全な ArgoCD ガイド |
| [FluxCD](02-fluxcd.md) | FluxCD のセットアップ、source controller、イメージ自動化 |

## 参考資料

- [CNCF GitOps Working Group](https://github.com/cncf/tag-app-delivery/tree/main/gitops-wg)
- [OpenGitOps Project](https://opengitops.dev/)
- [GitOps Principles](https://www.gitops.tech/)

## クイズ

学んだ内容を確認するには、次のクイズに挑戦してください。
- [ArgoCD クイズ](../quizzes/gitops/01-argocd-quiz.md)
- [FluxCD クイズ](../quizzes/gitops/02-fluxcd-quiz.md)
- [GitOps 比較クイズ](../quizzes/gitops/03-gitops-comparison-quiz.md)

### 参考ソース

- [OpenGitOps の原則](https://github.com/open-gitops/documents/blob/v1.0.0/PRINCIPLES.md)
- [Argo project の成熟度](https://www.cncf.io/projects/argo/)
- [Flux project の成熟度](https://www.cncf.io/projects/flux/)
- [Argo CD OCI ソース](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/)
- [Argo CD automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Flux マルチテナンシー](https://fluxcd.io/flux/installation/configuration/multitenancy/)
- [Flux エコシステム](https://fluxcd.io/ecosystem/)
- [JayeX project](https://jayex.io/v3/about/)
