# ArgoCD ベストプラクティス クイズ

このクイズでは、ArgoCD のベストプラクティスと運用パターンに関する理解度を確認します。

1. ArgoCD 自体の設定を管理するための推奨アプローチは何ですか？
   - A) UI を通じた手動設定
   - B) ArgoCD による ArgoCD の管理（app-of-apps パターン）
   - C) kubectl apply を直接使用する
   - D) 設定は決して変更すべきではない

<details>
<summary>回答を表示</summary>

**回答: B) ArgoCD による ArgoCD の管理（app-of-apps パターン）**

**解説:**
「app-of-apps」パターンでは、ArgoCD が自身の設定と他の ArgoCD Applications を管理します。これにより、ArgoCD の設定がバージョン管理され、GitOps の原則に従うことが保証されます。

</details>

2. GitOps に推奨されるリポジトリ構成は何ですか？
   - A) アプリケーションコードとマニフェストを同じリポジトリに混在させる
   - B) アプリケーションコード用とデプロイメントマニフェスト用のリポジトリを分ける
   - C) すべてを単一のファイルに保存する
   - D) パブリックリポジトリの Helm charts のみを使用する

<details>
<summary>回答を表示</summary>

**回答: B) アプリケーションコード用とデプロイメントマニフェスト用のリポジトリを分ける**

**解説:**
アプリケーションコードをデプロイメントマニフェストから分離すると、より明確な監査証跡が得られ、異なるチームがそれぞれを管理でき、デプロイメント変更による CI トリガーを防止できます。

</details>

3. 環境固有の設定はどのように扱うべきですか？
   - A) 環境ごとに個別の Applications を作成する
   - B) 環境ごとに Kustomize overlays または Helm values files を使用する
   - C) マニフェスト内に値をハードコードする
   - D) pods 内で環境変数を使用する

<details>
<summary>回答を表示</summary>

**回答: B) 環境ごとに Kustomize overlays または Helm values files を使用する**

**解説:**
Kustomize overlays または Helm values files を使用すると、共通のベース設定を維持しながら、環境ごとに特定の値（replicas、resources、domains）をカスタマイズできます。

</details>

4. 環境間で変更をプロモートするための推奨アプローチは何ですか？
   - A) 本番ブランチへの直接コミット
   - B) staging から本番へのレビュー付き Pull requests
   - C) UI での手動 sync
   - D) レビューなしの自動プロモーション

<details>
<summary>回答を表示</summary>

**回答: B) staging から本番へのレビュー付き Pull requests**

**解説:**
プロモーションに Pull requests を使用すると、本番に到達する前に変更がレビューされることが保証され、監査証跡が提供され、マージ前に自動チェック（tests、policy validation）を実行できます。

</details>

5. GitOps ワークフローで secrets はどのように扱うべきですか？
   - A) プレーンテキストの secrets を Git にコミットする
   - B) 暗号化された secrets（Sealed Secrets、SOPS）または外部 secret managers を使用する
   - C) 各クラスターで secrets を手動作成する
   - D) secrets を環境変数に保存する

<details>
<summary>回答を表示</summary>

**回答: B) 暗号化された secrets（Sealed Secrets、SOPS）または外部 secret managers を使用する**

**解説:**
secrets を Git にプレーンテキストで保存してはいけません。Sealed Secrets や SOPS などの暗号化ツール、または External Secrets Operator を備えた HashiCorp Vault などの外部 secret managers を使用してください。

</details>
