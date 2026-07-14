# Aplicaciones de ArgoCD

> **Versiones compatibles**: ArgoCD v2.9+
> **Última actualización**: February 22, 2026

## Tabla de contenido
- [Descripción general del CRD Application](#application-crd-overview)
- [Tipos de fuentes](#source-types)
- [Fuentes múltiples](#multiple-sources)
- [Configuración de destino](#destination-configuration)
- [Evaluación de estado](#health-assessment)
- [Hooks de recursos](#resource-hooks)
- [Ignorar diferencias](#ignore-differences)
- [Patrón App of Apps](#app-of-apps-pattern)

## Descripción general del CRD Application

El CRD Application es el recurso principal de ArgoCD que define cómo y dónde implementar tus aplicaciones. Conecta un repositorio de origen con un clúster Kubernetes de destino.

### Especificación completa

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

### Explicación de los campos clave

| Campo | Descripción |
|-------|-------------|
| `project` | AppProject al que pertenece esta aplicación |
| `source` | Desde dónde obtener los manifiestos |
| `destination` | Clúster y namespace de destino |
| `syncPolicy` | Comportamiento de sincronización automática y reintento |
| `ignoreDifferences` | Campos que se deben ignorar durante la comparación |
| `info` | Metadatos personalizados para mostrar |
| `revisionHistoryLimit` | Número de revisiones de implementación que se deben conservar |

## Tipos de fuentes

ArgoCD admite varios tipos de fuentes para obtener manifiestos de Kubernetes.

### Directorio YAML/JSON sin procesar

El tipo de fuente más simple: un directorio que contiene manifiestos de Kubernetes:

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

### Charts de Helm

#### Desde un repositorio Git

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

#### Desde un repositorio Helm

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

#### Con valores de archivos externos

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

### Artefactos OCI (v2.8+)

Implementa desde registros compatibles con OCI:

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

## Fuentes múltiples

ArgoCD v2.6+ admite múltiples fuentes en una sola aplicación, lo que permite escenarios de implementación complejos.

### Combinación de un chart Helm con valores de Git

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

### Múltiples aplicaciones en una

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

## Configuración de destino

### Uso de URL de servidor

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### Uso de nombre de clúster

```yaml
destination:
  name: production-cluster  # Must match registered cluster name
  namespace: my-app
```

### Creación automática de namespace

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## Evaluación de estado

ArgoCD evalúa el estado de las aplicaciones mediante comprobaciones integradas y personalizadas.

### Comprobaciones de estado integradas

ArgoCD incluye comprobaciones de estado para recursos estándar de Kubernetes:

| Recurso | Estado correcto cuando |
|----------|--------------|
| Deployment | Todas las réplicas están disponibles |
| StatefulSet | Todas las réplicas están listas |
| DaemonSet | El número deseado es igual al programado |
| ReplicaSet | Todas las réplicas están disponibles |
| Service | Existen endpoints |
| Ingress | Se asignó un balanceador de carga |
| PersistentVolumeClaim | Está vinculado |
| Pod | Está en ejecución y listo |
| Job | Se completó correctamente |

### Comprobaciones de estado personalizadas (Lua)

Define comprobaciones de estado personalizadas en `argocd-cm`:

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

### Comprobación de estado para recursos de AWS (ACK)

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

## Hooks de recursos

Los hooks de recursos permiten ejecutar jobs en puntos específicos durante la sincronización.

### Tipos de hook

| Hook | Cuándo se ejecuta |
|------|---------------|
| `PreSync` | Antes de que comience la sincronización |
| `Sync` | Durante la sincronización (después de PreSync) |
| `PostSync` | Después de que la sincronización se complete correctamente |
| `SyncFail` | Después de que falle la sincronización |
| `Skip` | Se omite durante la sincronización |

### Políticas de eliminación de hooks

| Política | Comportamiento |
|--------|----------|
| `HookSucceeded` | Eliminar después de que el hook se complete correctamente |
| `HookFailed` | Eliminar después de que falle el hook |
| `BeforeHookCreation` | Eliminar antes de que se ejecute el nuevo hook |

### Hook de migración de base de datos

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

### Hook de notificación de Slack

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

### Hook de comprobación de estado

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

## Ignorar diferencias

Configura ArgoCD para ignorar diferencias específicas durante la comparación.

### Por puntero JSON

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
      - /spec/replicas
      - /spec/template/spec/containers/0/image
```

### Por expresión de ruta JQ

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jqPathExpressions:
      - .spec.template.spec.containers[].resources
      - .metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]
```

### Por nombre

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-deployment
    namespace: production
    jsonPointers:
      - /spec/replicas
```

### Campos administrados (Kubernetes Server-Side Apply)

```yaml
ignoreDifferences:
  - group: "*"
    kind: "*"
    managedFieldsManagers:
      - kube-controller-manager
      - cluster-autoscaler
```

### Ignorar globalmente en argocd-cm

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

## Patrón App of Apps

El patrón App of Apps permite gestionar múltiples aplicaciones desde una única aplicación principal.

### Estructura de directorios

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

### Aplicación principal

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

### Plantilla de aplicación secundaria

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

### Archivo de valores

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

### Ondas de sincronización para App of Apps

Controla el orden de implementación de las aplicaciones secundarias:

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

## Historial de revisiones y reversión

### Ver historial

```bash
# CLI
argocd app history my-app

# Output
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ghi9012
```

### Reversión

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### Reversión declarativa

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

## Cuestionario

Para poner a prueba lo que has aprendido, prueba el [cuestionario de aplicaciones de ArgoCD](../../quizzes/gitops/argocd/02-applications-quiz.md).
