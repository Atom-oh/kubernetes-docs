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
`syncPolicy.automated` を有効にすると、Argo CD はポリシーに従って OutOfSync の変更を適用します。live state のみのドリフトを同期するには `selfHeal`、削除には `prune` が必要です。また、同じ失敗したコミットを無条件に何度も再試行するわけではありません。

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
automated sync で `prune: true` を設定すると、その Application が追跡しているリソースのうち、desired source からなくなったものを Argo CD が削除します。クラスター内のすべての未管理リソースを削除するわけではありません。

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
automated sync が有効な場合、selfHeal は比較対象となる live state のみのドリフトを調整します。同期ウィンドウ、権限、差分無視ルールの影響を受けます。失われたデータの復元や YAML エラーの修正は行いません。

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
`Replace=true` sync オプションは、Argo CD に `kubectl apply` ではなく `kubectl replace` を使用させ、リソースをパッチではなく置き換えるようにします。ただし、これだけで immutable field の制約を回避できるわけではありません。`Force=true` と `Replace=true` を併用するとリソースを削除して再作成できますが、PVC の移行手段として使えるわけではありません。

</details>
