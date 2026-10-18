# Prácticas recomendadas de Argo CD

> **Base de revisión**: Argo CD 3.5.2 / Helm Chart 10.8.4 / Kustomize 5.8.1; ejemplos de manifiestos actualizados al parche 3.5.5 (aún incluye Kustomize 5.8.1) después de revisar las notas de la versión (los ejemplos no se volvieron a ejecutar)
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenidos

- [Estructura del repositorio](#repository-structure)
- [Promoción de entornos](#environment-promotion)
- [Gestión de recursos](#resource-management)
- [Ajuste del rendimiento](#performance-tuning)
- [Recuperación ante desastres](#disaster-recovery)
- [Estrategias de actualización](#upgrade-strategies)
- [Resolución de problemas](#troubleshooting)
- [Prácticas recomendadas de EKS](#eks-best-practices)
- [Lista de verificación de producción](#production-checklist)

## Estructura del repositorio {#repository-structure}

### Patrón monorepo

Un único repositorio para todas las aplicaciones y entornos:

```
gitops-repo/
├── apps/
│   ├── app-a/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       ├── dev/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       ├── staging/
│   │       │   ├── kustomization.yaml
│   │       │   └── patch.yaml
│   │       └── production/
│   │           ├── kustomization.yaml
│   │           └── patch.yaml
│   └── app-b/
│       └── ...
├── platform/
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
└── clusters/
    ├── dev/
    ├── staging/
    └── production/
```

**Ventajas:**
- Fuente única de verdad
- Cambios sencillos entre aplicaciones
- CI/CD simplificado
- Un commit atómico de Git puede describir varias aplicaciones; sus implementaciones en el clúster no son una única transacción atómica

**Desventajas:**
- Puede volverse grande
- Complejidad en el control de acceso
- Punto único de fallo

![Diagrama que compara un monorepo, donde un repositorio Git contiene los directorios app-a, app-b e infra, con un polyrepo, donde los mismos componentes se dividen en tres repositorios Git independientes: app-a-repo, app-b-repo e infra-repo.](../../.gitbook/assets/en-gitops-argocd-09-best-practices-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-09-best-practices-0.html)

### Patrón polyrepo

Repositorios separados por aplicación o equipo:

```
Organization:
├── gitops-platform/          # Platform team
│   ├── argocd/
│   ├── monitoring/
│   └── ingress/
├── gitops-team-a/            # Team A applications
│   ├── app-a/
│   └── app-b/
├── gitops-team-b/            # Team B applications
│   ├── app-c/
│   └── app-d/
└── gitops-infra/             # Infrastructure
    ├── terraform/
    └── clusters/
```

**Ventajas:**
- Propiedad clara
- Implementaciones independientes
- Control de acceso detallado
- Repositorios más pequeños

**Desventajas:**
- Es más difícil coordinar cambios
- Más repositorios que gestionar
- Posibilidad de desviaciones

### Estructura de repositorio App of Apps

```
gitops-root/
├── argocd-apps/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-staging.yaml
│   ├── values-production.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml
│       ├── project.yaml
│       ├── app-a.yaml
│       ├── app-b.yaml
│       └── platform-apps.yaml
└── bootstrap/
    └── root-app.yaml
```

### Convenciones de nomenclatura recomendadas

| Tipo | Patrón | Ejemplo |
|------|---------|---------|
| Aplicación | `{app}-{env}` | `frontend-production` |
| Proyecto | `{team}` o `{env}` | `platform`, `production` |
| Namespace | `{app}` o `{app}-{env}` | `frontend`, `frontend-prod` |
| Repositorio | `gitops-{scope}` | `gitops-platform` |

## Promoción de entornos {#environment-promotion}

### Estrategia de ramas de Git

Las ramas de entorno de larga duración son una opción; los overlays basados en directorios en una rama main compartida suelen reducir la divergencia entre ramas. App of Apps es una capacidad administrativa: restrinja el acceso al repositorio raíz y la creación de Application secundarias. Una sincronización manual de producción es una barrera independiente de un cambio de Git revisado.

### Promoción basada en directorios

Promueva el mismo artefacto probado sin reconstruirlo por entorno. Estos ejemplos suponen bases existentes y etiquetas inmutables exigidas por el registro; prefiera digests cuando no se garantiza la inmutabilidad de las etiquetas. Cambiar el contenido de una etiqueta mutable no actualiza por sí mismo Git ni una plantilla de Pod de Deployment. El nombre de la imagen base es `my-app`; aplique conjuntamente las transformaciones de nombre/etiqueta en el overlay. Un overlay que coincida con un nombre antiguo no actualizará una imagen ya renombrada por la base.

```yaml
# overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3

---
# overlays/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3

---
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: my-app
    newName: my-registry/my-app
    newTag: v1.2.3
```

### Pipeline de promoción automatizada

Este flujo de trabajo abre una PR para un **digest ya probado**. Adapte el registro de ejemplo y la ruta del overlay. Proporcione `GITOPS_PR_TOKEN` mediante un token de GitHub App o un token con alcance limitado y acceso de escritura a contents/pull requests para el repositorio de destino. Los cambios realizados con el GITHUB_TOKEN predeterminado tienen restricciones para activar flujos de trabajo posteriores; verifique que puedan ejecutarse las comprobaciones necesarias. Exija revisión, pruebas y políticas de artefactos mediante rulesets del repositorio/protección de ramas.

```yaml
name: Promote tested image to production
on:
  workflow_dispatch:
    inputs:
      digest:
        description: 'Tested image digest (sha256: followed by 64 hex characters)'
        required: true
        type: string
permissions:
  contents: read
concurrency:
  group: promote-production
  cancel-in-progress: false
jobs:
  promote:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Install verified Kustomize
        shell: bash
        run: |
          set -euo pipefail
          tool_dir="$RUNNER_TEMP/kustomize-bin"
          mkdir -p "$tool_dir"
          cd "$tool_dir"
          curl -fsSL -o kustomize.tar.gz \
            https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v5.8.1/kustomize_v5.8.1_linux_amd64.tar.gz
          echo "029a7f0f4e1932c52a0476cf02a0fd855c0bb85694b82c338fc648dcb53a819d  kustomize.tar.gz" | sha256sum -c -
          tar -xzf kustomize.tar.gz kustomize
          echo "$tool_dir" >> "$GITHUB_PATH"
      - name: Update production overlay
        env:
          IMAGE_DIGEST: ${{ inputs.digest }}
        shell: bash
        run: |
          set -euo pipefail
          [[ "$IMAGE_DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]] || exit 1
          cd overlays/production
          kustomize edit set image "my-app=my-registry/my-app@${IMAGE_DIGEST}"
          kustomize build . > /dev/null
      - name: Create reviewed promotion PR
        uses: peter-evans/create-pull-request@5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          token: ${{ secrets.GITOPS_PR_TOKEN }}
          branch: promote-production
          title: 'Promote tested image to production'
          commit-message: 'chore: promote tested image digest'
          add-paths: overlays/production/kustomization.yaml
          body: |
            Promote the already tested image digest: ${{ inputs.digest }}
            Require the repository's validation and approval checks before merging.
```

## Gestión de recursos {#resource-management}

### Recursos de componentes

Estos valores de Chart 10.8.4 son **puntos de partida para la medición**, no una tabla de dimensionamiento garantizada. Incorpórelos a sus valores existentes y mantenga un único propietario de la implementación. El chart proporciona los nombres de contenedor y tipos de carga de trabajo correctos; evite parches incompletos de Deployment que añadan accidentalmente un contenedor.

```yaml
fullnameOverride: argocd
controller:
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: '2'
      memory: 4Gi
server:
  replicas: 2
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
repoServer:
  replicas: 2
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: '1'
      memory: 2Gi
```

| Medición | Dirección de ajuste |
|---|---|
| Tiempo de manifiesto, solicitudes simultáneas, tamaño del repositorio | CPU/memoria de repo-server, paralelismo, disco |
| Recuentos de recursos por clúster y memoria de watch/cache | Memoria del Controller y distribución de clústeres |
| Retraso de la cola de reconciliación/sincronización y limitación de API | Concurrencia del procesador junto con la capacidad de API objetivo |
| Limitación de CPU, OOM y reinicios | Requests/limits junto con la ejecución simultánea |

El número de aplicaciones por sí solo no establece un umbral de fragmentación de 100/500 aplicaciones. Redis es una caché reconstruible, pero la pérdida de caché puede causar carga de recálculo y latencia. Aplique los requisitos previos de nodo/anti-affinity/PDB de la [sección de instalación HA](01-installation.md#high-availability-setup). No replique ciegamente todos los componentes.

### HPA opcional de repo-server

Esto requiere Metrics Server y requests de CPU. Con HPA habilitado, este controla el número de réplicas. El escalado de CPU no explica todos los cuellos de botella de generación de manifiestos; escalar únicamente según la memoria de caché persistente puede mantener réplicas innecesarias en ejecución.

```yaml
repoServer:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: null
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
```

## Ajuste del rendimiento {#performance-tuning}

### Ubicación y significado de la configuración

Combine estos valores de Helm. `configs.params` genera `argocd-cmd-params-cm`; `configs.cm` genera `argocd-cm`. Los valores consumidos mediante configuraciones de línea de comandos/entorno requieren el rollout del controller/repo-server/server afectado; verifique el Pod renderizado y los logs de inicio.

```yaml
configs:
  params:
    controller.status.processors: '20'
    controller.operation.processors: '10'
    controller.repo.server.timeout.seconds: '180'
    server.repo.server.timeout.seconds: '180'
    reposerver.parallelism.limit: '2'
    reposerver.repo.cache.expiration: 24h
    reposerver.git.request.timeout: 30s
    reposerver.git.lsremote.parallelism.limit: '5'
  cm:
    timeout.reconciliation: 300s
    timeout.reconciliation.jitter: 60s
    application.resourceTrackingMethod: annotation
repoServer:
  env:
  - name: ARGOCD_EXEC_TIMEOUT
    value: 2m
```

- Los procesadores de estado/operación controlan la concurrencia, no la frecuencia de sondeo; 20/10 son los valores de concurrencia predeterminados.
- El tiempo de espera RPC de repo-server de 180 segundos, el tiempo de ejecución de herramientas de dos minutos y el tiempo de espera de solicitudes Git de treinta segundos son límites distintos. Identifique la etapa lenta y el comportamiento de cancelación antes de aumentarlos.
- `reposerver.parallelism.limit` limita la generación simultánea de manifiestos, no el TTL de la caché. Sométalo a pruebas de carga con respecto a los límites de memoria/procesos.
- La reconciliación periódica predeterminada es de 120 segundos más hasta 60 segundos de jitter. El ejemplo usa 300 + 60 segundos (cinco a seis minutos); los webhooks y otras causas de actualización son independientes.
- `application.resourceTrackingMethod` establece el seguimiento de recursos, no la frecuencia de actualización. Revise los efectos de migración antes de cambiar un método de seguimiento existente.

### Fragmentación de varios clústeres de destino

La unidad de fragmentación predeterminada es el **clúster** de destino. Aumentar las réplicas no distribuye uniformemente todas las Applications que tienen como destino un clúster. El chart coordina las réplicas de StatefulSet con `ARGOCD_CONTROLLER_REPLICAS`. La distribución dinámica de clústeres y round-robin/consistent-hashing son experimentales en esta versión; no las presente como valores predeterminados universales para producción.

```yaml
controller:
  replicas: 3
configs:
  params:
    controller.sharding.algorithm: legacy
```

### Límites de Application y HPA

Divida las Applications grandes según los límites de propiedad y ciclo de vida. Las divisiones arbitrarias por tipo de recurso complican las dependencias y el orden de eliminación de Secret/Service/Deployment. Las Applications secundarias en App of Apps no constituyen una única implementación atómica.

Este ejemplo supone un proyecto `workloads` existente, un namespace de destino y un HPA que controla el Deployment `my-app`. Prefiera omitir las réplicas de Git; cuando sea necesario, limite las exclusiones de diff/apply a ese recurso. Haga coincidir `ignoreDifferences.name` con el nombre final después de cualquier prefijo/sufijo de Kustomize. `ApplyOutOfSyncOnly` optimiza los destinos de aplicación; no cambia la frecuencia de sincronización.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: large-app
  namespace: argocd
spec:
  project: workloads
  source:
    repoURL: https://github.com/myorg/gitops.git
    targetRevision: main
    path: overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-production
  syncPolicy:
    automated:
      enabled: true
      prune: true
      selfHeal: true
    syncOptions:
    - ApplyOutOfSyncOnly=true
    - RespectIgnoreDifferences=true
  ignoreDifferences:
  - group: apps
    kind: Deployment
    name: my-app
    namespace: my-app-production
    jsonPointers:
    - /spec/replicas
```

## Recuperación ante desastres {#disaster-recovery}

### Alcance de la copia de seguridad

`argocd admin export` exporta Applications/AppProjects/ApplicationSets, cuatro ConfigMaps principales y Secrets seleccionados de Argo CD. **No es una copia de seguridad completa del namespace**. No suponga que se incluyen cmd-params, la configuración Notifications/CMP y los Secrets de TLS/notificaciones gestionados por separado. Compruebe también los namespaces adicionales configurados para Application/ApplicationSet.

Use la versión de CLI correspondiente, un kubecontext verificado, la herramienta `age` y un destinatario público aprobado. Guarde las identidades privadas por separado y pruebe el descifrado/la recuperación. La instantánea complementaria cifra todos los ConfigMaps/Secrets del namespace, incluidos potencialmente los Secrets de release de Helm. Seleccione los objetos necesarios durante la recuperación; no aplique a ciegas toda la instantánea complementaria.

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${ARGO_BACKUP_RECIPIENT:?Set the approved age public recipient}"
ARGO_BACKUP_DIR="./argocd-backup-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$ARGO_BACKUP_DIR"
kubectl config current-context
kubectl get configmap argocd-cm -n argocd -o name

argocd admin export -n argocd |
  age --recipient "$ARGO_BACKUP_RECIPIENT" --output "$ARGO_BACKUP_DIR/data.yaml.age.tmp"
mv "$ARGO_BACKUP_DIR/data.yaml.age.tmp" "$ARGO_BACKUP_DIR/data.yaml.age"

# Supplement: all namespace ConfigMaps/Secrets, including custom configuration.
kubectl get configmaps,secrets -n argocd -o yaml |
  age --recipient "$ARGO_BACKUP_RECIPIENT" --output "$ARGO_BACKUP_DIR/namespace-config.yaml.age.tmp"
mv "$ARGO_BACKUP_DIR/namespace-config.yaml.age.tmp" "$ARGO_BACKUP_DIR/namespace-config.yaml.age"
```

Conserve también los manifiestos de instalación/valores de Helm fijados, CRD y controllers de extensiones, y los procedimientos de recuperación para secretos externos/KMS, SSO, DNS y certificados. Las bases de datos/PV de aplicaciones necesitan copias de seguridad independientes. Elija la frecuencia y retención de las copias según sus RPO/RTO y su política de acceso.

### Alternativa de copia de seguridad de configuración con Velero

Este Schedule supone que Velero está instalado y que hay un BackupStorageLocation `aws-s3` disponible. Verifique la zona horaria de la programación, el cifrado y el control de acceso. Un selector de etiquetas part-of puede omitir las Applications creadas por usuarios, por lo que el ejemplo no tiene tal filtro. La recuperación de CRD/instalación/PV sigue siendo una parte independiente de DR.

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: argocd-config-backup
  namespace: velero
spec:
  schedule: 0 2 * * *
  template:
    includedNamespaces:
    - argocd
    includedResources:
    - applications.argoproj.io
    - applicationsets.argoproj.io
    - appprojects.argoproj.io
    - secrets
    - configmaps
    includeClusterResources: false
    storageLocation: aws-s3
    ttl: 720h0m0s
```

### Recuperación por etapas

Primero prepare una **instalación de recuperación aislada** usando la versión y el método de instalación originales. Establezca un único administrador activo para que las instancias primaria y de recuperación no modifiquen simultáneamente las mismas cargas de trabajo. Para el diseño predeterminado de StatefulSet, detenga los controllers de Application y ApplicationSet mientras inspecciona los cambios de importación. Adapte el tipo de carga de trabajo para la distribución dinámica.

```bash
set -euo pipefail
umask 077
: "${ARGO_BACKUP_FILE:?Set the encrypted data.yaml.age path}"
: "${ARGO_BACKUP_IDENTITY:?Set the protected age identity file}"

# Fresh, isolated recovery installation: default StatefulSet controller layout.
kubectl config current-context
kubectl scale statefulset/argocd-application-controller -n argocd --replicas=0
kubectl scale deployment/argocd-applicationset-controller -n argocd --replicas=0

ARGO_RESTORE_DIR="$(mktemp -d)"
trap 'rm -rf "$ARGO_RESTORE_DIR"' EXIT
age --decrypt --identity "$ARGO_BACKUP_IDENTITY" "$ARGO_BACKUP_FILE" \
  > "$ARGO_RESTORE_DIR/data.yaml"
argocd admin import -n argocd --dry-run "$ARGO_RESTORE_DIR/data.yaml"
# Keep controllers stopped while reviewing the recovery copy and destinations.
```

Revise el archivo de recuperación protegido en la misma shell: clústeres/namespaces de destino, credenciales de repositorio/clúster, finalizers de eliminación, políticas de sincronización automatizada y campos `operation` almacenados. Para retener la sincronización automática, actualice tanto las Applications como las plantillas de ApplicationSet y elimine las operaciones pendientes de la copia de recuperación. Compruebe si la fuente Git/Helm revertiría estas retenciones antes de reiniciar los controllers.

```bash
argocd admin import -n argocd "$ARGO_RESTORE_DIR/data.yaml"
```

Recupere los ConfigMaps/Secrets complementarios necesarios y las dependencias externas; a continuación, restaure las réplicas de controller desde la configuración de instalación revisada. Inspeccione los diffs/la salud de Applications representativas antes de reanudar las implementaciones individualmente. Una sincronización de todas las aplicaciones, una importación con `--prune` o la eliminación del namespace no es un paso de recuperación predeterminado.

## Estrategias de actualización {#upgrade-strategies}

### Propiedad de versión e instalación

El ejemplo se dirige a una actualización de parche 3.5.x revisada a 3.5.5, no a un salto incondicional desde 2.x o versiones menores anteriores. Revise cada nota de migración menor/mayor intermedia, combinación de Kubernetes probada y cambio de CRD/RBAC/SSO/CMP en entornos que no sean de producción. Conserve el propietario existente de manifiesto/Helm/GitOps. No aplique este procedimiento autogestionado a la capacidad administrada de Argo CD de EKS.

```bash
# Example: reviewed 3.5.x patch upgrade to 3.5.5, manifest-managed non-HA install.
kubectl config current-context
argocd version
kubectl apply --server-side -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.5/manifests/install.yaml
kubectl rollout status deployment/argocd-server -n argocd --timeout=5m
kubectl rollout status deployment/argocd-repo-server -n argocd --timeout=5m
kubectl rollout status statefulset/argocd-application-controller -n argocd --timeout=5m
kubectl rollout status deployment/argocd-applicationset-controller -n argocd --timeout=5m
kubectl rollout status deployment/argocd-notifications-controller -n argocd --timeout=5m
argocd version
argocd app list
```

Para una instalación de manifiesto HA, use `manifests/ha/install.yaml`; para overlays personalizados, actualice y renderice la base fijada. La aplicación del lado del servidor maneja CRD grandes. Inspeccione primero los conflictos de propiedad de campos; use `--force-conflicts` de la guía oficial solo para una transferencia de propiedad prevista. Los rollouts correctos de Pod no completan la validación de migración, SSO, diff y sync.

### Alternativa para instalaciones gestionadas por Helm

El chart 10.8.4 revisado implementa Argo CD v3.5.2, por lo que esta ruta de Helm no alcanza el parche 3.5.5 mencionado antes. Argo CD 3.5.5 aparece por primera vez en el chart 10.10.3, una actualización menor del chart que no se ha revisado aquí.

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd -f reviewed-values.yaml --dry-run=server --hide-secret
# After reviewing the dry run and the version-specific migration notes:
helm upgrade argocd argo/argo-cd --version 10.8.4 \
  --namespace argocd -f reviewed-values.yaml --wait --timeout 10m
```

`--hide-secret` oculta los manifiestos de Secret en la salida de dry-run; compruebe también si hay valores sensibles incrustados en otros lugares. Es posible que los cambios en CRD, datos persistentes e integraciones no se reviertan mediante un rollback de imagen, por lo que debe conservar un plan probado de copia de seguridad/recuperación.

### Límites de la validación en paralelo

Dos namespaces en un clúster siguen compartiendo CRD y otros recursos de ámbito de clúster. Cambiar solo el namespace de instalación no reescribe los subjects de ClusterRoleBinding. Kubernetes no tiene un comando `kubectl rename namespace`. Prefiera validar en un clúster independiente y planifique explícitamente las credenciales, los ID de seguimiento/instancia, los controllers activos y el cambio de tráfico. Eliminar el namespace antiguo puede propagarse mediante los finalizers de Application a las cargas de trabajo gestionadas.

## Resolución de problemas {#troubleshooting}

### Inspeccionar la sincronización y las diferencias

```bash
argocd app get my-app
argocd app diff my-app
argocd app history my-app
argocd app resources my-app
kubectl describe application my-app -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100

# Re-check desired state after identifying the cause; this does not apply resources.
argocd app get my-app --refresh
# Invalidates the cached target manifests for this Application; use sparingly.
argocd app get my-app --hard-refresh
```

`--force` no es una opción genérica de resolución de problemas y puede recrear recursos. La actualización completa no aplica ni revierte las cargas de trabajo, pero regenera manifiestos; evite ejecutarla repetidamente en todas las aplicaciones.

### Repositorios y webhooks

```bash
argocd repo list
argocd repo get https://github.com/myorg/myrepo.git
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repository
kubectl logs -n argocd deployment/argocd-server --tail=100 | grep -i webhook
```

Compruebe la confianza TLS/SSH, el alcance de las credenciales, DNS/egress y las firmas, URL y logs de entrega de los webhooks del proveedor. Enumerar nombres de Secret no requiere imprimir valores de credenciales. `argocd repo update --repo-cache-expiration` no es un comando válido de configuración de caché.

### OOM y procesamiento lento

```bash
kubectl top pods -n argocd
kubectl get pods -n argocd
kubectl describe pods -n argocd -l app.kubernetes.io/name=argocd-repo-server
argocd app get my-app -o json |
  jq '.status.operationState | {phase, startedAt, finishedAt}'
```

Distinga OOMKilled de la limitación de CPU, presión de disco de clones, manifiestos grandes, tiempos de espera de Git y limitación de API. Ajuste los recursos/la concurrencia mediante el propietario de Helm/Git. Eliminar todos los Pods de repo-server no borra la caché de manifiestos de Redis y añade carga de interrupción/clonado.

### Comprobaciones adicionales

```bash
argocd app manifests my-app
argocd app list -o wide
argocd cluster list
argocd cluster get https://my-target-cluster.example.com
kubectl logs -n argocd statefulset/argocd-application-controller --tail=100
kubectl logs -n argocd deployment/argocd-server --tail=100
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
```

Los manifiestos renderizados pueden incluir Secrets generados; manténgalos fuera de los logs compartidos. El controller predeterminado es un StatefulSet; inspeccione el Deployment real si la distribución dinámica está habilitada. Limite el registro de depuración temporal al componente afectado y gestione su rollout y eliminación.

## Prácticas recomendadas de EKS {#eks-best-practices}

### Credenciales de AWS

Un ARN de rol de ServiceAccount por sí solo no completa el acceso al EKS de destino. Configure la autenticación EKS del controller/server, los permisos assume-role, las entradas de acceso EKS de destino o la asignación de autenticación heredada y Kubernetes RBAC. Conceda a repo-server un rol independiente de mínimo privilegio solo cuando el acceso a S3/OCI/CMP lo requiera. También se requiere la confianza OIDC de IRSA o una asociación de Pod Identity; esto no es lo mismo que la autorización para extraer imágenes. Siga la [sección de instalación de EKS](01-installation.md#argocd-on-amazon-eks) para conocer el destino real y las cuentas de servicio.

### ALB interno con HTTPS

Esto requiere AWS Load Balancer Controller, conectividad de administrador a la VPC, certificado DNS/ACM coincidente, grupos de seguridad restringidos y SSO. Reemplace el ARN del certificado y el nombre de host. El backend permanece HTTPS con `server.insecure=false`; el acceso de CLI a través de este único grupo de destino HTTP usa `--grpc-web`.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd
  namespace: argocd
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:123456789012:certificate/REPLACE_WITH_CERTIFICATE_ID
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
spec:
  ingressClassName: alb
  rules:
  - host: argocd.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
```

Adjunte una Web ACL de WAF regional revisada en la misma región mediante su anotación independiente. Verifique la política y la región del bucket de logs de acceso de ALB. No habilite de forma predeterminada opciones de suscripción/con coste, como Shield Advanced.

### Actualizaciones de versión de EKS

Compruebe las combinaciones actuales/de destino probadas de EKS y Argo CD, la compatibilidad de complementos/CRD/nodo/kubelet y las API eliminadas. Actualice los planos de control de EKS una versión menor a la vez; las actualizaciones de nodos/complementos son independientes. Una actualización de versión in situ no requiere cambiar el endpoint de API existente. Un clúster de reemplazo sí requiere actualizaciones de endpoint/CA/acceso.

Si retiene la sincronización automática, registre la configuración original y cambie su propietario Git/ApplicationSet. Un cambio de Application secundaria solo mediante CLI puede ser revertido por su elemento padre. Después de verificar la conectividad, los diffs y una sincronización de muestra, restaure la política **original** de prune/selfHeal/automated en lugar de habilitar la automatización incondicionalmente.

## Lista de verificación de producción {#production-checklist}

- [ ] Verifique SSO/RBAC/TLS y el acceso de recuperación antes de deshabilitar el admin predeterminado
- [ ] Cifre/externalice secretos y limite las credenciales de repositorio/clúster
- [ ] Mida los recursos, la concurrencia y si se necesita fragmentación de clústeres
- [ ] Verifique nodos/anti-affinity/PDB de HA y réplicas/elección de líder específicas de componentes
- [ ] Valide la selección de métricas/ServiceMonitor y la entrega de alertas; recopile logs JSON y auditoría/eventos de Kubernetes
- [ ] Aplique origen/destino de AppProject, ventanas de sincronización y PR de promoción revisadas
- [ ] Pruebe el descifrado de copias de seguridad cifradas, la recuperación de configuración complementaria y DR de administrador único
- [ ] Mantenga runbooks de actualización, resolución de problemas y restauración de configuración específicos de la versión

## Referencias

- [Prácticas recomendadas](https://argo-cd.readthedocs.io/en/release-3.5/user-guide/best_practices/)
- [Alta disponibilidad y escalado](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/high_availability/)
- [Implementación y alcance de copia de seguridad](https://github.com/argoproj/argo-cd/blob/v3.5.5/cmd/argocd/commands/admin/backup.go)
- [Guía de actualización](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/upgrading/overview/)
- [Valores de Chart 10.8.4](https://github.com/argoproj/argo-helm/blob/argo-cd-10.8.4/charts/argo-cd/values.yaml)
- [Versión incluida de Kustomize](https://github.com/argoproj/argo-cd/blob/v3.5.5/hack/tool-versions.sh)
- [Programaciones de Velero](https://velero.io/docs/main/backup-reference/#schedule-a-backup)

## Cuestionario

Pruebe el [cuestionario de prácticas recomendadas](../../quizzes/gitops/argocd/09-best-practices-quiz.md).
