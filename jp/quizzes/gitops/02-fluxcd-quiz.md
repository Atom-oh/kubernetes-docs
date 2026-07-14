# FluxCD クイズ

このクイズでは、FluxCD とそのコンポーネントに関する理解を確認します。

1. FluxCD は CNCF でどのステータスを保持していますか？
   - A) Sandbox
   - B) Incubating
   - C) Graduated
   - D) Archived

<details>
<summary>回答を表示</summary>

**回答: C) Graduated**

**解説:**
FluxCD は 2022 年 11 月に CNCF を卒業し、成熟度に達して本番環境で広く採用されていることを示しています。

</details>

2. Git リポジトリから Artifact を取得する責務を持つ FluxCD Controller はどれですか？
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>回答を表示</summary>

**回答: C) Source Controller**

**解説:**
Source Controller は、Git リポジトリ（GitRepository）、Helm リポジトリ（HelmRepository）、OCI レジストリ（OCIRepository）、S3 バケット（Bucket）を含む外部ソースから Artifact を取得する責務を担います。

</details>

3. FluxCD が Kustomize 設定をデプロイするために使用する CRD は何ですか？
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>回答を表示</summary>

**回答: B) Kustomization**

**解説:**
Kustomization CRD は、Kustomize Overlay を Cluster に適用する方法を定義するために使用されます。これはソース（GitRepository）を参照し、Kustomize 設定へのパスを指定します。

</details>

4. FluxCD は Helm Chart のデプロイをどのように処理しますか？
   - A) Application CRD を使用する
   - B) HelmRelease CRD を使用する
   - C) helm CLI を直接使用する
   - D) Helm はサポートされていない

<details>
<summary>回答を表示</summary>

**回答: B) HelmRelease CRD を使用する**

**解説:**
HelmRelease CRD は、Helm Chart Release を宣言的に管理するために使用されます。Chart のソース、バージョン、Values、Upgrade/Rollback ポリシーを指定します。

</details>

5. FluxCD の ImageUpdateAutomation の目的は何ですか？
   - A) イメージの脆弱性をスキャンする
   - B) 新しいバージョンが検出されたときに、Git 内のイメージタグを自動的に更新する
   - C) コンテナイメージをビルドする
   - D) イメージプルシークレットを管理する

<details>
<summary>回答を表示</summary>

**回答: B) 新しいバージョンが検出されたときに、Git 内のイメージタグを自動的に更新する**

**解説:**
ImageUpdateAutomation は ImageRepository および ImagePolicy と連携して新しいコンテナイメージタグを検出し、Git リポジトリへ更新を自動的にコミットすることで、自動デプロイを実現します。

</details>

6. Cluster 上で FluxCD を Bootstrap するために使用するコマンドはどれですか？
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>回答を表示</summary>

**回答: B) flux bootstrap**

**解説:**
`flux bootstrap` コマンドは FluxCD コンポーネントをインストールし、Cluster を管理するための Git リポジトリを設定します。GitHub、GitLab、汎用 Git サーバーなど、さまざまな Git プロバイダーをサポートしています。

</details>

7. FluxCD は Multi-tenancy をどのようにサポートしますか？
   - A) ArgoCD のように Project を使用する
   - B) Namespace 分離と Kubernetes RBAC を使用する
   - C) Multi-tenancy はサポートされていない
   - D) 中央管理 Tenant を使用する

<details>
<summary>回答を表示</summary>

**回答: B) Namespace 分離と Kubernetes RBAC を使用する**

**解説:**
FluxCD は Namespace 分離を通じて Multi-tenancy をサポートします。各 Tenant は Flux リソースを含む独自の Namespace を持ち、アクセス制御には Kubernetes ネイティブの RBAC を組み合わせます。

</details>

8. FluxCD の Notification Controller の目的は何ですか？
   - A) SMS メッセージを送信する
   - B) イベントを処理し、外部サービスへアラートを送信する
   - C) Git Webhook のみを管理する
   - D) Pod ログを監視する

<details>
<summary>回答を表示</summary>

**回答: B) イベントを処理し、外部サービスへアラートを送信する**

**解説:**
Notification Controller は、外向きの通知（Slack、Teams などへの Alert）と、外部イベントの発生時に Reconciliation をトリガーする受信 Webhook（Receiver）の両方を処理します。

</details>
