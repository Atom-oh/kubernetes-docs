# EKSベースのCIパイプライン: ECRでのビルドとプッシュ

> **レビュー基準**: GitLab Runner 19.3.1 / chart 0.92.1、ARC 0.15.0、runner 2.337.0、Docker 29.8.0、Trivy 0.76.0、Node 24
> **最終確認**: 2026年10月16日。Helm/TOML/CIスキーマ、ローカルのテスト用代替実装と小規模なNext.js standaloneアプリを確認しました。実際のCIジョブ、レジストリへのプッシュ、AWSへのデプロイは実行していません。

< [前へ: NLB Blue/Green](02-infrastructure-advanced.md) | [目次](README.md) | [次へ: ArgoCDマルチクラスター](04-gitops-multi-cluster.md) >

このガイドでは、信頼できる保護済みの公開ジョブだけを実行する専用CIクラスターを使います。以下のDocker-in-Dockerは特権モードで動作します。Podを分けても完全なセキュリティ境界にはなりません。公開PRや信頼できないPRをこれらのrunnerに流したり、AWS公開用の認証情報を引き継がせたりしないでください。GitHubの例ではPRテストをGitHubホストrunnerで実行し、pushジョブでのみOIDC認証情報を取得します。

アプリケーションは`package-lock.json`を含むnpmプロジェクトで、動作する`lint`/`test`スクリプトとDockerfileを備えるものとします。これらのコマンドはアプリケーションに合わせて調整してください。runnerをEKS上に置いても、GitHub/GitLab API、レジストリ、パッケージリポジトリ、AWSエンドポイントへのネットワーク接続は引き続き必要です。

## 1. ECRリポジトリのセットアップ

アプリケーションのタグは変更不可にし、変更可能なBuildKitキャッシュ参照は**別のリポジトリ**に置いてください。コミット/run/jobごとの一意なタグは衝突を減らします。デプロイには承認済みダイジェストを使ってください。SHA形式に見えるタグだけでは変更不可になりません。公開済みビルドを再試行する場合は、検証済みダイジェストを再利用するか新しいビルド識別子を発行し、リリースタグを上書きしないでください。

Terraformの例は、CI用EKSクラスターとアカウントのGitHub OIDCプロバイダーがすでに存在することを前提とします。GitLab managerのS3キャッシュ用ロールと、ビルドPodのECR公開用ロールを分けています。ARCのjob PodにはPod Identity経由でECR公開権限を付与しません。信頼されたworkflowでは、専用のGitHub OIDC roleを使います。

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

このrootには専用の保護されたbackend/stateを使い、apply前にplanを確認してください。キャッシュバケットの出力をGitLabのvaluesへ、リポジトリ名とロールARNをCI変数へ渡します。EKS Pod Identityの関連付けはServiceAccountを作成しません。以下に示す対応するServiceAccountも必要です。

### 保持、スキャン、レプリケーション

- Lifecycleのprefix/pattern一覧は、ブランチのORリストではなく、イメージタグに対する**AND条件**です。ECRはEKSが現在使っているイメージや必要なロールバック版を把握しません。タグ付きイメージの期限切れルールを追加する前に、ポリシーの適用結果と保持要件を確認してください。
- レジストリスキャン設定はアカウント/リージョン全体に適用されます。ECR BasicスキャンイベントとInspector Enhancedの検出結果ではスキーマが異なります。Continuousスキャンは一致するscan-on-pushルールより優先されます。広い`*`のContinuousルールを設定すると、より限定的なdevルールもpush-onlyスキャンにはなりません。
- HighとCriticalは別々のseverity値であり、両方の値を同時に正にするものではありません。失敗または未完了のスキャンはクリーンなイメージではありません。以下のCI TrivyゲートはECR/Inspectorの通知とは独立しています。
- クロスアカウントのイメージ取得には、リポジトリのresource policyと、ECR authorization tokenへのアクセスを含む呼び出し元の適切なidentity権限の両方が必要です。アカウント内の全principalへの許可ではなく、特定のロールを指定してください。
- クロスアカウントレプリケーションには宛先registryの権限も必要です。レプリケーションは非同期で、既存イメージを自動で遡及コピーすることも、lifecycle/scanning/repository設定をすべて複製することもありません。

完全なレジストリ側の選択肢は[Amazon ECRガイド](../container-registry/02-amazon-ecr.md)、昇格、保持、署名については[レジストリ運用のベストプラクティス](../container-registry/04-best-practices.md)を参照してください。各アプリケーションstackから共有レジストリ設定を上書きさせないでください。

## 2. EKS上のGitLab Runner

### ServiceAccountと保護されたrunner登録

以下に示すnamespaceとServiceAccountを使ってください。GitLab側でproject runnerを2つ作成し、保護設定を有効にして、それぞれに`eks-ci-amd64`または`eks-ci-arm64`のtagを設定します。各runnerの認証tokenを格納するSecretも作成します。現在の認証token方式では、古い登録flagやHelm valuesによって設定が更新されるとは限りません。tag/protection/run-untaggedはGitLab側で設定してください。

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

tokenはGitとTerraformのvalues/stateの外に保存してください。chartは`gitlab-ci`内に既存の`gitlab-runner-auth-amd64`と`gitlab-runner-auth-arm64` Secretがあることを前提とします。Secretには`runner-token`と互換性用のキー`runner-registration-token`（値は空）を指定します。アクセス制御されたファイルまたはexternal-secretワークフローを使い、token値をshellコマンドラインに書かないでください:

```bash
# Repeat for the ARM runner using its own protected token file and Secret name.
kubectl create secret generic gitlab-runner-auth-amd64 -n gitlab-ci \
  --from-file=runner-token=/protected/gitlab-amd64-token \
  --from-literal=runner-registration-token=''
```

tokenのローテーションは、実際のSecret供給元とrunnerのreload/restart動作に合わせてください。managerのServiceAccountにはKubernetes APIアクセスが必要です。ビルドPodでは通常のKubernetes API tokenを無効にし、Pod Identityから別のAWS tokenを供給します。

### 安定したHelm valuesとrunner設定

以下はAMD64用のリリースです。開発ブランチの`bleeding` appVersionではなく、バージョンを固定したchartを使ってください。ARM版ではmanager/jobのarchitectureとtoken Secretが変わります。事前に作成したmanager ServiceAccountは両方のmanagerで利用できます。

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

`node_tolerations`はTOMLのmapです。`poll_interval`は新しく作られたKubernetes Podを確認します。一方、Helmの`checkInterval`/runnerの`check_interval`はcoordinatorへのjob pollingに関係します。同じ意味の設定ではありません。helperのバージョンはRunner 19.3.1に合わせます。architectureは`x86_64-latest`のhelper上書きではなく、明示したnode selectorで選択します。

メトリクスを出力するのはmanagerであり、各ビルドPodではありません。ServiceMonitorは、そのCRDと監視環境が存在するまで無効にします。S3の`AuthenticationType=iam`は`RoleARN`が未設定ならmanagerのcredential chainを使います。`RoleARN`を指定するとcacheの認証情報の扱いが変わり、別途レビュー済みのポリシーが必要です。

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

### CIツールイメージとpipeline

標準のDockerイメージには、pipelineで使うAWSコマンドがすべて含まれるとは限りません。このツールイメージをAMD64とARM64向けに、信頼されたbootstrap環境でビルド、スキャン、公開してください。`CI_TOOLS_IMAGE`には承認済みで変更不可のindex digestを設定します。Alpine 3.24は両architecture向けのAWS CLIを提供します。後日packageを再ビルドしても同じバイト列になるとは限らないため、生成したイメージのdigestを記録してください。

```dockerfile
# Dockerfile.ci-tools
# Build in a trusted bootstrap environment, scan, and publish with an immutable digest.
FROM docker.io/library/docker@sha256:eccaacfeed644c7de222ff047483568cb988dde95476fbaaf10ea2d04921bb66
RUN apk add --no-cache bash aws-cli jq
```

このpipelineではGitLab 19.3がサポートするnative matrix jobを使い、build → scan → publishを1対1でつなぎます。各archiveは、対応するイメージの公開前にスキャンします。Trivyのnative JSONはダウンロード可能なartifactとして扱い、GitLabのcontainer-scanning report schemaであるかのように扱いません。architectureごとの最終digestファイルは別名にし、manifest jobで上書きされないようにします。

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

DinD serviceには、runner設定のprivileged指定と共有`/certs/client` volumeが必要です。readiness待機には上限を設けます。Docker daemonやimageの状態は次のjobに引き継がれないため、image archiveを明示的な受け渡しにします。最終artifactは承認済みmulti-platform indexを示します。承認後のdeployment manifest更新は、別のGitOps workflowで行ってください。

## 3. GitHub Actions Runner Controller

### 現行のrunner scale set

公式OCI scale-set chartを使います。旧`RunnerDeployment`、`RunnerSet`、`HorizontalRunnerAutoscaler`は別のcontroller modelに属し、これらのchartがインストールするresourceではありません。現在のscale setではlistenerが需要を検出するため、scale-from-zeroを有効化する目的で無関係な旧webhook deploymentを追加しないでください。

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

承認済みSecretワークフローで`arc-runners`に`arc-github-app`を作成します。キーは`github_app_id`、`github_app_installation_id`、`github_app_private_key`です。保護されたkey fileを使い、Terraform/Helmへprivate keyを直接書かないでください。選んだrepository/organizationの範囲で必要なpermissionとアクセス権をGitHub Appに付与します。

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

このcustom templateは、chartが採用するKubernetes ≥1.29向けnative-sidecar DinD構成に合わせ、runner 2.337.0とDocker 29.8.0を固定します。独自layoutを指定する場合、`containerMode`は併用しないでください。RunnerとDinDは作業/socket pathとrunner externalsを共有します。生成されるrunner ServiceAccountにはECR公開用roleがありません。標準runner imageにはDocker/Buildx/jq/gitが含まれますが、AWS CLIは含まれません。以下のworkflowではBuildxから最終digestを取得します。

ARMでは`runnerScaleSetName`を`eks-ci-arm64`、nodeのCPU architectureを`arm64`に変更します。`runs-on`には実際のscale-set名を指定してください。organization runner group名が自動的にjob labelになるわけではありません。ARC 0.15.0では必要に応じて`scaleSetLabels`も設定できます。

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

`minRunners`は割り当て済みjob数に加えて確保するidle runner数の下限で、容量や最大数の制限を受けます。0にするとidle runner Podを減らせますが、controller/listenerやクラスターのすべてのコストがなくなるわけではありません。0以外でも起動遅延がなくなる保証はありません。どのrepository/workflowからscale setを使えるかを制限し、公開branch/tagを保護してください。

### GitHub workflow

repository variableとして`AWS_PUBLISH_ROLE_ARN`、`ECR_REPOSITORY`、`ECR_CACHE_REPOSITORY`を設定します。IAM trustはこのrepositoryのmain branchと保護された`v*` tagだけを許可します。GitHub Environmentを追加するとOIDCの`sub`形式が変わるため、必要な場合はtrustを意図的に調整してください。信頼できないcheckoutからこれらの認証情報に届くよう`pull_request_target`を使ってはいけません。

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

各native platformでscanを完了してから、そのdigestを公開します。manifest jobは変更不可の承認済みreferenceを使い、生成されたindexにAMD64とARM64の両方が含まれることを確認します。Action commitとinput/runtime定義は確認済みです。複数行のmetadata-action tag出力ではなく、最終digestをデプロイ/署名の入力にします。必要であれば[レジストリガイド](../container-registry/04-best-practices.md)を参考に署名とadmission検証を追加してください。

## 4. マルチプラットフォームCI向けのネイティブノード

以下のAuto Mode node poolでは、セルフマネージド環境だけで使う独自keyではなく、標準のinstance-type要件を使います。default NodeClassがすでに存在する前提です。managerとjobのselector/toleration、helperのarchitecture、サーバー側runner tagを揃えてください。

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

Spotではbuildが中断される可能性があります。ワークロードに合わせてcapacity typeとretryを選んでください。native runnerとQEMU emulationは異なる方式です。QEMUは別architecture向けの命令を実行しますが、cross compilerではありません。1台のrunnerでmulti-platform buildを行う場合、対応するemulationを使うか、明示的なcross-compilation設計が必要です。platform flagだけではどちらも実現できません。

## 5. ビルドの最適化と現在も保守されている代替手段

### Next.js standalone container

Node 20は2026年4月にEOLを迎えました。このnpmの例ではNode 24を使い、repository rootにNext.js appとlockfileが1つある前提です。buildにはdev dependencyが必要です。本番用に除外する場合は、traced production outputからだけにしてください。standalone outputを明示的に設定します:

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

この`.dockerignore`を使います:

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

Dockerfileではpublic assetと`.next/static`をコピーし、外部から到達できるbind addressを設定して、image内の非root `node` userで実行します。private npm credentialはBuildKit secret（`--secret id=npmrc,src=/protected/npmrc`）で渡せます。`.npmrc`をコピーしたり、build argumentにsecretを含めたりしないでください。monorepoではtracing rootと、対応するnested `COPY`/server pathを明示的に設定する必要があります。ここに示すroot直下の`server.js`構成が常に適切とは限りません。

Node 24.22.0を使ってNext 16.3.5/React 19.3.0のローカル検証用fixtureをbuildし、生成されたstandalone serverとコピーしたstatic fileがHTTP 200を返すことを確認しました。これは出力形式の契約を確認したもので、アプリケーション全体、container、CI deploymentを検証したものではありません。

### Cacheの動作

レジストリキャッシュはbuild layerをexportします。`RUN --mount=type=cache`のcacheは別途永続化しない限りbuilder内だけにあります。registryの`--cache-to`はすべてのcache-mount directoryを自動でexportするわけではありません。変更可能なcache tagは変更不可のrelease repositoryと分け、registry credentialをcacheに含めないでください。

浅い`HEAD~1`判定や、バックグラウンドcommandの後に失敗を隠す可能性のある`wait`だけの呼び出しは避け、宣言的なchange ruleとdependency graphを使ってください。存在しないDockerfileの`tester` stageを参照しないでください。cache再利用は最適化であり、source/test/scanが成功した証拠ではありません。

### Kanikoとrootless BuildKit

GoogleのKaniko repositoryはアーカイブされています。daemonlessであっても、すべてのDockerfileをrootなしでbuildできることや、buildが完全に分離されることを意味しません。新しい構成では現在も保守されているbuilderを使い、実際に必要な権限、kernel support、credential、image公開経路を確認してください。

この任意のBuildKit設定例は、BuildKit 0.33.0、AWS CLI、jq、Bashを含むCI imageを使う**別途検証済みの非privileged runner**向けです。上記のprivileged DinD設定にそのまま適用できるものではありません。選択したrootless modeが、user namespace/mount supportとクラスターのsecurity policyで許可されることを確認してください。

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

出力は対応するscanner/publisherに渡すOCI archiveです。Upstream BuildKitは、`--oci-worker-no-process-sandbox`によってdaemon container内のprocess分離が弱まり、残留build processをすべてcleanupできない場合があると警告しています。Kubernetesで使う場合は安全性とのトレードオフがあり、常に安全とは限りません。この選択肢を採用する前に、専用runner設定を検証してください。

## 参考資料

- [GitLab Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/)
- [GitLab Runnerの詳細設定](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
- [GitLab matrixの依存関係](https://docs.gitlab.com/ci/yaml/matrix_expressions/)
- [ARCでのrunner scale set](https://docs.github.com/en/actions/tutorials/use-actions-runner-controller/deploy-runner-scale-sets)
- [BuildKitのrootless要件](https://github.com/moby/buildkit/blob/v0.33.0/docs/rootless.md)
- [Next.js standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output)

< [前へ: NLB Blue/Green](02-infrastructure-advanced.md) | [目次](README.md) | [次へ: ArgoCDマルチクラスター](04-gitops-multi-cluster.md) >
