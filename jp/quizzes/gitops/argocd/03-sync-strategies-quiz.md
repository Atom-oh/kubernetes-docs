# ArgoCD Sync 戦略クイズ

このクイズでは、ArgoCD の同期戦略とオプションに関する理解を確認します。

1. ArgoCD における「Sync」と「Refresh」の違いは何ですか？
   - A) 同じ操作である
   - B) Refresh は現在の状態を Git と比較し、Sync は両者を一致させるために変更を適用する
   - C) Sync は手動で、Refresh は自動である
   - D) Refresh はリソースを削除し、Sync は作成する

<details>
<summary>答えを表示</summary>

**回答: B) Refresh は現在の状態を Git と比較し、Sync は両者を一致させるために変更を適用する**

**解説:**
Refresh 操作は Git から最新の manifest を取得して live state と比較し、Application のステータスを更新します。Sync 操作は、実際に変更を cluster に適用して、live state を Git 内の desired state に一致させます。

</details>

2. `automated` sync policy を有効にすると何が起こりますか？
   - A) application を自動的に削除する
   - B) desired state が live state と異なる場合に自動同期を有効にする
   - C) 自動ロールバックを有効にする
   - D) backup を自動的に作成する

<details>
<summary>答えを表示</summary>

**回答: B) desired state が live state と異なる場合に自動同期を有効にする**

**解説:**
`syncPolicy.automated` を有効にすると、ArgoCD は live state が Git で定義された desired state から乖離していることを検出するたびに、application を自動的に同期します。

</details>

3. automated sync における `prune` オプションの目的は何ですか？
   - A) 古い Git branch をクリーンアップする
   - B) Git で定義されなくなったリソースを自動的に削除する
   - C) 失敗した Deployment を削除する
   - D) application 自体を削除する

<details>
<summary>答えを表示</summary>

**回答: B) Git で定義されなくなったリソースを自動的に削除する**

**解説:**
automated sync で `prune: true` を設定すると、ArgoCD は cluster に存在するものの Git repository では定義されなくなった Kubernetes リソースを自動的に削除します。

</details>

4. sync policy において `selfHeal: true` は何をしますか？
   - A) YAML の構文エラーを自動的に修正する
   - B) 手動変更によって live state が desired state から逸脱した場合に自動的に同期する
   - C) 正常でない Pod を再起動する
   - D) 破損した Git repository を修復する

<details>
<summary>答えを表示</summary>

**回答: B) 手動変更によって live state が desired state から逸脱した場合に自動的に同期する**

**解説:**
Self-heal は、誰かが cluster 内のリソースに（Git の外で）手動変更を加えた場合、ArgoCD が Git 内の desired state に一致するよう自動的に元に戻すことを保証します。

</details>

5. patch を適用する代わりにリソースを置き換えるには、どの sync オプションを使用しますか？
   - A) Force=true
   - B) Replace=true
   - C) Recreate=true
   - D) Update=true

<details>
<summary>答えを表示</summary>

**回答: B) Replace=true**

**解説:**
`Replace=true` sync オプションは、ArgoCD に対して `kubectl apply` ではなく `kubectl replace` を使用するよう指示します。これにより resource は patch されるのではなく完全に置き換えられます。これは immutable field を扱う場合に役立ちます。

</details>
