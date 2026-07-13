# Cuestionario sobre mecanismos de extensión de Kubernetes

> **Documento relacionado**: [Mecanismos de extensión de Kubernetes](../../platform-engineering/04-kubernetes-extensions.md)

## Preguntas de opción múltiple

### 1. ¿Cuál es el propósito principal de un CRD (Custom Resource Definition)?

- A) Modificar recursos existentes de Kubernetes
- B) Extender la API de Kubernetes con tipos de recursos personalizados
- C) Configurar la red de Pod
- D) Aprovisionar volúmenes de almacenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Extender la API de Kubernetes con tipos de recursos personalizados**

**Explicación:**
Los CRD permiten extender la API de Kubernetes definiendo tipos de recursos personalizados que se comportan como recursos nativos de Kubernetes.

</details>

### 2. ¿Cuál es la tarea principal que realiza el ciclo de reconciliación de un Custom Controller?

- A) Eliminar recursos inmediatamente
- B) Reconciliar diferencias entre el estado actual y el estado deseado
- C) Registrar nuevas API con el API server
- D) Aplicar políticas de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reconciliar diferencias entre el estado actual y el estado deseado**

**Explicación:**
El ciclo de reconciliación del Custom Controller observa el estado actual de los recursos, lo compara con el estado deseado (spec) y toma acciones para alcanzar el estado deseado cuando existen diferencias.

</details>

### 3. ¿Cuáles son los componentes principales del patrón Operator?

- A) Deployment y Service
- B) CRD y Custom Controller
- C) ConfigMap y Secret
- D) Ingress y NetworkPolicy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) CRD y Custom Controller**

**Explicación:**
El patrón Operator usa CRD para definir la configuración de aplicaciones y Custom Controllers para automatizar conocimiento operativo, como despliegue, actualizaciones y recuperación.

</details>

### 4. ¿Cuál es el uso principal de MutatingAdmissionWebhook?

- A) Rechazar solicitudes de API
- B) Modificar solicitudes de API
- C) Registrar respuestas de API
- D) Actualizar versiones de API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Modificar solicitudes de API**

**Explicación:**
MutatingAdmissionWebhook puede modificar solicitudes de API antes de que se persistan. Los usos comunes incluyen: inyección de contenedores sidecar, configuración de valores predeterminados, etc.

</details>

### 5. ¿Cuál es el rol del plugin Filter en el scheduler framework?

- A) Asignar puntuaciones a los nodes
- B) Excluir nodes que no pueden ejecutar el Pod
- C) Vincular el Pod a un node
- D) Reservar recursos de node

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Excluir nodes que no pueden ejecutar el Pod**

**Explicación:**
Los plugins Filter filtran los nodes que no cumplen con los requisitos del Pod, excluyéndolos de la consideración.

</details>

### 6. ¿Cuál es la diferencia entre Aggregated API Server y CRD?

- A) No hay diferencia, son lo mismo
- B) Aggregated API proporciona más control, pero requiere ejecutar un servidor separado
- C) CRD proporciona más funcionalidades que Aggregated API
- D) Aggregated API está obsoleto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Aggregated API proporciona más control, pero requiere ejecutar un servidor separado**

**Explicación:**
Aggregated API Server proporciona control total sobre el comportamiento de la API, backends de almacenamiento personalizados y funcionalidades avanzadas, pero requiere desplegar y mantener un API server separado. Los CRD son más simples, pero tienen limitaciones.

</details>

### 7. ¿Cuál es el propósito de un Finalizer en Kubernetes?

- A) Acelerar la eliminación de recursos
- B) Evitar la eliminación de recursos hasta que se complete la limpieza
- C) Reiniciar automáticamente Pods fallidos
- D) Validar la creación de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Evitar la eliminación de recursos hasta que se complete la limpieza**

**Explicación:**
Los Finalizers bloquean la eliminación de recursos hasta que el controller realiza las operaciones de limpieza necesarias (como eliminar recursos externos) y elimina el finalizer.

</details>

### 8. ¿Qué punto de extensión del scheduler se ejecuta después de que un Pod se ha vinculado a un node?

- A) PreFilter
- B) PostBind
- C) Reserve
- D) Score

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PostBind**

**Explicación:**
Los plugins PostBind se llaman después de que el Pod se ha vinculado correctamente a un node. Son informativos y se usan para limpieza o notificaciones.

</details>

### 9. ¿Qué anotación se usa para inyectar sidecars mediante admission webhook en Istio?

- A) istio.io/inject
- B) sidecar.istio.io/inject
- C) istio-injection
- D) auto-inject.istio.io

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) sidecar.istio.io/inject**

**Explicación:**
La anotación `sidecar.istio.io/inject` controla si el mutating webhook de Istio inyecta el sidecar Envoy en un Pod. El control a nivel de namespace usa la etiqueta `istio-injection`.

</details>

### 10. ¿Cuál es el propósito del plugin Score en el scheduler framework?

- A) Filtrar nodes no adecuados
- B) Clasificar los nodes y seleccionar el mejor
- C) Vincular el Pod al node seleccionado
- D) Validar especificaciones de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Clasificar los nodes y seleccionar el mejor**

**Explicación:**
Los plugins Score asignan puntuaciones a los nodes que pasaron el filtrado. El scheduler selecciona el node con la puntuación combinada más alta de todos los plugins Score.

</details>

## Preguntas de respuesta corta

### 1. ¿Qué estándar se usa para la validación de esquemas en CRD?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: OpenAPI v3 Schema (openAPIV3Schema)**

**Explicación:**
Los CRD usan OpenAPI v3 schema en `spec.versions[].schema.openAPIV3Schema` para definir la estructura y las reglas de validación de recursos personalizados.

</details>

### 2. ¿Cuál es el rol de Owner Reference en los controllers de Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Definir relaciones de propiedad entre recursos y gestionar la recolección de basura y la propagación de eventos**

**Explicación:**
Owner Reference define relaciones padre-hijo y elimina automáticamente los hijos cuando el padre se elimina mediante la garbage collection de Kubernetes.

</details>

### 3. ¿Cuál es la diferencia entre ValidatingAdmissionPolicy y ValidatingAdmissionWebhook?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ValidatingAdmissionPolicy usa expresiones CEL y se ejecuta dentro del proceso, mientras que ValidatingAdmissionWebhook llama a endpoints HTTP externos.**

**Explicación:**
ValidatingAdmissionPolicy (introducida en 1.26) proporciona mejor rendimiento y no requiere infraestructura externa de webhook, pero tiene menos flexibilidad que los webhooks.

</details>

### 4. ¿Qué es la biblioteca controller-runtime y por qué se usa comúnmente?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: controller-runtime es una biblioteca que proporciona patrones comunes para crear controllers de Kubernetes, incluido el almacenamiento en caché de clientes, la elección de líder y la gestión del ciclo de reconciliación.**

**Explicación:**
Como parte del proyecto Kubebuilder, controller-runtime abstrae el código repetitivo y las mejores prácticas, lo que facilita crear operators confiables.

</details>

### 5. ¿Cuál es el propósito de los conversion webhooks en CRD?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Los conversion webhooks convierten recursos entre diferentes versiones de API del mismo CRD.**

**Explicación:**
Cuando un CRD tiene varias versiones (por ejemplo, v1alpha1, v1beta1, v1), los conversion webhooks gestionan la transformación entre versiones para admitir la evolución de la API.

</details>

## Preguntas prácticas

### 1. Escribe un CRD que cumpla los siguientes requisitos:

- Nombre: WebApp
- Grupo: apps.example.com
- Campos: replicas (integer, mínimo 1), image (string, obligatorio)

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: webapps.apps.example.com
spec:
  group: apps.example.com
  names:
    kind: WebApp
    plural: webapps
    singular: webapp
    shortNames:
      - wa
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["image"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  default: 1
                image:
                  type: string
            status:
              type: object
              properties:
                availableReplicas:
                  type: integer
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Replicas
          type: integer
          jsonPath: .spec.replicas
        - name: Available
          type: integer
          jsonPath: .status.availableReplicas
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

</details>

### 2. Escribe una configuración de ValidatingAdmissionWebhook que valide todos los Deployments en el namespace "production".

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: deployment-validator
webhooks:
  - name: validate-deployment.example.com
    clientConfig:
      service:
        name: webhook-service
        namespace: webhook-system
        path: /validate-deployment
      caBundle: <base64-encoded-ca-cert>
    rules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
        scope: Namespaced
    namespaceSelector:
      matchLabels:
        environment: production
    failurePolicy: Fail
    sideEffects: None
    admissionReviewVersions: ["v1"]
    timeoutSeconds: 10
```

**Explicación:**
- `namespaceSelector` limita el webhook a namespaces con la etiqueta `environment: production`
- `failurePolicy: Fail` rechaza solicitudes si el webhook no está disponible
- `sideEffects: None` indica que el webhook no tiene efectos secundarios

</details>

### 3. Escribe pseudocódigo de un ciclo de reconciliación simple para un Custom Controller.

<details>
<summary>Mostrar respuesta</summary>

```go
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := log.FromContext(ctx)

    // 1. Fetch the WebApp resource
    var webapp appsv1.WebApp
    if err := r.Get(ctx, req.NamespacedName, &webapp); err != nil {
        if errors.IsNotFound(err) {
            // Resource deleted, nothing to do
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // 2. Check if being deleted (handle finalizers)
    if !webapp.DeletionTimestamp.IsZero() {
        if containsFinalizer(webapp, finalizerName) {
            // Perform cleanup
            if err := r.cleanupExternalResources(&webapp); err != nil {
                return ctrl.Result{}, err
            }
            // Remove finalizer
            removeFinalizer(&webapp, finalizerName)
            if err := r.Update(ctx, &webapp); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // 3. Add finalizer if not present
    if !containsFinalizer(webapp, finalizerName) {
        addFinalizer(&webapp, finalizerName)
        if err := r.Update(ctx, &webapp); err != nil {
            return ctrl.Result{}, err
        }
    }

    // 4. Create or update Deployment
    deployment := r.constructDeployment(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, deployment, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, deployment); err != nil {
        return ctrl.Result{}, err
    }

    // 5. Create or update Service
    service := r.constructService(&webapp)
    if err := controllerutil.SetControllerReference(&webapp, service, r.Scheme); err != nil {
        return ctrl.Result{}, err
    }
    
    if err := r.CreateOrUpdate(ctx, service); err != nil {
        return ctrl.Result{}, err
    }

    // 6. Update status
    webapp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
    if err := r.Status().Update(ctx, &webapp); err != nil {
        return ctrl.Result{}, err
    }

    // 7. Requeue after interval for periodic reconciliation
    return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
}
```

**Puntos clave:**
- Manejar siempre el recurso no encontrado (puede haber sido eliminado)
- Usar finalizers para la limpieza de recursos externos
- Establecer owner references para la garbage collection
- Actualizar el subrecurso status por separado
- Considerar intervalos de requeue para comprobaciones periódicas

</details>

## Preguntas avanzadas

### 1. Diseña un Kubernetes Operator para un sistema distribuido complejo.

<details>
<summary>Mostrar respuesta</summary>

**Diseño de CRD:**
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.database.example.com
spec:
  group: database.example.com
  names:
    kind: PostgresCluster
    plural: postgresclusters
    shortNames:
      - pg
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required: ["replicas", "version"]
              properties:
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
                version:
                  type: string
                  enum: ["14", "15", "16"]
                storage:
                  type: object
                  properties:
                    size:
                      type: string
                      default: "10Gi"
                    storageClass:
                      type: string
                backup:
                  type: object
                  properties:
                    enabled:
                      type: boolean
                      default: true
                    schedule:
                      type: string
                      default: "0 2 * * *"
                    retention:
                      type: integer
                      default: 7
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum: ["Creating", "Running", "Upgrading", "Failed", "Deleting"]
                primaryEndpoint:
                  type: string
                replicaEndpoints:
                  type: array
                  items:
                    type: string
                currentVersion:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:
                        type: string
                      status:
                        type: string
                      reason:
                        type: string
                      message:
                        type: string
                      lastTransitionTime:
                        type: string
                        format: date-time
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
```

**Lógica central del Controller:**
- **Gestión de estado basada en fases** (Creating, Running, Upgrading, Failed)
- **Recuperación automática ante fallos** (Failover cuando Primary falla)
- **Estrategia de actualización gradual** (actualizar primero las replicas y luego primary)
- **Gestión de backups** (CronJob para backups programados)

**Arquitectura:**
```
PostgresCluster CR
       |
       v
   Controller
       |
       +---> StatefulSet (PostgreSQL pods)
       +---> Service (Primary endpoint)
       +---> Service (Replica endpoint)
       +---> Secret (Credentials)
       +---> ConfigMap (PostgreSQL config)
       +---> CronJob (Backups)
       +---> PodDisruptionBudget
```

</details>

### 2. Explica cómo implementar un scheduler personalizado usando el scheduler framework.

<details>
<summary>Mostrar respuesta</summary>

**Implementación del plugin Scheduler:**

```go
// Plugin implementing multiple extension points
type CustomSchedulerPlugin struct {
    handle framework.Handle
}

// Implement PreFilter - check pod requirements
func (p *CustomSchedulerPlugin) PreFilter(ctx context.Context, state *framework.CycleState, pod *v1.Pod) (*framework.PreFilterResult, *framework.Status) {
    // Validate pod has required annotations
    if _, ok := pod.Annotations["custom-scheduler/zone"]; !ok {
        return nil, framework.NewStatus(framework.Unschedulable, "missing zone annotation")
    }
    return nil, framework.NewStatus(framework.Success, "")
}

// Implement Filter - exclude unsuitable nodes
func (p *CustomSchedulerPlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
    requiredZone := pod.Annotations["custom-scheduler/zone"]
    nodeZone := nodeInfo.Node().Labels["topology.kubernetes.io/zone"]
    
    if requiredZone != nodeZone {
        return framework.NewStatus(framework.Unschedulable, "zone mismatch")
    }
    return framework.NewStatus(framework.Success, "")
}

// Implement Score - rank suitable nodes
func (p *CustomSchedulerPlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
    nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
    if err != nil {
        return 0, framework.NewStatus(framework.Error, err.Error())
    }
    
    // Score based on available resources
    allocatable := nodeInfo.Node().Status.Allocatable
    requested := nodeInfo.Requested
    
    cpuScore := calculateResourceScore(allocatable.Cpu(), requested.Cpu)
    memScore := calculateResourceScore(allocatable.Memory(), requested.Memory)
    
    return (cpuScore + memScore) / 2, framework.NewStatus(framework.Success, "")
}

// Register the plugin
func New(_ runtime.Object, h framework.Handle) (framework.Plugin, error) {
    return &CustomSchedulerPlugin{handle: h}, nil
}
```

**Configuración del Scheduler:**

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: custom-scheduler
    plugins:
      preFilter:
        enabled:
          - name: CustomSchedulerPlugin
      filter:
        enabled:
          - name: CustomSchedulerPlugin
      score:
        enabled:
          - name: CustomSchedulerPlugin
        disabled:
          - name: NodeResourcesBalancedAllocation
```

**Resumen de puntos de extensión:**

| Extension Point | Propósito | Cuándo se ejecuta |
|----------------|---------|-----------|
| PreFilter | Comprobaciones a nivel de Pod | Antes del filtrado |
| Filter | Eliminación de nodes | Para cada node |
| PostFilter | Manejar lo no programable | Cuando ningún node encaja |
| PreScore | Preparar la puntuación | Antes de puntuar |
| Score | Clasificación de nodes | Para nodes filtrados |
| NormalizeScore | Normalización de puntuaciones | Después de todas las puntuaciones |
| Reserve | Reserva de recursos | Después de seleccionar el node |
| Permit | Aprobación final | Antes del binding |
| PreBind | Acciones previas al binding | Antes del binding de API |
| Bind | Binding real | Actualización del API server |
| PostBind | Limpieza posterior al binding | Después del binding |

</details>
