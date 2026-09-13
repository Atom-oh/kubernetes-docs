# Cuestionario de gestión de políticas con Kyverno

> **Última actualización**: September 13, 2026

Estas preguntas utilizan las políticas CEL revisadas de Kyverno 1.19.1. Los ejemplos son fixtures locales; no se ejecutó ningún clúster ni ninguna limpieza destructiva.

## Preguntas del cuestionario

### 1. ¿Qué es Kyverno?

- A) Un motor de políticas de Kubernetes con controladores de admisión y controladores de background/ciclo de vida configurados por separado.
- B) Únicamente un escáner de vulnerabilidades.
- C) Un reemplazo de la autenticación del API server.
- D) Un dataplane de service mesh.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Un motor de políticas de Kubernetes con controladores de admisión y controladores de background/ciclo de vida configurados por separado.**

Las políticas de Kyverno validan, mutan, generan, verifican imágenes y eliminan dentro de los ámbitos que se les configuran. Las políticas v1 actuales usan CEL dentro de YAML/JSON; los patrones heredados de ClusterPolicy y JMESPath son lenguajes distintos. El empaquetado nativo de Kubernetes no elimina la necesidad de aprender las expresiones de política.

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

</details>

<span id="_2-which-of-the-following-is-not-a-policy-type-supported-by-kyverno"></span>

### 2. ¿Qué afirmación distingue correctamente las operaciones de política?

- A) Todas las políticas se ejecutan solo en la admisión y nunca modifican otros objetos.
- B) Audit convierte la generación y la eliminación en operaciones de solo lectura.
- C) Todas las solicitudes GET/list son interceptadas por los admission webhooks.
- D) La validación, la mutación, la generación y la eliminación programada tienen controladores, ajustes y permisos diferentes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) La validación, la mutación, la generación y la eliminación programada tienen controladores, ajustes y permisos diferentes.**

La autenticación de Kubernetes (por ejemplo, OIDC o tokens de ServiceAccount) y la autorización (RBAC) son independientes de la política de admisión; Authenticate no es una acción de política de Kyverno. DeletingPolicy usa una programación y condiciones; una regla de ClusterPolicy con cleanup.ttl no es su API. La mutación, la generación y la eliminación pueden modificar recursos incluso cuando una política de validación no relacionada está en Audit. Usa selectores explícitos de laboratorio, el RBAC necesario y una planificación de recuperación. La siguiente definición opcional de eliminación se muestra para comprender el esquema; no se aplicó y no implementa un umbral de antigüedad de 24 horas.

```yaml
apiVersion: policies.kyverno.io/v1
kind: DeletingPolicy
metadata:
  name: cleanup-lab-completed-pods
spec:
  schedule: 0 1 * * *
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      resources:
      - pods
      scope: Namespaced
    namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: policy-lab
  conditions:
  - name: explicitly-approved-completed
    expression: object.metadata.?labels['training.example.com/disposable'].orValue('') == 'true' && object.?status.phase.orValue('')
      in ['Succeeded', 'Failed']
```

</details>

### 3. ¿En qué se diferencian validationActions: [Audit] y [Deny] en una ValidatingPolicy actual?

- A) Ambos rechazan siempre una infracción coincidente.
- B) Audit permite las infracciones coincidentes para fines de informe; Deny las rechaza durante la admisión coincidente.
- C) Audit elimina los objetos infractores existentes.
- D) Deny reescribe el recurso automáticamente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Audit permite las infracciones coincidentes para fines de informe; Deny las rechaza durante la admisión coincidente.**

El failurePolicy del webhook se refiere a fallos de evaluación o de transporte y es algo aparte. Un resultado fail de la CLI local registra una infracción de política, no una prueba de que una política en Audit haya denegado una solicitud real. En la API heredada, las acciones de fallo Enforce/Audit tienen nombres de campo distintos; migra de forma deliberada.

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

</details>

<span id="_4-what-field-is-used-in-kyverno-to-select-which-resources-a-policy-applies-to"></span>

### 4. ¿Cómo se selecciona el ámbito de recursos de una ValidatingPolicy con CEL?

- A) Basta con una cadena target de nivel superior.
- B) Usando matchConstraints y matchConditions opcionales; se inspeccionan el kind, la operación, el namespace y la disponibilidad de los datos de la solicitud.
- C) Todas las políticas coinciden automáticamente con todos los recursos de Kubernetes.
- D) Usando metadata.name como único selector.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando matchConstraints y matchConditions opcionales; se inspeccionan el kind, la operación, el namespace y la disponibilidad de los datos de la solicitud.**

La ClusterPolicy clásica usa estructuras match/exclude en las reglas; no corresponden a la disposición actual de campos con CEL. Las condiciones de recurso y de usuario deben entenderse como expresiones, no como abreviaturas de OR/AND que se dan por supuestas. La información de usuario o de rol procedente de la admisión no siempre está disponible en los escaneos en background. Un selector de etiquetas de namespace también queda bajo el control de quien pueda cambiar esa etiqueta.

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

</details>

<span id="_5-which-policy-type-in-kyverno-automatically-modifies-resources-on-policy-violation"></span>

### 5. ¿Qué hace que esta mutación de valores predeterminados de recursos sea segura para los valores existentes?

- A) Sobrescribe todos los containers con límites idénticos.
- B) En CREATE, solo rellena los recursos de containers normales que están completamente sin definir y conserva los ajustes existentes, completos o parciales.
- C) Copia los valores del primer container a todos los demás containers.
- D) Usa sentencias if/hasKey de Helm dentro de una expresión de Kyverno.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En CREATE, solo rellena los recursos de containers normales que están completamente sin definir y conserva los ajustes existentes, completos o parciales.**

La salida real de la CLI se comparó con objetos de entrada completos y parcialmente configurados, y no presentó cambios. Los campos parciales requieren una revisión aparte; no crees un request superior a un límite pequeño ya existente. ApplyConfiguration y JSONPatch tienen semánticas diferentes; JSONPatch necesita una ruta padre existente, y el orden de ejecución de políticas independientes no está garantizado.

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

</details>

### 6. ¿Cuándo es útil una GeneratingPolicy?

- A) Para crear recursos derivados seleccionados explícitamente a partir de un disparador coincidente y con los permisos necesarios.
- B) Para respaldar automáticamente todos los recursos eliminados.
- C) Para garantizar el aislamiento de namespaces de forma atómica en el momento de la creación.
- D) Para eludir el RBAC del controlador de background.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Para crear recursos derivados seleccionados explícitamente a partir de un disparador coincidente y con los permisos necesarios.**

Este ejemplo de Deployment requiere una adhesión explícita (opt-in) y al menos dos réplicas deseadas, y copia por completo spec.selector. La generación puede ser asíncrona. La sincronización, las fuentes de datos frente a las de clonado, generate-existing y los ajustes de orphaning afectan al comportamiento de actualización y eliminación. No clones un Secret de registro en todos los namespaces nuevos sin un límite de origen/destino aprobado.

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

</details>

<span id="_7-what-policy-type-is-used-in-kyverno-to-verify-container-image-signatures"></span>

### 7. ¿Qué tipo actual de Kyverno verifica las firmas y las atestaciones de imágenes de contenedor?

- A) ResourceQuota.
- B) ImageValidatingPolicy.
- C) ServiceMonitor.
- D) LimitRange.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ImageValidatingPolicy.**

Las reglas heredadas verifyImages de ClusterPolicy son distintas del nuevo kind del manifiesto. Configura la ruta de confianza compatible de Cosign o de Notary/Notation, reglas precisas de firmante/emisor/clave y el acceso al registro tal como se describe en la guía de seguridad de imágenes. Material arbitrario de GPG o de Docker Content Trust no es un sustituto directo. La verificación no es un escaneo de vulnerabilidades ni constituye automáticamente una lista de permitidos de registros. La mutación de digest configurada puede cambiar la referencia de la imagen; en este capítulo no se ejecutó ninguna operación de registro ni de firma.

[Guía de seguridad de imágenes](../../security/07-image-security.md)

</details>

<span id="_8-what-does-the-background-false-setting-mean-in-a-kyverno-policy"></span>

### 8. ¿Qué significa deshabilitar el escaneo de validación en background?

- A) Los recursos existentes no se escanean periódicamente con ese ajuste de validación, pero las actualizaciones de admisión coincidentes se pueden seguir comprobando.
- B) Todos los recursos existentes quedan exentos permanentemente de la admisión.
- C) El ajuste detiene todos los controladores de Kyverno.
- D) Se eliminan las infracciones de política existentes.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Los recursos existentes no se escanean periódicamente con ese ajuste de validación, pero las actualizaciones de admisión coincidentes se pueden seguir comprobando.**

Para el tipo actual usa spec.evaluation.background.enabled; la ClusterPolicy clásica usaba background. Ninguno de los dos es un interruptor global para mutate-existing, la generación o la limpieza. El informe en background por sí mismo no repara, deniega ni elimina un recurso ya almacenado. Las operaciones de admisión y las condiciones de coincidencia siguen rigiendo las actualizaciones.

</details>

### 9. ¿Qué representación de PolicyReport es correcta?

- A) Un campo resource y un campo status con recuentos de resumen no relacionados con los resultados.
- B) Un PolicyReport con entradas resources/result y recuentos de resumen coherentes con esas entradas.
- C) Todo informe debe usar un timestamp.created de tipo cadena.
- D) ClusterPolicyReport significa una agregación arbitraria de todos los informes de namespace.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un PolicyReport con entradas resources/result y recuentos de resumen coherentes con esas entradas.**

El perfil predeterminado del chart usa los informes del Policy WG. PolicyReport está en un namespace y ClusterPolicyReport cubre los recursos de ámbito de clúster. Este es un ejemplo de esquema sintético, no evidencia recopilada en vivo. Un timestamp suministrado usa segundos y nanosegundos enteros. Otros backends de informes deben verificarse por separado.

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

</details>

<span id="_10-what-command-line-tool-can-be-used-to-test-policies-in-kyverno"></span>

### 10. ¿Cómo se deben probar localmente estas políticas de Kyverno?

- A) Ejecutando kyverno apply --cluster para instalar todas las políticas.
- B) Usando kyverno test con un directorio de manifiestos de prueba, o kyverno apply con archivos de recursos locales.
- C) Ejecutando el comando genérico inexistente kyverno validate.
- D) Un render correcto de Helm demuestra el comportamiento de las políticas y el RBAC.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando kyverno test con un directorio de manifiestos de prueba, o kyverno apply con archivos de recursos locales.**

La guía proporciona policy-lab-tests con entradas positivas y con fallos esperados. kyverno test --require-tests evita aceptar una carpeta de pruebas vacía. kyverno apply evalúa recursos; --cluster lee un clúster seleccionado para la evaluación y no es una instalación. --output recibe una ruta para los objetos mutados o generados. Existen subcomandos create para los helpers compatibles; no inventes un comando create disallow-latest-tag como plantilla.

```bash
kyverno test ./policy-lab-tests --require-tests --warnings-as-errors
kyverno apply ./policy-lab-tests/require-team.yaml \
  --resource ./policy-lab-tests/pod-missing.yaml \
  --continue-on-error=false --warn-no-pass --warn-exit-code 2
```

</details>

[Volver a la guía](../../security/01-kyverno-policy-management.md)
