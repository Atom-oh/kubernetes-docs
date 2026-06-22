# FinOps Cost Visibility Platform

> **Supported Versions**: Kubernetes 1.28+, Kubecost 2.x, OpenCost 1.x
> **Last Updated**: April 25, 2026

< [Previous: Event Capacity Planning](./12-event-capacity-planning.md) | [Table of Contents](./README.md) | [Next: None] >

---

## Overview

Running Kubernetes at scale introduces a unique cost management challenge: workloads are ephemeral, resources are shared, and traditional per-server cost attribution no longer applies. Without deliberate cost visibility, organizations often discover that their cloud bill has grown 2-5x beyond expectations, with no clear understanding of which teams, services, or environments are driving the spend.

**FinOps** (Financial Operations) is the practice of bringing financial accountability to the variable spend model of cloud computing. It bridges the gap between engineering teams who consume resources and finance teams who manage budgets. The FinOps lifecycle follows three iterative phases:

- **Inform**: Provide visibility into where money is being spent and by whom
- **Optimize**: Identify and act on opportunities to reduce waste and improve efficiency
- **Operate**: Establish governance, automation, and cultural practices that sustain cost efficiency

This guide builds a complete FinOps cost visibility platform on Kubernetes using OpenCost, Kubecost, Prometheus, and Grafana. It covers everything from foundational cost allocation through anomaly detection to automated rightsizing, giving platform teams the tools to make Kubernetes cost management a self-service capability for every engineering team.

### Learning Objectives

- Understand the FinOps operating model and how it applies to Kubernetes environments
- Deploy and configure OpenCost and Kubecost for accurate cost allocation
- Implement showback and chargeback systems using labels, namespaces, and cost APIs
- Build cost anomaly detection with alerting pipelines to Slack and PagerDuty
- Enable team self-service cost dashboards and automated weekly cost reports
- Establish resource rightsizing workflows using VPA recommendations and Goldilocks
- Define cost governance policies with Kyverno and regular review processes

---

## 1. FinOps Operating Model

The FinOps Foundation defines a maturity model that organizations progress through as they build cost management capabilities. Understanding this model is essential before deploying any tooling, because the tools you choose and how you configure them depend on your current maturity level.

### 1.1 Inform, Optimize, Operate Cycle

The FinOps lifecycle is not a one-time project but a continuous loop. Each iteration deepens your understanding and tightens your cost controls.

```mermaid
graph LR
    A[Inform] -->|Visibility & Allocation| B[Optimize]
    B -->|Rightsizing & Savings| C[Operate]
    C -->|Governance & Automation| A

    subgraph Inform
        A1[Cost Allocation]
        A2[Showback Dashboards]
        A3[Tagging & Labels]
    end

    subgraph Optimize
        B1[Rightsizing]
        B2[Spot / Savings Plans]
        B3[Idle Resource Cleanup]
    end

    subgraph Operate
        C1[Budget Alerts]
        C2[Policy Enforcement]
        C3[Regular Reviews]
    end

    A --- A1
    A --- A2
    A --- A3
    B --- B1
    B --- B2
    B --- B3
    C --- C1
    C --- C2
    C --- C3
```

**Inform Phase**: Establish visibility into Kubernetes costs by deploying cost monitoring tools, implementing a label strategy, and building showback dashboards. This is the foundation that all optimization efforts build on. Without accurate cost data, optimization is guesswork.

**Optimize Phase**: Use the visibility data to identify waste and act on it. This includes rightsizing workloads based on actual usage, leveraging Spot instances and Savings Plans, and cleaning up idle resources. The goal is to reduce spend without affecting performance.

**Operate Phase**: Institutionalize cost efficiency through budget alerts, policy enforcement (e.g., requiring resource limits on all deployments), and regular cost review meetings. Automation replaces manual effort, and cost awareness becomes part of the engineering culture.

### 1.2 Organizational Roles

Effective FinOps requires collaboration across multiple organizational functions. Each role has distinct responsibilities and uses different aspects of the cost platform.

| Role | Responsibilities | Primary Tools | Cadence |
|------|-----------------|---------------|---------|
| **FinOps Team** | Define cost allocation models, maintain dashboards, drive optimization initiatives, report to leadership | Kubecost, Grafana, AWS Cost Explorer | Daily monitoring, weekly reports |
| **Engineering Teams** | Set resource requests/limits, apply cost labels, review team cost dashboards, act on rightsizing recommendations | Team dashboards, VPA, Goldilocks | Sprint-level reviews |
| **Finance** | Budget planning, forecast validation, chargeback reconciliation, ROI analysis | Monthly cost reports, showback data | Monthly reconciliation |
| **Leadership** | Approve budgets, set cost targets, review unit economics, make strategic decisions | Executive dashboards, trend reports | Monthly/quarterly reviews |
| **Platform Engineering** | Deploy and maintain cost tools, build self-service dashboards, implement policies | Kubecost, OpenCost, Kyverno, Prometheus | Continuous |

### 1.3 Maturity Levels

Organizations typically progress through three maturity levels. Trying to jump to "Run" without establishing "Crawl" fundamentals leads to fragile, inaccurate cost systems.

| Level | Description | Cost Allocation | Optimization | Governance | Typical Timeline |
|-------|-------------|----------------|--------------|------------|-----------------|
| **Crawl** | Basic visibility established. Teams can see their costs but allocation may be approximate. | Namespace-level allocation, basic labels | Manual rightsizing, ad-hoc cleanup | No formal policies, reactive budget alerts | 1-3 months |
| **Walk** | Accurate allocation with showback. Teams receive regular cost reports and have self-service dashboards. | Label-based allocation with shared cost splitting, showback dashboards | VPA recommendations, scheduled reviews, Spot adoption | Label enforcement policies, monthly reviews | 3-6 months |
| **Run** | Full chargeback with automated optimization. Cost is a first-class engineering metric. | Real-time chargeback integrated with finance systems, CUR reconciliation | Automated rightsizing pipelines, continuous Spot optimization | Automated policy enforcement, weekly reviews, cost gates in CI/CD | 6-12 months |

---

## 2. OpenCost/Kubecost Deep Configuration

Both OpenCost (open-source CNCF project) and Kubecost (commercial product built on OpenCost) provide Kubernetes cost monitoring. OpenCost is suitable for single-cluster deployments with basic needs, while Kubecost adds multi-cluster federation, long-term storage, and enterprise features.

### 2.1 OpenCost Installation (Open Source)

OpenCost requires a Prometheus instance to function. It reads Prometheus metrics to calculate costs and exposes its own cost allocation API.

```yaml
# opencost-values.yaml
# Helm chart: https://github.com/opencost/opencost-helm-chart
# helm repo add opencost https://opencost.github.io/opencost-helm-chart
# helm install opencost opencost/opencost -n opencost --create-namespace -f opencost-values.yaml

opencost:
  exporter:
    defaultClusterId: "production-eks-us-east-1"
    image:
      registry: ghcr.io
      repository: opencost/opencost
      tag: "1.112.0"

    # AWS integration for accurate pricing
    aws:
      service_key_name: ""
      service_key_secret: ""
      spot_data_region: "us-east-1"
      spot_data_prefix: "spot-data-feed"
      spot_data_bucket: "my-company-spot-data-feed"

    # Prometheus connection settings
    prometheus:
      internal:
        enabled: true
        serviceName: prometheus-server
        namespaceName: monitoring
        port: 80
      external:
        enabled: false

    # Resource configuration
    resources:
      requests:
        cpu: "100m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"

    # Persistent storage for cost data
    persistence:
      enabled: true
      storageClass: "gp3"
      size: "32Gi"

    # Custom pricing configuration
    cloudCost:
      enabled: true
      monthToDateInterval: 6
      refreshRateHours: 6
      queryWindowDays: 14

  # OpenCost UI
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
        alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
        alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:us-east-1:123456789012:certificate/abc-123"
      hosts:
        - host: "opencost.internal.mycompany.com"
          paths:
            - path: /
              pathType: Prefix

  metrics:
    serviceMonitor:
      enabled: true
      namespace: monitoring
      additionalLabels:
        release: prometheus

# Network policies
networkPolicies:
  enabled: true

# Service account with IRSA for AWS pricing API access
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/opencost-role"
```

### 2.2 Kubecost Enterprise

Kubecost Enterprise extends OpenCost with multi-cluster federation, long-term ETL storage in S3, SAML/OIDC authentication, and advanced allocation features. The following configuration is production-ready for a multi-cluster EKS deployment.

```yaml
# kubecost-values.yaml
# helm repo add kubecost https://kubecost.github.io/cost-analyzer-helm-chart
# helm install kubecost kubecost/cost-analyzer -n kubecost --create-namespace -f kubecost-values.yaml

global:
  # Enterprise license
  prometheus:
    enabled: false  # Use existing Prometheus
    fqdn: "http://prometheus-server.monitoring.svc:80"

  grafana:
    enabled: false  # Use existing Grafana
    domainName: "grafana.monitoring.svc"

  # Multi-cluster configuration
  thanos:
    enabled: false  # Use Kubecost federation instead

# Kubecost primary configuration
kubecostProductConfigs:
  clusterName: "production-eks-us-east-1"
  clusterProfile: "production"
  currencyCode: "USD"
  defaultModelPricing:
    enabled: false  # Use actual AWS pricing
  productKey:
    enabled: true
    key: "KUBECOST-ENTERPRISE-LICENSE-KEY"
    secretName: "kubecost-product-key"

  # Shared namespaces for cost splitting
  sharedNamespaces: "kube-system,kubecost,monitoring,cert-manager,ingress-nginx"

  # Allocation settings
  shareTenancyCosts: true
  shareNamespaces: "kube-system,kubecost,monitoring"
  shareLabels: ""
  shareCost: ""
  shareSplit: "weighted"

# ETL storage in S3 for long-term data retention
kubecostModel:
  image: "gcr.io/kubecost1/cost-model:prod-2.3.0"
  resources:
    requests:
      cpu: "200m"
      memory: "512Mi"
    limits:
      cpu: "1000m"
      memory: "2Gi"

  etl: true
  etlFileStoreEnabled: false
  etlBucketConfig:
    enabled: true

  # Multi-cluster federation
  federatedETL:
    enabled: true
    primaryCluster: true
    federatedCluster: false
    readOnly: false

  # Allocation configuration
  maxQueryConcurrency: 5
  etlResolution: "1h"

# S3 backend for ETL data
kubecostS3Config:
  enabled: true
  bucketName: "mycompany-kubecost-etl"
  region: "us-east-1"
  # Uses IRSA for authentication

# Federated ETL object store
federatedETL:
  federatedStore:
    enabled: true
    bucket: "mycompany-kubecost-federation"
    region: "us-east-1"

# Aggregator for multi-cluster views
kubecostAggregator:
  enabled: true
  replicas: 1
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "4Gi"

# Frontend configuration
kubecostFrontend:
  image: "gcr.io/kubecost1/frontend:prod-2.3.0"
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "500m"
      memory: "256Mi"

# Networking and ingress
ingress:
  enabled: true
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: "internal"
    alb.ingress.kubernetes.io/target-type: "ip"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:us-east-1:123456789012:certificate/abc-123"
    alb.ingress.kubernetes.io/group.name: "internal"
  hosts:
    - host: "kubecost.internal.mycompany.com"
      paths:
        - path: /
          pathType: Prefix

# Service account with IRSA
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::123456789012:role/kubecost-role"

# Network policy
networkPolicy:
  enabled: true
  denyAll: false

# Pod disruption budget
podDisruptionBudget:
  enabled: true
  minAvailable: 1

# Priority class
priorityClassName: "system-cluster-critical"

# Tolerations for dedicated node
tolerations:
  - key: "monitoring"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"

nodeSelector:
  monitoring: "true"
```

### 2.3 AWS Cost and Usage Report (CUR) Integration

The AWS Cost and Usage Report provides the most accurate source of AWS billing data. Integrating CUR with Kubecost allows reconciliation of in-cluster cost estimates with actual AWS charges, including data transfer, EBS volumes, and other infrastructure costs that Kubernetes-level monitoring cannot see.

#### Terraform Configuration for CUR

```hcl
# cur-infrastructure.tf
# Provisions S3 bucket, CUR report definition, and IAM role for Kubecost access

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 bucket for CUR data
resource "aws_s3_bucket" "cur_bucket" {
  bucket = "mycompany-cur-reports"

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
    Purpose     = "cost-and-usage-reports"
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
    id     = "transition-to-ia"
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
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "cur_bucket_public_access" {
  bucket = aws_s3_bucket.cur_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy to allow CUR delivery
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

data "aws_caller_identity" "current" {}

# CUR report definition (must be created in us-east-1)
resource "aws_cur_report_definition" "daily_cur" {
  report_name                = "mycompany-daily-cur"
  time_unit                  = "DAILY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket                  = aws_s3_bucket.cur_bucket.id
  s3_region                  = "us-east-1"
  s3_prefix                  = "cur-reports"
  report_versioning          = "OVERWRITE_REPORT"
  refresh_closed_reports     = true

  additional_artifacts = ["ATHENA"]
}

# IAM role for Kubecost to read CUR data
resource "aws_iam_role" "kubecost_cur_role" {
  name = "kubecost-cur-reader"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.oidc_provider}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${var.oidc_provider}:sub" = "system:serviceaccount:kubecost:kubecost-cost-analyzer"
            "${var.oidc_provider}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "kubecost_cur_policy" {
  name = "kubecost-cur-read-policy"
  role = aws_iam_role.kubecost_cur_role.id

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
          "arn:aws:s3:::mycompany-kubecost-etl",
          "arn:aws:s3:::mycompany-kubecost-etl/*"
        ]
      },
      {
        Sid    = "AthenaQueryAccess"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = "arn:aws:athena:us-east-1:${data.aws_caller_identity.current.account_id}:workgroup/primary"
      },
      {
        Sid    = "GlueTableAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions"
        ]
        Resource = [
          "arn:aws:glue:us-east-1:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:aws:glue:us-east-1:${data.aws_caller_identity.current.account_id}:database/athenacurcfn_mycompany_daily_cur",
          "arn:aws:glue:us-east-1:${data.aws_caller_identity.current.account_id}:table/athenacurcfn_mycompany_daily_cur/*"
        ]
      },
      {
        Sid    = "PricingAPIAccess"
        Effect = "Allow"
        Action = [
          "pricing:GetProducts",
          "pricing:DescribeServices"
        ]
        Resource = "*"
      },
      {
        Sid    = "EC2DescribeForPricing"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeReservedInstances",
          "ec2:DescribeSpotPriceHistory",
          "ec2:DescribeSavingsPlans"
        ]
        Resource = "*"
      }
    ]
  })
}

variable "oidc_provider" {
  description = "OIDC provider URL for EKS cluster (without https:// prefix)"
  type        = string
}

output "kubecost_role_arn" {
  value       = aws_iam_role.kubecost_cur_role.arn
  description = "ARN of the IAM role for Kubecost CUR access"
}

output "cur_bucket_name" {
  value       = aws_s3_bucket.cur_bucket.id
  description = "Name of the S3 bucket containing CUR data"
}
```

#### Kubecost Cloud Integration Configuration

Add the following to your Kubecost Helm values to enable CUR reconciliation:

```yaml
# kubecost-cloud-integration-values.yaml (merge with main values)
kubecostProductConfigs:
  cloudIntegrationJSON: |
    {
      "aws": [
        {
          "athenaBucketName": "mycompany-cur-reports",
          "athenaRegion": "us-east-1",
          "athenaDatabase": "athenacurcfn_mycompany_daily_cur",
          "athenaTable": "mycompany_daily_cur",
          "athenaWorkgroup": "primary",
          "projectID": "123456789012",
          "serviceKeyName": "",
          "serviceKeySecret": ""
        }
      ]
    }

  # Reconciliation settings
  cloudIntegrationSecret: ""
  athenaProjectID: "123456789012"
  athenaBucketName: "s3://mycompany-cur-reports/cur-reports"
  athenaRegion: "us-east-1"
  athenaDatabase: "athenacurcfn_mycompany_daily_cur"
  athenaTable: "mycompany_daily_cur"
  athenaWorkgroup: "primary"
```

### 2.4 Cost Accuracy Tuning

Default pricing in Kubecost uses on-demand list prices, which can be significantly different from your actual costs if you use Reserved Instances, Savings Plans, or negotiated rates. The following configurations improve cost accuracy.

#### Custom Pricing Configuration

```yaml
# custom-pricing-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pricing-configs
  namespace: kubecost
data:
  # Override default pricing with negotiated rates
  default-pricing.json: |
    {
      "provider": "aws",
      "description": "Custom pricing for negotiated EDP rates",
      "CPU": "0.02835",
      "RAM": "0.00356",
      "GPU": "0.85",
      "storage": "0.000054795",
      "zoneNetworkEgress": "0.00",
      "regionNetworkEgress": "0.01",
      "internetNetworkEgress": "0.05",
      "spotCPU": "0.0085",
      "spotRAM": "0.00107",
      "spotLabel": "karpenter.sh/capacity-type",
      "spotLabelValue": "spot"
    }
```

#### Shared Cost Allocation Rules

```yaml
# shared-cost-allocation-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: allocation-configs
  namespace: kubecost
data:
  # Define how shared infrastructure costs are distributed
  shared-costs.json: |
    {
      "sharedCosts": [
        {
          "name": "Control Plane",
          "type": "weighted",
          "filter": {
            "namespace": "kube-system"
          },
          "weight": "cpuCost"
        },
        {
          "name": "Monitoring Stack",
          "type": "weighted",
          "filter": {
            "namespace": "monitoring"
          },
          "weight": "totalCost"
        },
        {
          "name": "Ingress Controllers",
          "type": "even",
          "filter": {
            "namespace": "ingress-nginx"
          }
        },
        {
          "name": "Service Mesh",
          "type": "weighted",
          "filter": {
            "namespace": "istio-system"
          },
          "weight": "networkCost"
        },
        {
          "name": "Cert Manager",
          "type": "even",
          "filter": {
            "namespace": "cert-manager"
          }
        },
        {
          "name": "Platform Tools",
          "type": "even",
          "filter": {
            "namespace": "kubecost,argocd,kyverno"
          }
        }
      ],
      "sharedOverhead": 0.0,
      "idleCostDistribution": "weighted"
    }
```

#### Negotiated Rate Override

When your organization has an Enterprise Discount Program (EDP) or negotiated pricing, use the cost model ConfigMap to reflect actual rates:

```yaml
# negotiated-rates-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kubecost-negotiated-rates
  namespace: kubecost
  labels:
    app: kubecost
data:
  # Node-type-specific cost overrides
  node-pricing.json: |
    {
      "nodeClassCost": [
        {
          "nodeClassFilter": {
            "instanceType": "m6i.xlarge"
          },
          "cpuCostPerHour": "0.0240",
          "ramCostPerGBHour": "0.0032",
          "gpuCostPerHour": "0.0"
        },
        {
          "nodeClassFilter": {
            "instanceType": "m6i.2xlarge"
          },
          "cpuCostPerHour": "0.0230",
          "ramCostPerGBHour": "0.0031",
          "gpuCostPerHour": "0.0"
        },
        {
          "nodeClassFilter": {
            "instanceType": "c6i.2xlarge"
          },
          "cpuCostPerHour": "0.0200",
          "ramCostPerGBHour": "0.0027",
          "gpuCostPerHour": "0.0"
        },
        {
          "nodeClassFilter": {
            "instanceType": "r6i.2xlarge"
          },
          "cpuCostPerHour": "0.0280",
          "ramCostPerGBHour": "0.0025",
          "gpuCostPerHour": "0.0"
        },
        {
          "nodeClassFilter": {
            "instanceType": "g5.xlarge"
          },
          "cpuCostPerHour": "0.0500",
          "ramCostPerGBHour": "0.0040",
          "gpuCostPerHour": "0.7500"
        }
      ]
    }
```

---

## 3. Showback/Chargeback Implementation

Showback reports costs to teams for awareness without direct billing. Chargeback actually bills teams or cost centers. Both require the same foundation: accurate cost allocation tied to organizational units.

### 3.1 Label Strategy

Labels are the primary mechanism for attributing Kubernetes costs to teams, services, and environments. A consistent, enforced label strategy is the single most important factor in cost allocation accuracy.

#### Required Labels

| Label | Purpose | Example Values | Applied To |
|-------|---------|---------------|------------|
| `team` | Cost attribution to engineering team | `platform`, `checkout`, `payments`, `search` | All workloads |
| `service` | Service-level cost tracking | `api-gateway`, `order-service`, `user-service` | All workloads |
| `environment` | Environment-level segregation | `production`, `staging`, `development` | All workloads |
| `cost-center` | Finance department mapping | `CC-1001`, `CC-2005`, `CC-3010` | All workloads |
| `product` | Product or business unit | `marketplace`, `payments-platform`, `analytics` | Optional |
| `managed-by` | Tool or team that manages the resource | `argocd`, `helm`, `terraform` | Optional |

#### Kyverno Label Enforcement Policy

This policy ensures that all Deployments, StatefulSets, and DaemonSets have the required cost labels. Workloads in system namespaces are excluded.

```yaml
# kyverno-cost-labels-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-cost-labels
  annotations:
    policies.kyverno.io/title: Require Cost Attribution Labels
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: high
    policies.kyverno.io/subject: Deployment, StatefulSet, DaemonSet
    policies.kyverno.io/description: >-
      All workloads must include cost attribution labels (team, service,
      environment, cost-center) to enable accurate cost allocation and
      showback reporting. Workloads without these labels will be rejected.
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-cost-labels-on-resource
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
                - DaemonSet
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - kube-node-lease
                - kubecost
                - monitoring
                - ingress-nginx
                - cert-manager
                - argocd
                - kyverno
      validate:
        message: >-
          Resource {{request.object.kind}}/{{request.object.metadata.name}}
          in namespace {{request.namespace}} is missing required cost labels.
          All workloads must have labels: team, service, environment, and cost-center.
          Current labels: {{request.object.metadata.labels}}
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
                - StatefulSet
                - DaemonSet
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - kube-node-lease
                - kubecost
                - monitoring
                - ingress-nginx
                - cert-manager
                - argocd
                - kyverno
      validate:
        message: >-
          Pod template in {{request.object.kind}}/{{request.object.metadata.name}}
          must also carry cost labels for accurate pod-level cost attribution.
        pattern:
          spec:
            template:
              metadata:
                labels:
                  team: "?*"
                  service: "?*"
                  environment: "?*"
                  cost-center: "?*"

    - name: validate-environment-values
      match:
        any:
          - resources:
              kinds:
                - Deployment
                - StatefulSet
                - DaemonSet
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - kube-node-lease
                - kubecost
                - monitoring
                - ingress-nginx
                - cert-manager
                - argocd
                - kyverno
      validate:
        message: >-
          Label 'environment' must be one of: production, staging, development, sandbox.
          Got: {{request.object.metadata.labels.environment}}
        pattern:
          metadata:
            labels:
              environment: "production | staging | development | sandbox"
```

### 3.2 Namespace-Based Cost Allocation

Namespaces provide the coarsest level of cost isolation. Each team or service boundary should map to a namespace, with ResourceQuotas preventing any single team from consuming disproportionate resources.

#### Kubecost Allocation API Examples

Query the Kubecost Allocation API to retrieve cost breakdowns programmatically:

```bash
# Get cost allocation by namespace for the last 7 days
curl -s "http://kubecost.internal.mycompany.com/model/allocation?window=7d&aggregate=namespace&accumulate=true" \
  | jq '.data[0] | to_entries[] | {namespace: .key, totalCost: .value.totalCost, cpuCost: .value.cpuCost, ramCost: .value.ramCost, pvCost: .value.pvCost, networkCost: .value.networkCost}'

# Get cost allocation by team label for the current month
curl -s "http://kubecost.internal.mycompany.com/model/allocation?window=thismonth&aggregate=label:team&accumulate=true&shareIdle=weighted&shareSplit=weighted&shareNamespaces=kube-system,monitoring,kubecost" \
  | jq '.data[0] | to_entries | sort_by(-.value.totalCost) | .[] | {team: .key, totalCost: (.value.totalCost | round), cpuEfficiency: (.value.cpuEfficiency * 100 | round), ramEfficiency: (.value.ramEfficiency * 100 | round)}'

# Get daily cost trend for a specific team over the last 30 days
curl -s "http://kubecost.internal.mycompany.com/model/allocation?window=30d&aggregate=label:team&step=1d&filterLabels=team:checkout" \
  | jq '[.data[] | to_entries[] | {date: .key, cost: .value.totalCost}]'
```

#### ResourceQuota Per Team Namespace

```yaml
# team-namespace-quota.yaml
# Apply per-team to enforce cost boundaries at the namespace level
apiVersion: v1
kind: Namespace
metadata:
  name: team-checkout
  labels:
    team: checkout
    cost-center: "CC-2005"
    environment: production
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-checkout-quota
  namespace: team-checkout
spec:
  hard:
    requests.cpu: "40"
    requests.memory: "80Gi"
    limits.cpu: "80"
    limits.memory: "160Gi"
    persistentvolumeclaims: "20"
    requests.storage: "500Gi"
    services.loadbalancers: "2"
    pods: "200"
    count/deployments.apps: "50"
    count/statefulsets.apps: "10"
    count/jobs.batch: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: team-checkout-limits
  namespace: team-checkout
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "8"
        memory: "16Gi"
      min:
        cpu: "10m"
        memory: "16Mi"
    - type: Pod
      max:
        cpu: "16"
        memory: "32Gi"
    - type: PersistentVolumeClaim
      max:
        storage: "100Gi"
      min:
        storage: "1Gi"
```

### 3.3 Shared Cost Distribution

Shared infrastructure costs (control plane, monitoring, ingress, service mesh) must be fairly distributed across teams. There are several strategies, each with trade-offs.

```mermaid
graph TD
    A[Total Cluster Cost] --> B[Direct Costs]
    A --> C[Shared Costs]
    A --> D[Idle Costs]

    B --> B1[Team A Workloads]
    B --> B2[Team B Workloads]
    B --> B3[Team C Workloads]

    C --> C1[kube-system]
    C --> C2[monitoring]
    C --> C3[ingress-nginx]
    C --> C4[istio-system]

    D --> D1[Unallocated CPU]
    D --> D2[Unallocated Memory]

    C1 -->|Weighted by CPU| E[Distributed to Teams]
    C2 -->|Weighted by Total Cost| E
    C3 -->|Even Split| E
    C4 -->|Weighted by Network Cost| E

    D1 -->|Weighted Distribution| E
    D2 -->|Weighted Distribution| E
```

| Distribution Method | When to Use | Pros | Cons |
|-------------------|-------------|------|------|
| **Weighted by CPU** | Control plane costs | Proportional to actual usage | Penalizes CPU-heavy workloads |
| **Weighted by Total Cost** | General shared services | Fair overall distribution | Requires accurate base allocation first |
| **Even Split** | Small shared services | Simple and transparent | Unfair if teams are different sizes |
| **Weighted by Network** | Ingress, service mesh | Accurate for network-heavy shared costs | Network costs can be volatile |
| **Proportional by Pods** | Platform tooling | Scales with workload count | Does not account for pod sizes |

The shared cost configuration was already provided in Section 2.4 (shared-cost-allocation-configmap.yaml). To verify your shared cost setup is working correctly:

```bash
# Verify shared cost distribution
curl -s "http://kubecost.internal.mycompany.com/model/allocation?window=7d&aggregate=label:team&accumulate=true&shareIdle=weighted&shareSplit=weighted&shareNamespaces=kube-system,monitoring,ingress-nginx,istio-system,cert-manager,kubecost,argocd,kyverno" \
  | jq '.data[0] | to_entries[] | {team: .key, directCost: .value.totalCost, sharedCost: .value.sharedCost, totalWithShared: (.value.totalCost + .value.sharedCost)}'
```

### 3.4 Grafana Showback Dashboards

The following Grafana dashboard provides a comprehensive cost overview, showing cost-per-team and cost-per-service panels using Prometheus metrics exposed by Kubecost.

```json
{
  "annotations": {
    "list": []
  },
  "description": "FinOps Showback Dashboard - Cost allocation by team and service",
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
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
            "axisBorderShow": false,
            "axisLabel": "Daily Cost (USD)",
            "drawStyle": "bars",
            "fillOpacity": 80,
            "stacking": {
              "mode": "normal"
            }
          },
          "unit": "currencyUSD"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 10,
        "w": 24,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": ["sum", "mean"],
          "displayMode": "table",
          "placement": "right"
        },
        "tooltip": {
          "mode": "multi"
        }
      },
      "title": "Daily Cost by Team",
      "type": "timeseries",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (\n  (\n    sum by (namespace, label_team) (kubecost_container_cpu_allocation_cost{} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})\n    +\n    sum by (namespace, label_team) (kubecost_container_memory_allocation_cost{} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})\n  )\n)",
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
          "unit": "currencyUSD",
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": null },
              { "color": "yellow", "value": 500 },
              { "color": "red", "value": 1000 }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 10,
        "w": 12,
        "x": 0,
        "y": 10
      },
      "id": 2,
      "options": {
        "displayMode": "gradient",
        "orientation": "horizontal",
        "showUnfilled": true,
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        }
      },
      "title": "Current Monthly Cost by Service",
      "type": "bargauge",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_service) (\n  (\n    kubecost_container_cpu_allocation_cost{}\n    + kubecost_container_memory_allocation_cost{}\n  ) * on(pod) group_left(label_service) kube_pod_labels{label_service!=\"\"}\n) * 730",
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
            "mode": "continuous-GrYlRd"
          },
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": null },
              { "color": "yellow", "value": 0.4 },
              { "color": "green", "value": 0.65 }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 10,
        "w": 12,
        "x": 12,
        "y": 10
      },
      "id": 3,
      "options": {
        "displayMode": "gradient",
        "orientation": "horizontal",
        "showUnfilled": true,
        "reduceOptions": {
          "calcs": ["lastNotNull"],
          "fields": "",
          "values": false
        }
      },
      "title": "Resource Efficiency by Team",
      "type": "bargauge",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (rate(container_cpu_usage_seconds_total{namespace!~\"kube-system|monitoring|kubecost\"}[1h]) * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})\n/\nsum by (label_team) (kube_pod_container_resource_requests{resource=\"cpu\", namespace!~\"kube-system|monitoring|kubecost\"} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})",
          "legendFormat": "{{label_team}} CPU Efficiency",
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
          "custom": {
            "align": "auto",
            "cellOptions": {
              "type": "auto"
            }
          },
          "unit": "currencyUSD"
        },
        "overrides": [
          {
            "matcher": { "id": "byName", "options": "CPU Efficiency" },
            "properties": [{ "id": "unit", "value": "percentunit" }]
          },
          {
            "matcher": { "id": "byName", "options": "Memory Efficiency" },
            "properties": [{ "id": "unit", "value": "percentunit" }]
          }
        ]
      },
      "gridPos": {
        "h": 10,
        "w": 24,
        "x": 0,
        "y": 20
      },
      "id": 4,
      "options": {
        "showHeader": true,
        "sortBy": [
          {
            "desc": true,
            "displayName": "Total Cost"
          }
        ]
      },
      "title": "Team Cost Summary Table",
      "type": "table",
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (\n  kubecost_container_cpu_allocation_cost{}\n  + kubecost_container_memory_allocation_cost{}\n  + kubecost_container_gpu_allocation_cost{}\n) * 730",
          "format": "table",
          "instant": true,
          "legendFormat": "Total Cost",
          "refId": "A"
        },
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (rate(container_cpu_usage_seconds_total{namespace!~\"kube-system|monitoring\"}[1h]) * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})\n/\nsum by (label_team) (kube_pod_container_resource_requests{resource=\"cpu\", namespace!~\"kube-system|monitoring\"} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})",
          "format": "table",
          "instant": true,
          "legendFormat": "CPU Efficiency",
          "refId": "B"
        },
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "sum by (label_team) (container_memory_working_set_bytes{namespace!~\"kube-system|monitoring\"} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})\n/\nsum by (label_team) (kube_pod_container_resource_requests{resource=\"memory\", namespace!~\"kube-system|monitoring\"} * on(namespace) group_left(label_team) kube_namespace_labels{label_team!=\"\"})",
          "format": "table",
          "instant": true,
          "legendFormat": "Memory Efficiency",
          "refId": "C"
        }
      ],
      "transformations": [
        {
          "id": "merge",
          "options": {}
        },
        {
          "id": "organize",
          "options": {
            "excludeByName": { "Time": true },
            "renameByName": {
              "label_team": "Team",
              "Value #A": "Total Cost",
              "Value #B": "CPU Efficiency",
              "Value #C": "Memory Efficiency"
            }
          }
        }
      ]
    }
  ],
  "refresh": "5m",
  "schemaVersion": 39,
  "tags": ["finops", "cost", "showback"],
  "templating": {
    "list": [
      {
        "current": {},
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "definition": "label_values(kube_namespace_labels{label_team!=\"\"}, label_team)",
        "hide": 0,
        "includeAll": true,
        "multi": true,
        "name": "team",
        "query": "label_values(kube_namespace_labels{label_team!=\"\"}, label_team)",
        "refresh": 2,
        "regex": "",
        "sort": 1,
        "type": "query"
      },
      {
        "current": {},
        "datasource": {
          "type": "prometheus",
          "uid": "prometheus"
        },
        "definition": "label_values(kube_namespace_labels{label_environment!=\"\"}, label_environment)",
        "hide": 0,
        "includeAll": true,
        "multi": true,
        "name": "environment",
        "query": "label_values(kube_namespace_labels{label_environment!=\"\"}, label_environment)",
        "refresh": 2,
        "regex": "",
        "sort": 1,
        "type": "query"
      }
    ]
  },
  "time": {
    "from": "now-30d",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "browser",
  "title": "FinOps Showback Dashboard",
  "uid": "finops-showback-v1",
  "version": 1
}
```

---

## 4. Cost Anomaly Detection

Cost anomalies indicate unexpected changes in spending patterns. These can result from misconfigurations (e.g., missing resource limits causing runaway pods), traffic spikes, or infrastructure changes. Detecting anomalies early prevents bill shock and allows teams to investigate before costs accumulate.

### 4.1 Kubecost Alert Configuration

Kubecost provides a built-in alerting system that can trigger on budget thresholds, efficiency drops, and recurring cost changes.

```yaml
# kubecost-alerts-values.yaml (merge with main Kubecost Helm values)
kubecostProductConfigs:
  # Global alerts configuration
  alertConfigs:
    enabled: true
    frontendUrl: "https://kubecost.internal.mycompany.com"

    # Alert definitions
    alerts:
      # Budget exceeded alert - fires when any namespace exceeds monthly budget
      - type: budget
        threshold: 5000
        window: 30d
        aggregation: namespace
        filter: ""
        ownerContact:
          - "platform-team"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        frequencyMinutes: 1440

      # Budget warning at 80% threshold
      - type: budget
        threshold: 4000
        window: 30d
        aggregation: namespace
        filter: ""
        ownerContact:
          - "platform-team"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        frequencyMinutes: 1440

      # Efficiency drop alert - fires when overall cluster efficiency drops below 40%
      - type: efficiency
        threshold: 0.4
        window: 48h
        aggregation: cluster
        filter: ""
        ownerContact:
          - "platform-team"
          - "finops-team"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        frequencyMinutes: 360

      # Recurring cost increase - fires when any team has a 30% cost increase week over week
      - type: recurringUpdate
        threshold: 0.30
        window: 7d
        aggregation: "label:team"
        filter: ""
        ownerContact:
          - "finops-team"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        frequencyMinutes: 10080

      # Spend spike alert - fires when daily spend exceeds 150% of 7-day average
      - type: spendChange
        threshold: 0.50
        window: 1d
        baselineWindow: 7d
        aggregation: namespace
        filter: ""
        ownerContact:
          - "platform-team"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        frequencyMinutes: 360

      # Team-specific budget alert for checkout team
      - type: budget
        threshold: 8000
        window: 30d
        aggregation: "label:team"
        filter: "team:checkout"
        ownerContact:
          - "checkout-team-lead"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/YYYYYYYYYYYYYYYYYYYYYYYY"
        frequencyMinutes: 1440

      # Team-specific budget alert for payments team
      - type: budget
        threshold: 12000
        window: 30d
        aggregation: "label:team"
        filter: "team:payments"
        ownerContact:
          - "payments-team-lead"
        slackWebhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/ZZZZZZZZZZZZZZZZZZZZZZZZ"
        frequencyMinutes: 1440
```

### 4.2 Prometheus-Based Cost Alerting

For organizations that prefer managing alerts through their existing Prometheus alerting pipeline, the following PrometheusRule resources detect cost anomalies using Kubecost metrics.

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
    - name: cost-anomaly-detection
      interval: 30m
      rules:
        # Alert when daily cluster cost exceeds historical average by 50%
        - alert: ClusterCostSpike
          expr: |
            (
              sum(kubecost_cluster_costs{}) 
              / 
              avg_over_time(sum(kubecost_cluster_costs{})[7d:1h])
            ) > 1.5
          for: 2h
          labels:
            severity: warning
            team: platform
            category: finops
          annotations:
            summary: "Cluster cost spike detected"
            description: |
              Current cluster cost is {{ $value | humanizePercentage }} of the 7-day average.
              This may indicate unexpected workload scaling, misconfigured resources, or a cost anomaly.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/cost-spike"

        # Alert when a specific namespace cost increases more than 100% day-over-day
        - alert: NamespaceCostDoubled
          expr: |
            (
              sum by (namespace) (kubecost_container_cpu_allocation_cost{} + kubecost_container_memory_allocation_cost{})
              /
              sum by (namespace) (kubecost_container_cpu_allocation_cost{} offset 1d + kubecost_container_memory_allocation_cost{} offset 1d)
            ) > 2.0
          for: 1h
          labels:
            severity: warning
            team: platform
            category: finops
          annotations:
            summary: "Namespace {{ $labels.namespace }} cost doubled"
            description: |
              Namespace {{ $labels.namespace }} cost has increased more than 100% compared to yesterday.
              Current ratio: {{ $value | printf "%.2f" }}x of yesterday's cost.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/namespace-cost-spike"

        # Alert when cluster-wide CPU efficiency drops below 30%
        - alert: LowClusterCPUEfficiency
          expr: |
            (
              sum(rate(container_cpu_usage_seconds_total{namespace!~"kube-system|monitoring|kubecost"}[1h]))
              /
              sum(kube_pod_container_resource_requests{resource="cpu", namespace!~"kube-system|monitoring|kubecost"})
            ) < 0.30
          for: 6h
          labels:
            severity: warning
            team: finops
            category: finops
          annotations:
            summary: "Cluster CPU efficiency below 30%"
            description: |
              Cluster-wide CPU efficiency has been below 30% for over 6 hours.
              Current efficiency: {{ $value | humanizePercentage }}.
              This indicates significant over-provisioning. Review VPA recommendations.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/low-efficiency"

        # Alert when cluster-wide memory efficiency drops below 40%
        - alert: LowClusterMemoryEfficiency
          expr: |
            (
              sum(container_memory_working_set_bytes{namespace!~"kube-system|monitoring|kubecost"})
              /
              sum(kube_pod_container_resource_requests{resource="memory", namespace!~"kube-system|monitoring|kubecost"})
            ) < 0.40
          for: 6h
          labels:
            severity: warning
            team: finops
            category: finops
          annotations:
            summary: "Cluster memory efficiency below 40%"
            description: |
              Cluster-wide memory efficiency has been below 40% for over 6 hours.
              Current efficiency: {{ $value | humanizePercentage }}.
              Consider rightsizing workloads using VPA or Goldilocks recommendations.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/low-memory-efficiency"

        # Alert when idle cost exceeds 20% of total cost
        - alert: HighIdleCost
          expr: |
            (
              sum(kubecost_cluster_costs{cost_type="idle"})
              /
              sum(kubecost_cluster_costs{})
            ) > 0.20
          for: 24h
          labels:
            severity: info
            team: finops
            category: finops
          annotations:
            summary: "Idle cost exceeds 20% of total cluster cost"
            description: |
              Idle resources account for {{ $value | humanizePercentage }} of total cluster cost.
              Review node utilization and consider scaling down or using more granular instance types.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/high-idle-cost"

        # Alert when projected monthly cost exceeds budget
        - alert: ProjectedMonthlyBudgetExceeded
          expr: |
            (
              sum(kubecost_cluster_costs{}) * 730
            ) > 50000
          for: 12h
          labels:
            severity: critical
            team: finops
            category: finops
          annotations:
            summary: "Projected monthly cost exceeds $50,000 budget"
            description: |
              Projected monthly cluster cost: ${{ $value | printf "%.0f" }}.
              This exceeds the $50,000 monthly budget. Immediate review required.
            runbook_url: "https://wiki.mycompany.com/runbooks/finops/budget-exceeded"
```

#### Alertmanager Route and Receiver Configuration

```yaml
# alertmanager-config.yaml
apiVersion: monitoring.coreos.com/v1alpha1
kind: AlertmanagerConfig
metadata:
  name: finops-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  route:
    receiver: "finops-slack"
    groupBy:
      - alertname
      - team
      - namespace
    groupWait: 30s
    groupInterval: 5m
    repeatInterval: 4h
    matchers:
      - name: category
        value: finops
        matchType: "="
    routes:
      - receiver: "finops-slack-critical"
        matchers:
          - name: severity
            value: critical
            matchType: "="
        repeatInterval: 1h
      - receiver: "finops-slack-warning"
        matchers:
          - name: severity
            value: warning
            matchType: "="
        repeatInterval: 4h
      - receiver: "finops-slack-info"
        matchers:
          - name: severity
            value: info
            matchType: "="
        repeatInterval: 24h

  receivers:
    - name: "finops-slack"
      slackConfigs:
        - apiURL:
            name: finops-slack-webhook
            key: webhook-url
          channel: "#finops-alerts"
          sendResolved: true
          title: '{{ template "slack.finops.title" . }}'
          text: '{{ template "slack.finops.text" . }}'
          color: '{{ if eq .Status "firing" }}{{ if eq .CommonLabels.severity "critical" }}danger{{ else }}warning{{ end }}{{ else }}good{{ end }}'

    - name: "finops-slack-critical"
      slackConfigs:
        - apiURL:
            name: finops-slack-webhook
            key: webhook-url
          channel: "#finops-critical"
          sendResolved: true
          title: "[CRITICAL] Cost Alert: {{ .CommonLabels.alertname }}"
          text: |
            *Alert:* {{ .CommonLabels.alertname }}
            *Severity:* {{ .CommonLabels.severity }}
            *Team:* {{ .CommonLabels.team }}
            {{ range .Alerts }}
            *Description:* {{ .Annotations.description }}
            *Runbook:* {{ .Annotations.runbook_url }}
            {{ end }}
          color: "danger"

    - name: "finops-slack-warning"
      slackConfigs:
        - apiURL:
            name: finops-slack-webhook
            key: webhook-url
          channel: "#finops-alerts"
          sendResolved: true
          title: "[WARNING] Cost Alert: {{ .CommonLabels.alertname }}"
          text: |
            *Alert:* {{ .CommonLabels.alertname }}
            *Severity:* {{ .CommonLabels.severity }}
            *Team:* {{ .CommonLabels.team }}
            {{ range .Alerts }}
            *Description:* {{ .Annotations.description }}
            *Runbook:* {{ .Annotations.runbook_url }}
            {{ end }}
          color: "warning"

    - name: "finops-slack-info"
      slackConfigs:
        - apiURL:
            name: finops-slack-webhook
            key: webhook-url
          channel: "#finops-alerts"
          sendResolved: true
          title: "[INFO] Cost Alert: {{ .CommonLabels.alertname }}"
          text: |
            *Alert:* {{ .CommonLabels.alertname }}
            {{ range .Alerts }}
            *Description:* {{ .Annotations.description }}
            {{ end }}
          color: "#439FE0"

---
# Secret for Slack webhook URL
apiVersion: v1
kind: Secret
metadata:
  name: finops-slack-webhook
  namespace: monitoring
type: Opaque
stringData:
  webhook-url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
```

### 4.3 AWS Cost Anomaly Detection Integration

AWS Cost Anomaly Detection provides machine learning-based anomaly detection for your overall AWS spend, complementing the Kubernetes-level detection from Kubecost.

#### Setting Up AWS Cost Anomaly Detection

```bash
# Create a cost anomaly monitor for the EKS service
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "eks-cost-monitor",
    "MonitorType": "DIMENSIONAL",
    "MonitorDimension": "SERVICE",
    "MonitorSpecification": {
      "OR": null,
      "AND": null,
      "NOT": null,
      "Dimensions": {
        "Key": "SERVICE",
        "Values": [
          "Amazon Elastic Kubernetes Service",
          "Amazon EC2",
          "Amazon Elastic Block Store"
        ],
        "MatchOptions": ["EQUALS"]
      }
    }
  }'

# Create a subscription to receive anomaly alerts via SNS
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "eks-cost-anomaly-alerts",
    "Frequency": "DAILY",
    "MonitorArnList": [
      "arn:aws:ce::123456789012:anomalymonitor/monitor-id"
    ],
    "Subscribers": [
      {
        "Address": "arn:aws:sns:us-east-1:123456789012:finops-alerts",
        "Type": "SNS"
      }
    ],
    "ThresholdExpression": {
      "Dimensions": {
        "Key": "ANOMALY_TOTAL_IMPACT_ABSOLUTE",
        "Values": ["100"],
        "MatchOptions": ["GREATER_THAN_OR_EQUAL"]
      }
    }
  }'
```

For a Terraform-managed approach:

```hcl
# aws-cost-anomaly-detection.tf
resource "aws_ce_anomaly_monitor" "eks_monitor" {
  name              = "eks-cost-anomaly-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_sns_topic" "finops_alerts" {
  name = "finops-cost-anomaly-alerts"
}

resource "aws_sns_topic_subscription" "finops_email" {
  topic_arn = aws_sns_topic.finops_alerts.arn
  protocol  = "email"
  endpoint  = "finops-team@mycompany.com"
}

resource "aws_ce_anomaly_subscription" "eks_anomaly_subscription" {
  name      = "eks-anomaly-alerts"
  frequency = "DAILY"

  monitor_arn_list = [
    aws_ce_anomaly_monitor.eks_monitor.arn
  ]

  subscriber {
    type    = "SNS"
    address = aws_sns_topic.finops_alerts.arn
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = ["100"]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }
}
```

---

## 5. Team Self-Service Cost Management

Self-service cost management is the key to scaling FinOps beyond the platform team. When every engineering team can independently view their costs, understand their efficiency, and respond to budget alerts, the FinOps team can focus on strategy rather than ad-hoc reporting.

### 5.1 Per-Team Cost Dashboard

A variable-driven Grafana dashboard that allows each team to select their team name and see only their own costs. This is the primary self-service tool for engineering teams.

```yaml
# grafana-team-dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-team-cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "true"
data:
  team-cost-dashboard.json: |
    {
      "annotations": { "list": [] },
      "description": "Self-service cost dashboard for individual teams",
      "editable": false,
      "graphTooltip": 1,
      "panels": [
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "currencyUSD" }
          },
          "gridPos": { "h": 4, "w": 6, "x": 0, "y": 0 },
          "id": 1,
          "options": {
            "reduceOptions": { "calcs": ["lastNotNull"] },
            "colorMode": "value",
            "graphMode": "area"
          },
          "title": "Current Monthly Cost (Projected)",
          "type": "stat",
          "targets": [{
            "expr": "sum(kubecost_container_cpu_allocation_cost{namespace=~\"team-$team.*\"} + kubecost_container_memory_allocation_cost{namespace=~\"team-$team.*\"}) * 730",
            "legendFormat": "Projected Monthly",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "percentunit", "min": 0, "max": 1 }
          },
          "gridPos": { "h": 4, "w": 6, "x": 6, "y": 0 },
          "id": 2,
          "options": {
            "reduceOptions": { "calcs": ["lastNotNull"] },
            "colorMode": "value",
            "graphMode": "none"
          },
          "title": "CPU Efficiency",
          "type": "stat",
          "targets": [{
            "expr": "sum(rate(container_cpu_usage_seconds_total{namespace=~\"team-$team.*\"}[1h])) / sum(kube_pod_container_resource_requests{resource=\"cpu\", namespace=~\"team-$team.*\"})",
            "legendFormat": "CPU Efficiency",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "percentunit", "min": 0, "max": 1 }
          },
          "gridPos": { "h": 4, "w": 6, "x": 12, "y": 0 },
          "id": 3,
          "options": {
            "reduceOptions": { "calcs": ["lastNotNull"] },
            "colorMode": "value",
            "graphMode": "none"
          },
          "title": "Memory Efficiency",
          "type": "stat",
          "targets": [{
            "expr": "sum(container_memory_working_set_bytes{namespace=~\"team-$team.*\"}) / sum(kube_pod_container_resource_requests{resource=\"memory\", namespace=~\"team-$team.*\"})",
            "legendFormat": "Memory Efficiency",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "short" }
          },
          "gridPos": { "h": 4, "w": 6, "x": 18, "y": 0 },
          "id": 4,
          "options": {
            "reduceOptions": { "calcs": ["lastNotNull"] },
            "colorMode": "value",
            "graphMode": "area"
          },
          "title": "Active Pods",
          "type": "stat",
          "targets": [{
            "expr": "count(kube_pod_status_phase{namespace=~\"team-$team.*\", phase=\"Running\"})",
            "legendFormat": "Running Pods",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": {
              "unit": "currencyUSD",
              "custom": { "drawStyle": "line", "fillOpacity": 20 }
            }
          },
          "gridPos": { "h": 8, "w": 24, "x": 0, "y": 4 },
          "id": 5,
          "title": "Daily Cost Trend (Last 30 Days)",
          "type": "timeseries",
          "targets": [{
            "expr": "sum(kubecost_container_cpu_allocation_cost{namespace=~\"team-$team.*\"} + kubecost_container_memory_allocation_cost{namespace=~\"team-$team.*\"}) * 24",
            "legendFormat": "Daily Cost",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "currencyUSD" }
          },
          "gridPos": { "h": 8, "w": 12, "x": 0, "y": 12 },
          "id": 6,
          "title": "Cost by Service",
          "type": "piechart",
          "options": {
            "legend": { "displayMode": "table", "placement": "right" },
            "pieType": "donut"
          },
          "targets": [{
            "expr": "sum by (label_service) (kubecost_container_cpu_allocation_cost{namespace=~\"team-$team.*\"} + kubecost_container_memory_allocation_cost{namespace=~\"team-$team.*\"}) * 730",
            "legendFormat": "{{label_service}}",
            "refId": "A"
          }]
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": {
            "defaults": { "unit": "currencyUSD" }
          },
          "gridPos": { "h": 8, "w": 12, "x": 12, "y": 12 },
          "id": 7,
          "title": "Cost by Environment",
          "type": "piechart",
          "options": {
            "legend": { "displayMode": "table", "placement": "right" },
            "pieType": "donut"
          },
          "targets": [{
            "expr": "sum by (label_environment) (kubecost_container_cpu_allocation_cost{namespace=~\"team-$team.*\"} + kubecost_container_memory_allocation_cost{namespace=~\"team-$team.*\"}) * 730",
            "legendFormat": "{{label_environment}}",
            "refId": "A"
          }]
        }
      ],
      "schemaVersion": 39,
      "tags": ["finops", "team", "self-service"],
      "templating": {
        "list": [{
          "current": {},
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "definition": "label_values(kube_namespace_labels{label_team!=\"\"}, label_team)",
          "hide": 0,
          "includeAll": false,
          "multi": false,
          "name": "team",
          "query": "label_values(kube_namespace_labels{label_team!=\"\"}, label_team)",
          "refresh": 2,
          "sort": 1,
          "type": "query"
        }]
      },
      "time": { "from": "now-30d", "to": "now" },
      "title": "Team Cost Self-Service Dashboard",
      "uid": "finops-team-self-service-v1"
    }
```

### 5.2 Slack Cost Report Bot

A weekly CronJob that queries the Kubecost Allocation API and posts a formatted cost report to each team's Slack channel.

```yaml
# slack-cost-report-cronjob.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-report-script
  namespace: kubecost
data:
  send-cost-report.sh: |
    #!/bin/bash
    set -euo pipefail

    # Configuration
    KUBECOST_URL="${KUBECOST_URL:-http://kubecost-cost-analyzer.kubecost.svc:9090}"
    SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL}"
    REPORT_WINDOW="${REPORT_WINDOW:-7d}"
    CLUSTER_NAME="${CLUSTER_NAME:-production}"

    echo "Generating cost report for window: ${REPORT_WINDOW}"

    # Fetch allocation data aggregated by team
    ALLOCATION_DATA=$(curl -sf "${KUBECOST_URL}/model/allocation?window=${REPORT_WINDOW}&aggregate=label:team&accumulate=true&shareIdle=weighted&shareSplit=weighted&shareNamespaces=kube-system,monitoring,kubecost" 2>&1)

    if [ $? -ne 0 ]; then
      echo "ERROR: Failed to fetch allocation data from Kubecost"
      curl -sf -X POST "${SLACK_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \":warning: Weekly cost report failed to generate. Kubecost API unreachable.\"}"
      exit 1
    fi

    # Calculate total cluster cost
    TOTAL_COST=$(echo "${ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.totalCost] | add | round')
    TOTAL_CPU_COST=$(echo "${ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.cpuCost] | add | round')
    TOTAL_RAM_COST=$(echo "${ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.ramCost] | add | round')
    TOTAL_STORAGE_COST=$(echo "${ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.pvCost] | add | round')
    TOTAL_NETWORK_COST=$(echo "${ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.networkCost] | add | round')

    # Build per-team cost breakdown
    TEAM_BREAKDOWN=$(echo "${ALLOCATION_DATA}" | jq -r '
      .data[0] | to_entries
      | sort_by(-.value.totalCost)
      | .[]
      | select(.key != "__idle__" and .key != "__unallocated__")
      | "| \(.key) | $\(.value.totalCost | round) | \(.value.cpuEfficiency * 100 | round)% | \(.value.ramEfficiency * 100 | round)% |"
    ')

    # Get previous week data for comparison
    PREV_ALLOCATION_DATA=$(curl -sf "${KUBECOST_URL}/model/allocation?window=${REPORT_WINDOW}&aggregate=label:team&accumulate=true&offset=${REPORT_WINDOW}&shareIdle=weighted" 2>/dev/null || echo "{}")
    PREV_TOTAL_COST=$(echo "${PREV_ALLOCATION_DATA}" | jq '[.data[0] | to_entries[].value.totalCost // 0] | add | round' 2>/dev/null || echo "0")

    if [ "${PREV_TOTAL_COST}" -gt 0 ]; then
      COST_CHANGE_PCT=$(echo "scale=1; (${TOTAL_COST} - ${PREV_TOTAL_COST}) * 100 / ${PREV_TOTAL_COST}" | bc 2>/dev/null || echo "N/A")
      TREND_EMOJI=":chart_with_upwards_trend:"
      if [ "$(echo "${COST_CHANGE_PCT} < 0" | bc 2>/dev/null)" = "1" ]; then
        TREND_EMOJI=":chart_with_downwards_trend:"
      fi
      TREND_LINE="${TREND_EMOJI} Week-over-week change: ${COST_CHANGE_PCT}% (\$${PREV_TOTAL_COST} -> \$${TOTAL_COST})"
    else
      TREND_LINE="No previous week data available for comparison."
    fi

    # Build Slack message payload
    SLACK_PAYLOAD=$(cat <<PAYLOAD
    {
      "blocks": [
        {
          "type": "header",
          "text": {
            "type": "plain_text",
            "text": "Weekly Kubernetes Cost Report - ${CLUSTER_NAME}",
            "emoji": true
          }
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*Report Period:* Last ${REPORT_WINDOW}\n*Generated:* $(date -u '+%Y-%m-%d %H:%M UTC')"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*Total Cluster Cost:* \$${TOTAL_COST}\n- CPU: \$${TOTAL_CPU_COST}\n- Memory: \$${TOTAL_RAM_COST}\n- Storage: \$${TOTAL_STORAGE_COST}\n- Network: \$${TOTAL_NETWORK_COST}\n\n${TREND_LINE}"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*Cost by Team:*\n| Team | Cost | CPU Eff | Mem Eff |\n|------|------|---------|---------|${TEAM_BREAKDOWN}"
          }
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": ":bar_chart: <https://kubecost.internal.mycompany.com|View in Kubecost> | :chart_with_upwards_trend: <https://grafana.internal.mycompany.com/d/finops-showback-v1|View Dashboard>"
          }
        }
      ]
    }
    PAYLOAD
    )

    # Send to Slack
    RESPONSE=$(curl -sf -X POST "${SLACK_WEBHOOK_URL}" \
      -H "Content-Type: application/json" \
      -d "${SLACK_PAYLOAD}" 2>&1)

    if [ $? -eq 0 ]; then
      echo "Cost report sent successfully to Slack"
    else
      echo "ERROR: Failed to send cost report to Slack: ${RESPONSE}"
      exit 1
    fi
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-cost-report
  namespace: kubecost
  labels:
    app: cost-report-bot
    team: platform
    service: finops
spec:
  schedule: "0 9 * * 1"  # Every Monday at 9:00 AM UTC
  timeZone: "America/New_York"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 300
      template:
        metadata:
          labels:
            app: cost-report-bot
            team: platform
            service: finops
        spec:
          serviceAccountName: cost-report-bot
          restartPolicy: OnFailure
          containers:
            - name: cost-reporter
              image: curlimages/curl:8.7.1
              command:
                - /bin/sh
                - /scripts/send-cost-report.sh
              env:
                - name: KUBECOST_URL
                  value: "http://kubecost-cost-analyzer.kubecost.svc:9090"
                - name: SLACK_WEBHOOK_URL
                  valueFrom:
                    secretKeyRef:
                      name: cost-report-slack-webhook
                      key: webhook-url
                - name: REPORT_WINDOW
                  value: "7d"
                - name: CLUSTER_NAME
                  value: "production-eks-us-east-1"
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
          volumes:
            - name: scripts
              configMap:
                name: cost-report-script
                defaultMode: 0755
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cost-report-bot
  namespace: kubecost
---
apiVersion: v1
kind: Secret
metadata:
  name: cost-report-slack-webhook
  namespace: kubecost
type: Opaque
stringData:
  webhook-url: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
```

### 5.3 Cost Budget Setting and Alerts

Enable teams to define their own monthly budgets using a ConfigMap-driven approach. A controller or CronJob reads these budgets and triggers alerts when thresholds are approached.

```yaml
# team-budgets-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: team-cost-budgets
  namespace: kubecost
  labels:
    app: finops
data:
  budgets.json: |
    {
      "budgets": [
        {
          "team": "checkout",
          "monthlyBudget": 8000,
          "warningThreshold": 0.80,
          "criticalThreshold": 0.95,
          "slackChannel": "#checkout-alerts",
          "slackWebhook": "CHECKOUT_SLACK_WEBHOOK",
          "contacts": ["checkout-lead@mycompany.com"]
        },
        {
          "team": "payments",
          "monthlyBudget": 12000,
          "warningThreshold": 0.80,
          "criticalThreshold": 0.95,
          "slackChannel": "#payments-alerts",
          "slackWebhook": "PAYMENTS_SLACK_WEBHOOK",
          "contacts": ["payments-lead@mycompany.com"]
        },
        {
          "team": "search",
          "monthlyBudget": 15000,
          "warningThreshold": 0.80,
          "criticalThreshold": 0.95,
          "slackChannel": "#search-alerts",
          "slackWebhook": "SEARCH_SLACK_WEBHOOK",
          "contacts": ["search-lead@mycompany.com"]
        },
        {
          "team": "platform",
          "monthlyBudget": 20000,
          "warningThreshold": 0.80,
          "criticalThreshold": 0.95,
          "slackChannel": "#platform-alerts",
          "slackWebhook": "PLATFORM_SLACK_WEBHOOK",
          "contacts": ["platform-lead@mycompany.com"]
        },
        {
          "team": "data-engineering",
          "monthlyBudget": 25000,
          "warningThreshold": 0.75,
          "criticalThreshold": 0.90,
          "slackChannel": "#data-eng-alerts",
          "slackWebhook": "DATA_ENG_SLACK_WEBHOOK",
          "contacts": ["data-lead@mycompany.com"]
        }
      ]
    }
---
# Budget check CronJob - runs every 6 hours
apiVersion: batch/v1
kind: CronJob
metadata:
  name: budget-check
  namespace: kubecost
  labels:
    app: finops
    component: budget-checker
spec:
  schedule: "0 */6 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 2
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 180
      template:
        metadata:
          labels:
            app: finops
            component: budget-checker
        spec:
          serviceAccountName: cost-report-bot
          restartPolicy: OnFailure
          containers:
            - name: budget-checker
              image: curlimages/curl:8.7.1
              command:
                - /bin/sh
                - -c
                - |
                  set -euo pipefail

                  KUBECOST_URL="http://kubecost-cost-analyzer.kubecost.svc:9090"
                  BUDGETS_FILE="/config/budgets.json"

                  # Get current month allocation by team
                  ALLOCATION=$(curl -sf "${KUBECOST_URL}/model/allocation?window=thismonth&aggregate=label:team&accumulate=true&shareIdle=weighted")

                  # Get number of days elapsed and total in month
                  DAY_OF_MONTH=$(date +%d)
                  DAYS_IN_MONTH=$(date -d "$(date +%Y-%m-01) +1 month -1 day" +%d)

                  # Read each budget and check against actual spend
                  echo "${BUDGETS_FILE} contents:"
                  cat "${BUDGETS_FILE}"

                  TEAMS=$(cat "${BUDGETS_FILE}" | jq -r '.budgets[].team')

                  for TEAM in ${TEAMS}; do
                    BUDGET=$(cat "${BUDGETS_FILE}" | jq -r ".budgets[] | select(.team == \"${TEAM}\") | .monthlyBudget")
                    WARNING_PCT=$(cat "${BUDGETS_FILE}" | jq -r ".budgets[] | select(.team == \"${TEAM}\") | .warningThreshold")
                    CRITICAL_PCT=$(cat "${BUDGETS_FILE}" | jq -r ".budgets[] | select(.team == \"${TEAM}\") | .criticalThreshold")
                    CHANNEL=$(cat "${BUDGETS_FILE}" | jq -r ".budgets[] | select(.team == \"${TEAM}\") | .slackChannel")

                    # Get actual cost for this team
                    ACTUAL_COST=$(echo "${ALLOCATION}" | jq -r ".data[0][\"${TEAM}\"].totalCost // 0 | round")

                    # Project monthly cost based on burn rate
                    PROJECTED_COST=$(echo "scale=0; ${ACTUAL_COST} * ${DAYS_IN_MONTH} / ${DAY_OF_MONTH}" | bc)

                    # Calculate budget usage percentage
                    BUDGET_USAGE=$(echo "scale=4; ${PROJECTED_COST} / ${BUDGET}" | bc)

                    echo "Team: ${TEAM} | Actual: \$${ACTUAL_COST} | Projected: \$${PROJECTED_COST} | Budget: \$${BUDGET} | Usage: ${BUDGET_USAGE}"

                    # Check thresholds and send alerts
                    CRITICAL_THRESHOLD=$(echo "scale=4; ${CRITICAL_PCT}" | bc)
                    WARNING_THRESHOLD=$(echo "scale=4; ${WARNING_PCT}" | bc)

                    if [ "$(echo "${BUDGET_USAGE} >= ${CRITICAL_THRESHOLD}" | bc)" = "1" ]; then
                      ALERT_MSG=":rotating_light: *CRITICAL Budget Alert* - Team: *${TEAM}*\nProjected monthly cost: \$${PROJECTED_COST} / \$${BUDGET} budget ($(echo "scale=0; ${BUDGET_USAGE} * 100" | bc)%)\nActual spend this month: \$${ACTUAL_COST}\nAction required: Review and reduce resource usage immediately."
                      curl -sf -X POST "${SLACK_WEBHOOK_URL}" \
                        -H "Content-Type: application/json" \
                        -d "{\"channel\": \"${CHANNEL}\", \"text\": \"${ALERT_MSG}\"}"
                    elif [ "$(echo "${BUDGET_USAGE} >= ${WARNING_THRESHOLD}" | bc)" = "1" ]; then
                      ALERT_MSG=":warning: *Budget Warning* - Team: *${TEAM}*\nProjected monthly cost: \$${PROJECTED_COST} / \$${BUDGET} budget ($(echo "scale=0; ${BUDGET_USAGE} * 100" | bc)%)\nActual spend this month: \$${ACTUAL_COST}\nConsider reviewing resource efficiency."
                      curl -sf -X POST "${SLACK_WEBHOOK_URL}" \
                        -H "Content-Type: application/json" \
                        -d "{\"channel\": \"${CHANNEL}\", \"text\": \"${ALERT_MSG}\"}"
                    fi
                  done

                  echo "Budget check completed successfully"
              env:
                - name: SLACK_WEBHOOK_URL
                  valueFrom:
                    secretKeyRef:
                      name: cost-report-slack-webhook
                      key: webhook-url
              resources:
                requests:
                  cpu: "50m"
                  memory: "64Mi"
                limits:
                  cpu: "200m"
                  memory: "128Mi"
              volumeMounts:
                - name: budget-config
                  mountPath: /config
          volumes:
            - name: budget-config
              configMap:
                name: team-cost-budgets
```

---

## 6. Resource Rightsizing Automation

Rightsizing is the process of matching resource requests and limits to actual workload usage. Over-provisioning wastes money; under-provisioning causes performance problems and OOM kills. The goal is to find the "just right" configuration for each workload.

### 6.1 VPA Recommendation Workflow

The Vertical Pod Autoscaler (VPA) can be run in recommendation-only mode (`updateMode: "Off"`) to provide resource suggestions without automatically changing workloads. This is the safest starting point.

```yaml
# vpa-recommendation-mode.yaml
# VPA for the order-service - recommendation only
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: order-service-vpa
  namespace: team-checkout
  labels:
    team: checkout
    service: order-service
    finops-rightsizing: "true"
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  updatePolicy:
    updateMode: "Off"  # Recommendation only, no automatic updates
  resourcePolicy:
    containerPolicies:
      - containerName: order-service
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
# VPA for the payment-processor - recommendation only
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: payment-processor-vpa
  namespace: team-payments
  labels:
    team: payments
    service: payment-processor
    finops-rightsizing: "true"
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-processor
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
      - containerName: payment-processor
        minAllowed:
          cpu: "100m"
          memory: "128Mi"
        maxAllowed:
          cpu: "8"
          memory: "16Gi"
        controlledResources:
          - cpu
          - memory
        controlledValues: RequestsAndLimits
---
# VPA for the user-service - recommendation only
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: user-service-vpa
  namespace: team-platform
  labels:
    team: platform
    service: user-service
    finops-rightsizing: "true"
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

To review VPA recommendations:

```bash
# Get recommendations for all VPAs in a namespace
kubectl get vpa -n team-checkout -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{"\t"}Target CPU: {.status.recommendation.containerRecommendations[0].target.cpu}{"\n"}{"\t"}Target Memory: {.status.recommendation.containerRecommendations[0].target.memory}{"\n"}{"\t"}Upper Bound CPU: {.status.recommendation.containerRecommendations[0].upperBound.cpu}{"\n"}{"\t"}Upper Bound Memory: {.status.recommendation.containerRecommendations[0].upperBound.memory}{"\n"}{end}'

# Compare current requests with VPA recommendations
kubectl get vpa -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,TARGET_CPU:.status.recommendation.containerRecommendations[0].target.cpu,TARGET_MEM:.status.recommendation.containerRecommendations[0].target.memory,UPPER_CPU:.status.recommendation.containerRecommendations[0].upperBound.cpu,UPPER_MEM:.status.recommendation.containerRecommendations[0].upperBound.memory'
```

### 6.2 Goldilocks Dashboard

Goldilocks runs VPA in recommendation mode for every Deployment in labeled namespaces and provides a web dashboard showing the current resource settings versus VPA recommendations.

#### Goldilocks Installation

```yaml
# goldilocks-values.yaml
# helm repo add fairwinds-stable https://charts.fairwinds.com/stable
# helm install goldilocks fairwinds-stable/goldilocks -n goldilocks --create-namespace -f goldilocks-values.yaml

vpa:
  enabled: true  # Install VPA if not already present
  updater:
    enabled: false  # We only want recommendations

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
      alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
      alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:us-east-1:123456789012:certificate/abc-123"
    hosts:
      - host: "goldilocks.internal.mycompany.com"
        paths:
          - path: /
            pathType: Prefix

controller:
  enabled: true
  resources:
    requests:
      cpu: "50m"
      memory: "64Mi"
    limits:
      cpu: "200m"
      memory: "128Mi"

# Service account
serviceAccount:
  create: true
```

#### Enable Goldilocks for Namespaces

Label namespaces to opt them into Goldilocks monitoring:

```bash
# Enable Goldilocks for team namespaces
kubectl label namespace team-checkout goldilocks.fairwinds.com/enabled=true
kubectl label namespace team-payments goldilocks.fairwinds.com/enabled=true
kubectl label namespace team-search goldilocks.fairwinds.com/enabled=true
kubectl label namespace team-platform goldilocks.fairwinds.com/enabled=true
kubectl label namespace team-data-engineering goldilocks.fairwinds.com/enabled=true

# Verify labeling
kubectl get namespaces -l goldilocks.fairwinds.com/enabled=true

# Exclude specific VPAs from Goldilocks (optional)
kubectl label deployment special-workload -n team-checkout goldilocks.fairwinds.com/vpa-update-mode=off
```

### 6.3 Automated Resource Adjustment Pipeline

For mature organizations, VPA recommendations can flow into an automated pipeline that creates pull requests for resource changes, allowing human review before application.

```mermaid
graph LR
    A[VPA Recommendations] --> B[CronJob: Collect Recommendations]
    B --> C[Compare with Current Requests]
    C --> D{Change > 20% Threshold?}
    D -->|Yes| E[Generate YAML Patch]
    E --> F[Create Git Branch]
    F --> G[Open Pull Request]
    G --> H[Team Review]
    H --> I[ArgoCD Auto-Sync]
    D -->|No| J[Skip - Within Tolerance]
```

```yaml
# rightsizing-pipeline-cronjob.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rightsizing-script
  namespace: kubecost
data:
  collect-recommendations.sh: |
    #!/bin/bash
    set -euo pipefail

    # Configuration
    THRESHOLD=0.20  # Only flag changes greater than 20%
    GIT_REPO="git@github.com:mycompany/k8s-manifests.git"
    GIT_BRANCH="rightsizing/$(date +%Y%m%d)"
    OUTPUT_DIR="/tmp/recommendations"

    mkdir -p "${OUTPUT_DIR}"

    echo "Collecting VPA recommendations with threshold: ${THRESHOLD}"

    # Get all VPAs with finops-rightsizing label
    VPAS=$(kubectl get vpa -A -l finops-rightsizing=true -o json)

    # Process each VPA
    echo "${VPAS}" | jq -c '.items[]' | while read -r VPA; do
      NAMESPACE=$(echo "${VPA}" | jq -r '.metadata.namespace')
      VPA_NAME=$(echo "${VPA}" | jq -r '.metadata.name')
      TARGET_KIND=$(echo "${VPA}" | jq -r '.spec.targetRef.kind')
      TARGET_NAME=$(echo "${VPA}" | jq -r '.spec.targetRef.name')

      # Get VPA recommendation
      REC_CPU=$(echo "${VPA}" | jq -r '.status.recommendation.containerRecommendations[0].target.cpu // empty')
      REC_MEM=$(echo "${VPA}" | jq -r '.status.recommendation.containerRecommendations[0].target.memory // empty')

      if [ -z "${REC_CPU}" ] || [ -z "${REC_MEM}" ]; then
        echo "SKIP: ${NAMESPACE}/${VPA_NAME} - no recommendation available yet"
        continue
      fi

      # Get current resource requests
      CURRENT=$(kubectl get "${TARGET_KIND}" "${TARGET_NAME}" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.template.spec.containers[0].resources.requests}')
      CURRENT_CPU=$(echo "${CURRENT}" | jq -r '.cpu // "0"')
      CURRENT_MEM=$(echo "${CURRENT}" | jq -r '.memory // "0"')

      echo "VPA: ${NAMESPACE}/${VPA_NAME}"
      echo "  Current:     CPU=${CURRENT_CPU}, Memory=${CURRENT_MEM}"
      echo "  Recommended: CPU=${REC_CPU}, Memory=${REC_MEM}"

      # Write recommendation to file for PR generation
      cat > "${OUTPUT_DIR}/${NAMESPACE}-${TARGET_NAME}.json" <<RECEOF
    {
      "namespace": "${NAMESPACE}",
      "kind": "${TARGET_KIND}",
      "name": "${TARGET_NAME}",
      "current": {
        "cpu": "${CURRENT_CPU}",
        "memory": "${CURRENT_MEM}"
      },
      "recommended": {
        "cpu": "${REC_CPU}",
        "memory": "${REC_MEM}"
      },
      "vpa": "${VPA_NAME}",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
    RECEOF
    done

    # Count recommendations
    REC_COUNT=$(ls "${OUTPUT_DIR}"/*.json 2>/dev/null | wc -l)
    echo "Collected ${REC_COUNT} recommendations"

    if [ "${REC_COUNT}" -eq 0 ]; then
      echo "No recommendations to process"
      exit 0
    fi

    # Generate summary report
    echo "=== Rightsizing Recommendation Summary ==="
    for FILE in "${OUTPUT_DIR}"/*.json; do
      ENTRY=$(cat "${FILE}")
      NS=$(echo "${ENTRY}" | jq -r '.namespace')
      NAME=$(echo "${ENTRY}" | jq -r '.name')
      CUR_CPU=$(echo "${ENTRY}" | jq -r '.current.cpu')
      REC_CPU=$(echo "${ENTRY}" | jq -r '.recommended.cpu')
      CUR_MEM=$(echo "${ENTRY}" | jq -r '.current.memory')
      REC_MEM=$(echo "${ENTRY}" | jq -r '.recommended.memory')
      echo "  ${NS}/${NAME}: CPU ${CUR_CPU} -> ${REC_CPU}, Memory ${CUR_MEM} -> ${REC_MEM}"
    done
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rightsizing-recommendations
  namespace: kubecost
  labels:
    app: finops
    component: rightsizing
spec:
  schedule: "0 6 * * 1"  # Every Monday at 6:00 AM UTC
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 600
      template:
        metadata:
          labels:
            app: finops
            component: rightsizing
        spec:
          serviceAccountName: rightsizing-bot
          restartPolicy: OnFailure
          containers:
            - name: recommender
              image: bitnami/kubectl:1.30
              command:
                - /bin/bash
                - /scripts/collect-recommendations.sh
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
          volumes:
            - name: scripts
              configMap:
                name: rightsizing-script
                defaultMode: 0755
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: rightsizing-bot
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
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: rightsizing-reader-binding
subjects:
  - kind: ServiceAccount
    name: rightsizing-bot
    namespace: kubecost
roleRef:
  kind: ClusterRole
  name: rightsizing-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## 7. Cost Optimization Governance

Governance ensures that cost optimization is not a one-time effort but a sustained organizational practice. It combines automated policy enforcement with regular human review processes.

### 7.1 Idle Resource Auto-Detection

Use PromQL queries to identify workloads that are consuming resources but not handling meaningful traffic. These are candidates for scaling down or decommissioning.

#### Detect Deployments with Near-Zero CPU Usage

```promql
# Deployments using less than 1% of their CPU requests over 7 days
# These are likely idle and candidates for removal or scale-down
(
  sum by (namespace, deployment) (
    rate(container_cpu_usage_seconds_total{namespace!~"kube-system|monitoring|kubecost"}[7d])
  )
  /
  sum by (namespace, deployment) (
    kube_pod_container_resource_requests{resource="cpu", namespace!~"kube-system|monitoring|kubecost"}
    * on(pod) group_left(deployment)
    kube_pod_owner{owner_kind="ReplicaSet"}
  )
) < 0.01
```

#### Detect Deployments with Consistently Low Memory Usage

```promql
# Deployments using less than 10% of their memory requests over 7 days
# Strong candidates for rightsizing
(
  sum by (namespace, deployment) (
    avg_over_time(container_memory_working_set_bytes{namespace!~"kube-system|monitoring|kubecost"}[7d])
  )
  /
  sum by (namespace, deployment) (
    kube_pod_container_resource_requests{resource="memory", namespace!~"kube-system|monitoring|kubecost"}
    * on(pod) group_left(deployment)
    kube_pod_owner{owner_kind="ReplicaSet"}
  )
) < 0.10
```

#### Detect Deployments with Zero Network Traffic

```promql
# Deployments that have received zero inbound network bytes for 7 days
# These services are not handling any traffic and may be unused
sum by (namespace, pod) (
  increase(container_network_receive_bytes_total{namespace!~"kube-system|monitoring|kubecost"}[7d])
) == 0
```

#### Detect Persistent Volumes Not Attached to Any Pod

```promql
# PVCs that are bound but not mounted by any pod
# These are wasting storage costs
kube_persistentvolumeclaim_status_phase{phase="Bound"} 
unless on(persistentvolumeclaim, namespace)
kube_pod_spec_volumes_persistentvolumeclaims_info
```

### 7.2 Cost Policies (Kyverno)

Policy enforcement prevents cost waste at the source. The following Kyverno policies catch common cost anti-patterns before workloads are deployed.

#### Block Deployments Without Resource Limits

```yaml
# kyverno-require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: Require Resource Limits
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: high
    policies.kyverno.io/description: >-
      All containers must specify CPU and memory limits to prevent
      unbounded resource consumption that leads to cost overruns
      and noisy-neighbor problems.
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: validate-resource-limits
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - kube-node-lease
      validate:
        message: >-
          All containers must have CPU and memory limits defined.
          Container '{{request.object.spec.containers[*].name}}' is missing resource limits.
          Add resources.limits.cpu and resources.limits.memory to your container spec.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                any:
                  - key: "{{ element.resources.limits.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.limits.memory || '' }}"
                    operator: Equals
                    value: ""

    - name: validate-init-container-limits
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - kube-public
                - kube-node-lease
      preconditions:
        all:
          - key: "{{ request.object.spec.initContainers[] || `[]` | length(@) }}"
            operator: GreaterThan
            value: 0
      validate:
        message: >-
          Init containers must also have resource limits defined.
        foreach:
          - list: "request.object.spec.initContainers"
            deny:
              conditions:
                any:
                  - key: "{{ element.resources.limits.cpu || '' }}"
                    operator: Equals
                    value: ""
                  - key: "{{ element.resources.limits.memory || '' }}"
                    operator: Equals
                    value: ""
```

#### Warn on Over-Provisioned Resources

```yaml
# kyverno-warn-over-provisioned.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: warn-over-provisioned-resources
  annotations:
    policies.kyverno.io/title: Warn on Over-Provisioned Resources
    policies.kyverno.io/category: FinOps
    policies.kyverno.io/severity: medium
    policies.kyverno.io/description: >-
      Generates a warning when containers request more than 4 CPU cores
      or 8Gi of memory. While not blocked, these workloads should be
      reviewed to ensure the requests are justified by actual usage.
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: warn-high-cpu-request
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - monitoring
                - kubecost
      validate:
        message: >-
          Container '{{ element.name }}' requests {{ element.resources.requests.cpu }} CPU.
          Requests above 4 CPU cores should be reviewed for rightsizing.
          Consider running VPA in recommendation mode to validate actual usage.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ element.resources.requests.cpu || '0' }}"
                    operator: GreaterThan
                    value: "4000m"

    - name: warn-high-memory-request
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - monitoring
                - kubecost
      validate:
        message: >-
          Container '{{ element.name }}' requests {{ element.resources.requests.memory }} memory.
          Requests above 8Gi should be reviewed for rightsizing.
          Consider running VPA in recommendation mode to validate actual usage.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ element.resources.requests.memory || '0' }}"
                    operator: GreaterThan
                    value: "8Gi"

    - name: warn-high-limits-to-requests-ratio
      match:
        any:
          - resources:
              kinds:
                - Pod
      exclude:
        any:
          - resources:
              namespaces:
                - kube-system
                - monitoring
                - kubecost
      validate:
        message: >-
          Container '{{ element.name }}' has a CPU limits-to-requests ratio greater than 5x.
          A high ratio indicates potential resource waste. Consider tightening the gap between
          requests and limits based on actual usage patterns.
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ divide( '{{ element.resources.limits.cpu }}', '{{ element.resources.requests.cpu }}') }}"
                    operator: GreaterThan
                    value: 5
```

### 7.3 Regular Cost Review Process

Automated tools catch the obvious waste, but human judgment is needed for strategic cost decisions. Establish a regular cadence of cost reviews at different organizational levels.

#### Review Cadence

| Review Type | Frequency | Participants | Duration | Key Agenda |
|------------|-----------|-------------|----------|------------|
| **Team Sprint Review** | Every 2 weeks | Team lead, engineers | 15 min | Review team dashboard, address rightsizing recommendations, check for idle resources |
| **Weekly FinOps Standup** | Weekly (Monday) | FinOps lead, platform eng | 30 min | Review weekly cost report, triage anomaly alerts, prioritize optimization actions |
| **Monthly Cost Review** | Monthly (1st week) | FinOps, engineering leads, finance | 60 min | Month-over-month trends, budget vs. actual, optimization ROI, next month forecast |
| **Quarterly Business Review** | Quarterly | Leadership, FinOps, finance | 90 min | Unit economics, cost per customer, efficiency targets, strategic savings initiatives |

#### Monthly Review Template

| Section | Content | Data Source |
|---------|---------|-------------|
| **Executive Summary** | Total spend, month-over-month change, budget status | Kubecost monthly report |
| **Cost by Team** | Breakdown with efficiency scores | Kubecost Allocation API |
| **Top 5 Cost Drivers** | Services with highest spend or highest growth | Kubecost trend analysis |
| **Optimization Wins** | Savings achieved from rightsizing, idle cleanup | Before/after comparisons |
| **Anomalies** | Unexplained cost changes investigated | Anomaly alert history |
| **Rightsizing Backlog** | VPA recommendations not yet applied | Goldilocks dashboard |
| **Idle Resources** | Resources identified for cleanup | Prometheus queries |
| **Action Items** | Assigned owners and due dates | Previous review follow-up |
| **Forecast** | Projected next month and quarter spend | Burn rate extrapolation |

#### Monthly Review Checklist

```
Monthly FinOps Review Checklist
================================

Pre-Meeting (FinOps Lead):
[ ] Generate monthly cost report from Kubecost
[ ] Run idle resource detection queries
[ ] Compile VPA recommendation summary from Goldilocks
[ ] Calculate month-over-month cost changes per team
[ ] Prepare budget vs. actual comparison
[ ] Review and summarize all anomaly alerts from the past month

During Meeting:
[ ] Walk through executive summary
[ ] Review each team's cost and efficiency
[ ] Discuss top cost drivers and growth areas
[ ] Celebrate optimization wins (positive reinforcement)
[ ] Triage open rightsizing recommendations
[ ] Assign action items with owners and due dates

Post-Meeting:
[ ] Send meeting notes to all participants
[ ] Update team budget allocations if needed
[ ] Create tickets for assigned optimization work
[ ] Update dashboards with any new metrics requested
[ ] Schedule follow-ups for critical action items
```

---

## 8. Best Practices

### Numbered Best Practices

1. **Start with visibility before optimization.** Deploy Kubecost or OpenCost and establish accurate cost allocation before attempting any optimization. Optimizing without visibility is guesswork, and you cannot measure the impact of changes without a baseline. Allow 2-4 weeks of data collection before making recommendations.

2. **Enforce labels from day one.** Retroactively labeling hundreds of workloads is painful and error-prone. Use Kyverno or OPA/Gatekeeper to enforce cost labels as an admission requirement from the very beginning. Labels are the foundation of all cost allocation, and missing labels create "unallocated" costs that erode trust in the data.

3. **Use VPA in recommendation mode before auto-applying.** Never enable VPA auto-update on production workloads without first running in recommendation mode for at least two weeks. Auto-updates cause pod restarts, and incorrect recommendations (e.g., based on insufficient data) can cause outages. Build confidence in the recommendations before automating.

4. **Separate showback from chargeback timelines.** Showback (visibility without billing) should come first. Give teams 2-3 months to see and understand their costs before implementing chargeback (actual billing). This builds trust in the data and gives teams time to optimize before costs hit their budgets.

5. **Account for shared costs transparently.** Do not hide shared infrastructure costs. Distribute them using a documented, agreed-upon methodology (weighted by usage, even split, etc.) and show the breakdown clearly in dashboards. Hidden costs breed distrust and disputes.

6. **Set budgets with a buffer.** Initial budgets should include a 15-20% buffer above current spend to account for growth and variability. Overly tight budgets create alert fatigue and discourage experimentation. Tighten budgets gradually as teams build confidence in their cost management.

7. **Make cost a team-level metric, not an individual one.** Cost accountability should be at the team or service level, never at the individual engineer level. Individual attribution creates perverse incentives (engineers avoiding necessary scaling) and a blame culture that undermines the collaborative spirit of FinOps.

8. **Automate the review process.** Manual cost reviews depend on someone remembering to run them. Automate weekly Slack reports, budget alerts, and rightsizing recommendation collection. The platform team should invest in self-service tools so that FinOps scales without headcount.

### Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| **Cost data hoarding** | Only the platform team has access to cost data; engineering teams cannot see their own costs | Deploy team self-service dashboards with variable-driven Grafana views; share weekly Slack reports automatically |
| **Alert-only FinOps** | Setting up cost alerts but never acting on them; alerts become noise | Pair every alert with a runbook and an assigned owner; track alert-to-resolution time as a metric |
| **Over-optimizing non-production** | Spending engineering time optimizing dev/staging environments that are a small fraction of total cost | Focus optimization efforts on production first; use simple policies (e.g., scale-to-zero at night) for non-production |
| **Ignoring data transfer costs** | Focusing exclusively on compute/memory costs while data transfer silently grows | Include network costs in all dashboards; integrate CUR data for accurate transfer cost visibility; review cross-AZ traffic patterns |

---

## 9. References

### External References

- [OpenCost Documentation](https://www.opencost.io/docs/) - Open-source Kubernetes cost monitoring
- [Kubecost Documentation](https://docs.kubecost.com/) - Enterprise Kubernetes cost management
- [AWS Cost and Usage Report](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html) - AWS billing data export
- [FinOps Foundation](https://www.finops.org/) - FinOps best practices and community
- [FinOps Framework](https://www.finops.org/framework/) - Inform, Optimize, Operate lifecycle
- [Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler) - Kubernetes VPA documentation
- [Goldilocks by Fairwinds](https://goldilocks.docs.fairwinds.com/) - VPA recommendation dashboard
- [Kyverno Policy Library](https://kyverno.io/policies/) - Policy examples for Kubernetes

### Internal References

- [EKS Cost Optimization](../eks/07-eks-cost-optimization.md) - AWS-specific cost optimization strategies for EKS
- [Resource Optimization](./10-resource-optimization.md) - Detailed resource requests/limits tuning and framework-specific guides
- [Scaling Strategies](./06-scaling-strategies.md) - HPA, KEDA, VPA, and Spot utilization strategies
- [Event Capacity Planning](./12-event-capacity-planning.md) - Cost-aware scaling for traffic events
- [Observability Alert Configuration](./07-observability-alerts.md) - Alert pipeline setup and Prometheus alerting patterns
