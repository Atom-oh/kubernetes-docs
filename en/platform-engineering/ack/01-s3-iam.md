# S3 and IAM (ACK)

[ACK](../02-ack.md)

Examples use S3 1.12.1 / IAM 1.9.0 CRDs. Prepare infra, controllers, ServiceAccounts and IAM permissions first. Replace bucket name, account, region and ARNs with approved values. Synchronize the IAM Policy and Role before applying the bucket policy that references that Role; S3 can reject nonexistent principals.

These versions do not use separate BucketPolicy or RolePolicyAttachment CRDs. Use Bucket.spec.policy and Role.spec.policyRefs. All four S3 Block Public Access settings are enabled and AES256 is explicit. Match object/bucket ARNs to the policy actions.

This Role trusts EC2. It is not an IRSA/Pod Identity role; EC2 use also requires an InstanceProfile association. Its data-reading policy is not a complete ACK controller policy.

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

## Verification and Operational Prerequisites

Fields were checked against official versioned CRDs. Schema success does not establish IAM permissions, AWS service constraints, creation, connectivity or recovery. Assign ownership, costs, cleanup and backup responsibilities for retained resources before applying.

- [s3 v1.12.1 CRDs](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/config/crd/bases)
- [iam v1.9.0 CRDs](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.9.0/config/crd/bases)
