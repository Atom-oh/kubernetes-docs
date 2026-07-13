# Gestión de políticas con Kyverno

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33 **Última actualización**: February 19, 2026

Kyverno es un motor de políticas nativo de Kubernetes utilizado para gestionar y aplicar políticas dentro de clusters. En este capítulo, aprenderemos a gestionar políticas en clusters de EKS usando Kyverno.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Herramientas requeridas

* kubectl v1.31 o superior
* Helm v3.10 o superior
* Un cluster de Kubernetes en funcionamiento (EKS, minikube, kind, etc.)

### Instalación de Kyverno

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/

# Update Helm repository
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno -n kyverno --create-namespace
```

## Introducción a Kyverno

Kyverno es un motor de políticas que te permite definir y gestionar políticas como recursos de Kubernetes. Kyverno proporciona las siguientes capacidades:

1. **Validate**: Verifica que los recursos cumplan con las políticas.
2. **Mutate**: Modifica automáticamente los recursos.
3. **Generate**: Crea automáticamente recursos relacionados.
4. **Clean up**: Elimina automáticamente los recursos que ya no son necesarios.

> **Concepto clave**: Kyverno usa un enfoque nativo de Kubernetes, por lo que no es necesario aprender un lenguaje o herramienta independiente. Las políticas se definen como recursos de Kubernetes y se pueden gestionar usando kubectl.

### Arquitectura de Kyverno y cómo funciona

### Kyverno vs OPA Gatekeeper

Kyverno y OPA Gatekeeper son herramientas para la gestión de políticas de Kubernetes, pero existen algunas diferencias importantes:

| Característica      | Kyverno                            | OPA Gatekeeper                 |
| ------------------- | ---------------------------------- | ------------------------------ |
| Lenguaje de políticas | Kubernetes YAML                    | Rego (lenguaje dedicado)       |
| Curva de aprendizaje | Baja (familiar para usuarios de Kubernetes) | Alta (requiere aprender Rego) |
| Políticas de mutación | Soporte nativo                     | Soporte limitado               |
| Generación de recursos | Compatible                         | No compatible                  |
| Verificación de imágenes | Soporte nativo                     | Requiere implementación personalizada |
| Excepciones de políticas | Simple                             | Compleja                       |
| Rendimiento        | Bueno                              | Muy bueno (para clusters grandes) |

Kyverno opera como un Admission Controller de Kubernetes, interceptando todas las solicitudes al servidor de API y realizando operaciones de validación, mutación, generación o limpieza según las políticas definidas. También verifica el cumplimiento de políticas para los recursos existentes mediante un escáner en segundo plano e informa las infracciones de políticas mediante un controlador de informes.

## Instalación de Kyverno

### Instalación usando Helm

Así se instala Kyverno usando Helm:

```bash
# Add Helm repository
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

# Install Kyverno
helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
```

### Instalación usando manifiestos YAML

Así se instala Kyverno usando manifiestos YAML:

```bash
# Create namespace
kubectl create namespace kyverno

# Install Kyverno
kubectl apply -f https://github.com/kyverno/kyverno/releases/download/v1.10.0/install.yaml
```

## Tipos de políticas

Kyverno admite los siguientes tipos de políticas:

### 1. Políticas de validación

Las políticas de validación verifican que los recursos cumplan condiciones específicas. Si no se cumplen las condiciones, se rechaza la creación o actualización del recurso.

Ejemplo: Una política que garantiza que todos los pods tengan límites de recursos configurados

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 2. Políticas de mutación

Las políticas de mutación modifican automáticamente los recursos. Esto te permite establecer valores predeterminados o agregar campos específicos.

Ejemplo: Una política que agrega labels predeterminados a todos los pods

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-default-labels
spec:
  rules:
  - name: add-labels
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        metadata:
          labels:
            environment: "{{request.namespace}}"
            app.kubernetes.io/managed-by: kyverno
```

### 3. Políticas de generación

Las políticas de generación crean automáticamente recursos relacionados cuando se crea un recurso.

Ejemplo: Una política que crea automáticamente una NetworkPolicy cuando se crea un namespace

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-networkpolicy
spec:
  rules:
  - name: generate-default-networkpolicy
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: NetworkPolicy
      name: default-deny-all
      namespace: "{{request.object.metadata.name}}"
      data:
        spec:
          podSelector: {}
          policyTypes:
          - Ingress
          - Egress
```

## Casos de uso de Kyverno en EKS

Usar Kyverno en clusters de EKS te permite aplicar políticas en varios aspectos, incluidos seguridad, optimización de costos y cumplimiento.

### Arquitectura de integración de EKS y Kyverno

El siguiente diagrama muestra cómo Kyverno se integra y opera dentro de un cluster de EKS:

En esta arquitectura, Kyverno opera como un Admission Webhook dentro del cluster de EKS, interceptando todas las solicitudes al servidor de API y procesándolas según las políticas definidas. Las infracciones de políticas pueden enviarse a CloudWatch para monitoreo y alertas.

### 1. Endurecimiento de seguridad

#### Prevención de contenedores privilegiados

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed."
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
```

#### Prevención de ejecución como usuario root

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-root-user
spec:
  validationFailureAction: enforce
  rules:
  - name: check-runAsNonRoot
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Running as root is not allowed. Set runAsNonRoot to true."
      pattern:
        spec:
          containers:
          - securityContext:
              runAsNonRoot: true
```

### 2. Optimización de costos

#### Configuración de límites de recursos

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: set-default-resources
spec:
  rules:
  - name: set-default-resources
    match:
      resources:
        kinds:
        - Pod
    mutate:
      patchStrategicMerge:
        spec:
          containers:
          - (name): "*"
            resources:
              limits:
                memory: "512Mi"
                cpu: "500m"
              requests:
                memory: "256Mi"
                cpu: "250m"
```

#### Aplicación de tipos de instancia específicos

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-node-types
spec:
  validationFailureAction: enforce
  rules:
  - name: check-node-type
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Pod must be scheduled on approved node types."
      pattern:
        spec:
          nodeSelector:
            node.kubernetes.io/instance-type: "?*"
          affinity:
            nodeAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                nodeSelectorTerms:
                - matchExpressions:
                  - key: node.kubernetes.io/instance-type
                    operator: In
                    values:
                    - m5.large
                    - c5.large
                    - r5.large
```

### 3. Cumplimiento

#### Generación automática de PodDisruptionBudget

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-pdb
spec:
  rules:
  - name: generate-pdb-for-deployment
    match:
      resources:
        kinds:
        - Deployment
    generate:
      kind: PodDisruptionBudget
      name: "{{request.object.metadata.name}}-pdb"
      namespace: "{{request.object.metadata.namespace}}"
      synchronize: true
      data:
        spec:
          minAvailable: 1
          selector:
            matchLabels:
              app: "{{request.object.metadata.labels.app}}"
```

#### Generación automática de ResourceQuota de namespace

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: generate-resourcequota
spec:
  rules:
  - name: generate-resourcequota
    match:
      resources:
        kinds:
        - Namespace
    generate:
      kind: ResourceQuota
      name: default-resourcequota
      namespace: "{{request.object.metadata.name}}"
      synchronize: true
      data:
        spec:
          hard:
            requests.cpu: "10"
            requests.memory: 10Gi
            limits.cpu: "20"
            limits.memory: 20Gi
            pods: "50"
```

## Pruebas y validación de políticas

Kyverno proporciona herramientas para probar y validar políticas.

### Flujo de trabajo de aplicación de políticas

El siguiente diagrama muestra el flujo de trabajo típico de desarrollo y aplicación para políticas de Kyverno:

### Simulación de políticas

Puedes simular políticas usando el comando `kyverno test`:

```bash
# Install Kyverno CLI
curl -LO https://github.com/kyverno/kyverno/releases/download/v1.10.0/kyverno-cli_v1.10.0_linux_x86_64.tar.gz
tar -xvf kyverno-cli_v1.10.0_linux_x86_64.tar.gz
sudo mv kyverno /usr/local/bin/

# Test policy
kyverno test ./policy.yaml --resource=./resource.yaml
```

### Validación de políticas

Puedes validar políticas usando el plugin `kubectl kyverno`:

```bash
# Install kubectl kyverno plugin
kubectl krew install kyverno

# Validate policy
kubectl kyverno apply ./policy.yaml --cluster
```

## Monitoreo e informes de políticas

Kyverno proporciona herramientas para monitorear e informar infracciones de políticas.

### Informes de políticas

Kyverno crea los siguientes recursos de informe:

1. **ClusterPolicyReport**: Informa infracciones de políticas a nivel de cluster.
2. **PolicyReport**: Informa infracciones de políticas a nivel de namespace.

```bash
# View cluster policy reports
kubectl get clusterpolicyreport

# View namespace policy reports
kubectl get policyreport -n <namespace>
```

### Métricas de Prometheus

Kyverno proporciona métricas de Prometheus para monitorear infracciones de políticas:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: kyverno-svc-metrics
  namespace: kyverno
  labels:
    app: kyverno
spec:
  ports:
  - port: 8000
    targetPort: 8000
    name: metrics
  selector:
    app: kyverno
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kyverno-svc-metrics
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: kyverno
  endpoints:
  - port: metrics
```

## Mejores prácticas

### 1. Implementación gradual

Al introducir nuevas políticas, se recomienda configurar primero el modo `validationFailureAction: audit` para monitorear infracciones y luego cambiar al modo `enforce` cuando esté listo.

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: audit  # Start with audit mode first
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 2. Manejo de excepciones

Para manejar excepciones de namespaces o recursos específicos, usa la sección `exclude`:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: enforce
  rules:
  - name: check-resource-limits
    match:
      resources:
        kinds:
        - Pod
    exclude:
      resources:
        namespaces:
        - kube-system
        - kyverno
    validate:
      message: "Resource limits are required for all containers."
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
                cpu: "?*"
```

### 3. Organización de políticas

Se recomienda organizar las políticas por propósito y usar nombres claros:

```
policies/
├── security/
│   ├── disallow-privileged-containers.yaml
│   ├── require-pod-probes.yaml
│   └── restrict-image-registries.yaml
├── cost-optimization/
│   ├── require-resource-limits.yaml
│   └── restrict-node-types.yaml
└── compliance/
    ├── generate-pdb.yaml
    └── generate-resourcequota.yaml
```

## Conclusión

Kyverno es una herramienta potente para gestionar políticas usando un enfoque nativo de Kubernetes. Usar Kyverno en clusters de EKS te permite aplicar políticas en varios aspectos, incluidos seguridad, optimización de costos y cumplimiento. Es importante introducir las políticas de forma gradual, manejar excepciones y organizarlas bien.

## Cuestionario

Para poner a prueba lo que has aprendido en este capítulo, prueba el [cuestionario sobre gestión de políticas con Kyverno](../quizzes/security/01-kyverno-policy-management-quiz.md).
