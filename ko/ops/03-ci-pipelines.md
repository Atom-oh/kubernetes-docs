# EKS 기반 CI 파이프라인: ECR 빌드 및 푸시

> **검토 기준**: GitLab Runner 19.3.1 / chart 0.92.1, ARC 0.14.2, runner 2.337.0, Docker 29.8.0, Trivy 0.74.0, Node 24
> **마지막 검토**: 2026년 9월 11일. Helm·TOML·CI 스키마, 로컬 테스트 대역과 작은 Next.js standalone 앱을 확인했습니다. 실제 CI 작업·레지스트리 push·AWS 배포는 실행하지 않았습니다.

< [이전: NLB 블루/그린](02-infrastructure-advanced.md) | [목차](README.md) | [다음: ArgoCD 멀티클러스터](04-gitops-multi-cluster.md) >

이 예제는 **신뢰하는 보호된 게시 작업을 위한 전용 CI 클러스터**를 전제로 합니다. 아래 Docker-in-Docker는 privileged입니다. 파드가 나뉜다는 것만으로 완전한 보안 경계가 생기지는 않습니다. 공개·비신뢰 PR을 이 러너에 배정하거나 AWS 게시 권한을 상속시키지 않습니다. GitHub 예제는 PR 테스트를 GitHub-hosted runner에서 실행하고 push 작업에서만 OIDC 권한을 받습니다.

애플리케이션에는 npm lockfile, 동작하는 `lint`·`test` 스크립트와 Dockerfile이 있어야 합니다. 실제 앱에 맞춰 명령을 조정합니다. 러너를 EKS에 두어도 GitHub/GitLab API, 레지스트리, 패키지 저장소와 AWS endpoint에 대한 네트워크 의존성은 남습니다.

## ECR 설정

애플리케이션 태그는 불변으로 두고, 계속 갱신하는 BuildKit 캐시는 **별도 mutable 리포지터리**에 둡니다. commit/run/job을 포함한 고유 태그로 충돌을 줄이고 배포에는 승인된 digest를 사용합니다. SHA처럼 생긴 태그 자체가 불변성을 강제하지는 않습니다. 이미 게시한 빌드를 재시도할 때는 검증된 digest를 재사용하거나 새 build ID를 부여하며 릴리스 태그를 덮어쓰지 않습니다.

아래 Terraform은 CI EKS 클러스터와 계정의 GitHub OIDC provider가 이미 있다는 전제입니다. GitLab manager의 S3 캐시 역할과 build Pod의 ECR 게시 역할을 분리합니다. ARC job Pod에는 게시용 Pod Identity 역할을 주지 않고, 신뢰하는 workflow가 자신의 OIDC 역할을 사용합니다.

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

이 root의 backend/state도 보호·분리하고 plan을 검토한 뒤 적용합니다. 캐시 버킷 출력은 GitLab values에, 리포지터리 이름·역할 ARN은 CI 변수에 넣습니다. Pod Identity association은 ServiceAccount를 만들지 않으므로 아래 계정들도 필요합니다.

### 보존·스캐닝·복제

- Lifecycle의 여러 prefix/pattern은 한 이미지의 태그에 대한 **AND 조건**이며 브랜치 OR 목록이 아닙니다. ECR은 EKS에서 사용하는 이미지나 필요한 롤백 버전을 알지 못합니다. 태그 이미지 만료 규칙을 추가하기 전에 정책 preview와 보존 요구를 검토합니다.
- Registry scanning 설정은 계정·리전 전체 설정입니다. Basic ECR scan 이벤트와 Inspector enhanced finding은 스키마가 다릅니다. 겹치는 규칙에서는 continuous가 우선하므로 `*` continuous 규칙 아래의 dev 규칙이 push-only로 남는다고 가정하지 않습니다.
- High와 Critical은 대안적인 severity 값이며 두 필드가 동시에 양수여야 하는 조건이 아닙니다. 스캔 실패·미완료는 깨끗한 이미지가 아닙니다. 아래 Trivy 게이트와 ECR/Inspector 알림도 별개입니다.
- 교차 계정 pull에는 리포지터리 정책과 호출 주체의 ECR 인증 토큰 권한 등이 모두 필요합니다. 계정 전체 위임보다 구체적인 역할을 검토합니다.
- 교차 계정 복제는 대상 registry 권한도 필요합니다. 복제는 비동기이며 기존 이미지와 모든 lifecycle/scanning/repository 설정을 자동으로 복사하지 않습니다.

전체 설정 대안은 검토된 [Amazon ECR 가이드](../container-registry/02-amazon-ecr.md), 승격·보존·서명은 [레지스트리 운영](../container-registry/04-best-practices.md)을 참고합니다. 애플리케이션별 stack이 하나의 registry 전체 설정을 서로 덮어쓰지 않게 소유권을 정합니다.

## GitLab Runner on EKS

### 계정과 보호된 러너 등록

아래 namespace/계정을 준비합니다. GitLab에서 **프로젝트 러너를 두 개** 만들고 보호된 작업만 받도록 설정하며 각각 `eks-ci-amd64`, `eks-ci-arm64` 태그를 부여합니다. 현대적인 authentication-token 방식에서는 태그·보호 여부·untagged 허용을 서버에서 설정하며 옛 registration 플래그나 Helm 값이 이를 바꾼다고 가정하지 않습니다.

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

토큰은 Git과 Terraform values/state 밖에서 관리합니다. 차트는 `gitlab-ci`의 `gitlab-runner-auth-amd64`, `gitlab-runner-auth-arm64` Secret을 참조합니다. `runner-token`과 호환용 빈 `runner-registration-token` 키가 필요합니다. 보호된 파일이나 외부 Secret 관리 방식을 사용하고 실제 토큰을 명령행에 넣지 않습니다.

```bash
# ARM도 별도의 토큰 파일과 Secret 이름으로 반복합니다.
kubectl create secret generic gitlab-runner-auth-amd64 -n gitlab-ci \
  --from-file=runner-token=/protected/gitlab-amd64-token \
  --from-literal=runner-registration-token=''
```

토큰 회전은 실제 Secret 원본과 러너의 reload/restart 동작에 맞춥니다. manager 계정은 Kubernetes API 접근이 필요하지만, build Pod의 일반 Kubernetes API 토큰은 끕니다. Pod Identity는 별도의 AWS용 projected token을 제공합니다.

### 안정 버전 Helm values와 TOML

아래는 AMD64 릴리스입니다. 개발 브랜치의 `bleeding` appVersion 대신 안정 차트를 사용합니다. ARM은 manager/job 아키텍처와 인증 Secret을 바꾸며 사전에 만든 manager ServiceAccount를 공유할 수 있습니다.

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

`node_tolerations`는 TOML map입니다. `poll_interval`은 생성한 Kubernetes Pod 상태를 확인하고, `checkInterval`/`check_interval`은 coordinator 작업 확인 주기에 관계합니다. 같은 설정이 아닙니다. Helper는 Runner 19.3.1과 맞추고 node selector로 아키텍처를 선택하며 `x86_64-latest`로 고정하지 않습니다.

metrics는 manager에 해당하며 모든 build Pod의 9252 포트를 수집하는 것이 아닙니다. ServiceMonitor는 CRD와 수집 구성을 준비할 때까지 끕니다. S3의 `AuthenticationType=iam`은 `RoleARN`이 없을 때 manager 자격 증명 체인을 사용합니다. `RoleARN`을 추가하면 helper 쪽 동작과 필요한 권한이 달라집니다.

```bash
# namespace, 계정, Secret, IAM association, CI 노드를 먼저 준비합니다.
helm upgrade --install gitlab-amd64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-values.yaml
# ARM values는 토큰 Secret과 manager/job의 두 amd64 선택자를 arm64로 변경합니다.
helm upgrade --install gitlab-arm64 gitlab-runner \
  --repo https://charts.gitlab.io --version 0.92.1 \
  --namespace gitlab-ci --values gitlab-arm64-values.yaml
```

### CI 도구 이미지와 파이프라인

기본 Docker 이미지에 파이프라인의 모든 AWS 도구가 들어 있다고 가정하지 않습니다. 아래 이미지를 신뢰하는 bootstrap 환경에서 두 아키텍처로 빌드·스캔·게시하고 `CI_TOOLS_IMAGE`에 승인한 불변 index digest를 넣습니다. Alpine 3.24에는 AMD64·ARM64용 AWS CLI가 있습니다. 나중에 같은 APK 명령을 실행해도 동일한 바이트라고 가정하지 말고 완성된 이미지 digest를 기록합니다.

```dockerfile
# Dockerfile.ci-tools
# Build in a trusted bootstrap environment, scan, and publish with an immutable digest.
FROM docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66
RUN apk add --no-cache bash aws-cli jq
```

GitLab 19.3이 지원하는 matrix 표현식으로 build → scan → publish를 아키텍처별 1:1로 연결합니다. 저장한 동일 이미지를 검사한 뒤 게시합니다. Trivy native JSON은 다운로드할 artifact로 보관하며 GitLab container-scanning 보고서 스키마라고 표시하지 않습니다. 최종 digest 파일 이름도 아키텍처별로 나눠 manifest 작업에서 덮어쓰지 않습니다.

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

DinD에는 privileged 설정과 `/certs/client` 공유 볼륨이 필요하며 준비 대기는 유한하게 제한합니다. 작업 사이에 Docker daemon의 이미지가 남지 않으므로 명시적인 image archive로 전달합니다. 최종 artifact는 승인된 멀티 플랫폼 index를 가리킵니다. 별도 GitOps workflow가 검토 후 배포 manifest를 변경하도록 구성합니다.

## GitHub Self-Hosted Runner

### 현재 runner scale set 방식

공식 OCI scale-set 차트를 사용합니다. `RunnerDeployment`, `RunnerSet`, `HorizontalRunnerAutoscaler`는 다른 레거시 컨트롤러 모델이며 이 차트가 설치하는 리소스가 아닙니다. 현재 scale-set listener가 수요를 처리하므로 scale-from-zero를 위해 무관한 레거시 webhook을 추가하지 않습니다.

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

`arc-runners`에 `arc-github-app` Secret을 승인된 관리 방식으로 생성합니다. 키는 `github_app_id`, `github_app_installation_id`, `github_app_private_key`입니다. 개인키를 Terraform·Helm values에 직접 넣지 않고 보호된 파일을 사용합니다. GitHub App에는 선택한 repository/organization 범위에 필요한 권한과 설치 대상 저장소를 지정합니다.

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

이 custom template은 차트의 Kubernetes ≥1.29 native-sidecar DinD 구성을 따르며 runner 2.337.0과 Docker 29.8.0을 고정합니다. 이 설정과 `containerMode`를 동시에 넣지 않습니다. runner와 DinD가 work/socket/externals를 공유하며 생성된 runner 계정에는 AWS 게시 역할이 없습니다. 기본 runner 이미지에는 Docker/Buildx/jq/git이 있지만 AWS CLI는 없어, 아래 workflow는 Buildx로 최종 digest를 확인합니다.

ARM은 `runnerScaleSetName`을 `eks-ci-arm64`, node architecture를 `arm64`로 바꿉니다. `runs-on`에는 실제 scale-set 이름을 사용합니다. 조직 runner group 이름이 자동으로 작업 label이 되지는 않습니다. ARC 0.14.2에는 추가 label을 위한 `scaleSetLabels`도 있습니다.

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

`minRunners`는 배정 작업에 더해 유지할 idle runner 수이며 용량/max 제한을 받습니다. 0은 유휴 runner Pod를 줄이지만 controller/listener나 모든 클러스터 비용을 없애지 않습니다. 0보다 커도 시작 지연이 전혀 없다고 보장하지 않습니다. 이용 가능한 저장소·workflow를 제한하고 게시용 브랜치·태그를 보호합니다.

### GitHub workflow

Repository variables에 `AWS_PUBLISH_ROLE_ARN`, `ECR_REPOSITORY`, `ECR_CACHE_REPOSITORY`를 설정합니다. IAM trust는 정확한 저장소의 main과 보호된 `v*` 태그를 허용합니다. GitHub Environment를 추가하면 OIDC `sub` 형식도 바뀌므로 trust를 함께 조정합니다. `pull_request_target`에서 비신뢰 코드를 checkout해 이 자격 증명에 접근하게 하지 않습니다.

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

각 네이티브 플랫폼을 스캔한 뒤 digest를 게시하고, manifest 작업은 승인된 불변 참조로 index를 만들며 AMD64·ARM64 포함 여부를 확인합니다. 액션 commit·입력·런타임 정의를 대조했습니다. 여러 줄 metadata-action 태그가 아니라 최종 digest를 배포·서명 입력으로 사용합니다. 플랫폼에서 요구하면 [레지스트리 가이드](../container-registry/04-best-practices.md)의 서명·admission 검증을 연결합니다.

## Multi-Platform Build

아래 Auto Mode pool은 self-managed provider 전용 키 대신 표준 instance-type 조건을 사용하며 기존 default NodeClass를 전제로 합니다. manager와 job 선택자, toleration, helper 아키텍처, 서버에 등록한 runner 태그를 함께 맞춥니다.

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

Spot은 빌드를 중단시킬 수 있으므로 capacity type과 재시도를 요구 사항에 맞춥니다. 네이티브 runner와 QEMU 에뮬레이션은 다른 방식입니다. QEMU는 다른 아키텍처 명령을 실행하며 그 자체가 크로스 컴파일러는 아닙니다. 단일 runner 멀티 플랫폼 빌드에는 지원되는 에뮬레이션 또는 명시적인 크로스 컴파일 구성이 필요하며 platform 플래그만으로 준비되지 않습니다.

## 빌드 최적화

### Next.js standalone 이미지

Node 20은 2026년 4월 지원 종료됐습니다. 아래 npm 예제는 Node 24, lockfile이 있는 단일 Next.js 앱 root를 전제로 합니다. 빌드에는 dev dependencies도 필요하며 최종 traced output에서 실행에 필요한 파일을 선택합니다. standalone을 명시적으로 설정합니다.

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

`.dockerignore`는 다음과 같이 준비합니다.

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

public과 `.next/static`을 복사하고 접근 가능한 bind address 및 비-root `node` 사용자를 설정합니다. Private npm 인증은 BuildKit secret(`--secret id=npmrc,src=/protected/npmrc`)으로 전달하며 `.npmrc`를 복사하거나 build-arg에 비밀을 넣지 않습니다. Monorepo는 tracing root와 중첩된 COPY/server 경로를 따로 맞춰야 하므로 여기의 root `server.js` 경로를 일반화하지 않습니다.

Node 24.21.0으로 Next 16.3.5/React 19.3.0의 작은 앱을 빌드하고 standalone 서버·정적 파일의 HTTP 200을 확인했습니다. 출력 계약 검증이며 전체 앱·컨테이너·실제 CI 배포를 실행한 결과는 아닙니다.

### 캐시 동작

Registry cache는 빌드 layer를 내보냅니다. `RUN --mount=type=cache`의 캐시는 별도로 보존하지 않으면 builder 로컬에 남으며, registry `--cache-to`가 모든 cache mount 디렉터리를 자동 내보내지는 않습니다. mutable 캐시 태그를 불변 release 리포지터리와 분리하고 인증 파일은 캐시하지 않습니다.

Shallow checkout의 `HEAD~1`이나 실패를 숨길 수 있는 bare `wait` 대신 명시적인 변경 규칙·작업 의존성을 사용합니다. Dockerfile에 없는 `tester` stage를 빌드하지 않습니다. 캐시 재사용은 최적화이며 소스·테스트·스캔 성공의 증거가 아닙니다.

### Kaniko와 rootless BuildKit

Google Kaniko 저장소는 보관 상태입니다. Daemonless라는 이유만으로 모든 Dockerfile이 root 없이 실행되거나 빌드가 완전히 격리되는 것은 아닙니다. 신규 구성은 유지되는 builder를 선택하고 실제 권한·커널 지원·인증·게시 경로를 확인합니다.

아래 선택적 발췌는 BuildKit 0.33.0, AWS CLI, jq, Bash가 포함된 이미지와 **별도로 검증한 비-privileged runner**용입니다. 위 privileged DinD 설정의 image만 바꾸는 대체품이 아닙니다. 노드의 user namespace/mount와 클러스터 보안 정책이 해당 rootless 방식을 허용해야 합니다.

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

출력은 OCI archive이며 이를 지원하는 scanner/publisher로 전달합니다. BuildKit은 `--oci-worker-no-process-sandbox`가 daemon 컨테이너 내부의 프로세스 격리를 약화시키고 남은 모든 빌드 프로세스를 정리할 수 없다고 경고합니다. Kubernetes에서 사용하는 절충안이며 보편적인 안전성 보장은 아닙니다. 별도 runner 구성을 먼저 검증합니다.

## 참고 자료

- [GitLab Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/)
- [GitLab Runner 고급 설정](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
- [GitLab matrix 의존성](https://docs.gitlab.com/ci/yaml/matrix_expressions/)
- [ARC runner scale set](https://docs.github.com/en/actions/tutorials/use-actions-runner-controller/deploy-runner-scale-sets)
- [BuildKit rootless 요구 사항](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

< [이전: NLB 블루/그린](02-infrastructure-advanced.md) | [목차](README.md) | [다음: ArgoCD 멀티클러스터](04-gitops-multi-cluster.md) >
