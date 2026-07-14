# Tekton Pipelines
> **Supported Versions**: Tekton Pipelines v0.62+, Tekton Triggers v0.28+
> **最終更新**: June 2025

< [前へ: FinOps Cost Visibility Platform](./13-finops-cost-platform.md) | [目次](./README.md) | [次へ: なし] >

---

## Overview

Tekton は、CI/CD システムを構築するための Kubernetes-native なオープンソースフレームワークです。Kubernetes に後付けで組み込む従来の CI platform とは異なり、Tekton は Pipeline を第一級の Kubernetes resource として実行します。すべての Task は Pod、すべての Step は container、すべての Pipeline は Custom Resource Definitions (CRDs) を監視する custom controller によってオーケストレーションされます。これにより、Tekton は本質的に portable で scalable であり、Kubernetes ecosystem と深く統合されます。

Tekton は、Google で Knative project の一部（具体的には `knative/build`）として始まり、2019 年に Continuous Delivery Foundation (CDF) に寄贈されました。CDF では Jenkins、Jenkins X、Spinnaker と並んで位置付けられています。Tekton は成熟した CDF project に昇格しており、Sigstore や in-toto などの project との統合を通じて CNCF ecosystem participant でもあります。

### Why Tekton Over Traditional CI/CD?

従来の CI/CD system（Jenkins、GitHub Actions、GitLab CI）は、runner に作業を dispatch する centralized service として動作します。この model は Kubernetes environment でいくつかの課題を生みます。

- **Infrastructure の重複**: Jenkins controller が Kubernetes cluster と並行して稼働するため、独自の availability、storage、scaling に関する考慮が必要になります。
- **Secret の拡散**: CI platform は独自の credential store を必要とし、Kubernetes が Secrets、IRSA、Pod Identity ですでに管理しているものを重複させます。
- **Kubernetes への認識不足**: 外部 CI system は Kubernetes API への native access を持たないため、kubectl の設定や kubeconfig の配布が必要になります。
- **Vendor lock-in**: Pipeline definition が CI platform 固有の proprietary YAML や Groovy DSL に強く結合されます。

Tekton は、Pipeline を Kubernetes CRDs として定義することで、これらの問題を解消します。cluster は実行環境であると同時に orchestration layer でもあります。

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

この guide を完了すると、次のことができるようになります。

- Tekton の architecture と、Tekton の CRDs が CI/CD concepts にどのように対応するかを理解する
- Amazon EKS 上で Tekton Pipelines、Triggers、Dashboard、Chains を install および configure する
- Step composition、script execution、results、sidecars を備えた reusable Tasks を作成する
- parallel execution、conditional logic、finally blocks を備えた multi-stage Pipelines を構築する
- Tekton Triggers を使用して webhook-based の automatic pipeline triggers を configure する
- OCI image signing と SLSA provenance を含む Tekton Chains によって supply chain security を実装する
- Tekton (CI) と ArgoCD (CD) を統合し、完全な GitOps-based CI/CD architecture を構築する
- cleanup policies、monitoring、troubleshooting strategies を使用して production で Tekton を運用する

---

## 1. Tekton Architecture

Tekton は、CI/CD concepts を model 化する一連の Custom Resource Definitions (CRDs) によって Kubernetes API を拡張します。Tekton controller はこれらの CRDs を監視し、desired state を Pods と containers に reconcile します。

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

**Task**: 再利用可能で parameterized された作業単位です。各 Task は、単一の Pod 内の containers で順次実行される 1 つ以上の Steps を定義します。Tasks は Workspaces（shared data 用）と Results（output values 用）も宣言します。

**TaskRun**: 具体的な parameter values と workspace bindings を持つ Task の instantiation です。TaskRun を作成すると、controller が Task の Steps を実行する Pod を起動します。

**Pipeline**: Tasks の順序付き collection です。Pipelines は execution order（sequential、parallel、または DAG-based）、Tasks 間の parameter passing、conditional execution（when expressions）、cleanup 用の finally blocks を定義します。

**PipelineRun**: Pipeline の instantiation です。PipelineRun を作成すると、controller が Pipeline 内の各 Task に対して TaskRuns を作成します。

**Workspace**: Steps 間（Task 内）または Tasks 間（Pipeline 内）で data を共有するための仕組みです。Workspaces は PersistentVolumeClaims、ConfigMaps、Secrets、または emptyDir volumes によって backed できます。

**Result**: Pipeline 内の downstream Tasks が consume できる、Task によって生成される string value です。Results は `/tekton/results/<name>` に書き込まれ、TaskRun status に保存されます。

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

**tekton-pipelines-controller**: core reconciliation controller です。新しい PipelineRun と TaskRun resources を監視し、実行用の Pods を作成し、container completion を監視し、results を伝播し、status を更新します。

**tekton-pipelines-webhook**: Tekton CRDs が永続化される前に validate および mutate する admission webhook です。schema correctness を強制し、defaults を適用します。

**tekton-chains-controller**: TaskRun completion を監視し、OCI images に自動的に sign し、SLSA provenance attestations を生成し、OCI registries または transparency logs に保存する separate controller です。

**tekton-triggers-controller**: incoming webhook events（GitHub、GitLab などから）を処理し、interceptors と CEL expressions を評価し、TriggerTemplate definitions に基づいて PipelineRun resources を作成します。

**tekton-dashboard**: PipelineRuns、TaskRuns、logs、cluster resources を表示するための optional web UI です。

### 1.3 Tekton Chains and Supply Chain Security

Tekton Chains は software supply chain security 専用の component です。TaskRun が完了すると、Chains は自動的に次を行います。

1. TaskRun によって生成された **OCI images に sign** します（Cosign (Sigstore) を使用）
2. 何が、どの source から、どの builder を使って build されたかを記録する **SLSA provenance** attestations を生成します
3. OCI registry に image signatures として、または transparency logs（Rekor）に **attestations を保存** します
4. source materials と build outputs を結び付ける **in-toto attestation** metadata を生成します

これにより、downstream consumers（admission controllers、policy engines）が images を deploy する前に verify できる、tamper-evident records が提供されます。

---

## 2. EKS Installation and Configuration

### 2.1 Prerequisites

Tekton を install する前に、EKS cluster が次の requirements を満たしていることを確認してください。

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

想定される output:

```
NAME                                           READY   STATUS    RESTARTS   AGE
tekton-pipelines-controller-7f6d5b8bc4-xxxxx   1/1     Running   0          30s
tekton-pipelines-webhook-6c9b5d7d8f-xxxxx      1/1     Running   0          30s
```

Tekton Pipelines feature flags を configure します。

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

internal ALB Ingress 経由で Dashboard を expose します。

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

images を ECR に push したり、artifacts を S3 に upload したりする Tekton Tasks には IAM permissions が必要です。least-privilege access を付与するには IAM Roles for Service Accounts (IRSA) を使用します。

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

IRSA-annotated ServiceAccount を作成します。

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

annotation を verify します。

```bash
kubectl get sa tekton-build-sa -n tekton-builds -o yaml
# Should show: eks.amazonaws.com/role-arn annotation
```

---

## 3. Task Authoring

Tasks は Tekton における fundamental building blocks です。よく設計された Task は reusable で parameterized され、意味のある results を生成します。

### 3.1 Step Composition

Task 内の各 Step は、同じ Pod 内の container として実行されます。Steps は sequentially に実行され、同じ network namespace と Workspace volumes を共有します。

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

Steps は complex logic のために inline scripts を実行できます。`script` field は container image で利用可能な任意の interpreter を受け付けます。

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

ある Task の Results は、`$(tasks.<taskName>.results.<resultName>)` 構文を使用して Pipeline 内の downstream Tasks から参照できます。Results は default で 4096 bytes に制限されています。

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

Sidecars は Steps と並行して実行される long-running containers で、Docker daemon、integration tests 用 databases、caches などの services に役立ちます。

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

[Tekton Hub](https://hub.tekton.dev) は、community-maintained な reusable Tasks の catalog を提供します。これらを cluster に直接 install します。

```bash
# Install the git-clone Task (official catalog)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.9/git-clone.yaml

# Install the kaniko Task (for building images without Docker daemon)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kaniko/0.7/kaniko.yaml

# Install the kubernetes-actions Task (for kubectl operations)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kubernetes-actions/0.2/kubernetes-actions.yaml
```

install 済みの Tasks を verify します。

```bash
kubectl get tasks -n tekton-builds
```

### 3.6 Complete Build-Push Task (Kaniko + ECR)

この Task は Kaniko（Docker daemon 不要）を使用して container image を build し、Amazon ECR に push します。

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

Pipelines は複数の Tasks を directed acyclic graph (DAG) として orchestrate します。Tasks は explicit dependencies に基づいて parallel、conditionally、または sequentially に実行できます。

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

上の diagram では、`git-clone` が完了した後、`lint` と `unit-test` が parallel に実行されます。`build-image` は両方の成功を待ちます。これは Pipeline spec で `runAfter` を使用することで実現されます。

### 4.2 Conditional Execution with When Expressions

When expressions により、parameter values や previous Tasks の results に基づいて Tasks を skip できます。

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

Finally Tasks は、Pipeline の success または failure に関係なく常に実行されます。code における `try/finally` と似ています。cleanup、notifications、status reporting に最適です。

### 4.4 Complete CI/CD Pipeline

次の Pipeline は、clone、test、build、push、scan、deploy という full CI/CD workflow を実装します。

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

Pipeline を実行するには PipelineRun を作成します。

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

Tekton Triggers は、Git pushes、pull requests、または任意の webhook-based event などの external events に応じて automatic Pipeline execution を可能にします。

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

**EventListener**: incoming webhook HTTP requests を受信し、それらを Triggers に route する Kubernetes Service です。

**TriggerBinding**: JSONPath expressions を使用して incoming event payload から parameter values を抽出します。

**TriggerTemplate**: TriggerBinding から populate された parameters を使用して Tekton resources（通常は PipelineRuns）を作成するための template です。

**Interceptor**: incoming events を validate、filter、transform する processing step です。built-in interceptors には GitHub（webhook signature validation）、GitLab、Bitbucket、CEL（filtering 用の Common Expression Language）が含まれます。

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

GitHub で webhook を configure します。

```
Payload URL:    https://tekton-hooks.mycompany.com
Content type:   application/json
Secret:         <same value as github-webhook-secret>
Events:         Pushes, Pull requests
```

### 5.6 GitLab Interceptor Example

GitLab webhooks の場合は、GitHub interceptor を置き換えます。

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

Tekton Chains は、CI/CD pipelines に automated supply chain security を提供します。TaskRun completions を観測し、何が、どのように、どの source から build されたかについての cryptographic attestations を自動生成します。

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

key-based signing（non-keyless）の場合は、Cosign key pair を生成し、Kubernetes Secret として保存します。

```bash
# Generate a Cosign signing key pair
cosign generate-key-pair k8s://tekton-chains/signing-secrets
```

これにより、private key を含む `signing-secrets` という名前の Secret が `tekton-chains` namespace に作成されます。public key は `cosign.pub` に output されます。

AWS KMS を使用する production environments の場合:

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

KMS 用に Chains config を更新します。

```yaml
# chains-config-kms.yaml (merge with chains-config)
data:
  sigstore.kms: "awskms:///arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

### 6.4 SLSA Provenance

Tekton Chains は [SLSA](https://slsa.dev/) (Supply-chain Levels for Software Artifacts) provenance attestations を自動生成します。provenance は次を記録します。

- **Builder**: どの Tekton Task/Pipeline が artifact を生成したか
- **Source**: git repository、branch、commit
- **Build configuration**: Pipeline parameters と Task steps
- **Materials**: Input artifacts（source code、base images）
- **Output**: build された artifact（image digest）

build 後に provenance を verify します。

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

SLSA provenance output の例（省略版）:

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

valid provenance を持つ signed images のみが deploy できるように Kyverno で enforce します。

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

最も効果的な production architecture は、CI（build、test、push）と CD（deploy）を分離します。Tekton が CI を担当し、ArgoCD が GitOps 経由で CD を担当します。この separation により、明確な ownership、independent scaling、信頼できる audit trail が得られます。

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

build が成功した後、Tekton は GitOps repository の image tag を更新します。ArgoCD はその change を detect し、deployment を reconcile します。

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

GitOps update を CI Pipeline の final step として追加します。

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

1. **Developer が push** します。application repository に code を push します
2. **GitHub webhook** が Tekton Triggers に発火します
3. **EventListener** が event を受信し、signature を validate し、CEL で filter します
4. **PipelineRun** が自動的に作成されます
5. **Tekton Pipeline** が実行されます: clone、test、lint、build、push to ECR、security scan
6. **Tekton Chains** が image に sign し、SLSA provenance を生成します
7. **GitOps update Task** が新しい image tag を GitOps repository に commit します
8. **ArgoCD** が change を detect し、deployment を sync します
9. **Kyverno** が Pod の実行を許可する前に image signature を verify します
10. **New version** が cluster に deploy されます

---

## 8. Production Operations

### 8.1 PipelineRun Cleanup Policies

PipelineRuns と TaskRuns は cluster 内に蓄積し、etcd storage を消費します。automatic cleanup を configure します。

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

Tekton controllers と build Pods の resource requests と limits を configure します。

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

LimitRange を使用して TaskRun Pods の default resource limits を設定します。

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

total build resource consumption に上限を設けるため ResourceQuota を設定します。

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

Tekton は controller の `:9090/metrics` endpoint で Prometheus metrics を expose します。scraping 用の ServiceMonitor を configure します。

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

monitoring すべき主要な Tekton metrics:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `tekton_pipelines_controller_pipelinerun_duration_seconds` | PipelineRun execution duration | > 30 minutes |
| `tekton_pipelines_controller_pipelinerun_count` | Total PipelineRun count by status | High failure rate |
| `tekton_pipelines_controller_taskrun_duration_seconds` | TaskRun execution duration | > 15 minutes |
| `tekton_pipelines_controller_taskrun_count` | Total TaskRun count by status | High failure rate |
| `tekton_pipelines_controller_running_pipelineruns_count` | Currently running PipelineRuns | > 20 concurrent |
| `tekton_pipelines_controller_client_latency` | API server request latency | > 5 seconds |
| `tekton_triggers_eventlistener_event_count` | Incoming webhook events | Drop to 0 (indicates webhook failure) |

alerting 用 PrometheusRule:

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

Tekton build logs を centralized logging system に forward します。

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

一般的な debugging commands:

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

1. **Tasks は小さく focused に保ちます。** Task は 1 つのこと（clone、build、scan、deploy）をうまく行うべきです。build、test、deploy を単一の 500-line script にまとめる monolithic Tasks は避けてください。小さな Tasks は Pipelines 間で reusable で、debug も容易です。

2. **すべてを parameterize します。** image versions、flags、thresholds、paths には params を使用します。これにより、Tasks を変更なしで projects 間で reusable にできます。

3. **internal Tasks を shared namespace に publish します。** organization-wide reusable Tasks 用に `tekton-catalog` namespace を作成します。Teams は YAML を copy するのではなく、name で参照します。

4. **Steps の image tags を pin します。** Step images で `latest` tags を使用しないでください。reproducible builds を保証するため、特定の versions（例: `golang:1.22.4`, `kaniko:v1.23.2`）に pin します。

5. **lightweight data passing には Results を使用します。** commit SHAs、image tags、status flags は Results 経由で渡します。source code や build artifacts のような large data には Workspaces を使用します。

### 9.2 Security

1. **long-lived credentials の代わりに IRSA を使用します。** AWS access keys を Kubernetes Secrets として保存しないでください。ECR、S3、KMS access には IRSA-annotated ServiceAccounts を使用します。

2. **可能な場合は build containers を non-root として実行します。** Task stepTemplate で `securityContext.runAsNonRoot: true` を設定します。Kaniko には root が必要ですが、他の多くの Steps では不要です。

3. **build namespaces を isolate します。** Tekton builds は dedicated namespace で実行し、必要な registries と APIs のみに egress を制限する NetworkPolicies を設定します。

4. **webhook secrets を定期的に rotate します。** CronJob または external secret manager を使用して GitHub/GitLab webhook secrets を rotate し、対応する Kubernetes Secrets を更新します。

5. **すべての production builds で Tekton Chains を enable します。** Supply chain security は optional ではありません。production に deploy されるすべての image は、verified signature と SLSA provenance を持つべきです。

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

1. **Go modules、npm packages、Maven repositories には Workspace caching を使用します。** PVC-backed Persistent Workspaces により、build のたびに dependencies を再 download することを避けられます。

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

2. **Kaniko layer caching を enable します。** multi-stage Docker builds を高速化するため、ECR repository を layer cache として使用します。

```yaml
# In the kaniko build step args
- --cache=true
- --cache-repo=123456789012.dkr.ecr.us-east-1.amazonaws.com/kaniko-cache
- --cache-ttl=168h  # 7 days
```

3. **affinity assistant を disable します。** affinity assistant は Workspace PVCs が Pods と co-located されるようにしますが、parallelism を制限します。`ReadWriteMany` PVCs または `emptyDir` workspaces を使用する場合は disable します。

```yaml
# In feature-flags ConfigMap
disable-affinity-assistant: "true"
```

4. **build workloads には node selectors を使用します。** fast local storage と high CPU を備えた dedicated node groups に build Pods を schedule します。

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

5. **aggressive timeouts を設定します。** runaway builds が resources を無期限に消費することを防ぎます。Pipeline-level、Task-level、finally-block timeouts を設定します。

### 9.4 Cost Optimization

1. **build nodes には Spot instances を使用します。** Build workloads は本質的に interruptible です。build Pods 用に Spot-only NodePool を Karpenter で使用します。

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

2. **build infrastructure を zero まで scale します。** active な PipelineRuns がない場合、Karpenter は build nodes を drain して terminate します。idle periods の compute cost は zero です。

3. **PVCs を積極的に clean up します。** pre-provisioned PVCs ではなく、PipelineRuns の `volumeClaimTemplate` を使用します。PVC は PipelineRun が garbage-collected されると自動的に delete されます。

4. **Step resource requests を right-size します。** builds を profile し、正確な CPU/memory requests を設定します。over-provisioned build containers は node resources を無駄にします。

---

## 10. References

### External References

- [Tekton Documentation](https://tekton.dev/docs/) - 公式 Tekton project documentation
- [Tekton Hub](https://hub.tekton.dev/) - reusable Tasks と Pipelines の catalog
- [Tekton Chains Documentation](https://tekton.dev/docs/chains/) - Tekton による supply chain security
- [SLSA Framework](https://slsa.dev/) - Supply-chain Levels for Software Artifacts
- [Sigstore / Cosign](https://docs.sigstore.dev/) - Container image signing と verification
- [CD Foundation](https://cd.foundation/) - Continuous Delivery Foundation（Tekton の home）
- [Kaniko](https://github.com/GoogleContainerTools/kaniko) - Docker daemon を使わない container image builds
- [in-toto Attestation Framework](https://in-toto.io/) - Software supply chain attestation

### Internal References

- [CI Pipelines (GitLab Runner, GitHub Actions on EKS)](./03-ci-pipelines.md) - EKS-based CI runner infrastructure
- [ArgoCD Installation](../gitops/argocd/01-installation.md) - ArgoCD setup と configuration
- [Image Security](../security/07-image-security.md) - Container image scanning、signing、admission policies
- [GitOps Multi-Cluster](./04-gitops-multi-cluster.md) - ArgoCD による multi-cluster deployment
- [Secrets Management](../security/05-secrets-management.md) - Kubernetes secret handling best practices
- [Kyverno Policy Management](../security/01-kyverno-policy-management.md) - Kubernetes の policy enforcement
