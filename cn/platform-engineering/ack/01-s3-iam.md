# S3 和 IAM (ACK)

[ACK](../02-ack.md)

示例使用 S3 1.12.1 / IAM 1.9.0 CRD。请先准备基础设施、controller、ServiceAccount 和 IAM 权限。请将 bucket 名称、账户、region 和 ARN 替换为已批准的值。在应用引用该 Role 的 bucket policy 前，请先同步 IAM Policy 和 Role；S3 可能会拒绝不存在的 principal。

这些版本不使用单独的 BucketPolicy 或 RolePolicyAttachment CRD。请使用 Bucket.spec.policy 和 Role.spec.policyRefs。四项 S3 Block Public Access 设置均已启用，并且显式指定 AES256。请使 object/bucket ARN 与 policy action 相匹配。

此 Role 信任 EC2。它不是 IRSA/Pod Identity Role；使用 EC2 还需要关联 InstanceProfile。它的数据读取 policy 并非完整的 ACK controller policy。

## Bucket — bucket-app-data

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

## Policy — policy-app-data-read

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Policy
metadata:
  name: app-data-read
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: AppDataRead
  policyDocument: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n    {\n\
    \      \"Effect\": \"Allow\",\n      \"Action\": \"s3:ListBucket\",\n      \"\
    Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name\"\n    },\n\
    \    {\n      \"Effect\": \"Allow\",\n      \"Action\": \"s3:GetObject\",\n  \
    \    \"Resource\": \"arn:aws:s3:::replace-with-globally-unique-bucket-name/*\"\
    \n    }\n  ]\n}"
```

## Role — role-app-role

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Role
metadata:
  name: app-role
  namespace: infra
  annotations:
    services.k8s.aws/deletion-policy: retain
spec:
  name: MyApplicationRole
  assumeRolePolicyDocument: "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [\n\
    \    {\n      \"Effect\": \"Allow\",\n      \"Principal\": {\n        \"Service\"\
    : \"ec2.amazonaws.com\"\n      },\n      \"Action\": \"sts:AssumeRole\"\n    }\n\
    \  ]\n}"
  policyRefs:
  - from:
      name: app-data-read
  maxSessionDuration: 3600
```

## 验证与运维前提条件

已根据官方版本化 CRD 检查字段。schema 验证成功并不代表 IAM 权限、AWS 服务约束、创建、连接或恢复已得到保证。应用前，请为保留的资源明确分配所有权、成本、清理和备份责任。

- [s3 v1.12.1 CRDs](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/config/crd/bases)
- [iam v1.9.0 CRDs](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.9.0/config/crd/bases)
