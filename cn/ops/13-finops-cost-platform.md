# FinOps 成本可见性平台

> **最后更新**：2026 年 10 月 16 日。OpenCost 1.121.3 / chart 2.5.33，Kubecost 3.2.4，Kyverno 1.19.1。
> **验证**：Helm 渲染、Kubernetes schemas、Terraform mock providers、本地成本计算和策略评估。本文不代表已在生产集群上安装，也不代表已与实际 AWS 账单对账。

< [上一章：活动容量规划](./12-event-capacity-planning.md) | [目录](./README.md) | [下一章：Tekton Pipelines](./14-tekton-pipelines.md) >

## 概述

FinOps 将工程、财务、产品和业务团队凝聚在一起，共同管理技术支出的价值。仅降低成本并不是成功标准：服务级别、增长、单位经济效益和可靠的成本归属同样重要。

本章区分 Kubernetes 分摊模型、AWS 账单数据和团队预算，然后将它们关联起来。部署前，请替换示例中的集群名称、命名空间、存储桶和 IAM 角色。安装命令会创建真实资源；本文报告的验证是在本地完成的。

## 1. FinOps 运营模式

Inform 阶段负责数据收集、成本分摊和可见性。Optimize 阶段将度量结果转化为改进。Operate 阶段持续落实所有权、预算和审查。这些阶段会反复进行。

![迭代式可见性、经过审查的优化、预算和所有权](../.gitbook/assets/en-ops-13-finops-cost-platform-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-13-finops-cost-platform-0.html)

| 角色 | 职责 |
| --- | --- |
| 平台 | 可靠的数据收集、成本数据访问控制、升级 |
| 服务团队 | 标签、资源请求、性能测试、变更审查 |
| 财务 / FinOps | 账单对账、共享成本规则、预算和预测 |
| 产品 / 业务 | 单位经济效益、价值和投资优先级 |

Crawl/Walk/Run 描述的是特定领域的能力，而非通用的 1–3 个月或 6–12 个月时间表。在自动执行分摊计费或删除操作之前，应先确保数据质量和所有权明确。

## 2. 成本数据与安装

### 2.1 区分不同度量

| 度量 | 含义 | 局限性 |
| --- | --- | --- |
| 当前成本分摊费率，USD/hour | 当前成本分摊和定价模型 | 不是实际月度支出 |
| 时间窗口内的分摊模型成本 | 在明确时段内进行 Kubernetes 成本归属 | 取决于覆盖范围、保留期限和模型 |
| CUR 2.0 / Cost Explorer | 基于 AWS 账单的成本 | 刷新延迟、折扣、抵扣额、税费和摊销选择 |
| 线性月末估算 | 截至目前的成本 / 已过去的天数 × 当月天数 | 不会考虑季节性或需求变化 |

EC2 CPU 和内存通常不是单独计费的产品。OpenCost 的每核和每 GiB 价格用于分摊实例成本。不要将任意 CPU/RAM 价格或另一个笼统的合同折扣说成账单金额。对同一基础设施，将 Cloud Cost 总额与 Allocation 总额相加可能造成重复计算。

### 2.2 安装 OpenCost

此配置假设已安装 [可观测性堆栈](./09-observability-stack.md) 中的 Prometheus Operator 和 ServiceMonitor CRD，并且有合适的 `gp3` StorageClass。EKS 存储可以使用 EBS CSI driver，也可以使用 Auto Mode 的 StorageClass 配置。示例中的 `release: prometheus` 必须与实际 Prometheus ServiceMonitor selector 相匹配。

此前 Prometheus 的七天数据保留期无法重建完整月份的数据。月度分析需要足够的数据保留期限和存储空间。延长保留期限无法恢复已删除的数据。下面的 exporter PVC 不能取代 Prometheus 存储。

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
  --version 2.5.33 --namespace opencost --create-namespace \
  -f opencost-values.yaml --wait --timeout 10m
kubectl -n opencost get pods,pvc,svc,servicemonitor
kubectl -n opencost port-forward service/opencost 9090:9090 9003:9003
```

本地 UI 使用端口 `9090`；API 使用 `9003`。`opencost.prometheus` 和 `opencost.cloudCost` 不是 exporter 的子项。Chart 2.5.33 默认启用 MCP，因此此基线配置会明确禁用它。如果要通过 MCP 暴露成本工具，请单独设计身份验证和访问范围；成本数据 MCP 与文档搜索 MCP 不同。

### 2.3 选择 Kubecost 3.x

Kubecost 是单独的产品和部署选项。3.x 版本使用 ClickHouse 存储和 `finops-agent` 数据收集。不要原样照搬 2.x 的 `kubecostModel`、Prometheus 或 ETL 设置。现有 2.x 安装需要遵循官方迁移流程，包括中间 agent、重新摄取数据以及功能限制。

当前的 chart 仓库是 `https://kubecost.github.io/kubecost/`。这是一个功能受限的安装基线。它会明确禁用 Cluster Controller、Admission Controller 和 forecasting。不要将其用作现有安装和存储的原位替换命令。

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

检查产品授权是否包含 SSO、细粒度 RBAC 和多集群功能。存在 SAML/OIDC 配置值并不意味着每种部署都启用了这些功能。`global.acknowledged` 用于确认 Enterprise 主版本升级，而非通用许可证接受。内部 ALB 不会对用户进行身份验证。

### 2.4 CUR 2.0、Athena 和 OpenCost Cloud Cost

以下 Terraform 定义了**一个新的 CUR 2.0 导出、两个 S3 存储桶、一个 Athena workgroup 和一个 OpenCost IRSA 角色**。管理现有资源之前，请检查其所有权并考虑导入。组织范围的账单数据需要适当的管理账户权限。

其中不包括 Glue crawler 和表的创建。请遵循 Data Exports Athena 处理流程：等待初始数据交付，然后使用导出的**数据目录**创建并刷新 Glue 表和分区。不要将清单和元数据与数据表混在一起。提供生成的数据库和表名称。Lake Formation 保护需要额外的授权。

`COST_AND_USAGE_REPORT` 是 Data Exports SQL 数据源，并非通用的 Athena Glue 表名。请检查生成的 schema：CUR 2.0 使用 `billing_period` 分区，而不应假设沿用旧版 CUR 的 `year`/`month` 布局。

Data Exports 使用 SSE-S3 交付数据。不要照搬要求直接使用 KMS 加密交付的配置。如果需要 KMS，请一并设计文档所述的交付后加密流程和使用方权限。需要先恢复才能访问的归档存储可能会导致针对活动数据的查询失败。

**`cur.tf`**

```hcl
terraform {
  required_version = ">= 1.12.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
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

`glue_database` 和 `glue_table` 用于指定查询目标；它们不会创建目标。示例 Athena 扫描上限为每次查询 10 GiB：请调查查询失败的原因，并根据数据集大小调整上限。按小时记录不代表报告也会按小时交付。

本例使用 **IRSA**。请提供现有的 OIDC provider ARN 和 issuer，并确保信任策略中的 `sub` 与实际的 `opencost/opencost` ServiceAccount 相匹配。EKS Pod Identity 使用不同的信任策略和关联方式，而非 IRSA annotation。

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
helm upgrade opencost opencost/opencost --version 2.5.33 \
  --namespace opencost -f opencost-values.yaml -f opencost-cloud-values.yaml
```

JSON 中的 `bucket` 是 **Athena 查询结果存储桶**，不是 CUR 源存储桶。`AWSServiceAccount` 使用 AWS SDK 默认凭证链，而非静态访问密钥。在声称账单集成正常工作之前，请验证源数据读取、结果写入、Secret 挂载和导入器数据新鲜度。

成本分摊标签键在激活之前可能不存在。目前 AWS 支持由管理账户回填最多 12 个月的数据，但前提是该期间资源上实际存在这些标签，且还需考虑处理延迟。现在添加标签并不会凭空生成历史标签记录。

## 3. Showback 和 Chargeback

Showback 会让消费团队了解支出情况。Chargeback 则根据约定的会计规则分摊费用并向其计费。模型值不会自动成为内部账单。应先明确周期、币种、直接/共享/闲置/未分配类别、税费、抵扣额、退款和舍入规则。

### 3.1 标签和策略

使用命名空间 `team` 标签进行团队聚合，并使用 Pod 模板中的 `team` / `cost-center` 标签实现更精细的成本归属。Kubernetes 标签和 AWS 成本分摊标签是两种独立的数据。即使没有团队标签，仍可按命名空间进行成本分摊，但无法保证能映射到团队。

Kyverno 1.19.1 会警告 ClusterPolicy 已弃用。新示例使用 `policies.kyverno.io/v1` 中的 CEL `ValidatingPolicy`，需要相应版本的 CRD 和 controller。示例面向带有 `finops.example.com/enabled=true` 标签的命名空间，并为 Pod controller 模板生成检查。

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

`Audit` 不会阻止违规操作。请审查后台报告和作用范围，与负责人一起解决问题，然后将选定策略切换为 `Deny`。如果需要面向用户的警告，请单独选择 `Warn`。本地 CLI 可能会因 Audit 策略而返回测试失败；这并不能证明 admission 会拒绝请求。

请求策略会检查**每个常规容器是否设置了正数的 CPU 和内存请求**。Init-container 和 Pod 级预算及 limit 策略需要单独制定。对所有应用统一设置四核 / 8 GiB 限制，并不能证明应用已正确配置资源。

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

此配额只是资源上限示例，并非美元预算，也不是所有云支出的上限。请结合当前用量和自动扩缩容最大值来确定配额，并为创建请求被拒绝的情况做好准备。

### 3.2 时间窗口分摊 API

此示例使用 OpenCost 1.121.3 的 `/allocation/compute`。请根据产品和版本验证周期、聚合方式及响应结构。`includeIdle` 和 `shareIdle` 是布尔值；`shareIdle=weighted` 并非文档规定的布尔值形式。

```bash
curl --fail --silent --show-error --get \
  'http://127.0.0.1:9003/allocation/compute' \
  --data-urlencode 'window=2026-09-01T00:00:00Z,2026-09-12T00:00:00Z' \
  --data-urlencode 'aggregate=namespace' \
  --data-urlencode 'includeIdle=true' \
  --data-urlencode 'shareIdle=false'
```

### 3.3 共享成本分摊与守恒

这些是**用于验证计算的合成 USD 输入，并非实际账单**。互不重叠的成本池包含 6,500 直接成本、2,500 共享成本和 1,000 闲置成本。共享成本按直接成本加权分摊；闲置成本平均分配。对于不足一分的金额，使用最大余数法，并以团队名称的字典序打破平局。

![经过舍入后总额仍保持不变的合成 USD 10,000 分摊](../.gitbook/assets/en-ops-13-finops-cost-platform-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-13-finops-cost-platform-1.html)

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

将无法归属的金额保留为 `unallocated`。此计算器不会自动重新分配负成本或退款。实际会计工作需要单独制定抵扣额、退款和货币转换规则。示例策略并非对所有组织都天然最公平的选择。

### 3.4 Prometheus 和 Grafana

这些规则假设使用的是**单个集群的 Prometheus**。中央 Prometheus/Thanos 查询必须在每次聚合和联接中保留真实的集群标识符。仅按节点名称联接多个集群可能会混淆成本。

`node_cpu_hourly_cost` 的单位是每核每小时，`node_ram_hourly_cost` 的单位是每 GiB 每小时。将其与分摊指标相乘，并使用 `max` 去重重复抓取的数据。不要虚构 `kubecost_container_cpu_cost` 之类的指标。将此 kube-state-metrics 设置合并到现有的可观测性 chart values 中，然后再联接标签。

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

此文件采用 Prometheus 规则文件格式。使用 Operator 时，请将其放在 `PrometheusRule.spec` 下，并将 metadata 标签设置为与实际规则 selector 相匹配。每小时 20 美元、持续 30 分钟，是基于模型数据的示例审查阈值。`for` 要求条件持续成立；它并不能消除误报。

Grafana 面板可以使用 `finops:namespace_compute_cost_per_hour` 和 `finops:team_compute_cost_per_hour`，并标注为 **USD/hour**。这些是已分摊的 CPU/RAM 费率，不是包含所有存储、网络、控制平面和闲置成本的账单。如果面板使用 `* 730`，应将其标注为固定的 730 小时估算。缺失的价格必须显示为缺失数据，而不是零成本。

没有团队标签的命名空间可能不会出现在团队聚合结果中。请将完整的命名空间总额与团队总额进行比较。Dashboard variables 和文件夹不会强制执行数据源授权。应使用服务端数据源权限或单独租户来隔离团队，并测试跨团队查询是否会被拒绝。

## 4. 基于账单的异常检测

`DIMENSIONAL` / `SERVICE` Cost Anomaly Detection monitor 会监控 AWS 服务支出。将其命名为 “EKS” 并不会将范围限定为 EKS。对于使用标签、关联账户或 Cost Categories 的 CUSTOM monitor，请确认其支持的范围和数据可用性。适当时可复用现有 monitor ARN。

此可选配置应与前面的 Terraform 文件放在一起。将 `DAILY` EMAIL 摘要与 `IMMEDIATE` SNS 通知分开。SNS 通知仍遵循账单更新和异常检测流程；它不会立即停止支出。该 topic 需要经单独批准的订阅者。此示例不会创建 Slack 订阅。

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

创建资源和订阅会产生实际费用并触发实际通知。如果 SNS 使用 KMS 加密，还要为 `costalerts.amazonaws.com` 配置必要的密钥权限，并限制 SourceAccount/SourceArn。请根据组织情况调整示例中的 100 美元阈值。

AWS Budgets Actions 可以执行受支持的 EC2/RDS 操作以及 IAM/SCP 操作。更新延迟和操作范围仍然适用；这不是一个能立即停止所有支出的硬性上限。

## 5. 团队预算和定时报表

### 5.1 明确的数值预算

`label_replace` 不会将命名空间 annotation 中的字符串转换为数值时间序列。本示例从 JSON 读取明确的 USD 预算。缺少预算时，比例为 `null`；零、负数和无效数值预算会被拒绝。

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

### 5.2 月度模型报告和可选的 Slack 发送

此脚本仅使用 Python 3.12 标准库。它查询已完成的 UTC 日期；`--as-of` 是**不包含在内的结束日期**。在每月第一天运行时，它会报告上一个完整月份。数据为空或包含多个时间步时，脚本会失败，而不会返回虚假的 USD 0 结果。脚本无法证明历史数据覆盖完整：请检查 API warnings 和导入器数据新鲜度。

默认情况下，它只会创建 JSON 文件，不会发送 Slack 消息。发送需要同时指定 `--send` 和 `--webhook-file`。不同频道需要不同的 incoming webhook；不会使用 payload 中的 `channel` 覆盖值。

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

使用合成数据验证得到的模型成本总额为 **USD 1,610.10**，线性月末估算为 **USD 4,391.18**。这些并非读者账户中的实际成本。该估算使用了 30 天的 9 月中已完成的 11 天，而非固定的 730 小时预测。

### 5.3 作为 CronJob 运行

将脚本和预算存储在 ConfigMap 中。此 CronJob 按 **Asia/Seoul 时间每天 09:00** 运行，将报告打印到 stdout，不会发送 Slack 消息。报告边界仍使用 UTC。日志包含内部成本信息，因此请配置访问权限和保留期限。Pod 删除后，`emptyDir` 中的输出文件也会消失。

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

部署前请验证镜像 digest 和平台支持情况，然后固定 digest。Python 版本和标准库代码已在本地测试；未执行容器镜像拉取或集群 CronJob 运行。

如需启用 Slack 实际发送，请将 webhook 作为 Secret 文件挂载，并添加 `--send --webhook-file /secrets/webhook`。切勿将其放在文档、Git 或日志中。`concurrencyPolicy: Forbid` 和 `backoffLimit: 0` 可以降低重复发送的风险，但无法保证恰好投递一次。确认丢失后重试可能会重复发送消息；请决定是否需要投递记录表和去重机制。

## 6. 资源优化

### 6.1 收集 VPA 建议

此示例假设 VPA recommender 和 CRD 已安装。请以 `Off` 模式进行观察，并避免多个 VPA 指向同一工作负载。如果 Goldilocks 管理 VPA，请勿再使用手动示例重复创建。`target` 是建议的 request；`upperBound` 并非强制的容器 limit。

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

Goldilocks 是一个可选的 dashboard，用于展示选择启用该功能的命名空间中的 VPA 建议。安装前请检查当前 chart 依赖项、controller 权限和 dashboard 访问权限；不要重复添加 recommender。为命名空间添加 `goldilocks.fairwinds.com/enabled=true` 标签本身并不会节省成本或批准变更。

### 6.2 生成变更建议

此脚本**不会修改集群或创建 PR**。它读取 `kubectl` JSON 快照，按名称匹配 Deployment/StatefulSet 容器，并建议将 request 至少降低 20%。它需要 `kubernetes==36.0.3`，示例中使用的 quantity parser 已经过测试。

请检查建议是否覆盖了充足的流量、峰值和恢复场景，以及 CPU requests 变更是否会影响 HPA utilization 计算。Init containers 和 Pod 级资源仍需单独审查。脚本不会猜测重复的 VPA、未知容器或缺失的 requests。

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

![只读变更建议，之后由负责人准备 manifests、PR 并进行验证](../.gitbook/assets/en-ops-13-finops-cost-platform-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-13-finops-cost-platform-2.html)

`estimatedBillingSavings` 为 `null`：减少 requests 并不保证节点数量或承诺成本会降低。负责人应修改实际 Git manifests、运行性能测试、审查 PR，并在 rollout 后观察 SLO。要实现自动化，还需要将代码映射到仓库文件、配置身份验证、处理重复 PR、设置 CI 和审批规则。

## 7. 闲置资源候选项与治理

### 7.1 审查列表，而非直接删除

此单集群查询会查找当前没有 Pod volume 引用的 Bound PVC。它会将 gauge 与 1 比较，并同时匹配命名空间和 claim 名称。

```promql
(kube_persistentvolumeclaim_status_phase{phase="Bound"} == 1)
unless on (namespace, persistentvolumeclaim)
kube_pod_spec_volumes_persistentvolumeclaims_info
```

其中可能包含已缩容至零副本的 StatefulSet、恢复卷或暂停作业的数据。删除前，请检查所有权、恢复要求、最近使用时间、快照和保留策略。Deployment 创建于七天前，并不能证明它已连续七天保持零副本。请验证历史数据是否连续、覆盖是否完整以及是否存在缺口。

低 CPU 或内存用量可能是突发型或备用工作负载的合理情况。将 Pod 聚合到 Deployment 时，需要 owner 关系（ReplicaSet → Deployment）、命名空间和集群标识符。仅凭网络接收量无法判断业务流量，也无法判断资源是否仍有用途。

### 7.2 定期审查

| 频率 | 审查内容 |
| --- | --- |
| 每日 | 数据收集缺口、导入器数据新鲜度、异常、预算估算 |
| 每周 | 闲置候选项的所有权、VPA 建议、SLO 影响 |
| 每月 | 账单对账、折扣、抵扣额、未归属成本、共享规则、单位经济效益 |

记录周期、币种、模型或账单数据源、刷新时间、成本分摊策略、未归属金额和审批人。不要假设标签完整就代表准确无误，也不要认为减少 requests 就等同于节省成本，或认为 dashboard 筛选器能够强制执行团队访问控制。

## 8. 参考资料

- [FinOps Foundation 定义](https://www.finops.org/introduction/what-is-finops/)
- [OpenCost 1.121.3 发布版本](https://github.com/opencost/opencost/releases/tag/v1.121.3)
- [OpenCost Helm chart](https://github.com/opencost/opencost-helm-chart)
- [OpenCost API](https://opencost.io/docs/integrations/api/)
- [OpenCost AWS authorizer 源码](https://github.com/opencost/opencost/blob/v1.121.3/pkg/cloud/aws/authorizer.go)
- [Kubecost chart 和迁移](https://github.com/kubecost/cost-analyzer-helm-chart)
- [AWS Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-data-exports.html)
- [Data Exports 加密](https://docs.aws.amazon.com/cur/latest/userguide/data-protection.html)
- [Data Exports 存储桶策略](https://docs.aws.amazon.com/cur/latest/userguide/dataexports-s3-bucket.html)
- [成本分摊标签回填](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html)
- [Cost anomaly SNS 权限](https://docs.aws.amazon.com/cost-management/latest/userguide/ad-SNS.html)
- [Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)
- [Kyverno ValidatingPolicy](https://kyverno.io/docs/policy-types/validating-policy/)
- [Goldilocks](https://goldilocks.docs.fairwinds.com/)


- [可观测性堆栈](./09-observability-stack.md)
- [资源优化](./10-resource-optimization.md)
- [活动容量规划](./12-event-capacity-planning.md)
