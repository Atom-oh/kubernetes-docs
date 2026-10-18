# ArgoCD セキュリティクイズ

このクイズでは、ArgoCD のセキュリティ機能とベストプラクティスに関する理解度を確認します。

1. ArgoCD はデフォルトで Git リポジトリ内の Secret をどのように扱いますか？
   - A) 自動的に暗号化する
   - B) Secret を特別には扱わず、プレーンテキストとして保存する
   - C) Kubernetes Secrets API を使用する
   - D) secrets manager を必要とする

<details>
<summary>回答を表示</summary>

**回答: B) Secret を特別には扱わず、プレーンテキストとして保存する**

**解説:**
ArgoCD 自体は Secret を暗号化しません。Sealed Secrets/SOPS は暗号文を Git に保存します。ESO/Vault との統合では外部参照を保存して値を取得できますが、Git 内のファイルが自動的に暗号化されるわけではありません。Base64 は暗号化ではありません。

</details>

2. controller の公開鍵を使用して Kubernetes Secret を封印するツールはどれですか？
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>回答を表示</summary>

**回答: B) Sealed Secrets**

**解説:**
Sealed Secrets は controller の鍵ペアを使用します。デフォルトの strict scope では Secret の名前と namespace も結び付けられます。復号の信頼境界は鍵を所持している主体によって決まります。暗号化された SealedSecret は Git に安全に保存でき、クラスター内の Sealed Secrets controller が復号します。

</details>

3. ArgoCD の Dex コンポーネントの目的は何ですか？
   - A) コンテナイメージのスキャン
   - B) OpenID Connect 認証と SSO
   - C) Network policy の適用
   - D) Secret のローテーション

<details>
<summary>回答を表示</summary>

**回答: B) OpenID Connect 認証と SSO**

**解説:**
Dex は OpenID Connect (OIDC) 認証を提供する ID サービスです。LDAP、SAML、GitHub などの ID を OIDC 経由で仲介します。Argo CD で OIDC を直接使用する場合、常に Dex が必要とは限りません。

</details>

4. Application が作成できる Kubernetes リソースを制限するにはどうすればよいですか？
   - A) Kubernetes ResourceQuotas を使用する
   - B) AppProject の namespaceResourceBlacklist または namespaceResourceWhitelist を使用する
   - C) Pod の requests/limits だけを変更する
   - D) ArgoCD では不可能である

<details>
<summary>回答を表示</summary>

**回答: B) AppProject の namespaceResourceBlacklist または namespaceResourceWhitelist を使用する**

**解説:**
AppProject では、`namespaceResourceBlacklist`（特定のリソースを拒否）または `namespaceResourceWhitelist`（特定のリソースのみを許可）を定義して、namespaced なリソース種別を制御できます。cluster-scoped リソースには別のリストを使います。また、この設定は admission policy のように、特権付き Pod の設定内容を検査するものではありません。

</details>

5. ArgoCD API server を公開する際の推奨プラクティスは何ですか？
   - A) Basic auth を使用してパブリックに公開する
   - B) TLS と認証を備えた保護されたアクセス経路を使用する
   - C) 認証なしで実行する
   - D) port-forwarding 経由でのみアクセスする

<details>
<summary>回答を表示</summary>

**回答: B) 内部に留め、TLS と認証を備えた ingress を使用する**

**解説:**
Ingress/Gateway または保護された内部経路を通じて、認証付き TLS を使用します。フロントエンドで TLS を終端しても、それだけでバックエンドの TLS が検証されるわけではありません。機密性の高い環境では、VPN アクセスや IP whitelist などの追加対策も推奨されます。

</details>
