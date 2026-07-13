# cert-manager クイズ

以下の問題で、cert-manager と Kubernetes certificate management に関する理解を確認しましょう。

---

## 問題

### 1. CNCF における cert-manager のプロジェクトステータスは何ですか？

- A) Sandbox project
- B) Incubating project
- C) Graduated project
- D) Archived project

<details>
<summary>答えを表示</summary>

**回答: C) Graduated project**

**解説:**
cert-manager は 2022 年 11 月に CNCF Graduated status を達成し、Kubernetes 向けの最も成熟し、広く採用されている certificate management solution の 1 つになりました。このステータスは、このプロジェクトが governance、security、community adoption に関する厳格な要件を満たしたことを示します。

</details>

---

### 2. cert-manager で Certificate resources を監視し、certificate issuance をトリガーする component はどれですか？

- A) cainjector
- B) webhook
- C) controller
- D) acmesolver

<details>
<summary>答えを表示</summary>

**回答: C) controller**

**解説:**
cert-manager は 3 つの core components で構成されています。
- **controller**: Certificate resources を監視し、certificate lifecycle を管理し、issuance/renewal をトリガーします
- **webhook**: admission webhooks 経由で cert-manager resources を検証および変更します
- **cainjector**: ValidatingWebhookConfiguration、MutatingWebhookConfiguration、CRD conversion webhooks に CA bundles を注入します

</details>

---

### 3. Issuer と ClusterIssuer resources の主な違いは何ですか？

- A) Issuer はより多くの certificate types をサポートする
- B) ClusterIssuer は namespace-scoped で、Issuer は cluster-scoped である
- C) Issuer は namespace-scoped で、ClusterIssuer は cluster-scoped である
- D) ClusterIssuer は ACME でのみ動作する

<details>
<summary>答えを表示</summary>

**回答: C) Issuer は namespace-scoped で、ClusterIssuer は cluster-scoped である**

**解説:**
```yaml
# Issuer - only issues certificates in its namespace
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-prod
  namespace: my-app  # Only works in this namespace

# ClusterIssuer - issues certificates across all namespaces
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # No namespace - cluster-wide
```

組織全体の certificate policies には ClusterIssuer を使用し、namespace 固有の configurations には Issuer を使用します。

</details>

---

### 4. wildcard certificate issuance をサポートする ACME challenge type はどれですか？

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) HTTP-01 と DNS-01 の両方

<details>
<summary>答えを表示</summary>

**回答: B) DNS-01**

**解説:**
ACME challenge types とその capabilities:
- **HTTP-01**: HTTP endpoint (port 80) 経由で domain control を証明します。wildcards はサポートしません。
- **DNS-01**: DNS TXT records 経由で domain control を証明します。wildcard certificates (*.example.com) をサポートします。
- **TLS-ALPN-01**: TLS (port 443) 経由で domain control を証明します。wildcards はサポートしません。

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
spec:
  acme:
    solvers:
    - dns01:
        route53:
          region: us-east-1
      selector:
        dnsNames:
        - "*.example.com"  # Wildcard requires DNS-01
```

</details>

---

### 5. Certificate resource で secretName field は何を指定しますか？

- A) Issuer secret の名前
- B) issued certificate が保存される Kubernetes Secret
- C) CA certificate secret
- D) ACME account secret

<details>
<summary>答えを表示</summary>

**回答: B) issued certificate が保存される Kubernetes Secret**

**解説:**
secretName field は、cert-manager が issued certificate を保存する場所を指定します。

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-app-tls
  namespace: my-app
spec:
  secretName: my-app-tls-cert  # Certificate stored here
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - my-app.example.com
```

生成される Secret には次が含まれます。
- `tls.crt`: certificate chain
- `tls.key`: private key
- `ca.crt`: CA certificate (利用可能な場合)

</details>

---

### 6. AWS Private CA Issuer の主な use case は何ですか？

- A) 無料の public certificates
- B) private/enterprise certificates 向けの internal PKI
- C) DNS-01 challenge automation
- D) Certificate revocation

<details>
<summary>答えを表示</summary>

**回答: B) private/enterprise certificates 向けの internal PKI**

**解説:**
AWS Private CA (PCA) Issuer は、cert-manager を AWS Certificate Manager Private Certificate Authority と統合します。

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: aws-pca-issuer
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789:certificate-authority/abc-123
  region: us-east-1
```

ユースケース:
- Internal microservice mTLS
- Enterprise PKI compliance requirements
- public internet に公開されない private certificates
- 既存の AWS PCA infrastructure との統合

</details>

---

### 7. cert-manager ecosystem で trust-manager は何をしますか？

- A) certificate signatures を検証する
- B) CA bundles を namespaces 全体に ConfigMaps または Secrets として配布する
- C) ACME account registration を管理する
- D) certificate revocation を処理する

<details>
<summary>答えを表示</summary>

**回答: B) CA bundles を namespaces 全体に ConfigMaps または Secrets として配布する**

**解説:**
trust-manager は、trusted CA certificates を配布する cert-manager sub-project です。

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: my-ca-bundle
spec:
  sources:
  - useDefaultCAs: true           # Include system CAs
  - secret:
      name: "internal-ca"
      key: "ca.crt"
  target:
    configMap:
      key: "ca-certificates.crt"
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled     # Distribute to labeled namespaces
```

これにより、すべての application namespaces で一貫した CA trust が確保されます。

</details>

---

### 8. Certificate resource の renewBefore field は何を制御しますか？

- A) minimum validity period
- B) expiry のどれくらい前に cert-manager が renewal を開始するか
- C) maximum renewal attempts
- D) renewal check interval

<details>
<summary>答えを表示</summary>

**回答: B) expiry のどれくらい前に cert-manager が renewal を開始するか**

**解説:**
renewBefore field は、cert-manager が renewal process を開始するタイミングを指定します。

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
spec:
  secretName: my-cert
  duration: 2160h    # 90 days validity
  renewBefore: 360h  # Renew 15 days before expiry
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
```

これらの設定では次のようになります。
- Certificate は 90 日間有効
- renewal は 75 日目に開始されます (90 - 15 = 75)
- renewal failures に備えた buffer を提供します

</details>

---

### 9. cert-manager の Istio integration における istio-csr の role は何ですか？

- A) Istio configurations を検証する
- B) cert-manager を使用して Istio service mesh 向けの workload certificates を発行する
- C) Istio gateway certificates のみを管理する
- D) clusters 間で certificates を同期する

<details>
<summary>答えを表示</summary>

**回答: B) cert-manager を使用して Istio service mesh 向けの workload certificates を発行する**

**解説:**
istio-csr は、workload identity のために Istio の built-in CA (istiod) を cert-manager に置き換えます。

```yaml
# istio-csr issues certificates for:
# - Workload mTLS (pod-to-pod)
# - Service mesh identity (SPIFFE)

# Configuration example
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: istiod
  namespace: istio-system
spec:
  secretName: istiod-tls
  issuerRef:
    name: istio-ca
    kind: ClusterIssuer
  isCA: true
```

メリット:
- 集中管理された PKI management
- mesh と ingress 全体で一貫した certificate policies
- external CAs (Vault, AWS PCA) との統合

</details>

---

### 10. cert-manager と AWS Certificate Manager (ACM) の主な違いは何ですか？

- A) ACM はより多くの issuers をサポートする
- B) cert-manager は EKS 上でしか実行できない
- C) cert-manager は certificates を Kubernetes Secrets として提供し、ACM はそれらを AWS に保存する
- D) ACM はより多くの certificate types をサポートする

<details>
<summary>答えを表示</summary>

**回答: C) cert-manager は certificates を Kubernetes Secrets として提供し、ACM はそれらを AWS に保存する**

**解説:**
cert-manager と AWS ACM の比較:

| Feature | cert-manager | AWS ACM |
|---------|--------------|---------|
| Storage | Kubernetes Secrets | AWS-managed |
| Private Key Access | Yes (in Secret) | No (AWS-only) |
| Use with Pods | Direct mounting | Not possible |
| Ingress Integration | Any ingress controller | ALB/NLB only |
| Multi-cloud | Yes | AWS only |
| Issuers | ACME, Vault, PCA, self-signed | Amazon, PCA |

次のような場合は cert-manager を使用します。
- Pods 内で certificates が必要な場合
- Multi-cloud portability が必要な場合
- Custom issuers が必要な場合
- private keys を細かく制御する必要がある場合

</details>

---

## スコア計算

- **9-10 正解**: 優秀 - cert-manager について深く理解しています。
- **7-8 正解**: 良好 - 主要な concepts をしっかり把握しています。
- **5-6 正解**: 普通 - 追加学習が必要な areas があります。
- **4 以下**: documentation をもう一度確認してください。

## 関連ドキュメント

- [cert-manager による Certificate Management](../../security/10-cert-manager.md)
