# Kyverno Policy 管理测验

本测验用于测试你对在 Kubernetes 中使用 Kyverno 进行 Policy 管理的理解。

## 测验题目

### 1. 什么是 Kyverno？

A. 一个 Kubernetes 原生的 Policy 引擎
B. 一个容器镜像扫描器
C. 一个集群监控工具
D. 一个 Service Mesh 实现

<details>
<summary>显示答案</summary>

**答案：A. 一个 Kubernetes 原生的 Policy 引擎**

**解析：**
Kyverno 是一个 Kubernetes 原生的 Policy 引擎，可以使用以 YAML 或 JSON 编写的 Policy 来验证、变更和生成 Kubernetes 资源。由于 Kyverno 使用 Kubernetes API 和 YAML 语法，你无需学习新的语言或工具即可定义和管理 Policy。

**主要特性：**
1. **原生 Kubernetes 集成**：直接与 Kubernetes API 配合工作。
2. **声明式 Policy 定义**：使用基于 YAML 的声明式 Policy。
3. **支持多种 Policy 类型**：支持 Validate、Mutate、Generate 和 Cleanup Policy。
4. **镜像验证**：提供容器镜像安全验证能力。
5. **审计和报告**：提供用于 Policy 合规性的审计和报告能力。

**示例 Policy：**
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

此 Policy 要求所有 Pod 都具有 'team' 标签。

**其他选项的问题：**
- B. 容器镜像扫描器：虽然 Kyverno 提供镜像验证能力，但它的主要用途是 Policy 管理。专用镜像扫描器包括 Trivy、Clair 等。
- C. 集群监控工具：Kyverno 不是监控工具。Prometheus、Grafana 等是监控工具。
- D. Service Mesh 实现：Kyverno 不是 Service Mesh。Istio、Linkerd 等是 Service Mesh 实现。
</details>

### 2. 以下哪一项不是 Kyverno 支持的 Policy 类型？

A. Validate
B. Mutate
C. Generate
D. Authenticate

<details>
<summary>显示答案</summary>

**答案：D. Authenticate**

**解析：**
Kyverno 支持以下 Policy 类型：

1. **Validate**：验证资源是否满足特定条件。
2. **Mutate**：自动修改资源。
3. **Generate**：当其他资源被创建时，自动创建额外资源。
4. **Verify Images**：验证容器镜像签名。
5. **Cleanup**：根据特定条件自动删除资源。

Kyverno 不直接支持 Authentication Policy 类型。Kubernetes 中的身份认证通常在 API server 层处理，并通过 RBAC（Role-Based Access Control）、OIDC（OpenID Connect）和 service account 等机制进行管理。

**各 Policy 类型示例：**

1. **Validate Policy 示例**：
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

2. **Mutate Policy 示例**：
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

3. **Generate Policy 示例**：
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

4. **Verify Images Policy 示例**：
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

5. **Cleanup Policy 示例**：
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

**其他选项说明：**
- A. Validate：Kyverno 支持的一种 Policy 类型，用于验证资源是否满足特定条件。
- B. Mutate：Kyverno 支持的一种 Policy 类型，用于自动修改资源。
- C. Generate：Kyverno 支持的一种 Policy 类型，用于在其他资源被创建时自动创建额外资源。
</details>
### 3. Kyverno Policy 中的 `validationFailureAction: enforce` 表示什么？

A. Policy 违规时仅生成警告
B. Policy 违规时阻止资源创建或更新
C. Policy 违规时自动修改资源
D. Policy 违规时删除资源

<details>
<summary>显示答案</summary>

**答案：B. Policy 违规时阻止资源创建或更新**

**解析：**
在 Kyverno Policy 中，`validationFailureAction: enforce` 是一个设置，表示当 Policy 违规时阻止资源创建或更新。应用此设置后，Policy 会拒绝创建或修改不满足 Policy 条件的资源，并向用户返回 Policy 违规消息。

`validationFailureAction` 有两个可能的值：
1. **enforce**：Policy 违规时阻止资源创建或更新。
2. **audit**：Policy 违规时允许资源创建或更新，但会记录违规。这对于测试 Policy 或审计当前状态很有用。

**示例 Policy：**
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

此 Policy 检查所有 Pod 容器是否配置了 readinessProbe，如果没有，则阻止 Pod 创建。

**如何应用该 Policy：**
```bash
# Apply the policy
kubectl apply -f require-probes.yaml

# Attempt to create a Pod without a readinessProbe
kubectl apply -f pod-without-probe.yaml
# Result: Error from server: error when creating "pod-without-probe.yaml": admission webhook "validate.kyverno.svc" denied the request:
# resource Pod/default/nginx was blocked due to the following policies: require-probes: check-readiness-probe: Readiness probe is required
```

**其他选项的问题：**
- A. Policy 违规时仅生成警告：这是 `validationFailureAction: audit` 的行为。
- C. Policy 违规时自动修改资源：这是 Mutate Policy 的行为，与 validationFailureAction 无关。
- D. Policy 违规时删除资源：Kyverno 不会在 Policy 违规时自动删除现有资源。Cleanup Policy 可以根据特定条件删除资源，但这是与 validationFailureAction 不同的机制。
</details>

### 4. Kyverno 使用哪个字段来选择 Policy 应用于哪些资源？

A. selector
B. match
C. target
D. apply

<details>
<summary>显示答案</summary>

**答案：B. match**

**解析：**
Kyverno 中用于选择 Policy 应用于哪些资源的字段是 `match`。此字段用于指定 Policy 规则适用资源的 kind、name、namespace、label 等。

`match` 字段可以包含以下子字段：
1. **resources**：指定资源 kind、name、namespace 等。
2. **subjects**：指定 Policy 适用的用户、组、service account。
3. **roles**：指定 Policy 适用的 role。
4. **clusterRoles**：指定 Policy 适用的 cluster role。

此外，`exclude` 字段可用于将特定资源排除在 Policy 应用范围之外。

**示例 Policy：**
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

此 Policy 仅应用于 'production' 和 'staging' namespace 中、带有 'app.kubernetes.io/managed-by: kustomize' 标签的 Deployment。

**复杂匹配示例：**
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

此 Policy 应用于 'production' 和 'staging' namespace 中带有 'tier: frontend' 标签的 Deployment 和 StatefulSet，并且仅在由 'admin@example.com' 用户或 'system:masters' 组创建或修改时生效。'kube-system' namespace 中的资源以及名为 'critical-deployment' 的资源会被排除。

**其他选项的问题：**
- A. selector：在 Kyverno 中，它作为 `match.resources.selector` 这样的子字段使用，但不是顶级字段。
- C. target：Kyverno Policy 中不使用的字段。
- D. apply：Kyverno Policy 中不使用的字段。
</details>

### 5. Kyverno 中哪种 Policy 类型会在 Policy 违规时自动修改资源？

A. Validate
B. Mutate
C. Generate
D. Verify

<details>
<summary>显示答案</summary>

**答案：B. Mutate**

**解析：**
Kyverno 中会在 Policy 违规时自动修改资源的 Policy 类型是 `Mutate`。Mutate Policy 会在资源创建或更新时自动修改资源，使其满足 Policy 要求。

Mutate Policy 可以使用以下方法修改资源：
1. **patchStrategicMerge**：使用 strategic merge patch 修改资源。
2. **patchesJson6902**：使用 JSON patch（RFC 6902）修改资源。
3. **overlay**：（旧版）提供与 patchStrategicMerge 相同功能的旧字段。

**示例 Policy：**
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

当创建或更新 Deployment 资源时，如果未为容器设置 resource limits 和 requests，此 Policy 会添加默认值。

**使用 JSON Patch 的示例：**
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

此 Policy 使用 JSON patch 向 Pod 添加标签。

**如何应用 Mutate Policy：**
```bash
# Apply the policy
kubectl apply -f add-default-resources.yaml

# Create a Deployment without resource limits
kubectl apply -f deployment-without-resources.yaml

# Check the created Deployment
kubectl get deployment my-deployment -o yaml
# Result: Resource limits and requests are automatically added
```

**其他选项的问题：**
- A. Validate：仅验证资源是否满足 Policy 条件，不会修改资源。
- C. Generate：在其他资源被创建时创建额外资源，但不会修改现有资源。
- D. Verify：一种用于验证容器镜像签名的 Policy 类型，不会修改资源。
</details>
### 6. Kyverno 的 Generate Policy 什么时候有用？

A. 当资源被创建时自动创建相关资源
B. 在资源验证期间自动生成错误消息
C. 当资源被删除时自动创建备份
D. 当资源被更新时自动创建先前版本

<details>
<summary>显示答案</summary>

**答案：A. 当资源被创建时自动创建相关资源**

**解析：**
Kyverno 的 Generate Policy 适用于在特定资源被创建时自动创建相关资源。这种 Policy 类型有助于管理资源之间的依赖关系、自动化标准配置，并维护一致的环境。

Generate Policy 的主要使用场景：
1. **创建 namespace 时创建默认资源**：创建 namespace 时自动创建 NetworkPolicy、ResourceQuota、LimitRange 等资源。
2. **部署应用时创建相关资源**：创建 Deployment 时自动创建相关的 Service、ConfigMap、Secret。
3. **自动化标准配置**：当特定类型的资源被创建时，创建带有标准配置的额外资源。
4. **多租户环境管理**：为新租户创建 namespace 时，自动创建所有必要资源。

**示例 Policy：**
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

此 Policy 会在创建新 namespace 时自动在该 namespace 中创建默认 NetworkPolicy（不包括 kube-system、kube-public、kube-node-lease）。此 NetworkPolicy 会阻止所有 ingress 和 egress 流量。

**synchronize 字段**：
- `synchronize: true`：将生成的资源与源资源同步。当源资源被更改或删除时，生成的资源也会相应更新或删除。
- `synchronize: false`：生成的资源独立于源资源存在。

**Clone Policy 示例：**
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

当创建新 namespace 时，此 Policy 会将 'docker-registry' Secret 从 'default' namespace 克隆到新的 namespace。

**其他选项的问题：**
- B. 在资源验证期间自动生成错误消息：这是 Validate Policy 的功能。
- C. 当资源被删除时自动创建备份：Kyverno 默认不提供在资源被删除时自动备份的功能。
- D. 当资源被更新时自动创建先前版本：这与 Kubernetes 的资源版本管理机制有关，与 Kyverno 的 Generate Policy 无关。
</details>

### 7. Kyverno 中用于验证容器镜像签名的 Policy 类型是什么？

A. ImagePolicy
B. VerifyImages
C. SignaturePolicy
D. ImageVerification

<details>
<summary>显示答案</summary>

**答案：B. VerifyImages**

**解析：**
Kyverno 中用于验证容器镜像签名的 Policy 类型是 `VerifyImages`。此 Policy 类型用于确认容器镜像来自可信来源，并验证镜像未被篡改。

VerifyImages Policy 提供以下功能：
1. **镜像签名验证**：使用数字签名验证镜像的完整性和来源。
2. **镜像 registry 限制**：限制只能从特定 registry 拉取镜像。
3. **镜像 tag 限制**：限制特定 tag（例如禁止使用 latest tag）。
4. **镜像 digest 验证**：验证镜像 digest，以确保使用精确的镜像版本。

**示例 Policy：**
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

此 Policy 会验证两个镜像来源的签名：
1. docker.io/library/* 镜像使用指定的 public key 进行验证。
2. ghcr.io/my-org/* 镜像使用指定的 certificate 进行验证。

**镜像签名工具：**
Kyverno 与多种镜像签名工具集成：
1. **Cosign**：Sigstore 项目的一部分，是用于签名和验证容器镜像的工具。
2. **Notary**：Docker 的 content trust framework。
3. **GnuPG (GPG)**：开源加密工具。

**使用 Cosign 进行镜像签名和验证的示例：**
```bash
# Generate key pair
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key my-registry.io/my-image:tag

# Extract public key to use in Kyverno policy
cat cosign.pub
```

**其他选项的问题：**
- A. ImagePolicy：Kyverno 中不使用的 Policy 类型。
- C. SignaturePolicy：Kyverno 中不使用的 Policy 类型。
- D. ImageVerification：Kyverno 中不使用的 Policy 类型。
</details>

### 8. Kyverno Policy 中的 `background: false` 设置表示什么？

A. Policy 不在后台运行
B. Policy 不适用于现有资源
C. Policy 不影响集群后台任务
D. Policy 不适用于由后台进程创建的资源

<details>
<summary>显示答案</summary>

**答案：B. Policy 不适用于现有资源**

**解析：**
Kyverno Policy 中的 `background: false` 设置表示该 Policy 不适用于现有资源，只适用于新创建或更新的资源。默认值为 `background: true`，在这种情况下，Policy 会适用于包括现有资源在内的所有资源。

`background` 设置的主要特点：
1. **现有资源扫描**：当 `background: true` 时，Kyverno 会定期扫描集群中的现有资源以检查 Policy 合规性。
2. **资源负载**：在大型集群中扫描大量资源可能会造成显著负载，因此最好仅在必要时使用 `background: true`。
3. **审计报告**：后台扫描结果记录在 PolicyReport 和 ClusterPolicyReport CRD 中。
4. **作用范围**：即使 `background: false`，Policy 仍然作为 Admission Controller 运行，并适用于新创建或更新的资源。

**示例 Policy：**
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

此 Policy 仅适用于新创建或更新的 Pod，不会扫描现有 Pod。

**何时需要后台扫描：**
1. **合规审计**：当你需要定期检查集群中的所有资源是否符合 Policy 时
2. **Security Policy 执行**：当你需要持续监控并报告安全漏洞时
3. **配置漂移检测**：当你需要检测资源配置是否随着时间推移偏离 Policy 时

**何时不需要后台扫描：**
1. **性能优化**：当你需要在大型集群中尽量减少资源使用时
2. **仅管理新资源**：当你希望现有资源保持原状，只要求新资源符合 Policy 时
3. **逐步引入 Policy**：当你希望仅将 Policy 应用于新 workload，而不影响现有 workload 时

**其他选项的问题：**
- A. Policy 不在后台运行：这是对 `background` 设置的误解。所有 Kyverno Policy 都作为 Admission Controller 运行。
- C. Policy 不影响集群后台任务：这与 `background` 设置无关。
- D. Policy 不适用于由后台进程创建的资源：这与 `background` 设置无关。无论资源由什么进程创建，Policy 都会应用。
</details>
### 9. Kyverno 中用于生成 Policy 违规报告的资源是什么？

A. PolicyViolation
B. PolicyReport
C. ComplianceReport
D. AuditReport

<details>
<summary>显示答案</summary>

**答案：B. PolicyReport**

**解析：**
Kyverno 中用于生成 Policy 违规报告的资源是 `PolicyReport` 和 `ClusterPolicyReport`。这些资源用于存储和报告 Policy 检查结果。

PolicyReport 和 ClusterPolicyReport 的主要特点：
1. **作用范围**：
   - `PolicyReport`：报告特定 namespace 内资源的 Policy 检查结果。
   - `ClusterPolicyReport`：报告集群级资源的 Policy 检查结果。

2. **生成方式**：
   - 后台扫描：带有 `background: true` 的 Policy 会定期扫描资源并将结果记录到报告中。
   - Admission 检查：在资源创建或更新期间执行的 Policy 检查结果也会记录到报告中。

3. **报告内容**：
   - Policy 名称
   - 被扫描的资源
   - 结果（pass、fail、warn、error、skip）
   - 消息
   - 严重性
   - 类别
   - 时间戳

**PolicyReport 示例：**
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

**如何查询报告：**
```bash
# Query namespace policy reports
kubectl get policyreport -n default

# Query cluster policy reports
kubectl get clusterpolicyreport

# Query specific report details
kubectl describe policyreport polr-ns-default -n default
```

**Policy Report 集成：**
Kyverno 的 Policy Report 遵循 Kubernetes Policy Working Group 定义的 PolicyReport CRD 规范。这使来自不同 Policy 引擎（Kyverno、OPA Gatekeeper 等）的结果能够以一致格式报告。

**如何使用报告：**
1. **合规监控**：持续监控集群的 Policy 合规状态。
2. **审计证据**：提供合规审计所需的证据。
3. **故障排查**：帮助识别并解决 Policy 违规。
4. **趋势分析**：分析 Policy 合规性随时间变化的趋势。

**其他选项的问题：**
- A. PolicyViolation：Kyverno 中不使用的资源类型。
- C. ComplianceReport：Kyverno 中不使用的资源类型。
- D. AuditReport：Kyverno 中不使用的资源类型。
</details>

### 10. 哪个命令行工具可用于测试 Kyverno 中的 Policy？

A. kyverno-cli
B. kubectl-kyverno
C. kyverno-test
D. policy-test

<details>
<summary>显示答案</summary>

**答案：B. kubectl-kyverno**

**解析：**
可用于测试 Kyverno 中 Policy 的命令行工具是 `kubectl-kyverno`。此工具作为 kubectl 插件运行，可帮助测试、验证和管理 Kyverno Policy。

`kubectl-kyverno` 的主要功能：
1. **Policy 测试**：针对资源模拟 Policy 应用结果。
2. **Policy 验证**：验证 Policy 语法和结构。
3. **Policy 生成**：为常见使用场景生成 Policy 模板。
4. **Policy 应用**：将 Policy 应用于集群。

**安装方法：**
```bash
# Installation using krew
kubectl krew install kyverno

# Direct download and installation
curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
sudo mv kubectl-kyverno /usr/local/bin/
```

**关键命令：**

1. **Policy 测试**：
```bash
# Test policy application against a resource
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml

# Test multiple policies
kubectl kyverno apply /path/to/policies/ --resource /path/to/resources/

# Check mutation results
kubectl kyverno apply /path/to/policy.yaml --resource /path/to/resource.yaml -o yaml
```

2. **Policy 验证**：
```bash
# Validate policy syntax and structure
kubectl kyverno validate /path/to/policy.yaml
```

3. **Policy 生成**：
```bash
# Generate a common policy template
kubectl kyverno create disallow-latest-tag

# Check available template list
kubectl kyverno create --help
```

4. **Policy 应用**：
```bash
# Apply policy to the cluster
kubectl kyverno apply /path/to/policy.yaml --cluster
```

**测试示例：**
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

**在 CI/CD Pipeline 中使用：**
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

**其他选项的问题：**
- A. kyverno-cli：Kyverno 中不使用的工具名称。
- C. kyverno-test：Kyverno 中不使用的工具名称。
- D. policy-test：Kyverno 中不使用的工具名称。
</details>
