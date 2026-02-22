# 시크릿 관리 퀴즈

이 퀴즈는 Kubernetes Secrets, AWS Secrets Manager, External Secrets Operator, 암호화에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. Kubernetes Secret의 기본 인코딩 방식은?

A. AES-256 암호화
B. Base64 인코딩
C. SHA-256 해시
D. RSA 암호화

<details>
<summary>정답 보기</summary>

**정답: B. Base64 인코딩**

**설명:**
Kubernetes Secret은 기본적으로 Base64로 인코딩됩니다. Base64는 암호화가 아닌 단순 인코딩이므로, etcd 암호화를 활성화하거나 외부 시크릿 관리 시스템을 사용해야 합니다.

</details>

### 2. EKS에서 etcd 암호화를 위해 사용하는 AWS 서비스는?

A. AWS Secrets Manager
B. AWS KMS (Key Management Service)
C. AWS Certificate Manager
D. AWS CloudHSM

<details>
<summary>정답 보기</summary>

**정답: B. AWS KMS (Key Management Service)**

**설명:**
EKS는 AWS KMS를 사용하여 etcd에 저장된 Kubernetes Secrets를 암호화합니다. 클러스터 생성 시 또는 이후에 envelope encryption을 활성화할 수 있습니다:
```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:..."}}]'
```

</details>

### 3. External Secrets Operator에서 AWS Secrets Manager의 시크릿을 참조하는 리소스는?

A. SecretStore
B. ExternalSecret
C. ClusterSecretStore
D. A와 B 또는 C와 B

<details>
<summary>정답 보기</summary>

**정답: D. A와 B 또는 C와 B**

**설명:**
External Secrets Operator 구성 요소:
- **SecretStore/ClusterSecretStore**: 외부 시크릿 저장소 연결 설정
- **ExternalSecret**: 실제 시크릿 참조 및 Kubernetes Secret 생성

SecretStore는 네임스페이스 범위, ClusterSecretStore는 클러스터 범위입니다.

</details>

### 4. Pod에서 Secret을 사용하는 방법이 아닌 것은?

A. 환경 변수로 주입
B. 볼륨으로 마운트
C. 이미지 풀 시크릿
D. ConfigMap으로 변환

<details>
<summary>정답 보기</summary>

**정답: D. ConfigMap으로 변환**

**설명:**
Pod에서 Secret을 사용하는 방법:
1. **환경 변수**: `envFrom.secretRef` 또는 `env.valueFrom.secretKeyRef`
2. **볼륨 마운트**: 파일로 마운트
3. **이미지 풀 시크릿**: `imagePullSecrets`

Secret은 ConfigMap으로 자동 변환되지 않습니다. 둘은 별개의 리소스입니다.

</details>

### 5. AWS Secrets Manager에서 자동 로테이션을 구성하는 데 사용하는 AWS 서비스는?

A. AWS EventBridge
B. AWS Lambda
C. AWS Step Functions
D. AWS SNS

<details>
<summary>정답 보기</summary>

**정답: B. AWS Lambda**

**설명:**
AWS Secrets Manager의 자동 로테이션은 Lambda 함수를 사용합니다. AWS는 RDS, Redshift 등을 위한 사전 구축된 로테이션 함수를 제공하며, 커스텀 로테이션도 Lambda로 구현할 수 있습니다.

</details>

### 6. Sealed Secrets의 주요 특징은?

A. etcd에서 암호화
B. Git에 안전하게 저장 가능
C. AWS 전용
D. 자동 로테이션 지원

<details>
<summary>정답 보기</summary>

**정답: B. Git에 안전하게 저장 가능**

**설명:**
Sealed Secrets는 공개키로 시크릿을 암호화하여 Git 저장소에 안전하게 저장할 수 있게 합니다. 클러스터의 Sealed Secrets 컨트롤러만 개인키로 복호화할 수 있습니다. GitOps 워크플로우에 적합합니다.

</details>

### 7. ExternalSecret의 refreshInterval 필드의 역할은?

A. 시크릿 만료 시간 설정
B. 외부 시크릿과 동기화 주기 설정
C. 캐시 유지 시간 설정
D. 재시도 간격 설정

<details>
<summary>정답 보기</summary>

**정답: B. 외부 시크릿과 동기화 주기 설정**

**설명:**
`refreshInterval`은 External Secrets Operator가 외부 시크릿 저장소와 동기화하는 주기를 정의합니다:
```yaml
spec:
  refreshInterval: 1h  # 1시간마다 동기화
```

외부에서 시크릿이 변경되면 이 주기에 따라 Kubernetes Secret이 업데이트됩니다.

</details>

### 8. Kubernetes Secret의 immutable 필드를 true로 설정하면?

A. 시크릿 삭제 불가
B. 시크릿 수정 불가
C. 시크릿 읽기 불가
D. 시크릿 복사 불가

<details>
<summary>정답 보기</summary>

**정답: B. 시크릿 수정 불가**

**설명:**
`immutable: true` 설정은 Secret이 생성된 후 수정을 방지합니다:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
immutable: true
data:
  password: cGFzc3dvcmQ=
```

변경하려면 Secret을 삭제하고 다시 생성해야 합니다. 이는 실수로 인한 변경을 방지하고 성능을 향상시킵니다.

</details>

### 9. CSI Secrets Store Driver의 주요 기능은?

A. Secret을 etcd에 암호화
B. 외부 시크릿을 볼륨으로 마운트
C. Secret 자동 생성
D. Secret 백업

<details>
<summary>정답 보기</summary>

**정답: B. 외부 시크릿을 볼륨으로 마운트**

**설명:**
Secrets Store CSI Driver는 AWS Secrets Manager, Azure Key Vault 등의 외부 시크릿을 CSI 볼륨으로 직접 마운트합니다. Kubernetes Secret을 생성하지 않고도 Pod에서 시크릿을 사용할 수 있습니다.

</details>

### 10. IRSA(IAM Roles for Service Accounts)와 함께 External Secrets를 사용할 때의 장점은?

A. 더 빠른 시크릿 접근
B. IAM 자격 증명을 Pod에 하드코딩할 필요 없음
C. 자동 시크릿 로테이션
D. 무료 사용

<details>
<summary>정답 보기</summary>

**정답: B. IAM 자격 증명을 Pod에 하드코딩할 필요 없음**

**설명:**
IRSA를 사용하면 Service Account에 IAM 역할을 연결할 수 있습니다. External Secrets Operator의 Pod가 AWS 자격 증명 없이 AWS Secrets Manager에 안전하게 접근할 수 있습니다. 이는 보안 모범 사례입니다.

</details>

### 11. Secret 데이터를 stringData로 정의할 때의 특징은?

A. 암호화됨
B. Base64 인코딩 불필요
C. 더 안전함
D. 압축됨

<details>
<summary>정답 보기</summary>

**정답: B. Base64 인코딩 불필요**

**설명:**
`stringData` 필드는 평문으로 값을 지정할 수 있게 합니다:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
stringData:
  password: mypassword  # 평문, 자동으로 Base64 인코딩됨
```

Kubernetes가 자동으로 Base64 인코딩을 처리합니다. 단, 조회 시에는 data 필드에 Base64로 표시됩니다.

</details>

### 12. 시크릿 관리 모범 사례가 아닌 것은?

A. etcd 암호화 활성화
B. RBAC로 Secret 접근 제한
C. 시크릿을 소스 코드에 커밋
D. 외부 시크릿 관리 시스템 사용

<details>
<summary>정답 보기</summary>

**정답: C. 시크릿을 소스 코드에 커밋**

**설명:**
시크릿 관리 모범 사례:
- etcd 암호화 활성화
- RBAC로 Secret 접근 제한
- 외부 시크릿 관리 시스템 사용 (AWS Secrets Manager, HashiCorp Vault 등)
- 감사 로깅 활성화
- 정기적인 시크릿 로테이션

시크릿을 소스 코드에 커밋하면 안 됩니다. 버전 관리 시스템에 평문 시크릿이 노출됩니다.

</details>
