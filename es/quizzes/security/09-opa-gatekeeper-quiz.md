# Cuestionario de OPA Gatekeeper

> **Última actualización**: September 13, 2026

Pon a prueba tu comprensión de OPA Gatekeeper y del lenguaje de políticas Rego con las siguientes preguntas.

***

## Preguntas

### 1. ¿Qué lenguaje se usa para escribir políticas en OPA Gatekeeper?

* A) YAML
* B) JSON
* C) Rego
* D) HCL

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Rego**

**Explicación:** OPA (Open Policy Agent) usa un lenguaje declarativo de políticas llamado Rego. Rego está optimizado para consultar datos JSON/YAML y tomar decisiones de políticas.

```rego
package docsrequiredlabels
valid_label(key) if {
  value := input.review.object.metadata.labels[key]
  is_string(value)
  value != ""
}
violation contains {"msg": sprintf("required nonempty label: %v", [key])} if {
  some key in input.parameters.labels
  not valid_label(key)
}
```

Aprende los conjuntos, las comprensiones y los contratos de entrada de Rego; después, selecciona un motor de políticas según tus requisitos y pruebas.

</details>

***

### 2. ¿Qué CRD define plantillas de políticas reutilizables en Gatekeeper?

* A) Policy
* B) ConstraintTemplate
* C) PolicyTemplate
* D) GatekeeperPolicy

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) ConstraintTemplate**

**Explicación:** ConstraintTemplate define la lógica de políticas Rego y el esquema de parámetros:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: docsrequiredlabels
spec:
  crd:
    spec:
      names:
        kind: DocsRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              minItems: 1
              items:
                type: string
                minLength: 1
          required:
          - labels
  targets:
  - target: admission.k8s.gatekeeper.sh
    code:
    - engine: Rego
      source:
        version: v1
        rego: |
          package docsrequiredlabels
          valid_label(key) if {
            value := input.review.object.metadata.labels[key]
            is_string(value)
            value != ""
          }
          violation contains {"msg": sprintf("required nonempty label: %v", [key])} if {
            some key in input.parameters.labels
            not valid_label(key)
          }
```

Los Constraints se crean a partir de ConstraintTemplates para aplicar las políticas reales.

</details>

***

### 3. ¿Qué valor NO es compatible con el campo enforcementAction de un Constraint de Gatekeeper?

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) audit**

**Explicación:** Valores enforcementAction compatibles de Gatekeeper:

* **deny**: Rechaza la solicitud ante una infracción de política
* **dryrun**: Registra la infracción, pero permite la solicitud
* **warn**: Muestra un mensaje de advertencia y permite la solicitud

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: DocsRequiredLabels
metadata:
  name: required-labels
spec:
  enforcementAction: deny
  match:
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
    namespaces:
    - policy-lab
  parameters:
    labels:
    - app.kubernetes.io/name
```

audit no es una enforcementAction, sino la función de auditoría en segundo plano de Gatekeeper.

</details>

***

### 4. ¿Cuál es la sintaxis para iterar por todos los elementos de un array en Rego?

* A) for item in array
* B) array.forEach(item)
* C) item := array\[\_]
* D) loop array as item

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) item := array\[\_]**

**Explicación:** En Rego, `[_]` significa todos los índices de un array:

```rego
# Iterate all containers
container := input.review.object.spec.containers[_]

# Iterate all label keys
key := object.keys(input.review.object.metadata.labels)[_]

# Specific index
first_container := input.review.object.spec.containers[0]

# When both index and value are needed
some i
container := input.review.object.spec.containers[i]
```

Esta sintaxis es un patrón fundamental de Rego que se usa al evaluar varios valores dentro de reglas.

</details>

***

### 5. ¿Qué función de Gatekeeper comprueba el cumplimiento de políticas de los recursos existentes del clúster?

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Audit**

**Explicación:** Función Audit de Gatekeeper:

* Inspecciona periódicamente los recursos existentes
* Registra las infracciones en el estado del Constraint
* Valida los recursos existentes, no solo los nuevos

```bash
# Check violations in Constraint
kubectl describe docsrequiredlabels required-labels

# Check violations in Status section:
# Status:
#   Audit Timestamp: 2026-02-21T10:00:00Z
#   Total Violations: 3
#   Violations:
#     - Kind: Pod
#       Name: nginx-without-labels
#       Namespace: default
```

Esto permite comprender el impacto antes de aplicar las políticas.

</details>

***

<span id="_6-what-crd-is-used-for-automatic-resource-modification-in-gatekeeper-v3-10"></span>

### 6. ¿Qué CRD se usa para la modificación automática de recursos en Gatekeeper 3.23.1?

* A) MutatingPolicy
* B) Assign / AssignMetadata
* C) ModifyResource
* D) ResourceMutator

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Assign / AssignMetadata**

**Explicación:** CRD de Mutation de Gatekeeper:

* **AssignMetadata**: Agrega metadatos (labels, annotations)
* **Assign**: Modifica campos generales como spec
* **ModifySet**: Agrega o elimina valores de arrays

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: AssignMetadata
metadata:
  name: add-owner-label
spec:
  match:
    scope: Namespaced
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
  location: "metadata.labels.owner"
  parameters:
    assign:
      value: "platform-team"
```

Similar a la función mutate de Kyverno.

</details>

***

### 7. ¿Qué operador calcula la diferencia entre dos conjuntos en Rego?

* A) difference()
* B) subtract()
* C) - (menos)
* D) diff()

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) - (menos)**

**Explicación:** Operaciones de conjuntos de Rego:

```rego
# Compare required and existing labels
required := {"app", "env", "team"}
provided := {"app", "team"}

# Set difference: find missing labels
missing := required - provided
# Result: {"env"}

# Intersection
common := required & provided
# Result: {"app", "team"}

# Union
all := required | provided
```

Estas operaciones se usan frecuentemente para la validación de labels requeridos.

</details>

***

### 8. ¿Qué configuración se necesita en Gatekeeper para hacer referencia a recursos de otros namespaces?

* A) CrossNamespacePolicy
* B) Config's sync.syncOnly
* C) GlobalConstraint
* D) NamespaceSelector

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Config's sync.syncOnly**

**Explicación:** Este ejemplo sincroniza objetos de Kubernetes en el inventario; no se conecta automáticamente a un proveedor HTTP externo ni a un bundle arbitrario:

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
      - group: ""
        version: "v1"
        kind: "Namespace"
      - group: "networking.k8s.io"
        version: "v1"
        kind: "Ingress"
```

Se puede acceder a los recursos sincronizados en Rego mediante `data.inventory`:

```rego
other_ingress := data.inventory.namespace[ns]["networking.k8s.io/v1"]["Ingress"][name]
```

</details>

***

### 9. ¿Cuál es la herramienta CLI oficial para probar políticas de Gatekeeper?

* A) opa test
* B) gatekeeper-cli
* C) gator
* D) conftest

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) gator**

**Explicación:** Gator es la herramienta CLI oficial para probar localmente políticas de Gatekeeper:

```bash
# Install
gator version  # verified 3.23.1 release binary

# Validate policies
gator verify tests/suite.yaml --verbose

# Run test suite
gator test -f templates/ -f constraints/ -f tests/fixtures/labels-present.yaml --output=json
```

Ejemplo de suite de pruebas:

```yaml
apiVersion: test.gatekeeper.sh/v1alpha1
kind: Suite
metadata:
  name: docs-gatekeeper
tests:
- name: required-labels
  template: ../templates/docsrequiredlabels.yaml
  constraint: ../constraints/required-labels.yaml
  cases:
  - name: labels-present
    object: fixtures/labels-present.yaml
    assertions:
    - violations: 0
  - name: labels-absent
    object: fixtures/labels-absent.yaml
    assertions:
    - violations: 1
```

</details>

***

<span id="_10-what-is-gatekeeper-s-advantage-when-comparing-gatekeeper-and-kyverno"></span>

### 10. ¿Qué requisito concreto puede motivar la elección de una política Rego?

* A) Uso de memoria inferior garantizado para cada política
* B) Generar automáticamente cada recurso sin comprobaciones
* C) Gestionar siempre una lógica más compleja que otro motor
* D) Aplicar operaciones de conjuntos y comprensiones a entradas JSON y validarlas con pruebas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Aplicar operaciones de conjuntos y comprensiones a entradas JSON y validarlas con pruebas**

**Explicación:** Rego proporciona operaciones declarativas para este requisito. Compara la expresión de política real, las habilidades del equipo, las pruebas y las necesidades operativas, en lugar de afirmar una superioridad universal de rendimiento o complejidad.

</details>

***

### 11. Cuando se definen varias reglas de infracción en Rego, ¿cómo se evalúan?

* A) Solo se evalúa la primera regla
* B) Todas las reglas se evalúan como OR
* C) Todas las reglas se evalúan como AND
* D) Se selecciona una al azar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Todas las reglas se evalúan como OR**

**Explicación:** Varias definiciones de esta regla de infracción de conjunto parcial aportan sus resultados al mismo conjunto:

```rego
package examples
violation contains {"msg": "Privileged container"} if {
  container := input.review.object.spec.containers[_]
  container.securityContext.privileged == true
}
violation contains {"msg": "Explicit root user"} if {
  container := input.review.object.spec.containers[_]
  container.securityContext.runAsUser == 0
}
```

Los resultados de cada regla de infracción se agregan a un conjunto y, si hay una o más infracciones, la política general falla.

Estas reglas de infracción de conjunto parcial aportan al mismo conjunto. Las condiciones dentro de cada cuerpo son AND; las reglas de documento completo en conflicto no se resuelven mediante OR. Este fragmento no es una implementación completa de PSS.

</details>

***

### 12. ¿Qué campo de Gatekeeper configura un Constraint para que se aplique solo a namespaces específicos?

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.match.namespaces**

**Explicación:** La sección match de un Constraint especifica el ámbito de aplicación:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: DocsRequiredLabels
metadata:
  name: required-labels
spec:
  enforcementAction: deny
  match:
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
    namespaces:
    - production
    - staging
  parameters:
    labels:
    - app.kubernetes.io/name
```

* `namespaces`: Lista de namespaces que se incluirán
* `excludedNamespaces`: Lista de namespaces que se excluirán
* `namespaceSelector`: Selección basada en labels

</details>

***

## Cálculo de puntuación

Calcula 1 punto por pregunta.

| Puntuación | Calificación                                           |
| ----- | ------------------------------------------------------- |
| 11-12 | Excelente - nivel de experto en OPA Gatekeeper          |
| 8-10  | Bueno - conceptos básicos comprendidos; se necesita profundizar en Rego |
| 5-7   | Promedio - se recomienda estudio adicional              |
| 0-4   | Se necesita aprendizaje básico                          |

***

## Documentación relacionada

* [OPA Gatekeeper](../../security/09-opa-gatekeeper.md)
* [Gestión de políticas de Kyverno](01-kyverno-policy-management-quiz.md)
* [Estándares de seguridad de Pod](03-pod-security-standards-quiz.md)
