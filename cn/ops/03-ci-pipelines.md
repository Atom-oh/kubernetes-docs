# 基于 EKS 的 CI 流水线：ECR 构建与推送

> **审查基线**：GitLab Runner 19.3.1 / chart 0.92.1、ARC 0.15.0、runner 2.337.0、Docker 29.8.0、Trivy 0.76.0、Node 24
> **最后审阅**：2026 年 10 月 16 日。已检查 Helm/TOML/CI schema、本地测试替身以及一个小型 Next.js standalone 应用。未运行真实 CI 作业、注册表推送或 AWS 部署。

< [上一节：NLB 蓝绿部署](02-infrastructure-advanced.md) | [目录](README.md) | [下一节：ArgoCD 多集群](04-gitops-multi-cluster.md) >

本指南使用**专用 CI 集群运行受信任的受保护发布作业**。下文的 Docker-in-Docker 具有特权。单独的 Pod 并不是完整的安全边界；不要将公共或不受信任的拉取请求路由到这些 runners，也不要为它们提供继承的 AWS 发布凭证。GitHub 示例在 GitHub 托管的 runners 上运行 PR 测试，并且只在 push 作业中获取 OIDC 凭证。

应用契约是一个 npm 项目，包含 `package-lock.json`、可正常工作的 `lint`/`test` 脚本以及 Dockerfile。请根据应用调整这些命令。即使 runners 运行在 EKS 上，GitHub/GitLab API、注册表、软件包仓库和 AWS 端点仍然是网络依赖项。

## 1. ECR 仓库设置

保持应用标签不可变，并将可变的 BuildKit 缓存引用放入**不同的仓库**。唯一的提交/运行/作业标签可减少冲突；部署时使用已批准的摘要。仅采用 SHA 格式的标签并不能实现不可变性控制。对于已发布构建的重试，应复用经过验证的摘要，或创建新的构建标识符，而不是覆盖发布标签。

Terraform 示例假定 CI EKS 集群和账户的 GitHub OIDC 提供商已经存在。它将 GitLab manager 的 S3 缓存角色与构建 Pod 的 ECR 发布角色分开。ARC 作业 Pod 没有 Pod Identity 发布角色：受信任的工作流使用自己的 GitHub OIDC 角色。

```hcl
# main.tf
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.69.1" }
  }
}
provider "aws" { region = var.region }
data "aws_caller_identity" "current" {}
data "aws_eks_cluster" "ci" { name = var.cluster_name }
locals {
  tags = { Project = var.project_name, ManagedBy = "terraform" }
}
resource "aws_ecr_repository" "application" {
  name                 = "${var.project_name}/application"
  image_tag_mutability = "IMMUTABLE"
  encryption_configuration { encryption_type = "AES256" }
  tags = local.tags
}
resource "aws_ecr_repository" "build_cache" {
  name                 = "${var.project_name}/build-cache"
  image_tag_mutability = "MUTABLE"
  encryption_configuration { encryption_type = "AES256" }
  tags = local.tags
}
# This minimal rule leaves tagged releases alone. Preview before applying any
# additional tagged-image retention rules; ECR does not know current EKS usage.
resource "aws_ecr_lifecycle_policy" "application" {
  repository = aws_ecr_repository.application.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Expire untagged images after 14 days"
    selection    = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 14 }
    action       = { type = "expire" }
  }] })
}
resource "aws_ecr_lifecycle_policy" "build_cache" {
  repository = aws_ecr_repository.build_cache.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Cache is disposable, not a release retention policy"
    selection    = { tagStatus = "any", countType = "sinceImagePushed", countUnit = "days", countNumber = 14 }
    action       = { type = "expire" }
  }] })
}
resource "aws_s3_bucket" "runner_cache" {
  bucket_prefix = "docs-ci-cache-"
  tags          = local.tags
}
resource "aws_s3_bucket_public_access_block" "runner_cache" {
  bucket                  = aws_s3_bucket.runner_cache.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "runner_cache" {
  bucket = aws_s3_bucket.runner_cache.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "runner_cache" {
  bucket = aws_s3_bucket.runner_cache.id
  rule {
    id     = "runner-cache"
    status = "Enabled"
    filter { prefix = "runner/" }
    expiration { days = 14 }
  }
}
resource "aws_iam_role" "gitlab" {
  for_each    = toset(["manager", "build"])
  name_prefix = "gitlab-${each.key}-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = { StringEquals = {
        "aws:RequestTag/eks-cluster-arn"            = data.aws_eks_cluster.ci.arn
        "aws:RequestTag/kubernetes-namespace"       = "gitlab-ci"
        "aws:RequestTag/kubernetes-service-account" = "gitlab-${each.key}"
      } }
    }]
  })
  tags = local.tags
}
resource "aws_eks_pod_identity_association" "gitlab" {
  for_each        = aws_iam_role.gitlab
  cluster_name    = var.cluster_name
  namespace       = "gitlab-ci"
  service_account = "gitlab-${each.key}"
  role_arn        = each.value.arn
}
resource "aws_iam_policy" "ecr_publish" {
  name_prefix = "docs-ci-ecr-"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "ecr:GetAuthorizationToken", Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = var.region } } },
      {
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage", "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload"]
        Resource = [aws_ecr_repository.application.arn, aws_ecr_repository.build_cache.arn]
      }
    ]
  })
}
resource "aws_iam_role_policy_attachment" "gitlab_build" {
  role       = aws_iam_role.gitlab["build"].name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
resource "aws_iam_role_policy" "gitlab_manager_cache" {
  role = aws_iam_role.gitlab["manager"].name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.runner_cache.arn}/runner/*" },
      { Effect = "Allow", Action = "s3:GetBucketLocation", Resource = aws_s3_bucket.runner_cache.arn }
    ]
  })
}
# Reuse the account's existing GitHub OIDC provider; do not create a duplicate.
resource "aws_iam_role" "github_publish" {
  name_prefix = "github-ci-publish-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.github_oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = { "token.actions.githubusercontent.com:sub" = [
          "repo:${var.github_repository}:ref:refs/heads/main",
          "repo:${var.github_repository}:ref:refs/tags/v*"
        ] }
      }
    }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "github_publish" {
  role       = aws_iam_role.github_publish.name
  policy_arn = aws_iam_policy.ecr_publish.arn
}
```

```hcl
# variables.tf
variable "region" {
  type    = string
  default = "ap-northeast-2"
}
variable "project_name" {
  type    = string
  default = "docs-ci"
}
variable "cluster_name" { type = string }
variable "github_oidc_provider_arn" {
  description = "Existing account OIDC provider for token.actions.githubusercontent.com"
  type        = string
}
variable "github_repository" {
  description = "Exact owner/repository; protect main and v* release tags in GitHub"
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Supply an exact owner/repository, without wildcards."
  }
}
```

```hcl
# outputs.tf
output "application_repository" { value = aws_ecr_repository.application.name }
output "application_url" { value = aws_ecr_repository.application.repository_url }
output "cache_repository" { value = aws_ecr_repository.build_cache.name }
output "cache_url" { value = aws_ecr_repository.build_cache.repository_url }
output "runner_cache_bucket" { value = aws_s3_bucket.runner_cache.id }
output "github_publish_role_arn" { value = aws_iam_role.github_publish.arn }
```

为此 root 使用独立的受保护后端/state，并在应用前审查 plan。将缓存 bucket 输出填入 GitLab values，并将仓库名称/角色 ARN 填入 CI 变量。EKS Pod Identity 关联不会创建 ServiceAccounts；还必须创建下文对应的账户。

### 保留、扫描与复制

- 生命周期前缀/模式列表是对镜像标签的 **AND 条件**，不是分支的 OR 列表。ECR 不知道 EKS 当前正在运行哪些镜像，也不知道你需要哪些回滚版本。添加带标签镜像的过期规则前，请预览策略并审查保留要求。
- 注册表扫描配置作用于账户/Region。基本 ECR 扫描事件和 Inspector 增强调查结果使用不同的 schema。持续扫描优先于匹配的推送时扫描规则；宽泛的 `*` 持续扫描规则不会让较窄的 dev 规则继续采用仅推送时扫描。
- High 和 Critical 是可选的严重性值，而不是必须同时为正值的两个字段。扫描失败或未完成，不代表镜像干净。下方 CI Trivy 门禁独立于 ECR/Inspector 通知。
- 跨账户拉取镜像需要仓库资源策略以及适当的调用方身份权限，其中包括 ECR 授权令牌访问权限。应优先授予特定角色，而不是将权限授予账户中的所有主体。
- 跨账户复制还需要目标注册表权限。复制是异步的，不会自动回填现有镜像，也不会复制所有生命周期/扫描/仓库设置。

完整的注册表级替代方案请参阅已审查的 [Amazon ECR 指南](../container-registry/02-amazon-ecr.md)，关于晋级、保留和签名的内容请参阅[注册表实践](../container-registry/04-best-practices.md)。不要让每个应用堆栈都覆盖同一份共享注册表配置。

## 2. 在 EKS 上运行 GitLab Runner

### Service accounts 和受保护的 runner 注册

使用下方的 namespace/accounts。创建**两个服务器端项目 runner**，启用受保护访问并设置标签 `eks-ci-amd64` 和 `eks-ci-arm64`，然后创建它们的认证令牌 Secrets。采用现代认证令牌工作流时，应在 GitLab 上配置标签/保护/允许未标记作业，不要假设旧的注册标志或 Helm values 会更新这些设置。

```yaml
# gitlab-prerequisites.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gitlab-ci
  labels:
    pod-security.kubernetes.io/enforce: privileged
---
# No Kubernetes API token is needed by build jobs. AWS Pod Identity uses its
# own projected token, provided by the configured association.
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitlab-build
  namespace: gitlab-ci
automountServiceAccountToken: false

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitlab-manager
  namespace: gitlab-ci
```

将令牌存储在 Git 和 Terraform values/state 之外。chart 会使用 `gitlab-ci` 中名为 `gitlab-runner-auth-amd64` 和 `gitlab-runner-auth-arm64` 的现有 Secrets。它需要 `runner-token` 和兼容键 `runner-registration-token`（值为空）。使用受保护的文件或外部 Secret 工作流；不要在 shell 命令行中放入令牌值：

```bash
# Repeat for the ARM runner using its own protected token file and Secret name.
kubectl create secret generic gitlab-runner-auth-amd64 -n gitlab-ci \
  --from-file=runner-token=/protected/gitlab-amd64-token \
  --from-literal=runner-registration-token=''
```

令牌轮换应与实际的 Secret 来源及 runner 重新加载/重启行为协调。manager ServiceAccount 需要 Kubernetes API 访问权限；构建 Pod 会禁用常规 Kubernetes API token，而 Pod Identity 会提供单独的 AWS token。

### 稳定的 Helm values 和 runner 配置

下面是 AMD64 release。请使用带版本号的 chart，而不是开发分支的 `bleeding` appVersion。ARM 变体需要更改 manager/job 架构和 token Secret；两个 manager 都可以使用预先创建的 manager ServiceAccount。

```yaml
# gitlab-values.yaml
# GitLab Runner chart 0.92.1 / Runner 19.3.1. Trusted protected jobs only.
gitlabUrl: https://gitlab.example.com/
concurrent: 4
checkInterval: 3
rbac:
  create: true
  clusterWideAccess: false
  rules:
    - apiGroups: [""]
      resources: [pods]
      verbs: [create, delete, get, list, watch]
    - apiGroups: [""]
      resources: [pods/attach, pods/exec]
      verbs: [create, delete, get, patch]
    - apiGroups: [""]
      resources: [pods/log]
      verbs: [get, list]
    - apiGroups: [""]
      resources: [secrets]
      verbs: [create, delete, get, update]
    - apiGroups: [""]
      resources: [services]
      verbs: [create, get]
    - apiGroups: [""]
      resources: [serviceaccounts]
      verbs: [get]
    - apiGroups: [""]
      resources: [events]
      verbs: [list, watch]
serviceAccount:
  create: false
  name: gitlab-manager
resources:
  requests: {cpu: 200m, memory: 256Mi}
  limits: {cpu: "1", memory: 512Mi}
nodeSelector:
  workload-type: ci-builder
  kubernetes.io/arch: amd64
tolerations:
  - key: ci-builder
    operator: Equal
    value: "true"
    effect: NoSchedule
service:
  enabled: true
metrics:
  enabled: true
  serviceMonitor:
    enabled: false
runners:
  secret: gitlab-runner-auth-amd64
  config: |
    [[runners]]
      executor = "kubernetes"
      [runners.kubernetes]
        namespace = "gitlab-ci"
        service_account = "gitlab-build"
        automount_service_account_token = false
        image = "docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66"
        privileged = true
        poll_interval = 3
        poll_timeout = 600
        cpu_request = "500m"
        cpu_limit = "2"
        memory_request = "1Gi"
        memory_limit = "4Gi"
        helper_cpu_request = "100m"
        helper_memory_request = "128Mi"
        helper_image_autoset_arch_and_os = true
        [runners.kubernetes.node_selector]
          "workload-type" = "ci-builder"
          "kubernetes.io/arch" = "amd64"
        [runners.kubernetes.node_tolerations]
          "ci-builder=true" = "NoSchedule"
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-certs"
          mount_path = "/certs/client"
          medium = "Memory"
      [runners.cache]
        Type = "s3"
        Path = "runner"
        Shared = true
        [runners.cache.s3]
          BucketName = "REPLACE_CACHE_BUCKET"
          BucketLocation = "ap-northeast-2"
          AuthenticationType = "iam"
```

`node_tolerations` 是 TOML map。`poll_interval` 用于检查新建的 Kubernetes Pods；Helm `checkInterval`/runner `check_interval` 则用于 coordinator 作业轮询。两者并非同义项。helper 版本与 Runner 19.3.1 对应；架构由显式 node selector 选择，而不是通过 `x86_64-latest` helper 覆盖项选择。

Metrics 属于 manager，而非每个构建 Pod。在 CRD 和监控设置就绪前，ServiceMonitor 保持禁用。未设置 `RoleARN` 时，S3 `AuthenticationType=iam` 使用 manager 凭证链；设置 `RoleARN` 会改变缓存凭证行为，因此需要单独审查策略。

```bash
# After namespace, accounts, Secrets, IAM associations, and CI nodes are ready.
helm upgrade --install gitlab-amd64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-values.yaml
# Use a separate token and replace both amd64 selectors with arm64 in the ARM values.
helm upgrade --install gitlab-arm64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-arm64-values.yaml
```

### CI 工具镜像和流水线

Docker 官方镜像不包含流水线使用的所有 AWS 命令。请在受信任的引导环境中为两种架构构建、扫描并发布此工具镜像。将 `CI_TOOLS_IMAGE` 设置为经批准的不可变索引摘要。Alpine 3.24 为 AMD64 和 ARM64 提供 AWS CLI；请记录生成的镜像摘要，不要假设后续软件包重建的字节完全一致。

```dockerfile
# Dockerfile.ci-tools
# Build in a trusted bootstrap environment, scan, and publish with an immutable digest.
FROM docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66
RUN apk add --no-cache bash aws-cli jq
```

该流水线使用原生矩阵作业，并建立一对一的 build → scan → publish 依赖关系；GitLab 19.3 支持这种方式。每个归档都会在发布前进行扫描，且扫描的是将要发布的同一个镜像。Trivy 原生 JSON 是可下载的 artifact，不会被误标为 GitLab 的 container-scanning 报告 schema。每种架构最终的摘要文件名各不相同，从而避免 manifest 作业中的 artifact 覆盖。

```yaml
# gitlab-ci.yaml
# The registered runner must be protected and limited to this trusted project.
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "push" && $CI_COMMIT_REF_PROTECTED == "true" && ($CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH || $CI_COMMIT_TAG =~ /^v[0-9]+\.[0-9]+\.[0-9]+$/)'
    - when: never
stages: [test, build, scan, publish, manifest]
variables:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: REPLACE_ACCOUNT.dkr.ecr.ap-northeast-2.amazonaws.com
  ECR_REPOSITORY: docs-ci/application
  ECR_CACHE_REPOSITORY: docs-ci/build-cache
  # Publish Dockerfile.ci-tools first; replace with its approved immutable image URI.
  CI_TOOLS_IMAGE: registry.example.invalid/ci-tools@sha256:REPLACE_DIGEST
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: /certs
  DOCKER_TLS_VERIFY: "1"
  DOCKER_CERT_PATH: /certs/client

default:
  tags: [eks-ci-amd64]

.native: &native
  tags: [$RUNNER]
  parallel:
    matrix:
      - ARCH: amd64
        RUNNER: eks-ci-amd64
      - ARCH: arm64
        RUNNER: eks-ci-arm64

test:
  stage: test
  image: docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run lint
    - npm test
  cache:
    key:
      prefix: node24-amd64-protected
      files: [package-lock.json]
    paths: [.npm/]

.docker-job:
  image: $CI_TOOLS_IMAGE
  services:
    - name: docker.io/library/docker@sha256:5efed980cba3fc126cf54e21a5a6ff8849d05b6e0623d6e7612f48e9cd6cd17e
      alias: docker
      variables:
        HEALTHCHECK_TCP_PORT: "2376"
  before_script:
    - |
      set -euo pipefail
      for attempt in $(seq 1 60); do
        docker info >/dev/null 2>&1 && break
        sleep 1
      done
      docker info >/dev/null
      aws ecr get-login-password --region "$AWS_REGION" |
        docker login --username AWS --password-stdin "$ECR_REGISTRY"

build:
  <<: *native
  extends: .docker-job
  stage: build
  needs: [test]
  script:
    - |
      set -euo pipefail
      TAG="sha-${CI_COMMIT_SHA}-${CI_PIPELINE_ID}-${CI_JOB_ID}-${ARCH}"
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY:$TAG"
      docker buildx create --name ci-builder --driver docker-container --use
      docker buildx build --platform "linux/$ARCH" --load \
        --cache-from "type=registry,ref=$ECR_REGISTRY/$ECR_CACHE_REPOSITORY:${ARCH}-protected" \
        --cache-to "type=registry,ref=$ECR_REGISTRY/$ECR_CACHE_REPOSITORY:${ARCH}-protected,mode=max,image-manifest=true,oci-mediatypes=true" \
        --tag "$IMAGE" .
      docker save "$IMAGE" -o image.tar
      printf 'IMAGE_TAG=%s\n' "$TAG" > build.env
  artifacts:
    paths: [image.tar]
    reports:
      dotenv: build.env
    expire_in: 1 day

scan:
  <<: *native
  stage: scan
  image:
    name: docker.io/aquasec/trivy@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222
    entrypoint: [""]
  needs:
    - job: build
      artifacts: true
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
  script:
    - trivy image --input image.tar --scanners vuln --severity HIGH,CRITICAL --exit-code 1 --format json --output trivy-report.json
  artifacts:
    when: always
    paths: [trivy-report.json]
    expire_in: 1 week
  allow_failure: false

publish:
  <<: *native
  extends: .docker-job
  stage: publish
  needs:
    - job: build
      artifacts: true
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
    - job: scan
      artifacts: false
      parallel:
        matrix:
          - ARCH: ['$[[ matrix.ARCH ]]']
            RUNNER: ['$[[ matrix.RUNNER ]]']
  script:
    - |
      set -euo pipefail
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY"
      docker load -i image.tar
      docker push "$IMAGE:$IMAGE_TAG"
      DIGEST="$(docker buildx imagetools inspect "$IMAGE:$IMAGE_TAG" --format '{{.Manifest.Digest}}')"
      [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
      mkdir -p approved
      printf '%s@%s\n' "$IMAGE" "$DIGEST" > "approved/$ARCH.txt"
  artifacts:
    paths: [approved/]
    expire_in: 1 week

manifest:
  extends: .docker-job
  stage: manifest
  tags: [eks-ci-amd64]
  needs:
    - job: publish
      artifacts: true
  script:
    - |
      set -euo pipefail
      IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY"
      AMD64="$(cat approved/amd64.txt)"
      ARM64="$(cat approved/arm64.txt)"
      for REF in "$AMD64" "$ARM64"; do
        [[ "$REF" == "$IMAGE@sha256:"* ]]
        [[ "${REF##*@}" =~ ^sha256:[a-f0-9]{64}$ ]]
      done
      TAG="sha-${CI_COMMIT_SHA}-${CI_PIPELINE_ID}-${CI_JOB_ID}"
      docker buildx imagetools create --tag "$IMAGE:$TAG" "$AMD64" "$ARM64"
      DIGEST="$(docker buildx imagetools inspect "$IMAGE:$TAG" --format '{{.Manifest.Digest}}')"
      [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
      docker buildx imagetools inspect "$IMAGE@$DIGEST" --raw | jq -e '
        [.manifests[].platform | select(.os == "linux") | .architecture]
        | unique | sort | . == ["amd64", "arm64"]
      ' >/dev/null
      printf 'APPROVED_IMAGE=%s@%s\n' "$IMAGE" "$DIGEST" > approved.env
  artifacts:
    reports:
      dotenv: approved.env
    expire_in: 1 week
```

DinD service 需要 runner 配置中的 privileged 设置和共享的 `/certs/client` volume。就绪等待有明确时限。Docker daemon/镜像状态不会保留到另一个作业：镜像归档是显式的交接方式。最终 artifact 标识已批准的多平台索引；获得批准后，应由单独的 GitOps 工作流更新部署清单。

## 3. GitHub Actions Runner Controller

### 当前 runner scale sets

使用官方 OCI scale-set charts。旧版 `RunnerDeployment`、`RunnerSet` 和 `HorizontalRunnerAutoscaler` 属于另一种 controller 模型，并不是这些 charts 安装的资源。当前的 scale-set listener 会根据需求驱动扩缩容；不要添加无关的旧版 webhook deployment 来启用从零扩容。

```yaml
# arc-namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: arc-systems
---
apiVersion: v1
kind: Namespace
metadata:
  name: arc-runners
  labels:
    pod-security.kubernetes.io/enforce: privileged
```

通过已批准的 Secret 工作流，在 `arc-runners` 中创建 `arc-github-app`。其键为 `github_app_id`、`github_app_installation_id` 和 `github_app_private_key`。使用受保护的密钥文件，不要将私钥值内联到 Terraform/Helm values 中。安装 GitHub App 时，应授予所选仓库/组织范围所需的权限和仓库访问权限。

```bash
kubectl create secret generic arc-github-app -n arc-runners \
  --from-literal=github_app_id=REPLACE_ID \
  --from-literal=github_app_installation_id=REPLACE_INSTALLATION_ID \
  --from-file=github_app_private_key=/protected/github-app.pem
```

```yaml
# arc-controller-values.yaml
replicaCount: 1
serviceAccount:
  create: true
  name: arc-controller
resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {cpu: "1", memory: 512Mi}
```

```yaml
# arc-runner-values.yaml
# ARC 0.15.0, Kubernetes >=1.29. Dedicated CI cluster, trusted publish jobs only.
githubConfigUrl: https://github.com/REPLACE_ORG/REPLACE_REPO
githubConfigSecret: arc-github-app
runnerScaleSetName: eks-ci-amd64
minRunners: 0
maxRunners: 4
controllerServiceAccount:
  namespace: arc-systems
  name: arc-controller
# Custom DinD template derived from the versioned chart; do not also set containerMode.
template:
  spec:
    automountServiceAccountToken: false
    nodeSelector:
      workload-type: ci-builder
      kubernetes.io/arch: amd64
    tolerations:
      - key: ci-builder
        operator: Equal
        value: "true"
        effect: NoSchedule
    initContainers:
      - name: init-dind-externals
        image: ghcr.io/actions/actions-runner@sha256:e5496277be5d09bc968b3d64911b74e219ac4a3f2edce956a3ecf9271bea1ef4
        command: [cp, -r, /home/runner/externals/., /home/runner/tmpDir/]
        volumeMounts:
          - name: dind-externals
            mountPath: /home/runner/tmpDir
      - name: dind
        image: docker.io/library/docker@sha256:5efed980cba3fc126cf54e21a5a6ff8849d05b6e0623d6e7612f48e9cd6cd17e
        args: [dockerd, --host=unix:///var/run/docker.sock, "--group=$(DOCKER_GROUP_GID)"]
        env:
          - name: DOCKER_GROUP_GID
            value: "123"
        securityContext:
          privileged: true
        restartPolicy: Always
        startupProbe:
          exec:
            command: [docker, info]
          failureThreshold: 24
          periodSeconds: 5
        resources:
          requests: {cpu: 250m, memory: 512Mi}
          limits: {cpu: "2", memory: 4Gi}
        volumeMounts:
          - name: work
            mountPath: /home/runner/_work
          - name: dind-sock
            mountPath: /var/run
          - name: dind-externals
            mountPath: /home/runner/externals
    containers:
      - name: runner
        image: ghcr.io/actions/actions-runner@sha256:e5496277be5d09bc968b3d64911b74e219ac4a3f2edce956a3ecf9271bea1ef4
        command: [/home/runner/run.sh]
        env:
          - name: DOCKER_HOST
            value: unix:///var/run/docker.sock
          - name: RUNNER_WAIT_FOR_DOCKER_IN_SECONDS
            value: "120"
        resources:
          requests: {cpu: 500m, memory: 1Gi}
          limits: {cpu: "2", memory: 4Gi}
        volumeMounts:
          - name: work
            mountPath: /home/runner/_work
          - name: dind-sock
            mountPath: /var/run
    volumes:
      - name: work
        emptyDir: {}
      - name: dind-sock
        emptyDir: {}
      - name: dind-externals
        emptyDir: {}
```

此自定义模板采用 chart 的 Kubernetes ≥1.29 原生 sidecar DinD 布局，并固定 runner 2.337.0 和 Docker 29.8.0。提供自定义布局时，不要同时设置 `containerMode`。Runner 和 DinD 共用 work/socket 路径以及 runner externals。生成的 runner ServiceAccount 没有发布角色。官方 runner 镜像包含 Docker/Buildx/jq/git，但不包含 AWS CLI；下方工作流会改用 Buildx 获取最终摘要。

对于 ARM，将 `runnerScaleSetName` 更改为 `eks-ci-arm64`，并将节点架构设为 `arm64`。在 `runs-on` 中使用这些实际的 scale-set 名称；组织 runner-group 名称不会自动成为作业标签。ARC 0.15.0 还提供 `scaleSetLabels`，可用于添加其他标签。

```bash
helm upgrade --install arc \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
  --version 0.15.0 --namespace arc-systems --values arc-controller-values.yaml
helm upgrade --install eks-ci-amd64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.15.0 --namespace arc-runners --values arc-runner-values.yaml
helm upgrade --install eks-ci-arm64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.15.0 --namespace arc-runners --values arc-runner-arm64-values.yaml
```

`minRunners` 是在已分配的工作量基础上增加的空闲 runner 下限，但仍受容量/最大值限制。将其设为零可以减少空闲 runner Pods，但不会移除 controller/listener 或所有集群成本。设为非零也不能保证没有启动延迟。应限制允许使用 runner scale sets 的仓库/工作流，并保护发布分支/标签。

### GitHub 工作流

设置仓库变量 `AWS_PUBLISH_ROLE_ARN`、`ECR_REPOSITORY` 和 `ECR_CACHE_REPOSITORY`。IAM 信任策略允许此确切仓库的 main 分支和受保护的 `v*` 标签。GitHub Environment 会改变 OIDC `sub` 的格式；如需添加 Environment，请有意识地调整信任策略。切勿将 `pull_request_target` 与不受信任的 checkout 搭配使用来获取这些凭证。

```yaml
# github-ci.yaml
name: Test and publish native ECR images
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: read
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: '24'
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm test
  publish:
    if: github.event_name == 'push'
    needs: test
    strategy:
      fail-fast: false
      matrix:
        include:
          - arch: amd64
            platform: linux/amd64
            runner: eks-ci-amd64
          - arch: arm64
            platform: linux/arm64
            runner: eks-ci-arm64
    runs-on: ${{ matrix.runner }}
    timeout-minutes: 30
    permissions:
      contents: read
      id-token: write
    env:
      AWS_REGION: ap-northeast-2
      ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
      ECR_CACHE_REPOSITORY: ${{ vars.ECR_CACHE_REPOSITORY }}
    steps:
      - name: Verify the native runner architecture
        env:
          ARCH: ${{ matrix.arch }}
        run: |
          case "$ARCH:$(uname -m)" in
            amd64:x86_64|arm64:aarch64) ;;
            *) echo "Runner architecture does not match the matrix" >&2; exit 1 ;;
          esac
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c # v6.2.4
        with:
          role-to-assume: ${{ vars.AWS_PUBLISH_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
        id: login
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - name: Define a unique build tag
        id: image
        env:
          REGISTRY: ${{ steps.login.outputs.registry }}
          ARCH: ${{ matrix.arch }}
        run: |
          set -euo pipefail
          TAG="sha-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${ARCH}"
          printf 'tag=%s/%s:%s\n' "$REGISTRY" "$ECR_REPOSITORY" "$TAG" >> "$GITHUB_OUTPUT"
      - uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          platforms: ${{ matrix.platform }}
          load: true
          push: false
          tags: ${{ steps.image.outputs.tag }}
          cache-from: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_CACHE_REPOSITORY }}:${{ matrix.arch }}-protected
          cache-to: type=registry,ref=${{ steps.login.outputs.registry }}/${{ env.ECR_CACHE_REPOSITORY }}:${{ matrix.arch }}-protected,mode=max,image-manifest=true,oci-mediatypes=true
      - uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          version: v0.76.0
          image-ref: ${{ steps.image.outputs.tag }}
          scan-type: image
          scanners: vuln
          severity: HIGH,CRITICAL
          exit-code: '1'
      - name: Publish only the scanned image
        env:
          TAGGED_IMAGE: ${{ steps.image.outputs.tag }}
          REGISTRY: ${{ steps.login.outputs.registry }}
          ARCH: ${{ matrix.arch }}
        run: |
          set -euo pipefail
          docker push "$TAGGED_IMAGE"
          DIGEST="$(docker buildx imagetools inspect "$TAGGED_IMAGE" --format '{{.Manifest.Digest}}')"
          [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
          mkdir -p approved
          printf '%s/%s@%s\n' "$REGISTRY" "$ECR_REPOSITORY" "$DIGEST" > "approved/$ARCH.txt"
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: approved-${{ matrix.arch }}
          path: approved/${{ matrix.arch }}.txt
          if-no-files-found: error
          retention-days: 7
  manifest:
    if: github.event_name == 'push'
    needs: publish
    runs-on: eks-ci-amd64
    timeout-minutes: 10
    permissions:
      contents: read
      id-token: write
    env:
      AWS_REGION: ap-northeast-2
      ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
    steps:
      - uses: aws-actions/configure-aws-credentials@cbe3b392738ccf3f987d68400dafcf4b0624a56c # v6.2.4
        with:
          role-to-assume: ${{ vars.AWS_PUBLISH_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      - uses: aws-actions/amazon-ecr-login@03f1aad4c6c7ffd436567f42f9384779290529bd # v2.1.7
        id: login
      - uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        with:
          pattern: approved-*
          path: approved
          merge-multiple: true
      - name: Publish the index of both approved platform digests
        env:
          REGISTRY: ${{ steps.login.outputs.registry }}
        run: |
          set -euo pipefail
          IMAGE="$REGISTRY/$ECR_REPOSITORY"
          AMD64="$(cat approved/amd64.txt)"
          ARM64="$(cat approved/arm64.txt)"
          for REF in "$AMD64" "$ARM64"; do
            [[ "$REF" == "$IMAGE@sha256:"* ]]
            DIGEST="${REF##*@}"
            [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]]
          done
          TAG="sha-${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
          docker buildx imagetools create --tag "$IMAGE:$TAG" "$AMD64" "$ARM64"
          INDEX="$(docker buildx imagetools inspect "$IMAGE:$TAG" --format '{{.Manifest.Digest}}')"
          [[ "$INDEX" =~ ^sha256:[a-f0-9]{64}$ ]]
          docker buildx imagetools inspect "$IMAGE@$INDEX" --raw | jq -e '
            [.manifests[].platform | select(.os == "linux") | .architecture]
            | unique | sort | . == ["amd64", "arm64"]
          ' >/dev/null
          printf '%s@%s\n' "$IMAGE" "$INDEX" > approved-image.txt
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: approved-image
          path: approved-image.txt
          if-no-files-found: error
          retention-days: 7
```

每种原生平台都会在发布其摘要前完成扫描。manifest 作业使用不可变的已批准引用，并验证生成的索引包含 AMD64 和 ARM64。已检查 Action commit 以及输入/运行时定义。部署/签名的输入应是最终摘要，而不是多行 metadata-action 标签输出。如平台有要求，请使用[注册表指南](../container-registry/04-best-practices.md)添加签名和准入验证。

## 4. 原生多平台 CI 节点

以下 Auto Mode 节点池使用标准实例类型要求，而不是特定于自管 provider 的键。它们假定存在默认 NodeClass。请使 manager/job selectors、tolerations、helper 架构和服务器端 runner 标签相互匹配。

```yaml
# nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-amd64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-builder
    spec:
      nodeClassRef: {group: eks.amazonaws.com, kind: NodeClass, name: default}
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [amd64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand, spot]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [c7i.xlarge, m7i.xlarge]
      taints:
        - key: ci-builder
          value: "true"
          effect: NoSchedule
  limits: {cpu: "64", memory: 256Gi}
  disruption: {consolidationPolicy: WhenEmpty, consolidateAfter: 5m}
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-arm64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-builder
    spec:
      nodeClassRef: {group: eks.amazonaws.com, kind: NodeClass, name: default}
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: [arm64]
        - key: karpenter.sh/capacity-type
          operator: In
          values: [on-demand, spot]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: [c7g.xlarge, m7g.xlarge]
      taints:
        - key: ci-builder
          value: "true"
          effect: NoSchedule
  limits: {cpu: "64", memory: 256Gi}
  disruption: {consolidationPolicy: WhenEmpty, consolidateAfter: 5m}
```

Spot 可能会中断构建；应根据工作负载需求选择容量类型和重试策略。原生 runners 和 QEMU 仿真是两种不同的方法。QEMU 执行异构架构指令；它本身并不是交叉编译器。单 runner 多平台构建需要受支持的仿真机制或明确的交叉编译设计。仅设置 platform 标志并不能提供其中任何一种能力。

## 5. 构建优化与维护良好的替代方案

### Next.js standalone 容器

Node 20 已于 2026 年 4 月结束生命周期。此 npm 示例使用 Node 24，并假设单个 Next.js 应用根目录中包含 lockfile。构建需要 dev dependencies；只有从跟踪生成的生产输出中才应省略它们。请显式配置 standalone 输出：

```javascript
export default {
  output: 'standalone'
}
```

```dockerfile
# Dockerfile.next
# syntax=docker/dockerfile:1
FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci

FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public && npm run build

FROM docker.io/library/node@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
```

使用以下 `.dockerignore`：

```text
node_modules
.next
.git
coverage
.npm
.env*
!.env.example
*.log
.npmrc
```

Dockerfile 会复制 public 资源和 `.next/static`，设置可访问的绑定地址，并以镜像中的非 root `node` 用户运行。私有 npm 凭证可以通过 BuildKit secret 提供（`--secret id=npmrc,src=/protected/npmrc`）；不要复制 `.npmrc`，也不要将密钥放入构建参数。monorepo 需要有意设置跟踪根目录，并使嵌套的 `COPY`/server 路径相匹配；此处根目录下的 `server.js` 布局并非通用方案。

使用 Node 24.22.0 构建了一个本地 Next 16.3.5/React 19.3.0 fixture，生成的 standalone server 和复制的静态文件均返回 HTTP 200。这验证的是输出契约，而不是完整应用/容器/CI 部署。

### 缓存行为

注册表缓存会导出构建层。除非单独持久化，否则 `RUN --mount=type=cache` 缓存仅在本地 builder 中有效；注册表 `--cache-to` 不会自动导出所有 cache-mount 目录。可变缓存标签应与不可变的发布仓库分开，且切勿缓存注册表凭证。

应使用声明式变更规则和依赖图，而不是浅层的 `HEAD~1` 测试，或在后台运行命令后仅使用一个可能掩盖失败的裸 `wait`。不要引用不存在的 `tester` Dockerfile 阶段。缓存复用是一种优化，不能证明源代码/测试/扫描工作已成功。

### Kaniko 和 rootless BuildKit

Google 的 Kaniko 仓库已归档。无 daemon 并不意味着每个 Dockerfile 都能在没有 root 的情况下运行，也不意味着构建完全隔离。对于新工作，应使用当前仍在维护的 builder，并核实其实际权限、内核支持、凭证和镜像发布路径。

以下可选 BuildKit 片段应在**另一台经过验证的非特权 runner**上使用，该 runner 的 CI 镜像包含 BuildKit 0.33.0、AWS CLI、jq 和 Bash。它不能直接替换上方具有特权的 DinD 配置。用户命名空间/mount 支持和集群安全策略必须允许所选的 rootless 模式。

```yaml
# rootless-buildkit.yaml
# Alternative fragment for a SEPARATE validated non-privileged runner.
# CI_ROOTLESS_IMAGE must contain BuildKit 0.33.0, aws CLI, jq, and a shell.
# Node user-namespace/mount/security-policy support is a prerequisite.
build-rootless:
  image:
    name: $CI_ROOTLESS_IMAGE
    entrypoint: [""]
  tags: [validated-rootless-runner]
  variables:
    BUILDKITD_FLAGS: --oci-worker-no-process-sandbox
  script:
    - |
      set -euo pipefail
      umask 077
      DOCKER_CONFIG="$(mktemp -d)"
      export DOCKER_CONFIG
      trap 'rm -f "$DOCKER_CONFIG/config.json"; rmdir "$DOCKER_CONFIG"' EXIT
      aws ecr get-login-password --region "$AWS_REGION" |
        awk '{printf "AWS:%s", $0}' | base64 | tr -d '\n' |
        jq -R --arg registry "$ECR_REGISTRY" \
          '{auths:{($registry):{auth:.}}}' > "$DOCKER_CONFIG/config.json"
      buildctl-daemonless.sh build --frontend dockerfile.v0 \
        --local context=. --local dockerfile=. \
        --output type=oci,dest=image.tar
  artifacts:
    paths: [image.tar]
```

输出是 OCI 归档，应传递给匹配的扫描器/发布器。上游 BuildKit 警告，`--oci-worker-no-process-sandbox` 会削弱 daemon 容器内的进程隔离，也无法清理所有残留的构建进程。在 Kubernetes 中使用它是一种权衡，并非普遍适用的安全保证。采用此替代方案前，请验证专用 runner 配置。

## 参考资料

- [GitLab Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/)
- [GitLab Runner 高级配置](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
- [GitLab 矩阵依赖](https://docs.gitlab.com/ci/yaml/matrix_expressions/)
- [ARC runner scale sets](https://docs.github.com/en/actions/tutorials/use-actions-runner-controller/deploy-runner-scale-sets)
- [BuildKit rootless 要求](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Next.js standalone 输出](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

< [上一节：NLB 蓝绿部署](02-infrastructure-advanced.md) | [目录](README.md) | [下一节：ArgoCD 多集群](04-gitops-multi-cluster.md) >
