# S3 と IAM (ACK)

[ACK](../02-ack.md)

例では S3 1.12.1 / IAM 1.9.0 の CRD を使用します。先にインフラ、controller、ServiceAccount、IAM 権限を準備してください。バケット名、アカウント、リージョン、ARN は承認済みの値に置き換えてください。その Role を参照するバケットポリシーを適用する前に、IAM Policy と Role を同期させてください。S3 は存在しないプリンシパルを拒否することがあります。

これらのバージョンでは、独立した BucketPolicy や RolePolicyAttachment の CRD は使用しません。Bucket.spec.policy と Role.spec.policyRefs を使用します。S3 Block Public Access の 4 つの設定はすべて有効化され、AES256 は明示的に指定されています。オブジェクト/バケットの ARN をポリシーのアクションに合わせてください。

この Role は EC2 を信頼します。IRSA/Pod Identity 用の role ではなく、EC2 で使用する場合は InstanceProfile の関連付けも必要です。このデータ読み取りポリシーは、ACK controller 用の完全なポリシーではありません。

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

## 検証と運用上の前提条件

各フィールドは公式のバージョン付き CRD と照合して確認しました。スキーマの検証が通っても、IAM 権限、AWS サービスの制約、リソースの作成、接続性、復旧が保証されるわけではありません。適用する前に、保持されるリソースについて所有者、コスト、クリーンアップ、バックアップの責任を割り当ててください。

- [s3 v1.12.1 CRDs](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/config/crd/bases)
- [iam v1.9.0 CRDs](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.9.0/config/crd/bases)