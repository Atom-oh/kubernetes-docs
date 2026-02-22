# EKS 보안 모범 사례

> **지원 버전**: Amazon EKS 1.31, 1.32, 1.33
> **마지막 업데이트**: 2025년 2월 21일

Amazon EKS 환경에서의 보안 모범 사례를 다룹니다. IAM 통합부터 네트워크 보안, 런타임 보호까지 EKS 클러스터를 안전하게 운영하는 방법을 상세히 알아봅니다.

## 목차

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC 엔드포인트](#vpc-엔드포인트)
5. [컨트롤 플레인 로깅](#컨트롤-플레인-로깅)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [클러스터 암호화](#클러스터-암호화)
10. [노드 보안](#노드-보안)
11. [프라이빗 클러스터](#프라이빗-클러스터)
12. [멀티테넌시 패턴](#멀티테넌시-패턴)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA 개요

IRSA(IAM Roles for Service Accounts)는 Kubernetes ServiceAccount에 IAM 역할을 연결하여 Pod가 AWS 서비스에 안전하게 접근할 수 있게 합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           IRSA 아키텍처                                  │
│                                                                         │
│  ┌─────────────┐                              ┌─────────────────────┐  │
│  │   EKS Pod   │                              │     AWS IAM         │  │
│  │             │                              │                     │  │
│  │ ServiceAcc  │──────┐                       │  ┌───────────────┐  │  │
│  │ (with IRSA) │      │                       │  │   IAM Role    │  │  │
│  └─────────────┘      │                       │  │               │  │  │
│         │             │                       │  │ Trust Policy: │  │  │
│         │             │                       │  │ OIDC Provider │  │  │
│         ▼             │                       │  └───────┬───────┘  │  │
│  ┌─────────────┐      │   ┌─────────────┐    │          │          │  │
│  │ Projected   │      │   │    OIDC     │    │          │          │  │
│  │   Token     │──────┴──▶│  Provider   │────┼──────────┘          │  │
│  └─────────────┘          └─────────────┘    │                     │  │
│                                              │  ┌───────────────┐  │  │
│                                              │  │ AWS Services  │  │  │
│                                              │  │ (S3, DynamoDB)│  │  │
│                                              │  └───────────────┘  │  │
└─────────────────────────────────────────────────────────────────────────┘
```

### IRSA 설정

```bash
# 1. OIDC Provider 생성 (클러스터당 한 번)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. IAM 정책 생성
cat <<EOF > s3-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-bucket",
                "arn:aws:s3:::my-bucket/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name S3ReadPolicy \
    --policy-document file://s3-policy.json

# 3. IAM ServiceAccount 생성
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### IRSA 사용

```yaml
# ServiceAccount 확인
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: production
  annotations:
    # IRSA 역할 ARN
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eksctl-my-cluster-s3-reader-sa
---
# Pod에서 ServiceAccount 사용
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa
  containers:
  - name: app
    image: amazon/aws-cli
    command: ["aws", "s3", "ls", "s3://my-bucket"]
    # AWS SDK가 자동으로 IRSA 토큰 사용
```

### IRSA 트러스트 정책

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.ap-northeast-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### IRSA 모범 사례

```yaml
# 1. 최소 권한 원칙
# 각 ServiceAccount에 필요한 최소 권한만 부여

# 2. 네임스페이스별 ServiceAccount 분리
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dynamodb-reader
  namespace: orders-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-dynamodb-role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-uploader
  namespace: media-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/media-s3-role
```

---

## EKS Pod Identity

### Pod Identity 개요

EKS Pod Identity는 IRSA의 후속 기능으로, 더 간단한 설정과 향상된 보안을 제공합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EKS Pod Identity 아키텍처                           │
│                                                                         │
│  ┌─────────────┐         ┌─────────────────┐         ┌──────────────┐  │
│  │   EKS Pod   │────────▶│  Pod Identity   │────────▶│   AWS IAM    │  │
│  │             │         │     Agent       │         │    Role      │  │
│  │ ServiceAcc  │         │  (DaemonSet)    │         │              │  │
│  └─────────────┘         └─────────────────┘         └──────────────┘  │
│                                                                         │
│  장점:                                                                   │
│  • OIDC Provider 설정 불필요                                             │
│  • 역할 재사용 용이                                                      │
│  • 향상된 감사 로깅                                                      │
│  • 세션 태그 지원                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pod Identity 설정

```bash
# 1. Pod Identity Agent 애드온 설치
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent \
    --addon-version v1.3.0-eksbuild.1

# 2. IAM 역할 생성 (Pod Identity용 트러스트 정책)
cat <<EOF > trust-policy.json
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
EOF

aws iam create-role \
    --role-name my-pod-role \
    --assume-role-policy-document file://trust-policy.json

# 3. 정책 연결
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Pod Identity Association 생성
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Pod Identity 사용

```yaml
# ServiceAccount (어노테이션 불필요)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
---
# Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK가 자동으로 Pod Identity 사용
```

### IRSA vs Pod Identity 비교

| 특성 | IRSA | EKS Pod Identity |
|------|------|------------------|
| **설정 복잡도** | OIDC Provider 필요 | 간단 (API 호출) |
| **트러스트 정책** | OIDC 조건 필요 | 간단한 서비스 프린시펄 |
| **역할 재사용** | 클러스터별 수정 필요 | 여러 클러스터에서 재사용 |
| **감사 로깅** | CloudTrail (SA 수준) | CloudTrail (Pod 수준) |
| **세션 태그** | 미지원 | 지원 |
| **권장** | 기존 환경 | 신규 환경 |

---

## Security Groups for Pods

### 개요

Security Groups for Pods는 Pod에 직접 VPC Security Group을 적용하여 네트워크 수준의 격리를 제공합니다.

### 사전 요구사항

```bash
# VPC CNI 버전 확인 (v1.7.7+)
kubectl describe daemonset aws-node -n kube-system | grep Image

# Security Groups for Pods 활성화
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# 노드 IAM 역할에 정책 추가
aws iam attach-role-policy \
    --role-name <node-role-name> \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

### SecurityGroupPolicy 설정

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # 대상 Pod 선택
  podSelector:
    matchLabels:
      app: database
  # 적용할 Security Group
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # 데이터베이스 SG
      - sg-0987654321fedcba0  # 공통 모니터링 SG
```

### Terraform으로 Security Group 구성

```hcl
# 데이터베이스 Pod용 Security Group
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for database pods"

  # PostgreSQL 접근 (App pods에서만)
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_pods.id]
    description     = "PostgreSQL from app pods"
  }

  # 모니터링 접근
  ingress {
    from_port       = 9187
    to_port         = 9187
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring.id]
    description     = "Postgres exporter metrics"
  }

  # 복제 트래픽
  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    self      = true
    description = "Replication between database pods"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "database-pods-sg"
  }
}

# SecurityGroupPolicy
resource "kubernetes_manifest" "database_sg_policy" {
  manifest = {
    apiVersion = "vpcresources.k8s.aws/v1beta1"
    kind       = "SecurityGroupPolicy"
    metadata = {
      name      = "database-sg-policy"
      namespace = "production"
    }
    spec = {
      podSelector = {
        matchLabels = {
          app = "database"
        }
      }
      securityGroups = {
        groupIds = [aws_security_group.database_pods.id]
      }
    }
  }
}
```

---

## VPC 엔드포인트

### 프라이빗 EKS를 위한 VPC 엔드포인트

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EKS VPC 엔드포인트 구성                               │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         VPC                                       │  │
│  │                                                                   │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │  │
│  │  │  Private    │    │  Private    │    │  Private    │          │  │
│  │  │  Subnet A   │    │  Subnet B   │    │  Subnet C   │          │  │
│  │  │             │    │             │    │             │          │  │
│  │  │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │          │  │
│  │  │ │  Node   │ │    │ │  Node   │ │    │ │  Node   │ │          │  │
│  │  │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │          │  │
│  │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘          │  │
│  │         │                  │                  │                  │  │
│  │         └──────────────────┼──────────────────┘                  │  │
│  │                            │                                     │  │
│  │                            ▼                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────┐│  │
│  │  │                   VPC Endpoints                              ││  │
│  │  │  • com.amazonaws.region.eks                                  ││  │
│  │  │  • com.amazonaws.region.ecr.api                              ││  │
│  │  │  • com.amazonaws.region.ecr.dkr                              ││  │
│  │  │  • com.amazonaws.region.s3 (Gateway)                         ││  │
│  │  │  • com.amazonaws.region.sts                                  ││  │
│  │  │  • com.amazonaws.region.logs                                 ││  │
│  │  │  • com.amazonaws.region.elasticloadbalancing                 ││  │
│  │  └─────────────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Terraform VPC 엔드포인트 설정

```hcl
# Interface 엔드포인트
locals {
  interface_endpoints = [
    "com.amazonaws.${var.region}.eks",
    "com.amazonaws.${var.region}.ecr.api",
    "com.amazonaws.${var.region}.ecr.dkr",
    "com.amazonaws.${var.region}.sts",
    "com.amazonaws.${var.region}.logs",
    "com.amazonaws.${var.region}.elasticloadbalancing",
    "com.amazonaws.${var.region}.autoscaling",
    "com.amazonaws.${var.region}.ssm",
    "com.amazonaws.${var.region}.ssmmessages",
    "com.amazonaws.${var.region}.ec2messages",
  ]
}

resource "aws_vpc_endpoint" "interface_endpoints" {
  for_each = toset(local.interface_endpoints)

  vpc_id              = module.vpc.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  subnet_ids          = module.vpc.private_subnets
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "vpce-${split(".", each.value)[4]}"
  }
}

# Gateway 엔드포인트 (S3, DynamoDB)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = module.vpc.private_route_table_ids

  tags = {
    Name = "vpce-s3"
  }
}

# VPC 엔드포인트용 Security Group
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "vpc-endpoints-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for VPC endpoints"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
    description = "HTTPS from VPC"
  }

  tags = {
    Name = "vpc-endpoints-sg"
  }
}
```

---

## 컨트롤 플레인 로깅

### EKS 컨트롤 플레인 로그 유형

| 로그 유형 | 설명 | 사용 사례 |
|----------|------|----------|
| **api** | Kubernetes API 서버 로그 | API 호출 추적, 문제 해결 |
| **audit** | Kubernetes 감사 로그 | 보안 감사, 컴플라이언스 |
| **authenticator** | AWS IAM 인증 로그 | 인증 문제 디버깅 |
| **controllerManager** | 컨트롤러 매니저 로그 | 컨트롤러 동작 추적 |
| **scheduler** | 스케줄러 로그 | Pod 스케줄링 문제 해결 |

### 로깅 활성화

```bash
# AWS CLI로 로깅 활성화
aws eks update-cluster-config \
    --name my-cluster \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

```hcl
# Terraform으로 로깅 설정
resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  vpc_config {
    subnet_ids              = module.vpc.private_subnets
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
}
```

### CloudWatch Logs Insights 쿼리

```sql
-- 실패한 인증 시도 찾기
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error/
| sort @timestamp desc
| limit 100

-- 특정 사용자의 API 호출 추적
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "admin"
| sort @timestamp desc
| limit 50

-- 권한 거부된 요청
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100

-- Secret 접근 감사
fields @timestamp, user.username, verb, requestURI
| filter @logStream like /audit/
| filter requestURI like /secrets/
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection

### GuardDuty EKS Protection 개요

Amazon GuardDuty EKS Protection은 EKS 클러스터에서 악성 활동과 비정상적인 동작을 탐지합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GuardDuty EKS Protection                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    탐지 영역                                     │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ EKS Audit   │  │  Runtime    │  │  VPC Flow   │             │   │
│  │  │    Logs     │  │ Monitoring  │  │    Logs     │             │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │   │
│  │         │                │                │                     │   │
│  │         └────────────────┼────────────────┘                     │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │              ┌───────────────────────┐                         │   │
│  │              │    GuardDuty ML       │                         │   │
│  │              │    위협 탐지 엔진      │                         │   │
│  │              └───────────┬───────────┘                         │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │              ┌───────────────────────┐                         │   │
│  │              │      Findings         │                         │   │
│  │              │   (보안 이벤트)        │                         │   │
│  │              └───────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### GuardDuty 활성화

```bash
# GuardDuty 활성화
aws guardduty create-detector --enable

# EKS Protection 활성화
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

aws guardduty update-detector \
    --detector-id $DETECTOR_ID \
    --features '[
        {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
        {"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED",
         "AdditionalConfiguration": [
            {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
         ]
        }
    ]'
```

### GuardDuty EKS Finding 유형

| Finding 유형 | 설명 | 심각도 |
|-------------|------|--------|
| `Kubernetes:MaliciousIPCaller.Custom` | 알려진 악성 IP에서 API 호출 | High |
| `Kubernetes:SuccessfulAnonymousAccess` | 익명 사용자의 성공적인 API 호출 | Medium |
| `Kubernetes:PrivilegedContainer` | 특권 컨테이너 생성 | Medium |
| `Kubernetes:AnomalousBehavior.PermissionChecked` | 비정상적인 권한 확인 | Low |
| `Runtime:Cryptocurrency.CoinMiner` | 암호화폐 채굴 활동 | High |
| `Runtime:ReverseShell` | 리버스 셸 연결 | Critical |
| `Runtime:Execution.Suspicious` | 의심스러운 프로세스 실행 | Medium |

### Finding 대응 자동화

```yaml
# EventBridge Rule
Resources:
  GuardDutyEKSRule:
    Type: AWS::Events::Rule
    Properties:
      Name: guardduty-eks-findings
      EventPattern:
        source:
          - aws.guardduty
        detail-type:
          - GuardDuty Finding
        detail:
          type:
            - prefix: Kubernetes
            - prefix: Runtime
      Targets:
        - Id: SNSTarget
          Arn: !Ref GuardDutyAlertTopic
        - Id: LambdaTarget
          Arn: !GetAtt GuardDutyResponseFunction.Arn

  GuardDutyResponseFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: guardduty-eks-response
      Runtime: python3.11
      Handler: index.handler
      Code:
        ZipFile: |
          import boto3
          import json

          def handler(event, context):
              finding = event['detail']
              severity = finding['severity']

              if severity >= 7:  # High severity
                  # 자동 대응: Pod 격리
                  eks = boto3.client('eks')
                  # 추가 대응 로직...

              return {'statusCode': 200}
```

---

## Amazon Inspector

### Inspector 컨테이너 이미지 스캔

```bash
# ECR 향상된 스캔 활성화
aws ecr put-registry-scanning-configuration \
    --scan-type ENHANCED \
    --rules '[
        {
            "repositoryFilters": [{"filter": "*", "filterType": "WILDCARD"}],
            "scanFrequency": "CONTINUOUS_SCAN"
        }
    ]'

# 스캔 결과 조회
aws ecr describe-image-scan-findings \
    --repository-name my-app \
    --image-id imageTag=latest
```

### Inspector와 CI/CD 통합

```yaml
# GitHub Actions 예시
name: Build and Scan

on:
  push:
    branches: [main]

jobs:
  build-scan-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: ap-northeast-2

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        run: |
          docker build -t $ECR_REGISTRY/my-app:${{ github.sha }} .
          docker push $ECR_REGISTRY/my-app:${{ github.sha }}

      - name: Wait for Inspector scan
        run: |
          sleep 60  # Inspector가 스캔을 완료할 때까지 대기

      - name: Check scan results
        run: |
          FINDINGS=$(aws ecr describe-image-scan-findings \
            --repository-name my-app \
            --image-id imageTag=${{ github.sha }} \
            --query 'imageScanFindings.findingSeverityCounts')

          CRITICAL=$(echo $FINDINGS | jq '.CRITICAL // 0')
          HIGH=$(echo $FINDINGS | jq '.HIGH // 0')

          if [ "$CRITICAL" -gt 0 ] || [ "$HIGH" -gt 5 ]; then
            echo "Security scan failed: CRITICAL=$CRITICAL, HIGH=$HIGH"
            exit 1
          fi
```

---

## CIS Kubernetes Benchmark

### kube-bench 실행

```bash
# kube-bench를 Job으로 실행
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: kube-bench
  namespace: kube-system
spec:
  template:
    spec:
      hostPID: true
      containers:
      - name: kube-bench
        image: aquasec/kube-bench:latest
        command: ["kube-bench", "--benchmark", "eks-1.4.0"]
        volumeMounts:
        - name: var-lib-kubelet
          mountPath: /var/lib/kubelet
          readOnly: true
        - name: etc-systemd
          mountPath: /etc/systemd
          readOnly: true
        - name: etc-kubernetes
          mountPath: /etc/kubernetes
          readOnly: true
      restartPolicy: Never
      volumes:
      - name: var-lib-kubelet
        hostPath:
          path: /var/lib/kubelet
      - name: etc-systemd
        hostPath:
          path: /etc/systemd
      - name: etc-kubernetes
        hostPath:
          path: /etc/kubernetes
EOF

# 결과 확인
kubectl logs job/kube-bench -n kube-system
```

### CIS 벤치마크 주요 항목

| 섹션 | 설명 | EKS 관련성 |
|------|------|-----------|
| 1. Control Plane | API 서버, etcd 등 | AWS 관리 |
| 2. etcd | etcd 보안 | AWS 관리 |
| 3. Control Plane Configuration | 컨트롤러, 스케줄러 | AWS 관리 |
| 4. Worker Nodes | 노드 설정 | **사용자 책임** |
| 5. Policies | RBAC, PSP/PSS, 네트워크 | **사용자 책임** |

### 자동화된 준수 검사

```yaml
# CronJob으로 정기 검사
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cis-benchmark-scan
  namespace: security
spec:
  schedule: "0 2 * * 0"  # 매주 일요일 02:00
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: cis-scanner
          containers:
          - name: kube-bench
            image: aquasec/kube-bench:latest
            command:
            - /bin/sh
            - -c
            - |
              kube-bench --benchmark eks-1.4.0 --json > /tmp/results.json
              # 결과를 S3에 업로드
              aws s3 cp /tmp/results.json s3://security-reports/cis-benchmark/$(date +%Y-%m-%d).json
          restartPolicy: OnFailure
```

---

## 클러스터 암호화

### EKS Secrets 암호화 (KMS)

```bash
# KMS 키 생성
aws kms create-key \
    --description "EKS Secrets Encryption Key" \
    --key-usage ENCRYPT_DECRYPT

# 클러스터 생성 시 암호화 설정
aws eks create-cluster \
    --name my-cluster \
    --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
    --resources-vpc-config subnetIds=subnet-xxx,subnet-yyy \
    --encryption-config '[{
        "resources": ["secrets"],
        "provider": {
            "keyArn": "arn:aws:kms:ap-northeast-2:123456789012:key/xxx-xxx"
        }
    }]'
```

```hcl
# Terraform 설정
resource "aws_kms_key" "eks_secrets" {
  description             = "EKS Secrets Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM policies"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_eks_cluster" "main" {
  name     = "my-cluster"
  role_arn = aws_iam_role.cluster.arn

  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = aws_kms_key.eks_secrets.arn
    }
  }

  # ... 기타 설정
}
```

---

## 노드 보안

### Bottlerocket OS

```hcl
# Bottlerocket 노드 그룹
resource "aws_eks_node_group" "bottlerocket" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "bottlerocket-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = module.vpc.private_subnets

  ami_type       = "BOTTLEROCKET_x86_64"
  instance_types = ["m5.large"]

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 1
  }

  # Bottlerocket 설정
  launch_template {
    id      = aws_launch_template.bottlerocket.id
    version = aws_launch_template.bottlerocket.latest_version
  }
}

resource "aws_launch_template" "bottlerocket" {
  name_prefix = "bottlerocket-"

  user_data = base64encode(<<-EOF
    [settings.kubernetes]
    cluster-name = "${aws_eks_cluster.main.name}"
    api-server = "${aws_eks_cluster.main.endpoint}"
    cluster-certificate = "${aws_eks_cluster.main.certificate_authority[0].data}"

    [settings.kubernetes.node-labels]
    "node.kubernetes.io/os" = "bottlerocket"

    [settings.kernel.sysctl]
    "net.core.rmem_max" = "16777216"
    "net.core.wmem_max" = "16777216"
  EOF
  )
}
```

### 노드 보안 강화

```yaml
# 노드 레이블 기반 Pod 스케줄링
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  nodeSelector:
    node.kubernetes.io/os: bottlerocket
  tolerations:
  - key: "security"
    operator: "Equal"
    value: "high"
    effect: "NoSchedule"
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      readOnlyRootFilesystem: true
      runAsNonRoot: true
```

---

## 프라이빗 클러스터

### 완전 프라이빗 EKS 구성

```hcl
resource "aws_eks_cluster" "private" {
  name     = "private-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  vpc_config {
    subnet_ids              = module.vpc.private_subnets
    endpoint_private_access = true
    endpoint_public_access  = false  # 퍼블릭 엔드포인트 비활성화
    security_group_ids      = [aws_security_group.cluster.id]
  }

  # 컨트롤 플레인 로깅
  enabled_cluster_log_types = [
    "api", "audit", "authenticator", "controllerManager", "scheduler"
  ]

  # Secrets 암호화
  encryption_config {
    resources = ["secrets"]
    provider {
      key_arn = aws_kms_key.eks.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_cloudwatch_log_group.cluster,
  ]
}
```

### Bastion 또는 VPN 접근

```hcl
# Client VPN 엔드포인트
resource "aws_ec2_client_vpn_endpoint" "eks_access" {
  description            = "EKS Access VPN"
  server_certificate_arn = aws_acm_certificate.vpn.arn
  client_cidr_block      = "10.100.0.0/16"

  authentication_options {
    type                       = "certificate-authentication"
    root_certificate_chain_arn = aws_acm_certificate.vpn_root.arn
  }

  connection_log_options {
    enabled              = true
    cloudwatch_log_group = aws_cloudwatch_log_group.vpn.name
  }

  vpc_id             = module.vpc.vpc_id
  security_group_ids = [aws_security_group.vpn.id]

  split_tunnel = true
}

resource "aws_ec2_client_vpn_network_association" "eks_access" {
  count                  = length(module.vpc.private_subnets)
  client_vpn_endpoint_id = aws_ec2_client_vpn_endpoint.eks_access.id
  subnet_id              = module.vpc.private_subnets[count.index]
}
```

---

## 멀티테넌시 패턴

### 네임스페이스 기반 멀티테넌시

```yaml
---
# 테넌트 네임스페이스
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: tenant-a
    environment: production
    pod-security.kubernetes.io/enforce: restricted
---
# ResourceQuota
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
---
# LimitRange
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-a-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    max:
      cpu: "2"
      memory: 4Gi
    min:
      cpu: 50m
      memory: 64Mi
    type: Container
---
# NetworkPolicy (테넌트 격리)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-isolation
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              tenant: tenant-a
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              tenant: tenant-a
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - port: 53
          protocol: UDP
```

### RBAC 멀티테넌시

```yaml
---
# 테넌트 관리자 역할
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-admin
  namespace: tenant-a
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps", "secrets"]
    verbs: ["*"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["*"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses"]
    verbs: ["*"]
---
# 테넌트 관리자 바인딩
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-admins
  namespace: tenant-a
subjects:
  - kind: Group
    name: tenant-a-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-admin
  apiGroup: rbac.authorization.k8s.io
```

---

## 요약

EKS 보안 모범 사례의 핵심:

1. **IAM 통합**: IRSA 또는 Pod Identity로 AWS 서비스 접근
2. **네트워크 보안**: Security Groups for Pods, VPC 엔드포인트
3. **로깅 및 모니터링**: 컨트롤 플레인 로그, GuardDuty
4. **이미지 보안**: Amazon Inspector, ECR 스캐닝
5. **규정 준수**: CIS Benchmark, kube-bench
6. **암호화**: KMS를 사용한 Secrets 암호화
7. **노드 보안**: Bottlerocket OS, 최소 권한
8. **멀티테넌시**: 네임스페이스 격리, RBAC, ResourceQuota

---

## 참고 자료

- [EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
