# GitOps 자동화: Atlantis, FluxCD, AIOps

> **지원 버전**: Atlantis v0.28+, FluxCD v2.3+, Terraform Cloud
> **마지막 업데이트**: 2025년 6월

< [이전: ArgoCD 멀티클러스터](./04-gitops-multi-cluster.md) | [목차](./README.md) | [다음: 스케일링 전략](./06-scaling-strategies.md) >

---

## 개요

GitOps 자동화는 인프라와 애플리케이션 배포를 Git 기반 워크플로우로 통합하여 일관성, 감사 가능성, 협업 효율성을 극대화합니다. 이 문서에서는 Terraform 인프라 자동화를 위한 Atlantis와 Terraform Cloud, Kubernetes 배포를 위한 FluxCD, 그리고 AI/ML을 활용한 AIOps 전략을 다룹니다.

### 학습 목표

- Atlantis를 EKS에 배포하고 PR 기반 Terraform 워크플로우 구성
- Terraform Cloud의 워크스페이스 기반 인프라 관리 이해
- FluxCD의 GitOps 패턴과 이미지 자동화 구현
- AIOps를 통한 운영 자동화 전략 수립

---

## 1. Atlantis on EKS

Atlantis는 Terraform Pull Request Automation 도구로, PR을 통해 인프라 변경사항을 계획(plan)하고 적용(apply)하는 워크플로우를 자동화합니다.

### 1.1 Atlantis 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub/GitLab                                │
│  ┌─────────────┐    Webhook     ┌─────────────────────────────────┐ │
│  │  PR Created │ ──────────────▶│          Atlantis               │ │
│  │  PR Updated │                │  ┌─────────────────────────────┐│ │
│  │  PR Comment │                │  │   terraform plan/apply      ││ │
│  └─────────────┘                │  │   ┌───────────────────────┐ ││ │
│        ▲                        │  │   │  AWS Provider         │ ││ │
│        │ Plan/Apply             │  │   │  (Pod Identity)       │ ││ │
│        │ Output                 │  │   └───────────────────────┘ ││ │
│        │                        │  └─────────────────────────────┘│ │
│        └────────────────────────┤                                 │ │
│                                 │  Locks (DynamoDB/BoltDB)        │ │
│                                 └─────────────────────────────────┘ │
│                                            │                        │
│                                            ▼                        │
│                                 ┌─────────────────────────────────┐ │
│                                 │         AWS Resources           │ │
│                                 │   VPC, EKS, RDS, S3, etc.       │ │
│                                 └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**핵심 구성 요소:**

| 구성 요소 | 역할 |
|-----------|------|
| Webhook Receiver | GitHub/GitLab PR 이벤트 수신 |
| Plan/Apply Engine | Terraform 명령 실행 |
| Locking System | 동시 PR 충돌 방지 |
| State Management | Remote State 연동 (S3, Terraform Cloud) |

### 1.2 Atlantis Helm 배포

**values.yaml:**

```yaml
# atlantis-values.yaml
replicaCount: 1

image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.28.0
  pullPolicy: IfNotPresent

# GitHub 연동 설정
github:
  user: "atlantis-bot"
  token: ""  # Secret으로 주입
  secret: ""  # Webhook Secret

# GitLab 연동 시
# gitlab:
#   user: "atlantis-bot"
#   token: ""
#   secret: ""
#   hostname: "gitlab.company.com"

# Atlantis 서버 설정
atlantisUrl: "https://atlantis.example.com"

# Org/Repo 허용 목록
orgAllowlist: "github.com/my-org/*"
# 또는 특정 저장소만
# repoAllowlist: "github.com/my-org/infra-*"

# 기본 Terraform 버전
defaultTFVersion: "1.9.0"

# Server-side repo config 사용
repoConfig: |
  ---
  repos:
  - id: github.com/my-org/eks-infra
    branch: main
    autoplan:
      when_modified: ["*.tf", "*.tfvars", "terragrunt.hcl"]
      enabled: true
    apply_requirements: [approved, mergeable]
    allowed_overrides: [workflow, apply_requirements]
    allow_custom_workflows: true

  workflows:
    network:
      plan:
        steps:
          - init:
              extra_args: ["-backend-config=backend.hcl"]
          - plan:
              extra_args: ["-var-file=terraform.tfvars"]
      apply:
        steps:
          - apply:
              extra_args: ["-var-file=terraform.tfvars"]

    cluster:
      plan:
        steps:
          - init
          - plan:
              extra_args: ["-var-file=terraform.tfvars", "-parallelism=30"]
      apply:
        steps:
          - run: echo "Applying cluster changes..."
          - apply:
              extra_args: ["-var-file=terraform.tfvars", "-parallelism=30"]

    platform:
      plan:
        steps:
          - init
          - run: terraform validate
          - plan
      apply:
        steps:
          - apply

# Pod 리소스
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

# 영구 스토리지 (Locking용)
persistence:
  enabled: true
  storageClassName: gp3
  accessModes:
    - ReadWriteOnce
  size: 10Gi

# 서비스 설정
service:
  type: ClusterIP
  port: 80

# Ingress 설정
ingress:
  enabled: true
  ingressClassName: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:111122223333:certificate/xxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
  hosts:
    - host: atlantis.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []

# ServiceAccount for Pod Identity
serviceAccount:
  create: true
  name: atlantis
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/AtlantisRole

# 환경 변수
environment:
  - name: TF_LOG
    value: "INFO"
  - name: ATLANTIS_WRITE_GIT_CREDS
    value: "true"
  - name: ATLANTIS_HIDE_PREV_PLAN_COMMENTS
    value: "true"
  - name: ATLANTIS_AUTOPLAN_MODULES
    value: "true"
  - name: ATLANTIS_PARALLEL_POOL_SIZE
    value: "5"

# Secret 환경 변수
environmentSecrets:
  - name: ATLANTIS_GH_TOKEN
    secretKeyRef:
      name: atlantis-secrets
      key: github-token
  - name: ATLANTIS_GH_WEBHOOK_SECRET
    secretKeyRef:
      name: atlantis-secrets
      key: webhook-secret

# Pod 보안
podSecurityContext:
  fsGroup: 1000

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

**Helm 설치:**

```bash
# Atlantis Helm repo 추가
helm repo add runatlantis https://runatlantis.github.io/helm-charts
helm repo update

# Secret 생성
kubectl create namespace atlantis
kubectl create secret generic atlantis-secrets -n atlantis \
  --from-literal=github-token="${GITHUB_TOKEN}" \
  --from-literal=webhook-secret="${WEBHOOK_SECRET}"

# Helm 설치
helm upgrade --install atlantis runatlantis/atlantis \
  -n atlantis \
  -f atlantis-values.yaml
```

### 1.3 Webhook 구성

**GitHub Webhook 설정:**

1. Repository Settings → Webhooks → Add webhook
2. Payload URL: `https://atlantis.example.com/events`
3. Content type: `application/json`
4. Secret: Webhook Secret 값 입력
5. Events 선택:
   - Pull request reviews
   - Pushes
   - Issue comments
   - Pull requests

**GitLab Webhook 설정:**

```bash
# GitLab Project → Settings → Webhooks
URL: https://atlantis.example.com/events
Secret Token: ${WEBHOOK_SECRET}
Trigger:
  - Push events
  - Comments
  - Merge request events
```

### 1.4 atlantis.yaml 프로젝트 구성

저장소 루트에 `atlantis.yaml` 파일을 생성하여 디렉토리별 워크플로우를 정의합니다.

```yaml
# atlantis.yaml
version: 3
automerge: false
delete_source_branch_on_merge: true
parallel_plan: true
parallel_apply: false  # Apply는 순차적으로

projects:
  # 01-network: VPC, Subnets, NAT Gateway
  - name: network-prod
    dir: 01-network/prod
    workspace: default
    terraform_version: v1.9.0
    workflow: network
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
        - "../modules/**/*.tf"
      enabled: true
    apply_requirements:
      - approved
      - mergeable

  - name: network-staging
    dir: 01-network/staging
    workspace: default
    terraform_version: v1.9.0
    workflow: network
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
      enabled: true
    apply_requirements:
      - approved

  # 02-cluster: EKS Cluster, Node Groups
  - name: cluster-prod
    dir: 02-cluster/prod
    workspace: default
    terraform_version: v1.9.0
    workflow: cluster
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
      enabled: true
    apply_requirements:
      - approved
      - mergeable
    depends_on:
      - network-prod

  - name: cluster-staging
    dir: 02-cluster/staging
    workspace: default
    workflow: cluster
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
      enabled: true
    depends_on:
      - network-staging

  # 03-platform: Add-ons, Helm Releases
  - name: platform-prod
    dir: 03-platform/prod
    workspace: default
    terraform_version: v1.9.0
    workflow: platform
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
        - "helm-values/*.yaml"
      enabled: true
    apply_requirements:
      - approved
    depends_on:
      - cluster-prod

  - name: platform-staging
    dir: 03-platform/staging
    workspace: default
    workflow: platform
    autoplan:
      enabled: true
    depends_on:
      - cluster-staging

workflows:
  network:
    plan:
      steps:
        - run: echo "Planning network infrastructure..."
        - init:
            extra_args: ["-backend-config=backend.hcl"]
        - plan:
            extra_args: ["-var-file=terraform.tfvars", "-out=tfplan"]
        - run: |
            terraform show -json tfplan > plan.json
            echo "Plan saved to plan.json"
    apply:
      steps:
        - run: echo "Applying network infrastructure..."
        - apply:
            extra_args: ["-var-file=terraform.tfvars"]
        - run: echo "Network apply completed!"

  cluster:
    plan:
      steps:
        - run: |
            echo "Checking network dependencies..."
            aws eks describe-cluster --name ${CLUSTER_NAME} 2>/dev/null || echo "Cluster will be created"
        - init
        - plan:
            extra_args: ["-var-file=terraform.tfvars", "-parallelism=30"]
    apply:
      steps:
        - run: |
            echo "⚠️ Applying EKS cluster changes..."
            echo "This may cause temporary disruption"
        - apply:
            extra_args: ["-var-file=terraform.tfvars", "-parallelism=30"]
        - run: |
            echo "Updating kubeconfig..."
            aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}

  platform:
    plan:
      steps:
        - init
        - run: terraform validate
        - run: terraform fmt -check=true -diff=true || echo "Format check warning"
        - plan
    apply:
      steps:
        - apply
        - run: |
            echo "Verifying platform components..."
            kubectl get pods -A --context=${CLUSTER_CONTEXT} | head -20
```

### 1.5 Pod Identity for AWS 액세스

Atlantis가 Terraform apply를 실행하려면 AWS 리소스에 대한 권한이 필요합니다.

**IAM Role Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
```

**IAM Policy (최소 권한 예시):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EKSManagement",
      "Effect": "Allow",
      "Action": [
        "eks:*"
      ],
      "Resource": [
        "arn:aws:eks:ap-northeast-2:111122223333:cluster/*",
        "arn:aws:eks:ap-northeast-2:111122223333:nodegroup/*/*/*"
      ]
    },
    {
      "Sid": "VPCManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:*Vpc*",
        "ec2:*Subnet*",
        "ec2:*SecurityGroup*",
        "ec2:*RouteTable*",
        "ec2:*InternetGateway*",
        "ec2:*NatGateway*",
        "ec2:*Address*",
        "ec2:Describe*",
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:CreateServiceLinkedRole",
        "iam:PassRole",
        "iam:TagRole",
        "iam:UntagRole"
      ],
      "Resource": [
        "arn:aws:iam::111122223333:role/eks-*",
        "arn:aws:iam::111122223333:role/atlantis-*"
      ]
    },
    {
      "Sid": "S3StateAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-terraform-state-bucket",
        "arn:aws:s3:::my-terraform-state-bucket/*"
      ]
    },
    {
      "Sid": "DynamoDBLocking",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-2:111122223333:table/terraform-locks"
    }
  ]
}
```

**Pod Identity Association:**

```bash
# Pod Identity Association 생성
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace atlantis \
  --service-account atlantis \
  --role-arn arn:aws:iam::111122223333:role/AtlantisRole
```

### 1.6 Multi-Repo 설정

여러 저장소에서 Atlantis를 사용할 때 server-side repo config로 일관된 정책을 적용합니다.

```yaml
# repos.yaml (ConfigMap으로 마운트)
repos:
  # 인프라 저장소 - 엄격한 정책
  - id: github.com/my-org/eks-infra
    branch: main
    apply_requirements:
      - approved
      - mergeable
    allowed_overrides:
      - workflow
    allow_custom_workflows: true
    pre_workflow_hooks:
      - run: |
          echo "Repository: $REPO_NAME"
          echo "PR: $PULL_NUM"
          echo "User: $USER_NAME"
    post_workflow_hooks:
      - run: |
          if [ "$COMMAND_NAME" = "apply" ]; then
            curl -X POST https://slack.webhook.url -d "{\"text\":\"Terraform applied by $USER_NAME in $PROJECT_NAME\"}"
          fi

  # 애플리케이션 인프라 - 느슨한 정책
  - id: github.com/my-org/app-infra-*
    apply_requirements:
      - approved
    allowed_overrides:
      - workflow
      - apply_requirements
    allow_custom_workflows: true

  # 테스트 저장소 - 자유로운 정책
  - id: /.*-test$/
    apply_requirements: []
    allow_custom_workflows: true

# 기본 정책 (위에 매칭되지 않는 저장소)
- id: /.*/
  apply_requirements:
    - approved
  allowed_overrides: []
  allow_custom_workflows: false
```

### 1.7 PR 기반 워크플로우

**일반적인 워크플로우:**

```
1. PR 생성
   └── Atlantis webhook 수신
       └── 자동 plan 실행 (autoplan: enabled)
           └── PR 코멘트에 plan 결과 표시

2. PR 리뷰
   └── 변경사항 검토
       └── 필요 시 코멘트로 재실행: `atlantis plan -p network-prod`

3. PR 승인
   └── apply_requirements 충족 확인
       └── 코멘트로 apply 실행: `atlantis apply -p network-prod`

4. PR 머지
   └── 자동 머지 (automerge: true 설정 시)
       └── Lock 해제
```

**Atlantis 코멘트 명령어:**

```bash
# Plan 실행
atlantis plan                     # 모든 프로젝트
atlantis plan -p network-prod     # 특정 프로젝트
atlantis plan -d 01-network/prod  # 특정 디렉토리
atlantis plan -- -target=aws_vpc.main  # Terraform 옵션 전달

# Apply 실행
atlantis apply                    # 모든 프로젝트
atlantis apply -p network-prod    # 특정 프로젝트
atlantis apply -d 01-network/prod # 특정 디렉토리

# Lock 관리
atlantis unlock                   # 현재 PR의 lock 해제

# 기타
atlantis version                  # 버전 확인
atlantis help                     # 도움말
```

### 1.8 보안: Apply 제한

특정 사용자/팀만 apply를 실행하도록 제한합니다.

```yaml
# repos.yaml
repos:
  - id: github.com/my-org/eks-infra
    # Apply 허용 사용자
    allowed_regexp_prefixes:
      - "apply"

    # Pre-workflow hook에서 사용자 검증
    pre_workflow_hooks:
      - run: |
          ALLOWED_USERS="admin1,admin2,infra-team-lead"
          if [ "$COMMAND_NAME" = "apply" ]; then
            if ! echo "$ALLOWED_USERS" | grep -q "$USER_NAME"; then
              echo "Error: User $USER_NAME is not authorized to run apply"
              exit 1
            fi
          fi

    # 특정 디렉토리에 대한 추가 검증
    workflows:
      production:
        plan:
          steps:
            - init
            - plan
        apply:
          steps:
            - run: |
                # Production 디렉토리는 추가 승인 필요
                if [[ "$DIR" == *"prod"* ]]; then
                  APPROVALS=$(gh pr view $PULL_NUM --json reviews -q '[.reviews[] | select(.state=="APPROVED")] | length')
                  if [ "$APPROVALS" -lt 2 ]; then
                    echo "Error: Production changes require at least 2 approvals"
                    exit 1
                  fi
                fi
            - apply
```

### 1.9 Locking 메커니즘

Atlantis는 동시에 같은 프로젝트를 수정하는 PR 충돌을 방지하기 위해 locking을 사용합니다.

```
PR #10: 01-network/prod 수정
  └── Plan 실행 → Lock 획득
      └── PR #10이 01-network/prod에 대한 lock 보유

PR #11: 01-network/prod 수정 시도
  └── Plan 실행 시도
      └── "Locked by PR #10" 에러
          └── PR #10이 완료되거나 unlock될 때까지 대기

해결 방법:
1. PR #10 완료 (merge/close)
2. `atlantis unlock` 명령어 사용
3. Atlantis UI에서 수동 unlock
```

**Lock 상태 확인:**

```bash
# Atlantis UI 접속
https://atlantis.example.com/locks

# 또는 API 호출
curl -s https://atlantis.example.com/api/locks | jq
```

---

## 2. Terraform Cloud

Terraform Cloud는 HashiCorp가 제공하는 관리형 Terraform 실행 환경으로, Atlantis의 대안으로 사용할 수 있습니다.

### 2.1 Workspace 구성

**계층별 Workspace 설계:**

```
terraform-cloud-org/
├── network-prod         # VPC, Subnets, NAT
├── network-staging
├── cluster-prod         # EKS Cluster
├── cluster-staging
├── platform-prod        # Add-ons, Helm
└── platform-staging
```

**Workspace 설정 (Terraform으로 관리):**

```hcl
# workspaces.tf
terraform {
  required_providers {
    tfe = {
      source  = "hashicorp/tfe"
      version = "~> 0.57"
    }
  }
}

provider "tfe" {
  organization = "my-org"
}

# Network Workspace
resource "tfe_workspace" "network_prod" {
  name              = "network-prod"
  organization      = "my-org"
  description       = "Production VPC and networking infrastructure"
  terraform_version = "1.9.0"
  working_directory = "01-network/prod"

  # VCS 연동
  vcs_repo {
    identifier     = "my-org/eks-infra"
    branch         = "main"
    oauth_token_id = var.oauth_token_id
  }

  # Auto apply 비활성화 (수동 승인 필요)
  auto_apply = false

  # Queue 설정
  queue_all_runs = true

  # Execution Mode
  execution_mode = "remote"

  # 태그
  tag_names = ["production", "network", "eks"]
}

# Cluster Workspace
resource "tfe_workspace" "cluster_prod" {
  name              = "cluster-prod"
  organization      = "my-org"
  description       = "Production EKS cluster"
  terraform_version = "1.9.0"
  working_directory = "02-cluster/prod"

  vcs_repo {
    identifier     = "my-org/eks-infra"
    branch         = "main"
    oauth_token_id = var.oauth_token_id
  }

  auto_apply = false
  tag_names  = ["production", "cluster", "eks"]
}

# Platform Workspace
resource "tfe_workspace" "platform_prod" {
  name              = "platform-prod"
  organization      = "my-org"
  description       = "Production platform components"
  terraform_version = "1.9.0"
  working_directory = "03-platform/prod"

  vcs_repo {
    identifier     = "my-org/eks-infra"
    branch         = "main"
    oauth_token_id = var.oauth_token_id
  }

  auto_apply = true  # Platform은 자동 적용
  tag_names  = ["production", "platform", "eks"]
}

# Variable Set (공통 변수)
resource "tfe_variable_set" "aws_credentials" {
  name         = "AWS Credentials"
  description  = "AWS credentials for all workspaces"
  organization = "my-org"
}

resource "tfe_variable" "aws_access_key" {
  key             = "AWS_ACCESS_KEY_ID"
  value           = var.aws_access_key_id
  category        = "env"
  sensitive       = true
  variable_set_id = tfe_variable_set.aws_credentials.id
}

resource "tfe_variable" "aws_secret_key" {
  key             = "AWS_SECRET_ACCESS_KEY"
  value           = var.aws_secret_access_key
  category        = "env"
  sensitive       = true
  variable_set_id = tfe_variable_set.aws_credentials.id
}

# Variable Set을 Workspace에 연결
resource "tfe_workspace_variable_set" "network_aws" {
  workspace_id    = tfe_workspace.network_prod.id
  variable_set_id = tfe_variable_set.aws_credentials.id
}

resource "tfe_workspace_variable_set" "cluster_aws" {
  workspace_id    = tfe_workspace.cluster_prod.id
  variable_set_id = tfe_variable_set.aws_credentials.id
}
```

### 2.2 VCS 기반 워크플로우

**GitHub Integration 설정:**

```hcl
# github-integration.tf
resource "tfe_oauth_client" "github" {
  organization     = "my-org"
  api_url          = "https://api.github.com"
  http_url         = "https://github.com"
  oauth_token      = var.github_oauth_token
  service_provider = "github"
}

output "oauth_token_id" {
  value = tfe_oauth_client.github.oauth_token_id
}
```

**워크플로우:**

```
1. main 브랜치에 push
   └── Terraform Cloud webhook 수신
       └── 해당 workspace에서 Plan 실행
           └── 결과 GitHub check에 표시

2. PR 생성
   └── Speculative Plan 실행 (실제 적용 X)
       └── PR 코멘트에 plan 결과 표시

3. PR 머지
   └── 실제 Plan + Apply 실행
       └── auto_apply=true면 자동 적용
       └── auto_apply=false면 UI에서 승인 후 적용
```

### 2.3 Run Triggers: 종속성 관리

Workspace 간 종속성을 설정하여 상위 인프라 변경 시 하위 workspace가 자동으로 트리거됩니다.

```hcl
# run-triggers.tf

# network-prod → cluster-prod 트리거
resource "tfe_run_trigger" "cluster_on_network" {
  workspace_id  = tfe_workspace.cluster_prod.id
  sourceable_id = tfe_workspace.network_prod.id
}

# cluster-prod → platform-prod 트리거
resource "tfe_run_trigger" "platform_on_cluster" {
  workspace_id  = tfe_workspace.platform_prod.id
  sourceable_id = tfe_workspace.cluster_prod.id
}
```

**트리거 흐름:**

```
network-prod Apply 완료
    │
    ▼
cluster-prod Plan 자동 시작 (Run Trigger)
    │
    ▼ (auto_apply 또는 수동 승인)
cluster-prod Apply 완료
    │
    ▼
platform-prod Plan 자동 시작 (Run Trigger)
    │
    ▼
platform-prod Apply
```

### 2.4 Sentinel Policy

Sentinel은 Terraform Cloud의 Policy as Code 프레임워크입니다.

**정책 예시들:**

```python
# sentinel/enforce-tags.sentinel
# 모든 리소스에 필수 태그 강제

import "tfplan/v2" as tfplan

required_tags = ["Environment", "Team", "CostCenter"]

# 태그 지원 리소스 타입
taggable_resource_types = [
  "aws_instance",
  "aws_vpc",
  "aws_subnet",
  "aws_security_group",
  "aws_eks_cluster",
  "aws_eks_node_group",
]

# 모든 리소스 검사
allResources = filter tfplan.resource_changes as _, rc {
  rc.mode is "managed" and
  rc.type in taggable_resource_types and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

# 필수 태그 검증
deny_resources_without_tags = rule {
  all allResources as _, resource {
    all required_tags as tag {
      resource.change.after.tags else {} contains tag
    }
  }
}

main = rule {
  deny_resources_without_tags
}
```

```python
# sentinel/restrict-instance-types.sentinel
# 허용된 인스턴스 타입만 사용

import "tfplan/v2" as tfplan

allowed_instance_types = [
  "t3.micro", "t3.small", "t3.medium", "t3.large",
  "m6i.large", "m6i.xlarge", "m6i.2xlarge",
  "c6i.large", "c6i.xlarge", "c6i.2xlarge",
]

ec2_instances = filter tfplan.resource_changes as _, rc {
  rc.type is "aws_instance" and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

eks_node_groups = filter tfplan.resource_changes as _, rc {
  rc.type is "aws_eks_node_group" and
  (rc.change.actions contains "create" or rc.change.actions contains "update")
}

# EC2 인스턴스 타입 검증
valid_ec2_types = rule {
  all ec2_instances as _, instance {
    instance.change.after.instance_type in allowed_instance_types
  }
}

# EKS 노드 그룹 인스턴스 타입 검증
valid_eks_types = rule {
  all eks_node_groups as _, ng {
    all ng.change.after.instance_types as instance_type {
      instance_type in allowed_instance_types
    }
  }
}

main = rule {
  valid_ec2_types and valid_eks_types
}
```

```python
# sentinel/cost-limit.sentinel
# 예상 비용 제한

import "tfrun"
import "decimal"

# 월간 비용 제한 ($5000)
cost_limit = decimal.new(5000)

# Cost Estimation 결과 확인
cost_estimate = decimal.new(tfrun.cost_estimate.proposed_monthly_cost)

main = rule {
  cost_estimate.less_than(cost_limit)
}
```

**Policy Set 구성:**

```hcl
# policy-sets.tf
resource "tfe_policy_set" "production_policies" {
  name         = "production-policies"
  description  = "Policies for production workspaces"
  organization = "my-org"
  kind         = "sentinel"

  # VCS에서 정책 로드
  vcs_repo {
    identifier         = "my-org/terraform-policies"
    branch             = "main"
    oauth_token_id     = var.oauth_token_id
    ingress_submodules = false
  }

  # 적용 대상 workspace
  workspace_ids = [
    tfe_workspace.network_prod.id,
    tfe_workspace.cluster_prod.id,
    tfe_workspace.platform_prod.id,
  ]
}
```

### 2.5 Remote State 공유

Workspace 간 state 참조를 통해 output 값을 공유합니다.

```hcl
# 02-cluster/prod/main.tf
# Network workspace의 output 참조

data "terraform_remote_state" "network" {
  backend = "remote"

  config = {
    organization = "my-org"
    workspaces = {
      name = "network-prod"
    }
  }
}

# Network output 사용
module "eks" {
  source = "../modules/eks"

  vpc_id          = data.terraform_remote_state.network.outputs.vpc_id
  private_subnets = data.terraform_remote_state.network.outputs.private_subnet_ids

  # ...
}
```

### 2.6 Atlantis vs Terraform Cloud 비교

| 기능 | Atlantis | Terraform Cloud |
|------|----------|-----------------|
| **호스팅** | Self-hosted (EKS) | HashiCorp 관리형 |
| **비용** | 인프라 비용만 | 사용량 기반 과금 |
| **VCS 통합** | GitHub, GitLab, Bitbucket | GitHub, GitLab, Bitbucket, Azure DevOps |
| **State 관리** | 외부 (S3, etc.) | 내장 |
| **Policy as Code** | 커스텀 스크립트 | Sentinel (내장) |
| **Cost Estimation** | 외부 도구 필요 | 내장 |
| **Run Triggers** | atlantis.yaml depends_on | 네이티브 지원 |
| **Private Registry** | 미지원 | 지원 |
| **팀 관리** | Git 권한 의존 | RBAC 내장 |
| **감사 로그** | 커스텀 구현 | 내장 |
| **복잡도** | 높음 (직접 운영) | 낮음 (관리형) |
| **유연성** | 높음 (완전 커스텀) | 중간 (정해진 워크플로우) |

**선택 가이드:**

- **Atlantis 추천**: 완전한 통제가 필요하거나, 비용 최적화가 중요하거나, 특수한 워크플로우가 필요한 경우
- **Terraform Cloud 추천**: 관리 오버헤드를 줄이고 싶거나, Sentinel 정책이 필요하거나, 팀이 빠르게 시작해야 하는 경우

---

## 3. FluxCD

FluxCD는 Kubernetes 네이티브 GitOps 도구로, Git 저장소를 진실의 원천(Source of Truth)으로 사용하여 클러스터 상태를 동기화합니다.

### 3.1 ArgoCD vs FluxCD 비교

| 기능 | ArgoCD | FluxCD |
|------|--------|--------|
| **아키텍처** | 단일 컨트롤러 + UI | 다중 컨트롤러 (GitOps Toolkit) |
| **UI** | 풍부한 웹 UI | CLI 중심, Weave GitOps UI (별도) |
| **CRD** | Application, AppProject | GitRepository, Kustomization, HelmRelease |
| **Helm 지원** | 네이티브 | HelmRelease CRD |
| **이미지 자동화** | argocd-image-updater (별도) | Image Automation Controller (내장) |
| **Multi-tenancy** | AppProject 기반 | Namespace 기반 |
| **알림** | Notification Controller | Notification Controller |
| **설치 복잡도** | Helm 단일 설치 | Bootstrap 명령어 |
| **리소스 사용량** | 중간 | 낮음 |
| **학습 곡선** | 낮음 (UI 기반) | 중간 (CLI 기반) |
| **커뮤니티** | CNCF Graduated | CNCF Graduated |
| **주요 사용 사례** | 애플리케이션 배포 중심 | 인프라 + 애플리케이션 통합 관리 |

**선택 가이드:**

- **ArgoCD**: UI가 중요하거나, 개발팀이 직접 배포를 관리하거나, 빠른 시작이 필요한 경우
- **FluxCD**: 이미지 자동화가 핵심이거나, 여러 소스 타입을 통합 관리하거나, 리소스 효율성이 중요한 경우

### 3.2 FluxCD 설치

**Bootstrap (GitHub 연동):**

```bash
# flux CLI 설치
curl -s https://fluxcd.io/install.sh | sudo bash

# GitHub Token 환경변수 설정
export GITHUB_TOKEN=<your-token>
export GITHUB_USER=<your-username>

# Bootstrap 실행
flux bootstrap github \
  --owner=${GITHUB_USER} \
  --repository=fleet-infra \
  --branch=main \
  --path=clusters/production \
  --personal \
  --components-extra=image-reflector-controller,image-automation-controller

# 결과: fleet-infra 저장소에 Flux 구성 생성
# clusters/production/flux-system/ 디렉토리에 Flux 컴포넌트 매니페스트
```

**Bootstrap 결과 구조:**

```
fleet-infra/
├── clusters/
│   └── production/
│       └── flux-system/
│           ├── gotk-components.yaml  # Flux 컴포넌트
│           ├── gotk-sync.yaml        # Self-sync 설정
│           └── kustomization.yaml
```

### 3.3 HelmRelease CRD

FluxCD로 ArgoCD 자체를 배포하는 예시입니다.

```yaml
# clusters/production/argocd/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
  labels:
    toolkit.fluxcd.io/tenant: platform
---
# clusters/production/argocd/helmrepository.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: argo
  namespace: argocd
spec:
  interval: 1h
  url: https://argoproj.github.io/argo-helm
---
# clusters/production/argocd/helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: argocd
  namespace: argocd
spec:
  interval: 30m
  chart:
    spec:
      chart: argo-cd
      version: "7.3.x"  # Semver 범위 지원
      sourceRef:
        kind: HelmRepository
        name: argo
        namespace: argocd
      interval: 12h

  # Helm values
  values:
    global:
      domain: argocd.example.com

    server:
      replicas: 2
      ingress:
        enabled: true
        ingressClassName: alb
        annotations:
          alb.ingress.kubernetes.io/scheme: internet-facing
          alb.ingress.kubernetes.io/target-type: ip
        hosts:
          - argocd.example.com

    controller:
      replicas: 1
      resources:
        requests:
          cpu: 500m
          memory: 512Mi

    repoServer:
      replicas: 2
      resources:
        requests:
          cpu: 200m
          memory: 256Mi

    redis:
      enabled: true
      resources:
        requests:
          cpu: 100m
          memory: 128Mi

    configs:
      params:
        server.insecure: true  # ALB에서 TLS 종료

  # Upgrade 설정
  upgrade:
    remediation:
      retries: 3

  # Test 비활성화
  test:
    enable: false

  # Rollback 설정
  rollback:
    cleanupOnFail: true
```

### 3.4 Kustomization for 환경 오버레이

**디렉토리 구조:**

```
fleet-infra/
├── base/
│   └── app/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch-replicas.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch-replicas.yaml
│   └── prod/
│       ├── kustomization.yaml
│       └── patch-replicas.yaml
└── clusters/
    ├── dev/
    │   └── apps.yaml
    ├── staging/
    │   └── apps.yaml
    └── prod/
        └── apps.yaml
```

**Flux Kustomization CRD:**

```yaml
# clusters/prod/apps.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  interval: 10m
  retryInterval: 1m
  timeout: 5m

  sourceRef:
    kind: GitRepository
    name: flux-system

  path: ./overlays/prod
  prune: true  # Git에서 삭제된 리소스 자동 삭제

  # Health check
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: myapp
      namespace: default

  # 종속성
  dependsOn:
    - name: infrastructure

  # 패치 (인라인)
  patches:
    - patch: |
        - op: replace
          path: /spec/replicas
          value: 5
      target:
        kind: Deployment
        name: myapp

  # Post-build 변수 치환
  postBuild:
    substitute:
      ENVIRONMENT: production
      DOMAIN: example.com
    substituteFrom:
      - kind: ConfigMap
        name: cluster-config
      - kind: Secret
        name: cluster-secrets
```

### 3.5 Image Automation Controller

새로운 컨테이너 이미지가 푸시되면 자동으로 매니페스트를 업데이트하고 Git에 커밋합니다.

**이미지 정책 설정:**

```yaml
# clusters/production/image-automation/image-repository.yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: myapp
  namespace: flux-system
spec:
  image: 111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/myapp
  interval: 1m
  provider: aws  # ECR 인증
  secretRef:
    name: ecr-credentials  # 또는 Pod Identity 사용
---
# clusters/production/image-automation/image-policy.yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: myapp
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: myapp
  policy:
    semver:
      range: 1.x.x  # 1.x.x 버전 중 최신
---
# 또는 알파벳 순서 (latest 태그)
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: myapp-latest
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: myapp
  policy:
    alphabetical:
      order: asc
  filterTags:
    pattern: '^main-[a-f0-9]+-(?P<ts>[0-9]+)$'
    extract: '$ts'
---
# 숫자 기반 (빌드 번호)
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: myapp-build
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: myapp
  policy:
    numerical:
      order: asc
  filterTags:
    pattern: '^build-(?P<build>[0-9]+)$'
    extract: '$build'
```

**이미지 업데이트 자동화:**

```yaml
# clusters/production/image-automation/image-update.yaml
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: flux-system
  namespace: flux-system
spec:
  interval: 30m

  sourceRef:
    kind: GitRepository
    name: flux-system

  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: fluxcdbot@example.com
        name: fluxcdbot
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $changes := .Changed.Objects -}}
        - {{ $resource.Kind }}/{{ $resource.Name }}:
            {{ range $_, $change := $changes -}}
            - {{ $change.OldValue }} -> {{ $change.NewValue }}
            {{ end -}}
        {{ end -}}
    push:
      branch: main

  update:
    path: ./clusters/production
    strategy: Setters  # 마커 기반 업데이트
```

**매니페스트에 마커 추가:**

```yaml
# clusters/production/apps/myapp/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
        - name: myapp
          image: 111122223333.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:1.2.3 # {"$imagepolicy": "flux-system:myapp"}
```

**자동화 흐름:**

```
1. 새 이미지 push: myapp:1.2.4
   │
   ▼
2. ImageRepository가 새 태그 감지
   │
   ▼
3. ImagePolicy가 1.x.x 범위에서 최신 버전 선택: 1.2.4
   │
   ▼
4. ImageUpdateAutomation이 매니페스트 업데이트
   │
   ▼
5. Git commit & push
   │
   ▼
6. Flux Kustomization이 변경 감지 → 클러스터 동기화
```

### 3.6 Source Controller

다양한 소스 타입을 지원합니다.

```yaml
# GitRepository
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: app-manifests
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/my-org/app-manifests
  ref:
    branch: main
  secretRef:
    name: git-credentials
  ignore: |
    # Flux 무시 패턴
    !.git
    *.md
    docs/
---
# HelmRepository
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: bitnami
  namespace: flux-system
spec:
  interval: 1h
  url: https://charts.bitnami.com/bitnami
---
# OCI Repository (Helm OCI)
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OCIRepository
metadata:
  name: podinfo
  namespace: flux-system
spec:
  interval: 5m
  url: oci://ghcr.io/stefanprodan/manifests/podinfo
  ref:
    tag: latest
---
# S3 Bucket
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: Bucket
metadata:
  name: terraform-states
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-terraform-state-bucket
  region: ap-northeast-2
  secretRef:
    name: aws-credentials
```

### 3.7 Notification Controller

```yaml
# Provider 설정
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: "#gitops-alerts"
  secretRef:
    name: slack-webhook
---
# Slack Secret
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: flux-system
stringData:
  address: https://hooks.slack.com/services/xxx/yyy/zzz
---
# Alert 설정
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: on-call-alerts
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: error
  eventSources:
    - kind: Kustomization
      name: '*'
    - kind: HelmRelease
      name: '*'
  summary: "Flux reconciliation alert"
---
# 모든 이벤트 알림
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: all-events
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: info
  eventSources:
    - kind: Kustomization
      name: '*'
      namespace: '*'
    - kind: HelmRelease
      name: '*'
      namespace: '*'
  inclusionList:
    - ".*succeeded.*"
    - ".*failed.*"
---
# Microsoft Teams Provider
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: teams
  namespace: flux-system
spec:
  type: msteams
  secretRef:
    name: teams-webhook
```

---

## 4. AIOps 전략

AIOps(Artificial Intelligence for IT Operations)는 AI/ML을 활용하여 운영 작업을 자동화하고 최적화합니다.

### 4.1 LLM 기반 PR 리뷰

**GitHub Copilot for PRs:**

```yaml
# .github/workflows/copilot-review.yaml
name: Copilot PR Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  copilot-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed files
        id: changed
        run: |
          echo "files=$(git diff --name-only origin/${{ github.base_ref }}...HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT

      # GitHub Copilot API 호출 (예시)
      - name: Request Copilot Review
        uses: actions/github-script@v7
        with:
          script: |
            const changedFiles = '${{ steps.changed.outputs.files }}'.split(' ').filter(f => f);

            // Copilot API 또는 자체 LLM 엔드포인트 호출
            const response = await fetch('https://api.copilot.example.com/review', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${process.env.COPILOT_TOKEN}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                repo: context.repo,
                pr: context.payload.pull_request.number,
                files: changedFiles
              })
            });

            const review = await response.json();

            // PR에 코멘트 추가
            await github.rest.pulls.createReview({
              ...context.repo,
              pull_number: context.payload.pull_request.number,
              body: review.summary,
              event: review.approved ? 'APPROVE' : 'COMMENT',
              comments: review.lineComments
            });
```

**Claude Code Review 통합:**

```yaml
# .github/workflows/claude-review.yaml
name: Claude Code Review
on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - '**.tf'
      - '**.yaml'
      - '**.yml'

jobs:
  claude-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get PR diff
        id: diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > pr_diff.txt

      - name: Claude Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Claude API 호출
          DIFF_CONTENT=$(cat pr_diff.txt | head -c 50000)

          REVIEW=$(curl -s https://api.anthropic.com/v1/messages \
            -H "Content-Type: application/json" \
            -H "x-api-key: ${ANTHROPIC_API_KEY}" \
            -H "anthropic-version: 2023-06-01" \
            -d "{
              \"model\": \"claude-sonnet-4-20250514\",
              \"max_tokens\": 4096,
              \"messages\": [{
                \"role\": \"user\",
                \"content\": \"Review this infrastructure code change. Focus on: security issues, best practices, potential problems, and suggestions for improvement.\n\nDiff:\n${DIFF_CONTENT}\"
              }]
            }" | jq -r '.content[0].text')

          echo "$REVIEW" > review.md

      - name: Post Review Comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('review.md', 'utf8');

            await github.rest.issues.createComment({
              ...context.repo,
              issue_number: context.payload.pull_request.number,
              body: `## Claude Code Review\n\n${review}`
            });
```

### 4.2 메트릭 기반 YAML 자동 수정

실제 사용량 메트릭을 기반으로 HPA 설정을 자동으로 조정합니다.

```python
# scripts/hpa-optimizer.py
import os
import yaml
import requests
from kubernetes import client, config
from datetime import datetime, timedelta

# Prometheus 쿼리
PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL', 'http://prometheus:9090')

def get_avg_cpu_usage(deployment_name, namespace, hours=168):
    """지난 N시간 동안의 평균 CPU 사용률 조회"""
    query = f'''
    avg(
      avg_over_time(
        container_cpu_usage_seconds_total{{
          namespace="{namespace}",
          pod=~"{deployment_name}-.*",
          container!="POD"
        }}[{hours}h]
      )
    ) by (container)
    '''

    response = requests.get(
        f'{PROMETHEUS_URL}/api/v1/query',
        params={'query': query}
    )
    result = response.json()

    if result['data']['result']:
        return float(result['data']['result'][0]['value'][1])
    return None

def get_p95_rps(service_name, namespace, hours=168):
    """지난 N시간 동안의 P95 RPS 조회"""
    query = f'''
    histogram_quantile(0.95,
      sum(rate(
        http_requests_total{{
          namespace="{namespace}",
          service="{service_name}"
        }}[5m]
      )) by (le)
    )
    '''

    response = requests.get(
        f'{PROMETHEUS_URL}/api/v1/query',
        params={'query': query}
    )
    result = response.json()

    if result['data']['result']:
        return float(result['data']['result'][0]['value'][1])
    return None

def calculate_optimal_hpa_target(current_target, avg_usage, p95_usage):
    """최적 HPA 타겟 계산"""
    # 여유율 20% 확보
    buffer = 0.2

    # P95 기준으로 계산
    if p95_usage:
        optimal = int(p95_usage * (1 + buffer))
    else:
        optimal = int(avg_usage * (1 + buffer))

    # 범위 제한: 50% ~ 90%
    optimal = max(50, min(90, optimal))

    return optimal

def update_hpa_manifest(file_path, new_target):
    """HPA 매니페스트 업데이트"""
    with open(file_path, 'r') as f:
        manifest = yaml.safe_load(f)

    # averageUtilization 업데이트
    for metric in manifest['spec']['metrics']:
        if metric['type'] == 'Resource':
            metric['resource']['target']['averageUtilization'] = new_target

    with open(file_path, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False)

    return manifest

def main():
    config.load_incluster_config()
    v1 = client.AutoscalingV1Api()

    # 모든 HPA 조회
    hpas = v1.list_horizontal_pod_autoscaler_for_all_namespaces()

    for hpa in hpas.items:
        name = hpa.metadata.name
        namespace = hpa.metadata.namespace

        # 현재 타겟 조회
        current_target = hpa.spec.target_cpu_utilization_percentage or 80

        # 메트릭 조회
        avg_cpu = get_avg_cpu_usage(name, namespace)
        p95_rps = get_p95_rps(name, namespace)

        if avg_cpu:
            optimal = calculate_optimal_hpa_target(current_target, avg_cpu, p95_rps)

            if abs(optimal - current_target) > 5:  # 5% 이상 차이날 때만 업데이트
                print(f"[{namespace}/{name}] Current: {current_target}% -> Optimal: {optimal}%")

                # Git 저장소의 매니페스트 업데이트 (실제 구현 시)
                # update_hpa_manifest(f'manifests/{namespace}/{name}-hpa.yaml', optimal)

if __name__ == '__main__':
    main()
```

**CronJob으로 실행:**

```yaml
# hpa-optimizer-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hpa-optimizer
  namespace: platform
spec:
  schedule: "0 6 * * 1"  # 매주 월요일 오전 6시
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: hpa-optimizer
          containers:
            - name: optimizer
              image: python:3.11-slim
              command:
                - python
                - /scripts/hpa-optimizer.py
              env:
                - name: PROMETHEUS_URL
                  value: "http://prometheus.monitoring:9090"
                - name: GIT_REPO
                  value: "https://github.com/my-org/k8s-manifests"
              volumeMounts:
                - name: scripts
                  mountPath: /scripts
          volumes:
            - name: scripts
              configMap:
                name: hpa-optimizer-scripts
          restartPolicy: OnFailure
```

### 4.3 트래픽 이상 탐지 및 자동 대응

```python
# scripts/traffic-anomaly-detector.py
import boto3
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
import json

cloudwatch = boto3.client('cloudwatch')
elbv2 = boto3.client('elbv2')

def get_request_count_history(target_group_arn, hours=24):
    """지난 N시간의 요청 수 조회"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'requests',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/ApplicationELB',
                        'MetricName': 'RequestCount',
                        'Dimensions': [
                            {
                                'Name': 'TargetGroup',
                                'Value': target_group_arn.split(':')[-1]
                            }
                        ]
                    },
                    'Period': 300,  # 5분 단위
                    'Stat': 'Sum'
                }
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )

    return response['MetricDataResults'][0]['Values']

def detect_anomaly(data):
    """Isolation Forest를 사용한 이상 탐지"""
    if len(data) < 10:
        return False, 0

    X = np.array(data).reshape(-1, 1)

    model = IsolationForest(
        contamination=0.1,
        random_state=42
    )
    model.fit(X)

    # 최근 값이 이상치인지 확인
    latest = np.array([[data[-1]]])
    prediction = model.predict(latest)
    score = model.score_samples(latest)[0]

    return prediction[0] == -1, score

def update_target_weights(listener_arn, primary_weight, fallback_weight):
    """NLB 타겟 그룹 가중치 조정"""
    response = elbv2.modify_listener(
        ListenerArn=listener_arn,
        DefaultActions=[
            {
                'Type': 'forward',
                'ForwardConfig': {
                    'TargetGroups': [
                        {
                            'TargetGroupArn': PRIMARY_TARGET_GROUP,
                            'Weight': primary_weight
                        },
                        {
                            'TargetGroupArn': FALLBACK_TARGET_GROUP,
                            'Weight': fallback_weight
                        }
                    ]
                }
            }
        ]
    )
    return response

def lambda_handler(event, context):
    """Lambda 핸들러"""
    target_group_arn = event.get('target_group_arn')
    listener_arn = event.get('listener_arn')

    # 히스토리 데이터 조회
    history = get_request_count_history(target_group_arn)

    # 이상 탐지
    is_anomaly, score = detect_anomaly(history)

    if is_anomaly:
        print(f"Anomaly detected! Score: {score}")

        # 심각도에 따른 가중치 조정
        if score < -0.5:
            # 심각한 이상: fallback으로 대부분 트래픽 전환
            update_target_weights(listener_arn, 10, 90)
            action = "Critical anomaly - redirected 90% to fallback"
        else:
            # 경미한 이상: 부분 전환
            update_target_weights(listener_arn, 50, 50)
            action = "Minor anomaly - balanced traffic 50/50"

        # SNS 알림
        sns = boto3.client('sns')
        sns.publish(
            TopicArn=os.environ['ALERT_TOPIC_ARN'],
            Subject='Traffic Anomaly Detected',
            Message=json.dumps({
                'target_group': target_group_arn,
                'anomaly_score': score,
                'action_taken': action,
                'timestamp': datetime.utcnow().isoformat()
            })
        )
    else:
        # 정상: 가중치 복원
        update_target_weights(listener_arn, 100, 0)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'is_anomaly': is_anomaly,
            'score': score
        })
    }
```

### 4.4 Progressive Delivery with Argo Rollouts

```yaml
# rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 10
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myapp:v2
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi

  strategy:
    canary:
      # Canary 단계 정의
      steps:
        - setWeight: 5
        - pause: {duration: 2m}
        - setWeight: 10
        - pause: {duration: 5m}
        - analysis:
            templates:
              - templateName: success-rate
            args:
              - name: service-name
                value: myapp
        - setWeight: 30
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency
        - setWeight: 50
        - pause: {duration: 10m}
        - setWeight: 80
        - pause: {duration: 5m}

      # 트래픽 라우팅
      canaryService: myapp-canary
      stableService: myapp-stable

      trafficRouting:
        alb:
          ingress: myapp-ingress
          servicePort: 80

      # Anti-Affinity
      antiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution:
          weight: 100
---
# analysis-templates.yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result[0] >= 0.99
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            sum(rate(
              http_requests_total{
                service="{{args.service-name}}",
                status=~"2.."
              }[5m]
            )) /
            sum(rate(
              http_requests_total{
                service="{{args.service-name}}"
              }[5m]
            ))
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency
spec:
  metrics:
    - name: p99-latency
      interval: 1m
      count: 5
      successCondition: result[0] < 500  # 500ms 미만
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus.monitoring:9090
          query: |
            histogram_quantile(0.99,
              sum(rate(
                http_request_duration_seconds_bucket{
                  service="{{args.service-name}}"
                }[5m]
              )) by (le)
            ) * 1000
```

### 4.5 AIOps 한계 및 휴먼 인 더 루프

**AIOps의 한계:**

| 영역 | 한계 | 대응 방안 |
|------|------|-----------|
| **컨텍스트 이해** | 비즈니스 컨텍스트 부족 | Human 승인 게이트 추가 |
| **엣지 케이스** | 학습되지 않은 상황 대응 불가 | Fallback 정책 정의 |
| **책임 소재** | 자동화 결정의 책임 불명확 | 감사 로그 및 승인 기록 |
| **오탐/미탐** | False Positive/Negative | 임계값 튜닝 및 모니터링 |
| **비용** | LLM API 비용 | Rate limiting, 캐싱 |

**Human-in-the-Loop 패턴:**

```yaml
# approval-workflow.yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  name: ai-suggested-change
spec:
  entrypoint: approval-flow
  templates:
    - name: approval-flow
      steps:
        - - name: ai-analysis
            template: analyze-metrics

        - - name: generate-suggestion
            template: llm-suggest
            arguments:
              parameters:
                - name: metrics
                  value: "{{steps.ai-analysis.outputs.result}}"

        - - name: human-approval
            template: approval-gate
            arguments:
              parameters:
                - name: suggestion
                  value: "{{steps.generate-suggestion.outputs.result}}"

        - - name: apply-change
            template: apply-suggestion
            when: "{{steps.human-approval.outputs.result}} == approved"

    - name: approval-gate
      inputs:
        parameters:
          - name: suggestion
      suspend: {}  # Human 승인까지 대기
      outputs:
        parameters:
          - name: result
            valueFrom:
              supplied: {}
```

**Guardrails 구현:**

```python
# guardrails.py
class AIOpsGuardrails:
    """AIOps 자동화의 안전장치"""

    # 자동 적용 가능한 변경 범위
    SAFE_AUTO_APPLY = {
        'hpa_target_change': (-10, 10),  # ±10%
        'replica_change': (-2, 2),        # ±2 replicas
        'resource_change': (-0.2, 0.2),   # ±20%
    }

    # 즉시 롤백 조건
    ROLLBACK_CONDITIONS = {
        'error_rate': 0.05,      # 5% 이상 에러율
        'latency_p99': 1000,     # 1초 이상 P99 레이턴시
        'availability': 0.99,   # 99% 미만 가용성
    }

    # 적용 금지 시간대
    FREEZE_WINDOWS = [
        ('Friday 18:00', 'Monday 06:00'),  # 주말
        ('23:00', '06:00'),                 # 야간
    ]

    @classmethod
    def can_auto_apply(cls, change_type, change_value):
        """자동 적용 가능 여부 확인"""
        if change_type not in cls.SAFE_AUTO_APPLY:
            return False

        min_val, max_val = cls.SAFE_AUTO_APPLY[change_type]
        return min_val <= change_value <= max_val

    @classmethod
    def should_rollback(cls, metrics):
        """롤백 필요 여부 확인"""
        if metrics.get('error_rate', 0) > cls.ROLLBACK_CONDITIONS['error_rate']:
            return True, 'High error rate'
        if metrics.get('latency_p99', 0) > cls.ROLLBACK_CONDITIONS['latency_p99']:
            return True, 'High latency'
        if metrics.get('availability', 1) < cls.ROLLBACK_CONDITIONS['availability']:
            return True, 'Low availability'
        return False, None

    @classmethod
    def is_freeze_window(cls):
        """변경 금지 시간대 여부 확인"""
        from datetime import datetime
        now = datetime.now()
        # 실제 구현에서는 시간대 파싱 로직 추가
        return False
```

---

## 요약

### GitOps 자동화 도구 선택 가이드

| 요구사항 | 추천 도구 |
|----------|----------|
| Terraform PR 자동화 (Self-hosted) | Atlantis |
| Terraform 관리형 서비스 | Terraform Cloud |
| K8s 배포 + UI 중심 | ArgoCD |
| K8s 배포 + 이미지 자동화 | FluxCD |
| 멀티 소스 통합 관리 | FluxCD |
| AIOps 시작 | Argo Rollouts + Analysis |

### 핵심 포인트

1. **Atlantis**: PR 기반 Terraform 워크플로우로 인프라 변경 협업 강화
2. **Terraform Cloud**: 관리형 서비스로 운영 부담 감소, Sentinel 정책 활용
3. **FluxCD**: 이미지 자동화로 완전한 GitOps 파이프라인 구축
4. **AIOps**: AI 지원 자동화는 항상 Human-in-the-Loop와 Guardrails 필수

---

## 참고 자료

- [Atlantis 공식 문서](https://www.runatlantis.io/docs/)
- [Terraform Cloud 문서](https://developer.hashicorp.com/terraform/cloud-docs)
- [FluxCD 공식 문서](https://fluxcd.io/docs/)
- [Argo Rollouts 문서](https://argoproj.github.io/argo-rollouts/)
- [GitOps Toolkit](https://fluxcd.io/flux/components/)

---

< [이전: ArgoCD 멀티클러스터](./04-gitops-multi-cluster.md) | [목차](./README.md) | [다음: 스케일링 전략](./06-scaling-strategies.md) >
