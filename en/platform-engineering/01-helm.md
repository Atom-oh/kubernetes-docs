# Helm Package Manager

> **Last Updated**: September 12, 2026
> **Local validation**: Helm 3.21.3 / Helm 4.3.0

Helm renders charts and manages Kubernetes resources and release history. Chart version, appVersion, image tag/digest and release revision are different values. Helm 4 accepts existing apiVersion:v2 charts, but CLI/apply/wait behavior must be checked for the exact version.

## Core Concepts and Permissions

Helm 3 removed Tiller; clients use their own Kubernetes credentials/RBAC. Chart-repository/OCI-registry communication is separate from Kubernetes API access. Removing Tiller does not make unsafe charts or broad permissions harmless.

Release storage defaults to Secrets in the release namespace; alternatives such as ConfigMap/SQL backends can be configured. Stored release data includes manifests/values and may expose sensitive information. Base64 is not encryption; restrict access to release Secrets.

## Complete Local Chart Example

`examples/platform/helm/reviewed-app` contains the eight files below. Helm 3/4 lint/render outputs, packaging, value overrides and rejection of invalid replicaCount were tested. No Kubernetes installation or container execution occurred. Verify image digests, namespaces, hardware and policies before operations.

### Chart.yaml

```yaml
apiVersion: v2
name: reviewed-app
description: Offline Helm teaching chart
type: application
version: 0.1.0
appVersion: "1.30.4"
```

### values.yaml

```yaml
replicaCount: 1
image:
  repository: nginxinc/nginx-unprivileged
  tag: "1.30.4-alpine"
service:
  port: 8080
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
env:
  LOG_LEVEL: info
```

### values.schema.json

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "replicaCount",
    "image",
    "service"
  ],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 0,
      "maximum": 5
    },
    "image": {
      "type": "object",
      "required": [
        "repository",
        "tag"
      ],
      "properties": {
        "repository": {
          "type": "string",
          "minLength": 1
        },
        "tag": {
          "type": "string",
          "minLength": 1
        }
      }
    },
    "service": {
      "type": "object",
      "required": [
        "port"
      ],
      "properties": {
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535
        }
      }
    },
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}
```

### templates/_helpers.tpl

```text
{{- define "reviewed-app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- define "reviewed-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name | quote }}
app.kubernetes.io/instance: {{ .Release.Name | quote }}
{{- end -}}
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "reviewed-app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "reviewed-app.selectorLabels" . | nindent 8 }}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: web
        image: {{ printf "%s:%s" .Values.image.repository .Values.image.tag | quote }}
        ports:
        - name: http
          containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        env:
          {{- range $key, $value := .Values.env }}
        - name: {{ $key | quote }}
          value: {{ $value | quote }}
          {{- end }}
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 64Mi
```

### templates/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "reviewed-app.fullname" . }}
spec:
  type: ClusterIP
  selector:
    {{- include "reviewed-app.selectorLabels" . | nindent 4 }}
  ports:
  - name: http
    port: {{ .Values.service.port }}
    targetPort: http
```

### templates/NOTES.txt

```text
Inspect the rendered resources and prepare namespace/image compatibility before installation.
Release: {{ .Release.Name }}
Namespace: {{ .Release.Namespace }}
```

### .helmignore

```text
*.private
```

All helpers are defined, the Service targets a named container port, securityContext is in the manifest, and resources/env are wired from values into templates. An unused values entry has no effect. This basic chart does not create a database, Ingress or autoscaler.

### Local Checks

Run from the repository root and check the selected binary with `helm version --short`.

```bash
helm lint examples/platform/helm/reviewed-app
helm template demo examples/platform/helm/reviewed-app --namespace example
helm template demo examples/platform/helm/reviewed-app   --set replicaCount=3 --set-string env.MAX_CONNECTIONS=100
helm package examples/platform/helm/reviewed-app --destination ./chart-packages
```

Lint/template success does not validate admission, CEL, RBAC, image execution, Service connectivity or readiness. Test hooks must actually execute in a cluster. `helm template --api-versions` supplies offline capabilities; it does not install CRDs.

## Commands and Helm 3/4 Differences

| Purpose | Example and limits |
| --- | --- |
| Repositories | `helm repo add/update/list/remove`, `helm search repo`; OCI registries have separate login/pull flows |
| Install | `helm install demo ./chart -n example --create-namespace`; verify namespace/release existence |
| Install or upgrade | `helm upgrade --install`; hooks, random values and external state need not be idempotent |
| Inspect | `helm list -n example`, status/history/get values/get manifest; protect sensitive output |
| Computed values | `helm get values demo -n example --all` includes chart defaults |
| Rollback | `helm rollback demo REVISION -n example`; revision is not an image tag |
| Uninstall | `helm uninstall demo -n example`; inspect PVC/CRD/hook/external-resource lifecycle |

The old stable repository is archival, not a current default. Verify external chart/image availability, licensing, support and security and pin chart versions. Old Bitnami PostgreSQL12/Redis17 dependencies are no longer this example's defaults.

### Dry Runs and Waiting

Helm 4.3 distinguishes `--dry-run=client` and `--dry-run=server`. In this environment, 4.3 client mode passed without a cluster; 3.21.3 install client dry-run attempted cluster access and failed. Use the verified `helm template` path for offline rendering. Server mode needs cluster access/permissions and does not prove all webhook/external side effects.

In Helm 4.3, omitted --wait defaults to hookOnly; specifying --wait defaults to watcher, with legacy also available. `--rollback-on-failure` rolls failed upgrades back to a prior successful release. Its name differs from Helm 3's --atomic. `--force-replace` and `--force-conflicts` separately control replacement and server-side-apply conflicts; check exact-version help.

Rollback is not a transaction reversing DB migrations, external API effects or deleted data. Distinguish timeout, Pod readiness, Job completion and application SLOs.

## Templates and Values

Chart, Release, Values and Capabilities are context objects. range/with change dot context; use `$` when the root is needed. Capabilities reflects supplied discovery information, not universal compatibility.

include returns named-template output as a string and can be piped into nindent, which also inserts a newline. Prefix helper names to avoid subchart collisions and avoid unnecessary selector changes across upgrades.

default/coalesce treat false, zero, empty strings and collections as empty. Check existence/types separately when preserving explicit false/zero. A default does not protect every nested lookup whose parent map is absent.

values.yaml is data: embedded <code v-pre>{{ .Values... }}</code> is not automatically evaluated again. Chart authors can explicitly use tpl where needed, but must review input trust and template privileges. The former subchart storageClass and Blue/Green selector strings were not automatically wired.

For repeated files/overrides, rightmost values win; understand map merging and list replacement. Save dev/staging/prod as separate files instead of duplicate keys in one YAML document. Use --set-string for numeric-looking strings and version-supported --set-json for structures.

--reuse-values, --reset-values and --reset-then-reuse-values combine prior release values and new defaults differently. Review computed values and rendered diffs instead of relying on implicit behavior.

## Dependency Management

Chart.yaml declares dependency names, versions, repositories and optional aliases/conditions. This fragment assumes a **prepared local helper subchart**.

```yaml
dependencies:
- name: helper
  alias: cache
  version: 0.1.0
  repository: file://../dependency-child
  condition: cache.enabled
```

With an alias, place values under cache and use a matching condition. Test behavior when a condition path is absent. Global values matter only when the subchart consumes them; import-values requires matching child/parent export structure.

dependency update resolves Chart.yaml constraints and writes Chart.lock. build uses locked versions; without a lock it can resolve similarly to update. A lock alone does not establish tamper resistance, pinned runtime images or complete reproducibility. Manage chart digests/signatures, supply paths and image revisions. Local file-dependency update/build and alias on/off were exercised with Helm 3/4.

## Hooks, CRDs and Tests

Pre/post install, upgrade, rollback, delete and test hooks execute at their lifecycle stages. Lower weights run first; inspect kind/name ordering for ties. A pre-install migration may run before the chart's ordinary database resource exists.

Hook Jobs/Pods need real executables, images, Services/Secrets, permissions, timeouts and repeat-safe behavior. Plan cleanup with before-hook-creation/hook-succeeded/hook-failed and Job TTLs; uninstall need not remove all hook resources. Interpret post-install readiness in conjunction with --wait.

CRDs under crds/ differ from normal templates. Do not assume automatic upgrade/deletion or rollback of CRD schemas. Use explicit migration and custom-resource retention plans; deleting a CRD can remove custom-resource data.

helm test runs declared hooks. Simple HTTP connectivity does not validate databases, security, load or recovery. Blue/Green/canary needs real Deployments, Services/mesh routes, controllers and metric/rollback conditions. Values alone do not implement progressive delivery.

## GitOps and Security

Argo CD generally uses Helm as a template renderer, distinct from owning Helm release lifecycle. Flux helm-controller reconciles HelmRelease. Verify source/chart revisions, valuesFrom namespace/precedence, hook mapping, pruning and ownership; avoid competing controllers.

Do not place secrets in chart defaults, --set arguments or debug output. --hide-secret covers Kubernetes Secret output during dry-run, not general redaction of all values/logs. Existing Secret references delivered through app environment variables still violate file-credential policies. Use approved Secret volumes and file reread/rotation paths.

Prepare current APIs such as ESO v1 and their controllers separately. Sealed Secrets/helm-secrets require their controller/plugin, key/KMS access and decryption workflow; they are not Helm core features. Inspect whether decrypted values enter release records or logs.

ServiceAccounts/Roles alone do not grant workload permissions. Connect RoleBindings and serviceAccountName when required, and do not grant all-Secret get/list/watch merely for a Secret volume. The demo web chart needs no Kubernetes API credentials and disables token automount.

## Troubleshooting Order

| Symptom | Investigation and correction |
| --- | --- |
| Reused release name | Check namespace/state/history; choose intended upgrade or a new name |
| Existing-resource collision | Inspect owner annotations/labels/controllers; use a reviewed adoption/migration or rename |
| Failed release | Check causes/events/history and retry with verified revision/configuration |
| Missing helper | Check definitions, names, scope and root context |
| Schema failure | Inspect final merged values, types, required fields and ranges |

Deletion/force flags are not universal fixes. Review diffs, immutable fields, data retention and other controllers before choosing a mutation.

## Verification and References

All 764 guide lines, 462 quiz lines per locale and 58 unique blocks were reviewed. Checks covered complete-chart Helm 3/4 lint/template/package, overrides/negative schemas and local dependencies/aliases; 4.3 client dry-run passed. The 3.21.3 install dry-run cluster-access failure is recorded. No real Kubernetes installation, upgrade, rollback, hooks or app HTTP behavior was validated.

- [Helm install](https://helm.sh/docs/helm/helm_install/)
- [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Charts and values](https://helm.sh/docs/topics/charts/)
- [Chart hooks](https://helm.sh/docs/topics/charts_hooks/)
- [Dependency build](https://helm.sh/docs/helm/helm_dependency_build/)
- [Helm 4.3.0 release](https://github.com/helm/helm/releases/tag/v4.3.0)

[Helm quiz](../quizzes/platform-engineering/01-helm-quiz.md)
