# OPA Gatekeeper Quiz

> **Last Updated**: September 13, 2026

Test your understanding of OPA Gatekeeper and the Rego policy language with the following questions.

***

## Questions

### 1. What language is used to write policies in OPA Gatekeeper?

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>Show Answer</summary>

**Answer: C) Rego**

**Explanation:** OPA (Open Policy Agent) uses a declarative policy language called Rego. Rego is optimized for querying JSON/YAML data and making policy decisions.

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

Learn Rego sets, comprehensions and input contracts, then select a policy engine against your requirements and tests.

</details>

***

### 2. What CRD defines reusable policy templates in Gatekeeper?

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>Show Answer</summary>

**Answer: B) ConstraintTemplate**

**Explanation:** ConstraintTemplate defines Rego policy logic and parameter schema:

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

Constraints are created based on ConstraintTemplates to apply actual policies.

</details>

***

### 3. Which value is NOT supported in the enforcementAction field of a Gatekeeper Constraint?

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>Show Answer</summary>

**Answer: D) audit**

**Explanation:** Gatekeeper's supported enforcementAction values:

* **deny**: Reject request on policy violation
* **dryrun**: Record violation but allow request
* **warn**: Show warning message, allow request

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

audit is not an enforcementAction but Gatekeeper's background audit feature.

</details>

***

### 4. What is the syntax for iterating through all elements of an array in Rego?

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>Show Answer</summary>

**Answer: C) item := array\[\_]**

**Explanation:** In Rego, `[_]` means all indices of an array:

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

This syntax is a core Rego pattern used when evaluating multiple values within rules.

</details>

***

### 5. What feature in Gatekeeper checks policy compliance of existing cluster resources?

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>Show Answer</summary>

**Answer: C) Audit**

**Explanation:** Gatekeeper Audit feature:

* Periodically inspects existing resources
* Records violations in Constraint status
* Validates existing resources, not just new ones

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

This allows understanding the impact before applying policies.

</details>

***

<span id="_6-what-crd-is-used-for-automatic-resource-modification-in-gatekeeper-v3-10"></span>

### 6. What CRD is used for automatic resource modification in Gatekeeper 3.23.1?

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>Show Answer</summary>

**Answer: B) Assign / AssignMetadata**

**Explanation:** Gatekeeper's Mutation CRDs:

* **AssignMetadata**: Add metadata (labels, annotations)
* **Assign**: Modify general fields like spec
* **ModifySet**: Add/remove values from arrays

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

***

### 7. What operator calculates the difference between two sets in Rego?

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>Show Answer</summary>

**Answer: C) - (minus)**

**Explanation:** Rego set operations:

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

***

### 8. What configuration is needed in Gatekeeper to reference resources from other namespaces?

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>Show Answer</summary>

**Answer: B) Config's sync.syncOnly**

**Explanation:** This example synchronizes Kubernetes objects into inventory; it does not automatically connect an external HTTP provider or arbitrary bundle:

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

***

### 9. What is the official CLI tool for testing Gatekeeper policies?

* A) opa test
* B) gatekeeper-cli
* C) gator
* D) conftest

<details>

<summary>Show Answer</summary>

**Answer: C) gator**

**Explanation:** Gator is the official CLI tool for locally testing Gatekeeper policies:

```bash
# Install
gator version  # verified 3.23.1 release binary

# Validate policies
gator verify tests/suite.yaml --verbose

# Run test suite
gator test -f templates/ -f constraints/ -f tests/fixtures/labels-present.yaml --output=json
```

Test suite example:

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

### 10. Which concrete requirement can motivate choosing a Rego policy?

* A) Guaranteed lower memory use for every policy
* B) Automatically generating every resource without checks
* C) Always handling more complex logic than another engine
* D) Applying set operations and comprehensions to JSON inputs and validating them with tests

<details>
<summary>Show Answer</summary>

**Answer: D) Applying set operations and comprehensions to JSON inputs and validating them with tests**

**Explanation:** Rego provides declarative operations for this requirement. Compare actual policy expression, team skills, tests and operating needs rather than asserting universal performance or complexity superiority.

</details>

***

### 11. When multiple violation rules are defined in Rego, how are they evaluated?

* A) Only first rule is evaluated
* B) All rules are evaluated as OR
* C) All rules are evaluated as AND
* D) One is randomly selected

<details>

<summary>Show Answer</summary>

**Answer: B) All rules are evaluated as OR**

**Explanation:** Multiple definitions of this partial-set violation rule contribute their results to the same set:

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

Results from each violation rule are added to a set, and if there's one or more violations, the overall policy fails.

These partial-set violation rules contribute to the same set. Conditions inside each body are AND; conflicting complete-document rules are not resolved by OR. This fragment is not a full PSS implementation.

</details>

***

### 12. What field in Gatekeeper configures a Constraint to apply only to specific namespaces?

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>Show Answer</summary>

**Answer: B) spec.match.namespaces**

**Explanation:** The match section of a Constraint specifies the application scope:

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

* `namespaces`: List of namespaces to include
* `excludedNamespaces`: List of namespaces to exclude
* `namespaceSelector`: Label-based selection

</details>

***

## Score Calculation

Calculate 1 point per question.

| Score | Rating                                                  |
| ----- | ------------------------------------------------------- |
| 11-12 | Excellent - OPA Gatekeeper expert level                 |
| 8-10  | Good - Basic concepts understood, Rego deep dive needed |
| 5-7   | Average - Additional study recommended                  |
| 0-4   | Basic learning needed                                   |

***

## Related Documentation

* [OPA Gatekeeper](../../security/09-opa-gatekeeper.md)
* [Kyverno Policy Management](01-kyverno-policy-management-quiz.md)
* [Pod Security Standards](03-pod-security-standards-quiz.md)
