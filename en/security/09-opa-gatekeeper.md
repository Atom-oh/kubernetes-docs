# OPA Gatekeeper

> **Validation baseline**: Gatekeeper/Gator 3.23.1 · Helm chart 3.23.1

> **Last Updated**: September 13, 2026

## Overview

Gatekeeper evaluates policies during Kubernetes admission and periodic audit. ConstraintTemplates define logic and parameter schemas; Constraints define scope, values and enforcementAction. The [complete examples](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/gatekeeper) use a dedicated `policy-lab` namespace and local tests. Do not apply every test fixture to a production cluster.

![Gatekeeper admission and periodic audit, with templates defining logic and Constraints selecting scope.](../.gitbook/assets/en-security-09-opa-gatekeeper-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-09-opa-gatekeeper-0.html)

<span id="gatekeeper-vs-kyverno-comparison"></span>

## Choosing Gatekeeper and Kyverno

Choose between Gatekeeper’s Rego/Constraint model and Kyverno’s Kubernetes-oriented policy model based on your requirements, tests and operating model. Gatekeeper also supports optional CEL-based Kubernetes native validation. Avoid unsupported fixed resource-usage rankings or claims that another engine cannot express complex logic. OPA’s CNCF graduation does not establish Gatekeeper as a separately graduated project.

<span id="installation-with-helm"></span>

<span id="installation-with-manifests"></span>

<span id="verify-installation"></span>

## Installing Gatekeeper

Use the pinned chart and supported values from the example directory. `auditInterval` and `logLevel` are top-level chart fields; do not assume arbitrary `audit.replicas` or `audit.logLevel` values take effect. The profile renders three webhook replicas and one audit Deployment. Verify the EKS control-plane-to-webhook network path, certificates, placement and available resources.

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm upgrade --install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace --values values.yaml --wait
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-controller-manager
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-audit
```

For staged rollout, `values.yaml` explicitly retains webhook `failurePolicy: Ignore`. Webhook invocation failures can therefore allow requests even when a Constraint says `deny`. Evaluate `Fail` together with API availability, recovery and exempt namespaces. Webhook scope can be broader than individual Constraint scope.

### Template and Constraint Ordering

Templates generate corresponding Constraint CRDs. Wait for Established CRDs and check template Pod status before applying Constraints. All example Constraints start in `dryrun`; review image prefixes, parameters and namespaces for the target environment.

```bash
kubectl create namespace policy-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f templates/
kubectl wait --for=condition=Established --timeout=90s \
  crd/docsrequiredlabels.constraints.gatekeeper.sh \
  crd/docsnoprivileged.constraints.gatekeeper.sh \
  crd/docsapprovedimages.constraints.gatekeeper.sh \
  crd/k8scontainerlimits.constraints.gatekeeper.sh \
  crd/docsuniqueingress.constraints.gatekeeper.sh
kubectl apply -f constraints/
```

<span id="rego-language-basics"></span>

<span id="rego-syntax-overview"></span>

<span id="rego-data-types"></span>

<span id="rego-operators-and-built-in-functions"></span>

## Rego and the Input Contract

Gatekeeper policies use `input.review`, not `input.request` from a generic OPA AdmissionReview example. `input.parameters` supplies Constraint values and `data.inventory` supplies synchronized Kubernetes objects. Existing `targets[].rego` uses supported Rego v0 by default. Rego v1 is selected explicitly with `code[].source.version: v1`; older v0 Templates are not automatically invalid.

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
        rego: "package docsrequiredlabels\nvalid_label(key) if {\n  value := input.review.object.metadata.labels[key]\n\
          \  is_string(value)\n  value != \"\"\n}\nviolation contains {\"msg\": sprintf(\"\
          required nonempty label: %v\", [key])} if {\n  some key in input.parameters.labels\n\
          \  not valid_label(key)\n}\n"
```

`violation contains ... if` is a v1 partial-set rule. Multiple definitions contribute to that set; this does not mean conflicting complete-document rules always combine as OR. Conditions within a rule body must all hold. Distinguish recursive user-defined rules from JSON traversal built-ins such as `walk`.

```rego
package examples
items := [x | some x in input.items; x > 10]
keys := object.keys(object.get(input, "labels", {}))
missing := {"app", "team"} - keys
```

`obj[_]` selects object values. Use `object.keys` or bind the key explicitly when you need label keys. Set difference `-`, intersection `&` and union `|` are useful policy operations.

<span id="writing-constraint-templates"></span>

<span id="basic-structure"></span>

<span id="preventing-privileged-containers"></span>

<span id="enforcing-resource-limits"></span>

<span id="restricting-image-registries"></span>

<span id="defining-constraints"></span>

<span id="basic-constraint-writing"></span>

<span id="using-namespace-selectors"></span>

<span id="resource-limits-constraint"></span>

<span id="image-registry-constraint"></span>

## Policies and Scope

| Template | Checks | Scope and limits |
|---|---|---|
| DocsRequiredLabels | Required nonempty labels | Pod metadata; Deployment metadata differs from Pod template labels |
| DocsNoPrivileged | Reject privileged=true | Regular, init and ephemeral containers; not a full PSS suite |
| DocsApprovedImages | Approved registry/path prefixes | All three container types; schema requires a trailing `/` boundary |
| K8sContainerLimits | CPU/memory limit presence and maximum | Pinned upstream policy; regular/init containers, since ephemeral containers cannot set resource fields |
| DocsUniqueIngress | Exact host conflicts in synced inventory | Excludes same-object updates; no wildcard or atomic concurrent-creation guarantee |

### Image Boundaries and Exceptions

`registry.example.com/team/` differs from `registry.example.com/team-evil/` and `registry.example.com.evil/`. Prefix matching needs a separator boundary and a fully qualified image-name contract. The example does not offer a workload-controlled bypass label such as `skip-privileged-check=true`. Namespace exceptions require controlled RBAC, authorization, expiry and audit records for label changes.

### Resource Quantities

A Gi/Mi/Ki-only parser can return undefined for `9G` or plain bytes and silently miss violations. The example pins the upstream `K8sContainerLimits` policy, which reports unsupported strings as violations. It does not accept every quantity representation Kubernetes permits; document its format restrictions. Native tests distinguish millicores, decimal/binary memory, plain bytes, numeric inputs and explicitly quoted exponent strings. Quote string fixtures such as `8e9` to prevent YAML parsers from converting them to numbers.

### PSS and Controller Resources

Do not label a few privileged/runAsNonRoot checks as complete Baseline/Restricted enforcement. Versioned PSS also covers host namespaces, seccomp, capabilities, OS distinctions, Pod-level inheritance and ephemeral containers; use the [Pod Security Standards guide](./03-pod-security-standards.md). These examples check Pod admission. To evaluate controller Pod templates earlier, configure separate template or ExpansionTemplate tests.

<span id="advanced-policy-patterns"></span>

<span id="external-data-reference"></span>

<span id="cross-namespace-policies"></span>

<span id="complex-condition-policies"></span>

## Synchronized Data and Referential Policies

`sync.yaml` synchronizes `networking.k8s.io/v1` Ingress objects into inventory. This differs from connecting an external HTTP provider or arbitrary OPA bundle. Synchronize only necessary objects and review RBAC, memory and sensitive data.

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
    - group: networking.k8s.io
      version: v1
      kind: Ingress
```

A different name in the same namespace, or the same name in another namespace, can still conflict. Requiring both namespace and name to differ misses those cases. The example excludes only the same namespace/name as a self-update. Because inventory is eventually consistent, it cannot atomically guarantee uniqueness for concurrent creations.

<span id="mutation-features"></span>

<span id="using-assignmetadata"></span>

<span id="using-assign"></span>

<span id="conditional-mutation"></span>

<span id="using-modifyset"></span>

## Mutation

AssignMetadata adds supported metadata labels/annotations; it is not a general overwrite mechanism. Assign sets a field. Assigning a whole toleration list can discard existing entries, so this example uses ModifySet merge. The toleration permits a dedicated lab taint; it does not select Spot nodes.

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: ModifySet
metadata:
  name: docs-dedicated-toleration
spec:
  applyTo:
  - groups:
    - ''
    versions:
    - v1
    kinds:
    - Pod
  match:
    scope: Namespaced
    namespaces:
    - policy-lab
  location: spec.tolerations
  parameters:
    operation: merge
    values:
      fromList:
      - key: dedicated
        operator: Equal
        value: policy-lab
        effect: NoSchedule
```

Separate mutation/defaulting from validation. Review CREATE/UPDATE scope, repeat application, convergence with other mutators and effects on existing objects. Creating a mutator does not automatically rewrite every existing object.

<span id="audit-configuration"></span>

<span id="checking-constraint-violations"></span>

<span id="prometheus-metrics"></span>

<span id="grafana-dashboard"></span>

## Audit and Monitoring

Set audit frequency with chart `auditInterval`. Config `validation.traces` is for debugging selected admission evaluations, not scheduling audit. Admission inputs and Rego prints can contain sensitive object data; enable them only for the needed scope. `constraintViolationsLimit` bounds the status detail list, which can differ from totalViolations.

```bash
kubectl get constraints
kubectl describe docsrequiredlabels required-labels
kubectl get constrainttemplatepodstatuses -n gatekeeper-system
kubectl get constraintpodstatuses -n gatekeeper-system
```

The chart webhook Service exposes only HTTPS webhook traffic, not metrics. `podmonitor.yaml` selects the actual named metrics:8888 container port on both audit and webhook Deployments. Install Prometheus Operator CRDs and align PodMonitor label/namespace selectors first.

| Metric | Interpretation |
|---|---|
| gatekeeper_validation_request_count | Validation requests with actual admission_status labels |
| gatekeeper_validation_request_duration_seconds | Validation latency histogram |
| gatekeeper_violations | Audited violations by enforcement_action; no assumed default constraint_name label |
| gatekeeper_audit_last_run_end_time | Last completed audit timestamp |
| gatekeeper_constraint_templates | Template status counts |

```promql
sum by (enforcement_action) (gatekeeper_violations)
histogram_quantile(0.99, sum by (le) (rate(gatekeeper_validation_request_duration_seconds_bucket[5m])))
```

<span id="testing-and-ci-cd-integration"></span>

<span id="gator-cli-testing"></span>

<span id="test-suite-definition"></span>

<span id="test-fixtures"></span>

<span id="github-actions-integration"></span>

## Gator Tests and CI

Install the official 3.23.1 release asset and verify its published checksum. The ARM64 binary reports +dirty in GitVersion; the audit verified the published archive hash rather than assuming that text means a local modification. Do not replace versioned evidence with an unpinned @latest CLI run.

```bash
gator version
gator verify tests/suite.yaml --verbose
gator test -f templates/docsnoprivileged.yaml \
  -f constraints/no-privileged.yaml \
  -f tests/fixtures/tenant-skip-label-no-bypass.yaml --output=json
```

`verify` checks expected violations in Suites; `test -f` evaluates manifests against Templates/Constraints. Verify can ignore a directory with no Suites, so check that all five tests and33 cases ran instead of trusting exit status alone. Fixture images are policy inputs, not pullable workloads. CI runs the local suite without credentials; any cluster dry-run belongs in a separate trusted environment with authorized access.

<span id="best-practices"></span>

<span id="policy-organization"></span>

<span id="gradual-policy-rollout"></span>

<span id="policy-exception-management"></span>

<span id="troubleshooting"></span>

<span id="common-issues"></span>

<span id="debugging-tips"></span>

## Rollout and Troubleshooting

Move the same populated Constraint through dryrun→warn→deny and review audit/admission results and exceptions. Do not create three parameterless Constraints as a rollout mechanism. Dryrun/warn can return violations with a zero Gator test exit status; deny violations return one. Observe webhook availability failures separately from policy violations.

```bash
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o yaml
kubectl -n gatekeeper-system logs deployment/gatekeeper-controller-manager --tail=100
kubectl -n gatekeeper-system logs deployment/gatekeeper-audit --tail=100
```

Check policy input, match scope, CRD/template errors, webhook certificates/network, audit timestamps and inventory freshness. Diagnose the cause before changing webhook enforcement or broadening namespace exceptions.

<span id="summary"></span>

<span id="related-documentation"></span>

## Validation Scope and Related Reading

Gator3.23.1 executed33 policy cases and three enforcement modes. Checks covered the pinned Helm render, eight Gatekeeper CRD objects and audit/webhook PodMonitor bindings. They did not execute Kubernetes admission, EKS networking, live audit-cache synchronization or API failover. Separate native mutation validation is recorded in the review report.

- [Gatekeeper quiz](../quizzes/security/09-opa-gatekeeper-quiz.md)
- [Kyverno](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [EKS security practices](./06-eks-security-best-practices.md)

## References

- [Gatekeeper v3.23.1](https://github.com/open-policy-agent/gatekeeper/tree/v3.23.1)
- [ConstraintTemplate and Rego versions](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/constrainttemplates.md)
- [Gator](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/gator.md)
- [Mutation](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/mutation.md)
- [Audit](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/audit.md)
- [Metrics](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/metrics.md)
- [Pinned resource-limits policy](https://github.com/open-policy-agent/gatekeeper-library/blob/bd333d4704647b1000cef5a92017257ee46fe2c8/library/general/containerlimits/template.yaml)
