# AWS Controllers for Kubernetes (ACK) 测验

[ACK](../../platform-engineering/02-ack.md)

这些问题保留了原有的 15 个主题，并采用经过审查的控制器行为作为依据。

## 1. ACK 的主要用途是什么？

<details>
<summary>显示答案</summary>

通过 Kubernetes API 和自定义资源以声明式方式管理 AWS 资源。它不保证自动节省成本或立即就绪。

</details>

## 2. 每项服务会安装什么组件？

<details>
<summary>显示答案</summary>

一个服务控制器及其 CRD。选择所需的服务，并检查带版本的 CRD 中支持的资源和字段。

</details>

## 3. 控制器应如何接收 AWS 凭证？

<details>
<summary>显示答案</summary>

配置工作负载身份，例如 IRSA 或受支持的 EKS Pod Identity。验证 OIDC 信任关系/关联、ServiceAccount、SDK/代理兼容性以及最小 IAM 权限。不要将访问密钥存储在 ConfigMap 中，也不要使用根凭证。

</details>

## 4. 删除 CR 后，哪个值可以保留 AWS 资源？

<details>
<summary>显示答案</summary>

`services.k8s.aws/deletion-policy: retain`。当前运行时不接受 orphan。优先级依次为 CR、命名空间的特定服务注解、控制器默认值。保留的 AWS 资源仍需要明确所有权并进行运维管理。

</details>

## 5. 如何接管现有资源？

<details>
<summary>显示答案</summary>

使用 ResourceAdoption 的 `adoption-policy: adopt` 和特定服务的 adoption-fields，并验证相关开关、标识符、区域和账户。resource-imported:true 并非此配置；adopt-or-create 可以创建缺失的资源。后续协调可能会修改资源，因此要区分资源接管与只读行为。

</details>

## 6. GA 状态说明了什么？

<details>
<summary>显示答案</summary>

它表示控制器的官方成熟度阶段，而不代表支持每个 AWS API 或满足所有运维要求。要区分成熟度与 CRD 的 v1alpha1 字符串，并核实字段、发行版本和运维适用性。

</details>

## 7. 哪个条件表示已同步？它有哪些局限？

<details>
<summary>显示答案</summary>

ACK.ResourceSynced=True 表示控制器已完成同步。它不能证明应用已就绪、数据库已连接或消息已送达。还应检查其他条件和 AWS 服务状态。

</details>

## 8. 将团队划分到不同命名空间就能实现完全隔离吗？

<details>
<summary>显示答案</summary>

不能。默认的 installScope=cluster 会监视所有命名空间中的 CR。应同时限制 watchNamespace/installScope、ServiceAccount/IAM/RBAC 以及跨命名空间/CARM 行为。命名空间模式仍可能具有针对其命名空间缓存的集群级读取权限。

</details>

## 9. 哪种模式可以使期望的 AWS 状态与实际状态保持一致？

<details>
<summary>显示答案</summary>

协调循环会反复处理受支持的字段和控制器逻辑。瞬时错误和 AWS 配额会影响协调过程；它不会立即修复所有可能的状态漂移。

</details>

## 10. 哪种 Kubernetes 扩展定义资源输入？

<details>
<summary>显示答案</summary>

CRD。S3 示例使用 Bucket.spec.policy。经审查的版本没有单独的 BucketPolicy 或 IAM RolePolicyAttachment CRD；请核实实际的 kind 和架构。

</details>

## 11. 可以在哪里找到 ARN？

<details>
<summary>显示答案</summary>

如果该资源提供 ARN，请使用 status.ackResourceMetadata.arn，包括 NLB 和 TargetGroup。其他 status 字段因资源而异。

</details>

## 12. CARM 与跨集群引用有何不同？

<details>
<summary>显示答案</summary>

CARM 会配置控制器，通过假设目标角色来管理另一个 AWS 账户，因此需要信任关系、AssumeRole 权限、映射和控制器设置。它不能确保多个集群同时修改资源是安全的。应将修改所有权与只读引用分开。

</details>

## 13. 带有 Development 标签的 S3 Bucket 示例应包含什么？

<details>
<summary>显示答案</summary>

使用全局唯一的名称、实际区域、tagging.tagSet、全部四项 Block Public Access 设置以及加密。应用 bucket policy 之前，principal/IAM Role 必须已经存在。请替换示例名称和账户 ID。

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

## 14. 如何检查 ACK S3 chart？安装之前需要做什么？

<details>
<summary>显示答案</summary>

该命令会在离线环境中渲染一个固定版本的 OCI chart。在实际安装/升级之前，先准备好 infra、其 ServiceAccount、IRSA/Pod Identity 和 IAM 权限。渲染结果不能验证 AWS 部署。

```bash
helm template ack-s3 \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --version 1.13.1 --namespace infra \
  --set aws.region=us-west-2 \
  --set installScope=namespace --set watchNamespace=infra \
  --set enableCARM=false --set enableCrossNamespace=false \
  --set serviceAccount.create=false \
  --set serviceAccount.name=ack-s3-controller \
  --set metrics.service.create=true --set deletionPolicy=retain
```

</details>

## 15. 应检查哪些状态和日志？

<details>
<summary>显示答案</summary>

指定命名空间和完全限定的 kind；检查条件/事件、控制器镜像/日志、实际账户/区域/权限以及引用。chart 标签是 app.kubernetes.io/instance=ack-s3。清除 finalizer 并非常规修复手段。

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
