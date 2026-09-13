# AWS Controllers for Kubernetes (ACK) 测验

[ACK](../../platform-engineering/02-ack.md)

这些问题基于经过审查的 controller 行为，保留了原有的 15 个主题。

## 1. ACK 的主要用途是什么？

<details>
<summary>显示答案</summary>

通过 Kubernetes APIs 和自定义资源以声明式方式管理 AWS 资源。它并不保证自动节省成本或立即就绪。

</details>

## 2. 每项服务会安装哪个组件？

<details>
<summary>显示答案</summary>

一个服务 controller 及其 CRDs。选择所需服务，并在已版本化的 CRDs 中检查受支持的资源和字段。

</details>

## 3. controller 应如何获取 AWS 凭证？

<details>
<summary>显示答案</summary>

配置工作负载身份，例如 IRSA 或受支持的 EKS Pod Identity。验证 OIDC 信任关系/关联、ServiceAccount、SDK/agent 兼容性以及最小 IAM 权限。不要将访问密钥存储在 ConfigMaps 中，也不要使用 root 凭证。

</details>

## 4. 哪个值可在删除 CR 后保留 AWS 资源？

<details>
<summary>显示答案</summary>

`services.k8s.aws/deletion-policy: retain`。当前运行时不接受 orphan。优先级依次为 CR、namespace 特定服务 annotation，然后是 controller 默认值。已保留的 AWS 资源仍需要所有权管理和运维操作。

</details>

## 5. 如何接管现有资源？

<details>
<summary>显示答案</summary>

使用 ResourceAdoption 的 `adoption-policy: adopt` 和服务特定的 adoption-fields，并验证 gates、标识符、区域和账户。resource-imported:true 并非此配置；adopt-or-create 可以创建缺失的资源。后续 reconciliation 可能会修改资源，因此应区分接管与只读行为。

</details>

## 6. GA 状态确立了什么？

<details>
<summary>显示答案</summary>

它标识 controller 的官方成熟度阶段，而不是对每个 AWS API 或运维要求的支持。应将成熟度与 CRD 的 v1alpha1 字符串区分开，并验证字段、版本发布和运维适用性。

</details>

## 7. 哪个 condition 表示同步，其限制是什么？

<details>
<summary>显示答案</summary>

ACK.ResourceSynced=True 描述 controller 同步状态。它并不能证明应用就绪、数据库连接或消息传递正常。请检查其他 conditions 和 AWS 服务状态。

</details>

## 8. 分离团队 namespace 是否就完成了隔离？

<details>
<summary>显示答案</summary>

否。默认的 installScope=cluster 会跨 namespace 监视 CR。应同时限制 watchNamespace/installScope、ServiceAccount/IAM/RBAC 和跨 namespace/CARM 行为。namespace 模式仍可能具有用于其 namespace 缓存的 cluster 读取权限。

</details>

## 9. 什么模式可使所需的 AWS 状态与观测到的状态保持一致？

<details>
<summary>显示答案</summary>

reconciliation loop 会反复处理受支持的字段和 controller 逻辑。瞬态错误和 AWS 配额会影响它；它不会立即修复所有可能的状态漂移。

</details>

## 10. 哪种 Kubernetes 扩展定义资源输入？

<details>
<summary>显示答案</summary>

CRDs。S3 示例使用 Bucket.spec.policy。经审查的版本没有单独的 BucketPolicy 或 IAM RolePolicyAttachment CRDs；请验证实际的 kinds 和 schemas。

</details>

## 11. 在哪里可以找到 ARN？

<details>
<summary>显示答案</summary>

当资源提供该值时，使用 status.ackResourceMetadata.arn，包括 NLB 和 TargetGroup。其他 status 字段因资源而异。

</details>

## 12. CARM 与跨集群引用有何不同？

<details>
<summary>显示答案</summary>

CARM 配置 controller 通过假设 target-role 来管理另一个 AWS 账户，这需要信任关系、AssumeRole 权限、映射和 controller 设置。它并不会让多个集群的竞争性修改变得安全。应将修改所有权与只读引用分离。

</details>

## 13. 带有 Development 标签的 S3 Bucket 示例中应包含什么？

<details>
<summary>显示答案</summary>

使用全局唯一名称、实际区域、tagging.tagSet、全部四项 Block Public Access 设置以及加密。应用 bucket policy 前，principal/IAM Role 必须已经存在。请替换示例名称和账户 IDs。

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: app-data
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: replace-with-globally-unique-bucket-name
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlock:
    blockPublicACLs: true
    blockPublicPolicy: true
    ignorePublicACLs: true
    restrictPublicBuckets: true
  encryption:
    rules:
    - applyServerSideEncryptionByDefault:
        sseAlgorithm: AES256
  tagging:
    tagSet:
    - key: Environment
      value: Development
  policy: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n      \"\
    Effect\": \"Allow\",\n      \"Principal\": {\n        \"AWS\": \"arn:aws:iam::123456789012:role/MyApplicationRole\"\
    \n      },\n      \"Action\": \"s3:GetObject\",\n      \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

</details>

## 14. 如何检查 ACK S3 chart，安装之前应做什么？

<details>
<summary>显示答案</summary>

该命令会离线渲染已固定版本的 OCI chart。在实际 install/upgrade 前，准备好 infra、其 ServiceAccount、IRSA/Pod Identity 和 IAM 权限。渲染并不是 AWS 部署验证。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.12.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

</details>

## 15. 应检查哪些 status 和 logs？

<details>
<summary>显示答案</summary>

指定 namespace 和完全限定的 kinds；检查 conditions/events、controller image/logs、实际账户/区域/权限以及引用。chart label 为 app.kubernetes.io/instance=ack-s3。清除 finalizers 并不是常规修复方法。

```bash
kubectl get buckets.s3.services.k8s.aws -n infra
kubectl get bucket.s3.services.k8s.aws app-data -n infra -o json
kubectl describe bucket.s3.services.k8s.aws app-data -n infra
kubectl logs -n infra \
  -l app.kubernetes.io/instance=ack-s3 --all-containers --tail=100
kubectl get events -n infra \
  --field-selector involvedObject.name=app-data
```

</details>
