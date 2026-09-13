# S3 및 IAM (ACK)

[ACK](../02-ack.md)

S3 1.12.1 / IAM 1.9.0 CRD 기준의 예제입니다. infra namespace, 각 controller와 ServiceAccount·IAM 권한을 먼저 준비하세요. bucket 이름과 계정·region·ARN을 실제 승인된 값으로 바꿉니다. 아래 IAM Policy와 Role이 동기화된 뒤, 그 Role을 참조하는 bucket policy를 적용합니다. 존재하지 않는 principal은 S3 policy에서 거부될 수 있습니다.

BucketPolicy나 RolePolicyAttachment라는 별도 CRD는 이 버전에서 사용하지 않습니다. Bucket.spec.policy와 Role.spec.policyRefs로 표현합니다. S3 Block Public Access 네 항목을 모두 켰으며 AES256을 명시했습니다. policy의 object ARN과 bucket ARN은 action에 맞게 구분합니다.

이 IAM Role의 trust는 EC2용입니다. Kubernetes Pod용 IRSA/Pod Identity role이 아니며 EC2에 쓰려면 InstanceProfile 연결도 별도로 필요합니다. 데이터 읽기 policy는 ACK controller를 운영하는 데 필요한 전체 policy가 아닙니다.

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

## 검증과 운영 전 확인

표시한 필드는 공식 versioned CRD로 검사했습니다. 스키마 통과는 IAM, AWS 서비스 제약, 실제 생성·연결·복구를 증명하지 않습니다. retain으로 남긴 리소스의 운영·비용·삭제 책임과 백업 계획을 정한 뒤 적용하세요.

- [s3 v1.12.1 CRDs](https://github.com/aws-controllers-k8s/s3-controller/tree/v1.12.1/config/crd/bases)
- [iam v1.9.0 CRDs](https://github.com/aws-controllers-k8s/iam-controller/tree/v1.9.0/config/crd/bases)
