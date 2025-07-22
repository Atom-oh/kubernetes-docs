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
