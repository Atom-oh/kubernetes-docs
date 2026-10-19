# Gestión de políticas con Kyverno

> **Referencia de validación**: Kyverno/CLI 1.19.1, Helm chart 3.9.1. La guía de la versión actual indica que Kubernetes 1.33–1.35 se probaron; el requisito de instalación más amplio del chart no garantiza compatibilidad.
> **Última actualización**: 19 de octubre de 2026

Kyverno evalúa las políticas de Kubernetes y realiza las operaciones de mutación, generación y eliminación que se configuren explícitamente. Estos ejemplos se verificaron localmente con el CLI real y los esquemas/charts publicados. No se realizó ninguna instalación en un clúster activo, admisión, aislamiento de red, limpieza ni integración con AWS.

Los ejemplos originales de `ClusterPolicy` se actualizaron a políticas CEL `policies.kyverno.io/v1`. La guía oficial de migración de la versión 1.19 marca como obsoletos ClusterPolicy/Policy, CleanupPolicy y PolicyException heredado `kyverno.io`, cuya eliminación está prevista para la versión 1.20. No han desaparecido aún en la versión 1.19; migre y haga pruebas antes de actualizar, en lugar de limitarse a reemplazar una cadena apiVersion.

## Configuración del entorno del laboratorio

### Herramientas necesarias

Para estas pruebas locales, use kubectl con una diferencia de versiones admitida por el servidor de API de destino, una versión compatible de Helm con capacidad para OCI y el CLI verificado de Kyverno 1.19.1. Obtenga el archivo del CLI correspondiente al sistema operativo y la arquitectura, y verifique la suma de comprobación/firma publicada. No reutilice un archivo de la versión 1.10.0 ni canalice una descarga no verificada a una instalación con permisos de root.

Empiece con archivos locales. Las políticas siguientes son ejemplos independientes, no un conjunto para aplicar en bloque. Los ejemplos de Pod se dirigen a `policy-lab`; la generación también requiere una etiqueta explícita. Restrinja quién puede modificar estas políticas, las etiquetas de los espacios de nombres, los Roles y las PolicyExceptions. Esos selectores no constituyen por sí solos un límite de seguridad de RBAC.

### Instalación de Kyverno

Prepare un espacio de nombres dedicado `kyverno`. Antes de modificar un clúster compartido, compruebe la versión elegida de EKS/Kubernetes, la conectividad entre el servidor de API y el webhook, el DNS, el comportamiento ante errores/tiempos de espera de admisión y el procedimiento de actualización de CRD. Las ServiceAccounts/RBAC de Kubernetes autorizan a los controladores; la instalación de Kyverno no requiere por sí misma un rol de administrador de AWS.

## Introducción a Kyverno

### Arquitectura de Kyverno y su funcionamiento

| Componente | Responsabilidad |
|---|---|
| Controlador de admisión | Coincidir con las solicitudes de admisión y validar/mutar políticas y comprobar imágenes; no procesa todas las solicitudes GET/list |
| Controlador en segundo plano | Generar y realizar las operaciones mutate-existing habilitadas explícitamente |
| Controlador de informes | Agregar e informar los resultados de las políticas |
| Controlador de limpieza | Políticas de eliminación programada y operaciones de limpieza permitidas |

Una política de validación no elimina ni repara los recursos existentes que no cumplen las reglas. Los informes en segundo plano, mutate-existing, generate-existing y la eliminación programada son mecanismos independientes con permisos distintos. La generación puede ser asíncrona; la creación del espacio de nombres y la aplicación de NetworkPolicy generadas no son una operación atómica.

### Kyverno frente a OPA Gatekeeper

Las políticas actuales de Kyverno usan CEL en manifiestos YAML/JSON; las políticas heredadas también usan patrones y JMESPath. El empaquetado nativo de Kubernetes no elimina la necesidad de aprender expresiones de políticas. Gatekeeper usa ConstraintTemplates/Constraints y los motores de políticas compatibles con su versión, con capacidades independientes de admisión/auditoría/mutación. Compare las funciones necesarias, los lenguajes de expresiones, las pruebas de políticas, la disponibilidad de los controladores y el impacto medido en la carga de trabajo. Las antiguas calificaciones de «fácil/complejo» y «rendimiento bueno/muy bueno» eran comparaciones sin fundamento, no pruebas de rendimiento.

### Actualización de octubre de 2026: aplicación en tiempo de ejecución, más allá de la admisión

En una [publicación de CNCF del 15 de octubre de 2026](https://www.cncf.io/blog/2026/10/15/extending-kubernetes-policy-enforcement-to-runtime-security-for-ai-workloads/), Nirmata (creadora de Kyverno) describe los límites del control de admisión —que solo responde «¿esta especificación parece correcta?» y no puede detectar que una carga de trabajo en ejecución se desvíe de su especificación (por ejemplo, una carga útil de segunda etapa que se descarga después del inicio o tráfico dirigido a un destino no aprobado)— y presenta **Nirmata Runtime for Kyverno**, una implementación de código abierto que aplica políticas a nivel del kernel mediante eBPF y los módulos de seguridad de Linux (LSM). Este enfoque está dirigido a la seguridad en tiempo de ejecución de cargas de trabajo no deterministas, como los agentes de IA. Es un componente separado, con sus propios permisos, distinto de las políticas de admisión/en segundo plano de este capítulo; además, la publicación es una presentación del proveedor (Nirmata). Antes de adoptarlo, compruebe el alcance de las funciones y los requisitos del kernel/plataforma.

## Instalación de Kyverno

### Instalación mediante Helm

Guarde esto como `kyverno-values.yaml`. Es una configuración de **laboratorio** con una sola réplica. Las CRD de ServiceMonitor y una instalación de Prometheus que seleccione el espacio de nombres/las etiquetas reales ya deben existir; sustituya la etiqueta de ejemplo `release: kube-prom` por el selector de esa instalación, o desactive ServiceMonitors hasta que esté todo preparado.

```yaml
admissionController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
backgroundController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
cleanupController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
reportsController:
  replicas: 1
  serviceMonitor:
    enabled: true
    additionalLabels:
      release: kube-prom
```

```bash
# Use an approved context; this changes real cluster resources.
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm template kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --values kyverno-values.yaml > kyverno-rendered.yaml
# Inspect the render, CRD migration and webhook reachability before installation.
helm upgrade --install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace --kube-context "$KUBE_CONTEXT" \
  --values kyverno-values.yaml
```

El renderizado contiene cuatro Deployments de controladores y cuatro ServiceMonitors de métricas. Para usar más réplicas se necesita planificar la topología, las interrupciones, el dimensionamiento de recursos y la disponibilidad de los webhooks; una réplica por controlador no es un diseño de alta disponibilidad. Inspeccione los valores predeterminados del chart actual y las etiquetas de imagen realmente renderizadas, en lugar de interpretar la etiqueta de versión del chart como la versión de la aplicación.

### Instalación mediante manifiestos YAML

Si GitOps administra YAML, renderice el chart fijado a una versión y revise sus CRD, RBAC, certificados y hooks como un conjunto administrado. Un `kubectl apply` directo del renderizado no ejecuta la semántica de hooks/actualización de Helm. No aplique el antiguo install.yaml de la versión 1.10.0 sobre una versión más reciente ni mezcle varios responsables de los mismos controladores.

## Tipos de políticas

### 1. Políticas de validación

Guarde este ejemplo independiente como `require-limits.yaml`. Comprueba que los contenedores **normales y de inicialización** tengan límites no vacíos de CPU/memoria. Los contenedores efímeros no pueden declarar solicitudes/límites de recursos; las comprobaciones de seguridad de abajo los cubren por separado. Esta es una política elegida para cada contenedor, no una afirmación de que todas las cargas de trabajo de Kubernetes deban usar esta estrategia de recursos.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-container-limits
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, has(c.resources) && has(c.resources.limits) && ['cpu', 'memory'].all(k, k in c.resources.limits
      && string(c.resources.limits[k]) != ''))
    message: Normal and init containers need nonempty CPU and memory limits.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([])
```

`validationActions: [Audit]` registra las infracciones y permite las solicitudes de admisión coincidentes; `[Deny]` las rechaza después de evaluar la puesta en marcha/el impacto. `Warn` puede mostrar advertencias al cliente. La opción `failurePolicy` del webhook determina qué ocurre si falla la evaluación/el transporte, y es una configuración distinta. Un resultado fallido del CLI sin conexión no demuestra que una política Audit haya rechazado una solicitud activa.

### 2. Políticas de mutación

Guarde el archivo como `add-default-label.yaml`. Se conservan las etiquetas `environment` existentes, incluso si sus valores se han dejado explícitamente vacíos. Esto usa ApplyConfiguration de CEL, no la sintaxis `if`/`hasKey` de las plantillas Go de Helm dentro de Kyverno.

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: add-default-label
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        has(object.metadata.labels) && 'environment' in object.metadata.labels
        ? Object{}
        : Object{metadata: Object.metadata{labels: {"environment": object.metadata.namespace}}}
```

El ejemplo desactiva mutate-existing. La mutación de admisión aún puede afectar las solicitudes CREATE/UPDATE coincidentes. Una alternativa con JSONPatch debe crear un mapa de etiquetas cuando no exista antes de agregar una clave secundaria, y debe escapar `/` como `~1` en las rutas de JSON Pointer. No se garantiza el orden de mutación entre políticas independientes.

### 3. Políticas de generación

Guarde el archivo como `generate-networkpolicy.yaml`. Este ejemplo solo se activa para un Namespace llamado `policy-lab` que tenga `training.example.com/managed: "true"`. Para un objeto Namespace, haga la coincidencia con su **nombre/etiquetas**, no con `metadata.namespace` ni con una lista heredada de exclusión de espacios de nombres.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-networkpolicy
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("networking.k8s.io/v1"),
        "kind": dyn("NetworkPolicy"),
        "metadata": dyn({"name": "lab-default-deny", "namespace": object.metadata.name}),
        "spec": dyn({"podSelector": {}, "policyTypes": ["Ingress", "Egress"]})
      }])
```

Prepare las reglas de permiso necesarias para DNS/API/aplicaciones antes de que las cargas de trabajo dependan de este espacio de nombres. El aislamiento de NetworkPolicy de Kubernetes requiere un CNI que lo aplique; otras políticas de permiso son aditivas y se debe tener en cuenta el comportamiento de host-network. Un manifiesto generado localmente no demuestra que se haya bloqueado el tráfico.

Aquí se desactivan la sincronización y generate-existing. Al instalar esta política, un Namespace que ya exista no se completará automáticamente: use un desencadenador coincidente posterior o revise explícitamente si se habilita generate-existing antes de cambiar esa configuración. Con la sincronización habilitada, el ciclo de vida de los recursos dependientes varía según se usen datos o una fuente de clonación, los cambios en el desencadenador y `orphanDownstreamOnPolicyDelete`; no es un mecanismo universal de copia de seguridad/reversión. Para compartir Secrets se necesita una lista de permitidos explícita para orígenes/destinos y una revisión de RBAC/ciclo de vida de credenciales, no una copia en todos los espacios de nombres nuevos.

### 4. Eliminación programada

`DeletingPolicy` usa `spec.schedule` y condiciones CEL; es independiente de la validación y no tiene un selector Audit en validationActions. El controlador de limpieza necesita permisos de eliminación explícitos. Prefiera una etiqueta acotada de espacio de nombres/objeto y un requisito claro de retención por antigüedad/estado, inspeccione los objetos seleccionados y pruebe la recuperación antes de habilitar una programación. El ejemplo opcional del cuestionario selecciona Pods completados y marcados; no significa «de más de 24 horas» y aquí no se ejecutó ninguna eliminación programada.

## Casos de uso de Kyverno en EKS

### Arquitectura de integración de EKS y Kyverno

El servidor de API de EKS invoca los webhooks de admisión coincidentes mediante la ruta de red/RBAC configurada en Kubernetes. La exportación a CloudWatch es una integración/recopilador independiente que requiere su propia configuración, IAM y retención; instalar Kyverno no envía automáticamente todos los PolicyReport a CloudWatch. Evite imprimir cargas útiles de admisión sin enmascarar, ya que pueden contener secretos.

### 1. Refuerzo de la seguridad

#### Impedir los contenedores privilegiados

Si falta `privileged`, se considera `false`. La comprobación cubre los contenedores normales, de inicialización y efímeros; la coincidencia declarada con `pods/ephemeralcontainers` sigue requiriendo pruebas de admisión/subrecurso en vivo en el entorno de destino.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, !c.?securityContext.privileged.orValue(false))
    message: Privileged normal, init and ephemeral containers are not allowed.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

#### Impedir la ejecución como usuario root

La política usa la anulación de cada contenedor o el valor predeterminado del Pod, exige un valor efectivo de runAsNonRoot y rechaza un UID efectivo explícito de 0. Esto valida la declaración; el comportamiento del kubelet/de la imagen sigue siendo relevante en tiempo de ejecución.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-non-root
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: variables.containers.all(c, c.?securityContext.runAsNonRoot.orValue(object.spec.?securityContext.runAsNonRoot.orValue(false))
      && c.?securityContext.runAsUser.orValue(object.spec.?securityContext.runAsUser.orValue(-1)) != 0)
    message: Use effective runAsNonRoot=true and do not select UID 0.
  variables:
  - name: containers
    expression: object.spec.containers + object.spec.?initContainers.orValue([]) + object.spec.?ephemeralContainers.orValue([])
```

### 2. Optimización de costos

#### Definir límites de recursos

Guarde el archivo como `default-resources.yaml`. Este ejemplo, que solo se aplica a CREATE, evita cambiar los recursos de Pods en ejecución durante una actualización normal y proporciona valores predeterminados solo cuando un contenedor normal **no tiene solicitudes ni límites**. Conserva los ajustes de recursos existentes, completos o parciales, en lugar de sobrescribir el dimensionamiento de la carga de trabajo o generar una solicitud superior a un límite pequeño existente. Revise por separado los ajustes parciales; esta política no rellena todos los campos que falten ni establece valores predeterminados para los recursos de contenedores de inicialización/efímeros.

```yaml
apiVersion: policies.kyverno.io/v1
kind: MutatingPolicy
metadata:
  name: default-unset-resources
spec:
  evaluation:
    mutateExisting:
      enabled: false
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  mutations:
  - patchType: ApplyConfiguration
    applyConfiguration:
      expression: |-
        Object{spec: Object.spec{containers: object.spec.containers.map(c,
          (!has(c.resources) || ((!has(c.resources.requests) || c.resources.requests.size() == 0) &&
            (!has(c.resources.limits) || c.resources.limits.size() == 0)))
          ? Object.spec.containers{name: c.name, resources: Object.spec.containers.resources{
              requests: {"cpu": "250m", "memory": "256Mi"},
              limits: {"cpu": "500m", "memory": "512Mi"}
            }}
          : Object.spec.containers{name: c.name}
        )}}
```

#### Aplicar tipos de instancia específicos

Los nombres de instancia originales son una lista de permitidos ilustrativa, no una recomendación actual. Un nodeSelector explícito es una restricción de programación obligatoria. Esta política de admisión, solo para CREATE, rechaza un nodeName proporcionado; el análisis en segundo plano está desactivado porque los Pods programados adquieren legítimamente un nodeName. La confianza en las etiquetas de los nodos, los permisos de programación/vinculación y la capacidad disponible son cuestiones independientes. Una comprobación de declaraciones no puede garantizar la ubicación frente a una entidad principal con permiso para vincular Pods o modificar Nodes.

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: approved-node-selector
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.spec.?nodeName.orValue('') == '' && object.spec.?nodeSelector['node.kubernetes.io/instance-type'].orValue('')
      in ['m5.large', 'c5.large', 'r5.large']
    message: Use an approved instance-type nodeSelector and do not bypass the scheduler with nodeName.
  evaluation:
    background:
      enabled: false
```

### 3. Cumplimiento normativo

#### Generación automática de PodDisruptionBudget

Este ejemplo opcional de Deployment exige al menos dos réplicas deseadas y copia **todo el spec.selector**, incluidos matchExpressions, en lugar de una etiqueta app de nivel superior que podría no existir. No demuestra que haya dos réplicas en estado Ready. Este presupuesto estático de laboratorio requiere una decisión independiente sobre quién lo administra y lo revisa tras cambiar la escala o el selector, especialmente con la sincronización desactivada. Los PDB restringen las expulsiones voluntarias que cumplen los requisitos, pero no todos los rollouts ni los fallos involuntarios.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-pdb
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - apps
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - deployments
  matchConditions:
  - name: approved-deployment
    expression: object.metadata.namespace == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true' && object.spec.?replicas.orValue(1) >= 2
  generate:
  - expression: |-
      generator.Apply(object.metadata.namespace, [{
        "apiVersion": dyn("policy/v1"), "kind": dyn("PodDisruptionBudget"),
        "metadata": dyn({"name": object.metadata.name + "-pdb", "namespace": object.metadata.namespace}),
        "spec": dyn({"minAvailable": 1, "selector": object.spec.selector})
      }])
```

El controlador en segundo plano necesita permisos reales para crear el recurso generado. Para la versión renderizada de `kyverno`, este Role/Binding adicional del espacio de nombres ilustra una concesión acotada para PDB. El chart ya incluye otros permisos de controlador; no describa esto como la política RBAC efectiva completa del controlador. Ajuste los nombres de ServiceAccount según el renderizado y compruebe la autorización en el clúster de destino.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
rules:
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: kyverno-lab-pdb-writer
  namespace: policy-lab
subjects:
- kind: ServiceAccount
  name: kyverno-background-controller
  namespace: kyverno
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: kyverno-lab-pdb-writer
```

#### Generación automática de ResourceQuota para espacios de nombres

Se aplica la misma opción explícita para Namespace. Los valores de cuota son una política de laboratorio, no un presupuesto de AWS ni un límite de costos; antes de habilitarla, tenga en cuenta las solicitudes de las cargas de trabajo, los contenedores de inicialización, los límites y las cuotas existentes.

```yaml
apiVersion: policies.kyverno.io/v1
kind: GeneratingPolicy
metadata:
  name: generate-lab-quota
spec:
  evaluation:
    synchronize:
      enabled: false
    generateExisting:
      enabled: false
    orphanDownstreamOnPolicyDelete:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - namespaces
  matchConditions:
  - name: approved-lab-namespace
    expression: object.metadata.name == 'policy-lab' && object.metadata.?labels['training.example.com/managed'].orValue('')
      == 'true'
  generate:
  - expression: |-
      generator.Apply(object.metadata.name, [{
        "apiVersion": dyn("v1"), "kind": dyn("ResourceQuota"),
        "metadata": dyn({"name": "lab-resource-quota", "namespace": object.metadata.name}),
        "spec": dyn({"hard": {"requests.cpu": "10", "requests.memory": "10Gi",
          "limits.cpu": "20", "limits.memory": "20Gi", "pods": "50"}})
      }])
```

## Pruebas y validación de políticas

### Flujo de trabajo para aplicar políticas

Revise quién administra las políticas y su alcance; pruebe localmente casos positivos, negativos y omitidos; inspeccione los objetos generados/modificados y, luego, prepare por etapas la admisión activa y los permisos de los controladores. Audit es una acción de validación; no hace que la mutación, la generación o la eliminación sean inocuas. La autogeneración de controladores de Pod y la generación nativa de ValidatingAdmissionPolicy/MutatingAdmissionPolicy son opciones independientes con límites de compatibilidad; inspeccione el estado de la política generada en lugar de suponer que se cubren todas las plantillas de controladores.

### Simulación de políticas

Cree `policy-lab-tests/` y guarde allí los cuatro archivos siguientes. La prueba espera intencionadamente una infracción para `missing-label`; que el conjunto de pruebas pase significa que se cumplieron las expectativas, no que todas las entradas cumplieran las reglas.

`require-team.yaml`:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-team
spec:
  validationActions:
  - Audit
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-lab'
  validations:
  - expression: object.metadata.?labels.team.orValue('') != ''
    message: A nonempty team label is required.
```

`pod.yaml` (un recurso de prueba local; no se descarga su imagen):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: good
  namespace: policy-lab
  labels:
    team: platform
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`pod-missing.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: missing-label
  namespace: policy-lab
spec:
  containers:
  - name: app
    image: registry.example.com/app:fixture
```

`kyverno-test.yaml`:

```yaml
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata:
  name: team-label-local-test
policies:
- require-team.yaml
resources:
- pod.yaml
- pod-missing.yaml
results:
- policy: require-team
  kind: Pod
  resources:
  - good
  result: pass
- policy: require-team
  kind: Pod
  resources:
  - missing-label
  result: fail
```

```bash
kyverno version
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
# Offline evaluation; this does not install a policy or modify cluster resources:
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
# For mutation/generation, --output takes a file/directory path, not a format name:
kyverno apply add-default-label.yaml --resource ./policy-lab-tests/pod.yaml --output ./mutated/
```

### Validación de políticas

`kyverno test` recibe un directorio con un manifiesto de prueba; `kyverno apply` evalúa la política con los recursos proporcionados. `--cluster` lee recursos del clúster seleccionado para evaluarlos; no es un comando para instalar políticas. La instalación de una política revisada se realiza con kubectl/GitOps y modifica el clúster. Consulte la ayuda del CLI fijado a una versión: un flujo de trabajo genérico `kyverno validate` o `kyverno create disallow-latest-tag` no es la interfaz probada. `create` sí existe para los recursos auxiliares de Kyverno compatibles.

## Supervisión e informes de políticas

### Informes de políticas

La configuración predeterminada usa las API `PolicyReport`/`ClusterPolicyReport` del grupo de trabajo de políticas (Policy WG). Un PolicyReport pertenece a un espacio de nombres; ClusterPolicyReport abarca recursos con ámbito de clúster, no simplemente la combinación de todos los espacios de nombres. La configuración de informes y los tipos de reglas compatibles son importantes. Los análisis en segundo plano informan de resultados de validación; no rechazan, modifican ni eliminan retroactivamente objetos existentes. Los objetos existentes siguen sujetos a las comprobaciones de admisión coincidentes cuando se actualizan, aunque el análisis en segundo plano esté desactivado.

Este es un **ejemplo de esquema sintético**, no un informe recopilado de un clúster. Los resultados usan `resources` y `result`, no `resource`/`status`; si se proporciona una marca de tiempo, usa segundos/nanosegundos enteros. Los recuentos del resumen deben coincidir con las entradas.

```yaml
apiVersion: wgpolicyk8s.io/v1alpha2
kind: PolicyReport
metadata:
  name: example-report
  namespace: policy-lab
summary:
  pass: 1
  fail: 1
  warn: 0
  error: 0
  skip: 0
results:
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: good
    namespace: policy-lab
  result: pass
- policy: require-team
  source: kyverno
  resources:
  - apiVersion: v1
    kind: Pod
    name: missing-label
    namespace: policy-lab
  result: fail
  message: A nonempty team label is required.
```

Consulte los informes reales con `kubectl get policyreports -n policy-lab` y `kubectl get clusterpolicyreports`. Reports Server/OpenReports son instalaciones/configuraciones opcionales e independientes; verifique que la API esté realmente instalada antes de dar por hecho que el backend existe.

### Métricas de Prometheus

Use los Services de métricas creados por el chart y los ServiceMonitors por controlador de los valores probados anteriormente. El nombre del puerto Service es `metrics-port`, en 8000, con selectores de componente/instancia/parte, no `app: kyverno`. El renderizado los coloca en `kyverno` y configura `namespaceSelector.matchNames: [kyverno]`. Prometheus debe seleccionar esos monitores y el espacio de nombres. La existencia de los recursos no demuestra que se estén recopilando métricas ni exportando a CloudWatch.

## Prácticas recomendadas

### 1. Despliegue gradual

Introduzca las nuevas validaciones por etapas con Audit, revise los informes y las excepciones reales y, luego, elija Deny cuando corresponda. Compruebe la política de errores del webhook, el tiempo de espera, la disponibilidad de réplicas y el procedimiento de recuperación de emergencia. Revise por separado la generación, mutate-existing y la eliminación destructiva.

### 2. Gestión de excepciones

Unos matchConstraints/matchConditions acotados no equivalen a una exención ilimitada. Revise el alcance del espacio de nombres, los nombres, los tipos y la disponibilidad de la información de admisión/usuario. No se puede suponer que las reglas clásicas que dependen de información de usuario/rol puedan evaluarse en análisis en segundo plano. CEL PolicyException usa `policies.kyverno.io/v1`, policyRefs/matchConditions explícitos y, de forma opcional, expiresAt; restrinja quién puede crearlas y verifique que la instalación/configuración las admita. Una excepción es un objeto sensible para la autorización, no un mecanismo para omitir la admisión que deba recibir cualquier equipo de aplicaciones.

### 3. Organización de políticas

Mantenga políticas de validación, mutación, generación y eliminación con versiones, pruebas y responsables definidos. Los patrones/JMESPath de ClusterPolicy heredados difieren de CEL; migre regla por regla y compare los resultados. La verificación de firmas de imágenes se implementa con `ImageValidatingPolicy` en la API actual; consulte la [guía de seguridad de imágenes](./07-image-security.md) para conocer los requisitos previos de atestadores/registro/confianza. La verificación de firmas no es un análisis de vulnerabilidades ni una lista general de registros permitidos.

## Conclusión

La validación local cubrió la evaluación real de políticas con Kyverno 1.19.1 y la conservación de la salida, los esquemas de API publicados y el renderizado del chart. No se ejecutaron el orden de los webhooks activos/autogeneración, el RBAC de los controladores, las redes, la confianza en las imágenes ni las acciones destructivas del ciclo de vida. Estos siguen siendo controles de aceptación del despliegue.

- [Versiones de Kyverno y versiones probadas de Kubernetes](https://kyverno.io/docs/installation/releases/)
- [Instalación y responsabilidades de los controladores](https://kyverno.io/docs/installation/installation/)
- [Migración a CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [CLI de Kyverno](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## Cuestionario

Pruebe el [cuestionario sobre gestión de políticas con Kyverno](../quizzes/security/01-kyverno-policy-management-quiz.md).
