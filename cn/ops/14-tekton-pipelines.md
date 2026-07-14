# Tekton Pipelines
> **支持版本**: Tekton Pipelines v0.62+, Tekton Triggers v0.28+
> **最后更新**: June 2025

< [上一篇：FinOps 成本可视化平台](./13-finops-cost-platform.md) | [目录](./README.md) | [下一篇：无] >

---

## 概述

Tekton 是一个 Kubernetes-native、开源的 CI/CD 系统构建框架。与那些把 Kubernetes 作为事后补充接入的传统 CI 平台不同，Tekton 将 pipelines 作为一等 Kubernetes resources 运行：每个 Task 都是一个 Pod，每个 Step 都是一个 container，每个 Pipeline 都由监听 Custom Resource Definitions (CRDs) 的自定义 controllers 编排。这使 Tekton 天然具备可移植性、可扩展性，并与 Kubernetes 生态系统深度集成。

Tekton 最初诞生于 Google，是 Knative 项目（具体是 `knative/build`）的一部分，随后于 2019 年捐赠给 Continuous Delivery Foundation (CDF)，与 Jenkins、Jenkins X 和 Spinnaker 并列。它已毕业成为成熟的 CDF 项目，并且通过与 Sigstore、in-toto 等项目的集成成为 CNCF 生态参与者。

### 为什么选择 Tekton 而不是传统 CI/CD？

传统 CI/CD 系统（Jenkins、GitHub Actions、GitLab CI）作为集中式服务运行，并将工作分发到 runners。这种模型在 Kubernetes 环境中会带来若干挑战：

- **基础设施重复**：Jenkins controller 与 Kubernetes cluster 并行运行，需要单独考虑可用性、存储和扩缩容。
- **Secret 蔓延**：CI 平台需要自己的凭证存储，重复了 Kubernetes 已经通过 Secrets、IRSA 和 Pod Identity 管理的内容。
- **有限的 Kubernetes 感知能力**：外部 CI 系统缺少对 Kubernetes APIs 的原生访问，需要配置 kubectl 并分发 kubeconfig。
- **Vendor lock-in**：Pipeline 定义与 CI 平台专有的 YAML 或 Groovy DSL 紧密耦合。

Tekton 通过将 pipelines 定义为 Kubernetes CRDs 来消除这些问题。cluster 同时是执行环境和编排层。

### Tekton 与其他 CI/CD 平台对比

| 功能 | Tekton | Jenkins | GitHub Actions | GitLab CI |
|---------|--------|---------|----------------|-----------|
| **运行时** | Kubernetes-native (CRDs) | 基于 JVM 的 controller | GitHub 托管 / self-hosted runners | GitLab 托管 / self-hosted runners |
| **Pipeline 定义** | Kubernetes YAML | Groovy (Jenkinsfile) | GitHub YAML | GitLab YAML |
| **可扩展性** | 随 Kubernetes 扩展（每个 TaskRun 一个 Pod） | 需要 agent 管理 | Runner autoscaling | Runner autoscaling |
| **可移植性** | 任意 Kubernetes cluster | 任意带 JVM 的 server | GitHub 生态系统 | GitLab 生态系统 |
| **供应链安全** | Tekton Chains (SLSA, Sigstore) | 需要插件 | Artifact attestations | Dependency scanning |
| **事件处理** | Tekton Triggers (webhooks, CEL) | Webhook + 插件 | 原生 GitHub 事件 | 原生 GitLab 事件 |
| **UI/Dashboard** | Tekton Dashboard（可选） | Jenkins UI（内置） | GitHub UI（内置） | GitLab UI（内置） |
| **Secret 管理** | Kubernetes Secrets, IRSA, CSI driver | Jenkins Credentials | GitHub Secrets | GitLab CI Variables |
| **学习曲线** | 中等（需要 Kubernetes 知识） | 高（Groovy、插件生态） | 低（熟悉的 YAML） | 低（熟悉的 YAML） |
| **成本** | 免费（仅计算资源） | 免费（基础设施维护） | 按分钟计费（托管） | 按分钟计费（托管） |

### 学习目标

完成本指南后，你将能够：

- 理解 Tekton 的架构，以及其 CRDs 如何映射到 CI/CD 概念
- 在 Amazon EKS 上安装并配置 Tekton Pipelines、Triggers、Dashboard 和 Chains
- 编写可复用的 Tasks，包含 Step 组合、script 执行、results 和 sidecars
- 构建包含并行执行、条件逻辑和 finally blocks 的多阶段 Pipelines
- 使用 Tekton Triggers 配置基于 webhook 的自动 pipeline 触发
- 使用 Tekton Chains 实现供应链安全，包括 OCI image signing 和 SLSA provenance
- 将 Tekton (CI) 与 ArgoCD (CD) 集成，形成完整的基于 GitOps 的 CI/CD 架构
- 在生产环境中通过清理策略、监控和故障排查策略运行 Tekton

---

## 1. Tekton 架构

Tekton 使用一组 Custom Resource Definitions (CRDs) 扩展 Kubernetes API，用于建模 CI/CD 概念。Tekton controller 监听这些 CRDs，并将期望状态调谐为 Pods 和 containers。

### 1.1 核心 CRDs

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

**Task**：一个可复用、可参数化的工作单元。每个 Task 定义一个或多个 Steps，这些 Steps 在单个 Pod 内的 containers 中按顺序执行。Tasks 还会声明 Workspaces（用于共享数据）和 Results（用于输出值）。

**TaskRun**：使用具体参数值和 workspace bindings 实例化的 Task。创建 TaskRun 会使 controller 启动一个 Pod 来执行该 Task 的 Steps。

**Pipeline**：Tasks 的有序集合。Pipelines 定义执行顺序（顺序、并行或基于 DAG）、Tasks 之间的参数传递、条件执行（when expressions）以及用于清理的 finally blocks。

**PipelineRun**：Pipeline 的实例化。创建 PipelineRun 会使 controller 为 Pipeline 中的每个 Task 创建 TaskRuns。

**Workspace**：在 Steps（Task 内）之间或 Tasks（Pipeline 内）之间共享数据的机制。Workspaces 可以由 PersistentVolumeClaims、ConfigMaps、Secrets 或 emptyDir volumes 支撑。

**Result**：由 Task 生成、可供 Pipeline 中下游 Tasks 消费的字符串值。Results 会写入 `/tekton/results/<name>`，并存储在 TaskRun status 中。

### 1.2 Controller 架构

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

**tekton-pipelines-controller**：核心 reconciliation controller。它监听新的 PipelineRun 和 TaskRun resources，创建用于执行的 Pods，监控 container 完成情况，传播 results，并更新 status。

**tekton-pipelines-webhook**：一个 admission webhook，在 Tekton CRDs 持久化之前对其进行验证和变更。它强制执行 schema 正确性并应用默认值。

**tekton-chains-controller**：一个独立 controller，监听 TaskRun 完成事件，自动签名 OCI images，生成 SLSA provenance attestations，并将它们存储到 OCI registries 或 transparency logs 中。

**tekton-triggers-controller**：处理传入的 webhook events（来自 GitHub、GitLab 等），评估 interceptors 和 CEL expressions，并根据 TriggerTemplate 定义创建 PipelineRun resources。

**tekton-dashboard**：一个可选的 Web UI，用于查看 PipelineRuns、TaskRuns、logs 和 cluster resources。

### 1.3 Tekton Chains 与供应链安全

Tekton Chains 是专用于软件供应链安全的组件。当 TaskRun 完成时，Chains 会自动：

1. **签名 OCI images**：使用 Cosign (Sigstore) 对 TaskRun 生成的 OCI images 进行签名
2. **生成 SLSA provenance**：记录构建了什么、来自什么 source、使用哪个 builder
3. **存储 attestations**：将 attestations 作为 image signatures 存储在 OCI registry 中，或存储在 transparency logs (Rekor) 中
4. **生成 in-toto attestation**：生成将 source materials 与 build outputs 关联起来的元数据

这提供了防篡改记录，下游消费者（admission controllers、policy engines）可以在部署 images 之前进行验证。

---

## 2. EKS 安装与配置

### 2.1 前提条件

安装 Tekton 之前，请确保你的 EKS cluster 满足以下要求：

```bash
# Verify cluster version (1.28+)
kubectl version --short

# Verify cluster has sufficient capacity
# Tekton controllers need ~500m CPU and ~512Mi memory total
kubectl top nodes

# Ensure the cluster has a default StorageClass for Workspaces
kubectl get storageclass
```

### 2.2 Tekton Pipelines 安装

```bash
# Install Tekton Pipelines (core)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/previous/v0.62.2/release.yaml

# Verify installation
kubectl get pods -n tekton-pipelines --watch
```

预期输出：

```
NAME                                           READY   STATUS    RESTARTS   AGE
tekton-pipelines-controller-7f6d5b8bc4-xxxxx   1/1     Running   0          30s
tekton-pipelines-webhook-6c9b5d7d8f-xxxxx      1/1     Running   0          30s
```

配置 Tekton Pipelines feature flags：

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

### 2.3 Tekton Triggers 安装

```bash
# Install Tekton Triggers
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/release.yaml

# Install Tekton Triggers Interceptors (required for GitHub/GitLab webhooks)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/previous/v0.28.0/interceptors.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-triggers
```

### 2.4 Tekton Dashboard 安装

```bash
# Install Tekton Dashboard (read-only mode for production)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/previous/v0.46.0/release-full.yaml

# Verify installation
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-dashboard
```

通过 internal ALB Ingress 暴露 Dashboard：

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

### 2.5 Tekton Chains 安装

```bash
# Install Tekton Chains
kubectl apply --filename https://storage.googleapis.com/tekton-releases/chains/previous/v0.22.1/release.yaml

# Verify installation
kubectl get pods -n tekton-chains
```

### 2.6 ECR 和 S3 的 IRSA 配置

向 ECR 推送 images 或向 S3 上传 artifacts 的 Tekton Tasks 需要 IAM 权限。使用 IAM Roles for Service Accounts (IRSA) 授予最小权限访问。

```bash
# Create OIDC provider (skip if already configured)
eksctl utils associate-iam-oidc-provider \
  --cluster my-eks-cluster \
  --region us-east-1 \
  --approve
```

**ECR Push IAM Policy：**

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

**S3 Artifact Upload IAM Policy：**

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

创建带 IRSA annotation 的 ServiceAccount：

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

验证 annotation：

```bash
kubectl get sa tekton-build-sa -n tekton-builds -o yaml
# Should show: eks.amazonaws.com/role-arn annotation
```

---

## 3. Task 编写

Tasks 是 Tekton 中的基础构建块。设计良好的 Task 可复用、可参数化，并产生有意义的 results。

### 3.1 Step 组合

Task 中的每个 Step 都作为同一 Pod 内的一个 container 运行。Steps 按顺序执行，共享同一个 network namespace 和 Workspace volumes。

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

### 3.2 Script 执行

Steps 可以运行 inline scripts 来处理复杂逻辑。`script` 字段接受 container image 中可用的任何解释器。

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

### 3.3 Tasks 之间传递 Results

一个 Task 的 results 可以通过 `$(tasks.<taskName>.results.<resultName>)` 语法被 Pipeline 中的下游 Tasks 引用。Results 默认限制为 4096 bytes。

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

Sidecars 是与 Steps 一起运行的长生命周期 containers，适用于 Docker daemon、集成测试数据库或缓存等服务。

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

### 3.5 来自 Tekton Hub 的可复用 Tasks

[Tekton Hub](https://hub.tekton.dev) 提供了由社区维护的可复用 Tasks catalog。可以将它们直接安装到你的 cluster 中：

```bash
# Install the git-clone Task (official catalog)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.9/git-clone.yaml

# Install the kaniko Task (for building images without Docker daemon)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kaniko/0.7/kaniko.yaml

# Install the kubernetes-actions Task (for kubectl operations)
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/kubernetes-actions/0.2/kubernetes-actions.yaml
```

验证已安装的 Tasks：

```bash
kubectl get tasks -n tekton-builds
```

### 3.6 完整 Build-Push Task（Kaniko + ECR）

此 Task 使用 Kaniko（无需 Docker daemon）构建 container image，并将其推送到 Amazon ECR：

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

## 4. Pipeline 构建

Pipelines 将多个 Tasks 编排为有向无环图 (DAG)。Tasks 可以根据显式依赖并行、条件性或顺序运行。

### 4.1 Task 排序与并行执行

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

在上图中，`lint` 和 `unit-test` 会在 `git-clone` 完成后并行运行。`build-image` 会等待二者都成功。这通过在 Pipeline spec 中使用 `runAfter` 实现。

### 4.2 使用 When Expressions 进行条件执行

When expressions 允许根据参数值或前序 Tasks 的 results 跳过 Tasks：

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

Finally Tasks 无论 Pipeline 成功还是失败都会执行，类似代码中的 `try/finally`。它们非常适合清理、通知和状态报告。

### 4.4 完整 CI/CD Pipeline

以下 Pipeline 实现完整 CI/CD 工作流：clone、test、build、push、scan 和 deploy。

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

### 4.5 运行 Pipeline

创建 PipelineRun 以执行 Pipeline：

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

Tekton Triggers 支持响应外部事件自动执行 Pipeline，例如 Git pushes、pull requests 或任何基于 webhook 的事件。

### 5.1 Trigger 架构

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

**EventListener**：一个 Kubernetes Service，用于接收传入的 webhook HTTP requests，并通过 Triggers 路由它们。

**TriggerBinding**：使用 JSONPath expressions 从传入的 event payload 中提取参数值。

**TriggerTemplate**：用于创建 Tekton resources（通常是 PipelineRuns）的模板，其参数由 TriggerBinding 填充。

**Interceptor**：一个处理步骤，用于验证、过滤和转换传入事件。内置 interceptors 包括 GitHub（webhook signature validation）、GitLab、Bitbucket 和 CEL（Common Expression Language，用于过滤）。

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

### 5.4 带 Interceptors 的 EventListener

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

### 5.5 暴露 EventListener

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

在 GitHub 中配置 webhook：

```
Payload URL:    https://tekton-hooks.mycompany.com
Content type:   application/json
Secret:         <same value as github-webhook-secret>
Events:         Pushes, Pull requests
```

### 5.6 GitLab Interceptor 示例

对于 GitLab webhooks，替换 GitHub interceptor：

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

## 6. Tekton Chains（供应链安全）

Tekton Chains 为你的 CI/CD pipelines 提供自动化供应链安全。它观察 TaskRun 完成情况，并自动生成关于构建了什么、如何构建、从什么 source 构建的加密 attestations。

### 6.1 Chains 工作原理

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

### 6.2 Chains 配置

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

### 6.3 Signing Key 设置

对于基于 key 的 signing（非 keyless），生成 Cosign key pair，并将其存储为 Kubernetes Secret：

```bash
# Generate a Cosign signing key pair
cosign generate-key-pair k8s://tekton-chains/signing-secrets
```

这会在 `tekton-chains` namespace 中创建一个名为 `signing-secrets` 的 Secret，其中包含 private key。public key 会输出到 `cosign.pub`。

对于使用 AWS KMS 的生产环境：

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

更新 Chains config 以使用 KMS：

```yaml
# chains-config-kms.yaml (merge with chains-config)
data:
  sigstore.kms: "awskms:///arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

### 6.4 SLSA Provenance

Tekton Chains 会自动生成 [SLSA](https://slsa.dev/) (Supply-chain Levels for Software Artifacts) provenance attestations。provenance 会记录：

- **Builder**：哪个 Tekton Task/Pipeline 生成了 artifact
- **Source**：git repository、branch 和 commit
- **Build configuration**：Pipeline parameters 和 Task steps
- **Materials**：输入 artifacts（source code、base images）
- **Output**：构建生成的 artifact（image digest）

构建后验证 provenance：

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

SLSA provenance 输出示例（已缩略）：

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

### 6.5 使用 Kyverno 进行策略执行

使用 Kyverno 强制要求只有带有效 provenance 的 signed images 才能部署：

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

## 7. ArgoCD + Tekton 集成

最有效的生产架构会将 CI（build、test、push）与 CD（deploy）分离。Tekton 负责 CI，而 ArgoCD 通过 GitOps 负责 CD。这种分离提供清晰的所有权、独立扩展能力以及可靠的审计轨迹。

### 7.1 CI/CD 分离架构

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

### 7.2 GitOps Repository 更新 Task

成功构建后，Tekton 会更新 GitOps repository 中的 image tag。ArgoCD 检测到变更并调谐 deployment。

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

### 7.3 带 GitOps Handoff 的完整 CI Pipeline

将 GitOps 更新作为 CI Pipeline 中的最后一步添加：

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

### 7.4 ArgoCD Application 配置

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

### 7.5 端到端工作流摘要

1. **Developer pushes** 代码到应用 repository
2. **GitHub webhook** 触发到 Tekton Triggers
3. **EventListener** 接收事件，验证 signature，并使用 CEL 过滤
4. **PipelineRun** 被自动创建
5. **Tekton Pipeline** 运行：clone、test、lint、build、push 到 ECR、security scan
6. **Tekton Chains** 签名 image 并生成 SLSA provenance
7. **GitOps update Task** 将新的 image tag 提交到 GitOps repository
8. **ArgoCD** 检测变更并同步 deployment
9. **Kyverno** 在允许 Pod 运行前验证 image signature
10. **新版本** 被部署到 cluster

---

## 8. 生产运维

### 8.1 PipelineRun 清理策略

PipelineRuns 和 TaskRuns 会在 cluster 中累积并消耗 etcd 存储。配置自动清理：

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

### 8.2 Resource 管理

为 Tekton controllers 和 build Pods 配置 resource requests 与 limits：

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

使用 LimitRange 为 TaskRun Pods 设置默认 resource limits：

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

设置 ResourceQuota 以限制总构建资源消耗：

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

### 8.3 使用 Prometheus 监控

Tekton 在 controller 的 `:9090/metrics` endpoint 暴露 Prometheus metrics。配置 ServiceMonitor 进行抓取：

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

需要监控的关键 Tekton metrics：

| Metric | 描述 | 告警阈值 |
|--------|-------------|-----------------|
| `tekton_pipelines_controller_pipelinerun_duration_seconds` | PipelineRun 执行时长 | > 30 分钟 |
| `tekton_pipelines_controller_pipelinerun_count` | 按 status 统计的 PipelineRun 总数 | 高失败率 |
| `tekton_pipelines_controller_taskrun_duration_seconds` | TaskRun 执行时长 | > 15 分钟 |
| `tekton_pipelines_controller_taskrun_count` | 按 status 统计的 TaskRun 总数 | 高失败率 |
| `tekton_pipelines_controller_running_pipelineruns_count` | 当前运行中的 PipelineRuns | > 20 并发 |
| `tekton_pipelines_controller_client_latency` | API server 请求延迟 | > 5 秒 |
| `tekton_triggers_eventlistener_event_count` | 传入 webhook events | 降至 0（表示 webhook 失败） |

用于告警的 PrometheusRule：

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

### 8.4 日志管理

将 Tekton build logs 转发到集中式日志系统：

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

### 8.5 故障排查指南

| 症状 | 可能原因 | 解决方法 |
|---------|---------------|------------|
| PipelineRun 卡在 `Running` | Pod 调度失败或 Step 挂起 | 检查 TaskRun Pod 的 `kubectl describe pod`；查找 resource quota 耗尽或 node affinity 问题 |
| TaskRun 因 `ImagePullBackOff` 失败 | image reference 不正确或缺少 registry credentials | 验证 image URL，并确认 ServiceAccount 有 imagePullSecrets 或 IRSA annotation |
| Workspace volume 未挂载 | PVC provisioning 失败或缺少 StorageClass | 在 build namespace 中检查 `kubectl get pvc`；验证 StorageClass 存在且容量可用 |
| EventListener 未收到事件 | Webhook URL 配置错误或 Ingress 问题 | 验证 Ingress 健康；检查 EventListener Pod 的 `kubectl logs`；使用 `curl -X POST` 测试 |
| Chains 未签名 images | Chains controller 未配置或缺少 signing key | 检查 `kubectl logs -n tekton-chains`；验证 `signing-secrets` Secret 存在；检查 `chains-config` ConfigMap |
| Results 过大 | Result 超过 4096-byte 限制 | 使用 Workspaces 而不是 Results 在 Tasks 之间传递大数据 |
| Build 磁盘耗尽 | Workspace PVC 对 build cache 来说太小 | 增加 PipelineRun workspace volumeClaimTemplate 中的 PVC 大小 |
| Parallel Tasks 成为瓶颈 | 过多并发 PipelineRuns 超出 node capacity | 设置 ResourceQuota limits；使用 PriorityClasses 确保关键 builds 优先调度 |

常用调试命令：

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

## 9. 最佳实践

### 9.1 Task 复用模式

1. **保持 Tasks 小而专注。** 一个 Task 应该只把一件事做好（clone、build、scan、deploy）。避免将 build、test 和 deploy 合并到一个 500 行 script 中的单体 Tasks。小 Tasks 可在 Pipelines 之间复用，并且更容易调试。

2. **对所有内容参数化。** 对 image versions、flags、thresholds 和 paths 使用 params。这使 Tasks 无需修改即可跨项目复用。

3. **将内部 Tasks 发布到共享 namespace。** 为组织级可复用 Tasks 创建 `tekton-catalog` namespace。团队按名称引用它们，而不是复制 YAML。

4. **固定 Step 中的 image tags。** 永远不要在 Step images 中使用 `latest` tags。固定到具体版本（例如 `golang:1.22.4`、`kaniko:v1.23.2`），以确保可复现 builds。

5. **使用 Results 传递轻量数据。** 通过 Results 传递 commit SHAs、image tags 和 status flags。对 source code 和 build artifacts 等大数据使用 Workspaces。

### 9.2 安全

1. **使用 IRSA 而不是长期凭证。** 永远不要将 AWS access keys 存储为 Kubernetes Secrets。对 ECR、S3 和 KMS 访问使用带 IRSA annotation 的 ServiceAccounts。

2. **尽可能以非 root 运行 build containers。** 在 Task stepTemplate 中设置 `securityContext.runAsNonRoot: true`。Kaniko 需要 root，但大多数其他 Steps 不需要。

3. **隔离 build namespaces。** 在专用 namespace 中运行 Tekton builds，并使用 NetworkPolicies 将 egress 限制为仅必要 registries 和 APIs。

4. **定期轮换 webhook secrets。** 使用 CronJob 或 external secret manager 轮换 GitHub/GitLab webhook secrets，并更新对应的 Kubernetes Secrets。

5. **为所有生产 builds 启用 Tekton Chains。** 供应链安全不是可选项。部署到生产环境的每个 image 都应具有可验证的 signature 和 SLSA provenance。

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

### 9.3 性能优化

1. **为 Go modules、npm packages 和 Maven repositories 使用 Workspace caching。** 由 PVCs 支撑的持久 Workspaces 可以避免每次 build 都重新下载依赖。

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

2. **启用 Kaniko layer caching。** 使用 ECR repository 作为 layer cache，以加速多阶段 Docker builds：

```yaml
# In the kaniko build step args
- --cache=true
- --cache-repo=123456789012.dkr.ecr.us-east-1.amazonaws.com/kaniko-cache
- --cache-ttl=168h  # 7 days
```

3. **禁用 affinity assistant。** affinity assistant 会确保 Workspace PVCs 与 Pods 位于同一位置，但它会限制并行性。使用 `ReadWriteMany` PVCs 或 `emptyDir` workspaces 时，请禁用它：

```yaml
# In feature-flags ConfigMap
disable-affinity-assistant: "true"
```

4. **为 build workloads 使用 node selectors。** 将 build Pods 调度到具有快速本地存储和高 CPU 的专用 node groups：

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

5. **设置严格 timeouts。** 防止失控 builds 无限期消耗资源。设置 Pipeline-level、Task-level 和 finally-block timeouts。

### 9.4 成本优化

1. **为 build nodes 使用 Spot instances。** Build workloads 天然可中断。使用 Karpenter 和仅 Spot 的 NodePool 来承载 build Pods：

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

2. **将 build 基础设施扩缩到零。** 当没有活动 PipelineRuns 时，Karpenter 会 drain 并终止 build nodes。空闲期间计算成本为零。

3. **积极清理 PVCs。** 在 PipelineRuns 中使用 `volumeClaimTemplate`，而不是预置 PVCs。PipelineRun 被垃圾回收时，PVC 会自动删除。

4. **合理调整 Step resource requests。** 分析你的 builds，并设置准确的 CPU/memory requests。过度配置的 build containers 会浪费 node resources。

---

## 10. 参考资料

### 外部参考

- [Tekton Documentation](https://tekton.dev/docs/) - 官方 Tekton 项目文档
- [Tekton Hub](https://hub.tekton.dev/) - 可复用 Tasks 和 Pipelines 的 catalog
- [Tekton Chains Documentation](https://tekton.dev/docs/chains/) - 使用 Tekton 实现供应链安全
- [SLSA Framework](https://slsa.dev/) - Supply-chain Levels for Software Artifacts
- [Sigstore / Cosign](https://docs.sigstore.dev/) - Container image signing 与 verification
- [CD Foundation](https://cd.foundation/) - Continuous Delivery Foundation（Tekton 的归属组织）
- [Kaniko](https://github.com/GoogleContainerTools/kaniko) - 无需 Docker daemon 的 container image builds
- [in-toto Attestation Framework](https://in-toto.io/) - 软件供应链 attestation

### 内部参考

- [CI Pipelines (GitLab Runner, GitHub Actions on EKS)](./03-ci-pipelines.md) - 基于 EKS 的 CI runner 基础设施
- [ArgoCD Installation](../gitops/argocd/01-installation.md) - ArgoCD 设置与配置
- [Image Security](../security/07-image-security.md) - Container image scanning、signing 和 admission policies
- [GitOps Multi-Cluster](./04-gitops-multi-cluster.md) - 使用 ArgoCD 进行多 cluster deployment
- [Secrets Management](../security/05-secrets-management.md) - Kubernetes secret 处理最佳实践
- [Kyverno Policy Management](../security/01-kyverno-policy-management.md) - Kubernetes 的策略执行
