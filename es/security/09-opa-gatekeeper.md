# OPA Gatekeeper

> **Versiones compatibles**: Gatekeeper v3.14+, Kubernetes 1.25+
> **Última actualización**: February 22, 2026

## Descripción general

OPA (Open Policy Agent) Gatekeeper es una herramienta de gestión de políticas para Kubernetes que usa el lenguaje Rego para escribir políticas declarativas y aplica las políticas del cluster mediante un Admission Controller.

```mermaid
graph TB
    subgraph "OPA Gatekeeper Architecture"
        API[API Server] --> WH[Webhook]
        WH --> GK[Gatekeeper Controller]
        GK --> OPA[OPA Engine]
        OPA --> CT[Constraint Templates]
        OPA --> C[Constraints]
        GK --> AR[Audit Results]
    end

    subgraph "Policy Components"
        CT --> |Defines| Rego[Rego Policy]
        C --> |Applies to| Target[Target Resources]
    end

    style GK fill:#e1f5fe
    style OPA fill:#fff3e0
```

## Comparación entre Gatekeeper y Kyverno

| Característica | Gatekeeper | Kyverno |
|---------|------------|---------|
| **Lenguaje de políticas** | Rego (declarativo) | YAML (nativo de K8s) |
| **Curva de aprendizaje** | Alta (lenguaje nuevo) | Baja (amigable para K8s) |
| **Flexibilidad** | Muy alta | Alta |
| **Datos externos** | OPA bundles, fuentes externas | ConfigMap, llamada a API |
| **Mutación** | Soporte en v3.10+ | Soporte nativo |
| **Generación** | No soportada | Soporte nativo |
| **Auditoría** | Integrada | Integrada |
| **Uso de recursos** | Medio | Bajo |
| **Comunidad** | Graduado de CNCF | Incubando en CNCF |

## Instalación de Gatekeeper

### Instalación con Helm

```bash
# Add Gatekeeper Helm repository
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update

# Install Gatekeeper
helm install gatekeeper gatekeeper/gatekeeper \
  --namespace gatekeeper-system \
  --create-namespace \
  --set replicas=3 \
  --set audit.replicas=1 \
  --set audit.logLevel=INFO \
  --set controllerManager.logLevel=INFO
```

### Instalación con manifiestos

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.14.0/deploy/gatekeeper.yaml
```

### Verificar la instalación

```bash
# Check Pod status
kubectl get pods -n gatekeeper-system

# Check CRDs
kubectl get crd | grep gatekeeper

# Example output:
# configs.config.gatekeeper.sh
# constrainttemplates.templates.gatekeeper.sh
# constraintpodstatuses.status.gatekeeper.sh
# mutatorpodstatuses.status.gatekeeper.sh
# assignmetadata.mutations.gatekeeper.sh
# assign.mutations.gatekeeper.sh
# modifyset.mutations.gatekeeper.sh
```

## Fundamentos del lenguaje Rego

### Descripción general de la sintaxis de Rego

```rego
# Package declaration
package kubernetes.admission

# import statements
import data.kubernetes.namespaces
import future.keywords.in
import future.keywords.contains
import future.keywords.if

# Basic rule definition
deny[msg] {
    input.request.kind.kind == "Pod"
    container := input.request.object.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v has no memory limit", [container.name])
}

# Helper function
is_privileged(container) {
    container.securityContext.privileged == true
}

# Complex condition
violation[{"msg": msg}] {
    container := input.request.object.spec.containers[_]
    is_privileged(container)
    msg := sprintf("Privileged container not allowed: %v", [container.name])
}
```

### Tipos de datos de Rego

```rego
package examples

# Scalar values
string_val := "hello"
number_val := 42
boolean_val := true
null_val := null

# Complex types
array_val := ["a", "b", "c"]
object_val := {"key": "value", "nested": {"inner": 1}}
set_val := {"unique", "values", "only"}

# Comprehensions
filtered := [x | x := input.items[_]; x > 10]
mapped := {k: v | some k; v := input.data[k]; v != null}
```

### Operadores y funciones integradas de Rego

```rego
package operators

# Comparison operators
equal := 1 == 1
not_equal := 1 != 2
less_than := 1 < 2
greater_than := 2 > 1

# String functions
contains_check := contains("hello world", "world")
starts_check := startswith("kubernetes", "kube")
ends_check := endswith("pod.yaml", ".yaml")
lower_case := lower("HELLO")
upper_case := upper("hello")
split_result := split("a,b,c", ",")
sprintf_result := sprintf("pod-%s", ["name"])

# Regular expressions
regex_match := regex.match("^pod-.*", "pod-123")

# Array/Set functions
count_items := count([1, 2, 3])
sum_items := sum([1, 2, 3])
max_item := max([1, 2, 3])
min_item := min([1, 2, 3])
sort_items := sort([3, 1, 2])
array_concat := array.concat([1, 2], [3, 4])

# Object functions
object_get := object.get({"a": 1}, "a", 0)
object_keys := object.keys({"a": 1, "b": 2})
json_marshal := json.marshal({"key": "value"})
json_unmarshal := json.unmarshal("{\"key\":\"value\"}")
```

## Escritura de Constraint Templates

### Estructura básica

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
  annotations:
    metadata.gatekeeper.sh/title: "Required Labels"
    metadata.gatekeeper.sh/version: 1.0.0
    description: "Requires resources to have specified labels"
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
              description: "A list of required labels"
            message:
              type: string
              description: "Custom error message"
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        import future.keywords.in

        violation[{"msg": msg, "details": {"missing_labels": missing}}] {
            provided := {label | input.review.object.metadata.labels[label]}
            required := {label | label := input.parameters.labels[_]}
            missing := required - provided
            count(missing) > 0
            msg := sprintf("Resource missing required labels: %v", [missing])
        }
```

### Prevención de containers privilegiados

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8spsprivilegedcontainer
  annotations:
    metadata.gatekeeper.sh/title: "Privileged Container"
    description: "Prevents containers from running in privileged mode"
spec:
  crd:
    spec:
      names:
        kind: K8sPSPPrivilegedContainer
      validation:
        openAPIV3Schema:
          type: object
          properties:
            exemptImages:
              type: array
              items:
                type: string
              description: "Images exempt from this policy"
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8spsprivilegedcontainer

        import future.keywords.in

        violation[{"msg": msg, "details": {"container": container.name}}] {
            container := input_containers[_]
            container.securityContext.privileged == true
            not is_exempt(container)
            msg := sprintf("Privileged container not allowed: %v", [container.name])
        }

        input_containers[c] {
            c := input.review.object.spec.containers[_]
        }

        input_containers[c] {
            c := input.review.object.spec.initContainers[_]
        }

        input_containers[c] {
            c := input.review.object.spec.ephemeralContainers[_]
        }

        is_exempt(container) {
            exempt_image := input.parameters.exemptImages[_]
            startswith(container.image, exempt_image)
        }
```

### Aplicación de límites de recursos

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8scontainerlimits
  annotations:
    metadata.gatekeeper.sh/title: "Container Limits"
    description: "Requires containers to have resource limits"
spec:
  crd:
    spec:
      names:
        kind: K8sContainerLimits
      validation:
        openAPIV3Schema:
          type: object
          properties:
            cpu:
              type: string
              description: "Maximum CPU limit"
            memory:
              type: string
              description: "Maximum memory limit"
            exemptContainers:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8scontainerlimits

        import future.keywords.in

        violation[{"msg": msg}] {
            container := input.review.object.spec.containers[_]
            not is_exempt(container.name)
            not container.resources.limits.cpu
            msg := sprintf("Container %v has no CPU limit", [container.name])
        }

        violation[{"msg": msg}] {
            container := input.review.object.spec.containers[_]
            not is_exempt(container.name)
            not container.resources.limits.memory
            msg := sprintf("Container %v has no memory limit", [container.name])
        }

        violation[{"msg": msg}] {
            container := input.review.object.spec.containers[_]
            not is_exempt(container.name)
            cpu_limit := container.resources.limits.cpu
            max_cpu := input.parameters.cpu
            exceeds_cpu(cpu_limit, max_cpu)
            msg := sprintf("Container %v CPU limit %v exceeds maximum %v",
                          [container.name, cpu_limit, max_cpu])
        }

        violation[{"msg": msg}] {
            container := input.review.object.spec.containers[_]
            not is_exempt(container.name)
            memory_limit := container.resources.limits.memory
            max_memory := input.parameters.memory
            exceeds_memory(memory_limit, max_memory)
            msg := sprintf("Container %v memory limit %v exceeds maximum %v",
                          [container.name, memory_limit, max_memory])
        }

        is_exempt(name) {
            exempt := input.parameters.exemptContainers[_]
            name == exempt
        }

        # CPU comparison function (convert to millicores)
        exceeds_cpu(limit, max) {
            limit_milli := parse_cpu(limit)
            max_milli := parse_cpu(max)
            limit_milli > max_milli
        }

        parse_cpu(cpu) = milli {
            endswith(cpu, "m")
            milli := to_number(trim_suffix(cpu, "m"))
        }

        parse_cpu(cpu) = milli {
            not endswith(cpu, "m")
            milli := to_number(cpu) * 1000
        }

        # Memory comparison function (convert to bytes)
        exceeds_memory(limit, max) {
            limit_bytes := parse_memory(limit)
            max_bytes := parse_memory(max)
            limit_bytes > max_bytes
        }

        parse_memory(mem) = bytes {
            endswith(mem, "Gi")
            bytes := to_number(trim_suffix(mem, "Gi")) * 1073741824
        }

        parse_memory(mem) = bytes {
            endswith(mem, "Mi")
            bytes := to_number(trim_suffix(mem, "Mi")) * 1048576
        }

        parse_memory(mem) = bytes {
            endswith(mem, "Ki")
            bytes := to_number(trim_suffix(mem, "Ki")) * 1024
        }
```

### Restricción de registros de imágenes

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sallowedrepos
  annotations:
    metadata.gatekeeper.sh/title: "Allowed Repositories"
    description: "Requires container images from allowed repositories"
spec:
  crd:
    spec:
      names:
        kind: K8sAllowedRepos
      validation:
        openAPIV3Schema:
          type: object
          properties:
            repos:
              type: array
              items:
                type: string
              description: "List of allowed image repositories"
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sallowedrepos

        import future.keywords.in

        violation[{"msg": msg}] {
            container := input.review.object.spec.containers[_]
            not image_allowed(container.image)
            msg := sprintf("Container %v uses image %v from disallowed repository",
                          [container.name, container.image])
        }

        violation[{"msg": msg}] {
            container := input.review.object.spec.initContainers[_]
            not image_allowed(container.image)
            msg := sprintf("InitContainer %v uses image %v from disallowed repository",
                          [container.name, container.image])
        }

        image_allowed(image) {
            repo := input.parameters.repos[_]
            startswith(image, repo)
        }
```

## Definición de Constraints

### Escritura básica de Constraints

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-app-labels
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet", "DaemonSet"]
    namespaces:
      - production
      - staging
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
  parameters:
    labels:
      - "app.kubernetes.io/name"
      - "app.kubernetes.io/version"
      - "app.kubernetes.io/component"
    message: "All resources must have standard Kubernetes labels"
```

### Uso de Namespace Selectors

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPSPPrivilegedContainer
metadata:
  name: deny-privileged-containers
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaceSelector:
      matchExpressions:
        - key: environment
          operator: In
          values: ["production", "staging"]
        - key: privileged-allowed
          operator: NotIn
          values: ["true"]
    labelSelector:
      matchExpressions:
        - key: skip-privileged-check
          operator: NotIn
          values: ["true"]
  parameters:
    exemptImages:
      - "gcr.io/google-containers/"
      - "k8s.gcr.io/"
```

### Constraint de límites de recursos

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sContainerLimits
metadata:
  name: container-resource-limits
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
      - monitoring
  parameters:
    cpu: "4"
    memory: "8Gi"
    exemptContainers:
      - istio-proxy
      - linkerd-proxy
```

### Constraint de registro de imágenes

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sAllowedRepos
metadata:
  name: allowed-image-repos
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces:
      - kube-system
  parameters:
    repos:
      - "123456789012.dkr.ecr.us-west-2.amazonaws.com/"
      - "gcr.io/distroless/"
      - "docker.io/library/"
```

## Patrones avanzados de políticas

### Referencia a datos externos

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
      - group: ""
        version: "v1"
        kind: "ConfigMap"
      - group: "networking.k8s.io"
        version: "v1"
        kind: "Ingress"
```

### Políticas entre namespaces

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8suniqueingresshost
spec:
  crd:
    spec:
      names:
        kind: K8sUniqueIngressHost
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8suniqueingresshost

        import future.keywords.in

        violation[{"msg": msg}] {
            input.review.kind.kind == "Ingress"
            host := input.review.object.spec.rules[_].host
            other := data.inventory.namespace[ns][otherapiversion]["Ingress"][name]
            other.metadata.namespace != input.review.object.metadata.namespace
            other.metadata.name != input.review.object.metadata.name
            other_host := other.spec.rules[_].host
            host == other_host
            msg := sprintf("Ingress host %v is already used by %v/%v",
                          [host, ns, name])
        }
```

### Políticas con condiciones complejas

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8spodsecuritystandard
spec:
  crd:
    spec:
      names:
        kind: K8sPodSecurityStandard
      validation:
        openAPIV3Schema:
          type: object
          properties:
            level:
              type: string
              enum: ["baseline", "restricted"]
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8spodsecuritystandard

        import future.keywords.in

        # Baseline level violations
        violation[{"msg": msg, "details": {"level": "baseline"}}] {
            input.parameters.level == "baseline"
            container := input_containers[_]
            container.securityContext.privileged == true
            msg := sprintf("Baseline violation: privileged container %v", [container.name])
        }

        violation[{"msg": msg, "details": {"level": "baseline"}}] {
            input.parameters.level == "baseline"
            container := input_containers[_]
            has_host_namespace(input.review.object.spec)
            msg := "Baseline violation: host namespaces not allowed"
        }

        # Restricted level violations (includes Baseline)
        violation[{"msg": msg, "details": {"level": "restricted"}}] {
            input.parameters.level == "restricted"
            container := input_containers[_]
            container.securityContext.privileged == true
            msg := sprintf("Restricted violation: privileged container %v", [container.name])
        }

        violation[{"msg": msg, "details": {"level": "restricted"}}] {
            input.parameters.level == "restricted"
            container := input_containers[_]
            not container.securityContext.runAsNonRoot == true
            msg := sprintf("Restricted violation: container %v must run as non-root",
                          [container.name])
        }

        violation[{"msg": msg, "details": {"level": "restricted"}}] {
            input.parameters.level == "restricted"
            container := input_containers[_]
            not container.securityContext.allowPrivilegeEscalation == false
            msg := sprintf("Restricted violation: container %v allows privilege escalation",
                          [container.name])
        }

        violation[{"msg": msg, "details": {"level": "restricted"}}] {
            input.parameters.level == "restricted"
            container := input_containers[_]
            has_dangerous_capabilities(container)
            msg := sprintf("Restricted violation: container %v has dangerous capabilities",
                          [container.name])
        }

        input_containers[c] {
            c := input.review.object.spec.containers[_]
        }

        input_containers[c] {
            c := input.review.object.spec.initContainers[_]
        }

        has_host_namespace(spec) {
            spec.hostNetwork == true
        }

        has_host_namespace(spec) {
            spec.hostPID == true
        }

        has_host_namespace(spec) {
            spec.hostIPC == true
        }

        has_dangerous_capabilities(container) {
            cap := container.securityContext.capabilities.add[_]
            dangerous_caps[cap]
        }

        dangerous_caps := {"ALL", "SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE"}
```

## Funcionalidades de mutación

### Uso de AssignMetadata

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
    excludedNamespaces:
      - kube-system
  location: "metadata.labels.owner"
  parameters:
    assign:
      value: "platform-team"
```

### Uso de Assign

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: Assign
metadata:
  name: set-image-pull-policy
spec:
  applyTo:
    - groups: [""]
      kinds: ["Pod"]
      versions: ["v1"]
  match:
    scope: Namespaced
    excludedNamespaces:
      - kube-system
  location: "spec.containers[name:*].imagePullPolicy"
  parameters:
    assign:
      value: "Always"
```

### Mutación condicional

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: Assign
metadata:
  name: add-tolerations-for-spot
spec:
  applyTo:
    - groups: [""]
      kinds: ["Pod"]
      versions: ["v1"]
  match:
    scope: Namespaced
    labelSelector:
      matchLabels:
        allow-spot: "true"
  location: "spec.tolerations"
  parameters:
    assign:
      value:
        - key: "kubernetes.io/spot"
          operator: "Exists"
          effect: "NoSchedule"
```

### Uso de ModifySet

```yaml
apiVersion: mutations.gatekeeper.sh/v1
kind: ModifySet
metadata:
  name: add-security-capability
spec:
  applyTo:
    - groups: [""]
      kinds: ["Pod"]
      versions: ["v1"]
  match:
    scope: Namespaced
  location: "spec.containers[name:*].securityContext.capabilities.drop"
  parameters:
    operation: merge
    values:
      fromList:
        - "ALL"
```

## Auditoría y monitoreo

### Configuración de auditoría

```yaml
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  # Audit interval setting (seconds)
  # Can be checked with audit command
  validation:
    traces:
      - user: "*"
        kind:
          group: ""
          version: "v1"
          kind: "Pod"
```

### Comprobación de violaciones de Constraints

```bash
# Check violation status for all Constraints
kubectl get constraints

# Get detailed violation info for specific Constraint
kubectl describe k8srequiredlabels require-app-labels

# Example output:
# Status:
#   Audit Timestamp:  2026-02-21T10:30:00Z
#   Total Violations:  5
#   Violations:
#     Enforcement Action:  deny
#     Kind:               Pod
#     Name:               nginx-without-labels
#     Namespace:          default
#     Message:            Resource missing required labels: {"app.kubernetes.io/name"}
```

### Métricas de Prometheus

```yaml
# Gatekeeper ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: gatekeeper-controller-manager
  namespace: gatekeeper-system
spec:
  selector:
    matchLabels:
      control-plane: controller-manager
  endpoints:
    - port: metrics
      interval: 30s
```

Métricas clave:

| Nombre de la métrica | Descripción |
|-------------|-------------|
| `gatekeeper_violations` | Violaciones por Constraint |
| `gatekeeper_constraints` | Recuento total de Constraints |
| `gatekeeper_constraint_templates` | Recuento total de ConstraintTemplates |
| `gatekeeper_request_count` | Recuento de solicitudes de Admission |
| `gatekeeper_request_duration_seconds` | Tiempo de procesamiento de solicitudes |
| `gatekeeper_audit_duration_seconds` | Duración de auditoría |

### Dashboard de Grafana

```json
{
  "panels": [
    {
      "title": "Policy Violations by Constraint",
      "targets": [
        {
          "expr": "sum by (constraint_name) (gatekeeper_violations)",
          "legendFormat": "{{constraint_name}}"
        }
      ]
    },
    {
      "title": "Admission Request Latency",
      "targets": [
        {
          "expr": "histogram_quantile(0.99, sum(rate(gatekeeper_request_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "p99"
        }
      ]
    },
    {
      "title": "Admission Requests by Status",
      "targets": [
        {
          "expr": "sum by (admission_status) (rate(gatekeeper_request_count[5m]))",
          "legendFormat": "{{admission_status}}"
        }
      ]
    }
  ]
}
```

## Pruebas e integración de CI/CD

### Pruebas con Gator CLI

```bash
# Install Gator
go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

# Validate policies
gator verify ./policies/

# Run test suite
gator test ./tests/
```

### Definición de suite de pruebas

```yaml
# tests/required-labels-test.yaml
kind: Suite
apiVersion: test.gatekeeper.sh/v1alpha1
metadata:
  name: required-labels-test
tests:
  - name: "Missing required labels should fail"
    template: ../templates/k8srequiredlabels.yaml
    constraint: ../constraints/require-app-labels.yaml
    cases:
      - name: pod-without-labels
        object: fixtures/pod-without-labels.yaml
        assertions:
          - violations: yes
            message: "missing required labels"

      - name: pod-with-all-labels
        object: fixtures/pod-with-labels.yaml
        assertions:
          - violations: no
```

### Fixtures de prueba

```yaml
# fixtures/pod-without-labels.yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: production
spec:
  containers:
    - name: nginx
      image: nginx:latest
---
# fixtures/pod-with-labels.yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  namespace: production
  labels:
    app.kubernetes.io/name: nginx
    app.kubernetes.io/version: "1.0"
    app.kubernetes.io/component: web
spec:
  containers:
    - name: nginx
      image: nginx:latest
```

### Integración con GitHub Actions

```yaml
name: Policy Validation
on:
  pull_request:
    paths:
      - 'policies/**'
      - 'constraints/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Gator
        run: |
          go install github.com/open-policy-agent/gatekeeper/cmd/gator@latest

      - name: Validate Constraint Templates
        run: |
          gator verify ./policies/templates/

      - name: Run Policy Tests
        run: |
          gator test ./policies/tests/

      - name: Dry-run against cluster
        if: github.event_name == 'pull_request'
        run: |
          kubectl apply --dry-run=server -f ./policies/
```

## Buenas prácticas

### Organización de políticas

```
policies/
├── templates/
│   ├── security/
│   │   ├── privileged-container.yaml
│   │   ├── host-namespaces.yaml
│   │   └── capabilities.yaml
│   ├── resources/
│   │   ├── container-limits.yaml
│   │   └── storage-class.yaml
│   └── networking/
│       ├── allowed-repos.yaml
│       └── ingress-host.yaml
├── constraints/
│   ├── production/
│   │   ├── security-constraints.yaml
│   │   └── resource-constraints.yaml
│   └── development/
│       └── basic-constraints.yaml
├── mutations/
│   ├── defaults/
│   │   └── image-pull-policy.yaml
│   └── labels/
│       └── add-owner-label.yaml
└── tests/
    ├── security/
    │   └── privileged-test.yaml
    └── resources/
        └── limits-test.yaml
```

### Despliegue gradual de políticas

```yaml
# Phase 1: Dry Run (dryrun mode)
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-dryrun
spec:
  enforcementAction: dryrun  # Logging only
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
---
# Phase 2: Warn mode
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-warn
spec:
  enforcementAction: warn  # Warning only
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
---
# Phase 3: Deny mode (full enforcement)
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-enforce
spec:
  enforcementAction: deny  # Reject
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
```

### Gestión de excepciones de políticas

```yaml
# Using namespace labels for exceptions
apiVersion: v1
kind: Namespace
metadata:
  name: legacy-app
  labels:
    policy-exceptions: "privileged"
---
# Exception handling in Constraint
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPSPPrivilegedContainer
metadata:
  name: deny-privileged
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaceSelector:
      matchExpressions:
        - key: policy-exceptions
          operator: NotIn
          values: ["privileged"]
```

## Solución de problemas

### Problemas comunes

```bash
# Check webhook issues
kubectl get validatingwebhookconfigurations gatekeeper-validating-webhook-configuration -o yaml

# Check Gatekeeper logs
kubectl logs -n gatekeeper-system -l control-plane=controller-manager -f

# Check Audit logs
kubectl logs -n gatekeeper-system -l control-plane=audit-controller -f

# Check Constraint sync status
kubectl get constrainttemplatepodstatuses -n gatekeeper-system
kubectl get constraintpodstatuses -n gatekeeper-system
```

### Consejos de depuración

```yaml
# Using print statements for Rego debugging
violation[{"msg": msg}] {
    container := input.review.object.spec.containers[_]
    print("Checking container:", container.name)
    print("Image:", container.image)
    not starts_with_allowed(container.image)
    msg := sprintf("Invalid image: %v", [container.image])
}
```

## Resumen

OPA Gatekeeper es un potente motor de políticas que proporciona:

1. **Lenguaje Rego**: escritura de políticas declarativa y flexible
2. **ConstraintTemplate**: plantillas de políticas reutilizables
3. **Constraint**: aplicación específica de políticas
4. **Mutación**: modificación automática de recursos
5. **Auditoría**: comprobación de cumplimiento de políticas para recursos existentes
6. **Pruebas**: validación de políticas con Gator

Aunque tiene una curva de aprendizaje más alta en comparación con Kyverno, ofrece mayor flexibilidad para lógica de políticas compleja.

---

## Documentación relacionada

- [Gestión de políticas con Kyverno](./01-kyverno-policy-management.md)
- [Pod Security Standards](./03-pod-security-standards.md)
- [Buenas prácticas de seguridad de EKS](./06-eks-security-best-practices.md)
