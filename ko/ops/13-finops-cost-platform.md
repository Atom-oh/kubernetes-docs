# FinOps 비용 가시성 플랫폼

> **지원 버전**: Kubernetes 1.28+, Kubecost 2.x, OpenCost 1.x
> **마지막 업데이트**: 2026년 4월 25일

< [이전: 이벤트 용량 계획](./12-event-capacity-planning.md) | [목차](./README.md) | [다음: 없음] >

---

## 개요

Kubernetes 환경에서 컨테이너화된 워크로드가 증가하면 비용 구조는 점점 복잡해집니다. 전통적인 VM 기반 환경에서는 서버 단위로 비용을 추적할 수 있었지만, Kubernetes에서는 하나의 노드에 여러 팀의 워크로드가 동시에 실행되므로 **비용 귀속(cost attribution)**이 어려워집니다.

FinOps는 클라우드 비용을 엔지니어링 조직이 주도적으로 관리하는 운영 프레임워크입니다. 단순히 비용을 절감하는 것이 아니라, **비용에 대한 가시성을 확보하고, 데이터 기반으로 의사결정하며, 지속적으로 최적화하는 문화**를 구축하는 것이 핵심입니다.

이 문서에서는 OpenCost와 Kubecost를 중심으로 Kubernetes 비용 가시성 플랫폼을 구축하고, Showback/Chargeback 체계를 구현하며, 비용 이상 탐지와 셀프서비스 비용 관리를 통해 조직 전체의 비용 효율성을 높이는 방법을 다룹니다.

### 학습 목표

- FinOps 운영 모델(Inform → Optimize → Operate)의 개념과 실무 적용 방법 이해
- OpenCost/Kubecost를 활용한 Kubernetes 비용 모니터링 플랫폼 구축
- AWS Cost and Usage Report(CUR)와 Kubecost 통합으로 정확한 비용 데이터 확보
- Showback/Chargeback 체계 설계 및 팀별 비용 할당 구현
- 비용 이상 탐지 자동화 및 Slack 기반 알림 파이프라인 구성
- 리소스 라이트사이징 자동화를 통한 지속적 비용 최적화 워크플로우 구축

---

## 1. FinOps 운영 모델

FinOps Foundation에서 정의한 FinOps 프레임워크는 세 가지 반복적 단계로 구성됩니다. 이 사이클은 한 번으로 끝나는 것이 아니라, 조직의 성숙도가 높아짐에 따라 점점 정교해지는 **지속적 개선 루프**입니다.

![Inform, Optimize, Operate 세 단계가 순환하며 각 단계의 핵심 활동을 보여주는 FinOps 라이프사이클 흐름도로, 비용 최적화 단계를 중심으로 강조한다.](../.gitbook/assets/ko-ops-13-finops-cost-platform-0.png)

### 1.1 각 단계의 핵심 활동

**Inform (가시성 확보)**

가시성이 없으면 최적화도 불가능합니다. 이 단계에서는 클러스터, 네임스페이스, 워크로드 수준에서 비용을 정확하게 측정하고, 팀별로 귀속시키는 체계를 구축합니다.

- 비용 할당 모델 설계 (Namespace, Label 기반)
- 공유 비용(컨트롤 플레인, 네트워킹 등) 분배 규칙 정의
- 팀별/서비스별 비용 대시보드 구축
- 정기 비용 리포트 자동화

**Optimize (비용 최적화)**

가시성 데이터를 기반으로 실제 비용을 줄이는 단계입니다. 리소스 라이트사이징, Spot Instance 활용, 유휴 리소스 제거 등을 수행합니다.

- VPA 추천 기반 리소스 라이트사이징
- Spot Instance / Savings Plans / Reserved Instance 활용
- 유휴 리소스(미사용 PVC, 비활성 Deployment 등) 자동 탐지 및 정리
- 스토리지 계층 최적화 (EBS 타입, S3 Lifecycle Policy)

**Operate (운영 체계화)**

최적화를 일회성이 아닌 지속적 프로세스로 만드는 단계입니다. 정책, 자동화, 거버넌스를 통해 비용 효율성을 조직 문화에 내재화합니다.

- 비용 예산 설정 및 초과 알림
- 비용 관련 정책 자동 적용 (Kyverno/OPA)
- 주간/월간 비용 리뷰 프로세스 운영
- FinOps 성숙도 측정 및 개선

### 1.2 조직 역할 정의

| 역할 | 책임 | 주요 활동 | 도구/접근 권한 |
|------|------|----------|---------------|
| **FinOps Team** | 비용 가시성 플랫폼 운영, 정책 수립 | 대시보드 구축, 비용 리포트 생성, 최적화 추천 | Kubecost Admin, AWS Cost Explorer, Grafana |
| **Engineering** | 리소스 효율적 사용, 라이트사이징 실행 | VPA 추천 적용, 비용 라벨 준수, 유휴 리소스 정리 | Kubecost Viewer, Grafana 팀 대시보드 |
| **Finance** | 예산 승인, 비용 분석 | 월간 비용 리뷰, 예산 대비 실적 분석, 비용 예측 | Kubecost Viewer, AWS Billing 콘솔 |
| **Leadership** | 비용 문화 주도, 투자 결정 | 분기별 비용 리뷰, ROI 분석, 예산 배분 | 경영진 대시보드, 월간 요약 리포트 |

### 1.3 성숙도 모델

| 단계 | 설명 | Inform | Optimize | Operate |
|------|------|--------|----------|---------|
| **Crawl** | 기초 단계 | 클러스터 수준 비용 확인, 기본 태깅 | 수동 라이트사이징, On-Demand만 사용 | 월간 비용 확인, 임의적 리뷰 |
| **Walk** | 중급 단계 | 네임스페이스별 비용 할당, Showback 리포트 | VPA 추천 활용, Spot 일부 사용 | 주간 비용 리뷰, 기본 예산 설정 |
| **Run** | 고급 단계 | 실시간 비용 대시보드, 자동 Chargeback | 자동 라이트사이징, Spot + RI 최적화 | 정책 자동화, 비용 거버넌스 내재화 |

---

## 2. OpenCost/Kubecost 심층 구성

### 2.1 OpenCost 설치 (오픈소스)

OpenCost는 CNCF 프로젝트로, Kubernetes 비용 모니터링의 오픈소스 표준입니다. Kubecost의 비용 할당 엔진 기반으로 만들어졌으며, 기본적인 비용 가시성을 무료로 제공합니다.

```yaml
# opencost-values.yaml
# OpenCost Helm Chart 설정
# helm repo add opencost https://opencost.github.io/opencost-helm-chart
# helm install opencost opencost/opencost -n opencost --create-namespace -f opencost-values.yaml

opencost:
  # Prometheus 연동 설정
  exporter:
    defaultClusterId: "eks-production"
    image:
      registry: ghcr.io
      repository: opencost/opencost
      tag: "1.112.0"
    resources:
      requests:
        cpu: "100m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
    extraEnv:
      # AWS 비용 데이터 통합
      CLOUD_PROVIDER_API_KEY: ""
      EMIT_KSM_V1_METRICS: "false"
      EMIT_KSM_V1_METRICS_ONLY: "true"
      PROM_CLUSTER_ID_LABEL: "cluster"
      LOG_LEVEL: "info"
    persistence:
      enabled: true
      size: "10Gi"
      storageClass: "gp3"
    # Prometheus 엔드포인트 설정
    prometheus:
      internal:
        enabled: true
        serviceName: "prometheus-server"
        namespaceName: "monitoring"
        port: 9090
      external:
        enabled: false

  # UI 설정
  ui:
    enabled: true
    image:
      registry: ghcr.io
      repository: opencost/opencost-ui
      tag: "1.112.0"
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

  # 커스텀 가격 설정 (AWS ap-northeast-2 기준)
  customPricing:
    enabled: true
    configmapName: "opencost-custom-pricing"
    configPath: "/tmp/custom-config"
    provider: "aws"
    costModel:
      description: "AWS ap-northeast-2 커스텀 가격"
      CPU: "0.0464"          # m6i.xlarge vCPU 시간당 가격 (서울 리전)
      RAM: "0.00580"         # GB 시간당 가격
      GPU: "0.526"           # GPU 시간당 가격
      storage: "0.000127397" # GP3 GB 시간당 가격
      spotCPU: "0.0139"      # Spot vCPU 시간당 가격 (약 70% 할인)
      spotRAM: "0.00174"     # Spot RAM GB 시간당 가격
      zoneNetworkEgress: "0.01"
      regionNetworkEgress: "0.01"
      internetNetworkEgress: "0.09"

# ServiceAccount 설정 (Pod Identity 사용)
serviceAccount:
  create: true
  name: "opencost"
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/opencost-role"
```

### 2.2 Kubecost Enterprise

Kubecost Enterprise는 OpenCost의 상용 확장 버전으로, 멀티 클러스터 연합, S3 ETL 스토리지, SSO, RBAC 등 엔터프라이즈 기능을 제공합니다.

```yaml
# kubecost-values.yaml
# helm repo add kubecost https://kubecost.github.io/cost-analyzer-helm-chart
# helm install kubecost kubecost/cost-analyzer -n kubecost --create-namespace -f kubecost-values.yaml

global:
  prometheus:
    enabled: false  # 외부 Prometheus 사용
    fqdn: "http://prometheus-server.monitoring.svc.cluster.local:9090"
  grafana:
    enabled: false  # 외부 Grafana 사용
    proxy: false
  notifications:
    alertmanager:
      enabled: true
      fqdn: "http://alertmanager.monitoring.svc.cluster.local:9093"

# 비용 분석 엔진 설정
kubecostModel:
  image: "gcr.io/kubecost1/cost-model:2.3.0"
  resources:
    requests:
      cpu: "200m"
      memory: "512Mi"
    limits:
      cpu: "1000m"
      memory: "2Gi"
  # ETL 스토리지 설정 (S3)
  etlBucketConfigSecret: "kubecost-etl-bucket"
  # 멀티 클러스터 설정
  federatedETL:
    enabled: true
    primaryCluster: true  # 이 클러스터가 Primary Hub
    federator:
      enabled: true
      primaryClusterID: "eks-production"
  # 할당 설정
  allocation:
    nodeEnabled: true
    # 공유 비용 설정
    sharedNamespaces: "kube-system,monitoring,istio-system,kubecost"
    sharedOverhead: "500"  # 월 $500 공유 인프라 비용
    shareIdle: true
    shareTenancyCosts: true

# 프론트엔드 설정
kubecostFrontend:
  image: "gcr.io/kubecost1/frontend:2.3.0"
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"
    limits:
      cpu: "500m"
      memory: "512Mi"

# S3 ETL 버킷 설정
kubecostProductConfigs:
  clusterName: "eks-production"
  clusterProfile: "production"
  currencyCode: "USD"
  defaultModelPricing:
    enabled: true
    region: "ap-northeast-2"
    provider: "aws"
  productKey:
    key: ""        # Enterprise 라이선스 키
    enabled: true
  # SAML/OIDC SSO 설정
  saml:
    enabled: true
    idpMetadataURL: "https://sso.example.com/metadata"
    appRootURL: "https://kubecost.internal.example.com"
    rbac:
      enabled: true
      groups:
        - name: "finops-admin"
          enabled: true
          allClusters: true
        - name: "team-platform"
          enabled: true
          clusters:
            - "eks-production"
          namespaces:
            - "platform-*"
        - name: "team-backend"
          enabled: true
          clusters:
            - "eks-production"
          namespaces:
            - "backend-*"

# Ingress 설정
ingress:
  enabled: true
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: "internal"
    alb.ingress.kubernetes.io/target-type: "ip"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:ap-northeast-2:123456789012:certificate/abc-123"
    alb.ingress.kubernetes.io/group.name: "internal"
  hosts:
    - host: "kubecost.internal.example.com"
      paths:
        - path: "/"
          pathType: "Prefix"

# 영구 스토리지
persistentVolume:
  enabled: true
  size: "50Gi"
  storageClass: "gp3"

# ServiceAccount (Pod Identity)
serviceAccount:
  create: true
  name: "kubecost"
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/kubecost-role"

# NetworkPolicy
networkPolicy:
  enabled: true
  costAnalyzer:
    enabled: true
    annotations: {}
    additionalLabels: {}
```

S3 ETL 버킷 Secret은 다음과 같이 생성합니다:

```yaml
# kubecost-etl-bucket-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: kubecost-etl-bucket
  namespace: kubecost
type: Opaque
stringData:
  bucket.json: |
    {
      "bucket": "kubecost-etl-production",
      "region": "ap-northeast-2",
      "path": "etl"
    }
```

### 2.3 AWS Cost and Usage Report (CUR) 통합

Kubecost가 실제 AWS 청구 데이터를 사용하면 비용 정확도가 크게 향상됩니다. EDP 할인, Savings Plans, Reserved Instances 등의 실제 할인율이 반영됩니다.

**Terraform으로 CUR 인프라 구성:**

```hcl
# cur-infrastructure.tf
# AWS Cost and Usage Report + S3 버킷 + IAM 역할 구성

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# CUR용 S3 버킷
resource "aws_s3_bucket" "cur_bucket" {
  bucket = "company-cur-reports-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "CUR Reports Bucket"
    Environment = "production"
    ManagedBy   = "terraform"
    Purpose     = "cost-and-usage-reports"
  }
}

# S3 버킷 버전관리 활성화
resource "aws_s3_bucket_versioning" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 버킷 암호화 설정
resource "aws_s3_bucket_server_side_encryption_configuration" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 수명 주기 정책 (오래된 CUR 데이터 자동 정리)
resource "aws_s3_bucket_lifecycle_configuration" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id

  rule {
    id     = "cur-lifecycle"
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
      days = 730  # 2년 후 삭제
    }
  }
}

# CUR 전용 버킷 정책 (AWS CUR 서비스 접근 허용)
resource "aws_s3_bucket_policy" "cur_bucket" {
  bucket = aws_s3_bucket.cur_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCURDelivery"
        Effect    = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action   = [
          "s3:GetBucketAcl",
          "s3:GetBucketPolicy"
        ]
        Resource = aws_s3_bucket.cur_bucket.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "aws:SourceArn"     = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
          }
        }
      },
      {
        Sid       = "AllowCURWrite"
        Effect    = "Allow"
        Principal = {
          Service = "billingreports.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cur_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "aws:SourceArn"     = "arn:aws:cur:us-east-1:${data.aws_caller_identity.current.account_id}:definition/*"
          }
        }
      }
    ]
  })
}

# CUR 리포트 정의 (us-east-1에서만 생성 가능)
resource "aws_cur_report_definition" "main" {
  provider = aws.us_east_1

  report_name                = "company-hourly-cur"
  time_unit                  = "HOURLY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket                  = aws_s3_bucket.cur_bucket.id
  s3_region                  = "ap-northeast-2"
  s3_prefix                  = "cur-reports"
  report_versioning          = "OVERWRITE_REPORT"
  additional_artifacts       = ["ATHENA"]
  refresh_closed_reports     = true
}

# Kubecost IAM 역할 (Pod Identity 사용)
resource "aws_iam_role" "kubecost" {
  name = "kubecost-cost-analyzer"

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
    Name      = "kubecost-cost-analyzer"
    ManagedBy = "terraform"
  }
}

# Kubecost IAM 정책
resource "aws_iam_role_policy" "kubecost" {
  name = "kubecost-cost-analyzer-policy"
  role = aws_iam_role.kubecost.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadCURBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.cur_bucket.arn,
          "${aws_s3_bucket.cur_bucket.arn}/*"
        ]
      },
      {
        Sid    = "ReadETLBucket"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject",
          "s3:GetBucketLocation"
        ]
        Resource = [
          "arn:aws:s3:::kubecost-etl-production",
          "arn:aws:s3:::kubecost-etl-production/*"
        ]
      },
      {
        Sid    = "CostExplorerAccess"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast",
          "ce:GetReservationUtilization",
          "ce:GetSavingsPlansUtilization",
          "ce:GetReservationPurchaseRecommendation",
          "ce:GetRightsizingRecommendation"
        ]
        Resource = "*"
      },
      {
        Sid    = "AthenaAccess"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup"
        ]
        Resource = [
          "arn:aws:athena:ap-northeast-2:${data.aws_caller_identity.current.account_id}:workgroup/primary"
        ]
      },
      {
        Sid    = "GlueAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:ap-northeast-2:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:ap-northeast-2:${data.aws_caller_identity.current.account_id}:database/athenacurcfn_company_hourly_cur",
          "arn:aws:glue:ap-northeast-2:${data.aws_caller_identity.current.account_id}:table/athenacurcfn_company_hourly_cur/*"
        ]
      },
      {
        Sid    = "EC2Describe"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeReservedInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

# Pod Identity Association
resource "aws_eks_pod_identity_association" "kubecost" {
  cluster_name    = "eks-production"
  namespace       = "kubecost"
  service_account = "kubecost"
  role_arn        = aws_iam_role.kubecost.arn
}

# 현재 계정 정보
data "aws_caller_identity" "current" {}
```

**Kubecost Cloud Integration 설정:**

```yaml
# kubecost-cloud-integration 값을 values.yaml에 추가
kubecostProductConfigs:
  cloudIntegrationJSON: |
    {
      "aws": [
        {
          "athenaBucketName": "company-cur-reports-123456789012",
          "athenaRegion": "ap-northeast-2",
          "athenaDatabase": "athenacurcfn_company_hourly_cur",
          "athenaTable": "company_hourly_cur",
          "athenaWorkgroup": "primary",
          "projectID": "123456789012",
          "serviceKeyName": "",
          "serviceKeySecret": ""
        }
      ]
    }
```

### 2.4 비용 정확도 튜닝

클라우드 제공자의 공식 가격표는 일반적인 비용을 반영하지만, EDP(Enterprise Discount Program), 볼륨 할인, 협상 가격 등을 반영하려면 커스텀 가격 설정이 필요합니다.

```yaml
# kubecost-custom-pricing.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubecost-custom-pricing
  namespace: kubecost
data:
  # 협상된 가격을 반영한 커스텀 가격표
  pricing.json: |
    {
      "provider": "aws",
      "region": "ap-northeast-2",
      "description": "EDP 15% 할인이 적용된 커스텀 가격표",
      "CPU": "0.03944",
      "RAM": "0.00493",
      "GPU": "0.4471",
      "storage": "0.000108",
      "spotCPU": "0.01183",
      "spotRAM": "0.00148",
      "zoneNetworkEgress": "0.01",
      "regionNetworkEgress": "0.01",
      "internetNetworkEgress": "0.076",
      "spotLabel": "karpenter.sh/capacity-type",
      "spotLabelValue": "spot",
      "gpuLabel": "karpenter.k8s.aws/instance-gpu-count",
      "gpuLabelValue": "1",
      "sharedOverheadCostPerMonth": "500",
      "sharedNamespaces": "kube-system,monitoring,istio-system,kubecost,cert-manager"
    }
```

**공유 비용 할당 설정:**

```yaml
# kubecost-shared-cost-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubecost-allocation-config
  namespace: kubecost
data:
  allocation.json: |
    {
      "sharedCosts": [
        {
          "name": "control-plane",
          "type": "weighted",
          "weight": "cpuCost",
          "filter": {
            "namespace": "kube-system"
          }
        },
        {
          "name": "monitoring",
          "type": "weighted",
          "weight": "totalCost",
          "filter": {
            "namespace": "monitoring"
          }
        },
        {
          "name": "service-mesh",
          "type": "weighted",
          "weight": "cpuCost",
          "filter": {
            "namespace": "istio-system"
          }
        },
        {
          "name": "networking",
          "type": "even",
          "filter": {
            "namespace": "aws-load-balancer-controller,external-dns,cert-manager"
          }
        }
      ],
      "idleCosts": {
        "shareByNode": true,
        "shareByCluster": false
      }
    }
```

---

## 3. Showback/Chargeback 구현

Showback은 각 팀에게 비용 정보를 보여주는 것이고, Chargeback은 실제로 내부 예산에서 차감하는 것입니다. 대부분의 조직은 Showback에서 시작하여 점차 Chargeback으로 진화합니다.

### 3.1 레이블 전략

비용 할당의 정확도는 레이블링 전략의 일관성에 달려 있습니다. 모든 워크로드에 비용 관련 레이블이 빠짐없이 적용되어야 합니다.

**필수 레이블:**

| 레이블 | 설명 | 예시 |
|--------|------|------|
| `team` | 워크로드를 소유한 팀 | `backend`, `frontend`, `data` |
| `service` | 서비스 이름 | `user-api`, `payment-service` |
| `environment` | 환경 구분 | `production`, `staging`, `dev` |
| `cost-center` | 비용 센터 코드 | `CC-1001`, `CC-2003` |

**권장 레이블:**

| 레이블 | 설명 | 예시 |
|--------|------|------|
| `product` | 제품/프로젝트 이름 | `marketplace`, `admin-portal` |
| `tier` | 서비스 등급 | `critical`, `standard`, `batch` |
| `managed-by` | 관리 도구 | `argocd`, `helm`, `kubectl` |

**Kyverno 정책으로 비용 레이블 강제:**

```yaml
# kyverno-cost-labels-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-cost-labels
  annotations:
    policies.kyverno.io/title: "비용 할당 레이블 필수 적용"
    policies.kyverno.io/description: >-
      모든 Deployment에 비용 할당에 필요한 레이블(team, service, environment, cost-center)이
      반드시 포함되어야 합니다. 이 레이블은 Kubecost 비용 할당과 Showback 리포트에 사용됩니다.
    policies.kyverno.io/category: "FinOps"
    policies.kyverno.io/severity: "high"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    # 시스템 네임스페이스는 제외
    - name: require-cost-labels-on-deployments
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!monitoring"
                - "!istio-system"
                - "!kubecost"
                - "!cert-manager"
                - "!argocd"
      validate:
        message: >-
          Deployment에 비용 할당 레이블이 누락되었습니다.
          다음 레이블을 모두 포함해야 합니다: team, service, environment, cost-center.
          예시:
            metadata:
              labels:
                team: "backend"
                service: "user-api"
                environment: "production"
                cost-center: "CC-1001"
        pattern:
          metadata:
            labels:
              team: "?*"
              service: "?*"
              environment: "production | staging | development"
              cost-center: "CC-?*"
    # Pod 템플릿에도 레이블 전파 확인
    - name: require-cost-labels-on-pod-template
      match:
        any:
          - resources:
              kinds:
                - Deployment
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!monitoring"
                - "!istio-system"
                - "!kubecost"
                - "!cert-manager"
                - "!argocd"
      validate:
        message: >-
          Deployment의 Pod 템플릿에 비용 할당 레이블이 누락되었습니다.
          spec.template.metadata.labels에 team, service 레이블을 포함해야 합니다.
        pattern:
          spec:
            template:
              metadata:
                labels:
                  team: "?*"
                  service: "?*"
    # StatefulSet에도 동일 적용
    - name: require-cost-labels-on-statefulsets
      match:
        any:
          - resources:
              kinds:
                - StatefulSet
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
                - "!monitoring"
                - "!istio-system"
                - "!kubecost"
                - "!cert-manager"
                - "!argocd"
      validate:
        message: >-
          StatefulSet에 비용 할당 레이블이 누락되었습니다.
          다음 레이블을 모두 포함해야 합니다: team, service, environment, cost-center.
        pattern:
          metadata:
            labels:
              team: "?*"
              service: "?*"
              environment: "production | staging | development"
              cost-center: "CC-?*"
```

### 3.2 Namespace 기반 비용 할당

Kubecost Allocation API를 사용하면 프로그래밍 방식으로 비용 데이터를 조회할 수 있습니다. 이를 통해 자동화된 리포트, 대시보드, Slack 알림 등을 구축할 수 있습니다.

**네임스페이스별 비용 조회:**

```bash
# 지난 7일간 네임스페이스별 비용 조회
curl -s "http://kubecost.kubecost.svc.cluster.local:9090/model/allocation?window=7d&aggregate=namespace&accumulate=true" \
  | jq '.data[] | to_entries[] | {
    namespace: .key,
    cpuCost: .value.cpuCost,
    ramCost: .value.ramCost,
    pvCost: .value.pvCost,
    networkCost: .value.networkCost,
    totalCost: .value.totalCost,
    cpuEfficiency: .value.cpuEfficiency,
    ramEfficiency: .value.ramEfficiency
  }' | jq -s 'sort_by(-.totalCost) | .[:10]'
```

**팀별 비용 조회 (레이블 기반):**

```bash
# team 레이블 기준 비용 조회 (지난 30일)
curl -s "http://kubecost.kubecost.svc.cluster.local:9090/model/allocation?window=30d&aggregate=label:team&accumulate=true&shareIdle=true&shareSplit=weighted&shareNamespaces=kube-system,monitoring,istio-system" \
  | jq '.data[] | to_entries[] | {
    team: .key,
    cpuCost: (.value.cpuCost | . * 100 | round / 100),
    ramCost: (.value.ramCost | . * 100 | round / 100),
    totalCost: (.value.totalCost | . * 100 | round / 100),
    cpuEfficiency: (.value.cpuEfficiency | . * 10000 | round / 100),
    ramEfficiency: (.value.ramEfficiency | . * 10000 | round / 100)
  }'
```

**서비스별 비용 상세 조회:**

```bash
# 특정 팀(backend)의 서비스별 비용 상세 (지난 7일)
curl -s "http://kubecost.kubecost.svc.cluster.local:9090/model/allocation?window=7d&aggregate=label:service&accumulate=true&filterLabels=team:backend" \
  | jq '.data[] | to_entries[] | {
    service: .key,
    totalCost: (.value.totalCost | . * 100 | round / 100),
    cpuRequest: (.value.cpuCoreRequestAverage | . * 1000 | round),
    ramRequestMB: (.value.ramByteRequestAverage / 1048576 | round),
    cpuEfficiency: (.value.cpuEfficiency | . * 10000 | round / 100),
    ramEfficiency: (.value.ramEfficiency | . * 10000 | round / 100),
    totalEfficiency: (.value.totalEfficiency | . * 10000 | round / 100)
  }' | jq -s 'sort_by(-.totalCost)'
```

**팀 네임스페이스 ResourceQuota 설정:**

```yaml
# team-backend-quota.yaml
# 백엔드 팀 네임스페이스의 리소스 한도 설정
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cost-quota
  namespace: backend-production
  labels:
    team: "backend"
    cost-center: "CC-1001"
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
    persistentvolumeclaims: "20"
    requests.storage: "200Gi"
    pods: "100"
    services.loadbalancers: "3"
---
# 프론트엔드 팀 네임스페이스의 리소스 한도 설정
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cost-quota
  namespace: frontend-production
  labels:
    team: "frontend"
    cost-center: "CC-1002"
spec:
  hard:
    requests.cpu: "10"
    requests.memory: "20Gi"
    limits.cpu: "20"
    limits.memory: "40Gi"
    persistentvolumeclaims: "10"
    requests.storage: "100Gi"
    pods: "50"
    services.loadbalancers: "2"
---
# 데이터 팀 네임스페이스의 리소스 한도 설정
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cost-quota
  namespace: data-production
  labels:
    team: "data"
    cost-center: "CC-2003"
spec:
  hard:
    requests.cpu: "30"
    requests.memory: "60Gi"
    limits.cpu: "60"
    limits.memory: "120Gi"
    persistentvolumeclaims: "50"
    requests.storage: "500Gi"
    pods: "200"
    services.loadbalancers: "2"
```

### 3.3 공유 비용 분배

Kubernetes 클러스터에는 모든 팀이 공유하는 인프라 비용이 존재합니다. 이 비용을 공정하게 분배하는 것이 Showback/Chargeback의 핵심 과제입니다.

**공유 비용 유형과 분배 방식:**

| 공유 비용 항목 | 포함 리소스 | 권장 분배 방식 | 근거 |
|---------------|-----------|---------------|------|
| 컨트롤 플레인 | kube-system, EKS 관리 비용 | CPU 비용 가중치 | 컴퓨팅 사용량에 비례 |
| 모니터링 | Prometheus, Grafana, Loki | 총 비용 가중치 | 전체 리소스 사용에 비례 |
| 서비스 메시 | Istio, Envoy 사이드카 | CPU 비용 가중치 | 네트워크 처리량에 비례 |
| 네트워킹 | ALB Controller, External DNS | 균등 분배 | 팀 수에 상관없이 동일 |
| 보안 | cert-manager, OPA, Falco | 균등 분배 | 모든 팀이 동일하게 혜택 |
| 유휴 비용 | 미사용 노드 리소스 | 노드별 가중치 | 노드 사용량에 비례 |

![총 1만 달러의 클러스터 비용을 직접·공유·유휴 비용으로 나눠 팀 A, B, C에 배분한 누적 막대 그래프로, 유휴 비용을 최적화 대상으로 강조한다.](../.gitbook/assets/ko-ops-13-finops-cost-platform-1.png)

### 3.4 Grafana Showback 대시보드

팀별/서비스별 비용을 실시간으로 확인할 수 있는 Grafana 대시보드를 구성합니다. Kubecost가 Prometheus에 노출하는 메트릭을 활용합니다.

```json
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "USD / day",
            "barAlignment": 0,
            "drawStyle": "bars",
            "fillOpacity": 80,
            "lineWidth": 1,
            "stacking": {
              "group": "A",
              "mode": "normal"
            }
          },
          "unit": "currencyUSD"
        }
      },
      "gridPos": {
        "h": 10,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": ["sum"],
          "displayMode": "table",
          "placement": "right",
          "sortBy": "Total",
          "sortDesc": true
        },
        "tooltip": {
          "mode": "multi",
          "sort": "desc"
        }
      },
      "title": "팀별 일일 비용 추이",
      "type": "timeseries",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (\n  label_replace(\n    container_cpu_allocation{namespace!~\"kube-system|monitoring|istio-system|kubecost\"} * on(node) group_left() node_cpu_hourly_cost * 24,\n    \"label_team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n  +\n  label_replace(\n    container_memory_allocation_bytes{namespace!~\"kube-system|monitoring|istio-system|kubecost\"} / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost * 24,\n    \"label_team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n)",
          "legendFormat": "{{label_team}}",
          "refId": "A"
        }
      ]
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "USD / day",
            "barAlignment": 0,
            "drawStyle": "bars",
            "fillOpacity": 80,
            "lineWidth": 1,
            "stacking": {
              "group": "A",
              "mode": "normal"
            }
          },
          "unit": "currencyUSD"
        }
      },
      "gridPos": {
        "h": 10,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "options": {
        "legend": {
          "calcs": ["sum"],
          "displayMode": "table",
          "placement": "right",
          "sortBy": "Total",
          "sortDesc": true
        },
        "tooltip": {
          "mode": "multi",
          "sort": "desc"
        }
      },
      "title": "서비스별 일일 비용 추이",
      "type": "timeseries",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_service) (\n  label_replace(\n    container_cpu_allocation{namespace!~\"kube-system|monitoring|istio-system|kubecost\"} * on(node) group_left() node_cpu_hourly_cost * 24,\n    \"label_service\", \"$1\", \"label_service\", \"(.+)\"\n  )\n  +\n  label_replace(\n    container_memory_allocation_bytes{namespace!~\"kube-system|monitoring|istio-system|kubecost\"} / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost * 24,\n    \"label_service\", \"$1\", \"label_service\", \"(.+)\"\n  )\n)",
          "legendFormat": "{{label_service}}",
          "refId": "A"
        }
      ]
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 40},
              {"color": "orange", "value": 60},
              {"color": "red", "value": 80}
            ]
          },
          "unit": "percentunit",
          "min": 0,
          "max": 1
        }
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 10
      },
      "id": 3,
      "options": {
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        },
        "orientation": "horizontal",
        "showUnfilled": true
      },
      "title": "팀별 CPU 효율성 (Request 대비 실사용)",
      "type": "bargauge",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (\n  rate(container_cpu_usage_seconds_total{namespace!~\"kube-system|monitoring|istio-system|kubecost\"}[1h])\n) \n/ \nsum by (label_team) (\n  container_cpu_allocation{namespace!~\"kube-system|monitoring|istio-system|kubecost\"}\n)",
          "legendFormat": "{{label_team}}",
          "refId": "A"
        }
      ]
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 40},
              {"color": "orange", "value": 60},
              {"color": "red", "value": 80}
            ]
          },
          "unit": "percentunit",
          "min": 0,
          "max": 1
        }
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 10
      },
      "id": 4,
      "options": {
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        },
        "orientation": "horizontal",
        "showUnfilled": true
      },
      "title": "팀별 메모리 효율성 (Request 대비 실사용)",
      "type": "bargauge",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (\n  container_memory_working_set_bytes{namespace!~\"kube-system|monitoring|istio-system|kubecost\"}\n) \n/ \nsum by (label_team) (\n  container_memory_allocation_bytes{namespace!~\"kube-system|monitoring|istio-system|kubecost\"}\n)",
          "legendFormat": "{{label_team}}",
          "refId": "A"
        }
      ]
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "currencyUSD",
          "color": {
            "mode": "thresholds"
          },
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 100},
              {"color": "red", "value": 500}
            ]
          }
        }
      },
      "gridPos": {
        "h": 8,
        "w": 24,
        "x": 0,
        "y": 18
      },
      "id": 5,
      "options": {
        "showHeader": true,
        "sortBy": [
          {
            "desc": true,
            "displayName": "Total Cost"
          }
        ]
      },
      "title": "네임스페이스별 월간 비용 요약",
      "type": "table",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (namespace) (\n  (container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost) * 730\n)",
          "format": "table",
          "instant": true,
          "legendFormat": "",
          "refId": "A"
        }
      ],
      "transformations": [
        {
          "id": "organize",
          "options": {
            "renameByName": {
              "namespace": "Namespace",
              "Value": "Monthly Cost (USD)"
            }
          }
        }
      ]
    }
  ],
  "refresh": "5m",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["finops", "cost", "kubernetes"],
  "templating": {
    "list": [
      {
        "current": {},
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "definition": "label_values(container_cpu_allocation, namespace)",
        "name": "namespace",
        "query": "label_values(container_cpu_allocation, namespace)",
        "refresh": 2,
        "type": "query",
        "multi": true,
        "includeAll": true
      },
      {
        "current": {},
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "definition": "label_values(kube_pod_labels{label_team!=\"\"}, label_team)",
        "name": "team",
        "query": "label_values(kube_pod_labels{label_team!=\"\"}, label_team)",
        "refresh": 2,
        "type": "query",
        "multi": true,
        "includeAll": true
      }
    ]
  },
  "time": {
    "from": "now-7d",
    "to": "now"
  },
  "title": "FinOps - Showback Dashboard",
  "uid": "finops-showback",
  "version": 1
}
```

---

## 4. 비용 이상 탐지

비용 이상을 조기에 탐지하면 예산 초과를 방지하고, 리소스 낭비나 잘못된 설정을 빠르게 수정할 수 있습니다.

### 4.1 Kubecost 알림 구성

Kubecost는 비용 기반 알림을 네이티브로 지원합니다. 예산 초과, 효율성 저하, 비용 급증 등 다양한 시나리오에 대한 알림을 구성할 수 있습니다.

```yaml
# kubecost-alerts-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubecost-alerts
  namespace: kubecost
data:
  alerts.json: |
    {
      "alerts": [
        {
          "type": "budget",
          "threshold": 10000,
          "window": "30d",
          "aggregation": "cluster",
          "filter": "",
          "ownerContact": [
            {
              "type": "slack",
              "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
            },
            {
              "type": "email",
              "url": "finops@example.com"
            }
          ],
          "slackWebhookUrl": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
          "name": "월간 클러스터 예산 초과",
          "description": "클러스터 월간 비용이 $10,000을 초과했습니다."
        },
        {
          "type": "budget",
          "threshold": 3000,
          "window": "30d",
          "aggregation": "namespace",
          "filter": "backend-production",
          "ownerContact": [
            {
              "type": "slack",
              "url": "https://hooks.slack.com/services/T00000000/B00000000/YYYYYYYYYYYYYYYYYYYYYYYY"
            }
          ],
          "name": "백엔드팀 월간 예산 초과",
          "description": "백엔드팀 네임스페이스 월간 비용이 $3,000을 초과했습니다."
        },
        {
          "type": "efficiency",
          "threshold": 0.4,
          "window": "48h",
          "aggregation": "namespace",
          "filter": "",
          "ownerContact": [
            {
              "type": "slack",
              "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
            }
          ],
          "name": "리소스 효율성 저하",
          "description": "네임스페이스의 리소스 효율성이 40% 미만으로 떨어졌습니다."
        },
        {
          "type": "recurringUpdate",
          "window": "7d",
          "aggregation": "namespace",
          "filter": "",
          "ownerContact": [
            {
              "type": "slack",
              "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
            }
          ],
          "name": "주간 비용 리포트",
          "description": "주간 네임스페이스별 비용 변화 리포트입니다."
        },
        {
          "type": "spendChange",
          "relativeThreshold": 0.3,
          "window": "1d",
          "baselineWindow": "7d",
          "aggregation": "namespace",
          "filter": "",
          "ownerContact": [
            {
              "type": "slack",
              "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
            }
          ],
          "name": "비용 급증 감지",
          "description": "지난 7일 평균 대비 일일 비용이 30% 이상 증가했습니다."
        }
      ],
      "globalAlertConfigs": {
        "enabled": true,
        "slackWebhookUrl": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "alertFrequencyMinutes": 1440
      }
    }
```

### 4.2 Prometheus 기반 비용 알림

Kubecost가 Prometheus에 노출하는 메트릭을 활용하면 기존 Alertmanager 파이프라인에 비용 알림을 통합할 수 있습니다.

```yaml
# cost-anomaly-prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-anomaly-rules
  namespace: monitoring
  labels:
    release: prometheus
    app: kube-prometheus-stack
spec:
  groups:
    - name: cost-anomaly-detection
      interval: 15m
      rules:
        # 일일 클러스터 비용이 7일 평균 대비 50% 이상 급증
        - alert: ClusterCostSpike
          expr: |
            (
              sum(
                container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
                + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost
              ) * 24
            )
            /
            (
              avg_over_time(
                sum(
                  container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
                  + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost
                )[7d:1d]
              ) * 24
            ) > 1.5
          for: 30m
          labels:
            severity: warning
            team: finops
            category: cost
          annotations:
            summary: "클러스터 일일 비용 50% 이상 급증"
            description: >
              클러스터 일일 비용이 지난 7일 평균 대비 50% 이상 증가했습니다.
              현재 비용 비율: {{ $value | humanizePercentage }}
            runbook_url: "https://wiki.example.com/runbooks/cost-spike"

        # 네임스페이스 비용이 설정된 예산 초과
        - alert: NamespaceBudgetExceeded
          expr: |
            (
              sum by (namespace) (
                container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
                + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost
              ) * 730
            )
            > on(namespace) group_left()
            (
              kube_namespace_annotations{annotation_budget_monthly_usd!=""} * 0
              + on(namespace) group_left(annotation_budget_monthly_usd)
              label_replace(
                kube_namespace_annotations{annotation_budget_monthly_usd!=""},
                "budget", "$1", "annotation_budget_monthly_usd", "(.*)"
              )
            )
          for: 1h
          labels:
            severity: warning
            team: finops
            category: cost
          annotations:
            summary: "{{ $labels.namespace }} 네임스페이스 월간 예산 초과"
            description: >
              네임스페이스 {{ $labels.namespace }}의 예상 월간 비용이 설정된 예산을 초과했습니다.

        # CPU 효율성이 30% 미만인 네임스페이스 감지
        - alert: LowCpuEfficiency
          expr: |
            (
              sum by (namespace) (
                rate(container_cpu_usage_seconds_total{namespace!~"kube-system|monitoring|istio-system|kubecost"}[6h])
              )
              /
              sum by (namespace) (
                container_cpu_allocation{namespace!~"kube-system|monitoring|istio-system|kubecost"}
              )
            ) < 0.3
            and
            sum by (namespace) (
              container_cpu_allocation{namespace!~"kube-system|monitoring|istio-system|kubecost"}
            ) > 2
          for: 24h
          labels:
            severity: info
            team: finops
            category: efficiency
          annotations:
            summary: "{{ $labels.namespace }} CPU 효율성 30% 미만"
            description: >
              네임스페이스 {{ $labels.namespace }}의 CPU 효율성이 24시간 동안
              30% 미만입니다. 리소스 라이트사이징을 검토하세요.
              현재 효율성: {{ $value | humanizePercentage }}

        # 메모리 효율성이 30% 미만인 네임스페이스 감지
        - alert: LowMemoryEfficiency
          expr: |
            (
              sum by (namespace) (
                container_memory_working_set_bytes{namespace!~"kube-system|monitoring|istio-system|kubecost"}
              )
              /
              sum by (namespace) (
                container_memory_allocation_bytes{namespace!~"kube-system|monitoring|istio-system|kubecost"}
              )
            ) < 0.3
            and
            sum by (namespace) (
              container_memory_allocation_bytes{namespace!~"kube-system|monitoring|istio-system|kubecost"}
            ) > 4294967296
          for: 24h
          labels:
            severity: info
            team: finops
            category: efficiency
          annotations:
            summary: "{{ $labels.namespace }} 메모리 효율성 30% 미만"
            description: >
              네임스페이스 {{ $labels.namespace }}의 메모리 효율성이 24시간 동안
              30% 미만입니다. 리소스 라이트사이징을 검토하세요.
              현재 효율성: {{ $value | humanizePercentage }}

        # 유휴 노드 비용이 클러스터 전체의 20% 초과
        - alert: HighIdleCost
          expr: |
            (
              sum(node_cpu_hourly_cost * (1 - instance:node_cpu_utilisation:rate5m)) * 730
              + sum(node_ram_hourly_cost * (1 - instance:node_memory_utilisation:rate5m)) * 730
            )
            /
            (
              sum(node_cpu_hourly_cost + node_ram_hourly_cost) * 730
            ) > 0.20
          for: 6h
          labels:
            severity: warning
            team: finops
            category: cost
          annotations:
            summary: "유휴 리소스 비용이 전체의 20% 초과"
            description: >
              클러스터의 유휴 리소스(미사용 CPU/메모리) 비용이 전체 비용의 20%를
              초과하고 있습니다. 노드 스케일 다운이나 워크로드 통합을 검토하세요.
              현재 유휴 비용 비율: {{ $value | humanizePercentage }}
```

**Alertmanager 라우팅 및 Slack 수신기 설정:**

```yaml
# alertmanager-cost-config.yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: cost-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  route:
    receiver: "cost-alerts-slack"
    groupBy:
      - "alertname"
      - "namespace"
      - "category"
    groupWait: "30s"
    groupInterval: "5m"
    repeatInterval: "12h"
    matchers:
      - name: category
        matchType: "=~"
        value: "cost|efficiency"
    routes:
      # 심각한 비용 알림은 즉시 전송
      - receiver: "cost-alerts-slack-urgent"
        matchers:
          - name: severity
            matchType: "="
            value: "critical"
        repeatInterval: "1h"
      # 효율성 관련 알림은 일 1회
      - receiver: "cost-alerts-slack"
        matchers:
          - name: category
            matchType: "="
            value: "efficiency"
        repeatInterval: "24h"

  receivers:
    - name: "cost-alerts-slack"
      slackConfigs:
        - apiURL:
            name: slack-webhook-secret
            key: cost-channel-url
          channel: "#finops-alerts"
          sendResolved: true
          title: |
            [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
          text: |
            *알림 이름*: {{ .CommonLabels.alertname }}
            *심각도*: {{ .CommonLabels.severity }}
            *카테고리*: {{ .CommonLabels.category }}
            {{ range .Alerts }}
            *설명*: {{ .Annotations.description }}
            *네임스페이스*: {{ .Labels.namespace }}
            *런북*: {{ .Annotations.runbook_url }}
            {{ end }}
          iconEmoji: ":money_with_wings:"
          username: "FinOps Alert Bot"
    - name: "cost-alerts-slack-urgent"
      slackConfigs:
        - apiURL:
            name: slack-webhook-secret
            key: cost-urgent-channel-url
          channel: "#finops-urgent"
          sendResolved: true
          title: |
            :rotating_light: [{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}
          text: |
            *긴급 비용 알림*
            *알림 이름*: {{ .CommonLabels.alertname }}
            {{ range .Alerts }}
            *설명*: {{ .Annotations.description }}
            *즉시 확인이 필요합니다.*
            {{ end }}
          iconEmoji: ":rotating_light:"
          username: "FinOps URGENT"
---
# Slack Webhook Secret
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook-secret
  namespace: monitoring
type: Opaque
stringData:
  cost-channel-url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  cost-urgent-channel-url: "https://hooks.slack.com/services/T00000000/B00000000/ZZZZZZZZZZZZZZZZZZZZZZZZ"
```

### 4.3 AWS Cost Anomaly Detection 통합

AWS Cost Anomaly Detection은 기계 학습을 사용하여 AWS 계정 수준의 비용 이상을 자동으로 탐지합니다. Kubernetes 비용 모니터링과 병행하면 더 넓은 범위의 비용 이상을 포착할 수 있습니다.

**Terraform으로 AWS Cost Anomaly Detection 구성:**

```hcl
# cost-anomaly-detection.tf

# 비용 이상 모니터 생성 (EKS 서비스 비용)
resource "aws_ce_anomaly_monitor" "eks_cost" {
  name              = "eks-cost-anomaly-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"

  tags = {
    Name      = "eks-cost-anomaly-monitor"
    ManagedBy = "terraform"
  }
}

# 커스텀 모니터 (태그 기반 필터링)
resource "aws_ce_anomaly_monitor" "kubernetes_tagged" {
  name         = "kubernetes-tagged-resources"
  monitor_type = "CUSTOM"

  monitor_specification = jsonencode({
    And = null
    Or  = null
    Not = null
    Dimensions = {
      Key           = "SERVICE"
      Values        = ["Amazon Elastic Kubernetes Service", "Amazon EC2", "Amazon Elastic Block Store"]
      MatchOptions  = ["EQUALS"]
    }
    Tags = null
    CostCategories = null
  })

  tags = {
    Name      = "kubernetes-tagged-resources"
    ManagedBy = "terraform"
  }
}

# 알림 구독 (이메일 + SNS)
resource "aws_ce_anomaly_subscription" "eks_alerts" {
  name = "eks-cost-anomaly-alerts"

  monitor_arn_list = [
    aws_ce_anomaly_monitor.eks_cost.arn,
    aws_ce_anomaly_monitor.kubernetes_tagged.arn
  ]

  frequency = "DAILY"

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = ["100"]
    }
  }

  subscriber {
    type    = "EMAIL"
    address = "finops@example.com"
  }

  subscriber {
    type    = "SNS"
    address = aws_sns_topic.cost_anomaly.arn
  }
}

# SNS 토픽 (Lambda/Slack 연동용)
resource "aws_sns_topic" "cost_anomaly" {
  name = "cost-anomaly-alerts"

  tags = {
    Name      = "cost-anomaly-alerts"
    ManagedBy = "terraform"
  }
}

# SNS 정책 (Cost Anomaly Detection이 게시 허용)
resource "aws_sns_topic_policy" "cost_anomaly" {
  arn = aws_sns_topic.cost_anomaly.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCostAnomalyPublish"
        Effect    = "Allow"
        Principal = {
          Service = "costalerts.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.cost_anomaly.arn
      }
    ]
  })
}
```

---

## 5. 팀 셀프서비스 비용 관리

엔지니어링 팀이 자신의 비용을 직접 모니터링하고 관리할 수 있는 셀프서비스 체계를 구축합니다. FinOps 팀에 의존하지 않고 각 팀이 자율적으로 비용을 최적화할 수 있어야 합니다.

### 5.1 팀별 비용 대시보드

Grafana의 변수(variable) 기능을 활용하면 하나의 대시보드 정의로 팀별 맞춤 뷰를 제공할 수 있습니다.

```yaml
# grafana-team-dashboard-configmap.yaml
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
      "templating": {
        "list": [
          {
            "name": "team",
            "label": "Team",
            "type": "query",
            "datasource": {
              "type": "prometheus",
              "uid": "prometheus"
            },
            "query": "label_values(kube_pod_labels{label_team!=\"\"}, label_team)",
            "refresh": 2,
            "current": {},
            "multi": false,
            "includeAll": false,
            "sort": 1
          },
          {
            "name": "timerange",
            "label": "Cost Period",
            "type": "custom",
            "query": "7d : 7 Days, 14d : 14 Days, 30d : 30 Days",
            "current": {
              "selected": true,
              "text": "7 Days",
              "value": "7d"
            },
            "multi": false,
            "includeAll": false
          }
        ]
      },
      "panels": [
        {
          "title": "${team} 팀 - 일일 비용 추이",
          "type": "timeseries",
          "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0},
          "targets": [
            {
              "expr": "sum by (label_service) (\n  container_cpu_allocation{label_team=\"$team\"} * on(node) group_left() node_cpu_hourly_cost * 24\n  +\n  container_memory_allocation_bytes{label_team=\"$team\"} / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost * 24\n)",
              "legendFormat": "{{label_service}}"
            }
          ]
        },
        {
          "title": "${team} 팀 - 서비스별 월 추정 비용",
          "type": "stat",
          "gridPos": {"h": 4, "w": 24, "x": 0, "y": 8},
          "targets": [
            {
              "expr": "sum(\n  container_cpu_allocation{label_team=\"$team\"} * on(node) group_left() node_cpu_hourly_cost\n  +\n  container_memory_allocation_bytes{label_team=\"$team\"} / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost\n) * 730",
              "legendFormat": "월 추정 비용"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "currencyUSD",
              "thresholds": {
                "steps": [
                  {"color": "green", "value": null},
                  {"color": "yellow", "value": 2000},
                  {"color": "red", "value": 4000}
                ]
              }
            }
          }
        },
        {
          "title": "${team} 팀 - 리소스 효율성",
          "type": "gauge",
          "gridPos": {"h": 6, "w": 12, "x": 0, "y": 12},
          "targets": [
            {
              "expr": "sum(rate(container_cpu_usage_seconds_total{label_team=\"$team\"}[1h])) / sum(container_cpu_allocation{label_team=\"$team\"})",
              "legendFormat": "CPU 효율성"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1,
              "thresholds": {
                "steps": [
                  {"color": "red", "value": null},
                  {"color": "yellow", "value": 0.3},
                  {"color": "green", "value": 0.6}
                ]
              }
            }
          }
        },
        {
          "title": "${team} 팀 - 라이트사이징 추천",
          "type": "table",
          "gridPos": {"h": 6, "w": 12, "x": 12, "y": 12},
          "targets": [
            {
              "expr": "sum by (container, namespace) (\n  container_cpu_allocation{label_team=\"$team\"}\n  - on(container, namespace, pod) \n  rate(container_cpu_usage_seconds_total{label_team=\"$team\"}[24h])\n) > 0.1",
              "legendFormat": "{{namespace}}/{{container}}",
              "format": "table",
              "instant": true
            }
          ]
        }
      ],
      "title": "팀 비용 셀프서비스 대시보드",
      "uid": "team-cost-selfservice",
      "tags": ["finops", "team", "self-service"]
    }
```

### 5.2 Slack 비용 리포트 봇

CronJob으로 주간 비용 리포트를 자동 생성하여 Slack 채널에 전송합니다. 각 팀이 자신의 비용 현황을 별도의 도구 접근 없이도 확인할 수 있습니다.

```yaml
# cost-report-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-cost-report
  namespace: kubecost
  labels:
    app: cost-report
    team: finops
spec:
  # 매주 월요일 오전 9시 (KST, UTC+9이므로 일요일 자정)
  schedule: "0 0 * * 1"
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 3
      activeDeadlineSeconds: 600
      template:
        metadata:
          labels:
            app: cost-report
        spec:
          serviceAccountName: cost-report
          restartPolicy: OnFailure
          containers:
            - name: cost-reporter
              image: curlimages/curl:8.7.1
              command:
                - /bin/sh
                - /scripts/weekly-cost-report.sh
              env:
                - name: KUBECOST_URL
                  value: "http://kubecost-cost-analyzer.kubecost.svc.cluster.local:9090"
                - name: SLACK_WEBHOOK_URL
                  valueFrom:
                    secretKeyRef:
                      name: cost-report-secrets
                      key: slack-webhook-url
                - name: REPORT_WINDOW
                  value: "7d"
              resources:
                requests:
                  cpu: "50m"
                  memory: "64Mi"
                limits:
                  cpu: "200m"
                  memory: "128Mi"
              volumeMounts:
                - name: scripts
                  mountPath: /scripts
                  readOnly: true
          volumes:
            - name: scripts
              configMap:
                name: cost-report-scripts
                defaultMode: 0755
---
# 비용 리포트 스크립트
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-report-scripts
  namespace: kubecost
data:
  weekly-cost-report.sh: |
    #!/bin/sh
    set -e

    # Kubecost API에서 비용 데이터 조회
    echo "[INFO] Kubecost API에서 비용 데이터를 조회합니다..."

    # 네임스페이스별 비용 조회
    NAMESPACE_COSTS=$(curl -s "${KUBECOST_URL}/model/allocation?window=${REPORT_WINDOW}&aggregate=namespace&accumulate=true&shareIdle=true&shareSplit=weighted&shareNamespaces=kube-system,monitoring,istio-system,kubecost")

    # 팀별 비용 조회 (label:team 기준)
    TEAM_COSTS=$(curl -s "${KUBECOST_URL}/model/allocation?window=${REPORT_WINDOW}&aggregate=label:team&accumulate=true&shareIdle=true&shareSplit=weighted&shareNamespaces=kube-system,monitoring,istio-system,kubecost")

    # 총 비용 계산
    TOTAL_COST=$(echo "${NAMESPACE_COSTS}" | jq '[.data[0] | to_entries[] | .value.totalCost] | add | . * 100 | round / 100')

    # 팀별 비용 상위 5개 추출
    TEAM_SUMMARY=$(echo "${TEAM_COSTS}" | jq -r '
      .data[0] | to_entries
      | sort_by(-.value.totalCost)
      | .[:5]
      | .[]
      | "\(.key): $\(.value.totalCost * 100 | round / 100) (CPU효율: \(.value.cpuEfficiency * 10000 | round / 100)%, MEM효율: \(.value.ramEfficiency * 10000 | round / 100)%)"
    ')

    # 효율성이 낮은 네임스페이스 추출 (40% 미만)
    LOW_EFFICIENCY=$(echo "${NAMESPACE_COSTS}" | jq -r '
      .data[0] | to_entries
      | map(select(.value.totalEfficiency < 0.4 and .value.totalCost > 10))
      | sort_by(.value.totalEfficiency)
      | .[:5]
      | .[]
      | "\(.key): 효율성 \(.value.totalEfficiency * 10000 | round / 100)%, 비용 $\(.value.totalCost * 100 | round / 100)"
    ')

    # 전주 대비 비용 변화 계산
    PREV_COSTS=$(curl -s "${KUBECOST_URL}/model/allocation?window=${REPORT_WINDOW}&aggregate=cluster&accumulate=true&offset=${REPORT_WINDOW}")
    PREV_TOTAL=$(echo "${PREV_COSTS}" | jq '[.data[0] | to_entries[] | .value.totalCost] | add | . * 100 | round / 100')

    if [ -n "${PREV_TOTAL}" ] && [ "${PREV_TOTAL}" != "null" ] && [ "${PREV_TOTAL}" != "0" ]; then
      CHANGE_PCT=$(echo "${TOTAL_COST} ${PREV_TOTAL}" | awk '{printf "%.1f", ($1 - $2) / $2 * 100}')
      CHANGE_INDICATOR="전주 대비 ${CHANGE_PCT}%"
    else
      CHANGE_INDICATOR="전주 데이터 없음"
    fi

    # 보고 기간
    REPORT_DATE=$(date '+%Y-%m-%d')

    # Slack 메시지 구성
    SLACK_PAYLOAD=$(cat <<PAYLOAD
    {
      "blocks": [
        {
          "type": "header",
          "text": {
            "type": "plain_text",
            "text": "주간 Kubernetes 비용 리포트 (${REPORT_DATE})"
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*리포트 기간*: 최근 7일\n*총 비용*: \$${TOTAL_COST}\n*변화*: ${CHANGE_INDICATOR}"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*팀별 비용 (Top 5)*\n\`\`\`\n${TEAM_SUMMARY}\n\`\`\`"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*효율성 낮은 네임스페이스 (< 40%)*\n\`\`\`\n${LOW_EFFICIENCY}\n\`\`\`"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "<https://kubecost.internal.example.com|Kubecost 대시보드에서 자세히 보기>"
          }
        }
      ]
    }
    PAYLOAD
    )

    # Slack 전송
    echo "[INFO] Slack으로 비용 리포트를 전송합니다..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST \
      -H "Content-Type: application/json" \
      -d "${SLACK_PAYLOAD}" \
      "${SLACK_WEBHOOK_URL}")

    if [ "${HTTP_STATUS}" = "200" ]; then
      echo "[INFO] 비용 리포트 전송 성공"
    else
      echo "[ERROR] 비용 리포트 전송 실패 (HTTP ${HTTP_STATUS})"
      exit 1
    fi
---
# Secrets
apiVersion: v1
kind: Secret
metadata:
  name: cost-report-secrets
  namespace: kubecost
type: Opaque
stringData:
  slack-webhook-url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
---
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cost-report
  namespace: kubecost
```

### 5.3 비용 예산 설정 및 알림

네임스페이스 수준에서 월간 예산을 설정하고, 예산 소진율에 따라 단계적 알림을 발송합니다.

```yaml
# namespace-budget-config.yaml
# 네임스페이스 어노테이션으로 예산 설정
apiVersion: v1
kind: Namespace
metadata:
  name: backend-production
  labels:
    team: "backend"
    cost-center: "CC-1001"
  annotations:
    budget.finops/monthly-usd: "3000"
    budget.finops/alert-threshold-warning: "70"
    budget.finops/alert-threshold-critical: "90"
    budget.finops/owner-email: "backend-team@example.com"
    budget.finops/slack-channel: "#backend-costs"
---
apiVersion: v1
kind: Namespace
metadata:
  name: frontend-production
  labels:
    team: "frontend"
    cost-center: "CC-1002"
  annotations:
    budget.finops/monthly-usd: "2000"
    budget.finops/alert-threshold-warning: "70"
    budget.finops/alert-threshold-critical: "90"
    budget.finops/owner-email: "frontend-team@example.com"
    budget.finops/slack-channel: "#frontend-costs"
---
apiVersion: v1
kind: Namespace
metadata:
  name: data-production
  labels:
    team: "data"
    cost-center: "CC-2003"
  annotations:
    budget.finops/monthly-usd: "5000"
    budget.finops/alert-threshold-warning: "70"
    budget.finops/alert-threshold-critical: "90"
    budget.finops/owner-email: "data-team@example.com"
    budget.finops/slack-channel: "#data-costs"
```

**예산 모니터링 PrometheusRule:**

```yaml
# budget-monitoring-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: namespace-budget-rules
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
    - name: namespace-budget-alerts
      interval: 30m
      rules:
        # 예산 70% 소진 경고
        - alert: BudgetWarning
          expr: |
            (
              sum by (namespace) (
                container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
                + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost
              ) * 730
            )
            /
            on(namespace)
            (
              kube_namespace_annotations{annotation_budget_finops_monthly_usd!=""}
              * on(namespace) group_left(annotation_budget_finops_monthly_usd)
              0 + ignoring(annotation_budget_finops_monthly_usd)
              kube_namespace_annotations{annotation_budget_finops_monthly_usd!=""}
            ) > 0.7
          for: 1h
          labels:
            severity: warning
            category: budget
          annotations:
            summary: "{{ $labels.namespace }} 예산 70% 소진"
            description: >
              네임스페이스 {{ $labels.namespace }}의 월 추정 비용이
              설정된 예산의 70%를 초과했습니다.

        # 예산 90% 소진 긴급
        - alert: BudgetCritical
          expr: |
            (
              sum by (namespace) (
                container_cpu_allocation * on(node) group_left() node_cpu_hourly_cost
                + container_memory_allocation_bytes / 1024 / 1024 / 1024 * on(node) group_left() node_ram_hourly_cost
              ) * 730
            )
            /
            on(namespace)
            (
              kube_namespace_annotations{annotation_budget_finops_monthly_usd!=""}
              * on(namespace) group_left(annotation_budget_finops_monthly_usd)
              0 + ignoring(annotation_budget_finops_monthly_usd)
              kube_namespace_annotations{annotation_budget_finops_monthly_usd!=""}
            ) > 0.9
          for: 30m
          labels:
            severity: critical
            category: budget
          annotations:
            summary: "{{ $labels.namespace }} 예산 90% 소진 - 긴급"
            description: >
              네임스페이스 {{ $labels.namespace }}의 월 추정 비용이
              설정된 예산의 90%를 초과했습니다. 즉시 검토가 필요합니다.
```

---

## 6. 리소스 라이트사이징 자동화

리소스 라이트사이징은 비용 최적화에서 가장 효과적인 방법 중 하나입니다. VPA(Vertical Pod Autoscaler) 추천과 Goldilocks를 활용하여 체계적으로 리소스를 최적화합니다.

### 6.1 VPA 추천 워크플로우

VPA를 `updateMode: "Off"`로 설정하면 실제 리소스를 변경하지 않고 추천값만 제공합니다. 이를 통해 안전하게 라이트사이징 기회를 발견할 수 있습니다.

```yaml
# vpa-recommendation-only.yaml
# 백엔드 API 서비스에 대한 VPA 추천
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: user-api-vpa
  namespace: backend-production
  labels:
    team: "backend"
    service: "user-api"
    purpose: "rightsizing-recommendation"
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: user-api
  updatePolicy:
    # Off 모드: 추천만 제공하고 실제 Pod 리소스는 변경하지 않음
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: "user-api"
        minAllowed:
          cpu: "50m"
          memory: "64Mi"
        maxAllowed:
          cpu: "4"
          memory: "8Gi"
        controlledResources:
          - cpu
          - memory
        controlledValues: RequestsAndLimits
---
# 결제 서비스에 대한 VPA 추천
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: payment-service-vpa
  namespace: backend-production
  labels:
    team: "backend"
    service: "payment-service"
    purpose: "rightsizing-recommendation"
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: payment-service
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: "payment-service"
        minAllowed:
          cpu: "100m"
          memory: "128Mi"
        maxAllowed:
          cpu: "2"
          memory: "4Gi"
        controlledResources:
          - cpu
          - memory
        controlledValues: RequestsAndLimits
---
# 프론트엔드 BFF 서비스에 대한 VPA 추천
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: bff-service-vpa
  namespace: frontend-production
  labels:
    team: "frontend"
    service: "bff-service"
    purpose: "rightsizing-recommendation"
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: bff-service
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: "bff-service"
        minAllowed:
          cpu: "25m"
          memory: "32Mi"
        maxAllowed:
          cpu: "2"
          memory: "4Gi"
        controlledResources:
          - cpu
          - memory
        controlledValues: RequestsAndLimits
```

VPA 추천값 확인:

```bash
# VPA 추천값 확인
kubectl get vpa -n backend-production -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.recommendation.containerRecommendations[0].target.cpu}{"\t"}{.status.recommendation.containerRecommendations[0].target.memory}{"\n"}{end}'

# 상세 추천 (lower/target/upper bound)
kubectl describe vpa user-api-vpa -n backend-production | grep -A 20 "Recommendation"
```

### 6.2 Goldilocks 대시보드

Goldilocks는 네임스페이스 내 모든 Deployment에 자동으로 VPA를 생성하고, 웹 대시보드에서 추천값을 한눈에 확인할 수 있게 해줍니다.

```yaml
# goldilocks-values.yaml
# helm repo add fairwinds-stable https://charts.fairwinds.com/stable
# helm install goldilocks fairwinds-stable/goldilocks -n goldilocks --create-namespace -f goldilocks-values.yaml

image:
  repository: us-docker.pkg.dev/fairwinds-ops/oss/goldilocks
  tag: "v4.13.0"

controller:
  enabled: true
  resources:
    requests:
      cpu: "25m"
      memory: "64Mi"
    limits:
      cpu: "100m"
      memory: "128Mi"
  flags:
    on-by-default: false
    exclude-containers: "istio-proxy,istio-init,linkerd-proxy,linkerd-init"

dashboard:
  enabled: true
  replicaCount: 2
  resources:
    requests:
      cpu: "25m"
      memory: "64Mi"
    limits:
      cpu: "100m"
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
      - host: "goldilocks.internal.example.com"
        paths:
          - path: "/"
            pathType: "Prefix"

vpa:
  enabled: true
  updater:
    enabled: false  # Goldilocks는 추천만, 실제 업데이트는 하지 않음

rbac:
  create: true

serviceAccount:
  create: true
  name: "goldilocks"
```

**Goldilocks 활성화 (네임스페이스 레이블링):**

```bash
# 비용 추적 대상 네임스페이스에 Goldilocks 활성화
kubectl label namespace backend-production goldilocks.fairwinds.com/enabled=true
kubectl label namespace frontend-production goldilocks.fairwinds.com/enabled=true
kubectl label namespace data-production goldilocks.fairwinds.com/enabled=true

# VPA 자동 생성 확인
kubectl get vpa -n backend-production
kubectl get vpa -n frontend-production
kubectl get vpa -n data-production

# 특정 네임스페이스에서 Goldilocks 비활성화
# kubectl label namespace test-namespace goldilocks.fairwinds.com/enabled-
```

### 6.3 자동 리소스 조정 파이프라인

VPA 추천을 수동으로 적용하는 대신, CI/CD 파이프라인을 통해 추천값을 PR로 생성하고 리뷰 후 적용하는 자동화 워크플로우를 구축합니다.

![CronJob이 매주 VPA 추천값을 조회해 스크립트가 PR을 생성하고, Git/CI가 검증 후 팀 리더의 승인·머지를 거쳐 ArgoCD로 안전하게 배포하는 시퀀스 다이어그램이다.](../.gitbook/assets/ko-ops-13-finops-cost-platform-2.png)

**라이트사이징 자동화 CronJob:**

```yaml
# rightsizing-automation-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rightsizing-pr-generator
  namespace: kubecost
  labels:
    app: rightsizing-automation
spec:
  # 매주 수요일 오전 10시 (KST)
  schedule: "0 1 * * 3"
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 900
      template:
        metadata:
          labels:
            app: rightsizing-automation
        spec:
          serviceAccountName: rightsizing-automation
          restartPolicy: OnFailure
          containers:
            - name: rightsizing
              image: bitnami/kubectl:1.30
              command:
                - /bin/bash
                - /scripts/generate-rightsizing-pr.sh
              env:
                - name: NAMESPACES
                  value: "backend-production,frontend-production,data-production"
                - name: CHANGE_THRESHOLD_PERCENT
                  value: "20"
                - name: MIN_SAVINGS_USD
                  value: "5"
                - name: GIT_REPO
                  value: "github.com/company/k8s-manifests.git"
                - name: GIT_BRANCH
                  value: "main"
                - name: GITHUB_TOKEN
                  valueFrom:
                    secretKeyRef:
                      name: rightsizing-secrets
                      key: github-token
              resources:
                requests:
                  cpu: "100m"
                  memory: "128Mi"
                limits:
                  cpu: "500m"
                  memory: "256Mi"
              volumeMounts:
                - name: scripts
                  mountPath: /scripts
                  readOnly: true
          volumes:
            - name: scripts
              configMap:
                name: rightsizing-scripts
                defaultMode: 0755
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: rightsizing-scripts
  namespace: kubecost
data:
  generate-rightsizing-pr.sh: |
    #!/bin/bash
    set -euo pipefail

    echo "=== 리소스 라이트사이징 PR 생성기 ==="
    echo "대상 네임스페이스: ${NAMESPACES}"
    echo "변경 임계값: ${CHANGE_THRESHOLD_PERCENT}%"
    echo "최소 절감 금액: $${MIN_SAVINGS_USD}/월"

    CHANGES_FOUND=0
    REPORT=""

    IFS=',' read -ra NS_ARRAY <<< "${NAMESPACES}"
    for NS in "${NS_ARRAY[@]}"; do
      echo ""
      echo "--- 네임스페이스: ${NS} ---"

      # VPA 목록 조회
      VPAS=$(kubectl get vpa -n "${NS}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

      if [ -z "${VPAS}" ]; then
        echo "[SKIP] VPA가 없습니다."
        continue
      fi

      for VPA_NAME in ${VPAS}; do
        # VPA 추천값 조회
        TARGET_CPU=$(kubectl get vpa "${VPA_NAME}" -n "${NS}" \
          -o jsonpath='{.status.recommendation.containerRecommendations[0].target.cpu}' 2>/dev/null || echo "")
        TARGET_MEM=$(kubectl get vpa "${VPA_NAME}" -n "${NS}" \
          -o jsonpath='{.status.recommendation.containerRecommendations[0].target.memory}' 2>/dev/null || echo "")

        if [ -z "${TARGET_CPU}" ] || [ -z "${TARGET_MEM}" ]; then
          echo "[SKIP] ${VPA_NAME}: 추천값이 없습니다."
          continue
        fi

        # 현재 Deployment 리소스 조회
        DEPLOY_NAME=$(kubectl get vpa "${VPA_NAME}" -n "${NS}" \
          -o jsonpath='{.spec.targetRef.name}' 2>/dev/null || echo "")

        if [ -z "${DEPLOY_NAME}" ]; then
          continue
        fi

        CURRENT_CPU=$(kubectl get deployment "${DEPLOY_NAME}" -n "${NS}" \
          -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}' 2>/dev/null || echo "")
        CURRENT_MEM=$(kubectl get deployment "${DEPLOY_NAME}" -n "${NS}" \
          -o jsonpath='{.spec.template.spec.containers[0].resources.requests.memory}' 2>/dev/null || echo "")

        echo "[CHECK] ${DEPLOY_NAME}: 현재 CPU=${CURRENT_CPU}, MEM=${CURRENT_MEM} → 추천 CPU=${TARGET_CPU}, MEM=${TARGET_MEM}"

        REPORT="${REPORT}\n| ${NS} | ${DEPLOY_NAME} | ${CURRENT_CPU} | ${TARGET_CPU} | ${CURRENT_MEM} | ${TARGET_MEM} |"
        CHANGES_FOUND=$((CHANGES_FOUND + 1))
      done
    done

    if [ ${CHANGES_FOUND} -eq 0 ]; then
      echo ""
      echo "[INFO] 변경이 필요한 워크로드가 없습니다."
      exit 0
    fi

    echo ""
    echo "=== ${CHANGES_FOUND}개 워크로드에 대한 라이트사이징 추천이 발견되었습니다 ==="
    echo ""
    echo "| Namespace | Deployment | Current CPU | Rec. CPU | Current Mem | Rec. Mem |"
    echo "|-----------|------------|-------------|----------|-------------|----------|"
    echo -e "${REPORT}"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rightsizing-automation
  namespace: kubecost
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: rightsizing-reader
rules:
  - apiGroups: ["autoscaling.k8s.io"]
    resources: ["verticalpodautoscalers"]
    verbs: ["get", "list"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: rightsizing-reader-binding
subjects:
  - kind: ServiceAccount
    name: rightsizing-automation
    namespace: kubecost
roleRef:
  kind: ClusterRole
  name: rightsizing-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## 7. 비용 최적화 거버넌스

거버넌스는 비용 최적화를 일회성 활동이 아닌 지속적인 조직 프로세스로 만드는 핵심 요소입니다. 정책 자동화와 정기 리뷰를 통해 비용 효율성을 조직 문화에 내재화합니다.

### 7.1 유휴 리소스 자동 탐지

유휴 리소스는 비용 낭비의 가장 큰 원인 중 하나입니다. PromQL 쿼리를 활용하여 다양한 유형의 유휴 리소스를 자동으로 탐지합니다.

**CPU 사용률이 5% 미만인 Deployment:**

```promql
# 24시간 동안 평균 CPU 사용률이 요청량의 5% 미만인 Deployment 탐지
# 최소 CPU Request가 100m 이상인 워크로드만 대상 (너무 작은 것은 제외)
sum by (namespace, deployment) (
  rate(container_cpu_usage_seconds_total{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    container!=""
  }[24h])
)
/
sum by (namespace, deployment) (
  kube_pod_container_resource_requests{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    resource="cpu",
    container!=""
  }
) < 0.05
and
sum by (namespace, deployment) (
  kube_pod_container_resource_requests{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    resource="cpu",
    container!=""
  }
) > 0.1
```

**메모리 사용률이 20% 미만인 Deployment:**

```promql
# 24시간 동안 평균 메모리 사용률이 요청량의 20% 미만인 Deployment 탐지
# 최소 Memory Request가 256Mi 이상인 워크로드만 대상
sum by (namespace, deployment) (
  container_memory_working_set_bytes{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    container!=""
  }
)
/
sum by (namespace, deployment) (
  kube_pod_container_resource_requests{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    resource="memory",
    container!=""
  }
) < 0.2
and
sum by (namespace, deployment) (
  kube_pod_container_resource_requests{
    namespace!~"kube-system|monitoring|istio-system|kubecost",
    resource="memory",
    container!=""
  }
) > 268435456
```

**미사용 PersistentVolumeClaim 탐지:**

```promql
# Pod에 마운트되지 않은 PVC 탐지 (bound 상태이지만 실제로 사용되지 않음)
kube_persistentvolumeclaim_status_phase{phase="Bound"}
unless on(namespace, persistentvolumeclaim)
kube_pod_spec_volumes_persistentvolumeclaims_info
```

**Replica가 0인 Deployment (장기 비활성):**

```promql
# 7일 이상 replica가 0인 Deployment 탐지
# 스케일 다운된 상태로 방치된 리소스를 찾아 정리 검토
kube_deployment_spec_replicas{
  namespace!~"kube-system|monitoring|istio-system"
} == 0
and
time() - kube_deployment_created{
  namespace!~"kube-system|monitoring|istio-system"
} > 604800
```

### 7.2 비용 정책 (Kyverno)

Kyverno 정책을 통해 비용 관련 규칙을 자동으로 적용합니다. 리소스 한도 미설정 방지, 과다 프로비저닝 경고 등을 자동화합니다.

**리소스 Limits 필수 정책:**

```yaml
# kyverno-require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: "리소스 Limits 필수 설정"
    policies.kyverno.io/description: >-
      모든 컨테이너에 CPU와 Memory Limits가 설정되어야 합니다.
      Limits가 없으면 노드의 리소스를 무제한으로 사용하여 비용 초과와
      다른 워크로드에 영향을 줄 수 있습니다.
    policies.kyverno.io/category: "FinOps"
    policies.kyverno.io/severity: "high"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-resource-limits
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
                - DaemonSet
                - Job
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
      validate:
        message: >-
          모든 컨테이너에 CPU와 Memory Limits를 설정해야 합니다.
          비용 관리와 노드 안정성을 위해 필수 설정입니다.
          예시:
            resources:
              requests:
                cpu: "100m"
                memory: "128Mi"
              limits:
                cpu: "500m"
                memory: "512Mi"
        foreach:
          - list: "request.object.spec.template.spec.containers[]"
            deny:
              conditions:
                any:
                  - key: "{{ element.resources.limits.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.limits.memory || '' }}"
                    operator: Equals
                    value: ""
    - name: check-resource-requests
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
                - DaemonSet
                - Job
              namespaces:
                - "!kube-system"
                - "!kube-public"
                - "!kube-node-lease"
      validate:
        message: >-
          모든 컨테이너에 CPU와 Memory Requests를 설정해야 합니다.
          스케줄러가 적절한 노드에 배치하고, 비용을 정확하게 할당하기 위해 필수입니다.
        foreach:
          - list: "request.object.spec.template.spec.containers[]"
            deny:
              conditions:
                any:
                  - key: "{{ element.resources.requests.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.requests.memory || '' }}"
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
    policies.kyverno.io/title: "과다 프로비저닝 리소스 경고"
    policies.kyverno.io/description: >-
      컨테이너의 CPU Limits가 4 코어를 초과하거나 Memory Limits가 8Gi를 초과하는 경우
      경고를 발생시킵니다. 대부분의 마이크로서비스는 이보다 적은 리소스로 충분하며,
      과다 프로비저닝은 비용 낭비의 주요 원인입니다.
    policies.kyverno.io/category: "FinOps"
    policies.kyverno.io/severity: "medium"
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: warn-high-cpu-limits
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
              namespaces:
                - "!kube-system"
                - "!monitoring"
                - "!data-production"
      validate:
        message: >-
          컨테이너 {{ element.name }}의 CPU Limits가 4 코어를 초과합니다 (현재: {{ element.resources.limits.cpu }}).
          대부분의 마이크로서비스는 4 코어 미만으로 충분합니다.
          이 설정이 필요한 경우 FinOps 팀(#finops-support)에 문의하세요.
        foreach:
          - list: "request.object.spec.template.spec.containers[]"
            deny:
              conditions:
                all:
                  - key: "{{ element.resources.limits.cpu || '0' }}"
                    operator: GreaterThan
                    value: "4000m"
    - name: warn-high-memory-limits
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
              namespaces:
                - "!kube-system"
                - "!monitoring"
                - "!data-production"
      validate:
        message: >-
          컨테이너 {{ element.name }}의 Memory Limits가 8Gi를 초과합니다 (현재: {{ element.resources.limits.memory }}).
          대부분의 마이크로서비스는 8Gi 미만으로 충분합니다.
          이 설정이 필요한 경우 FinOps 팀(#finops-support)에 문의하세요.
        foreach:
          - list: "request.object.spec.template.spec.containers[]"
            deny:
              conditions:
                all:
                  - key: "{{ element.resources.limits.memory || '0' }}"
                    operator: GreaterThan
                    value: "8Gi"
    - name: warn-limits-much-higher-than-requests
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
              namespaces:
                - "!kube-system"
                - "!monitoring"
      validate:
        message: >-
          컨테이너의 CPU Limits가 Requests의 10배를 초과합니다.
          이는 과다 프로비저닝의 징후일 수 있습니다. Limits/Requests 비율을 검토하세요.
          일반적으로 2-4배 이내가 권장됩니다.
        foreach:
          - list: "request.object.spec.template.spec.containers[]"
            deny:
              conditions:
                all:
                  - key: "{{ divide('{{ element.resources.limits.cpu || `0m` }}', '{{ element.resources.requests.cpu || `1m` }}') }}"
                    operator: GreaterThan
                    value: 10
```

### 7.3 정기 비용 리뷰 프로세스

주간과 월간 비용 리뷰를 통해 지속적으로 비용을 관리합니다.

**주간 비용 리뷰 (매주 월요일):**

| 항목 | 담당 | 활동 내용 | 도구 |
|------|------|----------|------|
| 비용 추이 확인 | FinOps Lead | 전주 대비 비용 변화 분석, 이상 항목 식별 | Kubecost Dashboard |
| 효율성 리뷰 | FinOps Lead | CPU/Memory 효율성 40% 미만 네임스페이스 식별 | Grafana Showback |
| 유휴 리소스 점검 | 팀 리더 | 미사용 PVC, 비활성 Deployment 확인 | PromQL Queries |
| 라이트사이징 검토 | 팀 리더 | VPA 추천 검토, PR 생성 요청 여부 결정 | Goldilocks |
| 신규 워크로드 비용 | 팀 리더 | 이번 주 신규 배포 워크로드의 예상 비용 확인 | Kubecost Allocation |
| 액션 아이템 생성 | FinOps Lead | 최적화 기회를 Jira 티켓으로 생성 | Jira/Linear |

**월간 비용 리뷰 (매월 첫째 주):**

| 항목 | 담당 | 활동 내용 | 도구 |
|------|------|----------|------|
| 월간 비용 분석 | FinOps Team | 전월 대비 비용 변화, 팀별 비용 추이 분석 | Kubecost + AWS CUR |
| 예산 대비 실적 | Finance | 팀별 예산 소진율, 초과/절감 내역 정리 | Kubecost Budget |
| 최적화 성과 측정 | FinOps Lead | 라이트사이징, Spot 전환 등 최적화 효과 정량화 | Kubecost Savings |
| RI/SP 활용률 | FinOps Team | Reserved Instances, Savings Plans 활용률 점검 | AWS Cost Explorer |
| 다음 달 예산 조정 | Finance + 팀 리더 | 트렌드 기반 예산 조정, 신규 프로젝트 비용 반영 | Spreadsheet |
| 경영진 보고 | FinOps Lead | 월간 요약, ROI 분석, 추천 사항 리포트 작성 | 프레젠테이션 |

**분기별 비용 전략 리뷰:**

| 항목 | 담당 | 활동 내용 |
|------|------|----------|
| 아키텍처 비용 리뷰 | 아키텍트 + FinOps | 서비스 아키텍처의 비용 효율성 평가 |
| 구매 옵션 최적화 | FinOps Team | RI/SP 구매 또는 갱신 계획 수립 |
| 도구/플랫폼 ROI | FinOps Lead | Kubecost, 모니터링 도구 등의 투자 대비 효과 분석 |
| FinOps 성숙도 평가 | 전체 | Crawl → Walk → Run 성숙도 현황 평가 및 다음 단계 계획 |
| 연간 예산 계획 입력 | Finance | 다음 분기/연간 인프라 비용 예측 및 예산 요청 |

---

## 8. 베스트 프랙티스

### 실전 운영 가이드

1. **태깅부터 시작하라**: 비용 가시성의 정확도는 레이블/태그의 일관성에 100% 의존합니다. Kyverno 등으로 태깅 정책을 강제하고, CI/CD 파이프라인에서 태그 검증을 포함하세요. 태그 없는 리소스는 비용 할당이 불가능합니다.

2. **Showback에서 시작하여 Chargeback으로 진화하라**: 처음부터 Chargeback을 도입하면 정확도 논쟁으로 시간을 낭비합니다. Showback으로 팀에게 비용 인식을 심어주고, 데이터 정확도가 검증된 후에 Chargeback으로 전환하세요. 일반적으로 3-6개월의 Showback 기간이 필요합니다.

3. **공유 비용 분배 규칙을 투명하게 공개하라**: 컨트롤 플레인, 모니터링, 서비스 메시 등 공유 인프라 비용의 분배 방식을 문서화하고 모든 팀에 공유하세요. 불투명한 비용 분배는 신뢰를 떨어뜨리고, FinOps 문화 정착을 방해합니다.

4. **VPA 추천을 자동화하되 적용은 사람이 검토하라**: VPA의 `updateMode: "Off"` 모드로 추천만 수집하고, PR 기반 워크플로우로 팀 리더가 검토 후 적용하세요. 자동 적용(`Auto` 모드)은 프로덕션 서비스에서 예기치 않은 Pod 재시작을 유발할 수 있습니다.

5. **비용 알림의 노이즈를 관리하라**: 알림 임계값을 너무 낮게 설정하면 경보 피로(alert fatigue)가 발생합니다. 시작은 보수적으로(50% 이상 급증만) 설정하고, 운영 경험에 따라 점차 정교화하세요. 심각도별 채널 분리도 중요합니다.

6. **비용 최적화의 ROI를 정량적으로 측정하라**: "비용이 줄었다"는 정성적 보고가 아닌, "VPA 라이트사이징으로 월 $1,200 절감", "Spot 전환으로 월 $3,500 절감" 등 정량적 성과를 추적하세요. 이것이 FinOps 투자의 정당성을 유지하는 핵심입니다.

7. **비용 데이터의 정확도를 지속적으로 검증하라**: Kubecost의 비용 추정치와 실제 AWS 청구서를 월간으로 비교하세요. CUR 통합 없이는 10-30%의 오차가 발생할 수 있습니다. 정확도 격차를 발견하면 커스텀 가격 설정이나 CUR 통합을 보완하세요.

8. **팀 자율성을 존중하면서 가드레일을 설정하라**: 각 팀이 예산 범위 내에서 자유롭게 리소스를 사용하도록 하되, 최대 리소스 한도(ResourceQuota), 필수 레이블(Kyverno), 예산 알림 등의 가드레일은 자동으로 적용하세요. 마이크로매니지먼트는 엔지니어링 문화를 해칩니다.

### 안티패턴

| 안티패턴 | 문제점 | 권장 해결책 |
|---------|--------|-----------|
| **비용 최적화 = 무조건 줄이기** | 비용만 줄이다가 성능/안정성 문제 발생. SLA 위반, 장애 대응 지연 등 | 비용과 성능의 균형을 추구. 효율성(비용 대비 성과)을 핵심 지표로 사용 |
| **FinOps = 인프라팀만의 일** | 엔지니어링 팀의 참여 없이 인프라팀만 비용 관리. 실제 최적화 실행이 안됨 | 팀별 비용 대시보드, 셀프서비스 도구, 비용 리뷰 참여를 통해 전 조직 참여 유도 |
| **월 1회 비용 확인** | 한 달이 지난 후에야 비용 초과 발견. 이미 늦음 | 실시간 대시보드, 일일/주간 자동 리포트, 예산 초과 즉시 알림 체계 구축 |
| **모든 리소스에 동일한 정책 적용** | 배치 작업과 실시간 서비스에 동일한 리소스 제한 적용. 비효율 또는 장애 발생 | 워크로드 특성(실시간/배치/ML 등)에 맞는 차별화된 정책과 예산 기준 수립 |

---

## 9. 참고 자료

### 외부 리소스

- [OpenCost 공식 문서](https://www.opencost.io/docs/)
- [Kubecost 공식 문서](https://docs.kubecost.com/)
- [AWS Cost and Usage Report 가이드](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)
- [FinOps Foundation](https://www.finops.org/)
- [FinOps Framework](https://www.finops.org/framework/)
- [Goldilocks 공식 문서](https://goldilocks.docs.fairwinds.com/)
- [Vertical Pod Autoscaler 문서](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [Kyverno 정책 라이브러리](https://kyverno.io/policies/)
- [AWS Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html)

### 내부 관련 문서

- [EKS 비용 최적화](../eks/07-eks-cost-optimization.md) - AWS EKS 환경에서의 비용 최적화 전략
- [리소스 최적화](./10-resource-optimization.md) - Requests/Limits 설정, JVM 튜닝, 프레임워크별 가이드
- [스케일링 전략](./06-scaling-strategies.md) - HPA, VPA, KEDA를 활용한 효율적 스케일링

---

< [이전: 이벤트 용량 계획](./12-event-capacity-planning.md) | [목차](./README.md) | [다음: 없음] >
