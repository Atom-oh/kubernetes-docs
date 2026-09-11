# ArgoCD Applications

> **Supported Versions**: Argo CD 3.5.2
> **Last Updated**: September 11, 2026

## Table of Contents
- [Application CRD Overview](#application-crd-overview)
- [Source Types](#source-types)
- [Multiple Sources](#multiple-sources)
- [Destination Configuration](#destination-configuration)
- [Health Assessment](#health-assessment)
- [Resource Hooks](#resource-hooks)
- [Ignore Differences](#ignore-differences)
- [App of Apps Pattern](#app-of-apps-pattern)

## Application CRD Overview

Examples are independent configurations. Replace myorg/accounts/clusters/paths with actual authorized sources. Choose source/sources, renderer and destination.server/name according to the scenario rather than enabling every alternative at once.

The Application CRD is the core resource in ArgoCD that defines how and where to deploy your applications. It connects a source repository to a target Kubernetes cluster.

### Full Specification

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-application
  namespace: argocd
  labels:
    app.kubernetes.io/name: my-application
    environment: production
  annotations:
    argocd.argoproj.io/sync-wave: "5"
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default

  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: manifests/production

  destination:
    server: https://kubernetes.default.svc
    namespace: my-app

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas

  info:
    - name: Documentation
      value: https://wiki.example.com/my-app
    - name: Owner
      value: platform-team

  revisionHistoryLimit: 10
```

Application.status is controller-reported state. To create Applications outside the control-plane namespace, an administrator must enable application.namespaces and the AppProject sourceNamespaces plus appropriate RBAC.

### Key Fields Explained

| Field | Description |
|-------|-------------|
| `project` | AppProject this application belongs to |
| `source` | Where to fetch manifests from |
| `destination` | Target cluster and namespace |
| `syncPolicy` | Automatic sync and retry behavior |
| `ignoreDifferences` | Fields to ignore when comparing |
| `info` | Custom metadata for display |
| `revisionHistoryLimit` | Number of deployment revisions to keep |

## Source Types

ArgoCD supports multiple source types for fetching Kubernetes manifests.

### Plain YAML/JSON Directory

The simplest source type - a directory containing Kubernetes manifests:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
    directory:
      recurse: true
      exclude: '{*.txt,*.md}'
      include: '*.yaml'
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
```

### Helm Charts

#### From Git Repository

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-helm-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/helm-charts.git
    targetRevision: HEAD
    path: charts/my-app
    helm:
      releaseName: my-app
      valueFiles:
        - values.yaml
        - values-production.yaml
      values: |
        replicaCount: 3
        image:
          tag: v1.2.3
      parameters:
        - name: service.type
          value: ClusterIP
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### From Helm Repository

A pinned small podinfo chart illustrates the source format. The final replicaCount is 3 because parameters override valuesObject. valuesObject supplies structured inline values; it does not automatically read environment variables.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-helm
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valuesObject:
        replicaCount: 2
        service:
          type: ClusterIP
        ui:
          message: "Managed by Argo CD"
      parameters:
      - name: replicaCount
        value: "3"
      passCredentials: false
      skipCrds: false
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

Precedence is parameters → valuesObject → values → valueFiles → chart defaults. Prefer one inline representation; when valuesObject exists it supplies the inline values. Enable passCredentials only when required because it can forward credentials to other domains. This baseline uses bundled Helm 4; do not arbitrarily select v2/v3.

#### With Values from External Files

A $values reference requires a matching ref source in spec.sources. The values repository/file must exist and be authorized.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-with-values
  namespace: argocd
spec:
  project: default
  sources:
  - repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valueFiles:
      - $values/environments/production/podinfo-values.yaml
  - repoURL: https://github.com/myorg/helm-values.git
    targetRevision: main
    ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

### Kustomize

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kustomize-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: HEAD
    path: overlays/production
    kustomize:
      namePrefix: prod-
      nameSuffix: -v1
      namespace: production
      labelWithoutSelector: true
      labelIncludeTemplates: true
      commonLabels:
        environment: production
        team: platform
      commonAnnotations:
        owner: platform-team@example.com
      images:
        - myregistry/myapp:v1.2.3
        - myregistry/sidecar:v2.0.0
      replicas:
        - name: my-deployment
          count: 5
      patches:
        - target:
            kind: Deployment
            name: my-deployment
          patch: |-
            - op: add
              path: /spec/progressDeadlineSeconds
              value: 600
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

### OCI Artifacts

General OCI sources use an oci:// URI and a path inside the expanded artifact. Replace this account/repository/tag with a published artifact. A normal container image is not automatically a manifest source.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: oci-manifests
  namespace: argocd
spec:
  project: default
  source:
    repoURL: oci://123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/my-manifests
    targetRevision: v1.0.0
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

Argo CD 3.5.2 requires one layer with a supported media type: by default application/vnd.oci.image.layer.v1.tar+gzip or Helm chart content tar+gzip. Validate other types with ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES and the artifact structure.

The Helm OCI form uses a chart field and a repository URL **without oci://**. This is a source fragment under Application.spec.

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

Match credentials to the source type: general OCI uses type: oci and an oci:// URL; Helm OCI uses type: helm, enableOCI: "true" and a scheme-less URL. ECR needs registry permissions and renewal/application of its 12-hour token; granting IRSA permissions does not update a Secret by itself.

### Jsonnet

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: jsonnet-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/jsonnet-configs.git
    targetRevision: HEAD
    path: environments/production
    directory:
      jsonnet:
        extVars:
          - name: environment
            value: production
          - name: replicas
            value: "3"
            code: true
        tlas:
          - name: config
            code: true
            value: |
              {
                "namespace": "production"
              }
        libs:
          - vendor/
          - lib/
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

## Multiple Sources

When sources is present, singular source is ignored. Combine configuration for one related application, such as a chart plus values repository; use ApplicationSet/App of Apps for independently managed platform stacks.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: podinfo-with-values
  namespace: argocd
spec:
  project: default
  sources:
  - repoURL: https://stefanprodan.github.io/podinfo
    chart: podinfo
    targetRevision: 6.15.0
    helm:
      valueFiles:
      - $values/environments/production/podinfo-values.yaml
  - repoURL: https://github.com/myorg/helm-values.git
    targetRevision: main
    ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: podinfo-demo
  syncPolicy:
    syncOptions: [CreateNamespace=true]
```

ref: values maps $values to that Git repository root. Without path it supplies only values; with path it also generates manifests there. A ref source cannot also specify chart. Duplicate group/kind/name/namespace resources use the last source and raise RepeatedResourceWarning; this is not an automatic field-by-field merge.

## Destination Configuration

Choose server or name for the registered destination. destination.namespace supplies the default for namespaced resources lacking their own namespace; CreateNamespace creates that destination only, not every namespace explicitly embedded in a chart. Use managedNamespaceMetadata with namespace creation and review ownership before updating an existing namespace.

### Using Server URL

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### Using Cluster Name

```yaml
destination:
  name: production-cluster  # Must match registered cluster name
  namespace: my-app
```

### Namespace Auto-Creation

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## Health Assessment

Synced describes compared desired/live fields, not proof that the service handles requests. Healthy follows configured per-resource checks. Custom resources without a check may be omitted from application health and need an appropriate definition.

### Built-in Health Checks

These summarize important 3.5.2 implementation checks, not complete predicates based on one replica counter.

| Resource | Important checks |
|---|---|
| Deployment | Observed generation, rollout progress/failure, updated/available replicas |
| StatefulSet | Generation, update strategy/partition, revisions and replica state |
| DaemonSet | Generation and desired/updated/available Pod counts |
| Pod | Phase, readiness and container termination/failure |
| Service | LoadBalancer waits for an address; other types do not validate endpoints |
| Ingress | Controller-reported loadBalancer address state |
| PVC | Bound state |
| Job | Incomplete Progressing, failed Degraded, completed Healthy, suspended Suspended |

### Custom Health Checks

Do not replace bundled Rollout/cert-manager Certificate checks with a simplistic phase comparison. The Certificate group is cert-manager.io; its bundled check handles Issuing before Ready. The ACK example below returns Progressing for missing status/conditions and does not equate ARN existence with Healthy. Validate the Ready/ACK.ResourceSynced and error conditions supplied by your ACK version. The example prefers Ready when present and otherwise falls back to ACK.ResourceSynced.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: argocd
data:
  resource.customizations.health.s3.services.k8s.aws_Bucket: |
    local hs = {status = "Progressing", message = "Waiting for ACK reconciliation"}
    local conditions = {}
    if obj.status ~= nil and obj.status.conditions ~= nil then
      conditions = obj.status.conditions
    end
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.Terminal" and condition.status == "True" then
        hs.status = "Degraded"
        hs.message = condition.message or "ACK reported a terminal error"
        return hs
      end
    end
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.Recoverable" and condition.status == "True" then
        hs.message = condition.message or "ACK is retrying a recoverable error"
        return hs
      end
    end
    local synchronized = nil
    local ready = nil
    for _, condition in ipairs(conditions) do
      if condition.type == "ACK.ResourceSynced" then synchronized = condition end
      if condition.type == "Ready" then ready = condition end
    end
    local reported = ready or synchronized
    if reported ~= nil then
      hs.message = reported.message or hs.message
      if reported.status == "True" then
        hs.status = "Healthy"
        hs.message = reported.message or "ACK reports the resource synchronized"
      end
    end
    return hs
```

This interprets controller-reported state; it does not query AWS directly. Merge the key into existing argocd-cm and test missing/waiting/ready/error/new-spec states with real CRs. EKS managed Argo CD provides ACK/kro checks, so inspect its existing checks and supported configuration first.

## Resource Hooks

PostSync waits for successful Sync and relevant Healthy resources. Explicit resource-selective sync does not run hooks. In 3.5.2, ApplyOutOfSyncOnly still runs hooks and records history. SyncFail handles eligible synchronization failures; do not rely on it as a guaranteed cleanup/backup path for every error, including manifest-generation failures.

Resource hooks allow running jobs at specific points during sync.

### Hook Types

| Hook | When Executed |
|------|---------------|
| `PreSync` | Before sync starts |
| `Sync` | During sync (after PreSync) |
| `PostSync` | After Sync succeeds and resources are Healthy |
| `SyncFail` | After sync fails |
| `Skip` | Manifest application is skipped |
| `PreDelete` | Before resources are deleted with the Application |
| `PostDelete` | After Application resources are deleted |

### Hook Delete Policies

| Policy | Behavior |
|--------|----------|
| `HookSucceeded` | Delete after hook succeeds |
| `HookFailed` | Delete after hook fails |
| `BeforeHookCreation` | Delete before new hook runs |

### Database Migration Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
    argocd.argoproj.io/sync-wave: "-5"
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: myapp/migrations:v1.2.3
          command: ["./migrate.sh"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
```

### Slack Notification Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: notify-deployment
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:8.22.0
          command:
            - sh
            - -c
            - |
              curl --fail --show-error --silent --connect-timeout 5 --max-time 20 -X POST "$SLACK_WEBHOOK" \
                -H 'Content-Type: application/json' \
                -d '{"text":"Deployment completed successfully!"}'
          env:
            - name: SLACK_WEBHOOK
              valueFrom:
                secretKeyRef:
                  name: slack-webhook
                  key: url
```

### Health Check Hook

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: smoke-test
          image: curlimages/curl:8.22.0
          command:
            - sh
            - -c
            - |
              for i in $(seq 1 10); do
                if curl --fail --show-error --silent --connect-timeout 3 --max-time 10 http://my-service:8080/health; then
                  echo "Health check passed"
                  exit 0
                fi
                echo "Attempt $i failed, retrying..."
                sleep 5
              done
              echo "Health check failed"
              exit 1
```

Fixed-name Jobs need lifecycle rules such as BeforeHookCreation for repeat runs. Preserve failure logs externally before cleanup; HookSucceeded cleanup follows Argo sync phase/result semantics. Prepare the migration image, database Secret and ServiceAccount and separately validate idempotence, locking and rollback compatibility. Hook failure does not automatically revert a database or existing Deployment. PreDelete/PostDelete apply to Application deletion, not ordinary sync pruning.

## Ignore Differences

Exclude only specific fields owned by a known other controller. This Application.spec fragment ignores HPA-managed replicas on my-deployment in production.

```yaml
spec:
  ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
    - /spec/replicas
  syncPolicy:
    syncOptions:
    - RespectIgnoreDifferences=true
```

ignoreDifferences normally affects comparison. RespectIgnoreDifferences=true extends it to synchronization, but initial creation without a live resource still applies the desired manifest. Broad image, secret, entire-resources or all-manager rules can hide important drift.

For webhook arrays, select by name rather than fixed indices and scope the resource name too. Use this only when the CA-injection controller and webhook identity are known.

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

Global resource.customizations.ignoreDifferences settings affect every Application. Prefer application-scoped rules; choose managedFieldsManagers only after inspecting which fields that manager actually owns.

## App of Apps Pattern

App of Apps is an administrative bootstrap pattern. Parent-source writers can affect powerful Applications/AppProjects in the management namespace; restrict write/review/destination privileges. Parent/child finalizers and pruning can cascade deletions. Creating child Applications in order does not by itself ensure child-workload readiness; validate Application health propagation, sync policy and wave behavior.

The App of Apps pattern allows managing multiple applications from a single parent application.

### Directory Structure

```
├── apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── namespace.yaml
│       ├── monitoring.yaml
│       ├── logging.yaml
│       ├── ingress.yaml
│       └── cert-manager.yaml
```

### Parent Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-apps
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/platform.git
    targetRevision: HEAD
    path: apps
    helm:
      values: |
        environment: production
        cluster: prod-us-west-2
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Child Application Template

This monitoring child pins kube-prometheus-stack 90.0.0. Review that chart's upgrade/CRD requirements and provision monitoring capacity separately. Pre-create a protected grafana-admin Secret in namespace monitoring with admin-user/admin-password keys; do not put admin credentials in the parent Git values.

```yaml
---
# apps/templates/monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monitoring-{{ .Values.environment }}
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 90.0.0
    helm:
      values: |
        prometheus:
          prometheusSpec:
            retention: {{ .Values.monitoring.retention | default "15d" }}
            replicas: {{ .Values.monitoring.replicas | default 2 }}
        grafana:
          enabled: true
          admin:
            existingSecret: grafana-admin
            userKey: admin-user
            passwordKey: admin-password
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Values File

```yaml
# apps/values.yaml
environment: production
cluster: prod-us-west-2

monitoring:
  retention: 30d
  replicas: 3

logging:
  retention: 7d

ingress:
  enabled: true
  class: alb
```

### Sync Waves for App of Apps

The following are metadata-only fragments; combine them with complete child specs. Ordering child Application creation is not a child-workload readiness guarantee: configure/verify child Application health propagation and sync policy.

```yaml
# Merge into the corresponding complete child Application metadata.
metadata:
  name: cert-manager
  annotations:
    argocd.argoproj.io/sync-wave: "-3"
---
metadata:
  name: ingress-controller
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
---
metadata:
  name: monitoring
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

## Revision History and Rollback

History rollback cannot be used while automated sync is enabled. Review the policy in its actual Git/ApplicationSet owner first. Rollback does not update Git, so later reconciliation may restore the Git state. Persist intended changes through an approved Git revert/revision change; database/external-state recovery is separate.

### View History

```bash
# CLI
argocd app history my-app

```

Example output (not shell commands):

```text
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ab89012
```

### Rollback

Choose an ID from the actual history. Applying a previous manifest revision and pruning extra resources are separate decisions.

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### Declarative Rollback

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: abc1234  # Specific commit for rollback
    path: manifests
```

## Quiz

To test what you've learned, try the [ArgoCD applications quiz](../../quizzes/gitops/argocd/02-applications-quiz.md).

## Versioned Review Sources

- [3.5.2 sources and Helm](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/user-guide/helm.md)
- [Multiple sources](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/user-guide/multiple_sources.md)
- [OCI source rules](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/user-guide/oci.md)
- [Sync options](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/user-guide/sync-options.md)
- [Phases, waves and hooks](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/user-guide/sync-waves.md)
- [Service health implementation](https://github.com/argoproj/argo-cd/blob/v3.5.2/gitops-engine/pkg/health/health_service.go)
- [ACK condition definitions](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
