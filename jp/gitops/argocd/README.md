# ArgoCD

> **レビュー基準**: Argo CD 3.5.2、Argo Rollouts 1.10.0。リリースノートの確認後、Argo CD マニフェストのピン留め先をパッチバージョン 3.5.5 に更新（例は再実行していません）
> **最終更新日**: 2026年10月19日

## 目次
- [ArgoCDとは？](#what-is-argocd)
- [主なメリット](#key-benefits)
- [アーキテクチャの概要](#architecture-overview)
- [主要な概念](#core-concepts)
- [サブガイドの案内](#sub-guide-navigation)
- [クイックスタート](#quick-start)
- [バージョン互換性](#version-compatibility)

## ArgoCDとは？ {#what-is-argocd}

ArgoCDは、Kubernetes向けの宣言型GitOps継続的デリバリーツールです。Gitリポジトリで定義された望ましい状態とクラスター内の実際の状態を同期することで、Kubernetesクラスターへのアプリケーションのデプロイを自動化します。

Argo CDは、CNCFのGraduatedプロジェクトであるArgoの一部です。採用実績があるからといって、特定のセキュリティ要件や可用性要件への適合性が保証されるわけではありません。

![ArgoCDのコントロールプレーンがRepo Serverを介してGit、Helm、OCIソースからマニフェストを取得し、Application Controllerがそれらを管理対象のKubernetesクラスターに反映して同期するアーキテクチャ図。ユーザーはWeb UI、CLI、またはgRPC APIを通じてAPI Serverにアクセスします。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主なメリット {#key-benefits}

### GitOpsネイティブ

- **Gitを信頼できる唯一の情報源として使用**: すべてのアプリケーション構成をGitに保存
- **宣言型デプロイ**: 望ましい状態を定義すれば、残りはArgoCDが処理
- **監査証跡**: Gitコミットを通じてすべての変更履歴を完全に記録
- **ロールバック**: 保持されている構成リビジョンを再デプロイ。データベースや外部状態の復旧は別途必要

### マルチクラスター管理

- **一元管理**: 単一のArgoCDインスタンスから数百のクラスターを管理
- **ApplicationSet**: テンプレートベースのマルチクラスターへのデプロイ
- **Cluster Generator**: ラベルに基づいて動的にクラスターを選択

### エンタープライズ対応

- **RBAC**: きめ細かなロールベースのアクセス制御
- **SSO統合**: OIDCを直接利用するか、他のIDプロバイダーにはサポート対象のDexコネクターを利用
- **マルチテナンシー**: Projectベースの分離
- **高可用性**: 本番環境向けのHAデプロイ

### 開発者エクスペリエンス

- **Web UI**: 視覚的なアプリケーション管理と監視
- **CLI**: 充実した機能を備えるコマンドラインインターフェース
- **通知**: Slack、Teams、メール、Webhookとの連携
- **ヘルスモニタリング**: 組み込みおよびカスタムのヘルスチェック

## アーキテクチャの概要 {#architecture-overview}

### 主要コンポーネント

| コンポーネント | 説明 | レプリカ数（HA） |
|-----------|-------------|---------------|
| **API Server** | すべてのAPIリクエスト、認証、RBACを処理 | 2以上 |
| **Repository Server** | リポジトリをクローンし、マニフェストを生成して、結果をキャッシュ | 2以上 |
| **Application Controller** | アプリケーションを監視し、状態を調整 | 2以上（シャーディング） |
| **Redis** | Repo ServerとController向けのキャッシュレイヤー | 3（HA） |
| **Dex** | オプションのIDブローカー。バンドルされたインメモリストレージは、レプリカを増やしても安全にスケールしません | 標準バンドルでは1 |
| **Notification Controller** | イベント発生時に通知を送信 | 1以上 |
| **ApplicationSet Controller** | ApplicationSetリソースを管理 | 1以上 |

### データフロー

![ユーザーがAPI Serverを通じてArgoCDアプリケーションを作成し、Repo Server経由でマニフェストがレンダリングされるシーケンス図。その後、Application Controllerは調整ループ内でKubernetes上の望ましい状態と実際の状態を繰り返し比較し、ドリフトがあれば変更を適用します。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## 主要な概念 {#core-concepts}

### Application

Application CRDは、ArgoCDの主要なリソースです。次の項目を定義します。
- **Source**: マニフェストの取得元（Gitリポジトリ、Helm Chart、OCI）
- **Destination**: デプロイ先（クラスターとnamespace）
- **Sync Policy**: 同期方法

### Project

Projectは、論理的なグループ化とアクセス制御を提供します。
- 使用できるリポジトリを制限
- デプロイ先のクラスターとnamespaceを制限
- 許可または禁止するリソースを定義

### ApplicationSet

ApplicationSetを使うと、Generatorによって単一の定義から複数のアプリケーションを管理できます。
- **List Generator**: 値の静的なリスト
- **Cluster Generator**: 登録済みクラスターを対象にする
- **Git Generator**: リポジトリのディレクトリやファイルをスキャン
- **Matrix/Merge**: 複数のGeneratorを組み合わせる

### Sync

同期では、クラスターの状態を望ましい状態に一致させます。
- **手動Sync**: ユーザーが開始
- **自動Sync**: Gitの変更時に自動実行
- **Self-Heal**: ドリフトを自動的に修正
- **Prune**: 孤立したリソースを削除

## サブガイドの案内 {#sub-guide-navigation}

| ガイド | 説明 |
|-------|-------------|
| [インストール](01-installation.md) | インストール方法、CLIのセットアップ、HA構成、EKSとの統合 |
| [アプリケーション](02-applications.md) | Application CRD、ソースの種類、ヘルスチェック、フック、App of Apps |
| [同期戦略](03-sync-strategies.md) | Syncポリシー、Wave、Window、差分比較、再試行の構成 |
| [ApplicationSet](04-applicationsets.md) | すべてのGenerator、テンプレート、段階的Sync、マルチクラスターのパターン |
| [トラフィック管理](05-traffic-management.md) | Argo Rollouts、Blue-Green、Canary、分析、Ingressとの統合 |
| [ProjectとRBAC](06-projects-rbac.md) | AppProject、RBACポリシー、マルチテナンシー、JWTトークン |
| [セキュリティ](07-security.md) | SSO統合、シークレット管理、TLS、監査ログ |
| [通知](08-notifications.md) | 通知サービス、トリガー、テンプレート、サブスクリプション |
| [ベストプラクティス](09-best-practices.md) | リポジトリのパターン、パフォーマンス調整、トラブルシューティング、EKSのヒント |
| [Rollouts Experimentsの詳細](10-rollouts-experiment.md) | Experiment CRD、一時的なReplicaSetの検証、AnalysisRunの判定 |

## クイックスタート {#quick-start}

### 1. ArgoCDをインストールする

これは、自己管理型でHA構成ではない評価用の例です。互換性のあるクラスター、CRD/RBAC権限、空の専用namespaceを用意してください。本番環境でのHA、認証、アップグレードに関する判断には、[インストールガイド](01-installation.md)を参照してください。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. UIにアクセスする

```bash
# Port forward to access locally
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 3. 初期パスワードを取得する

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### 4. CLIでログインする

[インストールガイド](01-installation.md)に記載されている手順に従って、OSとアーキテクチャに合ったCLIをインストールし、リリースチェックサムを検証してください。別のターミナルでポートフォワーディングを実行したままにします。

```bash
# Install CLI (macOS)
brew install argocd

# Login
argocd login localhost:8080

# Change the bootstrap password
argocd account update-password
kubectl -n argocd delete secret argocd-initial-admin-secret
```

### 5. 最初のアプリケーションをデプロイする

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

宣言的に作成する場合：

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

## バージョン互換性 {#version-compatibility}

レビュー対象の基準は**Argo CD 3.5.2 / Helm chart 10.8.4**です。リリースノートの確認後、マニフェストの例をパッチバージョン3.5.5に更新しました（再実行していません）。Chart 10.8.4がデプロイするのは引き続きArgo CD v3.5.2であり、3.5.5が初めて含まれるのはChart 10.10.3です。アプリケーションとインストール用Chartのバージョンは異なります。Argo CDがパッチを提供するのは直近の3つのマイナー系列で、これより古い系列はEOLです。

### テスト済みKubernetesの組み合わせ

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36、1.35、1.34、1.33 |
| 3.4 | 1.35、1.34、1.33、1.32 |
| 3.3 | 1.35、1.34、1.33、1.32 |

これは、3.5.5リポジトリに記録されている上流のテストマトリクスです。Chartの最小kubeVersion制約、Kubernetes/EKSのサポート期間、マネージドArgo CDのバージョンポリシーとは異なります。EKSのマイナーバージョンとArgo CDのマイナーバージョンに、一対一の対応関係はありません。

### 最近のリリース

- 3.5.0: **2026年8月4日**リリース。サーバーのHelm 4レンダラーなどの変更について、移行ガイダンスを確認してください。
- 3.5.1: 2026年8月12日リリース。
- 3.5.2: 2026年8月27日リリース。
- 3.5.3: 2026年9月14日リリース。バグ修正（ヘルスチェック、Syncの再試行状態、UI）。
- 3.5.4: 2026年10月6日リリース。**セキュリティパッチリリース**です。重大度CRITICALの4件の問題を修正します。具体的には、Kustomizeのリモート参照経由およびKustomizeのHelm config home経由でのrepo-server上のコマンド実行、Jsonnetインポート経由でのrepo-serverによるファイル読み取り、PreDelete/PostDeleteフックによるAppProject制限の回避（CVE-2026-77459）です。同じ修正はv3.4.10/v3.3.15にもバックポートされました。動作の変更点として、Kustomizeビルドで`helmGlobals.configHome`が適用されなくなり、4 MiBを超えるOCIマニフェストが拒否されます。アップグレード前に[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)を確認してください。
- 3.5.5: 2026年10月12日リリース。バグ修正のパッチリリースです（古いマニフェスト、CMP失敗後のrepo-serverにおけるgoroutineリーク、OCIキャッシュの動作など）。v3.4.11/v3.3.16も同日に公開されました。[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5)を参照してください。
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): 3.6系列の最初のリリース候補で、2026年9月15日に公開されました。本番環境の基準にはなりません。
- [3.6.0-rc3](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3): 3.6系列の最新のリリース候補で、2026年10月15日に公開されました。こちらも本番環境の基準にはなりません。

### 2026年10月の更新: Argo CD 4.0のビジョン策定を開始

[9月30日のCNCF投稿](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/)によると、ArgoコミュニティはArgo CD 4.0のビジョン策定プロセスを開始しました。また、KubeCon NAと併催される終日2トラックのイベント、ArgoCon North America 2026は、最近の開発状況と今後のバージョンを取り上げるメンテナーの基調講演で幕を開ける予定です。これはロードマップの初期段階における方向性の検討であり、4.0の機能や時期はまだ確定していません。

### Argo Rollouts

Rolloutsは独立したControllerであり、Argo CDなしでも使用できます。このレビューでは、バージョン1.10.0のドキュメントを参照しています。関連性のない製品のバージョン番号を対応付けるのではなく、RolloutsのCRD/Controller、トラフィックプラグイン、Kubernetes、Argo CDのヘルスチェック統合を検証してください。

### EKSマネージドArgo CDの機能

EKS Capability for Argo CDは、自己管理型インストールとは異なる運用モデルです。カスタム構成が適用されるのは、Capability用に設定されたnamespace内で、ラベル`app.kubernetes.io/part-of: argocd`が付与されているリソースのうち、**サポート対象**のargocd-cmキーに限られます。サポート対象外のキーやフラグは無視されます。標準Luaライブラリや任意の実行プラグインが利用できるとは想定しないでください。[マネージド構成ガイド](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)を参照してください。

## 次のステップ

1. **[インストールガイド](01-installation.md)**: ArgoCDを本番環境向けにセットアップする
2. **[アプリケーションガイド](02-applications.md)**: Application CRDについて学ぶ
3. **[ApplicationSetガイド](04-applicationsets.md)**: マルチクラスターにデプロイする

## リソース

- [ArgoCD公式ドキュメント](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHubリポジトリ](https://github.com/argoproj/argo-cd)
- [Argo Rolloutsドキュメント](https://argoproj.github.io/argo-rollouts/)
- [CNCF Argoプロジェクトページ](https://www.cncf.io/projects/argo/)

## クイズ

学んだ内容を確認するには、[ArgoCDインストールクイズ](../../quizzes/gitops/argocd/01-installation-quiz.md)に挑戦してください。

### バージョンを指定したレビュー資料

- [Argo CD 3.5.5でテスト済みのKubernetesバージョン](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [リリースサポートポリシー](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3（Argo CD 3.5.5を初めて含むChart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [HAコンポーネントの動作](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
