# Cuestionario de OPA Gatekeeper

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

**Explicación:** OPA (Open Policy Agent) usa un lenguaje de políticas declarativo llamado Rego. Rego está optimizado para consultar datos JSON/YAML y tomar decisiones de políticas.

```rego
package kubernetes.admission

violation[{"msg": msg}] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}
```

A diferencia de Kyverno, necesitas aprender un lenguaje nuevo, pero permite expresar lógica de políticas más compleja.

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
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg}] {
            # Rego policy logic
        }
```

Las Constraints se crean basándose en ConstraintTemplates para aplicar políticas reales.

</details>

***

### 3. ¿Qué valor NO es compatible con el campo enforcementAction de una Gatekeeper Constraint?

* A) deny
* B) dryrun
* C) warn
* D) audit

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) audit**

**Explicación:** Valores de enforcementAction compatibles con Gatekeeper:

* **deny**: Rechaza la solicitud ante una infracción de política
* **dryrun**: Registra la infracción pero permite la solicitud
* **warn**: Muestra un mensaje de advertencia y permite la solicitud

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels
spec:
  enforcementAction: deny  # or dryrun, warn
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

audit no es un enforcementAction, sino la característica de auditoría en segundo plano de Gatekeeper.

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
container := input.request.object.spec.containers[_]

# Iterate all label keys
label := input.request.object.metadata.labels[_]

# Specific index
first_container := input.request.object.spec.containers[0]

# When both index and value are needed
some i
container := input.request.object.spec.containers[i]
```

Esta sintaxis es un patrón fundamental de Rego que se usa al evaluar múltiples valores dentro de reglas.

</details>

***

### 5. ¿Qué característica de Gatekeeper comprueba el cumplimiento de políticas de los recursos existentes del cluster?

* A) Validation
* B) Mutation
* C) Audit
* D) Generation

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Audit**

**Explicación:** Característica Audit de Gatekeeper:

* Inspecciona periódicamente los recursos existentes
* Registra las infracciones en el estado de la Constraint
* Valida los recursos existentes, no solo los nuevos

```bash
# Check violations in Constraint
kubectl describe k8srequiredlabels require-labels

# Check violations in Status section:
# Status:
#   Audit Timestamp: 2026-02-21T10:00:00Z
#   Total Violations: 3
#   Violations:
#     - Kind: Pod
#       Name: nginx-without-labels
#       Namespace: default
```

Esto permite comprender el impacto antes de aplicar políticas.

</details>

***

### 6. ¿Qué CRD se usa para la modificación automática de recursos en Gatekeeper v3.10+?

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

Similar a la característica mutate de Kyverno.

</details>

***

### 7. ¿Qué operador calcula la diferencia entre dos conjuntos en Rego?

* A) difference()
* B) subtract()
* C) - (minus)
* D) diff()

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) - (minus)**

**Explicación:** Operaciones de conjuntos en Rego:

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

Estas operaciones se usan con frecuencia para la validación de labels obligatorios.

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

**Explicación:** Para que Gatekeeper haga referencia a datos externos, se requiere una configuración de sincronización mediante el recurso Config:

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

**Explicación:** Gator es la herramienta CLI oficial para probar políticas de Gatekeeper localmente:

```bash
# Install
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# Validate policies
gator verify ./policies/

# Run test suite
gator test ./tests/
```

Ejemplo de test suite:

```yaml
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
metadata:
  name: required-labels-test
tests:
  - name: "Pod without labels should fail"
    template: ../templates/k8srequiredlabels.yaml
    constraint: ../constraints/require-labels.yaml
    cases:
      - name: pod-without-labels
        object: fixtures/pod-no-labels.yaml
        assertions:
          - violations: yes
```

</details>

***

### 10. ¿Cuál es la ventaja de Gatekeeper al comparar Gatekeeper y Kyverno?

* A) Menor curva de aprendizaje
* B) Políticas nativas de YAML
* C) Característica de generación de recursos
* D) Expresividad de lógica de políticas complejas

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) Expresividad de lógica de políticas complejas**

**Explicación:** Comparación entre Gatekeeper (OPA) y Kyverno:

| Característica      | Gatekeeper               | Kyverno       |
| ------------------- | ------------------------ | ------------- |
| Lenguaje de políticas | Rego                   | YAML          |
| Curva de aprendizaje | Alta                    | Baja          |
| Lógica compleja     | Muy flexible             | Limitada      |
| Generación de recursos | No compatible         | Compatible    |
| Datos externos      | Compatibilidad con OPA Bundle | API Call |

La flexibilidad de Gatekeeper con Rego facilita manejar:

* Combinaciones de condiciones complejas
* Procesamiento recursivo de estructuras de datos
* Operaciones avanzadas de conjuntos
* Integración de datos externos

</details>

***

### 11. Cuando se definen varias reglas de violation en Rego, ¿cómo se evalúan?

* A) Solo se evalúa la primera regla
* B) Todas las reglas se evalúan como OR
* C) Todas las reglas se evalúan como AND
* D) Se selecciona una al azar

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Todas las reglas se evalúan como OR**

**Explicación:** En Rego, varias reglas con el mismo nombre se evalúan como OR:

```rego
# Rule 1: Check privileged containers
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged == true
    msg := "Privileged containers not allowed"
}

# Rule 2: Check root execution
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    container.securityContext.runAsUser == 0
    msg := "Running as root not allowed"
}

# Violation occurs if either rule is violated
```

Los resultados de cada regla de violation se agregan a un conjunto, y si hay una o más infracciones, la política general falla.

</details>

***

### 12. ¿Qué campo de Gatekeeper configura una Constraint para aplicarse solo a namespaces específicos?

* A) spec.targetNamespaces
* B) spec.match.namespaces
* C) spec.scope.namespaces
* D) spec.selector.namespaces

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) spec.match.namespaces**

**Explicación:** La sección match de una Constraint especifica el alcance de aplicación:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-prod
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
      - staging
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
    namespaceSelector:
      matchLabels:
        environment: production
```

* `namespaces`: Lista de namespaces que se incluyen
* `excludedNamespaces`: Lista de namespaces que se excluyen
* `namespaceSelector`: Selección basada en labels

</details>

***

## Cálculo de puntuación

Calcula 1 punto por pregunta.

| Puntuación | Calificación                                           |
| ---------- | ------------------------------------------------------ |
| 11-12      | Excelente: nivel experto en OPA Gatekeeper             |
| 8-10       | Bueno: conceptos básicos comprendidos, se necesita profundizar en Rego |
| 5-7        | Promedio: se recomienda estudio adicional              |
| 0-4        | Se necesita aprendizaje básico                         |

***

## Documentación relacionada

* [OPA Gatekeeper](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/09-opa-gatekeeper.md)
* [Gestión de políticas de Kyverno](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/01-kyverno-policy-management.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
