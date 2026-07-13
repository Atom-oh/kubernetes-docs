# OPA Gatekeeper クイズ

以下の問題で、OPA Gatekeeper と Rego policy language に関する理解を確認しましょう。

***

## 問題

### 1. OPA Gatekeeper で policy を記述するために使用される言語は何ですか？

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>答えを表示</summary>

**回答: C) Rego**

**解説:** OPA (Open Policy Agent) は Rego と呼ばれる宣言的な policy language を使用します。Rego は JSON/YAML data の照会と policy decision のために最適化されています。

```rego
package kubernetes.admission

violation[{"msg": msg}] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}
```

Kyverno とは異なり、新しい言語を学ぶ必要がありますが、より複雑な policy logic を表現できます。

</details>

***

### 2. Gatekeeper で再利用可能な policy template を定義する CRD は何ですか？

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>答えを表示</summary>

**回答: B) ConstraintTemplate**

**解説:** ConstraintTemplate は Rego policy logic と parameter schema を定義します。

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg}] {
            # Rego policy logic
        }
```

ConstraintTemplate に基づいて Constraint が作成され、実際の policy を適用します。

</details>

***

### 3. Gatekeeper Constraint の enforcementAction field でサポートされていない値はどれですか？

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>答えを表示</summary>

**回答: D) audit**

**解説:** Gatekeeper がサポートする enforcementAction の値は次のとおりです。

* **deny**: policy violation 時に request を拒否する
* **dryrun**: violation を記録するが request は許可する
* **warn**: warning message を表示し、request を許可する

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels
spec:
  enforcementAction: deny  # or dryrun, warn
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

audit は enforcementAction ではなく、Gatekeeper の background audit 機能です。

</details>

***

### 4. Rego で配列のすべての要素を反復処理する構文は何ですか？

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>答えを表示</summary>

**回答: C) item := array\[\_]**

**解説:** Rego では、`[_]` は配列のすべての index を意味します。

```rego
# Iterate all containers
container := input.request.object.spec.containers[_]

# Iterate all label keys
label := input.request.object.metadata.labels[_]

# Specific index
first_container := input.request.object.spec.containers[0]

# When both index and value are needed
some i
container := input.request.object.spec.containers[i]
```

この構文は、rule 内で複数の値を評価する際に使用される中核的な Rego pattern です。

</details>

***

### 5. Gatekeeper で既存の cluster resource の policy compliance を確認する機能は何ですか？

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>答えを表示</summary>

**回答: C) Audit**

**解説:** Gatekeeper Audit 機能:

* 既存の resource を定期的に検査する
* Constraint status に violation を記録する
* 新規 resource だけでなく、既存の resource も検証する

```bash
# Check violations in Constraint
kubectl describe k8srequiredlabels require-labels

# Check violations in Status section:
# Status:
#   Audit Timestamp: 2026-02-21T10:00:00Z
#   Total Violations: 3
#   Violations:
#     - Kind: Pod
#       Name: nginx-without-labels
#       Namespace: default
```

これにより、policy を適用する前に影響を把握できます。

</details>

***

### 6. Gatekeeper v3.10+ で自動的な resource modification に使用される CRD は何ですか？

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>答えを表示</summary>

**回答: B) Assign / AssignMetadata**

**解説:** Gatekeeper の Mutation CRD:

* **AssignMetadata**: metadata (labels, annotations) を追加する
* **Assign**: spec などの一般的な field を変更する
* **ModifySet**: 配列から値を追加/削除する

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

### 7. Rego で 2 つの set の差分を計算する operator は何ですか？

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>答えを表示</summary>

**回答: C) - (minus)**

**解説:** Rego の set operation:

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

これらの operation は、required label validation で頻繁に使用されます。

</details>

***

### 8. Gatekeeper で他の namespace の resource を参照するために必要な設定は何ですか？

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>答えを表示</summary>

**回答: B) Config's sync.syncOnly**

**解説:** Gatekeeper が external data を参照するには、Config resource による sync configuration が必要です。

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

同期された resource は Rego で `data.inventory` を介してアクセスできます。

```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

***

### 9. Gatekeeper policy をテストするための公式 CLI tool は何ですか？

* A) opa test
* B) gatekeeper-cli
* C) gator
* D) conftest

<details>

<summary>答えを表示</summary>

**回答: C) gator**

**解説:** Gator は Gatekeeper policy をローカルでテストするための公式 CLI tool です。

```bash
# Install
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# Validate policies
gator verify ./policies/

# Run test suite
gator test ./tests/
```

Test suite の例:

```yaml
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
metadata:
  name: required-labels-test
tests:
  - name: "Pod without labels should fail"
    template: ../templates/k8srequiredlabels.yaml
    constraint: ../constraints/require-labels.yaml
    cases:
      - name: pod-without-labels
        object: fixtures/pod-no-labels.yaml
        assertions:
          - violations: yes
```

</details>

***

### 10. Gatekeeper と Kyverno を比較したときの Gatekeeper の利点は何ですか？

* A) Learning curve が低い
* B) YAML native policies
* C) Resource generation feature
* D) Complex policy logic expressiveness

<details>

<summary>答えを表示</summary>

**回答: D) Complex policy logic expressiveness**

**解説:** Gatekeeper (OPA) と Kyverno の比較:

| Feature             | Gatekeeper         | Kyverno   |
| ------------------- | ------------------ | --------- |
| Policy Language     | Rego               | YAML      |
| Learning Curve      | High               | Low       |
| Complex Logic       | Very Flexible      | Limited   |
| Resource Generation | Not Supported      | Supported |
| External Data       | OPA Bundle Support | API Call  |

Gatekeeper は Rego による柔軟性により、次の処理が容易です。

* 複雑な条件の組み合わせ
* 再帰的な data structure の処理
* 高度な set operation
* external data integration

</details>

***

### 11. Rego で複数の violation rule が定義されている場合、それらはどのように評価されますか？

* A) 最初の rule のみが評価される
* B) すべての rule が OR として評価される
* C) すべての rule が AND として評価される
* D) 1 つがランダムに選択される

<details>

<summary>答えを表示</summary>

**回答: B) すべての rule が OR として評価される**

**解説:** Rego では、同じ名前の複数の rule は OR として評価されます。

```rego
# Rule 1: Check privileged containers
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers not allowed"
}

# Rule 2: Check root execution
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := "Running as root not allowed"
}

# Violation occurs if either rule is violated
```

各 violation rule の結果は set に追加され、1 つ以上の violation がある場合、policy 全体が失敗します。

</details>

***

### 12. Gatekeeper で Constraint を特定の namespace のみに適用するよう設定する field は何ですか？

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>答えを表示</summary>

**回答: B) spec.match.namespaces**

**解説:** Constraint の match section は適用範囲を指定します。

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-prod
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
      - staging
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
    namespaceSelector:
      matchLabels:
        environment: production
```

* `namespaces`: 含める namespace の list
* `excludedNamespaces`: 除外する namespace の list
* `namespaceSelector`: label-based selection

</details>

***

## スコア計算

各問題 1 点で計算してください。

| スコア | 評価                                                    |
| ------ | ------------------------------------------------------- |
| 11-12  | 優秀 - OPA Gatekeeper expert level                      |
| 8-10   | 良好 - Basic concepts understood, Rego deep dive needed |
| 5-7    | 普通 - Additional study recommended                     |
| 0-4    | 基礎学習が必要                                          |

***

## 関連ドキュメント

* [OPA Gatekeeper](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/09-opa-gatekeeper.md)
* [Kyverno Policy Management](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/01-kyverno-policy-management.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
