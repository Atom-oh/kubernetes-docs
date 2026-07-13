# AWS Controllers for Kubernetes (ACK)

## Table of Contents

* [Introduction](02-ack.md#introduction)
* [Architecture](02-ack.md#architecture)
* [Installation and Configuration](02-ack.md#installation-and-configuration)
* [Supported AWS Services](02-ack.md#supported-aws-services)
* [The Origins and Evolution of ACK](02-ack.md#the-origins-and-evolution-of-ack)
* [Resource Creation Examples](02-ack.md#resource-creation-examples)
* [Resource Management](02-ack.md#resource-management)
* [Security Considerations](02-ack.md#security-considerations)
* [Monitoring and Logging](02-ack.md#monitoring-and-logging)
* [Best Practices](02-ack.md#best-practices)
* [Troubleshooting](02-ack.md#troubleshooting)
* [Conclusion](02-ack.md#conclusion)

## Introduction

AWS Controllers for Kubernetes (ACK) 是一个项目，使 Kubernetes 用户能够通过 Kubernetes API 直接管理 AWS 服务和资源。ACK 将 Kubernetes 的声明式 API 模型扩展到 AWS 资源，让开发者和运维人员可以使用熟悉的 Kubernetes 工具和 API 来管理 AWS 基础设施。

### Key Benefits of ACK

* **统一体验**：使用相同的工具和工作流管理 Kubernetes 和 AWS 资源
* **GitOps 支持**：将 AWS 资源定义为代码，并在 Git 仓库中管理它们
* **声明式配置**：定义期望状态，并让 controller 协调实际状态
* **Kubernetes Native 方法**：使用标准 Kubernetes 概念和 API
* **多集群支持**：从多个集群引用相同的 AWS 资源
* **IAM 集成**：将 Kubernetes service accounts 与 AWS IAM roles 集成

### Comparison with Existing Approaches

| Feature                | ACK                 | AWS CloudFormation       | Terraform       | AWS SDK/CLI         |
| ---------------------- | ------------------- | ------------------------ | --------------- | ------------------- |
| Interface              | Kubernetes API      | CloudFormation templates | HCL             | Programming API/CLI |
| Declarative            | ✅                   | ✅                        | ✅               | ❌                   |
| State Management       | Kubernetes etcd     | CloudFormation stack     | Terraform state | Manual management   |
| Drift Detection        | ✅                   | ✅                        | ✅               | ❌                   |
| Kubernetes Integration | Native              | Limited                  | Limited         | Limited             |
| Supported Services     | Limited (expanding) | Extensive                | Extensive       | All services        |

## Architecture

ACK 基于 Kubernetes operator 模式，并为每个 AWS 服务提供 controller。

### Key Components

1. **Service Controller**：每个 AWS 服务的专用 controller
2. **Custom Resource Definitions (CRD)**：将 AWS 资源定义为 Kubernetes API
3. **Custom Resources (CR)**：AWS 资源的实例
4. **Reconciliation Loop**：检测并解决期望状态与实际状态之间的差异

### How It Works

1. 用户应用 Kubernetes YAML manifest 来定义 AWS 资源
2. ACK controller 检测 custom resource 变更
3. Controller 调用 AWS API 来创建、更新或删除对应的 AWS 资源
4. Controller 监控 AWS 资源状态并更新 Kubernetes resource status

## Installation and Configuration

### Prerequisites

* Kubernetes cluster (v1.16 或更高版本)
* 已配置 kubectl
* AWS 账户和适当的 IAM permissions
* Helm 3（可选）

### Installation Methods

#### 1. Installing ACK Service Controller

ACK controllers 会针对每个 AWS 服务分别安装。例如，要安装 S3 controller：

```bash
# Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts

# Install S3 controller
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart
```

#### 2. IAM Permission Setup

ACK controllers 需要适当的 IAM permissions 才能管理 AWS 资源。你可以使用 IRSA (IAM Roles for Service Accounts) 设置权限：

```bash
# Create IAM policy
aws iam create-policy \
  --policy-name ACKs3ControllerPolicy \
  --policy-document file://s3-controller-policy.json

# Attach IAM role to service account
eksctl create iamserviceaccount \
  --cluster=<cluster-name> \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::<account-id>:policy/ACKs3ControllerPolicy \
  --approve
```

s3-controller-policy.json 示例：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutBucketTagging",
        "s3:GetBucketTagging",
        "s3:PutEncryptionConfiguration",
        "s3:GetEncryptionConfiguration",
        "s3:PutBucketPolicy",
        "s3:GetBucketPolicy",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 3. Controller Configuration

你可以使用 Helm values files 来自定义 controller 配置：

```yaml
# values.yaml
aws:
  region: us-west-2
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<account-id>:role/ACKs3ControllerRole
```

```bash
helm install --create-namespace -n ack-system ack-s3-controller \
  aws-controllers-k8s/s3-chart -f values.yaml
```

## Supported AWS Services

ACK 为多种 AWS 服务提供 controllers。每个 service controller 都可以单独安装和管理。

### Currently Supported Services (as of July 2025)

* Amazon API Gateway (apigatewayv2)
* Amazon DynamoDB
* Amazon ECR
* Amazon EKS
* Amazon ElastiCache
* Amazon MemoryDB
* Amazon MQ
* Amazon RDS
* Amazon S3
* Amazon SageMaker
* AWS IAM
* AWS Lambda
* AWS SNS
* AWS SQS
* Amazon EventBridge
* Amazon MSK
* Amazon OpenSearch Service
* AWS ACM
* AWS Route 53

### Service Controller Status

每个 service controller 具有以下状态之一：

* **Alpha**：早期开发阶段，API 可能会变更
* **Beta**：功能完整，稳定但 API 可能会变更
* **GA (Generally Available)**：可用于生产环境

在 [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community) 查看最新状态。

## The Origins and Evolution of ACK

### Evolution of Infrastructure as Code

AWS resource management 的演进如下：

1. **手动管理时代**：直接在 AWS Console 中创建和管理资源
2. **AWS CloudFormation**：引入基于模板的声明式基础设施管理，但与 Kubernetes 工作流分离
3. **Terraform**：通过 multi-cloud 支持和 HCL 实现统一的基础设施管理，但仍然需要单独的工具和工作流
4. **ACK**：通过 Kubernetes API 直接管理 AWS 资源 — 利用现有的 K8s 工具链，包括 kubectl、GitOps、RBAC

### Why Kubernetes-Native AWS Management?

现有方法的限制：

* **工具分离**：分别操作 Terraform/CloudFormation 和 kubectl 带来的双重管理负担
* **状态不一致**：IaC 工具状态与 Kubernetes cluster 状态相互分离，可能导致漂移
* **GitOps 集成困难**：难以使用 ArgoCD/Flux 等 GitOps 工具管理 AWS 资源
* **团队体验碎片化**：基础设施团队和应用团队使用不同的工具和工作流

ACK 通过单一 Kubernetes control plane 实现 AWS 基础设施和应用程序的统一管理，从而解决这些问题。

## Resource Creation Examples

有关使用 ACK 创建 AWS 资源的详细示例，请参阅以下文档：

* [S3 and IAM](ack/01-s3-iam.md)
* [SQS and SNS](ack/02-sqs-sns.md)
* [ELBv2, Route 53, RDS (NLB + Aurora PostgreSQL)](ack/03-elbv2-route53-rds.md)

## Resource Management

### Checking Resource Status

要检查 ACK resources 的状态：

```bash
kubectl describe bucket my-sample-bucket
```

示例输出：

```
Name:         my-sample-bucket
Namespace:    default
API Version:  s3.services.k8s.aws/v1alpha1
Kind:         Bucket
Metadata:
  ...
Spec:
  Name:  my-unique-bucket-name-123
  ...
Status:
  Ack Resource Metadata:
    Arn:                    arn:aws:s3:::my-unique-bucket-name-123
    Owner Account ID:       123456789012
  Conditions:
    Last Transition Time:  2025-07-13T04:00:00Z
    Status:                True
    Type:                  ACK.ResourceSynced
```

### Updating Resources

要更新 ACK resource，请修改 manifest 并重新应用：

```bash
kubectl apply -f updated-bucket.yaml
```

### Deleting Resources

要删除 ACK resource：

```bash
kubectl delete bucket my-sample-bucket
```

默认情况下，当 Kubernetes resource 被删除时，ACK 也会删除对应的 AWS 资源。你可以使用 annotations 更改此行为：

```yaml
metadata:
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
```

### Importing Resources

要将现有 AWS 资源导入 ACK：

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: imported-bucket
  annotations:
    services.k8s.aws/resource-imported: "true"
spec:
  name: existing-bucket-name
```

## Security Considerations

### IAM Permission Management

ACK controllers 需要适当的 IAM permissions 来管理对应的 AWS 资源。建议遵循最小权限原则，只授予必要的权限。

#### Granular IAM Policy Example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:GetBucketTagging",
        "s3:PutBucketTagging"
      ],
      "Resource": "arn:aws:s3:::my-unique-bucket-name-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets"
      ],
      "Resource": "*"
    }
  ]
}
```

### Namespace Isolation

你可以为不同团队或环境使用独立的 namespaces 和 IAM roles 来隔离权限：

```bash
# Install controller for development environment
helm install --create-namespace -n ack-system-dev ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleDev

# Install controller for production environment
helm install --create-namespace -n ack-system-prod ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/ACKs3ControllerRoleProd
```

### Resource Policies

你可以使用 Kubernetes RBAC 限制对 ACK resources 的访问：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: s3-editor
rules:
- apiGroups: ["s3.services.k8s.aws"]
  resources: ["buckets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-s3-editor
  namespace: dev
subjects:
- kind: User
  name: developer
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: s3-editor
  apiGroup: rbac.authorization.k8s.io
```

## Monitoring and Logging

### Checking Controller Logs

要查看 ACK controller logs：

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
```

### Prometheus Metrics

ACK controllers 暴露 Prometheus metrics：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ack-s3-controller
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: ack-s3-controller
  endpoints:
  - port: metrics
    interval: 30s
```

关键 metrics：

* `ack_reconcile_success_total`：成功 reconciliations 的数量
* `ack_reconcile_failure_total`：失败 reconciliations 的数量
* `ack_api_call_duration_seconds`：AWS API call latency

### AWS CloudTrail Integration

ACK controllers 发起的 AWS API calls 会记录在 CloudTrail 中。你可以查看 CloudTrail logs 来审计 ACK 操作。

## Best Practices

### Resource Organization

1. **清晰命名**：使用清晰且一致的资源名称
2. **使用 Annotations**：利用 annotations 进行资源管理
3. **应用 Labels**：使用 labels 进行资源分组和过滤

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data-bucket
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
    description: "Application data storage"
  labels:
    environment: production
    app: my-application
    team: data-engineering
spec:
  name: my-app-data-20250713
  tagging:
    tagSet:
      - key: Environment
        value: Production
```

### Version Control

1. **使用 Git Repository**：将 ACK resource manifests 存储在 Git repository 中
2. **分离环境配置**：为 development、staging、production environments 维护独立配置
3. **使用 Kustomize**：使用 Kustomize 管理特定环境差异

```
├── base/
│   ├── s3-bucket.yaml
│   ├── sqs-queue.yaml
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch.yaml
│   └── prod/
│       ├── kustomization.yaml
│       └── patch.yaml
```

### Performance and Scalability

1. **设置 Resource Requests and Limits**：为 controllers 分配适当资源
2. **扩展 Controller Replicas**：在大型环境中增加 controller replicas
3. **调整 Reconciliation Frequency**：根据需要优化 reconciliation frequency

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: ack-s3-controller
  namespace: ack-system
spec:
  chart:
    spec:
      chart: s3-chart
      sourceRef:
        kind: HelmRepository
        name: aws-controllers-k8s
  values:
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
    replicaCount: 2
```

### Disaster Recovery

1. **备份策略**：定期备份 ACK resource manifests
2. **恢复计划**：记录发生故障时的资源恢复流程
3. **多区域考虑**：为关键资源实施 multi-region 策略

## Troubleshooting

### Common Issues

#### 1. Resource Creation Failure

**症状**：ACK resource 已创建，但 AWS 资源未创建

**解决方案**：

* 检查 controller logs
* 验证 IAM permissions
* 检查 resource status 和 events

```bash
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller
kubectl describe bucket my-sample-bucket
```

#### 2. Permission Issues

**症状**："AccessDenied" error message

**解决方案**：

* 验证 IAM policies 和 roles
* 检查 IRSA 配置
* 查看 CloudTrail logs

#### 3. Resource Deletion Stuck

**症状**：Resource 卡在 "Terminating" state

**解决方案**：

* 检查 dependencies
* 移除 finalizers（如有必要）

```bash
kubectl patch bucket my-sample-bucket -p '{"metadata":{"finalizers":[]}}' --type=merge
```

### Debugging Tools

```bash
# Check controller version
kubectl get deployment -n ack-system ack-s3-controller -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check CRDs
kubectl get crd | grep services.k8s.aws

# Check events
kubectl get events --field-selector involvedObject.name=my-sample-bucket

# Check controller logs in detail
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller --tail=100
```

## Conclusion

AWS Controllers for Kubernetes (ACK) 是一个强大的工具，可以弥合 Kubernetes 与 AWS 服务之间的差距。ACK 允许 Kubernetes 用户使用熟悉的 Kubernetes APIs 和工具来管理 AWS 资源。

本文档介绍了 ACK 的基本概念、安装方法、S3、IAM、SQS、SNS 资源创建示例、资源管理、安全注意事项、监控和故障排除。

ACK 会持续演进，并不断增加对更多 AWS 服务的支持。结合 GitOps workflows，它提供了一种强大的方式来以代码形式管理 AWS 基础设施。

### Next Steps

* 使用 ACK 构建 GitOps pipelines
* 集成多个 AWS service controllers
* 扩展 custom resource definitions
* 制定 multi-account 和 multi-region 策略

## References

* [ACK Official Documentation](https://aws-controllers-k8s.github.io/community/)
* [ACK GitHub Repository](https://github.com/aws-controllers-k8s/community)
* [AWS Service Controller List](https://aws-controllers-k8s.github.io/community/docs/community/services/)
* [ACK Design Principles](https://aws-controllers-k8s.github.io/community/docs/community/design/)
* [EKS Workshop - ACK](https://www.eksworkshop.com/intermediate/290_ack/)

## Quiz

要测试你在本章中学到的内容，请尝试 [ACK Quiz](../quizzes/platform-engineering/02-ack-quiz.md)。
