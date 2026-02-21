# EKS 기반 CI 파이프라인: ECR 빌드 및 푸시

> **지원 버전**: EKS 1.28+, GitLab Runner 17.0+, ARC 0.9+
> **마지막 업데이트**: 2025년 6월

< [이전: NLB 블루/그린](./02-infrastructure-advanced.md) | [목차](./README.md) | [다음: ArgoCD 멀티클러스터](./04-gitops-multi-cluster.md) >

---

이 문서에서는 Amazon EKS 클러스터에서 CI(Continuous Integration) 파이프라인을 구축하고 Amazon ECR(Elastic Container Registry)에 컨테이너 이미지를 빌드하여 푸시하는 방법을 설명합니다.

## 목차

- [ECR 설정](#ecr-설정)
- [GitLab Runner on EKS](#gitlab-runner-on-eks)
- [GitHub Self-Hosted Runner](#github-self-hosted-runner)
- [Multi-Platform Build](#multi-platform-build)
- [빌드 최적화](#빌드-최적화)

---

## ECR 설정

Amazon ECR은 완전관리형 컨테이너 레지스트리로, EKS와 긴밀하게 통합됩니다. Terraform을 사용하여 ECR 리포지토리를 설정하고 이미지 스캐닝, 수명 주기 정책, 교차 계정 액세스를 구성합니다.

### Terraform ECR 리포지토리 생성

```hcl
# ecr.tf - ECR 리포지토리 및 정책 설정

# ECR 리포지토리 생성
resource "aws_ecr_repository" "app" {
  name                 = "mycompany/myapp"
  image_tag_mutability = "IMMUTABLE"  # 이미지 태그 불변성 설정

  # 이미지 스캐닝 설정
  image_scanning_configuration {
    scan_on_push = true  # 푸시 시 자동 스캔
  }

  # 암호화 설정
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.ecr.arn
  }

  tags = {
    Environment = "production"
    Team        = "platform"
  }
}

# KMS 키 생성 (ECR 암호화용)
resource "aws_kms_key" "ecr" {
  description             = "ECR repository encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "ecr-encryption-key"
  }
}

# 이미지 수명 주기 정책
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "최근 30개의 프로덕션 이미지 유지"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["prod-", "release-"]
          countType     = "imageCountMoreThan"
          countNumber   = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "최근 10개의 개발 이미지 유지"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev-", "feature-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 3
        description  = "태그 없는 이미지 7일 후 삭제"
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
        rulePriority = 4
        description  = "90일 이상된 이미지 삭제"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 90
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

### 이미지 스캐닝 구성

```hcl
# ecr-scanning.tf - 향상된 스캐닝 설정

# 레지스트리 스캐닝 구성 (향상된 스캐닝)
resource "aws_ecr_registry_scanning_configuration" "this" {
  scan_type = "ENHANCED"  # Inspector 기반 향상된 스캐닝

  rule {
    scan_frequency = "CONTINUOUS_SCAN"  # 지속적 스캐닝
    repository_filter {
      filter      = "*"
      filter_type = "WILDCARD"
    }
  }

  rule {
    scan_frequency = "SCAN_ON_PUSH"
    repository_filter {
      filter      = "mycompany/*"
      filter_type = "WILDCARD"
    }
  }
}

# 스캔 결과 알림을 위한 EventBridge 규칙
resource "aws_cloudwatch_event_rule" "ecr_scan" {
  name        = "ecr-scan-findings"
  description = "ECR 이미지 스캔 결과 알림"

  event_pattern = jsonencode({
    source      = ["aws.ecr"]
    detail-type = ["ECR Image Scan"]
    detail = {
      scan-status = ["COMPLETE"]
      finding-severity-counts = {
        CRITICAL = [{ "numeric" : [">", 0] }]
        HIGH     = [{ "numeric" : [">", 0] }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.ecr_scan.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security_alerts.arn
}
```

### 교차 계정 액세스 정책

```hcl
# ecr-cross-account.tf - 교차 계정 액세스 설정

variable "allowed_accounts" {
  description = "ECR 액세스를 허용할 AWS 계정 ID 목록"
  type        = list(string)
  default     = ["111111111111", "222222222222"]
}

# ECR 리포지토리 정책 (교차 계정 풀 허용)
resource "aws_ecr_repository_policy" "cross_account" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CrossAccountPull"
        Effect = "Allow"
        Principal = {
          AWS = [for account in var.allowed_accounts : "arn:aws:iam::${account}:root"]
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
      },
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:ap-northeast-2:${data.aws_caller_identity.current.account_id}:function:*"
          }
        }
      }
    ]
  })
}

data "aws_caller_identity" "current" {}
```

### 멀티 리전 복제 구성

```hcl
# ecr-replication.tf - 멀티 리전 복제 설정

resource "aws_ecr_replication_configuration" "this" {
  replication_configuration {
    rule {
      destination {
        region      = "us-west-2"
        registry_id = data.aws_caller_identity.current.account_id
      }

      destination {
        region      = "eu-west-1"
        registry_id = data.aws_caller_identity.current.account_id
      }

      repository_filter {
        filter      = "mycompany/myapp"
        filter_type = "PREFIX_MATCH"
      }
    }

    # 교차 계정 복제 (DR 계정으로)
    rule {
      destination {
        region      = "ap-northeast-2"
        registry_id = "333333333333"  # DR 계정 ID
      }

      repository_filter {
        filter      = "mycompany/myapp"
        filter_type = "PREFIX_MATCH"
      }
    }
  }
}
```

---

## GitLab Runner on EKS

GitLab Runner를 EKS 클러스터에 배포하여 CI 파이프라인을 실행합니다. Kubernetes executor를 사용하면 각 빌드 작업이 독립된 Pod에서 실행됩니다.

### Helm values.yaml 설정

```yaml
# gitlab-runner-values.yaml
gitlabUrl: https://gitlab.com/
runnerRegistrationToken: ""  # 더 이상 사용하지 않음 (deprecated)

# Runner 인증 토큰 (GitLab 16.0+ 권장 방식)
runnerToken: ""  # GitLab UI에서 생성한 러너 토큰

# 동시 실행 작업 수
concurrent: 10

# 체크 간격 (초)
checkInterval: 3

# 로그 수준
logLevel: info

# RBAC 설정
rbac:
  create: true
  rules:
    - apiGroups: [""]
      resources: ["pods", "pods/exec", "secrets", "configmaps"]
      verbs: ["get", "list", "watch", "create", "delete", "update"]
    - apiGroups: [""]
      resources: ["pods/log"]
      verbs: ["get"]

# ServiceAccount 설정
serviceAccount:
  create: true
  name: gitlab-runner
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/GitLabRunnerRole

# Runner Pod 리소스
resources:
  limits:
    memory: 512Mi
    cpu: 500m
  requests:
    memory: 256Mi
    cpu: 200m

# Node 선택
nodeSelector:
  workload-type: ci-runner

# Tolerations
tolerations:
  - key: "ci-runner"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"

# Runner 설정 (config.toml)
runners:
  config: |
    [[runners]]
      name = "eks-kubernetes-runner"
      executor = "kubernetes"
      [runners.kubernetes]
        namespace = "gitlab-runner"
        image = "alpine:latest"
        privileged = false

        # Pod 리소스 제한
        cpu_limit = "2"
        cpu_limit_overwrite_max_allowed = "4"
        cpu_request = "500m"
        cpu_request_overwrite_max_allowed = "2"
        memory_limit = "4Gi"
        memory_limit_overwrite_max_allowed = "8Gi"
        memory_request = "1Gi"
        memory_request_overwrite_max_allowed = "4Gi"

        # 서비스 리소스 제한
        service_cpu_limit = "1"
        service_cpu_request = "100m"
        service_memory_limit = "1Gi"
        service_memory_request = "256Mi"

        # Helper 컨테이너 설정
        helper_cpu_limit = "500m"
        helper_cpu_request = "100m"
        helper_memory_limit = "256Mi"
        helper_memory_request = "128Mi"

        # Pod 어노테이션
        [runners.kubernetes.pod_annotations]
          "prometheus.io/scrape" = "true"
          "prometheus.io/port" = "9252"

        # Pod 라벨
        [runners.kubernetes.pod_labels]
          "app" = "gitlab-ci"
          "environment" = "ci"

        # Node 선택자
        [runners.kubernetes.node_selector]
          "workload-type" = "ci-build"

        # Tolerations
        [[runners.kubernetes.node_tolerations]]
          key = "ci-build"
          operator = "Equal"
          value = "true"
          effect = "NoSchedule"

        # 볼륨 마운트 (캐시용)
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-cache"
          mount_path = "/var/lib/docker"
          medium = "Memory"

        [[runners.kubernetes.volumes.empty_dir]]
          name = "build-cache"
          mount_path = "/cache"

        # 환경 변수
        [runners.kubernetes.pod_spec_patch]
          terminationGracePeriodSeconds = 30

      # Docker-in-Docker 서비스 설정
      [runners.kubernetes.services]
        [[runners.kubernetes.services]]
          name = "docker-dind"
          alias = "docker"

      # 캐시 설정 (S3)
      [runners.cache]
        Type = "s3"
        Shared = true
        [runners.cache.s3]
          ServerAddress = "s3.amazonaws.com"
          BucketName = "gitlab-runner-cache-bucket"
          BucketLocation = "ap-northeast-2"
```

### IAM 역할 및 신뢰 정책 (Pod Identity)

```hcl
# iam-gitlab-runner.tf - GitLab Runner용 IAM 설정

# IAM 역할 생성
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

  tags = {
    Purpose = "GitLab Runner on EKS"
  }
}

# ECR 푸시 정책
resource "aws_iam_role_policy" "ecr_push" {
  name = "ecr-push-policy"
  role = aws_iam_role.gitlab_runner.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRGetAuthToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "arn:aws:ecr:ap-northeast-2:123456789012:repository/mycompany/*"
      }
    ]
  })
}

# S3 캐시 버킷 액세스 정책
resource "aws_iam_role_policy" "s3_cache" {
  name = "s3-cache-policy"
  role = aws_iam_role.gitlab_runner.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3CacheAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::gitlab-runner-cache-bucket",
          "arn:aws:s3:::gitlab-runner-cache-bucket/*"
        ]
      }
    ]
  })
}

# EKS Pod Identity Association
resource "aws_eks_pod_identity_association" "gitlab_runner" {
  cluster_name    = var.cluster_name
  namespace       = "gitlab-runner"
  service_account = "gitlab-runner"
  role_arn        = aws_iam_role.gitlab_runner.arn
}
```

### .gitlab-ci.yml 예제

```yaml
# .gitlab-ci.yml - 완전한 CI 파이프라인 예제

variables:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
  IMAGE_NAME: mycompany/myapp
  DOCKER_HOST: tcp://docker:2376
  DOCKER_TLS_CERTDIR: "/certs"
  DOCKER_TLS_VERIFY: 1
  DOCKER_CERT_PATH: "$DOCKER_TLS_CERTDIR/client"

stages:
  - test
  - build
  - scan
  - push

# 기본 이미지 및 서비스
default:
  image: docker:24.0
  services:
    - docker:24.0-dind
  tags:
    - kubernetes
    - eks

# 캐시 설정
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .npm/
    - node_modules/
    - .cache/

# 단위 테스트
unit-test:
  stage: test
  image: node:20-alpine
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run lint
    - npm run test:unit -- --coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    paths:
      - coverage/
    expire_in: 1 week

# 통합 테스트
integration-test:
  stage: test
  image: node:20-alpine
  services:
    - name: postgres:15-alpine
      alias: db
    - name: redis:7-alpine
      alias: cache
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: test_user
    POSTGRES_PASSWORD: test_password
    DATABASE_URL: postgresql://test_user:test_password@db:5432/test_db
    REDIS_URL: redis://cache:6379
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run test:integration
  allow_failure: false

# Docker 이미지 빌드
build:
  stage: build
  before_script:
    - until docker info; do sleep 1; done
  script:
    - |
      docker build \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VCS_REF=${CI_COMMIT_SHA} \
        --build-arg VERSION=${CI_COMMIT_TAG:-$CI_COMMIT_SHORT_SHA} \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:cache \
        --tag ${IMAGE_NAME}:${CI_COMMIT_SHA} \
        --file Dockerfile \
        .
    - docker save ${IMAGE_NAME}:${CI_COMMIT_SHA} -o image.tar
  artifacts:
    paths:
      - image.tar
    expire_in: 1 hour

# 이미지 보안 스캔 (Trivy)
security-scan:
  stage: scan
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - docker load -i image.tar
    - |
      trivy image \
        --exit-code 1 \
        --severity CRITICAL,HIGH \
        --ignore-unfixed \
        --format json \
        --output trivy-report.json \
        ${IMAGE_NAME}:${CI_COMMIT_SHA}
  artifacts:
    reports:
      container_scanning: trivy-report.json
    paths:
      - trivy-report.json
    expire_in: 1 week
  allow_failure: true

# ECR에 푸시
push:
  stage: push
  before_script:
    - apk add --no-cache aws-cli
    - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
    - docker load -i image.tar
  script:
    # 태그 지정 및 푸시
    - docker tag ${IMAGE_NAME}:${CI_COMMIT_SHA} ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}

    # 브랜치별 태그
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        docker tag ${IMAGE_NAME}:${CI_COMMIT_SHA} ${ECR_REGISTRY}/${IMAGE_NAME}:latest
        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
      fi

    # 릴리스 태그
    - |
      if [ -n "$CI_COMMIT_TAG" ]; then
        docker tag ${IMAGE_NAME}:${CI_COMMIT_SHA} ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG}
        docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG}
      fi
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
```

### S3 캐시 버킷 구성

```hcl
# s3-cache.tf - GitLab Runner 캐시용 S3 버킷

resource "aws_s3_bucket" "gitlab_cache" {
  bucket = "gitlab-runner-cache-bucket"

  tags = {
    Purpose = "GitLab Runner Build Cache"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "gitlab_cache" {
  bucket = aws_s3_bucket.gitlab_cache.id

  rule {
    id     = "expire-old-cache"
    status = "Enabled"

    expiration {
      days = 14
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "gitlab_cache" {
  bucket = aws_s3_bucket.gitlab_cache.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "gitlab_cache" {
  bucket = aws_s3_bucket.gitlab_cache.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

### Runner 토큰 관리

```yaml
# runner-secret.yaml - GitLab Runner 토큰 시크릿
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-runner-token
  namespace: gitlab-runner
type: Opaque
stringData:
  runner-registration-token: ""  # deprecated
  runner-token: "glrt-xxxxxxxxxxxxxxxxxxxx"  # GitLab UI에서 생성
```

```bash
# GitLab Runner 토큰 생성 방법 (GitLab 16.0+)
# 1. GitLab UI -> Settings -> CI/CD -> Runners
# 2. "New project runner" 클릭
# 3. 러너 설정 구성 후 토큰 복사
# 4. Secret으로 저장

kubectl create secret generic gitlab-runner-token \
  --namespace gitlab-runner \
  --from-literal=runner-token="glrt-xxxxxxxxxxxxxxxxxxxx"
```

---

## GitHub Self-Hosted Runner

GitHub Actions Runner Controller(ARC)를 사용하여 EKS에서 자체 호스팅 러너를 운영합니다.

### ARC 설치 (Helm)

```hcl
# arc-installation.tf - Actions Runner Controller 설치

resource "helm_release" "arc_controller" {
  name       = "arc"
  namespace  = "arc-systems"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  chart      = "gha-runner-scale-set-controller"
  version    = "0.9.3"

  create_namespace = true

  values = [
    yamlencode({
      replicaCount = 2

      resources = {
        limits = {
          cpu    = "500m"
          memory = "512Mi"
        }
        requests = {
          cpu    = "200m"
          memory = "256Mi"
        }
      }

      metrics = {
        controllerManagerAddr = ":8080"
        listenerAddr          = ":8080"
        listenerEndpoint      = "/metrics"
      }
    })
  ]
}

resource "helm_release" "arc_runner_set" {
  name       = "arc-runner-set"
  namespace  = "arc-runners"
  repository = "oci://ghcr.io/actions/actions-runner-controller-charts"
  chart      = "gha-runner-scale-set"
  version    = "0.9.3"

  create_namespace = true

  depends_on = [helm_release.arc_controller]

  values = [
    yamlencode({
      githubConfigUrl = "https://github.com/myorg/myrepo"

      # GitHub App 인증 (권장)
      githubConfigSecret = {
        github_app_id              = var.github_app_id
        github_app_installation_id = var.github_app_installation_id
        github_app_private_key     = var.github_app_private_key
      }

      minRunners = 1
      maxRunners = 10

      runnerGroup = "eks-runners"

      template = {
        spec = {
          serviceAccountName = "arc-runner"

          containers = [
            {
              name  = "runner"
              image = "ghcr.io/actions/actions-runner:latest"

              resources = {
                limits = {
                  cpu    = "2"
                  memory = "4Gi"
                }
                requests = {
                  cpu    = "500m"
                  memory = "1Gi"
                }
              }

              env = [
                {
                  name  = "DOCKER_HOST"
                  value = "tcp://localhost:2376"
                },
                {
                  name  = "DOCKER_TLS_VERIFY"
                  value = "1"
                },
                {
                  name  = "DOCKER_CERT_PATH"
                  value = "/certs/client"
                }
              ]

              volumeMounts = [
                {
                  name      = "docker-certs"
                  mountPath = "/certs"
                },
                {
                  name      = "work"
                  mountPath = "/home/runner/_work"
                }
              ]
            },
            {
              name  = "docker"
              image = "docker:24.0-dind"

              securityContext = {
                privileged = true
              }

              env = [
                {
                  name  = "DOCKER_TLS_CERTDIR"
                  value = "/certs"
                }
              ]

              volumeMounts = [
                {
                  name      = "docker-certs"
                  mountPath = "/certs"
                },
                {
                  name      = "docker-graph"
                  mountPath = "/var/lib/docker"
                }
              ]
            }
          ]

          volumes = [
            {
              name = "docker-certs"
              emptyDir = {}
            },
            {
              name = "docker-graph"
              emptyDir = {}
            },
            {
              name = "work"
              emptyDir = {}
            }
          ]

          nodeSelector = {
            "workload-type" = "ci-runner"
          }

          tolerations = [
            {
              key      = "ci-runner"
              operator = "Equal"
              value    = "true"
              effect   = "NoSchedule"
            }
          ]
        }
      }
    })
  ]
}
```

### RunnerDeployment / RunnerSet CRD 예제

```yaml
# runner-deployment.yaml - 레거시 ARC v0.x 방식 (참고용)
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: eks-runner-deployment
  namespace: arc-runners
spec:
  replicas: 3
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - eks
        - self-hosted
        - linux

      serviceAccountName: arc-runner

      resources:
        limits:
          cpu: "2"
          memory: "4Gi"
        requests:
          cpu: "500m"
          memory: "1Gi"

      dockerEnabled: true
      dockerMTU: 1500

      nodeSelector:
        workload-type: ci-runner

      tolerations:
        - key: "ci-runner"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"

---
# runner-set.yaml - ARC v0.9+ 권장 방식
apiVersion: actions.github.com/v1alpha1
kind: AutoscalingRunnerSet
metadata:
  name: eks-runner-set
  namespace: arc-runners
spec:
  githubConfigUrl: "https://github.com/myorg"
  githubConfigSecret: github-config-secret

  minRunners: 1
  maxRunners: 20

  runnerGroup: "eks-runners"

  runnerScaleSetName: "eks-k8s-runners"

  template:
    spec:
      serviceAccountName: arc-runner
      containers:
        - name: runner
          image: ghcr.io/actions/actions-runner:latest
          command: ["/home/runner/run.sh"]
          resources:
            limits:
              cpu: "2"
              memory: "4Gi"
            requests:
              cpu: "500m"
              memory: "1Gi"
```

### Scale-from-Zero 설정

```yaml
# horizontal-runner-autoscaler.yaml - 레거시 방식 (참고용)
apiVersion: actions.summerwind.dev/v1alpha1
kind: HorizontalRunnerAutoscaler
metadata:
  name: eks-runner-autoscaler
  namespace: arc-runners
spec:
  scaleTargetRef:
    kind: RunnerDeployment
    name: eks-runner-deployment

  minReplicas: 0
  maxReplicas: 20

  scaleDownDelaySecondsAfterScaleOut: 300

  metrics:
    - type: PercentageRunnersBusy
      scaleUpThreshold: "0.75"
      scaleDownThreshold: "0.25"
      scaleUpFactor: "2"
      scaleDownFactor: "0.5"

    - type: TotalNumberOfQueuedAndInProgressWorkflowRuns
      repositoryNames:
        - myorg/myrepo
      scaleUpThreshold: "1"
      scaleDownThreshold: "0"

---
# ARC v0.9+ 방식에서는 scale-from-zero가 기본 동작
# minRunners: 0으로 설정하면 자동으로 scale-from-zero 활성화
```

### GitHub Actions 워크플로우

```yaml
# .github/workflows/build.yml
name: Build and Push to ECR

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
  IMAGE_NAME: mycompany/myapp

jobs:
  test:
    runs-on: eks-runners  # self-hosted runner label
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm run test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

  build:
    needs: test
    runs-on: eks-runners
    permissions:
      id-token: write
      contents: read

    outputs:
      image: ${{ steps.build.outputs.image }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:cache
          cache-to: type=registry,ref=${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:cache,mode=max
          build-args: |
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}
            VERSION=${{ github.ref_name }}

      - name: Output image
        run: echo "image=${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}" >> $GITHUB_OUTPUT

  security-scan:
    needs: build
    runs-on: eks-runners
    permissions:
      id-token: write
      contents: read
      security-events: write

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build.outputs.image }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

### Pod Identity 설정

```hcl
# iam-github-actions.tf - GitHub Actions용 IAM 설정

# OIDC Provider for GitHub Actions (워크플로우 ID 토큰용)
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]
}

# GitHub Actions용 IAM 역할
resource "aws_iam_role" "github_actions" {
  name = "GitHubActionsRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:myorg/myrepo:*"
          }
        }
      }
    ]
  })
}

# ECR 푸시 정책 연결
resource "aws_iam_role_policy_attachment" "ecr_push" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.ecr_push.arn
}

# ARC Runner용 Pod Identity
resource "aws_iam_role" "arc_runner" {
  name = "ArcRunnerRole"

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

resource "aws_eks_pod_identity_association" "arc_runner" {
  cluster_name    = var.cluster_name
  namespace       = "arc-runners"
  service_account = "arc-runner"
  role_arn        = aws_iam_role.arc_runner.arn
}
```

---

## Multi-Platform Build

ARM(Graviton)과 x86 아키텍처 모두를 지원하는 멀티 플랫폼 이미지를 빌드합니다.

### ARM Runner NodePool (Graviton)

```yaml
# arm-runner-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-runner-arm
  labels:
    purpose: ci-runner
    arch: arm64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-runner
        arch: arm64
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["c7g", "m7g", "r7g"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]

      taints:
        - key: ci-runner
          value: "true"
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 100
    memory: 200Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
```

### x86 Runner NodePool

```yaml
# x86-runner-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ci-runner-amd64
  labels:
    purpose: ci-runner
    arch: amd64
spec:
  template:
    metadata:
      labels:
        workload-type: ci-runner
        arch: amd64
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["c7i", "m7i", "r7i"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]

      taints:
        - key: ci-runner
          value: "true"
          effect: NoSchedule

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  limits:
    cpu: 100
    memory: 200Gi

  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 5m
```

### GitLab CI 멀티 아키텍처 빌드

```yaml
# .gitlab-ci.yml - 멀티 아키텍처 빌드
variables:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
  IMAGE_NAME: mycompany/myapp

stages:
  - build
  - manifest

# 아키텍처별 병렬 빌드
build:
  stage: build
  image: docker:24.0
  services:
    - docker:24.0-dind
  parallel:
    matrix:
      - ARCH: amd64
        RUNNER_TAG: ci-runner-amd64
      - ARCH: arm64
        RUNNER_TAG: ci-runner-arm64
  tags:
    - ${RUNNER_TAG}
  before_script:
    - apk add --no-cache aws-cli
    - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
  script:
    - |
      docker build \
        --platform linux/${ARCH} \
        --tag ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-${ARCH} \
        --push \
        .
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG

# 멀티 아키텍처 매니페스트 생성
create-manifest:
  stage: manifest
  image: docker:24.0
  tags:
    - kubernetes
  needs:
    - build
  before_script:
    - apk add --no-cache aws-cli
    - aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
  script:
    # 멀티 아키텍처 매니페스트 생성
    - |
      docker manifest create ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64

    # 아키텍처 어노테이션 추가
    - |
      docker manifest annotate ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
        --os linux --arch amd64

    - |
      docker manifest annotate ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64 \
        --os linux --arch arm64

    # 매니페스트 푸시
    - docker manifest push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}

    # latest 태그 (main 브랜치)
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        docker manifest create ${ECR_REGISTRY}/${IMAGE_NAME}:latest \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64
        docker manifest push ${ECR_REGISTRY}/${IMAGE_NAME}:latest
      fi

    # 릴리스 태그
    - |
      if [ -n "$CI_COMMIT_TAG" ]; then
        docker manifest create ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG} \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
          ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64
        docker manifest push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_TAG}
      fi
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
```

### GitHub Actions 멀티 아키텍처 빌드

```yaml
# .github/workflows/multi-arch-build.yml
name: Multi-Architecture Build

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
  IMAGE_NAME: mycompany/myapp

jobs:
  build:
    runs-on: eks-runners
    permissions:
      id-token: write
      contents: read

    strategy:
      matrix:
        platform:
          - linux/amd64
          - linux/arm64
        include:
          - platform: linux/amd64
            runner: eks-runners-amd64
          - platform: linux/arm64
            runner: eks-runners-arm64

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push by platform
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: ${{ matrix.platform }}
          push: true
          tags: ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-${{ matrix.platform == 'linux/amd64' && 'amd64' || 'arm64' }}
          cache-from: type=registry,ref=${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:cache-${{ matrix.platform == 'linux/amd64' && 'amd64' || 'arm64' }}
          cache-to: type=registry,ref=${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:cache-${{ matrix.platform == 'linux/amd64' && 'amd64' || 'arm64' }},mode=max

  manifest:
    needs: build
    runs-on: eks-runners
    permissions:
      id-token: write
      contents: read

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Create and push manifest
        run: |
          # imagetools를 사용한 멀티 아키텍처 매니페스트 생성
          docker buildx imagetools create \
            --tag ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --tag ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:latest \
            ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-amd64 \
            ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-arm64

          # 릴리스 태그
          if [[ "${{ github.ref }}" == refs/tags/* ]]; then
            TAG_NAME="${{ github.ref_name }}"
            docker buildx imagetools create \
              --tag ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${TAG_NAME} \
              ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-amd64 \
              ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-arm64
          fi

      - name: Inspect manifest
        run: |
          docker buildx imagetools inspect ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

---

## 빌드 최적화

빌드 시간을 단축하고 리소스 효율성을 높이는 최적화 기법입니다.

### BuildKit 캐시 활용

```dockerfile
# Dockerfile - BuildKit 최적화
# syntax=docker/dockerfile:1.6

FROM node:20-alpine AS builder

WORKDIR /app

# 패키지 파일만 먼저 복사하여 캐시 활용
COPY package*.json ./

# BuildKit 캐시 마운트 활용
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline

# 소스 코드 복사 및 빌드
COPY . .

RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

# 프로덕션 이미지
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# 비-root 사용자 생성
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 빌드 결과물만 복사
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
```

```yaml
# GitLab CI - BuildKit 캐시 활용
build:
  stage: build
  image: docker:24.0
  services:
    - docker:24.0-dind
  variables:
    DOCKER_BUILDKIT: 1
  script:
    - |
      docker build \
        --cache-from type=registry,ref=${ECR_REGISTRY}/${IMAGE_NAME}:cache \
        --cache-to type=registry,ref=${ECR_REGISTRY}/${IMAGE_NAME}:cache,mode=max \
        --tag ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        --push \
        .
```

### Kaniko 빌드 (Rootless)

```yaml
# kaniko-build.yaml - Docker 데몬 없이 빌드
apiVersion: v1
kind: Pod
metadata:
  name: kaniko-build
  namespace: ci-builds
spec:
  restartPolicy: Never
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:latest
      args:
        - "--dockerfile=Dockerfile"
        - "--context=git://github.com/myorg/myrepo.git#refs/heads/main"
        - "--destination=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/mycompany/myapp:latest"
        - "--cache=true"
        - "--cache-repo=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/mycompany/myapp/cache"
        - "--snapshot-mode=redo"
        - "--use-new-run"
      volumeMounts:
        - name: docker-config
          mountPath: /kaniko/.docker
      resources:
        limits:
          cpu: "2"
          memory: "4Gi"
        requests:
          cpu: "500m"
          memory: "1Gi"
  volumes:
    - name: docker-config
      secret:
        secretName: ecr-docker-config
        items:
          - key: .dockerconfigjson
            path: config.json
  serviceAccountName: kaniko-builder
```

```yaml
# .gitlab-ci.yml - Kaniko 빌드 작업
build-kaniko:
  stage: build
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  tags:
    - kubernetes
  script:
    - |
      # ECR 인증 설정
      mkdir -p /kaniko/.docker
      echo "{\"credsStore\":\"ecr-login\"}" > /kaniko/.docker/config.json
    - |
      /kaniko/executor \
        --context ${CI_PROJECT_DIR} \
        --dockerfile ${CI_PROJECT_DIR}/Dockerfile \
        --destination ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        --cache=true \
        --cache-repo=${ECR_REGISTRY}/${IMAGE_NAME}/cache \
        --snapshot-mode=redo \
        --compressed-caching=false
```

### 레이어 캐싱 전략

```dockerfile
# Dockerfile - 최적화된 레이어 캐싱

# 1단계: 의존성 설치 (캐시 효율 극대화)
FROM node:20-alpine AS deps
WORKDIR /app

# 패키지 매니저 락 파일만 복사
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

# 패키지 매니저에 따라 설치
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

# 2단계: 빌드
FROM node:20-alpine AS builder
WORKDIR /app

# 의존성 복사
COPY --from=deps /app/node_modules ./node_modules

# 소스 코드 복사
COPY . .

# 환경 변수 설정
ENV NEXT_TELEMETRY_DISABLED 1

# 빌드
RUN npm run build

# 3단계: 프로덕션 이미지
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 보안: 비-root 사용자
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 필요한 파일만 복사
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### 빌드 시간 최적화 팁

```yaml
# .gitlab-ci.yml - 빌드 최적화 예제
variables:
  # BuildKit 활성화
  DOCKER_BUILDKIT: 1
  BUILDKIT_PROGRESS: plain

  # 병렬 빌드 설정
  COMPOSE_DOCKER_CLI_BUILD: 1
  COMPOSE_PARALLEL_LIMIT: 4

build-optimized:
  stage: build
  script:
    # 1. 변경된 파일 기반 빌드 스킵
    - |
      if git diff --name-only HEAD~1 HEAD | grep -qvE '(\.md$|\.txt$|docs/)'; then
        echo "코드 변경 감지, 빌드 실행"
      else
        echo "문서만 변경됨, 빌드 스킵"
        exit 0
      fi

    # 2. 병렬 빌드 (멀티 스테이지)
    - |
      docker build \
        --target builder \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:builder-cache \
        --tag ${ECR_REGISTRY}/${IMAGE_NAME}:builder-cache \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        . &

      docker build \
        --target tester \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:tester-cache \
        --tag ${ECR_REGISTRY}/${IMAGE_NAME}:tester-cache \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        . &

      wait

    # 3. 최종 이미지 빌드
    - |
      docker build \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:builder-cache \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:tester-cache \
        --cache-from ${ECR_REGISTRY}/${IMAGE_NAME}:latest \
        --tag ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA} \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        .

    # 4. 캐시 이미지 푸시 (백그라운드)
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:builder-cache &
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:tester-cache &
    - docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${CI_COMMIT_SHA}
    - wait
```

---

## 요약

이 문서에서 다룬 주요 내용:

1. **ECR 설정**: Terraform을 사용한 ECR 리포지토리 생성, 수명 주기 정책, 이미지 스캐닝, 교차 계정 액세스, 멀티 리전 복제 구성

2. **GitLab Runner on EKS**: Helm을 통한 설치, Kubernetes executor 설정, Pod Identity를 통한 ECR 푸시, S3 캐시 구성

3. **GitHub Self-Hosted Runner**: ARC 설치 및 구성, RunnerDeployment/RunnerSet CRD, Scale-from-zero, GitHub Actions 워크플로우

4. **Multi-Platform Build**: ARM(Graviton)과 x86 러너 NodePool, 병렬 빌드, docker manifest 및 buildx imagetools를 통한 멀티 아키텍처 이미지 생성

5. **빌드 최적화**: BuildKit 캐시, Kaniko 빌드, 레이어 캐싱 전략, 빌드 시간 단축 기법

---

## 관련 문서

- [ArgoCD 멀티클러스터 배포](./04-gitops-multi-cluster.md)
- [ArgoCD 기초](../gitops/01-argocd.md)
- [NodePool 구성](../eks-auto-mode/02-nodepool-configuration.md)

---

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [CI 파이프라인 퀴즈](../quizzes/ops/03-ci-pipelines-quiz.md)를 풀어보세요.
