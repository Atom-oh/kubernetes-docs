# EKS Security Best Practices

> **Supported Versions**: Amazon EKS 1.31, 1.32, 1.33
> **Last Updated**: February 21, 2026

This document covers security best practices for Amazon EKS environments. Learn how to securely operate EKS clusters from IAM integration to network security and runtime protection.

## Table of Contents

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [Control Plane Logging](#control-plane-logging)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [Cluster Encryption](#cluster-encryption)
10. [Node Security](#node-security)
11. [Private Clusters](#private-clusters)
12. [Multi-tenancy Patterns](#multi-tenancy-patterns)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA Overview

IRSA (IAM Roles for Service Accounts) associates IAM roles with Kubernetes ServiceAccounts, enabling Pods to securely access AWS services.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           IRSA Architecture                              │
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

### IRSA Setup

```bash
# 1. Create OIDC Provider (once per cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. Create IAM policy
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

# 3. Create IAM ServiceAccount
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### Using IRSA

```yaml
# Verify ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: production
  annotations:
    # IRSA role ARN
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eksctl-my-cluster-s3-reader-sa
---
# Use ServiceAccount in Pod
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
    # AWS SDK automatically uses IRSA token
```

### IRSA Trust Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### IRSA Best Practices

```yaml
# 1. Principle of least privilege
# Grant only minimum required permissions to each ServiceAccount

# 2. Separate ServiceAccounts per namespace
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

### Pod Identity Overview

EKS Pod Identity is a successor to IRSA, providing simpler configuration and enhanced security.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      EKS Pod Identity Architecture                       │
│                                                                         │
│  ┌─────────────┐         ┌─────────────────┐         ┌──────────────┐  │
│  │   EKS Pod   │────────▶│  Pod Identity   │────────▶│   AWS IAM    │  │
│  │             │         │     Agent       │         │    Role      │  │
│  │ ServiceAcc  │         │  (DaemonSet)    │         │              │  │
│  └─────────────┘         └─────────────────┘         └──────────────┘  │
│                                                                         │
│  Benefits:                                                              │
│  • No OIDC Provider setup required                                      │
│  • Easy role reuse                                                      │
│  • Enhanced audit logging                                               │
│  • Session tags support                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pod Identity Setup

```bash
# 1. Install Pod Identity Agent addon
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent \
    --addon-version v1.3.0-eksbuild.1

# 2. Create IAM role (with Pod Identity trust policy)
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

# 3. Attach policy
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Create Pod Identity Association
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Using Pod Identity

```yaml
# ServiceAccount (no annotation needed)
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
    # AWS SDK automatically uses Pod Identity
```

### IRSA vs Pod Identity Comparison

| Feature | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **Setup Complexity** | OIDC Provider required | Simple (API call) |
| **Trust Policy** | OIDC conditions required | Simple service principal |
| **Role Reuse** | Per-cluster modification needed | Reuse across clusters |
| **Audit Logging** | CloudTrail (SA level) | CloudTrail (Pod level) |
| **Session Tags** | Not supported | Supported |
| **Recommended** | Existing environments | New environments |

---

## Security Groups for Pods

### Overview

Security Groups for Pods applies VPC Security Groups directly to Pods, providing network-level isolation.

### Prerequisites

```bash
# Check VPC CNI version (v1.7.7+)
kubectl describe daemonset aws-node -n kube-system | grep Image

# Enable Security Groups for Pods
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Add policy to node IAM role
aws iam attach-role-policy \
    --role-name <node-role-name> \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

### SecurityGroupPolicy Configuration

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # Target Pod selection
  podSelector:
    matchLabels:
      app: database
  # Security Groups to apply
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # Database SG
      - sg-0987654321fedcba0  # Common monitoring SG
```

### Security Group Configuration with Terraform

```hcl
# Security Group for database Pods
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for database pods"

  # PostgreSQL access (from app pods only)
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_pods.id]
    description     = "PostgreSQL from app pods"
  }

  # Monitoring access
  ingress {
    from_port       = 9187
    to_port         = 9187
    protocol        = "tcp"
    security_groups = [aws_security_group.monitoring.id]
    description     = "Postgres exporter metrics"
  }

  # Replication traffic
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

## VPC Endpoints

### VPC Endpoints for Private EKS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EKS VPC Endpoint Configuration                        │
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

### Terraform VPC Endpoint Setup

```hcl
# Interface endpoints
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

# Gateway endpoints (S3, DynamoDB)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = module.vpc.private_route_table_ids

  tags = {
    Name = "vpce-s3"
  }
}

# Security Group for VPC endpoints
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

## Control Plane Logging

### EKS Control Plane Log Types

| Log Type | Description | Use Case |
|----------|-------------|----------|
| **api** | Kubernetes API server logs | API call tracing, troubleshooting |
| **audit** | Kubernetes audit logs | Security auditing, compliance |
| **authenticator** | AWS IAM authenticator logs | Authentication debugging |
| **controllerManager** | Controller manager logs | Controller behavior tracking |
| **scheduler** | Scheduler logs | Pod scheduling troubleshooting |

### Enabling Logging

```bash
# Enable logging with AWS CLI
aws eks update-cluster-config \
    --name my-cluster \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

```hcl
# Terraform logging configuration
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

### CloudWatch Logs Insights Queries

```sql
-- Find failed authentication attempts
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error/
| sort @timestamp desc
| limit 100

-- Track API calls for specific user
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "admin"
| sort @timestamp desc
| limit 50

-- Permission denied requests
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100

-- Secret access audit
fields @timestamp, user.username, verb, requestURI
| filter @logStream like /audit/
| filter requestURI like /secrets/
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection

### GuardDuty EKS Protection Overview

Amazon GuardDuty EKS Protection detects malicious activity and anomalous behavior in EKS clusters.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GuardDuty EKS Protection                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Detection Areas                               │   │
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
│  │              │  Threat Detection     │                         │   │
│  │              └───────────┬───────────┘                         │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │              ┌───────────────────────┐                         │   │
│  │              │      Findings         │                         │   │
│  │              │  (Security Events)    │                         │   │
│  │              └───────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Enabling GuardDuty

```bash
# Enable GuardDuty
aws guardduty create-detector --enable

# Enable EKS Protection
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

### GuardDuty EKS Finding Types

| Finding Type | Description | Severity |
|-------------|-------------|----------|
| `Kubernetes:MaliciousIPCaller.Custom` | API call from known malicious IP | High |
| `Kubernetes:SuccessfulAnonymousAccess` | Successful API call by anonymous user | Medium |
| `Kubernetes:PrivilegedContainer` | Privileged container creation | Medium |
| `Kubernetes:AnomalousBehavior.PermissionChecked` | Anomalous permission check | Low |
| `Runtime:Cryptocurrency.CoinMiner` | Cryptocurrency mining activity | High |
| `Runtime:ReverseShell` | Reverse shell connection | Critical |
| `Runtime:Execution.Suspicious` | Suspicious process execution | Medium |

### Automated Finding Response

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
                  # Auto-response: Pod isolation
                  eks = boto3.client('eks')
                  # Additional response logic...

              return {'statusCode': 200}
```

---

## Amazon Inspector

### Inspector Container Image Scanning

```bash
# Enable ECR enhanced scanning
aws ecr put-registry-scanning-configuration \
    --scan-type ENHANCED \
    --rules '[
        {
            "repositoryFilters": [{"filter": "*", "filterType": "WILDCARD"}],
            "scanFrequency": "CONTINUOUS_SCAN"
        }
    ]'

# Get scan results
aws ecr describe-image-scan-findings \
    --repository-name my-app \
    --image-id imageTag=latest
```

### Inspector and CI/CD Integration

```yaml
# GitHub Actions example
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
          aws-region: us-east-1

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        run: |
          docker build -t $ECR_REGISTRY/my-app:${{ github.sha }} .
          docker push $ECR_REGISTRY/my-app:${{ github.sha }}

      - name: Wait for Inspector scan
        run: |
          sleep 60  # Wait for Inspector to complete scan

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

### Running kube-bench

```bash
# Run kube-bench as a Job
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

# Check results
kubectl logs job/kube-bench -n kube-system
```

### CIS Benchmark Key Sections

| Section | Description | EKS Relevance |
|---------|-------------|---------------|
| 1. Control Plane | API server, etcd, etc. | AWS managed |
| 2. etcd | etcd security | AWS managed |
| 3. Control Plane Configuration | Controllers, scheduler | AWS managed |
| 4. Worker Nodes | Node configuration | **User responsibility** |
| 5. Policies | RBAC, PSP/PSS, network | **User responsibility** |

### Automated Compliance Checks

```yaml
# CronJob for regular checks
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cis-benchmark-scan
  namespace: security
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 02:00
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
              # Upload results to S3
              aws s3 cp /tmp/results.json s3://security-reports/cis-benchmark/$(date +%Y-%m-%d).json
          restartPolicy: OnFailure
```

---

## Cluster Encryption

### EKS Secrets Encryption (KMS)

```bash
# Create KMS key
aws kms create-key \
    --description "EKS Secrets Encryption Key" \
    --key-usage ENCRYPT_DECRYPT

# Create cluster with encryption
aws eks create-cluster \
    --name my-cluster \
    --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
    --resources-vpc-config subnetIds=subnet-xxx,subnet-yyy \
    --encryption-config '[{
        "resources": ["secrets"],
        "provider": {
            "keyArn": "arn:aws:kms:us-east-1:123456789012:key/xxx-xxx"
        }
    }]'
```

```hcl
# Terraform configuration
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

  # ... other configuration
}
```

---

## Node Security

### Bottlerocket OS

```hcl
# Bottlerocket node group
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

  # Bottlerocket configuration
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

### Node Security Hardening

```yaml
# Pod scheduling based on node labels
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

## Private Clusters

### Fully Private EKS Configuration

```hcl
resource "aws_eks_cluster" "private" {
  name     = "private-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = "1.31"

  vpc_config {
    subnet_ids              = module.vpc.private_subnets
    endpoint_private_access = true
    endpoint_public_access  = false  # Disable public endpoint
    security_group_ids      = [aws_security_group.cluster.id]
  }

  # Control plane logging
  enabled_cluster_log_types = [
    "api", "audit", "authenticator", "controllerManager", "scheduler"
  ]

  # Secrets encryption
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

### Bastion or VPN Access

```hcl
# Client VPN endpoint
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

## Multi-tenancy Patterns

### Namespace-based Multi-tenancy

```yaml
---
# Tenant namespace
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
# NetworkPolicy (tenant isolation)
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

### RBAC Multi-tenancy

```yaml
---
# Tenant admin role
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
# Tenant admin binding
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

## Summary

Key EKS security best practices:

1. **IAM Integration**: Access AWS services with IRSA or Pod Identity
2. **Network Security**: Security Groups for Pods, VPC endpoints
3. **Logging and Monitoring**: Control plane logs, GuardDuty
4. **Image Security**: Amazon Inspector, ECR scanning
5. **Compliance**: CIS Benchmark, kube-bench
6. **Encryption**: Secrets encryption with KMS
7. **Node Security**: Bottlerocket OS, least privilege
8. **Multi-tenancy**: Namespace isolation, RBAC, ResourceQuota

---

## References

- [EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
