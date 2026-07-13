# Pod Security Standards クイズ

このクイズでは、Pod Security Standards (PSS)、Pod Security Admission (PSA)、およびセキュリティプロファイルについての理解を確認します。

## クイズ問題

### 1. Pod Security Standards (PSS) の3つのセキュリティレベルに含まれないものはどれですか？

A. Privileged
B. Baseline
C. Hardened
D. Restricted

<details>
<summary>回答を表示</summary>

**回答: C. Hardened**

**解説:**
Pod Security Standards は3つのセキュリティレベルを定義しています:
- **Privileged**: 制限なし、最大限の権限を許可
- **Baseline**: 既知の権限昇格を防止し、制限は最小限
- **Restricted**: 強化されたセキュリティで、Pod のハードニングのベストプラクティスを適用

Hardened は正式な PSS セキュリティレベルではありません。

</details>

### 2. ポリシー違反が発生したときに Pod の作成をブロックする Pod Security Admission (PSA) モードはどれですか？

A. audit
B. warn
C. enforce
D. deny

<details>
<summary>回答を表示</summary>

**回答: C. enforce**

**解説:**
PSA は3つのモードを提供します:
- **enforce**: ポリシー違反時に Pod の作成を拒否
- **audit**: 違反を監査ログに記録するが許可
- **warn**: ユーザーに警告メッセージを表示するが許可

deny は有効な PSA モードではありません。

</details>

### 3. PSS を namespace に適用するために使用するラベル形式はどれですか？

A. security.kubernetes.io/enforce: restricted
B. pod-security.kubernetes.io/enforce: restricted
C. pss.kubernetes.io/level: restricted
D. admission.kubernetes.io/policy: restricted

<details>
<summary>回答を表示</summary>

**回答: B. pod-security.kubernetes.io/enforce: restricted**

**解説:**
PSA は namespace ラベルを通じて設定します:
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

ラベル形式: `pod-security.kubernetes.io/<MODE>: <LEVEL>`

</details>

### 4. Baseline セキュリティレベルで許可されないものはどれですか？

A. hostNetwork: true
B. runAsNonRoot: false
C. allowPrivilegeEscalation: true
D. readOnlyRootFilesystem: false

<details>
<summary>回答を表示</summary>

**回答: A. hostNetwork: true**

**解説:**
Baseline レベルは既知の権限昇格を防止します。以下は禁止されています:
- hostNetwork, hostPID, hostIPC
- privileged containers
- 危険な capabilities (NET_RAW 以外は追加不可)
- hostPath volumes (特定のパスを除く)

runAsNonRoot、allowPrivilegeEscalation、readOnlyRootFilesystem は Baseline では制限されません。これらは Restricted レベルで強制されます。

</details>

### 5. Restricted セキュリティレベルの要件ではないものはどれですか？

A. runAsNonRoot: true
B. allowPrivilegeEscalation: false
C. readOnlyRootFilesystem: true
D. capabilities.drop: ["ALL"]

<details>
<summary>回答を表示</summary>

**回答: C. readOnlyRootFilesystem: true**

**解説:**
Restricted レベルでは以下が必要です:
- runAsNonRoot: true (必須)
- allowPrivilegeEscalation: false (必須)
- capabilities.drop: ["ALL"] (必須)
- seccompProfile.type: RuntimeDefault or Localhost (必須)

readOnlyRootFilesystem はセキュリティのベストプラクティスですが、Restricted レベルの必須要件ではありません。

</details>

### 6. PodSecurityPolicy (PSP) が削除されたのはどの Kubernetes バージョンですか？

A. 1.21
B. 1.23
C. 1.25
D. 1.27

<details>
<summary>回答を表示</summary>

**回答: C. 1.25**

**解説:**
PSP のタイムライン:
- Kubernetes 1.21: PSP の非推奨化が発表
- Kubernetes 1.22: PSA alpha が導入
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP が完全に削除され、PSA GA

</details>

### 7. PSA で PSS の特定バージョンを適用するラベルはどれですか？

A. pod-security.kubernetes.io/enforce-version: v1.28
B. pod-security.kubernetes.io/version: v1.28
C. pod-security.kubernetes.io/enforce-version: 1.28
D. pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>回答を表示</summary>

**回答: A. pod-security.kubernetes.io/enforce-version: v1.28**

**解説:**
バージョンラベルの形式:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

バージョン値は `v1.XX` 形式または `latest` を使用します。バージョンを指定すると、その Kubernetes バージョンの PSS 定義が使用されます。

</details>

### 8. EKS で PSA を有効にするにはどうしますか？

A. EKS add-on をインストールする必要がある
B. デフォルトで有効
C. eksctl command で有効化
D. AWS console で設定

<details>
<summary>回答を表示</summary>

**回答: B. デフォルトで有効**

**解説:**
Pod Security Admission は Kubernetes 1.25 以降でデフォルトで有効です。EKS 1.25 以降のバージョンでは、追加設定なしで PSA を使用できます。必要なのは、namespace に適切なラベルを追加することだけです。

</details>

### 9. PSA exemptions を設定する方法ではないものはどれですか？

A. RuntimeClass exemption
B. User exemption
C. Namespace exemption
D. Pod label exemption

<details>
<summary>回答を表示</summary>

**回答: D. Pod label exemption**

**解説:**
PSA は次の exemption タイプをサポートします:
- **usernames**: 特定ユーザーの exemptions
- **runtimeClassNames**: 特定 RuntimeClasses の exemptions
- **namespaces**: 特定 namespaces の exemptions

Pod ラベルベースの exemptions は PSA ではサポートされていません。Exemptions は AdmissionConfiguration を通じて設定されます。

</details>

### 10. Restricted レベルで許可される seccompProfile タイプはどれですか？

A. Unconfined
B. RuntimeDefault
C. Custom
D. Disabled

<details>
<summary>回答を表示</summary>

**回答: B. RuntimeDefault**

**解説:**
Restricted レベルで許可される seccompProfile タイプ:
- **RuntimeDefault**: Container runtime のデフォルトプロファイル
- **Localhost**: node 上で定義されたカスタムプロファイル

Unconfined は Restricted レベルでは許可されません。これは seccomp フィルタリングを無効にし、セキュリティリスクをもたらします。

</details>

### 11. PSP から PSA に移行する際に推奨される最初のステップは何ですか？

A. PSP をすぐに削除する
B. すべての namespaces に enforce モードを適用する
C. 違反を特定するために audit/warn モードから始める
D. 新しい cluster を作成する

<details>
<summary>回答を表示</summary>

**回答: C. 違反を特定するために audit/warn モードから始める**

**解説:**
推奨される PSA 移行手順:
1. **audit/warn モードから始める**: 違反を特定
2. **workloads を修正**: 違反を解消
3. **enforce モードに切り替える**: 段階的に適用
4. **PSP を削除**: 移行完了後

enforce モードをすぐに適用すると、既存の workloads に影響を与える可能性があります。

</details>

### 12. Privileged レベルでも制限されるものは何ですか？

A. hostNetwork usage
B. privileged containers
C. なし (すべて許可される)
D. hostPath volumes

<details>
<summary>回答を表示</summary>

**回答: C. なし (すべて許可される)**

**解説:**
Privileged レベルは完全に制限がありません:
- すべての security context 設定が許可
- hostNetwork, hostPID, hostIPC が許可
- privileged containers が許可
- すべての capabilities が許可
- すべての volume タイプが許可

このレベルは、システムおよびインフラストラクチャ workloads (例: CNI、storage drivers) に使用されます。

</details>
