# Policy Management with Kyverno

> **Validation baseline**: Kyverno/CLI 1.19.1, Helm chart 3.9.1. The current release guide lists Kubernetes 1.33–1.35 as tested; the chart's broader install constraint is not a compatibility guarantee.
> **Last Updated**: September 13, 2026

Kyverno evaluates Kubernetes policy and performs explicitly configured mutation, generation and deletion. These examples were checked locally with the real CLI and released schemas/charts. No live cluster installation, admission, network isolation, cleanup or AWS integration was executed.

The original `ClusterPolicy` examples have been updated to `policies.kyverno.io/v1` CEL policies. The official 1.19 migration guide deprecates ClusterPolicy/Policy, CleanupPolicy and legacy `kyverno.io` PolicyException, with removal planned for 1.20. They are not already absent in 1.19; migrate and test before upgrading rather than merely replacing an apiVersion string.

## Lab Environment Setup

### Required Tools

Use kubectl with version skew supported by the target API server, an OCI-capable supported Helm release, and the verified Kyverno 1.19.1 CLI for these local tests. Obtain the CLI's matching OS/architecture archive and verify its published checksum/signature. Do not reuse a 1.10.0 archive or pipe an unverified download into a root installation.

Begin with local files. The policies below are independent examples, not a set to apply wholesale. Pod examples target `policy-lab`; generation additionally requires an explicit label. Restrict who can change these policies, namespace labels, Roles and PolicyExceptions. Those selectors are not an RBAC security boundary by themselves.

### Installing Kyverno

Prepare a dedicated `kyverno` namespace. Check the chosen EKS/Kubernetes version, API-server-to-webhook connectivity, DNS, admission failure/timeout behavior and CRD upgrade procedure before changing a shared cluster. Kubernetes ServiceAccounts/RBAC authorize the controllers; installing Kyverno does not itself require an AWS administrator role.

## Introduction to Kyverno

### Kyverno Architecture and How It Works

| Component | Responsibility |
|---|---|
| Admission controller | Matching admission requests and policy validation/mutation/image checks; not every GET/list request |
| Background controller | Generate and explicitly enabled mutate-existing work |
| Reports controller | Policy result aggregation/reporting |
| Cleanup controller | Scheduled deletion policies and permitted cleanup operations |

A validating policy does not delete or repair existing noncompliant resources. Background reporting, mutate-existing, generate-existing and scheduled deletion are separate mechanisms with different permissions. Generation can be asynchronous; namespace creation and generated NetworkPolicy enforcement are not an atomic operation.

### Kyverno vs OPA Gatekeeper

Kyverno's current policies use CEL in YAML/JSON manifests; legacy policies also use patterns and JMESPath. Kubernetes-native packaging does not eliminate the need to learn policy expressions. Gatekeeper uses ConstraintTemplates/Constraints and supported policy engines for its version, with separate admission/audit/mutation capabilities. Compare required features, expression languages, policy tests, controller availability and measured workload impact. The old “easy/complex” and “good/very good performance” ratings were unsupported comparisons, not benchmarks.

## Installing Kyverno

### Installation Using Helm

Save this as `kyverno-values.yaml`. It is a single-replica **lab** profile. ServiceMonitor CRDs and a Prometheus installation selecting the actual namespace/labels must already exist; replace the example `release: kube-prom` label with that installation's selector, or disable ServiceMonitors until prepared.

```yaml
admissionController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
backgroundController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
cleanupController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
reportsController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
```

```bash
# Use an approved context; this changes real cluster resources.
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm template kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --values kyverno-values.yaml > kyverno-rendered.yaml
# Inspect the render, CRD migration and webhook reachability before installation.
helm upgrade --install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace --kube-context "$KUBE_CONTEXT" \
  --values kyverno-values.yaml
```

The render contains four controller Deployments and four metrics ServiceMonitors. More replicas require topology, disruption, resource sizing and webhook availability planning; one replica per controller is not an HA design. Inspect the current chart's defaults and actual rendered image tags instead of interpreting a chart version label as the application version.

### Installation Using YAML Manifests

If GitOps manages YAML, render the pinned chart and review its CRDs, RBAC, certificates and hooks as a managed set. A raw `kubectl apply` of a render does not execute Helm hook/upgrade semantics. Do not apply the old 1.10.0 install.yaml over a newer release or mix multiple owners for the same controllers.

## Policy Types

### 1. Validation Policies

Save this independent example as `require-limits.yaml`. It checks **normal and init containers** for nonempty CPU/memory limits. Ephemeral containers cannot declare resource requests/limits; security checks below cover them separately. This is a chosen per-container policy, not a claim that every Kubernetes workload must use this resource strategy.

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

`validationActions: [Audit]` records violations while permitting matching admission requests; `[Deny]` rejects them after staging/impact review. `Warn` can provide client warnings. Webhook `failurePolicy` governs evaluation/transport failure and is a different setting. Offline CLI failure results do not demonstrate that an Audit policy denied a live request.

### 2. Mutation Policies

Save as `add-default-label.yaml`. Existing `environment` labels, including explicitly empty values, are preserved. This uses CEL ApplyConfiguration, not Helm Go-template `if`/`hasKey` syntax inside Kyverno.

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: add-default-label
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
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        has(object.metadata.labels) && 'environment' in object.metadata.labels
        ? Object{}
        : Object{metadata: Object.metadata{labels: {"environment": object.metadata.namespace}}}
```

The example disables mutate-existing. Admission mutation can still affect matching CREATE/UPDATE requests. A JSONPatch alternative must create a missing labels map before adding a child key and escape `/` as `~1` in JSON Pointer paths. Mutation order is not guaranteed across independent policies.

### 3. Generation Policies

Save as `generate-networkpolicy.yaml`. Only a Namespace named `policy-lab` with `training.example.com/managed: "true"` triggers this example. For a Namespace object, match its **name/labels**, not `metadata.namespace` or a legacy namespace exclusion list.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-networkpolicy
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
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("networking.k8s.io/v1"),
        "kind": dyn("NetworkPolicy"),
        "metadata": dyn({"name": "lab-default-deny", "namespace": object.metadata.name}),
        "spec": dyn({"podSelector": {}, "policyTypes": ["Ingress", "Egress"]})
      }])
```

Prepare required DNS/API/application allow rules before workloads depend on this namespace. Kubernetes NetworkPolicy isolation needs an enforcing CNI; other allow policies are additive and host-network behavior must be considered. A locally generated manifest is not evidence that traffic was blocked.

Synchronization and generate-existing are disabled here. An already existing Namespace is not automatically backfilled when this policy is installed: use a later matching trigger or explicitly review enabling generate-existing before changing that setting. With synchronization enabled, downstream lifecycle depends on data versus clone source, trigger changes and `orphanDownstreamOnPolicyDelete`; it is not a universal backup/rollback mechanism. Sharing Secrets needs an explicit source/target allowlist and RBAC/credential-lifecycle review, not a copy into every new namespace.

### 4. Scheduled Deletion

`DeletingPolicy` uses `spec.schedule` and CEL conditions; it is separate from validation and has no validationActions Audit switch. A cleanup controller needs explicit deletion permissions. Prefer a narrow namespace/object label and a clear age/status retention requirement, inspect the selected candidates, and test recovery before enabling a schedule. The optional quiz example selects marked completed Pods; it does not mean “older than 24 hours,” and no scheduled deletion was executed here.

## Kyverno Use Cases in EKS

### EKS and Kyverno Integration Architecture

The EKS API server invokes matching admission webhooks using the configured Kubernetes network/RBAC path. CloudWatch export is a separate configured collector/integration with its own IAM and retention; installing Kyverno does not automatically send every PolicyReport to CloudWatch. Avoid printing raw admission payloads that may contain secrets.

### 1. Security Hardening

#### Preventing Privileged Containers

Missing `privileged` is treated as false. The check covers normal, init and ephemeral containers; declared `pods/ephemeralcontainers` matching still requires live admission/subresource testing in the target environment.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged
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
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, !c.?securityContext.privileged.orValue(false))
    message: Privileged normal, init and ephemeral containers are not allowed.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

#### Preventing Root User Execution

The policy uses each container's override or the Pod-level default, requires effective runAsNonRoot and rejects an explicit effective UID 0. This validates the declaration; kubelet/image behavior is still relevant at runtime.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-non-root
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
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, c.?securityContext.runAsNonRoot.orValue(object.spec.?securityContext.runAsNonRoot.orValue(false))
      && c.?securityContext.runAsUser.orValue(object.spec.?securityContext.runAsUser.orValue(-1)) != 0)
    message: Use effective runAsNonRoot=true and do not select UID 0.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

### 2. Cost Optimization

#### Setting Resource Limits

Save as `default-resources.yaml`. This CREATE-only example avoids changing running Pod resources during an ordinary update and supplies defaults only when a normal container has **no requests and no limits**. It preserves complete and partial existing resource settings instead of overwriting workload sizing or producing a request greater than an existing small limit. Review partial settings separately; it does not fill every missing field or default init/ephemeral resources.

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

#### Enforcing Specific Instance Types

The original instance names are an illustrative allowlist, not a current recommendation. An explicit nodeSelector is a mandatory scheduling constraint. This admission-only CREATE policy rejects a supplied nodeName; background scanning is disabled because scheduled Pods legitimately acquire nodeName. Trust in node labels, scheduler/binding permissions and available capacity is separate. A declaration check cannot guarantee placement against a principal allowed to bind Pods or modify Nodes.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-node-selector
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
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.spec.?nodeName.orValue('') == '' && object.spec.?nodeSelector['node.kubernetes.io/instance-type'].orValue('')
      in ['m5.large', 'c5.large', 'r5.large']
    message: Use an approved instance-type nodeSelector and do not bypass the scheduler with nodeName.
  evaluation:
    background:
      enabled: false
```

### 3. Compliance

#### Automatic PodDisruptionBudget Generation

This opt-in Deployment example requires at least two desired replicas and copies the **complete spec.selector**, including matchExpressions, rather than a possibly absent top-level app label. It does not prove two replicas are Ready. This static lab budget needs a separate ownership/review decision after scaling or selector changes, especially with synchronization disabled. PDBs constrain eligible voluntary evictions, not every rollout or involuntary failure.

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

The background controller needs actual permission to create the generated resource. For the rendered `kyverno` release, this additional namespace Role/Binding illustrates a narrow PDB grant. The chart already contains other controller permissions; do not call this the controller's entire effective RBAC policy. Adjust ServiceAccount names to the render and verify authorization in the target cluster.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
rules:
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
subjects:
- kind: ServiceAccount
  name: kyverno-background-controller
  namespace: kyverno
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kyverno-lab-pdb-writer
```

#### Automatic Namespace ResourceQuota Generation

The same explicit Namespace opt-in applies. Quota values are a lab policy, not an AWS budget or cost cap; account for workload requests, init containers, limits and existing quotas before enabling it.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-quota
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
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("v1"), "kind": dyn("ResourceQuota"),
        "metadata": dyn({"name": "lab-resource-quota", "namespace": object.metadata.name}),
        "spec": dyn({"hard": {"requests.cpu": "10", "requests.memory": "10Gi",
          "limits.cpu": "20", "limits.memory": "20Gi", "pods": "50"}})
      }])
```

## Policy Testing and Validation

### Policy Application Workflow

Review policy ownership and scope, test positive/negative/skip cases locally, inspect generated/mutated objects, then stage live admission and controller permissions. Audit is a validation action; it does not make mutation, generation or deletion harmless. Pod-controller autogeneration and native ValidatingAdmissionPolicy/MutatingAdmissionPolicy generation are separate opt-ins with compatibility limits; inspect generated policy status rather than assuming all controller templates are covered.

### Policy Simulation

Create `policy-lab-tests/` and save the following four files there. The test intentionally expects a violation for `missing-label`; a passing test suite means expectations matched, not that every input complied.

`require-team.yaml`:

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

`pod.yaml` (a local fixture; its image is not pulled):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good
  namespace: policy-lab
  labels:
    team: platform
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`pod-missing.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: missing-label
  namespace: policy-lab
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`kyverno-test.yaml`:

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: team-label-local-test
policies:
- require-team.yaml
resources:
- pod.yaml
- pod-missing.yaml
results:
- policy: require-team
  kind: Pod
  resources:
  - good
  result: pass
- policy: require-team
  kind: Pod
  resources:
  - missing-label
  result: fail
```

```bash
kyverno version
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
# Offline evaluation; this does not install a policy or modify cluster resources:
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
# For mutation/generation, --output takes a file/directory path, not a format name:
kyverno apply add-default-label.yaml --resource ./policy-lab-tests/pod.yaml --output ./mutated/
```

### Policy Validation

`kyverno test` takes a directory with a test manifest; `kyverno apply` evaluates policy against supplied resources. `--cluster` reads resources from the selected cluster for evaluation; it is not a policy installation command. Installing a reviewed policy uses kubectl/GitOps and changes the cluster. Consult the pinned CLI help: a generic `kyverno validate` or `kyverno create disallow-latest-tag` workflow is not the tested interface. `create` does exist for supported Kyverno helper resources.

## Policy Monitoring and Reporting

### Policy Reports

The default profile uses the Policy WG `PolicyReport`/`ClusterPolicyReport` APIs. A PolicyReport is namespaced; ClusterPolicyReport covers cluster-scoped resources, not simply all namespaces combined. Reporting configuration and supported rule types matter. Background scans report validation results; they do not retroactively deny, mutate or delete existing objects. Existing objects remain subject to matching admission checks when updated even if background scanning is disabled.

This is a **synthetic schema example**, not a report collected from a cluster. Results use `resources` and `result`, not `resource`/`status`; if a timestamp is supplied it uses integer seconds/nanos. Summary counts must agree with the entries.

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

Query actual reports with `kubectl get policyreports -n policy-lab` and `kubectl get clusterpolicyreports`. Reports Server/OpenReports are separate optional installations/configurations; verify the API actually installed before assuming the backend.

### Prometheus Metrics

Use the chart-created metrics Services and per-controller ServiceMonitors from the tested values above. Their Service port name is `metrics-port` on 8000, with component/instance/part-of selectors—not `app: kyverno`. The render places them in `kyverno` and configures `namespaceSelector.matchNames: [kyverno]`. Prometheus must select those monitors and the namespace. Resource existence does not prove scraping or CloudWatch export.

## Best Practices

### 1. Gradual Rollout

Stage new validation with Audit, review actual reports and exceptions, then choose Deny where appropriate. Check webhook failure policy, timeout, replica availability and emergency recovery. Keep generation, mutation-existing and destructive deletion review separate.

### 2. Exception Handling

Narrow matchConstraints/matchConditions are not equivalent to an unlimited exemption. Review namespace scope, names, kinds and admission/user information availability. Classic rules depending on user/role information cannot be assumed evaluable in background scans. CEL PolicyException uses `policies.kyverno.io/v1`, explicit policyRefs/matchConditions and optionally expiresAt; restrict who can create it and verify installation/configuration support. An exception is an authorization-sensitive object, not an admission bypass every application team should receive.

### 3. Policy Organization

Keep versioned validation, mutation, generation and deletion policies with tests and owners. Legacy ClusterPolicy patterns/JMESPath differ from CEL; migrate rule-by-rule with output comparisons. Image signature verification is `ImageValidatingPolicy` in the current API; see the [image security guide](./07-image-security.md) for attestor/registry/trust prerequisites. Signature verification is not vulnerability scanning or a blanket registry allowlist.

## Conclusion

Local validation covered real Kyverno 1.19.1 policy evaluation and output preservation, released API schemas and chart rendering. Live webhook ordering/autogeneration, controller RBAC, networking, image trust and destructive lifecycle actions were not executed. Those remain deployment acceptance checks.

- [Kyverno releases and tested Kubernetes versions](https://kyverno.io/docs/installation/releases/)
- [Installation and controller responsibilities](https://kyverno.io/docs/installation/installation/)
- [Migration to CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## Quiz

Try the [Kyverno Policy Management Quiz](../quizzes/security/01-kyverno-policy-management-quiz.md).
