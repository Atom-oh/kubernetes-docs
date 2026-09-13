# EKS-Based CI Pipelines: ECR Build and Push

> **Review baseline**: GitLab Runner 19.3.1 / chart 0.92.1, ARC 0.14.2, runner 2.337.0, Docker 29.8.0, Trivy 0.74.0, Node 24
> **Last reviewed**: September 11, 2026. Helm/TOML/CI schemas, local test doubles, and a small Next.js standalone application were checked. No real CI job, registry push, or AWS deployment was run.

< [Previous: NLB Blue/Green](02-infrastructure-advanced.md) | [Table of Contents](README.md) | [Next: ArgoCD Multi-Cluster](04-gitops-multi-cluster.md) >

This guide uses a **dedicated CI cluster for trusted, protected publish jobs**. Docker-in-Docker below is privileged. A separate Pod is not a complete security boundary; do not route public or untrusted pull requests to these runners or give them inherited AWS publishing credentials. The GitHub example runs PR tests on GitHub-hosted runners and acquires OIDC credentials only in push jobs.

The application contract is an npm project with `package-lock.json`, working `lint`/`test` scripts, and a Dockerfile. Adapt those commands to the application. GitHub/GitLab APIs, registries, package repositories, and AWS endpoints remain network dependencies even when runners run on EKS.

## 1. ECR Repository Setup

Keep application tags immutable and put mutable BuildKit cache references in a **different repository**. Unique commit/run/job tags reduce collisions; deploy by the approved digest. A SHA-shaped tag alone is not an immutability control. For retries of an already published build, reuse its verified digest or create a new build identifier instead of overwriting a release tag.

The Terraform example assumes the CI EKS cluster and the account's GitHub OIDC provider already exist. It separates the GitLab manager's S3 cache role from the build Pod's ECR publishing role. ARC job Pods have no Pod Identity publishing role: the trusted workflow uses its own GitHub OIDC role.

```hcl
# main.tf
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "6.64.0" }
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

Use a distinct protected backend/state for this root and review the plan before applying. Put the cache bucket output into the GitLab values, and repository names/role ARN into the CI variables. EKS Pod Identity associations do not create ServiceAccounts; the matching accounts below are also required.

### Retention, scanning, and replication

- Lifecycle prefix/pattern lists are **AND conditions on an image's tags**, not an OR list of branches. ECR does not know which images EKS is running or which rollback versions you need. Preview policies and retention requirements before adding tagged-image expiration rules.
- Registry scanning configuration is account/Region-wide. Basic ECR scan events and Inspector enhanced findings have different schemas. Continuous scanning takes precedence over a matching scan-on-push rule; a broad `*` continuous rule does not leave a narrower dev rule on push-only scanning.
- High and Critical are alternative severity values, not two fields that must both be positive. A failed or incomplete scan is not a clean image. The CI Trivy gate below is independent of ECR/Inspector notifications.
- Cross-account image pulls require both the repository resource policy and appropriate caller identity permissions, including ECR authorization-token access. Prefer specific roles over granting every principal in an account.
- Cross-account replication also needs the destination registry permissions. Replication is asynchronous and does not automatically backfill existing images or copy every lifecycle/scanning/repository setting.

Use the reviewed [Amazon ECR guide](../container-registry/02-amazon-ecr.md) for the complete registry-level alternatives and [registry practices](../container-registry/04-best-practices.md) for promotion, retention, and signing. Do not let every application stack overwrite one shared registry configuration.

## 2. GitLab Runner on EKS

### Service accounts and protected runner registration

Use the namespace/accounts below. Create **two server-side project runners**, with protected access and the tags `eks-ci-amd64` and `eks-ci-arm64`, then create their authentication-token Secrets. With the modern authentication-token workflow, configure tags/protection/run-untagged on GitLab, not by assuming old registration flags or Helm values will update them.

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

Store tokens outside Git and Terraform values/state. The chart uses existing Secrets named `gitlab-runner-auth-amd64` and `gitlab-runner-auth-arm64` in `gitlab-ci`. It expects `runner-token` and the compatibility key `runner-registration-token` (empty). Use protected files or an external-secret workflow; do not put token values on a shell command line:

```bash
# Repeat for the ARM runner using its own protected token file and Secret name.
kubectl create secret generic gitlab-runner-auth-amd64 -n gitlab-ci \
  --from-file=runner-token=/protected/gitlab-amd64-token \
  --from-literal=runner-registration-token=''
```

Coordinate token rotation with the actual secret source and runner reload/restart behavior. The manager ServiceAccount needs Kubernetes API access; build Pods disable the normal Kubernetes API token while Pod Identity supplies its separate AWS token.

### Stable Helm values and runner configuration

The following is the AMD64 release. Use the versioned chart, not a development branch's `bleeding` appVersion. The ARM variant changes the manager/job architecture and token Secret; both managers can use the pre-created manager ServiceAccount.

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

`node_tolerations` is a TOML map. `poll_interval` checks newly created Kubernetes Pods; Helm `checkInterval`/runner `check_interval` concerns coordinator job polling. They are not synonyms. The helper version follows Runner 19.3.1; architecture is selected from the explicit node selector rather than an `x86_64-latest` helper override.

Metrics belong to the manager, not every build Pod. ServiceMonitor is disabled until its CRD and monitoring setup exist. S3 `AuthenticationType=iam` uses the manager credential chain when `RoleARN` is unset; setting `RoleARN` changes cache credential behavior and requires a separate reviewed policy.

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

### CI tool image and pipeline

The stock Docker image does not provide every AWS command used by the pipeline. Build, scan, and publish this tool image in a trusted bootstrap environment for both architectures. Set `CI_TOOLS_IMAGE` to its approved immutable index digest. Alpine 3.24 supplies AWS CLI for AMD64 and ARM64; record the resulting image digest rather than assuming later package rebuilds are byte-identical.

```dockerfile
# Dockerfile.ci-tools
# Build in a trusted bootstrap environment, scan, and publish with an immutable digest.
FROM docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66
RUN apk add --no-cache bash aws-cli jq
```

The pipeline uses native matrix jobs with 1:1 build → scan → publish dependencies, supported by GitLab 19.3. Each archive is scanned before publishing that same image. Trivy's native JSON is a downloadable artifact, not mislabeled as GitLab's container-scanning report schema. Final per-architecture digest files have different names, avoiding artifact overwrites in the manifest job.

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
    name: docker.io/aquasec/trivy@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969
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

The DinD service requires the privileged setting and shared `/certs/client` volume in the runner configuration. Readiness waits are bounded. The Docker daemon/image state does not survive into another job: the image archive is the explicit handoff. The final artifact identifies the approved multi-platform index; a separate GitOps workflow should update deployment manifests after approval.

## 3. GitHub Actions Runner Controller

### Current runner scale sets

Use the official OCI scale-set charts. Legacy `RunnerDeployment`, `RunnerSet`, and `HorizontalRunnerAutoscaler` belong to a different controller model and are not resources installed by these charts. The current scale-set listener drives demand; do not add an unrelated legacy webhook deployment to enable scale-from-zero.

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

Create `arc-github-app` in `arc-runners` through the approved secret workflow. Its keys are `github_app_id`, `github_app_installation_id`, and `github_app_private_key`. Use a protected key file, not an inline Terraform/Helm private-key value. Install the GitHub App with permissions and repository access required by the chosen repository/organization scope.

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
# ARC 0.14.2, Kubernetes >=1.29. Dedicated CI cluster, trusted publish jobs only.
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

This custom template follows the chart's Kubernetes ≥1.29 native-sidecar DinD layout and pins runner 2.337.0 and Docker 29.8.0. Do not also set `containerMode` when supplying the custom layout. Runner and DinD share work/socket paths and runner externals. The generated runner ServiceAccount has no publishing role. The stock runner image includes Docker/Buildx/jq/git, but not AWS CLI; the workflow below obtains the final digest through Buildx instead.

For ARM, change `runnerScaleSetName` to `eks-ci-arm64` and the node architecture to `arm64`. Use those actual scale-set names in `runs-on`; an organization runner-group name is not automatically the job label. ARC 0.14.2 also exposes `scaleSetLabels` when additional labels are needed.

```bash
helm upgrade --install arc \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
  --version 0.14.2 --namespace arc-systems --values arc-controller-values.yaml
helm upgrade --install eks-ci-amd64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.14.2 --namespace arc-runners --values arc-runner-values.yaml
helm upgrade --install eks-ci-arm64 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
  --version 0.14.2 --namespace arc-runners --values arc-runner-arm64-values.yaml
```

`minRunners` is the idle-runner floor added to assigned work, subject to capacity/max limits. Zero reduces idle runner Pods but does not remove the controller/listener or all cluster costs. Nonzero does not guarantee no startup delay. Restrict which repositories/workflows may use the runner scale sets and protect publishing branches/tags.

### GitHub workflow

Set repository variables `AWS_PUBLISH_ROLE_ARN`, `ECR_REPOSITORY`, and `ECR_CACHE_REPOSITORY`. The IAM trust allows this exact repository's main branch and protected `v*` tags. A GitHub Environment changes the OIDC `sub` shape; adjust trust deliberately if you add one. Never use `pull_request_target` with an untrusted checkout to reach these credentials.

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
          version: v0.74.0
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

Every native platform is scanned before its digest is published. The manifest job consumes immutable approved references and verifies the resulting index includes AMD64 and ARM64. Action commits and input/runtime definitions were checked. The final digest, not a multiline metadata-action tag output, is the deployment/signing input. Add signature and admission verification using the [registry guide](../container-registry/04-best-practices.md) if required by the platform.

## 4. Native Multi-Platform CI Nodes

The following Auto Mode pools use standard instance-type requirements rather than self-managed-provider-specific keys. They assume an existing default NodeClass. Match both manager/job selectors, tolerations, helper architecture, and server-side runner tags.

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

Spot can interrupt builds; choose capacity types and retries from workload requirements. Native runners and QEMU emulation are different approaches. QEMU executes foreign-architecture instructions; it is not itself a cross compiler. Single-runner multi-platform builds need supported emulation or an explicit cross-compilation design. A platform flag alone does not provide either.

## 5. Build Optimization and Maintained Alternatives

### Next.js standalone container

Node 20 reached EOL in April 2026. This npm-based example uses Node 24 and assumes a single Next.js app root with a lockfile. Building needs dev dependencies; omit them only from the traced production output. Configure standalone output explicitly:

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

Use this `.dockerignore`:

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

The Dockerfile copies public assets and `.next/static`, sets a reachable bind address, and runs as the image's non-root `node` user. Private npm credentials can be supplied through a BuildKit secret (`--secret id=npmrc,src=/protected/npmrc`); do not copy `.npmrc` or put secrets in build arguments. A monorepo needs deliberate tracing roots and matching nested `COPY`/server paths; the root-level `server.js` layout here is not universal.

A local Next 16.3.5/React 19.3.0 fixture was built with Node 24.21.0, and the emitted standalone server and copied static file returned HTTP 200. This checks the output contract, not a full application/container/CI deployment.

### Cache behavior

Registry cache exports build layers. A `RUN --mount=type=cache` cache is local to the builder unless separately persisted; registry `--cache-to` does not automatically export every cache-mount directory. Keep mutable cache tags out of the immutable release repository and never cache registry credentials.

Use declared change rules and dependency graphs instead of a shallow `HEAD~1` test or background commands followed by a bare `wait` that can hide failures. Do not reference a `tester` Dockerfile stage that does not exist. Cache reuse is an optimization, not proof that source/test/scan work succeeded.

### Kaniko and rootless BuildKit

The Google Kaniko repository is archived. Daemonless does not imply that every Dockerfile runs without root or that builds are completely isolated. Use a currently maintained builder for new work and verify its actual privileges, kernel support, credentials, and image-publishing path.

This optional BuildKit fragment belongs on a **different, validated non-privileged runner** with a CI image containing BuildKit 0.33.0, AWS CLI, jq, and Bash. It is not a drop-in change to the privileged DinD configuration above. User-namespace/mount support and the cluster's security policy must allow the chosen rootless mode.

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

The output is an OCI archive to pass to a matching scanner/publisher. Upstream BuildKit warns that `--oci-worker-no-process-sandbox` weakens process isolation within the daemon container and cannot clean up every lingering build process. Its Kubernetes use is a trade-off, not a universal safety guarantee. Validate the dedicated runner configuration before adopting this alternative.

## References

- [GitLab Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/)
- [GitLab Runner advanced configuration](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
- [GitLab matrix dependencies](https://docs.gitlab.com/ci/yaml/matrix_expressions/)
- [ARC runner scale sets](https://docs.github.com/en/actions/tutorials/use-actions-runner-controller/deploy-runner-scale-sets)
- [BuildKit rootless requirements](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

< [Previous: NLB Blue/Green](02-infrastructure-advanced.md) | [Table of Contents](README.md) | [Next: ArgoCD Multi-Cluster](04-gitops-multi-cluster.md) >
