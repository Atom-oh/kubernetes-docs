# AWS Controllers for Kubernetes (ACK) 퀴즈

이 퀴즈는 AWS Controllers for Kubernetes (ACK)에 대한 이해도를 테스트합니다.

## 문제 1: ACK 기본 개념

<details>
<summary>ACK란 무엇이며 주요 목적은?</summary>

**답변:**
ACK(AWS Controllers for Kubernetes)는 Kubernetes에서 AWS 서비스를 직접 관리할 수 있게 해주는 컨트롤러 집합입니다.

**주요 목적:**
- Kubernetes API를 통한 AWS 리소스 관리
- GitOps 워크플로우와의 통합
- 인프라스트럭처를 코드로 관리 (IaC)
- AWS 서비스와 Kubernetes의 네이티브 통합
- 일관된 API 경험 제공
</details>

## 문제 2: 지원 서비스

<details>
<summary>ACK에서 지원하는 주요 AWS 서비스들은?</summary>

**답변:**
- **S3**: 버킷 및 객체 관리
- **RDS**: 데이터베이스 인스턴스 관리
- **DynamoDB**: NoSQL 테이블 관리
- **SQS**: 메시지 큐 관리
- **SNS**: 알림 서비스 관리
- **IAM**: 역할 및 정책 관리
- **Lambda**: 서버리스 함수 관리
- **EC2**: 인스턴스 및 VPC 관리
</details>

## 문제 3: 설치 및 구성

<details>
<summary>ACK 컨트롤러를 설치하는 방법은?</summary>

**답변:**
```bash
# Helm을 사용한 설치
helm repo add aws-controllers-k8s https://aws-controllers-k8s.github.io/community
helm repo update

# S3 컨트롤러 설치 예시
helm install ack-s3-controller \
  aws-controllers-k8s/s3-chart \
  --namespace ack-system \
  --create-namespace \
  --set aws.region=us-west-2

# 또는 kubectl을 사용한 설치
kubectl apply -f https://raw.githubusercontent.com/aws-controllers-k8s/s3-controller/main/config/crd/bases/s3.services.k8s.aws_buckets.yaml
```
</details>

## 문제 4: 리소스 생성

<details>
<summary>ACK를 사용하여 S3 버킷을 생성하는 YAML 예시는?</summary>

**답변:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-ack-s3-bucket
spec:
  name: my-unique-bucket-name-12345
  createBucketConfiguration:
    locationConstraint: us-west-2
  publicAccessBlockConfiguration:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
```
</details>

## 문제 5: IAM 권한

<details>
<summary>ACK 컨트롤러가 필요로 하는 IAM 권한 구성 방법은?</summary>

**답변:**
```bash
# IRSA (IAM Roles for Service Accounts) 생성
eksctl create iamserviceaccount \
  --name ack-s3-controller \
  --namespace ack-system \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve \
  --override-existing-serviceaccounts

# 또는 IAM 정책 직접 생성
aws iam create-policy \
  --policy-name ACK-S3-Policy \
  --policy-document file://ack-s3-policy.json
```

**필요한 권한:**
- 해당 AWS 서비스에 대한 CRUD 권한
- CloudFormation 스택 관리 권한 (일부 서비스)
- 태그 관리 권한
</details>

## 문제 6: 문제 해결

<details>
<summary>ACK 리소스가 생성되지 않을 때 확인해야 할 사항은?</summary>

**답변:**
1. **IAM 권한 확인**:
   ```bash
   kubectl describe serviceaccount ack-s3-controller -n ack-system
   ```

2. **컨트롤러 로그 확인**:
   ```bash
   kubectl logs -n ack-system -l app.kubernetes.io/name=s3-chart
   ```

3. **리소스 상태 확인**:
   ```bash
   kubectl describe bucket my-ack-s3-bucket
   ```

4. **AWS 리전 설정 확인**
5. **네트워크 연결 확인**
6. **CRD 설치 상태 확인**
</details>

---

**점수 계산:**
- 5-6개 정답: 우수 (ACK 전문가 수준)
- 3-4개 정답: 양호 (추가 학습 권장)
- 1-2개 정답: 보통 (기본 개념 복습 필요)
- 0개 정답: 미흡 (전체 내용 재학습 필요)
