# Gestión de políticas con Kyverno

> **Línea de base de validación**: Kyverno/CLI 1.19.1, chart de Helm 3.9.1. La guía de la versión actual enumera Kubernetes 1.33–1.35 como versiones probadas; la restricción de instalación más amplia del chart no es una garantía de compatibilidad.
> **Última actualización**: September 13, 2026

Kyverno evalúa políticas de Kubernetes y realiza mutación, generación y eliminación configuradas explícitamente. Estos ejemplos se verificaron localmente con la CLI real y los esquemas/charts publicados. No se ejecutó ninguna instalación en un cluster en vivo, admisión, aislamiento de red, limpieza ni integración con AWS.

Los ejemplos originales de `ClusterPolicy` se actualizaron a políticas CEL de `policies.kyverno.io/v1`. La guía oficial de migración de la versión 1.19 desaconseja ClusterPolicy/Policy, CleanupPolicy y el PolicyException heredado de `kyverno.io`, cuya eliminación está prevista para 1.20. No están ya ausentes en 1.19; migre y pruebe antes de actualizar, en lugar de simplemente reemplazar una cadena apiVersion.

## Configuración del entorno de laboratorio

### Herramientas necesarias

Use kubectl con la desviación de versión compatible con el API server de destino, una versión compatible de Helm con capacidad OCI y la CLI verificada de Kyverno 1.19.1 para estas pruebas locales. Obtenga el archivo para el OS/arquitectura correspondiente de la CLI y verifique su checksum/firma publicados. No reutilice un archivo 1.10.0 ni redirija una descarga no verificada a una instalación root.

Comience con archivos locales. Las políticas siguientes son ejemplos independientes, no un conjunto que deba aplicar íntegramente. Los ejemplos de Pod se dirigen a `policy-lab`; la generación requiere además una etiqueta explícita. Restrinja quién puede cambiar estas políticas, etiquetas de namespace, Roles y PolicyExceptions. Esos selectores no son por sí mismos un límite de seguridad de RBAC.

### Instalación de Kyverno

Prepare un namespace dedicado `kyverno`. Verifique la versión de EKS/Kubernetes elegida, la conectividad del API server a los webhooks, DNS, el comportamiento de fallos/timeouts de admisión y el procedimiento de actualización de CRD antes de cambiar un cluster compartido. Los ServiceAccounts/RBAC de Kubernetes autorizan los controllers; instalar Kyverno no requiere por sí solo un rol de administrador de AWS.

## Introducción a Kyverno

### Arquitectura de Kyverno y cómo funciona

| Componente | Responsabilidad |
|---|---|
| Controller de admisión | Solicitudes de admisión coincidentes y validación/mutación/verificaciones de imágenes de políticas; no todas las solicitudes GET/list |
| Controller en segundo plano | Trabajo de generación y mutate-existing habilitado explícitamente |
| Controller de informes | Agregación/elaboración de informes de resultados de políticas |
| Controller de limpieza | Políticas de eliminación programada y operaciones de limpieza permitidas |

Una política de validación no elimina ni repara recursos no conformes existentes. Los informes en segundo plano, mutate-existing, generate-existing y la eliminación programada son mecanismos independientes con permisos distintos. La generación puede ser asíncrona; la creación de namespace y la aplicación de NetworkPolicy generada no son una operación atómica.

### Kyverno frente a OPA Gatekeeper

Las políticas actuales de Kyverno usan CEL en manifiestos YAML/JSON; las políticas heredadas también usan patrones y JMESPath. El empaquetado nativo de Kubernetes no elimina la necesidad de aprender expresiones de políticas. Gatekeeper utiliza ConstraintTemplates/Constraints y motores de políticas compatibles con su versión, con capacidades independientes de admisión/auditoría/mutación. Compare las características necesarias, los lenguajes de expresión, las pruebas de políticas, la disponibilidad de controllers y el impacto medido en las cargas de trabajo. Las antiguas calificaciones de «fácil/complejo» y «buen/muy buen rendimiento» eran comparaciones sin respaldo, no benchmarks.

## Instalación de Kyverno

### Instalación mediante Helm

Guarde esto como `kyverno-values.yaml`. Es un perfil de **laboratorio** de una sola réplica. Los CRD de ServiceMonitor y una instalación de Prometheus que seleccione el namespace/las etiquetas reales ya deben existir; reemplace la etiqueta de ejemplo `release: kube-prom` por el selector de esa instalación o deshabilite los ServiceMonitors hasta estar preparado.

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

El render contiene cuatro Deployments de controller y cuatro ServiceMonitors de métricas. Más réplicas requieren planificación de topología, interrupciones, dimensionamiento de recursos y disponibilidad de webhooks; una réplica por controller no es un diseño HA. Inspeccione los valores predeterminados del chart actual y las etiquetas de imagen renderizadas reales, en lugar de interpretar la etiqueta de versión de un chart como la versión de la aplicación.

### Instalación mediante manifiestos YAML

Si GitOps administra YAML, renderice el chart fijado y revise sus CRD, RBAC, certificados y hooks como un conjunto administrado. Un `kubectl apply` sin procesar de un render no ejecuta la semántica de hook/actualización de Helm. No aplique el antiguo install.yaml 1.10.0 sobre una versión más reciente ni mezcle varios propietarios para los mismos controllers.

## Tipos de políticas

### 1. Políticas de validación

Guarde este ejemplo independiente como `require-limits.yaml`. Comprueba que los containers **normales e init** tengan límites de CPU/memoria no vacíos. Los containers efímeros no pueden declarar requests/limits de recursos; las verificaciones de seguridad a continuación los cubren por separado. Esta es una política elegida por container, no una afirmación de que cada carga de trabajo de Kubernetes deba usar esta estrategia de recursos.

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

`validationActions: [Audit]` registra infracciones mientras permite las solicitudes de admisión coincidentes; `[Deny]` las rechaza tras la preparación/revisión de impacto. `Warn` puede proporcionar advertencias al cliente. El `failurePolicy` de webhook gobierna los fallos de evaluación/transporte y es una configuración diferente. Los resultados de fallo de la CLI offline no demuestran que una política Audit haya denegado una solicitud en vivo.

### 2. Políticas de mutación

Guarde como `add-default-label.yaml`. Se preservan las etiquetas `environment` existentes, incluidos los valores explícitamente vacíos. Esto usa CEL ApplyConfiguration, no la sintaxis de plantilla Go de Helm `if`/`hasKey` dentro de Kyverno.

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

El ejemplo deshabilita mutate-existing. La mutación de admisión aún puede afectar solicitudes CREATE/UPDATE coincidentes. Una alternativa JSONPatch debe crear un mapa de etiquetas faltante antes de agregar una clave secundaria y escapar `/` como `~1` en las rutas JSON Pointer. El orden de mutación no está garantizado entre políticas independientes.

### 3. Políticas de generación

Guarde como `generate-networkpolicy.yaml`. Solo un Namespace llamado `policy-lab` con `training.example.com/managed: "true"` activa este ejemplo. Para un objeto Namespace, haga coincidir su **nombre/etiquetas**, no `metadata.namespace` ni una lista de exclusión de namespace heredada.

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

Prepare las reglas necesarias de DNS/API/aplicación antes de que las cargas de trabajo dependan de este namespace. El aislamiento de Kubernetes NetworkPolicy necesita un CNI que lo aplique; otras políticas de allow son aditivas y se debe considerar el comportamiento de host-network. Un manifiesto generado localmente no demuestra que se haya bloqueado el tráfico.

La sincronización y generate-existing están deshabilitados aquí. Un Namespace ya existente no se completa automáticamente cuando se instala esta política: use después un trigger coincidente o revise explícitamente la habilitación de generate-existing antes de cambiar esa configuración. Con la sincronización habilitada, el ciclo de vida downstream depende de los datos frente a la fuente clone, de cambios en el trigger y de `orphanDownstreamOnPolicyDelete`; no es un mecanismo universal de copia de seguridad/reversión. Compartir Secrets requiere una lista de allow explícita de origen/destino y una revisión de RBAC/ciclo de vida de credenciales, no una copia en cada namespace nuevo.

### 4. Eliminación programada

`DeletingPolicy` usa `spec.schedule` y condiciones CEL; es independiente de la validación y no tiene un interruptor validationActions Audit. Un controller de limpieza necesita permisos explícitos de eliminación. Prefiera una etiqueta de namespace/objeto estrecha y un requisito claro de retención por antigüedad/estado, inspeccione los candidatos seleccionados y pruebe la recuperación antes de habilitar una programación. El ejemplo opcional del quiz selecciona Pods completados marcados; no significa «más de 24 horas», y aquí no se ejecutó ninguna eliminación programada.

## Casos de uso de Kyverno en EKS

### Arquitectura de integración de EKS y Kyverno

El API server de EKS invoca los webhooks de admisión coincidentes mediante la ruta de red/RBAC de Kubernetes configurada. La exportación a CloudWatch es un collector/integración configurado independiente con su propio IAM y retención; instalar Kyverno no envía automáticamente todos los PolicyReport a CloudWatch. Evite imprimir payloads de admisión sin procesar que puedan contener secretos.

### 1. Fortalecimiento de seguridad

#### Prevención de containers privilegiados

La ausencia de `privileged` se trata como false. La comprobación cubre containers normales, init y efímeros; la coincidencia declarada de `pods/ephemeralcontainers` aún requiere pruebas de admisión/subrecurso en vivo en el entorno de destino.

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

#### Prevención de la ejecución como usuario root

La política usa la anulación de cada container o el valor predeterminado a nivel de Pod, requiere un runAsNonRoot efectivo y rechaza un UID efectivo explícito de 0. Esto valida la declaración; el comportamiento de kubelet/la imagen sigue siendo relevante en tiempo de ejecución.

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

#### Configuración de límites de recursos

Guarde como `default-resources.yaml`. Este ejemplo solo de CREATE evita cambiar recursos de Pod en ejecución durante una actualización ordinaria y proporciona valores predeterminados solo cuando un container normal no tiene **requests ni limits**. Conserva la configuración de recursos existente completa y parcial en lugar de sobrescribir el dimensionamiento de la carga de trabajo o producir un request mayor que un límite pequeño existente. Revise las configuraciones parciales por separado; no completa todos los campos faltantes ni establece valores predeterminados para recursos init/efímeros.

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

#### Aplicación de tipos de instancia específicos

Los nombres de instancia originales son una lista de allow ilustrativa, no una recomendación actual. Un nodeSelector explícito es una restricción de programación obligatoria. Esta política CREATE solo de admisión rechaza un nodeName proporcionado; el escaneo en segundo plano está deshabilitado porque los Pods programados adquieren legítimamente nodeName. La confianza en las etiquetas de nodo, los permisos de scheduler/binding y la capacidad disponible es independiente. Una comprobación de declaración no puede garantizar la ubicación frente a una entidad a la que se permite vincular Pods o modificar Nodes.

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

### 3. Cumplimiento

#### Generación automática de PodDisruptionBudget

Este ejemplo opt-in de Deployment requiere al menos dos réplicas deseadas y copia el **spec.selector completo**, incluidos matchExpressions, en lugar de una etiqueta app de nivel superior que podría estar ausente. No prueba que dos réplicas estén Ready. Este presupuesto de laboratorio estático requiere una decisión independiente de propiedad/revisión después de cambios de escalado o selector, especialmente con la sincronización deshabilitada. Los PDB restringen las expulsiones voluntarias elegibles, no cada rollout ni fallo involuntario.

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

El controller en segundo plano necesita permiso real para crear el recurso generado. Para la versión renderizada de `kyverno`, este Role/Binding de namespace adicional ilustra una concesión PDB estrecha. El chart ya contiene otros permisos de controller; no considere esto la política RBAC efectiva completa del controller. Ajuste los nombres de ServiceAccount al render y verifique la autorización en el cluster de destino.

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

#### Generación automática de ResourceQuota de Namespace

Se aplica el mismo opt-in explícito de Namespace. Los valores de cuota son una política de laboratorio, no un presupuesto de AWS ni un tope de costos; tenga en cuenta los requests de la carga de trabajo, los containers init, los limits y las cuotas existentes antes de habilitarla.

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

### Flujo de trabajo de aplicación de políticas

Revise la propiedad y el alcance de la política, pruebe localmente casos positivos/negativos/omitidos, inspeccione los objetos generados/mutados y, luego, prepare la admisión en vivo y los permisos de los controllers. Audit es una acción de validación; no hace que la mutación, la generación ni la eliminación sean inocuas. La autogeneración de Pod-controller y la generación nativa de ValidatingAdmissionPolicy/MutatingAdmissionPolicy son opt-ins independientes con límites de compatibilidad; inspeccione el estado de la política generada en lugar de asumir que todas las plantillas de controller están cubiertas.

### Simulación de políticas

Cree `policy-lab-tests/` y guarde allí los cuatro archivos siguientes. La prueba espera intencionalmente una infracción para `missing-label`; una suite de pruebas aprobada significa que las expectativas coincidieron, no que cada entrada cumplió.

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

`pod.yaml` (un fixture local; su imagen no se descarga):

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

`kyverno test` toma un directorio con un manifiesto de prueba; `kyverno apply` evalúa la política frente a los recursos proporcionados. `--cluster` lee recursos del cluster seleccionado para la evaluación; no es un comando de instalación de políticas. Instalar una política revisada usa kubectl/GitOps y cambia el cluster. Consulte la ayuda de la CLI fijada: un flujo de trabajo genérico de `kyverno validate` o `kyverno create disallow-latest-tag` no es la interfaz probada. `create` existe para recursos auxiliares compatibles de Kyverno.

## Monitoreo e informes de políticas

### Informes de políticas

El perfil predeterminado utiliza las API `PolicyReport`/`ClusterPolicyReport` de Policy WG. Un PolicyReport tiene alcance de namespace; ClusterPolicyReport cubre recursos con alcance de cluster, no simplemente todos los namespaces combinados. La configuración de informes y los tipos de reglas compatibles importan. Los escaneos en segundo plano informan resultados de validación; no deniegan, mutan ni eliminan retroactivamente objetos existentes. Los objetos existentes siguen sujetos a comprobaciones de admisión coincidentes cuando se actualizan incluso si el escaneo en segundo plano está deshabilitado.

Este es un **ejemplo de esquema sintético**, no un informe recopilado de un cluster. Los resultados usan `resources` y `result`, no `resource`/`status`; si se proporciona una marca de tiempo, usa segundos/nanos enteros. Los recuentos del resumen deben coincidir con las entradas.

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

Consulte los informes reales con `kubectl get policyreports -n policy-lab` y `kubectl get clusterpolicyreports`. Reports Server/OpenReports son instalaciones/configuraciones opcionales independientes; verifique la API realmente instalada antes de asumir el backend.

### Métricas de Prometheus

Use los Services de métricas creados por el chart y los ServiceMonitors por controller de los valores probados anteriores. El nombre de puerto Service es `metrics-port` en 8000, con selectores de component/instance/part-of, no `app: kyverno`. El render los coloca en `kyverno` y configura `namespaceSelector.matchNames: [kyverno]`. Prometheus debe seleccionar esos monitors y el namespace. La existencia de recursos no prueba scraping ni exportación a CloudWatch.

## Mejores prácticas

### 1. Despliegue gradual

Prepare la nueva validación con Audit, revise informes y excepciones reales y, después, elija Deny cuando sea apropiado. Compruebe la política de fallo de webhook, el timeout, la disponibilidad de réplicas y la recuperación de emergencia. Mantenga separadas la revisión de generación, mutation-existing y eliminación destructiva.

### 2. Gestión de excepciones

Las matchConstraints/matchConditions estrechas no equivalen a una exención ilimitada. Revise el alcance de namespace, nombres, kinds y la disponibilidad de información de admisión/usuario. No se puede asumir que las reglas clásicas que dependen de información de usuario/rol sean evaluables en escaneos en segundo plano. CEL PolicyException utiliza `policies.kyverno.io/v1`, policyRefs/matchConditions explícitos y opcionalmente expiresAt; restrinja quién puede crearlo y verifique el soporte de instalación/configuración. Una excepción es un objeto sensible a la autorización, no una omisión de admisión que todo equipo de aplicaciones deba recibir.

### 3. Organización de políticas

Mantenga políticas versionadas de validación, mutación, generación y eliminación con pruebas y propietarios. Los patrones/JMESPath de ClusterPolicy heredado difieren de CEL; migre regla por regla con comparaciones de salida. La verificación de firma de imagen es `ImageValidatingPolicy` en la API actual; consulte la [guía de seguridad de imágenes](./07-image-security.md) para los requisitos previos de attestor/registry/trust. La verificación de firmas no es escaneo de vulnerabilidades ni una lista de allow general para registry.

## Conclusión

La validación local cubrió la evaluación de políticas y la preservación de salida de Kyverno 1.19.1 reales, los esquemas de API publicados y el renderizado de charts. No se ejecutaron el orden/autogeneración de webhook en vivo, el RBAC de controller, las redes, la confianza de imagen ni las acciones destructivas del ciclo de vida. Estos siguen siendo comprobaciones de aceptación de despliegue.

- [Versiones de Kyverno y versiones probadas de Kubernetes](https://kyverno.io/docs/installation/releases/)
- [Instalación y responsabilidades de los controllers](https://kyverno.io/docs/installation/installation/)
- [Migración a CEL](https://kyverno.io/docs/guides/migration-to-cel/)
- [ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [MutatingPolicy](https://kyverno.io/docs/policy-types/mutating-policy/)
- [GeneratingPolicy](https://kyverno.io/docs/policy-types/generating-policy/)
- [DeletingPolicy](https://kyverno.io/docs/policy-types/deleting-policy/)
- [CLI de Kyverno](https://kyverno.io/docs/kyverno-cli/reference/kyverno/)

## Quiz

Pruebe el [Quiz de gestión de políticas de Kyverno](../quizzes/security/01-kyverno-policy-management-quiz.md).
