# Pod Security Standards クイズ

> **最終更新**: September 13, 2026
> **関連ドキュメント**: [Pod Security Standards](../../security/03-pod-security-standards.md)

通常の Linux Pod に対して回答してください。バージョン固有の Windows および user namespace の例外についてはガイドを参照してください。

このクイズでは、Pod Security Standards（PSS）、Pod Security Admission（PSA）、およびセキュリティプロファイルに関する理解を確認します。

## クイズ問題

### 1. Pod Security Standards（PSS）の 3 つのセキュリティレベルのうち、該当しないものはどれですか？

- A) Privileged
- B) Baseline
- C) Hardened
- D) Restricted

<details>
<summary>回答を表示</summary>

**回答: C) Hardened**

**解説:**
Pod Security Standards は 3 つのセキュリティレベルを定義しています。
- **Privileged**: 制限なし、最大限の権限を許可
- **Baseline**: 既知の権限昇格を防止し、最小限の制限を適用
- **Restricted**: 強化されたセキュリティで、Pod のハードニングのベストプラクティスを適用

Hardened は公式の PSS セキュリティレベルではありません。

</details>

### 2. ポリシー違反が発生したときに Pod の作成をブロックする Pod Security Admission（PSA）モードはどれですか？

- A) audit
- B) warn
- C) enforce
- D) deny

<details>
<summary>回答を表示</summary>

**回答: C) enforce**

**解説:**
PSA には 3 つのモードがあります。
- **enforce**: ポリシー違反時に Pod の作成を拒否
- **audit**: 監査ログに違反を記録するが、許可する
- **warn**: ユーザーに警告メッセージを表示するが、許可する

deny は有効な PSA モードではありません。audit/warn 自体は拒否しませんが、enforce または他のチェックにより同じリクエストが拒否される場合があります。監査ログの保持には適切なログ設定が必要です。

</details>

### 3. namespace に PSS を適用するために使用するラベル形式はどれですか？

- A) security.kubernetes.io/enforce: restricted
- B) pod-security.kubernetes.io/enforce: restricted
- C) pss.kubernetes.io/level: restricted
- D) admission.kubernetes.io/policy: restricted

<details>
<summary>回答を表示</summary>

**回答: B) pod-security.kubernetes.io/enforce: restricted**

**解説:**
PSA は namespace ラベルで設定します。
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

- A) hostNetwork: true
- B) runAsNonRoot: false
- C) allowPrivilegeEscalation: true
- D) readOnlyRootFilesystem: false

<details>
<summary>回答を表示</summary>

**回答: A) hostNetwork: true**

**解説:**
Baseline レベルは既知の権限昇格を防止します。以下は禁止されています。
- hostNetwork、hostPID、hostIPC
- privileged コンテナ
- NET_RAW を含む、Baseline の許可リスト外の明示的な capability の追加
- すべての hostPath volume。組み込みの PSA にはパスの許可リストはありません

Baseline では runAsNonRoot や allowPrivilegeEscalation: false は必須ではありません。Restricted では、想定される Pod タイプに対してこれらの制御が追加されます。readOnlyRootFilesystem は推奨されるハードニングですが、どちらのプロファイルでも要件ではありません。capability のチェックは明示的な追加に関するものであり、runtime のデフォルトセットを削除するものではありません。

</details>

### 5. Restricted セキュリティレベルの要件ではないものはどれですか？

- A) runAsNonRoot: true
- B) allowPrivilegeEscalation: false
- C) readOnlyRootFilesystem: true
- D) capabilities.drop: ["ALL"]

<details>
<summary>回答を表示</summary>

**回答: C) readOnlyRootFilesystem: true**

**解説:**
Restricted レベルでは以下が必要です。
- runAsNonRoot: true（必須）
- allowPrivilegeEscalation: false（必須）
- capabilities.drop: ["ALL"]（必須）
- seccompProfile.type: RuntimeDefault または Localhost（必須）

readOnlyRootFilesystem はセキュリティのベストプラクティスですが、Restricted レベルの必須要件ではありません。

</details>

### 6. PodSecurityPolicy（PSP）はどの Kubernetes バージョンで削除されましたか？

- A) 1.21
- B) 1.23
- C) 1.25
- D) 1.27

<details>
<summary>回答を表示</summary>

**回答: C) 1.25**

**解説:**
PSP のタイムライン:
- Kubernetes 1.21: PSP の非推奨化を発表
- Kubernetes 1.22: PSA alpha を導入
- Kubernetes 1.23: PSA beta
- Kubernetes 1.25: PSP を完全に削除、PSA GA

</details>

### 7. PSA で特定バージョンの PSS を適用するラベルはどれですか？

- A) pod-security.kubernetes.io/enforce-version: v1.28
- B) pod-security.kubernetes.io/version: v1.28
- C) pod-security.kubernetes.io/enforce-version: 1.28
- D) pod-security.kubernetes.io/policy-version: 1.28

<details>
<summary>回答を表示</summary>

**回答: A) pod-security.kubernetes.io/enforce-version: v1.28**

**解説:**
バージョンラベルの形式:
```yaml
pod-security.kubernetes.io/<MODE>-version: <VERSION>
```

値には `v1.XX` または `latest` を使用します。固定指定はポリシー定義を選択するものであり、Kubernetes のアップグレードではありません。v1.28 の選択は構文例であり、後に導入された制御は含まれません。latest は API server のバージョンに追従するため、アップグレード時に変更される可能性があります。

</details>

### 8. EKS で PSA を有効にするにはどうしますか？

- A) EKS add-on をインストールする必要がある
- B) デフォルトで有効
- C) eksctl コマンドで有効化する
- D) AWS console で設定する

<details>
<summary>回答を表示</summary>

**回答: B) デフォルトで有効**

**解説:**
PSA は GA に到達し、upstream Kubernetes 1.25+ ではデフォルトで有効です。AWS は EKS でのデフォルト有効化を 1.23 から文書化しており、permissive な privileged/latest のデフォルトと静的な exemption がないことを示しています。実際の namespace ラベルを確認してください。有効化だけで Baseline/Restricted の enforcement が提供されると想定するのではなく、適切なポリシーを追加してください。

</details>

### 9. PSA exemption の設定方法ではないものはどれですか？

- A) RuntimeClass exemption
- B) User exemption
- C) Namespace exemption
- D) Pod label exemption

<details>
<summary>回答を表示</summary>

**回答: D) Pod label exemption**

**解説:**
PSA は以下の exemption タイプをサポートしています。
- **usernames**: 特定のユーザーに対する exemption
- **runtimeClasses**: 特定の RuntimeClass に対する exemption
- **namespaces**: 特定の namespace に対する exemption

Pod ラベルによって exemption は作成されません。静的 exemption エントリは完全一致の名前であり、wildcard や group selector ではありません。User exemption は spec.serviceAccountName ではなく、リクエストの identity と照合されます。EKS ではこの control-plane 設定の編集は公開されていません。privileged な namespace enforcement を選択することは、静的 exemption とは異なります。

</details>

### 10. Restricted レベルで許可される seccompProfile タイプはどれですか？

- A) Unconfined
- B) RuntimeDefault
- C) Custom
- D) Disabled

<details>
<summary>回答を表示</summary>

**回答: B) RuntimeDefault**

**解説:**
Restricted レベルで許可される seccompProfile タイプ:
- **RuntimeDefault**: Container runtime のデフォルトプロファイル
- **Localhost**: node 上で定義されたカスタムプロファイル

Unconfined は Restricted レベルでは許可されません。seccomp filtering を無効にするため、セキュリティリスクがあります。

</details>

### 11. PSP から PSA への移行時に推奨される最初の手順は何ですか？

- A) 直ちに PSP を削除する
- B) すべての namespace に enforce モードを適用する
- C) 違反を特定するために audit/warn モードから開始する
- D) 新しい cluster を作成する

<details>
<summary>回答を表示</summary>

**回答: C) 違反を特定するために audit/warn モードから開始する**

**解説:**
推奨される PSA 移行手順:
1. **audit/warn モードから開始**: 違反を特定する
2. **workload を修正**: 違反を解決する
3. **enforce モードに切り替え**: 段階的に適用する
4. **PSP を削除**: 移行完了後

すでに実行中の Pod は、ラベルを再設定しただけでは eviction されません。その置き換えや関連する更新は拒否される可能性があるため、後の rollout が停止することがあります。この PSP 削除シーケンスは、v1.25 より前に PSP を提供していた cluster にとっての歴史的なものです。

</details>

<span id="_12-what-is-restricted-even-in-the-privileged-level"></span>

### 12. PSS Privileged プロファイル自体が禁止しているものはどれですか？

- A) hostNetwork の使用
- B) privileged コンテナ
- C) PSS 自体によるこれらのいずれもなし
- D) hostPath volume

<details>
<summary>回答を表示</summary>

**回答: C) PSS 自体によるこれらのいずれもなし**

**解説:**
Privileged は、これらの有効な Pod フィールドに PSS の制限を追加しません。
- すべての security context 設定を許可
- hostNetwork、hostPID、hostIPC を許可
- privileged コンテナを許可
- すべての capability を許可
- すべての volume タイプを許可

これは IAM/RBAC の権限を付与するものでも、schema validation やその他の admission policy を回避するものでも、privileged: true を強制するものでもありません。そのような namespace は、レビュー済みの host-access component に限定してください。

</details>
