# ArgoCD インストールクイズ

このクイズでは、ArgoCD のインストールと設定に関する理解度を確認します。

1. chart values を通じて HA/設定をバージョン管理したいチームに適したインストール方法はどれですか？
   - A) raw GitHub URL からの kubectl apply
   - B) カスタム values を使用した Helm chart
   - C) Docker Compose
   - D) 手動でのバイナリインストール

<details>
<summary>回答を表示</summary>

**回答: B) カスタム values を使用した Helm chart**

**解説:**
Helm は chart values を使うワークフローに適しています。公式の HA manifest や Kustomize も、本番環境に適したインストール方法です。管理主体を一つに決め、アップグレードもその主体の管理下で行ってください。

</details>

2. ArgoCD は通常、デフォルトでどの namespace にインストールされますか？
   - A) default
   - B) kube-system
   - C) argocd
   - D) gitops

<details>
<summary>回答を表示</summary>

**回答: C) argocd**

**解説:**
慣例により、ArgoCD は `argocd` namespace にインストールされます。これにより ArgoCD コンポーネントを分離でき、RBAC とリソースクォータの管理が容易になります。

</details>

3. ArgoCD Repo Server コンポーネントの目的は何ですか？
   - A) アプリケーションの状態を保存する
   - B) Git リポジトリを clone し、Kubernetes manifest を生成する
   - C) Web UI を提供する
   - D) ユーザー認証を管理する

<details>
<summary>回答を表示</summary>

**回答: B) Git リポジトリを clone し、Kubernetes manifest を生成する**

**解説:**
Repo Server は、Git リポジトリを clone し、さまざまなソース（Helm、Kustomize、プレーン YAML）から Kubernetes manifest を生成する役割を担います。パフォーマンス向上のため、リポジトリデータをキャッシュします。

</details>

4. ArgoCD のインストール後、初期 admin パスワードを取得するにはどうしますか？
   - A) インストール中に表示される
   - B) argocd-initial-admin-secret という名前の Secret から取得する
   - C) ArgoCD ConfigMap から取得する
   - D) 常に "admin" である

<details>
<summary>回答を表示</summary>

**回答: B) argocd-initial-admin-secret という名前の Secret から取得する**

**解説:**
通常の生成済み bootstrap password のフローでは、初期 admin パスワードが生成され、`argocd-initial-admin-secret` という名前の Kubernetes Secret に保存されます。次のコマンドで取得できます: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

</details>

5. より少ないリソースを使用する一方で、機能が制限される ArgoCD インストールモードはどれですか？
   - A) HA mode
   - B) Core mode
   - C) Lite mode
   - D) Minimal mode

<details>
<summary>回答を表示</summary>

**回答: B) Core mode**

**解説:**
ArgoCD Core mode は、API Server、UI、Dex なしで、必須コンポーネント（Application Controller と Repo Server）のみをインストールします。このモードは、ArgoCD が Git と CLI を介して完全に管理される環境に適しています。

</details>
