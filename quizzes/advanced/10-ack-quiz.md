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
