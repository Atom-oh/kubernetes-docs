# S3 및 IAM 리소스 생성 예제 (ACK)

> **참고**: 이 문서는 [ACK 개념 문서](../02-ack.md)의 실습 예제입니다.

## S3 버킷 생성

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-sample-bucket
spec:
  name: my-unique-bucket-name-123
  tagging:
    tagSet:
      - key: Environment
        value: Development
      - key: Project
        value: ACK-Demo
  createBucketConfiguration:
    locationConstraint: us-west-2
```

## S3 버킷 정책 설정

```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: BucketPolicy
metadata:
  name: my-bucket-policy
spec:
  bucket: my-unique-bucket-name-123
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::123456789012:role/MyRole"
          },
          "Action": [
            "s3:GetObject"
          ],
          "Resource": [
            "arn:aws:s3:::my-unique-bucket-name-123/*"
          ]
        }
      ]
    }
```

## IAM 역할 생성

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Role
metadata:
  name: my-iam-role
spec:
  name: MyApplicationRole
  assumeRolePolicyDocument: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "ec2.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
  description: "Role for my application"
  maxSessionDuration: 3600
  tags:
    - key: Environment
      value: Development
```

## IAM 정책 생성 및 연결

```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Policy
metadata:
  name: my-s3-access-policy
spec:
  name: S3ReadOnlyAccess
  policyDocument: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "s3:Get*",
            "s3:List*"
          ],
          "Resource": "*"
        }
      ]
    }
  description: "Policy for S3 read-only access"
---
apiVersion: iam.services.k8s.aws/v1alpha1
kind: RolePolicyAttachment
metadata:
  name: attach-s3-policy
spec:
  policyARN: arn:aws:iam::123456789012:policy/S3ReadOnlyAccess
  roleName: MyApplicationRole
```
