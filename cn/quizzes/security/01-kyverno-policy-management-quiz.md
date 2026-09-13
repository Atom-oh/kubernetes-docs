# Kyverno 策略管理测验

> **最后更新**: September 13, 2026

这些问题使用经过审查的 Kyverno 1.19.1 CEL 策略。示例为本地 fixture；未执行集群操作或破坏性清理。

## 测验题目

### 1. 什么是 Kyverno？

- A) 一种 Kubernetes 策略引擎，具有 admission 以及单独配置的 background/lifecycle controller。
- B) 仅是一种漏洞扫描器。
- C) API-server authentication 的替代方案。
- D) 一种 service mesh dataplane。

<details>
<summary>显示答案</summary>

**答案: A) 一种 Kubernetes 策略引擎，具有 admission 以及单独配置的 background/lifecycle controller。**

Kyverno 策略可在其配置的范围内执行验证、变更、生成、镜像验证和删除。当前 v1 策略在 YAML/JSON 中使用 CEL；旧版 ClusterPolicy 模式和 JMESPath 是不同的语言。Kubernetes 原生打包并不能免除学习策略表达式的需要。

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

- A) 每个策略仅在 admission 时运行，且绝不会更改其他对象。
- B) Audit 会使生成和删除变为只读。
- C) 所有 GET/list 请求都会被 admission webhook 拦截。
- D) 验证、变更、生成和计划删除具有不同的 controller、设置和权限。

<details>
<summary>显示答案</summary>

**答案: D) 验证、变更、生成和计划删除具有不同的 controller、设置和权限。**

Kubernetes authentication（例如 OIDC 或 ServiceAccount token）和 authorization（RBAC）与 admission 策略相互独立；Authenticate 不是 Kyverno 策略操作。DeletingPolicy 使用 schedule 和 condition；带有 cleanup.ttl 的 ClusterPolicy rule 不是它的 API。即使无关的验证策略处于 Audit，变更/生成/删除仍可能更改资源。请使用明确的 lab selector、所需的 RBAC 和恢复计划。以下可选删除定义用于理解 schema；它未被应用，也未实现 24 小时的时限阈值。

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
- B) Audit 允许匹配到的违规以便报告；Deny 会在匹配的 admission 期间拒绝它们。
- C) Audit 会删除现有的违规对象。
- D) Deny 会自动重写资源。

<details>
<summary>显示答案</summary>

**答案: B) Audit 允许匹配到的违规以便报告；Deny 会在匹配的 admission 期间拒绝它们。**

Webhook failurePolicy 处理评估/传输失败，与此相互独立。本地 CLI 的失败结果记录的是策略违规，并不能证明 Audit 策略拒绝了实时请求。在旧版 API 中，Enforce/Audit failure action 使用不同的字段名；请审慎迁移。

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

- A) 顶层 target string 已足够。
- B) 使用 matchConstraints 和可选的 matchConditions；检查 kind、operation、namespace 和 request-data 可用性。
- C) 每个策略都会自动匹配所有 Kubernetes 资源。
- D) 仅使用 metadata.name 作为 selector。

<details>
<summary>显示答案</summary>

**答案: B) 使用 matchConstraints 和可选的 matchConditions；检查 kind、operation、namespace 和 request-data 可用性。**

经典 ClusterPolicy 使用 rule match/exclude 结构；它们不是当前的 CEL 字段布局。必须将资源和用户 condition 理解为表达式，而不能假定 OR/AND 简写。来自 admission 的用户/role 信息不一定会在 background scan 中提供。namespace label selector 也受能够更改该 label 的主体控制。

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

### 5. 是什么使这种资源默认值变更对现有值安全？

- A) 它会用相同的 limit 覆盖每个 container。
- B) 在 CREATE 时，它仅填充完全未设置的 normal-container resource，并保留现有完整或部分设置。
- C) 它会将第一个 container 的值复制到其他每个 container。
- D) 它会在 Kyverno expression 中使用 Helm if/hasKey statement。

<details>
<summary>显示答案</summary>

**答案: B) 在 CREATE 时，它仅填充完全未设置的 normal-container resource，并保留现有完整或部分设置。**

实际 CLI 输出已与完整配置和部分配置的输入对象进行了比较，且保持不变。部分字段需要单独审查；请勿创建超过现有较小 limit 的 request。ApplyConfiguration 和 JSONPatch 具有不同的语义；JSONPatch 需要现有的 parent path，且独立策略的执行顺序无法保证。

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

- A) 从匹配的 trigger 创建明确选择的 downstream resource，并具备所需权限。
- B) 自动备份每个被删除的资源。
- C) 在创建时原子性地保证 namespace isolation。
- D) 绕过 background controller 的 RBAC。

<details>
<summary>显示答案</summary>

**答案: A) 从匹配的 trigger 创建明确选择的 downstream resource，并具备所需权限。**

此 Deployment 示例需要 opt-in 和至少两个所需的 replica，并复制完整的 spec.selector。生成可能是异步的。synchronization、data 与 clone source、generate-existing 和 orphaning 设置会影响更新/删除行为。未获得批准的 source/target boundary 时，请勿将 registry Secret clone 到每个新 namespace 中。

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

### 7. 哪种当前 Kyverno 类型用于验证 container image signature 和 attestation？

- A) ResourceQuota。
- B) ImageValidatingPolicy。
- C) ServiceMonitor。
- D) LimitRange。

<details>
<summary>显示答案</summary>

**答案: B) ImageValidatingPolicy。**

旧版 ClusterPolicy verifyImages rule 与新的 manifest kind 不同。请按照 image-security guide 所述，配置受支持的 Cosign 或 Notary/Notation trust path、精确的 signer/issuer/key rule 以及 registry access。任意的 GPG 或 Docker Content Trust material 不能直接替代。验证不是 vulnerability scanning，也不会自动成为 registry allowlist。配置的 digest mutation 可以更改 image reference；本章未执行 registry/signature 操作。

[镜像安全指南](../../security/07-image-security.md)

</details>

<span id="_8-what-does-the-background-false-setting-mean-in-a-kyverno-policy"></span>

### 8. 禁用 background validation scanning 意味着什么？

- A) 现有资源不会被该 validation setting 定期扫描，但仍可检查匹配的 admission update。
- B) 所有现有资源都将永久免于 admission。
- C) 此设置会停止所有 Kyverno controller。
- D) 现有策略违规会被删除。

<details>
<summary>显示答案</summary>

**答案: A) 现有资源不会被该 validation setting 定期扫描，但仍可检查匹配的 admission update。**

对于当前类型，请使用 spec.evaluation.background.enabled；经典 ClusterPolicy 使用 background。两者都不是 mutate-existing、generation 或 cleanup 的全局开关。background reporting 本身不会修复、拒绝或删除已存储的资源。admission operation 和 match condition 仍然控制 update。

</details>

### 9. 哪种 PolicyReport 表示形式是正确的？

- A) 包含 resource field 和 status field，且 summary count 与 result 无关。
- B) 一个 PolicyReport，具有 resources/result entry 以及与这些 entry 一致的 summary count。
- C) 每个 report 都必须使用 string timestamp.created。
- D) ClusterPolicyReport 表示所有 namespace report 的任意聚合。

<details>
<summary>显示答案</summary>

**答案: B) 一个 PolicyReport，具有 resources/result entry 以及与这些 entry 一致的 summary count。**

默认 chart profile 使用 Policy WG report。PolicyReport 是 namespaced 的，而 ClusterPolicyReport 覆盖 cluster-scoped resource。这是一个合成的 schema 示例，而不是实时收集的证据。提供的 timestamp 使用 integer second/nano。其他 report backend 必须单独验证。

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

- A) 运行 kyverno apply --cluster 以安装所有策略。
- B) 使用带有 test-manifest directory 的 kyverno test，或使用本地 resource file 的 kyverno apply。
- C) 运行不存在的通用 kyverno validate command。
- D) 成功的 Helm render 可以证明策略行为和 RBAC。

<details>
<summary>显示答案</summary>

**答案: B) 使用带有 test-manifest directory 的 kyverno test，或使用本地 resource file 的 kyverno apply。**

该指南提供 policy-lab-tests，其中包含正向输入和预期失败输入。kyverno test --require-tests 可避免接受空 test folder。kyverno apply 会评估资源；--cluster 会读取选定的 cluster 以进行评估，并非安装。--output 接受用于变更/生成对象的 path。Create subcommand 可用于受支持的 helper；请勿臆造 create disallow-latest-tag template command。

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[返回指南](../../security/01-kyverno-policy-management.md)
