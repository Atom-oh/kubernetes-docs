# Kyverno Policy Management Quiz

This quiz tests your understanding of policy management using Kyverno in Kubernetes.

## Quiz Questions

### 1. What is Kyverno?

A. A Kubernetes-native policy engine
B. A container image scanner
C. A cluster monitoring tool
D. A service mesh implementation

<details>
<summary>Show Answer</summary>

**Answer: A. A Kubernetes-native policy engine**

**Explanation:**
Kyverno is a Kubernetes-native policy engine that can validate, mutate, and generate Kubernetes resources using policies written in YAML or JSON. Since Kyverno uses the Kubernetes API and YAML syntax, you can define and manage policies without learning a new language or tools.

**Key Features:**
1. **Native Kubernetes Integration**: Works directly with the Kubernetes API.
2. **Declarative Policy Definition**: Uses YAML-based declarative policies.
3. **Various Policy Types Supported**: Supports Validate, Mutate, Generate, and Cleanup policies.
4. **Image Verification**: Provides container image security verification capabilities.
5. **Auditing and Reporting**: Provides auditing and reporting capabilities for policy compliance.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

This policy requires all Pods to have a 'team' label.

**Issues with Other Options:**
- B. Container image scanner: While Kyverno provides image verification capabilities, its primary purpose is policy management. Dedicated image scanners include Trivy, Clair, etc.
- C. Cluster monitoring tool: Kyverno is not a monitoring tool. Prometheus, Grafana, etc. are monitoring tools.
- D. Service mesh implementation: Kyverno is not a service mesh. Istio, Linkerd, etc. are service mesh implementations.
</details>

### 2. Which of the following is NOT a policy type supported by Kyverno?

A. Validate
B. Mutate
C. Generate
D. Authenticate

<details>
<summary>Show Answer</summary>

**Answer: D. Authenticate**

**Explanation:**
Kyverno supports the following policy types:

1. **Validate**: Validates that resources meet certain conditions.
2. **Mutate**: Automatically modifies resources.
3. **Generate**: Automatically creates additional resources when other resources are created.
4. **Verify Images**: Verifies container image signatures.
5. **Cleanup**: Automatically deletes resources based on certain conditions.

Kyverno does not directly support an Authentication policy type. Authentication in Kubernetes is typically handled at the API server level and managed through mechanisms such as RBAC (Role-Based Access Control), OIDC (OpenID Connect), and service accounts.

**Examples of Each Policy Type:**

1. **Validate Policy Example**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required"
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

2. **Mutate Policy Example**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-environment-label
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        metadata:
          labels:
            environment: "{{request.object.metadata.namespace}}"
```

3. **Generate Policy Example**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

4. **Verify Images Policy Example**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: check-image-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
```

5. **Cleanup Policy Example**:
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: cleanup-old-pods
spec:
  rules:
  - name: cleanup-completed-pods
    match:
      resources:
        kinds:
        - Pod
    preconditions:
      all:
      - key: "{{request.object.status.phase}}"
        operator: In
        value: ["Succeeded", "Failed"]
    cleanup:
      ttl: "24h"
```

**Explanation of Other Options:**
- A. Validate: A policy type supported by Kyverno that validates whether resources meet certain conditions.
- B. Mutate: A policy type supported by Kyverno that automatically modifies resources.
- C. Generate: A policy type supported by Kyverno that automatically creates additional resources when other resources are created.
</details>
### 3. What does `validationFailureAction: enforce` mean in a Kyverno policy?

A. Generate a warning only on policy violation
B. Block resource creation or update on policy violation
C. Automatically modify the resource on policy violation
D. Delete the resource on policy violation

<details>
<summary>Show Answer</summary>

**Answer: B. Block resource creation or update on policy violation**

**Explanation:**
In a Kyverno policy, `validationFailureAction: enforce` is a setting that blocks resource creation or update when a policy is violated. When this setting is applied, the policy rejects the creation or modification of resources that do not meet policy conditions and returns a policy violation message to the user.

There are two possible values for `validationFailureAction`:
1. **enforce**: Blocks resource creation or update on policy violation.
2. **audit**: Allows resource creation or update on policy violation but logs the violation. This is useful for testing policies or auditing the current state.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-probes
spec:
  validationFailureAction: enforce  # Block resource creation/update on policy violation
  rules:
  - name: check-readiness-probe
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Readiness probe is required"
      pattern:
        spec:
          containers:
          - readinessProbe:
              {}
```

This policy checks that all Pod containers have a readinessProbe configured, and if not, blocks Pod creation.

**How to Apply the Policy:**
```bash
# Apply the policy
kubectl apply -f require-probes.yaml

# Attempt to create a Pod without a readinessProbe
kubectl apply -f pod-without-probe.yaml
# Result: Error from server: error when creating "pod-without-probe.yaml": admission webhook "validate.kyverno.svc" denied the request:
# resource Pod/default/nginx was blocked due to the following policies: require-probes: check-readiness-probe: Readiness probe is required
```

**Issues with Other Options:**
- A. Generate a warning only on policy violation: This is the behavior of `validationFailureAction: audit`.
- C. Automatically modify the resource on policy violation: This is the behavior of mutate policies and is unrelated to validationFailureAction.
- D. Delete the resource on policy violation: Kyverno does not automatically delete existing resources on policy violation. Cleanup policies can delete resources based on certain conditions, but this is a different mechanism from validationFailureAction.
</details>

### 4. What field is used in Kyverno to select which resources a policy applies to?

A. selector
B. match
C. target
D. apply

<details>
<summary>Show Answer</summary>

**Answer: B. match**

**Explanation:**
The field used in Kyverno to select which resources a policy applies to is `match`. This field is used to specify the kind, name, namespace, labels, etc. of resources to which policy rules apply.

The `match` field can include the following subfields:
1. **resources**: Specifies resource kind, name, namespace, etc.
2. **subjects**: Specifies users, groups, service accounts to which the policy applies.
3. **roles**: Specifies roles to which the policy applies.
4. **clusterRoles**: Specifies cluster roles to which the policy applies.

Additionally, the `exclude` field can be used to exclude specific resources from policy application.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels-for-deployments
spec:
  validationFailureAction: enforce
  rules:
  - name: check-required-labels
    match:
      resources:
        kinds:
        - Deployment
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            app.kubernetes.io/managed-by: kustomize
    validate:
      message: "Required labels are missing"
      pattern:
        metadata:
          labels:
            app.kubernetes.io/name: "?*"
            app.kubernetes.io/version: "?*"
            app.kubernetes.io/component: "?*"
```

This policy applies only to Deployments in the 'production' and 'staging' namespaces that have the 'app.kubernetes.io/managed-by: kustomize' label.

**Complex Matching Example:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: complex-matching-policy
spec:
  validationFailureAction: enforce
  rules:
  - name: complex-match-rule
    match:
      resources:
        kinds:
        - Deployment
        - StatefulSet
        namespaces:
        - "production"
        - "staging"
        selector:
          matchLabels:
            tier: "frontend"
      subjects:
      - kind: User
        name: "admin@example.com"
      - kind: Group
        name: "system:masters"
    exclude:
      resources:
        namespaces:
        - "kube-system"
        names:
        - "critical-deployment"
    validate:
      message: "Policy validation failed"
      pattern:
        spec:
          template:
            spec:
              containers:
              - securityContext:
                  runAsNonRoot: true
```

This policy applies to Deployments and StatefulSets in the 'production' and 'staging' namespaces with the 'tier: frontend' label, and only when created or modified by the 'admin@example.com' user or 'system:masters' group. Resources in the 'kube-system' namespace and resources named 'critical-deployment' are excluded.

**Issues with Other Options:**
- A. selector: In Kyverno, it is used as a subfield like `match.resources.selector`, but is not a top-level field.
- C. target: A field not used in Kyverno policies.
- D. apply: A field not used in Kyverno policies.
</details>

### 5. Which policy type in Kyverno automatically modifies resources on policy violation?

A. Validate
B. Mutate
C. Generate
D. Verify

<details>
<summary>Show Answer</summary>

**Answer: B. Mutate**

**Explanation:**
The policy type in Kyverno that automatically modifies resources on policy violation is `Mutate`. Mutate policies automatically modify resources when they are created or updated to meet policy requirements.

Mutate policies can modify resources using the following methods:
1. **patchStrategicMerge**: Uses strategic merge patch to modify resources.
2. **patchesJson6902**: Uses JSON patch (RFC 6902) to modify resources.
3. **overlay**: (Legacy) A legacy field that provides the same functionality as patchStrategicMerge.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-resources
spec:
  rules:
  - name: add-default-cpu-memory
    match:
      resources:
        kinds:
        - Deployment
    mutate:
      patchStrategicMerge:
        spec:
          template:
            spec:
              containers:
              - (name): "*"
                resources:
                  limits:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.limits.memory }}{{ else }}512Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.limits \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.limits.cpu }}{{ else }}500m{{ end }}"
                  requests:
                    memory: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"memory\" }}{{ .object.spec.template.spec.containers[0].resources.requests.memory }}{{ else }}256Mi{{ end }}"
                    cpu: "{{ if hasKey .object.spec.template.spec.containers[0].resources.requests \"cpu\" }}{{ .object.spec.template.spec.containers[0].resources.requests.cpu }}{{ else }}250m{{ end }}"
```

This policy adds default values if resource limits and requests are not set for containers when Deployment resources are created or updated.

**Example Using JSON Patch:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-labels-json-patch
spec:
  rules:
  - name: add-labels
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchesJson6902: |-
        - op: add
          path: /metadata/labels/app.kubernetes.io~1managed-by
          value: kyverno
        - op: add
          path: /metadata/labels/environment
          value: "{{ request.object.metadata.namespace }}"
```

This policy uses JSON patch to add labels to Pods.

**How to Apply Mutate Policy:**
```bash
# Apply the policy
kubectl apply -f add-default-resources.yaml

# Create a Deployment without resource limits
kubectl apply -f deployment-without-resources.yaml

# Check the created Deployment
kubectl get deployment my-deployment -o yaml
# Result: Resource limits and requests are automatically added
```

**Issues with Other Options:**
- A. Validate: Only validates whether resources meet policy conditions, does not modify them.
- C. Generate: Creates additional resources when other resources are created, but does not modify existing resources.
- D. Verify: A policy type that verifies container image signatures, does not modify resources.
</details>
### 6. When is Kyverno's Generate policy useful?

A. Automatically create related resources when a resource is created
B. Automatically generate error messages during resource validation
C. Automatically create backups when a resource is deleted
D. Automatically create previous versions when a resource is updated

<details>
<summary>Show Answer</summary>

**Answer: A. Automatically create related resources when a resource is created**

**Explanation:**
Kyverno's Generate policy is useful for automatically creating related resources when a specific resource is created. This policy type helps manage dependencies between resources, automate standard configurations, and maintain consistent environments.

Main use cases for Generate policies:
1. **Create default resources when a namespace is created**: Automatically create resources like NetworkPolicy, ResourceQuota, LimitRange when a namespace is created.
2. **Create related resources when an application is deployed**: Automatically create related Service, ConfigMap, Secret when a Deployment is created.
3. **Automate standard configurations**: Create additional resources with standard configurations when specific types of resources are created.
4. **Multi-tenancy environment management**: Automatically create all necessary resources when a namespace is created for a new tenant.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-default-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    exclude:
      resources:
        namespaces:
        - "kube-system"
        - "kube-public"
        - "kube-node-lease"
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

This policy automatically creates a default NetworkPolicy in the namespace when a new namespace is created (excluding kube-system, kube-public, kube-node-lease). This NetworkPolicy blocks all ingress and egress traffic.

**synchronize field**:
- `synchronize: true`: Synchronizes the generated resource with the source resource. When the source resource is changed or deleted, the generated resource is also updated or deleted accordingly.
- `synchronize: false`: The generated resource exists independently of the source resource.

**Clone Policy Example:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: clone-secrets-across-namespaces
spec:
  rules:
  - name: clone-docker-registry-secret
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: Secret
      name: docker-registry
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      clone:
        namespace: default
        name: docker-registry
```

This policy clones the 'docker-registry' Secret from the 'default' namespace to the new namespace when a new namespace is created.

**Issues with Other Options:**
- B. Automatically generate error messages during resource validation: This is a feature of Validate policies.
- C. Automatically create backups when a resource is deleted: Kyverno does not provide automatic backup functionality when resources are deleted by default.
- D. Automatically create previous versions when a resource is updated: This is related to Kubernetes' resource version management mechanism and is not related to Kyverno's Generate policy.
</details>

### 7. What policy type is used in Kyverno to verify container image signatures?

A. ImagePolicy
B. VerifyImages
C. SignaturePolicy
D. ImageVerification

<details>
<summary>Show Answer</summary>

**Answer: B. VerifyImages**

**Explanation:**
The policy type used in Kyverno to verify container image signatures is `VerifyImages`. This policy type is used to confirm that container images come from trusted sources and to verify that images have not been tampered with.

VerifyImages policies provide the following features:
1. **Image signature verification**: Verifies the integrity and origin of images using digital signatures.
2. **Image registry restriction**: Restricts pulling images only from specific registries.
3. **Image tag restriction**: Restricts specific tags (e.g., prohibiting latest tag usage).
4. **Image digest verification**: Verifies image digests to ensure exact image versions are used.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-signatures
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - image: "docker.io/library/*"
      repository: "docker.io/library/*"
      key: |-
        -----BEGIN PUBLIC KEY-----
        MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE8xOUetsCa8AKa9F1hx3gUw1RcyZg
        rjMqwNZcDzDv3PpFtpSdwGzA1GRk7XBqDJJQa9Jekky0yvEUDjtwLFp7aw==
        -----END PUBLIC KEY-----
    - image: "ghcr.io/my-org/*"
      repository: "ghcr.io/my-org/*"
      roots: |-
        -----BEGIN CERTIFICATE-----
        MIICmTCCAj+gAwIBAgIUYzA4YTU5YjQ2OTk1MjNmMDI2OTVkMGYwDQYJKoZIhvcN
        AQELBQAwXDELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAkNBMRYwFAYDVQQHDA1TYW4g
        RnJhbmNpc2NvMQ8wDQYDVQQKDAZNeU9yZzEXMBUGA1UEAwwOY2EubXlvcmcubG9j
        YWwwHhcNMjMwNzIwMDAwMDAwWhcNMjQwNzE5MDAwMDAwWjBcMQswCQYDVQQGEwJV
        UzELMAkGA1UECAwCQ0ExFjAUBgNVBAcMDVNhbiBGcmFuY2lzY28xDzANBgNVBAoM
        Bk15T3JnMRcwFQYDVQQDDA5jYS5teW9yZy5sb2NhbDCBnzANBgkqhkiG9w0BAQEF
        AAOBjQAwgYkCgYEA1Jcpv/Gj0M3vaJQY4dLQJA9ZEMVCfOUzAFAgxm0DKJQSiQ+6
        HuQFTJjHnOJwYwKSAEGYe4JUg/fMUJMKl9BM7A9gjXKe0v8JMSyYGHVqTiPZ2RuW
        x7tO5Nh5jLz3GQYmZl0m7CRReY2zt9OUdRz2LR5xMPHitpy7aLGvGSsIZVECAwEA
        AaN7MHkwHQYDVR0OBBYEFPgVXUQGbNrGkFmXQkCXYvs8HzIIMB8GA1UdIwQYMBaA
        FPgVXUQGbNrGkFmXQkCXYvs8HzIIMA8GA1UdEwEB/wQFMAMBAf8wCwYDVR0PBAQD
        AgEGMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjANBgkqhkiG9w0BAQsF
        AAOBgQBB3TVGvZXKpZSzqPOzQzUNnCMzMEf1I7Qx9mKIqTKSZLqHYBDxHpQRQQNy
        aBBtMBgUn3KkZY8QdRUKj8Sw0PN+GV4bCXGwCJeRNZWO1FdaIVoUYKKWMPLYUUrJ
        UpZXfNQO8XUjIEqBK8RGn3MwYYwRF+OjDHGvpOf6hk0XPHGjlQ==
        -----END CERTIFICATE-----
```

This policy verifies signatures for two image sources:
1. docker.io/library/* images are verified using the specified public key.
2. ghcr.io/my-org/* images are verified using the specified certificate.

**Image Signing Tools:**
Kyverno integrates with various image signing tools:
1. **Cosign**: Part of the Sigstore project, a tool for signing and verifying container images.
2. **Notary**: Docker's content trust framework.
3. **GnuPG (GPG)**: Open-source encryption tool.

**Example of Image Signing and Verification Using Cosign:**
```bash
# Generate key pair
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key my-registry.io/my-image:tag

# Extract public key to use in Kyverno policy
cat cosign.pub
```

**Issues with Other Options:**
- A. ImagePolicy: A policy type not used in Kyverno.
- C. SignaturePolicy: A policy type not used in Kyverno.
- D. ImageVerification: A policy type not used in Kyverno.
</details>

### 8. What does the `background: false` setting mean in a Kyverno policy?

A. The policy does not run in the background
B. The policy does not apply to existing resources
C. The policy does not affect cluster background jobs
D. The policy does not apply to resources created by background processes

<details>
<summary>Show Answer</summary>

**Answer: B. The policy does not apply to existing resources**

**Explanation:**
The `background: false` setting in a Kyverno policy means that the policy does not apply to existing resources and only applies to newly created or updated resources. The default value is `background: true`, in which case the policy applies to all resources including existing ones.

Key characteristics of the `background` setting:
1. **Existing resource scanning**: When `background: true`, Kyverno periodically scans existing resources in the cluster to check policy compliance.
2. **Resource load**: Scanning many resources in large clusters can cause significant load, so it's better to use `background: true` only when necessary.
3. **Audit reports**: Background scan results are recorded in PolicyReport and ClusterPolicyReport CRDs.
4. **Scope**: Even when `background: false`, the policy still acts as an Admission Controller and applies to newly created or updated resources.

**Example Policy:**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  background: false  # Does not apply to existing resources
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
```

This policy applies only to newly created or updated Pods and does not scan existing Pods.

**When background scanning is needed:**
1. **Compliance auditing**: When you need to regularly check that all resources in the cluster comply with policies
2. **Security policy enforcement**: When you need to continuously monitor and report security vulnerabilities
3. **Configuration drift detection**: When you need to detect whether resource configurations deviate from policies over time

**When background scanning is not needed:**
1. **Performance optimization**: When you need to minimize resource usage in large clusters
2. **Managing only new resources**: When you want to leave existing resources as-is and only have new resources comply with policies
3. **Gradual policy introduction**: When you want to apply policies only to new workloads without affecting existing workloads

**Issues with Other Options:**
- A. The policy does not run in the background: This is a misinterpretation of the `background` setting. All Kyverno policies act as Admission Controllers.
- C. The policy does not affect cluster background jobs: This is unrelated to the `background` setting.
- D. The policy does not apply to resources created by background processes: This is unrelated to the `background` setting. Policies apply regardless of what process created the resource.
</details>
### 9. What resource is used in Kyverno to generate policy violation reports?

A. PolicyViolation
B. PolicyReport
C. ComplianceReport
D. AuditReport

<details>
<summary>Show Answer</summary>

**Answer: B. PolicyReport**

**Explanation:**
The resources used in Kyverno to generate policy violation reports are `PolicyReport` and `ClusterPolicyReport`. These resources are used to store and report policy check results.

Key characteristics of PolicyReport and ClusterPolicyReport:
1. **Scope**:
   - `PolicyReport`: Reports policy check results for resources within a specific namespace.
   - `ClusterPolicyReport`: Reports policy check results for cluster-level resources.

2. **Generation method**:
   - Background scan: Policies with `background: true` periodically scan resources and record results in reports.
   - Admission checks: Policy check results performed during resource creation or update are also recorded in reports.

3. **Report contents**:
   - Policy name
   - Scanned resource
   - Result (pass, fail, warn, error, skip)
   - Message
   - Severity
   - Category
   - Timestamp

**Example PolicyReport:**
```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: polr-ns-default
  namespace: default
summary:
  pass: 7
  fail: 3
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-labels
  rule: check-team-label
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: fail
  message: "label 'team' is required"
  severity: medium
  category: Best Practices
  timestamp:
    created: "2023-07-20T10:15:30Z"
- policy: require-probes
  rule: check-readiness-probe
  resource:
    kind: Pod
    name: nginx
    namespace: default
  status: pass
  timestamp:
    created: "2023-07-20T10:15:30Z"
```

**How to Query Reports:**
```bash
# Query namespace policy reports
kubectl get policyreport -n default

# Query cluster policy reports
kubectl get clusterpolicyreport

# Query specific report details
kubectl describe policyreport polr-ns-default -n default
```

**Policy Report Integration:**
Kyverno's policy reports follow the PolicyReport CRD specification defined by the Kubernetes Policy Working Group. This allows results from various policy engines (Kyverno, OPA Gatekeeper, etc.) to be reported in a consistent format.

**How to Use Reports:**
1. **Compliance monitoring**: Continuously monitor the policy compliance status of the cluster.
2. **Audit evidence**: Provide evidence needed for compliance audits.
3. **Troubleshooting**: Help identify and resolve policy violations.
4. **Trend analysis**: Analyze policy compliance trends over time.

**Issues with Other Options:**
- A. PolicyViolation: A resource type not used in Kyverno.
- C. ComplianceReport: A resource type not used in Kyverno.
- D. AuditReport: A resource type not used in Kyverno.
</details>

### 10. What command-line tool can be used to test policies in Kyverno?

A. kyverno-cli
B. kubectl-kyverno
C. kyverno-test
D. policy-test

<details>
<summary>Show Answer</summary>

**Answer: B. kubectl-kyverno**

**Explanation:**
The command-line tool that can be used to test policies in Kyverno is `kubectl-kyverno`. This tool works as a kubectl plugin and helps test, validate, and manage Kyverno policies.

Key features of `kubectl-kyverno`:
1. **Policy testing**: Simulates policy application results against resources.
2. **Policy validation**: Validates policy syntax and structure.
3. **Policy generation**: Generates policy templates for common use cases.
4. **Policy application**: Applies policies to the cluster.

**Installation Method:**
```bash
# Installation using krew
kubectl krew install kyverno

# Direct download and installation
curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
sudo mv kubectl-kyverno /usr/local/bin/
```

**Key Commands:**

1. **Policy testing**:
```bash
# Test policy application against a resource
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml

# Test multiple policies
kubectl kyverno apply /path/to/policies/ --resource /path/to/resources/

# Check mutation results
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml -o yaml
```

2. **Policy validation**:
```bash
# Validate policy syntax and structure
kubectl kyverno validate /path/to/policy.yaml
```

3. **Policy generation**:
```bash
# Generate a common policy template
kubectl kyverno create disallow-latest-tag

# Check available template list
kubectl kyverno create --help
```

4. **Policy application**:
```bash
# Apply policy to the cluster
kubectl kyverno apply /path/to/policy.yaml --cluster
```

**Test Example:**
```bash
# Create policy file
cat > require-labels.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: enforce
  rules:
  - name: check-team-label
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "label 'team' is required"
      pattern:
        metadata:
          labels:
            team: "?*"
EOF

# Create resource file
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.19.0
EOF

# Test the policy
kubectl kyverno apply require-labels.yaml --resource pod.yaml

# Result:
# applying 1 policy to 1 resource...
# resource Pod/default/nginx failed validation
# policy require-labels: rule check-team-label failed: label 'team' is required
```

**Usage in CI/CD Pipeline:**
```yaml
# GitHub Actions example
name: Kyverno Policy Test

on:
  pull_request:
    paths:
      - 'policies/**'
      - 'resources/**'

jobs:
  test-policies:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Install kubectl-kyverno
        run: |
          curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
          sudo mv kubectl-kyverno /usr/local/bin/

      - name: Validate policies
        run: |
          kubectl kyverno validate policies/

      - name: Test policies against resources
        run: |
          kubectl kyverno apply policies/ --resource resources/
```

**Issues with Other Options:**
- A. kyverno-cli: A tool name not used in Kyverno.
- C. kyverno-test: A tool name not used in Kyverno.
- D. policy-test: A tool name not used in Kyverno.
</details>
