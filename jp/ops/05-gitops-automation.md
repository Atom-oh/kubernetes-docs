# GitOps Automation: Atlantis, FluxCD, AIOps

> **対応バージョン**: EKS 1.28+, Atlantis 0.27+, FluxCD v2.2+, Terraform 1.6+
> **最終更新**: February 21, 2026

< [前へ: ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | [目次](./README.md) | [次へ: Scaling Strategies](./06-scaling-strategies.md) >

---

## はじめに

GitOps automation は、application deployment を超えて infrastructure management まで拡張されます。このガイドでは、Terraform PR workflow のための Atlantis、ArgoCD の代替としての FluxCD、そして intelligent automation のために登場しつつある AIOps pattern を扱います。

---

## 1. EKS 上の Atlantis

Atlantis は Terraform の pull request automation を提供し、code review workflow を通じて infrastructure change を可能にします。

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub/GitLab                            │
│                                                                 │
│  ┌──────────────┐    Webhook     ┌──────────────────────────┐  │
│  │  Pull Request │ ──────────────▶│      Atlantis Pod       │  │
│  │  (terraform/) │               │                          │  │
│  └──────────────┘               │  ┌────────────────────┐  │  │
│         ▲                        │  │   Plan/Apply       │  │  │
│         │                        │  │   Execution        │  │  │
│         │ Comment                │  └─────────┬──────────┘  │  │
│         │ (plan output)          │            │             │  │
│         │                        │            ▼             │  │
│         └────────────────────────│  ┌────────────────────┐  │  │
│                                  │  │   AWS Provider     │  │  │
│                                  │  │   (Pod Identity)   │  │  │
│                                  │  └────────────────────┘  │  │
│                                  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Helm Installation

```yaml
# atlantis-values.yaml
replicaCount: 1

image:
  repository: ghcr.io/runatlantis/atlantis
  tag: v0.27.3

ingress:
  enabled: true
  ingressClassName: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:ap-northeast-2:ACCOUNT:certificate/CERT_ID
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/security-groups: sg-atlantis-alb
  hosts:
    - host: atlantis.example.com
      paths:
        - /

# GitHub Configuration
github:
  user: atlantis-bot
  # Secret reference for token
  secret:
    name: atlantis-github-secrets
    usernameKey: username
    tokenKey: token

# Webhook Secret
githubWebhookSecret:
  secret:
    name: atlantis-github-secrets
    key: webhook-secret

# Service Account for Pod Identity
serviceAccount:
  create: true
  name: atlantis
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/atlantis-terraform-role

# Resource Configuration
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

# Persistent Volume for Locks
persistence:
  enabled: true
  storageClassName: gp3
  size: 10Gi

# Environment Variables
environment:
  ATLANTIS_REPO_ALLOWLIST: "github.com/myorg/*"
  ATLANTIS_ENABLE_DIFF_MARKDOWN_FORMAT: "true"
  ATLANTIS_PARALLEL_POOL_SIZE: "5"
  ATLANTIS_DEFAULT_TF_VERSION: "1.6.6"

# Server-side Repository Config
repoConfig: |
  ---
  repos:
    - id: github.com/myorg/infrastructure
      branch: main
      allowed_overrides: [workflow, apply_requirements]
      allow_custom_workflows: true
      delete_source_branch_on_merge: true

volumeMounts:
  - name: atlantis-config
    mountPath: /home/atlantis/.atlantis
    readOnly: true

volumes:
  - name: atlantis-config
    configMap:
      name: atlantis-repo-config
```

Helm で install します:

```bash
helm repo add runatlantis https://runatlantis.github.io/helm-charts
helm repo update

kubectl create namespace atlantis

# Create secrets
kubectl create secret generic atlantis-github-secrets \
  --namespace atlantis \
  --from-literal=username=atlantis-bot \
  --from-literal=token=${GITHUB_TOKEN} \
  --from-literal=webhook-secret=${WEBHOOK_SECRET}

helm install atlantis runatlantis/atlantis \
  --namespace atlantis \
  --values atlantis-values.yaml
```

### 1.3 Repository Configuration (atlantis.yaml)

```yaml
# atlantis.yaml at repository root
version: 3
automerge: false
delete_source_branch_on_merge: true
parallel_plan: true
parallel_apply: false

projects:
  # Network Layer
  - name: network-dev
    dir: terraform/network
    workspace: dev
    terraform_version: v1.6.6
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
        - "../modules/vpc/**/*.tf"
      enabled: true
    apply_requirements:
      - approved
      - mergeable
    workflow: network

  - name: network-prod
    dir: terraform/network
    workspace: prod
    terraform_version: v1.6.6
    autoplan:
      when_modified:
        - "*.tf"
        - "*.tfvars"
        - "../modules/vpc/**/*.tf"
      enabled: true
    apply_requirements:
      - approved
      - mergeable
    workflow: network-prod

  # EKS Cluster
  - name: eks-dev
    dir: terraform/eks
    workspace: dev
    terraform_version: v1.6.6
    autoplan:
      when_modified:
        - "*.tf"
        - "environments/dev.tfvars"
      enabled: true
    apply_requirements:
      - approved
    workflow: eks

  - name: eks-prod
    dir: terraform/eks
    workspace: prod
    terraform_version: v1.6.6
    autoplan:
      when_modified:
        - "*.tf"
        - "environments/prod.tfvars"
      enabled: true
    apply_requirements:
      - approved
      - mergeable
    workflow: eks-prod

  # Application Infrastructure
  - name: app-infra-dev
    dir: terraform/app-infra
    workspace: dev
    autoplan:
      when_modified:
        - "**/*.tf"
      enabled: true
    workflow: default

workflows:
  default:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - apply

  network:
    plan:
      steps:
        - init:
            extra_args: ["-backend-config=environments/dev-backend.hcl"]
        - plan:
            extra_args: ["-var-file=environments/dev.tfvars"]
    apply:
      steps:
        - apply

  network-prod:
    plan:
      steps:
        - init:
            extra_args: ["-backend-config=environments/prod-backend.hcl"]
        - plan:
            extra_args: ["-var-file=environments/prod.tfvars", "-lock-timeout=300s"]
    apply:
      steps:
        - run: echo "Applying production network changes..."
        - apply

  eks:
    plan:
      steps:
        - init
        - run: terraform validate
        - run: tflint --init && tflint
        - plan:
            extra_args: ["-var-file=environments/dev.tfvars"]
    apply:
      steps:
        - apply
        - run: |
            aws eks update-kubeconfig --name ${PROJECT_NAME} --region ap-northeast-2
            kubectl get nodes

  eks-prod:
    plan:
      steps:
        - init
        - run: terraform validate
        - run: tflint --init && tflint
        - run: checkov -d . --framework terraform --quiet
        - plan:
            extra_args: ["-var-file=environments/prod.tfvars"]
    apply:
      steps:
        - run: |
            # Require 2 approvals for production
            APPROVALS=$(gh pr view $PULL_NUM --json reviews -q '[.reviews[] | select(.state=="APPROVED")] | length')
            if [ "$APPROVALS" -lt 2 ]; then
              echo "Production requires 2 approvals. Current: $APPROVALS"
              exit 1
            fi
        - apply
        - run: |
            # Post-apply validation
            aws eks update-kubeconfig --name eks-prod --region ap-northeast-2
            kubectl get nodes
            kubectl get pods -A | grep -v Running | grep -v Completed && exit 1 || true
```

### 1.4 Pod Identity IAM Configuration

```hcl
# terraform/iam/atlantis-role.tf
data "aws_iam_policy_document" "atlantis_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
    actions = ["sts:AssumeRole", "sts:TagSession"]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_eks_cluster.main.arn]
    }
  }
}

resource "aws_iam_role" "atlantis" {
  name               = "atlantis-terraform-role"
  assume_role_policy = data.aws_iam_policy_document.atlantis_assume_role.json
}

# Terraform State Access
resource "aws_iam_role_policy" "atlantis_s3" {
  name = "atlantis-s3-state"
  role = aws_iam_role.atlantis.id

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
          "arn:aws:s3:::my-terraform-state-bucket",
          "arn:aws:s3:::my-terraform-state-bucket/*"
        ]
      }
    ]
  })
}

# DynamoDB for State Locking
resource "aws_iam_role_policy" "atlantis_dynamodb" {
  name = "atlantis-dynamodb-lock"
  role = aws_iam_role.atlantis.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:ap-northeast-2:*:table/terraform-locks"
      }
    ]
  })
}

# Infrastructure Management Permissions
resource "aws_iam_role_policy_attachment" "atlantis_infra" {
  role       = aws_iam_role.atlantis.name
  policy_arn = aws_iam_policy.atlantis_infrastructure.arn
}

resource "aws_iam_policy" "atlantis_infrastructure" {
  name = "atlantis-infrastructure"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "VPCManagement"
        Effect = "Allow"
        Action = [
          "ec2:*Vpc*",
          "ec2:*Subnet*",
          "ec2:*RouteTable*",
          "ec2:*SecurityGroup*",
          "ec2:*NetworkAcl*",
          "ec2:*InternetGateway*",
          "ec2:*NatGateway*",
          "ec2:*ElasticIp*"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = ["ap-northeast-2", "us-east-1"]
          }
        }
      },
      {
        Sid    = "EKSManagement"
        Effect = "Allow"
        Action = [
          "eks:*"
        ]
        Resource = "*"
      },
      {
        Sid    = "IAMPassRole"
        Effect = "Allow"
        Action = [
          "iam:PassRole",
          "iam:GetRole"
        ]
        Resource = [
          "arn:aws:iam::*:role/eks-*",
          "arn:aws:iam::*:role/karpenter-*"
        ]
      }
    ]
  })
}

# Pod Identity Association
resource "aws_eks_pod_identity_association" "atlantis" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "atlantis"
  service_account = "atlantis"
  role_arn        = aws_iam_role.atlantis.arn
}
```

### 1.5 Multi-Repository Configuration

```yaml
# Server-side repo config for multi-repo setups
# ConfigMap: atlantis-server-config
repos:
  # Main infrastructure repository
  - id: github.com/myorg/infrastructure
    branch: main
    allowed_overrides:
      - workflow
      - apply_requirements
      - delete_source_branch_on_merge
    allow_custom_workflows: true
    pre_workflow_hooks:
      - run: |
          echo "Repository: $BASE_REPO_NAME"
          echo "PR: $PULL_NUM"
          echo "User: $PULL_AUTHOR"

  # Application team repositories
  - id: github.com/myorg/team-*
    branch: main
    allowed_overrides:
      - workflow
    allow_custom_workflows: false
    workflow: restricted
    apply_requirements:
      - approved
      - mergeable

  # Shared modules (no apply allowed)
  - id: github.com/myorg/terraform-modules
    branch: main
    allowed_overrides: []
    allow_custom_workflows: false
    workflow: plan-only

workflows:
  restricted:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - run: |
            # Validate resource limits
            RESOURCE_COUNT=$(terraform state list | wc -l)
            if [ "$RESOURCE_COUNT" -gt 50 ]; then
              echo "Error: Team repos limited to 50 resources. Current: $RESOURCE_COUNT"
              exit 1
            fi
        - apply

  plan-only:
    plan:
      steps:
        - init
        - plan
    apply:
      steps:
        - run: echo "Apply disabled for module repositories"
        - run: exit 1
```

### 1.6 Security Restrictions

```yaml
# atlantis-security-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: atlantis-security-config
  namespace: atlantis
data:
  # Blocked Terraform resources
  blocked_resources.txt: |
    aws_iam_user
    aws_iam_access_key
    aws_iam_user_policy
    aws_organizations_*
    aws_account

  # Pre-workflow hook script
  security-check.sh: |
    #!/bin/bash
    set -e

    BLOCKED_RESOURCES=$(cat /config/blocked_resources.txt)

    # Check for blocked resources in plan
    for resource in $BLOCKED_RESOURCES; do
      if grep -r "resource \"$resource\"" *.tf; then
        echo "ERROR: Blocked resource type detected: $resource"
        exit 1
      fi
    done

    # Check for hardcoded secrets
    if grep -rE "(aws_access_key|aws_secret_key|password\s*=)" *.tf; then
      echo "ERROR: Potential hardcoded secrets detected"
      exit 1
    fi

    # Validate required tags
    if ! grep -q "tags\s*=" *.tf; then
      echo "WARNING: No tags found. All resources should have tags."
    fi

    echo "Security checks passed"
```

### 1.7 Locking Mechanism

```yaml
# atlantis-lock-config.yaml
# Lock configuration for preventing concurrent applies

# ConfigMap for lock behavior
apiVersion: v1
kind: ConfigMap
metadata:
  name: atlantis-lock-config
  namespace: atlantis
data:
  lock_config.yaml: |
    # Lock timeout (how long a lock is held)
    lock_timeout: 3600  # 1 hour

    # Projects that share locks (cannot be applied simultaneously)
    lock_groups:
      - name: network-layer
        projects:
          - network-dev
          - network-prod
      - name: eks-cluster
        projects:
          - eks-dev
          - eks-prod

    # Priority queue for applies
    apply_priority:
      - network-*
      - eks-*
      - app-*
```

lock management のための PR command:

```bash
# View current locks
atlantis unlock

# Force unlock (admin only)
atlantis unlock --force

# Lock a specific project
atlantis lock -p eks-prod

# View lock status
atlantis locks
```

---

## 2. Terraform Cloud Integration

Terraform Cloud は、追加の enterprise feature を備えた、Atlantis に代わる managed な選択肢を提供します。

### 2.1 Workspace Organization

```hcl
# terraform/tfc-workspaces/main.tf
terraform {
  cloud {
    organization = "my-organization"
    workspaces {
      tags = ["eks", "infrastructure"]
    }
  }
}

# Workspace definitions
resource "tfe_workspace" "network" {
  name              = "eks-network"
  organization      = var.tfc_organization
  execution_mode    = "remote"
  terraform_version = "1.6.6"
  working_directory = "terraform/network"

  vcs_repo {
    identifier     = "myorg/infrastructure"
    branch         = "main"
    oauth_token_id = var.github_oauth_token_id
  }

  tag_names = ["network", "production"]

  # Auto-apply after successful plan
  auto_apply = false

  # Queue all runs
  queue_all_runs = true
}

resource "tfe_workspace" "eks_cluster" {
  name              = "eks-cluster"
  organization      = var.tfc_organization
  execution_mode    = "remote"
  terraform_version = "1.6.6"
  working_directory = "terraform/eks"

  vcs_repo {
    identifier     = "myorg/infrastructure"
    branch         = "main"
    oauth_token_id = var.github_oauth_token_id
  }

  tag_names = ["eks", "production"]
}

resource "tfe_workspace" "eks_addons" {
  name              = "eks-addons"
  organization      = var.tfc_organization
  execution_mode    = "remote"
  terraform_version = "1.6.6"
  working_directory = "terraform/addons"

  vcs_repo {
    identifier     = "myorg/infrastructure"
    branch         = "main"
    oauth_token_id = var.github_oauth_token_id
  }

  tag_names = ["eks", "addons", "production"]
}
```

### 2.2 Run Triggers for Downstream Automation

```hcl
# Run triggers - downstream workspace auto-trigger
resource "tfe_run_trigger" "eks_after_network" {
  workspace_id  = tfe_workspace.eks_cluster.id
  sourceable_id = tfe_workspace.network.id
}

resource "tfe_run_trigger" "addons_after_eks" {
  workspace_id  = tfe_workspace.eks_addons.id
  sourceable_id = tfe_workspace.eks_cluster.id
}

# Variable sets for shared configuration
resource "tfe_variable_set" "aws_credentials" {
  name         = "aws-credentials"
  organization = var.tfc_organization
  description  = "AWS credentials for all workspaces"
}

resource "tfe_variable" "aws_region" {
  key             = "AWS_REGION"
  value           = "ap-northeast-2"
  category        = "env"
  variable_set_id = tfe_variable_set.aws_credentials.id
}

# Attach variable set to workspaces
resource "tfe_workspace_variable_set" "network_aws" {
  workspace_id    = tfe_workspace.network.id
  variable_set_id = tfe_variable_set.aws_credentials.id
}

resource "tfe_workspace_variable_set" "eks_aws" {
  workspace_id    = tfe_workspace.eks_cluster.id
  variable_set_id = tfe_variable_set.aws_credentials.id
}
```

### 2.3 Sentinel Policies

```hcl
# sentinel/enforce-tags.sentinel
import "tfplan/v2" as tfplan

# Required tags for all resources
required_tags = ["Environment", "Project", "Owner", "CostCenter"]

# Find all resources with tags attribute
tagged_resources = filter tfplan.resource_changes as _, rc {
    rc.mode is "managed" and
    rc.change.after is not null and
    keys(rc.change.after) contains "tags"
}

# Check each resource has required tags
violations = []
for tagged_resources as address, rc {
    tags = rc.change.after.tags else {}
    for required_tags as tag {
        if tags[tag] is null {
            append(violations, {
                "address": address,
                "missing_tag": tag,
            })
        }
    }
}

main = rule {
    length(violations) is 0
}

# Output violations for debugging
print("Tag violations:", violations)
```

```hcl
# sentinel/restrict-instance-types.sentinel
import "tfplan/v2" as tfplan

# Allowed instance types by environment
allowed_instances = {
    "dev": ["t3.medium", "t3.large", "m5.large"],
    "prod": ["m5.large", "m5.xlarge", "m5.2xlarge", "r5.large", "r5.xlarge"],
}

# Find EC2 instances and EKS node groups
ec2_instances = filter tfplan.resource_changes as _, rc {
    rc.type is "aws_instance" and
    rc.mode is "managed" and
    rc.change.after is not null
}

eks_node_groups = filter tfplan.resource_changes as _, rc {
    rc.type is "aws_eks_node_group" and
    rc.mode is "managed" and
    rc.change.after is not null
}

# Determine environment from workspace name
param environment default "dev"

# Validate instance types
instance_violations = []
for ec2_instances as address, rc {
    instance_type = rc.change.after.instance_type
    if instance_type not in allowed_instances[environment] {
        append(instance_violations, {
            "address": address,
            "instance_type": instance_type,
            "allowed": allowed_instances[environment],
        })
    }
}

main = rule {
    length(instance_violations) is 0
}
```

```hcl
# sentinel/cost-limit.sentinel
import "tfplan/v2" as tfplan
import "decimal"

# Monthly cost limits per workspace
cost_limits = {
    "eks-network": 500,
    "eks-cluster": 5000,
    "eks-addons": 1000,
}

# Get cost estimate from Terraform Cloud
param cost_estimate

# Parse estimated monthly cost
estimated_monthly = decimal.new(cost_estimate.proposed_monthly_cost)
workspace_limit = decimal.new(cost_limits[tfplan.workspace.name] else 10000)

cost_exceeded = estimated_monthly.greater_than(workspace_limit)

main = rule {
    not cost_exceeded
}

# Soft policy - warn but don't block
soft_main = rule when cost_exceeded {
    print("WARNING: Estimated monthly cost", estimated_monthly, "exceeds limit", workspace_limit)
    true
}
```

### 2.4 Atlantis vs Terraform Cloud Comparison

| 機能 | Atlantis | Terraform Cloud |
|---------|----------|-----------------|
| **Hosting** | EKS 上の Self-hosted | Managed SaaS |
| **Cost** | Infrastructure のみ | User 単位の pricing |
| **VCS Integration** | GitHub, GitLab, Bitbucket | 同じ + Azure DevOps |
| **PR Automation** | Full | Full |
| **Policy as Code** | External (OPA, Conftest) | Native Sentinel |
| **Cost Estimation** | External tool が必要 | Built-in |
| **Private Registry** | External setup | Included |
| **Run Triggers** | Manual scripting | Native |
| **State Management** | External S3 + DynamoDB | Built-in |
| **Audit Logs** | CloudWatch integration | Built-in |
| **SSO/SAML** | 自分で設定 | Enterprise feature |
| **Concurrent Runs** | Pod resource による制限 | Plan-based limits |
| **Air-gapped** | Fully supported | Terraform Enterprise |

**推奨:**
- 完全な control が必要な場合、self-hosting の security requirement がある場合、または SaaS cost を最小化したい場合は **Atlantis** を使用します
- managed infrastructure が欲しい場合、native policy enforcement が必要な場合、または enterprise compliance feature が必要な場合は **Terraform Cloud** を使用します

---

## 3. FluxCD

FluxCD は Kubernetes-native primitive に重点を置いた GitOps automation を提供します。

### 3.1 ArgoCD vs FluxCD Comparison

| 機能 | ArgoCD | FluxCD |
|---------|--------|--------|
| **Architecture** | UI を備えた Monolithic | Modular controllers |
| **UI** | Built-in web UI | Optional Weave GitOps UI |
| **Multi-tenancy** | AppProject-based | Namespace-based |
| **Sync Method** | Pull-based | Pull-based |
| **Helm Support** | Native | HelmRelease CRD |
| **Kustomize** | Native | Kustomization CRD |
| **Image Automation** | Argo Image Updater | Built-in controllers |
| **Notifications** | Built-in | Notification controller |
| **Source Types** | Git, Helm, OCI | Git, Helm, S3, OCI |
| **CRD Complexity** | Application CRD | 複数の specialized CRD |
| **Learning Curve** | 低め (single CRD) | 高め (multiple CRD) |
| **Resource Usage** | 高め (UI, Redis) | 低め (minimal) |

**FluxCD を選ぶ場合:**
- 複数の controller による Kubernetes-native approach を好む
- built-in の image automation が必要
- minimal resource footprint を求める
- source として S3 が必要

### 3.2 FluxCD Installation

```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux with GitHub
flux bootstrap github \
  --owner=myorg \
  --repository=flux-config \
  --branch=main \
  --path=clusters/production \
  --personal=false \
  --components-extra=image-reflector-controller,image-automation-controller

# Verify installation
flux check
```

Bootstrap は次の structure を作成します:

```
flux-config/
├── clusters/
│   └── production/
│       ├── flux-system/
│       │   ├── gotk-components.yaml
│       │   ├── gotk-sync.yaml
│       │   └── kustomization.yaml
│       ├── infrastructure/
│       │   └── kustomization.yaml
│       └── apps/
│           └── kustomization.yaml
```

### 3.3 Source Controller Configuration

```yaml
# clusters/production/infrastructure/sources.yaml
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/myorg/infrastructure
  ref:
    branch: main
  secretRef:
    name: github-credentials
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: applications
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/myorg/applications
  ref:
    branch: main
  secretRef:
    name: github-credentials
---
# Helm Repository Source
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: bitnami
  namespace: flux-system
spec:
  interval: 30m
  url: https://charts.bitnami.com/bitnami
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: eks-charts
  namespace: flux-system
spec:
  interval: 30m
  url: https://aws.github.io/eks-charts
---
# S3 Bucket Source
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: Bucket
metadata:
  name: config-bucket
  namespace: flux-system
spec:
  interval: 5m
  provider: aws
  bucketName: my-flux-config-bucket
  region: ap-northeast-2
  secretRef:
    name: aws-credentials
```

### 3.4 HelmRelease CRD

```yaml
# clusters/production/infrastructure/aws-load-balancer-controller.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: aws-load-balancer-controller
  namespace: kube-system
spec:
  interval: 30m
  chart:
    spec:
      chart: aws-load-balancer-controller
      version: "1.7.*"
      sourceRef:
        kind: HelmRepository
        name: eks-charts
        namespace: flux-system
      interval: 12h

  values:
    clusterName: production-cluster
    serviceAccount:
      create: true
      name: aws-load-balancer-controller
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/aws-load-balancer-controller

    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 256Mi

  # Upgrade configuration
  upgrade:
    remediation:
      retries: 3
      remediateLastFailure: true

  # Rollback configuration
  rollback:
    cleanupOnFail: true
    timeout: 5m

  # Test configuration
  test:
    enable: true
    timeout: 5m

---
# Application HelmRelease with values from ConfigMap
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: my-application
  namespace: production
spec:
  interval: 5m
  chart:
    spec:
      chart: ./charts/my-application
      sourceRef:
        kind: GitRepository
        name: applications
        namespace: flux-system

  valuesFrom:
    - kind: ConfigMap
      name: my-application-values
      valuesKey: values.yaml
    - kind: Secret
      name: my-application-secrets
      valuesKey: secrets.yaml

  values:
    replicaCount: 3
    image:
      repository: myregistry.ecr.ap-northeast-2.amazonaws.com/my-app
      tag: v1.0.0  # Will be updated by Image Automation

  dependsOn:
    - name: aws-load-balancer-controller
      namespace: kube-system
```

### 3.5 Kustomization for Environment Overlays

```yaml
# clusters/production/apps/kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: applications
  path: ./apps/overlays/production
  prune: true
  targetNamespace: production

  # Health checks
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: my-application
      namespace: production

  # Timeout for health checks
  timeout: 5m

  # Patches for production
  patches:
    - patch: |
        - op: replace
          path: /spec/replicas
          value: 5
      target:
        kind: Deployment
        name: my-application

  # Substitute variables
  postBuild:
    substitute:
      ENVIRONMENT: production
      CLUSTER_NAME: production-cluster
    substituteFrom:
      - kind: ConfigMap
        name: cluster-config
      - kind: Secret
        name: cluster-secrets

---
# Staging environment
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps-staging
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: applications
  path: ./apps/overlays/staging
  prune: true
  targetNamespace: staging

  postBuild:
    substitute:
      ENVIRONMENT: staging
      CLUSTER_NAME: staging-cluster
```

### 3.6 Image Automation Controller

```yaml
# clusters/production/image-automation/image-repository.yaml
---
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: my-application
  namespace: flux-system
spec:
  image: myregistry.ecr.ap-northeast-2.amazonaws.com/my-app
  interval: 1m
  secretRef:
    name: ecr-credentials
  provider: aws
---
# Image Policy - select latest semver
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: my-application
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: my-application
  policy:
    semver:
      range: ">=1.0.0 <2.0.0"
---
# Alternative: Latest tag matching pattern
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImagePolicy
metadata:
  name: my-application-latest
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: my-application
  filterTags:
    pattern: '^main-[a-f0-9]+-(?P<ts>[0-9]+)'
    extract: '$ts'
  policy:
    numerical:
      order: asc
---
# Image Update Automation
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: my-application
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: applications

  git:
    checkout:
      ref:
        branch: main
    commit:
      author:
        email: flux@example.com
        name: Flux Bot
      messageTemplate: |
        Automated image update

        Automation: {{ .AutomationObject }}

        Files:
        {{ range $filename, $_ := .Changed.FileChanges -}}
        - {{ $filename }}
        {{ end -}}

        Objects:
        {{ range $resource, $changes := .Changed.Objects -}}
        - {{ $resource.Kind }} {{ $resource.Name }}
          {{- range $_, $change := $changes }}
            - {{ $change.OldValue }} -> {{ $change.NewValue }}
          {{- end }}
        {{ end -}}
    push:
      branch: main

  update:
    path: ./apps
    strategy: Setters
```

automation のために manifest 内の image に印を付けます:

```yaml
# apps/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-application
spec:
  template:
    spec:
      containers:
        - name: app
          image: myregistry.ecr.ap-northeast-2.amazonaws.com/my-app:v1.0.0 # {"$imagepolicy": "flux-system:my-application"}
```

### 3.7 Notification Controller

```yaml
# clusters/production/notifications/slack.yaml
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: slack
  namespace: flux-system
spec:
  type: slack
  channel: "#gitops-notifications"
  secretRef:
    name: slack-webhook
---
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
    - kind: GitRepository
      name: "*"
    - kind: Kustomization
      name: "*"
    - kind: HelmRelease
      name: "*"
  summary: "Flux reconciliation failed"
---
# Info-level notifications for successful deployments
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: deployment-notifications
  namespace: flux-system
spec:
  providerRef:
    name: slack
  eventSeverity: info
  eventSources:
    - kind: HelmRelease
      name: "*"
      namespace: production
  exclusionList:
    - ".*upgrade.*in progress.*"
  summary: "Deployment update"
---
# Secret for Slack webhook
apiVersion: v1
kind: Secret
metadata:
  name: slack-webhook
  namespace: flux-system
type: Opaque
stringData:
  address: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

---

## 4. AIOps Strategy

AIOps は artificial intelligence と operations を組み合わせ、decision-making と response を自動化します。

### 4.1 LLM-Based PR Review

```yaml
# .github/workflows/ai-review.yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed files
        id: changed
        run: |
          echo "files=$(git diff --name-only origin/${{ github.base_ref }}...HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT

      - name: AI Review with Claude
        uses: anthropics/claude-code-review@v1
        with:
          api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          files: ${{ steps.changed.outputs.files }}
          review-type: security,performance,best-practices

      - name: AI Review for Terraform
        if: contains(steps.changed.outputs.files, '.tf')
        run: |
          # Custom Terraform review prompt
          cat > review-prompt.txt << 'EOF'
          Review the following Terraform changes for:
          1. Security issues (overly permissive IAM, public resources)
          2. Cost implications (instance sizes, storage)
          3. Best practices (naming, tagging, modularity)
          4. Potential blast radius

          Provide specific line-by-line feedback.
          EOF

          # Call Claude API
          curl -X POST https://api.anthropic.com/v1/messages \
            -H "x-api-key: ${{ secrets.ANTHROPIC_API_KEY }}" \
            -H "content-type: application/json" \
            -H "anthropic-version: 2023-06-01" \
            -d @- << EOF > review-output.json
          {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{
              "role": "user",
              "content": "$(cat review-prompt.txt)\n\nChanges:\n$(git diff origin/${{ github.base_ref }}...HEAD -- '*.tf')"
            }]
          }
          EOF

          # Post review as PR comment
          REVIEW=$(jq -r '.content[0].text' review-output.json)
          gh pr comment ${{ github.event.pull_request.number }} --body "## AI Terraform Review\n\n${REVIEW}"
        env:
          GH_TOKEN: ${{ github.token }}
```

### 4.2 Metrics-Based YAML Auto-Modification

```python
#!/usr/bin/env python3
# scripts/auto-tune-hpa.py
"""
Automatically adjusts HPA targets based on historical metrics.
Runs as a CronJob in the cluster.
"""

import os
import yaml
import requests
from datetime import datetime, timedelta
from kubernetes import client, config

PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL', 'http://prometheus:9090')
ADJUSTMENT_THRESHOLD = 0.15  # 15% deviation triggers adjustment
MIN_TARGET = 50
MAX_TARGET = 90

def get_average_utilization(namespace: str, deployment: str, metric: str, hours: int = 24) -> float:
    """Query Prometheus for average utilization over time period."""

    if metric == 'cpu':
        query = f'''
        avg(
          rate(container_cpu_usage_seconds_total{{
            namespace="{namespace}",
            pod=~"{deployment}-.*"
          }}[5m])
        ) /
        avg(
          kube_pod_container_resource_requests{{
            namespace="{namespace}",
            pod=~"{deployment}-.*",
            resource="cpu"
          }}
        ) * 100
        '''
    else:  # memory
        query = f'''
        avg(
          container_memory_working_set_bytes{{
            namespace="{namespace}",
            pod=~"{deployment}-.*"
          }}
        ) /
        avg(
          kube_pod_container_resource_requests{{
            namespace="{namespace}",
            pod=~"{deployment}-.*",
            resource="memory"
          }}
        ) * 100
        '''

    end = datetime.now()
    start = end - timedelta(hours=hours)

    response = requests.get(
        f'{PROMETHEUS_URL}/api/v1/query_range',
        params={
            'query': query,
            'start': start.isoformat(),
            'end': end.isoformat(),
            'step': '1h'
        }
    )

    data = response.json()
    if data['status'] == 'success' and data['data']['result']:
        values = [float(v[1]) for v in data['data']['result'][0]['values']]
        return sum(values) / len(values)
    return -1


def calculate_optimal_target(current_target: int, avg_utilization: float) -> int:
    """Calculate optimal HPA target based on utilization patterns."""

    if avg_utilization < 0:
        return current_target

    # If utilization is significantly below target, lower the target
    # If utilization is significantly above target, raise the target
    deviation = (avg_utilization - current_target) / current_target

    if abs(deviation) < ADJUSTMENT_THRESHOLD:
        return current_target

    # Adjust target to maintain ~75% of actual utilization as headroom
    new_target = int(avg_utilization * 0.75)

    # Apply bounds
    new_target = max(MIN_TARGET, min(MAX_TARGET, new_target))

    return new_target


def update_hpa_target(namespace: str, hpa_name: str, new_cpu_target: int, new_memory_target: int):
    """Update HPA with new target values."""

    config.load_incluster_config()
    api = client.AutoscalingV2Api()

    hpa = api.read_namespaced_horizontal_pod_autoscaler(hpa_name, namespace)

    updated = False
    for metric in hpa.spec.metrics:
        if metric.type == 'Resource':
            if metric.resource.name == 'cpu' and metric.resource.target.average_utilization != new_cpu_target:
                metric.resource.target.average_utilization = new_cpu_target
                updated = True
            elif metric.resource.name == 'memory' and metric.resource.target.average_utilization != new_memory_target:
                metric.resource.target.average_utilization = new_memory_target
                updated = True

    if updated:
        api.patch_namespaced_horizontal_pod_autoscaler(hpa_name, namespace, hpa)
        print(f"Updated HPA {namespace}/{hpa_name}: CPU={new_cpu_target}%, Memory={new_memory_target}%")

        # Create annotation for audit
        hpa.metadata.annotations = hpa.metadata.annotations or {}
        hpa.metadata.annotations['aiops.last-tuned'] = datetime.now().isoformat()
        hpa.metadata.annotations['aiops.cpu-target'] = str(new_cpu_target)
        hpa.metadata.annotations['aiops.memory-target'] = str(new_memory_target)
        api.patch_namespaced_horizontal_pod_autoscaler(hpa_name, namespace, hpa)


def main():
    # List of HPAs to auto-tune
    hpas_to_tune = [
        {'namespace': 'production', 'hpa': 'api-server', 'deployment': 'api-server'},
        {'namespace': 'production', 'hpa': 'web-frontend', 'deployment': 'web-frontend'},
    ]

    for item in hpas_to_tune:
        namespace = item['namespace']
        deployment = item['deployment']
        hpa_name = item['hpa']

        # Get current HPA configuration
        config.load_incluster_config()
        api = client.AutoscalingV2Api()
        hpa = api.read_namespaced_horizontal_pod_autoscaler(hpa_name, namespace)

        current_cpu_target = 70
        current_memory_target = 80

        for metric in hpa.spec.metrics:
            if metric.type == 'Resource':
                if metric.resource.name == 'cpu':
                    current_cpu_target = metric.resource.target.average_utilization
                elif metric.resource.name == 'memory':
                    current_memory_target = metric.resource.target.average_utilization

        # Get average utilization
        avg_cpu = get_average_utilization(namespace, deployment, 'cpu')
        avg_memory = get_average_utilization(namespace, deployment, 'memory')

        # Calculate optimal targets
        new_cpu_target = calculate_optimal_target(current_cpu_target, avg_cpu)
        new_memory_target = calculate_optimal_target(current_memory_target, avg_memory)

        # Update if changed
        if new_cpu_target != current_cpu_target or new_memory_target != current_memory_target:
            update_hpa_target(namespace, hpa_name, new_cpu_target, new_memory_target)


if __name__ == '__main__':
    main()
```

### 4.3 Traffic Anomaly Detection

```yaml
# aiops/anomaly-detector.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traffic-anomaly-detector
  namespace: aiops
spec:
  replicas: 1
  selector:
    matchLabels:
      app: anomaly-detector
  template:
    metadata:
      labels:
        app: anomaly-detector
    spec:
      serviceAccountName: anomaly-detector
      containers:
        - name: detector
          image: myregistry.ecr.ap-northeast-2.amazonaws.com/anomaly-detector:v1.0
          env:
            - name: PROMETHEUS_URL
              value: "http://prometheus-server.monitoring:80"
            - name: SLACK_WEBHOOK_URL
              valueFrom:
                secretKeyRef:
                  name: slack-webhook
                  key: url
            - name: NLB_ARN
              value: "arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:loadbalancer/net/my-nlb/50dc6c495c0c9188"
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
```

```python
#!/usr/bin/env python3
# anomaly-detector/detector.py
"""
Detects traffic anomalies and automatically adjusts NLB target weights.
"""

import os
import time
import numpy as np
import requests
import boto3
from dataclasses import dataclass
from typing import List, Optional

PROMETHEUS_URL = os.environ['PROMETHEUS_URL']
NLB_ARN = os.environ['NLB_ARN']
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    metric_name: str
    current_value: float
    expected_range: tuple
    action_taken: Optional[str] = None


def get_metrics(query: str, duration: str = '1h') -> List[float]:
    """Fetch metrics from Prometheus."""
    response = requests.get(
        f'{PROMETHEUS_URL}/api/v1/query_range',
        params={
            'query': query,
            'start': f'now()-{duration}',
            'end': 'now()',
            'step': '1m'
        }
    )
    data = response.json()
    if data['status'] == 'success' and data['data']['result']:
        return [float(v[1]) for v in data['data']['result'][0]['values']]
    return []


def detect_anomaly(values: List[float], current: float, std_multiplier: float = 3) -> AnomalyResult:
    """Simple anomaly detection using standard deviation."""
    if not values:
        return AnomalyResult(False, 0, '', current, (0, 0))

    mean = np.mean(values)
    std = np.std(values)

    lower_bound = mean - (std_multiplier * std)
    upper_bound = mean + (std_multiplier * std)

    is_anomaly = current < lower_bound or current > upper_bound
    score = abs(current - mean) / std if std > 0 else 0

    return AnomalyResult(
        is_anomaly=is_anomaly,
        score=score,
        metric_name='',
        current_value=current,
        expected_range=(lower_bound, upper_bound)
    )


def adjust_nlb_weights(target_group_arns: List[str], weights: List[int]):
    """Adjust NLB target group weights for traffic shifting."""
    elbv2 = boto3.client('elbv2')

    # Get current listener
    listeners = elbv2.describe_listeners(LoadBalancerArn=NLB_ARN)['Listeners']

    for listener in listeners:
        # Create weighted forward action
        actions = [{
            'Type': 'forward',
            'ForwardConfig': {
                'TargetGroups': [
                    {'TargetGroupArn': tg, 'Weight': w}
                    for tg, w in zip(target_group_arns, weights)
                ],
                'TargetGroupStickinessConfig': {
                    'Enabled': False
                }
            }
        }]

        elbv2.modify_listener(
            ListenerArn=listener['ListenerArn'],
            DefaultActions=actions
        )


def send_slack_notification(message: str, severity: str = 'warning'):
    """Send notification to Slack."""
    if not SLACK_WEBHOOK_URL:
        return

    color = '#ff0000' if severity == 'critical' else '#ffcc00'

    requests.post(SLACK_WEBHOOK_URL, json={
        'attachments': [{
            'color': color,
            'title': 'Traffic Anomaly Detected',
            'text': message,
            'footer': 'AIOps Anomaly Detector'
        }]
    })


def main():
    # Metrics to monitor
    metrics = {
        'error_rate': 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
        'latency_p99': 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))',
        'request_rate': 'sum(rate(http_requests_total[5m]))'
    }

    # Target groups for traffic shifting
    target_groups = {
        'primary': 'arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/primary/xxx',
        'canary': 'arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/canary/yyy'
    }

    while True:
        anomalies = []

        for metric_name, query in metrics.items():
            # Get historical data
            historical = get_metrics(query, duration='24h')

            # Get current value
            current_response = requests.get(
                f'{PROMETHEUS_URL}/api/v1/query',
                params={'query': query}
            )
            current_data = current_response.json()

            if current_data['status'] == 'success' and current_data['data']['result']:
                current_value = float(current_data['data']['result'][0]['value'][1])

                result = detect_anomaly(historical, current_value)
                result.metric_name = metric_name

                if result.is_anomaly:
                    anomalies.append(result)

        # Take action on anomalies
        if anomalies:
            critical_anomalies = [a for a in anomalies if a.score > 5]

            if critical_anomalies:
                # Shift traffic away from canary
                adjust_nlb_weights(
                    [target_groups['primary'], target_groups['canary']],
                    [100, 0]
                )

                message = f"Critical anomalies detected! Traffic shifted to primary.\n"
                for a in critical_anomalies:
                    message += f"- {a.metric_name}: {a.current_value:.2f} (expected: {a.expected_range[0]:.2f} - {a.expected_range[1]:.2f})\n"

                send_slack_notification(message, severity='critical')
            else:
                message = f"Anomalies detected:\n"
                for a in anomalies:
                    message += f"- {a.metric_name}: {a.current_value:.2f} (score: {a.score:.2f})\n"

                send_slack_notification(message, severity='warning')

        time.sleep(60)  # Check every minute


if __name__ == '__main__':
    main()
```

### 4.4 Progressive Delivery with Argo Rollouts

```yaml
# rollouts/api-server-rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 10
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
        - name: api-server
          image: myregistry.ecr.ap-northeast-2.amazonaws.com/api-server:v1.0.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi

  strategy:
    canary:
      # Traffic routing
      canaryService: api-server-canary
      stableService: api-server-stable

      trafficRouting:
        nginx:
          stableIngress: api-server-ingress

      # Progressive traffic increase
      steps:
        - setWeight: 5
        - pause: {duration: 5m}
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency
            args:
              - name: service-name
                value: api-server-canary
        - setWeight: 20
        - pause: {duration: 10m}
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency
        - setWeight: 50
        - pause: {duration: 15m}
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency
              - templateName: resource-usage
        - setWeight: 80
        - pause: {duration: 10m}
        - setWeight: 100

      # Anti-affinity for canary pods
      antiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution: {}

      # Auto rollback
      abortScaleDownDelaySeconds: 30

---
# Analysis Templates
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      count: 5
      successCondition: result[0] >= 0.99
      failureCondition: result[0] < 0.95
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}", status!~"5.."}[5m])) /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency
  namespace: production
spec:
  args:
    - name: service-name
  metrics:
    - name: latency-p99
      interval: 1m
      count: 5
      successCondition: result[0] <= 0.5
      failureCondition: result[0] > 1.0
      failureLimit: 2
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            histogram_quantile(0.99,
              sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[5m])) by (le)
            )

---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: resource-usage
  namespace: production
spec:
  metrics:
    - name: cpu-usage
      interval: 2m
      count: 3
      successCondition: result[0] <= 0.8
      failureCondition: result[0] > 0.95
      provider:
        prometheus:
          address: http://prometheus-server.monitoring:80
          query: |
            avg(
              rate(container_cpu_usage_seconds_total{
                namespace="production",
                pod=~"api-server-.*"
              }[5m])
            ) /
            avg(
              kube_pod_container_resource_limits{
                namespace="production",
                pod=~"api-server-.*",
                resource="cpu"
              }
            )
```

### 4.5 Production Guardrails and Human-in-the-Loop

```yaml
# guardrails/production-policy.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiops-guardrails
  namespace: aiops
data:
  policy.yaml: |
    # AIOps Guardrails Configuration

    # Auto-remediation limits
    auto_remediation:
      enabled: true
      max_actions_per_hour: 10
      cooldown_between_actions: 5m

      # Actions that can be automated
      allowed_actions:
        - scale_up_replicas
        - scale_down_replicas
        - adjust_hpa_target
        - shift_traffic_weight
        - restart_unhealthy_pod

      # Actions requiring approval
      requires_approval:
        - scale_to_zero
        - delete_resource
        - modify_pdb
        - change_resource_limits
        - rollback_deployment

    # Thresholds for auto-action
    thresholds:
      # Don't auto-scale below/above these limits
      min_replicas: 2
      max_replicas: 100

      # Don't adjust HPA beyond these
      hpa_target_min: 40
      hpa_target_max: 90

      # Traffic shift limits
      max_traffic_shift_percent: 50
      min_traffic_to_stable: 20

    # Human approval workflow
    approval:
      # Slack channel for approval requests
      slack_channel: "#aiops-approvals"

      # Timeout for approval
      timeout: 30m

      # Required approvers
      approvers:
        - "@oncall-sre"
        - "@platform-team"

      # Auto-approve in non-prod
      auto_approve_environments:
        - dev
        - staging

    # Rollback triggers
    auto_rollback:
      enabled: true
      triggers:
        - metric: error_rate
          threshold: 5  # percent
          duration: 2m
        - metric: latency_p99
          threshold: 2  # seconds
          duration: 3m
        - metric: availability
          threshold: 99  # percent
          duration: 5m
```

```python
# guardrails/approval-controller.py
"""
Human-in-the-loop approval controller for AIOps actions.
"""

import os
import time
import json
import requests
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']

@dataclass
class ApprovalRequest:
    id: str
    action: str
    resource: str
    namespace: str
    reason: str
    requester: str
    created_at: datetime
    expires_at: datetime
    status: str = 'pending'  # pending, approved, rejected, expired
    approver: Optional[str] = None


def request_approval(action: str, resource: str, namespace: str, reason: str) -> ApprovalRequest:
    """Send approval request to Slack and wait for response."""

    request = ApprovalRequest(
        id=f"aiops-{int(time.time())}",
        action=action,
        resource=resource,
        namespace=namespace,
        reason=reason,
        requester='aiops-system',
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=30)
    )

    # Send Slack message with approval buttons
    message = {
        'channel': '#aiops-approvals',
        'text': f'AIOps Action Approval Required',
        'attachments': [{
            'color': '#ffcc00',
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f'*Action Required:* {action}\n*Resource:* {namespace}/{resource}\n*Reason:* {reason}'
                    }
                },
                {
                    'type': 'actions',
                    'block_id': request.id,
                    'elements': [
                        {
                            'type': 'button',
                            'text': {'type': 'plain_text', 'text': 'Approve'},
                            'style': 'primary',
                            'action_id': 'approve',
                            'value': json.dumps({'request_id': request.id})
                        },
                        {
                            'type': 'button',
                            'text': {'type': 'plain_text', 'text': 'Reject'},
                            'style': 'danger',
                            'action_id': 'reject',
                            'value': json.dumps({'request_id': request.id})
                        }
                    ]
                },
                {
                    'type': 'context',
                    'elements': [{
                        'type': 'mrkdwn',
                        'text': f'Request ID: {request.id} | Expires: {request.expires_at.isoformat()}'
                    }]
                }
            ]
        }]
    }

    requests.post(
        'https://slack.com/api/chat.postMessage',
        headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'},
        json=message
    )

    return request


def check_guardrails(action: str, config: dict) -> tuple[bool, str]:
    """Check if action is allowed by guardrails."""

    guardrails = config.get('auto_remediation', {})

    # Check if action requires approval
    if action in guardrails.get('requires_approval', []):
        return False, 'Action requires manual approval'

    # Check if action is allowed
    if action not in guardrails.get('allowed_actions', []):
        return False, f'Action {action} is not in allowed list'

    # Check rate limits
    # (would check action history here)

    return True, 'OK'


def execute_with_guardrails(action: str, resource: str, namespace: str,
                            reason: str, config: dict) -> bool:
    """Execute action with guardrail checks and optional approval."""

    allowed, message = check_guardrails(action, config)

    if allowed:
        # Execute immediately
        print(f"Executing {action} on {namespace}/{resource}: {reason}")
        return True

    if 'requires manual approval' in message:
        # Request approval
        request = request_approval(action, resource, namespace, reason)

        # Wait for approval (in production, this would be async)
        timeout = datetime.now() + timedelta(minutes=30)
        while datetime.now() < timeout:
            # Check approval status (would query database/cache)
            if request.status == 'approved':
                print(f"Approved by {request.approver}. Executing {action}.")
                return True
            elif request.status == 'rejected':
                print(f"Rejected by {request.approver}. Skipping {action}.")
                return False
            time.sleep(30)

        print(f"Approval timeout for {action}. Skipping.")
        return False

    print(f"Guardrail blocked: {message}")
    return False
```

### 4.6 AIOps Limitations and Best Practices

**現在の制限事項:**

1. **Context Understanding**: LLM は人間が理解する domain-specific context を見落とすことがあります
2. **Cascading Failures**: 自動化された action は、適切に制限されていない場合、cascading issue を引き起こす可能性があります
3. **Novel Situations**: historical data で訓練された ML model は、前例のない scenario では失敗する可能性があります
4. **Latency**: LLM inference は decision loop に latency を追加します
5. **Cost**: 頻繁な LLM call は高コストになる可能性があります

**Best Practices:**

```yaml
# aiops/best-practices-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aiops-best-practices
  namespace: aiops
data:
  guidelines.md: |
    # AIOps Best Practices

    ## 1. Start with Observability
    - Ensure comprehensive metrics collection before automation
    - Establish baselines for normal behavior
    - Define clear SLOs and error budgets

    ## 2. Progressive Automation
    - Level 0: Alert only (no action)
    - Level 1: Suggest action (human approves)
    - Level 2: Auto-execute with notification
    - Level 3: Full automation with audit

    ## 3. Guardrails First
    - Always implement rate limits
    - Define maximum blast radius
    - Require approval for destructive actions
    - Maintain manual override capability

    ## 4. Testing in Non-Production
    - Chaos engineering to validate responses
    - Synthetic anomaly injection
    - Rollback testing

    ## 5. Continuous Learning
    - Review auto-actions weekly
    - Update models with new patterns
    - Incorporate human feedback

    ## 6. Transparency
    - Log all automated decisions
    - Explain reasoning in notifications
    - Provide audit trail for compliance
```

---

## まとめ

| Tool | Use Case | Key Feature |
|------|----------|-------------|
| **Atlantis** | Terraform PR automation | Self-hosted, full control |
| **Terraform Cloud** | Managed Terraform | Sentinel policies, cost estimation |
| **FluxCD** | Kubernetes の GitOps | Image automation, modular design |
| **AIOps** | Intelligent automation | Anomaly detection, auto-remediation |

**推奨 Architecture:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitOps Architecture                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Infrastructure         Application          Intelligence          │
│  ┌─────────────┐       ┌─────────────┐      ┌─────────────┐       │
│  │  Atlantis   │       │   FluxCD    │      │   AIOps     │       │
│  │  or TFC     │       │  or ArgoCD  │      │  Controller │       │
│  └──────┬──────┘       └──────┬──────┘      └──────┬──────┘       │
│         │                     │                     │              │
│         ▼                     ▼                     ▼              │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes Cluster                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │  │
│  │  │   VPC   │  │   EKS   │  │  Apps   │  │  Argo Rollouts  │ │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

< [前へ: ArgoCD Multi-Cluster](./04-gitops-multi-cluster.md) | [目次](./README.md) | [次へ: Scaling Strategies](./06-scaling-strategies.md) >
