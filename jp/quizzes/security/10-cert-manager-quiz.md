# cert-manager クイズ

> **最終更新日**: 2026年9月13日

発行、更新、信頼情報の配布、AWS 連携の境界について確認する 10 問です。

## 問題

### 1. CNCF における cert-manager のプロジェクト状況はどれですか?

- A) Sandbox
- B) Incubating
- C) Graduated
- D) Archived

<details>
<summary>答えを表示</summary>

**答え: C) Graduated**

cert-manager は 2024年9月29日に Graduated となりました。2022年9月19日に Incubating となっています。プロジェクトの成熟度は、個々のインストールの安全性や可用性を保証するものではありません。

</details>

<span id="_2-which-component-in-cert-manager-watches-certificate-resources-and-triggers-certificate-issuance"></span>

### 2. Certificate を監視し、発行と更新を調整する cert-manager component はどれですか?

- A) cainjector
- B) webhook
- C) controller
- D) scheduler

<details>
<summary>答えを表示</summary>

**答え: C) controller**

controller が証明書のライフサイクルを調整します。webhook は custom resource の検証、既定値の設定、変換を行います。cainjector は、対応する API/webhook 設定に CA bundle を注入します。

</details>

<span id="_3-what-is-the-key-difference-between-issuer-and-clusterissuer-resources"></span>

### 3. Issuer と ClusterIssuer の主な違いは何ですか?

- A) ACME に対応するのは Issuer だけである
- B) Issuer は namespace scope、ClusterIssuer は cluster scope である
- C) 自動更新するのは ClusterIssuer だけである
- D) ClusterIssuer を作成すると SAN policy が自動的に強制される

<details>
<summary>答えを表示</summary>

**答え: B) Issuer は namespace scope、ClusterIssuer は cluster scope である**

Issuer は同じ namespace 内で参照します。ClusterIssuer の credential/CA Secret は、通常 cert-manager である controller の cluster-resource namespace に置きます。resource scope だけでは SAN や issuerRef の利用は認可されません。別途、承認や admission policy が必要です。

</details>

<span id="_4-which-acme-challenge-type-supports-wildcard-certificate-issuance"></span>

### 4. 通常の Let's Encrypt ACME wildcard 証明書発行に対応する検証方式はどれですか?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) port 443 への接続確認だけ

<details>
<summary>答えを表示</summary>

**答え: B) DNS-01**

DNS-01 は TXT record によって domain の管理権限を証明します。HTTP-01 は port 80 を必要とし、wildcard に対応しません。DNS API の権限は、対象の zone/TXT name に限定してください。認証の再利用や ACM による事前検証を使えば、要求ごとに新しい Challenge を行わずに済む場合があります。

</details>

<span id="_5-in-a-certificate-resource-what-does-the-secretname-field-specify"></span>

### 5. Certificate resource の `spec.secretName` は何を指定しますか?

- A) ACME account key の Secret
- B) 同じ namespace に作成する出力証明書/秘密鍵の Secret
- C) root CA を常に配布する ConfigMap
- D) Issuer の認証用 Secret

<details>
<summary>答えを表示</summary>

**答え: B) 同じ namespace に作成する出力証明書/秘密鍵の Secret**

出力 Secret には `tls.crt` と `tls.key` が含まれます。`ca.crt` がない場合もあり、クライアントの trust を配布する代わりにはなりません。既定の `privateKey.rotationPolicy` は 1.18 以降 `Always` です。Secret 更新後に application が再読み込みするかは別途確認してください。

</details>

<span id="_6-what-is-the-primary-use-case-for-the-aws-private-ca-issuer"></span>

### 6. AWS Private CA を cert-manager の外部 Issuer として接続する extension はどれですか?

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) acmesolver
- D) trust-manager

<details>
<summary>答えを表示</summary>

**答え: B) aws-privateca-issuer**

`aws-privateca-issuer` は `AWSPCAIssuer`/`AWSPCAClusterIssuer` を処理します。CA scope の IAM permission、workload identity、request approval、互換性のある CA mode/template/lifetime が必要です。Private CA を使っても、証明書が public browser から信頼されるわけではなく、発行が無料になるわけでもありません。

</details>

<span id="_7-what-does-trust-manager-do-in-the-cert-manager-ecosystem"></span>

### 7. cert-manager ecosystem で trust-manager が担う役割は何ですか?

- A) 証明書と秘密鍵を発行する
- B) 選択した namespace に CA bundle を配布する
- C) すべての Pod に CA private key をコピーする
- D) 証明書を自動的に失効させる

<details>
<summary>答えを表示</summary>

**答え: B) 選択した namespace に CA bundle を配布する**

既定の 0.25.0 chart は Bundle v1alpha1 を使います。source は設定された trust namespace から読み取り、namespaceSelector で配布先を制限します。ConfigMap target はサポートされています。Secret target には別途有効化と RBAC が必要です。`subPath` mount は更新を受け取らず、directory projection でも process が再読み込みするとは限りません。

</details>

<span id="_8-what-does-the-renewbefore-field-control-in-a-certificate-resource"></span>

### 8. 証明書を 90 日で要求したのに 45 日の証明書が発行されました。renewal 設定も ARI も明示していない場合、既定の更新はいつ予定されますか?

- A) 実際の有効期間の約 3 分の 2 が経過した時点
- B) 要求した 90 日を基準に 60 日目
- C) 常に有効期限の 30 日前
- D) 発行から常に 75 日後

<details>
<summary>答えを表示</summary>

**答え: A) 実際の有効期間の約 3 分の 2 が経過した時点**

既定では、実際の X.509 有効期間の 3 分の 2 が経過した時点で更新されます。75 日目になるのは、実際に 90 日有効な証明書に `renewBefore: 360h` を設定した場合だけです。`renewBefore` と `renewBeforePercentage` を同時に設定してはいけません。1.21 の renewal policy/window や、サポートされる ARI 経路によって予定が変わる場合があります。`status.renewalTime` を確認してください。

</details>

<span id="_9-what-is-the-role-of-istio-csr-in-cert-manager-s-istio-integration"></span>

### 9. Istio sidecar の証明書発行経路について正しい説明はどれですか?

- A) Envoy が CA private key で署名する
- B) istio-agent → istio-csr → CertificateRequest/Issuer の順に処理し、SDS が Envoy に素材を渡す
- C) 同じ Pod 内の接続はすべて自動的に mTLS になる
- D) `rootCAFile` の path を指定すれば実際の CA file を mount しなくてよい

<details>
<summary>答えを表示</summary>

**答え: B) istio-agent → istio-csr → CertificateRequest/Issuer の順に処理し、SDS が Envoy に素材を渡す**

istio-agent が CSR を作成し、istio-csr が cert-manager による発行へ接続します。peer-proxy 間の mTLS と、ローカル application hop は別のものです。実際の trust-root mount、利用可能な Issuer、Istio external-CA 設定が必要です。別方式である Kubernetes CSR RA mode と混同しないでください。

</details>

<span id="_10-what-is-a-key-difference-between-cert-manager-and-aws-certificate-manager-acm"></span>

### 10. 現在の ACM と cert-manager の動作について正しい説明はどれですか?

- A) ACM certificate は Pod やオンプレミスで一切使えない
- B) ALB は Kubernetes TLS Secret を直接読む
- C) ACM exportable certificate は明示的な export に対応し、ACM ACME には別のライフサイクルと制約がある
- D) server URL だけ変更すれば ACM ACME 登録が完了する

<details>
<summary>答えを表示</summary>

**答え: C) ACM exportable certificate は明示的な export に対応し、ACM ACME には別のライフサイクルと制約がある**

ACK ACM export には `options.export:ENABLED`、`exportTo`、出力 Secret、別途の domain validation が必要です。ACM ACME には事前検証済み domain/EAB が必要で、key と renewal は client 側で管理します。45 日証明書を、管理対象の ALB/CloudFront/API Gateway integration に直接関連付けることはできません。cert-manager は Kubernetes Secret と複数の Issuer を調整しますが、controller、trust、CA の費用については運用者が責任を持ちます。

</details>

## スコア計算

- 9～10 問正解: 十分に理解できています。
- 7～8 問正解: 間違えた発行/信頼経路を復習してください。
- 6 問以下正解: ガイドと例を見直してください。

## 関連ドキュメント

- [cert-manager による証明書管理](../../security/10-cert-manager.md)
