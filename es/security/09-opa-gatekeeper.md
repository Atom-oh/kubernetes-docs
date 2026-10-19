# OPA Gatekeeper

> **Referencia de validación**: Gatekeeper/Gator 3.23.1 · Helm chart 3.23.1

> **Última actualización**: 13 de septiembre de 2026

## Descripción general

Gatekeeper evalúa políticas durante la admisión de Kubernetes y las auditorías periódicas. Los ConstraintTemplates definen la lógica y los esquemas de parámetros; los Constraints definen el alcance, los valores y enforcementAction. Los [ejemplos completos](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/gatekeeper) usan un namespace `policy-lab` dedicado y pruebas locales. No aplique cada fixture de prueba a un clúster de producción.

![Admisión y auditoría periódica de Gatekeeper, con plantillas que definen la lógica y Constraints que seleccionan el alcance.](../.gitbook/assets/en-security-09-opa-gatekeeper-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-security-09-opa-gatekeeper-0.html)

<span id="gatekeeper-vs-kyverno-comparison"></span>

## Elección entre Gatekeeper y Kyverno

Elija entre el modelo Rego/Constraint de Gatekeeper y el modelo de políticas orientado a Kubernetes de Kyverno según sus requisitos, pruebas y modelo operativo. Gatekeeper también admite validación nativa de Kubernetes basada en CEL de forma opcional. Evite clasificaciones fijas no compatibles de uso de recursos o afirmaciones de que otro motor no puede expresar lógica compleja. La graduación de OPA de CNCF no establece que Gatekeeper sea un proyecto graduado por separado.

<span id="installation-with-helm"></span>

<span id="installation-with-manifests"></span>

<span id="verify-installation"></span>

## Instalación de Gatekeeper

Use el chart fijado y los valores compatibles del directorio de ejemplos. `auditInterval` y `logLevel` son campos de chart de nivel superior; no suponga que valores arbitrarios de `audit.replicas` o `audit.logLevel` tienen efecto. El perfil renderiza tres réplicas de webhook y un Deployment de auditoría. Verifique la ruta de red del plano de control de EKS al webhook, los certificados, la ubicación y los recursos disponibles.

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm upgrade --install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace --values values.yaml --wait
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-controller-manager
kubectl -n gatekeeper-system rollout status deployment/gatekeeper-audit
```

Para un despliegue por fases, `values.yaml` conserva explícitamente el webhook `failurePolicy: Ignore`. Por lo tanto, los fallos de invocación del webhook pueden permitir solicitudes incluso cuando un Constraint indica `deny`. Evalúe `Fail` junto con la disponibilidad de la API, la recuperación y los namespaces exentos. El alcance del webhook puede ser más amplio que el alcance de un Constraint individual.

### Orden de aplicación de las plantillas y Constraints

Las plantillas generan los CRD de Constraint correspondientes. Espere a que los CRD tengan la condición Established y compruebe el estado de los pods generados por las plantillas antes de aplicar las Constraints. Todos los Constraints de ejemplo comienzan en `dryrun`; revise los prefijos de imagen, los parámetros y los namespaces para el entorno objetivo.

```bash
kubectl create namespace policy-lab --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f templates/
kubectl wait --for=condition=Established --timeout=90s \
  crd/docsrequiredlabels.constraints.gatekeeper.sh \
  crd/docsnoprivileged.constraints.gatekeeper.sh \
  crd/docsapprovedimages.constraints.gatekeeper.sh \
  crd/k8scontainerlimits.constraints.gatekeeper.sh \
  crd/docsuniqueingress.constraints.gatekeeper.sh
kubectl apply -f constraints/
```

<span id="rego-language-basics"></span>

<span id="rego-syntax-overview"></span>

<span id="rego-data-types"></span>

<span id="rego-operators-and-built-in-functions"></span>

## Rego y el contrato de entrada

Las políticas de Gatekeeper usan `input.review`, no `input.request` de un ejemplo genérico de OPA AdmissionReview. `input.parameters` proporciona valores de Constraint y `data.inventory` proporciona objetos de Kubernetes sincronizados. Los `targets[].rego` existentes usan Rego v0 compatible de forma predeterminada. Rego v1 se selecciona explícitamente con `code[].source.version: v1`; las plantillas v0 más antiguas no quedan automáticamente invalidadas.

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
        rego: "package docsrequiredlabels\nvalid_label(key) if {\n  value := input.review.object.metadata.labels[key]\n\
          \  is_string(value)\n  value != \"\"\n}\nviolation contains {\"msg\": sprintf(\"\
          required nonempty label: %v\", [key])} if {\n  some key in input.parameters.labels\n\
          \  not valid_label(key)\n}\n"
```

`violation contains ... if` es una regla de conjunto parcial v1. Varias definiciones contribuyen a ese conjunto; esto no significa que las reglas de valor completo que entran en conflicto siempre se combinen como OR. Todas las condiciones dentro del cuerpo de una regla deben cumplirse. Distinga las reglas recursivas definidas por el usuario de las funciones integradas de recorrido JSON como `walk`.

```rego
package examples
items := [x | some x in input.items; x > 10]
keys := object.keys(object.get(input, "labels", {}))
missing := {"app", "team"} - keys
```

`obj[_]` selecciona valores de objetos. Use `object.keys` o vincule explícitamente la clave cuando necesite claves de labels. La diferencia de conjuntos `-`, la intersección `&` y la unión `|` son operaciones útiles para políticas.

<span id="writing-constraint-templates"></span>

<span id="basic-structure"></span>

<span id="preventing-privileged-containers"></span>

<span id="enforcing-resource-limits"></span>

<span id="restricting-image-registries"></span>

<span id="defining-constraints"></span>

<span id="basic-constraint-writing"></span>

<span id="using-namespace-selectors"></span>

<span id="resource-limits-constraint"></span>

<span id="image-registry-constraint"></span>

## Políticas y alcance

| Template | Comprobaciones | Alcance y límites |
|---|---|---|
| DocsRequiredLabels | Labels no vacíos obligatorios | Metadatos de Pod; los metadatos de Deployment difieren de los labels de plantilla de Pod |
| DocsNoPrivileged | Rechaza privileged=true | Contenedores regulares, init y efímeros; no es un conjunto PSS completo |
| DocsApprovedImages | Prefijos aprobados de registry/ruta | Los tres tipos de contenedor; el esquema requiere un límite final `/` |
| K8sContainerLimits | Presencia y máximo de límites de CPU/memoria | Política upstream fijada; contenedores regulares/init, ya que los contenedores efímeros no pueden establecer campos de recursos |
| DocsUniqueIngress | Conflictos exactos de host en el inventario sincronizado | Excluye actualizaciones del mismo objeto; no hay garantía de comodines ni de creación concurrente atómica |

### Límites de imágenes y excepciones

`registry.example.com/team/` difiere de `registry.example.com/team-evil/` y `registry.example.com.evil/`. La coincidencia de prefijos necesita un límite de separador y un contrato de nombre de imagen completamente cualificado. El ejemplo no ofrece un label de omisión controlado por la carga de trabajo como `skip-privileged-check=true`. Las excepciones de namespace requieren RBAC controlado, autorización, caducidad y registros de auditoría para los cambios de labels.

### Cantidades de recursos

Un analizador limitado a Gi/Mi/Ki puede devolver un resultado indefinido para `9G` o bytes simples e ignorar silenciosamente infracciones. El ejemplo fija la política upstream `K8sContainerLimits`, que informa las cadenas no compatibles como infracciones. No acepta todas las representaciones de cantidades que permite Kubernetes; documente sus restricciones de formato. Las pruebas nativas distinguen millicores, memoria decimal/binaria, bytes simples, entradas numéricas y cadenas de exponentes entre comillas explícitamente. Ponga entre comillas fixtures de cadenas como `8e9` para evitar que los analizadores YAML las conviertan en números.

### PSS y recursos de los controladores

No etiquete unas pocas comprobaciones de privileged/runAsNonRoot como una aplicación completa de Baseline/Restricted. PSS versionado también cubre namespaces de host, seccomp, capabilities, distinciones de SO, herencia de nivel de Pod y contenedores efímeros; use la [guía de Pod Security Standards](./03-pod-security-standards.md). Estos ejemplos comprueban la admisión de Pod. Para evaluar antes las plantillas de Pod de los controladores, configure pruebas independientes con Template o ExpansionTemplate.

<span id="advanced-policy-patterns"></span>

<span id="external-data-reference"></span>

<span id="cross-namespace-policies"></span>

<span id="complex-condition-policies"></span>

## Datos sincronizados y políticas referenciales

`sync.yaml` sincroniza objetos Ingress de `networking.k8s.io/v1` en el inventario. Esto difiere de conectarse a un proveedor HTTP externo o a un bundle OPA arbitrario. Sincronice solo los objetos necesarios y revise RBAC, memoria y datos sensibles.

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
    - group: networking.k8s.io
      version: v1
      kind: Ingress
```

Un nombre diferente en el mismo namespace, o el mismo nombre en otro namespace, todavía puede generar conflicto. Exigir que tanto el namespace como el nombre sean diferentes omite esos casos. El ejemplo excluye solo el mismo namespace/nombre como una autoactualización. Dado que el inventario es eventualmente coherente, no puede garantizar atómicamente la unicidad para creaciones concurrentes.

<span id="mutation-features"></span>

<span id="using-assignmetadata"></span>

<span id="using-assign"></span>

<span id="conditional-mutation"></span>

<span id="using-modifyset"></span>

## Mutación

AssignMetadata agrega labels/anotaciones de metadatos compatibles; no es un mecanismo general de sobrescritura. Assign establece un campo. Asignar una lista completa de tolerations puede descartar entradas existentes, por lo que este ejemplo usa la fusión ModifySet. La toleration permite un taint de laboratorio dedicado; no selecciona nodos Spot.

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: ModifySet
metadata:
  name: docs-dedicated-toleration
spec:
  applyTo:
  - groups:
    - ''
    versions:
    - v1
    kinds:
    - Pod
  match:
    scope: Namespaced
    namespaces:
    - policy-lab
  location: spec.tolerations
  parameters:
    operation: merge
    values:
      fromList:
      - key: dedicated
        operator: Equal
        value: policy-lab
        effect: NoSchedule
```

Separe la mutación/establecimiento de valores predeterminados de la validación. Revise el alcance de CREATE/UPDATE, la aplicación repetida, la convergencia con otros mutadores y los efectos en objetos existentes. Crear un mutador no reescribe automáticamente todos los objetos existentes.

<span id="audit-configuration"></span>

<span id="checking-constraint-violations"></span>

<span id="prometheus-metrics"></span>

<span id="grafana-dashboard"></span>

## Auditoría y monitoreo

Establezca la frecuencia de auditoría con `auditInterval` del chart. La configuración `validation.traces` sirve para depurar evaluaciones de admisión seleccionadas, no para programar auditorías periódicas. Las entradas de admisión y las salidas de Rego pueden contener datos sensibles de objetos; actívelas solo para el alcance necesario. `constraintViolationsLimit` limita la lista de detalles de estado, que puede diferir de totalViolations.

```bash
kubectl get constraints
kubectl describe docsrequiredlabels required-labels
kubectl get constrainttemplatepodstatuses -n gatekeeper-system
kubectl get constraintpodstatuses -n gatekeeper-system
```

El Service del webhook del chart expone solo tráfico HTTPS del webhook, no métricas. `podmonitor.yaml` selecciona el puerto `metrics` (8888) del contenedor real tanto en el Deployment de auditoría como en el de webhook. Instale primero los CRD de Prometheus Operator y ajuste los selectores de etiquetas y espacios de nombres de PodMonitor.

| Métrica | Interpretación |
|---|---|
| gatekeeper_validation_request_count | Solicitudes de validación con labels admission_status reales |
| gatekeeper_validation_request_duration_seconds | Histograma de latencia de validación |
| gatekeeper_violations | Infracciones auditadas por enforcement_action; no se asume un label constraint_name predeterminado |
| gatekeeper_audit_last_run_end_time | Marca de tiempo de la última auditoría completada |
| gatekeeper_constraint_templates | Recuentos de estado de Template |

```promql
sum by (enforcement_action) (gatekeeper_violations)
histogram_quantile(0.99, sum by (le) (rate(gatekeeper_validation_request_duration_seconds_bucket[5m])))
```

<span id="testing-and-ci-cd-integration"></span>

<span id="gator-cli-testing"></span>

<span id="test-suite-definition"></span>

<span id="test-fixtures"></span>

<span id="github-actions-integration"></span>

## Pruebas de Gator y CI

Descargue el binario oficial de la versión 3.23.1 y verifique su checksum publicado. El binario ARM64 informa +dirty en GitVersion; la auditoría verificó el hash del archivo publicado en lugar de suponer que ese texto significa una modificación local. No reemplace evidencia versionada con una ejecución de CLI @latest no fijada.

```bash
gator version
gator verify tests/suite.yaml --verbose
gator test -f templates/docsnoprivileged.yaml \
  -f constraints/no-privileged.yaml \
  -f tests/fixtures/tenant-skip-label-no-bypass.yaml --output=json
```

`verify` comprueba las infracciones esperadas en Suites; `test -f` evalúa manifests frente a Templates/Constraints. Verify puede ignorar un directorio sin Suites, por lo que compruebe que se ejecutaron las cinco pruebas y los 33 casos en lugar de confiar solo en el estado de salida. Las imágenes de fixture son entradas de política, no cargas de trabajo que se puedan descargar. CI ejecuta el conjunto local sin credenciales; cualquier dry-run de clúster corresponde a un entorno confiable independiente con acceso autorizado.

<span id="best-practices"></span>

<span id="policy-organization"></span>

<span id="gradual-policy-rollout"></span>

<span id="policy-exception-management"></span>

<span id="troubleshooting"></span>

<span id="common-issues"></span>

<span id="debugging-tips"></span>

## Despliegue y solución de problemas

Mueva el mismo Constraint con valores establecidos a través de dryrun→warn→deny y revise los resultados de auditoría/admisión y las excepciones. No cree tres Constraints sin parámetros como mecanismo de despliegue. Dryrun/warn pueden devolver infracciones con un estado de salida de prueba Gator cero; las infracciones de deny devuelven uno. Observe los fallos de disponibilidad del webhook por separado de las infracciones de política.

```bash
kubectl get validatingwebhookconfiguration gatekeeper-validating-webhook-configuration -o yaml
kubectl -n gatekeeper-system logs deployment/gatekeeper-controller-manager --tail=100
kubectl -n gatekeeper-system logs deployment/gatekeeper-audit --tail=100
```

Compruebe la entrada de la política, el alcance de coincidencia, los errores de CRD/template, los certificados/red del webhook, las marcas de tiempo de auditoría y la actualidad del inventario. Diagnostique la causa antes de cambiar la aplicación del webhook o ampliar las excepciones de namespace.

<span id="summary"></span>

<span id="related-documentation"></span>

## Alcance de validación y lecturas relacionadas

Gator 3.23.1 ejecutó 33 casos de política y tres modos de aplicación. Las comprobaciones cubrieron el render de Helm fijado, ocho objetos CRD de Gatekeeper y los enlaces de PodMonitor de auditoría/webhook. No ejecutaron la admisión de Kubernetes, las redes de EKS, la sincronización de caché de auditoría en vivo ni la conmutación por error de API. La validación de mutación nativa independiente se registra en el informe de revisión.

- [Cuestionario de Gatekeeper](../quizzes/security/09-opa-gatekeeper-quiz.md)
- [Kyverno](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [Prácticas de seguridad de EKS](./06-eks-security-best-practices.md)

## Referencias

- [Gatekeeper v3.23.1](https://github.com/open-policy-agent/gatekeeper/tree/v3.23.1)
- [ConstraintTemplate y versiones de Rego](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/constrainttemplates.md)
- [Gator](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/gator.md)
- [Mutación](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/mutation.md)
- [Auditoría](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/audit.md)
- [Métricas](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/metrics.md)
- [Política de límites de recursos fijada](https://github.com/open-policy-agent/gatekeeper-library/blob/bd333d4704647b1000cef5a92017257ee46fe2c8/library/general/containerlimits/template.yaml)
