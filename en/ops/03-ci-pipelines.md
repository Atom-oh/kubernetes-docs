# EKS-Based CI Pipelines: ECR Build and Push

> **Supported Versions**: Amazon EKS 1.28+, GitLab Runner 16.x+, Actions Runner Controller 0.9+
> **Last Updated**: February 23, 2026

< [Previous: NLB Blue/Green](./02-infrastructure-advanced.md) | [Table of Contents](./README.md) | [Next: ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) >

---

## Overview

Building container images within EKS clusters eliminates external CI infrastructure dependencies and provides tighter integration with AWS services. This guide covers setting up CI pipelines using GitLab Runner and GitHub Actions Runner Controller, with multi-platform build strategies for both ARM (Graviton) and x86 architectures.

**Key Benefits:**
- Native ECR integration with Pod Identity
- Auto-scaling runners based on workload
- Multi-architecture builds on native hardware
- Cost optimization with Spot instances

---

## 1. ECR Repository Setup

### 1.1 Terraform ECR Module

Create a reusable ECR repository module with lifecycle policies, scanning, and cross-account access.

```hcl
# modules/ecr/main.tf

variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "image_tag_mutability" {
  description = "Tag mutability setting"
  type        = string
  default     = "IMMUTABLE"
}

variable "scan_on_push" {
  description = "Enable image scanning on push"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "Encryption type (AES256 or KMS)"
  type        = string
  default     = "AES256"
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption (required if encryption_type is KMS)"
  type        = string
  default     = null
}

variable "cross_account_ids" {
  description = "List of AWS account IDs for cross-account access"
  type        = list(string)
  default     = []
}

variable "lifecycle_policy_count" {
  description = "Number of images to retain"
  type        = number
  default     = 30
}

resource "aws_ecr_repository" "this" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = var.encryption_type
    kms_key         = var.kms_key_arn
  }

  tags = {
    Name        = var.repository_name
    ManagedBy   = "terraform"
    Environment = terraform.workspace
  }
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.lifecycle_policy_count} images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "release"]
          countType     = "imageCountMoreThan"
          countNumber   = var.lifecycle_policy_count
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "Remove dev/feature images older than 14 days"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev-", "feature-", "pr-"]
          countType     = "sinceImagePushed"
          countUnit     = "days"
          countNumber   = 14
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Cross-account access policy
resource "aws_ecr_repository_policy" "cross_account" {
  count      = length(var.cross_account_ids) > 0 ? 1 : 0
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CrossAccountPull"
        Effect = "Allow"
        Principal = {
          AWS = [for id in var.cross_account_ids : "arn:aws:iam::${id}:root"]
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      }
    ]
  })
}

output "repository_url" {
  value = aws_ecr_repository.this.repository_url
}

output "repository_arn" {
  value = aws_ecr_repository.this.arn
}
```

### 1.2 ECR Replication Configuration

Enable cross-region replication for disaster recovery:

```hcl
# ecr-replication.tf

resource "aws_ecr_replication_configuration" "this" {
  replication_configuration {
    rule {
      destination {
        region      = "us-west-2"
        registry_id = data.aws_caller_identity.current.account_id
      }

      repository_filter {
        filter      = "prod-"
        filter_type = "PREFIX_MATCH"
      }
    }

    rule {
      destination {
        region      = "eu-west-1"
        registry_id = data.aws_caller_identity.current.account_id
      }

      repository_filter {
        filter      = "prod-"
        filter_type = "PREFIX_MATCH"
      }
    }
  }
}
```

### 1.3 Enhanced Scanning Configuration

Configure ECR enhanced scanning with Inspector:

```hcl
# ecr-scanning.tf

resource "aws_ecr_registry_scanning_configuration" "this" {
  scan_type = "ENHANCED"

  rule {
    scan_frequency = "CONTINUOUS_SCAN"
    repository_filter {
      filter      = "*"
      filter_type = "WILDCARD"
    }
  }

  rule {
    scan_frequency = "SCAN_ON_PUSH"
    repository_filter {
      filter      = "dev-*"
      filter_type = "WILDCARD"
    }
  }
}
```

---

## 2. GitLab Runner on EKS

### 2.1 GitLab Runner Helm Values

Deploy GitLab Runner with Kubernetes executor for dynamic pod-based builds:

```yaml
# gitlab-runner/values.yaml

gitlabUrl: https://gitlab.example.com/
runnerRegistrationToken: ""  # Use runnerToken instead (deprecated)

# Use authentication token (GitLab 16.0+)
runnerToken: ""  # Set via --set or external secret

concurrent: 10
checkInterval: 3

rbac:
  create: true
  rules:
    - apiGroups: [""]
      resources: ["pods", "pods/exec", "secrets", "configmaps"]
      verbs: ["get", "list", "watch", "create", "patch", "delete"]
    - apiGroups: [""]
      resources: ["pods/log"]
      verbs: ["get"]

serviceAccount:
  create: true
  name: gitlab-runner
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/GitLabRunnerRole

runners:
  config: |
    [[runners]]
      name = "eks-runner"
      executor = "kubernetes"
      [runners.kubernetes]
        namespace = "gitlab-runner"
        image = "alpine:latest"
        privileged = false

        # Pod resources
        cpu_limit = "2"
        cpu_request = "500m"
        memory_limit = "4Gi"
        memory_request = "1Gi"

        # Service account for builds
        service_account = "gitlab-runner-build"

        # Node selection
        [runners.kubernetes.node_selector]
          "kubernetes.io/os" = "linux"
          "node.kubernetes.io/instance-type" = "m6i.xlarge"

        # Tolerations for dedicated CI nodes
        [[runners.kubernetes.node_tolerations]]
          key = "ci-workload"
          operator = "Equal"
          value = "true"
          effect = "NoSchedule"

        # Pod labels
        [runners.kubernetes.pod_labels]
          "app.kubernetes.io/component" = "ci-build"

        # Pod annotations for monitoring
        [runners.kubernetes.pod_annotations]
          "prometheus.io/scrape" = "true"

        # Helper image configuration
        helper_image = "gitlab/gitlab-runner-helper:x86_64-latest"

        # Build container security context
        [runners.kubernetes.build_container_security_context]
          run_as_user = 1000
          run_as_group = 1000
          run_as_non_root = true

        # Volume mounts for caching
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-cache"
          mount_path = "/var/lib/docker"
          medium = "Memory"

        [[runners.kubernetes.volumes.empty_dir]]
          name = "build-cache"
          mount_path = "/cache"

      [runners.cache]
        Type = "s3"
        Shared = true
        [runners.cache.s3]
          ServerAddress = "s3.amazonaws.com"
          BucketName = "gitlab-runner-cache-123456789012"
          BucketLocation = "us-east-1"

  # Tags for job matching
  tags: "eks,docker,linux"
  runUntagged: false
  protected: false

# Resource limits for runner manager pod
resources:
  limits:
    memory: 256Mi
    cpu: 200m
  requests:
    memory: 128Mi
    cpu: 100m

# Pod security context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 100
  fsGroup: 65533

# Affinity for runner manager
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: node.kubernetes.io/instance-type
              operator: In
              values:
                - t3.medium
                - t3.large

# Metrics for monitoring
metrics:
  enabled: true
  portName: metrics
  port: 9252
  serviceMonitor:
    enabled: true
```

### 2.2 IAM Role for GitLab Runner (Pod Identity)

```hcl
# gitlab-runner-iam.tf

# IAM Role for GitLab Runner
resource "aws_iam_role" "gitlab_runner" {
  name = "GitLabRunnerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

# ECR push policy
resource "aws_iam_role_policy" "gitlab_runner_ecr" {
  name = "ecr-push-policy"
  role = aws_iam_role.gitlab_runner.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:ListImages"
        ]
        Resource = "arn:aws:ecr:*:${data.aws_caller_identity.current.account_id}:repository/*"
      }
    ]
  })
}

# S3 cache policy
resource "aws_iam_role_policy" "gitlab_runner_cache" {
  name = "s3-cache-policy"
  role = aws_iam_role.gitlab_runner.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::gitlab-runner-cache-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::gitlab-runner-cache-${data.aws_caller_identity.current.account_id}/*"
        ]
      }
    ]
  })
}

# Pod Identity Association
resource "aws_eks_pod_identity_association" "gitlab_runner" {
  cluster_name    = var.cluster_name
  namespace       = "gitlab-runner"
  service_account = "gitlab-runner"
  role_arn        = aws_iam_role.gitlab_runner.arn
}

# Also create association for build service account
resource "aws_eks_pod_identity_association" "gitlab_runner_build" {
  cluster_name    = var.cluster_name
  namespace       = "gitlab-runner"
  service_account = "gitlab-runner-build"
  role_arn        = aws_iam_role.gitlab_runner.arn
}
```

### 2.3 Complete GitLab CI Pipeline

```yaml
# .gitlab-ci.yml

stages:
  - build
  - test
  - security
  - push
  - deploy

variables:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
  IMAGE_NAME: myapp
  DOCKER_BUILDKIT: "1"

.docker-login: &docker-login
  - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

.build-base:
  tags:
    - eks
    - docker
  before_script:
    - *docker-login

# Build stage
build:
  extends: .build-base
  stage: build
  image: docker:24-dind
  services:
    - docker:24-dind
  script:
    - docker build
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:cache
        --build-arg BUILDKIT_INLINE_CACHE=1
        -t ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
        -t ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_REF_SLUG}
        .
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_REF_SLUG}
  cache:
    key: docker-${CI_COMMIT_REF_SLUG}
    paths:
      - /cache
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# Unit tests
test:unit:
  stage: test
  image: ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
  tags:
    - eks
  script:
    - npm test
  coverage: '/Lines\s*:\s*(\d+\.?\d*)%/'
  artifacts:
    reports:
      junit: test-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
  needs:
    - build

# Integration tests
test:integration:
  stage: test
  image: ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
  tags:
    - eks
  services:
    - name: postgres:15
      alias: db
    - name: redis:7
      alias: cache
  variables:
    DATABASE_URL: postgres://postgres:postgres@db:5432/test
    REDIS_URL: redis://cache:6379
  script:
    - npm run test:integration
  needs:
    - build
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual

# Security scanning
security:trivy:
  stage: security
  image: aquasec/trivy:latest
  tags:
    - eks
  before_script:
    - *docker-login
  script:
    - trivy image
        --exit-code 1
        --severity HIGH,CRITICAL
        --ignore-unfixed
        --format json
        --output trivy-report.json
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
  artifacts:
    reports:
      container_scanning: trivy-report.json
  allow_failure: true
  needs:
    - build

# Push to production registry
push:production:
  extends: .build-base
  stage: push
  image: docker:24
  script:
    - docker pull ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
    - docker tag ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} ${ECR_REGISTRY}/${IMAGE_NAME}:latest
    - docker tag ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG}
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG}
  needs:
    - test:unit
    - security:trivy
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/

# Deploy to staging
deploy:staging:
  stage: deploy
  image: bitnami/kubectl:latest
  tags:
    - eks
  script:
    - kubectl set image deployment/myapp myapp=${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} -n staging
    - kubectl rollout status deployment/myapp -n staging --timeout=300s
  environment:
    name: staging
    url: https://staging.example.com
  needs:
    - test:unit
    - test:integration
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### 2.4 Runner Token Management with External Secrets

```yaml
# gitlab-runner-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: gitlab-runner-token
  namespace: gitlab-runner
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: gitlab-runner-secret
    creationPolicy: Owner
  data:
    - secretKey: runner-token
      remoteRef:
        key: gitlab/runner-token
        property: token
```

---

## 3. GitHub Self-Hosted Runner (Actions Runner Controller)

### 3.1 ARC Installation with Helm

```bash
# Add the ARC Helm repository
helm repo add actions-runner-controller https://actions-runner-controller.github.io/actions-runner-controller
helm repo update

# Create namespace
kubectl create namespace actions-runner-system
```

```yaml
# arc-values.yaml

replicaCount: 1

image:
  repository: ghcr.io/actions/actions-runner-controller
  tag: "0.9.3"

serviceAccount:
  create: true
  name: actions-runner-controller
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ActionsRunnerControllerRole

# Authentication via GitHub App (recommended)
authSecret:
  enabled: true
  create: false
  name: controller-manager

# GitHub App configuration
githubAPP:
  enabled: true

# Controller resources
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

# Metrics
metrics:
  serviceMonitor:
    enabled: true

# Pod security
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

# Webhook configuration for scale-from-zero
githubWebhookServer:
  enabled: true
  replicaCount: 1
  service:
    type: ClusterIP
  ingress:
    enabled: true
    ingressClassName: alb
    annotations:
      alb.ingress.kubernetes.io/scheme: internet-facing
      alb.ingress.kubernetes.io/target-type: ip
      alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/xxx
    hosts:
      - host: arc-webhook.example.com
        paths:
          - path: /
            pathType: Prefix
```

Install ARC:

```bash
helm install arc actions-runner-controller/actions-runner-controller \
  -n actions-runner-system \
  -f arc-values.yaml
```

### 3.2 GitHub App Secret

```yaml
# github-app-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: controller-manager
  namespace: actions-runner-system
type: Opaque
stringData:
  github_app_id: "123456"
  github_app_installation_id: "12345678"
  github_app_private_key: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### 3.3 RunnerDeployment Configuration

```yaml
# runner-deployment.yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: eks-runners
  namespace: actions-runner-system
spec:
  replicas: 2
  template:
    spec:
      organization: my-org
      # Or use repository for repo-level runners:
      # repository: my-org/my-repo

      labels:
        - eks
        - linux
        - x64

      group: production

      image: summerwind/actions-runner:latest

      serviceAccountName: actions-runner

      resources:
        limits:
          cpu: "2"
          memory: 4Gi
        requests:
          cpu: "500m"
          memory: 1Gi

      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64

      tolerations:
        - key: ci-workload
          operator: Equal
          value: "true"
          effect: NoSchedule

      # Docker-in-Docker mode
      dockerdWithinRunnerContainer: true

      # Volume mounts
      volumeMounts:
        - name: work
          mountPath: /runner/_work

      volumes:
        - name: work
          emptyDir: {}

      env:
        - name: DOCKER_BUILDKIT
          value: "1"
        - name: AWS_REGION
          value: us-east-1
```

### 3.4 RunnerSet for Stateful Runners

```yaml
# runner-set.yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerSet
metadata:
  name: eks-runner-set
  namespace: actions-runner-system
spec:
  organization: my-org

  replicas: 3

  selector:
    matchLabels:
      app: runner

  serviceName: runner

  template:
    metadata:
      labels:
        app: runner
    spec:
      serviceAccountName: actions-runner

      containers:
        - name: runner
          image: summerwind/actions-runner:latest
          resources:
            limits:
              cpu: "4"
              memory: 8Gi
            requests:
              cpu: "1"
              memory: 2Gi

          volumeMounts:
            - name: runner-work
              mountPath: /runner/_work
            - name: docker-cache
              mountPath: /var/lib/docker

      nodeSelector:
        node.kubernetes.io/instance-type: m6i.2xlarge

  volumeClaimTemplates:
    - metadata:
        name: runner-work
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 100Gi
    - metadata:
        name: docker-cache
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 50Gi
```

### 3.5 HorizontalRunnerAutoscaler (Scale from Zero)

```yaml
# horizontal-runner-autoscaler.yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: HorizontalRunnerAutoscaler
metadata:
  name: eks-runners-autoscaler
  namespace: actions-runner-system
spec:
  scaleTargetRef:
    kind: RunnerDeployment
    name: eks-runners

  minReplicas: 0
  maxReplicas: 20

  scaleDownDelaySecondsAfterScaleOut: 300

  metrics:
    - type: TotalNumberOfQueuedAndInProgressWorkflowRuns
      repositoryNames:
        - my-org/repo1
        - my-org/repo2

  # Scale up triggers
  scaleUpTriggers:
    - githubEvent:
        workflowJob: {}
      amount: 1
      duration: "5m"
```

### 3.6 Complete GitHub Actions Workflow

```yaml
# .github/workflows/build-push.yaml

name: Build and Push to ECR

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: myapp

permissions:
  id-token: write
  contents: read
  packages: write

jobs:
  build:
    runs-on: [self-hosted, eks, linux, x64]

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha,prefix=

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:cache
          cache-to: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:cache,mode=max
          provenance: false

  test:
    runs-on: [self-hosted, eks, linux, x64]
    needs: build
    if: github.event_name == 'pull_request'

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run tests
        run: |
          npm ci
          npm test

  security-scan:
    runs-on: [self-hosted, eks, linux, x64]
    needs: build
    if: github.event_name != 'pull_request'

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build.outputs.image-tag }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'HIGH,CRITICAL'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  deploy:
    runs-on: [self-hosted, eks, linux, x64]
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - name: Deploy to EKS
        run: |
          kubectl set image deployment/myapp \
            myapp=${{ needs.build.outputs.image-tag }} \
            -n production
          kubectl rollout status deployment/myapp -n production
```

### 3.7 IAM Role for GitHub Actions Runner

```hcl
# github-actions-runner-iam.tf

resource "aws_iam_role" "github_actions_runner" {
  name = "GitHubActionsRunnerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_actions_ecr" {
  role       = aws_iam_role.github_actions_runner.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

resource "aws_eks_pod_identity_association" "github_actions_runner" {
  cluster_name    = var.cluster_name
  namespace       = "actions-runner-system"
  service_account = "actions-runner"
  role_arn        = aws_iam_role.github_actions_runner.arn
}
```

---

## 4. Multi-Platform Build (ARM + x86)

### 4.1 ARM Runner Configuration (Graviton)

```yaml
# arm-runner-deployment.yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: eks-arm-runners
  namespace: actions-runner-system
spec:
  replicas: 2
  template:
    spec:
      organization: my-org

      labels:
        - eks
        - linux
        - arm64
        - graviton

      image: summerwind/actions-runner:latest

      serviceAccountName: actions-runner

      resources:
        limits:
          cpu: "4"
          memory: 8Gi
        requests:
          cpu: "1"
          memory: 2Gi

      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
        node.kubernetes.io/instance-type: m7g.xlarge

      tolerations:
        - key: arch
          operator: Equal
          value: arm64
          effect: NoSchedule

      dockerdWithinRunnerContainer: true
```

### 4.2 x86 Runner Configuration

```yaml
# x86-runner-deployment.yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: eks-x86-runners
  namespace: actions-runner-system
spec:
  replicas: 2
  template:
    spec:
      organization: my-org

      labels:
        - eks
        - linux
        - amd64
        - x64

      image: summerwind/actions-runner:latest

      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
        node.kubernetes.io/instance-type: m6i.xlarge

      dockerdWithinRunnerContainer: true
```

### 4.3 GitHub Actions Multi-Platform Workflow

```yaml
# .github/workflows/multi-arch-build.yaml

name: Multi-Architecture Build

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: myapp

permissions:
  id-token: write
  contents: read

jobs:
  build-amd64:
    runs-on: [self-hosted, eks, linux, amd64]
    outputs:
      digest: ${{ steps.build.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push AMD64
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}-amd64
          platforms: linux/amd64
          provenance: false

  build-arm64:
    runs-on: [self-hosted, eks, linux, arm64]
    outputs:
      digest: ${{ steps.build.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push ARM64
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY }}:${{ github.sha }}-arm64
          platforms: linux/arm64
          provenance: false

  create-manifest:
    runs-on: [self-hosted, eks, linux, amd64]
    needs: [build-amd64, build-arm64]

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Create and push manifest
        env:
          REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          # Create manifest list
          docker manifest create ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA} \
            ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-amd64 \
            ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-arm64

          # Annotate with architecture info
          docker manifest annotate ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA} \
            ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-amd64 \
            --os linux --arch amd64

          docker manifest annotate ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA} \
            ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-arm64 \
            --os linux --arch arm64

          # Push manifest
          docker manifest push ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}

          # Tag as latest for main branch
          if [[ "${GITHUB_REF}" == "refs/heads/main" ]]; then
            docker manifest create ${REGISTRY}/${ECR_REPOSITORY}:latest \
              ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-amd64 \
              ${REGISTRY}/${ECR_REPOSITORY}:${GITHUB_SHA}-arm64
            docker manifest push ${REGISTRY}/${ECR_REPOSITORY}:latest
          fi
```

### 4.4 GitLab CI Multi-Platform with Matrix

```yaml
# .gitlab-ci.yml (multi-arch)

stages:
  - build
  - manifest
  - deploy

variables:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
  IMAGE_NAME: myapp

.docker-login: &docker-login
  - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Parallel architecture builds
build:
  stage: build
  image: docker:24-dind
  services:
    - docker:24-dind
  parallel:
    matrix:
      - ARCH: amd64
        RUNNER_TAG: x64
      - ARCH: arm64
        RUNNER_TAG: graviton
  tags:
    - eks
    - ${RUNNER_TAG}
  before_script:
    - *docker-login
  script:
    - docker build
        --platform linux/${ARCH}
        -t ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-${ARCH}
        .
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-${ARCH}

# Create multi-arch manifest
manifest:
  stage: manifest
  image: docker:24
  tags:
    - eks
    - x64
  before_script:
    - *docker-login
  script:
    # Create manifest list
    - docker manifest create ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64

    # Annotate architectures
    - docker manifest annotate ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64
        --os linux --arch amd64

    - docker manifest annotate ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64
        --os linux --arch arm64

    # Push manifest
    - docker manifest push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}

    # Tag as latest for default branch
    - |
      if [ "$CI_COMMIT_BRANCH" == "$CI_DEFAULT_BRANCH" ]; then
        docker manifest create ${ECR_REGISTRY}/${IMAGE_NAME}:latest \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64
        docker manifest push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
      fi
  needs:
    - build
```

### 4.5 Buildx Multi-Platform (Single Runner)

For simpler setups, use Docker Buildx with QEMU emulation:

```yaml
# .github/workflows/buildx-multi-arch.yaml

name: Buildx Multi-Architecture

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, eks, linux, amd64]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/GitHubActionsRole
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push multi-platform
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/myapp:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/myapp:latest
          cache-from: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/myapp:cache
          cache-to: type=registry,ref=${{ steps.login-ecr.outputs.registry }}/myapp:cache,mode=max
```

---

## 5. Build Optimization

### 5.1 BuildKit Cache with ECR

```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN --mount=type=cache,target=/root/.npm \
    npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

Build with cache:

```bash
# Build with ECR cache
docker buildx build \
  --cache-from type=registry,ref=${ECR_REGISTRY}/myapp:cache \
  --cache-to type=registry,ref=${ECR_REGISTRY}/myapp:cache,mode=max \
  --push \
  -t ${ECR_REGISTRY}/myapp:${VERSION} \
  .
```

### 5.2 Kaniko Builds (Rootless)

Kaniko enables building images without Docker daemon:

```yaml
# kaniko-build-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kaniko-build
  namespace: ci
spec:
  backoffLimit: 0
  template:
    spec:
      serviceAccountName: kaniko-builder
      restartPolicy: Never
      containers:
        - name: kaniko
          image: gcr.io/kaniko-project/executor:latest
          args:
            - --dockerfile=Dockerfile
            - --context=git://github.com/myorg/myrepo.git#refs/heads/main
            - --destination=123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:latest
            - --cache=true
            - --cache-repo=123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp/cache
            - --snapshot-mode=redo
            - --use-new-run
          env:
            - name: AWS_REGION
              value: us-east-1
          resources:
            limits:
              cpu: "2"
              memory: 4Gi
            requests:
              cpu: "1"
              memory: 2Gi
```

GitLab CI with Kaniko:

```yaml
# .gitlab-ci.yml (kaniko)

build:kaniko:
  stage: build
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  tags:
    - eks
  script:
    - |
      /kaniko/executor \
        --context "${CI_PROJECT_DIR}" \
        --dockerfile "${CI_PROJECT_DIR}/Dockerfile" \
        --destination "${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}" \
        --cache=true \
        --cache-repo="${ECR_REGISTRY}/${IMAGE_NAME}/cache" \
        --snapshot-mode=redo \
        --use-new-run
```

### 5.3 Layer Caching Strategies

```dockerfile
# Optimized Dockerfile for caching

# Stage 1: Dependencies (cached unless package files change)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build (cached unless source changes)
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
# Copy configuration first (changes less often)
COPY tsconfig.json next.config.js ./
# Copy source last (changes most often)
COPY src ./src
COPY public ./public
RUN npm run build

# Stage 3: Production image
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

### 5.4 S3 Cache for Build Artifacts

```yaml
# GitLab Runner cache configuration
runners:
  config: |
    [[runners]]
      [runners.cache]
        Type = "s3"
        Shared = true
        [runners.cache.s3]
          ServerAddress = "s3.amazonaws.com"
          BucketName = "ci-cache-bucket"
          BucketLocation = "us-east-1"
```

```hcl
# S3 bucket for CI cache
resource "aws_s3_bucket" "ci_cache" {
  bucket = "ci-cache-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_lifecycle_configuration" "ci_cache" {
  bucket = aws_s3_bucket.ci_cache.id

  rule {
    id     = "expire-old-cache"
    status = "Enabled"

    expiration {
      days = 7
    }

    filter {
      prefix = "runner/"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ci_cache" {
  bucket = aws_s3_bucket.ci_cache.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

---

## Summary

This guide covered the complete setup for EKS-based CI pipelines:

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| ECR | Container registry | Lifecycle policies, scanning, cross-account access |
| GitLab Runner | GitLab CI executor | Kubernetes executor, Pod Identity, S3 cache |
| ARC | GitHub Actions runner | Scale-from-zero, webhook-based autoscaling |
| Multi-platform | ARM + x86 builds | Native runners, manifest lists |
| BuildKit/Kaniko | Optimized builds | Layer caching, rootless builds |

**Best Practices:**
- Use Pod Identity for secure AWS access (no static credentials)
- Enable scale-from-zero to optimize costs
- Implement multi-stage Dockerfiles for smaller images
- Use registry-based caching for faster builds
- Run security scans as part of the pipeline

---

## Related Documentation

- [ArgoCD Multi-Cluster Deployment](./04-gitops-multi-cluster.md)
- [GitOps Fundamentals](../gitops/argocd/README.md)
- [EKS Networking](../eks/03-eks-networking-part1.md)
- [Pod Identity Configuration](../eks/02-eks-cluster-creation-part3.md)

---

< [Previous: NLB Blue/Green](./02-infrastructure-advanced.md) | [Table of Contents](./README.md) | [Next: ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) >
