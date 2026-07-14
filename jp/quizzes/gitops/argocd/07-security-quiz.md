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
ArgoCD 自体は Secret の暗号化を提供しません。Git 内の Secret は、Git にコミットする前に Sealed Secrets、SOPS、External Secrets Operator、Vault などのツールを使用して暗号化する必要があります。

</details>

2. クラスタ固有のキーを使用して Kubernetes Secrets を暗号化するツールはどれですか？
   - A) SOPS
   - B) Sealed Secrets
   - C) Vault
   - D) KMS

<details>
<summary>回答を表示</summary>

**回答: B) Sealed Secrets**

**解説:**
Sealed Secrets は、クラスタ固有のキーペアを使用して Secret を暗号化します。暗号化された SealedSecret は Git に安全に保存でき、クラスタ内の Sealed Secrets controller によって復号されます。

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
Dex は OpenID Connect (OIDC) 認証を提供する ID サービスです。これにより、ArgoCD はシングルサインオンのためにさまざまな ID プロバイダー（LDAP、SAML、GitHub など）と統合できます。

</details>

4. Application が作成できる Kubernetes リソースを制限するにはどうすればよいですか？
   - A) Kubernetes ResourceQuotas を使用する
   - B) AppProject の namespaceResourceBlacklist または namespaceResourceWhitelist を使用する
   - C) Pod Security Policies を使用する
   - D) ArgoCD では不可能である

<details>
<summary>回答を表示</summary>

**回答: B) AppProject の namespaceResourceBlacklist または namespaceResourceWhitelist を使用する**

**解説:**
AppProject では、`namespaceResourceBlacklist`（特定のリソースを拒否）または `namespaceResourceWhitelist`（特定のリソースのみを許可）を定義して、Application が管理できる Kubernetes リソースの種類を制御できます。

</details>

5. ArgoCD API server を公開する際の推奨プラクティスは何ですか？
   - A) Basic auth を使用してパブリックに公開する
   - B) 内部に留め、TLS と認証を備えた ingress を使用する
   - C) 認証なしで実行する
   - D) port-forwarding 経由でのみアクセスする

<details>
<summary>回答を表示</summary>

**回答: B) 内部に留め、TLS と認証を備えた ingress を使用する**

**解説:**
ArgoCD API server は、TLS termination と適切な認証（SSO/OIDC）を備えた ingress を通じて公開する必要があります。機密性の高い環境では、VPN アクセスや IP whitelist などの追加対策が推奨されます。

</details>
