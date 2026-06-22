# FinOps 비용 가시성 플랫폼

> **지원 버전**: Kubernetes 1.28+, Kubecost 2.x, OpenCost 1.x
> **마지막 업데이트**: 2026년 4월 25일

< [이전: 이벤트 용량 계획](./12-event-capacity-planning.md) | [목차](./README.md) | [다음: 없음] >

---

## 개요

Kubernetes 환경에서 비용 관리는 단순히 클라우드 청구서를 확인하는 것 이상의 체계적인 접근이 필요합니다. 컨테이너화된 워크로드는 동적으로 스케일링되고, 여러 팀이 공유 인프라를 사용하며, 비용 귀속이 복잡해지기 때문입니다.

**FinOps**(Cloud Financial Operations)는 엔지니어링, 재무, 비즈니스 팀이 협력하여 클라우드 비용을 최적화하는 운영 프레임워크입니다. FinOps의 핵심 사이클은 **Inform(인지) -> Optimize(최적화) -> Operate(운영)**으로 구성됩니다.

이 문서는 Kubernetes 클러스터에 FinOps 원칙을 적용하여 비용 가시성을 확보하고, 팀별 비용 책임을 명확히 하며, 지속적인 비용 최적화를 달성하기 위한 실전 가이드를 제공합니다. OpenCost와 Kubecost를 중심으로 비용 측정 인프라를 구축하고, Showback/Chargeback 체계, 이상 탐지, 셀프서비스 비용 관리까지 포괄합니다.

### 학습 목표

- FinOps 운영 모델과 Inform -> Optimize -> Operate 사이클 이해
- OpenCost/Kubecost를 활용한 Kubernetes 비용 측정 인프라 구축
- Showback/Chargeback 체계를 통한 팀별 비용 귀속 구현
- Prometheus와 Grafana 기반 비용 이상 탐지 및 알림 설정
- 팀 셀프서비스 비용 대시보드 및 Slack 리포트 자동화
- Kyverno 정책을 통한 비용 최적화 거버넌스 적용

---

## 1. FinOps 운영 모델

### 1.1 Inform -> Optimize -> Operate 사이클

FinOps는 반복적인 사이클을 통해 비용 효율성을 지속적으로 개선합니다.

```mermaid
graph LR
    subgraph "FinOps Lifecycle"
        A[Inform<br/>비용 가시성 확보] --> B[Optimize<br/>비용 최적화 실행]
        B --> C[Operate<br/>거버넌스 운영]
        C --> A
    end

    subgraph "Inform 단계"
        A1[비용 할당 및 태깅]
        A2[Showback 리포트]
        A3[비용 이상 탐지]
    end

    subgraph "Optimize 단계"
        B1[리소스 라이트사이징]
        B2[유휴 리소스 제거]
        B3[Spot/Savings Plans 활용]
    end

    subgraph "Operate 단계"
        C1[예산 정책 적용]
        C2[자동화된 워크플로우]
        C3[정기 리뷰 프로세스]
    end

    A --> A1
    A --> A2
    A --> A3
    B --> B1
    B --> B2
    B --> B3
    C --> C1
    C --> C2
    C --> C3
```

| 단계 | 목표 | 주요 활동 | 도구 |
|------|------|----------|------|
| **Inform** | 비용 가시성 확보 | 비용 할당, 태깅, Showback 리포트 생성 | OpenCost, Kubecost, Grafana |
| **Optimize** | 비용 효율성 개선 | 라이트사이징, 유휴 리소스 제거, 할인 활용 | VPA, Goldilocks, Spot Instances |
| **Operate** | 지속 가능한 운영 | 예산 정책, 자동화, 정기 리뷰 | Kyverno, CI/CD, Slack Bot |

### 1.2 조직 역할

| 역할 | 책임 | 주요 활동 |
|------|------|----------|
| **FinOps Team** | 비용 최적화 전략 수립 및 조율 | 비용 할당 정책 설계, 도구 운영, 리뷰 주관 |
| **Engineering** | 리소스 효율적 사용 | 적절한 Requests/Limits 설정, 라이트사이징 적용 |
| **Finance** | 예산 관리 및 예측 | 예산 승인, 비용 예측, 할인 협상 |
| **Leadership** | 의사결정 및 우선순위 | 비용 목표 설정, 투자 대비 효과 평가 |

### 1.3 성숙도 수준

| 수준 | 설명 | 비용 가시성 | 최적화 | 거버넌스 |
|------|------|-----------|--------|---------|
| **Crawl** | 기본 비용 인지 | 클러스터 전체 비용 확인 | 수동 리소스 조정 | 비용 리포트 공유 |
| **Walk** | 팀별 비용 귀속 | Namespace/Label 기반 비용 할당 | VPA 추천 기반 라이트사이징 | 예산 알림 설정 |
| **Run** | 자동화된 비용 최적화 | 실시간 비용 대시보드 + 이상 탐지 | 자동 라이트사이징 + Spot 활용 | 정책 기반 자동 거버넌스 |

---

## 2. OpenCost/Kubecost 심층 구성

### 2.1 OpenCost 설치 (오픈소스)

OpenCost는 CNCF 프로젝트로, Kubernetes 비용을 측정하는 오픈소스 도구입니다. Prometheus와 연동하여 비용 메트릭을 수집합니다.

```yaml
# opencost-values.yaml
# OpenCost Helm Chart 설정
opencost:
  exporter:
    defaultClusterId: "production-eks"
    aws:
      spot_data_region: "ap-northeast-2"
      spot_data_prefix: "spot-data-feed"
      spot_data_bucket: "my-company-spot-feed"
    extraEnv:
      EMIT_KSM_V1_METRICS: "false"
      EMIT_KSM_V1_METRICS_ONLY: "true"
      PROM_CLUSTER_ID_LABEL: "cluster"
      LOG_LEVEL: "info"

    resources:
      requests:
        cpu: "100m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

    persistence:
      enabled: true
      size: "10Gi"
      storageClass: "gp3"

    # Prometheus 연동 설정
    prometheus:
      internal:
        enabled: true
        serviceName: "prometheus-server"
        namespaceName: "monitoring"
        port: 9090
      external:
        enabled: false

  ui:
    enabled: true
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "128Mi"
    ingress:
      enabled: true
      ingressClassName: "alb"
      annotations:
        alb.ingress.kubernetes.io/scheme: "internal"
        alb.ingress.kubernetes.io/target-type: "ip"
        alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
        alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:123456789012:certificate/abc-123"
      hosts:
        - host: "opencost.internal.example.com"
          paths:
            - path: "/"
              pathType: "Prefix"

  metrics:
    serviceMonitor:
      enabled: true
      namespace: "monitoring"
      additionalLabels:
        release: "prometheus"

  networkPolicies:
    enabled: true

  customPricing:
    enabled: true
    configmapName: "opencost-custom-pricing"
    provider: "aws"
```

**설치 명령:**

```bash
# Helm 저장소 추가
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

# 네임스페이스 생성 및 설치
kubectl create namespace opencost
helm install opencost opencost/opencost \
  -n opencost \
  -f opencost-values.yaml \
  --version 1.42.0
```

### 2.2 Kubecost Enterprise

Kubecost Enterprise는 멀티 클러스터 비용 집계, S3 ETL 스토리지, SSO 등 엔터프라이즈 기능을 제공합니다.

```yaml
# kubecost-values.yaml
# Kubecost Enterprise Helm Chart 설정
global:
  prometheus:
    enabled: false  # 기존 Prometheus 사용
    fqdn: "http://prometheus-server.monitoring.svc.cluster.local:9090"

  grafana:
    enabled: false  # 기존 Grafana 사용
    proxy: false

  notifications:
    alertmanager:
      enabled: true
      fqdn: "http://alertmanager.monitoring.svc.cluster.local:9093"

kubecostProductConfigs:
  clusterName: "production-eks"
  currencyCode: "USD"
  defaultModelPricing:
    enabled: true
    CPU: "0.031611"
    RAM: "0.004237"
    storage: "0.000138"
    GPU: "0.95"

  # S3 ETL 스토리지 설정 (장기 비용 데이터 보관)
  etlBucketConfigSecret: "kubecost-etl-bucket"

  # 멀티 클러스터 설정
  federatedETL:
    enabled: true
    primaryCluster: true
    federatedCluster: true
    agentKeySecretName: "kubecost-agent-key"

  # SAML/OIDC SSO 설정
  saml:
    enabled: true
    appRootURL: "https://kubecost.internal.example.com"
    idpMetadataURL: "https://login.example.com/saml/metadata"
    rbac:
      enabled: true
      groups:
        - name: "admin"
          enabled: true
          clusterRoles: "*"
        - name: "team-leads"
          enabled: true
          allClusters: true
        - name: "engineers"
          enabled: true
          allClusters: false

# S3 ETL 스토리지 시크릿
kubecostModel:
  etlBucketConfig:
    region: "ap-northeast-2"
    bucket: "my-company-kubecost-etl"
    path: "etl"

  resources:
    requests:
      cpu: "200m"
      memory: "512Mi"
    limits:
      cpu: "1"
      memory: "2Gi"

  allocation:
    nodeLabels:
      - "team"
      - "environment"
      - "cost-center"

# 프론트엔드 설정
kubecostFrontend:
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "500m"
      memory: "256Mi"

  ingress:
    enabled: true
    className: "alb"
    annotations:
      alb.ingress.kubernetes.io/scheme: "internal"
      alb.ingress.kubernetes.io/target-type: "ip"
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
      alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:123456789012:certificate/abc-123"
    hosts:
      - host: "kubecost.internal.example.com"
        paths:
          - path: "/"
            pathType: "Prefix"

# 네트워크 비용 모니터링
networkCosts:
  enabled: true
  config:
    services:
      amazon-web-services: true
    destinations:
      direct-classification:
        - region: "ap-northeast-2"
          zone: "ap-northeast-2a"

# Prometheus ServiceMonitor
serviceMonitor:
  enabled: true
  namespace: "monitoring"
  additionalLabels:
    release: "prometheus"
```

**설치 명령:**

```bash
# ETL 버킷 시크릿 생성
kubectl create namespace kubecost

kubectl create secret generic kubecost-etl-bucket \
  -n kubecost \
  --from-literal=AWS_ACCESS_KEY_ID="AKIA..." \
  --from-literal=AWS_SECRET_ACCESS_KEY="..." \
  --from-literal=BUCKET_NAME="my-company-kubecost-etl" \
  --from-literal=S3_REGION="ap-northeast-2"

# Kubecost Enterprise 설치
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm repo update

helm install kubecost kubecost/cost-analyzer \
  -n kubecost \
  -f kubecost-values.yaml \
  --version 2.5.0
```

### 2.3 AWS Cost and Usage Report (CUR) 통합

AWS CUR을 Kubecost와 통합하면 실제 AWS 청구 데이터를 기반으로 비용 정확도를 크게 향상시킬 수 있습니다.

**Terraform 인프라 구성:**

```hcl
# cur-infrastructure.tf
# AWS Cost and Usage Report용 S3 버킷 및 IAM 역할

# CUR 데이터 저장용 S3 버킷
resource "aws_s3_bucket" "cur_bucket" {
  bucket = "my-company-cur-data"

  tags = {
    Purpose     = "AWS Cost and Usage Report"
    ManagedBy   = "terraform"
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "cur_bucket_versioning" {
  bucket = aws_s3_bucket.cur_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "cur_bucket_lifecycle" {
  bucket = aws_s3_bucket.cur_bucket.id

  rule {
    id     = "cur-data-lifecycle"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 730
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cur_bucket_sse" {
  bucket = aws_s3_bucket.cur_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cur_bucket_public_access" {
  bucket = aws_s3_bucket.cur_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CUR 데이터 전달을 위한 S3 버킷 정책
resource "aws_s3_bucket_policy" "cur_bucket_policy" {
  bucket = aws_s3_bucket.cur_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCURDelivery"
        Effect = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action = [
          "s3:GetBucketAcl",
          "s3:GetBucketPolicy"
        ]
        Resource = aws_s3_bucket.cur_bucket.arn
        Condition = {
          StringEquals = {
            "aws:SourceArn"    = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AllowCURWrite"
        Effect = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cur_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceArn"    = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# CUR 리포트 정의
resource "aws_cur_report_definition" "cost_report" {
  report_name                = "kubecost-cur-report"
  time_unit                  = "HOURLY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES", "SPLIT_COST_ALLOCATION_DATA"]
  s3_bucket                  = aws_s3_bucket.cur_bucket.bucket
  s3_region                  = "us-east-1"
  s3_prefix                  = "cur-data"
  report_versioning          = "OVERWRITE_REPORT"
  refresh_closed_reports     = true
}

# Kubecost가 CUR 데이터를 읽기 위한 IAM 역할 (IRSA)
resource "aws_iam_role" "kubecost_cur_role" {
  name = "kubecost-cur-reader"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:kubecost:kubecost-cost-analyzer"
            "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "kubecost_cur_policy" {
  name = "kubecost-cur-access"
  role = aws_iam_role.kubecost_cur_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.cur_bucket.arn,
          "${aws_s3_bucket.cur_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = "*"
      }
    ]
  })
}

# Athena 쿼리 결과 저장용 S3 버킷
resource "aws_s3_bucket" "athena_results" {
  bucket = "my-company-athena-results"

  tags = {
    Purpose   = "Athena Query Results"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results_lifecycle" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "cleanup-old-results"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "cluster" {
  name = "production-eks"
}

output "kubecost_role_arn" {
  value       = aws_iam_role.kubecost_cur_role.arn
  description = "Kubecost ServiceAccount에 연결할 IAM Role ARN"
}

output "cur_bucket_name" {
  value       = aws_s3_bucket.cur_bucket.bucket
  description = "CUR 데이터가 저장되는 S3 버킷"
}
```

**Kubecost CUR 통합 설정:**

```yaml
# kubecost-cloud-integration.yaml
# Kubecost values.yaml에 추가할 CUR 통합 설정
kubecostProductConfigs:
  cloudIntegrationSecret: "kubecost-cloud-integration"

  athenaProjectID: "123456789012"
  athenaBucketName: "s3://my-company-athena-results"
  athenaRegion: "us-east-1"
  athenaDatabase: "athenacurcfn_kubecost_cur_report"
  athenaTable: "kubecost_cur_report"
  athenaWorkgroup: "primary"

serviceAccount:
  create: true
  name: "kubecost-cost-analyzer"
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/kubecost-cur-reader"
```

```bash
# Cloud Integration 시크릿 생성
cat <<EOF > cloud-integration.json
{
  "aws": [
    {
      "athenaBucketName": "s3://my-company-athena-results",
      "athenaRegion": "us-east-1",
      "athenaDatabase": "athenacurcfn_kubecost_cur_report",
      "athenaTable": "kubecost_cur_report",
      "athenaWorkgroup": "primary",
      "projectID": "123456789012",
      "serviceKeyName": "",
      "serviceKeySecret": "",
      "masterPayerARN": ""
    }
  ]
}
EOF

kubectl create secret generic kubecost-cloud-integration \
  -n kubecost \
  --from-file=cloud-integration.json
```

### 2.4 비용 정확도 튜닝

기본 비용 모델은 On-Demand 가격을 사용하지만, 실제 협상 가격이나 Savings Plans 할인을 반영해야 정확한 비용을 산출할 수 있습니다.

```yaml
# custom-pricing-configmap.yaml
# 커스텀 가격 설정 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: opencost-custom-pricing
  namespace: opencost
data:
  default.json: |
    {
      "provider": "aws",
      "description": "프로덕션 클러스터 커스텀 가격",
      "regionOverrides": {
        "ap-northeast-2": {
          "cpu": "0.0280",
          "ram": "0.0038",
          "gpu": "0.85",
          "storage": "0.000127"
        }
      },
      "CPU": "0.031611",
      "spotCPU": "0.010537",
      "RAM": "0.004237",
      "spotRAM": "0.001412",
      "GPU": "0.95",
      "storage": "0.000138",
      "zoneNetworkEgress": "0.01",
      "regionNetworkEgress": "0.01",
      "internetNetworkEgress": "0.09",
      "spotLabel": "karpenter.sh/capacity-type",
      "spotLabelValue": "spot"
    }
```

```yaml
# kubecost-shared-cost-config.yaml
# 공유 비용 할당 설정
kubecostProductConfigs:
  # 공유 네임스페이스 비용 분배
  sharedNamespaces: "kube-system,monitoring,istio-system,cert-manager,external-dns"

  # 공유 비용 분배 방법
  sharedOverhead:
    cpu: "2000m"      # 컨트롤 플레인 CPU 오버헤드
    ram: "8Gi"        # 컨트롤 플레인 메모리 오버헤드
    monthly: "500"    # 월간 고정 비용 (관리형 서비스 등)

  # 분배 가중치 (비율 기반)
  shareBy: "weighted"  # weighted | even | proportional

  # Idle 비용 할당
  shareTenancyCosts: true
  idleByNode: false

  # 네임스페이스별 할인 적용
  discount:
    defaultDiscount: "0.25"  # Savings Plans 25% 할인 기본 적용
    negotiatedDiscount:
      - namespace: "production"
        discount: "0.30"    # 프로덕션은 30% 할인 (Reserved Instance)
      - namespace: "staging"
        discount: "0.20"    # 스테이징은 20% 할인

  # 라벨 기반 비용 집계
  labelMappingConfigs:
    enabled: true
    owner_label: "team"
    product_label: "service"
    environment_label: "environment"
    department_label: "cost-center"
```

---

## 3. Showback/Chargeback 구현

### 3.1 레이블 전략

효과적인 비용 귀속을 위해 모든 워크로드에 표준화된 레이블을 적용해야 합니다.

**필수 레이블:**

| 레이블 | 설명 | 예시 값 |
|--------|------|--------|
| `team` | 소유 팀 | `platform`, `backend`, `frontend`, `data` |
| `service` | 서비스 이름 | `api-gateway`, `user-service`, `payment` |
| `environment` | 환경 구분 | `production`, `staging`, `development` |
| `cost-center` | 비용 센터 코드 | `CC-1001`, `CC-2001`, `CC-3001` |

**Kyverno 레이블 강제 정책:**

```yaml
# kyverno-cost-labels-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-cost-labels
  annotations:
    policies.kyverno.io/title: 비용 관련 필수 레이블 강제
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: high
    policies.kyverno.io/subject: Deployment
    policies.kyverno.io/description: >-
      모든 Deployment에 비용 귀속을 위한 필수 레이블(team, service,
      environment, cost-center)을 요구합니다.
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-cost-labels-on-deployment
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!kyverno"
      validate:
        message: >-
          Deployment에 필수 비용 레이블이 누락되었습니다.
          다음 레이블을 모두 포함해야 합니다:
          team, service, environment, cost-center.
          누락된 레이블: {{request.object.metadata.labels}}
        pattern:
          metadata:
            labels:
              team: "?*"
              service: "?*"
              environment: "?*"
              cost-center: "?*"
    - name: check-cost-labels-on-pod-template
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!kyverno"
      validate:
        message: >-
          Deployment의 Pod template에도 비용 레이블을 포함해야 합니다.
          Pod 레벨 메트릭 수집에 필요합니다.
        pattern:
          spec:
            template:
              metadata:
                labels:
                  team: "?*"
                  service: "?*"
                  environment: "?*"
                  cost-center: "?*"
    - name: validate-cost-center-format
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!kyverno"
      validate:
        message: >-
          cost-center 레이블은 'CC-' 접두사와 4자리 숫자 형식이어야 합니다.
          예: CC-1001
        pattern:
          metadata:
            labels:
              cost-center: "CC-????"
```

### 3.2 Namespace 기반 비용 할당

**Kubecost Allocation API 활용:**

```bash
# 팀별 월간 비용 조회
curl -s "http://kubecost.internal.example.com/model/allocation" \
  --data-urlencode 'window=month' \
  --data-urlencode 'aggregate=label:team' \
  --data-urlencode 'idle=true' \
  --data-urlencode 'shareIdle=weighted' \
  | jq '.data[0] | to_entries[] | {
      team: .key,
      totalCost: (.value.totalCost | round),
      cpuCost: (.value.cpuCost | round),
      ramCost: (.value.ramCost | round),
      pvCost: (.value.pvCost | round),
      networkCost: (.value.networkCost | round)
    }'

# 네임스페이스별 일일 비용 추이 (최근 7일)
curl -s "http://kubecost.internal.example.com/model/allocation" \
  --data-urlencode 'window=7d' \
  --data-urlencode 'aggregate=namespace' \
  --data-urlencode 'accumulate=false' \
  --data-urlencode 'idle=true' \
  | jq '.data[] | to_entries[] | {
      namespace: .key,
      date: .value.start,
      totalCost: (.value.totalCost | round)
    }'

# 특정 팀의 서비스별 비용 상세 조회
curl -s "http://kubecost.internal.example.com/model/allocation" \
  --data-urlencode 'window=lastweek' \
  --data-urlencode 'aggregate=label:service' \
  --data-urlencode 'filterLabels=team:backend' \
  --data-urlencode 'idle=false' \
  | jq '.data[0] | to_entries | sort_by(-.value.totalCost) | .[:10] | .[] | {
      service: .key,
      totalCost: (.value.totalCost * 100 | round / 100),
      cpuEfficiency: ((.value.cpuEfficiency // 0) * 100 | round),
      ramEfficiency: ((.value.ramEfficiency // 0) * 100 | round)
    }'
```

**팀 네임스페이스 ResourceQuota:**

```yaml
# team-resource-quotas.yaml
# backend 팀 프로덕션 네임스페이스 쿼터
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-backend-quota
  namespace: backend-production
  labels:
    team: "backend"
    cost-center: "CC-2001"
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    persistentvolumeclaims: "20"
    requests.storage: "200Gi"
    pods: "100"
    services: "30"
    services.loadbalancers: "3"
---
# frontend 팀 프로덕션 네임스페이스 쿼터
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-frontend-quota
  namespace: frontend-production
  labels:
    team: "frontend"
    cost-center: "CC-2002"
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    persistentvolumeclaims: "10"
    requests.storage: "100Gi"
    pods: "60"
    services: "20"
    services.loadbalancers: "2"
---
# data 팀 프로덕션 네임스페이스 쿼터
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-data-quota
  namespace: data-production
  labels:
    team: "data"
    cost-center: "CC-3001"
spec:
  hard:
    requests.cpu: "40"
    requests.memory: "160Gi"
    limits.cpu: "80"
    limits.memory: "320Gi"
    persistentvolumeclaims: "30"
    requests.storage: "1Ti"
    pods: "150"
    services: "20"
    services.loadbalancers: "2"
```

### 3.3 공유 비용 분배

클러스터에는 특정 팀에 귀속되지 않는 공유 비용이 존재합니다. 이를 공정하게 분배하는 전략이 필요합니다.

```mermaid
graph TD
    A[총 클러스터 비용] --> B[직접 비용<br/>팀 워크로드]
    A --> C[공유 비용]

    C --> D[컨트롤 플레인<br/>EKS 관리 비용]
    C --> E[공유 인프라<br/>Monitoring, Ingress]
    C --> F[네트워크 비용<br/>NAT Gateway, LB]
    C --> G[유휴 리소스<br/>미사용 할당량]

    D --> H{분배 방법}
    E --> H
    F --> H
    G --> H

    H --> I[균등 분배<br/>팀 수로 나눔]
    H --> J[비례 분배<br/>리소스 사용 비율]
    H --> K[가중 분배<br/>커스텀 가중치]
```

**공유 비용 분배 유형:**

| 비용 유형 | 분배 방법 | 근거 |
|----------|----------|------|
| EKS Control Plane ($73/월) | 균등 분배 | 모든 팀이 동등하게 사용 |
| Monitoring Stack | CPU/Memory 비례 | 메트릭 양에 비례 |
| Ingress Controller | 트래픽 비례 | 요청 수에 비례 |
| NAT Gateway | 아웃바운드 비례 | 외부 트래픽에 비례 |
| 유휴 리소스 | CPU/Memory 비례 | 할당량에 비례하여 책임 |

```yaml
# kubecost-shared-costs.yaml
# Kubecost 공유 비용 분배 상세 설정
kubecostProductConfigs:
  sharedCosts:
    # 컨트롤 플레인 비용 - 균등 분배
    - name: "EKS Control Plane"
      type: "recurring"
      monthly: "73.00"
      allocation: "even"

    # 모니터링 스택 - 비례 분배
    - name: "Monitoring Infrastructure"
      type: "namespace"
      namespaces:
        - "monitoring"
        - "logging"
      allocation: "proportional"

    # Ingress / Load Balancer 비용 - 비례 분배
    - name: "Ingress Infrastructure"
      type: "namespace"
      namespaces:
        - "ingress-nginx"
        - "external-dns"
      allocation: "proportional"

    # 보안 인프라 - 균등 분배
    - name: "Security Infrastructure"
      type: "namespace"
      namespaces:
        - "cert-manager"
        - "kyverno"
        - "falco"
      allocation: "even"

    # NAT Gateway 비용 - 비례 분배
    - name: "NAT Gateway"
      type: "recurring"
      monthly: "150.00"
      allocation: "proportional"
```

### 3.4 Grafana Showback 대시보드

팀별/서비스별 비용을 시각화하는 Grafana 대시보드 설정입니다.

```json
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "panels": [
    {
      "title": "Total Monthly Cost by Team",
      "type": "barchart",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": { "h": 10, "w": 12, "x": 0, "y": 0 },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 1000 },
              { "color": "red", "value": 5000 }
            ]
          }
        },
        "overrides": []
      },
      "options": {
        "orientation": "horizontal",
        "showValue": "always",
        "barWidth": 0.7,
        "groupWidth": 0.7
      },
      "targets": [
        {
          "expr": "sum by (label_team) (avg_over_time(kubecost_cluster_costs{cluster=\"production-eks\"}[30d]) * 730)",
          "legendFormat": "{{label_team}}",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Daily Cost Trend by Team",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": { "h": 10, "w": 12, "x": 12, "y": 0 },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "custom": {
            "drawStyle": "line",
            "lineWidth": 2,
            "fillOpacity": 15,
            "pointSize": 5,
            "stacking": { "mode": "normal" }
          }
        },
        "overrides": []
      },
      "options": {
        "legend": { "displayMode": "table", "placement": "bottom", "calcs": ["sum", "mean"] },
        "tooltip": { "mode": "multi" }
      },
      "targets": [
        {
          "expr": "sum by (label_team) (kubecost_namespace_daily_cost{cluster=\"production-eks\"})",
          "legendFormat": "{{label_team}}",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Cost per Service (Top 15)",
      "type": "table",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": { "h": 12, "w": 12, "x": 0, "y": 10 },
      "fieldConfig": {
        "defaults": {},
        "overrides": [
          {
            "matcher": { "id": "byName", "options": "Total Cost" },
            "properties": [{ "id": "unit", "value": "currencyUSD" }]
          },
          {
            "matcher": { "id": "byName", "options": "CPU Efficiency" },
            "properties": [
              { "id": "unit", "value": "percentunit" },
              { "id": "thresholds", "value": {
                "mode": "absolute",
                "steps": [
                  { "color": "red", "value": null },
                  { "color": "yellow", "value": 0.4 },
                  { "color": "green", "value": 0.65 }
                ]
              }}
            ]
          }
        ]
      },
      "options": {
        "sortBy": [{ "displayName": "Total Cost", "desc": true }],
        "showHeader": true
      },
      "targets": [
        {
          "expr": "topk(15, sum by (label_service) (avg_over_time(kubecost_namespace_costs{cluster=\"production-eks\"}[30d]) * 730))",
          "format": "table",
          "legendFormat": "",
          "refId": "A",
          "instant": true
        }
      ],
      "transformations": [
        {
          "id": "organize",
          "options": {
            "renameByName": {
              "label_service": "Service",
              "Value": "Total Cost"
            }
          }
        }
      ]
    },
    {
      "title": "Resource Efficiency by Namespace",
      "type": "gauge",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": { "h": 6, "w": 12, "x": 12, "y": 10 },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": null },
              { "color": "orange", "value": 0.3 },
              { "color": "yellow", "value": 0.5 },
              { "color": "green", "value": 0.65 }
            ]
          }
        },
        "overrides": []
      },
      "options": {
        "showThresholdLabels": false,
        "showThresholdMarkers": true,
        "orientation": "auto"
      },
      "targets": [
        {
          "expr": "avg by (namespace) (kubecost_container_cpu_usage / kubecost_container_cpu_request)",
          "legendFormat": "{{namespace}}",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Cost Breakdown (CPU / Memory / Storage / Network)",
      "type": "piechart",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "gridPos": { "h": 6, "w": 12, "x": 12, "y": 16 },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD"
        },
        "overrides": []
      },
      "options": {
        "legend": { "displayMode": "table", "placement": "right", "values": ["value", "percent"] },
        "pieType": "donut",
        "reduceOptions": { "calcs": ["lastNotNull"] }
      },
      "targets": [
        {
          "expr": "sum(kubecost_cluster_cpu_cost{cluster=\"production-eks\"}) * 730",
          "legendFormat": "CPU",
          "refId": "A"
        },
        {
          "expr": "sum(kubecost_cluster_ram_cost{cluster=\"production-eks\"}) * 730",
          "legendFormat": "Memory",
          "refId": "B"
        },
        {
          "expr": "sum(kubecost_cluster_pv_cost{cluster=\"production-eks\"}) * 730",
          "legendFormat": "Storage",
          "refId": "C"
        },
        {
          "expr": "sum(kubecost_cluster_network_cost{cluster=\"production-eks\"}) * 730",
          "legendFormat": "Network",
          "refId": "D"
        }
      ]
    }
  ],
  "refresh": "5m",
  "schemaVersion": 39,
  "tags": ["finops", "cost", "kubecost"],
  "templating": {
    "list": [
      {
        "name": "cluster",
        "type": "query",
        "datasource": { "type": "prometheus", "uid": "prometheus" },
        "query": "label_values(kubecost_cluster_costs, cluster)",
        "current": { "text": "production-eks", "value": "production-eks" },
        "refresh": 2
      },
      {
        "name": "team",
        "type": "query",
        "datasource": { "type": "prometheus", "uid": "prometheus" },
        "query": "label_values(kube_pod_labels{cluster=\"$cluster\"}, label_team)",
        "includeAll": true,
        "multi": true,
        "refresh": 2
      }
    ]
  },
  "time": { "from": "now-30d", "to": "now" },
  "timepicker": {},
  "timezone": "Asia/Seoul",
  "title": "FinOps - Team Cost Showback",
  "uid": "finops-showback-001",
  "version": 1
}
```

---

## 4. 비용 이상 탐지

### 4.1 Kubecost 알림 구성

Kubecost의 내장 알림 기능을 활용하여 비용 이상을 탐지합니다.

```yaml
# kubecost-alerts-values.yaml
# Kubecost Helm values에 추가할 알림 설정
kubecostProductConfigs:
  alerts:
    # 일일 예산 초과 알림
    - type: budget
      threshold: 150         # 일일 $150 초과 시
      window: daily
      aggregation: cluster
      filter: ""
      ownerContact:
        - "finops-team@example.com"
        - "slack:finops-alerts"

    # 팀별 주간 예산 초과
    - type: budget
      threshold: 500         # 주간 $500 초과 시
      window: weekly
      aggregation: label:team
      filter: ""
      ownerContact:
        - "finops-team@example.com"

    # 비용 급증 알림 (전주 대비 30% 이상 증가)
    - type: recurringUpdate
      threshold: 0.30        # 30% 증가 시
      window: weekly
      aggregation: namespace
      filter: ""
      ownerContact:
        - "finops-team@example.com"
        - "slack:finops-alerts"

    # 리소스 효율성 저하 알림
    - type: efficiency
      threshold: 0.40        # 효율성 40% 미만
      window: 48h
      aggregation: label:team
      filter: ""
      ownerContact:
        - "finops-team@example.com"

    # Spot Instance 중단 비용 영향
    - type: recurringUpdate
      threshold: 0.50        # 비용 50% 이상 변동
      window: daily
      aggregation: label:karpenter.sh/capacity-type
      filter: "spot"
      ownerContact:
        - "platform-team@example.com"

    # 새로운 고비용 워크로드 탐지
    - type: budget
      threshold: 50          # 일일 $50 초과하는 새 워크로드
      window: daily
      aggregation: controller
      filter: ""
      ownerContact:
        - "finops-team@example.com"

  # Slack Webhook 연동
  notifications:
    slack:
      enabled: true
      webhookURL: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
      channel: "#finops-alerts"
      username: "Kubecost Alert"
    email:
      enabled: true
      smtpHost: "smtp.example.com"
      smtpPort: 587
      smtpUsername: "alerts@example.com"
      smtpPasswordSecret: "kubecost-smtp-secret"
      fromAddress: "kubecost@example.com"
```

### 4.2 Prometheus 기반 비용 알림

Prometheus 규칙을 사용하여 더 세밀한 비용 이상 탐지를 구현합니다.

```yaml
# cost-anomaly-prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-anomaly-detection
  namespace: monitoring
  labels:
    release: prometheus
    app: kube-prometheus-stack
spec:
  groups:
    - name: cost-anomaly-alerts
      interval: 5m
      rules:
        # 일일 클러스터 비용이 평균 대비 2배 이상 증가
        - alert: ClusterCostSpike
          expr: |
            (
              sum(kubecost_cluster_costs) * 24
            ) > 2 * (
              avg_over_time(sum(kubecost_cluster_costs)[7d:1h]) * 24
            )
          for: 30m
          labels:
            severity: critical
            team: finops
            category: cost
          annotations:
            summary: "클러스터 일일 비용 급증 감지"
            description: |
              현재 일일 예상 비용: ${{ $value | printf "%.2f" }}
              최근 7일 평균 대비 2배 이상 증가했습니다.
            runbook_url: "https://wiki.example.com/runbook/cost-spike"

        # 네임스페이스 비용이 전주 대비 50% 이상 증가
        - alert: NamespaceCostIncrease
          expr: |
            (
              sum by (namespace) (kubecost_namespace_daily_cost) -
              sum by (namespace) (kubecost_namespace_daily_cost offset 7d)
            ) / sum by (namespace) (kubecost_namespace_daily_cost offset 7d) > 0.5
          for: 1h
          labels:
            severity: warning
            team: finops
            category: cost
          annotations:
            summary: "네임스페이스 {{ $labels.namespace }} 비용 50% 이상 증가"
            description: |
              네임스페이스 {{ $labels.namespace }}의 일일 비용이 전주 대비
              {{ $value | humanizePercentage }} 증가했습니다.

        # CPU 리소스 효율성 30% 미만
        - alert: LowCPUEfficiency
          expr: |
            (
              sum by (namespace) (rate(container_cpu_usage_seconds_total{namespace!~"kube-system|monitoring|istio-system"}[1h]))
              /
              sum by (namespace) (kube_pod_container_resource_requests{resource="cpu", namespace!~"kube-system|monitoring|istio-system"})
            ) < 0.3
          for: 6h
          labels:
            severity: warning
            team: finops
            category: efficiency
          annotations:
            summary: "네임스페이스 {{ $labels.namespace }} CPU 효율성 30% 미만"
            description: |
              CPU 사용률이 요청량의 {{ $value | humanizePercentage }}입니다.
              리소스 라이트사이징을 검토하세요.

        # 메모리 리소스 효율성 30% 미만
        - alert: LowMemoryEfficiency
          expr: |
            (
              sum by (namespace) (container_memory_working_set_bytes{namespace!~"kube-system|monitoring|istio-system"})
              /
              sum by (namespace) (kube_pod_container_resource_requests{resource="memory", namespace!~"kube-system|monitoring|istio-system"})
            ) < 0.3
          for: 6h
          labels:
            severity: warning
            team: finops
            category: efficiency
          annotations:
            summary: "네임스페이스 {{ $labels.namespace }} 메모리 효율성 30% 미만"
            description: |
              메모리 사용률이 요청량의 {{ $value | humanizePercentage }}입니다.
              리소스 라이트사이징을 검토하세요.

        # PVC 사용률 10% 미만 (유휴 스토리지)
        - alert: UnderutilizedPVC
          expr: |
            (
              kubelet_volume_stats_used_bytes
              /
              kubelet_volume_stats_capacity_bytes
            ) < 0.1
          for: 24h
          labels:
            severity: info
            team: finops
            category: waste
          annotations:
            summary: "PVC {{ $labels.persistentvolumeclaim }} 사용률 10% 미만"
            description: |
              네임스페이스 {{ $labels.namespace }}의 PVC {{ $labels.persistentvolumeclaim }}
              사용률: {{ $value | humanizePercentage }}. 축소 또는 삭제를 검토하세요.

        # 예상 월간 비용이 예산 초과
        - alert: MonthlyBudgetExceeded
          expr: |
            (sum(kubecost_cluster_costs) * 730) > 10000
          for: 2h
          labels:
            severity: critical
            team: finops
            category: budget
          annotations:
            summary: "예상 월간 비용이 예산($10,000)을 초과합니다"
            description: |
              현재 추세 기반 예상 월간 비용: ${{ $value | printf "%.0f" }}
              즉시 비용 리뷰를 진행하세요.
```

**Alertmanager 라우팅 설정:**

```yaml
# alertmanager-cost-routes.yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: cost-alert-routing
  namespace: monitoring
  labels:
    release: prometheus
spec:
  route:
    groupBy: ["category", "namespace"]
    groupWait: "30s"
    groupInterval: "5m"
    repeatInterval: "4h"
    receiver: "finops-slack"
    routes:
      - match:
          severity: critical
          category: cost
        receiver: "finops-slack-critical"
        repeatInterval: "1h"
      - match:
          severity: critical
          category: budget
        receiver: "finops-slack-critical"
        repeatInterval: "2h"
      - match:
          severity: warning
          category: cost
        receiver: "finops-slack"
        repeatInterval: "6h"
      - match:
          category: efficiency
        receiver: "finops-slack"
        repeatInterval: "12h"
      - match:
          category: waste
        receiver: "finops-slack"
        repeatInterval: "24h"

  receivers:
    - name: "finops-slack"
      slackConfigs:
        - apiURL:
            name: "slack-webhook-secret"
            key: "webhook-url"
          channel: "#finops-alerts"
          sendResolved: true
          title: |
            [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
          text: |
            *Alert:* {{ .CommonAnnotations.summary }}
            *Description:* {{ .CommonAnnotations.description }}
            *Severity:* {{ .CommonLabels.severity }}
            *Namespace:* {{ .CommonLabels.namespace }}
          actions:
            - type: "button"
              text: "Runbook"
              url: "{{ .CommonAnnotations.runbook_url }}"
            - type: "button"
              text: "Kubecost Dashboard"
              url: "https://kubecost.internal.example.com"

    - name: "finops-slack-critical"
      slackConfigs:
        - apiURL:
            name: "slack-webhook-secret"
            key: "webhook-url"
          channel: "#finops-critical"
          sendResolved: true
          title: |
            :rotating_light: [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
          text: |
            *CRITICAL COST ALERT*
            *Alert:* {{ .CommonAnnotations.summary }}
            *Description:* {{ .CommonAnnotations.description }}
            *Action Required:* 즉시 확인이 필요합니다.
          actions:
            - type: "button"
              text: "Runbook"
              url: "{{ .CommonAnnotations.runbook_url }}"
            - type: "button"
              text: "Kubecost Dashboard"
              url: "https://kubecost.internal.example.com"
```

### 4.3 AWS Cost Anomaly Detection 통합

AWS Cost Anomaly Detection은 ML 기반으로 AWS 비용 이상을 자동 탐지합니다. Kubecost와 별도로 AWS 레벨에서 추가 안전망을 제공합니다.

```bash
# AWS Cost Anomaly Detection 모니터 생성
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "EKS-Cost-Monitor",
    "MonitorType": "DIMENSIONAL",
    "MonitorDimension": "SERVICE",
    "MonitorSpecification": {
      "AND": null,
      "CostCategories": null,
      "Dimensions": {
        "Key": "SERVICE",
        "MatchOptions": ["EQUALS"],
        "Values": ["Amazon Elastic Kubernetes Service", "Amazon EC2", "Amazon ECR"]
      },
      "NOT": null,
      "OR": null,
      "Tags": null
    }
  }'

# SNS 토픽을 통한 알림 구독 생성
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "EKS-Cost-Alerts",
    "MonitorArnList": ["arn:aws:ce::123456789012:anomalymonitor/monitor-id"],
    "Subscribers": [
      {
        "Address": "arn:aws:sns:ap-northeast-2:123456789012:finops-alerts",
        "Type": "SNS"
      }
    ],
    "Threshold": 50.0,
    "Frequency": "DAILY",
    "ThresholdExpression": {
      "Dimensions": {
        "Key": "ANOMALY_TOTAL_IMPACT_ABSOLUTE",
        "MatchOptions": ["GREATER_THAN_OR_EQUAL"],
        "Values": ["50"]
      }
    }
  }'
```

---

## 5. 팀 셀프서비스 비용 관리

### 5.1 팀별 비용 대시보드

각 팀이 자신의 비용을 독립적으로 모니터링할 수 있는 Grafana 대시보드를 제공합니다. Grafana 변수를 활용하여 팀을 선택하면 해당 팀의 비용만 필터링됩니다.

```yaml
# grafana-team-dashboard-provisioning.yaml
# Grafana 대시보드 프로비저닝 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-team-cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  team-cost-dashboard.json: |
    {
      "title": "My Team Cost Dashboard",
      "uid": "team-cost-self-service",
      "tags": ["finops", "self-service"],
      "templating": {
        "list": [
          {
            "name": "team",
            "type": "query",
            "datasource": { "type": "prometheus", "uid": "prometheus" },
            "query": "label_values(kube_pod_labels, label_team)",
            "current": {},
            "refresh": 2,
            "sort": 1
          },
          {
            "name": "period",
            "type": "custom",
            "options": [
              {"text": "Last 7 Days", "value": "7d"},
              {"text": "Last 30 Days", "value": "30d"},
              {"text": "Last 90 Days", "value": "90d"}
            ],
            "current": {"text": "Last 30 Days", "value": "30d"}
          }
        ]
      },
      "panels": [
        {
          "title": "Current Month Estimated Cost",
          "type": "stat",
          "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
          "targets": [{
            "expr": "sum(kubecost_namespace_daily_cost{label_team=\"$team\"}) * 30",
            "legendFormat": "Monthly Estimate"
          }],
          "fieldConfig": {
            "defaults": {
              "unit": "currencyUSD",
              "thresholds": {
                "steps": [
                  {"color": "green", "value": null},
                  {"color": "yellow", "value": 1000},
                  {"color": "red", "value": 3000}
                ]
              }
            }
          }
        },
        {
          "title": "Cost Trend",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 18, "x": 6, "y": 0},
          "targets": [{
            "expr": "sum by (label_service) (kubecost_namespace_daily_cost{label_team=\"$team\"})",
            "legendFormat": "{{label_service}}"
          }],
          "fieldConfig": {
            "defaults": {
              "unit": "currencyUSD",
              "custom": {"drawStyle": "line", "fillOpacity": 20, "stacking": {"mode": "normal"}}
            }
          }
        },
        {
          "title": "Budget Remaining",
          "type": "gauge",
          "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
          "targets": [{
            "expr": "1 - (sum(kubecost_namespace_daily_cost{label_team=\"$team\"}) * 30) / kubecost_team_budget{team=\"$team\"}",
            "legendFormat": "Budget Remaining"
          }],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0, "max": 1,
              "thresholds": {
                "steps": [
                  {"color": "red", "value": null},
                  {"color": "yellow", "value": 0.2},
                  {"color": "green", "value": 0.5}
                ]
              }
            }
          }
        }
      ],
      "time": {"from": "now-$period", "to": "now"},
      "schemaVersion": 39
    }
```

### 5.2 Slack 비용 리포트 봇

매주 월요일 아침에 각 팀의 비용 요약을 Slack으로 자동 전송하는 CronJob입니다.

```yaml
# cost-report-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-cost-report
  namespace: kubecost
  labels:
    app: cost-report-bot
    team: finops
spec:
  schedule: "0 9 * * 1"  # 매주 월요일 09:00 KST
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 3
      activeDeadlineSeconds: 300
      template:
        metadata:
          labels:
            app: cost-report-bot
        spec:
          serviceAccountName: cost-report-bot
          restartPolicy: OnFailure
          containers:
            - name: cost-reporter
              image: curlimages/curl:8.7.1
              command: ["/bin/sh", "-c"]
              args:
                - |
                  #!/bin/sh
                  set -e

                  KUBECOST_URL="http://kubecost-cost-analyzer.kubecost.svc.cluster.local:9090"
                  SLACK_WEBHOOK="${SLACK_WEBHOOK_URL}"

                  echo "=== Weekly Cost Report Generator ==="
                  echo "Kubecost URL: ${KUBECOST_URL}"

                  # 팀별 주간 비용 조회
                  TEAM_COSTS=$(curl -sf "${KUBECOST_URL}/model/allocation" \
                    --data-urlencode 'window=lastweek' \
                    --data-urlencode 'aggregate=label:team' \
                    --data-urlencode 'idle=true' \
                    --data-urlencode 'shareIdle=weighted')

                  if [ -z "${TEAM_COSTS}" ]; then
                    echo "ERROR: Failed to fetch cost data"
                    exit 1
                  fi

                  # 전체 주간 비용 계산
                  TOTAL_WEEKLY=$(echo "${TEAM_COSTS}" | \
                    jq '[.data[0] | to_entries[].value.totalCost] | add | round')

                  # 전주 대비 변화율
                  PREV_COSTS=$(curl -sf "${KUBECOST_URL}/model/allocation" \
                    --data-urlencode 'window=2d ago,9d ago' \
                    --data-urlencode 'aggregate=cluster' \
                    --data-urlencode 'idle=true')

                  PREV_TOTAL=$(echo "${PREV_COSTS}" | \
                    jq '[.data[0] | to_entries[].value.totalCost] | add | round')

                  if [ "${PREV_TOTAL}" -gt 0 ] 2>/dev/null; then
                    CHANGE_PCT=$(echo "scale=1; (${TOTAL_WEEKLY} - ${PREV_TOTAL}) * 100 / ${PREV_TOTAL}" | bc)
                  else
                    CHANGE_PCT="N/A"
                  fi

                  # 팀별 비용 테이블 생성
                  TEAM_TABLE=$(echo "${TEAM_COSTS}" | jq -r '
                    .data[0] | to_entries
                    | sort_by(-.value.totalCost)
                    | .[]
                    | "| " + .key + " | $" + (.value.totalCost | round | tostring) +
                      " | " + ((.value.cpuEfficiency // 0) * 100 | round | tostring) + "%" +
                      " | " + ((.value.ramEfficiency // 0) * 100 | round | tostring) + "% |"
                  ')

                  # 월간 예상 비용
                  MONTHLY_ESTIMATE=$(echo "scale=0; ${TOTAL_WEEKLY} * 4.33 / 1" | bc)

                  # Slack 메시지 전송
                  PAYLOAD=$(cat <<EOFPAYLOAD
                  {
                    "blocks": [
                      {
                        "type": "header",
                        "text": {
                          "type": "plain_text",
                          "text": "Weekly Kubernetes Cost Report"
                        }
                      },
                      {
                        "type": "section",
                        "fields": [
                          {"type": "mrkdwn", "text": "*Total Weekly Cost:*\n\$${TOTAL_WEEKLY}"},
                          {"type": "mrkdwn", "text": "*Week-over-Week:*\n${CHANGE_PCT}%"},
                          {"type": "mrkdwn", "text": "*Monthly Estimate:*\n\$${MONTHLY_ESTIMATE}"},
                          {"type": "mrkdwn", "text": "*Report Period:*\nLast 7 Days"}
                        ]
                      },
                      {
                        "type": "divider"
                      },
                      {
                        "type": "section",
                        "text": {
                          "type": "mrkdwn",
                          "text": "*Team Cost Breakdown:*\n| Team | Cost | CPU Eff | RAM Eff |\n|------|------|---------|---------|${TEAM_TABLE}"
                        }
                      },
                      {
                        "type": "actions",
                        "elements": [
                          {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Kubecost"},
                            "url": "https://kubecost.internal.example.com"
                          },
                          {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Grafana"},
                            "url": "https://grafana.internal.example.com/d/finops-showback-001"
                          }
                        ]
                      }
                    ]
                  }
                  EOFPAYLOAD
                  )

                  curl -sf -X POST "${SLACK_WEBHOOK}" \
                    -H "Content-Type: application/json" \
                    -d "${PAYLOAD}"

                  echo "Cost report sent successfully"
              env:
                - name: SLACK_WEBHOOK_URL
                  valueFrom:
                    secretKeyRef:
                      name: slack-webhook-secret
                      key: webhook-url
              resources:
                requests:
                  cpu: "50m"
                  memory: "64Mi"
                limits:
                  cpu: "200m"
                  memory: "128Mi"
```

### 5.3 비용 예산 설정 및 알림

팀별 월간 예산을 설정하고, 임계값 도달 시 자동으로 알림을 보냅니다.

```yaml
# team-budget-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: team-budgets
  namespace: kubecost
  labels:
    app: cost-management
data:
  budgets.json: |
    {
      "budgets": [
        {
          "team": "backend",
          "namespace": "backend-production",
          "monthlyBudget": 3000,
          "alertThresholds": [0.50, 0.75, 0.90, 1.00],
          "contacts": {
            "slack": "#backend-team",
            "email": "backend-leads@example.com"
          }
        },
        {
          "team": "frontend",
          "namespace": "frontend-production",
          "monthlyBudget": 1500,
          "alertThresholds": [0.50, 0.75, 0.90, 1.00],
          "contacts": {
            "slack": "#frontend-team",
            "email": "frontend-leads@example.com"
          }
        },
        {
          "team": "data",
          "namespace": "data-production",
          "monthlyBudget": 5000,
          "alertThresholds": [0.50, 0.75, 0.90, 1.00],
          "contacts": {
            "slack": "#data-team",
            "email": "data-leads@example.com"
          }
        },
        {
          "team": "platform",
          "namespace": "platform-production",
          "monthlyBudget": 2000,
          "alertThresholds": [0.50, 0.75, 0.90, 1.00],
          "contacts": {
            "slack": "#platform-team",
            "email": "platform-leads@example.com"
          }
        }
      ]
    }
---
# budget-alert-prometheus-rule.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: team-budget-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
    - name: team-budget-alerts
      rules:
        # 각 팀의 예산 소진률 메트릭
        - record: team:monthly_cost_ratio:budget
          expr: |
            (
              sum by (label_team) (kubecost_namespace_daily_cost) * 30
            ) / on(label_team) group_left() kubecost_team_budget

        # 예산 75% 도달 경고
        - alert: TeamBudget75Percent
          expr: team:monthly_cost_ratio:budget > 0.75
          for: 1h
          labels:
            severity: warning
            category: budget
          annotations:
            summary: "팀 {{ $labels.label_team }} 월간 예산 75% 도달"
            description: |
              팀 {{ $labels.label_team }}의 예상 월간 비용이 예산의
              {{ $value | humanizePercentage }}에 도달했습니다.
              비용 최적화를 검토하세요.

        # 예산 90% 도달 심각 경고
        - alert: TeamBudget90Percent
          expr: team:monthly_cost_ratio:budget > 0.90
          for: 1h
          labels:
            severity: critical
            category: budget
          annotations:
            summary: "팀 {{ $labels.label_team }} 월간 예산 90% 도달"
            description: |
              팀 {{ $labels.label_team }}의 예상 월간 비용이 예산의
              {{ $value | humanizePercentage }}에 도달했습니다.
              즉시 조치가 필요합니다.

        # 예산 초과
        - alert: TeamBudgetExceeded
          expr: team:monthly_cost_ratio:budget > 1.0
          for: 30m
          labels:
            severity: critical
            category: budget
          annotations:
            summary: "팀 {{ $labels.label_team }} 월간 예산 초과!"
            description: |
              팀 {{ $labels.label_team }}의 예상 월간 비용이 예산을
              {{ $value | humanizePercentage }} 초과했습니다.
              비용 리뷰 미팅을 즉시 소집하세요.
```

---

## 6. 리소스 라이트사이징 자동화

### 6.1 VPA 추천 워크플로우

VPA(Vertical Pod Autoscaler)를 `Off` 모드로 설정하면 실제로 리소스를 변경하지 않고 추천값만 제공합니다.

```yaml
# vpa-recommendation-only.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-gateway-vpa
  namespace: backend-production
  labels:
    team: backend
    service: api-gateway
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  updatePolicy:
    updateMode: "Off"  # 추천만 제공, 자동 적용 안 함
  resourcePolicy:
    containerPolicies:
      - containerName: api-gateway
        minAllowed:
          cpu: "100m"
          memory: "128Mi"
        maxAllowed:
          cpu: "4"
          memory: "8Gi"
        controlledResources: ["cpu", "memory"]
        controlledValues: RequestsAndLimits
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: user-service-vpa
  namespace: backend-production
  labels:
    team: backend
    service: user-service
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: user-service
        minAllowed:
          cpu: "50m"
          memory: "64Mi"
        maxAllowed:
          cpu: "2"
          memory: "4Gi"
        controlledResources: ["cpu", "memory"]
        controlledValues: RequestsAndLimits
```

**VPA 추천 확인:**

```bash
# VPA 추천값 조회
kubectl get vpa api-gateway-vpa -n backend-production -o jsonpath='{.status.recommendation}' | jq .

# 모든 VPA 추천 요약
kubectl get vpa -A -o custom-columns=\
'NAMESPACE:.metadata.namespace,'\
'NAME:.metadata.name,'\
'TARGET:.spec.targetRef.name,'\
'CPU_REQ:.status.recommendation.containerRecommendations[0].target.cpu,'\
'MEM_REQ:.status.recommendation.containerRecommendations[0].target.memory,'\
'CPU_LOWER:.status.recommendation.containerRecommendations[0].lowerBound.cpu,'\
'MEM_LOWER:.status.recommendation.containerRecommendations[0].lowerBound.memory,'\
'CPU_UPPER:.status.recommendation.containerRecommendations[0].upperBound.cpu,'\
'MEM_UPPER:.status.recommendation.containerRecommendations[0].upperBound.memory'
```

### 6.2 Goldilocks 대시보드

Goldilocks는 VPA 추천을 웹 대시보드로 시각화하여 팀이 직접 적절한 리소스 설정을 확인할 수 있게 합니다.

```yaml
# goldilocks-values.yaml
dashboard:
  enabled: true
  replicaCount: 2
  resources:
    requests:
      cpu: "50m"
      memory: "64Mi"
    limits:
      cpu: "200m"
      memory: "128Mi"

  ingress:
    enabled: true
    ingressClassName: "alb"
    annotations:
      alb.ingress.kubernetes.io/scheme: "internal"
      alb.ingress.kubernetes.io/target-type: "ip"
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    hosts:
      - host: "goldilocks.internal.example.com"
        paths:
          - path: "/"
            pathType: "Prefix"

controller:
  enabled: true
  resources:
    requests:
      cpu: "50m"
      memory: "64Mi"
    limits:
      cpu: "200m"
      memory: "128Mi"

  # VPA 자동 생성 설정
  flags:
    on-by-default: false
    exclude-containers: "istio-proxy,linkerd-proxy"

vpa:
  enabled: true
  updater:
    enabled: false  # Updater 비활성화 (추천만 사용)
```

**Goldilocks 모니터링 대상 네임스페이스 설정:**

```bash
# 네임스페이스에 Goldilocks 레이블 추가 (모니터링 활성화)
kubectl label namespace backend-production goldilocks.fairwinds.com/enabled=true
kubectl label namespace frontend-production goldilocks.fairwinds.com/enabled=true
kubectl label namespace data-production goldilocks.fairwinds.com/enabled=true

# Goldilocks 설치
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm repo update

helm install goldilocks fairwinds-stable/goldilocks \
  -n goldilocks --create-namespace \
  -f goldilocks-values.yaml

# 모니터링 상태 확인
kubectl get vpa -A | grep goldilocks
```

### 6.3 자동 리소스 조정 파이프라인

VPA 추천을 기반으로 자동으로 PR을 생성하고, 리뷰 후 적용하는 CI/CD 파이프라인입니다.

```mermaid
graph LR
    A[VPA<br/>추천 수집] --> B[추천값 분석<br/>임계값 비교]
    B --> C{변경 필요?}
    C -->|Yes| D[매니페스트<br/>자동 수정]
    C -->|No| E[스킵]
    D --> F[PR 생성]
    F --> G[팀 리뷰]
    G --> H{승인?}
    H -->|Yes| I[자동 배포]
    H -->|No| J[의견 반영]
    J --> D
```

```yaml
# rightsizing-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vpa-rightsizing-pr
  namespace: platform-tools
  labels:
    app: vpa-rightsizing
spec:
  schedule: "0 2 * * 3"  # 매주 수요일 02:00
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 600
      template:
        spec:
          serviceAccountName: vpa-rightsizing-bot
          restartPolicy: OnFailure
          containers:
            - name: rightsizing-bot
              image: bitnami/kubectl:1.30
              command: ["/bin/bash", "-c"]
              args:
                - |
                  #!/bin/bash
                  set -euo pipefail

                  echo "=== VPA Rightsizing PR Generator ==="

                  THRESHOLD=0.20  # 20% 이상 차이가 나면 PR 생성
                  CHANGES_FOUND=false
                  REPORT=""

                  # 모든 VPA 추천 수집
                  for vpa in $(kubectl get vpa -A -o json | jq -r '.items[] | select(.status.recommendation != null) | "\(.metadata.namespace)/\(.metadata.name)"'); do
                    NS=$(echo "$vpa" | cut -d'/' -f1)
                    NAME=$(echo "$vpa" | cut -d'/' -f2)

                    # 현재 설정값과 추천값 비교
                    TARGET_REF=$(kubectl get vpa "$NAME" -n "$NS" -o jsonpath='{.spec.targetRef.name}')
                    TARGET_KIND=$(kubectl get vpa "$NAME" -n "$NS" -o jsonpath='{.spec.targetRef.kind}')

                    CURRENT_CPU=$(kubectl get "$TARGET_KIND" "$TARGET_REF" -n "$NS" \
                      -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}' 2>/dev/null || echo "0")
                    RECOMMENDED_CPU=$(kubectl get vpa "$NAME" -n "$NS" \
                      -o jsonpath='{.status.recommendation.containerRecommendations[0].target.cpu}' 2>/dev/null || echo "0")

                    CURRENT_MEM=$(kubectl get "$TARGET_KIND" "$TARGET_REF" -n "$NS" \
                      -o jsonpath='{.spec.template.spec.containers[0].resources.requests.memory}' 2>/dev/null || echo "0")
                    RECOMMENDED_MEM=$(kubectl get vpa "$NAME" -n "$NS" \
                      -o jsonpath='{.status.recommendation.containerRecommendations[0].target.memory}' 2>/dev/null || echo "0")

                    REPORT="${REPORT}\n| ${NS} | ${TARGET_REF} | ${CURRENT_CPU} -> ${RECOMMENDED_CPU} | ${CURRENT_MEM} -> ${RECOMMENDED_MEM} |"
                    CHANGES_FOUND=true
                  done

                  if [ "$CHANGES_FOUND" = true ]; then
                    echo -e "Rightsizing recommendations:\n${REPORT}"
                    # 실제 환경에서는 여기서 Git clone -> manifest 수정 -> PR 생성
                    echo "PR creation would happen here via GitHub API"
                  else
                    echo "No significant rightsizing changes needed"
                  fi
              resources:
                requests:
                  cpu: "100m"
                  memory: "128Mi"
                limits:
                  cpu: "500m"
                  memory: "256Mi"
```

---

## 7. 비용 최적화 거버넌스

### 7.1 유휴 리소스 자동 탐지

PromQL 쿼리를 사용하여 유휴 또는 과다 프로비저닝된 리소스를 탐지합니다.

**유휴 Deployment 탐지 (CPU 사용률 5% 미만):**

```promql
# 최근 24시간 동안 CPU 사용률이 5% 미만인 Deployment
sum by (namespace, deployment) (
  rate(container_cpu_usage_seconds_total{
    namespace!~"kube-system|monitoring|istio-system|kyverno",
    container!=""
  }[24h])
)
/
sum by (namespace, deployment) (
  kube_pod_container_resource_requests{
    resource="cpu",
    namespace!~"kube-system|monitoring|istio-system|kyverno"
  }
) < 0.05
```

**유휴 메모리 탐지 (사용률 20% 미만):**

```promql
# 최근 24시간 동안 메모리 사용률이 20% 미만인 Pod
sum by (namespace, pod) (
  avg_over_time(container_memory_working_set_bytes{
    namespace!~"kube-system|monitoring|istio-system",
    container!=""
  }[24h])
)
/
sum by (namespace, pod) (
  kube_pod_container_resource_requests{
    resource="memory",
    namespace!~"kube-system|monitoring|istio-system"
  }
) < 0.20
```

**스케일-투-제로 후보 (복제본은 있지만 트래픽 없음):**

```promql
# 최근 6시간 동안 수신 요청이 없는 Deployment
sum by (namespace, deployment) (
  rate(http_requests_total{
    namespace!~"kube-system|monitoring"
  }[6h])
) == 0
and
sum by (namespace, deployment) (
  kube_deployment_spec_replicas{
    namespace!~"kube-system|monitoring"
  }
) > 0
```

**미사용 PersistentVolumeClaim 탐지:**

```promql
# 어떤 Pod에도 마운트되지 않은 PVC
kube_persistentvolumeclaim_info
unless on (namespace, persistentvolumeclaim) (
  kube_pod_spec_volumes_persistentvolumeclaims_info
)
```

### 7.2 비용 정책 (Kyverno)

**리소스 Limits 필수 정책:**

```yaml
# kyverno-require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: 리소스 Limits 필수
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: high
    policies.kyverno.io/description: >-
      모든 컨테이너에 CPU와 메모리 리소스 requests 및 limits를 설정해야 합니다.
      리소스 제한 없이 배포하면 비용 예측이 불가능하고 다른 워크로드에 영향을 줄 수 있습니다.
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: validate-resources
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!kyverno"
      validate:
        message: >-
          모든 컨테이너에 resources.requests와 resources.limits를 설정해야 합니다.
          CPU와 메모리 모두 지정해야 합니다.
          컨테이너: {{request.object.spec.containers[*].name}}
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                any:
                  - key: "{{ element.resources.requests.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.requests.memory || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.limits.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.limits.memory || '' }}"
                    operator: Equals
                    value: ""
```

**과다 프로비저닝 경고 정책:**

```yaml
# kyverno-warn-over-provisioned.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: warn-over-provisioned-resources
  annotations:
    policies.kyverno.io/title: 과다 프로비저닝 경고
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: medium
    policies.kyverno.io/description: >-
      단일 컨테이너에 과도한 리소스를 요청하면 경고합니다.
      CPU 4코어 또는 메모리 8Gi를 초과하는 요청은 검토가 필요합니다.
spec:
  validationFailureAction: Audit  # 경고만 (차단하지 않음)
  background: true
  rules:
    - name: check-cpu-over-provisioning
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - "!kube-system"
                - "!monitoring"
      validate:
        message: >-
          CPU requests가 4코어를 초과합니다 (현재: {{ request.object.spec.containers[0].resources.requests.cpu }}).
          이 수준의 리소스가 정말 필요한지 확인하세요.
          VPA 추천을 참고하여 적절한 값으로 조정하세요.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ regex_match('^[0-9]+$', element.resources.requests.cpu || '0') }}"
                    operator: Equals
                    value: true
                  - key: "{{ to_number(element.resources.requests.cpu || '0') }}"
                    operator: GreaterThan
                    value: 4
    - name: check-memory-over-provisioning
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - "!kube-system"
                - "!monitoring"
      validate:
        message: >-
          메모리 requests가 8Gi를 초과합니다.
          이 수준의 리소스가 정말 필요한지 확인하세요.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ regex_match('.*Gi$', element.resources.requests.memory || '0Mi') }}"
                    operator: Equals
                    value: true
                  - key: "{{ to_number(regex_replace_all('Gi', element.resources.requests.memory || '0Gi', '')) }}"
                    operator: GreaterThan
                    value: 8
    - name: warn-limits-too-high-ratio
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!monitoring"
      validate:
        message: >-
          CPU limits가 requests의 5배를 초과합니다.
          Limits/Requests 비율이 너무 크면 노드 과부하의 원인이 됩니다.
          적절한 비율(2-3x)로 조정하세요.
        pattern:
          spec:
            template:
              spec:
                containers:
                  - resources:
                      requests:
                        cpu: "?*"
                      limits:
                        cpu: "?*"
```

### 7.3 정기 비용 리뷰 프로세스

| 주기 | 참석자 | 안건 | 산출물 |
|------|--------|------|--------|
| **주간** (30분) | FinOps + 팀 리드 | 주간 비용 트렌드, 이상 항목 검토, 긴급 최적화 항목 | 주간 비용 리포트, 액션 아이템 |
| **월간** (1시간) | FinOps + Engineering + Finance | 월간 비용 대비 예산, 팀별 비용 리뷰, 최적화 성과 | 월간 비용 리포트, 다음 달 예산 |
| **분기** (2시간) | FinOps + Leadership | 분기 비용 추이, RI/SP 구매 검토, 비용 목표 재설정 | 분기 비용 보고서, 전략 업데이트 |

**월간 비용 리뷰 템플릿:**

```
## 월간 Kubernetes 비용 리뷰 - [YYYY년 MM월]

### 1. 비용 요약
| 항목 | 이번 달 | 지난 달 | 변화율 | 예산 대비 |
|------|---------|---------|--------|----------|
| 총 비용 | $X,XXX | $X,XXX | +X% | X% |
| CPU 비용 | $X,XXX | $X,XXX | +X% | - |
| 메모리 비용 | $X,XXX | $X,XXX | +X% | - |
| 스토리지 비용 | $XXX | $XXX | +X% | - |
| 네트워크 비용 | $XXX | $XXX | +X% | - |

### 2. 팀별 비용
| 팀 | 비용 | 예산 | 소진률 | CPU 효율 | 메모리 효율 |
|----|------|------|--------|---------|-----------|
| backend | $X,XXX | $X,XXX | X% | X% | X% |
| frontend | $X,XXX | $X,XXX | X% | X% | X% |
| data | $X,XXX | $X,XXX | X% | X% | X% |

### 3. 주요 변동 사항
- [변동 사항 1]
- [변동 사항 2]

### 4. 최적화 성과
- [성과 1: 라이트사이징으로 월 $XXX 절감]
- [성과 2: 유휴 리소스 제거로 월 $XXX 절감]

### 5. 다음 달 액션 아이템
- [ ] [액션 1]
- [ ] [액션 2]
- [ ] [액션 3]
```

---

## 8. 베스트 프랙티스

### 핵심 원칙

1. **Day 1부터 비용 레이블 적용**: 나중에 레이블을 추가하는 것은 매우 어렵습니다. 초기부터 Kyverno 정책으로 필수 레이블(team, service, environment, cost-center)을 강제하세요. 레이블 없는 리소스가 누적되면 비용 귀속이 불가능해집니다.

2. **Requests = 실제 사용량, Limits = 피크 사용량 기준**: CPU requests는 P50 사용량, limits는 P99 사용량을 기준으로 설정하세요. 메모리 requests는 정상 운영 시 사용량, limits는 최대 사용량 + 여유분(20%)으로 설정합니다. VPA 추천을 참고하되 맹목적으로 따르지 마세요.

3. **공유 비용을 무시하지 말 것**: 모니터링, 네트워킹, 컨트롤 플레인 비용은 전체 비용의 15-30%를 차지할 수 있습니다. 이를 공정하게 분배하지 않으면 팀별 비용 비교가 왜곡됩니다. 분배 방법(균등/비례/가중)을 명확히 정의하세요.

4. **효율성과 안정성의 균형**: 리소스 효율성 100%를 목표로 하지 마세요. 65-80% 효율성이 현실적인 목표입니다. 과도한 최적화는 서비스 안정성을 해칩니다. 프로덕션 환경에서는 안전 마진(20-30%)을 항상 유지하세요.

5. **셀프서비스 도구 제공**: FinOps 팀이 모든 최적화를 직접 수행할 수 없습니다. Goldilocks 대시보드, 팀별 Grafana 대시보드, Slack 비용 리포트 등 셀프서비스 도구를 제공하여 각 팀이 자율적으로 비용을 관리하도록 하세요.

6. **비용 리뷰를 문화로 정착**: 주간/월간 비용 리뷰를 정기적으로 실시하고, 비용 절감 성과를 공유하세요. 비용 의식이 엔지니어링 문화에 내재화되어야 지속적인 최적화가 가능합니다.

7. **CUR 통합으로 비용 정확도 확보**: OpenCost/Kubecost의 기본 가격 모델은 On-Demand 기준입니다. AWS CUR과 통합하면 실제 청구 가격(Savings Plans, Reserved Instance 할인 포함)을 반영하여 비용 정확도를 높일 수 있습니다.

8. **점진적으로 성숙도 향상**: Crawl(기본 비용 확인) -> Walk(팀별 비용 귀속) -> Run(자동화된 최적화) 단계로 점진적으로 발전하세요. 처음부터 모든 것을 자동화하려 하면 복잡성만 증가합니다.

### 안티패턴

| 안티패턴 | 문제 | 해결 방법 |
|---------|------|----------|
| **레이블 없는 배포 허용** | 비용 귀속 불가, "미분류" 비용 증가 | Kyverno 정책으로 필수 레이블 강제 |
| **리소스 Limits 미설정** | 비용 예측 불가, 노이지 네이버 문제 | Admission Controller로 Limits 필수 적용 |
| **월 1회 청구서만 확인** | 이상 비용 발견 지연, 사후 대응만 가능 | 일일 비용 모니터링 + 실시간 이상 탐지 |
| **모든 최적화를 FinOps 팀이 수행** | 병목 현상, 팀 자율성 저하 | 셀프서비스 도구 + 팀 예산 책임제 |

---

## 9. 참고 자료

### 외부 자료

- [OpenCost Documentation](https://www.opencost.io/docs/)
- [Kubecost Documentation](https://docs.kubecost.com/)
- [AWS Cost and Usage Report Guide](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)
- [FinOps Foundation Framework](https://www.finops.org/framework/)
- [FinOps for Kubernetes](https://www.finops.org/wg/containers-kubernetes/)
- [CNCF FinOps Landscape](https://landscape.finops.org/)
- [Goldilocks Documentation](https://goldilocks.docs.fairwinds.com/)

### 내부 참고 문서

- [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) - EKS 특화 비용 최적화 전략
- [리소스 최적화](./10-resource-optimization.md) - Requests/Limits 설정, VPA/HPA 활용
- [스케일링 전략](./06-scaling-strategies.md) - HPA, KEDA, Karpenter 기반 스케일링
- [이벤트 용량 계획](./12-event-capacity-planning.md) - 이벤트 기반 용량 계획 및 비용 예측
