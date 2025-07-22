# AWS Controllers for Kubernetes (ACK) 퀴즈

이 퀴즈는 AWS Controllers for Kubernetes(ACK)에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. AWS Controllers for Kubernetes(ACK)의 주요 목적은 무엇인가요?

A. Kubernetes 클러스터를 AWS에 배포하고 관리  
B. Kubernetes 클러스터에서 AWS 리소스를 생성하고 관리  
C. AWS 서비스를 Kubernetes 클러스터에 자동으로 배포  
D. Kubernetes 애플리케이션을 AWS Lambda로 변환  

<details>
<summary>정답 및 설명</summary>

**정답: B. Kubernetes 클러스터에서 AWS 리소스를 생성하고 관리**

**설명:**
AWS Controllers for Kubernetes(ACK)의 주요 목적은 Kubernetes 클러스터에서 AWS 리소스를 생성하고 관리하는 것입니다. ACK는 Kubernetes 사용자가 Kubernetes API와 kubectl 명령을 사용하여 AWS 리소스(예: S3 버킷, DynamoDB 테이블, RDS 데이터베이스 등)를 생성, 업데이트, 삭제할 수 있게 해주는 컨트롤러 세트입니다.

**ACK의 주요 특징:**

1. **Kubernetes 네이티브 방식**: AWS 리소스를 Kubernetes 커스텀 리소스(CR)로 관리합니다.
2. **선언적 API**: Kubernetes의 선언적 API를 사용하여 AWS 리소스의 원하는 상태를 정의합니다.
3. **GitOps 호환**: 리소스 정의를 Git 저장소에 저장하고 GitOps 워크플로우를 통해 관리할 수 있습니다.
4. **다양한 AWS 서비스 지원**: S3, DynamoDB, RDS, SQS, SNS 등 다양한 AWS 서비스를 지원합니다.
5. **상태 조정**: AWS 리소스의 실제 상태를 원하는 상태와 일치하도록 지속적으로 조정합니다.

**ACK 작동 방식:**

1. **컨트롤러 설치**: 특정 AWS 서비스(예: S3, RDS)에 대한 ACK 컨트롤러를 Kubernetes 클러스터에 설치합니다.
2. **CRD 등록**: 컨트롤러는 해당 AWS 서비스의 리소스를 나타내는 커스텀 리소스 정의(CRD)를 등록합니다.
3. **CR 생성**: 사용자는 Kubernetes 매니페스트를 작성하여 AWS 리소스를 정의하는 커스텀 리소스(CR)를 생성합니다.
4. **리소스 프로비저닝**: ACK 컨트롤러는 CR을 감시하고 해당하는 AWS 리소스를 생성, 업데이트 또는 삭제합니다.
5. **상태 업데이트**: 컨트롤러는 AWS 리소스의 상태를 CR의 상태 필드에 반영합니다.

**ACK 사용 예시:**

S3 버킷 생성:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-unique-bucket-name
```

RDS 데이터베이스 인스턴스 생성:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  masterUsername: admin
  masterUserPassword:
    namespace: default
    name: my-db-password
    key: password
  allocatedStorage: 20
```

**ACK의 이점:**

1. **통합 워크플로우**: Kubernetes와 AWS 리소스를 동일한 워크플로우로 관리할 수 있습니다.
2. **일관된 도구**: kubectl, Helm 등 익숙한 Kubernetes 도구를 사용하여 AWS 리소스를 관리할 수 있습니다.
3. **버전 제어**: AWS 리소스 정의를 코드로 관리하고 버전 제어할 수 있습니다.
4. **자동화**: Kubernetes의 자동화 기능을 활용하여 AWS 리소스 관리를 자동화할 수 있습니다.
5. **상태 추적**: AWS 리소스의 상태를 Kubernetes 객체의 상태로 추적할 수 있습니다.

**다른 옵션들의 문제점:**
- A. Kubernetes 클러스터를 AWS에 배포하고 관리: 이는 EKS(Elastic Kubernetes Service)의 역할입니다.
- C. AWS 서비스를 Kubernetes 클러스터에 자동으로 배포: ACK는 AWS 서비스 자체를 배포하는 것이 아니라, AWS 리소스를 생성하고 관리합니다.
- D. Kubernetes 애플리케이션을 AWS Lambda로 변환: 이는 ACK의 기능이 아닙니다.
</details>

### 2. ACK에서 'Service Controller'는 무엇을 의미하나요?

A. Kubernetes Service 리소스를 관리하는 컨트롤러  
B. 특정 AWS 서비스(예: S3, DynamoDB)의 리소스를 관리하는 컨트롤러  
C. AWS 서비스 메시를 관리하는 컨트롤러  
D. Kubernetes 서비스와 AWS 서비스 간의 통신을 관리하는 컨트롤러  

<details>
<summary>정답 및 설명</summary>

**정답: B. 특정 AWS 서비스(예: S3, DynamoDB)의 리소스를 관리하는 컨트롤러**

**설명:**
ACK에서 'Service Controller'는 특정 AWS 서비스(예: S3, DynamoDB, RDS 등)의 리소스를 관리하는 컨트롤러를 의미합니다. 각 서비스 컨트롤러는 해당 AWS 서비스의 API를 사용하여 리소스를 생성, 업데이트, 삭제하고 상태를 모니터링합니다. ACK는 각 AWS 서비스에 대해 별도의 서비스 컨트롤러를 제공하므로, 필요한 서비스에 대한 컨트롤러만 설치하여 사용할 수 있습니다.

**서비스 컨트롤러의 주요 기능:**

1. **CRD 등록**: 해당 AWS 서비스의 리소스를 나타내는 커스텀 리소스 정의(CRD)를 등록합니다.
2. **리소스 조정**: Kubernetes CR과 AWS 리소스 간의 상태를 조정합니다.
3. **이벤트 처리**: 리소스 변경 이벤트를 처리하고 적절한 AWS API 호출을 수행합니다.
4. **상태 업데이트**: AWS 리소스의 상태를 CR의 상태 필드에 반영합니다.
5. **오류 처리**: AWS API 호출 중 발생하는 오류를 처리하고 보고합니다.

**주요 ACK 서비스 컨트롤러:**

1. **S3 컨트롤러**: S3 버킷 및 관련 리소스 관리
2. **DynamoDB 컨트롤러**: DynamoDB 테이블 및 인덱스 관리
3. **RDS 컨트롤러**: RDS 데이터베이스 인스턴스 및 클러스터 관리
4. **SQS 컨트롤러**: SQS 대기열 관리
5. **SNS 컨트롤러**: SNS 주제 및 구독 관리
6. **Lambda 컨트롤러**: Lambda 함수 및 이벤트 소스 매핑 관리
7. **IAM 컨트롤러**: IAM 역할, 정책, 사용자 관리
8. **ECR 컨트롤러**: ECR 저장소 관리
9. **EKS 컨트롤러**: EKS 클러스터 및 노드 그룹 관리
10. **API Gateway 컨트롤러**: API Gateway API 및 리소스 관리

**서비스 컨트롤러 설치 예시:**

Helm을 사용한 S3 컨트롤러 설치:
```bash
helm install --namespace ack-system ack-s3-controller \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2
```

**서비스 컨트롤러 아키텍처:**

각 서비스 컨트롤러는 다음과 같은 구성 요소로 이루어져 있습니다:

1. **컨트롤러 매니저**: Kubernetes 컨트롤러 런타임을 관리합니다.
2. **조정기(Reconciler)**: CR과 AWS 리소스 간의 상태를 조정합니다.
3. **리소스 매니저**: AWS SDK를 사용하여 AWS 리소스를 관리합니다.
4. **캐시**: AWS 리소스 상태를 캐싱하여 성능을 향상시킵니다.
5. **이벤트 핸들러**: Kubernetes 이벤트를 처리합니다.

**서비스 컨트롤러 사용 예시:**

S3 버킷 생성 및 관리:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-unique-bucket-name
  versioning:
    status: Enabled
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
```

RDS 데이터베이스 인스턴스 생성 및 관리:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  masterUsername: admin
  masterUserPassword:
    namespace: default
    name: my-db-password
    key: password
  allocatedStorage: 20
  backupRetentionPeriod: 7
  deleteAutomatedBackups: true
  deletionProtection: false
```

**다른 옵션들의 문제점:**
- A. Kubernetes Service 리소스를 관리하는 컨트롤러: ACK 서비스 컨트롤러는 Kubernetes Service 리소스가 아닌 AWS 서비스 리소스를 관리합니다.
- C. AWS 서비스 메시를 관리하는 컨트롤러: AWS App Mesh와 같은 서비스 메시는 별도의 컨트롤러로 관리되며, ACK 서비스 컨트롤러의 주요 목적이 아닙니다.
- D. Kubernetes 서비스와 AWS 서비스 간의 통신을 관리하는 컨트롤러: ACK 서비스 컨트롤러는 통신 관리가 아닌 AWS 리소스 생성 및 관리에 중점을 둡니다.
</details>
### 3. ACK에서 리소스 생성 시 AWS 자격 증명(Credentials)을 관리하는 가장 일반적인 방법은 무엇인가요?

A. Kubernetes Secret에 AWS 액세스 키 저장  
B. 서비스 컨트롤러에 IAM 역할 연결  
C. AWS IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA)  
D. 환경 변수로 AWS 자격 증명 전달  

<details>
<summary>정답 및 설명</summary>

**정답: C. AWS IAM 역할을 Kubernetes 서비스 계정에 연결(IRSA)**

**설명:**
ACK에서 리소스 생성 시 AWS 자격 증명(Credentials)을 관리하는 가장 일반적인 방법은 AWS IAM 역할을 Kubernetes 서비스 계정에 연결(IAM Roles for Service Accounts, IRSA)하는 것입니다. 이 방법은 EKS에서 제공하는 기능으로, Kubernetes 서비스 계정과 AWS IAM 역할 간의 신뢰 관계를 설정하여 파드가 특정 AWS 리소스에 접근할 수 있는 권한을 안전하게 부여합니다.

**IRSA 작동 방식:**

1. **OIDC 제공자 설정**: EKS 클러스터에 대한 OIDC(OpenID Connect) 제공자를 AWS IAM에 설정합니다.
2. **IAM 역할 생성**: 필요한 AWS 권한을 가진 IAM 역할을 생성하고, 신뢰 정책에 Kubernetes 서비스 계정을 지정합니다.
3. **서비스 계정 생성**: 특정 어노테이션을 포함한 Kubernetes 서비스 계정을 생성합니다.
4. **파드 연결**: 해당 서비스 계정을 사용하는 파드는 자동으로 AWS 자격 증명을 받습니다.

**IRSA 설정 단계:**

1. **EKS 클러스터의 OIDC 제공자 ID 가져오기**:
```bash
aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text
```

2. **OIDC 제공자 생성**:
```bash
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

3. **IAM 역할 및 정책 생성**:
```bash
# IAM 정책 생성
aws iam create-policy --policy-name ACKPolicy --policy-document file://ack-policy.json

# IAM 역할 생성 및 서비스 계정 연결
eksctl create iamserviceaccount \
  --name ack-controller \
  --namespace ack-system \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::ACCOUNT_ID:policy/ACKPolicy \
  --approve
```

4. **서비스 계정 어노테이션 확인**:
```bash
kubectl describe serviceaccount ack-controller -n ack-system
```
출력에서 다음과 같은 어노테이션을 확인할 수 있습니다:
```
Annotations:  eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/eksctl-my-cluster-addon-iamserviceaccount-Role1-XXXX
```

**ACK 컨트롤러 설치 시 IRSA 사용 예시:**

Helm을 사용한 S3 컨트롤러 설치:
```bash
helm install --namespace ack-system ack-s3-controller \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2 \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/ACKRole
```

**필요한 IAM 권한:**

ACK 컨트롤러가 AWS 리소스를 관리하기 위해서는 해당 AWS 서비스에 대한 적절한 IAM 권한이 필요합니다. 예를 들어, S3 컨트롤러에는 다음과 같은 권한이 필요할 수 있습니다:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutBucketPolicy",
        "s3:GetBucketPolicy",
        "s3:ListBucket",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock"
      ],
      "Resource": "*"
    }
  ]
}
```

**IRSA의 장점:**

1. **보안 강화**: AWS 자격 증명을 코드나 구성 파일에 저장할 필요가 없습니다.
2. **세분화된 권한**: 각 서비스 계정에 필요한 최소한의 권한만 부여할 수 있습니다.
3. **자격 증명 순환**: AWS STS(Security Token Service)를 통해 자격 증명이 자동으로 순환됩니다.
4. **감사 용이성**: AWS CloudTrail을 통해 서비스 계정의 AWS API 호출을 추적할 수 있습니다.

**다른 자격 증명 관리 방법:**

1. **Kubernetes Secret에 AWS 액세스 키 저장**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: ack-system
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: AKIAXXXXXXXXXXXXXXXX
  AWS_SECRET_ACCESS_KEY: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
이 방법은 보안 위험이 있으므로 권장되지 않습니다.

2. **환경 변수로 AWS 자격 증명 전달**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ack-controller
spec:
  template:
    spec:
      containers:
      - name: controller
        env:
        - name: AWS_ACCESS_KEY_ID
          value: AKIAXXXXXXXXXXXXXXXX
        - name: AWS_SECRET_ACCESS_KEY
          value: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
이 방법도 보안 위험이 있으므로 권장되지 않습니다.

**다른 옵션들의 문제점:**
- A. Kubernetes Secret에 AWS 액세스 키 저장: 이 방법은 액세스 키가 노출될 위험이 있고, 키 순환이 어렵습니다.
- B. 서비스 컨트롤러에 IAM 역할 연결: 이 표현은 정확하지 않습니다. IAM 역할은 EC2 인스턴스나 Kubernetes 서비스 계정에 연결됩니다.
- D. 환경 변수로 AWS 자격 증명 전달: 이 방법은 자격 증명이 로그나 디버그 출력에 노출될 위험이 있습니다.
</details>

### 4. ACK에서 'Adopted Resource'는 무엇을 의미하나요?

A. 다른 Kubernetes 클러스터에서 가져온 리소스  
B. 이미 존재하는 AWS 리소스를 ACK 관리 하에 가져오는 것  
C. ACK에서 자동으로 생성한 종속 리소스  
D. 다른 컨트롤러에서 ACK로 마이그레이션된 리소스  

<details>
<summary>정답 및 설명</summary>

**정답: B. 이미 존재하는 AWS 리소스를 ACK 관리 하에 가져오는 것**

**설명:**
ACK에서 'Adopted Resource'는 이미 존재하는 AWS 리소스를 ACK 관리 하에 가져오는 것을 의미합니다. 이 기능을 통해 ACK를 도입하기 전에 생성된 AWS 리소스를 Kubernetes를 통해 관리할 수 있게 됩니다. 리소스 입양(Adoption)은 기존 인프라를 Kubernetes 기반 GitOps 워크플로우로 통합하는 데 유용합니다.

**리소스 입양 과정:**

1. **AdoptedResource CR 생성**: 입양하려는 AWS 리소스의 정보를 포함한 AdoptedResource 커스텀 리소스를 생성합니다.
2. **리소스 검색**: ACK 컨트롤러는 지정된 AWS 리소스를 찾습니다.
3. **CR 생성**: 컨트롤러는 해당 AWS 리소스를 나타내는 Kubernetes CR을 생성합니다.
4. **관리 전환**: 이후 해당 리소스는 ACK를 통해 관리됩니다.

**AdoptedResource 예시:**
```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: AdoptedResource
metadata:
  name: my-adopted-bucket
spec:
  aws:
    # AWS 리소스가 있는 리전
    region: us-west-2
    # 리소스의 AWS 계정 ID (선택 사항)
    accountID: "123456789012"
  kubernetes:
    # 생성할 CR의 그룹
    group: s3.services.k8s.aws
    # 생성할 CR의 종류
    kind: Bucket
    # 생성할 CR의 메타데이터
    metadata:
      # 생성할 CR의 이름
      name: my-existing-bucket
  # 입양할 AWS 리소스의 고유 식별자
  aws_resource_name: my-existing-bucket
```

**리소스 입양 상태 확인:**
```bash
kubectl get adoptedresources my-adopted-bucket
```

출력 예시:
```
NAME                STATUS   AGE
my-adopted-bucket   ACTIVE   30s
```

**입양된 리소스 확인:**
```bash
kubectl get buckets my-existing-bucket
```

**리소스 입양 시 고려 사항:**

1. **읽기 전용 필드**: 일부 AWS 리소스 필드는 생성 시에만 설정할 수 있고 나중에 수정할 수 없습니다. 이러한 필드는 입양 후에도 수정할 수 없습니다.
2. **리소스 드리프트**: 입양 후 AWS 콘솔이나 CLI를 통해 리소스를 직접 수정하면 ACK와 실제 상태 간에 불일치가 발생할 수 있습니다.
3. **권한**: 리소스를 입양하려면 해당 리소스를 설명하고 수정할 수 있는 IAM 권한이 필요합니다.
4. **리소스 지원**: 모든 ACK 컨트롤러가 리소스 입양을 지원하는 것은 아닙니다.

**리소스 입양 사용 사례:**

1. **기존 인프라 통합**: 기존 AWS 인프라를 Kubernetes 기반 관리로 통합합니다.
2. **점진적 마이그레이션**: 수동으로 관리되던 리소스를 점진적으로 ACK로 마이그레이션합니다.
3. **하이브리드 관리**: 일부 리소스는 ACK로, 일부는 기존 방식으로 관리합니다.
4. **GitOps 도입**: 기존 리소스를 GitOps 워크플로우에 통합합니다.

**리소스 입양 제한 사항:**

1. **복잡한 리소스**: 복잡한 구성이나 관계를 가진 리소스는 입양이 어려울 수 있습니다.
2. **부분 입양**: 리소스의 일부만 입양하는 것은 불가능합니다.
3. **리소스 종속성**: 종속 리소스를 자동으로 입양하지 않으므로, 종속 리소스도 별도로 입양해야 합니다.

**리소스 입양 해제:**

리소스 입양을 해제하려면 AdoptedResource CR을 삭제하면 됩니다:
```bash
kubectl delete adoptedresource my-adopted-bucket
```

이렇게 하면 ACK가 해당 리소스의 관리를 중단하지만, AWS 리소스 자체는 삭제되지 않습니다.

**다른 옵션들의 문제점:**
- A. 다른 Kubernetes 클러스터에서 가져온 리소스: ACK는 AWS 리소스를 관리하며, 다른 Kubernetes 클러스터의 리소스를 가져오는 것은 아닙니다.
- C. ACK에서 자동으로 생성한 종속 리소스: 이는 'Adopted Resource'의 정의가 아닙니다.
- D. 다른 컨트롤러에서 ACK로 마이그레이션된 리소스: 이는 컨트롤러 간의 마이그레이션을 의미하며, 'Adopted Resource'의 정의가 아닙니다.
</details>
### 5. ACK에서 'FieldExport'의 주요 목적은 무엇인가요?

A. AWS 리소스의 필드 값을 Kubernetes Secret이나 ConfigMap으로 내보내기  
B. Kubernetes 리소스의 필드를 AWS 리소스로 내보내기  
C. AWS 리소스의 필드를 다른 AWS 리소스로 복사  
D. Kubernetes 리소스의 필드를 로그로 내보내기  

<details>
<summary>정답 및 설명</summary>

**정답: A. AWS 리소스의 필드 값을 Kubernetes Secret이나 ConfigMap으로 내보내기**

**설명:**
ACK에서 'FieldExport'의 주요 목적은 AWS 리소스의 필드 값을 Kubernetes Secret이나 ConfigMap으로 내보내는 것입니다. 이 기능을 통해 AWS 리소스에서 생성된 값(예: 데이터베이스 엔드포인트, 버킷 이름, 큐 URL 등)을 Kubernetes 애플리케이션에서 쉽게 참조할 수 있게 됩니다. FieldExport는 AWS 리소스와 Kubernetes 애플리케이션 간의 통합을 간소화하는 중요한 기능입니다.

**FieldExport 작동 방식:**

1. **FieldExport CR 생성**: 내보낼 AWS 리소스 필드와 대상 Kubernetes 리소스(Secret 또는 ConfigMap)를 지정하는 FieldExport CR을 생성합니다.
2. **필드 값 추출**: ACK 컨트롤러는 지정된 AWS 리소스에서 필드 값을 추출합니다.
3. **대상 리소스 생성/업데이트**: 추출된 값으로 Secret 또는 ConfigMap을 생성하거나 업데이트합니다.
4. **값 동기화**: AWS 리소스의 필드 값이 변경되면 대상 리소스도 자동으로 업데이트됩니다.

**FieldExport 예시:**
```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: FieldExport
metadata:
  name: export-db-endpoint
spec:
  from:
    path: "status.endpoint"
    resource:
      group: rds.services.k8s.aws
      kind: DBInstance
      name: my-db-instance
  to:
    kind: Secret
    name: db-connection
    namespace: default
    key: endpoint
```

이 예시에서:
- RDS DBInstance `my-db-instance`의 `status.endpoint` 필드 값을 추출합니다.
- 추출된 값을 `default` 네임스페이스의 `db-connection` Secret의 `endpoint` 키로 저장합니다.

**ConfigMap으로 내보내기 예시:**
```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: FieldExport
metadata:
  name: export-bucket-name
spec:
  from:
    path: "spec.name"
    resource:
      group: s3.services.k8s.aws
      kind: Bucket
      name: my-bucket
  to:
    kind: ConfigMap
    name: app-config
    namespace: default
    key: bucket_name
```

**내보낸 값 사용 예시:**

Secret에서 값 사용:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: DB_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: db-connection
              key: endpoint
```

ConfigMap에서 값 사용:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        env:
        - name: BUCKET_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: bucket_name
```

**FieldExport의 장점:**

1. **자동화된 구성**: AWS 리소스 생성 후 수동으로 값을 복사할 필요가 없습니다.
2. **동적 업데이트**: AWS 리소스의 값이 변경되면 자동으로 Kubernetes 리소스가 업데이트됩니다.
3. **GitOps 호환**: 구성 값을 코드로 관리할 수 있습니다.
4. **보안 강화**: 민감한 값을 Secret으로 안전하게 저장할 수 있습니다.

**FieldExport 사용 사례:**

1. **데이터베이스 연결 정보**: RDS 데이터베이스의 엔드포인트, 포트 등을 애플리케이션에 제공합니다.
2. **스토리지 정보**: S3 버킷 이름, ElastiCache 엔드포인트 등을 애플리케이션에 제공합니다.
3. **메시징 정보**: SQS 큐 URL, SNS 주제 ARN 등을 애플리케이션에 제공합니다.
4. **인증 정보**: IAM 역할 ARN, Cognito 사용자 풀 ID 등을 애플리케이션에 제공합니다.

**FieldExport 상태 확인:**
```bash
kubectl get fieldexports export-db-endpoint
```

출력 예시:
```
NAME                STATUS   AGE
export-db-endpoint  ACTIVE   30s
```

**내보낸 Secret 확인:**
```bash
kubectl get secret db-connection -o yaml
```

**내보낸 ConfigMap 확인:**
```bash
kubectl get configmap app-config -o yaml
```

**FieldExport 제한 사항:**

1. **단방향 동기화**: AWS 리소스에서 Kubernetes 리소스로의 단방향 동기화만 지원합니다.
2. **단일 필드**: 하나의 FieldExport는 하나의 필드만 내보낼 수 있습니다.
3. **지원 리소스**: Secret과 ConfigMap만 대상 리소스로 지원됩니다.
4. **컨트롤러 지원**: 모든 ACK 컨트롤러가 FieldExport를 지원하는 것은 아닙니다.

**다른 옵션들의 문제점:**
- B. Kubernetes 리소스의 필드를 AWS 리소스로 내보내기: FieldExport는 반대 방향으로 작동합니다.
- C. AWS 리소스의 필드를 다른 AWS 리소스로 복사: FieldExport는 AWS 리소스 간이 아닌 AWS에서 Kubernetes로의 내보내기를 담당합니다.
- D. Kubernetes 리소스의 필드를 로그로 내보내기: 이는 FieldExport의 기능이 아닙니다.
</details>

### 6. ACK에서 여러 AWS 계정의 리소스를 관리하는 방법으로 가장 적절한 것은 무엇인가요?

A. 각 AWS 계정마다 별도의 ACK 컨트롤러 설치  
B. 다중 계정 자격 증명을 단일 Secret에 저장  
C. 각 AWS 계정에 대한 별도의 서비스 계정과 IAM 역할 설정  
D. AWS Organizations를 통해 단일 자격 증명으로 모든 계정 관리  

<details>
<summary>정답 및 설명</summary>

**정답: C. 각 AWS 계정에 대한 별도의 서비스 계정과 IAM 역할 설정**

**설명:**
ACK에서 여러 AWS 계정의 리소스를 관리하는 가장 적절한 방법은 각 AWS 계정에 대한 별도의 서비스 계정과 IAM 역할을 설정하는 것입니다. 이 접근 방식을 통해 각 계정에 대한 권한을 명확하게 분리하고, 최소 권한 원칙을 준수하며, 여러 AWS 계정의 리소스를 동일한 Kubernetes 클러스터에서 관리할 수 있습니다.

**다중 계정 설정 단계:**

1. **각 AWS 계정에 IAM 역할 생성**:
   각 AWS 계정에 필요한 권한을 가진 IAM 역할을 생성하고, EKS 클러스터의 OIDC 제공자를 신뢰하도록 설정합니다.

2. **각 계정에 대한 Kubernetes 서비스 계정 생성**:
   각 AWS 계정에 대해 별도의 Kubernetes 서비스 계정을 생성하고, 해당 계정의 IAM 역할을 어노테이션으로 지정합니다.

3. **계정별 ACK 컨트롤러 배포**:
   각 AWS 계정에 대해 별도의 ACK 컨트롤러 인스턴스를 배포하고, 해당 계정의 서비스 계정을 사용하도록 구성합니다.

**AWS 계정별 IAM 역할 생성 예시:**

계정 A(123456789012)의 IAM 역할:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:ack-system:ack-account-a"
        }
      }
    }
  ]
}
```

계정 B(987654321098)의 IAM 역할:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:ack-system:ack-account-b"
        }
      }
    }
  ]
}
```

**계정별 Kubernetes 서비스 계정 생성:**

계정 A의 서비스 계정:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ack-account-a
  namespace: ack-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ACKRoleAccountA
```

계정 B의 서비스 계정:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ack-account-b
  namespace: ack-system
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::987654321098:role/ACKRoleAccountB
```

**계정별 ACK 컨트롤러 배포:**

계정 A의 S3 컨트롤러:
```bash
helm install --namespace ack-system ack-s3-controller-a \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2 \
  --set serviceAccount.name=ack-account-a \
  --set serviceAccount.create=false \
  --set resourceTags.ack-account=account-a
```

계정 B의 S3 컨트롤러:
```bash
helm install --namespace ack-system ack-s3-controller-b \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2 \
  --set serviceAccount.name=ack-account-b \
  --set serviceAccount.create=false \
  --set resourceTags.ack-account=account-b
```

**리소스 생성 시 계정 지정:**

계정 A의 S3 버킷:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket-account-a
  annotations:
    services.k8s.aws/controller-account: account-a
spec:
  name: my-unique-bucket-account-a
```

계정 B의 S3 버킷:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket-account-b
  annotations:
    services.k8s.aws/controller-account: account-b
spec:
  name: my-unique-bucket-account-b
```

**다중 계정 관리의 장점:**

1. **권한 분리**: 각 AWS 계정에 대한 권한을 명확하게 분리하여 보안을 강화합니다.
2. **최소 권한**: 각 서비스 계정에 필요한 최소한의 권한만 부여할 수 있습니다.
3. **계정 격리**: 한 계정의 문제가 다른 계정에 영향을 미치지 않습니다.
4. **감사 용이성**: 각 계정의 활동을 별도로 추적하고 감사할 수 있습니다.

**다중 계정 관리의 단점:**

1. **복잡성 증가**: 여러 컨트롤러와 서비스 계정을 관리해야 하므로 복잡성이 증가합니다.
2. **리소스 사용량**: 각 계정마다 별도의 컨트롤러를 실행하므로 리소스 사용량이 증가합니다.
3. **구성 중복**: 여러 컨트롤러에 대한 구성이 중복될 수 있습니다.

**다른 옵션들의 문제점:**
- A. 각 AWS 계정마다 별도의 ACK 컨트롤러 설치: 이 방법은 가능하지만, 일반적으로 각 계정마다 별도의 컨트롤러 인스턴스를 동일한 Kubernetes 클러스터에 배포하는 것이 더 효율적입니다.
- B. 다중 계정 자격 증명을 단일 Secret에 저장: 이 방법은 보안 위험이 있으며, 권한 분리 원칙에 위배됩니다.
- D. AWS Organizations를 통해 단일 자격 증명으로 모든 계정 관리: ACK는 AWS Organizations를 통한 단일 자격 증명 관리를 직접 지원하지 않으며, 이 방법은 최소 권한 원칙에 위배될 수 있습니다.
</details>
### 7. ACK에서 AWS 리소스 삭제 시 'deletion policy'의 역할은 무엇인가요?

A. AWS 리소스 삭제 순서 결정  
B. AWS 리소스 삭제 시 종속 리소스 처리 방법 지정  
C. Kubernetes CR 삭제 시 실제 AWS 리소스 처리 방법 지정  
D. AWS 리소스 삭제 권한 관리  

<details>
<summary>정답 및 설명</summary>

**정답: C. Kubernetes CR 삭제 시 실제 AWS 리소스 처리 방법 지정**

**설명:**
ACK에서 'deletion policy'의 역할은 Kubernetes CR(Custom Resource) 삭제 시 실제 AWS 리소스 처리 방법을 지정하는 것입니다. 이 정책을 통해 Kubernetes에서 리소스를 삭제할 때 해당하는 AWS 리소스를 실제로 삭제할지, 유지할지, 또는 스냅샷을 생성한 후 삭제할지 등을 제어할 수 있습니다. 이는 데이터 손실 방지와 리소스 관리 유연성을 제공하는 중요한 기능입니다.

**삭제 정책 유형:**

1. **Delete (기본값)**: Kubernetes CR이 삭제되면 해당 AWS 리소스도 삭제됩니다.
2. **Orphan**: Kubernetes CR이 삭제되어도 AWS 리소스는 유지됩니다.
3. **Snapshot (일부 리소스만 지원)**: 리소스의 스냅샷을 생성한 후 삭제합니다.

**삭제 정책 설정 방법:**

1. **어노테이션 사용**:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
spec:
  name: my-unique-bucket-name
```

2. **컨트롤러 기본값 설정**:
Helm 차트 설치 시 기본 삭제 정책을 설정할 수 있습니다:
```bash
helm install --namespace ack-system ack-s3-controller \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2 \
  --set deletionPolicy=ORPHAN
```

**삭제 정책 사용 예시:**

1. **Delete 정책 (기본값)**:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
  # 어노테이션이 없으면 기본값인 'delete' 정책이 적용됩니다
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  masterUsername: admin
  masterUserPassword:
    namespace: default
    name: my-db-password
    key: password
  allocatedStorage: 20
```

2. **Orphan 정책**:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-important-bucket
  annotations:
    services.k8s.aws/deletion-policy: "orphan"
spec:
  name: my-important-bucket-name
```

3. **Snapshot 정책 (RDS와 같은 일부 리소스만 지원)**:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
  annotations:
    services.k8s.aws/deletion-policy: "snapshot"
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  # ... 기타 설정 ...
```

**삭제 정책 사용 시나리오:**

1. **Delete 정책**:
   - 개발/테스트 환경의 임시 리소스
   - 자동화된 CI/CD 파이프라인의 일부로 생성/삭제되는 리소스
   - 데이터가 중요하지 않은 리소스

2. **Orphan 정책**:
   - 중요한 프로덕션 데이터를 포함하는 리소스
   - 실수로 인한 삭제를 방지해야 하는 리소스
   - ACK 관리에서 제외하려는 리소스
   - 다른 시스템에서 참조하는 공유 리소스

3. **Snapshot 정책**:
   - 삭제 전 백업이 필요한 데이터베이스
   - 롤백 가능성을 유지해야 하는 리소스
   - 규정 준수를 위해 데이터 보존이 필요한 리소스

**삭제 정책 변경:**

리소스가 생성된 후에도 어노테이션을 수정하여 삭제 정책을 변경할 수 있습니다:
```bash
kubectl annotate bucket my-bucket services.k8s.aws/deletion-policy=orphan --overwrite
```

**삭제 정책과 AdoptedResource:**

AdoptedResource를 사용하여 기존 AWS 리소스를 입양한 경우, 해당 리소스에 대한 삭제 정책을 신중하게 설정하는 것이 중요합니다. 기본적으로 AdoptedResource는 Orphan 정책을 사용하지만, 명시적으로 설정하는 것이 좋습니다:

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: AdoptedResource
metadata:
  name: my-adopted-bucket
spec:
  aws:
    region: us-west-2
  kubernetes:
    group: s3.services.k8s.aws
    kind: Bucket
    metadata:
      name: my-existing-bucket
      annotations:
        services.k8s.aws/deletion-policy: "orphan"
  aws_resource_name: my-existing-bucket
```

**삭제 정책 제한 사항:**

1. **서비스 지원**: 모든 ACK 컨트롤러가 모든 삭제 정책을 지원하는 것은 아닙니다.
2. **Snapshot 제한**: Snapshot 정책은 스냅샷을 지원하는 리소스(예: RDS, EBS)에서만 사용할 수 있습니다.
3. **정책 변경 시점**: 리소스 삭제 요청 시점의 정책이 적용됩니다.

**다른 옵션들의 문제점:**
- A. AWS 리소스 삭제 순서 결정: 삭제 정책은 삭제 순서가 아닌 삭제 여부와 방법을 결정합니다.
- B. AWS 리소스 삭제 시 종속 리소스 처리 방법 지정: 이는 AWS 서비스 자체의 동작에 따라 결정되며, ACK 삭제 정책의 역할이 아닙니다.
- D. AWS 리소스 삭제 권한 관리: 삭제 권한은 IAM 정책을 통해 관리되며, ACK 삭제 정책의 역할이 아닙니다.
</details>

### 8. ACK에서 'late initialization'이란 무엇인가요?

A. AWS 리소스 생성을 지연시키는 기능  
B. AWS에서 자동 생성된 필드 값을 Kubernetes CR에 다시 채우는 기능  
C. Kubernetes 클러스터 시작 후 ACK 컨트롤러를 지연 시작하는 기능  
D. AWS 리소스 업데이트를 일정 시간 지연시키는 기능  

<details>
<summary>정답 및 설명</summary>

**정답: B. AWS에서 자동 생성된 필드 값을 Kubernetes CR에 다시 채우는 기능**

**설명:**
ACK에서 'late initialization'이란 AWS에서 자동 생성된 필드 값을 Kubernetes CR(Custom Resource)에 다시 채우는 기능입니다. 많은 AWS 리소스는 생성 시 AWS에서 자동으로 생성되는 필드(예: 리소스 ARN, 생성 시간, 기본 구성 값 등)를 가지고 있습니다. Late initialization은 이러한 자동 생성된 값을 AWS에서 가져와 Kubernetes CR의 spec 필드에 다시 채워 넣어, CR이 실제 AWS 리소스의 완전한 상태를 반영하도록 합니다.

**Late Initialization의 작동 방식:**

1. **리소스 생성**: 사용자가 필수 필드만 포함된 CR을 생성합니다.
2. **AWS 리소스 생성**: ACK 컨트롤러가 AWS API를 호출하여 리소스를 생성합니다.
3. **자동 생성 필드**: AWS는 리소스를 생성하면서 추가 필드와 기본값을 설정합니다.
4. **필드 동기화**: ACK 컨트롤러는 AWS에서 리소스 상태를 가져와 누락된 필드를 CR의 spec에 채웁니다.
5. **상태 업데이트**: 리소스의 전체 상태는 CR의 status 필드에도 반영됩니다.

**Late Initialization 예시:**

사용자가 생성한 원래 CR:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-unique-bucket-name
```

Late initialization 후 CR:
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-unique-bucket-name
  versioning:
    status: Suspended  # AWS의 기본값으로 채워짐
  publicAccessBlock:
    blockPublicAcls: true  # AWS의 기본값으로 채워짐
    blockPublicPolicy: true  # AWS의 기본값으로 채워짐
    ignorePublicAcls: true  # AWS의 기본값으로 채워짐
    restrictPublicBuckets: true  # AWS의 기본값으로 채워짐
status:
  ackResourceMetadata:
    arn: arn:aws:s3:::my-unique-bucket-name
    ownerAccountID: "123456789012"
    region: us-west-2
  conditions:
  - status: "True"
    type: ACK.ResourceSynced
  creationTimestamp: "2023-07-22T12:34:56Z"
```

**Late Initialization의 이점:**

1. **간소화된 CR 정의**: 사용자는 필수 필드만 지정하고 나머지는 AWS 기본값을 사용할 수 있습니다.
2. **완전한 리소스 상태**: CR이 AWS 리소스의 실제 상태를 완전히 반영합니다.
3. **선언적 구성 유지**: 자동 생성된 필드도 CR의 spec에 포함되어 선언적 구성을 유지합니다.
4. **드리프트 감지 개선**: 모든 필드가 spec에 포함되므로 드리프트 감지가 더 정확해집니다.

**Late Initialization과 Status 필드의 차이:**

- **Late Initialization**: AWS에서 자동 생성된 값을 CR의 **spec** 필드에 채웁니다. 이는 리소스의 원하는 상태(desired state)의 일부가 됩니다.
- **Status 필드**: 리소스의 현재 상태(current state)를 반영하며, 읽기 전용입니다. 여기에는 ARN, 생성 시간, 리소스 상태 등이 포함됩니다.

**Late Initialization 예시 (RDS):**

사용자가 생성한 원래 CR:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  masterUsername: admin
  masterUserPassword:
    namespace: default
    name: my-db-password
    key: password
  allocatedStorage: 20
```

Late initialization 후 CR:
```yaml
apiVersion: rds.services.k8s.aws/v1alpha1
kind: DBInstance
metadata:
  name: my-db-instance
spec:
  dbInstanceIdentifier: my-db-instance
  engine: mysql
  dbInstanceClass: db.t3.micro
  masterUsername: admin
  masterUserPassword:
    namespace: default
    name: my-db-password
    key: password
  allocatedStorage: 20
  backupRetentionPeriod: 7  # AWS의 기본값으로 채워짐
  autoMinorVersionUpgrade: true  # AWS의 기본값으로 채워짐
  copyTagsToSnapshot: true  # AWS의 기본값으로 채워짐
  publiclyAccessible: false  # AWS의 기본값으로 채워짐
  storageType: gp2  # AWS의 기본값으로 채워짐
status:
  ackResourceMetadata:
    arn: arn:aws:rds:us-west-2:123456789012:db:my-db-instance
    ownerAccountID: "123456789012"
    region: us-west-2
  conditions:
  - status: "True"
    type: ACK.ResourceSynced
  dbInstanceStatus: available
  endpoint:
    address: my-db-instance.abcdefghijkl.us-west-2.rds.amazonaws.com
    port: 3306
  engineVersion: 8.0.28
  dbInstanceArn: arn:aws:rds:us-west-2:123456789012:db:my-db-instance
  creationTimestamp: "2023-07-22T12:34:56Z"
```

**Late Initialization 제한 사항:**

1. **변경 불가능한 필드**: 일부 필드는 생성 후 변경할 수 없으므로, late initialization 후에도 수정할 수 없습니다.
2. **컨트롤러 지원**: 모든 ACK 컨트롤러가 late initialization을 동일하게 구현하는 것은 아닙니다.
3. **타이밍**: Late initialization은 리소스 생성 후 발생하므로, 초기 생성 시에는 이러한 값을 사용할 수 없습니다.

**다른 옵션들의 문제점:**
- A. AWS 리소스 생성을 지연시키는 기능: Late initialization은 리소스 생성을 지연시키지 않습니다.
- C. Kubernetes 클러스터 시작 후 ACK 컨트롤러를 지연 시작하는 기능: 이는 late initialization의 의미가 아닙니다.
- D. AWS 리소스 업데이트를 일정 시간 지연시키는 기능: Late initialization은 업데이트를 지연시키지 않습니다.
</details>
### 9. ACK와 AWS CloudFormation의 주요 차이점은 무엇인가요?

A. ACK는 AWS 리소스만 관리하지만 CloudFormation은 타사 리소스도 관리할 수 있음  
B. ACK는 선언적 API를 사용하지만 CloudFormation은 명령형 API를 사용함  
C. ACK는 Kubernetes 네이티브 방식으로 AWS 리소스를 관리하지만 CloudFormation은 AWS 네이티브 방식을 사용함  
D. ACK는 무료지만 CloudFormation은 유료 서비스임  

<details>
<summary>정답 및 설명</summary>

**정답: C. ACK는 Kubernetes 네이티브 방식으로 AWS 리소스를 관리하지만 CloudFormation은 AWS 네이티브 방식을 사용함**

**설명:**
ACK와 AWS CloudFormation의 주요 차이점은 ACK는 Kubernetes 네이티브 방식으로 AWS 리소스를 관리하지만 CloudFormation은 AWS 네이티브 방식을 사용한다는 것입니다. ACK는 Kubernetes의 커스텀 리소스 정의(CRD)와 컨트롤러를 사용하여 AWS 리소스를 관리하므로, Kubernetes 사용자는 익숙한 도구와 워크플로우를 사용하여 AWS 리소스를 관리할 수 있습니다. 반면 CloudFormation은 AWS의 자체 템플릿 형식과 API를 사용하여 AWS 리소스를 관리합니다.

**ACK와 CloudFormation의 주요 차이점:**

1. **관리 방식**:
   - **ACK**: Kubernetes API, kubectl, YAML 매니페스트 등 Kubernetes 네이티브 도구를 사용합니다.
   - **CloudFormation**: AWS 콘솔, AWS CLI, CloudFormation 템플릿(JSON/YAML) 등 AWS 네이티브 도구를 사용합니다.

2. **리소스 정의**:
   - **ACK**: Kubernetes 커스텀 리소스(CR)로 AWS 리소스를 정의합니다.
   - **CloudFormation**: CloudFormation 템플릿으로 AWS 리소스를 정의합니다.

3. **상태 관리**:
   - **ACK**: Kubernetes etcd에 리소스 상태를 저장하고 Kubernetes 컨트롤러 패턴을 사용하여 조정합니다.
   - **CloudFormation**: CloudFormation 서비스가 스택 상태를 관리하고 변경 세트를 통해 업데이트를 처리합니다.

4. **실행 환경**:
   - **ACK**: Kubernetes 클러스터 내에서 실행됩니다.
   - **CloudFormation**: AWS 클라우드에서 관리형 서비스로 실행됩니다.

5. **통합 환경**:
   - **ACK**: Kubernetes 에코시스템(Helm, Kustomize, GitOps 도구 등)과 통합됩니다.
   - **CloudFormation**: AWS 에코시스템(AWS CDK, AWS CLI, AWS 콘솔 등)과 통합됩니다.

**ACK 예시:**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  name: my-unique-bucket-name
  versioning:
    status: Enabled
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
```

**CloudFormation 예시:**
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-unique-bucket-name
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
```

**ACK의 장점 (CloudFormation 대비):**

1. **Kubernetes 통합**: Kubernetes 사용자에게 익숙한 도구와 워크플로우를 제공합니다.
2. **실시간 조정**: Kubernetes 컨트롤러는 지속적으로 실행되어 리소스 상태를 조정합니다.
3. **세분화된 리소스 관리**: 개별 리소스 수준에서 관리가 가능합니다.
4. **Kubernetes 리소스와 함께 관리**: AWS 리소스와 Kubernetes 리소스를 동일한 방식으로 관리할 수 있습니다.
5. **GitOps 호환성**: Kubernetes 기반 GitOps 워크플로우와 쉽게 통합됩니다.

**CloudFormation의 장점 (ACK 대비):**

1. **AWS 네이티브 통합**: AWS 서비스와 더 깊게 통합되어 있습니다.
2. **스택 기반 관리**: 관련 리소스를 스택으로 그룹화하여 관리합니다.
3. **변경 세트**: 변경 사항을 미리 확인하고 적용할 수 있습니다.
4. **롤백 기능**: 오류 발생 시 자동 롤백을 지원합니다.
5. **더 넓은 리소스 지원**: 더 많은 AWS 리소스 유형을 지원합니다.

**사용 시나리오 비교:**

1. **Kubernetes 중심 환경**:
   - **ACK 선호**: Kubernetes를 주요 플랫폼으로 사용하고 AWS 리소스도 동일한 방식으로 관리하려는 경우
   - **CloudFormation 선호**: Kubernetes와 AWS 리소스를 별도로 관리하려는 경우

2. **하이브리드 클라우드**:
   - **ACK 선호**: Kubernetes를 여러 클라우드 환경에서 일관되게 사용하려는 경우
   - **CloudFormation 선호**: AWS 리소스만 관리하는 경우

3. **기존 투자**:
   - **ACK 선호**: 이미 Kubernetes 도구와 워크플로우에 투자한 경우
   - **CloudFormation 선호**: 이미 AWS 도구와 워크플로우에 투자한 경우

**다른 옵션들의 문제점:**
- A. ACK는 AWS 리소스만 관리하지만 CloudFormation은 타사 리소스도 관리할 수 있음: CloudFormation도 기본적으로 AWS 리소스만 관리하며, 타사 리소스는 커스텀 리소스를 통해 제한적으로 지원합니다.
- B. ACK는 선언적 API를 사용하지만 CloudFormation은 명령형 API를 사용함: 둘 다 선언적 접근 방식을 사용합니다.
- D. ACK는 무료지만 CloudFormation은 유료 서비스임: CloudFormation 자체는 무료 서비스이며, 생성한 리소스에 대해서만 비용이 발생합니다.
</details>

### 10. ACK를 사용하여 S3 버킷과 IAM 역할을 생성하는 가장 좋은 방법은 무엇인가요?

A. 단일 YAML 파일에 모든 리소스 정의  
B. 각 리소스 유형에 대한 별도의 컨트롤러를 설치하고 별도의 YAML 파일로 리소스 정의  
C. AWS CLI를 사용하여 리소스를 생성한 다음 ACK로 가져오기  
D. CloudFormation 템플릿을 사용하여 리소스 생성  

<details>
<summary>정답 및 설명</summary>

**정답: B. 각 리소스 유형에 대한 별도의 컨트롤러를 설치하고 별도의 YAML 파일로 리소스 정의**

**설명:**
ACK를 사용하여 S3 버킷과 IAM 역할을 생성하는 가장 좋은 방법은 각 리소스 유형에 대한 별도의 컨트롤러를 설치하고 별도의 YAML 파일로 리소스를 정의하는 것입니다. ACK는 AWS 서비스별로 별도의 컨트롤러를 제공하므로, S3 리소스를 관리하려면 S3 컨트롤러를, IAM 리소스를 관리하려면 IAM 컨트롤러를 설치해야 합니다. 각 컨트롤러는 해당 서비스의 리소스를 관리하기 위한 CRD를 설치하고, 이러한 CRD를 사용하여 리소스를 정의할 수 있습니다.

**ACK 컨트롤러 설치 단계:**

1. **S3 컨트롤러 설치**:
```bash
helm install --namespace ack-system ack-s3-controller \
  oci://public.ecr.aws/aws-controllers-k8s/s3-chart \
  --set aws.region=us-west-2
```

2. **IAM 컨트롤러 설치**:
```bash
helm install --namespace ack-system ack-iam-controller \
  oci://public.ecr.aws/aws-controllers-k8s/iam-chart \
  --set aws.region=us-west-2
```

**S3 버킷 정의 (bucket.yaml):**
```yaml
apiVersion: s3.services.k8s.aws/v1alpha1
kind: Bucket
metadata:
  name: my-app-bucket
spec:
  name: my-unique-app-bucket-name
  versioning:
    status: Enabled
  publicAccessBlock:
    blockPublicAcls: true
    blockPublicPolicy: true
    ignorePublicAcls: true
    restrictPublicBuckets: true
```

**IAM 역할 정의 (role.yaml):**
```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Role
metadata:
  name: my-app-role
spec:
  name: my-app-role
  description: "Role for my application"
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
```

**IAM 정책 정의 (policy.yaml):**
```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: Policy
metadata:
  name: my-app-policy
spec:
  name: my-app-policy
  description: "Policy for my application"
  policyDocument: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "s3:GetObject",
            "s3:PutObject"
          ],
          "Resource": "arn:aws:s3:::my-unique-app-bucket-name/*"
        }
      ]
    }
```

**IAM 역할에 정책 연결 (role-policy-attachment.yaml):**
```yaml
apiVersion: iam.services.k8s.aws/v1alpha1
kind: RolePolicyAttachment
metadata:
  name: my-app-role-policy-attachment
spec:
  roleName: my-app-role
  policyARN: "arn:aws:iam::ACCOUNT_ID:policy/my-app-policy"
```

**리소스 생성:**
```bash
kubectl apply -f bucket.yaml
kubectl apply -f role.yaml
kubectl apply -f policy.yaml
kubectl apply -f role-policy-attachment.yaml
```

**이 접근 방식의 장점:**

1. **모듈성**: 각 리소스를 별도로 관리할 수 있어 유지 관리가 용이합니다.
2. **컨트롤러 분리**: 각 서비스에 대한 컨트롤러가 분리되어 있어 문제 격리가 용이합니다.
3. **리소스 종속성 관리**: 리소스 간의 종속성을 명시적으로 관리할 수 있습니다.
4. **선택적 설치**: 필요한 컨트롤러만 설치하여 리소스 사용을 최적화할 수 있습니다.
5. **버전 관리**: 각 컨트롤러를 독립적으로 업그레이드할 수 있습니다.

**리소스 간 종속성 처리:**

ACK는 리소스 간 종속성을 자동으로 관리하지 않으므로, 종속성이 있는 리소스를 생성할 때는 적절한 순서를 고려해야 합니다. 예를 들어, RolePolicyAttachment는 Role과 Policy가 먼저 생성되어야 합니다.

이를 관리하는 방법:

1. **Kubernetes Job 사용**:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: create-role-policy-attachment
spec:
  template:
    spec:
      containers:
      - name: kubectl
        image: bitnami/kubectl
        command:
        - /bin/sh
        - -c
        - |
          kubectl wait --for=condition=ACK.ResourceSynced=True role.iam.services.k8s.aws/my-app-role --timeout=300s
          kubectl wait --for=condition=ACK.ResourceSynced=True policy.iam.services.k8s.aws/my-app-policy --timeout=300s
          kubectl apply -f /manifests/role-policy-attachment.yaml
        volumeMounts:
        - name: manifests
          mountPath: /manifests
      volumes:
      - name: manifests
        configMap:
          name: aws-resource-manifests
      restartPolicy: OnFailure
```

2. **Helm 차트 사용**:
Helm의 hooks를 사용하여 리소스 생성 순서를 제어할 수 있습니다.

3. **GitOps 도구 사용**:
ArgoCD나 Flux와 같은 GitOps 도구는 종속성 관리 기능을 제공합니다.

**다른 옵션들의 문제점:**
- A. 단일 YAML 파일에 모든 리소스 정의: 서로 다른 컨트롤러가 관리하는 리소스를 단일 파일에 정의하는 것은 가능하지만, 관리와 문제 해결이 어려워질 수 있습니다.
- C. AWS CLI를 사용하여 리소스를 생성한 다음 ACK로 가져오기: 이 방법은 가능하지만(AdoptedResource 사용), 처음부터 ACK로 리소스를 생성하는 것이 더 일관된 관리를 제공합니다.
- D. CloudFormation 템플릿을 사용하여 리소스 생성: 이는 ACK를 사용하는 방법이 아니라 완전히 다른 접근 방식입니다.
</details>
