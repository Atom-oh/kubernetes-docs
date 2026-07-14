# Tekton Pipelines
> **Versiones compatibles**: Tekton Pipelines v0.62+, Tekton Triggers v0.28+
> **Última actualización**: June 2025

< [Anterior: Plataforma de visibilidad de costos FinOps](./13-finops-cost-platform.md) | [Tabla de contenidos](./README.md) | [Siguiente: Ninguno] >

---

## Descripción general

Tekton es un framework open-source, nativo de Kubernetes, para crear sistemas de CI/CD. A diferencia de las plataformas de CI tradicionales que se acoplan a Kubernetes como algo secundario, Tekton ejecuta pipelines como recursos Kubernetes de primera clase: cada Task es un Pod, cada Step es un container y cada Pipeline está orquestado por controladores personalizados que observan Custom Resource Definitions (CRDs). Esto hace que Tekton sea inherentemente portable, escalable y profundamente integrado con el ecosistema Kubernetes.

Tekton se originó en Google como parte del proyecto Knative (específicamente `knative/build`) antes de ser donado a la Continuous Delivery Foundation (CDF) en 2019, donde convive con Jenkins, Jenkins X y Spinnaker. Se graduó como proyecto maduro de CDF y también participa en el ecosistema CNCF gracias a su integración con proyectos como Sigstore e in-toto.

### ¿Por qué Tekton en lugar de CI/CD tradicional?

Los sistemas de CI/CD tradicionales (Jenkins, GitHub Actions, GitLab CI) operan como servicios centralizados que envían trabajo a runners. Este modelo introduce varios desafíos en entornos Kubernetes:

- **Duplicación de infraestructura**: Un controlador Jenkins se ejecuta junto al cluster Kubernetes, lo que requiere sus propias consideraciones de disponibilidad, almacenamiento y escalado.
- **Dispersión de secretos**: Las plataformas de CI necesitan sus propios almacenes de credenciales, duplicando lo que Kubernetes ya administra mediante Secrets, IRSA y Pod Identity.
- **Conocimiento limitado de Kubernetes**: Los sistemas de CI externos carecen de acceso nativo a las APIs de Kubernetes, lo que requiere configuración de kubectl y distribución de kubeconfig.
- **Dependencia del proveedor**: Las definiciones de Pipeline están fuertemente acopladas al YAML propietario o al DSL Groovy de la plataforma de CI.

Tekton elimina estos problemas al definir pipelines como CRDs de Kubernetes. El cluster es tanto el entorno de ejecución como la capa de orquestación.

### Tekton frente a otras plataformas de CI/CD

| Característica | Tekton | Jenkins | GitHub Actions | GitLab CI |
|---------|--------|---------|----------------|-----------|
| **Entorno de ejecución** | Nativo de Kubernetes (CRDs) | Controlador basado en JVM | Runners alojados en GitHub / autoalojados | Runners alojados en GitLab / autoalojados |
| **Definición de Pipeline** | YAML de Kubernetes | Groovy (Jenkinsfile) | YAML de GitHub | YAML de GitLab |
| **Escalabilidad** | Escala con Kubernetes (Pod por TaskRun) | Requiere gestión de agentes | Autoescalado de runners | Autoescalado de runners |
| **Portabilidad** | Cualquier cluster Kubernetes | Cualquier servidor con JVM | Ecosistema GitHub | Ecosistema GitLab |
| **Seguridad de cadena de suministro** | Tekton Chains (SLSA, Sigstore) | Requiere plugins | Atestaciones de artefactos | Escaneo de dependencias |
| **Gestión de eventos** | Tekton Triggers (webhooks, CEL) | Webhook + plugins | Eventos nativos de GitHub | Eventos nativos de GitLab |
| **UI/Dashboard** | Tekton Dashboard (opcional) | Jenkins UI (integrada) | GitHub UI (integrada) | GitLab UI (integrada) |
| **Gestión de secretos** | Kubernetes Secrets, IRSA, CSI driver | Jenkins Credentials | GitHub Secrets | GitLab CI Variables |
| **Curva de aprendizaje** | Moderada (requiere conocimiento de Kubernetes) | Alta (Groovy, ecosistema de plugins) | Baja (YAML familiar) | Baja (YAML familiar) |
| **Costo** | Gratis (solo cómputo) | Gratis (mantenimiento de infraestructura) | Facturación por minuto (alojado) | Facturación por minuto (alojado) |

### Objetivos de aprendizaje

Después de completar esta guía, podrás:

- Comprender la arquitectura de Tekton y cómo sus CRDs se asignan a conceptos de CI/CD
- Instalar y configurar Tekton Pipelines, Triggers, Dashboard y Chains en Amazon EKS
- Crear Tasks reutilizables con composición de Steps, ejecución de scripts, Results y sidecars
- Construir Pipelines de varias etapas con ejecución paralela, lógica condicional y bloques finally
- Configurar disparadores automáticos de pipelines basados en webhooks usando Tekton Triggers
- Implementar seguridad de cadena de suministro con Tekton Chains, incluida la firma de imágenes OCI y la procedencia SLSA
- Integrar Tekton (CI) con ArgoCD (CD) para una arquitectura CI/CD completa basada en GitOps
- Operar Tekton en producción con políticas de limpieza, monitoreo y estrategias de solución de problemas

---

## 1. Arquitectura de Tekton

Tekton extiende la API de Kubernetes con un conjunto de Custom Resource Definitions (CRDs) que modelan conceptos de CI/CD. El controlador de Tekton observa estas CRDs y reconcilia el estado deseado en Pods y containers.

### 1.1 CRDs principales

```mermaid
graph TB
    subgraph "Tekton CRD Hierarchy"
        Pipeline["Pipeline<br/>(Defines ordered Tasks)"]
        PipelineRun["PipelineRun<br/>(Executes a Pipeline)"]
        Task["Task<br/>(Defines Steps)"]
        TaskRun["TaskRun<br/>(Executes a Task)"]
        Step["Step<br/>(Single container action)"]
        Workspace["Workspace<br/>(Shared volume)"]
        Result["Result<br/>(Output value)"]
    end

    PipelineRun -->|"creates"| TaskRun
    PipelineRun -->|"references"| Pipeline
    Pipeline -->|"contains"| Task
    TaskRun -->|"references"| Task
    Task -->|"contains"| Step
    Task -->|"declares"| Workspace
    Task -->|"produces"| Result
    Pipeline -->|"declares"| Workspace

    subgraph "Kubernetes Resources"
        Pod["Pod"]
        Container["Container"]
        PVC["PersistentVolumeClaim"]
    end

    TaskRun -->|"creates"| Pod
    Step -->|"maps to"| Container
    Workspace -->|"backed by"| PVC
```

**Task**: Una unidad de trabajo reutilizable y parametrizada. Cada Task define uno o más Steps que se ejecutan secuencialmente en containers dentro de un único Pod. Las Tasks también declaran Workspaces (para datos compartidos) y Results (para valores de salida).

**TaskRun**: Una instanciación de una Task con valores de parámetros concretos y bindings de workspace. Crear un TaskRun hace que el controlador levante un Pod que ejecuta los Steps de la Task.

**Pipeline**: Una colección ordenada de Tasks. Los Pipelines definen el orden de ejecución (secuencial, paralelo o basado en DAG), el paso de parámetros entre Tasks, la ejecución condicional (expresiones when) y bloques finally para limpieza.

**PipelineRun**: Una instanciación de un Pipeline. Crear un PipelineRun hace que el controlador cree TaskRuns para cada Task del Pipeline.

**Workspace**: Un mecanismo para compartir datos entre Steps (dentro de una Task) o entre Tasks (dentro de un Pipeline). Los Workspaces pueden estar respaldados por PersistentVolumeClaims, ConfigMaps, Secrets o volúmenes emptyDir.

**Result**: Un valor string producido por una Task que puede ser consumido por Tasks posteriores en un Pipeline. Los Results se escriben en `/tekton/results/<name>` y se almacenan en el estado del TaskRun.

### 1.2 Arquitectura del controlador

```mermaid
graph LR
    subgraph "Tekton Components"
        Controller["tekton-pipelines-controller<br/>(Reconciliation loop)"]
        Webhook["tekton-pipelines-webhook<br/>(Admission + validation)"]
        Chains["tekton-chains-controller<br/>(Signing + attestation)"]
        Triggers["tekton-triggers-controller<br/>(Event processing)"]
        Dashboard["tekton-dashboard<br/>(Web UI)"]
    end

    subgraph "Kubernetes API Server"
        API["kube-apiserver"]
    end

    subgraph "Storage"
        ETCD["etcd<br/>(CRD state)"]
        OCI["OCI Registry<br/>(Signed images)"]
        S3["S3 / Cloud Storage<br/>(Logs, artifacts)"]
    end

    API --> ETCD
    Controller -->|"watches CRDs"| API
    Webhook -->|"validates CRDs"| API
    Chains -->|"watches TaskRuns"| API
    Chains -->|"signs + attests"| OCI
    Triggers -->|"creates PipelineRuns"| API
    Dashboard -->|"reads CRDs"| API

    User["User / Webhook"] -->|"POST event"| Triggers
    User -->|"kubectl apply"| API
```

**tekton-pipelines-controller**: El controlador de reconciliación principal. Observa nuevos recursos PipelineRun y TaskRun, crea Pods para la ejecución, monitorea la finalización de containers, propaga resultados y actualiza el estado.

**tekton-pipelines-webhook**: Un admission webhook que valida y muta las CRDs de Tekton antes de que se persistan. Exige la corrección del esquema y aplica valores predeterminados.

**tekton-chains-controller**: Un controlador separado que observa las finalizaciones de TaskRun y firma automáticamente imágenes OCI, genera atestaciones de procedencia SLSA y las almacena en registries OCI o logs de transparencia.

**tekton-triggers-controller**: Procesa eventos webhook entrantes (desde GitHub, GitLab, etc.), evalúa interceptores y expresiones CEL, y crea recursos PipelineRun basados en definiciones TriggerTemplate.

**tekton-dashboard**: Una UI web opcional para ver PipelineRuns, TaskRuns, logs y recursos del cluster.

### 1.3 Tekton Chains y seguridad de cadena de suministro

Tekton Chains es un componente dedicado a la seguridad de la cadena de suministro de software. Cuando un TaskRun se completa, Chains automáticamente:

1. **Firma imágenes OCI** producidas por el TaskRun usando Cosign (Sigstore)
2. **Genera procedencia SLSA** con atestaciones que registran qué se construyó, desde qué fuente y usando qué builder
3. **Almacena atestaciones** en el OCI registry como firmas de imagen o en logs de transparencia (Rekor)
4. **Produce metadatos de atestación in-toto** que vinculan los materiales fuente con las salidas de build

Esto proporciona registros a prueba de manipulación que los consumidores posteriores (admission controllers, policy engines) pueden verificar antes de desplegar imágenes.

---

## 2. Instalación y configuración en EKS

### 2.1 Prerrequisitos

Antes de instalar Tekton, asegúrate de que tu cluster EKS cumpla los siguientes requisitos:

```bash
# Verify cluster version (1.28+)
kubectl version --short

# Verify cluster has sufficient capacity
# Tekton controllers need ~500m CPU and ~512Mi memory total
kubectl top nodes

# Ensure the cluster has a default StorageClass for Workspaces
kubectl get storageclass
```

### 2.2 Instalación de Tekton Pipelines

```bash
# Install Tekton Pipelines (core)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/previous/v0.62.2/release.yaml

# Verify installation
kubectl get pods -n tekton-pipelines --watch
```

Salida esperada:

```
NAME                                           READY   STATUS    RESTARTS   AGE
tekton-pipelines-controller-7f6d5b8bc4-xxxxx   1/1     Running   0          30s
tekton-pipelines-webhook-6c9b5d7d8f-xxxxx      1/1     Running   0          30s
```

Configura los feature flags de Tekton Pipelines:

```yaml
# tekton-pipelines-feature-flags.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
  namespace: tekton-pipelines
data:
  # Enable Step-level resource requirements
  disable-affinity-assistant: "true"
  # Enable alpha API features (required for some Chains features)
  enable-api-fields: "beta"
  # Set result extraction method
  results-from: "termination-message"
  # Enable Workspace isolation
  running-in-environment-with-injected-sidecars: "true"
  # Set default timeout (1 hour)
  default-timeout-minutes: "60"
  # Enable larger results (4096 bytes max by default)
  max-result-size: "4096"
  # Enable Kubernetes events for PipelineRuns
  send-cloudevents-for-runs: "false"
```

```bash
kubectl apply -f tekton-pipelines-feature-flags.yaml
```

### 2.3 Instalación de Tekton Triggers

```bash
# Install Tekton Triggers
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/release.yaml

# Install Tekton Triggers Interceptors (required for GitHub/GitLab webhooks)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/interceptors.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-triggers
```

### 2.4 Instalación de Tekton Dashboard

```bash
# Install Tekton Dashboard (read-only mode for production)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/previous/v0.46.0/release-full.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-dashboard
```

Expón el Dashboard mediante un Ingress ALB interno:

```yaml
# tekton-dashboard-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tekton-dashboard
  namespace: tekton-pipelines
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
    alb.ingress.kubernetes.io/group.name: internal-services
spec:
  ingressClassName: alb
  rules:
    - host: tekton.internal.mycompany.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: tekton-dashboard
                port:
                  number: 9097
```

### 2.5 Instalación de Tekton Chains

```bash
# Install Tekton Chains
kubectl apply --filename https://storage.googleapis.com/tekton-releases/chains/previous/v0.22.1/release.yaml

# Verify installation
kubectl get pods -n tekton-chains
```

### 2.6 Configuración de IRSA para ECR y S3

Las Tekton Tasks que envían imágenes a ECR o suben artefactos a S3 requieren permisos IAM. Usa IAM Roles for Service Accounts (IRSA) para conceder acceso con privilegios mínimos.

```bash
# Create OIDC provider (skip if already configured)
eksctl utils associate-iam-oidc-provider \
  --cluster my-eks-cluster \
  --region us-east-1 \
  --approve
```

**Política IAM para push a ECR:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository",
        "ecr:TagResource"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/*"
    }
  ]
}
```

**Política IAM para carga de artefactos a S3:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-tekton-artifacts",
        "arn:aws:s3:::my-tekton-artifacts/*"
      ]
    }
  ]
}
```

Crea el ServiceAccount anotado con IRSA:

```bash
# Create IAM role and ServiceAccount for Tekton builds
eksctl create iamserviceaccount \
  --cluster my-eks-cluster \
  --namespace tekton-builds \
  --name tekton-build-sa \
  --attach-policy-arn arn:aws:iam::123456789012:policy/TektonECRPush \
  --attach-policy-arn arn:aws:iam::123456789012:policy/TektonS3Artifacts \
  --approve \
  --override-existing-serviceaccounts
```

Verifica la anotación:

```bash
kubectl get sa tekton-build-sa -n tekton-builds -o yaml
# Should show: eks.amazonaws.com/role-arn annotation
```

---

## 3. Creación de Tasks

Las Tasks son los bloques de construcción fundamentales en Tekton. Una Task bien diseñada es reutilizable, parametrizada y produce resultados significativos.

### 3.1 Composición de Steps

Cada Step en una Task se ejecuta como un container dentro del mismo Pod. Los Steps se ejecutan secuencialmente y comparten el mismo namespace de red y volúmenes Workspace.

```yaml
# task-go-build.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: go-build
  labels:
    app.kubernetes.io/version: "1.0"
  annotations:
    tekton.dev/pipelines.minVersion: "0.62.0"
    tekton.dev/categories: Build
    tekton.dev/tags: go, build
    tekton.dev/displayName: "Go Build and Test"
spec:
  description: >
    Builds and tests a Go application, producing a binary artifact.
  params:
    - name: package
      type: string
      description: "Go package path to build"
      default: "./cmd/server"
    - name: go-version
      type: string
      description: "Go version to use"
      default: "1.22"
    - name: goos
      type: string
      description: "Target operating system"
      default: "linux"
    - name: goarch
      type: string
      description: "Target architecture"
      default: "amd64"
    - name: flags
      type: string
      description: "Go build flags"
      default: "-v"
    - name: ldflags
      type: string
      description: "Go linker flags"
      default: ""
  workspaces:
    - name: source
      description: "Workspace containing Go source code"
    - name: go-cache
      description: "Go module and build cache"
      optional: true
  results:
    - name: binary-path
      description: "Path to the built binary"
    - name: test-passed
      description: "Whether tests passed (true/false)"
    - name: binary-sha256
      description: "SHA256 hash of the built binary"
  steps:
    - name: unit-test
      image: golang:$(params.go-version)
      workingDir: $(workspaces.source.path)
      env:
        - name: GOMODCACHE
          value: "$(workspaces.go-cache.path)/mod"
        - name: GOCACHE
          value: "$(workspaces.go-cache.path)/build"
      script: |
        #!/usr/bin/env bash
        set -euo pipefail
        echo "Running unit tests..."
        go test -race -coverprofile=coverage.out ./...
        COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}')
        echo "Test coverage: ${COVERAGE}"
        printf "true" > $(results.test-passed.path)

    - name: build
      image: golang:$(params.go-version)
      workingDir: $(workspaces.source.path)
      env:
        - name: GOOS
          value: "$(params.goos)"
        - name: GOARCH
          value: "$(params.goarch)"
        - name: CGO_ENABLED
          value: "0"
        - name: GOMODCACHE
          value: "$(workspaces.go-cache.path)/mod"
        - name: GOCACHE
          value: "$(workspaces.go-cache.path)/build"
      script: |
        #!/usr/bin/env bash
        set -euo pipefail
        OUTPUT_PATH="$(workspaces.source.path)/output/app"
        mkdir -p "$(dirname ${OUTPUT_PATH})"

        echo "Building $(params.package)..."
        go build $(params.flags) \
          -ldflags "$(params.ldflags)" \
          -o "${OUTPUT_PATH}" \
          "$(params.package)"

        HASH=$(sha256sum "${OUTPUT_PATH}" | awk '{print $1}')
        echo "Binary built: ${OUTPUT_PATH} (SHA256: ${HASH})"

        printf "%s" "${OUTPUT_PATH}" > $(results.binary-path.path)
        printf "%s" "${HASH}" > $(results.binary-sha256.path)
```

### 3.2 Ejecución de scripts

Los Steps pueden ejecutar scripts inline para lógica compleja. El campo `script` acepta cualquier intérprete disponible en la imagen del container.

```yaml
# task-security-scan.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: trivy-image-scan
spec:
  description: "Scans a container image for vulnerabilities using Trivy"
  params:
    - name: image-url
      type: string
      description: "Full image URL including tag or digest"
    - name: severity-threshold
      type: string
      description: "Minimum severity to report (CRITICAL, HIGH, MEDIUM, LOW)"
      default: "HIGH,CRITICAL"
    - name: exit-code
      type: string
      description: "Exit code when vulnerabilities found (0=warn, 1=fail)"
      default: "1"
  workspaces:
    - name: trivy-cache
      description: "Cache for Trivy vulnerability database"
      optional: true
  results:
    - name: vulnerability-count
      description: "Number of vulnerabilities found"
    - name: scan-result
      description: "PASS or FAIL"
  steps:
    - name: scan
      image: aquasec/trivy:0.53.0
      env:
        - name: TRIVY_CACHE_DIR
          value: "$(workspaces.trivy-cache.path)"
      script: |
        #!/usr/bin/env sh
        set -uo pipefail

        echo "Scanning image: $(params.image-url)"
        echo "Severity threshold: $(params.severity-threshold)"

        trivy image \
          --severity "$(params.severity-threshold)" \
          --format json \
          --output /tmp/trivy-report.json \
          --exit-code 0 \
          "$(params.image-url)"

        VULN_COUNT=$(cat /tmp/trivy-report.json | \
          grep -o '"VulnerabilityID"' | wc -l || echo "0")

        printf "%s" "${VULN_COUNT}" > $(results.vulnerability-count.path)

        if [ "${VULN_COUNT}" -gt "0" ]; then
          echo "Found ${VULN_COUNT} vulnerabilities"
          trivy image \
            --severity "$(params.severity-threshold)" \
            --format table \
            "$(params.image-url)"
          printf "FAIL" > $(results.scan-result.path)
          exit $(params.exit-code)
        else
          echo "No vulnerabilities found"
          printf "PASS" > $(results.scan-result.path)
        fi
```

### 3.3 Paso de Results entre Tasks

Los Results de una Task pueden ser referenciados por Tasks posteriores en un Pipeline usando la sintaxis `$(tasks.<taskName>.results.<resultName>)`. Los Results están limitados a 4096 bytes de forma predeterminada.

```yaml
# task-generate-tag.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: generate-image-tag
spec:
  description: "Generates a deterministic image tag from git commit and timestamp"
  params:
    - name: image-base
      type: string
      description: "Base image URL (registry/repository)"
  workspaces:
    - name: source
      description: "Workspace containing git repository"
  results:
    - name: image-tag
      description: "Generated image tag"
    - name: image-url
      description: "Full image URL with tag"
    - name: short-sha
      description: "Short git commit SHA"
  steps:
    - name: generate
      image: alpine/git:2.43.0
      workingDir: $(workspaces.source.path)
      script: |
        #!/usr/bin/env sh
        set -euo pipefail
        SHORT_SHA=$(git rev-parse --short HEAD)
        TIMESTAMP=$(date +%Y%m%d-%H%M%S)
        TAG="${SHORT_SHA}-${TIMESTAMP}"

        printf "%s" "${TAG}" > $(results.image-tag.path)
        printf "%s" "$(params.image-base):${TAG}" > $(results.image-url.path)
        printf "%s" "${SHORT_SHA}" > $(results.short-sha.path)

        echo "Generated tag: ${TAG}"
        echo "Full image URL: $(params.image-base):${TAG}"
```

### 3.4 Sidecars

Los sidecars son containers de larga duración que se ejecutan junto a los Steps, útiles para servicios como Docker daemon, bases de datos para pruebas de integración o cachés.

```yaml
# task-integration-test.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: integration-test-with-postgres
spec:
  description: "Runs integration tests against a PostgreSQL sidecar"
  params:
    - name: go-version
      type: string
      default: "1.22"
    - name: postgres-version
      type: string
      default: "16"
    - name: test-packages
      type: string
      default: "./internal/integration/..."
  workspaces:
    - name: source
  sidecars:
    - name: postgres
      image: postgres:$(params.postgres-version)
      env:
        - name: POSTGRES_DB
          value: "testdb"
        - name: POSTGRES_USER
          value: "testuser"
        - name: POSTGRES_PASSWORD
          value: "testpassword"
      ports:
        - containerPort: 5432
      readinessProbe:
        exec:
          command: ["pg_isready", "-U", "testuser", "-d", "testdb"]
        initialDelaySeconds: 5
        periodSeconds: 2
  steps:
    - name: wait-for-postgres
      image: postgres:$(params.postgres-version)
      script: |
        #!/usr/bin/env bash
        set -euo pipefail
        echo "Waiting for PostgreSQL to become ready..."
        for i in $(seq 1 30); do
          if pg_isready -h localhost -U testuser -d testdb; then
            echo "PostgreSQL is ready"
            exit 0
          fi
          sleep 2
        done
        echo "PostgreSQL failed to start"
        exit 1

    - name: run-tests
      image: golang:$(params.go-version)
      workingDir: $(workspaces.source.path)
      env:
        - name: DATABASE_URL
          value: "postgres://testuser:testpassword@localhost:5432/testdb?sslmode=disable"
      script: |
        #!/usr/bin/env bash
        set -euo pipefail
        echo "Running integration tests..."
        go test -v -count=1 -timeout 10m $(params.test-packages)
        echo "Integration tests passed"
```

### 3.5 Tasks reutilizables de Tekton Hub

[Tekton Hub](https://hub.tekton.dev) proporciona un catálogo de Tasks reutilizables mantenidas por la comunidad. Instálalas directamente en tu cluster:

```bash
# Install the git-clone Task (official catalog)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.9/git-clone.yaml

# Install the kaniko Task (for building images without Docker daemon)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kaniko/0.7/kaniko.yaml

# Install the kubernetes-actions Task (for kubectl operations)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kubernetes-actions/0.2/kubernetes-actions.yaml
```

Verifica las Tasks instaladas:

```bash
kubectl get tasks -n tekton-builds
```

### 3.6 Task completa de build-push (Kaniko + ECR)

Esta Task construye una imagen de container usando Kaniko (no se requiere Docker daemon) y la envía a Amazon ECR:

```yaml
# task-kaniko-ecr-build.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: kaniko-ecr-build
spec:
  description: >
    Builds a container image with Kaniko and pushes to Amazon ECR.
    Requires an IRSA-annotated ServiceAccount with ECR push permissions.
  params:
    - name: image
      type: string
      description: "Full ECR image URL (without tag)"
    - name: tag
      type: string
      description: "Image tag"
      default: "latest"
    - name: dockerfile
      type: string
      description: "Path to Dockerfile relative to workspace root"
      default: "Dockerfile"
    - name: context
      type: string
      description: "Build context directory relative to workspace root"
      default: "."
    - name: build-args
      type: array
      description: "List of build arguments"
      default: []
    - name: cache-repo
      type: string
      description: "ECR repository for layer caching (empty to disable)"
      default: ""
  workspaces:
    - name: source
      description: "Workspace containing Dockerfile and source code"
    - name: dockerconfig
      description: "Docker config.json for registry authentication"
      optional: true
  results:
    - name: image-url
      description: "Full image URL with tag"
    - name: image-digest
      description: "Image digest (sha256)"
  steps:
    - name: ecr-login
      image: amazon/aws-cli:2.17.0
      script: |
        #!/usr/bin/env bash
        set -euo pipefail
        REGION=$(echo "$(params.image)" | cut -d'.' -f4)
        ACCOUNT=$(echo "$(params.image)" | cut -d'.' -f1)

        echo "Logging into ECR: ${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
        aws ecr get-login-password --region "${REGION}" | \
          docker-credential-ecr-login login \
            --username AWS \
            --password-stdin \
            "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

        mkdir -p /kaniko/.docker
        aws ecr get-login-password --region "${REGION}" | \
          python3 -c "
        import sys, json, base64
        password = sys.stdin.read().strip()
        auth = base64.b64encode(f'AWS:{password}'.encode()).decode()
        registry = '${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com'
        config = {'auths': {registry: {'auth': auth}}}
        json.dump(config, open('/kaniko/.docker/config.json', 'w'))
        "
      volumeMounts:
        - name: kaniko-config
          mountPath: /kaniko/.docker

    - name: build-and-push
      image: gcr.io/kaniko-project/executor:v1.23.2
      args:
        - --dockerfile=$(workspaces.source.path)/$(params.dockerfile)
        - --context=$(workspaces.source.path)/$(params.context)
        - --destination=$(params.image):$(params.tag)
        - --digest-file=$(results.image-digest.path)
        - --snapshotMode=redo
        - --compressed-caching=false
        - --use-new-run
      volumeMounts:
        - name: kaniko-config
          mountPath: /kaniko/.docker
  volumes:
    - name: kaniko-config
      emptyDir: {}
  stepTemplate:
    securityContext:
      runAsUser: 0
```

---

## 4. Construcción de Pipelines

Los Pipelines orquestan múltiples Tasks en un grafo acíclico dirigido (DAG). Las Tasks pueden ejecutarse en paralelo, de forma condicional o secuencialmente según dependencias explícitas.

### 4.1 Ordenamiento de Tasks y ejecución paralela

```mermaid
graph LR
    Clone["git-clone"] --> Lint["lint"]
    Clone --> Test["unit-test"]
    Lint --> Build["build-image"]
    Test --> Build
    Build --> Scan["security-scan"]
    Scan --> Deploy["deploy"]

    style Clone fill:#e1f5fe
    style Lint fill:#fff3e0
    style Test fill:#fff3e0
    style Build fill:#e8f5e9
    style Scan fill:#fce4ec
    style Deploy fill:#f3e5f5
```

En el diagrama anterior, `lint` y `unit-test` se ejecutan en paralelo después de que `git-clone` se completa. `build-image` espera a que ambas tengan éxito. Esto se logra usando `runAfter` en la especificación del Pipeline.

### 4.2 Ejecución condicional con expresiones When

Las expresiones when permiten omitir Tasks según valores de parámetros o Results de Tasks anteriores:

```yaml
# When expression examples (used within Pipeline tasks)
when:
  - input: "$(params.run-security-scan)"
    operator: in
    values: ["true"]
  - input: "$(tasks.unit-test.results.test-passed)"
    operator: in
    values: ["true"]
```

### 4.3 Tasks finally

Las Tasks finally siempre se ejecutan independientemente del éxito o fallo del Pipeline, de forma similar a `try/finally` en código. Son ideales para limpieza, notificaciones e informes de estado.

### 4.4 Pipeline CI/CD completo

El siguiente Pipeline implementa un flujo de trabajo CI/CD completo: clonar, probar, construir, enviar, escanear y desplegar.

```yaml
# pipeline-ci-cd.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: application-ci-cd
  labels:
    app.kubernetes.io/version: "1.0"
spec:
  description: >
    Complete CI/CD pipeline: clones source, runs tests, builds and pushes
    a container image to ECR, scans for vulnerabilities, and deploys to
    the target environment.
  params:
    - name: git-url
      type: string
      description: "Git repository URL"
    - name: git-revision
      type: string
      description: "Git revision (branch, tag, or commit SHA)"
      default: "main"
    - name: image-registry
      type: string
      description: "ECR registry URL (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com)"
    - name: image-name
      type: string
      description: "Image repository name"
    - name: dockerfile
      type: string
      description: "Path to Dockerfile"
      default: "Dockerfile"
    - name: deploy-environment
      type: string
      description: "Target deployment environment"
      default: "staging"
    - name: deploy-namespace
      type: string
      description: "Kubernetes namespace to deploy into"
      default: "staging"
    - name: run-security-scan
      type: string
      description: "Whether to run security scan (true/false)"
      default: "true"

  workspaces:
    - name: shared-workspace
      description: "Shared workspace for source code and build artifacts"
    - name: git-credentials
      description: "Git credentials (SSH key or token)"
      optional: true
    - name: docker-credentials
      description: "Docker registry credentials"
      optional: true

  tasks:
    # ---- Stage 1: Clone ----
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: "$(params.git-url)"
        - name: revision
          value: "$(params.git-revision)"
        - name: deleteExisting
          value: "true"
      workspaces:
        - name: output
          workspace: shared-workspace
        - name: ssh-directory
          workspace: git-credentials

    # ---- Stage 2: Test + Lint (parallel) ----
    - name: unit-test
      taskRef:
        name: go-build
      runAfter:
        - clone
      params:
        - name: package
          value: "./..."
      workspaces:
        - name: source
          workspace: shared-workspace

    - name: lint
      taskRef:
        name: golangci-lint
      runAfter:
        - clone
      params:
        - name: flags
          value: "--timeout=5m"
      workspaces:
        - name: source
          workspace: shared-workspace

    # ---- Stage 3: Generate Tag ----
    - name: generate-tag
      taskRef:
        name: generate-image-tag
      runAfter:
        - clone
      params:
        - name: image-base
          value: "$(params.image-registry)/$(params.image-name)"
      workspaces:
        - name: source
          workspace: shared-workspace

    # ---- Stage 4: Build and Push ----
    - name: build-push
      taskRef:
        name: kaniko-ecr-build
      runAfter:
        - unit-test
        - lint
        - generate-tag
      params:
        - name: image
          value: "$(params.image-registry)/$(params.image-name)"
        - name: tag
          value: "$(tasks.generate-tag.results.image-tag)"
        - name: dockerfile
          value: "$(params.dockerfile)"
      workspaces:
        - name: source
          workspace: shared-workspace

    # ---- Stage 5: Security Scan (conditional) ----
    - name: security-scan
      taskRef:
        name: trivy-image-scan
      runAfter:
        - build-push
      when:
        - input: "$(params.run-security-scan)"
          operator: in
          values: ["true"]
      params:
        - name: image-url
          value: "$(tasks.build-push.results.image-url)"
        - name: severity-threshold
          value: "HIGH,CRITICAL"
        - name: exit-code
          value: "1"

    # ---- Stage 6: Deploy ----
    - name: deploy
      taskRef:
        name: kubernetes-deploy
      runAfter:
        - security-scan
      params:
        - name: image-url
          value: "$(tasks.build-push.results.image-url)"
        - name: namespace
          value: "$(params.deploy-namespace)"
        - name: environment
          value: "$(params.deploy-environment)"
      workspaces:
        - name: source
          workspace: shared-workspace

  finally:
    # ---- Cleanup and Notification ----
    - name: notify-slack
      taskRef:
        name: send-slack-notification
      params:
        - name: webhook-url-secret
          value: "slack-webhook"
        - name: webhook-url-secret-key
          value: "url"
        - name: message
          value: >
            Pipeline $(context.pipelineRun.name) for
            $(params.image-name):$(tasks.generate-tag.results.image-tag)
            completed with status: $(tasks.status)

    - name: cleanup-workspace
      taskRef:
        name: cleanup
      workspaces:
        - name: source
          workspace: shared-workspace
```

### 4.5 Ejecución del Pipeline

Crea un PipelineRun para ejecutar el Pipeline:

```yaml
# pipelinerun-example.yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: app-ci-cd-run-
  namespace: tekton-builds
  labels:
    tekton.dev/pipeline: application-ci-cd
    app: my-service
spec:
  pipelineRef:
    name: application-ci-cd
  params:
    - name: git-url
      value: "git@github.com:myorg/my-service.git"
    - name: git-revision
      value: "main"
    - name: image-registry
      value: "123456789012.dkr.ecr.us-east-1.amazonaws.com"
    - name: image-name
      value: "my-service"
    - name: deploy-environment
      value: "staging"
    - name: deploy-namespace
      value: "staging"
  workspaces:
    - name: shared-workspace
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 5Gi
          storageClassName: gp3
    - name: git-credentials
      secret:
        secretName: git-ssh-key
  taskRunTemplate:
    serviceAccountName: tekton-build-sa
  timeouts:
    pipeline: "1h0m0s"
    tasks: "45m0s"
    finally: "15m0s"
```

```bash
# Create the PipelineRun
kubectl create -f pipelinerun-example.yaml

# Watch the execution
kubectl get pipelineruns -n tekton-builds --watch

# View logs for a specific TaskRun
kubectl logs -n tekton-builds -l tekton.dev/pipelineRun=app-ci-cd-run-xxxxx --all-containers -f
```

---

## 5. Tekton Triggers

Tekton Triggers permite la ejecución automática de Pipelines en respuesta a eventos externos como pushes de Git, pull requests o cualquier evento basado en webhook.

### 5.1 Arquitectura de Triggers

```mermaid
graph LR
    GH["GitHub Webhook"] -->|"POST /hooks"| EL["EventListener<br/>(Service + Pod)"]
    EL --> I["Interceptor<br/>(GitHub validation)"]
    I --> CEL["CEL Filter<br/>(branch, action)"]
    CEL --> TB["TriggerBinding<br/>(Extract params)"]
    TB --> TT["TriggerTemplate<br/>(PipelineRun template)"]
    TT -->|"creates"| PR["PipelineRun"]

    style GH fill:#e1f5fe
    style EL fill:#fff3e0
    style I fill:#fce4ec
    style CEL fill:#fce4ec
    style TB fill:#e8f5e9
    style TT fill:#e8f5e9
    style PR fill:#f3e5f5
```

**EventListener**: Un Service Kubernetes que recibe solicitudes HTTP webhook entrantes y las enruta a través de Triggers.

**TriggerBinding**: Extrae valores de parámetros del payload del evento entrante usando expresiones JSONPath.

**TriggerTemplate**: Una plantilla para crear recursos Tekton (normalmente PipelineRuns) con parámetros poblados desde el TriggerBinding.

**Interceptor**: Un paso de procesamiento que valida, filtra y transforma eventos entrantes. Los interceptores integrados incluyen GitHub (validación de firma de webhook), GitLab, Bitbucket y CEL (Common Expression Language para filtrado).

### 5.2 TriggerBinding

```yaml
# triggerbinding-github-push.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-push-binding
  namespace: tekton-builds
spec:
  params:
    - name: git-url
      value: "$(body.repository.ssh_url)"
    - name: git-revision
      value: "$(body.after)"
    - name: git-branch
      value: "$(body.ref)"
    - name: repository-name
      value: "$(body.repository.name)"
    - name: repository-full-name
      value: "$(body.repository.full_name)"
    - name: pusher-name
      value: "$(body.pusher.name)"
    - name: commit-message
      value: "$(body.head_commit.message)"
---
# triggerbinding-github-pr.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-pr-binding
  namespace: tekton-builds
spec:
  params:
    - name: git-url
      value: "$(body.pull_request.head.repo.ssh_url)"
    - name: git-revision
      value: "$(body.pull_request.head.sha)"
    - name: git-branch
      value: "$(body.pull_request.head.ref)"
    - name: pr-number
      value: "$(body.pull_request.number)"
    - name: pr-title
      value: "$(body.pull_request.title)"
    - name: repository-name
      value: "$(body.repository.name)"
    - name: action
      value: "$(body.action)"
```

### 5.3 TriggerTemplate

```yaml
# triggertemplate-ci-cd.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: ci-cd-trigger-template
  namespace: tekton-builds
spec:
  params:
    - name: git-url
      description: "Git repository URL"
    - name: git-revision
      description: "Git commit SHA"
    - name: git-branch
      description: "Git branch reference"
    - name: repository-name
      description: "Repository name"
  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: "$(tt.params.repository-name)-run-"
        namespace: tekton-builds
        labels:
          tekton.dev/pipeline: application-ci-cd
          triggers.tekton.dev/trigger: github-push
          app: "$(tt.params.repository-name)"
        annotations:
          tekton.dev/git-branch: "$(tt.params.git-branch)"
      spec:
        pipelineRef:
          name: application-ci-cd
        params:
          - name: git-url
            value: "$(tt.params.git-url)"
          - name: git-revision
            value: "$(tt.params.git-revision)"
          - name: image-registry
            value: "123456789012.dkr.ecr.us-east-1.amazonaws.com"
          - name: image-name
            value: "$(tt.params.repository-name)"
          - name: deploy-environment
            value: "staging"
          - name: deploy-namespace
            value: "staging"
        workspaces:
          - name: shared-workspace
            volumeClaimTemplate:
              spec:
                accessModes:
                  - ReadWriteOnce
                resources:
                  requests:
                    storage: 5Gi
                storageClassName: gp3
          - name: git-credentials
            secret:
              secretName: git-ssh-key
        taskRunTemplate:
          serviceAccountName: tekton-build-sa
        timeouts:
          pipeline: "1h0m0s"
```

### 5.4 EventListener con interceptores

```yaml
# eventlistener-github.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-listener
  namespace: tekton-builds
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    # Trigger 1: Push to main branch
    - name: github-push-main
      interceptors:
        - ref:
            name: "github"
          params:
            - name: "secretRef"
              value:
                secretName: github-webhook-secret
                secretKey: token
            - name: "eventTypes"
              value: ["push"]
        - ref:
            name: "cel"
          params:
            - name: "filter"
              value: >
                body.ref == 'refs/heads/main' &&
                !body.head_commit.message.contains('[skip ci]')
            - name: "overlays"
              value:
                - key: truncated-sha
                  expression: "body.after.truncate(7)"
      bindings:
        - ref: github-push-binding
      template:
        ref: ci-cd-trigger-template

    # Trigger 2: Pull request opened or synchronized
    - name: github-pr
      interceptors:
        - ref:
            name: "github"
          params:
            - name: "secretRef"
              value:
                secretName: github-webhook-secret
                secretKey: token
            - name: "eventTypes"
              value: ["pull_request"]
        - ref:
            name: "cel"
          params:
            - name: "filter"
              value: >
                body.action in ['opened', 'synchronize'] &&
                !body.pull_request.draft
      bindings:
        - ref: github-pr-binding
      template:
        ref: ci-cd-trigger-template

  resources:
    kubernetesResource:
      spec:
        template:
          spec:
            serviceAccountName: tekton-triggers-sa
            containers: []
          metadata:
            labels:
              app: tekton-triggers-eventlistener
---
# ServiceAccount for Tekton Triggers
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tekton-triggers-sa
  namespace: tekton-builds
---
# RBAC: Allow Triggers to create PipelineRuns
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tekton-triggers-role
  namespace: tekton-builds
rules:
  - apiGroups: ["triggers.tekton.dev"]
    resources: ["eventlisteners", "triggerbindings", "triggertemplates", "triggers"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["tekton.dev"]
    resources: ["pipelineresources", "pipelineruns", "taskruns"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tekton-triggers-rolebinding
  namespace: tekton-builds
subjects:
  - kind: ServiceAccount
    name: tekton-triggers-sa
roleRef:
  kind: Role
  name: tekton-triggers-role
  apiGroup: rbac.authorization.k8s.io
```

### 5.5 Exponer EventListener

```yaml
# eventlistener-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tekton-triggers-webhook
  namespace: tekton-builds
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc-123
    alb.ingress.kubernetes.io/healthcheck-path: /live
spec:
  ingressClassName: alb
  rules:
    - host: tekton-hooks.mycompany.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: el-github-listener
                port:
                  number: 8080
```

Configura el webhook en GitHub:

```
Payload URL:    https://tekton-hooks.mycompany.com
Content type:   application/json
Secret:         <same value as github-webhook-secret>
Events:         Pushes, Pull requests
```

### 5.6 Ejemplo de interceptor de GitLab

Para webhooks de GitLab, reemplaza el interceptor de GitHub:

```yaml
interceptors:
  - ref:
      name: "gitlab"
    params:
      - name: "secretRef"
        value:
          secretName: gitlab-webhook-secret
          secretKey: token
      - name: "eventTypes"
        value: ["Push Hook", "Merge Request Hook"]
  - ref:
      name: "cel"
    params:
      - name: "filter"
        value: >
          (header.match('X-Gitlab-Event', 'Push Hook') &&
           body.ref == 'refs/heads/main') ||
          (header.match('X-Gitlab-Event', 'Merge Request Hook') &&
           body.object_attributes.action in ['open', 'update'])
```

---

## 6. Tekton Chains (seguridad de cadena de suministro)

Tekton Chains proporciona seguridad automatizada de cadena de suministro para tus pipelines de CI/CD. Observa las finalizaciones de TaskRun y genera automáticamente atestaciones criptográficas sobre qué se construyó, cómo y a partir de qué fuente.

### 6.1 Cómo funciona Chains

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Git as Git Repository
    participant Tekton as Tekton Pipeline
    participant Chains as Tekton Chains
    participant ECR as Amazon ECR
    participant Rekor as Rekor (Transparency Log)

    Dev->>Git: Push code
    Git->>Tekton: Webhook trigger
    Tekton->>Tekton: Build image (TaskRun)
    Tekton->>ECR: Push image
    Tekton->>Tekton: TaskRun completes
    Chains->>Tekton: Observe TaskRun completion
    Chains->>Chains: Generate SLSA provenance
    Chains->>Chains: Sign with Cosign
    Chains->>ECR: Store signature + attestation
    Chains->>Rekor: Upload to transparency log
    Note over ECR: Image now has:<br/>1. Image layers<br/>2. Cosign signature<br/>3. SLSA provenance attestation
```

### 6.2 Configuración de Chains

```yaml
# tekton-chains-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chains-config
  namespace: tekton-chains
data:
  # Artifact storage (oci = store in OCI registry alongside image)
  artifacts.taskrun.format: "in-toto"
  artifacts.taskrun.storage: "oci"
  artifacts.taskrun.signer: "x509"

  artifacts.oci.format: "simplesigning"
  artifacts.oci.storage: "oci"
  artifacts.oci.signer: "x509"

  # SLSA provenance configuration
  artifacts.pipelinerun.format: "in-toto"
  artifacts.pipelinerun.storage: "oci"
  artifacts.pipelinerun.signer: "x509"

  # Sigstore configuration
  sigstore.fulcio.enabled: "false"
  # For keyless signing with Fulcio (recommended for production):
  # sigstore.fulcio.enabled: "true"
  # sigstore.fulcio.address: "https://fulcio.sigstore.dev"
  # sigstore.rekor.url: "https://rekor.sigstore.dev"

  # Transparency log
  transparency.enabled: "true"
  transparency.url: "https://rekor.sigstore.dev"
```

### 6.3 Configuración de clave de firma

Para firma basada en claves (no keyless), genera un par de claves Cosign y almacénalo como un Kubernetes Secret:

```bash
# Generate a Cosign signing key pair
cosign generate-key-pair k8s://tekton-chains/signing-secrets
```

Esto crea un Secret llamado `signing-secrets` en el namespace `tekton-chains` que contiene la clave privada. La clave pública se envía a `cosign.pub`.

Para entornos de producción que usan AWS KMS:

```bash
# Create a KMS key for signing
aws kms create-key \
  --description "Tekton Chains image signing key" \
  --key-usage SIGN_VERIFY \
  --key-spec ECC_NIST_P256 \
  --tags TagKey=Purpose,TagValue=tekton-chains

# Use KMS key with Cosign
cosign generate-key-pair --kms awskms:///arn:aws:kms:us-east-1:123456789012:key/abc-123
```

Actualiza la configuración de Chains para KMS:

```yaml
# chains-config-kms.yaml (merge with chains-config)
data:
  sigstore.kms: "awskms:///arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

### 6.4 Procedencia SLSA

Tekton Chains genera automáticamente atestaciones de procedencia [SLSA](https://slsa.dev/) (Supply-chain Levels for Software Artifacts). La procedencia registra:

- **Builder**: Qué Tekton Task/Pipeline produjo el artefacto
- **Fuente**: El repositorio git, la rama y el commit
- **Configuración de build**: Los parámetros del Pipeline y los Steps de la Task
- **Materiales**: Artefactos de entrada (código fuente, imágenes base)
- **Salida**: El artefacto construido (digest de imagen)

Verifica la procedencia después de un build:

```bash
# Verify image signature
cosign verify \
  --key cosign.pub \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/my-service:abc1234-20250622-120000

# Verify and view SLSA provenance attestation
cosign verify-attestation \
  --key cosign.pub \
  --type slsaprovenance \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/my-service:abc1234-20250622-120000 | \
  jq -r '.payload' | base64 -d | jq .
```

Ejemplo de salida de procedencia SLSA (abreviado):

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "subject": [
    {
      "name": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-service",
      "digest": {
        "sha256": "a1b2c3d4e5f6..."
      }
    }
  ],
  "predicate": {
    "builder": {
      "id": "https://tekton.dev/chains/v2"
    },
    "buildType": "tekton.dev/v1beta1/TaskRun",
    "invocation": {
      "configSource": {},
      "parameters": {
        "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-service",
        "tag": "abc1234-20250622-120000"
      }
    },
    "buildConfig": {
      "steps": [
        { "entryPoint": "...", "image": "gcr.io/kaniko-project/executor:v1.23.2" }
      ]
    },
    "materials": [
      {
        "uri": "git+https://github.com/myorg/my-service.git",
        "digest": { "sha1": "abc1234..." }
      }
    ]
  }
}
```

### 6.5 Aplicación de políticas con Kyverno

Usa Kyverno para exigir que solo se puedan desplegar imágenes firmadas con procedencia válida:

```yaml
# kyverno-verify-image-signature.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-tekton-chains-signature
  annotations:
    policies.kyverno.io/title: Verify Tekton Chains Image Signature
    policies.kyverno.io/category: Supply Chain Security
    policies.kyverno.io/severity: critical
spec:
  validationFailureAction: Enforce
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-image-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - tekton-pipelines
                - tekton-chains
      verifyImages:
        - imageReferences:
            - "123456789012.dkr.ecr.us-east-1.amazonaws.com/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
          attestations:
            - type: https://slsa.dev/provenance/v0.2
              conditions:
                - all:
                    - key: "{{ builder.id }}"
                      operator: Equals
                      value: "https://tekton.dev/chains/v2"
```

---

## 7. Integración de ArgoCD + Tekton

La arquitectura de producción más efectiva separa CI (build, test, push) de CD (deploy). Tekton gestiona CI mientras ArgoCD gestiona CD mediante GitOps. Esta separación proporciona propiedad clara, escalado independiente y un rastro de auditoría confiable.

### 7.1 Arquitectura de separación CI/CD

```mermaid
graph TB
    subgraph "CI - Tekton"
        Push["Developer Push"] --> Trigger["Tekton Triggers"]
        Trigger --> Pipeline["Tekton Pipeline"]
        Pipeline --> Clone["git-clone"]
        Clone --> Test["unit-test + lint"]
        Test --> Build["kaniko-build"]
        Build --> Scan["trivy-scan"]
        Scan --> Sign["Tekton Chains<br/>(sign + attest)"]
        Sign --> ECR["ECR<br/>(image + signature)"]
    end

    subgraph "Handoff"
        Sign --> UpdateManifest["Update GitOps Repo<br/>(image tag)"]
    end

    subgraph "CD - ArgoCD"
        UpdateManifest --> GitOps["GitOps Repository"]
        GitOps --> Argo["ArgoCD"]
        Argo --> Verify["Kyverno Verify<br/>(signature check)"]
        Verify --> Deploy["Deploy to Cluster"]
    end

    style Push fill:#e1f5fe
    style ECR fill:#e8f5e9
    style GitOps fill:#fff3e0
    style Deploy fill:#f3e5f5
```

### 7.2 Task de actualización del repositorio GitOps

Después de un build exitoso, Tekton actualiza el tag de imagen en el repositorio GitOps. ArgoCD detecta el cambio y reconcilia el deployment.

```yaml
# task-update-gitops-repo.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: update-gitops-repo
spec:
  description: >
    Updates the image tag in a GitOps repository, triggering ArgoCD
    to reconcile and deploy the new version.
  params:
    - name: gitops-repo-url
      type: string
      description: "GitOps repository SSH URL"
    - name: gitops-branch
      type: string
      description: "Branch to update"
      default: "main"
    - name: image-name
      type: string
      description: "Application name (matches directory in gitops repo)"
    - name: new-image-url
      type: string
      description: "Full image URL with new tag"
    - name: environment
      type: string
      description: "Target environment (staging, production)"
      default: "staging"
    - name: author-name
      type: string
      default: "Tekton CI"
    - name: author-email
      type: string
      default: "tekton@mycompany.com"
  workspaces:
    - name: ssh-directory
      description: "SSH credentials for git push"
  steps:
    - name: update-and-push
      image: alpine/git:2.43.0
      script: |
        #!/usr/bin/env sh
        set -euo pipefail

        # Configure SSH
        mkdir -p ~/.ssh
        cp $(workspaces.ssh-directory.path)/id_rsa ~/.ssh/id_rsa
        chmod 600 ~/.ssh/id_rsa
        ssh-keyscan github.com >> ~/.ssh/known_hosts

        # Clone the GitOps repository
        WORK_DIR="/tmp/gitops"
        git clone --branch "$(params.gitops-branch)" \
          --single-branch --depth 1 \
          "$(params.gitops-repo-url)" "${WORK_DIR}"
        cd "${WORK_DIR}"

        # Update the image tag in the Kustomize overlay
        OVERLAY_DIR="overlays/$(params.environment)/$(params.image-name)"
        if [ -f "${OVERLAY_DIR}/kustomization.yaml" ]; then
          echo "Updating Kustomize overlay..."
          cd "${OVERLAY_DIR}"

          # Extract registry/repo and tag from full URL
          IMAGE_REF=$(echo "$(params.new-image-url)" | cut -d':' -f1)
          IMAGE_TAG=$(echo "$(params.new-image-url)" | cut -d':' -f2)

          # Use kustomize edit to update the image
          kustomize edit set image "${IMAGE_REF}:${IMAGE_TAG}"
          cd "${WORK_DIR}"
        else
          echo "ERROR: Overlay directory not found: ${OVERLAY_DIR}"
          exit 1
        fi

        # Commit and push
        git config user.name "$(params.author-name)"
        git config user.email "$(params.author-email)"
        git add -A
        git diff --cached --quiet && {
          echo "No changes to commit"
          exit 0
        }
        git commit -m "chore($(params.environment)): update $(params.image-name) to $(params.new-image-url)

        Triggered by Tekton PipelineRun
        Image: $(params.new-image-url)"

        git push origin "$(params.gitops-branch)"
        echo "GitOps repository updated successfully"
```

### 7.3 Pipeline CI completo con traspaso a GitOps

Agrega la actualización de GitOps como paso final en el Pipeline de CI:

```yaml
# Add to the pipeline-ci-cd.yaml tasks list (after security-scan)
    - name: update-gitops
      taskRef:
        name: update-gitops-repo
      runAfter:
        - security-scan
      params:
        - name: gitops-repo-url
          value: "git@github.com:myorg/k8s-gitops.git"
        - name: gitops-branch
          value: "main"
        - name: image-name
          value: "$(params.image-name)"
        - name: new-image-url
          value: "$(tasks.build-push.results.image-url)"
        - name: environment
          value: "$(params.deploy-environment)"
      workspaces:
        - name: ssh-directory
          workspace: git-credentials
```

### 7.4 Configuración de Application de ArgoCD

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-service-staging
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: ci-cd-notifications
    notifications.argoproj.io/subscribe.on-sync-failed.slack: ci-cd-alerts
spec:
  project: default
  source:
    repoURL: git@github.com:myorg/k8s-gitops.git
    targetRevision: main
    path: overlays/staging/my-service
  destination:
    server: https://kubernetes.default.svc
    namespace: staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### 7.5 Resumen del flujo end-to-end

1. **El desarrollador hace push** de código al repositorio de la aplicación
2. **El webhook de GitHub** se dispara hacia Tekton Triggers
3. **EventListener** recibe el evento, valida la firma y filtra con CEL
4. **PipelineRun** se crea automáticamente
5. **Tekton Pipeline** se ejecuta: clone, test, lint, build, push a ECR, escaneo de seguridad
6. **Tekton Chains** firma la imagen y genera procedencia SLSA
7. **La GitOps update Task** confirma el nuevo tag de imagen en el repositorio GitOps
8. **ArgoCD** detecta el cambio y sincroniza el deployment
9. **Kyverno** verifica la firma de la imagen antes de permitir que el Pod se ejecute
10. **La nueva versión** se despliega en el cluster

---

## 8. Operaciones de producción

### 8.1 Políticas de limpieza de PipelineRun

PipelineRuns y TaskRuns se acumulan en el cluster y consumen almacenamiento de etcd. Configura limpieza automática:

```yaml
# tekton-pruner-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-leader-election
  namespace: tekton-pipelines
data: {}
---
# CronJob-based cleanup (recommended for fine-grained control)
apiVersion: batch/v1
kind: CronJob
metadata:
  name: tekton-cleanup
  namespace: tekton-pipelines
spec:
  schedule: "0 2 * * *"  # Daily at 2:00 AM UTC
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 600
      template:
        spec:
          serviceAccountName: tekton-cleanup-sa
          restartPolicy: OnFailure
          containers:
            - name: cleanup
              image: bitnami/kubectl:1.30
              command:
                - /bin/bash
                - -c
                - |
                  set -euo pipefail

                  # Delete completed PipelineRuns older than 7 days
                  echo "Cleaning up PipelineRuns older than 7 days..."
                  kubectl get pipelineruns -A \
                    -o jsonpath='{range .items[?(@.status.completionTime)]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.completionTime}{"\n"}{end}' | \
                  while IFS=$'\t' read -r ns name completed; do
                    if [ "$(date -d "${completed}" +%s)" -lt "$(date -d '7 days ago' +%s)" ]; then
                      echo "Deleting PipelineRun ${ns}/${name} (completed: ${completed})"
                      kubectl delete pipelinerun "${name}" -n "${ns}" --wait=false
                    fi
                  done

                  # Delete orphaned TaskRuns older than 7 days
                  echo "Cleaning up orphaned TaskRuns..."
                  kubectl get taskruns -A \
                    -o jsonpath='{range .items[?(@.status.completionTime)]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.completionTime}{"\n"}{end}' | \
                  while IFS=$'\t' read -r ns name completed; do
                    if [ "$(date -d "${completed}" +%s)" -lt "$(date -d '7 days ago' +%s)" ]; then
                      echo "Deleting TaskRun ${ns}/${name} (completed: ${completed})"
                      kubectl delete taskrun "${name}" -n "${ns}" --wait=false
                    fi
                  done

                  # Clean up completed Pods from Tekton builds
                  echo "Cleaning up completed build Pods..."
                  kubectl delete pods -A \
                    -l app.kubernetes.io/managed-by=tekton-pipelines \
                    --field-selector=status.phase=Succeeded \
                    --wait=false || true

                  echo "Cleanup complete"
              resources:
                requests: { cpu: "100m", memory: "128Mi" }
                limits:   { cpu: "500m", memory: "256Mi" }
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tekton-cleanup-sa
  namespace: tekton-pipelines
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tekton-cleanup
rules:
  - apiGroups: ["tekton.dev"]
    resources: ["pipelineruns", "taskruns"]
    verbs: ["get", "list", "delete"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tekton-cleanup
subjects:
  - kind: ServiceAccount
    name: tekton-cleanup-sa
    namespace: tekton-pipelines
roleRef:
  kind: ClusterRole
  name: tekton-cleanup
  apiGroup: rbac.authorization.k8s.io
```

### 8.2 Gestión de recursos

Configura requests y limits de recursos para los controladores de Tekton y los Pods de build:

```yaml
# tekton-controller-resources.yaml
# Patch the Tekton controller deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tekton-pipelines-controller
  namespace: tekton-pipelines
spec:
  template:
    spec:
      containers:
        - name: tekton-pipelines-controller
          resources:
            requests:
              cpu: "200m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
```

Establece límites de recursos predeterminados para Pods TaskRun usando LimitRange:

```yaml
# tekton-builds-limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: tekton-build-limits
  namespace: tekton-builds
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "4"
        memory: "8Gi"
    - type: PersistentVolumeClaim
      max:
        storage: "20Gi"
```

Establece un ResourceQuota para limitar el consumo total de recursos de build:

```yaml
# tekton-builds-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tekton-build-quota
  namespace: tekton-builds
spec:
  hard:
    requests.cpu: "16"
    requests.memory: "32Gi"
    limits.cpu: "32"
    limits.memory: "64Gi"
    persistentvolumeclaims: "20"
    pods: "50"
```

### 8.3 Monitoreo con Prometheus

Tekton expone métricas Prometheus en el endpoint `:9090/metrics` del controlador. Configura un ServiceMonitor para scraping:

```yaml
# tekton-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tekton-pipelines
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
      - tekton-pipelines
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/part-of: tekton-pipelines
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tekton-triggers
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
      - tekton-pipelines
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/part-of: tekton-triggers
  endpoints:
    - port: metrics
      interval: 30s
```

Métricas clave de Tekton para monitorear:

| Métrica | Descripción | Umbral de alerta |
|--------|-------------|-----------------|
| `tekton_pipelines_controller_pipelinerun_duration_seconds` | Duración de ejecución de PipelineRun | > 30 minutos |
| `tekton_pipelines_controller_pipelinerun_count` | Recuento total de PipelineRun por estado | Alta tasa de fallos |
| `tekton_pipelines_controller_taskrun_duration_seconds` | Duración de ejecución de TaskRun | > 15 minutos |
| `tekton_pipelines_controller_taskrun_count` | Recuento total de TaskRun por estado | Alta tasa de fallos |
| `tekton_pipelines_controller_running_pipelineruns_count` | PipelineRuns actualmente en ejecución | > 20 concurrentes |
| `tekton_pipelines_controller_client_latency` | Latencia de solicitudes al API server | > 5 segundos |
| `tekton_triggers_eventlistener_event_count` | Eventos webhook entrantes | Caída a 0 (indica fallo del webhook) |

PrometheusRule para alertas:

```yaml
# tekton-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: tekton-pipelines-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
    - name: tekton-pipelines
      interval: 60s
      rules:
        - alert: TektonPipelineRunHighFailureRate
          expr: |
            (
              sum(rate(tekton_pipelines_controller_pipelinerun_count{status="failed"}[1h]))
              /
              sum(rate(tekton_pipelines_controller_pipelinerun_count[1h]))
            ) > 0.3
          for: 15m
          labels:
            severity: warning
          annotations:
            summary: "High PipelineRun failure rate (> 30%)"
            description: "More than 30% of PipelineRuns have failed in the last hour."

        - alert: TektonPipelineRunStuck
          expr: |
            tekton_pipelines_controller_running_pipelineruns_count > 0
            and
            tekton_pipelines_controller_pipelinerun_duration_seconds{status="running"} > 3600
          for: 10m
          labels:
            severity: critical
          annotations:
            summary: "PipelineRun stuck for over 1 hour"
            description: "A PipelineRun has been running for more than 1 hour and may be stuck."

        - alert: TektonControllerDown
          expr: |
            absent(up{job="tekton-pipelines-controller"} == 1)
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Tekton Pipelines controller is down"
            description: "The Tekton Pipelines controller has been unreachable for 5 minutes."

        - alert: TektonWebhookEventsDropped
          expr: |
            rate(tekton_triggers_eventlistener_event_count[5m]) == 0
            and
            tekton_triggers_eventlistener_event_count > 0
          for: 30m
          labels:
            severity: warning
          annotations:
            summary: "No webhook events received for 30 minutes"
            description: "The Tekton EventListener has not received any events. Verify webhook configuration."
```

### 8.4 Gestión de logs

Envía los logs de builds de Tekton a un sistema de logging centralizado:

```yaml
# fluentbit-tekton-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-tekton
  namespace: logging
data:
  tekton-pipelines.conf: |
    [INPUT]
        Name              tail
        Tag               tekton.*
        Path              /var/log/containers/*tekton-pipelines*.log
        Parser            docker
        DB                /var/log/flb_tekton.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name              kubernetes
        Match             tekton.*
        Kube_URL          https://kubernetes.default.svc:443
        Kube_Tag_Prefix   tekton.var.log.containers.
        Merge_Log         On
        Keep_Log          Off
        K8S-Logging.Parser On

    [FILTER]
        Name              modify
        Match             tekton.*
        Add               log_source tekton-pipelines

    [OUTPUT]
        Name              opensearch
        Match             tekton.*
        Host              opensearch.logging.svc
        Port              9200
        Index             tekton-logs
        Type              _doc
        Logstash_Format   On
        Logstash_Prefix   tekton
        Retry_Limit       5
```

### 8.5 Guía de solución de problemas

| Síntoma | Causa posible | Resolución |
|---------|---------------|------------|
| PipelineRun atascado en `Running` | Fallo de scheduling del Pod o Step colgado | Revisa `kubectl describe pod` para el Pod de TaskRun; busca agotamiento de resource quota o problemas de node affinity |
| TaskRun falla con `ImagePullBackOff` | Referencia de imagen incorrecta o credenciales de registry faltantes | Verifica la URL de imagen y que el ServiceAccount tenga imagePullSecrets o anotación IRSA |
| Volumen Workspace no montado | Fallo de aprovisionamiento de PVC o StorageClass faltante | Revisa `kubectl get pvc` en el namespace de build; verifica que el StorageClass exista y tenga capacidad disponible |
| EventListener no recibe eventos | Configuración incorrecta de la URL del webhook o problema de Ingress | Verifica que el Ingress esté saludable; revisa `kubectl logs` para el Pod de EventListener; prueba con `curl -X POST` |
| Chains no firma imágenes | Controlador Chains no configurado o clave de firma faltante | Revisa `kubectl logs -n tekton-chains`; verifica que exista el Secret `signing-secrets`; revisa el ConfigMap `chains-config` |
| Results demasiado grandes | El Result supera el límite de 4096 bytes | Usa Workspaces para pasar datos grandes entre Tasks en lugar de Results |
| Build se queda sin disco | PVC de Workspace demasiado pequeño para la caché de build | Aumenta el tamaño del PVC en el volumeClaimTemplate del workspace del PipelineRun |
| Tasks paralelas con cuello de botella | Demasiados PipelineRuns concurrentes superan la capacidad de los nodes | Establece límites ResourceQuota; usa PriorityClasses para asegurar que builds críticos se programen primero |

Comandos comunes de depuración:

```bash
# View PipelineRun status and conditions
kubectl get pipelinerun <name> -n tekton-builds -o yaml | \
  yq '.status.conditions'

# View TaskRun logs (all steps)
kubectl logs -n tekton-builds \
  -l tekton.dev/pipelineRun=<pipelinerun-name> \
  --all-containers --timestamps

# View specific Step logs
kubectl logs -n tekton-builds <taskrun-pod-name> -c step-<step-name>

# List all running PipelineRuns
kubectl get pipelineruns -A --field-selector=status.conditions[0].reason=Running

# Describe a failed TaskRun for error details
kubectl describe taskrun <name> -n tekton-builds

# Check Tekton controller logs for reconciliation errors
kubectl logs -n tekton-pipelines deployment/tekton-pipelines-controller \
  --tail=100 --since=10m

# Check Chains controller logs
kubectl logs -n tekton-chains deployment/tekton-chains-controller \
  --tail=50 --since=10m

# Verify EventListener is healthy
kubectl get eventlisteners -n tekton-builds
kubectl logs -n tekton-builds -l eventlistener=github-listener --tail=50
```

---

## 9. Buenas prácticas

### 9.1 Patrones de reutilización de Tasks

1. **Mantén las Tasks pequeñas y enfocadas.** Una Task debe hacer una cosa bien (clone, build, scan, deploy). Evita Tasks monolíticas que combinen build, test y deploy en un único script de 500 líneas. Las Tasks pequeñas son reutilizables entre Pipelines y más fáciles de depurar.

2. **Parametriza todo.** Usa params para versiones de imagen, flags, umbrales y rutas. Esto hace que las Tasks sean reutilizables entre proyectos sin modificación.

3. **Publica Tasks internas en un namespace compartido.** Crea un namespace `tekton-catalog` para Tasks reutilizables de toda la organización. Los equipos las referencian por nombre en lugar de copiar YAML.

4. **Fija los tags de imagen en los Steps.** Nunca uses tags `latest` en imágenes de Step. Fíjalos a versiones específicas (por ejemplo, `golang:1.22.4`, `kaniko:v1.23.2`) para garantizar builds reproducibles.

5. **Usa Results para paso de datos ligeros.** Pasa commits SHA, tags de imagen y flags de estado mediante Results. Usa Workspaces para datos grandes como código fuente y artefactos de build.

### 9.2 Seguridad

1. **Usa IRSA en lugar de credenciales de larga duración.** Nunca almacenes claves de acceso de AWS como Kubernetes Secrets. Usa ServiceAccounts anotados con IRSA para acceso a ECR, S3 y KMS.

2. **Ejecuta containers de build como non-root cuando sea posible.** Establece `securityContext.runAsNonRoot: true` en el stepTemplate de la Task. Kaniko requiere root, pero la mayoría de los demás Steps no.

3. **Aísla los namespaces de build.** Ejecuta builds de Tekton en un namespace dedicado con NetworkPolicies que restrinjan el egress solo a registries y APIs necesarios.

4. **Rota los secretos de webhook regularmente.** Usa un CronJob o un administrador externo de secretos para rotar los secretos de webhook de GitHub/GitLab y actualizar los Kubernetes Secrets correspondientes.

5. **Habilita Tekton Chains para todos los builds de producción.** La seguridad de cadena de suministro no es opcional. Cada imagen desplegada en producción debe tener una firma verificada y procedencia SLSA.

```yaml
# network-policy-tekton-builds.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tekton-builds-egress
  namespace: tekton-builds
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    # Allow DNS
    - to: []
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # Allow HTTPS to ECR, GitHub, and package registries
    - to: []
      ports:
        - protocol: TCP
          port: 443
    # Allow access to Kubernetes API server
    - to:
        - ipBlock:
            cidr: 172.20.0.1/32  # Adjust to your cluster API server IP
      ports:
        - protocol: TCP
          port: 443
```

### 9.3 Optimización de rendimiento

1. **Usa caché de Workspace para módulos Go, paquetes npm y repositorios Maven.** Los Workspaces persistentes respaldados por PVCs evitan volver a descargar dependencias en cada build.

```yaml
# Reusable PVC for Go module cache
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: go-module-cache
  namespace: tekton-builds
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: gp3
```

2. **Habilita el caché de capas de Kaniko.** Usa un repositorio ECR como caché de capas para acelerar builds Docker multietapa:

```yaml
# In the kaniko build step args
- --cache=true
- --cache-repo=123456789012.dkr.ecr.us-east-1.amazonaws.com/kaniko-cache
- --cache-ttl=168h  # 7 days
```

3. **Deshabilita el affinity assistant.** El affinity assistant asegura que los PVCs de Workspace estén coubicados con los Pods, pero limita el paralelismo. Cuando uses PVCs `ReadWriteMany` o workspaces `emptyDir`, deshabilítalo:

```yaml
# In feature-flags ConfigMap
disable-affinity-assistant: "true"
```

4. **Usa node selectors para workloads de build.** Programa Pods de build en grupos de nodes dedicados con almacenamiento local rápido y CPU alta:

```yaml
# In PipelineRun taskRunTemplate
taskRunTemplate:
  podTemplate:
    nodeSelector:
      node-role.kubernetes.io/build: "true"
    tolerations:
      - key: "build-workload"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

5. **Establece timeouts agresivos.** Evita que builds descontrolados consuman recursos indefinidamente. Establece timeouts a nivel de Pipeline, Task y bloque finally.

### 9.4 Optimización de costos

1. **Usa instancias Spot para build nodes.** Las workloads de build son inherentemente interrumpibles. Usa Karpenter con un NodePool solo Spot para Pods de build:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: tekton-builds
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m6i.xlarge", "m6a.xlarge", "m5.xlarge"]
      taints:
        - key: build-workload
          value: "true"
          effect: NoSchedule
  limits:
    cpu: "64"
    memory: "128Gi"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```

2. **Escala la infraestructura de build a cero.** Cuando no hay PipelineRuns activos, Karpenter drena y termina los build nodes. No hay costo de cómputo durante los periodos inactivos.

3. **Limpia PVCs agresivamente.** Usa `volumeClaimTemplate` en PipelineRuns en lugar de PVCs preaprovisionados. El PVC se elimina automáticamente cuando el PipelineRun es recolectado por garbage collection.

4. **Dimensiona correctamente los requests de recursos de Step.** Perfila tus builds y establece requests precisos de CPU/memoria. Los containers de build sobredimensionados desperdician recursos de los nodes.

---

## 10. Referencias

### Referencias externas

- [Documentación de Tekton](https://tekton.dev/docs/) - Documentación oficial del proyecto Tekton
- [Tekton Hub](https://hub.tekton.dev/) - Catálogo de Tasks y Pipelines reutilizables
- [Documentación de Tekton Chains](https://tekton.dev/docs/chains/) - Seguridad de cadena de suministro con Tekton
- [Framework SLSA](https://slsa.dev/) - Supply-chain Levels for Software Artifacts
- [Sigstore / Cosign](https://docs.sigstore.dev/) - Firma y verificación de imágenes de container
- [CD Foundation](https://cd.foundation/) - Continuous Delivery Foundation (hogar de Tekton)
- [Kaniko](https://github.com/GoogleContainerTools/kaniko) - Builds de imágenes de container sin Docker daemon
- [Framework de atestación in-toto](https://in-toto.io/) - Atestación de cadena de suministro de software

### Referencias internas

- [Pipelines de CI (GitLab Runner, GitHub Actions en EKS)](./03-ci-pipelines.md) - Infraestructura de runners CI basada en EKS
- [Instalación de ArgoCD](../gitops/argocd/01-installation.md) - Configuración e instalación de ArgoCD
- [Seguridad de imágenes](../security/07-image-security.md) - Escaneo, firma y políticas de admisión de imágenes de container
- [GitOps multi-cluster](./04-gitops-multi-cluster.md) - Despliegue multi-cluster con ArgoCD
- [Gestión de Secrets](../security/05-secrets-management.md) - Buenas prácticas de manejo de secretos de Kubernetes
- [Gestión de políticas Kyverno](../security/01-kyverno-policy-management.md) - Aplicación de políticas para Kubernetes
