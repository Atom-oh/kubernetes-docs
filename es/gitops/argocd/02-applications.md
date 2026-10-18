# Aplicaciones de ArgoCD

> **Referencia de revisión**: Argo CD 3.5.2; actualizado al parche 3.5.4 tras revisar las notas de la versión (no se volvieron a ejecutar los ejemplos)
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenido
- [Descripción general del CRD Application](#application-crd-overview)
- [Tipos de fuentes](#source-types)
- [Varias fuentes](#multiple-sources)
- [Configuración del destino](#destination-configuration)
- [Evaluación del estado](#health-assessment)
- [Hooks de recursos](#resource-hooks)
- [Ignorar diferencias](#ignore-differences)
- [Patrón App of Apps](#app-of-apps-pattern)

## Descripción general del CRD Application {#application-crd-overview}

Los ejemplos son configuraciones independientes. Sustituye myorg/accounts/clusters/paths por fuentes autorizadas reales. Elige la fuente o las fuentes, el renderizador y destination.server/name según el escenario, en lugar de habilitar todas las alternativas a la vez.

El CRD Application es el recurso principal de ArgoCD que define cómo y dónde implementar tus aplicaciones. Conecta un repositorio de origen con un clúster de Kubernetes de destino.

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

Application.status es el estado informado por el controlador. Para crear Applications fuera del espacio de nombres del plano de control, un administrador debe habilitar application.namespaces y AppProject sourceNamespaces, además de configurar el RBAC correspondiente.

### Explicación de los campos clave

| Campo | Descripción |
|-------|-------------|
| `project` | AppProject al que pertenece esta aplicación |
| `source` | De dónde obtener los manifiestos |
| `destination` | Clúster y espacio de nombres de destino |
| `syncPolicy` | Comportamiento de sincronización automática y reintentos |
| `ignoreDifferences` | Campos que se deben ignorar al comparar |
| `info` | Metadatos personalizados para mostrar |
| `revisionHistoryLimit` | Número de revisiones de implementación que se conservarán |

## Tipos de fuentes {#source-types}

ArgoCD admite varios tipos de fuentes para obtener manifiestos de Kubernetes.

### Directorio de YAML/JSON sin formato

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

#### Desde un repositorio de Git

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

#### Desde un repositorio de Helm

Un chart podinfo pequeño y fijado ilustra el formato de la fuente. El replicaCount final es 3 porque los parámetros prevalecen sobre valuesObject. valuesObject proporciona valores en línea estructurados; no lee automáticamente variables de entorno.

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

El orden de precedencia es parameters → valuesObject → values → valueFiles → valores predeterminados del chart. Es preferible usar una sola representación en línea; si existe valuesObject, este proporciona los valores en línea. Habilita passCredentials solo cuando sea necesario, ya que puede reenviar credenciales a otros dominios. Esta referencia usa Helm 4 incluido; no selecciones v2/v3 arbitrariamente.

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

Las fuentes OCI generales usan un URI oci:// y una ruta dentro del artefacto expandido. Sustituye esta cuenta/repositorio/etiqueta por un artefacto publicado. Una imagen de contenedor normal no se convierte automáticamente en una fuente de manifiestos.

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

Argo CD 3.5.4 requiere una capa con un tipo de medio admitido: de forma predeterminada, application/vnd.oci.image.layer.v1.tar+gzip o contenido tar+gzip de un chart de Helm. Valida otros tipos con ARGOCD_REPO_SERVER_OCI_LAYER_MEDIA_TYPES y la estructura del artefacto. A partir de la versión 3.5.4, se rechazan los manifiestos OCI de más de 4 MiB (GHSA-w996-f2wq-x9c6).

El formato OCI de Helm usa un campo chart y una URL de repositorio **sin oci://**. Este es un fragmento de fuente dentro de Application.spec.

```yaml
source:
  repoURL: ghcr.io/stefanprodan/charts
  chart: podinfo
  targetRevision: 6.15.0
  helm:
    valuesObject:
      replicaCount: 2
```

Haz coincidir las credenciales con el tipo de fuente: OCI general usa type: oci y una URL oci://; OCI de Helm usa type: helm, enableOCI: "true" y una URL sin esquema. ECR requiere permisos para el registro, además de renovar y aplicar su token de 12 horas; conceder permisos de IRSA no actualiza un Secret por sí solo.

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

## Varias fuentes {#multiple-sources}

Cuando se especifica sources, se ignora source. Combina configuraciones de una aplicación relacionada, como un chart más un repositorio de valores; usa ApplicationSet/App of Apps para pilas de plataforma administradas de forma independiente.

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

ref: values asigna $values a la raíz de ese repositorio de Git. Sin path, solo proporciona valores; con path, también genera manifiestos en esa ubicación. Una fuente ref no puede especificar chart a la vez. Los recursos duplicados con la misma combinación de group/kind/name/namespace usan la última fuente y generan RepeatedResourceWarning; esto no realiza una combinación automática campo por campo.

## Configuración del destino {#destination-configuration}

Elige server o name para el destino registrado. destination.namespace proporciona el valor predeterminado para los recursos con espacio de nombres que no tengan uno propio; CreateNamespace crea solo ese destino, no todos los espacios de nombres incluidos explícitamente en un chart. Usa managedNamespaceMetadata junto con la creación del espacio de nombres y revisa la propiedad antes de actualizar uno existente.

### Uso de una URL de servidor

```yaml
destination:
  server: https://kubernetes.default.svc  # In-cluster
  namespace: my-app
```

### Uso del nombre del clúster

```yaml
destination:
  name: production-cluster  # Must match registered cluster name
  namespace: my-app
```

### Creación automática del espacio de nombres

```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
```

## Evaluación del estado {#health-assessment}

Synced describe los campos deseados/activos que se compararon; no demuestra que el servicio gestione solicitudes. Healthy depende de las comprobaciones configuradas para cada recurso. Los recursos personalizados sin una comprobación pueden omitirse del estado de la aplicación y necesitar una definición adecuada.

### Comprobaciones de estado integradas

Estas resumen comprobaciones importantes de la implementación de 3.5.4; no son predicados completos basados en un único contador de réplicas.

| Recurso | Comprobaciones importantes |
|---|---|
| Deployment | Generación observada, progreso/fallo del despliegue, réplicas actualizadas/disponibles |
| StatefulSet | Generación, estrategia/partición de actualización, revisiones y estado de las réplicas |
| DaemonSet | Generación y recuento de Pods deseados/actualizados/disponibles |
| Pod | Fase, preparación y terminación/fallo de los contenedores |
| Service | LoadBalancer espera una dirección; los demás tipos no validan los endpoints |
| Ingress | Estado de la dirección loadBalancer informado por el controlador |
| PVC | Estado enlazado |
| Job | Incompleto: Progressing; fallido: Degraded; completado: Healthy; suspendido: Suspended |

### Comprobaciones de estado personalizadas

No sustituyas las comprobaciones integradas de Rollout/cert-manager Certificate por una comparación simplista de fases. El grupo de Certificate es cert-manager.io; su comprobación integrada gestiona Issuing antes de Ready. El ejemplo de ACK que aparece a continuación devuelve Progressing si faltan status/conditions y no considera que la existencia de un ARN equivalga a Healthy. Valida las condiciones Ready/ACK.ResourceSynced y de error que proporcione tu versión de ACK. El ejemplo da prioridad a Ready cuando está presente y, de lo contrario, recurre a ACK.ResourceSynced.

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

Esto interpreta el estado informado por el controlador; no consulta AWS directamente. Combina la clave con el argocd-cm existente y prueba los estados faltante/en espera/listo/error/especificación nueva con CR reales. Argo CD administrado por EKS proporciona comprobaciones de ACK/kro, así que primero inspecciona las comprobaciones existentes y la configuración admitida.

## Hooks de recursos {#resource-hooks}

PostSync espera a que la sincronización finalice correctamente y a que los recursos pertinentes estén Healthy. La sincronización selectiva explícita de recursos no ejecuta hooks. En 3.5.4, ApplyOutOfSyncOnly sigue ejecutando hooks y registrando el historial. SyncFail gestiona los fallos de sincronización que correspondan; no confíes en él como una ruta garantizada de limpieza/copia de seguridad para todos los errores, incluidos los fallos de generación de manifiestos.

Los hooks de recursos permiten ejecutar Jobs en momentos específicos durante la sincronización.

### Tipos de hooks

| Hook | Cuándo se ejecuta |
|---|---------------|
| `PreSync` | Antes de que comience la sincronización |
| `Sync` | Durante la sincronización (después de PreSync) |
| `PostSync` | Después de que Sync finalice correctamente y los recursos estén Healthy |
| `SyncFail` | Después de que falle la sincronización |
| `Skip` | Se omite la aplicación del manifiesto |
| `PreDelete` | Antes de eliminar los recursos junto con la Application |
| `PostDelete` | Después de eliminar los recursos de la Application |

### Políticas de eliminación de hooks

| Política | Comportamiento |
|--------|----------|
| `HookSucceeded` | Eliminar después de que el hook finalice correctamente |
| `HookFailed` | Eliminar después de que falle el hook |
| `BeforeHookCreation` | Eliminar antes de ejecutar el nuevo hook |

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
          image: curlimages/curl:8.23.0
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
          image: curlimages/curl:8.23.0
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

Los Jobs con nombres fijos necesitan reglas de ciclo de vida, como BeforeHookCreation, para ejecutarse repetidamente. Guarda los registros de los fallos fuera del clúster antes de la limpieza; la limpieza HookSucceeded sigue la semántica de fase/resultado de sincronización de Argo. Prepara la imagen de migración, el Secret de la base de datos y la ServiceAccount; valida por separado la idempotencia, el bloqueo y la compatibilidad con la reversión. El fallo de un hook no revierte automáticamente una base de datos ni un Deployment existente. PreDelete/PostDelete se aplican a la eliminación de una Application, no a la poda habitual de la sincronización.

## Ignorar diferencias {#ignore-differences}

Excluye solo campos específicos que pertenezcan a otro controlador conocido. Este fragmento de Application.spec ignora las réplicas administradas por HPA en my-deployment en producción.

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

ignoreDifferences normalmente afecta a la comparación. RespectIgnoreDifferences=true también lo aplica a la sincronización, pero la creación inicial sin un recurso activo sigue aplicando el manifiesto deseado. Las reglas generales para imágenes, secretos, recursos completos o todos los managers pueden ocultar divergencias importantes.

Para arrays de webhooks, selecciona por nombre en lugar de usar índices fijos y limita también el ámbito al nombre del recurso. Úsalo solo cuando se conozcan el controlador de inyección de CA y la identidad del webhook.

```yaml
spec:
  ignoreDifferences:
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    name: my-webhook
    jqPathExpressions:
    - '.webhooks[]? | select(.name == "admission.example.com") | .clientConfig.caBundle'
```

La configuración global resource.customizations.ignoreDifferences afecta a todas las Applications. Es preferible usar reglas específicas de la aplicación; elige managedFieldsManagers solo después de inspeccionar qué campos administra realmente ese manager.

## Patrón App of Apps {#app-of-apps-pattern}

App of Apps es un patrón administrativo de arranque. Quienes escriben en la fuente principal pueden afectar a Applications/AppProjects con privilegios en el espacio de nombres de administración; restringe los permisos de escritura/revisión/destino. Los finalizers de la aplicación principal/secundaria y la poda pueden desencadenar eliminaciones en cascada. Crear Applications secundarias en orden no garantiza por sí solo que las cargas de trabajo secundarias estén listas; valida la propagación del estado de Application, la política de sincronización y el comportamiento de las waves.

El patrón App of Apps permite administrar varias aplicaciones desde una única aplicación principal.

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

### Application principal

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

### Plantilla de Application secundaria

Esta Application secundaria de monitorización fija kube-prometheus-stack en la versión 90.0.0. Revisa los requisitos de actualización/CRD de ese chart y aprovisiona la capacidad de monitorización por separado. Crea previamente un Secret protegido grafana-admin en el espacio de nombres monitoring, con las claves admin-user/admin-password; no incluyas credenciales de administrador en los valores de Git de la aplicación principal.

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

### Sync Waves para App of Apps

A continuación se muestran fragmentos que solo contienen metadatos; combínalos con las especificaciones completas de las Applications secundarias. Ordenar la creación de las Applications secundarias no garantiza que sus cargas de trabajo estén listas: configura y verifica la propagación del estado de Application secundaria y la política de sincronización.

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

## Historial de revisiones y reversión

No se puede usar la reversión del historial mientras la sincronización automática esté habilitada. Revisa primero la política en el propietario real de Git/ApplicationSet. La reversión no actualiza Git, por lo que una conciliación posterior puede restaurar el estado de Git. Conserva los cambios previstos mediante una reversión de Git o un cambio de revisión aprobados; la recuperación de la base de datos/estado externo es independiente.

### Ver el historial

```bash
# CLI
argocd app history my-app

```

Ejemplo de salida (no son comandos de shell):

```text
ID  DATE                           REVISION
0   2024-01-15 10:30:00 +0000 UTC  abc1234
1   2024-01-16 14:45:00 +0000 UTC  def5678
2   2024-01-17 09:15:00 +0000 UTC  ab89012
```

### Revertir

Elige un ID del historial real. Aplicar una revisión anterior de los manifiestos y podar los recursos adicionales son decisiones independientes.

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

Para comprobar lo que has aprendido, prueba el [cuestionario sobre aplicaciones de ArgoCD](../../quizzes/gitops/argocd/02-applications-quiz.md).

## Fuentes de revisión por versión

- [Fuentes 3.5.4 y Helm](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/helm.md)
- [Varias fuentes](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/multiple_sources.md)
- [Reglas de fuentes OCI](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/oci.md)
- [Opciones de sincronización](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-options.md)
- [Fases, waves y hooks](https://github.com/argoproj/argo-cd/blob/v3.5.4/docs/user-guide/sync-waves.md)
- [Implementación del estado de Service](https://github.com/argoproj/argo-cd/blob/v3.5.4/gitops-engine/pkg/health/health_service.go)
- [Definiciones de condiciones de ACK](https://github.com/aws-controllers-k8s/runtime/blob/main/apis/core/v1alpha1/conditions.go)
