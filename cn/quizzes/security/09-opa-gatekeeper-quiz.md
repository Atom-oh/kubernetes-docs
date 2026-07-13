# OPA Gatekeeper 测验

通过以下问题测试你对 OPA Gatekeeper 和 Rego 策略语言的理解。

***

## 问题

### 1. 在 OPA Gatekeeper 中使用哪种语言编写策略？

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>显示答案</summary>

**答案：C) Rego**

**解释：** OPA (Open Policy Agent) 使用一种名为 Rego 的声明式策略语言。Rego 针对查询 JSON/YAML 数据和进行策略决策进行了优化。

```rego
package kubernetes.admission

violation[{"msg": msg}] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}
```

与 Kyverno 不同，你需要学习一门新语言，但它允许表达更复杂的策略逻辑。

</details>

***

### 2. Gatekeeper 中哪个 CRD 定义可复用的策略模板？

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>显示答案</summary>

**答案：B) ConstraintTemplate**

**解释：** ConstraintTemplate 定义 Rego 策略逻辑和参数 schema：

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

Constraints 基于 ConstraintTemplates 创建，用于应用实际策略。

</details>

***

### 3. Gatekeeper Constraint 的 enforcementAction 字段不支持哪个值？

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>显示答案</summary>

**答案：D) audit**

**解释：** Gatekeeper 支持的 enforcementAction 值：

* **deny**：在策略违规时拒绝请求
* **dryrun**：记录违规但允许请求
* **warn**：显示警告消息，允许请求

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

audit 不是 enforcementAction，而是 Gatekeeper 的后台审计功能。

</details>

***

### 4. 在 Rego 中遍历数组所有元素的语法是什么？

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>显示答案</summary>

**答案：C) item := array\[\_]**

**解释：** 在 Rego 中，`[_]` 表示数组的所有索引：

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

这种语法是在规则中评估多个值时使用的核心 Rego 模式。

</details>

***

### 5. Gatekeeper 中哪个功能会检查现有集群资源的策略合规性？

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>显示答案</summary>

**答案：C) Audit**

**解释：** Gatekeeper Audit 功能：

* 定期检查现有资源
* 在 Constraint 状态中记录违规
* 验证现有资源，而不仅仅是新资源

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

这可以在应用策略之前了解其影响。

</details>

***

### 6. Gatekeeper v3.10+ 中用于自动修改资源的 CRD 是什么？

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>显示答案</summary>

**答案：B) Assign / AssignMetadata**

**解释：** Gatekeeper 的 Mutation CRDs：

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

类似于 Kyverno 的 mutate 功能。

</details>

***

### 7. Rego 中哪个运算符用于计算两个集合之间的差集？

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>显示答案</summary>

**答案：C) - (minus)**

**解释：** Rego 集合操作：

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

这些操作经常用于必需 label 验证。

</details>

***

### 8. 在 Gatekeeper 中引用其他 namespaces 的资源需要什么配置？

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>显示答案</summary>

**答案：B) Config's sync.syncOnly**

**解释：** 要让 Gatekeeper 引用外部数据，需要通过 Config 资源进行 sync 配置：

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

同步后的资源可以在 Rego 中通过 `data.inventory` 访问：

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

**答案：C) gator**

**解释：** Gator 是用于在本地测试 Gatekeeper 策略的官方 CLI 工具：

```bash
# Install
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# Validate policies
gator verify ./policies/

# Run test suite
gator test ./tests/
```

测试套件示例：

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

### 10. 在比较 Gatekeeper 和 Kyverno 时，Gatekeeper 的优势是什么？

* A) 学习曲线更低
* B) YAML 原生策略
* C) 资源生成功能
* D) 复杂策略逻辑表达能力

<details>

<summary>显示答案</summary>

**答案：D) 复杂策略逻辑表达能力**

**解释：** Gatekeeper (OPA) 与 Kyverno 对比：

| Feature             | Gatekeeper         | Kyverno   |
| ------------------- | ------------------ | --------- |
| Policy Language     | Rego               | YAML      |
| Learning Curve      | High               | Low       |
| Complex Logic       | Very Flexible      | Limited   |
| Resource Generation | Not Supported      | Supported |
| External Data       | OPA Bundle Support | API Call  |

Gatekeeper 借助 Rego 的灵活性，更容易处理：

* 复杂条件组合
* 递归数据结构处理
* 高级集合操作
* 外部数据集成

</details>

***

### 11. 当 Rego 中定义了多个 violation 规则时，它们如何被评估？

* A) 只评估第一条规则
* B) 所有规则按 OR 进行评估
* C) 所有规则按 AND 进行评估
* D) 随机选择一条规则

<details>

<summary>显示答案</summary>

**答案：B) 所有规则按 OR 进行评估**

**解释：** 在 Rego 中，多个同名规则会按 OR 进行评估：

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

每条 violation 规则的结果都会添加到一个集合中，如果存在一个或多个违规，则整体策略失败。

</details>

***

### 12. Gatekeeper 中哪个字段配置 Constraint 仅应用于特定 namespaces？

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>显示答案</summary>

**答案：B) spec.match.namespaces**

**解释：** Constraint 的 match 部分指定应用范围：

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

* `namespaces`：要包含的 namespaces 列表
* `excludedNamespaces`：要排除的 namespaces 列表
* `namespaceSelector`：基于 label 的选择

</details>

***

## 分数计算

每题计 1 分。

| 分数 | 评级                                                  |
| ----- | ------------------------------------------------------- |
| 11-12 | 优秀 - OPA Gatekeeper 专家级别                 |
| 8-10  | 良好 - 已理解基本概念，需要深入学习 Rego |
| 5-7   | 一般 - 建议继续学习                  |
| 0-4   | 需要基础学习                                   |

***

## 相关文档

* [OPA Gatekeeper](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/09-opa-gatekeeper.md)
* [Kyverno 策略管理](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/01-kyverno-policy-management.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
