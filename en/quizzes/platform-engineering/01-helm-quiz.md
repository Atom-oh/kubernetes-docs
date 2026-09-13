# Helm Package Manager Quiz

> **Related guide**: [Helm](../../platform-engineering/01-helm.md)

These 20 question topics follow the Helm 3.21.3 / 4.3.0 review.

## Multiple Choice

### 1. What did removing Tiller change?

- A) Only chart size changes.
- B) The client uses its Kubernetes credentials and RBAC.
- C) Every chart becomes safe.
- D) The Kubernetes API is no longer needed.

<details>
<summary>Show answer</summary>

**Answer: B**

Helm 3 removed Tiller and simplified the permission path. Unsafe manifests and broad client permissions still require review.

</details>

### 2. What is values.yaml for?

- A) Chart metadata
- B) Default configuration data consumed by templates
- C) Release history
- D) An automatically executed template

<details>
<summary>Show answer</summary>

**Answer: B**

Only values consumed by templates have an effect. Files and --set variants can override them; embedded template strings are not automatically evaluated.

</details>

### 3. What does helm upgrade --install do?

- A) Always creates a new release
- B) Always deletes and recreates
- C) Installs a missing release or upgrades an existing one
- D) Guarantees idempotency of external operations

<details>
<summary>Show answer</summary>

**Answer: C**

It selects installation or upgrade. Hooks, random values and external database changes need not be idempotent.

</details>

### 4. What is Release.Name?

- A) Chart name
- B) Cluster name
- C) The chosen release name
- D) Image tag

<details>
<summary>Show answer</summary>

**Answer: C**

In `helm install demo ./chart`, the name is demo. It differs from chart name, appVersion and release revision.

</details>

### 5. What does a dependency condition specify?

- A) Image tag
- B) A values path controlling whether the dependency is enabled
- C) Registry password
- D) Pod priority

<details>
<summary>Show answer</summary>

**Answer: B**

For alias cache, use a real Boolean path such as cache.enabled. Test absent-path behavior and distinguish it from values passed into the subchart.

</details>

### 6. When does a pre-upgrade hook run?

- A) After deletion
- B) After rendering and before ordinary resources are upgraded
- C) Always after new Pods are Ready
- D) Only after rollback

<details>
<summary>Show answer</summary>

**Answer: B**

A database migration must account for database availability, retries, failure and compatibility with the previous app. Rollback does not automatically undo database changes.

</details>

### 7. What is the purpose of ordinary helm template?

- A) Install into a cluster
- B) Render manifests locally
- C) Validate real webhooks
- D) Roll back automatically

<details>
<summary>Show answer</summary>

**Answer: B**

Default local rendering does not prove admission, RBAC, image execution or connectivity. Distinguish it from options that contact a server.

</details>

### 8. What is _helpers.tpl for?

- A) Store metadata
- B) Define reusable named templates
- C) Store default values
- D) Store release history

<details>
<summary>Show answer</summary>

**Answer: B**

Use define for named templates and include to consume them. Prefix names to avoid collisions and pass the intended context.

</details>

### 9. What does helm get values demo --all output?

- A) Only user overrides
- B) Computed values including chart defaults
- C) Only manifests
- D) Only history

<details>
<summary>Show answer</summary>

**Answer: B**

Select the correct namespace and release. Values can contain sensitive information, so protect the output.

</details>

### 10. Why combine toYaml with nindent?

- A) Automatic encryption
- B) Serialize structured values to YAML and add a newline/indentation
- C) Generate only JSON
- D) Always convert numbers to strings

<details>
<summary>Show answer</summary>

**Answer: B**

Unlike indent, nindent also prepends a newline. Match the indentation required at the insertion point.

</details>

## Short Answer

### 1. What is the default release storage resource?

<details>
<summary>Show answer</summary>

A Secret in the release namespace, named `sh.helm.release.v1.<release>.v<revision>`. Other backends such as ConfigMap or SQL can be configured. Base64 is not encryption.

</details>

### 2. Which lock file does dependency update create, and what are its limits?

<details>
<summary>Show answer</summary>

Chart.lock. dependency build uses its locked versions, but the lock alone does not guarantee artifact integrity, pinned images or complete reproducibility.

</details>

### 3. Which empty values matter when using default?

<details>
<summary>Show answer</summary>

False, zero, empty strings and collections count as empty. Check presence and type when explicit false/zero must be preserved. default does not protect every nested lookup.

</details>

### 4. Which annotation controls hook ordering?

<details>
<summary>Show answer</summary>

`helm.sh/hook-weight`. Lower weights run first within the phase, including negative weights. Also consider kind/name tie ordering, Job completion and timeouts.

</details>

### 5. When and why is NOTES.txt used?

<details>
<summary>Show answer</summary>

It templates instructions shown after successful install/upgrade and available through `helm get notes`. Keep instructions accurate and avoid secrets. Notes do not prove application readiness.

</details>

## Hands-on

### 1. Install the example as web-server in frontend with three replicas.

<details>
<summary>Show answer</summary>

```bash
helm install web-server examples/platform/helm/reviewed-app \
  --namespace frontend --create-namespace \
  --set replicaCount=3
```

Run from the repository root with an approved cluster context and permissions. This audit ran lint/template/package, not installation.

</details>

### 2. How should LOG_LEVEL=debug and MAX_CONNECTIONS="100" render as env?

<details>
<summary>Show answer</summary>

```yaml
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: MAX_CONNECTIONS
    value: "100"
```

Range over the map and quote each value so both remain strings. Go templates traverse maps with basic ordered keys in key order; this is distinct from list ordering.

</details>

### 3. Write a helper for chart, release and appVersion labels.

<details>
<summary>Show answer</summary>

```text
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
```

Pass the intended root context and indent at the call site. appVersion is metadata and does not automatically select an image tag.

</details>

## Advanced

### 1. What is needed for Blue/Green and canary delivery with Helm?

<details>
<summary>Show answer</summary>

Blue/Green requires two Deployments with labels and an actual Service template that selects the active color after validation. Template strings inside values.yaml are not automatically evaluated. Canary requires real routes/subsets or a rollout controller, weights, observation metrics and abort conditions. Values alone do not create automated analysis or rollback. Account for database compatibility and in-flight requests.

</details>

### 2. Design chart security and secret management.

<details>
<summary>Show answer</summary>

Validate required values and types with a supported values.schema.json, and pin reviewed chart/image revisions. Connect required ServiceAccounts and RoleBindings with minimal API permissions. A Secret volume does not justify granting the app access to all Secrets. Keep secret values out of defaults, CLI arguments and debug logs; plan approved file mounts, rotation and rereading. ESO v1, Sealed Secrets and helm-secrets require their controllers/plugins and provider/key permissions. Check whether decrypted values enter release records. Combine a non-root UID, dropped capabilities, a read-only root and required writable volumes, then verify actual image compatibility.

</details>
