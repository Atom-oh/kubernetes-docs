# AWS Controllers for Kubernetes (ACK) 测验

本测验考查你对 AWS Controllers for Kubernetes (ACK) 的概念、架构、安装、安全性和运维的理解。

## 选择题

1. ACK (AWS Controllers for Kubernetes) 的主要用途是什么？
   - A) 仅通过 AWS console 管理 AWS resources
   - B) 通过 Kubernetes API 以声明式方式管理 AWS resources
   - C) 仅在 AWS 上运行 Kubernetes clusters
   - D) 自动降低 AWS costs

<details>

<summary>显示答案</summary>

**答案：B) 通过 Kubernetes API 以声明式方式管理 AWS resources**

**解释：**
ACK 是一个项目，使 Kubernetes 用户能够直接使用熟悉的 Kubernetes APIs 和工具（kubectl、Helm 等）来管理 AWS services 和 resources。这允许与 GitOps 工作流集成，并通过声明式配置以基础设施即代码的方式管理 AWS infrastructure。
</details>

2. 在 ACK 架构中，哪个组件会针对每个 AWS service 单独安装？
   - A) Kubernetes API Server
   - B) Service controller
   - C) etcd database
   - D) kubelet

<details>

<summary>显示答案</summary>

**答案：B) Service controller**

**解释：**
ACK 为每个 AWS service（S3、RDS、DynamoDB 等）提供独立的 service controllers。例如，要管理 S3 buckets，你需要安装 S3 controller；要管理 RDS databases，你需要安装 RDS controller。这种模块化方法允许你只安装所需 services 的 controllers。
</details>

3. 为 ACK controllers 设置 IAM permissions 以管理 AWS resources 的推荐方法是什么？
   - A) 仅使用 EC2 instance profiles
   - B) 将 AWS access keys 存储在 ConfigMap 中
   - C) 使用 IRSA (IAM Roles for Service Accounts)
   - D) 使用具有所有 AWS permissions 的 root account

<details>

<summary>显示答案</summary>

**答案：C) 使用 IRSA (IAM Roles for Service Accounts)**

**解释：**
IRSA (IAM Roles for Service Accounts) 是为 ACK controllers 授予 AWS resource management permissions 的推荐方法，它通过将 IAM roles 与 Kubernetes service accounts 关联来实现。此方法遵循最小权限原则，支持安全的凭证管理，并允许仅向每个 controller 授予必要权限。
</details>

4. 在 ACK 中，删除 Kubernetes resource 时若要保留 AWS resource，应使用哪个 annotation？
   - A) services.k8s.aws/keep-resource: "true"
   - B) services.k8s.aws/deletion-policy: "orphan"
   - C) services.k8s.aws/preserve: "true"
   - D) services.k8s.aws/no-delete: "true"

<details>

<summary>显示答案</summary>

**答案：B) services.k8s.aws/deletion-policy: "orphan"**

**解释：**
默认情况下，当 Kubernetes resource 被删除时，ACK 会删除对应的 AWS resource。不过，设置 `services.k8s.aws/deletion-policy: "orphan"` annotation 后，即使 Kubernetes resource 被删除，也会保留 AWS resource。这对于防止在生产环境中意外删除重要 resources 很有用。
</details>

5. 如何使用 ACK 将现有 AWS resources 导入 Kubernetes？
   - A) 使用 kubectl import command
   - B) 使用 AWS console 的 export feature
   - C) 将 services.k8s.aws/resource-imported: "true" annotation 添加到 resource manifest
   - D) 使用 ACK CLI import command

<details>

<summary>显示答案</summary>

**答案：C) 将 services.k8s.aws/resource-imported: "true" annotation 添加到 resource manifest**

**解释：**
要将现有 AWS resources 导入 ACK，请创建 resource manifest 并添加 `services.k8s.aws/resource-imported: "true"` annotation。这会使 ACK controller 连接到现有 AWS resource，而不是创建新的 resource。这支持将现有基础设施逐步迁移到 GitOps 工作流。
</details>

6. 哪个 ACK service controllers 的成熟度级别适合生产使用？
   - A) Alpha
   - B) Beta
   - C) GA (Generally Available)
   - D) Preview

<details>

<summary>显示答案</summary>

**答案：C) GA (Generally Available)**

**解释：**
ACK service controllers 会经历三个成熟度级别：Alpha、Beta 和 GA。Alpha 是早期开发阶段，API 可能发生变化；Beta 表示功能已完整，但 API 仍可能变化。GA (Generally Available) 是可用于生产的阶段，提供稳定的 APIs 和完整功能。
</details>

7. 哪个 Condition type 表示 ACK resource 已成功同步？
   - A) ACK.Ready
   - B) ACK.ResourceSynced
   - C) ACK.Healthy
   - D) ACK.Available

<details>

<summary>显示答案</summary>

**答案：B) ACK.ResourceSynced**

**解释：**
可以在 `status.conditions` 字段中检查 ACK resource 的状态。当 `ACK.ResourceSynced` Condition 为 True 时，表示 Kubernetes resource 的期望状态（spec）已与实际 AWS resource 状态成功同步。这允许你验证 resource 是否已正确创建或更新。
</details>

8. 在 ACK 中，为多个团队或环境隔离 permissions 的推荐方法是什么？
   - A) 使用单个 controller 管理所有环境
   - B) 使用独立 namespaces 和 IAM roles 进行隔离
   - C) 仅使用 AWS Organizations
   - D) 仅使用 VPC isolation

<details>

<summary>显示答案</summary>

**答案：B) 使用独立 namespaces 和 IAM roles 进行隔离**

**解释：**
要在 ACK 中为多个团队或环境（开发、预发布、生产）隔离 permissions，建议为每个团队或环境使用独立的 Kubernetes namespaces 和 IAM roles。为每个 namespace 安装独立的 controllers，并将 roles 与适用于该环境的 IAM policies 关联。此外，可以使用 Kubernetes RBAC 控制用户对 ACK resources 的访问。
</details>

## 简答题

9. ACK controllers 调用 AWS APIs 来创建、更新和删除 resources，同时检测并解决期望状态与实际状态之间差异的模式叫什么？

<details>

<summary>显示答案</summary>

**答案：Reconciliation Loop 或 Reconciliation Pattern**

**解释：**
Reconciliation loop 是 Kubernetes controllers 的核心模式，ACK 也基于此模式。ACK controllers 会持续比较 Kubernetes resources 的期望状态（spec）与 AWS resources 的实际状态。当检测到差异时，controller 会调用 AWS APIs，使实际状态与期望状态一致。此过程会自动重复，以检测并纠正漂移。
</details>

10. ACK 使用哪种 Kubernetes extension mechanism 通过 Kubernetes API 定义 AWS resources？

<details>

<summary>显示答案</summary>

**答案：CRD (Custom Resource Definition)**

**解释：**
ACK 使用 CRD (Custom Resource Definition) 通过 Kubernetes API 定义 AWS resources。例如，安装 S3 controller 时，会创建 `Bucket` 和 `BucketPolicy` 等 CRDs，让你可以像管理 Kubernetes resources 一样管理 S3 buckets。每个 service controller 都会为对应 AWS service 的 resources 提供 CRDs。
</details>

11. 检查 ACK resource 状态时，可以在哪个字段找到 AWS resource 的 ARN (Amazon Resource Name)？

<details>

<summary>显示答案</summary>

**答案：status.ackResourceMetadata.arn**

**解释：**
当 ACK resource 成功创建后，对应 AWS resource 的 ARN 会存储在 `status.ackResourceMetadata.arn` 字段中。使用 `kubectl describe` command 检查 resource 状态时可以看到此信息。你也可以在 `status.ackResourceMetadata.ownerAccountID` 字段中查看拥有该 resource 的 AWS account ID。
</details>

12. ACK 中允许从多个 clusters 引用同一个 AWS resource，或管理不同 AWS accounts 中 resources 的功能叫什么？

<details>

<summary>显示答案</summary>

**答案：Cross-Account Resource Management 或 Multi-Cluster Support**

**解释：**
ACK 提供了从多个 Kubernetes clusters 引用同一个 AWS resource，或管理不同 AWS accounts 中 resources 的功能。为此，需要配置 IAM role chaining 或 cross-account IAM policies，使 ACK controllers 能够访问其他 accounts 中的 resources。此功能支持在 multi-cluster 或 multi-account 环境中进行集中式 resource management。
</details>

## 动手实践题

13. 编写一个 Kubernetes manifest，使用 ACK 创建一个 S3 bucket。bucket 名称为 "my-ack-demo-bucket-2025"，并添加标签 Environment: Development。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-demo-bucket
  namespace: default
spec:
  name: my-ack-demo-bucket-2025
  tagging:
    tagSet:
      - key: Environment
        value: Development
  createBucketConfiguration:
    locationConstraint: us-west-2
```

**解释：**
这是使用 ACK S3 controller 创建 S3 bucket 的 manifest。`metadata.name` 是 Kubernetes resource name，`spec.name` 是实际的 AWS S3 bucket name。由于 bucket names 必须全局唯一，实际使用时请使用唯一名称。AWS resource tags 可以通过 `tagging.tagSet` 设置，`createBucketConfiguration.locationConstraint` 指定 bucket 将被创建的 region。
</details>

14. 编写使用 Helm 安装 ACK S3 controller 并配置 IRSA 的 commands。使用 cluster name "my-eks-cluster" 和 namespace "ack-system"。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1. Add Helm chart repository
helm repo add aws-controllers-k8s https://aws.github.io/eks-charts
helm repo update

# 2. Create IAM service account for IRSA
eksctl create iamserviceaccount \
  --cluster=my-eks-cluster \
  --namespace=ack-system \
  --name=ack-s3-controller \
  --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 3. Install S3 controller
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set aws.region=us-west-2
```

**解释：**
首先，添加 ACK Helm chart repository。然后使用 eksctl 创建用于 IRSA 配置的 IAM service account。S3 management 所需的 IAM policy 会附加到此 service account。最后，使用 Helm 安装 S3 controller，并配置为使用已创建的 service account。对于生产环境，最好使用遵循最小权限原则的 custom policy，而不是 AmazonS3FullAccess。
</details>

15. 编写 commands，用于检查 controller logs 并查看 resource status，以排查 ACK 创建的 resources 的问题。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1. Check ACK controller logs
kubectl logs -n ack-system -l app.kubernetes.io/name=ack-s3-controller

# 2. Check specific resource status and events
kubectl describe bucket my-ack-demo-bucket

# 3. Check detailed resource status (JSON format)
kubectl get bucket my-ack-demo-bucket -o json | jq '.status'

# 4. Check resource-related events
kubectl get events --field-selector involvedObject.name=my-ack-demo-bucket

# 5. Check CRD installation status
kubectl get crd | grep services.k8s.aws

# 6. Check controller deployment status
kubectl get deployment -n ack-system
```

**解释：**
排查 ACK resource 创建问题时，需要检查多个方面。首先，检查 controller logs 以识别 AWS API 调用错误或 permission 问题。使用 `kubectl describe` 检查 resource 状态和 Conditions，并通过 events 跟踪最近的变化。同时确认 CRDs 已正确安装且 controller pods 正常运行。常见问题包括 IAM permissions 不足、region 设置不正确以及 resource name 冲突。
</details>

---

**评分：**
- 13-15 题正确：优秀（ACK expert level）
- 10-12 题正确：良好（具备 practical application 能力）
- 7-9 题正确：一般（建议 additional learning）
- 0-6 题正确：不足（需要复习 basic concepts）

[返回学习材料](../../platform-engineering/02-ack.md)
