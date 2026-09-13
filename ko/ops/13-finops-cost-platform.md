# FinOps 비용 가시성 플랫폼

> **검토 기준**: 2026-09-12. OpenCost 1.121.2 / chart 2.5.31, Kubecost 3.2.4, Kyverno 1.19.1.
> **검증 범위**: Helm 렌더링, Kubernetes 스키마, Terraform 모의 공급자, 로컬 비용 계산·정책 검사. 실제 AWS 청구서 대사와 운영 클러스터 설치를 수행한 결과는 아닙니다.

< [이전: 이벤트 용량 계획](./12-event-capacity-planning.md) | [목차](./README.md) | [다음: Tekton Pipelines](./14-tekton-pipelines.md) >

## 개요

FinOps는 엔지니어링·재무·제품·비즈니스가 기술 지출의 가치를 함께 관리하는 운영 방식입니다. 비용을 줄이는 것만으로 성공을 판단하지 않습니다. 서비스 수준, 성장, 단위 경제성과 비용 귀속의 신뢰도를 함께 봅니다.

이 장에서는 OpenCost의 Kubernetes 할당 모델, AWS 청구 데이터, 팀별 예산을 구분하고 연결합니다. 각 예제의 클러스터 이름·네임스페이스·버킷·IAM 역할은 배포 환경에 맞게 바꿔야 합니다. 설치 명령은 실제 리소스를 만들며, 여기서 수행한 검증은 로컬 검증입니다.

## 1. FinOps 운영 모델

Inform은 데이터 수집·귀속·가시성을, Optimize는 측정에 근거한 개선을, Operate는 책임·예산·검토 절차의 지속성을 다룹니다. 세 단계는 반복됩니다.

![비용 가시성, 검토 후 최적화, 예산과 운영 책임의 반복 과정](../.gitbook/assets/ko-ops-13-finops-cost-platform-0.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-13-finops-cost-platform-0.html)

| 역할 | 책임 |
| --- | --- |
| 플랫폼 | 수집 안정성, 비용 데이터 접근 제어, 도구 업그레이드 |
| 서비스 팀 | 레이블·요청량, 성능 검증, 변경 검토 |
| 재무·FinOps | 청구 대사, 공유 비용 규칙, 예산·예측 |
| 제품·비즈니스 | 단위 비용과 가치, 투자 우선순위 |

Crawl/Walk/Run은 영역별 역량을 설명하는 기준입니다. 모든 조직에 동일한 1–3개월·6–12개월 일정을 적용하지 않습니다. 데이터 품질과 책임이 정착되기 전에 자동 청구나 자동 삭제를 도입하지 않습니다.

## 2. 비용 데이터와 설치

### 2.1 서로 다른 비용 수치

| 수치 | 의미 | 주의점 |
| --- | --- | --- |
| 현재 할당 비용률, USD/시간 | 현재 요청량·사용량과 가격 모델의 비용률 | 한 달 실제 지출이 아님 |
| 기간별 할당 모델 비용 | 명시한 기간의 Kubernetes 비용 귀속 | 수집 누락·모델·보관 기간의 영향 |
| CUR 2.0 / Cost Explorer | AWS 청구 기반 비용 | 갱신 지연, 할인·크레딧·세금·상각 기준 |
| 월말 선형 예상 | 누적 비용 ÷ 완료 일수 × 해당 월 일수 | 추세 변화·계절성을 반영하지 못함 |

AWS EC2의 CPU·메모리는 일반적으로 독립적인 청구 항목이 아닙니다. OpenCost의 코어·GiB 가격은 인스턴스 비용을 나누는 모델입니다. 임의 CPU/RAM 단가나 계약 할인 15%를 다시 곱해 청구액이라고 표시하지 않습니다. Cloud Cost 합계와 같은 인프라의 Allocation 합계를 더하면 이중 계산할 수 있습니다.

### 2.2 OpenCost 설치

[관측 스택](./09-observability-stack.md)의 Prometheus Operator와 ServiceMonitor CRD, `gp3` StorageClass를 전제로 합니다. EKS의 스토리지 구성에 따라 EBS CSI 또는 Auto Mode용 StorageClass가 필요합니다. 예제의 `release: prometheus`가 실제 Prometheus ServiceMonitor selector와 일치해야 합니다.

기존 관측 예제의 7일 보관으로 월초부터의 비용을 복원할 수 없습니다. 월간 분석에는 최소 해당 기간을 포함하는 보관 정책과 용량이 필요합니다. 보관 기간을 늘려도 이미 삭제된 데이터는 돌아오지 않습니다. 아래 exporter PVC는 Prometheus 데이터 PVC를 대신하지 않습니다.

**`opencost-values.yaml`**

```yaml
serviceAccount:
  create: true
  name: opencost
opencost:
  mcp:
    enabled: false
  exporter:
    defaultClusterId: eks-production
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        memory: 2Gi
    persistence:
      enabled: true
      accessMode: ReadWriteOnce
      storageClass: gp3
      size: 10Gi
  prometheus:
    internal:
      enabled: true
      serviceName: prometheus-kube-prometheus-prometheus
      namespaceName: observability
      port: 9090
    external:
      enabled: false
  metrics:
    serviceMonitor:
      enabled: true
      namespace: opencost
      additionalLabels:
        release: prometheus
      honorLabels: true
  customPricing:
    enabled: false
  cloudCost:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm upgrade --install opencost opencost/opencost \
  --version 2.5.31 --namespace opencost --create-namespace \
  -f opencost-values.yaml --wait --timeout 10m
kubectl -n opencost get pods,pvc,svc,servicemonitor
kubectl -n opencost port-forward service/opencost 9090:9090 9003:9003
```

UI는 로컬 `9090`, API는 `9003`입니다. `opencost.prometheus`와 `opencost.cloudCost`를 exporter 아래에 넣으면 설정이 적용되지 않습니다. Chart 2.5.31의 MCP 기본값은 활성화이므로 이 예제는 명시적으로 끕니다. 비용 MCP를 사용할 경우 인증·접근 범위를 별도로 설계하십시오. 문서 검색용 MCP와 비용 데이터용 MCP는 별개입니다.

### 2.3 Kubecost 3.x를 선택하는 경우

OpenCost와 별도의 제품·배포 선택입니다. Kubecost 3.x는 ClickHouse 기반 저장소와 `finops-agent` 수집 구조를 사용합니다. 2.x의 `kubecostModel`·Prometheus·ETL 설정을 그대로 복사하지 않습니다. 기존 2.x 운영 환경은 공식 마이그레이션 절차의 중간 에이전트 버전, 데이터 재수집과 기능 제약을 확인해야 합니다.

새 chart 저장소는 `https://kubecost.github.io/kubecost/`입니다. 아래는 제한된 기능의 설치 시작점입니다. Cluster Controller·Admission Controller·forecasting을 명시적으로 끄며, 기존 저장소와 인스턴스를 그대로 대체하는 업그레이드 명령으로 쓰지 않습니다.

**`kubecost-values.yaml`**

```yaml
global:
  clusterId: eks-production
  defaultStorageClass: gp3
frontend:
  enabled: true
  service:
    type: ClusterIP
localStore:
  enabled: true
  persistentVolume:
    enabled: true
    size: 32Gi
    storageClass: gp3
finopsagent:
  enabled: true
aggregator:
  enabled: true
cloudCost:
  enabled: false
networkCosts:
  enabled: false
clusterController:
  enabled: false
kubecostAdmissionController:
  enabled: false
forecasting:
  enabled: false
ingress:
  enabled: false
telemetry:
  enabled: false
```

```bash
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm template kubecost kubecost/kubecost --version 3.2.4 \
  --namespace kubecost -f kubecost-values.yaml > kubecost-rendered.yaml
# Review storage, RBAC, images and product entitlements before installation.
helm install kubecost kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --create-namespace -f kubecost-values.yaml
```

SSO·세분화 RBAC·다중 클러스터 기능은 사용 제품과 계약의 지원 범위를 확인합니다. SAML/OIDC 설정 키가 있다는 이유만으로 모든 배포에서 기능이 제공되지는 않습니다. `global.acknowledged`는 Enterprise 메이저 업그레이드 확인에 관한 설정이며 일반 설치의 라이선스 허용 스위치가 아닙니다. 내부 ALB도 사용자 인증을 대신하지 않습니다.

### 2.4 CUR 2.0, Athena와 OpenCost Cloud Cost

다음 Terraform은 **새 CUR 2.0 export·두 S3 버킷·Athena workgroup·OpenCost IRSA 역할**을 정의합니다. 기존 버킷/역할을 관리하는 구성이라면 먼저 Terraform 소유권과 import를 확인합니다. 조직 전체 청구 데이터에는 관리 계정의 적절한 권한이 필요합니다.

Glue crawler와 테이블 생성은 이 코드에 포함하지 않습니다. 먼저 Data Exports의 Athena 처리 절차를 따라 첫 파일을 수신하고, export의 **data 폴더만** 대상으로 Glue 테이블과 파티션을 생성·갱신해야 합니다. manifest·메타데이터 폴더를 같은 테이블에 섞지 않습니다. 실제 생성된 데이터베이스와 테이블 이름을 변수에 넣습니다. Lake Formation으로 보호한다면 별도 권한도 필요합니다.

`COST_AND_USAGE_REPORT`는 Data Exports SQL의 원본 테이블 이름이며, Athena에서 모든 사용자가 동일하게 조회할 Glue 테이블 이름이라는 뜻은 아닙니다. CUR 2.0은 기존 CUR의 `year`/`month`와 다른 `billing_period` 파티션을 사용하므로 실제 스키마를 검사합니다.

Data Exports는 SSE-S3로 전달합니다. 전달 버킷을 KMS 전용으로 바꾸는 예제를 그대로 적용하지 않습니다. KMS 보호가 필요하면 공식 문서의 전달 후 암호화 처리와 소비자 권한을 함께 설계합니다. 활성 조회 데이터에 복원 절차가 필요한 보관 계층을 적용하면 Athena 조회가 실패할 수 있습니다.

**`cur.tf`**

```hcl
terraform {
  required_version = ">= 1.12.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "aws" {
  alias  = "billing"
  region = "us-east-1"
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "cur_bucket" {
  type = string
}

variable "results_bucket" {
  type = string
  validation {
    condition     = var.results_bucket != var.cur_bucket
    error_message = "Use separate CUR source and Athena result buckets."
  }
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_issuer" {
  type = string
}

variable "glue_database" {
  type = string
}

variable "glue_table" {
  type = string
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
  arn     = "arn:${data.aws_partition.current.partition}"
  issuer  = trimprefix(trimsuffix(var.oidc_issuer, "/"), "https://")
  buckets = { cur = var.cur_bucket, results = var.results_bucket }
}

resource "aws_s3_bucket" "cost" {
  for_each      = local.buckets
  bucket        = each.value
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "cost" {
  for_each                = aws_s3_bucket.cost
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "cost" {
  for_each = aws_s3_bucket.cost
  bucket   = each.value.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cost" {
  for_each = aws_s3_bucket.cost
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "delivery" {
  bucket = aws_s3_bucket.cost["cur"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowDataExports"
      Effect    = "Allow"
      Principal = { Service = "bcm-data-exports.amazonaws.com" }
      Action    = "s3:PutObject"
      Resource  = "${aws_s3_bucket.cost["cur"].arn}/cur/*"
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account }
        ArnLike = {
          "aws:SourceArn" = "${local.arn}:bcm-data-exports:us-east-1:${local.account}:export/*"
        }
      }
    }]
  })
}

resource "aws_bcmdataexports_export" "cur" {
  provider = aws.billing
  depends_on = [
    aws_s3_bucket_policy.delivery,
    aws_s3_bucket_public_access_block.cost,
    aws_s3_bucket_server_side_encryption_configuration.cost
  ]
  export {
    name = "opencost-cur"
    data_query {
      query_statement = "SELECT * FROM COST_AND_USAGE_REPORT"
      table_configurations = {
        COST_AND_USAGE_REPORT = {
          BILLING_VIEW_ARN                      = "${local.arn}:billing::${local.account}:billingview/primary"
          TIME_GRANULARITY                      = "HOURLY"
          INCLUDE_RESOURCES                     = "TRUE"
          INCLUDE_MANUAL_DISCOUNT_COMPATIBILITY = "FALSE"
          INCLUDE_SPLIT_COST_ALLOCATION_DATA    = "FALSE"
        }
      }
    }
    destination_configurations {
      s3_destination {
        s3_bucket = aws_s3_bucket.cost["cur"].bucket
        s3_prefix = "cur"
        s3_region = var.region
        s3_output_configurations {
          overwrite   = "OVERWRITE_REPORT"
          format      = "PARQUET"
          compression = "PARQUET"
          output_type = "CUSTOM"
        }
      }
    }
    refresh_cadence {
      frequency = "SYNCHRONOUS"
    }
  }
}

resource "aws_athena_workgroup" "opencost" {
  name          = "opencost-cur"
  force_destroy = false
  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 10737418240
    result_configuration {
      output_location       = "s3://${aws_s3_bucket.cost["results"].bucket}/opencost/"
      expected_bucket_owner = local.account
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

resource "aws_iam_role" "opencost" {
  name = "opencost-cur-reader"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.issuer}:aud" = "sts.amazonaws.com"
          "${local.issuer}:sub" = "system:serviceaccount:opencost:opencost"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "opencost" {
  role = aws_iam_role.opencost.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["athena:StartQueryExecution", "athena:StopQueryExecution",
        "athena:GetQueryExecution", "athena:GetQueryResults", "athena:GetWorkGroup"]
        Resource = aws_athena_workgroup.opencost.arn
      },
      {
        Effect = "Allow"
        Action = ["glue:GetDatabase", "glue:GetDatabases", "glue:GetTable",
        "glue:GetTables", "glue:GetPartitions"]
        Resource = [
          "${local.arn}:glue:${var.region}:${local.account}:catalog",
          "${local.arn}:glue:${var.region}:${local.account}:database/${var.glue_database}",
          "${local.arn}:glue:${var.region}:${local.account}:table/${var.glue_database}/${var.glue_table}"
        ]
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetBucketLocation"
        Resource = [for b in aws_s3_bucket.cost : b.arn]
      },
      {
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.cost["cur"].arn
        Condition = { StringLike = { "s3:prefix" = ["cur", "cur/*"] } }
      },
      {
        Effect    = "Allow"
        Action    = "s3:ListBucket"
        Resource  = aws_s3_bucket.cost["results"].arn
        Condition = { StringLike = { "s3:prefix" = ["opencost", "opencost/*"] } }
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.cost["cur"].arn}/cur/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = "${aws_s3_bucket.cost["results"].arn}/opencost/*"
      }
    ]
  })
}

output "opencost_role_arn" {
  value = aws_iam_role.opencost.arn
}

output "cur_export_arn" {
  value = aws_bcmdataexports_export.cur.arn
}

output "athena_results" {
  value = "s3://${aws_s3_bucket.cost["results"].bucket}/opencost/"
}
```

`glue_database`와 `glue_table`은 조회 대상만 지정하며 테이블을 생성하지 않습니다. 이 구성의 Athena 조회량 제한 10 GiB는 예시입니다. 실패한 쿼리 원인을 확인하고 데이터량에 맞게 조정하십시오. 시간 단위 레코드를 내보내더라도 보고서가 매시간 도착한다는 의미는 아닙니다.

이 예제는 **IRSA**입니다. 기존 OIDC provider ARN과 issuer를 입력하고, 실제 Pod가 사용하는 ServiceAccount `opencost/opencost`와 신뢰 정책의 `sub`를 맞춥니다. EKS Pod Identity를 선택한다면 IRSA annotation 대신 해당 신뢰 정책과 association을 별도로 구성합니다.

**`cloud-integration.json`**

```json
{
  "aws": {
    "athena": [
      {
        "bucket": "s3://REPLACE_QUERY_RESULTS_BUCKET/opencost/",
        "region": "ap-northeast-2",
        "database": "REPLACE_GLUE_DATABASE",
        "catalog": "AwsDataCatalog",
        "table": "REPLACE_GLUE_TABLE",
        "workgroup": "opencost-cur",
        "account": "123456789012",
        "authorizer": {
          "authorizerType": "AWSServiceAccount"
        }
      }
    ]
  }
}
```

**`opencost-cloud-values.yaml`**

```yaml
serviceAccount:
  create: true
  name: opencost
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/opencost-cur-reader
opencost:
  cloudIntegrationSecret: opencost-cloud-integrations
  cloudCost:
    enabled: true
```

```bash
# Replace all placeholders and account IDs in the files first.
kubectl -n opencost create secret generic opencost-cloud-integrations \
  --from-file=cloud-integration.json=cloud-integration.json \
  --dry-run=client -o yaml | kubectl apply -f -
helm upgrade opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml -f opencost-cloud-values.yaml
```

JSON의 `bucket`은 **Athena 결과 버킷**입니다. CUR 원본 버킷이 아닙니다. `AWSServiceAccount` authorizer는 AWS SDK 기본 자격 증명 체인을 사용하므로 정적 Access Key를 넣지 않습니다. 실제 읽기 권한·조회 결과 쓰기 권한·Secret 마운트·importer 갱신 시각을 모두 확인해야 청구 데이터 연결이 완료됩니다.

비용 할당 태그 활성화 전에는 원하는 열/키가 없을 수 있습니다. 현재 AWS는 관리 계정에서 최대 12개월의 비용 할당 태그 backfill을 지원하지만, 해당 기간에 리소스에 태그가 실제로 존재해야 하며 반영에 시간이 걸립니다. 태그를 나중에 붙여 과거 사실을 새로 만들어 내는 기능은 아닙니다.

## 3. Showback과 Chargeback

Showback은 사용 조직에 비용을 보여주는 절차이며, Chargeback은 합의한 회계 규칙에 따라 비용을 배분·청구하는 절차입니다. 모델 값이 곧 내부 청구 금액이 되지는 않습니다. 기간·통화·직접/공유/유휴 비용·미귀속 비용·세금·크레딧·환불·반올림 규칙을 먼저 합의합니다.

### 3.1 레이블과 정책

네임스페이스의 `team`은 팀 집계에, Pod template의 `team`·`cost-center`는 세부 귀속에 사용합니다. Pod 메타데이터와 AWS 비용 할당 태그는 별개의 데이터입니다. 레이블이 없더라도 네임스페이스 귀속은 가능하지만 팀 매핑을 보장하지 않습니다.

Kyverno 1.19.1은 기존 ClusterPolicy에 폐기 예정 경고를 표시합니다. 새 예제는 `policies.kyverno.io/v1`의 CEL `ValidatingPolicy`를 사용합니다. 이 CRD와 해당 버전의 컨트롤러가 필요합니다. `finops.example.com/enabled=true` 네임스페이스만 대상으로 하며 Pod controller의 template 검사도 자동 생성합니다.

**`cost-labels.yaml`**

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: finops-pod-labels
spec:
  validationActions: [Audit]
  evaluation:
    admission:
      enabled: true
    background:
      enabled: true
  autogen:
    podControllers:
      controllers: [deployments, statefulsets, daemonsets, jobs, cronjobs]
  matchConstraints:
    namespaceSelector:
      matchLabels:
        finops.example.com/enabled: "true"
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
  validations:
    - expression: >-
        ['team', 'cost-center'].all(label,
          object.metadata.?labels[label].orValue('') != '')
      message: "Add team and cost-center labels to the Pod template."
```

**`resource-requests.yaml`**

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: finops-container-requests
spec:
  validationActions: [Audit]
  evaluation:
    admission:
      enabled: true
    background:
      enabled: true
  autogen:
    podControllers:
      controllers: [deployments, statefulsets, daemonsets, jobs, cronjobs]
  matchConstraints:
    namespaceSelector:
      matchLabels:
        finops.example.com/enabled: "true"
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [pods]
  validations:
    - expression: >-
        object.spec.containers.all(c,
          has(c.resources) && has(c.resources.requests) &&
          ['cpu', 'memory'].all(r,
            r in c.resources.requests &&
            quantity(c.resources.requests[r]).isGreaterThan(quantity('0'))))
      message: "Set positive CPU and memory requests for each regular container."
```

`Audit`는 위반을 차단하지 않습니다. background scan의 보고서와 적용 범위를 확인하고 소유자와 개선한 뒤 필요한 정책만 `Deny`로 전환합니다. 사용자에게 경고도 보내려면 `Warn` 동작을 별도로 선택합니다. 로컬 CLI는 Audit 정책에서도 테스트 위반을 실패로 반환할 수 있으므로 이를 실제 admission 차단과 혼동하지 않습니다.

요청량 정책은 **일반 컨테이너 각각의 양수 CPU·메모리 request**만 검사합니다. init container·Pod-level resource 예산과 limit 전략은 별도 정책입니다. 모든 서비스에 CPU 4개·메모리 8Gi 상한을 일률 적용한다고 적정 크기가 검증되지는 않습니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-backend
  labels:
    team: backend
    finops.example.com/enabled: "true"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-capacity
  namespace: team-backend
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    requests.storage: 200Gi
    persistentvolumeclaims: "20"
    pods: "100"
```

이 Quota는 예시 자원 상한입니다. 달러 예산이나 모든 클라우드 지출을 제한하는 기능이 아닙니다. 기존 사용량과 autoscaling 최댓값을 고려해 정하고, 초과로 생성이 거부되는 경우를 운영 절차에 포함합니다.

### 3.2 기간별 할당 API

아래 경로는 OpenCost 1.121.2의 `/allocation/compute`를 사용합니다. API의 기간·집계·응답 구조는 제품과 버전별로 확인합니다. `includeIdle`과 `shareIdle`은 boolean이며 `shareIdle=weighted`가 아닙니다.

```bash
curl --fail --silent --show-error --get \
  'http://127.0.0.1:9003/allocation/compute' \
  --data-urlencode 'window=2026-09-01T00:00:00Z,2026-09-12T00:00:00Z' \
  --data-urlencode 'aggregate=namespace' \
  --data-urlencode 'includeIdle=true' \
  --data-urlencode 'shareIdle=false'
```

### 3.3 공유 비용 배분과 합계 보존

다음 값은 **실제 청구서가 아닌 계산 검증용 가상 USD 데이터**입니다. 직접 비용 6,500, 공유 비용 2,500, 유휴 비용 1,000의 서로 겹치지 않는 풀을 사용합니다. 공유 비용은 직접 비용 비중으로, 유휴 비용은 세 팀에 균등 배분합니다. 센트 미만의 나머지는 largest remainder 규칙으로 배분하고 동률은 팀 이름 순으로 정합니다.

![합계 10,000달러를 직접·공유·유휴 비용으로 나누고 반올림 합계를 보존하는 예제](../.gitbook/assets/ko-ops-13-finops-cost-platform-1.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-13-finops-cost-platform-1.html)

```text
Team     Direct    Shared     Idle      Total
A        3000.00   1153.85    333.34     4487.19
B        2000.00    769.23    333.33     3102.56
C        1500.00    576.92    333.33     2410.25
Total    6500.00   2500.00   1000.00    10000.00
```

**`allocation-example.json`**

```json
{
  "description": "Synthetic reconciled expense pool, not an actual account bill.",
  "currency": "USD",
  "direct": {
    "team-a": "3000.00",
    "team-b": "2000.00",
    "team-c": "1500.00"
  },
  "shared": "2500.00",
  "idle": "1000.00",
  "unallocated": "0.00"
}
```

**`allocate_costs.py`**

```python
"""Allocate one reconciled USD expense pool using explicit, conserved cent amounts."""
import argparse
import json
from decimal import Decimal
from fractions import Fraction


def cents(value):
    if isinstance(value, bool):
        raise ValueError("Money cannot be boolean")
    value=Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError("Use finite nonnegative expense amounts; handle refunds explicitly")
    scaled=value*100
    if scaled != scaled.to_integral_value():
        raise ValueError("Settle source amounts to cents under an approved rounding policy first")
    return int(scaled)


def money(value):
    return f"{Decimal(value)/100:.2f}"


def distribute(total, weights):
    if not weights:
        raise ValueError("At least one allocation target is required")
    rational={}
    for name, weight in weights.items():
        value=Decimal(str(weight))
        if not value.is_finite() or value < 0:
            raise ValueError("Weights must be finite and nonnegative")
        rational[name]=Fraction(value)
    denominator=sum(rational.values(),Fraction(0))
    if denominator==0:
        if total:
            raise ValueError("A positive pool cannot be allocated with zero total weight")
        return {name:0 for name in weights}
    exact={name:Fraction(total)*weight/denominator for name,weight in rational.items()}
    result={name:value.numerator//value.denominator for name,value in exact.items()}
    remainder=total-sum(result.values())
    # Largest remainder; ties resolved by stable target name.
    order=sorted(exact,key=lambda name:(-(exact[name]-result[name]),name))
    for name in order[:remainder]:
        result[name]+=1
    assert sum(result.values())==total
    return result


def allocate(config):
    if config.get("currency")!="USD":
        raise ValueError("This example accepts a single USD ledger; do not mix currencies")
    direct={name:cents(value) for name,value in config["direct"].items()}
    if not direct:
        raise ValueError("No teams supplied")
    shared=cents(config["shared"])
    idle=cents(config["idle"])
    unallocated=cents(config.get("unallocated","0"))
    shared_alloc=distribute(shared,direct)
    idle_alloc=distribute(idle,{name:1 for name in direct})
    teams={name:{"direct":money(value),"shared":money(shared_alloc[name]),"idle":money(idle_alloc[name]),
                 "total":money(value+shared_alloc[name]+idle_alloc[name])} for name,value in sorted(direct.items())}
    source_total=sum(direct.values())+shared+idle+unallocated
    allocated_total=sum(cents(value["total"]) for value in teams.values())+unallocated
    assert source_total==allocated_total
    return {"currency":"USD","policy":"Shared weighted by direct cost; idle split equally; unallocated retained",
            "rounding":"Exact cents; largest remainder with lexical tie-break",
            "teams":teams,"unallocated":money(unallocated),"source_total":money(source_total),
            "allocated_total":money(allocated_total),
            "limits":["Use one reconciled pool; do not add overlapping Allocation and Cloud Cost totals.",
                      "This policy is an example, not an inherently fair or mandatory chargeback rule.",
                      "Refunds, credits, taxes and currency conversion require explicit separate policies."]}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("input")
    args=parser.parse_args()
    try:
        with open(args.input,encoding="utf-8") as stream:
            result=allocate(json.load(stream))
    except (ValueError,KeyError,ArithmeticError) as error:
        parser.error(str(error))
    print(json.dumps(result,ensure_ascii=False,indent=2))
```

```bash
python3 allocate_costs.py allocation-example.json
```

배분되지 않은 금액을 삭제하지 않고 `unallocated`로 남깁니다. 이 계산기는 음수 비용·환불을 자동 재배분하지 않습니다. 실제 회계 규칙에서는 크레딧과 환불, 통화 변환을 별도로 처리합니다. 이 예시 정책이 조직에 가장 공정한 규칙이라는 뜻도 아닙니다.

### 3.4 Prometheus와 Grafana

다음 rule은 **한 클러스터의 Prometheus**를 전제로 합니다. 중앙 Prometheus/Thanos에서 여러 클러스터를 조회한다면 모든 집계·join 키에 실제 클러스터 식별자를 유지하십시오. 노드 이름만으로 여러 클러스터를 연결하면 비용이 섞일 수 있습니다.

`node_cpu_hourly_cost`는 코어당, `node_ram_hourly_cost`는 GiB당 시간 비용입니다. allocation 지표와 곱하며 같은 시계열의 중복 scrape는 `max`로 제거합니다. 이름이 비슷한 `kubecost_container_cpu_cost` 같은 존재하지 않는 지표를 사용하지 않습니다. label join 전에 다음 kube-state-metrics 설정을 기존 관측 chart values에 병합합니다.

```yaml
kube-state-metrics:
  metricLabelsAllowlist:
    - namespaces=[team]
```

**`cost-rules.yaml`**

```yaml
groups:
  - name: finops-current-rates
    rules:
      - record: finops:node_cpu_hourly_cost
        expr: max by (node) (node_cpu_hourly_cost)
      - record: finops:node_ram_hourly_cost
        expr: max by (node) (node_ram_hourly_cost)
      - record: finops:namespace_cpu_cost_per_hour
        expr: |
          sum by (namespace) (
            max by (namespace, pod, container, node) (container_cpu_allocation{container!=""})
            * on (node) group_left finops:node_cpu_hourly_cost
          )
      - record: finops:namespace_ram_cost_per_hour
        expr: |
          sum by (namespace) (
            max by (namespace, pod, container, node) (container_memory_allocation_bytes{container!=""}) / 1073741824
            * on (node) group_left finops:node_ram_hourly_cost
          )
      - record: finops:namespace_compute_cost_per_hour
        expr: finops:namespace_cpu_cost_per_hour + finops:namespace_ram_cost_per_hour
      - record: finops:team_compute_cost_per_hour
        expr: |
          sum by (label_team) (
            finops:namespace_compute_cost_per_hour
            * on (namespace) group_left (label_team)
              max by (namespace, label_team) (kube_namespace_labels{label_team!=""})
          )
      - alert: OpenCostMetricsUnavailable
        expr: absent(node_cpu_hourly_cost)
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "OpenCost CPU pricing metrics are absent"
      - alert: KubernetesComputeRateAboveReviewThreshold
        expr: sum(finops:namespace_compute_cost_per_hour) > 20
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Allocated compute model exceeds the example USD 20/hour threshold"
```

위 파일은 Prometheus rule 파일 형식입니다. Operator에서는 `PrometheusRule.spec` 아래로 넣고, 해당 리소스를 실제 Prometheus rule selector가 선택하도록 metadata label을 맞춥니다. 20 USD/시간·30분은 예시 검토 임계값이며 모델 기반 값입니다. `for`는 조건의 지속 시간을 요구할 뿐 오탐을 없애지 않습니다.

Grafana 패널은 `finops:namespace_compute_cost_per_hour`와 `finops:team_compute_cost_per_hour`를 사용하고 단위를 **USD/hour**로 표시합니다. CPU/RAM만의 할당 비용률이며 스토리지·네트워크·컨트롤 플레인·유휴 비용을 모두 포함한 청구액이 아닙니다. `* 730` 패널을 추가한다면 “고정 730시간 예상”으로 표시해야 합니다. 현재 가격이 사라지면 비용 0으로 대체하지 말고 데이터 누락을 표시합니다.

팀 레이블이 없는 네임스페이스는 팀별 집계에서 빠질 수 있으므로 전체 네임스페이스 합계와 팀 합계의 차이도 확인합니다. namespace 변수나 dashboard folder는 데이터 접근 권한 경계가 아닙니다. 팀 격리가 필요하면 데이터 소스의 서버 측 권한 또는 별도의 테넌트를 구성하고 다른 팀 조회가 거부되는지 테스트합니다.

## 4. 청구 기반 이상 탐지

AWS Cost Anomaly Detection의 `DIMENSIONAL` / `SERVICE` monitor는 서비스별 전체 AWS 비용을 다룹니다. 이름에 “EKS”를 붙여도 EKS 전용이 되지 않습니다. 태그·연결 계정·Cost Category 기반 CUSTOM monitor는 실제 지원 범위와 비용 데이터 가용성을 확인합니다. 기존 monitor가 있다면 ARN을 재사용합니다.

다음은 앞의 Terraform 파일과 같은 디렉터리에 두는 선택 구성입니다. EMAIL 요약은 `DAILY`, SNS는 `IMMEDIATE`로 나눕니다. SNS의 IMMEDIATE도 청구 데이터 갱신과 이상 탐지 이후이므로 실시간 과금 차단이 아닙니다. SNS topic에는 별도로 승인된 구독자가 필요합니다. 예제 자체가 Slack 구독을 만들지 않습니다.

**`anomaly.tf`**

```hcl
# Optional: supply an existing monitor ARN to avoid duplicating a SERVICE monitor.
variable "cost_monitor_arn" {
  type = string
}

variable "notification_email" {
  type = string
}

resource "aws_ce_anomaly_subscription" "daily" {
  provider         = aws.billing
  name             = "daily-cost-anomalies"
  frequency        = "DAILY"
  monitor_arn_list = [var.cost_monitor_arn]
  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = ["100"]
    }
  }
  subscriber {
    type    = "EMAIL"
    address = var.notification_email
  }
}

resource "aws_sns_topic" "anomalies" {
  provider = aws.billing
  name     = "cost-anomalies"
}

resource "aws_sns_topic_policy" "anomalies" {
  provider = aws.billing
  arn      = aws_sns_topic.anomalies.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "costalerts.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.anomalies.arn
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account }
        ArnLike = {
          "aws:SourceArn" = "${local.arn}:ce::${local.account}:anomalysubscription/*"
        }
      }
    }]
  })
}

resource "aws_ce_anomaly_subscription" "immediate" {
  provider         = aws.billing
  depends_on       = [aws_sns_topic_policy.anomalies]
  name             = "immediate-cost-anomalies"
  frequency        = "IMMEDIATE"
  monitor_arn_list = [var.cost_monitor_arn]
  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = ["100"]
    }
  }
  subscriber {
    type    = "SNS"
    address = aws_sns_topic.anomalies.arn
  }
}
```

리소스 생성이나 구독 설정에는 실제 알림·비용 영향이 있습니다. KMS로 SNS를 암호화한다면 `costalerts.amazonaws.com`에 필요한 키 사용 권한과 SourceAccount/SourceArn 범위를 추가로 구성합니다. 예제의 100 USD 임계값은 조직별로 조정합니다.

AWS Budgets Action은 IAM/SCP 적용 외에도 지원되는 EC2/RDS 작업을 수행할 수 있습니다. 다만 예산 갱신과 동작 범위의 제약이 있으므로 모든 지출을 즉시 멈추는 hard cap이라고 설명하지 않습니다.

## 5. 팀 예산과 정기 리포트

### 5.1 숫자 예산을 명시적으로 입력

namespace annotation의 문자열을 `label_replace`로 바꾼다고 숫자 시계열이 되지 않습니다. 여기서는 USD 예산을 JSON으로 입력하고 실제 숫자로 파싱합니다. 예산이 없으면 비율은 `null`이며, 0·음수 예산과 비정상 숫자는 거부합니다.

**`budgets.json`**

```json
{
  "currency": "USD",
  "namespaces": {
    "backend-production": "3000.00",
    "frontend-production": "2000.00"
  }
}
```

### 5.2 월간 모델 리포트와 선택적 Slack 전달

다음 스크립트는 Python 3.12 표준 라이브러리만 사용합니다. UTC 기준 완료된 날짜까지 조회하며, `--as-of`는 **제외되는 종료 날짜**입니다. 매월 1일에는 직전 완료 월을 보고합니다. API가 비어 있거나 기간 전체가 아닌 여러 step을 반환하면 실패하고 0 USD로 위장하지 않습니다. 실제 데이터 보관 범위와 누락까지 자동 입증하지 않으므로 API warnings와 importer 시각을 확인해야 합니다.

기본 동작은 JSON 파일 생성이며 Slack을 전송하지 않습니다. `--send`와 `--webhook-file`을 함께 지정해야 전송합니다. 서로 다른 채널에는 각각의 incoming webhook이 필요하며 payload의 `channel`로 덮어쓰는 방식은 사용하지 않습니다.

**`report_costs.py`**

```python
"""Read-only OpenCost monthly model-cost report and optional reviewed Slack delivery."""
import argparse
import calendar
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def decimal_value(value, name, positive=False):
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name}: missing/invalid number")
    amount=Decimal(str(value))
    if not amount.is_finite() or (positive and amount <= 0):
        raise ValueError(f"{name}: invalid finite range")
    return amount


def usd(value):
    return format(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP),"f")


def month_window(as_of):
    end=date.fromisoformat(as_of)
    month_reference=end if end.day>1 else end-timedelta(days=1)
    start=month_reference.replace(day=1)
    completed=(end-start).days
    return start,end,completed,calendar.monthrange(start.year,start.month)[1]


def summarize(payload, budgets, as_of):
    start,end,days,month_days=month_window(as_of)
    if not isinstance(payload,dict) or not isinstance(budgets,dict) or not isinstance(budgets.get("namespaces",{}),dict):
        raise ValueError("Expected API and budget JSON objects")
    if budgets.get("currency")!="USD":
        raise ValueError("This report requires an explicitly configured USD cost source and budgets")
    if payload.get("code",200)!=200 or payload.get("status","success")!="success" or payload.get("errors"):
        raise ValueError("Cost API reported an error")
    sets=payload.get("data")
    if not isinstance(sets,list) or len(sets)!=1 or not isinstance(sets[0],dict) or not sets[0]:
        raise ValueError("Expected one nonempty whole-window allocation set; missing data is not zero cost")
    namespace_costs={}
    for namespace,allocation in sets[0].items():
        if not isinstance(allocation,dict) or "totalCost" not in allocation:
            raise ValueError(f"{namespace}: missing allocation cost")
        namespace_costs[namespace]=decimal_value(allocation["totalCost"],namespace)
    total=sum(namespace_costs.values(),Decimal(0))
    rows=[]
    for namespace,cost in sorted(namespace_costs.items(),key=lambda row:(-row[1],row[0])):
        budget=budgets.get("namespaces",{}).get(namespace)
        budget_value=None if budget is None else decimal_value(budget,"budget",positive=True)
        projected=cost*Decimal(month_days)/Decimal(days)
        rows.append({
            "namespace":namespace,
            "model_cost_to_date_usd":usd(cost),
            "linear_month_estimate_usd":usd(projected),
            "budget_usd":None if budget_value is None else usd(budget_value),
            "model_budget_ratio":None if budget_value is None else str(cost/budget_value),
            "linear_estimate_budget_ratio":None if budget_value is None else str(projected/budget_value),
        })
    return {
        "source":"OpenCost allocation model, not an AWS invoice",
        "currency":"USD","window_start":start.isoformat()+"T00:00:00Z",
        "window_end_exclusive":end.isoformat()+"T00:00:00Z",
        "completed_calendar_days":days,"days_in_month":month_days,
        "total_model_cost_to_date_usd":usd(total),
        "total_linear_month_estimate_usd":usd(total*Decimal(month_days)/Decimal(days)),
        "namespaces":rows,"api_warnings":payload.get("warnings",[]),
        "limits":[
            "Linear estimates assume complete coverage and stable daily cost; inspect retention, gaps and importer freshness.",
            "Idle and unallocated buckets are retained; this is not automatic chargeback.",
            "Calendar-to-date model cost, a linear estimate and actual billed cost are different quantities.",
            "Do not add overlapping cloud-billing and Kubernetes-allocation totals."
        ]
    }


def get_allocation(base_url, as_of):
    start,end,_,_=month_window(as_of)
    parsed=urlsplit(base_url)
    if parsed.scheme not in ("http","https") or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
        raise ValueError("Use an HTTP(S) API base URL without credentials, query or fragment")
    query=urlencode({
        "window":start.isoformat()+"T00:00:00Z,"+end.isoformat()+"T00:00:00Z",
        "aggregate":"namespace","includeIdle":"true","shareIdle":"false","resolution":"1m"
    })
    request=Request(base_url.rstrip("/")+"/allocation/compute?"+query,
                    headers={"Accept":"application/json"},method="GET")
    with build_opener(NoRedirect).open(request,timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"Cost API status {response.status}")
        body=response.read(10*1024*1024+1)
    if len(body)>10*1024*1024:
        raise ValueError("Cost API response exceeded the configured limit")
    return json.loads(body,parse_float=Decimal)


def slack_payload(report):
    # Dynamic names stay in plain_text blocks to avoid markup/mention interpretation.
    header=f"Calendar-month Kubernetes model costs — {report['window_end_exclusive'][:10]}"
    blocks=[{"type":"header","text":{"type":"plain_text","text":header}},
            {"type":"section","text":{"type":"plain_text","text":
                f"UTC window: {report['window_start']} to {report['window_end_exclusive']} (exclusive)\n"
                f"Model cost: USD {report['total_model_cost_to_date_usd']}\n"
                f"Linear estimate: USD {report['total_linear_month_estimate_usd']}\n"
                "This is an allocation estimate, not an AWS invoice."}}]
    for row in report["namespaces"][:10]:
        text=f"{row['namespace']}: USD {row['model_cost_to_date_usd']}"
        blocks.append({"type":"section","text":{"type":"plain_text","text":text[:2900]}})
    omitted=max(0,len(report["namespaces"])-10)
    if omitted:
        blocks.append({"type":"section","text":{"type":"plain_text","text":
            f"{omitted} additional buckets are included in the total. See the full JSON report."}})
    return {"blocks":blocks}


def send_slack(payload, webhook_file):
    url=Path(webhook_file).read_text().strip()
    parsed=urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname not in ("hooks.slack.com","hooks.slack-gov.com"):
        raise ValueError("Use a trusted HTTPS Slack incoming-webhook URL file")
    body=json.dumps(payload,ensure_ascii=False).encode()
    request=Request(url,data=body,headers={"Content-Type":"application/json"},method="POST")
    with build_opener(NoRedirect).open(request,timeout=15) as response:
        result=response.read(1024).decode().strip()
        if response.status!=200 or result!="ok":
            raise ValueError("Slack did not acknowledge the message")


def main():
    parser=argparse.ArgumentParser()
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--api-url")
    parser.add_argument("--budgets",required=True)
    parser.add_argument("--as-of",default=datetime.now(timezone.utc).date().isoformat(),
                        help="Exclusive UTC reporting end date")
    parser.add_argument("--report",default="cost-report.json")
    parser.add_argument("--slack-payload",default="slack-payload.json")
    parser.add_argument("--print-report",action="store_true",
                        help="Write model-cost JSON to stdout for controlled log collection")
    parser.add_argument("--send",action="store_true")
    parser.add_argument("--webhook-file")
    args=parser.parse_args()
    try:
        if args.send and not args.webhook_file:
            raise ValueError("--send requires --webhook-file")
        payload=(json.loads(Path(args.input).read_text(),parse_float=Decimal) if args.input
                 else get_allocation(args.api_url,args.as_of))
        budgets=json.loads(Path(args.budgets).read_text(),parse_float=Decimal)
        report=summarize(payload,budgets,args.as_of)
        slack=slack_payload(report)
        Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        Path(args.slack_payload).write_text(json.dumps(slack,ensure_ascii=False,indent=2)+"\n")
        if args.print_report:
            print(json.dumps(report,ensure_ascii=False))
        if args.send:
            send_slack(slack,args.webhook_file)
        print(f"Report written: {args.report}; Slack delivery: {'requested' if args.send else 'disabled'}")
    except (ValueError,KeyError,ArithmeticError,OSError) as error:
        parser.exit(1,f"Cost report failed: {error}\n")


if __name__=="__main__":
    main()
```

```bash
python3 report_costs.py \
  --api-url http://127.0.0.1:9003 \
  --budgets budgets.json --as-of 2026-09-12 \
  --report cost-report.json --slack-payload slack-payload.json
```

가상 데이터로 총 모델 비용 **1,610.10 USD**, 월말 선형 예상 **4,391.18 USD**를 검증했습니다. 이는 사용자 계정의 비용이 아닙니다. 전체 기간 30일인 9월의 완료 일수 11일을 사용한 예측이며, 고정 730시간 계산과 다릅니다.

### 5.3 CronJob 실행

스크립트와 예산 파일을 ConfigMap에 넣습니다. 아래 CronJob은 매일 **한국 시간 09:00**에 실행되고 Slack 전송 없이 보고서를 stdout에 기록합니다. 데이터의 날짜 경계는 여전히 UTC입니다. 로그에는 내부 비용 정보가 있으므로 로그 접근 권한과 보관 정책을 설정합니다. `emptyDir` 출력 파일은 Pod 삭제 시 사라집니다.

```bash
kubectl -n opencost create configmap finops-report-code \
  --from-file=report_costs.py --from-file=budgets.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

**`reporter-cronjob.yaml`**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: finops-report
  namespace: opencost
spec:
  schedule: "0 9 * * *"
  timeZone: Asia/Seoul
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 1800
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 180
      template:
        spec:
          automountServiceAccountToken: false
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
            - name: report
              image: python:3.12.13-slim
              command: [python, /app/report_costs.py]
              args:
                - --print-report
                - --api-url
                - http://opencost.opencost.svc.cluster.local:9003
                - --budgets
                - /app/budgets.json
                - --report
                - /output/cost-report.json
                - --slack-payload
                - /output/slack-payload.json
              resources:
                requests:
                  cpu: 50m
                  memory: 64Mi
                limits:
                  memory: 256Mi
              securityContext:
                readOnlyRootFilesystem: true
                allowPrivilegeEscalation: false
                capabilities:
                  drop: [ALL]
              volumeMounts:
                - name: app
                  mountPath: /app
                  readOnly: true
                - name: output
                  mountPath: /output
          volumes:
            - name: app
              configMap:
                name: finops-report-code
            - name: output
              emptyDir: {}
```

배포 전 이미지 digest와 플랫폼 지원을 확인하고 고정합니다. 이 예제의 Python 버전과 표준 라이브러리 코드는 로컬에서 검증했으며, 컨테이너 이미지 pull이나 클러스터 CronJob 실행은 수행하지 않았습니다.

Slack 전달을 운영에서 선택하려면 webhook을 Secret의 파일로 마운트하고 `--send --webhook-file /secrets/webhook`을 추가합니다. webhook을 문서·Git·로그에 쓰지 않습니다. `concurrencyPolicy: Forbid`와 `backoffLimit: 0`은 중복 위험을 줄이지만 exactly-once 전달을 보장하지 않습니다. 응답 유실 뒤 재실행하면 중복 메시지가 생길 수 있으므로 전달 기록과 중복 제거가 필요한지 결정합니다.

## 6. 리소스 라이트사이징

### 6.1 VPA 권장값 수집

VPA recommender와 CRD가 이미 설치된 환경을 전제로 합니다. `Off` 모드로 관측하며 동일 workload를 대상으로 여러 VPA를 만들지 않습니다. Goldilocks가 VPA를 관리한다면 아래 수동 VPA와 중복되지 않도록 합니다. `target`은 권장 request이고 `upperBound`는 반드시 설정해야 하는 limit이 아닙니다.

**`vpa.yaml`**

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: backend-api
  namespace: team-backend
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-api
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        controlledResources: [cpu, memory]
        controlledValues: RequestsOnly
```

Goldilocks는 namespace opt-in과 VPA 권장값을 보여주는 선택적 도구입니다. 설치 시 현재 chart의 VPA 의존성·컨트롤러 권한·대시보드 접근 제어를 확인하고 기존 recommender를 중복 설치하지 않습니다. namespace에 `goldilocks.fairwinds.com/enabled=true`를 부여하는 것만으로 비용 절감이나 변경 승인이 이루어지지는 않습니다.

### 6.2 변경 제안 생성

다음 스크립트는 **클러스터를 변경하거나 PR을 만들지 않습니다**. `kubectl`로 읽은 JSON을 입력받아 Deployment/StatefulSet의 컨테이너 이름을 VPA와 맞추고, request가 20% 이상 감소하는 후보를 출력합니다. 기본 API와 단위 파서를 검증한 `kubernetes==36.0.3` 패키지가 필요합니다.

권장값이 충분한 트래픽·피크·장애 복구 상황을 반영하는지, HPA의 CPU utilization 분모를 바꾸는 영향이 있는지 확인해야 합니다. init container·Pod-level resources는 별도 검토로 남깁니다. 같은 target의 중복 VPA, 모르는 컨테이너, 없는 request는 자동 추정하지 않습니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'kubernetes==36.0.3'
kubectl --context YOUR_CONTEXT get deployments,statefulsets -A -o json > workloads.json
kubectl --context YOUR_CONTEXT get vpa -A -o json > vpas.json
.venv/bin/python recommend_resources.py \
  --workloads workloads.json --vpas vpas.json --threshold 0.20 > proposals.json
```

**`recommend_resources.py`**

```python
#!/usr/bin/env python3
"""Build review proposals from kubectl JSON snapshots; never patch workloads."""
import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from kubernetes.utils.quantity import parse_quantity


def quantity(value):
    parsed = parse_quantity(str(value))
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError("resource quantity must be finite and positive")
    return parsed


def propose(workloads, vpas, threshold=Decimal("0.20")):
    if not Decimal(0) < threshold < Decimal(1):
        raise ValueError("threshold must be between zero and one")
    index = {}
    for w in workloads.get("items", []):
        key = (w["metadata"].get("namespace", "default"), w["kind"], w["metadata"]["name"])
        index[key] = w
    results = []
    targets = Counter(
        (v["metadata"].get("namespace", "default"),
         v.get("spec", {}).get("targetRef", {}).get("kind"),
         v.get("spec", {}).get("targetRef", {}).get("name"))
        for v in vpas.get("items", [])
    )
    for v in vpas.get("items", []):
        namespace = v["metadata"].get("namespace", "default")
        target = v.get("spec", {}).get("targetRef", {})
        key = (namespace, target.get("kind"), target.get("name"))
        row = {"vpa": v["metadata"]["name"], "namespace": namespace,
               "kind": key[1], "workload": key[2], "proposals": [], "warnings": []}
        if target.get("apiVersion") != "apps/v1" or key[1] not in ("Deployment", "StatefulSet"):
            row["warnings"].append("unsupported target: only apps/v1 Deployment/StatefulSet")
        elif targets[key] > 1:
            row["warnings"].append("duplicate VPA target: remove overlap before proceeding")
        elif key not in index:
            row["warnings"].append("target missing from workload snapshot")
        else:
            workload = index[key]
            pod = workload["spec"]["template"]["spec"]
            containers = {c["name"]: c for c in pod["containers"]}
            conditions = v.get("status", {}).get("conditions", [])
            if not any(c.get("type") == "RecommendationProvided" and c.get("status") == "True" for c in conditions):
                row["warnings"].append("RecommendationProvided is not True")
            else:
                recommendations = v.get("status", {}).get("recommendation", {}).get("containerRecommendations", [])
                if not recommendations:
                    row["warnings"].append("recommendations missing")
                for rec in recommendations:
                    name = rec.get("containerName")
                    if name not in containers:
                        row["warnings"].append(f"unknown container {name}")
                        continue
                    container = containers[name]
                    for resource in ("cpu", "memory"):
                        current = container.get("resources", {}).get("requests", {}).get(resource)
                        target_value = rec.get("target", {}).get(resource)
                        if current is None or target_value is None:
                            row["warnings"].append(f"{name}/{resource}: missing current request or target")
                            continue
                        try:
                            current_number, target_number = quantity(current), quantity(target_value)
                            reduction = (current_number - target_number) / current_number
                            limit = container.get("resources", {}).get("limits", {}).get(resource)
                            if limit is not None and target_number > quantity(limit):
                                row["warnings"].append(f"{name}/{resource}: target exceeds existing limit")
                                continue
                        except (ValueError, ArithmeticError) as error:
                            row["warnings"].append(f"{name}/{resource}: invalid quantity ({error})")
                            continue
                        if reduction >= threshold:
                            row["proposals"].append({
                                "container": name, "resource": resource,
                                "currentRequest": current, "proposedRequest": target_value,
                                "requestReductionRatio": str(reduction),
                                "estimatedBillingSavings": None
                            })
                if pod.get("initContainers") or pod.get("resources"):
                    row["warnings"].append("init containers and Pod-level resources require separate review")
        results.append(row)
    return {"mode": "proposal-only", "threshold": str(threshold), "workloads": results,
            "limitations": ["No PR, patch, or cluster change is created.",
                            "VPA history, peak load, HPA interaction, and SLOs require human review.",
                            "Lower requests do not guarantee fewer nodes or billing savings."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workloads", type=Path, required=True)
    parser.add_argument("--vpas", type=Path, required=True)
    parser.add_argument("--threshold", type=Decimal, default=Decimal("0.20"))
    args = parser.parse_args()
    print(json.dumps(propose(json.loads(args.workloads.read_text()),
                             json.loads(args.vpas.read_text()), args.threshold), indent=2))
```

![조회 전용 권장값 수집 후 담당자가 manifest와 PR을 준비하고 검증하는 절차](../.gitbook/assets/ko-ops-13-finops-cost-platform-2.png)

[인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-ops-13-finops-cost-platform-2.html)

출력의 `estimatedBillingSavings`는 `null`입니다. request 감소는 노드 수 감소나 예약 약정 비용 감소를 보장하지 않기 때문입니다. 담당자는 Git의 실제 manifest를 수정하고 성능 테스트·PR 리뷰·배포 후 SLO 관측을 수행합니다. 이를 자동화하려면 저장소 파일 매핑·인증·중복 PR 처리·CI·승인 규칙을 별도로 구현해야 합니다.

## 7. 유휴 후보와 거버넌스

### 7.1 삭제 후보가 아닌 검토 목록

다음 쿼리는 한 클러스터에서 Bound지만 현재 Pod volume reference가 없는 PVC를 찾습니다. gauge의 값이 1인지 비교하고 namespace와 PVC 이름을 함께 사용합니다.

```promql
(kube_persistentvolumeclaim_status_phase{phase="Bound"} == 1)
unless on (namespace, persistentvolumeclaim)
kube_pod_spec_volumes_persistentvolumeclaims_info
```

스케일 0인 StatefulSet의 데이터, 복구용 볼륨, 일시 중지된 작업도 여기에 포함될 수 있습니다. 소유자·복구 요구·마지막 사용·snapshot·보존 정책을 확인하기 전에는 삭제하지 않습니다. Deployment 생성 시각이 7일 전이라는 사실은 replica가 7일 내내 0이었다는 증거가 아닙니다. 연속 이력, 샘플 범위와 누락을 확인해야 합니다.

낮은 CPU·메모리 사용률도 버스트나 대기 워크로드의 특성일 수 있습니다. Pod 데이터를 Deployment로 합칠 때 owner 관계(ReplicaSet → Deployment)와 namespace·cluster 식별자를 유지합니다. 네트워크 receive 값만으로 업무 트래픽이나 자원의 필요성을 판단하지 않습니다.

### 7.2 정기 검토

| 주기 | 확인 내용 |
| --- | --- |
| 일간 | 수집 누락, importer 시각, 이상 비용, 예산 예측 |
| 주간 | 유휴 후보의 소유자 확인, VPA 제안, SLO 영향 |
| 월간 | 실제 청구 대사, 할인·크레딧·미귀속 비용, 공유 규칙, 단위 경제성 |

월간 보고서에는 기간·통화·모델/청구 구분·데이터 갱신 시각·공유 배분 규칙·미귀속 금액·승인자를 기록합니다. “라벨 100%면 비용 정확도 100%”, “요청량 감소율이 곧 절감률”, “대시보드 필터가 팀 권한” 같은 가정을 피합니다.

## 8. 참고 자료

- [FinOps Foundation definition](https://www.finops.org/introduction/what-is-finops/)
- [OpenCost 1.121.2 release](https://github.com/opencost/opencost/releases/tag/v1.121.2)
- [OpenCost Helm chart](https://github.com/opencost/opencost-helm-chart)
- [OpenCost API](https://opencost.io/docs/integrations/api/)
- [OpenCost AWS authorizer source](https://github.com/opencost/opencost/blob/v1.121.2/pkg/cloud/aws/authorizer.go)
- [Kubecost chart and migration](https://github.com/kubecost/cost-analyzer-helm-chart)
- [AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-data-exports.html)
- [Data Exports encryption](https://docs.aws.amazon.com/cur/latest/userguide/data-protection.html)
- [Data Exports bucket policy](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-s3-bucket.html)
- [Cost allocation tag backfill](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)
- [Cost anomaly SNS permissions](https://docs.aws.amazon.com/cost-management/latest/userguide/ad-SNS.html)
- [Kyverno CEL migration](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [Goldilocks](https://goldilocks.docs.fairwinds.com/)


- [Observability stack](./09-observability-stack.md)
- [Resource optimization](./10-resource-optimization.md)
- [Event capacity planning](./12-event-capacity-planning.md)
