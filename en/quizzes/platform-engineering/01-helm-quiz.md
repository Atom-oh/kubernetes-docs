# Helm Package Manager Quiz

> **Related Document**: [Helm Package Manager](../../platform-engineering/01-helm.md)

## Multiple Choice Questions

### 1. What is the primary reason Tiller was removed in Helm v3?

- A) To improve performance
- B) To enhance security and simplify architecture
- C) To reduce chart size
- D) For Kubernetes version compatibility

<details>
<summary>Show Answer</summary>

**Answer: B) To enhance security and simplify architecture**

**Explanation:**
Helm v2's Tiller ran with elevated privileges within the cluster, posing security risks. In Helm v3, Tiller was removed and the client communicates directly with the Kubernetes API, enhancing security and simplifying the architecture.

</details>

### 2. What is the primary purpose of the values.yaml file in a Helm Chart?

- A) To store chart metadata
- B) To define default configuration values used in templates
- C) To store Kubernetes manifests directly
- D) To define chart dependencies

<details>
<summary>Show Answer</summary>

**Answer: B) To define default configuration values used in templates**

**Explanation:**
The values.yaml file defines default configuration values used by chart templates. Users can override these values using the --set flag or -f flag to customize deployments for different environments.

</details>

### 3. What is the behavior of the `helm upgrade --install` command?

- A) Always installs a new release
- B) Always upgrades an existing release
- C) Installs if the release doesn't exist, upgrades if it does
- D) Deletes and reinstalls the release

<details>
<summary>Show Answer</summary>

**Answer: C) Installs if the release doesn't exist, upgrades if it does**

**Explanation:**
`helm upgrade --install` provides idempotent behavior. If the specified release doesn't exist, it installs a new one; if it exists, it upgrades it. This is particularly useful in CI/CD pipelines.

</details>

### 4. What does <code v-pre>{{ .Release.Name }}</code> reference in a Helm template?

- A) Chart name
- B) Kubernetes cluster name
- C) Name of the installed release
- D) Namespace name

<details>
<summary>Show Answer</summary>

**Answer: C) Name of the installed release**

**Explanation:**
`.Release.Name` is a Helm built-in object that references the release name specified in the `helm install` command. For example, in `helm install my-app chart/`, `.Release.Name` would be "my-app".

</details>

### 5. What is the purpose of the `condition` attribute in Chart.yaml's `dependencies` field?

- A) To specify the dependency chart version
- B) To specify the values path that enables/disables the dependency chart
- C) To specify the dependency chart repository URL
- D) To specify the dependency chart priority

<details>
<summary>Show Answer</summary>

**Answer: B) To specify the values path that enables/disables the dependency chart**

**Explanation:**
The `condition` attribute specifies a path in values.yaml that determines whether to enable the dependency chart. For example, `condition: postgresql.enabled` means the PostgreSQL subchart is only included when the `postgresql.enabled` value is true.

</details>

### 6. When is the `pre-upgrade` Helm Hook executed?

- A) Before release deletion
- B) After upgrade request, before resources are updated
- C) After all resources are created
- D) After rollback completion

<details>
<summary>Show Answer</summary>

**Answer: B) After upgrade request, before resources are updated**

**Explanation:**
The `pre-upgrade` Hook runs after receiving an upgrade request but before actual resource updates begin. It's commonly used for database migrations or backup operations.

</details>

### 7. What is the primary use of the `helm template` command?

- A) To deploy a chart to the cluster
- B) To render chart templates locally for verification
- C) To update chart dependencies
- D) To rollback a release

<details>
<summary>Show Answer</summary>

**Answer: B) To render chart templates locally for verification**

**Explanation:**
`helm template` renders chart templates locally, allowing you to preview the Kubernetes manifests that will be generated. This enables template verification without connecting to a cluster.

</details>

### 8. What is the purpose of the `_helpers.tpl` file in Helm?

- A) To store chart metadata
- B) To define reusable template helper functions
- C) To store default values
- D) To display post-installation messages

<details>
<summary>Show Answer</summary>

**Answer: B) To define reusable template helper functions**

**Explanation:**
The `_helpers.tpl` file defines helper functions (named templates) that are commonly used across multiple templates. It encapsulates repetitive logic like chart names, labels, and selectors.

</details>

### 9. What does the `helm get values my-release --all` command output?

- A) Only user-specified values
- B) All values including defaults
- C) The release manifest
- D) The release history

<details>
<summary>Show Answer</summary>

**Answer: B) All values including defaults**

**Explanation:**
Using the `--all` flag outputs all computed values, including both user-overridden values and the chart's default values from values.yaml.

</details>

### 10. Why are `toYaml` and `nindent` functions commonly used together in Helm charts?

- A) To convert YAML to JSON
- B) To insert complex values into YAML with proper indentation
- C) To Base64 encode values
- D) To wrap strings in quotes

<details>
<summary>Show Answer</summary>

**Answer: B) To insert complex values into YAML with proper indentation**

**Explanation:**
`toYaml` converts Go objects to YAML strings, and `nindent` applies the specified number of spaces for indentation. This combination is essential for correctly inserting complex structures like resources and annotations into templates.

</details>

## Short Answer Questions

### 1. What Kubernetes resource type is used to store release information in Helm v3?

<details>
<summary>Show Answer</summary>

**Answer: Secret**

**Explanation:**
Helm v3 stores release information as Secrets within the namespace where the release is deployed. The Secret name format is `sh.helm.release.v1.<release-name>.v<version>`.

</details>

### 2. What is the name of the lock file generated by the `helm dependency update` command?

<details>
<summary>Show Answer</summary>

**Answer: Chart.lock**

**Explanation:**
`helm dependency update` parses the dependencies in Chart.yaml and generates a Chart.lock file containing exact versions. This file ensures reproducible builds.

</details>

### 3. What function provides a default value when a value is empty in Helm templates?

<details>
<summary>Show Answer</summary>

**Answer: default**

**Explanation:**
The `default` function provides a default value when a value is empty or undefined. Usage example: <code v-pre>{{ .Values.image.tag | default .Chart.AppVersion }}</code>

</details>

### 4. What annotation controls the execution order of Helm Hooks?

<details>
<summary>Show Answer</summary>

**Answer: helm.sh/hook-weight**

**Explanation:**
The `helm.sh/hook-weight` annotation determines the execution order within the same Hook type. Lower numbers execute first, and negative values are allowed.

</details>

### 5. When is the NOTES.txt file in a Helm chart displayed to users?

<details>
<summary>Show Answer</summary>

**Answer: After helm install or helm upgrade completes successfully**

**Explanation:**
NOTES.txt is displayed to users after a successful installation or upgrade. It typically includes application access instructions and initial setup guidance.

</details>

## Hands-on Questions

### 1. Write a Helm command that meets the following requirements:

- Install bitnami/nginx chart as "web-server" release
- Deploy to "frontend" namespace (create if it doesn't exist)
- Set replicaCount to 3

<details>
<summary>Show Answer</summary>

```bash
helm install web-server bitnami/nginx \
  -n frontend --create-namespace \
  --set replicaCount=3
```

**Explanation:**
- `helm install web-server bitnami/nginx`: Install nginx chart as "web-server" release
- `-n frontend`: Specify frontend namespace
- `--create-namespace`: Create namespace if it doesn't exist
- `--set`: Override values inline

</details>

### 2. Predict the output of the following Helm template snippet:

```yaml
# values.yaml
env:
  LOG_LEVEL: debug
  MAX_CONNECTIONS: "100"

# template
env:
{{- range $key, $value := .Values.env }}
  - name: {{ $key }}
    value: {{ $value | quote }}
{{- end }}
```

<details>
<summary>Show Answer</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

**Explanation:**
- The `range` function iterates over the `.Values.env` map
- `$key` is the map key, `$value` is the map value
- The `quote` function wraps values in quotes
- Maps are sorted alphabetically

</details>

### 3. Write a `_helpers.tpl` template that meets the following requirements:

- Name: mychart.labels
- app.kubernetes.io/name: chart name
- app.kubernetes.io/instance: release name
- app.kubernetes.io/version: app version

<details>
<summary>Show Answer</summary>

```yaml
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

**Explanation:**
- `define` creates a reusable named template
- `.Chart.Name` references the chart name
- `.Release.Name` references the release name
- `.Chart.AppVersion` references the app version (quote ensures string type)

</details>

## Advanced Questions

### 1. Explain how to implement Blue-Green and Canary deployments using Helm charts.

<details>
<summary>Show Answer</summary>

**Blue-Green Deployment:**
```yaml
# values.yaml
deployment:
  activeColor: blue

blue:
  enabled: true
  image:
    tag: "v1.0.0"

green:
  enabled: true
  image:
    tag: "v2.0.0"

service:
  selector:
    color: "{{ .Values.deployment.activeColor }}"
```

**Implementation Strategy:**
1. Create two Deployment templates for Blue and Green
2. Switch Service selector using activeColor value
3. Set green.image.tag to new version during deployment
4. After verification, change deployment.activeColor to green
5. Immediately rollback to blue if issues arise

**Canary Deployment (with Istio):**
```yaml
# VirtualService for traffic distribution
http:
  - route:
      - destination:
          host: myapp
          subset: stable
        weight: 90
      - destination:
          host: myapp
          subset: canary
        weight: 10
```

**Implementation Strategy:**
1. Create two Deployments for Stable and Canary
2. Control traffic ratio using Istio VirtualService
3. Gradually increase Canary ratio (10% -> 25% -> 50% -> 100%)
4. Implement automatic rollback based on metric monitoring

</details>

### 2. Explain Helm chart security best practices and design a secret management strategy.

<details>
<summary>Show Answer</summary>

**Security Best Practices:**

1. **Value Validation (values.schema.json)**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["image"],
  "properties": {
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "pattern": "^[a-z0-9.-/]+$"
        }
      }
    }
  }
}
```

2. **RBAC Least Privilege Principle**
```yaml
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]  # Grant only necessary permissions
```

3. **Apply Pod Security Standards**
```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Secret Management Strategy:**

1. **External Secrets Manager Integration (AWS Secrets Manager)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: {{ include "mychart.fullname" . }}-secrets
  data:
    - secretKey: database-password
      remoteRef:
        key: myapp/database
        property: password
```

2. **Using Sealed Secrets**
```bash
# Encrypt secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml
```

3. **Helm Secrets Plugin**
```bash
# Use encrypted values file
helm secrets install myapp ./mychart -f secrets.yaml
```

</details>
