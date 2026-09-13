# Kyverno Policy Management Quiz

> **Last Updated**: September 13, 2026

These questions use the reviewed Kyverno 1.19.1 CEL policies. Examples are local fixtures; no cluster or destructive cleanup was executed.

## Quiz Questions

### 1. What is Kyverno?

- A) A Kubernetes policy engine with admission and separately configured background/lifecycle controllers.
- B) Only a vulnerability scanner.
- C) An API-server authentication replacement.
- D) A service mesh dataplane.

<details>
<summary>Show Answer</summary>

**Answer: A) A Kubernetes policy engine with admission and separately configured background/lifecycle controllers.**

Kyverno policies validate, mutate, generate, verify images and delete under their configured scopes. Current v1 policies use CEL inside YAML/JSON; legacy ClusterPolicy patterns and JMESPath are different languages. Kubernetes-native packaging does not remove the need to learn policy expressions.

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

### 2. Which statement correctly distinguishes policy operations?

- A) Every policy runs only on admission and never changes other objects.
- B) Audit makes generation and deletion read-only.
- C) All GET/list requests are intercepted by admission webhooks.
- D) Validation, mutation, generation and scheduled deletion have different controllers, settings and permissions.

<details>
<summary>Show Answer</summary>

**Answer: D) Validation, mutation, generation and scheduled deletion have different controllers, settings and permissions.**

Kubernetes authentication (for example, OIDC or ServiceAccount tokens) and authorization (RBAC) are separate from admission policy; Authenticate is not a Kyverno policy action. DeletingPolicy uses a schedule and conditions; a ClusterPolicy rule with cleanup.ttl is not its API. Mutation/generation/deletion can change resources even when an unrelated validation policy is in Audit. Use explicit lab selectors, required RBAC and recovery planning. The following optional deletion definition is shown for schema understanding; it was not applied and does not implement a 24-hour age threshold.

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

### 3. How do validationActions: [Audit] and [Deny] differ in a current ValidatingPolicy?

- A) Both always reject a matched violation.
- B) Audit permits matched violations for reporting; Deny rejects them during matching admission.
- C) Audit deletes existing violating objects.
- D) Deny automatically rewrites the resource.

<details>
<summary>Show Answer</summary>

**Answer: B) Audit permits matched violations for reporting; Deny rejects them during matching admission.**

Webhook failurePolicy deals with evaluation/transport failures and is separate. A local CLI fail result records a policy violation, not proof that an Audit policy denied a live request. In the legacy API, Enforce/Audit failure actions have different field names; migrate deliberately.

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

### 4. How is the resource scope of a CEL ValidatingPolicy selected?

- A) A top-level target string is sufficient.
- B) Use matchConstraints and optional matchConditions; inspect kind, operation, namespace and request-data availability.
- C) Every policy automatically matches all Kubernetes resources.
- D) Use metadata.name as the only selector.

<details>
<summary>Show Answer</summary>

**Answer: B) Use matchConstraints and optional matchConditions; inspect kind, operation, namespace and request-data availability.**

Classic ClusterPolicy uses rule match/exclude structures; they are not the current CEL field layout. Resource and user conditions must be understood as expressions, not assumed OR/AND shorthand. User/role information from admission is not always available in background scans. A namespace label selector is also controlled by whoever can change that label.

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

### 5. What makes this resource-default mutation safe for existing values?

- A) It overwrites every container with identical limits.
- B) On CREATE, it fills only completely unset normal-container resources and preserves existing complete or partial settings.
- C) It copies the first container’s values to every other container.
- D) It uses Helm if/hasKey statements inside a Kyverno expression.

<details>
<summary>Show Answer</summary>

**Answer: B) On CREATE, it fills only completely unset normal-container resources and preserves existing complete or partial settings.**

The real CLI output was compared with complete and partially configured input objects and was unchanged. Partial fields require separate review; do not create a request above an existing small limit. ApplyConfiguration and JSONPatch have different semantics; JSONPatch needs an existing parent path, and independent policy execution order is not guaranteed.

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

### 6. When is a GeneratingPolicy useful?

- A) Creating explicitly selected downstream resources from a matched trigger with the necessary permissions.
- B) Backing up every deleted resource automatically.
- C) Guaranteeing namespace isolation atomically at creation.
- D) Bypassing the background controller’s RBAC.

<details>
<summary>Show Answer</summary>

**Answer: A) Creating explicitly selected downstream resources from a matched trigger with the necessary permissions.**

This Deployment example requires opt-in and at least two desired replicas, and copies the entire spec.selector. Generation can be asynchronous. Synchronization, data versus clone sources, generate-existing and orphaning settings affect update/deletion behavior. Do not clone a registry Secret into every new namespace without an approved source/target boundary.

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

### 7. Which current Kyverno type verifies container image signatures and attestations?

- A) ResourceQuota.
- B) ImageValidatingPolicy.
- C) ServiceMonitor.
- D) LimitRange.

<details>
<summary>Show Answer</summary>

**Answer: B) ImageValidatingPolicy.**

Legacy ClusterPolicy verifyImages rules are different from the new manifest kind. Configure the supported Cosign or Notary/Notation trust path, precise signer/issuer/key rules and registry access described in the image-security guide. Arbitrary GPG or Docker Content Trust material is not a drop-in replacement. Verification is not vulnerability scanning or automatically a registry allowlist. Configured digest mutation can change the image reference; no registry/signature operation was executed in this chapter.

[Image security guide](../../security/07-image-security.md)

</details>

<span id="_8-what-does-the-background-false-setting-mean-in-a-kyverno-policy"></span>

### 8. What does disabling background validation scanning mean?

- A) Existing resources are not periodically scanned by that validation setting, but matching admission updates can still be checked.
- B) All existing resources are permanently exempt from admission.
- C) The setting stops every Kyverno controller.
- D) Existing policy violations are deleted.

<details>
<summary>Show Answer</summary>

**Answer: A) Existing resources are not periodically scanned by that validation setting, but matching admission updates can still be checked.**

For the current type use spec.evaluation.background.enabled; classic ClusterPolicy used background. Neither is a global switch for mutate-existing, generation or cleanup. Background reporting itself does not repair, deny or delete an already stored resource. Admission operations and match conditions still govern updates.

</details>

### 9. Which PolicyReport representation is correct?

- A) A resource field and status field with summary counts unrelated to results.
- B) A PolicyReport with resources/result entries and summary counts consistent with those entries.
- C) Every report must use a string timestamp.created.
- D) ClusterPolicyReport means an arbitrary aggregation of all namespace reports.

<details>
<summary>Show Answer</summary>

**Answer: B) A PolicyReport with resources/result entries and summary counts consistent with those entries.**

The default chart profile uses Policy WG reports. PolicyReport is namespaced and ClusterPolicyReport covers cluster-scoped resources. This is a synthetic schema example, not collected live evidence. A supplied timestamp uses integer seconds/nanos. Other report backends must be verified separately.

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

### 10. How should these Kyverno policies be tested locally?

- A) Run kyverno apply --cluster to install all policies.
- B) Use kyverno test with a test-manifest directory, or kyverno apply with local resource files.
- C) Run the nonexistent generic kyverno validate command.
- D) A successful Helm render proves policy behavior and RBAC.

<details>
<summary>Show Answer</summary>

**Answer: B) Use kyverno test with a test-manifest directory, or kyverno apply with local resource files.**

The guide supplies policy-lab-tests with positive and expected-failure inputs. kyverno test --require-tests avoids accepting an empty test folder. kyverno apply evaluates resources; --cluster reads a selected cluster for evaluation and is not installation. --output takes a path for mutated/generated objects. Create subcommands exist for supported helpers; do not invent a create disallow-latest-tag template command.

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[Return to the guide](../../security/01-kyverno-policy-management.md)
