# S3 and IAM (ACK)

[ACK](../02-ack.md)

示例使用 S3 1.13.1 / IAM 1.10.1 CRD。请先准备基础设施、控制器、ServiceAccount 和 IAM 权限。将存储桶名称、账户、区域和 ARN 替换为已批准的值。在应用引用该 Role 的存储桶策略之前，请先同步 IAM Policy 和 Role；S3 可能会拒绝不存在的主体。

这些版本不使用单独的 BucketPolicy 或 RolePolicyAttachment CRD。请使用 Bucket.spec.policy 和 Role.spec.policyRefs。所有四项 S3 Block Public Access 设置均已启用，并明确指定了 AES256。请确保对象/存储桶 ARN 与策略操作匹配。

此 Role 信任 EC2。它不是 IRSA/Pod Identity Role；EC2 使用时还需要关联 InstanceProfile。其数据读取策略并非完整的 ACK 控制器策略。

## Bucket: bucket-app-data

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

## Policy: policy-app-data-read

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

## Role: role-app-role

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

## 验证和运维前提条件

字段已根据官方版本化 CRD 进行核对。Schema 验证通过并不能证明 IAM 权限、AWS 服务约束、资源创建、连接或恢复均符合要求。应用之前，请明确保留资源的所有权、成本、清理和备份责任。

- [s3 v1.13.1 CRDs](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.13.1/config/crd/bases)
- [iam v1.10.1 CRDs](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.10.1/config/crd/bases)
