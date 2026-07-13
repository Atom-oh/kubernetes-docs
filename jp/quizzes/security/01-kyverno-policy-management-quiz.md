# Kyverno Policy Management Quiz

このクイズでは、Kubernetes における Kyverno を使用した policy 管理についての理解を確認します。

## クイズ問題

### 1. Kyverno とは何ですか？

A. Kubernetes-native の policy engine
B. container image scanner
C. cluster monitoring tool
D. service mesh 実装

<details>
<summary>答えを表示</summary>

**答え: A. Kubernetes-native の policy engine**

**解説:**
Kyverno は Kubernetes-native の policy engine で、YAML または JSON で記述された policy を使用して Kubernetes resources を検証、変更、生成できます。Kyverno は Kubernetes API と YAML 構文を使用するため、新しい言語やツールを学習せずに policy を定義して管理できます。

**主な機能:**
1. **Native Kubernetes Integration**: Kubernetes API と直接連携します。
2. **Declarative Policy Definition**: YAML ベースの宣言的 policy を使用します。
3. **Various Policy Types Supported**: Validate、Mutate、Generate、Cleanup policy をサポートします。
4. **Image Verification**: container image のセキュリティ検証機能を提供します。
5. **Auditing and Reporting**: policy compliance のための監査およびレポート機能を提供します。

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

この policy は、すべての Pods に 'team' label があることを要求します。

**他の選択肢の問題点:**
- B. Container image scanner: Kyverno は image verification 機能を提供しますが、主な目的は policy 管理です。専用の image scanner には Trivy、Clair などがあります。
- C. Cluster monitoring tool: Kyverno は monitoring tool ではありません。Prometheus、Grafana などが monitoring tool です。
- D. Service mesh implementation: Kyverno は service mesh ではありません。Istio、Linkerd などが service mesh 実装です。
</details>

### 2. 次のうち、Kyverno がサポートしていない policy type はどれですか？

A. Validate
B. Mutate
C. Generate
D. Authenticate

<details>
<summary>答えを表示</summary>

**答え: D. Authenticate**

**解説:**
Kyverno は次の policy types をサポートします。

1. **Validate**: resources が特定の条件を満たしていることを検証します。
2. **Mutate**: resources を自動的に変更します。
3. **Generate**: 他の resources が作成されたときに追加の resources を自動的に作成します。
4. **Verify Images**: container image の signatures を検証します。
5. **Cleanup**: 特定の条件に基づいて resources を自動的に削除します。

Kyverno は Authentication policy type を直接サポートしていません。Kubernetes における Authentication は通常 API server レベルで処理され、RBAC (Role-Based Access Control)、OIDC (OpenID Connect)、service accounts などの仕組みを通じて管理されます。

**各 policy type の例:**

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

**他の選択肢の説明:**
- A. Validate: resources が特定の条件を満たしているかを検証する、Kyverno がサポートする policy type です。
- B. Mutate: resources を自動的に変更する、Kyverno がサポートする policy type です。
- C. Generate: 他の resources が作成されたときに追加の resources を自動的に作成する、Kyverno がサポートする policy type です。
</details>
### 3. Kyverno policy における `validationFailureAction: enforce` は何を意味しますか？

A. policy violation 時に warning のみを生成する
B. policy violation 時に resource の作成または更新をブロックする
C. policy violation 時に resource を自動的に変更する
D. policy violation 時に resource を削除する

<details>
<summary>答えを表示</summary>

**答え: B. policy violation 時に resource の作成または更新をブロックする**

**解説:**
Kyverno policy では、`validationFailureAction: enforce` は policy に違反したときに resource の作成または更新をブロックする設定です。この設定が適用されると、policy 条件を満たさない resources の作成または変更を拒否し、policy violation メッセージをユーザーに返します。

`validationFailureAction` には 2 つの値があります。
1. **enforce**: policy violation 時に resource の作成または更新をブロックします。
2. **audit**: policy violation 時でも resource の作成または更新を許可しますが、違反をログに記録します。これは policy のテストや現在の状態の監査に役立ちます。

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

この policy は、すべての Pod containers に readinessProbe が設定されていることを確認し、設定されていない場合は Pod の作成をブロックします。

**Policy の適用方法:**
```bash
# Apply the policy
kubectl apply -f require-probes.yaml

# Attempt to create a Pod without a readinessProbe
kubectl apply -f pod-without-probe.yaml
# Result: Error from server: error when creating "pod-without-probe.yaml": admission webhook "validate.kyverno.svc" denied the request:
# resource Pod/default/nginx was blocked due to the following policies: require-probes: check-readiness-probe: Readiness probe is required
```

**他の選択肢の問題点:**
- A. policy violation 時に warning のみを生成する: これは `validationFailureAction: audit` の動作です。
- C. policy violation 時に resource を自動的に変更する: これは mutate policies の動作であり、validationFailureAction とは関係ありません。
- D. policy violation 時に resource を削除する: Kyverno は policy violation 時に既存の resources を自動的に削除しません。Cleanup policies は特定の条件に基づいて resources を削除できますが、これは validationFailureAction とは異なる仕組みです。
</details>

### 4. Kyverno で policy を適用する resources を選択するために使用される field は何ですか？

A. selector
B. match
C. target
D. apply

<details>
<summary>答えを表示</summary>

**答え: B. match**

**解説:**
Kyverno で policy を適用する resources を選択するために使用される field は `match` です。この field は、policy rules を適用する resources の kind、name、namespace、labels などを指定するために使用されます。

`match` field には次の subfields を含めることができます。
1. **resources**: resource kind、name、namespace などを指定します。
2. **subjects**: policy が適用される users、groups、service accounts を指定します。
3. **roles**: policy が適用される roles を指定します。
4. **clusterRoles**: policy が適用される cluster roles を指定します。

さらに、`exclude` field を使用して、特定の resources を policy の適用対象から除外できます。

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

この policy は、'production' および 'staging' namespaces にあり、'app.kubernetes.io/managed-by: kustomize' label を持つ Deployments にのみ適用されます。

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

この policy は、'tier: frontend' label を持つ 'production' および 'staging' namespaces 内の Deployments と StatefulSets に適用され、'admin@example.com' user または 'system:masters' group によって作成または変更された場合にのみ適用されます。'kube-system' namespace 内の resources と 'critical-deployment' という名前の resources は除外されます。

**他の選択肢の問題点:**
- A. selector: Kyverno では `match.resources.selector` のような subfield として使用されますが、top-level field ではありません。
- C. target: Kyverno policies では使用されない field です。
- D. apply: Kyverno policies では使用されない field です。
</details>

### 5. Kyverno で policy violation 時に resources を自動的に変更する policy type はどれですか？

A. Validate
B. Mutate
C. Generate
D. Verify

<details>
<summary>答えを表示</summary>

**答え: B. Mutate**

**解説:**
Kyverno で policy violation 時に resources を自動的に変更する policy type は `Mutate` です。Mutate policies は、resources が作成または更新されるときに policy 要件を満たすよう自動的に変更します。

Mutate policies は次の方法で resources を変更できます。
1. **patchStrategicMerge**: strategic merge patch を使用して resources を変更します。
2. **patchesJson6902**: JSON patch (RFC 6902) を使用して resources を変更します。
3. **overlay**: (Legacy) patchStrategicMerge と同じ機能を提供する legacy field です。

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

この policy は、Deployment resources が作成または更新されるときに、containers に resource limits と requests が設定されていない場合、default values を追加します。

**JSON Patch を使用する例:**
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

この policy は JSON patch を使用して Pods に labels を追加します。

**Mutate Policy の適用方法:**
```bash
# Apply the policy
kubectl apply -f add-default-resources.yaml

# Create a Deployment without resource limits
kubectl apply -f deployment-without-resources.yaml

# Check the created Deployment
kubectl get deployment my-deployment -o yaml
# Result: Resource limits and requests are automatically added
```

**他の選択肢の問題点:**
- A. Validate: resources が policy 条件を満たしているかを検証するだけで、変更はしません。
- C. Generate: 他の resources が作成されたときに追加の resources を作成しますが、既存の resources は変更しません。
- D. Verify: container image signatures を検証する policy type であり、resources は変更しません。
</details>
### 6. Kyverno の Generate policy はどのような場合に役立ちますか？

A. resource が作成されたときに関連 resources を自動的に作成する
B. resource validation 中に error messages を自動的に生成する
C. resource が削除されたときに backups を自動的に作成する
D. resource が更新されたときに previous versions を自動的に作成する

<details>
<summary>答えを表示</summary>

**答え: A. resource が作成されたときに関連 resources を自動的に作成する**

**解説:**
Kyverno の Generate policy は、特定の resource が作成されたときに関連 resources を自動的に作成する場合に役立ちます。この policy type は、resources 間の依存関係を管理し、standard configurations を自動化し、一貫した environments を維持するのに役立ちます。

Generate policies の主なユースケース:
1. **namespace 作成時に default resources を作成する**: namespace が作成されたときに NetworkPolicy、ResourceQuota、LimitRange などの resources を自動的に作成します。
2. **application deployment 時に関連 resources を作成する**: Deployment が作成されたときに、関連する Service、ConfigMap、Secret を自動的に作成します。
3. **standard configurations を自動化する**: 特定の種類の resources が作成されたときに、standard configurations を持つ追加 resources を作成します。
4. **Multi-tenancy environment management**: 新しい tenant 用に namespace が作成されたときに、必要なすべての resources を自動的に作成します。

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

この policy は、新しい namespace が作成されたときに、その namespace 内に default NetworkPolicy を自動的に作成します（kube-system、kube-public、kube-node-lease は除外）。この NetworkPolicy はすべての ingress および egress traffic をブロックします。

**synchronize field**:
- `synchronize: true`: 生成された resource を source resource と同期します。source resource が変更または削除されると、生成された resource もそれに応じて更新または削除されます。
- `synchronize: false`: 生成された resource は source resource とは独立して存在します。

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

この policy は、新しい namespace が作成されたときに、'default' namespace から 'docker-registry' Secret を新しい namespace に clone します。

**他の選択肢の問題点:**
- B. resource validation 中に error messages を自動的に生成する: これは Validate policies の機能です。
- C. resource が削除されたときに backups を自動的に作成する: Kyverno は、resources が削除されたときに自動 backup 機能をデフォルトでは提供しません。
- D. resource が更新されたときに previous versions を自動的に作成する: これは Kubernetes の resource version management mechanism に関連するものであり、Kyverno の Generate policy とは関係ありません。
</details>

### 7. Kyverno で container image signatures を検証するために使用される policy type は何ですか？

A. ImagePolicy
B. VerifyImages
C. SignaturePolicy
D. ImageVerification

<details>
<summary>答えを表示</summary>

**答え: B. VerifyImages**

**解説:**
Kyverno で container image signatures を検証するために使用される policy type は `VerifyImages` です。この policy type は、container images が信頼できる sources から来ていることを確認し、images が改ざんされていないことを検証するために使用されます。

VerifyImages policies は次の機能を提供します。
1. **Image signature verification**: digital signatures を使用して images の integrity と origin を検証します。
2. **Image registry restriction**: 特定の registries からのみ images を pull できるよう制限します。
3. **Image tag restriction**: 特定の tags を制限します（例: latest tag の使用禁止）。
4. **Image digest verification**: image digests を検証して、正確な image versions が使用されていることを保証します。

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

この policy は 2 つの image sources の signatures を検証します。
1. docker.io/library/* images は、指定された public key を使用して検証されます。
2. ghcr.io/my-org/* images は、指定された certificate を使用して検証されます。

**Image Signing Tools:**
Kyverno はさまざまな image signing tools と統合します。
1. **Cosign**: Sigstore project の一部であり、container images に署名して検証するための tool です。
2. **Notary**: Docker の content trust framework です。
3. **GnuPG (GPG)**: open-source encryption tool です。

**Cosign を使用した Image Signing と Verification の例:**
```bash
# Generate key pair
cosign generate-key-pair

# Sign the image
cosign sign --key cosign.key my-registry.io/my-image:tag

# Extract public key to use in Kyverno policy
cat cosign.pub
```

**他の選択肢の問題点:**
- A. ImagePolicy: Kyverno では使用されない policy type です。
- C. SignaturePolicy: Kyverno では使用されない policy type です。
- D. ImageVerification: Kyverno では使用されない policy type です。
</details>

### 8. Kyverno policy における `background: false` 設定は何を意味しますか？

A. policy が background で実行されない
B. policy が既存の resources に適用されない
C. policy が cluster background jobs に影響しない
D. policy が background processes によって作成された resources に適用されない

<details>
<summary>答えを表示</summary>

**答え: B. policy が既存の resources に適用されない**

**解説:**
Kyverno policy における `background: false` 設定は、policy が既存の resources に適用されず、新しく作成または更新された resources にのみ適用されることを意味します。デフォルト値は `background: true` で、この場合 policy は既存のものを含むすべての resources に適用されます。

`background` 設定の主な特徴:
1. **Existing resource scanning**: `background: true` の場合、Kyverno は cluster 内の既存 resources を定期的に scan して policy compliance を確認します。
2. **Resource load**: 大規模な clusters で多数の resources を scan すると大きな load が発生する可能性があるため、必要な場合にのみ `background: true` を使用するのがよいです。
3. **Audit reports**: Background scan results は PolicyReport と ClusterPolicyReport CRDs に記録されます。
4. **Scope**: `background: false` の場合でも、policy は引き続き Admission Controller として動作し、新しく作成または更新された resources に適用されます。

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

この policy は新しく作成または更新された Pods にのみ適用され、既存の Pods は scan しません。

**background scanning が必要な場合:**
1. **Compliance auditing**: cluster 内のすべての resources が policies に準拠していることを定期的に確認する必要がある場合
2. **Security policy enforcement**: security vulnerabilities を継続的に監視し、レポートする必要がある場合
3. **Configuration drift detection**: resource configurations が時間の経過とともに policies から逸脱していないかを検出する必要がある場合

**background scanning が不要な場合:**
1. **Performance optimization**: 大規模な clusters で resource usage を最小化する必要がある場合
2. **Managing only new resources**: 既存 resources はそのままにして、新しい resources のみ policies に準拠させたい場合
3. **Gradual policy introduction**: 既存 workloads に影響を与えず、新しい workloads にのみ policies を適用したい場合

**他の選択肢の問題点:**
- A. policy が background で実行されない: これは `background` 設定の誤解です。すべての Kyverno policies は Admission Controllers として動作します。
- C. policy が cluster background jobs に影響しない: これは `background` 設定とは関係ありません。
- D. policy が background processes によって作成された resources に適用されない: これは `background` 設定とは関係ありません。Policies は resource を作成した process に関係なく適用されます。
</details>
### 9. Kyverno で policy violation reports を生成するために使用される resource は何ですか？

A. PolicyViolation
B. PolicyReport
C. ComplianceReport
D. AuditReport

<details>
<summary>答えを表示</summary>

**答え: B. PolicyReport**

**解説:**
Kyverno で policy violation reports を生成するために使用される resources は `PolicyReport` と `ClusterPolicyReport` です。これらの resources は、policy check results を保存してレポートするために使用されます。

PolicyReport と ClusterPolicyReport の主な特徴:
1. **Scope**:
   - `PolicyReport`: 特定の namespace 内の resources に対する policy check results をレポートします。
   - `ClusterPolicyReport`: cluster-level resources に対する policy check results をレポートします。

2. **Generation method**:
   - Background scan: `background: true` の policies が resources を定期的に scan し、結果を reports に記録します。
   - Admission checks: resource の作成または更新時に実行された policy check results も reports に記録されます。

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

**Reports のクエリ方法:**
```bash
# Query namespace policy reports
kubectl get policyreport -n default

# Query cluster policy reports
kubectl get clusterpolicyreport

# Query specific report details
kubectl describe policyreport polr-ns-default -n default
```

**Policy Report Integration:**
Kyverno の policy reports は、Kubernetes Policy Working Group によって定義された PolicyReport CRD specification に従います。これにより、さまざまな policy engines（Kyverno、OPA Gatekeeper など）の結果を一貫した format でレポートできます。

**Reports の使用方法:**
1. **Compliance monitoring**: cluster の policy compliance status を継続的に監視します。
2. **Audit evidence**: compliance audits に必要な evidence を提供します。
3. **Troubleshooting**: policy violations の特定と解決を支援します。
4. **Trend analysis**: policy compliance trends を時間の経過とともに分析します。

**他の選択肢の問題点:**
- A. PolicyViolation: Kyverno では使用されない resource type です。
- C. ComplianceReport: Kyverno では使用されない resource type です。
- D. AuditReport: Kyverno では使用されない resource type です。
</details>

### 10. Kyverno で policies をテストするために使用できる command-line tool は何ですか？

A. kyverno-cli
B. kubectl-kyverno
C. kyverno-test
D. policy-test

<details>
<summary>答えを表示</summary>

**答え: B. kubectl-kyverno**

**解説:**
Kyverno で policies をテストするために使用できる command-line tool は `kubectl-kyverno` です。この tool は kubectl plugin として動作し、Kyverno policies のテスト、検証、管理を支援します。

`kubectl-kyverno` の主な機能:
1. **Policy testing**: resources に対する policy application results をシミュレートします。
2. **Policy validation**: policy syntax と structure を検証します。
3. **Policy generation**: 一般的な use cases 向けの policy templates を生成します。
4. **Policy application**: policies を cluster に適用します。

**Installation Method:**
```bash
# Installation using krew
kubectl krew install kyverno

# Direct download and installation
curl -L https://github.com/kyverno/kyverno/releases/download/v1.10.0/kubectl-kyverno_v1.10.0_linux_x86_64.tar.gz | tar -xvz
sudo mv kubectl-kyverno /usr/local/bin/
```

**主なコマンド:**

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

**CI/CD Pipeline での使用:**
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

**他の選択肢の問題点:**
- A. kyverno-cli: Kyverno では使用されない tool name です。
- C. kyverno-test: Kyverno では使用されない tool name です。
- D. policy-test: Kyverno では使用されない tool name です。
</details>
