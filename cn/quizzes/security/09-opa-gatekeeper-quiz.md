# OPA Gatekeeper 测验

> **最后更新**: September 13, 2026

通过以下问题测试您对 OPA Gatekeeper 和 Rego 策略语言的理解。

***

## 问题

### 1. OPA Gatekeeper 使用什么语言编写策略？

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>显示答案</summary>

**答案: C) Rego**

**说明：** OPA（Open Policy Agent）使用一种名为 Rego 的声明式策略语言。Rego 针对查询 JSON/YAML 数据和作出策略决策进行了优化。

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

学习 Rego 集合、推导式和输入契约，然后根据您的需求和测试选择策略引擎。

</details>

***

### 2. 哪个 CRD 在 Gatekeeper 中定义可复用的策略模板？

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>显示答案</summary>

**答案: B) ConstraintTemplate**

**说明：** ConstraintTemplate 定义 Rego 策略逻辑和参数 schema：

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

基于 ConstraintTemplate 创建 Constraint，以应用实际策略。

</details>

***

### 3. Gatekeeper Constraint 的 enforcementAction 字段不支持以下哪个值？

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>显示答案</summary>

**答案: D) audit**

**说明：** Gatekeeper 支持的 enforcementAction 值：

* **deny**：策略违规时拒绝请求
* **dryrun**：记录违规，但允许请求
* **warn**：显示警告消息，允许请求

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

audit 并非 enforcementAction，而是 Gatekeeper 的后台 Audit 功能。

</details>

***

### 4. 在 Rego 中遍历数组所有元素的语法是什么？

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>显示答案</summary>

**答案: C) item := array\[\_]**

**说明：** 在 Rego 中，`[_]` 表示数组的所有索引：

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

在规则中评估多个值时，此语法是核心 Rego 模式。

</details>

***

### 5. Gatekeeper 中哪个功能检查现有集群资源的策略合规性？

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>显示答案</summary>

**答案: C) Audit**

**说明：** Gatekeeper Audit 功能：

* 定期检查现有资源
* 在 Constraint status 中记录违规
* 验证现有资源，而不仅仅是新资源

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

这使您能够在应用策略之前了解其影响。

</details>

***

<span id="_6-what-crd-is-used-for-automatic-resource-modification-in-gatekeeper-v3-10"></span>

### 6. Gatekeeper 3.23.1 中使用哪个 CRD 进行自动资源修改？

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>显示答案</summary>

**答案: B) Assign / AssignMetadata**

**说明：** Gatekeeper 的 Mutation CRD：

* **AssignMetadata**：添加 metadata（labels、annotations）
* **Assign**：修改 spec 等通用字段
* **ModifySet**：从数组中添加/移除值

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

与 Kyverno 的 mutate 功能类似。

</details>

***

### 7. Rego 中哪个运算符计算两个集合之间的差集？

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>显示答案</summary>

**答案: C) - (minus)**

**说明：** Rego 集合操作：

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

这些操作常用于必需 label 验证。

</details>

***

### 8. Gatekeeper 中需要什么配置才能引用其他 namespace 中的资源？

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>显示答案</summary>

**答案: B) Config's sync.syncOnly**

**说明：** 此示例将 Kubernetes 对象同步到 inventory；它不会自动连接外部 HTTP provider 或任意 bundle：

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

可通过 Rego 中的 `data.inventory` 访问已同步的资源：

```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

***

### 9. 用于测试 Gatekeeper 策略的官方 CLI 工具是什么？

* A) opa test
* B) gatekeeper-cli
* C) gator
* D) conftest

<details>

<summary>显示答案</summary>

**答案: C) gator**

**说明：** Gator 是在本地测试 Gatekeeper 策略的官方 CLI 工具：

```bash
# Install
gator version  # verified 3.23.1 release binary

# Validate policies
gator verify tests/suite.yaml --verbose

# Run test suite
gator test -f templates/ -f constraints/ -f tests/fixtures/labels-present.yaml --output=json
```

测试套件示例：

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

### 10. 哪项具体需求可能促使您选择 Rego 策略？

* A) 保证每个策略的内存使用量都更低
* B) 无需检查即可自动生成每种资源
* C) 始终处理比其他引擎更复杂的逻辑
* D) 对 JSON 输入应用集合操作和推导式，并通过测试验证它们

<details>
<summary>显示答案</summary>

**答案: D) 对 JSON 输入应用集合操作和推导式，并通过测试验证它们**

**说明：** Rego 为此需求提供声明式操作。应比较实际策略表达、团队技能、测试和运行需求，而不是断言其在性能或复杂度上具有普遍优势。

</details>

***

### 11. 在 Rego 中定义多个 violation 规则时，它们如何被评估？

* A) 仅评估第一个规则
* B) 所有规则均按 OR 评估
* C) 所有规则均按 AND 评估
* D) 随机选择其中一个

<details>

<summary>显示答案</summary>

**答案: B) 所有规则均按 OR 评估**

**说明：** 此 partial-set violation 规则的多个定义会将其结果贡献给同一个集合：

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

每个 violation 规则的结果都会添加到一个集合中；如果存在一个或多个违规，整体策略即失败。

这些 partial-set violation 规则会贡献给同一个集合。每个 body 内部的条件均为 AND；发生冲突的 complete-document 规则不会通过 OR 解决。此片段并非完整的 PSS 实现。

</details>

***

### 12. Gatekeeper 中哪个字段将 Constraint 配置为仅应用于特定 namespace？

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>显示答案</summary>

**答案: B) spec.match.namespaces**

**说明：** Constraint 的 match 部分指定应用范围：

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

* `namespaces`：要包含的 namespace 列表
* `excludedNamespaces`：要排除的 namespace 列表
* `namespaceSelector`：基于 label 的选择

</details>

***

## 分数计算

每题 1 分。

| 分数 | 评级                                                  |
| ----- | ------------------------------------------------------- |
| 11-12 | 优秀 - OPA Gatekeeper 专家级别                 |
| 8-10  | 良好 - 已理解基本概念，需要深入学习 Rego |
| 5-7   | 一般 - 建议进一步学习                  |
| 0-4   | 需要基础学习                                   |

***

## 相关文档

* [OPA Gatekeeper](../../security/09-opa-gatekeeper.md)
* [Kyverno 策略管理](01-kyverno-policy-management-quiz.md)
* [Pod 安全标准](03-pod-security-standards-quiz.md)
