# ArgoCD

> **レビュー基準**: Argo CD 3.5.2、Argo Rollouts 1.10.0。リリースノートのレビュー後、Argo CD マニフェストのピンをパッチ 3.5.4 に更新しました（例は再実行していません）
> **最終更新**: October 12, 2026

## 目次
- [ArgoCD とは？](#what-is-argocd)
- [主な利点](#key-benefits)
- [アーキテクチャの概要](#architecture-overview)
- [コアコンセプト](#core-concepts)
- [サブガイドのナビゲーション](#sub-guide-navigation)
- [クイックスタート](#quick-start)
- [バージョン互換性](#version-compatibility)

## ArgoCD とは？

ArgoCD は、Kubernetes 向けの宣言的な GitOps 継続的デリバリーツールです。Git リポジトリで定義された望ましい状態をクラスター内の実際の状態と同期することで、Kubernetes クラスターへのアプリケーションのデプロイを自動化します。

Argo CD は、CNCF を卒業した Argo プロジェクトの一部です。採用実績だけで、特定のセキュリティまたは可用性要件への適合性が確立されるわけではありません。

![ArgoCD のコントロールプレーンが Repo Server を介して Git、Helm、OCI ソースからマニフェストを取得し、Application Controller がそれらを管理対象の Kubernetes クラスターへリコンサイルおよび同期する一方、ユーザーは web UI、CLI、または gRPC API を介して API Server にアクセスする様子を示すアーキテクチャ図。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主な利点

### GitOps ネイティブ

- **信頼できる唯一の情報源としての Git**: すべてのアプリケーション設定を Git に保存
- **宣言的デプロイ**: 望ましい状態を定義すれば、残りは ArgoCD が処理
- **監査証跡**: Git コミットを通じたすべての変更の完全な履歴
- **ロールバック**: 保持された設定リビジョンを再デプロイ。データベース／外部状態の復旧は別途必要

### マルチクラスター管理

- **一元的な制御**: 単一の ArgoCD インスタンスから数百のクラスターを管理
- **ApplicationSet**: テンプレートベースのマルチクラスターデプロイ
- **Cluster Generator**: ラベルに基づく動的なクラスターターゲティング

### エンタープライズ対応

- **RBAC**: きめ細かなロールベースアクセス制御
- **SSO 統合**: 他のアイデンティティプロバイダー向けの直接 OIDC またはサポート対象 Dex コネクター
- **マルチテナンシー**: Project ベースの分離
- **高可用性**: 本番環境対応の HA デプロイ

### 開発者エクスペリエンス

- **Web UI**: 視覚的なアプリケーション管理と監視
- **CLI**: フル機能のコマンドラインインターフェース
- **通知**: Slack、Teams、email、webhook の統合
- **ヘルスモニタリング**: 組み込みおよびカスタムのヘルスチェック

## アーキテクチャの概要

### コアコンポーネント

| コンポーネント | 説明 | レプリカ数 (HA) |
|-----------|-------------|---------------|
| **API Server** | すべての API リクエスト、認証、RBAC を処理 | 2+ |
| **Repository Server** | リポジトリをクローンし、マニフェストを生成して、結果をキャッシュ | 2+ |
| **Application Controller** | アプリケーションを監視し、状態をリコンサイル | 2+ (sharded) |
| **Redis** | repo server と controller のキャッシュレイヤー | 3 (HA) |
| **Dex** | 任意のアイデンティティブローカー。バンドルされたインメモリストレージはレプリカ追加による安全なスケーリングに対応しない | 標準バンドルでは 1 |
| **Notification Controller** | イベント発生時に通知を送信 | 1+ |
| **ApplicationSet Controller** | ApplicationSet リソースを管理 | 1+ |

### データフロー

![ユーザーが API Server を通じて ArgoCD アプリケーションを作成すると、Repo Server を介してマニフェストがレンダリングされ、その後 Application Controller がリコンサイルループで Kubernetes に対して望ましい状態と実際の状態を繰り返し比較し、ドリフト時に変更を適用する様子を示すシーケンス図。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## コアコンセプト

### Application

Application CRD は ArgoCD の主要リソースです。以下を定義します。
- **ソース**: マニフェストの取得元（Git repo、Helm chart、OCI）
- **デスティネーション**: デプロイ先（クラスターと namespace）
- **Sync Policy**: 同期の処理方法

### Project

Project は論理的なグループ化とアクセス制御を提供します。
- 使用できるリポジトリを制限
- デスティネーションのクラスターと namespace を制限
- 許可／拒否するリソースを定義

### ApplicationSet

ApplicationSet は generator を使用して、単一の定義から複数のアプリケーションを管理できます。
- **List Generator**: 静的な値のリスト
- **Cluster Generator**: 登録済みクラスターをターゲット
- **Git Generator**: リポジトリのディレクトリ／ファイルをスキャン
- **Matrix/Merge**: 複数の generator を組み合わせ

### Sync

同期により、クラスターの状態を望ましい状態に一致させます。
- **手動 Sync**: ユーザーがトリガー
- **Auto Sync**: Git の変更時に自動実行
- **Self-Heal**: ドリフトを自動修正
- **Prune**: 孤立したリソースを削除

## サブガイドのナビゲーション

| ガイド | 説明 |
|-------|-------------|
| [インストール](01-installation.md) | インストール方法、CLI セットアップ、HA 設定、EKS 統合 |
| [アプリケーション](02-applications.md) | Application CRD、ソースタイプ、ヘルスチェック、hook、App of Apps |
| [Sync 戦略](03-sync-strategies.md) | Sync Policy、wave、window、差分比較、retry 設定 |
| [ApplicationSet](04-applicationsets.md) | すべての generator、テンプレート化、段階的 Sync、マルチクラスターパターン |
| [トラフィック管理](05-traffic-management.md) | Argo Rollouts、blue-green、canary、分析、ingress 統合 |
| [Project と RBAC](06-projects-rbac.md) | AppProject、RBAC Policy、マルチテナンシー、JWT token |
| [セキュリティ](07-security.md) | SSO 統合、secret 管理、TLS、監査ログ |
| [通知](08-notifications.md) | Notification Service、trigger、template、subscription |
| [ベストプラクティス](09-best-practices.md) | リポジトリパターン、パフォーマンスチューニング、トラブルシューティング、EKS のヒント |
| [Rollouts Experiments の詳細](10-rollouts-experiment.md) | Experiment CRD、エフェメラル ReplicaSet の検証、AnalysisRun の判定 |

## クイックスタート

### 1. ArgoCD をインストール

これは自己管理の非 HA 評価用の例です。互換性のあるクラスター、CRD/RBAC 権限、空の専用 namespace を準備してください。本番の HA／認証／アップグレードに関する判断には[インストールガイド](01-installation.md)を使用してください。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.4/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. UI にアクセス

```bash
# Port forward to access locally
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 3. 初期パスワードを取得

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### 4. CLI 経由でログイン

[インストールガイド](01-installation.md)に示すように、対応する OS／アーキテクチャ用 CLI をインストールし、リリースのチェックサムを検証してください。別のターミナルで port forwarding を実行し続けます。

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. 最初のアプリケーションをデプロイ

```bash
# Create application via CLI
argocd app create guestbook \
  --repo https://github.com/argoproj/argocd-example-apps.git \
  --path guestbook \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default

# Sync the application
argocd app sync guestbook
```

または宣言的に行います。

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
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## バージョン互換性

レビュー対象の基準は **Argo CD 3.5.2 / Helm chart 10.8.4** です。リリースノートのレビュー後にマニフェストの例をパッチ 3.5.4 へ更新しました（再実行していません）。chart 10.8.4 は引き続き Argo CD v3.5.2 をデプロイします。3.5.4 が最初に含まれるのは chart 10.9.7 です。Application と installation-chart のバージョンは異なります。Argo CD は直近 3 つの minor line にパッチを提供し、それより古い line は EOL です。

### テスト済み Kubernetes の組み合わせ

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

これは 3.5.4 リポジトリに記録された upstream のテストマトリクスです。chart の最小 kubeVersion 制約、Kubernetes/EKS サポート期間、管理対象 Argo CD のバージョンポリシーとは異なります。EKS の minor バージョンと Argo CD の minor バージョンに一対一の対応関係はありません。

### 最近のリリース

- 3.5.0: **2026-08-04** にリリース。server の Helm 4 renderer を含む変更について、移行ガイダンスを確認してください。
- 3.5.1: 2026-08-12 にリリース。
- 3.5.2: 2026-08-27 にリリース。
- 3.5.3: 2026-09-14 にリリース。バグ修正（ヘルスチェック、Sync retry state、UI）。
- 3.5.4: 2026-10-06 にリリース。**セキュリティパッチリリース**です。Kustomize remote ref および Kustomize Helm config home を介した repo-server でのコマンド実行、Jsonnet import を介した repo-server のファイル読み取り、PreDelete/PostDelete hook による AppProject 制限のバイパス（CVE-2026-77459）の 4 件の CRITICAL 問題を修正し、同じ修正が v3.4.10/v3.3.15 にもバックポートされています。動作の変更点: Kustomize build は `helmGlobals.configHome` を考慮しなくなり、4 MiB を超える OCI マニフェストは拒否されます。アップグレード前に[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)を確認してください。
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): 3.6 line の最初のリリース候補で、2026-09-15 に公開。本番の基準ではありません。

### 2026 年 10 月更新: Argo CD 4.0 のビジョン策定を開始

[9 月 30 日の CNCF 投稿](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/)によると、Argo コミュニティは Argo CD 4.0 のビジョン策定プロセスを開始しました。また、ArgoCon North America 2026（KubeCon NA と同時開催される終日・2 トラックのイベント）は、最近の開発状況と今後のバージョンを取り上げるメンテナー基調講演で開幕します。これは初期段階のロードマップ方向性の策定であり、4.0 の機能と時期はまだ確定していません。

### Argo Rollouts

Rollouts は独立した controller であり、Argo CD なしでも使用できます。このレビューではその 1.10.0 ドキュメントを使用しています。無関係な製品バージョン番号を対応付けるのではなく、Rollouts の CRD/controller、traffic plugin、Kubernetes、および Argo CD のヘルスチェック統合を検証してください。

### EKS Managed Argo CD Capability

Argo CD 向け EKS Capability は、自己管理インストールとは異なる運用モデルです。そのカスタム設定は、capability で設定された namespace 内で `app.kubernetes.io/part-of: argocd` ラベルを持つ、**サポート対象**の argocd-cm key にのみ適用されます。サポート対象外の key／flag は無視されます。標準 Lua library や任意実行 plugin が利用可能と想定しないでください。[managed configuration guide](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)を参照してください。

## 次のステップ

1. **[インストールガイド](01-installation.md)**: 本番向けに ArgoCD をセットアップ
2. **[アプリケーションガイド](02-applications.md)**: Application CRD について学ぶ
3. **[ApplicationSets ガイド](04-applicationsets.md)**: マルチクラスターデプロイ

## リソース

- [ArgoCD 公式ドキュメント](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub リポジトリ](https://github.com/argoproj/argo-cd)
- [Argo Rollouts ドキュメント](https://argoproj.github.io/argo-rollouts/)
- [CNCF ArgoCD プロジェクトページ](https://www.cncf.io/projects/argo/)

## クイズ

学んだ内容をテストするには、[ArgoCD インストールクイズ](../../quizzes/gitops/argocd/01-installation-quiz.md)に挑戦してください。

### バージョン付きレビューソース

- [Argo CD 3.5.4 でテスト済みの Kubernetes バージョン](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/tested-kubernetes-versions.md)
- [リリースサポートポリシー](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.9.7（Argo CD 3.5.4 を含む最初の chart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.9.7)
- [HA コンポーネントの動作](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/operator-manual/high_availability.md)
