# Cuestionario sobre migración de Helm a KRO

> **Documento relacionado**: [Kubernetes Resource Operator (KRO)](../../platform-engineering/03-kro.md)

## Preguntas de opción múltiple

### 1. ¿Cuál de los siguientes NO es un concepto central de Kubernetes Resource Operator (KRO)?

- A) Relaciones declarativas entre recursos
- B) Reconciliation basada en estado
- C) Ejecución imperativa de scripts
- D) Resource graph

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ejecución imperativa de scripts**

**Explicación:**
KRO administra recursos de forma declarativa. Las relaciones declarativas entre recursos, la reconciliation basada en estado, el resource graph y la administración automatizada del ciclo de vida son conceptos centrales, mientras que la ejecución imperativa de scripts no forma parte de los conceptos centrales de KRO.

</details>

### 2. ¿Cuál es el rol de `childResources` en una ResourceGraphDefinition (RGD)?

- A) Definir los metadatos del recurso parent
- B) Definir la lista de child resources que se crearán a partir del recurso parent
- C) Definir configuraciones de todo el cluster
- D) Definir políticas de namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir la lista de child resources que se crearán a partir del recurso parent**

**Explicación:**
`childResources` define la lista y las plantillas de child Kubernetes resources (Deployment, Service, Ingress, etc.) que se crearán a partir del parent custom resource.

</details>

### 3. ¿Cuál es el principal diferenciador de KRO en comparación con Helm?

- A) Uso de plantillas Go
- B) Empaquetado de archivos de Chart
- C) Modelado explícito de relaciones entre recursos y propagación automática de estado
- D) Administración del historial de releases

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Modelado explícito de relaciones entre recursos y propagación automática de estado**

**Explicación:**
KRO modela las relaciones entre recursos como un grafo explícito y propaga automáticamente los estados de child resources al parent resource.

</details>

### 4. ¿A qué hace referencia `.parent` en las plantillas RGD?

- A) Cluster de Kubernetes
- B) Parent custom resource
- C) Namespace
- D) Controller pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Parent custom resource**

**Explicación:**
En las plantillas RGD, `.parent` hace referencia al parent custom resource al que se aplica la ResourceGraphDefinition.

</details>

### 5. ¿Qué campo se usa para la creación condicional de child resources en KRO?

- A) `when`
- B) `if`
- C) `condition`
- D) `enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) `condition`**

**Explicación:**
El campo `condition` en `childResources` de una RGD se puede usar para crear child resources de forma condicional.

</details>

### 6. ¿Cuál es el propósito de `statusMappings` en una RGD?

- A) Definir el comportamiento de manejo de errores
- B) Mapear el status del child resource al status del parent resource
- C) Configurar niveles de logging
- D) Establecer resource quotas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mapear el status del child resource al status del parent resource**

**Explicación:**
`statusMappings` define cómo extraer información de status de child resources y propagarla al campo status del parent custom resource.

</details>

### 7. ¿Cómo maneja KRO las dependencias entre recursos?

- A) Mediante ordenamiento manual en archivos YAML
- B) Mediante el resource graph que determina automáticamente el orden de creación
- C) Mediante campos numéricos de prioridad
- D) Mediante orden alfabético

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante el resource graph que determina automáticamente el orden de creación**

**Explicación:**
KRO usa el resource graph para entender las dependencias entre recursos y determinar automáticamente el orden correcto para la creación y eliminación de recursos.

</details>

### 8. ¿Qué sucede cuando se elimina un parent custom resource en KRO?

- A) Los child resources quedan huérfanos
- B) Los child resources se eliminan automáticamente mediante garbage collection
- C) Se requiere limpieza manual
- D) Se lanza un error

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los child resources se eliminan automáticamente mediante garbage collection**

**Explicación:**
KRO establece owner references en los child resources, de modo que cuando se elimina el parent, el garbage collector de Kubernetes elimina automáticamente todos los child resources.

</details>

### 9. ¿Qué componente observa los cambios en custom resources en KRO?

- A) API Server
- B) Scheduler
- C) KRO Controller
- D) Kubelet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) KRO Controller**

**Explicación:**
El KRO Controller observa los cambios en custom resources definidos por ResourceGraphDefinitions y reconcilia el estado deseado.

</details>

### 10. ¿Cuál es el equivalente en KRO del comportamiento de `helm upgrade --install` de Helm?

- A) `kubectl apply` en el custom resource
- B) `kubectl replace` en el custom resource
- C) `kubectl patch` en el custom resource
- D) `kubectl create --save-config`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `kubectl apply` en el custom resource**

**Explicación:**
`kubectl apply` proporciona un comportamiento idempotente similar a `helm upgrade --install`. Crea el recurso si no existe y lo actualiza si existe.

</details>

## Preguntas de respuesta corta

### 1. ¿Cuál es el recurso central en KRO que define la relación entre custom resources y recursos nativos de Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: ResourceGraphDefinition (RGD)**

**Explicación:**
ResourceGraphDefinition (RGD) es el componente central de KRO que define de forma declarativa la relación entre custom resources (parent) y recursos nativos de Kubernetes (children).

</details>

### 2. ¿Cuál es el equivalente en KRO de values.yaml de Helm?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: El campo spec del Custom Resource (CR)**

**Explicación:**
Así como Helm personaliza la configuración mediante values.yaml, KRO define la configuración de la aplicación mediante el campo spec del custom resource.

</details>

### 3. ¿Cómo haces referencia a la salida de un sibling child resource en una plantilla RGD?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Usando la sintaxis `.children.<resourceId>`**

**Explicación:**
En las plantillas RGD, puedes hacer referencia a otros child resources usando `.children.<resourceId>` para acceder a sus campos de metadata, spec o status para referencias entre recursos.

</details>

### 4. ¿Qué annotation usa KRO para rastrear recursos administrados?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: annotation `kro.run/owner`**

**Explicación:**
KRO usa la annotation `kro.run/owner` junto con Kubernetes owner references para rastrear qué recursos son administrados por cada parent custom resource.

</details>

### 5. ¿Cómo maneja KRO la validación de schema para custom resources?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: Mediante OpenAPI v3 Schema definido en el campo spec.schema de la RGD**

**Explicación:**
KRO genera una CRD a partir de la RGD, y la validación de schema se realiza usando OpenAPI v3 Schema definido en la ResourceGraphDefinition.

</details>

## Preguntas prácticas

### 1. Convierte el siguiente values.yaml de Helm en una instancia de custom resource de KRO.

```yaml
# Helm values.yaml
replicaCount: 2
image:
  repository: myapp
  tag: "1.0.0"
service:
  type: ClusterIP
  port: 8080
```

<details>
<summary>Mostrar respuesta</summary>

```yaml
apiVersion: kro.example.com/v1
kind: MyApp
metadata:
  name: my-application
spec:
  replicas: 2
  image:
    repository: myapp
    tag: "1.0.0"
  service:
    type: ClusterIP
    port: 8080
```

</details>

### 2. Escribe una definición de RGD childResource que cree un Deployment basado en el parent spec.

<details>
<summary>Mostrar respuesta</summary>

```yaml
childResources:
  - id: deployment
    resource:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: "{{.parent.metadata.name}}"
      spec:
        replicas: "{{.parent.spec.replicas}}"
        selector:
          matchLabels:
            app: "{{.parent.metadata.name}}"
        template:
          metadata:
            labels:
              app: "{{.parent.metadata.name}}"
          spec:
            containers:
              - name: app
                image: "{{.parent.spec.image.repository}}:{{.parent.spec.image.tag}}"
                ports:
                  - containerPort: "{{.parent.spec.service.port}}"
```

</details>

### 3. Escribe una configuración de statusMappings que exponga las réplicas disponibles del Deployment en el status del parent.

<details>
<summary>Mostrar respuesta</summary>

```yaml
statusMappings:
  - childResourceId: deployment
    fieldPath: status.availableReplicas
    parentFieldPath: status.availableReplicas
  - childResourceId: deployment
    fieldPath: status.conditions
    parentFieldPath: status.deploymentConditions
```

**Explicación:**
statusMappings extrae campos específicos del status del child resource y los mapea al status del parent custom resource, lo que permite a los usuarios comprobar el estado de la aplicación mediante el parent resource.

</details>

## Preguntas avanzadas

### 1. Diseña una estrategia de deployment multi-entorno (dev/staging/production) usando KRO.

<details>
<summary>Mostrar respuesta</summary>

**Instancias de Custom Resource específicas por entorno:**

```yaml
# dev/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-dev
spec:
  replicas: 1
  image:
    tag: "dev-latest"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
---
# staging/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-staging
spec:
  replicas: 2
  image:
    tag: "rc-1.0.0"
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
---
# production/webapp.yaml
apiVersion: kro.example.com/v1
kind: WebApp
metadata:
  name: myapp
  namespace: app-prod
spec:
  replicas: 3
  image:
    tag: "v1.0.0"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
  resources:
    requests:
      cpu: "500m"
      memory: "512Mi"
```

**Integración con GitOps:**
Usa ArgoCD ApplicationSet para automatizar deployments específicos por entorno con una sola RGD en todos los entornos.

</details>

### 2. Compara las diferencias operativas entre Helm y KRO para administrar una aplicación con estado como un cluster de base de datos.

<details>
<summary>Mostrar respuesta</summary>

**Enfoque de Helm:**
- Basado en plantillas: genera manifiestos estáticos en el momento de la instalación
- Administración de releases: rastrea versiones mediante Secrets/ConfigMaps
- Proceso de upgrade: requiere el comando `helm upgrade`
- Seguimiento de estado: no hay reconciliation integrada después del deployment inicial
- Rollback: usa el historial de releases almacenado

**Enfoque de KRO:**
- Basado en reconciliation: monitorea y corrige continuamente el drift
- Kubernetes nativo: usa kubectl y CRDs estándar
- Proceso de upgrade: modifica el CR spec, el controller reconcilia
- Seguimiento de estado: el controller observa y reconcilia continuamente
- Rollback: revierte el CR spec al estado anterior

**Diferencias clave para aplicaciones con estado:**

| Aspect | Helm | KRO |
|--------|------|-----|
| Drift Detection | Manual | Automatic |
| Self-healing | No | Yes |
| Status Visibility | External (helm status) | Native (kubectl get) |
| Dependency Management | Chart dependencies | Resource graph |
| Lifecycle Hooks | pre/post hooks | Controller logic |

**Recomendación:**
KRO es más adecuado para aplicaciones con estado que requieren reconciliation continua, corrección automática de drift y administración compleja del ciclo de vida. Helm es más simple para aplicaciones sin estado con deployments directos.

</details>
