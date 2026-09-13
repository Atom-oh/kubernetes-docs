# OPA Gatekeeper クイズ

> **最終更新**: September 13, 2026

以下の質問で、OPA Gatekeeper と Rego ポリシー言語についての理解を確認しましょう。

***

## 問題

### 1. OPA Gatekeeper でポリシーを記述するために使用される言語は何ですか？

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>回答を表示</summary>

**回答: C) Rego**

**解説:** OPA (Open Policy Agent) は、Rego という宣言型ポリシー言語を使用します。Rego は JSON/YAML データのクエリとポリシー判断に最適化されています。

```rego
package docsrequiredlabels
valid_label(key) if {
  value := input.review.object.metadata.labels[key]
  is_string(value)
  value != ""
}
violation contains {"msg": sprintf("required nonempty label: %v", [key])} if {
  some key in input.parameters.labels
  not valid_label(key)
}
```

Rego のセット、内包表記、入力コントラクトを学び、その後に要件とテストに照らしてポリシーエンジンを選択してください。

</details>

***

### 2. Gatekeeper で再利用可能なポリシーテンプレートを定義する CRD はどれですか？

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>回答を表示</summary>

**回答: B) ConstraintTemplate**

**解説:** ConstraintTemplate は Rego ポリシーロジックとパラメータスキーマを定義します。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: docsrequiredlabels
spec:
  crd:
    spec:
      names:
        kind: DocsRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              minItems: 1
              items:
                type: string
                minLength: 1
          required:
          - labels
  targets:
  - target: admission.k8s.gatekeeper.sh
    code:
    - engine: Rego
      source:
        version: v1
        rego: |
          package docsrequiredlabels
          valid_label(key) if {
            value := input.review.object.metadata.labels[key]
            is_string(value)
            value != ""
          }
          violation contains {"msg": sprintf("required nonempty label: %v", [key])} if {
            some key in input.parameters.labels
            not valid_label(key)
          }
```

実際のポリシーを適用するため、Constraint は ConstraintTemplate に基づいて作成されます。

</details>

***

### 3. Gatekeeper Constraint の enforcementAction フィールドでサポートされていない値はどれですか？

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>回答を表示</summary>

**回答: D) audit**

**解説:** Gatekeeper でサポートされる enforcementAction の値:

* **deny**: ポリシー違反時にリクエストを拒否する
* **dryrun**: 違反を記録するが、リクエストは許可する
* **warn**: 警告メッセージを表示し、リクエストを許可する

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: DocsRequiredLabels
metadata:
  name: required-labels
spec:
  enforcementAction: deny
  match:
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
    namespaces:
    - policy-lab
  parameters:
    labels:
    - app.kubernetes.io/name
```

audit は enforcementAction ではなく、Gatekeeper のバックグラウンド監査機能です。

</details>

***

### 4. Rego で配列のすべての要素を反復処理する構文はどれですか？

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>回答を表示</summary>

**回答: C) item := array\[\_]**

**解説:** Rego では、`[_]` は配列のすべてのインデックスを意味します。

```rego
# Iterate all containers
container := input.review.object.spec.containers[_]

# Iterate all label keys
key := object.keys(input.review.object.metadata.labels)[_]

# Specific index
first_container := input.review.object.spec.containers[0]

# When both index and value are needed
some i
container := input.review.object.spec.containers[i]
```

この構文は、ルール内で複数の値を評価するときに使用される Rego の中核的なパターンです。

</details>

***

### 5. Gatekeeper で既存のクラスターリソースのポリシー準拠を確認する機能は何ですか？

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>回答を表示</summary>

**回答: C) Audit**

**解説:** Gatekeeper Audit 機能:

* 既存リソースを定期的に検査する
* Constraint ステータスに違反を記録する
* 新規リソースだけでなく既存リソースも検証する

```bash
# Check violations in Constraint
kubectl describe docsrequiredlabels required-labels

# Check violations in Status section:
# Status:
#   Audit Timestamp: 2026-02-21T10:00:00Z
#   Total Violations: 3
#   Violations:
#     - Kind: Pod
#       Name: nginx-without-labels
#       Namespace: default
```

これにより、ポリシーを適用する前に影響を把握できます。

</details>

***

<span id="_6-what-crd-is-used-for-automatic-resource-modification-in-gatekeeper-v3-10"></span>

### 6. Gatekeeper 3.23.1 で自動リソース変更に使用される CRD はどれですか？

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>回答を表示</summary>

**回答: B) Assign / AssignMetadata**

**解説:** Gatekeeper の Mutation CRD:

* **AssignMetadata**: メタデータ（ラベル、アノテーション）を追加する
* **Assign**: spec のような一般フィールドを変更する
* **ModifySet**: 配列の値を追加または削除する

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: AssignMetadata
metadata:
  name: add-owner-label
spec:
  match:
    scope: Namespaced
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  location: "metadata.labels.owner"
  parameters:
    assign:
      value: "platform-team"
```

Kyverno の mutate 機能に似ています。

</details>

***

### 7. Rego で 2 つのセットの差分を計算する演算子はどれですか？

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>回答を表示</summary>

**回答: C) - (minus)**

**解説:** Rego のセット演算:

```rego
# Compare required and existing labels
required := {"app", "env", "team"}
provided := {"app", "team"}

# Set difference: find missing labels
missing := required - provided
# Result: {"env"}

# Intersection
common := required & provided
# Result: {"app", "team"}

# Union
all := required | provided
```

これらの演算は、必須ラベルの検証で頻繁に使用されます。

</details>

***

### 8. 他の Namespace のリソースを参照するために Gatekeeper で必要な設定は何ですか？

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>回答を表示</summary>

**回答: B) Config's sync.syncOnly**

**解説:** この例は Kubernetes オブジェクトを inventory に同期します。外部 HTTP プロバイダーや任意のバンドルへ自動的に接続するものではありません。

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
      - group: ""
        version: "v1"
        kind: "Namespace"
      - group: "networking.k8s.io"
        version: "v1"
        kind: "Ingress"
```

同期されたリソースには、Rego で `data.inventory` を介してアクセスできます。

```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

***

### 9. Gatekeeper ポリシーをテストする公式 CLI ツールは何ですか？

* A) opa test
* B) gatekeeper-cli
* C) gator
* D) conftest

<details>

<summary>回答を表示</summary>

**回答: C) gator**

**解説:** Gator は Gatekeeper ポリシーをローカルでテストするための公式 CLI ツールです。

```bash
# Install
gator version  # verified 3.23.1 release binary

# Validate policies
gator verify tests/suite.yaml --verbose

# Run test suite
gator test -f templates/ -f constraints/ -f tests/fixtures/labels-present.yaml --output=json
```

テストスイートの例:

```yaml
apiVersion: test.gatekeeper.sh/v1alpha1
kind: Suite
metadata:
  name: docs-gatekeeper
tests:
- name: required-labels
  template: ../templates/docsrequiredlabels.yaml
  constraint: ../constraints/required-labels.yaml
  cases:
  - name: labels-present
    object: fixtures/labels-present.yaml
    assertions:
    - violations: 0
  - name: labels-absent
    object: fixtures/labels-absent.yaml
    assertions:
    - violations: 1
```

</details>

***

<span id="_10-what-is-gatekeeper-s-advantage-when-comparing-gatekeeper-and-kyverno"></span>

### 10. Rego ポリシーを選択する動機となり得る具体的な要件はどれですか？

* A) すべてのポリシーで必ずメモリ使用量が少なくなる
* B) チェックなしですべてのリソースを自動生成する
* C) 常に他のエンジンより複雑なロジックを処理する
* D) JSON 入力にセット演算と内包表記を適用し、テストで検証する

<details>
<summary>回答を表示</summary>

**回答: D) JSON 入力にセット演算と内包表記を適用し、テストで検証する**

**解説:** Rego はこの要件に対する宣言型の演算を提供します。普遍的なパフォーマンスや複雑性の優位性を主張するのではなく、実際のポリシー表現、チームのスキル、テスト、運用上のニーズを比較してください。

</details>

***

### 11. Rego で複数の violation ルールが定義されている場合、どのように評価されますか？

* A) 最初のルールのみ評価される
* B) すべてのルールが OR として評価される
* C) すべてのルールが AND として評価される
* D) 1 つがランダムに選択される

<details>

<summary>回答を表示</summary>

**回答: B) すべてのルールが OR として評価される**

**解説:** この部分セット violation ルールの複数の定義は、同じセットに結果を追加します。

```rego
package examples
violation contains {"msg": "Privileged container"} if {
  container := input.review.object.spec.containers[_]
  container.securityContext.privileged == true
}
violation contains {"msg": "Explicit root user"} if {
  container := input.review.object.spec.containers[_]
  container.securityContext.runAsUser == 0
}
```

各 violation ルールの結果はセットに追加され、1 つ以上の違反がある場合、ポリシー全体は失敗します。

これらの部分セット violation ルールは同じセットに寄与します。各本体内の条件は AND です。競合する完全ドキュメントルールが OR によって解決されるわけではありません。この断片は完全な PSS 実装ではありません。

</details>

***

### 12. Constraint を特定の Namespace にのみ適用するよう Gatekeeper で設定するフィールドはどれですか？

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>回答を表示</summary>

**回答: B) spec.match.namespaces**

**解説:** Constraint の match セクションは適用範囲を指定します。

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: DocsRequiredLabels
metadata:
  name: required-labels
spec:
  enforcementAction: deny
  match:
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
    namespaces:
    - production
    - staging
  parameters:
    labels:
    - app.kubernetes.io/name
```

* `namespaces`: 含める Namespace のリスト
* `excludedNamespaces`: 除外する Namespace のリスト
* `namespaceSelector`: ラベルベースの選択

</details>

***

## スコア計算

各問題を 1 点として計算します。

| Score | Rating                                                  |
| ----- | ------------------------------------------------------- |
| 11-12 | 優秀 - OPA Gatekeeper のエキスパートレベル              |
| 8-10  | 良好 - 基本概念は理解済み、Rego の詳細学習が必要        |
| 5-7   | 平均 - 追加学習を推奨                                   |
| 0-4   | 基本的な学習が必要                                      |

***

## 関連ドキュメント

* [OPA Gatekeeper](../../security/09-opa-gatekeeper.md)
* [Kyverno ポリシー管理](01-kyverno-policy-management-quiz.md)
* [Pod Security Standards](03-pod-security-standards-quiz.md)
