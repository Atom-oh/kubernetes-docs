# ArgoCD

> **レビューの基準**: Argo CD 3.5.2、Argo Rollouts 1.10.0。リリースノートの確認後、Argo CD マニフェストの指定バージョンをパッチリリース 3.5.5 に更新（例は再実行していません）
> **最終更新日**: 2026年10月26日

## 目次
- [ArgoCD とは？](#what-is-argocd)
- [主なメリット](#key-benefits)
- [アーキテクチャの概要](#architecture-overview)
- [主要な概念](#core-concepts)
- [サブガイドの一覧](#sub-guide-navigation)
- [クイックスタート](#quick-start)
- [バージョン互換性](#version-compatibility)

## ArgoCD とは？

ArgoCD は、Kubernetes 向けの宣言型 GitOps 継続的デリバリーツールです。Git リポジトリで定義した望ましい状態とクラスター内の実際の状態を同期することで、Kubernetes クラスターへのアプリケーションのデプロイを自動化します。

Argo CD は CNCF の Graduated Argo プロジェクトの一部です。採用実績だけでは、特定のセキュリティ要件や可用性要件への適合性は証明されません。

![ArgoCD のコントロールプレーンが Repo Server を介して Git、Helm、OCI ソースからマニフェストを取得し、Application Controller がそれらを調整して管理対象の Kubernetes クラスターに同期するアーキテクチャ図。ユーザーは Web UI、CLI、または gRPC API を介して API Server にアクセスします。](../../.gitbook/assets/en-gitops-argocd-overview-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-0.html)

## 主なメリット

### GitOps ネイティブ

- **Git を唯一の信頼できる情報源に**: すべてのアプリケーション設定を Git に保存
- **宣言型デプロイ**: 望ましい状態を定義すれば、あとは ArgoCD が処理
- **監査証跡**: Git コミットを通じてすべての変更履歴を完全に記録
- **ロールバック**: 保持されている設定リビジョンを再デプロイ。データベースや外部状態の復旧は別途対応

### マルチクラスター管理

- **一元管理**: 1 つの ArgoCD インスタンスから数百のクラスターを管理
- **ApplicationSet**: テンプレートベースのマルチクラスター・デプロイ
- **Cluster Generator**: ラベルに基づいて動的にクラスターを指定

### エンタープライズ対応

- **RBAC**: きめ細かなロールベースのアクセス制御
- **SSO 統合**: OIDC による直接連携、または他の ID プロバイダー向けのサポート対象 Dex コネクター
- **マルチテナンシー**: Project ベースの分離
- **高可用性**: 本番環境に対応した HA デプロイ

### 開発者エクスペリエンス

- **Web UI**: アプリケーションの視覚的な管理と監視
- **CLI**: 機能が充実したコマンドラインインターフェイス
- **通知**: Slack、Teams、メール、Webhook との連携
- **ヘルスモニタリング**: 組み込みおよびカスタムのヘルスチェック

## アーキテクチャの概要

### 主要コンポーネント

| コンポーネント | 説明 | レプリカ数（HA） |
|-----------|-------------|---------------|
| **API Server** | すべての API リクエスト、認証、RBAC を処理 | 2+ |
| **Repository Server** | リポジトリをクローンし、マニフェストを生成して、結果をキャッシュ | 2+ |
| **Application Controller** | アプリケーションを監視し、状態を調整 | 2+（シャーディング構成） |
| **Redis** | Repo Server と Controller 向けのキャッシュ層 | 3（HA） |
| **Dex** | 任意の ID ブローカー。組み込みのインメモリストレージは、レプリカを追加しても安全にスケーリングできません | 標準バンドルでは 1 |
| **Notification Controller** | イベント発生時に通知を送信 | 1+ |
| **ApplicationSet Controller** | ApplicationSet リソースを管理 | 1+ |

### データフロー

![ユーザーが API Server を介して ArgoCD アプリケーションを作成し、API Server が Repo Server を通じてマニフェストをレンダリングするシーケンス図。その後、Application Controller は Kubernetes に対して望ましい状態と実際の状態を繰り返し比較し、調整ループ内でドリフトを検出すると変更を適用します。](../../.gitbook/assets/en-gitops-argocd-overview-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-overview-1.html)

## 主要な概念

### Application

Application CRD は ArgoCD の主要なリソースです。次の項目を定義します。
- **Source**: マニフェストの取得元（Git リポジトリ、Helm chart、OCI）
- **Destination**: デプロイ先（クラスターと namespace）
- **Sync Policy**: 同期の処理方法

### Project

Project は、論理的なグループ化とアクセス制御を提供します。
- 使用できるリポジトリを制限
- 配置先のクラスターと namespace を制限
- 許可／拒否するリソースを定義

### ApplicationSet

ApplicationSet を使うと、Generator によって 1 つの定義から複数のアプリケーションを管理できます。
- **List Generator**: 静的な値の一覧
- **Cluster Generator**: 登録済みクラスターを対象に指定
- **Git Generator**: リポジトリのディレクトリ／ファイルをスキャン
- **Matrix/Merge**: 複数の Generator を組み合わせる

### Sync

同期では、クラスターの状態を望ましい状態に一致させます。
- **手動同期**: ユーザーが実行
- **自動同期**: Git の変更時に自動実行
- **Self-Heal**: ドリフトを自動的に修正
- **Prune**: 孤立したリソースを削除

## サブガイドの一覧

| ガイド | 説明 |
|-------|-------------|
| [インストール](01-installation.md) | インストール方法、CLI のセットアップ、HA 設定、EKS 連携 |
| [アプリケーション](02-applications.md) | Application CRD、ソースの種類、ヘルスチェック、フック、App of Apps |
| [同期戦略](03-sync-strategies.md) | 同期ポリシー、Wave、ウィンドウ、差分比較、再試行設定 |
| [ApplicationSet](04-applicationsets.md) | すべての Generator、テンプレート化、段階的同期、マルチクラスターのパターン |
| [トラフィック管理](05-traffic-management.md) | Argo Rollouts、Blue-Green、Canary、Analysis、Ingress 連携 |
| [Project と RBAC](06-projects-rbac.md) | AppProject、RBAC ポリシー、マルチテナンシー、JWT トークン |
| [セキュリティ](07-security.md) | SSO 連携、シークレット管理、TLS、監査ログ |
| [通知](08-notifications.md) | 通知サービス、トリガー、テンプレート、サブスクリプション |
| [ベストプラクティス](09-best-practices.md) | リポジトリのパターン、パフォーマンス調整、トラブルシューティング、EKS のヒント |
| [Rollouts Experiment 詳細解説](10-rollouts-experiment.md) | Experiment CRD、一時的な ReplicaSet の検証、AnalysisRun の判定結果 |

## クイックスタート

### 1. ArgoCD をインストールする

これは、HA ではないセルフマネージド環境での評価用の例です。互換性のあるクラスター、CRD/RBAC 権限、専用の空の namespace を用意してください。本番環境の HA、認証、アップグレードに関する判断には、[インストールガイド](01-installation.md)を参照してください。

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s
```

### 2. UI にアクセスする

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

### 4. CLI でログインする

[インストールガイド](01-installation.md)の手順に従って、対応する OS／アーキテクチャの CLI をインストールし、リリースのチェックサムを検証してください。別のターミナルでポートフォワーディングを実行したままにします。

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

または、宣言型で作成します。

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

レビューの基準は **Argo CD 3.5.2 / Helm chart 10.8.4** です。リリースノートの確認後、マニフェストの例をパッチリリース 3.5.5 に更新しました（再実行していません）。Chart 10.8.4 がデプロイするのは引き続き Argo CD v3.5.2 です。3.5.5 が初めて含まれるのは chart 10.10.3 です。Application とインストール用 chart のバージョンは異なります。Argo CD がパッチを提供するのは直近 3 つのマイナーリリースラインです。それより古いラインは EOL です。

### テスト済みの Kubernetes バージョン組み合わせ

| Argo CD | Kubernetes |
|---|---|
| 3.5 | 1.36, 1.35, 1.34, 1.33 |
| 3.4 | 1.35, 1.34, 1.33, 1.32 |
| 3.3 | 1.35, 1.34, 1.33, 1.32 |

これは 3.5.5 のリポジトリに記録された upstream のテストマトリクスです。chart の最小 kubeVersion 制約、Kubernetes/EKS のサポート期間、マネージド Argo CD のバージョンポリシーとは異なります。EKS のマイナーバージョンと Argo CD のマイナーバージョンに一対一の対応関係はありません。

### 最近のリリース

- 3.5.0: **2026年8月4日** リリース。サーバーの Helm 4 レンダラーなど、変更点について移行ガイダンスを確認してください。
- 3.5.1: 2026年8月12日リリース。
- 3.5.2: 2026年8月27日リリース。
- 3.5.3: 2026年9月14日リリース。バグ修正（ヘルスチェック、同期の再試行状態、UI）。
- 3.5.4: 2026年10月6日リリース。**セキュリティパッチリリース**です。CRITICAL な問題を 4 件修正しています。Kustomize のリモート参照および Kustomize の Helm config home を介した repo-server でのコマンド実行、Jsonnet import を介した repo-server のファイル読み取り、PreDelete/PostDelete フックによる AppProject 制限の回避（CVE-2026-77459）です。同じ修正は v3.4.10/v3.3.15 にもバックポートされました。動作変更として、Kustomize のビルドでは `helmGlobals.configHome` が適用されなくなり、4 MiB を超える OCI マニフェストは拒否されます。アップグレード前に[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)を確認してください。
- 3.5.5: 2026年10月12日リリース。バグ修正のパッチリリースです（古いマニフェスト、CMP の失敗後に repo-server で発生する goroutine リーク、OCI キャッシュの動作など）。v3.4.11/v3.3.16 も同日に公開されました。[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.5)を参照してください。
- 3.5.6: 2026年10月20日リリース。バグ修正のパッチリリースです。v3.4.12（2026年10月21日）と v3.3.17（2026年10月20日）も同じ期間に公開されました。[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.5.6)を参照してください。
- 3.3.18: 2026年10月22日リリース。3.3 ライン向けの**セキュリティ修正**が含まれています。侵害された eMudhra CA 証明書（2026年10月20日に公表された中間 CA の侵害。エコシステム全体で修正済み）を信頼しないようにする修正です。[リリースノート](https://github.com/argoproj/argo-cd/releases/tag/v3.3.18)を参照してください。
- [3.6.0-rc1](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc1): 3.6 ラインの最初のリリース候補で、2026年9月15日に公開されました。本番環境の基準バージョンではありません。
- [3.6.0-rc3](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc3): 3.6 ラインのリリース候補で、2026年10月15日に公開されました。同様に、本番環境の基準バージョンではありません。
- [3.6.0-rc4](https://github.com/argoproj/argo-cd/releases/tag/v3.6.0-rc4): 3.6 ラインの最新リリース候補で、2026年10月22日に公開されました。同様に、本番環境の基準バージョンではありません。

### 2026年10月の更新: Argo CD 4.0 のビジョン策定が開始

[9月30日の CNCF の投稿](https://www.cncf.io/blog/2026/09/30/argocon-north-america-2026-what-to-expect-as-the-argo-community-looks-toward-cd-4-0/)によると、Argo コミュニティは Argo CD 4.0 のビジョン策定プロセスを開始しました。また、KubeCon NA と併催される終日・2 トラック構成のイベントである ArgoCon North America 2026 は、最近の動向と今後のバージョンについて解説するメンテナーの基調講演で幕を開けます。これはロードマップの方向性を定める初期段階であり、4.0 の機能や時期はまだ確定していません。

### Argo Rollouts

Rollouts は独立した Controller であり、Argo CD を使わずに利用できます。このレビューでは 1.10.0 のドキュメントを使用しています。関連のない製品のバージョン番号を対応づけるのではなく、Rollouts の CRD/Controller、トラフィックプラグイン、Kubernetes、および Argo CD のヘルスチェック連携を検証してください。

### EKS マネージド Argo CD の機能

EKS Capability for Argo CD は、セルフマネージドのインストールとは異なる運用モデルです。カスタム設定が適用されるのは、Capability が設定された namespace 内にあり、ラベル `app.kubernetes.io/part-of: argocd` が付いた、**サポート対象**の argocd-cm キーのみです。サポートされていないキーやフラグは無視されます。標準の Lua ライブラリや任意の実行プラグインが利用可能だとは想定しないでください。[マネージド設定ガイド](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)を参照してください。

2026年10月のテストでは、ローカルクラスターでさえ EKS ARN を使用するクラスター Secret による登録が必要で、自動作成されたアクセスエントリは `AmazonEKSEditPolicy` と `AmazonEKSAdminViewPolicy` の両方をアタッチするまで同期できませんでした。デフォルトの Git ポーリングでは、コミットから Synced になるまで 342～697 秒かかりました。GitHub webhook を使うと約 7 秒になりました。サインインには IAM Identity Center のみを使用でき、Notifications、CMP、`argocd admin` は利用できません。また、バージョンは AWS が選択します。権限、マルチクラスター構成、バージョンへの備え、セルフマネージドとの比較については、[EKS Capabilities](../../eks/13-eks-capabilities.md)を参照してください。

## 次のステップ

1. **[インストールガイド](01-installation.md)**: 本番環境向けに ArgoCD をセットアップする
2. **[アプリケーションガイド](02-applications.md)**: Application CRD について学ぶ
3. **[ApplicationSet ガイド](04-applicationsets.md)**: マルチクラスター・デプロイ

## リソース

- [ArgoCD 公式ドキュメント](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub リポジトリ](https://github.com/argoproj/argo-cd)
- [Argo Rollouts ドキュメント](https://argoproj.github.io/argo-rollouts/)
- [CNCF Argo プロジェクトページ](https://www.cncf.io/projects/argo/)

## クイズ

学んだ内容を確認するには、[ArgoCD インストールクイズ](../../quizzes/gitops/argocd/01-installation-quiz.md)に挑戦してください。

### バージョン付きレビュー資料

- [Argo CD 3.5.5 でテスト済みの Kubernetes バージョン](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/tested-kubernetes-versions.md)
- [リリースサポートポリシー](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/developer-guide/release-process-and-cadence.md)
- [3.5.0 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.0)
- [3.5.2 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.2)
- [3.5.3 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.3)
- [3.5.4 リリース](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4)
- [Chart 10.10.3（Argo CD 3.5.5 が初めて含まれる chart）](https://github.com/argoproj/argo-helm/releases/tag/argo-cd-10.10.3)
- [HA コンポーネントの動作](https://github.com/argoproj/argo-cd/blob/v3.5.5/docs/operator-manual/high_availability.md)
