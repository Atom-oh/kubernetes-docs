# ArgoCD Applications

> **Supported Versions**: ArgoCD v2.9+
> **Last Updated**: February 21, 2026

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
          value: LoadBalancer
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### From Helm Repository

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: prometheus
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: 55.5.0
    helm:
      releaseName: prometheus
      values: |
        prometheus:
          prometheusSpec:
            retention: 30d
            storageSpec:
              volumeClaimTemplate:
                spec:
                  storageClassName: gp3
                  resources:
                    requests:
                      storage: 100Gi
        grafana:
          enabled: true
          adminPassword: admin
        alertmanager:
          enabled: true
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring
```

#### With Values from External Files

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app-with-external-values
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://charts.bitnami.com/bitnami
    chart: nginx
    targetRevision: 15.4.0
    helm:
      valueFiles:
        - $values/production/nginx-values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: web
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
      commonLabels:
        environment: production
        team: platform
      commonAnnotations:
        owner: platform-team@example.com
      images:
        - myregistry/myapp:v1.2.3
        - name: myregistry/sidecar
          newTag: v2.0.0
      replicas:
        - name: my-deployment
          count: 5
      patches:
        - target:
            kind: Deployment
            name: my-deployment
          patch: |-
            - op: replace
              path: /spec/template/spec/containers/0/resources/limits/memory
              value: 2Gi
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

### OCI Artifacts (v2.8+)

Deploy from OCI-compliant registries:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: oci-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: 123456789012.dkr.ecr.us-west-2.amazonaws.com/my-manifests
    targetRevision: v1.0.0
    path: .
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

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
        tlas:
          - name: config
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

ArgoCD v2.6+ supports multiple sources in a single application, enabling complex deployment scenarios.

### Combining Helm Chart with Values from Git

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: multi-source-app
  namespace: argocd
spec:
  project: default
  sources:
    # Primary source: Helm chart from registry
    - repoURL: https://charts.bitnami.com/bitnami
      chart: postgresql
      targetRevision: 14.0.0
      helm:
        valueFiles:
          - $values/environments/production/postgresql-values.yaml

    # Values source: Git repository
    - repoURL: https://github.com/myorg/helm-values.git
      targetRevision: HEAD
      ref: values

  destination:
    server: https://kubernetes.default.svc
    namespace: database
```

### Multiple Applications in One

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-stack
  namespace: argocd
spec:
  project: default
  sources:
    # Monitoring stack
    - repoURL: https://prometheus-community.github.io/helm-charts
      chart: kube-prometheus-stack
      targetRevision: 55.5.0
      helm:
        releaseName: monitoring

    # Logging stack
    - repoURL: https://grafana.github.io/helm-charts
      chart: loki-stack
      targetRevision: 2.10.0
      helm:
        releaseName: logging

    # Custom dashboards from Git
    - repoURL: https://github.com/myorg/dashboards.git
      targetRevision: HEAD
      path: grafana-dashboards

  destination:
    server: https://kubernetes.default.svc
    namespace: observability
```

## Destination Configuration

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

ArgoCD assesses application health using built-in and custom checks.

### Built-in Health Checks

ArgoCD includes health checks for standard Kubernetes resources:

| Resource | Healthy When |
|----------|--------------|
| Deployment | All replicas available |
| StatefulSet | All replicas ready |
| DaemonSet | Desired equals scheduled |
| ReplicaSet | All replicas available |
| Service | Endpoints exist |
| Ingress | Load balancer assigned |
| PersistentVolumeClaim | Bound |
| Pod | Running and ready |
| Job | Succeeded |

### Custom Health Checks (Lua)

Define custom health checks in `argocd-cm`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.customizations.health.certmanager.io_Certificate: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.conditions ~= nil then
        for i, condition in ipairs(obj.status.conditions) do
          if condition.type == "Ready" and condition.status == "False" then
            hs.status = "Degraded"
            hs.message = condition.message
            return hs
          end
          if condition.type == "Ready" and condition.status == "True" then
            hs.status = "Healthy"
            hs.message = "Certificate is ready"
            return hs
          end
        end
      end
    end
    hs.status = "Progressing"
    hs.message = "Waiting for certificate"
    return hs

  resource.customizations.health.argoproj.io_Rollout: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.phase == "Healthy" then
        hs.status = "Healthy"
        hs.message = "Rollout is healthy"
      elseif obj.status.phase == "Paused" then
        hs.status = "Suspended"
        hs.message = "Rollout is paused"
      elseif obj.status.phase == "Progressing" then
        hs.status = "Progressing"
        hs.message = "Rollout in progress"
      else
        hs.status = "Degraded"
        hs.message = obj.status.message or "Rollout degraded"
      end
    else
      hs.status = "Progressing"
      hs.message = "Waiting for rollout status"
    end
    return hs
```

### Health Check for AWS Resources (ACK)

```yaml
resource.customizations.health.s3.services.k8s.aws_Bucket: |
  hs = {}
  if obj.status ~= nil then
    if obj.status.ackResourceMetadata ~= nil and obj.status.ackResourceMetadata.arn ~= nil then
      hs.status = "Healthy"
      hs.message = "Bucket created: " .. obj.status.ackResourceMetadata.arn
    else
      hs.status = "Progressing"
      hs.message = "Waiting for bucket creation"
    end
  else
    hs.status = "Progressing"
    hs.message = "Waiting for status"
  end
  return hs
```

## Resource Hooks

Resource hooks allow running jobs at specific points during sync.

### Hook Types

| Hook | When Executed |
|------|---------------|
| `PreSync` | Before sync starts |
| `Sync` | During sync (after PreSync) |
| `PostSync` | After sync succeeds |
| `SyncFail` | After sync fails |
| `Skip` | Skipped during sync |

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
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
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
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              curl -X POST $SLACK_WEBHOOK \
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
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              for i in $(seq 1 10); do
                if curl -sf http://my-service:8080/health; then
                  echo "Health check passed"
                  exit 0
                fi
                echo "Attempt $i failed, retrying..."
                sleep 5
              done
              echo "Health check failed"
              exit 1
```

## Ignore Differences

Configure ArgoCD to ignore specific differences during comparison.

### By JSON Pointer

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
      - /spec/replicas
      - /spec/template/spec/containers/0/image
```

### By JQ Path Expression

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jqPathExpressions:
      - .spec.template.spec.containers[].resources
      - .metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
```

### By Name

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
      - /spec/replicas
```

### Managed Fields (Kubernetes Server-Side Apply)

```yaml
ignoreDifferences:
  - group: "*"
    kind: "*"
    managedFieldsManagers:
      - kube-controller-manager
      - cluster-autoscaler
```

### Global Ignore in argocd-cm

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.compareoptions: |
    ignoreAggregatedRoles: true
    ignoreResourceStatusField: all

  resource.customizations.ignoreDifferences.all: |
    managedFieldsManagers:
      - kube-controller-manager
    jsonPointers:
      - /metadata/annotations/kubectl.kubernetes.io~1last-applied-configuration
```

## App of Apps Pattern

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

```yaml
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
    targetRevision: 55.5.0
    helm:
      values: |
        prometheus:
          prometheusSpec:
            retention: {{ .Values.monitoring.retention | default "15d" }}
            replicas: {{ .Values.monitoring.replicas | default 2 }}
        grafana:
          enabled: true
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

Control the order of child application deployment:

```yaml
# apps/templates/cert-manager.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cert-manager
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-3"  # Deploy first
spec:
  # ...

# apps/templates/ingress.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ingress-controller
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-2"  # Deploy second
spec:
  # ...

# apps/templates/monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: monitoring
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "0"  # Deploy last
spec:
  # ...
```

## Revision History and Rollback

### View History

```bash
# CLI
argocd app history my-app

# Output
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ghi9012
```

### Rollback

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
  source:
    repoURL: https://github.com/myorg/myrepo.git
    targetRevision: abc1234  # Specific commit for rollback
    path: manifests
```

## Quiz

To test what you've learned, try the [ArgoCD applications quiz](../../quizzes/gitops/argocd/02-applications-quiz.md).
