# OPA Gatekeeper Quiz

Test your understanding of OPA Gatekeeper and the Rego policy language with the following questions.

---

## Questions

### 1. What language is used to write policies in OPA Gatekeeper?

- A) YAML
- B) JSON
- C) Rego
- D) HCL

<details>
<summary>Show Answer</summary>

**Answer: C) Rego**

**Explanation:**
OPA (Open Policy Agent) uses a declarative policy language called Rego. Rego is optimized for querying JSON/YAML data and making policy decisions.

```rego
package kubernetes.admission

violation[{"msg": msg}] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}
```

Unlike Kyverno, you need to learn a new language, but it allows expressing more complex policy logic.

</details>

---

### 2. What CRD defines reusable policy templates in Gatekeeper?

- A) Policy
- B) ConstraintTemplate
- C) PolicyTemplate
- D) GatekeeperPolicy

<details>
<summary>Show Answer</summary>

**Answer: B) ConstraintTemplate**

**Explanation:**
ConstraintTemplate defines Rego policy logic and parameter schema:

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

Constraints are created based on ConstraintTemplates to apply actual policies.

</details>

---

### 3. Which value is NOT supported in the enforcementAction field of a Gatekeeper Constraint?

- A) deny
- B) dryrun
- C) warn
- D) audit

<details>
<summary>Show Answer</summary>

**Answer: D) audit**

**Explanation:**
Gatekeeper's supported enforcementAction values:
- **deny**: Reject request on policy violation
- **dryrun**: Record violation but allow request
- **warn**: Show warning message, allow request

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

audit is not an enforcementAction but Gatekeeper's background audit feature.

</details>

---

### 4. What is the syntax for iterating through all elements of an array in Rego?

- A) for item in array
- B) array.forEach(item)
- C) item := array[_]
- D) loop array as item

<details>
<summary>Show Answer</summary>

**Answer: C) item := array[_]**

**Explanation:**
In Rego, `[_]` means all indices of an array:

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

This syntax is a core Rego pattern used when evaluating multiple values within rules.

</details>

---

### 5. What feature in Gatekeeper checks policy compliance of existing cluster resources?

- A) Validation
- B) Mutation
- C) Audit
- D) Generation

<details>
<summary>Show Answer</summary>

**Answer: C) Audit**

**Explanation:**
Gatekeeper Audit feature:
- Periodically inspects existing resources
- Records violations in Constraint status
- Validates existing resources, not just new ones

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

This allows understanding the impact before applying policies.

</details>

---

### 6. What CRD is used for automatic resource modification in Gatekeeper v3.10+?

- A) MutatingPolicy
- B) Assign / AssignMetadata
- C) ModifyResource
- D) ResourceMutator

<details>
<summary>Show Answer</summary>

**Answer: B) Assign / AssignMetadata**

**Explanation:**
Gatekeeper's Mutation CRDs:
- **AssignMetadata**: Add metadata (labels, annotations)
- **Assign**: Modify general fields like spec
- **ModifySet**: Add/remove values from arrays

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

Similar to Kyverno's mutate feature.

</details>

---

### 7. What operator calculates the difference between two sets in Rego?

- A) difference()
- B) subtract()
- C) - (minus)
- D) diff()

<details>
<summary>Show Answer</summary>

**Answer: C) - (minus)**

**Explanation:**
Rego set operations:

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

These operations are frequently used for required label validation.

</details>

---

### 8. What configuration is needed in Gatekeeper to reference resources from other namespaces?

- A) CrossNamespacePolicy
- B) Config's sync.syncOnly
- C) GlobalConstraint
- D) NamespaceSelector

<details>
<summary>Show Answer</summary>

**Answer: B) Config's sync.syncOnly**

**Explanation:**
For Gatekeeper to reference external data, sync configuration via Config resource is required:

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

Synchronized resources can be accessed in Rego via `data.inventory`:
```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

---

### 9. What is the official CLI tool for testing Gatekeeper policies?

- A) opa test
- B) gatekeeper-cli
- C) gator
- D) conftest

<details>
<summary>Show Answer</summary>

**Answer: C) gator**

**Explanation:**
Gator is the official CLI tool for locally testing Gatekeeper policies:

```bash
# Install
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# Validate policies
gator verify ./policies/

# Run test suite
gator test ./tests/
```

Test suite example:
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

---

### 10. What is Gatekeeper's advantage when comparing Gatekeeper and Kyverno?

- A) Lower learning curve
- B) YAML native policies
- C) Resource generation feature
- D) Complex policy logic expressiveness

<details>
<summary>Show Answer</summary>

**Answer: D) Complex policy logic expressiveness**

**Explanation:**
Gatekeeper (OPA) vs Kyverno comparison:

| Feature | Gatekeeper | Kyverno |
|---------|------------|---------|
| Policy Language | Rego | YAML |
| Learning Curve | High | Low |
| Complex Logic | Very Flexible | Limited |
| Resource Generation | Not Supported | Supported |
| External Data | OPA Bundle Support | API Call |

Gatekeeper's flexibility with Rego makes it easier to handle:
- Complex condition combinations
- Recursive data structure processing
- Advanced set operations
- External data integration

</details>

---

### 11. When multiple violation rules are defined in Rego, how are they evaluated?

- A) Only first rule is evaluated
- B) All rules are evaluated as OR
- C) All rules are evaluated as AND
- D) One is randomly selected

<details>
<summary>Show Answer</summary>

**Answer: B) All rules are evaluated as OR**

**Explanation:**
In Rego, multiple rules with the same name are evaluated as OR:

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

Results from each violation rule are added to a set, and if there's one or more violations, the overall policy fails.

</details>

---

### 12. What field in Gatekeeper configures a Constraint to apply only to specific namespaces?

- A) spec.targetNamespaces
- B) spec.match.namespaces
- C) spec.scope.namespaces
- D) spec.selector.namespaces

<details>
<summary>Show Answer</summary>

**Answer: B) spec.match.namespaces**

**Explanation:**
The match section of a Constraint specifies the application scope:

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

- `namespaces`: List of namespaces to include
- `excludedNamespaces`: List of namespaces to exclude
- `namespaceSelector`: Label-based selection

</details>

---

## Score Calculation

Calculate 1 point per question.

| Score | Rating |
|-------|--------|
| 11-12 | Excellent - OPA Gatekeeper expert level |
| 8-10 | Good - Basic concepts understood, Rego deep dive needed |
| 5-7 | Average - Additional study recommended |
| 0-4 | Basic learning needed |

---

## Related Documentation

- [OPA Gatekeeper](../security/09-opa-gatekeeper.md)
- [Kyverno Policy Management](../security/01-kyverno-policy-management.md)
- [Pod Security Standards](../security/03-pod-security-standards.md)
