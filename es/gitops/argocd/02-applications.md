# Aplicaciones de ArgoCD

> **Base de revisión**: Argo CD 3.5.2; actualizado al parche 3.5.4 después de revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: October 12, 2026

## Tabla de contenido
- [Descripción general del CRD Application](#application-crd-overview)
- [Tipos de fuentes](#source-types)
- [Múltiples fuentes](#multiple-sources)
- [Configuración de destino](#destination-configuration)
- [Evaluación de estado](#health-assessment)
- [Hooks de recursos](#resource-hooks)
- [Ignorar diferencias](#ignore-differences)
- [Patrón App of Apps](#app-of-apps-pattern)

## Descripción general del CRD Application

Los ejemplos son configuraciones independientes. Reemplace myorg/accounts/clusters/paths por fuentes autorizadas reales. Elija source/sources, el renderizador y destination.server/name según el escenario, en lugar de habilitar todas las alternativas a la vez.

El CRD Application es el recurso principal de ArgoCD que define cómo y dónde desplegar sus aplicaciones. Conecta un repositorio fuente con un cluster de Kubernetes de destino.

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

Application.status es el estado informado por el controlador. Para crear Applications fuera del namespace del plano de control, un administrador debe habilitar application.namespaces y los sourceNamespaces de AppProject, además del RBAC apropiado.

### Explicación de los campos clave

| Campo | Descripción |
|-------|-------------|
| `project` | AppProject al que pertenece esta aplicación |
| `source` | De dónde obtener los manifiestos |
| `destination` | Cluster y namespace de destino |
| `syncPolicy` | Comportamiento de sincronización automática y reintentos |
| `ignoreDifferences` | Campos que se deben ignorar al comparar |
| `info` | Metadatos personalizados para mostrar |
| `revisionHistoryLimit` | Número de revisiones de despliegue que se conservan |

## Tipos de fuentes

ArgoCD admite varios tipos de fuentes para obtener manifiestos de Kubernetes.

### Directorio YAML/JSON sin procesar

El tipo de fuente más sencillo: un directorio que contiene manifiestos de Kubernetes:

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
          value: ClusterIP
        - name: ingress.enabled
          value: "true"
      skipCrds: false
      passCredentials: false
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

#### Desde un repositorio Helm

Un chart podinfo pequeño y fijado ilustra el formato de la fuente. El replicaCount final es 3 porque parameters reemplaza a valuesObject. valuesObject proporciona valores estructurados en línea; no lee automáticamente variables de entorno.

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

La precedencia es parameters → valuesObject → values → valueFiles → valores predeterminados del chart. Prefiera una sola representación en línea; cuando existe valuesObject, proporciona los valores en línea. Habilite passCredentials solo cuando sea necesario, ya que puede reenviar credenciales a otros dominios. Esta base usa Helm 4 integrado; no seleccione v2/v3 arbitrariamente.

#### Con valores de archivos externos

Una referencia $values requiere una fuente ref coincidente en spec.sources. El repositorio/archivo de valores debe existir y estar autorizado.

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

### Artefactos OCI

Las fuentes OCI generales usan una URI oci:// y una ruta dentro del artefacto expandido. Reemplace esta cuenta/repositorio/tag por un artefacto publicado. Una imagen de contenedor normal no es automáticamente una fuente de manifiestos.

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

Argo CD 3.5.4 requiere una capa con un tipo de medio compatible: de forma predeterminada, application/vnd.oci.image.layer.v1.tar+gzip o contenido tar+gzip de chart Helm. Valide otros tipos con ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES y la estructura del artefacto. Los manifiestos OCI de más de 4 MiB se rechazan a partir de 3.5.4 (GHSA-w996-f2wq-x9c6).

La forma Helm OCI usa un campo chart y una URL de repositorio **sin oci://**. Este es un fragmento de fuente bajo Application.spec.

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

Haga coincidir las credenciales con el tipo de fuente: OCI general usa type: oci y una URL oci://; Helm OCI usa type: helm, enableOCI: "true" y una URL sin esquema. ECR necesita permisos de registro y la renovación/aplicación de su token de 12 horas; otorgar permisos de IRSA no actualiza un Secret por sí solo.

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

## Múltiples fuentes

Cuando sources está presente, se ignora el source en singular. Combine la configuración de una aplicación relacionada, como un chart más un repositorio de valores; use ApplicationSet/App of Apps para stacks de plataforma administrados de forma independiente.

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

ref: values asigna $values a la raíz de ese repositorio Git. Sin path proporciona solo valores; con path también genera manifiestos allí. Una fuente ref no puede especificar también chart. Los recursos duplicados de group/kind/name/namespace usan la última fuente y generan RepeatedResourceWarning; esto no es una combinación automática campo por campo.

## Configuración de destino

Elija server o name para el destino registrado. destination.namespace proporciona el valor predeterminado para recursos con namespace que carecen de su propio namespace; CreateNamespace crea solo ese destino, no cada namespace incorporado explícitamente en un chart. Use managedNamespaceMetadata con la creación de namespace y revise la propiedad antes de actualizar un namespace existente.

### Uso de la URL del servidor

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### Uso del nombre del cluster

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

Synced describe los campos deseados/en ejecución comparados, no prueba que el Service procese solicitudes. Healthy sigue las comprobaciones configuradas por recurso. Los recursos personalizados sin una comprobación pueden omitirse del estado de la aplicación y necesitan una definición apropiada.

### Comprobaciones de estado integradas

Estas resumen comprobaciones de implementación importantes de 3.5.4, no predicados completos basados en un único contador de réplicas.

| Recurso | Comprobaciones importantes |
|---|---|
| Deployment | Generación observada, progreso/error del rollout, réplicas actualizadas/disponibles |
| StatefulSet | Generación, estrategia/partición de actualización, revisiones y estado de réplicas |
| DaemonSet | Generación y recuentos de Pod deseados/actualizados/disponibles |
| Pod | Fase, preparación y terminación/error del contenedor |
| Service | LoadBalancer espera una dirección; otros tipos no validan endpoints |
| Ingress | Estado de dirección de loadBalancer informado por el controlador |
| PVC | Estado Bound |
| Job | Incompleto Progressing, fallido Degraded, completado Healthy, suspendido Suspended |

### Comprobaciones de estado personalizadas

No reemplace las comprobaciones integradas de Rollout/cert-manager Certificate con una comparación simplista de fase. El grupo Certificate es cert-manager.io; su comprobación integrada gestiona Issuing antes de Ready. El ejemplo de ACK a continuación devuelve Progressing cuando falta status/conditions y no equipara la existencia de ARN con Healthy. Valide las condiciones Ready/ACK.ResourceSynced y de error que proporciona su versión de ACK. El ejemplo prefiere Ready cuando está presente y, de lo contrario, recurre a ACK.ResourceSynced.

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

Esto interpreta el estado informado por el controlador; no consulta AWS directamente. Fusione la clave en el argocd-cm existente y pruebe estados de CR reales faltantes/en espera/listos/con error/con nuevas especificaciones. Argo CD administrado por EKS proporciona comprobaciones de ACK/kro, así que inspeccione primero sus comprobaciones existentes y la configuración compatible.

## Hooks de recursos

PostSync espera recursos Sync exitosos y Healthy relevantes. La sincronización explícita selectiva por recurso no ejecuta hooks. En 3.5.4, ApplyOutOfSyncOnly sigue ejecutando hooks y registra el historial. SyncFail gestiona fallos de sincronización elegibles; no dependa de él como ruta garantizada de limpieza/copia de seguridad para cada error, incluidos los fallos de generación de manifiestos.

Los hooks de recursos permiten ejecutar jobs en puntos específicos durante la sincronización.

### Tipos de hooks

| Hook | Cuándo se ejecuta |
|------|---------------|
| `PreSync` | Antes de que comience la sincronización |
| `Sync` | Durante la sincronización (después de PreSync) |
| `PostSync` | Después de que Sync tenga éxito y los recursos estén Healthy |
| `SyncFail` | Después de que falle la sincronización |
| `Skip` | Se omite la aplicación del manifiesto |
| `PreDelete` | Antes de que se eliminen los recursos con la Application |
| `PostDelete` | Después de que se eliminen los recursos de la Application |

### Políticas de eliminación de hooks

| Política | Comportamiento |
|--------|----------|
| `HookSucceeded` | Eliminar después de que el hook tenga éxito |
| `HookFailed` | Eliminar después de que el hook falle |
| `BeforeHookCreation` | Eliminar antes de que se ejecute el nuevo hook |

### Hook de migración de base de datos

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

### Hook de notificación de Slack

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

Los Jobs con nombre fijo necesitan reglas de ciclo de vida como BeforeHookCreation para ejecuciones repetidas. Conserve los logs de fallos externamente antes de la limpieza; la limpieza HookSucceeded sigue la semántica de fase/resultado de sincronización de Argo. Prepare la imagen de migración, el Secret de base de datos y el ServiceAccount, y valide por separado la idempotencia, el bloqueo y la compatibilidad de rollback. El fallo de un hook no revierte automáticamente una base de datos ni un Deployment existente. PreDelete/PostDelete se aplican a la eliminación de Application, no al pruning de sincronización habitual.

## Ignorar diferencias

Excluya solo campos específicos que pertenezcan a otro controlador conocido. Este fragmento Application.spec ignora las réplicas administradas por HPA en my-deployment en production.

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

ignoreDifferences normalmente afecta a la comparación. RespectIgnoreDifferences=true lo extiende a la sincronización, pero la creación inicial sin un recurso en ejecución sigue aplicando el manifiesto deseado. Las reglas amplias de imagen, secret, recursos completos o todos los gestores pueden ocultar una desviación importante.

Para los arrays de webhook, seleccione por nombre en lugar de índices fijos y delimite también el nombre del recurso. Use esto solo cuando se conozcan el controlador de inyección de CA y la identidad del webhook.

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

La configuración global resource.customizations.ignoreDifferences afecta a cada Application. Prefiera reglas con ámbito de aplicación; elija managedFieldsManagers solo después de inspeccionar qué campos posee realmente ese gestor.

## Patrón App of Apps

App of Apps es un patrón de arranque administrativo. Quienes escriben en la fuente padre pueden afectar Applications/AppProjects poderosos en el namespace de administración; restrinja los privilegios de escritura/revisión/destino. Los finalizers y el pruning de padre/hijo pueden encadenar eliminaciones. Crear Applications hijas en orden no garantiza por sí solo la preparación de las cargas de trabajo hijas; valide la propagación del estado de Application, la política de sincronización y el comportamiento de waves.

El patrón App of Apps permite administrar varias aplicaciones desde una única aplicación padre.

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

### Application padre

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

### Plantilla de Application hija

Esta hija de monitoring fija kube-prometheus-stack 90.0.0. Revise los requisitos de actualización/CRD de ese chart y aprovisione por separado la capacidad de monitoring. Cree previamente un Secret grafana-admin protegido en el namespace monitoring con claves admin-user/admin-password; no coloque credenciales de administrador en los valores Git padre.

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

### Waves de sincronización para App of Apps

Los siguientes son fragmentos solo de metadatos; combínelos con especificaciones hijas completas. Ordenar la creación de Applications hijas no garantiza que las cargas de trabajo hijas estén listas: configure/verifique la propagación de estado y la política de sincronización de Application.

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

## Historial de revisiones y rollback

El rollback del historial no se puede usar mientras la sincronización automatizada esté habilitada. Revise primero la política en su propietario real Git/ApplicationSet. El rollback no actualiza Git, por lo que una reconciliación posterior puede restaurar el estado de Git. Conserve los cambios previstos mediante un revert/cambio de revisión de Git aprobado; la recuperación de la base de datos/estado externo es independiente.

### Ver historial

```bash
# CLI
argocd app history my-app

```

Salida de ejemplo (no son comandos de shell):

```text
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ab89012
```

### Rollback

Elija un ID del historial real. Aplicar una revisión de manifiesto anterior y hacer pruning de recursos adicionales son decisiones independientes.

```bash
# Rollback to specific revision
argocd app rollback my-app 1

# Or sync to specific Git revision
argocd app sync my-app --revision abc1234
```

### Rollback declarativo

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

## Cuestionario

Para comprobar lo que ha aprendido, pruebe el [cuestionario de aplicaciones de ArgoCD](../../quizzes/gitops/argocd/02-applications-quiz.md).

## Fuentes de revisión versionadas

- [Fuentes y Helm 3.5.4](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/helm.md)
- [Múltiples fuentes](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/multiple_sources.md)
- [Reglas de fuente OCI](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/oci.md)
- [Opciones de sincronización](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [Fases, waves y hooks](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [Implementación de estado de Service](https://github.com/argoproj/argo-cd/blob/v3.5.4/gitops-engine/pkg/health/health_service.go)
- [Definiciones de condiciones de ACK](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
