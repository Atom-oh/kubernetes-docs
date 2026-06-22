# Tekton Pipelines
> **Supported Versions**: Tekton Pipelines v0.62+, Tekton Triggers v0.28+
> **Last Updated**: June 2025

< [Previous: FinOps Cost Visibility Platform](./13-finops-cost-platform.md) | [Table of Contents](./README.md) | [Next: None] >

---

## Overview

Tekton is a Kubernetes-native, open-source framework for building CI/CD systems. Unlike traditional CI platforms that bolt onto Kubernetes as an afterthought, Tekton runs pipelines as first-class Kubernetes resources: every Task is a Pod, every Step is a container, and every Pipeline is orchestrated by custom controllers watching Custom Resource Definitions (CRDs). This makes Tekton inherently portable, scalable, and deeply integrated with the Kubernetes ecosystem.

Tekton originated at Google as part of the Knative project (specifically `knative/build`) before being donated to the Continuous Delivery Foundation (CDF) in 2019, where it sits alongside Jenkins, Jenkins X, and Spinnaker. It graduated to a mature CDF project and is also a CNCF ecosystem participant through its integration with projects like Sigstore and in-toto.

### Why Tekton Over Traditional CI/CD?

Traditional CI/CD systems (Jenkins, GitHub Actions, GitLab CI) operate as centralized services that dispatch work to runners. This model introduces several challenges in Kubernetes environments:

- **Infrastructure duplication**: A Jenkins controller runs alongside the Kubernetes cluster, requiring its own availability, storage, and scaling concerns.
- **Secret sprawl**: CI platforms need their own credential stores, duplicating what Kubernetes already manages through Secrets, IRSA, and Pod Identity.
- **Limited Kubernetes awareness**: External CI systems lack native access to Kubernetes APIs, requiring kubectl configuration and kubeconfig distribution.
- **Vendor lock-in**: Pipeline definitions are tightly coupled to the CI platform's proprietary YAML or Groovy DSL.

Tekton eliminates these issues by defining pipelines as Kubernetes CRDs. The cluster is both the execution environment and the orchestration layer.

### Tekton vs. Other CI/CD Platforms

| Feature | Tekton | Jenkins | GitHub Actions | GitLab CI |
|---------|--------|---------|----------------|-----------|
| **Runtime** | Kubernetes-native (CRDs) | JVM-based controller | GitHub-hosted / self-hosted runners | GitLab-hosted / self-hosted runners |
| **Pipeline Definition** | Kubernetes YAML | Groovy (Jenkinsfile) | GitHub YAML | GitLab YAML |
| **Scalability** | Scales with Kubernetes (Pod per TaskRun) | Requires agent management | Runner autoscaling | Runner autoscaling |
| **Portability** | Any Kubernetes cluster | Any server with JVM | GitHub ecosystem | GitLab ecosystem |
| **Supply Chain Security** | Tekton Chains (SLSA, Sigstore) | Plugins required | Artifact attestations | Dependency scanning |
| **Event Handling** | Tekton Triggers (webhooks, CEL) | Webhook + plugins | Native GitHub events | Native GitLab events |
| **UI/Dashboard** | Tekton Dashboard (optional) | Jenkins UI (built-in) | GitHub UI (built-in) | GitLab UI (built-in) |
| **Secret Management** | Kubernetes Secrets, IRSA, CSI driver | Jenkins Credentials | GitHub Secrets | GitLab CI Variables |
| **Learning Curve** | Moderate (requires Kubernetes knowledge) | High (Groovy, plugin ecosystem) | Low (familiar YAML) | Low (familiar YAML) |
| **Cost** | Free (compute only) | Free (infra maintenance) | Per-minute billing (hosted) | Per-minute billing (hosted) |

### Learning Objectives

After completing this guide, you will be able to:

- Understand Tekton's architecture and how its CRDs map to CI/CD concepts
- Install and configure Tekton Pipelines, Triggers, Dashboard, and Chains on Amazon EKS
- Author reusable Tasks with step composition, script execution, results, and sidecars
- Construct multi-stage Pipelines with parallel execution, conditional logic, and finally blocks
- Configure webhook-based automatic pipeline triggers using Tekton Triggers
- Implement supply chain security with Tekton Chains, including OCI image signing and SLSA provenance
- Integrate Tekton (CI) with ArgoCD (CD) for a complete GitOps-based CI/CD architecture
- Operate Tekton in production with cleanup policies, monitoring, and troubleshooting strategies

---

## 1. Tekton Architecture

Tekton extends the Kubernetes API with a set of Custom Resource Definitions (CRDs) that model CI/CD concepts. The Tekton controller watches these CRDs and reconciles desired state into Pods and containers.

### 1.1 Core CRDs

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

**Task**: A reusable, parameterized unit of work. Each Task defines one or more Steps that execute sequentially in containers within a single Pod. Tasks also declare Workspaces (for shared data) and Results (for output values).

**TaskRun**: An instantiation of a Task with concrete parameter values and workspace bindings. Creating a TaskRun causes the controller to spin up a Pod that executes the Task's Steps.

**Pipeline**: An ordered collection of Tasks. Pipelines define execution order (sequential, parallel, or DAG-based), parameter passing between Tasks, conditional execution (when expressions), and finally blocks for cleanup.

**PipelineRun**: An instantiation of a Pipeline. Creating a PipelineRun causes the controller to create TaskRuns for each Task in the Pipeline.

**Workspace**: A mechanism for sharing data between Steps (within a Task) or between Tasks (within a Pipeline). Workspaces can be backed by PersistentVolumeClaims, ConfigMaps, Secrets, or emptyDir volumes.

**Result**: A string value produced by a Task that can be consumed by downstream Tasks in a Pipeline. Results are written to `/tekton/results/<name>` and stored in the TaskRun status.

### 1.2 Controller Architecture

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

**tekton-pipelines-controller**: The core reconciliation controller. It watches for new PipelineRun and TaskRun resources, creates Pods for execution, monitors container completion, propagates results, and updates status.

**tekton-pipelines-webhook**: An admission webhook that validates and mutates Tekton CRDs before they are persisted. It enforces schema correctness and applies defaults.

**tekton-chains-controller**: A separate controller that watches TaskRun completions and automatically signs OCI images, generates SLSA provenance attestations, and stores them in OCI registries or transparency logs.

**tekton-triggers-controller**: Processes incoming webhook events (from GitHub, GitLab, etc.), evaluates interceptors and CEL expressions, and creates PipelineRun resources based on TriggerTemplate definitions.

**tekton-dashboard**: An optional web UI for viewing PipelineRuns, TaskRuns, logs, and cluster resources.

### 1.3 Tekton Chains and Supply Chain Security

Tekton Chains is a dedicated component for software supply chain security. When a TaskRun completes, Chains automatically:

1. **Signs OCI images** produced by the TaskRun using Cosign (Sigstore)
2. **Generates SLSA provenance** attestations recording what was built, from what source, using which builder
3. **Stores attestations** in the OCI registry as image signatures or in transparency logs (Rekor)
4. **Produces in-toto attestation** metadata linking source materials to build outputs

This provides tamper-evident records that downstream consumers (admission controllers, policy engines) can verify before deploying images.

---

## 2. EKS Installation and Configuration

### 2.1 Prerequisites

Before installing Tekton, ensure your EKS cluster meets the following requirements:

```bash
# Verify cluster version (1.28+)
kubectl version --short

# Verify cluster has sufficient capacity
# Tekton controllers need ~500m CPU and ~512Mi memory total
kubectl top nodes

# Ensure the cluster has a default StorageClass for Workspaces
kubectl get storageclass
```

### 2.2 Tekton Pipelines Installation

```bash
# Install Tekton Pipelines (core)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/previous/v0.62.2/release.yaml

# Verify installation
kubectl get pods -n tekton-pipelines --watch
```

Expected output:

```
NAME                                           READY   STATUS    RESTARTS   AGE
tekton-pipelines-controller-7f6d5b8bc4-xxxxx   1/1     Running   0          30s
tekton-pipelines-webhook-6c9b5d7d8f-xxxxx      1/1     Running   0          30s
```

Configure Tekton Pipelines feature flags:

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

### 2.3 Tekton Triggers Installation

```bash
# Install Tekton Triggers
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/release.yaml

# Install Tekton Triggers Interceptors (required for GitHub/GitLab webhooks)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/interceptors.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-triggers
```

### 2.4 Tekton Dashboard Installation

```bash
# Install Tekton Dashboard (read-only mode for production)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/previous/v0.46.0/release-full.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-dashboard
```

Expose the Dashboard via an internal ALB Ingress:

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

### 2.5 Tekton Chains Installation

```bash
# Install Tekton Chains
kubectl apply --filename https://storage.googleapis.com/tekton-releases/chains/previous/v0.22.1/release.yaml

# Verify installation
kubectl get pods -n tekton-chains
```

### 2.6 IRSA Configuration for ECR and S3

Tekton Tasks that push images to ECR or upload artifacts to S3 require IAM permissions. Use IAM Roles for Service Accounts (IRSA) to grant least-privilege access.

```bash
# Create OIDC provider (skip if already configured)
eksctl utils associate-iam-oidc-provider \
  --cluster my-eks-cluster \
  --region us-east-1 \
  --approve
```

**ECR Push IAM Policy:**

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

**S3 Artifact Upload IAM Policy:**

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

Create the IRSA-annotated ServiceAccount:

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

Verify the annotation:

```bash
kubectl get sa tekton-build-sa -n tekton-builds -o yaml
# Should show: eks.amazonaws.com/role-arn annotation
```

---

## 3. Task Authoring

Tasks are the fundamental building blocks in Tekton. A well-designed Task is reusable, parameterized, and produces meaningful results.

### 3.1 Step Composition

Each Step in a Task runs as a container within the same Pod. Steps execute sequentially, sharing the same network namespace and Workspace volumes.

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

### 3.2 Script Execution

Steps can run inline scripts for complex logic. The `script` field accepts any interpreter available in the container image.

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

### 3.3 Results Passing Between Tasks

Results from one Task can be referenced by downstream Tasks in a Pipeline using the `$(tasks.<taskName>.results.<resultName>)` syntax. Results are limited to 4096 bytes by default.

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

Sidecars are long-running containers that run alongside Steps, useful for services like Docker daemon, databases for integration tests, or caches.

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

### 3.5 Reusable Tasks from Tekton Hub

[Tekton Hub](https://hub.tekton.dev) provides a catalog of community-maintained, reusable Tasks. Install them directly into your cluster:

```bash
# Install the git-clone Task (official catalog)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.9/git-clone.yaml

# Install the kaniko Task (for building images without Docker daemon)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kaniko/0.7/kaniko.yaml

# Install the kubernetes-actions Task (for kubectl operations)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kubernetes-actions/0.2/kubernetes-actions.yaml
```

Verify installed Tasks:

```bash
kubectl get tasks -n tekton-builds
```

### 3.6 Complete Build-Push Task (Kaniko + ECR)

This Task builds a container image using Kaniko (no Docker daemon required) and pushes it to Amazon ECR:

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

## 4. Pipeline Construction

Pipelines orchestrate multiple Tasks into a directed acyclic graph (DAG). Tasks can run in parallel, conditionally, or sequentially based on explicit dependencies.

### 4.1 Task Ordering and Parallel Execution

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

In the diagram above, `lint` and `unit-test` run in parallel after `git-clone` completes. `build-image` waits for both to succeed. This is achieved by using `runAfter` in the Pipeline spec.

### 4.2 Conditional Execution with When Expressions

When expressions allow Tasks to be skipped based on parameter values or results from previous Tasks:

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

### 4.3 Finally Tasks

Finally Tasks always execute regardless of Pipeline success or failure — similar to `try/finally` in code. They are ideal for cleanup, notifications, and status reporting.

### 4.4 Complete CI/CD Pipeline

The following Pipeline implements a full CI/CD workflow: clone, test, build, push, scan, and deploy.

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

### 4.5 Running the Pipeline

Create a PipelineRun to execute the Pipeline:

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

Tekton Triggers enable automatic Pipeline execution in response to external events such as Git pushes, pull requests, or any webhook-based event.

### 5.1 Trigger Architecture

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

**EventListener**: A Kubernetes Service that receives incoming webhook HTTP requests and routes them through Triggers.

**TriggerBinding**: Extracts parameter values from the incoming event payload using JSONPath expressions.

**TriggerTemplate**: A template for creating Tekton resources (typically PipelineRuns) with parameters populated from the TriggerBinding.

**Interceptor**: A processing step that validates, filters, and transforms incoming events. Built-in interceptors include GitHub (webhook signature validation), GitLab, Bitbucket, and CEL (Common Expression Language for filtering).

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

### 5.4 EventListener with Interceptors

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

### 5.5 Expose EventListener

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

Configure the webhook in GitHub:

```
Payload URL:    https://tekton-hooks.mycompany.com
Content type:   application/json
Secret:         <same value as github-webhook-secret>
Events:         Pushes, Pull requests
```

### 5.6 GitLab Interceptor Example

For GitLab webhooks, replace the GitHub interceptor:

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

## 6. Tekton Chains (Supply Chain Security)

Tekton Chains provides automated supply chain security for your CI/CD pipelines. It observes TaskRun completions and automatically generates cryptographic attestations about what was built, how, and from what source.

### 6.1 How Chains Works

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

### 6.2 Chains Configuration

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

### 6.3 Signing Key Setup

For key-based signing (non-keyless), generate a Cosign key pair and store it as a Kubernetes Secret:

```bash
# Generate a Cosign signing key pair
cosign generate-key-pair k8s://tekton-chains/signing-secrets
```

This creates a Secret named `signing-secrets` in the `tekton-chains` namespace containing the private key. The public key is output to `cosign.pub`.

For production environments using AWS KMS:

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

Update Chains config for KMS:

```yaml
# chains-config-kms.yaml (merge with chains-config)
data:
  sigstore.kms: "awskms:///arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

### 6.4 SLSA Provenance

Tekton Chains generates [SLSA](https://slsa.dev/) (Supply-chain Levels for Software Artifacts) provenance attestations automatically. The provenance records:

- **Builder**: Which Tekton Task/Pipeline produced the artifact
- **Source**: The git repository, branch, and commit
- **Build configuration**: The Pipeline parameters and Task steps
- **Materials**: Input artifacts (source code, base images)
- **Output**: The built artifact (image digest)

Verify provenance after a build:

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

Example SLSA provenance output (abbreviated):

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

### 6.5 Policy Enforcement with Kyverno

Use Kyverno to enforce that only signed images with valid provenance can be deployed:

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

## 7. ArgoCD + Tekton Integration

The most effective production architecture separates CI (build, test, push) from CD (deploy). Tekton handles CI while ArgoCD handles CD via GitOps. This separation provides clear ownership, independent scaling, and a reliable audit trail.

### 7.1 CI/CD Separation Architecture

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

### 7.2 GitOps Repository Update Task

After a successful build, Tekton updates the image tag in the GitOps repository. ArgoCD detects the change and reconciles the deployment.

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

### 7.3 Complete CI Pipeline with GitOps Handoff

Add the GitOps update as the final step in the CI Pipeline:

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

### 7.4 ArgoCD Application Configuration

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

### 7.5 End-to-End Workflow Summary

1. **Developer pushes** code to the application repository
2. **GitHub webhook** fires to Tekton Triggers
3. **EventListener** receives the event, validates the signature, filters with CEL
4. **PipelineRun** is created automatically
5. **Tekton Pipeline** runs: clone, test, lint, build, push to ECR, security scan
6. **Tekton Chains** signs the image and generates SLSA provenance
7. **GitOps update Task** commits the new image tag to the GitOps repository
8. **ArgoCD** detects the change and syncs the deployment
9. **Kyverno** verifies the image signature before allowing the Pod to run
10. **New version** is deployed to the cluster

---

## 8. Production Operations

### 8.1 PipelineRun Cleanup Policies

PipelineRuns and TaskRuns accumulate in the cluster and consume etcd storage. Configure automatic cleanup:

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

### 8.2 Resource Management

Configure resource requests and limits for Tekton controllers and build Pods:

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

Set default resource limits for TaskRun Pods using LimitRange:

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

Set a ResourceQuota to cap total build resource consumption:

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

### 8.3 Monitoring with Prometheus

Tekton exposes Prometheus metrics on the controller's `:9090/metrics` endpoint. Configure a ServiceMonitor for scraping:

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

Key Tekton metrics to monitor:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `tekton_pipelines_controller_pipelinerun_duration_seconds` | PipelineRun execution duration | > 30 minutes |
| `tekton_pipelines_controller_pipelinerun_count` | Total PipelineRun count by status | High failure rate |
| `tekton_pipelines_controller_taskrun_duration_seconds` | TaskRun execution duration | > 15 minutes |
| `tekton_pipelines_controller_taskrun_count` | Total TaskRun count by status | High failure rate |
| `tekton_pipelines_controller_running_pipelineruns_count` | Currently running PipelineRuns | > 20 concurrent |
| `tekton_pipelines_controller_client_latency` | API server request latency | > 5 seconds |
| `tekton_triggers_eventlistener_event_count` | Incoming webhook events | Drop to 0 (indicates webhook failure) |

PrometheusRule for alerting:

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

### 8.4 Log Management

Forward Tekton build logs to a centralized logging system:

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

### 8.5 Troubleshooting Guide

| Symptom | Possible Cause | Resolution |
|---------|---------------|------------|
| PipelineRun stuck in `Running` | Pod scheduling failure or Step hanging | Check `kubectl describe pod` for the TaskRun Pod; look for resource quota exhaustion or node affinity issues |
| TaskRun fails with `ImagePullBackOff` | Incorrect image reference or missing registry credentials | Verify image URL and that the ServiceAccount has imagePullSecrets or IRSA annotation |
| Workspace volume not mounted | PVC provisioning failure or StorageClass missing | Check `kubectl get pvc` in the build namespace; verify the StorageClass exists and has available capacity |
| EventListener not receiving events | Webhook URL misconfiguration or Ingress issue | Verify the Ingress is healthy; check `kubectl logs` for the EventListener Pod; test with `curl -X POST` |
| Chains not signing images | Chains controller not configured or signing key missing | Check `kubectl logs -n tekton-chains`; verify `signing-secrets` Secret exists; check `chains-config` ConfigMap |
| Results too large | Result exceeds 4096-byte limit | Use Workspaces to pass large data between Tasks instead of Results |
| Build runs out of disk | Workspace PVC too small for build cache | Increase the PVC size in the PipelineRun workspace volumeClaimTemplate |
| Parallel Tasks bottleneck | Too many concurrent PipelineRuns exceeding node capacity | Set ResourceQuota limits; use PriorityClasses to ensure critical builds are scheduled first |

Common debugging commands:

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

## 9. Best Practices

### 9.1 Task Reuse Patterns

1. **Keep Tasks small and focused.** A Task should do one thing well (clone, build, scan, deploy). Avoid monolithic Tasks that combine build, test, and deploy into a single 500-line script. Small Tasks are reusable across Pipelines and easier to debug.

2. **Parameterize everything.** Use params for image versions, flags, thresholds, and paths. This makes Tasks reusable across projects without modification.

3. **Publish internal Tasks to a shared namespace.** Create a `tekton-catalog` namespace for organization-wide reusable Tasks. Teams reference them by name rather than copying YAML.

4. **Pin image tags in Steps.** Never use `latest` tags in Step images. Pin to specific versions (e.g., `golang:1.22.4`, `kaniko:v1.23.2`) to ensure reproducible builds.

5. **Use Results for lightweight data passing.** Pass commit SHAs, image tags, and status flags via Results. Use Workspaces for large data like source code and build artifacts.

### 9.2 Security

1. **Use IRSA instead of long-lived credentials.** Never store AWS access keys as Kubernetes Secrets. Use IRSA-annotated ServiceAccounts for ECR, S3, and KMS access.

2. **Run build containers as non-root when possible.** Set `securityContext.runAsNonRoot: true` in the Task stepTemplate. Kaniko requires root, but most other Steps do not.

3. **Isolate build namespaces.** Run Tekton builds in a dedicated namespace with NetworkPolicies that restrict egress to only necessary registries and APIs.

4. **Rotate webhook secrets regularly.** Use a CronJob or external secret manager to rotate GitHub/GitLab webhook secrets and update the corresponding Kubernetes Secrets.

5. **Enable Tekton Chains for all production builds.** Supply chain security is not optional. Every image deployed to production should have a verified signature and SLSA provenance.

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

### 9.3 Performance Optimization

1. **Use Workspace caching for Go modules, npm packages, and Maven repositories.** Persistent Workspaces backed by PVCs avoid re-downloading dependencies on every build.

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

2. **Enable Kaniko layer caching.** Use an ECR repository as a layer cache to speed up multi-stage Docker builds:

```yaml
# In the kaniko build step args
- --cache=true
- --cache-repo=123456789012.dkr.ecr.us-east-1.amazonaws.com/kaniko-cache
- --cache-ttl=168h  # 7 days
```

3. **Disable the affinity assistant.** The affinity assistant ensures Workspace PVCs are co-located with Pods, but it limits parallelism. When using `ReadWriteMany` PVCs or `emptyDir` workspaces, disable it:

```yaml
# In feature-flags ConfigMap
disable-affinity-assistant: "true"
```

4. **Use node selectors for build workloads.** Schedule build Pods on dedicated node groups with fast local storage and high CPU:

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

5. **Set aggressive timeouts.** Prevent runaway builds from consuming resources indefinitely. Set Pipeline-level, Task-level, and finally-block timeouts.

### 9.4 Cost Optimization

1. **Use Spot instances for build nodes.** Build workloads are inherently interruptible. Use Karpenter with a Spot-only NodePool for build Pods:

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

2. **Scale build infrastructure to zero.** When no PipelineRuns are active, Karpenter drains and terminates build nodes. There is zero compute cost during idle periods.

3. **Clean up PVCs aggressively.** Use `volumeClaimTemplate` in PipelineRuns instead of pre-provisioned PVCs. The PVC is automatically deleted when the PipelineRun is garbage-collected.

4. **Right-size Step resource requests.** Profile your builds and set accurate CPU/memory requests. Over-provisioned build containers waste node resources.

---

## 10. References

### External References

- [Tekton Documentation](https://tekton.dev/docs/) - Official Tekton project documentation
- [Tekton Hub](https://hub.tekton.dev/) - Catalog of reusable Tasks and Pipelines
- [Tekton Chains Documentation](https://tekton.dev/docs/chains/) - Supply chain security with Tekton
- [SLSA Framework](https://slsa.dev/) - Supply-chain Levels for Software Artifacts
- [Sigstore / Cosign](https://docs.sigstore.dev/) - Container image signing and verification
- [CD Foundation](https://cd.foundation/) - Continuous Delivery Foundation (Tekton's home)
- [Kaniko](https://github.com/GoogleContainerTools/kaniko) - Container image builds without Docker daemon
- [in-toto Attestation Framework](https://in-toto.io/) - Software supply chain attestation

### Internal References

- [CI Pipelines (GitLab Runner, GitHub Actions on EKS)](./03-ci-pipelines.md) - EKS-based CI runner infrastructure
- [ArgoCD Installation](../gitops/argocd/01-installation.md) - ArgoCD setup and configuration
- [Image Security](../security/07-image-security.md) - Container image scanning, signing, and admission policies
- [GitOps Multi-Cluster](./04-gitops-multi-cluster.md) - Multi-cluster deployment with ArgoCD
- [Secrets Management](../security/05-secrets-management.md) - Kubernetes secret handling best practices
- [Kyverno Policy Management](../security/01-kyverno-policy-management.md) - Policy enforcement for Kubernetes
