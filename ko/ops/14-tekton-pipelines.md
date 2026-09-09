# Tekton Pipelines: Kubernetes 네이티브 CI/CD

> **지원 버전**: Tekton Pipelines v0.62+, Tekton Triggers v0.28+
> **마지막 업데이트**: 2025년 6월

< [이전: FinOps 비용 가시성 플랫폼](./13-finops-cost-platform.md) | [목차](./README.md) | [다음: 없음] >

---

## 개요 및 학습 목표

### Tekton이란

Tekton은 **Kubernetes 네이티브 CI/CD 프레임워크**로, 빌드, 테스트, 배포 파이프라인을 Kubernetes CRD(Custom Resource Definition)로 선언적으로 정의하고 실행합니다. 2018년 Google의 Knative Build 프로젝트에서 분리되어 시작되었으며, 현재는 **CD Foundation(Continuous Delivery Foundation)**의 핵심 프로젝트이자 **CNCF 생태계**와 긴밀하게 통합됩니다.

Tekton의 핵심 철학은 다음과 같습니다:

- **Kubernetes 네이티브**: 모든 파이프라인 구성 요소가 Kubernetes CRD로 정의됩니다. kubectl로 관리하고, RBAC으로 제어하며, Pod으로 실행됩니다.
- **선언적 파이프라인**: YAML로 파이프라인을 코드로 관리(Pipeline as Code)하여 버전 관리, 코드 리뷰, 재사용이 가능합니다.
- **클라우드 네이티브 공급망 보안**: Tekton Chains를 통해 SLSA Provenance, OCI 이미지 서명, in-toto attestation 등 소프트웨어 공급망 보안을 기본 지원합니다.
- **확장성**: Tekton Hub의 커뮤니티 Task를 재사용하고, Interceptor를 통해 다양한 이벤트 소스와 연동할 수 있습니다.

### Tekton vs 기존 CI/CD 도구 비교

| 특성 | Tekton | Jenkins | GitHub Actions | GitLab CI |
|------|--------|---------|---------------|-----------|
| **실행 환경** | Kubernetes Pod | 전용 서버/에이전트 | GitHub 호스팅/셀프호스팅 | GitLab Runner |
| **파이프라인 정의** | Kubernetes CRD (YAML) | Groovy (Jenkinsfile) | YAML (workflow) | YAML (.gitlab-ci.yml) |
| **확장성** | Kubernetes 수평 확장 | 에이전트 수동 추가 | 러너 자동 확장 | 러너 수동/자동 확장 |
| **상태 관리** | Kubernetes etcd | Jenkins 파일 시스템 | GitHub 인프라 | GitLab 인프라 |
| **공급망 보안** | Tekton Chains 기본 지원 | 플러그인 필요 | Sigstore 제한적 | 제한적 |
| **멀티 클라우드** | 모든 Kubernetes 환경 | 가능 (복잡) | GitHub 종속 | GitLab 종속 |
| **벤더 종속성** | 없음 (오픈소스) | 없음 (오픈소스) | GitHub 종속 | GitLab 종속 |
| **학습 곡선** | 높음 (K8s 지식 필요) | 중간 | 낮음 | 낮음 |
| **운영 부담** | 높음 (자체 운영) | 높음 | 없음 (SaaS) | 중간 |

### 언제 Tekton을 선택하는가

Tekton은 다음과 같은 환경에서 특히 효과적입니다:

- **멀티 클라우드/하이브리드 환경**: 특정 클라우드 벤더에 종속되지 않는 CI/CD가 필요할 때
- **Kubernetes 중심 인프라**: 이미 Kubernetes를 운영 플랫폼으로 사용하고 있을 때
- **공급망 보안 필수 환경**: SLSA, SBOM, 이미지 서명 등 규제 요구사항이 있을 때
- **플랫폼 엔지니어링**: 개발팀에게 셀프서비스 CI/CD 플랫폼을 제공해야 할 때

### 학습 목표

- Tekton의 핵심 CRD(Task, Pipeline, Trigger)를 이해하고 프로덕션급 파이프라인 작성
- EKS 환경에서 Tekton 스택(Pipelines, Triggers, Dashboard, Chains) 설치 및 IRSA 구성
- Tekton Triggers를 활용한 Webhook 기반 자동 파이프라인 트리거 구현
- Tekton Chains를 통한 소프트웨어 공급망 보안(SLSA Provenance, 이미지 서명) 구현
- ArgoCD와 Tekton을 결합한 CI/CD 분리 아키텍처 설계 및 구현
- 프로덕션 환경에서의 Tekton 운영, 모니터링, 문제 해결 역량 확보

---

## 1. Tekton 아키텍처

### 1.1 핵심 CRD 구조

Tekton의 모든 구성 요소는 Kubernetes CRD로 정의됩니다. 다음 다이어그램은 핵심 CRD 간의 관계를 보여줍니다.

![Tekton Triggers가 Webhook 이벤트를 처리해 PipelineRun을 생성하고, PipelineRun이 Pipeline과 TaskRun을 거쳐 Task를 실행해 Workspace/Result에 데이터를 남기며, TaskRun 완료를 Tekton Chains가 감지해 서명과 SLSA Provenance를 만드는 핵심 CRD 구조를 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-0.html)

### 1.2 핵심 CRD 상세

| CRD | 설명 | 유사 개념 |
|-----|------|----------|
| **Task** | 하나의 작업 단위. 여러 Step(컨테이너)으로 구성 | Jenkins Stage, GitHub Actions Job |
| **TaskRun** | Task의 실행 인스턴스. 실행 파라미터와 상태 포함 | 빌드 실행 |
| **Pipeline** | Task들의 실행 순서와 의존 관계를 정의 | Jenkinsfile, workflow |
| **PipelineRun** | Pipeline의 실행 인스턴스 | 파이프라인 실행 |
| **Workspace** | Task/Pipeline 간 데이터를 공유하는 스토리지 | 공유 볼륨 |
| **Result** | Task 간 데이터를 전달하는 매개체 | 출력 변수 |

### 1.3 컨트롤러 아키텍처

Tekton은 Kubernetes Operator 패턴으로 동작합니다. 핵심 컴포넌트는 다음과 같습니다.

![kube-apiserver를 중심으로 tekton-pipelines-controller가 CRD 변경을 감시해 TaskRun Pod를 생성하고, webhook과 resolver가 API 서버를 거쳐 검증·해석하며, 생성된 Pod들이 같은 Workspace PVC를 공유하는 컨트롤 플레인/데이터 플레인 구조를 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-1.html)

**컨트롤러 동작 원리:**

1. 사용자가 `PipelineRun` 또는 `TaskRun` 리소스를 생성합니다.
2. `tekton-pipelines-webhook`이 CRD의 유효성을 검증합니다.
3. `tekton-pipelines-controller`가 리소스 변경을 감지하고, 각 Task에 대해 Pod을 생성합니다.
4. 각 Pod 내에서 Step 컨테이너가 순서대로 실행됩니다.
5. 실행 결과(상태, Results, 아티팩트)가 CRD 상태에 기록됩니다.

### 1.4 Tekton Chains와 공급망 보안

Tekton Chains는 TaskRun 완료 후 자동으로 실행되어 다음을 수행합니다:

- **OCI 이미지 서명**: Cosign/Sigstore를 사용하여 빌드된 이미지에 디지털 서명
- **SLSA Provenance 생성**: 빌드 과정의 출처 증명(provenance)을 SLSA 형식으로 생성
- **in-toto Attestation**: 소프트웨어 공급망의 각 단계를 증명하는 attestation 생성
- **투명성 로그**: Rekor 투명성 로그에 서명 정보를 기록하여 감사 가능성 확보

---

## 2. EKS 설치 및 구성

### 2.1 Tekton Pipelines 설치

```bash
# Tekton Pipelines 최신 안정 버전 설치
kubectl apply --filename https://storage.googleapis.com/tekton-releases/pipeline/latest/release.yaml

# 설치 확인
kubectl get pods -n tekton-pipelines
```

```
NAME                                           READY   STATUS    RESTARTS   AGE
tekton-pipelines-controller-7f4fc9b58d-x2b4k   1/1     Running   0          30s
tekton-pipelines-webhook-6c9d4d5bff-mj7q2      1/1     Running   0          30s
```

**Helm을 사용한 설치 (권장):**

```bash
# Tekton Helm 리포지토리 추가
helm repo add tekton https://tekton.dev/helm-charts
helm repo update

# values 파일 생성
cat <<EOF > tekton-pipelines-values.yaml
# tekton-pipelines-values.yaml
controller:
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      cpu: "500m"
      memory: "512Mi"
  
  # 기능 플래그 설정
  featureFlags:
    # Step 컨테이너에서 Script 필드를 위한 새 API 사용
    enable-api-fields: "beta"
    # Step 결과를 더 큰 크기로 허용 (기본 4096 바이트)
    max-result-size: "10240"
    # 인라인 스펙 지원
    disable-inline-spec: "false"
    # Affinity Assistant 비활성화 (성능 향상)
    disable-affinity-assistant: "true"

webhook:
  resources:
    requests:
      cpu: "50m"
      memory: "128Mi"
    limits:
      cpu: "200m"
      memory: "256Mi"

  replicas: 2  # HA 구성
EOF

# 설치
helm install tekton-pipelines tekton/tekton-pipeline \
  -n tekton-pipelines --create-namespace \
  -f tekton-pipelines-values.yaml
```

### 2.2 Tekton Triggers 설치

```bash
# Tekton Triggers 설치
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/release.yaml

# Interceptors 설치 (GitHub, GitLab, CEL 등)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/triggers/latest/interceptors.yaml

# 설치 확인
kubectl get pods -n tekton-pipelines -l app.kubernetes.io/part-of=tekton-triggers
```

### 2.3 Tekton Dashboard 설치

```bash
# Tekton Dashboard 설치 (읽기 전용 모드)
kubectl apply --filename https://storage.googleapis.com/tekton-releases/dashboard/latest/release.yaml

# 접속 (포트 포워딩)
kubectl port-forward svc/tekton-dashboard -n tekton-pipelines 9097:9097
```

프로덕션 환경에서는 Ingress를 통해 노출하고 인증을 구성합니다:

```yaml
# tekton-dashboard-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tekton-dashboard
  namespace: tekton-pipelines
  annotations:
    # ALB Ingress Controller 사용
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    # OIDC 인증 (Amazon Cognito)
    alb.ingress.kubernetes.io/auth-type: oidc
    alb.ingress.kubernetes.io/auth-idp-oidc: |
      {"issuer":"https://cognito-idp.ap-northeast-2.amazonaws.com/ap-northeast-2_xxxxx",
       "authorizationEndpoint":"https://your-domain.auth.ap-northeast-2.amazoncognito.com/oauth2/authorize",
       "tokenEndpoint":"https://cognito-idp.ap-northeast-2.amazonaws.com/ap-northeast-2_xxxxx/oauth2/token",
       "userInfoEndpoint":"https://cognito-idp.ap-northeast-2.amazonaws.com/ap-northeast-2_xxxxx/oauth2/userInfo",
       "secretName":"cognito-oidc-secret"}
spec:
  rules:
    - host: tekton.internal.example.com
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

### 2.4 Tekton Chains 설치

```bash
# Tekton Chains 설치
kubectl apply --filename https://storage.googleapis.com/tekton-releases/chains/latest/release.yaml

# 설치 확인
kubectl get pods -n tekton-chains
```

### 2.5 IRSA 구성 (ECR Push, S3 접근)

Tekton Pipeline의 TaskRun Pod이 AWS 서비스에 접근하려면 IRSA(IAM Roles for Service Accounts)를 구성해야 합니다.

```yaml
# tekton-irsa-policy.json
# ECR Push 및 S3 접근을 위한 IAM 정책
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPush",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3ArtifactAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::tekton-artifacts-*",
        "arn:aws:s3:::tekton-artifacts-*/*"
      ]
    }
  ]
}
```

```bash
# IRSA용 IAM 역할 생성
CLUSTER_NAME="my-eks-cluster"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME \
  --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')

# IAM 역할 생성
aws iam create-role \
  --role-name tekton-pipeline-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::'$ACCOUNT_ID':oidc-provider/'$OIDC_PROVIDER'"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "'$OIDC_PROVIDER':sub": "system:serviceaccount:tekton-pipelines:tekton-pipeline-sa"
        }
      }
    }]
  }'

# 정책 연결
aws iam put-role-policy \
  --role-name tekton-pipeline-role \
  --policy-name tekton-ecr-s3-policy \
  --policy-document file://tekton-irsa-policy.json

# Kubernetes ServiceAccount 생성 (IRSA 어노테이션 포함)
kubectl create serviceaccount tekton-pipeline-sa -n tekton-pipelines
kubectl annotate serviceaccount tekton-pipeline-sa \
  -n tekton-pipelines \
  eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/tekton-pipeline-role
```

**Terraform을 사용한 IRSA 구성:**

```hcl
# tekton-irsa.tf
module "tekton_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "tekton-pipeline-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["tekton-pipelines:tekton-pipeline-sa"]
    }
  }

  role_policy_arns = {
    ecr_push = aws_iam_policy.tekton_ecr_push.arn
    s3_access = aws_iam_policy.tekton_s3_access.arn
  }
}

resource "aws_iam_policy" "tekton_ecr_push" {
  name   = "tekton-ecr-push"
  policy = file("${path.module}/policies/tekton-ecr-push.json")
}

resource "aws_iam_policy" "tekton_s3_access" {
  name   = "tekton-s3-access"
  policy = file("${path.module}/policies/tekton-s3-access.json")
}

resource "kubernetes_service_account" "tekton_pipeline" {
  metadata {
    name      = "tekton-pipeline-sa"
    namespace = "tekton-pipelines"
    annotations = {
      "eks.amazonaws.com/role-arn" = module.tekton_irsa.iam_role_arn
    }
  }
}
```

---

## 3. Task 작성

### 3.1 Task 기본 구조

Task는 Tekton의 가장 기본적인 실행 단위입니다. 하나 이상의 Step으로 구성되며, 각 Step은 별도의 컨테이너에서 실행됩니다.

```yaml
# basic-task.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: hello-world
  namespace: tekton-pipelines
spec:
  # 파라미터 정의
  params:
    - name: greeting
      type: string
      default: "Hello"
    - name: target
      type: string
      description: "인사 대상"

  # 결과 정의 (다른 Task에서 참조 가능)
  results:
    - name: message
      description: "생성된 인사 메시지"

  # Step 정의 (순서대로 실행)
  steps:
    - name: greet
      image: alpine:3.19
      script: |
        #!/bin/sh
        MSG="$(params.greeting), $(params.target)!"
        echo "$MSG"
        # 결과를 파일에 기록 (다른 Task에서 참조)
        echo -n "$MSG" | tee $(results.message.path)
```

### 3.2 프로덕션급 빌드 Task

다음은 Kaniko를 사용하여 컨테이너 이미지를 빌드하고 ECR에 Push하는 완전한 Task입니다.

```yaml
# task-kaniko-build.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: kaniko-build
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/version: "0.1"
  annotations:
    tekton.dev/pipelines.minVersion: "0.62.0"
    tekton.dev/categories: "Image Build"
    tekton.dev/tags: "image-build,kaniko,ecr"
spec:
  description: >
    Kaniko를 사용하여 컨테이너 이미지를 빌드하고 ECR에 Push합니다.
    멀티 스테이지 빌드, 캐시 활용, 이미지 다이제스트 출력을 지원합니다.

  params:
    - name: IMAGE
      description: "빌드할 이미지의 전체 경로 (예: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp)"
      type: string
    - name: TAG
      description: "이미지 태그"
      type: string
      default: "latest"
    - name: DOCKERFILE
      description: "Dockerfile 경로"
      type: string
      default: "./Dockerfile"
    - name: CONTEXT
      description: "빌드 컨텍스트 경로"
      type: string
      default: "."
    - name: BUILD_ARGS
      description: "Docker build arguments (--build-arg 형식)"
      type: array
      default: []
    - name: CACHE_REPO
      description: "Kaniko 캐시 리포지토리 (비워두면 캐시 비활성화)"
      type: string
      default: ""

  results:
    - name: IMAGE_DIGEST
      description: "빌드된 이미지의 SHA256 다이제스트"
    - name: IMAGE_URL
      description: "빌드된 이미지의 전체 URL (태그 포함)"

  workspaces:
    - name: source
      description: "소스 코드가 포함된 workspace"
    - name: dockerconfig
      description: "Docker 레지스트리 인증 정보"
      optional: true

  stepTemplate:
    env:
      - name: AWS_REGION
        value: "ap-northeast-2"

  steps:
    # Step 1: ECR 로그인
    - name: ecr-login
      image: amazon/aws-cli:2.15.0
      script: |
        #!/bin/bash
        set -eu

        echo "[INFO] ECR 로그인 수행 중..."
        REGISTRY=$(echo "$(params.IMAGE)" | cut -d'/' -f1)
        
        aws ecr get-login-password --region $AWS_REGION | \
          tee /workspace/dockerconfig/config.json > /dev/null

        # Docker config 형식으로 변환
        TOKEN=$(aws ecr get-login-password --region $AWS_REGION)
        cat > /workspace/dockerconfig/config.json <<EOCFG
        {
          "auths": {
            "${REGISTRY}": {
              "auth": "$(echo -n "AWS:${TOKEN}" | base64)"
            }
          }
        }
        EOCFG

        echo "[INFO] ECR 로그인 완료: ${REGISTRY}"

    # Step 2: Kaniko 빌드 및 Push
    - name: build-and-push
      image: gcr.io/kaniko-project/executor:v1.23.0
      args:
        - --dockerfile=$(params.DOCKERFILE)
        - --context=dir://$(workspaces.source.path)/$(params.CONTEXT)
        - --destination=$(params.IMAGE):$(params.TAG)
        - --digest-file=$(results.IMAGE_DIGEST.path)
        - --snapshotMode=redo
        - --compressed-caching=false
        - --use-new-run
      env:
        - name: DOCKER_CONFIG
          value: /workspace/dockerconfig
      securityContext:
        runAsUser: 0

    # Step 3: 결과 기록
    - name: write-url
      image: alpine:3.19
      script: |
        #!/bin/sh
        DIGEST=$(cat $(results.IMAGE_DIGEST.path))
        echo -n "$(params.IMAGE):$(params.TAG)@${DIGEST}" | tee $(results.IMAGE_URL.path)
        echo ""
        echo "[INFO] 이미지 빌드 완료"
        echo "  URL: $(params.IMAGE):$(params.TAG)"
        echo "  Digest: ${DIGEST}"
```

### 3.3 테스트 Task

```yaml
# task-run-tests.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: run-tests
  namespace: tekton-pipelines
spec:
  description: >
    소스 코드에 대해 유닛 테스트와 린트를 실행합니다.

  params:
    - name: TEST_COMMAND
      description: "테스트 실행 명령어"
      type: string
      default: "go test ./... -v -coverprofile=coverage.out"
    - name: LINT_COMMAND
      description: "린트 실행 명령어"
      type: string
      default: "golangci-lint run"
    - name: LANGUAGE
      description: "프로그래밍 언어 (go, python, node)"
      type: string
      default: "go"

  results:
    - name: COVERAGE
      description: "테스트 커버리지 비율"
    - name: TEST_RESULT
      description: "테스트 결과 (pass/fail)"

  workspaces:
    - name: source
      description: "소스 코드 workspace"

  sidecars:
    # 테스트에 필요한 의존성 서비스 (예: PostgreSQL)
    - name: postgres
      image: postgres:16-alpine
      env:
        - name: POSTGRES_USER
          value: test
        - name: POSTGRES_PASSWORD
          value: test
        - name: POSTGRES_DB
          value: testdb
      readinessProbe:
        exec:
          command: ["pg_isready", "-U", "test"]
        initialDelaySeconds: 5
        periodSeconds: 3

  steps:
    - name: wait-for-dependencies
      image: alpine:3.19
      script: |
        #!/bin/sh
        echo "[INFO] 의존성 서비스 준비 대기 중..."
        sleep 5
        echo "[INFO] 의존성 서비스 준비 완료"

    - name: run-lint
      image: golangci/golangci-lint:v1.59
      workingDir: $(workspaces.source.path)
      script: |
        #!/bin/bash
        set -e
        echo "[INFO] 린트 검사 실행 중..."
        $(params.LINT_COMMAND)
        echo "[INFO] 린트 검사 통과"

    - name: run-tests
      image: golang:1.22-alpine
      workingDir: $(workspaces.source.path)
      env:
        - name: DATABASE_URL
          value: "postgres://test:test@localhost:5432/testdb?sslmode=disable"
      script: |
        #!/bin/bash
        set -e
        echo "[INFO] 테스트 실행 중..."
        $(params.TEST_COMMAND)
        
        # 커버리지 추출
        if [ -f coverage.out ]; then
          COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}')
          echo -n "$COVERAGE" | tee $(results.COVERAGE.path)
          echo "[INFO] 테스트 커버리지: $COVERAGE"
        fi
        
        echo -n "pass" | tee $(results.TEST_RESULT.path)
        echo "[INFO] 모든 테스트 통과"
```

### 3.4 Sidecar 활용

위의 테스트 Task에서 보듯이, Sidecar는 테스트 의존성 서비스(DB, 캐시 등)를 Task와 함께 실행할 때 사용합니다. 주요 활용 사례는 다음과 같습니다:

- **데이터베이스**: PostgreSQL, MySQL, MongoDB 등을 Sidecar로 실행하여 통합 테스트 수행
- **캐시**: Redis, Memcached를 Sidecar로 실행
- **Docker-in-Docker**: DinD Sidecar로 Docker 빌드 (Kaniko 대안)
- **프록시**: Envoy, Nginx 등을 Sidecar로 실행하여 네트워크 테스트

### 3.5 재사용 가능한 Task (Tekton Hub)

Tekton Hub는 커뮤니티가 관리하는 Task 카탈로그입니다. 자주 사용하는 Task를 재사용하여 파이프라인 개발 시간을 단축할 수 있습니다.

```bash
# Tekton CLI로 Hub에서 Task 설치
# git-clone Task 설치
tkn hub install task git-clone

# kaniko Task 설치
tkn hub install task kaniko

# 설치된 Task 확인
tkn task list
```

주요 커뮤니티 Task:

| Task | 설명 | 사용 사례 |
|------|------|----------|
| `git-clone` | Git 리포지토리 클론 | 소스 코드 체크아웃 |
| `kaniko` | Kaniko 이미지 빌드 | Dockerfile 빌드 |
| `buildah` | Buildah 이미지 빌드 | OCI 이미지 빌드 |
| `golang-test` | Go 테스트 실행 | Go 프로젝트 테스트 |
| `pylint` | Python 린트 | Python 코드 품질 검사 |
| `trivy-scanner` | Trivy 취약점 스캔 | 이미지 보안 스캔 |
| `helm-upgrade-from-source` | Helm 배포 | Kubernetes 배포 |

---

## 4. Pipeline 구성

### 4.1 Pipeline 기본 구조

Pipeline은 여러 Task를 조합하여 CI/CD 워크플로우를 정의합니다. Task 간 순서, 병렬 실행, 조건부 실행 등을 선언적으로 구성할 수 있습니다.

![git-clone 이후 테스트와 린트가 병렬로 실행되고 두 결과가 이미지 빌드로 합류한 뒤 취약점 스캔과 배포로 이어지며, 배포가 끝나면 finally 영역의 슬랙 알림과 정리 작업이 항상 함께 실행되는 CI/CD Task 그래프를 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-2.html)

### 4.2 완전한 CI/CD Pipeline

```yaml
# pipeline-ci-cd.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: ci-cd-pipeline
  namespace: tekton-pipelines
spec:
  description: >
    완전한 CI/CD 파이프라인: 소스 클론 → 테스트 → 빌드 → 이미지 Push → 취약점 스캔 → 배포

  # Pipeline 파라미터
  params:
    - name: git-url
      type: string
      description: "Git 리포지토리 URL"
    - name: git-revision
      type: string
      description: "Git 브랜치 또는 커밋"
      default: "main"
    - name: image-registry
      type: string
      description: "ECR 리포지토리 URL"
    - name: image-tag
      type: string
      description: "이미지 태그"
      default: "latest"
    - name: deployment-name
      type: string
      description: "Kubernetes Deployment 이름"
    - name: namespace
      type: string
      description: "배포 대상 네임스페이스"
      default: "default"

  # Pipeline Workspace
  workspaces:
    - name: shared-workspace
      description: "Task 간 공유 workspace"
    - name: docker-credentials
      description: "Docker 레지스트리 인증 정보"
    - name: git-credentials
      description: "Git 인증 정보"
      optional: true

  # Task 정의
  tasks:
    # 1. 소스 코드 클론
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.git-url)
        - name: revision
          value: $(params.git-revision)
        - name: deleteExisting
          value: "true"
      workspaces:
        - name: output
          workspace: shared-workspace

    # 2. 유닛 테스트 (clone 이후 실행)
    - name: test
      runAfter: ["clone"]
      taskRef:
        name: run-tests
      params:
        - name: TEST_COMMAND
          value: "go test ./... -v -coverprofile=coverage.out -count=1"
      workspaces:
        - name: source
          workspace: shared-workspace

    # 3. 린트 (clone 이후 병렬 실행)
    - name: lint
      runAfter: ["clone"]
      taskRef:
        name: run-tests
      params:
        - name: TEST_COMMAND
          value: "golangci-lint run --timeout 5m"
      workspaces:
        - name: source
          workspace: shared-workspace

    # 4. 이미지 빌드 (테스트 + 린트 모두 통과 후)
    - name: build
      runAfter: ["test", "lint"]
      taskRef:
        name: kaniko-build
      params:
        - name: IMAGE
          value: $(params.image-registry)
        - name: TAG
          value: $(params.image-tag)
        - name: CONTEXT
          value: "."
      workspaces:
        - name: source
          workspace: shared-workspace
        - name: dockerconfig
          workspace: docker-credentials

    # 5. 취약점 스캔 (빌드 이후)
    - name: scan
      runAfter: ["build"]
      taskRef:
        name: trivy-scan
      params:
        - name: IMAGE
          value: "$(tasks.build.results.IMAGE_URL)"
        - name: SEVERITY
          value: "CRITICAL,HIGH"
      workspaces:
        - name: manifest-dir
          workspace: shared-workspace

    # 6. Kubernetes 배포 (스캔 통과 후)
    - name: deploy
      runAfter: ["scan"]
      taskRef:
        name: kubectl-deploy
      params:
        - name: DEPLOYMENT
          value: $(params.deployment-name)
        - name: NAMESPACE
          value: $(params.namespace)
        - name: IMAGE
          value: "$(tasks.build.results.IMAGE_URL)"

  # Finally Task (항상 실행)
  finally:
    # Slack 알림 전송
    - name: notify
      taskRef:
        name: send-slack-notification
      params:
        - name: pipeline-name
          value: $(context.pipelineRun.name)
        - name: status
          value: $(tasks.status)
        - name: image
          value: "$(tasks.build.results.IMAGE_URL)"

    # 임시 리소스 정리
    - name: cleanup
      taskRef:
        name: cleanup-workspace
      workspaces:
        - name: source
          workspace: shared-workspace
```

### 4.3 PipelineRun으로 실행

```yaml
# pipelinerun-example.yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: ci-cd-pipeline-run-
  namespace: tekton-pipelines
spec:
  pipelineRef:
    name: ci-cd-pipeline
  
  params:
    - name: git-url
      value: "https://github.com/myorg/myapp.git"
    - name: git-revision
      value: "main"
    - name: image-registry
      value: "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp"
    - name: image-tag
      value: "v1.2.3"
    - name: deployment-name
      value: "myapp"
    - name: namespace
      value: "production"

  workspaces:
    # PVC를 사용한 공유 workspace
    - name: shared-workspace
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 5Gi
          storageClassName: gp3

    # ECR 인증 Secret
    - name: docker-credentials
      secret:
        secretName: ecr-credentials

    # Git 인증 Secret
    - name: git-credentials
      secret:
        secretName: git-credentials

  # TaskRun 파드에 적용할 ServiceAccount
  taskRunTemplate:
    serviceAccountName: tekton-pipeline-sa

  # 타임아웃 설정
  timeouts:
    pipeline: "1h"
    tasks: "30m"
    finally: "10m"
```

### 4.4 조건부 실행 (when)

```yaml
# 조건부 실행 예제: 특정 브랜치에서만 배포
tasks:
  - name: deploy-to-staging
    runAfter: ["build"]
    when:
      - input: $(params.git-revision)
        operator: in
        values: ["develop", "staging"]
    taskRef:
      name: kubectl-deploy
    params:
      - name: NAMESPACE
        value: "staging"

  - name: deploy-to-production
    runAfter: ["build"]
    when:
      - input: $(params.git-revision)
        operator: in
        values: ["main"]
      # 테스트 커버리지가 80% 이상일 때만 배포
      - input: $(tasks.test.results.TEST_RESULT)
        operator: in
        values: ["pass"]
    taskRef:
      name: kubectl-deploy
    params:
      - name: NAMESPACE
        value: "production"
```

### 4.5 Finally Task

Finally Task는 파이프라인의 성공/실패 여부에 관계없이 항상 실행됩니다. 주로 알림 전송, 리소스 정리, 보고서 생성에 사용합니다.

```yaml
# Slack 알림 전송 Task
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: send-slack-notification
  namespace: tekton-pipelines
spec:
  params:
    - name: pipeline-name
      type: string
    - name: status
      type: string
    - name: image
      type: string
      default: "N/A"

  steps:
    - name: send-notification
      image: curlimages/curl:8.5.0
      env:
        - name: SLACK_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: slack-webhook
              key: url
      script: |
        #!/bin/sh
        STATUS="$(params.status)"
        
        if [ "$STATUS" = "Succeeded" ]; then
          COLOR="#36a64f"
          EMOJI=":white_check_mark:"
          STATUS_TEXT="성공"
        else
          COLOR="#ff0000"
          EMOJI=":x:"
          STATUS_TEXT="실패"
        fi

        curl -s -X POST "$SLACK_WEBHOOK_URL" \
          -H "Content-Type: application/json" \
          -d '{
            "attachments": [{
              "color": "'$COLOR'",
              "blocks": [
                {
                  "type": "header",
                  "text": {
                    "type": "plain_text",
                    "text": "'$EMOJI' Pipeline '$STATUS_TEXT'"
                  }
                },
                {
                  "type": "section",
                  "fields": [
                    {"type": "mrkdwn", "text": "*Pipeline:*\n$(params.pipeline-name)"},
                    {"type": "mrkdwn", "text": "*Status:*\n'$STATUS_TEXT'"},
                    {"type": "mrkdwn", "text": "*Image:*\n$(params.image)"}
                  ]
                }
              ]
            }]
          }'
```

---

## 5. Tekton Triggers

### 5.1 Triggers 아키텍처

Tekton Triggers는 외부 이벤트(Git push, PR, 태그 생성 등)를 수신하여 자동으로 PipelineRun을 생성합니다.

![GitHub Webhook 이벤트가 EventListener에 도착해 GitHub Interceptor의 Secret 검증과 CEL Interceptor 필터를 거친 뒤 TriggerBinding이 파라미터를 추출하고 TriggerTemplate이 새 PipelineRun을 생성하는 Tekton Triggers 구조를 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-3.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-3.html)

### 5.2 EventListener

EventListener는 Webhook을 수신하는 HTTP 서버를 Kubernetes에 배포합니다.

```yaml
# eventlistener.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-listener
  namespace: tekton-pipelines
spec:
  serviceAccountName: tekton-triggers-sa
  
  triggers:
    # Push 이벤트 트리거
    - name: github-push-trigger
      interceptors:
        # GitHub Webhook Secret 검증
        - ref:
            name: "github"
          params:
            - name: "secretRef"
              value:
                secretName: github-webhook-secret
                secretKey: token
            - name: "eventTypes"
              value: ["push"]
        # CEL 필터: main 브랜치 푸시만 처리
        - ref:
            name: "cel"
          params:
            - name: "filter"
              value: "body.ref == 'refs/heads/main'"
            - name: "overlays"
              value:
                - key: truncated_sha
                  expression: "body.after.truncate(7)"
                - key: branch
                  expression: "body.ref.split('/')[2]"
      bindings:
        - ref: github-push-binding
      template:
        ref: github-push-template

    # Pull Request 이벤트 트리거
    - name: github-pr-trigger
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
                body.pull_request.base.ref == 'main'
      bindings:
        - ref: github-pr-binding
      template:
        ref: github-pr-template

  resources:
    kubernetesResource:
      spec:
        template:
          spec:
            serviceAccountName: tekton-triggers-sa
            containers: []
          metadata:
            labels:
              app: tekton-triggers
      replicas: 2  # HA 구성
```

### 5.3 TriggerBinding

TriggerBinding은 Webhook 이벤트의 데이터를 Pipeline 파라미터로 매핑합니다.

```yaml
# triggerbinding-push.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-push-binding
  namespace: tekton-pipelines
spec:
  params:
    - name: git-url
      value: $(body.repository.clone_url)
    - name: git-revision
      value: $(body.after)
    - name: git-branch
      value: $(extensions.branch)
    - name: short-sha
      value: $(extensions.truncated_sha)
    - name: repo-name
      value: $(body.repository.name)
    - name: commit-message
      value: $(body.head_commit.message)
    - name: author
      value: $(body.head_commit.author.name)

---
# triggerbinding-pr.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerBinding
metadata:
  name: github-pr-binding
  namespace: tekton-pipelines
spec:
  params:
    - name: git-url
      value: $(body.pull_request.head.repo.clone_url)
    - name: git-revision
      value: $(body.pull_request.head.sha)
    - name: git-branch
      value: $(body.pull_request.head.ref)
    - name: pr-number
      value: $(body.pull_request.number)
    - name: pr-title
      value: $(body.pull_request.title)
```

### 5.4 TriggerTemplate

TriggerTemplate은 바인딩된 파라미터를 사용하여 PipelineRun을 생성합니다.

```yaml
# triggertemplate-push.yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: github-push-template
  namespace: tekton-pipelines
spec:
  params:
    - name: git-url
    - name: git-revision
    - name: git-branch
    - name: short-sha
    - name: repo-name
    - name: commit-message
    - name: author

  resourcetemplates:
    - apiVersion: tekton.dev/v1
      kind: PipelineRun
      metadata:
        generateName: $(tt.params.repo-name)-$(tt.params.short-sha)-
        namespace: tekton-pipelines
        labels:
          tekton.dev/trigger: github-push
          app.kubernetes.io/managed-by: tekton-triggers
          app: $(tt.params.repo-name)
        annotations:
          tekton.dev/git-commit: $(tt.params.git-revision)
          tekton.dev/git-branch: $(tt.params.git-branch)
          tekton.dev/commit-message: $(tt.params.commit-message)
          tekton.dev/author: $(tt.params.author)
      spec:
        pipelineRef:
          name: ci-cd-pipeline
        params:
          - name: git-url
            value: $(tt.params.git-url)
          - name: git-revision
            value: $(tt.params.git-revision)
          - name: image-registry
            value: "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/$(tt.params.repo-name)"
          - name: image-tag
            value: "$(tt.params.short-sha)"
          - name: deployment-name
            value: $(tt.params.repo-name)
          - name: namespace
            value: "production"
        workspaces:
          - name: shared-workspace
            volumeClaimTemplate:
              spec:
                accessModes: ["ReadWriteOnce"]
                resources:
                  requests:
                    storage: 5Gi
                storageClassName: gp3
          - name: docker-credentials
            secret:
              secretName: ecr-credentials
          - name: git-credentials
            secret:
              secretName: git-credentials
        taskRunTemplate:
          serviceAccountName: tekton-pipeline-sa
        timeouts:
          pipeline: "1h"
```

### 5.5 Webhook 설정 및 Ingress 구성

```bash
# EventListener Service 확인
kubectl get svc -n tekton-pipelines -l app.kubernetes.io/managed-by=EventListener

# Ingress로 EventListener 노출
```

```yaml
# eventlistener-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tekton-triggers-ingress
  namespace: tekton-pipelines
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:123456789012:certificate/xxxxx"
spec:
  rules:
    - host: tekton-webhooks.example.com
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

```bash
# GitHub Webhook 등록
# Settings → Webhooks → Add webhook
# Payload URL: https://tekton-webhooks.example.com
# Content type: application/json
# Secret: (github-webhook-secret에 저장한 값)
# Events: Push, Pull Request

# Webhook Secret 생성
kubectl create secret generic github-webhook-secret \
  -n tekton-pipelines \
  --from-literal=token=$(openssl rand -hex 20)
```

### 5.6 Interceptors 활용

Interceptors는 이벤트를 수신 후 필터링, 변환, 검증하는 역할을 합니다.

| Interceptor | 설명 | 사용 사례 |
|-------------|------|----------|
| **GitHub** | GitHub Webhook Secret 검증, 이벤트 타입 필터 | GitHub 리포지토리 연동 |
| **GitLab** | GitLab Webhook Token 검증 | GitLab 리포지토리 연동 |
| **Bitbucket** | Bitbucket Webhook 검증 | Bitbucket 연동 |
| **CEL** | Common Expression Language 기반 필터/변환 | 복잡한 조건부 트리거 |

**CEL Interceptor 고급 활용:**

```yaml
# CEL을 사용한 고급 필터링
interceptors:
  - ref:
      name: "cel"
    params:
      # 특정 파일 변경 시에만 트리거
      - name: "filter"
        value: >
          body.commits.exists(c, c.modified.exists(m, m.startsWith('src/'))) ||
          body.commits.exists(c, c.added.exists(a, a.startsWith('src/')))
      # 이벤트 데이터 변환
      - name: "overlays"
        value:
          - key: image-tag
            expression: "body.after.truncate(7) + '-' + string(body.repository.pushed_at)"
          - key: is-main
            expression: "body.ref == 'refs/heads/main'"
```

---

## 6. Tekton Chains (Supply Chain Security)

### 6.1 개요

Tekton Chains는 TaskRun이 완료된 후 자동으로 아티팩트(이미지, 바이너리 등)에 서명하고 공급망 증명(attestation)을 생성합니다. 이를 통해 소프트웨어 공급망의 무결성을 보장합니다.

![이미지 빌드 TaskRun의 완료를 Tekton Chains가 감지해 Cosign 서명과 SLSA Provenance/in-toto Attestation을 생성하고 Rekor 투명성 로그에 기록한 뒤, 배포 시점에 cosign verify와 Kyverno 정책을 거쳐 Admission Control이 허용 여부를 결정하는 흐름을 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-4.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-4.html)

### 6.2 Chains 구성

```bash
# Tekton Chains 설정 (ConfigMap)
kubectl patch configmap chains-config \
  -n tekton-chains \
  --type merge \
  -p '{
    "data": {
      "artifacts.taskrun.format": "slsa/v1",
      "artifacts.taskrun.storage": "oci",
      "artifacts.oci.storage": "oci",
      "artifacts.oci.format": "simplesigning",
      "transparency.enabled": "true",
      "transparency.url": "https://rekor.sigstore.dev",
      "signers.x509.fulcio.enabled": "true",
      "signers.x509.fulcio.address": "https://fulcio.sigstore.dev"
    }
  }'
```

**완전한 Chains ConfigMap:**

```yaml
# chains-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chains-config
  namespace: tekton-chains
data:
  # 아티팩트 형식 설정
  artifacts.taskrun.format: "slsa/v1"        # SLSA v1 형식
  artifacts.taskrun.storage: "oci"           # OCI 레지스트리에 저장
  artifacts.taskrun.signer: "x509"           # X.509 인증서로 서명
  
  artifacts.oci.storage: "oci"               # OCI 이미지 서명 저장소
  artifacts.oci.format: "simplesigning"      # 간단한 서명 형식
  artifacts.oci.signer: "x509"
  
  artifacts.pipelinerun.format: "slsa/v1"    # PipelineRun 레벨 provenance
  artifacts.pipelinerun.storage: "oci"
  artifacts.pipelinerun.signer: "x509"
  
  # 투명성 로그 설정
  transparency.enabled: "true"
  transparency.url: "https://rekor.sigstore.dev"
  
  # Fulcio (Keyless Signing) 설정
  signers.x509.fulcio.enabled: "true"
  signers.x509.fulcio.address: "https://fulcio.sigstore.dev"
  signers.x509.fulcio.issuer: "https://token.actions.githubusercontent.com"
  signers.x509.identity.token.file: "/var/run/sigstore/cosign/oidc-token"
  
  # 빌더 ID (SLSA Provenance에 포함)
  builddefinition.buildtype: "https://tekton.dev/chains/v2/slsa"
```

### 6.3 Cosign을 사용한 서명 키 설정

```bash
# Cosign 키 쌍 생성
cosign generate-key-pair k8s://tekton-chains/signing-secrets

# 또는 KMS를 사용한 키 관리 (프로덕션 권장)
cosign generate-key-pair --kms awskms:///arn:aws:kms:ap-northeast-2:123456789012:key/xxxxx

# KMS 기반 Chains 설정
kubectl patch configmap chains-config \
  -n tekton-chains \
  --type merge \
  -p '{
    "data": {
      "signers.x509.fulcio.enabled": "false",
      "artifacts.taskrun.signer": "kms",
      "artifacts.oci.signer": "kms",
      "signers.kms.kmsref": "awskms:///arn:aws:kms:ap-northeast-2:123456789012:key/xxxxx"
    }
  }'
```

### 6.4 서명 검증

빌드된 이미지의 서명을 검증하여 공급망 무결성을 확인합니다.

```bash
# Cosign으로 이미지 서명 검증
cosign verify \
  --key k8s://tekton-chains/signing-secrets \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.2.3

# SLSA Provenance 확인
cosign verify-attestation \
  --key k8s://tekton-chains/signing-secrets \
  --type slsaprovenance \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.2.3

# Provenance 내용 확인 (jq로 파싱)
cosign verify-attestation \
  --key k8s://tekton-chains/signing-secrets \
  --type slsaprovenance \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:v1.2.3 \
  | jq -r '.payload' | base64 -d | jq .
```

### 6.5 Kyverno를 사용한 이미지 서명 정책 적용

```yaml
# kyverno-verify-image.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-tekton-signed-images
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: verify-image-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - production
                - staging
      verifyImages:
        - imageReferences:
            - "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
          attestations:
            - type: https://slsa.dev/provenance/v1
              conditions:
                - all:
                    - key: "{{ buildDefinition.buildType }}"
                      operator: Equals
                      value: "https://tekton.dev/chains/v2/slsa"
```

---

## 7. ArgoCD + Tekton 통합

### 7.1 CI/CD 분리 아키텍처

Tekton으로 CI(빌드/테스트/이미지 Push)를, ArgoCD로 CD(GitOps 배포)를 담당하는 분리 아키텍처는 프로덕션 환경에서 가장 권장되는 패턴입니다.

![소스 저장소 push가 Tekton CI를 트리거해 클론·테스트·이미지 빌드·ECR Push·매니페스트 업데이트를 거치고, GitOps 저장소에 커밋된 변경을 ArgoCD가 감지해 ECR 이미지를 pull하여 클러스터에 배포하는 CI/CD 분리 아키텍처를 보여준다.](../.gitbook/assets/ko-ops-14-tekton-pipelines-5.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-14-tekton-pipelines-5.html)

### 7.2 매니페스트 업데이트 Task

CI 파이프라인의 마지막 단계에서 GitOps 리포지토리의 이미지 태그를 업데이트합니다.

```yaml
# task-update-manifest.yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: update-gitops-manifest
  namespace: tekton-pipelines
spec:
  description: >
    GitOps 리포지토리의 Kubernetes 매니페스트에서 이미지 태그를 업데이트하고 
    커밋/푸시하여 ArgoCD 동기화를 트리거합니다.

  params:
    - name: GITOPS_REPO_URL
      description: "GitOps 리포지토리 URL"
      type: string
    - name: GITOPS_REPO_BRANCH
      description: "대상 브랜치"
      type: string
      default: "main"
    - name: IMAGE_NAME
      description: "업데이트할 이미지 이름 (전체 경로)"
      type: string
    - name: IMAGE_TAG
      description: "새 이미지 태그"
      type: string
    - name: MANIFEST_PATH
      description: "매니페스트 파일 경로 (예: overlays/production/kustomization.yaml)"
      type: string
    - name: APP_NAME
      description: "애플리케이션 이름"
      type: string
    - name: COMMIT_AUTHOR
      description: "커밋 작성자"
      type: string
      default: "Tekton CI"

  workspaces:
    - name: gitops-source
      description: "GitOps 리포지토리 workspace"
    - name: git-credentials
      description: "Git 인증 정보"

  results:
    - name: COMMIT_SHA
      description: "매니페스트 업데이트 커밋 SHA"

  steps:
    - name: clone-gitops-repo
      image: alpine/git:2.43.0
      script: |
        #!/bin/sh
        set -eu
        
        cd $(workspaces.gitops-source.path)
        
        # Git 자격 증명 설정
        git config --global credential.helper store
        cp $(workspaces.git-credentials.path)/.git-credentials ~/.git-credentials 2>/dev/null || true
        
        # GitOps 리포지토리 클론
        git clone --branch $(params.GITOPS_REPO_BRANCH) \
          $(params.GITOPS_REPO_URL) gitops-repo
        
        echo "[INFO] GitOps 리포지토리 클론 완료"

    - name: update-image-tag
      image: mikefarah/yq:4.40.5
      workingDir: $(workspaces.gitops-source.path)/gitops-repo
      script: |
        #!/bin/sh
        set -eu
        
        MANIFEST="$(params.MANIFEST_PATH)"
        echo "[INFO] 매니페스트 업데이트: $MANIFEST"
        echo "[INFO] 이미지: $(params.IMAGE_NAME):$(params.IMAGE_TAG)"
        
        # Kustomization 파일인 경우
        if echo "$MANIFEST" | grep -q "kustomization"; then
          yq eval -i '
            (.images[] | select(.name == "'"$(params.IMAGE_NAME)"'")).newTag = "'"$(params.IMAGE_TAG)"'"
          ' "$MANIFEST"
        fi
        
        # Helm values 파일인 경우
        if echo "$MANIFEST" | grep -q "values"; then
          yq eval -i '
            .image.tag = "'"$(params.IMAGE_TAG)"'"
          ' "$MANIFEST"
        fi
        
        echo "[INFO] 변경 사항:"
        git diff

    - name: commit-and-push
      image: alpine/git:2.43.0
      workingDir: $(workspaces.gitops-source.path)/gitops-repo
      script: |
        #!/bin/sh
        set -eu
        
        git config user.email "tekton-ci@example.com"
        git config user.name "$(params.COMMIT_AUTHOR)"
        
        # 변경 사항이 있는 경우에만 커밋
        if git diff --quiet; then
          echo "[WARN] 변경 사항 없음. 이미 최신 버전입니다."
          COMMIT_SHA=$(git rev-parse HEAD)
        else
          git add -A
          git commit -m "chore($(params.APP_NAME)): update image to $(params.IMAGE_TAG)

        Automated by Tekton CI Pipeline
        Image: $(params.IMAGE_NAME):$(params.IMAGE_TAG)"
          
          git push origin $(params.GITOPS_REPO_BRANCH)
          COMMIT_SHA=$(git rev-parse HEAD)
          echo "[INFO] 매니페스트 업데이트 커밋 완료: $COMMIT_SHA"
        fi
        
        echo -n "$COMMIT_SHA" | tee $(results.COMMIT_SHA.path)
```

### 7.3 ArgoCD + Tekton 통합 Pipeline

```yaml
# pipeline-ci-with-gitops.yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: ci-gitops-pipeline
  namespace: tekton-pipelines
spec:
  description: >
    Tekton CI + ArgoCD CD 통합 파이프라인:
    소스 빌드 → 이미지 Push → GitOps 매니페스트 업데이트 → ArgoCD 자동 동기화

  params:
    - name: git-url
      type: string
    - name: git-revision
      type: string
      default: "main"
    - name: image-registry
      type: string
    - name: image-tag
      type: string
    - name: app-name
      type: string
    - name: gitops-repo-url
      type: string
    - name: manifest-path
      type: string
      default: "overlays/production/kustomization.yaml"

  workspaces:
    - name: shared-workspace
    - name: gitops-workspace
    - name: docker-credentials
    - name: git-credentials

  tasks:
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: $(params.git-url)
        - name: revision
          value: $(params.git-revision)
      workspaces:
        - name: output
          workspace: shared-workspace

    - name: test
      runAfter: ["clone"]
      taskRef:
        name: run-tests
      workspaces:
        - name: source
          workspace: shared-workspace

    - name: build
      runAfter: ["test"]
      taskRef:
        name: kaniko-build
      params:
        - name: IMAGE
          value: $(params.image-registry)
        - name: TAG
          value: $(params.image-tag)
      workspaces:
        - name: source
          workspace: shared-workspace
        - name: dockerconfig
          workspace: docker-credentials

    # GitOps 리포지토리 매니페스트 업데이트
    - name: update-manifest
      runAfter: ["build"]
      taskRef:
        name: update-gitops-manifest
      params:
        - name: GITOPS_REPO_URL
          value: $(params.gitops-repo-url)
        - name: IMAGE_NAME
          value: $(params.image-registry)
        - name: IMAGE_TAG
          value: $(params.image-tag)
        - name: MANIFEST_PATH
          value: $(params.manifest-path)
        - name: APP_NAME
          value: $(params.app-name)
      workspaces:
        - name: gitops-source
          workspace: gitops-workspace
        - name: git-credentials
          workspace: git-credentials

  finally:
    - name: notify
      taskRef:
        name: send-slack-notification
      params:
        - name: pipeline-name
          value: $(context.pipelineRun.name)
        - name: status
          value: $(tasks.status)
        - name: image
          value: "$(params.image-registry):$(params.image-tag)"
```

### 7.4 ArgoCD Application 구성

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
  annotations:
    # ArgoCD Notifications로 Slack 알림
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.slack: deployments
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/app-manifests.git
    targetRevision: main
    path: overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 3
      backoff:
        duration: "10s"
        factor: 2
        maxDuration: "3m"
```

---

## 8. 프로덕션 운영

### 8.1 PipelineRun 정리 정책

프로덕션 환경에서는 완료된 PipelineRun이 누적되어 etcd 스토리지를 소비합니다. 자동 정리 정책을 구성해야 합니다.

```bash
# Tekton 기본 정리 설정 (ConfigMap)
kubectl patch configmap feature-flags \
  -n tekton-pipelines \
  --type merge \
  -p '{
    "data": {
      "keep-pod-on-cancel": "false",
      "running-in-environment-with-injected-sidecars": "true"
    }
  }'
```

**CronJob 기반 자동 정리:**

```yaml
# pipelinerun-cleanup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: tekton-cleanup
  namespace: tekton-pipelines
spec:
  schedule: "0 2 * * *"  # 매일 오전 2시
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: tekton-cleanup-sa
          containers:
            - name: cleanup
              image: bitnami/kubectl:1.29
              command:
                - /bin/bash
                - -c
                - |
                  echo "[INFO] Tekton PipelineRun 정리 시작"
                  
                  # 7일 이상 된 완료된 PipelineRun 삭제
                  CUTOFF=$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%SZ)
                  
                  kubectl get pipelinerun -n tekton-pipelines \
                    -o jsonpath='{range .items[?(@.status.conditions[0].status=="True")]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' \
                    | while read NAME TIMESTAMP; do
                      if [ "$TIMESTAMP" \< "$CUTOFF" ]; then
                        echo "[INFO] 삭제: $NAME (생성일: $TIMESTAMP)"
                        kubectl delete pipelinerun "$NAME" -n tekton-pipelines
                      fi
                    done
                  
                  # 실패한 PipelineRun도 14일 이후 삭제
                  CUTOFF_FAILED=$(date -d '14 days ago' -u +%Y-%m-%dT%H:%M:%SZ)
                  
                  kubectl get pipelinerun -n tekton-pipelines \
                    -o jsonpath='{range .items[?(@.status.conditions[0].status=="False")]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' \
                    | while read NAME TIMESTAMP; do
                      if [ "$TIMESTAMP" \< "$CUTOFF_FAILED" ]; then
                        echo "[INFO] 삭제 (실패): $NAME (생성일: $TIMESTAMP)"
                        kubectl delete pipelinerun "$NAME" -n tekton-pipelines
                      fi
                    done
                  
                  echo "[INFO] 정리 완료"
          restartPolicy: OnFailure

---
# cleanup ServiceAccount 및 RBAC
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tekton-cleanup-sa
  namespace: tekton-pipelines

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tekton-cleanup-role
  namespace: tekton-pipelines
rules:
  - apiGroups: ["tekton.dev"]
    resources: ["pipelineruns", "taskruns"]
    verbs: ["get", "list", "delete"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tekton-cleanup-binding
  namespace: tekton-pipelines
subjects:
  - kind: ServiceAccount
    name: tekton-cleanup-sa
roleRef:
  kind: Role
  name: tekton-cleanup-role
  apiGroup: rbac.authorization.k8s.io
```

### 8.2 리소스 관리

TaskRun Pod의 리소스를 효율적으로 관리하여 클러스터 리소스를 최적화합니다.

```yaml
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tekton-resource-quota
  namespace: tekton-pipelines
spec:
  hard:
    # 동시 실행 가능한 Pod 수 제한
    pods: "20"
    # CPU/메모리 총량 제한
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    # PVC 수 제한
    persistentvolumeclaims: "30"

---
# limit-range.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: tekton-limit-range
  namespace: tekton-pipelines
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "256Mi"
      max:
        cpu: "4"
        memory: "8Gi"
    - type: PersistentVolumeClaim
      max:
        storage: "20Gi"
```

### 8.3 모니터링 (Prometheus 메트릭)

Tekton은 Prometheus 메트릭을 기본으로 노출합니다.

```yaml
# tekton-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: tekton-pipelines
  namespace: tekton-pipelines
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app.kubernetes.io/component: controller
      app.kubernetes.io/part-of: tekton-pipelines
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

**주요 Tekton 메트릭:**

| 메트릭 | 설명 | 사용 사례 |
|--------|------|----------|
| `tekton_pipelines_controller_pipelinerun_duration_seconds` | PipelineRun 실행 시간 | 파이프라인 성능 모니터링 |
| `tekton_pipelines_controller_pipelinerun_count` | PipelineRun 실행 횟수 | 사용량 추적 |
| `tekton_pipelines_controller_taskrun_duration_seconds` | TaskRun 실행 시간 | Task 성능 분석 |
| `tekton_pipelines_controller_running_pipelineruns_count` | 현재 실행 중인 PipelineRun 수 | 동시성 모니터링 |
| `tekton_pipelines_controller_client_latency_seconds` | API 서버 요청 지연 시간 | 컨트롤러 건강 상태 |

**Grafana 대시보드 PromQL 예제:**

```promql
# 파이프라인 평균 실행 시간 (최근 1시간)
avg(rate(tekton_pipelines_controller_pipelinerun_duration_seconds_sum[1h])
  / rate(tekton_pipelines_controller_pipelinerun_duration_seconds_count[1h]))

# 파이프라인 성공률
sum(tekton_pipelines_controller_pipelinerun_count{status="success"})
  / sum(tekton_pipelines_controller_pipelinerun_count) * 100

# 현재 실행 중인 파이프라인 수
tekton_pipelines_controller_running_pipelineruns_count
```

### 8.4 로그 관리

```bash
# PipelineRun 로그 확인 (Tekton CLI)
tkn pipelinerun logs ci-cd-pipeline-run-xyz -n tekton-pipelines

# 특정 Task의 로그만 확인
tkn pipelinerun logs ci-cd-pipeline-run-xyz -n tekton-pipelines --task build

# 실시간 로그 스트리밍
tkn pipelinerun logs ci-cd-pipeline-run-xyz -n tekton-pipelines -f

# 실패한 최근 PipelineRun 로그 확인
tkn pipelinerun logs --last -n tekton-pipelines
```

**구조화된 로그 수집 (Loki 연동):**

```yaml
# 로그 수집을 위한 Pod 라벨 활용
# Promtail/Alloy 설정에서 tekton-pipelines 네임스페이스의 Pod 로그를 수집합니다
# Loki LogQL 쿼리 예제:

# 특정 PipelineRun의 모든 로그
# {namespace="tekton-pipelines"} |= "ci-cd-pipeline-run-xyz"

# 빌드 실패 로그 검색
# {namespace="tekton-pipelines", container=~"step-.*"} |= "ERROR" or |= "FATAL"
```

### 8.5 문제 해결

**일반적인 문제와 해결 방법:**

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| TaskRun Pod이 `Pending` 상태 | 리소스 부족 또는 PVC 바인딩 대기 | `kubectl describe pod`으로 이벤트 확인, ResourceQuota/LimitRange 조정 |
| `ImagePullBackOff` | 잘못된 이미지 경로 또는 인증 실패 | ECR 로그인 확인, IRSA 권한 확인 |
| Step `Timeout` | 실행 시간 초과 | `timeouts` 설정 조정, 병목 Step 최적화 |
| `Resolution Failed` | Task/Pipeline 참조 오류 | `tkn task list`로 Task 존재 확인 |
| Workspace 마운트 실패 | PVC 접근 모드 불일치 | `ReadWriteOnce` → `ReadWriteMany` 변경 또는 Affinity Assistant 확인 |
| Trigger 미동작 | Webhook 전달 실패 또는 Interceptor 오류 | EventListener Pod 로그 확인, Interceptor 설정 검증 |

```bash
# 문제 해결 명령어 모음

# PipelineRun 상태 상세 확인
tkn pipelinerun describe ci-cd-pipeline-run-xyz -n tekton-pipelines

# TaskRun Pod 이벤트 확인
kubectl describe pod -l tekton.dev/pipelineRun=ci-cd-pipeline-run-xyz -n tekton-pipelines

# 컨트롤러 로그 확인
kubectl logs -l app=tekton-pipelines-controller -n tekton-pipelines --tail=100

# Webhook 로그 확인
kubectl logs -l app=tekton-pipelines-webhook -n tekton-pipelines --tail=100

# EventListener 로그 확인 (Triggers 문제)
kubectl logs -l app.kubernetes.io/managed-by=EventListener -n tekton-pipelines --tail=100

# Chains 로그 확인 (서명 문제)
kubectl logs -l app=tekton-chains-controller -n tekton-chains --tail=100

# CRD 상태 확인
kubectl get pipelinerun,taskrun -n tekton-pipelines --sort-by=.metadata.creationTimestamp
```

---

## 9. 모범 사례

### 9.1 Task 재사용 패턴

**Tekton Bundle을 사용한 Task 버전 관리:**

Tekton Bundle은 Task/Pipeline을 OCI 이미지로 패키징하여 ECR에 저장하고, 버전별로 관리할 수 있게 합니다.

```bash
# Task를 OCI Bundle로 패키징
tkn bundle push \
  123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/tekton-tasks/kaniko-build:v1.0 \
  -f task-kaniko-build.yaml

# Pipeline에서 Bundle Task 참조
```

```yaml
# Bundle Task 참조 예제
tasks:
  - name: build
    taskRef:
      resolver: bundles
      params:
        - name: bundle
          value: "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/tekton-tasks/kaniko-build:v1.0"
        - name: name
          value: kaniko-build
        - name: kind
          value: Task
```

**공통 StepAction 패턴 (Tekton v0.62+):**

```yaml
# stepaction-aws-ecr-login.yaml
apiVersion: tekton.dev/v1beta1
kind: StepAction
metadata:
  name: aws-ecr-login
  namespace: tekton-pipelines
spec:
  params:
    - name: REGION
      type: string
      default: "ap-northeast-2"
    - name: REGISTRY
      type: string
  results:
    - name: DOCKER_CONFIG_PATH
      description: "생성된 Docker config 경로"
  image: amazon/aws-cli:2.15.0
  script: |
    #!/bin/bash
    set -eu
    TOKEN=$(aws ecr get-login-password --region $(params.REGION))
    mkdir -p /home/user/.docker
    cat > /home/user/.docker/config.json <<EOCFG
    {"auths": {"$(params.REGISTRY)": {"auth": "$(echo -n "AWS:${TOKEN}" | base64)"}}}
    EOCFG
    echo -n "/home/user/.docker" > $(step.results.DOCKER_CONFIG_PATH.path)
```

### 9.2 보안 모범 사례

**Secret 관리:**

```yaml
# External Secrets Operator를 사용한 AWS Secrets Manager 연동
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: tekton-git-credentials
  namespace: tekton-pipelines
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: git-credentials
    template:
      type: kubernetes.io/basic-auth
      data:
        username: "{{ .username }}"
        password: "{{ .token }}"
  data:
    - secretKey: username
      remoteRef:
        key: tekton/git-credentials
        property: username
    - secretKey: token
      remoteRef:
        key: tekton/git-credentials
        property: token
```

**최소 권한 원칙:**

```yaml
# 최소 권한 ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tekton-pipeline-sa
  namespace: tekton-pipelines
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/tekton-pipeline-role

---
# 필요한 권한만 부여
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tekton-pipeline-role
  namespace: tekton-pipelines
rules:
  # PipelineRun/TaskRun 생성 권한
  - apiGroups: ["tekton.dev"]
    resources: ["pipelineruns", "taskruns"]
    verbs: ["create", "get", "list", "watch"]
  # Pod 로그 조회
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list"]
  # Secret 읽기 (빌드 시 필요한 인증 정보)
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
    resourceNames: ["ecr-credentials", "git-credentials", "slack-webhook"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tekton-pipeline-binding
  namespace: tekton-pipelines
subjects:
  - kind: ServiceAccount
    name: tekton-pipeline-sa
roleRef:
  kind: Role
  name: tekton-pipeline-role
  apiGroup: rbac.authorization.k8s.io
```

**네트워크 정책:**

```yaml
# tekton-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tekton-pipeline-policy
  namespace: tekton-pipelines
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/managed-by: tekton-pipelines
  policyTypes:
    - Ingress
    - Egress
  egress:
    # DNS 허용
    - to: []
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # ECR 접근 허용
    - to: []
      ports:
        - protocol: TCP
          port: 443
    # Git SSH 접근 허용
    - to: []
      ports:
        - protocol: TCP
          port: 22
  ingress: []  # 인바운드 트래픽 차단
```

### 9.3 성능 최적화

| 최적화 항목 | 방법 | 효과 |
|-------------|------|------|
| **Workspace 캐시 활용** | PVC에 빌드 캐시(Maven, npm, Go modules) 저장 | 빌드 시간 40-60% 단축 |
| **Affinity Assistant 비활성화** | `disable-affinity-assistant: "true"` | Pod 스케줄링 유연성 향상 |
| **병렬 Task 실행** | 독립적인 Task에 `runAfter` 미지정 | 파이프라인 총 실행 시간 단축 |
| **이미지 캐시** | Kaniko `--cache=true --cache-repo` 옵션 | 이미지 빌드 시간 단축 |
| **Step 이미지 사전 Pull** | DaemonSet으로 자주 사용하는 이미지 사전 배포 | Step 시작 시간 단축 |
| **결과 크기 최적화** | 큰 데이터는 Workspace, 작은 데이터만 Result | 메모리 사용량 감소 |

**빌드 캐시 Workspace 구성:**

```yaml
# 빌드 캐시를 위한 영구 PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: build-cache
  namespace: tekton-pipelines
spec:
  accessModes:
    - ReadWriteMany  # 여러 TaskRun이 동시 접근
  resources:
    requests:
      storage: 50Gi
  storageClassName: efs-sc  # EFS를 사용하여 ReadWriteMany 지원
```

```yaml
# Pipeline에서 캐시 Workspace 참조
workspaces:
  - name: build-cache
    persistentVolumeClaim:
      claimName: build-cache
```

### 9.4 비용 최적화

- **PipelineRun 정리 자동화**: 완료된 PipelineRun을 주기적으로 삭제하여 etcd 스토리지와 API 서버 부하 감소
- **Workspace PVC 정리**: VolumeClaimTemplate으로 생성된 PVC를 자동 삭제하도록 설정
- **Spot Instance 활용**: 빌드 워크로드를 Spot 노드에 스케줄링하여 비용 절감
- **리소스 요청 최적화**: Step별 실제 사용량 기반으로 리소스 요청 조정
- **동시성 제어**: ResourceQuota로 동시 실행 파이프라인 수를 제한하여 예측 가능한 비용 유지

```yaml
# Spot 노드에서 빌드 실행
taskRunTemplate:
  podTemplate:
    tolerations:
      - key: "kubernetes.io/spot"
        operator: "Exists"
        effect: "NoSchedule"
    nodeSelector:
      node.kubernetes.io/capacity-type: spot
```

---

## 10. 참고 문서

### 공식 문서

- [Tekton 공식 문서](https://tekton.dev/docs/)
- [Tekton Pipelines GitHub](https://github.com/tektoncd/pipeline)
- [Tekton Triggers GitHub](https://github.com/tektoncd/triggers)
- [Tekton Chains GitHub](https://github.com/tektoncd/chains)
- [Tekton Hub (커뮤니티 Task)](https://hub.tekton.dev/)
- [SLSA 프레임워크](https://slsa.dev/)
- [Sigstore/Cosign 문서](https://docs.sigstore.dev/)

### 관련 내부 문서

| 문서 | 설명 |
|------|------|
| [CI 파이프라인](./03-ci-pipelines.md) | ECR 빌드, GitLab Runner, GitHub ARC 기반 CI |
| [ArgoCD 설치 및 구성](../gitops/argocd/01-installation.md) | ArgoCD 설치, HA 구성, EKS 통합 |
| [컨테이너 이미지 보안](../security/07-image-security.md) | Trivy 스캐닝, Cosign 서명, 공급망 보안 |
| [ArgoCD 멀티클러스터](./04-gitops-multi-cluster.md) | Hub-spoke 패턴, ApplicationSet |
| [GitOps 자동화](./05-gitops-automation.md) | Atlantis, FluxCD, Terraform Cloud |

---

< [이전: FinOps 비용 가시성 플랫폼](./13-finops-cost-platform.md) | [목차](./README.md) | [다음: 없음] >
