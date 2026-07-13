# Secrets 管理クイズ

このクイズでは、Kubernetes Secrets、AWS Secrets Manager、External Secrets Operator、および暗号化についての理解を確認します。

## クイズ問題

### 1. Kubernetes Secrets のデフォルトのエンコーディング方式は何ですか？

A. AES-256 暗号化
B. Base64 エンコーディング
C. SHA-256 ハッシュ
D. RSA 暗号化

<details>
<summary>解答を表示</summary>

**解答: B. Base64 エンコーディング**

**解説:**
Kubernetes Secrets はデフォルトで Base64 エンコードされます。Base64 は単純なエンコーディングであり、暗号化ではないため、etcd 暗号化を有効にするか、外部の secrets 管理システムを使用する必要があります。

</details>

### 2. EKS で etcd 暗号化に使用される AWS service はどれですか？

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>解答を表示</summary>

**解答: B. AWS KMS (Key Management Service)**

**解説:**
EKS は AWS KMS を使用して、etcd に保存される Kubernetes Secrets を暗号化します。エンベロープ暗号化は、cluster の作成時または作成後に有効化できます:
```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

</details>

### 3. External Secrets Operator で AWS Secrets Manager の secrets を参照する resources はどれですか？

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A と B、または C と B

<details>
<summary>解答を表示</summary>

**解答: D. A と B、または C と B**

**解説:**
External Secrets Operator の components:
- **SecretStore/ClusterSecretStore**: 外部 secret store の接続設定
- **ExternalSecret**: 実際の secret 参照と Kubernetes Secret の作成

SecretStore は namespace スコープ、ClusterSecretStore は cluster スコープです。

</details>

### 4. Pod で Secrets を使用する方法ではないものはどれですか？

A. environment variables として注入する
B. volumes としてマウントする
C. image pull secrets
D. ConfigMap に変換する

<details>
<summary>解答を表示</summary>

**解答: D. ConfigMap に変換する**

**解説:**
Pod で Secrets を使用する方法:
1. **Environment variables**: `envFrom.secretRef` または `env.valueFrom.secretKeyRef`
2. **Volume mount**: ファイルとしてマウントする
3. **Image pull secrets**: `imagePullSecrets`

Secrets は自動的に ConfigMaps に変換されません。これらは別々の resources です。

</details>

### 5. AWS Secrets Manager で automatic rotation を設定するために使用される AWS service はどれですか？

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>解答を表示</summary>

**解答: B. AWS Lambda**

**解説:**
AWS Secrets Manager の automatic rotation は Lambda functions を使用します。AWS は RDS、Redshift など向けに事前構築済みの rotation functions を提供しており、custom rotation も Lambda で実装できます。

</details>

### 6. Sealed Secrets の主な特徴は何ですか？

A. etcd 内での暗号化
B. Git に安全に保存できる
C. AWS 専用
D. automatic rotation のサポート

<details>
<summary>解答を表示</summary>

**解答: B. Git に安全に保存できる**

**解説:**
Sealed Secrets は public key で secrets を暗号化するため、Git repositories に安全に保存できます。cluster 内の Sealed Secrets controller だけが private key で復号できます。GitOps workflows に適しています。

</details>

### 7. ExternalSecret の refreshInterval field の役割は何ですか？

A. secret の有効期限を設定する
B. external secret との同期間隔を設定する
C. cache の保持時間を設定する
D. retry interval を設定する

<details>
<summary>解答を表示</summary>

**解答: B. external secret との同期間隔を設定する**

**解説:**
`refreshInterval` は External Secrets Operator が external secret store と同期する頻度を定義します:
```yaml
spec:
  refreshInterval: 1h  # Sync every 1 hour
```

secrets が外部で変更されると、この間隔に従って Kubernetes Secret が更新されます。

</details>

### 8. Kubernetes Secret の immutable field が true に設定されるとどうなりますか？

A. Secret を削除できなくなる
B. Secret を変更できなくなる
C. Secret を読み取れなくなる
D. Secret をコピーできなくなる

<details>
<summary>解答を表示</summary>

**解答: B. Secret を変更できなくなる**

**解説:**
`immutable: true` 設定は、Secret が作成された後の変更を防ぎます:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
immutable: true
data:
  password: cGFzc3dvcmQ=
```

変更するには、Secret を削除して再作成する必要があります。これにより、偶発的な変更を防ぎ、performance が向上します。

</details>

### 9. CSI Secrets Store Driver の主な機能は何ですか？

A. etcd 内の secrets を暗号化する
B. external secrets を volumes としてマウントする
C. secrets を自動生成する
D. secrets をバックアップする

<details>
<summary>解答を表示</summary>

**解答: B. external secrets を volumes としてマウントする**

**解説:**
Secrets Store CSI Driver は、AWS Secrets Manager、Azure Key Vault などの external secrets を CSI volumes として直接マウントします。Pods は Kubernetes Secrets を作成せずに secrets を使用できます。

</details>

### 10. External Secrets で IRSA (IAM Roles for Service Accounts) を使用する利点は何ですか？

A. secret へのアクセスが高速になる
B. Pods に IAM credentials をハードコードする必要がない
C. automatic secret rotation
D. 無料で使用できる

<details>
<summary>解答を表示</summary>

**解答: B. Pods に IAM credentials をハードコードする必要がない**

**解説:**
IRSA により、Service Accounts に IAM roles を関連付けることができます。External Secrets Operator Pods は AWS credentials なしで AWS Secrets Manager に安全にアクセスできます。これは security best practice です。

</details>

### 11. stringData で Secret data を定義する特徴は何ですか？

A. 暗号化される
B. Base64 エンコーディングが不要
C. より安全である
D. 圧縮される

<details>
<summary>解答を表示</summary>

**解答: B. Base64 エンコーディングが不要**

**解説:**
`stringData` field では、値を plain text で指定できます:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:
  password: mypassword  # Plain text, auto Base64 encoded
```

Kubernetes が自動的に Base64 エンコーディングを処理します。ただし、query すると data field では Base64 として表示されます。

</details>

### 12. secrets 管理の best practice ではないものはどれですか？

A. etcd 暗号化を有効にする
B. RBAC で Secret access を制限する
C. secrets を source code に commit する
D. external secrets management system を使用する

<details>
<summary>解答を表示</summary>

**解答: C. secrets を source code に commit する**

**解説:**
Secrets 管理の best practices:
- etcd 暗号化を有効にする
- RBAC で Secret access を制限する
- external secrets management systems (AWS Secrets Manager、HashiCorp Vault など) を使用する
- audit logging を有効にする
- 定期的な secret rotation

secrets を source code に commit してはいけません。plain text secrets は version control systems で公開されてしまいます。

</details>
