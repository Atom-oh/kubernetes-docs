# Kyverno 策略管理测验

> **最后更新**：2026年9月13日

这些题目基于已审查的 Kyverno 1.19.1 CEL 策略。示例均为本地测试夹具；未执行任何集群操作或破坏性清理。

## 测验题目

### 1. 什么是 Kyverno？

- A) 一种 Kubernetes 策略引擎，可执行准入控制，并由单独配置的后台和生命周期控制器处理相应任务。
- B) 仅是一种漏洞扫描器。
- C) API 服务器身份验证的替代方案。
- D) 一种服务网格数据平面。

<details>
<summary>显示答案</summary>

**答案: A) 一种 Kubernetes 策略引擎，可执行准入控制，并由单独配置的后台和生命周期控制器处理相应任务。**

Kyverno 策略可在配置的作用范围内验证、变更和生成资源，验证镜像或删除资源。当前 v1 策略在 YAML/JSON 中使用 CEL；旧式 ClusterPolicy 写法和 JMESPath 属于不同语言。采用 Kubernetes 原生方式打包，并不意味着无需学习策略表达式。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_2-which-of-the-following-is-not-a-policy-type-supported-by-kyverno"></span>

### 2. 哪项陈述正确区分了策略操作？

- A) 每个策略仅在准入阶段运行，且绝不会更改其他对象。
- B) Audit 会使生成和删除变为只读。
- C) 所有 GET/list 请求都会被准入 Webhook 拦截。
- D) 验证、变更、资源生成和定时删除分别由不同的控制器、配置和权限管理。

<details>
<summary>显示答案</summary>

**答案: D) 验证、变更、资源生成和定时删除分别由不同的控制器、配置和权限管理。**

Kubernetes 身份验证（例如 OIDC 或 ServiceAccount 令牌）和授权（RBAC）与准入策略相互独立；Authenticate 不是 Kyverno 策略操作。DeletingPolicy 按计划和条件执行；ClusterPolicy 中的 cleanup.ttl 规则不是该 API。即使另一条验证策略处于 Audit 模式，变更、生成和删除操作仍可能修改资源。请明确限定实验范围、配置所需 RBAC，并制定恢复计划。下面的可选删除定义仅用于理解 schema；它未实际应用，也不实现“对象年龄超过 24 小时”的阈值。

```yaml
apiVersion: policies.kyverno.io/v1
kind: DeletingPolicy
metadata:
  name: cleanup-lab-completed-pods
spec:
  schedule: 0 1 * * *
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      scope: Namespaced
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: policy-lab
  conditions:
  - name: explicitly-approved-completed
    expression: object.metadata.?labels['training.example.com/disposable'].orValue('') == 'true' && object.?status.phase.orValue('')
      in ['Succeeded', 'Failed']
```

</details>

### 3. 在当前 ValidatingPolicy 中，validationActions: [Audit] 和 [Deny] 有何不同？

- A) 两者始终拒绝匹配到的违规。
- B) Audit 允许报告匹配到的违规；Deny 会在匹配请求的准入阶段拒绝违规操作。
- C) Audit 会删除现有的违规对象。
- D) Deny 会自动重写资源。

<details>
<summary>显示答案</summary>

**答案: B) Audit 允许报告匹配到的违规；Deny 会在准入请求匹配到该策略时拒绝违规资源。**

Webhook 的 failurePolicy 用于处理评估或传输失败，与验证动作相互独立。本地 CLI 返回失败只表示检测到策略违规，并不能证明 Audit 策略拒绝了集群中的实时请求。在旧版 API 中，Enforce 和 Audit 失败动作使用不同的字段名；迁移时应仔细核对。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-container-limits
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, has(c.resources) && has(c.resources.limits) && ['cpu', 'memory'].all(k, k in c.resources.limits
      && string(c.resources.limits[k]) != ''))
    message: Normal and init containers need nonempty CPU and memory limits.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([])
```

</details>

<span id="_4-what-field-is-used-in-kyverno-to-select-which-resources-a-policy-applies-to"></span>

### 4. 如何选择 CEL ValidatingPolicy 的资源范围？

- A) 只需指定顶层目标字符串。
- B) 使用 matchConstraints 和可选的 matchConditions，并检查资源类型、操作类型、命名空间及请求数据是否可用。
- C) 每个策略都会自动匹配所有 Kubernetes 资源。
- D) 只用 metadata.name 作为选择条件。

<details>
<summary>显示答案</summary>

**答案: B) 使用 matchConstraints 和可选的 matchConditions，并检查资源类型、操作类型、命名空间及请求数据是否可用。**

传统 ClusterPolicy 使用规则的匹配/排除结构；这与当前 CEL 字段布局不同。资源和用户条件必须按表达式理解，不能简单假定为 OR/AND 关系。准入请求中的用户或角色信息不一定能在后台扫描时获取。命名空间标签选择器也受有权修改该标签的主体控制。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

</details>

<span id="_5-which-policy-type-in-kyverno-automatically-modifies-resources-on-policy-violation"></span>

### 5. 为什么这种资源默认值变更能保留已有配置？

- A) 它会用相同的资源限制覆盖所有容器。
- B) 在 CREATE 时，它只为尚未设置任何资源配置的普通容器填入默认值，并保留已有的完整或部分配置。
- C) 它会把第一个容器的值复制给其他所有容器。
- D) 它会在 Kyverno 表达式中使用 Helm 的 if/hasKey 语句。

<details>
<summary>显示答案</summary>

**答案: B) 在 CREATE 时，它只为尚未设置任何资源配置的普通容器填入默认值，并保留已有的完整或部分配置。**

我们将实际 CLI 输出与资源配置完整和部分缺失的输入对象进行了比较，结果均未改变。部分配置仍需单独审查；不要创建高于现有限制值的请求值。ApplyConfiguration 与 JSONPatch 的语义不同；JSONPatch 要求父路径已存在，而且不同策略的执行顺序没有保证。

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: default-unset-resources
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        Object{spec: Object.spec{containers: object.spec.containers.map(c,
          (!has(c.resources) || ((!has(c.resources.requests) || c.resources.requests.size() == 0) &&
            (!has(c.resources.limits) || c.resources.limits.size() == 0)))
          ? Object.spec.containers{name: c.name, resources: Object.spec.containers.resources{
              requests: {"cpu": "250m", "memory": "256Mi"},
              limits: {"cpu": "500m", "memory": "512Mi"}
            }}
          : Object.spec.containers{name: c.name}
        )}}
```

</details>

### 6. GeneratingPolicy 何时有用？

- A) 根据匹配到的触发事件创建明确指定的下游资源，并拥有所需权限。
- B) 自动备份每个被删除的资源。
- C) 在创建时原子性地保证命名空间隔离。
- D) 绕过后台控制器的 RBAC 权限检查。

<details>
<summary>显示答案</summary>

**答案: A) 根据匹配到的触发事件创建明确指定的下游资源，并拥有所需权限。**

此 Deployment 示例需要显式启用，并要求期望副本数至少为 2；生成的资源会复制完整的 spec.selector。生成操作可能异步完成。同步、数据源与克隆源、既有资源生成及孤儿资源处理设置都会影响后续更新或删除行为。在源与目标范围均获批准前，不要将 registry Secret 克隆到任何新命名空间。

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-pdb
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - deployments
  matchConditions:
  - name: approved-deployment
    expression: object.metadata.namespace == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true' && object.spec.?replicas.orValue(1) >= 2
  generate:
  - expression: |-
      generator.Apply(object.metadata.namespace, [{
        "apiVersion": dyn("policy/v1"), "kind": dyn("PodDisruptionBudget"),
        "metadata": dyn({"name": object.metadata.name + "-pdb", "namespace": object.metadata.namespace}),
        "spec": dyn({"minAvailable": 1, "selector": object.spec.selector})
      }])
```

</details>

<span id="_7-what-policy-type-is-used-in-kyverno-to-verify-container-image-signatures"></span>

### 7. 哪种当前 Kyverno 类型用于验证容器镜像签名和证明材料？

- A) ResourceQuota。
- B) ImageValidatingPolicy。
- C) ServiceMonitor。
- D) LimitRange。

<details>
<summary>显示答案</summary>

**答案: B) ImageValidatingPolicy。**

旧版 ClusterPolicy 的 verifyImages 规则与新的清单类型不同。请按照镜像安全指南配置受支持的 Cosign 或 Notary/Notation 信任验证路径、准确的签名者/签发者/密钥规则，以及注册表访问权限。任意 GPG 或 Docker Content Trust 材料都不能直接替代这些配置。签名验证不等于漏洞扫描，也不会自动构成注册表允许列表。若配置了 digest mutation，策略可能会改写镜像引用；本章未执行任何注册表或签名操作。

[镜像安全指南](../../security/07-image-security.md)

</details>

<span id="_8-what-does-the-background-false-setting-mean-in-a-kyverno-policy"></span>

### 8. 禁用后台验证扫描意味着什么？

- A) 该验证设置不会定期扫描现有资源，但仍会检查符合条件的准入更新。
- B) 所有现有资源都将永久免于准入检查。
- C) 此设置会停止所有 Kyverno 控制器。
- D) 现有策略违规会被删除。

<details>
<summary>显示答案</summary>

**答案: A) 该验证设置不会定期扫描现有资源，但仍会检查符合条件的准入更新。**

当前类型使用 spec.evaluation.background.enabled；传统 ClusterPolicy 使用 background。二者都不是变更既有资源、生成资源或清理操作的全局开关。后台报告本身不会修复、拒绝或删除已存储的资源。准入操作类型和匹配条件仍决定哪些更新会被检查。

</details>

### 9. 哪种 PolicyReport 表示形式是正确的？

- A) 包含 resource 和 status 字段，但汇总计数与结果无关。
- B) PolicyReport 中包含资源和结果条目，汇总计数与这些条目一致。
- C) 每份报告都必须将 timestamp.created 写成字符串。
- D) ClusterPolicyReport 表示对所有命名空间报告进行任意聚合。

<details>
<summary>显示答案</summary>

**答案: B) PolicyReport 中包含资源和结果条目，汇总计数与这些条目一致。**

默认 Helm Chart 配置使用 Policy WG 报告。PolicyReport 按命名空间作用域生成，ClusterPolicyReport 则涵盖集群作用域的资源。这是合成的 schema 示例，并非现场收集的证据。示例时间戳使用整数秒和纳秒。其他报告后端必须另行验证。

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: example-report
  namespace: policy-lab
summary:
  pass: 1
  fail: 1
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: good
    namespace: policy-lab
  result: pass
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: missing-label
    namespace: policy-lab
  result: fail
  message: A nonempty team label is required.
```

</details>

<span id="_10-what-command-line-tool-can-be-used-to-test-policies-in-kyverno"></span>

### 10. 应如何在本地测试这些 Kyverno 策略？

- A) 运行 kyverno apply --cluster 来安装所有策略。
- B) 使用 kyverno test 和测试清单目录，或使用 kyverno apply 和本地资源文件。
- C) 运行并不存在的通用 kyverno validate 命令。
- D) Helm 成功渲染即可证明策略行为和 RBAC 配置正确。

<details>
<summary>显示答案</summary>

**答案: B) 使用 kyverno test 和测试清单目录，或使用 kyverno apply 和本地资源文件。**

指南中的 policy-lab-tests 包含预期通过和预期失败的输入。kyverno test --require-tests 可防止空测试目录被误认为有效测试。kyverno apply 用于评估资源；--cluster 会读取选定集群以辅助评估，并非安装策略。--output 接受用于保存变更或生成对象的路径。支持的辅助资源可使用 create 子命令；不要臆造 create disallow-latest-tag template 命令。

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[返回指南](../../security/01-kyverno-policy-management.md)
